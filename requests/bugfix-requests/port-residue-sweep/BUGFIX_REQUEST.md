> **Status:** intake · created 2026-08-17 · open · next: diagnosed

# Bug Report — The ported skills still describe a sibling repo in places nobody has looked

## Symptom

`.claude/skills/` and `.claude/agents/` were adapted from `nba2k-rpg` / `nba-analysis`.
The adaptation was uneven, and every instance found so far was found **by accident** —
while working on something else. Nothing has ever swept for them deliberately.

Seven instances are known, and they were not found by one search:

| # | Instance | Found while |
|---|---|---|
| 1 | Six skills named `tests/test_request_links.py`, which never existed here | diagnosing the batching guard |
| 2 | `verify_batching_guard.mjs`'s fixture keyed by `data-contract` / `extraction`, lenses this panel does not define | the same diagnosis |
| 3 | `diagnose-bug/SKILL.md` wrote status `root-cause`; the track grammar is `diagnosed` | writing an RCA with it |
| 4 | `plan_panel.js:147`, `:164` and `scope_panel.js:125` cited `docs/data-sources.md`, which never existed here | widening a guard for #1 |
| 5 | `diagnose-bug/SKILL.md`'s worked example cited `tests/test_extract_pagination.py` failing with *"expected 1230 games, got 1000"* — an NBA regular season, in a baseball save-file parser | reading the template |
| 6 | `implement-plan/SKILL.md` Step 7 says to set the Index row to `implemented` on **both** tracks; the bugfix track's terminal word is `fixed` | running that skill |
| 7 | **`gitleaks` was promised twice and exists nowhere.** `git grep -il gitleaks` over `.github/`, `ops/` and `pyproject.toml` returns nothing. **One occurrence remains**, at `update-docs/SKILL.md:25`, which lists `gitleaks` among the mechanical checks that "moved to CI, where it runs on every PR and cannot be skipped". The `commit/SKILL.md` occurrence was removed on 2026-08-17 — see the note below | fixing the leak guard |

> **Instance 7 was miscounted once already, in both directions.** The intake for
> `leak-guard-blind-to-untracked-files` said the claim appears twice; that request's
> ROOT_CAUSE_ANALYSIS "corrected" it to once; the planning panel then measured it and the
> original was right.
>
> **Then one of the two was removed by accident, on 2026-08-17.** That fix's plan said
> explicitly not to touch either occurrence — one finding, one tracker — but its Phase 5
> rewrote the surrounding paragraph in `commit/SKILL.md`, and the false sentence went with
> it. The removal is kept rather than reverted, because restoring a claim known to be false
> in order to preserve a tracker's tidiness is the wrong trade. Recorded here so this
> request's evidence stays accurate: **one occurrence remains, not two.**

Instances 1–5 are fixed (`requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/`).
**#6 is open and unfixed** — it is the concrete starting point for this request.

## Reproduction attempt

**Partially mechanical, which is the point.** Two guards now catch a subset automatically:

```
uv run pytest tests/test_skill_references.py tests/test_doc_links.py
```

`tests/test_skill_references.py` resolves every `tests/test_*.py` and `docs/*.md` path a
skill names, across `.md`, `.js` and `.mjs`. It is green today. But it only covers **two
token shapes in one directory**, and instances 3, 5 and 6 are invisible to it: a wrong
*stage word*, a domain-wrong *example*, and a wrong *terminal word* are all well-formed
prose naming nothing.

For #6, deterministic by reading: `.claude/skills/implement-plan/SKILL.md` Step 7
instructs `implemented` for either track, against
`requests/bugfix-requests/README.md`'s `intake → diagnosed → planned → fixed`.
*(measured 2026-08-17)*

## Expected vs Actual

- **Expected:** a skill describes the repo it lives in. Where it names a file, the file
  exists; where it names a stage word, the track README defines it; where it gives a
  worked example, the example is from this domain.
- **Actual:** six known divergences, five found incidentally, one still live. The rate of
  accidental discovery is the evidence: instances keep turning up in files nobody was
  auditing, which is weak-but-accumulating evidence that a deliberate pass finds more.

## Severity

**No data at risk; agent instructions are wrong.** Nothing is corrupted and no number
reaches a baseball decision. The cost is that an agent following a skill literally does
the wrong thing — writes a status word the doc gate rejects, greps for a file that
isn't there, or grounds itself in a document that does not exist. Instance 4 is the
sharpest: three planning agents were told to read a file that has never existed, on
every planning run since the port.

**Not urgent.** The two highest-traffic instances are fixed and the mechanical half is
now guarded. This is cleanup with a real but bounded payoff.

## Triage

- **Verdict:** needs-full-track
- **Obviousness hint (non-binding):** the *instances* are obvious once seen; the
  **scope** is not. This is a search problem, not a diagnosis problem — which is exactly
  why it needs a written scope before anyone starts editing.

## Affected Area & Pointers

1. `.claude/skills/implement-plan/SKILL.md` — Step 7's terminal stage word, instance #6
2. `tests/test_skill_references.py` — the mechanical half that exists; what it covers is
   the boundary of what is already handled
3. `requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md` —
   the port-drift class, with instances 1–4 evidenced
4. `.claude/agents/data-engineer-memory.md` — three 2026-08-17 entries record what the
   widened guard actually found

## Open Questions for Diagnosis

- **What is the vocabulary of "residue"?** A missing file is mechanical. A wrong stage
  word is checkable against a README. A worked example from the wrong sport is neither —
  it needs a human read. Are these one request or three?
- **Is a mechanical guard possible for the non-path classes**, or does this end in a
  one-time human pass plus a checklist for the next port?
- **How far does the sweep reach?** `.claude/skills/` only, or `.claude/agents/`, the
  ADRs, and `ops/` too? Each widening multiplies the read.
- **What stops the next port from doing this again?** The most valuable output may be a
  porting checklist rather than the fixes themselves.
- **Not a regression.** Everything here arrived with the scaffolding port and has been
  true since day one.

## Stage plan

**Full pipeline.** Trigger 1: Open Questions is non-empty, and the first is load-bearing —
whether this is one request or three changes what gets built. Trigger 2 also fires: the
*Explicitly out* boundary genuinely cannot be filled yet, because nobody has measured how
much residue exists. That is the honest reason this is an intake and not a fix.
