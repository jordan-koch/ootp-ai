"""The half that changes every time the league is simulated: counts, dates, freshness.

ADR 0005's rule — *does this artifact change when the league is simulated?* — is what
splits the catalog in two, and everything in this module is on the **yes** side. None of
it is tracked; it generates into the git-ignored output root beside the reports,
partitioned by the same snapshot triple, so the exact figures the GM read are still on
disk when a `gm/decisions/` record citing them is checked months later.

## Counts come from `COUNT(*)`, not from `information_schema.TABLES.TABLE_ROWS`

The plan says the generator *"reads `information_schema` for counts"*, and this module
reads `information_schema` for exactly what it can answer: **which declared tables exist**
in the connected schema. It does not take the row counts from there. `TABLE_ROWS` is an
estimate for InnoDB — sampled from index statistics and routinely wrong by a wide margin —
and a catalog that printed an estimate under a heading saying *row count* would be a
confidently wrong number on the one surface ADR 0016 gives the GM. The counts here are
`COUNT(*)` scoped to the resolved triple, which is also the only form that can answer
per-snapshot at all: `TABLE_ROWS` counts every landing the table holds.

## Coverage statements are computed, never remembered

Scope folded-in §3: *"players: 18,072 rows, active only, retired excluded, 1,920 carry an
external ID"* is worth more to a GM pricing an action than a table name, and computed from
counts it cannot go stale. The roster report was bitten by the opposite — it shipped with
two constants carried over from the probe save's export, one of them wrong for the managed
league by roughly 27x — so every figure this module emits is derived from the landing being
described and from no other.

The one the scope names explicitly is **how many players hold no roster row at all**: free
agents, draft-eligible players, international signings and the unassigned. They are the
population `bronze_team_roster` structurally cannot contain, and a GM that cannot see them
prices *"who is available"* as zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.contracts.loader import Contracts
from ootp_ai.contracts.policy import Disposition, WithheldFieldError, column_disposition
from ootp_ai.reports.resolve import SnapshotRef, landed_sim_dates
from ootp_ai.warehouse.ingest_run import read_ingest_run
from ootp_ai.warehouse.load import landed_tables
from ootp_ai.warehouse.sql import quote_ident

__all__ = [
    "COVERAGE_COLUMNS",
    "CoverageFact",
    "SourceFile",
    "TableVolume",
    "Volume",
    "check_coverage_columns_renderable",
    "fetch_volume",
]

_PLAYER_TABLE: Final = "bronze_player"
_ROSTER_TABLE: Final = "bronze_team_roster"
_TEAM_TABLE: Final = "bronze_team"
_DIVISION_TABLE: Final = "bronze_division_team"

#: Every landed column a coverage statement reads, declared so the serving gate can decide
#: it. The catalog emits counts rather than values, but a count is still a read of the
#: column, and CLAUDE.md's rule is that every landed value reaching a page routes through
#: `contracts/policy.py` — with no second path. Declaring the list is what makes that
#: assertable rather than asserted; `tests/test_catalog.py` pins it against the queries.
COVERAGE_COLUMNS: Final = (
    (_PLAYER_TABLE, "player_id"),
    (_PLAYER_TABLE, "historical_id"),
    (_ROSTER_TABLE, "player_id"),
    (_TEAM_TABLE, "team_id"),
    (_DIVISION_TABLE, "team_id"),
)


@dataclass(frozen=True, slots=True)
class TableVolume:
    """One declared table's row count for one landing, or its absence from the schema."""

    name: str
    landed: bool
    row_count: int | None


