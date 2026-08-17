> **Status:** diagnosed · created 2026-08-16 · decided · next: plan

# Bug Report — Link guard: six skills name a test that does not exist, and the test that does rejects content those skills promise is exempt

## Symptom

Two related observable failures.

**A — the named test is absent.** Six skills instruct the agent to run
`tests/test_request_links.py`. No such file exists. The tests present are
`test_agent_contract.py`, `test_doc_links.py`, `test_no_leaks.py`,
`test_repo_structure.py`. An agent following the instruction literally gets a
pytest collection error; the failure was hit twice in one session, in `/commit`
and `/update-docs`, and worked around by silently substituting `test_doc_links.py`.

**B — the guard that does exist rejects documented-safe content.** Every skill in
the pipeline tells artifact authors that three things are exempt from link
checking. None of them is. Following the documented guidance produces a red build:

```
E   AssertionError: broken relative links:
E     _repro_fence_check.md -> IMPLEMENTATION_PLAN.md
E     _repro_fence_check.md -> tests/test_doc_links.py:38
E     _repro_fence_check.md -> var/snapshots/2024-03-07/
```

## Reproduction attempt

Deterministic. Create any Markdown file in the repo containing the three
constructs the skills say are safe — a link inside a fenced code block, a citation
with a `file.py:123` line suffix, and a link targeting `var/` — then run:

```
uv run pytest tests/test_doc_links.py -q
```

All three are reported as broken links and the test fails. Removing the file
returns the suite to 18/18.

Symptom A reproduces by reading: `grep -r test_request_links .claude/skills/`
returns six hits, and `ls tests/` does not contain that file.

## Expected vs Actual

- **Expected**, per the "What good looks like" section carried by
  `make-feature-request`, `make-bugfix-request`, `diagnose-bug`,
  `create-implementation-plan`, `commit` and `update-docs`: the check runs as
  `tests/test_request_links.py`; **fenced content is exempt** ("precisely so a
  report can quote a dead target"); citations **may carry a `file.py:123`
  suffix**; and **`var/` targets are exempt**.
- **Actual:** that filename does not exist. `tests/test_doc_links.py` scans every
  `*.md` in the repo outside `.git` and `var/`, applies one regex for Markdown
  links with no awareness of fences, and exempts only `http(s)://`, `mailto:`,
  `#`, and `<angle-bracket>` placeholders. Fenced links, line-suffixed citations
  and `var/` targets are all flagged.

## Severity

**Blocks correct work; no data at risk.** Nothing is corrupted, no money is spent,
and no number reaches a decision. But it fails CI on content the project's own
documentation instructs authors to write, which is worse than a missing check —
a guard that punishes following the manual teaches people to distrust the manual.

**It is about to bite.** The next planned action is `/make-feature-request` for the
`.dat` parser. Stage-1 templates routinely carry forward references to artifacts
later stages create, and the documented workaround for those — fence them — is
exactly the case that fails. This request was itself written around the defect, by
using code spans instead of links.

## Triage

- **Verdict:** needs-full-track
- **Obviousness hint (non-binding):** symptom A looks like a one-line rename in six
  places. Symptom B does not — it is missing behavior in the guard, and *which
  direction to fix* is a real decision rather than a typo.

## Affected Area & Pointers

Skills and repo tooling. A cold diagnosis agent opens, in order:

1. `tests/test_doc_links.py` — the guard that exists; the regex and skip list are
   the whole of its exemption logic
2. `.claude/skills/make-feature-request/SKILL.md` — the fullest statement of the
   promised contract, in its "What good looks like" section
3. `.github/workflows/ci.yml` — confirms the guard is blocking, via
   `uv run pytest -m "not gamedata"`

The other five references are at `commit/SKILL.md`, `update-docs/SKILL.md`,
`diagnose-bug/SKILL.md`, `create-implementation-plan/SKILL.md`, and
`make-bugfix-request/SKILL.md`.

## Reporter's cause-hunch (non-binding)

The skills were ported from a sibling repo (`nba2k-rpg`) whose guard was named
`test_request_links.py` and was scoped to `requests/` artifacts with a richer
exemption set. This repo's `test_doc_links.py` appears to be a differently-scoped
guard — all Markdown, simpler rules — that inherited the job without inheriting
the contract. Explicitly non-binding: diagnosis is free to find otherwise.

## Open Questions for Diagnosis

- **Which direction is correct?** Rename/extend `test_doc_links.py` to match what
  the skills promise, or correct the six skills to describe what the guard does?
  These produce materially different repos.
- **One guard or two?** The skills describe a `requests/`-scoped scanner that also
  reads **bare `requests/...` tokens**, not just Markdown links. The existing guard
  does neither. If the upstream had two distinct checks, the port may have dropped
  one rather than renamed it.
- **Is the same drift present in the other ported guards?** The known-failing
  `verify_batching_guard.mjs` recorded in `CLAUDE.md` came from the same port, and
  the pattern — ported artifact describing behavior this repo does not have — may
  not be limited to these two.
- Not a regression in this repo: the guard and the skills arrived together in the
  scaffolding commit, so this has been true since day one and was simply not
  exercised until artifacts started being written.

## Stage plan

**Full pipeline.** Trigger 1: Open Questions came out non-empty, and not
cosmetically — the first one asks which of two materially different repos we want,
which is a decision the plan panel exists to settle rather than something a fix
should assume.

Trigger 3 also fires, more weakly: the guard is a blocking CI check that every
future request artifact passes through. Loosening it wrongly lets genuinely dead
pointers into artifacts that later stages depend on, and the whole point of the
check is that a dead pointer misleads the next stage silently.
