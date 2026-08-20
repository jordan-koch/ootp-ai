"""Tier B — the landed warehouse against the probe save's export, per field by name.

This is the harness that converts the field map's labels from beliefs into findings. Every
prior phase measured its own file against the export by hand, once, in a review document;
this runs the whole comparison on every invocation and names what disagreed.

## What it compares, and what it deliberately cannot

Both sides live in **one MySQL instance** — the landed bronze rows in the warehouse schema,
the export in `ootp_truth_real` — which is ADR 0004's stated rationale for choosing MySQL
at all: the answer key never has to leave the server to be joined against.

**The comparison itself happens in Python, on decoded values, and that is not an accident.**
`ops/mysql-bootstrap.sql` creates every schema `utf8mb4_0900_ai_ci` — accent- *and*
case-insensitive — so `WHERE ours.abbr = theirs.abbr` would score `Ramírez == Ramirez` as a
match, in a repo whose export was configured with *Replace accents* Off precisely so names
would survive validation. A differential that compares server-side passes hardest on
exactly the rows most likely to be mis-decoded (SD-13, and Phase 7's finding).

**Tier B is exact for what this slice lands and can never be a rating validator.** Ids,
names, dates, roster lists, the team dimension, division membership and the calendar are
byte-for-byte comparable here. Ratings are not: the export writes display scale, and
`players_batting.batting_ratings_overall_contact` carries exactly **12 distinct values
across 20-80**. A bucketed check passes a parser reading the *adjacent* `u16`, which is
CLAUDE.md's named correctness trap in its most dangerous form. `players.csv` (Tier A) stays
the permanent exact rating validator, and nothing in this module should ever be extended to
cover a rating.

## No aggregate, ever

Every disagreement is emitted **per field by name, with its key**. An aggregate pass rate is
how a parser reading the adjacent field ships green: 99.99% looks like rounding and is
1,800 wrong players. `DiffReport.failures()` returns one line per disagreeing field and
never a percentage.

## The absence rules, and why each is bounded

A *correct* parse disagrees with the export in a small number of named places, because the
export cannot represent structural absence: it writes `0`, or `''`, or a filler string,
where the save carries nothing at all. Without a named allowlist those become false
mismatches, and the tempting fix is to make the parser write the filler — which is exactly
the error `.claude/agents/data-engineer.md` warns about, and it converts *incomplete* data
into *wrong* data.

So each rule is a **named column, a reason, a predicate, and an exact population**. The
population is the part that matters: a rule that may suppress any number of rows is a mute
button, and the day a real regression makes 200 cities disagree it would absorb them
silently. Every rule below fires on exactly as many rows as it declares, or the harness
fails naming the rule.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.parser.primitives import SaveDate
from ootp_ai.warehouse.ingest_run import as_sql_date
from ootp_ai.warehouse.sql import column_list, quote_ident

__all__ = [
    "ABSENCE_RULES",
    "DIVISION_EXPORT_CLUBS",
    "DIVISION_LEAGUES",
    "DIVISION_MEMBERSHIPS",
    "DIVISION_SPEC",
    "EXPORT_ACTIVE_PLAYERS",
    "EXPORT_CALENDAR_EVENTS",
    "EXPORT_ROSTER_ROWS",
    "EXPORT_RULE_COLUMNS",
    "EXPORT_TEAMS",
    "PARSED_ONLY_PLAYERS",
    "PARSED_ONLY_PLAYER_IDS",
    "ROW_SPECS",
    "SPECS",
    "TRUTH_SAVE_HUMAN_TEAM_ID",
    "TRUTH_SAVE_HUMAN_TEAM_NICKNAME",
    "TRUTH_SAVE_SIM_DATE",
    "AbsenceRule",
    "ColumnPair",
    "ColumnResult",
    "DiffReport",
    "DuplicateKeys",
    "ProvenanceMismatch",
    "RowSpec",
    "TableResult",
    "TableSpec",
    "argb_hex",
    "check_provenance",
    "compare_keyed",
    "compare_rows",
    "diff_snapshot",
    "exact",
    "magnitude",
]

# ── the universe this harness is allowed to run against ──────────────────────
#
# Asserted before any value is compared. A field diff against a *different* universe is
# noise that looks like a finding: every id would disagree and the output would read as a
# catastrophic parser fault rather than as "you pointed it at the wrong save".

#: The retained standard-mode save's in-game date. Read from the export through a **quoted**
#: identifier — see `check_provenance`, where the reason is a measured incident rather than a
#: style rule.
#:
#: Named for the save's role, not its history. "Probe" is ambiguous in this repo — `.env`
#: carries both `OOTP_PROBE_LEAGUE` (the Challenge-mode twin) and `OOTP_TRUTH_LEAGUE` (this
#: one, the only save with an export), and these constants describe the second.
TRUTH_SAVE_SIM_DATE: Final = "2024-03-18"

#: The club this universe is managed by. Not "Chicago": measured, the export carries two
#: clubs named Chicago (5 White Sox, 6 Cubs), which is the same ambiguity `ingest.py` refuses
#: to resolve `human_team_id` from `saved_games.dat`'s display string over.
TRUTH_SAVE_HUMAN_TEAM_ID: Final = 6
TRUTH_SAVE_HUMAN_TEAM_NICKNAME: Final = "Cubs"

# ── the populations, pinned so a quietly narrowed comparison cannot pass ──────
#
# Every count below is `measured` against `ootp_truth_real` on 2026-08-19. They are pinned
# here rather than read at run time for one reason: a comparison that derives its own
# expected size from the data it is comparing cannot notice that it compared nothing.

EXPORT_TEAMS: Final = 259
EXPORT_ACTIVE_PLAYERS: Final = 18_072
EXPORT_ROSTER_ROWS: Final = 15_672
EXPORT_CALENDAR_EVENTS: Final = 3_058

#: `players.dat` frames **18,077** records; the export's `retired = 0` population is 18,072.
#: Five records exist that the export does not carry in any form — not as retired rows, not
#: at all — measured in Phase 6a and pinned again here. They land (bronze is 1:1 with the
#: walk) and they are excluded from the value comparison because there is nothing to compare
#: them against. Risk 11 of the plan is this number; it fired, and it was the plan's
#: assumption that was wrong rather than the walk.
PARSED_ONLY_PLAYERS: Final = 5

#: And **which** five, because a count is not an identity. A mis-framed walk that shifts
#: identity rather than dropping rows need not lose an id: five real players lost and five
#: garbage records gained still counts to five. These ids are already recorded publicly in
#: `docs/data-access.md`, so pinning them here adds no leak surface the repo has not accepted.
PARSED_ONLY_PLAYER_IDS: Final = (42001, 49008, 50468, 50469, 132324)

#: The reach of the division walk on this save: one league, six divisions, thirty clubs.
#: Pinned as a shape rather than as a league id, because the id is this save's and the shape
#: is the claim — `world.dat`'s other fourteen leagues sit behind their own unmapped scalar
#: blocks (Phase 5b) and are not reached.
DIVISION_LEAGUES: Final = 1
DIVISION_MEMBERSHIPS: Final = 30

#: The export side of the division comparison **before** the absence rule runs: the same
#: league's 34 clubs, four of them all-star sides that sit in no division. Distinct from
#: `DIVISION_MEMBERSHIPS` on purpose — `export_rows` pins what the export returns, and
#: conflating it with our own landed count is how a field named for the export's population
#: ends up carrying ours.
DIVISION_EXPORT_CLUBS: Final = 34

_EXPORT_ACTIVE_PLAYER_FILTER: Final = f"WHERE {quote_ident('retired')} = 0"


class ProvenanceMismatch(Exception):  # noqa: N818
    """The landed snapshot and the export do not describe the same universe.

    Raised *before* any value is compared. Named without the `…Error` suffix to match
    `SnapshotDateMismatch`, which is the same refusal one layer up.
    """


# ── comparison modes ─────────────────────────────────────────────────────────

Compare = Callable[[Any, Any], bool]


def exact(ours: Any, theirs: Any) -> bool:
    """Equality on decoded values, accent- and case-sensitive.

    Integers are normalised across the two column widths (our `TINYINT UNSIGNED` against
    the export's `smallint`, say) and nothing else is coerced. In particular `None` is
    **not** equal to `""` or to `0`: those are the structural-absence disagreements the
    absence rules exist to name individually, and folding them in here would make the
    rules unreachable and the populations unpinned.
    """
    if isinstance(ours, bool) or isinstance(theirs, bool):  # pragma: no cover - no bool lands
        return bool(ours) == bool(theirs)
    if isinstance(ours, int) and isinstance(theirs, int):
        return ours == theirs
    return bool(ours == theirs)


def magnitude(ours: Any, theirs: Any) -> bool:
    """Equality of magnitude, for the one column the export deliberately signs.

    The export marks *assigned to a club but on no roster list* by negating `league_id` —
    measured, on exactly 176 rows of this probe, and `contracts/loader.py` already refuses
    an unsigned column for the fields the walker signs because of it. The save stores the
    magnitude plus a separate roster-status byte, so the two encodings carry the same fact
    in different places and the magnitude is what is comparable.

    This is a *declared* semantic, not a tolerance: `field_map.toml` labels the field
    `export-exact-magnitude-all-rows`, `tests/test_parser_vs_export.py` pins the sign
    against the roster walk's independently derived unrostered set, and
    `tests/test_export_diff.py` asserts this spec and that label agree.
    """
    if not isinstance(ours, int) or not isinstance(theirs, int):  # pragma: no cover
        return False
    return ours == abs(theirs)


#: `teams.dat` stores a colour as a u32 ARGB; the export writes it as `#RRGGBB`. Measured
#: on every colour slot of all 259 clubs: the alpha byte is 0xff without exception, so the
#: two encodings carry the same 24 bits and nothing is discarded by comparing them.
_ALPHA_OPAQUE: Final = 0xFF
_RGB_MASK: Final = 0xFFFFFF


def argb_hex(ours: Any, theirs: Any) -> bool:
    """A stored ARGB integer against the export's `#RRGGBB` string.

    The alpha byte is **checked, not stripped**. Masking it away unconditionally would make
    a walk that had started reading one byte early compare equal on any club whose colour
    happened to survive the shift, and alpha is the one byte here whose expected value is
    known for every record.
    """
    if not isinstance(ours, int) or not isinstance(theirs, str):  # pragma: no cover
        return False
    if (ours >> 24) != _ALPHA_OPAQUE:
        return False
    return f"#{ours & _RGB_MASK:06X}" == theirs.upper()


# ── the specification ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ColumnPair:
    """One landed column, the export column that answers for it, and how they compare.

    `field` names the `field_map.toml` entry the column resolves through, and `validator`
    repeats the validator token that entry is expected to carry. That repetition is
    deliberate and is cross-checked by `tests/test_export_diff.py`: it makes the label a
    claim this harness *proves* rather than a label this harness *reads*. Deriving the
    comparison from the declaration would let somebody silence a failure by editing a label,
    which is precisely backwards.
    """

    column: str
    export: str
    field: str
    validator: str
    compare: Compare = exact


@dataclass(frozen=True, slots=True)
class TableSpec:
    """A landed table compared to an export table row by row, keyed, column by column."""

    table: str
    export_table: str
    key: str
    export_key: str
    columns: tuple[ColumnPair, ...]
    export_filter: str = ""
    #: What the export's population is expected to be. Pinned; see the module note.
    export_rows: int = 0
    #: How many framed records the export does not carry at all. Not a mismatch — a
    #: coverage fact, and one that has to be stated or a superset looks like a failure.
    parsed_only: int = 0

    @property
    def compared_columns(self) -> tuple[str, ...]:
        return tuple(pair.column for pair in self.columns)


@dataclass(frozen=True, slots=True)
class RowSpec:
    """A landed table whose whole row is the unit of comparison.

    Three of the six tables have no useful per-column diff. A roster membership *is* the
    triple `(team_id, player_id, list_id)`; there is no attribute hanging off it to
    disagree about, so the comparison is set equality and a disagreement names the whole
    row. The calendar is a multiset — the export carries genuine duplicate events, measured
    — so it is counted rather than set-differenced, or 325 duplicate rows would cancel out
    against each other and vanish.
    """

    table: str
    export_table: str
    columns: tuple[str, ...]
    export_columns: tuple[str, ...]
    #: `(field_map entry, the validator token that entry is expected to carry)`, one per
    #: compared column. **Per column rather than one token for the table**, because a green
    #: row comparison does not prove the same thing about every column in the row:
    #: `calendar_real_sim_date` is compared here and is 0 on both sides of every one of the
    #: 3,058 events, so the match discriminates nothing and its token stays `none`. Folding
    #: eight columns under one validator would have quietly promoted it.
    fields: tuple[tuple[str, str], ...]
    export_rows: int = 0
    export_filter: str = ""
    #: True where the export legitimately holds the same row more than once.
    multiset: bool = False


@dataclass(frozen=True, slots=True)
class AbsenceRule:
    """One named place a **correct** parse disagrees with the export, and how many.

    `population` is the whole point. A rule with no population is a mute button: it would
    absorb the day a real fault makes two hundred rows disagree in a shape the rule happens
    to match. Every rule declares exactly how many rows it may suppress, and
    `compare_keyed` / `compare_rows` fail naming the rule when the count moves in either
    direction — too few is as informative as too many, because it means the export changed
    under a harness that still claims to allow for it.
    """

    table: str
    #: `None` means the rule suppresses a whole export row rather than one column's value.
    #: A whole-row rule on a table compared column by column can never fire, so `compare_keyed`
    #: reports it as orphaned instead of carrying it silently.
    column: str | None
    reason: str
    population: int
    #: A **column** rule sees both rows and decides whether their disagreement is the export
    #: filling a gap. A **whole-row** rule sees only the export row, because there is no
    #: landed row to see — that is the whole claim. Two signatures rather than one with a
    #: dead parameter: a rule handed an empty `ours` mapping would read `ours.get(...)` as
    #: `None` and answer confidently for the wrong reason.
    allows: Callable[..., bool]


def _city_is_an_all_star_filler(ours: Mapping[str, Any], theirs: Mapping[str, Any]) -> bool:
    """The export substitutes the nickname where the save carries no city string.

    Measured: 26 clubs land `city` NULL, every one of them an `allstar_team` side, and on
    exactly those the export writes `name == nickname == 'All-Stars'`. The export never
    writes an empty `name` on any of the 259 — so it is filling, not passing through, and
    our NULL is the more faithful reading.

    Tied to the nickname rather than to the literal string: a rule reading *"NULL is fine
    when the export says All-Stars"* would also pass a club that genuinely lost its city.
    """
    return ours.get("city") is None and theirs.get("name") == theirs.get("nickname")


def _empty_string_for_no_counterpart(ours: Mapping[str, Any], theirs: Mapping[str, Any]) -> bool:
    """The export writes `''` where a club has no real-world counterpart; we write NULL.

    A CSV-shaped export has no NULL to write. 229 of 259 clubs are fictional and carry an
    empty `historical_id` there against NULL here.

    **The asymmetry with `bronze_player.historical_id` is real and is recorded rather than
    smoothed over.** The player walk lands `""` for a fictional player and reserves NULL for
    an undecoded tail — two different facts, deliberately kept apart (`warehouse/load.py`).
    The team walk has no such distinction to draw and lands NULL for both. Making them
    agree is a landing change, not a differential change, and it is carried in the phase
    handoff rather than made here under cover of a validation phase.
    """
    return ours.get("historical_id") is None and theirs.get("historical_id") == ""


def _all_star_side_sits_in_no_division(theirs: Mapping[str, Any]) -> bool:
    """The export writes division 0 for a club that is in no division at all.

    This is the case the plan pre-registered, landing on a real column. `division_id` counts
    from 0 within its sub-league — East really *is* division 0 — so a club that no division
    array names cannot be represented by a zero without colliding with a real division. It
    is represented by the absence of a row, which is why `bronze_division_team` is a
    membership table and not a `division_id` column on `bronze_team`.

    Measured: four all-star sides in the covered league, each carrying `division_id = 0` in
    the export and no row here.
    """
    return int(theirs.get("allstar_team") or 0) == 1


#: Every named place a correct parse and the export disagree. Three rules, and the plan's
#: own examples are **not** among them for a stated reason: `rules_active_roster_limit` and
#: the service-time columns live on the export's `leagues` table, and no walker lands a
#: league dimension, so those columns are outside the landed field set entirely. Inventing
#: entries for them would be an allowlist describing a comparison that does not happen.
ABSENCE_RULES: Final[tuple[AbsenceRule, ...]] = (
    AbsenceRule(
        table="bronze_team",
        column="city",
        reason=(
            "the save carries no city string for a generic all-star side; the export "
            "substitutes the nickname, and every one of these 26 clubs is an allstar_team"
        ),
        population=26,
        allows=_city_is_an_all_star_filler,
    ),
    AbsenceRule(
        table="bronze_team",
        column="historical_id",
        reason=(
            "a club with no real-world counterpart has no id; the export has no NULL to "
            "write and writes '' instead"
        ),
        population=229,
        allows=_empty_string_for_no_counterpart,
    ),
    AbsenceRule(
        table="bronze_division_team",
        column=None,
        reason=(
            "an all-star side is named by no division array and holds no row; the export "
            "writes division 0, which is a real division for every other club"
        ),
        population=4,
        allows=_all_star_side_sits_in_no_division,
    ),
)


SPECS: Final[tuple[TableSpec, ...]] = (
    TableSpec(
        table="bronze_team",
        export_table="teams",
        key="team_id",
        export_key="team_id",
        export_rows=EXPORT_TEAMS,
        columns=(
            ColumnPair("city", "name", "team_city", "export-exact-modulo-absence"),
            ColumnPair("abbr", "abbr", "team_abbr", "export-exact-all-rows"),
            ColumnPair("nickname", "nickname", "team_nickname", "export-exact-all-rows"),
            ColumnPair(
                "logo_filename",
                "logo_file_name",
                "team_logo_filename",
                "export-exact-all-rows",
            ),
            ColumnPair("city_id", "city_id", "team_city_id", "export-exact-all-rows"),
            ColumnPair("park_id", "park_id", "team_park_id", "export-exact-all-rows"),
            ColumnPair("league_id", "league_id", "team_league_id", "export-exact-all-rows"),
            ColumnPair(
                "sub_league_id",
                "sub_league_id",
                "team_sub_league_id",
                "export-exact-all-rows",
            ),
            ColumnPair("nation_id", "nation_id", "team_nation_id", "export-exact-all-rows"),
            ColumnPair("human_team", "human_team", "team_human_flag", "export-exact-all-rows"),
            ColumnPair("level", "level", "team_level", "export-exact-all-rows"),
            ColumnPair(
                "parent_team_id", "parent_team_id", "team_parent_id", "export-exact-all-rows"
            ),
            ColumnPair(
                "historical_id",
                "historical_id",
                "team_historical_id",
                "export-exact-modulo-absence",
            ),
            # Two of the three colours are identified exactly and the middle one is not.
            # Measured over all 259 clubs: `color_1` equals `background_color_id` 259/259,
            # `color_3` equals `text_color_id` 259/259, and `color_2` matches nothing the
            # export exposes — its best candidate, `ballcaps_visor_color_id`, scores 237/259.
            # So two colours are compared and the third is deliberately absent from this
            # list. Comparing it against its best candidate would ship a 22-row failure as
            # the harness's normal state, and allowlisting it would be an allowlist standing
            # in for an unfinished decode.
            ColumnPair(
                "color_1",
                "background_color_id",
                "team_color_background",
                "export-exact-all-rows",
                argb_hex,
            ),
            ColumnPair(
                "color_3",
                "text_color_id",
                "team_color_text",
                "export-exact-all-rows",
                argb_hex,
            ),
        ),
    ),
    TableSpec(
        table="bronze_player",
        export_table="players",
        key="player_id",
        export_key="player_id",
        export_filter=_EXPORT_ACTIVE_PLAYER_FILTER,
        export_rows=EXPORT_ACTIVE_PLAYERS,
        parsed_only=PARSED_ONLY_PLAYERS,
        columns=(
            ColumnPair("date_of_birth", "date_of_birth", "date_of_birth", "export-exact-all-rows"),
            ColumnPair("age", "age", "age", "export-exact-all-rows"),
            ColumnPair("nation_id", "nation_id", "nation_id", "export-exact-all-rows"),
            ColumnPair(
                "city_of_birth_id", "city_of_birth_id", "city_of_birth_id", "export-exact-all-rows"
            ),
            ColumnPair("weight", "weight", "weight", "export-exact-all-rows"),
            ColumnPair("height", "height", "height", "export-exact-all-rows"),
            ColumnPair(
                "uniform_number", "uniform_number", "uniform_number", "export-exact-all-rows"
            ),
            ColumnPair("experience", "experience", "experience", "export-exact-all-rows"),
            ColumnPair("team_id", "team_id", "team_id", "export-exact-all-rows"),
            ColumnPair("last_team_id", "last_team_id", "last_team_id", "export-exact-all-rows"),
            ColumnPair(
                "organization_id", "organization_id", "organization_id", "export-exact-all-rows"
            ),
            ColumnPair(
                "last_organization_id",
                "last_organization_id",
                "last_organization_id",
                "export-exact-all-rows",
            ),
            ColumnPair(
                "league_id",
                "league_id",
                "league_id",
                "export-exact-magnitude-all-rows",
                magnitude,
            ),
            ColumnPair(
                "last_league_id", "last_league_id", "last_league_id", "export-exact-all-rows"
            ),
            ColumnPair("free_agent", "free_agent", "free_agent", "export-exact-all-rows"),
            ColumnPair("bats", "bats", "bats", "export-exact-all-rows"),
            ColumnPair("throws", "throws", "throws", "export-exact-all-rows"),
            ColumnPair("historical_id", "historical_id", "historical_id", "export-exact-all-rows"),
        ),
    ),
)


ROW_SPECS: Final[tuple[RowSpec, ...]] = (
    RowSpec(
        table="bronze_team_roster",
        export_table="team_roster",
        columns=("team_id", "player_id", "list_id"),
        export_columns=("team_id", "player_id", "list_id"),
        fields=(("roster_membership", "export-exact-all-rows"),),
        export_rows=EXPORT_ROSTER_ROWS,
    ),
    RowSpec(
        table="bronze_league_event",
        export_table="league_events",
        # `seq` is absent on purpose: it is the file's own field and the export does not
        # expose it, which is exactly why `bronze_league_event`'s key had to be settled from
        # the bytes rather than from the answer key. Every column the export *does* expose
        # is compared.
        columns=(
            "league_id",
            "start_date",
            "event_type",
            "event_over",
            "deleted",
            "name",
            "needs_human_action",
            "real_sim_date",
        ),
        export_columns=(
            "league_id",
            "start_date",
            "type",
            "event_over",
            "deleted",
            "name",
            "needs_human_action",
            "real_sim_date",
        ),
        fields=(
            ("calendar_league_id", "export-exact-all-events"),
            ("calendar_start_date", "export-exact-all-events"),
            ("calendar_event_type", "export-exact-all-events"),
            ("calendar_event_over", "export-exact-all-events"),
            ("calendar_deleted", "export-exact-all-events"),
            ("calendar_name", "export-exact-all-events"),
            ("calendar_needs_human_action", "export-exact-all-events"),
            # Compared, and it proves nothing — deliberately left `none`. Measured on this
            # export: `real_sim_date` is 0 on all 3,058 rows and on every row of every save,
            # so a parser reading an adjacent zero `u16` scores identically here. The Phase
            # 8a panel caught this field labelled `verified` once already; a green
            # comparison is not evidence when the oracle cannot discriminate.
            ("calendar_real_sim_date", "none"),
        ),
        export_rows=EXPORT_CALENDAR_EVENTS,
        # Measured, and **two different keys give two different numbers** — both true, and
        # confusing them is how a correct figure ends up attached to the wrong claim. This
        # comment carried the wrong one until the Phase 9 acceptance panel re-measured it:
        #
        #   * the four-column human-readable key `(league_id, start_date, type, name)`
        #     collapses 3,058 rows to **2,600**, losing 458 — that is the Phase 8a *grain*
        #     argument for keying `bronze_league_event` on `seq` (plan §Phase 5b);
        #   * the **eight columns compared here** collapse 3,058 to **2,733**, losing 325 —
        #     and that is why *this* comparison is a multiset.
        #
        # 325 is still ample: under set semantics a walk that dropped one of a duplicated
        # pair would compare equal to one that kept both, and 325 lost events would report
        # clean.
        multiset=True,
    ),
)


#: Division membership, which is the one comparison written from **opposite sides**.
#: `bronze_division_team` comes out of `world.dat`'s division arrays — the league's view of
#: which clubs it contains — while the export's `teams.division_id` is the club's view of
#: which division it sits in. Two independent encodings of one fact; their agreement says
#: something no single-source check could. Kept out of `ROW_SPECS` because its export side
#: needs a league scope computed from our own rows, which `_diff_divisions` supplies.
DIVISION_SPEC: Final = RowSpec(
    table="bronze_division_team",
    export_table="teams",
    columns=("league_id", "sub_league_id", "division_id", "team_id"),
    export_columns=("league_id", "sub_league_id", "division_id", "team_id"),
    fields=(
        ("division_league_id", "export-exact-all-divisions"),
        ("division_sub_league_id", "export-exact-all-divisions"),
        ("division_id", "export-exact-all-divisions"),
        ("division_team_id", "export-exact-all-divisions"),
    ),
    # The EXPORT's population, not ours: the covered league's 34 clubs, four of which the
    # absence rule then suppresses to reach our 30. This carried `DIVISION_MEMBERSHIPS` — our
    # own landed count — while nothing read the field, which is how a declaration named for
    # one side ends up holding the other's number.
    export_rows=DIVISION_EXPORT_CLUBS,
)


# ── results ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ColumnResult:
    """One column's verdict, with every disagreeing row named."""

    table: str
    column: str
    export: str
    compared: int
    allowed: int
    mismatches: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.mismatches


@dataclass(frozen=True, slots=True)
class TableResult:
    """One table's verdict: its populations, its rule applications, and its columns."""

    table: str
    ours_rows: int
    theirs_rows: int
    compared_rows: int
    ours_only: tuple[str, ...]
    theirs_only: tuple[str, ...]
    columns: tuple[ColumnResult, ...]
    #: Export rows a whole-row absence rule suppressed. Carried so the table line can say so
    #: rather than leaving a reader to subtract `ours_rows` from `theirs_rows` and guess why.
    suppressed: int = 0
    rule_faults: tuple[str, ...] = ()

    @property
    def clean(self) -> bool:
        return (
            not self.ours_only
            and not self.theirs_only
            and not self.rule_faults
            and all(column.clean for column in self.columns)
        )


@dataclass(frozen=True, slots=True)
class DiffReport:
    """Every table's verdict. `failures()` is the whole output contract."""

    tables: tuple[TableResult, ...]

    @property
    def clean(self) -> bool:
        return all(table.clean for table in self.tables)

    def failures(self, *, sample: int = 10) -> tuple[str, ...]:
        """One line per disagreeing field, named. Never a rate.

        `sample` bounds how many individual rows each line quotes; the *count* is always
        exact and always stated, so a bounded sample can never read as a bounded problem.
        """
        lines: list[str] = []
        for table in self.tables:
            for fault in table.rule_faults:
                lines.append(f"{table.table}: {fault}")
            if table.ours_only:
                lines.append(
                    f"{table.table}: {len(table.ours_only)} rows landed that the export does "
                    f"not carry: {', '.join(table.ours_only[:sample])}"
                )
            if table.theirs_only:
                lines.append(
                    f"{table.table}: {len(table.theirs_only)} export rows did not land: "
                    f"{', '.join(table.theirs_only[:sample])}"
                )
            for column in table.columns:
                if column.clean:
                    continue
                lines.append(
                    f"{table.table}.{column.column} (export {column.export}): "
                    f"{len(column.mismatches)} of {column.compared} rows disagree — "
                    + "; ".join(column.mismatches[:sample])
                )
        return tuple(lines)

    def describe(self) -> str:
        """The whole run as text, clean columns included, for a handoff or a failure."""
        lines: list[str] = []
        for table in self.tables:
            suppressed = (
                f", {table.suppressed} allowed by an absence rule" if table.suppressed else ""
            )
            lines.append(
                f"{table.table}: {table.compared_rows} rows compared "
                f"(landed {table.ours_rows}, export {table.theirs_rows}{suppressed})"
            )
            for column in table.columns:
                verdict = "ok" if column.clean else f"{len(column.mismatches)} MISMATCHED"
                allowed = f", {column.allowed} allowed" if column.allowed else ""
                lines.append(
                    f"    {column.column} vs {column.export}: "
                    f"{column.compared} compared{allowed} — {verdict}"
                )
        return "\n".join(lines)


# ── the comparison itself, pure so CI can exercise it without a warehouse ─────


def compare_keyed(
    ours: Mapping[Any, Mapping[str, Any]],
    theirs: Mapping[Any, Mapping[str, Any]],
    spec: TableSpec,
    rules: Sequence[AbsenceRule] = ABSENCE_RULES,
) -> TableResult:
    """Diff two keyed row sets column by column, applying the absence rules.

    Rows the export does not carry are **not** silently dropped: `spec.parsed_only` states
    how many are expected, and a different number is reported as a row-level difference.
    That is what keeps *"the walk frames five records the export has never heard of"* — a
    real, measured property of `players.dat` — separate from *"the walk lost five records"*.

    **The count check runs in both directions.** Reporting only the rows it can name made
    the guard one-directional: with `parsed_only = 5` and nothing extra landed, there were
    no rows to list, so the report came back empty and the run read clean — which is the
    silent green this module exists to refuse. A walk that stopped framing the five records
    the export has never carried is exactly as interesting as one that grew a sixth.
    """
    applicable = [rule for rule in rules if rule.table == spec.table]
    shared = sorted(set(ours) & set(theirs), key=_sort_key)

    ours_only = sorted(set(ours) - set(theirs), key=_sort_key)
    theirs_only = sorted(set(theirs) - set(ours), key=_sort_key)

    rule_faults: list[str] = []
    unexplained_ours_only: tuple[str, ...] = ()
    if len(ours_only) != spec.parsed_only:
        unexplained_ours_only = tuple(f"{spec.key}={key}" for key in ours_only)
        rule_faults.append(
            f"{len(ours_only)} landed rows are absent from the export against a declared "
            f"parsed_only of {spec.parsed_only}. Fewer is as informative as more: it means "
            "the walk stopped framing records the export has never carried, and there are "
            "no rows left to name"
        )

    rule_faults.extend(_export_population_fault(spec.table, spec.export_rows, len(theirs)))

    # A whole-row rule on a keyed table can never match a column, so it would sit here
    # forever, never firing and never population-checked. Named rather than ignored.
    orphaned = [
        rule
        for rule in applicable
        if rule.column is None or rule.column not in spec.compared_columns
    ]
    rule_faults.extend(
        f"the absence rule on {rule.table}.{rule.column or '(whole rows)'} targets a table "
        "compared column by column, but names no column this spec compares. It can never "
        "fire, so its population is never checked"
        for rule in orphaned
    )

    columns: list[ColumnResult] = []
    for pair in spec.columns:
        rule = next(
            (r for r in applicable if r.column is not None and r.column == pair.column), None
        )
        mismatches: list[str] = []
        allowed = 0
        for key in shared:
            our_row, their_row = ours[key], theirs[key]
            if pair.compare(our_row.get(pair.column), their_row.get(pair.export)):
                continue
            if rule is not None and rule.allows(our_row, their_row):
                allowed += 1
                continue
            mismatches.append(
                f"{spec.key}={key}: landed {our_row.get(pair.column)!r} vs export "
                f"{their_row.get(pair.export)!r}"
            )
        if rule is not None and allowed != rule.population:
            rule_faults.append(_rule_fault(rule, allowed))
        columns.append(
            ColumnResult(
                table=spec.table,
                column=pair.column,
                export=pair.export,
                compared=len(shared),
                allowed=allowed,
                mismatches=tuple(mismatches),
            )
        )

    return TableResult(
        table=spec.table,
        ours_rows=len(ours),
        theirs_rows=len(theirs),
        compared_rows=len(shared),
        ours_only=unexplained_ours_only,
        theirs_only=tuple(f"{spec.key}={key}" for key in theirs_only),
        columns=tuple(columns),
        rule_faults=tuple(rule_faults),
    )


def compare_rows(
    ours: Iterable[Mapping[str, Any]],
    theirs: Iterable[Mapping[str, Any]],
    spec: RowSpec,
    rules: Sequence[AbsenceRule] = ABSENCE_RULES,
) -> TableResult:
    """Diff two row sets whose whole row is the unit, as a set or as a multiset.

    Rules with `column is None` apply here: they suppress an export row that legitimately
    has no counterpart, and they are counted against their declared population exactly as
    the column rules are.

    **Each rule keeps its own tally.** A single shared counter judged every rule against the
    sum, so two rules of population 1 matching one row each would both report having allowed
    2 — turning a correct run red — while a rule over-firing could be masked by a sibling
    that under-fired. First match wins, and a row two rules both claim is reported in its own
    right rather than being counted once and attributed arbitrarily.
    """
    applicable = [rule for rule in rules if rule.table == spec.table and rule.column is None]

    our_rows = list(ours)
    their_rows = list(theirs)
    export_population = len(their_rows)

    ours_keys = Counter(_row_key(row, spec.columns) for row in our_rows)

    rule_faults: list[str] = []
    allowed_by_rule: dict[int, int] = dict.fromkeys(range(len(applicable)), 0)
    if applicable:
        kept: list[Mapping[str, Any]] = []
        for row in their_rows:
            claiming = [index for index, rule in enumerate(applicable) if rule.allows(row)]
            if not claiming:
                kept.append(row)
                continue
            allowed_by_rule[claiming[0]] += 1
            if len(claiming) > 1:
                rule_faults.append(
                    f"an export row is claimed by {len(claiming)} absence rules at once "
                    f"({[applicable[i].column or '(whole rows)' for i in claiming]}), so "
                    "whichever population it is counted against is arbitrary"
                )
        their_rows = kept

    theirs_keys = Counter(_row_key(row, spec.export_columns) for row in their_rows)
    rule_faults.extend(
        _rule_fault(rule, allowed_by_rule[index])
        for index, rule in enumerate(applicable)
        if allowed_by_rule[index] != rule.population
    )
    # Against the PRE-suppression population: `export_rows` pins what the export returns,
    # which is what a narrowed fetch would change.
    rule_faults.extend(_export_population_fault(spec.table, spec.export_rows, export_population))

    if spec.multiset:
        ours_extra = ours_keys - theirs_keys
        theirs_extra = theirs_keys - ours_keys
    else:
        # A set difference over rows that are supposed to be unique. Duplicates on either
        # side would be invisible to it, so they are reported in their own right rather
        # than assumed away.
        for label, counted in (("landed", ours_keys), ("export", theirs_keys)):
            repeated = [key for key, count in counted.items() if count > 1]
            if repeated:
                rule_faults.append(
                    f"the {label} side holds {len(repeated)} duplicate rows in a table "
                    f"declared unique: {repeated[:5]}"
                )
        ours_extra = Counter(dict.fromkeys(set(ours_keys) - set(theirs_keys), 1))
        theirs_extra = Counter(dict.fromkeys(set(theirs_keys) - set(ours_keys), 1))

    compared = sum((ours_keys & theirs_keys).values())
    return TableResult(
        table=spec.table,
        ours_rows=len(our_rows),
        theirs_rows=export_population,
        compared_rows=compared,
        ours_only=_render_rows(ours_extra, spec.columns),
        theirs_only=_render_rows(theirs_extra, spec.columns),
        # One entry per compared column, carrying no mismatches of its own — row-level
        # differences stay where they are, in `ours_only` / `theirs_only`. Without these a
        # clean row-spec table printed a single row-count line, and a reader auditing a GREEN
        # run had no evidence that the eight calendar columns were in scope at all: a run
        # comparing all eight and a run comparing none looked identical.
        columns=tuple(
            ColumnResult(
                table=spec.table,
                column=column,
                export=export,
                compared=compared,
                allowed=0,
                mismatches=(),
            )
            for column, export in zip(spec.columns, spec.export_columns, strict=True)
        ),
        suppressed=sum(allowed_by_rule.values()),
        rule_faults=tuple(rule_faults),
    )


def _export_population_fault(table: str, expected: int, actual: int) -> tuple[str, ...]:
    """The anti-narrowing pin, enforced rather than declared.

    `export_rows` was documented as *the* guarantee that a comparison cannot silently shrink
    — "a comparison that derives its own expected size from the data it is comparing cannot
    notice that it compared nothing" — and nothing read it. The real pin lived in the
    `gamedata` module, which CI never runs, so a `WHERE` clause added to a fetch would have
    turned the offline suite greener rather than redder.
    """
    if not expected or expected == actual:
        return ()
    return (
        f"the export side of {table} came back with {actual} rows against a pinned "
        f"{expected}. Either the answer key moved or the fetch was narrowed; a comparison "
        "over fewer rows than declared passes more easily than the one that was specified",
    )


def _rule_fault(rule: AbsenceRule, allowed: int) -> str:
    target = rule.column or "(whole rows)"
    return (
        f"the absence rule on {target} allowed {allowed} rows against a declared population "
        f"of {rule.population}. The rule exists because {rule.reason}; a population that has "
        "moved means either the export changed or something the rule was never meant to "
        "cover is now matching it"
    )


def _row_key(row: Mapping[str, Any], columns: Sequence[str]) -> tuple[Any, ...]:
    return tuple(_normalise(row.get(name)) for name in columns)


def _normalise(value: Any) -> Any:
    """Make two column widths of the same number compare and hash alike."""
    if isinstance(value, bool):  # pragma: no cover - no bool column lands
        return int(value)
    return value


def _render_rows(counted: Counter[tuple[Any, ...]], columns: Sequence[str]) -> tuple[str, ...]:
    rendered: list[str] = []
    for key, count in sorted(counted.items(), key=lambda item: _sort_key(item[0])):
        row = ", ".join(f"{name}={value!r}" for name, value in zip(columns, key, strict=False))
        rendered.append(row if count == 1 else f"{row} (x{count})")
    return tuple(rendered)


def _sort_key(value: Any) -> str:
    """Order keys of mixed type without raising. Presentation only."""
    return str(value)


# ── provenance, asserted before anything is compared ─────────────────────────


def check_provenance(
    truth: Connection[DictCursor],
    *,
    sim_date: SaveDate,
    human_team_id: int | None,
) -> None:
    """Refuse to diff a landed snapshot against an export of a different universe.

    Both halves matter and they fail differently. A **date** disagreement means the export
    was taken at another moment of the same league: ids still line up, so the diff would
    return a plausible scatter of roster and age differences that reads exactly like a
    parser bug. A **club** disagreement means somebody pointed the harness at another save
    entirely, and every id would disagree at once.

    `current_date` is read through `quote_ident`, and this is the one place in the project
    where that has been *observed* to matter: measured on this export, bare
    ``SELECT current_date FROM leagues`` returns the wall-clock date — 2026-08-19 on the day
    this was written — because MySQL parses the bare name as the `CURRENT_DATE` function,
    while the backticked form returns the league's 2024-03-18. A provenance check written
    the obvious way would have compared the sim date against today's date, failed, and sent
    the next reader hunting a parser bug that does not exist.

    Raises:
        ProvenanceMismatch: naming both sides.
    """
    with truth.cursor() as cursor:
        cursor.execute(
            f"SELECT {quote_ident('current_date')} AS sim_date "
            f"FROM {quote_ident('leagues')} "
            f"WHERE {quote_ident('league_id')} = ("
            f"  SELECT {quote_ident('league_id')} FROM {quote_ident('teams')} "
            f"  WHERE {quote_ident('human_team')} = 1 LIMIT 1)"
        )
        row = cursor.fetchone()
        cursor.execute(
            f"SELECT {column_list(('team_id', 'nickname'))} FROM {quote_ident('teams')} "
            f"WHERE {quote_ident('human_team')} = 1"
        )
        human = cursor.fetchall()

    if row is None:
        raise ProvenanceMismatch(
            "the export names no league for its human club, so it cannot state the date it "
            "describes and nothing below could be trusted"
        )
    export_date = str(row["sim_date"])
    if export_date != str(sim_date):
        raise ProvenanceMismatch(
            f"the landed snapshot is dated {sim_date} and the export describes "
            f"{export_date}. These are two moments of a league, and a field diff across "
            "them returns a plausible scatter of differences that reads like a parser fault"
        )
    if export_date != TRUTH_SAVE_SIM_DATE:
        raise ProvenanceMismatch(
            f"the export describes {export_date}, not the retained standard-mode save's "
            f"{TRUTH_SAVE_SIM_DATE}. Tier B is confined to that one save; a different export "
            "is a different answer key and its populations are not the ones pinned here"
        )

    if len(human) != 1:
        raise ProvenanceMismatch(
            f"the export flags {len(human)} human clubs, not one, so which universe it "
            "describes is not decidable"
        )
    export_team = int(human[0]["team_id"])
    if (
        export_team != TRUTH_SAVE_HUMAN_TEAM_ID
        or human[0]["nickname"] != TRUTH_SAVE_HUMAN_TEAM_NICKNAME
    ):
        raise ProvenanceMismatch(
            f"the export's human club is {export_team} ({human[0]['nickname']!r}), not "
            f"{TRUTH_SAVE_HUMAN_TEAM_ID} ({TRUTH_SAVE_HUMAN_TEAM_NICKNAME!r})"
        )
    if human_team_id is not None and human_team_id != export_team:
        raise ProvenanceMismatch(
            f"the landed snapshot is managed by club {human_team_id} and the export by "
            f"{export_team}. The binaries and the export do not describe the same universe"
        )


# ── reading both sides ───────────────────────────────────────────────────────


def diff_snapshot(
    warehouse: Connection[DictCursor],
    truth: Connection[DictCursor],
    *,
    save_id: str,
    sim_date: SaveDate,
    ingest_seq: int,
    human_team_id: int | None = None,
) -> DiffReport:
    """Diff one landed snapshot against the export, table by table.

    Both connections point at the same MySQL instance and neither side is written or
    exported to a file. The comparison happens here, in Python, on decoded values.

    **Provenance is asserted here, as the first statement, before a single value is read.**
    It was previously asserted only by a test that happened to sit above the comparison in
    one module, which made *"provenance before any value comparison"* a property of pytest's
    file ordering rather than of the code — and this is the entry point Phase 10's render
    gate is told to call. A caller that skipped the check would diff whatever is landed
    against whatever export is configured and get a plausible scatter of roster and age
    differences that reads exactly like a catastrophic parser fault.

    Raises:
        ProvenanceMismatch: the landing and the export describe different universes.
    """
    check_provenance(truth, sim_date=sim_date, human_team_id=human_team_id)

    results: list[TableResult] = []
    for spec in SPECS:
        ours = _fetch_keyed(
            warehouse,
            table=spec.table,
            key=spec.key,
            columns=spec.compared_columns,
            save_id=save_id,
            sim_date=sim_date,
            ingest_seq=ingest_seq,
        )
        theirs = _fetch_export_keyed(truth, spec)
        results.append(compare_keyed(ours, theirs, spec))

    for row_spec in ROW_SPECS:
        our_rows = _fetch_rows(
            warehouse,
            table=row_spec.table,
            columns=row_spec.columns,
            save_id=save_id,
            sim_date=sim_date,
            ingest_seq=ingest_seq,
        )
        their_rows = _fetch_export_rows(truth, row_spec)
        results.append(compare_rows(our_rows, their_rows, row_spec))

    results.append(_diff_divisions(warehouse, truth, save_id, sim_date, ingest_seq))
    return DiffReport(tables=tuple(results))


def _diff_divisions(
    warehouse: Connection[DictCursor],
    truth: Connection[DictCursor],
    save_id: str,
    sim_date: SaveDate,
    ingest_seq: int,
) -> TableResult:
    """The one comparison written from opposite sides, which is what makes it worth having.

    `bronze_division_team` comes out of `world.dat`'s division arrays — the league's view of
    which clubs it contains. The export's `teams.division_id` is the club's view of which
    division it sits in. Two independent encodings of one fact, and their agreement says
    something a single-source check could not.

    **Scoped to the leagues the walk actually reaches**, which is MLB alone: the other
    fourteen leagues sit behind their own unmapped scalar blocks in `world.dat` (Phase 5b).
    The scope is taken from our own side and then *pinned* — one league, thirty memberships
    — so a walk that quietly stopped covering a division narrows the comparison and goes red
    rather than comparing less and still passing.
    """
    spec = DIVISION_SPEC
    columns = spec.columns
    ours = _fetch_rows(
        warehouse,
        table=spec.table,
        columns=columns,
        save_id=save_id,
        sim_date=sim_date,
        ingest_seq=ingest_seq,
    )
    covered = sorted({int(row["league_id"]) for row in ours})

    faults: list[str] = []
    if len(covered) != DIVISION_LEAGUES or len(ours) != DIVISION_MEMBERSHIPS:
        faults.append(
            f"the division walk covers {len(covered)} leagues and {len(ours)} memberships "
            f"against the pinned {DIVISION_LEAGUES} and {DIVISION_MEMBERSHIPS}. The "
            "comparison below is scoped to what the walk covers, so a narrowed walk would "
            "otherwise compare less and still pass"
        )

    with truth.cursor() as cursor:
        placeholders = ", ".join(["%s"] * len(covered)) if covered else "NULL"
        cursor.execute(
            f"SELECT {column_list((*spec.export_columns, 'allstar_team'))} "
            f"FROM {quote_ident(spec.export_table)} "
            f"WHERE {quote_ident('league_id')} IN ({placeholders})",
            tuple(covered),
        )
        theirs = list(cursor.fetchall())

    result = compare_rows(ours, theirs, spec)
    if not faults:
        return result
    return TableResult(
        table=result.table,
        ours_rows=result.ours_rows,
        theirs_rows=result.theirs_rows,
        compared_rows=result.compared_rows,
        ours_only=result.ours_only,
        theirs_only=result.theirs_only,
        columns=result.columns,
        suppressed=result.suppressed,
        rule_faults=(*result.rule_faults, *faults),
    )


def _fetch_keyed(
    connection: Connection[DictCursor],
    *,
    table: str,
    key: str,
    columns: Sequence[str],
    save_id: str,
    sim_date: SaveDate,
    ingest_seq: int,
) -> dict[Any, Mapping[str, Any]]:
    rows = _fetch_rows(
        connection,
        table=table,
        columns=(key, *columns),
        save_id=save_id,
        sim_date=sim_date,
        ingest_seq=ingest_seq,
    )
    return _key_by(rows, key, where=table)


class DuplicateKeys(Exception):  # noqa: N818
    """One side of a keyed comparison holds a key more than once.

    Silently collapsing it is the failure `compare_rows` already refuses on the set path —
    *"a set difference cannot see a duplicate"*. Our side is protected by the bronze primary
    key; the export side is not ours and carries no such guarantee, and a duplicated export
    row would otherwise present as a smaller-than-pinned population, which is a true symptom
    reported as the wrong problem.
    """


def _key_by(
    rows: Sequence[Mapping[str, Any]], key: str, *, where: str
) -> dict[Any, Mapping[str, Any]]:
    keyed = {row[key]: row for row in rows}
    if len(keyed) != len(rows):
        seen = Counter(row[key] for row in rows)
        repeated = sorted((str(value) for value, n in seen.items() if n > 1))[:10]
        raise DuplicateKeys(
            f"{where} returned {len(rows)} rows under {len(keyed)} distinct {key} values; "
            f"repeated: {repeated}. Keying them would drop rows without reporting anything, "
            "and the population would come back short with no indication why"
        )
    return keyed


def _fetch_rows(
    connection: Connection[DictCursor],
    *,
    table: str,
    columns: Sequence[str],
    save_id: str,
    sim_date: SaveDate,
    ingest_seq: int,
) -> list[Mapping[str, Any]]:
    """One landed snapshot's rows. Every identifier quoted; all three values bound."""
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {column_list(columns)} FROM {quote_ident(table)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            (save_id, as_sql_date(sim_date), ingest_seq),
        )
        return list(cursor.fetchall())


def _fetch_export_keyed(
    connection: Connection[DictCursor], spec: TableSpec
) -> dict[Any, Mapping[str, Any]]:
    # The rule columns are pulled whether or not they are compared. The absence rules read
    # them to decide whether a NULL is the export filling a gap or a real disagreement, and
    # a rule that cannot see the row it is judging is a rule that says yes to everything.
    wanted = {pair.export for pair in spec.columns}
    wanted.update(EXPORT_RULE_COLUMNS.get(spec.export_table, ()))
    columns = (spec.export_key, *sorted(wanted - {spec.export_key}))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {column_list(columns)} FROM {quote_ident(spec.export_table)} "
            f"{spec.export_filter}".strip()
        )
        return _key_by(list(cursor.fetchall()), spec.export_key, where=spec.export_table)


def _fetch_export_rows(
    connection: Connection[DictCursor], spec: RowSpec
) -> list[Mapping[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {column_list(spec.export_columns)} FROM {quote_ident(spec.export_table)} "
            f"{spec.export_filter}".strip()
        )
        return list(cursor.fetchall())


#: Which extra export columns each table's absence rules need in hand to judge a row. A
#: rule reads the whole export row, not just the column under comparison, which is what
#: lets `_city_is_an_all_star_filler` tie its exception to the nickname rather than
#: accepting any NULL city at all.
EXPORT_RULE_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "teams": ("nickname", "allstar_team"),
}
