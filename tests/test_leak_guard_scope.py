"""The leak guard's SCOPE: which files it can see at all.

`tests/test_no_leaks.py` owns *what* counts as a leak. This module owns *where it
looks*, because those fail differently: a bad pattern produces a false negative on a
file the guard read, while a bad scope produces a false negative on a file the guard
never opened. The second is worse — it is invisible, and no amount of pattern work
finds it.

The guard enumerates candidates with `git ls-files`, which lists tracked and staged
paths only. A file that was just written is invisible until it is staged, so the guard
first fires at the moment a leak can already enter history.

**Constructed, never literal.** The probe's banned string is assembled at runtime. A
literal one in this file would trip the guard on this file — `EXEMPT` at
`tests/test_no_leaks.py:16` holds exactly one entry, and it is not this module. That
constraint is itself part of the finding: a report about a leak cannot quote the leak.

See `requests/bugfix-requests/leak-guard-blind-to-untracked-files/`.
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
    """The defect: a file that exists but is not staged is never opened.

    Measured 2026-08-17 — three times in one session a panel agent wrote absolute
    machine paths into an untracked `reviews/` artifact, the full offline suite ran
    green, and the paths were found only by a hand scan that imported this guard's own
    PATTERNS. The guard was working exactly as written and caught none of them.
    """
    with untracked_file("_leak_guard_probe.md", f"# probe\n\n{LEAK}\n") as probe:
        seen = guard.tracked_text_files()
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
        assert probe not in guard.tracked_text_files(), (
            "a gitignored file must stay out of scope — widening the guard must respect "
            ".gitignore, or it becomes unusable and gets switched off"
        )


@pytest.mark.parametrize("junk", [".venv", "__pycache__", "node_modules", "var"])
def test_no_ignored_directory_leaks_into_the_candidate_set(junk: str) -> None:
    """Pins the property above across the directories that would hurt most."""
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in guard.tracked_text_files()
        if junk in p.relative_to(REPO_ROOT).parts
    ]
    assert not offenders, f"{junk}/ entered the guard's candidate set: {offenders[:5]}"
