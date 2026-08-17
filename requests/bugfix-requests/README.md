# Bugfix Requests

For **defects in things that already exist and fail** — a parser that raises, a
dbt model that won't compile, a CI job that passes when it shouldn't, a path
resolution that breaks, a skill that misfires, a regression.

> **Something must have actually failed.** If the pipeline was green and the
> output is still wrong, it is a
> [data incident](../data-incidents/), not a bug. If the capability never existed,
> it is a [feature](../feature-requests/).

## The pipeline

| # | Stage | Skill | Produces |
|---|---|---|---|
| 1 | **Intake** | `/make-bugfix-request` | `BUGFIX_REQUEST.md` — symptom, reproduction, expected vs actual, severity |
| 2 | **Root cause** | `/diagnose-bug` | `ROOT_CAUSE_ANALYSIS.md` — confirmed cause with `file:line` evidence, a committed failing repro, a verdict, a tiered fix posture |
| 3–4 | **Plan → Implement** | shared back half | Reuses `/create-implementation-plan` → `/implement-plan`, auto-detected from the artifact path |

Stage 2 opens with an **obviousness funnel**: an obvious one-liner gets a terse
inline RCA, and a true one-liner may go straight to fix-plus-test. A murky cause
escalates.

**"Done" means the red reproduction goes green and a regression test is left
behind.** A defect with no recorded repro, cause, or guard is how the same bug
comes back.

## Layout

```
bugfix-requests/
  <slug>/
    BUGFIX_REQUEST.md
    ROOT_CAUSE_ANALYSIS.md
    IMPLEMENTATION_PLAN.md     # if the fix warranted one
    IMPLEMENTATION_REPORT.md
    reviews/
  _done/<slug>/
```

Every artifact opens with a status blockquote:

> **Status:** &lt;stage&gt; · created &lt;YYYY-MM-DD&gt; · &lt;open | decided&gt; · next: &lt;stage&gt;

**Status grammar:** `intake` → `diagnosed` → `planned` → `fixed`

## Index

| Bug | Stage | Notes |
|---|---|---|
| [doc-link-guard-mismatch](doc-link-guard-mismatch/) | intake | Six skills name `tests/test_request_links.py`, which does not exist; the guard that does exist rejects fenced links, `file.py:123` citations and `var/` targets that those skills promise are exempt |
| [leak-guard-blind-to-untracked-files](leak-guard-blind-to-untracked-files/) | intake | `test_no_leaks.py` enumerates via `git ls-files`, so a banned pattern in a new file passes until it is staged — the guard fires only once a leak can enter history, and it is the repo's only leak protection |
| [verify-batching-guard-red-on-arrival](verify-batching-guard-red-on-arrival/) | intake | `verify_batching_guard.mjs` exits 1 on a clean checkout and always has, so stage 4's Verify phase is unproven; fails byte-identically in `nba2k-rpg` from a separately-adapted copy, which points the defect at the shared ported logic |
