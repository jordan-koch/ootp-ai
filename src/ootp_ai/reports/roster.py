"""The roster report — the first thing in this project's history that names a player.

This is the page the whole slice exists for. Everything upstream of it is machinery; this
is where the GM stops reading integers and starts reading *Rafael Devers*.

## Why the columns are data and not code

Plan step 4 is *"route **every** report column through `contracts/policy.py`. There is no
second path to the page."* A rule like that is only worth what its enforcement is worth,
and enforcement by code review is worth nothing six months from now. So the values this
report renders are a declared tuple, `check_renderable` resolves every one of them through
the serving gate before a single line is formatted, and a withheld column aborts the whole
report rather than being quietly skipped.

That ordering matters: skipping a withheld column would produce a page that looks correct
and is missing something the reader has no way to notice. Refusing produces a page that
does not exist, which is loud.

**`REPORT_COLUMNS` and `SELECTED_COLUMNS` are asserted congruent offline**, because the
first version of this module claimed the column list was "exhaustive by construction" and
it was not: the club headings printed `city`, `nickname` and `level`, the section headings
printed `list_id`, and none of the four was gated, while their sibling `abbr` was. The
claim is now a test rather than a sentence.

## The grain, and why a player can appear twice

`bronze_team_roster` is one row per player per team per **list**, and lists overlap by
design (`parser/rosters.py`): a 40-man prospect assigned to an affiliate holds a list-1
row at the affiliate and a list-3 row at the parent club. Grouping by list therefore shows
some players more than once, and the report says so — and counts them from the rows in
hand — rather than de-duplicating. Collapsing them would invent a hierarchy the warehouse
does not have, and would lose exactly the fan-out the grain was designed to keep.

## The population no roster list contains

Driving this report from `bronze_team_roster` alone would silently lose every player who
is on the club's books and on no list. `tables.toml` flags it in so many words: *"A query
asking 'who is in Boston's organisation' from this table alone misses them."* So the query
drives from `bronze_player.organization_id` and joins the roster rows on, which turns those
players into a named section instead of an absence.

## No figure on this page is remembered

Every count the page states is derived from the snapshot being rendered. An earlier draft
printed two constants carried over from the probe save's export — one of them wrong for
this landing by roughly 27x — a few lines under the page's own promise that *"every figure
below is that snapshot and no other."* On the single surface ADR 0016 gives the GM, a
confidently wrong number is the most expensive thing this module could produce.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.contracts.loader import Column, Contracts
from ootp_ai.contracts.policy import (
    Disposition,
    WithheldFieldError,
    column_disposition,
    uncertainty_banner,
)
from ootp_ai.parser.names import SINGLE_NAME_SPACE
from ootp_ai.parser.rosters import LIST_ACTIVE, LIST_ASSIGNMENT, LIST_INJURED, LIST_SECONDARY
from ootp_ai.reports.resolve import SnapshotRef
from ootp_ai.warehouse.sql import column_list, quote_ident

__all__ = [
    "ABSENT",
    "LIST_LABELS",
    "REPORT_COLUMNS",
    "SELECTED_COLUMNS",
    "Club",
    "ReportColumn",
    "RosterRow",
    "build_roster",
    "check_renderable",
    "club_display_name",
    "fetch_clubs",
    "list_label_mode",
    "name_join_predicate",
    "render_roster",
]

#: What a cell shows when the value is structurally absent — the record did not carry the
#: field. **Never an empty string and never a zero.** `bats`/`throws` land NULL when a
#: player's identity tail did not decode, and "we did not read it" is a different fact from
#: "he bats right" (`.claude/agents/data-engineer.md`, structural absence).
ABSENT: Final = "—"

#: The `list_id` enum in the operator-verified reading, cross-checked against the export
#: (`reviews/list-id-semantics.md`). Human labels are used because the mapping is
#: `verified` — well above the `inferred` floor the scope's SD-17 fallback set for
#: printing a label at all. Were it below that floor this would print raw integers with a
#: banner instead, and `contracts/policy.py` would be the thing forcing the choice.
LIST_LABELS: Final[Mapping[int, str]] = {
    LIST_ACTIVE: "Active roster",
    LIST_SECONDARY: "Secondary (40-man) roster",
    LIST_INJURED: "Injured list",
    LIST_ASSIGNMENT: "Assigned to the club",
}

#: Presentation order: what a GM looks for first, not the numeric order of the enum.
LIST_ORDER: Final = (LIST_ACTIVE, LIST_SECONDARY, LIST_INJURED, LIST_ASSIGNMENT)

#: `bats` and `throws` as the walker verified them against the export on all 18,072 rows
#: (`field_map.toml`). A value outside these is not silently passed through — see
#: `_handedness`.
BATS_LABELS: Final[Mapping[int, str]] = {1: "R", 2: "L", 3: "S"}
THROWS_LABELS: Final[Mapping[int, str]] = {1: "R", 2: "L"}


@dataclass(frozen=True, slots=True)
class ReportColumn:
    """One value on the page, tied to the declared column it comes from.

    `table` and `column` are the declaration's names rather than the header's, which is
    what lets `check_renderable` resolve the epistemic label. A column with no declared
    source could not be gated, so there is no way to declare one.

    `may_be_uncertain` marks the one value with a **pre-registered fallback**. Scope
    SD-17 says the report may print a human roster-list label only while that mapping
    holds at least `inferred`, and must otherwise fall back to raw integers plus a
    banner. For every other value there is no fallback and low confidence aborts.
    """

    header: str
    table: str
    column: str
    may_be_uncertain: bool = False


#: Every landed value this report renders, headings and ordering included.
#:
#: **Corrected after the Phase 10 acceptance panel.** The first version held seven entries
#: and the docstring claimed the list was "exhaustive by construction" — it was not.
#: `city`, `nickname` and `level` reached the page through the club headings, `list_id`
#: through the section headings, and `team_id` through the unresolvable-club fallback,
#: none of them gated, while their sibling `abbr` was declared. The list was internally
#: inconsistent rather than merely short, and a guard that misses the values its author
#: did not think about is the guard failing at its only job.
REPORT_COLUMNS: Final = (
    ReportColumn(header="Player", table="bronze_name", column="name_text"),
    ReportColumn(header="Age", table="bronze_player", column="age"),
    ReportColumn(header="B/T", table="bronze_player", column="bats"),
    ReportColumn(header="B/T", table="bronze_player", column="throws"),
    ReportColumn(header="#", table="bronze_player", column="uniform_number"),
    ReportColumn(header="Player id", table="bronze_player", column="player_id"),
    ReportColumn(header="Club", table="bronze_player", column="team_id"),
    ReportColumn(header="Organisation", table="bronze_player", column="organization_id"),
    ReportColumn(header="Club", table="bronze_team", column="team_id"),
    ReportColumn(header="Club", table="bronze_team", column="abbr"),
    ReportColumn(header="Club", table="bronze_team", column="city"),
    ReportColumn(header="Club", table="bronze_team", column="nickname"),
    ReportColumn(header="Club order", table="bronze_team", column="level"),
    # All three resolve through the single `roster_membership` field entry, so its label
    # governs the whole triple and the fallback has to cover the whole triple too. Marking
    # only `list_id` made a downgrade abort the report instead of taking the fallback —
    # which is precisely the outcome SD-17 exists to avoid. Raw ids plus the banner is the
    # honest render of an unconfirmed membership mapping; refusing to render is not.
    ReportColumn(
        header="Club", table="bronze_team_roster", column="team_id", may_be_uncertain=True
    ),
    ReportColumn(
        header="Player id", table="bronze_team_roster", column="player_id", may_be_uncertain=True
    ),
    ReportColumn(
        header="Roster list", table="bronze_team_roster", column="list_id", may_be_uncertain=True
    ),
)

#: The `(table, column)` pairs this module puts in a SELECT list — the values it pulls out
#: of the warehouse, as opposed to the key columns it filters and joins on.
#:
#: Kept beside the gate so `tests/test_report_rendering.py` can assert the two are the
#: **same set**. Congruence rather than containment: a selected column missing from the
#: gate is a value reaching the page unchecked, and a gated column nobody selects is a
#: guard aimed at nothing, quietly reporting coverage it does not have.
SELECTED_COLUMNS: Final = frozenset(
    {
        ("bronze_player", "player_id"),
        ("bronze_player", "age"),
        ("bronze_player", "bats"),
        ("bronze_player", "throws"),
        ("bronze_player", "uniform_number"),
        ("bronze_player", "team_id"),
        ("bronze_player", "organization_id"),
        ("bronze_name", "name_text"),
        ("bronze_team_roster", "team_id"),
        ("bronze_team_roster", "player_id"),
        ("bronze_team_roster", "list_id"),
        ("bronze_team", "team_id"),
        ("bronze_team", "abbr"),
        ("bronze_team", "city"),
        ("bronze_team", "nickname"),
        ("bronze_team", "level"),
    }
)


@dataclass(frozen=True, slots=True)
class Club:
    """One club of the landing, as a roster heading needs it.

    `level` orders the organisation the way a GM reads it — the major-league club first,
    then the affiliates by rung — rather than alphabetically, which would open Boston's
    roster with a rookie-league side.
    """

    team_id: int
    abbr: str
    name: str
    level: int


@dataclass(frozen=True, slots=True)
class RosterRow:
    """One player of the configured organisation, with the lists he holds."""

    player_id: int
    first_name: str | None
    last_name: str | None
    age: int | None
    bats: int | None
    throws: int | None
    uniform_number: int | None
    team_id: int | None
    memberships: tuple[tuple[int, int], ...]
    """`(team_id, list_id)` pairs, sorted. Empty for a player on no list at all."""

    @property
    def display_name(self) -> str:
        """First and last as the name table resolved them.

        Absence is reported rather than papered over: a name index that resolved to
        nothing means the join failed, and printing the id alone would look like a player
        genuinely called `47035`.
        """
        parts = [part for part in (self.first_name, self.last_name) if part]
        return " ".join(parts) if parts else ABSENT


def check_renderable(contracts: Contracts, columns: Sequence[ReportColumn]) -> None:
    """Resolve every report column through the serving gate, or refuse the report.

    **The gate runs over the declared column, not over a hand-kept list of "safe" names.**
    `column_disposition` checks the column name against the withheld fragments *and*
    resolves its field entry's category and epistemic label, so a rating that acquired a
    report column would be caught by the same call that checks a uniform number.

    A withheld column always aborts. An *uncertain* one aborts too, unless it is the one
    value carrying a pre-registered fallback (`may_be_uncertain`) — and even then the
    fallback has to be taken, which is `list_label_mode`'s job rather than this one's.
    Dropping a column silently is never an option: a missing column is indistinguishable
    from one nobody asked for.

    Raises:
        WithheldFieldError: naming the column and what the policy decided about it.
    """
    for entry in columns:
        decided = _disposition_of(contracts, entry)
        if decided is Disposition.RENDERABLE:
            continue
        if decided is Disposition.UNCERTAIN and entry.may_be_uncertain:
            continue
        raise WithheldFieldError(
            f"roster report column {entry.header!r} reads "
            f"{entry.table}.{entry.column}, which the policy rules {decided.value}. "
            "The report refuses rather than dropping the column: a silently missing "
            "column is indistinguishable from one nobody asked for"
        )


def list_label_mode(contracts: Contracts) -> tuple[bool, str | None]:
    """Whether roster-list headings may use human labels, and the banner if they may not.

    **Scope SD-17's pre-registered fallback, implemented rather than described.** The rule
    is that the report *"never prints a human label (`active roster`, `40-man`) for a
    `list_id` whose mapping is not labelled at least `inferred` — a wrong label produces a
    confidently wrong roster with nothing throwing."*

    That rule was prose until the Phase 10 acceptance panel simulated downgrading
    `roster_membership` to `unconfirmed` and found the report still printing "Active
    roster" with nothing red, because no code in this package had ever called
    `render_with_uncertainty` or `uncertainty_banner`. The fallback was documented as
    honoured and was unreachable.

    Returns:
        `(True, None)` while the mapping holds, or `(False, banner)` when it does not —
        in which case headings become raw `list_id = N` and the banner goes on the page.
    """
    entry = next(column for column in REPORT_COLUMNS if column.column == "list_id")
    decided = _disposition_of(contracts, entry)
    if decided is Disposition.RENDERABLE:
        return (True, None)
    table = contracts.table(entry.table)
    field = contracts.field(_required_field(table.column(entry.column)))
    return (False, uncertainty_banner(field))


def _disposition_of(contracts: Contracts, entry: ReportColumn) -> Disposition:
    table = contracts.table(entry.table)
    return column_disposition(contracts, table, table.column(entry.column))


def _required_field(column: Column) -> str:
    if column.field is None:  # pragma: no cover - the loader refuses such a column
        raise WithheldFieldError(f"column {column.name!r} carries no field to describe")
    return column.field


def build_roster(
    connection: Connection[DictCursor],
    contracts: Contracts,
    ref: SnapshotRef,
) -> tuple[RosterRow, ...]:
    """Every player whose organisation is the landing's human club, with his lists.

    Raises:
        WithheldFieldError: a report column is not renderable.
        ValueError: the landing recorded no human club, so "our organisation" is undefined.
    """
    check_renderable(contracts, REPORT_COLUMNS)
    if ref.human_team_id is None:
        raise ValueError(
            f"the landing {ref.save_id} at {ref.sim_date} seq {ref.ingest_seq} recorded no "
            "human_team_id, so the configured organisation cannot be resolved. A roster "
            "report filtered to nobody would render as an empty club rather than an error"
        )

    players = _fetch_organization_players(connection, ref, organization_id=ref.human_team_id)
    memberships = _fetch_memberships(connection, ref, organization_id=ref.human_team_id)

    rows = [
        RosterRow(
            player_id=int(row["player_id"]),
            first_name=_text(row["first_name"]),
            last_name=_text(row["last_name"]),
            age=_number(row["age"]),
            bats=_number(row["bats"]),
            throws=_number(row["throws"]),
            uniform_number=_number(row["uniform_number"]),
            team_id=_number(row["team_id"]),
            memberships=tuple(sorted(memberships.get(int(row["player_id"]), ()))),
        )
        for row in players
    ]
    rows.sort(key=lambda row: (row.last_name or "", row.first_name or "", row.player_id))
    return tuple(rows)


def render_roster(
    ref: SnapshotRef,
    rows: Sequence[RosterRow],
    clubs: Mapping[int, Club],
    *,
    club_name: str,
    list_labels: bool = True,
    list_banner: str | None = None,
) -> str:
    """The Markdown page.

    Line one carries the club, the `sim_date` **and** the `ingest_seq`, in that order.
    The sequence is not decoration: once a date has been ingested twice, a report that
    names only the date points at a moving target, and a decision citing it cannot be
    checked afterwards (§2.3(d)).

    **Every list is broken down by club, and that is a correctness fix rather than a
    layout preference.** Rendered flat, the first run of this report announced *"Active
    roster — 213"* for a club whose active roster holds 26. The number was right — an
    organisation's seven affiliates each carry their own active list — and it read as a
    plain falsehood. A GM acting on it would have been acting on nonsense.
    """
    lines: list[str] = [
        f"# {club_name} — organisation roster",
        "",
        f"**Club** {club_name} · **Sim date** {ref.sim_date} · "
        f"**Ingest seq** {ref.ingest_seq} · **Save** `{ref.save_id}`",
        "",
        f"Rendered from the warehouse landing `({ref.save_id}, {ref.sim_date}, "
        f"{ref.ingest_seq})`. Every figure below is that snapshot and no other.",
        "",
        f"{len(rows)} players carry this organisation in `bronze_player.organization_id`. "
        "Each roster list below is broken down by the club that holds it — an "
        "organisation's affiliates each carry their own active list, so an undivided "
        "total would describe no roster that exists.",
        "",
    ]

    if list_banner is not None:
        lines.extend([f"> **{list_banner}**", ""])

    by_list = _group_by_list(rows)
    for list_id in LIST_ORDER:
        group = by_list.get(list_id, ())
        heading = LIST_LABELS[list_id] if list_labels else f"Roster list `list_id = {list_id}`"
        lines.extend(_render_group(heading, list_id, group, clubs, ref))

    unlisted = tuple(row for row in rows if not row.memberships)
    lines.extend(_render_unlisted(unlisted, clubs))
    lines.extend(_render_notes(rows))
    return "\n".join(lines).rstrip() + "\n"


def _render_group(
    label: str,
    list_id: int,
    group: Sequence[tuple[RosterRow, int]],
    clubs: Mapping[int, Club],
    ref: SnapshotRef,
) -> list[str]:
    lines = [f"## {label} — {len(group)} across the organisation", ""]
    if not group:
        lines.extend(
            [
                f"No player of this organisation holds a `list_id = {list_id}` row in this "
                "snapshot. That is the landed data, not a rendering failure.",
                "",
            ]
        )
        return lines

    by_club: dict[int, list[RosterRow]] = {}
    for row, team_id in group:
        by_club.setdefault(team_id, []).append(row)

    for team_id in sorted(by_club, key=lambda key: _club_order(key, clubs, ref)):
        members = by_club[team_id]
        lines.extend([f"### {_club_heading(team_id, clubs)} — {len(members)}", ""])
        lines.extend(_table(members, columns=("Player", "Age", "B/T", "#", "Player id")))
    return lines


def _render_unlisted(rows: Sequence[RosterRow], clubs: Mapping[int, Club]) -> list[str]:
    """The players `bronze_team_roster` cannot show, named rather than dropped."""
    lines = [f"## On the organisation's books, on no roster list — {len(rows)}", ""]
    lines.extend(
        [
            "These players carry this organisation in `bronze_player.organization_id` and "
            "hold **no** row in `bronze_team_roster`. Their absence from the roster table "
            "is by design rather than a gap — a roster-*list* table has no row to give a "
            'player who is on no list — so a query answering *"who is in this '
            'organisation"* from that table alone would miss every one of them. The club '
            "shown is their `bronze_player.team_id` assignment.",
            "",
        ]
    )
    if not rows:
        lines.extend(["None in this snapshot.", ""])
        return lines
    lines.extend(["| Player | Age | B/T | # | Club | Player id |", "|---|---|---|---|---|---|"])
    for row in rows:
        club = ABSENT if row.team_id is None else _club_abbr(row.team_id, clubs)
        lines.append(
            f"| {row.display_name} | {_cell(row.age)} | {_handedness(row)} | "
            f"{_cell(row.uniform_number)} | {club} | {row.player_id} |"
        )
    lines.append("")
    return lines


def _table(rows: Sequence[RosterRow], *, columns: Sequence[str]) -> list[str]:
    lines = [f"| {' | '.join(columns)} |", f"|{'---|' * len(columns)}"]
    for row in rows:
        lines.append(
            f"| {row.display_name} | {_cell(row.age)} | {_handedness(row)} | "
            f"{_cell(row.uniform_number)} | {row.player_id} |"
        )
    lines.append("")
    return lines


def _club_order(team_id: int, clubs: Mapping[int, Club], ref: SnapshotRef) -> tuple[int, int, str]:
    """The human club first, then by level, then by abbreviation.

    A club the landing does not name sorts last rather than crashing the sort: an
    unresolvable id is a data question, not a reason to withhold the whole page.
    """
    club = clubs.get(team_id)
    first = 0 if team_id == ref.human_team_id else 1
    if club is None:
        return (first, 1 << 30, str(team_id))
    return (first, club.level, club.abbr)


def _club_heading(team_id: int, clubs: Mapping[int, Club]) -> str:
    club = clubs.get(team_id)
    if club is None:
        return f"team {team_id}"
    return f"{club.name} ({club.abbr})" if club.name else club.abbr


def _club_abbr(team_id: int, clubs: Mapping[int, Club]) -> str:
    club = clubs.get(team_id)
    return club.abbr if club is not None else str(team_id)


def _render_notes(rows: Sequence[RosterRow]) -> list[str]:
    """What the page is not showing, and why. The GM prices a gap it can see.

    The request's second desired outcome is *"the GM knows what it is not seeing"*, and a
    roster with a silently missing column serves the opposite. Position is the one that
    bites: the scope asked for it and `players.dat` does not yield it exactly yet.

    **Every number here is computed from `rows`, and that is not a style choice.** This
    section used to state *"Measured, 935 players span two clubs this way"* — a figure
    lifted from the probe save's export, wrong for this landing by roughly 27x, printed in
    the `Measured` register this project reserves for verified numbers, and sitting four
    sections under the page's own promise that *"every figure below is that snapshot and
    no other."* A page that contradicts its own provenance line is worse than one that
    omits the detail, so the detail is now derived rather than remembered.
    """
    spanning = sum(1 for row in rows if len({team for team, _ in row.memberships}) > 1)
    return [
        "## What this page does not show",
        "",
        "- **Position.** Not landed. `players.dat`'s role byte decodes exactly only "
        "within fixed-shape groups whose shape rule is not derived, and the closer role "
        "is not stored in it at all, so landing it would mean landing it at roughly 97% "
        "— a confidently wrong position on one player in thirty. `field_map.toml` records "
        "how far the decode got.",
        "- **Every rating.** Withheld by ADR 0012 and enforced by `contracts/policy.py`, "
        "not by this module's restraint.",
        "- **Win-loss records and the standings.** Not landed by any walker: the standings "
        "region is not in `teams.dat`, and the `world.dat` walk reached division "
        "membership and the league calendar rather than team records.",
        f"- **A `{ABSENT}` in any cell** means the save did not carry that field for that "
        "player — structural absence, never a zero and never a guess.",
        "",
        f"{spanning} of this organisation's {len(rows)} players appear under more than one "
        "club above, because they hold roster rows at more than one: a 40-man prospect "
        "assigned to an affiliate sits on that affiliate's assignment list and on the "
        "parent club's secondary list at once. The duplication is the grain, not a defect.",
        "",
    ]


def _group_by_list(
    rows: Sequence[RosterRow],
) -> dict[int, list[tuple[RosterRow, int]]]:
    """Players by `list_id`, carrying the club each membership sits at."""
    grouped: dict[int, list[tuple[RosterRow, int]]] = {}
    for row in rows:
        for team_id, list_id in row.memberships:
            grouped.setdefault(list_id, []).append((row, team_id))
    return grouped


def _fetch_organization_players(
    connection: Connection[DictCursor],
    ref: SnapshotRef,
    *,
    organization_id: int,
) -> list[Mapping[str, Any]]:
    """The organisation's players, names already resolved through the snapshot's own table.

    The name join is `LEFT` and is pinned to the **same** landing on both sides. `names.dat`
    is a fixed-size, per-save-populated table (scope SD-10): the same index resolves to
    different strings in different saves, so joining across snapshots would produce
    confident, wrong names.
    """
    player = quote_ident("bronze_player")
    name = quote_ident("bronze_name")
    wanted = ("player_id", "age", "bats", "throws", "uniform_number", "team_id", "organization_id")
    selected = ", ".join(f"p.{quote_ident(column)}" for column in wanted)
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {selected}, "
            f"fn.{quote_ident('name_text')} AS {quote_ident('first_name')}, "
            f"ln.{quote_ident('name_text')} AS {quote_ident('last_name')} "
            f"FROM {player} p "
            f"LEFT JOIN {name} fn ON {_name_join('fn', 'first_name_index')} "
            f"LEFT JOIN {name} ln ON {_name_join('ln', 'last_name_index')} "
            f"WHERE p.{quote_ident('save_id')} = %s "
            f"AND p.{quote_ident('sim_date')} = %s "
            f"AND p.{quote_ident('ingest_seq')} = %s "
            f"AND p.{quote_ident('organization_id')} = %s",
            (SINGLE_NAME_SPACE, SINGLE_NAME_SPACE, *ref.triple, organization_id),
        )
        return list(cursor.fetchall())


def name_join_predicate(alias: str, index_column: str) -> str:
    """The join binding **every** column of `bronze_name`'s declared key.

    Exposed so an offline test can assert the predicate names the whole key — the failure
    it guards has no offline signal otherwise, and was measured rather than imagined: with
    `name_space` omitted, a second space in the table pairs every first name with every
    last name, and a 226-player organisation comes back as 904 rows under fabricated names.

    `tables.toml` pre-registers exactly this. It keeps `name_space` in the key *"even
    though ONE space was measured … while the wrong key would collide two spaces
    silently"* — so a report joining on four of five columns is written against the one
    assumption the declaration refuses to make.
    """
    return _name_join(alias, index_column)


def _name_join(alias: str, index_column: str) -> str:
    parts = [
        f"{alias}.{quote_ident(column)} = p.{quote_ident(column)}"
        for column in ("save_id", "sim_date", "ingest_seq")
    ]
    # Bound, not interpolated — the value is data even though it is a constant today.
    parts.append(f"{alias}.{quote_ident('name_space')} = %s")
    parts.append(f"{alias}.{quote_ident('name_index')} = p.{quote_ident(index_column)}")
    return " AND ".join(parts)


def _fetch_memberships(
    connection: Connection[DictCursor],
    ref: SnapshotRef,
    *,
    organization_id: int,
) -> dict[int, list[tuple[int, int]]]:
    """`player_id` to its `(team_id, list_id)` rows, for this organisation's players only.

    Filtered by joining back to `bronze_player.organization_id` rather than by the roster
    row's own `team_id`: a list-3 row sits at the *organisation's* club while a list-1 row
    sits at the affiliate, so filtering on the roster table's `team_id` would drop half the
    memberships of every prospect.
    """
    roster = quote_ident("bronze_team_roster")
    player = quote_ident("bronze_player")
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT r.{quote_ident('team_id')}, r.{quote_ident('player_id')}, "
            f"r.{quote_ident('list_id')} "
            f"FROM {roster} r "
            f"JOIN {player} p ON p.{quote_ident('save_id')} = r.{quote_ident('save_id')} "
            f"AND p.{quote_ident('sim_date')} = r.{quote_ident('sim_date')} "
            f"AND p.{quote_ident('ingest_seq')} = r.{quote_ident('ingest_seq')} "
            f"AND p.{quote_ident('player_id')} = r.{quote_ident('player_id')} "
            f"WHERE r.{quote_ident('save_id')} = %s "
            f"AND r.{quote_ident('sim_date')} = %s "
            f"AND r.{quote_ident('ingest_seq')} = %s "
            f"AND p.{quote_ident('organization_id')} = %s",
            (*ref.triple, organization_id),
        )
        rows = list(cursor.fetchall())

    memberships: dict[int, list[tuple[int, int]]] = {}
    for row in rows:
        memberships.setdefault(int(row["player_id"]), []).append(
            (int(row["team_id"]), int(row["list_id"]))
        )
    return memberships


def fetch_clubs(connection: Connection[DictCursor], ref: SnapshotRef) -> dict[int, Club]:
    """Every club of the landing, by `team_id`.

    The whole landing rather than the organisation's clubs alone: a list row may name a
    club outside the organisation, and rendering a bare integer where every other row
    carries a name reads as a rendering bug rather than as the data.

    `city` is nullable by design — 26 of 259 records carry no city string — so the display
    name is assembled from the parts that exist rather than formatted from all of them.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {column_list(('team_id', 'abbr', 'city', 'nickname', 'level'))} "
            f"FROM {quote_ident('bronze_team')} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            ref.triple,
        )
        rows = list(cursor.fetchall())
    return {
        int(row["team_id"]): Club(
            team_id=int(row["team_id"]),
            abbr=str(row["abbr"]),
            name=_assemble_name(row["city"], row["nickname"]),
            level=int(row["level"]),
        )
        for row in rows
    }


