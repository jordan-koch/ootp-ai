"""`uv run python -m ootp_ai.ingest land` — the operator's write-side entry point.

The third instance of a deliberate pattern, and the first that *creates* a landing.
`reports/__main__.py` set the shape and says so — resolve settings, resolve the target
explicitly, act, print what was done — and `catalog/__main__.py` followed it. Both only
read a landing that already existed. Until this module, nothing outside `pytest` could
make one, and `README.md` documented running the test suite as the setup path.

**One verb, not three.** The library keeps its deliberate snapshot / parse / land split
for callers who want the pieces; the operator wants one act. `land` pre-flights,
snapshots, parses and lands, then prints the `(save_id, sim_date, ingest_seq)` triple —
the same three facts `reports render` prints, so a landing and a render can be tied
together in a `gm/decisions/` record afterwards.

**Every game read happens in `ingest/read.py`**, which is what lets ADR 0001's manifest
diff bracket the operator's own path rather than a composition that only ever existed
inside a test. The warehouse lookup happens out here and travels down as plain data, so
that guard never acquires a MySQL dependency.

**Nothing here creates a file.** The snapshot copy belongs to `snapshot.py`, the only
module in this package allowed to write, which is why `tests/test_read_only.py`'s
allowlist is byte-unchanged by this command rather than one entry wider.

**No absolute path reaches stdout**, ever. `saved_games.dat` embeds a user-profile path
per save and an ingest run is the record most likely to be pasted into a tracked file
(ADR 0006). A `ConfigError` on *stderr* may name the offending path, because a
misconfiguration message that does not name it is not actionable.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final, Literal

import pymysql

from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.db import connect_warehouse
from ootp_ai.ingest import (
    IngestRun,
    ParsedSnapshot,
    SnapshotDateMismatch,
    UndecodedRecords,
    parse_snapshot,
    read,
)
from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.reports.resolve import landed_sim_dates
from ootp_ai.snapshot import (
    SnapshotCorrupt,
    SnapshotExists,
    SnapshotFile,
    read_manifest,
    verify_snapshot,
)
from ootp_ai.warehouse.ingest_run import IngestRunExists, landed_max_seq, latest_landing
from ootp_ai.warehouse.load import ConcurrentLandingError, LoadError, ensure_tables, land_snapshot

#: How this command is invoked, as one string. `README.md` and
#: `reports/resolve.py`'s "nothing landed" advice both have to name a command that
#: exists, and both are prose files no import can reach — so the literal is duplicated
#: by necessity and `tests/test_ingest_command.py` reads it from here and asserts it
#: appears in both. The constant is the anti-drift device; importing it into a message
#: string would only move the duplication somewhere harder to check.
INVOCATION: Final = "uv run python -m ootp_ai.ingest land"

#: Every key `--json` always emits. Pinned here rather than in the test so the payload
#: `incremental-loading` writes its procedure against has one owner.
JSON_KEYS: Final = (
    "save_id",
    "sim_date",
    "ingest_seq",
    "verdict",
    "reason",
    "mode",
    "parse_seconds",
    "row_counts",
    "residual_bytes",
    "tables_created",
)

#: Emitted **only when the two allocators disagree** (Decision 4). Printed prose the
#: operator may not keep is not a record; a divergence that reaches the JSON is.
SEQUENCE_KEYS: Final = ("snapshot_dir_seq", "warehouse_max_seq")

#: Every value `verdict` can take, as one closed set — this is the discriminator
#: `incremental-loading` writes its procedure against, so it is typed rather than left
#: to whatever string a branch happens to produce. `unchanged` never appears on a
#: `LandingResult`: the unchanged case raises, so it reaches stdout only through the
#: refusal envelope, which is exactly why that envelope has to exist (Decision 6).
LandingVerdict = Literal["no-prior", "changed", "new-look", "from-snapshot"]

#: Refused for a reason the operator can act on, so each is caught by name and reported
#: as one line rather than a traceback. They share no base class — `SnapshotExists` and
#: friends derive from `Exception` while `LoadError` and `ConcurrentLandingError` derive
#: from `RuntimeError` — so the tuple is explicit, and a parametrised test walks it so
#: that adding a tenth without handling it fails loudly.
REFUSALS: Final = (
    SaveFormatError,
    SnapshotExists,
    SnapshotCorrupt,
    SnapshotDateMismatch,
    UndecodedRecords,
    read.SaveUnchanged,
    IngestRunExists,
    ConcurrentLandingError,
    LoadError,
)


class UnknownSave(ValueError):  # noqa: N818
    """`--save-id` named a universe `.env` does not configure.

    A distinct type rather than a bare `ValueError`, because the established convention
    maps `ValueError` to exit 1 — *the operation refused* — and this is exit 2, an argv
    or `.env` problem the operator fixes before running anything again.

    The `…Error` suffix ruff's N818 wants is skipped for the reason `SnapshotExists` and
    `IngestRunExists` skip it: this package names its refusals after the state of the
    world they found, and one exception spelled differently would read as a different
    kind of thing.
    """


@dataclass(frozen=True, slots=True)
class LandingResult:
    """What one `land` did, in the terms both output formats are built from.

    **Two sequence fields, named for where each came from.** `snapshot_dir_seq` is what
    `take_snapshot` allocated by looking at the filesystem; `warehouse_max_seq` is the
    highest the warehouse already held at this date. They are usually equal-and-one-apart
    and occasionally not — one save on this machine has a snapshot directory whose rows
    were purged — so the landed sequence is `max(snapshot_dir_seq, warehouse_max_seq + 1)`
    and a reader who needs to know which store it came from can tell.
    """

    run: IngestRun
    verdict: LandingVerdict
    mode: str
    snapshot_dir_seq: int
    warehouse_max_seq: int
    tables_created: tuple[str, ...]
    #: Why the pre-flight decided this save had moved, or `None` where no comparison was
    #: made — a first landing, a `--new-look`, or a `--from-snapshot` re-land. A verdict
    #: without a reason is a verdict the operator cannot check.
    reason: str | None = None

    @property
    def sequences_diverged(self) -> bool:
        """Whether the two allocators disagreed, in **either** direction.

        Two ways they can, and an earlier version of this only caught one:

        * **The warehouse was ahead** — the landed sequence is not the snapshot
          directory's number, so the snapshot backing this triple sits at a path that
          triple does not address, which is exactly what ADR 0021's
          snapshot-is-authoritative triage relies on.
        * **The filesystem was ahead** — the landed sequence equals the directory's
          number, so the first test is False, yet the warehouse just acquired a *gapped*
          sequence. That is the live case on this machine, where a snapshot directory
          survives a landing whose rows were purged; a later reader applying ADR 0021's
          "starting at 1" can read the gap as a lost landing.

        Accepted deliberately (Decision 4), on condition it is always *stated*.
        """
        return (
            self.run.ingest_seq != self.snapshot_dir_seq
            or self.snapshot_dir_seq != self.warehouse_max_seq + 1
        )


def main(argv: list[str] | None = None) -> int:
    """Land one save into the warehouse. Returns a process exit code.

    0 landed · 1 refused for a reason named on stderr · 2 the command, `.env`, or the
    warehouse `.env` names is wrong. Every one of the three is reached by a named
    message rather than a traceback — a first run that cannot find MySQL is the most
    likely thing to happen to a fresh clone, and it is the least useful thing to hand
    somebody as a stack trace.
    """
    args = _parser().parse_args(argv)
    try:
        settings = load_settings()
    except ConfigError as error:
        print(f"configuration: {error}", file=sys.stderr)
        return 2

    try:
        result = land(
            settings,
            save_id=args.save_id,
            new_look=args.new_look,
            from_snapshot=None if args.from_snapshot is None else Path(args.from_snapshot),
        )
    except UnknownSave as error:
        print(f"--save-id: {error}", file=sys.stderr)
        return 2
    except pymysql.err.Error as error:
        # The single likeliest failure on a fresh clone — the schema was never
        # bootstrapped, or the credentials in `.env` are wrong — and the one AC18's
        # setup walk-through runs straight into. Without this it exits on a bare
        # traceback, which is not the 0/1/2 contract this docstring promises.
        print(
            f"warehouse: {type(error).__name__}: {error}\n"
            f"The command reached no database. Check MYSQL_* in .env, that the server "
            f"is running, and that `mysql -u root -p < ops/mysql-bootstrap.sql` has been "
            f"run once on this machine. Nothing was read and nothing was landed.",
            file=sys.stderr,
        )
        return 2
    except read.SaveUnchanged as error:
        # The one refusal with a machine-readable shape. `verdict` is a discriminator
        # `incremental-loading` can branch on, and the unchanged case is the only value
        # it has that a successful landing never produces — so emitting it only on the
        # success path would promise a field the control flow makes unreachable.
        if args.json:
            print(json.dumps(_unchanged_envelope(error), indent=2, sort_keys=True))
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    except REFUSALS as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print(format_json(result) if args.json else format_result(result))
    return 0


def land(
    settings: Settings,
    *,
    save_id: str | None = None,
    snapshot_root: Path | None = None,
    new_look: bool = False,
    from_snapshot: Path | None = None,
) -> LandingResult:
    """Take one save from disk to a landed bronze snapshot.

    `save_id` defaults to the managed league — the club this front office runs — and stays
    overridable, because SD-20 sequences every filesystem-touching operation against the
    disposable Challenge-mode twin first.

    The order is deliberate. `ensure_tables` runs **before** anything is read, so a fresh
    clone with an empty schema fails on a connection rather than after a 52.4 MiB copy;
    the pre-flight runs **before** the copy, so an unchanged save costs ~40 ms and leaves
    nothing behind; and `verify_snapshot` runs after the copy, against the copy.

    Raises:
        UnknownSave: `save_id` names no configured universe.
        SaveUnchanged: the save is byte-identical to its own most recent landing.
        SaveFormatError, SnapshotExists, SnapshotCorrupt, SnapshotDateMismatch,
        UndecodedRecords, IngestRunExists, ConcurrentLandingError, LoadError: the
            refusals `main` reports by name.
    """
    root = settings.snapshot_root if snapshot_root is None else snapshot_root
    # One variable, because the two are mutually exclusive at the argparse level and a
    # pair of optionals would let a caller ask for both or neither. Resolved BEFORE the
    # connection is opened: a mistyped `--save-id` is an argv problem and must not cost a
    # round trip to MySQL to discover, or a machine whose warehouse is down would report
    # the typo as a database failure.
    if from_snapshot is not None and save_id is not None:
        raise UnknownSave(
            "--save-id cannot be combined with --from-snapshot: a snapshot's manifest "
            "already names the save it was taken from, so the two can only disagree"
        )
    target: SaveRef | Path = (
        from_snapshot if from_snapshot is not None else _resolve_save(settings, save_id)
    )

    connection = connect_warehouse(settings)
    try:
        # Captured, not printed at call time: the operator wants one block of output at
        # the end, and a table creation is part of what the run did.
        created = ensure_tables(connection)

        reason: str | None = None
        if isinstance(target, Path):
            parsed, dir_seq, mode, verdict = _reread_snapshot(target)
        else:
            save = target
            previous = None if new_look else _prior_landing(connection, save.save_id)
            try:
                reading = read.read_save(save, snapshot_root=root, previous=previous)
            except read.SaveUnchanged as unchanged:
                # Re-raised carrying what the warehouse holds. The shared function has no
                # connection by design, so only out here can the refusal name the dates.
                raise read.SaveUnchanged(
                    unchanged.save_id,
                    unchanged.sim_date,
                    unchanged.ingest_seq,
                    landed=tuple(landed_sim_dates(connection, save_id=save.save_id)),
                ) from unchanged
            parsed = reading.parsed
            dir_seq, mode, reason = reading.snapshot_dir_seq, reading.mode, reading.reason
            # `read_save` infers its verdict from `previous is None`, which cannot tell
            # "nothing was ever landed" from "the operator told us not to look". Only
            # here is the intent known, so only here can the two be told apart.
            verdict = "new-look" if new_look else reading.verdict

        # The copy is proved against its own manifest before a row is written. Called
        # here rather than inside the shared function because it reads the snapshot, not
        # the game — putting it there would muddy that function's whole claim, and would
        # add a re-digest to every `landed_probe` call on every gamedata run.
        verify_snapshot(parsed.run.snapshot.path)

        # End the read view opened by `_prior_landing` before asking for the sequence.
        # InnoDB defaults to REPEATABLE READ and the copy above takes seconds, so without
        # this the sequence would be decided from a snapshot of `ingest_run` taken before
        # the save was even read — and a landing that committed in between would be
        # invisible to the arithmetic that is supposed to step over it.
        connection.commit()
        warehouse_max = landed_max_seq(
            connection, save_id=parsed.run.save_id, sim_date=parsed.run.sim_date
        )
        # Reconciled rather than chosen. Against an accurate committed maximum the result
        # is always greater than it, so it cannot collide with a landing already there —
        # but the sequence is passed EXPLICITLY, which forfeits `land_snapshot`'s
        # per-attempt re-allocation (`load.py:232-250` only re-allocates on the `None`
        # branch). So a second writer that commits between the read above and the insert
        # below surfaces as `IngestRunExists` rather than as a retry, and the operator is
        # told the work is already done when it is not. Single-operator use makes that
        # rare rather than impossible; re-running the command recovers it, because the
        # maximum is re-read. The trade is Scope Risk §5 / Plan Risk 4, accepted knowingly.
        sequence = max(dir_seq, warehouse_max + 1)
        run = land_snapshot(connection, parsed, ingest_seq=sequence)
    finally:
        connection.close()

    return LandingResult(
        run=run,
        verdict=verdict,
        mode=mode,
        snapshot_dir_seq=dir_seq,
        warehouse_max_seq=warehouse_max,
        tables_created=created,
        reason=reason,
    )


def format_result(result: LandingResult) -> str:
    """The human block. **Line one is pinned** so a test can parse the triple off it."""
    run = result.run
    lines = [
        f"landed {run.save_id} {run.sim_date} ingest_seq {run.ingest_seq}",
        f"  save mode: {result.mode}",
        f"  verdict: {result.verdict}",
        f"  reason: {result.reason or 'no prior landing was compared against'}",
        f"  parse: {'not measured' if run.parse_seconds is None else f'{run.parse_seconds:.2f} s'}",
    ]
    if result.tables_created:
        lines.append(f"  tables created: {', '.join(result.tables_created)}")
    lines.append("  " + sequence_line(result))
    lines.append("  rows: " + _pairs(run.row_counts))
    lines.append("  residual bytes: " + _pairs(run.residual_bytes))
    return "\n".join(lines)


def sequence_line(result: LandingResult) -> str:
    """Where the landed sequence came from — stated **every** run, agreeing or not.

    Printing this only on divergence would make silence do the work of a statement, and
    a reader cannot tell "the two agreed" from "nobody checked". That matters most on
    `--from-snapshot`, where AC15 requires the output to say explicitly whether the
    landed sequence still matches the directory it was re-landed from: a snapshot filed
    at `.../3` that lands as sequence 5 is the exact case ADR 0021's triage needs to
    know about, and the exact case a silent success would hide.
    """
    where = (
        f"snapshot directory {result.snapshot_dir_seq}, warehouse held "
        f"{result.warehouse_max_seq} — landed {result.run.ingest_seq}"
    )
    if not result.sequences_diverged:
        return f"sequence: {where}; the two allocators agree."
    if result.run.ingest_seq != result.snapshot_dir_seq:
        return (
            f"sequence: {where}. The snapshot on disk is NOT filed under the sequence "
            "this landing carries."
        )
    return (
        f"sequence: {where}. The filesystem was ahead of the warehouse, so the landed "
        "sequence is gapped — this is not a lost landing."
    )


def format_json(result: LandingResult) -> str:
    """The machine block. A stable contract, not a print format for anyone to grep."""
    run = result.run
    payload: dict[str, Any] = {
        "save_id": run.save_id,
        "sim_date": str(run.sim_date),
        "ingest_seq": run.ingest_seq,
        "verdict": result.verdict,
        # Null rather than absent when no comparison was made: a consumer branching on
        # `verdict` gets a key that is always there, and `null` says "not compared"
        # distinctly from a string that would say "compared, and here is what moved".
        "reason": result.reason,
        "mode": result.mode,
        "parse_seconds": run.parse_seconds,
        "row_counts": dict(run.row_counts),
        "residual_bytes": dict(run.residual_bytes),
        "tables_created": list(result.tables_created),
    }
    if result.sequences_diverged:
        payload["snapshot_dir_seq"] = result.snapshot_dir_seq
        payload["warehouse_max_seq"] = result.warehouse_max_seq
    return json.dumps(payload, indent=2, sort_keys=True)


# ── internals ────────────────────────────────────────────────────────────────


def _unchanged_envelope(error: read.SaveUnchanged) -> dict[str, Any]:
    """The refusal, in the same shape a success is reported in."""
    return {
        "verdict": "unchanged",
        "save_id": error.save_id,
        "sim_date": str(error.sim_date),
        "ingest_seq": error.ingest_seq,
    }


def _reread_snapshot(directory: Path) -> tuple[ParsedSnapshot, int, str, LandingVerdict]:
    """Re-parse a snapshot already on disk, without opening the game at all.

    The correction ADR 0021 names: a landing that was wrong is replaced by a *new*
    landing, never an edit, and the bytes it was made from are still on disk. No new
    parsing code is needed — `dump_parse` already composes exactly this.

    The save's mode is reported as **not recorded** rather than guessed: a snapshot holds
    the five in-scope files and `challenge.dat` is not one of them, so the fact simply is
    not present. Reporting "standard" here would be inventing it.
    """
    snapshot = read_manifest(directory)
    return parse_snapshot(snapshot), snapshot.ingest_seq, "not recorded", "from-snapshot"


def _resolve_save(settings: Settings, save_id: str | None) -> SaveRef:
    """The configured universe `save_id` names, or the managed league by default.

    Resolved **by name across the configured saves**, never by path: a filesystem path
    passed here matches no `save_id` and is refused, which is what keeps the command from
    becoming a way to point the pipeline at an arbitrary directory.
    """
    configured = {
        ref.save_id: ref
        for ref in (settings.managed, settings.truth_save, settings.probe_save)
        if ref is not None
    }
    if save_id is None:
        return settings.managed
    if save_id not in configured:
        known = ", ".join(sorted(configured)) or "none"
        raise UnknownSave(f"{save_id!r} is not a configured save. Configured: {known}")
    return configured[save_id]


def _prior_landing(connection: Any, save_id: str) -> read.PriorLanding | None:
    """The save's most recent landing as the plain data the pre-flight compares against.

    `None` means the save has never landed, which skips the comparison entirely — a first
    landing has nothing to be unchanged from.
    """
    row = latest_landing(connection, save_id=save_id)
    if row is None:
        return None
    return read.PriorLanding(
        sim_date=_as_save_date(row["sim_date"]),
        ingest_seq=int(row["ingest_seq"]),
        files=tuple(
            SnapshotFile(
                name=str(entry["name"]), size=int(entry["size"]), sha256=str(entry["sha256"])
            )
            for entry in row["source_files"]
        ),
    )


def _as_save_date(value: Any) -> SaveDate:
    """A landed `DATE` column back as the save's own date type."""
    if isinstance(value, date):
        return SaveDate(day=value.day, month=value.month, year=value.year)
    year, month, day = (int(part) for part in str(value).split("-"))
    return SaveDate(day=day, month=month, year=year)


