<!-- Raw, unfiltered acceptance-panel output. Saved by /implement-plan step 5.
     Agent prose is FENCED and drive letters are bracketed: tests/test_no_leaks.py has
     no fence exemption (that refusal is this fix's D3), so a trail about a leak guard
     cannot quote what the guard bans. Only path prefixes changed. -->

# Acceptance panel - raw output

Run 2026-08-17. Verdict: **fix**.

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
  "criteria_total": 35,
  "criteria_met": 26,
  "criteria_unmet": 8,
  "criteria_unverifiable": 1,
  "confirmed_findings": 20,
  "blockers": 0,
  "majors": 7
}
```

degraded_lenses: `[]`

## Verdict rationale

~~~
Not 'go': the upstream bugfix-track contract requires an acceptance ledger carrying the 'red repro now green + regression test present' row, and no IMPLEMENTATION_REPORT.md exists anywhere in the tree (U4 unmet — raised by all six lenses and confirmed by seven independent verify passes, and reproduced by me). Plan Phase 6 criteria P6.1 and P6.2 are unmet; P2.2, P2.3, P5.4 and P7 are partial; P1.3 is unmet. Not 'no-go': the implementation is substantively on-plan and correct — Phases 1 through 5 all landed, the red repro is green BECAUSE of the fix (the 146-vs-147 enumeration proves it, not a rewritten test), and the full local gate is green (205 passed, ruff/format/mypy clean, five .mjs guards exit 0). No confirmed blocker exists; nothing touches the parser, a save, or game data. The remaining work is one report file, three status advances, an Index row and its stale present-tense prose, two test-coverage additions the plan's own §4 'every guard must be seen to fail' standard already demanded, and one false rationale sentence in /commit.
~~~

## Summary

~~~
The code half of this fix is real and I re-verified the load-bearing parts by execution rather than trusting the panel. `uv run pytest -m "not gamedata" --tb=no` -> `205 passed, 62 deselected in 1.42s` (plan baseline was `1 failed, 196 passed`; 197 + 8 new tests = 205). The enumeration widening does exactly what it claims and adds zero junk: `git ls-files` = 146, `git ls-files --cached --others --exclude-standard` = 147, the sole delta being the untracked `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md` this implementation itself wrote. The `.gitignore:27` `*.lg` tightening is real and carries a dated measured comment at :25-26. No ADR 0001 / ADR 0006 / fixed-offset surface exists: `git diff HEAD --stat` covers 8 files, none under `src/`, none a fixture byte. The RCA's contract — red repro green + regression test left behind + nothing else regresses — is MET by measurement.

What is not done is the paper trail and two coverage holes the widening did not close. Phase 6 was not executed: there is no IMPLEMENTATION_REPORT.md (the directory holds only BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md and reviews/), all three status headers still read `next: plan`/`next: implement`, and `requests/bugfix-requests/README.md:52` still says `planned` and still describes the defect in the present tense as live. That also means Phase 2's mandatory falsification demonstration is recorded nowhere — `git grep "silently missed"` returns only the two plan lines. On coverage: I confirmed zero `pytest.raises` in either guard module, so no committed test ever watches the guard go red; the verifier demonstrated by execution that a mutant scanning 0 of 134 files, or an EXEMPT_PREFIXES change collapsing the set from 134 to 9, leaves all 18 guard tests green. I independently measured the suffix filter: 12 tracked files are enumerated but never opened, including all eight planning/acceptance panel `.js`/`.mjs` files and `gm/ledger.jsonl` (0 pattern hits today, so latent) — and the new `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md:58` declares guard scope "now fixed", closing the route by which that would be picked up.

ONE FINDING REFUTED AND DROPPED: infra-cost LG-01 claimed the inverted `is_file()` mutant survives the suite. It does not — the verifier measured `1 failed, 14 passed`, with `test_a_path_that_no_longer_exists_does_not_crash_the_scan` raising `FileNotFoundError`. The underlying "no test sees the guard go red" gap is nonetheless real and is carried forward on the edgecases lens's separate, reproduced mutant (`if not path.is_file() or True:` -> 18 passed while scanning nothing).
~~~

## Acceptance ledger

### U1 - MET
~~~
criterion: RCA contract: the red repro goes GREEN — test_an_untracked_file_is_visible_to_the_leak_guard passes
source: ROOT_CAUSE_ANALYSIS.md — bugfix-track acceptance contract

evidence:
I ran `uv run pytest -m "not gamedata" --tb=no` -> `205 passed, 62 deselected in 1.42s`, zero failures, which includes the repro. Green BECAUSE of the fix, not vacuously: I measured `(git ls-files).Count` = 146 vs `(git ls-files --cached --others --exclude-standard).Count` = 147, the delta being the untracked requests/feature-requests/secret-scanning/FEATURE_REQUEST.md; the auditor's read-only replication of the pre-fix enumeration returned 133 candidates and could not see that file, while scannable_text_files() returns 134 and does.

reconciliation:
Auditor and verifier both 'met' on identical execution evidence; my own run reproduces the tally exactly. No disagreement.
~~~

### U2 - MET
~~~
criterion: RCA contract: a regression test is left behind
source: ROOT_CAUSE_ANALYSIS.md — bugfix-track definition of done

evidence:
tests/test_leak_guard_scope.py grew 7 -> 15 tests (+114/-8 lines in `git diff HEAD --stat`). The eight added at :113-200 cover nested untracked dirs, non-ASCII filenames, no-empty-entries, suffix-outside-keep, the game-data enumeration seeing an untracked fixture, the var/ counterweight, plain `.lg` exclusion, and the deleted-path crash. All green in my 205-passed run.

reconciliation:
Both ledgers 'met' on the same static+execution evidence. Agreed. The qualitative gap is recorded separately as CF-03/CF-04: all eight are membership assertions, none observes a failure.
~~~

### U3 - MET
~~~
criterion: RCA contract: nothing else regresses — no other audit or test breaks
source: ROOT_CAUSE_ANALYSIS.md — bugfix-track definition of done

evidence:
My run: `205 passed, 62 deselected in 1.42s`, zero failures. Both reviewers independently measured `uv run ruff check .` -> All checks passed; `uv run ruff format --check .` -> 129 files already formatted; `uv run mypy` -> Success: no issues found in 40 source files; all five .mjs guards exit 0. Deselected count unchanged at 62, so no marker moved.

reconciliation:
Identical verdicts from both ledgers. The verifier honestly flags that the `-m gamedata` selection was NOT run (needs the real save) — correct, and CI runs `-m "not gamedata"` only per .github/workflows/ci.yml:57, so this is the full checkable surface.
~~~

### U4 - UNMET
~~~
criterion: Bugfix-run acceptance ledger MUST carry a 'red repro now green + regression test present' row
source: ROOT_CAUSE_ANALYSIS.md — upstream acceptance contract for this stage

evidence:
I ran `Get-ChildItem -Recurse requests\bugfix-requests\leak-guard-blind-to-untracked-files`: it returns exactly reviews\, BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md, reviews\plan-adversarial.md, reviews\plan-proposals.md. No IMPLEMENTATION_REPORT.md. `git status --porcelain` lists only 8 modified files and one untracked directory (requests/feature-requests/secret-scanning/). The ledger row exists nowhere in the repo.

reconciliation:
Auditor 'unmet'; the verifier routes the same fact through P6.1 'unmet'. Both agree and I reproduced it. This is the single unmet UPSTREAM criterion and the reason the verdict is 'fix'.
~~~

### P0 - NOT-VERIFIABLE
~~~
criterion: Phase 0 — the tally, both enumeration counts, branch and SHA written down; tree clean before starting
source: plan-phase-0

evidence:
The plan's only sanctioned home for these numbers is Phase 6's IMPLEMENTATION_REPORT.md, which does not exist. `git log --oneline -3` shows 0826da6 / 4c21117 (Plan the leak-guard fix in six commit-gated phases) / edc7aea (Diagnose the leak guard's blind spot); the tree is now dirty with the implementation, so pre-implementation cleanliness cannot be reconstructed without a mutating git command I am forbidden to run. Indirect corroboration only: 196 passed + 1 fixed + 8 new = the 205 I measured.

reconciliation:
Both ledgers 'not-verifiable' with identical reasoning. Agreed.
~~~

### P1.1 - MET
~~~
criterion: Phase 1 — `uv run pytest tests/test_leak_guard_scope.py --tb=short` green; red repro green and all six counterweights hold
source: plan-phase-1

evidence:
Both reviewers ran it: `15 passed in ~0.3s`. The count is 15 rather than the plan's Phase-1 figure of 7 because Phases 2-3 legitimately added 8 tests to the same module; the original seven (probe-string-is-banned, untracked-visibility repro, gitignored counterweight, and the four parametrised junk-dir cases) survive at :56-105 and pass.

reconciliation:
Both 'met'; both explained the 7->15 delta the same way. Agreed.
~~~

### P1.2 - MET
~~~
criterion: Phase 1 — `uv run pytest -m "not gamedata" --tb=no` -> 197 passed, 62 deselected, zero failures
source: plan-phase-1

evidence:
My own run: `205 passed, 62 deselected in 1.42s`, zero failures. 205 = 197 (the Phase-1 target) + 8 tests from Phases 2-3, exactly as plan §4 predicted. Deselected count matches 62 exactly.

reconciliation:
Both 'met' on identical arithmetic; my run reproduces it. Agreed.
~~~

### P1.3 - UNMET
~~~
criterion: Phase 1 — `git diff --stat` lists exactly one file, and tests/test_leak_guard_scope.py is not in it
source: plan-phase-1

evidence:
`git diff HEAD --stat` lists 8 files including `tests/test_leak_guard_scope.py | 114 +++++--`. `git log --oneline -3` shows the newest commit is 0826da6 (unrelated work) — there are no phase commits, so all six phases sit in one uncommitted blob and the Phase 1 isolation boundary never existed.

reconciliation:
DISAGREEMENT: auditor 'unmet', verifier 'not-verifiable'. I side with the auditor. Both saw the same evidence, but 'not-verifiable' implies an unknown; the absence of any Phase 1 commit is a determinate measured fact from git log, so the criterion is definitively not satisfied rather than unknowable. I record the verifier's substance point in full: the auditor independently closed the underlying question by replicating the pre-fix enumeration read-only (133 candidates, blind to the untracked FR), proving the repro was genuinely red at HEAD — so the CODE claim holds even though the plan's chosen proof does not.
~~~

### P1.4 - MET
~~~
criterion: Phase 1 — on a clean tree both enumerations return the same count; the widening added no junk
source: plan-phase-1

evidence:
I measured: tracked=146, widened=147. The auditor's Compare-Object showed the single delta is requests/feature-requests/secret-scanning/FEATURE_REQUEST.md — the one untracked file, created by this implementation. Junk check on the widened set: var/ 0, .venv/ 0, __pycache__ 0, node_modules 0, with .venv, .pytest_cache and tests/__pycache__ confirmed present on disk, so the zeros are real exclusions.

reconciliation:
Both 'met' with the same 146/147 measurement, which I reproduced. Agreed.
~~~

### P1.5 - MET
~~~
criterion: Phase 1 — ruff / format / mypy green; five .mjs guards still exit 0
source: plan-phase-1

evidence:
Both reviewers ran all four: `All checks passed!`, `129 files already formatted`, `Success: no issues found in 40 source files`, and node exit=0 on merge_failure_repro.mjs, three merge_fallback_guard.mjs and verify_batching_guard.mjs. mypy is strict over tests/, so `git_paths(*args: str) -> list[str]` and every new test annotation type-check.

reconciliation:
Both 'met', independently executed by two lenses. Agreed.
~~~

### P2.1 - MET
~~~
criterion: Phase 2 — all new tests green, and the seven pre-existing ones unchanged (D4: assertion messages byte-identical)
source: plan-phase-2

evidence:
15 passed. Both reviewers read `git diff HEAD -- tests/test_leak_guard_scope.py` hunk by hunk: the only edits to the pre-existing seven are the tracked_text_files -> scannable_text_files rename at :74, :91, :102 plus docstring prose. Every assertion message appears as unchanged CONTEXT (no +/- marker), e.g. the messages at :76-77 and :92-93 — so the rename did not launder a weakened test.

reconciliation:
Both 'met' on line-level diff reads. Agreed.
~~~

### P2.2 - PARTIAL
~~~
criterion: Phase 2 — prove the encoding fix bites: a non-ASCII probe is reported, and the reverted `text=True` form SILENTLY misses it
source: plan-phase-2

evidence:
The technical property is confirmed by three independent executions in throwaway scratch repos: under the old form `git ls-files -o --exclude-standard` emits `"caf\303\251_probe.md"` (C-quoted, apparent suffix `.md"`, rejected by the keep set at tests/test_no_leaks.py:72) and the enumeration yields `[]`, while the `-z` + explicit UTF-8 form yields `café_probe.md`. `locale.getpreferredencoding(False)` is cp1252 here and `core.quotepath` is unset, so both halves of the docstring at tests/test_no_leaks.py:44-53 are true. But the criterion is a falsification the IMPLEMENTER was to perform and Phase 6 step 1 was to record verbatim; `git grep -rniI "silently missed"` returns only the two plan lines, and no .md under requests/ contains 'text=True' outside the plan.

reconciliation:
EFFECTIVE DISAGREEMENT: both ledgers marked this 'met'. I downgrade to 'partial' and side with the fidelity lens's separate finding (verified CONFIRMED as V3): the reviewers proved the mechanism themselves, which is evidence about the CODE, not evidence that the plan's required observation-and-record step was performed. The code half is met; the record half is unmet and is carried as CF-02.
~~~

### P2.3 - PARTIAL
~~~
criterion: Phase 2 — full offline suite green with the new count recorded
source: plan-phase-2

evidence:
Run half MET: `205 passed, 62 deselected` (my run). Recorded half UNMET: no count appears anywhere in the 8-file diff, and the plan routes recorded counts into Phase 6's IMPLEMENTATION_REPORT.md, which does not exist.

reconciliation:
Both ledgers 'partial' with identical reasoning. Agreed.
~~~

### P2.4 - MET
~~~
criterion: Phase 2 — ruff / format / mypy green
source: plan-phase-2

evidence:
Same executions as P1.5. Notable that mypy is strict over tests/: `git_paths(*args: str) -> list[str]` at tests/test_no_leaks.py:39 and `game_data_offenders() -> list[str]` at :136 are both fully annotated, and the new tests annotate `-> None` and `monkeypatch: pytest.MonkeyPatch`.

reconciliation:
Both 'met'. Agreed.
~~~

### P2.5 - MET
~~~
criterion: Phase 2 steps — `-z` passed, decode pinned to UTF-8, NUL split with trailing empty dropped, read guarded NARROWLY against a deleted path
source: plan-phase-2

evidence:
I read tests/test_no_leaks.py:39-80 directly: :56 `["git", "ls-files", "-z", *args]`; :61 `out.stdout.decode("utf-8", errors="surrogateescape")` with `text=` removed entirely; :62 `[rel for rel in decoded.split("\0") if rel]`. The verifier confirmed :122-123 `if not path.is_file(): continue` alongside the retained narrow `except UnicodeDecodeError` at :126, with no bare `except Exception` in the file.

reconciliation:
Only the verifier carried this row; the auditor folded it into P2.2/P3.x. I adopt the verifier's row — it is grounded in a full static read I reproduced for the git_paths half. See CF-15 for two residual defects in the is_file() skip that do not unmake this 'met'.
~~~

### P3.1 - MET
~~~
criterion: Phase 3 — the new tests green; `git check-ignore --no-index` confirms the `.lg` tightening
source: plan-phase-3

evidence:
I read .gitignore:24-28 myself: a dated comment ('Both forms: `*.lg/` alone matches only a DIRECTORY, so a plain file named `foo.lg` was not ignored. Measured 2026-08-17 with `git check-ignore --no-index`.') followed by `*.lg` at :27 above the pre-existing `*.lg/` at :28. Both reviewers ran `git check-ignore --no-index -v foo.lg` -> `.gitignore:27:*.lg`, and `roster.lg/x.txt` -> `.gitignore:28:*.lg/`. The regression test at tests/test_leak_guard_scope.py:180-185 is non-vacuous: without the new line the untracked probe would appear in `--others`.

reconciliation:
Both 'met'; I verified the .gitignore text and its comment myself. Agreed.
~~~

### P3.2 - MET
~~~
criterion: Phase 3 — full suite green; ruff / format / mypy green; the second enumeration rerouted through the shared seam
source: plan-phase-3

evidence:
205 passed; ruff/format/mypy green. tests/test_no_leaks.py:155 now calls `git_paths("--cached","--others","--exclude-standard")` behind `game_data_offenders() -> list[str]` at :136, and test_game_data_is_not_tracked at :160-163 is reduced to asserting against it. The auditor invoked game_data_offenders() directly against the live tree and got [].

reconciliation:
Both 'met'. Agreed. CF-10 records that the function's name and message still say 'tracked' despite the widening.
~~~

### P3.3 - MET
~~~
criterion: Phase 3 — the source comment names the three measured .gitignore holes
source: plan-phase-3

evidence:
tests/test_no_leaks.py:142-149 names all three verbatim (tests/fixtures/players.csv, tests/fixtures/x.dat, datasets/x.dat) with the reason — the `!tests/fixtures/**` and `!datasets/**` negations at .gitignore:64-65 are LATER rules and git is last-match-wins. Both reviewers re-measured: `git check-ignore --no-index -v tests/fixtures/probe.dat` resolves to `.gitignore:65:!tests/fixtures/**`, i.e. matched by a negation and therefore NOT ignored.

reconciliation:
Both 'met'. Agreed. CF-15 notes a fourth hole (gm/, via `!gm/` and `!gm/**`) the comment omits.
~~~

### P4.1 - MET
~~~
criterion: Phase 4 — `git grep -n 'tracked_text_files' -- tests/` returns ZERO hits
source: plan-phase-4

evidence:
Both reviewers ran it: no output, $LASTEXITCODE = 1. All call sites renamed including the in-module one an earlier draft had missed — tests/test_no_leaks.py:65 (definition) and :115 (`for path in scannable_text_files():`), plus tests/test_leak_guard_scope.py:74, :91, :102. The identifier survives only in requests/ artifacts, which the criterion's own scoping note excluded as historical record.

reconciliation:
Both 'met' on identical execution. Agreed.
~~~

### P4.2 - MET
~~~
criterion: Phase 4 — full suite green with assertion messages unchanged; mypy green
source: plan-phase-4

evidence:
205 passed; mypy Success. Diff read confirms only `guard.tracked_text_files()` -> `guard.scannable_text_files()` inside the three renamed assertions, message strings unmodified — closing plan §6's risk row 3 (a rename laundering a weakened test).

reconciliation:
Both 'met'. Agreed.
~~~

### P4.3 - MET
~~~
criterion: Phase 4 — tests/test_agent_contract.py green; the appended memory entry carries a valid epistemic label
source: plan-phase-4

evidence:
Both reviewers ran `uv run pytest tests/test_agent_contract.py tests/test_doc_links.py tests/test_skill_references.py --tb=short` -> `9 passed`. .claude/agents/data-engineer-memory.md appends three 2026-08-17 entries at :318, :327, :334 labelled `verified`, `measured`, `measured`, and marks the falsified 2026-08-16 entry 'SUPERSEDED 2026-08-17' in place rather than pruning it, honouring append-never-prune at :41.

