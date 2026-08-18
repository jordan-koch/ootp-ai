<!-- Raw planner proposals. Fenced + repo root stripped, as above. -->

# Planning panel - raw planner proposals

## Proposal 1

~~~
{
  "planner": "code-grounded",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Read the Verdict, the Evidence block (points at tests/test_no_leaks.py:31-48), the measured table under 'The idiom that does work', and the tiered Fix posture. Its recommendation — direction (a) now, (d) as an ordering note, (b) refused, (c) to the feature track — is DECIDED; do not re-open it."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/BUGFIX_REQUEST.md",
      "why": "Context only. Its 'Affected Area & Pointers' (:109-123) names the three files to open in order and records that ci.yml's git ls-files dependency is deliberate."
    },
    {
      "path": "tests/test_no_leaks.py",
      "why": "The file being fixed. 116 lines, two independent enumerations: tracked_text_files() at :31-48 and test_game_data_is_not_tracked() at :97-116. Both shell out to plain `git ls-files` (:33 and :100)."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "why": "The committed red reproduction (landed in edc7aea, 103 lines, 7 tests). test_an_untracked_file_is_visible_to_the_leak_guard at :62-75 is the RED one; :78-102 are the six counterweights that a naive widening breaks. This is the acceptance contract."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "Confirms the guard is blocking (:54-57, `pytest -m \"not gamedata\"`) and carries the comment at :20-24 saying the `git ls-files` dependency is deliberate. Read before deciding whether that comment needs editing — it does not."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "why": "Step 2 'Stage deliberately' (:49-79) is where the pre-history-catch expectation lives (:77-79) and where the one-line ordering note (direction (d)) goes. Step 4 (:114-148) owns advancing the request status and the Index row; Step 6 rails at :210-216."
    },
    {
      "path": ".gitignore",
      "why": "The exclusion set the fix inherits wholesale. Load-bearing lines: var/ at :18, *.lg/ at :25, *.dat at :31, and the negations !datasets/** at :61 and !tests/fixtures/** at :62 which UN-ignore game-data suffixes under those two trees."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "why": "The entry at :78-85 is a `measured` claim that this fix falsifies. It currently tells agents the guard is blind to new files and to hand-run PATTERNS instead. Correcting it is part of landing the fix, not optional polish."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The pipeline contract this plan is stage 3 of. Status grammar at :45 (intake -> diagnosed -> planned -> fixed); the Index row for this slug is :52; the 'done means red goes green + a regression test is left behind' contract is at :24-26."
    }
  ],
  "architecture_notes": "THE TOUCHED AREA IS ONE FILE PLUS ITS COMMITTED REPRO. There is no src/ code in this change, no parser, no dbt model, no dataset — it is repo-governance tooling.\n\nCURRENT STRUCTURE\n\n`tests/test_no_leaks.py` (116 lines) has three moving parts and TWO independent enumerations:\n\n1. Policy constants. `EXEMPT = {\"tests/test_no_leaks.py\"}` at :16 (exactly one entry — this is why neither the BUGFIX_REQUEST nor the RCA can quote a banned string). `EXEMPT_PREFIXES: tuple[str, ...] = ()` at :18 — currently empty, so `rel.startswith(EXEMPT_PREFIXES)` at :43 is always False. `PATTERNS` at :24-28: three compiled regexes (windows drive path, unix home path, email address).\n\n2. Enumeration A — `tracked_text_files()` at :31-48. Shells out to `[\"git\", \"ls-files\"]` at :32-38 with `cwd=REPO_ROOT, check=True`, splits stdout, drops EXEMPT/EXEMPT_PREFIXES at :43, then keeps only paths whose suffix is in the `keep` set at :39 (`.md .py .toml .yml .yaml .json .sql .example .txt`) or whose name is `.env.example` (:46). Consumed by `test_no_machine_paths_or_identifiers()` at :81-94, which opens each file (:85-88, catching only `UnicodeDecodeError`) and applies PATTERNS line by line.\n\n3. Enumeration B — `test_game_data_is_not_tracked()` at :97-116. A SECOND, separate `subprocess.run([\"git\", \"ls-files\"], ...)` at :99-105, its own filter over `banned_names` / `banned_suffixes` at :106-107. It shares the blindness and shares nothing else.\n\n`test_patterns_still_catch_real_leaks()` at :51-78 is a pure-pattern test that touches neither enumeration; it is unaffected by this change and is the reason a loosening of PATTERNS would be caught.\n\nTHE EXACT SEAM\n\nThe defect is one argument list, twice. `git ls-files` enumerates the INDEX. The seam is `tests/test_no_leaks.py:33` (and, for the Root tier, `:100`): swap the argv to `[\"git\", \"ls-files\", \"--cached\", \"--others\", \"--exclude-standard\"]`. Nothing else in the function needs to move — `--others` emits repo-relative, forward-slash paths in exactly the same shape as `--cached`, so the `rel` handling at :41-47 is untouched, and `--exclude-standard` applies `.gitignore`, `.git/info/exclude` and the global excludes file so the whole existing exclusion set is inherited rather than reimplemented.\n\nRE-MEASURED IN THIS REPO TODAY (2026-08-17, commit edc7aea, clean tree):\n- `git ls-files` -> 142 paths. `git ls-files --cached --others --exclude-standard` -> 142 paths, and `Compare-Object` reports the two sets IDENTICAL. The RCA measured 140/140 two commits earlier; the property holds.\n- `.venv/`, `__pycache__/`, `node_modules/`, `var/` -> 0 entries each in the widened form.\n- `.env` absent (gitignored at .gitignore:4); `.env.example` present (the `!.env.example` negation at .gitignore:6 is honoured). This pair is why the widening does not put the guard at war with the one file whose job is machine-specific values.\n- `git check-ignore` on `reviews/trail.md` and `requests/feature-requests/first-sight/reviews/x.md`: NOT ignored — i.e. exactly the artifact class that leaked three times on 2026-08-17 becomes visible.\n\nWHY THIS IS A NO-OP IN CI, AND WHY THAT IS THE POINT. `actions/checkout@v7` at ci.yml:20-24 produces a tree with no untracked files, so `--others` contributes nothing there and CI's verdict is bit-identical before and after. The entire value of the change is local: the guard's first possible warning moves from `git add` to \"any `uv run pytest`\". The comment at ci.yml:22-24 (\"needs the repo, not a detached blob export\") stays literally true of the new argv — DO NOT edit it.\n\nA SIBLING PRECEDENT, AND WHY NOT TO COPY IT. `tests/test_doc_links.py::markdown_files()` at :159-171 solves the same visibility problem with `REPO_ROOT.rglob(\"*.md\")` plus a hand-written exclusion list (`.git`, `var`, `_done`). That list does not exclude `.venv/`, `__pycache__/` or `node_modules/`. Reimplementing `.gitignore` by hand is precisely the failure mode the six counterweight tests at test_leak_guard_scope.py:78-102 exist to prevent. Use git's own exclusion machinery; do not follow the sibling.\n\nA SECOND, MEASURED BLIND SPOT (Root tier, gated). Enumeration B's blindness is not theoretical here, because two `.gitignore` negations punch holes in the game-data rules. Measured with `git check-ignore -q --no-index`: `tests/fixtures/players.csv`, `tests/fixtures/x.dat` and `datasets/x.dat` are all VISIBLE — the `!datasets/**` (:61) and `!tests/fixtures/**` (:62) negations override `players.csv` (:27) and `*.dat` (:31). Separately, `foo.lg` as a plain FILE is VISIBLE, because `*.lg/` at :25 matches directories only. So an OOTP `.dat` dropped into `tests/fixtures/` sits un-ignored in the tree and Enumeration B cannot see it until someone stages it — while `tests/fixtures/README.md:26` tells readers that guard \"catches the obvious cases\". Folding Enumeration B in closes that; leaving it open is a defensible scope call but must be a stated one.",
  "phases": [
    {
      "name": "Phase 1 — Widen the text guard's enumeration (turn the red repro green)",
      "goal": "`tests/test_leak_guard_scope.py` goes 7/7 green with no change to that file, and no other test regresses. This phase alone satisfies the bugfix track's acceptance contract.",
      "steps": [
        "Read `tests/test_no_leaks.py:31-48` and `tests/test_leak_guard_scope.py` in full before editing. Run `uv run pytest tests/test_leak_guard_scope.py -q` first and SEE the red: 1 failed, 6 passed, failing at `tests/test_leak_guard_scope.py:72` with 'the leak guard cannot see an untracked file'. A fix applied to a repro you never watched fail is a fix you cannot claim.",
        "In `tracked_text_files()`, change the argv at `tests/test_no_leaks.py:33` from `[\"git\", \"ls-files\"]` to `[\"git\", \"ls-files\", \"--cached\", \"--others\", \"--exclude-standard\"]`. Change NOTHING else in the function: `cwd=REPO_ROOT`, `check=True`, the EXEMPT filter at :43 and the `keep` suffix filter at :39/:46 all stay exactly as they are.",
        "Add a comment directly above the argv recording WHY all three flags are present and that dropping any one is a silent regression: `--cached` keeps the 142 tracked paths, `--others` adds untracked ones, `--exclude-standard` is what keeps `.venv/`, `__pycache__/`, `node_modules/` and `var/` out. Cite the refuted alternative by name so nobody re-proposes it: `git status --porcelain --untracked-files=all` returns 0 paths on a clean tree (RCA, 'Two corrections to the intake report').",
        "Rewrite the module docstring at `tests/test_no_leaks.py:1-5`. The current first line, 'Nothing machine-specific may be tracked', is the sentence the RCA had to argue past to reach `confirmed-bug`; leaving it in place re-arms that argument for the next reader. State the scope the guard now actually has: the working tree minus everything git ignores — tracked, staged, and not-yet-staged alike — because a leak is cheap to fix before `git add` and a history rewrite after.",
        "Do NOT touch `.github/workflows/ci.yml`. Re-read :20-24 and confirm for yourself that the comment stays true of the new argv, then leave it alone. Do NOT touch the `gitleaks` sentence at `.claude/skills/commit/SKILL.md:78` — the RCA explicitly reserves it for `requests/bugfix-requests/port-residue-sweep/` ('What this does not close').",
        "Run the guard against itself on a dirty tree: create a scratch file OUTSIDE the repo or under `var/`, confirm the suite stays green, then confirm the repro's own probe path is what flips it."
      ],
      "acceptance": [
        "`uv run pytest tests/test_leak_guard_scope.py -q` -> 7 passed, 0 failed. In particular `test_an_untracked_file_is_visible_to_the_leak_guard` passes AND all four parametrizations of `test_no_ignored_directory_leaks_into_the_candidate_set` (`.venv`, `__pycache__`, `node_modules`, `var`) still pass, as does `test_a_gitignored_file_stays_out_of_scope`.",
        "`uv run pytest -m \"not gamedata\"` is fully green — no other test regressed.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all clean (mypy is strict over `tests` per pyproject.toml:91-95).",
        "A one-off manual check, recorded in the commit message: `git ls-files --cached --others --exclude-standard | Measure-Object -Line` returns the same count as `git ls-files` on a clean tree (142 at edc7aea), proving the widening added zero junk.",
        "`git diff` touches exactly one file, `tests/test_no_leaks.py`, and within it only the argv at :33, an added comment, and the module docstring."
      ],
      "commit_note": "Widen the leak guard from the index to the working tree. `/commit` — one file, no doc-map change, so Step 3's two-minute version (`uv run pytest tests/test_doc_links.py -q`) suffices rather than the full `/update-docs` sweep. Message should name the measured identity (142 == 142 on a clean tree) and state that CI's verdict is unchanged because a fresh checkout has no untracked files."
    },
    {
      "name": "Phase 2 — Make the guard survive a dirty tree (gated, recommended)",
      "goal": "Now that the guard is meaningful mid-edit, it must not ERROR mid-edit. A tracked file deleted from the working tree but not yet staged is still listed by `--cached`, and `Path.read_text` on it raises `FileNotFoundError` — which the handler at `tests/test_no_leaks.py:85-88` does not catch, so the guard blows up with a traceback instead of reporting.",
      "steps": [
        "Confirm the gap by reading `tests/test_no_leaks.py:85-88`: the only handled exception is `UnicodeDecodeError`. This is pre-existing, not introduced by Phase 1 — but Phase 1 is what makes 'run the suite mid-refactor' the normal case, so it stops being latent.",
        "In `tracked_text_files()`, filter to files that actually exist before appending at :47: add `p.is_file()` to the condition. Prefer this over broadening the `except` clause — a leak guard that swallows `OSError` can skip a file it should have read and report green, which is the exact failure class this whole request is about.",
        "As belt-and-braces only, widen the handler at :85-88 to `except (UnicodeDecodeError, FileNotFoundError)`. Do not add a bare `except OSError` or `except Exception`.",
        "Add a regression test to `tests/test_leak_guard_scope.py` — monkeypatch, do NOT mutate the tree. Use pytest's `monkeypatch` to replace `guard.subprocess.run` with a stub returning a `CompletedProcess`-shaped object whose `stdout` names a `.md` path that does not exist, then assert `guard.tracked_text_files()` omits it and does not raise. Annotate it `-> None` and type the stub; mypy is strict over `tests/`.",
        "Name the test for the failure, e.g. `test_a_tracked_file_deleted_from_the_worktree_does_not_crash_the_guard`, and put the reason in its docstring: the guard's value is that it runs on a half-finished tree, so a half-finished tree must not turn it into a traceback."
      ],
      "acceptance": [
        "`uv run pytest tests/test_leak_guard_scope.py -q` -> 8 passed (7 existing + the new one).",
        "The new test fails if `p.is_file()` is reverted — verify by temporarily removing the filter, watching it go red, and restoring.",
        "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run mypy` all green.",
        "No file was created or deleted inside the repo by the new test — it is monkeypatch-only. `git status --porcelain` is clean after the run."
      ],
      "commit_note": "Keep the leak guard reporting rather than crashing on a half-finished tree. `/commit` — tests only, two-minute doc check."
    },
    {
      "name": "Phase 3 — Fold in the second enumeration (Root tier, GATED — implement only if the user disposed it in)",
      "goal": "`test_game_data_is_not_tracked()` at `tests/test_no_leaks.py:97-116` stops sharing the blindness. The RCA flags it under 'Root' and again under 'What this does not close'; the measurements below say the exposure is real, not hypothetical.",
      "steps": [
        "First re-measure the justification yourself so you are not taking it on faith. `git check-ignore -q --no-index -- tests/fixtures/players.csv` and `-- tests/fixtures/x.dat` and `-- datasets/x.dat` each exit NON-ZERO (not ignored) — the negations `!datasets/**` at `.gitignore:61` and `!tests/fixtures/**` at `.gitignore:62` override `players.csv` (:27) and `*.dat` (:31). Separately `git check-ignore -q --no-index -- foo.lg` exits non-zero, because `*.lg/` at `.gitignore:25` matches directories only, never a plain file.",
        "Extract the duplicated shell-out into one module-level helper, e.g. `def repo_files() -> list[str]:` returning the stripped, non-empty relative paths from `git ls-files --cached --others --exclude-standard`. Have `tracked_text_files()` consume it, and replace the second `subprocess.run` at `tests/test_no_leaks.py:99-105` with a call to it. One enumeration, one place to get it wrong.",
        "Update `test_game_data_is_not_tracked`'s docstring at :98 and its assertion message at :116. 'must never be tracked' is now too narrow: an un-ignored `.dat` sitting in the tree is one `git add -A` away from permanent public history, which is the hazard `.claude/skills/commit/SKILL.md:51-52` is built around. Say 'tracked, or sitting un-ignored in the tree'.",
        "Add two regression tests to `tests/test_leak_guard_scope.py` using the existing `untracked_file` context manager at :38-51 (it write/yield/unlinks in a `finally`, so the tree is always restored): (a) an untracked `tests/fixtures/_leak_guard_probe.dat` IS reported by the game-data check; (b) a probe under `var/tmp/` is NOT. The second is the counterweight — without it, a future widening to a raw `rglob` would pass.",
        "Consider, and state a verdict either way in the commit message, adding a bare `*.lg` line beside `*.lg/` at `.gitignore:25`. It is strictly a tightening (a directory named `foo.lg` is already covered), and `tests/test_repo_structure.py:64-79` shows the house style for pinning a `.gitignore` invariant with a test if you want one."
      ],
      "acceptance": [
        "`uv run pytest tests/test_leak_guard_scope.py -q` green with the two new game-data scope tests included.",
        "`grep -c 'git\", \"ls-files' tests/test_no_leaks.py` finds the argv exactly ONCE — the duplication is gone.",
        "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all green.",
        "`git status --porcelain` is clean after the suite — no `.dat` probe left in `tests/fixtures/`.",
        "No OOTP game data was created that is real: the probe is a zero-information placeholder file that merely carries the banned SUFFIX, never bytes copied from a save (ADR 0006). `tests/fixtures/synthetic.py:6` is the precedent."
      ],
      "commit_note": "One enumeration for both leak guards; the game-data check now sees un-ignored files too. `/commit` — if `.gitignore` changed, this touches a rule CLAUDE.md describes, so run the full `/update-docs` sweep per `.claude/skills/commit/SKILL.md:86-100`."
    },
    {
      "name": "Phase 4 — The `/commit` ordering note (direction (d))",
      "goal": "Close the gap for an operator who does not run the suite before staging. The RCA calls this 'nearly free — /commit already runs the guard, and running it after staging is a sentence in the skill'.",
      "steps": [
        "Read `.claude/skills/commit/SKILL.md:49-79` (Step 2 — Stage deliberately) end to end before editing, and `:206-208`, which already names `tests/test_no_leaks.py` as the reason not to write absolute paths into tracked files.",
        "Add ONE sentence to the sanity-check block at `:71-79`: the leak guard is now scoped to the working tree, so `uv run pytest tests/test_no_leaks.py -q` catches a machine path BEFORE staging, not only after — run it while the content is still an edit rather than a history rewrite.",
        "Leave the `gitleaks` claim at `:78` exactly as it is. It is false, it is known to be false, and the RCA assigns it to `requests/bugfix-requests/port-residue-sweep/` specifically so the same finding is not fragmented across three trackers. Fixing it here is out of scope and will be flagged as such.",
        "Keep the addition to a sentence. This skill is 258 lines and its Step 2 is already the longest; a paragraph here is how a gate becomes something people route around (`:107-108` makes exactly that argument about the doc check).",
        "Any repo path you write into the skill must exist — `tests/test_skill_references.py::test_every_repo_path_a_skill_names_exists` at :86-94 enforces it, and `tests/test_doc_links.py` checks relative link targets."
      ],
      "acceptance": [
        "`uv run pytest tests/test_skill_references.py tests/test_doc_links.py -q` green.",
        "`uv run pytest -m \"not gamedata\"` green.",
        "`git diff .claude/skills/commit/SKILL.md` shows an addition of roughly one sentence inside `:71-79` and no deletion — in particular the `gitleaks` sentence at :78 is byte-identical.",
        "The added sentence names a command that actually works: `uv run pytest tests/test_no_leaks.py -q` runs clean from the repo root."
      ],
      "commit_note": "Tell /commit to run the leak guard before staging, now that it can see unstaged files. `/commit` — a skill edit; `tests/test_skill_references.py` and `tests/test_doc_links.py` are the relevant guards."
    },
    {
      "name": "Phase 5 — Retire the stale memory entry and close the request",
      "goal": "No tracked document still tells an agent the guard is blind. Then the request reaches `fixed` and the directory is archived.",
      "steps": [
        "Correct `.claude/agents/data-engineer-memory.md:78-85`. That entry is labelled `measured` and says `tests/test_no_leaks.py` iterates `git ls-files` so a file you just created is invisible until commit, and instructs agents to import `PATTERNS` and hand-scan instead. After Phase 1 it is FALSE, and it is the single most load-bearing stale claim in the repo because it actively teaches the workaround. Follow the file's own house style — the entry at :82-84 shows how a prior correction was recorded inline with a date and a reason, rather than by deletion. Note that its contrast with `tests/test_doc_links.py` also collapses: both guards now see untracked files, by different means.",
        "Re-read `.claude/agents/data-engineer.md:121` ('No machine-specific paths in tracked files. tests/test_no_leaks.py enforces it.'). Decide whether 'tracked' should become 'in the repo tree'. CLAUDE.md warns that the data-engineer rulebook is the SINGLE OWNER of the build rules and that restating one elsewhere recreates the duplication single ownership exists to prevent — so change it in place, do not add a copy anywhere.",
        "Check `CLAUDE.md:60` ('Everything resolves from `.env`; `tests/test_no_leaks.py` fails the build') and `tests/test_config.py:62` ('scans every tracked file for exactly these shapes'). The first stays true as written. The second is a docstring whose 'tracked' is now narrower than reality — a one-word edit, or leave it and say why.",
        "Run `/update-docs` for real rather than eyeballing: this change alters a rule the docs describe, which is exactly the trigger at `.claude/skills/commit/SKILL.md:86-100`. Note that bullet at :96-99 fires on its own terms — `.claude/agents/data-engineer-memory.md` appearing in the staged diff mandates the sweep.",
        "Advance the request. Per `requests/bugfix-requests/README.md:45` the grammar is `intake -> diagnosed -> planned -> fixed`. Set the status blockquote on `BUGFIX_REQUEST.md:1`, `ROOT_CAUSE_ANALYSIS.md:1` and `IMPLEMENTATION_PLAN.md` to `fixed`, set the Index row at `requests/bugfix-requests/README.md:52` to `fixed`, and move the directory into `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/` with the Index link repointed — the terminal-stage row of the table at `.claude/skills/commit/SKILL.md:126-129`. `/commit` owns this step; let it drive.",
        "Do NOT open the PR and do NOT merge. `.claude/skills/commit/SKILL.md:218-237` and CLAUDE.md's conventions both reserve that for the operator; `/commit` pushes the branch and hands back the URL."
      ],
      "acceptance": [
        "`grep -n 'invisible to it' .claude/agents/data-engineer-memory.md` returns nothing, or returns only a line explicitly marked as corrected/superseded with today's date.",
        "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all green — the final gate before handoff.",
        "`uv run pytest tests/test_doc_links.py tests/test_skill_references.py tests/test_repo_structure.py -q` green after the directory move (the move breaks any relative link into the old path, and `tests/test_doc_links.py::markdown_files()` at :159-171 skips `_done/` bodies but NOT links pointing INTO them).",
        "The Index row at `requests/bugfix-requests/README.md` reads `fixed` and its link resolves to `_done/leak-guard-blind-to-untracked-files/`.",
        "Every artifact's status blockquote and its Index row agree — the 'What good looks like' bullet at `.claude/skills/commit/SKILL.md:252-254`."
      ],
      "commit_note": "Close the leak-guard blindness request: correct the stale memory entry, advance to fixed, archive. `/commit` with the FULL `/update-docs` sweep — `data-engineer-memory.md` in the diff mandates it, and this commit moves a request directory."
    }
  ],
  "testing": "THE ACCEPTANCE CONTRACT IS THE BUGFIX TRACK'S, NOT A FEATURE'S: the red repro goes green, a regression test is left behind, and nothing else regresses (`requests/bugfix-requests/README.md:24-26`). All three are already expressible as commands here, because the repro landed in commit edc7aea.\n\nTHE RED REPRO. `uv run pytest tests/test_leak_guard_scope.py -q`. Before the fix (verified by me at edc7aea, clean tree): 1 failed, 6 passed, failing at `tests/test_leak_guard_scope.py:72` — `AssertionError: the leak guard cannot see an untracked file, so it fires only once the content is staged`. After Phase 1: 7 passed. The implementer MUST observe the red state before editing.\n\nTHE REGRESSION GUARD IS ALREADY WRITTEN, AND SIX-SEVENTHS OF IT GUARDS AGAINST THE FIX, NOT THE BUG. This is the unusual and important property of this repro and the reason a naive `rglob` widening must not be substituted:\n- `test_the_probe_string_is_one_the_guard_actually_bans` (:54-59) — anti-vacuity. If `PATTERNS` ever stops matching the constructed probe, every scope assertion below would pass while testing nothing. This test is why you cannot \"fix\" the suite by weakening PATTERNS.\n- `test_an_untracked_file_is_visible_to_the_leak_guard` (:62-75) — THE red one.\n- `test_a_gitignored_file_stays_out_of_scope` (:78-91) — writes a probe to `var/tmp/` and asserts it stays out. `var/` is gitignored at `.gitignore:18` and holds ~600MB snapshots (`tests/test_repo_structure.py:64-67`).\n- `test_no_ignored_directory_leaks_into_the_candidate_set` (:94-102), parametrized over `.venv`, `__pycache__`, `node_modules`, `var` — four independent cases.\n\nFULL LOCAL GATE, run at the end of EVERY phase before `/commit`:\n  uv run pytest -m \"not gamedata\"\n  uv run ruff check .\n  uv run ruff format --check .\n  uv run mypy\nmypy is strict over `src` AND `tests` (`pyproject.toml:91-95`), so every helper and test added in Phases 2-3 needs full annotations and a `-> None` return. `--strict-markers --strict-config` is in `addopts` (`pyproject.toml:100`), so do not invent a marker — the collection fails outright and presents as a broken repo (`pyproject.toml:101-107`).\n\nCI PARITY. `.github/workflows/ci.yml:45-57` runs ruff check, ruff format --check, mypy, then `pytest -m \"not gamedata\"` — the same four commands. `:70-78` additionally runs five node skill guards by explicit path; none of them read `tests/` or the commit skill, so Phase 4 does not put them at risk, but they run on the PR regardless.\n\nTHE ONE ASYMMETRY TO UNDERSTAND BEFORE TRUSTING A GREEN CI. In CI the checkout has no untracked files, so `--others` contributes nothing and CI's result is identical before and after this fix. **CI going green therefore proves nothing about the fix.** The proof is local: the repro's probe file only exists in a working tree. Do not treat a green PR as the verification.\n\nMANUAL VERIFICATION TO RECORD IN THE PHASE 1 COMMIT MESSAGE (all read-only):\n  git ls-files | Measure-Object -Line\n  git ls-files --cached --others --exclude-standard | Measure-Object -Line\nBoth returned 142 on a clean tree at edc7aea, and `Compare-Object` reported the sets identical — proof the widening adds zero junk. Re-run and record the numbers, since the tracked count moves with every commit.\n\nNEGATIVE TEST BY HAND, once, after Phase 1: write a scratch file into `var/` containing a banned pattern and confirm `uv run pytest tests/test_no_leaks.py -q` stays green; then write one into the repo root and confirm it goes red. Delete both. This is the human-legible version of what the six counterweights assert.",
  "risks": [
    "THE PROBE FILE IS A LANDMINE IF A RUN IS INTERRUPTED. `tests/test_leak_guard_scope.py:70` writes `_leak_guard_probe.md` into the REPO ROOT with a real banned string, removing it in a `finally` at :51. After Phase 1 the widened guard SEES the repo root, so if a run is killed (Ctrl-C, a crash, a killed terminal) the orphaned probe makes every subsequent `uv run pytest` fail in `test_no_machine_paths_or_identifiers` with a confusing violation in a file the implementer never wrote. REMEDY, and put it in the plan's own References: if the suite starts failing on `_leak_guard_probe.md`, delete that file. Same for `var/tmp/_leak_guard_ignored_probe.md`. Do not stage either, ever.",
    "PARALLEL TEST EXECUTION WOULD MAKE THE SUITE NON-DETERMINISTIC. The probe exists in the tree for the duration of one test. Serially this is safe — `test_leak_guard_scope.py` sorts before `test_no_leaks.py` and always cleans up first. Under `pytest-xdist` (`-n auto`) the two files can run concurrently and `test_no_machine_paths_or_identifiers` would intermittently see the probe and fail. `pytest-xdist` is NOT in the dev group (`pyproject.toml:29-37`) — do not add it as part of this change, and if anyone adds it later this pair needs a lock or a serial marker.",
    "AN OPERATOR'S OWN SCRATCH NOTES BECOME BUILD FAILURES. Anyone keeping an untracked TODO or notes file at the repo root with a Windows path in it now gets a red suite. This is the intended behaviour, but it is a real usability regression and the whole reason a widened guard can get switched off (`tests/test_leak_guard_scope.py:78-91` argues exactly this). MITIGATION: the remedy is `var/` — it is already the gitignored scratch root (`.gitignore:14-18`) and is invisible to the widened guard by measurement. Say so in the Phase 1 commit message and in the `/commit` sentence added in Phase 4, so the first person who hits it knows where to put the file rather than reaching for `EXEMPT_PREFIXES`.",
    "`--exclude-standard` PULLS IN MACHINE-SPECIFIC EXCLUDE SOURCES. It honours `.git/info/exclude` and the user's global `core.excludesFile`, neither of which is in version control. Two developers can therefore get different candidate sets from the same tree. The blast radius is bounded — it can only make the guard see LESS locally, and CI has neither file and no untracked files anyway — but it means 'green on my machine' is a weaker statement than it looks. Do not attempt to suppress this with `--no-standard-notes` style flags; inheriting git's exclusion machinery wholesale is the point, and hand-reimplementing `.gitignore` is the failure the counterweights forbid.",
    "THE OBVIOUS-LOOKING ALTERNATIVE IS MEASURABLY CATASTROPHIC AND WOULD PASS EVERY EXISTING TEST. `git status --porcelain --untracked-files=all` is proposed in the intake's Open Question 3 and is REFUTED: it reports only CHANGED entries, so on a clean tree it returns 0 paths. Substituting it silently reduces the guard from 142 files to whatever happens to be dirty, and every existing test still passes — because they only assert that no violation is FOUND. If the implementer reaches for it out of familiarity, the suite will not stop them. It is called out here for exactly that reason.",
    "THE STALE `measured` MEMORY ENTRY IS ACTIVELY HARMFUL IF LEFT. `.claude/agents/data-engineer-memory.md:78-85` tells agents to hand-run `PATTERNS` because the guard is blind. Left uncorrected it teaches a workaround for a check that now works — the same failure mode the entry's own parenthetical at :82-84 records having already been corrected once, in the opposite direction. Phase 5 is not cosmetic.",
    "SCOPE CREEP TOWARD A SECRET SCANNER. The RCA is explicit: direction (c), a real credential scanner, is 'genuinely valuable and genuinely separate' and belongs on the FEATURE track; direction (b), a pre-commit hook, is refused because a hook lives outside version control and protects only the machine that installed it. Do not add either in this change, and do not add a `gitleaks` step to `.github/workflows/ci.yml` — however tempting given that `.claude/skills/commit/SKILL.md:78` already promises one.",
    "THE FALSE `gitleaks` CLAIM WILL TEMPT AN EDIT IN PHASE 4. Phase 4 edits the block that CONTAINS it (`.claude/skills/commit/SKILL.md:71-79`). The RCA assigns it to `requests/bugfix-requests/port-residue-sweep/` under 'What this does not close', because filing it as a fifth request would fragment one finding across three trackers. Fixing it here would be a plausible-looking diff that quietly undermines a decided piece of triage.",
    "PHASE 3 CREATES A FILE WITH AN OOTP-RESERVED SUFFIX INSIDE `tests/fixtures/`. `tests/fixtures/README.md:26` and `tests/fixtures/synthetic.py:6` both build bytes rather than shipping a `.dat`, precisely because `test_game_data_is_not_tracked` treats the suffix as banned. The probe must be a placeholder created and unlinked in a `finally`, never staged, and never real save bytes (ADR 0006). Running Phase 3's tests with a dirty index is how it accidentally gets committed."
  ],
  "files_to_touch": [
    {
      "path": "tests/test_no_leaks.py",
      "change": "PHASE 1 (required): argv at :33 becomes `[\"git\", \"ls-files\", \"--cached\", \"--others\", \"--exclude-standard\"]`, plus a comment above it recording why all three flags are load-bearing and naming the refuted `git status --porcelain -uall` alternative; module docstring at :1-5 rewritten so its scope statement matches the new behaviour. PHASE 2 (gated): add `p.is_file()` to the append condition at :46-47 and widen the handler at :85-88 to `(UnicodeDecodeError, FileNotFoundError)`. PHASE 3 (gated): extract a `repo_files() -> list[str]` helper and route both `tracked_text_files()` (:31-48) and `test_game_data_is_not_tracked()`'s shell-out (:99-105) through it; update that test's docstring at :98 and its assertion message at :116 from 'never be tracked' to 'never be tracked, or sit un-ignored in the tree'."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "change": "DO NOT MODIFY IN PHASE 1 — it is the acceptance contract and must go green untouched. PHASE 2 (gated): append a monkeypatch-based `test_a_tracked_file_deleted_from_the_worktree_does_not_crash_the_guard`. PHASE 3 (gated): append two game-data scope tests using the existing `untracked_file` helper at :38-51 — an untracked `tests/fixtures/*.dat` probe IS seen, a `var/tmp/` one is NOT."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "change": "PHASE 4: add ONE sentence inside Step 2's sanity-check block at :71-79 saying the leak guard now sees unstaged files, so `uv run pytest tests/test_no_leaks.py -q` should run BEFORE `git add`. The `gitleaks` sentence at :78 must come out of the diff byte-identical."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "change": "PHASE 5: correct the `measured` entry at :78-85, which after Phase 1 is false and instructs agents to hand-run PATTERNS around a guard that now works. Follow the in-place correction style already used at :82-84 rather than deleting. Its contrast with `tests/test_doc_links.py` also needs restating — both guards now see untracked files, by different mechanisms."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "change": "PHASE 5, judgment call: the bullet at :121 reads 'No machine-specific paths in tracked files.' Decide whether 'tracked' becomes 'in the repo tree'. Edit in place — this file is CLAUDE.md's declared single owner of the build rules, so never add a second copy elsewhere."
    },
    {
      "path": "tests/test_config.py",
      "change": "PHASE 5, optional one-word edit: the docstring at :62 says the guard 'scans every tracked file', which is now narrower than reality. Change it or record why it was left."
    },
    {
      "path": ".gitignore",
      "change": "PHASE 3 only, and only if that phase is disposed in: consider adding a bare `*.lg` beside `*.lg/` at :25 — measured, `foo.lg` as a plain FILE is not ignored today. Strictly a tightening. If changed, this triggers the full `/update-docs` sweep because CLAUDE.md describes these rules."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md",
      "change": "This plan itself. Opens at `> **Status:** planned · created 2026-08-17 · decided · next: implement`, and moves to `fixed` in Phase 5 along with its two siblings."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "PHASE 5, driven by `/commit`: Index row at :52 -> `fixed`, and the `[leak-guard-blind-to-untracked-files]` link repointed to `_done/leak-guard-blind-to-untracked-files/` when the directory moves."
    },
    {
      "path": ".github/workflows/ci.yml",
      "change": "NO CHANGE. Listed so the implementer stops and confirms rather than guessing: re-read :20-24 and satisfy yourself that 'test_no_leaks.py shells out to `git ls-files`; it needs the repo, not a detached blob export' is still literally true of the new argv. It is. Leave the file alone."
    }
  ],
  "code_references": [
    {
      "ref": "tests/test_no_leaks.py:32-38 (`tracked_text_files`, the `subprocess.run` call)",
      "claim": "The cause. Argv is `[\"git\", \"ls-files\"]` at :33 with `cwd=REPO_ROOT, capture_output=True, text=True, check=True`. `git ls-files` enumerates the INDEX, so a file just written is absent from the candidate list and :83 never opens it. Read and confirmed."
    },
    {
      "ref": "tests/test_no_leaks.py:39-47 (the `keep` set and the append loop)",
      "claim": "Everything downstream of the argv survives the swap unchanged: `.md .py .toml .yml .yaml .json .sql .example .txt` plus `.env.example` by name. `--others` emits the same repo-relative forward-slash shape as `--cached`, so `REPO_ROOT / rel` at :45 needs no adjustment. Read and confirmed."
    },
    {
      "ref": "tests/test_no_leaks.py:16-18 (`EXEMPT`, `EXEMPT_PREFIXES`)",
      "claim": "`EXEMPT` holds exactly one entry, `tests/test_no_leaks.py` — which is why the RCA and the bug report describe banned strings rather than quoting them. `EXEMPT_PREFIXES` is the empty tuple, so the `startswith` filter at :43 is currently a no-op. Read and confirmed."
    },
    {
      "ref": "tests/test_no_leaks.py:85-88 (the `try` / `except UnicodeDecodeError`)",
      "claim": "Only `UnicodeDecodeError` is handled. A tracked file deleted from the worktree but not staged is still in `--cached`, so `read_text` raises an uncaught `FileNotFoundError` and the guard errors instead of reporting. Phase 2's justification. Read and confirmed."
    },
    {
      "ref": "tests/test_no_leaks.py:97-116 (`test_game_data_is_not_tracked`)",
      "claim": "A SECOND independent `git ls-files` shell-out at :99-105 with the same blindness, filtering `banned_names`/`banned_suffixes` at :106-107. The RCA's Root tier and 'What this does not close'. Read and confirmed."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:62-75 (`test_an_untracked_file_is_visible_to_the_leak_guard`)",
      "claim": "The RED reproduction, and it is COMMITTED (contrary to the RCA's 'Not yet committed' — it landed in edc7aea; `git ls-files tests/test_leak_guard_scope.py` returns it). I ran it: fails at :72 with 'the leak guard cannot see an untracked file, so it fires only once the content is staged'."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:78-102 (the counterweights)",
      "claim": "Six green tests that pin what the fix must NOT do: `var/tmp/` stays out (:78-91), and `.venv`/`__pycache__`/`node_modules`/`var` must produce zero candidates (:94-102, parametrized). These are what make a naive `rglob` widening fail. Read and confirmed."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:38-51 (`untracked_file` context manager)",
      "claim": "Writes a real probe into the working tree and unlinks it in a `finally`; it refuses to clobber an existing path at :46. The reason a `tmp_path` fixture cannot serve is stated at :42-44 — the guard enumerates the repository, so the probe must live inside it. Reusable for Phase 3's `.dat` probes. Read and confirmed."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:33-35 (`LEAK`)",
      "claim": "The banned string is assembled at runtime from `chr(92)` so this file never contains a literal one — it is not in `EXEMPT`. Anti-vacuity is pinned separately at :54-59. Read and confirmed."
    },
    {
      "ref": ".github/workflows/ci.yml:20-24 (`actions/checkout@v7`, `fetch-depth: 1`)",
      "claim": "Carries the comment 'test_no_leaks.py shells out to `git ls-files`; it needs the repo, not a detached blob export'. Still true of `--cached --others --exclude-standard`. Leave unedited. Read and confirmed."
    },
    {
      "ref": ".github/workflows/ci.yml:3-6 (triggers)",
      "claim": "`pull_request` and `push` to `main` only — no feature-branch push trigger, so a leak can be committed and pushed with nothing having run. This is the amplifier that makes moving detection to the local test run worth doing. Read and confirmed."
    },
    {
      "ref": ".github/workflows/ci.yml:45-57 (ruff check, ruff format --check, mypy, pytest -m \"not gamedata\")",
      "claim": "The exact four commands the per-phase local gate must reproduce before `/commit`. Read and confirmed."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:71-79 (Step 2 sanity-check block)",
      "claim": "Where the ordering note goes. :77-79 is the 'catching it before it enters history is the difference between an edit and a history rewrite' sentence AND the false `gitleaks will catch it in CI' claim, which must stay byte-identical (RCA reserves it for port-residue-sweep). Read and confirmed."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:126-135 (the request-status table)",
      "claim": "Terminal stage `fixed` requires updating the Index row AND moving the directory once into `_done/` with the link repointed; status grammar for bugfix work is `intake -> diagnosed -> planned -> fixed`. Phase 5's mechanics. Read and confirmed."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:96-99 (the data-engineer-memory trigger)",
      "claim": "`.claude/agents/data-engineer-memory.md` appearing in the staged diff mandates the FULL /update-docs sweep — the trigger is the file's presence, not a judgment about the entries. Phase 5 therefore cannot use the two-minute doc check. Read and confirmed."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:210-216, :218-237",
      "claim": "Hard rails: never `--no-verify`, never `--amend`, never `-A` at the commit step; never push `main`, never force-push, never open the PR. Also records at :239-241 that a first push to a fresh branch triggers no CI. Read and confirmed."
    },
    {
      "ref": ".claude/agents/data-engineer-memory.md:78-85",
      "claim": "A `measured`-labelled entry stating `tests/test_no_leaks.py` iterates `git ls-files` so a new file is invisible until commit, instructing agents to import `PATTERNS` and hand-scan instead, and contrasting it with `test_doc_links.py`'s `rglob`. Phase 1 falsifies it. Its own parenthetical at :82-84 shows the in-place correction style. Read and confirmed."
    },
    {
      "ref": ".claude/agents/data-engineer.md:121",
      "claim": "'No machine-specific paths in tracked files. `tests/test_no_leaks.py` enforces it.' The word 'tracked' becomes narrower than the guard after Phase 1. Read and confirmed."
    },
    {
      "ref": "tests/test_doc_links.py:159-171 (`markdown_files`)",
      "claim": "The sibling guard's enumeration: `REPO_ROOT.rglob(\"*.md\")` excluding `.git`, `var` and `_done` — a hand-written exclusion list that does NOT exclude `.venv/`, `__pycache__/` or `node_modules/`. The precedent to cite as what NOT to copy. Read and confirmed."
    },
    {
      "ref": ".gitignore:61-62 (`!datasets/**`, `!tests/fixtures/**`)",
      "claim": "Two negations that un-ignore game-data suffixes under those trees. Measured with `git check-ignore -q --no-index`: `tests/fixtures/players.csv`, `tests/fixtures/x.dat` and `datasets/x.dat` all exit NON-ZERO, i.e. NOT ignored. This is the concrete exposure Phase 3 closes."
    },
    {
      "ref": ".gitignore:25 (`*.lg/`)",
      "claim": "Matches directories only. Measured: `git check-ignore -q --no-index -- foo.lg` exits non-zero, so a plain FILE named `foo.lg` is un-ignored and invisible to `test_game_data_is_not_tracked` until staged."
    },
    {
      "ref": ".gitignore:4-6, :18, :27-31",
      "claim": "`.env` ignored at :4 and un-ignored at :6 by `!.env.example`; `var/` at :18; `players.csv` :27, `names.xml` :28, `*.dat` :31. Measured through the widened enumeration: `.env` absent, `.env.example` present, `var/` contributes 0 — the exclusion behaviour the fix inherits for free."
    },
    {
      "ref": "pyproject.toml:91-95 ([tool.mypy])",
      "claim": "`strict = true`, `warn_unreachable = true`, `files = [\"src\", \"tests\"]` — every helper and test added in Phases 2-3 needs full annotations. Read and confirmed."
    },
    {
      "ref": "pyproject.toml:98-108 ([tool.pytest.ini_options])",
      "claim": "`addopts = \"-q --strict-markers --strict-config\"`, `testpaths = [\"tests\"]`, and exactly one marker, `gamedata`. Inventing a second marker is a hard COLLECTION error per the comment at :101-107. Read and confirmed."
    },
    {
      "ref": "pyproject.toml:28-37 ([dependency-groups] dev)",
      "claim": "pytest, pytest-cov, ruff, mypy, types-PyMySQL. No `pytest-xdist` — which is what keeps the probe-file/leak-guard test pair deterministic. Read and confirmed."
    },
    {
      "ref": "tests/test_skill_references.py:86-94 (`test_every_repo_path_a_skill_names_exists`)",
      "claim": "Any repo path named in a skill file must exist. Constrains the Phase 4 edit to `.claude/skills/commit/SKILL.md`. Read and confirmed."
    },
    {
      "ref": "tests/test_repo_structure.py:64-79 (`test_var_is_gitignored`, `test_gm_memory_carve_out_survives`)",
      "claim": "The house pattern for pinning a `.gitignore` invariant with a regex over the file's text — the model to follow if Phase 3 adds a bare `*.lg` line. Read and confirmed."
    },
    {
      "ref": "tests/fixtures/README.md:26",
      "claim": "States that `tests/test_no_leaks.py::test_game_data_is_not_tracked` 'catches the obvious cases'. Measured above, it cannot catch an un-ignored `.dat` under `tests/fixtures/` until that file is staged — so the sentence overstates the guard until Phase 3 lands."
    },
    {
      "ref": "requests/bugfix-requests/README.md:45, :52",
      "claim": ":45 fixes the status grammar `intake -> diagnosed -> planned -> fixed`. :52 is this slug's Index row, currently `diagnosed`, to become `planned` when the plan lands and `fixed` at Phase 5. Read and confirmed."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:175-231",
      "claim": "The stage-3 section MENU. Sections 1-8 and References are Always/Default; §9 Data contracts is Conditional and is OMITTED here — this change touches no dataset, no source registration, no grain. §10 Code-grounding verification is included, since every reference above was verified by reading. Read and confirmed."
    }
  ],
  "open_questions": [
    "GATED — fold in `test_game_data_is_not_tracked` (Phase 3)? The RCA lists it under Root and again under 'What this does not close, unless the plan folds it in'. RECOMMEND YES, on measurement rather than symmetry: `tests/fixtures/players.csv`, `tests/fixtures/x.dat` and `datasets/x.dat` are all un-ignored today (the `!tests/fixtures/**` and `!datasets/**` negations at .gitignore:61-62 override the game-data rules), so a real save file dropped into the fixtures directory is invisible to that guard until someone stages it — while `tests/fixtures/README.md:26` tells readers it is covered. The counter-argument is scope discipline: the bugfix contract is satisfied by Phase 1 alone.",
    "GATED — tighten `.gitignore:25` from `*.lg/` to also cover a plain `*.lg` file? Measured: `foo.lg` is not ignored today. RECOMMEND YES if Phase 3 runs (it is strictly a tightening — a directory named `foo.lg` is already covered), NO as a standalone, since without Phase 3 nothing enforces it.",
    "GATED — Phase 2's dirty-tree robustness. Strictly it is pre-existing and outside the red-goes-green contract. RECOMMEND YES anyway: Phase 1 is what makes 'run the suite mid-refactor' the normal case, and a guard that raises `FileNotFoundError` instead of reporting is a guard people learn to skip. It costs one condition and one monkeypatched test.",
    "GATED, AND THE RCA'S HARDENING ITEM — should `tests/test_no_leaks.py` gain a fenced-code exemption, as `tests/test_doc_links.py` did on 2026-08-17 (`strip_fences` at :55-93)? RECOMMEND NO, and recommend recording the refusal rather than leaving it to drift. The RCA states the counter-argument itself: a fence exemption in a LEAK guard is a channel for smuggling a credential past it, which is not true of a link checker. The cost is real and visible — this plan, the RCA and the bug report all had to describe strings rather than quote them — but 'describe, do not quote' is a cheap standing rule and an exemption is not reversible once artifacts start relying on it. A narrower alternative, adding the bugfix directory to `EXEMPT_PREFIXES` (:18, currently empty), has the same smuggling shape in a smaller box; I would decline that too. Whichever way it goes, the decision should be written down once — the RCA's own request.",
    "NOT IN SCOPE, RESOLVED UPSTREAM, listed so nobody re-opens them mid-implementation: a pre-commit hook (direction (b)) is REFUSED — a hook lives outside version control and protects only the machine that installed it; a real secret scanner (direction (c)) is a FEATURE-track item, and nothing in this repo scans for credentials at all today; the false `gitleaks` promise at `.claude/skills/commit/SKILL.md:78` belongs to `requests/bugfix-requests/port-residue-sweep/`.",
    "BOOKKEEPING — the RCA's Reproduction section says the repro is 'Not yet committed', but it landed in commit edc7aea and `git ls-files tests/test_leak_guard_scope.py` returns it. The RCA also measured 140 paths where the tree now has 142 (two commits of drift). Neither changes the verdict or the fix. Worth one corrective sentence when the artifact is archived in Phase 5, or worth explicitly leaving as the historical record it is — the implementer should not silently rewrite a decided artifact's measurements."
  ]
}
~~~