def _pairs(counts: Any) -> str:
    """`name value, name value` in sorted order, or `none` — never a path."""
    items = sorted(dict(counts).items())
    return ", ".join(f"{name} {value:,}" for name, value in items) if items else "none"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ootp_ai.ingest",
        description="Land an OOTP save into the bronze warehouse.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    land_command = sub.add_parser(
        "land",
        help="snapshot, parse and land one save",
        description=(
            "Copies the in-scope files out of the save, parses them and lands them into "
            "bronze, printing the (save_id, sim_date, ingest_seq) triple it created. A "
            "save byte-identical to its own most recent landing is refused before "
            "anything is copied; pass --new-look to land it again deliberately. The "
            "first run creates the declared tables — it does not repair a table whose "
            "shape has drifted, which is a migration and a decision made in the open."
        ),
    )
    land_command.add_argument(
        "--save-id",
        default=None,
        help="the universe to land. Defaults to the managed league from .env.",
    )
    land_command.add_argument(
        "--json",
        action="store_true",
        help="emit the run as JSON instead of the human block.",
    )
    # Mutually exclusive because a snapshot re-land has no pre-flight to override: the
    # bytes are already on disk and the game is never opened.
    look = land_command.add_mutually_exclusive_group()
    look.add_argument(
        "--new-look",
        action="store_true",
        help="land the save again even if it is unchanged, at the next sequence.",
    )
    look.add_argument(
        "--from-snapshot",
        default=None,
        metavar="DIR",
        help="re-land a snapshot already on disk, without reading the game.",
    )
    return parser


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
