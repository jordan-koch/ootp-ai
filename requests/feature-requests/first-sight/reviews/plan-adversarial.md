# Planning Panel — Adversarial & Meta-Audit Findings

Run 2026-08-16 · workflow `wf_567f4abc-f44`.
Panel health: **3/3 planners, 2/2 adversaries, 1/1 meta-audit** — but
`degraded_lenses = [merge:fallback]`: the structured merge died on the 64k
output-token ceiling. Findings: 62 total — 9 blocker, 20 major.

> **`convergence_map` is empty and that is a degradation artifact, not a signal.**
> It is produced by the structured merge, which failed. Absence of convergence data
> here does NOT mean the planners disagreed.

Six of the nine blockers (F02, F03, EX-01, MERGE-01, MERGE-02, MERGE-04) are
consequences of that merge failure rather than defects in the planners' thinking.
Verbatim, with two mechanical normalizations and no edits to substance: absolute
machine paths rewritten repo-relative (finding F01), and one relative Markdown link
written at the wrong directory depth by a panel agent converted to a code span, because
`tests/test_doc_links.py` resolves every link target in every tracked `.md` and a dead
one fails the build.

## Reviewer summaries

### code-grounded

CODE-GROUNDED VERIFICATION of the merged `first-sight` plan draft. I read every file the plan cites and checked the line numbers literally, plus ran the guards the plan depends on. The good news first: the plan's hardest, most consequential citations are correct and I confirmed them by execution, not by reading. `git check-ignore -q tests/fixtures/sample.dat` exits 1 (NOT ignored — `.gitignore:62`'s `!tests/fixtures/**` really does negate `:31`'s `*.dat`), `git check-ignore -q var/reports/roster.md` exits 0, `src/ootp_ai/__init__.py` is exactly 241 bytes / 7 lines, `uv run pytest -m "not gamedata"` really is 18 passed, `tests/` really does hold exactly the four named guards, `docs/` really does hold only `data-access.md` and `league-rules.md` (Open Question 10 is right — `docs/data-sources.md` does not exist), `leagues.dat` really does appear at `docs/league-rules.md:129` and `:295` and nowhere else in `docs/`, and `tests/test_request_links.py` really is named by `.claude/skills/create-implementation-plan/SKILL.md:251` while not existing. The `data-engineer.md` deny-set lines (`:150`-`:157`), the header-layout block (`data-access.md:172-189`), the primitives table (`:193-201`), the ADR 0012 corollary (`:75-76`) and the ADR 0004 Notes range (`:89-106`) all resolve exactly as claimed. That is an unusually high hit rate for a citation-dense plan.

But three defects make the draft un-executable as shipped, and one turns CI red on the very first commit. (1) `onboarding.files_to_read` carries absolute `...` paths; I ran the real `PATTERNS` from `tests/test_no_leaks.py` against them and they match `windows drive path`, so the tracked `IMPLEMENTATION_PLAN.md` would fail `test_no_machine_paths_or_identifiers` — the exact guard acceptance criterion 16 requires green. (2) The `phases` array is four overlapping plans (`[code-grounded]` 1-11, `[sequencing]` 1-13, `[domain-convention]` 0-11) with a fifth numbering in the prose, and they disagree on ordering (the spike is Phase 1 / Phase 2 / Phase 0 depending which you read). A cold agent cannot execute four plans. (3) `decisions`, `conventions`, `convergence_map` and `gated_decisions` are empty arrays while the prose carries roughly ten binding decisions (driver choice, `save_id` definition, `ingest_run` keying, `name_space` discriminator, catalog location, output partitioning) — the structured record a cold agent scans is blank.

Beyond that the citation errors are few and small but real: `pyproject.toml:53` is `"UP"`, not `A` (which is at `:55`, and the plan itself says `:55` elsewhere — an internal contradiction); `ops/mysql-bootstrap.sql:35-38` is a comment about utf8mb4, not where the collation is declared (`:24`, `:31`, `:33`); `docs/data-access.md:336` is `Use INSERT IGNORE`, the Replace-accents row is `:335`; and `.claude/agents/data-engineer.md:53-58` is cited for the `challenge.dat`-at-241-bytes fact, which appears nowhere in that file (it is `docs/data-access.md:65-68`). One substantive testing defect survives from the scope into the plan unresolved: acceptance criterion 4's literal command `uv run pytest tests/test_grain_contracts.py` has no `-m` filter, so it will also collect the `-m gamedata` half the plan puts in the same file — and the plan's own two acceptance lines for that phase contradict each other about whether the filter is there.

### executability

ADVERSARY 2 — EXECUTABILITY & SEQUENCING. The plan's *content* is unusually well-grounded: I spot-checked ~40 file:line citations and the overwhelming majority are exact (data-engineer.md:69-74/98/101-104/150-157, data-access.md:172-181/195-197/224-228/238/282/292-295, league-rules.md:26/129/295 — and `grep leagues.dat docs/` returns exactly those two sites, so AC19's target set is right; pyproject.toml:9/23/55/57/58/78/80; test_no_leaks.py:24-28/31-48/106-107; .gitignore:18/31/62; gm/standing-orders.md:42-50; requests/feature-requests/README.md:119). I also independently re-ran the plan's two "VERIFIED" gitignore probes: `git check-ignore -q tests/fixtures/sample.dat` exits **1** and `git check-ignore -q var/reports/roster.md` exits **0** — both claims hold, and the baseline `uv run pytest -m "not gamedata"` is green at 18 passed as stated. The failures are structural, not factual. (1) ORDER: the artifact contains **four mutually inconsistent phase sequences** — a 14-phase narrative triplicated verbatim across `summary`/`architecture_map`/`onboarding.what_it_is`, plus three separately-numbered arrays inside `phases[]` — that disagree on whether names.dat precedes players.dat, whether the spike precedes the config layer, and where the contracts land. A cold agent cannot determine what to run. (2) A real internal contradiction: `is_renderable()` as "the only path to a page" makes the plan's own pre-registered `list_id` fallback unreachable. (3) Missing prerequisites: `uv.lock` **is tracked** (confirmed via `git ls-files -- uv.lock`) and no phase relocks it; nobody is told to populate the two new keys in the untracked local `.env`; there is no `conftest.py` and no subpackage `__init__.py` anywhere in files_to_touch. (4) Six acceptance criteria invoke `grep -rn` on a PowerShell-only box. (5) The marker-widening "hard collection error" that drives the phase-1 ordering argument is not real — `--strict-markers` validates the marker *name*, which is already registered. Conventions are otherwise baked in well: read-only, sequential-walk, resolve-by-name, /commit-only, tests/-is-deny-set are all stated and re-asserted per phase.

### meta-audit

META-AUDIT OF THE MERGE. The merge has two halves and they diverge sharply. The NARRATIVE half (`summary` / `architecture_map` — the same ~30KB document) is a genuinely good convergence: 14 phases, ~20 deduped risks, a per-phase /commit cadence, and it faithfully carries each planner's distinctive contribution (code-grounded's brute-force-against-a-full-answer-key names method and the `quote_ident` incident; sequencing's fixed-offset negative control, the ordering-first marker widening, and the "guards that must be seen to fail" drill; domain-convention's `name_space` discriminator, the NOT-NULL-PK/COUNT(DISTINCT) trap, the AC10-vs-append-only-ingest_run collision, the structural-absence allowlist, and scoping the `historical_id` guard to `src/` so `test_names_join_boston.py` can still do its job).

On SCOPE-CREEP the merge is clean. I checked all nine gated items (coaches.dat, the world.dat §1 diff, playoff seeds, minor-league populations in the roster report, dbt silver/gold, the rating-scale dataset, OSA divergence, the report registry, the second OSA export) and NONE is promoted: two bespoke renderers, W-L-pct-GB with no seeds, org-only rosters, a dbt deferral note in ADR 0004 §Notes. The one arguable addition — a third `.env` key for the report output root beyond Core §19's two — is required by Core §15 and is correctly surfaced as an operator question.

The STRUCTURED half was not merged at all. `phases` holds all 36 raw proposal phases concatenated and planner-tagged, under three incompatible numberings and orderings. `files_to_touch` holds three concatenated lists that name the same module twice under different names (`primitives.py`/`cursor.py`, `load.py`/`loader.py`, `rosters.py`/`roster.py`). `risks` holds ~46 entries covering ~20 distinct risks. `testing` holds three overlapping test plans whose per-phase selector table is keyed to a numbering the narrative does not use. `decisions`, `conventions`, `convergence_map` and `gated_decisions` are all empty — so the merge left no record of its own convergence and none of the eight binding design calls the prose makes. A cold agent consuming the structured fields gets an unexecutable plan.

Beneath the packaging there is one real convergence error with teeth: the merge took sequencing/domain's names-before-players ordering but imported code-grounded's names method, which walks player records — so Phase 6 cannot run without Phase 7, and Phase 7's AC9 display-name assertion cannot run without Phase 6. And one measured cost-unrealism: I measured `$OOTP_INSTALL` at 19,243 files / 3,751.9 MB and `$OOTP_SAVED_GAMES` at 11,425 files / 2,315.6 MB, so the read-only proof the plan calls "the cost of seconds" and prescribes at eight checkpoints is a 6.07 GB double-hash over 30,668 files.

## Code-grounded / executability adversaries

### BLOCKER (5)

#### [F01] Absolute machine paths in files_to_read will turn CI red via test_no_leaks.py

*reviewer:* code-grounded · *confidence:* high · *category:* correctness

**Location:** tests/test_no_leaks.py:25

**Problem.** `onboarding.files_to_read` carries entries with absolute paths, e.g. `requests/feature-requests/first-sight/PROJECT_SCOPE.md`, `pyproject.toml`, `.claude/agents/data-engineer.md` (11 of the 15 entries in the first list). `IMPLEMENTATION_PLAN.md` is a TRACKED file. I imported the real `PATTERNS` list from `tests/test_no_leaks.py` and ran it against those exact strings: the `windows drive path` pattern at `:25` MATCHES all of them. `test_no_machine_paths_or_identifiers` (`:81-94`) enumerates every tracked `.md` and would report the plan itself as a violation. That guard is one of the four the plan's own acceptance criterion 16 requires to stay green, so the plan document fails the plan's own first acceptance gate. CLAUDE.md's ADR 0006 section states the same rule independently: 'No machine-specific paths, account ids, tokens, or personal identifiers.'

**Proposed fix.** Rewrite every path in `onboarding.files_to_read` (and anywhere else in the plan) as repo-relative: `requests/feature-requests/first-sight/PROJECT_SCOPE.md`, `pyproject.toml`, `.claude/agents/data-engineer.md`. Then, before the plan is committed, run `uv run pytest tests/test_no_leaks.py` and confirm 18/18 still passes with the new file staged — `tracked_text_files()` at `:31-48` shells to `git ls-files`, so the check only sees the plan AFTER it is staged.

#### [F02] The phases array contains four different, mutually contradictory plans

*reviewer:* code-grounded · *confidence:* high · *category:* plan-structure

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:604

**Problem.** `phases` is not one plan. It is four concatenated plans, each with its own numbering and ordering, distinguished only by a bracketed prefix in the `name` field: `[code-grounded] Phase 1-11`, `[sequencing] Phase 1-13`, `[domain-convention] Phase 0-11` — and the prose in `summary`/`architecture_map` describes a FIFTH numbering ('Thirteen phases', 0-13). They disagree on load-bearing sequencing: the scouted-view spike is `[code-grounded] Phase 1`, `[sequencing] Phase 2`, `[domain-convention] Phase 0`, and prose Phase 2. The `leagues.dat` doc correction is `[sequencing] Phase 2` (early, with a `tests/test_doc_corrections.py`) but `[domain-convention] Phase 10` and prose Phase 12 (late, via `/update-docs`). A cold agent told to 'execute Phase 3' has three different answers. This defeats the premise the scope states at PROJECT_SCOPE.md:604 — that a cold stage-3 agent works from this document.

