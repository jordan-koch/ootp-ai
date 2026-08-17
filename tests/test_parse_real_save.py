"""AC9 — the walker against the real saves, including the one with no answer key.

Two universes are checked here and they are checked differently, on purpose.

The **standard-mode probe** has an export, so every claim can be made against a source
that is not this parser: 259 teams, the human club, the hierarchy. That is the whole
reason a disposable standard save was created and retained (ADR 0003 — Challenge Mode
has no export).

**`OOTP-AI.lg` has no export at all**, and it is the league that actually matters. So the
checks that survive there are the structural ones: the top league's shape, a unique id
per team, and a human club resolved from data rather than from a constant. The plan's
§2.5 names the failure this guards — *code that hardcodes "we are team 6" passes on every
save the parser is developed against and breaks invisibly on ours*, and since the
validation harness runs against the probe, nothing else in the suite would ever catch it.

**Three files independently answer "which club do we manage", and all three are checked.**
`human_managers.dat` names it outright in 835 bytes. `teams.dat` reaches it through the
last slot of a variable-length integer run. `saved_games.dat` carries the club's full
name — `'Boston Red Sox'`, `'Chicago Cubs'` — which corroborates but is still not a join
key, because joining on a display name across two universes is what `team_id` exists to
avoid. None of the three carried a usable id in Phase 4, which is why it left the
question red rather than guessing.

**What this file cannot assert, and why.** `division_id` and `allstar_team` are not in
`teams.dat` — measured, 0 of 140 and 0 of 30 on their own discriminating subsets — so
the 30-club count and the division hierarchy come from `world.dat` in Phase 5b. The
standings region is not in `teams.dat` either. Nothing here fakes them from a field that
does not exist.

`gamedata`: needs the saves, and the export half needs MySQL. Excluded from CI.

This module grows: Phase 5b tightens the top-league count from 34 to 30, Phase 6 adds the
player and roster clauses, and Phase 7 adds AC9's display-name clause, which cannot pass
before the `names.dat` join exists.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.db import connect_truth
from ootp_ai.parser.human_managers import HUMAN_MANAGERS_FILE, read_human_manager
from ootp_ai.parser.saved_games import SAVED_GAMES_FILE, read_saved_games
from ootp_ai.parser.teams import TEAMS_FILE, TeamRecord, TeamsFile, read_teams

pytestmark = pytest.mark.gamedata

#: The 30 clubs of the top league, `measured` 2026-08-16 from the export's
#: `league_id = 203, allstar_team = 0` set. Real-baseball abbreviations, not OOTP's
#: shipped data — the seeded universe renders the same 30 franchises in both saves.
#: `test_the_expected_abbreviations_match_the_export` re-derives this from the
#: warehouse whenever MySQL is up, so the constant cannot drift unnoticed.
MLB_ABBREVIATIONS = frozenset(
    {
        "AZ", "ATL", "BAL", "BOS", "CWS", "CHC", "CIN", "CLE", "COL", "DET",
        "MIA", "HOU", "KC", "LAA", "LAD", "MIL", "MIN", "NYY", "NYM", "OAK",
        "PHI", "PIT", "SD", "SEA", "SF", "STL", "TB", "TEX", "TOR", "WSH",
    }
)  # fmt: skip

#: `measured` — the export gives Boston `team_id` 4, and `OOTP-AI.lg`'s own mail
#: independently renders the club as the token `<Boston:team#4>`. Two sources, one
#: number, in two different universes.
BOSTON_TEAM_ID = 4
BOSTON_SIGNATURE = ("Boston", "BOS", "Red Sox")

#: The top league's own level. Everything above 1 is an affiliate or a complex side.
TOP_LEVEL = 1


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings: {exc}")


def _walk(save: SaveRef) -> TeamsFile:
    path = save.path / TEAMS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {TEAMS_FILE}")
    return read_teams(path.read_bytes())


def _human_club(parsed: TeamsFile) -> TeamRecord:
    """The one club the flag points at, or a failure naming what it found instead."""
    flagged = [team for team in parsed.teams if team.human_team]
    assert len(flagged) == 1, (
        f"{len(flagged)} clubs carry the human flag: "
        f"{[(t.team_id, t.city) for t in flagged]}. Exactly one club is managed in each "
        "of these saves, so a count other than one means the flag is not the flag."
    )
    return flagged[0]


def _top_league(parsed: TeamsFile) -> list[TeamRecord]:
    """Every level-1 record in the human club's own league — **34, not 30**.

    `league_id` 203 is the top league in the export, but `OOTP-AI.lg` was created
    separately and nothing has checked that its ids match. Anchoring on the human club
    keeps this working in a universe nobody has an export for.

    The four All-Star sides cannot be separated out here, and that is not an oversight:
    `allstar_team` is **not in `teams.dat`** — appending it to the integer model scores
    0 of 30 on the All-Star sides themselves. The 30-club assertion therefore needs
    `world.dat`'s division arrays, where the All-Star sides appear in none, and it
    lands in Phase 5b rather than being faked here from a field that does not exist.
    """
    home = _human_club(parsed)
    return [
        team
        for team in parsed.teams
        if team.league_id == home.league_id and team.level == TOP_LEVEL
    ]


@contextmanager
def _truth_cursor(settings: Settings) -> Iterator[Any]:
    """The export, or a loud skip. A silent pass here would be worse than a red."""
    try:
        connection = connect_truth(settings)
    except ConfigError as exc:
        pytest.skip(f"ground truth unavailable: {exc}")
    except Exception as exc:
        # Any driver failure is a skip with a named reason, never a quiet pass.
        pytest.skip(f"cannot reach the ground-truth schema: {type(exc).__name__}: {exc}")
    try:
        with connection.cursor() as cursor:
            yield cursor
    finally:
        connection.close()


# ── the league we actually manage ────────────────────────────────────────────


def test_the_managed_leagues_top_level_is_thirty_clubs_plus_four_all_star_sides() -> None:
    """AC9's headline clause, at the strength `teams.dat` alone can actually support.

    34 = the 30 franchises plus the AL/NL All-Star and Future Stars squads. Asserting
    30 here would require `allstar_team`, which this file does not carry, so the honest
    form is 34 with the four named — and Phase 5b tightens it to 30 once `world.dat`'s
    division arrays are readable.
    """
    clubs = _top_league(_walk(_settings().managed))
    assert len(clubs) == 34, (
        f"{len(clubs)} records at top level, expected 34 (30 clubs + 4 All-Star sides): "
        f"{sorted(team.abbr for team in clubs)}"
    )


def test_the_managed_league_renders_the_thirty_abbreviations_of_real_baseball() -> None:
    """Content, not just cardinality. Thirty-four wrong strings also count to 34.

    Stated as a superset rather than equality, because the four All-Star sides are in
    this list and are not franchises. Equality returns in Phase 5b.
    """
    clubs = _top_league(_walk(_settings().managed))
    abbrs = {team.abbr for team in clubs}

    missing = MLB_ABBREVIATIONS - abbrs
    assert not missing, f"top league is missing real clubs: {sorted(missing)}"

    # Measured: the four All-Star sides share two abbreviations between them — the
    # All-Star and Future Stars squads of each sub-league both render `AL` / `NL`. So
    # the set difference is 2 while the record count is 4, and asserting the set size
    # was 4 was simply wrong about the data.
    assert abbrs - MLB_ABBREVIATIONS == {"AL", "NL"}, (
        f"unexpected non-franchise abbreviations: {sorted(abbrs - MLB_ABBREVIATIONS)}"
    )
    assert sum(1 for team in clubs if team.abbr in {"AL", "NL"}) == 4, (
        "expected 4 All-Star records (All-Star and Future Stars, per sub-league)"
    )


def test_the_club_we_manage_is_boston_resolved_from_a_flag() -> None:
    """The assertion Phase 4 left red, and the reason Phase 5 exists at all.

    `saved_games.dat` names the club and carries no id (`parser/saved_games.py` records
    what was enumerated). The id is here, on the team record.
    """
    home = _human_club(_walk(_settings().managed))
    assert (home.city, home.abbr, home.nickname) == BOSTON_SIGNATURE
    assert home.team_id == BOSTON_TEAM_ID, (
        f"the human club is team {home.team_id}; both the export and this league's own "
        f"mail put Boston at {BOSTON_TEAM_ID}"
    )


def test_boston_carries_the_full_five_string_signature() -> None:
    """`docs/data-access.md` records the 5-string signature `verified`; spend it."""
    parsed = _walk(_settings().managed)
    boston = next(team for team in parsed.teams if team.team_id == BOSTON_TEAM_ID)

    assert (boston.city, boston.abbr, boston.nickname) == BOSTON_SIGNATURE
    assert boston.logo_filename == "boston_red_sox.png"
    assert boston.full_name and boston.full_name != boston.city, (
        f"the fifth signature string is {boston.full_name!r} — it should be the club's "
        "full name, which is not the same string as the city"
    )
    assert boston.historical_id == "BOS"


# ── properties every save must have ──────────────────────────────────────────


def _all_saves(settings: Settings) -> list[tuple[str, TeamsFile]]:
    present = [ref for ref in (settings.managed, settings.probe_save, settings.truth_save) if ref]
    return [(ref.league, _walk(ref)) for ref in present]


def test_team_ids_are_unique_within_a_save() -> None:
    """The bronze key's whole premise. A duplicate silently merges two clubs."""
    for league, parsed in _all_saves(_settings()):
        ids = [team.team_id for team in parsed.teams]
        duplicates = sorted({team_id for team_id in ids if ids.count(team_id) > 1})
        assert not duplicates, f"{league}: team_id repeats for {duplicates}"


