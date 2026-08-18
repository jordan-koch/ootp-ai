<!-- REDACTED: three adversary quotes contained literal drive-letter paths, quoted as
     EVIDENCE of what the guard bans. tests/test_no_leaks.py has no fenced-code
     exemption, so a tracked file cannot hold one even inside a fence -- the exact
     cost this request records. Each was rewritten to bracket the drive letter, which
     breaks the pattern's letter-immediately-before-colon requirement and nothing else.
     (This note originally tripped the guard too, by illustrating the rewrite with a
     literal example. That is the finding, demonstrated twice.) -->
<!-- Raw, unfiltered panel output. Saved by /create-implementation-plan step 3.
     Agent prose is FENCED and this checkout's repo root is stripped: the panel emitted
     absolute drive paths, which tests/test_no_leaks.py bans outright -- a finding the
     adversaries raised against the draft itself. -->

# Planning panel - raw output

Run 2026-08-17. Verdict stats: {"planners_ok": 3, "adversaries_ok": 2, "meta_audit_ok": 1, "findings": 44, "blockers": 6, "majors": 13} - degraded_lenses []

## Summary

~~~
A one-line scope defect in the repo's only leak guard, fixed in six commit-gated phases. `tests/test_no_leaks.py:33` enumerates candidates with `git ls-files`, which lists the **index**, so a file that exists on disk but has not been staged is never opened and none of the patterns at `:24-28` are ever applied to it — the guard's first possible warning arrives at `git add`, the moment content becomes committable. Phase 1 swaps the argv to `git ls-files --cached --others --exclude-standard` and turns the committed red repro (`tests/test_leak_guard_scope.py:62-75`) green without touching that file, which alone satisfies the bugfix track's acceptance contract. Phase 2 hardens the widened enumeration against the two failure modes it makes live — git C-quoting a non-ASCII path so it silently drops out of the `keep` filter, and a tracked-but-deleted path raising an uncaught `FileNotFoundError` — and leaves five regression tests pinning shapes the repro misses, including the nested-untracked-directory case that was the actual shape of all three real leaks. Phase 3 (gated, recommended) folds in the second, independently blind enumeration at `:97-116`, where `.gitignore`'s later negations at `:61-62` leave three measured holes. Phase 4 renames `tracked_text_files` and corrects the `measured` memory entry that currently teaches agents to work around the guard. Phase 5 lands the RCA's direction (d) as one sentence in `/commit`. Phase 6 closes the request and stops before the PR. **Baseline re-measured 2026-08-17 on branch `fix-leak-guard-untracked-blindness` at `edc7aea`: `uv run pytest -m "not gamedata"` → 1 failed, 196 passed, 62 deselected** — the single failure is the repro. All three planners reported 124/125; those figures were wrong and this plan supersedes them.
~~~

## Adversary findings (25)

### [BLOCKER] The plan's own file paths are banned strings — writing this plan turns the guard red

~~~
location: tests/test_no_leaks.py:25
confidence: high

PROBLEM
Every entry in `files_to_touch[].path` and `onboarding.files_to_read[].path` is written as an absolute drive path (`tests/test_no_leaks.py`, `.gitignore`, and thirteen more). I ran the guard's own compiled regex over one of them — `uv run python -c "import test_no_leaks as g; ..."` returns `['windows drive path']`. The `EXEMPT` set at `tests/test_no_leaks.py:16` holds exactly one entry and it is not `IMPLEMENTATION_PLAN.md`. So the moment those strings are written into `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md` and staged, `test_no_machine_paths_or_identifiers` goes red — and after Phase 1 lands, red the moment the file is *written*, before staging. The plan diagnoses this exact hazard in its own `files_to_touch` entry for the plan file ("never write an absolute or drive-letter path into it") and then violates it fifteen times in the same document. This is not a cosmetic slip: the very first action of the implementer — write the plan, run the gate — fails, in the file that documents the fix for that failure.

PROPOSED FIX
Before the plan is written to disk, rewrite EVERY path in `files_to_touch` and `onboarding.files_to_read` as repo-relative (`tests/test_no_leaks.py`, `.gitignore`, `.claude/agents/data-engineer-memory.md`, …). Add an explicit rail at the top of the Files-to-touch section: 'every path in this document is repo-relative on purpose; a drive letter here fails `tests/test_no_leaks.py:25`.' Then, as the plan's own first acceptance step, run `uv run pytest tests/test_no_leaks.py` (no `-q`) with the plan file present and confirm 3 passed.
~~~

### [BLOCKER] `-z` alone does not close the non-ASCII hole on this machine — subprocess text mode decodes as cp1252, not UTF-8

~~~
location: tests/test_no_leaks.py:32-38
confidence: high

PROBLEM
Phase 2's central hardening decision is 'pass `-z` and split on NUL', justified by the measured claim that default output C-quotes `café.md` as `"caf\303\251.md"` whose suffix fails the `keep` test at `tests/test_no_leaks.py:39`. That measurement is correct, but the prescribed remedy is incomplete. The existing call at `:32-38` uses `text=True` with no `encoding=`, so Python decodes git's stdout with `locale.getpreferredencoding(False)`. I measured that on this machine: **cp1252**, while `sys.getfilesystemencoding()` is **utf-8**. Git emits path bytes as UTF-8, so with `-z` and no explicit encoding, `café.md` arrives as the string `cafÃ©.md`. `REPO_ROOT / 'cafÃ©.md'` names no file; its suffix IS `.md` so it survives the `keep` filter at `:39`, and then Phase 2's own `p.is_file()` addition drops it **silently** — reproducing, exactly, the never-opened-the-bytes failure class the plan says `-z` exists to prevent. The prescribed regression test (`probe in seen`, where `probe` is `REPO_ROOT / 'café.md'`) would fail against the plan's own prescribed fix, and the most likely implementer response to a red new test is to weaken the test.

PROPOSED FIX
In Phase 2, `git_paths` must run `subprocess.run([...], cwd=REPO_ROOT, capture_output=True, text=True, encoding='utf-8', check=True)` — the explicit `encoding` is as load-bearing as `-z` and needs the same comment. Add the encoding to the phase's 'prove it red' list: temporarily drop `encoding='utf-8'` and confirm the non-ASCII test goes red for a *different* reason than dropping `-z` does. `.claude/agents/data-engineer.md:126-128` already records that this is a Windows-development repo, which is why the default is cp1252 here and would be UTF-8 in CI — i.e. this bug is green on Linux CI and red locally, the inverse of the usual asymmetry.
~~~

### [BLOCKER] Phase 4's zero-hit grep is unsatisfiable and can only be met by editing artifacts the plan forbids editing

~~~
location: plan Phase 4, acceptance criterion 1; verified against requests/bugfix-requests/ROOT_CAUSE_ANALYSIS.md:64 and :130
confidence: high

PROBLEM
Phase 4 acceptance #1 reads: "`grep -rn 'tracked_text_files' .` over the repo returns zero hits (the three call sites at tests/test_leak_guard_scope.py:71,88,99 and the memory-file mention at :85 are all updated)." I ran `git grep -n tracked_text_files`: there are 26 hits, and only 5 of them are editable under this plan's own rules. The rest live in artifacts the plan explicitly protects: `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/BUGFIX_REQUEST.md:59` and `:113` and `ROOT_CAUSE_ANALYSIS.md:64` and `:130` (the plan says "Status blockquote at `:1` only — the body is DECIDED and must not be edited"); `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:482` and `PROJECT_SCOPE.md:469` plus 12 hits under `first-sight/reviews/` (the plan says "FLAG ONLY — do not edit without the user's say-so"); and `.claude/agents/data-engineer-memory.md:85`, which is the evidence field of the very entry Phase 4 step 3 says to annotate rather than delete, per the never-prune rule at `:39-48`. On top of that, `grep -rn ... .` recurses into `.venv/` and `var/` (the latter documented at tests/test_repo_structure.py:65 as holding ~600MB), so the command is also slow and noisy. A cold agent that treats acceptance criteria as gates has exactly two moves here, and both are wrong: stall, or start rewriting decided artifacts.

PROPOSED FIX
Replace the criterion with a scoped, satisfiable one: "`git grep -n tracked_text_files -- tests/ src/` returns zero hits." Then add an explicit note listing the surviving occurrences as EXPECTED and off-limits — the two decided artifacts in this request directory, the two live first-sight artifacts plus its `reviews/` trail, and `.claude/agents/data-engineer-memory.md:85`, which is the historical evidence pointer of an entry the same phase says to annotate in place rather than rewrite. Use `git grep` rather than `grep -r`, so `.venv/` and `var/` are excluded by construction.
~~~

### [BLOCKER] No phase commits the IMPLEMENTATION_PLAN itself or advances the track to `planned`, and Phase 1's acceptance actively forbids it

~~~
location: plan Phase 1 acceptance criterion 7 vs .claude/skills/commit/SKILL.md:128 and requests/bugfix-requests/README.md:52
confidence: high

PROBLEM
`files_to_touch` lists `IMPLEMENTATION_PLAN.md` as NEW with an opening blockquote of `> **Status:** planned`, and lists `ROOT_CAUSE_ANALYSIS.md` / `BUGFIX_REQUEST.md` as "Status blockquote at `:1` only — advanced to `planned`, then `fixed`." But no phase's steps stage any of them at `planned`: Phase 6 handles only the `fixed` transition, and the Index row at `requests/bugfix-requests/README.md:52` (verified — it currently reads `diagnosed`) is likewise only touched in Phase 6. Meanwhile Phase 1's acceptance criterion 7 states "`git diff` touches exactly one file, `tests/test_no_leaks.py`", which forbids folding the plan into that commit. `.claude/skills/commit/SKILL.md:128` is explicit that "A new artifact landed (`PROJECT_SCOPE.md`, `IMPLEMENTATION_PLAN.md`, …)" requires "The artifact's own status blockquote, and the track Index row's Stage cell" in the same commit. So the plan document either never gets committed at all — leaving it permanently untracked and, after Phase 1, re-scanned by the widened guard on every single test run for the rest of the build — or it gets smuggled into a phase whose acceptance says it must not be there.

