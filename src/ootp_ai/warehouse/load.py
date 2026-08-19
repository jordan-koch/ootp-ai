"""Bronze landing — 1:1 with what the walkers read, in one transaction, keyed by declaration.

`.claude/agents/data-engineer.md`: bronze is *"1:1 with parser output — typing, casing and
deduplication only. No joins, no filtering, no semantic renaming."* Everything below
follows from that sentence.

**Everything the walk yields lands.** Every team record including every minor-league club,
every framed player, every name entry, every calendar event including the ones marked
deleted. The organisation filter lives in the report layer (Decisions §7): a walk that
dropped the deleted calendar rows would return 566 and look perfectly consistent, and a
bronze that landed only Boston could never answer *"who else is available"*.

Populations are stated in `contracts/tables.toml`'s coverage statements and deliberately
not repeated here. They differ per save — 259 clubs and 18,077 players on a probe against
337 and 22,046 in the managed league — and a second copy of a number that varies is a copy
that will end up describing the development target and not the club we manage.

**Structural absence lands as NULL, never zero.** A club that no division array names is
absent from `bronze_division_team` rather than sitting in division zero; an undecoded
record tail lands `historical_id` NULL while a fictional player lands `""`, because those
are different facts and collapsing them would turn *"we did not read this"* into *"this
player has no real-world counterpart"*.

## The declaration is the column list — this module has no second copy

Every row a builder yields is checked against the declared column set for its table
**before it is bound**, and a row that names a column the declaration does not, or omits
one it does, refuses. That is the tie the Phase 8a panel recorded as missing (CF22):
before it, nothing connected a declared column set to the parser record it claims to be
1:1 with, so adding a column to `tables.toml` and forgetting the loader landed a silent
NULL, and renaming a parser field landed a silent nothing. Now either fails loudly, on the
first row, naming both sides.

The universal triple — `save_id`, `sim_date`, `ingest_seq` — is supplied centrally and is
the only thing a builder does not produce. Everything else, including `bronze_name`'s
`name_space` discriminator, comes from the builder, so "which columns are ours" is not a
judgment call made per column.

## One transaction, and the run row claimed first

The whole landing is one transaction: a snapshot whose teams landed and whose players
raised would leave the warehouse holding half a universe under a key claiming to be
whole. The `ingest_run` row is inserted **first**, so a colliding load fails on one small
insert rather than part-way through a quarter of a million name rows.

Its `table_row_counts` are written from the counts the builders produced, and every table
is then **counted back out of the schema** inside the same transaction and compared. A
disagreement rolls the whole thing back rather than committing a provenance row that
misdescribes its own landing.

That read-back is the point, and it was nearly not one: comparing `executemany`'s return
value to `len(rows)` compares two derivations of the same Python list and can only fire on
a driver anomaly. Eight primary-key-prefix `COUNT(*)`s against a landing that already does
tens of round trips cost nothing, and they make `table_row_counts` an answer rather than a
restatement — which matters because Phase 9's cost harness and Phase 11's catalog are both
specified to read that column for the rest of the project's life.

## Contention loses a retry, not a landing

The whole landing is one transaction over ~300,000 rows, so a second writer touching the
same tables can deadlock it. Measured during review: two concurrent loaders deadlock
deterministically, and `FOR UPDATE` does not prevent it (see `ingest_run.py`). A deadlock
rolls everything back, which is exactly what makes retrying safe — nothing was committed —
so `land_snapshot` retries a bounded number of times, re-allocating the sequence each time
because the winner may have taken the one this attempt intended. `IngestRunExists` is
never retried: that refusal is AC10's contract, not contention.

## Nothing here deletes, updates, or overwrites

There is no `DELETE` and no `UPDATE` path in this module, deliberately. Append-only is the
property that makes the pre-action and post-action states of one sim date both
retrievable, and a delete helper written "just for tests" is how that property quietly
stops being true. A test that needs to clean up after itself writes its own statement and
is visible doing it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import replace
from typing import Any, Final

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.contracts.loader import Contracts, Table, load_contracts
from ootp_ai.ingest import IngestRun, ParsedSnapshot
from ootp_ai.warehouse.ddl import create_table_statement
from ootp_ai.warehouse.ingest_run import (
    INGEST_RUN_TABLE,
    LOCK_ERRORS,
    as_sql_date,
    claim_ingest_run,
    ingest_run_values,
    next_ingest_seq,
    nullable_sql_date,
)
from ootp_ai.warehouse.sql import column_list, quote_ident

__all__ = [
    "FIELD_LABEL_TABLE",
    "LANDING_ATTEMPTS",
    "PROVENANCE_COLUMNS",
    "ConcurrentLandingError",
    "LoadError",
    "ensure_tables",
    "land_snapshot",
    "landed_tables",
    "table_digest",
]

FIELD_LABEL_TABLE: Final = "bronze_field_label"

#: Supplied by the loader on every row of every table: the universe, the in-game date, and
#: which attempt at that date. Plan §2.3(d), and the leading three columns of every key.
PROVENANCE_COLUMNS: Final = ("save_id", "sim_date", "ingest_seq")

#: `teams.dat` writes exactly three ARGB colours per club. Asserted rather than sliced,
#: because a club with two would otherwise land the third as whatever came next.
_TEAM_COLOR_COUNT: Final = 3

#: The single literal `bronze_name.name_space` takes. One index space was measured; the
#: discriminator stays because the declared key is correct under both outcomes and costs
#: one column, while the wrong key would collide two spaces with nothing raised.
_NAME_SPACE: Final = "all"

#: Rows per `executemany`. Large enough that 264,095 name rows take tens of round trips
#: rather than thousands, small enough that the packet stays far under MySQL's default
#: `max_allowed_packet` — a limit whose failure mode is an aborted connection mid-landing.
_CHUNK_ROWS: Final = 5_000

#: How many times a landing re-tries after losing a deadlock. Bounded rather than
#: open-ended: contention that survives three attempts is a second loader running
#: continuously, which is an operational fact the operator should see rather than a blip to
#: absorb.
LANDING_ATTEMPTS: Final = 3


class LoadError(RuntimeError):
    """A landing cannot proceed: the declaration and the parse disagree about a table."""


class ConcurrentLandingError(RuntimeError):
    """Another loader held the rows this landing needed, for every attempt.

    Deliberately **not** `IngestRunExists`. That one means *this snapshot is already in the
    warehouse* and is an answer; this one means *somebody else is writing right now* and is
    a retry that ran out. Telling an operator the first when the second is true sends them
    looking for a landing that never happened.
    """


# ── the schema ───────────────────────────────────────────────────────────────


def landed_tables(connection: Connection[DictCursor]) -> tuple[str, ...]:
    """Every table name in the connected schema, sorted. The acceptance reads this."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME AS name FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME"
        )
        return tuple(str(row["name"]) for row in cursor.fetchall())


