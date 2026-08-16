"""Relative Markdown links must resolve. Broken cross-references rot docs fast."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def markdown_files() -> list[Path]:
    return [p for p in REPO_ROOT.rglob("*.md") if ".git" not in p.parts and "var" not in p.parts]


def test_relative_links_resolve() -> None:
    broken: list[str] = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            if target.startswith(SKIP_PREFIXES):
                continue
            # Angle brackets mark a template placeholder, not a path: the skills
            # document directory shapes like `[<slug>](<slug>/)`. Those are meant
            # to be filled in, so there is nothing on disk to resolve.
            if "<" in target or ">" in target:
                continue
            clean = target.split("#", 1)[0].strip()
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                rel = path.relative_to(REPO_ROOT).as_posix()
                broken.append(f"{rel} -> {target}")

    assert not broken, "broken relative links:\n" + "\n".join(broken)
