> **Status:** fixed · created 2026-08-17 · decided · next: commit

# Implementation Report — Repair the ported guards, and make the promises they carry true

> **One-line outcome:** the batching guard exits 0 for the first time in this repo's
> history, and the link guard now implements all five promises five skills make about it ·
> **Acceptance:** the bugfix contract is met — red repro green, regression guards left
> behind, nothing else regresses · **Branch:** `verify-batching-guard-red-on-arrival`
>
> **This report closes TWO requests** — `verify-batching-guard-red-on-arrival` and
> `doc-link-guard-mismatch`, whose gated decision the operator disposed on 2026-08-17.

## 1. Acceptance ledger

The bugfix track's contract is *"the red repro goes green + a regression test is left
behind + nothing else regresses"* (`requests/bugfix-requests/README.md`). Every row below
was verified by running it, and independently re-run by the acceptance panel's verifier.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| U1 | The committed red repro goes GREEN | **met** | `uv run pytest -m "not gamedata"` → 190 passed, 0 failed. Baseline 2026-08-17 was `2 failed, 170 passed` |
| U1b | The human-readable symptom is resolved | **met** | `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` → exit 0, four diagnostic lines byte-identical to the plan's pinned text |
| U2 | A regression test is left behind, assertions not weakened | **met** | Both `tests/test_skill_references.py` assertions intact and **widened**; plus a new in-process check in the guard itself and 19 tests in `tests/test_doc_link_contract.py` |
| U3 | Nothing else regresses | **met** | ruff `All checks passed!` · `ruff format --check` 120 files clean · mypy `Success: no issues found in 39 source files` · all five `.mjs` guards exit 0 |
| P1 | Phase 1 — fixture re-keyed, panel untouched | **met** | `raw=11 deduped=9 batches=4/4 unverified=0`; exactly one net test flipped; `acceptance_panel.js` absent from every diff |
| P2 | Phase 2 — an orphaned lens fails by name | **met** | Three deliberately re-broken copies each exit 1 naming the orphan, with **no** `[cap+dedupe]` line and no `dedupe:`/`coverage:` cascade |
| P3 | Phase 3 — seven dead references repointed | **met** | `git grep test_request_links -- .claude/skills/` → zero hits; 11 files legitimately retain the token as quoted evidence |
| P4 | Phase 4 — status grammar settled | **met** | Seven sites corrected; the four surviving `root-cause` uses are frontmatter pipeline descriptions and a `next:` slot, all deliberate |
| P5 | Phase 5 — link guard matches its promise | **met** | 19 contract tests; both halves proven to bite on a live probe, with fenced / line-suffixed / `var/` controls correctly silent |
| P6 | Phase 6 — reference guard widened | **met** | Went RED naming three phantom-doc sites, green after the fix |
| P7 | Phase 7 — record | **met** | This report, three memory entries, both Index rows, the D5 intake |
| P8 | Phase 8 — guards run in CI, and the step is not vacuous | **met** | Green run on the PR with `Skill guards (node)` passing; then a deliberate probe commit turned **that step and only that step** red, with ruff, format, mypy and pytest all green ahead of it — see §6 |

**One criterion is deliberately not claimed.** Nothing here tests the acceptance panel's
*behaviour* against a real run. The guard tests its dedupe and batching against a synthetic
fixture. Whether the panel finds real bugs is out of scope and is not asserted.

## 2. What shipped

**The batching guard** (`verify_batching_guard.mjs`) — two fixture keys re-keyed to this
repo's lenses, the stale roster comment corrected, and a new fixture/roster agreement check
that runs *first* and exits before the counting assertions can cascade. Routed through one
`reportRedAndExit()` helper so there is a single RED path. `acceptance_panel.js` was never
opened for writing, which the RCA proved correct and every reviewer agreed on.

**Seven dead references** repointed across six skills, plus a worked example re-grounded
from an NBA season to a real, runnable test in this repo.

**The status-word grammar** settled at seven sites in two skills, prose only — no
mechanical guard, per D3.

