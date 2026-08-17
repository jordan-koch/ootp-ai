> **Status:** planned · created 2026-08-17 · decided · next: implement

# Implementation Plan — Repair the ported guards, and make the promises they carry true

> **One-line goal:** every guard in `.claude/skills/` describes the repo it actually lives in — the
> batching guard goes green for the first time, the link guard gains the contract six skills promise,
> and an orphaned reference fails by name instead of miscounting · **Target component:**
> `.claude/skills/` (five skills), `tests/test_doc_links.py`, `tests/test_skill_references.py`,
> `.github/workflows/ci.yml`, `.claude/agents/data-engineer-memory.md`.

> **This plan closes TWO requests.** `verify-batching-guard-red-on-arrival` (the primary, whose RCA is
> the decided upstream artifact) and `doc-link-guard-mismatch` (whose gated decision the operator
> disposed on 2026-08-17 — see §5 D1). The doc-link request has no plan of its own; this is it.
>
> **Citation convention.** Every `file:line` below is an inline code span, never a Markdown link.
> `tests/test_doc_links.py:10` has no fence awareness and `:30` strips a `#fragment` but never a
> `:123` suffix, so an ordinary Markdown link whose target carries a line suffix turns CI red
> **today** — even inside a fenced block, and even when written only as an example of the broken
> shape. **This document hit exactly that on its first run**, which is the cheapest possible
> demonstration of why Phase 5 exists. Until Phase 5 lands the code-span convention is mandatory,
> including here.

## 1. Onboarding — read these first

The stage-4 acceptance panel spawns adversarial reviewer lenses, dedupes their blocker/major findings,
buckets them by location, and packs them into at most `VERIFY_CAP` batch verifiers.
`verify_batching_guard.mjs` pins four properties of that Verify phase. It does not import the panel —
it reads `acceptance_panel.js` as text and re-evaluates it inside a `new Function(...)` with a stub
`agent`, which answers each reviewer call out of a synthetic finding set **keyed by lens name**. Two of
those keys are a sibling repo's vocabulary, so their findings never enter the run, and the guard has
reported a miscount and blamed the panel since the day it arrived.

**Do not edit `acceptance_panel.js`.** The RCA proved it correct by experiment. Editing it is the
single worst available outcome, and it is the one thing every planner and both adversaries agreed on.

**Read in this order. All paths are repo-relative.**

| # | File | Why |
|---|---|---|
| 1 | `requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md` | The decided upstream artifact. **Consume it; do not re-open it.** Verdict at `:17-24`, the per-failure-line table at `:88-96`, the tiered fix posture at `:173-214` |
| 2 | `requests/bugfix-requests/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md` | The second request this plan closes. Its gated decision at `:82-93` — **now disposed in favour of extending the guard**; `:95-98` is why the reference repointing was always safe to do early |
| 3 | `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` | The file being fixed — 293 lines, read it in full. Fixture `:40-64`, the two bad keys `:54`/`:58`, the silent swallow `:78`, the stale roster comment `:150`, the call recorder `:163-179`, `fails` at `:181`, Scenario 1 at `:185-226`, the single RED path at `:285-292` |
| 4 | `.claude/skills/implement-plan/acceptance_panel.js` | The code under test — **read, never edit**. `CORE` `:189-194`, `SPEC_DEFS` `:196-202`, `AREA_TO_SPEC` `:203-207`, `specKeys`/`ROSTER` `:208-209`. `safeAgent` `:139-146` swallows every throw, which constrains how Phase 2 may fail loudly. The dedupe the guard falsely accused: `normLocation` `:298-301` and the `jaccard >= 0.5` gate at `:317` |
| 5 | `tests/test_skill_references.py` | The committed red repro **and** the regression guard the acceptance contract requires. `TEST_REFERENCE` `:32`, `LENS_KEY` `:37`, `FIXTURE_LENS` `:40`, `fixture_lens_keys()` `:72-76` (splits on literal delimiters), the deliberate one-directionality note `:94-95`. **Its two assertions are not weakened to fit the fix**; its docstrings *are* moved to past tense in Phase 3 |
| 6 | `tests/test_doc_links.py` | **38 lines**, blocking in CI, and Phase 5 rewrites it. `LINK` `:10` (one regex over raw text — no fence state), `SKIP_PREFIXES` `:11` (the complete exemption list), `:15` (excludes `var/` from files *scanned*, which is not an exemption for link *targets*), `:30` (strips `#fragment`, never `:123`) |
| 7 | `requests/bugfix-requests/README.md` | The track contract (`requests/README.md:12` makes each track README the contract). Definition of done `:24-26`, status grammar `:45`, and the two Index rows this plan advances at `:51` and `:53` |
| 8 | `.claude/agents/data-engineer-memory.md` | Read `:24-43` for the mechanically-checked bullet shape and the **append-never-prune** rule before Phase 7. `:151-155` is the falsified 2026-08-15 entry being corrected — read what it actually claims before writing the correction |
| 9 | `tests/test_agent_contract.py` | `:84-95` is the guard the appended memory entry must satisfy — it regexes `^- \*\*\d{4}-\d{2}-\d{2}\*\*` then requires one of five backticked epistemic labels |
| 10 | `.claude/agents/data-engineer.md` | Its Write allowlist at `:132-165` repo-level **denies** `tests/`, `.github/`, `ops/` and all of `.claude/` except one memory file. Every path this plan touches is inside that deny set — **the write-capable subagent may not build this. The main thread does.** |
| 11 | `.github/workflows/ci.yml` | 49 lines, one job. The in-file warning `:13-15`, the job display name `:16-17` pinned by `ops/branch-protection.json`, the four gates at `:37-49`. No node step today |
| 12 | `.claude/skills/create-implementation-plan/SKILL.md` | The stage-3 contract, and **five sites this plan repairs**: `:56`, `:65`, `:172`, `:176` (Phase 4) and `:251` (Phase 3). Also `plan_panel.js:147`, which sends planners after a file that does not exist |

## 2. Architecture map

Everything here lives under `.claude/skills/`, plus two pytest modules, one agent-memory file, and one
CI job. Nothing in `src/ootp_ai/`, no dbt model, no dataset, no `.env` path, no save file. **The game
is not read, let alone written.** The parser conventions — sequential walking, the fixed-offset ban,
`players.csv` as ground truth, `unconfirmed` labels, resolve-by-name — have no surface here and must
not be padded into the work. `datasets/` does not exist and CLAUDE.md forbids creating it
speculatively. The correctness that matters is **project-convention correctness**, and that is where
the traps are.

