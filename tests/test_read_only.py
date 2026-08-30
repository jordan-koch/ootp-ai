"""ADR 0001 gets a test, not a promise.

This is the one unrecoverable failure in the project. A Challenge Mode save carries
an integrity hash, the league cannot be reloaded or undone, and there is no upstream
copy of `OOTP-AI.lg` anywhere. Every other mistake here costs time; this one costs
the experiment.

So the claim *"nothing we run writes to the game"* is checked the only way a claim
like that can be: manifest **every** file under both game roots, run the pipeline,
manifest again, and diff. Not "the files we thought we opened" — every file, because
the whole point is to catch the write nobody predicted.

**Two tiers, deliberately.** `size` + `mtime_ns` catch every realistic failure: our
code writes through `open`, `shutil` and `Path.write_*`, none of which preserve a
modification time. `sha256` catches the paranoid case a restored mtime would hide,
and — more usefully in practice — catches corruption that is nobody's fault, which
matters because a torn source file is indistinguishable from a bad parse downstream.

**Ordering is structural, not conventional** (plan §2.5 / SD-20). The disposable
Challenge Mode probe is a twin of production — same club, same mode, eleven days
ahead — so untested code meets it first. That ordering lives inside a single test
rather than across two, because two tests are ordered by collection and collection
order is a convention. If the probe leg fails, the managed leg is never reached.

The cost is real, and `measured` 2026-08-16 so nobody has to guess whether it hung:
**2m35s** for the pair, over 30,703 files and ~6.4 GB hashed three times — the baseline,
then after the probe, then after the managed league. That is the price of the check, and
it is charged only when someone runs `-m gamedata` on purpose.

First green run, same date: zero mtime differences and zero digest differences under both
roots, after ingesting the disposable probe and then `OOTP-AI.lg` — the first time any
code in this project touched the managed league.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from ootp_ai.config import ConfigError, Settings, load_settings
from ootp_ai.ingest import read

_DIGEST_CHUNK = 1 << 20


@dataclass(frozen=True, slots=True)
class FileFacts:
    """What must not change about a file the pipeline is not allowed to touch."""

    size: int
    mtime_ns: int
    sha256: str


def _digest(path: Path) -> str:
    """SHA-256 of `path`, or a stable marker naming why it could not be read.

    An unreadable file records its error rather than raising. Two passes that both
    fail the same way agree, so a permanently locked file does not turn this guard
    into a flake — while a file that *becomes* unreadable mid-run still shows up as a
    difference, which is the thing worth knowing.
    """
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_DIGEST_CHUNK):
                hasher.update(chunk)
    except OSError as exc:
        return f"<unreadable: {type(exc).__name__}>"
    return hasher.hexdigest()


def manifest(root: Path) -> dict[str, FileFacts]:
    """Every file under `root`, keyed by its path relative to `root`.

    `os.walk` rather than `rglob` for two reasons: it does not follow directory
    symlinks, and a game install is large enough that the difference in traversal
    cost is visible.
    """
    facts: dict[str, FileFacts] = {}
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        directory = Path(dirpath)
        for name in filenames:
            path = directory / name
            try:
                stat = path.stat()
            except OSError:
                # A file that vanished between listing and stat is itself a change.
                facts[path.relative_to(root).as_posix()] = FileFacts(-1, -1, "<vanished>")
                continue
            facts[path.relative_to(root).as_posix()] = FileFacts(
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                sha256=_digest(path),
            )
    return facts


def differences(before: dict[str, FileFacts], after: dict[str, FileFacts]) -> list[str]:
    """Every way the two manifests disagree, as readable lines."""
    found: list[str] = []
    for rel in sorted(set(before) - set(after)):
        found.append(f"{rel}: DELETED")
    for rel in sorted(set(after) - set(before)):
        found.append(f"{rel}: CREATED")
    for rel in sorted(set(before) & set(after)):
        was, now = before[rel], after[rel]
        if was == now:
            continue
        changed = [
            f"{field}: {getattr(was, field)!r} -> {getattr(now, field)!r}"
            for field in ("size", "mtime_ns", "sha256")
            if getattr(was, field) != getattr(now, field)
        ]
        found.append(f"{rel}: " + ", ".join(changed))
    return found


# ── offline: prove the guard can fail ────────────────────────────────────────
#
# Without these, a broken `manifest` or `differences` yields a green AC11 that
# proves nothing at all — the failure mode this repo has already been bitten by
# once, and the reason `test_no_leaks.py` and `test_no_fixed_offsets.py` both
# carry self-tests. These run in CI; the guard they cover does not.


def _tree(root: Path) -> Path:
    (root / "sub").mkdir(parents=True)
    (root / "a.dat").write_bytes(b"alpha")
    (root / "sub" / "b.dat").write_bytes(b"bravo")
    return root


def test_an_unchanged_tree_shows_no_differences(tmp_path: Path) -> None:
    root = _tree(tmp_path / "game")
    assert differences(manifest(root), manifest(root)) == []


def test_a_rewritten_file_is_detected(tmp_path: Path) -> None:
    root = _tree(tmp_path / "game")
    before = manifest(root)
    (root / "sub" / "b.dat").write_bytes(b"BRAVO")
    found = differences(before, manifest(root))
    assert any("sub/b.dat" in line for line in found), found


def test_a_same_size_edit_is_detected_by_digest(tmp_path: Path) -> None:
    """The case `size` alone misses, and the reason the digest tier exists."""
    root = _tree(tmp_path / "game")
    before = manifest(root)
    target = root / "a.dat"
    stat = target.stat()
    target.write_bytes(b"omega")  # same length, different bytes
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # and mtime restored

    found = differences(before, manifest(root))
    assert any("a.dat" in line and "sha256" in line for line in found), found


def test_a_new_file_is_detected(tmp_path: Path) -> None:
    root = _tree(tmp_path / "game")
    before = manifest(root)
    (root / "sub" / "c.dat").write_bytes(b"charlie")
    assert any("CREATED" in line for line in differences(before, manifest(root)))


def test_a_deleted_file_is_detected(tmp_path: Path) -> None:
    root = _tree(tmp_path / "game")
    before = manifest(root)
    (root / "a.dat").unlink()
    assert any("DELETED" in line for line in differences(before, manifest(root)))


# ── gamedata: the real thing ─────────────────────────────────────────────────


def _settings(tmp_path: Path) -> Settings:
    """Real settings, with the snapshot root redirected into the test's own tmp dir.

    Redirected on purpose: `take_snapshot` refuses to overwrite, so running this test
    repeatedly against the configured root would accrete a 52.4 MiB directory per run
    (`measured` 2026-08-30 — 54,938,202 bytes across the five in-scope files; the "46 MB"
    this said until then predated the 2026-08-16 widening that added `world.dat`).
    The source side — the only side ADR 0001 is about — is untouched by the redirect.
    """
    try:
        settings = load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings, so the game roots are unknown: {exc}")
    return replace(settings, snapshot_root=tmp_path / "snapshots")


def _roots(settings: Settings) -> dict[str, Path]:
    return {"OOTP_SAVED_GAMES": settings.saved_games, "OOTP_INSTALL": settings.install}


def _manifests(settings: Settings) -> dict[str, dict[str, FileFacts]]:
    return {key: manifest(root) for key, root in _roots(settings).items()}


def _assert_untouched(
    before: dict[str, dict[str, FileFacts]],
    after: dict[str, dict[str, FileFacts]],
    *,
    what: str,
) -> None:
    for key in sorted(before):
        found = differences(before[key], after[key])
        assert not found, (
            f"ADR 0001 VIOLATED — {len(found)} file(s) under ${key} changed while "
            f"{what}.\n"
            "If OOTP is open, close it and re-run before reading anything into this: "
            "the game writes to its own install and saves.\n"
            "If it was closed, something in this pipeline wrote to the game and the "
            "managed league may be unrecoverable.\n" + "\n".join(found[:40])
        )


@pytest.mark.gamedata
def test_a_full_run_touches_nothing_under_the_game_directories(tmp_path: Path) -> None:
    """AC11. The probe, then the truth save, then the managed league — in that order.

    Each run's post-manifest is the next run's baseline, so the roots are walked once per
    leg plus one, rather than twice per leg.

    **The truth save joined the sequence in Phase 9**, which made it a routinely parsed save
    rather than a one-time export source: `tests/test_parser_vs_export.py` snapshots and
    parses it on every `-m gamedata` run. A read-only proof that covered the two saves the
    pipeline used to touch, while a third was being opened on every run, would be asserting
    less than it appeared to.

    **Each leg calls `ingest.read.read_save`, which is the operator's own path.** The
    legs used to compose `parse_snapshot(ingest_save(...))` by hand, which proved a
    composition that existed only inside this test: the command a human runs was a fourth
    arrangement of the same calls, and nothing kept it in step. `read_save` is the one
    function *the command* uses to open anything under a game root, so what the operator
    runs is what this diff brackets. It is not the only code in the project that reads a
    game file — `ingest_save` still does, and `tests/test_provenance.py` still calls it —
    so this proves the operator's path, not every path. It parses as well as snapshotting
    — the copy alone would be a strictly
    smaller pipeline reading like a full-run proof, and `parse_snapshot` is what opens the
    32 MB files and so the code most likely to grow a stray write.

    **`previous=None`, deliberately.** That skips the digest pre-flight, so the save is
    always snapshotted and the legs always exercise the copy. Passing a real prior landing
    would need a warehouse lookup, and landing is *still* excluded for the same reason it
    always was: it writes to MySQL, not to the game, and pulling a warehouse dependency
    into ADR 0001's guard would let an unrelated outage silence the one test the project
    cannot afford to lose.
    """
    settings = _settings(tmp_path)
    if settings.probe_save is None:
        pytest.skip(
            "OOTP_PROBE_LEAGUE is unset. SD-20 requires the disposable Challenge Mode "
            "probe to be exercised BEFORE the managed league, so this test refuses to "
            "run against OOTP-AI.lg alone rather than skipping the safer half."
        )

    baseline = _manifests(settings)

    probe_reading = read.read_save(
        settings.probe_save, snapshot_root=settings.snapshot_root, previous=None
    )

    # The pre-flight's OWN game reads, brought inside the diff. `previous=None` skips the
    # comparison entirely, so without this second call `snapshot.source_facts` — which
    # digests all five files of the LIVE save — was exercised by no leg of this test and
    # caught by no static scan either (the write guard looks for writes, and this only
    # reads). Handing it the reading's own manifest makes the save unchanged by
    # construction, so it raises before copying: the cost is one digest pass (~40 ms
    # against this test's 2m35s), no extra manifest pass and no fourth leg, which is what
    # keeps the plan's Risk 7 fence intact in substance as well as in letter.
    prior = read.PriorLanding(
        sim_date=probe_reading.parsed.run.sim_date,
        ingest_seq=probe_reading.parsed.run.ingest_seq,
        files=probe_reading.parsed.run.snapshot.files,
    )
    with pytest.raises(read.SaveUnchanged):
        read.read_save(settings.probe_save, snapshot_root=settings.snapshot_root, previous=prior)

    latest = _manifests(settings)
    _assert_untouched(baseline, latest, what="ingesting the disposable probe save")

    if settings.truth_save is not None:
        # Conditional rather than a `pytest.skip`: skipping would drop the probe and managed
        # legs too, which is strictly worse than covering two saves out of three. On a
        # machine where `OOTP_TRUTH_LEAGUE` is unset this leg does not run, and the test
        # asserts exactly what it did before Phase 9 — no less, and no false coverage.
        read.read_save(settings.truth_save, snapshot_root=settings.snapshot_root, previous=None)
        after_truth = _manifests(settings)
        _assert_untouched(latest, after_truth, what="ingesting the standard-mode truth save")
        latest = after_truth

    read.read_save(settings.managed, snapshot_root=settings.snapshot_root, previous=None)
    _assert_untouched(latest, _manifests(settings), what="ingesting the managed league")


@pytest.mark.gamedata
def test_the_manifest_is_not_vacuous(tmp_path: Path) -> None:
    """A guard over an empty file set passes without proving anything.

    Measured 2026-08-16: 11,460 files under the saved-games root and 19,243 under the
    install. Asserting thousands rather than the measured counts, because the operator
    installing a mod or retaining another save must not turn this red.
    """
    settings = _settings(tmp_path)
    for key, root in _roots(settings).items():
        assert len(manifest(root)) > 1000, f"${key} at {root.name} holds almost no files"


# ── offline: the static half of the same claim ───────────────────────────────
#
# The diff above proves *this run* wrote nothing, and only when someone runs it.
# These prove the source has no way to write to a game directory at all, and they
# run in CI on every pull request — which is where a regression would actually be
# introduced. Together they are the phase's acceptance grep, made mechanical.

SRC = Path(__file__).resolve().parent.parent / "src" / "ootp_ai"

#: The modules allowed to open a file for writing, as paths relative to the package
#: root. If a name has to be added here, that is a decision worth making in the open —
#: which is the whole reason the list is asserted rather than described.
#:
#: **Paths, not bare filenames, since Phase 10.** The list matched `path.name` until the
#: roster report arrived, and allowlisting a bare `__main__.py` would have released every
#: `__main__.py` in the tree — including `catalog/__main__.py`, which Phase 11 adds and
#: nobody has reviewed yet. A guard that widens itself to cover files that do not exist
#: is not a guard.
WRITERS = {
    # The snapshot copy and its manifest, both under `snapshot_root`, never under a game
    # root.
    "snapshot.py",
    # The rendered reports, under `output_root` — the first thing in this project to write
    # game-derived content to a file. It creates the snapshot-partitioned directory and
    # writes `roster.md`; `tests/test_no_leaks.py` pins that both are git-ignored.
    "reports/__main__.py",
    # The catalog, which writes to TWO roots and is the only module here that does. Its
    # generated half goes under `output_root` beside the reports; its structural half is
    # written into the repository's own `docs/`, tracked on purpose — table names, grains
    # and keys are derived schema knowledge, which ADR 0006 explicitly permits tracking,
    # and `tests/test_catalog.py` pins that no row-level value reaches it.
    "catalog/__main__.py",
}

#: Verbs that mutate or destroy something that already exists. None has a use in
#: this pipeline at all — a snapshot copies, and never disturbs what it copied from —
#: so these are banned outright rather than allowlisted per module.
DESTRUCTIVE_CALLS = (
    "shutil.move",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
    "os.rename",
    "os.replace",
    "os.utime",
    "os.chmod",
    "os.truncate",
    ".unlink(",
    ".rename(",
)

#: Ways to create or extend a file. Legal, but only in a module on the allowlist.
CREATIVE_CALLS = (".write_text(", ".write_bytes(", ".touch(", ".mkdir(", "os.makedirs")

_WRITE_MODE_CHARS = set("wax+")

_OPEN_MODE = re.compile(r"""\.?open\([^)]*?["']([rwxab+t]{1,4})["']""", re.DOTALL)


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _writes_in(text: str) -> list[tuple[int, str]]:
    """Every write this module can recognise, as (line number, what was seen)."""
    found: list[tuple[int, str]] = []
    for match in _OPEN_MODE.finditer(text):
        mode = match.group(1)
        if _WRITE_MODE_CHARS & set(mode):
            found.append((text[: match.start()].count("\n") + 1, f"open mode {mode!r}"))
    for lineno, line in enumerate(text.splitlines(), start=1):
        code = line.split("#", 1)[0]
        found.extend((lineno, verb) for verb in CREATIVE_CALLS if verb in code)
    return sorted(found)


def test_only_allowlisted_modules_can_write_a_file() -> None:
    offenders = [
        f"{path.relative_to(SRC).as_posix()}:{line}: {what}"
        for path in _source_files()
        if path.relative_to(SRC).as_posix() not in WRITERS
        for line, what in _writes_in(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "a file write appeared outside the modules allowed to write. ADR 0001 makes "
        "one write to the managed save unrecoverable, so widening the allowlist is a "
        "decision to make in the open, not an oversight:\n" + "\n".join(offenders)
    )


def test_the_pipeline_contains_no_destructive_filesystem_call() -> None:
    offenders = [
        f"{path.name}:{lineno}: {verb}"
        for path in _source_files()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        for verb in DESTRUCTIVE_CALLS
        if verb in line.split("#", 1)[0]
    ]
    assert not offenders, (
        "a destructive filesystem call reached the pipeline. None of these has a use "
        "here — a snapshot copies, it never moves, renames or deletes:\n" + "\n".join(offenders)
    )


def test_the_write_guards_still_catch_a_real_offender() -> None:
    """A guard loosened until it passes is not a guard.

    Both scans above pass trivially over a source tree that does nothing at all, so
    each is pinned against the shape it exists to catch and against a read that must
    not trip it.
    """
    assert _writes_in('with path.open("wb") as handle:') == [(1, "open mode 'wb'")]
    assert _writes_in("with open(target, 'a') as handle:") == [(1, "open mode 'a'")]
    assert _writes_in("    target.write_bytes(payload)") == [(1, ".write_bytes(")]
    assert _writes_in('with path.open("rb") as handle:') == []
    assert _writes_in("    data = path.read_bytes()") == []
    assert any(verb in "    shutil.move(src, dst)" for verb in DESTRUCTIVE_CALLS)
    assert not any(verb in "    shutil.copy2(src, dst)" for verb in DESTRUCTIVE_CALLS)
