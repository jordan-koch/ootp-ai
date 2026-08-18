<!-- Raw, unfiltered panel output. Saved by /create-implementation-plan step 3.
     REPOINTED: when this request was archived, every `requests/bugfix-requests/<slug>/`
     path in this file was rewritten to its `_done/` location so a reader can still follow
     it. `_done/` is excluded from tests/test_doc_links.py, so this was for the reader, not
     for CI. Only path prefixes changed; no agent's wording was altered. -->


# Planning panel — adversarial + meta-audit findings

Two code-grounded adversaries and one meta-audit, run 2026-08-17.
Stats: {"planners_ok": 3, "adversaries_ok": 2, "meta_audit_ok": 1, "findings": 35, "blockers": 1, "majors": 9} · degraded_lenses: []

## Adversary findings (22)

### [BLOCKER] Four of five gated decisions change phase content, but disposing them is never stated as a precondition to Phase 0

- **Location:** `plan §gated_decisions 1-4 + phases[3].steps ("SEE GATED DECISION 2 before writing"), phases[4].name ("Include this phase only if gated decision 3 is disposed in favour"), phases[6].steps ("See gated decision 4")`
- **Confidence:** high
- **Category:** sequencing

**Problem**

The plan's own phase text defers to undisposed gated decisions at four separate points, and those decisions do not merely colour the work — they change which files get edited, whether two whole phases exist, and what the passing test count is. GD1 sets how far Phase 3 goes into the four "What good looks like" bullets. GD2 decides whether `create-implementation-plan/SKILL.md:172`/`:176` are corrected, which in turn decides whether Phase 4's new grammar guard can be green at all. GD3 decides whether Phases 5 and 6 exist. GD4 decides whether Phase 7 touches `.claude/agents/data-engineer-memory.md`. Nothing in `onboarding` or Phase 0 tells the implementer that all five must be disposed before work starts. A COLD agent — which is exactly the audience the stage-3 contract names — reaches Phase 3 step 3 and Phase 4 step 6 with no disposition on record and must either guess (the outcome both RCAs name as the worst available) or stop. `.claude/skills/create-implementation-plan/SKILL.md:67-69` treats an `open` disposition as a loud warning precisely because planning on unmade decisions is the failure being guarded against; this plan reproduces that failure one stage later.

**Proposed fix**

Add a Phase 0 step, stated as a hard precondition: "BEFORE any edit, confirm every gated decision in this plan has been disposed by the operator and record the disposition inline in this document. If any is still open, STOP and ask — do not take the recommendation by default." Then make each dependent phase read the disposition rather than deferring: give Phase 3, Phase 4 and Phases 5-6 an explicit two-branch instruction ("GD2 in favour → also correct `:172`/`:176` and add the grammar guard; GD2 against → correct only `:56`/`:65`, do NOT add the guard, and Phase 4 ends at `172 passed`").

### [MAJOR] Phase 3's grep acceptance criterion is false on today's tree and points the implementer at archived artifacts

- **Location:** `requests/bugfix-requests/README.md:51`
- **Confidence:** high
- **Category:** acceptance-criteria-wrong

**Problem**

Phase 3 acceptance criterion 4 reads: "Grepping the repo for `test_request_links` and `test_extract_pagination` returns hits ONLY inside `requests/bugfix-requests/*/BUGFIX_REQUEST.md` and `*/ROOT_CAUSE_ANALYSIS.md`." I ran that grep. It hits 14 files, and five of the survivors are neither a BUGFIX_REQUEST nor an RCA: `requests/bugfix-requests/README.md:51` (the doc-link Index row's Notes cell quotes the token), `tests/test_skill_references.py:50` (the repro's own docstring), `requests/feature-requests/_done/agent-memory-curation/FEATURE_REQUEST.md` (an archived artifact), and `requests/feature-requests/first-sight/reviews/plan-proposals.md` + `plan-adversarial.md` (committed review records). The plan also contradicts itself here: Phase 7 explicitly requires `requests/bugfix-requests/README.md:51` to stay byte-unchanged, while Phase 3's criterion says a hit there means the phase is not done. A cold implementer resolving that contradiction the wrong way rewrites an Index row, a docstring, an archived `_done/` request and two frozen adversarial review records — none of them in scope, and the review records are historical evidence that must not be edited.

**Proposed fix**

Replace criterion 4 with the one part that is actually true and load-bearing — "`rg 'test_request_links|test_extract_pagination' .claude/skills/` returns zero hits" — and enumerate the legitimate survivors explicitly so they read as expected rather than as failures: `requests/bugfix-requests/README.md:51`, `tests/test_skill_references.py`'s docstrings, both `doc-link-guard-mismatch` artifacts, this slug's `BUGFIX_REQUEST.md`/`ROOT_CAUSE_ANALYSIS.md`, `requests/feature-requests/_done/agent-memory-curation/FEATURE_REQUEST.md`, and the two `requests/feature-requests/first-sight/reviews/*.md` files. Add one line: "archived and review artifacts are historical records — never edit them to satisfy a grep."

### [MAJOR] The plan freezes the repro module's docstrings in their pre-fix tense, leaving the exact prose drift the request is about

- **Location:** `tests/test_skill_references.py:50`
- **Confidence:** high
- **Category:** doc-drift

**Problem**

`files_to_touch` says of `tests/test_skill_references.py`: "The two EXISTING tests are the red repro and the regression guard — DO NOT modify or weaken them", and Phase 1's onboarding repeats "DO NOT rewrite it to fit the fix." That is right about the ASSERTIONS and wrong about the prose. `:50-53` states as present fact: "Six skills instruct the agent to run `tests/test_request_links.py`. There is no such file" — false the moment Phase 3 lands. `:89-92` states: "Measured — two ported keys (`data-contract`, `extraction` …) cost the fixture 3 of its 11 findings" — false the moment Phase 1 lands. The module docstring at `:1-12` is written entirely in the present tense about a live defect. So the plan ships a green regression guard whose own documentation asserts the bug is still there: a ported-artifact-describes-a-repo-that-does-not-exist defect, in the file created to catch that defect class. `/commit`'s doc gate is judgment-based and may or may not catch it, and no mechanical check will.

**Proposed fix**

Split the instruction. Keep "the two assertions and their regexes are untouched — never weaken them to fit the fix", and ADD an explicit step in Phase 3 (the phase that closes the contract): move the three docstrings to past tense with a pointer, e.g. `:50` → "Six skills used to instruct the agent to run `tests/test_request_links.py`, which has never existed here; they were repointed at `tests/test_doc_links.py` — see `requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/`." Same for `:89-92` and the module docstring. State in the commit note that only prose moved, so a reviewer can confirm the assertions are byte-identical with `git diff -U0 tests/`.

### [MAJOR] Phase 3's grep acceptance criterion is factually wrong and will read as a failure on a correct implementation

- **Location:** `plan phases[2].acceptance[3] — "Grepping the repo for `test_request_links` and `test_extract_pagination` returns hits ONLY inside `requests/bugfix-requests/*/BUGFIX_REQUEST.md` and `*/ROOT_CAUSE_ANALYSIS.md`"`
- **Confidence:** high
- **Category:** acceptance-criterion

**Problem**