reconciliation:
Both 'met'. Agreed. CF-20 carries the nit that three entries landed where one was asked, each ~2x the file's own four-line guidance at :31.
~~~

### P5.1 - MET
~~~
criterion: Phase 5 — `git grep -n 'gitleaks' -- .claude/` still returns both occurrences, untouched
source: plan-phase-5

evidence:
Both survive: .claude/skills/commit/SKILL.md:86 and .claude/skills/update-docs/SKILL.md:25. I read SKILL.md:84-88 directly and the gitleaks sentence is byte-preserved; its line number moved from :78 to :86 only because 8 lines were inserted above. update-docs/SKILL.md is absent from `git status --porcelain`, i.e. genuinely untouched — the plan's explicit NOT-to-touch item.

reconciliation:
Both 'met'. Agreed. CF-13 carries the resulting adjacency problem: the new true sentence now sits three lines from the retained false one.
~~~

### P5.2 - MET
~~~
criterion: Phase 5 — first-sight's plan no longer instructs a reader to work around this defect, marked as dated amendments
source: plan-phase-5

evidence:
requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561 strikes the old instruction and adds '**Amended 2026-08-17: that gap is closed.** … the guard now enumerates `--cached --others --exclude-standard` … The function is called `scannable_text_files()` and its enumeration seam is `git_paths()`'. Risk 15 at :757 is struck and marked 'Fixed 2026-08-17', retaining the residual risk rather than deleting the entry. Both use strikethrough, honouring D5.

reconciliation:
Both 'met' on the LITERAL criterion — the two lines Phase 5 step 2 named were both correctly amended, and the diff touched exactly those two lines. But the phase's stated GOAL ('nothing in the repo still teaches a workaround for a defect that is now fixed') is not achieved: I read :623 myself and it still orders a fresh agent to file the follow-up this fix closed, with :626 requiring 'Two follow-up requests filed.' That residue is CF-05, raised at major by the parser lens and confirmed as V10.
~~~

### P5.3 - MET
~~~
criterion: Phase 5 — `uv run pytest tests/test_doc_links.py tests/test_skill_references.py` green
source: plan-phase-5

evidence:
`9 passed` across doc-links, skill-references and agent-contract. The auditor additionally ran the exact command the skill now prescribes — `uv run pytest tests/test_no_leaks.py` -> `3 passed` — so the instruction added at .claude/skills/commit/SKILL.md:81 is runnable, not dangling. The verifier notes test_doc_links.py uses rglob and therefore also validated the brand-new untracked secret-scanning FEATURE_REQUEST.md.

reconciliation:
Both 'met'. Agreed.
~~~

### P5.4 - PARTIAL
~~~
criterion: Phase 5 step 3 — one line added to port-residue-sweep/BUGFIX_REQUEST.md recording the SECOND gitleaks occurrence, without fixing either
source: plan-phase-5

evidence:
I verified both halves. The instance landed (the file is in `git status --porcelain` with +7 lines) and neither gitleaks occurrence was fixed (P5.1). BUT Select-String shows requests/bugfix-requests/port-residue-sweep/BUGFIX_REQUEST.md:11 still reads 'Six instances are known' above what is now a seven-row table, :56 still says 'six known divergences', and requests/bugfix-requests/README.md's Index row still summarises it as 'Six known places'.

reconciliation:
Only the verifier carried this row; the auditor did not check the surrounding counts. I adopt the verifier's 'partial' and confirmed it myself by direct Select-String. Carried as CF-14.
~~~

### P6.1 - UNMET
~~~
criterion: Phase 6 — IMPLEMENTATION_REPORT.md written with the acceptance ledger, the before/after baseline, and the Phase 2 encoding demonstration verbatim
source: plan-phase-6

evidence:
My `Get-ChildItem -Recurse` on the request directory returns only reviews\, BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md, reviews\plan-adversarial.md, reviews\plan-proposals.md. `git status --porcelain` shows the only untracked addition in the whole tree is requests/feature-requests/secret-scanning/.

reconciliation:
Both ledgers 'unmet'; six of six independent verify passes confirmed it. Agreed and reproduced.
~~~

### P6.2 - UNMET
~~~
criterion: Phase 6 — statuses and Index agree at the track's terminal word (`fixed`); directory moved into `_done/` with the Index link repointed
source: plan-phase-6

evidence:
I read all three headers: BUGFIX_REQUEST.md:1 `diagnosed · created 2026-08-16 · decided · next: plan`; ROOT_CAUSE_ANALYSIS.md:1 `diagnosed · created 2026-08-17 · decided · next: plan`; IMPLEMENTATION_PLAN.md:1 `planned · created 2026-08-17 · decided · next: implement`. requests/bugfix-requests/README.md:52 still reads `| planned |`, links outside `_done/`, and still describes the defect in the PRESENT tense ('enumerates via `git ls-files`, so a banned pattern in a new file passes until it is staged') — now false, in a tracked file in a repo CLAUDE.md declares world-readable forever.

reconciliation:
Both ledgers 'unmet'. I add a mitigation two verify passes surfaced that neither ledger recorded: .claude/skills/commit/SKILL.md Step 4 (:133-138) assigns the status blockquote, the Index Stage cell and the one-time `_done/` move to /commit, which has not run. So this half is legitimately PENDING that gate rather than skipped — unlike P6.1, which is the implementer's own deliverable and has no such excuse. Verdict stays 'unmet' because the work is not done; see GD-04.
~~~

### P6.3 - MET
~~~
criterion: Phase 6 — the secret-scanner feature request exists (RCA direction (c) routed to the feature track)
source: plan-phase-6

evidence:
requests/feature-requests/secret-scanning/FEATURE_REQUEST.md exists (untracked, 81 lines), status `intake · created 2026-08-17 · open · next: scope`, with a matching Index row at requests/feature-requests/README.md:122. Content is grounded: it states the three PATTERNS shapes, names both false gitleaks sites, routes that prose to port-residue-sweep at :57, and carries the negative half ('Explicitly out' §).

reconciliation:
Both 'met'. Agreed — but I read :55-60 myself and CF-06 records that its :58 makes a false claim about guard scope.
~~~

### P6.4 - MET
~~~
criterion: Phase 6 — full local gate green at closure
source: plan-phase-6

evidence:
My run: 205 passed, 62 deselected. Reviewers: ruff `All checks passed!`, format `129 files already formatted`, mypy `Success: no issues found in 40 source files`, five .mjs guards exit 0. Same gate .github/workflows/ci.yml:45-78 runs.

reconciliation:
Both 'met'. Agreed.
~~~

### P7 - PARTIAL
~~~
criterion: Plan §7 files-to-touch checklist — every listed file changed, and the excluded one not changed
source: plan-§7-checklist

evidence:
`git status --porcelain` shows every positive item landed except one: .claude/agents/data-engineer-memory.md, .claude/skills/commit/SKILL.md, .gitignore, requests/bugfix-requests/port-residue-sweep/BUGFIX_REQUEST.md, requests/feature-requests/README.md, requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md, tests/test_leak_guard_scope.py, tests/test_no_leaks.py, plus `?? requests/feature-requests/secret-scanning/`. The NOT-item is honoured: .claude/skills/update-docs/SKILL.md is absent from the diff. Missing: the requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/ row (report, statuses, `_done/` move).

reconciliation:
Both ledgers 'partial' with the same single missing row; my git status reproduces the file list exactly. One verify pass correctly noted the §7 boxes are ALL still unticked (`- [ ]`), so 'the last unchecked item' is loose phrasing — the substance, that the request-directory row is the only one whose WORK is absent, holds.
~~~

### C1 - MET
~~~
criterion: Conventions — the game stays READ-ONLY (ADR 0001): no code path writes a save, a roster import, or automates the game UI
source: CLAUDE.md / ADR 0001

evidence:
`git diff HEAD --stat` lists 8 files: two under tests/, .gitignore, and five prose/skill/memory files. Nothing under src/, no dbt model, no fixture bytes — so no fixed-offset or field-mapping surface either. The only filesystem writes introduced are test probes inside the repo working tree (tests/test_leak_guard_scope.py:40-53 `untracked_file`, which unlinks in a `finally`) — never under the OOTP install or saved-games directory.

reconciliation:
Only the verifier carried this row explicitly; the parser lens reached the same conclusion in its summary ('no surface'). I reproduced the diff --stat. Agreed 'met'.
~~~

### C2 - MET
~~~
criterion: Conventions — no absolute/drive-letter path in any tracked file; no OOTP game data tracked (ADR 0006)
source: CLAUDE.md / ADR 0006

evidence:
test_no_machine_paths_or_identifiers and test_game_data_is_not_tracked both pass inside my 205, and they now scan the untracked secret-scanning FEATURE_REQUEST.md too. .gitignore:27 tightens rather than loosens. The only drive-letter strings in the change are the deliberate fixtures inside the EXEMPT file (tests/test_no_leaks.py:90-91) and the runtime-assembled LEAK at tests/test_leak_guard_scope.py:37, built from concatenated chars so no literal exists. The parser lens confirmed `git ls-files -- tests/fixtures` returns only README.md, __init__.py, synthetic.py, tiers.py.

reconciliation:
Verifier 'met'; parser and infra-cost lenses independently concurred. Agreed. CF-06 records that 12 enumerated files are never opened — a latent coverage hole, not a live violation (I measured 0 pattern hits across all 12).
~~~

### C3 - MET
~~~
criterion: Conventions — no new pytest markers (--strict-markers); pytest run without a second -q so summary lines are real
source: CLAUDE.md / pyproject.toml

evidence:
pyproject.toml:100 `addopts = "-q --strict-markers --strict-config"`; :107 declares `gamedata` as the sole marker. My run produced a real summary line ('205 passed, 62 deselected in 1.42s'), not a dot-count, and the deselected count is 62 both before and after — so no marker was added or moved.

reconciliation:
Only the verifier carried this row; I reproduced the run. Agreed 'met'.
~~~

### C4 - MET
~~~
criterion: Conventions — commits go through /commit only; agents never push main, force-push or amend
source: CLAUDE.md

evidence:
`git log --oneline -3` shows HEAD at 0826da6 with no new commit; the entire implementation is uncommitted. No commit was made outside /commit because no commit was made at all. No rule was broken.

reconciliation:
Only the verifier carried this row. Agreed 'met' — but note the side effect it correctly flags: the plan's six commit-gated checkpoints collapsed into one tree (CF-12), which is why P1.3 is unmet.
~~~

### D3 - MET
~~~
criterion: Plan §5 D3 — the refusal of a fenced-code exemption is recorded in a comment near tests/test_no_leaks.py:16, and no exemption (nor an EXEMPT_PREFIXES directory entry) was added
source: plan-phase-2 / §5 D3

evidence:
The refusal comment landed at tests/test_no_leaks.py:18-25, naming the asymmetry with test_doc_links.py, the smuggling argument, the accepted cost, and 'Do not add one without re-opening the decision.' EXEMPT at :16 still holds exactly one entry; EXEMPT_PREFIXES at :26 is still the empty tuple — corroborated by my own suffix-drop probe, which found no path excluded by prefix.

reconciliation:
Only the verifier carried this row, from a full static read. Agreed 'met'. The 8 inserted lines are also the direct cause of the citation drift in CF-07.
~~~

## Confirmed findings (20)

### [MAJOR] Phase 6 not executed: no IMPLEMENTATION_REPORT.md, so the bugfix track's required acceptance ledger row exists nowhere; statuses and Index still say the work is only planned

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/ (no IMPLEMENTATION_REPORT.md); requests/bugfix-requests/README.md:52

PROBLEM
Raised independently by all six lenses (acceptance F1, fidelity F1, correctness F1, edgecases F3, parser LG-01, skill-quality LG-03, infra-cost LG-03) and CONFIRMED by seven separate verify passes; I reproduced it myself. `Get-ChildItem -Recurse` on the request directory returns only reviews/, BUGFIX_REQUEST.md, IMPLEMENTATION_PLAN.md, ROOT_CAUSE_ANALYSIS.md, reviews/plan-adversarial.md, reviews/plan-proposals.md — no report. `git status --porcelain` shows no new file there. Consequently the upstream contract's ledger row ('red repro now green + regression test present') exists nowhere, and every number the plan told the implementer to record — Phase 0's baseline, Phase 2's suite count, Phase 2's encoding demonstration — is unrecorded, making Phase 0 unauditable. Alongside it, BUGFIX_REQUEST.md:1 and ROOT_CAUSE_ANALYSIS.md:1 still read `next: plan`, IMPLEMENTATION_PLAN.md:1 reads `next: implement`, and requests/bugfix-requests/README.md:52 still carries `planned` AND still describes the defect in the present tense ('enumerates via `git ls-files`, so a banned pattern in a new file passes until it is staged') — a sentence that is now false, in a tracked file in a repo CLAUDE.md declares world-readable forever. The paper trail says this work has not been done while the working tree says it has.

PROPOSED FIX
Write requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_REPORT.md carrying (a) the acceptance ledger whose first row is the contract row — red repro `test_an_untracked_file_is_visible_to_the_leak_guard` now green, regression tests at tests/test_leak_guard_scope.py:113-200; (b) the before/after baseline (`1 failed, 196 passed, 62 deselected` -> `205 passed, 62 deselected`; enumeration 146 -> 147; scope module 7 -> 15 tests); (c) the Phase 2 encoding demonstration verbatim (CF-02); (d) the Phase 1 AC3 note from CF-12; (e) what stays open (the gitleaks prose owned by port-residue-sweep, the fence exemption refused in §5 D3). Then at /commit Step 4 advance all three status headers to the track's terminal word `fixed` (requests/bugfix-requests/README.md:45 — NOT `implemented`, per port-residue-sweep instance 6), rewrite the README.md:52 Stage cell AND its present-tense prose to past tense, and move the directory into `_done/` with the Index link repointed.
~~~