PROPOSED FIX
Insert a Phase 0 before Phase 1 with three steps and its own `/commit` checkpoint: (1) write `IMPLEMENTATION_PLAN.md` with the `planned` blockquote; (2) advance the `:1` blockquotes on `BUGFIX_REQUEST.md` and `ROOT_CAUSE_ANALYSIS.md` to `planned`, matching the grammar at `requests/bugfix-requests/README.md:45`; (3) advance the Stage cell of the Index row at `requests/bugfix-requests/README.md:52`, matched by its `[leak-guard-blind-to-untracked-files]` link, not by position. Acceptance: `uv run pytest tests/test_doc_links.py -q` green and the four status records agree. Only then does Phase 1's "exactly one file" criterion become true.
~~~

### [MAJOR] Phase 4's `grep -rn tracked_text_files` acceptance is unsatisfiable and collides with the plan's own do-not-edit rule

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md:64
confidence: high

PROBLEM
Phase 4's first acceptance criterion is "`grep -rn 'tracked_text_files' .` over the repo returns zero hits (the three call sites at `tests/test_leak_guard_scope.py:71,88,99` and the memory-file mention at `:85` are all updated)". I ran `git grep -n tracked_text_files`: there are **24 hits across 8 files**, not four. Beyond the four the plan lists, they include the two DECIDED artifacts this plan is forbidden to edit — `ROOT_CAUSE_ANALYSIS.md:64` and `:130`, `BUGFIX_REQUEST.md:59` and `:113` — plus another live track's artifacts (`requests/feature-requests/first-sight/PROJECT_SCOPE.md:469`, `IMPLEMENTATION_PLAN.md:482`) and fifteen occurrences in `first-sight/reviews/plan-proposals.md` and `plan-adversarial.md`. Driving this criterion to zero would require rewriting a decided RCA's evidence sentence, which the plan explicitly forbids elsewhere ('The body is DECIDED and must not be edited'). A cold implementer either burns the phase chasing an impossible number or, worse, edits the decided artifacts to satisfy it.

PROPOSED FIX
Scope the criterion to code: "`git grep -n tracked_text_files -- tests/ src/` returns zero hits." Add a second, separate line: "Prose references in `requests/**` and the RCA are historical records of the old name and stay as written — the rename does not chase them." Keep the `.claude/agents/data-engineer-memory.md:85` mention out of the rename too: `:78-85` is an entry Phase 4 annotates in place as historically true-then-corrected, and silently renaming the symbol inside it falsifies the record it is preserving.
~~~

### [MAJOR] Phase 4's rename step omits the in-module call site at tests/test_no_leaks.py:83

~~~
location: tests/test_no_leaks.py:83
confidence: high

PROBLEM
Phase 4 step 1 says: rename the definition at `tests/test_no_leaks.py:31`, then 'Update the three call sites at `tests/test_leak_guard_scope.py:71`, `:88` and `:99`'. There is a FOURTH call site the plan never names: line 83, `for path in tracked_text_files():` inside `test_no_machine_paths_or_identifiers`. Renaming the definition without it is an immediate `NameError` that takes the guard from 'leak report' to 'broken module' — the exact presentation Phase 2's `p.is_file()` step is meant to prevent. It is a five-second fix once seen, but a cold implementer working a step list literally will rename exactly what the list enumerates, and the plan's own acceptance criterion (F3) is scoped so loosely it does not force the discovery either.

PROPOSED FIX
Amend Phase 4 step 1 to read 'the definition at `:31` and its in-module call site at `:83`, then the three call sites in `tests/test_leak_guard_scope.py` at `:71`, `:88`, `:99`'. Add `uv run pytest tests/test_no_leaks.py` (no `-q`) → 3 passed as the phase's first acceptance line, before the scope-module run.
~~~

### [MAJOR] Every count-reading acceptance criterion uses `-q`, which suppresses the count

~~~
location: pyproject.toml:100
confidence: high

PROBLEM
`addopts = "-q --strict-markers --strict-config"` at `pyproject.toml:100` already carries `-q`. A second `-q` on the command line double-quiets pytest and removes the summary line entirely. I measured it: `uv run pytest tests/test_no_leaks.py -q` printed only `...  [100%]`, while `uv run pytest tests/test_no_leaks.py` printed `3 passed in 0.14s`. The plan then asks the implementer to READ counts out of double-quiet runs at least eight times — Phase 1 acceptance ('`uv run pytest tests/test_leak_guard_scope.py -q` → **7 passed, 0 failed**'), Phase 1 step 1 ('`uv run pytest -m "not gamedata" -q --tb=no`: expect **1 failed, 196 passed, 62 deselected**'), Phase 2 acceptance ('→ 12 passed'), and the whole per-phase selector block in the testing section. None of those numbers will appear. This is recorded as a `measured` entry in the very file Phase 4 edits — `.claude/agents/data-engineer-memory.md:124-127`: '`addopts` already carries `-q` … Run without the extra flag when the handoff needs a number to cite.'

PROPOSED FIX
Strip `-q` from every command in the plan whose acceptance depends on a count, and add a one-line note citing `.claude/agents/data-engineer-memory.md:124-127` so the next reader does not re-add it. Keep `-q` only where the acceptance is the progress string (Phase 1 step 1's `.F.....` observation), and say so explicitly there.
~~~

### [MAJOR] Phase 3's two regression tests have no seam to assert against — `test_game_data_is_not_tracked` exposes no offender list

~~~
location: tests/test_no_leaks.py:110-114
confidence: high

PROBLEM
Phase 3 prescribes '(a) an untracked `tests/fixtures/_leak_guard_probe.dat` IS reported as an offender; (b) a probe under `var/tmp/` is NOT' and says to 'Follow the pattern at `tests/test_leak_guard_scope.py:78-91`'. That pattern asserts membership in a list returned by a helper (`guard.tracked_text_files()`). No such helper exists on the game-data side: `offenders` is a local list comprehension at `tests/test_no_leaks.py:110-114`, computed inside the test function and consumed by the assertion at `:116`. There is nothing to call and nothing to assert membership in. Phase 3 routes only the `subprocess.run` at `:99-105` through `git_paths`; the `banned_names`/`banned_suffixes` filter stays inline. So the phase as written cannot produce the tests it promises, and the acceptance criterion 'the two new game-data scope tests … green' cannot be reached by the prescribed route.

PROPOSED FIX
Add an explicit extraction step to Phase 3: pull the filter out as `def game_data_offenders() -> list[str]` (using `git_paths("--cached", "--others", "--exclude-standard")`), leave `test_game_data_is_not_tracked` as a three-line assertion over it, and have the two new tests in `tests/test_leak_guard_scope.py` assert membership / non-membership in `guard.game_data_offenders()`. That mirrors the `tracked_text_files()` seam the existing counterweights already rely on. State the alternative (`pytest.raises(AssertionError)` around `guard.test_game_data_is_not_tracked()`) and reject it — it proves the assertion fires but not which path triggered it.
~~~

### [MAJOR] The tree at edc7aea is NOT clean — two acceptance criteria are unsatisfiable as written

~~~
location: requests/feature-requests/first-sight/reviews/list-id-semantics.md:1
confidence: high

PROBLEM
The plan states, three separate times, that it re-measured on 'branch `fix-leak-guard-untracked-blindness` at `edc7aea`, clean tree' and got `git ls-files` → 142 and `git ls-files --cached --others --exclude-standard` → 142, 'identical set'. The branch and SHA are right (I confirmed both), but the tree is not clean. `git status --porcelain` returns one entry: `?? requests/feature-requests/first-sight/reviews/list-id-semantics.md`, a 105-line untracked artifact belonging to ANOTHER live request. Measured now: `git ls-files` = 142, the widened form = **143**. Two acceptance criteria break on this. Phase 1's 'Recorded in the commit message: … return the SAME count on a clean tree' is false in this working tree, and an implementer who trusts it will read 142≠143 as evidence the widening pulled in junk. Phase 6's '`git status --porcelain` is empty at the end' cannot be satisfied without committing or deleting another request's file. (Mitigating: I ran all three of the guard's `PATTERNS` over that file — zero hits — so Phase 1 does still go green.)

PROPOSED FIX
Replace the count-identity criterion with the property that actually holds: 'the widened set is a strict superset of `git ls-files`, and the difference is exactly the output of `git ls-files --others --exclude-standard` — enumerate it and account for every entry.' Change Phase 6's criterion to 'git status --porcelain contains no file this branch created.' And add to Phase 1 step 3 the concrete pre-existing entry by name, with the finding that it is already clean, so the implementer meets it as expected data rather than as a surprise.
~~~

### [MAJOR] Phase 2's `-z` fix is incomplete on the dev platform: `text=True` mojibakes the path, and the new `p.is_file()` filter then drops it silently

~~~
location: plan Phase 2 step 1; against tests/test_no_leaks.py:32-38 and the new `p.is_file()` at :46-47
confidence: high

