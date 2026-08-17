"""Snapshots are immutable, and that is what makes a past decision re-examinable.

`.claude/agents/data-engineer.md` puts it as a rule: a snapshot, once written, is
never modified. The reason is downstream of everything this project is for. The
warehouse can be rebuilt from a snapshot; a snapshot cannot be rebuilt from the game,
because the game moves forward and Challenge Mode has no undo. So the bytes the GM's
decision was actually made from either survive on disk or are gone.

Three properties carry that, and each is tested here rather than described:

**A snapshot directory is written once.** Re-snapshotting an existing
`(save_id, sim_date, ingest_seq)` refuses loudly instead of overwriting.

**A second look at the same in-game date is a new `ingest_seq`, not an overwrite.**
Plan §2.3(d): the operator executes an action on 2024-03-07 and wants the club before
and after. The sim date has not moved. Both states are retrievable, and the first is
bit-identical after the second lands.

**The copy is provably the source.** Per-file size and SHA-256, recorded at copy
time, so a later disagreement between the warehouse and the game is triaged against
bytes rather than memory.

The offline half builds a synthetic save from `tests/fixtures/synthetic.py` and needs
no game, so CI enforces all three. The `gamedata` half confirms the same properties
on the disposable Challenge Mode probe — never on the managed league, which this
module has no reason to touch.

AC10's warehouse clauses (row counts and checksums across a re-load) arrive with the
loader in Phase 8; this module owns the snapshot half.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from fixtures.synthetic import make_header
from ootp_ai.config import DEFAULT_SNAPSHOT_ROOT, ConfigError, SaveRef, Settings, load_settings
from ootp_ai.parser.header import read_header
from ootp_ai.snapshot import (
    SNAPSHOT_FILES,
    Snapshot,
    SnapshotCorrupt,
    SnapshotExists,
    next_ingest_seq,
    read_manifest,
    take_snapshot,
    verify_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

SYNTHETIC_SIM_DATE = (7, 3, 2024)
SYNTHETIC_SIM_DATE_TEXT = "2024-03-07"

#: Present in a save, deliberately NOT in scope for the copy. `retired.dat` is 154 MB
#: of players nobody on the roster is; `challenge.dat` is a 241-byte integrity blob
#: that is not ours to move around. The snapshot copies a **named set**, never a
#: directory — a sweep would quietly grow the copy every time OOTP adds a file.
NOT_COPIED = ("retired.dat", "challenge.dat", "scouting.dat")

#: Files the set must contain, whatever else it grows. `world.dat` joined in Phase 5
#: under ADR 0018's tier-2 rule (operator-disposed 2026-08-16): division membership
#: and the league calendar are there and nowhere else, so a snapshot without it cannot
#: reproduce a parse. `human_managers.dat` is 835 bytes and is the **only** file that
#: names the club we manage — measured, offsets 231/235/239 read 4/4/6 across the
#: three saves — so omitting it would make provenance unresolvable from the copy.
REQUIRED_IN_SET = ("teams.dat", "players.dat", "names.dat", "world.dat", "human_managers.dat")


# ── a synthetic save, so the whole contract runs offline ─────────────────────


def _make_save(root: Path, name: str = "Synthetic") -> SaveRef:
    """A save directory whose files carry real headers and junk bodies.

    The bodies differ per file so a copy that mixed two of them up would show as a
    digest mismatch rather than passing.
    """
    path = root / f"{name}.lg"
    path.mkdir(parents=True)
    for index, filename in enumerate(SNAPSHOT_FILES):
        header = make_header(filename=filename, sim_date=SYNTHETIC_SIM_DATE)
        (path / filename).write_bytes(header + bytes([index + 1]) * (64 * (index + 1)))
    for filename in NOT_COPIED:
        (path / filename).write_bytes(make_header(filename=filename) + b"\xff" * 32)
    return SaveRef(league=name, root=root)


def _stat_facts(path: Path) -> dict[str, tuple[int, int]]:
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(path.glob("*.dat"))}


# ── the copy is the source ───────────────────────────────────────────────────


def test_a_snapshot_copies_exactly_the_in_scope_files(tmp_path: Path) -> None:
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")

    assert {f.name for f in snap.files} == set(SNAPSHOT_FILES)
    assert {p.name for p in snap.path.glob("*.dat")} == set(SNAPSHOT_FILES)
    for excluded in NOT_COPIED:
        assert not (snap.path / excluded).exists(), (
            f"{excluded} was copied. The snapshot is a named set, not a directory "
            "sweep — retired.dat alone is 154 MB and out of scope."
        )


def test_the_snapshot_set_holds_every_file_a_parse_depends_on() -> None:
    """Widening this set is ADR 0018 tier 2 and belongs in a request, not a refactor.

    Narrowing it is the failure this guards. A snapshot that omits a file the parser
    needs is not a smaller snapshot — it is one that cannot be re-parsed without the
    game, which is the entire property snapshots exist to provide.
    """
    missing = [name for name in REQUIRED_IN_SET if name not in SNAPSHOT_FILES]
    assert not missing, (
        f"SNAPSHOT_FILES no longer copies {missing}. Division membership and the "
        "league calendar live only in world.dat, and human_managers.dat is the only "
        "file naming the club we manage — a snapshot without them is not re-parseable."
    )


def test_every_copied_byte_matches_the_source(tmp_path: Path) -> None:
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")

    for filename in SNAPSHOT_FILES:
        assert (snap.path / filename).read_bytes() == (save.path / filename).read_bytes()


def test_the_manifest_records_the_size_and_digest_of_each_file(tmp_path: Path) -> None:
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")

    assert len(snap.files) == len(SNAPSHOT_FILES)
    for entry in snap.files:
        assert entry.size == (save.path / entry.name).stat().st_size
        assert len(entry.sha256) == 64, "a SHA-256 is 64 hex characters"
    digests = {entry.sha256 for entry in snap.files}
    assert len(digests) == len(snap.files), "two files share a digest — a copy went wrong"


def test_the_manifest_round_trips_from_disk(tmp_path: Path) -> None:
    """A snapshot outlives the process that wrote it, or it is not a snapshot."""
    save = _make_save(tmp_path / "games")
    written = take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    assert read_manifest(written.path) == written


def test_verify_detects_a_tampered_snapshot(tmp_path: Path) -> None:
    """The manifest exists to be checked, so prove checking it works."""
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    verify_snapshot(snap.path)

    target = snap.path / SNAPSHOT_FILES[0]
    payload = bytearray(target.read_bytes())
    payload[-1] ^= 0xFF  # same length, one bit different
    target.write_bytes(bytes(payload))

    with pytest.raises(SnapshotCorrupt, match=SNAPSHOT_FILES[0]):
        verify_snapshot(snap.path)


def test_snapshotting_does_not_touch_the_source(tmp_path: Path) -> None:
    """ADR 0001 in miniature, on a tree that can be safely broken."""
    save = _make_save(tmp_path / "games")
    before = _stat_facts(save.path)
    take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    assert _stat_facts(save.path) == before


# ── immutability, and the seq that keeps it from being a wall ────────────────


def test_the_snapshot_path_is_save_id_then_sim_date_then_seq(tmp_path: Path) -> None:
    """The key and the path are the same three components, in the same order.

    Plan §2.3(d) keys every bronze row `(save_id, sim_date, ingest_seq)`. A snapshot
    directory that is keyed differently is a second grain nobody declared, and the
    first thing to disagree with the warehouse.
    """
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=root)

    assert snap.path.relative_to(root).parts == (save.save_id, SYNTHETIC_SIM_DATE_TEXT, "1")
    assert snap.save_id == save.save_id
    assert str(snap.sim_date) == SYNTHETIC_SIM_DATE_TEXT
    assert snap.ingest_seq == 1


def test_the_sim_date_comes_from_the_header_not_the_wall_clock(tmp_path: Path) -> None:
    """The league's date, not ours. A key built from the clock drifts off the league."""
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    header = read_header((save.path / "teams.dat").read_bytes(), "teams.dat")
    assert snap.sim_date == header.sim_date


