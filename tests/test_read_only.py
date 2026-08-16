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

The cost is real: ~6.4 GB across both roots, hashed three times. That is the price of
the check, and it is charged only when someone runs `-m gamedata` on purpose.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from ootp_ai.config import ConfigError, Settings, load_settings
from ootp_ai.ingest import ingest_save

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
    repeatedly against the configured root would accrete a 46 MB directory per run.
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
    """AC11. The probe first, then the managed league — in that order, in one test.

    The post-probe manifest is the pre-managed baseline, so the roots are walked
    three times rather than four.
    """
    settings = _settings(tmp_path)
    if settings.probe_save is None:
        pytest.skip(
            "OOTP_PROBE_LEAGUE is unset. SD-20 requires the disposable Challenge Mode "
            "probe to be exercised BEFORE the managed league, so this test refuses to "
            "run against OOTP-AI.lg alone rather than skipping the safer half."
        )

    baseline = _manifests(settings)

    ingest_save(settings.probe_save, settings=settings)
    after_probe = _manifests(settings)
    _assert_untouched(baseline, after_probe, what="ingesting the disposable probe save")

    ingest_save(settings.managed, settings=settings)
    _assert_untouched(after_probe, _manifests(settings), what="ingesting the managed league")


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

#: The one module allowed to open a file for writing. It writes the snapshot copy
#: and its manifest, both under `snapshot_root`, and never under a game root. If a
#: second name has to be added here, that is a decision worth making in the open —
#: which is the whole reason the list is asserted rather than described.
WRITERS = {"snapshot.py"}

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
        f"{path.name}:{line}: {what}"
        for path in _source_files()
        if path.name not in WRITERS
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
