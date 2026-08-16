"""Structural guards — the conventions in CLAUDE.md that a test can actually hold."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_required_docs_exist() -> None:
    for rel in [
        "README.md",
        "CLAUDE.md",
        "docs/data-access.md",
        "docs/decisions/README.md",
        "requests/README.md",
        "requests/feature-requests/README.md",
        "requests/bugfix-requests/README.md",
        "requests/data-incidents/README.md",
        ".env.example",
    ]:
        assert (REPO_ROOT / rel).is_file(), f"missing required file: {rel}"


def test_every_adr_is_indexed() -> None:
    """An ADR nobody can find from the index may as well not exist."""
    adr_dir = REPO_ROOT / "docs" / "decisions"
    index = (adr_dir / "README.md").read_text(encoding="utf-8")
    adrs = sorted(p.name for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert adrs, "no ADRs found"
    missing = [name for name in adrs if name not in index]
    assert not missing, f"ADRs absent from docs/decisions/README.md: {missing}"


def test_every_adr_records_its_cost() -> None:
    """ADR format requires consequences to state what the decision COST.

    An ADR that only lists benefits is a sales pitch, not a decision record.
    """
    adr_dir = REPO_ROOT / "docs" / "decisions"
    offenders = []
    for path in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
        text = path.read_text(encoding="utf-8").lower()
        if "**costs:**" not in text and "## consequences" not in text:
            offenders.append(path.name)
            continue
        if "cost" not in text:
            offenders.append(path.name)
    assert not offenders, f"ADRs not recording their cost: {offenders}"


def test_adrs_are_sequentially_numbered() -> None:
    adr_dir = REPO_ROOT / "docs" / "decisions"
    numbers = sorted(
        int(m.group(1))
        for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")
        if (m := re.match(r"(\d{4})-", p.name))
    )
    assert numbers == list(range(1, len(numbers) + 1)), f"ADR numbering has gaps: {numbers}"


def test_var_is_gitignored() -> None:
    """var/ holds ~600MB save snapshots. Tracking it would be a disaster."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert re.search(r"^var/\s*$", gitignore, re.MULTILINE), "var/ must be gitignored"
