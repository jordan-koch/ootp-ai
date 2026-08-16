"""The repo is PUBLIC (ADR 0006). Nothing machine-specific may be tracked.

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


def tracked_text_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    keep = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".sql", ".example", ".txt"}
    paths = []
    for line in out.stdout.splitlines():
        rel = line.strip()
        if not rel or rel in EXEMPT or rel.startswith(EXEMPT_PREFIXES):
            continue
        p = REPO_ROOT / rel
        if p.suffix in keep or p.name == ".env.example":
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


def test_no_machine_paths_or_identifiers() -> None:
    violations: list[str] = []
    for path in tracked_text_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    violations.append(f"{rel}:{lineno}: {label}: {line.strip()[:100]}")

    assert not violations, "machine-specific values in tracked files:\n" + "\n".join(violations)


def test_game_data_is_not_tracked() -> None:
    """OOTP's shipped data and saves are theirs, not ours (ADR 0006)."""
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    banned_names = {"players.csv", "names.xml", "world_default.xml", "schools.xml"}
    banned_suffixes = {".dat", ".lg"}

    tracked = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    offenders = [
        rel
        for rel in tracked
        if Path(rel).name in banned_names or Path(rel).suffix in banned_suffixes
    ]

    assert not offenders, "OOTP game data must never be tracked:\n" + "\n".join(offenders)
