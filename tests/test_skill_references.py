"""The skills were ported from sibling repos, and nothing checks that they landed.

`.claude/skills/` arrived by adaptation from `nba2k-rpg` / `nba-analysis`. The
adaptation was uneven, and the failure mode is silent in both directions: a skill
names a test file this repo does not have (an agent following the instruction gets
a collection error), or a skill's own guard feeds a fixture keyed by a lens this
repo's panel does not define (the guard reports a miscount and blames the code
under test).

Both are the same class of defect — a ported artifact describing behaviour this
repo does not have — and both survived because no check resolves an artifact's
references against the repo it now lives in. That check is what this module is.

See requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ and
requests/bugfix-requests/_done/doc-link-guard-mismatch/.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

PANEL = SKILLS_DIR / "implement-plan" / "acceptance_panel.js"
BATCHING_GUARD = SKILLS_DIR / "implement-plan" / "tests" / "verify_batching_guard.mjs"

#: A repo path a skill names as a thing to read or run — a `tests/test_*.py` module or a
#: `docs/*.md` document, in a code span, a link, or a `::test_name` citation. Every one is
#: an instruction an agent may follow literally, so an unresolvable one is a broken
#: instruction rather than a typo.
#:
#: Deliberately NOT covered: `datasets/manifest.json` and anything else under `datasets/`
#: or `build/`. Those are forward-looking by design — CLAUDE.md says those directories
#: arrive with the phase that needs them and forbids creating them speculatively — so a
#: skill naming one is describing the shape of future work, not citing a missing file.
#: The leading boundary is load-bearing: without it `docs/` matches inside a longer path
#: and `../update-docs/SKILL.md` yields a phantom `docs/SKILL.md`.
REPO_REFERENCE = re.compile(r"(?<![\w/-])(?:tests/test_[a-z0-9_]+\.py|docs/[A-Za-z0-9_/-]+\.md)")

#: The panel declares its lenses as `key: 'name'` — four core reviewers plus the
#: specialist definitions. Reading them out of the source keeps this guard honest when
#: the roster changes, rather than pinning a second copy of the list here.
LENS_KEY = re.compile(r"\bkey:\s*'([a-z0-9-]+)'")

#: The guard's synthetic reviews, keyed by lens: `  fidelity: [` / `  'data-contract': [`.
FIXTURE_LENS = re.compile(r"^ {2}'?([a-z0-9-]+)'?:\s*\[", re.MULTILINE)


def skill_documents() -> list[Path]:
    """Every skill file that can carry an instruction — prose AND the panel scripts.

    The `.js`/`.mjs` panels matter as much as the `.md` bodies: `plan_panel.js` builds the
    prompt three planning agents ground themselves in, so a repo path it names wrongly
    sends them after a file that does not exist. Scanning only `*.md` is how one such
    reference survived unnoticed until this guard was widened.
    """
    return sorted(p for ext in ("*.md", "*.js", "*.mjs") for p in SKILLS_DIR.rglob(ext))


def scannable_text(path: Path) -> str:
    """A file's text with synthetic fixture blocks blanked out.

    `verify_batching_guard.mjs` stocks its stub agent with invented findings at invented
    locations (`tests/test_extract_client.py:9` and friends). Those are test DATA, not
    citations — the file is deliberately describing a repo that does not exist. Blanking
    the block rather than exempting the file keeps the rest of that guard in scope, which
    matters because it is one of the files this check exists to police.
    """
    text = path.read_text(encoding="utf-8")
    marker = "const FINDINGS_BY_LENS = {"
    if marker not in text:
        return text
    head, rest = text.split(marker, 1)
    fixture, sep, tail = rest.partition("\n}\n")
    if not sep:
        # The block's column-0 closing brace was reflowed or commented. Blanking on a
        # failed partition would drop the entire remainder of the file from the scan —
        # the same silent-blindness failure this module exists to catch — so scan it all
        # and accept the false positives instead.
        return text
    return head + marker + ("\n" * fixture.count("\n")) + sep + tail


def test_every_repo_path_a_skill_names_exists() -> None:
    """A skill that names a file this repo lacks is an un-followable instruction.

    Six skills used to instruct the agent to run `tests/test_request_links.py`, which
    has never existed here — the guard that does is `tests/test_doc_links.py` — so an
    agent following the instruction got a pytest collection error and had to guess a
    substitution. The guess was made twice in one session before anyone wrote it down.
    Repointed 2026-08-17; this test is what keeps them pointed at files that exist.
    """
    broken: list[str] = []
    for path in skill_documents():
        for lineno, line in enumerate(scannable_text(path).splitlines(), start=1):
            for reference in REPO_REFERENCE.findall(line):
                if not (REPO_ROOT / reference).exists():
                    rel = path.relative_to(REPO_ROOT).as_posix()
                    broken.append(f"{rel}:{lineno} -> {reference}")

    assert not broken, (
        "skills name repo paths that do not exist in this repo:\n"
        + "\n".join(broken)
        + "\n\nEither the file was never ported, or it was renamed here and the skills "
        "were not updated with it."
    )


def fixture_lens_keys() -> set[str]:
    """The lens keys the batching guard's synthetic finding set is keyed by."""
    source = BATCHING_GUARD.read_text(encoding="utf-8")
    block = source.split("const FINDINGS_BY_LENS = {", 1)[1].split("\n}\n", 1)[0]
    return set(FIXTURE_LENS.findall(block))


def panel_lens_keys() -> set[str]:
    """Every lens the acceptance panel actually defines — core plus specialists."""
    return set(LENS_KEY.findall(PANEL.read_text(encoding="utf-8")))


def test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines() -> None:
    """An unknown lens key does not fail — it silently contributes zero findings.

    The guard stubs a review per lens with `FINDINGS_BY_LENS[lensKey] || []`, so a key
    the panel never asks for is never noticed: its findings simply never enter the run.
    Measured — two ported keys (`data-contract`, `extraction`, this repo's `warehouse`
    and `parser`) cost the fixture 3 of its 11 findings, and every one of the guard's
    six failure lines followed from that, including a merge miscount that read as a
    defect in the panel's dedupe. Re-keyed 2026-08-17; the guard now carries its own
    equivalent check so a `node` run catches the next one too.

    This is one-directional on purpose. A fixture need not exercise every lens; it must
    only name lenses that exist.
    """
    fixture = fixture_lens_keys()
    panel = panel_lens_keys()
    assert fixture, "parsed no lens keys out of the guard's fixture — the regex has drifted"
    assert panel, "parsed no lens keys out of the acceptance panel — the regex has drifted"

    unknown = sorted(fixture - panel)
    assert not unknown, (
        f"the batching guard's fixture is keyed by lenses the panel does not define: "
        f"{unknown}\nthe panel's lenses are: {sorted(panel)}\n"
        "Findings under an unknown key are dropped silently, and the guard then reports "
        "the shortfall as a miscount in the code under test."
    )