def ensure_tables(
    connection: Connection[DictCursor], contracts: Contracts | None = None
) -> tuple[str, ...]:
    """Create any declared table the schema is missing. Returns the ones created.

    Creates rather than replaces: an existing table is left exactly as it is, because
    dropping one would destroy landed rows a `gm/decisions/` record may cite. A table whose
    *shape* has drifted from the declaration is therefore not repaired here — that is a
    migration, and a migration is a decision somebody makes in the open.
    """
    declaration = load_contracts() if contracts is None else contracts
    existing = set(landed_tables(connection))
    created: list[str] = []
    with connection.cursor() as cursor:
        for table in declaration.tables:
            if table.name in existing:
                continue
            cursor.execute(create_table_statement(table))
            created.append(table.name)
    connection.commit()
    return tuple(created)


# ── landing ──────────────────────────────────────────────────────────────────


def land_snapshot(
    connection: Connection[DictCursor],
    parsed: ParsedSnapshot,
    *,
    ingest_seq: int | None = None,
    contracts: Contracts | None = None,
) -> IngestRun:
    """Land one parsed snapshot into bronze, and return the run that describes it.

    `ingest_seq` decides which of the two AC10 operations this is, and the choice is the
    caller's because only the caller knows whether a durable snapshot is on disk:

    * **An integer claims exactly that sequence**, and refuses with `IngestRunExists` if it
      is already landed. Pass `parsed.run.ingest_seq` — the sequence the snapshot
      directory itself carries — whenever the snapshot is the artifact you want the row to
      point at, which keeps the two stores naming the same attempt.
    * **`None` allocates the next sequence from the warehouse** inside this transaction.
      That is the right call when the snapshot is transient — a parse into a temporary
      directory always allocates `1` on the filesystem side, and landing that number twice
      would collide with an unrelated earlier landing.

    The returned run carries the sequence that was actually written and the row counts that
    actually landed, so a caller never has to assume either.

    Raises:
        IngestRunExists: an explicit `ingest_seq` is already landed.
        ConcurrentLandingError: another loader held these rows for every attempt.
        LoadError: a builder and the declaration disagree about a table's columns, or a
            table holds a different number of rows than the run row claims.
    """
    declaration = load_contracts() if contracts is None else contracts
    # Built once, outside the retry: it is the expensive half and it cannot be affected by
    # anything another connection does.
    rows_by_table = _build_rows(declaration, parsed)
    counts = {name: len(rows) for name, rows in rows_by_table.items()}
    counts[INGEST_RUN_TABLE] = 1

    last: Exception | None = None
    for _attempt in range(LANDING_ATTEMPTS):
        try:
            return _land_once(
                connection, declaration, parsed, rows_by_table, counts, ingest_seq=ingest_seq
            )
        except pymysql.err.OperationalError as error:
            # A deadlock rolls the whole transaction back, so there is nothing to undo and
            # nothing half-landed. The sequence is re-allocated on the next attempt because
            # the loader that won may have taken the one this attempt intended.
            if not error.args or error.args[0] not in LOCK_ERRORS:
                raise
            last = error
    raise ConcurrentLandingError(
        f"{parsed.run.save_id} at {parsed.run.sim_date} lost a lock race on all "
        f"{LANDING_ATTEMPTS} attempts ({last}). Nothing was committed. Another loader is "
        "writing these tables — this is not the same thing as the snapshot already being "
        "landed, which refuses immediately and by name"
    ) from last