## Proposal 2

~~~
{
  "planner": "sequencing",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Verdict confirmed-bug; cause at its `Evidence` section; the tiered fix posture and the gated direction decision (a)+(d) yes, (b) no, (c) feature-track. Consume it — do not re-open the verdict."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/BUGFIX_REQUEST.md",
      "why": "Context only. Its `Affected Area & Pointers` (:109-123) is the read order; its Open Questions 1-3 were all disposed by the RCA."
    },
    {
      "path": "tests/test_no_leaks.py",
      "why": "The file being fixed. `tracked_text_files()` at :31-48 is the whole defect; `PATTERNS` :24-28; `EXEMPT` :16; `EXEMPT_PREFIXES` :18 (currently empty); the `keep` suffix set :39; the second blind enumeration in `test_game_data_is_not_tracked` at :97-116."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "why": "The committed red repro (contrary to the RCA's 'Not yet committed' note — it landed in edc7aea). One RED test at :62-75, six counterweights at :54-59 and :78-102 that pin what the fix must NOT do. Its `untracked_file` helper at :39-51 writes into the real tree and cleans up in a `finally`."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "The gates the phases must satisfy: ruff check :46, ruff format --check :49, mypy :52, `pytest -m \"not gamedata\"` :57, node skill guards :70-78. The comment at :22-24 records that the `git ls-files` dependency on a real checkout is deliberate — the fix must keep that true."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "why": "Step 2 (:49-79) is where the RCA's recommendation (d) lands. :77-79 holds BOTH the sentence to amend and the false `gitleaks` claim that is explicitly out of scope. :96-99 is the trigger that makes editing data-engineer-memory.md force a full /update-docs sweep. :114-151 owns the request-status advance."
    },
    {
      "path": "tests/test_doc_links.py",
      "why": "The sibling Markdown guard. `markdown_files()` at :159-171 uses `rglob` and therefore already sees untracked files — the asymmetry this fix removes. `strip_fences()` at :55-92 is the reusable implementation if the gated fence-exemption decision comes back yes."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "why": "Lines 78-85 carry a `measured` entry that says the leak guard cannot see untracked files and instructs agents to work around it. Phase 1 makes that entry FALSE; leaving it is exactly the drift `test_agent_contract.py::test_memory_entries_carry_an_epistemic_label` exists near."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The pipeline contract. Stage table :14-18, the 'done' definition :24-26 (red repro green + regression test left behind), status grammar :45, and this bug's Index row at :52 which must advance to `fixed`."
    },
    {
      "path": "pyproject.toml",
      "why": "The local gate's shape: mypy is strict over BOTH src and tests (:91-95), ruff line-length 100 with E501 ignored (:56, :74-76), pytest `--strict-markers --strict-config` over `testpaths=[\"tests\"]` (:98-100). Any helper added to a test module must be fully annotated."
    },
    {
      "path": ".gitignore",
      "why": "The negative space the widened guard relies on: `.env` ignored / `!.env.example` restored (:4-6), `var/` (:18), the game-data block (:25-31), the `!gm/**` carve-out (:55-56). `--exclude-standard` reads exactly this file, so it is now load-bearing for the guard's usability."
    },
    {
      "path": "tests/test_agent_contract.py",
      "why": "`test_deny_set_still_protects_the_guards` at :76-81 asserts `tests/` is in the data-engineer subagent's deny set. This whole fix lives in `tests/`, so it CANNOT be delegated to that subagent — the implementer does it directly."
    }
  ],
  "architecture_notes": "SHAPE OF THE CHANGE. This is a pure repo-tooling fix. It touches no parser, no dbt model, no dataset, no save file, and no warehouse table — so the plan carries no data-contracts section, and the parser conventions (sequential walk, no fixed offsets, players.csv as ground truth, epistemic labelling of field mappings) do not apply to the code being written. They still apply as things the change must not weaken.\n\nTHE MECHANISM. `tests/test_no_leaks.py:31-48` builds its candidate set by shelling out to `[\"git\", \"ls-files\"]` (:32-38). That command enumerates the INDEX. Everything downstream is correct: the `keep` suffix filter at :39, the `EXEMPT`/`EXEMPT_PREFIXES` skip at :43, the per-line pattern application at :89-92. The bug is that :83 never receives the path of a file that exists on disk but has not been staged, so `PATTERNS` at :24-28 is never applied to it. It is a scope defect, not a pattern defect — every real leak in the 2026-08-17 session matched `PATTERNS` and was found by a hand scan that imported them.\n\nTHE FIX SURFACE IS ONE ARGV LIST, but the enumeration it produces is a different KIND of list, and three properties change with it:\n\n1. Membership. `git ls-files --cached --others --exclude-standard` = tracked ∪ untracked, minus everything `.gitignore` excludes. Re-measured on this tree 2026-08-17: 142 paths, byte-identical set to plain `git ls-files` on a clean tree (Compare-Object returned nothing), zero duplicates, zero entries under `.venv/`, `__pycache__/`, `node_modules/` or `var/`, `.env` absent, `.env.example` present. Runtime 27ms. The RCA measured 140/141 on a smaller tree; the delta is the two files committed since (edc7aea).\n\n2. Liveness. Under `--cached` alone the candidate paths were index entries the working tree usually agrees with. Under the union, the list now includes files an agent wrote seconds ago — which is the point — and that makes two latent hazards live. (a) A tracked file DELETED from the working tree is still listed by `--cached`; `path.read_text()` at :86 catches only `UnicodeDecodeError` (:87-88), so it would raise `FileNotFoundError` and the guard would crash rather than report. (b) `core.quotePath` is unset on this machine (default TRUE, measured), so `git ls-files` C-quotes any path with a non-ASCII or special character. Under the old scope such a file had to be deliberately staged; under the new scope any file an agent writes — a `reviews/` note with an em-dash in its name — is enumerated, and the quoted literal will not resolve on disk. Both are fixed by reading `-z`-delimited output and tolerating an unreadable path.\n\n3. Blast radius of the author's own scratch. Once Phase 1 lands, `uv run pytest` scans whatever the implementer has lying in the tree unignored. That is the fix working, and it is also the single most likely surprise during the build. `var/` (.gitignore:18) and the session scratchpad outside the repo are the sanctioned places to put working files.\n\nTHE SECOND BLIND ENUMERATION. `test_game_data_is_not_tracked` at :97-116 repeats `[\"git\", \"ls-files\"]` at :99-105 and has the same blindness for `.dat`/`.lg`/`players.csv`. Measured caveat the plan must state honestly: every banned name and suffix at :106-107 is ALREADY covered by `.gitignore:25-31`, so widening that function with `--exclude-standard` surfaces nothing today. Its value is that it converts \"the .gitignore rule covers this\" from an assumption into a checked property — if a rule is ever removed or shadowed by a negation, an untracked `players.csv` would then surface and the test fires. That is worth having, but it is a smaller prize than the RCA's framing suggests and it belongs in its own late, droppable phase.\n\nWHY THE FUNCTION NAME IS NOT COSMETIC. The RCA's third argument for `confirmed-bug` (its Verdict section) is that the module docstring at :1-5 — \"Nothing machine-specific may be tracked\" — is the narrowest statement of intent in the repo and was written by the same commit as the enumeration. Leaving `tracked_text_files` and that docstring in place after widening re-arms exactly that argument for the next agent, who will read the name, conclude the widening was a mistake, and narrow it back. The naming/docstring pass is the durability half of the fix.\n\nWHAT THE COUNTERWEIGHTS BUY. `tests/test_leak_guard_scope.py` is already the regression harness the bugfix contract (requests/bugfix-requests/README.md:24-26) asks to be \"left behind\". Six of its seven tests are green today and pin the failure mode of a careless fix: :78-91 a gitignored file stays out, :94-102 none of `.venv`/`__pycache__`/`node_modules`/`var` enter the set, :54-59 the probe string still matches a live pattern so the scope assertions cannot pass vacuously. The implementer adds to this module rather than creating a new one.\n\nWHO MAY DO THE WORK. `tests/` is in the data-engineer subagent's deny set (`tests/test_agent_contract.py:76-81`), so this fix must not be delegated to `.claude/agents/data-engineer.md`. The implementer edits directly. Subagents used for review get read-only git.",
  "phases": [
    {
      "name": "Phase 0 — Re-measure the enumeration idiom on this tree, and record the baseline",
      "goal": "Confirm the RCA's measured table still holds on the tree as it exists today, BEFORE any code changes, and leave a durable record of the numbers. The RCA's counts (140/141) were taken on a smaller tree and its 'Not yet committed' claim about the repro is already stale — so verify rather than inherit.",
      "steps": [
        "Confirm the red repro is red and the tree is clean: `uv run pytest tests/test_leak_guard_scope.py -q`. Expect exactly `.F.....` with `test_an_untracked_file_is_visible_to_the_leak_guard` failing at tests/test_leak_guard_scope.py:72. Then `git status --porcelain --untracked-files=all` must print nothing — the repro writes `_leak_guard_probe.md` into the repo root and removes it in a `finally` (tests/test_leak_guard_scope.py:48-51); a leftover means a crashed run, not a clean baseline.",
        "Capture the full offline baseline: `uv run pytest -m \"not gamedata\" -q`. Record the pass/fail counts. Exactly one failure is expected — the repro. Anything else is pre-existing and must be surfaced, not fixed here.",
        "Measure both enumerations side by side and diff the SETS, not just the counts: `git ls-files` vs `git ls-files --cached --others --exclude-standard`. Record: total count each, the set difference, whether any path repeats.",
        "Measure the four counterweight properties directly against the wide form: count entries whose path contains `.venv`, `__pycache__`, `node_modules`, and `var/` (expect 0 each); confirm `.env` is ABSENT and `.env.example` is PRESENT (the `!.env.example` negation at .gitignore:6 is what makes the second true, and the first is what keeps the guard out of permanent conflict with a file whose job is machine-specific values).",
        "Measure the untracked case without hand-writing a probe: it is already covered by the repro at tests/test_leak_guard_scope.py:70-75, which will flip in Phase 1. Note it as covered-by-test rather than measuring it twice.",
        "Time the wide form (`Measure-Command`). Record the milliseconds. It runs on every local `pytest` invocation, so cost is a real acceptance property, not a curiosity.",
        "Record `git config --get core.quotepath`. An empty result means the default (TRUE) is in force and paths with non-ASCII characters WILL be C-quoted — this is the input to Phase 2.",
        "Write the numbers to `requests/bugfix-requests/leak-guard-blind-to-untracked-files/reviews/enumeration-measurement.md`. HARD RAIL: record COUNTS and property names only. Do not paste any enumerated path into that file — it becomes tracked on commit and is scanned by the very guard being fixed, and the RCA's opening blockquote explains why a report about a leak cannot quote one."
      ],
      "acceptance": [
        "`uv run pytest tests/test_leak_guard_scope.py -q` prints `.F.....` and names `test_an_untracked_file_is_visible_to_the_leak_guard` as the only failure.",
        "`git status --porcelain --untracked-files=all` is empty after that run — the repro cleaned up after itself.",
        "The full offline run `uv run pytest -m \"not gamedata\"` has exactly one failure and it is the repro.",
        "The measurement note exists at requests/bugfix-requests/leak-guard-blind-to-untracked-files/reviews/enumeration-measurement.md and records, as numbers: both enumeration counts, the set difference, 0 entries for each of the four junk roots, `.env` absent / `.env.example` present, the elapsed milliseconds, and the `core.quotepath` setting.",
        "The note contains no absolute path, no drive letter, no home directory and no email address — verify by running `uv run pytest tests/test_no_leaks.py -q` after staging it (the guard is still index-scoped at this phase, so staging is the only way to see it)."
      ],
      "commit_note": "Nothing behavioural changed; one new artifact under `reviews/`. Hand to `/commit`. Because the guard is still blind at this point, stage the note FIRST and re-run `uv run pytest tests/test_no_leaks.py -q` before answering yes — this phase is the last one where that ordering matters, which is itself the bug being fixed."
    },
    {
      "name": "Phase 1 — Widen the candidate set to tracked-plus-untracked-minus-ignored",
      "goal": "Flip the red repro green with the smallest possible behavioural change: the argv list at tests/test_no_leaks.py:33, plus the module docstring that would otherwise authorise narrowing it back. No rename, no robustness work, no second enumeration — those are separate, separately revertible commits.",
      "steps": [
        "Before writing anything: clear the tree of unignored scratch. Move any working notes into `var/` (gitignored, .gitignore:18) or the session scratchpad outside the repo. From this commit onward, `uv run pytest` reads whatever is lying in the tree unignored, and a machine path in your own draft will turn the suite red.",
        "Scrub this request's own `reviews/` trail files for absolute paths before proceeding. The RCA records that panel agents wrote 27 absolute machine paths into untracked trail files during the 2026-08-17 session; those files sit under this work-dir and become in-scope the moment this phase lands. Import `PATTERNS` from tests/test_no_leaks.py and run it over them by hand, exactly as the RCA describes the manual scan working.",
        "Edit tests/test_no_leaks.py:32-38: change the argv from `[\"git\", \"ls-files\"]` to `[\"git\", \"ls-files\", \"--cached\", \"--others\", \"--exclude-standard\"]`. Leave `cwd=REPO_ROOT`, `capture_output=True`, `text=True`, `check=True` exactly as they are — `check=True` is what makes a git failure loud instead of an empty candidate set, which is the vacuous-pass failure mode this guard exists to avoid.",
        "Add a comment above the call, in the style the file already uses at :20-23, stating WHY all three flags are present: `--cached` keeps the 142 tracked paths, `--others` adds files that exist but are not staged, `--exclude-standard` is what keeps `.venv/`, `__pycache__/`, `node_modules/`, `var/` and `.env` out. Name the consequence of dropping `--exclude-standard` — the guard becomes unusable and gets switched off — because that is the pressure the next editor will be under.",
        "Rewrite the module docstring at tests/test_no_leaks.py:1-5 so it describes the new scope. The current sentence 'Nothing machine-specific may be tracked' is the RCA's exhibit for why this was arguable at all; replace it with wording that covers files present in the working tree, not only files in the index, and say plainly that the guard fires before content can enter history.",
        "Do NOT touch `PATTERNS` (:24-28), `EXEMPT` (:16), `EXEMPT_PREFIXES` (:18) or the `keep` suffix set (:39) in this phase. In particular, do not add a prefix to `EXEMPT_PREFIXES` to quiet new noise — an exempted prefix is a re-created blind spot, and it is the exact shape of the defect being fixed.",
        "Do NOT edit any assertion or message in tests/test_leak_guard_scope.py. The repro must go green by the code changing, not by the test changing."
      ],
      "acceptance": [
        "`uv run pytest tests/test_leak_guard_scope.py -q` → 7 passed, 0 failed. The previously RED `test_an_untracked_file_is_visible_to_the_leak_guard` is green and the six counterweights (:54-59, :78-91, :94-102) are still green — the second half is what proves the widening did not buy visibility by scanning everything.",
        "`uv run pytest tests/test_no_leaks.py -q` → 3 passed. In particular `test_patterns_still_catch_real_leaks` (:51-78) is untouched and green, proving no pattern was loosened to make the suite pass.",
        "`git diff` for tests/test_leak_guard_scope.py is EMPTY. The repro was not edited.",
        "`uv run pytest -m \"not gamedata\"` is fully green — zero failures, matching the Phase 0 baseline minus the one repro failure.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all clean (these are ci.yml:46, :49 and :52 verbatim).",
        "Negative control, run by hand and then undone: create an untracked file at the repo root containing a banned shape assembled the way tests/test_leak_guard_scope.py:35 assembles `LEAK`, run `uv run pytest tests/test_no_leaks.py -q`, and confirm it goes RED naming that file — then delete it and confirm green again. The regression test asserts membership in the candidate set; this confirms the whole chain from enumeration through `PATTERNS` to a failing assertion.",
        "The comment at .github/workflows/ci.yml:22-24 is still true: the new form still requires a real checkout rather than a detached blob export. Confirm by reading it; no edit expected."
      ],
      "commit_note": "This is the fix. Red repro green, six counterweights green, one file changed. Hand to `/commit`. It is deliberately the smallest revertible unit — if anything downstream goes wrong, reverting this one commit restores the old behaviour without unpicking a rename or a robustness change."
    },
    {
      "name": "Phase 2 — Make the widened enumeration robust to the files it can now see",
      "goal": "Close the two hazards that the widening makes live: a quoted path that does not resolve on disk, and a tracked-but-deleted path that raises on read. Both turn the guard from 'reports a leak' into 'crashes', and a guard that crashes gets disabled.",
      "steps": [
        "Switch the enumeration to NUL-delimited output: add `-z` to the argv and split `out.stdout` on `\\0` instead of `splitlines()`, dropping the trailing empty element. `-z` suppresses git's C-quoting entirely, so a path containing a non-ASCII character, a space-plus-quote, or a newline arrives verbatim. Measured input for this step: `git config --get core.quotepath` is unset on this machine, i.e. quoting is ON by default (Phase 0 recorded it).",
        "Make the read tolerant at tests/test_no_leaks.py:85-88. Today the `try` catches only `UnicodeDecodeError`. Widen it to also swallow `OSError` (which covers `FileNotFoundError` for a `--cached` entry deleted from the working tree, and a permission error on a locked file). Keep the `continue` — an unreadable file is not a leak, and the alternative is the whole guard erroring out.",
        "Add a regression test to tests/test_leak_guard_scope.py: a file whose NAME contains a non-ASCII character is enumerated. Build the name with an escape (`–` or `chr(...)`) rather than a literal glyph — ruff's RUF001/RUF003 flag ambiguous unicode in source, and tests/test_doc_links.py:40 already uses the escape form for exactly this reason. Reuse the existing `untracked_file` context manager at tests/test_leak_guard_scope.py:39-51 so cleanup stays in a `finally`.",
        "Add a second regression test: the guard does not raise when a `--cached` path is absent from the working tree. Do NOT delete a real tracked file to produce this — that is a working-tree mutation a test must not make. Instead assert the property at the read layer: call the module's scanning test body against a candidate list containing a non-existent path, or factor the read into a small annotated helper and test the helper. Choose whichever keeps `uv run mypy` (strict over tests, pyproject.toml:91-95) clean with full annotations.",
        "Keep both new tests in tests/test_leak_guard_scope.py rather than a new module — that file's docstring (:1-19) already declares itself the owner of WHERE the guard looks, and these are scope-and-liveness properties, not pattern properties."
      ],
      "acceptance": [
        "`uv run pytest tests/test_leak_guard_scope.py -q` → 9 passed (7 pre-existing + 2 new), 0 failed.",
        "Both new tests are demonstrated to FAIL against the Phase 1 code: temporarily revert `-z` and confirm the non-ASCII-name test goes red; temporarily narrow the `except` back to `UnicodeDecodeError` and confirm the tolerance test goes red. Then restore. A regression test never seen red is a regression test that may be asserting nothing.",
        "`uv run pytest -m \"not gamedata\"` fully green.",
        "`uv run ruff check .` clean — specifically no RUF001/RUF003 on the new test, proving the non-ASCII character was written as an escape.",
        "`uv run mypy` clean under strict — every new helper carries full parameter and return annotations.",
        "The enumeration timing is still in the same order of magnitude as the Phase 0 measurement (`-z` changes parsing, not work)."
      ],
      "commit_note": "Robustness only; no change to WHICH files are in scope. Hand to `/commit`. Separated from Phase 1 so a bisect can tell 'the widening broke it' apart from 'the parsing change broke it'."
    },
    {
      "name": "Phase 3 — Make the names and the surrounding docs tell the truth about the new scope",
      "goal": "Remove every remaining artifact that says the guard is index-scoped. This is the durability half: the RCA's own third argument for calling this a bug is that a guard's self-description was accepted as the authority on its scope, and a stale name or a stale memory entry re-arms that argument for the next agent.",
      "steps": [
        "Rename `tracked_text_files()` (tests/test_no_leaks.py:31) to a name that describes the new scope — e.g. `scannable_files()`. The name is now the only remaining place the old scope is asserted.",
        "Update the three call sites in tests/test_leak_guard_scope.py — :71, :88 and :99 — and nothing else in that file. The assertion text and messages stay byte-identical; only the attribute name on `guard.` changes.",
        "Confirm with a repo-wide grep that no other reference to `tracked_text_files` survives. Known references to check: .claude/agents/data-engineer-memory.md:85 names it in an evidence field.",
        "Correct .claude/agents/data-engineer-memory.md:78-85. That `measured` entry states the guard cannot see a file you just created and instructs agents to import `PATTERNS` and scan by hand. It is now FALSE, and it is a standing instruction to work around a check that works — the same failure the entry's own parenthetical correction of 2026-08-16 was already made for. Rewrite it as a dated entry with a valid epistemic label; `tests/test_agent_contract.py:84-95` requires one of {measured, verified, inferred, assumed, unconfirmed} in backticks on every dated line, so a rewrite that drops the label turns the suite red.",
        "Re-read .github/workflows/ci.yml:22-24. The comment says the guard 'shells out to `git ls-files`; it needs the repo, not a detached blob export.' Still true of the new form. Leave it, or tighten it to mention that untracked files are now in scope — but do not delete it: it is the record of why `fetch-depth: 1` is deliberate.",
        "Check whether CLAUDE.md:60 and docs/decisions/0006-public-repo-local-data.md:30 still describe the guard accurately. Both say it 'fails the build' on machine paths, which remains true and now understates rather than overstates — no edit required, but confirm rather than assume."
      ],
      "acceptance": [
        "`grep -rn \"tracked_text_files\"` over the repo returns zero hits.",
        "`uv run pytest tests/test_leak_guard_scope.py tests/test_no_leaks.py -q` → 12 passed.",
        "`uv run pytest tests/test_agent_contract.py -q` green — in particular `test_memory_entries_carry_an_epistemic_label` (:84-95) accepts the rewritten memory entry.",
        "Reading tests/test_no_leaks.py:1-5 and the new function name, a stranger would conclude the guard scans the working tree and not the index. State this as a read-aloud check, not a grep.",
        "`uv run pytest -m \"not gamedata\"` fully green; ruff check, ruff format --check and mypy all clean."
      ],
      "commit_note": "Rename plus doc-truth pass. Hand to `/commit`. NOTE: the staged diff will contain `.claude/agents/data-engineer-memory.md`, which per `.claude/skills/commit/SKILL.md:96-99` FORCES the full `/update-docs` sweep rather than the two-minute link check. That is intended — expect the gate to take longer here than in the other phases."
    },
    {
      "name": "Phase 4 — Fold in the second blind enumeration (droppable)",
      "goal": "Give `test_game_data_is_not_tracked` the same visibility, so a `.dat`, a `.lg` or a `players.csv` sitting unignored in the working tree is caught rather than waiting for someone to stage it. The RCA flags this as left open by a fix touching only the text scan.",
      "steps": [
        "FIRST, measure before building — the honest value of this phase is smaller than it looks. Every banned name and suffix at tests/test_no_leaks.py:106-107 (`players.csv`, `names.xml`, `world_default.xml`, `schools.xml`, `.dat`, `.lg`) is ALREADY covered by .gitignore:25-31, so `--exclude-standard` will filter them out and the widened enumeration surfaces nothing today. Confirm that by measurement, and record the result in the same reviews note Phase 0 created.",
        "Decide on the measurement. If confirmed, the phase's value is that it converts 'the .gitignore rule covers this' from an assumption into a checked property: if a rule is ever removed, renamed or shadowed by a negation, an untracked `players.csv` would then surface and this test would fire. That is real but modest. If the user would rather not carry it, DROP this phase — nothing downstream depends on it. Record the disposition either way.",
        "If kept: change the argv at tests/test_no_leaks.py:99-105 to the same wide form, reusing the enumeration helper from Phase 2 rather than writing a third `subprocess.run`. Three copies of the same idiom is how the second one drifted from the first.",
        "Add a counterweight test asserting a `.dat` under `var/` stays OUT of the offender list — `var/` is where every legitimate save snapshot lives (.gitignore:14-18), and a guard that flags the operator's own snapshots is a guard that gets disabled. Follow the pattern of tests/test_leak_guard_scope.py:78-91.",
        "Do NOT extend `banned_names` to catch a RENAMED copy of `players.csv`. That is a known, separately-owned gap — requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:411 records that the guard catches by filename only and that catching a renamed derived slice is on the implementer. Widening it here is scope creep into another live plan."
      ],
      "acceptance": [
        "The measurement result is recorded in the reviews note: how many `.dat`/`.lg`/banned-name paths the wide enumeration surfaces today (expected: zero, because .gitignore:25-31 covers them all).",
        "`uv run pytest tests/test_no_leaks.py -q` green, including the new `var/`-snapshot counterweight.",
        "The new counterweight is demonstrated red against a naive widening that omits `--exclude-standard`, then restored — proving it actually pins the property.",
        "Only one enumeration helper exists in tests/test_no_leaks.py; `grep -c \"git\\\", \\\"ls-files\" tests/test_no_leaks.py` shows the idiom is not duplicated.",
        "`uv run pytest -m \"not gamedata\"` fully green; ruff check, ruff format --check and mypy clean."
      ],
      "commit_note": "Optional and self-contained. Hand to `/commit`, or drop the phase entirely — record which, and why, in the plan's Decisions section so the disposition survives."
    },
    {
      "name": "Phase 5 — The `/commit` ordering note (RCA recommendation (d))",
      "goal": "Close the residual gap for anyone who does not run the suite before staging, with the one-sentence change the RCA describes as 'nearly free' — and touch nothing else in that skill.",
      "steps": [
        "Read `.claude/skills/commit/SKILL.md:49-79` (Step 2 — Stage deliberately) in full before editing. The paragraph at :77-79 is where the change goes.",
        "Add the ordering instruction: with the widened guard, `uv run pytest tests/test_no_leaks.py -q` now catches a machine path in an unstaged file, so it should be run at the survey/stage step rather than relied on after the fact. Keep it to a sentence or two — the skill's own rail at :28-30 says 'Keep this skill lightweight. It is a gate, not a pipeline.'",
        "HARD NON-GOAL: do NOT correct the false `gitleaks` claim in that same paragraph at :78. The RCA's 'What this does not close' section assigns it to requests/bugfix-requests/port-residue-sweep/ as a fourth instance of the ported-artifact drift class, and fixing it here fragments one finding across two trackers. It is one clause away from the line you are editing — this is the most likely accidental scope breach in the whole plan.",
        "Note the side effect: `tests/test_doc_link_contract.py:75` cites `.claude/skills/commit/SKILL.md:189` as literally '2. ```'. Inserting lines above 189 shifts that. It is a docstring comment, not an assertion, so nothing goes red — but leaving a wrong line number in a test's rationale is the citation rot this repo files bugs about. Re-check and correct the number if it moved.",
        "If the added sentence names a test path, it must be a path that exists: `tests/test_skill_references.py:86-108` asserts every `tests/test_*.py` a skill names resolves on disk. `tests/test_no_leaks.py` and `tests/test_leak_guard_scope.py` both qualify."
      ],
      "acceptance": [
        "`uv run pytest tests/test_skill_references.py -q` green — the sentence names only test paths that exist.",
        "`uv run pytest tests/test_doc_links.py -q` green — no relative link or bare `requests/` token was broken by the edit.",
        "`git diff .claude/skills/commit/SKILL.md` shows the added ordering sentence and, at most, a corrected line number — and does NOT show any change to the `gitleaks` clause at :78. Read the diff and confirm this explicitly.",
        "`node .claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs` and the other four commands at .github/workflows/ci.yml:70-78 still exit 0 (unchanged by this edit, but they are a CI step and cheap to run).",
        "`uv run pytest -m \"not gamedata\"` fully green; ruff check, ruff format --check and mypy clean."
      ],
      "commit_note": "One skill file, one paragraph. Hand to `/commit`. Expect the gate to note that a skill changed."
    },
    {
      "name": "Phase 6 — Status advance, report, and the request's terminal move",
      "goal": "Close the request the way requests/bugfix-requests/README.md:24-26 defines closure: the red repro is green, a regression test is left behind, nothing else regressed — and the record says so.",
      "steps": [
        "Write `requests/bugfix-requests/leak-guard-blind-to-untracked-files/IMPLEMENTATION_REPORT.md` per the layout at requests/bugfix-requests/README.md:30-39. State which phases landed, which were dropped and why, and how the gated decisions were disposed. Same hard rail as Phase 0: it is a tracked Markdown file scanned by the guard it describes, so it cannot quote a banned string — describe, do not paste.",
        "Set the artifact status blockquotes to the terminal stage. The grammar is `intake → diagnosed → planned → fixed` (requests/bugfix-requests/README.md:45), and the blockquote shape is `> **Status:** <stage> · created <YYYY-MM-DD> · <open|decided> · next: <stage>` (:43).",
        "Update the Index row at requests/bugfix-requests/README.md:52 — Stage cell to `fixed` — matching the row by its `[leak-guard-blind-to-untracked-files]` link, per `.claude/skills/commit/SKILL.md:128-130`.",
        "Move the directory into `requests/bugfix-requests/_done/` and repoint the Index link, per the same table row at .claude/skills/commit/SKILL.md:129. Note the consequence: `tests/test_doc_links.py`'s `markdown_files()` at :159-171 excludes `_done/`, so the moved bodies leave the link scan — but every INBOUND link from a live document to the old path breaks and WILL go red. Grep for the old path before moving.",
        "Check the two live references in requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md — risk 15 at :678 ('The leak guard is blind to unstaged files … Run the guard *after* staging; file the structural fix as a follow-up') and follow-up 4 at :544 (which files this very bug). Both are now obsolete advice in a live plan. Whether to edit another request's plan is an open question for the user; at minimum, surface it rather than leaving a live document instructing agents to work around a fixed defect.",
        "Re-run the whole gate one final time on a clean tree, then hand off."
      ],
      "acceptance": [
        "`uv run pytest -m \"not gamedata\"` fully green — this is the CI selection at .github/workflows/ci.yml:57 verbatim.",
        "All five node skill guards at .github/workflows/ci.yml:70-78 exit 0.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean.",
        "`uv run pytest tests/test_doc_links.py -q` green AFTER the `_done/` move — no inbound link to the old path survives.",
        "The Index row at requests/bugfix-requests/README.md reads `fixed`, its link points into `_done/`, and the artifacts' own status blockquotes agree with it. `.claude/skills/commit/SKILL.md:140-145` forbids marking ahead and forbids silently marking down.",
        "`git status --porcelain --untracked-files=all` is empty at the end — no scratch left in the tree, which is now a correctness property rather than a tidiness one.",
        "The bugfix contract is satisfiable in one sentence a reviewer can check: `tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard` was red at HEAD~n and is green now, and nine scope tests remain as the regression guard."
      ],
      "commit_note": "Final commit of the branch. Hand to `/commit` — it will run the full `/update-docs` sweep and own the status/Index bookkeeping. Then STOP: opening the PR, merging it, and any push to `main` stay the user's. Never `--amend`, never force-push, never `--no-verify`."
    },
    {
      "name": "Phase 7 — The fenced-code exemption (GATED — may be dropped entirely)",
      "goal": "Settle, explicitly rather than by drift, whether the leak guard gains the fenced-code exemption its sibling `tests/test_doc_links.py` got on 2026-08-17. The RCA raises this as Hardening and recommends settling it, not assuming it.",
      "steps": [
        "Do not start this phase until the user has disposed the decision. The RCA states both sides: two Markdown-scanning guards in one repo with opposite policies is a decision worth making once, BUT a fence exemption in a LEAK guard is a way to smuggle a credential past it, which is not true of a link checker. The planner's recommendation is NO — the inability of this request's own documents to quote the string they are about is a cost worth paying, and the repo has already paid it three times (BUGFIX_REQUEST.md:19-24, ROOT_CAUSE_ANALYSIS.md:5-9, and every acceptance note in this plan).",
        "If disposed NO: the phase is a two-line comment near tests/test_no_leaks.py:16 recording that the absence of a fence exemption is deliberate and why, so the next agent does not add one as an obvious convenience. No behaviour change, no new test.",
        "If disposed YES: reuse `strip_fences()` from tests/test_doc_links.py:55-92 rather than writing a second fence parser — that function already handles the blockquoted opener, the list-item opener (`FENCE` at :30), the CommonMark same-marker-and-length closing rule (:77-83), and the fail-toward-CHECKING behaviour on an unterminated fence (:86-92). Each of those was learned the hard way; a fresh implementation will re-lose them.",
        "If disposed YES: scope the exemption as narrowly as the value requires — fenced content under `requests/**` only, never under `gm/`, never `.env.example`, never a `.py`/`.yml`/`.json` file. Add a test asserting the exemption does NOT apply outside that scope, or the narrowing is unenforced prose.",
        "If disposed YES: extend `test_patterns_still_catch_real_leaks` (tests/test_no_leaks.py:51-78) with a case proving a banned string OUTSIDE a fence in an exempt-scope file is still caught. An exemption with no negative test is how a guard quietly stops guarding."
      ],
      "acceptance": [
        "If dropped: the decision and its rationale are recorded in the IMPLEMENTATION_REPORT, and no code changed. Dropping is a valid, complete outcome for this phase.",
        "If NO: `git diff tests/test_no_leaks.py` shows only a comment; `uv run pytest tests/test_no_leaks.py tests/test_leak_guard_scope.py -q` green with unchanged counts.",
        "If YES: `uv run pytest tests/test_no_leaks.py tests/test_doc_link_contract.py tests/test_leak_guard_scope.py -q` green, with new tests covering (a) a banned string inside a fence in an in-scope file passing, (b) the same string outside the fence failing, (c) the same string inside a fence in an OUT-of-scope file still failing.",
        "If YES: `strip_fences` has exactly one implementation in the repo — grep proves no second fence parser was written.",
        "`uv run pytest -m \"not gamedata\"` fully green; ruff check, ruff format --check and mypy clean."
      ],
      "commit_note": "Sequenced LAST precisely so it can be dropped at zero cost to everything above it. Hand to `/commit` only if it produced a change."
    }
  ],
  "testing": "THE ACCEPTANCE CONTRACT for this track (requests/bugfix-requests/README.md:24-26) is: the red reproduction goes green, a regression test is left behind, and nothing else regresses. All three are checkable by command here.\n\nTHE RED REPRO, and its exact selector:\n`uv run pytest tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard -q`\nRed today (confirmed by running it 2026-08-17: `.F.....`, failing at tests/test_leak_guard_scope.py:72). Green from Phase 1 onward. That single selector is the phase-1 gate.\n\nTHE REGRESSION TEST is already committed and does not need inventing — `tests/test_leak_guard_scope.py` landed in edc7aea, contrary to the RCA's 'Not yet committed' line. It is the harness the plan adds to. Its seven tests split into one that fails today and six that are green and must STAY green:\n- `test_the_probe_string_is_one_the_guard_actually_bans` (:54-59) — the anti-vacuity guard. If `PATTERNS` drifts so the probe no longer matches, every scope assertion below would pass while testing nothing. This is the test that makes the other six meaningful.\n- `test_a_gitignored_file_stays_out_of_scope` (:78-91) — the widening must respect `.gitignore`.\n- `test_no_ignored_directory_leaks_into_the_candidate_set` (:94-102), parametrized over `.venv`, `__pycache__`, `node_modules`, `var` — four separate assertions that the fix did not buy visibility by scanning everything.\nPhases 2 and 4 add to this module: a non-ASCII-filename enumeration test, an unreadable-path tolerance test, and (if kept) a `var/`-snapshot counterweight for the game-data scan.\n\nPER-PHASE SELECTORS:\n- Phase 0: `uv run pytest tests/test_leak_guard_scope.py -q` (expect `.F.....`), then `uv run pytest -m \"not gamedata\" -q` for the baseline count.\n- Phase 1: `uv run pytest tests/test_leak_guard_scope.py tests/test_no_leaks.py -q` → 10 passed.\n- Phase 2: same selector → 12 passed.\n- Phase 3: add `uv run pytest tests/test_agent_contract.py -q` (the memory-entry label guard at :84-95 must accept the rewritten entry).\n- Phase 4: `uv run pytest tests/test_no_leaks.py::test_game_data_is_not_tracked -q` plus the new counterweight.\n- Phase 5: `uv run pytest tests/test_skill_references.py tests/test_doc_links.py -q` — the first asserts every `tests/test_*.py` a skill names exists (:86-108), the second that no link broke.\n- Phase 6: `uv run pytest -m \"not gamedata\"` plus `uv run pytest tests/test_doc_links.py -q` re-run AFTER the `_done/` move.\n\nTHE FULL LOCAL GATE at the end of every phase, mirroring .github/workflows/ci.yml exactly:\n  uv run ruff check .            (ci.yml:46)\n  uv run ruff format --check .   (ci.yml:49 — easy to forget, and it fails CI on formatting alone)\n  uv run mypy                    (ci.yml:52 — strict over src AND tests, pyproject.toml:91-95)\n  uv run pytest -m \"not gamedata\"  (ci.yml:57)\nand, for any phase touching `.claude/skills/`, the five node commands at ci.yml:70-78.\n\nPROVING EACH NEW TEST CAN FAIL. Every regression test this plan adds must be seen red before it is trusted: revert the `-z` flag and watch the non-ASCII test fail; narrow the `except` back to `UnicodeDecodeError` and watch the tolerance test fail; drop `--exclude-standard` and watch the `var/` counterweight fail. This repo has a filed history of a guard that was red or vacuous from the day it landed and nothing noticed (requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/, and the comment at ci.yml:66-69 that exists because of it) — an unseen-red assertion is that failure repeating.\n\nTHE NEGATIVE CONTROL that proves the whole chain, not just the seam. The regression test asserts a path is IN the candidate set; it does not prove a leak in that path produces a failing assertion. Once per build, by hand: write an untracked file at the repo root containing a banned shape assembled at runtime the way tests/test_leak_guard_scope.py:35 assembles `LEAK`, run `uv run pytest tests/test_no_leaks.py -q`, confirm it goes RED naming that file, delete it, confirm green. Never write the banned string as a literal into any file that will be committed.\n\nREGRESSION SAFETY BEYOND THE GUARD ITSELF. `tests/test_repo_structure.py` (the `!gm/**` carve-out at :70-91), `tests/test_agent_contract.py` (the rulebook invariants at :53-73 and the `tests/` deny set at :76-81), `tests/test_doc_links.py` and `tests/test_doc_link_contract.py` are all in the offline selection, so every phase re-runs them automatically. CI re-runs the identical selection on the PR. The change touches no parser fixture, so `tests/test_parse_real_save.py` and the byte-accounting suite are unaffected — but they are in the offline run and their staying green is part of 'nothing else regresses'.\n\nWHAT IS NOT TESTED, STATED PLAINLY. Nothing here proves a leak cannot reach history — it proves the guard SEES the file. An author who never runs the suite is still unprotected, because there are no git hooks (RCA, confirmed) and CI does not run on a feature-branch push (ci.yml:3-6). Phase 5's `/commit` ordering note narrows that gap by instruction, not by mechanism. Saying so is the honest scope of the fix.",
  "risks": [
    "THE IMPLEMENTER'S OWN SCRATCH TURNS THE SUITE RED — the most likely surprise in the whole build. From the moment Phase 1 lands, `uv run pytest` scans every unignored file in the tree, including drafts, notes and panel output the implementer just wrote. A machine path in your own working file now fails the build. Mitigation: before Phase 1, move all working files into `var/` (gitignored, .gitignore:18) or the session scratchpad outside the repo. Do not respond by adding an entry to `EXEMPT_PREFIXES` (tests/test_no_leaks.py:18, currently empty) — that re-creates the exact blind spot being removed.",
    "THIS REQUEST'S OWN `reviews/` TRAIL FILES MAY CONTAIN THE LEAK. The RCA records that panel agents wrote 27 absolute machine paths into untracked trail files on 2026-08-17, and `.claude/skills/create-implementation-plan/SKILL.md:130-135` writes exactly such files under this work-dir. They are invisible today and in scope the moment Phase 1 lands. Scrub them by importing `PATTERNS` and scanning by hand BEFORE the phase-1 green run, or the fix's own commit is what discovers the leak.",
    "ACCIDENTALLY FIXING THE `gitleaks` CLAIM IN PHASE 5. The false claim sits at `.claude/skills/commit/SKILL.md:78`, one clause away from the sentence being edited, and it is obviously wrong — which is why it will get 'helpfully' corrected. The RCA's 'What this does not close' assigns it to requests/bugfix-requests/port-residue-sweep/ as a fourth instance of a drift class being tracked together. Read the Phase 5 diff and confirm that clause is untouched.",
    "THE DELETED-BUT-TRACKED CRASH. `--cached` lists index entries whose working-tree file may be gone; tests/test_no_leaks.py:85-88 catches only `UnicodeDecodeError`, so `read_text` would raise `FileNotFoundError` and the guard ERRORS instead of reporting. Pre-existing rather than introduced (plain `git ls-files` has the same property), but the widened scope makes the guard run in dirtier trees far more often. Phase 2 closes it; if Phase 2 is dropped, this stays a live way for the guard to break.",
    "QUOTED PATHS SILENTLY MISSING. `core.quotepath` is unset on this machine, i.e. the default TRUE is in force (measured), so git C-quotes paths with non-ASCII or special characters. Under the old scope such a file had to be deliberately staged; under the new one, any file an agent writes qualifies — a `reviews/` note with an em-dash in its name arrives as a quoted literal that does not resolve. The failure is a MISS or a crash, both silent-ish. `-z` in Phase 2 removes the class entirely; `-c core.quotePath=false` is the weaker alternative because it does not handle a newline in a filename.",
    "OVER-WIDENING UNDER PRESSURE. The obvious way to make the guard 'work everywhere' is to drop `--exclude-standard` or add `--ignored`. That pulls in `.venv/`, `__pycache__/`, `node_modules/`, every `var/` snapshot, and `.env` — a file whose entire job is holding machine-specific values (.gitignore:4-6). The result is a guard that is permanently red, gets switched off, and leaves the repo with zero leak protection. tests/test_leak_guard_scope.py:78-102 exists to make this fail loudly; do not weaken those tests to make a widening pass.",
    "PHASE 4's VALUE IS SMALLER THAN THE RCA IMPLIES. Every banned name and suffix at tests/test_no_leaks.py:106-107 is already covered by .gitignore:25-31, so `--exclude-standard` filters them and the widening surfaces nothing today. Its real value is converting a .gitignore assumption into a checked property. Build it knowing that, or drop it — but do not describe it in the report as closing a live hole.",
    "THE `_done/` MOVE BREAKS INBOUND LINKS. tests/test_doc_links.py:159-171 excludes `_done/` from the scan, so the moved bodies stop being checked — but any LIVE document still linking to the old path goes red, including the Index row itself. Grep for the old path before moving; `.claude/skills/commit/SKILL.md:129` requires the Index link to be repointed in the same commit.",
    "LINE-NUMBER ROT IN CITATIONS. tests/test_doc_link_contract.py:75 cites `.claude/skills/commit/SKILL.md:189` as literally '2. ```'. Inserting lines above 189 in Phase 5 shifts it. It is a docstring, so nothing goes red — which is precisely why it will be missed. This repo files bugs about citation rot; do not add one while fixing another.",
    "THE FIX CANNOT BE DELEGATED TO THE BUILD SUBAGENT. `tests/` is in the data-engineer's deny set, asserted by tests/test_agent_contract.py:76-81 — an agent that can edit the tests that catch it is the stated core failure mode. Every phase here edits `tests/`. The implementer does this directly; any review subagent gets read-only git.",
    "THE RCA IS ALREADY STALE IN ONE PLACE. It says the reproduction is 'Not yet committed'; it landed in edc7aea and `git ls-files tests/test_leak_guard_scope.py` confirms it is tracked. Its counts (140/141 paths) are also from a smaller tree — re-measured at 142 on 2026-08-17. Trust the RCA's verdict and cause; re-measure its numbers, which is what Phase 0 exists for.",
    "A GREEN SUITE STILL DOES NOT MEAN NO LEAK REACHED HISTORY. There are no git hooks, and .github/workflows/ci.yml:3-6 triggers only on `pull_request` and push to `main` — so a commit can be pushed to a feature branch with nothing having run. This fix moves first detection from `git add` to 'any local test run'. It does not make detection mandatory. Do not let the report claim otherwise."
  ],
  "files_to_touch": [
    {
      "path": "tests/test_no_leaks.py",
      "change": "THE FIX. Phase 1: argv at :33 becomes `[\"git\", \"ls-files\", \"--cached\", \"--others\", \"--exclude-standard\"]`, plus a why-comment and a rewritten module docstring (:1-5) that no longer says 'tracked'. Phase 2: add `-z`, split on NUL, widen the `except` at :87 from `UnicodeDecodeError` to also swallow `OSError`. Phase 3: rename `tracked_text_files` (:31). Phase 4 (optional): route `test_game_data_is_not_tracked`'s enumeration (:99-105) through the same helper. Do NOT touch `PATTERNS` (:24-28), `EXEMPT` (:16), `EXEMPT_PREFIXES` (:18) or the `keep` set (:39)."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "change": "Phase 1: NOT EDITED AT ALL — the repro must go green by the code changing. Phase 2: add two regression tests (non-ASCII filename is enumerated; an unreadable candidate does not crash the guard), reusing the `untracked_file` context manager at :39-51. Phase 3: update the three `guard.tracked_text_files()` call sites at :71, :88, :99 for the rename — attribute name only, assertion text byte-identical. Phase 4 (optional): the `var/`-snapshot counterweight."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "change": "Phase 3: correct the `measured` entry at :78-85. It states the guard cannot see a just-created file and instructs agents to hand-scan around it — false after Phase 1, and a standing instruction to work around a working check. Keep a valid epistemic label in backticks or tests/test_agent_contract.py:84-95 goes red. Its presence in a staged diff forces the full /update-docs sweep (.claude/skills/commit/SKILL.md:96-99)."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "change": "Phase 5 ONLY: one or two sentences in Step 2 (:49-79) noting that the widened guard now sees unstaged files, so run `uv run pytest tests/test_no_leaks.py -q` at the survey/stage step. HARD NON-GOAL: leave the false `gitleaks` clause at :78 exactly as it is — it belongs to requests/bugfix-requests/port-residue-sweep/."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/reviews/enumeration-measurement.md",
      "change": "NEW, Phase 0. The measured baseline: both enumeration counts, the set difference, 0 entries for each of the four junk roots, `.env` absent / `.env.example` present, elapsed ms, `core.quotepath`. Counts and property names only — never an enumerated path, because the file becomes tracked and is scanned by the guard it describes."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/IMPLEMENTATION_REPORT.md",
      "change": "NEW, Phase 6. Per the layout at requests/bugfix-requests/README.md:30-39. Records which phases landed, which were dropped, and how the gated decisions (the fence exemption; whether Phase 4 was kept) were disposed. Describes banned strings, never quotes them."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md",
      "change": "Phase 6, status blockquote only (:1) — advance to the terminal disposition. The body is decided and is not re-opened."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/BUGFIX_REQUEST.md",
      "change": "Phase 6, status blockquote only (:1)."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "Phase 6: Index row at :52, Stage cell → `fixed`, and the `[leak-guard-blind-to-untracked-files]` link repointed into `_done/` when the directory moves (.claude/skills/commit/SKILL.md:128-130). Match the row by its link, not by position."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md",
      "change": "NEW — this plan itself, written by stage 3 before any of the above. Opens at `planned · decided · next: implement`."
    },
    {
      "path": ".github/workflows/ci.yml",
      "change": "Phase 3, OPTIONAL and comment-only. The note at :22-24 explaining that `fetch-depth: 1` exists because the guard needs a real repo stays TRUE under the new form. Tighten it to mention untracked files if useful; never delete it — it is the record of why the checkout is shaped that way."
    },
    {
      "path": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md",
      "change": "Phase 6, FLAG ONLY — do not edit without the user's say-so. Risk 15 at :678 tells agents to 'Run the guard *after* staging' and follow-up 4 at :544 files this very bug; both are obsolete once this lands. Editing another live plan is an open question, but leaving a live document teaching a workaround for a fixed defect is the drift class this repo tracks."
    }
  ],
  "code_references": [
    {
      "ref": "tests/test_no_leaks.py:32-38",
      "claim": "`tracked_text_files()` shells out to `[\"git\", \"ls-files\"]` with `cwd=REPO_ROOT`, `capture_output=True`, `text=True`, `check=True`. The argv literal `[\"git\", \"ls-files\"],` is on line 33 — this is the single line the fix changes."
    },
    {
      "ref": "tests/test_no_leaks.py:1-5",
      "claim": "Module docstring reads 'The repo is PUBLIC (ADR 0006). Nothing machine-specific may be tracked.' The RCA's third argument is that this narrow self-description was the guard's only defence of its own scope; Phase 1 rewrites it."
    },
    {
      "ref": "tests/test_no_leaks.py:16",
      "claim": "`EXEMPT = {\"tests/test_no_leaks.py\"}` — exactly one entry, which is why no other file in the repo may contain a literal banned string, including every artifact of this request."
    },
    {
      "ref": "tests/test_no_leaks.py:18",
      "claim": "`EXEMPT_PREFIXES: tuple[str, ...] = ()` — currently EMPTY. The intake wondered whether it would 'need rethinking under any wider scan'; it does not, because there is nothing in it. The risk is the opposite: adding one to quiet new noise."
    },
    {
      "ref": "tests/test_no_leaks.py:24-28",
      "claim": "`PATTERNS` — three compiled regexes (windows drive path with a load-bearing lookbehind, unix home path, email address). Untouched by this fix: the RCA establishes the failure is scope, not patterns."
    },
    {
      "ref": "tests/test_no_leaks.py:39",
      "claim": "The `keep` suffix set — `.md .py .toml .yml .yaml .json .sql .example .txt` — is what the widened candidate list is filtered through, so a stray binary or lockfile never reaches `read_text`."
    },
    {
      "ref": "tests/test_no_leaks.py:85-88",
      "claim": "The read at :86 is wrapped in a `try` that catches ONLY `UnicodeDecodeError`. A `--cached` path deleted from the working tree would raise `FileNotFoundError` and error the guard out; Phase 2 widens this to `OSError`."
    },
    {
      "ref": "tests/test_no_leaks.py:97-116",
      "claim": "`test_game_data_is_not_tracked` repeats `[\"git\", \"ls-files\"]` at :99-105 — the second blind enumeration the RCA says a fix touching only `tracked_text_files()` leaves open. `banned_names` at :106, `banned_suffixes` at :107."
    },
    {
      "ref": "tests/test_no_leaks.py:51-78",
      "claim": "`test_patterns_still_catch_real_leaks` — six must-catch samples and five must-ignore samples. It is the check that a widening was not made to pass by loosening a pattern; it must stay green untouched through every phase."
    },
    {
      "ref": "tests/test_leak_guard_scope.py",
      "claim": "The committed red reproduction. CORRECTION TO THE RCA: it says 'Not yet committed', but `git ls-files tests/test_leak_guard_scope.py` returns it and `git log` shows it landed in edc7aea ('Diagnose the leak guard's blind spot: it enumerates the index'). Verified by running it 2026-08-17: `.F.....`."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:62-75",
      "claim": "`test_an_untracked_file_is_visible_to_the_leak_guard` — THE red test. Asserts at :72 that a probe written into the repo root is in `guard.tracked_text_files()`. This is the selector that must go green in Phase 1."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:39-51",
      "claim": "`untracked_file` — a context manager that writes a real file into the repo (a `tmp_path` fixture cannot serve, since the guard enumerates the repository) and unlinks it in a `finally`. Phase 2's new tests reuse it rather than writing a second one."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:35",
      "claim": "`LEAK` is assembled at runtime from `chr(92)` and string concatenation so this repo never holds a literal banned string outside the exempt file. Any new test the plan adds follows the same construction rule."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:78-102",
      "claim": "The counterweights that must stay green: `test_a_gitignored_file_stays_out_of_scope` (:78-91) and the `.venv`/`__pycache__`/`node_modules`/`var` parametrization (:94-102). They are the regression guard against over-widening."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:54-59",
      "claim": "`test_the_probe_string_is_one_the_guard_actually_bans` — the anti-vacuity guard. Without it, a drifted `PATTERNS` would let every scope assertion pass while testing nothing."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:71,88,99",
      "claim": "The three `guard.tracked_text_files()` call sites that Phase 3's rename must update — attribute name only; every assertion message stays byte-identical."
    },
    {
      "ref": ".github/workflows/ci.yml:22-24",
      "claim": "Comment on `actions/checkout` recording that the guard 'shells out to `git ls-files`; it needs the repo, not a detached blob export.' Still true of the proposed form, so `fetch-depth: 1` needs no change."
    },
    {
      "ref": ".github/workflows/ci.yml:46,49,52,57",
      "claim": "The four gate commands verbatim: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -m \"not gamedata\"`. The per-phase local gate is these four; `ruff format --check` is the one most often forgotten locally."
    },
    {
      "ref": ".github/workflows/ci.yml:70-78",
      "claim": "The `Skill guards (node)` step runs five explicit node commands under `set -euo pipefail`. Any phase touching `.claude/skills/` re-runs them locally; the comment at :66-69 explains they exist because a guard was red from the day it landed and nothing noticed."
    },
    {
      "ref": ".github/workflows/ci.yml:3-6",
      "claim": "The workflow triggers on `pull_request` and on push to `main` only — so a feature-branch push runs nothing. This bounds what the fix can claim: it moves first detection to 'any local test run', not to 'always'."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:77-79",
      "claim": "The paragraph carrying both the sentence Phase 5 amends ('catching it before it enters history is the difference between an edit and a history rewrite') and the false `gitleaks` promise that must be left alone."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:96-99",
      "claim": "`.claude/agents/data-engineer-memory.md` appearing in a staged diff FORCES the full `/update-docs` sweep — 'the trigger is the file's presence, not a judgment'. Phase 3's memory correction therefore makes that phase's commit gate the slow one."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:128-130",
      "claim": "The status table: a new artifact advances the blockquote and the Index Stage cell; reaching the terminal stage also moves the directory into `_done/` with the Index link repointed. This is Phase 6's checklist."
    },
    {
      "ref": ".claude/agents/data-engineer-memory.md:78-85",
      "claim": "A `measured` entry dated 2026-08-16 stating the leak guard cannot see a just-created file and telling agents to import `PATTERNS` and scan by hand. Phase 1 makes it false; it already carries one parenthetical correction from 2026-08-16 for teaching a workaround around a working check."
    },
    {
      "ref": "tests/test_agent_contract.py:76-81",
      "claim": "`test_deny_set_still_protects_the_guards` asserts `tests/` is in the data-engineer subagent's deny set — 'An agent that can edit the tests that catch it is the core failure mode.' This fix lives entirely in `tests/`, so it cannot be delegated to that subagent."
    },
    {
      "ref": "tests/test_agent_contract.py:84-95",
      "claim": "`test_memory_entries_carry_an_epistemic_label` requires every dated line in the memory file to carry one of {measured, verified, inferred, assumed, unconfirmed} in backticks. Phase 3's rewrite must keep one."
    },
    {
      "ref": "tests/test_doc_links.py:159-171",
      "claim": "`markdown_files()` uses `REPO_ROOT.rglob(\"*.md\")` and skips `.git`, `var` and `_done` — so it already sees untracked files, which is the asymmetry between the two guards that this fix removes. It also means the `_done/` move in Phase 6 drops the moved bodies from the link scan while breaking any inbound link to the old path."
    },
    {
      "ref": "tests/test_doc_links.py:55-92",
      "claim": "`strip_fences()` — handles blockquoted and list-item fence openers, the CommonMark same-marker-and-length closing rule (:77-83), and fails toward CHECKING on an unterminated fence (:86-92). If the gated fence-exemption decision comes back YES, Phase 7 reuses this rather than writing a second parser."
    },
    {
      "ref": "tests/test_doc_links.py:40",
      "claim": "`LINE_SUFFIX` spells its dash class as `–` with an explicit note that the escape exists so the source carries no ambiguous glyph (ruff RUF001/RUF003). Phase 2's non-ASCII filename test must use the same escape form."
    },
    {
      "ref": "tests/test_doc_link_contract.py:75",
      "claim": "A docstring citing `.claude/skills/commit/SKILL.md:189` as literally '2. ```'. It is a comment, not an assertion, so a Phase 5 insertion above line 189 rots the citation silently rather than turning the suite red."
    },
    {
      "ref": "tests/test_skill_references.py:86-108",
      "claim": "`test_every_repo_path_a_skill_names_exists` — every `tests/test_*.py` or `docs/*.md` a skill names must resolve on disk. Constrains what Phase 5's added sentence may cite."
    },
    {
      "ref": ".gitignore:4-6",
      "claim": "`.env` and `.env.*` ignored, `!.env.example` restored. This is why the widened enumeration excludes `.env` (a file whose whole job is machine-specific values) while still scanning `.env.example` — measured on this tree 2026-08-17, both hold."
    },
    {
      "ref": ".gitignore:18",
      "claim": "`var/` — the gitignored working root. It is where the implementer's scratch must live once Phase 1 lands, and it is why `--exclude-standard` keeps snapshots out of the candidate set."
    },
    {
      "ref": ".gitignore:25-31",
      "claim": "The game-data block: `*.lg/`, `saved_games/`, `players.csv`, `names.xml`, `world_default.xml`, `schools.xml`, `*.dat`. Every banned name and suffix in `test_game_data_is_not_tracked` is already covered here, which is what makes Phase 4 a check-of-an-assumption rather than a closed hole."
    },
    {
      "ref": "pyproject.toml:91-95",
      "claim": "`[tool.mypy]` strict with `files = [\"src\", \"tests\"]` — any helper added to a test module needs full annotations or `uv run mypy` fails."
    },
    {
      "ref": "pyproject.toml:98-108",
      "claim": "`[tool.pytest.ini_options]`: `testpaths = [\"tests\"]`, `addopts = \"-q --strict-markers --strict-config\"`, and one marker `gamedata`. `--strict-markers` means inventing a second marker is a hard COLLECTION error, so no new marker is available to this fix."
    },
    {
      "ref": "requests/bugfix-requests/README.md:24-26",
      "claim": "The track's acceptance contract in one sentence: 'Done means the red reproduction goes green and a regression test is left behind.' This is what Phase 6 must be able to assert."
    },
    {
      "ref": "requests/bugfix-requests/README.md:45",
      "claim": "Status grammar `intake → diagnosed → planned → fixed`, and the blockquote shape at :43. Phase 6's bookkeeping follows these, not an invented form."
    },
    {
      "ref": "requests/bugfix-requests/README.md:52",
      "claim": "The Index row for this bug, currently at Stage `diagnosed`. Phase 6 advances it to `fixed` and repoints its link into `_done/`."
    },
    {
      "ref": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:678",
      "claim": "Risk 15: 'The leak guard is blind to unstaged files … Run the guard *after* staging; file the structural fix as a follow-up.' A live document teaching a workaround this fix removes."
    },
    {
      "ref": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:544",
      "claim": "Follow-up item 4 files 'the `git ls-files` staging gap in `test_no_leaks.py`' — this request's own origin, recorded in another live plan."
    },
    {
      "ref": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:411",
      "claim": "Records that `test_no_leaks.py` catches `players.csv` by FILENAME ONLY, so a renamed derived copy passes — an owned, separate gap. Phase 4 must not absorb it."
    },
    {
      "ref": "docs/decisions/0006-public-repo-local-data.md:30",
      "claim": "'`tests/test_no_leaks.py` fails the build on absolute paths, home directories…' — the ADR this guard enforces. Still accurate after the widening (it now understates rather than overstates), so no ADR edit is required; confirm rather than assume."
    },
    {
      "ref": "CLAUDE.md:60",
      "claim": "'Everything resolves from `.env`; `tests/test_no_leaks.py` fails the build.' Names this test as ADR 0006's enforcement mechanism — the RCA's second reason the guard's scope is not a private implementation detail. Remains true unchanged."
    }
  ],
  "open_questions": [
    "THE GATED HARDENING DECISION (Phase 7): does `tests/test_no_leaks.py` gain a fenced-code exemption, matching what `tests/test_doc_links.py` got on 2026-08-17? The RCA raises it and explicitly declines to settle it. The planner's recommendation is NO — a fence exemption in a LEAK guard is a way to smuggle a credential past it, which is not true of a link checker, and the cost (a report about a leak cannot quote the leak) has already been paid three times without harm. If the user says YES, Phase 7 must reuse `strip_fences()` from tests/test_doc_links.py:55-92, scope the exemption to `requests/**` only, and add a negative test. Needs disposal before Phase 7 starts; nothing else in the plan depends on it.",
    "IS PHASE 4 WORTH ITS COMMIT? Measured: every banned name and suffix at tests/test_no_leaks.py:106-107 is already covered by .gitignore:25-31, so widening `test_game_data_is_not_tracked` surfaces nothing today. Its value is converting a .gitignore assumption into a checked property against future removal or shadowing. Real, but smaller than the RCA's 'Root' framing implies. Keep or drop — either is a complete outcome, but the report must say which and why.",
    "SHOULD THE RENAME (Phase 3) HAPPEN AT ALL? Renaming `tracked_text_files` touches the committed repro's three call sites, which some would rather leave pristine. Against that: leaving a function called `tracked_*` that scans untracked files re-arms the exact 'the guard's own self-description is the authority on its scope' argument the RCA had to defeat to call this a bug. Recommendation: rename, in its own commit, with assertions byte-identical.",
    "MAY THE PLAN EDIT ANOTHER REQUEST'S LIVE PLAN? requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:678 (risk 15) tells agents to run the guard after staging — obsolete once this lands, and first-sight is still live, not in `_done/`. Editing another track's decided artifact is normally out of bounds; leaving stale operational advice in a live plan is the drift class this repo files bugs about. Surface at Phase 6 and let the user choose.",
    "DOES THE `/commit` NOTE (Phase 5) GO FAR ENOUGH, OR SHOULD THE SKILL'S SCAN STEP ACTUALLY MOVE? The RCA's recommendation (d) is 'a one-line ordering note'. A stronger reading is that Step 2's scan should be relocated to Step 1 (Survey), before staging, since the guard can now see unstaged content. The stronger version edits more of a skill that carries its own rail against growing (:28-30). Recommendation: the sentence, not the restructure — but confirm.",
    "HOW SHOULD THE UNREADABLE-CANDIDATE TEST (Phase 2) BE WRITTEN WITHOUT MUTATING THE TREE? Deleting a real tracked file to prove the guard tolerates it is a working-tree mutation a test must not make. Options: factor the read into a small annotated helper and unit-test the helper against a non-existent path, or assert at the scan-body level with an injected candidate list. Either is fine; the choice affects how much of tests/test_no_leaks.py gets restructured, and a bigger restructure is a bigger revert.",
    "IS A SECRET SCANNER GOING TO BE FILED? The RCA is emphatic that nothing in this repo scans for credentials at all, and routes it to the feature track as out of scope here. Nothing in this plan opens it. Worth confirming that a FEATURE_REQUEST gets filed, or the finding evaporates with this request's closure."
  ]
}
~~~