def test_no_team_id_is_zero() -> None:
    """Measured: ids run 1..259 in the export, so 0 is free to mean "no team".

    That is what makes `parent_team_id = 0` readable as "no parent" downstream — but
    only in silver. Bronze lands the zero it was given.
    """
    for league, parsed in _all_saves(_settings()):
        assert all(team.team_id > 0 for team in parsed.teams), f"{league}: a team_id is 0"


def test_a_zero_sub_league_is_the_american_league_and_survives_the_walk() -> None:
    """The structural-absence trap, in the direction that actually bites here.

    Measured: 242 of 259 teams carry `sub_league_id` 0 and 119 carry `division_id` 0.
    Boston is one of them — AL East is (0, 0). A walker that mapped zero to `None`
    somewhere between the bytes and the dataclass would delete half of baseball and
    still return 30 clubs.
    """
    for league, parsed in _all_saves(_settings()):
        clubs = _top_league(parsed)
        assert any(team.sub_league_id == 0 for team in clubs), (
            f"{league}: no top-level club has sub_league_id 0 — the American League "
            "has gone missing, which is what a zero-to-None conversion looks like"
        )
        assert any(team.sub_league_id == 1 for team in clubs), f"{league}: no National League"


def test_top_level_clubs_have_no_parent_and_affiliates_do() -> None:
    """`parent_team_id` is what makes an affiliate distinguishable from a club.

    Measured: all 34 level-1 rows carry 0, and of the 225 rows below it, 199 carry a
    real parent while 26 are genuinely independent sides. So the assertion is
    one-directional — every top-level club is parentless, and *most* affiliates are not.
    """
    for league, parsed in _all_saves(_settings()):
        assert all(team.parent_team_id == 0 for team in _top_league(parsed)), (
            f"{league}: a top-level club claims a parent team"
        )
        affiliates = [team for team in parsed.teams if team.level > TOP_LEVEL]
        assert affiliates, f"{league}: no teams below the top level at all"
        parented = sum(1 for team in affiliates if team.parent_team_id != 0)
        assert parented > len(affiliates) / 2, (
            f"{league}: only {parented} of {len(affiliates)} lower-level teams have a "
            "parent — the field is probably not parent_team_id"
        )