PROBLEM
Phase 2 prescribes `git_paths(*args: str) -> list[str]` running `["git", "ls-files", "-z", *args]` "with the existing call shape at `:32-38`" — which is `capture_output=True, text=True` with no `encoding`. Measured on this machine: `locale.getpreferredencoding(False)` is `cp1252`, and `subprocess.run([...], text=True)` returns `['cafÃ©.md', ...]` for a file actually named `café.md`, whereas the same call with `encoding='utf-8'` returns `['café.md', ...]`. `REPO_ROOT / 'cafÃ©.md'` does not exist. With Phase 2's own `p.is_file()` filter added at `:46-47`, that path is then dropped from the candidate set with NO error raised — which is verbatim the failure class the phase's rationale says `-z` exists to close, reintroduced by a different mechanism. Two concrete consequences for a cold agent: the phase's own non-ASCII regression test fails on Windows dev while passing on Linux CI (whose locale is UTF-8), and the phase's acceptance "temporarily revert `-z` → the non-ASCII test goes red" cannot be run meaningfully because the test is red either way locally.

PROPOSED FIX
Make the helper `subprocess.run(["git", "ls-files", "-z", *args], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", check=True)` and comment that the explicit encoding is as load-bearing as `-z` — git emits UTF-8 path bytes, and Python 3.12 on Windows defaults to the ANSI codepage. Add to Phase 2's acceptance: "the non-ASCII test is green on the Windows dev machine, not only in CI", and add a third revert-probe: "drop `encoding='utf-8'` → the non-ASCII test goes red on Windows."
~~~

### [MAJOR] Every path in `onboarding` and `files_to_touch` is a drive-letter absolute that the guard itself bans — landing them turns the suite red on the plan document

~~~
location: plan onboarding.files_to_read and files_to_touch (all 15 entries); pattern at tests/test_no_leaks.py:25
confidence: high

PROBLEM
Every `path` and `files_to_read` entry is written as `...`. The windows-drive pattern at `tests/test_no_leaks.py:25` is `(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}[A-Za-z0-9_.\-]`, and `[D]:/p` matches it — `tests/test_no_leaks.py:59` pins the near-identical string `the save lives at var` as a must-catch. So if those absolutes are transcribed into `IMPLEMENTATION_PLAN.md`, then the moment Phase 1 lands, `test_no_machine_paths_or_identifiers` goes red on the plan document itself (untracked or not — that is the whole point of the fix), producing a confusing self-inflicted failure in the same commit that is supposed to demonstrate success. The plan is aware of the hazard in one place — its own `files_to_touch` entry for the plan says "never write an absolute or drive-letter path into it" — while violating it in the surrounding fifteen entries. This is not hypothetical: `requests/feature-requests/first-sight/reviews/plan-adversarial.md:56` records the identical defect being caught in a prior stage-3 run, with the fix "Rewrite every path in `onboarding.files_to_read` (and anywhere else in the plan) as repo-relative."

PROPOSED FIX
Before writing the plan document, rewrite every path in `onboarding.files_to_read`, `files_to_touch`, `code_references` and the prose as repo-relative (`tests/test_no_leaks.py`, `.claude/skills/commit/SKILL.md`), and add it as a hard rail in Phase 0: "no drive-letter or absolute path appears in any artifact this request produces — plan, report, or `reviews/` trail." Add a Phase 1 pre-flight assertion: import `PATTERNS` from the guard and scan the freshly written plan and report before either is staged.
~~~

### [MAJOR] The clean-tree arithmetic the plan hands the implementer is already false — the tree has an untracked file right now

~~~
location: plan architecture_map ("142 → 142, identical set") and Phase 2 acceptance ("`git status --porcelain` is empty")
confidence: high

PROBLEM
The plan asserts, as its own 2026-08-17 re-measurement, "`git ls-files` → 142 paths. `git ls-files --cached --others --exclude-standard` → 142, identical set" and makes it a Phase 1 acceptance criterion ("return the SAME count on a clean tree — proving the widening added zero junk"). I re-ran it just now on branch `fix-leak-guard-untracked-blindness` at `edc7aea`: narrow = 142, widened = **143**. `git status --porcelain` reports `?? requests/feature-requests/first-sight/reviews/list-id-semantics.md` — an untracked file that predates this work. The plan's own Phase 2 acceptance "`git status --porcelain` is empty immediately after the suite" is therefore already unmeetable before any code is touched. A cold agent running Phase 1's measurement gets 142 vs 143, sees its acceptance criterion fail, and cannot tell whether it broke something. (I checked: that file contains no banned pattern, so Phase 1 will not go red on it — but the agent has no way to know that without being told to look.)

PROPOSED FIX
Replace the count-equality criterion with a set-difference criterion that survives a dirty tree: "the widened set minus the narrow set contains only untracked non-ignored paths you can enumerate and account for; the narrow set minus the widened set is EMPTY." Add a Phase 0 inventory step: run `git status --porcelain --untracked-files=all`, list every untracked path, scan each with the guard's own `PATTERNS`, and record the disposition — noting `requests/feature-requests/first-sight/reviews/list-id-semantics.md` as the known pre-existing entry. Reword Phase 2's criterion to "`git status --porcelain` shows no NEW entries relative to the Phase 0 inventory."
~~~

### [MAJOR] Phase 3 consumes the `git_paths` helper that only Phase 2 creates, while the plan treats Phase 2 as droppable

~~~
location: plan Phase 3 step 2 vs risks entry ("If Phase 2 is dropped, the omission of `--directory` is enforced by a source comment alone")
confidence: high

PROBLEM
Phase 3 step 2 reads: "Replace `subprocess.run` at `tests/test_no_leaks.py:99-105` with `git_paths(\"--cached\", \"--others\", \"--exclude-standard\")`." `git_paths` does not exist until Phase 2 step 1 creates it. Phase 3 is labelled GATED ("implement only if the user disposes it in"), and Phase 2 is separately contemplated as droppable — the risks section says outright "If Phase 2 is dropped, the omission of `--directory` is enforced by a source comment alone", and the gated decision on bundling frames Phase 2 as a judgment call. Nothing in the plan states that Phase 3 REQUIRES Phase 2. A user who disposes Phase 3 in and Phase 2 out hands the implementer a step that references an undefined name; Phase 3's own acceptance ("`grep -c 'ls-files'` shows the argv idiom appears exactly ONCE") is likewise only achievable via the Phase 2 helper.

PROPOSED FIX
State the dependency explicitly in Phase 3's goal line: "REQUIRES Phase 2 (the `git_paths` helper). If Phase 2 is dropped, Phase 3 must be dropped too, or it must inline a second `-z` shell-out — which reinstates the duplication that let the two enumerations drift apart." Better: promote Phase 2 from droppable to mandatory, since both its changes sit in the six lines Phase 1 already touches and both close the same silent-blindness class as the bug under repair.
~~~

### [MINOR] `.claude/settings.local.json` is excluded only by the user's GLOBAL git ignore, not the repo's — a real, present instance of the risk the plan states abstractly

~~~
location: .gitignore:1
confidence: high

PROBLEM
The plan's risk list correctly warns that `--exclude-standard` honours `.git/info/exclude` and the user's global `core.excludesFile`, 'neither of which is in version control'. It treats this as theoretical. It is not. I ran `git check-ignore -v --no-index -- .claude/settings.local.json` and got: `"[C]:\Users\...\.config\git\ignore":3:**/.claude/settings.local.json`. The repo's own `.gitignore` has no rule for it — the only thing keeping Claude Code's local settings file out of the widened guard's candidate set on THIS machine is a file outside the repo. That file routinely carries permission entries containing absolute paths. On a fresh clone, on a second machine, or for any other contributor, Phase 1 turns the guard red on a file nobody edited and whose contents are supposed to be machine-specific — the precise pressure `tests/test_leak_guard_scope.py:78-91` argues gets a widened guard switched off.

PROPOSED FIX
Add to Phase 1, alongside the argv change: a `.claude/settings.local.json` line in `.gitignore` (it belongs in the Secrets block near `:4-12`, since it holds machine-local permission grants), and pin it with a `re.search` test in the house style of `tests/test_repo_structure.py:64-79`. Note in the phase that this is what makes the widening reproducible off this machine, and cite the `git check-ignore -v` output as the evidence.
~~~

### [MINOR] Phase 5's `git grep -n gitleaks` acceptance is false on arrival

~~~
location: requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:41
confidence: high

PROBLEM
Phase 5's acceptance says "`git grep -n gitleaks` still returns exactly the pre-existing occurrences at `.claude/skills/commit/SKILL.md:78` and `.claude/skills/update-docs/SKILL.md:25`." I ran it: there are **11** hits, not two. Beyond the two skill occurrences the plan cares about, `gitleaks` appears at `BUGFIX_REQUEST.md:82,85,119,146`, `ROOT_CAUSE_ANALYSIS.md:80,91,144,158`, and `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:41`. The plan's own IMPLEMENTATION_PLAN and IMPLEMENTATION_REPORT will add several more, since both discuss the claim at length. As literally worded the criterion is red before the phase starts, which teaches the implementer to skim past it — the one criterion in the phase that must be read carefully, because it is the tripwire on the plan's single most-flagged accidental-scope risk.

PROPOSED FIX
Scope it: "`git grep -n gitleaks -- .claude/` returns exactly two hits, `.claude/skills/commit/SKILL.md:78` and `.claude/skills/update-docs/SKILL.md:25`, byte-identical to their pre-change text." Pair it with the diff check the plan already has ('read the Phase 5 diff and confirm the clause is byte-identical').
~~~

