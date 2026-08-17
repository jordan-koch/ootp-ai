"""Guards on the write-capable subagent's definition (ADR 0009).

The allowlist and the rulebook are *prose* — this harness has no path-level
permission system. These tests cannot enforce the agent's behaviour. What they
CAN do is guarantee the rules are still written down, because the design's only
real protection is that a human can read them and check the diff against them.

A rule silently deleted from the definition is the failure this catches.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / ".claude" / "agents"
DEFINITION = AGENT_DIR / "data-engineer.md"
MEMORY = AGENT_DIR / "data-engineer-memory.md"

# There is deliberately no length guard on the memory file. One existed — a 250-line
# ceiling — and it was removed on 2026-08-16 because it was enforced against the wrong
# actor. The file's own rules tell the agent to append freely and never prune, so at the
# ceiling there was no legal move: the Phase 5b builder had six entries to record, could
# not append without turning this file red, and was forbidden to trim. The judgment about
# what to cut and the authority to cut it both live with the curator at `/update-docs`,
# which now owns the audit. What survives here is the guard below, which is about whether
# an entry is *honest* rather than whether the file is *long* — and that one CI can answer.


def definition_text() -> str:
    return DEFINITION.read_text(encoding="utf-8")


def test_definition_exists_and_has_frontmatter() -> None:
    """Frontmatter is the discriminator — it's what registers the agent type."""
    text = definition_text()
    assert text.startswith("---\n"), "definition must open with YAML frontmatter"
    fm = text.split("---", 2)[1]
    assert re.search(r"^name:\s*\S+", fm, re.MULTILINE), "frontmatter needs a non-empty name"
    assert re.search(r"^description:\s*\S+", fm, re.MULTILINE), "frontmatter needs a description"
    assert re.search(r"^tools:\s*\S+", fm, re.MULTILINE), "frontmatter needs a tools grant"


def test_memory_and_readme_carry_no_frontmatter() -> None:
    """Exactly one file here is a definition. The others must not register agents."""
    for path in [MEMORY, AGENT_DIR / "README.md"]:
        assert not path.read_text(encoding="utf-8").startswith("---\n"), (
            f"{path.name} must not carry frontmatter — it would register a second agent type"
        )


def test_rulebook_invariants_survive() -> None:
    """Every invariant the agent builds against must still be stated in its definition.

    These are load-bearing: each one, if forgotten, produces silently wrong data
    rather than a failure. See docs/data-access.md for why.
    """
    text = definition_text().lower()
    required = {
        "the game is read-only": "read-only",
        "never seek to a fixed offset": "fixed offset",
        "ground truth is players.csv": "players.csv",
        "unvalidated mappings labelled unconfirmed": "unconfirmed",
        "format version guard": "version",
        "snapshot immutability": "immutable",
        "grain declared and proven": "grain",
        "no game data in git": "no ootp game data in git",
        "git is read-only": "git is read-only",
        "return contract": "return contract",
    }
    missing = [name for name, needle in required.items() if needle not in text]
    assert not missing, f"invariants dropped from the agent definition: {missing}"


def test_deny_set_still_protects_the_guards() -> None:
    """An agent that can edit the tests that catch it is the core failure mode."""
    text = definition_text()
    allowlist_section = text.split("## Write allowlist", 1)[1].split("## Tool allowlist", 1)[0]
    for denied in ["tests/", ".github/", "ops/", "CLAUDE.md", "docs/decisions/"]:
        assert denied in allowlist_section, f"{denied} missing from the agent's deny set"


def test_memory_entries_carry_an_epistemic_label() -> None:
    """An `assumed` claim written as `verified` is worse than no entry."""
    labels = {"measured", "verified", "inferred", "assumed", "unconfirmed"}
    bad: list[str] = []
    for line in MEMORY.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not re.match(r"^- \*\*\d{4}-\d{2}-\d{2}\*\*", stripped):
            continue
        m = re.search(r"`([a-z]+)`", stripped)
        if not m or m.group(1) not in labels:
            bad.append(stripped[:90])
    assert not bad, "memory entries missing a valid epistemic label:\n" + "\n".join(bad)
