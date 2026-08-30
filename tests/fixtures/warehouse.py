"""Landing a real snapshot into the real warehouse, and taking it back out again.

Shared by the two `gamedata` modules that need rows in MySQL — the grain guards and the
snapshot-semantics suite. It lives here rather than in a `conftest.py` so that a reader of
either module can see the landing being set up by name instead of inheriting it.

## Why the tests clean up, and why the delete lives here rather than in `src/`

`warehouse/load.py` holds no `DELETE` and no `UPDATE` path on purpose: append-only is what
makes the pre-action and post-action states of one sim date both retrievable, and a delete
helper written "just for tests" is how that property quietly stops being true. So the
statement is written here, in the tests, where it is visible — and it is scoped to exactly
the `(save_id, sim_date, ingest_seq)` the test itself landed.

Without the cleanup each run of the suite would add ~301,000 rows to the development
schema, most of them `bronze_name`, and the first ingest recorded in the phase handoff
would be buried under test data within a week.

## Why the landings allocate their sequence from the warehouse

A snapshot taken into a temporary directory always allocates `ingest_seq = 1` on the
filesystem side, because that directory is empty. Landing that number would collide with
the first ingest, which holds seq 1 legitimately. So these landings pass `ingest_seq=None`
and take the next sequence the warehouse has free — which is the operation the plan
describes for exactly this case, and which the explicit-seq path is separately tested
against in `test_snapshot_semantics.py`.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.contracts.loader import load_contracts
from ootp_ai.db import connect_warehouse
from ootp_ai.ingest import IngestRun, ParsedSnapshot, read
from ootp_ai.warehouse.ingest_run import INGEST_RUN_TABLE, as_sql_date
from ootp_ai.warehouse.load import ensure_tables, landed_tables
from ootp_ai.warehouse.load import land_snapshot as _land
from ootp_ai.warehouse.sql import quote_ident

__all__ = [
    "landed_probe",
    "purge_snapshot",
    "save_or_skip",
    "settings_or_skip",
    "warehouse_or_skip",
]


def settings_or_skip() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"cannot resolve settings: {exc}")


def save_or_skip(settings: Settings, which: str) -> SaveRef:
    """One configured save, or a skip naming which key is unset.

    A skip that says "no save" sends the reader looking at the game; a skip that names the
    key sends them to `.env`, which is where the answer is.
    """
    save = getattr(settings, which)
    if save is None:
        pytest.skip(f"settings.{which} is unset — no save to land")
    assert isinstance(save, SaveRef)
    if not save.path.is_dir():
        pytest.skip(f"settings.{which} names {save.league}, which is not on disk")
    return save


@contextmanager
def warehouse_or_skip(settings: Settings) -> Iterator[Connection[DictCursor]]:
    """An open warehouse connection with the declared tables present, or a loud skip.

    **Never a vacuous pass.** A warehouse test that silently succeeds because MySQL is
    down is worse than a red one: it reports that the grain holds without having looked.
    """
    try:
        connection = connect_warehouse(settings)
    except Exception as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"warehouse unreachable ({type(exc).__name__}: {exc})")
    try:
        ensure_tables(connection)
        yield connection
    finally:
        connection.close()


def purge_snapshot(connection: Connection[DictCursor], run: IngestRun) -> None:
    """Remove exactly the rows one landing wrote, from the tables the contract declares.

    **`ingest_run` goes first, and the order is the point.** An interruption part-way
    through then leaves bronze rows with no run row — visibly orphaned, and detectable by
    an anti-join. The other order leaves a run row describing rows that are no longer
    there, which is exactly the lying provenance record `warehouse/load.py` exists to
    prevent, and nothing would flag it.

    **Scoped to the declared tables**, not to every table on the server. Once dbt's silver
    and gold models live in this schema, a sweep over `information_schema` would either
    reach into them or raise on the first model without a `save_id` column.
    """
    declared = {table.name for table in load_contracts().tables}
    present = [name for name in landed_tables(connection) if name in declared]
    ordered = [INGEST_RUN_TABLE, *(name for name in present if name != INGEST_RUN_TABLE)]

    sim_date = as_sql_date(run.sim_date)
    with connection.cursor() as cursor:
        for name in ordered:
            if name not in present:
                continue
            # Every identifier quoted; all three values bound. Scoped to the triple this
            # test landed, so a concurrent snapshot or the first ingest is untouched.
            cursor.execute(
                f"DELETE FROM {quote_ident(name)} "
                f"WHERE {quote_ident('save_id')} = %s "
                f"AND {quote_ident('sim_date')} = %s "
                f"AND {quote_ident('ingest_seq')} = %s",
                (run.save_id, sim_date, run.ingest_seq),
            )
    connection.commit()


@contextmanager
def landed_probe(
    settings: Settings,
    connection: Connection[DictCursor],
    *,
    which: str = "probe_save",
) -> Iterator[tuple[ParsedSnapshot, IngestRun]]:
    """Snapshot a save into a temporary directory, land it, and take it back out.

    The snapshot is temporary and the landing is not: the rows are really in the
    development schema for the duration of the block, which is the only way a grain
    assertion means anything. `purge_snapshot` runs in `finally`, so a failing assertion
    still leaves the schema as it found it.

    **The read goes through `ingest.read.read_save`, which is the operator's own path.**
    The fixture used to compose the two library calls itself, so a test proved a
    composition nobody ran. `previous=None` skips the pre-flight entirely: this fixture
    exists to land, not to decide whether landing is worthwhile, and a comparison here
    would make every grain assertion depend on what the warehouse already held.
    """
    save = save_or_skip(settings, which)
    run: IngestRun | None = None
    with tempfile.TemporaryDirectory() as tmp:
        try:
            parsed = read.read_save(save, snapshot_root=Path(tmp), previous=None).parsed
            run = _land(connection, parsed)
            yield parsed, run
        finally:
            if run is not None:
                purge_snapshot(connection, run)