## Proposal 3

~~~
{
  "planner": "domain-convention",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Consume it, do not re-open it: verdict is confirmed-bug, the cause is the `git ls-files` argv, the fix posture is tiered, and its 'Gated decision' block already disposes the four candidate directions to (a)+(d). Its measured table at :101-114 is the evidence base for Phase 2 and I re-measured every row of it."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/BUGFIX_REQUEST.md",
      "why": "Context only. Its 'Affected Area & Pointers' at :109-123 is the fastest reading order, and its Severity section at :72-96 records the three amplifiers (no gitleaks, no hooks, CI does not run on a feature-branch push) that set how much this fix actually buys."
    },
    {
      "path": "tests/test_no_leaks.py",
      "why": "The file being fixed. `tracked_text_files()` at :31-48 is the whole defect; `PATTERNS` at :24-28, `EXEMPT`/`EXEMPT_PREFIXES` at :16-18, the read loop at :81-94, and a SECOND independent `git ls-files` call inside `test_game_data_is_not_tracked` at :99-105."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "why": "The committed red repro (landed in edc7aea, not 'not yet committed' as the RCA says). Seven tests: one RED at :62-75, six counterweights. `untracked_file()` at :38-51 is the fixture every new regression test in Phase 3 reuses; `LEAK` at :35 is assembled at runtime so the file never contains a literal banned string."
    },
    {
      "path": "tests/test_doc_links.py",
      "why": "The sibling Markdown guard, and the repo's counter-example: `markdown_files()` at :159-171 enumerates with `Path.rglob(\"*.md\")` and therefore ALREADY sees untracked files. Read it to see why the two guards diverged, and because `strip_fences()` at :55-92 is the ready-made implementation the gated 'fence exemption' hardening would reuse if it is taken."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "why": "The build rulebook — and decisive here: its repo-level deny set at :147-158 forbids the data-engineer subagent from writing to `tests/`, `.github/` and `.claude/`, which is 100% of this fix's target paths. This work must be built on the MAIN THREAD. The one carve-out is `.claude/agents/data-engineer-memory.md` at :142."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "why": "The commit gate every phase ends at. Step 2 staging at :49-79 is where the RCA's direction (d) ordering note lands; :78 carries the false `gitleaks` promise; :96-99 makes the agent-memory file's presence in a staged diff a HARD trigger for the full /update-docs sweep; :128-130 governs the terminal `_done/` move; :229-237 pins that the PR stays the user's."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "The comment at :22-24 records that the `git ls-files` dependency on a real checkout is deliberate — the fix must keep it true. :57 is the `-m \"not gamedata\"` selection the repro runs under; :70-78 is the node skill-guards step that must also be run locally before handoff."
    },
    {
      "path": "pyproject.toml",
      "why": "mypy is `strict = true` over BOTH `src` and `tests` (:91-95), so every new test helper needs full annotations or the build is red. pytest config and the single `gamedata` marker at :98-108 — `--strict-markers` means inventing a second marker is a hard collection error."
    },
    {
      "path": ".gitignore",
      "why": "The file `--exclude-standard` actually reads. :4-6 is why `.env` is out of scope but `.env.example` is in; :18 is `var/`; :25-31 is why widening the game-data check buys nothing (every banned name/suffix is already ignored)."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The pipeline contract this track runs on. Status grammar at :45 (`intake -> diagnosed -> planned -> fixed`), the 'done means the red repro goes green and a regression test is left behind' definition at :25-26, and the Index row for this slug at :52 that Phase 5 advances."
    }
  ],
  "architecture_notes": "This change has NO data surface. It adds no source, no dataset, no `datasets/manifest.json` entry, no dbt model, no warehouse table, no parser field mapping. There is therefore no grain, no key, no coverage window, no update semantics and no pull cost to declare, and the plan must NOT carry a data-contracts section — `docs/data-access.md` is not touched and none of its epistemic labels are load-bearing here. My lens is pivoted, per mandate, to PROJECT-CONVENTION correctness.\n\nTHE TOPOLOGY BEING CHANGED. `tests/test_no_leaks.py` is, per `CLAUDE.md:60` and `docs/decisions/0006-public-repo-local-data.md:30`, the sole mechanism enforcing ADR 0006 in a public repo. It runs two independent enumerations, both shelling out to bare `git ls-files`:\n  1. `tracked_text_files()` at :31-48 — feeds `test_no_machine_paths_or_identifiers` at :81-94, filtering to a `keep` suffix set at :39 plus `.env.example`, minus `EXEMPT` (:16, exactly one entry: the guard's own source) and `EXEMPT_PREFIXES` (:18, currently the empty tuple, so the `startswith` filter at :43 is inert).\n  2. `test_game_data_is_not_tracked` at :97-116 — its own `git ls-files` at :99-105, checking banned names and `.dat`/`.lg` suffixes.\nBoth list the INDEX. Neither sees a file that exists but has not been staged.\n\nTHE REPO ALREADY CONTAINS THE OPPOSITE ANSWER. `tests/test_doc_links.py` `markdown_files()` at :159-171 enumerates with `REPO_ROOT.rglob(\"*.md\")` and a hand-rolled exclusion of `.git`, `var` and `_done`, so it has always seen untracked files. Two Markdown-scanning guards in one repo with opposite enumeration policies is exactly the drift the RCA's Hardening section flags. The fix should move the leak guard toward git's own ignore semantics (which are correct and maintained) rather than toward the rglob approach (whose hand-rolled exclusion list is why `.venv/` is only accidentally out of scope — measured: `.venv/` holds 1 `.md` file today, and would hold thousands under a different dependency set).\n\nWHAT THE FIX IS, MEASURED BY ME ON 2026-08-17. `git ls-files --cached --others --exclude-standard` run in the repo root returns 142 paths, byte-identical to `git ls-files` on a clean tree (`Compare-Object` diff = 0). Zero entries under `.venv/`, `__pycache__/`, `node_modules/` or `var/`. `.env` absent (gitignored). `.env.example` present (the `!.env.example` negation at `.gitignore:6` is honoured). Every row of the RCA's table at :101-114 reproduces.\n\nTWO MEASURED FACTS THE RCA DOES NOT CARRY, both from probe repos I built in the scratchpad rather than in this tree:\n  * `--directory` MUST NOT be passed. Without it, git lists nested untracked files individually (`reviews/a.md`, `reviews/deep/b.md`). With it, the whole tree collapses to a single `reviews/` entry and the nested file is never listed. Since all three real 2026-08-17 leaks lived in `requests/**/reviews/` — a directory git had never seen — this is the difference between fixing the bug and appearing to.\n  * `-z` MUST be passed. Default `git ls-files` output QUOTES a path containing a non-ASCII byte: `café.md` comes back as the literal 14-character string `\"caf\\303\\251.md\"`. `REPO_ROOT / rel` then names a file that does not exist, and `Path('\"caf\\\\303\\\\251.md\"').suffix` is `.md\"`, which is not in the `keep` set at :39 — so the path is dropped from the candidate list SILENTLY. That is the identical never-opened-the-bytes failure class as the bug under repair, reintroduced by the fix itself. `-z` disables quoting; split `stdout` on `\\0`.\n\nWHY THE SECOND ENUMERATION SHOULD NOT BE FOLDED IN. The RCA's \"Root\" tier notes `test_game_data_is_not_tracked` has \"the same blindness\". Measured with `git check-ignore -v`: `players.csv` -> `.gitignore:27`, `x/players.dat` -> `.gitignore:31 (*.dat)`, `names.xml` -> `.gitignore:28`, `roster.lg/x.txt` -> `.gitignore:25 (*.lg/)`. Every banned name and suffix that check hunts is already gitignored, so `--exclude-standard` would exclude all of them from `--others` and the widening would add approximately nothing. Its assertion is literally \"must never be TRACKED\", and the index is the correct set for that sentence. Leave its enumeration on `--cached`; give it the `-z` helper and a comment recording this measurement so the next reader does not \"complete\" the fix and think they gained coverage.\n\nTHE SUBAGENT SEAM. `.claude/agents/data-engineer.md:147-158` denies the write-capable subagent `tests/`, `.github/` and `.claude/` at repo level, with the stated rationale at :160-162 that \"an agent that can edit the guards that catch it and then report green is the worst failure mode available here\". Every target path of this fix is inside that deny set. The plan must instruct the implementer to build on the main thread and explicitly NOT spawn the data-engineer; if one is spawned anyway, its own rulebook requires it to stop and report rather than build. The sole exception is `.claude/agents/data-engineer-memory.md` (:142).\n\nBASELINE, MEASURED. `uv run pytest -m \"not gamedata\" -q` on `fix-leak-guard-untracked-blindness` at `edc7aea`: 125 collected, 124 passed, 1 failed — `tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard`, with the RCA's exact assertion message. The tree is clean (`git status --porcelain` empty). That single failure is the whole acceptance contract.",
  "phases": [
    {
      "name": "Phase 1 — Pre-flight: measure what the widened guard will newly see",
      "goal": "Know, before a line changes, whether the about-to-be-widened candidate set already contains a violation — so a red assertion in Phase 2 is unambiguous evidence about the fix rather than a mystery about the tree.",
      "steps": [
        "Re-establish the baseline: `uv run pytest -m \"not gamedata\" -q --tb=no`. Expect exactly one failure, `tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard` (measured 2026-08-17 at edc7aea: 124 passed, 1 failed, 125 collected). Any other failure means the tree is not the one this plan was written against — stop and say so.",
        "Confirm the tree is clean: `git status --porcelain` (read-only). Then enumerate exactly what widening adds: `git ls-files --others --exclude-standard`. On a clean tree this returns zero lines; every line it returns is a file the guard is about to start reading.",
        "Apply the guard's own patterns to that added set BY HAND — the same technique the RCA records as the only thing that caught all three real leaks. From the repo root: import `PATTERNS` from `tests/test_no_leaks.py` and run each pattern over each newly-visible path's lines. Record the hits verbatim in your working notes (describe them; do not paste a matched line into any tracked file — `tests/test_no_leaks.py:25` bans a drive path in tracked text and this repo is public).",
        "If there are hits: fix the CONTENT, not the guard. Rewrite absolute paths as repo-relative. Do NOT add anything to `EXEMPT` (:16) or `EXEMPT_PREFIXES` (:18). `requests/**/reviews/` in particular is where all three 2026-08-17 leaks lived; exempting it recreates the defect under a new name. The panel trail this very plan ships with (`requests/bugfix-requests/leak-guard-blind-to-untracked-files/reviews/`) is the highest-probability source of hits — panel output routinely cites absolute paths.",
        "Move any personal scratch out of the repo and into the session scratchpad directory. From Phase 2 onward, the cleanliness of the working tree becomes a test input: an untracked note with a drive path in it will turn the suite red, correctly.",
        "Read `.claude/agents/data-engineer.md:147-158` and confirm the plan's target paths (`tests/`, `.claude/skills/commit/SKILL.md`, `.github/workflows/ci.yml`) are inside the write-capable subagent's repo-level deny set. Build this on the main thread. Do not spawn the data-engineer for any phase of this plan."
      ],
      "acceptance": [
        "The baseline is recorded verbatim: 124 passed / 1 failed, and the single failure is `tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard`.",
        "The output of `git ls-files --others --exclude-standard` is captured, and every path in it has been scanned with the guard's own `PATTERNS` with zero remaining hits.",
        "Nothing was added to `EXEMPT` or `EXEMPT_PREFIXES`, and no `reviews/`-shaped exemption exists anywhere in the diff.",
        "`git status --porcelain` shows no stray scratch files inside the repo."
      ],
      "commit_note": "Usually nothing to commit. If content was scrubbed in step 4, land it alone through `/commit` before touching the guard — a scrub commit and a guard commit are different claims and should not be entangled. Message shape: \"Scrub absolute paths out of the panel trail\"."
    },
    {
      "name": "Phase 2 — Widen the enumeration; the red repro goes green",
      "goal": "Change `tracked_text_files()` so the guard sees tracked, staged AND untracked-but-not-ignored files, without letting a single ignored path into the candidate set — and without reintroducing the same silent-drop failure through git's output encoding.",
      "steps": [
        "In `tests/test_no_leaks.py`, extract a single module-level helper both enumerations use, e.g. `def git_paths(*args: str) -> list[str]`. It runs `[\"git\", \"ls-files\", \"-z\", *args]` with `cwd=REPO_ROOT, capture_output=True, text=True, check=True` (the existing call shape at :32-38) and returns `[p for p in out.stdout.split(\"\\0\") if p]`. mypy is strict over `tests/` (`pyproject.toml:91-95`), so annotate fully.",
        "`-z` is not optional and the comment must say why: measured 2026-08-17, default `git ls-files` output quotes a non-ASCII path — `café.md` returns as the literal string `\"caf\\303\\251.md\"`. That resolves to no file, and its `.suffix` is `.md\"`, which fails the `keep` membership test at :39, so the path is dropped from the candidate set with no error. That is the same never-opened-the-bytes failure as the bug being fixed.",
        "Point `tracked_text_files()` at `git_paths(\"--cached\", \"--others\", \"--exclude-standard\")`. Leave the `EXEMPT` / `EXEMPT_PREFIXES` / suffix filtering at :39-47 exactly as it is.",
        "Do NOT pass `--directory`, and leave a comment saying so. Measured in a scratch repo: without it git lists `reviews/a.md` and `reviews/deep/b.md` individually; with it the whole untracked tree collapses to a single `reviews/` entry and the nested file is never listed. All three real leaks were nested inside an untracked directory, so `--directory` would make the fix look green while fixing nothing.",
        "Harden the read loop at :83-88: skip a path that does not exist on disk. `--cached` still lists a tracked file that has been deleted from the working tree, and the loop catches only `UnicodeDecodeError`, so a `FileNotFoundError` would present as a broken suite rather than as a leak. Pre-existing, but this change makes it likelier to be hit.",
        "Leave `test_game_data_is_not_tracked` (:97-116) enumerating the INDEX ONLY — switch it to `git_paths(\"--cached\")` for the `-z` fix and nothing more. Comment the measurement: `git check-ignore -v` resolves `players.csv` to `.gitignore:27`, `x/players.dat` to `.gitignore:31`, `names.xml` to `.gitignore:28` and `roster.lg/x.txt` to `.gitignore:25`, so `--exclude-standard` would exclude every path that check hunts and the widening would buy nothing. Its assertion is literally \"must never be TRACKED\"; the index is the right set.",
        "Rewrite the module docstring at :1-5. It currently reads \"Nothing machine-specific may be **tracked**\" — the RCA identifies that exact sentence as the narrowest statement of intent in the repo and the only reason `works-as-intended` was arguable. State the scope the guard now has: tracked, staged, and untracked-but-not-ignored, with ignored paths deliberately out of scope because `.env` and `var/` hold machine-specific values by design.",
        "Run the gates: `uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`."
      ],
      "acceptance": [
        "`uv run pytest tests/test_leak_guard_scope.py -q` → 7 passed, 0 failed. The RED test at :62-75 is green and all six counterweights — the gitignored-file test at :78-91 and the four parametrized junk-dir cases at :94-102 — stay green.",
        "`uv run pytest -m \"not gamedata\" -q` → 125 passed, 0 failed (up from 124/1).",
        "`uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` are all clean.",
        "`git ls-files --cached --others --exclude-standard | Measure-Object` returns 142 on a clean tree, identical to `git ls-files` — the widening added coverage without changing the clean-tree candidate set.",
        "The diff contains no `--directory` flag, no new `EXEMPT` entry, and no new `EXEMPT_PREFIXES` entry.",
        "`test_game_data_is_not_tracked` still enumerates `--cached` only, and carries the comment explaining why widening it is a measured no-op."
      ],
      "commit_note": "\"Widen the leak guard to untracked-but-not-ignored files\". Body should carry the two measurements that are not obvious from the diff: why `--directory` is absent, and why `-z` is present. Land through `/commit` only — never `git commit` ad hoc, not even for a one-line argv change."
    },
    {
      "name": "Phase 3 — Pin the shapes the committed repro does not cover",
      "goal": "Leave behind regression tests for the actual bug shape. The committed repro writes its probe at the repo root; every real leak was nested inside an untracked directory. Those are different git behaviours, and only one of them is currently pinned.",
      "steps": [
        "Extend `untracked_file()` at `tests/test_leak_guard_scope.py:38-51` (or add a sibling contextmanager) so it can create and then remove a parent directory. It currently only `unlink`s the file, so a nested probe would leave an empty directory behind — which the next run's `assert not path.exists()` guard at :46 would not catch, but a reviewer would. Keep the `finally` cleanup discipline exactly as it is.",
        "Add `test_an_untracked_file_in_an_untracked_directory_is_visible` — write `LEAK` (the runtime-assembled string at :35) to a nested path such as `_leak_probe_dir/nested/probe.md` and assert it appears in `guard.tracked_text_files()`. This is the shape of all three 2026-08-17 leaks and it is what makes the absence of `--directory` load-bearing rather than incidental.",
        "Add a non-ASCII-name probe (a filename containing an accented character) and assert it appears in the candidate set. Without `-z` this fails; with it, it passes. This pins the encoding decision so a future simplification that drops `-z` goes red instead of going quiet.",
        "Add an assertion-level test, not just an enumeration-level one: with an untracked probe present, `guard.test_no_machine_paths_or_identifiers()` must raise `AssertionError`. Every existing scope test proves the file is ENUMERATED; none proves the guard actually fires on it. Use `pytest.raises(AssertionError)` inside the `untracked_file` contextmanager.",
        "Add a test that `guard.EXEMPT_PREFIXES` covers no `requests/` path. `EXEMPT_PREFIXES` is `()` today (:18) and `str.startswith(())` is always False, so the filter at :43 is inert — which makes it the obvious place for a future maintainer to silence a noisy `reviews/` artifact, recreating this exact defect. Pin it with a message that says so.",
        "Prove each new test is a real regression test: it must FAIL against the pre-Phase-2 enumeration. Do this in a scratchpad copy of the repo rather than by reverting in place — `.claude/agents/data-engineer-memory.md:99-104` records the working technique (copy `pyproject.toml`, `src/` and `tests/`, run the repo venv's `pytest.exe` from the copy, and expect `test_repo_structure.py` / `test_agent_contract.py` to fail there as noise, not signal).",
        "Re-run the four gates."
      ],
      "acceptance": [
        "Every new test is in `tests/test_leak_guard_scope.py` and assembles its banned string at runtime — grep the file for a literal drive-letter path and find none, so the module stays outside `EXEMPT`.",
        "Each new test demonstrably fails against the old `[\"git\", \"ls-files\"]` argv (evidenced from the scratchpad copy) and passes against the new one.",
        "`uv run pytest -m \"not gamedata\" -q` green, with the file count on `tests/test_leak_guard_scope.py` risen from 7 to at least 11.",
        "No probe file or probe directory survives a run: `git status --porcelain` is empty immediately after the suite, including after a deliberately interrupted run of the new nested test.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean."
      ],
      "commit_note": "\"Pin the nested-directory and non-ASCII shapes of the leak-guard scope\". This is the half of the bugfix contract that survives the fix — `requests/bugfix-requests/README.md:25-26` defines done as red-goes-green PLUS a regression test left behind. Land through `/commit`."
    },
    {
      "name": "Phase 4 — Make the workflow prose true about what the guard now sees",
      "goal": "Close the RCA's disposed direction (d) and repair every comment and doc sentence this fix falsifies, so nothing in the repo still describes the old scope.",
      "steps": [
        "`.claude/skills/commit/SKILL.md`, Step 2 (:71-79): add the ordering note. WORD IT CAREFULLY — with the widening landed, the guard already sees untracked files, so an instruction to \"stage first so the guard can see it\" is now both redundant and dangerous: it nudges an agent toward the `git add -A` habit that :51-52 exists to forbid. The correct note is to RUN the guard (`uv run pytest tests/test_no_leaks.py -q`) as a concrete step in place of the manual eyeball at :77-78, and to note that it now covers untracked files too, so it is worth running before staging as well as after.",
        "Do NOT touch the false `gitleaks` claim at `.claude/skills/commit/SKILL.md:78` — the RCA's 'What this does not close' section routes it to `requests/bugfix-requests/port-residue-sweep/` and explicitly warns that filing it here fragments one finding across three trackers. Record, for that sweep, a fact the RCA missed: a SECOND false gitleaks promise exists at `.claude/skills/update-docs/SKILL.md:25`, which lists `gitleaks` among the mechanical checks that \"moved to CI\". The RCA's correction says the claim occurs once; it occurs in two skills, in two different files. Whether to write that into the sweep's request body in this commit is an open question for the gate.",
        "`.github/workflows/ci.yml:22-24`: extend the comment by one clause. It currently justifies the checkout only against `git ls-files`; the guard now also depends on `--others` seeing the working tree and on `--exclude-standard` being able to read `.gitignore`. `actions/checkout@v7` with `fetch-depth: 1` provides both, so the step needs no change — but add the honest caveat that CI's tree is clean, so `--others` contributes nothing there and a green CI run is NOT evidence that the widening works. The local suite is where that is proven.",
        "`.claude/agents/data-engineer-memory.md`: append one new dated entry in the fixed format at :25-29 (`- **YYYY-MM-DD** · `label` · <claim> · evidence: <pointer> · tag: harness`), labelled `measured`, recording the new scope and the two non-obvious flags. Then annotate the now-stale entry at :78-85 in the established inline style already used at :82-84 — that entry currently teaches agents to hand-run `PATTERNS` because the guard is blind, which stops being true the moment Phase 2 lands. Do not delete it: :39-48 says append freely and never prune, and curation belongs to `/update-docs`.",
        "Budget for the consequence: `.claude/skills/commit/SKILL.md:96-99` makes this memory file appearing in a staged diff a HARD trigger for the full `/update-docs` sweep — not a judgment call. Expect the heavier gate on this phase's commit.",
        "Sweep the other five places the guard is described and correct only where the new scope makes them under-describe: `CLAUDE.md:60`, `docs/decisions/0006-public-repo-local-data.md:30`, `gm/README.md:153`, `.env.example:4`, `.claude/agents/data-engineer.md:121`. Most say \"fails the build\" or \"no machine-specific paths in tracked files\" and stay true; the last one is the likeliest to need a word.",
        "Re-run the four gates plus `uv run pytest tests/test_doc_links.py tests/test_skill_references.py -q` — `test_skill_references.py:86-108` resolves every `tests/test_*.py` a skill names, so any test module you cite in the commit skill must exist."
      ],
      "acceptance": [
        "`.claude/skills/commit/SKILL.md` Step 2 names `uv run pytest tests/test_no_leaks.py -q` as a concrete step, and contains no new instruction that could be read as \"stage everything so the guard can see it\".",
        "`git grep -n \"gitleaks\"` still returns exactly the two pre-existing occurrences (`.claude/skills/commit/SKILL.md:78`, `.claude/skills/update-docs/SKILL.md:25`) — this phase repaired neither, by design.",
        "`.github/workflows/ci.yml` still runs `pytest -m \"not gamedata\"` unchanged and its checkout comment now covers `--others` and `--exclude-standard`.",
        "`.claude/agents/data-engineer-memory.md` has exactly one new entry matching the format at :25-29 with a real epistemic label, and the entry at :78-85 carries a dated correction annotation rather than having been deleted or rewritten.",
        "`uv run pytest tests/test_doc_links.py tests/test_skill_references.py -q` green — no skill now names a test module that does not exist, and no relative link is broken.",
        "Full suite, ruff, ruff format and mypy all green."
      ],
      "commit_note": "\"Tell the commit gate and the docs what the leak guard now sees\". The agent-memory file in this diff forces the full `/update-docs` sweep at the gate — run it, and surface anything it flags rather than resolving it silently. Land through `/commit`."
    },
    {
      "name": "Phase 5 — Close out: full local gate, request status, hand off",
      "goal": "Prove nothing else regressed, write the implementation report, advance the bugfix track's status records to `fixed`, and stop at the point where the work becomes the user's.",
      "steps": [
        "Run everything CI runs, locally: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -m \"not gamedata\"`, and the node skill guards enumerated at `.github/workflows/ci.yml:70-78` (`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs`, `node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs`, and the three `merge_*` guards under `scope-feature` and `create-implementation-plan`). Two of those belong to the planning skills this very artifact came from, and CI added that step precisely because a guard nobody is forced to run was red for the life of a skill.",
        "Do a final honest scope check with the fixed guard itself: `uv run pytest tests/test_no_leaks.py -q` on a tree that still holds the untracked implementation report before it is staged. That run is the fix demonstrating its own value — it is the check that would have caught all three 2026-08-17 leaks.",
        "Write `requests/bugfix-requests/leak-guard-blind-to-untracked-files/IMPLEMENTATION_REPORT.md`. Open it with the status blockquote grammar from `requests/bugfix-requests/README.md:41-45`. Record the before/after suite counts (124 passed + 1 failed → 125 passed), the two measured decisions (`-z`, no `--directory`), and the decision NOT to widen `test_game_data_is_not_tracked` with the `git check-ignore` evidence behind it.",
        "Advance the status records in the SAME commit as the work, per `.claude/skills/commit/SKILL.md:120-131`: the `ROOT_CAUSE_ANALYSIS.md` and `IMPLEMENTATION_PLAN.md` status blockquotes, and the Index row at `requests/bugfix-requests/README.md:52` matched by its `[leak-guard-blind-to-untracked-files]` link, moved to `fixed`.",
        "Terminal stage means the directory moves once into `requests/bugfix-requests/_done/` with the Index link repointed (`.claude/skills/commit/SKILL.md:128-130`). Do this in the same commit and then re-run `uv run pytest tests/test_doc_links.py -q`: `markdown_files()` at `tests/test_doc_links.py:170` excludes `_done/` from scanning, but any LIVE document that links INTO this directory still has to resolve after the move. Fix any that break.",
        "STOP. Do not open the PR, do not merge, do not push `main`, do not amend — `.claude/skills/commit/SKILL.md:229-237` reserves all four for the user. Report the short SHA and the PR-creation URL and hand over.",
        "Note that pushing this branch triggers no CI: the workflow fires on `pull_request` and on push to `main` only (`.github/workflows/ci.yml:3-6`). Say so, rather than leaving the user watching for a run that will never start."
      ],
      "acceptance": [
        "`uv run pytest -m \"not gamedata\"` → 0 failures; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` → clean; all five node skill guards exit 0.",
        "The red reproduction named in the RCA — `tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard` — is green, and at least four new regression tests from Phase 3 are present and green.",
        "`IMPLEMENTATION_REPORT.md` exists in the work dir with a conforming status blockquote and carries the before/after suite counts.",
        "The Index row and both artifact status blockquotes read `fixed`, the directory sits under `requests/bugfix-requests/_done/`, and `uv run pytest tests/test_doc_links.py -q` is green after the move.",
        "No PR was opened, no push to `main`, no force-push, no `--amend`, and every commit in the branch was made through `/commit`."
      ],
      "commit_note": "\"Close out the leak-guard scope fix\" — report, status blockquotes, Index row and the `_done/` move in one commit. This is the terminal commit: `/commit` pushes the feature branch and hands back the PR URL, and that is where the agent's job ends."
    }
  ],
  "testing": "The acceptance contract is the bugfix track's, stated at `requests/bugfix-requests/README.md:25-26`: the red reproduction goes green, a regression test is left behind, and nothing else regresses. All three are measurable here.\n\nBASELINE (measured by me, 2026-08-17, branch `fix-leak-guard-untracked-blindness` at `edc7aea`, clean tree): `uv run pytest -m \"not gamedata\" -q` collects 125, passes 124, fails 1 — `tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard`, with the RCA's exact assertion text. `uv run pytest tests/test_leak_guard_scope.py -q` prints `.F.....` — one red, six green.\n\nRED GOES GREEN. `tests/test_leak_guard_scope.py:62-75` writes a probe into the working tree via the `untracked_file` contextmanager at :38-51 and asserts it appears in `guard.tracked_text_files()`. After Phase 2 it passes. The six counterweights are the harder half and must stay green: the gitignored-file test at :78-91 (a probe under `var/tmp/` must NOT be enumerated) and the four parametrized junk-directory cases at :94-102 (`.venv`, `__pycache__`, `node_modules`, `var`). The seventh test at :54-59 asserts the runtime-assembled `LEAK` string still matches a live pattern, so the scope assertions cannot pass vacuously if `PATTERNS` at `tests/test_no_leaks.py:24-28` ever changes.\n\nREGRESSION TESTS LEFT BEHIND (Phase 3), each pinning something the committed repro does not:\n  * nested untracked directory — the actual bug shape. Measured: `git ls-files --others --exclude-standard` lists `reviews/deep/b.md` individually, while adding `--directory` collapses it to `reviews/`. Without this test, a later \"simplification\" that adds `--directory` goes green while restoring the defect.\n  * non-ASCII filename — pins `-z`. Measured: default output returns `\"caf\\303\\251.md\"` quoted, which resolves to no file and whose `.suffix` fails the `keep` test at `tests/test_no_leaks.py:39`, so the path drops silently.\n  * assertion-level firing — `pytest.raises(AssertionError)` around `guard.test_no_machine_paths_or_identifiers()` with a probe present. Every existing scope test proves enumeration; none proves the guard actually fails the build on what it enumerated.\n  * `EXEMPT_PREFIXES` covers no `requests/` path — the one-line silencing move that would recreate the defect, given all three real leaks lived in `requests/**/reviews/`.\n\nEach must be shown RED against the pre-fix argv. Prove that in a scratchpad copy of the repo, not by reverting in place; `.claude/agents/data-engineer-memory.md:99-104` records the working recipe and warns that `test_repo_structure.py` and `test_agent_contract.py` fail in such a copy as expected noise.\n\nNOTHING ELSE REGRESSES. The full offline selection must return to 0 failures at 125+ tests. Beyond pytest: `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy` (strict over `tests/` as well as `src/`, `pyproject.toml:91-95`, so an unannotated helper is a hard failure), plus the five node skill guards at `.github/workflows/ci.yml:70-78` which CI runs and which no pytest invocation covers.\n\nWHAT CI CANNOT PROVE, and the plan must say so out loud: CI checks out a clean tree, so `--others` contributes zero paths there and a green CI run is not evidence that the widening works. The proof is local, in `tests/test_leak_guard_scope.py`, which manufactures the untracked state it needs. Additionally, per `.github/workflows/ci.yml:3-6` the workflow fires only on `pull_request` and on push to `main` — pushing this branch runs nothing.\n\nFINAL DOGFOOD. Before staging the implementation report, run `uv run pytest tests/test_no_leaks.py -q` while that report is still untracked. That single run is the fix exercising itself on exactly the artifact class that produced the bug.",
  "risks": [
    "THE PANEL TRAIL THAT SHIPS WITH THIS PLAN IS THE MOST LIKELY FIRST CASUALTY. `requests/bugfix-requests/leak-guard-blind-to-untracked-files/reviews/` does not exist yet (measured: the directory holds only the two `.md` artifacts today) but stage 3 writes `plan-proposals.md` and `plan-adversarial.md` into it, and panel output routinely carries absolute paths. The moment Phase 2 lands, those files are in scope. That is the guard working, not a bug — but an implementer who meets a red suite mid-fix may conclude the widening is wrong. Phase 1 exists to discover this as data first. Mitigation: fix the content; never exempt `reviews/`.",
    "THE ONE-LINE FIX THAT SILENTLY DOES NOTHING. Adding `--directory` to `git ls-files --others` looks like a tidy way to keep output short and is measurably catastrophic: it collapses an untracked tree to its top directory, so `reviews/deep/b.md` is never listed — and every one of the three real leaks was nested. The red repro's probe sits at the repo ROOT, so it would still pass. Mitigation: the Phase 3 nested-directory test, plus an explicit comment in the argv.",
    "THE FIX REINTRODUCING ITS OWN BUG CLASS THROUGH ENCODING. Measured: without `-z`, git quotes a non-ASCII filename as `\"caf\\303\\251.md\"`; that string resolves to no file and its suffix is `.md\\\"`, so it fails the `keep` membership test at `tests/test_no_leaks.py:39` and is dropped from the candidate set with no error raised. A guard that widens its scope and then silently drops the files with unusual names has traded one blind spot for a subtler one.",
    "DELEGATING THIS TO THE WRITE-CAPABLE SUBAGENT. `.claude/agents/data-engineer.md:147-158` denies it `tests/`, `.github/` and `.claude/` at repo level — which is every path this fix touches — with the rationale at :160-162 that an agent able to edit the guards that catch it and then report green is the worst available failure mode. The subagent's own rulebook requires it to stop and report if the spec's targets land in the deny set, so delegating produces a refusal at best and a rules violation at worst. Build on the main thread.",
    "'COMPLETING' THE FIX BY WIDENING `test_game_data_is_not_tracked`. The RCA's Root tier invites it, and it is a measured near-no-op: `git check-ignore -v` resolves every banned name and suffix that check hunts to a `.gitignore` line (`:27` players.csv, `:31` *.dat, `:28` names.xml, `:25` *.lg/), so `--exclude-standard` would exclude them all from `--others`. Worse, the change would read as new coverage in the diff while adding none. Leave it on `--cached` and comment the measurement.",
    "A LATENT CRASH THE WIDENING MAKES LIKELIER. The read loop at `tests/test_no_leaks.py:83-88` catches only `UnicodeDecodeError`. `--cached` still lists a tracked file deleted from the working tree, so `path.read_text()` raises `FileNotFoundError` and the guard presents as a broken suite rather than as a leak report — during a rename or a `git rm` workflow, exactly when someone is moving files around. Cheap to fix in Phase 2; expensive to diagnose later.",
    "THE (d) ORDERING NOTE, WORDED WRONG, ATTACKS A CONVENTION. Once (a) lands, telling `/commit` to 'stage before you verify' is redundant for detection and actively pushes toward the `git add -A` habit that `.claude/skills/commit/SKILL.md:51-52` names as the single habit the skill exists to prevent. The note must instruct the agent to RUN the guard, not to stage more.",
    "THE `_done/` MOVE BREAKING LIVE LINKS. Phase 5 moves the directory per `.claude/skills/commit/SKILL.md:128-130`. `tests/test_doc_links.py:170` exempts `_done/` bodies from scanning, but live documents linking INTO the directory — including the Index row at `requests/bugfix-requests/README.md:52` — still have to resolve. Re-run the link guard after the move, not before.",
    "THE AGENT-MEMORY EDIT FORCES THE HEAVY GATE. `.claude/skills/commit/SKILL.md:96-99` makes `.claude/agents/data-engineer-memory.md` appearing in a staged diff a hard trigger for the full `/update-docs` sweep — the trigger is the file's presence, not a judgment that the entries look fine. Phase 4's commit will be slower than the others; plan for it rather than being surprised into skipping it.",
    "AN UNTRACKED SCRATCH NOTE TURNING THE SUITE RED MID-BUILD. After Phase 2 the cleanliness of the working tree is a test input. Any note an implementer drops in the repo root with a drive path in it fails `test_no_machine_paths_or_identifiers`. Keep scratch in the session scratchpad, which is outside the repo and therefore outside the candidate set."
  ],
  "files_to_touch": [
    {
      "path": "tests/test_no_leaks.py",
      "change": "THE FIX. Extract a `git_paths(*args) -> list[str]` helper running `git ls-files -z` and splitting on NUL (fully annotated — mypy is strict over tests). Point `tracked_text_files()` at :31-48 to `--cached --others --exclude-standard`, with no `--directory`. Skip non-existent paths in the read loop at :83-88 so a tracked-but-deleted file cannot raise FileNotFoundError. Switch `test_game_data_is_not_tracked` at :99-105 to the same helper with `--cached` only, plus a comment recording why widening it is a measured no-op. Rewrite the module docstring at :1-5, which currently says 'tracked' and is the narrowest statement of the guard's intent in the repo. Leave EXEMPT (:16), EXEMPT_PREFIXES (:18) and PATTERNS (:24-28) untouched."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "change": "Extend the committed repro with the shapes it does not cover: a nested untracked directory (the real bug shape), a non-ASCII filename (pins `-z`), an assertion-level test that `test_no_machine_paths_or_identifiers` actually raises with a probe present, and a test that EXEMPT_PREFIXES covers no `requests/` path. Extend `untracked_file()` at :38-51 to create and remove a parent directory. Every banned string stays assembled at runtime, as at :35 — a literal one would trip the guard on this module, which is not in EXEMPT."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "change": "Step 2 (:71-79): replace the manual 'scan the staged diff' eyeball with a concrete `uv run pytest tests/test_no_leaks.py -q`, noting the guard now covers untracked files so it is worth running before staging too. This is the RCA's disposed direction (d). Do NOT touch the false `gitleaks` sentence at :78 — the RCA routes it to `port-residue-sweep`."
    },
    {
      "path": ".github/workflows/ci.yml",
      "change": "Comment only, at :22-24. Extend it to say the guard now also depends on `--others` seeing the working tree and `--exclude-standard` reading `.gitignore` — both of which `actions/checkout@v7` with `fetch-depth: 1` already provides — and add the honest caveat that CI's tree is clean, so a green CI run is not evidence the widening works. No step changes."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "change": "Append one new `measured` entry in the format at :25-29 recording the widened scope, the `-z` requirement and the absent `--directory`. Annotate the stale entry at :78-85 (which currently teaches agents to hand-run PATTERNS because the guard is blind) in the same inline correction style already used at :82-84. Do not prune — :39-48 forbids it. Expect this file's presence in the diff to force the full /update-docs sweep."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "change": "Possible one-word touch at :121 ('No machine-specific paths in tracked files') if the sweep finds it now under-describes the guard's scope. Check; change only if needed."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/IMPLEMENTATION_PLAN.md",
      "change": "NEW — this stage's deliverable. Opens `> **Status:** planned · created <today> · decided · next: implement`. Write every `file:line` as a code span, never as a Markdown link target, and never write an absolute or drive-letter path into it: `tests/test_no_leaks.py:25` bans one in tracked text and — after this very fix lands — will ban one in the untracked draft too."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/IMPLEMENTATION_REPORT.md",
      "change": "NEW at Phase 5. Records the before/after suite counts (124 passed + 1 failed → 125 passed), the two measured argv decisions, and the reasoned decision not to widen `test_game_data_is_not_tracked`."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "Index row at :52 matched by its `[leak-guard-blind-to-untracked-files]` link: Stage cell to `planned` when the plan lands, then to `fixed` at Phase 5 with the link repointed into `_done/`. Status grammar is at :45."
    },
    {
      "path": "requests/bugfix-requests/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md",
      "change": "Status blockquote at :1 only — advanced to `planned` then `fixed`. The body is DECIDED and must not be edited."
    }
  ],
  "code_references": [
    {
      "ref": "tests/test_no_leaks.py:31-48 `tracked_text_files()`",
      "claim": "The whole defect. Shells out to bare `git ls-files` at :33, which lists the index, so an unstaged file never reaches the suffix filter at :39-47 and its bytes are never read."
    },
    {
      "ref": "tests/test_no_leaks.py:39",
      "claim": "The `keep` suffix set. Load-bearing for the `-z` argument: a git-quoted non-ASCII path has suffix `.md\"`, fails this membership test, and is dropped with no error."
    },
    {
      "ref": "tests/test_no_leaks.py:16",
      "claim": "`EXEMPT = {\"tests/test_no_leaks.py\"}` — exactly one entry, the guard's own source. This is why no other file in the repo, including the RCA and the repro, may contain a literal banned string."
    },
    {
      "ref": "tests/test_no_leaks.py:18",
      "claim": "`EXEMPT_PREFIXES: tuple[str, ...] = ()` — currently empty, so the `startswith` filter at :43 is inert. It is the obvious place a future maintainer silences a noisy `reviews/` artifact, which is why Phase 3 pins it."
    },
    {
      "ref": "tests/test_no_leaks.py:24-28 `PATTERNS`",
      "claim": "Three patterns: windows drive path, unix home path, email address. Every one of the three real 2026-08-17 leaks matched these — the failure was never a pattern miss."
    },
    {
      "ref": "tests/test_no_leaks.py:83-88",
      "claim": "The read loop catches only `UnicodeDecodeError`, so a tracked-but-deleted file (still listed by `--cached`) raises `FileNotFoundError` and presents as a broken suite. Pre-existing; Phase 2 guards it."
    },
    {
      "ref": "tests/test_no_leaks.py:97-116 `test_game_data_is_not_tracked`",
      "claim": "The second, independent `git ls-files` call at :99-105. Measured to be correct as-is: `--exclude-standard` would exclude every name and suffix it hunts, so widening it buys nothing."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:62-75",
      "claim": "The committed RED test. Verified failing 2026-08-17 with the RCA's exact assertion message. Note the RCA says 'Not yet committed' — it IS committed, in `edc7aea`."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:35",
      "claim": "`LEAK` is assembled at runtime from `chr(92)` and single characters so the module never contains a literal drive path. Every test added in Phase 3 must follow this construction."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:38-51 `untracked_file()`",
      "claim": "The contextmanager that writes a probe into the real working tree and removes it in a `finally`. It only unlinks the file, so Phase 3's nested-directory probe needs it extended to remove the parent."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:94-102",
      "claim": "The four parametrized junk-directory counterweights (`.venv`, `__pycache__`, `node_modules`, `var`). Measured green under the proposed idiom: zero entries from each."
    },
    {
      "ref": "tests/test_doc_links.py:159-171 `markdown_files()`",
      "claim": "The sibling guard enumerates with `REPO_ROOT.rglob(\"*.md\")` and a hand-rolled `.git`/`var`/`_done` exclusion — so it has always seen untracked files. The two guards' opposite policies are the drift this fix narrows."
    },
    {
      "ref": "tests/test_doc_links.py:55-92 `strip_fences()`",
      "claim": "A tested, fence-parity-correct implementation already exists in this repo. It is what the RCA's gated 'fence exemption' hardening would reuse, if that gate is taken — which this plan recommends deferring."
    },
    {
      "ref": ".github/workflows/ci.yml:22-24",
      "claim": "The checkout comment recording that the `git ls-files` dependency is deliberate — 'it needs the repo, not a detached blob export'. Still true under the new idiom; Phase 4 extends it rather than replacing it."
    },
    {
      "ref": ".github/workflows/ci.yml:3-6",
      "claim": "The workflow triggers on `pull_request` and push to `main` only. Pushing this branch runs no CI, which is why the local gate is the real gate."
    },
    {
      "ref": ".github/workflows/ci.yml:70-78",
      "claim": "Five node skill guards CI runs that no pytest invocation covers. Two belong to `create-implementation-plan` itself; Phase 5 runs all five locally."
    },
    {
      "ref": ".claude/agents/data-engineer.md:147-158",
      "claim": "The write-capable subagent's repo-level deny set: `tests/`, `.github/`, `ops/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md`, `docs/decisions/`. Every target of this fix is inside it, so this work is main-thread work."
    },
    {
      "ref": ".claude/agents/data-engineer.md:142",
      "claim": "`.claude/agents/data-engineer-memory.md` is the sole `.claude/` write carve-out — the one file in this change set a subagent could legally touch."
    },
    {
      "ref": ".claude/agents/data-engineer-memory.md:78-85",
      "claim": "A `measured` entry telling agents the leak guard is blind to untracked files and to hand-run `PATTERNS` instead. It goes stale the moment Phase 2 lands and must be annotated, not deleted."
    },
    {
      "ref": ".claude/agents/data-engineer-memory.md:39-48",
      "claim": "'There is no budget. Append freely and never prune.' Curation happens at `/update-docs`. This is why Phase 4 appends plus annotates rather than editing in place."
    },
    {
      "ref": ".claude/agents/data-engineer-memory.md:99-104",
      "claim": "The scratchpad-copy technique for proving a change in a deny-set path, with the warning that `test_repo_structure.py` and `test_agent_contract.py` fail in the copy as expected noise. Phase 3 uses it to prove each new test is genuinely red pre-fix."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:71-79",
      "claim": "Step 2's manual staged-diff scan, and at :78 the false claim that `gitleaks` will catch a secret in CI. The RCA's direction (d) note lands here; the gitleaks sentence is routed elsewhere and must not be touched."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:51-52",
      "claim": "'Never `git add -A` or `git add .` without reading the untracked list first' — the habit the skill exists to prevent, and the reason the (d) note must say 'run the guard', not 'stage first'."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:96-99",
      "claim": "The agent-memory file appearing in a staged diff is a hard trigger for the full `/update-docs` sweep — 'the trigger is the file's presence, not a judgment'. Phase 4 must budget for it."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:128-130",
      "claim": "A terminal stage (`fixed`) moves the request directory into `_done/` with the Index link repointed, in the same commit as the work."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:229-237",
      "claim": "Never push `main`, never force-push, never open the PR. Phase 5 stops at the pushed branch and the handed-back URL."
    },
    {
      "ref": ".claude/skills/update-docs/SKILL.md:25",
      "claim": "A SECOND false `gitleaks` promise, listing it among mechanical checks that 'moved to CI'. The RCA's correction says the claim occurs once; it occurs in two skills. Belongs in `port-residue-sweep`, recorded here so that sweep is complete."
    },
    {
      "ref": "pyproject.toml:91-95",
      "claim": "`[tool.mypy] strict = true`, `files = [\"src\", \"tests\"]` — the new `git_paths` helper and every new test needs full annotations or the build is red."
    },
    {
      "ref": "pyproject.toml:98-108",
      "claim": "`addopts = \"-q --strict-markers --strict-config\"` and exactly one marker, `gamedata`. Inventing a second marker is a hard collection error, not a warning."
    },
    {
      "ref": ".gitignore:4-6",
      "claim": "`.env`, `.env.*`, `!.env.example`. Measured under the new idiom: `.env` absent from the candidate set (it legitimately holds machine paths), `.env.example` present."
    },
    {
      "ref": ".gitignore:25-31",
      "claim": "`*.lg/`, `players.csv`, `names.xml`, `world_default.xml`, `schools.xml`, `*.dat` — confirmed by `git check-ignore -v` to be why widening `test_game_data_is_not_tracked` is a measured no-op."
    },
    {
      "ref": "CLAUDE.md:60",
      "claim": "'Everything resolves from `.env`; `tests/test_no_leaks.py` fails the build.' Names this guard as the enforcement mechanism for ADR 0006 — one of the five places Phase 4 sweeps for drift."
    },
    {
      "ref": "docs/decisions/0006-public-repo-local-data.md:30",
      "claim": "'`tests/test_no_leaks.py` fails the build on absolute paths, home...' — the ADR's own description of the guard, checked for under-description after the widening."
    },
    {
      "ref": "requests/bugfix-requests/README.md:45",
      "claim": "Status grammar for this track: `intake -> diagnosed -> planned -> fixed`. The plan opens at `planned`; Phase 5 advances to `fixed`."
    },
    {
      "ref": "requests/bugfix-requests/README.md:52",
      "claim": "The Index row for `[leak-guard-blind-to-untracked-files]`, currently `diagnosed`. Its link target changes when Phase 5 moves the directory into `_done/`."
    },
    {
      "ref": "requests/bugfix-requests/README.md:25-26",
      "claim": "'Done means the red reproduction goes green and a regression test is left behind.' The acceptance contract this plan is measured against."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:175-231",
      "claim": "The stage-3 section MENU. Sections 1-8 and References are Always/Default; section 9 (data contracts) is Conditional and must be OMITTED here — this change adds no dataset. Section 10 (code-grounding verification) applies."
    },
    {
      "ref": "tests/test_skill_references.py:86-108",
      "claim": "Resolves every `tests/test_*.py` and `docs/*.md` path a skill names against the repo. Any test module the Phase 4 edit to `commit/SKILL.md` cites must exist, or this blocking check goes red."
    }
  ],
  "open_questions": [
    "THE HARDENING GATE THE RCA LEFT OPEN — is a fenced-code exemption in scope? `tests/test_doc_links.py` gained one on 2026-08-17 (`strip_fences()` at :55-92 is tested and reusable), and its absence here is why neither the intake report nor the RCA can quote the string it is about. The counter-argument in the RCA is real and specific: a fence exemption in a LEAK guard is a way to smuggle a credential past it, which is not true of a link checker. RECOMMENDATION: keep it OUT of this fix and settle it as its own decision — folding a policy question into a scope fix is how the two guards drifted apart in the first place. Needs the human gate either way.",
    "THE SECOND FALSE `gitleaks` PROMISE. The RCA's 'Two corrections to the intake report' states the claim appears once, at `.claude/skills/commit/SKILL.md:78`. Measured: it also appears at `.claude/skills/update-docs/SKILL.md:25`, which lists `gitleaks` among the mechanical checks that 'moved to CI, where it runs on every PR and cannot be skipped'. Both are false. The RCA routes the finding to `port-residue-sweep`. Should this plan write the second occurrence into that request's body in Phase 4's commit (keeping the sweep complete), or leave the sweep to rediscover it? Recording it costs one line; rediscovering it costs a session.",
    "CONFIRM THE DECISION TO LEAVE `test_game_data_is_not_tracked` ON THE INDEX. The RCA's Root tier says a fix touching only `tracked_text_files()` 'leaves that one open'. I measured that widening it is a near-no-op — every banned name and suffix resolves to a `.gitignore` line, so `--exclude-standard` excludes them all — and that the change would read in the diff as coverage it does not provide. The plan takes the narrow path with a comment. If the gate disagrees, the honest alternative is `--cached --others` WITHOUT `--exclude-standard` for that one check, which would scan ignored paths and is a materially different (and much noisier) decision.",
    "SHOULD THE `-z` HARDENING AND THE MISSING-PATH GUARD RIDE ALONG, OR BE FILED? Both are real, both are measured, both are in the same six lines the fix already touches, and both are the same silent-blindness class as the bug. Bundling them is efficient; a purist reading of the bugfix track says a fix does one thing. RECOMMENDATION: bundle, because splitting means a second request whose whole content is 'the fix we just shipped drops files with accented names'.",
    "CI ON FEATURE-BRANCH PUSH. The intake's third amplifier (`BUGFIX_REQUEST.md:90-92`) is that a leak can be committed AND pushed with zero checks run, since `.github/workflows/ci.yml:3-6` fires only on `pull_request` and push to `main`. This fix does not close that. RECOMMENDATION: out of scope — it is a CI-policy change, not a defect — but the gate should say so explicitly rather than leave it implied.",
    "WORDING OF THE (d) NOTE. Direction (d) was disposed as 'a one-line ordering note' telling `/commit` to stage before it verifies. With (a) landed, staging-first no longer buys detection, and a note phrased as 'stage first' pushes toward the `git add -A` habit `.claude/skills/commit/SKILL.md:51-52` exists to forbid. The plan therefore reinterprets (d) as 'run the guard as a concrete step, and note it now sees untracked files too'. That is a faithful reading of the RCA's intent, not its literal words — worth confirming at the gate rather than assuming."
  ]
}
~~~