def test_a_second_snapshot_of_the_same_sim_date_gets_the_next_seq(tmp_path: Path) -> None:
    """The operator's real case: the club before and after an executed action."""
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    first = take_snapshot(save, snapshot_root=root)

    (save.path / "teams.dat").write_bytes(
        make_header(filename="teams.dat", sim_date=SYNTHETIC_SIM_DATE) + b"\x99" * 128
    )
    second = take_snapshot(save, snapshot_root=root)

    assert (first.ingest_seq, second.ingest_seq) == (1, 2)
    assert first.path != second.path
    assert str(first.sim_date) == str(second.sim_date), "the in-game date did not move"


def test_the_earlier_seq_is_bit_identical_after_a_later_one_lands(tmp_path: Path) -> None:
    """Append-only means the first state is still exactly the first state."""
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    first = take_snapshot(save, snapshot_root=root)
    before = {p.name: p.read_bytes() for p in sorted(first.path.iterdir())}

    (save.path / "players.dat").write_bytes(
        make_header(filename="players.dat", sim_date=SYNTHETIC_SIM_DATE) + b"\x77" * 256
    )
    take_snapshot(save, snapshot_root=root)

    assert {p.name: p.read_bytes() for p in sorted(first.path.iterdir())} == before
    verify_snapshot(first.path)


def test_rewriting_an_existing_snapshot_refuses(tmp_path: Path) -> None:
    """Immutability is enforced, not documented.

    `take_snapshot` allocates a fresh seq, so reaching this needs the seq named
    explicitly — which is exactly what a re-run script or a retry would do.
    """
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    first = take_snapshot(save, snapshot_root=root)

    with pytest.raises(SnapshotExists):
        take_snapshot(save, snapshot_root=root, ingest_seq=first.ingest_seq)


