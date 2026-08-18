"""The repo is PUBLIC (ADR 0006). Nothing machine-specific may reach a tracked file.

Scope, stated precisely because a narrow self-description is what let the last defect
here survive: this scans every file git knows about **or would accept** — tracked, staged
and merely written — minus whatever `.gitignore` excludes. It is deliberately NOT limited
to what has been staged; a leak is cheapest to fix before it can enter history.

This guard is mechanical and deliberately blunt: machine paths and personal
identifiers get pasted into docs during investigation and are easy to forget.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# This file necessarily contains the patterns it bans.
EXEMPT = {"tests/test_no_leaks.py"}

# Deliberately empty, and there is deliberately NO fenced-code exemption either — the
# sibling `tests/test_doc_links.py` gained one on 2026-08-17 and this guard refused it
# the same day. The asymmetry is the point: a fence exemption in a LINK checker only
# lets a report quote a dead target, while in a LEAK guard it is a channel for smuggling
# a credential past the only protection this public repo has. Exempting a directory here
# is the same shape in a smaller box. The cost is real and known — a bug report about a
# leak cannot quote the leak, so describe banned strings rather than showing them — and
# it was accepted with that cost in view. Do not add one without re-opening the decision.
EXEMPT_PREFIXES: tuple[str, ...] = ()

# The drive-letter lookbehind is load-bearing: without it, an escape sequence
# like "links:\n" inside a string literal reads as a drive path and the guard
# cries wolf on its own source. test_patterns_still_catch_real_leaks pins both
# directions.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("windows drive path", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}[A-Za-z0-9_.\-]")),
    ("unix home path", re.compile(r"/home/[a-z]|/Users/[A-Za-z]")),
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
]


def git_paths(*args: str) -> list[str]:
    """Repo-relative paths from `git ls-files`, NUL-separated and decoded explicitly.

    Two details are load-bearing, and both were measured rather than assumed:

    `-z` because git's default output *C-quotes* any path outside ASCII. Measured: a file
    named with an accented character comes back wrapped in literal double quotes with
    octal escapes inside, so its apparent suffix carries a trailing quote, fails the
    `keep` test below, and the file is dropped **silently** — a subtler version of the
    blindness this guard was just fixed for.

    The decode is pinned to UTF-8 rather than left to `subprocess`'s `text=True`, because
    that defers to the platform's preferred encoding — measured as cp1252 on the machine
    this was written on. `surrogateescape` so an undecodable byte survives round-trip
    instead of raising, since a path we cannot decode is exactly one worth still checking.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    decoded = out.stdout.decode("utf-8", errors="surrogateescape")
    return [rel for rel in decoded.split("\0") if rel]


def scannable_text_files() -> list[Path]:
    # --cached --others --exclude-standard = tracked PLUS untracked, MINUS ignored.
    # Bare `git ls-files` lists only the index, so a file that had just been written was
    # never opened and none of the patterns below were ever applied to it — the guard's
    # first possible warning arrived at `git add`, the moment content becomes committable.
    # Measured on a clean tree: this returns the identical set, so the widening costs
    # nothing and buys sight of the files most likely to carry a leak.
    # Case-folded: `Path("NOTES.MD").suffix` is ".MD", and Windows (the dev platform)
    # is case-preserving, so an uppercase extension would otherwise be dropped unread.
    #
    # `.js`/`.mjs`/`.jsonl` added 2026-08-17. Measured: 12 tracked files were enumerated
    # and never opened, and eight of them are the planning and acceptance panel scripts —
    # the prompt text whose absolute-path residue is what prompted this guard's widening
    # in the first place. `gm/ledger.jsonl` is tracked GM memory in a public repo
    # (ADR 0011 + ADR 0006). All 12 were clean when added, so this cost nothing to close.
    keep = {
        ".md",
        ".py",
        ".toml",
        ".yml",
        ".yaml",
        ".json",
        ".jsonl",
        ".js",
        ".mjs",
        ".sql",
        ".example",
        ".txt",
    }
    paths = []
    for rel in git_paths("--cached", "--others", "--exclude-standard"):
        if rel in EXEMPT or rel.startswith(EXEMPT_PREFIXES):
            continue
        p = REPO_ROOT / rel
        if p.suffix.lower() in keep or p.name == ".env.example":
            paths.append(p)
    return paths


