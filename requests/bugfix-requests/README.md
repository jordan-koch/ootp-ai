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
| [fixed-offset-guard-cannot-see-subscripts](fixed-offset-guard-cannot-see-subscripts/) | planned | `test_no_fixed_offsets.py` flags `.seek(<literal>)` and `unpack_from(..., <literal>)` and **never inspects a subscript**, so the same wrong read is caught as `unpack_from("<I", data, 58)` and silent as `data[start + 58 : start + 62]` — the spelling this parser's byte-slicing style makes likeliest. Meanwhile `CLAUDE.md:103` says CI enforces the ban and the guard's docstring claims zero exemptions. Nothing is mis-parsed today; every current instance was surveyed and each is defensible. The hard part is the **rule**, not the fix: flagging every `data[x + N]` would fire on length-prefix arithmetic and date decoding throughout the parser, and this guard's own docstring says a guard that cries wolf gets loosened. Narrowing the docs instead is a live third option, since `Cursor` carries the real structural guarantee |
| [doc-link-guard-mismatch](_done/doc-link-guard-mismatch/) | fixed | Six skills name `tests/test_request_links.py`, which does not exist; the guard that does exist rejects fenced links, `file.py:123` citations and `var/` targets that those skills promise are exempt. Diagnosed jointly with the batching guard as one port-drift class; the promised bare-token scan is a **dropped capability**, not just missing exemptions. Gate disposed 2026-08-17 — **extend the guard**. This request has no plan or report of its own: both live in `verify-batching-guard-red-on-arrival/` (Phase 5 of its plan, §5 D1 of its report), which is why its own directory stops at `diagnosed` |
| [leak-guard-blind-to-untracked-files](_done/leak-guard-blind-to-untracked-files/) | fixed | `test_no_leaks.py` **used to** enumerate via `git ls-files`, so a banned pattern in a new file passed until it was staged — the guard fired only once a leak could enter history, and it is the repo's only leak protection. It bit three times on 2026-08-17, every one caught by a hand scan importing the guard's own `PATTERNS` and none by the guard. Now enumerates `--cached --others --exclude-standard`, hardened against git's C-quoting of non-ASCII paths (`text=True` decodes cp1252 here, so `-z` alone was not enough), and **seen to fail** — a no-op mutant that previously left all 18 tests green now dies |
| [port-residue-sweep](port-residue-sweep/) | intake | Six known places where the ported skills still describe a sibling repo — five found by accident while fixing something else, one (`implement-plan/SKILL.md`'s terminal stage word) still live. Filed per D5 of the batching-guard plan. The scope, not the instances, is the hard part: a missing file is mechanical, a wrong stage word is checkable, an NBA-season worked example is neither |
| [verify-batching-guard-red-on-arrival](_done/verify-batching-guard-red-on-arrival/) | fixed | `verify_batching_guard.mjs` exits 1 on a clean checkout and always has, so stage 4's Verify phase is unproven. **Cause: the guard's fixture, not the panel** — two lens keys name a sibling repo's specialists, `\|\| []` swallows them, and all six failure lines follow from the 3 findings lost. Proven by re-keying two words and going green with the panel untouched. Carries the joint port-drift analysis |
