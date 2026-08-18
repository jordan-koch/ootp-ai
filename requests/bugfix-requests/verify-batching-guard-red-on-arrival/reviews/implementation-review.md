<!-- Raw, unfiltered acceptance-panel output. Saved by /implement-plan step 5.
     Agent prose is FENCED throughout: reviewers quote deliberately-dead paths as
     evidence, and tests/test_doc_links.py resolves unfenced ones. Fencing a quoted
     dead target is the documented remedy, not a workaround. -->

# Acceptance panel - raw output

Run 2026-08-17 over the uncommitted diff. Roster: acceptance, fidelity, correctness, edgecases, skill-quality, parser, infra-cost.
Verdict: **fix**.

```json
{
  "reviewers_ok": 7,
  "reviewers_total": 7,
  "verifiers_ok": 5,
  "verifiers_total": 5,
  "verify_batches": 4,
  "verify_cap": 4,
  "findings_blocker_major_raw": 17,
  "findings_blocker_major_deduped": 17,
  "findings_unverified": 0,
  "meta_ok": 1,
  "criteria_total": 41,
  "criteria_met": 29,
  "criteria_unmet": 10,
  "criteria_unverifiable": 2,
  "confirmed_findings": 19,
  "blockers": 1,
  "majors": 4
}
```

degraded_lenses: `[]`

## Verdict rationale

~~~
Not "go": four upstream/plan acceptance criteria are measurably UNMET on the tree I inspected — the bugfix track's record row (no IMPLEMENTATION_REPORT.md), Phase 7 acceptance 1 and 3 (no status advance, no Index rows), Phase 7 step 6 (the corrupted-copy evidence is unrecorded anywhere), and Phase 8 acceptance 1-2 (nothing is pushed, so the in-CI non-vacuity proof the plan called non-negotiable has not happened). Two further core criteria are partial: Phase 5 step 7 ("do not weaken the scan to make the repo pass") and the guard-matches-its-promise criterion that is the entire subject of doc-link-guard-mismatch. A "go" with those open would be dishonest. Not "no-go" either: the implementation is on-plan and substantively correct — every phase's code landed, the pinned guard output matches character-for-character, the widened reference guard demonstrably found MORE drift than the plan predicted (three phantom `docs/data-sources.md` sites, not one), and the fixes are right on the merits. What stands between this and landing is bounded and mechanical: write the record, and repair three defects in the newly written link guard that recreate — inside the fix — the same "a guard that quietly stopped checking" failure class this request exists to eliminate. That is a "fix".
~~~

## Summary

~~~
The CODE half of `verify-batching-guard-red-on-arrival` is real and I re-proved it by execution, not by reading: `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 with the four diagnostic lines the plan pinned byte-for-byte; `uv run pytest -m "not gamedata"` is 187 passed / 0 failed (baseline 2 failed, 170 passed); ruff, ruff-format and mypy-strict are all clean; `git diff HEAD --stat -- src/` is empty, so ADR 0001, the fixed-offset ban, players.csv ground truth and ADR 0006 have no surface here and none was violated. The upstream RCA's acceptance contract — red repro green, regression guard left behind, nothing else regresses — is MET. Two halves are not. (1) Phase 7, the RECORD, produced no diff at all: `git status --porcelain -- requests/` is empty, the request directory holds no IMPLEMENTATION_REPORT.md, and both Index rows plus all four artifact status blockquotes still read `planned`/`diagnosed`. The plan's own words — "A green guard nobody has seen fail is a guard nobody has tested" — describe exactly what was lost: the three deliberately-corrupted-copy runs Phase 2 demanded exist only in reviewers' scratchpads, because six separate lenses had to re-derive them. (2) The NEW link guard shipped with three defects I confirmed myself by probe: `strip_fences` misses a fence opened on a list-item line (`.claude/skills/commit/SKILL.md:189` is literally "2. ```"), which flips fence parity and silently blanks 75 non-blank lines running to EOF — the only file of the 82 scanned that ends inside an open fence; an `own_dir` exemption the plan never authorised that buys exactly ONE token repo-wide while silencing every typo'd sibling-artifact pointer (I measured both directions); and a fifth documented promise, "link titles are exempt too", still unimplemented in three skills — I resolved `[the ADR](docs/decisions/0001-read-only-no-write-back.md "ADR 0001")` through the shipped code and got exists=False against an untitled control of exists=True. Nothing was REFUTED outright, but I corrected several sub-claims rather than launder them forward: fidelity's assertion that the own_dir exemption is what hid the missing IMPLEMENTATION_REPORT is FALSE (the plan carries no such bare token — the exemption rescues only first-sight's checklist line); the "29%" / "209 markdown files" / "92 blanked lines" figures are actually 75 of 194 non-blank lines and 82 files scanned; "Phase 7 entirely undone" overstates it, since step 5's agent-memory append DID land, correctly, append-only with a `verified` label; and the "four properties" header drift is real but `git grep 'four properties'` returns nothing because the phrase wraps lines 8-9 — I read the file to confirm rather than trusting either grep.
~~~

## Acceptance ledger

### U1 - MET
~~~
criterion: RCA contract: the committed red repro goes GREEN
source: ROOT_CAUSE_ANALYSIS.md:26-53 (Reproduction (red))

evidence:
I ran `uv run pytest -m "not gamedata" -q` -> 187 passed, 0 failed, which includes both tests in tests/test_skill_references.py. Baseline red state independently reproducible: `git grep -n -E "test_request_links|test_extract_pagination" HEAD -- .claude/skills/` returns the 7 dead references the RCA quoted; the same grep on the working tree exits 1 with no output.

reconciliation:
Auditor and verifier agree (met/met), both by execution. Reproduced by me.
~~~

### U1b - MET
~~~
criterion: RCA contract: the human-readable symptom — `node verify_batching_guard.mjs` exiting 1 on a clean checkout — is resolved
source: ROOT_CAUSE_ANALYSIS.md:60-62

evidence:
I ran the guard myself: EXIT=0, printing `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`, `[dead-batch] verifiers=4/5 unverified=3/9 note="verify:b1 (3 findings left unverified)"`, `[rubberstmp] b1Calls=2 verifiers=4/5 unverified=3`, `[verifyCap ] cap=2 batches=2 unverified=0/9`, then GREEN — byte-identical to IMPLEMENTATION_PLAN.md:153-156.

reconciliation:
The verifier raised this as its own row; the auditor folded it into P1.1. Both met; I re-ran it.
~~~

### U2 - MET
~~~
criterion: RCA contract: a regression test is left behind, with its assertions not weakened to fit the fix
source: ROOT_CAUSE_ANALYSIS.md:26-58; IMPLEMENTATION_PLAN.md:600 ('never weaken its two assertions')

