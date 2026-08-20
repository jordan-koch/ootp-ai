"""AC6 — Tier B. The landed warehouse against the probe save's export, per field by name.

This is the criterion that converts the field map's labels from beliefs into findings, and
it must be green before anything is rendered for a GM to read. A report built on an
unvalidated parse is exactly the silent-wrong-data failure `requests/README.md` describes.

## What this can and cannot reach, permanently

**Tier B exists only on the standard-mode probe.** Challenge Mode has no export (ADR 0003),
so the row-for-row differential is *structurally confined* to the Cubs save and can never
run against `OOTP-AI.lg`. That is not a gap to close; it is a property of the project, and
it is said here rather than left for a green suite to imply the parser was diffed against
the club we actually manage. What covers the managed league instead: Tier A
(`test_names_join_boston.py`), byte accounting, cross-mode format equivalence
(`test_cross_mode_format.py`), and the operator's own in-game spot-check.

**Tier B is never a rating validator.** The export writes display scale — measured,
`players_batting.batting_ratings_overall_contact` carries exactly 12 distinct values across
20-80 — so a bucketed comparison passes a parser reading the *adjacent* `u16`, which is
CLAUDE.md's named correctness trap in its most dangerous form. This slice lands no ratings
and this harness compares none; `tests/test_export_diff.py` asserts that mechanically, and
`players.csv` (Tier A) stays the permanent exact rating validator.

## The three ways a correct parse disagrees with the export, all measured

Named here because a reader who meets them in a failure message deserves to know they were
expected, and because each one is a fact about the *export* rather than about the walk:

1. **26 clubs land a NULL city** where the export writes the nickname. They are the generic
   all-star sides; the save carries no city string for them.
2. **229 clubs land a NULL `historical_id`** where the export writes `''`. A CSV-shaped
   export has no NULL.
3. **176 players carry a negated `league_id` in the export**, marking *assigned to a club
   but on no roster list*. `test_the_negated_league_ids_are_exactly_the_unrostered_players`
   below proves that reading against a set the roster walk derives from entirely different
   bytes.

And one that is not a disagreement at all: `players.dat` frames **18,077** records against
the export's 18,072 active. The five extras are carried by the export in no form whatever.

## A vacuous green is worse than a red

If the export is unreachable this module skips with a named reason rather than passing
(§4.3). `test_the_skip_path_names_its_reason` fires that path, because a skip nobody has
seen work is as unverified as a guard nobody has seen fail.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from fixtures.warehouse import landed_probe, settings_or_skip, warehouse_or_skip
from ootp_ai.config import ConfigError, Settings
from ootp_ai.db import connect_truth
from ootp_ai.ingest import IngestRun, ParsedSnapshot
from ootp_ai.validate.export_diff import (
    ABSENCE_RULES,
    DIVISION_MEMBERSHIPS,
    DIVISION_SPEC,
    EXPORT_ACTIVE_PLAYERS,
    EXPORT_CALENDAR_EVENTS,
    EXPORT_ROSTER_ROWS,
    EXPORT_TEAMS,
    PARSED_ONLY_PLAYER_IDS,
    PARSED_ONLY_PLAYERS,
    ROW_SPECS,
    SPECS,
    TRUTH_SAVE_HUMAN_TEAM_ID,
    TRUTH_SAVE_SIM_DATE,
    DiffReport,
    ProvenanceMismatch,
    check_provenance,
    compare_keyed,
    diff_snapshot,
)
from ootp_ai.warehouse.sql import column_list, quote_ident

pytestmark = pytest.mark.gamedata

#: How many `retired = 0` export rows carry a negated `league_id`. Measured, and equal to
#: the roster walk's independently derived `unrostered` population.
NEGATED_LEAGUE_ROWS = 176

_TEAM_SPEC = SPECS[0]


@pytest.fixture(scope="module")
def settings() -> Settings:
    return settings_or_skip()


@pytest.fixture(scope="module")
def truth(settings: Settings) -> Iterator[Connection[DictCursor]]:
    """The export, opened read-only, or a skip that names the missing key.

    A read-only session is asserted by `db.connect_truth` rather than promised: rebuilding
    `ootp_truth_real` costs a save rebuild plus an export run, and it is the only artifact
    in the project that can prove the parser correct.
    """
    try:
        connection = connect_truth(settings)
    except ConfigError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(
            f"the ground-truth export is unavailable ({exc}), so AC6 has no answer key. "
            "Skipping rather than passing: the criterion is unproven, not satisfied."
        )
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture(scope="module")
def landed(settings: Settings) -> Iterator[tuple[ParsedSnapshot, IngestRun]]:
    """The probe, parsed and landed under its own `save_id`, then taken back out.

    Landed rather than compared in memory, deliberately: the criterion is about what the
    **warehouse** holds. A differential run against the parser's Python objects would leave
    the loader — the layer that binds every column, converts every date and decides what
    NULL means — entirely unexercised, and the report layer reads the warehouse.

    Module-scoped because it costs a ~2 s parse plus a ~5 s landing of ~300,000 rows, and
    every test below asks a different question of the same landing.
    """
    with warehouse_or_skip(settings) as connection:
        with landed_probe(settings, connection, which="truth_save") as landing:
            yield landing


@pytest.fixture(scope="module")
def warehouse(settings: Settings) -> Iterator[Connection[DictCursor]]:
    with warehouse_or_skip(settings) as connection:
        yield connection


@pytest.fixture(scope="module")
def report(
    warehouse: Connection[DictCursor],
    truth: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> DiffReport:
    _parsed, run = landed
    return diff_snapshot(
        warehouse,
        truth,
        save_id=run.save_id,
        sim_date=run.sim_date,
        ingest_seq=run.ingest_seq,
        human_team_id=run.human_team_id,
    )


# ── provenance, asserted before any value is compared ────────────────────────


def test_provenance_is_asserted_before_anything_is_compared(
    truth: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """AC6's first clause. The binaries and the export must describe one universe.

    A field diff across two moments of the same league is noise that looks like a finding:
    ids still line up, so it returns a plausible scatter of roster and age differences and
    reads exactly like a parser bug.
    """
    _parsed, run = landed

    assert str(run.sim_date) == TRUTH_SAVE_SIM_DATE
    assert run.human_team_id == TRUTH_SAVE_HUMAN_TEAM_ID

    check_provenance(truth, sim_date=run.sim_date, human_team_id=run.human_team_id)


def test_the_provenance_check_refuses_a_snapshot_from_another_moment(
    truth: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The guard, seen to fire. One that has never refused anything is decoration."""
    _parsed, run = landed
    from ootp_ai.parser.primitives import SaveDate

    with pytest.raises(ProvenanceMismatch) as caught:
        check_provenance(
            truth,
            sim_date=SaveDate(day=1, month=4, year=2024),
            human_team_id=run.human_team_id,
        )
    assert "2024-04-01" in str(caught.value)
    assert TRUTH_SAVE_SIM_DATE in str(caught.value)


