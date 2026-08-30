"""Every read of the game, in one function, so one test can bracket all of them.

`tests/test_read_only.py` proves ADR 0001 by manifesting every file under both game
roots, running the pipeline, manifesting again and diffing. That proof is only as wide
as the code it brackets. Before this module the test composed the library calls by
hand, which meant the *operator's* path and the *proved* path were two different
compositions that happened to agree — and nothing kept them agreeing.

`read_save` is the one function **the ingest command** uses to open anything under a
game root, and it is the function ADR 0001's three legs and the landing fixture call —
so the guard brackets the operator's path rather than a rehearsal of it.

It is **not** the only code in the project that reads a game file, and the difference
matters: `ingest_save` (`ingest/__init__.py`) still snapshots a save directly and
`tests/test_provenance.py` still calls it, while `snapshot.take_snapshot`,
`snapshot.read_sim_date`, `snapshot.source_facts` and `saves.is_record_file` all open
game files on their own account. What is true is the narrower claim, and writing the
broad one would tell a future reader that a guard covers ground it does not.

**The prior landing arrives as plain data.** `PriorLanding` is a value, not a query:
this module imports nothing from `warehouse/`. That is deliberate and load-bearing —
`tests/test_read_only.py` refuses to depend on MySQL in terms, because an unrelated
database outage silencing the one test the project cannot afford to lose is a worse
failure than the one the dependency would buy. The caller does the lookup and passes
the answer down.

**The unchanged case raises rather than returning an empty reading.** A `SaveReading`
always carries a parse; there is no shape that means "I looked and did nothing". The
alternative — an optional `parsed` — is dead API that still costs a `None` check at
every use, and the first implementer to fill it in with a placeholder would break the
refusal silently.

**Nothing here creates anything.** Every write in the ingest path belongs to
`snapshot.py`, which is the only module in `src/ootp_ai/` allowed to, and this module
delegates to it rather than earning an allowlist entry of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ootp_ai.config import SaveRef
from ootp_ai.ingest import ParsedSnapshot, parse_snapshot
from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.saves import is_challenge_mode
from ootp_ai.snapshot import (
    SNAPSHOT_FILES,
    SnapshotFile,
    read_sim_date,
    source_facts,
    take_snapshot,
)

__all__ = [
    "PriorLanding",
    "SaveReading",
    "SaveUnchanged",
    "read_save",
    "reason_from_digests",
    "reason_from_sizes",
]

#: What `read_save` did with the save it was handed. `no-prior` means nothing was
#: landed to compare against, so the comparison was skipped rather than passed.
Verdict = Literal["no-prior", "changed"]


@dataclass(frozen=True, slots=True)
class PriorLanding:
    """The most recent landing of one save, as the facts a comparison needs.

    Carries the landing's own `SnapshotFile` records — the same shape `take_snapshot`
    writes into its manifest, digested on the *source* side by `snapshot._copy_one`. So
    comparing today's save against these compares like with like: both are statements
    about the save's bytes, not about a copy's.
    """

    sim_date: SaveDate
    ingest_seq: int
    files: tuple[SnapshotFile, ...]


@dataclass(frozen=True, slots=True)
class SaveReading:
    """One completed pass over a save: what was parsed, and what it cost to decide to.

    `snapshot_dir_seq` is the sequence `take_snapshot` allocated **from the filesystem**,
    which is not necessarily the sequence the landing will use — the warehouse allocates
    its own, and the two can drift. Named for where it came from so a caller reconciling
    the two cannot mistake one for the other.
    """

    parsed: ParsedSnapshot
    verdict: Verdict
    snapshot_dir_seq: int
    mode: str
    #: Why this save was judged changed, in the words the comparison used — e.g.
    #: "players.dat is 32,078,633 bytes against 32,070,091 landed". `None` when there
    #: was no prior landing to compare against, which is not the same as "no difference
    #: was found": that case raises `SaveUnchanged` and never builds a reading at all.
    #:
    #: Carried rather than discarded because Scope Core asks the command to say *why* it
    #: landed, and the comparison has already computed the answer — the alternative is an
    #: operator reading "verdict: changed" and having no way to learn what moved.
    reason: str | None = None


class SaveUnchanged(Exception):  # noqa: N818
    """The save is byte-for-byte what the prior landing already holds.

    Raised **before** anything is copied, which is the whole point: the naive
    composition allocates a sequence and copies 52.4 MiB before it could discover this,
    and nothing reclaims either.

    Carries the existing triple so the caller can name it. A refusal that says only
    "already landed" sends the operator looking for which landing; this one tells them.

    Named without the `…Error` suffix to match `SnapshotExists` and `SnapshotCorrupt`,
    which are the same idea seen from the filesystem side.
    """

    def __init__(
        self,
        save_id: str,
        sim_date: SaveDate,
        ingest_seq: int,
        *,
        landed: tuple[SaveDate, ...] = (),
    ) -> None:
        self.save_id = save_id
        self.sim_date = sim_date
        self.ingest_seq = ingest_seq
        self.landed = landed
        # `landed` is optional because this module has no warehouse connection and must
        # not acquire one. A caller that has one re-raises with the dates filled in; the
        # refusal is complete either way, and richer when someone can afford to look.
        dates = (
            f" This save has landed at: {', '.join(str(date) for date in landed)}."
            if landed
            else ""
        )
        super().__init__(
            f"{save_id} at {sim_date} is unchanged since ingest_seq {ingest_seq} — "
            "every in-scope file matches that landing byte for byte. Nothing was "
            f"copied.{dates} Pass --new-look to land the same bytes again deliberately."
        )


def reason_from_sizes(
    previous: PriorLanding,
    sim_date: SaveDate,
    sizes: Mapping[str, int],
) -> str | None:
    """Why the save differs from `previous`, judged on the date and the sizes alone.

    `None` means *these cheap facts found nothing*, *not* "unchanged" — the caller must
    escalate to `reason_from_digests` before it may refuse. Measured 2026-08-30, the
    size survey costs 0.21 ms against the full digest's ~40 ms, so it is worth asking
    first; but of the managed league's five files only `players.dat` moved between the
    live save and its landing, so four of five give no signal, and on a genuinely
    unchanged save *every* size matches by definition. This function can settle the
    changed direction cheaply. It can never settle the unchanged one.

    There is deliberately no digest comparison here. `SnapshotFile.sha256` is a
    mandatory `str`, so a single function taking `SnapshotFile`s could not represent
    "size known, digest not computed" — an implementer filling the gap with `""` would
    see a mismatch on every file, never reach the digest branch, and ship a pre-flight
    that can never refuse. Two functions over two argument shapes cannot express that
    bug.
    """
    if previous.sim_date != sim_date:
        return f"the sim date moved from {previous.sim_date} to {sim_date}"

    landed = {entry.name: entry.size for entry in previous.files}
    for name in SNAPSHOT_FILES:
        if name not in landed:
            # A landing taken before the 2026-08-16 widening names three files, not
            # five. Treating an unnamed file as unchanged would report "unchanged" for
            # a save whose `world.dat` was never digested at all. This is a real state
            # on disk, not a hypothetical.
            return f"{name} is in scope today but was not part of ingest_seq {previous.ingest_seq}"
        if sizes[name] != landed[name]:
            return f"{name} is {sizes[name]:,} bytes against {landed[name]:,} landed"
    return None


def reason_from_digests(
    previous: PriorLanding,
    current: tuple[SnapshotFile, ...],
) -> str | None:
    """Why the save differs from `previous`, judged on the digests. `None` is unchanged.

    Called only when every size matched, which is the only case where paying for a
    digest buys an answer that sizes could not give — a same-size edit, which is exactly
    what a sim that reshuffles fixed-width records produces.
    """
    landed = {entry.name: entry.sha256 for entry in previous.files}
    for entry in current:
        if entry.name not in landed:
            return f"{entry.name} is in scope today but was not part of that landing"
        if entry.sha256 != landed[entry.name]:
            return (
                f"{entry.name} hashes to {entry.sha256[:16]}…, landed as {landed[entry.name][:16]}…"
            )
    return None


def read_save(
    save: SaveRef,
    *,
    snapshot_root: Path,
    previous: PriorLanding | None = None,
) -> SaveReading:
    """Decide whether `save` is worth landing, and if it is, snapshot and parse it.

    **This function has exactly three callers, and changing it changes what the
    operator's command does.** They are `ingest/__main__.py::land` — the command itself;
    `tests/fixtures/warehouse.py::landed_probe`, which every gamedata landing goes
    through; and the three legs of
    `tests/test_read_only.py::test_a_full_run_touches_nothing_under_the_game_directories`,
    which is ADR 0001's proof. That is the whole point of the shape: the command and the
    guard are the same code, so the diff brackets what a human actually runs. Edit this
    and you are editing all three at once.

    With `previous`, the comparison runs **before** the copy: sizes first, digests only
    if every size matched, and `SaveUnchanged` if the digests agree too. A refusal
    therefore costs ~40 ms and leaves nothing behind. Without `previous` — which is what
    both test call sites pass — the comparison is skipped entirely and the save is
    always snapshotted.

    **The save's mode is reported, never refused.** `tests/test_parser_vs_export.py`
    lands the retained standard-mode save through this function on every gamedata run,
    so a refusal here would break the Tier-B export diff. Challenge Mode is a fact about
    the save, not a precondition for reading it.

    **`teams.dat` is read twice per call** — once here for the sim date, once inside
    `take_snapshot`. Accepted rather than plumbed around: collapsing it means giving
    `take_snapshot` a second way to be told the date, and a ~5 MB re-read is a poor
    trade for a wider contract on the module that owns every write.

    There is deliberately **no `ingest_seq` parameter**. The sequence belongs to whoever
    calls `land_snapshot`; a shared function that carried one would push the command's
    explicit-sequence policy into `landed_probe`, which lands with `None` on purpose,
    and the collision would surface as `IngestRunExists` in unrelated grain tests.

    Raises:
        SaveUnchanged: `previous` was given and every in-scope byte matches it.
        SaveFormatError: `teams.dat` is missing, truncated, or not version 25.
        SnapshotExists: the target snapshot directory is already on disk.
        SnapshotCorrupt: a copy does not match the source it was copied from.
        SnapshotDateMismatch: two files of the snapshot name different in-game dates.
        UndecodedRecords: a walk crossed records whose tail it could not decode.
    """
    sim_date = read_sim_date(save)
    mode = "challenge" if is_challenge_mode(save.path) else "standard"

    verdict: Verdict = "no-prior"
    reason: str | None = None
    if previous is not None:
        verdict = "changed"
        try:
            sizes = {name: (save.path / name).stat().st_size for name in SNAPSHOT_FILES}
        except OSError as error:
            # Named rather than raised raw: a save missing an in-scope file is a real
            # state (a partial copy, a save from an older OOTP), and a bare
            # FileNotFoundError escapes the command's refusal surface as a traceback.
            raise SaveFormatError(
                f"{save.save_id}: an in-scope file could not be read — {error}"
            ) from error
        reason = reason_from_sizes(previous, sim_date, sizes)
        if reason is None:
            reason = reason_from_digests(previous, source_facts(save))
        if reason is None:
            raise SaveUnchanged(save.save_id, previous.sim_date, previous.ingest_seq)

    snapshot = take_snapshot(save, snapshot_root=snapshot_root)
    return SaveReading(
        parsed=parse_snapshot(snapshot),
        verdict=verdict,
        snapshot_dir_seq=snapshot.ingest_seq,
        mode=mode,
        reason=reason,
    )