def test_patterns_still_catch_real_leaks() -> None:
    """A guard that has been loosened until it passes is not a guard.

    Every string below is a leak this repo must never ship. If a future fix to
    a false positive also kills one of these, this test says so.
    """
    must_catch = [
        r"C:\Users\someone\Documents\OOTP",
        r"the save lives at D:\projects\ootp-ai\var",
        "OOTP_INSTALL=E:/Games/OOTP 25",
        "/home/jordan/ootp",
        "/Users/jordan/ootp",
        "contact someone@example.com",
    ]
    for sample in must_catch:
        assert any(p.search(sample) for _, p in PATTERNS), f"guard no longer catches: {sample!r}"

    # ...and these must NOT trip it, or the guard is unusable in its own repo.
    must_ignore = [
        r'"broken links:\n" + "\n".join(broken)',
        "see docs/data-access.md",
        "resolve from $OOTP_INSTALL",
        "ratio 3:1 improvement",
        "https://pypi.org/pypi/dbt-mysql/json",
    ]
    for sample in must_ignore:
        hits = [label for label, p in PATTERNS if p.search(sample)]
        assert not hits, f"false positive ({hits}) on: {sample!r}"


def machine_path_violations() -> list[str]:
    """Every banned value found in scope, as `path:line: label: text` strings.

    A helper rather than an inline loop so a test can assert the scan actually REPORTS —
    not merely that the right files are enumerated. Membership assertions alone cannot
    tell a working guard from one that opens every file and finds nothing, which is how a
    mutant scanning zero files passed the whole suite before this seam existed.
    """
    violations: list[str] = []
    for path in scannable_text_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        # `--cached` still lists a path that is tracked but deleted from the working
        # tree, so the read below would raise. Skip anything that is not a regular file.
        # Both this and the `except` are deliberately NARROW: a broad `except Exception`
        # here would swallow a real read failure and restore exactly the silent blindness
        # this guard was widened to remove.
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    violations.append(f"{rel}:{lineno}: {label}: {line.strip()[:100]}")
    return violations


def test_no_machine_paths_or_identifiers() -> None:
    violations = machine_path_violations()
    assert not violations, "machine-specific values in scanned files:\n" + "\n".join(violations)


def game_data_offenders() -> list[str]:
    """OOTP files that must never enter this repo, as repo-relative paths.

    A helper rather than an inline comprehension so a regression test can assert against
    the result — the same seam `scannable_text_files` provides for the pattern scan.

    Enumerated with the same widened argv, because `.gitignore` does NOT make this
    redundant. Measured with `git check-ignore --no-index`: `players.csv` and
    `x/players.dat` at the repo root ARE ignored, but `tests/fixtures/players.csv`,
    `tests/fixtures/x.dat` and `datasets/x.dat` are NOT — the `!tests/fixtures/**` and
    `!datasets/**` negations are LATER rules and git is last-match-wins, so they punch
    holes straight through the game-data block above them. This check is the only thing
    standing between the repo and a committed game-data fixture in those two directories,
    and until this widening it could not see one until it had already been staged.
    """
    banned_names = {"players.csv", "names.xml", "world_default.xml", "schools.xml"}
    banned_suffixes = {".dat", ".lg"}
    return [
        rel
        for rel in git_paths("--cached", "--others", "--exclude-standard")
        if Path(rel).name in banned_names or Path(rel).suffix in banned_suffixes
    ]


def test_game_data_is_not_tracked() -> None:
    """OOTP's shipped data and saves are theirs, not ours (ADR 0006)."""
    offenders = game_data_offenders()
    assert not offenders, "OOTP game data must never enter this repo:\n" + "\n".join(offenders)