def _assemble_name(city: Any, nickname: Any) -> str:
    parts = [str(part) for part in (city, nickname) if part]
    return " ".join(parts)


def club_display_name(clubs: Mapping[int, Club], team_id: int | None) -> str:
    """`City Nickname` for one club, falling back through what actually exists.

    Pure over the already-fetched map rather than a second query — and therefore
    exercisable offline, which a function that opened a connection would not be. 26 of 259
    records carry no city string (Phase 5), so every fallback here is a real case: a club
    with no city renders as its nickname, and one the landing does not name at all renders
    as its id rather than as `None`.
    """
    if team_id is None:
        return "unknown club"
    club = clubs.get(team_id)
    if club is None:
        return f"team {team_id}"
    return club.name or club.abbr or f"team {team_id}"


def _handedness(row: RosterRow) -> str:
    """`B/T` as two letters, or the absence marker on either side.

    An unmapped integer renders as itself rather than as a letter. The mapping is
    `verified` against the export on every row today; if a game patch ever introduced a
    fourth value, showing `4` is honest and showing `R` is a confidently wrong fact about
    a player the GM is about to make a decision on.
    """
    bats = BATS_LABELS.get(row.bats, str(row.bats)) if row.bats is not None else ABSENT
    throws = THROWS_LABELS.get(row.throws, str(row.throws)) if row.throws is not None else ABSENT
    return f"{bats}/{throws}"


def _cell(value: int | None) -> str:
    return ABSENT if value is None else str(value)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> int | None:
    return None if value is None else int(value)