I ran `git grep -n test_request_links` on the clean tree. After Phase 3 removes the six skill references, the token still survives in SIX places outside the two named file patterns: `requests/bugfix-requests/README.md:51` (the doc-link Index row, which this same plan says must stay byte-unchanged), `tests/test_skill_references.py:50` (the committed repro's docstring, which the plan says must not be modified), `requests/feature-requests/_done/agent-memory-curation/FEATURE_REQUEST.md:183`, and `requests/feature-requests/first-sight/reviews/plan-adversarial.md:24` and `:749` plus `plan-proposals.md:1568`. A cold agent running this criterion literally sees six unexpected hits and has exactly two moves: waste a cycle re-diagnosing, or edit the README Index row and the repro docstring to satisfy it — both explicitly forbidden by `files_to_touch` ("Leave `:51` … byte-unchanged", "DO NOT modify or weaken them"). The criterion actively steers toward a forbidden edit. (`test_extract_pagination` is fine — its only survivors are in this RCA.)

**Proposed fix**

Restate the criterion as the check that actually matters and is actually true: "`git grep -n test_request_links -- .claude/skills/` returns ZERO hits, and `git grep -n test_extract_pagination -- .claude/skills/` returns zero hits." Then add, as a separate note: "The token deliberately survives elsewhere — the two bugfix RCAs and `BUGFIX_REQUEST.md`s quote it as evidence, `requests/bugfix-requests/README.md:51` describes the open doc-link defect, `tests/test_skill_references.py:50` documents what its assertion catches, and three `_done`/`reviews` artifacts are historical records. None of these may be edited."

### [MAJOR] The record phase that completes the bugfix acceptance contract is sequenced behind two human-gated optional CI phases

- **Location:** `plan phases[4].commit_note ("hand the branch to the user, and STOP until the log line comes back") → phases[5] → phases[6] ("Record: statuses, Index, memory, and what stays open")`
- **Confidence:** high
- **Category:** sequencing

**Problem**

Phase 5 ends in an unbounded human wait for a CI log line, and Phase 6 is explicitly gated on that measurement. Phase 7 carries everything that makes the work legible afterwards: the Index row advance at `requests/bugfix-requests/README.md:53`, the status blockquotes on both artifacts, the falsified agent-memory correction, and the IMPLEMENTATION_REPORT. But the acceptance contract at `requests/bugfix-requests/README.md:24-26` is already fully met at the end of Phase 3 (repro green, regression guard left behind). So the plan parks the paper trail for a DONE fix behind two optional, human-blocked, admittedly-out-of-scope-if-the-user-says-so phases. An agent that reaches Phase 5 stops with the Index row still reading `diagnosed` and no report — and if the operator disposes GD3 against, the phase numbering leaves the recording orphaned with no instruction on where it goes.

**Proposed fix**

Renumber: make the record phase Phase 5 (immediately after Phase 4, where the contract is met and the fix is complete), and demote the CI work to trailing Phases 6 and 7 marked "optional, after the record phase; may be split into a separate follow-up PR." Add an explicit terminal statement to the record phase: "A run may end cleanly here. The acceptance contract is met, the Index row and both status headers are current, and the CI hardening is separable."

### [MAJOR] Phase 4's acceptance asserts `173 passed, zero failures` unconditionally, contradicting its own steps

- **Location:** `plan phases[3].acceptance[2] vs phases[3].steps[5] ("SEE GATED DECISION 2 before writing") and steps[7] ("Only `diagnose-bug/SKILL.md:107` and `create-implementation-plan/SKILL.md:176` fail today — which is why `:176` must be corrected if the guard is added")`
- **Confidence:** high
- **Category:** acceptance-criterion

**Problem**

Phase 4 both defers `:172`/`:176` to gated decision 2 AND states a flat acceptance of `173 passed, 62 deselected, zero failures`. Those cannot both hold. I confirmed by grep that exactly six `> **Status:**` templates exist under `.claude/skills/`, and that under the union of the two grammars — `{intake, diagnosed, planned, fixed, scoped, implemented}` from `requests/bugfix-requests/README.md:45` and `requests/feature-requests/README.md:110` — precisely two fail today: `diagnose-bug/SKILL.md:107` (`root-cause`) and `create-implementation-plan/SKILL.md:176` (`plan`). If GD2 is disposed against, `:176` stays `plan`, the new guard is permanently RED, and the phase can never reach `173 passed` — the plan even says so in GD2's own text ("leaving it means shipping a guard red on a file the plan declined to touch") but never propagates that into the acceptance list. A cold agent hits an unsatisfiable criterion with no branch to take.

**Proposed fix**

Split the acceptance on the disposition. "GD2 in favour: `:56`, `:65`, `:172`, `:176` and the three `diagnose-bug` sites corrected, grammar guard added, `uv run pytest -m \"not gamedata\"` → `173 passed, 62 deselected`. GD2 against: correct `:56`, `:65` and the three `diagnose-bug` sites only, DO NOT add the grammar guard (it would land red on a line this request declined to touch), and Phase 4 ends at `172 passed, 62 deselected` — file the `plan`→`planned` correction as a separate intake."

### [MAJOR] Phase 7 instructs the implementer to create the IMPLEMENTATION_PLAN it is executing

- **Location:** `plan phases[6].steps[0] ("Open `requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md` with `> **Status:** planned · created <today> · decided · next: implement`") and files_to_touch entry for the same path ("NEW — the stage-3 deliverable")`
- **Confidence:** high
- **Category:** sequencing

**Problem**

By the time Phase 0 runs, this plan document exists and is committed — it IS the artifact stage 4 was handed. Instructing the implementer to create it, at stage word `planned · next: implement`, is circular: the implementer either overwrites the plan mid-execution or stalls trying to work out which stage it is in. The confusion is doubled by `files_to_touch` labelling it NEW, alongside a genuinely-new `IMPLEMENTATION_REPORT.md`. The stage-3 skill's own template ownership (`.claude/skills/create-implementation-plan/SKILL.md:173`) makes clear the `planned` header is written at plan-authoring time, not at implementation time.

**Proposed fix**

Change the step to "ADVANCE the existing `IMPLEMENTATION_PLAN.md` status blockquote in step with the Index row (`planned` → the terminal word once the fix lands), leaving its body untouched — it is the decided artifact you are executing." Change the `files_to_touch` entry from "NEW — the stage-3 deliverable" to "EXISTS — status blockquote at `:1` advanced in Phase 7; body untouched." Keep IMPLEMENTATION_REPORT.md as the only NEW artifact.

### [MAJOR] The stated functional justification for widening Phase 4 into create-implementation-plan/SKILL.md is contradicted by that file's own disposition gate

- **Location:** `plan decisions[7] and phases[3].steps[2] ("the stage-3 disposition gate would reject a correctly-written `diagnosed` RCA — including the one this plan was built from") vs `.claude/skills/create-implementation-plan/SKILL.md:63-66``
- **Confidence:** high
- **Category:** grounding

**Problem**

I read the gate. `:63-66` says verbatim: "The Status blockquote has four fields … **Gate on the 3rd field (the disposition), not the stage word** — a ready scope correctly reads `scoped · … · decided · next: plan` and a ready bugfix RCA reads `root-cause · … · decided · next: plan`, so the stage word appearing is *expected*, not a problem." And `:57-58` adds that the Index Stage cell can lag and must be cross-checked against the artifact's own blockquote. So the drift at `:56`/`:65` is a stale Index-lookup hint and a stale worked example — real, worth correcting, but with NO gate consequence. The plan elevates it to "not cosmetic" and "the stage-3 disposition gate's own criterion," which is the load-bearing argument for widening a decided scope past what the RCA enumerated. Worse, an implementer who believes the gate is broken may go and rewrite `:63-69` — the disposition-gate prose the plan nowhere authorises touching. Proof the claim is false in practice: this very plan was produced from an RCA whose header reads `diagnosed · created 2026-08-17 · decided · next: plan`, and the gate did not reject it.

**Proposed fix**

Rewrite the rationale to what is true: "`:56` is an Index-lookup hint naming a stage word the bugfix track does not define, and `:65`'s worked example teaches it. Both are drift of the same class as `diagnose-bug/SKILL.md:107`. Neither breaks the disposition gate — `:64` gates on the 3rd field, not the stage word, and this plan's own upstream RCA passed it while reading `diagnosed`. Correct the two stage words and NOTHING else in that section; `:63-69` is not in scope."

### [MINOR] "7 lenses" in the guard header is defensible, and the plan orders it changed to 6 as if it were flat drift

- **Location:** `.claude/skills/implement-plan/tests/verify_batching_guard.mjs:11`
- **Confidence:** high
- **Category:** over-correction

**Problem**

Phase 1 step 6 says: "Fix the header comment at `:11`, which says `N findings across 7 lenses`; the fixture defines six." I instrumented the panel run: it requests exactly SEVEN review lenses — `acceptance, correctness, edgecases, fidelity, parser, skill-quality, warehouse` (4 CORE at `acceptance_panel.js:189-194` plus the 3 specialists `AREA_TO_SPEC` resolves at `:203-207`). Six of those seven carry fixture findings; `acceptance` is answered by `validAcceptanceReview()` at `:68-76` and legitimately emits none. So the header sentence — "N findings across 7 lenses collapse to <= cap batch agents" — reads correctly as describing the seven-lens roster the findings are collected across. Changing it to 6 replaces one ambiguous number with another, in the one file whose comment drift is the subject of the bug, and the plan asserts the correction as fact rather than as a judgment call.

**Proposed fix**

Either drop the `:11` edit from Phase 1 (it is not part of the defect and the RCA does not name it), or make it unambiguous rather than merely different: "N findings raised across 6 of the panel's 7 requested lenses". If it is kept, state in the plan that it is a wording clarification, not a corrected fact — the measured roster is 7.

### [MINOR] Phase 2's "`raw=8, expected 11` must NOT appear" criterion passes vacuously in all three demonstrations it gates

- **Location:** `.claude/skills/implement-plan/tests/verify_batching_guard.mjs:199`
- **Confidence:** high
- **Category:** vacuous-check

**Problem**

Phase 2's PROVE IT BITES criterion requires re-breaking ONE fixture key at a time and asserts "the string `raw=8, expected 11` must NOT appear." The fixture totals 11 across six keys (fidelity 3, correctness 2, edgecases 2, warehouse 2, parser 1, skill-quality 1). Re-breaking only `warehouse`→`'data-contract'` drops 2, so `:199` would print `raw=9, expected 11`; re-breaking only `parser`→`extraction` drops 1, giving `raw=10`. `raw=8` arises only when BOTH keys are broken — the pre-fix state, which none of the three demonstrations reproduce. So that clause is true whether or not the new assertion exists or fires, which is exactly the vacuously-passing check the plan itself flags as worse than none (citing `acceptance_panel.js:201` item 4). The two sibling clauses in the same bullet (exit 1; the FIRST printed failure names the key) do bite, so the defect is a redundant criterion rather than a hole — but a cold implementer may treat the vacuous one as the proof.

**Proposed fix**

Restate the clause so it is about the cascade rather than a literal string: "the `[cap+dedupe]` diagnostic line and every `dedupe:`/`coverage:` failure must be ABSENT from the output — the run exits on the fixture assertion before Scenario 1's counting assertions execute." Optionally add a fourth demonstration that re-breaks BOTH keys at once, which is the only configuration where `raw=8, expected 11` is the string the check is really about.

### [MINOR] Phase 4's grammar guard is specified against two track READMEs, but the repo defines three tracks

- **Location:** `requests/README.md:10`
- **Confidence:** high
- **Category:** incomplete-guard

**Problem**

Phase 4 says to "Parse the allowed stage words out of BOTH track READMEs' `**Status grammar:**` lines", and gated decision/testing sections repeat "both". `requests/README.md:6-10` defines THREE tracks — `feature-requests/`, `bugfix-requests/` and `data-incidents/` — and `:12` makes each track's README the contract, not just two of them. I grepped: `**Status grammar:**` exists only at `requests/bugfix-requests/README.md:45` and `requests/feature-requests/README.md:110`; `requests/data-incidents/README.md` carries no Status or grammar line at all today. So a two-README union is correct as of now, but it is hardcoded to a fact that can change, and the guard's only loud-failure path is an EMPTY parse (mirroring `tests/test_skill_references.py:99-100`) — a third track gaining a grammar would not be empty, it would just be silently excluded, and a legitimate data-incident status template would then fail the guard.

**Proposed fix**

Have the guard glob `requests/*/README.md`, collect every `**Status grammar:**` line it finds, union the backticked words, and assert at least two grammars were parsed (not merely that the set is non-empty). Add a one-line comment naming `requests/README.md:12` as why the READMEs are the source rather than a hardcoded list. Blast radius is unchanged today: I checked all six `> **Status:**` template lines under `.claude/skills/` and only `diagnose-bug/SKILL.md:107` and `create-implementation-plan/SKILL.md:176` fail — the plan's claim is correct.

### [MINOR] Phase 5 puts a deliberately CI-reddening probe and a user round-trip ahead of the record-keeping phase

- **Location:** `.github/workflows/ci.yml:37`
- **Confidence:** medium
- **Category:** sequencing

**Problem**

Phase 5 adds a `node --version` step to the `quality` job with "Add NO `continue-on-error`. If node is absent the job SHOULD go red — that is the measurement", then ends at a hard STOP waiting for the user to open a PR and paste a log line. Phase 7 — the statuses, the Index row at `requests/bugfix-requests/README.md:53`, the agent-memory correction and the IMPLEMENTATION_REPORT — is ordered AFTER it. If gated decision 3 is disposed in favour, the acceptance contract (met at the end of Phase 3) cannot be recorded as `fixed` until an optional hardening round-trip completes, and a red probe leaves the branch red while the paper trail is still unwritten. The optional work is correctly last among the CODE phases; the bookkeeping should not be behind it.

**Proposed fix**

Renumber so the record phase runs immediately after Phase 4 and the two gated CI phases run last, or add an explicit note to Phase 7: "this phase may be executed before Phases 5-6 and does not depend on them; if 5-6 land afterwards, the CI measurement is appended to the report rather than blocking it." Also worth stating in Phase 5 that the probe is the LAST commit on the branch before the user's PR, so a red probe never masks the state of the Phase 1-4 commits.

### [MINOR] The architecture map attributes the unknown-area silent failure to the wrong expression

- **Location:** `.claude/skills/implement-plan/acceptance_panel.js:208`
- **Confidence:** high
- **Category:** imprecise-citation

**Problem**

The plan's `code_references` entry for `acceptance_panel.js:208-209` claims "`.filter(Boolean)` is why an unknown area key would also fail silently." Reading the two lines: `:208` is `const specKeys = [...new Set(AREAS.flatMap(a => AREA_TO_SPEC[a] || []))]` — the `|| []` there is what swallows an unknown AREA; `:209`'s `.filter(Boolean)` swallows an unknown SPEC key (a name in `AREA_TO_SPEC`'s values with no matching `SPEC_DEFS` entry). Two different silent failures on two different lines, and the plan swaps them. Minor in isolation, but this plan's whole subject is a `|| []` that swallowed a name mismatch, and the architecture map is the cold implementer's map of the roster's single home — a reader chasing the wrong expression will not find the behaviour described.

**Proposed fix**

Reword to: "`AREA_TO_SPEC[a] || []` at `:208` silently drops an unrecognized touched-area; `.filter(Boolean)` at `:209` silently drops a spec key that `SPEC_DEFS` does not define. Both are the same swallow-a-name-mismatch shape as the fixture's `|| []` at `verify_batching_guard.mjs:78` — noted for the reader, not in scope to change."

### [MINOR] Phase 6's local negative-test step is un-runnable in this repo's shell as described

- **Location:** `plan phases[5].steps[3] ("Chain them so the FIRST non-zero exit fails the step") and acceptance[1] ("A local demonstration of the same command shape exiting non-zero")`
- **Confidence:** high
- **Category:** environment

**Problem**

The CI `run:` block executes under bash on `ubuntu-latest`, where a `set -e` chain or `&&` works. The local environment is Windows PowerShell 5.1, where — per this environment's own documented constraints — `&&` and `||` are a parser error and native exit codes must be read from `$LASTEXITCODE`. So "run the same chained command shape locally" cannot be done as written, and an implementer who copies a PowerShell-flavoured chain into `.github/workflows/ci.yml` ships a step that is either a syntax error or silently swallows exit codes — which is precisely the vacuous-check failure `acceptance_panel.js:201` item 4 and the plan's own risk list name. The plan gives no concrete recipe for either side.

**Proposed fix**

Give the exact CI recipe — a `run: |` block opening `set -euo pipefail`, then `node --version` and one `node <explicit path>` line per guard (five lines, no glob) — and state the local equivalent separately: run each of the five guards as its own PowerShell invocation and check `$LASTEXITCODE` after each, since PowerShell 5.1 has no `&&`. Note that this is a shell difference, not an optional detail: the chaining semantics are the whole point of the step.

### [MINOR] Phase 0 has no environment or branch precondition gate

- **Location:** `plan phases[0].steps — runs `node …` and `uv run …` with no availability check, and checks only `git status --porcelain`, never `git branch --show-current``
- **Confidence:** high
- **Category:** prerequisites

**Problem**

Every phase's primary acceptance runs `node` and `uv`; neither is ever established as present. A cold agent on a machine without node reads `node : command not found` as a guard failure rather than a missing prerequisite — the exact misattribution this whole request is about. Separately, the plan checks the tree is clean but never the branch, while `/commit` (`.claude/skills/commit/SKILL.md:44-47`) explicitly "stops for a decision" when the current branch is `main`. Every phase ends at a `/commit` checkpoint, so on `main` the run stalls at the first gate mid-plan on a question the plan never anticipated. (The current tree happens to sit on `verify-batching-guard-red-on-arrival`, so this bites a fresh checkout rather than today's tree.)

**Proposed fix**

Add to Phase 0: "Record `node --version` and `uv --version`. If node is absent, STOP — the primary acceptance check cannot run and no phase can be verified. Record `git branch --show-current`; if it is `main`, create the working branch first (`git switch -c fix/verify-batching-guard-fixture`) — `/commit` will otherwise stop for a decision at every checkpoint. Note that branch creation is the MAIN THREAD's; a read-only subagent may never run it."

### [MINOR] Phase 4's blast-radius enumeration of status templates is incomplete

- **Location:** `plan phases[3].steps[7] — names `implement-plan/SKILL.md:272`, `make-bugfix-request/SKILL.md:130`, `diagnose-bug/SKILL.md:107`, `create-implementation-plan/SKILL.md:176``
- **Confidence:** high
- **Category:** completeness

**Problem**

There are SIX `> **Status:**` template lines under `.claude/skills/`, not four. The plan omits `make-feature-request/SKILL.md:171` (`intake`) and `scope-feature/SKILL.md:149` (`scoped`). Both are valid under the union, so the plan's conclusion ("only `:107` and `:176` fail today") is correct — but only by luck of the two omissions being feature-track words. An implementer sizing the guard from this list may parse only the bugfix README's grammar, in which case `scoped` and `implemented` become false positives and the new guard lands red on three files nobody scoped.

**Proposed fix**

Enumerate all six in the step, and state the parsed union explicitly so the implementer can check their parse against it: `{intake, diagnosed, planned, fixed}` from `requests/bugfix-requests/README.md:45` ∪ `{intake, scoped, planned, implemented}` from `requests/feature-requests/README.md:110` = `{intake, scoped, diagnosed, planned, implemented, fixed}`. Add: "a parse that yields fewer than six words has drifted — fail loudly, per `tests/test_skill_references.py:99-100`."

### [MINOR] Phase 5's deliberately-failing probe lands in an open PR that branch protection then blocks

- **Location:** `plan phases[4].steps[2] ("Add NO `continue-on-error`. If node is absent the job SHOULD go red — that is the measurement") vs `ops/branch-protection.json` (`"contexts": ["Lint, types, tests"]`, `"enforce_admins": true`) and `.claude/skills/commit/SKILL.md:239-241``
- **Confidence:** high
- **Category:** sequencing

**Problem**

The probe is deliberately fail-open into the SAME `quality` job whose display name is the single required status check, with `enforce_admins: true`. Phase 5 also requires the user to open the PR (CI fires only on `pull_request`, per `ci.yml:3-6`, and `commit/SKILL.md:239-241` warns a first push to a fresh branch triggers nothing). So if node turns out absent, the measurement leaves the PR permanently un-mergeable until Phase 6 resolves it — and Phase 6 is itself gated on that same measurement and on a further operator decision. The plan never says this out loud, so the operator opens a PR without knowing the deliberate red may block their merge.

**Proposed fix**

State the consequence in Phase 5's steps: "This probe is deliberately fail-open into the required check. If node is absent, the PR will be un-mergeable until Phase 6 either adds `actions/setup-node` or the probe step is removed. Tell the operator that before asking them to open the PR, and offer removing the probe as the immediate unblock." Alternatively, follow GD3's own recommendation and pin `actions/setup-node` up front — that removes the failure mode entirely and keeps `node --version` purely informational.

### [NIT] Phase 2 duplicates the RED reporter instead of routing the early exit through one path

- **Location:** `.claude/skills/implement-plan/tests/verify_batching_guard.mjs:285`
- **Confidence:** high
- **Category:** maintainability

**Problem**

Phase 2 step 5 says: "If that check fired, print the RED block and `process.exit(1)` right there, before Scenario 1's remaining assertions run." The guard already has exactly one RED-printing path at `:285-292` (`console.log('\nRED: …')` + the `for (const f of fails)` loop + `process.exit(1)`). Inlining a second copy inside Scenario 1's block gives the file two places that format failures, which will drift — the same one-declaration-many-consumers argument the plan makes convincingly in decision 3 for reading the roster out of `calls` instead of adding a second regex.

**Proposed fix**

Extract the existing block into `function reportRedAndExit() { console.log('\nRED: acceptance verify-batching guard FAILED:'); for (const f of fails) console.log(`  - ${f}`); process.exit(1) }` near `const fails = []` at `:181`, call it from the Phase 2 check, and have `:285` call it too. One RED path, no behaviour change, and the diff stays small enough to review at a glance.

### [NIT] The onboarding says four repair sites in create-implementation-plan/SKILL.md; the plan actually edits five

- **Location:** `.claude/skills/create-implementation-plan/SKILL.md:251`
- **Confidence:** high
- **Category:** internal-inconsistency

**Problem**

`onboarding.files_to_read` says of `.claude/skills/create-implementation-plan/SKILL.md`: "`:56`, `:65`, `:172` and `:176` are themselves four sites this plan repairs, which makes the file self-referential." But `files_to_touch` and Phase 3 also edit `:251` (the sixth dead `tests/test_request_links.py` reference — which I confirmed is at `:251`). Five sites, not four. A cold implementer who works the onboarding note as a checklist stops one edit short in the file that is hardest to keep straight because the plan was written from it.

**Proposed fix**

Change to "`:56`, `:65`, `:172`, `:176` and `:251` are five sites this plan repairs (`:251` in Phase 3, the rest in Phase 4)". While there, note that `:250-256`'s promise prose around `:251` is explicitly out of scope per gated decision 1, so the two adjacent edits are not confused.

### [NIT] Phase 1's `7 lenses` → `6 lenses` header edit is asserted as drift but the original number is defensible

- **Location:** `plan phases[0].steps[6] and code_references entry for `.claude/skills/implement-plan/tests/verify_batching_guard.mjs:11``
- **Confidence:** medium
- **Category:** correctness

**Problem**

The header reads "N findings across 7 lenses collapse to <= cap batch agents". The plan calls 7 wrong because "the fixture defines six". But the ROSTER this run actually spawns is seven: the four `CORE` lenses at `acceptance_panel.js:189-194` plus the three specialists `AREA_TO_SPEC` resolves for `['transform','src','skills']`. The fixture supplies findings for six of those seven because `acceptance` uses a different schema and emits none. So "7 lenses" is a true statement about the roster and "6" is a true statement about finding-emitting fixture keys; the plan presents a contestable reading as settled drift, in a comment whose whole purpose is teaching the next reader the mechanism.

**Proposed fix**

Either leave `:11` alone, or make the edit unambiguous rather than numeric: "N findings raised across the 6 finding-emitting lenses of a 7-lens roster". If the number is changed, have the implementer derive it from `CORE` + `AREA_TO_SPEC` themselves and say which reading they took in the commit body — the same discipline the plan already imposes on the `:150` comment.

### [NIT] Phase 4 sources the stage-word union from 'BOTH track READMEs' while the repo has three tracks

- **Location:** `plan phases[3].steps[6] ("Parse the allowed stage words out of BOTH track READMEs") vs `requests/README.md:10` and `requests/README.md:12``
- **Confidence:** high
- **Category:** completeness

**Problem**

`requests/README.md:10` lists a third track, `data-incidents/`, and `:12` makes each track's README the contract — including that one. I checked: `requests/data-incidents/README.md` carries no `**Status grammar:**` line today, so a two-README parse is currently complete and the guard is correct as of this tree. But the plan hard-codes "BOTH", so the day the incidents track gains a grammar and a skill templates one of its stage words, the guard fails on correct work with a message pointing at the skill rather than at its own short union.

**Proposed fix**

Have the guard glob `requests/*/README.md` for `**Status grammar:**` lines rather than naming two files, keep the existing fail-loudly-on-empty-parse assertion, and add a one-line comment noting that the data-incidents track has no grammar line today so the union is currently two-track. Costs nothing now and removes a future false red.

### [QUESTION] The Phase 7 memory correction over-claims: the RCA never re-tested the sibling repo the falsified entry cites

- **Location:** `.claude/agents/data-engineer-memory.md:151`
- **Confidence:** medium
- **Category:** epistemics

**Problem**

Phase 7 and gated decision 4 describe the 2026-08-15 entry at `:151-155` as falsified outright, because it says the guard's failure is "a pre-existing upstream defect, not a porting error". I read the entry: it is labelled `measured` and its measured claim is that the guard "fails **identically** in the `nba2k-rpg` repo it came from". This request's RCA establishes the cause IN THIS REPO (the fixture names lenses this panel does not define) and never examines the sibling repo — so it decisively refutes the entry's CONCLUSION ("not a porting error") while leaving its OBSERVATION (it also fails upstream) untested. Writing a `verified` correction that asserts the whole entry was wrong would put an unverified claim in the file whose entire purpose is labelled epistemics, and `tests/test_agent_contract.py:84-95` checks only that a label is present, not that it is earned.

**Proposed fix**

Have the appended entry state exactly what was measured here and nothing more: label `verified`, tag `harness`, claim — "the guard's fixture keys `data-contract`/`extraction` name lenses this repo's panel does not define; re-keying them to `warehouse`/`parser` turns the guard green with `acceptance_panel.js` byte-untouched (measured 2026-08-17, Node v24.15.0). The 2026-08-15 entry's conclusion 'not a porting error' is refuted for this repo; its upstream observation was not re-tested." Evidence pointer: `requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md`, as an inline code span. Also drop the plan's assertion that the entry's dead `CLAUDE.md` pointer proves the entry wrong — I confirmed by grep that no 'Outstanding scaffolding work' section survives (removed by `1c47c2d`), but a dead pointer is stale, not false.

## Meta-audit findings (13)

### [MAJOR] Phase 4's new pytest grammar guard is work beyond the decided tiers, and it is ungated while it forces gated decision 2

- **Location:** `merged plan → phases[4] ("Phase 4") step 7 ("Add a third test to `tests/test_skill_references.py`"); files_to_touch entry for `tests/test_skill_references.py`; cf. requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md:191-192`
- **Confidence:** high
- **Category:** scope-creep

**Problem**

The RCA's Root step 5 is exactly one sentence and asks for one thing: "Settle the `root-cause` / `diagnosed` grammar in `diagnose-bug/SKILL.md` against the track README" (`ROOT_CAUSE_ANALYSIS.md:191-192`). It does not ask for a mechanical guard — a guard is Hardening-shaped work, and the RCA's Hardening tier (items 6-8) is the tier the merge otherwise correctly defers or gates. The merged plan folds a NEW tracked test into `tests/` (a repo-level deny-set path, and a file that blocks CI) as a plain, ungated Phase 4 step. Only code-grounded declined to propose it, so it is a 2-of-3 convergence, not a decided item. Worse, it is load-bearing on an UNRESOLVED gate: the merge's own gated decision 2 admits "if the Phase 4 grammar guard lands, `:176` is one of exactly two lines that fail it, so leaving it means shipping a guard red on a file the plan declined to touch." I verified that dependency is real — the only two `> **Status:**` lines under `.claude/skills/` that fall outside the union of both READMEs' grammars are `diagnose-bug/SKILL.md:107` (`root-cause`) and `create-implementation-plan/SKILL.md:176` (`plan`). So an ungated step coerces a gated one, which is the exact shape of a silently-promoted gated item.

**Proposed fix**

Move the grammar guard out of phases[4].steps and into gated_decisions[1] as the SAME disposition as `:172`/`:176` — one question, one answer: "correct the two extra sites AND add the guard" vs "correct the SKILL.md stage words only, file the guard as its own intake." Phase 4's ungated core then stays exactly what the RCA decided: `diagnose-bug/SKILL.md:97,:107,:150` (plus `create-implementation-plan/SKILL.md:56,:65`, which the plan already argues separately on functional grounds). If the user disposes in favour, the guard and the `:172`/`:176` edits land together in one Phase 4; if not, neither does, and nothing ships red.

### [MAJOR] The merge widened sequencing's deliberately bugfix-only grammar guard to a both-tracks union, adding blast radius and blinding it to the one instance that planner flagged

- **Location:** `merged plan → phases[4] step 7 and step 9 ("Check the guard's blast radius"), decisions[8]; drops the constraint at proposals[1] (sequencing) phases[3] step "SCOPE THE GUARD NARROWLY, ON PURPOSE" and risks[3]`
- **Confidence:** high
- **Category:** completeness

**Problem**

Sequencing raised an explicit scoping constraint and gave a reason: keep the guard bugfix-track-only, because "the feature track has its own separate divergence ... Those are real but are NOT this RCA's finding — a guard broad enough to catch them turns red on work nobody scoped." The merge silently adopted the opposite design (parse the union of BOTH track READMEs) without recording the constraint it dropped or arguing against it — decisions[8] and the convergence_map are silent on the narrow-vs-union choice. Two concrete costs follow. (1) The union widens the guard's subject from 2 skills to all 6 `> **Status:**` templates under `.claude/skills/`, which is what pulls `create-implementation-plan/SKILL.md:176` into the plan and creates the M1 dependency. (2) The union makes the guard WEAKER exactly where sequencing was pointing: `.claude/skills/implement-plan/SKILL.md:272` templates `implemented`, which is valid under the FEATURE grammar and therefore passes the union guard forever — even though `implement-plan` serves both tracks and a bugfix IMPLEMENTATION_REPORT must open at `fixed` per `requests/bugfix-requests/README.md:45`. The merged plan notices this (code_references entry for `SKILL.md:272`: "Its bugfix-track terminal word would be `fixed`; noted as a follow-up") but does not connect it to the design choice that guarantees the guard can never catch it. So the merge paid the wider blast radius and got the weaker check.

**Proposed fix**

Record the narrow-vs-union choice as an explicit decision with sequencing's counter-argument stated, and prefer the narrow form: parse only `requests/bugfix-requests/README.md:45`'s grammar and assert only over the bugfix-track skills (`diagnose-bug`, `make-bugfix-request`). That leaves `create-implementation-plan/SKILL.md:176` and `implement-plan/SKILL.md:272` out of the guard's reach, which decouples Phase 4 from gated decision 2 (fixing M1 as a side effect) and lets `:272`'s track-sensitivity be filed as the follow-up the plan already says it is. If the union form is kept anyway, add a sentence to decisions[8] saying so and naming `:272` as knowingly out of the guard's reach.

### [MINOR] Phase 2's assertion is specified as living at "module scope" but reads `calls`, which is block-scoped inside Scenario 1

- **Location:** `merged plan → phases[2] step 2 ("Add the assertion at the guard's module scope, inside Scenario 1's block") and decisions[2] ("lives at the guard's module scope and reads what the panel ACTUALLY requested out of `calls`"); .claude/skills/implement-plan/tests/verify_batching_guard.mjs:185-187`
- **Confidence:** high
- **Category:** correctness

**Problem**

`verify_batching_guard.mjs:185` opens a bare block and `:186` declares `const calls = []` inside it; `:187` is the `runPanel` call. `calls` therefore does not exist at module scope. The merged plan uses "module scope" as a load-bearing phrase in three places — it is the stated reason the assertion cannot live in `reviewFor` — and then in the same breath says "inside Scenario 1's block". A cold implementer taking the decisions[2] wording literally hoists the check above `:181` and hits a ReferenceError, or re-derives the roster with a regex (the thing decisions[2] exists to prevent). The phrase the plan actually means is "in the guard's own assertion code, not inside the stubbed agent".

**Proposed fix**

Replace "module scope" with "in the guard's own assertion path (Scenario 1's block, after `:187` and before `:193`), not inside the stubbed agent" in phases[2] step 2, decisions[2], and risks[1]. Keep the substantive argument — safeAgent swallows throws from the stub, and `reviewFor` structurally cannot see an orphaned key — which is correct and verified at `acceptance_panel.js:139-146`.

### [MINOR] The rationale for dropping the reverse-direction check defeats a variant no planner proposed (`throw`), not the one domain-convention actually proposed (`process.exit(1)`)

- **Location:** `merged plan → decisions[2] reason (1) and decisions[3]; drops proposals[2] (domain-convention) phases[2] step 2 and its open_questions[5], which explicitly chose exit over throw`
- **Confidence:** high
- **Category:** completeness

**Problem**

Domain-convention proposed a second, opposite-direction check — a strict `reviewFor` that fails when the PANEL asks for a lens the fixture lacks — and its open_questions[5] settled the mechanism deliberately: "Should Phase 3's strict `reviewFor` `process.exit(1)` or `throw`? Exiting is louder and matches the guard's existing exit-code contract at lines 285-292; throwing would be caught by the harness's own try/catch ... Recommendation: exit." The merged plan rejects the whole direction with, as its first stated reason, "A throw inside the stub agent is swallowed by `safeAgent`" — which is true (I verified `acceptance_panel.js:139-146`) but is precisely the failure mode that planner had already routed around. `process.exit()` is not catchable, so the rejected proposal would in fact have worked. The merge's OTHER argument (decisions[3]: `RAW_TOTAL` is fixture-derived, a skipped lens is harmless, and asserting the reverse breaks the moment `touchedAreas` grows) is sound and sufficient on the merits — so the outcome is right and the reasoning is not. That matters because the plan is a cold handoff: an implementer who spots that `exit` dodges `safeAgent` will reasonably conclude the plan was wrong and re-add the check.

**Proposed fix**

In decisions[2], drop reason (1) as stated or rewrite it as "a THROW inside the stub is swallowed by `safeAgent`; an `exit` would work but is unwanted for the reason in decisions[3]". Keep decisions[3] as the governing argument and cite `tests/test_skill_references.py:94-95` ("A fixture need not exercise every lens; it must only name lenses that exist") as the repo's own settled position on the direction.

### [MINOR] Phase 6's "prove the CI step is not vacuous" was downgraded from an in-CI red run to a local shell-shape run, which cannot catch a YAML-level swallowed exit

- **Location:** `merged plan → phases[6] last step and its acceptance criterion 2; drops proposals[0] (code-grounded) phases[4] final step ("on the PR, temporarily re-key one fixture entry and confirm the CI step goes red, then revert")`
- **Confidence:** medium
- **Category:** cost-unrealism

**Problem**

The merged plan's own risk register names the vacuous CI step as the phase's main hazard, and cites `acceptance_panel.js:201` item 4 for it — correctly; I confirmed that mandate reads "A step that passes vacuously (an empty selection, a swallowed exit code, a skipped leg) is worse than no check." But the acceptance criterion the merge kept is a LOCAL demonstration: "run the same chained command shape locally against the Phase-2 scratchpad copy with a re-broken fixture, and show a non-zero exit." A local shell run proves the command shape fails; it does not prove the workflow step propagates that exit code, which is the actual failure being guarded against (shell selection, a trailing `|| true`, a `continue-on-error` inherited from a step template, the guards enumerated but the last one's status masking the first's). Code-grounded's version — break it on the PR, watch the check go red, revert — is the only one that tests the thing. The merge dropped it without recording why.

**Proposed fix**

Restore the in-CI demonstration as Phase 6's acceptance criterion, keeping the local run as a cheap pre-check: after the guards step is added and CI is green, push one commit that re-keys a single fixture entry, confirm the `Lint, types, tests` check goes RED and the log names the failing guard, then revert in the next commit. Both commits go through `/commit`; the push and the PR stay the user's, consistent with the plan's existing manual gate. Paste both run URLs.

### [MINOR] Phase 1 dropped the cheap repo-wide grep that confirms the sibling vocabulary is actually gone

- **Location:** `merged plan → phases[1] acceptance list; drops proposals[2] (domain-convention) phases[0] step 4 ("Confirm the vocabulary is gone: grep `.claude/` for `data-contract|extraction`")`
- **Confidence:** high
- **Category:** completeness

**Problem**

Phase 1 makes three edits to the same file — the two keys at `:54`/`:58` and the stale teaching comment at `:150` — and its acceptance list checks only the guard's exit code, the diagnostic numbers, one pytest selector, and `git diff --stat`. None of those catches a missed `:150`: the comment is prose, so the guard still exits 0 and the Python test still passes with the comment left teaching `data-contract + extraction`. That is exactly the residue this whole request is about, in the one file it is about, and the merged plan itself argues the comment is load-bearing ("that comment is how the next reader learns the names"). Domain-convention proposed the one-line check that closes it and even pre-recorded the expected survivors (unrelated prose about extraction cost in three request-authoring skills). The merge kept the edit and dropped the verification.

**Proposed fix**

Add to phases[1].acceptance: "Grepping `.claude/skills/implement-plan/` for `data-contract|extraction` returns zero hits. Repo-wide, the only survivors are unrelated prose about extraction cost in `make-feature-request/SKILL.md`, `create-implementation-plan/SKILL.md` and `make-bugfix-request/SKILL.md` — enumerate them in the report so the judgment is checkable."

### [MINOR] Phase 7 mandates a mechanically-checked append to the agent-memory file, but neither that file nor its guard is in the onboarding reading list

- **Location:** `merged plan → onboarding.files_to_read (11 entries, neither `.claude/agents/data-engineer-memory.md` nor `tests/test_agent_contract.py`); phases[7] step 5; gated_decisions[3]`
- **Confidence:** high
- **Category:** completeness

**Problem**

Phase 7 requires appending an entry in "the exact shape at `:28`", labelled from a fixed five-word vocabulary, satisfying `tests/test_agent_contract.py:84-95` — and it must not edit or prune, per `:41`. I verified all three constraints are real (`data-engineer-memory.md:28` is the bullet shape, `:41` is the no-prune rule, `test_agent_contract.py:90-93` regexes `^- \*\*\d{4}-\d{2}-\d{2}\*\*` then requires a backticked label from `{measured, verified, inferred, assumed, unconfirmed}`). Both planners who raised this (domain-convention primarily) put `data-engineer-memory.md` and `tests/test_agent_contract.py` in their onboarding lists. The merge kept every constraint and dropped both files from `files_to_read`, so the cold implementer meets a shape-sensitive append with no instruction to read the file that defines the shape. `.claude/agents/data-engineer.md` IS in the list, but for the deny set, not the memory format.

**Proposed fix**

Add two entries to `onboarding.files_to_read`: `.claude/agents/data-engineer-memory.md` ("read `:24-43` for the mechanically-checked bullet shape and the no-prune rule before Phase 7; `:151-155` is the falsified entry you are correcting — never edit it") and `tests/test_agent_contract.py` ("`:76-81` is the deny set that decides who implements this; `:84-95` is the check your appended entry must pass").

### [MINOR] The plan lists its own stage-3 deliverable as a file the stage-4 implementer creates, and Phase 7 tells them to "Open" it

- **Location:** `merged plan → files_to_touch entry for `requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md` ("NEW — the stage-3 deliverable"); phases[7] step 1 ("Open ... IMPLEMENTATION_PLAN.md with `> **Status:** planned · created <today> ...`")`
- **Confidence:** medium
- **Category:** correctness

**Problem**

By the time any phase runs, the IMPLEMENTATION_PLAN.md is the document the implementer is reading — it cannot also be an output of Phase 7. Phase 7 step 1 instructs writing its status header with `created <today>`, which if followed literally re-dates a committed artifact and, at the terminal stage, would write `planned` over a header that should be advancing toward `fixed`. All three planners carried this same muddle (each lists the plan doc in files_to_touch), so the merge inherited rather than introduced it — but a merge is where an inherited artifact-vs-instruction confusion should be resolved, since a cold agent trusts the phase list literally.

**Proposed fix**

Split the entry. In `files_to_touch`, relabel it "ALREADY EXISTS — this document. Phase 7 advances its status blockquote only; its body is not rewritten." In phases[7] step 1, replace "Open ... with" by "Confirm this plan's own status blockquote at `:1` reads `planned · … · decided · next: implement` (it should already, per the track grammar and `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1`), and advance it in step with the Index row as the work lands. Do not re-date `created`."

### [MINOR] Gated Phases 5 and 6 sit inline in the numbered phase list, so the default reading order executes optional CI work

- **Location:** `merged plan → phases[5] and phases[6] ("Phase 5 — OPTIONAL, GATED", "Phase 6 — OPTIONAL, GATED ON PHASE 5's MEASUREMENT"), gated_decisions[2]`
- **Confidence:** medium
- **Category:** scope-creep

**Problem**

The RCA files node-in-CI under "Hardening — worth considering, not assumed" (`ROOT_CAUSE_ANALYSIS.md:206`, item 7 at `:209-211`) and flags its supporting claim as *unconfirmed*. The merge handles the epistemics impeccably — Phase 5 exists solely to measure, Phase 6 is gated on the measurement, and gated_decisions[2] states the trade-off honestly. But it then RECOMMENDS "IN SCOPE, and YES pin `actions/setup-node`", places both phases inline between the acceptance-contract phases and the recording phase, and makes Phase 7 the seventh step of a seven-step sequence. A cold agent working the phase list in order, on a plan whose per-phase cadence is prescribed, will execute two CI commits and two blocking user round-trips on a two-word bugfix unless it stops to notice the gate — and the acceptance contract (`requests/bugfix-requests/README.md:24-26`) is already fully met at the end of Phase 3.

**Proposed fix**

Move Phases 5 and 6 after the recording phase and renumber, so the mandatory sequence ends at a complete, committable state (fixture re-key → hardening → references → grammar → record) and the CI hardening is a clearly optional tail. Add one line at the head of each: "DO NOT START unless gated decision 3 has been disposed in favour by the user. The acceptance contract is already met without this phase."

### [NIT] convergence_map overstates the status-word theme as three-way triangulation when the three planners found different sites and disagreed on one of them

- **Location:** `merged plan → convergence_map[7] ("The status-word drift extends beyond `diagnose-bug/SKILL.md`", planners: all three, "Three independent discoveries of further instances is real evidence the class is broader than diagnosed")`
- **Confidence:** high
- **Category:** convergence-quality

**Problem**

The entry lists `create-implementation-plan/SKILL.md:56`/`:65`, `:172`/`:176`, and `make-bugfix-request/SKILL.md:130` as the converged evidence. In fact each site was raised by exactly ONE planner (sequencing found `:56`/`:65` and `:130`; code-grounded and domain-convention found `:172`/`:176`), and the planners actively DISAGREED on `:130` — sequencing wanted it changed to `next: diagnosed`, domain-convention argued the `next:` slot is imperative and correct. The merge resolved that disagreement well and, I confirmed, correctly: `make-feature-request/SKILL.md:171` reads `next: scope`, `scope-feature/SKILL.md:149` reads `next: plan`, and this request's own two artifacts read `next: plan` — so `next: root-cause` is the live convention, not drift. But the convergence entry presents a set of single-source findings plus one resolved conflict as "three independent discoveries", which inflates the confidence a reader assigns to the widened Phase 4.

**Proposed fix**

Rewrite convergence_map[7] to say what actually happened: "Each planner found a DIFFERENT additional site, and they disagreed on `make-bugfix-request/SKILL.md:130` — sequencing read the `next:` slot as drift, domain-convention as correct. The merge sided with domain-convention on in-repo evidence (`make-feature-request/SKILL.md:171` `next: scope`, `scope-feature/SKILL.md:149` `next: plan`, and this request's own artifacts' `next: plan`). Treat the extra sites as single-source findings that each need their own grounding, not as triangulated agreement." Keep decisions[6], which already carries the resolution.

### [NIT] `tests/test_doc_links.py` is described as 39 lines; the file is 38

- **Location:** `merged plan → onboarding.files_to_read entry for `tests/test_doc_links.py` ("39 lines, blocking in CI")`
- **Confidence:** medium
- **Category:** citation-accuracy

**Problem**

The file's last line is 38 (`assert not broken, ...`). Two planners carried "39 lines" and the merge propagated it. Harmless in itself, but the merged plan's own standard is that a cold implementer trusts numbers literally, and every other count in the plan (293 lines for the guard, 49 for `ci.yml`) is exact — I checked both and they are.

**Proposed fix**

Say "38 lines" or drop the count and keep the substantive part ("blocking in CI; `:10` has no fence awareness, `:11` is the complete exemption list, `:15` excludes `var/` from files scanned, `:30` strips a `#fragment` but never a `:123` suffix"), all four of which I verified.

### [NIT] `tests/test_no_leaks.py` is cited five times without the line number a planner supplied

- **Location:** `merged plan → risks[5], conventions[2], phases[2] acceptance, phases[7] steps; drops the `:25` cite from proposals[1] (sequencing) code_references`
- **Confidence:** medium
- **Category:** completeness

**Problem**

The merged plan invokes `tests/test_no_leaks.py` as the reason scratchpad paths must never enter tracked text — a rule it applies in Phases 2, 6 and 7 — but never says where the drive-path pattern lives. Sequencing pinned it at `:25` with the regex quoted. Every other guard the plan leans on gets a line cite; this one does not, so an implementer who wants to check what exactly is banned has to hunt.

**Proposed fix**

Add a `code_references` entry for `tests/test_no_leaks.py:25` carrying the windows-drive-path pattern, and reference it from risks[5] and conventions[2] instead of naming the file bare.

### [NIT] The four standing warnings are restated in five or six places each, diluting the phase-specific instructions around them

- **Location:** `merged plan → "acceptance_panel.js must not appear in git diff" (summary, architecture_map, phases 1/2/3/7, testing, risks[0], decisions[0], files_to_touch); "citations are code spans" (conventions[9], risks[5], testing, phases[7], decisions[12]); "the subagent may not build this" (architecture_map, conventions[4], risks[10], decisions[10], onboarding)`
- **Confidence:** low
- **Category:** dedup

**Problem**

Each of these is a genuine trap and each deserves to appear in the conventions and once at its point of use. Appearing five or six times, at full length, in a plan already at the top of its length budget, makes the phase steps harder to scan and raises the odds that a cold implementer skims a phase whose steps look like restated boilerplate — which is where the phase-specific instructions (the two-space indent constraint, the `:150` comment, the `builder:` negative test) actually live. This is inherited from all three proposals rather than introduced by the merge, and it is the one place where the merge chose union over selection.

**Proposed fix**

Keep each warning at full length in exactly two places — `conventions` (the standing rule) and the single phase where it first bites — and reduce the remaining occurrences to a one-clause pointer (e.g. in phases 2/3/7 acceptance: "`acceptance_panel.js` absent from `git diff --stat` (see decisions[0])"). No content is lost and the phase steps regain their signal.

## Reviewer summaries

### code-grounded

CODE-GROUNDED VERIFICATION: I resolved every code reference the merged plan cites — all ~70 of them, across `code_references`, `onboarding.files_to_read`, `architecture_map`, `phases`, `files_to_touch`, `decisions`, `risks` and `gated_decisions` — against the working tree at HEAD `0ed70d5` (clean). **Zero dangling references. Zero wrong-line citations. Zero fictional symbols or fictional reuse claims.** Every function, constant and regex the plan names exists at the line it names: `FINDINGS_BY_LENS` at `verify_batching_guard.mjs:40`, `'data-contract'` at `:54`, `extraction` at `:58`, the column-0 `}` at `:64`, `|| []` at `:78`, the stale comment at `:150`, `calls.push` at `:165`, `const fails = []` at `:181`, `runPanel(...)` at `:187`; `safeAgent` at `acceptance_panel.js:139-146`, `CORE`/`SPEC_DEFS`/`AREA_TO_SPEC`/`specKeys`/`ROSTER` at `:189-209`, `normLocation` at `:298-301` and the `jaccard(...) >= 0.5` gate at `:317`; `TEST_REFERENCE`/`LENS_KEY`/`FIXTURE_LENS`/`fixture_lens_keys()` at `tests/test_skill_references.py:32/37/40/72-76`; `tests/test_parse_world.py:179` (real, above the `gamedata` boundary at `:513`); `tests/test_byte_accounting.py:46`; `tests/test_agent_contract.py:76-81` and `:84-95`; the deny set at `.claude/agents/data-engineer.md:147-158` with the stop-and-report at `:164`; the memory shape at `:28`, the never-prune rule at `:41`, the falsified entry at `:151-155`; `ci.yml:13-17`/`:34-49`; `ops/branch-protection.json`'s single `"Lint, types, tests"` context; `pyproject.toml:91-95`/`:100-107`. All seven dead test references sit at exactly the six files and seven lines claimed; all four `root-cause` stage-word sites and the two `plan` sites are where claimed. MEASUREMENTS I RAN: baseline `2 failed, 170 passed, 62 deselected` (exact match to the plan); the guard exits 1 with all six failure lines verbatim; Node v24.15.0; the four sibling `.mjs` guards all exit 0; ruff, ruff format and mypy (38 source files) all green. Most importantly I EXECUTED the prescribed Phase 1 fix in a scratchpad copy with `HERE` repointed at the tracked skill directory — it exits 0 and prints the four diagnostic lines byte-for-byte as the plan's acceptance asserts (`raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` …). I also instrumented Phase 2's proposed mechanism: the panel requests exactly `acceptance,correctness,edgecases,fidelity,parser,skill-quality,warehouse` and the post-fix fixture keys are a strict subset, so the module-scope `calls`-derived assertion works as designed. The plan's spine is sound and measured. My findings are all in the periphery: two acceptance criteria that are wrong or vacuous against today's tree (one of which would drive a cold implementer into editing archived artifacts), one prose-drift gap the plan's own "do not touch the repro" instruction opens, and a handful of precision/sequencing issues.

### executability

EXECUTABILITY & SEQUENCING review. I read every file the plan cites and re-ran its two decisive experiments. The technical core is sound and unusually well grounded: I reproduced the RED baseline verbatim (`exit 1`, `raw=8 deduped=7`, all six failure lines), confirmed `2 failed, 170 passed, 62 deselected`, confirmed all four sibling `.mjs` guards, and — most importantly — built the Phase 1 fix in the scratchpad and got the plan's asserted four diagnostic lines back BYTE FOR BYTE (`raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` … `[verifyCap ] cap=2 batches=2 unverified=0/9`). I also prototyped Phase 2's prescribed hardening (derive the requested lens set from `calls`, assert at module scope) and confirmed it is inert on a clean tree and bites on all three negative cases the plan demands, including the `builder:` case the Python test cannot see. Every line citation I spot-checked resolved exactly — the seven dead references at their stated lines, `ci.yml:13-17`/`:34-49`, `ops/branch-protection.json`, `data-engineer.md:147-158`, `data-engineer-memory.md:28`/`:41`/`:151-155`, `pyproject.toml:91-95`/`:100`, `test_agent_contract.py:76-95`, `test_parse_world.py:179`, `test_byte_accounting.py:46`, `first-sight/IMPLEMENTATION_PLAN.md:1`. The files_to_touch checklist would produce a working result for Phases 1-4, and the CLAUDE.md conventions (never `git commit` ad hoc, read-only-git subagents, the data-engineer deny set, no game data, no drive paths) are baked in explicitly rather than gestured at. Where it breaks is COLD execution, not correctness. Four of five gated decisions change what the phases actually do and what their acceptance numbers are, yet nothing tells the implementer to dispose them before Phase 0 — the plan cannot be run "without the author present" as written. Phase 4's acceptance is stated unconditionally while its own steps admit it depends on gated decision 2. The record phase that completes the bugfix track's paper trail sits BEHIND two human-gated optional CI phases, so an agent that reaches Phase 5 blocks forever and never advances the Index row. Phase 3 carries a grep acceptance criterion that is factually false and whose only "fix" is an edit the plan forbids in three other places. And Phase 7 instructs the implementer to create the very plan document it is executing.

### meta-audit

META-AUDIT OF THE MERGE, not the repo. I re-verified the merged plan's grounding against the tree before judging convergence: `git status --porcelain` empty; `uv run pytest -m "not gamedata"` collects 172 with exactly the 2 `test_skill_references.py` failures (= the claimed `2 failed, 170 passed`); `verify_batching_guard.mjs` exits 1 and the four named siblings exit 0; `acceptance_panel.js:139-146/189-194/196-202/203-209/317` and the nine `key: '...'` declarations are as described; `test_skill_references.py:32/37/40/72-76/94-95/99-100`, `test_doc_links.py:10/11/15/28/30`, `ci.yml:13-17/34-49`, `data-engineer.md:132-165`, `test_agent_contract.py:76-81/84-95`, `data-engineer-memory.md:28/41/151-155`, `pyproject.toml:91-95/100-107`, both track READMEs' `**Status grammar:**` lines, `requests/README.md:12`, `first-sight/IMPLEMENTATION_PLAN.md:1`, `implement-plan/SKILL.md:309`, `create-implementation-plan/SKILL.md:172/176/219-222/250-256`, `diagnose-bug/SKILL.md:97/107/117-118/150`, `test_parse_world.py:179` (first `gamedata` at `:513`) and `test_byte_accounting.py:46` all resolve. I also confirmed `CLAUDE.md` no longer carries the "Outstanding scaffolding work" section the memory entry cites, and that exactly six `> **Status:**` templates exist under `.claude/skills/` with exactly two violating the union grammar — the merge's own arithmetic. CONVERGENCE VERDICT: the merge is faithful and unusually well-verified. It resolved three genuine planner disagreements with checkable evidence rather than averaging them (the `next: root-cause` reversal, the `test_byte_accounting` rejection, the `calls`-vs-regex hardening seam), and it surfaced five gated decisions rather than absorbing them. No blockers. The defects are: (a) ONE scope addition that is in the plan ungated and not in the decided tiers — the new status-grammar pytest guard, which the RCA never asks for and which then forces gated decision 2; (b) the merge silently widened a planner's deliberately-narrow guard scope, costing the one instance that planner was protecting; (c) a handful of dropped verification steps and one rationale that misrepresents the alternative it rejects.

## Convergence map

```json
[
  {
    "theme": "The two-word fixture re-key (`'data-contract'` → `warehouse`, `extraction` → `parser`) is the proven minimal fix, and `acceptance_panel.js` is byte-untouched",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three independently re-ran the RCA's decisive experiment from a scratchpad copy with the panel repointed at the tracked file, and all three reported the identical green output (`raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`). I reproduced the RED baseline myself and derived the same mapping from `acceptance_panel.js:203-207`. This is a measurement three times over, not a hypothesis — the plan can treat Phase 1 as certain."
  },
  {
    "theme": "`git diff --stat` showing `acceptance_panel.js` is a HARD STOP, checked at every phase boundary rather than assumed",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Three planners converged on turning the RCA's central verdict into a mechanical per-phase check. It is the one failure mode that produces a green guard and a worse repo simultaneously — and `acceptance_panel.js:317`'s `jaccard >= 0.5` gate is precisely the correct behaviour a 'fix' would loosen. Converting a verdict into a checkable diff assertion is what makes it survive a cold handoff."
  },
  {
    "theme": "Phase ordering: fixture first, dead references second — the RCA's 'the one step that must not move first'",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three preserved the RCA's explicit ordering constraint and gave the same reason: the reference work sits adjacent to the doc-link request's undisposed gate, so the proven self-contained change must land first and unambiguously. Independent agreement on sequencing is the strongest signal that the ordering is real rather than stylistic."
  },
  {
    "theme": "The hardening cannot live inside `reviewFor`, because `safeAgent` swallows every throw and `reviewFor` never sees an orphaned key",
    "planners": [
      "code-grounded",
      "sequencing"
    ],
    "why_high_signal": "Two planners traced the same two-step argument through `acceptance_panel.js:139-146` and reached the same conclusion, and it invalidates the most natural-looking implementation. The third planner proposed exactly that natural implementation (a strict `reviewFor` + `process.exit`), which is what makes the convergence load-bearing: without it a cold implementer writes the obvious thing and ships a no-op."
  },
  {
    "theme": "The fixture edit must preserve the two-space indent and the column-0 closing brace, or the Python guard parses zero keys and passes vacuously",
    "planners": [
      "code-grounded",
      "sequencing"
    ],
    "why_high_signal": "Both traced `tests/test_skill_references.py:40` and `:75` and identified the same silent-failure mode: a broken parse turns the regression guard from red into a vacuous green, which is strictly worse than the bug. This is the kind of constraint a cold implementer would never infer from the diff alone."
  },
  {
    "theme": "Every citation written during this work is an inline code span, because `tests/test_doc_links.py` is fence-blind and does not strip a `:123` suffix",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three grounded it in `tests/test_doc_links.py:10` and `:30` and noted the plan document itself is scanned by a blocking CI check. It is a self-referential trap: the plan for fixing a link-guard defect can be failed by that same defect. Three independent hits mean it belongs in the conventions, not a footnote."
  },
  {
    "theme": "The doc-link request's promise prose is untouchable here — only the file-name token is direction-independent",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three cited `doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:95-98` ('common to both readings ... the only part safe to do early'). They diverged on how far to go, which sharpened the boundary rather than blurring it, and that divergence became gated decision 1 instead of an unexamined edit."
  },
  {
    "theme": "The status-word drift extends beyond `diagnose-bug/SKILL.md` — the RCA's third instance has siblings the RCA did not enumerate",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Each planner found additional sites independently and by different routes (`create-implementation-plan/SKILL.md:56`/`:65`, `:172`/`:176`, `make-bugfix-request/SKILL.md:130`). Three independent discoveries of further instances is real evidence the class is broader than diagnosed — and grounding them against `requests/README.md:12` plus both track READMEs is what separates the genuine drift from the two false positives (frontmatter descriptions and `next:` slots)."
  },
  {
    "theme": "CI hardening adds a STEP to the existing `quality` job, never a new job, because `ops/branch-protection.json` pins the display name",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three read `.github/workflows/ci.yml:13-17` and `ops/branch-protection.json` and independently identified the same latent catastrophe: a rename or a new job leaves every future PR waiting forever on a check that never reports. The workflow warns about it in-file and `acceptance_panel.js:201` item 5 names it as a bug class — three sources plus three planners."
  },
  {
    "theme": "'ubuntu-latest ships node' is unconfirmed, and the plan must either measure it or remove it from the dependency chain",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three refused to build on it, and they proposed two genuinely different remedies — a throwaway CI probe (measure it) versus a pinned `actions/setup-node` (eliminate the dependency). Both are legitimate and the disagreement is the useful part: it became gated decision 3 with a real trade-off rather than a silent assumption."
  },
  {
    "theme": "Negative testing is an acceptance criterion — every new check must be demonstrated RED before it is trusted GREEN",
    "planners": [
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Both made it a per-phase acceptance criterion rather than advice, with the same rationale: `verify_batching_guard.mjs` had only ever been observed FAILING and nobody checked which side was wrong for months. A check that has never been watched to fail is the defect class this request is about, so demonstrating it is the fix's own dogfood."
  },
  {
    "theme": "No data-contracts section, and `docs/data-sources.md` does not exist in this repo",
    "planners": [
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Both grounded the omission in `.claude/skills/create-implementation-plan/SKILL.md:219-222` (section 9 is Conditional) and both flagged that the analogous doc is `docs/data-access.md` and is untouched. Independent agreement that a section is CORRECTLY ABSENT is worth as much as agreement on one being present — it stops a cold implementer inventing a data-contract entry to look thorough."
  },
  {
    "theme": "The replacement worked example must name a file that exists even inside a fenced code block",
    "planners": [
      "code-grounded",
      "domain-convention"
    ],
    "why_high_signal": "Both traced `tests/test_skill_references.py:32` and noted it runs line-by-line with no fence awareness — that absence is itself the doc-link defect this repo still carries. Naming an invented test inside the fence would re-create the exact bug being fixed, in the template a cold agent copies from."
  }
]
```

## Gated decisions as the panel posed them

```json
[
  {
    "question": "How far does Phase 3 go on the four 'What good looks like' bullets? Repointing `tests/test_request_links.py` → `tests/test_doc_links.py` is safe under both readings of the doc-link gate. But those same bullets (`create-implementation-plan/SKILL.md:250-256`, `make-bugfix-request/SKILL.md:199-204`, `make-feature-request/SKILL.md:245-250`, `diagnose-bug/SKILL.md:176-181`) promise three exemptions the real guard does not implement — and attaching a false promise to a REAL file arguably makes the misinformation more credible than a dangling name did.",
    "recommendation": "REPOINT THE TOKEN ONLY; leave the promise prose exactly as it is, and record the known-incomplete state in the IMPLEMENTATION_REPORT where it cannot be mistaken for a promise. Two reasons. First, `doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:95-98` says the reference correction is the only part safe to do early — rewriting the promises IS reading (b)'s work, and doing it here decides the gate by implication. Second, that request's own recommendation is reading (a) — extend the guard — under which the promises become TRUE, so a rewrite now would be work thrown away and would make (a) cheaper to abandon. The alternative (describe the guard's current behaviour plus a bare pointer to the open request) is defensible and reads as more honest, but it is not free: it hard-codes reading (b)'s framing into four files. The user disposes.",
    "related": [
      "requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:82-98",
      "tests/test_doc_links.py:10-33",
      ".claude/skills/create-implementation-plan/SKILL.md:250-256"
    ]
  },
  {
    "question": "Does Phase 4 also correct `.claude/skills/create-implementation-plan/SKILL.md:172` and `:176` from stage word `plan` to `planned`? It is a fourth instance of the RCA's third-instance class, found while planning and NOT enumerated in the RCA — so including it widens a decided scope by one file.",
    "recommendation": "INCLUDE IT. It is provably wrong against three independent artifacts — `requests/bugfix-requests/README.md:45`, `requests/feature-requests/README.md:110`, and the in-repo precedent `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1` — with `requests/README.md:12` making each track README the contract. It is also FORCED by this very plan: Phase 7 must write either `plan` or `planned` in its own status header, so the question cannot be deferred, only answered silently. And if the Phase 4 grammar guard lands, `:176` is one of exactly two lines that fail it, so leaving it means shipping a guard red on a file the plan declined to touch. If the user prefers to keep this request narrow, the fallback is: write `planned` in Phase 7 (following the contract), skip the grammar guard, and file the skill correction as a separate intake.",
    "related": [
      ".claude/skills/create-implementation-plan/SKILL.md:172-176",
      "requests/bugfix-requests/README.md:45",
      "requests/feature-requests/README.md:110",
      "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1"
    ]
  },
  {
    "question": "Are Phases 5 and 6 (measure node on the runner, then run the five `.mjs` guards in CI) in scope? The RCA files this under Hardening — 'worth considering, not assumed' — and it widens a bugfix into CI work across two commits and two user round-trips. If it IS in scope, should `actions/setup-node` be pinned regardless of what the measurement says?",
    "recommendation": "IN SCOPE, and YES pin `actions/setup-node`. In favour: the guard was red from the day it arrived and nothing noticed for the life of the skill — that IS the defect class, and `tests/test_skill_references.py` only catches lens-key drift, not a guard that breaks for any other reason. `.claude/skills/implement-plan/SKILL.md:309` instructs running it after every `acceptance_panel.js` change, and a check nobody is forced to run is how this one rotted. On the node question: pinning `setup-node` removes the unconfirmed claim from the dependency chain entirely and pins the runtime the guards execute on, which is strictly better than testing the claim — but keep Phase 5's `node --version` probe anyway so the fact is measured and recorded rather than merely made irrelevant. If the user wants to keep this a pure bugfix, drop both phases and file Hardening 7 as its own intake; the acceptance contract does not depend on them.",
    "related": [
      "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md:209-211",
      ".github/workflows/ci.yml:13-17",
      ".github/workflows/ci.yml:34-49",
      "ops/branch-protection.json"
    ]
  },
  {
    "question": "Should the main thread append a correcting entry to `.claude/agents/data-engineer-memory.md`, or leave the falsified 2026-08-15 entry (`:151-155`) for `/update-docs` curation? That file is the write-capable subagent's memory, and commit b32f325 moved agent-memory curation from CI to the doc gate.",
    "recommendation": "APPEND IT, in Phase 7. The entry states 'a pre-existing upstream defect, not a porting error', which this request's RCA disproves outright, and its evidence pointer (a `CLAUDE.md` 'Outstanding scaffolding work' section) no longer exists — I verified by grep that commit 1c47c2d removed it. The doc gate has already run at least once since without catching it, so waiting is not a plan. Append never prune (`:41`), use the exact shape at `:28`, label `verified`, tag `harness`, and expect `/commit`'s doc gate to trigger on the file appearing in the staged diff. If the user prefers curation to stay with `/update-docs`, the alternative is to note the falsification in the IMPLEMENTATION_REPORT and let the next doc-gate pass reconcile it.",
    "related": [
      ".claude/agents/data-engineer-memory.md:28",
      ".claude/agents/data-engineer-memory.md:41",
      ".claude/agents/data-engineer-memory.md:151-155",
      "tests/test_agent_contract.py:84-95"
    ]
  },
  {
    "question": "Is RCA Hardening 6 (generalise `tests/test_skill_references.py` from two token classes to every repo path a skill names) owned by the doc-link plan, and is Hardening 8 (a deliberate sweep for remaining sibling-repo domain residue) filed as a fresh intake before this request closes?",
    "recommendation": "CONFIRM Hardening 6 belongs to the doc-link plan — it appears in BOTH RCAs (this one at its `:208`, the doc-link one at its `:104-106`), which is exactly the shape where each request assumes the other owns it and neither does. And FILE Hardening 8 as a new intake rather than running it here: two residue instances turned up by accident in one sitting, plus a fourth status-word instance during planning, which is now weak-but-growing evidence a deliberate pass would find more — but it is an open-ended search with no acceptance criterion, and folding it in would turn a bugfix into an audit. A bounded, vocabulary-agreed sweep deserves its own scope.",
    "related": [
      "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md:206-214",
      "requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:104-106",
      "tests/test_skill_references.py:32"
    ]
  }
]
```
