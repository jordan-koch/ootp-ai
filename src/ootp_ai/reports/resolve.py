"""Which snapshot a report renders from, and where it writes.

Separated from the reports themselves because **this is the seam an incremental
warehouse turns on**. Bronze is append-only across two axes at once (ADR 0021): a new
in-game date, and a new `ingest_seq` within one date when the operator acts without
simming. A report that hardcoded "the latest rows" would silently re-point at a
different game state every time either axis moved, and a `gm/decisions/` record citing
it would stop being checkable.

So resolution is explicit and it is stated on the page:

* **A caller may name a `sim_date`.** Absent one, the most recent landed date for that
  save is used — convenient, and never guessed at silently, because the resolved triple
  is printed on line one of every report.
* **Within a date, `max(ingest_seq)` wins.** §2.3(d) of the plan: *"a query or report
  that omits `ingest_seq` reads an ambiguous grain once any date has been ingested
  twice."*

The resolved triple then partitions the output path, so re-rendering the same triple is
idempotent while a new date or a new sequence writes a new directory beside the old one
rather than over it. That is what makes the bytes the GM actually read still be on disk
months later, which is the whole point of citing a report in a decision record.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.parser.primitives import SaveDate
from ootp_ai.warehouse.ingest_run import INGEST_RUN_TABLE, as_sql_date
from ootp_ai.warehouse.sql import quote_ident

__all__ = [
    "NoSuchSnapshot",
    "SnapshotRef",
    "landed_sim_dates",
    "report_dir",
    "resolve_snapshot",
]


class NoSuchSnapshot(Exception):  # noqa: N818
    """Nothing is landed for the save — or for the `sim_date` — a report was asked for.

    Raised rather than returning an empty report. A roster page with no players on it
    and no explanation is indistinguishable from a club that released everybody, and the
    GM has no way to tell the difference from the page alone.
    """


@dataclass(frozen=True, slots=True)
class SnapshotRef:
    """The exact landing a report rendered from, and the club that landing belongs to.

    `human_team_id` comes from the `ingest_run` row rather than from configuration: it is
    resolved from `human_managers.dat` at ingest time, so it names the club *as the save
    understood it* rather than as `.env` currently claims. The two can disagree — a `.env`
    edited between landings would — and the landed answer is the one the rows were
    filtered by.
    """

    save_id: str
    sim_date: SaveDate
    ingest_seq: int
    human_team_id: int | None

    @property
    def triple(self) -> tuple[str, str, int]:
        """The key every bronze query binds, in declaration order."""
        return (self.save_id, as_sql_date(self.sim_date), self.ingest_seq)


def landed_sim_dates(connection: Connection[DictCursor], *, save_id: str) -> list[SaveDate]:
    """Every in-game date this save has landed, oldest first.

    Exposed rather than kept private because "what does the warehouse hold for this
    universe" is the question anyone reaches for the moment a second snapshot exists, and
    answering it from the `ingest_run` table beats answering it from a directory listing.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT DISTINCT {quote_ident('sim_date')} "
            f"FROM {quote_ident(INGEST_RUN_TABLE)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"ORDER BY {quote_ident('sim_date')}",
            (save_id,),
        )
        rows = list(cursor.fetchall())
    return [_as_save_date(row["sim_date"]) for row in rows]


def resolve_snapshot(
    connection: Connection[DictCursor],
    *,
    save_id: str,
    sim_date: SaveDate | None = None,
) -> SnapshotRef:
    """The landing a report should render, as an explicit triple.

    Args:
        save_id: the universe. Never inferred — two saves can hold the same `sim_date`.
        sim_date: the in-game date, or `None` for the most recent one landed.

    Raises:
        NoSuchSnapshot: naming what was asked for and what the warehouse holds instead.
    """
    row = _latest_run(connection, save_id=save_id, sim_date=sim_date)
    if row is None:
        raise NoSuchSnapshot(_nothing_landed_message(connection, save_id, sim_date))
    return SnapshotRef(
        save_id=save_id,
        sim_date=_as_save_date(row["sim_date"]),
        ingest_seq=int(row["ingest_seq"]),
        # NULL is a real answer here: `human_manager_team_id` is nullable, and a save with
        # no human manager is not a save whose manager is club 0.
        human_team_id=None if row["human_team_id"] is None else int(row["human_team_id"]),
    )


def report_dir(output_root: Path, ref: SnapshotRef) -> Path:
    """`<output_root>/<save_id>/<sim_date>/<ingest_seq>/`, not created.

    Partitioned by the whole triple so a re-render of one snapshot cannot overwrite
    another's. `save_id` is normalised at config time to `[A-Za-z0-9_-]`, which is what
    makes it safe to put in a path at all — it can carry neither a separator nor a drive
    letter (`config.to_save_id`).
    """
    return output_root / ref.save_id / str(ref.sim_date) / str(ref.ingest_seq)


def _latest_run(
    connection: Connection[DictCursor],
    *,
    save_id: str,
    sim_date: SaveDate | None,
) -> dict[str, Any] | None:
    """The highest `ingest_seq` for the requested date, or for the most recent date.

    One statement for both cases rather than two: ordering by `(sim_date, ingest_seq)`
    descending and taking the first row answers "latest snapshot of this save", and adding
    the date predicate narrows it to "latest attempt at this date" without changing the
    shape of the result.
    """
    where = [f"{quote_ident('save_id')} = %s"]
    values: list[object] = [save_id]
    if sim_date is not None:
        where.append(f"{quote_ident('sim_date')} = %s")
        values.append(as_sql_date(sim_date))

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {quote_ident('sim_date')}, {quote_ident('ingest_seq')}, "
            f"{quote_ident('human_team_id')} "
            f"FROM {quote_ident(INGEST_RUN_TABLE)} "
            f"WHERE {' AND '.join(where)} "
            f"ORDER BY {quote_ident('sim_date')} DESC, {quote_ident('ingest_seq')} DESC "
            "LIMIT 1",
            tuple(values),
        )
        return cursor.fetchone()


def _nothing_landed_message(
    connection: Connection[DictCursor], save_id: str, sim_date: SaveDate | None
) -> str:
    """Say what the warehouse *does* hold, so the refusal is actionable.

    A bare "no snapshot found" sends the reader to check `.env`, the loader and the
    database in turn. Naming the landed dates usually identifies the mistake on sight —
    a typo'd `save_id`, or a date that was never ingested.
    """
    available = landed_sim_dates(connection, save_id=save_id)
    if not available:
        # The invocation is spelled out rather than imported from
        # `ingest/__main__.py`'s `INVOCATION`: importing an entry point from a library
        # module to build an error string couples the two the wrong way round. The
        # literal is duplicated on purpose and `tests/test_ingest_command.py` reads the
        # constant and asserts this file carries it, so the two cannot drift apart
        # silently — which they did, for two phases, while this line advised running a
        # command that did not exist.
        return (
            f"no landing exists for save {save_id!r}. The warehouse holds no ingest_run "
            "row for that universe at any date — run "
            f"`uv run python -m ootp_ai.ingest land --save-id {save_id}` before rendering"
        )
    dates = ", ".join(str(date) for date in available)
    return (
        f"save {save_id!r} has no landing at sim_date {sim_date}. It has landed at: {dates}. "
        "A report renders from a snapshot that exists; it does not interpolate one"
    )


def _as_save_date(value: Any) -> SaveDate:
    """A driver-returned `datetime.date` as the save's own date type."""
    return SaveDate(day=value.day, month=value.month, year=value.year)
