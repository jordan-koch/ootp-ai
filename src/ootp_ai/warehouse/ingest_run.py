"""The `ingest_run` row: claiming a landing, and refusing one that already happened.

This module owns the one table that is a record *about* a landing rather than a fact from
a save, and with it the two operations AC10 turns on. They are different operations and
conflating them is the failure the plan pre-registered:

* **Re-landing an already-landed `(save_id, sim_date, ingest_seq)` refuses loudly.** The
  triple is immutable once written. Nothing is ever overwritten, which is what makes
  AC10's *"loading the same snapshot twice leaves row counts and checksums unchanged"*
  hold trivially rather than by comparison.
* **A *new* snapshot of an already-ingested `sim_date` allocates the next `ingest_seq`**
  and lands a fresh row set alongside its predecessor. The operator executes a GM action
  without simming and wants to prove it landed; the sim date has not moved. A key of
  `(save_id, sim_date)` alone blocks that legitimate request.

## What the allocation's locking read does and does not buy — measured, not assumed

`next_ingest_seq` runs `FOR UPDATE` inside the caller's open transaction. **It does not
serialise two allocators**, and an earlier version of this docstring claimed it did. The
claim was measured false twice: two connections that had committed nothing both allocated
`ingest_seq = 1` in 0.000 s, and a controlled two-process run showed the second
`SELECT … FOR UPDATE` returning after 0.001 s with no block at all, then failing on the
`INSERT` with a 1213 deadlock. InnoDB's gap locks are mutually compatible, so a gap lock
is not a queue.

What actually guarantees that nothing is overwritten is the **primary key** on
`(save_id, sim_date, ingest_seq)`: two allocators that pick the same sequence collide on
the insert, and one of them loses. `FOR UPDATE` still earns its place — it bounds the read
within the transaction rather than letting a repeatable-read snapshot answer from before
the statement — but it is the second line of defence here, not the first.

The consequence is handled rather than described: a colliding loader raises 1213 (deadlock)
or 1205 (lock wait timeout), which `warehouse/load.py` retries with a freshly allocated
sequence. A deadlock rollback is total, so retrying is safe precisely because nothing was
committed.

## Nothing here writes a file, and no column can hold a path

`IngestRun` has nowhere to put one (`tests/test_provenance.py`), and `source_files`
carries names, sizes, digests and header versions — never a location. `saved_games.dat`
embeds an absolute user-profile path per save and an ingest-run row is the artifact most
likely to be rendered into a catalog, so the defence is the shape rather than a filter.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.contracts.loader import Table
from ootp_ai.ingest import IngestRun
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.warehouse.sql import column_list, quote_ident

__all__ = [
    "INGEST_RUN_TABLE",
    "LOCK_ERRORS",
    "IngestRunExists",
    "as_sql_date",
    "claim_ingest_run",
    "ingest_run_values",
    "landed_max_seq",
    "latest_landing",
    "next_ingest_seq",
    "nullable_sql_date",
    "read_ingest_run",
]

INGEST_RUN_TABLE: Final = "ingest_run"

#: MySQL's duplicate-key error. Matched by number rather than by message text, which is
#: localised and version-dependent.
_DUPLICATE_ENTRY: Final = 1062

#: Deadlock (1213) and lock-wait timeout (1205). Both mean *another loader was writing the
#: same rows*, both roll the whole transaction back, and neither is a reason to lose a
#: multi-second landing — so `warehouse/load.py` retries them. Matched by number for the
#: same reason as above. **A duplicate key is deliberately not in this set**: that refusal
#: is AC10's contract and retrying it would be retrying a decision.
LOCK_ERRORS: Final = frozenset({1213, 1205})

#: The JSON columns, so the reader decodes exactly the ones the declaration says are JSON
#: rather than guessing from the value.
_JSON_COLUMNS: Final = ("source_files", "table_row_counts", "residual_bytes")


class IngestRunExists(Exception):  # noqa: N818
    """This `(save_id, sim_date, ingest_seq)` has already been landed.

    Refused rather than overwritten, exactly as `SnapshotExists` refuses on the filesystem
    side. A legitimate second look at the same in-game date is the *next* sequence.

    The `…Error` suffix ruff's N818 wants is skipped for the same reason `SnapshotExists`
    skips it: the two are one concept seen from two stores, and naming them differently
    would suggest they are not.
    """


def nullable_sql_date(value: SaveDate) -> str | None:
    """`SaveDate` as `YYYY-MM-DD`, or `None` where the record carries no date at all.

    Text rather than `datetime.date` deliberately: the text goes straight to a bound
    parameter, and `date` cannot represent the 0/0/0 a save writes for a date that does not
    apply. `SaveDate.as_date()` already draws exactly this line, so the absence test is
    delegated to it rather than restated here.

    **Structural absence lands as NULL.** `parser/world.py` is explicit that a calendar
    record with no date is absence rather than a mis-frame, so a date-less event has to have
    somewhere to go; the alternative found in review was that one such event aborted a
    300,000-row landing with a message about keys.
    """
    return None if value.as_date() is None else str(value)


def as_sql_date(value: SaveDate) -> str:
    """The same, for a **key column**, where absence is not a legal value.

    Every bronze key carries a real sim date, so a 0/0/0 reaching one would key a whole
    snapshot on a date that does not exist. That reasoning is true of key columns and only
    of key columns, which is why the nullable sibling above exists and why this is not the
    default: an earlier version applied this refusal to `start_date` and `date_of_birth`,
    neither of which is in any key.
    """
    text = nullable_sql_date(value)
    if text is None:
        raise ValueError(
            f"{value!r} is not a calendar date. A save writes 0/0/0 for a date that does "
            "not apply, and that is structural absence — it may not become a key"
        )
    return text


def next_ingest_seq(cursor: Any, save_id: str, sim_date: SaveDate) -> int:
    """The next unused sequence for `(save_id, sim_date)`, starting at 1.

    **Must be called inside the transaction that will insert the row.** `FOR UPDATE` is
    what makes it safe against a concurrent loader, and a lock taken in a transaction that
    has already committed protects nothing.
    """
    cursor.execute(
        f"SELECT COALESCE(MAX({quote_ident('ingest_seq')}), 0) AS used "
        f"FROM {quote_ident(INGEST_RUN_TABLE)} "
        f"WHERE {quote_ident('save_id')} = %s AND {quote_ident('sim_date')} = %s "
        "FOR UPDATE",
        (save_id, as_sql_date(sim_date)),
    )
    row = cursor.fetchone()
    used = 0 if row is None else int(row["used"])
    return used + 1


def latest_landing(
    connection: Connection[DictCursor],
    *,
    save_id: str,
) -> dict[str, Any] | None:
    """The save's most recent landing, JSON columns decoded. `None` if it never landed.

    Keyed on `save_id` **alone**, not on `(save_id, sim_date)`. That is what lets an
    ingest pre-flight ask *what did we last land for this save?* without first reading
    the game to learn the date — which would put a game read outside the bracket ADR
    0001's manifest diff covers. The equivalence that makes it sound is asserted in
    `tests/test_ingest_command.py`: the sim date lives in `teams.dat`'s header and
    `teams.dat` is one of the digested files, so unchanged bytes imply an unchanged date.

    "Most recent" is the highest `(sim_date, ingest_seq)`, not the latest `ingested_at`.
    Wall-clock order can disagree with league order — re-landing an older save after a
    newer one is a legitimate correction — and it is the league's date this answers about.

    A plain read with **no `FOR UPDATE`**, deliberately. See this module's docstring: the
    lock does not serialise two allocators, so taking one here would buy nothing and
    suggest a guarantee that does not exist.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM {quote_ident(INGEST_RUN_TABLE)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"ORDER BY {quote_ident('sim_date')} DESC, {quote_ident('ingest_seq')} DESC "
            "LIMIT 1",
            (save_id,),
        )
        row = cursor.fetchone()
    return None if row is None else _decode_json_columns(row)


