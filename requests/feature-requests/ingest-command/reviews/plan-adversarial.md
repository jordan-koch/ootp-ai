# Plan panel — adversarial + meta-audit findings, and the convergence map

Panel health: 3/3 planners, 2/2 adversaries, 1/1 meta-audit, 43 findings (4 blocker, 13 major). Degraded lenses: none.

Verbatim. Lines naming a file a later stage creates, or quoting link syntax generically, are
fenced so `tests/test_doc_links.py` exempts them; the text is unchanged.

## Convergence map

### AC1's literal `from tests.test_read_only import WRITERS` does not resolve in this repo; the working form is a bare top-level import.

**Planners:** code-grounded, sequencing, domain-convention

All three lenses reached it independently, and I verified every leg: no `conftest.py` anywhere in the tree, no `tests/__init__.py`, `tests/fixtures/__init__.py:4` records that pytest's prepend mode puts `tests/` on `sys.path`, and every existing cross-test import uses the bare form (`tests/test_leak_guard_scope.py:34`, `tests/test_doc_link_contract.py:23`, `tests/test_guard_probe_isolation.py:58`). A cold agent copying the scope's spelling literally gets a collection error on the very first offline test — the cheapest possible failure to prevent and the easiest to trip.

### The naive composition (`take_snapshot` + `parse_snapshot` + `land_snapshot`) does NOT surface ADR 0021's refusal — it silently lands a full duplicate.

**Planners:** code-grounded, sequencing, domain-convention

This is the specific failure the whole re-run-default decision exists to avoid, and it is invisible: `snapshot.py:189-201` auto-allocates and never raises, so the obvious implementation ships a README claiming a protection the code does not provide, at a cost of 52.4 MiB and ~301,000 rows per accidental re-run with no retention policy to reclaim either. Three independent lenses naming it means the pre-flight's placement before `take_snapshot` is not a detail to be optimised away.

### The shared function must have NO `ingest_seq` parameter — the sequence decision belongs only to whoever calls `land_snapshot`.

**Planners:** code-grounded, sequencing, domain-convention

The failure mode is displaced and therefore very hard to diagnose: if the CLI's explicit-sequence policy travels into the shared function, `landed_probe` starts colliding at seq 1 (`tests/fixtures/warehouse.py:19-26`) and the symptom appears as `IngestRunExists` in unrelated grain-contract tests. AC17's sub-clause was written for exactly this, and three lenses converged on the structural fix rather than a comment.

### `latest_ingest_seq` / `landed_max_seq` must be a plain SELECT, deliberately NOT `next_ingest_seq`.

**Planners:** code-grounded, sequencing, domain-convention

`ingest_run.py:140-143` requires `next_ingest_seq` be called inside the inserting transaction, and :16-35 records that this repo already got that function's locking semantics wrong once — measured twice, at 0.000 s, with the primary key doing the actual work. CLAUDE.md carries the same correction as a standing 'do not re-derive this'. A cold agent reusing the existing helper for a display read would reproduce the exact belief the codebase spent a measurement disproving.

### The nine refusal exceptions share no base class, so the tuple must be explicit and parametrised.

**Planners:** code-grounded, sequencing, domain-convention

Verified across five modules: `snapshot.py:100,113` and `ingest.py:148,220` and `ingest_run.py:91` and `parser/errors.py:25` derive from `Exception`; `load.py:142,146` derive from `RuntimeError`. A tuple that misses one turns an operator-facing refusal into a traceback, which is the exact failure the scope's Goal 8 is written against.

### `IngestRunExists` and `ConcurrentLandingError` must produce DISTINCT messages.

**Planners:** code-grounded, sequencing, domain-convention

`load.py:146-154` names the failure in the codebase's own words: an operator told 'already landed' for a contention loss goes looking for a landing that never happened. A single `except (…, …)` handler with one message is tidier code and passes a naive test — which is precisely why AC5 asserts distinctness and why three lenses flagged it.

### The allocator drift is real and one instance is live on the truth save.

**Planners:** code-grounded, sequencing, domain-convention

All three insisted the query be re-run rather than trusted, and I re-ran it: two pairs in step, `Test-Save-Standard-Mode` 2024-03-18 with a filesystem seq-1 directory and no warehouse row. The scope explicitly hands the reconciliation choice to the plan, so this is the one place the plan makes a decision the scope did not — and it is grounded in a measurement rather than a hypothetical.

### Compose `take_snapshot + parse_snapshot`, never `ingest_save`.

**Planners:** code-grounded, sequencing, domain-convention

`ingest.py:488-492` measures `_describe(..., payload=None)` at '~48 MB of avoidable I/O per ingest'. Using `ingest_save` would push that cost into a timing harness (`tests/test_extraction_cost.py`, `DRIFT_FACTOR = 10.0`) and into the most expensive test in the repo. The convergence also yields a bonus nobody expected: the AC11 legs get CHEAPER by ~48 MB each, because they currently DO use `ingest_save` at :254/:263/:268.

### AC11 must not get more expensive, and no MySQL dependency may enter its bracket.

**Planners:** code-grounded, sequencing, domain-convention

`tests/test_read_only.py:240-242` refuses it in terms, and :25-28 measures the cost at 2m35s over 30,703 files. This is the one test the project cannot afford to lose, and the pre-flight's warehouse lookup is the natural thing to put inside the shared function — so the constraint has to be structural (the lookup stays outside; `previous=None` at both test call sites means zero digest work) rather than a comment.

### Every test file is authored on the main thread, because `tests/` is in the builder's deny set.

**Planners:** code-grounded, sequencing, domain-convention

Verified at `.claude/agents/data-engineer.md:154,157` ('the guards that catch you') with the stop-and-report obligation at :171. Roughly half of core lands in `tests/`, so a plan that silently hands the whole change to a spawned builder stalls at the first test file — and the builder's own contract requires it to refuse rather than build.

### Per-table `table_digest` values stay out of `--json`.

**Planners:** code-grounded, sequencing, domain-convention

`load.py:540-547` reads every column of every row for the triple ordered by the declared key — ~301,000 rows for one landing, 264,095 of them `bronze_name` — which is a second full read of everything the landing just wrote, on the operator's most frequent command. The scope already defers it; three lenses independently re-deriving the cost means nobody should fold it back in as a 'cheap win'.

### A docstring can red the write guard, and both new modules' docstrings are exactly the place it would happen.

**Planners:** code-grounded, domain-convention

`_writes_in` (`tests/test_read_only.py:348-358`) strips `#` comments but NOT docstrings, and `test_the_pipeline_contains_no_destructive_filesystem_call` (:375-386) behaves the same for `.unlink(` and `.rename(`. The hazard is live precisely because the honest thing to write in those docstrings — 'this module never calls `.mkdir(`' — is the thing that fails the build. Two lenses caught it; naming the safe phrasing ('creates no directory of its own') is what makes it actionable.

### `.claude/agents/data-engineer-memory.md:202` is the single live line-numbered reference to the moved file, and historical `requests/**/reviews/` handoffs must NOT be rewritten.

**Planners:** sequencing, domain-convention

```text
Verified: it is the only `ingest.py` path reference outside the reviews trail, no markdown link targets the file, and `tests/test_doc_links.py` chases only `[text](target)` links and bare `requests/…` tokens — so CI would not catch a stale path, which is exactly why it has to be found by grep BEFORE the move. The third planner argued for appending rather than correcting on the file's own :41 append-only rule; I checked, and :41 governs pruning, not fixing a path that no longer resolves, so the scope's instruction stands.
```

### `--from-snapshot` reuses `dump_parse`'s existing `read_manifest` → `parse_snapshot` composition and needs no new parsing code.

**Planners:** code-grounded, sequencing, domain-convention

`ingest.py:300` is literally `_serialize(parse_snapshot(read_manifest(path)))`. Three lenses finding the same one-line precedent means the correction workflow ADR 0021:57-59 names costs almost nothing to ship, which is why the scope promoted it into v1.

## Reviewer summaries

### `code-grounded` (adversary)

I read the decided PROJECT_SCOPE in full, then verified every code reference the merged plan cites — all ~70 in `code_references` plus the ones embedded in onboarding, architecture_map, phases, files_to_touch and conventions — against the actual repo.

**The plan's grounding is unusually good.** I could not find a single fabricated path, missing symbol, or invented reuse. Spot-verified and confirmed exact: `ingest.py` is 502 lines with an 11-name `__all__` at :50-62; `snapshot.py`'s `_read_sim_date` (:285) has precisely one caller (:185); `ensure_tables` (load.py:169) has precisely one caller in the whole repo (`tests/fixtures/warehouse.py:93`); `verify_snapshot` (:254) has zero `src/` callers; `ops/mysql-bootstrap.sql` really does create three databases (:23,:30,:42), one user (:54), three grants (:57,:58,:63) and no tables in 65 lines; `tests/test_bronze_landing.py` really does not import `landed_probe`; there is no `conftest.py` anywhere and no `tests/__init__.py`, so the plan's correction of AC1's dotted import spelling to the bare house form (`tests/test_leak_guard_scope.py:34`, `test_doc_link_contract.py:23`, `test_guard_probe_isolation.py:58`) is right; `contracts/tables.toml` holds exactly eight `[[table]]` entries; the AC11 leg count (four with `OOTP_TRUTH_LEAGUE`, three without) is right; `_writes_in` (:348-358) really does strip only `#` comments, so the docstring hazard is real; and the plan's correction of the scope's own `:187` to `tests/test_read_only.py:186` for the stale "46 MB" comment is correct. The four measurements are internally consistent to the byte and I reproduced the snapshot total independently: 54,939,056 B across `var/snapshots/OOTP-AI/2024-03-07/1`.

**What I found is concentrated in the seams the plan invents rather than the code it cites.** Four majors: (1) `SaveReading.parsed: ParsedSnapshot | None` reds mypy strict at both prescribed call sites; (2) the size-only pre-flight pass has no representable value under `SnapshotFile`'s mandatory `sha256`, whose naive resolution makes the refusal silently never fire — the plan's own Risk #1; (3) AC6 carries three mutually contradictory monkeypatch prescriptions, one of which raises `AttributeError` against the import style the plan mandates two phases earlier; (4) the `max(fs, warehouse+1)` reconciliation breaks the path-equals-triple invariant `snapshot.py:16-19` states outright, and the plan treats that as a display concern. Then five minors and three nits, including one ordering instruction that is a hard `ruff` RUF022 failure (RUF022 confirmed non-preview on the pinned ruff 0.16.3) and one citation whose `unconfirmed` label turns out to be about `text_data.sqlite3` rather than the save files.

