"""The leak guard's SCOPE: which files it can see at all.

`tests/test_no_leaks.py` owns *what* counts as a leak. This module owns *where it
looks*, because those fail differently: a bad pattern produces a false negative on a
file the guard read, while a bad scope produces a false negative on a file the guard
never opened. The second is worse — it is invisible, and no amount of pattern work
finds it.

The guard used to enumerate candidates with a bare `git ls-files`, which lists tracked
and staged paths only — so a file that had just been written was invisible until it was
staged, and the guard first fired at the moment a leak could already enter history.
Widened 2026-08-17 to `--cached --others --exclude-standard`; these tests are what keep
it widened, and what stop the widening from buying visibility by scanning junk.

**Constructed, never literal.** The probe's banned string is assembled at runtime. A
literal one in this file would trip the guard on this file — `EXEMPT` at
`tests/test_no_leaks.py:16` holds exactly one entry, and it is not this module. That
constraint is itself part of the finding: a report about a leak cannot quote the leak.

See `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

import test_no_leaks as guard

REPO_ROOT = Path(__file__).resolve().parent.parent

#: A banned string built at runtime so this file never contains one. Matches the
#: "windows drive path" pattern at `tests/test_no_leaks.py:25`.
LEAK = "the snapshot lives at " + "D" + ":" + chr(92) + "projects" + chr(92) + "ootp-ai"


@contextmanager
def untracked_file(relative: str, body: str) -> Iterator[Path]:
    """Write a real file into the working tree and always remove it again.

    A `tmp_path` fixture cannot serve here: the guard enumerates the repository, so
    the probe has to exist inside it to be a fair test of what the guard can see.
    """
    path = REPO_ROOT / relative
    assert not path.exists(), f"{relative} already exists; refusing to clobber it"
    path.write_text(body, encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def test_the_probe_string_is_one_the_guard_actually_bans() -> None:
    """Guard the guard: if LEAK stopped matching, the tests below would pass emptily."""
    assert any(pattern.search(LEAK) for _, pattern in guard.PATTERNS), (
        "the constructed probe no longer matches any banned pattern, so every "
        "scope assertion below would pass without testing anything"
    )


def test_an_untracked_file_is_visible_to_the_leak_guard() -> None:
    """The original defect: a file that existed but was not staged was never opened.

    Measured 2026-08-17 — three times in one session a panel agent wrote absolute
    machine paths into an untracked `reviews/` artifact, the full offline suite ran
    green, and the paths were found only by a hand scan that imported this guard's own
    PATTERNS. The guard was working exactly as written and caught none of them. Fixed
    the same day; this test is the reason it stays fixed.
    """
    with untracked_file("_leak_guard_probe.md", f"# probe\n\n{LEAK}\n") as probe:
        seen = guard.scannable_text_files()
        assert probe in seen, (
            "the leak guard cannot see an untracked file, so it fires only once the "
            "content is staged — the point at which a leak can enter history"
        )


def test_a_gitignored_file_stays_out_of_scope() -> None:
    """The counterweight, and the reason the naive widening is wrong.

    `var/` is gitignored and holds snapshots, scratch and generated output. Scanning it
    would be slow, noisy, and would flag machine paths that are *supposed* to be
    machine-specific. Any fix to the test above must not buy visibility by scanning
    everything.
    """
    (REPO_ROOT / "var" / "tmp").mkdir(parents=True, exist_ok=True)
    with untracked_file("var/tmp/_leak_guard_ignored_probe.md", LEAK) as probe:
        assert probe not in guard.scannable_text_files(), (
            "a gitignored file must stay out of scope — widening the guard must respect "
            ".gitignore, or it becomes unusable and gets switched off"
        )


@pytest.mark.parametrize("junk", [".venv", "__pycache__", "node_modules", "var"])
def test_no_ignored_directory_leaks_into_the_candidate_set(junk: str) -> None:
    """Pins the property above across the directories that would hurt most."""
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in guard.scannable_text_files()
        if junk in p.relative_to(REPO_ROOT).parts
    ]
    assert not offenders, f"{junk}/ entered the guard's candidate set: {offenders[:5]}"


# --- Failure modes the widening MAKES LIVE ------------------------------------------
# Seeing untracked files is worth nothing if the enumeration then drops some of them for
# a different reason. Each test below pins a way that could happen silently.


def test_an_untracked_file_several_directories_deep_is_visible() -> None:
    """The shape all three real leaks actually had — none was at the repo root.

    A root-level probe can pass while a nested one fails, so the repro's root-level case
    is not by itself sufficient.
    """
    nested = REPO_ROOT / "requests" / "bugfix-requests" / "_leak_guard_nested_probe.md"
    with untracked_file(nested.relative_to(REPO_ROOT).as_posix(), f"# probe\n\n{LEAK}\n"):
        assert nested in guard.scannable_text_files(), (
            "a nested untracked file must be visible; the leaks this guard missed were "
            "all several directories deep"
        )


def test_a_non_ascii_filename_survives_enumeration() -> None:
    """git C-quotes non-ASCII paths by default, and the quote breaks the suffix filter.

    Measured before the fix: the quoted form's apparent suffix carried a trailing double
    quote, so the file failed the `keep` test and was dropped **silently**. `-z` plus an
    explicit UTF-8 decode is what closes it — `text=True` alone defers to the platform
    encoding, cp1252 on the machine this was written on.
    """
    name = "café_leak_guard_probe.md"
    with untracked_file(name, f"# probe\n\n{LEAK}\n") as probe:
        seen = guard.scannable_text_files()
        assert probe in seen, (
            "a file whose name is not pure ASCII must survive enumeration; if this fails, "
            "the guard is silently skipping files it appears to cover"
        )


def test_enumeration_yields_no_empty_entries() -> None:
    """NUL-separated output ends with a trailing separator; a blank entry would resolve
    to REPO_ROOT itself and quietly turn a directory into a scan candidate.

    Asserted against the raw split as well as the filtered result — checking only the
    latter would be tautological, since `git_paths` filters empties with the very
    expression that builds its return value.
    """
    paths = guard.git_paths("--cached", "--others", "--exclude-standard")
    assert "" not in paths
    assert all(p.strip() for p in paths), "a whitespace-only path would resolve to a directory"
    assert not any(p.endswith("\0") for p in paths), "NUL separators must not survive the split"


def test_a_suffix_outside_the_keep_set_is_not_scanned() -> None:
    """The guard reads text files by extension on purpose; widening scope must not
    widen the file *types* it opens."""
    with untracked_file("_leak_guard_probe.bin", LEAK) as probe:
        assert probe not in guard.scannable_text_files()


def test_the_game_data_guard_sees_an_untracked_fixture() -> None:
    """The second enumeration was blind in exactly the same way.

    It matters more than symmetry: measured with `git check-ignore --no-index`,
    `tests/fixtures/` and `datasets/` are NOT covered by the game-data block in
    `.gitignore`, because the `!` negations below it are later rules and git is
    last-match-wins. This check is the only thing stopping a committed `.dat` fixture
    there — and it could not see one until it was already staged.
    """
    with untracked_file("tests/fixtures/_leak_guard_probe.dat", "not real game data"):
        assert "tests/fixtures/_leak_guard_probe.dat" in guard.game_data_offenders(), (
            "an untracked game-data file in tests/fixtures/ must be reported; .gitignore "
            "does not cover that directory"
        )


def test_the_game_data_guard_still_ignores_var() -> None:
    """The counterweight: `var/` holds real snapshots and must stay out of scope."""
    (REPO_ROOT / "var" / "tmp").mkdir(parents=True, exist_ok=True)
    with untracked_file("var/tmp/_leak_guard_probe.dat", "snapshot scratch"):
        assert not [o for o in guard.game_data_offenders() if "var/" in o]


def test_a_plain_lg_file_is_ignored_not_just_an_lg_directory() -> None:
    """`*.lg/` matches directories only, so a plain `foo.lg` file slipped through."""
    with untracked_file("_leak_guard_probe.lg", "save-shaped"):
        assert "_leak_guard_probe.lg" not in guard.git_paths(
            "--cached", "--others", "--exclude-standard"
        ), "a plain .lg file must be gitignored, not merely caught downstream"


# --- The guard must be SEEN TO FAIL -------------------------------------------------
# Every test above asserts membership in a candidate set. None of them can tell a working
# guard from one that opens every file and reports nothing — measured, a mutant scanning
# zero files left the entire suite green. These three close that, and they are the reason
# to believe any of the others mean something.


def test_the_guard_actually_reports_a_planted_leak() -> None:
    """The end-to-end property: a banned string in scope is REPORTED, not merely seen.

    Enumeration is a means; this is the end. Without it the suite proves the guard looks
    in the right places and nothing about whether it finds anything there.
    """
    with untracked_file("_leak_guard_reported_probe.md", f"# probe\n\n{LEAK}\n"):
        violations = guard.machine_path_violations()
        assert any("_leak_guard_reported_probe.md" in v for v in violations), (
            "a planted banned string in an in-scope file must appear in the violation "
            f"list; the guard is not reporting what it can see (got {len(violations)} "
            "violations, none naming the probe)"
        )


def test_the_guard_is_silent_when_the_same_file_is_clean() -> None:
    """The other half: it must not report a file merely for existing."""
    with untracked_file("_leak_guard_clean_probe.md", "# probe\n\nnothing banned here\n"):
        assert not [v for v in guard.machine_path_violations() if "_leak_guard_clean_probe" in v]


def test_the_candidate_set_has_a_floor() -> None:
    """A coverage floor, because every other test here survives the set collapsing.

    Measured 2026-08-17: the guard scans ~134 files. An `EXEMPT_PREFIXES` edit that cut
    that to 9 left all the membership tests green, because a probe being present says
    nothing about the other 125 files going unread. The floor is deliberately far below
    the real count so ordinary repo churn never trips it — it exists to catch a collapse,
    not to track a number.
    """
    count = len(guard.scannable_text_files())
    assert count >= 80, (
        f"the guard scans only {count} files; it has been scanning ~134. A collapse this "
        "large means an exemption or a filter is swallowing the repo, and every "
        "membership test above would still pass"
    )


def test_a_path_that_no_longer_exists_does_not_crash_the_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--cached` lists tracked-but-deleted paths, which the read would raise on.

    Before the `is_file()` guard this raised `FileNotFoundError` and took the whole suite
    down — loudly rather than silently, but still a guard that cannot run is a guard that
    is not protecting anything.
    """
    monkeypatch.setattr(
        guard, "scannable_text_files", lambda: [REPO_ROOT / "_deleted_but_still_indexed.md"]
    )
    guard.test_no_machine_paths_or_identifiers()