def test_no_team_string_carries_a_machine_path() -> None:
    """This repo is public and team strings reach rendered reports (ADR 0006).

    `logo_filename` is the one field here shaped like a path. It should be a bare asset
    name; if an install ever writes an absolute one, it must fail here rather than in a
    committed catalog.
    """
    settings = _settings()
    roots = (str(settings.saved_games), str(settings.install))
    for league, parsed in _all_saves(settings):
        for team in parsed.teams:
            # Absent strings are skipped rather than coerced: `city` is missing on 26
            # records and `logo_filename` on 289 of the managed league's, and checking
            # the literal "None" would be checking nothing.
            candidates = (team.abbr, team.nickname, team.full_name, team.city, team.logo_filename)
            for value in (v for v in candidates if v is not None):
                assert not any(root in value for root in roots), f"{league}: {value!r}"
                assert ":" not in value and "\\" not in value, f"{league}: {value!r}"


# ── the two files have to agree about who we are ─────────────────────────────


def test_the_index_and_the_team_flag_name_the_same_club() -> None:
    """The cross-check `human_team_name` was added for.

    **Measured 2026-08-16, correcting an earlier assumption in this module:** the index
    carries the club's **full name** — `'Boston Red Sox'`, `'Chicago Cubs'` — not its
    city. An earlier draft compared against `city` and argued the index could not
    identify the club because "Chicago" names two of them. That argument was about a
    string the file does not contain; `'Chicago Cubs'` is unambiguous.

    So this is a stronger check than it was written to be: two files independently
    identify the same club. It is still **not a join key** — joining on a display name
    across two universes is exactly what `team_id` exists to avoid — but as a
    corroboration it now stands on its own.
    """
    settings = _settings()
    for ref in (settings.managed, settings.probe_save, settings.truth_save):
        if ref is None:
            continue
        index = ref.root / SAVED_GAMES_FILE
        if not index.is_file():
            pytest.skip(f"no {SAVED_GAMES_FILE} beside {ref.league}")

        listed = {entry.league: entry for entry in read_saved_games(index.read_bytes())}
        entry = listed.get(ref.league)
        assert entry is not None, f"{SAVED_GAMES_FILE} does not list {ref.league}"

        home = _human_club(_walk(ref))
        assert entry.human_team_name == home.full_name, (
            f"{ref.league}: the index says the human club is "
            f"{entry.human_team_name!r} but teams.dat flags {home.full_name!r} "
            f"(team {home.team_id}). One of the two walks is in the wrong place."
        )