### [MAJOR] Phase 2's mandatory 'seen to fail' encoding demonstration has no recorded evidence anywhere in the repo

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md:161-164 (Phase 2 acceptance #2) vs. the repo

PROBLEM
Raised by the fidelity lens (F2), echoed by parser LG-01 and skill-quality LG-03, CONFIRMED as V3. Phase 2 acceptance criterion 2 is a falsification requirement, not a pass requirement: create a non-ASCII probe, confirm it is reported, then temporarily revert to `text=True` with no encoding, confirm it is SILENTLY MISSED, and restore. Plan §4 gives the reason ('A widened guard that has never been observed dropping a file is exactly the unfalsified-confidence this request exists to end') and :288 states 'Every guard this plan ships or widens must be seen to fail.' The verifier ran `git grep -rniI "silently missed"` and the ONLY two hits in the entire repo are the two plan lines — no transcript, no report; no .md under requests/ contains 'text=True' outside the plan. The mechanism is genuine and three reviewers reproduced it in throwaway scratch repos (old form returns [] for a café probe; git emits `"caf\303\251_probe.md"` whose apparent suffix `.md"` fails the keep set at tests/test_no_leaks.py:72; `locale.getpreferredencoding(False)` is cp1252 here) — but reviewer reconstruction is evidence about the code, not evidence the implementer performed the required observation. This is why ledger row P2.2 is 'partial' rather than 'met'.

PROPOSED FIX
Run the demonstration and paste its raw output into the CF-01 report: with the non-ASCII probe present show `test_a_non_ascii_filename_survives_enumeration` green, then with git_paths temporarily using `text=True` and no `encoding=` show it red, then restored and green again. Separately add a one-line comment at tests/test_leak_guard_scope.py:127 recording that the DECODE half of that test is only load-bearing on a non-UTF-8 platform — on a Linux CI runner only the `-z`/C-quoting half bites, so CI does not pin the cp1252 behaviour the docstring cites.
~~~

### [MAJOR] No committed test ever watches the leak guard go RED — a mutant that scans zero files leaves all 18 guard tests green

~~~
location: tests/test_leak_guard_scope.py:64-78 and :188-200; tests/test_no_leaks.py:113-133

PROBLEM
Raised by the edgecases lens (F1) and CONFIRMED as V6 by execution. I verified the core fact myself: `Select-String -Pattern "raises"` over tests/test_leak_guard_scope.py and tests/test_no_leaks.py returns ZERO hits — the repo's only leak protection has no test in which it fails. Every scope test asserts set membership in `scannable_text_files()` (:75, :91, :102-105, :121, :138, :154) or `game_data_offenders()` (:167, :177); the sole invocation of the scan itself, at :200, monkeypatches the candidate list to a nonexistent path and asserts only that nothing raises. The verifier measured the consequence: a mutant widening the skip at tests/test_no_leaks.py:122 to `if not path.is_file() or True:` — the guard opens ZERO of its 134 candidate files — produces `18 passed`. The plan set this exact bar at IMPLEMENTATION_PLAN.md:288. PROVENANCE NOTE: the infra-cost lens raised the same concern (LG-01) using a DIFFERENT mutant (inverted `is_file()`), and that specific claim was REFUTED — the verifier measured `1 failed, 14 passed` with FileNotFoundError from the deleted-path test. I carry this finding on the edgecases/V6 evidence only, and have dropped the refuted mutant claim.

PROPOSED FIX
Add one end-to-end red test to tests/test_leak_guard_scope.py using the existing fixture: `with untracked_file("requests/_leak_guard_red_probe.md", f"# probe\n\n{LEAK}\n"): with pytest.raises(AssertionError, match="_leak_guard_red_probe"): guard.test_no_machine_paths_or_identifiers()`. Five lines; the only assertion in the module that would pin detection rather than visibility, and it kills the scan-nothing mutant. Keep the deleted-path test as the counterweight.
~~~

### [MAJOR] The widened candidate set has no coverage floor — it can collapse from 134 files to 9 and every guard test still passes

~~~
location: tests/test_leak_guard_scope.py:108-185; tests/test_no_leaks.py:133 and :163

PROBLEM
Raised by the skill-quality lens (LG-01) and CONFIRMED as V11 by execution. All nine tests added under the 'Failure modes the widening MAKES LIVE' banner are probe-must-be-present or junk-must-be-absent; nothing pins the SIZE or membership of the ordinary candidate set, and the two production assertions (`assert not violations` at tests/test_no_leaks.py:133, `assert not offenders` at :163) are vacuous on an empty input. The verifier ran two in-memory EXEMPT_PREFIXES simulations: one shrank the set from 134 to 77, the other to 9 — a 93% coverage collapse removing docs/, src/, gm/, .claude/, tests/, ops/ and most of requests/ from the repo's only leak protection — and BOTH produced `18 passed … exit code: 0`. This is precisely the regression class ROOT_CAUSE_ANALYSIS.md:96-98 named and rejected: 'a catastrophic coverage regression that would still pass every existing test, since the existing tests assert only that no violation is found.' Nine tests were added to a module whose entire subject is scope, and the hole remains. Distinct from CF-03: that one is about never seeing a failure, this is about never noticing an empty input.

PROPOSED FIX
Add `def test_the_candidate_set_has_not_silently_shrunk() -> None:` to tests/test_leak_guard_scope.py asserting both a floor and named membership — `seen = guard.scannable_text_files(); assert len(seen) > 100, f"candidate set collapsed to {len(seen)}"; assert REPO_ROOT / "CLAUDE.md" in seen; assert REPO_ROOT / "tests/test_leak_guard_scope.py" in seen`. Both anchors are in the 134-file scanned set today (I measured `scanned: 134`). This is the assertion that turns every other scope test from possibly-vacuous into meaningful.
~~~

### [MAJOR] first-sight's LIVE plan still orders a fresh agent to file the follow-up this fix already closed

~~~
location: requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:623 and :626

PROBLEM
Raised by the parser lens (LG-02) and CONFIRMED as V10; I read the lines myself. Phase 5's stated Goal is 'Nothing in the repo still teaches a workaround for a defect that is now fixed.' Its step 2 named :561 and :757 and both were correctly amended — `git diff HEAD` shows exactly two lines changed in that file. But :623 survives untouched: 'File the two follow-ups the scope named but excluded: the `git ls-files` staging gap in `test_no_leaks.py`, and the GM tool-grant guard test', reinforced by :626 'Two follow-up requests filed.' The `git ls-files` staging gap IS this bugfix, whose request directory already exists. A cold agent executing that step files a duplicate tracker for a closed defect — the exact drift class port-residue-sweep exists to sweep up. The document is live: its header reads `Status: planned · created 2026-08-16 · decided · next: implement`. This is not a citation nit; it is an executable instruction that produces wrong work. (Verifier correction to the raising lens: the step sits in Phase 13, headed at :615, not Phase 12.)

PROPOSED FIX
Amend :623 in the same dated-amendment style already used at :561 and :757 — strike the `git ls-files` staging gap, noting it landed as requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/ on 2026-08-17 — and reduce :626's acceptance from 'Two follow-up requests filed' to one (the GM tool-grant guard test).
~~~

### [MAJOR] The new secret-scanning request declares guard scope 'now fixed', which is false for the file-TYPE half — and 12 tracked files including all eight panel .js/.mjs and gm/ledger.jsonl are enumerated but never opened

~~~
location: tests/test_no_leaks.py:72 (the `keep` set); tests/test_leak_guard_scope.py:150-154; requests/feature-requests/secret-scanning/FEATURE_REQUEST.md:58

PROBLEM
Raised by the edgecases lens (F2), CONFIRMED as V7, and I re-measured it independently: of 147 enumerated paths, 134 are scanned and exactly 12 are dropped by `p.suffix in keep` — .claude/skills/create-implementation-plan/plan_panel.js, .claude/skills/implement-plan/acceptance_panel.js, .claude/skills/scope-feature/scope_panel.js, five .mjs guards, gm/ledger.jsonl, uv.lock, .gitattributes, .gitignore. I scanned all 12 against the guard's own PATTERNS: `total pattern hits in dropped files: 0`, so this is LATENT, not a live leak, and it is pre-existing scope rather than something the fix broke. Two things make it worse than inherited: (a) the new `test_a_suffix_outside_the_keep_set_is_not_scanned` at :150-154 now CEMENTS the extension filter as a deliberate decision, so the next reader treats the hole as settled; (b) FEATURE_REQUEST.md:58 — which I read directly — states under 'Explicitly out': 'Anything about *scope* of the existing guard — that was the leak-guard bugfix, now fixed.' That is false for file type and closes the only route by which this would later be picked up. The panel .js/.mjs files are the prompt text of the very planning/acceptance panels whose absolute-path residue this whole request was filed about, and gm/ledger.jsonl is tracked GM memory in a public repo (ADR 0011 + 0006).

PROPOSED FIX
Minimum: correct FEATURE_REQUEST.md:58 to say the bugfix fixed WHEN the guard looks and that the file-TYPE half of scope remains open. Recommended alongside it (see GD-02): add `.js`, `.mjs` and `.jsonl` to the `keep` set at tests/test_no_leaks.py:72 — I confirmed all 12 files are pattern-clean today, so it lands green — and retarget the :150 test at a genuinely binary suffix such as `.png` so it still pins 'widening scope must not widen file types' without pinning this specific hole shut.
~~~

### [MAJOR] /commit's new leak-guard sentence re-teaches the exact belief this fix removed, and both halves of its rationale are false

~~~
location: .claude/skills/commit/SKILL.md:77-78

PROBLEM
Raised at major by infra-cost (LG-02) and at minor by correctness F2 and edgecases F4; CONFIRMED as V16. SEVERITY: I carry the raising lens's major. I read the lines myself: 'Then run the leak guard, **after staging rather than before** — it enumerates through git, so this is the point at which it can see everything the commit will contain.' Both clauses are now wrong. (a) Staging is not what grants sight — that is the entire fix: I measured the widened enumeration at 147 including the `??` untracked requests/feature-requests/secret-scanning/FEATURE_REQUEST.md, versus 146 for the bare form. (b) The guard never reads staged blobs: tests/test_no_leaks.py:125 is `path.read_text(encoding="utf-8")` against the working tree, so a staged-then-edited file is scanned in its worktree form and files that will NOT be in the commit are scanned too — 'everything the commit will contain' is precisely what it does not see. The same changeset states the opposite correctly at requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561 ('it is no longer load-bearing for detection'), and plan §5 D8 (:337-340) explicitly recorded that staging first 'buys nothing for detection'. So the shipped sentence contradicts both the code and the decision that authorised it, in the repo's most-executed skill — and a future agent reading it may 'restore' the narrow enumeration on that basis, the same regression risk §5 D4 cited to justify the rename.

PROPOSED FIX
Keep the concrete command; drop or invert the rationale. E.g.: 'Then run the leak guard — since 2026-08-17 it enumerates untracked files too and reads the working tree, so it does not need staging to see your work: `uv run pytest tests/test_no_leaks.py`. Running it after staging stays the habit, because that is also when a `git add -f` of a gitignored path first becomes visible to it.' Do not touch the gitleaks sentence at :86 — port-residue-sweep owns it and P5.1 requires it survive byte-identical.
~~~

### [MINOR] The fix shifted every anchor in test_no_leaks.py and left seven stale citations in first-sight's live plan — including two inside the sentence it amended itself

~~~
location: requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:42, :210, :251, :490, :561, :563, :759; tests/test_leak_guard_scope.py:36

PROBLEM
Raised at MAJOR by the fidelity lens (F3), also by acceptance F3 and parser LG-03, CONFIRMED as V4. SEVERITY CHANGE, stated openly: I carry it at MINOR rather than major because V4 itself established that the plan's Phase 5 acceptance #2 is literally satisfied (only :561 and :757 were in scope) and no code behaviour is affected; it is doc rot, albeit in a repo that files bugs about exactly this. The verifier reconstructed pre- and post-change anchors from `git show HEAD:tests/test_no_leaks.py`: PATTERNS moved :24-28 -> :32-36, the drive-letter pattern :25 -> :33, banned_names :106 -> :151, banned_suffixes :107 -> :152, test_patterns_still_catch_real_leaks :51-78 -> :83-110 — caused by the D3 refusal comment at :18-25, git_paths at :39-62 and the game_data_offenders docstring at :136-157. Line :561 is the line this implementation rewrote: its new text correctly names `scannable_text_files()` and `git_paths()` while the same sentence still points a cold agent at `:24-28` (now the middle of the EXEMPT_PREFIXES comment) and `:106-107`. V4 also found a bonus instance: tests/test_leak_guard_scope.py:36 — inside this fix's own regression module — cites the drive-path pattern at `tests/test_no_leaks.py:25`, now :33.

PROPOSED FIX
Repoint all eight while the amendment is being written: PATTERNS `:32-36` at first-sight :42 and :561; drive-letter `:33` at :210 and at tests/test_leak_guard_scope.py:36; banned_names `:151` at :490 and :561; banned_suffixes `:152` at :251, :561 and :759; test_patterns_still_catch_real_leaks `:83-110` at :563. Better and durable: cite symbol names (`PATTERNS`, `banned_suffixes`, `game_data_offenders`) instead of line numbers, which is what the :561 amendment already does for `scannable_text_files()`. Leave `_done/` and `reviews/` occurrences alone — they are historical record.
~~~

### [MINOR] /commit's frontmatter description says it runs no tests while Step 2 now runs pytest

~~~
location: .claude/skills/commit/SKILL.md:12-13

PROBLEM
Raised at MAJOR by skill-quality (LG-04) and CONFIRMED as V14. SEVERITY CHANGE, stated openly: I carry it at MINOR because V14 established by `git show HEAD:` that the contradiction PRE-EXISTED this change (the committed version already ran `uv run pytest tests/test_doc_links.py -q` at Step 3), so this is an inherited inaccuracy deepened rather than a regression introduced. It is still real and worth fixing here: I read :12-13 directly — 'It does NOT run lint, types, tests; CI owns those and runs them on the PR' — against the new :81 `uv run pytest tests/test_no_leaks.py`. The description is the only part of a skill an agent has in context before opening the body, so an agent that honours it skips the new gate, and one that notices the contradiction may drop the body step as an error. Nothing mechanical catches it: the three doc/skill guards return `9 passed` with the contradiction in place. Note the doc-links run is at least loosely covered by 'runs the doc-drift checks proportionally to what changed'; the leak-guard run is covered by no clause at all.

PROPOSED FIX
Amend :12-13 inside the existing sentence so the description stays one paragraph and tests/test_skill_references.py keeps passing: 'It does NOT run lint or types, and the only test it runs is the leak guard; CI owns the rest and runs them on the PR.'
~~~

### [MINOR] The guard still describes itself as scanning only 'tracked' files — the exact narrow self-description Phase 4 spent a whole phase eliminating

~~~
location: tests/test_no_leaks.py:1, :133, :160, :163

PROBLEM
Raised by acceptance F2 and skill-quality LG-06. §5 D4's stated rationale for renaming tracked_text_files was that 'a function called tracked_* that scans untracked files re-arms the very argument the RCA rejected — the next agent would read the name, conclude the widening was a mistake, and narrow it back.' The rename landed (P4.1 met) but three sibling self-descriptions did not. The module docstring at :1 still reads 'Nothing machine-specific may be tracked' — the exact sentence the ROOT_CAUSE_ANALYSIS quoted as the works-as-intended counterargument it had to overrule. The failure message at :133 reads 'machine-specific values in tracked files', now false: it fires on files that are not tracked, mis-triaging the reader toward hunting git history for a local-only scratch file. The second check is still named test_game_data_is_not_tracked at :160 with the message 'OOTP game data must never be tracked' at :163, despite Phase 3 having widened it — and the likeliest real trigger is now an untracked scratch .dat under tests/fixtures/ or datasets/, the two directories the widening exists to cover.

PROPOSED FIX
Update :1 to state the widened intent ('Nothing machine-specific may exist in a file this repo could ship — tracked or merely written'); change :133 to 'machine-specific values in repo files (tracked or not)'; change :163 to 'OOTP game data must never be in this repo, tracked or untracked'; and either rename test_game_data_is_not_tracked to test_game_data_is_not_present or add a one-line comment recording that it deliberately fires before staging. Note in the commit message that D4's byte-identical-message rule was Phase-4-scoped (to stop a rename laundering a weakened test) and is being deliberately released here, so the next reader does not read this as the laundering D4 forbade.
~~~

### [MINOR] `--exclude-standard` ties the newly-bought untracked coverage to ignore files that are not in version control

~~~
location: tests/test_no_leaks.py:56 and :74

PROBLEM
Raised at MAJOR by skill-quality (LG-02) and at minor/medium by acceptance F5, correctness F3 and edgecases F7; CONFIRMED as V12 but with a blast-radius CORRECTION that justifies my downgrade to MINOR, stated openly. V12 measured it: with a global excludes file containing `*.md`, the enumeration fell 147 -> 146 and the single dropped path was the UNTRACKED FEATURE_REQUEST.md — every tracked .md survived, because `--exclude-standard` filters the `--others` listing and never `--cached`. So pre-fix coverage remains machine-independent; what is machine-dependent is exactly the untracked visibility this fix bought, which a developer's global gitignore or `.git/info/exclude` can silently revoke with a green suite. Latent here: `git config --get core.excludesFile` exits 1 and .git/info/exclude contains only comments. CI is a fresh checkout with no untracked files, so the widening is a no-op there and the regression tests are the only thing exercising it. The counterweight tests at tests/test_leak_guard_scope.py:81-105 pin only .gitignore-sourced exclusions, and neither the plan's evidence table nor git_paths' otherwise-thorough docstring at :40-53 mentions the other two sources.

PROPOSED FIX
Neutralise the un-versioned half at the seam: invoke as `["git", "-c", "core.excludesFile=", "ls-files", "-z", *args]` at tests/test_no_leaks.py:56 — V12 measured that this restores the full 147 even with a scratch global ignore in play, while var/ stays at 0, .env stays out and .env.example stays in, so test_a_gitignored_file_stays_out_of_scope still passes. Add a paragraph to git_paths' docstring naming all three exclude sources and noting `.git/info/exclude` remains outside repo control. Land it with CF-04's floor test, which is what would make a future recurrence visible.
~~~

### [MINOR] Six commit-gated phases landed as one uncommitted eight-file diff, destroying the bisect boundary D7 asked for by name and making Phase 1's restraint criterion unverifiable

~~~
location: git log (HEAD 0826da6, unrelated) vs. IMPLEMENTATION_PLAN.md:81, :126 (Phase 1 AC3) and :332 (D7)

PROBLEM
Raised by all six lenses (acceptance F6, fidelity F4, edgecases F10, parser LG-08, skill-quality LG-09, infra-cost LG-05). I verified: `git log --oneline -3` gives 0826da6 / 4c21117 / edc7aea — no phase commits — and `git status --porcelain` shows all eight files plus the untracked FR in one blob. No rule was broken (nothing committed ad hoc, main untouched), so this is process fidelity, not a violation. The concrete casualty is Phase 1 acceptance criterion 3 — '`git diff --stat` lists exactly one file, and tests/test_leak_guard_scope.py is not in it' — which the plan itself called the thing that makes 'the repro passed on its own terms' a checkable claim. tests/test_leak_guard_scope.py is in the same diff (+114/-8), so from the record alone a reviewer cannot distinguish 'the argv swap turned the repro green' from 'the repro was edited into passing'. That gap was closed by other means (the auditor's read-only replication returned 133 candidates blind to the untracked FR; I measured 146 vs 147), but the plan's own audit trail cannot close it. D7 at :332 chose to bundle the hardening specifically 'so the bisect boundary a purist wants survives'; it does not. Note the unrelated commit 0826da6 sits on this branch and will ride into the same PR.

PROPOSED FIX
See GD-01 — this is a judgment call between re-splitting and recording. Whichever is chosen, the IMPLEMENTATION_REPORT must state that Phase 1 AC3 was not satisfiable from history and paste the 146-vs-147 enumeration measurement in its place. Separately decide whether 0826da6 belongs on this branch.
~~~

### [MINOR] /commit's rewritten Step 2 paragraph now asserts and denies credential scanning three lines apart

~~~
location: .claude/skills/commit/SKILL.md:84-88

PROBLEM
Raised by edgecases F5, parser LG-04 and skill-quality LG-05. I read the block: ':84 It does **not** scan for credentials — nothing in this repo does — so also read the staged diff yourself … :86 `gitleaks` will catch it in CI, but catching it *before* it enters history is the difference between an edit and a history rewrite.' Both halves are inside this diff's blast radius: the same changeset files instance 7 in port-residue-sweep/BUGFIX_REQUEST.md recording that the gitleaks promise is false, and files a whole feature request (secret-scanning/FEATURE_REQUEST.md:18-24) whose thesis is that the claim makes the gap look closed. Leaving the gitleaks sentence unfixed was CORRECT per plan §7 and P5.1 (one finding, one tracker), but moving a true negative claim to sit directly against the retained false positive produced a paragraph worse than either version alone — the contradiction reads as though the author checked and disagreed, and the reader gets no usable instruction.

PROPOSED FIX
Do not edit the gitleaks sentence — P5.1's acceptance requires both occurrences survive byte-identical, and `git grep -n gitleaks -- .claude/` must keep returning commit/SKILL.md:86 and update-docs/SKILL.md:25. Instead flag it in place: after 'nothing in this repo does' add a parenthetical naming the tracker, e.g. '(the `gitleaks` claim below is false and is tracked as instance 7 of `requests/bugfix-requests/port-residue-sweep/`)'. That removes the contradiction without touching the owned token.
~~~

### [MINOR] port-residue-sweep gained a seventh instance row but its own count and Index summary still say six

~~~
location: requests/bugfix-requests/port-residue-sweep/BUGFIX_REQUEST.md:11 and :56; requests/bugfix-requests/README.md (port-residue-sweep row)

PROBLEM
Raised only by the independent verifier's ledger (P5.4); I confirmed it directly with Select-String. Phase 5 step 3 correctly added the second-gitleaks-occurrence instance as row 7 (+7 lines in `git status --porcelain`) and correctly fixed neither occurrence. But the surrounding counts were not updated: :11 still reads 'Six instances are known, and they were not found by one search:' above what is now a seven-row table, :56 still says 'six known divergences, five found incidentally, one still live', and requests/bugfix-requests/README.md's Index row still summarises it as 'Six known places where the ported skills still describe a sibling repo'. Small, but it is internal-consistency drift introduced by this change, in the very request whose subject is stale ported prose.

PROPOSED FIX
Update BUGFIX_REQUEST.md:11 to 'Seven instances are known', reconcile :56's tally against the table before writing it, and update the Index row's summary sentence in requests/bugfix-requests/README.md to match.
~~~

### [MINOR] The is_file() skip is silent and uncounted, and its own docstring promises the opposite for undecodable paths

~~~
location: tests/test_no_leaks.py:122 vs. the docstring claim at :52-53

PROBLEM
Raised by fidelity F7, correctness F6, edgecases F9 and parser LG-05 (minor/nit, medium confidence throughout). git_paths' docstring at :52-53 justifies `errors="surrogateescape"` with 'so an undecodable byte survives round-trip instead of raising, since a path we cannot decode is exactly one worth still checking' — but the next consumer is `if not path.is_file(): continue` at :122, and `pathlib.Path.is_file()` swallows both OSError and ValueError and returns False. So a surrogate-bearing path, a permission-denied file, or an ELOOP symlink is dropped with no signal, indistinguishable from the intended tracked-but-deleted case — the silent-drop shape the comment at :119-121 explicitly warns against ('a broad `except Exception` here would swallow a real read failure and restore exactly the silent blindness this guard was widened to remove'). Windows impact is near zero (NTFS names are UTF-16) and CI is not this machine, hence medium confidence — but the code and its own docstring disagree, and the docstring is what a future agent will trust. Secondary point from acceptance F4: the check lives in the test rather than in `scannable_text_files()`, so the public seam hands out Paths that may not resolve, and the regression test at tests/test_leak_guard_scope.py:188-200 must monkeypatch a synthetic list rather than exercise the real enumeration — with named downstream consumers already queued in first-sight's plan and the secret-scanning FR.

PROPOSED FIX
Make behaviour match the promise: skip only when the path is genuinely absent (`if not path.exists() and not path.is_symlink(): continue`) and add `except OSError as exc: violations.append(f"{rel}: unreadable: {exc}")` alongside the existing narrow `except UnicodeDecodeError`, so a stat/read failure is loud. Alternatively soften :52-53 to say surrogateescape prevents an enumeration-time crash and such a path is then REPORTED as unscannable. Consider moving the absence check into `scannable_text_files()` just before the suffix test at :78 so downstream consumers inherit it. Separately add `gm/` to the measured-holes docstring at :142-149 — `!gm/` and `!gm/**` at .gitignore:58-59 punch the same last-match-wins hole, and gm/ is the one directory this repo deliberately tracks (ADR 0011).
~~~

### [MINOR] Test probes are written into non-gitignored repo directories and are now visible to the guard they test, so a killed run reds the suite with a misleading message

~~~
location: tests/test_leak_guard_scope.py:40-53 (`untracked_file`), used at :73, :119, :136, :153, :166, :176, :182

PROBLEM
Raised by acceptance F7, correctness F5, edgecases F6, parser LG-06 and skill-quality LG-07. `untracked_file()` writes real files into the working tree and removes them in a `finally`, which survives an assertion failure or Ctrl-C but not a hard kill, a crashed runner, or a reboot mid-run. Before this fix a survivor was invisible to the guard; it no longer is. Two sharp cases: `requests/bugfix-requests/_leak_guard_nested_probe.md` carries the constructed banned string and would make test_no_machine_paths_or_identifiers red, and `tests/fixtures/_leak_guard_probe.dat` at :166 would make test_game_data_is_not_tracked red — in a directory `.gitignore:65`'s `!tests/fixtures/**` negation deliberately un-ignores, so it is also stageable. The resulting message points at an ADR 0006 violation rather than at an abandoned test run, the most expensive kind of false alarm. Worse, the `assert not path.exists(), "...refusing to clobber it"` at :48 means the next run does not self-heal — it errors at setup. Related invariant nobody recorded: the widening also couples the suite to sequential single-process execution (no pytest-xdist configured; pyproject.toml:100 addopts has no `-n`), so adding `-n auto` later would make it non-deterministically red. Current tree is clean of residue — I confirmed via `git status --porcelain` after my runs.

PROPOSED FIX
Add a session-scoped autouse fixture that sweeps `_leak_guard_*` under REPO_ROOT, tests/fixtures/ and var/tmp/ before and after the session, and give probe names a per-process suffix (os.getpid() or uuid4().hex[:8]) so a concurrent run cannot collide. Downgrade the :48 assert to unlink-and-warn when the path carries the reserved `_leak_guard_` token, keeping the clobber guard for any other path. Add a comment on `untracked_file` recording that its probes are deliberately visible to the widened guard, so the suite must not be parallelised across processes.
~~~

### [NIT] Two new tests are weak: one is tautological, one can pass vacuously on a loose substring

~~~
location: tests/test_leak_guard_scope.py:144-147 and :177

PROBLEM
Raised by skill-quality LG-08 and correctness F4. (1) `test_enumeration_yields_no_empty_entries` asserts `"" not in guard.git_paths(...)`, but git_paths at tests/test_no_leaks.py:62 returns `[rel for rel in decoded.split("\0") if rel]` — the empty string is filtered by the very expression that builds the list, so the assertion is a tautology for any form of that comprehension. Its own docstring names the property it actually cares about ('a blank entry would resolve to REPO_ROOT itself and quietly turn a directory into a scan candidate') and does not test it. (2) `test_the_game_data_guard_still_ignores_var` asserts `not [o for o in guard.game_data_offenders() if "var/" in o]`, which holds whenever the offender list is empty for ANY reason — the opposite of what a counterweight is for — and `"var/" in o` is unanchored, so it would also match `harvard/x.dat`. Its probe at var/tmp/_leak_guard_probe.dat is ignored twice over (`var/` at .gitignore:18 AND `*.dat` at :34), so the test cannot even distinguish which rule did the work.

PROPOSED FIX
(1) Replace the tautology with the downstream property: `assert REPO_ROOT not in guard.scannable_text_files()`, which fails the moment a blank entry survives regardless of how git_paths is written. (2) Pair the var/ counterweight with a positive control in the same test — write both the var/ probe and a tests/fixtures/ probe, assert the fixtures path IS an offender while the var path is NOT — and anchor the check with `o.startswith("var/")`.
~~~

### [NIT] The keep-suffix comparison is case-sensitive, so an uppercase extension is silently unscanned

~~~
location: tests/test_no_leaks.py:78 and :156

PROBLEM
Raised by edgecases F8. `p.suffix in keep` compares exactly: `Path('NOTES.MD').suffix` is `'.MD'`, which is not in `{'.md', ...}`. A file committed as README.MD, CONFIG.YML or notes.TXT — trivially easy on Windows, the development platform here, which is case-preserving — is dropped from the candidate set with no signal. Nothing in the tree hits it today (I measured all 12 suffix-drops; every remaining candidate uses lowercase extensions), so it is latent — but it is the same silent-drop shape the `-z`/encoding work was undertaken to eliminate, and it costs one method call. `game_data_offenders()` at :156 has the same exposure: `Path(rel).suffix in banned_suffixes` would miss a `SAVE.DAT`.

PROPOSED FIX
Use `p.suffix.lower() in keep or p.name == ".env.example"` at :78 and mirror it at :156 with `Path(rel).suffix.lower() in banned_suffixes`.
~~~

### [NIT] git_paths() can return a path three times during an unresolved merge

~~~
location: tests/test_no_leaks.py:39-62

PROBLEM
Raised by infra-cost LG-06. `git ls-files --cached` lists an unmerged path once per stage (1/2/3), so during a conflicted merge `git_paths("--cached", "--others", "--exclude-standard")` yields duplicates and the same violation is reported up to three times; `game_data_offenders()` would likewise triple an offender. Cosmetic rather than a miss, but it makes the guard's output confusing in exactly the situation where someone is already under pressure. Nothing pins uniqueness — `test_enumeration_yields_no_empty_entries` covers only the blank-entry edge, and is itself tautological (CF-17).

PROPOSED FIX
Return `list(dict.fromkeys(rel for rel in decoded.split("\0") if rel))` — order-preserving dedup, one line — and add `assert len(paths) == len(set(paths))` to the enumeration test.
~~~

### [NIT] Three memory entries appended where the plan asked for one, each roughly double the file's own length rule

~~~
location: .claude/agents/data-engineer-memory.md:318-339 vs. its own format rule at :31

PROBLEM
Raised by fidelity F9 and skill-quality LG-10. Plan Phase 4 step 4 asked for one appended correcting entry with an epistemic label; three landed (the correction, the C-quoting/cp1252 measurement, and the gitignore last-match-wins measurement) at 8, 7 and 7 lines against the file's own rule at :31 ('Keep an entry to about four lines'), adding ~22 lines to a file whose curation trigger now fires from /update-docs when it appears in a staged diff (commit b32f325). All three carry valid labels and tests/test_agent_contract.py is green, so this is the unenforced half of that section, and the two extra entries do record genuinely reusable tooling traps. Also: the superseded 2026-08-16 entry's evidence pointer at :87 still names `tracked_text_files()` — correct as history, but reading as a live pointer to a function that no longer exists.

PROPOSED FIX
No change strictly required. If tightening is wanted, compress each toward the four-line shape at :31 — the cp1252 entry in particular duplicates reasoning already carried verbatim in the git_paths docstring at tests/test_no_leaks.py:40-53. Consider adding '(then named `tracked_text_files()`)' to the superseded entry's pointer at :87. Expect /update-docs to raise this at the commit gate anyway.
~~~

## Meta-audit findings (5)

### [MAJOR] CF-11 dropped the one concrete remediation and adopted the wrong side of a measured disagreement — and its recommended fix arms the failure it dismissed as latent

~~~
location: merged report CF-11 (evidence clause "Latent here: git config --get core.excludesFile exits 1") vs. fidelity F8 / correctness F3; repo anchor .gitignore and tests/test_no_leaks.py:72

PROBLEM
Six lenses raised the `--exclude-standard` machine-dependence. Two of them (fidelity F8, correctness F3) ran the DIRECT check — `git check-ignore -v --no-index .claude/settings.local.json` — and reported that the match comes from the operator's GLOBAL ignore file. Four others (acceptance F5, edgecases F7, skill-quality LG-02, and verify pass V12) ran `git config --get core.excludesFile`, got exit 1, and concluded the hazard is "latent" / "no live impact". I reproduced both: `git config --get core.excludesFile` exits 1, AND `git check-ignore -v --no-index .claude/settings.local.json` returns `"[C]:\Users\jorda/.config/git/ignore":3:**/.claude/settings.local.json` (exit 0). Git falls back to the XDG default `~/.config/git/ignore` when core.excludesFile is unset; that file exists and carries two live rules. So the hazard is ACTIVE on this machine, not latent. The merge adopted the wrong side: CF-11's evidence repeats "Latent here", uses that to justify the major→minor downgrade, and drops fidelity F8's / correctness F3's remediation (add `.claude/settings.local.json` to the repo `.gitignore`) entirely — it appears nowhere in CF-11's proposed_fix, in any other CF, or in the gated decisions. Worse, CF-11's recommended fix makes it dangerous: `git -c core.excludesFile= ls-files ...` disables the only rule excluding that path, `.json` is in the `keep` set at tests/test_no_leaks.py:72, and Claude Code writes permission entries containing absolute filesystem paths into that file — so the recommendation arms a red `test_no_machine_paths_or_identifiers` on a file that can never be committed. I measured that the fix is inert TODAY only because the file is absent: with and without `-c core.excludesFile=` the enumeration is 147 either way.

PROPOSED FIX
Rewrite CF-11. Replace the "Latent here" evidence with the measured fact: `git check-ignore -v --no-index .claude/settings.local.json` resolves to the operator's global ignore file, so an un-versioned rule is ALREADY shaping the guard's candidate set, and `git config --get core.excludesFile` returning empty does not mean no global ignore is in force. Restore the dropped remediation and make it a PRECONDITION of the neutralisation: add `.claude/settings.local.json` (and any sibling `*.local.json` the harness writes) to the repo `.gitignore` FIRST, then apply `git -c core.excludesFile=` at tests/test_no_leaks.py:56 — never the second without the first. Reconsider the major→minor downgrade, since its stated rationale (V12's blast-radius correction plus "latent here") is now half-false.
~~~

### [MAJOR] U4 — the verdict's first stated ground — is attributed to the ROOT_CAUSE_ANALYSIS, which contains no such requirement

~~~
location: merged report acceptance_ledger U4 ("source": "ROOT_CAUSE_ANALYSIS.md — upstream acceptance contract for this stage") and verdict_rationale sentence 1

PROBLEM
U4 reads: "Bugfix-run acceptance ledger MUST carry a 'red repro now green + regression test present' row", sourced to ROOT_CAUSE_ANALYSIS.md. I read that file's structure and grepped all 130 lines: `Select-String -Pattern "ledger|IMPLEMENTATION_REPORT|acceptance|definition of done|regression test"` returns ZERO matches, and a narrower grep for `IMPLEMENTATION_REPORT|ledger` returns count 0. Its headings are Verdict / Reproduction (red) / Evidence (the cause) / Two corrections to the intake report / The idiom that does work, measured / Fix posture (tiered) / What this does not close. The requirement is genuine but lives in IMPLEMENTATION_PLAN.md Phase 6 step 1 (:265-266) — a PLAN phase, not the upstream contract. The consequence is material: verdict_rationale opens "Not 'go': the upstream bugfix-track contract requires an acceptance ledger carrying the 'red repro now green + regression test present' row", and the U4 row itself is labelled "the single unmet UPSTREAM criterion and the reason the verdict is 'fix'". On the actual upstream contract (red repro green + regression test + nothing regresses) ALL THREE criteria are met, and the 'fix' verdict rests entirely on plan-phase criteria P6.1, P6.2 and P1.3. Compounding it, U4's reconciliation claims "Auditor 'unmet'; the verifier routes the same fact through P6.1 'unmet'. Both agree" — but the independent verifier's ledger has no U4 row at all and never asserted the criterion is upstream; it filed the fact as a plan criterion. A one-sided invention is presented as two-sided agreement.

PROPOSED FIX
Re-source U4 to `IMPLEMENTATION_PLAN.md:265-266` (Phase 6 step 1) and the bugfix track's process docs, or fold it into P6.1 and delete the standalone row. Rewrite verdict_rationale's first sentence to state the true ground: all three upstream RCA criteria are MET; the verdict is 'fix' because plan Phase 6 (P6.1, P6.2) is unexecuted and P1.3 is unmet. Correct U4's reconciliation to record that only the auditor asserted this as an upstream criterion. The verdict itself ('fix') stands — only its stated basis is wrong.
~~~

### [MAJOR] Merged P5.2 silently deleted the half of the criterion the verifier had marked 'met' on false evidence, leaving D8's 'one sentence, not a restructure' adjudicated nowhere

~~~
location: merged report acceptance_ledger P5.2 vs. independent verifier P5.2; anchor .claude/skills/commit/SKILL.md:74-88

PROBLEM
The independent verifier's P5.2 criterion read: "Phase 5: first-sight's plan no longer instructs a reader to work around this defect; the /commit ordering sentence lands as one concrete command", with evidence asserting the change is "one sentence plus a command, not a restructure, exactly as D8 specified". I measured that claim false: `git diff HEAD -- .claude/skills/commit/SKILL.md` removes 3 lines and adds 12, including a fenced code block and a new paragraph — precisely what fidelity F5 measured as "a net +9 lines in the skill's already-longest step" against plan §5 D8's "one sentence, not a restructure" (:337-340) and Phase 5 step 1's explicit REPLACE instruction (:236-239). The merge did not correct the verifier's false claim; it removed the clause. Merged P5.2's criterion is now only "first-sight's plan no longer instructs a reader to work around this defect, marked as dated amendments", verdict 'met'. Narrowing a criterion until the surviving half passes converts a partial into a met — the exact pattern a meta-audit is meant to catch — and it is undisclosed: the reconciliation field discusses only the :623 residue, never the deleted clause. Fidelity F5 is the only place that measurement survives, and it appears in no confirmed finding; the gated decision names D8 but never states the measured 3→12 deviation, so a reader deciding 'accept or revert' has no number in front of them.

PROPOSED FIX
Restore the deleted clause and re-verdict P5.2 as 'partial': the first-sight half is met; the /commit half deviates from D8's explicitly-argued shape (3 lines replaced by 12, plus a code fence, and the manual eyeball was KEPT rather than replaced as Phase 5 step 1 directed). Record in the reconciliation that the independent verifier asserted this half 'met' on evidence that does not survive a diff read. Add the measured 3→12 line count to gated decision #3 so the accept-or-revert call is made on a number rather than an adjective.
~~~

### [MINOR] P0 was declared 'not-verifiable' by both ledgers and the merge without either reading the one commit that bears on it — and CF-12 then asks a question that commit already answers

~~~
location: merged report acceptance_ledger P0 and CF-12 proposed_fix ("Separately decide whether 0826da6 belongs on this branch")

PROBLEM
Plan Phase 0 step 1 (:91-94) reads: "Confirm the tree is clean... If the first-sight baseball artifacts are still uncommitted, land them first or stash nothing — just record what is outstanding and account for it." Both ledgers marked P0 'not-verifiable' on the ground that no baseline record exists, and neither examined `git show 0826da6` — the commit that sits between the plan commit 4c21117 and the working tree. I read it: its body states verbatim "Rides along on the leak-guard branch so first-sight's plan is already correct when that feature is picked back up. Unrelated to the leak guard; kept as its own commit for that reason." That is directly responsive evidence — it shows outstanding first-sight work being landed as its own commit before implementation, which is Phase 0 step 1's instruction being followed and recorded, in the git record rather than in the missing report. Because nobody read it, the merge also inherits a redundant ask: CF-12's proposed_fix tells the operator to "decide whether 0826da6 belongs on this branch", a decision the commit body already documents explicitly.

PROPOSED FIX
Re-verdict P0 as 'partial' rather than 'not-verifiable', citing `git show 0826da6`'s body as the surviving record of Phase 0 step 1 (outstanding work landed as its own commit, with the reason stated), and noting that the numeric half — the tally, both enumeration counts, branch and SHA — remains unrecorded pending CF-01's report. Delete the "decide whether 0826da6 belongs on this branch" clause from CF-12's proposed_fix, or replace it with a pointer to the commit body that already answers it.
~~~

### [MINOR] CF-01's headline corroboration is a redundancy artifact: lenses with no surface in their own remit converged on the same trivially-checkable absent file

~~~
location: merged report CF-01 ("Raised independently by all six lenses... and CONFIRMED by seven separate verify passes") vs. CF-04 (single-lens origin)

PROBLEM
CF-01 is presented with multiplicity as evidentiary weight — seven lens-findings and seven verify passes for the same fact, which is the presence or absence of one file in one directory. That number is not independent corroboration; it is what happens when lenses whose remit has no surface migrate to the easiest shared target. The parser lens is the clearest case: its own summary opens "PARSER-INTEGRITY LENS: no surface. git diff HEAD --stat -- src/ is empty", and it then filed eight findings, none about a parser, two of them (LG-01, LG-08) duplicates of CF-01 and CF-12. Meanwhile CF-04 — the coverage floor, where an EXEMPT_PREFIXES change was MEASURED to collapse the scanned set from 134 to 9 while all 18 guard tests stayed green, i.e. the sharpest technical defect in the report and the one that reproduces the RCA's own named regression class — was raised by exactly ONE lens (skill-quality LG-01), as was CF-05 (parser LG-02, an executable instruction that produces wrong work). A reader triaging by the stated corroboration counts will start with a missing markdown file and reach the two findings with real teeth last.

PROPOSED FIX
In CF-01's problem field, replace "raised independently by all six lenses" with the count plus the caveat that the fact is a single directory listing and multiplicity here reflects lens overlap, not independent confirmation. Order confirmed_findings by consequence rather than by raiser count — CF-04 and CF-05 ahead of CF-01 — or add a one-line note to the summary flagging that CF-04 and CF-05 are single-lens findings that survived verification and should not be discounted for it. For future runs, have a lens that finds no surface in its remit say so and stop, rather than re-deriving other lenses' findings.
~~~

## Low-severity findings (39)

### [MINOR] The guard still describes itself as scanning only 'tracked' files — the exact narrow self-description Phase 4 spent a whole phase eliminating

~~~
location: tests/test_no_leaks.py:1, :133, :160, :163

PROBLEM
D4's stated rationale for renaming tracked_text_files was that 'a function called tracked_* that scans untracked files re-arms the very argument the RCA rejected — the next agent would read the name, conclude the widening was a mistake, and narrow it back.' The rename landed, but three sibling self-descriptions did not. The module docstring at :1 still reads 'Nothing machine-specific may be tracked' — and that is precisely the sentence the ROOT_CAUSE_ANALYSIS quoted as the works-as-intended counterargument it had to overrule. The failure message at :133 reads 'machine-specific values in tracked files', which is now false: it will fire on a file that is not tracked. And the second enumeration is still named test_game_data_is_not_tracked (:160) with the message 'OOTP game data must never be tracked' (:163) despite Phase 3 having widened it to untracked files too. A future reader following the docstring rather than the function name reaches exactly the wrong conclusion about the guard's intended scope.

PROPOSED FIX
Update tests/test_no_leaks.py:1 to state the widened intent (e.g. 'Nothing machine-specific may exist in a file this repo could ship — tracked or merely written'), change the :133 message to 'machine-specific values in scannable files', and either rename test_game_data_is_not_tracked to test_game_data_is_not_present (updating its :163 message likewise) or add a one-line comment there recording that the check deliberately fires before staging. Keep the tests/test_leak_guard_scope.py assertion messages byte-identical per D4; these three are in the other file and are not covered by that rule.
~~~

### [MINOR] Stale file:line citations introduced by this change, including in a line the change itself edited

~~~
location: tests/test_leak_guard_scope.py:36 and requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561

PROBLEM
Inserting the 8-line D3 refusal comment at tests/test_no_leaks.py:18-25 and the git_paths helper shifted every anchor below them, and three citations were not re-pointed. (1) tests/test_leak_guard_scope.py:36 says the probe 'Matches the "windows drive path" pattern at `tests/test_no_leaks.py:25`'; line 25 is now the tail of the refusal comment ('# it was accepted with that cost in view...') and the pattern is at :33. (2) requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561 — a line this change rewrote — still says 'The existing guard bans four filenames and two suffixes at `:106-107`' (now :151-152) and 'reuse the existing `PATTERNS` at `:24-28`' (now :32-36). (3) The adjacent acceptance line in the same first-sight step cites test_patterns_still_catch_real_leaks at `:51-78`; it is now :83-110. In a repo that treats citation accuracy as load-bearing and files bugfix requests about ported-artifact drift, amending a sentence while leaving its anchors pointing at the wrong lines is the same drift class.

PROPOSED FIX
Re-point tests/test_leak_guard_scope.py:36 to `tests/test_no_leaks.py:33`. In requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561, update `:106-107` -> `:151-152` and `PATTERNS at :24-28` -> `:32-36` inside the amendment already being written there, and update the `:51-78` anchor on the following acceptance line to `:83-110`. Prefer symbol names over line numbers where the sentence allows it — `game_data_offenders()`'s banned sets, `PATTERNS`, `test_patterns_still_catch_real_leaks` — since those survive the next insertion.
~~~

### [MINOR] The deleted-path guard sits in the test rather than in the enumeration seam, so scannable_text_files() hands out paths that may not exist

~~~
location: tests/test_no_leaks.py:122-123

PROBLEM
`--cached` lists tracked-but-deleted paths, and the `if not path.is_file(): continue` fix was placed inside test_no_machine_paths_or_identifiers rather than inside scannable_text_files(). The public seam therefore returns Path objects that may not resolve, and the regression test at tests/test_leak_guard_scope.py:188-200 has to monkeypatch the enumerator to a synthetic one-element list to exercise it — it never proves the real enumeration + real filter combination. This matters because the seam already has named downstream consumers: requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561 directs a future step to extend this module reusing the existing helpers, and requests/feature-requests/secret-scanning/FEATURE_REQUEST.md:47-49 names `git_paths()` 'and two helpers' as the model seam for a credential scanner. Each new consumer must independently rediscover that it has to call is_file() first, and the docstring at :65-71 does not warn them. game_data_offenders() has the same asymmetry in the other direction (it will report a deleted-but-still-indexed .dat), which is arguably correct but is undocumented.

PROPOSED FIX
Move the `if not p.is_file(): continue` check into scannable_text_files() just before the suffix test at tests/test_no_leaks.py:78, keeping the narrow-catch comment with it, and drop the now-redundant check in the test. Add one sentence to game_data_offenders()'s docstring stating that a tracked-but-deleted path is still reported, and why that is intended (it is still in the index). Then rewrite tests/test_leak_guard_scope.py:188-200 to exercise the real enumeration if a deleted-path fixture can be arranged read-only, or keep the monkeypatch but assert against scannable_text_files() itself rather than the test function.
~~~

### [MINOR] `--exclude-standard` silently inherits per-machine exclude files that nothing in the repo controls or documents

~~~
location: tests/test_no_leaks.py:56

PROBLEM
`git ls-files --others --exclude-standard` honours three exclude sources, not one: .gitignore, .git/info/exclude, and the user's global core.excludesFile. Only the first is tracked. A developer with, say, `*.md` or `notes/` in a global ignore file would have those paths silently removed from the guard's candidate set on their machine, while CI — which has neither a global excludes file nor any untracked files — stays green and never reveals the gap. That is the same shape of failure this bugfix exists to close, just relocated. Measured on this machine there is no live impact: `git config --get core.excludesFile` exits 1 (unset) and .git/info/exclude contains only comments. But nothing in git_paths()'s otherwise-thorough docstring (:40-53) or in the scope tests records the dependency, and the .gitignore-respecting property is currently pinned only against .gitignore-sourced exclusions (tests/test_leak_guard_scope.py:81-105).

PROPOSED FIX
Add a paragraph to git_paths()'s docstring at tests/test_no_leaks.py:40-53 naming all three exclude sources and stating that only .gitignore is under repo control, so a machine-local exclude can narrow the guard without any signal. If stronger protection is wanted, have the guard assert at import or in a dedicated test that `git config --get core.excludesFile` is unset and .git/info/exclude has no active patterns, failing loudly rather than shrinking silently — that is cheap and matches the module's own 'seen to fail' standard.
~~~

### [MINOR] Six commit-gated phases landed as one uncommitted 8-file diff, destroying the bisect boundaries D1 and D7 explicitly asked for

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md:81 (and D1, D7, Phase 1 acceptance #3)

PROBLEM
`git log --oneline -5` shows the newest commit is 0826da6, unrelated to this work; `git status --porcelain` shows all eight touched files uncommitted. The plan opens §3 with 'Six phases, each ending at a /commit-gated checkpoint on a green local run', D1 says the second enumeration 'Lands as its own commit (Phase 3)', and D7 bundles the hardening 'as its own commit rather than a separate request'. None of that exists. The concrete casualty is Phase 1 acceptance criterion 3 — 'git diff --stat lists exactly one file, and tests/test_leak_guard_scope.py is not in it' — which the plan itself called the thing that makes 'the repro passed on its own terms' a checkable claim. tests/test_leak_guard_scope.py is in the same diff (114 lines changed), so from the record alone a reviewer cannot distinguish 'the argv swap turned the repro green' from 'the repro was edited into passing'. I closed that gap by other means (replicating the pre-fix enumeration read-only proved the repro was genuinely red), but the plan's own audit trail cannot.

PROPOSED FIX
Split the work into the planned commits when running /commit: (1) tests/test_no_leaks.py argv only; (2) git_paths + decode + is_file + the Phase 2 regression tests; (3) the second enumeration, the game_data_offenders seam and .gitignore:27 with its tests; (4) the rename plus the memory append; (5) the three prose corrections; (6) the report, statuses and the secret-scanning FR. If splitting is no longer practical, record in IMPLEMENTATION_REPORT.md that Phase 1 AC3 was not satisfiable and paste the read-only replication that proves the repro was red at HEAD in its place.
~~~

### [MINOR] The plan's six `/commit`-gated checkpoints collapsed into one uncommitted lump, destroying the bisect boundary D7 asked for by name

~~~
location: git log (HEAD = 0826da6, unrelated to this fix) vs. IMPLEMENTATION_PLAN.md:81 and :168

PROBLEM
The plan opens §3 with 'Six phases, each ending at a `/commit`-gated checkpoint on a green local run', gives every phase a Commit note, and §5 D7 justifies bundling the hardening specifically by promising it lands as 'its own commit, so the bisect boundary a purist wants survives'. In reality `git log --oneline` shows the last commit on `fix-leak-guard-untracked-blindness` is `0826da6 Settle the team_roster list_id enum by reading the game`, and all eight modified files plus the new feature request sit uncommitted. Two concrete consequences. (1) Phase 1's central restraint — 'the repro goes green WITHOUT touching tests/test_leak_guard_scope.py', which the plan calls out as 'what makes "the repro passed on its own terms" a checkable claim' — cannot be checked from history at all, because the repro module is modified in the same working-tree state as the fix. I substituted the only available check: I read every hunk of `git diff HEAD -- tests/test_leak_guard_scope.py` and confirmed the seven pre-existing tests changed only by the `tracked_text_files` -> `scannable_text_files` rename and docstring prose, with all four assertion messages byte-identical. The substance holds; the checkability the plan engineered for does not. (2) Phase 3's `.gitignore` tightening and Phase 2's hardening are no longer separately bisectable. No commit constraint was violated — nothing was committed ad hoc, `main` was not touched — so this is process fidelity, not a rules breach.

PROPOSED FIX
Either land the work as the plan's phase sequence via `/commit` (argv swap; hardening; second enumeration + `.gitignore`; rename + memory; prose; close), or record in the IMPLEMENTATION_REPORT that the phases were collapsed into a single commit, why, and how Phase 1's 'repro untouched' restraint was verified instead (the hunk-level diff read above). An unrecorded deviation from an explicitly-argued decision is the thing to avoid; a recorded one is fine.
~~~

### [MINOR] Phase 5 step 1 grew commit/SKILL.md Step 2 by ~10 lines and a code fence, against D8's explicit 'one sentence, not a restructure'

~~~
location: .claude/skills/commit/SKILL.md:77-88 (diff replaces 3 lines with 12)

PROBLEM
Plan §5 D8 is unusually specific: 'Direction (d) lands as one sentence, not a restructure', and Phase 5 step 1 says to REPLACE the manual eyeball at `:77` with a concrete `uv run pytest tests/test_no_leaks.py` after staging, with the stated rationale that 'Step 2 is already the skill's longest, and a gate people route around is worse than a light one.' The implementation instead kept the manual eyeball, added a new prose paragraph, a fenced command block, and a new sentence about credentials — a net +9 lines in the skill's already-longest step. On the merits the addition is defensible and arguably better than what was planned: the guard genuinely does not scan for credentials, so deleting the manual eyeball would have overstated what the automated check buys, and the new text says so explicitly. But the plan decided the opposite shape by name, and nothing in the diff argues the reversal. Note the restraint that WAS honoured: `git grep -n gitleaks -- .claude/` still returns both occurrences (commit/SKILL.md:86, update-docs/SKILL.md:25) and update-docs/SKILL.md is untouched, so Phase 5 acceptance 1 and the port-residue-sweep ownership boundary hold.

PROPOSED FIX
Keep the text — it is better than the planned version — but record the deviation and its reasoning in the IMPLEMENTATION_REPORT (F1), noting that D8's 'replace the eyeball' was reinterpreted as 'add the command and keep the eyeball, because the guard covers three shapes and credentials is not one of them'. If Step-2 length is genuinely a concern, tighten the added block to the command plus the one-clause caveat and drop the re-explanation of what the guard covers, which now also lives in the memory entry and the secret-scanning request.
~~~

### [MINOR] New comment block in test_no_leaks.py silently invalidated the repro module's own citation of the drive-path pattern

~~~
location: tests/test_leak_guard_scope.py:36 citing tests/test_no_leaks.py:25

PROBLEM
tests/test_leak_guard_scope.py:35-37 reads: 'A banned string built at runtime so this file never contains one. Matches the "windows drive path" pattern at `tests/test_no_leaks.py:25`.' That citation was correct before this change (the plan records PATTERNS at `:24`). The D3 refusal comment added at tests/test_no_leaks.py:18-25 pushed PATTERNS down to `:32`, and the windows-drive-path entry now sits at `:33` — `:25` is now the last line of the EXEMPT_PREFIXES comment. The implementation edited this exact module (rename plus eight new tests) and edited its docstring, so the stale anchor was in front of the author. It is small, but it is inside the pair of files the whole request is about, and this repo has an open bugfix request devoted to precisely this drift class.

PROPOSED FIX
Change tests/test_leak_guard_scope.py:36 to cite `tests/test_no_leaks.py:33`, or better, drop the line number and cite the pattern by its label — `the "windows drive path" entry in tests/test_no_leaks.py PATTERNS` — so the next insertion into that file cannot rot it again.
~~~

### [MINOR] The `is_file()` skip silently drops exactly the undecodable paths the `surrogateescape` docstring says are worth checking

~~~
location: tests/test_no_leaks.py:52-53 (docstring claim) vs. tests/test_no_leaks.py:122 (`if not path.is_file(): continue`)

PROBLEM
git_paths' docstring at :52-53 justifies `errors="surrogateescape"` with 'so an undecodable byte survives round-trip instead of raising, since a path we cannot decode is exactly one worth still checking'. But the scan at tests/test_no_leaks.py:122 skips anything for which `Path.is_file()` is False, and on this platform a surrogate-bearing path cannot be encoded to the filesystem encoding — measured: `sys.getfilesystemencoding()` is `utf-8` with `surrogatepass`, and `Path('x' + chr(0xdc80) + '.md').is_file()` returns **False** rather than raising, because `Path.is_file()` swallows ValueError. So a path that survived the decode via surrogateescape is then dropped silently by the very guard added to prevent silent drops — the shape the plan's Phase 2 step 5 warns about ('a bare `except Exception` would re-create silent blindness'), reached through a different door. Practical impact on Windows is near zero (NTFS names are UTF-16, so undecodable bytes essentially cannot occur) and the CI runner is not the machine this was measured on, which is why I rate this medium rather than high — but the code and its own docstring currently disagree.

PROPOSED FIX
Either make the behaviour match the docstring — detect surrogates in the decoded path and append to `violations` as an explicit 'unreadable path' entry rather than skipping, so the guard fails loudly on a path it cannot inspect — or soften the docstring at tests/test_no_leaks.py:52-53 to say that surrogateescape prevents an enumeration-time crash and that such a path is then reported as unscannable, not scanned. Do not leave the current mismatch: the docstring is the thing a future agent will trust.
~~~

### [MINOR] The widened exclusion set now depends on the developer's GLOBAL gitignore, which the plan's evidence table never measured

~~~
location: tests/test_no_leaks.py:74 (`git_paths("--cached", "--others", "--exclude-standard")`) vs. IMPLEMENTATION_PLAN.md:53-59 (the measured evidence table)

PROBLEM
`--exclude-standard` reads three sources: the repo `.gitignore`, `.git/info/exclude`, AND the user's global `core.excludesFile`. The plan's evidence table measured only repo-level outcomes (`.venv/`, `__pycache__/`, `node_modules/`, `var/`, `.env`, `.env.example`) — all of which are in the repo `.gitignore`. I checked one case that is not: `git check-ignore -v .claude/settings.local.json` reports the matching rule as `**/.claude/settings.local.json` in the operator's GLOBAL git ignore file, not in `.gitignore`. That file does not currently exist here so nothing is affected today, but the consequence is that the guard's candidate set is now machine-dependent: on a contributor machine without that global rule, an untracked `.claude/settings.local.json` (which typically contains permission entries carrying filesystem paths) enters the scan and can turn the whole local suite red for reasons unrelated to the change under test. That is exactly the 'a check that cries wolf gets switched off' failure mode the six counterweight tests exist to prevent, arriving through a source the counterweights do not cover. CI is unaffected — a fresh checkout has no untracked files at all, which incidentally means the widening is a no-op there and the regression tests are the only thing exercising it.

PROPOSED FIX
Add `.claude/settings.local.json` (and any other genuinely-local file currently covered only by a global ignore) to the repo's own `.gitignore`, so the guard's exclusion set is reproducible from tracked state rather than from whatever is configured on one machine. Optionally add a counterweight test in tests/test_leak_guard_scope.py asserting that a probe at that path stays out of `scannable_text_files()`, which would fail today on a machine without the global rule and thereby pin the repo-level fix.
~~~

### [MINOR] The new leak-guard sentence in /commit gives a rationale the fix just falsified, and re-teaches the defect's premise

~~~
location: .claude/skills/commit/SKILL.md:77

PROBLEM
The added text reads: run the leak guard 'after staging rather than before — it enumerates through git, so this is the point at which it can see everything the commit will contain.' The causal clause is now WRONG and is precisely the belief this bugfix removed. After the change, `scannable_text_files()` at tests/test_no_leaks.py:74 passes `--others --exclude-standard`, so the guard sees an unstaged file; staging is no longer what grants it sight. I verified this directly: `git ls-files --cached --others --exclude-standard` on this tree returns 147 entries including the UNSTAGED `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md`, while bare `git ls-files` returns 146. The same change amends requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561 to say the opposite — 'Running the guard after staging is still the habit ... but it is no longer load-bearing for detection' — so the diff contradicts itself across two tracked files. It also runs against the plan's own §5 D8, which explicitly rejected the literal 'stage before you verify' framing because it 'buys nothing for detection and nudges toward the `git add -A` habit the skill exists to forbid'; the value D8 wanted was the concrete command, not the ordering claim. A future agent reading SKILL.md:77 learns the pre-fix mental model and may 'restore' the narrow enumeration on that basis — the same regression risk D4 cited to justify the rename.

PROPOSED FIX
Keep the concrete `uv run pytest tests/test_no_leaks.py` command and drop or invert the rationale clause. Something like: 'Then run the leak guard. Since 2026-08-17 it enumerates untracked files too, so it does not need staging to see your work — run it here anyway, because staging is also when a force-added ignored file first becomes visible to it.' That preserves the only case where staging genuinely changes the guard's input (a `git add -f` of a gitignored path, which `--cached` picks up and `--exclude-standard` cannot filter) without re-teaching the fixed defect.
~~~

### [MINOR] The widened scope now depends on a machine-global gitignore: .claude/settings.local.json is not covered by the repo's .gitignore

~~~
location: .gitignore:87

PROBLEM
`--exclude-standard` reads three exclusion sources, and only one of them is in the repo: .gitignore, .git/info/exclude, and the user's core.excludesFile. Measured here: `git check-ignore --no-index -v .claude/settings.local.json` attributes the match to the OPERATOR'S GLOBAL file (`.../.config/git/ignore:3:**/.claude/settings.local.json`), not to the repo's .gitignore — and .git/info/exclude contains only the shipped comment block. So the guard's candidate set is now a function of configuration that lives outside the repository and is not reviewable, not versioned, and not present on a fresh clone. Concrete failure: a second operator (or this one after a machine rebuild) clones the repo, Claude Code writes `.claude/settings.local.json` with a permission entry containing an absolute path, and because `.json` is in the `keep` set at tests/test_no_leaks.py:72 the file is enumerated and scanned. The 'windows drive path' pattern at tests/test_no_leaks.py:33 fires, and the repo's ONLY leak guard goes red on a file that can never be committed. That is the exact outcome the plan's counterweight test warns about at tests/test_leak_guard_scope.py:92 — 'or it becomes unusable and gets switched off'. The four counterweight cases that were pinned (.venv, __pycache__, node_modules, var) are all covered by the repo's own .gitignore; this one is not. Note the reciprocal hazard too: a developer whose global ignore carries a broad rule silently narrows the guard, and the suite stays green.

PROPOSED FIX
Add `.claude/settings.local.json` (and, if the harness writes others, `.claude/*.local.json`) to the repo's .gitignore under the Editors & OS block around :87, so the exclusion is versioned and reviewable rather than inherited from the operator's home directory. Optionally add a counterweight test alongside test_no_ignored_directory_leaks_into_the_candidate_set asserting the path stays out of `scannable_text_files()`, which would then be proving a repo rule rather than a machine one.
~~~

### [MINOR] commit/SKILL.md's replacement sentence re-teaches the exact stale model this fix removed

~~~
location: .claude/skills/commit/SKILL.md:77-78

PROBLEM
The new text reads: run the leak guard "**after staging rather than before** — it enumerates through git, so this is the point at which it can see everything the commit will contain". After this fix that rationale is false: `scannable_text_files()` passes `--cached --others --exclude-standard`, so the working-tree file is in scope BEFORE staging — I measured the widened set at 148 including an unstaged file versus 147 for the bare form. The fix's own amendment to requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:757 says exactly this: "Running the guard after staging is still the habit ... but it is no longer load-bearing for detection." Phase 5's stated goal is "Nothing in the repo still teaches a workaround for a defect that is now fixed" — and this is the one file Phase 5 rewrote to achieve it. An agent reading Step 2 comes away believing the pre-staging blind spot still exists.

PROPOSED FIX
Reword to keep the ordering as habit and drop the false causal clause: "Then run the leak guard — it now sees unstaged files too, so it can be run at any point; after staging is the habit because that is when the commit's contents are settled."
~~~

### [MINOR] The same rewritten paragraph now contradicts itself about gitleaks in adjacent sentences

~~~
location: .claude/skills/commit/SKILL.md:84-88

PROBLEM
The new prose says "It does **not** scan for credentials — nothing in this repo does — so also read the staged diff yourself ... `gitleaks` will catch it in CI". Both halves are in the diff's own blast radius: `git grep -n gitleaks -- .claude/` returns commit/SKILL.md:86 and update-docs/SKILL.md:25, and the same change set files instance 7 in port-residue-sweep/BUGFIX_REQUEST.md recording that the gitleaks promise is false, plus a whole feature request (secret-scanning/FEATURE_REQUEST.md:18-24) whose thesis is that this claim makes the gap look closed. Leaving the false clause was correct per plan §7 ("NOT the gitleaks line", one finding one tracker), but rewriting the sentence immediately before it produced a paragraph that asserts and denies the same fact two clauses apart — which is worse than the untouched original, because the contradiction reads as though the author checked and disagreed.

PROPOSED FIX
Do not fix the gitleaks claim here, but do not leave it hanging off the new sentence either: end the new material at "...a connection string." and leave the pre-existing gitleaks sentence as its own paragraph with an inline pointer such as `(see requests/bugfix-requests/port-residue-sweep/, instance 7)` so the reader knows it is a tracked falsehood rather than a live promise.
~~~

### [MINOR] Probe files carry a banned string into the working tree, and an interrupted run now poisons every later run

~~~
location: tests/test_leak_guard_scope.py:40-53 (`untracked_file`), used at :73, :120, :136, :153, :166, :176, :182

PROBLEM
Nine tests write real probe files into the repo, five of them containing LEAK and one being `tests/fixtures/_leak_guard_probe.dat`. Cleanup is a `finally: path.unlink()`, which survives an assertion failure but not a SIGINT, an OOM, or a killed CI step. Before this fix a survivor was invisible to the guard; AFTER it, a survivor makes `test_no_machine_paths_or_identifiers` fail repo-wide with a message that points at a file nobody wrote, and a survivor under tests/fixtures/ fails `test_game_data_is_not_tracked` too — and I confirmed tests/fixtures/ is NOT gitignored (`git check-ignore --no-index -q tests/fixtures/x.dat` exits 1), so the .dat probe is genuinely stageable. Worse, `untracked_file` opens with `assert not path.exists(), "...refusing to clobber it"` (:48), so the next run does not self-heal — it errors at setup and the operator sees a broken suite rather than a stale probe. (Verified the happy path is clean: after a full run, `git status --porcelain -uall | Select-String probe` returns nothing.)

PROPOSED FIX
Add a session-scoped autouse fixture in tests/test_leak_guard_scope.py that globs `_leak_guard_*` under REPO_ROOT, tests/fixtures/ and var/tmp/ and unlinks any survivor before collection, and downgrade the :48 assert to "unlink the stale probe and warn" so a killed run costs one warning instead of a red suite.
~~~

### [MINOR] `--exclude-standard` makes the guard's scope depend on untracked, per-machine exclude files

~~~
location: tests/test_no_leaks.py:66 (the `--cached --others --exclude-standard` comment) and tests/test_leak_guard_scope.py:81-105

PROBLEM
The comment states the argv means "tracked PLUS untracked, MINUS ignored", and the two counterweight tests pin only `.gitignore` behaviour. `--exclude-standard` in fact unions THREE sources: `.gitignore`, `$GIT_DIR/info/exclude`, and `core.excludesFile`. The latter two are per-clone/per-machine and not tracked, so a developer whose global excludes file lists `notes/`, `*.local.md` or `scratch/` silently loses exactly the untracked-file coverage this fix bought, while CI — a fresh runner with neither — sees more. That is the same class of invisible false negative the RCA calls the worse of the two failure modes. Measured here: `git config --get core.excludesFile` is unset (exit 1) and `.git/info/exclude` has no active lines, so it is latent on this machine only, and it is untestable from the tracked repo because the divergence lives in files git will never show a reviewer.

PROPOSED FIX
Name all three sources in the comment at :66, and add a cheap test that asserts `git config --get core.excludesFile` is unset and `.git/info/exclude` contains no non-comment lines — a red build there is exactly the right signal, because it tells the operator the guard is running with a scope CI does not share.
~~~

### [MINOR] Four test_no_leaks.py line anchors in first-sight's live plan were made stale by this diff, two of them inside the new amendment

~~~
location: requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:561

PROBLEM
The 8-line D3 refusal comment inserted at tests/test_no_leaks.py:18-25 and the git_paths/game_data_offenders extraction shifted every anchor in that file. Verified by reading the file: PATTERNS is now :32-36 (was :24-28); banned_names/banned_suffixes are now :151-152 (was :106-107). first-sight's plan still cites the old numbers in four places — :42 (`test_no_leaks.py:24-28`), :490 (`test_no_leaks.py:106`), :561 (both `:106-107` and `:24-28`), :759 (`test_no_leaks.py:107`). I checked what those lines now hold: :24-28 is the middle of the fence-exemption refusal comment, and :106-107 is inside the must_ignore sample list of test_patterns_still_catch_real_leaks. The sharpest instance is :561, because that is the line this fix *amended* — the amendment corrected the prose about the gap while leaving two now-wrong anchors in the same sentence. Nothing in CI catches this (the suite is green), so it will only be found by an agent following a citation to the wrong code.

PROPOSED FIX
Repoint the four anchors while the amendment is being written: `:24-28` → `:32-36` (PATTERNS) at :42 and :561; `:106` → `:151` at :490; `:106-107` → `:151-152` at :561; `:107` → `:152` at :759. Cheaper and more durable: cite the identifiers (`PATTERNS`, `banned_names`, `game_data_offenders`) rather than line numbers, which is what the amendment already does for `scannable_text_files()` and `git_paths()`.
~~~

### [MINOR] /commit's leak-guard paragraph now contradicts itself in adjacent sentences

~~~
location: .claude/skills/commit/SKILL.md:84

PROBLEM
The rewritten Step 2 block reads (`:84-88`): "It does **not** scan for credentials — nothing in this repo does — so also read the staged diff yourself ... `gitleaks` will catch it in CI". Those two clauses are flatly incompatible, three lines apart. Before this change the paragraph was internally consistent (merely wrong about gitleaks); now it is self-refuting, and an agent reading it gets no usable instruction about whether credential scanning exists. The plan was right that the gitleaks sentence belongs to port-residue-sweep and must not be *fixed* here — but leaving it adjacent to its own refutation is a new defect this diff introduced, not one it inherited.

PROPOSED FIX
Without editing the gitleaks sentence (it stays port-residue-sweep instance 7's to fix), neutralise the collision — e.g. after "nothing in this repo does" add a parenthetical naming the tracker: "(the `gitleaks` claim below is false and is tracked as `port-residue-sweep` instance 7)". That preserves Phase 5 AC1 — `git grep -n gitleaks -- .claude/` still returns both occurrences, which I confirmed it currently does — while removing the contradiction.
~~~

### [MINOR] The new is_file() skip is silent and uncounted, re-creating the drop-without-signal shape the fix removed

~~~
location: tests/test_no_leaks.py:122

PROBLEM
`if not path.is_file(): continue` drops a path with no record that it was dropped. The comment above it correctly argues against a broad `except Exception`, but the `continue` has the same silent-blindness shape it warns about, just narrower. Concretely: if the UTF-8 decode at :61 were ever loosened back toward the platform encoding, a non-ASCII path would decode to a name that does not exist on disk, `is_file()` would return False, and the file would be dropped here with zero signal — the very failure this diff exists to close, relocated from the suffix filter to the read loop. The only thing catching that today is `test_a_non_ascii_filename_survives_enumeration` (tests/test_leak_guard_scope.py:127), which asserts at the enumeration layer and only for a `.md` probe. Nothing asserts that the *scan* opened everything the enumeration handed it. Note this is a hardening gap, not a live bug — the decode is correct today and I verified the café test is non-vacuous (cp1252 is the preferred encoding here).

PROPOSED FIX
Count the skips and surface them: collect skipped paths into a list alongside `violations` and assert it is empty (or assert `len(scanned) == len(candidates)`), so a path git reported but the scan could not open fails loudly instead of vanishing. A tracked-but-deleted path is the one legitimate skip, so exclude it explicitly rather than by falling through the same branch — e.g. skip only when the path is absent AND git reports it as deleted.
~~~

### [MINOR] Probe files are now visible to the guard under test, so the suite depends on sequential single-process execution

~~~
location: tests/test_leak_guard_scope.py:73

PROBLEM
The widening created a coupling that did not exist before it. While `_leak_guard_probe.md` exists at the repo root (tests/test_leak_guard_scope.py:73), it is a real offender for `test_no_machine_paths_or_identifiers` — it contains a string matching the windows-drive-path pattern, and the guard can now see untracked files. Same for `tests/fixtures/_leak_guard_probe.dat` (:166) against `test_game_data_is_not_tracked`. Before this fix the probes were invisible to the guard, so no overlap was possible. Today this is safe: I confirmed `uv pip list | Select-String xdist` returns nothing and pyproject's addopts is `-q --strict-markers --strict-config` with no `-n`, so pytest runs one process in file order. But the safety is now an undocumented invariant — adding pytest-xdist with `-n auto` would make the suite non-deterministically red, and the failure would present as a genuine leak, which is the most expensive kind of false alarm.

PROPOSED FIX
Record the invariant where it will be read: a comment on `untracked_file` (tests/test_leak_guard_scope.py:41) stating that its probes are deliberately visible to the widened guard and that the suite therefore must not be parallelised across processes. Optionally add a `pytest.ini` note or a `-p no:xdist`-style assertion so the constraint is mechanical rather than remembered.
~~~

### [MINOR] All six phases sit as one uncommitted blob, so Phase 1's own acceptance criterion and D7's bisect boundary can no longer be satisfied

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md:126

PROBLEM
The plan structures the work as "Six phases, each ending at a `/commit`-gated checkpoint" (:81), and two of its acceptance criteria are statements about commit shape rather than about code: Phase 1 AC3 requires that `git diff --stat` list exactly one file with tests/test_leak_guard_scope.py absent from it — the check that makes "the repro passed on its own terms" falsifiable — and D7 (:332) chose to bundle the hardening "as its own commit rather than a separate request" specifically "so the bisect boundary a purist wants survives." `git log --oneline` shows the last commit is 0826da6 (unrelated) and `git status --porcelain` shows all eight files plus the new feature request uncommitted together. Phase 1 AC3 is now unverifiable — I cannot confirm the repro went green without its own test file being touched, because both changed in the same working tree. The code is right either way; the evidence that it was reached the disciplined way is gone.

PROPOSED FIX
Split at /commit time rather than landing one blob: commit tests/test_no_leaks.py's argv+helper change first (Phases 1–2), then .gitignore + the second enumeration (Phase 3), then the rename and .claude/agents/data-engineer-memory.md (Phase 4), then the three prose corrections (Phase 5), then the report and archive (Phase 6). If splitting is not worth the cost now, say so explicitly in IMPLEMENTATION_REPORT.md and record that Phase 1 AC3 was satisfied during the build but is not reconstructible from history — an honest unverifiable beats a claimed verification.
~~~

### [MINOR] The new "nothing in this repo scans for credentials" sentence sits two lines above "`gitleaks` will catch it in CI"

~~~
location: .claude/skills/commit/SKILL.md:84-88

PROBLEM
The rewritten Step 2 paragraph now reads, in four consecutive lines: "It does **not** scan for credentials — nothing in this repo does — so also read the staged diff yourself ... `gitleaks` will catch it in CI". Those two statements refute each other inside one paragraph. The plan was right to leave the `gitleaks` claim itself alone — IMPLEMENTATION_PLAN.md:361 and :366 assign it to port-residue-sweep, and Phase 5 acceptance 1 requires both occurrences survive untouched (verified: `git grep -n gitleaks -- .claude/` still returns commit/SKILL.md:86 and update-docs/SKILL.md:25) — but moving a true negative claim to sit directly against the false positive one made the paragraph worse than either version alone. A reader now has no way to tell which half to believe.

PROPOSED FIX
Add a pointer that flags the claim without editing it, preserving the grep-untouched acceptance: after "...`gitleaks` will catch it in CI" append "— **that promise is false and is tracked as instance 7 of `requests/bugfix-requests/port-residue-sweep/`; do not act on it** —". The `gitleaks` token and its sentence remain byte-identical, so Phase 5 acceptance 1 still holds.
~~~

### [MINOR] `test_game_data_is_not_tracked`'s failure message says "tracked" for a case that is now untracked by construction

~~~
location: tests/test_no_leaks.py:160-163

PROBLEM
Phase 3 deliberately widened `game_data_offenders()` to `--cached --others --exclude-standard` so it reports UNTRACKED game data — that is the entire point of D1, and `test_the_game_data_guard_sees_an_untracked_fixture` at tests/test_leak_guard_scope.py:157-170 pins it. But the test kept its old docstring "OOTP's shipped data and saves are theirs, not ours (ADR 0006)" and, more importantly, its old assertion message "OOTP game data must never be tracked:". The overwhelmingly likely trigger in practice is now an untracked scratch `.dat` under `tests/fixtures/` or `datasets/` — the two directories the widening exists to cover, confirmed un-ignored by `git check-ignore --no-index -v tests/fixtures/players.csv` -> `.gitignore:65:!tests/fixtures/**` and `datasets/x.dat` -> `.gitignore:64:!datasets/**`. The reader gets a message asserting the file is tracked when it is not, and will go looking in the index for something that is only on disk.

PROPOSED FIX
Change the assertion message at tests/test_no_leaks.py:163 to name both states, e.g. `"OOTP game data must never enter this repo — these are tracked, or untracked and committable:\n"`, and extend the docstring at :161 with one clause noting the check now covers files that are merely present. Purely a message change; no assertion logic moves.
~~~

### [MINOR] A hard-interrupted run leaves a probe that permanently reds the suite with a misleading ADR 0006 message

~~~
location: tests/test_leak_guard_scope.py:48

PROBLEM
`untracked_file` asserts `not path.exists(), f"{relative} already exists; refusing to clobber it"` and cleans up in a `finally`. A `finally` does not survive a hard kill (Ctrl-C during collection, a crashed runner, a machine reboot mid-run). Before this change a stale probe cost one erroring test. Now it costs more: a leftover `tests/fixtures/_leak_guard_probe.dat` — created at :166 — makes `test_game_data_is_not_tracked` in the OTHER module fail on every subsequent run, with the message "OOTP game data must never be tracked", which points the next agent at an ADR 0006 violation rather than at a leftover test probe. The same applies to `_leak_guard_probe.lg` and `café_leak_guard_probe.md`. No pytest-xdist is configured (`pyproject.toml:100` addopts is `-q --strict-markers --strict-config`, no `-n`), so the sequential case is safe; this is purely about crash residue.

PROPOSED FIX
Make the probe names unique per process and self-healing. In `untracked_file`, either interpolate `os.getpid()` / `uuid4().hex[:8]` into the caller-supplied name, or replace the refuse-to-clobber assert with a targeted unlink guarded by a reserved prefix: `if path.exists() and path.name.startswith("_leak_guard_") or "_leak_guard_" in path.name: path.unlink()`. Keep the assert for any path that does not carry the reserved token, so the clobber protection still covers a caller typo.
~~~

### [MINOR] The plan's six commit-gated checkpoints collapsed into one uncommitted blob, making Phase 1's restraint criterion unverifiable

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md:131

PROBLEM
Phases 1 through 5 each end "**Commit note.** `/commit`", and D7 at :332-335 justified bundling the hardening specifically so it would land "as its own commit rather than a separate request" and keep "the bisect boundary a purist wants". None of that happened: `git log --oneline -1` on branch `fix-leak-guard-untracked-blindness` is `0826da6 Settle the team_roster list_id enum by reading the game` — unrelated work — and all eight touched files plus the new feature-request directory are still dirty in one blob. Two concrete losses. (a) Phase 1 acceptance 3 — "`git diff --stat` lists exactly one file, and `tests/test_leak_guard_scope.py` is not in it" — was the plan's checkable proof that the committed red repro went green on its own terms, and it is now unverifiable after the fact; I can confirm the repro passes, but not that it passed before the repro module was edited. (b) An unrelated commit (`0826da6`) sits on this fix's branch and will ride into the same PR.

PROPOSED FIX
Stage and `/commit` in the plan's phase order rather than as one commit: first tests/test_no_leaks.py's argv change alone, then the `git_paths` / decode / `is_file` hardening plus its regression tests, then the game-data enumeration + `.gitignore`, then the rename + memory entry, then the prose. If that is no longer practical, record the collapse and the unverifiable Phase 1 criterion explicitly in the LG-03 IMPLEMENTATION_REPORT.md rather than letting the ledger imply it was checked. Separately, decide whether `0826da6` belongs on this branch or should be split out before the PR.
~~~

### [MINOR] Both assertion messages still say "tracked" although the guard now reports untracked files

~~~
location: tests/test_no_leaks.py:133 and tests/test_no_leaks.py:163 (also the module docstring at :1-3 and the function name test_game_data_is_not_tracked)

PROBLEM
The scan now fails with `machine-specific values in tracked files:` for a file that is untracked, and the game-data check fails with `OOTP game data must never be tracked:` for a `.dat` that has never been added. The mis-triage is concrete and runs the wrong way: a developer whose local-only scratch note trips the guard is told the value is already in tracked content and may go hunting history or, worse, conclude the leak is already committed; an operator who drops a real save `.dat` under `datasets/` for a one-off experiment is told OOTP data is in the repo when it is not. Plan §5 D4's byte-identical-messages rule existed so the *rename* could not launder a weakened test — it was scoped to Phase 4, not intended to freeze a message the widening made inaccurate.

PROPOSED FIX
Change :133 to `"machine-specific values in repo files (tracked or not — delete it or gitignore it):\n"` and :163 to `"OOTP game data must never be in this repo, tracked or untracked:\n"`. Note in the commit message that D4's byte-identical constraint was Phase-4-scoped and is being deliberately released here, so the next reader does not read it as the laundering D4 forbade.
~~~

### [MINOR] Everything landed as one uncommitted blob, so Phase 1's checkable claim is no longer checkable

~~~
location: git status --porcelain (8 modified files + 1 untracked dir, zero commits since 1c47c2d)

PROBLEM
The plan specified six `/commit`-gated checkpoints, with Phase 1 explicitly 'the commit that satisfies the acceptance contract' and Phase 2 'its own commit, so the bisect boundary a purist wants survives' (§5 D7). Nothing is committed, and tests/test_leak_guard_scope.py is modified in the same working tree as the argv swap — so Phase 1's deliberately-checkable restraint, 'the repro went green WITHOUT touching tests/test_leak_guard_scope.py', can no longer be verified from history by anyone. That restraint was the plan's chosen proof that the fix, not the test, moved.

PROPOSED FIX
Either stage in the planned order across separate /commit calls (argv swap alone -> hardening -> second enumeration + .gitignore -> rename + memory -> prose), or, if that is not worth the churn now, state in IMPLEMENTATION_REPORT.md that the phase boundaries were collapsed into one commit and record the Phase 1 evidence some other way (the pre-fix `git ls-files` count of 146 vs 147 is exactly that evidence and should be written down).
~~~

### [NIT] Probe files are written into non-gitignored repo directories, and a killed run leaves a .dat under tests/fixtures/

~~~
location: tests/test_leak_guard_scope.py:40-53, :166, :89, :175

PROBLEM
untracked_file() writes real files into the working tree and removes them in a finally, which is correct for a normal failure or Ctrl-C but not for a killed process. Two of the paths are in directories the repo treats as holes: tests/test_leak_guard_scope.py:166 writes tests/fixtures/_leak_guard_probe.dat, and .gitignore:65's `!tests/fixtures/**` negation means that residue would NOT be gitignored — it is exactly the committed-game-data-fixture shape the widened game_data_offenders() exists to catch. It would now be caught (the guard would go red), which is a real mitigation, but a red suite from stale residue is a confusing failure mode. Separately, :89 and :175 create var/tmp/ with mkdir(parents=True, exist_ok=True) and never remove it, and the concurrent-run case trips the 'refusing to clobber it' assert at :48 rather than skipping.

PROPOSED FIX
Give the probe names a per-process suffix (e.g. os.getpid()) so a concurrent run does not collide, and add a session-scoped autouse fixture that sweeps any leftover `_leak_guard_probe*` / `_leak_guard_nested_probe*` paths at session start. Optionally have the tests/fixtures probe assert on game_data_offenders() using a name that .gitignore does cover, if a variant exists that still proves the point.
~~~

### [NIT] Three memory entries appended where the plan asked for one, each roughly double the file's own length guidance

~~~
location: .claude/agents/data-engineer-memory.md:318-339 (three new entries) vs. IMPLEMENTATION_PLAN.md:213-215 (Phase 4 step 4, 'Append a correcting entry')

PROBLEM
Phase 4 step 4 asked for one appended correcting entry with an epistemic label. The implementation appended three (the correction itself, the C-quoting/cp1252 measurement, and the gitignore last-match-wins measurement) at 8, 7 and 8 lines respectively, against the file's own stated format rule at :31 ('Keep an entry to about four lines'). It also annotated the superseded 2026-08-16 entry in place at :84-85 rather than purely appending — though that is defensible: the file's append-never-prune rule at :41 forbids pruning, not annotation, and the same entry already carried an in-place '(Corrected 2026-08-16 at the doc gate...)' note, so the precedent is the file's own. All three new entries carry valid labels and `tests/test_agent_contract.py` is green (confirmed in the 205-passed run), and the two extra entries record genuinely reusable tooling traps, which is what the file is for. Flagged only because it is unargued growth in a file whose length policy was itself the subject of a recent request.

PROPOSED FIX
No change required. If tightening is wanted, compress each new entry toward the four-line shape at :31 — the cp1252 entry in particular repeats the reasoning already carried verbatim in the `git_paths` docstring at tests/test_no_leaks.py:40-53. Note also that the superseded entry's evidence pointer at :87 still names `tracked_text_files()`, which is correct as history but will read as a live pointer to a function that no longer exists.
~~~

### [NIT] test_the_game_data_guard_still_ignores_var passes vacuously and matches on a loose substring

~~~
location: tests/test_leak_guard_scope.py:177

PROBLEM
The assertion is `assert not [o for o in guard.game_data_offenders() if "var/" in o]`. Two weaknesses. First it is vacuity-prone: it holds whenever `game_data_offenders()` returns an empty or short list for ANY reason, so a future change that broke the enumeration entirely would leave this counterweight green — the opposite of what a counterweight is for. Its sibling at :167 has the same shape but is a positive assertion, so it cannot pass vacuously; this one can. Second, `"var/" in o` is an unanchored substring test and would also match a path like `harvard/x.dat` or `src/invar/y.dat`, so it does not actually pin 'the var/ directory'. It also over-constrains nothing: the probe at var/tmp/_leak_guard_probe.dat is ignored twice over (by `var/` at .gitignore:18 AND by `*.dat` at :34), so the test cannot distinguish which rule did the work.

PROPOSED FIX
Make the counterweight non-vacuous by pairing it with a positive control in the same test — e.g. write the var/ probe AND a tests/fixtures/ probe in one context, then assert the fixtures path IS in the offender list while the var path is NOT. Anchor the var check with `o.startswith("var/")` rather than `"var/" in o`. Consider naming the var probe with a non-banned suffix in a second case so the test isolates the `var/` rule from the `*.dat` rule.
~~~

### [NIT] Probes are written into the live worktree, and the widened guard can now be poisoned by residue from an aborted run

~~~
location: tests/test_leak_guard_scope.py:41

PROBLEM
`untracked_file()` writes real files into REPO_ROOT and relies on a `finally: path.unlink()` to clean up. That was harmless before this change, because the guard could not see untracked files. It is no longer harmless: after the widening, any probe left behind is enumerated by the very guard the next run executes. The two sharpest cases are `requests/bugfix-requests/_leak_guard_nested_probe.md` (:119-120), which contains the constructed banned string and would make `test_no_machine_paths_or_identifiers` red, and `tests/fixtures/_leak_guard_probe.dat` (:166), which would make `test_game_data_is_not_tracked` red — in a directory `.gitignore:65`'s `!tests/fixtures/**` negation deliberately un-ignores, so it is also stageable by a `git add tests/fixtures/`. `finally` covers exceptions and KeyboardInterrupt but not a hard kill, a crash inside pytest, or a `write_text` that partially succeeds. I confirmed the current tree is clean of residue via `git status --porcelain -uall` after two runs, so this is a latent hazard rather than an active bug — but the failure it produces is a red suite whose message points at the repo rather than at the abandoned run, which is expensive to diagnose.

PROPOSED FIX
Add a session-scoped autouse fixture in tests/conftest.py (or at the top of this module) that, before and after the session, sweeps REPO_ROOT for untracked files matching the single `_leak_guard_` prefix every probe already shares and unlinks them. That makes the invariant enforced rather than dependent on `finally` running, and costs one rglob.
~~~

### [NIT] Path.is_file() swallows OSError, so an unreadable file is skipped silently — the comment beside it claims the opposite

~~~
location: tests/test_no_leaks.py:122

PROBLEM
The added guard is `if not path.is_file(): continue`, and the comment above it at :119-121 says both this and the `except` are 'deliberately NARROW: a broad `except Exception` here would swallow a real read failure and restore exactly the silent blindness this guard was widened to remove.' But `pathlib.Path.is_file()` is implemented as a `stat()` wrapped in `except (OSError, ValueError): return False`, so it already swallows every OSError class — PermissionError, ELOOP on a symlink cycle, ENAMETOOLONG — and returns False. Concrete scenario: a tracked file whose ACL denies read to the current user (or, on Linux CI, a path inside a directory with the execute bit cleared) is stat-failed, `is_file()` returns False, and the file is skipped with no signal — indistinguishable from the intended tracked-but-deleted case. It is a narrow window and strictly better than the pre-fix uncaught FileNotFoundError, but the code's own comment overclaims, and the whole point of this bugfix is that a guard which drops files silently is worse than one that is loudly narrow.

PROPOSED FIX
Distinguish the two conditions rather than collapsing them: skip only when the path is genuinely absent (`if not path.exists() and not path.is_symlink(): continue`), and let a stat/read failure surface — e.g. wrap `read_text` in `except UnicodeDecodeError: continue` as now, plus `except OSError as exc: violations.append(f"{rel}: unreadable: {exc}")`. That keeps the deleted-path case handled while making an unreadable file a loud failure, which is what the adjacent comment promises. Either that, or soften the comment to say what the code actually does.
~~~

### [NIT] The keep-suffix test is case-sensitive, so an uppercase extension is silently unscanned

~~~
location: tests/test_no_leaks.py:78

PROBLEM
`p.suffix in keep` compares exactly. Traced with the project interpreter: `Path('NOTES.MD').suffix` is `'.MD'` and `'.MD' in {'.md'}` is False. A file committed as `README.MD`, `CONFIG.YML` or `notes.TXT` — trivially easy on Windows, which is the development platform here and is case-preserving — is dropped from the candidate set with no signal at all. Nothing in the tree hits it today (all 148 candidates use lowercase extensions), so this is latent, but it is the same silent-drop shape the `-z`/encoding work was undertaken to eliminate and it costs one method call to close.

PROPOSED FIX
Change to `if p.suffix.lower() in keep or p.name == ".env.example"` at tests/test_no_leaks.py:78, and mirror it in `game_data_offenders()` at :156 where `Path(rel).suffix in banned_suffixes` would likewise miss a `SAVE.DAT`.
~~~

### [NIT] A surrogate-escaped path is skipped by is_file() — the opposite of what the decode docstring promises

~~~
location: tests/test_no_leaks.py:61 and :122

PROBLEM
`git_paths` decodes with `errors="surrogateescape"` and the docstring at :52-53 justifies it as "a path we cannot decode is exactly one worth still checking". But the resulting str carries lone surrogates, and the very next consumer is `if not path.is_file(): continue` at :122 — `Path.is_file()` swallows both OSError and ValueError and returns False, so such a path is dropped with no message. The stated intent ("still checking") is therefore not achieved for the only case surrogateescape exists to serve. On Windows this cannot arise (git emits UTF-8 for the wide-API filenames), which is why the suite is green here; on the ubuntu-latest CI runner a filename with non-UTF-8 bytes would be silently skipped. Reproduced only in trace, not in a live repo, hence medium confidence on the exact mechanism — the silent-skip outcome is certain either way.

PROPOSED FIX
Before the `is_file()` skip, detect an undecodable path and report it rather than dropping it: `if any("\udc80" <= ch <= "\udcff" for ch in rel): violations.append(f"{rel}: unreadable path name — cannot be scanned"); continue`. That turns the one case surrogateescape was added for into a loud failure instead of the silent one the docstring says it is avoiding.
~~~

### [NIT] Phase 1's 'the repro went green untouched' is no longer checkable, because nothing was committed

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md:112-126

PROBLEM
The plan deliberately staged the work so Phase 1 was the argv swap alone, with acceptance criterion 3 being "`git diff --stat` lists exactly one file, and tests/test_leak_guard_scope.py is not in it" — the plan says in as many words that this restraint "is what makes 'the repro passed on its own terms' a checkable claim", and D7/Phase 3 ask for separate commits so a bisect boundary survives. All six phases sit in one uncommitted lump (`git log` shows the branch's last commit is the diagnosis commit edc7aea, which is where the red repro landed), and the repro was rewritten in the same tree by the Phase 4 rename, so `git show edc7aea:tests/test_leak_guard_scope.py` no longer runs against the current guard at all. I confirmed the SUBSTANCE independently — bare `git ls-files` returns 147 paths and omits the untracked file, the widened form returns 148 and includes it — so the fix is real; what is gone is the audit trail the plan asked for, and the bisect boundary with it.

PROPOSED FIX
Nothing to re-do in the code. When /commit runs, split the staging along the plan's phase boundaries (argv swap; `git_paths`/decode/`is_file` hardening; game-data enumeration + `.gitignore`; rename; prose) so the intended bisect boundaries exist, and state in IMPLEMENTATION_REPORT.md that Phase 1's criterion 3 was verified by measurement of the two enumerations rather than by a one-file diff.
~~~

### [NIT] The measured-holes comment names three .gitignore holes; there is a fourth

~~~
location: tests/test_no_leaks.py:143

PROBLEM
`game_data_offenders()`'s docstring names `tests/fixtures/players.csv`, `tests/fixtures/x.dat` and `datasets/x.dat` as the paths the game-data block does not cover, attributing it to the `!tests/fixtures/**` and `!datasets/**` negations at .gitignore:64-65. Correct as far as it goes, but `!gm/` and `!gm/**` at .gitignore:58-59 are also later rules, and I verified with `git check-ignore --no-index` that `gm/x.dat` is likewise NOT ignored. Since gm/ is the one directory this repo deliberately tracks (ADR 0011) and it is written to by agents, it is arguably the hole most likely to be exercised. The guard already covers it correctly — only the comment is incomplete, and the comment exists precisely so the next reader does not simplify the widening away.

PROPOSED FIX
Add `gm/` to the enumeration in the docstring at tests/test_no_leaks.py:143-149 — "`!gm/` and `!gm/**` at .gitignore:58-59 punch the same hole, so a `.dat` under gm/ is not ignored either" — and cite .gitignore:58-59 alongside :64-65.
~~~

### [NIT] `test_enumeration_yields_no_empty_entries` restates the implementation and cannot fail

~~~
location: tests/test_leak_guard_scope.py:144-147

PROBLEM
The test asserts `"" not in guard.git_paths("--cached", "--others", "--exclude-standard")`. `git_paths` at tests/test_no_leaks.py:62 returns `[rel for rel in decoded.split("\0") if rel]` — the empty string is filtered by the very expression that produces the list, so this assertion is a tautology as long as the comprehension exists in any form, including a rewritten one. Its own docstring names the behaviour it actually cares about — "a blank entry would resolve to REPO_ROOT itself and quietly turn a directory into a scan candidate" — but it does not test that. It is the one new test that buys nothing.

PROPOSED FIX
Assert the downstream property the docstring describes, which stays meaningful across refactors of the filter: `assert REPO_ROOT not in guard.scannable_text_files()`. That fails the moment a blank entry survives into the path list, regardless of how `git_paths` is written.
~~~

### [NIT] The three new memory entries each run to seven or eight lines against the file's own "about four lines" rule

~~~
location: .claude/agents/data-engineer-memory.md:318-339

PROBLEM
.claude/agents/data-engineer-memory.md:31 states the entry format rule: "Continuation lines are indented under the bullet. Keep an entry to about four lines." The three entries appended on 2026-08-17 run 8, 7 and 7 lines respectively — roughly double, adding ~22 lines to a file whose curation trigger now fires from `/update-docs` when it appears in a staged diff (per commit b32f325). `tests/test_agent_contract.py` passes (9 passed alongside the doc-link and skill-reference guards), so the epistemic labels and the mechanical opening shape are correct; this is the unenforced half of the same section.

PROPOSED FIX
Compress each to its claim plus the one measurement that makes it actionable, moving the reasoning to the cited evidence. The `.gitignore` entry, for instance, needs only: last-match-wins means `!tests/fixtures/**` and `!datasets/**` re-admit what the game-data block excluded, and `*.lg/` matched directories only — check with `git check-ignore --no-index`, not by reading top-down. Expect `/update-docs` to raise this at the commit gate anyway.
~~~

### [NIT] git_paths() can return a path three times during an unresolved merge

~~~
location: tests/test_no_leaks.py:39-62

PROBLEM
`git ls-files --cached` lists an unmerged path once per stage (1/2/3), so during a conflicted merge `git_paths("--cached", "--others", "--exclude-standard")` yields duplicates. The consequence is cosmetic rather than a miss — the same violation is reported up to three times, and `game_data_offenders()` would likewise triple an offender — but it makes the guard's output confusing in exactly the situation where someone is already under pressure. `test_enumeration_yields_no_empty_entries` pins the blank-entry edge but nothing pins uniqueness.

PROPOSED FIX
Return `list(dict.fromkeys(rel for rel in decoded.split("\0") if rel))` — order-preserving dedup, one line, and add an assertion to test_enumeration_yields_no_empty_entries that `len(paths) == len(set(paths))`.
~~~

## Gated decisions as posed

~~~
[
  {
    "question": "The plan specified six /commit-gated checkpoints and D7 justified bundling the hardening specifically so 'the bisect boundary a purist wants survives'. Everything landed as one uncommitted eight-file blob instead. Re-split into the planned commits at /commit time, or land as one commit and record the deviation?",
    "recommendation": "Land as one commit and RECORD it. The change is 8 files of tests, .gitignore and prose with no production code \u2014 the bisect value of six boundaries over ~220 inserted lines does not repay the cost of reconstructing a staged sequence after the fact, and re-splitting now would produce commits that were never independently green-tested, which is worse than an honest single commit. But the record must say so: the IMPLEMENTATION_REPORT should state that Phase 1 AC3 ('git diff --stat lists exactly one file') was not satisfiable from history, and paste in its place the measurement that closes the same question \u2014 bare `git ls-files` returns 146 paths and cannot see requests/feature-requests/secret-scanning/FEATURE_REQUEST.md, while the widened form returns 147 and does, proving the repro was genuinely red at HEAD rather than edited into passing. An unrecorded deviation from an explicitly-argued decision is the thing to avoid; a recorded one is fine. Separately decide whether the unrelated commit 0826da6 ('Settle the team_roster list_id enum') should ride into this PR or be split out.",
    "related": [
      "CF-12",
      "CF-01"
    ]
  },
  {
    "question": "Should the `keep` suffix set be widened to `.js`/`.mjs`/`.jsonl` in THIS fix, or filed as follow-up work?",
    "recommendation": "Widen it here, and correct FEATURE_REQUEST.md:58 either way. I measured all 12 currently-dropped files against the guard's own PATTERNS and got zero hits, so adding the three suffixes lands green today \u2014 a one-word change with no cleanup burden. The reason to do it now rather than file it: the eight dropped .js/.mjs files are the prompt text of the very planning and acceptance panels whose absolute-path residue triggered this request, and gm/ledger.jsonl is tracked GM memory in a public repo (ADR 0011 + 0006). Against that, a purist reading says file-TYPE scope was never in this bugfix's contract and the fix should stay narrow \u2014 a legitimate call for the operator. What is NOT optional either way is CF-06's second half: requests/feature-requests/secret-scanning/FEATURE_REQUEST.md:58 currently declares guard scope 'now fixed', which is false and closes the only route by which a follow-up would be picked up. If the widening is deferred, that line must be corrected to say the bugfix fixed WHEN the guard looks and that the file-type half remains open.",
    "related": [
      "CF-06"
    ]
  },
  {
    "question": "Plan \u00a75 D8 said the /commit change should land as 'one sentence, not a restructure' and should REPLACE the manual eyeball. The implementation kept the eyeball and added a paragraph plus a fenced command \u2014 a net +9 lines in the skill's already-longest step. Accept the deviation or revert to the planned shape?",
    "recommendation": "Accept the longer text \u2014 it is genuinely better than what was planned, because the guard does not scan for credentials and deleting the manual eyeball would have overstated what the automated check buys \u2014 but record the reinterpretation in the IMPLEMENTATION_REPORT, and fix the two defects the added text introduced. D8's underlying value was the concrete command, not the ordering claim, and the added rationale sentence at :77-78 asserts the opposite of D8's own reasoning that staging 'buys nothing for detection' (CF-08). Fixing CF-08 and CF-13 also trims the block toward D8's intended weight, addressing the length concern without losing the true content.",
    "related": [
      "CF-08",
      "CF-13",
      "CF-09"
    ]
  },
  {
    "question": "The three artifact status headers, the Index Stage cell and the `_done/` move are assigned to /commit Step 4 (.claude/skills/commit/SKILL.md:133-138), which has not run. Is P6.2 work the implementer skipped, or legitimately pending the commit gate?",
    "recommendation": "Treat the status/Index/`_done` half as legitimately pending /commit \u2014 the skill owns it and running it out of band would duplicate the gate \u2014 but treat the IMPLEMENTATION_REPORT as owed NOW and blocking. The report is the implementer's own Phase 6 step 1 deliverable, it is where the upstream contract's ledger row lives (U4, the only unmet upstream criterion), and it is where Phase 2's falsification transcript was supposed to be preserved; /commit does not produce it. One thing must not be deferred silently either way: requests/bugfix-requests/README.md:52 currently states the defect in the PRESENT tense as live, in a tracked world-readable file, and that prose needs rewriting to past tense as part of the same Index update \u2014 not just the Stage cell.",
    "related": [
      "CF-01",
      "CF-02"
    ]
  }
]
~~~

## Reviewer summaries

### acceptance

~~~
The code half of this fix is real, and I proved it by execution rather than by reading. The argv swap works: replicating the pre-fix enumeration read-only against the live repo returns 133 candidates and cannot see the untracked `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md` this very implementation wrote; `scannable_text_files()` returns 134 and does scan it. The widening adds zero junk — `git ls-files` = 146, widened = 147, and `Compare-Object` shows the single delta is that one untracked file; `.env` is out, `.env.example` is in, `.venv/`/`__pycache__/`/`node_modules/`/`var/`/`.pytest_cache/`/`.ruff_cache/` are all 0. The encoding hardening is the strongest part and I reproduced Phase 2's "seen to fail" demonstration in a throwaway scratch repo: with a `café_probe.md` present, the old `text=True`, no-`-z` form yields `[]` (git emits `"caf\303\251_probe.md"`, apparent suffix `.md"`, dropped silently) while the `-z` + explicit UTF-8 form yields `café_probe.md`; `locale.getpreferredencoding(False)` is `cp1252` here exactly as documented. `git check-ignore --no-index -v foo.lg` resolves to `.gitignore:27:*.lg`, so the `.lg` tightening bites. Full offline suite: 205 passed, 62 deselected, 0 failed (baseline was 1 failed/196 passed = 197 collected; +8 new tests = 205, arithmetic consistent). ruff, ruff format, mypy strict and all five `.mjs` guards green. The rename is complete inside `tests/` (`git grep tracked_text_files -- tests/` exits 1) and the three pre-existing assertion messages are byte-identical in the diff.

Where it falls down is the paper trail and a few scope-description residues. Phase 6 was not executed at all: there is no `IMPLEMENTATION_REPORT.md`, so the bugfix track's required acceptance ledger row ("red repro now green + regression test present") does not exist anywhere; all three artifact status headers still read `next: implement`/`next: plan`; the Index row in `requests/bugfix-requests/README.md:52` still says `planned`; the directory was not moved to `_done/`. Phase 1's acceptance criterion 3 ("`git diff --stat` lists exactly one file, and `tests/test_leak_guard_scope.py` is not in it") is now permanently unverifiable — all six phases are collapsed into one uncommitted 8-file diff with zero commits, and `tests/test_leak_guard_scope.py` is in it, so the plan's headline "the repro went green untouched" claim cannot be checked from the record. Substantively, D4 spent a whole phase renaming `tracked_text_files` because a narrow self-description invites the next agent to narrow the guard back — but the module docstring at `tests/test_no_leaks.py:1`, the assertion message at `:133` and the test name/message at `:160-163` still all say "tracked", and `:1` is the exact sentence the RCA cited as the works-as-intended counterargument. Two sets of line citations went stale in files this change edited. I found no ADR 0001 / ADR 0006 / parser-convention exposure: nothing here touches a save, a fixed offset, or game data.
~~~

### fidelity

~~~
PLAN-FIDELITY & COMPLETENESS. I ran `git status --porcelain`/`git diff HEAD`, read `tests/test_no_leaks.py` and `tests/test_leak_guard_scope.py` in full, read the IMPLEMENTATION_PLAN and ROOT_CAUSE_ANALYSIS in full, and re-ran every gate myself: `uv run pytest tests/test_leak_guard_scope.py` -> 15 passed; `uv run pytest -m "not gamedata"` -> 205 passed, 62 deselected (plan baseline was 1 failed/196 passed, so the red repro is green and 8 regression tests were added); `uv run ruff check .` -> all checks passed; `uv run ruff format --check .` -> 129 files formatted; `uv run mypy` -> no issues in 40 source files; all five `.mjs` skill guards exit 0. I independently confirmed the plan's two load-bearing measurements: `locale.getpreferredencoding(False)` is cp1252 on this machine (so pinning the UTF-8 decode really is required, not cargo cult), and `git check-ignore -v --no-index` shows `.gitignore:27:*.lg` now catches a plain `foo.lg` while `.gitignore:65:!tests/fixtures/**` still un-ignores `tests/fixtures/foo.lg` — which is exactly why `game_data_offenders()` has to cover that directory. Enumeration counts: `git ls-files` = 146, widened form = 147, the delta being the one untracked file — the widening adds zero junk, as claimed, and I verified it recurses into a wholly-untracked directory (`requests/feature-requests/secret-scanning/FEATURE_REQUEST.md` appears). Phase 4's rename is complete: `git grep -n tracked_text_files -- tests/` returns nothing, and reading the diff hunk-by-hunk confirms all four pre-existing assertion messages are byte-identical, so the rename did not launder a weakened test. Phase 5's `gitleaks` restraint holds: both occurrences survive at `commit/SKILL.md:86` and `update-docs/SKILL.md:25`, and `update-docs/SKILL.md` was not touched at all. VERDICT: Phases 1-5 are substantively and correctly implemented, and the bugfix track's acceptance contract (red repro green + regression tests left behind + nothing else regresses) is satisfied by measurement. What is NOT done is Phase 6 — three of its four steps — plus a class of stale citations the fix itself created and was explicitly authorized to correct. The plan's six `/commit`-gated checkpoints also collapsed into a single uncommitted lump, which destroys the bisect boundary D7 argued for by name.
~~~

### correctness

~~~
Correctness lens, run adversarially against the uncommitted diff with live verification. The central fix — swapping `git ls-files` for `git ls-files -z --cached --others --exclude-standard` behind a `git_paths()` seam, pinning the UTF-8 decode, and guarding the read with `is_file()` — is CORRECT, and I confirmed it rather than trusting it: the offline suite is `205 passed, 62 deselected`; ruff/format/mypy green; the widened enumeration on this tree is an exact superset (146 -> 147, sole addition the new untracked FEATURE_REQUEST.md); and I independently reproduced BOTH failure modes the plan claimed. In a throwaway scratch repo, the pre-fix form returned `'"caf\\303\\251_probe.md"\n'` for an accented filename (apparent suffix `.md"`, silently dropped by the `keep` filter) while the fixed form returned `'café_probe.md\x00'`, and `locale.getpreferredencoding(False)` is `cp1252` here exactly as the docstring says. I also verified the widening did NOT regress the game-data guard: in a scratch repo, `--exclude-standard` still lists force-added ignored `players.dat` and `roster.lg`, because exclusions apply only to `--others`. The rename is complete (`git grep tracked_text_files -- tests/` exits 1), the `.gitignore` tightening is real (`git check-ignore --no-index -v _leak_guard_probe.lg` -> `.gitignore:27:*.lg`), and the docstring's measured claim that `tests/fixtures/x.dat` is NOT ignored is true (check-ignore exits 1). No fixed-offset seeking, no unvalidated field mapping, no true-vs-scouted conflation, no key confusion, no as-of error — the diff touches no parser or warehouse code, and the plan was right that those conventions have no surface here. No BLOCKER found, and I am not inventing one. What survives is one real acceptance gap (Phase 6 was not executed, leaving a tracked public doc asserting a now-false present-tense description of the defect), one doc rationale that the fix itself falsified and that contradicts the plan's own D8, one new machine-dependent scope hole the widening opens, and three low-severity test-quality items.
~~~

### edgecases

~~~
TEST & EDGE-CASE lens, run adversarially against the uncommitted tree on branch `fix-leak-guard-untracked-blindness` (HEAD 0826da6). The change is entirely `tests/`, `.gitignore` and prose — `git status --porcelain` shows no `src/`, no dbt, no dataset, no fixture bytes — so there is ZERO regression risk to any validated field mapping, to sequential parsing, or to ADR 0001/0006 (I verified `src/` is untouched rather than assuming it).

WHAT I VERIFIED BY RUNNING IT, not by reading:
- Full offline suite: `uv run pytest -m "not gamedata" --tb=no` → **205 passed, 62 deselected**. Plan's Phase 0 baseline was `1 failed, 196 passed`; 197 + 8 new tests = 205. The red repro (`tests/test_leak_guard_scope.py:64`) is green. `ruff check` / `ruff format --check` / `mypy` all exit 0; all five node skill guards exit 0. The RCA's contract (red repro green + regression test left behind + nothing else regresses) is **met**.
- The enumeration widening buys exactly what it claims and no junk: `git ls-files` = 147 paths, `git ls-files --cached --others --exclude-standard` = 148, the single delta being the untracked `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md`. `.venv/`, `__pycache__/`, `node_modules/`, `var/` contribute 0.
- The `.gitignore` claims baked into the code comments are TRUE, re-measured with `git check-ignore --no-index -q`: `foo.lg`→ignored (the new `*.lg` line bites), `players.csv`→ignored, `x/players.dat`→ignored, but `tests/fixtures/players.csv`, `tests/fixtures/x.dat`, `datasets/x.dat`→**not** ignored. (My first pass used `-v`, whose exit code lies; the quiet form is what I trusted.)
- The two hardening claims are REAL, reproduced independently in a throwaway git repo in the scratchpad (never touching this repo): with `text=True` and no `-z`, an accented filename comes back C-quoted so its apparent suffix is `.md"` and it is **DROPPED silently**; with `-z` + explicit UTF-8 decode it survives. `getpreferredencoding()` here is indeed **cp1252**. A tracked-but-deleted path really is listed by `--cached` and `read_text` really raises `FileNotFoundError`, which the new `is_file()` skip prevents.
- The tests are not theatre: the monkeypatched deleted-path test would error (not silently pass) if the `is_file()` guard were removed; `test_the_probe_string_is_one_the_guard_actually_bans` stops the scope assertions passing emptily; the `.lg` test genuinely fails without the new `.gitignore` line. No stray probe files survive a run (`git status --porcelain -uall` after the run is clean of them).

WHERE IT IS INCOMPLETE OR SUBTLY WRONG: the regression suite proves the guard *can see* the file but never once observes it *going red* — the exact thing the plan's §4 demanded ("must be seen to fail"), and neither guard module uses `pytest.raises` at all. And the widening fixed *when* the guard looks while leaving *what* it opens untouched: measured today, 12 of the 148 candidates are dropped by the suffix filter, including all eight panel `.js`/`.mjs` files (the files whose authors are the very agents that wrote the leaked paths) and the tracked `gm/ledger.jsonl` — and a brand-new test now pins that hole as intended behaviour while the new feature request declares scope "now fixed". No live leak exists in those 12 today; I checked each against the guard's own PATTERNS and got zero hits. Finally, Phase 6 of the plan simply did not run, and the one file the fix rewrote to stop teaching a stale model (`commit/SKILL.md`) re-teaches it in the replacement sentence.
~~~

### parser

~~~
PARSER-INTEGRITY LENS: no surface. `git diff HEAD --stat -- src/` is empty — nothing in `src/ootp_ai/` changed, so there is no fixed-offset read, no version-guard, no snapshot-mutation, and no save-write path in this diff to judge. `git ls-files -- tests/fixtures` returns only `README.md`, `__init__.py`, `synthetic.py`, `tiers.py` — no OOTP data is embedded in any fixture (ADR 0006 clean). The change is entirely `tests/`, one `.gitignore` line, and prose.

WHAT I VERIFIED BY RUNNING IT (not by reading the diff):
- `uv run pytest -m "not gamedata" --tb=no` → **205 passed, 62 deselected** (baseline in the plan was `1 failed, 196 passed`; 197 + 8 new tests = 205 ✓). `uv run ruff check .` → All checks passed. `uv run ruff format --check .` → 129 files already formatted. `uv run mypy` → Success, 40 source files. All five `.mjs` skill guards exit 0.
- **The fix genuinely bites.** `git ls-files` → 146 paths; `git ls-files --cached --others --exclude-standard` → 147, and the delta is exactly `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md`, the one untracked file present. The bare form lists nothing under that path; the widened form lists the file. Git recurses into a wholly-untracked directory without `--directory`, so nested files are enumerated individually — confirmed empirically, not assumed.
- **Both halves of the encoding hardening are load-bearing, not decorative.** In a throwaway git repo in the scratchpad (never in the project, never near the game), `git ls-files --others` returned `"caf\303\251_x.md"` — C-quoted, so the apparent suffix carries a trailing quote and would fail `keep`. And `uv run python -c "locale.getpreferredencoding(False)"` → **cp1252**, `utf8_mode=0`, `PYTHONUTF8` unset — so `text=True` would have decoded UTF-8 bytes to `cafÃ©…`, and `tests/test_leak_guard_scope.py:127` is non-vacuous on both counts.
- **The `.lg` tightening works.** `git check-ignore --no-index`: `foo.lg` → IGNORED (was not, before), while `tests/fixtures/x.dat`, `tests/fixtures/players.csv`, `datasets/x.dat` → NOT ignored, exactly as `tests/test_no_leaks.py:143-149` claims. `players.csv` and `x/players.dat` at root → IGNORED. The measured-holes comment is accurate.
- **Plan acceptance spot-checks.** Phase 4 AC1: `git grep -n tracked_text_files -- tests/` exits 1, zero hits ✓. Phase 5 AC1: both `gitleaks` occurrences survive untouched at `.claude/skills/commit/SKILL.md:86` and `.claude/skills/update-docs/SKILL.md:25` ✓.
- **Every new regression test is non-vacuous**, checked by mechanism: the deleted-path test would raise `FileNotFoundError` without the `is_file()` skip at `tests/test_no_leaks.py:122`; the fixtures-`.dat` test would return an empty offender list under bare `git ls-files`; the plain-`.lg` test was red before the `.gitignore` line.

VERDICT: the RCA's contract is met — the red repro at `tests/test_leak_guard_scope.py:64` is green, eight regression tests are left behind, and nothing regressed. The engineering is genuinely careful (narrow `except`, pinned decode, seam extraction, measured comments). What is NOT done is Phase 6 in full, and Phase 5 stopped one line short of its own stated goal: `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:623` still orders a fresh agent to file the follow-up this fix already closed, and four `test_no_leaks.py:NN` anchors in that live plan — including two inside the new amendment itself — now point at unrelated lines because this diff moved them.
~~~

### skill-quality

~~~
Verified by running, not reading. The RCA's contract is MET: the red repro `test_an_untracked_file_is_visible_to_the_leak_guard` is green, regression tests are left behind, and nothing regressed — `uv run pytest -m "not gamedata"` gives `205 passed, 62 deselected` against the plan's `1 failed, 196 passed` baseline (197 + 8 new items; the scope module went 7 → 15 items, 3 in test_no_leaks). ruff check, ruff format --check (129 files), and `mypy` (40 files, strict over tests/) are all green; the five `.mjs` skill guards each exit 0; `test_doc_links.py`, `test_skill_references.py`, `test_agent_contract.py` = 9 passed. The two load-bearing `measured` claims in the new docstrings are true on this machine: `locale.getpreferredencoding(False)` returns `cp1252`, and `core.quotepath` is unset (default true, so git C-quotes). The `.gitignore` claims check out under `git check-ignore --no-index -v`: `foo.lg` now hits `.gitignore:27:*.lg`, `roster.lg/x.txt` hits `:28:*.lg/`, and `tests/fixtures/players.csv` / `datasets/x.dat` are un-ignored by the later `!` negations at `:65` / `:64` exactly as the plan measured. End-to-end proof the widening actually works on real content: the untracked `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md` is in the live candidate set (134 files scanned). No parser, dbt, save-file, or write-back surface is touched — ADR 0001/0002 and the fixed-offset ban have no contact with this diff, and the plan correctly refused to pad them in. What is NOT right: the widened enumeration has no coverage-floor assertion, so it can silently shrink and every one of the nine new tests still passes — the precise regression class the RCA itself named at :93-98; `--exclude-standard` newly ties scope to un-versioned ignore files; Phase 6 is entirely unexecuted (no IMPLEMENTATION_REPORT.md, statuses still `planned · next: implement`, index row still `planned`, no `_done/` move), which also means the plan's mandatory encoding demonstration has no recorded evidence; and `/commit`'s frontmatter now contradicts its own body about running tests.
~~~

### infra-cost

~~~
CI / secrets / repo-hygiene lens on the leak-guard widening. The core fix is real and I verified it rather than took it on trust: `git ls-files` returns 146 paths and `git ls-files --cached --others --exclude-standard` returns 147, the single delta being the new untracked `requests/feature-requests/secret-scanning/FEATURE_REQUEST.md` — i.e. the widening adds sight of exactly the new file and zero junk. Full offline suite `uv run pytest -m "not gamedata" --tb=no` -> **205 passed, 62 deselected** (plan predicted 197 at Phase 1 + 8 new tests = 205). `uv run ruff check .` / `ruff format --check .` / `mypy` all green (40 source files). The measured claims baked into the source comments all verify independently: `git check-ignore --no-index` confirms `players.csv` and `x/players.dat` IGNORED but `tests/fixtures/players.csv`, `tests/fixtures/x.dat`, `datasets/x.dat` NOT-IGNORED (last-match-wins through `!tests/fixtures/**` / `!datasets/**`), and `git check-ignore -v --no-index foo.lg` -> `.gitignore:27:*.lg`, so the new line is what closes the plain-`.lg`-file hole rather than being decorative. `locale.getpreferredencoding(False)` is genuinely `cp1252` here, and `"café_leak_guard_probe.md".encode("utf-8").decode("cp1252")` is a different string — so the non-ASCII test is a real mutant-killer for BOTH `-z` and the pinned decode, not theatre. `git grep -n tracked_text_files -- tests/` returns zero hits (Phase 4 AC1 met); `git grep -n gitleaks -- .claude/` still returns both occurrences untouched (Phase 5 AC1 met). SECRETS: no credential, token, account id, personal email or machine-specific absolute path enters a tracked file — the only literal drive paths live in `tests/test_no_leaks.py:90-94`, which is the guard's own `EXEMPT` entry and pre-existing; the new untracked FEATURE_REQUEST.md is now itself scanned by the widened guard and is clean. GAME DATA: no `.dat`/`.csv`/`.xml`/save/export enters the tree; `.gitignore` change is strictly a tightening (`var/` still ignored, `.env` still ignored, `!.env.example` still honoured). CI: `.github/workflows/ci.yml` and `ops/branch-protection.json` are untouched, no job display name moved, so no branch-protection drift; no `pyproject.toml`/`uv.lock` change so no lockfile drift; nothing new needs a local OOTP install. The RCA contract is met on its face — the red repro is green and eight regression tests are left behind. What I am unhappy about is one hole of exactly the class this bugfix exists to close: I ran a mutation probe and the newly-added `is_file()` skip is NOT covered by any assertion that the guard still detects, so an inverted condition leaves the guard scanning nothing while all 205 tests stay green. Plus one prose regression in `/commit` that re-teaches the belief the fix removed, and an unexecuted Phase 6.
~~~