### [MINOR] The '27 absolute machine paths' figure is attributed to the RCA; it is not in the RCA

~~~
location: requests/bugfix-requests/README.md:52
confidence: high

PROBLEM
The plan's risk list and convergence map both state 'The RCA records that 27 absolute machine paths were written into untracked trail files on 2026-08-17.' I searched `ROOT_CAUSE_ANALYSIS.md` for '27': zero matches. The RCA says only 'three times in one session' (`:22-26`) and 'Zero were caught by the guard'. The number 27 comes from the track Index row at `requests/bugfix-requests/README.md:52` ('twice with 27 absolute machine paths a planning agent wrote into untracked trail files'). The figure is real and the point stands, but the citation sends a cold implementer to a document that does not contain it — and the plan uses that misattributed sentence to justify its highest-probability mid-build risk (the implementer's own `reviews/` trail).

PROPOSED FIX
Repoint the citation to `requests/bugfix-requests/README.md:52`, and keep the RCA cite for the separate claim it does support (three failures in one session, `ROOT_CAUSE_ANALYSIS.md:22-26`).
~~~

### [MINOR] Onboarding truncates BUGFIX_REQUEST.md's Open Questions, dropping the 'not a regression' finding

~~~
location: requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/BUGFIX_REQUEST.md:157
confidence: high

PROBLEM
The onboarding table says 'Its Open Questions at `:133-150` were all disposed by the RCA — do not re-litigate them.' The section actually runs `:133-160`. The truncation cuts off item 5 at `:157-160`: '**Not a regression.** The guard and the CI workflow arrived together in the scaffolding commit, so this has been true since day one. It went unnoticed because nothing generated sizeable artifacts into the tree until the scoping panels began writing `reviews/` files.' That is the single most useful line in the section for an implementer — it is the reason the plan's headline risk (the request's own `reviews/` trail becoming a build input) exists at all, and it is the sentence that stops someone bisecting for a regression that never happened.

PROPOSED FIX
Change the range to `:133-160` and add the item-5 finding to the 'why' cell in one clause: 'including item 5 — not a regression; it has been true since the scaffolding commit and only began biting when panels started writing `reviews/` artifacts.'
~~~

### [MINOR] No pre-flight for an orphaned probe file, so an interrupted prior run makes Phase 1 step 1 report the wrong kind of failure

~~~
location: plan Phase 1 step 1 vs tests/test_leak_guard_scope.py:46
confidence: high

PROBLEM
The risks section correctly identifies the orphan-probe landmine, but no phase's STEPS act on it. `tests/test_leak_guard_scope.py:46` is `assert not path.exists(), f"{relative} already exists; refusing to clobber it"`, inside the `untracked_file` context manager. If a prior run was interrupted (Ctrl-C, crash) and `_leak_guard_probe.md` or `var/tmp/_leak_guard_ignored_probe.md` survives, the repro does not FAIL with the predicted message at `:72` — it fails at `:46` with "refusing to clobber it", and after Phase 1 the stale probe additionally reddens `test_no_machine_paths_or_identifiers` with a violation in a file the implementer never wrote. Phase 1 step 1 instructs: "Any OTHER failure means the tree is not the one this plan was written against — stop and say so." So the plan converts a 5-second cleanup into a false halt.

PROPOSED FIX
Add as the first step of Phase 0/Phase 1: "Pre-flight — run `git status --porcelain --untracked-files=all`. If `_leak_guard_probe.md` (repo root) or `var/tmp/_leak_guard_ignored_probe.md` is present, it is an orphan from an interrupted run: delete it and re-run. Never stage either." Reference `tests/test_leak_guard_scope.py:46` so the agent recognises the "refusing to clobber it" message when it sees it.
~~~

### [MINOR] `grep -c 'ls-files'` cannot verify what Phases 2 and 3 claim, because Phase 1 is instructed to write `ls-files` into a comment

~~~
location: plan Phase 2 acceptance criterion 3 and Phase 3 acceptance criterion 3
confidence: high

PROBLEM
Phase 2 asserts "`grep -c 'ls-files' tests/test_no_leaks.py` shows the idiom is not duplicated" and Phase 3 asserts it "appears exactly ONCE". But Phase 1 step 5 explicitly instructs adding a comment above the argv that names `git ls-files` behaviour and the refuted `git status --porcelain --untracked-files=all` alternative, and Phase 2 step 2 adds a further comment explaining `-z`. `grep -c` counts lines, and comments count. So the criterion will report 3-5 on a correctly implemented file and 1 only if the implementer deletes the comments the plan asked for. It measures prose, not structure.

PROPOSED FIX
Assert on the code instead: "`git grep -n 'subprocess.run' -- tests/test_no_leaks.py` returns exactly one hit (inside `git_paths`)" — that is the property both phases actually care about, it is unaffected by comment text, and it is the structural claim (one enumeration, not two) that the whole of Phase 3 rests on.
~~~

### [MINOR] Phase 6's `_done/` move silently rots a pointer in the test module, and the plan's stated detection mechanism cannot see it

~~~
location: tests/test_leak_guard_scope.py:18 vs plan Phase 6 step 6
confidence: high

PROBLEM
`tests/test_leak_guard_scope.py:18` is `See \`requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/\`.` — a live pointer to the directory Phase 6 moves into `_done/`. Phase 6 step 6 says to "Grep for the old path BEFORE moving" but frames the consequence entirely in markdown terms: "every INBOUND link from a live document to the old path breaks and WILL go red. Re-run `uv run pytest tests/test_doc_links.py -q` after the move." That will not catch this one: `markdown_files()` at `tests/test_doc_links.py:159-171` returns only `REPO_ROOT.rglob("*.md")`, so a Python docstring is invisible to it, and the pointer is backticked inline code rather than markdown-link syntax, which `.claude/agents/data-engineer-memory.md:35-37` records as invisible to the link checker by design. Nothing goes red; the citation just quietly stops resolving — the precise drift class this repo files bugs about.

PROPOSED FIX
Name the file in Phase 6's steps: "Update `tests/test_leak_guard_scope.py:18` to the `_done/` path in the same commit as the move." And replace the grep instruction with a concrete, non-markdown-limited command: `git grep -n "leak-guard-blind-to-untracked-files"` — I ran it, and it returns `tests/test_leak_guard_scope.py:18`, `requests/bugfix-requests/README.md:52`, plus several already-archived `_done/` bodies that correctly need no change.
~~~

### [MINOR] The plan never tells a cold agent which branch to be on, and `main` is protected

~~~
location: plan conventions / Phase 1 steps; CLAUDE.md "Work on a branch; land it through a PR"
confidence: medium

PROBLEM
The branch name `fix-leak-guard-untracked-blindness` appears only inside measurement provenance notes ("measured 2026-08-17 on branch `fix-leak-guard-untracked-blindness` at `edc7aea`"), never as an instruction. The conventions list covers `/commit`, never-push-`main`, never-amend and read-only-git subagents, but not "be on a branch before you start." A cold agent resuming this work in a fresh session could plausibly be sitting on `main` — which CLAUDE.md marks protected — and would only discover it at the first `/commit`, where `.claude/skills/commit/SKILL.md:45-47` offers a branch but says "Proceed on `main` only if the user explicitly says to." Six phases of work already exist by then.

PROPOSED FIX
Add as the first line of Phase 0's steps: "Confirm `git branch --show-current` is `fix-leak-guard-untracked-blindness`; if you are on `main`, `git switch` to it (it already exists at `edc7aea`) before writing anything. `main` is protected and this plan never pushes to it."
~~~

### [NIT] Phase 2 justifies the non-ASCII escape with a ruff rule that would not fire on the character it names

~~~
location: pyproject.toml:72
confidence: medium

PROBLEM
Phase 2 step 6 says to build the non-ASCII probe name 'with an escape (`chr(0xe9)` or similar) rather than a literal glyph — ruff's RUF001/RUF003 flag ambiguous unicode in source'. `RUF` IS selected (`pyproject.toml:72`), so the rules are live — that half checks out. But RUF001/002/003 target *confusable* characters (Cyrillic homoglyphs, en-dash-for-hyphen, and similar); `é` (U+00E9) is not confusable with any ASCII character and would not be flagged. The advice is still right for a better reason the plan does not give — a literal glyph in the source makes the test's outcome depend on the source file's own encoding round-trip, which is exactly the variable under test — but a reviewer who checks the stated reason and finds it wrong will discount the instruction.

PROPOSED FIX
Keep the escape, replace the reason: 'build the name from an escape so the test's own source encoding is not a hidden variable in a test *about* path encoding — and so a PowerShell-mediated edit (`.claude/agents/data-engineer-memory.md:250-254`) cannot silently double-encode it.' Drop the RUF001/RUF003 claim or soften it to 'ruff's RUF rules are on (`pyproject.toml:72`), so avoid literal non-ASCII in source generally.'
~~~

### [NIT] `--cached` emits an unmerged path once per stage, so the widened enumerator can read and report the same file three times

~~~
location: tests/test_no_leaks.py:41
confidence: medium

PROBLEM
The loop at `tests/test_no_leaks.py:41-47` appends without deduplication. `git ls-files --cached` lists an unmerged path once per merge stage (up to three times) during a conflict, so on a conflicted tree the guard opens and scans the same file up to three times and reports each violation three times. Phase 2 is the natural place to close this — it is already extracting `git_paths` and already reasoning about what the argv emits — and the plan's own Phase 4/6 sequencing makes a rebase or merge on this branch entirely plausible. Pre-existing rather than introduced, and cosmetic in effect (a noisier report, never a missed leak), which is why this is a nit rather than a defect.