**The roster, in one place.** `acceptance_panel.js` assembles its reviewer lenses at exactly one site:
`CORE` (`:189-194`) is four always-on lenses — `acceptance`, `fidelity`, `correctness`, `edgecases`.
`SPEC_DEFS` (`:196-202`) is five specialists — `parser`, `warehouse`, `builder`, `skill-quality`,
`infra-cost`. `AREA_TO_SPEC` (`:203-207`) maps the guard's `touchedAreas: ['transform','src','skills']`
to `warehouse`, `parser`, `skill-quality`. The fixture names `data-contract` and `extraction`, which
exist nowhere.

**Three sibling swallows, same shape, only one in scope.** `FINDINGS_BY_LENS[lensKey] || []` at
`verify_batching_guard.mjs:78` is the one being fixed. `AREA_TO_SPEC[a] || []` at
`acceptance_panel.js:208` silently drops an unrecognised touched-area, and `.filter(Boolean)` at `:209`
silently drops a spec key with no `SPEC_DEFS` entry. **Noted for the reader; not in scope to change** —
they are in the file this plan must not touch.

**The link guard's shape after Phase 5.** `tests/test_doc_links.py` grows from a single
`markdown_files()` → regex → `Path.exists()` pass into: a fence-stripping pre-pass, a target normaliser
that drops a trailing `:123`, a `var/` target exemption, and a second scanner over bare
`requests/...` tokens. The four "What good looks like" bullets in five skills become **true statements**
rather than promises, which is why no prose rewrite is needed there.

## 3. Phased implementation

Nine phases. Each ends at a `/commit`-gated checkpoint on a green local run of `uv run pytest`,
`uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy`. **Phases 1 and 3 must not be
merged or reordered** — Phase 1's acceptance is that exactly one of the two red tests flips, which is
the proof the fixture fix and the reference fix are independent.

---

### Phase 0 — Record the baseline, and confirm the dispositions (no edits)

**Goal.** Every later phase asserts a number moved. Capture the numbers first, on a clean tree, so
"green" is a measured delta rather than a feeling.

**Steps.**
1. **Precondition, stated as a hard gate.** Confirm every gated decision in §5 D1–D5 is recorded as
   disposed. All five were disposed by the operator on 2026-08-17 and are written into this document;
   if a later reader finds one open, **stop and ask** — do not take a recommendation by default. Four
   of the five change which files get edited.
2. Confirm the tree is clean: `git status --porcelain` returns nothing. Record
   `git branch --show-current` — if it is `main`, create the working branch first; `/commit` stops for
   a decision on `main` (`.claude/skills/commit/SKILL.md:44-47`) and every phase ends at a `/commit`.
3. Record `node --version` and `uv --version`. **If node is absent, STOP** — the primary acceptance
   check cannot run and no phase can be verified. A cold agent reading `node : command not found` as a
   guard failure is the exact misattribution this whole request is about.
4. Run `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` and paste its exit-1
   output — four diagnostic lines plus six failure lines — into your working notes.
5. Run `uv run pytest -m "not gamedata"` and record the tally. **Measured 2026-08-17 on a clean tree:
   `2 failed, 170 passed, 62 deselected`**, both failures in `tests/test_skill_references.py`.
6. Run the four sibling guards and confirm all four exit 0:
   `.claude/skills/implement-plan/tests/merge_fallback_guard.mjs`,
   `.claude/skills/scope-feature/tests/merge_fallback_guard.mjs`,
   `.claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs`,
   `.claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs`.
   *(Measured 2026-08-17: the last two exit 0 — so the drift is specific, not systemic.)*
7. Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` and record each.

**Acceptance.** The guard's RED output, the pytest tally, both tool versions and the branch name are
written down. All four sibling guards exit 0. `git status --porcelain` is empty.

**Commit note.** No commit — this phase produces measurements, not a diff.

---

### Phase 1 — Re-key the fixture to this repo's lenses (RCA Minimal 1)

**Goal.** The batching guard exits 0 for the first time in this repo's history, with
`acceptance_panel.js` byte-untouched. Proven by the RCA's experiment (`ROOT_CAUSE_ANALYSIS.md:102-115`)
and re-derivable from `AREA_TO_SPEC`.

**Steps.**
1. In `.claude/skills/implement-plan/tests/verify_batching_guard.mjs`, change `:54` from
   `  'data-contract': [` to `  warehouse: [`. Unquoted is correct — `warehouse` is a valid JS
   identifier and `tests/test_skill_references.py:40` accepts either form.
2. Change `:58` from `  extraction: [` to `  parser: [`.
3. **Keep exactly two leading spaces on both keys, do not reflow the object**, and leave
   `const FINDINGS_BY_LENS = {` at `:40` and the column-0 closing `}` at `:64` exactly as they are.
   `tests/test_skill_references.py:72-76` carves the fixture block on those literal delimiters.
4. Do **not** touch `'skill-quality'` at `:61` — the hyphen means it needs its quotes.
5. Leave the per-entry comments at `:55` and `:59` alone. Both are still accurate after the re-key and
   both are why the dedupe assertions are meaningful.
6. Fix the stale teaching comment at `:150` — `// -> data-contract + extraction + skill-quality
   specialists` becomes `// -> warehouse + parser + skill-quality specialists`. Trace it yourself
   against `acceptance_panel.js:203-207` rather than trusting this line.
7. **The header at `:11` says "7 lenses" and that number is correct** — an adversary instrumented the
   run and the panel requests seven (`acceptance` legitimately emits no findings, so six carry
   fixture entries). Do not "correct" 7 to 6. If you touch it at all, make it unambiguous:
   *"N findings raised across the 6 finding-emitting lenses of a 7-lens roster."*
8. **Do not open `acceptance_panel.js` for editing.**

**Acceptance.**
1. `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 with exactly:
   `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` ·
   `[dead-batch] verifiers=4/5 unverified=3/9 note="verify:b1 (3 findings left unverified)"` ·
   `[rubberstmp] b1Calls=2 verifiers=4/5 unverified=3` · `[verifyCap ] cap=2 batches=2 unverified=0/9`.
2. `uv run pytest tests/test_skill_references.py::test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines`
   passes.
3. `uv run pytest -m "not gamedata"` → **`1 failed, 171 passed, 62 deselected`** — exactly one net test
   flipped. The remaining failure is `test_every_test_file_a_skill_names_exists`, which Phase 3 owns;
   that is expected, and is the proof Phase 3 did not move first.
4. `git diff --stat` lists exactly one file. **`acceptance_panel.js` must not appear.**
5. Grepping `.claude/skills/implement-plan/` for `data-contract|extraction` returns zero hits — this is
   what catches a missed `:150`, which no test can see because it is prose.
6. Four sibling guards still exit 0; ruff / format / mypy unchanged from baseline.

**Commit note.** `/commit`. Suggested subject: *"Re-key the batching guard's fixture to this repo's
lenses"*. Put the before/after diagnostic pair in the body — it is the whole story in four lines.

---

### Phase 2 — Make an unrequested fixture lens fail loudly instead of miscounting (RCA Root 4)

**Goal.** Close the mechanism that hid this defect for the guard's entire life. The next roster rename
must produce a named, self-explaining error naming the fixture — not six miscounts blaming the code
under test.

**Steps.**
1. **Understand the constraint first: do not make `reviewFor` (`:77-93`) throw.**
   `acceptance_panel.js:139-146` (`safeAgent`) catches every throw from the stub agent and returns
   `null`, so the guard would degrade a lens rather than report the fixture.
2. Put the assertion **in the guard's own assertion path** — Scenario 1's block, immediately after
   `const r = await runPanel(...)` at `:187` and **before** the cap/dedupe checks at `:193` — **not**
   inside the stubbed agent. (The draft called this "module scope"; `calls` is declared at `:186`
   inside that block, so the phrase was wrong and the placement is what matters.)
3. Derive what the panel actually requested from `calls` (populated at `:165`): take entries whose
   `label` starts with `review:`, strip the prefix, build a Set. Push one failure onto `fails` (`:181`)
   for every `Object.keys(FINDINGS_BY_LENS)` entry absent from that Set. The message must name the
   orphaned key **and** list the lenses actually requested.
4. **Guard against a vacuous pass:** if the derived request Set is empty, that is a broken harness, not
   a clean run — push a failure saying so. Mirrors `tests/test_skill_references.py:99-100`.
5. If the check fired, print the RED block and exit before Scenario 1's remaining assertions run —
   otherwise the reader gets one honest line plus six cascading red herrings. **Route it through the
   existing single RED path**: extract `:285-292` into a `reportRedAndExit()` helper declared near
   `fails` at `:181` and call it from both sites. Two copies of the failure formatter will drift.
6. Use `calls`, not a second regex over `acceptance_panel.js`. `tests/test_skill_references.py:37`
   already owns the fixture ⊆ roster direction in CI.
7. **Do not assert the reverse direction.** `tests/test_skill_references.py:94-95` states the
   one-directionality deliberately: a fixture need not exercise every lens.
8. Extend the header block (`:1-27`) with a fifth pinned property describing the fixture/roster
   agreement. **Do not change the `RUN:` line at `:26`** — `.claude/skills/implement-plan/SKILL.md:309`
   quotes it verbatim.
9. Add nothing to `merge_fallback_guard.mjs` — it has no lens-keyed fixture.

**Acceptance.**
1. The guard still exits 0 with the same four diagnostic lines. The new check is inert on a correct tree.
2. **Prove it bites** — `acceptance_panel.js:201` item 4 names a vacuously-passing check as worse than
   none. Copy the guard into the scratchpad, repoint its `HERE` constant (`:32`) at the real tracked
   skill directory, re-break **one** key, and confirm exit 1. The correct assertion is **not** that the
   string `raw=8, expected 11` appears — re-breaking one key gives `raw=9` or `raw=10`, and `raw=8`
   only arises when both are broken. Assert instead that **the `[cap+dedupe]` line and every
   `dedupe:`/`coverage:` failure are absent**, because the run exits on the fixture assertion before
   Scenario 1's counting assertions execute.
3. Repeat for the other key. Both, not one — a one-sided demonstration is how this defect had two
   instances and one symptom.
4. Repeat with a key **valid in the panel but outside this run's roster** (e.g. `builder:`). It must
   also exit 1, via the same assertion. This is the direction the Python test cannot see.
5. Scratchpad copies stay in the scratchpad. **Never paste the scratchpad's absolute path into a
   tracked file** — `tests/test_no_leaks.py:25` fails the build on a Windows drive path.
6. `uv run pytest -m "not gamedata"` still `1 failed, 171 passed`. Four sibling guards exit 0. ruff /
   format / mypy green. `acceptance_panel.js` still absent from `git diff --stat`.

**Commit note.** `/commit`. Suggested subject: *"Name an unrequested fixture lens instead of
miscounting"*. Put the three re-broken-copy outputs in the body — they are the proof it bites.

---

### Phase 3 — Point the seven dead references at files that exist (RCA Minimal 2–3)

**Goal.** The first red repro test goes green, completing the bugfix track's acceptance contract. Six
skills stop instructing agents to run a file that has never existed here, and the diagnose-bug template
stops teaching a sibling repo's domain.

**Steps.**
1. Replace `tests/test_request_links.py` with `tests/test_doc_links.py` at exactly six grep-verified
   sites: `.claude/skills/commit/SKILL.md:104`, `.claude/skills/update-docs/SKILL.md:56`,
   `.claude/skills/diagnose-bug/SKILL.md:176`, `.claude/skills/make-bugfix-request/SKILL.md:199`,
   `.claude/skills/make-feature-request/SKILL.md:246`,
   `.claude/skills/create-implementation-plan/SKILL.md:251`.
2. **The surrounding promise prose stays exactly as written.** Those bullets promise a fenced-content
   exemption, a `file.py:123` suffix, `var/` targets and a bare-token scan — and **Phase 5 makes all
   four true.** This is the disposition in §5 D1; under it, rewriting the prose would be work thrown
   away.
3. Re-ground the worked example at `.claude/skills/diagnose-bug/SKILL.md:117-118`. It cites
   `tests/test_extract_pagination.py::test_all_pages_landed` failing with *"expected 1230 games, got
   1000"* — there is no pagination in a save-file parser and 1,230 is an NBA regular season. Replace it
   with a real test in this repo that sits **above** the `gamedata` boundary in its module, so the
   template's `uv run pytest` invocation stays runnable. The replacement **must name a file that
   exists even though it sits inside a fenced block** — `tests/test_skill_references.py:32` runs line
   by line with no fence awareness, so an invented name there re-creates the exact defect being fixed.
4. **Move the repro module's docstrings to past tense.** `tests/test_skill_references.py:50-53` states
   as present fact *"Six skills instruct the agent to run `tests/test_request_links.py`. There is no
   such file"* — false the moment this phase lands, and it is the same prose drift this request is
   about. Rewrite to the past with a pointer to this plan. **The two assertions and their regexes are
   untouched** — never weaken them to fit the fix.
5. Do **not** edit `tests/test_doc_links.py` here. Phase 5 owns it.
6. Review `git diff -U0 .claude/skills/` line by line. Every changed line must be the reference token,
   the pagination example, or nothing.

**Acceptance.**
1. `uv run pytest tests/test_skill_references.py` → **2 passed. The red repro is green.** Together with
   the regression guard left behind, this is the bugfix track's definition of done
   (`requests/bugfix-requests/README.md:24-26`).
2. `uv run pytest -m "not gamedata"` → `172 passed, 62 deselected`, zero failures.
3. `git grep -n test_request_links -- .claude/skills/` returns **zero hits**, and the same for
   `test_extract_pagination`. **The tokens deliberately survive elsewhere** and those are expected, not
   failures: `requests/bugfix-requests/README.md:51` (the doc-link Index row quotes the token),
   `tests/test_skill_references.py` (the repro's own docstring, now past-tense), both RCAs, both
   BUGFIX_REQUESTs, and the archived `requests/feature-requests/_done/agent-memory-curation/` artifacts.
4. `uv run pytest tests/test_doc_links.py` passes — no new broken relative link.
5. Seven files changed: six skills plus `tests/test_skill_references.py`. `tests/test_doc_links.py` is
   not among them.
6. The batching guard and four siblings still exit 0; ruff / format / mypy green.

**Commit note.** `/commit`, and **the most important checkpoint — this is where the primary request's
acceptance contract is met.** Suggested subject: *"Point the seven dead test references at files that
exist"*.

---

### Phase 4 — Settle the status-word grammar against the track contract (RCA Root 5)

**Goal.** The skills stop teaching a stage vocabulary the track READMEs do not define.

**Per §5 D3, this phase corrects prose only — no mechanical guard.** The RCA's step 5 asks for one
thing ("settle the grammar"); a guard is Hardening-shaped work, and the meta-audit caught the merge
promoting it into the mandatory tier while making another gated decision depend on it.

**Steps.**
1. Establish the authority by reading: `requests/README.md:12`, `requests/bugfix-requests/README.md:45`
   (`intake → diagnosed → planned → fixed`), `requests/feature-requests/README.md:110`.
2. Correct `.claude/skills/diagnose-bug/SKILL.md` at three **stage-word** sites — `:97`, `:107` (the
   Status blockquote template) and `:150` (the Index-advance instruction) — from `root-cause` to
   `diagnosed`.
3. Correct `.claude/skills/create-implementation-plan/SKILL.md:56` and `:65`, which describe a ready
   bugfix RCA as reading `root-cause`. **State the reason correctly:** `:56` is an Index-lookup hint
   naming a stage word the bugfix track does not define and `:65`'s worked example teaches it. Neither
   *breaks* the disposition gate — `:63-66` gates on the third field, not the stage word, which is
   exactly why this plan's own upstream RCA passed the gate this morning reading `diagnosed`.
4. Correct `.claude/skills/create-implementation-plan/SKILL.md:172` (Index Stage cell `plan` →
   `planned`) and `:176` (template header). Both track READMEs say `planned`, and the in-repo precedent
   is `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1`. **This document already follows
   the corrected form.**
5. **Leave `description:` frontmatter alone** — `.claude/skills/diagnose-bug/SKILL.md:7` and
   `.claude/skills/make-bugfix-request/SKILL.md:5-6` name the *pipeline stage*
   ("intake -> root-cause -> reuse plan/implement"), matching the track README's own table row.
6. **Leave every `next:` slot alone**, including `.claude/skills/make-bugfix-request/SKILL.md:130`'s
   `next: root-cause`. The repo's live practice writes the imperative stage name there. Two planners
   disagreed about this line; the conservative reading wins.
7. Do **not** modify either track README. They are the contract; they are read, never edited.

**Acceptance.**
1. Grepping `.claude/skills/` for `root-cause` returns only genuine prose: the two frontmatter pipeline
   descriptions, the `next:` slot at `make-bugfix-request/SKILL.md:130`, and phrases like "root-cause
   analysis".
2. `uv run pytest -m "not gamedata"` → `172 passed`, zero failures.
3. Both track READMEs byte-unchanged. All five `.mjs` guards exit 0; ruff / format / mypy green.

**Commit note.** `/commit`. Suggested subject: *"The bugfix stage word is the track README's —
diagnosed, not root-cause"*. Say in the body why the frontmatter descriptions and `next:` slots were
deliberately left alone.

---

### Phase 5 — Give the link guard the contract five skills promise (closes `doc-link-guard-mismatch`)

**Goal.** `tests/test_doc_links.py` stops rejecting content the project's own documentation instructs
authors to write, and gains the bare-token scan it never had. **This is the disposition in §5 D1**, and
it is what retires the code-span workaround that currently shapes every artifact in the repo.

**Steps.**
1. **Write the red repro first.** The doc-link RCA deliberately declined to author it at diagnosis time
   because it would have presumed the direction; the direction is now decided, so it is authored here.
   Add a test module (or extend `tests/test_doc_links.py`'s module with testable helpers) asserting the
   four promised behaviours against **fixture strings built in code**, not files on disk:
   a link inside a ``` fence is exempt · a `path.py:123` citation resolves by stripping the suffix ·
   a `var/...` target is exempt · a bare `requests/<slug>/FILE.md` token in prose is **resolved and
   reported when dead**. Run it, confirm RED, and paste the output.
2. Refactor `tests/test_doc_links.py` so the logic is callable rather than living entirely inside one
   test function — the current shape (`:18-38`) cannot be unit-tested at all. Keep
   `test_relative_links_resolve` as the repo-wide entry point.
3. **Fence stripping is a pre-pass, not a regex tweak.** Track fence state line by line (``` and ~~~,
   including inside blockquotes, per the promise text) and blank out fenced regions before `LINK`
   (`:10`) runs. A regex that tries to do this inline will mis-handle nested and blockquoted fences.
4. Normalise a trailing `:123` (and `:12-20`) off a target before `Path.exists()`, alongside the
   existing `#fragment` strip at `:30`. Reuse the shape already proven at
   `acceptance_panel.js:298-301`'s `normLocation` if it helps — but this is our own code, in Python.
5. Exempt `var/` **targets**, distinct from `:15`'s exclusion of `var/` from files *scanned*. Note in a
   comment why both exist: `var/` is gitignored, so its targets can never resolve in CI.
6. Add the bare-token scan: resolve `requests/...` tokens appearing in prose, not only inside Markdown
   link syntax. This is the **dropped capability** the doc-link RCA identified, and it is the half that
   catches a dead pointer misleading the next stage.
7. **Expect this to surface real dead pointers on the first run, and treat each on its merits.** A
   token that is genuinely dead gets fixed; a token that is a deliberate template placeholder gets the
   angle-bracket treatment already exempted at `:28`. Do not weaken the scan to make the repo pass.
8. The five skills' promise prose is already correct after this phase — verify by reading one of the
   canonical instances (`.claude/skills/make-feature-request/SKILL.md:245-250`) against the new
   behaviour, and change nothing there.

**Acceptance.**
1. The Phase 5 repro goes from RED to **green**, and its assertions were not weakened en route.
2. `uv run pytest -m "not gamedata"` green with zero failures, and the tally is recorded — it will have
   grown by the new tests.
3. **Prove the guard still bites:** introduce a genuinely broken relative link in a scratch tracked-path
   file, confirm `tests/test_doc_links.py` goes red, revert. A guard loosened until it passes is not a
   guard.
4. **Prove the bare-token scan bites:** add a prose reference to a `requests/` path that does not
   exist, confirm red, revert.
5. `uv run mypy` clean under strict over the rewritten module; ruff and format clean.
6. All five `.mjs` guards still exit 0.

**Commit note.** `/commit`, and **this is the commit that closes the second request.** Suggested
subject: *"Give the link guard the fence, line-suffix, var/ and bare-token contract"*. State in the
body that the code-span citation workaround is now retired for future artifacts.

---

### Phase 6 — Widen the reference guard to the panel scripts (RCA Hardening 6, accepted en bloc)

**Goal.** Catch the fourth drift instance, which the committed repro cannot see.

**Steps.**
1. **Confirm the gap first.** `tests/test_skill_references.py:44-45` globs `SKILLS_DIR.rglob("*.md")`,
   so a citation inside a `.js` or `.mjs` panel script is invisible to it. Measured 2026-08-17:
   `.claude/skills/create-implementation-plan/plan_panel.js:147` instructs all three planners to ground
   in `docs/data-sources.md`, telling them its contents are "marked unconfirmed". **That file does not
   exist**; this repo's is `docs/data-access.md`. Same class as the other three instances.
2. Widen `skill_documents()` to include `*.js` and `*.mjs` under `.claude/skills/`, and widen the
   token pattern beyond `tests/test_*.py` to the repo-path shapes actually cited there (`docs/*.md` at
   minimum). Run it and **confirm it goes RED naming `plan_panel.js:147`** before fixing anything.
3. Fix `plan_panel.js:147`: `docs/data-sources.md` → `docs/data-access.md`. Read the surrounding
   sentence — it also asserts the file's contents are "currently marked unconfirmed", which is not true
   of `docs/data-access.md` as a whole (its labels are per-claim). Correct the sentence, not just the
   filename.
4. **Do not** widen the scan to `datasets/manifest.json`, which is cited in the same prompt and
   legitimately does not exist yet — CLAUDE.md says `datasets/` arrives with its phase. Exclude
   deliberately-forward-looking paths with a comment saying which and why, or the guard turns red on
   correct work.
5. Likewise exclude the batching guard's own synthetic fixture locations
   (`tests/test_extract_client.py:9` and friends at `verify_batching_guard.mjs:40-64`) — they are
   deliberately fictional test data, not citations.

**Acceptance.**
1. The widened test goes RED naming `plan_panel.js:147`, then green after step 3. Paste both.
2. `uv run pytest -m "not gamedata"` green, zero failures.
3. The exclusions in steps 4–5 are each justified by an in-file comment, so a later reader can tell an
   exemption from an oversight.
4. mypy / ruff / format clean; all five `.mjs` guards exit 0.

**Commit note.** `/commit`. Suggested subject: *"Widen the reference guard to the panel scripts, and
fix the phantom data-sources doc"*.

---

### Phase 7 — Record: statuses, both Index rows, memory, and what stays open

**Goal.** The paper trail matches what landed, the falsified agent-memory entry stops misleading the
next build, and the genuinely-open threads are named rather than quietly inherited.

**Steps.**
1. **Advance this plan's own status blockquote** — it already exists and is the artifact you are
   executing. Do **not** re-create it and do **not** re-date it. It moves to the terminal word once the
   fix lands.
2. Advance the Index row Stage cell for `[verify-batching-guard-red-on-arrival]` at
   `requests/bugfix-requests/README.md:53`, and the status blockquotes on that directory's
   `BUGFIX_REQUEST.md:1` and `ROOT_CAUSE_ANALYSIS.md:1`, in step. **The RCA's body is decided** — do
   not revise its verdict, evidence or fix posture.
3. **Advance `doc-link-guard-mismatch` too** — its row at `requests/bugfix-requests/README.md:51` and
   both its artifacts. Phase 5 closed it. Its Notes cell should point at this plan, since that request
   has no plan of its own. *(This reverses the draft's instruction to leave that row untouched, which
   assumed the doc-link direction stayed gated.)*
4. Leave `leak-guard-blind-to-untracked-files` at `:52` byte-unchanged. Untouched by this work.
5. **Append — never edit, never prune** (`.claude/agents/data-engineer-memory.md:41`) — one dated entry
   correcting the falsified 2026-08-15 entry at `:151-155`. **Claim only what was measured here**
   (per §5 D4): that the fixture keys `data-contract`/`extraction` name lenses this panel does not
   define, and that re-keying them turns the guard green with `acceptance_panel.js` byte-untouched.
   **Do not claim the sibling repo was re-tested — it was not.** The old entry's `measured` claim about
   `nba2k-rpg` failing identically stands; what this refutes is its *interpretation* ("a pre-existing
   upstream defect, not a porting error"). Use the bullet shape at `:28`, label `verified`, tag
   `harness`.
6. Write the IMPLEMENTATION_REPORT with the before/after guard output pasted verbatim, including
   Phase 2's deliberately-corrupted-copy runs. **A green guard nobody has seen fail is a guard nobody
   has tested.**
7. State plainly what this does **not** close: `leak-guard-blind-to-untracked-files` is untouched; RCA
   Hardening 8 (a deliberate sweep for remaining sibling-repo domain residue) is filed as a fresh
   intake per §5 D5, not done here.

**Acceptance.**
1. `uv run pytest tests/test_doc_links.py` and `tests/test_skill_references.py` pass with the new
   documents in the tree.
2. `uv run pytest tests/test_agent_contract.py::test_memory_entries_carry_an_epistemic_label` passes —
   proving the appended entry carries one of the five valid labels (`tests/test_agent_contract.py:84-95`).
3. Both requests' Index rows and all four artifact status blockquotes agree and use the track README's
   grammar, so `/commit`'s doc gate passes without a drift complaint.
4. The `leak-guard-blind-to-untracked-files` row is byte-unchanged.
5. Full local gate green, plus all five `.mjs` guards at exit 0.

**Commit note.** `/commit`. Expect the doc gate to trigger on `.claude/agents/data-engineer-memory.md`
appearing in the staged diff — that trigger is by design (`b32f325`).

---

### Phase 8 — Run the five skill guards in CI (RCA Hardening 7, in scope per §5 D2)

**Goal.** The `.mjs` guards stop being run-by-hand-if-someone-remembers. **A check nobody is forced to
run is how this one stayed red from the day it arrived** — that is the defect class this request is
about.

**Ordered last deliberately.** The acceptance contract is met at Phase 3 and the record is complete at
Phase 7, so a run may end cleanly before this phase. It involves a PR round-trip and may be split into
a follow-up PR without leaving anything half-done.

**Steps.**
1. **Pin `actions/setup-node`** rather than relying on the runner image. This removes the RCA's one
   *unconfirmed* claim from the dependency chain entirely and pins the runtime the guards execute on.
2. **Keep a `node --version` line anyway**, as the first command of the guards step, so the fact is
   measured and recorded in every log rather than merely made irrelevant. Record the first observed
   value in §5 with an epistemic label — `measured <date>`, with the run URL.
3. Add a **step to the existing `quality` job — never a new job.** A new job introduces a display name
   `ops/branch-protection.json` does not list, which is the trap `.github/workflows/ci.yml:13-15` warns
   about in-file. Place it after the pytest step (`:46-49`) so the cheap Python gates fail first.
4. **Do not touch the job display name at `:16-17`.** `ops/branch-protection.json` pins
   `required_status_checks.contexts` to exactly that string with `enforce_admins: true`.
5. Run all five guards by **explicit path, never a glob** — a glob that matches nothing shrinks to zero
   and passes. Write the step as a `run: |` block opening `set -euo pipefail`, then `node --version`,
   then one `node <explicit path>` line per guard. **Do not write a PowerShell-style chain**: CI runs
   bash, while this repo's local shell is PowerShell 5.1 where `&&` is a parser error. The local
   equivalent is five separate invocations, each followed by a `$LASTEXITCODE` check.
6. Confirm the guards need no network, no `uv`, no warehouse and no OOTP install — they read only
   tracked files under `.claude/skills/`. Nothing belongs behind the `gamedata` marker and nothing
   touches ADR 0006.

**Acceptance.**
1. A CI run log showing the guards step naming all five files and exiting 0, inside the
   `Lint, types, tests` job. Paste it with the run URL.
2. **Prove the step is not vacuous IN CI, not just locally.** Once green, push one commit that re-keys
   a single fixture entry, confirm the `Lint, types, tests` check goes **red** naming the guard, then
   revert. A local shell demonstration cannot catch a YAML-level swallowed exit code, which is the
   failure mode `acceptance_panel.js:201` item 4 names.
3. `git diff ops/branch-protection.json` is empty — a step was added to the existing job.
4. The workflow adds no secret, no token and no machine-specific absolute path.
5. All local gates green; all five guards exit 0 locally.

**Commit note.** `/commit`, then hand to the user to push. **Agents never open the PR.** Reversible by
deleting the step.

## 4. Testing & verification

**The acceptance contract is the bugfix track's** (`requests/bugfix-requests/README.md:24-26`): the red
repro goes green, a regression test is left behind, nothing else regresses. Concretely — baseline
`2 failed, 170 passed, 62 deselected` (measured 2026-08-17) becomes zero failures, and
`tests/test_skill_references.py` stays behind as the guard.

**Four independent verification channels, because a green suite is not proof here:**

1. **The guard's own exit code** — `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs`
   exits 0 with four pinned diagnostic lines. This is the symptom the request opened with.
2. **The Python guards in CI** — `tests/test_skill_references.py` (fixture ⊆ roster, and every named
   repo path exists) and `tests/test_doc_links.py` (the promised link contract). These run on every PR;
   the `.mjs` guard does not until Phase 8.
3. **Deliberate re-breaking** — Phases 2, 5 and 8 each require watching a guard go red on a corrupted
   copy and back to green. Every guard this plan ships or extends must be *seen* to fail.
4. **Byte-level negative check** — `acceptance_panel.js` must never appear in `git diff --stat`. It is
   the file the RCA proved correct, and editing it is the outcome the whole diagnosis existed to avoid.

**What is NOT verified here, stated so nobody infers it:** nothing in this plan tests the acceptance
panel's *behaviour* against a real run. The guard tests the panel's dedupe and batching against a
synthetic fixture. Whether the panel finds real bugs is not in scope and is not claimed.

## 5. Decisions

**D1 — The doc-link guard is extended, not the skills corrected.** *Operator, 2026-08-17.* Both RCAs
recommended it; the operator disposed in favour and widened this plan to cover both requests. The three
exemptions are correct on the merits: stage-1 artifacts routinely forward-reference files later stages
create, `file.py:123` is this repo's dominant citation form, and `var/` is gitignored so its targets can
never resolve in CI. Renaming the guard to `test_request_links.py` was rejected independently — it
scans all Markdown, not just `requests/`, so the ported name misdescribes it. **Consequence:** Phase 5
exists, the promise prose in five skills stays untouched because it becomes true, and
`doc-link-guard-mismatch` closes with this plan.

**D2 — CI hardening is in scope, with `actions/setup-node` pinned.** *Operator, 2026-08-17.* Pinning
beats testing the "ubuntu-latest ships node" claim, because it removes the claim from the dependency
chain rather than merely confirming it. The `node --version` line stays anyway so the fact is measured.
Ordered last so the acceptance contract and the record never depend on a PR round-trip.

**D3 — The status-word grammar is corrected in prose only; no mechanical guard.** *Operator,
2026-08-17.* The meta-audit's catch: the RCA's Root step 5 asks to "settle the grammar", and a guard is
Hardening-shaped work the merge promoted into the mandatory tier. A guard would also have needed a
narrow-vs-union scoping decision that no one had made. **Consequence:** Phase 4 edits seven sites and
adds no test; the guard is available as a future hardening item if the drift recurs.

**D4 — The agent-memory correction claims only what was measured here.** *Operator, 2026-08-17,
narrowed by an adversary finding.* The stale entry's `measured` claim — that the guard fails
identically in `nba2k-rpg` — was never re-tested by this RCA and stands. What this work refutes is its
*interpretation*: "a pre-existing upstream defect, not a porting error". Two separately-adapted copies
producing byte-identical failure output is fully consistent with a porting error in the shared
inherited part, which is what the fixture keys turned out to be.

**D5 — Accepted en bloc.** RCA Hardening 6 (generalise the reference guard) lands here as Phase 6,
since the doc-link work is now in scope and the fourth instance sits in a `.js` file the current guard
cannot see. RCA Hardening 8 (a deliberate sweep for remaining sibling-repo residue) is **filed as a
fresh intake** rather than done here — it is an open-ended search with no acceptance criterion, and
folding it in would turn a bugfix into an audit.

**D6 — `acceptance_panel.js` is never edited.** All three planners, both adversaries and the RCA agree.
Editing it to satisfy the guard as written would have renamed this repo's `parser` and `warehouse`
lenses into a sibling's vocabulary and loosened a dedupe that was already correct.

**D7 — The orphaned-lens check lives in the guard's assertion path, not in the stub.** A throw inside
`reviewFor` is swallowed by `safeAgent` (`acceptance_panel.js:139-146`) and would degrade a lens rather
than report the fixture — reporting the wrong thing, which is the defect being fixed.

**D8 — The check is one-directional.** A fixture need not exercise every lens; it must only name lenses
that exist. Asserting the reverse would turn a harmless partial fixture red.

## 6. Risks & gotchas

| Risk | Mitigation |
|---|---|
| **Editing `acceptance_panel.js`** — the single worst outcome, and the guard's own failure text invites it by naming an "over-merge" that does not exist | Phase 1/2/3 acceptance each assert the file is absent from `git diff --stat`. Stated in D6 and in the architecture map |
| **Phase 5 turns the suite red on pre-existing dead pointers** the bare-token scan has never looked for | Expected, not a surprise. Step 7 says treat each on its merits and never weaken the scan; budget time for it. This is the first time these tokens are checked at all |
| **Fence tracking done as a regex** rather than a line-by-line pre-pass | Nested and blockquoted fences are explicitly in the promise text. Step 3 mandates the pre-pass; the repro's fixture strings include a blockquoted fence |
| **The repro's docstrings freeze in pre-fix tense**, leaving the exact prose drift this request is about inside the guard that catches it | Phase 3 step 4 moves them to past tense while leaving assertions untouched |
| **A vacuous CI step** — a glob matching nothing, a swallowed exit code | Phase 8 mandates explicit paths, `set -euo pipefail`, and an **in-CI** red demonstration rather than a local one |
| **PowerShell 5.1 has no `&&`** and native exit codes need `$LASTEXITCODE` | Phase 8 step 5 gives the bash recipe for CI and the separate local equivalent. Do not copy one into the other |
| **A scratchpad absolute path reaching a tracked file** — Phases 2, 5 and 8 all use scratch copies | `tests/test_no_leaks.py:25` fails the build on a Windows drive path. Phase 2 acceptance 5 states it; run the leak guard after staging, since it enumerates via `git ls-files` and is blind to untracked files |
| **The write-capable subagent may not build this** — every path is inside its deny set (`.claude/agents/data-engineer.md:132-165`) | The main thread does the work. If a subagent is spawned for reading, it gets read-only git |
| **Marking a request `fixed` before the fix lands** | `/commit` owns the Index rows; Phase 7 advances them in the same commit as the work, never ahead |

## 7. Files to touch (checklist)

- [ ] `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` — re-key `:54`/`:58`, comment `:150`, orphaned-lens check + `reportRedAndExit()` helper, header property (Phases 1–2)
- [ ] `.claude/skills/commit/SKILL.md` — reference `:104` (Phase 3)
- [ ] `.claude/skills/update-docs/SKILL.md` — reference `:56` (Phase 3)
- [ ] `.claude/skills/make-bugfix-request/SKILL.md` — reference `:199` (Phase 3)
- [ ] `.claude/skills/make-feature-request/SKILL.md` — reference `:246` (Phase 3)
- [ ] `.claude/skills/diagnose-bug/SKILL.md` — reference `:176`, example `:117-118` (Phase 3); stage words `:97`, `:107`, `:150` (Phase 4)
- [ ] `.claude/skills/create-implementation-plan/SKILL.md` — reference `:251` (Phase 3); stage words `:56`, `:65`, `:172`, `:176` (Phase 4) — **five sites in this file**
- [ ] `.claude/skills/create-implementation-plan/plan_panel.js` — `:147` phantom doc (Phase 6)
- [ ] `tests/test_skill_references.py` — docstrings to past tense (Phase 3); widen to `.js`/`.mjs` (Phase 6). **Never weaken its two assertions**
- [ ] `tests/test_doc_links.py` — the promised contract (Phase 5)
- [ ] the Phase 5 red repro — fixture-string tests for the four promised behaviours
- [ ] `.github/workflows/ci.yml` — `actions/setup-node` + the guards step (Phase 8)
- [ ] `.claude/agents/data-engineer-memory.md` — **append one entry** (Phase 7)
- [ ] `requests/bugfix-requests/README.md` — Index rows `:51` and `:53` (Phase 7)
- [ ] `requests/bugfix-requests/verify-batching-guard-red-on-arrival/` — `BUGFIX_REQUEST.md:1`, `ROOT_CAUSE_ANALYSIS.md:1`, this plan's `:1`, new `IMPLEMENTATION_REPORT.md` (Phase 7)
- [ ] `requests/bugfix-requests/doc-link-guard-mismatch/` — `BUGFIX_REQUEST.md:1`, `ROOT_CAUSE_ANALYSIS.md:1` (Phase 7)
- [ ] **NOT** `.claude/skills/implement-plan/acceptance_panel.js` — proven correct; must never appear in the diff
- [ ] **NOT** `requests/bugfix-requests/README.md`'s `leak-guard-blind-to-untracked-files` row, or either track README's contract text

## 8. Conventions (bake these in)

- **Commits go through `/commit` only** — never `git commit` ad hoc, not for a two-word change. Never
  push `main`, never force-push, never amend. **Agents never open the PR.**
- **Subagents get read-only git**, and the write-capable `data-engineer` **may not build this at all** —
  every path is in its deny set.
- **Citations are inline code spans until Phase 5 lands.** After it, Markdown links with line suffixes
  become legal; before it, they turn CI red.
- **Never write an absolute or drive-letter path into a tracked file** (`tests/test_no_leaks.py:25`).
  The leak guard enumerates via `git ls-files`, so it is blind to untracked files — scan after staging.
- **No new pytest markers.** `pyproject.toml` sets `--strict-markers` with `gamedata` as the only
  declared marker; an undeclared one is a hard collection error, not a skip.
- **mypy strict covers `tests/` as well as `src/`** — annotate `-> None` like the existing modules.
- The parser conventions (read-only game, sequential walking, the fixed-offset ban, `players.csv` as
  ground truth, epistemic labels on field mappings, ADR 0006) **have no surface in this change** and
  must not be padded in.

## 9. Code-grounding verification

The panel's two adversaries verified the draft's 76 `code_references` against the repo and returned 22
findings; the meta-audit returned 13. Panel health: `planners_ok` 3, `adversaries_ok` 2,
`meta_audit_ok` 1, `degraded_lenses` empty. Corrections applied to this document:

| Cited in the draft | Verified / corrected |
|---|---|
| Phase 3 acceptance: repo-wide grep returns hits only in RCA/request files | **Corrected** — false on today's tree (14 files hit). Scoped to `.claude/skills/`, legitimate survivors enumerated |
| Phase 7: "Open `IMPLEMENTATION_PLAN.md` with `created <today>`" | **Corrected** — circular; the plan exists and is being executed. Now "advance its status blockquote" |
| Phase 4 rationale: "the disposition gate would reject a `diagnosed` RCA" | **Corrected** — `SKILL.md:63-66` gates on the third field, not the stage word. Real drift, wrong reason |
| `acceptance_panel.js:208-209`: "`.filter(Boolean)` is why an unknown area fails silently" | **Corrected** — `:208`'s `|| []` swallows an unknown *area*; `:209`'s `.filter(Boolean)` swallows an unknown *spec key*. Two different lines |
| `tests/test_doc_links.py` "39 lines" | **Corrected** — 38 |
| "four repair sites in `create-implementation-plan/SKILL.md`" | **Corrected** — five (`:251` in Phase 3, the rest in Phase 4) |
| Phase 1: "`7 lenses` is drift, the fixture defines six" | **Corrected** — the measured roster *is* 7; `acceptance` emits no findings. The edit is now optional and must not assert 6 |
| Phase 2: "`raw=8, expected 11` must NOT appear" | **Corrected** — passes vacuously in all three demonstrations; restated as absence of the `[cap+dedupe]` and `dedupe:`/`coverage:` lines |
| Phase 2: assertion "at module scope" | **Corrected** — `calls` is block-scoped at `:186`; restated as Scenario 1's block after `:187` |
| Phase 6/8: local `&&` chain to prove the CI step | **Corrected** — PowerShell 5.1 parser error; bash recipe and local `$LASTEXITCODE` form given separately |
| Phase 2: inline a second RED-printing block | **Corrected** — routed through one `reportRedAndExit()` helper |
| Phase 8 acceptance: local demonstration of non-vacuity | **Corrected** — restored to an in-CI red demonstration, per the meta-audit |
| Phase 7 memory entry "the 2026-08-15 entry is falsified outright" | **Corrected** — its `measured` sibling-repo claim was never re-tested; only the interpretation is refuted (D4) |
| Grammar guard in the mandatory tier | **Removed** — meta-audit; the RCA asked only to settle the grammar (D3) |
| `verify_batching_guard.mjs` 293 lines · `ci.yml` 49 lines · `CORE` `:189-194` · `SPEC_DEFS` `:196-202` · `AREA_TO_SPEC` `:203-207` · `README.md:45`/`:53` | **Verified** — independently re-checked against files read directly |

**Found during planning, not by the panel:** `plan_panel.js:147` cites `docs/data-sources.md`, which
does not exist — the fourth instance of the drift class, inside the planning panel itself. Phase 6.

## References

- `requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md` — the decided upstream artifact
- `requests/bugfix-requests/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md` — the second request this plan closes
- `requests/bugfix-requests/verify-batching-guard-red-on-arrival/reviews/plan-proposals.md` — the three planners' raw proposals
- `requests/bugfix-requests/verify-batching-guard-red-on-arrival/reviews/plan-adversarial.md` — 22 adversary + 13 meta-audit findings, the convergence map, and the gated decisions as posed
- `requests/bugfix-requests/README.md` — the track contract, status grammar, and definition of done
- `.claude/agents/data-engineer.md` — the write allowlist that puts every path here in the deny set