### `executability` (adversary)

I read the decided PROJECT_SCOPE in full, then followed its "Affected Area & Pointers" table and verified every line citation the merged plan makes against the real files: `src/ootp_ai/{snapshot,ingest,config,saves}.py`, `reports/__main__.py`, `reports/resolve.py`, `catalog/__main__.py`, `warehouse/{load,ingest_run}.py`, `tests/{test_read_only,test_bronze_landing,test_no_leaks,test_extraction_cost}.py`, `tests/fixtures/{warehouse,__init__}.py`, `pyproject.toml`, `ops/mysql-bootstrap.sql`, `README.md`, `.claude/agents/data-engineer{,-memory}.md` and `docs/data-access.md`.

The plan's factual grounding is unusually good. Essentially every line number checks out (`ingest.py` is 502 lines with `__all__` at :50-62 and eleven names; `WRITERS` is at :303-317; `_writes_in` at :348-358; `next_ingest_seq` at :137-153 with the FOR-UPDATE contract at :140-143; `ensure_tables` at :169-189 with exactly one caller at `tests/fixtures/warehouse.py:93`; `table_digest` at :540-572; the bootstrap's CREATEs at :23/:30/:42/:54 and grants at :57/:58/:63 with no table anywhere). I independently confirmed the three claims the plan leans hardest on: there is no `conftest.py` anywhere and no `tests/__init__.py`, so the bare cross-test import spelling is right and AC1's dotted form would not resolve; there are exactly ten `from ootp_ai.ingest import` sites; and `test_bronze_landing.py` does NOT import `landed_probe` (the four real consumers are `test_extraction_cost`, `test_grain_contracts`, `test_parser_vs_export`, `test_snapshot_semantics`), so AC17's correction of the scoping panel stands.

The conventions are baked in properly: read-only game, no fixed-offset work, resolve-by-name target lookup, no new `.env` key, no `[project.scripts]`, `/commit`-gated per-phase checkpoints, read-only git for subagents, and the explicit rule that every test file is authored on the main thread because `tests/` sits in the builder's deny set (`.claude/agents/data-engineer.md:157`, stop-and-report at :171).

Where it breaks down is executability, and the damage is concentrated in three places. **AC6 — the criterion the scope's adversaries specifically rewrote away from a source scan — is internally contradictory**: Phase 2 mandates module-attribute call sites, Phase 4 tells the implementer to patch an attribute that then does not exist, and the risks entry asserts the exact inverse of Python's import semantics. As written the test either errors or passes vacuously, recreating the failure mode `tree-seam-for-remaining-guards` exists for. **`SaveReading.parsed` is declared Optional for no stated reason** and fails mypy strict at all three call sites, so Phase 2 cannot reach its own gate. **Phase 4's acceptance requires the `land()` body that Phase 4's steps defer to Phase 5** — a straight phase-depends-on-later-work inversion. Below those: `reason_to_land` has one signature for two incompatible call modes; every gamedata gate can go green by skipping with no anti-vacuous rule at the checkpoint; the offline `Settings` recipe (existing directories, `tests/test_config.py:24-36`) is never stated; `--json`'s `verdict` can never emit `"unchanged"` because that path raises; and AC10/AC12 drive `main()` while the mandated cleanup needs the `IngestRun` only `land()` returns. The Phase 1 byte-exactness command is not a byte comparison and its `>` redirect adds a BOM. Sixteen findings, three blockers.

### `meta-audit` (meta_audit)