def test_the_provenance_check_refuses_a_snapshot_of_another_club(
    truth: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The other half, which fails differently and matters more.

    A club disagreement means somebody pointed the harness at another save entirely, and
    every id would disagree at once.
    """
    _parsed, run = landed
    with pytest.raises(ProvenanceMismatch) as caught:
        check_provenance(truth, sim_date=run.sim_date, human_team_id=TRUTH_SAVE_HUMAN_TEAM_ID + 1)
    assert str(TRUTH_SAVE_HUMAN_TEAM_ID) in str(caught.value)


def test_the_export_sim_date_needs_a_quoted_identifier_to_be_read_at_all(
    truth: Connection[DictCursor],
) -> None:
    """The measured, silent data incident `warehouse/sql.py` exists to prevent, pinned.

    `current_date` is a MySQL function *and* a column of `ootp_truth_real.leagues`. Bare, the
    function wins and the query returns the wall-clock date; backticked, it returns the
    league's. A provenance check written the obvious way would compare the sim date against
    today's, fail, and send the next reader hunting a parser bug that does not exist.

    This asserts the two readings **differ**, so the hazard is demonstrated rather than
    described, and that the quoted one is the sim date.
    """
    # The ONE place in this module that writes a bare identifier on purpose: demonstrating
    # the collision requires the unquoted form. Every other query here routes through
    # `quote_ident`, exactly as `validate/export_diff.py` does.
    with truth.cursor() as cursor:
        cursor.execute(
            f"SELECT current_date AS unquoted, {quote_ident('current_date')} AS quoted "
            f"FROM {quote_ident('leagues')} "
            f"WHERE {quote_ident('league_id')} = ("
            f"  SELECT {quote_ident('league_id')} FROM {quote_ident('teams')} "
            f"  WHERE {quote_ident('human_team')} = 1)"
        )
        row = cursor.fetchone()

    assert row is not None
    assert str(row["quoted"]) == TRUTH_SAVE_SIM_DATE
    assert str(row["unquoted"]) != str(row["quoted"]), (
        "the bare and backticked readings agree, so this machine cannot demonstrate the "
        "collision — which means the guard in warehouse/sql.py is untested here, not that "
        "it is unnecessary"
    )


def test_the_public_entry_point_asserts_provenance_itself(
    warehouse: Connection[DictCursor],
    truth: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> None:
    """`diff_snapshot` refuses a mismatched universe — not the test file's ordering.

    Until the acceptance panel caught it, "provenance before any value comparison" held only
    because `test_provenance_is_asserted_before_anything_is_compared` sits above the
    report-consuming tests in this file. Anything else calling `diff_snapshot` — and the
    handoff hands Phase 10's render gate exactly that instruction — got no check at all.

    Driven through the entry point with a deliberately wrong human club, so what is under
    test is the caller's guarantee rather than `check_provenance`'s own behaviour.
    """
    _parsed, run = landed
    with pytest.raises(ProvenanceMismatch):
        diff_snapshot(
            warehouse,
            truth,
            save_id=run.save_id,
            sim_date=run.sim_date,
            ingest_seq=run.ingest_seq,
            human_team_id=TRUTH_SAVE_HUMAN_TEAM_ID + 1,
        )


# ── AC6 itself ───────────────────────────────────────────────────────────────


def test_the_differential_is_clean_over_every_landed_field(report: DiffReport) -> None:
    """AC6. Zero row-count and zero value differences over the landed field set.

    Every failure is listed **per field by name** with its key. There is no pass rate in
    this output and there must never be one: 99.99% looks like rounding and is 1,800 wrong
    players.
    """
    failures = report.failures()
    assert not failures, (
        f"{len(failures)} fields disagree with the export:\n"
        + "\n".join(failures)
        + "\n\nFull run:\n"
        + report.describe()
    )


def test_every_declared_population_was_actually_compared(report: DiffReport) -> None:
    """The anti-narrowing guard: a clean run over nothing is not a clean run.

    Pinned counts rather than "whatever came back", because a comparison that derives its
    own expected size from the data it compares cannot notice that it compared nothing —
    and a `WHERE` clause quietly added to a fetch would otherwise turn AC6 green by
    shrinking it.
    """
    compared = {table.table: table for table in report.tables}

    assert compared["bronze_team"].theirs_rows == EXPORT_TEAMS
    assert compared["bronze_team"].compared_rows == EXPORT_TEAMS

    assert compared["bronze_player"].theirs_rows == EXPORT_ACTIVE_PLAYERS
    assert compared["bronze_player"].compared_rows == EXPORT_ACTIVE_PLAYERS
    assert compared["bronze_player"].ours_rows == EXPORT_ACTIVE_PLAYERS + PARSED_ONLY_PLAYERS

    assert compared["bronze_team_roster"].ours_rows == EXPORT_ROSTER_ROWS
    assert compared["bronze_team_roster"].theirs_rows == EXPORT_ROSTER_ROWS

    assert compared["bronze_league_event"].ours_rows == EXPORT_CALENDAR_EVENTS
    assert compared["bronze_league_event"].theirs_rows == EXPORT_CALENDAR_EVENTS

    assert compared["bronze_division_team"].ours_rows == DIVISION_MEMBERSHIPS


def test_every_absence_rule_fired_on_exactly_its_declared_population(
    report: DiffReport,
) -> None:
    """The allowlist is a set of measurements, not a mute button.

    Each rule declares how many rows it may suppress. `compare_keyed` and `compare_rows`
    already fail when a count moves, so this asserts the complementary thing: that every
    rule fired **at all**. A rule matching zero rows is either a fact that stopped being
    true or an exception nobody needed, and both should be noticed rather than carried.
    """
    by_column = {
        (table.table, column.column): column.allowed
        for table in report.tables
        for column in table.columns
    }
    for rule in ABSENCE_RULES:
        if rule.column is None:
            continue
        allowed = by_column.get((rule.table, rule.column))
        assert allowed == rule.population, (
            f"the rule on {rule.table}.{rule.column} suppressed {allowed} rows against its "
            f"declared {rule.population}"
        )

    assert not [fault for table in report.tables for fault in table.rule_faults]


# ── the three expected disagreements, each corroborated independently ────────


def test_the_negated_league_ids_are_exactly_the_unrostered_players(
    truth: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The strongest single result in this phase, and it is a triangulation.

    The export marks a player who is assigned to a club but on no roster list by **negating
    `league_id`**. The save does not: it stores the magnitude, and records the same fact in
    a roster-status byte that `parser/rosters.py` reads out of a different file region
    entirely and surfaces as `RostersFile.unrostered`.

    Two encodings, derived from two independent readings, and this asserts they name the
    **same 176 players** — not the same count, the same set. A count could coincide; a set
    of 176 arbitrary ids could not. It is also what licenses the `magnitude` comparison, so
    the tolerance rests on evidence rather than on convenience.
    """
    parsed, _run = landed

    with truth.cursor() as cursor:
        cursor.execute(
            f"SELECT {quote_ident('player_id')} FROM {quote_ident('players')} "
            f"WHERE {quote_ident('retired')} = 0 AND {quote_ident('league_id')} < 0"
        )
        negated = {int(row["player_id"]) for row in cursor.fetchall()}

    unrostered = {player_id for _team_id, player_id in parsed.rosters.unrostered}

    assert len(negated) == NEGATED_LEAGUE_ROWS
    assert negated == unrostered, (
        f"the export negates league_id on {len(negated)} players and the roster walk calls "
        f"{len(unrostered)} unrostered, and the sets differ by "
        f"{sorted(negated ^ unrostered)[:10]}. These are two readings of one fact from two "
        "different regions of the save; if they disagree, one of them is wrong"
    )

    with truth.cursor() as cursor:
        cursor.execute(
            f"SELECT DISTINCT {quote_ident('player_id')} FROM {quote_ident('team_roster')}"
        )
        rostered = {int(row["player_id"]) for row in cursor.fetchall()}
    assert not (negated & rostered), (
        "a player the export marks unrostered appears in its own team_roster table, so the "
        "reading of the negation is wrong"
    )


def test_the_five_extra_records_are_carried_by_the_export_in_no_form_at_all(
    truth: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """Risk 11, which fired: the file's count is right and the export's is not the same thing.

    They are **not** retired players filtered out by the `retired = 0` predicate — the
    export has no row for them under any predicate. Asserted against the unfiltered table,
    because "absent from the active population" and "absent from the export" are different
    claims and only the second one is true.

    **Pinned by identity, not by count.** A count of five passes for a walk that lost five
    real players and invented five garbage records — a mis-framing that shifts identity need
    not drop a row. The ids are already recorded publicly in `docs/data-access.md`, so
    naming them here costs nothing.
    """
    parsed, _run = landed
    parsed_ids = {player.player_id for player in parsed.players.players}

    with truth.cursor() as cursor:
        cursor.execute(f"SELECT {quote_ident('player_id')} FROM {quote_ident('players')}")
        every_export_id = {int(row["player_id"]) for row in cursor.fetchall()}

    extras = sorted(parsed_ids - every_export_id)
    assert extras == sorted(PARSED_ONLY_PLAYER_IDS), (
        f"the walk frames {len(extras)} records the export has never heard of — {extras[:10]} "
        f"— against the pinned {sorted(PARSED_ONLY_PLAYER_IDS)}. The identity matters as much "
        "as the count: five lost players and five invented records also total five"
    )
    assert len(extras) == PARSED_ONLY_PLAYERS

    # Every one is unassigned. That does not explain them, and is not offered as an
    # explanation — it is pinned so a later change in what they are gets noticed.
    by_id = {player.player_id: player for player in parsed.players.players}
    assert all(by_id[player_id].team_id == 0 for player_id in extras)


def test_the_null_cities_are_the_all_star_sides_and_nothing_else(
    truth: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The city rule's premise, checked rather than assumed.

    The rule allows a NULL city only where the export's `name` equals its `nickname`. That
    is a proxy for "this is a generic all-star side", and this asserts the proxy holds: the
    NULL-city set is exactly the set of clubs the export flags `allstar_team` *and* names
    after their nickname. The four all-star sides with real names — the two league squads
    and the two Future Stars sides — carry a city and are compared normally.
    """
    parsed, _run = landed
    null_city = {team.team_id for team in parsed.teams.teams if team.city is None}

    with truth.cursor() as cursor:
        # `name` is a MySQL keyword; quoted like every other identifier here, for the reason
        # the `current_date` test above demonstrates on this very export.
        cursor.execute(
            f"SELECT {column_list(('team_id', 'name', 'nickname', 'allstar_team'))} "
            f"FROM {quote_ident('teams')}"
        )
        rows = {int(row["team_id"]): row for row in cursor.fetchall()}

    assert null_city == {
        team_id
        for team_id, row in rows.items()
        if int(row["allstar_team"]) == 1 and row["name"] == row["nickname"]
    }
    assert all(int(rows[team_id]["allstar_team"]) == 1 for team_id in null_city)
    assert all(rows[team_id]["name"] for team_id in null_city), (
        "the export writes an empty name somewhere, so it is passing absence through "
        "rather than filling it, and the rule's reasoning is wrong"
    )


# ── the guard, seen to fail ──────────────────────────────────────────────────


def test_a_corrupted_field_is_named_by_the_harness_rather_than_averaged_away(
    warehouse: Connection[DictCursor],
    truth: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> None:
    """§4.4's Phase 9 row, against the real landed rows: corrupt one field, be named.

    A differential harness never seen to fail informatively is not yet a harness. This
    falsifies **one column of one real club** after the rows are read and before they are
    compared — the same values, through the same comparison, as a genuine parser fault would
    produce — and requires the output to identify the column, the row and both values, and
    to carry no aggregate.

    Done here rather than by editing the parser so it runs on every invocation instead of
    once, by hand, in a phase nobody will repeat.
    """
    _parsed, run = landed
    from ootp_ai.validate.export_diff import _fetch_export_keyed, _fetch_keyed

    ours = dict(
        _fetch_keyed(
            warehouse,
            table=_TEAM_SPEC.table,
            key=_TEAM_SPEC.key,
            columns=_TEAM_SPEC.compared_columns,
            save_id=run.save_id,
            sim_date=run.sim_date,
            ingest_seq=run.ingest_seq,
        )
    )
    theirs = _fetch_export_keyed(truth, _TEAM_SPEC)

    victim = sorted(set(ours) & set(theirs))[0]
    corrupted = dict(ours[victim])
    corrupted["abbr"] = "ZZZ"
    ours[victim] = corrupted

    lines = DiffReport(tables=(compare_keyed(ours, theirs, _TEAM_SPEC),)).failures()

    assert len(lines) == 1, "expected one named field, got:\n" + "\n".join(lines)
    assert "bronze_team.abbr" in lines[0]
    assert f"team_id={victim}" in lines[0]
    assert "ZZZ" in lines[0]
    assert "%" not in lines[0]


def test_the_skip_path_names_its_reason(settings: Settings) -> None:
    """A vacuous green on AC6 would be worse than a red one, so the skip is exercised.

    With the truth database unset, opening the export must raise an `ootp_ai` `ConfigError`
    naming the key — which is what the `truth` fixture turns into a skip. A pass here would
    report AC6 green having compared nothing.
    """
    blinded = Settings(
        install=settings.install,
        saved_games=settings.saved_games,
        managed=settings.managed,
        truth_save=settings.truth_save,
        probe_save=settings.probe_save,
        snapshot_root=settings.snapshot_root,
        output_root=settings.output_root,
        mysql=type(settings.mysql)(
            host=settings.mysql.host,
            port=settings.mysql.port,
            user=settings.mysql.user,
            password=settings.mysql.password,
            database=settings.mysql.database,
            truth_database=None,
        ),
    )

    with pytest.raises(ConfigError) as caught:
        connect_truth(blinded)
    assert "MYSQL_TRUTH_REAL_DATABASE" in str(caught.value), (
        "the refusal does not name what is missing, so a reader of a green-with-skips run "
        "cannot tell which answer key was absent"
    )


def test_the_run_is_reported_in_full_including_the_columns_that_agreed(
    report: DiffReport,
) -> None:
    """`describe()` is what a handoff quotes, so it must show the whole comparison.

    A report that printed only failures would make a clean run indistinguishable from a run
    that compared nothing — which is the same vacuity the pinned populations guard against,
    seen from the output side.

    **Every spec, not just the keyed two.** The row specs emitted no per-column output at
    all until the acceptance panel caught it, so a clean `bronze_league_event` line was
    indistinguishable from one whose eight columns had never been in scope — and this loop
    iterated only `SPECS`, so it could not have noticed.
    """
    text = report.describe()
    for spec in SPECS:
        assert spec.table in text
        for pair in spec.columns:
            assert f"{pair.column} vs {pair.export}" in text
    for row_spec in (*ROW_SPECS, DIVISION_SPEC):
        assert row_spec.table in text
        for column, export in zip(row_spec.columns, row_spec.export_columns, strict=True):
            assert f"{column} vs {export}" in text
    assert "compared" in text
    # The four suppressed all-star sides are stated rather than left as 34 minus 30.
    assert "allowed by an absence rule" in text


def test_nothing_here_reaches_a_rating_table(report: DiffReport) -> None:
    """Tier B's limit, asserted at the run level as well as at the spec level.

    `tests/test_export_diff.py` proves no *declared field* the harness compares is a rating.
    This proves the complementary thing about the run that actually happened: the tables it
    touched are the **five** bronze tables this harness reaches, and none of the export's
    rating tables appears in it.

    `bronze_name` is the sixth and is deliberately not here: the export has no string table,
    and its values are validated through `players.first_name` / `.last_name` by AC7's
    `tests/test_names_join.py` — a different criterion in a different module.
    """
    touched = {table.table for table in report.tables}
    assert touched == {
        "bronze_team",
        "bronze_player",
        "bronze_team_roster",
        "bronze_league_event",
        "bronze_division_team",
    }
    assert not any("rating" in name or "batting" in name for name in touched)


def test_the_calendar_key_is_validated_by_count_alone_and_the_limit_is_stated(
    truth: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """`bronze_league_event.seq` has no oracle, so its ORDER is unproven. Say so.

    The export does not expose `seq` — which is precisely why the key had to be settled from
    the bytes — so a walk that emitted the same 3,058 events in a permuted order passes AC6
    unchanged. That is a real limit of Tier B here, and the cheap structural check available
    without an oracle is that the walk agrees with itself: `seq` is contiguous from its
    minimum across one snapshot, so a walk that skipped or repeated one would be caught even
    though a reordering would not.
    """
    parsed, _run = landed
    sequences = sorted(event.seq for event in parsed.world.calendar)

    assert len(sequences) == EXPORT_CALENDAR_EVENTS
    assert len(set(sequences)) == len(sequences), "seq repeats, and it is a primary-key column"
    assert sequences == list(range(sequences[0], sequences[0] + len(sequences))), (
        "seq is not contiguous, so the walk either skipped an event or invented one — the "
        "only self-consistency the export can never check, because it does not carry seq"
    )


def test_no_landed_calendar_event_carries_a_null_start_date(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The nullable path exists for a measured reason and is measured to be empty here.

    `bronze_league_event.start_date` was made nullable in Phase 8b because `parser/world.py`
    accepts `year == 0` on purpose — structural absence, not a mis-frame — and a date-less
    event aborted a 300,000-row landing. On every save on disk, zero rows take that path.

    Pinned rather than left silent so the uncovered branch is a **stated fact** rather than
    an absence of evidence. If one ever appears, this goes red and somebody decides whether
    the export's own row for it needs a named absence rule; today there is nothing to name.
    """
    _parsed, run = landed
    with warehouse.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS n FROM {quote_ident('bronze_league_event')} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s "
            f"AND {quote_ident('start_date')} IS NULL",
            (run.save_id, str(run.sim_date), run.ingest_seq),
        )
        row = cursor.fetchone()

    assert row is not None
    assert int(row["n"]) == 0, (
        f"{row['n']} landed calendar events carry a NULL start_date. The path is legitimate "
        "and untested; if it is now reachable, the differential needs a named absence rule "
        "for whatever the export writes in its place"
    )