def _land_once(
    connection: Connection[DictCursor],
    declaration: Contracts,
    parsed: ParsedSnapshot,
    rows_by_table: Mapping[str, Sequence[Mapping[str, object]]],
    counts: Mapping[str, int],
    *,
    ingest_seq: int | None,
) -> IngestRun:
    """One attempt at the landing transaction. All of it, or none of it."""
    connection.begin()
    try:
        with connection.cursor() as cursor:
            seq = (
                next_ingest_seq(cursor, parsed.run.save_id, parsed.run.sim_date)
                if ingest_seq is None
                else ingest_seq
            )
            run = replace(parsed.run, ingest_seq=seq, row_counts=dict(counts))
            claim_ingest_run(
                cursor,
                declaration.table(INGEST_RUN_TABLE),
                ingest_run_values(run, ingest_seq=seq),
            )
            for name, rows in rows_by_table.items():
                _write_table(cursor, declaration.table(name), rows, run=run)
            _check_counts(cursor, declaration, run, counts)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return run


def _check_counts(
    cursor: Any, declaration: Contracts, run: IngestRun, counts: Mapping[str, int]
) -> None:
    """Count every declared table back out of the schema and compare, before committing.

    Read back rather than restated. `executemany`'s return value and `len(rows)` derive
    from the same list, so comparing them proves only that the driver counted; a
    `COUNT(*)` over the landed triple is the only version of this check that could
    disagree with the builder. It covers `ingest_run` itself too, which is otherwise the
    one row whose count nothing verifies.
    """
    sim_date = as_sql_date(run.sim_date)
    for table in declaration.tables:
        # Every identifier is quoted; all three filter values are bound. The predicate is
        # the primary key's leading prefix, so this is an index range scan per table.
        cursor.execute(
            f"SELECT COUNT(*) AS landed FROM {quote_ident(table.name)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            (run.save_id, sim_date, run.ingest_seq),
        )
        row = cursor.fetchone()
        landed = 0 if row is None else int(row["landed"])
        expected = counts.get(table.name, 0)
        if landed != expected:
            raise LoadError(
                f"{table.name} holds {landed} rows for this landing while the ingest_run "
                f"row claims {expected}. The provenance record would misdescribe its own "
                "landing, so nothing is committed"
            )


def _build_rows(
    contracts: Contracts, parsed: ParsedSnapshot
) -> dict[str, list[Mapping[str, object]]]:
    """Every bronze row for this snapshot, by table, in declaration order.

    Built before the transaction opens. A builder that raises should do so with no lock
    held and no row written, and materialising the rows is also what lets the run row carry
    counts that are checked against reality rather than reported by it.
    """
    built = {
        "bronze_team": list(_team_rows(parsed)),
        "bronze_player": list(_player_rows(parsed)),
        "bronze_team_roster": list(_roster_rows(parsed)),
        "bronze_name": list(_name_rows(parsed)),
        "bronze_division_team": list(_division_rows(parsed)),
        "bronze_league_event": list(_event_rows(parsed)),
        FIELD_LABEL_TABLE: list(_field_label_rows(contracts)),
    }
    declared = {table.name for table in contracts.tables}
    unbuilt = sorted(declared - set(built) - {INGEST_RUN_TABLE})
    if unbuilt:
        raise LoadError(
            f"the declaration names tables {unbuilt} that this loader does not build. A "
            "declared table nobody fills is an empty table that looks landed"
        )
    return built