def test_next_ingest_seq_starts_at_one_and_counts_up(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")

    assert next_ingest_seq(root, save.save_id, SYNTHETIC_SIM_DATE_TEXT) == 1
    take_snapshot(save, snapshot_root=root)
    assert next_ingest_seq(root, save.save_id, SYNTHETIC_SIM_DATE_TEXT) == 2


def test_two_universes_at_the_same_sim_date_do_not_collide(tmp_path: Path) -> None:
    """`save_id` separates universes. Without it these two would be one snapshot."""
    root = tmp_path / "snapshots"
    boston = take_snapshot(_make_save(tmp_path / "a", "OOTP-AI"), snapshot_root=root)
    probe = take_snapshot(_make_save(tmp_path / "b", "Test Save"), snapshot_root=root)

    assert boston.path != probe.path
    assert boston.ingest_seq == probe.ingest_seq == 1
    assert boston.save_id != probe.save_id


def test_a_save_id_never_carries_a_separator_into_a_path(tmp_path: Path) -> None:
    """The real save names contain spaces and dashes; a key may not."""
    snap = take_snapshot(
        _make_save(tmp_path / "games", "Test Save - Challenge Mode"),
        snapshot_root=tmp_path / "snapshots",
    )
    assert snap.save_id == "Test-Save-Challenge-Mode"
    assert " " not in snap.save_id


# ── the snapshot root is never tracked ───────────────────────────────────────


def _is_git_ignored(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
        ).returncode
        == 0
    )


def _tracked_under(path: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _assert_never_tracked(path: Path, *, label: str) -> None:
    """Either outside the worktree, or ignored inside it. Both are safe; nothing else.

    AC14's earlier phrasing asked for "outside the git worktree", which the default
    root cannot satisfy — `var/` is inside the worktree and merely ignored. A
    configured root, though, genuinely can be outside it, and that is *safer* rather
    than a failure, so the assertion admits both.
    """
    inside = path.resolve().is_relative_to(REPO_ROOT)
    if inside:
        assert _is_git_ignored(path), (
            f"{label} resolves inside the repo and is NOT git-ignored. A snapshot is "
            "OOTP's data and this repo is public (ADR 0006)."
        )
    assert not _tracked_under(path), f"{label} already has tracked files under it"


def test_the_default_snapshot_root_is_git_ignored() -> None:
    """Runs in CI, where there is no `.env` — so the default is what CI can prove."""
    _assert_never_tracked(REPO_ROOT / DEFAULT_SNAPSHOT_ROOT, label="the default snapshot root")


# ── gamedata: the disposable probe only ──────────────────────────────────────


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings: {exc}")


def _probe() -> SaveRef:
    settings = _settings()
    if settings.probe_save is None:
        pytest.skip("OOTP_PROBE_LEAGUE is unset — no disposable save to snapshot")
    return settings.probe_save


@pytest.mark.gamedata
def test_the_configured_snapshot_root_is_never_tracked() -> None:
    _assert_never_tracked(_settings().snapshot_root, label="OOTP_SNAPSHOT_ROOT")


@pytest.mark.gamedata
def test_a_real_snapshot_of_the_probe_carries_the_whole_set(tmp_path: Path) -> None:
    snap = take_snapshot(_probe(), snapshot_root=tmp_path)

    assert {entry.name for entry in snap.files} == set(SNAPSHOT_FILES)
    for entry in snap.files:
        assert (snap.path / entry.name).stat().st_size == entry.size
    verify_snapshot(snap.path)
    assert isinstance(snap, Snapshot)


@pytest.mark.gamedata
def test_a_real_snapshot_is_the_size_the_measurement_predicts(tmp_path: Path) -> None:
    """~55 MB across the set. A band, not the measured sizes.

    Exact sizes would go red the moment the operator legitimately sims the probe,
    which is what the probe is for. A truncated or empty copy still fails. The band
    was already wide enough to absorb `world.dat`'s 8.9 MB, so Phase 5's widening did
    not move it — worth knowing, because a band that never has to move is a band that
    might not be measuring anything.
    """
    total = sum(entry.size for entry in take_snapshot(_probe(), snapshot_root=tmp_path).files)
    assert 20_000_000 < total < 120_000_000, f"snapshot totals {total:,} bytes"


@pytest.mark.gamedata
def test_a_real_snapshot_uses_the_leagues_own_sim_date(tmp_path: Path) -> None:
    probe = _probe()
    snap = take_snapshot(probe, snapshot_root=tmp_path)

    header = read_header((probe.path / "teams.dat").read_bytes(), "teams.dat")
    assert snap.sim_date == header.sim_date
    assert snap.path.parent.name == str(header.sim_date)