**The link guard** (`tests/test_doc_links.py`) rewritten from a single regex pass into
callable rules: a line-level fence pre-pass (``` and ~~~, blockquoted, list-item-indented,
length-aware), a line-suffix normaliser, a link-title stripper, a `var/` target exemption,
and the bare-`requests/...`-token scan that was promised but never existed.

**The reference guard** widened to `.js`/`.mjs` and to `docs/*.md`, which found three
phantom-doc sites in two panel scripts.

**CI** gained a pinned `actions/setup-node` and a `Skill guards (node)` step running all
five guards by explicit path under `set -euo pipefail`.

## 3. Deviations from the plan

- **The nine `/commit`-gated phases were accumulated into one diff.** `/implement-plan`
  prescribes one accumulated diff and one panel; the plan prescribed a checkpoint per
  phase. The skill governs the stage, so I followed it — at the cost of three per-phase
  delta criteria (P1's "exactly one net test flipped" was checked live but is not
  reconstructible from git history). Recorded because it is a real loss, not a tidy-up.
- **Phase 6 edited two files the checklist did not name** — `plan_panel.js:164` and
  `scope_panel.js:125`, both genuine instances of the same phantom `docs/data-sources.md`.
  Phase 6's acceptance could not go green without them. The plan's checklist was
  under-specified, which is itself a small vindication of widening the guard.
- **Three memory entries were appended where the plan mandated one.** All append-only,
  all labelled, `test_memory_entries_carry_an_epistemic_label` green. The mandated entry
  honours D4 exactly: it refutes only the *interpretation* of the 2026-08-15 entry and
  states that entry's sibling-repo measurement "stands and was not re-tested here".
- **The red repro's test was renamed** — `test_every_test_file_a_skill_names_exists` →
  `test_every_repo_path_a_skill_names_exists`, because Phase 6 widened it beyond test
  files. The RCA and plan cite the old selector; both are decided artifacts and were not
  edited. **A reader following those citations will not find the test by that name.**
- **`requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` was edited** — one
  checklist line fenced, as the consequence of dropping the own-directory exemption.

## 4. Verification & edge cases

Four independent channels, because a green suite is not proof here:

1. **The guard's own exit code**, with four diagnostic lines pinned byte-for-byte.
2. **The Python guards in CI** — `test_skill_references.py` and `test_doc_links.py` run on
   every PR; the `.mjs` guards do not until Phase 8's step is proven.
3. **Deliberate re-breaking.** Every guard shipped or extended here was *watched failing*:
   three re-keyed fixture copies, a broken relative link, a dead bare token, and a
   mistyped artifact name. A green guard nobody has seen fail is a guard nobody has tested.
4. **A byte-level negative check** — `acceptance_panel.js` absent from `git diff --stat`.

**Edge cases exercised:** a fence opened on a list-item line; a blockquoted fence; a
tilde fence; an unterminated fence; a ``` inside a ```` block; a line range with an en
dash; a link title in three quoting styles; a titled link to a dead file; a glob; an
angle-bracket placeholder; a `var/` lookalike (`variance.md`).

## 5. Findings resolved

The panel ran at full strength — 7/7 reviewers, 5/5 verifiers, `findings_unverified` **0**,
meta-audit 1, no degraded lenses — and returned `fix` with 19 confirmed findings. Every
objective one was fixed and re-verified. **Three were real defects in code written during
this build**, all in the new link guard, and all confirmed by my own probes before fixing:

| Finding | Fix |
|---|---|
| **MAJOR** `strip_fences` missed a fence opened on a list-item line (`commit/SKILL.md:189` is literally ``2. ``` ``), flipping parity and silently blanking **76 of 194** non-blank lines to EOF | `FENCE` accepts a list-item prefix. That file now scans 164 of 194 lines (30 genuinely fenced) |
| **MAJOR** An unterminated fence blanked the rest of the document with no diagnostic | `strip_fences` now restores everything from a dangling opener — it fails *toward checking*, so a missing fence costs a false positive rather than silent blindness |
| **MAJOR** A fifth documented promise, "link titles are exempt too", was never implemented | `LINK_TITLE` strips a quoted title in three styles, with a negative test proving it cannot launder a dead path |
| **MAJOR** The own-directory exemption keyed on directory alone, silencing typo'd sibling pointers | **Dropped entirely** per the operator's disposition; the one affected line in first-sight's plan is fenced instead — the documented remedy |
| **MINOR** `partition` fragility could drop a file's tail from the scan | Returns the whole text on a failed partition |
| **MINOR** A `"*" in token` filter that could never fire made a test pass for the wrong reason | Dead branch removed; the test now asserts through the pattern itself |
| **NIT** A ``` closed a ```` block | Fence length compared, per CommonMark |
| **NIT** `_done/` was scanned although the promise says live bodies only | Excluded |
| **NIT** `docs/` pattern was case-sensitive, and matched mid-path (`../update-docs/SKILL.md` → phantom `docs/SKILL.md`) | Widened, with a leading boundary |
| **NIT** The re-grounded worked example named a test that does not exist | Repointed at a real offline test — **caught by the very guard this request added** |
| **NIT** The guard header said "four properties" above a list of five | Corrected |

**Two panel claims I did not accept.** Its "29% / 209 markdown files / 92 blanked lines"
figures were wrong (75 of 194, 82 files), and one reviewer's assertion that the own-dir
exemption hid the missing report was false — the plan carries no such token. The panel
caught both itself and corrected them rather than laundering them forward.

## 6. Manual gates & user-run steps — both COMPLETED 2026-08-17

The operator disposed that Phase 8's proof happen on this PR rather than a follow-up.
Both steps ran; the CI gate is proven in both directions.

1. **The guards step runs green in CI.** ✅ Observed by the operator on the PR: the
   `Lint, types, tests` job passed with `Skill guards (node)` included.
2. **The step is not vacuous.** ✅ Commit `7bab8d5` deliberately broke one duplicate-pair
   title in the fixture; the operator confirmed `Skill guards (node)` went **red**. Reverted
   in the next commit, restoring the file byte-identical to `7ab0362`.

**The probe's design is the part worth keeping.** The obvious mutation — re-keying a fixture
lens back to `data-contract` — was tried first and **rejected**: it also fails
`tests/test_skill_references.py`, pytest runs *before* the guards step, and the job would
have stopped early without ever executing the step under test. A green-then-red-at-the-right-step
sequence is the only evidence that distinguishes a working gate from one that silently runs
nothing, and a mutation that trips an earlier gate cannot produce it. Ruff, format, mypy and
pytest were all confirmed green under the probe before it was pushed.

**Epistemics, stated rather than assumed.** The runner's node version is `pinned` at 22 via
`actions/setup-node`, not `measured` — the `node --version` line is emitted into every log by
design, but was not read back here. Local runs were v24.15.0. The pin is what makes the
difference immaterial; the RCA's *unconfirmed* "ubuntu-latest ships node" claim is now moot
rather than confirmed, and no doc asserts it.

## 7. Hand-off

`/commit` is next; it stages, runs the doc gate — expect it to trigger on
`.claude/agents/data-engineer-memory.md` appearing in the diff, which is by design — and
pushes the branch. Opening the PR stays the operator's.

**What this does NOT close:**

- **`requests/bugfix-requests/leak-guard-blind-to-untracked-files/`** is untouched at
  `intake`. It bit twice during this work: 27 absolute machine paths reached an untracked
  trail file and were caught only by a manual scan. That request has earned priority.
- **`requests/bugfix-requests/port-residue-sweep/`** was filed here per D5, carrying six
  known instances. One of them — `implement-plan/SKILL.md` Step 7 telling both tracks to
  use `implemented` when the bugfix terminal word is `fixed` — is **live and unfixed**,
  and was deliberately left rather than widening this request's scope a third time.
- **Archiving both `fixed` requests into `_done/`** is due and deliberately deferred:
  18 files reference these two directories by path, and the bare-token scan shipped here
  would catch every stale one, so it is a mechanical commit of its own rather than more
  churn on this diff.