@dataclass(frozen=True, slots=True)
class CoverageFact:
    """One generated coverage statement, kept as its parts so JSON is not prose.

    `statement` is what the Markdown prints and `value` is what a machine reads. Rendering
    the sentence into JSON and asking a consumer to parse it back out is how a catalog
    stops being machine-readable while still claiming to be.
    """

    name: str
    value: int
    statement: str


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One file the parse read, as the run row accounts for it."""

    name: str
    size: int
    residual_bytes: int | None


@dataclass(frozen=True, slots=True)
class Volume:
    """Everything about one landing that a later landing will make wrong."""

    save_id: str
    sim_date: str
    ingest_seq: int
    human_team_id: int | None
    ingested_at: str | None
    parse_seconds: float | None
    landed_dates: tuple[str, ...]
    tables: tuple[TableVolume, ...]
    coverage: tuple[CoverageFact, ...]
    source_files: tuple[SourceFile, ...]

    @property
    def total_rows(self) -> int:
        return sum(table.row_count or 0 for table in self.tables)


def check_coverage_columns_renderable(contracts: Contracts) -> None:
    """Route every column a coverage statement reads through the serving gate, or refuse.

    The same posture `reports/roster.py` takes with `check_renderable`, and for the same
    reason: a column that quietly stopped being renderable would otherwise keep feeding a
    number onto the GM's page with nothing raised. A count is a weaker disclosure than a
    value, and "weaker" is not the test the policy applies.

    Raises:
        WithheldFieldError: naming the column and what the policy decided about it.
    """
    for table_name, column_name in COVERAGE_COLUMNS:
        table = contracts.table(table_name)
        decided = column_disposition(contracts, table, table.column(column_name))
        if decided is not Disposition.RENDERABLE:
            raise WithheldFieldError(
                f"the catalog's coverage statements read {table_name}.{column_name}, which "
                f"the policy rules {decided.value}. The catalog refuses rather than dropping "
                "the statement: a silently missing coverage line reads as a population of "
                "zero, which is the opposite of what it is"
            )


def fetch_volume(
    connection: Connection[DictCursor],
    contracts: Contracts,
    ref: SnapshotRef,
) -> Volume:
    """Every changing figure about one landing, read from the landing itself.

    Raises:
        WithheldFieldError: a column a coverage statement reads is not renderable.
    """
    check_coverage_columns_renderable(contracts)

    run = read_ingest_run(
        connection,
        save_id=ref.save_id,
        sim_date=ref.sim_date,
        ingest_seq=ref.ingest_seq,
    )
    present = _landed_by_this_run(connection, run)

    tables = tuple(
        TableVolume(
            name=table.name,
            landed=table.name in present,
            row_count=(_count(connection, table.name, ref) if table.name in present else None),
        )
        for table in sorted(contracts.tables, key=lambda table: table.name)
    )

    return Volume(
        save_id=ref.save_id,
        sim_date=str(ref.sim_date),
        ingest_seq=ref.ingest_seq,
        human_team_id=ref.human_team_id,
        ingested_at=_timestamp(run),
        parse_seconds=_seconds(run),
        landed_dates=tuple(str(date) for date in landed_sim_dates(connection, save_id=ref.save_id)),
        tables=tables,
        coverage=_coverage(connection, ref, present),
        source_files=_source_files(run),
    )


# ── the counts ───────────────────────────────────────────────────────────────


def _landed_by_this_run(
    connection: Connection[DictCursor], run: dict[str, Any] | None
) -> frozenset[str]:
    """Which declared tables **this landing** wrote — not which exist in the schema.

    The distinction is the project's own rule about absence, applied to itself.
    `landed_tables()` answers `TABLE_SCHEMA = DATABASE()`, which is scoped to no run at
    all, so a table created after an older landing looks present to that landing and every
    count against it comes back `0`. Measured at the Phase 11 panel with a triple the run
    row does not cover: all eight tables reported `landed=True, row_count=0`, and the page
    stated *"`bronze_player` holds **0** players"* and *"**0** players hold no roster
    row"* — structural absence rendered as a population, which is the one reading this
    project treats as worse than an error.

    The distinguishing fact is already landed. `ingest_run.table_row_counts` records what
    the run actually wrote, so membership in that mapping *is* the answer. Bronze being
    append-only makes regenerating an older landing a `--sim-date` away, so this is
    reachable rather than theoretical.

    Falls back to schema presence only when the run row is missing entirely — in which
    case nothing better exists, and a count is still preferable to refusing the page.
    """
    if run is not None:
        counts = run.get("table_row_counts")
        if isinstance(counts, dict) and counts:
            return frozenset(str(name) for name in counts)
    return frozenset(landed_tables(connection))


def _count(connection: Connection[DictCursor], table: str, ref: SnapshotRef) -> int:
    """`COUNT(*)` for one declared table, scoped to the triple. Identifier quoted."""
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM {quote_ident(table)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            ref.triple,
        )
        row = cursor.fetchone()
    return 0 if row is None else int(row["total"])


def _scalar(connection: Connection[DictCursor], sql: str, values: tuple[Any, ...]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        row = cursor.fetchone()
    return 0 if row is None else int(row["total"])


def _coverage(
    connection: Connection[DictCursor],
    ref: SnapshotRef,
    present: frozenset[str],
) -> tuple[CoverageFact, ...]:
    """The generated coverage statements, skipping any whose tables this run did not land.

    Skipping rather than reporting zero: a table this landing never wrote and a table that
    landed no rows are different facts, and this project's rule is that absence is never a
    zero. A statement that cannot be computed is simply not made — which is why `present`
    is derived from the run row rather than from the schema (`_landed_by_this_run`).
    """
    facts: list[CoverageFact] = []
    triple = ref.triple

    if _PLAYER_TABLE in present:
        players = _count(connection, _PLAYER_TABLE, ref)
        external = _scalar(
            connection,
            f"SELECT COUNT(*) AS total FROM {quote_ident(_PLAYER_TABLE)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s "
            f"AND {quote_ident('historical_id')} IS NOT NULL "
            f"AND {quote_ident('historical_id')} <> %s",
            (*triple, ""),
        )
        facts.append(
            CoverageFact(
                name="players_landed",
                value=players,
                statement=(
                    f"`{_PLAYER_TABLE}` holds **{players:,}** players for this landing — "
                    "every record the walk frames, with no filtering."
                ),
            )
        )
        facts.append(
            CoverageFact(
                name="players_with_external_id",
                value=external,
                statement=(
                    f"**{external:,}** of them carry a Lahman/BBRef `historical_id`, the "
                    "join key to public baseball data. The rest are fictional to this "
                    "universe and have no external record anywhere — structural absence, "
                    "not a gap in the parse."
                ),
            )
        )

    if _PLAYER_TABLE in present and _ROSTER_TABLE in present:
        on_a_list = _scalar(
            connection,
            f"SELECT COUNT(DISTINCT {quote_ident('player_id')}) AS total "
            f"FROM {quote_ident(_ROSTER_TABLE)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            triple,
        )
        # NOT EXISTS rather than the subtraction the plan sketches: subtracting the
        # distinct roster population assumes every roster row names a player the same
        # landing also holds, and an anti-join answers the question asked without that
        # assumption. The two agree today; only one of them keeps agreeing if it stops
        # being true, and that disagreement is itself worth surfacing.
        unlisted = _scalar(
            connection,
            f"SELECT COUNT(*) AS total FROM {quote_ident(_PLAYER_TABLE)} p "
            f"WHERE p.{quote_ident('save_id')} = %s "
            f"AND p.{quote_ident('sim_date')} = %s "
            f"AND p.{quote_ident('ingest_seq')} = %s "
            f"AND NOT EXISTS (SELECT 1 FROM {quote_ident(_ROSTER_TABLE)} r "
            f"WHERE r.{quote_ident('save_id')} = p.{quote_ident('save_id')} "
            f"AND r.{quote_ident('sim_date')} = p.{quote_ident('sim_date')} "
            f"AND r.{quote_ident('ingest_seq')} = p.{quote_ident('ingest_seq')} "
            f"AND r.{quote_ident('player_id')} = p.{quote_ident('player_id')})",
            triple,
        )
        facts.append(
            CoverageFact(
                name="players_on_a_roster_list",
                value=on_a_list,
                statement=(
                    f"**{on_a_list:,}** distinct players hold at least one row in "
                    f"`{_ROSTER_TABLE}`."
                ),
            )
        )
        facts.append(
            CoverageFact(
                name="players_on_no_roster_list",
                value=unlisted,
                statement=(
                    f"**{unlisted:,}** players hold **no** roster row at all — free "
                    "agents, draft-eligible, international and unassigned players. A "
                    'query answering *"who is available"* from '
                    f"`{_ROSTER_TABLE}` alone misses every one of them, because a "
                    "roster-*list* table has no row to give a player who is on no list."
                ),
            )
        )

    if _TEAM_TABLE in present:
        clubs = _count(connection, _TEAM_TABLE, ref)
        facts.append(
            CoverageFact(
                name="clubs_landed",
                value=clubs,
                statement=(
                    f"`{_TEAM_TABLE}` holds **{clubs:,}** clubs — every league in the "
                    "universe, not the majors alone. The organisation filter lives in the "
                    "report layer, never in bronze."
                ),
            )
        )

    if _DIVISION_TABLE in present:
        placed = _scalar(
            connection,
            f"SELECT COUNT(DISTINCT {quote_ident('team_id')}) AS total "
            f"FROM {quote_ident(_DIVISION_TABLE)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            triple,
        )
        facts.append(
            CoverageFact(
                name="clubs_placed_in_a_division",
                value=placed,
                statement=(
                    f"**{placed:,}** clubs are placed in a division. The walk reaches "
                    "MLB's six divisions only; every other league sits behind its own "
                    "unmapped block in `world.dat`, so a club missing here is unreached "
                    "rather than unaffiliated."
                ),
            )
        )

    return tuple(facts)


# ── the run row ──────────────────────────────────────────────────────────────


def _timestamp(run: dict[str, Any] | None) -> str | None:
    """`ingested_at` as text, or `None` when the run row is gone.

    Formatted from whatever the driver returned rather than re-read from a clock: this is
    freshness, and a freshness figure taken from the present moment says nothing about
    when the rows landed.
    """
    if run is None:
        return None
    value = run.get("ingested_at")
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat(sep=" ", timespec="seconds"))
    return str(value)


def _seconds(run: dict[str, Any] | None) -> float | None:
    """`parse_seconds`, via text because the column is `DECIMAL(12,3)` (AC17)."""
    if run is None:
        return None
    value = run.get("parse_seconds")
    if value is None:
        return None
    if isinstance(value, Decimal | float | int):
        return float(str(value))
    return None


def _source_files(run: dict[str, Any] | None) -> tuple[SourceFile, ...]:
    """The files the parse read, by name and size.

    **Named keys, never the whole entry.** `saved_games.dat` embeds an absolute
    user-profile path for every save (finding F19), and a provenance section that dumped a
    manifest entry wholesale would be one schema change away from publishing a username.
    Reading only `name`, `size` and the residual makes that structurally impossible rather
    than currently untrue.
    """
    if run is None:
        return ()
    sources = run.get("source_files")
    residual = run.get("residual_bytes")
    residuals: dict[str, Any] = residual if isinstance(residual, dict) else {}
    if not isinstance(sources, list):
        return ()

    files: list[SourceFile] = []
    for entry in sources:
        if not isinstance(entry, dict) or "name" not in entry:
            continue
        name = str(entry["name"])
        left = residuals.get(name)
        files.append(
            SourceFile(
                name=name,
                size=int(entry.get("size", 0)),
                residual_bytes=None if left is None else int(left),
            )
        )
    return tuple(sorted(files, key=lambda file: file.name))