PROPOSED FIX
In Phase 2's `git_paths`, return `list(dict.fromkeys(p for p in out.stdout.split('\0') if p))` and note in the comment that `--cached` is stage-multiplied on unmerged paths. One expression, no behaviour change on a clean tree, and it keeps the violation list readable when the guard fires mid-conflict — which is precisely when someone is least inclined to read it.
~~~

### [NIT] Phase 5's gitleaks-count criterion understates the true occurrence count, inviting a false alarm

~~~
location: plan Phase 5 acceptance criterion 1
confidence: high

PROBLEM
The criterion reads "`git grep -n gitleaks` still returns exactly the pre-existing occurrences at `.claude/skills/commit/SKILL.md:78` and `.claude/skills/update-docs/SKILL.md:25`." I ran it: today it returns 12 lines. Two are in skills, and the other ten are in this request's own `BUGFIX_REQUEST.md` (`:82`, `:85`, `:119`, `:146`), its `ROOT_CAUSE_ANALYSIS.md` (`:80`, `:91`, `:144`, `:158`), and `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:41`. Phase 6's own IMPLEMENTATION_REPORT will legitimately add more. An agent reading the criterion as "exactly two" will see a mismatch and either investigate a non-problem or wrongly conclude something regressed.

PROPOSED FIX
Scope the criterion to what it actually guards: "`git grep -n gitleaks -- .claude/` returns exactly two lines, `commit/SKILL.md:78` and `update-docs/SKILL.md:25`, both byte-unchanged." That is the invariant Phase 5 must not disturb, and it is stable against the request artifacts that discuss the claim.
~~~

### [NIT] Phase 2's missing-path test monkeypatches a process-global module attribute where a narrower seam exists

~~~
location: plan Phase 2 step 8
confidence: medium

PROBLEM
Phase 2 step 8 offers "monkeypatch `guard.subprocess.run` with a typed stub returning a `CompletedProcess`-shaped object." `guard.subprocess` is the real `subprocess` module (imported at `tests/test_no_leaks.py:10`), so `monkeypatch.setattr(guard.subprocess, "run", ...)` replaces `subprocess.run` process-wide for the duration of the test, not just for the guard. `monkeypatch` restores it afterwards so this is safe today, but it is a broader blast radius than the test needs, and typing the stub to satisfy mypy strict over `tests/` (`pyproject.toml:95`) is more work than the alternative. The step does offer the narrower option second, without preferring it.

PROPOSED FIX
Prefer the narrow seam explicitly: once Phase 2 has extracted `git_paths`, monkeypatch `guard.git_paths` — a module-level function this repo owns — to return a list containing one non-existent `.md` path, then assert `tracked_text_files()` omits it and does not raise. One annotation, no global patching, and it tests the filter rather than the subprocess plumbing.
~~~

## Meta-audit findings (19)

### [BLOCKER] The plan's own absolute paths will turn the guard it fixes RED

~~~
location: merged plan: onboarding.files_to_read[0-10].path and files_to_touch[0-12].path (all use ...)
confidence: high

PROBLEM
Every one of the 11 onboarding paths and 13 files_to_touch paths in the merged draft is written in the absolute drive-letter form. I ran the guard's own patterns against that exact string: `uv run python -c "import test_no_leaks as g; ..."` returns `['windows drive path']` — the regex at tests/test_no_leaks.py:25 matches `[D]:/projects` (lookbehind satisfied, `[A-Za-z]` `:` `/` `[A-Za-z]`). Rendered into the tracked requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md, this makes test_no_machine_paths_or_identifiers report ~24 violations the moment the plan is staged — and after the plan's own Phase 1 lands, red on any local pytest run before staging. The merge wrote the prohibition into its own files_to_touch entry for the plan ('never write an absolute or drive-letter path into it — tests/test_no_leaks.py:25 bans one in tracked text') and then violated it in the same document. The sequencing planner used repo-relative paths throughout its files_to_touch; the merge converged on the wrong form.

PROPOSED FIX
Rewrite every path in onboarding.files_to_read and files_to_touch as repo-relative (`tests/test_no_leaks.py`, `.claude/skills/commit/SKILL.md`, `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md`, …) before the plan is written to disk. Then add a Phase-0-style pre-write step: run `uv run python -c "import sys; sys.path.insert(0,'tests'); import test_no_leaks as g; ..."` over the draft plan file itself and confirm zero hits. This is the plan dogfooding its own fix on its own first artifact.
~~~

### [BLOCKER] Phase 4 acceptance 'grep returns zero hits' is unsatisfiable without editing decided artifacts

~~~
location: merged plan: phases[3] (Phase 4) acceptance[0]
confidence: high

PROBLEM
The criterion reads: "`grep -rn 'tracked_text_files' .` over the repo returns zero hits (the three call sites at tests/test_leak_guard_scope.py:71,88,99 and the memory-file mention at :85 are all updated)." `git grep -n tracked_text_files` returns 25 hits. Beyond the four the merge enumerates, they include: ROOT_CAUSE_ANALYSIS.md:64 and :130 and BUGFIX_REQUEST.md:59 and :113 — DECIDED artifacts the same plan says must not be edited (files_to_touch: 'The body is DECIDED and must not be edited'); requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:482 and PROJECT_SCOPE.md:469 — another live track's artifacts the plan says to FLAG ONLY, not edit; and ~15 hits across requests/feature-requests/first-sight/reviews/. It also omits the module's own internal call site at tests/test_no_leaks.py:83. A cold implementer either stalls or resolves the contradiction by editing artifacts the plan forbids. The merge inherited this verbatim from the sequencing proposal ('grep -rn "tracked_text_files" over the repo returns zero hits') without verifying it.

PROPOSED FIX
Replace with a scoped, satisfiable criterion: "`git grep -n tracked_text_files -- tests/ .claude/` returns zero hits; historical references inside requests/ artifacts (decided or another track's) are left untouched by design." Add tests/test_no_leaks.py:83 to Phase 4 step 1's call-site list. Add one sentence to Phase 4 noting that ~20 historical mentions survive in requests/ and that this is correct, so the next reader does not 'finish' the rename into decided artifacts.
~~~

### [MAJOR] Phase 2 is an unconditional phase AND an open gated question at the same time

~~~
location: merged plan: phases[1] (Phase 2) vs gated_decisions[6] ('Should the -z / p.is_file() hardening ride along, or be filed separately?')
confidence: high

PROBLEM
Phase 2 carries a goal, 11 steps, 7 acceptance criteria and a commit note with no gating language whatsoever, while gated_decisions asks the user whether that work should ride along at all. Its content (`-z` NUL parsing, a new `git_paths` helper, `p.is_file()`, five new tests) appears nowhere in the RCA's Minimal or Root tiers — it is planner-invented hardening. This is the pattern the audit is meant to catch: a gated item written into the plan's spine so the gate reads as ceremony. Contrast Phase 3, which the merge correctly labels 'GATED — implement only if the user disposes it in' in its own goal line. The three proposals split on this: sequencing wrote it ungated, domain folded it into the fix phase, code-grounded marked its version 'gated, recommended'.

PROPOSED FIX
Pick one posture and make the phase and the gate agree. Recommended: keep the phase but label its goal 'GATED (recommended) — bundle only if the user disposes gated_decisions[6] in', matching Phase 3's treatment, and state in the goal that the bugfix contract's 'regression test left behind' half is satisfied by the nested-directory and assertion-level tests even if the `-z`/`p.is_file()` half is deferred — so the phase can be partially taken.
~~~

### [MAJOR] Phase 4's rename is unconditional in the phase but gated in the decisions

~~~
location: merged plan: phases[3] (Phase 4) steps[0] vs gated_decisions[3] ('Rename tracked_text_files()?')
confidence: high

PROBLEM
gated_decisions[3] poses the rename as a question ('some would rather leave [the repro's call sites] pristine') and recommends YES; Phase 4 step 1 states it as a flat instruction with a hard acceptance criterion built on it. Only one of three planners (sequencing) proposed the rename at all — the RCA never asks for it. The merge's own convergence_map does not list it as a converged theme, yet it became a phase spine item. Combined with M2, the gate and the phase disagree about whether it is happening and the acceptance can't be met either way.

PROPOSED FIX
Mark Phase 4's rename step as gated on gated_decisions[3] the way Phase 3's goal is gated, and split Phase 4 into 4a (memory-entry correction + doc sweep — converged by all three planners, genuinely required because the entry is a standing instruction) and 4b (the rename — gated, one-planner origin). 4a can land without 4b; 4b's acceptance then stands alone and can be scoped per M2.
~~~

### [MAJOR] Dropped: the secret-scanner follow-up is never filed, so RCA direction (c) evaporates at closure

~~~
location: merged plan: risks[15] and phases[5] (Phase 6) — vs sequencing proposal, open_questions[6]
confidence: high

PROBLEM
The RCA routes direction (c), a real credential scanner, to the FEATURE track: 'genuinely valuable and genuinely separate ... nothing in this repo scans for credentials at all.' The merge carries only the negative half — risks[15] says 'Do not add either' — and Phase 6 moves the whole request directory into `_done/`. The sequencing planner raised the affirmative: 'Worth confirming that a FEATURE_REQUEST gets filed, or the finding evaporates with this request's closure.' The merge dropped it. Since tests/test_doc_links.py:170 excludes `_done/` from the doc scan and the RCA body is the only record of (c), archiving this request with nothing filed loses a decided routing.