def landed_max_seq(
    connection: Connection[DictCursor],
    *,
    save_id: str,
    sim_date: SaveDate,
) -> int:
    """The highest `ingest_seq` the warehouse holds for `(save_id, sim_date)`, or 0.

    Zero means *nothing landed at this date*, which is why the caller adds one rather
    than treating this as a sequence.

    Sits beside `next_ingest_seq` on purpose, and carries **no `FOR UPDATE`** where that
    one does. The contrast is the point: `next_ingest_seq` is an allocation and must run
    inside the inserting transaction, while this is a question asked long before any
    transaction is open — and this module's docstring records the measurement proving
    that the lock would not serialise anything even if it were taken.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COALESCE(MAX({quote_ident('ingest_seq')}), 0) AS used "
            f"FROM {quote_ident(INGEST_RUN_TABLE)} "
            f"WHERE {quote_ident('save_id')} = %s AND {quote_ident('sim_date')} = %s",
            (save_id, as_sql_date(sim_date)),
        )
        row = cursor.fetchone()
    return 0 if row is None else int(row["used"])


def ingest_run_values(run: IngestRun, *, ingest_seq: int) -> dict[str, object]:
    """The `ingest_run` row for `run`, as column name to bound value.

    The three repeating groups land as JSON rather than as a child table. A ninth table is
    one the plan never sequenced, and fixed columns would bake today's `SNAPSHOT_FILES`
    into the schema. `residual_bytes` stays **per file** because the accounting tier
    differs per file by design — strict for `names.dat`, diagnostic for `teams.dat` and
    `players.dat`, region-accounted for `world.dat` — so a summed total would make a
    strict-tier failure arithmetically indistinguishable from an expected diagnostic
    residual, and *which walker left bytes unaccounted for* would stop being answerable
    from the warehouse. Two of the four files being diagnostic makes that argument stronger,
    not weaker: `teams.dat` lands a non-zero residual on every save (2,274 managed / 1,137
    probe), so a sum would never be zero and no reader could tell which file moved.

    `ingested_at` is created tz-aware in UTC (ruff `DTZ`) and stored in a `DATETIME(6)`,
    which carries no zone: the value is UTC because it is always made that way here, and
    `TIMESTAMP` was rejected precisely because it converts on the way in and out using
    whichever session happens to be reading.
    """
    return {
        "save_id": run.save_id,
        "sim_date": as_sql_date(run.sim_date),
        "ingest_seq": ingest_seq,
        "human_team_id": run.human_team_id,
        "source_files": json.dumps(
            [
                {
                    "name": source.name,
                    "size": source.size,
                    "sha256": source.sha256,
                    "version": source.version,
                }
                for source in sorted(run.sources, key=lambda source: source.name)
            ],
            sort_keys=True,
        ),
        "table_row_counts": json.dumps(dict(run.row_counts), sort_keys=True),
        "residual_bytes": json.dumps(dict(run.residual_bytes), sort_keys=True),
        # None stays None: a run that did not measure the parse is not a run that parsed
        # in zero seconds, and the column is nullable so the difference survives landing.
        "parse_seconds": None if run.parse_seconds is None else round(run.parse_seconds, 3),
        "ingested_at": datetime.now(tz=UTC),
    }


def claim_ingest_run(cursor: Any, table: Table, values: Mapping[str, object]) -> None:
    """Insert the run row, claiming the triple, or refuse because it is already claimed.

    Called **first** in the landing transaction rather than last. Claiming the key before
    any bronze row is written means a colliding load fails on one small insert instead of
    part-way through 264,095 name rows, and the rollback has less to undo.

    Raises:
        IngestRunExists: naming the triple.
    """
    declared = tuple(column.name for column in table.columns)
    missing = [name for name in declared if name not in values]
    unknown = sorted(name for name in values if name not in declared)
    if missing or unknown:
        raise ValueError(
            f"{table.name} row does not match the declaration: missing {missing}, "
            f"unknown {unknown}. The declaration is the column list, not this module"
        )

    # Every identifier goes through `quote_ident`; every value is a bound placeholder.
    statement = (
        f"INSERT INTO {quote_ident(table.name)} ({column_list(declared)}) "
        f"VALUES ({', '.join(['%s'] * len(declared))})"
    )
    try:
        cursor.execute(statement, tuple(values[name] for name in declared))
    except pymysql.err.IntegrityError as error:
        if error.args and error.args[0] == _DUPLICATE_ENTRY:
            raise IngestRunExists(
                f"{values['save_id']} at {values['sim_date']} ingest_seq "
                f"{values['ingest_seq']} is already landed. Snapshots are immutable — a "
                "second look at the same in-game date takes the next sequence rather than "
                "overwriting the state a past decision was made from"
            ) from error
        raise


def read_ingest_run(
    connection: Connection[DictCursor],
    *,
    save_id: str,
    sim_date: SaveDate,
    ingest_seq: int,
) -> dict[str, Any] | None:
    """Read one landed run back, JSON columns decoded. `None` if it never landed.

    The row counts are read from **here** rather than from whatever the loader printed:
    the acceptance asks what the warehouse holds, and a number that only ever existed on
    stdout proves nothing about that.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM {quote_ident(INGEST_RUN_TABLE)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            (save_id, as_sql_date(sim_date), ingest_seq),
        )
        row = cursor.fetchone()
    return None if row is None else _decode_json_columns(row)


def _decode_json_columns(row: Mapping[str, Any]) -> dict[str, Any]:
    """One `ingest_run` row with its declared JSON columns turned back into objects.

    Shared by both readers rather than written twice: a caller that got a decoded
    `source_files` from one and a JSON string from the other would be holding two
    different types under one column name, and only one of them would iterate.
    """
    decoded = dict(row)
    for column in _JSON_COLUMNS:
        value = decoded.get(column)
        # PyMySQL hands a JSON column back as text; it does not decode it.
        if isinstance(value, str | bytes | bytearray):
            decoded[column] = json.loads(value)
    return decoded
