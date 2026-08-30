"""Copy the in-scope save files, digest them, and never touch them again.

Everything downstream parses a snapshot, not the live save. That is not tidiness —
it is what makes a past decision re-examinable. The warehouse can be rebuilt from a
snapshot; a snapshot cannot be rebuilt from the game, because the game moves forward
and Challenge Mode has no undo. So the bytes a GM decision was actually made from
either survive on disk or are gone.

Three properties carry that, and each is enforced here rather than described.

**The copy is provably the source.** Every file is digested on the source side, copied,
then digested on the destination side and compared before the manifest is written. A
torn copy is caught at copy time, where it is a retry, rather than downstream, where it
is indistinguishable from a bad parse.

**A snapshot directory is written once.** The path is
`<snapshot_root>/<save_id>/<sim_date>/<ingest_seq>/` — the same three components, in the
same order, as every bronze primary key (plan §2.3(d)). An existing directory is refused
loudly; nothing here overwrites, moves, renames or deletes anything.

**A second look at the same in-game date is a new sequence, not an overwrite.** The
operator executes an action on 2024-03-07 and wants the club before and after. The sim
date has not moved, so `ingest_seq` separates the two states and both stay retrievable.

**Read-only, absolutely** (ADR 0001). The source side is opened `"rb"` and stat'ed, and
that is the entire interaction with the game's directories. `shutil.copy2` reads the
source and writes only the destination. This module is the one place in `src/ootp_ai/`
allowed to create a file at all, and `tests/test_read_only.py` asserts that allowlist —
widening it is a decision to make in the open.

**The sim date comes from `teams.dat`'s own header**, which is the league's in-game date
rather than the wall clock. A key built from the clock drifts off the league. The
saved-games index carries a sim date too, but its own header's is `(0, 0, 0)` — see
`parser/saved_games.py`.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ootp_ai.config import SaveRef
from ootp_ai.parser.header import read_header
from ootp_ai.parser.primitives import SaveDate

__all__ = [
    "MANIFEST_NAME",
    "MANIFEST_VERSION",
    "SIM_DATE_SOURCE",
    "SNAPSHOT_FILES",
    "Snapshot",
    "SnapshotCorrupt",
    "SnapshotExists",
    "SnapshotFile",
    "next_ingest_seq",
    "read_manifest",
    "read_sim_date",
    "source_facts",
    "take_snapshot",
    "verify_snapshot",
]

#: The files this project parses, and nothing else. ~55 MB against a ~600 MB `.lg`.
#: `retired.dat` (154 MB) is players nobody on a roster is; `challenge.dat` is a
#: 241-byte integrity blob that is not ours to move around; `scouting.dat` has no
#: walker. A snapshot is a named set, never a directory sweep — a sweep would quietly
#: grow the copy every time OOTP adds a file.
#:
#: **Widened 2026-08-16, operator-disposed under ADR 0018 tier 2.** `world.dat` (8.9 MB)
#: is the only home of division membership and the league calendar, and
#: `human_managers.dat` (835 bytes) is the only file that names the club we manage
#: outright — so a snapshot without either cannot be re-parsed without the game, which is
#: the entire property a snapshot exists to provide. `world.dat` joins now rather than
#: with its walker so that the snapshot stops changing shape between phases.
SNAPSHOT_FILES: tuple[str, ...] = (
    "teams.dat",
    "players.dat",
    "names.dat",
    "world.dat",
    "human_managers.dat",
)

#: Which file's header supplies the league's in-game date. `teams.dat` because every save
#: has one and it is already the file the walkers open first; `measured` — every record
#: file in a save carries the same sim date in its header.
SIM_DATE_SOURCE = "teams.dat"

MANIFEST_NAME = "manifest.json"

#: Bumped only if the manifest's shape changes. A snapshot outlives the code that
#: wrote it, so a reader has to be able to tell that it is looking at a shape it
#: understands rather than guessing.
MANIFEST_VERSION = 1

_DIGEST_CHUNK = 1 << 20


class SnapshotExists(Exception):  # noqa: N818
    """The target `(save_id, sim_date, ingest_seq)` is already on disk.

    Refused rather than overwritten. Snapshots are immutable, and that immutability is
    what makes a warehouse-versus-snapshot disagreement decidable: if the two differ,
    the warehouse is wrong. A legitimate second look at the same in-game date is a new
    `ingest_seq`, which `take_snapshot` allocates on its own.

    The `…Error` suffix ruff's N818 wants is skipped because the offline suite imports
    this name; the test pins the interface and the naming rule yields.
    """


class SnapshotCorrupt(Exception):  # noqa: N818
    """A snapshot disagrees with its own manifest, or the manifest is unreadable.

    Every message names the offending file. A snapshot that cannot be trusted is worse
    than no snapshot, because everything downstream treats it as the answer key.
    """


@dataclass(frozen=True, slots=True)
class SnapshotFile:
    """One copied file: what it is called, how big it was, and what it hashed to."""

    name: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    """A landed, immutable copy of the in-scope files at one `(save, date, seq)`.

    There is deliberately no wall-clock field. Ingestion time is an attribute of an
    ingest *run*, never part of a key: for every practical purpose you snapshot when
    you sim, and keying on the clock would fragment one game state across re-runs.
    """

    save_id: str
    sim_date: SaveDate
    ingest_seq: int
    path: Path
    files: tuple[SnapshotFile, ...]


def next_ingest_seq(snapshot_root: Path, save_id: str, sim_date: str) -> int:
    """The next unused sequence for `(save_id, sim_date)`, starting at 1.

    `sim_date` is the directory component — `str(SaveDate)`, i.e. `YYYY-MM-DD` — not a
    `SaveDate`, because the caller that needs this is naming a directory.

    Allocated from the filesystem rather than a counter so that it survives a process
    restart and agrees with what is actually on disk. A directory whose name is not a
    plain integer is ignored: it was not written by this module.
    """
    parent = snapshot_root / save_id / sim_date
    if not parent.is_dir():
        return 1
    used = [
        int(child.name)
        for child in parent.iterdir()
        if child.is_dir() and child.name.isdigit() and not child.name.startswith("0")
    ]
    return max(used, default=0) + 1


def take_snapshot(
    save: SaveRef,
    *,
    snapshot_root: Path,
    ingest_seq: int | None = None,
) -> Snapshot:
    """Copy the in-scope files out of `save` and record what was copied.

    `ingest_seq` is allocated automatically when omitted. Naming it explicitly is what
    a re-run script or a retry does, and that is exactly the case that must refuse:
    landing over an existing sequence would destroy the state a prior decision was made
    from, with nothing raised.

    Raises:
        SnapshotExists: the target directory already exists.
        SnapshotCorrupt: a copy does not match the source it was copied from.
        SaveFormatError: `teams.dat` is missing, truncated, or not version 25.
    """
    sim_date = read_sim_date(save)
    sim_date_text = str(sim_date)
    save_id = save.save_id

    seq = (
        next_ingest_seq(snapshot_root, save_id, sim_date_text) if ingest_seq is None else ingest_seq
    )
    if seq < 1:
        raise ValueError(f"ingest_seq starts at 1; got {seq}")

    snapshot_dir = snapshot_root / save_id / sim_date_text / str(seq)
    if snapshot_dir.exists():
        raise SnapshotExists(
            f"{save_id} at {sim_date_text} already has ingest_seq {seq} on disk. "
            "Snapshots are immutable — a second look at the same in-game date takes "
            "the next sequence instead of overwriting this one."
        )

    # `parents=True` builds the save/date levels; no `exist_ok`, so a concurrent run
    # that won the race fails here rather than landing two snapshots in one directory.
    snapshot_dir.mkdir(parents=True)

    files = tuple(_copy_one(save.path / name, snapshot_dir / name) for name in SNAPSHOT_FILES)
    snapshot = Snapshot(
        save_id=save_id,
        sim_date=sim_date,
        ingest_seq=seq,
        path=snapshot_dir,
        files=files,
    )
    _write_manifest(snapshot)
    return snapshot


def read_manifest(snapshot_dir: Path) -> Snapshot:
    """Rebuild the `Snapshot` a directory describes.

    A snapshot outlives the process that wrote it, or it is not a snapshot: this is how
    a later phase, a later session, or an incident triage picks one up again.
    """
    payload = _load_manifest(snapshot_dir)
    try:
        version = int(payload["manifest_version"])
        if version != MANIFEST_VERSION:
            raise SnapshotCorrupt(
                f"{MANIFEST_NAME} declares version {version}, this reader understands "
                f"{MANIFEST_VERSION} — refusing rather than guessing at its shape"
            )
        files = tuple(
            SnapshotFile(
                name=str(entry["name"]),
                size=int(entry["size"]),
                sha256=str(entry["sha256"]),
            )
            for entry in payload["files"]
        )
        return Snapshot(
            save_id=str(payload["save_id"]),
            sim_date=_parse_sim_date(str(payload["sim_date"])),
            ingest_seq=int(payload["ingest_seq"]),
            path=snapshot_dir,
            files=files,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotCorrupt(
            f"{MANIFEST_NAME} in {snapshot_dir.name} is missing or malformed: {exc}"
        ) from exc


def verify_snapshot(snapshot_dir: Path) -> None:
    """Re-digest every file and refuse if any of them has moved a bit.

    The manifest exists to be checked. Called after landing a snapshot and again by any
    consumer that wants to know the bytes it is about to parse are the bytes that were
    copied — which is the whole argument for triaging a warehouse disagreement against
    a snapshot rather than against memory.

    Raises:
        SnapshotCorrupt: naming the file that disagrees.
    """
    for entry in read_manifest(snapshot_dir).files:
        path = snapshot_dir / entry.name
        if not path.is_file():
            raise SnapshotCorrupt(f"{entry.name} is listed in the manifest but is not on disk")
        size = path.stat().st_size
        if size != entry.size:
            raise SnapshotCorrupt(
                f"{entry.name} is {size:,} bytes; the manifest records {entry.size:,}"
            )
        digest = _digest(path)
        if digest != entry.sha256:
            raise SnapshotCorrupt(
                f"{entry.name} hashes to {digest[:16]}…; the manifest records "
                f"{entry.sha256[:16]}… — this snapshot is no longer the bytes it claims"
            )


def read_sim_date(save: SaveRef) -> SaveDate:
    """The league's in-game date, from the header of the save's own `teams.dat`.

    Read whole and handed to the parser as `bytes`: nothing in `parser/` opens a file,
    which is what keeps every read of the game `"rb"` by construction. `teams.dat` is
    ~5 MB, so the cost is not worth a partial read that would need a length constant.

    Public because it is the only cheap answer to *what date would this land at?* —
    `measured` 2026-08-30 at 0.005 s, against the 52.4 MiB a snapshot copies to reach
    the same fact. A caller deciding whether a save is worth landing needs the date
    before it pays for the copy, and the alternative is snapshotting first and
    discovering the answer afterwards, which allocates a sequence and leaves a
    directory nothing reclaims.
    """
    source = save.path / SIM_DATE_SOURCE
    return read_header(source.read_bytes(), SIM_DATE_SOURCE).sim_date


def source_facts(save: SaveRef) -> tuple[SnapshotFile, ...]:
    """Size and digest every in-scope file *in place*, copying nothing.

    The same `SnapshotFile` shape `take_snapshot` records, computed against the live
    save. That is what lets a caller compare a save to a prior landing on the landing's
    own terms rather than on a second, parallel notion of what a file's identity is.

    Reads only (ADR 0001): `stat` and `"rb"`, the same interaction `_copy_one` has with
    the source side, minus the copy.

    `measured` 2026-08-30 over the managed league's five files (54,938,202 bytes, warm
    cache, three runs): 48.2 / 36.9 / 35.4 ms. The size survey alone is 0.21 / 0.41 /
    0.22 ms, which is why a caller that can decide on sizes should decide on sizes.
    """
    facts = []
    for name in SNAPSHOT_FILES:
        source = save.path / name
        facts.append(SnapshotFile(name=name, size=source.stat().st_size, sha256=_digest(source)))
    return tuple(facts)


# ── internals ────────────────────────────────────────────────────────────────


def _copy_one(source: Path, destination: Path) -> SnapshotFile:
    """Copy one file and prove the copy landed intact.

    Digested before and after so a torn copy surfaces here. `copy2` reads the source and
    writes only the destination; nothing under the game's directories is opened for
    writing, ever (ADR 0001).

    A failure part-way leaves an incomplete directory behind on purpose — this module
    deletes nothing. The next run allocates the next sequence, and the incomplete one
    has no manifest, so `read_manifest` refuses it rather than serving half a snapshot.
    """
    size = source.stat().st_size
    digest = _digest(source)

    shutil.copy2(source, destination)

    landed_size = destination.stat().st_size
    if landed_size != size or _digest(destination) != digest:
        raise SnapshotCorrupt(
            f"{source.name}: the copy does not match its source "
            f"({landed_size:,} bytes landed against {size:,} read). "
            "The snapshot was not written; nothing under the save was modified."
        )
    return SnapshotFile(name=source.name, size=size, sha256=digest)


def _digest(path: Path) -> str:
    """SHA-256 of a file, streamed. 64 lowercase hex characters."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_DIGEST_CHUNK):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_manifest(snapshot: Snapshot) -> None:
    """Record what was copied, beside the copy.

    `sort_keys` and an explicit `newline` because a manifest is compared byte-for-byte
    during incident triage and this project develops on Windows and runs CI on Linux.
    """
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "save_id": snapshot.save_id,
        "sim_date": str(snapshot.sim_date),
        "ingest_seq": snapshot.ingest_seq,
        "files": [
            {"name": entry.name, "size": entry.size, "sha256": entry.sha256}
            for entry in snapshot.files
        ],
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    (snapshot.path / MANIFEST_NAME).write_text(text, encoding="utf-8", newline="\n")


def _load_manifest(snapshot_dir: Path) -> dict[str, Any]:
    try:
        raw = (snapshot_dir / MANIFEST_NAME).read_text(encoding="utf-8")
    except OSError as exc:
        raise SnapshotCorrupt(
            f"{MANIFEST_NAME} could not be read from {snapshot_dir.name}: {type(exc).__name__}"
        ) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SnapshotCorrupt(f"{MANIFEST_NAME} in {snapshot_dir.name} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SnapshotCorrupt(f"{MANIFEST_NAME} in {snapshot_dir.name} is not a JSON object")
    return payload


def _parse_sim_date(text: str) -> SaveDate:
    """`YYYY-MM-DD` back into the three integers the save actually stores.

    Kept as integers rather than a `datetime.date` for the reason `SaveDate` exists: a
    save writes 0/0/0 where a date does not apply, and collapsing that into a calendar
    date would turn structural absence into a wrong value.
    """
    year_text, month_text, day_text = text.split("-")
    return SaveDate(day=int(day_text), month=int(month_text), year=int(year_text))