def test_the_three_saves_do_not_all_resolve_to_the_same_club() -> None:
    """The anti-hardcoding control, now against the id rather than the display name.

    Boston, Boston, Chicago — so a single value across all three means the resolution is
    constant somewhere. Phase 4 could only run this on names; it runs on ids now, which
    is the form that matters, because the id is what every downstream row is keyed on.
    """
    settings = _settings()
    if settings.probe_save is None or settings.truth_save is None:
        pytest.skip("both validation saves are needed — a two-Boston sample proves nothing")

    saves = (settings.managed, settings.probe_save, settings.truth_save)
    ids = [_human_club(_walk(ref)).team_id for ref in saves]
    assert len(set(ids)) > 1, (
        f"all three saves resolve to team {ids[0]}; the managed league and the Challenge "
        "probe are Boston and the standard probe is the Chicago Cubs"
    )
    assert ids[0] == ids[1] != ids[2], (
        f"expected Boston, Boston, Chicago and got team ids {ids} — the two Challenge "
        "saves are both managed by Boston, so a three-way split is as wrong as none"
    )


# ── against the export ───────────────────────────────────────────────────────


def test_the_expected_abbreviations_match_the_export() -> None:
    """Keeps the hardcoded constant above from drifting away from the answer key."""
    settings = _settings()
    with _truth_cursor(settings) as cursor:
        cursor.execute(
            "SELECT abbr FROM teams WHERE level = %s AND allstar_team = 0 "
            "AND league_id = (SELECT league_id FROM teams WHERE human_team <> 0 LIMIT 1)",
            (TOP_LEVEL,),
        )
        assert {row["abbr"] for row in cursor.fetchall()} == MLB_ABBREVIATIONS


def test_every_parsed_team_matches_the_export_field_by_field() -> None:
    """The probe's whole point: 259 rows compared against a source we did not write.

    Per-field and per-team, never an aggregate pass rate — a 98% match is 5 wrong clubs,
    and which 5 is the only useful part of the answer.
    """
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("OOTP_TRUTH_LEAGUE is unset — the export describes that save only")

    parsed = {team.team_id: team for team in _walk(settings.truth_save).teams}
    with _truth_cursor(settings) as cursor:
        cursor.execute(
            "SELECT team_id, name, abbr, nickname, logo_file_name, level, league_id, "
            "sub_league_id, city_id, park_id, nation_id, parent_team_id, human_team "
            "FROM teams ORDER BY team_id"
        )
        expected = cursor.fetchall()

    assert {row["team_id"] for row in expected} == set(parsed), (
        "the parsed team ids differ from the export's — "
        f"missing {sorted({r['team_id'] for r in expected} - set(parsed))}, "
        f"extra {sorted(set(parsed) - {r['team_id'] for r in expected})}"
    )

    mismatches: list[str] = []
    for row in expected:
        team = parsed[row["team_id"]]
        actual = (
            team.abbr,
            team.nickname,
            team.logo_filename,
            team.level,
            team.league_id,
            team.sub_league_id,
            team.city_id,
            team.park_id,
            team.nation_id,
            team.parent_team_id,
            team.human_team,
        )
        wanted = (
            row["abbr"],
            row["nickname"],
            row["logo_file_name"],
            row["level"],
            row["league_id"],
            row["sub_league_id"],
            row["city_id"],
            row["park_id"],
            row["nation_id"],
            row["parent_team_id"],
            bool(row["human_team"]),
        )
        if actual != wanted:
            mismatches.append(f"  team {row['team_id']}: parsed {actual} != export {wanted}")

        # `city` is compared separately: 26 records carry no city string, and the
        # export renders that absence as the club's display name rather than as NULL.
        # Comparing them directly would fail on a correct parse.
        if team.city is not None and team.city != row["name"]:
            mismatches.append(f"  team {row['team_id']}: city {team.city!r} != {row['name']!r}")

    assert not mismatches, "teams disagree with the export:\n" + "\n".join(mismatches)