PROPOSED FIX
Add a step to Phase 6, before the `_done/` move: surface to the user that RCA direction (c) is routed to the feature track and unfiled, and either run /make-feature-request for it or record in IMPLEMENTATION_REPORT.md that the user declined. Add the same as a gated_decisions entry so the disposition is recorded either way. Mirror the treatment the merge already gives the `port-residue-sweep` gitleaks line.
~~~

### [MAJOR] The never-push-main / never-amend rails are cited to the wrong line range, and the correct citations were dropped

~~~
location: merged plan: conventions[4] ('per .claude/skills/commit/SKILL.md:114-151')
confidence: high

PROBLEM
conventions[4] attributes 'Never push main, never force-push, never --amend, never --no-verify' to .claude/skills/commit/SKILL.md:114-151. I read that range: it is Step 4 — Request status (the artifact/Index bookkeeping the merge itself cites at :126-130 and :142-145). The rails actually live at :212 ('Never --no-verify'), :213-214 ('Never --amend'), :231 ('Never push main'), :234 ('Never force-push') and :257-258 ('What good looks like'). The code-grounded planner cited :210-216 and :218-237 and the domain planner cited :229-237; the merge dropped both and substituted a range that does not contain the rule. A cold implementer following the citation to check the rail finds request-status bookkeeping instead.

PROPOSED FIX
Change conventions[4] to cite `.claude/skills/commit/SKILL.md:212-214` and `:231-234`, and add a code_references entry for them (the merge's code_references has none for the rails). Leave the :114-151 citation where it belongs — on Step 4's status/Index work in Phase 6.
~~~

### [MINOR] Two verified doc-sweep targets dropped from Phase 4

~~~
location: merged plan: phases[3] (Phase 4) steps[4] — vs domain proposal, Phase 4 step 6
confidence: high

PROBLEM
The domain planner named five places the guard is described and asked Phase 4 to sweep all five: CLAUDE.md:60, docs/decisions/0006-public-repo-local-data.md:30, gm/README.md:153, .env.example:4, .claude/agents/data-engineer.md:121. The merge kept three (CLAUDE.md, ADR 0006, data-engineer.md), swapped in tests/test_config.py:62, and dropped gm/README.md:153 and .env.example:4. I verified both exist and both use the narrowed word: gm/README.md:153 reads '`tests/test_no_leaks.py` covers this directory like every other'; .env.example:4 reads '...belongs in a tracked file. tests/test_no_leaks.py enforces it.' Neither is wrong after the widening, but both under-describe, which is exactly the criterion Phase 4 step 5 applies to the three it kept.

PROPOSED FIX
Restore both to Phase 4 step 5's sweep list with their verified line numbers, framed as the merge already frames CLAUDE.md:60 — 'confirm rather than assume; edit only if the new scope makes the sentence under-describe.' Cheap: two greps and at most two words.
~~~

### [MINOR] The fence-exemption refusal has a recommendation but no step and no acceptance

~~~
location: merged plan: gated_decisions[2] ('record the refusal in a comment near tests/test_no_leaks.py:16'), related: 'Phase 2 comment placement'
confidence: high

PROBLEM
The merge recommends NO on the RCA's Hardening item and explicitly says the refusal must be 'record[ed] in a comment near tests/test_no_leaks.py:16 rather than leaving it to drift.' No phase step instructs writing that comment and no acceptance criterion checks for it. Phase 2's steps enumerate comments for `-z` and `--directory` only; Phase 1's comment is about the argv flags. The sequencing planner made this a whole phase (its Phase 7) with a concrete two-line-comment outcome; the merge compressed it into a gated_decision and lost the deliverable. The RCA's own instruction was 'settling it explicitly rather than by drift' — an unrecorded refusal is drift.

PROPOSED FIX
Add a step to Phase 2 (or Phase 4): 'Write a two-line comment near tests/test_no_leaks.py:16 recording that the absence of a fenced-code exemption is deliberate, and why (a fence exemption in a LEAK guard is a smuggling channel; this is not true of the link checker at tests/test_doc_links.py:55-92).' Add the matching acceptance: the comment exists and names the sibling guard so the asymmetry is explained rather than looking like an oversight.
~~~

### [MINOR] The `grep -c 'ls-files'` acceptance conflicts with the comments the plan itself mandates

~~~
location: merged plan: phases[1] acceptance[2] and phases[2] acceptance[2]
confidence: high

PROBLEM
Phase 2 acceptance asserts "`grep -c 'ls-files' tests/test_no_leaks.py` shows the idiom is not duplicated" and Phase 3 asserts it "appears exactly ONCE — the duplication between :33 and :100 is gone." But Phase 1 step 5 requires a comment recording that `git status --porcelain --untracked-files=all` is refuted and that `--directory` must not be added, and Phase 3 step 4 requires a comment about the check-ignore measurement — comments that naturally name `git ls-files`. A literal `grep -c` will then exceed 1 and the criterion reads as failed while the code is correct. An implementer either weakens the comment or ignores the criterion; both are bad.

PROPOSED FIX
Scope the check to code rather than text: `git grep -n 'subprocess.run' -- tests/test_no_leaks.py` returns exactly one hit (inside `git_paths`), or grep for the argv literal `"ls-files",` with the trailing comma. State the intent — one shell-out, one place to get it wrong — rather than a raw string count.
~~~

### [MINOR] 'git status --porcelain is empty' acceptance is already false on the target tree

~~~
location: merged plan: phases[1] acceptance[5], phases[2] acceptance[3], phases[5] acceptance[5]
confidence: high

PROBLEM
Three phases gate on `git status --porcelain` being empty, and the architecture_map asserts the tree is clean at edc7aea. It is not: `git status --porcelain` on branch fix-leak-guard-untracked-blindness returns `?? requests/feature-requests/first-sight/reviews/list-id-semantics.md`, an untracked artifact belonging to another live request. As a result `git ls-files` = 142 but `git ls-files --cached --others --exclude-standard` = 143 right now, so Phase 1's 'same count on a clean tree' check also needs the caveat. (I scanned that file with the guard's PATTERNS: no hits, so Phase 1 will not go red on it — but the implementer will meet a non-empty porcelain and a 142/143 mismatch and have no instruction for it.)

PROPOSED FIX
Reword the criterion as 'no probe file or probe directory created by the suite survives — compare `git status --porcelain` before and after the run, not against empty.' In Phase 1, note that first-sight's untracked reviews/list-id-semantics.md is present, is another track's in-flight artifact, and is clean under PATTERNS — so it must be left alone, not scrubbed or staged. That also makes Phase 1 step 3's scrub instruction concrete instead of hypothetical.
~~~

### [MINOR] The ci.yml comment edit went in over an explicit planner dissent that was not recorded

~~~
location: merged plan: phases[4] (Phase 5) steps[5] and files_to_touch[4]
confidence: high

PROBLEM
The RCA says the checkout comment at .github/workflows/ci.yml:22-24 'stays true' and asks for no change. The code-grounded planner listed the file explicitly as 'NO CHANGE. Listed so the implementer stops and confirms rather than guessing ... Leave the file alone.' The merge sided with sequencing/domain and made it a Phase 5 edit, without noting the dissent anywhere in decisions or convergence_map. The edit is small and honest, but it is work beyond the decided tiers and it touches .github/ — a repo-level deny path — for a comment the RCA already blessed as accurate.

PROPOSED FIX
Record the dissent in decisions[10] ('Do not touch ci.yml's steps; extend only its checkout comment'): add one clause noting that one planner argued for no change at all on the ground that the existing comment is already true, and that the extension is taken only for the CI-cannot-prove-this caveat. Alternatively drop the edit and put the caveat in IMPLEMENTATION_REPORT.md, where it costs nothing and touches no deny-set file.
~~~

### [MINOR] §10 Code-grounding verification is claimed as included but the trust ledger is absent

~~~
location: merged plan: architecture_map ('§10 Code-grounding verification is included') and code_references[45]
confidence: high

PROBLEM
The plan asserts twice that §10 of the stage-3 menu is included. Per .claude/skills/create-implementation-plan/SKILL.md:224-227, §10 is 'the trust ledger: on a clean run a one-liner ("N cites checked, 0 corrected"); when refs were corrected, a short table of cited-reference → verified/corrected. It's the fingerprint that the stage's defining rigor actually ran.' The merged draft has no such ledger — only per-reference 'Read and confirmed' tags. That matters here precisely because the merge DID correct several proposals' citations (the RCA's 140/141 counts, the domain planner's 124/125 suite figures, the RCA's 'gitleaks once' correction, the 'repro not yet committed' line). Those corrections are the ledger's whole content and they are scattered across five prose fields instead.

PROPOSED FIX
Add a §10 block to the rendered plan: a count of references checked, plus a short table of the corrections actually made — RCA 140/141 → 142; RCA 'Not yet committed' → committed in edc7aea; RCA 'gitleaks promised once' → twice (commit/SKILL.md:78, update-docs/SKILL.md:25); planner baseline 124/125 → 196/197. That is the fingerprint the section exists to leave, and it also fixes M18.
~~~

### [MINOR] The monkeypatch alternative in Phase 2 would not test the filter it claims to test

~~~
location: merged plan: phases[1] (Phase 2) steps[7] ('missing-path tolerance test')
confidence: medium