def _write_table(
    cursor: Any, table: Table, rows: Sequence[Mapping[str, object]], *, run: IngestRun
) -> None:
    """Bind and insert one table's rows, checking each against the declared columns.

    Returns nothing on purpose. What was actually landed is established by `_check_counts`
    reading the schema back, not by trusting a driver's affected-row tally.
    """
    declared = tuple(column.name for column in table.columns)
    expected = frozenset(declared) - frozenset(PROVENANCE_COLUMNS)
    provenance: dict[str, object] = {
        "save_id": run.save_id,
        "sim_date": as_sql_date(run.sim_date),
        "ingest_seq": run.ingest_seq,
    }

    payload: list[tuple[object, ...]] = []
    for index, row in enumerate(rows):
        if row.keys() != expected:
            raise LoadError(
                f"{table.name} row {index} carries {sorted(row)} against declared "
                f"{sorted(expected)}. Missing: {sorted(expected - row.keys())}. "
                f"Not declared: {sorted(row.keys() - expected)}. Bronze is 1:1 with the "
                "walker, and the declaration is what says which columns that means"
            )
        merged = {**provenance, **row}
        payload.append(tuple(merged[name] for name in declared))

    if not payload:
        return

    # Every identifier goes through `quote_ident`; every value is a bound placeholder.
    statement = (
        f"INSERT INTO {quote_ident(table.name)} ({column_list(declared)}) "
        f"VALUES ({', '.join(['%s'] * len(declared))})"
    )
    for start in range(0, len(payload), _CHUNK_ROWS):
        cursor.executemany(statement, payload[start : start + _CHUNK_ROWS])


# ── the row builders, one per table, each 1:1 with its walker ────────────────


def _team_rows(parsed: ParsedSnapshot) -> Iterator[Mapping[str, object]]:
    for team in parsed.teams.teams:
        if len(team.colors) != _TEAM_COLOR_COUNT:
            raise LoadError(
                f"team {team.team_id} carries {len(team.colors)} colours; "
                f"{_TEAM_COLOR_COUNT} are declared as separate columns"
            )
        primary, secondary, tertiary = team.colors
        yield {
            "team_id": team.team_id,
            "city": team.city,
            "abbr": team.abbr,
            "nickname": team.nickname,
            "logo_filename": team.logo_filename,
            "full_name": team.full_name,
            "color_1": primary,
            "color_2": secondary,
            "color_3": tertiary,
            "city_id": team.city_id,
            "park_id": team.park_id,
            "league_id": team.league_id,
            "sub_league_id": team.sub_league_id,
            "nation_id": team.nation_id,
            "human_team": int(team.human_team),
            "level": team.level,
            # A VALUE, not structural absence: `parser/teams.py` argues the distinction,
            # and 0 here means "this club is its own parent", which 34 of them are.
            "parent_team_id": team.parent_team_id,
            "historical_id": team.historical_id,
        }


def _player_rows(parsed: ParsedSnapshot) -> Iterator[Mapping[str, object]]:
    for player in parsed.players.players:
        yield {
            "player_id": player.player_id,
            "first_name_index": player.first_name_index,
            "last_name_index": player.last_name_index,
            "date_of_birth": as_sql_date(player.date_of_birth),
            "age": player.age,
            "nation_id": player.nation_id,
            "city_of_birth_id": player.city_of_birth_id,
            "weight": player.weight,
            "height": player.height,
            "uniform_number": player.uniform_number,
            "experience": player.experience,
            "team_id": player.team_id,
            "last_team_id": player.last_team_id,
            "organization_id": player.organization_id,
            "last_organization_id": player.last_organization_id,
            "league_id": player.league_id,
            "last_league_id": player.last_league_id,
            "free_agent": int(player.free_agent),
            # `None` is "the record's tail was not decoded", which is not "right-handed".
            "bats": player.bats,
            "throws": player.throws,
            # `""` is a fictional player and NULL is an undecoded tail. Two facts, and the
            # column is nullable so landing keeps them apart.
            "historical_id": player.historical_id,
        }


