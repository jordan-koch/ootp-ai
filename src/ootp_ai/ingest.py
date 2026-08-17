"""The ingest-run record: what was read, from where, and on whose authority.

This is the shape a later phase fills, landed now on purpose. `row_counts` arrives with
the bronze loader (Phase 8), `residual_bytes` with byte accounting (Phase 6) and
`parse_seconds` with the differential harness (Phase 9). Their emptiness here is the
point — a provenance schema invented three phases from now, under time pressure, is how
a grain drifts and how a key ends up meaning two things.

**Every fact in a run is resolved from data, never configured or assumed.** The sim date
comes from `teams.dat`'s own header, the digests and sizes from the snapshot copy, and
the version from each file's header. Code that hardcoded *"we are team 6"* would pass on
every save the parser is developed against and break invisibly on the managed league —
and since the validation harness runs against a probe, nothing would catch it. The human
club is now resolved the same way, out of the snapshot's own `human_managers.dat`.

**Nothing here writes.** `snapshot.py` is the only module in this package allowed to
create a file, and `tests/test_read_only.py` asserts that allowlist mechanically. This
module reads a snapshot that has already landed, and never re-opens the save.

**No path field, anywhere in the record.** `saved_games.dat` embeds an absolute
user-profile path per save, and an ingest-run row is the artifact most likely to be
rendered into a catalog. The defence is that the type has nowhere to put one (ADR 0006).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ootp_ai.config import SaveRef, Settings
from ootp_ai.parser.header import read_header
from ootp_ai.parser.human_managers import HUMAN_MANAGERS_FILE, read_human_manager
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.snapshot import Snapshot, SnapshotFile, take_snapshot

__all__ = [
    "IngestRun",
    "SourceFile",
    "ingest_save",
]


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One parsed input, as provenance rather than as content.

    `version` is the header's self-declared format version, read from the snapshot copy
    of each file individually rather than assumed from the save. A patched game that
    moved one file's layout would show up here as a refusal, not as a silent misparse.
    """

    name: str
    size: int
    sha256: str
    version: int


@dataclass(frozen=True, slots=True)
class IngestRun:
    """Everything one pass over one snapshot knows about itself.

    Keyed, like every bronze table, on `(save_id, sim_date, ingest_seq)` — the universe,
    the in-game date, and which attempt at that date (plan §2.3(d)). There is no
    wall-clock field in the key: ingestion time is an attribute, and keying on it would
    fragment a single game state across re-runs.

    `human_team_id` is resolved from `human_managers.dat`, which names the managed club
    outright in 835 bytes. It is **not** taken from `saved_games.dat`, which carries only
    a display string ("Chicago" is two clubs), and not from `teams.dat`, which reaches the
    same answer through the last slot of a variable-length integer run — a longer route,
    and the one `tests/test_parse_real_save.py` cross-checks this against rather than
    trusts. `None` means the file was absent from the snapshot, which is a known gap and
    never a zero.
    """

    save_id: str
    sim_date: SaveDate
    ingest_seq: int
    human_team_id: int | None
    snapshot: Snapshot
    sources: tuple[SourceFile, ...]
    #: Per-table landed row counts. Filled by the bronze loader, Phase 8.
    row_counts: Mapping[str, int] = field(default_factory=dict)
    #: Per-file unaccounted bytes after a walk. Filled by the walkers, Phase 6.
    residual_bytes: Mapping[str, int] = field(default_factory=dict)
    #: Wall-clock parse duration. Filled by the differential harness, Phase 9. `None`
    #: means "not measured yet", which is not the same number as zero.
    parse_seconds: float | None = None


def ingest_save(save: SaveRef, *, settings: Settings) -> IngestRun:
    """Snapshot a save, digest what was copied, and resolve the run's provenance.

    At this phase the pipeline stops here: no walker runs, no warehouse is opened, and
    nothing is persisted. What it does establish is that every later phase parses an
    immutable copy rather than the live save — which is the whole reason this runs
    *before* the phases that open the 32 MB files, not after.

    The only interaction with the game's directories is reading. ADR 0001: one write to
    the managed Challenge Mode save is unrecoverable, and there is no upstream backup.

    Raises:
        SnapshotExists: this `(save_id, sim_date, ingest_seq)` already landed.
        SaveFormatError: a header is not version 25, or a file is not what it claims.
    """
    snapshot = take_snapshot(save, snapshot_root=settings.snapshot_root)
    return IngestRun(
        save_id=snapshot.save_id,
        sim_date=snapshot.sim_date,
        ingest_seq=snapshot.ingest_seq,
        human_team_id=_resolve_human_team(snapshot),
        snapshot=snapshot,
        sources=tuple(_describe(snapshot, entry) for entry in snapshot.files),
    )


def _resolve_human_team(snapshot: Snapshot) -> int | None:
    """Which club this universe is managed by, read from the snapshot copy.

    From the **copy**, never the save: re-opening the game's directory to answer a
    question the snapshot can answer is avoidable contact with the one tree this project
    must not disturb, and the copy is verified byte-identical to it (ADR 0001).

    `None` only when the file is not in the snapshot at all — a save shape this project
    has not seen. A parse failure is *not* swallowed into `None`: an unreadable
    `human_managers.dat` means the run does not know which club it describes, and every
    bronze row would be stamped with that ignorance.
    """
    source = snapshot.path / HUMAN_MANAGERS_FILE
    if not source.is_file():
        return None
    return read_human_manager(source.read_bytes()).team_id


def _describe(snapshot: Snapshot, entry: SnapshotFile) -> SourceFile:
    """Attach a header version to a file the snapshot has already sized and digested.

    Read from the **snapshot copy**, not the save. Re-opening the save to answer a
    question the copy can answer is avoidable contact with the one directory this
    project must not disturb, and the copy is verified identical to it.
    """
    payload = (snapshot.path / entry.name).read_bytes()
    header = read_header(payload, entry.name)
    return SourceFile(
        name=entry.name,
        size=entry.size,
        sha256=entry.sha256,
        version=header.version,
    )