evidence:
Both tests survive in tests/test_skill_references.py with `assert not broken` / `assert not unknown` intact; REPO_REFERENCE at :38 was WIDENED (docs/*.md added) and skill_documents() widened from *.md to *.md+*.js+*.mjs. Two further guards added: verify_batching_guard.mjs:196-220 (in-process orphaned-lens check) and tests/test_doc_link_contract.py (14 tests).

reconciliation:
Both agree. The verifier's framing is stronger and I adopt it: scannable_text() blanks only 23 of 331 lines and cannot be a regression at all, because .mjs files were not scanned by this guard at baseline.
~~~

### U3 - MET
~~~
criterion: RCA contract: nothing else regresses — no audit or test regresses
source: requests/bugfix-requests/README.md:24-26 (definition of done)

evidence:
My own runs: pytest 187 passed / 62 deselected / 0 failed; `uv run ruff check .` -> All checks passed!; `uv run ruff format --check .` -> 119 files already formatted; `uv run mypy` -> Success: no issues found in 39 source files. All five .mjs guards exit 0.

reconciliation:
Unanimous across all six lenses and the verifier; reproduced independently.
~~~

### U4 - UNMET
~~~
criterion: Bugfix-track contract: the record carries a 'red repro now green + regression test present' row and the request is closable
source: requests/bugfix-requests/README.md:24-26; IMPLEMENTATION_PLAN.md:441-443

evidence:
`git status --porcelain -- requests/` returns NOTHING. `Get-ChildItem requests\bugfix-requests\verify-batching-guard-red-on-arrival` lists only reviews/, BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md — no IMPLEMENTATION_REPORT.md. The Index still reads `planned` for both doc-link-guard-mismatch and verify-batching-guard-red-on-arrival.

reconciliation:
Auditor 'unmet'; verifier folded it into P7 'unmet'. No disagreement; I reproduced both commands.
~~~

### P0 - NOT-VERIFIABLE
~~~
criterion: Phase 0: baseline RED output, pytest tally, tool versions and branch name recorded; four sibling guards exit 0; tree clean
source: plan-phase-0

evidence:
No working-notes artifact and no IMPLEMENTATION_REPORT.md exist, so the recording cannot be inspected; the tree now carries the implementation, so baseline cleanliness cannot be observed retroactively. The four sibling guards do exit 0 now, and node/uv are present.

reconciliation:
Auditor split this into P0.1/P0.2/P0.3 (not-verifiable / met / not-verifiable); the verifier gave one not-verifiable row. Same substance; I take the verifier's shape and keep the auditor's 'four guards exit 0' as evidence inside it.
~~~

### P1.1 - MET
~~~
criterion: Phase 1: the batching guard exits 0 with exactly the four pinned diagnostic lines
source: plan-phase-1 acceptance 1

evidence:
Reproduced by me — see U1b. Character-for-character match with the plan's pinned text.

reconciliation:
Auditor met, verifier met, both by execution.
~~~

### P1.2 - MET
~~~
criterion: Phase 1: fixture re-keyed to warehouse/parser with formatting and delimiters preserved; test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines passes
source: plan-phase-1 acceptance 2

evidence:
verify_batching_guard.mjs:61 `  warehouse: [` and :65 `  parser: [` — two-space indent, unquoted, with `const FINDINGS_BY_LENS = {` and the column-0 `}` intact, which matters because tests/test_skill_references.py:44 carves on those literal delimiters. That test passes inside the green suite.

reconciliation:
Both agree; the verifier additionally checked delimiter preservation, which is the sharper check. Adopted.
~~~

### P1.3 - MET
~~~
criterion: Phase 1: the stale teaching comment is caught — `git grep -E 'data-contract|extraction' -- .claude/skills/implement-plan/` returns zero hits
source: plan-phase-1 acceptance 5

evidence:
The grep exits 1 with no output; the comment at verify_batching_guard.mjs:157 now reads `// -> warehouse + parser + skill-quality specialists`.

reconciliation:
Auditor and verifier agree, both by execution.
~~~

### P1.4 - UNMET
~~~
criterion: Phase 1 isolation: `git diff --stat` lists exactly one file and the intermediate tally is exactly `1 failed, 171 passed, 62 deselected` — the proof the fixture fix and the reference fix are independent
source: plan-phase-1 acceptance 3-4; IMPLEMENTATION_PLAN.md:84-87

evidence:
`git log --oneline -3` ends at a656acb 'Plan the ported-guard repair'; the whole implementation is one uncommitted blob of 13 modified files + 1 untracked. The plan required each phase to end at a /commit-gated checkpoint and said Phases 1 and 3 'must not be merged or reordered'. The intermediate tally is not reconstructible without modifying the tree.

reconciliation:
DISAGREEMENT: auditor 'partial' (crediting the acceptance_panel.js-untouched half), verifier 'unmet'. I side with the VERIFIER — this criterion is about phase isolation and the independence proof, and neither happened; the acceptance_panel.js half is a separate criterion (C1) and is credited there. Scoring 'partial' here would double-count a pass.
~~~

### P2.1 - MET
~~~
criterion: Phase 2: the new orphaned-lens check is inert on a correct tree — the guard still exits 0 with the same four lines, and the check sits in Scenario 1 before the counting assertions (D7)
source: plan-phase-2 acceptance 1

evidence:
Exit 0, same four lines. The block sits at verify_batching_guard.mjs:196-220, after `const r = await runPanel(...)` and before the cap/dedupe assertions — not inside the stub, so safeAgent cannot swallow it.

reconciliation:
Auditor and verifier agree, static read plus execution on both sides.
~~~

### P2.2 - MET
~~~
criterion: Phase 2: PROVE IT BITES — re-break one fixture key; exit 1, with the `[cap+dedupe]` line and every dedupe:/coverage: failure ABSENT
source: plan-phase-2 acceptance 2

evidence:
Independently reproduced by five lenses plus the verifier, using two different techniques (scratchpad copy with HERE repointed; in-memory data:-URL re-import). Every run: exit 1, a single `fixture: FINDINGS_BY_LENS has an orphaned lens '<key>' that the panel never requests …` line, no `[cap+dedupe]` line, no cascade.

reconciliation:
Both met. Both also note what I record in S1: the acceptance is satisfied only because reviewers re-derived it — the implementer left no record of ever running it.
~~~

### P2.3 - MET
~~~
criterion: Phase 2: repeat for the OTHER key — both, not one
source: plan-phase-2 acceptance 3

evidence:
`parser` -> `extraction` (auditor, parser, edgecases) and `parser` -> `ingest` (verifier): exit 1, same single-line shape, no [cap+dedupe] line.

reconciliation:
Agreed by execution on both sides.
~~~

### P2.4 - MET
~~~
criterion: Phase 2: repeat with a key VALID in the panel but outside this run's roster (`builder:`) — the direction the Python test structurally cannot see
source: plan-phase-2 acceptance 4

evidence:
Re-keying to `builder` exits 1 via the same assertion in every reviewer's run and the verifier's. This is the coverage tests/test_skill_references.py cannot provide, since `builder` IS in the panel's lens set.

reconciliation:
Agreed by execution on both sides.
~~~

### P2.5 - MET
~~~
criterion: Phase 2: an empty derived request Set is itself a failure (no vacuous pass), and there is one RED path via reportRedAndExit()
source: plan-phase-2 steps 4-5

evidence:
The verifier forced the branch by replacing the `calls.filter(...)` expression with `[]` in memory: exit 1 with `fixture: the panel requested NO review lenses — the harness is broken, not the fixture`. reportRedAndExit() at :192-196 is called from both the fixture check (:219) and the tail (:327); the tail's three inlined lines are gone in the diff.

reconciliation:
Only the VERIFIER tested this; the auditor's ledger has no row for it. I adopt the verifier's — it is execution evidence for a criterion that would otherwise go unscored.
~~~

### P2.6 - MET
~~~
criterion: Phase 2: no scratchpad absolute path reaches a tracked file (tests/test_no_leaks.py fails the build on a Windows drive path)
source: plan-phase-2 acceptance 5 / conventions

evidence:
Regex scan over `git diff HEAD` for drive-letter paths returns nothing. Because tests/test_no_leaks.py enumerates via `git ls-files` it is blind to the untracked tests/test_doc_link_contract.py, so auditor AND verifier both applied its PATTERNS to that file by hand — zero hits.

reconciliation:
Agreed; both independently noticed the leak-guard blind spot and worked around it, which is the right instinct given the open leak-guard bug.
~~~

### P3.1 - MET
~~~
criterion: Phase 3: `uv run pytest tests/test_skill_references.py` -> 2 passed; whole suite zero failures
source: plan-phase-3 acceptance 1-2

evidence:
187 passed / 0 failed in my own run. The plan predicted `172 passed` at this checkpoint; the delta to 187 is exactly Phase 5's 15 new tests (14 in test_doc_link_contract.py + test_bare_request_tokens_resolve), which reconciles arithmetically.

reconciliation:
Auditor and verifier agree, including the same reconciliation of the tally delta.
~~~

### P3.2 - MET
~~~
criterion: Phase 3: `git grep test_request_links` and `test_extract_pagination` in .claude/skills/ return ZERO hits, with the surrounding promise prose byte-unchanged (D1)
source: plan-phase-3 acceptance 3

evidence:
Both greps exit 1 with no output. All six sites now read tests/test_doc_links.py (commit/SKILL.md:104, update-docs/SKILL.md:56, diagnose-bug/SKILL.md:176, make-bugfix-request/SKILL.md:199, make-feature-request/SKILL.md:246, create-implementation-plan/SKILL.md:251), matching the HEAD grep line-for-line.

reconciliation:
Agreed. The verifier additionally read the diff line-by-line to confirm the promise prose is byte-unchanged per D1, which the auditor asserted but did not show; I take the verifier's stronger evidence.
~~~

### P3.3 - MET
~~~
criterion: Phase 3: the worked example is re-grounded on a test that EXISTS and sits above the gamedata boundary so the template's `uv run pytest` stays runnable
source: plan-phase-3 step 3

evidence:
diagnose-bug/SKILL.md now cites `tests/test_parse_world.py::test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key`, defined at tests/test_parse_world.py:179; the first `@pytest.mark.gamedata` in that module is at :513. Running that exact selector under `-m 'not gamedata'` passes.

reconciliation:
Agreed by execution on both sides. Caveat carried as nit S17: I read .claude/skills/diagnose-bug/SKILL.md:113-119 myself and the accompanying failure message ('expected 3058 calendar entries, got 2600') describes a count the named column/key test cannot produce.
~~~

### P3.4 - MET
~~~
criterion: Phase 3: the repro module's docstrings move to past tense; its two assertions and regexes are NOT weakened
source: plan-phase-3 step 4; plan §7

evidence:
Docstrings now read 'Six skills USED TO instruct … Repointed 2026-08-17' and 'Re-keyed 2026-08-17'; the assertion bodies and FIXTURE_LENS/LENS_KEY regexes are untouched in the diff, and REPO_REFERENCE was widened rather than narrowed.

reconciliation:
Agreed. The verifier flagged the incidental test RENAME as a side effect; I carry it as nit S13 rather than as a ledger failure, since the new name is more accurate.
~~~

### P3.5 - NOT-VERIFIABLE
~~~
criterion: Phase 3 isolation: seven files changed — six skills plus tests/test_skill_references.py; tests/test_doc_links.py not among them
source: plan-phase-3 acceptance 5

evidence:
No Phase-3 commit exists; `git diff HEAD --stat` shows all 13 files from all phases at once. The per-phase boundary cannot be recovered without rewriting the tree, which is out of bounds for review.

reconciliation:
Auditor 'not-verifiable'; the verifier folded it into its phase-isolation 'unmet' row. I keep it as its own not-verifiable row — a criterion whose evidence no longer exists differs from one that was checked and failed.
~~~

### P4 - MET
~~~
criterion: Phase 4: the bugfix stage word becomes `diagnosed`/`planned` at seven sites; `git grep root-cause -- .claude/skills/` returns only the two frontmatter pipeline descriptions, the `next:` slot and genuine prose; both track READMEs byte-unchanged
source: plan-phase-4 acceptance 1 and 3

evidence:
The grep returns exactly 4 sanctioned lines (diagnose-bug/SKILL.md:7; make-bugfix-request/SKILL.md:5, :6, :130). The seven corrections are visible in the diff at diagnose-bug/SKILL.md :97/:107/:150 and create-implementation-plan/SKILL.md :56/:65/:172/:176. `git status --porcelain -- requests/` is empty, so both track READMEs are byte-unchanged.

reconciliation:
Auditor and verifier agree exactly, including the enumeration of the four permitted survivors.
~~~

### P5.1 - MET
~~~
criterion: Phase 5: the four promised behaviours (fence exemption, file.py:123 suffix, var/ target exemption, bare-token scan) are implemented and unit-tested against fixture strings built in code, not files on disk
source: plan-phase-5 acceptance 1

evidence:
tests/test_doc_link_contract.py holds 14 tests grouped under the four promises, all against in-code strings, importing the refactored helpers strip_fences/link_targets/resolve_target/bare_request_tokens (tests/test_doc_links.py:42-137). All 14 pass. Necessarily red before the fix: `git show HEAD:tests/test_doc_links.py` defines only markdown_files and test_relative_links_resolve, so the contract module could not even import.

reconciliation:
Auditor and verifier agree, both by execution plus a HEAD-blob check.
~~~

### P5.2 - MET
~~~
criterion: Phase 5: PROVE the link guard still bites, and PROVE the bare-token scan bites
source: plan-phase-5 acceptance 3-4

evidence:
Three lenses and the verifier drove the REAL test functions with injected fixtures and got red in both directions, e.g. `broken relative links: docs/__probe_never_written__.md -> decisions/9999-does-not-exist.md` and `bare requests/ tokens that do not resolve: … -> requests/feature-requests/no-such-slug/PROJECT_SCOPE.md`. Neither scan is vacuous: across the 82 files the guard examines ~393-397 link targets and 209 bare tokens.

reconciliation:
Agreed by execution. As with P2.2, met only in reviewers' hands — no record of the implementer having run it exists.
~~~

### P5.3 - PARTIAL
~~~
criterion: Phase 5 step 7: the scan was NOT weakened to make the repo pass — a dead token gets fixed, a placeholder gets the angle-bracket treatment, nothing else
source: plan-phase-5 step 7 (IMPLEMENTATION_PLAN.md:353-355)

evidence:
Fence-stripping hides zero currently-dead link targets tree-wide (verifier measured 0). But an `own_dir` exemption the plan never authorised was added at tests/test_doc_links.py:126/134. I measured its blast radius myself: it rescues exactly ONE token in the whole repo (`requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> …/IMPLEMENTATION_REPORT.md`) while silencing typo'd siblings — my probe `bare_request_tokens('… /ROOT_CAUSE_ANALYSES.md', source=<that plan>)` returns `[]` while `source=None` returns the dead token.

reconciliation:
Auditor 'partial', verifier 'partial' — same one-token measurement reached independently, and I reproduced it a third time. The verifier is more charitable ('narrow, documented and honest, but ratify rather than inherit'); the auditor harsher. 'Partial' stands either way; the remedy is a gated decision.
~~~

### P5.4 - PARTIAL
~~~
criterion: Phase 5: the guard now matches the promise prose the five skills state to authors — which is the whole subject of doc-link-guard-mismatch
source: promise text at .claude/skills/create-implementation-plan/SKILL.md:256 and two siblings

evidence:
Four of five stated promises are implemented. The fifth is not: three skills promise '`var/` targets AND LINK TITLES are exempt too'. I ran the shipped code — `link_targets('[the ADR](docs/decisions/0001-read-only-no-write-back.md "ADR 0001")')` returns the target WITH the title attached, resolve_target leaves it attached, exists=False; the untitled control on the same real file is exists=True. `git diff HEAD -- .claude/skills/ | Select-String 'link titles'` is empty, so the promise is live and untouched.

reconciliation:
Only the SKILL-QUALITY lens raised this; the auditor scored P5.1 'met' on the plan's enumerated four and has no row for it. Verify confirmed it and I re-ran it against a real ADR path to rule out a fabricated target. I ADD this row because the request being closed is doc-link-guard-mismatch — closing it with a false promise still live in three skills is a partial, not a met.
~~~

### P5.5 - MET
~~~
criterion: Phase 5: mypy clean under strict over the rewritten module; ruff and format clean
source: plan-phase-5 acceptance 5

evidence:
My own runs: mypy 'Success: no issues found in 39 source files'; ruff 'All checks passed!'; format '119 files already formatted'. pyproject.toml sets strict=true over ["src","tests"], so both new modules are in scope.

reconciliation:
Agreed by execution on both sides.
~~~

### P6.1 - MET
~~~
criterion: Phase 6: the widened reference guard goes RED naming plan_panel.js:147 before the fix, and green after
source: plan-phase-6 acceptance 1

evidence:
Three lenses and the verifier replayed the new REPO_REFERENCE regex against the `git show HEAD:` blobs and got three hits: plan_panel.js:147, plan_panel.js:164, scope_panel.js:125, all citing a `docs/data-sources.md` that has never existed. The old tests/test_*.py-only regex would have found zero. I read the scope_panel.js hunk myself: it now cites `docs/data-access.md` (Test-Path True) and drops the false 'currently marked unconfirmed' claim in favour of per-claim labelling — the sentence-level correction step 3 demanded, not a filename swap.

reconciliation:
Agreed. Both sides flag that the plan predicted one site and the guard found three — over-delivery, carried as nit S14, not a ledger failure.
~~~

### P6.2 - MET
~~~
criterion: Phase 6: each exclusion (datasets//build/, the batching guard's synthetic fixture locations) is justified by an in-file comment so a reader can tell an exemption from an oversight
source: plan-phase-6 acceptance 3

evidence:
tests/test_skill_references.py:34-40 documents the datasets//build/ exclusion citing CLAUDE.md's 'arrives with its phase' rule; scannable_text()'s docstring at :60-70 justifies blanking the FINDINGS_BY_LENS block rather than exempting the whole file. The verifier proved the claim rather than accepting it: 23 lines blanked, `test_extract_client.py` gone from the scannable text, the `RUN:` line still scanned.

reconciliation:
Auditor met (static read), verifier met (execution). I take the verifier's — it is the one that measured.
~~~

### P6.3 - PARTIAL
~~~
criterion: Phase 6: the widened token pattern covers 'the repo-path shapes actually cited there (docs/*.md at minimum)'
source: plan-phase-6 step 2

evidence:
REPO_REFERENCE = `(?:tests/test_[a-z0-9_]+\.py|docs/[a-z0-9/-]+\.md)`. The verifier fed candidates to the live regex: `docs/decisions/0012-scouted-ratings-only.md` matches, but `docs/README.md` and `docs/Data_Access.md` return []. Meets the stated minimum and caught the real drift; an uppercase or underscored phantom would still slip.

reconciliation:
DISAGREEMENT of form, not substance: the auditor raised it only as a nit finding with no ledger row; the verifier scored the criterion 'partial'. I side with the VERIFIER — 'at minimum' is satisfied but the criterion's intent is not, and the verifier is the one who probed the live regex. Carried as nit S15.
~~~

### P7.1 - UNMET
~~~
criterion: Phase 7: an IMPLEMENTATION_REPORT.md is written carrying the before/after guard output and Phase 2's deliberately-corrupted-copy runs verbatim
source: plan-phase-7 step 6 / acceptance 1

evidence:
`Get-ChildItem requests\bugfix-requests\verify-batching-guard-red-on-arrival` returns reviews/, BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md. No report exists. The plan's justification at :441-443 — 'A green guard nobody has seen fail is a guard nobody has tested' — names exactly the evidence lost.

reconciliation:
Auditor 'unmet' (P7.1/P7.6), verifier 'unmet'. Unanimous across all six lenses; I ran the listing myself.
~~~

### P7.2 - UNMET
~~~
criterion: Phase 7: both requests' Index rows and all four artifact status blockquotes agree, using the track README's grammar, so /commit's doc gate passes without a drift complaint
source: plan-phase-7 acceptance 3

evidence:
I read the Index myself: requests/bugfix-requests/README.md still shows `| [doc-link-guard-mismatch](…) | planned |` and `| [verify-batching-guard-red-on-arrival](…) | planned |`, the latter's Notes still present-tense ('exits 1 on a clean checkout and always has'). IMPLEMENTATION_PLAN.md:1 still reads `planned · … · next: implement`; the four artifact blockquotes still read `diagnosed · … · next: plan`.

reconciliation:
Auditor and verifier both 'unmet'. One mitigation both recorded honestly and I preserve: .claude/skills/commit/SKILL.md:117-129 gives /commit ownership of advancing Index rows and statuses, so that half is arguably deferred by design. The IMPLEMENTATION_REPORT is not — /commit does not write it.
~~~

### P7.3 - MET
~~~
criterion: Phase 7 step 5: ONE dated agent-memory entry is APPENDED (never edited, never pruned), carries an epistemic label, and is narrowed per D4
source: plan-phase-7 step 5 / acceptance 2

evidence:
.claude/agents/data-engineer-memory.md is a pure append (+24 lines at EOF, no deletions). The mandated entry at :290 carries `**2026-08-17** · `verified` ·` and honours D4 by stating the sibling-repo measurement 'stands and was not re-tested here'. `uv run pytest tests/test_agent_contract.py::test_memory_entries_carry_an_epistemic_label` passes.

reconciliation:
Auditor 'met'; the verifier folded it inside P7 'unmet' while acknowledging the append landed and is correct. I SPLIT IT OUT AS MET — it is a distinct satisfied criterion, and burying it in an unmet phase row understates what the implementer actually did. Deviation noted separately: three entries were appended where the plan said one; the extras are in-shape and append-only, so it is a gated decision, not a defect.
~~~

### P7.4 - MET
~~~
criterion: Phase 7: the leak-guard-blind-to-untracked-files Index row is byte-unchanged
source: plan-phase-7 acceptance 4

evidence:
requests/bugfix-requests/README.md is entirely unmodified, so :52 is byte-unchanged.

reconciliation:
Auditor 'met' with the honest caveat that it is met only because the whole phase was skipped. I keep 'met' and repeat the caveat rather than laundering it into a clean pass.
~~~

### P7.5 - UNMET
~~~
criterion: Phase 7 / §5 D5: RCA Hardening 8 is filed as a fresh intake rather than done here
source: plan §5 D5

evidence:
No new intake directory exists anywhere under requests/ — the verifier and two lenses listed requests/bugfix-requests, requests/feature-requests and requests/data-incidents and found the newest directory is verify-batching-guard-red-on-arrival itself; `git status --untracked-files=all` shows nothing under requests/.

reconciliation:
The fidelity, parser and verifier lenses tracked D5; the auditor's ledger has no row. I adopt it — it is a named commitment in the decided plan and it did not happen.
~~~

### P8.1 - MET
~~~
criterion: Phase 8: a guards step is added to the EXISTING quality job (never a new job); the `Lint, types, tests` display name untouched; ops/branch-protection.json diff empty; five guards by EXPLICIT path under set -euo pipefail; no secret, token or machine path
source: plan-phase-8 steps 1-5, acceptance 3-4

evidence:
I read the step at .github/workflows/ci.yml myself: it opens `set -euo pipefail`, runs `node --version`, then names all five guards by literal path — no glob, and the in-file comment explains why ('a glob that matches nothing shrinks to zero commands and the step passes vacuously'). The verifier parsed the YAML with pyyaml: one job (`quality`), name unchanged, step appended after pytest so the cheap Python gates fail first, and ops/branch-protection.json:5 still pins the matching context with an empty `git status -- ops/`.

reconciliation:
Auditor met (static read + path cross-check), verifier met (YAML parse). The parse is the stronger evidence for 'one job, right order'; adopted.
~~~

### P8.2 - UNMET
~~~
criterion: Phase 8: a real CI run log showing the guards step exiting 0, pasted with its run URL; AND an IN-CI red demonstration (push a re-keyed fixture, watch the check go red, revert) — the plan states a local demonstration explicitly does not satisfy this
source: plan-phase-8 acceptance 1-2 (IMPLEMENTATION_PLAN.md:493-502)

evidence:
Nothing is committed or pushed (`git log --oneline -3` ends at a656acb; the tree is dirty), so no run and no URL can exist. The plan's reason is specific: 'A local shell demonstration cannot catch a YAML-level swallowed exit code.' Phase 8 step 2's follow-on — record the observed node version in §5 with a `measured <date>` label — is also undone, consistent with requests/ being untouched.

reconciliation:
DISAGREEMENT: auditor split into P8.1 'not-verifiable' + P8.2 'unmet'; verifier gave a single 'unmet'. I side with the VERIFIER's single unmet — 'not-verifiable' understates it, because the criterion is unmet BECAUSE the prerequisite (push) was not taken, which is a state of the work rather than a limit of the review. Mitigating and preserved: the plan at :469-471 permits Phase 8 to split into a follow-up PR, so this is a legitimate deferral if declared.
~~~

### C1 - MET
~~~
criterion: Convention/D6: acceptance_panel.js is NEVER edited — the RCA-proven-correct file stays byte-untouched
source: plan §5 D6 / plan-phase-1 acceptance 4

evidence:
`git diff HEAD --stat -- .claude/skills/implement-plan/acceptance_panel.js` produces no output; the file is absent from my own `git status --porcelain` listing of all 14 changed paths.

reconciliation:
Auditor and verifier agree; I reproduced the porcelain listing.
~~~

### C2 - MET
~~~
criterion: Convention: the `RUN:` line in verify_batching_guard.mjs is unchanged, because implement-plan/SKILL.md quotes it verbatim
source: plan-phase-2 step 8

evidence:
verify_batching_guard.mjs:33 reads `// RUN: node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` — moved down by the header insertion, text identical — and SKILL.md:309 still quotes the same command.

reconciliation:
Agreed by both, one via Select-String and one via file read.
~~~

### C3 - MET
~~~
criterion: Project conventions: game is READ-ONLY (ADR 0001); no fixed-offset parser read; players.csv ground truth; no OOTP data tracked (ADR 0006); no hardcoded machine paths; no ad-hoc commit
source: CLAUDE.md / plan §8

evidence:
I ran `git diff HEAD --stat -- src/` — empty. The 14-path change set touches only .claude/, .github/ and tests/: no parser code, no dbt model, no dataset, no .env read, no save file, no .dat/.csv. tests/test_no_leaks.py passes inside the green suite, and its PATTERNS were applied by hand to the untracked new test file (zero hits). Nothing is committed, consistent with agents-commit-only-through-/commit.

reconciliation:
Unanimous across all six lenses and the verifier. The parser lens correctly reported its whole axis as vacuously clean rather than manufacturing findings — the right call, and the plan's §2 said these conventions 'have no surface here and must not be padded in'.
~~~

### C4 - PARTIAL
~~~
criterion: Plan §7 files-to-touch: the changed set matches the checklist, with no unplanned files and nothing on the NOT list
source: plan §7 (IMPLEMENTATION_PLAN.md:590-609)

evidence:
Both NOT items honoured (acceptance_panel.js absent; requests/ untouched, so the leak-guard row and both track READMEs are byte-unchanged). All code/skill items done. MISSING: the five requests/ items. EXTRA: .claude/skills/scope-feature/scope_panel.js, not on the checklist — I read the hunk and it is a correct third instance of the phantom-doc fix the widened Phase 6 guard demanded, i.e. an under-specified checklist rather than scope creep.

reconciliation:
Auditor 'partial', verifier 'partial', same two deviations named independently. No disagreement.
~~~

## Confirmed findings (19)

### [BLOCKER] Phase 7 produced no diff at all: no IMPLEMENTATION_REPORT.md, no status advances, no Index rows, no D5 intake

~~~
location: requests/bugfix-requests/README.md:53 (and :51); requests/bugfix-requests/verify-batching-guard-red-on-arrival/ (no IMPLEMENTATION_REPORT.md)
confidence: high
category: acceptance-contract

PROBLEM
SEVERITY NOTE, stated plainly rather than edited in silently: five lenses raised this; four rated it MAJOR and the acceptance lens rated it BLOCKER. I keep BLOCKER because it is not a quality concern but four measurably UNMET acceptance criteria (U4, P7.1, P7.2, P7.5) plus five unticked lines on the plan's own files-to-touch checklist — the change cannot pass /commit's doc gate or close either request as it stands. Verified by me directly: `git status --porcelain -- requests/` returns nothing; the request directory holds only reviews/, BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md; the Index at :51 and :53 still reads `planned` for both requests, with verify-batching-guard's Notes still present-tense ('exits 1 on a clean checkout and always has'); all four artifact blockquotes still read `diagnosed · … · next: plan` and the plan's own :1 still reads `planned · … · next: implement`; no new intake directory exists for RCA Hardening 8 (D5). The sharpest loss is the report itself. Phase 2 acceptance 2-4 and Phase 5 acceptance 3-4 are satisfied ONLY because six reviewers independently re-derived the demonstrations — the corrupted-copy runs, the injected-broken-link probes, the pre-fix RED replay — none of which exists anywhere in the tree. Correction to one lens's framing: Phase 7 is not 'entirely undone'; step 5's memory append DID land and is correct. The accurate statement is that no requests/ artifact was touched.

PROPOSED FIX
Before /commit: (1) write requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_REPORT.md pasting the pre-fix RED output, the post-fix four diagnostic lines, and the three re-broken-fixture runs verbatim — all reproducible with the in-memory technique (re-key one FINDINGS_BY_LENS entry, repoint HERE at the tracked skill dir, import as a data: URL, write no file) — and do NOT paste an absolute scratch path into the tracked report; include the 'red repro now green + regression test present' row naming tests/test_skill_references.py's two tests, plus the old->new test identifier from S13. (2) Advance the Index Stage cells at README.md:51 and :53 to `fixed`, rewrite their Notes to past tense, point doc-link-guard-mismatch's Notes at this plan, and leave the leak-guard row at :52 byte-unchanged. (3) Advance the four artifact status blockquotes plus this plan's :1, in the same commit as the work and never ahead of it, without re-dating or revising the decided RCA bodies. (4) File the D5 Hardening-8 sweep as a fresh intake, or state in the report that it was consciously dropped.
~~~

### [MAJOR] strip_fences misses a fence opened on a list-item line, flipping fence parity and silently blanking 75 lines of commit/SKILL.md out of BOTH link scans

~~~
location: tests/test_doc_links.py:25 (FENCE) and :42-65 (strip_fences); triggered by .claude/skills/commit/SKILL.md:189
confidence: high
category: correctness

PROBLEM
SEVERITY NOTE: four lenses raised this; three rated major and the parser lens rated blocker. I keep MAJOR — nothing dead sits in the blinded window today, so the build is not wrong, it is un-checked. I confirmed the mechanism myself: FENCE allows only whitespace and blockquote markers before the delimiter, so my probe prints `line189: '2. ```' FENCE: False` and `line191: '   ```' FENCE: True` — the CommonMark-legal fence opened as list-item content is invisible, its genuine CLOSER is read as an OPENER, and parity inverts for the rest of the file. Measured on the shipped code: 75 originally-non-blank lines are blanked, running to line 257, and my repo-wide scan shows commit/SKILL.md is the ONLY one of the 82 scanned files that ends inside an open fence. Reviewers proved the consequence rather than inferring it: injecting `[the missing doc](docs/definitely-not-here.md)` plus a dead `requests/…` token at line 250 makes BOTH scans return empty, while the identical injection at line 20 of the same file is caught by both. So the guard Phase 3 just repointed six skills at has a permanent blind spot inside one of those very skills — the 'quietly stopped checking' failure class this request exists to eliminate, recreated inside the fix. Panel figures corrected: it is 75 of 194 non-blank lines (39%), not '29% of 258'; 82 files are scanned, not 209.

PROPOSED FIX
Widen the opener to allow a list marker: FENCE = re.compile(r"^\s*(?:>\s*)*(?:(?:[-*+]|\d+[.)])\s+)?(`{3,}|~{3,})"). Two lenses ran exactly this across every scanned file: it reclassifies exactly ONE line repo-wide (commit/SKILL.md:189), after which zero files end with an open fence — the change is contained. Then add two fixtures to tests/test_doc_link_contract.py, which today has no list-item fence anywhere: a dead link INSIDE a `2. ``` ` block (exempt) and a dead link on the line AFTER it closes (still reported). The second is the assertion that would have caught this.
~~~

### [MAJOR] An unterminated fence silently blanks the rest of the document with no diagnostic, so any author who forgets a closing fence switches the guard off for the file's tail

~~~
location: tests/test_doc_links.py:50-65 (strip_fences carries `marker` past the end of the loop unchecked)
confidence: high
category: correctness

PROBLEM
Distinct from S2 and independently reachable, which is why I carry it separately rather than merging. The loop exits with `marker` still bound and line 65 returns only a str, so there is no channel to report an unbalanced document even if one wanted to. Reproduced by the edgecases lens and confirmed by verify: strip_fences("```\ncode\n\n[dead](docs/nope.md)\n") yields zero link targets — a dead pointer, invisible, no error. My own repo-wide scan confirms exactly one file is in that state now (via S2), but the mechanism needs no bug to fire: any forgotten closer turns the guard off for the tail and the reward is a green build. A guard whose failure mode is 'passes silently' is what the doc-link RCA names ('both failure directions are silent') and what IMPLEMENTATION_PLAN.md:355 forbids.

PROPOSED FIX
Make the unbalanced case loud. Either have strip_fences return the still-open fence's line number alongside the blanked text (or raise), or add a third repo-wide test asserting no scanned Markdown file ends inside an open fence, naming the file and the opening line. Cover it in tests/test_doc_link_contract.py with a fixture string that opens a fence and never closes it. This converts a silent exemption into a red build, which is the entire point of the guard.
~~~

### [MAJOR] The own-directory exemption in bare_request_tokens is far broader than the single token it buys, and silences typo'd sibling-artifact pointers — a loosening the plan explicitly forbade

~~~
location: tests/test_doc_links.py:126 and :134 (`if own_dir is not None and target.parent == own_dir: continue`)
confidence: high
category: guard-weakening

PROBLEM
Raised by all six lenses; verify confirmed on three separate runs; I reproduced both halves myself. The exemption keys on the DIRECTORY only, never the filename, so any unresolvable `requests/…` token in the citing document's own directory is skipped. My probe: bare_request_tokens('see requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSES.md', source=<that plan>) returns [], while source=None correctly returns the dead token. A plan citing its own RCA, or an RCA citing its own BUGFIX_REQUEST, is the most common cross-reference this pipeline makes — so the docstring's justification at :123-124 ('a token pointing into a DIFFERENT request's directory is still checked, which is where a genuinely misleading cross-reference would live') has it exactly backwards. My blast-radius measurement across all 82 scanned files: the exemption rescues exactly ONE token, requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> …/IMPLEMENTATION_REPORT.md, whose documented remedy is a one-line fence. IMPLEMENTATION_PLAN.md:355 says in terms: 'Do not weaken the scan to make the repo pass.' CORRECTION carried forward honestly: the fidelity lens claimed this exemption is why nothing flagged the missing IMPLEMENTATION_REPORT (S1). That is FALSE — my source=None sweep shows this plan contains no such bare token; its checklist writes only the directory path, which resolves. Do not repeat that claim in the report.

PROPOSED FIX
Two viable remedies, gated below. Preferred: drop the `source`/`own_dir` parameter and the :134 continue entirely, then fence or angle-bracket the single offending line in requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md — the remedy Phase 5 step 7 prescribes and the five skills already document — and retarget tests/test_doc_link_contract.py:149-165 onto that path. Alternative: narrow the predicate to a small frozenset of pipeline stage filenames intersected with `target.parent == own_dir`, AND add the negative test the suite lacks (a typo'd sibling in the source's own directory IS reported), AND write the fifth rule into the skills' promise prose so code and documentation stay one artifact.
~~~

### [MAJOR] A fifth documented promise — 'link titles are exempt too', stated in three skills — is still unimplemented, so doc-link-guard-mismatch would close with the defect it is about still live

~~~
location: .claude/skills/create-implementation-plan/SKILL.md:256 (identical at diagnose-bug/SKILL.md:184 and make-bugfix-request/SKILL.md:204); implementation at tests/test_doc_links.py:20 and :73-106
confidence: high
category: acceptance-gap

PROBLEM
Raised only by the skill-quality lens; verify confirmed; I re-ran it myself against a REAL file to rule out a fabricated path. LINK at :20 captures the whole parenthetical and resolve_target strips only `#fragment` and a line suffix, so my probe on `[the ADR](docs/decisions/0001-read-only-no-write-back.md "ADR 0001")` returns the target with ` "ADR 0001"` still attached and resolves to exists=False, while the untitled control on the SAME real file (Test-Path True) is exists=True. `git grep 'link titles' -- .claude/skills/` returns those three live lines and `git diff HEAD -- .claude/skills/ | Select-String 'link titles'` is empty, so the promise is pre-existing and untouched by this change. The miss has a precise cause worth recording: Phase 5 step 8 told the implementer to verify the prose against the new behaviour by reading make-feature-request/SKILL.md:245-250 — the ONE copy that omits the link-title clause. No titled link exists in the repo today, so the suite is green; but an author who follows the documentation gets a red build, which is exactly the defect doc-link-guard-mismatch was filed about.

PROPOSED FIX
In resolve_target, strip an optional CommonMark link title before resolving: split the captured target on unescaped whitespace and keep the first token when the remainder is wrapped in "…", '…' or (…). Add two cases to tests/test_doc_link_contract.py under a 'Promise 5' heading — a titled link to a live file resolves, and a titled link to a DEAD file is still reported, mirroring test_a_genuinely_dead_target_is_still_dead_with_a_suffix so the strip cannot launder a broken path. If the operator declines the scope, delete the ' and link titles' clause from the three SKILL.md lines instead and say so in the report — the promise cannot be left false either way.
~~~

### [MINOR] Phase 8's in-CI non-vacuity proof has not happened and cannot have — nothing is committed or pushed

~~~
location: .github/workflows/ci.yml:70-78 against IMPLEMENTATION_PLAN.md:493-502
confidence: high
category: verification-gap

PROBLEM
Raised by four lenses at minor/question; verify agreed it is a real gap with a legitimate deferral path. The step itself is well built and I read it: `set -euo pipefail`, `node --version`, five guards by literal path with no glob, appended to the existing `quality` job so the branch-protection context name is untouched, with an in-file comment explaining why a glob would pass vacuously. But Phase 8 acceptance 1 wants a run log with its URL and acceptance 2 wants the step proved non-vacuous IN CI — push a commit re-keying one fixture entry, watch `Lint, types, tests` go red naming the guard, revert — precisely because 'a local shell demonstration cannot catch a YAML-level swallowed exit code'. `git log --oneline -3` ends at a656acb and the tree is dirty, so no run exists. Step 2's follow-on (record the observed node version in §5 with a `measured <date>` label and run URL) is likewise undone. Two residual risks nobody could clear locally: CI pins node 22 while every local run was v24.15.0, and `set -euo pipefail` under GitHub's default `bash -e {0}` is correct in principle but unexercised.

PROPOSED FIX
Either carry both demonstrations through on this PR — capture the guards-step log with the run URL, then push one throwaway commit re-keying `warehouse:` back to `'data-contract':` at verify_batching_guard.mjs:61, confirm the check goes red inside `Skill guards (node)`, and revert — or split Phase 8 into the follow-up PR the plan permits at :469-471 and say so explicitly in the IMPLEMENTATION_REPORT under 'what this does not close'. Do not record the phase complete on local evidence.
~~~

### [MINOR] The batching guard's header still says it pins 'the four properties' immediately above a list of five

~~~
location: .claude/skills/implement-plan/tests/verify_batching_guard.mjs:8-9 (and .claude/skills/implement-plan/SKILL.md:309)
confidence: high
category: doc-drift

PROBLEM
Raised by the fidelity and parser lenses. A note on method, because it matters: `git grep 'four properties'` returns NOTHING — the phrase WRAPS, with 'four' ending line 8 and 'properties' opening line 9 — so I read the file rather than trusting the grep in either direction. Lines 8-9 read 'this guard pins the four properties that make it safe to trade agents for batches:' followed by items 1 through 5, item 5 being the FIXTURE/ROSTER AGREEMENT property Phase 2 correctly added at :25-29. This is a stale count in a comment, inside the one file whose entire reason for being in this request is that a stale comment at :150 taught the wrong roster for the guard's whole life. No test can see it — Phase 1 acceptance 5 flagged exactly this class. While there, the inserted clause at :11-13 left 'collapse to <= cap batch agents, the' stranded mid-thought.

PROPOSED FIX
Change :8 to 'pins the five properties' and reflow the item-1 sentence at :11-13. Separately extend .claude/skills/implement-plan/SKILL.md:309, which still enumerates the exit-0 contract as four properties, with the fifth clause ('…and its fixture names only lenses the panel actually requests') and note that CI now runs all five guards on every PR. Leave the guard's `RUN:` line at :33 untouched — SKILL.md quotes it verbatim.
~~~

### [MINOR] The unreachable placeholder/glob filter in bare_request_tokens makes a unit test pass for a different reason than its name claims

~~~
location: tests/test_doc_links.py:129; test at tests/test_doc_link_contract.py:135
confidence: high
category: dead-code

PROBLEM
Raised by the correctness lens. `if "*" in token or "<" in token or ">" in token: continue` can never fire: BARE_REQUEST_TOKEN at :35 uses character class [A-Za-z0-9._/-] with a final class of [A-Za-z0-9_/], so no emitted token can contain *, < or >. Measured: findall('requests/<track>-requests/<slug>/') == [] and findall('requests/bugfix-requests/*/BUGFIX_REQUEST.md') == ['requests/bugfix-requests/']. So test_a_templated_or_globbed_token_is_not_a_dead_pointer is green because the regex TRUNCATES, not because the filter exempts — a vacuously-passing check of exactly the kind the panel's own contract calls worse than none. The truncation has a real side effect too: a templated path under a dead prefix reports the confusing stub `requests/no-such-track/` rather than what the author wrote.

PROPOSED FIX
Either delete the unreachable branch and rewrite the test to assert the real behaviour (a templated path yields no dead report because the token truncates, and the truncated prefix is what gets checked), or widen BARE_REQUEST_TOKEN to admit */</> so the filter becomes live and the reported token matches the source text. Do not leave a test whose name claims a rule the code does not implement.
~~~

### [MINOR] scannable_text's fixture carve uses str.partition, so a reflowed closing brace would silently drop the rest of the file from the scan

~~~
location: tests/test_skill_references.py:74 (`fixture, _, tail = rest.partition("\n}\n")`)
confidence: medium
category: fragile-carve

PROBLEM
Raised by the fidelity lens at medium confidence; latent, not live. str.partition returns (rest, '', '') when the separator is absent, so if the FINDINGS_BY_LENS block's column-0 closing `}` is ever indented, reflowed, or given a trailing comment, `tail` becomes empty and every line after the marker leaves the scan silently. The verifier measured that the happy path is currently correct (331 lines in, 331 out; 23 blanked; the RUN: line preserved; test_extract_client.py blanked). This is the same silent-swallow shape the doc-link RCA blamed for the original defect, reintroduced inside the guard's own helper.

PROPOSED FIX
Capture the separator and assert it was found: `fixture, sep, tail = rest.partition("\n}\n")` then `assert sep, f"{path}: FINDINGS_BY_LENS block has no column-0 closing brace — the carve is stale"`, so a reflowed fixture fails loudly instead of shrinking the scan.
~~~

### [MINOR] The synthetic fixture paths recur outside the blanked block, so the next natural widening of REPO_REFERENCE turns the guard red on its own test data

~~~
location: tests/test_skill_references.py:60 (scannable_text) vs .claude/skills/implement-plan/tests/verify_batching_guard.mjs:247, :248, :262
confidence: high
category: maintainability

PROBLEM
Raised by the correctness lens. scannable_text blanks only the `const FINDINGS_BY_LENS = { … \n}\n` block, and its docstring argues that blanking the block rather than exempting the file keeps the rest of the guard in scope. But the same invented locations appear OUTSIDE it: 'src/ootp_ai/land/writer.py' at :247, 'transform/models/silver/dim_player.sql' at :248, repeated at :262. Harmless today only because REPO_REFERENCE covers just tests/test_*.py and docs/*.md. The moment anyone widens it to src/ or transform/ — the obvious next hardening, which the appended memory entry effectively celebrates — the guard goes red on its own fixture, inside the file it exists to police.

PROPOSED FIX
Blank the synthetic locations wherever they occur rather than by block position — derive the fixture's loc strings once and blank every occurrence of each in that file — or have the scenario-1 assertions compare against constants derived from FINDINGS_BY_LENS instead of repeating the literals. Add an in-file comment saying which exemption covers which site, to the standard Phase 6 acceptance 3 set for the others.
~~~

### [MINOR] The nine /commit-gated phases were collapsed into one uncommitted blob, permanently retiring three per-phase delta criteria

~~~
location: requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md:84-87
confidence: high
category: process

PROBLEM
`git log --oneline -3` shows HEAD = a656acb with all 13 modified files plus one untracked sitting uncommitted. The plan required each phase to end at a /commit-gated checkpoint and stated that 'Phases 1 and 3 must not be merged or reordered — Phase 1's acceptance is that exactly one of the two red tests flips, which is the proof the fixture fix and the reference fix are independent'. With no intermediate commits, P1.3 (1 failed, 171 passed), P1.4 (exactly one file) and P3.5 (seven files changed) can never be measured, and the independence proof was never taken. The acceptance lens re-derived independence structurally instead: the fixture test reads only the .mjs + panel (tests/test_skill_references.py:103-112) while the other reads the skill documents, and `git grep` on HEAD shows all 7 dead references were still present.

PROPOSED FIX
Cannot be undone without rewriting the tree, which is out of bounds for review. Record it honestly in the IMPLEMENTATION_REPORT: state the phases were executed as one unit, name the three criteria that were therefore not measured, and paste the structural independence evidence in their place. If the operator wants the checkpoints back, the diff splits cleanly by path — Phase 1/2 to verify_batching_guard.mjs, Phase 3/4 to the six SKILL.md files, Phase 5 to the two test modules, Phase 6 to the two panel .js files, Phase 8 to ci.yml.
~~~

### [MINOR] node and the five .mjs guards became a blocking CI gate, but neither README.md's setup nor ops/README.md's local toolchain mentions them

~~~
location: ops/README.md:26-34; README.md:96-102
confidence: high
category: doc-drift

PROBLEM
Raised by the infra-cost lens and confirmed mechanically: `git grep -n -i -E 'node|npm|\.mjs' -- README.md ops/` returns nothing, and the repo carries no package.json, .nvmrc or .node-version. As of this diff the required `Lint, types, tests` check also runs five node scripts, so a contributor who runs the documented local gate to completion still cannot predict the check, and node is now an undocumented prerequisite for reproducing CI. Same shape as the defect being fixed: a documented contract that no longer describes the gate that actually runs.

PROPOSED FIX
Add a guards line to ops/README.md's Local toolchain block noting node is required and that CI pins node 22 via actions/setup-node, keeping the PowerShell caveat the plan established (five separate invocations each followed by a $LASTEXITCODE check — `&&` is a parser error in PowerShell 5.1). /update-docs would normally catch this; it has not run because nothing is committed.
~~~

### [NIT] The RCA's named red-repro test was renamed, so the selector the upstream artifact cites no longer resolves

~~~
location: tests/test_skill_references.py:78 (test_every_repo_path_a_skill_names_exists)
confidence: high
category: traceability

PROBLEM
ROOT_CAUSE_ANALYSIS.md:38 and IMPLEMENTATION_PLAN.md:160 both pin the repro as test_every_test_file_a_skill_names_exists. Phase 6 widened and renamed it. The rename is right on the merits — the test now covers docs/*.md too, so the old name would itself be drift — but anyone replaying the RCA's repro by node id now gets an empty-selection error and has to guess, which is the same failure mode the RCA describes for tests/test_request_links.py. The plan authorised widening the regex but never a rename.

PROPOSED FIX
Keep the new name and close the trace: add one clause to the docstring naming the previous identifier, and state old -> new in the IMPLEMENTATION_REPORT next to the 'red repro now green' row. Do not revise the decided RCA body.
~~~

### [NIT] scope_panel.js and a second plan_panel.js site were changed although the plan's checklist names only one — correct work, unrecorded

~~~
location: .claude/skills/scope-feature/scope_panel.js:125; .claude/skills/create-implementation-plan/plan_panel.js:164
confidence: high
category: scope-deviation

PROBLEM
The Phase 6 checklist names only 'plan_panel.js — :147 phantom doc'. Four lenses replayed the widened REPO_REFERENCE against the `git show HEAD:` blobs and all three sites are genuine instances of the same phantom docs/data-sources.md, so the widened guard REQUIRES all three fixed for Phase 6 acceptance 2 to pass. I read the scope_panel.js hunk myself: it swaps in docs/data-access.md (which exists) and replaces the false 'its contents are currently marked unconfirmed' claim with per-claim labelling — the sentence-level correction step 3 demanded, not a filename swap. This is an under-specified checklist, not over-reach. The only problem is that with no IMPLEMENTATION_REPORT (S1) nothing anywhere reconciles diff against checklist.

PROPOSED FIX
Record it in the IMPLEMENTATION_REPORT and the /commit message body: the widened guard found three instances rather than the one the plan measured; list all three file:line sites; note that the checklist was under-specified. No code change needed.
~~~

### [NIT] REPO_REFERENCE's docs/ pattern excludes uppercase and underscores, so several real citation shapes stay invisible

~~~
location: tests/test_skill_references.py:38
confidence: high
category: coverage

PROBLEM
`docs/[a-z0-9/-]+\.md` matches only lowercase-hyphen paths. The verifier fed candidates to the live regex: docs/decisions/0012-scouted-ratings-only.md matches, but docs/README.md and docs/Data_Access.md return []. Root-level CLAUDE.md, FRONT_OFFICE.md and README.md, which the skills cite constantly, are out of scope entirely. The three phantom instances happened to fit the narrow shape; the guard is correct-by-luck rather than by construction. This satisfies the plan's stated minimum ('docs/*.md at minimum') but leaves the obvious next gap.

PROPOSED FIX
Widen the docs alternative to `docs/[A-Za-z0-9_/-]+\.md` and optionally add the three root-level filenames; re-run and treat any new hits on their merits rather than narrowing back. Keep the datasets//build/ exclusion comment as-is.
~~~

### [NIT] The guard scans _done/ archives although all five skills promise only live (non-_done/) bodies are scanned

~~~
location: tests/test_doc_links.py:141 (markdown_files) vs .claude/skills/make-bugfix-request/SKILL.md:198 and siblings
confidence: medium
category: promise-code-mismatch

PROBLEM
The promise Phase 5 exists to make true says 'A live (non-`_done/`) artifact body is scanned by tests/test_doc_links.py'. markdown_files() filters only .git and var, so archived artifacts are in scope — 1 file today, and the new bare-token scan inherits it across all 209 token resolutions. Being stricter than documented can only false-red, never false-green, and the mismatch predates this change; but archiving a request MOVES its directory, so a frozen requests/<old-path>/… token inside an archived body goes dead through no author's fault and turns CI red on history nobody may edit. It is the one promise of the five still untrue after the phase whose stated goal was to make them all true.

PROPOSED FIX
Either exclude `_done` in markdown_files() alongside .git and var, with a comment citing the promise text, or state in the module docstring that archives are deliberately in scope and open a follow-up to reconcile the five skills' wording. Do not leave it undecided.
~~~

### [NIT] The re-grounded diagnose-bug worked example pairs a real test with a failure message that test cannot produce

~~~
location: .claude/skills/diagnose-bug/SKILL.md:113-119
confidence: high
category: doc-correctness

PROBLEM
I read this myself. The template now cites the real, runnable tests/test_parse_world.py::test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key — correct, and above the gamedata boundary as required — but pairs it with 'fails: expected 3058 calendar entries, got 2600'. That test asserts a column set and a key, not an entry count. A cold agent copies this template verbatim, so it teaches a red output the named test could not emit: a smaller instance of the same 'artifact describes a repo that does not exist' drift this request is about.

PROPOSED FIX
Make the failure message match the assertion — e.g. '(fails: expected 8 columns, got 7)' — or cite a different real test whose failure genuinely is an entry count.
~~~

### [NIT] strip_fences compares only the fence marker's first character, so an inner 3-backtick fence closes a 4-backtick block

~~~
location: tests/test_doc_links.py:56 and :61 (`marker = hit.group(1)[0]`)
confidence: medium
category: edge-case

PROBLEM
The regex captures the whole run but only [0] is retained and compared, discarding fence LENGTH. CommonMark requires a closing fence at least as long as the opener; here a 4-backtick block is terminated by the first inner 3-backtick line, re-exposing the remainder to both scans. Zero 4+-backtick fences exist in the tree today, so nothing is affected — but these very skills teach authors to write ABOUT fences ('Put either inside a fenced code block (``` or ~~~, blockquoted is fine)'), and the natural way to quote that guidance is a longer outer fence, which would leak.

PROPOSED FIX
Keep the whole marker run and close only when `hit.group(1)[0] == marker[0] and len(hit.group(1)) >= len(marker)`. Add one fixture: a 4-backtick fence containing a 3-backtick fence and a dead link stays fully exempt.
~~~

### [NIT] tests/test_doc_link_contract.py imports its sibling as a bare top-level module — the only such import in the suite

~~~
location: tests/test_doc_link_contract.py:23
confidence: medium
category: fragility

PROBLEM
`import test_doc_links as guard` works only because tests/ has no __init__.py (confirmed absent) and pytest's default prepend import mode puts tests/ on sys.path; mypy resolves it the same way. It is the only sibling-module import in the suite. Adding tests/__init__.py, switching to importlib import mode, or running the module outside pytest's rootdir would each break collection with an ImportError that reads as a missing dependency rather than a layout assumption.

PROPOSED FIX
A one-line comment at :23 recording the assumption is sufficient ('tests/ has no __init__.py; pytest prepend mode and mypy both put this directory on the path'). The point is that the next person moving test layout gets a warning rather than a puzzle.
~~~

## Meta-audit findings (7)

### [MAJOR] DROPPED SIGNAL: the edgecases lens's finding that the new orphaned-lens check has no automated regression test was dropped from the merged report entirely

~~~
location: .claude/skills/implement-plan/tests/verify_batching_guard.mjs:199-225 (merged report confirmed_findings — no S-row exists)
confidence: high
category: dropped-signal

PROBLEM
The edgecases lens raised F5: "The new orphaned-lens check in the batching guard has no automated regression test — its correctness rests on a manual demonstration." I walked all six lenses' findings against S1-S19 and this is the ONLY one with no merged counterpart. It is not redundant with S6 (which is about the CI step being unproven) or S11 (phase collapse) — it is about the check's own branch being unexercised by any automated gate. I verified the substance: `Select-String -Path tests/*.py -Pattern 'subprocess|node'` shows no pytest anywhere in the repo invokes node, and tests/test_skill_references.py:126-128 states its one-directionality on purpose ("A fixture need not exercise every lens"), so it structurally cannot see the `builder:` direction that Phase 2 acceptance 4 exists for. The irony is on the page: the repro's own docstring at tests/test_skill_references.py:123-124 asserts "the guard now carries its own equivalent check so a `node` run catches the next one too" — a claim that only holds if something forces the node run, which is precisely what Phase 8 has not yet proven (S6). So the merged report drops the finding that closes the loop between S6 and the request's whole thesis: a check nobody is forced to run is how this guard stayed red for its entire life.

PROPOSED FIX
Add it back as an S-finding at minor severity, sourced to edgecases F5, with the fix that lens proposed and which I confirmed is viable: one pytest in tests/test_skill_references.py that reads verify_batching_guard.mjs, rewrites HERE/PANEL to the tracked path derived from REPO_ROOT, substitutes one FINDINGS_BY_LENS key for `builder`, writes to tmp_path, runs it via subprocess, and asserts returncode == 1, `orphaned lens 'builder'` in stdout, and `[cap+dedupe]` absent — skipped when shutil.which('node') is None so the Python-only path stays green. Build the path from tmp_path, never a literal, so tests/test_no_leaks.py stays clean. Note in the same row that this would also make Phase 2 acceptance 2-4 reproducible from the repo instead of from reviewers' scratchpads.
~~~

### [MAJOR] S2's blast-radius figure is wrong and asserted as the report's own measurement, and the false-RED half of the confirmed finding was dropped

~~~
location: merged report confirmed_findings S2 ("silently blanking 75 lines"); real behaviour at tests/test_doc_links.py:25 against .claude/skills/commit/SKILL.md:189-191
confidence: high
category: evidence-accuracy

PROBLEM
The merged report positions itself as the arbiter of the panel's arithmetic ("Panel figures corrected: it is 75 of 194 non-blank lines (39%), not '29% of 258'") and states "I confirmed the mechanism myself... Measured on the shipped code: 75 originally-non-blank lines are blanked, running to line 257." I ran it: the shipped strip_fences blanks 76 non-blank lines, range 35-258, not 75/257. Worse, that figure is the wrong QUANTITY. Most of those lines are legitimately fenced code the guard is supposed to skip; the defect's actual blast radius is the DIFFERENCE between the shipped tracker and a list-marker-aware one, which I measured at 49 over-blanked non-blank lines (76 shipped vs 30 list-aware). The verify ledger had already produced two mutually inconsistent deltas for this — V14 said 52 lines of disagreement, V9 said 64 — and the merged report resolved the conflict by substituting a third number that measures something else, without flagging that its sources disagreed. Separately, edgecases F1 proved BOTH failure directions ('the fenced link leaked (false red) and the unfenced one was swallowed (false green)'), and S2's title and problem statement carry only the false-green half. That direction is live in the real file, not just the synthetic repro: I measured lines 189, 190 and 223 of commit/SKILL.md as genuinely-fenced content that the shipped tracker feeds INTO both scans. Harmless today (line 190 is `git commit -F var/commit-msg.txt`, and `var/` is exempt anyway) but it is half of a confirmed finding, silently trimmed.

PROPOSED FIX
Restate S2's measurement as two numbers with the distinction made explicit: 76 non-blank lines blanked in total, of which 49 are over-blanked live prose that a list-marker-aware tracker would have scanned (192-193, 195-197, ... 256-258), and note that V9's 64 and V14's 52 differ because one counted all lines and the other non-blank only. Fix the range to 35-258. Add one clause to the problem statement recording the false-RED direction with its three real line numbers, since a fix that only addresses false-green would leave half the confirmed finding standing.
~~~

### [MINOR] Ledger integrity: the auditor's P5.2 'partial' was dropped, P6.1 is credited 'met' despite an unfulfillable 'Paste both' clause, and the merged P5.x IDs collide with the auditor's while meaning different criteria

~~~
location: merged report acceptance_ledger rows P5.1-P5.5 and P6.1; source criteria at requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md:362-363 and :404
confidence: high
category: dropped-signal

PROBLEM
Three defects in the merged ledger, all checkable against the plan text I read. (a) The auditor scored P5.2 — plan Phase 5 acceptance 2, `uv run pytest -m "not gamedata"` green "and the tally is recorded" — as PARTIAL, explicitly because the tally is recorded nowhere. The merged ledger has no row for that criterion at all; the green half is absorbed into P3.1 and the recorded half into S1, so a stated 'partial' left the ledger without a verdict. (b) Plan Phase 6 acceptance 1 (:404) reads "The widened test goes RED naming plan_panel.js:147, then green after step 3. **Paste both.**" The merged P6.1 is scored MET on reviewers having re-derived the RED from HEAD blobs — but the paste obligation lands in the IMPLEMENTATION_REPORT that does not exist, so the criterion is at best partial. The same pattern would apply to any acceptance item whose text carries a recording obligation. (c) The merged report renumbers Phase 5 rows so that merged P5.2 ('prove the guards bite') is the auditor's P5.3/P5.4, and merged P5.3 ('step 7') is the auditor's P5.7. Anyone reconciling the merged ledger against the two source ledgers by ID gets silently mismatched rows.

PROPOSED FIX
Restore a row for plan Phase 5 acceptance 2 at 'partial', citing the auditor's evidence verbatim. Re-score P6.1 as 'partial' with the reason stated (the RED was re-derived by reviewers; the paste obligation depends on the missing report) rather than met, or add a one-line convention at the top of the ledger saying that record-keeping halves of acceptance items are scored once, under U4/P7.1, and are not re-counted per row. Renumber the merged Phase 5 rows to P5a/P5b/... or carry an explicit `merged_from` crosswalk per row, as the confirmed_findings list already does for findings.
~~~

### [MINOR] COVERAGE GAP: nobody in either ledger checked that the untracked Phase 5 repro module must be staged, yet P5.1 is scored 'met' on a file that is not in git

~~~
location: tests/test_doc_link_contract.py (untracked, `??` in git status); .github/workflows/ci.yml:20 (actions/checkout@v7) and :57 (uv run pytest -m "not gamedata")
confidence: high
category: coverage-gap

PROBLEM
Six lenses, the auditor and the independent verifier all observed that tests/test_doc_link_contract.py is untracked — but every one of them treated it as a footnote about tests/test_no_leaks.py's `git ls-files` blindness. Nobody asked the consequential question. I checked the CI workflow myself: :20 is `actions/checkout@v7` and :57 is `uv run pytest -m "not gamedata"`, so CI sees TRACKED files only. If /commit's deliberate staging (the skill explicitly refuses a blind `git add -A`) misses an untracked new file, all 14 Phase 5 contract tests silently never run in CI, and tests/test_doc_links.py's four newly extracted helpers — strip_fences, link_targets, resolve_target, bare_request_tokens — ship with zero enforced coverage. That is the same 'a check nobody is forced to run' failure class as the request itself. The merged ledger nonetheless scores P5.1 ('the Phase 5 repro goes from RED to green') as MET, and §4 channel 3 of the plan (:518-520) asserts these Python guards 'run on every PR' — a claim that is false for this module until it is added. This is a genuine gap, not a restatement: it appears in no lens finding, no ledger row from either ledger, and no gated decision.

PROPOSED FIX
Add a ledger caveat to P5.1 and a nit-severity S-finding: tests/test_doc_link_contract.py is untracked, so P5.1 is met in the working tree only; explicitly instruct /commit to stage it by name, and note that after staging tests/test_no_leaks.py will finally see it (the by-hand PATTERNS probe both ledgers ran becomes the automated check). Optionally add to the plan's §7 checklist that a new test module counts as landed only once `git ls-files` returns it.
~~~

### [MINOR] VERDICT HONESTY: the rationale undercounts its own unmet rows and claims 'every phase's code landed' while S5 establishes Phase 5's fifth promise did not

~~~
location: merged report verdict_rationale, against its own acceptance_ledger rows U4, P1.4, P7.1, P7.2, P7.5, P8.2
confidence: high
category: verdict-honesty

PROBLEM
The 'fix' verdict is CORRECT and I am not challenging it — four-plus criteria are measurably unmet, the work is on-plan and the remainder is bounded. Two statements inside the rationale are not accurate against the report's own ledger, which matters because the rationale is the paragraph an operator reads instead of the ledger. (a) It says 'four upstream/plan acceptance criteria are measurably UNMET' and then names five things (U4, P7.1, P7.2, Phase 7 step 6, P8.2), while the ledger actually carries SIX rows with verdict 'unmet': U4, P1.4 (phase isolation), P7.1, P7.2, P7.5 (the D5 intake), P8.2. P1.4 and P7.5 are omitted from the count and the enumeration both. (b) It asserts 'every phase's code landed' as part of the not-no-go argument, one paragraph after the same report's S5 establishes that Phase 5 shipped four of five documented promises and P5.4 is scored partial for exactly that reason. Both are the kind of rounding that turns a 'fix' into a 'go' at the next handoff.

PROPOSED FIX
Change 'four' to 'six' and enumerate all six unmet row ids inline. Replace 'every phase's code landed' with the accurate form: 'every phase's code landed except Phase 5's fifth documented promise (S5), and Phase 7 landed only its memory append.' No change to the verdict word itself.
~~~

### [NIT] P7.3 is scored 'met' against a criterion whose text says ONE appended memory entry when three landed

~~~
location: merged report acceptance_ledger P7.3; .claude/agents/data-engineer-memory.md:290-313 (+24 lines, three dated entries)
confidence: high
category: quiet-upgrade

PROBLEM
The merged criterion is written as 'Phase 7 step 5: ONE dated agent-memory entry is APPENDED (never edited, never pruned), carries an epistemic label, and is narrowed per D4' and is scored MET. Three entries were appended. The deviation is disclosed — but only in the `reconciliation` field, not in the `evidence` field and not in the verdict word, and the merged report elsewhere holds itself to the standard that a criterion's literal text governs (it downgraded P1.4 to unmet on exactly that reasoning). I agree with the substance of keeping all three: the diff is pure append at EOF, all three carry labels, test_memory_entries_carry_an_epistemic_label passes, and D4 is honoured. The issue is only that a numeric criterion was scored met against a different number.

PROPOSED FIX
Score P7.3 'met with deviation' (or split: 'appended, labelled, D4-narrowed' met; 'exactly one entry' deviated) and move the three-entries fact from `reconciliation` into `evidence`, where a reader scanning verdicts will see it. The existing gated decision recommending the entries be kept is right and needs no change.
~~~

### [NIT] Consensus inflation: the merged report cites 'raised by all six lenses' as corroborative weight for findings six lenses reached by running the same one-line command, while the genuinely lens-specific findings each had a single source

~~~
location: merged report confirmed_findings S1 ("five lenses raised this") and S4 ("Raised by all six lenses"), against S5 (skill-quality only) and S8 (correctness only)
confidence: medium
category: panel-design

PROBLEM
S1 and S4 are cited with head-count as evidence strength. But S1 is reachable by `git status --porcelain -- requests/` and S4 by one probe of bare_request_tokens — every lens found them because they are the two most visible facts in the tree, not because six independent methods converged. Meanwhile the two findings that required actual lens-specific insight each came from exactly one reviewer: S5 (the fifth 'link titles' promise, which required noticing that Phase 5 step 8 pointed the implementer at make-feature-request/SKILL.md:245-250, the ONE copy of five that omits the clause) came only from skill-quality, and S8 (the unreachable placeholder filter making a named unit test pass for the wrong reason) came only from correctness. The dropped edgecases F5 (M1 above) was likewise single-sourced. The pattern is that single-sourced findings are the ones at risk of being lost or under-weighted, and one of the three already was. This does not change any verdict; it is a note about how the panel's budget was spent and how the merge should weight head-count.

PROPOSED FIX
Stop using reviewer head-count as an evidence qualifier in the merged report — replace 'raised by all six lenses' with the method that established it ('confirmed by `git status --porcelain -- requests/`, reproduced independently'). Add a merge-time rule that a finding raised by exactly ONE lens gets an explicit keep/drop disposition with a reason, which is the check that would have caught M1 before the report shipped.
~~~

## Low-severity findings (32)

### [MINOR] Nine /commit-gated phases were collapsed into one uncommitted blob, making every per-phase delta criterion permanently unverifiable

~~~
location: requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md:84
confidence: high
category: process

PROBLEM
`git log --oneline` shows HEAD = a656acb 'Plan the ported-guard repair' with all 13 modified files plus one untracked file sitting uncommitted. The plan required each phase to end at a /commit-gated checkpoint (:84) and stated that 'Phases 1 and 3 must not be merged or reordered — Phase 1's acceptance is that exactly one of the two red tests flips, which is the proof the fixture fix and the reference fix are independent' (:86-87). With no intermediate commits, P1.3 (`1 failed, 171 passed, 62 deselected`), P1.4 ('exactly one file in git diff --stat') and P3.5 ('seven files changed') can never be checked, and the independence proof was never taken. I could only re-derive independence structurally (the fixture test at tests/test_skill_references.py:103-112 reads only the .mjs + panel, and `git grep -n 'test_request_links' HEAD -- '.claude/skills/*.md'` confirms all 7 dead references were still present at HEAD).

PROPOSED FIX
This cannot be undone without rewriting the tree, which is out of bounds here. Record it honestly in the IMPLEMENTATION_REPORT: state that the phases were executed as one unit, name the three per-phase criteria that were therefore not measured, and paste the structural independence evidence above in their place. If the operator wants the checkpoints restored, the diff can be split into per-phase commits by path before pushing — Phase 1/2 are confined to verify_batching_guard.mjs, Phase 3/4 to the six SKILL.md files plus test_skill_references.py's docstrings, Phase 5 to the two test modules, Phase 6 to the two panel .js files plus test_skill_references.py, Phase 8 to ci.yml.
~~~

### [MINOR] scope_panel.js was changed although it is not on the plan's files-to-touch checklist, and the deviation is recorded nowhere

~~~
location: .claude/skills/scope-feature/scope_panel.js:125
confidence: high
category: scope-deviation

PROBLEM
The Phase 6 checklist (IMPLEMENTATION_PLAN.md:599) names only `.claude/skills/create-implementation-plan/plan_panel.js — :147 phantom doc`. The diff also rewrites scope_panel.js:125 and a second site at plan_panel.js:164. My scratchpad probe over the HEAD copies confirms all three were genuine instances of the same phantom `docs/data-sources.md` (plan_panel.js:147, :164, scope_panel.js:125) that the widened guard correctly found, so the fixes are right on the merits. The problem is purely that a reviewer of the commit has nowhere to read why a file outside the checklist changed — and with no IMPLEMENTATION_REPORT (F1) there is no record at all. The .claude/agents/data-engineer-memory.md:302-307 entry mentions 'three references' but does not name the extra file.

PROPOSED FIX
Name the deviation in the IMPLEMENTATION_REPORT: the widened Phase 6 guard found three instances rather than the one the plan cited, list all three file:line sites, and note that the plan's checklist was under-specified rather than that the implementation over-reached. Also note in the /commit message body that scope_panel.js is a Phase 6 sibling fix.
~~~

### [MINOR] The RCA's red-repro test was renamed, so the identifier the upstream artifact and any external selector cite no longer exists

~~~
location: tests/test_skill_references.py:78
confidence: high
category: traceability

PROBLEM
`test_every_test_file_a_skill_names_exists` became `test_every_repo_path_a_skill_names_exists`. The RCA's Reproduction section (ROOT_CAUSE_ANALYSIS.md:38) and the plan's Phase 1 acceptance item 3 (IMPLEMENTATION_PLAN.md:160) both name the old identifier, and the plan authorised widening the regex (Phase 6 step 2) but never a rename. Anyone running `uv run pytest tests/test_skill_references.py::test_every_test_file_a_skill_names_exists` from the RCA now gets an empty-selection error rather than a pass. The rename is defensible — the test no longer covers only test files — but it silently breaks the trace from the decided upstream artifact to the guard that proves it fixed.

PROPOSED FIX
Keep the new name (it is more accurate) and close the trace in the IMPLEMENTATION_REPORT: state the old -> new identifier explicitly next to the 'red repro now green' row, so a reader following the RCA's selector finds the redirect. No code change needed.
~~~

### [MINOR] The batching guard's header still says it pins "four properties" while now listing five

~~~
location: .claude/skills/implement-plan/tests/verify_batching_guard.mjs:8
confidence: high
category: stale-comment-drift

PROBLEM
Phase 2 step 8 said to "Extend the header block (`:1-27`) with a fifth pinned property", and the implementation correctly added item 5 (FIXTURE/ROSTER AGREEMENT) at `:25-29`. But `:8-9` still reads "this guard pins the **four** properties that make it safe to trade agents for batches:" immediately above a list numbered 1 through 5. `git grep -n 'four properties' -- .claude/skills/implement-plan/tests/verify_batching_guard.mjs` returns `:8`. This is the same stale-teaching-comment defect Phase 1 step 6 existed to fix at `:150`, left behind in the file whose entire purpose in this request is to stop describing a repo it does not live in. No test can see it, exactly as Phase 1 acceptance #5 warned about prose.

PROPOSED FIX
Change `:8` from "pins the four properties" to "pins the five properties". While there, reflow the item-1 sentence: the inserted clause left "collapse to <= cap batch agents, the" stranded on `:13` mid-thought.
~~~

### [MINOR] strip_fences desyncs on a fence opened on a list-item line, silently blanking 35 lines and the whole tail of a document

~~~
location: tests/test_doc_links.py:25 (`FENCE`) and :42 (`strip_fences`), triggered by .claude/skills/commit/SKILL.md:189
confidence: high
category: correctness-silent-exemption

PROBLEM
`FENCE = re.compile(r"^\s*(?:>\s*)*(`{3,}|~{3,})")` requires the marker at line start (optionally indented/blockquoted). `.claude/skills/commit/SKILL.md:189` opens a fence on a numbered-list line — `2. ```` — which FENCE does not match, so the opener is missed and the CLOSER at `:191` (`   ```` ) is read as an opener. I instrumented the real state machine: the file ends with an unclosed fence, `:191-222` is blanked, and `:224` re-opens with nothing to close it so `:224-258` is blanked too. Today the damage is nil — I diffed old-logic vs new-logic coverage repo-wide (394 -> 393 targets checked; the single loss is an unrelated `..` target genuinely inside a fence in `requests/feature-requests/first-sight/reviews/plan-proposals.md`) — but the mechanism is a silent exemption of ~65 lines of a live skill document, and any future link or `requests/` token added there is invisible to both scanners. This is the vacuous-pass shape the plan repeatedly names (Phase 2 acceptance #2, Phase 8 step 5) and Risk row 3 flagged fence handling specifically.

PROPOSED FIX
Two cheap fixes, both in `tests/test_doc_links.py`: (1) allow an ordered/unordered list marker before the fence in `FENCE`, e.g. `^\s*(?:>\s*)*(?:(?:[-*+]|\d+[.)])\s+)?(`{3,}|~{3,})`; (2) make `strip_fences` (or the repo-wide test) report a file that reaches EOF with a fence still open, so a desync surfaces as a named failure rather than as a quietly exempted tail. Add a fixture-string case to `tests/test_doc_link_contract.py` for the list-item fence.
~~~

### [MINOR] scannable_text's fixture carve silently drops the rest of the file if its closing delimiter is ever absent

~~~
location: tests/test_skill_references.py:74 (`fixture, _, tail = rest.partition("\n}\n")`)
confidence: medium
category: fragile-carve

PROBLEM
Phase 6 step 5 asked to exclude the batching guard's synthetic fixture locations, and the implementation blanks the `const FINDINGS_BY_LENS = { … }` block. `str.partition` returns `(rest, '', '')` when the separator is not found, so if the fixture's column-0 closing `}` is ever reflowed, indented, or given a trailing comment, `tail` becomes empty and **every line after the marker silently leaves the scan** — a guard that quietly stops checking the file it was widened to police. I verified the current happy path is correct (331 raw lines -> 331 scannable lines, `RUN: node` preserved, `test_extract_client` blanked), so this is latent, not live. It is the same `|| []`-shaped silent swallow the RCA identified as the reason this whole defect went unnoticed, reintroduced in the guard's own helper.

PROPOSED FIX
Assert the delimiter was found before rebuilding, e.g. `assert sep, f"{path}: FINDINGS_BY_LENS block has no column-0 closing brace — the carve is stale"` using `fixture, sep, tail = rest.partition("\n}\n")`, so a reflowed fixture fails loudly instead of shrinking the scan.
~~~

### [MINOR] Two files were edited that the plan's files-to-touch checklist never lists, and three memory entries were appended where Phase 7 said one

~~~
location: .claude/skills/scope-feature/scope_panel.js:122; .claude/skills/create-implementation-plan/plan_panel.js:164 (PLANNER 2 mandate); .claude/agents/data-engineer-memory.md:290-313
confidence: high
category: plan-deviation-unrecorded

PROBLEM
The plan's §7 checklist names only `.claude/skills/create-implementation-plan/plan_panel.js` — `:147` phantom doc (Phase 6). The diff also changes `scope_panel.js:122` and plan_panel.js's PLANNER 2 mandate string. Both are COMPELLED, not gratuitous: Phase 6 widened `skill_documents()` to `*.js`/`*.mjs` and `REPO_REFERENCE` to `docs/*.md`, and all three sites cited the phantom `docs/data-sources.md`, so the widened test stays red without them — `git grep data-sources -- .claude/` now returns zero hits and the suite is green. So this is a gap in the plan's checklist rather than implement-time scope creep, and the sentence-level correction Phase 6 step 3 demanded ("Correct the sentence, not just the filename") was done at all three. Separately, Phase 7 step 5 says "Append — never edit, never prune — **one** dated entry"; three were appended (`:290`, `:302`, `:308`). The two extras are honest, in-shape (`test_memory_entries_carry_an_epistemic_label` passes) and append-only, and D4's narrowing is respected — the correction entry explicitly says the `nba2k-rpg` measurement "stands and was not re-tested here". None of this is wrong; all of it is unrecorded, because F1 means there is no IMPLEMENTATION_REPORT to record it in.

PROPOSED FIX
No code change. Record both deviations in the IMPLEMENTATION_REPORT from F1: that the Phase 6 widening compelled two sites beyond the checklist (with the zero-hit grep as evidence), and that two extra memory entries were appended beyond Phase 7's single mandated correction, with their epistemic labels and why each was worth a line.
~~~

### [MINOR] Phase 8's two non-negotiable acceptance items — the in-CI red demonstration and the recorded node version + run URL — are unmet and unrecorded

~~~
location: .github/workflows/ci.yml:34-38 and :70-78; requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md:493-502 (§5)
confidence: high
category: unverified-acceptance

PROBLEM
The step itself is built correctly and matches every structural instruction: `actions/setup-node@v4` pinned to 22 (step 1), `node --version` kept anyway (step 2), added to the existing `quality` job rather than a new one (step 3), display name at `:16-17` untouched and `ops/branch-protection.json` unchanged in `git status` (steps 3-4), five explicit paths with `set -euo pipefail` and no glob (step 5), no secret or absolute path (acceptance 4). I confirmed all five guards exit 0 locally. But Phase 8 acceptance #1 wants "A CI run log … Paste it with the run URL" and acceptance #2 wants the step proved non-vacuous **in CI** — "A local shell demonstration cannot catch a YAML-level swallowed exit code, which is the failure mode `acceptance_panel.js:201` item 4 names." Nothing is committed or pushed, so no run exists; and step 2's instruction to "Record the first observed value in §5 with an epistemic label — `measured <date>`, with the run URL" left §5 (`IMPLEMENTATION_PLAN.md:530-574`) unchanged. This is inherently deferrable — the plan says Phase 8 is ordered last and may split into a follow-up PR — but it must be stated, not inherited silently, or the request closes claiming a CI gate nobody has watched fail.

PROPOSED FIX
On the PR: capture the `Lint, types, tests` log showing the guards step naming all five files at exit 0 and paste it with the URL; then push one commit that re-keys a single `FINDINGS_BY_LENS` entry, confirm the check goes red naming the guard, and revert. Record the observed node version in the plan's §5 as `measured 2026-08-__` with the run URL. If the operator prefers to split Phase 8 into a follow-up PR, say so explicitly in the IMPLEMENTATION_REPORT under "what this does not close", alongside the D5 intake.
~~~

### [MINOR] Unreachable placeholder/glob filter, and a unit test that passes for a different reason than it documents

~~~
location: tests/test_doc_links.py:129
confidence: high
category: dead-code

PROBLEM
`if "*" in token or "<" in token or ">" in token: continue` can never fire: BARE_REQUEST_TOKEN (`:35`) has character class `[A-Za-z0-9._/-]` and a final class of `[A-Za-z0-9_/]`, so no emitted token can contain `*`, `<` or `>`. Measured: `BARE_REQUEST_TOKEN.findall("requests/<track>-requests/<slug>/")` == `[]` and `findall("requests/bugfix-requests/*/BUGFIX_REQUEST.md")` == `['requests/bugfix-requests/']`. Consequently `test_a_templated_or_globbed_token_is_not_a_dead_pointer` (tests/test_doc_link_contract.py:135) is green because the regex truncates, not because the filter exempts — a vacuously-passing check of the exact kind acceptance_panel.js item 4 names as worse than none. The truncation also has a real user-visible effect: a templated path under a dead prefix reports the confusing stub `requests/no-such-track/` rather than the path the author wrote (measured).

PROPOSED FIX
Either delete the unreachable branch and rewrite the unit test to assert the real behaviour (a templated/globbed path yields no dead report because the token truncates at the placeholder, and the truncated prefix is checked instead), or widen BARE_REQUEST_TOKEN to admit `*`/`<`/`>` inside the token so the filter becomes live and the reported token matches what the author actually wrote. Do not leave a test whose name claims a rule the code does not implement.
~~~

### [MINOR] The synthetic-fixture exemption blanks only the declaration, while the same fictional paths recur three lines later

~~~
location: tests/test_skill_references.py:60
confidence: high
category: maintainability

PROBLEM
`scannable_text` blanks the `const FINDINGS_BY_LENS = {` … `\n}\n` block only, and its docstring argues that 'blanking the block rather than exempting the file keeps the rest of that guard in scope'. But the same invented locations appear OUTSIDE that block: `verify_batching_guard.mjs:247` (`'src/ootp_ai/land/writer.py'`), `:248` (`'transform/models/silver/dim_player.sql'`) and `:262` repeat them as literals. I confirmed with a broadened pattern that those two dead paths are the only repo-path tokens in `.claude/skills/` that the shipped REPO_REFERENCE does not currently catch. It is harmless today only because REPO_REFERENCE (`:38`) covers just `tests/test_*.py` and `docs/*.md` — and the one `tests/test_extract_client.py:9` literal happens to live inside the blanked block. The moment anyone widens the pattern to `src/` or `transform/` (the natural next hardening, and the appended memory entry celebrates exactly this kind of widening), the guard goes red on its own test data, inside the file it exists to police.

PROPOSED FIX
Blank the synthetic locations wherever they occur rather than by block position — e.g. derive the fixture's `loc` strings once and blank every occurrence of each in that file, or move the scenario-1 assertions to compare against constants derived from FINDINGS_BY_LENS instead of repeating the literal paths at :247/:248/:262. Add an in-file comment saying which exemption covers which site, so a later reader can tell an exemption from an oversight (Phase 6 acceptance 3).
~~~

### [MINOR] The bare-token scan's own-directory exemption is broad enough to swallow a typo'd or wrong-track sibling artifact

~~~
location: tests/test_doc_links.py:126 and :134
confidence: high
category: correctness

PROBLEM
`bare_request_tokens` skips any dead token whose `target.parent == own_dir`, on the rationale that a plan may list the report its next stage will write. The exemption is keyed on the *directory* only, never on the filename, so any misspelling of a sibling artifact is invisible. Verified against the real plan file: `bare_request_tokens('see requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYIS.md and requests/bugfix-requests/verify-batching-guard-red-on-arrival/PROJECT_SCOPE.md', source=<that plan>)` returns `[]` — a typo'd RCA name and a feature-track artifact in a bugfix directory both pass.

A typo'd pointer to a document that DOES exist under another spelling is precisely the "dead pointer misleading the next stage" this capability was added to catch (plan `:352`), and the exemption is load-bearing for exactly one real token in the whole repo: I re-ran the scan with `source=None` and the only suppressed finding is `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`. Plan Phase 5 step 7 warned against widening the scan to make the repo pass; one token bought a general hole.

tests/test_doc_link_contract.py:149 pins the exemption but only with the benign case (`IMPLEMENTATION_REPORT.md`); nothing tests that a misspelling in the same directory is still caught.

PROPOSED FIX
Narrow the exemption from "any file in my own directory" to "a stage deliverable my own stage has not written yet" — a small allow-set such as `{"IMPLEMENTATION_REPORT.md", "IMPLEMENTATION_PLAN.md", "PROJECT_SCOPE.md", "ROOT_CAUSE_ANALYSIS.md"}` intersected with the track's own artifact names, so an unrecognised filename in the same directory is still reported. Then add the negative test: a token naming `ROOT_CAUSE_ANALYIS.md` in the document's own directory must come back dead.
~~~

### [MINOR] The new orphaned-lens check in the batching guard has no automated regression test — its correctness rests on a manual demonstration

~~~
location: .claude/skills/implement-plan/tests/verify_batching_guard.mjs:200-224
confidence: high
category: test-coverage

PROBLEM
The check is inert on a correct tree by design, so nothing in `uv run pytest` or in the new CI step exercises the branch that fires. `tests/test_skill_references.py::test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` asserts the *fixture keys* are panel lenses; it never runs the `.mjs` check itself, and it is explicitly one-directional (`:122-124`), so it cannot see the `builder:` case — a key the panel defines but this run's `touchedAreas` never requests.

I verified the check does bite, on all three variants, by scratch-copying the guard and re-breaking one key at a time (results in the summary above). But that verification lives nowhere in the repo: if a later edit reorders the check after the counting assertions, or moves it out of Scenario 1's block where `calls` is populated, every guard run stays green and nothing notices. That is the same "a check nobody is forced to run" argument the CI step's own comment makes.

PROPOSED FIX
Add one pytest to tests/test_skill_references.py that does what I did by hand: read `verify_batching_guard.mjs`, rewrite `PANEL` to the tracked `acceptance_panel.js` absolute path derived from `REPO_ROOT`, substitute one fixture key for `builder`, write to `tmp_path`, run it via `subprocess.run(["node", ...])`, and assert returncode == 1, that the stdout contains `orphaned lens 'builder'`, and that `[cap+dedupe]` is absent. Skip it if `shutil.which("node")` is None so the Python-only path stays green. Build the temp path from `tmp_path`, never a literal, so tests/test_no_leaks.py stays clean.
~~~

### [MINOR] The bare-token scan gained an own-directory exemption that is not in the plan and hides a typo'd sibling artifact name

~~~
location: tests/test_doc_links.py:126 and :134 (`own_dir = source.parent.resolve()` / `if own_dir is not None and target.parent == own_dir: continue`)
confidence: high
category: guard-strength

PROBLEM
Plan Phase 5 step 7 is explicit: 'A token that is genuinely dead gets fixed; a token that is a deliberate template placeholder gets the angle-bracket treatment … Do not weaken the scan to make the repo pass.' The implementation instead added a third disposition — any `requests/...` token whose parent directory equals the scanning document's own directory is skipped. I measured its blast radius by running the scan with and without `source=`: it suppresses exactly one token today (`requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`), so nothing real is hidden right now. But the exemption is unbounded by filename: a plan citing its own `ROOT_CAUSE_ANALYIS.md` (typo) or `PROJECT_SCOPE.MD` goes unreported forever, and a request directory is the highest-traffic place a dead cross-reference actually occurs. It also currently exempts this very plan's missing `IMPLEMENTATION_REPORT.md` (F1), meaning the guard cannot notice that the report was never written.

PROPOSED FIX
Narrow the exemption to the pipeline's known stage outputs rather than any sibling path: skip only when `target.parent == own_dir` AND `target.name` is in a small frozenset (`IMPLEMENTATION_PLAN.md`, `IMPLEMENTATION_REPORT.md`, `PROJECT_SCOPE.md`, `ROOT_CAUSE_ANALYSIS.md`, `FEATURE_REQUEST.md`, `BUGFIX_REQUEST.md`), with the existing comment kept. Add a contract test that a misspelled sibling (`ROOT_CAUSE_ANALYIS.md`) in the document's own directory IS still reported — the negative case the current suite lacks.
~~~

### [MINOR] Phase 8's non-vacuity proof is unperformed and unrecordable — the CI step has never run

~~~
location: .github/workflows/ci.yml:70-78 (`Skill guards (node)`), against IMPLEMENTATION_PLAN.md:493-499
confidence: high
category: verification-gap

PROBLEM
The step itself is correctly built — added to the existing `quality` job rather than a new one (so `ops/branch-protection.json` stays valid, and it is byte-unchanged in `git status`), explicit paths not a glob, `set -euo pipefail`, `node --version` first, `actions/setup-node@v4` pinned at node 22. I confirmed all five named guards exist and exit 0 locally. But Phase 8 acceptance 1 demands 'A CI run log showing the guards step naming all five files and exiting 0 … Paste it with the run URL' and acceptance 2 demands an IN-CI red demonstration ('A local shell demonstration cannot catch a YAML-level swallowed exit code'), plus step 2 requires recording the observed node version in the plan's §5 with a `measured <date>` label and run URL. None of that exists: nothing is committed or pushed, and the plan file is unmodified. The step is currently reasoned-correct, not proven-correct — which is the precise distinction this whole request is about.

PROPOSED FIX
Treat Phase 8 as open. After the branch is pushed and CI is green, paste the guards-step log (with `node --version` output and all five paths) plus the run URL into the IMPLEMENTATION_REPORT and into the plan's §5 D2 with a `measured 2026-08-17` label; then push one commit re-keying a single fixture entry, confirm `Lint, types, tests` goes red naming `verify_batching_guard.mjs`, and revert. Or split Phase 8 into a follow-up PR as IMPLEMENTATION_PLAN.md:471 explicitly permits, and say so in the report.
~~~

### [MINOR] implement-plan/SKILL.md's self-verification bullet still describes a four-property guard that now pins five

~~~
location: .claude/skills/implement-plan/SKILL.md:309
confidence: high
category: skill-description-drift

PROBLEM
The bullet reads: 'exit 0 = the Verify phase stays under its cap, merges only true duplicates, groups findings by location, adjudicates each against its own id, and degrades honestly when a batch dies or rubber-stamps · … Run it whenever `acceptance_panel.js` or this file changes.' The guard's own header at verify_batching_guard.mjs:25-29 now declares a FIFTH pinned property (FIXTURE/ROSTER AGREEMENT), and the guard's most likely failure mode from today onward is an orphaned fixture key — a failure the SKILL.md's enumerated exit-0 meaning does not cover, so a reader who hits it will look for a batching bug that isn't there. The trigger clause is also now wrong in two directions: the guard must be run when its own fixture changes (not just when `acceptance_panel.js` or SKILL.md change), and as of ci.yml:70 CI runs it on every PR, which is worth telling the agent so it stops reading a red guard as pre-existing noise.

PROPOSED FIX
At .claude/skills/implement-plan/SKILL.md:309, add the fifth property to the exit-0 sentence ('…and its fixture names only lenses the panel actually requests') and change the trailing sentence to 'Run it whenever `acceptance_panel.js`, this file, or the guard's own fixture changes — CI runs all five skill guards on every PR (`.github/workflows/ci.yml`).'
~~~

### [MINOR] The bare-token scan gained a fifth exemption the four promises do not contain, and it is the one that would hide this very plan's missing report

~~~
location: tests/test_doc_links.py:126
confidence: high
category: guard-scope

PROBLEM
`bare_request_tokens` takes a `source` argument and skips any dead token whose parent directory equals the pointing document's own directory (`if own_dir is not None and target.parent == own_dir: continue`). That is a fifth rule; the module docstring and `tests/test_doc_link_contract.py:8-12` enumerate exactly four promises (fenced content, `file.py:123` suffixes, `var/` targets, bare-token resolution), and Phase 5 step 7 prescribed a different remedy for this case — 'a token that is a deliberate template placeholder gets the angle-bracket treatment already exempted at `:28`'. I measured its blast radius across the whole tree: it suppresses exactly ONE token today, `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`. So a one-line angle-bracket or fence edit to that single plan would have kept the guard at exactly the four documented promises. The cost of keeping it is real and slightly ironic: the scan is now permanently blind to a dead pointer inside a document's own request directory — which is exactly where F2's missing `IMPLEMENTATION_REPORT.md` would have been noticed. The rule is well-commented (`:118-124`) and covered by two tests (`test_doc_link_contract.py:149,161`), so this is a judgment call to record rather than a defect, but it is a deviation from a decided plan step and it widens a guard beyond what any skill documents.

PROPOSED FIX
Either (a) drop the `source`/`own_dir` parameter and fence or angle-bracket the single occurrence in `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md`, restoring the guard to the four promises exactly; or (b) keep it and make it documented rather than invisible — add the fifth rule to the 'What good looks like' bullet in the five skills so authors know it exists, and narrow it to filenames the pipeline actually creates (IMPLEMENTATION_REPORT.md, IMPLEMENTATION_PLAN.md, PROJECT_SCOPE.md, ROOT_CAUSE_ANALYSIS.md) rather than any path in the directory.
~~~

### [MINOR] The batching guard's header still says 'the four properties' while listing five

~~~
location: .claude/skills/implement-plan/tests/verify_batching_guard.mjs:8
confidence: high
category: doc-drift

PROBLEM
Line 8 reads 'this guard pins the four properties that make it safe to trade agents for batches:' and is immediately followed by numbered items 1 through 5, because Phase 2 step 8 added the FIXTURE/ROSTER AGREEMENT property at `:25-29` without updating the count. This is a stale count in a comment, in the exact file whose entire reason for existing in this request is that a stale comment at `:150` ('-> data-contract + extraction + skill-quality specialists') taught the wrong roster for the guard's whole life. No test can see it — the plan called this out at Phase 1 acceptance 5 precisely because prose drift is invisible to CI. The `:150` comment itself WAS correctly updated to '-> warehouse + parser + skill-quality specialists' and `git grep -E 'data-contract|extraction' -- .claude/skills/implement-plan/` returns zero hits, so this is the one survivor of the same class.

PROPOSED FIX
Change `:8` to 'this guard pins the five properties that make it safe to trade agents for batches:'. While there, confirm the header's neighbouring claim stays true: `:11-13` now correctly reads '6 finding-emitting lenses of this run's 7-lens roster', which I verified against the live run — the panel requested acceptance, correctness, edgecases, fidelity, parser, skill-quality, warehouse (7), and the fixture stocks 6 of them.
~~~

### [MINOR] Phase 8's mandatory in-CI non-vacuity demonstration has not been performed and cannot have been — no run exists

~~~
location: .github/workflows/ci.yml:70-78
confidence: high
category: ci-integrity

PROBLEM
Phase 8 acceptance 1-2 (IMPLEMENTATION_PLAN.md:494-499) require a pasted CI run log naming all five guards inside the `Lint, types, tests` job, and then a pushed commit that re-keys one fixture entry to watch the check go RED — explicitly "IN CI, not just locally", because "a local shell demonstration cannot catch a YAML-level swallowed exit code". The whole change is uncommitted (`git status --porcelain` shows 13 modified + 1 untracked, nothing staged), so no run URL can exist and no such evidence is recorded anywhere. I did what I could statically and it looks correct: the step is on the existing `quality` job (so `ops/branch-protection.json` needs no change and is byte-unchanged), it is a `run: |` block opening `set -euo pipefail` under GitHub's default `bash -e`, every guard is a literal explicit path rather than a glob, all five paths are tracked (confirmed via `git ls-files`), there is no `continue-on-error` and no `if:`, and I verified locally that each of the five exits 0 and that a corrupted verify_batching_guard.mjs exits 1. The residual risk is small but is exactly the one the plan refused to accept on faith.

PROPOSED FIX
Treat Phase 8 as open until the evidence exists. After the PR is up and the job is green, push one throwaway commit that changes `warehouse:` back to `'data-contract':` at verify_batching_guard.mjs:61, confirm the `Lint, types, tests` check goes red with the `fixture: ... orphaned lens ...` line in the `Skill guards (node)` step, revert, and paste the run URL and the log excerpt into the IMPLEMENTATION_REPORT from F1. If the operator would rather not spend a round trip on this PR, split the ci.yml hunk into a follow-up PR — the plan at IMPLEMENTATION_PLAN.md:469-471 already sanctions that — rather than landing an unproven gate.
~~~

### [MINOR] node and the five .mjs guards became a blocking CI gate, but neither ops/README.md's local toolchain nor README.md's setup mentions them

~~~
location: ops/README.md:26-34
confidence: high
category: doc-drift

PROBLEM
ops/README.md's "Local toolchain" block lists exactly `uv sync`, `cp .env.example .env`, `uv run pytest`, `uv run ruff check .`, `uv run mypy` — and README.md:96-102's Setup block lists `uv sync`, `cp .env.example .env`, `uv run pytest`. As of this diff, the required `Lint, types, tests` check also runs five node scripts (.github/workflows/ci.yml:70-78), so a contributor who runs the documented local gate to completion still cannot predict the check, and node is now an undocumented prerequisite for reproducing CI. I confirmed the gap mechanically: `git grep -n -i -E "node|npm|\.mjs" -- README.md ops/` returns nothing, and the repo carries no package.json, .nvmrc or .node-version to hint at it. This is the same shape as the defect being fixed — a documented contract that no longer describes the gate that actually runs — and it is squarely what /update-docs is supposed to catch, which has not run because nothing is committed yet.

PROPOSED FIX
Add to ops/README.md's Local toolchain block a line for the guards, e.g. `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs   # + the four sibling guards; also run in CI`, with a one-line note that node is required and that CI pins node 22 via actions/setup-node. Keep the PowerShell caveat the plan already established (IMPLEMENTATION_PLAN.md:585): locally these are five separate invocations each followed by a `$LASTEXITCODE` check, never a `&&` chain, which is a parser error in PowerShell 5.1.
~~~

### [NIT] REPO_REFERENCE's docs/ pattern excludes uppercase and underscores, so several real citation shapes stay invisible to the widened guard

~~~
location: tests/test_skill_references.py:38
confidence: high
category: coverage

PROBLEM
`docs/[a-z0-9/-]+\.md` matches only lowercase-hyphen paths. A skill citing `docs/data_access.md` (underscore), `docs/FRONT_OFFICE.md`, or the root-level `CLAUDE.md` / `FRONT_OFFICE.md` / `README.md` — all of which the skills reference constantly — would not be checked at all. The three phantom `docs/data-sources.md` instances happened to fit the narrow shape; the next drift may not. The plan asked for 'the repo-path shapes actually cited there (docs/*.md at minimum)' (IMPLEMENTATION_PLAN.md:389), so this satisfies the letter but leaves an obvious next gap.

PROPOSED FIX
Widen to `(?:tests/test_[a-z0-9_]+\.py|docs/[A-Za-z0-9_/-]+\.md|(?:CLAUDE|README|FRONT_OFFICE)\.md)` and re-run; if that surfaces new hits, treat each on its merits rather than narrowing back. Keep the existing datasets//build/ exclusion comment at :34-37 as-is.
~~~

### [NIT] tests/test_doc_link_contract.py imports its sibling as a bare top-level module, which no other test in the repo does

~~~
location: tests/test_doc_link_contract.py:23
confidence: medium
category: fragility

PROBLEM
`import test_doc_links as guard` works only because tests/ has no __init__.py (confirmed: Test-Path tests/__init__.py -> False) and pytest's default prepend import mode puts tests/ on sys.path; mypy resolves it the same way. Select-String across tests/*.py shows this is the ONLY sibling-module import in the suite. Adding tests/__init__.py, switching to importlib import mode, or running the module outside pytest's rootdir would all break collection with an ImportError that reads as a missing dependency rather than a layout assumption.

PROPOSED FIX
Either add a one-line comment at tests/test_doc_link_contract.py:23 recording the assumption ('tests/ has no __init__.py; pytest prepend mode and mypy both put this directory on the path'), or make it explicit with an importlib.util.spec_from_file_location load off REPO_ROOT/'tests'/'test_doc_links.py' as I did in my probe. The comment is sufficient; the point is that the next person moving test layout gets a warning rather than a puzzle.
~~~

### [NIT] The guard scans `_done/` artifacts although all five skills promise only live (non-`_done/`) bodies are scanned

~~~
location: tests/test_doc_links.py:139 (`markdown_files()`); promise text at .claude/skills/make-bugfix-request/SKILL.md:198 and its four siblings
confidence: high
category: promise-code-mismatch

PROBLEM
The promise prose Phase 5 was built to make true reads "A live (non-`_done/`) artifact body is scanned by `tests/test_doc_links.py`, a blocking CI check". `markdown_files()` filters only `.git` and `var`, so archived artifacts are in scope: I measured 82 markdown files scanned, 1 of them under `requests/feature-requests/_done/`. The new bare-token scan inherits this and now applies 209 token resolutions across that same set. It is harmless today (the suite is green) and the mismatch predates this change, but it is the one promise of the five that is still not true after the phase whose stated goal was to make them all true — and being stricter than documented is what turns a guard red on a correctly-archived artifact later, which is how a guard becomes something people step over.

PROPOSED FIX
Either exclude `_done` in `markdown_files()` alongside `.git` and `var` — one clause, with a comment citing the promise text — or, if scanning archives is deliberate, note in the module docstring that the guard is intentionally stricter than the prose and open a follow-up to reconcile the five skills' wording. Do not leave it undecided.
~~~

### [NIT] The re-grounded diagnose-bug example pairs a real test name with a failure message that does not match it

~~~
location: .claude/skills/diagnose-bug/SKILL.md:117
confidence: high
category: doc-correctness

PROBLEM
The replacement worked example cites `tests/test_parse_world.py::test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key` (verified real — tests/test_parse_world.py:179, and above the first `@pytest.mark.gamedata` at :513, so the template's `uv run pytest` invocation stays runnable, which is what the plan required) but pairs it with 'fails: expected 3058 calendar entries, got 2600'. That test asserts a column set and a key, not an entry count. A cold agent copies this template verbatim, so it teaches a red output that the named test could not produce — a smaller instance of the same 'artifact describes a repo that does not exist' drift this request is about.

PROPOSED FIX
Make the failure message match the assertion the named test actually makes, e.g. '(fails: expected 8 columns, got 7)' as the planning panel's own proposal suggested — or cite a different real test whose failure genuinely is an entry count.
~~~

### [NIT] The widened repo-path reference regex misses any docs/ filename with an underscore or an uppercase letter

~~~
location: tests/test_skill_references.py:38 (REPO_REFERENCE)
confidence: high
category: coverage

PROBLEM
`REPO_REFERENCE = re.compile(r"(?:tests/test_[a-z0-9_]+\.py|docs/[a-z0-9/-]+\.md)")`. Confirmed by running it: `docs/data-sources.md` matches, but `docs/data_access.md` and `docs/DATA-ACCESS.md` both return `[]`. The Phase 6 drift instance it was widened to catch (`plan_panel.js` citing a `docs/data-sources.md` that never existed) would have slipped through unnoticed had the phantom name carried an underscore. Every doc in the repo happens to be lowercase-hyphen today, so the guard is correct-by-luck rather than by construction, and the next hand-written citation is where luck runs out.

PROPOSED FIX
Broaden the docs alternative to `docs/[A-Za-z0-9_/-]+\.md` and add a one-line unit assertion (or extend the existing test's docstring with a fixture check) that `docs/data_access.md` is matched. The `datasets/` and `build/` exclusion is a separate concern and is already correctly documented in the comment above the pattern.
~~~

### [NIT] The bare-token scan covers `_done/` archives, which the promise text the skills now make true excludes

~~~
location: tests/test_doc_links.py:141-142 (markdown_files) vs .claude/skills/make-feature-request/SKILL.md:245-250
confidence: medium
category: consistency

PROBLEM
The five skills' "What good looks like" bullet — which Phase 5 exists to make literally true — scopes the check to "a live (non-`_done/`) artifact body". `markdown_files()` excludes only `.git` and `var`, so archived artifacts under `requests/feature-requests/_done/` are scanned too (1 file today). The scan is stricter than the promise, so it can only false-red, never false-green — but archiving a request moves its directory, and any frozen `requests/<old-path>/…` token inside an archived body becomes dead through no author's fault and turns CI red on history nobody may edit. The plan's Phase 5 step 7 anticipated dead tokens surfacing but assumed each would be fixable on its merits; a frozen archive is the case where it is not.

PROPOSED FIX
Either exclude `_done` from `markdown_files()` for the bare-token scan (keeping it in scope for the link scan, matching the promise text), or state in a comment that archives are deliberately in scope and accept that archiving requires a token sweep. Whichever way, add a line to the `test_bare_request_tokens_resolve` docstring saying which, so a future reader can tell an exemption from an oversight — the same standard Phase 6 step 3 held the other exclusions to.
~~~

### [NIT] Two files were edited that the plan's files-to-touch checklist does not list, and with no report the deviation is unrecorded

~~~
location: .claude/skills/scope-feature/scope_panel.js:125 and .claude/skills/create-implementation-plan/plan_panel.js:164, against IMPLEMENTATION_PLAN.md:592-609
confidence: high
category: traceability

PROBLEM
The plan's Phase 6 step 3 and checklist name exactly one site: `plan_panel.js:147`. The widened guard actually finds three — I confirmed by running the new `REPO_REFERENCE` scan over the HEAD blobs: `plan_panel.js:147 -> docs/data-sources.md`, `plan_panel.js:164 -> docs/data-sources.md`, `scope_panel.js:125 -> docs/data-sources.md`. All three were fixed, which is correct and in fact mandatory for Phase 6 acceptance 2 to pass. The problem is only bookkeeping: `scope-feature/scope_panel.js` appears in the diff but nowhere in the plan's §7 checklist, and because the IMPLEMENTATION_REPORT is missing (F1) there is no artifact anywhere reconciling the two. A later reader diffing checklist against diff sees an unexplained file.

PROPOSED FIX
Record it in the IMPLEMENTATION_REPORT: the widened guard found three instances of the phantom `docs/data-sources.md`, not the one the plan predicted, so `scope_panel.js` and a second `plan_panel.js` site were repaired under the same phase. Quote the guard's RED output naming all three as the justification. No code change needed.
~~~

### [NIT] strip_fences compares only the fence marker's first character, so a 4-backtick fence is closed early by an inner 3-backtick fence

~~~
location: tests/test_doc_links.py:25 (FENCE), :56 (`marker = hit.group(1)[0]`) and :61 (`hit.group(1)[0] == marker`)
confidence: medium
category: edge-case

PROBLEM
The regex captures the full run (`` `{3,} ``) but only `[0]` is retained and compared, so fence LENGTH is discarded. CommonMark requires a closing fence at least as long as the opener; here a ```` ```` ```` block would be terminated by the first inner ``` ``` ```, re-exposing the rest of the block to the link and bare-token scans. I checked the tree and there are currently zero 4+-backtick fences in any tracked Markdown file, so nothing is affected today. It matters because these very skills teach authors to write about fences ('Put either inside a fenced code block (``` or ~~~, blockquoted is fine)'), and the natural way to quote that guidance is a longer outer fence — which would then leak.

PROPOSED FIX
Store the whole marker run, not its first char: keep `marker = hit.group(1)` and close only when `hit.group(1)[0] == marker[0] and len(hit.group(1)) >= len(marker)`. Add one case to tests/test_doc_link_contract.py: a 4-backtick fence containing a 3-backtick fence and a dead link stays fully exempt.
~~~

### [NIT] scope_panel.js was changed but is not on the plan's files-to-touch checklist

~~~
location: .claude/skills/scope-feature/scope_panel.js:125
confidence: high
category: plan-fidelity

PROBLEM
The checklist at `IMPLEMENTATION_PLAN.md:599` names only `.claude/skills/create-implementation-plan/plan_panel.js` for the Phase 6 phantom-doc fix, but `git status --porcelain` shows `.claude/skills/scope-feature/scope_panel.js` modified too. This is correct work, not scope creep: I re-ran the widened `REPO_REFERENCE` detector against HEAD's content and it flags three sites, not one — `plan_panel.js:147`, `plan_panel.js:164` and `scope_panel.js:125`, all citing a `docs/data-sources.md` that has never existed here. The plan measured only the first, so the widened guard found two more, which is exactly what Phase 6 was for. The nit is bookkeeping: an out-of-checklist file in the diff is the shape a reviewer is trained to challenge, and the appended memory entry at `.claude/agents/data-engineer-memory.md:302` already records 'all three in one run' while the plan's checklist implies one.

PROPOSED FIX
Say so explicitly in the /commit message body and in the IMPLEMENTATION_REPORT: the widened guard found three instances of the phantom `docs/data-sources.md`, not the one the plan measured, so `scope_panel.js` joins the checklist. No code change needed — both replacement sentences correctly drop the false 'its contents are currently marked unconfirmed' claim in favour of the per-claim labelling that `docs/data-access.md` actually uses.
~~~

### [NIT] The RCA's named red-repro test was renamed, so the documented reproduction node-id no longer resolves

~~~
location: tests/test_skill_references.py:73 (test_every_repo_path_a_skill_names_exists)
confidence: high
category: traceability

PROBLEM
ROOT_CAUSE_ANALYSIS.md:38 pins the red repro by name as `test_every_test_file_a_skill_names_exists`, and IMPLEMENTATION_PLAN.md:161 refers to it by that name as the failure Phase 3 owns. Phase 6 widened it and renamed it to `test_every_repo_path_a_skill_names_exists`. The rename is defensible on the merits — the test now covers `docs/*.md` as well as `tests/test_*.py`, so the old name would itself be drift — but nothing in the tree records the renaming, so anyone replaying the RCA's repro by node id gets an `ERROR: not found` and has to guess a substitution. That is the identical failure mode the RCA describes at :39-46 for `tests/test_request_links.py`, and the plan itself warned about it in the risk row at :583.

PROPOSED FIX
Record the rename where the repro is defined and where it is cited: add one clause to the docstring at tests/test_skill_references.py:74-82 naming the previous test id, and note it in the IMPLEMENTATION_REPORT from F1. Do not rename the RCA's body — IMPLEMENTATION_PLAN.md:426 forbids revising a decided RCA.
~~~

### [NIT] implement-plan/SKILL.md's stated exit-0 contract still lists four pinned properties; the guard now pins five

~~~
location: .claude/skills/implement-plan/SKILL.md:309
confidence: high
category: doc-drift

PROBLEM
SKILL.md:309 defines what a green run means — "exit 0 = the Verify phase stays under its cap, merges only true duplicates, groups findings by location, adjudicates each against its own id, and degrades honestly when a batch dies or rubber-stamps". Phase 2 added a fifth pinned property to the guard and documented it in the guard's own header at verify_batching_guard.mjs:25-29 ("FIXTURE/ROSTER AGREEMENT"), but SKILL.md was not updated, so the skill's contract line under-describes what a red run can now mean. A reader who hits the new `fixture: ... orphaned lens ...` failure will not find that failure mode in the contract they were pointed at. This is small and the plan deliberately protected the adjacent `RUN:` line (Phase 2 step 8 forbids changing verify_batching_guard.mjs:33 because SKILL.md quotes it verbatim) — but it never forbade extending SKILL.md's prose, and CLAUDE.md's "single ownership" instinct argues the two should agree.

PROPOSED FIX
Extend .claude/skills/implement-plan/SKILL.md:309 with the fifth clause, e.g. "… degrades honestly when a batch dies or rubber-stamps, and its own fixture names only lenses the panel actually requests". Leave the `RUN:` line and the guard's :33 untouched.
~~~

### [QUESTION] Phase 8's in-CI non-vacuity demonstration has not happened and cannot be verified locally

~~~
location: .github/workflows/ci.yml:69
confidence: medium
category: verification-gap

PROBLEM
The new 'Skill guards (node)' step is well built — explicit paths (no glob), `set -euo pipefail`, `node --version` recorded, added as a STEP to the existing `quality` job so the `Lint, types, tests` display name pinned by ops/branch-protection.json is untouched (I confirmed `ops/branch-protection.json` is absent from `git status`). But plan Phase 8 acceptance 2 requires proving the step is not vacuous IN CI — push a commit that re-keys one fixture entry, watch `Lint, types, tests` go red naming the guard, revert — because a local shell run cannot catch a YAML-level swallowed exit code. Nothing is committed yet and no PR exists, so that demonstration is outstanding. I verified locally that all five guards exit 0 and that the batching guard exits 1 on a corrupted copy, which is necessary but explicitly not sufficient per the plan.

PROPOSED FIX
After the PR is open, run the red demonstration in CI once and paste the run URL into the IMPLEMENTATION_REPORT alongside the green log, or state plainly in the report that Phase 8 acceptance 2 is outstanding and split it into the follow-up PR the plan permits (it says a run may end cleanly before Phase 8) rather than recording the phase as complete on local evidence.
~~~

### [QUESTION] Phase 8's acceptance is unmet by construction: the CI step has never executed, and its non-vacuity was to be proven IN CI

~~~
location: .github/workflows/ci.yml:70
confidence: high
category: test-coverage

PROBLEM
Phase 8 acceptance 1 requires 'a CI run log showing the guards step naming all five files and exiting 0' and acceptance 2 requires pushing a commit that re-keys a fixture entry, watching `Lint, types, tests` go RED, then reverting — explicitly because 'a local shell demonstration cannot catch a YAML-level swallowed exit code'. The work is uncommitted, so neither has happened; the step at `:70-78` has never run once. What I CAN confirm locally: the five paths are explicit rather than globbed, all five exist and exit 0 on Node v24.15.0, the step is inside the existing `quality` job after pytest (`:54-57`) so no new display name is introduced, `name: Lint, types, tests` at `:17` is byte-unchanged, and `ops/branch-protection.json` is absent from `git status --porcelain` (Phase 8 acceptance 3 satisfied). Two residual risks I could not clear: the guards are pinned to `node-version: '22'` in CI but were only ever validated on v24.15.0 locally, and `set -euo pipefail` under GitHub's default `bash -e {0}` is correct in principle but unexercised. Note the plan itself pre-authorises deferring this ('a run may end cleanly before this phase … may be split into a follow-up PR'), so this is a hand-off question rather than a defect.

PROPOSED FIX
Either split Phase 8 into a follow-up PR as the plan permits, or carry the two demonstrations through on this PR before merge: confirm the guards step exits 0 in the run log naming all five files, then push one commit re-keying a single FINDINGS_BY_LENS entry and confirm the `Lint, types, tests` check goes red naming verify_batching_guard.mjs, then revert. Also run the five guards once on Node 22 locally (or note the version delta in the IMPLEMENTATION_REPORT) so the pinned runtime is measured rather than assumed.
~~~

## Gated decisions as the panel posed them

```json
[
  {
    "question": "How should the own-directory exemption in bare_request_tokens be resolved — drop it and fence the single offender, or narrow it to a stage-artifact whitelist?",
    "recommendation": "DROP IT. My own measurement (and three reviewers' independently) shows the exemption rescues exactly ONE token in the entire repo — first-sight/IMPLEMENTATION_PLAN.md's checklist line naming its own future IMPLEMENTATION_REPORT.md — and Phase 5 step 7 already prescribes the remedy for exactly that shape: fence it or angle-bracket it, which is also what all five skills tell authors to do. Dropping restores the guard to exactly the promises the documentation makes, which is the whole subject of doc-link-guard-mismatch; keeping it means the guard is permanently more permissive than its own contract and a typo'd sibling artifact can never be caught. If the operator prefers to keep it on its merits, it must be narrowed to a small frozenset of pipeline stage filenames AND written into the promise prose in the same commit, so code and documentation stay one artifact.",
    "related": [
      "S4",
      "P5.3"
    ]
  },
  {
    "question": "Should the fifth promise ('link titles are exempt too') be implemented, or should the clause be deleted from the three skills that state it?",
    "recommendation": "IMPLEMENT IT. The clause is live in three skills, the strip is a handful of lines in resolve_target, and the request being closed is precisely 'the guard rejects what the documentation promises'. Closing doc-link-guard-mismatch while a documented exemption still produces a red build reinstates the defect under a new number. Pair it with the negative test (a titled link to a DEAD file is still reported) so the strip cannot launder a broken path. Deleting the clause is the acceptable fallback only if the operator wants scope frozen — and then it must be stated in the IMPLEMENTATION_REPORT, because the promise is currently false either way.",
    "related": [
      "S5",
      "P5.4"
    ]
  },
  {
    "question": "Should Phase 8's in-CI demonstrations be completed on this PR, or split into the follow-up PR the plan permits at :469-471?",
    "recommendation": "COMPLETE THEM ON THIS PR. The cost is one throwaway commit and a revert; the plan's own reasoning is that a local run cannot catch a YAML-level swallowed exit code, and two residual risks remain uncleared locally (CI pins node 22 while every local run was v24.15.0, and `set -euo pipefail` under GitHub's default `bash -e {0}` is unexercised). Landing an unproven gate is exactly the pattern this request exists to end — verify_batching_guard.mjs was red from the day it landed because nobody was forced to run it. If the operator does split it, the deferral must be named in the IMPLEMENTATION_REPORT under 'what this does not close', never inherited silently.",
    "related": [
      "S6",
      "P8.2"
    ]
  },
  {
    "question": "The widened Phase 6 guard found three phantom-doc sites where the plan's checklist named one, so scope_panel.js was edited outside the checklist. Accept the fold-in?",
    "recommendation": "ACCEPT IT, and record it. All three were replayed against the HEAD blobs by four independent lenses and are genuine instances of the same never-existing docs/data-sources.md; Phase 6 acceptance 2 cannot go green without all three fixed. I read the scope_panel.js hunk and it makes the sentence-level correction step 3 demanded rather than a filename swap. The plan's checklist was under-specified — itself a small vindication of the widening. Name all three file:line sites in the IMPLEMENTATION_REPORT and the /commit message body so a reviewer of the commit is not left with an unexplained file.",
    "related": [
      "S14",
      "C4",
      "P6.1"
    ]
  },
  {
    "question": "Phase 7 step 5 mandated ONE appended memory entry; three were appended. Keep all three?",
    "recommendation": "KEEP THEM. All three are append-only at EOF with no deletions, all carry epistemic labels, test_memory_entries_carry_an_epistemic_label passes, and the mandated entry honours D4 precisely — it refutes only the INTERPRETATION of the 2026-08-15 entry while stating that entry's sibling-repo measurement 'stands and was not re-tested here'. The two extras record what the widened guard actually found. Note the deviation in the IMPLEMENTATION_REPORT with each entry's label and why it earned a line; do not prune, since the memory file's own rule is append-never-prune.",
    "related": [
      "P7.3"
    ]
  },
  {
    "question": "RCA Hardening 8 was to be filed as a fresh intake per D5 and was not. File it now, or declare it dropped?",
    "recommendation": "FILE IT. D5 was a decided disposition in the plan and the cost is one intake artifact. If the operator would rather not open another request while two are closing, state plainly in the IMPLEMENTATION_REPORT that D5 was consciously dropped and why — an undone commitment nobody records is how the next port-drift defect gets diagnosed from scratch. Either way, also state per Phase 7 step 7 that leak-guard-blind-to-untracked-files remains untouched at `intake`.",
    "related": [
      "S1",
      "P7.5"
    ]
  }
]
```

## Verify results

```json
[
  {
    "id": "F1",
    "title": "Phase 7 was not executed: no IMPLEMENTATION_REPORT, no status advances, no Index rows — the bugfix track's record half is missing",
    "severity": "blocker",
    "confidence": "high",
    "category": "acceptance-contract",
    "location": "requests/bugfix-requests/README.md:53",
    "problem": "`git status --porcelain -- requests/` returns nothing. The Index row at :53 still reads `planned` for verify-batching-guard-red-on-arrival and :51 still reads `planned` for doc-link-guard-mismatch; IMPLEMENTATION_PLAN.md:1 still reads `planned · created 2026-08-17 · decided · next: implement`; ROOT_CAUSE_ANALYSIS.md:1 still reads `diagnosed · … · next: plan`; and Get-ChildItem on the request directory shows no IMPLEMENTATION_REPORT.md. The bugfix track's definition of done (requests/bugfix-requests/README.md:24-26) is the fix PLUS the record, and the plan's Phase 7 acceptance items 1 and 3 both depend on documents that do not exist. Concretely this loses the one thing the plan called irreplaceable: the before/after guard output and the three deliberately-corrupted-copy runs (IMPLEMENTATION_PLAN.md:441-443, 'A green guard nobody has seen fail is a guard nobody has tested'). I had to re-derive all three during this review because no record of them exists. It also leaves the paper trail actively wrong: two requests marked `planned` whose work is sitting finished in the working tree.",
    "proposed_fix": "Before /commit: (1) write requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_REPORT.md pasting the pre-fix six-line RED output, the post-fix four diagnostic lines, and the three re-broken-copy runs verbatim (they are reproducible from the scratchpad recipe: copy the guard, repoint HERE at the tracked tests dir, re-key one fixture entry); include a 'red repro now green + regression test present' row naming tests/test_skill_references.py's two tests as the guard left behind. (2) Advance requests/bugfix-requests/README.md:53 and :51 to `fixed`, pointing the doc-link Notes cell at this plan. (3) Advance the status blockquotes on both requests' BUGFIX_REQUEST.md, ROOT_CAUSE_ANALYSIS.md, and this IMPLEMENTATION_PLAN.md, without re-dating or revising the RCA bodies. (4) State plainly, per Phase 7 step 7, that leak-guard-blind-to-untracked-files is untouched and RCA Hardening 8 is deferred to a fresh intake.",
    "reviewer": "acceptance",
    "reviewers": [
      "acceptance"
    ],
    "merged_from": [
      "F1"
    ],
    "vid": "V1",
    "verdict": "confirmed",
    "verify_evidence": "`git status --porcelain -- requests/` returns EMPTY while 13 files are modified + 1 untracked elsewhere (.claude/skills/*, tests/test_doc_links.py, tests/test_skill_references.py, tests/test_doc_link_contract.py, .github/workflows/ci.yml, .claude/agents/data-engineer-memory.md). Directory listing of the request shows only `reviews/`, `BUGFIX_REQUEST.md` (8505b), `IMPLEMENTATION_PLAN.md` (52046b), `ROOT_CAUSE_ANALYSIS.md` (13307b) — there is NO IMPLEMENTATION_REPORT.md. requests/bugfix-requests/README.md:53 reads `| [verify-batching-guard-red-on-arrival](...) | planned | ...` with Notes in present tense ('exits 1 on a clean checkout and always has'); :51 reads `| [doc-link-guard-mismatch](...) | planned |` even though Phase 5 landed. IMPLEMENTATION_PLAN.md:1 = '> **Status:** planned · created 2026-08-17 · decided · next: implement'; verify-.../ROOT_CAUSE_ANALYSIS.md:1 and BUGFIX_REQUEST.md:1 both = 'diagnosed · created 2026-08-17 · decided · next: plan'. README.md:24-26 states the track's definition of done. Plan Phase 7 acceptance 1 (:449-450, 'with the new documents in the tree') and acceptance 3 (:453-454, both Index rows + all four blockquotes agree) are therefore unmet, and Phase 7 step 6 (:441-443, 'A green guard nobody has seen fail is a guard nobody has tested') produced nothing — the Phase 2 corrupted-copy runs exist in no tracked artifact. Severity 'blocker' is defensible on the track contract, though the upstream RCA's own correctness contract is independently met (see V15 evidence).",
    "verify_ran": "`git status --porcelain` (full tree) and `git status --porcelain -- requests/`; `Get-ChildItem requests\\bugfix-requests\\verify-batching-guard-red-on-arrival`; `Get-Content` of the first line of all four artifact status blockquotes; printed `requests/bugfix-requests/README.md` lines 43-53 and 24-26."
  },
  {
    "id": "F2",
    "title": "strip_fences mis-parses a fence opened on a list-item line and silently blanks 29% of a live skill document out of both link checks",
    "severity": "major",
    "confidence": "high",
    "category": "correctness",
    "location": "tests/test_doc_links.py:42",
    "problem": "FENCE (tests/test_doc_links.py:25) only matches a delimiter at line start after optional whitespace/blockquote markers, so it MISSES a fence opened on the same line as a list marker. `.claude/skills/commit/SKILL.md:189` is exactly that shape (`2. ```` `), while its closer at :191 is an ordinary indented ``` — so the pre-pass reads :191 as an OPENER, parity flips for the rest of the file, and every later delimiter is mislabelled. Measured consequence: 75 of 258 non-blank lines of that file (lines 35-257, including the entire live-prose 'What good looks like' section at :245-258, e.g. :247 '- **Nothing landed that the user didn't see.** …') are blanked before LINK and BARE_REQUEST_TOKEN ever run. A dead link or dead requests/ token anywhere in that 29% is now invisible. My probe also confirms this leaves the file with a run-away fence opened at :224 that never closes, so the blanking runs to EOF. This is the same failure class the request exists to eliminate: a guard that reports green while having quietly stopped checking, and it is exactly the risk row the plan flagged ('Nested and blockquoted fences are explicitly in the promise text'). The suite is green today only because the blanked region happens to contain no links.",
    "proposed_fix": "Two changes in strip_fences: (1) recognise a fence opener that follows a list marker by also matching `^\\s*(?:[-*+]|\\d+[.)])\\s+(`{3,}|~{3,})\\s*$` and treating it as an opener; (2) make an unterminated fence LOUD rather than silent — if `marker is not None` when the loop ends, either treat the run-away region as unfenced (fail-closed) or have the repo-wide tests append a failure naming the file and the opening line. Add a case to tests/test_doc_link_contract.py for both shapes: a `2. ``` ` opener whose content is exempt, and an unterminated fence that does not switch the guard off for the remainder of the file.",
    "reviewer": "acceptance",
    "reviewers": [
      "acceptance"
    ],
    "merged_from": [
      "F2"
    ],
    "vid": "V2",
    "verdict": "confirmed",
    "verify_evidence": "FENCE at tests/test_doc_links.py:25 is `^\\s*(?:>\\s*)*(`{3,}|~{3,})` — no list-marker alternative. Probe output: line 189 is `'2. ```'` -> FENCE match: False; line 191 is `'   ```'` -> FENCE match: True. Event trace tail: ('open',175 close)…('open',191,'   ```'),('close',222,'```'),('open',224,'```') and `final marker state: `` ` `` — i.e. the file ends inside an open fence, exactly as the finding says. Measured blanking: `blanked count: 75` originally-non-blank lines, ranges ending [245,245] and [247,257]; the file's 'What good looks like' prose (245-258, e.g. :247 \"- **Nothing landed that the user didn't see.**…\") is inside that. Injection proof from a second probe: inserting `[the missing doc](docs/definitely-not-here.md)` + `requests/feature-requests/no-such-slug/PROJECT_SCOPE.md` at line 250 gives `dead link seen=False dead tokens=[]`; the identical injection at line 20 gives `dead link seen=True dead tokens=['requests/feature-requests/no-such-slug/PROJECT_SCOPE.md']`. So the region is genuinely out of BOTH scans. Full `uv run pytest -q` is green (all pass), confirming the suite is green only because that window happens to hold no dead pointer. Two minor arithmetic nits that do not change the verdict: the file has 194 non-blank lines (not 258 — 258 is total lines), so the blanked share is 75/194 = 39%, not 29%; and the plan risk row cited is real (IMPLEMENTATION_PLAN.md:582, 'Nested and blockquoted fences are explicitly in the promise text'), as is the 'Do not weaken the scan to make the repo pass' constraint at IMPLEMENTATION_PLAN.md:355.",
    "verify_ran": "Read tests/test_doc_links.py:20-65 in full, then ran a probe (uv run python) that applied the SHIPPED strip_fences to .claude/skills/commit/SKILL.md, printed which originally-non-blank lines came back blank, and replayed the fence state machine printing every open/close event and the final marker. Also read .claude/skills/commit/SKILL.md:170-258 directly, and ran `uv run pytest -q` (full suite)."
  },
  {
    "id": "F3",
    "title": "The own-directory exemption in bare_request_tokens is far broader than the single token it was added for, and silences typo'd sibling-artifact pointers",
    "severity": "major",
    "confidence": "high",
    "category": "guard-weakening",
    "location": "tests/test_doc_links.py:134",
    "problem": "`if own_dir is not None and target.parent == own_dir: continue` exempts ANY unresolvable requests/ token whose parent directory is the source document's own directory. I measured what it actually buys: re-running the repo-wide scan with `source=` dropped reports exactly ONE additional token in the entire tree — `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`. In exchange it blanket-exempts the single most common cross-reference these documents make: a stage-3 plan citing its own stage-2 artifact. Probe: `bare_request_tokens('see requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSES.md', source=<that plan>)` returns `[]` — a typo'd RCA pointer inside the plan that cites its RCA a dozen times is reported as clean. This is precisely what IMPLEMENTATION_PLAN.md:355 forbade ('Do not weaken the scan to make the repo pass'), and the exemption appears in neither the plan nor the doc-link RCA, so no reviewer has ever disposed on it.",
    "proposed_fix": "Narrow the exemption to the case it was written for: exempt only when the missing basename is a not-yet-written PIPELINE artifact that a later stage creates — e.g. `target.name in {'IMPLEMENTATION_REPORT.md', 'IMPLEMENTATION_PLAN.md'}` AND `target.parent == own_dir`. Everything else in the document's own directory stays checked, so a typo'd ROOT_CAUSE_ANALYSIS.md/PROJECT_SCOPE.md/BUGFIX_REQUEST.md pointer goes red as it should. Then extend tests/test_doc_link_contract.py:149 with the negative case (a typo'd sibling artifact in the source's own directory IS reported), which is the assertion that would have caught this.",
    "reviewer": "acceptance",
    "reviewers": [
      "acceptance"
    ],
    "merged_from": [
      "F3"
    ],
    "vid": "V3",
    "verdict": "confirmed",
    "verify_evidence": "tests/test_doc_links.py:134 is literally `if own_dir is not None and target.parent == own_dir: continue` — no filename predicate at all, so it covers ANY unresolvable requests/ token in the source's own directory. Probe output, source = requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md (exists: True): token `.../ROOT_CAUSE_ANALYSES.md` -> `with source: []` | `source=None: ['requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSES.md']`. Same shape for a typo'd `PROJECT_SCOPE.md` in that directory: with source `[]`. Cost measurement across all 82 markdown files scanned: `tokens rescued by own-dir exemption: 1` — and it is exactly `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`, matching the finding's measurement (the finding's '209 markdown files' is wrong; the guard scans 82 — the ONE-token result is right). So narrowing to a stage-artifact whitelist would keep the suite green and restore the typo'd-sibling check. One correction to the finding's framing: the exemption is not wholly undisposed — plan D1 (IMPLEMENTATION_PLAN.md:534) blesses forward-references in principle ('stage-1 artifacts routinely forward-reference files later stages create'). What is undisposed is the BREADTH of the mechanism chosen; nothing in the plan or the doc-link RCA authorises exempting arbitrary same-directory tokens, and IMPLEMENTATION_PLAN.md:355 forbids weakening the scan. tests/test_doc_link_contract.py:161 only covers a dead pointer into ANOTHER request's directory, so the typo'd-sibling case is untested.",
    "verify_ran": "Read tests/test_doc_links.py:109-137 (bare_request_tokens) and tests/test_doc_link_contract.py:149-166. Ran a probe calling guard.bare_request_tokens on a typo'd sibling token with source=<the verify-batching-guard plan> and with source=None, then a repo-wide diff of the two modes across every markdown file returned by guard.markdown_files(). Also grepped IMPLEMENTATION_PLAN.md and requests/bugfix-requests/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md for the exemption's rationale and read plan D1 (IMPLEMENTATION_PLAN.md:532-539)."
  },
  {
    "id": "F1",
    "title": "Phase 7 (Record) is almost entirely unimplemented — statuses, both Index rows, the IMPLEMENTATION_REPORT and the D5 intake are all missing",
    "severity": "major",
    "confidence": "high",
    "category": "plan-fidelity-silently-skipped-phase",
    "location": "requests/bugfix-requests/README.md:51 and :53; requests/bugfix-requests/verify-batching-guard-red-on-arrival/{BUGFIX_REQUEST.md:1, ROOT_CAUSE_ANALYSIS.md:1, IMPLEMENTATION_PLAN.md:1}; requests/bugfix-requests/doc-link-guard-mismatch/{BUGFIX_REQUEST.md:1, ROOT_CAUSE_ANALYSIS.md:1}",
    "problem": "`git status --porcelain` shows NO file under `requests/` changed, and `Test-Path .../IMPLEMENTATION_REPORT.md` returns False. Measured on the tree: both Index rows still read `planned`; `verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md:1` and `ROOT_CAUSE_ANALYSIS.md:1` still read `diagnosed · … · next: plan`; `IMPLEMENTATION_PLAN.md:1` still reads `planned · … · next: implement`; `doc-link-guard-mismatch`'s two artifacts still read `diagnosed · … · next: plan` even though Phase 5 closed that request. `Get-ChildItem requests/bugfix-requests, requests/feature-requests` shows no new intake directory, so D5's \"RCA Hardening 8 is filed as a fresh intake\" did not happen either. Of Phase 7's seven steps only step 5 (the memory append) landed. Phase 7 acceptance #3 — \"Both requests' Index rows and all four artifact status blockquotes agree … so /commit's doc gate passes without a drift complaint\" — is unmet, and the plan's §7 checklist carries five unticked record items. Step 6 is the load-bearing one: \"Write the IMPLEMENTATION_REPORT with the before/after guard output pasted verbatim, including Phase 2's deliberately-corrupted-copy runs. A green guard nobody has seen fail is a guard nobody has tested.\" Those three corrupted-copy runs were the plan's central proof obligation and nothing in the tree records them; I had to re-derive them myself. Phase 0's baseline measurements have no home either.",
    "proposed_fix": "Before /commit: (a) write `requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_REPORT.md` with the Phase 0 baseline, the before/after guard diagnostics, and the three re-broken-copy outputs verbatim; (b) advance the four artifact status blockquotes and this plan's own `:1` to the track README's terminal word (`fixed`), leaving the RCA bodies unrevised; (c) advance both Index rows at `requests/bugfix-requests/README.md:51` and `:53`, pointing doc-link-guard-mismatch's Notes at this plan, and leave `leak-guard-blind-to-untracked-files` at `:52` byte-unchanged; (d) file the D5 Hardening-8 sweep as a fresh intake, or state explicitly in the report that it was consciously dropped.",
    "reviewer": "fidelity",
    "reviewers": [
      "fidelity"
    ],
    "merged_from": [
      "F1"
    ],
    "vid": "V4",
    "verdict": "confirmed",
    "verify_evidence": "`git status --porcelain` lists 13 modified files + 1 untracked (tests/test_doc_link_contract.py) and NOTHING under requests/; `git diff HEAD --stat -- requests/` prints nothing. `Test-Path .../IMPLEMENTATION_REPORT.md` -> False, and the recursive listing of requests/bugfix-requests returns only the 7 pre-existing artifacts + 2 reviews files. Measured statuses: requests/bugfix-requests/README.md:51 `| [doc-link-guard-mismatch](doc-link-guard-mismatch/) | planned |`, :53 `| [verify-batching-guard-red-on-arrival](...) | planned |`; verify-batching.../BUGFIX_REQUEST.md:1 and ROOT_CAUSE_ANALYSIS.md:1 = `> **Status:** diagnosed · created 2026-08-17 · decided · next: plan`; IMPLEMENTATION_PLAN.md:1 = `planned · … · next: implement`; doc-link-guard-mismatch's two artifacts likewise `diagnosed · … · next: plan` even though Phase 5 closed that request. The directory listing shows no new intake dir anywhere under requests/ (newest is verify-batching-guard-red-on-arrival, 8/17 4:04 PM), so D5's 'RCA Hardening 8 is filed as a fresh intake' (plan :444-446, :559-563) did not happen. Only Phase 7 step 5 landed: three dated entries at data-engineer-memory.md:290-313 (the `verified` 2026-08-17 correction of the 2026-08-15 entry, plus two `measured` entries), and `uv run pytest tests/test_agent_contract.py::test_memory_entries_carry_an_epistemic_label` passes. Phase 7 acceptance 3 (plan :453-454) is therefore unmet, and Phase 7 step 6's load-bearing report ('A green guard nobody has seen fail is a guard nobody has tested', plan :441-443) — the only home for Phase 2's three deliberately-corrupted-copy runs and Phase 0's baseline — does not exist in the tree.",
    "verify_ran": "`git status --porcelain` and `git diff HEAD --stat -- requests/` in <repo root>; `Get-ChildItem -Recurse -File requests/bugfix-requests`; `Get-ChildItem -Directory requests/bugfix-requests, requests/feature-requests, requests/data-incidents`; read line 1 of all five artifacts and lines 43-53 of requests/bugfix-requests/README.md; read the plan's Phase 7 (:415-459) and §7 checklist (:590-609); read .claude/agents/data-engineer-memory.md:285-313."
  },
  {
    "id": "F2",
    "title": "Phase 5 added an undocumented \"own request directory\" exemption to the bare-token scan — a loosening the plan forbade, and it masks this run's own missing artifact",
    "severity": "major",
    "confidence": "high",
    "category": "plan-deviation-guard-weakened",
    "location": "tests/test_doc_links.py:126 and :134 (`own_dir` / `if own_dir is not None and target.parent == own_dir: continue`)",
    "problem": "Phase 5 step 7 is explicit: \"A token that is genuinely dead gets fixed; a token that is a deliberate template placeholder gets the angle-bracket treatment already exempted at `:28`. Do not weaken the scan to make the repo pass.\" The four promises the plan enumerates (fence, `:123` suffix, `var/` target, bare-token scan) contain no fifth same-directory exemption, and the promise prose the five skills state — which Phase 5 step 8 says must become TRUE and must not be edited — prescribes a different remedy for exactly this shape: \"a **forward reference** to a file a later stage creates … Put either inside a fenced code block\". I measured the exemption's blast radius by re-running the repo-wide scan with `source=None`: it suppresses exactly ONE token, `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`. So a whole undocumented exemption class was minted to avoid fencing one line. Worse, it is self-blinding in precisely this run: a plan citing its own not-yet-written `IMPLEMENTATION_REPORT.md` is exempt, which is why nothing in the green suite flagged F1. The result is a guard whose behaviour again diverges from the documentation five skills give authors — the exact defect class this request exists to close, re-created inside the fix.",
    "proposed_fix": "Drop the `source`/`own_dir` parameter and the `:134` continue. Fence the single offending token in `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` (or angle-bracket it) as the skills' own prose instructs, then delete `test_a_document_may_name_a_not_yet_written_artifact_in_its_own_directory` and `test_but_a_dead_pointer_into_another_request_is_still_caught` from `tests/test_doc_link_contract.py:149-165`. If the operator prefers to keep the exemption, it must be added to the promise prose in all five skills in the same commit, so code and documentation still agree.",
    "reviewer": "fidelity",
    "reviewers": [
      "fidelity"
    ],
    "merged_from": [
      "F2"
    ],
    "vid": "V5",
    "verdict": "confirmed",
    "verify_evidence": "The exemption exists exactly as cited: tests/test_doc_links.py:126 `own_dir = source.parent.resolve() if source is not None else None` and :134 `if own_dir is not None and target.parent == own_dir: continue`. Blast radius measured, and the finding's number is exact — with `source=None` the repo-wide scan prints ONE line: `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`; with `source=path` it prints nothing. The offender is a single checklist line, first-sight/IMPLEMENTATION_PLAN.md:738 (`- [ ] requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md + the track Index row`), whose documented remedy is a fence. The plan forbids exactly this: IMPLEMENTATION_PLAN.md:355 reads \"a token that is a deliberate template placeholder gets the angle-bracket treatment already exempted at `:28`. Do not weaken the scan to make the repo pass.\" And the promise prose the guard must satisfy — .claude/skills/make-bugfix-request/SKILL.md:201-203, \"a **forward reference** to a file a later stage creates … Put either inside a fenced code block (``` or ~~~, blockquoted is fine) — fenced content is exempt\" — names fencing as THE escape hatch and says nothing about a same-directory rule. So the shipped guard is strictly more permissive than the contract five skills state, and a genuinely dead pointer inside a document's own request directory (e.g. a typo'd `ROOT_CAUSE_ANALYSYS.md`) is now silently skipped. One sub-claim of V5 is WRONG and should not be relied on: \"a plan citing its own not-yet-written IMPLEMENTATION_REPORT.md is exempt, which is why nothing in the green suite flagged F1\". The `source=None` sweep proves this plan contains no such bare token at all — its checklist at IMPLEMENTATION_PLAN.md:606 writes only the directory token `requests/bugfix-requests/verify-batching-guard-red-on-arrival/`, which resolves. The exemption is not what hides the missing report. The main claim (undocumented loosening, forbidden by Phase 5 step 7, one-token blast radius, two tests at test_doc_link_contract.py:149-165 codifying it) is fully confirmed.",
    "verify_ran": "Read tests/test_doc_links.py:109-137 in full (the `bare_request_tokens` body). Read the plan's Phase 5 step 7 at requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md:353-355 and step 8 at :356-358. Read the promise prose at .claude/skills/make-bugfix-request/SKILL.md:198-204 and grepped its four siblings (`git grep -n 'bare ' -- .claude/skills/*/SKILL.md`). Measured the exemption's blast radius by re-running the scanner over every markdown file twice — once `source=None`, once `source=path` — via `uv run python -c` importing tests/test_doc_links.py. Read tests/test_doc_link_contract.py:149-165. Ran `uv run pytest -m \"not gamedata\" -q` (all green) and the batching guard (exit 0)."
  },
  {
    "id": "F1",
    "title": "Fence tracker misses a fence opened inside a list item, blanking 75 lines of commit/SKILL.md from both link checks",
    "severity": "major",
    "confidence": "high",
    "category": "correctness",
    "location": "tests/test_doc_links.py:25 (FENCE); triggered by .claude/skills/commit/SKILL.md:189",
    "problem": "FENCE = `^\\s*(?:>\\s*)*(`{3,}|~{3,})` only recognises a fence marker after whitespace or blockquote markers, so the CommonMark-legal fence that opens inside a numbered list item at `.claude/skills/commit/SKILL.md:189` (`2. ```) is not seen as an opener. `strip_fences` then reads the genuine CLOSER at :191 as an OPENER and fence parity is inverted for the rest of the file: measured, 75 of 258 lines are blanked, including all of \"Step 7 — Push the branch\", \"Why not -m\" and the entire \"What good looks like\" section, and the file ends with an unclosed fence (it is the only such file in the repo — I scanned all 209 markdown files). I proved the consequence by injecting `- see [the missing doc](docs/definitely-not-here.md) and requests/bugfix-requests/no-such-slug/X.md` at line 251 of that file: `test_relative_links_resolve` and `test_bare_request_tokens_resolve` both report NOTHING, while the identical broken link appended to CLAUDE.md is caught. So the guard that Phase 3 just repointed six skills at has a silent 29% blind spot in one of those very skills — the same 'a guard nobody is forced to notice' failure this request exists to fix. Plan Phase 5 acceptance 3 ('prove the guard still bites') passes only because the demonstration was done in a file with balanced fences.",
    "proposed_fix": "Make FENCE list-aware: `^\\s*(?:>\\s*)*(?:[-*+]\\s+|\\d+[.)]\\s+)?(`{3,}|~{3,})`. I ran this against every markdown file in the repo: it reclassifies exactly one line (commit/SKILL.md:189) and afterwards ZERO documents end with an open fence — no false positives on the ten other lines that merely mention ``` inline. Then add the cheap invariant that would have caught this class: a test asserting no scanned document ends with fence state open, so an unclosed fence fails loudly instead of silently exempting the tail.",
    "reviewer": "correctness",
    "reviewers": [
      "correctness"
    ],
    "merged_from": [
      "F1"
    ],
    "vid": "V6",
    "verdict": "confirmed",
    "verify_evidence": "FENCE = `^\\s*(?:>\\s*)*(`{3,}|~{3,})` at tests/test_doc_links.py:25 does not match `.claude/skills/commit/SKILL.md:189` (`2. ```` — the CommonMark-legal fence opened inside a numbered list item), so strip_fences reads the genuine closer at :191 as an opener and parity inverts. Measured: 75 of 258 lines blanked, in runs including 191-193, 195-200, 218 ('## Step 7 — Push the branch'), 245 ('## What good looks like') and 247-257 to EOF; blanked headings printed were exactly ['## Step 7 — Push the branch', '## What good looks like']. Final-fence-state scan over all 82 files markdown_files() returns: `OPEN: .claude/skills/commit/SKILL.md` — the only one. Consequence reproduced: injecting `- see [the missing doc](docs/definitely-not-here.md) and requests/bugfix-requests/no-such-slug/X.md` at line 251 yields `commit/SKILL.md broken links detected: []` and `dead bare tokens: []`, while the identical text appended to CLAUDE.md yields `['docs/definitely-not-here.md']` and `['requests/bugfix-requests/no-such-slug/X.md']`. The blind spot sits in one of the six skills Phase 3 just repointed at this guard (`git grep -n test_doc_links.py -- .claude/skills/` shows commit/SKILL.md:104 among them). Proposed fix validated: the list-aware regex reclassifies exactly ONE line repo-wide (commit/SKILL.md:189) and afterwards zero files end with an open fence. Only imprecision: the finding says '209 markdown files' — the guard's actual scan set is 82 (markdown_files() excludes .git and var); the substance is unaffected.",
    "verify_ran": "Read tests/test_doc_links.py in full (FENCE at :25, strip_fences :42-65) and .claude/skills/commit/SKILL.md:179-200. Then ran an in-memory probe (scratchpad script, no repo file touched) that imported tests.test_doc_links, diffed strip_fences() output against the raw file, computed final fence state for every file in markdown_files(), tested the proposed list-aware regex over the same set, and injected the finding's broken link at line 251 in memory for both commit/SKILL.md and CLAUDE.md."
  },
  {
    "id": "F2",
    "title": "Plan Phase 7 (the record) is entirely undone — statuses, both Index rows and the IMPLEMENTATION_REPORT are missing",
    "severity": "major",
    "confidence": "high",
    "category": "completeness",
    "location": "requests/bugfix-requests/README.md:51 and :53",
    "problem": "The plan's files-to-touch checklist requires advancing four artifact status blockquotes and two Index rows and writing an IMPLEMENTATION_REPORT.md; none of it is in the working tree. Measured: `requests/bugfix-requests/README.md` still shows both `doc-link-guard-mismatch` and `verify-batching-guard-red-on-arrival` at Stage `planned`; `verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md:1` and `doc-link-guard-mismatch/{BUGFIX_REQUEST,ROOT_CAUSE_ANALYSIS}.md:1` all still read `diagnosed`; `IMPLEMENTATION_PLAN.md:1` still reads `planned · … · next: implement`; and a glob of the request directory shows no IMPLEMENTATION_REPORT.md. Phase 7 acceptance 3 ('both requests' Index rows and all four artifact status blockquotes agree') is unmet, and /commit's doc gate is specified to complain about exactly this drift. Note the fix itself is done — the bugfix track's acceptance contract (red repro green, regression guard left behind, nothing regressed) is satisfied; this is the paper trail, and Phase 7 step 6 is explicit that a green guard nobody has seen fail is a guard nobody has tested.",
    "proposed_fix": "Before the commit: advance both Index row Stage cells to the track README's terminal word, advance the four artifact status blockquotes in step, advance this plan's own blockquote (do not re-date it), and write IMPLEMENTATION_REPORT.md with the before/after guard output plus the three deliberately-re-broken-copy runs pasted verbatim. Leave the `leak-guard-blind-to-untracked-files` row byte-unchanged, and leave both RCAs' bodies decided.",
    "reviewer": "correctness",
    "reviewers": [
      "correctness"
    ],
    "merged_from": [
      "F2"
    ],
    "vid": "V7",
    "verdict": "confirmed",
    "verify_evidence": "Every measurement in the finding reproduces. `git status --porcelain` returns 13 modified paths plus one untracked, all under .claude/, .github/ or tests/ — nothing under requests/. requests/bugfix-requests/README.md:51 still reads `| [doc-link-guard-mismatch](doc-link-guard-mismatch/) | planned |` and :53 still reads `| [verify-batching-guard-red-on-arrival](verify-batching-guard-red-on-arrival/) | planned |`, against the track grammar at :45 (`intake → diagnosed → planned → fixed`). All four artifact blockquotes still read `diagnosed`: verify-.../BUGFIX_REQUEST.md:1 and ROOT_CAUSE_ANALYSIS.md:1 (`diagnosed · created 2026-08-17 · decided · next: plan`), doc-link-guard-mismatch/BUGFIX_REQUEST.md:1 (`created 2026-08-16`) and its ROOT_CAUSE_ANALYSIS.md:1. The plan's own blockquote at IMPLEMENTATION_PLAN.md:1 still reads `planned · created 2026-08-17 · decided · next: implement`. Get-ChildItem on the request directory returns only `reviews`, BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md — no IMPLEMENTATION_REPORT.md. Plan Phase 7 acceptance 3 (:453-454, \"Both requests' Index rows and all four artifact status blockquotes agree\") is therefore measurably unmet. The finding's framing that the fix itself is done also checks out: `uv run pytest -m \"not gamedata\"` is fully green and `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 printing the four pinned diagnostic lines. Two corrections to the finding's scope, neither changing the verdict: (a) Phase 7 is not wholly undone — step 5's agent-memory append IS present, three dated `verified`/`measured` entries added at .claude/agents/data-engineer-memory.md:+290-313; (b) .claude/skills/commit/SKILL.md:117-129 says /commit owns advancing artifact status blockquotes and Index rows, so that half is arguably deferred by design, but IMPLEMENTATION_REPORT.md is not something /commit writes and is missing outright — and Phase 7 step 6 (:441-443) calls it out as the item carrying the deliberately-corrupted-copy evidence, which exists nowhere in the tree.",
    "verify_ran": "`git status --porcelain` and `git diff HEAD --stat` on the uncommitted tree. Read requests/bugfix-requests/README.md:43-53 (status grammar + all three Index rows). Read line 1 of requests/bugfix-requests/verify-batching-guard-red-on-arrival/{BUGFIX_REQUEST,ROOT_CAUSE_ANALYSIS,IMPLEMENTATION_PLAN}.md and of doc-link-guard-mismatch/{BUGFIX_REQUEST,ROOT_CAUSE_ANALYSIS}.md. Listed the request directory with Get-ChildItem. Read the plan's Phase 7 (:415-459) and its checklist (:590-609). Read .claude/skills/commit/SKILL.md:117-129 to check whether /commit legitimately owns any of it. Ran the full suite and the batching guard."
  },
  {
    "id": "F3",
    "title": "The bare-token scan's own-directory exemption swallows the most common dead pointer it was added to catch",
    "severity": "major",
    "confidence": "high",
    "category": "correctness",
    "location": "tests/test_doc_links.py:134",
    "problem": "`if own_dir is not None and target.parent == own_dir: continue` exempts EVERY unresolvable `requests/...` token whose parent directory is the citing document's own directory — not just a not-yet-written stage artifact. Measured against the real tree: `bare_request_tokens(\"see requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSYS.md\", source=<that plan>)` returns `[]`, and so does a typo'd `BUGFIX_REQEST.md`; the same token with `source=None` is correctly reported. A plan citing its own RCA, or an RCA citing its own BUGFIX_REQUEST, is the single most likely misleading cross-reference in this pipeline, and the docstring's justification ('a token pointing into a DIFFERENT request's directory is still checked, which is where a genuinely misleading cross-reference would live') is the wrong way round. The dropped-capability half of the doc-link RCA is therefore only half restored.",
    "proposed_fix": "Narrow the exemption from 'any token in my own directory' to a whitelist of not-yet-written stage artifacts, e.g. `target.name == \"IMPLEMENTATION_REPORT.md\"` (or a small tuple of downstream stage filenames) in addition to the parent check. I measured the cost: across all 209 markdown files exactly ONE token is currently rescued by this exemption — `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md` — so narrowing to that whitelist keeps the suite green and restores the check for typo'd siblings. Add a unit test for the typo'd-sibling case alongside the existing one at tests/test_doc_link_contract.py:149.",
    "reviewer": "correctness",
    "reviewers": [
      "correctness"
    ],
    "merged_from": [
      "F3"
    ],
    "vid": "V8",
    "verdict": "confirmed",
    "verify_evidence": "Probe output, verbatim: `ROOT_CAUSE_ANALYSYS.md` -> `with source: [] | source=None: ['requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSYS.md']`; `BUGFIX_REQEST.md` -> `with source: [] | source=None: ['requests/bugfix-requests/verify-batching-guard-red-on-arrival/BUGFIX_REQEST.md']`. Both typo'd sibling artifacts are silently swallowed with source set, and both are correctly reported with source=None — precisely the claim. The docstring at tests/test_doc_links.py:124 asserts 'A token pointing into a DIFFERENT request's directory is still checked, which is where a genuinely misleading cross-reference would live', which is backwards for this pipeline: a plan cites its own RCA and an RCA cites its own BUGFIX_REQUEST far more often than they cite another slug's. Cost of narrowing measured across all files the guard scans: `tokens rescued by own-dir exemption: 1`, `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md` — so a whitelist limited to IMPLEMENTATION_REPORT.md keeps `uv run pytest -q` green (it is green now) while restoring the check. The finding's '209 markdown files' figure is inaccurate (the guard's markdown_files() returns 82), but the one-token conclusion it rests on reproduces exactly.",
    "verify_ran": "Read the guard's own docstring justification at tests/test_doc_links.py:117-124 and the branch at :134. Ran a probe issuing the finding's exact two probes — `bare_request_tokens('see requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSYS.md', source=<that plan>)` and the same with `BUGFIX_REQEST.md` — each also with source=None as a control, plus the repo-wide rescued-token census."
  },
  {
    "id": "F1",
    "title": "strip_fences mis-detects a fence opened after a list marker, silently exempting 64 live lines of commit/SKILL.md from both link scans",
    "severity": "major",
    "confidence": "high",
    "category": "correctness",
    "location": "tests/test_doc_links.py:25 (FENCE) and tests/test_doc_links.py:42-65 (strip_fences)",
    "problem": "`FENCE = re.compile(r\"^\\s*(?:>\\s*)*(`{3,}|~{3,})\")` only recognises a fence marker preceded by whitespace or blockquote arrows. A fence opened inside a list item — CommonMark-legal and present in the repo — is invisible, and its *closing* marker (indented, so it DOES match) is then read as an OPEN, inverting fence state for the rest of the document.\n\nMeasured on the real tree with the shipped code: `.claude/skills/commit/SKILL.md:189` is `2. ```` (opener, NOT matched), `:191` is `   ```` (closer, matched as an OPEN), `:222` is then consumed as its close, and `:224` opens a fence that never closes. A list-marker-aware tracker blanks 31 lines of that file; the shipped one blanks 92 — **64 live lines (192–258) are treated as fenced**, including the entire `## Step 7 — Push the branch` section and all of `## What good looks like`.\n\nI proved the consequence rather than inferring it: injecting `- see [the missing doc](docs/definitely-not-here.md) and requests/feature-requests/no-such-slug/PROJECT_SCOPE.md` at line 250 yields `link targets found: []` and `dead bare tokens found: []` — both scans miss it. The identical injection at line 20 yields `['docs/definitely-not-here.md']` and `['requests/feature-requests/no-such-slug/PROJECT_SCOPE.md']`. Same file, same guard, opposite verdicts.\n\nThe minimal reproducer also shows both failure directions at once: `strip_fences(\"1. ```\\n   [dead](docs/nope.md)\\n   ```\\n[live](docs/also-nope.md)\\n\")` returns `['docs/nope.md']` — the *fenced* link leaked (false red) and the *unfenced* one was swallowed (false green).\n\nNone of the eleven tests in tests/test_doc_link_contract.py uses a list-item fence; every fixture there is a column-0 or blockquoted fence, so the rule is implemented but the case is never exercised.",
    "proposed_fix": "Widen the opener to allow an optional list marker, e.g. `FENCE = re.compile(r\"^\\s*(?:>\\s*)*(?:(?:[-*+]|\\d+[.)])\\s+)?(`{3,}|~{3,})\")` — I ran exactly this against every tracked Markdown file and `.claude/skills/commit/SKILL.md` is the only file whose blanked-line set changes (92 → 31), so the change is contained. Then add two fixture-string tests to tests/test_doc_link_contract.py alongside the existing fence tests: one asserting a link inside a `1. ``` … ``` ` list-item fence is exempt, and one asserting a link on the line AFTER that fence closes is still scanned. The second is the one that would have caught this.",
    "reviewer": "edgecases",
    "reviewers": [
      "edgecases"
    ],
    "merged_from": [
      "F1"
    ],
    "vid": "V9",
    "verdict": "confirmed",
    "verify_evidence": "Reproduced to the digit. `line189 repr: '2. ```' FENCE match: False` / `line191 repr: '   ```' FENCE match: True` — the list-item opener is invisible and its closer is read as an OPEN. Fenced-line sets: shipped = 92 lines, list-marker-aware = 31; the set difference is exactly `only-shipped count: 64 range: 192 - 258`, in two runs `[(192, 221), (225, 258)]` — i.e. the whole of `## Step 7 — Push the branch` (:218) and `## What good looks like` are silently exempt. Consequence proven, not inferred: injecting `- see [the missing doc](docs/definitely-not-here.md) and requests/feature-requests/no-such-slug/PROJECT_SCOPE.md` at line 250 gives `link targets found: [] dead bare tokens found: []`; the identical injection at line 20 gives `['docs/definitely-not-here.md']` and `['requests/feature-requests/no-such-slug/PROJECT_SCOPE.md']`. Minimal reproducer `strip_fences(\"1. ```\\n   [dead](docs/nope.md)\\n   ```\\n[live](docs/also-nope.md)\\n\")` yields link_targets `['docs/nope.md']` — the fenced link leaked and the unfenced one was swallowed, both directions at once. And tests/test_doc_link_contract.py has no list-item fence anywhere: its fence fixtures are column-0 (:37/:39, :68, :145) or blockquoted (:58/:60) only, so tests/test_doc_links.py:25 (FENCE) and :42-65 (strip_fences) implement the rule with the case never exercised.",
    "verify_ran": "Imported the shipped `strip_fences`/`FENCE`/`link_targets`/`bare_request_tokens` from tests/test_doc_links.py under `uv run python` and (1) matched FENCE against .claude/skills/commit/SKILL.md lines 189 and 191, (2) computed the fenced-line set under the shipped FENCE vs a list-marker-aware variant, (3) injected the reviewer's exact probe line at line 250 and at line 20 and re-ran both scans, (4) ran the minimal reproducer string, (5) grepped tests/test_doc_link_contract.py for every fence fixture."
  },
  {
    "id": "F2",
    "title": "An unclosed fence blanks the rest of the document with no error, so a whole file can be silently exempted",
    "severity": "major",
    "confidence": "high",
    "category": "test-coverage",
    "location": "tests/test_doc_links.py:50-65",
    "problem": "`strip_fences` carries `marker` past the end of the loop without ever noticing it is still set. Any document ending inside an open fence has every line from the opener to EOF blanked, and both `test_relative_links_resolve` and `test_bare_request_tokens_resolve` go quiet over that region — with no diagnostic at all. Verified directly: `strip_fences(\"```\\ncode\\n\\n[dead](docs/nope.md)\\n\")` yields zero link targets.\n\nThis is the amplifier that turns F1 from a 30-line bug into a 64-line one, and it is independently reachable: any author who forgets a closing fence turns off the link guard for the tail of their file and gets a green build as the reward. Scanning the tree today, exactly one file ends inside an open fence (`.claude/skills/commit/SKILL.md`), and it does so only because of F1 — but the mechanism is general.\n\nA guard whose failure mode is \"passes silently\" is the exact defect class the upstream RCA names (`ROOT_CAUSE_ANALYSIS.md:161-168`, \"both failure directions are silent\"), and Phase 5 step 7 of the plan says in terms: do not weaken the scan to make the repo pass.",
    "proposed_fix": "Make the unbalanced case loud rather than lenient. Have `strip_fences` return the blanked text plus the line number of any still-open fence (or raise), and add an assertion in `test_relative_links_resolve` — or a third repo-wide test — that no scanned Markdown file ends inside an open fence, naming the file and the opener's line. Cover it in tests/test_doc_link_contract.py with a fixture string that opens a fence and never closes it. This converts a silent exemption into a red build, which is what the guard is for.",
    "reviewer": "edgecases",
    "reviewers": [
      "edgecases"
    ],
    "merged_from": [
      "F2"
    ],
    "vid": "V10",
    "verdict": "confirmed",
    "verify_evidence": "Code: the loop at tests/test_doc_links.py:52-63 exits with `marker` still bound and line 65 returns `\"\\n\".join(out)` — there is no post-loop check of `marker`, and strip_fences returns only a str (signature line 42), so there is no channel to report an unbalanced document even if one wanted to. Reproduction output: `V10 probe: []` — the dead target `docs/nope.md` after an unclosed fence is invisible to link_targets, with no diagnostic. Repo-wide: `files open at EOF: [('.claude/skills/commit/SKILL.md', 224)]` — exactly one file today, matching the finding, and a control run with a list-aware fence pattern returns `final marker: None` for that file, confirming the finding's point that this instance is downstream of the list-item bug while the silent-tail mechanism is general and independently reachable by any author who omits a closer. `uv run pytest -q` is fully green with that tail unscanned, which is the 'passes silently' failure mode the upstream RCA names ('both failure directions are silent', ROOT_CAUSE_ANALYSIS.md ~:161-168, which I read) and that IMPLEMENTATION_PLAN.md:355 forbids.",
    "verify_ran": "Read strip_fences at tests/test_doc_links.py:42-65 line by line. Ran the finding's exact reproduction — `guard.link_targets(guard.strip_fences('```\\ncode\\n\\n[dead](docs/nope.md)\\n'))` — and then a repo-wide scan replaying the shipped fence state machine over every file guard.markdown_files() returns, printing any file whose marker is still set at EOF and the line that opened it."
  },
  {
    "id": "F3",
    "title": "Phase 7 (the record) was not executed: no IMPLEMENTATION_REPORT.md, and both requests' Index rows and all four status blockquotes still read `planned`",
    "severity": "major",
    "confidence": "high",
    "category": "plan-completeness",
    "location": "requests/bugfix-requests/README.md:51 and :53 (Index rows), requests/bugfix-requests/verify-batching-guard-red-on-arrival/ (no IMPLEMENTATION_REPORT.md)",
    "problem": "`git status --porcelain` lists thirteen modified files and one untracked test. Nothing under `requests/` is touched, and no `IMPLEMENTATION_REPORT.md` exists anywhere in the tree (`Get-ChildItem requests/bugfix-requests -Recurse -File` returns only the pre-existing seven artifacts). The Index still reads `| [doc-link-guard-mismatch](doc-link-guard-mismatch/) | planned |` and `| [verify-batching-guard-red-on-arrival](...) | planned |`, and IMPLEMENTATION_PLAN.md:1 still reads `> **Status:** planned · created 2026-08-17 · decided · next: implement`.\n\nThe plan's files-to-touch checklist names five `requests/` items (`:605-607`) and Phase 7 step 6 is explicit about why the report matters: \"Write the IMPLEMENTATION_REPORT with the before/after guard output pasted verbatim, including Phase 2's deliberately-corrupted-copy runs. A green guard nobody has seen fail is a guard nobody has tested.\" That evidence exists only in this session's scratchpad — I had to regenerate it myself to review the change. Phase 7 acceptance 3 (\"Both requests' Index rows and all four artifact status blockquotes agree\") is unmet on the current tree.\n\nAlso unwritten: Phase 8 step 2's requirement to record the first observed CI node version in the plan's §5 with a `measured <date>` label and run URL — §5 is byte-unchanged.",
    "proposed_fix": "Before handing to `/commit`: write `requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_REPORT.md` containing the before/after guard diagnostics and the three re-broken-fixture runs verbatim; advance the Stage cells at requests/bugfix-requests/README.md:51 and :53 to `fixed`; advance the status blockquotes on both requests' BUGFIX_REQUEST.md and ROOT_CAUSE_ANALYSIS.md and on IMPLEMENTATION_PLAN.md:1; leave the `leak-guard-blind-to-untracked-files` row byte-unchanged. Note that the new IMPLEMENTATION_REPORT.md will be resolved by the bare-token scan, so write it before staging.",
    "reviewer": "edgecases",
    "reviewers": [
      "edgecases"
    ],
    "merged_from": [
      "F3"
    ],
    "vid": "V11",
    "verdict": "confirmed",
    "verify_evidence": "`git status --porcelain` returns exactly 13 ' M' entries plus one '?? tests/test_doc_link_contract.py' — thirteen modified files and one untracked test, as claimed — and none of the 14 is under requests/; `git diff HEAD --stat -- requests/` is empty. The recursive listing of requests/bugfix-requests returns only the pre-existing artifacts; no IMPLEMENTATION_REPORT.md exists (Test-Path -> False). README.md:51 and :53 both still carry Stage `planned`, and IMPLEMENTATION_PLAN.md:1 still reads `> **Status:** planned · created 2026-08-17 · decided · next: implement`. The plan's checklist at :605-607 names the five requests/ items (README rows :51/:53; the primary dir's BUGFIX_REQUEST.md:1, ROOT_CAUSE_ANALYSIS.md:1, this plan's :1, new IMPLEMENTATION_REPORT.md; doc-link-guard-mismatch's two artifacts) — all unticked and none edited. Phase 7 step 6's rationale is quoted correctly at plan :441-443. §5 (:530-575) is byte-unchanged (it lives in requests/, which shows no diff) and contains D1-D8 only, with no `measured <date>` node version or run URL, so Phase 8 step 2's second requirement is unwritten. Fair caveat, which does not change the verdict: that specific item requires an observed CI run, which cannot exist before the branch is pushed, and the plan itself (:469-471) permits Phase 8 to split into a follow-up PR — the unmet Phase 7 items carry no such excuse.",
    "verify_ran": "`git status --porcelain` (counted entries); `git diff HEAD --stat -- requests/`; `Get-ChildItem -Recurse -File requests/bugfix-requests`; read requests/bugfix-requests/README.md lines 43-53; read IMPLEMENTATION_PLAN.md:1 and its §5 (:530-575), Phase 8 step 2 (:478-479) and the files-to-touch checklist (:590-609)."
  },
  {
    "id": "F1",
    "title": "Phase 7 (Record) is entirely undone — no requests/ artifact was touched",
    "severity": "major",
    "confidence": "high",
    "category": "plan-completeness",
    "location": "requests/bugfix-requests/README.md:51 and :53 (Index rows still `planned`); requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md:1",
    "problem": "`git status --porcelain` lists only `.claude/`, `.github/` and `tests/` paths — nothing under `requests/`. Concretely: `requests/bugfix-requests/README.md:53` still reads `| [verify-batching-guard-red-on-arrival](...) | planned |` and `:51` still reads `planned` for `doc-link-guard-mismatch`, even though Phase 5 closed it; the plan's own status blockquote at IMPLEMENTATION_PLAN.md:1 still reads `planned · … · next: implement`; both requests' `BUGFIX_REQUEST.md:1` and `ROOT_CAUSE_ANALYSIS.md:1` still read `diagnosed`; and `requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_REPORT.md` does not exist. Plan Phase 7 acceptance 3 requires 'Both requests' Index rows and all four artifact status blockquotes agree', and the checklist at IMPLEMENTATION_PLAN.md:604-607 lists every one of these. The report is the item the plan calls out most emphatically (step 6: 'A green guard nobody has seen fail is a guard nobody has tested') and it is the only place the deliberately-corrupted-copy runs would be recorded — the evidence I had to re-derive myself because nothing in the tree carries it.",
    "proposed_fix": "Before /commit: write `requests/bugfix-requests/verify-batching-guard-red-on-arrival/IMPLEMENTATION_REPORT.md` with the before/after guard output and the three re-broken-key runs pasted verbatim; advance the Index Stage cells at `requests/bugfix-requests/README.md:51` and `:53` from `planned` to `fixed` (leaving `:52` byte-unchanged); advance the status blockquotes on both requests' `BUGFIX_REQUEST.md`, `ROOT_CAUSE_ANALYSIS.md` and this plan to the track README's terminal word `fixed` (grammar at requests/bugfix-requests/README.md:45), and add the doc-link row's Notes pointer to this plan.",
    "reviewer": "skill-quality",
    "reviewers": [
      "skill-quality"
    ],
    "merged_from": [
      "F1"
    ],
    "vid": "V12",
    "verdict": "confirmed",
    "verify_evidence": "The porcelain claim is exact: the 14 entries are .claude/agents/data-engineer-memory.md, six .claude/skills/ files, .claude/skills/create-implementation-plan/plan_panel.js, .claude/skills/scope-feature/scope_panel.js, .claude/skills/implement-plan/tests/verify_batching_guard.mjs, .github/workflows/ci.yml, tests/test_doc_links.py, tests/test_skill_references.py, and untracked tests/test_doc_link_contract.py — zero requests/ paths. README.md:53 verbatim: `| [verify-batching-guard-red-on-arrival](verify-batching-guard-red-on-arrival/) | planned | …`; :51 likewise `planned` for doc-link-guard-mismatch even though Phase 5 landed (tests/test_doc_links.py is rewritten and tests/test_doc_link_contract.py exists). IMPLEMENTATION_PLAN.md:1 = `> **Status:** planned · created 2026-08-17 · decided · next: implement`. Both requests' BUGFIX_REQUEST.md:1 and ROOT_CAUSE_ANALYSIS.md:1 read `diagnosed`. No IMPLEMENTATION_REPORT.md in the directory listing. The checklist citation is accurate — IMPLEMENTATION_PLAN.md:605 is the Index rows `:51` and `:53`, :606 is `BUGFIX_REQUEST.md:1, ROOT_CAUSE_ANALYSIS.md:1, this plan's :1, new IMPLEMENTATION_REPORT.md`, :607 is doc-link-guard-mismatch's two artifacts; :604 is the memory append. The report's absence is the load-bearing part: Phase 2 acceptance 2-4 (:207-217) required three deliberately-re-broken-copy runs and Phase 7 step 6 required pasting them; nothing in the tree carries that evidence, so it is unreproducible from the record — I had to re-derive the guard's green output myself (`exit=0`, `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` …). Scope correction, not changing the verdict: the title's \"entirely undone\" is an overstatement — Phase 7 step 5's memory append is present (.claude/agents/data-engineer-memory.md, +24 lines, three dated entries with `verified`/`measured` labels); the accurate claim is the subtitle, \"no requests/ artifact was touched\".",
    "verify_ran": "`git status --porcelain` (checked the path prefixes of every entry). Grepped/read requests/bugfix-requests/README.md lines 43-53 with explicit line numbering. Read IMPLEMENTATION_PLAN.md:1, its files-to-touch checklist at :590-609 (specifically :604-607), and Phase 7 steps :420-446. Listed the request directory for IMPLEMENTATION_REPORT.md. Cross-checked the track grammar at requests/bugfix-requests/README.md:45. Independently re-ran the batching guard and the pytest suite so the report's would-be evidence could be compared against reality."
  },
  {
    "id": "F2",
    "title": "\"link titles are exempt too\" — a fourth promise in three skills — is still unimplemented, so the guard the plan claims to have fixed still rejects documented content",
    "severity": "major",
    "confidence": "high",
    "category": "acceptance-gap",
    "location": ".claude/skills/create-implementation-plan/SKILL.md:256 (identical text at .claude/skills/diagnose-bug/SKILL.md:184 and .claude/skills/make-bugfix-request/SKILL.md:204); implementation at tests/test_doc_links.py:20 and :73-106",
    "problem": "Three skills promise authors: \"Citations may carry a `file.py:123` suffix; `var/` targets **and link titles** are exempt too.\" Phase 5 implemented four promises (fence, line suffix, var/, bare tokens) and left the fifth. Measured: `LINK` at tests/test_doc_links.py:20 (`\\[[^\\]]*\\]\\(([^)]+)\\)`) captures the whole parenthetical, so for `[the ADR](../docs/decisions/0001-no-write-back.md \"ADR 0001\")` `link_targets` returns `../docs/decisions/0001-no-write-back.md \"ADR 0001\"`, and `resolve_target` (which strips only `#fragment` at :87 and a line suffix at :88) resolves it to a path ending in ` \"ADR 0001\"` — exists: False. I ran this: the guard reports it as a broken link. The plan's Phase 5 step 8 said to verify the promise prose against the new behaviour by reading `.claude/skills/make-feature-request/SKILL.md:245-250` — which happens to be the ONE of the five copies that omits the link-title clause, which is exactly why it was missed. Closing `doc-link-guard-mismatch` on this basis reinstates the defect the request is about: an author who follows the documentation gets a red build.",
    "proposed_fix": "In `resolve_target` (tests/test_doc_links.py:73), strip an optional CommonMark link title before resolving — split the captured target on unescaped whitespace and keep the first token when the remainder is wrapped in `\"…\"`, `'…'` or `(…)`. Add two cases to tests/test_doc_link_contract.py under a 'Promise 5' heading: a titled link to a live file resolves, and a titled link to a dead file is still reported (so the strip cannot launder a broken path, mirroring test_a_genuinely_dead_target_is_still_dead_with_a_suffix at :88). If the operator prefers not to widen scope, the alternative is to delete the ' and link titles' clause from the three SKILL.md lines — but then say so in the report, because the promise is currently false.",
    "reviewer": "skill-quality",
    "reviewers": [
      "skill-quality"
    ],
    "merged_from": [
      "F2"
    ],
    "vid": "V13",
    "verdict": "confirmed",
    "verify_evidence": "Measured with a target that genuinely exists (docs/decisions/0001-read-only-no-write-back.md): TITLED `[the ADR](docs/decisions/0001-read-only-no-write-back.md \"ADR 0001\")` → link_targets returns `'docs/decisions/0001-read-only-no-write-back.md \"ADR 0001\"'`, resolve_target returns a path ending in ` \"ADR 0001\"`, `exists= False`, and the simulated test_relative_links_resolve body reports it as broken. CONTROL (same file, no title) → `exists= True`. LINK at tests/test_doc_links.py:20 captures the whole parenthetical and resolve_target at :87-88 strips only `#fragment` and LINE_SUFFIX, never a title. The promise is live and pre-existing, not something the diff introduced: `git grep` finds the identical clause '`file.py:123` suffix; `var/` targets and link titles are exempt too.' at create-implementation-plan/SKILL.md:256, diagnose-bug/SKILL.md:184, make-bugfix-request/SKILL.md:204, and `git diff HEAD` over those three files contains no 'link titles' line — so Phase 5 shipped four of five promises. The finding's explanation of the miss is exact: make-feature-request/SKILL.md:250 (the one copy Phase 5 step 8 at plan :356-358 told the implementer to verify against) reads '...`var/` targets are exempt too.' with the link-title clause absent. tests/test_doc_link_contract.py has no link-title case among its eleven tests.",
    "verify_ran": "Ran the shipped `link_targets`/`resolve_target` from tests/test_doc_links.py on a titled link and an untitled control pointing at the SAME real file; `git grep -n \"link titles\" -- .claude/skills/`; `git diff HEAD -- <the three skills> | Select-String \"link titles\"`; printed .claude/skills/make-feature-request/SKILL.md:243-252; listed every test in tests/test_doc_link_contract.py."
  },
  {
    "id": "F1",
    "title": "strip_fences misses a fence opened on a list-item line, silently exempting 64 live lines of commit/SKILL.md",
    "severity": "blocker",
    "confidence": "high",
    "category": "correctness",
    "location": "tests/test_doc_links.py:25",
    "problem": "FENCE = r\"^\\s*(?:>\\s*)*(`{3,}|~{3,})\" allows only whitespace and blockquote markers before the fence, so it does not match a fence opened inside a list item. `.claude/skills/commit/SKILL.md:189` is literally `2. ``` ` — a CommonMark fence opening as list-item content. The tracker misses that opener, then treats the CLOSER at `:191` as an opener, and never re-syncs: `:222` closes the phantom block and `:224` opens another that runs to EOF. I measured it: the shipped tracker blanks 92 lines of that file where a list-aware tracker blanks 31 — 64 LIVE lines (192-258) are silently treated as fenced, and the file's fence state is still OPEN at EOF. Proof it hides real defects, not just theory: injecting `[the missing doc](docs/definitely-not-here.md)` plus the bare token `requests/feature-r
```

## Reviewer summaries

### acceptance

~~~
Acceptance-criteria audit of the uncommitted `verify-batching-guard-red-on-arrival` implementation, verified by execution rather than reading. THE CODE HALF IS SOLID AND I PROVED IT BY RUNNING IT: the batching guard now exits 0 with the four diagnostic lines the plan pinned, byte-for-byte; `acceptance_panel.js` is absent from `git diff --stat`; both RCA repro tests are green; the full gate is `187 passed, 62 deselected` with ruff, ruff-format and mypy-strict clean and all five `.mjs` guards at exit 0. I independently re-proved the three "prove it bites" demonstrations the plan demanded but the implementer left no record of: three scratchpad copies of the guard with one fixture key re-broken each (`data-contract`, `extraction`, and the valid-but-unrequested `builder`) all exit 1 with one honest `fixture: … orphaned lens …` line and NO `[cap+dedupe]` line and no cascading `dedupe:`/`coverage:` failures — exactly the Phase-2 acceptance shape; the widened reference guard goes RED on the pre-fix panel scripts naming `plan_panel.js:147` (plus two instances the plan did not know about); and the two repo-wide link tests still go red on a synthetic dead link and a synthetic dead `requests/` token. Nothing touches the parser, the game, `.env`, dbt or any tracked game data — ADR 0001/0005/0006 have no surface here and were not violated. THE RECORD HALF IS MISSING ENTIRELY. Phase 7 was not executed: `git status --porcelain -- requests/` is empty, so no `IMPLEMENTATION_REPORT.md` exists, neither request's Index row moved off `planned`, and none of the four artifact status blockquotes advanced. For a bugfix run the track contract's "done" is the record as well as the fix, and the required 'red repro now green + regression test present' ledger row does not exist anywhere in the tree. TWO REAL DEFECTS IN THE NEW GUARD CODE, both found by probing rather than by reading: `strip_fences` mis-parses a fence opened on a list-item line (`.claude/skills/commit/SKILL.md:189`), flipping parity so that 75 non-blank lines — 29% of a live skill document, including its whole "What good looks like" prose section — are silently blanked out of BOTH link checks; and the undocumented `own_dir` exemption in `bare_request_tokens` suppresses exactly ONE token in the entire repo while blanket-exempting every dead sibling-artifact pointer (a typo'd `ROOT_CAUSE_ANALYSES.md` inside the very plan that cites its own RCA comes back clean). Both are the "green guard that has quietly stopped checking" failure class this whole request exists to eliminate. Finally, the nine `/commit`-gated phases were collapsed into one uncommitted blob, so every per-phase delta criterion (`1 failed, 171 passed`, "exactly one file in git diff --stat", "seven files changed") is now permanently unverifiable.
~~~

### fidelity

~~~
PLAN-FIDELITY & COMPLETENESS review of the uncommitted `verify-batching-guard-red-on-arrival` implementation, grounded by running everything.

**What I ran (real output, on the working tree):**
- `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` → **exit 0**, with the four diagnostic lines byte-matching Phase 1 acceptance #1 (`raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`, `verifiers=4/5 unverified=3/9`, `b1Calls=2`, `cap=2 batches=2 unverified=0/9`).
- The four sibling guards → all exit 0.
- `uv run pytest -m "not gamedata"` → **187 passed, 62 deselected, 0 failed** (baseline was `2 failed, 170 passed`; the delta reconciles exactly: 170+2 flipped +14 new contract tests +1 new bare-token test).
- `uv run ruff check .` / `ruff format --check .` / `uv run mypy` (strict over `src` and `tests`) → all clean; the new `tests/test_doc_link_contract.py` and rewritten `tests/test_doc_links.py` pass strict individually.
- **Phase 2 non-vacuity, proved by scratchpad copies with `HERE` repointed at the tracked skill dir** (all three re-break directions the plan demanded): re-breaking `warehouse`→`data-contract`, `parser`→`extraction`, and `parser`→`builder` each exits 1 with a single named `fixture: FINDINGS_BY_LENS has an orphaned lens '<key>' …` line, and **the `[cap+dedupe]` line and every `dedupe:`/`coverage:` failure are absent** — exactly the assertion the plan's §9 correction table specified. The unmodified control copy exits 0.
- Repo-wide instrumentation of the new link guard: 393 link targets still resolved-and-existence-checked (394 before the rewrite), 209 bare `requests/` tokens examined across 82 markdown files — the guard is not vacuous.
- Negative check: `acceptance_panel.js` is absent from `git status --porcelain`; `ops/branch-protection.json` unchanged; `git grep -E 'data-contract|extraction' -- .claude/skills/implement-plan/`, `git grep test_request_links -- .claude/skills/`, `git grep test_extract_pagination -- .claude/skills/` and `git grep docs/data-sources.md -- .claude/skills/` all return **zero hits**. Phase 4's `root-cause` grep returns exactly the four legitimate survivors the plan enumerated. The Phase 3 replacement example is real and correctly placed: `test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key` exists at `tests/test_parse_world.py:179`, above the first `@pytest.mark.gamedata` at `:513`, and its `3058 → 2600` figures are this repo's own measured numbers (`requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:362`).

**Verdict.** Phases 1–6 and 8's code are implemented faithfully and verifiably; the bugfix track's acceptance contract (red repro green + regression guard left behind + nothing regressed) is **met**. The failures are at the edges: **Phase 7 (Record) is essentially unbuilt** — no status blockquote moved, neither Index row advanced, no `IMPLEMENTATION_REPORT.md`, no D5 intake — and Phase 5 shipped an **exemption the plan never authorized and no skill documents**, which is the one place the implementation quietly loosened a guard to make the repo pass. Nothing here touches the parser, a save, `.env`, or game data; ADR 0001/0006 have no surface and were not violated.
~~~

### correctness

~~~
Ran the whole contract myself rather than trusting the diff. Verified GREEN: `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 with exactly the four pinned diagnostic lines (`raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`, etc.); `uv run pytest -m "not gamedata"` = 187 passed, 62 deselected, zero failures (baseline was 2 failed/170 passed); ruff check, ruff format --check and mypy strict all clean; all four sibling `.mjs` guards exit 0; `acceptance_panel.js` is absent from `git status`/`git diff` (D6 honored). I also proved the new orphaned-lens check BITES rather than passing vacuously: re-keying `warehouse`→`sibling-lens`, `parser`→`extraction`, and `parser`→`builder` (a panel-valid but unrequested lens) on an in-memory copy each exits 1 with the single fixture line and NO `[cap+dedupe]` line and no cascading `dedupe:`/`coverage:` failures — exactly Phase 2 acceptance 2-4. The bare-token scan is not vacuous either: 209 tokens and 397 link targets scanned repo-wide. The bugfix track's contract (red repro green + regression guard left behind + nothing regressed) is MET. Project-convention correctness: nothing here touches the parser, the save, ratings, player keys or as-of resolution — no ADR 0001/0006 surface, no fixed-offset read, no hardcoded path (I leak-scanned the untracked `tests/test_doc_link_contract.py`, which `test_no_leaks.py` cannot see because it enumerates via `git ls-files`; it is clean). The real defects are in the newly written link guard, which silently stops checking part of the repo, plus an unfinished Phase 7.
~~~

### edgecases

~~~
TEST & EDGE-CASE lens. I ran the whole gate myself rather than trusting the diff: `uv run pytest -m "not gamedata"` → **187 passed, 62 deselected**; `ruff check` / `ruff format --check` / `mypy` all clean; all five `.mjs` guards exit 0, including `verify_batching_guard.mjs`, which now prints the four pinned diagnostic lines the RCA predicted (`raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`, …). I independently executed the plan's Phase 2 "prove it bites" step that no automated test covers: I copied the guard to the scratchpad, repointed `PANEL` at the tracked `acceptance_panel.js`, and re-broke each fixture key in turn — `warehouse`→`'data-contract'`, `parser`→`extraction`, and `warehouse`→`builder` (a real panel lens outside this run's roster). All three exit 1 with a single named `fixture: … orphaned lens '<key>' …` line, and in all three the `[cap+dedupe]` line and every `dedupe:`/`coverage:` failure are **absent** — exactly the non-cascading behaviour Phase 2 acceptance 2–4 demands. `acceptance_panel.js` is absent from `git diff --stat` (D6 honoured). The Phase 1/3/4/6 acceptance greps are all clean (`data-contract|extraction` in `implement-plan/` → 0; `test_request_links` in `.claude/skills/` → 0; `test_extract_pagination` → 0; `root-cause` → only the two frontmatter pipeline descriptions and the deliberately-preserved `next: root-cause` slot; `data-sources` → only the memory entry describing it). The RCA's acceptance contract (red repro green + regression guard left behind + nothing regresses) is **met**. This change touches no parser, no dbt model, no `.env` path and no save file, so the ADR-0001/fixed-offset/players.csv conventions have no surface here — correctly, the diff does not pad them in. Where the implementation is genuinely weak is the *new* Phase 5 code: the fence pre-pass is the one piece with no adversarial test, and it is broken in a way that silently switches the guard OFF over 64 live lines of a tracked file — the precise "quietly wrong guard" failure this whole request exists to eliminate. Phase 7's record deliverables are also simply absent from the tree.
~~~

### skill-quality

~~~
SKILL-QUALITY lens, adversarial, everything re-run locally rather than taken on trust. What I verified by execution: `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` now exits 0 with exactly the four diagnostic lines the plan pins (`raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` etc.); all four sibling `.mjs` guards exit 0; `uv run pytest -m "not gamedata"` = 187 passed, 0 failed (baseline was 2 failed/170 passed; +15 net new tests, arithmetic checks out); ruff, ruff format --check and mypy strict all clean; `acceptance_panel.js` is absent from `git diff HEAD --name-only` (D6 honoured) and `git grep data-contract|extraction` over `.claude/skills/implement-plan/` returns zero. I proved the two NEW guards actually bite rather than passing vacuously: I re-ran the batching guard from an in-memory copy with `HERE` repointed at the tracked skill dir and each fixture key broken in turn (`data-contract`, `extraction`, and the panel-valid-but-out-of-roster `builder`) — all three exit 1 with the single orphaned-lens line and NO `[cap+dedupe]` line and no cascading dedupe/coverage failures, exactly as Phase 2 acceptance 2–4 demand. I replayed the widened reference scan against the pre-fix `git show HEAD:` blobs and confirmed it goes red naming `plan_panel.js:147`, `plan_panel.js:164` and `scope_panel.js:125` — all three now fixed. I measured that fence-stripping hides zero genuinely-broken links repo-wide, and that the new own-directory exemption suppresses exactly one token. Read-only throughout: no Edit/Write, no state-changing git, nothing written to var/ or the game. Verdict: the RCA's acceptance contract (red repro green + regression guard left behind + nothing regressed) IS met at the code level and the engineering is unusually careful. Two things stop it being done: the entire Phase 7 record is missing (no requests/ file touched at all — no IMPLEMENTATION_REPORT.md, both Index rows and all four status blockquotes still say `planned`), and Phase 5 closes `doc-link-guard-mismatch` while a fourth documented promise — "link titles are exempt too", stated verbatim in three skills — is still unimplemented and still turns the build red, which is the same defect class the request exists to eliminate.
~~~

### parser

~~~
PARSER-INTEGRITY LENS: NOT APPLICABLE, verified rather than assumed. `git diff HEAD --stat -- src/` is empty — no file under `src/ootp_ai/` changed, and the full diff contains no `open(`, `writeFileSync`, `Set-Content`, `Out-File`, `.dat`, `.lg` or savegame token. So all six parser checks are vacuously clean: no fixed-offset read introduced (no parsing code at all), no new field claimed so no ground-truth obligation, no code path opens a save for writing (ADR 0001 intact), the version guard is untouched, no snapshot is written or mutated, and no OOTP-shipped data enters git (`test_no_leaks.py` patterns run clean over all five changed/new files, including the untracked `tests/test_doc_link_contract.py` that the leak guard cannot yet see because it enumerates via `git ls-files`). The change is entirely `.claude/skills/`, two pytest modules, one CI job and one agent-memory append — exactly the surface §2 of the plan predicted.

VERIFICATION I RAN: batching guard exit 0 with the four pinned diagnostic lines verbatim; `uv run pytest -m "not gamedata"` = 187 passed / 62 deselected / 0 failed (baseline 2 failed, 170 passed); ruff, ruff format --check, mypy all exit 0; four sibling .mjs guards exit 0; `acceptance_panel.js` absent from the diff (D6 honored, byte-untouched). I reproduced Phase 2's non-vacuity myself on three scratchpad copies with `HERE` repointed at the tracked skill dir — re-breaking `warehouse`→`data-contract`, `parser`→`extraction`, and `parser`→`builder` each exits 1 with one orphaned-lens line, the `[cap+dedupe]` line and all `dedupe:`/`coverage:` failures absent, exactly as Phase 2 acceptance 2-4 demand. I reproduced Phase 6's pre-fix RED by running the widened detector over HEAD's panel scripts: three hits (`plan_panel.js:147`, `plan_panel.js:164`, `scope_panel.js:125`), all now fixed. Old-vs-new link-guard semantics over the whole tree: 0 dead links before, 0 after, so the guard was NOT loosened to launder an existing failure.

THE UPSTREAM RCA CONTRACT IS MET: the red repro (`tests/test_skill_references.py`, 2 tests) is green, the regression guards are left behind and were seen to fail, and nothing else regressed. THE PLAN'S CONTRACT IS NOT: Phase 7 produced no diff at all, and the new fence pre-pass has a proven silent-exemption hole that recreates the exact "a guard that quietly checks nothing" failure this request exists to eliminate.
~~~

### infra-cost

~~~
CI / secrets / repo-hygiene lens, verified by running everything rather than reading step names. **The core fix is real and I proved it**: `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` now exits 0 with exactly the four diagnostic lines the plan pinned (`raw=11 deduped=9 batches=4/4 verifiers=5/5`), all four sibling guards exit 0, `uv run pytest -m "not gamedata"` is `187 passed, 62 deselected` (baseline was `2 failed, 170 passed`), and ruff / ruff-format / mypy-strict are clean. `acceptance_panel.js` is byte-untouched (D6 honoured) — confirmed by `git diff HEAD --stat` on that path returning empty. I independently proved Phase 2's new orphaned-lens check BITES: by loading three in-memory-corrupted copies of the guard (no files written) I got exit 1 for an invented key, for `extraction`, and for `builder` (a real panel lens outside this run's roster), each printing one honest `fixture: ... orphaned lens ...` line with the `[cap+dedupe]` line and all `dedupe:`/`coverage:` cascades absent — exactly Phase 2 acceptance 2-4. I also confirmed Phase 6's widening genuinely bites: replaying the new `REPO_REFERENCE` regex against `git show HEAD:` content flags `plan_panel.js:147`, `plan_panel.js:164` and `scope_panel.js:125` for the phantom `docs/data-sources.md`, all three now fixed, and `scannable_text` blanks exactly lines 48-70 of the batching guard while preserving the line count (331 -> 331).

**On my specialist axes, the diff is clean.** SECRETS: no credential, token, account id, email or machine path enters any file; `tests/test_no_leaks.py` passes, and because it enumerates via `git ls-files` it is blind to the one untracked file (`tests/test_doc_link_contract.py`), so I ran its `PATTERNS` over that file by hand — zero hits. `.env` is still ignored (`.gitignore:4`). GAME DATA: nothing tracked is OOTP IP; the diff is `.md`/`.py`/`.js`/`.mjs`/`.yml` only. GITIGNORE: `.gitignore` is byte-unchanged and `git check-ignore -v var/anything.dat` still resolves to `.gitignore:18:var/`; `tests/test_repo_structure.py` passes. CI INTEGRITY: the new `Skill guards (node)` step is a step on the *existing* `quality` job, uses `run: |` with `set -euo pipefail`, names all five guards by explicit path (no glob that could shrink to zero), swallows no exit code, and requires no OOTP install — nothing belongs behind the `gamedata` marker. BRANCH PROTECTION: the job display name `Lint, types, tests` (`.github/workflows/ci.yml:17`) is unchanged and `ops/branch-protection.json` is byte-unchanged, so no rename trap. REPRODUCIBILITY: `pyproject.toml` and `uv.lock` are both untouched (no Python dep added), `actions/setup-node@v4` pins `node-version: '22'`, and `.github/dependabot.yml` already covers `github-actions` so it will be bumped. I grepped the panels and guards for Node-24-only APIs (`Object.groupBy`, `Array.fromAsync`, `.toSorted`, `Promise.withResolvers`, import attributes) — zero hits, so node 22 in CI vs node 24 locally is not a divergence risk.

**What is NOT done.** Phase 7's record is missing almost entirely, and Phase 5 shipped an undocumented loosening of the very scan it was adding. Details below. Everything I assert has a command output or a file:line behind it; the one thing I could not verify is the in-CI behaviour of the new step, because no CI run exists yet, and I say so rather than claiming it.
~~~

## Independent verifier ledger

```json
[
  {
    "id": "U1",
    "criterion": "RCA contract: the committed red repro goes GREEN",
    "source": "ROOT_CAUSE_ANALYSIS.md:26-53 (Reproduction (red))",
    "verdict": "met",
    "evidence": "`uv run pytest tests/test_agent_contract.py::test_memory_entries_carry_an_epistemic_label tests/test_skill_references.py tests/test_doc_links.py tests/test_doc_link_contract.py -q` -> `...................  [100%]` (19 passed, 0 failed). Both repro tests in tests/test_skill_references.py pass. I independently confirmed the baseline was genuinely red: `git grep -n \"test_request_links|test_extract_pagination\" HEAD -- .claude/skills/` returns exactly the 7 lines quoted at ROOT_CAUSE_ANALYSIS.md:40-46; the same grep on the working tree returns zero hits (exit 1).",
    "how_checked": "execution (targeted pytest + git grep against the HEAD blob and the working tree)"
  },
  {
    "id": "U1b",
    "criterion": "RCA contract: the original human-readable symptom — `node verify_batching_guard.mjs` exit 1 — is resolved",
    "source": "ROOT_CAUSE_ANALYSIS.md:60-62",
    "verdict": "met",
    "evidence": "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` -> EXIT=0, printing exactly the four lines the plan pinned: `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`, `[dead-batch] verifiers=4/5 unverified=3/9 note=\"verify:b1 (3 findings left unverified)\"`, `[rubberstmp] b1Calls=2 verifiers=4/5 unverified=3`, `[verifyCap ] cap=2 batches=2 unverified=0/9`, then GREEN.",
    "how_checked": "execution"
  },
  {
    "id": "U2",
    "criterion": "RCA contract: a regression test is left behind, with its assertions not weakened to fit the fix",
    "source": "ROOT_CAUSE_ANALYSIS.md:26-58 + IMPLEMENTATION_PLAN.md:600",
    "verdict": "met",
    "evidence": "tests/test_skill_references.py retains both tests and is STRENGTHENED: REPO_REFERENCE (`:36`) widens the token class from `tests/test_*.py` to also cover `docs/*.md`, and skill_documents() (`:49-58`) widens the glob from `*.md` to `*.md`+`*.js`+`*.mjs` (16 files: 8 .md, 3 .js, 5 .mjs). The one new exclusion, scannable_text() (`:61-76`), blanks only 23 of the guard's 331 lines and cannot be a regression because .mjs was not scanned at all at baseline. Independently: the guard now also carries its own equivalent check in-process (verify_batching_guard.mjs:196-214).",
    "how_checked": "execution (python probe measuring blanked-line count = 23, files scanned = 16, and confirming `test_extract_client.py` is blanked while the RUN: line is still scanned) + static read of the full module"
  },
  {
    "id": "U3",
    "criterion": "RCA contract: nothing else regresses — no audit or test regresses",
    "source": "requests/bugfix-requests/README.md:24-26 (definition of done)",
    "verdict": "met",
    "evidence": "`uv run pytest -m \"not gamedata\"` -> `187 passed, 62 deselected in 1.06s` (baseline per plan: 2 failed, 170 passed, 62 deselected). `uv run ruff check .` -> `All checks passed!` (exit 0). `uv run ruff format --check .` -> `119 files already formatted` (exit 0). `uv run mypy` -> `Success: no issues found in 39 source files` (exit 0). All five .mjs guards exit 0 (A=0 B=0 C=0 D=0 for the siblings, plus the batching guard).",
    "how_checked": "execution"
  },
  {
    "id": "P0",
    "criterion": "Phase 0: the guard's RED output, pytest tally, tool versions and branch name are written down; all four sibling guards exit 0; tree clean",
    "source": "plan-phase-0",
    "verdict": "not-verifiable",
    "evidence": "No working notes and no IMPLEMENTATION_REPORT.md exist in the tree (`Get-ChildItem -Recurse requests/bugfix-requests` lists only BUGFIX_REQUEST.md, ROOT_CAUSE_ANALYSIS.md, IMPLEMENTATION_PLAN.md and reviews/ for this slug), so the baseline record cannot be inspected. What I could verify independently: node v24.15.0 and uv 0.12.3 are present; the four sibling guards exit 0 now; and the HEAD state that produced the claimed 2-failure baseline is reproducible via git grep. The tree is NOT clean (that is expected — the work is uncommitted).",
    "how_checked": "static (directory listing) + execution (node --version, uv --version, four sibling guards)"
  },
  {
    "id": "P1a",
    "criterion": "Phase 1: the batching guard exits 0 with exactly the four specified diagnostic lines",
    "source": "plan-phase-1 acceptance 1",
    "verdict": "met",
    "evidence": "Exit 0; the four lines match the plan's text character-for-character. See U1b.",
    "how_checked": "execution"
  },
  {
    "id": "P1b",
    "criterion": "Phase 1: the fixture keys are re-keyed to warehouse/parser with formatting and delimiters preserved, and `git grep data-contract|extraction` in implement-plan/ returns zero hits (catches a missed comment at :150)",
    "source": "plan-phase-1 acceptance 2 and 5",
    "verdict": "met",
    "evidence": "`git grep -n \"data-contract|extraction\" -- .claude/skills/implement-plan/` exits 1 with no output. verify_batching_guard.mjs:61 is `  warehouse: [` and `:65` is `  parser: [` — two leading spaces, unquoted, `const FINDINGS_BY_LENS = {` and the column-0 `}` intact (which matters: test_skill_references.py:44 FIXTURE_LENS carves on those literal delimiters, and it passes). The teaching comment at `:157` now reads `// -> warehouse + parser + skill-quality specialists`. `'skill-quality'` keeps its quotes at `:68`.",
    "how_checked": "execution (git grep, exit 1) + static read of verify_batching_guard.mjs:47-71 and :154-160"
  },
  {
    "id": "P1c",
    "criterion": "Phase 1: acceptance_panel.js is byte-untouched and never appears in git diff --stat (the plan's D6 and the byte-level negative check)",
    "source": "plan-phase-1 acceptance 4 / §4 channel 4 / D6",
    "verdict": "met",
    "evidence": "`git diff HEAD --stat -- .claude/skills/implement-plan/acceptance_panel.js` produces no output. The file is absent from the full 13-file `git diff HEAD --stat` and from `git status --porcelain`.",
    "how_checked": "execution"
  },
  {
    "id": "P1d",
    "criterion": "Phase 1: phase isolation — `git diff --stat` lists exactly one file, and the intermediate tally is exactly `1 failed, 171 passed, 62 deselected`",
    "source": "plan-phase-1 acceptance 3 and 4",
    "verdict": "unmet",
    "evidence": "All nine phases sit in a single uncommitted working-tree state: `git diff HEAD --stat` lists 13 files plus one untracked (tests/test_doc_link_contract.py), and `git log --oneline -8` shows no commit after a656acb 'Plan the ported-guard repair'. The plan states at :85-87 that each phase ends at a /commit-gated checkpoint and that 'Phases 1 and 3 must not be merged'. The intermediate 1-failed state is therefore not reconstructible after the fact. Substantively harmless — the end state is correct and I verified the two fixes are independent by other means — but the phase-independence proof the plan asked for does not exist.",
    "how_checked": "execution (git diff HEAD --stat, git status --porcelain, git log)"
  },
  {
    "id": "P2a",
    "criterion": "Phase 2: the guard still exits 0 with the same four diagnostic lines — the new check is inert on a correct tree",
    "source": "plan-phase-2 acceptance 1",
    "verdict": "met",
    "evidence": "Exit 0, four lines unchanged from the RCA's decisive-experiment output at ROOT_CAUSE_ANALYSIS.md:106-109. The check sits in Scenario 1's block immediately after `const r = await runPanel(...)` and before the cap/dedupe checks (verify_batching_guard.mjs:196-219), exactly where D7 requires — not inside the stub, so safeAgent cannot swallow it.",
    "how_checked": "execution + static read of verify_batching_guard.mjs:188-222"
  },
  {
    "id": "P2b",
    "criterion": "Phase 2: PROVE IT BITES — re-break one fixture key, confirm exit 1, and confirm the `[cap+dedupe]` line and every `dedupe:`/`coverage:` failure are ABSENT (the run exits before the counting assertions)",
    "source": "plan-phase-2 acceptance 2",
    "verdict": "met",
    "evidence": "I re-broke `warehouse:` -> `notalens:` in memory (data-URL module re-import with HERE repointed at the real tracked skill dir; no file written). Output was exit 1 and a SINGLE line: `fixture: FINDINGS_BY_LENS has an orphaned lens 'notalens' that the panel never requests — its findings are silently dropped. The panel asked for: acceptance, correctness, edgecases, fidelity, parser, skill-quality, warehouse`. No `[cap+dedupe]` line, no dedupe:/coverage: failures — exactly the property the plan specified instead of the vacuous `raw=8` assertion. As a bonus this measurement independently confirms the header's disputed '7-lens roster' claim: the panel requests exactly 7.",
    "how_checked": "execution (in-memory re-break, no file modified)"
  },
  {
    "id": "P2c",
    "criterion": "Phase 2: repeat for the OTHER key — both, not one",
    "source": "plan-phase-2 acceptance 3",
    "verdict": "met",
    "evidence": "Re-broke `parser:` -> `ingest:`: exit 1, single line `fixture: FINDINGS_BY_LENS has an orphaned lens 'ingest' that the panel never requests...`, again with no [cap+dedupe] line and no cascade.",
    "how_checked": "execution (second in-memory re-break)"
  },
  {
    "id": "P2d",
    "criterion": "Phase 2: repeat with a key VALID in the panel but outside this run's roster (e.g. `builder:`) — the direction the Python test cannot see",
    "source": "plan-phase-2 acceptance 4",
    "verdict": "met",
    "evidence": "Re-keyed `parser:` -> `builder:` (a real SPEC_DEFS lens that AREA_TO_SPEC does not map for touchedAreas ['transform','src','skills']): exit 1 via the same assertion, `orphaned lens 'builder' that the panel never requests`. This is the direction test_skill_references.py structurally cannot catch, and it is covered.",
    "how_checked": "execution (third in-memory re-break)"
  },
  {
    "id": "P2e",
    "criterion": "Phase 2: guard against a vacuous pass — an empty derived request Set must itself be a failure; and one RED path via reportRedAndExit()",
    "source": "plan-phase-2 steps 4-5",
    "verdict": "met",
    "evidence": "I forced the branch by replacing the `calls.filter(...)` expression with `[]` in memory: exit 1 with `fixture: the panel requested NO review lenses — the harness is broken, not the fixture`. The single RED formatter now lives in `reportRedAndExit()` (verify_batching_guard.mjs:192-196) and is called from both the fixture check (`:219`) and the tail (`:327`) — the tail's three inlined lines are gone in the diff. The `RUN:` line at `:33` is unchanged, so .claude/skills/implement-plan/SKILL.md:309's verbatim quote still resolves (verified by Select-String).",
    "how_checked": "execution (forced-branch re-run + Select-String on SKILL.md:309) + static read of the diff"
  },
  {
    "id": "P2f",
    "criterion": "Phase 2: no scratchpad absolute path reaches a tracked file (tests/test_no_leaks.py:25 fails the build on a Windows drive path)",
    "source": "plan-phase-2 acceptance 5 / Conventions",
    "verdict": "met",
    "evidence": "I wrote NO files at all — every re-break ran through an in-memory data: URL import. Applying test_no_leaks.py's own PATTERNS directly to the untracked tests/test_doc_link_contract.py (which the leak guard is blind to until staged, per the known leak-guard defect) returned `leaks in the untracked new test file: []`. test_no_leaks.py's two tests pass in the full run.",
    "how_checked": "execution (python probe importing test_no_leaks.PATTERNS and applying them to the untracked file)"
  },
  {
    "id": "P3a",
    "criterion": "Phase 3: `git grep test_request_links` and `test_extract_pagination` in .claude/skills/ return ZERO hits, with the legitimate survivors elsewhere untouched",
    "source": "plan-phase-3 acceptance 3",
    "verdict": "met",
    "evidence": "`git grep -n \"test_request_links|test_extract_pagination\" -- .claude/skills/` exits 1 with no output. All six reference sites are repointed at tests/test_doc_links.py (commit/SKILL.md:104, update-docs/SKILL.md:56, diagnose-bug/SKILL.md:176, make-bugfix-request/SKILL.md:199, make-feature-request/SKILL.md:246, create-implementation-plan/SKILL.md:251) — matching the HEAD grep line-for-line. The surrounding promise prose is byte-unchanged in every case, per D1.",
    "how_checked": "execution (git grep on tree and on HEAD) + line-by-line read of `git diff HEAD -- .claude/skills/*/SKILL.md`"
  },
  {
    "id": "P3b",
    "criterion": "Phase 3: the pagination worked example is re-grounded on a test that EXISTS and sits above the gamedata boundary, so the template's `uv run pytest` stays runnable",
    "source": "plan-phase-3 step 3",
    "verdict": "met",
    "evidence": "diagnose-bug/SKILL.md now cites `tests/test_parse_world.py::test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key`. I ran that exact selector: `. [100%]` — it exists and passes. It is defined at tests/test_parse_world.py:179; the first `@pytest.mark.gamedata` in that module is at :513, so it is above the boundary and runs in CI. The NBA-shaped '1230 games' number is gone. Critically, the replacement names a real file even though it sits inside a fenced block — which is what test_skill_references.py:32's fence-unaware line scan requires.",
    "how_checked": "execution (uv run pytest on the exact selector; Select-String for the gamedata marks)"
  },
  {
    "id": "P3c",
    "criterion": "Phase 3: the repro module's docstrings move to past tense while the two assertions and their regexes are NOT weakened",
    "source": "plan-phase-3 step 4 / files-to-touch: 'Never weaken its two assertions'",
    "verdict": "met",
    "evidence": "tests/test_skill_references.py:71-79 now reads 'Six skills USED TO instruct... Repointed 2026-08-17; this test is what keeps them pointed at files that exist', and :119-125 'Re-keyed 2026-08-17'. The assertions are widened, never narrowed (see U2). The one-directionality note survives at :127-128. One deviation: the test was RENAMED test_every_test_file_a_skill_names_exists -> test_every_repo_path_a_skill_names_exists, which leaves the selector quoted at ROOT_CAUSE_ANALYSIS.md:38 stale.",
    "how_checked": "static (read the full module and the diff hunk)"
  },
  {
    "id": "P3d",
    "criterion": "Phase 3: `uv run pytest tests/test_skill_references.py` -> 2 passed, and the whole suite has zero failures",
    "source": "plan-phase-3 acceptance 1, 2, 4",
    "verdict": "met",
    "evidence": "Full suite `187 passed, 62 deselected, 0 failed`. Targeted run of test_skill_references.py + test_doc_links.py + test_doc_link_contract.py + the memory-label test: 19 passed. The plan predicted `172 passed` at this phase; the delta to 187 is exactly the 15 tests Phase 5 added (14 in test_doc_link_contract.py + test_bare_request_tokens_resolve), which reconciles.",
    "how_checked": "execution"
  },
  {
    "id": "P4",
    "criterion": "Phase 4: the bugfix stage word becomes `diagnosed` at seven sites; grepping .claude/skills/ for `root-cause` returns ONLY the two frontmatter pipeline descriptions, the `next:` slot, and genuine prose; both track READMEs byte-unchanged",
    "source": "plan-phase-4 acceptance 1 and 3",
    "verdict": "met",
    "evidence": "`git grep -n root-cause -- .claude/skills/` returns exactly 4 lines, all sanctioned: diagnose-bug/SKILL.md:7 (frontmatter pipeline), make-bugfix-request/SKILL.md:5 ('root-cause analysis' prose) and :6 (frontmatter pipeline), and :130 (`next: root-cause`, which the plan explicitly says to leave alone). The seven corrected sites are visible in the diff: diagnose-bug/SKILL.md :97/:107/:150 and create-implementation-plan/SKILL.md :56/:65/:172/:176 (the last two `plan`->`planned`). `git status --porcelain -- requests/` is empty, so both track READMEs are byte-unchanged. No mechanical guard was added, per D3.",
    "how_checked": "execution (git grep, git status) + read of the diff hunks"
  },
  {
    "id": "P5a",
    "criterion": "Phase 5: the four promised behaviours (fence exemption, file.py:123 suffix, var/ target exemption, bare-token scan) are implemented and unit-tested against fixture strings built in code, not files on disk",
    "source": "plan-phase-5 acceptance 1",
    "verdict": "met",
    "evidence": "tests/test_doc_link_contract.py (untracked, 166 lines) holds 14 tests grouped under the four promises, all against in-code strings. It imports the logic as `import test_doc_links as guard`, which required Phase 5 step 2's refactor — tests/test_doc_links.py now exposes strip_fences(), link_targets(), resolve_target() and bare_request_tokens() as callable helpers (`:42-137`) with test_relative_links_resolve() kept as the repo-wide entry point (`:144`). Fence tracking is a line-by-line pre-pass (FENCE regex at `:25` handles ``` and ~~~ and blockquoted `>` prefixes, and only the opening marker can close). All 14 pass.",
    "how_checked": "execution (targeted pytest) + full read of both modules"
  },
  {
    "id": "P5b",
    "criterion": "Phase 5: PROVE the link guard still bites — a genuinely broken relative link goes red; and PROVE the bare-token scan bites — a dead prose `requests/` reference goes red",
    "source": "plan-phase-5 acceptance 3 and 4",
    "verdict": "met",
    "evidence": "Ran the real functions on injected fixtures (no files written, so I could not literally 'add a broken link to a tracked file and revert' as the plan phrases it): `injected broken link reported: True` for `[x](does/not/exist.md)`, and `injected dead bare token: ['requests/feature-requests/nope/X.md']`. Neither scan is vacuous — across 82 markdown files the guard examines 397 link targets and 209 bare `requests/` tokens. The unit module also pins the negative direction: test_a_genuinely_dead_target_is_still_dead_with_a_suffix (`:88-91`) proves suffix-stripping cannot launder a dead path, and test_the_var_exemption_does_not_swallow_a_lookalike (`:105-106`) proves `variance.md` is not caught by the `var` exemption.",
    "how_checked": "execution (python probe driving the real guard functions)"
  },
  {
    "id": "P5c",
    "criterion": "Phase 5: the scan was NOT weakened to make the repo pass — real dead pointers are treated on their merits, not exempted away",
    "source": "plan-phase-5 step 7 ('Do not weaken the scan to make the repo pass')",
    "verdict": "partial",
    "evidence": "Two loosenings measured. (1) Fence-stripping hides ZERO currently-dead link targets tree-wide — I compared raw vs fence-stripped extraction across all 82 files and got `dead link targets now hidden by fence-stripping: 0`. Clean. (2) bare_request_tokens() carries an `own_dir` exemption (tests/test_doc_links.py:117-137) that is NOT anywhere in the plan — the plan named only the angle-bracket placeholder treatment. I measured its blast radius by diffing source=None vs source=path over the tree: it suppresses exactly ONE token, `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md -> requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md` — precisely the 'a plan lists the report its stage 4 will write' case its docstring argues, and it is pinned in both directions by tests at :149-165. Narrow, documented, and honest, but it is an unplanned exemption added on the implementer's own authority and the operator should ratify it rather than inherit it.",
    "how_checked": "execution (python probe computing the strict-vs-lax token delta across all 82 markdown files, and the raw-vs-stripped link delta)"
  },
  {
    "id": "P5d",
    "criterion": "Phase 5: mypy clean under strict over the rewritten module; ruff and format clean",
    "source": "plan-phase-5 acceptance 5",
    "verdict": "met",
    "evidence": "`uv run mypy` -> `Success: no issues found in 39 source files` (mypy strict covers tests/ here). `uv run ruff check .` -> `All checks passed!`. `uv run ruff format --check .` -> `119 files already formatted`. Note tests/test_doc_links.py:31 spells the en-dash as `–` specifically to keep ruff RUF001/RUF003 quiet — a real convention detail honoured.",
    "how_checked": "execution"
  },
  {
    "id": "P6a",
    "criterion": "Phase 6: the widened reference guard goes RED naming plan_panel.js:147 before the fix, and green after",
    "source": "plan-phase-6 acceptance 1",
    "verdict": "met",
    "evidence": "I could not un-apply the fix, so I replayed the widened matcher against the HEAD blobs via `git show`. Result: `HEAD version of create-implementation-plan/plan_panel.js -> ['...:147 -> docs/data-sources.md', '...:164 -> docs/data-sources.md']` and `HEAD version of scope-feature/scope_panel.js -> ['...:125 -> docs/data-sources.md']`. So the widened guard demonstrably goes red on the pre-fix tree, naming :147 as the plan predicted — plus two instances the plan's checklist never named. `docs/data-sources.md` does not exist (confirmed); `git grep data-sources` now returns hits only in requests/ artifacts and the memory file, none of which the guard scans. The fix also corrected the surrounding sentence (the false 'currently marked unconfirmed' claim) rather than just the filename, as step 3 required.",
    "how_checked": "execution (python probe applying the current REPO_REFERENCE regex to `git show HEAD:` blobs) + git grep"
  },
  {
    "id": "P6b",
    "criterion": "Phase 6: the exclusions (datasets/manifest.json forward-looking; the batching guard's synthetic fixture locations) are each justified by an in-file comment so a reader can tell an exemption from an oversight",
    "source": "plan-phase-6 acceptance 3 / steps 4-5",
    "verdict": "met",
    "evidence": "tests/test_skill_references.py:36-40 carries the datasets/build exclusion rationale in the REPO_REFERENCE docstring-comment, citing CLAUDE.md's 'those directories arrive with the phase that needs them'. scannable_text()'s docstring at :62-70 justifies blanking the fixture block rather than exempting the whole file, explicitly so 'the rest of that guard stays in scope'. I verified that is true, not just claimed: 23 lines blanked, `test_extract_client.py` gone from the scannable text, the RUN: line still present.",
    "how_checked": "execution (python probe on scannable_text) + static read"
  },
  {
    "id": "P6c",
    "criterion": "Phase 6: the widened token pattern covers 'the repo-path shapes actually cited there (docs/*.md at minimum)'",
    "source": "plan-phase-6 step 2",
    "verdict": "partial",
    "evidence": "REPO_REFERENCE = `(?:tests/test_[a-z0-9_]+\\.py|docs/[a-z0-9/-]+\\.md)` (tests/test_skill_references.py:36). I probed it: `docs/decisions/0012-scouted-ratings-only.md` matches, but `docs/README.md` -> [] and `docs/Data_Access.md` -> [] (no uppercase or underscore in the class), and `src/...`, `.claude/...`, `ops/...` paths are out of scope entirely. This meets the plan's stated minimum and catches the real drift instance, but a phantom uppercase docs filename would still slip through. One-character fix if the operator wants the spirit as well as the letter.",
    "how_checked": "execution (python probe feeding six candidate strings to the live regex)"
  },
  {
    "id": "P7",
    "criterion": "Phase 7: statuses advanced on all four artifacts + both Index rows; the leak-guard row byte-unchanged; one appended memory entry; IMPLEMENTATION_REPORT.md written with the before/after and corrupted-copy output; RCA Hardening 8 filed as a fresh intake",
    "source": "plan-phase-7 acceptance 1-5 / files-to-touch checklist",
    "verdict": "unmet",
    "evidence": "`git status --porcelain -- requests/ ops/` returns NOTHING — no requests/ file changed. Concretely: requests/bugfix-requests/README.md still shows both rows at Stage `planned`; verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md:1, doc-link-guard-mismatch/BUGFIX_REQUEST.md:1 and doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:1 all still read `Status: diagnosed ... next: plan`; IMPLEMENTATION_PLAN.md:1 still reads `planned ... next: implement`. `Get-ChildItem -Recurse requests/bugfix-requests` confirms there is NO IMPLEMENTATION_REPORT.md and no new intake directory for RCA Hardening 8 (§5 D5). The ONLY Phase 7 item that landed is the memory append — and it is three entries where the plan said one. The mandated entry (data-engineer-memory.md:290-301) is correct: label `verified`, tag `harness`, and correctly narrowed per D4 (it refutes the 2026-08-15 entry's INTERPRETATION while explicitly stating the sibling-repo measurement 'stands and was not re-tested here'). `uv run pytest tests/test_agent_contract.py::test_memory_entries_carry_an_epistemic_label` passes. The leak-guard row is byte-unchanged (trivially — nothing in requests/ changed).",
    "how_checked": "execution (git status on requests/ and ops/, recursive directory listing, Get-Content -TotalCount 1 on each artifact, targeted pytest) + static read of the memory diff"
  },
  {
    "id": "P8a",
    "criterion": "Phase 8: a guards step is added to the EXISTING quality job (never a new job), the job display name at ci.yml:16-17 is untouched, ops/branch-protection.json diff is empty",
    "source": "plan-phase-8 acceptance 3 / steps 3-4",
    "verdict": "met",
    "evidence": "Parsed ci.yml with pyyaml: `jobs: ['quality']` (one job), `job name: Lint, types, tests` (unchanged), steps end `..., 'mypy', 'pytest', 'Skill guards (node)'` — appended after pytest so the cheap Python gates fail first. `ops/branch-protection.json:5` pins `\"Lint, types, tests\"` and `git status --porcelain -- ops/` is empty, so the required-check context still resolves.",
    "how_checked": "execution (pyyaml parse of the workflow + git status on ops/) + read of ci.yml in full"
  },
  {
    "id": "P8b",
    "criterion": "Phase 8: node is pinned via actions/setup-node, a `node --version` line is kept anyway, and all five guards run by EXPLICIT path under `set -euo pipefail` — never a glob",
    "source": "plan-phase-8 steps 1-2, 5",
    "verdict": "met",
    "evidence": "ci.yml:34-37 pins `actions/setup-node@v4` with `node-version: '22'`, with an in-file comment saying pinning removes the unmeasured 'ubuntu-latest ships node' claim from the chain. The parsed run block is exactly: `set -euo pipefail` / `node --version` / five `node <explicit path>` lines naming verify_batching_guard.mjs, implement-plan/merge_fallback_guard.mjs, scope-feature/merge_fallback_guard.mjs, create-implementation-plan/merge_fallback_guard.mjs and merge_failure_repro.mjs. No glob, no PowerShell-style `&&` chain. I confirmed all five run offline against tracked files only — every one exits 0 locally with no network, no uv, no warehouse.",
    "how_checked": "execution (pyyaml dump of the step's run script + running all five guards locally)"
  },
  {
    "id": "P8c",
    "criterion": "Phase 8: a real CI run log showing the guards step exiting 0 inside 'Lint, types, tests', pasted with its run URL; AND an IN-CI red demonstration (push a re-keyed fixture, watch the check go red, revert) — a local demonstration explicitly does not satisfy this",
    "source": "plan-phase-8 acceptance 1 and 2",
    "verdict": "unmet",
    "evidence": "Nothing is committed (`git log --oneline -8` still ends at a656acb 'Plan the ported-guard repair'; the entire implementation is uncommitted per `git status --porcelain`). No PR exists, so no run log and no run URL can exist, and the in-CI red demonstration — which the plan's meta-audit specifically restored BECAUSE a local demo cannot catch a YAML-level swallowed exit code — has not happened. Phase 8 step 2's follow-on ('record the first observed node version in §5 with a `measured <date>` label and the run URL') is also undone, consistent with requests/ being untouched. The plan itself says at :469-471 that this phase may split into a follow-up PR, so this is a deferral rather than a contradiction — but it is not met.",
    "how_checked": "execution (git log, git status) — the check is structurally impossible pre-PR and I am recording that honestly rather than inferring success"
  },
  {
    "id": "C1",
    "criterion": "Conventions: the game is READ-ONLY (ADR 0001); no fixed-offset parser read; players.csv ground truth; no OOTP data tracked (ADR 0006); no hardcoded machine paths; commits through /commit only",
    "source": "CLAUDE.md / plan §8 Conventions",
    "verdict": "met",
    "evidence": "The 14-file change set touches only .claude/skills/, .claude/agents/data-engineer-memory.md, .github/workflows/ci.yml and tests/ — nothing in src/ootp_ai/, no dbt model, no dataset, no .env read, no save file, no parser code path. The plan's §2 states the parser conventions 'have no surface here and must not be padded in', and none were. test_no_leaks.py's three tests pass in the full run, and I separately applied its PATTERNS to the untracked tests/test_doc_link_contract.py (which the leak guard cannot see until staged) — zero hits, so no scratchpad drive path leaked in. Nothing is committed, consistent with agents-never-commit-ad-hoc.",
    "how_checked": "execution (full pytest incl. test_no_leaks, plus a direct PATTERNS probe on the untracked file) + line-by-line read of `git diff HEAD`"
  },
  {
    "id": "C2",
    "criterion": "Files-to-touch checklist: the changed set matches the plan's checklist, with no unplanned files and nothing on the NOT list",
    "source": "plan §7 Files to touch",
    "verdict": "partial",
    "evidence": "13 modified + 1 untracked. Present and planned: verify_batching_guard.mjs, the six SKILL.md files, plan_panel.js, tests/test_skill_references.py, tests/test_doc_links.py, the Phase 5 repro (tests/test_doc_link_contract.py), ci.yml, data-engineer-memory.md. Both NOT items are honoured — acceptance_panel.js is absent from the diff, and requests/ is entirely untouched so neither track README's contract text nor the leak-guard row moved. TWO deviations: (a) `.claude/skills/scope-feature/scope_panel.js` was changed and is NOT on the checklist — it is the same phantom-docs fix at :125, so it is correct over-delivery consistent with Phase 6's intent, and my HEAD replay confirms the widened guard would have demanded it anyway; (b) the five requests/ checklist items (both Index rows, four status blockquotes, IMPLEMENTATION_REPORT.md) are all missing — see P7.",
    "how_checked": "execution (git status --porcelain, git diff HEAD --stat) + item-by-item comparison against IMPLEMENTATION_PLAN.md:592-609"
  }
]
```