def test_exactly_the_minor_league_all_star_sides_carry_no_city_string() -> None:
    """26 of 259, measured — and the count is what makes this more than a shrug.

    A walk that silently dropped a string on some *other* record would still produce
    `None`s; pinning both the number and which clubs they are turns a soft observation
    into something that fails when the walk drifts.
    """
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("OOTP_TRUTH_LEAGUE is unset — the export names the All-Star sides")

    parsed = {team.team_id: team for team in _walk(settings.truth_save).teams}
    cityless = {tid for tid, team in parsed.items() if team.city is None}

    with _truth_cursor(settings) as cursor:
        cursor.execute("SELECT team_id FROM teams WHERE allstar_team <> 0 AND league_id <> 203")
        minor_all_stars = {row["team_id"] for row in cursor.fetchall()}

    assert len(cityless) == 26, f"{len(cityless)} records carry no city, expected 26"
    assert cityless == minor_all_stars, (
        f"the city-less records are not the minor-league All-Star sides: "
        f"unexpected {sorted(cityless - minor_all_stars)}, "
        f"missing {sorted(minor_all_stars - cityless)}"
    )


# ── two files, one club, and neither is allowed to be trusted alone ──────────


def test_the_manager_file_and_the_team_flag_name_the_same_club() -> None:
    """The cheap pre-registered cross-check, and the reason both walks exist.

    `human_managers.dat` is 835 bytes and names the club directly — measured, the only
    offsets holding each save's own `team_id` across all three are 231/235/239, and the
    same intersection at ±1/+2/+10/+100 is empty. `teams.dat` reaches the same answer by
    a completely different route: the last slot of a variable-length integer run whose
    fields are omitted when zero.

    Two independent derivations of one fact is worth far more than either. The 835-byte
    file is the one to trust if they ever disagree — it is small enough to account for
    completely, while the teams run still has 18 field orders that fit equally well.
    """
    settings = _settings()
    for ref in (settings.managed, settings.probe_save, settings.truth_save):
        if ref is None:
            continue
        flagged = _human_club(_walk(ref)).team_id
        named = read_human_manager((ref.path / HUMAN_MANAGERS_FILE).read_bytes()).team_id
        assert flagged == named, (
            f"{ref.league}: teams.dat flags team {flagged} as human but "
            f"{HUMAN_MANAGERS_FILE} names team {named}. These are two unrelated walks "
            "of two unrelated files, so a disagreement means one of them is wrong — "
            "and every downstream row is keyed on the answer."
        )


def test_the_manager_file_alone_produces_boston_boston_chicago() -> None:
    """The anti-hardcoding control, restated against the simpler of the two sources.

    Measured 2026-08-16: 4, 4, 6. This is the triple Phase 4 hunted through
    `saved_games.dat` and could not find, and it turned out to be sitting in an
    835-byte file nobody had opened.
    """
    settings = _settings()
    if settings.probe_save is None or settings.truth_save is None:
        pytest.skip("both validation saves are needed — a two-Boston sample proves nothing")

    ids = [
        read_human_manager((ref.path / HUMAN_MANAGERS_FILE).read_bytes()).team_id
        for ref in (settings.managed, settings.probe_save, settings.truth_save)
    ]
    assert ids[0] == ids[1] != ids[2], f"expected Boston, Boston, Chicago and got team ids {ids}"
    assert ids[0] == BOSTON_TEAM_ID