**Proposed fix.** Collapse to ONE phase list. The prose narrative (Phase 0 pre-register, 1 toolchain/config, 2 spike, 3 parser spine, 4 snapshot/read-only, 5 teams, 6 names, 7 players, 8 contracts/bronze, 9 differential, 10 reports, 11 catalog, 12 docs, 13 USER-RUN) is the most complete and is what `summary` already commits to; adopt it verbatim and delete the other three sets, folding any unique step (e.g. `[sequencing] Phase 2`'s `tests/test_doc_corrections.py`) into the surviving phase that owns it.

#### [F03] decisions, conventions, convergence_map and gated_decisions are empty while the prose carries ~10 binding decisions

*reviewer:* code-grounded · *confidence:* high · *category:* plan-structure

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:705

**Problem.** Every structured decision field in the draft is an empty array, yet the prose settles at least ten choices that bind the implementer and that a later reader must be able to find: the MySQL driver (`PyMySQL` + `types-PyMySQL`), `save_id` = save directory stem validated against `^[A-Za-z0-9_-]+$`, `ingest_run` keyed `(snapshot_date, save_id)` with a loud refusal on re-land, the `name_space` NOT NULL discriminator on `bronze_name`, every PK column NOT NULL (because MySQL's COUNT(DISTINCT ...) drops NULL tuples), report output partitioned `<output_root>/<save_id>/<snapshot_date>/`, tracked catalog at `docs/warehouse-catalog.md`, code spans instead of Markdown links, TOML via stdlib `tomllib`, and the ownership split. The upstream scope models the expected shape at PROJECT_SCOPE.md:705 with eleven numbered Decisions each carrying a rationale. Several plan items also appear in BOTH the prose as decided and in Open Questions as unresolved, so the same item reads two ways.

**Proposed fix.** Populate `decisions` with each settled call as {decision, rationale, alternatives_rejected, phase_it_binds}. Move the genuinely-unsettled ones (driver confirmation, `save_id` definition, catalog location, output-root `.env` key, AC15 de-marking) into `gated_decisions` with the operator as the gate, and delete their duplicate appearances from the decided list so nothing reads both ways.

#### [EX-01] The plan contains four different, mutually inconsistent phase sequences — a cold agent cannot know which to execute

*reviewer:* executability · *confidence:* high · *category:* sequencing

**Location:** plan: `phases[]` array (11 entries prefixed `[code-grounded]`, 13 prefixed `[sequencing]`, 12 prefixed `[domain-convention]`) vs the 14-phase narrative in `summary` / `architecture_map` / `onboarding.what_it_is`

**Problem.** The merged draft was never reconciled into one plan. `phases[]` holds three complete, independently-numbered lane outputs, and the narrative fields hold a fourth (Phases 0–13), triplicated verbatim. They disagree on load-bearing order, not just labels: (a) `[code-grounded]` Phase 5 walks `players.dat` BEFORE Phase 6 resolves `names.dat`, while the narrative Phase 6 and `[domain-convention]` Phase 5 put names FIRST and explicitly justify it — "the phase is sequenced *before* the players walk so the branch fires at a clean checkpoint rather than mid-report"; (b) the spike is Phase 0 in `[domain-convention]` (before any config exists), Phase 1 in `[code-grounded]`, and Phase 2 in both the narrative and `[sequencing]` (after config/deps); (c) the `contracts/` skeleton + `policy.py` land in `[code-grounded]` Phase 3 but in narrative Phase 8 and `[sequencing]` Phase 8; (d) `[sequencing]` splits contracts (P8) from the loader (P9) while the narrative fuses them (P8). Two agents handed this build two different systems, and one of them inherits precisely the risk the other says it mitigated.

**Proposed fix.** Collapse to ONE numbered sequence before this ships as IMPLEMENTATION_PLAN.md. Recommend the 14-phase narrative (0–13) as canonical, since it is the only one that carries the ownership split, the guards-must-be-seen-to-fail table, and the risk register. Delete the three lane arrays from `phases[]` and replace them with the canonical 14, and cut the verbatim triplication so `summary` holds a short abstract and `architecture_map` holds only §1. Where a lane disagreed, state the resolution once (names.dat precedes players.dat; spike after config; contracts precede the loader).

#### [EX-02] `is_renderable()` as the sole serving gate makes the plan's own pre-registered `list_id` fallback unreachable

*reviewer:* executability · *confidence:* high · *category:* correctness

**Location:** plan §1.3(c) + Phase 10 step 4 vs Phase 0 step 2 and Phase 7 step 5; grounds in requests/feature-requests/first-sight/PROJECT_SCOPE.md:275-282 (AC13) and :384-389 (Core §9)

**Problem.** §1.3(c) defines `is_renderable(field)` to return false when `epistemic in {"unconfirmed", "assumed"}`, and Phase 10 step 4 says "Route EVERY report column through `contracts/policy.py::is_renderable()`. There is no second path to the page." But Phase 0 step 2 pre-registers the `list_id` fallback as: land it as an opaque integer and "group the roster report by raw value with a header line stating the meanings are `unconfirmed`". Under the single gate, a field labelled `unconfirmed` cannot reach the page at all — so if the fallback fires (a branch the plan treats as live, and Phase 7's acceptance explicitly allows), Phase 10 cannot render the roster grouping the request depends on. The same collision hits any non-rating field that has not yet earned an `inferred` label. Phase 10's acceptance would be unsatisfiable and the implementer's cheapest escape is to quietly upgrade the label — the exact error the discipline exists to prevent.

**Proposed fix.** Split the predicate in §1.3(c) into two rules and say so in the plan text: (i) `category == "rating-true"` → WITHHELD, no exceptions (ADR 0012); (ii) a low-confidence *non-rating* field → renderable only through an explicit `render_with_uncertainty` path that forces the report to emit the raw value plus the `unconfirmed` banner, and is asserted by the AC13 negative test alongside the `rating-scouted` case. Then restate Phase 10 step 4 as "every report column routes through `policy.py`; `policy.py` has exactly two outcomes and no bypass."

### MAJOR (13)

#### [F04] Acceptance criterion 4's command has no marker filter but the plan puts a gamedata test in the same file

*reviewer:* code-grounded · *confidence:* high · *category:* testing

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:213

**Problem.** AC4 is literally `uv run pytest tests/test_grain_contracts.py` ... 'is green offline', and AC5 (PROJECT_SCOPE.md:222) is `uv run pytest -m gamedata tests/test_grain_contracts.py::test_roster_grain_is_not_player_grain` — the same module. pytest markers only FILTER; they do not skip. Running AC4's command with no `-m` collects and runs the gamedata half, which needs a live MySQL, so AC4 fails on a machine with no warehouse. The plan does not resolve this and its own acceptance lines disagree: prose Phase 8 says `uv run pytest tests/test_grain_contracts.py -m "not gamedata"` green offline, while `[domain-convention] Phase 7` acceptance says `uv run pytest tests/test_grain_contracts.py tests/test_withheld_fields.py` green OFFLINE — which is exactly the command that breaks. The plan already prescribes the correct pattern for `tests/test_names_join.py` ('skips loudly with a named reason if `ootp_truth_real` is unreachable') but does not generalise it.

**Proposed fix.** State as a plan-wide convention: every `-m gamedata` test ALSO carries a runtime `pytest.skip(reason=...)` when its precondition (game install, save, or reachable MySQL) is absent, so AC4's literal unfiltered command passes offline by skipping rather than erroring. Then make every acceptance line in the plan quote the criterion's command verbatim rather than a paraphrase with an added `-m` filter.

#### [F05] files_to_touch names the same module twice under two different paths, six times over

*reviewer:* code-grounded · *confidence:* high · *category:* plan-structure

**Location:** src/ootp_ai/__init__.py:3

**Problem.** `files_to_touch` merges entries from the four phase sets without deduplication, so six artifacts appear under two or three incompatible names — and since `src/ootp_ai/` today contains only `__init__.py` (verified: 241 bytes, docstring at :3 reading 'No pipeline code yet'), every one of these is created from nothing and a cold agent following the list literally creates duplicates. The collisions: `parser/primitives.py` ('forward-only Cursor') vs `parser/cursor.py` ('Forward-only cursor ... No seek method at all'); `parser/rosters.py` vs `parser/roster.py`; `warehouse/load.py` vs `warehouse/loader.py`; `contracts/loader.py` vs `contracts/__init__.py` (both 'tomllib reader'); `tests/test_db_identifiers.py` vs `tests/test_quote_ident.py` (both assert `quote_ident('current_date')` backticks); and the spike verdict lands at THREE paths — `reviews/spike-scouted-view.md`, `reviews/scouted-view-spike.md`, and `SPIKE_SCOUTED_VIEW.md`. The architecture map at section 1.2 names `primitives.py`, `rosters.py`, `load.py`, `contracts/loader.py`, so that set should win.

**Proposed fix.** Deduplicate `files_to_touch` against the section 1.2 package tree, keeping `parser/primitives.py`, `parser/rosters.py`, `warehouse/load.py`, `contracts/loader.py`, `tests/test_db_identifiers.py`, and a single spike path `requests/feature-requests/first-sight/reviews/spike-scouted-view.md`. Also replace the aggregate entry 'tests/ (16 new modules, ALL main-thread authored)' — which is not a path and which then lists 20 modules, not 16 — with one row per test file.

#### [F06] Two incompatible snapshot/report partition schemes with no mapping between them

*reviewer:* code-grounded · *confidence:* high · *category:* correctness

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:358

**Problem.** Plan section 1.4 says reports render to `<output_root>/<save_id>/<snapshot_date>/roster.md`, and section 1.3(d) makes `save_id` the save directory stem (`OOTP-AI`). But Phase 4 step 1 says `snapshot.py` copies to `<snapshot_root>/<league>/<sim_date>/`, following Core section 5 at PROJECT_SCOPE.md:358 ('copy only the parsed files to the snapshot root under `<league>/<sim_date>/`'). Two different first components (`save_id` vs `league`) and two different second components (`snapshot_date` vs `sim_date`), with no statement anywhere that they are the same value. This matters because the plan keys `ingest_run` on `(snapshot_date, save_id)` and AC10 requires re-landing an existing snapshot id to refuse — if the snapshot directory is keyed `(league, sim_date)` while the warehouse is keyed `(save_id, snapshot_date)`, the directory-collision check and the warehouse refusal are looking at different identities.

**Proposed fix.** Pick one identity pair and use it everywhere: `<root>/<save_id>/<snapshot_date>/` for both the snapshot directory and the report output root, with one sentence stating `save_id` is the `.lg` directory stem and `snapshot_date` is the sim date read from `saved_games.dat`. Restate Phase 4 step 1 in those terms and note it as a deliberate refinement of Core section 5's `<league>/<sim_date>/` phrasing.

#### [F07] The plan gives two different, both-wrong Index-row status words for a stage-3 deliverable

*reviewer:* code-grounded · *confidence:* high · *category:* process

**Location:** requests/feature-requests/README.md:110

**Problem.** The status grammar at `requests/feature-requests/README.md:110` is `intake -> scoped -> planned -> implemented`, and the first-sight row at `:119` currently reads `scoped` (verified). The plan says two different and both-incorrect things: `files_to_touch` says 'Advance the first-sight Index row at :119 from `scoped` to `plan`' — `plan` is not a value in the grammar, `planned` is — and `[domain-convention] Phase 10` says 'Set the Index row ... from `scoped` to `implemented`, and move the slug directory into `_done/`', which is stage 4's terminal transition, not stage 3's. That second instruction also directly contradicts the plan's own Phase 13 commit note: 'Do not mark the request `implemented` on the acceptance panel's word alone ... Move the slug to `_done/` only after both come back green.'

**Proposed fix.** State once: landing this plan sets the `:119` Index row and the `PROJECT_SCOPE.md` status header to `planned`; only stage 4, after USER-RUN criteria 20 and 21 return green, sets `implemented` and moves the slug into `_done/` per `requests/feature-requests/README.md:102-104`. Delete the `[domain-convention] Phase 10` instruction.

#### [EX-03] `uv.lock` is tracked, Phase 1 changes three dependencies, and no phase relocks or stages it

*reviewer:* executability · *confidence:* high · *category:* missing-step

**Location:** Phase 1 step 2 and `files_to_touch` (no `uv.lock` entry); verified `git ls-files -- uv.lock` returns `uv.lock`, and `.gitattributes` carries `uv.lock  linguist-generated=true -diff`

**Problem.** Phase 1 moves `python-dotenv` from `[dependency-groups] dev` (pyproject.toml:23) into `[project].dependencies` and adds `PyMySQL` + `types-PyMySQL`. The lockfile is a tracked file (75 tracked files total, uv.lock among them). No step, no acceptance criterion, and no `files_to_touch` row mentions it. In practice the first `uv run` after the edit silently rewrites `uv.lock` in the working tree, so the implementer arrives at the `/commit` gate with an unexplained modified tracked file they did not author and were not told to expect — and `/commit` stages deliberately, so the likely outcome is a committed pyproject with a stale-or-unstaged lock. CI's `uv sync --all-extras --dev` (.github/workflows/ci.yml:35) then re-resolves against a lock that does not match the manifest.

**Proposed fix.** Add to Phase 1 steps: "after editing `pyproject.toml`, run `uv lock` and stage `uv.lock` in the same unit of work — it is tracked." Add `uv.lock` to `files_to_touch` marked MODIFY (generated, main thread — it sits outside the subagent's `src/ootp_ai/**` target paths). Add to Phase 1 acceptance: `git status --porcelain` shows no unstaged tracked modification other than the files the phase declares.

#### [EX-04] Six acceptance criteria are `grep -rn` commands on a PowerShell-only platform

*reviewer:* executability · *confidence:* high · *category:* environment

**Location:** Phase 1 acceptance (`grep -rn 'parents\[' src/`), Phase 4 acceptance (`grep -rn 'open(' src/ootp_ai/`), Phase 12 acceptance (`grep -rn 'leagues.dat' docs/` — this one IS acceptance criterion 19), plus `grep -r MYSQL_TRUTH_OSA_DATABASE` and `grep -rniE '[A-Za-z]:[\\/]' src/` in the lane phases

**Problem.** The build platform is Windows PowerShell — CLAUDE.md's env block says so and `.claude/agents/data-engineer.md:169` states it explicitly: "The shell tool on this platform is **`PowerShell`**, not `Bash`." Stock Windows has no `grep`. A cold agent copying these acceptance commands literally gets `grep : The term 'grep' is not recognized`, and the most likely recovery is to declare the criterion unverifiable or hand-wave it — which is worst for AC19, whose entire proof is the grep. The `-rniE '[A-Za-z]:[\\/]'` variant additionally re-implements `tests/test_no_leaks.py`'s PATTERNS regex badly, without the drive-letter lookbehind that file documents at :20-23 as load-bearing.

**Proposed fix.** Rewrite every acceptance grep as PowerShell or as the Grep tool. e.g. AC19 becomes `Select-String -Path docs\*.md -Pattern 'leagues\.dat'` (which today returns exactly `league-rules.md:129` and `:295` — I confirmed the target set is those two sites and nothing else). For the leak check, drop the ad-hoc regex entirely and cite `uv run pytest tests/test_no_leaks.py` — the guard already owns those patterns.

#### [EX-05] Nobody is told to populate the two new keys in the local, untracked `.env` — Phases 2 and 3 depend on them

*reviewer:* executability · *confidence:* high · *category:* missing-step

**Location:** Phase 1 step 5 (edits `.env.example` only) vs Phase 2 step 1 and Phase 3 step 8, which read the probe saves; `.env.example:1` and `.gitignore:4-6` confirm `.env` is untracked

**Problem.** Phase 1 adds keys for the retained standard-mode probe save and the disposable Challenge Mode probe save to `.env.example`, with all values empty (correctly — `tests/test_no_leaks.py:25` would flag a drive letter). But `.env` is the file the config layer actually reads and it is gitignored, so the new keys do not exist on the operator's machine until a human types them. Phase 2's spike reads the probe save's `scouting.dat`, and Phase 3's `test_save_enumerator.py` gamedata half runs "against the disposable Challenge Mode probe first" — both hard-fail on an unset key. The plan also records (Core §2, and the scope confirms) that `OOTP_SNAPSHOT_ROOT` is *already empty* in the live `.env`, so this is a known-live class of gap, not a hypothetical.

**Proposed fix.** Add an explicit USER-RUN step at the end of Phase 1: "Operator: copy the new keys from `.env.example` into your local `.env` and fill them — the probe save directory, the Challenge Mode probe league, and the report/catalog output root. No later phase can start without them." Add to Phase 1 acceptance: `load_settings()` resolves all keys without raising, run as a one-line `uv run python -c`. Have `config.py` raise a named error listing the missing key rather than a KeyError.

#### [EX-06] Phase 4's read-only proof is specified to "run the full pipeline entry point" three phases before any pipeline entry point exists

*reviewer:* executability · *confidence:* high · *category:* sequencing

**Location:** Phase 4 step 6 and Phase 4 acceptance ("`uv run pytest -m gamedata tests/test_read_only.py` green … AC11")

**Problem.** At the end of Phase 4 the package contains config, saves, snapshot, the header reader and `saved_games.py`. There is no ingest entry point, no walker, no loader and no renderer — the first CLI entry point (`python -m ootp_ai.reports`) arrives in Phase 10. So the step as written is unexecutable, and the acceptance's claim that AC11 is green there is an overstatement: acceptance criterion 11 (PROJECT_SCOPE.md:261-266) says the manifest is taken "before and after a **full parse**", which cannot happen yet. The plan's own §3.5 mitigation (re-run it every phase from 5 onward) is the right instinct but it is written as regression insurance rather than as the admission that AC11 is only *closed* at Phase 12.

**Proposed fix.** Reword Phase 4 step 6 to "run the snapshot step (the only game-touching code that exists at this phase)" and change Phase 4's acceptance to "AC11's harness exists and is green against the snapshot step". Move the "AC11 satisfied" claim to Phase 12, whose acceptance already requires `uv run pytest -m gamedata` to pass in full in one pass, and note in Phase 4's commit note that AC11 is *partially* discharged.

#### [EX-07] The read-only proof digests every file under `$OOTP_INSTALL` and is mandated at every checkpoint "for the cost of seconds"

*reviewer:* executability · *confidence:* medium · *category:* efficiency

**Location:** Phase 4 step 6 ("build a manifest of size + `mtime_ns` + SHA-256 over every file under `$OOTP_SAVED_GAMES` and `$OOTP_INSTALL`") and plan §3.5 ("Checking both at every checkpoint costs seconds")

**Problem.** `$OOTP_INSTALL` is a full OOTP 25 game install — many gigabytes of art, audio and data — and `$OOTP_SAVED_GAMES` holds `OOTP-AI.lg` plus two probe saves, including `retired.dat` at 154,088,679 bytes that this feature explicitly never reads. Hashing all of it twice per run, and then re-running that from Phase 5 through Phase 13 as the plan mandates, is minutes-to-tens-of-minutes each time, not seconds. The predictable failure is not a wrong result — it is an implementer who quietly stops re-running the one guard the plan calls "the one unrecoverable failure in the project."

**Proposed fix.** Scope the manifest to what the pipeline can actually reach: full SHA-256 over `$OOTP_SAVED_GAMES/<league>.lg/**` and the probe saves, plus `$OOTP_INSTALL/data/database/` only (the sole install path this feature reads, per `.env.example:7-9`); for the rest of the install use size + `mtime_ns` with no digest. State the measured wall-clock of the resulting check in Phase 4's acceptance so the §3.5 "costs seconds" claim is either true or corrected.

#### [EX-08] The Phase-1 ordering argument rests on a marker claim that is false — `--strict-markers` validates the marker name, not its description

*reviewer:* executability · *confidence:* high · *category:* correctness

**Location:** Phase 1 step 1 ("Do **not** add a second marker … an undeclared marker is a **hard collection error** … the single cheapest ordering mistake available in this plan") and the `testing` section ("Until that lands, every warehouse-reading test … is a HARD COLLECTION ERROR"); grounds at pyproject.toml:78-81

**Problem.** `pyproject.toml:79-81` registers exactly one marker by NAME: `gamedata`. `--strict-markers` errors only on a marker name absent from that list. The description string "requires a local OOTP install or save" is inert metadata — `@pytest.mark.gamedata` on a warehouse-reading test collects and runs fine today, before any edit. So the widening is a docs-accuracy fix (worth doing, and the scope asks for it at PROJECT_SCOPE.md:184-189), not a blocking prerequisite. The plan escalates it into a sequencing constraint and uses it as part of the justification for running config before the spike, which means a cold agent reasons about ordering from a premise that does not hold — and Phase 1's acceptance ("`uv run pytest --collect-only -m gamedata` collects without a marker error") is a test that passes identically before and after the change, i.e. it verifies nothing.

**Proposed fix.** Demote the marker widening to a one-line docs correction inside Phase 1, remove the "hard collection error" framing from Phase 1 and from the `testing` section, and drop it from the ordering rationale in Open Question 2. Replace Phase 1's vacuous collect-only acceptance with a real one: the marker's description text now contains the word "warehouse", asserted by reading `pyproject.toml`.

#### [EX-09] Ten Open Questions are said to block Phase 1, but no phase encodes the gate and the `decisions`/`gated_decisions` fields are empty

*reviewer:* executability · *confidence:* high · *category:* sequencing

**Location:** plan §5 ("Open questions for the operator — settle these before Phase 1") vs the empty `decisions`, `conventions`, `convergence_map` and `gated_decisions` arrays; Phase 1 step 2 says "Record the choice and the stub story in the plan's Decisions"

**Problem.** Two failures compound. First, the plan repeatedly instructs the implementer to "record the pick and its rationale in the plan's Decisions" — a section that does not exist in the artifact, so the instruction is a dangling reference with nowhere to land. Second, at least four Open Questions are hard blockers with no gate: Q1 (MySQL driver) is required before Phase 1's acceptance can assert "mypy clean **with the new driver imported**"; Q3 (`save_id` definition) is flagged as "changing it later re-keys every bronze table" yet nothing stops Phase 8 emitting DDL without it; Q6 (report output root — a third `.env` key vs a subdirectory) is needed by Phase 10 but must be added to `.env.example` back in Phase 1; Q4 (catalog location) is needed by Phase 11 but may require a `tests/test_repo_structure.py:12-24` edit. No phase's steps or acceptance says "do not start until the operator has answered N."

**Proposed fix.** Populate `gated_decisions` with the four blocking questions, each naming the phase it gates and its default-if-silent. Add a Phase 0 step: "Put Q1, Q3, Q4 and Q6 to the operator and record their answers in the plan's Decisions section before Phase 1 begins," and make Phase 0's acceptance include "all four answered in writing." Add the missing `decisions` array with the driver pick, `save_id` definition, output-root key and catalog location as entries the implementer fills.

#### [EX-10] Reports filter to "the configured organization" but Phase 4 mandates resolving the human team from data and no org config key is ever defined

*reviewer:* executability · *confidence:* high · *category:* correctness

**Location:** Phase 10 steps 2 and 5 ("the **configured organization** only … zero rows belonging to any other") vs Phase 4 step 4 (folded-in §7, "Resolve the human team from data on every run … Code that hardcodes *'we are team 6'* … passes on ground truth and breaks on our league, invisibly"); Phase 1 step 3 lists no such key

**Problem.** Two phases specify the same value from two different sources and the plan never reconciles them. Phase 1's `Settings` enumerates install, saved-games, league, snapshot root, the two probe keys and MySQL — no organization. Phase 4 establishes `saved_games.dat` as the authoritative source of the human team (Boston for `OOTP-AI`, the Cubs for the probe) precisely so it is never hardcoded. Phase 10 then says "configured", which reads as a config key. The implementer either invents an eleventh `.env` key that duplicates a fact already read from data (and drifts from it the day the operator takes over a different club), or reads it from `saved_games.dat` and leaves Phase 10's wording and `test_reports.py`'s fixture unexplained.

**Proposed fix.** State once, in §1.3, that the reporting organization is *derived*: `settings.report_org = human_team_id resolved from saved_games.dat for the configured OOTP_LEAGUE`, with no config key. Reword Phase 10 steps 2 and 5 to "the resolved human organization" and have `tests/test_reports.py` assert the roster's org equals the value `parser/saved_games.py` returns for that save — which also gives folded-in §7 a test rather than a warning.

#### [EX-11] No `conftest.py` and no subpackage `__init__.py` anywhere in the plan — the files_to_touch checklist does not produce an importable, type-clean package

*reviewer:* executability · *confidence:* high · *category:* missing-step

**Location:** `files_to_touch` (20 new `tests/test_*.py` rows, zero `conftest.py`; `src/ootp_ai/parser/…`, `warehouse/…`, `contracts/…`, `reports/…`, `catalog/…`, `validate/…` rows with no `__init__.py`); mypy config at pyproject.toml:69-73 (`strict = true`, `files = ["src", "tests"]`)

**Problem.** Two concrete gaps. (a) Six new subpackages are created and not one `__init__.py` is listed. Under mypy strict over a `src` layout this is where "Source file found twice under different module names" and namespace-package resolution errors surface, and `uv run python -m ootp_ai.reports render` (acceptance criterion 14's literal command) plus hatchling's `packages = ["src/ootp_ai"]` both assume real packages. (b) There is no `conftest.py`, yet the plan mandates cross-cutting test behaviour in ~13 gamedata modules: resolved settings, a read-only `ootp_truth_real` connection, "skips **loudly with a named reason**" when truth is unreachable, and "every filesystem-touching test runs against the disposable Challenge Mode probe first … Encode the ordering *in the test modules*, not as prose." Without a shared fixture module that is copy-paste repeated a dozen times, and the loud-skip rule — the plan's own anti-vacuity guarantee — degrades on the third copy.

**Proposed fix.** Add `src/ootp_ai/parser/__init__.py`, `warehouse/__init__.py`, `contracts/__init__.py`, `reports/__init__.py`, `catalog/__init__.py`, `validate/__init__.py` to `files_to_touch` (subagent, Phase 3/8/10/11 as each appears). Add `tests/conftest.py` (main thread, Phase 1) owning: a `settings` fixture, `require_truth_db()` and `require_save()` helpers that `pytest.skip(reason=…)` with a named reason, and a `save_under_test` parametrization that yields the disposable probe before `OOTP-AI.lg`. Reference it from every gamedata phase so the ordering rule has one implementation.

### MINOR (20)

#### [F08] pyproject.toml:53 cited for ruff rule A — that line is UP

*reviewer:* code-grounded · *confidence:* high · *category:* citation

**Location:** pyproject.toml:53

**Problem.** `code_references` claims `pyproject.toml:53` — 'ruff selects `A` (builtin shadowing). A record walker naturally reaches for `id`, `bytes`, `list`, `type` and `format` as local names'. Line 53 is `"UP",        # pyupgrade`. `A` is at line 55. The plan is internally inconsistent about this: the summary's Phase 1 'Watch out' block correctly says 'Ruff already selects `A` at `pyproject.toml:55`'. A related entry cites `:56-59` for 'ruff selects DTZ ... PTH ... and A' — `A` at 55 is outside that range too (`DTZ` is `:57` and `PTH` is `:58`, both correct).

**Proposed fix.** Change the `code_references` entry to `pyproject.toml:55`, and correct the `:56-59` range to `:52-59`, which covers `N` at 52 through `RUF` at 59.

#### [F09] ops/mysql-bootstrap.sql:35-38 cited as where the collation is declared — it is a comment

*reviewer:* code-grounded · *confidence:* high · *category:* citation

**Location:** ops/mysql-bootstrap.sql:35

**Problem.** A `code_references` entry claims `ops/mysql-bootstrap.sql:35-38` — 'Schemas are `utf8mb4_0900_ai_ci` — accent- and case-INSENSITIVE'. Lines 35-38 are the prose comment 'utf8mb4 is load-bearing, not decorative. The export is configured with "Replace accents" OFF ...' and contain no COLLATE clause. The collation is declared three times: `:24` (`ootp`), `:31` (`ootp_truth_real`), `:33` (`ootp_truth_osa`). The plan's `risks` list gets this right ('ops/mysql-bootstrap.sql:24, :31, :33'), so this is an internal inconsistency as well as a wrong line — and it matters because SD-13's collation decision is one of the plan's top-five risks.

**Proposed fix.** Change the reference to `ops/mysql-bootstrap.sql:24, :31, :33`. Keep `:35-38` only if you want to cite the supporting comment, and label it as the rationale rather than the declaration.

#### [F10] docs/data-access.md:336 cited for the Replace-accents row — that is the INSERT IGNORE row

*reviewer:* code-grounded · *confidence:* high · *category:* citation

**Location:** docs/data-access.md:335

**Problem.** Phase 6 step 6 and the Risks section both cite `docs/data-access.md:336` for '`Replace accents` Off ... mangles names and breaks validation against `names.dat`'. Line 336 is `| Use INSERT IGNORE commands | **Off** — silently drops rows ...`. The `Replace accents` row is line 335. The plan's own `code_references` cites `:335` correctly, so this is a second internal inconsistency between the prose and the reference list.

**Proposed fix.** Change both prose citations from `docs/data-access.md:336` to `docs/data-access.md:335`.

#### [F11] data-engineer.md:53-58 cited for the challenge.dat 241-byte fact, which is not in that file

*reviewer:* code-grounded · *confidence:* high · *category:* citation

**Location:** .claude/agents/data-engineer.md:53

**Problem.** A `risks` entry reads: 'POINTING UNTESTED FILESYSTEM CODE AT `OOTP-AI.lg` FIRST. `challenge.dat` is present at 241 bytes and one write is unrecoverable with no backup upstream (`.claude/agents/data-engineer.md:53-58`).' I grepped the file: it never mentions `challenge.dat` or 241 bytes anywhere. Line 53 is the closing `(ADR 0001 (`docs/decisions/0001-read-only-no-write-back.md`)).` of the read-only paragraph. The 'one write destroys the league irreversibly, and there is no backup upstream' half IS at `:55-58` and is correct; the 241-byte half belongs to `docs/data-access.md:65-68` ('`challenge.dat` is present at exactly 241 bytes in a Challenge Mode save and absent otherwise').

**Proposed fix.** Split the citation: `.claude/agents/data-engineer.md:55-58` for the unrecoverable-write consequence, `docs/data-access.md:65-68` for the 241-byte filesystem mode check.

#### [F12] docs/league-rules.md:31 credited with a supersession claim it does not make

*reviewer:* code-grounded · *confidence:* high · *category:* citation

**Location:** docs/league-rules.md:31

**Problem.** A `code_references` entry says '`:26` and `:31` claim the warehouse supersedes section 1 "the moment the parser lands"'. Only `:26` says that — it is the lifespan-table row: 'Temporary. Every value is a column on the `leagues` row; the warehouse supersedes this the moment the parser lands'. Lines 30-31 read 'The split matters. Section 1 is scaffolding and should be deleted when it stops being needed.' — a related but distinct claim requiring a different edit. The plan's Phase 12 uses the range `:30-31`, which at least brackets the real sentence; the `:31` singleton does not.

**Proposed fix.** Cite `docs/league-rules.md:26` for the supersession claim and `:30-31` separately for the 'section 1 is scaffolding' claim, since correcting them requires two different edits and Risk 11 of the scope names both.

#### [F13] test_doc_links.py is described as scanning tracked .md files; it scans the filesystem

*reviewer:* code-grounded · *confidence:* high · *category:* correctness

**Location:** tests/test_doc_links.py:15

**Problem.** The plan repeatedly says the guard 'resolves every relative link target in every tracked `.md`'. `markdown_files()` at `:15` is `REPO_ROOT.rglob("*.md")` filtered only on `.git` and `var` path parts — it never consults `git ls-files`. So it also scans UNTRACKED Markdown anywhere outside `var/`. The open bugfix request confirms this behaviourally: its repro at `requests/bugfix-requests/_done/doc-link-guard-mismatch/BUGFIX_REQUEST.md:20-25` shows an untracked `_repro_fence_check.md` turning the suite red, and its line 38 notes 'Removing the file returns the suite to 18/18'. This matters for this feature specifically, because the plan has scratch and verdict Markdown written under `requests/feature-requests/first-sight/reviews/` — a stray link there breaks the LOCAL suite immediately, which is the exact opposite of the `test_no_leaks.py` staging blind spot the plan documents alongside it.

**Proposed fix.** Correct the description to 'every `.md` on disk outside `.git/` and `var/`, tracked or not', and add a one-line warning to Phase 2 and Phase 12: any scratch Markdown written outside `var/` is scanned immediately, so keep throwaway notes under `var/` (which the plan already prescribes for the spike script).

#### [F14] test_doc_corrections.py appears in one phase set and in no test inventory

*reviewer:* code-grounded · *confidence:* high · *category:* test-coverage

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:318

**Problem.** `[sequencing] Phase 2` creates `tests/test_doc_corrections.py` (asserting `leagues.dat` appears nowhere under `docs/` except on a line carrying an explicit correction marker) and its per-phase selector list references it as P2. But the plan's `testing` section lists it in neither the offline nor the gamedata inventory, `files_to_touch` has no row for it, and prose Phase 12 discharges AC19 with a bare `grep -rn 'leagues.dat' docs/` instead. So AC19 (PROJECT_SCOPE.md:318, which asks for 'a grep asserting the string `leagues.dat` appears nowhere in `docs/` except as an explicit correction note') has two different enforcement mechanisms depending on which phase set you read, and one of them creates a test file nothing else in the plan knows about. I verified the current state: `leagues.dat` occurs at exactly `docs/league-rules.md:129` and `:295` and nowhere else in `docs/`.

**Proposed fix.** Pick one. A committed `tests/test_doc_corrections.py` is the stronger choice — a grep in a commit note is not a regression guard, and nothing would stop the assertion returning. Add it to `files_to_touch`, to the offline test inventory in section 3.1, and to the single phase that lands the correction.

#### [F15] ingest_run table naming drifts across the plan and the six-table count does not reconcile

*reviewer:* code-grounded · *confidence:* medium · *category:* correctness

**Location:** .claude/agents/data-engineer.md:101

**Problem.** The ingest-run table is called `ingest_run` in prose Phase 8 step 5 ('key `ingest_run` on `(snapshot_date, save_id)`') and in `src/ootp_ai/warehouse/ingest_run.py`, but `bronze_ingest_run` in `[code-grounded] Phase 7` ('`bronze_ingest_run` carries UNIQUE(save_id, snapshot_date)'). Prose Phase 8's acceptance says the `ootp` schema 'holds exactly the six named tables' while the step list names only five by key (`bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name`, `bronze_field_label`) plus the ingest run under whichever name. A `warehouse/ddl.py` that emits DDL from `tables.toml` needs one literal name, and `tests/test_catalog.py` asserts 'every landed table appears' — a mismatch between the declaration and the emitter is exactly the prose-vs-enforcement drift `.claude/agents/data-engineer.md:101` demands must not exist ('states its grain in prose and enforces it with a uniqueness test, and the two must agree').

**Proposed fix.** Fix the name to `bronze_ingest_run` for consistency with the other five, list all six explicitly in the Phase 8 step 1 declaration, and state the key as `(snapshot_date, save_id)` in exactly one place.

#### [F16] Phase 0 ownership contradicts files_to_touch on who writes the spike artifacts

*reviewer:* code-grounded · *confidence:* high · *category:* process

**Location:** .claude/agents/data-engineer.md:144

**Problem.** Prose Phase 0's commit note says 'Main thread only, no code' for `requests/feature-requests/first-sight/reviews/spike-pivot-rule.md`, but `files_to_touch` marks both that file and `spike-scouted-view.md` as 'NEW (builder)'. The plan's section 0 ownership paragraph says the subagent's declared targets are `src/ootp_ai/**` and `requests/feature-requests/first-sight/reviews/**`, which makes the builder-authored reading legal under the allowlist at `.claude/agents/data-engineer.md:144` (`requests/<track>-requests/<slug>/reviews/`) — but the phase text says otherwise. Since Phase 0 is explicitly 'no code' and the spike needs a `.env`-resolved MySQL connection that Phase 1 has not built yet, spawning the builder for it also wastes a spawn.

**Proposed fix.** Make Phase 0 and Phase 2 main-thread work and change both `files_to_touch` rows to '(main thread)'. Keep `reviews/**` in the subagent's declared targets only for its own handoff file, which the return contract at `.claude/agents/data-engineer.md:206` requires it to write there.

#### [F17] Two phase-acceptance greps are vacuous — they pass trivially against the design the plan prescribes

*reviewer:* code-grounded · *confidence:* high · *category:* test-coverage

**Location:** src/ootp_ai/__init__.py:7

**Problem.** Phase 4's acceptance includes "`grep -rn 'open(' src/ootp_ai/` shows no write mode against any path derived from `OOTP_INSTALL` or `OOTP_SAVED_GAMES`" — but section 1.3(a) prescribes reading files with `Path.read_bytes()` and Phase 4 prescribes a manifest-writing copy, so nothing calls `open()` at all and the grep returns empty for the wrong reason. Phase 1's "`grep -rn 'parents\[' src/` returns nothing" is the same class: `src/ootp_ai/` today is a single 7-line file (verified, 241 bytes, `__version__` at `:7`), so it passes before any work is done. The plan itself sets the standard these fail — section 3.4, 'A guard nobody has observed failing is decoration', with five guards listed that must be seen to go red. These two cannot go red.

**Proposed fix.** Replace the `open(` grep with the real proof already in the plan: `uv run pytest -m gamedata tests/test_read_only.py` green with zero mtime and zero digest differences (AC11). If a static check is still wanted, scan for any file-open call whose mode argument is not `"rb"` AND assert the scanner flags a synthetic offending snippet — the same self-test pattern Phase 3 already prescribes for `test_no_fixed_offsets.py`.

#### [F18] The AC3 fixed-offset scan covers only src/ootp_ai/parser/, leaving byte-reading modules outside it unguarded

*reviewer:* code-grounded · *confidence:* high · *category:* test-coverage

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:209

**Problem.** AC3 scopes the scan to 'anywhere under `src/ootp_ai/parser/`', and the plan honours that. But the plan's own section 1.2 package tree puts byte-touching code OUTSIDE that directory: `src/ootp_ai/snapshot.py` (copies 46 MB of `.dat` files — the single most plausible place a chunked-copy `seek` appears) and `src/ootp_ai/validate/export_diff.py`. The plan is scope-conformant, so this is not a violation — but it is a gap a cold implementer should be told about rather than discover, especially since the plan calls the fixed-offset ban 'the silent-corruption class CLAUDE.md names as the most likely way to corrupt every downstream recommendation' and `.claude/agents/data-engineer.md:72` calls seeking code 'a blocker, not a style note'.

**Proposed fix.** Keep the AC3-mandated `src/ootp_ai/parser/` scan as the criterion, and add one sentence to Phase 3 step 7 noting the guard may be widened to all of `src/ootp_ai/` at no cost, since no non-parser module legitimately seeks — then either widen it or record the gap explicitly so it is a decision rather than an oversight.

#### [F21] summary, onboarding.what_it_is and architecture_map are three identical copies of the whole document

*reviewer:* code-grounded · *confidence:* high · *category:* plan-structure

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:418

**Problem.** All three fields contain the same ~40 KB text: the full plan from the '# IMPLEMENTATION PLAN' heading through Open Questions. `summary` should be a summary, `architecture_map` should be section 1 only, and `onboarding.what_it_is` should orient a cold agent in a few paragraphs. Triplicating them means every future edit must be applied three times or the copies diverge — and the plan violates its own stated principle about itself, since section 1.3(b) argues (correctly, echoing Core section 14 at PROJECT_SCOPE.md:418: 'one declaration, three consumers, so drift is structurally impossible') that a single source with multiple consumers is what makes drift impossible. It also means the wrong-line citations in F08, F10 and F11 each appear up to three times.

**Proposed fix.** Write `summary` as a short orientation (what this plan builds, the thirteen-phase shape, the three binding constraints); scope `architecture_map` to section 1 (what exists today, target package shape, the five seams, the two path decisions); scope `onboarding.what_it_is` to a few paragraphs plus the ownership split. Keep the full narrative in exactly one place.

#### [F22] onboarding.files_to_read has a malformed key and ten duplicate entries

*reviewer:* code-grounded · *confidence:* high · *category:* plan-structure

**Location:** .github/workflows/ci.yml:49

**Problem.** The final `files_to_read` entry — the one for `.github/workflows/ci.yml`, whose cited content at `:49` (`uv run pytest -m "not gamedata"`) I verified as correct — carries a bogus extra key `".path": "x"` alongside its real `path` and `why`. Separately, the list is a concatenation of several panelists' reading lists and repeats ten files under two entries each with different `why` text and different, sometimes conflicting, line citations: `PROJECT_SCOPE.md`, `.claude/agents/data-engineer.md`, `docs/data-access.md`, `pyproject.toml`, `tests/test_no_leaks.py`, `.gitignore`, `docs/league-rules.md`, `gm/standing-orders.md`, `.claude/agents/gm.md`, `tests/fixtures/README.md` — the first copy of each using an absolute path (see F01) and the second a relative one. A cold agent reading top to bottom reads the same file twice and gets two accounts of it.

**Proposed fix.** Drop the `.path` key. Merge each duplicated file into one entry with a relative path and a single consolidated `why` keeping the strongest line citations from both copies (e.g. for `pyproject.toml`: `:9` empty dependencies, `:23` dotenv in the dev group only, `:52-59` ruff selections, `:71-73` mypy strict over src and tests, `:78-80` strict-markers and the single `gamedata` marker).

#### [EX-12] Phase 4's `grep 'open('` read-only proof cannot catch the writes it is meant to catch

*reviewer:* executability · *confidence:* high · *category:* correctness

**Location:** Phase 4 acceptance: "`grep -rn 'open(' src/ootp_ai/` shows no write mode against any path derived from `OOTP_INSTALL` or `OOTP_SAVED_GAMES`"

**Problem.** Beyond the PowerShell issue (EX-04), the pattern is the wrong shape. ruff selects `PTH` (pyproject.toml:58), which pushes the code away from builtin `open()` toward `Path.read_bytes()`, `Path.write_bytes()`, `Path.write_text()`, `shutil.copy2()` and `Path.unlink()` — none of which contain the substring `open(` except `Path.open(`. So a genuine violation (`dest.write_bytes(...)` where `dest` derives from `OOTP_SAVED_GAMES`) passes this check cleanly, and the criterion reads as proof while proving nothing. It sits next to `test_read_only.py`, which is the real proof, and risks being trusted in its place.

**Proposed fix.** Delete the grep from Phase 4's acceptance and replace it with a static guard the main thread owns, in the same spirit as `test_no_fixed_offsets.py`: an `ast` scan over `src/ootp_ai/` flagging any write-family call (`write_bytes`, `write_text`, `open(..., mode!='rb'/'r')`, `shutil.copy*`, `os.utime`, `unlink`, `rename`) whose receiver traces to `settings.ootp_install` or `settings.ootp_saved_games`. Include the scanner self-test the plan already requires of its sibling guard.

#### [EX-13] Phase 6's acceptance asks `git ls-files` to inspect file contents, which it cannot do

*reviewer:* executability · *confidence:* high · *category:* correctness

**Location:** Phase 6 acceptance: "`git ls-files` lists no file **containing** a Lahman-to-name lookup"

**Problem.** `git ls-files` emits tracked paths; it has no notion of contents. As written the criterion is unrunnable, so a cold agent either skips it or substitutes something arbitrary. It guards a real and sharp hazard the plan itself identifies — `tests/test_no_leaks.py:106` catches `players.csv` by filename only, and `tests/fixtures/README.md:26-28` states plainly that a renamed real slice "is on you" — so leaving it unexecutable removes the only check on the one leak class this feature newly creates.

**Proposed fix.** Replace with a content scan over tracked text files, modelled on `tracked_text_files()` at `tests/test_no_leaks.py:31-48`: assert no tracked file matches the Lahman-ID shape `\b[a-z]{5,6}[a-z]{2}\d{2}\b` more than N times, and none matches it on the same line as a capitalised name token. Add it to `tests/test_no_leaks.py` as an extension (the plan already routes Folded-in §1 through that file) rather than as a bespoke Phase 6 command.

#### [EX-14] The `ootp_truth_osa` retirement is cited over line spans that include the `ootp_truth_real` create and grant

*reviewer:* executability · *confidence:* high · *category:* correctness

**Location:** plan onboarding entry for `ops/mysql-bootstrap.sql`: ":30-33 and :47-49 create and grant `ootp_truth_osa`, the schema Decisions 10 retires"

**Problem.** Read against the file: `:30-31` creates **`ootp_truth_real`** — the Tier B validator every differential test in Phases 6, 8 and 9 depends on — and `:32-33` creates `ootp_truth_osa`. Likewise `:47` grants `ootp`, `:48` grants `ootp_truth_real`, and only `:49` grants the osa schema. A cold agent told to delete ":30-33 and :47-49" destroys the create and grant for the ground-truth database and discovers it as an access-denied error mid-Phase 9, in a file the subagent is forbidden to touch (`ops/` is deny-set at `.claude/agents/data-engineer.md:152`). Phase 1's own step 5 gets it right ("removing the `ootp_truth_osa` create and its grant") — the onboarding row is the one that misleads.

**Proposed fix.** Correct the citation to ":32-33 (create) and :49 (grant)" and add an explicit "do not touch :30-31 or :48 — that is `ootp_truth_real`, the Tier B validator." Add to Phase 1 acceptance: `mysql -e "show databases"` still lists `ootp` and `ootp_truth_real`.

#### [EX-15] The bronze table-name set is inconsistent across phases, and an acceptance criterion counts "exactly six" against no canonical list

*reviewer:* executability · *confidence:* high · *category:* consistency

**Location:** narrative Phase 8 acceptance ("the `ootp` schema … holds exactly the six named tables") vs Phase 8 step 5 (`ingest_run`) vs the `[code-grounded]` lane (`bronze_ingest_run`, and "`bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name`, `bronze_field_label`, `bronze_ingest_run` and nothing else")

**Problem.** Three different names appear for the same object (`ingest_run`, `bronze_ingest_run`, and the module `warehouse/ingest_run.py`), and the metadata table is `bronze_field_label` in one place and "a warehouse metadata table" in another. The acceptance says "exactly the six named tables" but the six are never enumerated in the phase that asserts them. `tests/test_grain_contracts.py`'s offline half and `catalog/generate.py` both read the same declaration, so a name mismatch between `tables.toml` and the DDL emitter surfaces as a confusing failure in a test whose job is to prove they agree.

**Proposed fix.** Fix the canonical set once in §1.3(b): `bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name`, `bronze_field_label`, `bronze_ingest_run` — and note that `ingest_run` is an append-forbidden control table keyed `(snapshot_date, save_id)`, not a bronze fact table, if that distinction is intended. Restate the six in Phase 8's acceptance verbatim so the count is checkable.

#### [EX-16] Two wrong line citations in otherwise well-grounded reference lists

*reviewer:* executability · *confidence:* high · *category:* correctness

**Location:** `code_references`: "pyproject.toml:53 — ruff selects `A` (builtin shadowing)" and "docs/data-access.md:336 — The export was configured with `Replace accents` OFF"

**Problem.** Verified against the files: `pyproject.toml:53` is `"UP",` (pyupgrade); `A` is line 55 — which the plan's Phase 1 "Watch out" block cites correctly, so the artifact contradicts itself. `docs/data-access.md:336` is the `Use INSERT IGNORE commands` row; the `Replace accents` row is `:335`, which Phase 6 step 6 also cites correctly in one place and as `:336` in another. The brief's own standard applies: a cold implementer trusts a citation literally, and these two are the only ones out of roughly forty I checked that do not resolve.

**Proposed fix.** Change to `pyproject.toml:55` and `docs/data-access.md:335`. While there, correct the `ops/mysql-bootstrap.sql:35-38` reference for the collation — `:35-38` is the utf8mb4 rationale comment; the `utf8mb4_0900_ai_ci` collation is declared at `:24`, `:31` and `:33`, and `:24` is what Phase 6's collation risk actually rests on.

#### [EX-17] Snapshot and report output use two different partition keys for the same value

*reviewer:* executability · *confidence:* high · *category:* consistency

**Location:** Phase 4 step 1 (`<snapshot_root>/<league>/<sim_date>/`) vs §1.4 and Phase 10 step 1 (`<output_root>/<save_id>/<snapshot_date>/`)

**Problem.** `save_id` is defined in §1.3(d) as the save directory stem — i.e. the same string as `<league>` — and `snapshot_date` is the sim date. So the two schemes are the same partition wearing two names, but nothing in the plan says so. An implementer writing `snapshot.py` from Phase 4 and `reports/__main__.py` from Phase 10 produces two different path-building helpers, and the manifest lookup in Phase 9's differential (which must find the snapshot for a given `save_id`) has to guess which one it is.

**Proposed fix.** Standardise on `<root>/<save_id>/<snapshot_date>/` for both, note in §1.3(d) that `save_id == OOTP_LEAGUE` today and is validated `^[A-Za-z0-9_-]+$`, and put one `snapshot_path(settings, save_id, snapshot_date)` helper in `snapshot.py` that both Phase 4 and Phase 10 call.

#### [EX-18] Mutation-test instructions say "revert" five times without saying it must be a hand edit, in a repo that bans destructive git for subagents

*reviewer:* executability · *confidence:* medium · *category:* convention

**Location:** plan §3.4 ("Break each once … confirm red, revert") and the acceptance of Phases 3, 8, 9 and 11 ("Introduce `f.seek(128)` … confirm red, revert"; "Mutate the declared key … revert"; "Deliberately corrupt one parsed field … revert"; "Hand-edit one character … revert")

**Problem.** The plan's own §0 states the rule — "Subagents get read-only git … never `checkout`/`reset`/`restore`/`clean`/`stash`" — and `.claude/agents/data-engineer.md:188-190` makes it absolute, with a recorded incident: "a write-capable review agent once ran `git checkout` and silently wiped uncommitted work while a vacuous selftest passed green." Then the plan asks for five deliberate mutations and tells the implementer to "revert" each. The natural reading of "revert" is `git restore <file>` or `git checkout -- <file>`, which is exactly the banned command and exactly the incident. Four of the five mutations also land in main-thread-owned files (`tests/`, the tracked catalog), compounding the ownership confusion.

**Proposed fix.** Replace every "revert" with "undo the edit with the Edit tool — never `git restore`, `git checkout` or `git stash`; the mutation is deliberate and its undo is a hand edit." State once in §3.4 who performs each mutation (main thread for the `tests/`, catalog and declaration mutations; subagent only for the `src/ootp_ai/parser/` seek), and require `git status --porcelain` clean before the phase's `/commit`.

### QUESTION ()

#### [F19] AC15's de-marking is listed as an unresolved operator question but is already baked into Phase 11's acceptance

*reviewer:* code-grounded · *confidence:* high · *category:* process

**Location:** requests/feature-requests/first-sight/PROJECT_SCOPE.md:295

**Problem.** AC15 as decided reads `uv run pytest -m gamedata tests/test_catalog.py` for the whole criterion including the byte-identity clause. The plan's Open Question 5 asks the operator whether to split that clause off `gamedata` so CI enforces it. But Phase 11's acceptance already asserts it as done — '`uv run pytest tests/test_catalog.py -m "not gamedata"` green OFFLINE — the committed structural half is byte-identical to a fresh regeneration' — and section 3.1 lists 'the offline half of `test_catalog.py`' in the CI-enforced inventory. So the plan simultaneously asks permission and proceeds. Since this changes what the stage-4 acceptance panel checks against a DECIDED scope, it should not be resolved silently inside a phase body.

**Proposed fix.** Either move it to `gated_decisions` and write Phase 11's acceptance against AC15 as literally written (all `-m gamedata`), noting the recommended split as a follow-up; or get the operator's ruling before the plan lands and state AC15 as amended in exactly one place. Do not leave both readings in the document.

### NIT (3)

#### [F20] gm/staff.md is paraphrased as 'no staff exist' — it says inherited staff exist but none is engaged

*reviewer:* code-grounded · *confidence:* high · *category:* citation

**Location:** gm/staff.md:5

**Problem.** The plan justifies the new engineering-owned report kind with 'gm/staff.md records that no staff exist, so naming an owner would be fiction' (Phase 12 step 5, and `code_references` citing `gm/staff.md:5-8`). The file actually reads: 'Status: no staff engaged. The club exists ... and carries inherited staff, but none has been engaged and no analytics capability exists yet.' The conclusion still holds — no engaged analyst exists to own a report — but the stated premise is not what the file says, and the distinction matters if a later reader engages an inherited coach and expects the engineering-owned report kind to become unnecessary.

**Proposed fix.** Rephrase to 'gm/staff.md:5-8 records that no staff member has been engaged and no analytics capability exists, so no analyst can be named as the report's owner' — which is what the file says and what the scope's Decisions section 4 actually rests on.

#### [EX-19] The plan uses the status token `plan` where the repo's status grammar is `planned`

*reviewer:* executability · *confidence:* high · *category:* convention

**Location:** `[sequencing]` Phase 12 commit note ("advance the first-sight Index row at `:119` from `scoped` to `plan`") vs requests/feature-requests/README.md:110 ("**Status grammar:** `intake` → `scoped` → `planned` → `implemented`")

**Problem.** The Index row at requests/feature-requests/README.md:119 currently reads `scoped`. The grammar at :110 names the next state `planned`. Writing `plan` produces a status that is not in the grammar; `/update-docs` checks Index rows against artifact status headers, so this surfaces as a doc-gate finding rather than a test failure, but it is free to get right.

**Proposed fix.** Use `planned`. Also state which phase advances it: the plan currently defers all Index maintenance to Phase 12/13, but the row should move to `planned` when IMPLEMENTATION_PLAN.md lands (i.e. before Phase 0), and to `implemented` only after acceptance criteria 20 and 21 come back green from the operator.

#### [EX-20] The onboarding read-list has a malformed entry and roughly ten duplicates, and the plan body is triplicated verbatim

*reviewer:* executability · *confidence:* high · *category:* artifact-hygiene

**Location:** `onboarding.files_to_read` (29 entries; the `.github/workflows/ci.yml` row carries a stray `".path": "x"` key alongside `path`); `summary`, `architecture_map` and `onboarding.what_it_is` hold the same ~15,000-word document three times

**Problem.** `.claude/agents/data-engineer.md`, `docs/data-access.md`, `pyproject.toml`, `tests/test_no_leaks.py`, `.gitignore`, `tests/fixtures/README.md` and `PROJECT_SCOPE.md` each appear twice in the read list — once with an absolute `...` path and once relative — which both doubles the cold agent's read budget and puts machine-specific absolute paths into an artifact destined for a tracked file in a public repo (`tests/test_no_leaks.py:25`'s windows-drive-path pattern would flag `...` the moment IMPLEMENTATION_PLAN.md is committed with them). The stray `".path": "x"` key is a merge artifact.

**Proposed fix.** Deduplicate to one row per file, use repo-relative paths only (never `<drive>:/…` — the leak guard will fail the build), drop the malformed key, and collapse the triplicated narrative so `summary` is an abstract, `architecture_map` is §1, and `onboarding.what_it_is` is a short orientation paragraph.

## Meta-audit (did the merge converge faithfully?)

### BLOCKER (4)

#### [MERGE-01] `phases` is all three raw proposals concatenated, not the converged 14-phase plan

*reviewer:* meta-audit · *confidence:* high · *category:* completeness-dedup

**Location:** merged plan, `phases` array (36 objects tagged `[code-grounded]` / `[sequencing]` / `[domain-convention]`) vs `summary` §2 (Phase 0-13)

**Problem.** The narrative describes ONE plan: Phase 0 pre-register pivots, 1 toolchain, 2 spike, 3 spine, 4 snapshot, 5 teams, 6 names, 7 players, 8 contracts/bronze, 9 differential, 10 reports, 11 catalog, 12 docs, 13 USER-RUN. The `phases` field instead holds 11 + 13 + 12 = 36 phase objects under three incompatible numberings and three incompatible orderings — code-grounded runs the spike as Phase 1 with no `src/` code, sequencing runs toolchain as Phase 1 and the spike as Phase 2, domain-convention runs the spike as Phase 0. There are three different 'Phase 1' and three different 'Phase 5', prescribing different work. A cold agent reading the structured field rather than the prose has no executable plan; an agent reading both cannot tell which is authoritative.

**Proposed fix.** Replace `phases` with the 14 phases the narrative prescribes (Phase 0 through Phase 13), one object each, carrying that phase's goal / steps / acceptance / commit_note exactly as written in `summary` §2. Move the three raw proposals to a `reviews/plan-proposals.md` panel-trail artifact — the pattern PROJECT_SCOPE.md:767-772 already uses for `reviews/scope-proposals.md` — and reference it from the plan instead of inlining it.

#### [MERGE-02] `files_to_touch` names the same module twice under conflicting paths — the cold implementer builds both

*reviewer:* meta-audit · *confidence:* high · *category:* completeness-dedup

**Location:** merged plan, `files_to_touch` array vs `architecture_map` §1.2 target package shape

**Problem.** The three proposals' file lists were concatenated without reconciliation, so the same object appears under two names: `src/ootp_ai/parser/primitives.py` AND `src/ootp_ai/parser/cursor.py`; `src/ootp_ai/warehouse/load.py` AND `src/ootp_ai/warehouse/loader.py`; `src/ootp_ai/parser/rosters.py` AND `src/ootp_ai/parser/roster.py`; `src/ootp_ai/contracts/loader.py` + `contracts/policy.py` AND `src/ootp_ai/contracts/__init__.py` AND a bare `src/ootp_ai/contracts/` entry. Pure duplicates also survive: `pyproject.toml`, `.env.example`, `docs/data-access.md`, `docs/league-rules.md`, `gm/standing-orders.md`, `tests/test_no_leaks.py` and `requests/feature-requests/README.md` each appear twice with different change descriptions. §1.2's architecture map is the correct single answer and `files_to_touch` contradicts it. The implementation subagent's spec is built from declared target paths (`.claude/agents/data-engineer.md:143-144`); handing it this list yields two cursors and two loaders, or an Escalation.

**Proposed fix.** Rewrite `files_to_touch` as one deduped list keyed to §1.2. Canonical: `parser/primitives.py`, `parser/header.py`, `parser/errors.py`, `parser/teams.py`, `parser/names.py`, `parser/players.py`, `parser/rosters.py`, `parser/saved_games.py`, `contracts/tables.toml`, `contracts/field_map.toml`, `contracts/loader.py`, `contracts/policy.py`, `warehouse/sql.py`, `warehouse/ddl.py`, `warehouse/load.py`, `warehouse/ingest_run.py`, `validate/export_diff.py`, `reports/__main__.py|roster.py|standings.py`, `catalog/__main__.py|generate.py`. One entry per path, each with an explicit `(builder)` or `(main thread)` owner tag.

#### [MERGE-03] Phase 6 (names) and Phase 7 (players) are mutually blocking — the merge crossed two proposals' orderings

*reviewer:* meta-audit · *confidence:* high · *category:* sequencing

**Location:** merged plan, Phase 6 steps 3/5/7 and acceptance; Phase 7 step 1 and step 6

**Problem.** Phase 6 step 3 says 'For each candidate u32 position the walk exposes, apply the mapping across all 18,072 probe players', and step 7 requires 'for every player in `OOTP-AI.lg` carrying a non-empty `historical_id`'. Both need `parser/players.py` — which merged Phase 7 step 1 creates ('`player_id`, ... the name indices, and `historical_id`'). Phase 6's acceptance demands AC7 and AC8 green, so the phase cannot close. Symmetrically Phase 7 step 6 requires 'zero roster rows carry a null or blank display name' (AC9), which needs Phase 6's resolver. This is a merge artifact: code-grounded ordered players (its P5) BEFORE names (its P6) precisely so the brute-force method had records to search; sequencing and domain-convention ordered names first and never specified that method. The merge took the ordering from two planners and the method from the third.

**Proposed fix.** Either (a) restore code-grounded's ordering — players walk first (minimal field set + `historical_id` + raw name indices, no display names), then the names.dat table and the join, moving AC9's display-name clause into the names phase; or (b) split Phase 6 into 6a `names.dat` table walk + strict byte accounting (no join, no player dependency) and 6b the join + AC7/AC8, placing 6b AFTER the players walk. Either way restate §4 Risk 20's 'do not merge phases 5-7' in terms of the corrected dependency graph, because as written it forbids the obvious repair.

#### [MERGE-04] `decisions`, `conventions`, `convergence_map` and `gated_decisions` are all empty — no audit trail, and none of the eight binding calls recorded

*reviewer:* meta-audit · *confidence:* high · *category:* completeness-dedup

**Location:** merged plan: `decisions: []`, `conventions: []`, `convergence_map: []`, `gated_decisions: []`

**Problem.** The narrative makes at least eight decisions a cold implementer is bound by and cannot re-derive: (1) PyMySQL + types-PyMySQL as the first runtime dependency; (2) `save_id` = the save directory stem, `VARCHAR(64) NOT NULL`, validated `^[A-Za-z0-9_-]+$`; (3) contracts as TOML read via `tomllib`, shipped in-package; (4) `ingest_run` keyed `(snapshot_date, save_id)` with a loud refusal on re-land, resolving the AC10 collision; (5) a NOT NULL `name_space` discriminator on `bronze_name`; (6) snapshot-partitioned report output paths; (7) every PK column NOT NULL because MySQL's `COUNT(DISTINCT a,b,c)` drops NULL tuples; (8) AC15's byte-identity clause moved offline. None appears in `decisions`. `convergence_map` empty means there is no record of which planner contributed what or what was dropped — exactly what this audit had to reconstruct by hand. `gated_decisions` empty is misleading when §5 carries ten live operator questions, three of which block Phase 1.

**Proposed fix.** Populate `decisions` with the eight above, each with the alternative rejected and why. Populate `gated_decisions` with §5's ten questions, each tagged with the phase it blocks (driver → Phase 1; `save_id` → before Phase 8's DDL; output root → Phase 10; catalog location → Phase 11; AC15 split → Phase 11). Populate `convergence_map` with what each proposal uniquely contributed and what was deliberately dropped.

### MAJOR (7)

#### [MERGE-05] COST-UNREALISM: the read-only proof is a 6 GB double-hash over 30,668 files, prescribed at eight checkpoints as 'the cost of seconds'

*reviewer:* meta-audit · *confidence:* high · *category:* cost-unrealism

**Location:** merged plan §3.5 ('Checking both at every checkpoint costs seconds'); Phase 4 step 6; Phase 5 commit note ('every phase re-runs `test_read_only.py`')

**Problem.** Phase 4 step 6 specifies 'a manifest of size + `mtime_ns` + SHA-256 over every file under `$OOTP_SAVED_GAMES` and `$OOTP_INSTALL`', taken before AND after the run. Measured from the live `.env` on this machine: `$OOTP_INSTALL` = 19,243 files / 3,751.9 MB; `$OOTP_SAVED_GAMES` = 11,425 files / 2,315.6 MB. That is 30,668 files and 6.07 GB hashed twice per invocation — ~12 GB of reads and ~61k file opens on Windows — and §3.5 prescribes it at every phase from 5 through 12, eight times. 'Costs seconds' is measurably false. An implementer who takes it at face value builds the expensive version, discovers the cost, and quietly weakens the guard for ADR 0001 — the one unrecoverable failure in the project. No proposal measured this; all three inherited AC11's wording uncritically.

**Proposed fix.** Split the manifest by cost. Cheap tier: `size` + `mtime_ns` over both full trees — that alone satisfies AC11's 'modification time ... different from the pre-run manifest' clause and runs in seconds. Expensive tier: SHA-256 restricted to the files the pipeline actually opens (the three in-scope `.dat` files per save, plus `challenge.dat`, `saved_games.dat`, `players.csv`) plus a random sample of the rest. Run the full-tree digest pass ONCE in Phase 4 and once at Phase 12's final gate, not at all eight checkpoints; per-phase re-runs use the cheap tier. Record the measured wall clock into the ingest-run row and replace 'costs seconds' in §3.5 with the number.

#### [MERGE-06] `testing` is three test plans concatenated, and its per-phase selector table uses a phase numbering the plan does not have

*reviewer:* meta-audit · *confidence:* high · *category:* completeness-dedup

**Location:** merged plan, `testing` field — three sections beginning 'THE SHAPE OF THE SUITE', 'VERIFICATION MODEL' and 'THE CI CONDITION IS THE DESIGN CONSTRAINT'; the P1..P13 selector table inside the second

**Problem.** The `testing` field is code-grounded's, then sequencing's, then domain-convention's testing section, verbatim and unreconciled: three overlapping offline-vs-gamedata splits, three restatements of the Tier A/B/C model, three restatements of the anti-vacuity rules. Worse, the per-phase selector table (`P1 test_config.py`, `P2 test_doc_corrections.py`, ... `P13 full suite`) is keyed to SEQUENCING's 13-phase numbering, not the merged narrative's Phase 0-13. Merged Phase 2 is the scouted-view spike; the table says P2 runs `tests/test_doc_corrections.py`, a module no merged phase creates. An implementer running the selector table per phase runs the wrong tests.

**Proposed fix.** Collapse `testing` to one section — keep the first section's suite split, the second's four-guards-must-be-seen-to-fail drill and regression-safety rule, and the third's four-validation-chains framing, each stated once. Re-key the selector table to Phase 0-13 so every line is copy-pasteable and matches that phase's acceptance list, and either delete the `test_doc_corrections.py` row or restore the module to a phase (see MERGE-08).

#### [MERGE-07] AC15 is modified from `-m gamedata` to offline and baked into three phase artifacts while simultaneously being an open operator question

*reviewer:* meta-audit · *confidence:* high · *category:* scope-creep

**Location:** merged plan §1.3(e) 'Recommended strengthening', §3.1 offline list, Phase 11 step 7 and acceptance, vs §5 Open Question 5; scope PROJECT_SCOPE.md:295-304 (AC15 is `uv run pytest -m gamedata tests/test_catalog.py`)

**Problem.** The decided scope marks AC15 entirely `-m gamedata`. The merge recommends splitting the byte-identity clause offline — defensible, and it IS surfaced as Open Question 5 — but then writes it in as settled: §3.1 lists the offline half of `test_catalog.py` in the CI-enforced suite, and Phase 11's acceptance reads '`uv run pytest tests/test_catalog.py -m "not gamedata"` green OFFLINE'. A plan cannot both prescribe and question the same change. Concrete failure: stage 4's acceptance panel checks the SCOPE's AC15, finds a criterion whose invocation no longer matches, and either flags a false failure or silently accepts a substitution. This is the one place the merge modifies a decided acceptance criterion.

**Proposed fix.** Pick one posture and write it once. Recommended: satisfy AC15 exactly as worded — one `-m gamedata` module that includes the byte-identity assertion — and ADD an offline `test_catalog_structure.py` carrying the same assertion as a strictly additional CI guard. That strengthens CI without editing a decided criterion, removes Open Question 5 from the blocking set, and leaves the stage-4 panel checking the criterion it was handed.

#### [MERGE-08] Dropped: sequencing's committed offline regression guard for AC19, leaving an orphan file reference behind

*reviewer:* meta-audit · *confidence:* medium · *category:* completeness-dedup

**Location:** merged plan Phase 12 acceptance (`grep -rn 'leagues.dat' docs/`) vs sequencing proposal Phase 2 step 5 (`tests/test_doc_corrections.py`); module still named in merged `files_to_touch` and in the `testing` selector table

**Problem.** Sequencing proposed a committed offline test asserting the string `leagues.dat` appears nowhere under `docs/` except on a line carrying an explicit correction marker, with a deliberately narrow exemption mechanism. The merge replaced it with a one-off manual `grep` in Phase 12's acceptance and gave no reason. AC19 permits 'a grep' so the merge is compliant — but scope Goal 9 is explicitly 'leave behind mechanical enforcement rather than prose', and a grep run once at Phase 12 does not stop a later doc edit from reintroducing the claim. The drop is also incomplete: `tests/test_doc_corrections.py` still appears in `files_to_touch` and in the `testing` selectors, so the plan simultaneously does and does not create it.

**Proposed fix.** Restore `tests/test_doc_corrections.py` as a main-thread offline module in Phase 12 (or Phase 0, per MERGE-09), asserting the correction survives, with the exemption scoped to a single marked line rather than a whole-file allowlist. If the drop was deliberate, say so and remove the module from `files_to_touch` and the selector table so no orphan reference remains.

#### [MERGE-09] AC19 needs no parser, no save and no MySQL, but the merge defers it to Phase 12 — past the phase it names as the early-ship point

*reviewer:* meta-audit · *confidence:* medium · *category:* sequencing

**Location:** merged plan Phase 12 step 2 vs Phase 10 commit note ('the natural early-ship point if the slice needs to stop'); sequencing proposal Phase 2 landed the same correction second

**Problem.** The `leagues.dat` correction (AC19) is a pure documentation edit whose evidence — `major_league_ml_c_2024.lsdl` at byte 5,559,751 of `world.dat` — the merge already records in Phase 0 step 3. It is deliverable on day one. Sequencing landed it as its Phase 2, arguing exactly that: 'the guaranteed doc correction that needs no parser at all'. The merge consolidated all doc work into Phase 12 of 14 while Phase 10's commit note explicitly invites stopping early: 'Phases 11-13 add the catalog and the doc sweep, but the GM can already see its club'. If the slice stops where the plan says it may, AC19 — one of only two criteria closeable in the first hour — is unmet, and `docs/league-rules.md:129` and `:295` keep asserting a file that does not exist.

**Proposed fix.** Move the AC19 correction to Phase 0, alongside the `world.dat` measurement it depends on. `docs/league-rules.md` is NOT in the data-engineer deny set (`.claude/agents/data-engineer.md:150-157` lists only `docs/data-access.md` and `docs/decisions/`), so the main thread can edit it directly without waiting for the Phase 12 `/update-docs` batch. Leave the `docs/data-access.md` label upgrades in Phase 12, where they genuinely depend on Tier A/B results.

#### [MERGE-10] `risks` holds ~46 entries covering ~20 distinct risks — the narrative's dedup and cost ordering were not carried into the structured field

*reviewer:* meta-audit · *confidence:* high · *category:* completeness-dedup

**Location:** merged plan, `risks` array vs `summary` §4 ('Ordered by expected cost, not by likelihood', 20 items)

**Problem.** §4 of the narrative is a clean, deduped, cost-ordered list of 20 risks. The `risks` array is the three proposals' lists concatenated: names.dat-is-per-save appears three times ('names.dat CONTENT IS PER-SAVE...', 'PROBE-DERIVED NAME INDICES DO NOT TRANSFER...', '`names.dat` CONTENT IS PER-SAVE AND A PROBE-DERIVED INDEX DOES NOT TRANSFER'); the collation trap three times; `tests/` in the deny set three times; mypy-strict-over-tests three times; ruff `A`/`DTZ`/`PTH` three times; the doc-link guard three times; the leak-guard staging gap three times; SD-21 three times; 'nobody has run any of this code' three times. Beyond bloat, duplication destroys the cost ordering §4 established and makes it impossible to tell whether an item is a distinct risk or the same one restated — the exact judgment a reader uses a risk list to make.

**Proposed fix.** Replace `risks` with §4's 20 deduped items in their existing cost order, each with its mitigation and the phase that owns it. Where three proposals stated the same risk with different evidence, keep the strongest single statement — e.g. for the per-save names table, keep domain-convention's structural framing ('the resolver's cache key must include `save_id`, enforced by a test') over the data-coincidence smoke test, which the narrative already identifies as the weaker guard.

#### [MERGE-11] Contradictory ownership of the two spike artifacts: 'main thread only' in the phase, '(builder)' in files_to_touch

*reviewer:* meta-audit · *confidence:* high · *category:* ownership

**Location:** merged plan Phase 0 commit note ('Main thread only, no code') and Phase 2 step 4, vs `files_to_touch` entries for `requests/feature-requests/first-sight/reviews/spike-pivot-rule.md` and `spike-scouted-view.md`, both marked 'NEW (builder)'

**Problem.** The §0 ownership split is the plan's most load-bearing operational rule — §4 Risk 7 says handing a phase spec across the boundary costs a whole phase. But the two spike artifacts are assigned to opposite owners in two places. Both sit inside `requests/<track>-requests/<slug>/reviews/`, which IS the subagent's allowlisted handoff directory (`.claude/agents/data-engineer.md:143`), so either owner is legal — which is precisely why the ambiguity will not surface as an error. It surfaces as the artifact being written twice, or not at all, or as the spike being run by an agent whose return contract (`:206-224`) forces an eight-section 120-line format the plan's acceptance does not anticipate.

**Proposed fix.** Assign both spike artifacts to the main thread and say so identically in Phase 0, Phase 2 and `files_to_touch`. The spike reads `ootp_truth_real` and a probe save through a throwaway script under `var/`; nothing about it needs the builder, and keeping it main-thread avoids the handoff-format collision. If the builder is preferred instead, state that its return must be the `<!-- handoff: v1 -->` eight-section file and that the verdict document is a separate artifact the main thread writes from it.

### MINOR (7)

#### [MERGE-12] The same ruff rule is cited at two different line numbers, one of which is wrong

*reviewer:* meta-audit · *confidence:* high · *category:* citation-accuracy

**Location:** merged plan Phase 1 'Watch out' (`A` at `pyproject.toml:55`) vs `risks` item 9 and `code_references` (`A` at `pyproject.toml:53`); actual file pyproject.toml:55

**Problem.** `pyproject.toml:53` is `"UP",  # pyupgrade`; `A` (builtin shadowing) is at `:55`. The merge inherited the correct `:55` from one proposal's phase text and the incorrect `:53` from code-grounded's `code_references`, and kept both. The plan's own framing states that a cold implementer trusts citations literally, so a wrong one is worse than none. The same fields also restate `A`/`DTZ`/`PTH`/`N` three times with drifting ranges (`:52-60`, `:53`, `:55`, `:56-59`).

**Proposed fix.** Fix to `pyproject.toml:55` everywhere and state the ruff rule locations once: `N` at `:52`, `UP` at `:53`, `B` at `:54`, `A` at `:55`, `C4` at `:56`, `DTZ` at `:57`, `PTH` at `:58`. Then dedup `code_references` generally — `data-engineer.md`'s fixed-offset ban, `docs/data-access.md`'s header layout, `.gitignore:31`, `pyproject.toml:78` and `docs/league-rules.md:129` each appear three times with slightly different ranges.

#### [MERGE-13] `onboarding.files_to_read` is triplicated and carries a malformed entry copied verbatim from a proposal

*reviewer:* meta-audit · *confidence:* high · *category:* completeness-dedup

**Location:** merged plan, `onboarding.files_to_read` (39 entries, ~14 distinct); the `.github/workflows/ci.yml` entry carries a stray `".path": "x"` key alongside its real `path`

**Problem.** The onboarding list is the three proposals' lists concatenated. `PROJECT_SCOPE.md`, `.claude/agents/data-engineer.md`, `docs/data-access.md`, `pyproject.toml`, `tests/test_no_leaks.py`, `tests/fixtures/README.md`, `docs/league-rules.md`, `gm/standing-orders.md`, `.claude/agents/gm.md`, `.gitignore`, `.github/workflows/ci.yml` and `requests/feature-requests/README.md` each appear two or three times with different `why` text and different cited ranges. Paths are inconsistently absolute (`...`) and repo-relative for the same file — and CLAUDE.md bans machine-specific paths in tracked files, so the absolute form cannot be committed as-is. One entry additionally carries a junk `".path": "x"` key inherited unchanged from the domain-convention proposal, which is direct evidence the field was concatenated rather than merged.

**Proposed fix.** Deduplicate to ~14 entries, one per file, merging the three `why` texts into the single strongest set of load-bearing line citations. Make every path repo-relative. Delete the `".path": "x"` key.

#### [MERGE-14] The full ~30 KB plan document is stored three times in the merged output

*reviewer:* meta-audit · *confidence:* high · *category:* completeness-dedup

**Location:** merged plan: `summary`, `architecture_map`, and `onboarding.what_it_is` are byte-identical copies of the same document

**Problem.** Three identical copies of the whole plan. Beyond size, this is a correctness hazard the moment anyone edits it: a fix applied to `summary` leaves two stale copies that read as authoritative, and nothing flags the divergence. `architecture_map` in particular should be the §1 architecture section, not the entire document including phases, risks and open questions.

**Proposed fix.** `summary` keeps the full document. `architecture_map` carries only §0-§1 (how to read this plan, current state, target package shape, the five seams, the two path decisions). `onboarding.what_it_is` carries a short orientation paragraph — what this plan is, what the upstream artifact decided, and where the phases live — not a third copy.

#### [MERGE-15] COST-UNREALISM (small): 'Snapshot-partitioning dissolves SD-21 at zero cost' — the plan's own Risk 18 concedes it does not

*reviewer:* meta-audit · *confidence:* high · *category:* cost-unrealism

**Location:** merged plan §1.4 ('dissolves SD-21 / Risk 10 ... at zero cost') and Phase 10 step 1, vs §4 Risk 18 ('note the residual: the tracked catalog's pointer names the *pattern*, not a dated path')

**Problem.** Snapshot-partitioned output paths are a cheap and correct fix for SD-21, but not free. They force Core §15's tracked report-path pointer to name a template rather than a resolvable path — weakening exactly what that pointer exists for (making AC20 reproducible by someone who was not in the room) — and they add a dated-directory resolution step to AC14's git-ignored-root assertion. The plan says 'zero cost' twice and then contradicts itself in Risk 18. An implementer who reads §1.4 and not §4 will not budget for the pointer problem.

**Proposed fix.** Change 'at zero cost' to 'cheaply, with one residual' in §1.4 and Phase 10, cross-referencing Risk 18 inline. Then close the residual: have the catalog generator emit BOTH the path pattern (tracked half) and the most recent resolved path (generated, ignored half, where a concrete path is permitted), so the umpires' spawn instruction points at a real file.

#### [MERGE-16] COST-UNREALISM (small): 'reuse the existing PATTERNS rather than inventing a second set' does not cover the new git-ignored-root assertion

*reviewer:* meta-audit · *confidence:* high · *category:* cost-unrealism

**Location:** merged plan Phase 10 step 6; tests/test_no_leaks.py:24-28 (PATTERNS) and :31-48 (`tracked_text_files()` shells out to `git ls-files` only)

**Problem.** Phase 10 frames the leak-guard work as an extension that reuses what is there. Half of it is: the 'never absolute paths in the tracked catalog' clause is genuinely covered by the existing windows-drive and unix-home regexes at `:25-26`. The other half is not. 'Assert the report and catalog output roots resolve to git-ignored paths' requires a `git check-ignore -q` subprocess helper plus config resolution, neither of which exists in that module — `tracked_text_files()` at `:31-48` shells out to `git ls-files` and nothing else. Calling the whole item a reuse understates it and invites an implementer to skip the machinery.

**Proposed fix.** Split Phase 10 step 6 into two named assertions: (a) absolute-path scan over the tracked catalog and field map — reuses `PATTERNS` verbatim, genuinely cheap; (b) output-root-is-ignored — a new `git check-ignore` helper plus a config import into the test module, and note that this makes `test_no_leaks.py` depend on `src/ootp_ai/config.py` for the first time, a coupling worth stating explicitly.

#### [MERGE-17] Phase 8 is oversized against the plan's own 'independently revertible units' argument

*reviewer:* meta-audit · *confidence:* medium · *category:* sequencing

**Location:** merged plan Phase 8 (8 steps, 4 test modules) vs §4 Risk 20 ('Three checkpoints cost three commits and buy three independently revertible units')

**Problem.** Risk 20 argues forcefully against merging phases 5-7 because each is separately provable. Phase 8 violates the same principle in the other direction: it lands `tables.toml` + `field_map.toml` + the DDL emitter + the bronze loader + `ingest_run` + `bronze_field_label` + `dump_parse` + `test_grain_contracts.py` (both halves) + `test_withheld_fields.py` + the completion of `test_snapshot_semantics.py` + a deliberate key-mutation drill — and it is the first phase requiring a running MySQL, so a failure anywhere in it is not separable from the schema change. Its own commit note concedes 'local and CI signal diverge permanently from here'.

**Proposed fix.** Split into 8a (contracts declaration + DDL emitter + the OFFLINE grain and withheld-field tests — no MySQL, fully CI-provable, fully revertible) and 8b (loader + `ingest_run` + `bronze_field_label` + `dump_parse` + the `-m gamedata` grain and snapshot-semantics tests). 8a is the cheapest possible checkpoint at which to catch a wrong grain — the argument the sequencing proposal made for its own Phase 8, whose sentence the merge kept without the split.

#### [MERGE-18] AC18's ordering risk is flagged but carries no fallback if the operator reads it strictly

*reviewer:* meta-audit · *confidence:* medium · *category:* sequencing

**Location:** merged plan §5 Open Question 2; Phase 1 (creates `src/ootp_ai/config.py`, `db.py`, `warehouse/sql.py`) sitting between Phase 0's pivot rule and Phase 2's verdict

**Problem.** AC18 requires the spike verdict 'committed *before any ratings code exists*'. The merge reads that as 'no ratings code', notes this slice contains none, and puts config/deps/DB before the spike — defensible, and correctly surfaced. But code-grounded's ordering had ZERO files under `src/ootp_ai/` before the verdict, and its Phase 1 acceptance asserted it (`git ls-files src/ootp_ai` still lists only `__init__.py`). The merge keeps that assertion in Phase 0 and then invalidates it in Phase 1. Open Question 2 asks the operator to confirm but gives no instruction for the strict-reading branch, so a cold agent that gets a strict answer is stuck.

**Proposed fix.** Add the fallback inline: if the operator reads AC18 strictly, run the spike as a hardcoded throwaway script under `var/` (untracked, so Core §2's resolve-by-name rule is not violated in any tracked artifact) BEFORE Phase 1, and record the verdict from it. That is a one-paragraph branch and it removes the question from the blocking set.

### QUESTION ()

#### [MERGE-20] The tracked-catalog location is recommended in two places and questioned in a third, with no phase assigned to settle it

*reviewer:* meta-audit · *confidence:* medium · *category:* gated-decision

**Location:** merged plan §1.3(e) and Phase 11 step 2 (recommend `docs/warehouse-catalog.md` + `.json`), Phase 11 commit note ('Raise the tracked-catalog location with the operator here if it was not settled earlier'), §5 Open Question 4

**Problem.** Three references, three postures: a recommendation, a conditional 'raise it here if not settled earlier', and an open question. Nothing says WHEN it gets settled or who raises it, so 'if it was not settled earlier' can be true at Phase 11 with nobody having asked. The follow-on — whether the new tracked doc joins `tests/test_repo_structure.py`'s required-docs list — is a main-thread test edit that also has no owner. CLAUDE.md forbids creating directories speculatively, so a top-level `catalog/` genuinely needs the operator's argument, which makes this a real gate rather than a preference.

**Proposed fix.** Move the decision into §5's must-settle-before-Phase-1 set alongside `save_id` and the driver, since Phase 8's field-map declaration and Phase 11's generator both depend on it, and answer the required-docs-list question in the same breath. Then delete the conditional phrasing from Phase 11's commit note so no branch of the plan depends on whether someone remembered to ask.

### NIT ()

#### [MERGE-19] Open Question 9 raises `bronze_name`'s per-snapshot storage cost but gives the implementer no arithmetic

*reviewer:* meta-audit · *confidence:* medium · *category:* cost-unrealism

**Location:** merged plan §5 Open Question 9; Phase 8 step 1 (`bronze_name` keyed `snapshot_date, save_id, name_space, name_index`)

**Problem.** The question flags that `bronze_name` re-lands ~264,095 rows per save per snapshot even though `names.dat` is fixed-size and probably immutable for a save's lifetime, and says it is 'flagging the storage number, not re-litigating the decision' — but it never states the number. With two saves landed for validation that is ~528k rows on the first snapshot alone, and it is also the single largest contributor to the AC17 extraction-cost figure the plan asks to be recorded without a threshold. An implementer sizing the load has to compute it themselves and will likely be surprised by where the wall-clock number comes from.

**Proposed fix.** State the arithmetic: ~264,095 rows per save per snapshot, ~528k across the probe and the managed league on the first landing, growing linearly per sim date. Note explicitly that this dominates the AC17 number, and that Phase 8's ingest-run row already records the per-snapshot `names.dat` digest, so a later slice can prove immutability and de-snapshot it without re-parsing.

## Code references submitted for grounding (104)

- `src/ootp_ai/__init__.py:7` — The entire package today is a docstring plus `__version__ = "0.1.0"`. Every module this plan names is created from nothing — there is no existing parser, config layer, loader, renderer or catalog to hook into.
- `pyproject.toml:9` — `dependencies = []` — no runtime dependency has been chosen. SD-14's blocker is real: a MySQL driver and a .env loader must both be selected, with type stubs, before any code compiles clean under strict mypy.
- `pyproject.toml:11-15` — A tracked comment states 'The first real dependency will arrive with the warehouse loader.' Phase 2 makes that sentence describe the past, so the comment must be updated in the same commit.
- `pyproject.toml:23` — `python-dotenv>=1.0` currently sits in the `dev` dependency group. The config layer imports it at runtime, so it must move into `[project] dependencies` or a non-dev install breaks.
- `pyproject.toml:57` — ruff selects `DTZ` with the comment 'naive datetimes — every timestamp here is tz-aware or it is a bug'. Every wall-clock stamp in the ingest-run row must use `datetime.now(UTC)` or lint fails.
- `pyproject.toml:53` — ruff selects `A` (builtin shadowing). A record walker naturally reaches for `id`, `bytes`, `list`, `type` and `format` as local names; all of them are lint errors here.
- `pyproject.toml:69-73` — mypy runs `strict = true` over BOTH `src` and `tests`. Every new test function needs a `-> None` annotation, matching the existing guards, and every third-party import needs stubs.
- `pyproject.toml:78-81` — `addopts = "-q --strict-markers --strict-config"` with exactly one declared marker, `gamedata: requires a local OOTP install or save.` An undeclared second marker is a hard collection error, which is why the scope widens this declaration rather than adding one.
- `.github/workflows/ci.yml:37-49` — CI runs exactly ruff check, ruff format --check, mypy, and `pytest -m "not gamedata"`. This is the definition of 'offline' for acceptance criteria 1-5, 13 and 16.
- `.claude/agents/data-engineer.md:69` — 'Never seek to a fixed offset... Code that seeks is a blocker, not a style note.' Acceptance criterion 3 turns this line into an AST scan over src/ootp_ai/parser/.
- `.claude/agents/data-engineer.md:89` — 'never a literal path, never a `parents[N]` walk. (Test modules are the one established exception...)'. This is why config.py cannot resolve the repo root from `__file__` to build the documented `var/snapshots` default.
- `.claude/agents/data-engineer.md:91` — 'Never require a game install to satisfy a test.' The offline/gamedata split in this plan's testing section is this rule applied file by file.
- `.claude/agents/data-engineer.md:98` — 'Bronze is 1:1 with the parser output. Typing, casing, deduplication. No joins, no business logic, no filtering, no semantic renaming.' This is why the Boston org filter lives in the report layer, not in load.py.
- `.claude/agents/data-engineer.md:101` — 'Silver declares its grain and proves it... and the two must agree.' Acceptance criterion 4 enforces exactly this at bronze, by comparing the prose grain sentence in tables.toml against the key the DDL emitter produces.
- `.claude/agents/data-engineer.md:150` — `tests/` is the first line of the repo-level deny set, above `.github/`, `ops/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md`, `docs/decisions/`. Handing a spec with test targets to the subagent produces an Escalation and zero tests.
- `.claude/agents/data-engineer.md:157` — '<anything under the OOTP install or saved-games directory>' is in the deny set, cross-referenced to 'The game is read-only'. No code path may open a save for writing.
- `.claude/agents/data-engineer.md:206-224` — The return contract: one Markdown file in requests/<track>-requests/<slug>/reviews/, first line exactly `<!-- handoff: v1 -->`, eight named sections, at or under 120 lines, no diff hunks. The spike verdict and the build handoff both land here.
- `.claude/agents/data-engineer.md:239-247` — Data facts never go in agent memory — they travel as `## docs-delta` with a proposed epistemic label and the main thread routes them through /update-docs. This is the only legal path for the phase-11 docs/data-access.md corrections.
- `docs/data-access.md:172-181` — The byte-exact header: offset 0 u8 0x00, offset 1 char[4] "OOTP", offset 5 u32 25, then u32 11, 104, 84, 1, then the null-padded filename at offset 25. Acceptance criterion 1 is a direct transcription of this block.
- `docs/data-access.md:183-186` — 'A reader that checks `data[0:4] == b"OOTP"` sees `\x00OOT` and rejects a valid save; one that reads the version as a u32 at offset 4 gets 6480 rather than 25.' Criterion 1's offset-0 rejection case comes from here.
- `docs/data-access.md:193-201` — The primitives table: string = u32-LE length prefix + raw ASCII with no terminator; date = u8 day, u8 month, u16 year; color = u32 ARGB; money = u32 whole dollars. These are the four readers Cursor must expose.
- `docs/data-access.md:204-215` — Records contain variable-length regions, `verified` by the same player's ratings block sitting at different distances from both a leading and a trailing anchor in two saves — but field ORDER is stable across saves, which is what makes a sequential walk transfer.
- `docs/data-access.md:224-226` — `verified` — teams.dat carries a 5-string signature (city, abbreviation, nickname, logo filename, full name) followed by u32 ARGB colors, and all 30 MLB clubs extract cleanly. This is the only verified teams.dat knowledge; :228 marks everything else `unconfirmed`, which is why strict byte accounting on that file is a risk rather than a given.
- `docs/data-access.md:234-238` — Player names are indices into a ~264,095-entry names.dat table, and `unconfirmed` — 'The index encoding and the names.dat table layout. Resolving names requires a two-file join that has not been built.' This is the largest single unknown on the critical path of the headline report.
- `docs/data-access.md:282` — `unconfirmed` — 'Which file holds which view, and whether the scouted view is stored at all.' The project-threatening unknown that phase 1's spike answers before any parser code exists.
- `docs/data-access.md:292-295` — The spike's method, written and never run: export real and scouted ratings together, then search scouting.dat for the exported scouted values. Found -> stored and the parser has its source; absent everywhere -> computed, and there is a design problem before any rating can be served.
- `docs/data-access.md:60-63` — `measured` — 'a `*.lg` glob is not a list of saves.' The saved-games directory contains a stray, empty directory literally named `.lg`. The enumerator must confirm players.dat and teams.dat are present.
- `docs/data-access.md:65-68` — `measured` — challenge.dat is present at exactly 241 bytes in a Challenge Mode save and absent otherwise. A cheap filesystem-level mode check with no menu involved, promoted to a per-run pre-flight.
- `docs/data-access.md:36-38` — `verified` — 'saved_games.dat is the index: plaintext league name, team name, league date, and the absolute path of each save. Readable without parsing.' The scope's finding F19 contradicts this at `high` confidence, so the label is downgraded in phase 11 and the file is read through the header reader instead.
- `docs/data-access.md:79-80` — players.csv is ~12,855 rows, comma-separated, with a `//`-prefixed header line — the Tier A parser must strip that prefix or the first column name is wrong.
- `docs/data-access.md:99-102` — `verified` — the Lahman/BBRef ID is embedded in players.dat itself as a length-prefixed string (e.g. `deverra01`), ~1,712 unique values, each appearing twice per file. This is `historical_id`, a nullable attribute and never a join key in any serving path.
- `docs/data-access.md:336` — The export was configured with 'Replace accents' OFF specifically because it 'mangles names and breaks validation against names.dat'. That care is undone if the comparison runs under an accent-insensitive collation.
- `ops/mysql-bootstrap.sql:23-24` — `CREATE DATABASE IF NOT EXISTS ootp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci` — accent-insensitive AND case-insensitive. An 'exact string equality' comparison performed in SQL under this collation is not exact, which is SD-13's unresolved collation decision sitting on disk as a wrong default.
- `ops/mysql-bootstrap.sql:32-33` — `CREATE DATABASE IF NOT EXISTS ootp_truth_osa` plus its grant at :49 — the schema Decisions 10 retires, because ootp_truth_real already carries both scouting perspectives from one export.
- `tests/test_no_leaks.py:106-107` — `banned_names = {"players.csv", "names.xml", "world_default.xml", "schools.xml"}` and `banned_suffixes = {".dat", ".lg"}` applied to every tracked path. This is why no fixture may be named *.dat — and why a RENAMED copy of players.csv would sail straight through, which is the hard bind on the names fallback.
- `tests/test_no_leaks.py:31-48` — `tracked_text_files()` enumerates via `git ls-files`, so the guard cannot see a new file until it is staged. A leak in an untracked rendered artifact passes locally and only fails in CI — the feedback-loop gap the scope files as a follow-up.
- `tests/test_no_leaks.py:24-28` — The three leak PATTERNS (windows drive path, unix home path, email). The new rendered-game-data guard reuses these rather than inventing a second set, so a tracked catalog carrying an absolute path trips the existing regex.
- `tests/test_doc_links.py:22-37` — Every `[..](..)` in every tracked .md is resolved against the filesystem, with no exemption for fenced code blocks and none for `var/` targets. A tracked Markdown link into the ignored output root turns CI red, which is why the catalog's report pointer is a code span.
- `tests/test_repo_structure.py:64-67` — `test_var_is_gitignored` asserts a bare `var/` line in .gitignore. Combined with .gitignore:18 this is what makes acceptance criterion 14's `git check-ignore -q` assertion hold for the report output root.
- `tests/test_agent_contract.py:46-66` — `test_rulebook_invariants_survive` pins ten invariant strings in the data-engineer definition, including 'fixed offset', 'players.csv', 'unconfirmed' and 'immutable'. Any edit to that file during this feature must keep all ten present.
- `tests/fixtures/README.md:45-51` — 'A real save's day-0 state is the LEAST informative test input available: every variable-length region is at its minimum, so a parser that seeks to a fixed offset passes cleanly and fails later in production.' This is the argument for synthetic byte builders over any captured bytes.
- `.gitignore:18` — A bare `var/` rule makes the whole scratch root ignored — the basis for criterion 14's git-ignored-output-root proof.
- `.gitignore:62` — `!tests/fixtures/**` re-includes the fixtures directory after the `*.dat` ignore at :31. So a fixture named *.dat WOULD be trackable by git and would then be caught by test_no_leaks.py:107 — the guard is the backstop, not gitignore.
- `.env.example:25` — 'MUST be on local disk, not a cloud-synced folder — snapshots are ~600MB each. Defaults to var/snapshots.' The documented default the config layer must produce without a parents[N] walk.
- `.env.example:57-58` — MYSQL_TRUTH_REAL_DATABASE and MYSQL_TRUTH_OSA_DATABASE. The second is retired by Decisions 10; the first is the Tier B validator every differential test reads.
- `docs/league-rules.md:129` — 'The parser reads `leagues.dat` directly and may recover some of these.' Grep-confirmed at this exact line — one of the two false assertions acceptance criterion 19 removes.
- `docs/league-rules.md:295` — 'Until the parser can open `leagues.dat`, every value here is believed rather than confirmed for our league.' Grep-confirmed at this exact line (the scope's citation is correct; adversary finding SD-27's proposed correction to :296 is wrong).
- `docs/league-rules.md:26` — §1 is described as 'Temporary. Every value is a column on the leagues row; the warehouse supersedes this the moment the parser lands.' This slice lands the parser without landing the league config, so the sentence becomes partially false on delivery — the doc gate must catch it.
- `docs/league-rules.md:79-81` — `schedule_file_1 = major_league_ml_c_2024.lsdl` — the exact string the scope measured at byte 5,559,751 of OOTP-AI.lg/world.dat, which is what located the league configuration block outside teams.dat.
- `gm/standing-orders.md:42-50` — The per-report format block (Established / Owner / Policy / Rationale / Review trigger). Decisions 4 requires extending it with an engineering-owned kind, because gm/staff.md:5-8 records that no staff exist and naming an owner would be fiction.
- `gm/README.md:19` — The placement rule: 'Can this be rebuilt from the save? Yes -> var/. No -> here.' This is what routes the rendered reports into the ignored root while the DECISION that they exist stays tracked in standing-orders.
- `.claude/agents/gm.md:4` — `tools: Read, Glob` — the entire delivery surface for this feature. The GM cannot query, cannot run a command, and cannot open a .dat; a Markdown file handed into its context is the only channel.
- `.claude/agents/gm.md:32` — Forced-read item 8: 'Any report or analysis handed to you for this invocation.' Acceptance criterion 20 is a spawn that exercises exactly this line.
- `docs/decisions/0012-scouted-ratings-only.md:75-76` — 'The corollary for the parser: an unclassified rating field is not "probably fine." Under this ADR it is withheld until classified.' This is the rule policy.py::is_renderable() encodes.
- `docs/decisions/0005-hybrid-data-layer.md:66-71` — The boundary rule verbatim, and the worked example that players.csv resolves as STATIC REFERENCE — 'its day-0 snapshot role is a use, not its nature'. This is what keeps this feature off the datasets/ side and out of build/.
- `docs/decisions/0004-mysql-warehouse.md:94-106` — The four live adapter options and 'The decision comes due when the first dbt model is requested.' Decisions 9 defers rather than resolves, and records the deferral as a note here rather than as a superseding ADR.
- `requests/feature-requests/README.md:70-85` — 'Testable' means a cold agent runs one command and gets a pass or fail; criteria only a human can prove must be marked user-run 'so the acceptance panel doesn't claim them'. Criteria 20 and 21 are those.
- `requests/feature-requests/README.md:119` — The Index row for first-sight currently reads `scoped`. /commit Step 4 advances it to `plan` when the IMPLEMENTATION_PLAN lands and to `implemented` at the end of stage 4.
- `requests/feature-requests/first-sight/PROJECT_SCOPE.md:5-9` — The citation convention this feature's artifacts must follow: code spans, not Markdown links, wherever a citation carries a file:line suffix or points into var/ — because both forms fail tests/test_doc_links.py today, a live defect with an open bugfix request.
- `.claude/skills/create-implementation-plan/SKILL.md:251` — The skill's 'What good looks like' section cites `tests/test_request_links.py` as 'a blocking CI check'. That file does not exist in this repo — the only link guard is tests/test_doc_links.py. Do not plan around a check that isn't there.
- `pyproject.toml:78` — `addopts = "-q --strict-markers --strict-config"` — an undeclared marker is a hard COLLECTION error, not a failure, which is why the marker widening is sequenced first.
- `pyproject.toml:80` — The single declared marker reads 'requires a local OOTP install or save' and says nothing about a database. Phase 1 widens it to 'install, save, or warehouse' rather than adding a second marker.
- `.github/workflows/ci.yml:49` — CI runs `uv run pytest -m "not gamedata"`, so the offline suite is the only regression protection on future PRs — every phase carries an offline assertion, not only a gamedata one.
- `.claude/agents/data-engineer.md:69-72` — The fixed-offset ban with its evidence (the same player's ratings block at 43 bytes from one anchor and 107 in another). Phase 3 encodes it mechanically as `tests/test_no_fixed_offsets.py` and structurally as a Cursor with no seek.
- `.claude/agents/data-engineer.md:91-92` — 'Never require a game install to satisfy a test' — the reason phases 5 and 7 add synthetic-buffer tests alongside their real-save tests rather than relying on `-m gamedata` alone.
- `.claude/agents/data-engineer.md:156` — `docs/data-access.md` is deny-set for WRITES (reads are free), so every parser finding travels as a `## docs-delta` routed through `/update-docs` in phase 13 rather than being edited in place.
- `tests/test_agent_contract.py:69-75` — `test_deny_set_still_protects_the_guards` asserts `tests/`, `.github/`, `ops/`, `CLAUDE.md` and `docs/decisions/` stay in the deny set — the mechanical backstop behind this plan's authorship split.
- `tests/test_no_leaks.py:97-116` — `test_game_data_is_not_tracked` bans four filenames and the `.dat`/`.lg` suffixes. It is the only thing catching a `.dat` fixture (see the .gitignore note) and it catches `players.csv` by FILENAME ONLY — a renamed derived copy sails through, which is why Decisions §5 hard-binds against tracking a Lahman-to-name lookup.
- `.gitignore:31` — `*.dat` is ignored — but `.gitignore:62`'s later `!tests/fixtures/**` negation re-includes it, so git would track `tests/fixtures/foo.dat` happily. Phase 3's fixtures therefore take a non-`.dat` extension.
- `tests/test_doc_links.py:15` — `markdown_files()` skips `var` when ENUMERATING files, but `test_relative_links_resolve` still resolves link TARGETS — so a tracked Markdown link into the ignored output root turns CI red. The catalog's report pointer is text, never a link (SD-11).
- `docs/data-access.md:14` — '`unconfirmed` — Nobody has looked. An unconfirmed claim is a task, not a fact.' This is the rule that forces phase 2 (the scouted-view spike) and phase 6 (the names encoding) to precede anything that builds on them.
- `docs/data-access.md:172-189` — The header layout: leading `0x00`, magic at offset 1 (not 0), u32 version 25 at offset 5, self-naming filename at offset 25. All four of AC1's assertions come straight from this block.
- `docs/data-access.md:238` — '`unconfirmed` — The index encoding and the `names.dat` table layout.' The largest single unknown in the request, and the reason phase 6 is placed before the players walk with a pre-registered fallback.
- `docs/data-access.md:282-295` — The critical-path question — whether the scouted view is stored at all — and the exact test that has never been run. Phase 2 runs it with the pivot rule committed first, satisfying AC18.
- `docs/league-rules.md:80` — Records `schedule_file_1 = major_league_ml_c_2024.lsdl` — exactly the string the scope located at byte 5,559,751 of `world.dat`, which is the corrected location phase 2 records.
- `.env.example:22-25` — `OOTP_SNAPSHOT_ROOT` is documented as defaulting to `var/snapshots` and warned against cloud-synced storage. Verified against the live `.env`: it is EMPTY, so phase 1 must define and validate the default rather than assume a value.
- `ops/mysql-bootstrap.sql:35-38` — Schemas are `utf8mb4_0900_ai_ci` — accent- and case-INSENSITIVE. Phase 6's exact-string name comparison must state its collation explicitly (SD-13) or its '100% exact' claim is weaker than it reads.
- `gm/standing-orders.md:10-11` — 'Status: none active' — the line that changes when phase 13 lands the first two report entries; useful as a one-line check that the tracked half of the report channel actually shipped.
- `tests/fixtures/README.md:32-37` — Names exactly the fixtures phase 3 needs — 'a length-prefixed string at a buffer boundary, a 1-year contract next to a 10-year one, a header carrying an unrecognized version byte' — so the fixture set is prescribed, not invented.
- `docs/decisions/0012-scouted-ratings-only.md:57-59` — 'A field we cannot classify must be treated as true-rating and withheld' — the ADR text phase 8's `tests/test_withheld_fields.py` enforces by declared CATEGORY rather than by column-name glob.
- `requests/README.md:20-32` — Explains why a wrong `u16` produces a plausible number with every test green and no stack trace — the failure class phases 5-10's ground-truth harness exists to catch, and the reason phase 10 must be green before phase 11 renders anything.
- `.claude/agents/data-engineer.md:101-104` — Grain must be declared in prose AND enforced with a uniqueness test, and the two must agree. AC4 tests exactly that agreement between the tracked declaration and the emitted DDL.
- `.claude/agents/data-engineer.md:111-112` — "Structural absence is not missing data." The basis for the parser-level rule that a field absent from a record becomes None/NULL while a present zero stays 0, and for the export-diff allowlist covering the 14 non-MLB league rows the export writes 0 into.
- `.claude/agents/data-engineer.md:150-157` — The hard deny set: tests/, .github/, ops/, .claude/, CLAUDE.md, docs/data-access.md, docs/decisions/. Combined with :164-166 ("stop and report it — do not build it"), this forces the plan's subagent/main-thread split; handing the whole spec over yields an Escalation and zero tests.
- `.claude/agents/data-engineer.md:130` — "Anything outward-facing is user-run. Stage it as a script and report it under still-open. Never run it yourself." Governs AC20, AC21 and the ledger append in Phase 11.
- `.claude/agents/data-engineer.md:238-249` — The Routing rule: data facts never go in agent memory; they travel as `## docs-delta` with a proposed epistemic label and the main thread routes them through /update-docs. This is the mechanism Phase 10 depends on.
- `docs/data-access.md:173-186` — The header layout byte-for-byte (0x00, "OOTP" at offset 1, u32 25 at offset 5, then 11/104/84/1, then the null-padded filename) and the explicit warning that a reader checking data[0:4] rejects every valid save. AC1 tests both directions.
- `docs/data-access.md:188` — "the header names its own file" — the cheap cross-check that the file on disk is the file we think we opened. Folded-in #6 promotes this to a pre-flight on every run.
- `docs/data-access.md:280-295` — The critical-path question (is the scouted view stored at all) and the exact spike test at :292-295 — export real and scouted together, then search scouting.dat for the exported scouted values. Phase 0 runs precisely this.
- `docs/data-access.md:335` — The export was configured with `Replace accents` OFF because it "mangles names and breaks validation against names.dat". Accented names are therefore present, which is what makes MySQL's default accent-insensitive collation a silent-pass hazard for the names join.
- `pyproject.toml:73` — `files = ["src", "tests"]` under `strict = true` — mypy runs strict over the tests too, which is why the driver's type stubs are a Phase 1 blocker rather than a nicety (Risk SD-14).
- `pyproject.toml:52-60` — ruff already selects A (builtin shadowing), DTZ (naive datetimes), PTH (pathlib) and N (naming). These bite a binary parser specifically: no `id`/`type`/`bytes` names, `datetime.date` for the sim date, `time.perf_counter()` for the extraction-cost timing.
- `.gitignore:61` — `!datasets/**` is already present as a carve-out for a directory that does not exist. The scope's Non-Goals forbid creating datasets/ or a manifest entry here, so leave this rule untouched.
- `tests/test_doc_links.py:10-15` — One regex over every Markdown link, skipping only http/mailto/#/angle-brackets, and markdown_files() excludes files UNDER var/ but not links TO var/. Confirms the live defect: the report-path pointer must use code spans, not links.
- `.github/workflows/ci.yml:38-49` — The four gates each phase must pass locally before /commit: `ruff check .`, `ruff format --check .`, `mypy`, and `pytest -m "not gamedata"`. CI has no game install and no MySQL by design (ADR 0006).
- `gm/README.md:17-19` — The placement rule — "Can this be rebuilt from the save? Yes -> var/. No -> here." The rendered reports rebuild from the save (var/); the DECISION that the report exists does not (tracked).
- `gm/README.md:63-79` — The ledger.jsonl row schema (seq, sim_date, period, what, staff, proposed, reasoning, precedent, ruling, overridden, overturns) that the Phase 11 umpire append must match.
- `docs/league-rules.md:129-130` — "The parser reads `leagues.dat` directly and may recover some of these" — false; OOTP-AI.lg holds 18 .dat files and none is leagues.dat. AC19's first correction target.
- `docs/league-rules.md:295-296` — "Until the parser can open `leagues.dat`, every value here is believed rather than confirmed" — AC19's second correction target. The league config block is measured at byte 5,559,751 of world.dat instead.
- `docs/decisions/0004-mysql-warehouse.md:89-106` — "This is not yet resolved and does not need to be… The decision comes due when the first dbt model is requested," with four live options and options 3/4 called likely correct. Decisions §9 requires the deferral recorded as a note here rather than a superseding ADR.
- `docs/decisions/0005-hybrid-data-layer.md:64-71` — The boundary rule verbatim — does this artifact change when the league is simulated? No -> builder + datasets/. Yes -> parser + dbt — and the worked example that players.csv resolves as static reference. This is what keeps this feature entirely off the datasets/ side.
- `tests/test_repo_structure.py:12-24` — The required-docs list every phase must keep satisfied, and the shape any new tracked doc joins. Together with :64-67 (var/ must stay gitignored) and :94-103 (the GM contract files), it is part of AC16's regression set.
- `tests/fixtures/README.md:8-9` — "A fixture may contain our own derived observations. It may never contain OOTP's shipped data." With :26-28 stating plainly that the leak guard cannot catch a renamed real slice — that one is on the implementer.
- `requests/bugfix-requests/_done/doc-link-guard-mismatch/BUGFIX_REQUEST.md:20-25` — The reproduction showing test_doc_links.py flagging a fenced link, a file.py:123 citation, and a var/ target as broken. Confirms the plan's artifacts must use code spans and must not link into the output root.