I audited the merge, not the repo, and re-ran what the merge claims to have measured. The convergence is unusually strong on facts: every citation I spot-checked held (load.py:142/146, ensure_tables:169-189, test_parser_vs_export.py:130 `which="truth_save"`, test_cross_mode_format.py:119, test_read_only.py:186's "46 MB" comment, :303-317 WRITERS, _writes_in stripping only `#`, pyproject :52/:88/:93/:95/:100/:101, requests README:126, no conftest.py and no tests/__init__.py, test_bronze_landing.py NOT importing landed_probe, data-access.md:85 and :226-227, memory :41 vs :202). Two headline measurements reproduced EXACTLY on my own run: the landed snapshot is 54,939,056 bytes across five files plus manifest.json, and the live managed `players.dat` is 32,078,633 against 32,070,091 landed. All 19 acceptance criteria are mapped to a phase; none was dropped; the phase ordering (promotion alone, then the re-point alone, then CLI, then wiring) is a genuine improvement over all three proposals.

The failures cluster in three places. (1) COST-UNREALISM, and it is the merge's own decisive claim: "digest-before-copy wins by roughly three orders of magnitude" — I measured the digest at ~48 ms (matching their 42 ms) and the copy it supposedly beats at ~18 ms, three times warm. Digest is ~2.5x MORE expensive than the copy, not 1000x cheaper; the copy side was never measured, and Phase 7 instructs writing this comparison into a tracked IMPLEMENTATION_REPORT labelled `measured` in a repo whose central rule is per-claim epistemics. (2) DESIGN SUPERIMPOSITION rather than convergence: `SaveReading` folds code-grounded's return-a-verdict shape and domain-convention's raise-an-exception shape together, producing a `parsed: ParsedSnapshot | None` that can never be None, a `verdict="unchanged"` that can never be observed, and two re-pointed call sites that will fail `uv run mypy` strict at the Phase 2 gate. The same superimposition breaks AC6: the plan makes module-attribute calls "load-bearing" and then prescribes an `is`-identity assertion and a `__main__.read_save` patch that only work under the name-import style it forbids. (3) ONE DROPPED ADVERSARIAL QUESTION: the sequencing planner's M2 (the size fast path's real hit rate) was replaced by a single anecdote and declared settled — but 4 of the 5 SNAPSHOT_FILES are byte-size-identical between live and landed, and on the refusal path (the case the pre-flight exists for) all sizes match by definition, so the fast path can never fire there and every refusal pays the full 52.4 MB digest. Scope creep is small and mostly self-flagged; the `--json` field set is the one place four fields rode in past the scope's explicit "trimmed" list with only the fifth gated.

## Code-grounding & executability findings

### [BLOCKER] EXEC-01 — AC6's monkeypatch target does not exist under the call style the plan mandates, and the risks entry states the mechanics backwards

**Reviewer:** `executability` · **Confidence:** high · **Category:** executability-contradiction · **Location:** plan phases[1] (Phase 2, step 'The module-attribute call style') vs phases[3] acceptance 'AC6 (command half)' vs risks[8]

**Problem:** Phase 2 mandates that both callers import the MODULE (`from ootp_ai.ingest import read`) and call `read.read_save(...)`, and says that is 'load-bearing' for AC6. Under that style there is no `read_save` attribute on `ootp_ai.ingest.__main__` at all — only a `read` module reference — so Phase 4's acceptance instruction to 'monkeypatch `ootp_ai.ingest.__main__.read_save`' fails outright: `monkeypatch.setattr` raises `AttributeError` unless `raising=False`, and with `raising=False` it silently sets an attribute nothing reads, so the spy records zero calls and the test passes for the wrong reason. risks[8] then compounds it by asserting the exact inverse of Python's semantics: 'Patching only `ootp_ai.ingest.read.read_save` would record zero calls.' With module-attribute call sites, patching `ootp_ai.ingest.read.read_save` is precisely what records BOTH callers — it is the only patch point that works. AC6 is the criterion the scope's adversaries specifically rewrote away from a source-text scan (PROJECT_SCOPE.md:205-209) because that class of guard cannot fail; the plan has reintroduced a guard that cannot fail, by a different route. Phase 5's fixture half adds a third, incompatible technique ('monkeypatch `fixtures.warehouse.read` module attribute', i.e. replacing the module object).

**Proposed fix:** Pick one mechanism and state it once: both call sites do `from ootp_ai.ingest import read` and call `read.read_save(...)`; AC6 patches the single attribute `ootp_ai.ingest.read.read_save` with a wrapping recorder and asserts the recorder saw one call from `land(...)` and one from `landed_probe`. Delete the `ootp_ai.ingest.__main__.read_save` and `fixtures.warehouse.read` patch targets from Phase 4/5 acceptance, and rewrite risks[8] to say the opposite of what it currently says. Add a belt-and-braces `assert ootp_ai.ingest.__main__.read is ootp_ai.ingest.read` identity check so a future `from ... import read_save` refactor at either site reds the test instead of silencing it.

### [BLOCKER] EXEC-02 — `SaveReading.parsed: ParsedSnapshot | None` fails mypy strict at every one of its three call sites

**Reviewer:** `executability` · **Confidence:** high · **Category:** type-safety · **Location:** plan phases[1] step 1 (`SaveReading` field list) — against pyproject.toml:93,95 (`strict = true`, `files = ["src", "tests"]`)

**Problem:** The plan declares `SaveReading.parsed: ParsedSnapshot | None`, then has callers use it unguarded: `tests/fixtures/warehouse.py:151` becomes `parsed = read.read_save(...).parsed` followed by `_land(connection, parsed)` — but `land_snapshot` (src/ootp_ai/warehouse/load.py:195-201) takes `parsed: ParsedSnapshot`, so mypy strict rejects `ParsedSnapshot | None`. Phase 5's `land()` does `verify_snapshot(reading.parsed.run.snapshot.path)`, which mypy rejects as 'Item "None" of "ParsedSnapshot | None" has no attribute "run"'. Nothing in the plan ever explains why the field is optional: the only non-parsing outcome is `SaveUnchanged`, which RAISES rather than returns. mypy is a named gate at every phase boundary, so Phase 2 — the phase carrying the riskiest edit in the change — cannot reach its own checkpoint as written.

**Proposed fix:** Make it `parsed: ParsedSnapshot` (non-optional) and state in the docstring that the unchanged case raises `SaveUnchanged` rather than returning a reading with no parse, so the type carries the invariant. If a future no-parse mode is wanted, it belongs in a separate return type, not an Optional the three call sites all have to narrow. Same treatment for `filesystem_seq`/`snapshot_ingest_seq` on `LandingResult`: state which are `None` only on the `--from-snapshot` path and have the formatters narrow explicitly.

### [BLOCKER] EXEC-03 — Phase 4's acceptance criteria require `land()`'s body, which Phase 4's steps defer to Phase 5

**Reviewer:** `executability` · **Confidence:** high · **Category:** phase-ordering · **Location:** plan phases[3] (Phase 4 steps vs acceptance AC5/AC6/AC7) and phases[4] step 1 ('Wire `land()` in the fail-fast order')

**Problem:** Phase 4's steps specify only `land()`'s signature, `_parser()`, target resolution, `LandingResult`, the formatters and the exception tuple. Phase 5's first step is 'Wire `land()` in the fail-fast order: `connect_warehouse` -> `ensure_tables` -> `latest_landing` -> `read_save` -> ... -> `land_snapshot`'. But Phase 4's acceptance demands AC5 ('with `land_snapshot` monkeypatched to raise `IngestRunExists`, `main(["land"])` returns 1'), AC6 ('drive `land(...)` with `land_snapshot` stubbed, assert exactly one recorded `read_save` call') and AC7 ('a shared call log proves `ensure_tables` is called exactly once and at an index BEFORE `read_save`'). None of those can pass unless `land()` already calls `connect_warehouse`, `ensure_tables`, `read_save` and `land_snapshot` in order — i.e. unless Phase 5's work is already done. A cold agent executing Phase 4 as written hits a red suite at its own checkpoint with no instruction telling it to write the body.

**Proposed fix:** Redraw the boundary explicitly: Phase 4 writes the FULL `land()` skeleton — connect, `ensure_tables`, `read_save(previous=None)`, `land_snapshot(ingest_seq=None)`, print — which makes AC5/AC6/AC7 genuinely provable offline against stubs; Phase 5 then adds only the three things it names (the `latest_landing`/`PriorLanding` pre-flight, the `max(fs, warehouse+1)` reconciliation, and `verify_snapshot`), and owns AC10-AC14. Alternatively move AC5/AC6/AC7 into Phase 5's acceptance and reduce Phase 4 to AC2/AC3/AC4/AC9. Either is fine; leaving both phases claiming the same tests is not.

### [MAJOR] CG-01 — `SaveReading.parsed: ParsedSnapshot | None` reds `uv run mypy` at both prescribed call sites

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** correctness · **Location:** src/ootp_ai/warehouse/load.py:197

**Problem:** Phase 2 declares `SaveReading` with `parsed: ParsedSnapshot | None`, then prescribes two call expressions that consume it without narrowing: `tests/fixtures/warehouse.py:151` becomes `parsed = read.read_save(save, snapshot_root=Path(tmp)).parsed` followed by the existing `_land(connection, parsed)` at :152, and Phase 5's `land()` calls `verify_snapshot(reading.parsed.run.snapshot.path)`. `land_snapshot`'s second parameter is `parsed: ParsedSnapshot` (load.py:197), and mypy runs `strict = true` over `files = ["src", "tests"]` (pyproject.toml:93,95). Both lines are `Optional` errors — `Argument 2 to "land_snapshot" has incompatible type "ParsedSnapshot | None"` and `Item "None" of "ParsedSnapshot | None" has no attribute "run"`. Every phase gate in this plan requires `uv run mypy` green, so the cold implementer hits this in Phase 2 and again in Phase 5. The `| None` is also gratuitous by the plan's own design: `read_save` raises `SaveUnchanged` on the no-work path, so a successful return always carries a parse.

**Proposed fix:** Declare `SaveReading.parsed: ParsedSnapshot` (non-optional) and state in the plan that the unchanged case is signalled only by `SaveUnchanged`, never by a `None` payload. If a non-raising variant is ever wanted, it belongs on a separate return type, not on this one.

### [MAJOR] CG-02 — The size-only pre-pass has no representable value: `SnapshotFile.sha256` is a required `str`

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** correctness · **Location:** src/ootp_ai/snapshot.py:122

**Problem:** Phase 2 prescribes calling the pure `reason_to_land(previous, sim_date, current)` twice — first with sizes surveyed by `Path.stat()` and no digests, then (only if every size matches) with `snapshot.source_facts(save)`. But `PriorLanding.files` and the `current` argument are declared as `tuple[SnapshotFile, ...]`, and `SnapshotFile` (snapshot.py:122-127) is a frozen dataclass whose `sha256: str` is mandatory. There is no way to express "size known, digest not yet computed", and `reason_to_land`'s check (d) is "any sha256 mismatch". An implementer filling the digest with `""` on the first pass gets a spurious mismatch for every file, so `reason_to_land` always returns a reason, the digest branch is never reached, and the pre-flight never refuses — the exact silent failure the plan names as Risk #1 (a README claiming a protection the code does not provide). Nothing in the offline test set the plan specifies catches it; only AC12 (gamedata, probe) would, and only if run.

**Proposed fix:** Split the contract explicitly in the plan: give `reason_to_land` a `digests_known: bool` flag (or two functions — `reason_from_sizes(previous, sim_date, sizes)` and `reason_from_digests(previous, current)`) so the sha256 comparison is structurally unreachable on the size-only pass. Add an offline test asserting that identical sizes with `digests_known=False` returns `None` (i.e. escalates to digesting) rather than a reason.

### [MAJOR] CG-03 — AC6's three monkeypatch prescriptions contradict each other; one of them raises AttributeError

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** correctness · **Location:** tests/fixtures/warehouse.py:43

**Problem:** The plan gives four mutually inconsistent accounts of how AC6 observes the shared function. Phase 2 step 8 mandates module-attribute call style — `from ootp_ai.ingest import read` then `read.read_save(...)` at both call sites — and says "this is what lets AC6 observe both." Phase 4's AC6 then says "monkeypatch `ootp_ai.ingest.__main__.read_save`", which under that import style does not exist as a module attribute and raises `AttributeError` from `monkeypatch.setattr`. Phase 5's AC6 half says "monkeypatch `fixtures.warehouse.read` module attribute" — replacing the whole module object, a third technique. And risks[8] states the opposite of the Phase 2 rationale: "monkeypatching the source module does not rebind it… must patch the attribute on each importing module" — which is false for `read.read_save(...)`, where patching `ootp_ai.ingest.read.read_save` is seen by every caller. The `testing` section compounds it with "an `is`-identity assertion proving both modules reference the same object", but under module-attribute access neither module holds its own reference to compare.

**Proposed fix:** Pick one and state it everywhere: both callers do `from ootp_ai.ingest import read` and call `read.read_save(...)`; AC6 patches the single source attribute `ootp_ai.ingest.read.read_save` with a wrapping recorder and asserts one recorded call from `land(...)` and one from `landed_probe`. Delete the `__main__.read_save` and `fixtures.warehouse.read` variants, drop the `is`-identity clause, and correct risks[8] to say the module-attribute style is precisely what makes a single-site patch sufficient.

### [MAJOR] CG-04 — `max(fs_seq, warehouse_max + 1)` silently breaks the snapshot-path-equals-triple invariant `snapshot.py` states

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** design · **Location:** src/ootp_ai/snapshot.py:16

**Problem:** `snapshot.py:16-19` states the invariant in terms: "A snapshot directory is written once. The path is `<snapshot_root>/<save_id>/<sim_date>/<ingest_seq>/` — the same three components, in the same order, as every bronze primary key." The plan's reconciliation lands at `max(snapshot_dir_seq, landed_max_seq + 1)`, and in the two divergent cases it names (the live `Test-Save-Standard-Mode` drift, and the reachable `rm -rf var/` direction) the landed `ingest_seq` is NOT the directory's number — so the snapshot backing the landed triple sits at a path that triple does not address. The plan treats this purely as a display concern ("prints both numbers whenever they disagree"), and Decision 4 asserts "the two stores name the same attempt" only for the in-step pairs. But ADR 0021's snapshot-is-authoritative triage — the ground on which Phase 5 also folds in `verify_snapshot` — depends on being able to find the snapshot from the landed triple. A stdout line the operator did not save does not preserve that.

**Proposed fix:** State the consequence explicitly in the plan and choose deliberately: either (a) accept it, and require the divergent case to also record the snapshot directory's own number in `ingest_run.source_files`-adjacent output AND in the `--json` payload (not stdout prose alone), or (b) take the snapshot at the reconciled sequence — compute `landed_max_seq` before `read_save` and pass `ingest_seq=seq` into `take_snapshot`, accepting `SnapshotExists` as a loud refusal — so the path and the triple can never diverge. Either way the invariant at snapshot.py:16-19 must be named and its status settled, not left implied.

### [MAJOR] EXEC-04 — `reason_to_land` is specified to be called in two modes but given one signature that always requires a sha256

**Reviewer:** `executability` · **Confidence:** high · **Category:** under-specification · **Location:** plan phases[1] steps 2-3 (Phase 2, `read_save` body and `reason_to_land` check order)

**Problem:** Step 2 has `read_save` call `reason_to_land` twice: first with a size-only survey ('survey the five `SNAPSHOT_FILES` with `Path.stat()` for sizes only and call `reason_to_land`'), then, only if every size matches, again with `snapshot.source_facts(save)`. But `current` is typed as `SnapshotFile`s, and `SnapshotFile` (src/ootp_ai/snapshot.py:121-127) has a mandatory `sha256: str`. On the size-only pass the digests do not exist, so the caller must invent placeholders — at which point check (d) ('any sha256 mismatch') fires on every save and the function returns a spurious 'changed' reason, defeating the whole two-stage design. The plan's own unit tests assume both behaviours coexist ('one size changed -> a reason naming the file, again with no digest performed' AND 'equal sizes with one sha256 changed -> a reason'), which the single signature cannot deliver.

**Proposed fix:** Give the pure function an explicit mode: either `reason_to_land(previous, sim_date, current, *, compare_digests: bool)` where `compare_digests=False` skips check (d), or a dedicated `SourceFacts` type whose `sha256` is `str | None` with the contract that `None` means 'not computed, do not compare'. State which of (a)-(d) each mode evaluates, and keep the five unit tests but parametrise them over the mode so the size-only path is proved to return `None` on equal sizes.

### [MAJOR] EXEC-05 — Every gamedata phase gate can report green by skipping, and the plan gives the checkpoint no anti-vacuous rule

**Reviewer:** `executability` · **Confidence:** high · **Category:** verification-strength · **Location:** plan phases[1]/[4]/[5] acceptance (`uv run pytest -m gamedata ...` green) — against tests/test_read_only.py:189-193 and tests/fixtures/warehouse.py:59-96

**Problem:** `_settings()` (tests/test_read_only.py:189-192) calls `pytest.skip` on `ConfigError`, and AC11's own test skips when `settings.probe_save is None` (:245-250); `warehouse_or_skip` skips when MySQL is unreachable (tests/fixtures/warehouse.py:88-91); `save_or_skip` skips per missing save. pytest reports a fully-skipped `-m gamedata` run as green with exit 0. So an implementer without `.env`, the probe save, or a running MySQL can satisfy the literal wording of Phase 2's 'green', Phase 5's 'green' and Phase 6's 'green' while having proved nothing about the single riskiest edit in the change (the `landed_probe`/AC11 re-point, which couples four gamedata modules to one new function). The plan's Phase 2 does ask for a wall-clock comparison against the 2m35s baseline, which implicitly requires a real run, but never says the gate is void on a skip.

**Proposed fix:** Add one line to the per-phase cadence in `testing`: every gamedata gate must be run with `-rs` and the phase handoff must record the collected/passed/skipped counts, and a gate with zero passed gamedata tests is NOT a checkpoint — the phase stops and the run is handed to the operator. State the environment prerequisites once, up front: `.env` with `OOTP_PROBE_LEAGUE` set, the probe save on disk, and a reachable MySQL with the `ootp_dev` schema from ops/mysql-bootstrap.sql. Phases 2, 5 and 6 cannot be completed on a CI-shaped machine, and the plan should say so rather than letting an agent discover it as a green run.

### [MAJOR] EXEC-06 — The offline `Settings` prerequisite is unstated: `load_settings(mapping)` refuses unless OOTP_INSTALL and OOTP_SAVED_GAMES name existing directories

**Reviewer:** `executability` · **Confidence:** high · **Category:** missing-prerequisite · **Location:** plan phases[3] acceptance AC3/AC5 ('with `Settings` built through `load_settings(mapping)` (`config.py:111`)') — against src/ootp_ai/config.py:115-116,169-173 and tests/test_config.py:24-36

**Problem:** The plan cites `load_settings(env)` as 'the mapping injection point every offline test uses' but never states its precondition: `_required_directory` (src/ootp_ai/config.py:169-173) raises `ConfigError` unless both `OOTP_INSTALL` and `OOTP_SAVED_GAMES` resolve to directories that EXIST on disk, and `load_settings` additionally shells out to `git check-ignore` via `_check_never_tracked` (:241-269) for an output root inside the worktree. A cold agent writing AC3/AC5 with a plain dict of strings gets a `ConfigError` and no guidance. The repo already has the exact helper — `tests/test_config.py:24-36`'s `_env(tmp_path, **overrides)`, which mkdirs `tmp_path/install` and `tmp_path/saves` and supplies the five required keys — and the plan's `files_to_read` never names `tests/test_config.py` at all.

**Proposed fix:** Add `tests/test_config.py:24-36` to `files_to_read` with the note that `_env(tmp_path)` is the established offline-Settings recipe, and add a Phase 4 step: 'Build offline Settings from a `tmp_path`-backed mapping in the shape of `tests/test_config.py:_env`, adding `OOTP_TRUTH_LEAGUE`/`OOTP_PROBE_LEAGUE` for the multi-save resolution cases and omitting both for the fresh-clone case AC3 requires.'

### [MAJOR] EXEC-07 — The `--json` `verdict` field can never emit the value the downstream consumer needs

**Reviewer:** `executability` · **Confidence:** high · **Category:** design-inconsistency · **Location:** plan decisions[8] and gated_decisions[4] (`verdict` = `no-prior`/`changed`/`unchanged`) vs phases[1] step 2 (`a None return raises SaveUnchanged`)

**Problem:** The plan folds a three-valued `verdict` into `--json` on the argument that it gives `incremental-loading` 'exactly the discriminator that a distinct exit code 3 was dropped for'. But the `unchanged` case raises `SaveUnchanged`, which Phase 4's exception tuple maps to a stderr line and exit 1 — at which point no JSON is printed at all (Phase 4: 'Under `--json` the human block is suppressed'; the refusal path emits no `LandingResult`). So `--json` can only ever emit `no-prior` or `changed`, and a downstream script cannot distinguish 'refused because unchanged' from any of the other eight refusals except by parsing the stderr exception name — which is the state the plan claims `verdict` fixes. risks[13] correctly warns that this diff is pinning `incremental-loading`'s contract.

**Proposed fix:** Decide one: (a) drop `verdict` from `--json` and say plainly that stderr's `type(error).__name__` is the discriminator — accurate, and consistent with the dropped exit code 3; or (b) emit the JSON envelope on the refusal path too (`{"verdict": "unchanged", "save_id": ..., "sim_date": ..., "ingest_seq": <existing>}` on stdout, exception name still on stderr, exit still 1) and add an offline test asserting `json.loads(stdout)["verdict"] == "unchanged"` with exit 1. (b) is the one that delivers what the decision claims; either way the plan must stop asserting the value exists when the control flow forbids it.

### [MAJOR] EXEC-08 — AC10/AC12 drive `main()` but the mandated cleanup needs the `IngestRun` only `land()` returns

**Reviewer:** `executability` · **Confidence:** high · **Category:** test-executability · **Location:** plan phases[4] acceptance AC10 ('`main(["land", "--save-id", <probe>])` returns 0') and phases[4] step 6 ('Every test purges in `finally` via `fixtures.warehouse.purge_snapshot`') — against tests/fixtures/warehouse.py:99-130

**Problem:** `purge_snapshot(connection, run)` requires an `IngestRun` to read `run.save_id`, `run.sim_date` and `run.ingest_seq` from. `main(argv) -> int` returns an exit code and nothing else, so a test that lands through `main()` has no object to hand the purge. The plan's own note says 'without it each run adds ~301,000 rows to the dev schema' — so the gap is not cosmetic. AC12 compounds it: it lands once, refuses once, and must clean up the first landing. The plan's next criterion then says 'a row at exactly the triple the function RETURNED', implying `land()` rather than `main()`, so the two criteria assume different entry points without saying so.

**Proposed fix:** Split the criteria by entry point explicitly. Use `main([...])` ONLY where the exit code and stdout are the claim (AC10's exit-0 and triple parse, AC12's non-zero), and reconstruct the run for cleanup from the parsed triple plus `read_ingest_run`, or build a tiny `_purge_triple(connection, save_id, sim_date, ingest_seq)` helper in the test module. Use `land(...)` -> `LandingResult.run` for every criterion that needs the object (AC11's row read-back, AC13, AC14). State in Phase 5's steps which criterion uses which, so the cold agent does not have to infer it.

### [MINOR] CG-05 — The prescribed `__all__` insertion point for `latest_landing` is out of order and fails ruff RUF022

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** correctness · **Location:** src/ootp_ai/warehouse/ingest_run.py:61

**Problem:** Phase 3 instructs: "Add both names to `__all__` (:61-71), sorted: `latest_landing` between `ingest_run_values` and `landed_max_seq`, and `landed_max_seq` before `next_ingest_seq`." That places `latest_landing` before `landed_max_seq`, but `landed_max_seq` sorts first (`lan` < `lat`). `pyproject.toml:72` selects `RUF`, and I confirmed on the pinned toolchain (ruff 0.16.3) that RUF022 `unsorted-dunder-all` is not preview-gated, so it is enforced — the ordering the plan dictates is a hard `uv run ruff check .` failure at the phase gate.

**Proposed fix:** Correct the instruction to: `ingest_run_values`, `landed_max_seq`, `latest_landing`, `next_ingest_seq`. (The parallel `snapshot.__all__` guidance is right: `read_manifest` < `read_sim_date` < `source_facts` < `take_snapshot`.)

### [MINOR] CG-06 — `docs/data-access.md:226-227`'s `unconfirmed` label is about `text_data.sqlite3`, not the save files or a running-game check

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** grounding · **Location:** docs/data-access.md:226

**Problem:** The plan's `conventions` and `risks` both cite "`docs/data-access.md:226-227` labels the OOTP write-lock question `unconfirmed`" as the ground for keeping running-game detection out of scope, and asserts "this repo forbids building on an unconfirmed or assumed claim." The line does exist and does carry `unconfirmed`, but it sits under `## 3. The SQLite database` (:212) and "this file" refers to `<save>.lg/temp/text_data.sqlite3` (:214) — a file this pipeline never opens and which is not in `SNAPSHOT_FILES`. There is no labelled claim anywhere about whether OOTP holds a lock on the `.dat` files it copies. The plan's conclusion (defer the spike) is right, but it rests on the scope's second ground — a research task does not belong in a wiring change — not on this citation.

**Proposed fix:** Rewrite the citation to say what it actually supports: `:85` records `flag_save_completed.dat` with no read content, and `:226-227`'s `unconfirmed` write-lock note is about the SQLite text-data file, so the `.dat` write-lock question is unlabelled — i.e. entirely unexamined, which is a stronger reason to keep the spike separate, not a weaker one.

### [MINOR] CG-07 — Phase 1's pre-move grep misses three live bare-filename references to `ingest.py`

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** completeness · **Location:** src/ootp_ai/validate/export_diff.py:118

**Problem:** Phase 1 says "Find every reference to the old path BEFORE moving: `rg -n 'ootp_ai/ingest\.py'`. The single live line-numbered reference is `.claude/agents/data-engineer-memory.md:202`." That pattern is path-qualified and finds only the memory file. Searching bare `ingest.py` turns up three more live prose references that survive in tracked source after the move: `src/ootp_ai/validate/export_diff.py:118` ("the same ambiguity `ingest.py` refuses"), `src/ootp_ai/parser/human_managers.py:114` ("`ingest.py` resolves it from here"), and `tests/test_extraction_cost.py:25` ("What it covers is stated in `ingest.py`"). None is line-numbered and none is a markdown link, so `tests/test_doc_links.py` (LINK at :20, BARE_REQUEST_TOKEN at :48) will not catch them — which is exactly why the scope's Risks §12 says to find every reference before the move.

**Proposed fix:** Change the prescribed command to the unqualified `rg -n 'ingest\.py'` (or `Select-String -Pattern 'ingest\.py'`, since `rg` is not on PATH on this machine — the plan's own commands assume it is), and add the three sites to Phase 1's edit list as one-word corrections (`ingest.py` → `ingest/`), while keeping the `requests/**/reviews/` exclusion the plan already states.

### [MINOR] CG-08 — The target-resolution `ValueError` → exit 2 collides with the established `ValueError` → exit 1 convention, with no distinguishing type given

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** correctness · **Location:** src/ootp_ai/reports/__main__.py:53

**Problem:** Phase 4 requires an unknown `--save-id` to "raise a `ValueError` naming every configured `save_id`, which `main` maps to exit **2**" (AC3), while the same phase's error-surface bullet lists a nine-member refusal tuple mapped to exit 1 — and the pattern being copied, `reports/__main__.py:53`, catches bare `ValueError` and returns 1. The plan never says how `main` tells the two apart. A cold implementer who adds `ValueError` to the refusal tuple, or who wraps resolution inside the same `try`, gets exit 1 and reds AC3; one who catches `ValueError` → 2 broadly changes the funnel for every other `ValueError` the command can raise.

**Proposed fix:** Name a distinct exception in the plan — e.g. `UnknownSave(ValueError)` defined in `ingest/__main__.py` — caught in its own `except` returning 2, and state that resolution happens in a separate `try` block preceding the refusal tuple. Add it to the parametrised nine-exception walk as the one member asserted to yield 2 rather than 1.

### [MINOR] CG-09 — Printing `ensure_tables`' created tables at call time would displace AC10's pinned line one

**Reviewer:** `code-grounded` · **Confidence:** medium · **Category:** correctness · **Location:** src/ootp_ai/warehouse/load.py:189

**Problem:** The architecture map's fail-fast order says "`ensure_tables` (print any table created)" — i.e. printed where it happens, before the copy — while Phase 4 carries `created_tables` on `LandingResult` and renders it inside `format_result` after the pinned first line `landed <save_id> <YYYY-MM-DD> ingest_seq <n>`. AC10 parses the triple out of `capsys` stdout line one, and AC18 is exactly the fresh-clone run where `ensure_tables` (load.py:169-189) actually creates all eight tables and returns them. If an implementer follows the ordering bullet literally, line one on the first-ever run is a created-table line and AC10's parse breaks on the one machine state AC18 exercises.

**Proposed fix:** Delete "print" from the fail-fast ordering bullet — it should read "`ensure_tables` (capture the created tuple)" — and state once, in Phase 4, that the command emits nothing until `format_result`/`format_json` runs, so line one is unconditionally the triple.

### [MINOR] EXEC-09 — Phase 1's 'byte-exact' verification command is not a byte comparison and its redirect corrupts the baseline

**Reviewer:** `executability` · **Confidence:** high · **Category:** verification-strength · **Location:** plan phases[0] step 4 (`git show HEAD:... > before.py`, then `Compare-Object (Get-Content ...) (Get-Content ...)`)

**Problem:** Two defects in one command. First, PowerShell's `>` in this environment defaults to UTF-8 **with BOM**, so the redirected baseline differs from the blob in its first three bytes before any comparison happens. Second, `Compare-Object` over `Get-Content` compares line arrays: it is blind to a CRLF/LF change, to a missing or added trailing newline, and to trailing whitespace normalisation — exactly the classes of drift a cross-platform repo that pins `newline="\n"` in `snapshot._write_manifest` cares about. The step's own acceptance restates it as 'returns no differences', so a corrupted move would pass the gate.

**Proposed fix:** Replace with a real content-hash comparison that never materialises a file: `git show HEAD:src/ootp_ai/ingest.py | git hash-object --stdin` compared against `git hash-object src/ootp_ai/ingest/__init__.py` — identical blob hashes prove byte-identity. Also drop the `git mv` suggestion or route it through the operator explicitly: `git mv` writes the index, and the plan's own conventions say subagents get read-only git; `Move-Item` plus `/commit`'s deliberate staging is the in-convention move.

### [MINOR] EXEC-10 — The pre-move grep pattern is too narrow, and 'the single live line-numbered reference' will stop a cold agent looking too early

**Reviewer:** `executability` · **Confidence:** high · **Category:** missing-step · **Location:** plan phases[0] step 2 (`rg -n 'ootp_ai/ingest\.py'`) and risks[16]

**Problem:** The prescribed pattern only matches the path-qualified form. Grepping the whole tree for bare `ingest.py` turns up three live references that survive after the move and become stale: `src/ootp_ai/parser/human_managers.py:114` ('`ingest.py` resolves it from here'), `src/ootp_ai/validate/export_diff.py:118` ('the same ambiguity `ingest.py` refuses to resolve'), and `tests/test_extraction_cost.py:25` ('What it covers is stated in `ingest.py`'). None is line-numbered, so the plan's claim is defensible as literally worded — but the confident phrasing 'The single live line-numbered reference is `.claude/agents/data-engineer-memory.md:202`' tells the agent the search is finished, and the given pattern would not have surfaced them anyway.

**Proposed fix:** Change the step to `rg -n 'ingest\.py' --glob '!requests/**/reviews/**'` and list the four expected hits (the three above plus data-engineer-memory.md:202) with the disposition for each: correct :202's path to `src/ootp_ai/ingest/__init__.py`; leave the three bare prose references as-is if the module name still reads correctly, or update them to `ingest/__init__.py` in the same commit. Keep the existing rule that `requests/**/reviews/` handoffs are never rewritten.

### [MINOR] EXEC-11 — The docstring write-guard hazard list omits most of the literals that actually trip the guard

**Reviewer:** `executability` · **Confidence:** high · **Category:** incomplete-guidance · **Location:** plan phases[1] step 5, testing 'Regression safety (3)', risks[7] — against tests/test_read_only.py:322-334,337,341,375-386

**Problem:** The plan bans seven literals in the new modules' prose (`.mkdir(`, `.write_text(`, `.write_bytes(`, `.touch(`, `os.makedirs`, `.unlink(`, `.rename(`). `DESTRUCTIVE_CALLS` (tests/test_read_only.py:322-334) actually holds eleven entries — it also carries `shutil.move`, `shutil.rmtree`, `os.remove`, `os.unlink`, `os.rename`, `os.replace`, `os.utime`, `os.chmod` and `os.truncate` — and `_writes_in` additionally matches write-mode `open(...)` via `_OPEN_MODE` (:341), which scans the whole text with no comment stripping at all. This is a live hazard for exactly these two modules: `ingest/__main__.py`'s docstring is specified to record that it deliberately has 'no purge' and 'no retention policy', and the natural way to write that names `shutil.rmtree` or `os.remove`.

**Proposed fix:** Replace the seven-item list with a pointer plus the full rule: 'no literal from `tests/test_read_only.py:322-334` (DESTRUCTIVE_CALLS) or :337 (CREATIVE_CALLS) may appear anywhere in these modules' source text, docstrings included, and no `open(...)` with a quoted mode containing w/a/x/+ may appear even inside a docstring. Prefer prose that names no call: "creates no directory of its own", "removes nothing".' Add `uv run pytest tests/test_read_only.py -k "allowlisted or destructive"` as the immediate check after writing each docstring.

### [MINOR] EXEC-12 — The invocation-string constant cannot be single-sourced into reports/resolve.py, but the plan says it is

**Reviewer:** `executability` · **Confidence:** medium · **Category:** design-gap · **Location:** plan phases[3] step 8 ('Define the literal invocation string ONCE as a module-level constant') vs phases[6] step 3 and files_to_touch['src/ootp_ai/reports/resolve.py']

**Problem:** The constant is specified to live in `src/ootp_ai/ingest/__main__.py`. `reports/resolve.py` cannot import from another package's `__main__` module without an awkward and cycle-prone dependency (and `ingest/__init__.py` is pinned byte-unchanged by AC9, so the constant cannot go there). In practice the string will exist in three places — the constant, `README.md`, and `resolve.py:179-182`'s message — with only a test binding them. That is a workable design, but the plan states the opposite ('so ... cannot drift'), which will send a cold agent hunting for an import that should not be written.

**Proposed fix:** State it plainly: the string is duplicated by necessity, and the anti-drift device is the AC8 test, which reads the constant from the command module and asserts the literal appears in both `README.md` and `src/ootp_ai/reports/resolve.py`. If genuine single-sourcing is wanted, put `LAND_COMMAND: Final = "uv run python -m ootp_ai.ingest land"` in `src/ootp_ai/ingest/read.py` (a new module, no `__all__` constraint, already imported by `__main__`) and import it into `resolve.py` — but say which of the two you chose, and note the `reports -> ingest.read` import edge if you pick the second.

### [MINOR] EXEC-13 — Phase 4 claims all nine offline criteria green while AC8 is explicitly deferred to Phase 7

**Reviewer:** `executability` · **Confidence:** high · **Category:** internal-inconsistency · **Location:** plan phases[3] goal and commit_note ('all nine offline criteria go green in CI' / 'All nine offline criteria proved in CI') vs phases[6] acceptance AC8 and files_to_touch['tests/test_ingest_command.py']

**Problem:** AC8 asserts `README.md` contains the literal invocation string and does not contain 'There is no ingest command', and that `reports/resolve.py` carries the same string. Both edits are Phase 7 steps, and `files_to_touch` confirms 'AC8's README/resolve.py literals (Phase 7)'. An implementer taking Phase 4's goal at face value writes AC8's test in Phase 4 and gets a red offline suite at the checkpoint, or writes the README edit early and lands a doc change in a phase whose commit note describes only the CLI surface.

**Proposed fix:** Change Phase 4's goal and commit_note to 'eight of the nine offline criteria (AC1-AC7, AC9); AC8 lands with the docs in Phase 7'. Add the same note to Phase 4's acceptance list so the criterion count in the acceptance ledger is unambiguous at every checkpoint.

### [NIT] CG-10 — "Define the invocation string ONCE" is not achievable across `README.md` and `resolve.py`, and the literal reading invites an import cycle

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** design · **Location:** src/ootp_ai/reports/resolve.py:181

**Problem:** Phase 4 says "Define the literal invocation string ONCE as a module-level constant, so Phase 7's README and `resolve.py` assertions and the command itself cannot drift." Two of the three consumers cannot share it: `README.md:117-118` is markdown, and `_nothing_landed_message` (resolve.py:179-182) is in the `reports` package. Importing the constant from `ootp_ai.ingest.__main__` into `resolve.py` would also close a cycle — Phase 5 has `ingest/__main__.py` importing `reports.resolve.landed_sim_dates` (:78-94) for the refusal message. The string is necessarily triplicated; only AC8's test reconciles it.

**Proposed fix:** Reword to: the command module owns the canonical constant, the README and `resolve.py` carry copies, and AC8 is the mechanism that keeps them equal — and add an explicit "do not import the constant into `reports/resolve.py`; that closes an import cycle with `ingest/__main__.py`."

### [NIT] CG-11 — `verify_snapshot`'s 0.042 s figure is a measurement of a source-side digest, presented as a measurement of `verify_snapshot`

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** epistemics · **Location:** src/ootp_ai/snapshot.py:254

**Problem:** Phase 5 states "`verify_snapshot` … Its cost objection is measured away: a full SHA-256 over all 54,946,744 bytes took **0.042 s** on 2026-08-30." 54,946,744 bytes is the plan's own live-save total (the five source files, with `players.dat` at 32,078,633); `verify_snapshot` (snapshot.py:254-279) digests the snapshot COPY, whose five files total 54,938,202 bytes, and additionally does a `stat()` and `read_manifest` per call. The number is a good proxy but it is not a measurement of the function, and the repo's convention is to label what was actually measured. It also does not state cache state, which matters for a 52 MB streamed read.

**Proposed fix:** Relabel it as `measured — a streamed SHA-256 over the five source files (54,946,744 B), warm cache, as a proxy for verify_snapshot's cost`, and keep Phase 7's obligation to record the real post-copy `verify_snapshot` timing, which is the number the scope's fold-in asked for.

### [NIT] CG-12 — The fake-cursor tests need the `cast`/wrapper pattern `test_bronze_landing.py` uses, which the plan does not mention

**Reviewer:** `code-grounded` · **Confidence:** high · **Category:** completeness · **Location:** tests/test_bronze_landing.py:188

**Problem:** Phase 3 prescribes "offline tests … against a fake cursor in the `_FakeConnection` style already used in `tests/test_bronze_landing.py`." That module does not pass its fake straight to typed library functions: `_FakeCursor` is at :86, `_FakeConnection` at :140, and every call goes through a local `_land(connection: _FakeConnection, …)` wrapper at :188 with `cast` imported at :36. The new `latest_landing`/`landed_max_seq` will be typed `Connection[DictCursor]`, and mypy strict covers `tests` (pyproject.toml:93,95), so a direct call with a fake is a type error at the phase gate.

**Proposed fix:** Add one sentence to Phase 3: the new offline tests wrap each helper in a local `_FakeConnection`-typed shim that `cast`s, mirroring `tests/test_bronze_landing.py:188-195`.

### [NIT] EXEC-14 — `read_save` reads teams.dat twice per call, unremarked, in a function whose whole purpose is bounding game reads

**Reviewer:** `executability` · **Confidence:** high · **Category:** efficiency · **Location:** plan phases[1] step 2 (steps 1 and 4 of the `read_save` body) — against src/ootp_ai/snapshot.py:185,285-293

**Problem:** `read_save` opens with `sim_date = read_sim_date(save)`, which does `source.read_bytes()` over the whole ~5 MB `teams.dat` (snapshot.py:292-293). It then calls `take_snapshot`, whose first act (snapshot.py:185) is `_read_sim_date(save)` again — the same whole-file read of the same game file. That is ~10 MB of game reads where 5 MB is needed, on the one function the plan bills as 'performs EVERY game read the command makes', repeated three to four times per AC11 run. It does not break anything, but the plan measures `read_sim_date` at 0.005 s and never mentions that it is paid twice, which will confuse anyone later reconciling the measurement against the code.

**Proposed fix:** Either accept it and say so in `read_save`'s docstring ('`take_snapshot` re-reads the header; the duplicate 5 MB read is accepted so `take_snapshot` keeps its single-argument contract'), or add an optional `sim_date: SaveDate | None = None` keyword to `take_snapshot` that skips its own `read_sim_date` when supplied. The second is three lines and removes a game read; either way state which, because silence here reads as an oversight in the function ADR 0001's guard brackets.

### [NIT] EXEC-15 — The `unconfirmed` label cited to keep running-game detection out of scope is about the OSA SQLite file, not the save's .dat write lock

**Reviewer:** `executability` · **Confidence:** high · **Category:** citation-accuracy · **Location:** plan conventions[3] and risks[11] ('docs/data-access.md:226-227 labels the OOTP write-lock question `unconfirmed`') — against docs/data-access.md:223-227

**Problem:** docs/data-access.md:226-227 reads 'Whether OOTP holds a write lock on this file while the game is running. Read with `mode=ro` and expect to need the game closed.' — `mode=ro` is a SQLite URI parameter, and the surrounding claim at :223-224 cross-checks a row count against the in-game Database screen, so 'this file' is the OSA SQLite database, not `players.dat`. The plan's conclusion (no running-game spike in a wiring change) is correct and rests on a second, independent ground it already states; but the epistemic citation supporting it does not say what the plan says it says, and this repo's own rule is to read the label AND the claim it attaches to.

**Proposed fix:** Cite the two claims the repo actually carries: `docs/data-access.md:85` records `flag_save_completed.dat` with no read content at all (so nothing is known about it), and the write-lock `unconfirmed` at :226-227 is about the OSA database. Then keep the drop on the ground the scope already gave it (PROJECT_SCOPE.md:403-408): a research task producing a labelled finding does not belong in a wiring change.

### [NIT] EXEC-16 — The memory correction fixes the path but leaves the surrounding verified claim's subject false

**Reviewer:** `executability` · **Confidence:** medium · **Category:** doc-truth · **Location:** plan phases[0] step 8 ('Correct `.claude/agents/data-engineer-memory.md:202`'s evidence path') — against .claude/agents/data-engineer-memory.md:199-203

**Problem:** The entry reads: '`verified` — A refusing parser must not be wired into `ingest_save`: `tests/test_read_only.py` calls it, so a raise there converts the ADR 0001 proof from green to error.' Phase 2 re-points AC11's three legs off `ingest_save` entirely (test_read_only.py:254,263,268), so after this change `tests/test_read_only.py` no longer calls `ingest_save` — the entry's stated mechanism becomes false while the hazard itself transfers wholesale to `ingest/read.py::read_save`. Correcting only the trailing evidence path leaves a `verified` claim whose body no longer describes the repo.

**Proposed fix:** In the same edit, append a dated line rather than rewriting the old one (the file's :41 rule is append-freely): '**2026-08-3x** · `verified` · The refusing-parser hazard moved: `tests/test_read_only.py`'s AC11 legs now call `ingest/read.py::read_save`, not `ingest_save`, so a raise wired into `read_save` is what would convert the ADR 0001 proof from green to error. · evidence: `tests/test_read_only.py:254,263,268` · tag: harness'. Cheaper than a rewrite and it keeps the record of what was believed when.

## Meta-audit findings (did the merge converge faithfully?)

### [BLOCKER] M-01 — The merge closes the scope's mandated cost decision with a comparison it never measured, and the number is wrong by ~2,500x in the wrong direction

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** cost-unrealism · **Location:** merged plan `summary` ("at 42 ms against a 52.4 MiB copy, digest-before-copy wins by roughly three orders of magnitude and the debate is closed") + `decisions[1]` + Phase 7 step writing it into IMPLEMENTATION_REPORT.md labelled `measured`; grounds itself on src/ootp_ai/snapshot.py:296-319

**Problem:** Scope Risks §2 (PROJECT_SCOPE.md:427-432) requires the plan to pick digest-before-copy or copy-then-compare and say which "with numbers on both sides". The merge produced a number for ONE side only (the digest) and inferred the other. I measured both on this machine over the same 54,938,202 bytes (var/snapshots/OOTP-AI/2024-03-07/1, manifest excluded), three runs: digest 54.1 / 47.8 / 47.4 ms; copy 18.3 / 16.0 / 25.5 ms. The digest is ~2.5x MORE expensive than the copy it is supposed to avoid, not three orders of magnitude cheaper. It cannot be otherwise: a digest reads 52.4 MB, a copy reads 52.4 MB and writes it, so the ceiling on any such advantage is ~2x, and it runs the wrong way. The merge appears to have transposed the size-fast-path figure (0.313 ms, which genuinely is ~3 orders below a copy) onto the full-digest claim. Three planners did not make this error — the sequencing planner explicitly reserved it as measurement M3 with numbers required on both sides, and the merge dropped that phase on the grounds that it had already taken the measurements.

**Proposed fix:** Keep the decision — digest-before-copy is still right — but replace the justification with the one that survives measurement, which the merge already states as a side note: copy-then-compare consumes a filesystem `ingest_seq`, creates a directory under `var/snapshots` that nothing in this project reclaims (ADR 0021 §Consequences: 'no retention policy exists'), and leaves an orphan on every refusal. Rewrite the summary sentence to: 'digest-before-copy costs ~48 ms measured, roughly 2.5x the ~18 ms copy it avoids; it is chosen anyway because copy-then-compare burns a sequence and leaves an unreclaimable 52.4 MiB directory on every refusal.' Record BOTH timings in IMPLEMENTATION_REPORT.md, with the measurement conditions (warm page cache, same volume), and delete the 'three orders of magnitude' claim wherever it appears.

### [MAJOR] M-02 — `SaveReading` superimposes two planners' incompatible control flows, creating unreachable states that fail mypy strict at the Phase 2 gate

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** completeness-dedup · **Location:** merged plan Phase 2, step 1 (`SaveReading` field list) and step 2 (`a None return raises SaveUnchanged`); consumed at Phase 2 step 6 (`read.read_save(...).parsed`) and Phase 5 step 1 (`verify_snapshot(reading.parsed.run.snapshot.path)`)

**Problem:** The code-grounded proposal returned the outcome (`SaveReading.parsed: ParsedSnapshot | None`, `verdict` in {no-prior, changed, unchanged}, with an explicit documented invariant 'parsed is None iff verdict == unchanged and refuse_unchanged'). The domain-convention proposal raised `SaveUnchanged` instead and returned a non-optional `SaveRead`. The merge folded both: it keeps `parsed: ProcessedSnapshot | None` AND `verdict: str` AND raises `SaveUnchanged` on the unchanged branch. Under the raising design `parsed` can never be None and `verdict` can never be "unchanged" on a returned value, so both are dead API. Worse, it breaks the phase gate: `tests/fixtures/warehouse.py::landed_probe` becomes `read.read_save(...).parsed` handed to `_land(connection, parsed)`, and Phase 5 dereferences `reading.parsed.run.snapshot.path` — both are `ParsedSnapshot | None` under mypy `strict = true` over `files = ["src", "tests"]` (pyproject.toml:93,95), so `uv run mypy` reds at the end of Phase 2 with no design guidance in the plan for which way to resolve it.

**Proposed fix:** Pick one shape and delete the other's residue. Recommended: keep `SaveUnchanged` (it maps cleanly onto the nine-exception exit-1 tuple the plan already specifies) and make `SaveReading.parsed: ParsedSnapshot` non-optional, with `verdict: Literal["no-prior", "changed"]`. Move the 'unchanged' outcome entirely onto the exception, which should carry the prior triple. State the resulting invariant in one sentence in the module docstring so the deleted alternative cannot be re-derived.

### [MAJOR] M-03 — The gated `verdict` field cannot deliver the discriminator it is justified by — its only interesting value is unreachable in `--json`

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** correctness · **Location:** merged plan `gated_decisions[4]` (`verdict` in `--json`) + `decisions[8]` + Phase 4 step 5 (`format_json` emits `verdict` ("no-prior"/"changed"/"unchanged"))

**Problem:** The merge argues `verdict` is worth adding beyond the scope's trimmed `--json` list because 'it gives `incremental-loading` the discriminator that a distinct exit code 3 was dropped for' (PROJECT_SCOPE.md:413-415). But under the plan's own control flow, the unchanged case raises `SaveUnchanged` inside `read_save`, is caught in `main()`, printed to stderr and returns 1 — no `LandingResult` is ever constructed, so `format_json` is never called and `verdict="unchanged"` never reaches stdout. The two values that CAN appear (`no-prior`, `changed`) both mean 'a landing happened', which the presence of a triple already tells you. The addition therefore buys nothing and pays a widening of a field set the scope deliberately trimmed.

**Proposed fix:** Either drop `verdict` and record in the plan that the append-only refusal is discriminated by `type(error).__name__` on stderr plus exit 1 (which the scope already accepted when it dropped exit code 3), or make it real: emit a machine-readable object on the refusal path too — `{"verdict": "unchanged", "save_id": ..., "sim_date": ..., "ingest_seq": ...}` on stdout with exit 1 — and say so explicitly in AC5's test. Do not ship the current shape, which promises a discriminator the code cannot produce.

### [MAJOR] M-04 — AC6's identity assertion and the Phase 4 monkeypatch both contradict the module-attribute call style the plan declares load-bearing

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** testability · **Location:** merged plan `testing` ("an `is`-identity assertion proving both modules reference the same object") vs Phase 2 step 8 and `risks[8]` ("Both call sites therefore import the MODULE (`from ootp_ai.ingest import read`) and call `read.read_save(...)`") vs Phase 4 acceptance AC6 ("monkeypatch `ootp_ai.ingest.__main__.read_save`")

**Problem:** Three mutually inconsistent prescriptions merged from two planners. The domain-convention proposal used name imports and therefore an `is`-identity assertion (`test_read_only.read_save is fixtures.warehouse.read_save is read.read_save`) plus patching both module attributes. The code-grounded proposal used module imports (`read.read_save(...)`) so that ONE patch on `ootp_ai.ingest.read.read_save` observes both callers. The merge adopts the code-grounded style and calls it 'load-bearing, not cosmetic', then keeps the domain-convention identity assertion — which under module imports has no `read_save` attribute to reference on either module and degrades to the vacuous `fixtures.warehouse.read is read` — and then Phase 4's AC6 step says to patch `ootp_ai.ingest.__main__.read_save`, an attribute that does not exist if `__main__` imports the module. A cold implementer will write one of these, watch it record zero calls, and 'fix' it by switching to name imports, silently losing the single-patch property the plan says protects AC6.

**Proposed fix:** Commit to module imports and rewrite AC6 as exactly two assertions, both in terms of `ootp_ai.ingest.read`: (a) `assert fixtures.warehouse.read is ootp_ai.ingest.read is ootp_ai.ingest.__main__.read` — the modules, not the functions; (b) `monkeypatch.setattr(ootp_ai.ingest.read, "read_save", recorder)` ONCE, then drive `land(...)` and `landed_probe(...)` and assert two recorded calls. Delete the `__main__.read_save` and `fixtures.warehouse.read_save` patch instructions from Phases 4 and 5.

### [MAJOR] M-05 — The merge dropped the sequencing planner's size-fast-path hit-rate question and declared it settled from a single file's anecdote — the fast path cannot fire on the refusal path at all

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** cost-unrealism · **Location:** merged plan `summary` ("The size fast path fires on a real save, which the scope could only assume") and `decisions[1]` ("the mitigation the scope hoped for is also confirmed rather than assumed"); dropped from the sequencing proposal's Phase 0 M2 and its second risk entry

**Problem:** The sequencing planner raised, with evidence from docs/data-access.md's size table, that most snapshot files are size-stable and the fast path may settle little — and reserved a measurement (M2) to price it before the plan leaned on it. The merge dropped M2 and substituted one observation: live `players.dat` 32,078,633 vs 32,070,091 landed. I reproduced that exactly, and also the rest: `teams.dat`, `names.dat`, `world.dat` and `human_managers.dat` are byte-size-IDENTICAL between the live managed save and its landing. So 4 of 5 files gave no signal. More decisively, the fast path is structurally unavailable in the case the pre-flight exists for: when the operator re-runs against an unchanged save, every size matches by definition, so `reason_to_land` always falls through to the full ~48 ms / 52.4 MB digest before it can refuse. The merge's claim that the refusal 'costs nothing because it fires before the copy' is therefore priced against the wrong baseline, and 'the objection to folding verify_snapshot in' is not killed by the same number — verify_snapshot adds a THIRD full digest of the same bytes in the same process.

**Proposed fix:** Restore the sequencing planner's M2 as a one-paragraph honest statement in the risks list: the size fast path settles the CHANGED direction cheaply (measured: 1 of 5 files moved on the managed league, 2026-08-30) and cannot fire at all on the UNCHANGED/refusal path, so every refusal costs a full source-side digest (~48 ms measured, warm). Then restate the refusal's cost as '~48 ms and no directory created' rather than 'costs nothing', and re-derive the verify_snapshot fold's total (`_copy_one` source digest + `_copy_one` destination digest + `verify_snapshot`) as three passes over 52.4 MB per land, recording the sum in Phase 7.

### [MINOR] m-06 — `--json` quietly gained four fields beyond the scope's explicitly 'trimmed' folded-in list; only the fifth was gated

**Reviewer:** `meta-audit` · **Confidence:** medium · **Category:** scope-creep · **Location:** merged plan Phase 4 step 5 (`format_json` emits ... `challenge_mode`, `created_tables`, both sequences ...) against PROJECT_SCOPE.md:344-347 ("**`--json`**, trimmed: the triple, per-table row counts, per-file residual bytes and `parse_seconds`")

**Problem:** The scope names four `--json` fields and uses the word 'trimmed' deliberately, having just deferred per-table digests out of the same fold. The merge emits eight-plus: the scope's four, then `challenge_mode`, `created_tables`, `filesystem_seq`, `warehouse_max_seq` and `verdict`. Only `verdict` was surfaced in `gated_decisions`; the other four ride in unflagged. Each is individually free (zero extra queries, all already on `LandingResult`), but the scope also notes this diff PINS the downstream contract `incremental-loading` will be written against (Risks §16) — so 'free to compute' is not the same as 'free to promise', and AC4's 'yields exactly the documented keys' makes each one a pinned contract.

**Proposed fix:** Either trim `format_json` back to the scope's four fields plus whatever the gate approves, or list all five additions together in `gated_decisions` with the one-line argument for each and let the operator dispose of them as a set, exactly as `verdict` was handled.

### [MINOR] m-07 — An open question two planners raised — where the new warehouse read helpers live — was resolved silently with no rationale and no gate

**Reviewer:** `meta-audit` · **Confidence:** medium · **Category:** completeness-dedup · **Location:** merged plan Phase 3 (both helpers added to `src/ootp_ai/warehouse/ingest_run.py`); dropped from the sequencing proposal's Phase 3 step 3 and the domain-convention proposal's open_questions[1]

**Problem:** The sequencing planner deliberately placed the composed prior-landing lookup under `ingest/` rather than `warehouse/` so 'the warehouse package gains exactly one new function', and the domain-convention planner raised placement as an explicit open question, noting the precedent cuts both ways because `reports/resolve.py:78-94` already writes its own `ingest_run` SQL outside `warehouse/`. The merge puts BOTH new helpers inside `warehouse/ingest_run.py` and never mentions the alternative. The choice is probably right — it sits them beside `next_ingest_seq`, whose docstring is the warning they must not repeat — but that argument exists only in the discarded proposals, so a reviewer who asks 'why here?' gets nothing, and the plan loses the one reason that makes the placement obviously correct.

**Proposed fix:** Add a one-line entry to `decisions`: the helpers live in `warehouse/ingest_run.py` beside `next_ingest_seq` (:137-153) precisely so a future reader sees the FOR-UPDATE contrast at the point of temptation; the `reports/resolve.py` precedent for warehouse SQL outside the package was considered and rejected on that ground. Note that `tests/test_bronze_landing.py:812-818`'s scan then covers them, which is a benefit rather than a cost.

### [MINOR] m-08 — The summary claims Phase 4 turns all nine offline criteria green, but AC8 lands in Phase 7 and AC1 in Phase 2

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** internal-consistency · **Location:** merged plan `summary` ("(4) the CLI surface, all nine offline criteria green in CI") vs Phase 4 `acceptance` (lists AC2-AC7 and AC9 only) and Phase 7 acceptance (AC8)

**Problem:** AC1-AC9 are the nine offline criteria. Phase 4's own acceptance list contains seven of them; AC1 is proved in Phase 2 and AC8 (README + resolve.py literal strings) is deliberately deferred to Phase 7 because the invocation string is only stable once Phases 4-6 ship — which is a good call, correctly argued in Phase 7's goal. The summary contradicts it. A cold implementer working the summary as a checklist will look for AC8 work in Phase 4 and find none, or worse, write the README edits early and pin a string the later phases then change.

**Proposed fix:** Change the summary to '(4) the CLI surface, seven of the nine offline criteria green in CI — AC1 landed in Phase 2, AC8 waits for Phase 7 because it pins the invocation string.' Phase 4's acceptance list is already correct; leave it.

### [MINOR] m-09 — `verify_snapshot`'s cost is asserted as measured when only a proxy was timed, and every timing in the plan is warm-cache without saying so

**Reviewer:** `meta-audit` · **Confidence:** medium · **Category:** epistemics · **Location:** merged plan Phase 5 step 5 ("a full SHA-256 over all 54,946,744 bytes took **0.042 s** on 2026-08-30" offered as verify_snapshot's cost) and `decisions[4]`; Phase 7 step instructing all four numbers be recorded labelled `measured`

**Problem:** CLAUDE.md makes per-claim epistemic labelling binding, and `measured` is the strongest label available. What was actually timed is a source-side digest of the five SNAPSHOT_FILES; `snapshot.verify_snapshot` (snapshot.py:254-279) re-digests the snapshot COPY and additionally re-reads and validates the manifest. Same order of magnitude, but not the same measurement, and the plan presents it as one. Separately, my own reproduction shows the first (cold-ish) digest run at 167 ms falling to ~48 ms once warm — a 3.5x spread — so a bare '0.042 s' with no stated conditions will be read as the cost of a cold operator run, which it is not. The same applies to `read_sim_date` at 0.005 s for a 5.3 MB whole-file read.

**Proposed fix:** Downgrade the verify_snapshot figure to `inferred (from an equivalent-volume digest, not from verify_snapshot itself)` until Phase 5 actually times the call, which its own acceptance already schedules. Add 'warm page cache, same volume as the snapshot root' to every timing in the plan and in IMPLEMENTATION_REPORT.md, and record one cold figure alongside the warm one for the digest, since the operator's first run of the day is the cold case.

### [MINOR] m-10 — The regression test that guards 'the Challenge-mode line reports and never refuses' is scheduled a phase after the line ships, and appears only in prose

**Reviewer:** `meta-audit` · **Confidence:** medium · **Category:** sequencing · **Location:** merged plan `testing` per-phase selectors ("**Phase 6:** the same, plus `uv run pytest -m gamedata tests/test_cross_mode_format.py`") vs Phase 4 step 5 and Phase 5, where the mode line is written and wired; no phase's `acceptance` array names it

**Problem:** The mode line comes from `saves.is_challenge_mode` and the whole hazard — flagged by all three planners and by the scope — is that calling `assert_challenge_mode` instead would break `tests/test_parser_vs_export.py:130`, which lands the STANDARD-mode truth save through the fixture on every gamedata run (verified: test_cross_mode_format.py:119 is `assert not is_challenge_mode(settings.truth_save.path)`). The formatter is written in Phase 4 and wired in Phase 5, but the guard runs in Phase 6's selector, and only in the testing narrative — no phase's acceptance list contains it, so the per-phase gate does not enforce it. The sequencing planner had it in the same phase as the fold.

**Proposed fix:** Move `uv run pytest -m gamedata tests/test_cross_mode_format.py tests/test_parser_vs_export.py` into Phase 5's acceptance array, worded as 'proving the mode line reports and did not become a refusal', and keep it in Phase 6's selector as a re-run.

### [MINOR] m-11 — `LandingResult` carries two fields that appear to name the same number, a dedup artifact of merging two field lists

**Reviewer:** `meta-audit` · **Confidence:** medium · **Category:** completeness-dedup · **Location:** merged plan Phase 4 step 4 (`snapshot_ingest_seq: int | None`, `filesystem_seq: int | None`, `warehouse_max_seq: int`) against Phase 5 step 3 ("Record both numbers on the `LandingResult`")

**Problem:** Phase 5's reconciliation names exactly two inputs — the snapshot directory's own filesystem-allocated sequence (`parsed.run.ingest_seq`) and `landed_max_seq`. `LandingResult` declares three sequence fields. `snapshot_ingest_seq` and `filesystem_seq` are the same quantity on the normal path; presumably one was meant for `--from-snapshot`, where the directory's number is read rather than allocated, but the plan never says which is which and both are `int | None`. The formatter is then specified to print 'whether the landed `ingest_seq` still matches the snapshot directory's number' EVERY time (Scope Decision §3) — from an ambiguous pair, a cold implementer will pick one and the sentence will be silently wrong on one of the two paths.

**Proposed fix:** Collapse to two fields with names that say where each came from: `snapshot_dir_seq: int` (allocated by `take_snapshot` on the normal path, read off the directory name on `--from-snapshot`) and `warehouse_max_seq: int`. Delete `filesystem_seq`. State in one line that the printed match/divergence sentence compares `run.ingest_seq` against `snapshot_dir_seq`.

### [NIT] n-12 — The 'do not rewrite' rule covers `requests/**/reviews/` only, leaving four stale `src/ootp_ai/ingest.py` citations in this request's own decided artifacts unaddressed

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** documentation · **Location:** merged plan Phase 1 last step ("Do NOT rewrite any `requests/**/reviews/` handoff citing `ingest.py:NNN`"); the uncovered references are PROJECT_SCOPE.md:68, :283, :543, :580 and FEATURE_REQUEST.md:76, :126

**Problem:** I grepped `ootp_ai/ingest\.py` across the tree. Outside the reviews trail there are six live references in this request's own DECIDED artifacts, two of them line-numbered (`ingest.py:436`, `ingest.py:10-12`), plus the one in `.claude/agents/data-engineer-memory.md:202` the plan does handle. The plan's rule is scoped to `reviews/`, so a conscientious cold agent doing Phase 7's 'advance the request artifacts' step has no instruction and may well 'fix' the paths in PROJECT_SCOPE.md — editing a decided upstream artifact, which is exactly the thing the reviews rule exists to prevent.

**Proposed fix:** Widen the sentence: 'Do NOT rewrite any path citation inside `requests/` — not the reviews handoffs and not this request's own FEATURE_REQUEST.md or PROJECT_SCOPE.md. They are the record of what was believed when. The only prose correction in this change is `.claude/agents/data-engineer-memory.md:202`.'

### [NIT] n-13 — `.claude/agents/data-engineer-memory.md:202` is described as 'line-numbered' when it is a bare path

**Reviewer:** `meta-audit` · **Confidence:** high · **Category:** accuracy · **Location:** merged plan Phase 1 step 2 and `code_references` entry for `.claude/agents/data-engineer-memory.md:41,202`

**Problem:** The actual text at :202 is `· evidence: \`src/ootp_ai/ingest.py\` \`human_team_id=None\` ·` — a bare path with a symbol, no line number. The plan (inheriting the phrasing from the sequencing proposal) calls it 'the single live line-numbered reference to the moved file'. The line-numbered citations are the `:436` and `:10-12` ones in the request artifacts, which the plan says not to touch. Harmless to the action but a cold agent grepping for a line-numbered form will not find it and may conclude the reference is already gone.

**Proposed fix:** Reword to 'the single live reference to the moved path outside `requests/` — a bare path in an evidence line, no line number'.

### [NIT] n-14 — The `unconfirmed` label cited to justify dropping the running-game check belongs to a different file's write lock than the one the risk describes

**Reviewer:** `meta-audit` · **Confidence:** medium · **Category:** accuracy · **Location:** merged plan `risks[11]` and `conventions[3]` citing docs/data-access.md:226-227; the scope's own ground is the `assumed` content note at docs/data-access.md:92-96

**Problem:** docs/data-access.md:226-227 reads 'Whether OOTP holds a write lock on this file while the game is running. Read with `mode=ro` and expect to need the game closed' — it sits in a section about a database-style file read with a `mode=ro` connection string, not about the `.dat` files the snapshot copies. The merge uses it as the general 'can the command tell OOTP is running' authority. The scope's own justification (Above & Beyond, 'A spike on whether OOTP is currently running') rests instead on the `assumed` content label covering `flag_save_completed.dat` at :85, spelled out at :92-96 ('for the other fourteen the content column is `assumed` from the filename and nothing has opened them'). The code-grounded proposal cited that correctly; the merge substituted a weaker citation.

**Proposed fix:** Cite both, in the scope's own order: docs/data-access.md:85 with the label note at :92-96 (`flag_save_completed.dat`'s content is `assumed`, nothing has opened it) as the primary ground, and :226-227 only as a secondary note that the write-lock question is `unconfirmed` for the one file where it was asked.

### [NIT] n-15 — The merge dropped the code-grounded reason for `--from-snapshot` landing with `ingest_seq=None`, and inherits the weakened deadlock retry on that path without noting it

**Reviewer:** `meta-audit` · **Confidence:** medium · **Category:** completeness-dedup · **Location:** merged plan Phase 6 step 3 (`seq = max(snapshot.ingest_seq, landed_max_seq(...) + 1)`) vs the code-grounded proposal's Phase 4 `--from-snapshot` step (`land_snapshot(...)` with `ingest_seq=None`, 'which keeps the deadlock retry effective on this path')

**Problem:** The merge correctly identifies (risks[3], decisions) that an explicit `ingest_seq` defeats the per-attempt re-allocation in `load.py:232-250`, so a lost race surfaces as `ConcurrentLandingError` rather than a recovery — and states it as a knowing trade on the normal path. The code-grounded proposal had `--from-snapshot` keep `ingest_seq=None` specifically so that ONE path retained the retry, which is also the path most likely to be run twice in quick succession during a correction. The merge extends the explicit-sequence policy to `--from-snapshot` (correctly, to satisfy AC15 and the reconciliation rule) but drops the observation that this is where the retry is lost too.

**Proposed fix:** Add one sentence to Phase 6: 'This path also passes an explicit sequence, so like the normal path it forfeits `load.py:232-250`'s per-attempt re-allocation. The alternative — `ingest_seq=None`, keeping the retry — was rejected because AC15 and the printed match/divergence sentence both need the directory's own number in hand.'