PROBLEM
The step offers two ways to test the deleted-file case: monkeypatch `guard.subprocess.run` with a typed CompletedProcess stub, 'or route the check through the `git_paths` helper and test the filter directly.' The second option does not work as described: per Phase 2 step 1, `git_paths` only runs git and splits on NUL — the `p.is_file()` filter added in step 3 lives in `tracked_text_files`, not in `git_paths`. Testing `git_paths` directly exercises nothing about existence filtering. Separately, the first option is presented as cheap; `subprocess.run` is an overloaded generic returning `CompletedProcess[str]`, and a stub that satisfies mypy strict (pyproject.toml:91-95, files = ['src','tests']) is genuinely fiddly, not a one-liner.

PROPOSED FIX
Drop the second option or correct it to 'test `tracked_text_files` with `git_paths` monkeypatched to return a fabricated list containing a non-existent .md path' — monkeypatching the plan's own helper is far cheaper to type than monkeypatching subprocess.run, and it is the seam that actually sits above the filter. Note the mypy cost explicitly so the implementer budgets for it.
~~~

### [MINOR] The .gitignore *.lg tightening is nested-gated inside an already-gated phase and is not in the RCA

~~~
location: merged plan: phases[2] (Phase 3) steps[6] and gated_decisions[1]
confidence: high

PROBLEM
Phase 3 is itself gated. Inside it, step 7 says 'Optionally tighten .gitignore:25' and gated_decisions[1] poses it as a separate question answered 'YES if Phase 3 runs, NO as a standalone' — so the item is gated on a gate. The RCA never mentions .gitignore. Only the code-grounded planner raised it. I confirmed the underlying measurement (`git check-ignore -q --no-index -- foo.lg` exits non-zero; `roster.lg/x.txt` is ignored), so the finding is real — but two levels of conditionality inside a phase whose own acceptance says 'If .gitignore was touched...' will read as optional-forever to a cold implementer, and the merge itself notes 'an unenforced .gitignore line is a comment.'

PROPOSED FIX
Flatten it: either fold the `*.lg` line into Phase 3's mandatory steps WITH the pinning test in the house style of tests/test_repo_structure.py:64-79 (so the phase is one decision, not two), or lift it out of Phase 3 entirely into a one-line note in IMPLEMENTATION_REPORT.md as a filed observation for a future request. Do not leave it as an optional step inside an optional phase.
~~~

### [MINOR] tests/fixtures/README.md:26 is cited as overstating the guard but never scheduled for correction

~~~
location: merged plan: architecture_map, code_references[34], gated_decisions[0] related[2] ('tests/fixtures/README.md:26 overstates the guard')
confidence: medium

PROBLEM
The merge names this sentence four times as evidence for Phase 3 — 'tests/fixtures/README.md:26 tells readers the guard catches the obvious cases' while an un-ignored .dat under tests/fixtures/ is invisible until staged. I verified the line: 'tests/test_no_leaks.py::test_game_data_is_not_tracked catches the obvious cases by filename and extension.' But the file appears nowhere in files_to_touch and no phase step touches it. If Phase 3 lands, the sentence becomes true and needs no edit — but the plan never says so, so a reader who took the merge's 'overstates' framing seriously has an unresolved item. If Phase 3 is DROPPED, the sentence stays overstated and nothing records it.

PROPOSED FIX
Add one line to Phase 3's steps: 'If this phase lands, confirm tests/fixtures/README.md:26 now reads accurately and leave it; if this phase is dropped, add a clause there noting the guard sees only staged paths under tests/fixtures/.' That closes the loop in both dispositions and costs a grep.
~~~

### [NIT] 'All three planners reported 124/125' is false — one did

~~~
location: merged plan: architecture_map (final line) and summary (final sentence)
confidence: high

PROBLEM
The merge states twice: 'All three planners reported 124/125; those figures are wrong and this plan supersedes them.' Only the domain-convention planner reported 124 passed / 125 collected. The code-grounded planner gave no suite count. The sequencing planner explicitly instructed the implementer to 'Capture the full offline baseline ... Record the pass/fail counts' without asserting a figure. The merge's own number (1 failed, 196 passed, 62 deselected) is correct — I reproduced it exactly — so the substance is right and only the attribution is wrong. In a plan whose credibility rests on 'Read and confirmed' per reference, a checkable claim about the inputs that is checkably false is corrosive.

PROPOSED FIX
Change to 'One planner reported 124/125; that figure was not reproducible on this tree and this plan supersedes it. The other two deferred the measurement rather than asserting one.' Fold the correction into the §10 trust ledger proposed in M12.
~~~

### [NIT] tests/test_doc_link_contract.py citation is off by two lines

~~~
location: merged plan: code_references[32] and phases[4] (Phase 5) steps[5]
confidence: high

PROBLEM
Both places say 'a docstring at :75 citing .claude/skills/commit/SKILL.md:189'. I read the file: line 70 is the `def`, 71 opens the docstring, 72 is blank, and the citing line is 73 — not 75. The surrounding range the merge also gives (:72-80) is roughly right, and the cited target IS correct (SKILL.md:189 is literally '2. ```'). Minor, but the whole point of this reference is that a Phase 5 insertion rots a line number silently, and the plan opens by rotting one itself. Both the sequencing planner and the merge carry :75.

PROPOSED FIX
Correct to `tests/test_doc_link_contract.py:73` in both places, or cite the test by name (`test_a_fence_opened_inside_a_list_item_closes_again`) rather than by line, which is rot-proof and is the house convention the plan recommends elsewhere.
~~~

### [NIT] Three key measurements are each restated four to five times across the plan

~~~
location: merged plan: the --directory measurement in architecture_map, decisions[1], risks[3], phases[1] steps[4], testing; the -z measurement in architecture_map, decisions[2], risks[4], phases[1] steps[1], testing; the .gitignore-negation measurement in architecture_map, decisions[4], gated_decisions[0], phases[2] steps[0]
confidence: high

PROBLEM
Each of the three novel measurements is written out at near-full length in four or five places, with the same numbers and the same C-quoted example string. Some repetition is deliberate reinforcement for a cold implementer, but at this density it inflates the artifact, and — given M1 — every additional copy is another place a machine-specific string could be introduced when the plan is rendered. It also creates four places to update if a measurement is ever re-taken, which is precisely the argument decisions[5] used to REFUSE creating a separate measurement note ('a maintenance artifact whose numbers go stale').

PROPOSED FIX
State each measurement once at full length — in decisions, which is where the plan's own §5 says rationale lives — and reference it by decision name from architecture_map, risks, phases and testing ('per decision 2 (-z)'). Apply the same standard the merge applied when it declined the reviews/enumeration-measurement.md artifact.
~~~

### [NIT] Runtime cost of the widened enumeration was measured by a planner and dropped

~~~
location: merged plan: phases[0] acceptance — vs sequencing proposal, Phase 0 step 6 and Phase 2 acceptance
confidence: medium

PROBLEM
The sequencing planner measured the widened form at 27ms and made 'the enumeration timing is still in the same order of magnitude' a Phase 2 acceptance criterion, on the ground that this shell-out now runs on every local `pytest` invocation so cost is a real property. The merge dropped both the measurement and the criterion. Low stakes — the counts are identical on a clean tree, so the work is the same — but the whole usability argument the plan makes (risks[5]: a guard people find slow or noisy gets switched off) has a cost dimension the plan now asserts nothing about.

PROPOSED FIX
Add one line to Phase 1's re-measurement step: time both forms with `Measure-Command` and record the delta in the commit message alongside the counts. No acceptance threshold needed — just a recorded number, so a future regression has a baseline to compare against.
~~~

## Convergence map

