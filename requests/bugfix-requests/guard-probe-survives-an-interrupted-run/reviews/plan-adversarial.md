# Plan panel - adversarial findings, meta-audit, convergence

Panel health: planners_ok 3/3, adversaries_ok 2/2, meta_audit_ok 1/1, findings 47, blockers 0, majors 13. No degraded lenses.

## Adversary findings (code-grounded + executability)

```json
[
    {
        "id":  "CG-01",
        "title":  "Three per-phase pytest selectors run tests/test_grain_contracts.py without `-m \"not gamedata\"`, so 7 MySQL-dependent tests execute and fail",
        "severity":  "major",
        "confidence":  "high",
        "category":  "correctness",
        "location":  "tests/test_grain_contracts.py:442",
        "problem":  "Phase 0\u0027s acceptance criterion is `uv run pytest tests/test_fixed_offset_guard_scope.py tests/test_no_fixed_offsets.py tests/test_grain_contracts.py` GREEN; the same module appears in the testing section\u0027s Phase-0 selector and in Phase 1\u0027s mode-B concurrency command (`uv run pytest tests/test_no_fixed_offsets.py tests/test_grain_contracts.py`). A bare module-path selector does NOT apply the `-m \"not gamedata\"` filter — `pyproject.toml:100` sets `addopts = \"-q --strict-markers --strict-config\"` with no marker exclusion. `tests/test_grain_contracts.py` carries seven `@pytest.mark.gamedata` tests (:442, :456, :482, :518, :561, :586, :624) that land a real snapshot into MySQL. On any machine without a populated warehouse — which includes CI and any cold implementer\u0027s first run — that selector is red for reasons unrelated to this change. The plan then compounds it: its own testing section says \"If a `gamedata` test starts failing, something else is wrong — do not absorb it into this request\", so the implementer is told to treat a red the plan itself commanded as an unrelated emergency. Phase 1\u0027s mode-B round counting is worse: it is a 10+ round loop that would report reds every round.",
        "proposed_fix":  "Append `-m \"not gamedata\"` to every per-phase selector that names `tests/test_grain_contracts.py` — Phase 0\u0027s acceptance, the testing section\u0027s Phase-0 line, and Phase 1\u0027s mode-B command. Simplest correct form: `uv run pytest -m \"not gamedata\" tests/test_fixed_offset_guard_scope.py tests/test_no_fixed_offsets.py tests/test_grain_contracts.py`. The other named modules (test_fixed_offset_guard_scope, test_no_fixed_offsets, test_guard_probe_isolation, test_leak_guard_scope, test_no_leaks, test_doc_links, test_repo_structure, test_agent_contract) carry zero gamedata marks — verified — so only the grain-contracts selectors need it.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-02",
        "title":  "Phase 4\u0027s \"zero allowlist entries\" is falsified by a REPO_ROOT-derived `.unlink(` the plan explicitly forbids editing",
        "severity":  "major",
        "confidence":  "high",
        "category":  "correctness",
        "location":  "tests/test_guard_probe_isolation.py:97",
        "problem":  "Phase 4 defines the rule as \"a write call (`.write_text(`, `.write_bytes(`, `.touch(`, `.mkdir(`, `.unlink(`, `os.makedirs`) whose target derives from a name bound to `REPO_ROOT` — directly, or through a module-level constant such as `PARSER_DIR = REPO_ROOT / ...`\" and asserts it lands with ZERO allowlist entries, calling that \"measured\". It is not measured correctly. `tests/test_guard_probe_isolation.py:97` is `survivor.unlink(missing_ok=True)`, iterating `_planted_probes()` (:60-62), which globs `PARSER_DIR` — imported from the scope module at :35 and bound to `REPO_ROOT / \"src\" / \"ootp_ai\" / \"parser\"` at tests/test_fixed_offset_guard_scope.py:60. That is exactly the shape the rule bans, and the plan\u0027s files_to_touch says of that file: \"the exit-code assertion (:83-87) and the survivor assertion (:89-94) stay exactly as they are\" — the `finally` at :95-97 is inside that preserved region. The plan\u0027s enumeration of \"the complete set of REPO_ROOT-derived writes under tests/\" (`test_fixed_offset_guard_scope.py:94`, `test_leak_guard_scope.py:49`, and the two mkdirs at `:89,183`) also omits the two matching `.unlink(` calls at `tests/test_fixed_offset_guard_scope.py:98` and `tests/test_leak_guard_scope.py:53` — those two do go away with the mirrors, but :97 does not. Phase 4 therefore lands red, and the cheapest wrong fix is adding the allowlist entry the phase\u0027s whole argument says must not exist.",
        "proposed_fix":  "Either (a) scope the rule to CREATIVE writes only — `.write_text(`, `.write_bytes(`, `.touch(`, `.mkdir(`, `os.makedirs` — matching `tests/test_read_only.py:337`\u0027s `CREATIVE_CALLS` exactly, and drop `.unlink(` (a cleanup of a survivor is the one repo-side write the residue story deliberately permits); or (b) keep `.unlink(` and make the `finally` at tests/test_guard_probe_isolation.py:95-97 an explicit, argued second self-exemption, stating in the module docstring why deleting a survivor is not planting one. Prefer (a): it keeps the zero-allowlist claim true, and it aligns the verb set with the in-repo precedent the plan already cites. Re-run the enumeration before asserting \"zero\" — the correct pre-phase set is :94/:98 in the fixed-offset scope module, :49/:53/:89/:183 in the leak scope module, and :97 in the isolation repro.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-03",
        "title":  "Phase 2\u0027s source-text assertion will fire on `parser_probe`\u0027s own legitimate yield string and on the docstring Phase 1 rewrites",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "correctness",
        "location":  "tests/test_fixed_offset_guard_scope.py:96",
        "problem":  "Phase 2 adds `test_the_probe_fixture_cannot_reach_the_live_package()`, asserting via `inspect.getsource(parser_probe)` that its body \"contains no reference to `PARSER_DIR` and no `REPO_ROOT`-derived write target\". I confirmed `inspect.getsource` resolves through the `@contextmanager` wrapper and returns the decorator line, signature, full docstring and body (measured on the live function). Two collisions follow. First, Phase 1 requires the fixture to keep yielding `f\"src/ootp_ai/parser/{name}\"` (:96) so every `rel in v` assertion at :113, :127, :432 and tests/test_guard_probe_isolation.py:112 keeps matching — so the source legitimately contains the live package path as a literal, and any substring check for a \"REPO_ROOT-derived write target\" spelled that way cries wolf. Second, Phase 1 also instructs a rewritten docstring that discusses the live package and the compensating assertions; if it uses the token `PARSER_DIR` in prose the assertion fires on a comment. A guard that fires on its own subject\u0027s docstring is precisely the cry-wolf failure this repo\u0027s guards are written to avoid (tests/test_fixed_offset_guard_scope.py:223-227).",
        "proposed_fix":  "Make the assertion structural rather than textual: `ast.parse(inspect.getsource(parser_probe))`, walk it, and assert no `ast.Name` with `id == \"PARSER_DIR\"` and no `ast.Name` with `id == \"REPO_ROOT\"` appears anywhere in the function body — which ignores strings, docstrings and comments by construction. If a text check is kept instead, strip the docstring first (`ast.get_docstring`) and check for the bare identifier `PARSER_DIR` with word boundaries, never for the path literal `src/ootp_ai/parser/`.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-04",
        "title":  "\"Eight pinned residuals\" is wrong — the module pins five; ADR 0020 and the request Index both say six",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "accuracy",
        "location":  "tests/test_fixed_offset_guard_scope.py:28",
        "problem":  "Phase 1\u0027s acceptance criterion says \"The scope module\u0027s six cry-wolf controls and eight pinned residuals are present in the same number and unchanged in rule — a phase that quietly dropped one has widened the fixed-offset ban\u0027s blind spot\". The six cry-wolf controls are correct (`CRY_WOLF` at :229-270 holds exactly six entries — verified). \"Eight\" is not. The module\u0027s own docstring at :28 says \"Five of these tests assert that something is **not** flagged which arguably should be\", and there are exactly five `_is_a_documented_hole` tests (:285, :324, :338, :371, :391). Two independent tracked artifacts say six: `docs/decisions/0020-sanctioned-lookahead-seam.md:95` (\"The guard\u0027s docstring names **six** things it cannot see, and `tests/test_fixed_offset_guard_scope.py` pins every one\") and `requests/bugfix-requests/README.md:51` (\"Six residuals are named and pinned\"). No artifact anywhere says eight. An acceptance criterion phrased as a countable with a fabricated number is not checkable: the implementer either concludes they lost three residuals and goes hunting, or silently ignores the criterion.",
        "proposed_fix":  "Replace the count with the check that actually matters: \"the six `CRY_WOLF` entries and every `..._is_a_documented_hole` test are present and unchanged in rule\". If a number is wanted, use six and cite `docs/decisions/0020-sanctioned-lookahead-seam.md:95` as its source — but note the pre-existing five-vs-six discrepancy between that ADR and tests/test_fixed_offset_guard_scope.py:28, and leave reconciling it to `/update-docs` rather than absorbing it into this request.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-05",
        "title":  "The mypy \"80 → 81 files\" baseline is stale: a clean tree today reports 81, so the plan\u0027s own signal reads as a survivor",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "accuracy",
        "location":  "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md:84",
        "problem":  "The plan repeats \"mypy silently widens 80 → 81\" in four places — the architecture map, onboarding\u0027s BUGFIX_REQUEST entry, Phase 0\u0027s baseline step, and the testing section\u0027s regression list — and Phase 1\u0027s acceptance says \"mypy\u0027s file count is stable\". Measured on the current clean tree (`git status --porcelain --untracked-files=all` empty): `uv run mypy` reports **\"Success: no issues found in 81 source files\"**, and 37 `src/ootp_ai/**/*.py` + 44 `tests/**/*.py` = 81. The intake\u0027s 80 was measured before `tests/test_guard_probe_isolation.py` landed with the RCA (commit 1296c8f, \"File the guard-probe survivor at intake\"). A cold implementer who reads \"the clean baseline is 80\" and then sees 81 on a clean checkout will conclude a survivor is present and go hunting for a phantom — the exact cost this whole request exists to stop.",
        "proposed_fix":  "Stop quoting 80 as the current baseline. Phase 0 already instructs recording the number first; make that the only source of truth and say so explicitly: \"record `uv run mypy`\u0027s file count on the clean tree before editing (measured 2026-08-21: **81**, = 37 src + 44 tests); a survivor adds one to whatever you recorded.\" Where BUGFIX_REQUEST.md:84\u0027s 80 → 81 is cited, label it as the intake-date measurement rather than today\u0027s baseline.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-06",
        "title":  "`git status --porcelain --untracked-files=all` \"must print nothing\" can never hold at a mid-phase checkpoint",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "correctness",
        "location":  "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md:45",
        "problem":  "The testing section elevates `git status --porcelain --untracked-files=all` to \"the one command this bug makes mandatory\" and states flatly \"It must print nothing after a full suite run.\" It cannot. Every phase checkpoint runs with the phase\u0027s own uncommitted edits in the working tree — Phase 0 alone adds a new tracked-to-be file (`tests/fixtures/guard_trees.py`, which shows as `??`) plus modifications to two test modules — so the command prints several lines at every checkpoint by design. Phase 0\u0027s own acceptance is self-consistent (\"shows only the intended edits\"), but Phase 1\u0027s, Phase 3\u0027s and the testing section\u0027s absolute phrasing contradict it. An implementer following the absolute reading either stages prematurely to silence it or concludes the fix leaked.",
        "proposed_fix":  "Restate the gate as the property the intake\u0027s step 4 actually used (BUGFIX_REQUEST.md:45 — a `??` entry for a probe): after a full suite run, `git status --porcelain --untracked-files=all` must show **no path under `src/`**, **no `_guard_scope*_probe.py` anywhere**, and **no `_leak_guard*` path** at the repo root, `var/tmp/`, `requests/bugfix-requests/` or `tests/fixtures/` — beyond that, only the phase\u0027s intended edits. Apply the same wording to Phase 1 and Phase 3\u0027s acceptance lists.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-07",
        "title":  "Moving `test_the_probe_is_removed_even_though_the_scan_read_it` onto a mirror makes its post-block assertion tautological unless the mirror outlives the probe",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "test-design",
        "location":  "tests/test_fixed_offset_guard_scope.py:134",
        "problem":  "Today the test asserts `(PARSER_DIR / \"_guard_scope_cleanup_probe.py\").exists()` inside the with-block (:133) and `not ...exists()` after it (:134) — meaningful because `PARSER_DIR` outlives the context. Phase 1 says these \"become the mirror path\" and separately says `parser_probe(name, body)` with `tree_root=None` \"opens its own `mirrored_package()` and owns it for the life of the context\". If this test uses the default root, the tempdir is destroyed on context exit, so `not path.exists()` at :134 passes whether or not the `finally` unlinked anything — the one assertion in the module that proves cleanup happens becomes vacuous. That is the same class of defect as the leak-guard no-op mutant recorded at tests/test_leak_guard_scope.py:196-200.",
        "proposed_fix":  "Make the step explicit for this test: `with mirrored_package() as tree:` OUTSIDE, then `with parser_probe(\"_guard_scope_cleanup_probe.py\", OFFENDER, tree_root=tree):` inside, and assert against `tree / \"src\" / \"ootp_ai\" / \"parser\" / \"_guard_scope_cleanup_probe.py\"` after the inner block exits but before the outer one does. Phase 1\u0027s step already prescribes the two-context form for the other three plant sites; state that this site requires it for correctness, not just symmetry.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-08",
        "title":  "The forward-reference risk is misstated: test_doc_links only scans markdown links and bare `requests/...` tokens, not arbitrary paths",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "accuracy",
        "location":  "tests/test_doc_links.py:48",
        "problem":  "Both the risks list and Phase 5\u0027s step assert that because `tests/fixtures/guard_trees.py` and `tests/test_probe_isolation_contract.py` do not exist until Phases 0 and 4, \"every mention of them in the plan and report must sit inside a fenced code block\". That is not what the guard does. `BARE_REQUEST_TOKEN` at :48 matches only `requests/...` prefixed tokens, and `LINK` at :20 matches only `[text](target)` markdown-link syntax; `test_relative_links_resolve` (:174-184) and `test_bare_request_tokens_resolve` (:187-201) are the only two checks. A backticked `tests/fixtures/guard_trees.py` in prose is invisible to both. The real and under-emphasised exposure is the opposite one: this plan and the report will name `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md` before it exists, and `bare_request_tokens` resolves it against the filesystem at :154 with deliberately NO exemption for a document\u0027s own directory — its docstring at :144-150 records that a draft carried one and it was removed.",
        "proposed_fix":  "Rewrite the risk to name the actual trigger: any `requests/...` token, and any markdown link, whose target does not yet exist on disk must be fenced (`strip_fences`, :55, is the documented remedy per :149) — with `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md` called out by name as the one this plan certainly contains. Drop the claim that non-`requests/` code paths need fencing; it sends the implementer chasing a constraint the guard does not impose.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-09",
        "title":  "`tests/fixtures/` already holds four non-data harness modules, not one — the Phase 5 README line understates the exception it documents",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "accuracy",
        "location":  "tests/fixtures/README.md:30",
        "problem":  "Phase 5\u0027s step and the files_to_touch entry both describe `tests/fixtures/README.md:30-36` as documenting \"committed DATA fixtures only while `warehouse.py` is already a harness\", framing `guard_trees.py` as making explicit \"a second undocumented exception\". The directory in fact contains four non-data modules besides `__init__.py`: `synthetic.py` (byte builders — its own docstring opens \"**Functions, not data files.**\"), `warehouse.py` (landing harness), `reports.py` (shared rendering expectations), and `tiers.py` (a shared vocabulary that its docstring says lives under `tests/` \"for a reason that is not tidiness\"). So the README\u0027s \"What belongs here\" (:32-36 — synthetic binary records, expected-value tables) has been out of step with the directory for some time, and `guard_trees.py` would be the fifth such module, not the second. A one-line addition framed around a single prior exception documents the wrong thing.",
        "proposed_fix":  "Change the Phase 5 step to add a third bullet naming the CLASS rather than a second instance: \"**Shared test harnesses** — setup and builders imported by name so a reader sees the setup rather than inheriting it (`synthetic.py`, `warehouse.py`, `reports.py`, `tiers.py`, `guard_trees.py`); see `tests/fixtures/warehouse.py` for why these are not a `conftest.py`.\" Keep the citation to warehouse.py:4-5, which is where the no-conftest reasoning actually lives.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-10",
        "title":  "The plan asks for tempdir paths in the implementation report, which the leak guard bans",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "correctness",
        "location":  "tests/test_no_leaks.py:38",
        "problem":  "Phase 5\u0027s IMPLEMENTATION_REPORT step asks for \"the copytree and `git init` timings, the seven parity verdicts, ... the mode-A exit-97 result\" as recorded evidence, and Phase 1\u0027s mutation log records where mirrors were built. Both mirrors live under the OS temp root — on this platform `\u003cdrive\u003e\\\u003cuser\u003e\\\u003cuser\u003e\\AppData\\Local\\Temp\\...`. `PATTERNS` at tests/test_no_leaks.py:38 bans `[A-Za-z]:[\\\\/]` (windows drive path) and :39 bans `/Users/[A-Za-z]` (unix home path), and `.md` is in the scanned `keep` set (:86). A report that quotes a mirror\u0027s absolute path — the natural way to evidence \"the abort child leaks one tempdir per run, by design\", which the risks section explicitly wants recorded — turns `test_no_machine_paths_or_identifiers` red, in the very change whose Phase 3 re-roots that guard\u0027s own scope tests. The leak scope module\u0027s docstring at :16-18 already states the constraint in general form: \"a report about a leak cannot quote the leak.\"",
        "proposed_fix":  "Add an explicit instruction to the Phase 5 report step: describe temp locations by shape only — \"a `TemporaryDirectory` under the OS temp root, prefixed `ootp_guard_mirror_`\" — never by absolute path, and quote no tempdir path in any tracked artifact. Same rule for the `reviews/` handoff. Cite tests/test_no_leaks.py:37-41 and the EXEMPT_PREFIXES refusal at :23-31 so the implementer does not reach for an exemption instead.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-11",
        "title":  "Phase 0\u0027s new production-root test duplicates an existing assertion it does not cite as duplicated",
        "severity":  "nit",
        "confidence":  "high",
        "category":  "simplification",
        "location":  "tests/test_fixed_offset_guard_scope.py:180",
        "problem":  "Phase 0\u0027s `test_the_production_scan_root_is_the_live_package()` is specified to assert three things, the third being \"that BOTH `guard.EXEMPT_MODULES` entries appear in `{p.relative_to(REPO_ROOT).as_posix() for p in guard.parser_modules()}`\". That is verbatim what `test_an_allowlisted_path_matches_what_the_real_scan_builds` already does at :180-184, parametrised over `guard.EXEMPT_MODULES` at :176 — a test the plan elsewhere (correctly) insists must keep observing production. Two tests asserting the same thing with different messages means a future failure names whichever collected first, and the second reads as redundant to the next reader.",
        "proposed_fix":  "Drop the third assertion from the new test and keep it to the two things that are genuinely new: `guard.SCAN_ROOT == REPO_ROOT / \"src\" / \"ootp_ai\"`, and a no-argument `guard.parser_modules()` returning only paths under it. Add a one-line comment pointing at :176-184 for the allowlist-string half, so the pairing is visible rather than duplicated.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-12",
        "title":  "\"37 byte-identical copies\" undercounts the mirror by the probe itself",
        "severity":  "nit",
        "confidence":  "high",
        "category":  "accuracy",
        "location":  "tests/test_no_fixed_offsets.py:352",
        "problem":  "Phase 1\u0027s docstring-replacement step says the probe \"still sits among 37 byte-identical copies of the real modules\". Measured: `src/ootp_ai/**/*.py` is exactly 37 files, and `parser_modules()` returns 37 — so with a probe planted the mirror holds 38 and `parser_modules(tree)` returns 38. Meanwhile Phase 0\u0027s `test_the_mirror_holds_the_same_modules_as_the_live_package` compares mirror-vs-live set equality on an UNPLANTED mirror, where 37 is right. The two numbers are describing different states with one figure, which will read as an inconsistency to anyone checking.",
        "proposed_fix":  "Say \"among the package\u0027s 37 real modules\" in the docstring (the probe is the 38th, not one of the 37), and state in the set-equality test\u0027s docstring that it must run on a mirror with nothing planted — otherwise the equality it asserts is false by exactly one entry.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "CG-13",
        "title":  "Phase 3\u0027s `mirrored_repo` must not write the `.gitignore` copy in a way Phase 4\u0027s own rule reads as REPO_ROOT-derived",
        "severity":  "question",
        "confidence":  "medium",
        "category":  "correctness",
        "location":  "tests/test_no_leaks.py:103",
        "problem":  "Phase 3 specifies `mirrored_repo` copies `REPO_ROOT/.gitignore` verbatim into the mirror. The obvious spelling is `(root / \".gitignore\").write_text((REPO_ROOT / \".gitignore\").read_text(encoding=\"utf-8\"), encoding=\"utf-8\")` — a `.write_text(` call in a statement that also mentions `REPO_ROOT`, in a file (`tests/fixtures/guard_trees.py`) that Phase 4\u0027s guard scans under `tests/**`. Whether that trips the guard depends entirely on whether the AST rule keys on the write\u0027s TARGET expression or merely on `REPO_ROOT` appearing anywhere in the statement — the plan says \"whose target derives from a name bound to `REPO_ROOT`\" but never pins the discrimination as a test. The plan already requires cry-wolf controls for a `tmp_path` write, a fixture-root write and a REPO_ROOT-derived read (tests/test_no_leaks.py:103 is cited as the read control) — but not for this shape, which is the one its own new helper introduces.",
        "proposed_fix":  "Add a fourth cry-wolf control to Phase 4, drawn from the helper the plan itself writes: a write whose target is mirror-derived but whose SOURCE argument is `REPO_ROOT`-derived must not fire. Pin it as a string in the contract module\u0027s controls alongside the other three. Alternatively have `mirrored_repo` use `shutil.copy2(REPO_ROOT / \".gitignore\", root / \".gitignore\")`, which is not in the verb set at all — but note that `shutil.copy2` is *not* in `DESTRUCTIVE_CALLS` (tests/test_read_only.py:322-334, and :402 pins that it is deliberately allowed), so this is safe on both guards.",
        "reviewer":  "code-grounded"
    },
    {
        "id":  "EX-01",
        "title":  "Phase 3\u0027s first step depends on two things later steps create",
        "severity":  "major",
        "confidence":  "high",
        "category":  "sequencing",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 3 steps 1-3 (grounded against tests/test_no_leaks.py:216-232 and tests/test_leak_guard_scope.py:40-53)",
        "problem":  "Phase 3 step 1 says \"Re-pin the parity measurement in code FIRST, before moving any test\" and prescribes `test_the_mirror_repo_ignores_what_this_repo_ignores()` pinning seven pairwise `git check-ignore --no-index` verdicts. That test cannot exist yet: `mirrored_repo()` is created in step 2, and the `repo` parameter on `is_git_ignored` (tests/test_no_leaks.py:216, `cwd=REPO_ROOT` at :229) is threaded in step 3. A cold agent following the steps in order writes a test that calls a helper that does not exist against a function signature that does not accept a root. This is exactly the \u0027a phase depends on later work\u0027 failure, one level down.",
        "proposed_fix":  "Reorder Phase 3 to: (1) add `mirrored_repo()` to `tests/fixtures/guard_trees.py`; (2) thread `repo: Path = REPO_ROOT` through `git_paths` (:44/:62), `scannable_text_files` (:70/:100/:103), `machine_path_violations` (:139/:148/:149), `game_data_offenders` (:173/:192) and `is_git_ignored` (:216/:229); (3) land the seven-verdict parity control and STOP HERE for the off-ramp decision; (4) only then move the ten planting tests. Restate the off-ramp as \u0027if step 3 goes red, revert steps 1-2 and stop\u0027, which is now a clean revert boundary.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-02",
        "title":  "Phase 4\u0027s \"ZERO allowlist entries\" acceptance is falsified by a REPO_ROOT-derived unlink Phase 2 deliberately keeps",
        "severity":  "major",
        "confidence":  "high",
        "category":  "acceptance-criterion",
        "location":  "tests/test_guard_probe_isolation.py:95-97",
        "problem":  "Phase 4 bans `.unlink(` among the write verbs and calls a zero-entry allowlist \"the objective proof that Phases 1 and 3 removed every site\". But `tests/test_guard_probe_isolation.py:95-97` is `finally: for survivor in _planted_probes(): survivor.unlink(missing_ok=True)`, and `_planted_probes()` (:60-62) globs the live `PARSER_DIR` — a REPO_ROOT-derived module constant. Phase 2 explicitly says that block \"stays exactly as it is\". I confirmed by scanning every write call under tests/ that this is the one site the plan\u0027s own \"complete set\" (test_fixed_offset_guard_scope.py:94, test_leak_guard_scope.py:49/:89/:183) omits, and it survives Phases 1 and 3. So the implementer either (a) writes a rule that catches it, fails the zero-allowlist criterion, and reaches for the allowlist entry the criterion exists to forbid, or (b) writes a rule narrow enough to miss it, in which case the criterion proves less than claimed and nobody is told.",
        "proposed_fix":  "Decide it in the plan. Either drop `.unlink(` from the verb set and state the rule as \u0027no test CREATES a file or directory in a tree a guard reads\u0027 (deleting a probe that should not exist is the one live-tree write the plan intentionally keeps), or keep `.unlink(` and pre-declare exactly two exemptions — the contract module\u0027s self-exemption and `tests/test_guard_probe_isolation.py`\u0027s residue cleanup — with the count asserted the way `test_the_allowlist_is_exactly_two_entries` (tests/test_fixed_offset_guard_scope.py:156-167) does. Change the acceptance criterion from \u0027ZERO\u0027 to the exact expected count, with the reason for each entry.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-03",
        "title":  "Two acceptance criteria are `grep` commands; this repo\u0027s shell is PowerShell",
        "severity":  "major",
        "confidence":  "high",
        "category":  "environment",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 2 acceptance (`grep -n \u0027_guard_scope\u0027 tests/test_no_fixed_offsets.py`) and Phase 3 acceptance (`grep -n \u0027REPO_ROOT\u0027 tests/test_leak_guard_scope.py`)",
        "problem":  "`grep` does not exist on this platform. `.claude/agents/data-engineer.md:176-177` states outright that the shell is PowerShell, not Bash, and the environment block confirms win32/PowerShell 5.1. A cold agent runs the criterion literally, gets a CommandNotFoundException, and either declares the criterion unverifiable or silently substitutes something weaker. Both acceptance criteria are load-bearing: the first is the ADR-0020 check that the guard learned no probe names, the second is the check that no REPO_ROOT-derived write remains in the leak scope module.",
        "proposed_fix":  "Restate both as `Select-String -Path \u003cfile\u003e -Pattern \u0027\u003cpat\u003e\u0027` (asserting no match), or as an assertion inside the tests themselves so CI enforces them rather than a human. The ADR-0020 one in particular deserves to be a test — `assert \u0027_guard_scope\u0027 not in Path(\u0027tests/test_no_fixed_offsets.py\u0027).read_text()` inside the new residue module — since a prose acceptance criterion checked once never fires again.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-04",
        "title":  "The plan document will redden test_doc_links at Phase 0 by naming IMPLEMENTATION_REPORT.md unfenced",
        "severity":  "major",
        "confidence":  "high",
        "category":  "blocking-check",
        "location":  "tests/test_doc_links.py:48 and :137-156",
        "problem":  "`BARE_REQUEST_TOKEN` (:48) matches any bare `requests/...` path \"written in prose or inside a code span\" — backticks do NOT exempt it, only fences do (`strip_fences`, :55), and the docstring at :143-150 records that there is deliberately NO exemption for a document\u0027s own directory. `markdown_files()` (:159-171) scans every live `.md`, so IMPLEMENTATION_PLAN.md is in scope the moment it lands. The plan\u0027s `files_to_touch` names `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md`, which does not exist until Phase 5. The plan mentions fencing only inside Phase 5\u0027s steps and a risk — not as an authoring instruction for the plan document itself. Result: `uv run pytest -m \"not gamedata\"` is red from the moment the plan is committed, for a reason unrelated to the bug.",
        "proposed_fix":  "Add an explicit authoring instruction at the top of the plan: every `requests/...` path that does not yet exist on disk — `IMPLEMENTATION_REPORT.md` above all — must sit inside a fenced code block in this document and in the report. Verify with `uv run pytest tests/test_doc_links.py` immediately after writing the plan, before Phase 0\u0027s first edit, and add that run to Phase 0\u0027s acceptance list.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-05",
        "title":  "Phase 2\u0027s source-text assertion contradicts the docstring and yield Phase 1 prescribes",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "correctness",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 2 step 3, against tests/test_fixed_offset_guard_scope.py:96",
        "problem":  "Phase 2 adds `test_the_probe_fixture_cannot_reach_the_live_package()` asserting via `inspect.getsource(parser_probe)` that its body \"contains no reference to `PARSER_DIR` and no `REPO_ROOT`-derived write target\". But Phase 1 mandates that `parser_probe` keeps yielding `f\"src/ootp_ai/parser/{name}\"` (:96) — a literal spelling of the live package path — and instructs the implementer to rewrite its docstring to explain the live package the probe must never reach. A naive substring check therefore fails on code the same plan requires. This is the identical hazard the plan correctly identifies for Phase 4 (tests/test_read_only.py:337 and :398 hold the banned verbs as string literals, which is why that guard must be AST-based), repeated here without the same remedy.",
        "proposed_fix":  "Specify the check as AST over the function body with the docstring and every `ast.Constant` string excluded — collect `ast.Name`/`ast.Attribute` identifiers only and assert `PARSER_DIR` and `REPO_ROOT` are absent. State the exclusion in the step, not just \u0027assert via inspect.getsource\u0027. Alternatively drop it: Phase 1\u0027s behavioural `test_no_probe_is_ever_written_into_the_live_package` already asserts the same property without the literal-string trap.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-06",
        "title":  "The import line for the new helper is never written down, and getting it wrong reproduces the ABORT_CHILD trap the plan spends a risk on",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "missing-step",
        "location":  "tests/test_guard_probe_isolation.py:51-53 and pyproject.toml:88",
        "problem":  "`mirrored_package` lives in `tests/fixtures/guard_trees.py` and is imported by `tests/test_fixed_offset_guard_scope.py`, which ABORT_CHILD imports in a bare process after `sys.path.insert(0, str(Path(sys.argv[1]) / \"tests\"))` (:51). The only import form that works there is `from fixtures.guard_trees import mirrored_package` — verified as the house pattern at 20 call sites (e.g. tests/test_grain_contracts.py:65, tests/test_snapshot_semantics.py:63) with `tests/fixtures/__init__.py` present and `known-first-party = [\"ootp_ai\", \"fixtures\"]` at pyproject.toml:88. The plan explains WHY tests/fixtures/ was chosen but never states the literal import line. A `from tests.fixtures...` or relative form passes locally under pytest\u0027s rootdir insertion and kills the child with ImportError → exit 1 → the repro fails with \"the child never reached the probe\" (tests/test_guard_probe_isolation.py:83-87) — reading as a broken test, which is precisely the trap the plan\u0027s top risk warns about.",
        "proposed_fix":  "Write the exact line into Phase 0\u0027s steps: `from fixtures.guard_trees import mirrored_package`, and add a Phase 0 verification step that runs the abort child by hand (`uv run python \u003cscript\u003e \u003crepo-root\u003e`, expect exit 97) BEFORE Phase 1 changes anything, establishing that the import path still works under the added dependency.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-07",
        "title":  "\"eight pinned residuals\" matches no count in the file, so the criterion cannot be checked",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "acceptance-criterion",
        "location":  "tests/test_fixed_offset_guard_scope.py:26-33 and :279-448",
        "problem":  "Phase 1\u0027s acceptance says \"the scope module\u0027s six cry-wolf controls and eight pinned residuals are present in the same number and unchanged in rule\". I counted: `CRY_WOLF` (:229-270) has exactly six entries, so that half is right. But the residuals section holds five `..._is_a_documented_hole` tests (:285, :324, :338, :371, :391), the module docstring at :28 says \"Five of these tests\", ADR 0020:95-96 says the guard\u0027s docstring names SIX things it cannot see, and the section :279-448 contains eleven test functions in total. \"Eight\" matches none of these. A cold agent checking this criterion has no defined thing to count.",
        "proposed_fix":  "Replace with the two numbers that are actually checkable: `len(CRY_WOLF) == 6`, and the five `..._is_a_documented_hole` tests named explicitly (`test_a_fully_hoisted_read_...`, `test_an_attribute_valued_buffer_...`, `test_a_renamed_unannotated_parameter_...`, `test_a_position_composed_into_a_local_...`, `test_an_offset_misnamed_as_a_span_...`). Better: express it as a before/after node-id diff from `--collect-only`, which catches a dropped residual under any name.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-08",
        "title":  "Keeping the clobber assert \"verbatim\" makes it silently vacuous in a fresh mirror",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "guard-vacuity",
        "location":  "tests/test_fixed_offset_guard_scope.py:93",
        "problem":  "Phase 1 says \"Keep the clobber assert (:93) verbatim\". Verbatim, `assert not path.exists(), f\"{name} already exists; refusing to clobber it\"` now runs against a freshly built copytree mirror where the probe name can never pre-exist — so a check the RCA analysed at length (Open Question 3, ROOT_CAUSE_ANALYSIS.md:108-121) becomes an assertion that cannot fire. In a repo whose scope module opens (:9-14) with the record of two guards that were green while guarding nothing, silently converting a live check into a tautology without saying so is the exact failure mode the module exists to prevent.",
        "proposed_fix":  "Keep the line but add a comment recording that it is now near-vacuous by construction and retained only for the caller-supplied-`tree_root` path (where two probes in one mirror would collide). Say the same in the rewritten docstring. If the plan wants the protection back, have `mirrored_package` exclude `_guard_scope*_probe.py` from the copy AND assert the mirror starts clean — see EX-12.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-09",
        "title":  "The mypy file-count criteria are inconsistent across phases and unverifiable as written",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "acceptance-criterion",
        "location":  "pyproject.toml:91-95 and BUGFIX_REQUEST.md:84",
        "problem":  "Phase 0 requires \"mypy\u0027s file count is the baseline plus one\", Phase 1 and Phase 3 require it \"stable\", Phase 4 omits it entirely while adding `tests/test_probe_isolation_contract.py`. With `files = [\"src\", \"tests\"]` (pyproject.toml:95) the count moves +1 at Phase 0 and +1 again at Phase 4, so \"stable\" at Phase 4 would be wrong and its silence hides a legitimate change. The plan also never says where the number is read from (mypy prints it only in its trailing `Success: no issues found in N source files` line), and the baseline of 80 is quoted from BUGFIX_REQUEST.md:84 rather than measured on the branch.",
        "proposed_fix":  "Have Phase 0 step 1 record the actual number from `uv run mypy`\u0027s success line on the current branch, then state the expected value per phase explicitly: baseline+1 after Phase 0, unchanged through Phases 1-3, baseline+2 after Phase 4. Name the success line as the source.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-10",
        "title":  "The mode-B concurrency acceptance has no executable form and no pass/fail definition",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "acceptance-criterion",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 1 and Phase 3 acceptance (\"two shells at once, 10+ rounds\"), grounded at pyproject.toml:98-108",
        "problem":  "The plan correctly argues no single-session run can prove mode B (no xdist, pyproject.toml:98-108) and then makes the two-shell run a mandatory acceptance criterion — but gives no invocation. A cold agent driving a one-command-at-a-time shell tool has no stated way to run two pytest sessions concurrently, no loop, and no definition of a failure beyond \"zero reds\" (which does not say whether a red in EITHER shell counts, nor how to distinguish a real cross-contamination red from a flake). The plan also asserts \"before the fix this is the reproduction\" without prescribing the pre-fix run that would establish the baseline.",
        "proposed_fix":  "Write the concrete form: launch `uv run pytest tests/test_no_fixed_offsets.py tests/test_grain_contracts.py` in a loop with `run_in_background` while running `uv run pytest tests/test_fixed_offset_guard_scope.py` in a loop in the foreground; define red as any non-zero exit in either loop across N rounds; record N and both exit-code streams. Add the pre-fix baseline run at the end of Phase 0 (where the bug is still live) so the after-run has something to be compared against.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-11",
        "title":  "Nothing assigns the requests/ Index transition diagnosed -\u003e planned, and /commit will demand it at the first checkpoint",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "process",
        "location":  "requests/bugfix-requests/README.md:45 and :54",
        "problem":  "The status grammar is `intake → diagnosed → planned → fixed` (:45) and the Index row at :54 currently reads `diagnosed`. Phase 5 moves it `diagnosed → fixed`. Nobody moves it to `planned`, yet `/commit` \"keeps the `requests/` artifact statuses and track Index rows in step with what actually landed\" and will see an IMPLEMENTATION_PLAN.md landing against a row that says `diagnosed`. Phase 0\u0027s checkpoint is where that friction lands, unannounced.",
        "proposed_fix":  "Add a pre-Phase-0 step: commit IMPLEMENTATION_PLAN.md with its own status blockquote and move the Index row at requests/bugfix-requests/README.md:54 to `planned` in the same commit. Then Phase 5\u0027s step becomes `planned → fixed`, matching the grammar.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-12",
        "title":  "mirrored_package copies a live survivor into every mirror, so a pre-existing probe poisons the new tests too",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "robustness",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 0 step 7 (`shutil.copytree` with `ignore_patterns(\"__pycache__\")`)",
        "problem":  "The mirror is a faithful copy of `src/ootp_ai`, and `_guard_scope*_probe.py` residue from an older revision lives in `src/ootp_ai/parser/` — the exact state this request exists to describe. Every mirror then inherits the offender, so `guard.parser_module_violations(tree)` in the new Phase 0 tests carries a violation nobody planted, and the failure reads as a broken mirror rather than as residue. The plan\u0027s own Phase 2 residue detector is the only thing that would name the real cause, and it does not exist until two phases later.",
        "proposed_fix":  "Extend the ignore to `shutil.ignore_patterns(\"__pycache__\", \"_guard_scope*_probe.py\")` and add one assertion inside `mirrored_package` that the freshly built mirror reports zero violations before yielding — which also restores real meaning to the clobber assert flagged in EX-08.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-13",
        "title":  "The baseline one-liner is Bash-quoted and will not run in PowerShell 5.1 as written",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "environment",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 0 step 1",
        "problem":  "The prescribed baseline command is `uv run python -c \"import sys; sys.path.insert(0,\u0027tests\u0027); import test_no_fixed_offsets as g; print(len(g.parser_modules()), len(g.parser_module_violations()))\"`. On Windows PowerShell 5.1 the outer double quotes are consumed by the shell and the embedded single quotes plus semicolons make the argument fragile; a cold agent copy-pastes it and gets a parse error or a mangled `-c` payload, then either skips the baseline or improvises. The baseline (37 modules / 0 violations) is cited as an acceptance criterion in Phases 0 and 5, so losing it costs two checkpoints.",
        "proposed_fix":  "Replace with a form that survives PowerShell — e.g. write a two-line script into the scratchpad and run `uv run python \u003cscript\u003e`, or use `uv run pytest tests/test_fixed_offset_guard_scope.py -k module_set_has_a_floor -s` plus a temporary print. Note in the plan that all commands must be PowerShell-safe (.claude/agents/data-engineer.md:176-177).",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-14",
        "title":  "Phase 1\u0027s REPO_ROOT mutation re-creates this very bug on the implementer\u0027s tree, with no cleanliness re-check prescribed",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "safety",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 1 mutation step (\"temporarily make `mirrored_package` yield `REPO_ROOT`\")",
        "problem":  "That mutation restores the exact defect: `parser_probe` writes `_guard_scope*_probe.py` into the live `src/ootp_ai/parser/`. If the mutation run is interrupted — the failure mode under repair, and one BUGFIX_REQUEST.md:52-53 attributes partly to Windows AV holding a handle on a freshly written `.py` — the implementer leaves a survivor mid-fix and then measures a poisoned tree for the rest of the phase. The plan says \u0027then revert\u0027 but prescribes no post-mutation verification.",
        "proposed_fix":  "After every mutation revert, require `git status --porcelain --untracked-files=all` to print nothing AND `uv run pytest tests/test_no_fixed_offsets.py` to be green, recorded in the report. Scope the mutation run to `tests/test_guard_probe_isolation.py` alone so the blast radius is one module.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-15",
        "title":  "The branch prerequisite is never stated, and five /commit checkpoints on main would be unlandable",
        "severity":  "nit",
        "confidence":  "high",
        "category":  "process",
        "location":  "CLAUDE.md project conventions (\"Work on a branch; land it through a PR. `main` is protected\")",
        "problem":  "The plan\u0027s first mention of branching is Phase 5\u0027s \u0027ASK before opening the PR\u0027. Phases 0-4 each end at a `/commit`, which pushes the feature branch. On this machine HEAD happens to be `guard-probe-survives-an-interrupted-run` already, so the gap is latent rather than live — but a cold agent handed this plan on a fresh clone starts on protected `main` and hits the wall at the first checkpoint.",
        "proposed_fix":  "Add a Phase 0 step zero: confirm `git rev-parse --abbrev-ref HEAD` is a feature branch (not `main`) and that the tree is clean, before recording the baseline. Read-only; no branch creation by a subagent.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-16",
        "title":  "Phase 3\u0027s extension of the residue detector crosses module boundaries with no stated import",
        "severity":  "nit",
        "confidence":  "medium",
        "category":  "missing-step",
        "location":  "IMPLEMENTATION_PLAN draft, Phase 3 step 10, against tests/test_guard_probe_isolation.py:35",
        "problem":  "Phase 2 puts `test_no_probe_residue_is_present_in_the_working_tree` in `tests/test_guard_probe_isolation.py` (a fixed-offset-guard module, importing `OFFENDER, PARSER_DIR, parser_probe` at :35). Phase 3 then extends it to also refuse `_leak_guard*probe*` residue at four sites. The plan does not say whether those four paths are hardcoded there or imported from `tests/test_leak_guard_scope.py`, and the latter creates a new cross-guard import the repo has nowhere else.",
        "proposed_fix":  "State it: hardcode the four repo-relative probe globs in the residue test with a comment citing tests/test_leak_guard_scope.py:73, :90, :120, :174 as their origin — a residue detector that imports the module whose residue it hunts would fail to collect if that module ever breaks.",
        "reviewer":  "executability"
    },
    {
        "id":  "EX-17",
        "title":  "After the fix the committed mode-B repro no longer distinguishes a working fixture from a no-op one",
        "severity":  "question",
        "confidence":  "medium",
        "category":  "regression-value",
        "location":  "tests/test_guard_probe_isolation.py:111-117",
        "problem":  "`test_the_real_scan_does_not_report_a_probe_a_sibling_test_has_planted` asserts `leaked == []` against the live-tree scan. Post-fix that assertion is satisfied by a `parser_probe` that does nothing at all, or that raises before writing — the same \u0027green while guarding nothing\u0027 shape the scope module\u0027s docstring (:9-14) was written to refuse. The plan celebrates the zero-edit green (correctly, as red-to-green evidence) without noting that the test\u0027s ongoing regression value drops to near zero.",
        "proposed_fix":  "Have the plan say so explicitly and name what carries the property afterwards: Phase 1\u0027s `test_no_probe_is_ever_written_into_the_live_package` (positive assertion during and after the with-block) and Phase 0\u0027s `test_the_mirror_reports_a_planted_offender_with_the_real_path_string` (the probe still plants something a real scan reports). Record it in the implementation report rather than leaving the next reader to discover the weakened test.",
        "reviewer":  "executability"
    }
]
```

## Meta-audit findings (did the merge converge the planners faithfully?)

```json
[
    {
        "id":  "MA-01",
        "title":  "Acceptance criterion counts \"eight pinned residuals\" — a number that matches nothing, and contradicts the merge\u0027s own \"six\"",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness-dedup",
        "location":  "Merged plan → testing §\"Nothing-else-regresses\" item 2 and Phase 1 acceptance (last bullet); measured against tests/test_fixed_offset_guard_scope.py:279-447 and docs/decisions/0020-sanctioned-lookahead-seam.md:95",
        "problem":  "The merge makes \"the six cry-wolf controls and eight pinned residuals ... must still pass and still be present in the same number\" a nothing-else-regresses acceptance criterion, repeated in Phase 1\u0027s acceptance list. I verified the numbers. \"Six\" is right: CRY_WOLF at tests/test_fixed_offset_guard_scope.py:229-270 holds exactly six tuples, driven by one parametrized test at :273-276. \"Eight\" is right under no reading at all: the module\u0027s own docstring at :28 says \"Five of these tests assert that something is not flagged which arguably should be\"; counting `_is_a_documented_hole` tests gives five (:285, :324, :338, :371, :391); ADR 0020:95 says \"The guard\u0027s docstring names **six** things it cannot see, and tests/test_fixed_offset_guard_scope.py pins every one\"; and the residuals section :279-447 contains eleven test functions. The merge itself cites the ADR\u0027s six in its own onboarding entry for ADR 0020, so the plan contradicts itself. The number came from planner 2 (\"eight pinned residuals (:285-447)\") and the merge carried it without reconciling it against the ADR citation it also carried.",
        "proposed_fix":  "Drop the invented count and make the criterion enumerable instead: \"every test currently defined under the `# --- Cry-wolf controls` header (:223) and the `# --- Known residuals` header (:279) is still present and its rule is unchanged — capture the test-id list from `uv run pytest tests/test_fixed_offset_guard_scope.py --collect-only -q` before Phase 0 and diff it at every checkpoint.\" If a number is wanted, pin the two the repo actually asserts: six CRY_WOLF entries, and ADR 0020:95\u0027s six named residuals — and note in the report that the module docstring\u0027s \"Five\" is stale relative to the ADR, as a separate observation, not something this change fixes.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-02",
        "title":  "Phase 2\u0027s `inspect.getsource` guard is broken by Phase 1\u0027s own re-documentation step",
        "severity":  "major",
        "confidence":  "high",
        "category":  "internal-contradiction",
        "location":  "Merged plan → Phase 2 step 3 (`test_the_probe_fixture_cannot_reach_the_live_package`) vs Phase 1 steps 2-3; target is tests/test_fixed_offset_guard_scope.py:60 and :81-98",
        "problem":  "Phase 2 prescribes: \"Assert via `inspect.getsource(parser_probe)` that its body contains no reference to `PARSER_DIR` and no `REPO_ROOT`-derived write target.\" Phase 1 step 3 prescribes: \"Re-document `PARSER_DIR` (:60). It survives with a changed role: the LIVE package the probe must never reach\", and Phase 1 step 2 prescribes replacing `parser_probe`\u0027s fidelity paragraph (:85-86) with prose about \"the package is one nothing else reads\". `inspect.getsource` returns the decorator, signature, docstring and body as one string — so a single mention of `PARSER_DIR` in the fixture\u0027s new docstring, which is exactly the mention Phase 1 encourages, turns the Phase 2 guard red for a documentation sentence. The implementer\u0027s cheapest resolution is to delete the explanatory docstring or to loosen the assertion, and both undo work the plan elsewhere insists on (\"do not delete the argument silently\", \"the code would be lying to the next reader\").",
        "proposed_fix":  "Assert on structure, not text. Parse the fixture with `ast.parse(inspect.getsource(parser_probe))`, drop the leading docstring node from the function body, and assert no `Name`/`Attribute` node in the remaining body resolves to `PARSER_DIR` or `REPO_ROOT`. Cheaper alternative that needs no AST: assert `\"PARSER_DIR\" not in parser_probe.__code__.co_names` and `\"REPO_ROOT\" not in parser_probe.__code__.co_names` (plus `co_freevars`), which sees only what the compiled body actually references and is blind to comments and docstrings by construction. State in the step which one was chosen and why the naive text scan was rejected.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-03",
        "title":  "Dropped without replacement: the anti-vacuity coverage that proves a default-root `parser_probe` call plants anything at all",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "completeness-dropped-signal",
        "location":  "Merged plan → Phase 1 (steps for `parser_probe`) and Phase 1 acceptance \"MODE A\"; dropped from planner code-grounded (ABORT_CHILD `os._exit(96)` branch, and the paired positive assertion on the mode-B test)",
        "problem":  "Planner code-grounded proposed two anti-vacuity additions the merge dropped: an `os._exit(96)` branch inside ABORT_CHILD so \"the fixture planted nothing\" is distinguishable from \"the child never ran\", and a paired assertion on the mode-B test that the same violation IS reported by a scan of the mirror while absent from the default-root scan. The merge dropped both deliberately, to keep tests/test_guard_probe_isolation.py byte-unedited — a trade it argues for well — but it never replaces the coverage. After the fix, `parser_probe(name, body)` with `tree_root=None` owns a private mirror the caller never sees and yields only a `str`, so nothing observes where it wrote. If `mirrored_package()` silently produced an empty tree, or the `write_text` were removed, the child would still exit 97 and `_planted_probes()` (tests/test_guard_probe_isolation.py:60-62) would still be empty: both repro tests green, and the new `test_no_probe_is_ever_written_into_the_live_package` green too. Phase 0\u0027s `test_the_mirror_reports_a_planted_offender_with_the_real_path_string` does not close this — it hand-writes the offender rather than driving the fixture. This is precisely the failure mode tests/test_fixed_offset_guard_scope.py:9-14 records twice.",
        "proposed_fix":  "Add one test in Phase 1 that drives the fixture in its default-root mode and observes the write: give `mirrored_package()` no new surface, but have `parser_probe` record the tree it owns on a module-level `LAST_PROBE_TREE: Path | None` (set on entry, left set on exit) and assert `guard.parser_module_violations(LAST_PROBE_TREE)` names the yielded `rel` while `guard.parser_module_violations()` does not. If a module-level global is unwelcome, achieve the same by asserting inside the with-block that exactly one path under `tempfile.gettempdir()` matching `ootp_guard_mirror_*/src/ootp_ai/parser/\u003cname\u003e` exists. Either way, add it to the mutation list: delete the `write_text` and watch it die.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-04",
        "title":  "\"Byte-faithful\" is the merge\u0027s whole fidelity argument, and no prescribed test checks bytes",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "completeness-dropped-signal",
        "location":  "Merged plan → architecture_map §\"The fidelity trade\", summary, and Phase 0 step `test_the_mirror_holds_the_same_modules_as_the_live_package`; dropped from planner domain-convention (`test_the_mirror_is_a_faithful_copy_of_the_live_package`, bytes match)",
        "problem":  "The merge sells the fidelity trade on the word byte-faithful — \"a byte-faithful `shutil.copytree` mirror\", \"37 byte-identical copies of the real modules\", \"\u0027the scan read a copy\u0027 degrades no further than \u0027the scan read a byte-identical copy\u0027\". Planner domain-convention proposed the assertion that earns the word: the mirror\u0027s repo-relative path set equals the live one\u0027s AND every file\u0027s bytes match. The merge kept only the path-set equality and explicitly framed it as \"set equality, not a count, so ordinary churn never trips it\" — which is right about counts and silent about contents. A `copytree` replaced by a loop that touches 37 empty files passes the merged assertion, and the mirror then proves the scan enumerates a directory of empty modules, which is the weaker `tmp_path` test that tests/test_fixed_offset_guard_scope.py:85-86 rejects. The merge\u0027s own risk MA-list names \"a mirror that is not a real package\" as a hazard and then mitigates it with the assertion that cannot see it.",
        "proposed_fix":  "Extend `test_the_mirror_holds_the_same_modules_as_the_live_package` to compare content, not just names: build `{p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()}` for both trees and assert the dicts are equal. 37 files / 551,657 bytes (measured on this tree), so the cost is milliseconds. Add the corresponding mutation to Phase 1\u0027s list: make `mirrored_package` write empty files instead of copying, and watch this test die — the merge\u0027s existing mutation 2 (copy only `__init__.py`) does not catch the empty-file case.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-05",
        "title":  "`--exclude-standard` reads more than `.gitignore`, and the merge removed the risk that says so",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "completeness-dropped-signal",
        "location":  "Merged plan → Phase 3 step 2 (`mirrored_repo`) and risks list; dropped from planner domain-convention\u0027s UNCONFIRMED item",
        "problem":  "Planner domain-convention flagged that `git ls-files --exclude-standard` consults `.git/info/exclude` and the user\u0027s global `core.excludesFile` in addition to `.gitignore`. The merge dropped that entirely and reduced the mirror recipe to \"copy `REPO_ROOT/.gitignore` **verbatim**\". The measurement itself is sound — I reproduced all seven `check-ignore` verdicts in a scratch `git init` mirror, and this repo\u0027s `.git/info/exclude` happens to contain only comments, which is why parity held — but the merge presents the result as a property of the recipe rather than a property of this machine. A cold implementer on a machine with a populated `.git/info/exclude`, or a `core.excludesFile` scoped to the repo, gets a mirror that diverges from the real repo, and the plan gives them no reason to look there. This is exactly the condition Phase 3\u0027s off-ramp exists for, and the merge deleted the signal that would trigger it.",
        "proposed_fix":  "Restore the risk bullet naming both extra sources. In Phase 3\u0027s parity control (`test_the_mirror_repo_ignores_what_this_repo_ignores`), add a precondition assertion that `REPO_ROOT/.git/info/exclude` contains no active (non-blank, non-comment) rule, with a message saying the mirror does not inherit it and that a populated one invalidates the seven verdicts; and copy it into the mirror if it is non-empty. Record `git config --get core.excludesFile` in the implementation report alongside the seven verdicts, so the measurement is reproducible rather than machine-shaped.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-06",
        "title":  "The non-ASCII enumeration property is dropped from the parity pins, while the test that depends on it is moved onto the mirror",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "completeness-dropped-signal",
        "location":  "Merged plan → Phase 3 step 1 (seven pinned verdicts) vs Phase 3 step 5 (ten planting tests moved, including :127-141); dropped from planner domain-convention\u0027s six-property list",
        "problem":  "Phase 3 moves `test_a_non_ascii_filename_survives_enumeration` (tests/test_leak_guard_scope.py:127-141, plants `café_leak_guard_probe.md`) onto the mirrored repo, but the seven verdicts Phase 3 pins as its parity control are all `git check-ignore` outcomes — none exercises enumeration of a non-ASCII path. Planner domain-convention listed it explicitly as one of six properties the temp repo must reproduce before any test moves. It is not an academic gap: that test exists because git C-quotes non-ASCII paths and the apparent suffix then carries a trailing quote, and the fix was `-z` plus an explicit UTF-8/surrogateescape decode (tests/test_no_leaks.py:44-67, whose docstring records the cp1252 measurement). Filesystem encoding and path normalisation on a Windows `%TEMP%` mirror are not guaranteed to match the repo\u0027s working tree, and my own scratch reproduction of the mirror could not exercise this property. If it diverges, the moved test fails for a harness reason and the cheapest wrong fix is to weaken it.",
        "proposed_fix":  "Add an eighth pinned verdict to `test_the_mirror_repo_ignores_what_this_repo_ignores` (or a sibling test): write `café_leak_guard_probe.md` into the mirror and assert `guard.git_paths(\"--cached\", \"--others\", \"--exclude-standard\", repo=mirror)` lists it with the accented character intact — i.e. the decoded string round-trips and its `Path(...).suffix` is `.md`. Run it as part of Phase 3\u0027s opening measurement step, before :127-141 is moved, and route a failure to the documented off-ramp rather than to an edit of the leak-guard test.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-07",
        "title":  "`git_paths` needs a keyword-ONLY parameter; \"keyword-defaulted\" invites a signature that swallows a git argument",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "correctness",
        "location":  "Merged plan → Phase 3 step 3 and files_to_touch entry for tests/test_no_leaks.py; target signature is tests/test_no_leaks.py:44 (`def git_paths(*args: str) -\u003e list[str]`)",
        "problem":  "`git_paths` is variadic (`*args: str`, tests/test_no_leaks.py:44), so a `repo` parameter can only be added after the star — it is necessarily keyword-only. The merge says \"Thread a keyword-defaulted `repo: Path = REPO_ROOT` through `git_paths` (:44, and `cwd=REPO_ROOT` at :62)\" in both Phase 3 and files_to_touch, and never writes the signature. A cold implementer reading \"keyword-defaulted\" as \"defaulted, pass by keyword\" can write `def git_paths(repo: Path = REPO_ROOT, *args: str)`, and every existing call — `git_paths(\"--cached\", \"--others\", \"--exclude-standard\")` at tests/test_no_leaks.py:100 and :192 and tests/test_leak_guard_scope.py:152 and :191 — then binds `\"--cached\"` to `repo` and runs git in a directory named `--cached`. Planner domain-convention wrote the correct signature out (`git_paths(*args: str, repo: Path = REPO_ROOT)`) and the merge lost it. mypy strict will catch the type mismatch here, but only because `repo` is annotated `Path`; the same slip on an untyped helper would not be caught.",
        "proposed_fix":  "Write the signatures literally in the Phase 3 step, for all five seams: `def git_paths(*args: str, repo: Path = REPO_ROOT) -\u003e list[str]`, `def scannable_text_files(repo: Path = REPO_ROOT) -\u003e list[Path]`, `def machine_path_violations(repo: Path = REPO_ROOT) -\u003e list[str]`, `def game_data_offenders(repo: Path = REPO_ROOT) -\u003e list[str]`, `def is_git_ignored(rel: str, repo: Path = REPO_ROOT) -\u003e bool`. Add a one-line note that `git_paths`\u0027s parameter is keyword-only because the function is variadic, and that every internal call site must pass it by keyword.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-08",
        "title":  "`test_the_production_enumeration_root_is_the_repo` is vacuous as specified — in a request about vacuous guards",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "correctness",
        "location":  "Merged plan → Phase 3 step 8; compare with the non-vacuous Phase 0 twin `test_the_production_scan_root_is_the_live_package`",
        "problem":  "Phase 3 prescribes: \"a no-argument `git_paths(\"--cached\", \"--others\", \"--exclude-standard\")` runs in REPO_ROOT and equals `git_paths(..., repo=REPO_ROOT)`.\" The second half is true by construction for any default value whatsoever — including a wrong one. If someone set `repo: Path = REPO_ROOT / \"var\"`, the assertion still passes. The Phase 0 twin does not have this problem, because it asserts against a literal (`guard.SCAN_ROOT == REPO_ROOT / \"src\" / \"ootp_ai\"`) and against membership of both `EXEMPT_MODULES` entries. Shipping a tautological compensating assertion in the one request whose subject is guards that pass while guarding nothing (tests/test_fixed_offset_guard_scope.py:9-14 records two) is the wrong artifact, and it is the kind of thing this repo\u0027s acceptance panels catch late.",
        "proposed_fix":  "Replace the equality half with two claims that can fail: `inspect.signature(guard.git_paths).parameters[\"repo\"].default == REPO_ROOT` (the default is the live repo, asserted against a literal), and that a no-argument `guard.scannable_text_files()` returns a non-empty list every element of which is under `REPO_ROOT` and `is_file()`. Keep the `inspect.getsource` pins on `test_no_machine_paths_or_identifiers` (:168-170) and `test_game_data_is_not_tracked` (:197-200) — those are the non-vacuous half and they are correctly specified. Add the mutation: point the default at the mirror and watch these die.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-09",
        "title":  "Phase 2 ships the RCA\u0027s explicitly GATED hardening tier (a) as an unconditional phase",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "scope-creep",
        "location":  "Merged plan → Phase 2 (`test_no_probe_residue_is_present_in_the_working_tree`) vs ROOT_CAUSE_ANALYSIS.md:157-161 and the merge\u0027s own gated_decisions entry 3",
        "problem":  "ROOT_CAUSE_ANALYSIS.md:157 puts the survivor sweep under \"**Hardening — gated, not assumed**\", and the merge\u0027s own gated_decisions entry 3 asks the operator to dispose hardening (a) and (b), recommending report-only. But Phase 2 is an unconditional entry in the `phases` array that builds and lands the report-only half of hardening (a) with no gate, no off-ramp and no \"dispose decision 3 first\" precondition. The merge is careful about this everywhere else — Phase 3 carries an explicit off-ramp, Phase 4 is labelled SEVERABLE in its name and commit note, and gated_decisions 4 and 5 are cross-referenced from the phases. Phase 2 alone is not. The recommendation is a good one and I would not argue against report-only on the merits; the defect is that a decided-artifact tier marked \"gated\" is executed before the gate, which is the pattern the RCA\u0027s own posture exists to prevent.",
        "proposed_fix":  "Rename Phase 2 to carry its gate the way Phase 4 does (\"Phase 2 — A survivor names itself (GATED on decision 3)\"), and add a first step: \"Do not start until gated decision 3 has been disposed. If the operator declines hardening (a) entirely, skip this phase, keep `test_the_probe_fixture_cannot_reach_the_live_package` — which is convention enforcement, not hardening — and record the decline in the implementation report.\" That also separates the two things Phase 2 currently bundles: the residue detector (gated hardening) and the structural fixture assertion (part of the fix\u0027s own convention).",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-10",
        "title":  "ADR 0022 is a mandatory Phase 5 step while gated_decisions calls it the softest gate — and the two disagree about whether Phase 4 stays severable",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "scope-creep",
        "location":  "Merged plan → Phase 5 step 2 vs gated_decisions entry 5, and Phase 4\u0027s commit_note (\"Fully severable\")",
        "problem":  "Phase 5 step 2 reads as an instruction: \"Write ADR 0022 at docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md.\" gated_decisions entry 5 reads as a question with the answer \"this is the softest of the five gates and a lighter answer is defensible\". A cold implementer executes the phases, not the gates, so the ADR gets written regardless of disposition. It is not free: tests/test_repo_structure.py:33-40 requires it be indexed in docs/decisions/README.md, :43-57 requires the word \"cost\" plus a `## Consequences` or `**Costs:**` section, :60-67 requires sequential numbering (I verified 0001–0021 exist, so 0022 is correct), and it spends a decision number on a testing convention in a repo where ADRs are described as \"twenty-one calls\". Worse, gated_decisions 5 states that declining the ADR makes Phase 4\u0027s contract guard \"load-bearing rather than severable\" — which directly contradicts Phase 4\u0027s own commit note, \"Fully severable — the bug is already fixed without it\". The plan therefore has two mutually exclusive severability stories depending on a gate it does not sequence.",
        "proposed_fix":  "Make Phase 5 step 2 conditional in its own text: \"If gated decision 5 was disposed FOR, write ADR 0022 …; if disposed AGAINST, record the convention in `tests/fixtures/guard_trees.py`\u0027s module docstring and the appended memory entry only, and say so in the report.\" Then reconcile the severability claim explicitly in one place: state that decisions 4 and 5 cannot both be declined without leaving the convention prose-only, and that if both are declined the report must say the convention is unenforced. Sequence both gates before Phase 0, as gated_decisions entry 1 already does for the leak-guard tier.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-11",
        "title":  "Three prescribed tests assert the same property — the live package holds no probe",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "dedup",
        "location":  "Merged plan → Phase 1 step 10 (`test_no_probe_is_ever_written_into_the_live_package`), Phase 2 step 1 (`test_no_probe_residue_is_present_in_the_working_tree`), and the pre-existing repro at tests/test_guard_probe_isolation.py:100-117",
        "problem":  "After the fix, three tests assert that `src/ootp_ai/parser/` holds no `_guard_scope*_probe.py`. Phase 1\u0027s new test drives `parser_probe` and checks the live dir during and after; Phase 2\u0027s residue detector checks the live dir via the same `_planted_probes()` helper (tests/test_guard_probe_isolation.py:60-62); and the committed repro\u0027s mode-B test already asserts the live scan reports nothing while a probe is planted. Any survivor from an older revision reddens all three at once, with three different messages, and any regression in the fix reddens at least two. The merge presents them as covering different properties (\"mode B as a positive property\", \"the only retroactive coverage\") without noticing that the observable they read is identical. Not harmful, but it inflates the diff in a change whose acceptance criterion is \"before/after pass counts must match except for tests deliberately added\", and it makes the added-test count harder to reconcile.",
        "proposed_fix":  "Keep the Phase 2 residue detector — it is the only coverage of pre-fix survivors and it carries the message a reader needs. Fold Phase 1\u0027s `test_no_probe_is_ever_written_into_the_live_package` into it as a second assertion inside the same test (check `_planted_probes()` at module scope AND while driving `parser_probe`), or, if both are kept, add one sentence to each docstring naming the other and saying why they are not the same test — the way tests/test_no_leaks.py:139-146 justifies `machine_path_violations` existing beside the membership assertions.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-12",
        "title":  "Convergence map overclaims unanimity: one planner did propose a removing sweep",
        "severity":  "nit",
        "confidence":  "medium",
        "category":  "convergence-accuracy",
        "location":  "Merged plan → convergence_map theme \"The residue check REPORTS, never sweeps\" (\"All three refused an autouse deleting sweep\"); compare planner domain-convention\u0027s Phase 5 (OPTIONAL) and planner sequencing\u0027s Phase 5(a)",
        "problem":  "The convergence map states \"All three refused an autouse deleting sweep, each grounding it differently.\" That is not what the proposals say. Planner domain-convention proposed a `tests/conftest.py` `pytest_sessionstart` hook that \"REPORTS ... and removes\" surviving probes, as an explicit optional Phase 5, and recommended skipping it rather than refusing it. Planner sequencing recommended against the removing form but framed it as a disposition to be presented to the user, not a refusal. Only planner code-grounded refused outright. The convergence map\u0027s entire purpose is to grade how much independent agreement stands behind a recommendation, so reporting a two-plus-one-conditional as three-of-three inflates the confidence a reader assigns to the merge\u0027s strongest refusals — and this one is doing real work (it is the basis for dropping the conftest option entirely).",
        "proposed_fix":  "Restate the theme honestly: \"two refused outright; one offered it as an optional, recommended-against phase.\" Then name the deciding ground rather than the vote — this repo has no `conftest.py` anywhere (verified), and tests/fixtures/warehouse.py:1-6 states the reason (\"a reader ... can see the landing being set up by name instead of inheriting it\"), so a deleting autouse hook would be the repo\u0027s first conftest and a structural first well beyond this bug. That argument stands on its own without needing unanimity.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-13",
        "title":  "copytree cost gets a measurement step with no threshold and no fallback, while `git init` gets both",
        "severity":  "nit",
        "confidence":  "medium",
        "category":  "cost-realism",
        "location":  "Merged plan → Phase 0 final step (\"MEASURE and record: wall time of one `copytree`\") vs Phase 3 final acceptance bullet (\"if the module\u0027s runtime grew by more than ~5s, adopt a session-scoped mirror\")",
        "problem":  "Phase 3 gives the `git init` cost a threshold and a named fallback. Phase 0 gives the copytree cost only \"MEASURE and record\", with no threshold and no prescribed action if the number is bad. Both other planners supplied the missing half: planner code-grounded prescribed a module-scoped `tmp_path_factory` mirror outright with a stated per-copy cost, and planner domain-convention wrote \"If the copy is material ... switch `mirrored_package` to a module-scoped copy with per-test probe names and say so.\" As specified, `parser_probe` builds a private mirror per default-root call and each explicit call site opens its own, so tests/test_fixed_offset_guard_scope.py performs roughly eight copytrees of 37 files / 551,657 bytes (I verified both figures). That is almost certainly fine on this machine; the point is that a cold implementer told to measure without a threshold has no basis for deciding anything, and the merge already knows the right shape because it used it one phase later.",
        "proposed_fix":  "Give Phase 0 the Phase 3 shape: \"If `uv run pytest tests/test_fixed_offset_guard_scope.py` grows by more than ~2s, switch `mirrored_package` to a module-scoped mirror built once per module with per-test probe names — the clobber assert at tests/test_fixed_offset_guard_scope.py:93 still catches a name collision inside a shared mirror — and record the reason in the implementation report.\" Note that the default-root path in `parser_probe` must keep building a private mirror regardless, because ABORT_CHILD runs outside pytest and cannot see a module-scoped fixture.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-14",
        "title":  "Phase 4\u0027s cry-wolf control is mislabelled as a READ; the line cited is a path construction",
        "severity":  "nit",
        "confidence":  "medium",
        "category":  "citation-accuracy",
        "location":  "Merged plan → Phase 4 step 4 (\"a `REPO_ROOT`-derived READ (tests/test_no_leaks.py:103)\")",
        "problem":  "tests/test_no_leaks.py:103 is `p = REPO_ROOT / rel` — a path binding inside `scannable_text_files`, not a read. The actual read is at :158 (`text = path.read_text(encoding=\"utf-8\")`), where the receiver `path` is a loop variable and is not syntactically REPO_ROOT-derived at that line. The control is the right one to have — the rule must not fire on a REPO_ROOT-derived expression that is never written — but the label misdescribes what it is testing, and an implementer building the AST rule from the label may write it as \"exclude read calls\" rather than \"only fire on write calls\", which is a materially different and much leakier rule. Planner sequencing cited tests/test_repo_structure.py:36 and tests/test_no_leaks.py:158 for this control; the merge substituted :103 and kept the old label.",
        "proposed_fix":  "Split the control and label each correctly: (a) \"a REPO_ROOT-derived path bound but never written — tests/test_no_leaks.py:103\", and (b) \"a REPO_ROOT-derived read — tests/test_repo_structure.py:36 (`(adr_dir / \"README.md\").read_text(...)` reached from REPO_ROOT at :35)\". Restate the rule positively in the step: the guard fires only on a call in `CREATIVE_CALLS`/`.unlink(`/`os.makedirs` whose receiver resolves to a REPO_ROOT-derived name; everything else, read or otherwise, is out of scope by construction rather than by exclusion.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-15",
        "title":  "Dropped citation: the in-repo precedent for treating an edited assertion message as a laundered weakening",
        "severity":  "nit",
        "confidence":  "high",
        "category":  "completeness-dropped-signal",
        "location":  "Merged plan → Phase 3 acceptance bullet 1 (\"an edited message inside a mechanical rename is how a weakening gets laundered\"); dropped from planner code-grounded\u0027s citation of requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/reviews/implementation-review.md:178",
        "problem":  "Planner code-grounded grounded this acceptance criterion in a real prior review — `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/reviews/implementation-review.md:178`, which I confirmed exists. The merge kept the sentence and dropped the citation, so the strongest in-repo precedent for the criterion now reads as the plan\u0027s own opinion. In a repo whose stated convention is \"ground every claim\" and whose plan elsewhere cites forty-odd file:line pointers, an uncited assertion in an acceptance list is the one a reviewer discounts. It matters because this criterion is doing real work: ten leak-guard tests and four fixed-offset tests move mechanically in Phase 3, and that diff is exactly where a weakened message hides.",
        "proposed_fix":  "Restore the citation to Phase 3\u0027s acceptance bullet and to the corresponding risk (\"A RENAME OR SIGNATURE CHANGE CAN LAUNDER A WEAKENED ASSERTION\"), verifying the line number against the file when the plan is written. Also add the mechanical check the citation implies: `git diff -U0 tests/test_leak_guard_scope.py tests/test_no_leaks.py | Select-String \u0027^[-+].*assert\u0027` should show only added lines and moved-not-modified assertion text.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-16",
        "title":  "The CLAUDE.md project-map disposition was dropped from Phase 5\u0027s /update-docs list",
        "severity":  "nit",
        "confidence":  "medium",
        "category":  "completeness-dropped-signal",
        "location":  "Merged plan → Phase 5 step 7; dropped from planner code-grounded (\"CLAUDE.md\u0027s project map line `tests/  Structural guards + parser fixtures` still holds\") and planner domain-convention (\"let /update-docs judge whether CLAUDE.md\u0027s map needs tests/fixtures/guard_trees.py mentioned\")",
        "problem":  "Two planners pre-disposed the same /update-docs question: does CLAUDE.md\u0027s project map need to change now that `tests/fixtures/guard_trees.py` (and possibly `tests/test_probe_isolation_contract.py`) exist? The merge kept only the ADR-0020-not-invalidated judgement and the prohibition on restating the rulebook inside CLAUDE.md, and dropped the map question entirely. That leaves the one doc-surface question this change actually raises unanswered, while carefully answering the one it does not. It is a small gap but it is the kind /update-docs will raise at the last checkpoint, after the four gates have already been run.",
        "proposed_fix":  "Add the map line to Phase 5\u0027s disposition list beside the ADR 0020 judgement: \"CLAUDE.md\u0027s map entry `tests/  Structural guards + parser fixtures` — decide whether it still describes a directory that now also holds a tree-mirroring harness, and record the judgement rather than assuming it. Do NOT add the new rule to the build-rulebook section.\" Note that tests/fixtures/README.md is already being amended in the same phase, which is the cheaper place for the detail if the map stays as it is.",
        "reviewer":  "meta-audit"
    },
    {
        "id":  "MA-17",
        "title":  "Phase 4\u0027s zero-allowlist premise is verified but conditional on Phase 3 landing, and the plan does not say what happens if Phase 3 takes its off-ramp",
        "severity":  "question",
        "confidence":  "medium",
        "category":  "scope-creep",
        "location":  "Merged plan → Phase 4 step 6 and gated_decisions entry 4, read against Phase 3\u0027s off-ramp (final step)",
        "problem":  "Phase 4\u0027s headline justification is that its AST contract guard \"lands with ZERO allowlist entries\" — \"the objective proof that Phases 1 and 3 removed every site\". I verified the premise: grepping `tests/**` for write calls, the only REPO_ROOT-derived writes are tests/test_fixed_offset_guard_scope.py:94, tests/test_leak_guard_scope.py:49, and the two `(REPO_ROOT / \"var\" / \"tmp\").mkdir(...)` calls at tests/test_leak_guard_scope.py:89 and :183; every other write in the directory targets `tmp_path` or a fixture-built root. But three of those four are removed by Phase 3, and Phase 3 carries an explicit off-ramp (\"STOP after Phase 2, file the leak-guard site as its own BUGFIX_REQUEST\"). If that off-ramp is taken, Phase 4 must either land with three allowlist entries — which the plan calls a signal that \"an earlier phase left something behind\" — or not land at all. The plan sequences Phase 4 after Phase 3 but never states the dependency. Separately, Phase 4 is the one deliverable the RCA does not name at all (its Root tier asks for \"one shared convention\", not a new AST guard module), so the question of whether it belongs in this change is live; the merge does surface that in gated_decisions entry 4, which is why this is a question rather than a scope-creep finding.",
        "proposed_fix":  "Add a first step to Phase 4: \"Void if Phase 3 took its off-ramp. A contract guard whose allowlist names the very site that was severed is a guard satisfied by adding entries — the shape docs/decisions/0020-sanctioned-lookahead-seam.md:92-93 forecloses. If Phase 3 was severed, skip Phase 4, record that the convention is prose-plus-helper-docstring only, and attach the guard to the follow-up request instead.\" Also require gated decision 4 to be disposed before Phase 0, as decision 1 already is, since it changes the branch\u0027s size and the PR\u0027s blast radius.",
        "reviewer":  "meta-audit"
    }
]
```

## Reviewer summaries

```json
[
    {
        "reviewer":  "code-grounded",
        "kind":  "adversary",
        "summary":  "Code-grounded adversarial verification of the merged IMPLEMENTATION_PLAN draft for `guard-probe-survives-an-interrupted-run`. I read the upstream RCA and BUGFIX_REQUEST in full, then resolved every cited file:line in the draft against the working tree.\n\n**The citation quality is unusually high.** I checked roughly 90 distinct references and confirmed: `tests/test_fixed_offset_guard_scope.py` (:9-14, :18, :60, :65-68, :81-98, :85-86, :104-116, :119-127, :130-134, :137-150, :156-167, :176-184, :187-197, :421-434); `tests/test_no_fixed_offsets.py` (:96-97, :104-107, :339-342, :345-354, :357-363, :361, :569-575); `tests/test_guard_probe_isolation.py` (:20-23, :35, :46-57, :51, :60-62, :83-87, :89-94, :100-117); `tests/test_leak_guard_scope.py` (:20, :37, :40-53, :49, :73, :89, :119-120, :165-178, :183, :196-200, :224-238, :250-252, and all ten planting-test ranges); `tests/test_no_leaks.py` (:21, :31, :44-67, :62, :70-106, :139-165, :173-194, :180-186, :216-232); `tests/test_grain_contracts.py` (:75, :364-380); `tests/test_read_only.py` (:292, :337, :344-345, :389-402, :398); `tests/test_repo_structure.py` (:33-40, :43-57, :60-67); `tests/test_agent_contract.py` (:76-81, :84-95); `tests/test_doc_links.py` (:55, :137-156, :149); `tests/fixtures/__init__.py`, `warehouse.py:1-6`, `README.md:30-36`; `pyproject.toml` (:78-79, :81-88, :91-95, :98-108); `.github/workflows/ci.yml` (:46, :49, :52, :57, :70-78); `docs/decisions/0020-*.md` (:92-93, :95-102); `.claude/agents/data-engineer.md` (:154-172); `.claude/agents/data-engineer-memory.md` (:340-350, :351-356); `requests/bugfix-requests/README.md` (:24-26, :41-45, :54); `requests/feature-requests/README.md:20`; both acceptance-panel citations. **Every one resolved to what the plan claims.** No fictional function, no fictional reuse. `parser_modules`, `parser_module_violations`, `scan_source`, `parser_probe`, `untracked_file`, `git_paths`, `scannable_text_files`, `machine_path_violations`, `game_data_offenders`, `is_git_ignored`, `_planted_probes`, `source_modules`, `_source_files`, `CREATIVE_CALLS`, `EXEMPT_MODULES`, `EXEMPT_PREFIXES`, `strip_fences`, `bare_request_tokens` all exist with the signatures claimed.\n\n**I also independently re-ran the plan\u0027s two load-bearing measurements.** `parser_modules()` → 37 modules, `parser_module_violations()` → 0 (confirmed). `src/ootp_ai/**/*.py` → 37 files / 551,657 bytes (confirmed exactly). And I rebuilt the Phase-3 git mirror in a scratchpad tempdir: a `git init` repo carrying a verbatim `.gitignore` copy returned **identical** `git check-ignore --no-index` verdicts to the real repo on all seven probed paths, and `git ls-files --cached --others --exclude-standard` correctly listed untracked probes and excluded the ignored one with no commits and no configured identity. **The plan\u0027s riskiest empirical claim holds.**\n\nWhat survives verification is 13 findings, none of which invalidate the design. Two are execution blockers a cold implementer hits within minutes (a gamedata-marked module inside three per-phase pytest selectors; a REPO_ROOT-derived write the Phase-4 guard would flag in a file the plan explicitly leaves unedited). The rest are stale counts, an over-tight source-text assertion, and a gate stated as an absolute that can never hold mid-phase."
    },
    {
        "reviewer":  "executability",
        "kind":  "adversary",
        "summary":  "I verified the plan\u0027s citations against the repo and most hold: `PARSER_DIR` at tests/test_fixed_offset_guard_scope.py:60, `parser_probe` :81-98, `SCAN_ROOT`/`EXEMPT_MODULES`/`scan_source`/`parser_modules`/`parser_module_violations` at tests/test_no_fixed_offsets.py:97/104-107/339-342/345-354/357-363, `ABORT_CHILD` at tests/test_guard_probe_isolation.py:46-57, the ten planting tests and the zero-arg monkeypatch at tests/test_leak_guard_scope.py:250-252, the deny set at .claude/agents/data-engineer.md:154-172, CI\u0027s four gates at .github/workflows/ci.yml:45-57, ADRs 0001-0021 (so 0022 is right), no conftest.py anywhere, `from fixtures.X import` as the house import form, and — measured myself — 37 `.py` files / 551,657 bytes under `src/ootp_ai`. The architecture (repo-root seam, copytree mirror, two-positional `parser_probe` so the committed repro needs no edit) is sound and the phase DAG is genuinely ordered. What a cold agent would hit are executability defects inside the phases, not in the design: Phase 3\u0027s steps are internally out of order (its first step needs a seam and a helper that steps 2 and 3 create); Phase 4\u0027s headline acceptance (\"ZERO allowlist entries\") is falsified by a `REPO_ROOT`-derived `.unlink(` at tests/test_guard_probe_isolation.py:95-97 that Phase 2 explicitly preserves; two acceptance criteria are `grep` invocations on a PowerShell-only machine; the plan document itself will redden `tests/test_doc_links.py` at Phase 0 by naming a not-yet-existing `requests/...` path unfenced; and Phase 2\u0027s source-text assertion contradicts the docstring and `f\"src/ootp_ai/parser/{name}\"` yield that Phase 1 prescribes. Several acceptance criteria (mypy file count, \"eight pinned residuals\", the mode-B concurrency run) are not checkable as written."
    },
    {
        "reviewer":  "meta-audit",
        "kind":  "meta_audit",
        "summary":  "Meta-audit of the merge, not the repo. I re-ran the merge\u0027s own load-bearing measurements before judging it, and the merge\u0027s grounding is unusually good: `parser_modules()` → 37 / `parser_module_violations()` → 0 reproduce exactly; `src/ootp_ai` is 37 files / 551,657 bytes exactly as claimed; all seven `git check-ignore --no-index` verdicts reproduce on the real repo AND in a scratch `git init` mirror carrying a verbatim `.gitignore` (with no commits and no configured identity, `git ls-files -z --cached --others --exclude-standard` listed the untracked probes and excluded the ignored one) — so the merge\u0027s single riskiest asserted-as-measured claim is real, not laundered; `CRY_WOLF` has exactly six entries (tests/test_fixed_offset_guard_scope.py:229-270); the complete set of REPO_ROOT-derived writes under `tests/` really is the four lines the merge names (test_fixed_offset_guard_scope.py:94, test_leak_guard_scope.py:49, :89, :183), so Phase 4\u0027s zero-allowlist premise holds; there is no `conftest.py` anywhere; ADRs 0001–0021 exist so 0022 is right; `datasets/` does not exist. The merge\u0027s central design claim also survives tracing: with `parser_probe(name, body, tree_root=None)` building a private mirror, both tests in tests/test_guard_probe_isolation.py go green with that file unedited — that is a genuine improvement the merge picked from one planner over two others, and it is correctly argued rather than asserted. SCOPE-CREEP: nothing beyond the RCA\u0027s core is smuggled silently — Phase 4 (a new AST guard) and ADR 0022 are both beyond the decided tiers but both are surfaced in gated_decisions; the real defect is that the `phases` array executes them unconditionally while the gates say \"dispose first\", and Phase 2 ships the report-only half of the RCA\u0027s explicitly *gated* hardening tier (a) with no gate at all. COMPLETENESS: three substantive planner items were dropped without replacement — planner 1\u0027s anti-vacuity coverage for the abort child, planner 3\u0027s byte-equality assertion behind the word \"byte-faithful\", and planner 3\u0027s `.git/info/exclude`/global-excludes risk plus the non-ASCII enumeration property. COST-UNREALISM: no false \"reuse what\u0027s there\" claims found; the only cost gap is that copytree gets a measurement step with no threshold or fallback while `git init` gets both. Two internal contradictions would bite a cold implementer directly: an acceptance criterion counting \"eight pinned residuals\" (matches nothing — five by the module docstring, six by ADR 0020, eleven by test count, and the merge itself says six elsewhere), and a Phase 2 `inspect.getsource` assertion that Phase 1\u0027s own re-documentation step would break. 17 findings, no blockers."
    }
]
```

## Convergence map (where two or more planners agreed)

```json
[
    {
        "theme":  "The seam must be a REPO root, not a scan root — the RCA\u0027s literal fix sketch does not compile",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three independently traced `scan_source` (tests/test_no_fixed_offsets.py:339-342) → `EXEMPT_MODULES` (:104-107, repo-relative posix strings) → `path.relative_to(REPO_ROOT)` (:361), and all three concluded the RCA\u0027s `parser_modules(root=SCAN_ROOT)` sketch (ROOT_CAUSE_ANALYSIS.md:139-141) would either raise ValueError or silently un-exempt the sanctioned seam. Three independent derivations of the same non-obvious correction to a decided artifact\u0027s sketch is the strongest signal in this panel — and it is a correction to a SKETCH, not a re-litigation of the verdict."
    },
    {
        "theme":  "A byte-faithful copytree mirror plus explicit compensating assertions, never a bare tmp_path",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three adopted the RCA\u0027s middle path (:147-149) and all three independently arrived at the same compensations: production scan root is the live package; the mirror\u0027s module set equals the live one\u0027s; the floor tests keep observing production. Two of the three also independently proposed pinning the tree-is-clean test\u0027s default-root call. The unanimity means the fidelity argument at tests/test_fixed_offset_guard_scope.py:85-86 is answered rather than dodged, and the mirror cannot decay into the weaker thing without a test dying."
    },
    {
        "theme":  "ABORT_CHILD is the sharpest trap in the change — a source string invisible to ruff and mypy",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three flagged tests/test_guard_probe_isolation.py:46-57 as the likeliest way this fix becomes a different failure, and all three quoted the test\u0027s own warning at :83-87. They diverged on the remedy — two said edit the string in lockstep, one said keep the signature so it never needs editing — and the third answer strictly dominates: it makes the committed repro go green with ZERO edits, which is the strongest red→green evidence the bugfix track can produce. Convergence on the hazard plus one clearly better resolution."
    },
    {
        "theme":  "The floor tests must keep running against the real tree, or the fix buys a vacuous guard",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three named `test_the_module_set_has_a_floor` (:137-150) and its leak-side twin `test_the_candidate_set_has_a_floor` (tests/test_leak_guard_scope.py:224-238) as lines that must NOT move onto a mirror, and all three cited the same in-repo history (tests/test_fixed_offset_guard_scope.py:9-14: a leak-guard no-op mutant left all 18 tests green). Two independently proposed adding a comment at each because it is exactly the line a future refactor would tidy. This is the plan\u0027s main defence against trading a fixture flake for a weaker guard."
    },
    {
        "theme":  "Refuse the name-aware guard message, on ADR 0020\u0027s foreclosure",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three declined the RCA\u0027s hardening (b) and reached it from different directions: one cited ADR 0020:92-93\u0027s \u0027no per-site exemption registry, ever\u0027 verbatim; one argued it becomes unreachable dead code inside the project\u0027s most load-bearing structural ban after the fix; one noted `EXEMPT_MODULES`\u0027s own comment treats any widening as a decision to be made against a failing test. Independent convergence on refusing the one option the RCA flagged as trading against ADR 0020 is what makes this a settled recommendation rather than a preference."
    },
    {
        "theme":  "The leak-guard site is the same class with a worse survivor, and its git-mirror parity was the one unconfirmed claim",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three identified tests/test_leak_guard_scope.py:40-53 as structurally identical and its survivor as worse (a banned machine-path string at the repo root poisoning the only ADR-0006 protection). Two of the three independently isolated the same load-bearing subtlety — `git_paths` shells git with `cwd=REPO_ROOT`, so un-sharing needs a git repo, and several tests depend on the real `.gitignore`\u0027s last-match-wins negations (tests/test_no_leaks.py:180-186). Two independently labelled the temp-repo parity `unconfirmed` and gated the phase on measuring it. That gate is now discharged: measured 2026-08-21, seven identical verdicts, and `ls-files` works with no commits and no git identity."
    },
    {
        "theme":  "The monkeypatch at tests/test_leak_guard_scope.py:250-252 breaks on arity",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three found the zero-argument lambda replacing `guard.scannable_text_files` and predicted the same failure: a TypeError that is red for an unrelated reason, whose cheapest wrong fix is deleting the test — which would restore the FileNotFoundError crash its own docstring records. A defect three independent readers found by reading is one a cold implementer will otherwise find as a mystery red, so it is written as an explicit numbered step rather than a risk."
    },
    {
        "theme":  "The residue check REPORTS, never sweeps",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three refused an autouse deleting sweep, each grounding it differently: ROOT_CAUSE_ANALYSIS.md:157-161 says a sweep cannot fix either mode; a silent tidy destroys the evidence the next reader needs; and this repo has no conftest.py anywhere, with tests/fixtures/warehouse.py:1-6 stating why. One also noted that gitignoring the probe name would remove `git status --porcelain --untracked-files=all` as a detection signal — the exact signal BUGFIX_REQUEST.md:45 used. Three refusals, three reasons, one recommendation."
    },
    {
        "theme":  "This work cannot be delegated to the write-capable subagent",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three located `tests/` as the first entry in the deny set (.claude/agents/data-engineer.md:154-165), the stop-and-report instruction at :171-172, and the test that enforces it (tests/test_agent_contract.py:76-81). Every file this change touches is under tests/, docs/decisions/ or .claude/ — all denied. Three independent hits on a delegation constraint that a cold implementer would otherwise violate by reflex."
    },
    {
        "theme":  "More readers share the tree than the RCA enumerates, which is the argument for un-sharing rather than teaching one reader",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "Two planners independently found tests/test_grain_contracts.py:75 + :364-367 as a second rglob over the identical root; one also found tests/test_read_only.py:292 + :344-345 as a third. None plants anything, so none is part of the cause — but together they are the structural case that a per-reader fix would have to be repeated three times, while un-sharing the tree fixes all of them at once. All three planners also agreed those files stay untouched."
    },
    {
        "theme":  "The shared helper\u0027s home is tests/fixtures/, and it is not a free choice",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three landed on tests/fixtures/ and all three cited pyproject.toml:88\u0027s `known-first-party = [\"ootp_ai\", \"fixtures\"]` with its recorded warm-local-vs-cold-CI import-order failure. Two independently added that it must be a plain function or contextmanager rather than a pytest fixture, because the abort child imports it in a bare process; two independently noted this repo has no conftest.py and cited tests/fixtures/warehouse.py\u0027s stated reason. Convergence on a siting decision that looks arbitrary but is constrained from three directions."
    },
    {
        "theme":  "Mutation testing is mandatory here, not a nicety",
        "planners":  [
                         "code-grounded",
                         "sequencing",
                         "domain-convention"
                     ],
        "why_high_signal":  "All three prescribed explicit apply-observe-revert mutations with recorded outcomes, and all three grounded it in the same in-repo history: two guards that were green while guarding nothing (tests/test_fixed_offset_guard_scope.py:9-14) and the standing practice recorded at .claude/agents/data-engineer-memory.md:351-356. The union of their proposed mutations is six, each killing a different assertion, and each is written into an acceptance list rather than into prose."
    }
]
```

## Gated decisions as the panel posed them

```json
[
    {
        "question":  "Does the leak-guard site (tests/test_leak_guard_scope.py + tests/test_no_leaks.py) land in THIS change as Phase 3, or become its own bugfix request? It changes the branch\u0027s size and the PR\u0027s blast radius, so dispose it before Phase 0 starts.",
        "recommendation":  "**Land it here, as Phase 3.** ROOT_CAUSE_ANALYSIS.md:152-156 names two independent fixes as the outcome to avoid, and this site\u0027s survivor is strictly worse: a deliberately banned machine-path string (tests/test_leak_guard_scope.py:37) dropped at the repo root, poisoning the repo\u0027s only ADR-0006 protection, and racing test_doc_links (CF-14, carried forward unfixed since phase-7-acceptance-panel.md:63). The blocker was an unconfirmed claim about git-mirror fidelity; I measured it on this tree 2026-08-21 and it holds on all seven probed paths, including the two the last-match-wins negations make load-bearing, with `git ls-files --cached --others --exclude-standard` working in a repo with no commits and no configured identity. Phase 3 re-pins those seven as an executable control, and carries an explicit off-ramp: if they do not reproduce, or `git init` proves unstable in CI, STOP after Phase 2 and file the site LOUDLY — a new BUGFIX_REQUEST with its own Index row, never a sentence in a report.",
        "related":  [
                        "tests/test_leak_guard_scope.py:40-53",
                        "tests/test_no_leaks.py:44-67",
                        "tests/test_no_leaks.py:180-186",
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md:122-131",
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md:152-156"
                    ]
    },
    {
        "question":  "Is the copy-the-package variant accepted as sufficient fidelity, or does the operator want a live plant retained in some form? The RCA names this as the one design call it does not settle, and tests/test_fixed_offset_guard_scope.py:85-86 is a real argument.",
        "recommendation":  "**Accept the copy, with the three compensating assertions treated as non-negotiable.** The docstring\u0027s claim is true of an EMPTY tmp_path and false of a faithful copy: the scan still rglobs a real tree and opens 37 real modules, and the probe still sits among real neighbours. What the copy loses is the assertion that PRODUCTION points at the live package — and the compensations assert strictly MORE than the live plant ever did, because the live plant never checked where the default root pointed. If the operator wants a live plant retained anyway, the only honest form is a `gamedata`-marked or manually-run test, and that trades the bug back for the fidelity; I do not recommend it. What I would refuse outright is landing the copy WITHOUT the compensations — that is the trade the intake\u0027s stage plan said needed a panel (BUGFIX_REQUEST.md:168-173).",
        "related":  [
                        "tests/test_fixed_offset_guard_scope.py:85-86",
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md:144-151",
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md:168-173"
                    ]
    },
    {
        "question":  "Hardening (a): report-only, or actually sweep survivors? And hardening (b): should the guard learn probe names and emit a friendlier message? The RCA hands both to this stage (:166-170) rather than deciding them.",
        "recommendation":  "**(a) Report-only — DECLINE the sweep. (b) DECLINE outright.** For (a): ROOT_CAUSE_ANALYSIS.md:157-161 says a sweep cannot fix either mode and must not be sold as the fix; a deleting autouse hook would also need this repo\u0027s first conftest.py (there is none anywhere, and tests/fixtures/warehouse.py:1-6 states why this repo avoids one), and silent tidying destroys the evidence the next reader needs. `test_no_probe_residue_is_present_in_the_working_tree` delivers the one real value — coverage of survivors from pre-fix revisions — without mutating anything. Also do NOT gitignore `_guard_scope*_probe.py`: that removes `git status --porcelain --untracked-files=all` as a detection signal, which is exactly the signal that identified the phantom (BUGFIX_REQUEST.md:45). For (b): docs/decisions/0020-sanctioned-lookahead-seam.md:92-93 forecloses a per-site exemption registry, and a filename-keyed special case inside the guard is one; after Phase 1 the branch is unreachable dead code inside the enforcement of the project\u0027s most load-bearing structural ban. If the operator wants it anyway, it is an ADR-level decision that reopens 0020 — not a phase step.",
        "related":  [
                        "docs/decisions/0020-sanctioned-lookahead-seam.md:92-93",
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md:157-164",
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md:45",
                        "tests/fixtures/warehouse.py:1-6"
                    ]
    },
    {
        "question":  "Is Phase 4\u0027s AST contract guard (`tests/test_probe_isolation_contract.py`) in scope, or is it creep? It is the only deliverable the RCA does not name outright.",
        "recommendation":  "**Include it, and keep it severable.** It is the executable form of the RCA\u0027s Root tier (:152-156) — prose cannot stop a third site being invented, and there are already three other readers of the same tree that a per-reader fix would leave unprotected. Crucially it lands with ZERO allowlist entries, and that is measured rather than hoped: today the complete set of REPO_ROOT-derived writes under tests/ is tests/test_fixed_offset_guard_scope.py:94, tests/test_leak_guard_scope.py:49 and the two mkdirs at tests/test_leak_guard_scope.py:89,183 — all four removed by Phases 1 and 3; every other write in tests/ targets tmp_path or a fixture-built root. It must be AST-based, not a grep (tests/test_read_only.py:337 and :398 hold the banned strings as literals). If the operator drops it, the filed bug is still closed by Phase 1 — but say in the report that the convention is then prose-only, so the next reader knows.",
        "related":  [
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md:152-156",
                        "tests/test_read_only.py:337",
                        "tests/test_read_only.py:389-402",
                        "tests/test_leak_guard_scope.py:89",
                        "tests/test_grain_contracts.py:364-380"
                    ]
    },
    {
        "question":  "Should the convention be recorded as ADR 0022, or is a helper docstring plus an appended memory entry enough?",
        "recommendation":  "**Write ADR 0022 — but this is the softest of the five gates and a lighter answer is defensible.** For: the RCA\u0027s Root tier is explicitly about stopping a third site being invented, ADRs are the artifact this repo checks mechanically (indexed, sequentially numbered, cost stated — tests/test_repo_structure.py:33-67), and the convention binds future guards rather than just this fixture. Against: it spends a decision number on a testing convention, and the memory entry plus Phase 4\u0027s guard already bind the next agent. If the operator prefers the lighter form, drop the ADR and keep the memory append plus the `guard_trees.py` docstring — but then Phase 4\u0027s contract guard becomes load-bearing rather than severable, because it would be the only thing holding the rule. Either way: do NOT amend ADR 0020 (its :95-102 stays true), and do NOT restate the rule inside CLAUDE.md\u0027s build-rulebook section.",
        "related":  [
                        "docs/decisions/0020-sanctioned-lookahead-seam.md:95-102",
                        "tests/test_repo_structure.py:33-40",
                        "tests/test_repo_structure.py:43-57",
                        "tests/test_repo_structure.py:60-67",
                        ".claude/agents/data-engineer-memory.md:351-356"
                    ]
    },
    {
        "question":  "Should tests/test_grain_contracts.py:364-367 (and tests/test_read_only.py:344-345) get the same `tree_root` seam, so the convention is genuinely repo-wide?",
        "recommendation":  "**No — leave both untouched in this change, and record it as a named follow-up rather than an unfiled observation.** Neither plants anything, so neither is part of the cause; giving them a seam now would be scope creep into files the RCA explicitly excludes (:133-135 — `src/` and its guards are not implicated). They matter here only as the architectural argument for un-sharing the tree rather than teaching one reader about probe names. If the operator wants the seam repo-wide for symmetry, file it as its own request — an unfiled observation is precisely the failure this request documents (BUGFIX_REQUEST.md:24-28: observed five times, filed zero times).",
        "related":  [
                        "tests/test_grain_contracts.py:75",
                        "tests/test_grain_contracts.py:364-380",
                        "tests/test_read_only.py:292",
                        "requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md:133-135"
                    ]
    }
]
```
