"""Structural guards — the conventions in CLAUDE.md that a test can actually hold."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_required_docs_exist() -> None:
    for rel in [
        "README.md",
        "CLAUDE.md",
        "docs/data-access.md",
        # Generated, and required to be PRESENT anyway (Decision P5, the stronger of the
        # two options the operator was offered). The catalog is the only tracked statement
        # of what the warehouse holds and what it withholds; its absence would otherwise be
        # invisible until somebody went looking for it. `tests/test_catalog.py` owns the
        # harder half — that its bytes are exactly what the generator produces.
        "docs/warehouse-catalog.md",
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


def test_gm_memory_carve_out_survives() -> None:
    """gm/ is TRACKED — the one inversion of the disposable-state rule (ADR 0011).

    A blanket ignore rule added carelessly would silently stop backing up the only
    copy of the GM's reasoning. The save records what happened, never why.
    """
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert re.search(r"^!gm/\*\*\s*$", gitignore, re.MULTILINE), (
        "the !gm/** carve-out is missing from .gitignore — GM memory must stay tracked"
    )


def test_gm_memory_is_actually_tracked() -> None:
    """The carve-out is only worth having if git honours it."""
    out = subprocess.run(
        ["git", "check-ignore", "-q", "gm/README.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    # exit 0 = the path IS ignored, which is the failure we're guarding against.
    assert out.returncode != 0, "gm/README.md is gitignored — the carve-out is being shadowed"


def test_gm_contract_files_exist() -> None:
    """A GM with no charter or ledger contract is a GM with amnesia (ADR 0010)."""
    for rel in [
        "gm/README.md",
        "gm/charter.md",
        "gm/standing-orders.md",
        "gm/staff.md",
        "gm/decisions/README.md",
    ]:
        assert (REPO_ROOT / rel).is_file(), f"missing GM memory contract file: {rel}"