~~~
[
  {
    "theme": "The fix is one argv list: `git ls-files` \u2192 `git ls-files --cached --others --exclude-standard`, in `tracked_text_files()` at `tests/test_no_leaks.py:33`, with everything downstream (`keep` set, `EXEMPT` filter, `rel` handling) left untouched.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three independently re-measured the RCA's table on this tree and all three got the same result: 142 == 142 on a clean tree, zero entries from the four junk roots, `.env` out and `.env.example` in. Three independent measurements of the same property, converging on the same one-line seam, is as close to certainty as a plan gets. It also means the fix is small enough to be its own revertible commit."
  },
  {
    "theme": "The committed repro must go green by the CODE changing, never by the test changing \u2014 `tests/test_leak_guard_scope.py` is not edited in the phase that fixes the bug.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Six of the repro's seven tests guard against the FIX, not the bug (`:54-59` anti-vacuity, `:78-91` gitignored stays out, `:94-102` four junk-dir cases). That inversion is unusual and is exactly why a careless widening \u2014 an `rglob`, a dropped `--exclude-standard` \u2014 would be caught. Treating the module as the untouchable acceptance contract in Phase 1 is what makes the green run mean something."
  },
  {
    "theme": "`.claude/agents/data-engineer-memory.md:78-85` is a `measured` entry that this fix FALSIFIES, and it actively teaches agents to hand-run `PATTERNS` around a guard that will then work.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three found it independently and all three rated correcting it as part of landing the fix rather than optional polish. It is the single most load-bearing stale claim in the repo because it is a standing instruction, and its own parenthetical at `:82-84` records having already been corrected once for teaching a workaround around a working check. Its presence in a staged diff also forces the full `/update-docs` sweep (`.claude/skills/commit/SKILL.md:96-99`) \u2014 a cost all three flagged."
  },
  {
    "theme": "The false `gitleaks` claim at `.claude/skills/commit/SKILL.md:78` sits one clause from the Phase-5 edit and MUST be left byte-identical; it belongs to `requests/bugfix-requests/port-residue-sweep/`.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Three planners independently named it as the most likely accidental scope breach in the whole plan \u2014 an obviously-wrong sentence inside the exact paragraph being edited, which is precisely the shape of thing that gets 'helpfully' corrected. The RCA's 'What this does not close' section routes it deliberately so one finding is not fragmented across three trackers. Convergent identification of a temptation is worth as much as convergent identification of a defect."
  },
  {
    "theme": "The implementer's own untracked scratch \u2014 and specifically this request's `reviews/` trail files \u2014 becomes a build input the moment the fix lands, and is the most likely mid-build surprise.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "The RCA records that 27 absolute machine paths were written into untracked trail files on 2026-08-17. Stage 3 writes exactly such files into this request's own `reviews/` directory (which, measured, does not exist yet). So the highest-probability first casualty of the fix is the fix's own paperwork. All three planners reached the same mitigation independently: scrub the content, put scratch in `var/`, and never reach for `EXEMPT_PREFIXES` \u2014 which is empty at `tests/test_no_leaks.py:18` and would recreate the defect under a new name."
  },
  {
    "theme": "A latent crash the widening makes live: `--cached` still lists a tracked file deleted from the working tree, and `tests/test_no_leaks.py:85-88` catches only `UnicodeDecodeError`, so `read_text` raises an uncaught `FileNotFoundError`.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Pre-existing rather than introduced \u2014 but all three planners reached the same conclusion for the same reason: Phase 1 makes 'run the suite mid-refactor on a dirty tree' the normal case, so a latent crash becomes a routine one, and a guard that produces a traceback instead of a report is a guard people learn to skip. Cheap to close (one condition), expensive to diagnose later."
  },
  {
    "theme": "CI cannot prove this fix. A fresh `actions/checkout@v7` tree has no untracked files, so `--others` contributes nothing and CI's verdict is identical before and after.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Independently derived by all three from `.github/workflows/ci.yml:20-24`. It inverts the normal handoff instinct \u2014 'the PR is green, we're done' \u2014 and it is compounded by `:3-6`, which triggers only on `pull_request` and push to `main`, so pushing the branch runs nothing at all. Stating it out loud is the difference between an honest report and a false one."
  },
  {
    "theme": "The RCA is stale in two places that a cold implementer would otherwise trust: it says the repro is 'Not yet committed' (it landed in `edc7aea`) and its counts are 140/141 (the tree is now 142).",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three caught it and all three reached the same disposition: re-measure the numbers, do not silently rewrite the decided artifact. A plan that inherited 'not yet committed' would send the implementer off to write a repro that already exists. Worth one corrective sentence in the IMPLEMENTATION_REPORT rather than an edit to the RCA's body."
  }
]
~~~

## Gated decisions as posed

~~~
[
  {
    "question": "Fold `test_game_data_is_not_tracked` into the widened enumeration (Phase 3)? The RCA lists it under Root and again under 'What this does not close, unless the plan folds it in.' Two planners disagreed about whether it buys anything.",
    "recommendation": "**YES**, on measurement rather than symmetry \u2014 but land it as its own commit after Phase 1, and comment the measurement so the next reader does not undo it. `git check-ignore -q --no-index` settles the planners' disagreement with nuance: in the general case widening is a no-op (`players.csv`, `x/players.dat`, `names.xml`, `a.dat`, `roster.lg/x.txt` are all IGNORED), but three real holes exist \u2014 `tests/fixtures/players.csv`, `tests/fixtures/x.dat` and `datasets/x.dat` are NOT ignored, because `!datasets/**` at `.gitignore:61` and `!tests/fixtures/**` at `:62` are later rules and git is last-match-wins; and `foo.lg` as a plain FILE is NOT ignored, because `*.lg/` at `:25` matches directories only. `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:240` and `:680` independently verified the same negation behaviour and record that `tests/test_no_leaks.py:107` is the ONLY thing stopping a committed `.dat` fixture, while `tests/fixtures/README.md:26` tells readers the guard 'catches the obvious cases'. The counter-argument is scope discipline: Phase 1 alone satisfies the bugfix contract. If you decline, say so in the report \u2014 do not leave it looking overlooked.",
    "related": [
      "Phase 3",
      ".gitignore:25 tightening",
      "tests/fixtures/README.md:26 overstates the guard"
    ]
  },
  {
    "question": "Tighten `.gitignore:25` from `*.lg/` to also cover a plain `*.lg` file?",
    "recommendation": "**YES if Phase 3 runs, NO as a standalone.** Measured: `foo.lg` as a plain file is not ignored today while `roster.lg/x.txt` is. It is strictly a tightening \u2014 a directory named `foo.lg` is already covered \u2014 so there is no coverage regression risk. But without Phase 3 nothing enforces it, and an unenforced `.gitignore` line is a comment. If added, pin it with a test in the house style of `tests/test_repo_structure.py:64-79`, and expect the full `/update-docs` sweep because CLAUDE.md describes these rules."
  },
  {
    "question": "Should `tests/test_no_leaks.py` gain a fenced-code exemption, as its sibling `tests/test_doc_links.py` did on 2026-08-17 (`strip_fences()` is the ready-made implementation)? The RCA raises it as Hardening and explicitly declines to settle it.",
    "recommendation": "**NO \u2014 and record the refusal in a comment near `tests/test_no_leaks.py:16` rather than leaving it to drift.** All three planners reached this independently. The RCA states the counter-argument itself: a fence exemption in a LEAK guard is a channel for smuggling a credential past it, which is not true of a link checker. The cost is real and visible \u2014 this plan, the RCA and the intake all had to describe strings rather than quote them \u2014 but 'describe, do not quote' is a cheap standing rule and an exemption is not reversible once artifacts start relying on it. The narrower alternative (adding the bugfix directory to `EXEMPT_PREFIXES` at `:18`, currently empty) has the same smuggling shape in a smaller box; decline that too. If you disagree, the exemption must reuse `strip_fences()` rather than growing a second fence parser, scope to `requests/**` only, and ship with a negative test proving a banned string OUTSIDE a fence in an in-scope file is still caught.",
    "related": [
      "Phase 2 comment placement",
      "tests/test_doc_links.py strip_fences",
      "EXEMPT_PREFIXES at tests/test_no_leaks.py:18"
    ]
  },
  {
    "question": "Rename `tracked_text_files()`? It touches the committed repro's three call sites at `tests/test_leak_guard_scope.py:71`, `:88`, `:99`, which some would rather leave pristine.",
    "recommendation": "**YES, in Phase 4, in its own commit, with every assertion message byte-identical.** Only one planner raised it, but the argument is the RCA's own: its third reason for `confirmed-bug` is that the guard's narrow self-description was treated as the authority on its scope. Leaving a function called `tracked_*` that scans untracked files re-arms exactly that argument for the next agent, who will read the name, conclude the widening was a mistake, and narrow it back. Deferring it past Phase 1 keeps 'the repro went green untouched' a true and checkable claim."
  },
  {
    "question": "May this plan edit another request's LIVE artifact? `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:678` (risk 15) tells agents to 'Run the guard *after* staging' and `:544` files this very bug \u2014 both obsolete once this lands, and first-sight is live, not in `_done/`.",
    "recommendation": "**FLAG, do not edit.** Surface it in the IMPLEMENTATION_REPORT and let the user decide. Editing another track's decided artifact is normally out of bounds, and first-sight's plan is an execution document its own implementer is working from \u2014 a silent edit mid-flight is worse than a stale line. But leaving a live document teaching a workaround for a fixed defect is exactly the drift class this repo files bugs about, so it must not simply go unmentioned."
  },
  {
    "question": "Record the SECOND false `gitleaks` promise into `requests/bugfix-requests/port-residue-sweep/`?",
    "recommendation": "**YES, one line, in Phase 6's commit.** Verified by `git grep -n gitleaks`: the claim appears at `.claude/skills/commit/SKILL.md:78` AND at `.claude/skills/update-docs/SKILL.md:25`, which lists `gitleaks` among the mechanical checks that 'moved to CI, where it runs on every PR and cannot be skipped'. The RCA's 'Two corrections to the intake report' at `:91` says the claim occurs once \u2014 that correction is itself wrong. Recording the second occurrence in the sweep's body keeps one finding in one tracker and costs a line; making the sweep rediscover it costs a session. Do NOT fix either occurrence here."
  },
  {
    "question": "Should the `-z` / NUL-parsing hardening and the `p.is_file()` guard ride along in this fix, or be filed separately? A purist reading of the bugfix track says a fix does one thing.",
    "recommendation": "**BUNDLE, as Phase 2 \u2014 a separate commit inside the same branch, not a separate request.** Both are measured, both live in the six lines the fix already touches, and both are the same silent-blindness class as the bug under repair: a widened guard that then silently drops files with accented names has traded one blind spot for a subtler one. Splitting means a second request whose entire content is 'the fix we just shipped drops files with accented names'. Keeping it as its own commit preserves the bisect boundary that a purist actually wants."
  },
  {
    "question": "Does the `/commit` note (Phase 5) go far enough, or should Step 2's scan step actually MOVE to Step 1 (Survey)?",
    "recommendation": "**The sentence, not the restructure.** `.claude/skills/commit/SKILL.md` is already 258 lines and Step 2 is its longest; the skill's own argument at `:107-108` is that a gate people route around is worse than a light one. A concrete `uv run pytest tests/test_no_leaks.py -q` replacing the manual eyeball at `:77-78` captures direction (d)'s whole value. Note the reinterpretation the plan makes here \u2014 (d)'s literal words were 'stage before you verify', which after (a) buys nothing for detection and nudges toward the `git add -A` habit `:51-52` exists to forbid. Confirm you are happy with that reading."
  }
]
~~~