def _roster_rows(parsed: ParsedSnapshot) -> Iterator[Mapping[str, object]]:
    for membership in parsed.rosters.memberships:
        yield {
            "team_id": membership.team_id,
            "player_id": membership.player_id,
            "list_id": membership.list_id,
        }


def _name_rows(parsed: ParsedSnapshot) -> Iterator[Mapping[str, object]]:
    for record in parsed.names.names:
        yield {
            "name_space": _NAME_SPACE,
            "name_index": record.index,
            "name_text": record.text,
            # Landed and withheld, which are different acts: the byte is unclassified
            # evidence (`tests/test_withheld_fields.py::LANDED_BUT_WITHHELD`), so keeping
            # it lets a later slice re-examine it as a query instead of a re-parse, while
            # `contracts/policy.py` keeps it off every page.
            "name_category": record.category,
        }


def _division_rows(parsed: ParsedSnapshot) -> Iterator[Mapping[str, object]]:
    for membership in parsed.world.divisions:
        # A club named by no division array yields nothing here. That is structural
        # absence and it is the whole reason this is a membership table rather than a
        # `division_id` column on `bronze_team` — the four All-Star sides sit in no
        # division, and a column would have had to write zero for them.
        for team_id in membership.team_ids:
            yield {
                "league_id": membership.league_id,
                "sub_league_id": membership.sub_league_id,
                "division_id": membership.division_id,
                "team_id": team_id,
            }


def _event_rows(parsed: ParsedSnapshot) -> Iterator[Mapping[str, object]]:
    for event in parsed.world.calendar:
        yield {
            "seq": event.seq,
            "league_id": event.league_id,
            "event_type": event.event_type,
            # NULLABLE, and `parser/world.py` is the reason: "a calendar record with no
            # date is structural absence", and its scanner accepts `year == 0` on purpose.
            # The strict converter belongs to key columns; using it here meant one date-less
            # event aborted a 300,000-row landing with a message about keys.
            "start_date": nullable_sql_date(event.start_date),
            "name": event.name,
            "event_over": event.event_over,
            # Every event lands, deleted included. Filtering belongs to the report: a walk
            # that dropped these would return 566 rows and look perfectly consistent.
            "deleted": event.deleted,
            "needs_human_action": event.needs_human_action,
            "real_sim_date": event.real_sim_date,
        }


def _field_label_rows(contracts: Contracts) -> Iterator[Mapping[str, object]]:
    """What we believed about every column, on the day it landed.

    Every column of every declared table, not only the ones carrying save data. A
    provenance column lands with NULL labels — it has no field-map entry because no walker
    produced it — and that NULL is itself the answer to *"where did this come from"*.

    `ingest_run` is included for the same reason: its `human_team_id` resolves from
    `human_managers.dat` and carries a real epistemic label, and a rule that skipped the
    table would drop that belief on a technicality about the table's name.
    """
    for table in contracts.tables:
        for column in table.columns:
            entry = None if column.field is None else contracts.field(column.field)
            yield {
                "table_name": table.name,
                "column_name": column.name,
                "field_name": None if entry is None else entry.name,
                "source_file": None if entry is None else entry.source,
                "category": None if entry is None else entry.category,
                "epistemic": None if entry is None else entry.epistemic,
                "validator": None if entry is None else entry.validator,
            }


# ── reading a landing back ───────────────────────────────────────────────────


def table_digest(
    connection: Connection[DictCursor],
    table: Table,
    *,
    save_id: str,
    sim_date: str,
    ingest_seq: int,
) -> str:
    """A SHA-256 over one snapshot's rows in one table, read back in declared key order.

    AC10 asks that a re-load leave *"row counts and checksums unchanged"*. This is that
    checksum, computed here rather than with `CHECKSUM TABLE`: the server's version covers
    a whole table rather than one snapshot's rows, so a second snapshot landing alongside
    would change it, which is exactly the case AC10 requires to leave the first alone.

    Ordered by the declared key so the digest describes the data and not the order InnoDB
    felt like returning it in.
    """
    columns = tuple(column.name for column in table.columns)
    with connection.cursor() as cursor:
        # Every identifier is quoted; the three filter values are bound.
        cursor.execute(
            f"SELECT {column_list(columns)} FROM {quote_ident(table.name)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s "
            f"ORDER BY {column_list(table.key)}",
            (save_id, sim_date, ingest_seq),
        )
        hasher = hashlib.sha256()
        for row in cursor.fetchall():
            hasher.update(json.dumps(row, sort_keys=True, default=str).encode("utf-8"))
    return hasher.hexdigest()
