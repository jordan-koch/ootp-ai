# Plan panel - raw planner proposals

Three divergent planners, unfiltered, as returned on 2026-08-21. Provenance only:
the merged, adversary-corrected plan is the sibling IMPLEMENTATION_PLAN.md.
Machine paths were rewritten repo-relative before this file was written.

## Planner: code-grounded - returned: True

```json
{
    "planner":  "code-grounded",
    "ok":  true,
    "onboarding_files":  [
                             {
                                 "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md",
                                 "why":  "The decided upstream artifact. Read the two-mode table at :17-21 first — mode B (a concurrent reader scanning while a healthy run has a probe planted) leaves nothing behind, is what every documented sighting actually was, and is the reason a survivor sweep cannot be the fix. The tiered fix posture at :137-164 and the three questions handed to the plan at :166-170 are what this plan answers."
                             },
                             {
                                 "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md",
                                 "why":  "Context only. Its measured blast-radius table at :79-89 is narrower than earlier panel claims: only test_no_fixed_offsets and `ruff format --check` go red; ruff check, mypy and the leak guard pass. Do not re-widen that claim."
                             },
                             {
                                 "path":  "tests/test_fixed_offset_guard_scope.py",
                                 "why":  "The site of the defect. `parser_probe` at :81-98 writes a real .py into the live package and unlinks in a `finally`; its docstring at :83-91 is the crux argument the fix must answer, not delete. `PARSER_DIR` is at :60. Four probe names are planted across :111, :126, :132, :430."
                             },
                             {
                                 "path":  "tests/test_no_fixed_offsets.py",
                                 "why":  "The reader. `SCAN_ROOT` at :97, `scan_source` at :339-342 (the exemption keys on a repo-relative posix string against `EXEMPT_MODULES` at :104-107), `parser_modules()` at :345-354, `parser_module_violations()` at :357-363, and the test that goes red at :569-575. This is where the seam is opened."
                             },
                             {
                                 "path":  "tests/test_guard_probe_isolation.py",
                                 "why":  "The committed red repro (landed in a146b20). `ABORT_CHILD` at :46-57 is a source string executed in a child process — it hard-codes `parser_probe(\"_guard_scope_abort_probe.py\", OFFENDER)` at :55, so it MUST be edited in the same commit as any signature change. `_planted_probes()` at :60-62 globs the live PARSER_DIR and must keep doing so."
                             },
                             {
                                 "path":  "tests/test_leak_guard_scope.py",
                                 "why":  "The second site of the same hazard class (RCA :122-131). `untracked_file` at :40-53 plants into REPO_ROOT with the same name-keyed clobber assert at :48; `LEAK` at :37 is a deliberately banned machine-path string, so a survivor here poisons the repo\u0027s only leak protection. Note the monkeypatch at :250-252, which breaks on any arity change."
                             },
                             {
                                 "path":  "tests/test_no_leaks.py",
                                 "why":  "The guard the second site poisons. `git_paths` at :44-67 (cwd=REPO_ROOT), `scannable_text_files` at :70-106, `machine_path_violations` at :139-165, `game_data_offenders` at :173-194, `is_git_ignored` at :216-232 — whose docstring already records this exact hazard class and its resolution (\"Asking git about a path costs nothing and cannot litter\")."
                             },
                             {
                                 "path":  "docs/decisions/0020-sanctioned-lookahead-seam.md",
                                 "why":  ":92-93 — \"No per-site exemption registry, ever. A registry lets a guard be satisfied by adding entries.\" This is the grounded reason Hardening (b) (teaching the guard to recognise probe names) is refused: it would be exactly that registry, keyed on filename."
                             },
                             {
                                 "path":  ".claude/agents/data-engineer.md",
                                 "why":  ":154-171 — `tests/` is in the write-capable subagent\u0027s repo-level deny set, and :171 says to stop and report if the spec\u0027s targets fall inside it. This change is ENTIRELY inside tests/, so the main thread implements it; the data-engineer subagent must not be spawned for it."
                             },
                             {
                                 "path":  "pyproject.toml",
                                 "why":  ":81-88 — `known-first-party = [\"ootp_ai\", \"fixtures\"]`, with a recorded local-vs-CI import-order failure caused by inference. It is why a new shared helper belongs under `tests/fixtures/` and nowhere else. :91-95 mypy strict over src AND tests. :98-108 pytest config: no xdist, which is why CI has never gone red on this."
                             }
                         ],
    "architecture_notes":  "## What the touched area actually looks like today\n\nThree separate test modules independently walk one shared, mutable directory — `src/ootp_ai/**/*.py` — and one of them writes into it.\n\n**The reader (guard):** `tests/test_no_fixed_offsets.py`\n- `REPO_ROOT` :96, `SCAN_ROOT = REPO_ROOT / \"src\" / \"ootp_ai\"` :97 — module constants, no parameter anywhere.\n- `parser_modules()` :345-354 = `sorted(SCAN_ROOT.rglob(\"*.py\"))` plus an anti-vacuity assert. Measured today: **37 modules, 0 violations**.\n- `parser_module_violations()` :357-363 relativises each path against `REPO_ROOT` and passes that posix string into `scan_source(source, rel)` :339-342, which decides exemption by `filename in EXEMPT_MODULES` (:104-107, two repo-relative posix strings). **The rel string is load-bearing twice** — once as the violation message, once as the exemption key. Any root parameter must preserve it exactly or `lookahead.py` stops being exempt inside a mirror.\n- `test_no_parser_module_seeks_to_a_fixed_offset()` :569-575 asserts that list is empty. This is the test that goes red on a phantom.\n\n**The writer (probe):** `tests/test_fixed_offset_guard_scope.py`\n- `PARSER_DIR = REPO_ROOT / \"src\" / \"ootp_ai\" / \"parser\"` :60; `parser_probe(name, body)` :81-98 writes into it and unlinks in a `finally`, yielding the rel string `src/ootp_ai/parser/{name}` that every assertion matches on (`rel in v` at :113, :127, :432).\n- Its docstring :85-86 is the design argument: *\"the scan enumerates the package on disk, so the probe has to exist inside it to be a fair test of what the scan actually reads.\"* That argument is correct about what it needs and must survive the fix rather than be discarded.\n- `test_the_module_set_has_a_floor` :137-150 and `test_an_allowlisted_path_matches_what_the_real_scan_builds` :176-184 call the guard with **no arguments** and must keep doing so — they are the coverage floor over the real package.\n\n**The seam that does not exist:** there is no way to point the reader at a different tree, so a probe placed where the scan will fairly find it is placed where every other reader will also find it.\n\n**A third reader the RCA did not name.** `tests/test_grain_contracts.py:75` defines its own `SCAN_ROOT = REPO_ROOT / \"src\" / \"ootp_ai\"` and `source_modules()` at :364-367 does the same `rglob(\"*.py\")`, feeding `test_no_module_in_src_joins_on_the_historical_id` at :370-380. It plants nothing, so it is not part of the *cause*; but it means a survivor whose body mentioned `historical_id` would redden a third guard. This is architecture, not scope: it is why \"un-share the tree\" is the right shape and \"teach one guard about probe names\" is not — the second fix would have to be repeated per reader.\n\n**The second instance of the class:** `tests/test_leak_guard_scope.py:40-53` `untracked_file` is structurally identical, writing into REPO_ROOT (:73 repo root, :119-120 under `requests/bugfix-requests/`, :89-90 under `var/tmp`, :174 under `tests/fixtures/`) with the same name-keyed clobber assert at :48. Its reader, `tests/test_no_leaks.py`, is repo-rooted through `git_paths(...)` at :44-67 (`cwd=REPO_ROOT`) and `REPO_ROOT / rel` at :103 / `relative_to(REPO_ROOT)` at :149.\n\n## Where the change hooks in\n\n**One seam, one convention, two sites.** The seam is a `repo_root` parameter defaulting to the live `REPO_ROOT`, threaded through each guard\u0027s enumeration helpers; the convention is a shared mirror builder under `tests/fixtures/` that materialises a faithful copy of the scanned tree in `tmp_path` and returns *a repo root*, so the derived rel strings — and therefore `EXEMPT_MODULES` matching, violation messages, and `.gitignore` semantics — are byte-identical to production.\n\nDeriving the scan root *inside* the guard from a single `repo_root` argument (rather than accepting a `root` that points straight at `src/ootp_ai`, as the RCA\u0027s minimal tier sketched) is what keeps the exemption key intact. That is a deliberate refinement of the RCA\u0027s shape and the plan should say so.\n\n**The fidelity argument is answered by the copy, not by a concession.** The RCA\u0027s middle path — copy the real package into the temp tree and plant beside it — is adopted, plus two compensating assertions that make it non-vacuous: (a) the production scan root **is** the live package, and (b) the mirror\u0027s module set **equals** the live package\u0027s. Without (b) the mirror can silently decay into a bare `tmp_path` with one file, which is precisely the weakening `parser_probe`\u0027s docstring warned about.\n\n**Name-awareness moves out of the guard and into a sibling test.** The report\u0027s Q2 asked whether the guard should recognise `_guard_scope*_probe.py` and say \"a test fixture survived an interrupted run\". ADR 0020:92-93 forecloses a per-site exemption registry, and a filename-keyed special case in the guard is one. The honest message is delivered instead by a separate residue-detector test that names the survivor and its cause, while `test_no_parser_module_seeks_to_a_fixed_offset` keeps its verdict unchanged. Both go red together; the new one explains, the old one does not lie.\n\n**The hardening sweep is a detector, not a deleter.** The RCA (:157-161) says a sweep cannot fix either mode and must not be sold as the fix. So no autouse fixture deletes anything: the residue test reports and fails. Deletion stays a human act, which is also the only behaviour compatible with \"the repo is public and nothing silently mutates the tree\".\n\n**Structural enforcement of the convention.** Rather than prose, `parser_probe` and `untracked_file` are given a `root` first parameter **with no default**. A fixture that cannot be called without naming a tree cannot silently plant in the live one, and `inspect.signature` makes that assertable.",
    "phases":  [
                   {
                       "name":  "Phase 1 — Open the root seam and rehome the probe into a mirrored package",
                       "goal":  "Both committed repro tests in tests/test_guard_probe_isolation.py go GREEN, and the fixture\u0027s fidelity claim is preserved by a real copy of the package plus two compensating assertions rather than abandoned.",
                       "steps":  [
                                     "Create `tests/fixtures/guard_mirror.py` (new file; `tests/fixtures/` is already a package — `tests/fixtures/__init__.py` exists and explains why — and `fixtures` is declared first-party at pyproject.toml:88, so an import from it does not churn ruff\u0027s isort ordering). Give it a module docstring that states the convention in one sentence: a guard fixture never mutates the tree the guard reads; it mirrors that tree into a temp directory and mutates the mirror.",
                                     "In `guard_mirror.py` add `def mirror_package(dest: Path) -\u003e Path:` — `shutil.copytree(REPO_ROOT / \"src\" / \"ootp_ai\", dest / \"src\" / \"ootp_ai\", ignore=shutil.ignore_patterns(\"__pycache__\"))` and return `dest`. It returns the mirror\u0027s **repo root**, not the package dir, so callers build the same repo-relative posix strings production builds. Fully annotate (mypy is strict over tests/, pyproject.toml:91-95). Do not use pytest fixtures here — a plain function is required because `ABORT_CHILD` runs it in a bare child process with no pytest.",
                                     "In `tests/test_no_fixed_offsets.py`, change `parser_modules()` (:345-354) to `def parser_modules(repo_root: Path = REPO_ROOT) -\u003e list[Path]:` and derive `scan_root = repo_root / \"src\" / \"ootp_ai\"` inside it; keep the existing anti-vacuity assert at :353, updating its message to name the derived root. Leave `SCAN_ROOT` at :97 in place as the documented production root and keep it referenced (the new fidelity test asserts against it).",
                                     "In `tests/test_no_fixed_offsets.py`, change `parser_module_violations()` (:357-363) to `def parser_module_violations(repo_root: Path = REPO_ROOT) -\u003e list[str]:`, pass `repo_root` to `parser_modules(...)`, and relativise with `path.relative_to(repo_root)` at :361. **Do not change the shape of the rel string** — `scan_source` at :340 decides exemption with `filename in EXEMPT_MODULES` (:104-107), so `src/ootp_ai/parser/lookahead.py` must come out of a mirror identically or the seam stops being exempt there. Add a short comment at the relativisation saying exactly that.",
                                     "Add a one-paragraph note to `parser_modules`\u0027s docstring explaining that the parameter exists so a fixture can probe a mirrored copy without mutating the tree every other reader shares, and that production callers pass nothing.",
                                     "In `tests/test_fixed_offset_guard_scope.py`, change `parser_probe` (:81-98) to `def parser_probe(root: Path, name: str, body: str) -\u003e Iterator[str]:` — **`root` first and with no default**. Plant at `root / \"src\" / \"ootp_ai\" / \"parser\" / name`; `mkdir(parents=True, exist_ok=True)` is not needed when `root` came from `mirror_package`, but keep the clobber assert at :93 verbatim. Keep yielding `f\"src/ootp_ai/parser/{name}\"` unchanged so every `rel in v` assertion (:113, :127, :432) keeps working.",
                                     "Rewrite `parser_probe`\u0027s docstring (:83-91). Do NOT delete the argument at :85-86 — restate it and answer it: the scan still enumerates a real package on disk holding every real module, so the probe is still read among real neighbours; what changed is that the package is a mirror nothing else reads. Cite the request directory so the reason survives.",
                                     "Add a module-scoped fixture in `tests/test_fixed_offset_guard_scope.py`: `@pytest.fixture(scope=\"module\")` `def mirror(tmp_path_factory: pytest.TempPathFactory) -\u003e Path: return mirror_package(tmp_path_factory.mktemp(\"guard_scope_mirror\"))`. Module scope means one copytree per module (~37 files, 551 KB measured — milliseconds); the per-session `tmp_path` root is what closes mode B, because two concurrent pytest sessions get different basetemps.",
                                     "Update the four planting call sites to take `mirror`: :111 `test_the_scan_reports_a_planted_offender_in_the_real_tree` (and pass `mirror` to `guard.parser_module_violations(mirror)` at :112), :126 (`:127` likewise), :132 `test_the_probe_is_removed_even_though_the_scan_read_it` — whose two `PARSER_DIR / ...` assertions at :133-134 become the mirror path — and :430 (`:431` likewise). Rename `test_the_scan_reports_a_planted_offender_in_the_real_tree` only if its name becomes a lie; prefer keeping the name and amending the docstring, since the tree is still a real package on disk.",
                                     "Add `test_the_production_scan_root_is_the_live_package()` to `tests/test_fixed_offset_guard_scope.py` — the compensating assertion the RCA requires (:148-150). Assert `guard.SCAN_ROOT == REPO_ROOT / \"src\" / \"ootp_ai\"`, that a no-argument `guard.parser_modules()` returns only paths under it, and that both `guard.EXEMPT_MODULES` entries appear in `{p.relative_to(REPO_ROOT).as_posix() for p in guard.parser_modules()}`. Message: the parameter exists for fixtures, and production must never be pointed elsewhere.",
                                     "Add `test_the_mirror_holds_the_same_modules_as_the_live_package(mirror)` — set equality between `{p.relative_to(mirror).as_posix() for p in guard.parser_modules(mirror)}` and `{p.relative_to(REPO_ROOT).as_posix() for p in guard.parser_modules()}`. Without this the mirror can decay into a bare tmp_path and the fidelity argument is silently lost.",
                                     "Leave `test_the_module_set_has_a_floor` (:137-150) and `test_an_allowlisted_path_matches_what_the_real_scan_builds` (:176-184) calling the guard with **no arguments**. The RCA is explicit (:150) that the floor must keep running against the real package or the fix buys a vacuous guard.",
                                     "In `tests/test_guard_probe_isolation.py`, update `ABORT_CHILD` (:46-57) in the same edit: it must import `mirror_package` from `fixtures.guard_mirror`, build a mirror under a directory passed as a second argv element, and call `parser_probe(root, \"_guard_scope_abort_probe.py\", OFFENDER)`. Add an anti-vacuity step inside the child — if the planted file does not exist, `os._exit(96)` — and keep `os._exit(97)` as the success path.",
                                     "Update `test_a_run_that_dies_inside_the_probe_leaves_no_module_behind` (:65-97) to pass the extra argv path, and add `96` to the assertion message at :83-87 as the distinguishable \"the fixture planted nothing\" outcome. **Do not change `_planted_probes()` (:60-62) or the survivor assertion at :89-94** — they must keep globbing the LIVE `PARSER_DIR`, because that is the entire regression guard.",
                                     "Update `test_the_real_scan_does_not_report_a_probe_a_sibling_test_has_planted` (:100-117) to plant into a mirror, and add the paired anti-vacuity assertion in the same test: the same violation IS reported by `guard.parser_module_violations(mirror_root)` while absent from the default-root scan. Otherwise the test passes whenever nothing was planted at all."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_guard_probe_isolation.py` — 2 passed (both were RED before this phase).",
                                          "`uv run pytest tests/test_fixed_offset_guard_scope.py tests/test_no_fixed_offsets.py` — green, with two new tests present (`test_the_production_scan_root_is_the_live_package`, `test_the_mirror_holds_the_same_modules_as_the_live_package`) and the pre-existing count otherwise unchanged.",
                                          "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all green.",
                                          "`git status --porcelain --untracked-files=all` is EMPTY immediately after the full suite run — the bug\u0027s own Expected, stated at BUGFIX_REQUEST.md:59-61.",
                                          "Mutation 1 (guard not weakened): hand-write `src/ootp_ai/parser/_guard_scope_probe.py` containing the OFFENDER body from tests/test_fixed_offset_guard_scope.py:65-68; `uv run pytest tests/test_no_fixed_offsets.py` must still be RED naming that file. Delete it afterwards and re-confirm green.",
                                          "Mutation 2 (regression guard is live): temporarily repoint `parser_probe` at `PARSER_DIR`; both tests in tests/test_guard_probe_isolation.py must go RED. Revert.",
                                          "Mutation 3 (mirror is not vacuous): temporarily make `mirror_package` copy nothing but `__init__.py`; `test_the_mirror_holds_the_same_modules_as_the_live_package` must go RED. Revert.",
                                          "Measured and recorded: `guard.parser_modules()` still returns 37 modules and `guard.parser_module_violations()` still returns 0 violations (the pre-change baseline measured 2026-08-21)."
                                      ],
                       "commit_note":  "Un-share the tree: the fixed-offset probe plants into a mirrored package, not the live one. Adds a repo_root seam to parser_modules/parser_module_violations, a shared mirror builder under tests/fixtures/, and two compensating assertions that keep the fidelity argument honest. Turns both committed repro tests green."
                   },
                   {
                       "name":  "Phase 2 — Make a survivor name itself, without teaching the guard about its own test",
                       "goal":  "If an older revision left a probe behind, the run says \u0027a test fixture survived an interrupted run; delete it\u0027 — from a sibling test, never from the guard, so ADR 0020\u0027s no-exemption-registry rule stays untouched and the fixed-offset guard\u0027s verdict on the file is unchanged.",
                       "steps":  [
                                     "Add `test_no_probe_residue_is_present_in_the_working_tree()` to `tests/test_guard_probe_isolation.py`. Reuse `_planted_probes()` (:60-62) for the `src/ootp_ai/parser/_guard_scope*_probe.py` case; assert the list is empty with a message that names the file, says it is a fixture artifact from an interrupted run of an older revision, says to delete it, and points at this request directory.",
                                     "Do NOT delete anything. The RCA (:157-161) says a sweep cannot fix either mode and must not be sold as the fix; a reporting test is the only part of Hardening (a) with real value, and silent tidying would hide the evidence the next reader needs.",
                                     "Add `test_a_guard_probe_cannot_be_planted_without_naming_a_tree()` — `inspect.signature(parser_probe).parameters` has `root` as the first parameter with `Parameter.empty` as its default. This is the structural half of the convention: a fixture that cannot be called without naming a tree cannot silently plant in the live one.",
                                     "Extend the module docstring of `tests/test_guard_probe_isolation.py` (:1-26) with a short paragraph recording the resolution: the seam, the mirror, and the explicit refusal to teach the guard probe names, citing docs/decisions/0020-sanctioned-lookahead-seam.md:92-93.",
                                     "Add a comment (not a code change) near `tests/test_no_fixed_offsets.py`\u0027s `parser_module_violations` recording that the guard deliberately does not recognise probe filenames, and why — so a future reader does not re-propose it."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_guard_probe_isolation.py` — 4 passed.",
                                          "With a hand-planted `src/ootp_ai/parser/_guard_scope_probe.py`: `test_no_probe_residue_is_present_in_the_working_tree` is RED and its message names the file and the cause; `test_no_parser_module_seeks_to_a_fixed_offset` is ALSO red with its message unchanged from today\u0027s. Delete the plant; both green.",
                                          "`grep -n \u0027_guard_scope\u0027 tests/test_no_fixed_offsets.py` returns nothing — the guard itself knows no probe names.",
                                          "Full gate green: `uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`."
                                      ],
                       "commit_note":  "A surviving probe now names itself, from a sibling test rather than the guard. Refuses ADR 0020\u0027s foreclosed shape (a filename-keyed exemption inside the guard) and pins the no-default-root convention with a signature assertion."
                   },
                   {
                       "name":  "Phase 3 — The class, not the instance: the leak-guard probe stops writing into the live repo",
                       "goal":  "`untracked_file` in tests/test_leak_guard_scope.py plants into a mirrored git repo instead of REPO_ROOT, so a survivor can no longer drop a deliberately banned machine-path string into the repo root and redden the only leak protection this public repo has.",
                       "steps":  [
                                     "In `tests/fixtures/guard_mirror.py` add `def mirror_repo(dest: Path) -\u003e Path:` — `git init -q` in `dest` (capture output; do not assume a default branch name and do NOT commit: CI has no configured git identity), copy the repo\u0027s `.gitignore` verbatim into `dest`, and `mkdir` the directories the existing tests plant into: `var/tmp`, `requests/bugfix-requests`, `tests/fixtures`. Copying the real `.gitignore` is what keeps the last-match-wins tests real — `.gitignore:64-65`\u0027s `!datasets/**` and `!tests/fixtures/**` negations are exactly what tests/test_leak_guard_scope.py:165-178 exists to pin.",
                                     "Thread `repo_root: Path = REPO_ROOT` through `tests/test_no_leaks.py`: `git_paths` (:44, and its `cwd=REPO_ROOT` at :62), `scannable_text_files` (:70, and `REPO_ROOT / rel` at :103), `machine_path_violations` (:139, and `relative_to(REPO_ROOT)` at :149), `game_data_offenders` (:173), `is_git_ignored` (:216, `cwd` at :229). Defaults stay the live repo; the four `test_*` functions keep calling with no arguments.",
                                     "Change `untracked_file` (:40-53) to `def untracked_file(root: Path, relative: str, body: str) -\u003e Iterator[Path]:` — `root` first, **no default**, same clobber assert at :48, same `finally` unlink. Rewrite its docstring (:42-46) the way Phase 1 rewrote `parser_probe`\u0027s: restate the fidelity argument and say the mirror answers it.",
                                     "Add a module-scoped `mirror` fixture to `tests/test_leak_guard_scope.py` built from `mirror_repo(tmp_path_factory.mktemp(\"leak_guard_mirror\"))`, and move every planting test onto it, passing the same root to the guard call in the same test: :64-78, :81-94, :113-124, :127-141, :158-162, :165-178, :181-185, :188-193, :203-215, :218-221. Delete the `(REPO_ROOT / \"var\" / \"tmp\").mkdir(...)` calls at :89 and :183 — `mirror_repo` creates them.",
                                     "Add `test_the_mirror_carries_this_repo_s_ignore_rules()` — assert the mirror\u0027s `.gitignore` text equals `(REPO_ROOT / \".gitignore\").read_text(encoding=\"utf-8\")`. This is the leak-guard analogue of Phase 1\u0027s set-equality test: without it the gitignore-sensitive tests at :81-94, :165-178, :181-193 quietly start testing an invented rule set.",
                                     "Leave on the REAL repo, with no root argument: `test_the_probe_string_is_one_the_guard_actually_bans` (:56-61), `test_no_ignored_directory_leaks_into_the_candidate_set` (:97-105), `test_enumeration_yields_no_empty_entries` (:144-155), `test_the_candidate_set_has_a_floor` (:224-238, the ~134-file floor), and the three report-root tests at :235-283 of tests/test_no_leaks.py. Same reasoning as the module floor: the coverage assertions must observe production or the fix buys a vacuous guard.",
                                     "**Fix the monkeypatch arity** at `tests/test_leak_guard_scope.py:250-252`: `lambda: [...]` becomes a callable accepting the new `repo_root` argument (e.g. `lambda repo_root=REPO_ROOT: [...]`). If this is missed the test dies with a TypeError, which is red for the wrong reason and invites deleting the test.",
                                     "Add `test_a_leak_probe_cannot_be_planted_without_naming_a_tree()` mirroring Phase 2\u0027s signature assertion, this time over `untracked_file`.",
                                     "Extend `test_no_probe_residue_is_present_in_the_working_tree` (Phase 2) to also refuse `_leak_guard*probe*` residue at the repo root, under `var/tmp`, under `requests/bugfix-requests/` and under `tests/fixtures/` — the four sites tests/test_leak_guard_scope.py plants into today.",
                                     "OFF-RAMP, decide before starting: if `mirror_repo` proves unstable in CI (git availability, ownership/`safe.directory`, init warnings), STOP after Phase 2, file the leak-guard site as its own bugfix request under requests/bugfix-requests/, and record the split in the implementation report. Do not half-land it."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_leak_guard_scope.py tests/test_no_leaks.py` — green, with the same number of pre-existing tests plus the two new ones. No pre-existing assertion MESSAGE is edited (read the diff hunk by hunk; the leak-guard\u0027s own prior implementation review, requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/reviews/implementation-review.md:178, treats an edited message inside a mechanical rename as a laundered weakening).",
                                          "Mutation: temporarily repoint `untracked_file` at REPO_ROOT and confirm `test_no_probe_residue_is_present_in_the_working_tree` catches a leftover `_leak_guard_probe.md` at the repo root. Revert.",
                                          "Mutation (guard not weakened): the no-op mutant recorded at requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_REPORT.md:96 — make `scannable_text_files` return `[]` — must still kill `test_the_guard_actually_reports_a_planted_leak`.",
                                          "`git status --porcelain --untracked-files=all` is EMPTY after `uv run pytest -m \"not gamedata\"`.",
                                          "Full gate green: pytest / ruff check / ruff format --check / mypy. `uv run mypy` still reports the same source-file count as before the change (BUGFIX_REQUEST.md:84 records that a survivor silently widened it 80 → 81)."
                                      ],
                       "commit_note":  "Apply the same convention to the leak-guard probe: it plants into a mirrored git repo carrying this repo\u0027s own .gitignore, never into the working tree. Threads a repo_root seam through tests/test_no_leaks.py, keeps every coverage floor on production, and extends the residue detector to the four leak-probe sites."
                   },
                   {
                       "name":  "Phase 4 — Close the record",
                       "goal":  "The request artifacts and the repo\u0027s own documentation say what actually landed, including what was deliberately refused and why.",
                       "steps":  [
                                     "Write `requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md` with the red→green evidence for both repro tests, the three Phase 1 mutation results, the measured before/after (`37 modules, 0 violations` both sides), and an explicit section on what was refused: the survivor sweep as a fix (RCA :157-161) and the name-aware guard message (ADR 0020:92-93).",
                                     "Set the `guard-probe-survives-an-interrupted-run` Index row in `requests/bugfix-requests/README.md:54` from `diagnosed` to `fixed`, and amend the note to record the two-site outcome. Per requests/bugfix-requests/README.md:45 the status grammar is intake → diagnosed → planned → fixed.",
                                     "Run `/update-docs` and dispose what it raises. Expected findings and their correct dispositions: ADR 0020 is NOT invalidated (the rule, the allowlist and the visitor are untouched — only where the fixture does its work changed); CLAUDE.md\u0027s project map line `tests/  Structural guards + parser fixtures` still holds; docs/data-access.md is not implicated (no ingestion surface is touched, and no claim in it underpins this change).",
                                     "If Phase 3 took the off-ramp, file the leak-guard site as its own BUGFIX_REQUEST under requests/bugfix-requests/ and link it from this request\u0027s report — do not leave it as an unfiled observation, which is precisely the failure this request itself documents (BUGFIX_REQUEST.md:24-28: observed five times, filed zero times).",
                                     "Land through `/commit` and open the PR. Confirm CI\u0027s `Lint, types, tests` job is green — .github/workflows/ci.yml:45-57 runs ruff check, ruff format --check, mypy and `pytest -m \"not gamedata\"`, which is the exact local gate."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_doc_links.py tests/test_repo_structure.py` green — every relative link written in the report and plan resolves on disk.",
                                          "requests/bugfix-requests/README.md:54\u0027s Stage cell reads `fixed`, and the IMPLEMENTATION_PLAN.md / IMPLEMENTATION_REPORT.md status blockquotes follow the grammar at requests/bugfix-requests/README.md:41-45.",
                                          "`/update-docs` reports no outstanding drift, with the ADR-0020-not-invalidated judgement recorded rather than assumed.",
                                          "CI green on the PR, including the node skill-guard step (.github/workflows/ci.yml:70-78), which this change does not touch."
                                      ],
                       "commit_note":  "Record the guard-probe fix: two sites, one convention, and the two hardening options deliberately refused."
                   }
               ],
    "testing":  "**The acceptance contract is the bugfix track\u0027s, not a feature\u0027s:** the committed red repro goes green, a regression test is left behind, and nothing else regresses (requests/bugfix-requests/README.md:24-26).\n\n**The red repro is already committed** (commit a146b20, `tests/test_guard_probe_isolation.py`) and is RED on today\u0027s code with the two failures quoted at ROOT_CAUSE_ANALYSIS.md:45-54. It is `-m \"not gamedata\"`, offline, and runs in CI.\n\n**The local gate, per phase, before `/commit`** — identical to what CI runs at .github/workflows/ci.yml:45-57:\n\n```\nuv run ruff check .\nuv run ruff format --check .\nuv run mypy\nuv run pytest -m \"not gamedata\"\n```\n\nplus one command this particular bug makes mandatory, because it is the bug\u0027s own Expected (BUGFIX_REQUEST.md:59-61):\n\n```\ngit status --porcelain --untracked-files=all\n```\n\nIt must print nothing after a full suite run. A non-empty result means a fixture is still writing into the working tree.\n\n**Phase-by-phase red→green ledger.** Phase 1 flips both repro tests. Phases 2–4 must leave them green; each phase re-runs the whole gate, so a later phase cannot silently unflip an earlier one.\n\n**Regression tests left behind** (this is what the track\u0027s \"done\" requires beyond the repro):\n- `test_the_production_scan_root_is_the_live_package` — production is never pointed at a mirror.\n- `test_the_mirror_holds_the_same_modules_as_the_live_package` — the mirror cannot decay into a bare tmp_path, which is the only way the fidelity argument at tests/test_fixed_offset_guard_scope.py:85-86 could be lost silently.\n- `test_no_probe_residue_is_present_in_the_working_tree` — a survivor from an older revision names itself.\n- `test_a_guard_probe_cannot_be_planted_without_naming_a_tree` / `..._a_leak_probe_...` — the convention is structural, not prose.\n- `test_the_mirror_carries_this_repo_s_ignore_rules` — the leak-guard mirror tests the real `.gitignore`.\n- Untouched and load-bearing: `test_the_module_set_has_a_floor` (tests/test_fixed_offset_guard_scope.py:137-150) and `test_the_candidate_set_has_a_floor` (tests/test_leak_guard_scope.py:224-238) keep observing production.\n\n**Mutation testing is not optional here.** This repo has been bitten twice by guards that were green while guarding nothing (tests/test_fixed_offset_guard_scope.py:9-14). Every acceptance list above carries an explicit mutation with a revert; run them and record the outcome in the implementation report rather than asserting the fix works.\n\n**The measured baseline to reproduce on both sides of the change** (measured 2026-08-21 against this working tree): `parser_modules()` → 37 modules; `parser_module_violations()` → 0 violations; `mypy` source-file count unchanged (a survivor silently widens it 80 → 81, BUGFIX_REQUEST.md:84).\n\n**What this change does not need to test.** No parser, warehouse, report or contract code is touched, so no gamedata run, no MySQL, no save, and no `players.csv` ground-truth diff is involved. `uv run pytest -m gamedata` is out of scope and must not be claimed as evidence.",
    "risks":  [
                  "**ABORT_CHILD drift is the sharpest trap.** `tests/test_guard_probe_isolation.py:46-57` is a source STRING run in a child process; static analysis, mypy and ruff see nothing inside it. Change `parser_probe`\u0027s signature without updating it and the child exits 1, the assertion at :83-87 fires with a message about the child never reaching the probe, and the temptation is to \"simplify\" the test rather than fix the string. Mitigation: edit both in the same hunk, and add the exit-96 anti-vacuity branch so a fixture that plants nothing is distinguishable from one that never ran.",
                  "**The exemption key is easy to break invisibly.** `scan_source` decides exemption by `filename in EXEMPT_MODULES` (tests/test_no_fixed_offsets.py:340 against :104-107, repo-relative posix strings). If the root parameter is taken as a *scan root* pointing straight at the package (the RCA\u0027s literal sketch at :140) rather than as a *repo root*, `path.relative_to(root)` yields `parser/lookahead.py` and the seam silently stops being exempt inside the mirror — the mirror then reports violations production does not, and the natural \u0027fix\u0027 is to loosen the rule. Mitigation: one `repo_root` parameter, scan root derived inside, plus the mirror/live set-equality test.",
                  "**A mirror that is not a real package is the weakening the fixture warned about.** If `mirror_package` is quietly reduced to writing one file, `test_the_scan_reports_a_planted_offender_in_the_real_tree` becomes the `tmp_path` test its own docstring at :85-86 rejects, with no test going red. Mitigation: `test_the_mirror_holds_the_same_modules_as_the_live_package`, and Mutation 3 proving it dies.",
                  "**Weakening the guard to close the bug is the failure this whole request exists to prevent.** BUGFIX_REQUEST.md:72 quotes the plan\u0027s own warning that a flapping guard gets deleted rather than fixed, and the stage plan (:170-173) names \u0027weakening the project\u0027s most load-bearing structural guard to stop a fixture flake\u0027 as the trade needing a panel. Nothing in this plan changes `FixedOffsetVisitor`, `EXEMPT_MODULES`, or any rule; the hand-planted-survivor mutation exists to prove that.",
                  "**ADR 0020:92-93 forecloses the tempting message fix.** Teaching `test_no_fixed_offsets.py` to recognise `_guard_scope*_probe.py` is a per-site exemption registry keyed on a filename. If an implementer reaches for it because the residue test feels indirect, they are trading against an accepted ADR and must reopen it rather than slip it in.",
                  "**The monkeypatch at tests/test_leak_guard_scope.py:250-252 breaks on arity.** `lambda: [...]` replaces `guard.scannable_text_files`; once that function takes `repo_root`, the lambda raises TypeError. Red for the wrong reason, and the cheapest wrong fix is deleting the test — which would restore the FileNotFoundError crash its docstring at :243-249 records.",
                  "**`mirror_repo` shells out to git, and CI is the place that will surprise you.** `git init` in a temp dir, ownership/`safe.directory` checks, and default-branch hints all differ between the Windows dev machine and ubuntu-latest. Never `git commit` in the mirror (no identity is configured in CI). If this proves flaky, take the Phase 3 off-ramp and file the leak-guard site separately rather than shipping an intermittently red guard — an intermittently red guard is the exact defect being fixed.",
                  "**Do not build either mirror inside the repo working tree.** A mirror under `var/` or anywhere in the worktree recreates the bug at one remove: `tests/test_grain_contracts.py:364` and the leak guard\u0027s own enumeration would both see it. `tmp_path_factory` only — and the per-session basetemp is precisely what closes mode B.",
                  "**The shared helper\u0027s home is not a free choice.** pyproject.toml:81-88 records a real local-passed/CI-failed import-order split caused by isort inference. `tests/fixtures/` is already a package (tests/fixtures/__init__.py) and `fixtures` is declared first-party; a new top-level module under `tests/` would be classified third-party and churn import ordering. It also avoids introducing this repo\u0027s first `conftest.py` (there is none anywhere today), which would be a structural change well beyond this bug.",
                  "**mypy is strict over `tests/` (pyproject.toml:91-95).** Every new helper, fixture and parameter needs full annotations — `mirror_package(dest: Path) -\u003e Path`, `tmp_path_factory: pytest.TempPathFactory`, `Iterator[str]` on the changed context managers.",
                  "**A rename or a signature change can launder a weakened assertion.** The sibling leak-guard fix\u0027s own review (requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/reviews/implementation-review.md:178) treated any edited assertion message inside a mechanical change as suspect. Read the diff hunk by hunk and keep every pre-existing message as unchanged context.",
                  "**A third reader exists.** `tests/test_grain_contracts.py:75` + `:364-367` walks the same `src/ootp_ai` tree. This plan does not change it (it plants nothing, so it is not part of the cause), but an implementer who \u0027fixes\u0027 the hazard by teaching one reader to ignore probes has left two readers unfixed — which is the structural argument for un-sharing the tree instead."
              ],
    "files_to_touch":  [
                           {
                               "path":  "tests/fixtures/guard_mirror.py",
                               "change":  "NEW. The shared convention, in code: `mirror_package(dest) -\u003e Path` (Phase 1) copies `src/ootp_ai` into `dest/src/ootp_ai` and returns the mirror\u0027s repo root; `mirror_repo(dest) -\u003e Path` (Phase 3) git-inits a mirror carrying this repo\u0027s own `.gitignore` and the directories the leak probes plant into. Plain functions, not pytest fixtures — ABORT_CHILD calls `mirror_package` in a bare child process. Lives under tests/fixtures/ because that package is already declared first-party at pyproject.toml:88."
                           },
                           {
                               "path":  "tests/test_no_fixed_offsets.py",
                               "change":  "Add `repo_root: Path = REPO_ROOT` to `parser_modules()` (:345-354) and `parser_module_violations()` (:357-363); derive the scan root inside and relativise against `repo_root` at :361. `SCAN_ROOT` (:97) stays as the documented production root. No rule, visitor or allowlist change — `EXEMPT_MODULES` (:104-107) and `scan_source` (:339-342) are untouched. Plus a comment recording why the guard deliberately knows no probe filenames."
                           },
                           {
                               "path":  "tests/test_fixed_offset_guard_scope.py",
                               "change":  "`parser_probe` (:81-98) takes `root: Path` first with no default and plants into the mirror; its docstring (:83-91) is rewritten to restate and answer the fidelity argument rather than drop it. A module-scoped `mirror` fixture; four call sites updated (:111, :126, :132, :430) along with the two `PARSER_DIR` assertions at :133-134. Two new tests: `test_the_production_scan_root_is_the_live_package` and `test_the_mirror_holds_the_same_modules_as_the_live_package`. `test_the_module_set_has_a_floor` (:137-150) and `test_an_allowlisted_path_matches_what_the_real_scan_builds` (:176-184) keep calling with no arguments."
                           },
                           {
                               "path":  "tests/test_guard_probe_isolation.py",
                               "change":  "The committed red repro. `ABORT_CHILD` (:46-57) rebuilt around `mirror_package` plus an exit-96 anti-vacuity branch; both tests updated to pass a mirror while `_planted_probes()` (:60-62) and the survivor assertion (:89-94) keep watching the LIVE package. Adds the paired \u0027the mirror scan DOES report it\u0027 assertion at :112, `test_no_probe_residue_is_present_in_the_working_tree` and `test_a_guard_probe_cannot_be_planted_without_naming_a_tree` (Phase 2), extended to the leak-probe sites in Phase 3."
                           },
                           {
                               "path":  "tests/test_no_leaks.py",
                               "change":  "Phase 3. Thread `repo_root: Path = REPO_ROOT` through `git_paths` (:44, cwd at :62), `scannable_text_files` (:70, `REPO_ROOT / rel` at :103), `machine_path_violations` (:139, `relative_to` at :149), `game_data_offenders` (:173) and `is_git_ignored` (:216, cwd at :229). Defaults stay live; the four test functions keep calling with no arguments. No pattern, EXEMPT or keep-set change."
                           },
                           {
                               "path":  "tests/test_leak_guard_scope.py",
                               "change":  "Phase 3. `untracked_file` (:40-53) takes `root: Path` first with no default; ten planting tests move onto a module-scoped mirror repo; the `(REPO_ROOT / \"var\" / \"tmp\").mkdir` calls at :89 and :183 are dropped. The monkeypatch lambda at :250-252 gains the `repo_root` parameter. Adds `test_the_mirror_carries_this_repo_s_ignore_rules` and the `untracked_file` signature assertion. `test_the_candidate_set_has_a_floor` (:224-238), `test_no_ignored_directory_leaks_into_the_candidate_set` (:97-105) and `test_enumeration_yields_no_empty_entries` (:144-155) stay on the real repo."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_PLAN.md",
                               "change":  "NEW — this stage\u0027s deliverable. Opens `\u003e **Status:** planned · created \u003ctoday\u003e · decided · next: implement` per requests/bugfix-requests/README.md:41-45."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md",
                               "change":  "NEW, written in Phase 4 (stage 4\u0027s artifact). Carries the red→green evidence, the mutation results, the unchanged 37-modules/0-violations baseline, and the two refusals (sweep-as-fix; name-aware guard, per ADR 0020:92-93)."
                           },
                           {
                               "path":  "requests/bugfix-requests/README.md",
                               "change":  "Phase 4. The `guard-probe-survives-an-interrupted-run` Index row at :54 moves from `diagnosed` to `fixed`, with the note amended to record the two-site outcome (or the Phase 3 off-ramp, if taken)."
                           },
                           {
                               "path":  "tests/test_grain_contracts.py",
                               "change":  "NOT TOUCHED — listed so the implementer does not touch it. Its `SCAN_ROOT` (:75) and `source_modules()` (:364-367) are a third reader of the same tree, but it plants nothing and is therefore not part of the cause. Sharing the seam with it is a follow-up, not this change."
                           }
                       ],
    "code_references":  [
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:97",
                                "claim":  "`SCAN_ROOT = REPO_ROOT / \"src\" / \"ootp_ai\"` — a module constant with no parameter, so the reader cannot be pointed elsewhere. Read; matches the RCA\u0027s citation exactly."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:345-354 parser_modules()",
                                "claim":  "`sorted(SCAN_ROOT.rglob(\"*.py\"))` with an anti-vacuity assert at :353. Gains `repo_root: Path = REPO_ROOT` in Phase 1. Measured live: returns 37 modules."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:357-363 parser_module_violations()",
                                "claim":  "Takes no root parameter; relativises against REPO_ROOT at :361 and feeds that posix string to `scan_source`. Measured live: returns 0 violations. This is the function the seam is opened on."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:339-342 scan_source()",
                                "claim":  "`FixedOffsetVisitor(filename, exempt=filename in EXEMPT_MODULES)` — exemption is decided by the rel STRING, which is why the seam must be a repo root and not a scan root. Untouched by this change."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:104-107 EXEMPT_MODULES",
                                "claim":  "Exactly two repo-relative posix strings, `src/ootp_ai/parser/lookahead.py` and `src/ootp_ai/parser/primitives.py`. Must come out of a mirror byte-identical. Not edited."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:569-575",
                                "claim":  "`test_no_parser_module_seeks_to_a_fixed_offset()` — the test that goes red on a phantom file. Its message and verdict are unchanged by this fix."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:60",
                                "claim":  "`PARSER_DIR = REPO_ROOT / \"src\" / \"ootp_ai\" / \"parser\"` — kept, because it is what the survivor check and the residue detector must keep watching."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:81-98 parser_probe",
                                "claim":  "The writer: clobber assert at :93, `write_text` at :94, yields `src/ootp_ai/parser/{name}` at :96, unlinks in a `finally` at :97-98. Gains a no-default `root` first parameter; the yielded rel string is preserved so every `rel in v` assertion still matches."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:85-86",
                                "claim":  "The crux docstring — \u0027the scan enumerates the package on disk, so the probe has to exist inside it to be a fair test of what the scan actually reads.\u0027 The plan answers it with a real copied package rather than discarding it."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:137-150 test_the_module_set_has_a_floor",
                                "claim":  "Coverage floor (\u003e= 12; actual 37) over the real package. Keeps calling `guard.parser_modules()` with no arguments — RCA:150 says the fix is vacuous otherwise."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:176-184",
                                "claim":  "`test_an_allowlisted_path_matches_what_the_real_scan_builds` builds `{p.relative_to(REPO_ROOT).as_posix() for p in guard.parser_modules()}` — the second production-observing test that must keep its default call."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:111,126,132,430",
                                "claim":  "The four `parser_probe` call sites planting `_guard_scope_probe.py`, `_guard_scope_clean_probe.py`, `_guard_scope_cleanup_probe.py` and `_guard_scope_folded_probe.py`. All four move onto the mirror."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:46-57 ABORT_CHILD",
                                "claim":  "A source string executed in a child process, hard-coding the fixture call at :55. Invisible to ruff and mypy; must be edited in the same hunk as the signature change or the repro fails for the wrong reason."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:60-62 _planted_probes()",
                                "claim":  "`sorted(PARSER_DIR.glob(\"_guard_scope*_probe.py\"))` over the LIVE package. Unchanged — it is the whole regression guard, and the residue detector reuses it."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:89-94",
                                "claim":  "The survivor assertion of mode A. Must keep asserting emptiness of the live package, not of the mirror."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:111-117",
                                "claim":  "The mode-B test: plants, then calls the default-root `guard.parser_module_violations()`. Gains the paired positive assertion against the mirror root so it cannot pass by planting nothing."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:40-53 untracked_file",
                                "claim":  "The second instance of the class: clobber assert at :48, `write_text` at :49, `finally` unlink at :52-53, target `REPO_ROOT / relative` at :47. Phase 3 gives it a no-default `root`."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:37",
                                "claim":  "`LEAK` — a banned windows-drive-path string assembled at runtime. This is why a survivor here is worse than a parser probe: it carries a banned string into the repo root and poisons the only leak protection there is."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:250-252",
                                "claim":  "`monkeypatch.setattr(guard, \"scannable_text_files\", lambda: [...])` — a zero-arg lambda that breaks with TypeError the moment the guard function takes `repo_root`. Named as a concrete step so it is not discovered as a mystery red."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:224-238 test_the_candidate_set_has_a_floor",
                                "claim":  "The ~134-file floor (asserts \u003e= 80). Stays on the real repo, for the same reason as the module floor."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:44-67 git_paths",
                                "claim":  "`git ls-files -z` with `cwd=REPO_ROOT` at :62, explicit UTF-8/surrogateescape decode at :66. The enumeration seam a `repo_root` parameter threads through."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:70-106 scannable_text_files",
                                "claim":  "Builds `REPO_ROOT / rel` at :103 and filters by suffix. Needs the same parameter, and `machine_path_violations` at :139-165 relativises against REPO_ROOT at :149."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:216-232 is_git_ignored",
                                "claim":  "Its docstring already records this exact hazard class and its resolution — \u0027An interrupted run then leaves the probe behind and reddens a later, unrelated run — a hazard the Phase 9 acceptance panel raised against exactly that pattern (CF24). Asking git about a path costs nothing and cannot litter.\u0027 In-repo precedent for the convention this plan generalises."
                            },
                            {
                                "ref":  "tests/test_grain_contracts.py:75,364-380",
                                "claim":  "A THIRD reader of `src/ootp_ai/**/*.py` that the RCA does not name — `SCAN_ROOT` at :75, `source_modules()` at :364-367, `test_no_module_in_src_joins_on_the_historical_id` at :370-380. It plants nothing, so it is not part of the cause; it is the architectural argument for un-sharing the tree rather than teaching one reader about probe names. Explicitly not touched."
                            },
                            {
                                "ref":  "tests/fixtures/__init__.py",
                                "claim":  "Exists and documents why (mypy would otherwise see a module under two names). Confirms `tests/fixtures/` is a real package and the right home for the shared helper; `tests/test_grain_contracts.py:65` shows the `from fixtures.warehouse import ...` import style to follow."
                            },
                            {
                                "ref":  "pyproject.toml:81-88",
                                "claim":  "`known-first-party = [\"ootp_ai\", \"fixtures\"]`, with the recorded warm-cache-local-vs-cold-CI import-order failure. The reason a new top-level helper module under tests/ is refused and tests/fixtures/ is chosen."
                            },
                            {
                                "ref":  "pyproject.toml:98-108",
                                "claim":  "`testpaths`, `addopts = \"-q --strict-markers --strict-config\"`, one marker, no xdist — why a single session is strictly sequential and CI has never gone red on this. Not changed by the fix."
                            },
                            {
                                "ref":  ".github/workflows/ci.yml:45-57",
                                "claim":  "The four gates — `ruff check .`, `ruff format --check .`, `mypy`, `pytest -m \"not gamedata\"` — that the per-phase local checkpoint mirrors exactly."
                            },
                            {
                                "ref":  "docs/decisions/0020-sanctioned-lookahead-seam.md:92-93",
                                "claim":  "\u0027No per-site exemption registry, ever. A registry lets a guard be satisfied by adding entries, which is how a guard stops being one.\u0027 The grounded refusal of Hardening (b) — a filename-keyed special case inside the guard."
                            },
                            {
                                "ref":  ".claude/agents/data-engineer.md:154-171",
                                "claim":  "`tests/` is in the write-capable subagent\u0027s repo-level deny set, and :171 instructs it to stop and report when the spec\u0027s targets fall inside that set. This change is entirely inside tests/, so the main thread implements it."
                            },
                            {
                                "ref":  "requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/IMPLEMENTATION_REPORT.md:96",
                                "claim":  "The recorded no-op mutant that left all 18 leak-guard tests green before the `machine_path_violations()` seam existed. Reused as the Phase 3 mutation check so the leak guard is proved still able to fail after being re-rooted."
                            }
                        ],
    "open_questions":  [
                           "**Does the leak-guard site land in this change or as its own request?** This plan puts it in, as Phase 3, on the RCA\u0027s Root-tier argument (:152-156) that two independent fixes are the outcome to avoid — with an explicit off-ramp if `mirror_repo`\u0027s `git init` proves unstable in CI. The user should dispose this before Phase 1 starts, because it changes the branch\u0027s size and the PR\u0027s blast radius.",
                           "**Module-scoped or function-scoped mirror?** The plan prescribes module-scoped (`tmp_path_factory`), one copytree per test module — 37 files / 551 KB measured, so function scope is also affordable. Module scope keeps a shared mutable tree *within* a session, which the clobber assert at tests/test_fixed_offset_guard_scope.py:93 still catches loudly. Downgrade to function scope if any cross-test bleed appears.",
                           "**Should `tests/test_grain_contracts.py:364-367` share the same seam?** It is the third reader of `src/ootp_ai` and would be poisoned by a survivor whose body mentioned `historical_id`. It plants nothing, so it is not part of the cause and this plan leaves it alone — but if the convention is to be repo-wide, a follow-up should give it the same `repo_root` parameter.",
                           "**Report-only or sweep-and-report for residue?** The plan chooses report-only (`test_no_probe_residue_is_present_in_the_working_tree` fails and names the file, deletes nothing), because RCA:157-161 says a sweep cannot fix either mode and must not be sold as the fix. If the user wants the sweep\u0027s one real value — cleaning survivors left by older revisions — it should be a documented manual `git clean`-equivalent instruction in the report, not an autouse fixture that silently mutates the tree.",
                           "**Is `test_the_scan_reports_a_planted_offender_in_the_real_tree` still the right NAME after the fix?** The tree is still a real package on disk holding every real module, just a mirrored one, so the plan keeps the name and amends the docstring. If the user reads the name as a lie once the package is a copy, rename it (e.g. `..._in_a_real_package_on_disk`) in Phase 1 rather than later."
                       ]
}
```

## Planner: sequencing - returned: True

```json
{
    "planner":  "sequencing",
    "ok":  true,
    "onboarding_files":  [
                             {
                                 "path":  "requests\\bugfix-requests\\guard-probe-survives-an-interrupted-run\\ROOT_CAUSE_ANALYSIS.md",
                                 "why":  "The decided upstream artifact. Read the two-mode table (:17-21) and the tiered fix posture (:137-164) before writing a line — mode B (a concurrent reader seeing a healthy run\u0027s plant) is what rules out a survivor sweep as \u0027the fix\u0027, and the fidelity argument it hands to this stage (:144-151) is the one real design call."
                             },
                             {
                                 "path":  "tests\\test_fixed_offset_guard_scope.py",
                                 "why":  "The defect site. `parser_probe` at :81-98 writes a real module into `PARSER_DIR` (:60) and unlinks in a `finally` (:97-98); its docstring at :83-91 is the argument this change overturns, and :85-86 is the exact sentence to rewrite. Four plant sites: :111, :126, :132, :430."
                             },
                             {
                                 "path":  "tests\\test_no_fixed_offsets.py",
                                 "why":  "The reader. `SCAN_ROOT` :97, `EXEMPT_MODULES` :104-107 (keyed on repo-relative posix strings), `scan_source` :339-342, `parser_modules` :345-354, `parser_module_violations` :357-363 (relativises with `path.relative_to(REPO_ROOT)` at :361), and the test that goes red, :569-575. This is where the root seam is added."
                             },
                             {
                                 "path":  "tests\\test_guard_probe_isolation.py",
                                 "why":  "The committed red repro (landed in a146b20). Both tests drive the real fixture on purpose (:20-23). `ABORT_CHILD` :46-57 hard-codes the two-argument `parser_probe(name, body)` call and the child\u0027s exit-code assertion at :83-87 explicitly warns that a signature change must be mirrored here — the likeliest way to \u0027fix\u0027 this bug into a different failure."
                             },
                             {
                                 "path":  "tests\\test_leak_guard_scope.py",
                                 "why":  "The second site of the same hazard class (RCA open question 4). `untracked_file` :40-53 with the same name-keyed clobber assert at :48; plants at the repo root (:73), under `requests/bugfix-requests/` (:119-120) and under `var/tmp` (:89-90, :183-184); its probe body carries a deliberately banned machine path built at :37."
                             },
                             {
                                 "path":  "tests\\test_no_leaks.py",
                                 "why":  "The guard that second site poisons — the repo\u0027s only leak protection. `git_paths` :44-67 shells `git ls-files` with `cwd=REPO_ROOT` (:62), so un-sharing that tree means a temp git repo, not just a path parameter. `scannable_text_files` :70-106, `machine_path_violations` :139-165, `game_data_offenders` :173-194, and the `.gitignore` last-match-wins subtlety documented at :180-186."
                             },
                             {
                                 "path":  "tests\\fixtures\\warehouse.py",
                                 "why":  "The precedent for where a shared test harness lives and how it justifies itself: :1-27 explains why it sits in `tests/fixtures/` rather than a `conftest.py` (a reader should see the setup by name, not inherit it). There is no `conftest.py` anywhere in this repo — match that, don\u0027t break it."
                             },
                             {
                                 "path":  "tests\\test_agent_contract.py",
                                 "why":  "`test_deny_set_still_protects_the_guards` :76-81 asserts `tests/` is in the write-capable subagent\u0027s deny set. This entire fix lives in `tests/`, so it CANNOT be delegated to the data-engineer subagent — the primary agent implements it directly. Read this before planning any handoff."
                             },
                             {
                                 "path":  "tests\\test_read_only.py",
                                 "why":  "Shows the live package is read by a THIRD guard: `SRC` :292 and `_source_files()` :344-345 rglob `src/ootp_ai` exactly as the fixed-offset scan does. Also the model for an AST/text guard that is itself seen to fail (:389-402), which Phase 4\u0027s new contract guard should imitate."
                             },
                             {
                                 "path":  ".github\\workflows\\ci.yml",
                                 "why":  "The gates each phase must be green against: `ruff check` :46, `ruff format --check` :49 (the gate the RCA measured going red on a survivor), `mypy` :52, `pytest -m \"not gamedata\"` :57. CI is single-process — `pyproject.toml:98-108` declares no xdist — which is why this hazard has never reddened a build and why local verification is the only proof."
                             }
                         ],
    "architecture_notes":  "SHAPE OF THE DEFECT, IN ONE LINE: a writer and a reader share one filesystem path with no seam between them. `tests/test_fixed_offset_guard_scope.py:60` plants into `REPO_ROOT/src/ootp_ai/parser`; `tests/test_no_fixed_offsets.py:97` scans `REPO_ROOT/src/ootp_ai`; `parser_module_violations()` (:357-363) takes no root parameter, so the fixture has no way to ask for a different tree. Mode A (survivor outliving an interrupted process) and mode B (a second session reading mid-flight) are the same cause observed at two times.\n\nTHE SEAM TO ADD, AND WHY IT IS ONE PARAMETER AND NOT TWO. `scan_source(source, filename)` (:339-342) decides exemption by `filename in EXEMPT_MODULES`, and `EXEMPT_MODULES` (:104-107) holds repo-relative posix strings (`src/ootp_ai/parser/lookahead.py`). `parser_module_violations` builds that string with `path.relative_to(REPO_ROOT).as_posix()` (:361). So the scan needs a REPO ROOT, not a scan root: give both helpers `repo_root: Path = REPO_ROOT`, derive `repo_root / \"src\" / \"ootp_ai\"` inside, and relativise against the same value. A probe tree built as `tmp/src/ootp_ai/parser/x.py` then yields byte-identical violation strings and identical exemption behaviour. Two separate parameters would let them drift and silently exempt nothing — the exact failure `test_an_allowlisted_path_matches_what_the_real_scan_builds` (`test_fixed_offset_guard_scope.py:176-184`) exists to catch.\n\nTHE FIDELITY TRADE, RESOLVED BY COMPENSATION RATHER THAN BY ARGUMENT. `parser_probe`\u0027s docstring (:85-86) claims a `tmp_path` probe proves the scan reads *a* directory rather than *the* directory. That claim is true of an EMPTY tmp_path and false of a faithful COPY of the package: copy `src/ootp_ai` into `tmp/src/ootp_ai` and the scan still rglobs a real tree, opens real files, and reports a real offender found among 37 real modules. What the copy genuinely loses is the assertion that PRODUCTION points at the live package — so buy that back explicitly, with (a) a test that `guard.SCAN_ROOT == REPO_ROOT/\"src\"/\"ootp_ai\"` and that the default-argument call still enumerates it, (b) a copy-equivalence test asserting the copied tree\u0027s repo-relative posix set is identical to the live one (so a `copytree` that silently drops a subpackage fails loudly), and (c) `test_the_module_set_has_a_floor` (`:137-150`) left running against the REAL root, as the RCA requires (:150). Together those are strictly MORE than the live plant asserted, because the live plant never checked where the default root pointed.\n\nWHY THE LEAK-GUARD SITE IS A DIFFERENT ENGINEERING PROBLEM. `test_no_leaks.git_paths` (:44-67) shells out to `git ls-files` with `cwd=REPO_ROOT` (:62), so its scope is defined by a git index and a `.gitignore`, not by a directory walk. Un-sharing it means building a throwaway git repo under `tmp_path` (`git init`, copy the real `.gitignore` verbatim, `git add` a couple of files so `--cached` is non-empty — no commit, so no user identity is needed) and threading a `root` parameter through `git_paths`, `scannable_text_files`, `machine_path_violations` and `game_data_offenders`. The load-bearing subtlety is that several tests depend on the REAL `.gitignore`\u0027s last-match-wins negations (`test_no_leaks.py:180-186`: `tests/fixtures/` and `datasets/` are NOT covered by the game-data block), so the temp repo must carry a verbatim copy and that equivalence must be MEASURED, not assumed. This is the highest-uncertainty work in the change, which is why Phase 1 measures it before Phase 3 depends on it.\n\nTHE THIRD SITE THAT DOES NOT EXIST YET IS THE REAL DELIVERABLE. The RCA\u0027s Root tier (:152-156) asks for one convention so a third site is not invented. Prose cannot hold that; a guard can. `tests/test_read_only.py:361-372` already demonstrates the shape — an AST/text scan over a tree, with the rule itself pinned against a planted offender at :389-402. After Phases 2 and 3 there are exactly ZERO writes in `tests/**` whose target derives from `REPO_ROOT` (measured today: only `test_fixed_offset_guard_scope.py:94`, `test_leak_guard_scope.py:49`, and the two `var/tmp` mkdirs at `test_leak_guard_scope.py:89,183`), so the guard can land with no allowlist at all. That zero is what makes Phase 4 cheap, and it is why Phase 4 must come AFTER both site fixes rather than before.\n\nWHAT THIS CHANGE MUST NOT TOUCH. No file under `src/` changes — the RCA is explicit (:134-135) that the parser, warehouse and report code are not implicated and ADR 0020\u0027s rule is not at issue. The scanning RULE inside `test_no_fixed_offsets.py` (the visitor, `EXEMPT_MODULES`, the residual set) does not change either; only where the scan is pointed. `git diff --name-only` carrying no `src/` path is an objective, checkable acceptance criterion for the whole change and should be run at every checkpoint.\n\nEPISTEMICS. `docs/data-access.md:14` defines the labels, and nothing in that document is load-bearing here: this fix reads no save bytes, no `players.csv`, no export. There is therefore no unconfirmed source-endpoint claim requiring a bytes-verification phase. The analogous unconfirmed claims are repo-mechanical — copy fidelity, temp-git-repo `.gitignore` equivalence, and the cost of both — and Phase 1 verifies all three by measurement before any phase depends on them.",
    "phases":  [
                   {
                       "name":  "Phase 1 — Verify the escape hatch is faithful, before anything depends on it",
                       "goal":  "Prove by measurement that a copied package tree and a throwaway git repo reproduce what the two guards actually read, and add the root seams as pure default-argument additions that change no behaviour. Nothing moves off the live tree yet, so the red repro stays red and this phase is provably a no-op for every existing caller.",
                       "steps":  [
                                     "In `tests/test_no_fixed_offsets.py`, give `parser_modules` (:345-354) and `parser_module_violations` (:357-363) a `repo_root: Path = REPO_ROOT` parameter. Derive the scan root inside as `repo_root / \"src\" / \"ootp_ai\"` and relativise with `path.relative_to(repo_root).as_posix()` at what is today :361. Keep `SCAN_ROOT` (:97) as the module constant and keep the non-vacuity assert at :353 — pointing it at `repo_root`. Do not touch the visitor, `EXEMPT_MODULES` (:104-107), `scan_source` (:339-342) or any rule.",
                                     "Add to `tests/test_fixed_offset_guard_scope.py` a test `test_the_production_scan_root_is_the_live_package`: assert `guard.SCAN_ROOT == REPO_ROOT / \u0027src\u0027 / \u0027ootp_ai\u0027` and that `guard.parser_modules()` (no argument) returns exactly `guard.parser_modules(REPO_ROOT)`. This is compensating assertion (a) from the architecture notes and it must land BEFORE the fidelity is spent.",
                                     "Add `test_a_copied_package_is_the_same_tree_to_the_scan(tmp_path)`: `shutil.copytree(REPO_ROOT/\u0027src\u0027/\u0027ootp_ai\u0027, tmp_path/\u0027src\u0027/\u0027ootp_ai\u0027, ignore=shutil.ignore_patterns(\u0027__pycache__\u0027))`, then assert `{p.relative_to(tmp_path).as_posix() for p in guard.parser_modules(tmp_path)} == {p.relative_to(REPO_ROOT).as_posix() for p in guard.parser_modules()}` — 37 modules today, and an identity assertion rather than a count so ordinary churn never trips it.",
                                     "Add `test_the_copied_tree_reports_a_planted_offender_with_the_real_path_string(tmp_path)`: plant `OFFENDER` (:65-68) at `tmp_path/src/ootp_ai/parser/_probe.py` and assert `parser_module_violations(tmp_path)` names `src/ootp_ai/parser/_probe.py` — proving the exemption-keying string is byte-identical to what the live scan builds. This is the single riskiest assumption in the whole plan; if it fails, stop and re-plan rather than proceeding.",
                                     "MEASURE and write the numbers into the implementation report: wall time of one `copytree` of `src/ootp_ai` (expect single-digit milliseconds for 37 small modules) and the delta in `uv run pytest tests/test_fixed_offset_guard_scope.py` runtime. If a per-test copy costs more than ~1s across the module, record it and revisit function-scoped copying in Phase 2.",
                                     "MEASURE the leak-guard hatch as a throwaway spike (do NOT land production changes for it here): build a temp git repo under `tmp_path` — `git init`, copy `REPO_ROOT/.gitignore` verbatim, `git add` one file — and confirm with `git check-ignore --no-index` that it returns the SAME verdict as the real repo for a fixed list: `var/tmp/x.md` (ignored), `tests/fixtures/x.dat` (NOT ignored), `datasets/x.dat` (NOT ignored), `_probe.md` (NOT ignored), `x.lg` (ignored). Record the five verdicts and the `git init` cost in the report. If any verdict differs, Phase 3 is severable — say so and carry it as a follow-up request rather than improvising.",
                                     "Run `uv run mypy` — every new helper and parameter must be annotated; the config is strict over `src` AND `tests` (`pyproject.toml:93-95`)."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_fixed_offset_guard_scope.py tests/test_no_fixed_offsets.py` is GREEN and the count has grown by exactly the three tests added (32 passed → 35 in the scope module, plus the unchanged fixed-offset module).",
                                          "`uv run pytest tests/test_guard_probe_isolation.py` is STILL RED on both tests, with the same two assertion messages the RCA records (:45-53). A phase that accidentally turned the repro green would mean the repro is not measuring what it claims.",
                                          "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all clean.",
                                          "`git status --porcelain` is clean of any `src/ootp_ai/parser/_guard_scope*_probe.py` after the run, and `git diff --name-only` contains no path under `src/`.",
                                          "The five `git check-ignore` verdicts and the two timing measurements are written down (in the working notes that become the implementation report), not merely observed."
                                      ],
                       "commit_note":  "Checkpoint: hand to the user for `/commit`. Message shape: \"Give the fixed-offset scan a root, and prove a copied tree is the same tree\". Purely additive — every existing call site uses the default and behaves identically, so this phase reverts cleanly with a single revert and leaves the bug exactly as it was."
                   },
                   {
                       "name":  "Phase 2 — Move the fixed-offset probe off the live tree (the fix; the red repro goes green)",
                       "goal":  "Plant every probe into a temp tree that shares nothing with the package the guard scans, so mode A and mode B close together. This is the phase the RCA\u0027s acceptance contract is measured against.",
                       "steps":  [
                                     "Create `tests/fixtures/guard_probe.py` — the one convention, sited beside `tests/fixtures/warehouse.py` and justified in its docstring the way that module justifies itself (:1-27), including why it is NOT a `conftest.py` (this repo has none; a reader should see setup by name). Export two things: `parser_tree(tmp_path)` returning a repo-shaped root with `src/ootp_ai` copied in (`shutil.copytree`, `ignore_patterns(\u0027__pycache__\u0027)`), and `plant(root, relative, body)` — a context manager that asserts the target does not exist, refuses any `root` not under the caller\u0027s `tmp_path`, writes, yields the repo-relative posix string, and unlinks in a `finally`. The refusal is the load-bearing line: it is what makes \u0027planted somewhere shared\u0027 unrepresentable rather than merely discouraged.",
                                     "Rewrite `parser_probe` in `tests/test_fixed_offset_guard_scope.py` (:81-98) to take `tmp_path` and delegate to the fixture module, yielding both the temp repo root and the relative string. Its docstring must be REPLACED, not edited around: the sentence at :85-86 (\"A `tmp_path` fixture cannot serve…\") is now false as written and would leave the code lying to the next reader. Say instead that a faithful COPY preserves what the argument was protecting, and name the three compensating assertions that buy it back.",
                                     "Update the four plant sites to take `tmp_path: Path` and pass the temp root to the scan: :111 (`test_the_scan_reports_a_planted_offender_in_the_real_tree` — rename to `…_in_a_real_tree_on_disk`, since the old name would now overclaim), :126, :132, :430 (`test_the_folded_constant_rule_reports_an_offender_in_the_real_tree`, same rename reasoning).",
                                     "Leave `test_the_module_set_has_a_floor` (:137-150) calling `guard.parser_modules()` with NO argument — the RCA requires it (:150), and a floor measured against a temp copy is a vacuous guard. Add a one-line comment saying so, because it is the exact line a future refactor would \u0027tidy\u0027 into the temp root.",
                                     "Add `test_no_probe_is_ever_written_into_the_live_package(tmp_path)`: drive `parser_probe` and assert `sorted(PARSER_DIR.glob(\u0027_guard_scope*_probe.py\u0027)) == []` both DURING and after the with-block. This is mode B stated as a positive property rather than only as the repro\u0027s absence.",
                                     "Update `ABORT_CHILD` in `tests/test_guard_probe_isolation.py` (:46-57) to the new signature: the child builds its own temp tree, enters the fixture, and still calls `os._exit(97)`. Keep the child driving the REAL fixture — the module\u0027s docstring (:20-23) explains why a self-planting child would be a different, weaker test. Keep the exit-code assertion at :83-87 so a signature drift reports as \"the child never reached the probe\" rather than masquerading as the bug. Its `sys.path.insert` at :51 already puts `\u003crepo\u003e/tests` on the path, so `fixtures.guard_probe` imports (there is a `tests/fixtures/__init__.py`); confirm the child\u0027s temp dir is cleaned by the parent\u0027s `finally` at :95-97.",
                                     "Do NOT weaken or delete either repro test. `test_the_probe_is_removed_even_though_the_scan_read_it` (:130-134) keeps its shape against the temp tree; its old rationale (\"a leftover would break the next lint, mypy and leak-guard run\") is now obsolete and must be restated as \"the fixture still cleans up, and the tree it dirties is disposable\".",
                                     "Run the MUTATION before trusting it: temporarily point `parser_tree` back at `PARSER_DIR` and confirm `tests/test_guard_probe_isolation.py` goes red again with the two original messages; then revert the mutation. Record it — this repo\u0027s memory entry of 2026-08-18 (`.claude/agents/data-engineer-memory.md:351-356`) is exactly the practice of not trusting a guard you have not watched die."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_guard_probe_isolation.py` is GREEN — both `test_a_run_that_dies_inside_the_probe_leaves_no_module_behind` and `test_the_real_scan_does_not_report_a_probe_a_sibling_test_has_planted` pass. This is the RCA\u0027s acceptance contract and the phase\u0027s whole point.",
                                          "`uv run pytest -m \"not gamedata\"` is green across the suite, and `tests/test_fixed_offset_guard_scope.py` still reports every one of its pre-existing tests — the six cry-wolf controls (:229-276) and the eight pinned residuals (:285-447) are untouched in both rule and count.",
                                          "The mode-B check by hand, since it is the mode with no artifact: with `uv run pytest tests/test_fixed_offset_guard_scope.py` running in one shell, run `uv run pytest tests/test_no_fixed_offsets.py` in a second. Both green. Before this phase that is the reproduction; after it, it must be uneventful.",
                                          "`git status --porcelain --untracked-files=all` shows nothing under `src/` at any point, and `uv run ruff format --check .` is clean (the second gate the RCA measured going red, `ROOT_CAUSE_ANALYSIS.md:74-76`).",
                                          "The mutation is recorded: pointing the probe tree back at the live package turns the repro red again."
                                      ],
                       "commit_note":  "Checkpoint: hand to the user for `/commit`. Message shape: \"Plant the fixed-offset probe in a tree the guard does not scan\". This is the shippable fix — if Phases 3-6 are abandoned, the filed bug is closed and the repo is strictly better. Reversible on its own."
                   },
                   {
                       "name":  "Phase 3 — Apply the same treatment to the leak-guard site (the RCA\u0027s Root tier)",
                       "goal":  "Close the second, worse instance of the class: `untracked_file` plants a deliberately banned machine-path string into the live repo root, and the guard it poisons is the only leak protection this public repo has (ADR 0006).",
                       "steps":  [
                                     "Only proceed if Phase 1\u0027s five `git check-ignore` verdicts matched. If any differed, STOP: file the leak site as its own bugfix request and skip to Phase 4 with a single, named, dated allowlist entry. Say which path was taken in the implementation report — a silently-skipped tier reads as \u0027closed\u0027 and the RCA (:130-131) specifically warns against that.",
                                     "In `tests/test_no_leaks.py`, thread `root: Path = REPO_ROOT` through `git_paths` (:44-67, replacing `cwd=REPO_ROOT` at :62), `scannable_text_files` (:70-106, replacing `REPO_ROOT / rel` at :103), `machine_path_violations` (:139-165, replacing the relativise at :149) and `game_data_offenders` (:173-194). Change no pattern, no `keep` set, no `EXEMPT`/`EXEMPT_PREFIXES` — `EXEMPT_PREFIXES` being empty is a decision with its own written cost (:23-31) and is not this change\u0027s to reopen.",
                                     "Add `repo_tree(tmp_path)` to `tests/fixtures/guard_probe.py`: `git init` under `tmp_path`, copy `REPO_ROOT/.gitignore` verbatim, create the directories the tests address (`var/tmp`, `tests/fixtures`, `requests/bugfix-requests`), and `git add` one innocuous file so `--cached` is non-empty. No commit, so no `user.name`/`user.email` is required — record that as the reason, because a future reader will otherwise add an identity config that CI does not have.",
                                     "Rewrite `untracked_file` (:40-53) to take the temp root, reusing the same `plant` helper as Phase 2 — one convention, two call shapes. Delete the two `(REPO_ROOT / \u0027var\u0027 / \u0027tmp\u0027).mkdir(...)` lines at :89 and :183; they become directories of the temp repo.",
                                     "Keep the coverage floor and the junk-directory tests on the REAL repo: `test_the_candidate_set_has_a_floor` (:224-238, `\u003e= 80`) and `test_no_ignored_directory_leaks_into_the_candidate_set` (:97-105) must call the no-argument form, for the same reason the module-set floor does. Add a comment at each saying so.",
                                     "Add the compensating assertion, mirroring Phase 1\u0027s: `test_the_production_enumeration_root_is_the_repo` — the no-argument `git_paths()` runs in `REPO_ROOT`, and its result equals `git_paths(root=REPO_ROOT)`.",
                                     "Add `test_the_temp_repo_ignores_what_the_real_repo_ignores` pinning the five `git check-ignore` verdicts measured in Phase 1, so the temp-repo fidelity is an executable control rather than a claim in a report.",
                                     "Mutation check: point `untracked_file` back at `REPO_ROOT`, confirm the new Phase 4 contract guard (or, before it exists, a hand grep) sees it; revert."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_leak_guard_scope.py tests/test_no_leaks.py` is green with no test lost — all 18-plus scope tests, including the three seen-to-fail tests at :203-238 and the non-ASCII-filename case at :127-141.",
                                          "During and after the run, `git status --porcelain --untracked-files=all` shows no `_leak_guard*` path anywhere in the repo — not at the root (:73), not under `requests/bugfix-requests/` (:119-120), not under `var/tmp`.",
                                          "`grep -n \u0027REPO_ROOT\u0027 tests/test_leak_guard_scope.py` shows no remaining write, mkdir or plant target derived from it; only read-side uses (the floor and junk tests).",
                                          "`uv run pytest -m \"not gamedata\"` green; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean.",
                                          "The runtime cost of `git init` per test is measured and recorded; if the module\u0027s total runtime grew by more than ~5s, a session-scoped temp repo with per-test subdirectories is adopted instead and the reason is written down."
                                      ],
                       "commit_note":  "Checkpoint: hand to the user for `/commit`. Message shape: \"Probe the leak guard in a repo it does not protect\". Independently revertible: reverting it restores the old fixture without disturbing Phase 2\u0027s fix. This is the phase to sever into its own request if Phase 1\u0027s measurement went the wrong way."
                   },
                   {
                       "name":  "Phase 4 — One convention, enforced: no test may write into the tree a guard reads",
                       "goal":  "Make a third instance of the hazard class unrepresentable rather than merely discouraged. This is the executable form of the RCA\u0027s Root tier (:152-156), and after Phases 2 and 3 it can land with no allowlist at all.",
                       "steps":  [
                                     "Create `tests/test_probe_isolation_contract.py`. Its rule: within `tests/**/*.py`, a write call (`.write_text(`, `.write_bytes(`, `.touch(`, `.mkdir(`, `.unlink(`) whose target derives from a name bound to `REPO_ROOT` — directly, or through a module-level constant like `PARSER_DIR = REPO_ROOT / ...` — is a violation. Implement it AST-first, not by grep: `tests/test_read_only.py:396-402` shows why (a string literal such as `.write_bytes(payload)` inside an assertion at :398 must not fire), and `tests/test_no_fixed_offsets.py`\u0027s visitor already demonstrates the derived-name tracking pattern to imitate.",
                                     "Expose the rule through a `scan_source(source, filename)`-shaped seam, exactly as `test_no_fixed_offsets.py:339-342` and `test_no_leaks.py:139-165` do — so the guard can be asserted to REPORT, not merely to enumerate. This repo has been bitten twice by guards that passed while reading nothing (`test_fixed_offset_guard_scope.py:9-14`); do not add a third.",
                                     "Pin the guard against a planted offender string (the exact shape `test_fixed_offset_guard_scope.py:92-94` used to have) AND against cry-wolf controls taken from real lines: a write under `tmp_path` (`tests/test_snapshot_semantics.py:119-124`), a write under a fixture-built save root (`tests/test_save_enumerator.py:39-44`), and a `REPO_ROOT`-derived READ (`tests/test_repo_structure.py:36`, `tests/test_no_leaks.py:158`). A guard that fired on a read would be deleted within a week.",
                                     "Exempt exactly one file — the contract module itself, which necessarily contains the strings it bans — following `test_no_leaks.py:21`\u0027s single-entry `EXEMPT` precedent, and assert the exemption set has exactly one entry the way `test_the_allowlist_is_exactly_two_entries` (`test_fixed_offset_guard_scope.py:156-167`) does.",
                                     "Add `test_no_probe_survivor_is_present_in_the_package` — the honest form of the RCA\u0027s hardening (a): scan `src/ootp_ai/parser/` for `_guard_scope*_probe.py` and fail with \"a test fixture from an older revision survived an interrupted run; delete it\". It DETECTS and REPORTS rather than sweeping. Its only value is survivors from revisions before Phase 2, which no design change can reach retroactively — say that in the docstring so nobody later mistakes it for the fix.",
                                     "Run the mutation: make the rule return `[]` unconditionally and confirm the seen-to-fail tests die; then restore. A guard nobody has watched fail is not yet a guard."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_probe_isolation_contract.py` is green with ZERO allowlist entries beyond the module\u0027s own self-exemption — the objective proof that Phases 2 and 3 actually removed every site.",
                                          "The guard is seen to fail: the planted-offender test reports, the three cry-wolf controls do not, and the no-op mutation was watched to kill the module.",
                                          "Re-introducing `path.write_text(body)` against `PARSER_DIR` in a scratch copy of the old fixture makes the guard red with a message naming the file and line.",
                                          "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all clean.",
                                          "`git diff --name-only` still contains no path under `src/` — the guard is a test, and this change touches no production code at all."
                                      ],
                       "commit_note":  "Checkpoint: hand to the user for `/commit`. Message shape: \"Guard the guards: no test writes into a tree a guard reads\". Fully severable — the bug is already fixed without it; this is what stops the third site."
                   },
                   {
                       "name":  "Phase 5 — The two gated hardening options, disposed in the open",
                       "goal":  "Settle the two calls the RCA explicitly refused to make (:157-164) with a written recommendation and the user\u0027s disposition, rather than letting them arrive by drift.",
                       "steps":  [
                                     "Option (a), the session-scoped sweep that removes survivors. RECOMMEND AGAINST the removing form and note why concretely: this repo has no `conftest.py` anywhere, and `tests/fixtures/warehouse.py:1-6` states the reason (a reader should see setup by name rather than inherit it), so an autouse session fixture would be a structural first. Phase 4\u0027s detect-and-report test delivers the same retroactive coverage without silently tidying evidence. Present it; let the user dispose.",
                                     "Option (b), teaching `test_no_fixed_offsets.py` to recognise a `_guard_scope*_probe.py` name and fail with a friendlier message. RECOMMEND AGAINST, and state the reason as a trade rather than a taste: after Phase 2 no probe name can ever reach the package, so the branch would be dead code inside the enforcement of the project\u0027s most load-bearing structural ban (ADR 0020), and `EXEMPT_MODULES`\u0027s own comment (`test_no_fixed_offsets.py:99-103`) treats every widening of that guard as a decision to be made against a failing test. The honest message is already delivered from outside, by Phase 4\u0027s survivor test.",
                                     "If the user disposes either one FOR, implement it in this phase alone so it stays independently revertible, and add its own seen-to-fail control — a sweep that removed nothing and reported nothing would look identical to a clean tree.",
                                     "Record both dispositions verbatim in the implementation report, including the ones declined, so the trail survives the way `ROOT_CAUSE_ANALYSIS.md:166-170` hands them over."
                                 ],
                       "acceptance":  [
                                          "Both options carry a written recommendation with its reason, and a recorded user disposition — accepted or declined. A phase that quietly implemented neither and said nothing has failed this phase even though the suite is green.",
                                          "If anything was implemented, it has its own test AND its own watched failure, and `uv run pytest -m \"not gamedata\"` stays green.",
                                          "If both were declined, the suite is unchanged and the phase\u0027s only artifact is the recorded disposition — a legitimate, zero-diff outcome that still gets written down."
                                      ],
                       "commit_note":  "Checkpoint: hand to the user for `/commit` only if code landed; otherwise the dispositions ride along with Phase 6\u0027s documentation commit. Message shape: \"Decline the name-aware guard message, and say why\"."
                   },
                   {
                       "name":  "Phase 6 — Truth up the record and close the request",
                       "goal":  "Leave the repo\u0027s documentation describing the repo that now exists, and advance the bugfix track\u0027s artifacts so the Index and the status blockquotes agree with what landed.",
                       "steps":  [
                                     "Write `requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md`: red-to-green evidence for both repro tests, the Phase 1 measurements (copy cost, the five `git check-ignore` verdicts, the runtime deltas), every mutation watched to fail, the Phase 5 dispositions, and whether the leak-guard tier landed here or was severed.",
                                     "Set the Index row for `[guard-probe-survives-an-interrupted-run]` in `requests/bugfix-requests/README.md:54` from `diagnosed` to `fixed`, and update the status blockquotes at the head of `BUGFIX_REQUEST.md:1` and `ROOT_CAUSE_ANALYSIS.md:1` to the README\u0027s grammar (`README.md:41-45`).",
                                     "Add one line to `tests/fixtures/README.md` covering the harness module. That README\u0027s \"What belongs here\" (:30-36) currently describes DATA fixtures only, while `warehouse.py` is already a harness — this makes the exception explicit rather than leaving a second undocumented one.",
                                     "APPEND a dated entry to `.claude/agents/data-engineer-memory.md` — append-only by that file\u0027s own rule (`tests/test_agent_contract.py:21-28` records why the length ceiling was removed). The 2026-08-18 entry at :351-356 prescribes \"a planted offender written to disk and removed in `finally`\"; the new entry refines it (`measured`): plant on disk, but never in a tree another guard reads — a `finally` is not a guarantee when the failure mode is the process not surviving to run it. Do not edit the old entry; a ledger is a log.",
                                     "Do NOT write a new ADR and do NOT amend ADR 0020: the ban\u0027s rule, its allowlist and its residuals are untouched, and 0020\u0027s only reference to the scope module (`:96`) — that it pins every residual as an executable control — remains true. Say this explicitly in the report so the next reader does not go looking for a missing decision record.",
                                     "Check whether `requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`\u0027s follow-up 3 (the Phase 10 record of this sighting) should be marked resolved, and let `/update-docs` judge the rest of the doc surface.",
                                     "Watch for the forward-reference trap: `tests/test_doc_links.py` scans live (non-`_done/`) artifact bodies, so any path this plan or the report names that does not yet exist on disk must sit inside a fenced code block."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_doc_links.py tests/test_repo_structure.py tests/test_agent_contract.py` green — every path named in the new artifacts resolves, and the appended memory entry carries a valid epistemic label (`test_memory_entries_carry_an_epistemic_label`, `tests/test_agent_contract.py:84-95`).",
                                          "The Index row, both status blockquotes and the new plan/report headers all agree, and `/commit`\u0027s doc-drift step raises nothing further.",
                                          "Full final gate, run in one pass on a clean tree: `uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` — all green, and `git status --porcelain --untracked-files=all` clean.",
                                          "`git diff --name-only main` lists no path under `src/`, confirming the RCA\u0027s \"Not implicated\" (:134-135) held for the whole change."
                                      ],
                       "commit_note":  "Final checkpoint: hand to the user for `/commit`, then ask before opening the PR — the PR and any merge stay the user\u0027s (CLAUDE.md). Never push `main`, never force-push, never amend."
                   }
               ],
    "testing":  "HOW THE WHOLE THING IS VERIFIED. The acceptance contract is the bugfix track\u0027s, not a feature\u0027s: the red repro goes green, a regression test is left behind, nothing else regresses (`requests/bugfix-requests/README.md:24-26`).\n\nRed-to-green, the headline: `uv run pytest tests/test_guard_probe_isolation.py` is RED today on both tests with the two messages recorded at `ROOT_CAUSE_ANALYSIS.md:45-53`, and must be GREEN after Phase 2. Phase 1 must NOT turn it green — that is an acceptance criterion in its own right, because a seam that accidentally fixed the bug would mean the repro is not measuring what it claims.\n\nPer-phase pytest selectors: Phase 1 `uv run pytest tests/test_fixed_offset_guard_scope.py tests/test_no_fixed_offsets.py` (green) plus `uv run pytest tests/test_guard_probe_isolation.py` (still red); Phase 2 `uv run pytest tests/test_guard_probe_isolation.py` (green) then `uv run pytest -m \"not gamedata\"`; Phase 3 `uv run pytest tests/test_leak_guard_scope.py tests/test_no_leaks.py`; Phase 4 `uv run pytest tests/test_probe_isolation_contract.py`; Phase 5 the selector for whatever was disposed FOR, or none; Phase 6 `uv run pytest tests/test_doc_links.py tests/test_repo_structure.py tests/test_agent_contract.py`. Every phase also ends on the full local gate: `uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`. The format check is not optional here — it is the second gate the RCA measured going red on a survivor (`ROOT_CAUSE_ANALYSIS.md:74-76`) and CI runs it at `.github/workflows/ci.yml:49`.\n\nTHE MODE-B CHECK HAS NO ARTIFACT, SO IT MUST BE RUN BY HAND ONCE. `tests/test_guard_probe_isolation.py:100-117` reproduces mode B sequentially, which is sound and deterministic — but the sighting it models is two pytest sessions against one working tree, and that is worth performing once at Phase 2\u0027s checkpoint: run `uv run pytest tests/test_fixed_offset_guard_scope.py` in one shell and `uv run pytest tests/test_no_fixed_offsets.py` in a second, overlapping. Before Phase 2 that is the reproduction; after it, it must be uneventful. Record the result.\n\nSEEN TO FAIL, EVERY TIME. This repo\u0027s standing practice — recorded as a `measured` memory entry at `.claude/agents/data-engineer-memory.md:351-356`, and argued at `tests/test_fixed_offset_guard_scope.py:9-14` where a no-op mutant left all 18 leak-guard tests green — is that a guard is not trusted until it has been watched to die. Three mutations are prescribed and must be recorded in the report: point the probe tree back at `PARSER_DIR` (Phase 2\u0027s repro must go red again); point `untracked_file` back at `REPO_ROOT` (Phase 3); make Phase 4\u0027s rule return `[]` (its seen-to-fail tests must die). None of these is a code change that ships — each is applied, observed, reverted.\n\nREGRESSION SAFETY, IN ORDER OF STRENGTH. (1) No file under `src/` changes: `git diff --name-only` carrying no `src/` path is checkable at every checkpoint and is the strongest single statement that no parser, warehouse or report behaviour can have moved. It also means the `gamedata`-marked suites — which need a local OOTP install and a populated MySQL that CI does not have — cannot regress, so their absence from the local gate is sound rather than convenient. (2) The scanning RULE is untouched: `tests/test_fixed_offset_guard_scope.py`\u0027s six cry-wolf controls (:229-276) and eight pinned residuals (:285-447) must still pass and still be present in the same number; a phase that quietly dropped one has widened the fixed-offset ban\u0027s blind spot while claiming to fix a fixture. (3) `test_the_module_set_has_a_floor` (:145) and `test_the_candidate_set_has_a_floor` (`tests/test_leak_guard_scope.py:233`) keep running against the REAL roots — the RCA names the first explicitly (:150), and a floor measured against a temp copy is exactly the vacuous guard both were written to prevent. (4) The three compensating assertions (production scan root is the live package; production enumeration root is the repo; the copied tree\u0027s module set is identical to the live one) are what stop the fidelity loss being real rather than nominal.\n\nWHAT THE SUITE CANNOT PROVE, STATED PLAINLY. Nothing here proves a probe never survives on a machine running a revision from BEFORE Phase 2 — no design change is retroactive. Phase 4\u0027s survivor-detection test is the only coverage of that case, and it reports rather than sweeps on purpose.",
    "risks":  [
                  "THE SIGNATURE TRAP, AND IT IS THE MOST LIKELY WAY THIS FIX GOES WRONG. `ABORT_CHILD` at `tests/test_guard_probe_isolation.py:46-57` hard-codes `parser_probe(\"_guard_scope_abort_probe.py\", OFFENDER)`. Change the fixture\u0027s signature without changing the child and the child dies on a TypeError, exits 1, and the assertion at :83-87 fails with \"the child never reached the probe\" — a message that looks like a broken test rather than the bug, and which an implementer under time pressure may \u0027fix\u0027 by relaxing the exit-code check. The test warns about this in its own words; keep the exit-code assertion, update the child, and never delete the child\u0027s use of the real fixture.",
                  "A COPIED TREE CAN GO STALE INVISIBLY. If `copytree` silently misses a subpackage — an ignore pattern that grows, a new directory added under `src/ootp_ai` — the probe still gets reported and every test stays green while the fidelity claim quietly becomes false. Mitigation is the identity assertion in Phase 1 (the copied tree\u0027s repo-relative posix set EQUALS the live one, currently 37 modules), asserted as a set rather than as a count so churn never trips it and a drop always does.",
                  "THE EXEMPTION STRING IS THE SILENT FAILURE MODE. `scan_source` (`tests/test_no_fixed_offsets.py:339-342`) keys exemption on `filename in EXEMPT_MODULES` — repo-relative posix strings. Relativise against the wrong root and every path becomes `parser/lookahead.py` instead of `src/ootp_ai/parser/lookahead.py`, so the two sanctioned modules stop being exempt and the tree-is-clean test goes red for a reason nobody would diagnose from its message — or, worse, a backslash form exempts NOTHING and the guard silently widens. One `repo_root` parameter used for both the walk and the relativise is the mitigation; `test_an_allowlisted_path_matches_what_the_real_scan_builds` (`tests/test_fixed_offset_guard_scope.py:176-184`) is the control that catches it.",
                  "THIS WORK CANNOT BE DELEGATED TO THE WRITE-CAPABLE SUBAGENT. `tests/` is in that agent\u0027s deny set, asserted at `tests/test_agent_contract.py:76-81`, and every file this change touches except the documentation is under `tests/`. The primary agent implements it directly. An implementer who spawns the data-engineer for this will either get a refusal or a violation of ADR 0009\u0027s contract.",
                  "THE LEAK-GUARD TEMP REPO DEPENDS ON `.gitignore` LAST-MATCH-WINS SEMANTICS THAT ARE EASY TO BREAK BY ACCIDENT. `tests/test_no_leaks.py:180-186` records the measurement: `tests/fixtures/` and `datasets/` are NOT covered by the game-data block because the `!` negations below it are later rules. A temp repo built with a hand-written or trimmed `.gitignore` would give different verdicts and turn `test_the_game_data_guard_sees_an_untracked_fixture` (`tests/test_leak_guard_scope.py:165-178`) into a test of the fixture rather than of the guard. Copy the real file verbatim, and pin the five verdicts as an executable control.",
                  "COST CREEP IN THE INNER LOOP. A `copytree` per test across four plant sites plus a `git init` per test across roughly fourteen leak-guard tests is small but not free, and a suite that gets slower gets run less often — which is how a guard stops protecting anything. Measure in Phase 1, record the numbers, and switch to a session-scoped pristine tree with per-test subdirectories only if the measurement demands it, never speculatively.",
                  "THE FIDELITY LOSS IS REAL AND MUST NOT BE PAPERED OVER. `parser_probe`\u0027s docstring at `tests/test_fixed_offset_guard_scope.py:85-86` makes an argument the RCA itself calls strong (:145-147). The copy answers most of it but not all: nothing after this change plants an offender in the actual `src/ootp_ai/parser/`. If the three compensating assertions are skipped as busywork, the change trades a fixture flake for a weaker guard — exactly the trade the intake\u0027s stage plan said needed a panel (`BUGFIX_REQUEST.md:168-173`).",
                  "A GUARD THAT KNOWS ABOUT ITS OWN TEST IS A ONE-WAY DOOR. If Phase 5(b) is disposed FOR, `test_no_fixed_offsets.py` gains a name-aware branch inside the enforcement of the project\u0027s most load-bearing structural ban, and after Phase 2 that branch is unreachable dead code. `EXEMPT_MODULES`\u0027s own comment (:99-103) treats any widening of this guard as a decision made against a failing test; make it that way or decline it.",
                  "THE PLAN\u0027S OWN FORWARD REFERENCES CAN BREAK CI. `tests/test_doc_links.py` scans live artifact bodies and is a blocking check. `tests/fixtures/guard_probe.py` and `tests/test_probe_isolation_contract.py` do not exist until Phases 2 and 4, so every mention of them in the plan and the report must sit inside a fenced code block until they land.",
                  "DECLARING THE LEAK SITE \u0027CLOSED\u0027 WITHOUT DOING IT. The RCA is explicit (:130-131) that a fix aimed at `parser_probe` alone leaves the leak site open and that the record should say so rather than read as closed. If Phase 3 is severed on Phase 1\u0027s measurement, it must be severed loudly — a new bugfix request and an Index row — not silently omitted from the report."
              ],
    "files_to_touch":  [
                           {
                               "path":  "tests/test_no_fixed_offsets.py",
                               "change":  "Phase 1. Add `repo_root: Path = REPO_ROOT` to `parser_modules` (:345-354) and `parser_module_violations` (:357-363); derive the walk root as `repo_root/\u0027src\u0027/\u0027ootp_ai\u0027` and relativise against the same value (today\u0027s :361). Keep `SCAN_ROOT` (:97) and the non-vacuity assert (:353). No change to the visitor, `EXEMPT_MODULES` (:104-107), `scan_source` (:339-342), or any residual."
                           },
                           {
                               "path":  "tests/fixtures/guard_probe.py",
                               "change":  "NEW, Phases 2-3. The one convention: `parser_tree(tmp_path)` (copy `src/ootp_ai` into a repo-shaped temp root), `repo_tree(tmp_path)` (git init + verbatim `.gitignore` + `git add`), and `plant(root, relative, body)` — assert-not-exists, refuse any root not under tmp_path, write, yield the repo-relative posix string, unlink in a `finally`. Docstring justifies its siting the way `tests/fixtures/warehouse.py:1-27` does."
                           },
                           {
                               "path":  "tests/test_fixed_offset_guard_scope.py",
                               "change":  "Phases 1-2. Rewrite `parser_probe` (:81-98) to take `tmp_path` and delegate; REPLACE the docstring claim at :85-86. Thread `tmp_path` through the four plant sites (:111, :126, :132, :430) and rename the two \u0027…in_the_real_tree\u0027 tests to \u0027…in a real tree on disk\u0027. Leave `test_the_module_set_has_a_floor` (:137-150) on the real root, with a comment saying why. Add: production-scan-root, copy-equivalence, planted-offender-in-the-copy, and no-probe-in-the-live-package tests."
                           },
                           {
                               "path":  "tests/test_guard_probe_isolation.py",
                               "change":  "Phase 2. Update `ABORT_CHILD` (:46-57) to the new fixture signature — the child builds its own temp tree, still `os._exit(97)`. Keep the exit-code assertion (:83-87), the survivor assertion (:89-94) and the parent\u0027s cleanup `finally` (:95-97). Do not weaken either test; both must go green on the fix alone."
                           },
                           {
                               "path":  "tests/test_no_leaks.py",
                               "change":  "Phase 3. Thread `root: Path = REPO_ROOT` through `git_paths` (:44-67, the `cwd=REPO_ROOT` at :62), `scannable_text_files` (:70-106, the `REPO_ROOT / rel` at :103), `machine_path_violations` (:139-165, the relativise at :149) and `game_data_offenders` (:173-194). No pattern, `keep`-set, `EXEMPT` (:21) or `EXEMPT_PREFIXES` (:31) change."
                           },
                           {
                               "path":  "tests/test_leak_guard_scope.py",
                               "change":  "Phase 3. Rewrite `untracked_file` (:40-53) to plant into `repo_tree(tmp_path)` via the shared `plant`. Delete the two live-repo mkdirs at :89 and :183. Keep `test_the_candidate_set_has_a_floor` (:224-238) and `test_no_ignored_directory_leaks_into_the_candidate_set` (:97-105) on the real repo. Add the production-enumeration-root and five-verdict `.gitignore` equivalence tests."
                           },
                           {
                               "path":  "tests/test_probe_isolation_contract.py",
                               "change":  "NEW, Phase 4. AST guard: no write in `tests/**` may target a `REPO_ROOT`-derived path (directly or via a module constant). A `scan_source`-shaped seam so it can be asserted to REPORT; a planted offender; three cry-wolf controls drawn from real lines; a one-entry self-exemption with the count asserted. Plus `test_no_probe_survivor_is_present_in_the_package`, which detects and reports pre-Phase-2 survivors with an honest message."
                           },
                           {
                               "path":  "tests/fixtures/README.md",
                               "change":  "Phase 6. One line under \u0027What belongs here\u0027 (:30-36) covering harness modules — the README describes data fixtures only today, while `warehouse.py` is already an undocumented exception."
                           },
                           {
                               "path":  ".claude/agents/data-engineer-memory.md",
                               "change":  "Phase 6. APPEND (never edit) a dated `measured` entry refining the 2026-08-18 entry at :351-356: plant an offender on disk, but never in a tree another guard reads — a `finally` is not a guarantee when the failure mode is the process not surviving to run it. Must carry a valid epistemic label or `tests/test_agent_contract.py:84-95` goes red."
                           },
                           {
                               "path":  "requests/bugfix-requests/README.md",
                               "change":  "Phase 6. Set the Index row Stage cell for `[guard-probe-survives-an-interrupted-run]` (:54) from `diagnosed` to `fixed`; if the leak-guard tier was severed, add its new row."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_PLAN.md",
                               "change":  "Stage-3 deliverable. Opens `\u003e **Status:** planned · created \u003ctoday\u003e · decided · next: implement`. Any path that does not yet exist on disk goes inside a fenced code block — `tests/test_doc_links.py` is a blocking CI check."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md",
                               "change":  "Phase 6. Red-to-green evidence, the Phase 1 measurements, the three watched mutations, the Phase 5 dispositions (including the declined ones), and whether the leak-guard tier landed or was severed."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md",
                               "change":  "Phase 6. Status blockquote (:1) advanced to the README\u0027s grammar (`requests/bugfix-requests/README.md:41-45`)."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md",
                               "change":  "Phase 6. Status blockquote (:1) advanced. The body is decided and is not re-opened."
                           }
                       ],
    "code_references":  [
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:60",
                                "claim":  "`PARSER_DIR = REPO_ROOT / \"src\" / \"ootp_ai\" / \"parser\"` — the writer\u0027s path, and the shared state at the heart of the defect."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:81-98",
                                "claim":  "`parser_probe` writes a real module into the live package (:94) and unlinks in a `finally` (:97-98). Phase 2 rewrites it to take `tmp_path`."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:85-86",
                                "claim":  "The docstring sentence claiming a `tmp_path` fixture cannot serve. It is the argument the plan overturns with a faithful COPY plus three compensating assertions, and it must be replaced rather than left standing."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:93",
                                "claim":  "`assert not path.exists(), f\"{name} already exists; refusing to clobber it\"` — the name-keyed clobber guard the RCA measured as firing only in a run that collects this module, and as structurally blind to mode B."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:111",
                                "claim":  "First plant site, `_guard_scope_probe.py` with OFFENDER — the test the whole module exists for; gains `tmp_path` and a name that no longer overclaims \u0027the real tree\u0027."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:126",
                                "claim":  "Second plant site, `_guard_scope_clean_probe.py` with INNOCENT — the not-crying-wolf half."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:132",
                                "claim":  "Third plant site, `_guard_scope_cleanup_probe.py`; its stated rationale (a leftover breaks the next lint/mypy/leak-guard run) becomes obsolete once the tree is disposable and must be restated."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:137-150",
                                "claim":  "`test_the_module_set_has_a_floor` calls `guard.parser_modules()` at :145 and must keep running against the REAL root — the RCA requires it at :150, and a floor over a temp copy is a vacuous guard."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:176-184",
                                "claim":  "`test_an_allowlisted_path_matches_what_the_real_scan_builds` — the control that catches a wrong relativise root turning the two exemptions into strings that exempt nothing."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:430",
                                "claim":  "Fourth plant site, `_guard_scope_folded_probe.py` — the folded-constant rule\u0027s seen-to-fail-on-disk test."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:97",
                                "claim":  "`SCAN_ROOT = REPO_ROOT / \"src\" / \"ootp_ai\"` — the reader\u0027s path. Stays as the module constant; the walk root is derived from the new `repo_root` parameter."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:104-107",
                                "claim":  "`EXEMPT_MODULES` holds two repo-relative posix strings, which is why the seam must be a repo root rather than a scan root."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:339-342",
                                "claim":  "`scan_source(source, filename)` decides exemption by `filename in EXEMPT_MODULES` — the model for Phase 4\u0027s report-not-just-enumerate seam."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:345-354",
                                "claim":  "`parser_modules()` is `sorted(SCAN_ROOT.rglob(\"*.py\"))` with a non-vacuity assert at :353. Takes `repo_root` in Phase 1. Enumerates 37 modules today."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:357-363",
                                "claim":  "`parser_module_violations()` takes no root parameter — the missing seam — and builds the exemption key with `path.relative_to(REPO_ROOT).as_posix()` at :361."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:569-575",
                                "claim":  "`test_no_parser_module_seeks_to_a_fixed_offset` — the test that goes red on a phantom file. Its rule and message are unchanged by this fix."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:46-57",
                                "claim":  "`ABORT_CHILD` hard-codes the two-argument `parser_probe` call and `os._exit(97)`. Phase 2 must update it in lockstep with the signature."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:83-87",
                                "claim":  "The child\u0027s exit-code assertion, whose message says outright that a changed fixture signature must be mirrored in ABORT_CHILD. Keep it; it is what separates a broken test from the bug."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:100-117",
                                "claim":  "`test_the_real_scan_does_not_report_a_probe_a_sibling_test_has_planted` — mode B made deterministic without a second process. The green form of this test is the fix\u0027s proof."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:40-53",
                                "claim":  "`untracked_file` — the same hazard shape at the second site: a real write into the live repo (:49), a `finally` unlink (:53), and the same name-keyed clobber assert at :48."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:37",
                                "claim":  "`LEAK` is a deliberately banned machine-path string built at runtime, so a survivor from this fixture reddens the repo\u0027s only leak protection — the reason the RCA calls this site worse."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:89",
                                "claim":  "`(REPO_ROOT / \"var\" / \"tmp\").mkdir(parents=True, exist_ok=True)` — a live-repo write to delete in Phase 3; the twin at :183 goes with it."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:119-120",
                                "claim":  "The nested plant under `requests/bugfix-requests/` — proof the hazard is not confined to the repo root and that the temp repo must reproduce nested paths."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:224-238",
                                "claim":  "`test_the_candidate_set_has_a_floor` (`\u003e= 80`) must stay on the real repo, the leak-guard twin of the module-set floor."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:44-67",
                                "claim":  "`git_paths` shells `git ls-files` with `cwd=REPO_ROOT` at :62 — the reason un-sharing this site needs a temp GIT repo, not merely a path parameter."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:70-106",
                                "claim":  "`scannable_text_files` resolves `REPO_ROOT / rel` at :103 and filters by suffix; gains the `root` parameter in Phase 3."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:180-186",
                                "claim":  "The measured `.gitignore` last-match-wins finding — `tests/fixtures/` and `datasets/` are NOT covered by the game-data block. The temp repo must carry the real `.gitignore` verbatim or this property silently inverts."
                            },
                            {
                                "ref":  "tests/test_read_only.py:292",
                                "claim":  "`SRC = ... / \"src\" / \"ootp_ai\"` — a THIRD guard whose scan root is the live package, alongside the fixed-offset scan and mypy/ruff. More readers of the shared tree than the RCA enumerates, and further reason to un-share rather than sweep."
                            },
                            {
                                "ref":  "tests/test_read_only.py:389-402",
                                "claim":  "`test_the_write_guards_still_catch_a_real_offender` — the template for Phase 4\u0027s seen-to-fail control, and the demonstration (its `.write_bytes(payload)` string at :398) of why the new guard must be AST-based rather than a grep."
                            },
                            {
                                "ref":  "tests/test_agent_contract.py:76-81",
                                "claim":  "`test_deny_set_still_protects_the_guards` asserts `tests/` sits in the write-capable subagent\u0027s deny set — so this fix, which is entirely under `tests/`, cannot be delegated to it."
                            },
                            {
                                "ref":  "tests/test_agent_contract.py:84-95",
                                "claim":  "`test_memory_entries_carry_an_epistemic_label` — the appended memory entry in Phase 6 must carry one of measured/verified/inferred/assumed/unconfirmed or CI goes red."
                            },
                            {
                                "ref":  "tests/fixtures/warehouse.py:1-27",
                                "claim":  "The precedent for a shared harness in `tests/fixtures/` and its stated reason for not being a `conftest.py`. There is no `conftest.py` anywhere in this repo — the new `guard_probe.py` follows this siting."
                            },
                            {
                                "ref":  "tests/fixtures/__init__.py",
                                "claim":  "`tests/fixtures/` is a real package, and `pyproject.toml:88` declares `fixtures` first-party for isort — so `from fixtures.guard_probe import …` works from a test module and from the spawned abort child, which already puts `\u003crepo\u003e/tests` on `sys.path`."
                            },
                            {
                                "ref":  "pyproject.toml:98-108",
                                "claim":  "`testpaths`, `addopts = \"-q --strict-markers --strict-config\"`, and exactly one marker (`gamedata`) — no xdist, no parallel plugin. This is why the hazard has never reddened CI, and why `--strict-markers` makes inventing a second marker a hard collection error."
                            },
                            {
                                "ref":  ".github/workflows/ci.yml:45-57",
                                "claim":  "The four gates each phase must satisfy locally: `ruff check` (:46), `ruff format --check` (:49), `mypy` (:52), `pytest -m \"not gamedata\"` (:57). The format check is the second gate the RCA measured going red on a survivor."
                            },
                            {
                                "ref":  "docs/decisions/0020-sanctioned-lookahead-seam.md:96",
                                "claim":  "The ADR\u0027s only reference to the scope module — that it pins every named residual as an executable control. That remains true after this change, which is why no ADR amendment is needed and why dropping a residual would falsify a live decision record."
                            },
                            {
                                "ref":  "docs/data-access.md:14",
                                "claim":  "The epistemic-label definitions (`unconfirmed` = nobody has looked; a task, not a fact). Cited to record that NO claim in that document is load-bearing here — this fix reads no save bytes — so no bytes-verification phase is required, only the repo-mechanical measurements in Phase 1."
                            },
                            {
                                "ref":  "requests/bugfix-requests/README.md:24-26",
                                "claim":  "The bugfix track\u0027s definition of done: the red reproduction goes green and a regression test is left behind. The acceptance contract this plan is measured against."
                            },
                            {
                                "ref":  "requests/bugfix-requests/README.md:54",
                                "claim":  "The Index row for this slug, currently `diagnosed`; Phase 6 advances it to `fixed`."
                            }
                        ],
    "open_questions":  [
                           "Does the leak-guard tier land in this change or become its own request? The plan sequences it as Phase 3 with an explicit severance point gated on Phase 1\u0027s five `git check-ignore` verdicts. The RCA hands the call to this stage (:168-169) and is emphatic that whichever way it goes must be stated rather than left reading as \u0027closed\u0027.",
                           "Is the copy-the-package variant accepted as sufficient fidelity, or does the user want the live plant retained in some form? The plan recommends the copy plus three compensating assertions, on the ground that they assert strictly more than the live plant ever did — but `test_fixed_offset_guard_scope.py:85-86` is a real argument and this is the RCA\u0027s own named design call (:144-151).",
                           "Phase 5(a): detect-and-report a survivor, or actually sweep it? The plan recommends detect-and-report, because a session-scoped autouse sweep would need the repo\u0027s first `conftest.py` and `tests/fixtures/warehouse.py:1-6` states the reason this repo avoids one. Silent tidying also destroys the evidence a reader needs.",
                           "Phase 5(b): should `test_no_fixed_offsets.py` learn probe names and emit a friendlier message? The plan recommends declining — after Phase 2 the branch is unreachable, and it would put dead code inside the enforcement of ADR 0020. Explicitly the user\u0027s call (RCA :168).",
                           "Is Phase 4\u0027s contract guard in scope, or is it creep? It is the executable form of the RCA\u0027s Root tier (:152-156) and lands with zero allowlist entries once Phases 2-3 are done, but it is the one deliverable the RCA does not name outright. If dropped, say in the report that the convention is prose-only.",
                           "Per-test copy/`git init` versus a session-scoped pristine tree: left to Phase 1\u0027s measurement rather than decided in advance, with a stated threshold (~1s for the scope module, ~5s for the leak module) so the decision is made against a number instead of a preference.",
                           "Should `requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md`\u0027s follow-up 3 — the Phase 10 record of this sighting — be marked resolved as part of Phase 6, or left for `/update-docs` to judge?"
                       ]
}
```

## Planner: domain-convention - returned: True

```json
{
    "planner":  "domain-convention",
    "ok":  true,
    "onboarding_files":  [
                             {
                                 "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md",
                                 "why":  "The decided artifact. Read the two-mode table (:17-21) and the fix posture (:137-164) before touching code: mode B (a concurrent reader seeing a healthy run\u0027s probe) leaves nothing behind, so a survivor sweep cannot be the fix. It also hands three design calls to this plan (:166-170)."
                             },
                             {
                                 "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md",
                                 "why":  "Context only. Its blast-radius table (:79-89) is the measured one: pytest tests/test_no_fixed_offsets.py and `ruff format --check` go red; `ruff check`, mypy and the leak guard pass. Do not re-open its triage."
                             },
                             {
                                 "path":  "tests/test_guard_probe_isolation.py",
                                 "why":  "The committed RED repro — the acceptance contract. Two tests, one per mode. It drives the real fixture on purpose (:20-23), so any fix that stops the fixture poisoning the live tree turns both green. Note the exact coupling it has to the fixture: it imports OFFENDER, PARSER_DIR and parser_probe at :35, and ABORT_CHILD calls `parser_probe(name, body)` positionally at :55 inside a child process."
                             },
                             {
                                 "path":  "tests/test_fixed_offset_guard_scope.py",
                                 "why":  "The file being fixed. `PARSER_DIR` (:60) and `parser_probe` (:81-98) are the planter; the docstring at :85-86 carries the fidelity argument the RCA says this plan must actually decide. Six tests call the real disk scan (:112, :127, :133, :145, :180, :431)."
                             },
                             {
                                 "path":  "tests/test_no_fixed_offsets.py",
                                 "why":  "The guard being poisoned. `SCAN_ROOT` (:97), `parser_modules()` (:345-354) and `parser_module_violations()` (:357-363) are the seam to be parameterised — and :361\u0027s `path.relative_to(REPO_ROOT)` is why a naive `root=` parameter raises ValueError on a tmp tree. `test_no_parser_module_seeks_to_a_fixed_offset` (:569-575) is the test that goes red on a phantom."
                             },
                             {
                                 "path":  "tests/test_leak_guard_scope.py",
                                 "why":  "The second site of the same hazard class (RCA Q4). `untracked_file` (:40-53) plants real files at the repo root (:73), under requests/bugfix-requests/ (:119-120), in tests/fixtures/ as a `.dat` (:174) and under var/tmp (:89-90), with a runtime-built banned string (:37). Its survivor is worse than the parser one."
                             },
                             {
                                 "path":  "tests/test_no_leaks.py",
                                 "why":  "The guard the leak-scope probes poison, and the seams Phase 3 must parameterise: `git_paths` (:44-67, cwd=REPO_ROOT), `scannable_text_files` (:70-106), `machine_path_violations` (:139-165), `game_data_offenders` (:173-194). This is the repo\u0027s only leak protection (ADR 0006)."
                             },
                             {
                                 "path":  ".claude/agents/data-engineer.md",
                                 "why":  "The build rulebook — and the reason this fix is NOT delegable. Its repo-level deny set (:154-165) forbids the write-capable subagent from touching `tests/`, and :171-172 tells it to stop and report if a spec\u0027s targets land there. This change is 100% under tests/."
                             },
                             {
                                 "path":  ".claude/agents/data-engineer-memory.md",
                                 "why":  "Append-only harness memory (:39-53: no budget, never prune, curation at /update-docs). The entry at :351-356 currently prescribes the exact hazardous pattern — \u0027a planted offender written to disk and removed in `finally`\u0027 — so this change must APPEND a superseding entry in the fixed bullet shape at :25-37, never edit that one."
                             },
                             {
                                 "path":  "pyproject.toml",
                                 "why":  "The toolchain contract this must satisfy: ruff per-file-ignores for tests (:78-79), `known-first-party = [\"ootp_ai\", \"fixtures\"]` (:88, which is why a shared helper belongs at tests/fixtures/), mypy strict over src AND tests (:91-95), and pytest with no xdist (:98-108) — the reason CI has never gone red on this."
                             },
                             {
                                 "path":  ".github/workflows/ci.yml",
                                 "why":  "The gates every phase checkpoint must mirror locally: `ruff check .` (:46), `ruff format --check .` (:49), `mypy` (:52), `pytest -m \"not gamedata\"` (:57)."
                             },
                             {
                                 "path":  "docs/decisions/0020-sanctioned-lookahead-seam.md",
                                 "why":  "The decision the poisoned guard enforces. Read §\u0027What it does not claim\u0027 (:95-102) — it leans on tests/test_fixed_offset_guard_scope.py pinning six residuals. Those residual controls run through `scan_source` on strings and are untouched by this fix; confirm that before assuming an ADR edit is needed (it is not)."
                             }
                         ],
    "architecture_notes":  "THE SHAPE OF THE DEFECT, IN ONE SENTENCE: `tests/test_fixed_offset_guard_scope.py` writes a real `.py` into `src/ootp_ai/parser/` (:92-98) and `tests/test_no_fixed_offsets.py` enumerates `src/ootp_ai` (:97, :352) — one path, two owners, no seam.\n\nTHIS CHANGE TOUCHES NO DATA. Nothing is parsed, landed, modelled or served; no dataset is added; `datasets/manifest.json` is not involved (it does not exist yet — CLAUDE.md\u0027s project map says `datasets/` arrives with its first builder). There is no grain, no coverage window, no update semantics and no pull cost to declare, and a data-contracts section would be noise. The correctness lens that DOES bind is project-convention correctness, and it binds hard, because every file this plan edits is a guard.\n\nTHE THREE READERS OF THE LIVE PACKAGE TREE. A survivor in `src/ootp_ai/parser/` is seen by more than the headline guard: `tests/test_no_fixed_offsets.py:352` (rglob), `tests/test_grain_contracts.py:364-367` (`source_modules()`, the same rglob over the same root), `ruff format --check .`, and mypy\u0027s file set. Only the first two are pytest; the RCA\u0027s measured blast radius (test_no_fixed_offsets + ruff format) is right about which ones actually go red today, because the grain guard\u0027s rule does not match the probe bodies. Do not widen that claim without measuring.\n\nTHE SEAM THAT DOES NOT EXIST YET. `parser_module_violations()` (:357-363) builds each scanned file\u0027s identity as `path.relative_to(REPO_ROOT).as_posix()` at :361, and that string is BOTH the reported path and the key `EXEMPT_MODULES` (:104-107) and the location rule are matched against. So the RCA\u0027s sketched signature — `parser_modules(root=SCAN_ROOT)` — is not sufficient as written: pointing `root` at a tmp directory makes :361 raise `ValueError: not in the subpath of`. The parameter must be a REPO-ROOT-SHAPED directory, not a package directory. Prescribed shape:\n\n    PACKAGE_RELATIVE = Path(\"src\") / \"ootp_ai\"\n    SCAN_ROOT = REPO_ROOT / PACKAGE_RELATIVE            # keep; it is the production constant\n    def parser_modules(tree_root: Path = REPO_ROOT) -\u003e list[Path]\n    def parser_module_violations(tree_root: Path = REPO_ROOT) -\u003e list[str]   # rel = path.relative_to(tree_root)\n\nA mirror laid out as `\u003ctmp\u003e/src/ootp_ai/...` then yields byte-identical repo-relative strings, so the allowlist, the interior stricter rule and the reported message all behave exactly as in production. One parameter, one invariant preserved.\n\nTHE FIDELITY TRADE, DECIDED. The RCA\u0027s middle path is the right one and the cheap version is not: copy the real package into the tmp tree (`shutil.copytree`, ignoring `__pycache__`) and plant the probe BESIDE the real modules, so the probe still sits among real code on disk and the scan still walks a directory of real files. Measured: 37 `.py` files, 551,657 bytes — a copy per probe is sub-second and the suite makes ~8 of them. The weakening is that the scan reads a faithful copy rather than the original, and it is paid for in the same commit by three compensating assertions (production default root is the live package; the tree-is-clean test calls it with no arguments; the mirror\u0027s module set and bytes equal the live one\u0027s). Never land the weakening without the compensation.\n\nTHE FIXTURE SIGNATURE IS LOAD-BEARING AND MUST NOT CHANGE. `ABORT_CHILD` (test_guard_probe_isolation.py:46-57) is source text executed in a child process; it calls `parser_probe(\"_guard_scope_abort_probe.py\", OFFENDER)` positionally at :55, and the test asserts the child exited exactly 97 (:83-87) — a `TypeError` from a changed signature exits 1 and the repro fails with \"the child never reached the probe\", which reads as a different bug. So `parser_probe(name, body)` must stay two-positional-arg callable and must keep yielding a plain `str`. Prescribed decomposition, which satisfies both:\n\n    @contextmanager\n    def mirrored_package() -\u003e Iterator[Path]                       # yields a repo-shaped tmp tree_root\n    @contextmanager\n    def parser_probe(name: str, body: str, tree_root: Path | None = None) -\u003e Iterator[str]\n        # tree_root=None -\u003e the fixture makes and owns a private mirror\n\nCall sites that need the root open both: `with mirrored_package() as tree, parser_probe(n, b, tree_root=tree) as rel:`. `ABORT_CHILD` keeps working untouched, and `PARSER_DIR` (:60) survives — changing role from \"where we plant\" to \"the live package the probe must never reach\", which is exactly what `_planted_probes()` (test_guard_probe_isolation.py:60-62) globs.\n\nWHERE THE SHARED HELPER LIVES. `tests/fixtures/` is the house location for shared test harness code — a real package (`tests/fixtures/__init__.py`), declared first-party for isort at pyproject.toml:88, imported as `from fixtures.warehouse import ...` (tests/test_catalog.py:48) and `from fixtures.reports import NAME_PATTERN` (tests/test_reports.py:50). Put the mirror helpers in `tests/fixtures/guard_trees.py`. It must not depend on pytest fixtures (`tmp_path` is unavailable inside ABORT_CHILD\u0027s child), so build the tree with `tempfile`, and it must be mypy-strict clean and PTH-clean (pathlib, not os.path).\n\nWHY CI NEVER CAUGHT THIS AND STILL WON\u0027T. pyproject.toml:98-108 declares no xdist and no parallel plugin, so plant and scan are strictly sequential in one session (RCA :100-106). This is a multi-session hazard on a developer\u0027s or an acceptance panel\u0027s machine — `requests/feature-requests/first-sight/reviews/phase-10-acceptance-panel.md:84-87` records the lenses running concurrently against one shared working tree and calls the resulting `test_no_fixed_offsets` red cross-contamination. Consequence for verification: a green single-session CI run is NOT evidence that mode B is closed. The plan therefore prescribes a measured two-session concurrency run as acceptance, not an assertion.\n\nTHE CLASS, NOT THE INSTANCE. `untracked_file` (test_leak_guard_scope.py:40-53) is the same shape with a worse survivor: its probe bodies carry a deliberately banned machine-path string built at :37, so a survivor at the repo root (:73) reddens `tests/test_no_leaks.py` — the repo\u0027s only leak protection — and one under `requests/bugfix-requests/` (:119-120) races `test_doc_links` (recorded as CF-14 at phase-7-acceptance-panel.md:63, carried forward unfixed). Its un-sharing is harder because the guard\u0027s scope IS the real repo: `git_paths` shells `git ls-files --cached --others --exclude-standard` with `cwd=REPO_ROOT` (test_no_leaks.py:60-65). The split that works: every test that PLANTS moves to a `git init`-ed tmp repo carrying a copy of the real `.gitignore`; every test that MEASURES the real repo (the \u003e=80 floor at :224-238, the junk-directory parametrise at :97-105, the tracked-markdown pairing at test_no_leaks.py:266-283) plants nothing and keeps the default. That split is the one-sentence convention worth writing down: A GUARD\u0027S SCOPE TEST MAY PLANT ONLY IN A TREE IT OWNS; A TEST THAT READS THE LIVE TREE PLANTS NOTHING.\n\nONE UNCONFIRMED CLAIM, AND IT GATES PHASE 3. \"A `git init` temp repo with a copied `.gitignore` reproduces the real enumeration semantics\" is `unconfirmed` — nobody has run it. A temp repo has an empty index, so `--cached` returns nothing and any assertion that depends on tracked files changes meaning there. Phase 3 opens with a measurement step that proves parity for the six enumeration properties before any test is moved; if parity fails, Phase 3 degrades to a filed follow-up rather than a weakened leak guard.",
    "phases":  [
                   {
                       "name":  "Phase 1 — Give the scan a tree seam (no behaviour change)",
                       "goal":  "`tests/test_no_fixed_offsets.py` can be pointed at a repo-root-shaped tree, while production keeps reading the live package. Nothing about what the guard flags changes, and nothing is planted anywhere new yet.",
                       "steps":  [
                                     "In tests/test_no_fixed_offsets.py, next to `SCAN_ROOT` (:96-97), introduce `PACKAGE_RELATIVE = Path(\"src\") / \"ootp_ai\"` and redefine `SCAN_ROOT = REPO_ROOT / PACKAGE_RELATIVE`. Keep the name `SCAN_ROOT` — it is the production constant the compensating assertions in Phase 2 pin, and `.claude/agents/data-engineer.md:77-79` and ADR 0020 both describe this guard by its scope.",
                                     "Change `parser_modules()` (:345-354) to `parser_modules(tree_root: Path = REPO_ROOT) -\u003e list[Path]`, globbing `tree_root / PACKAGE_RELATIVE`. Keep the vacuity assertion at :353 and make its message name the resolved root, so a mis-pointed mirror fails loudly instead of passing empty.",
                                     "Change `parser_module_violations()` (:357-363) to `parser_module_violations(tree_root: Path = REPO_ROOT) -\u003e list[str]` and change :361 from `path.relative_to(REPO_ROOT)` to `path.relative_to(tree_root)`. This is the line that would otherwise raise ValueError on a tmp tree; the resulting string must still read `src/ootp_ai/parser/\u003cname\u003e.py` so `EXEMPT_MODULES` (:104-107) and the location rule are keyed identically.",
                                     "Do NOT change `test_no_parser_module_seeks_to_a_fixed_offset` (:569-575): it must keep calling `parser_module_violations()` with no arguments. Add a comment at the seam saying that production passes no argument on purpose and that Phase 2\u0027s compensating test asserts it.",
                                     "Extend the two callables\u0027 docstrings to say what `tree_root` is for — a scope test plants in a tree it owns — and cite `requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/` as the reason, matching how `tests/test_leak_guard_scope.py:20` cites its own request directory.",
                                     "Leave every caller unchanged this phase (tests/test_fixed_offset_guard_scope.py :112, :127, :145, :180, :431 and tests/test_guard_probe_isolation.py:112 all still call with defaults)."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest -m \"not gamedata\" tests/test_no_fixed_offsets.py tests/test_fixed_offset_guard_scope.py tests/test_grain_contracts.py` is green — identical pass counts to before the phase.",
                                          "`uv run pytest tests/test_guard_probe_isolation.py` is STILL RED, with both original failures. This is expected and must be stated in the commit note: the seam alone closes neither mode.",
                                          "`uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` are clean (mypy is strict over tests/ — pyproject.toml:91-95 — so both new signatures need full annotations).",
                                          "`git status --porcelain --untracked-files=all` shows only the intended edit: no stray `_guard_scope*_probe.py` under src/.",
                                          "Grep proves the seam is complete: `parser_modules(`/`parser_module_violations(` have exactly the 6 call sites listed in Files to touch, and no other module imports them."
                                      ],
                       "commit_note":  "Give the fixed-offset scan a tree_root seam, defaults unchanged. Mechanical: the guard still reads the live package in production; the repro stays red because nothing has moved yet."
                   },
                   {
                       "name":  "Phase 2 — Plant in a faithful copy, and pay for the fidelity in the same commit",
                       "goal":  "The probe never touches `src/ootp_ai/parser/` again — closing mode A and mode B together — and the one test proving the guard reads the real package is compensated rather than weakened. Both repro tests go GREEN.",
                       "steps":  [
                                     "Create `tests/fixtures/guard_trees.py` with two context managers and no pytest dependency (it is imported by ABORT_CHILD\u0027s child process, where `tmp_path` does not exist): `mirrored_package() -\u003e Iterator[Path]` yields a tempdir laid out as `\u003ctmp\u003e/src/ootp_ai/...`, built with `shutil.copytree(SRC_PACKAGE, tree_root / \u0027src\u0027 / \u0027ootp_ai\u0027, ignore=shutil.ignore_patterns(\u0027__pycache__\u0027))`; and a small `plant(tree_root, name, body) -\u003e Path` helper. Use `tempfile`, `pathlib` (ruff PTH), full annotations (mypy strict), and remove the tree in a `finally` — the `finally` is now a tidiness measure in a directory nobody else reads, which is the whole point.",
                                     "Write the module docstring as the convention\u0027s operative statement: a guard\u0027s scope test may plant only in a tree it owns; a test that reads the live tree plants nothing. Say why a `tmp_path`-only probe was rejected (it proves the scan reads *a* directory) and why a byte-faithful copy is the accepted middle, citing the RCA.",
                                     "In tests/test_fixed_offset_guard_scope.py, keep `PARSER_DIR` (:60) but re-document it: it is now the live package the probe must never reach, and it is what `tests/test_guard_probe_isolation.py:60-62` globs. Rewrite `parser_probe` (:81-98) to `parser_probe(name: str, body: str, tree_root: Path | None = None) -\u003e Iterator[str]` — planting into the given tree, or into a private `mirrored_package()` when None. It MUST stay callable with two positional args and MUST keep yielding a `str`, or ABORT_CHILD (test_guard_probe_isolation.py:55) breaks and the repro fails for the wrong reason. Keep the `assert not path.exists()` clobber guard (:93).",
                                     "Replace the fixture docstring\u0027s fidelity paragraph (:85-86 — \u0027A `tmp_path` fixture cannot serve…\u0027) with the honest new argument: the probe sits among byte-identical copies of the real modules, sharing nothing, and three named tests pin that production still reads the original. Do not delete the old reasoning silently — say what replaced it and why.",
                                     "Update the six call sites to open a mirror where they need the root: `test_the_scan_reports_a_planted_offender_in_the_real_tree` (:104-116) and `test_the_folded_constant_rule_reports_an_offender_in_the_real_tree` (:421-434) become `with mirrored_package() as tree, parser_probe(..., tree_root=tree) as rel: violations = guard.parser_module_violations(tree_root=tree)`; same for :119-127 and :130-134. Rename the two \u0027…in_the_real_tree\u0027 tests to say what they now do (e.g. `…_in_a_faithful_copy_of_the_tree`) — a test name that lies is the failure mode this whole request is about.",
                                     "Leave `test_the_module_set_has_a_floor` (:137-150) and `test_an_allowlisted_path_matches_what_the_real_scan_builds` (:176-184) calling `guard.parser_modules()` with NO argument, against the live package. The RCA is explicit: move these and the fix buys a vacuous guard. Add a comment saying so at each.",
                                     "Add the three compensating assertions in tests/test_fixed_offset_guard_scope.py: (a) `test_the_production_scan_root_is_the_live_package` — every path from `guard.parser_modules()` is under `guard.SCAN_ROOT`, and both `EXEMPT_MODULES` entries are present; (b) `test_the_tree_is_clean_test_takes_the_default_root` — `inspect.getsource(guard.test_no_parser_module_seeks_to_a_fixed_offset)` matches `parser_module_violations\\(\\s*\\)`, so nobody can quietly point production at a mirror; (c) `test_the_mirror_is_a_faithful_copy_of_the_live_package` — the mirror\u0027s repo-relative path set equals the live one\u0027s and every file\u0027s bytes match, so \u0027the scan read a copy\u0027 degrades no further than \u0027the scan read a byte-identical copy\u0027.",
                                     "Add one anti-vacuity assertion: `len(guard.parser_modules(tree_root=mirror)) == len(guard.parser_modules())` (37 today, floor 12), proving the planted probe really is surrounded by real modules rather than sitting alone in an otherwise empty tree.",
                                     "Do not edit `tests/test_guard_probe_isolation.py` at all this phase, beyond (optionally) appending a line to its module docstring recording that it now passes and what fixed it. It is the red-goes-green evidence; if you must change an assertion to make it pass, you have changed what it proves — stop and re-read the RCA.",
                                     "Measure and record the cost: time `uv run pytest tests/test_fixed_offset_guard_scope.py` before and after. If the copy is material (it should not be — 37 files, 551,657 bytes), switch `mirrored_package` to a module-scoped copy with per-test probe names and say so."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest tests/test_guard_probe_isolation.py` is GREEN — both `test_a_run_that_dies_inside_the_probe_leaves_no_module_behind` and `test_the_real_scan_does_not_report_a_probe_a_sibling_test_has_planted` pass, with the file unedited (or only its docstring touched).",
                                          "MODE A, measured by hand: run the ABORT_CHILD script directly (`uv run python \u003cscript\u003e \u003crepo-root\u003e`), confirm exit code 97, then `git status --porcelain --untracked-files=all` shows nothing new under `src/` and `Get-ChildItem src/ootp_ai/parser -Filter _guard_scope*_probe.py` is empty.",
                                          "MODE B, measured by hand and recorded with the numbers: in two shells at once, loop `uv run pytest tests/test_fixed_offset_guard_scope.py` against `uv run pytest tests/test_no_fixed_offsets.py tests/test_grain_contracts.py` at least 10 times each; zero reds. Do the same run on the pre-fix commit to show it flapping, or state plainly that it was not re-measured. A single-session green CI run is NOT evidence here (no xdist — pyproject.toml:98-108).",
                                          "The whole offline suite is green: `uv run pytest -m \"not gamedata\"`, plus `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean. `ruff format --check` passing while a probe would have been planted is itself part of the fix (the intake\u0027s second red gate).",
                                          "Mypy\u0027s reported file count is stable across a run of the guard-scope module — the intake measured it silently widening 80 -\u003e 81 with a survivor present.",
                                          "Every renamed test\u0027s new name is true of what it asserts, and no test named \u0027…in_the_real_tree\u0027 plants outside a tree it owns."
                                      ],
                       "commit_note":  "Plant the fixed-offset probe in a faithful copy of the package, not in the package. Closes both the survivor and the concurrent-reader paths; three compensating assertions pin that production still scans the live tree, and the committed repro goes green untouched."
                   },
                   {
                       "name":  "Phase 3 — The class, not the instance: the leak-guard probe (gated on a measurement)",
                       "goal":  "`untracked_file` stops writing into the live repo, using the same convention — or, if temp-repo parity cannot be measured, the site is filed as its own bugfix request rather than half-fixed. Its survivor is the worse one: a banned machine-path string at the repo root, poisoning the repo\u0027s only leak protection.",
                       "steps":  [
                                     "MEASUREMENT FIRST, before moving any test. The claim \u0027a `git init` temp repo carrying a copy of the real .gitignore reproduces the real enumeration semantics\u0027 is `unconfirmed`. Prove or disprove it in a scratch script under the scratchpad (never in the repo): create a tempdir, `git init -q`, copy `.gitignore`, create `var/tmp/`, `tests/fixtures/`, `requests/bugfix-requests/`, then check all six properties the moved tests depend on — an untracked file is listed; a `var/` file is not; a nested untracked file is listed; a non-ASCII filename survives `-z` decoding; a `.lg` file is ignored; an untracked `.dat` under `tests/fixtures/` IS listed (the last is the whole point of test_no_leaks.py:173-194, and depends on git\u0027s last-match-wins negations). Record the results with labels.",
                                     "If parity holds: parameterise the guard\u0027s four seams in tests/test_no_leaks.py with a keyword-only default — `git_paths(*args: str, repo: Path = REPO_ROOT)` (:44-67, pass `cwd=repo`), `scannable_text_files(repo: Path = REPO_ROOT)` (:70-106), `machine_path_violations(repo: Path = REPO_ROOT)` (:139-165) and `game_data_offenders(repo: Path = REPO_ROOT)` (:173-194). `EXEMPT`/`EXEMPT_PREFIXES` keying stays repo-relative and therefore unchanged.",
                                     "Add `mirrored_repo()` to `tests/fixtures/guard_trees.py` — same convention, second tree: tempdir, `git init -q`, copy the real `.gitignore` verbatim (the file\u0027s CONTENT is what those tests are about), create the directories the probes need.",
                                     "Move only the PLANTING tests in tests/test_leak_guard_scope.py to the mirrored repo: :64-78, :81-94, :113-124, :127-141, :158-162, :165-178, :181-185, :188-193, :203-215, :218-221. Leave the measuring tests on the real repo untouched: the \u003e=80 floor (:224-238), the junk-directory parametrise (:97-105), and test_no_leaks.py\u0027s own tracked-markdown pairing (:266-283) — they plant nothing, so they are already safe.",
                                     "TRAP: `test_a_path_that_no_longer_exists_does_not_crash_the_scan` (:241-253) monkeypatches `guard.scannable_text_files` with a ZERO-ARGUMENT lambda at :251. Once the real function takes `repo`, `machine_path_violations` will call it with an argument and the lambda raises TypeError. Change it to `lambda repo=REPO_ROOT: [...]` in the same edit or this test fails for an unrelated reason.",
                                     "Add the mirrored-repo equivalents of Phase 2\u0027s compensations: the production leak scan still enumerates the real repo (`scannable_text_files()` with no argument returns paths under REPO_ROOT), and `test_no_machine_paths_or_identifiers` (:168-170) / `test_game_data_is_not_tracked` (:197-200) still call with defaults — pinned the same way, via `inspect.getsource`.",
                                     "If parity does NOT hold for any of the six properties: stop. Do not weaken a leak-guard assertion to fit a temp repo. Write the measurement into this request\u0027s IMPLEMENTATION_REPORT, file a follow-up bugfix request for the site, and add its Index row. Keep the shared helper and the convention from Phase 2 — that is what stops a third site being invented, which is the RCA\u0027s actual root-tier ask."
                                 ],
                       "acceptance":  [
                                          "`git status --porcelain --untracked-files=all` is clean immediately after `uv run pytest tests/test_leak_guard_scope.py` — and, separately, after killing that run mid-suite (Ctrl-C or a hard kill), nothing named `_leak_guard*probe.*` exists anywhere under the repo.",
                                          "The mode-B proof for this site: two concurrent shells looping `uv run pytest tests/test_leak_guard_scope.py` against `uv run pytest tests/test_no_leaks.py tests/test_doc_links.py`, 10+ rounds, zero reds. `test_doc_links` racing the root-level probe is CF-14 at requests/feature-requests/first-sight/reviews/phase-7-acceptance-panel.md:63 — this is the evidence that closes it.",
                                          "No leak-guard assertion got weaker: the \u003e=80 candidate floor, the junk-directory exclusions and the `tests/fixtures/*.dat` game-data check all still run against the REAL repo and still pass.",
                                          "Full offline suite plus all four CI gates green.",
                                          "The parity measurement is written down with an epistemic label — `measured` if run, and every property named individually rather than summarised as \u0027it works\u0027."
                                      ],
                       "commit_note":  "Move the leak-guard probes into a repo the test owns (or: file the site as a follow-up, with the parity measurement that decided it). Same convention as the fixed-offset probe — one shared helper, not two independent fixes."
                   },
                   {
                       "name":  "Phase 4 — Record the convention where it binds the next agent",
                       "goal":  "The rule survives this request. Three artifacts carry it, each in the form its own contract demands, and the harness memory entry that currently prescribes the hazardous pattern is superseded rather than quietly edited.",
                       "steps":  [
                                     "APPEND to `.claude/agents/data-engineer-memory.md` — do not edit the entry at :351-356, which tells the next builder to plant \u0027a planted offender written to disk and removed in `finally`\u0027. That file is append-only by its own contract (:39-53: no budget, never prune, curation happens at /update-docs), and the 2026-08-18 precedent at :340-350 shows the house form for superseding: name the entry you are dating and say both stay because a ledger is a log. Use the exact bullet shape at :25-37 with a valid epistemic label — `tests/test_agent_contract.py:84-95` fails the build on a missing or invalid one — and cite `tests/fixtures/guard_trees.py` as inline code, never a markdown link (:35-37).",
                                     "Write ADR 0022 (next free number — 0001..0021 exist) stating the decision: a guard\u0027s scope test plants only in a tree it owns; a test that reads the live tree plants nothing; fidelity is bought with a byte-faithful copy plus a compensating assertion that production reads the original. It must have a `## Consequences` section that states the COST in as many words — `tests/test_repo_structure.py:43-57` fails an ADR that only lists benefits — and it must be added to `docs/decisions/README.md` (:33-40 asserts every ADR is indexed) with sequential numbering (:60-67). Name the cost honestly: the end-to-end test now reads a copy, and two helper trees exist that must stay faithful.",
                                     "Truth-up the prose that this change made false: the module docstring of tests/test_fixed_offset_guard_scope.py at :18 (\u0027a real offender written into `src/ootp_ai/parser/`\u0027), and the stale floor message at :146-149 (\u0027it has been covering 18\u0027 — the real count is 37 today, measured; the \u003e=12 floor still stands and should not move).",
                                     "Do NOT edit `docs/decisions/0020-sanctioned-lookahead-seam.md`. Its §\u0027What it does not claim\u0027 (:95-102) leans on this module pinning six residuals, and those controls run `scan_source` over strings (:285-447) — untouched by this fix. ADRs are the main thread\u0027s (data-engineer.md:163) and an accepted one is not amended to reflect a test refactor.",
                                     "Do NOT retro-edit `BUGFIX_REQUEST.md` or `ROOT_CAUSE_ANALYSIS.md`. They quote the old docstring at :85-86 and that is the historical record. The only artifact movement is the Index row in `requests/bugfix-requests/README.md:54`, whose Stage cell goes `diagnosed` -\u003e `planned` (when the plan lands) -\u003e `fixed`, per the status grammar at :45.",
                                     "Write `IMPLEMENTATION_REPORT.md` in the request directory with the measured evidence: the mode-A exit-97 run, the concurrent-session rounds and their counts, the copy-cost timing, and (if Phase 3 ran) the six temp-repo parity properties. Follow the `_done/` siblings\u0027 shape.",
                                     "Run `/update-docs` and let it judge whether CLAUDE.md\u0027s map needs `tests/fixtures/guard_trees.py` mentioned. Do not restate the new rule in CLAUDE.md\u0027s build-rulebook section — that file names the rulebook rather than restating it, and `tests/test_agent_contract.py:53-73` exists because restating creates the second copy single ownership is meant to prevent."
                                 ],
                       "acceptance":  [
                                          "`uv run pytest -m \"not gamedata\" tests/test_agent_contract.py tests/test_repo_structure.py tests/test_doc_links.py tests/test_no_leaks.py` green — the memory entry\u0027s label parses, the ADR is indexed, numbered and states its cost, and every link in the new artifacts resolves.",
                                          "The memory file has one MORE entry than before and zero changed lines above it (`git diff` shows an append only).",
                                          "`requests/bugfix-requests/README.md:54`\u0027s Stage cell and `IMPLEMENTATION_PLAN.md`\u0027s status blockquote agree — /commit checks this pairing.",
                                          "Every relative link and bare `requests/...` token in the new artifacts resolves on disk; any forward reference (a follow-up request directory that does not exist yet) sits inside a fenced code block, which is the documented exemption.",
                                          "All four CI gates green."
                                      ],
                       "commit_note":  "Record the probe-isolation convention: ADR 0022, a superseding harness-memory entry, and the docstring truth-up. The rule now binds the next agent instead of living in one fixture."
                   },
                   {
                       "name":  "Phase 5 — Janitor for old survivors (OPTIONAL — recommend report-only, or skip)",
                       "goal":  "Clean survivors left by revisions that predate the fix — the one thing no design change can do retroactively — without letting a sweep be mistaken for the fix.",
                       "steps":  [
                                     "Decide explicitly whether to ship this at all. The RCA is blunt (:157-161): a sweep closes neither mode and must not be sold as the fix; its only real value is survivors from older commits. After Phases 1-3 no new survivor can be created, so this decays to a one-time cleanup — a `git status` and a delete would do it.",
                                     "If shipped: add `tests/conftest.py` (none exists today) with a `pytest_sessionstart` hook that REPORTS, via a terminal warning, any `src/ootp_ai/parser/_guard_scope*_probe.py` or repo-root `_leak_guard*probe.*` it finds, and removes it. Reporting is not optional — a silent tidy makes the next survivor invisible, which is how this bug cost five reviewers a false alarm.",
                                     "Do not implement the RCA\u0027s option (b) — teaching `tests/test_no_fixed_offsets.py` to recognise a probe filename and emit \u0027a test fixture survived an interrupted run\u0027. It is a guard knowing about its own test, and it trades directly against the fixed-offset ban\u0027s enforcement (ADR 0020). After Phase 2 it protects against nothing that can still happen. If it is shipped anyway, that is an ADR-level decision, not a phase step.",
                                     "Do not gitignore `_guard_scope*_probe.py`. A survivor that no longer shows in `git status --porcelain --untracked-files=all` is harder to find, not safer — the intake\u0027s step 4 (:45) used exactly that signal to identify the phantom.",
                                     "Verify a new conftest.py changes nothing about collection or sys.path: the suite\u0027s cross-module imports (e.g. `import test_no_fixed_offsets as guard`) already rely on pytest\u0027s rootdir prepend, and pass counts must be identical before and after."
                                 ],
                       "acceptance":  [
                                          "If shipped: with a survivor planted by hand, the next session reports it by name and removes it, and the suite\u0027s pass count is otherwise unchanged.",
                                          "If skipped: the decision and its reason are recorded in the IMPLEMENTATION_REPORT, so the next reader does not re-propose the sweep.",
                                          "Full offline suite plus all four CI gates green either way."
                                      ],
                       "commit_note":  "Report-and-remove survivors from older revisions (or: record why no sweep shipped). Janitorial only — Phases 1-3 are what stop a survivor being created."
                   }
               ],
    "testing":  "THE ACCEPTANCE CONTRACT IS THE BUGFIX TRACK\u0027S, NOT A FEATURE\u0027S: the red repro goes green, a regression test is left behind, and nothing else regresses (requests/bugfix-requests/README.md:24-26).\n\nRED -\u003e GREEN, exactly. Today `uv run pytest tests/test_guard_probe_isolation.py` fails both tests; after Phase 2 both pass with the module UNEDITED. That constraint is the test\u0027s own design (its docstring at :20-23 says it drives the real fixture so that any fix which stops the poisoning turns it green) and it is what stops the fix being \"teach the guard to ignore the file\". If you find yourself editing an assertion in that file to get green, the fix is wrong, not the test. The one legitimate edit is `ABORT_CHILD` (:46-57) IF `parser_probe`\u0027s signature changes — which this plan avoids precisely so that escape hatch is never needed.\n\nTHE REGRESSION TESTS LEFT BEHIND. `tests/test_guard_probe_isolation.py` itself is the primary one and stays permanently. Phase 2 adds four more in tests/test_fixed_offset_guard_scope.py, and they are the ones that keep the fix honest rather than merely green: (a) the production scan root is the live package; (b) the tree-is-clean test calls `parser_module_violations()` with no arguments, asserted from its own source; (c) the mirror is a byte-faithful copy of the live package; (d) the mirrored scan covers the same module count as the live one. Without (b) a future edit could point production at a mirror and every other test would still pass — the exact vacuity failure `test_the_module_set_has_a_floor` (:137-150) and `test_the_candidate_set_has_a_floor` (tests/test_leak_guard_scope.py:224-238) were written for.\n\nWHAT MUST KEEP RUNNING AGAINST THE REAL TREE. `test_the_module_set_has_a_floor` (:145 — `guard.parser_modules()`), `test_an_allowlisted_path_matches_what_the_real_scan_builds` (:180), and `test_no_parser_module_seeks_to_a_fixed_offset` (:569-575). The RCA is explicit that moving these buys a vacuous guard. Same rule on the leak side: the \u003e=80 floor and the junk-directory exclusions stay on the real repo.\n\nFOUR GATES PER CHECKPOINT, MIRRORING CI (.github/workflows/ci.yml:45-57):\n  uv run ruff check .\n  uv run ruff format --check .        \u003c- non-negotiable here: it is the intake\u0027s second red gate\n  uv run mypy                          \u003c- strict over tests/ too (pyproject.toml:91-95)\n  uv run pytest -m \"not gamedata\"      \u003c- the gamedata suite needs a save + MySQL and is not touched by this change\nThen /commit, which stages deliberately, runs the doc gate and asks before writing. /commit does NOT run lint/types/tests — that is yours locally and CI\u0027s on the PR.\n\nTWO THINGS THAT MUST BE MEASURED, NOT ASSERTED, because no single-session pytest run can prove them (pyproject.toml:98-108 declares no xdist, which is why this has cost five reviewers and zero builds):\n1. MODE A, durability. Run ABORT_CHILD\u0027s script directly, confirm exit 97 (any other code means the child never reached the probe — the assertion at test_guard_probe_isolation.py:83-87 says so), then confirm `src/ootp_ai/parser/` holds no `_guard_scope*_probe.py` and `git status --porcelain --untracked-files=all` is clean.\n2. MODE B, concurrency. Two shells at once, 10+ rounds: `uv run pytest tests/test_fixed_offset_guard_scope.py` against `uv run pytest tests/test_no_fixed_offsets.py tests/test_grain_contracts.py`. Zero reds. Repeat for the leak site against `tests/test_no_leaks.py tests/test_doc_links.py` if Phase 3 lands. Record the round count and the result; \"green in CI\" is not evidence for this property.\n\nNOTHING-ELSE-REGRESSES, CONCRETELY. Before/after pass counts for the whole offline suite must match except for the tests deliberately added or renamed — take them from `--junit-xml` rather than a summary line, which is the correction the Phase 10 panel had to make about its own counts (phase-10-acceptance-panel.md:80-83). Also confirm mypy\u0027s file count is stable (a survivor silently widened it 80 -\u003e 81, per the intake\u0027s table) and that `tests/test_grain_contracts.py`\u0027s live-tree scan (:364-380) is unaffected.\n\nTHE GAMEDATA SUITE IS OUT OF SCOPE and must stay that way: this change touches no parser, no warehouse, no report. If a `-m gamedata` test starts failing, something else is wrong — do not absorb it into this request.",
    "risks":  [
                  "THE FIXTURE SIGNATURE TRAP. `ABORT_CHILD` (tests/test_guard_probe_isolation.py:46-57) is source text run in a child process; it calls `parser_probe(name, body)` positionally at :55 and the test asserts exit code exactly 97 (:83-87). Adding a required parameter makes the child die with TypeError -\u003e exit 1, and the repro then fails saying \u0027the child never reached the probe\u0027, which reads as a completely different bug. Mitigation: keep `parser_probe(name, body)` two-positional-arg callable with `tree_root` keyword-optional, and keep it yielding a plain `str` (the repro binds it with `as rel` at :111 and does `rel in v` at :112 — a tuple there raises TypeError).",
                  "THE RCA\u0027S SKETCHED SIGNATURE DOES NOT COMPILE. `parser_modules(root=SCAN_ROOT)` as written in the fix posture (:139-141) breaks `parser_module_violations`, which calls `path.relative_to(REPO_ROOT)` at tests/test_no_fixed_offsets.py:361 — a tmp root raises ValueError, and if someone \u0027fixes\u0027 that by relativising to the package root instead, every `EXEMPT_MODULES` key (:104-107) and the whole location rule silently stop matching, turning the sanctioned seam into an unsanctioned module. The parameter must be a REPO-ROOT-SHAPED directory. This is a correction to a sketch, not a re-litigation of the verdict.",
                  "A VACUOUS MIRROR IS INVISIBLE. If `mirrored_package()` mis-lays the tree (say `\u003ctmp\u003e/ootp_ai/` instead of `\u003ctmp\u003e/src/ootp_ai/`), `parser_modules` finds nothing, the vacuity assertion at :353 fires — good — but if it finds ONLY the probe, the planted-offender test passes while proving far less than it claims. Mitigation: the faithful-copy and module-count assertions in Phase 2 are mandatory, not nice-to-have.",
                  "MONKEYPATCH ARITY, PHASE 3. `tests/test_leak_guard_scope.py:250-252` replaces `guard.scannable_text_files` with a zero-argument lambda. The moment that function takes `repo`, the call from `machine_path_violations` raises TypeError and the test fails for an unrelated reason. Change the lambda to accept a defaulted `repo` in the same edit.",
                  "TEMP-REPO PARITY IS UNCONFIRMED. Nobody has run `git ls-files --cached --others --exclude-standard` inside a `git init`-ed mirror carrying a copied `.gitignore`. An empty index changes what `--cached` means, `--exclude-standard` also consults `.git/info/exclude` and the user\u0027s global excludesfile, and the `tests/fixtures/*.dat` case depends on git\u0027s last-match-wins negations (test_no_leaks.py:180-186). Phase 3 opens with the measurement and degrades to a filed follow-up if parity fails — never weaken a leak-guard assertion to fit the harness.",
                  "THE LEAK-GUARD SURVIVOR IS THE DANGEROUS ONE, AND IT IS THE ONE MOST LIKELY TO BE DEFERRED. Its probe bodies carry a runtime-built banned machine path (tests/test_leak_guard_scope.py:37) and it plants at the repo root, under requests/bugfix-requests/ and as a `.dat` under tests/fixtures/. A survivor there reddens the repo\u0027s only ADR-0006 protection and races test_doc_links (CF-14, phase-7-acceptance-panel.md:63). If Phase 3 is deferred, the deferral must be a filed request with an Index row, not a sentence in a report.",
                  "DELEGATION IS FORBIDDEN HERE AND THE HARNESS WILL NOT STOP IT. Every file this plan edits is under `tests/`, which is the first entry in the write-capable subagent\u0027s repo-level deny set (.claude/agents/data-engineer.md:157), asserted by tests/test_agent_contract.py:76-81. That deny is prose, not enforcement (:141-144). The main thread implements this directly; if a subagent is spawned for any part of it, that spec\u0027s targets fall in the deny set and the correct response is stop-and-report (:171-172). Any read-only subagent used for review gets read-only git.",
                  "A TEST NAME THAT LIES IS THIS EXACT BUG IN MINIATURE. `test_the_scan_reports_a_planted_offender_in_the_real_tree` (:104) stops being true the moment the probe moves. Leaving the name is how the next reader concludes the guard is proven against the live package when it is proven against a copy. Rename both \u0027…in_the_real_tree\u0027 tests and fix the module docstring at :18 in the same commit as the move.",
                  "DOC-DRIFT THAT CI WILL CATCH LATE. A new ADR must be indexed (tests/test_repo_structure.py:33-40), sequentially numbered (:60-67) and must state its cost (:43-57); a memory entry must carry one of the five epistemic labels in the exact bullet shape (tests/test_agent_contract.py:84-95); every link in the new artifacts is scanned by tests/test_doc_links.py, so a forward reference to a follow-up request directory that does not exist yet must sit inside a fenced code block. Run the four gates before /commit rather than discovering these on the PR.",
                  "THE OPPORTUNITY TO OVER-FIX. Two temptations are explicitly out: teaching the guard to recognise probe filenames (a guard knowing about its own test, trading against ADR 0020\u0027s enforcement) and gitignoring `_guard_scope*_probe.py` (which makes a survivor invisible to `git status`, the signal the intake used to identify the phantom at BUGFIX_REQUEST.md:45). Neither belongs in this change; if either is wanted, it is an ADR-level decision.",
                  "WINDOWS SPECIFICS. The intake names an AV scanner holding a handle on a freshly-written `.py` as one cause of a failed `finally`. After the fix that only ever affects a tempdir, but `shutil.rmtree` on a tempdir can still raise PermissionError on Windows for the same reason — swallow that narrowly (it is scratch outside the repo) rather than letting the cleanup fail a green test, and never widen the same tolerance to the repo-side assertions."
              ],
    "files_to_touch":  [
                           {
                               "path":  "tests/test_no_fixed_offsets.py",
                               "change":  "Phase 1. Add `PACKAGE_RELATIVE`; keep `SCAN_ROOT` (:96-97) derived from it. Give `parser_modules` (:345-354) and `parser_module_violations` (:357-363) a `tree_root: Path = REPO_ROOT` parameter, and change :361\u0027s `relative_to(REPO_ROOT)` to `relative_to(tree_root)`. `test_no_parser_module_seeks_to_a_fixed_offset` (:569-575) keeps calling with no arguments — comment saying so. No rule change, no docstring residual change."
                           },
                           {
                               "path":  "tests/fixtures/guard_trees.py",
                               "change":  "NEW (Phase 2, extended in Phase 3). `mirrored_package()` -\u003e a repo-shaped tmp tree holding a byte-faithful copytree of src/ootp_ai (ignoring __pycache__); a `plant()` helper; and in Phase 3 `mirrored_repo()` -\u003e a `git init`-ed tmp repo carrying a copy of the real .gitignore. tempfile + pathlib only, no pytest dependency (it is imported inside ABORT_CHILD\u0027s child process), mypy-strict annotated. Its docstring is the operative statement of the convention."
                           },
                           {
                               "path":  "tests/test_fixed_offset_guard_scope.py",
                               "change":  "Phase 2. Re-document `PARSER_DIR` (:60) as the live package the probe must never reach. Rewrite `parser_probe` (:81-98) to plant into a caller-supplied or private mirror while keeping its two-positional-arg call shape and `str` yield. Replace the fidelity paragraph at :85-86 with the faithful-copy argument. Repoint the six real-scan call sites (:112, :127, :133, :180 stays live, :431) and rename the two \u0027…in_the_real_tree\u0027 tests. Keep :137-150 and :176-184 on the live tree. Add four new tests: production scan root, no-argument production call (via inspect.getsource), mirror faithfulness, mirror module count."
                           },
                           {
                               "path":  "tests/test_guard_probe_isolation.py",
                               "change":  "DO NOT EDIT the assertions — it is the red-goes-green evidence and it must pass untouched. At most append to the module docstring recording that it now passes and naming the fix. Touch `ABORT_CHILD` (:46-57) only if `parser_probe`\u0027s signature changed, which this plan is designed to avoid."
                           },
                           {
                               "path":  "tests/test_no_leaks.py",
                               "change":  "Phase 3, gated on the parity measurement. Keyword-only `repo: Path = REPO_ROOT` on `git_paths` (:44-67, threaded into `cwd=`), `scannable_text_files` (:70-106), `machine_path_violations` (:139-165) and `game_data_offenders` (:173-194). `test_no_machine_paths_or_identifiers` (:168-170) and `test_game_data_is_not_tracked` (:197-200) keep calling with defaults."
                           },
                           {
                               "path":  "tests/test_leak_guard_scope.py",
                               "change":  "Phase 3. Point the ten planting tests at `mirrored_repo()`; leave the floor (:224-238) and junk-directory (:97-105) tests on the real repo. Fix the zero-argument monkeypatch lambda at :251. Add the production-still-reads-the-real-repo compensations."
                           },
                           {
                               "path":  ".claude/agents/data-engineer-memory.md",
                               "change":  "Phase 4. APPEND one entry (never edit :351-356, which prescribes the hazardous \u0027removed in finally\u0027 pattern; follow the supersede-by-appending precedent at :340-350). Exact bullet shape from :25-37, a real epistemic label, inline-code paths not markdown links."
                           },
                           {
                               "path":  "docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md",
                               "change":  "NEW (Phase 4). The convention as a decision: plant only in a tree you own; a test that reads the live tree plants nothing; fidelity is bought with a byte-faithful copy plus a compensating assertion that production reads the original. Must carry a ## Consequences section stating the cost."
                           },
                           {
                               "path":  "docs/decisions/README.md",
                               "change":  "Phase 4. Index the new ADR — tests/test_repo_structure.py:33-40 fails the build on an unindexed one."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_PLAN.md",
                               "change":  "This plan. Status blockquote `planned · created \u003ctoday\u003e · decided · next: implement`, per the grammar at requests/bugfix-requests/README.md:45."
                           },
                           {
                               "path":  "requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md",
                               "change":  "NEW (Phase 4). The measured evidence: exit-97 mode-A run, the concurrent-session round counts, copy-cost timing, and the six temp-repo parity properties if Phase 3 ran."
                           },
                           {
                               "path":  "requests/bugfix-requests/README.md",
                               "change":  "Index row :54 Stage cell — `diagnosed` -\u003e `planned` when this plan lands, -\u003e `fixed` when the work does. Add a follow-up row if Phase 3 is deferred rather than done."
                           },
                           {
                               "path":  "tests/fixtures/README.md",
                               "change":  "Phase 4, if the doc gate agrees. Its \u0027What belongs here\u0027 (:30-43) describes committed inputs; a tree-mirroring harness helper is a third kind (as `fixtures/warehouse.py` already is). One line, or leave it to /update-docs."
                           },
                           {
                               "path":  "tests/conftest.py",
                               "change":  "NEW and OPTIONAL (Phase 5 only). A `pytest_sessionstart` hook that REPORTS and removes survivors from pre-fix revisions. None exists today; verify pass counts and cross-module imports are unchanged if it is added. Recommend skipping unless a real survivor is found."
                           }
                       ],
    "code_references":  [
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:92-98 (parser_probe body)",
                                "claim":  "Writes a real module into PARSER_DIR and unlinks it in a `finally` — the mutation of shared state that is the cause. The `finally` is the mitigation mode A defeats and mode B ignores."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:85-86 (parser_probe docstring)",
                                "claim":  "\u0027A `tmp_path` fixture cannot serve: the scan enumerates the package on disk, so the probe has to exist inside it to be a fair test of what the scan actually reads\u0027 — the fidelity argument the RCA hands to this plan. The faithful-copy mirror answers it; this paragraph gets rewritten, not deleted silently."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:60 (PARSER_DIR)",
                                "claim":  "`REPO_ROOT / \"src\" / \"ootp_ai\" / \"parser\"`. Survives the fix with a changed role: the live package the probe must never reach. tests/test_guard_probe_isolation.py:35 imports it and :62 globs it."
                            },
                            {
                                "ref":  "tests/test_fixed_offset_guard_scope.py:137-150 (test_the_module_set_has_a_floor)",
                                "claim":  "Calls `guard.parser_modules()` with no argument, floor \u003e=12. Must keep running against the live package or the fix buys a vacuous guard. Its message says \u0027it has been covering 18\u0027; measured today the real count is 37, so the prose is stale while the floor is still correct."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:345-354 (parser_modules)",
                                "claim":  "`sorted(SCAN_ROOT.rglob(\"*.py\"))` plus a non-vacuity assertion, and it takes no root parameter — the missing seam."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:361",
                                "claim":  "`rel = path.relative_to(REPO_ROOT).as_posix()` — the exact line that makes the RCA\u0027s sketched `root=` parameter raise ValueError on a tmp tree, and the line that produces the string EXEMPT_MODULES is keyed on."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:104-107 (EXEMPT_MODULES)",
                                "claim":  "Two repo-relative posix strings, `src/ootp_ai/parser/lookahead.py` and `.../primitives.py`. A mirror laid out as `\u003ctmp\u003e/src/ootp_ai/...` keeps these keys valid; any other layout silently un-exempts the sanctioned seam."
                            },
                            {
                                "ref":  "tests/test_no_fixed_offsets.py:569-575",
                                "claim":  "`test_no_parser_module_seeks_to_a_fixed_offset` — the test that goes red on a phantom file. It must keep calling `parser_module_violations()` with no arguments, pinned by a new source-level assertion."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:46-57 (ABORT_CHILD) and :55",
                                "claim":  "Child-process source calling `parser_probe(\"_guard_scope_abort_probe.py\", OFFENDER)` positionally. Any signature change turns exit 97 into exit 1 and the repro fails saying the child never reached the probe (:83-87)."
                            },
                            {
                                "ref":  "tests/test_guard_probe_isolation.py:111-112",
                                "claim":  "`with parser_probe(...) as rel:` then `if rel in v` — the fixture must keep yielding a plain `str`, so the tree root cannot be smuggled out by changing the yield to a tuple."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:40-53 (untracked_file)",
                                "claim":  "The second site of the class: writes a real file into the live repo, name-keyed clobber assert at :48, cleanup in a `finally` at :52-53."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:37 (LEAK)",
                                "claim":  "A banned machine-path string assembled at runtime. It is what makes a leak-guard survivor worse than a parser one — a survivor carries a banned string into the repo root and reddens the repo\u0027s only leak protection."
                            },
                            {
                                "ref":  "tests/test_leak_guard_scope.py:250-253",
                                "claim":  "`monkeypatch.setattr(guard, \"scannable_text_files\", lambda: [...])` — a ZERO-argument lambda. Adding a `repo` parameter to the real function breaks this test with a TypeError unless the lambda is updated in the same edit."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:60-65 (git_paths subprocess)",
                                "claim":  "`git ls-files -z ...` with `cwd=REPO_ROOT` — the leak guard\u0027s scope is hard-wired to the real repo, which is why un-sharing it is harder than the parser case and needs a `git init`-ed mirror."
                            },
                            {
                                "ref":  "tests/test_no_leaks.py:180-186 (game_data_offenders docstring)",
                                "claim":  "Measured: `tests/fixtures/` and `datasets/` are NOT covered by the .gitignore game-data block because git is last-match-wins. This property must be re-measured inside any temp repo before the `.dat` probe test is moved there."
                            },
                            {
                                "ref":  "tests/test_grain_contracts.py:364-380 (source_modules)",
                                "claim":  "A SECOND whole-tree reader of `src/ootp_ai` with the same rglob (SCAN_ROOT at :75). Confirms a survivor is visible to more than the headline guard; do not widen the RCA\u0027s measured blast radius without measuring this one."
                            },
                            {
                                "ref":  ".claude/agents/data-engineer.md:154-165 and :171-172",
                                "claim":  "`tests/` heads the repo-level deny set for the write-capable subagent, and a spec whose targets land there must be stopped and reported. This entire fix is under tests/, so the main thread implements it directly."
                            },
                            {
                                "ref":  "tests/test_agent_contract.py:76-81",
                                "claim":  "`test_deny_set_still_protects_the_guards` asserts `tests/` stays in that deny set — the convention above is enforced, not advisory."
                            },
                            {
                                "ref":  ".claude/agents/data-engineer-memory.md:351-356",
                                "claim":  "The 2026-08-18 `measured` entry prescribing \u0027a planted offender written to disk and removed in `finally`\u0027 — the pattern this fix supersedes. Append a new entry; never edit it (the file is append-only per :39-53, and :340-350 shows the house form for dating a prior entry)."
                            },
                            {
                                "ref":  "tests/test_agent_contract.py:84-95",
                                "claim":  "Every memory bullet must carry one of five epistemic labels in a fixed shape, checked mechanically — the new entry fails CI if it does not."
                            },
                            {
                                "ref":  "pyproject.toml:98-108",
                                "claim":  "`addopts = \"-q --strict-markers --strict-config\"`, one marker, no xdist — the reason plant and scan are sequential within a session and CI has never gone red on this. Consequence: a green CI run cannot be the mode-B evidence."
                            },
                            {
                                "ref":  "pyproject.toml:88 and :91-95",
                                "claim":  "`known-first-party = [\"ootp_ai\", \"fixtures\"]`, and mypy strict over both src and tests — the shared helper belongs in tests/fixtures/ (imported `from fixtures.guard_trees import ...`, as tests/test_catalog.py:48 does for fixtures.warehouse) and must be fully annotated."
                            },
                            {
                                "ref":  ".github/workflows/ci.yml:45-57",
                                "claim":  "The four gates each phase checkpoint mirrors locally: ruff check, ruff format --check, mypy, pytest -m \"not gamedata\". `ruff format --check` is the intake\u0027s second red gate, so it is not optional here."
                            },
                            {
                                "ref":  "requests/feature-requests/first-sight/reviews/phase-10-acceptance-panel.md:84-87",
                                "claim":  "M5 — the lenses ran concurrently against one shared working tree and at least two reds were cross-contamination, including a test_no_fixed_offsets failure from a sibling planting a probe. The documented mode-B sighting, and the reason acceptance must include a concurrent two-session run."
                            },
                            {
                                "ref":  "requests/feature-requests/first-sight/reviews/phase-7-acceptance-panel.md:63",
                                "claim":  "CF-14 — test_doc_links races the leak-guard probe files planted at the repo root; recorded as unreachable in single-process CI and carried forward unfixed. Phase 3\u0027s concurrency run is what closes it."
                            },
                            {
                                "ref":  "docs/decisions/0020-sanctioned-lookahead-seam.md:95-102",
                                "claim":  "The ADR leans on tests/test_fixed_offset_guard_scope.py pinning six residuals as executable controls. Those controls call `scan_source` on strings (:285-447) and are untouched by moving the probe, so the ADR needs no amendment — confirm this rather than editing an accepted ADR."
                            },
                            {
                                "ref":  "tests/test_repo_structure.py:33-40, :43-57, :60-67",
                                "claim":  "A new ADR must be indexed in docs/decisions/README.md, must state its cost, and must be sequentially numbered. 0001-0021 exist, so the new one is 0022."
                            },
                            {
                                "ref":  "requests/bugfix-requests/README.md:24-26 and :45",
                                "claim":  "\u0027Done\u0027 means the red reproduction goes green and a regression test is left behind; the status grammar is intake -\u003e diagnosed -\u003e planned -\u003e fixed. The Index row for this slug is :54."
                            }
                        ],
    "open_questions":  [
                           "Handed over by the RCA (:166-170), answered by this plan, and re-openable at the gate: does the fidelity argument at test_fixed_offset_guard_scope.py:85-86 survive a parameterised root? This plan says it survives only with the copy-the-package variant plus three compensating assertions, and that the cheap tmp_path version does not. If the operator disagrees, the cheap version is one edit away — but then the end-to-end \u0027seen to fail\u0027 claim weakens to \u0027the scan reads a directory\u0027.",
                           "Also handed over: is the name-aware guard message acceptable at all (RCA hardening (b))? This plan says no — a guard knowing about its own test trades against ADR 0020\u0027s enforcement, and after Phase 2 it protects against nothing that can still happen. It is listed as an explicit non-goal rather than silently dropped, so the gate can overturn it.",
                           "Also handed over: same change or follow-up for tests/test_leak_guard_scope.py? This plan says same change (Phase 3), gated on a parity measurement, because a survivor there is strictly worse and because the RCA\u0027s stated worst outcome is two independent fixes. The fallback — file it with its own Index row and keep the shared helper — is written into the phase so a deferral stays honest.",
                           "UNCONFIRMED and must be measured before Phase 3 builds on it: does a `git init`-ed temp repo carrying a copy of the real .gitignore reproduce all six enumeration properties the moved leak-guard tests depend on? The empty index changes what `--cached` means, and `--exclude-standard` also consults .git/info/exclude and the user\u0027s global excludesfile. Nobody has run it; the phase opens with the measurement and stops if it fails.",
                           "Is a session-scoped survivor sweep worth shipping at all once Phases 1-3 make new survivors impossible? The RCA says its only value is cleaning survivors from older revisions. This plan recommends a one-time manual check instead of new permanent machinery in a repo that currently has no tests/conftest.py.",
                           "Should the convention be an ADR (0022) or only a helper docstring plus a memory entry? This plan says ADR, because the RCA\u0027s root tier is explicitly about stopping a third site being invented and because ADRs are the artifact this repo checks for indexing and cost. A lighter answer is defensible if the operator would rather not spend an ADR number on a testing convention."
                       ]
}
```
