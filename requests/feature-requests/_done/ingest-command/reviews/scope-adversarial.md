# Scope panel — adversarial findings & convergence map

Panel health: 3/3 scopers, 2/2 adversaries, 44 findings (4 blocker, 12 major). Degraded lenses: none.

## Convergence map

### The request's Scope Signals are wrong about the writer allowlist, and the correct outcome is the opposite: `WRITERS` must stay byte-unchanged

**Scopers:** fit, ambitious, minimalist

All three independently read `tests/test_read_only.py:348-358` and reached the same conclusion, and I verified it: `_writes_in()` is a source-text scan of a module's *own* text for `.write_text(`/`.write_bytes(`/`.touch(`/`.mkdir(`/`os.makedirs` and write-mode `open(`, not a capability model. A module delegating every file creation to `snapshot.py:205` trips nothing. Adding an entry anyway would widen ADR 0001's allowlist to buy nothing — precisely the quiet erosion the list's own comment at `:294-302` was written to prevent. Three-way convergence *against* the request's own stated scope is the strongest signal in this panel.

### `ensure_tables` has exactly one caller and `ops/mysql-bootstrap.sql` creates no tables, so the fresh-clone story dies without the command creating the schema

**Scopers:** fit, ambitious, minimalist

A gap none of the three was asked to look for, found independently by all three and confirmed by grep: the only reference to `ensure_tables` outside its definition is `tests/fixtures/warehouse.py:93`. The bootstrap script's four `CREATE` statements are three databases and a user. The test suite is therefore doing *two* pieces of production work — creating the schema and filling it — not one, which means the request's own observable signal ('an empty warehouse, one command, then a rendered roster') cannot hold unless this is in core.

### The naive composition auto-allocates rather than refusing, so open question 3 must be settled deliberately or the command silently duplicates

**Scopers:** fit, minimalist, ambitious

Fit and minimalist reached this independently and stated it in the same terms; the ambitious scoper hit the same mechanic and drew the opposite conclusion (treating unreachability of the refusal as a feature), which sharpens rather than weakens the finding. Verified at `snapshot.py:189-201`: `ingest_seq=None` allocates the next free filesystem sequence and never raises. The consequence is quantified consistently across scopers — ~46 MB plus ~301,000 rows per accidental re-run, unreclaimable. This is why the re-run default is the headline gated decision.

### `--save-id` cannot mean on the ingest side what it means on the render side, and must resolve against the configured `SaveRef`s only

**Scopers:** fit, ambitious, minimalist

All three saw that `reports render --save-id` takes a *warehouse key* looked up in `ingest_run`, while an ingest target is a *save on disk* — and `Settings` exposes exactly three `SaveRef`s with no id-to-ref lookup anywhere (`config.py:99-108`). Left unsettled, the plan either invents an `enumerate_saves` sweep (letting a typo ingest an unrelated league) or ships a flag that only ever accepts the managed league's own id. The reconciling fact, which fit and minimalist both found, is that `SaveRef.save_id` *is* `to_save_id(league)` (`config.py:82-84`) — the same string the warehouse keys on — so one vocabulary with configured-only resolution is coherent.

### Pass the snapshot's own filesystem `ingest_seq` explicitly to `land_snapshot`, because the operator's snapshot is durable

**Scopers:** fit, ambitious, minimalist

Unanimous, and all three cite the same justification at `warehouse/load.py:203-217`: an explicit integer keeps the snapshot store and the warehouse naming the same attempt, which is the correspondence ADR 0021's *if the two disagree, the snapshot is right* triage rests on. `None` is for transient snapshots. The ambitious scoper additionally surfaced the cost nobody else caught — the deadlock retry re-allocates the sequence each attempt and therefore only helps on the `None` branch — which the plan must carry.

### No absolute path may reach stdout, because this output is the artifact most likely to be pasted into a tracked `gm/decisions/` record

**Scopers:** fit, ambitious, minimalist

All three connected three separate facts into the same rule: `saved_games.dat` embeds a user-profile path per save, `ingest.py:25-27` records that the run *type* deliberately has nowhere to put one, and `tests/test_no_leaks.py:37-41` scans tracked `.md` for drive letters and home directories. All three also noted the precedent cuts the other way (`reports/__main__.py:57-58` prints full paths), which is exactly why it must be a stated and tested divergence rather than an implicit one.

### The test fixture is re-pointable onto the operator's path without any of its test-only powers becoming CLI surface

**Scopers:** fit, ambitious, minimalist

The request's open question 4 asked whether re-pointing would leak test powers into production, and all three answered it the same way with the same evidence: `snapshot_root` is already a `Settings` field manipulated by `replace(...)` at `tests/test_read_only.py:193`, `ingest_seq=None` is already a `land_snapshot` parameter, and both can be library keyword arguments with no argparse flag. `purge_snapshot` stays in `tests/` because ADR 0021 §3 and `load.py:69-74` are explicit that a delete helper written 'just for tests' inside `src/` is how append-only stops being true.

### Three already-built safety functions have zero production callers and their docstrings claim otherwise

**Scopers:** fit, ambitious

Independently found and verified by grep: `saves.is_challenge_mode` / `assert_challenge_mode` and `snapshot.verify_snapshot` are called only from tests, while `saves.py:11-15` says the mode check is *'cheap enough to run on every ingest'* and `snapshot.py:254-260` says `verify_snapshot` is *'called after landing a snapshot'*. Both scopers also independently flagged the trap: adopting `assert_challenge_mode` as a *refusal* would break ingestion of the retained standard-mode truth save, which `tests/test_cross_mode_format.py:119` pins and `tests/test_read_only.py:258-266` parses on every gamedata run. Report, never refuse.

### 'What does this save already hold?' is useful here and is claimed by `incremental-loading`, so the boundary needs writing down in both requests

**Scopers:** fit, ambitious, minimalist

All three flagged the same overlap against the same line of the neighbouring request. Convergence on a *boundary* rather than on a feature is the shape that most reliably produces either duplicated work or a dropped capability, and none of the three felt authorised to draw it — which is precisely what makes it a gated decision rather than a fold.

### Module placement is a real decision CLAUDE.md forbids defaulting, and two of three recommend promoting `ingest.py` to a package

**Scopers:** ambitious, minimalist, fit

Ambitious and minimalist independently recommended `ingest/__init__.py` + `ingest/__main__.py` and independently verified import-transparency (I count ten `from ootp_ai.ingest import ...` sites, all unaffected). Fit dissented toward `warehouse/__main__.py` on the grounds that promotion churns tests and docs. The minimalist supplied the decisive technical reason neither other scoper had: running a plain module under `-m` double-imports it under two names, producing two distinct `IngestRun`/`ParsedSnapshot` classes and a silent `isinstance` hazard across the boundary with `warehouse/load.py:90`.

## Adversary summaries

### `fit-ac`

I resolved every file, line range, function and constant the merged scope cites. The repo-fit verdict is mostly accurate and unusually well grounded — `reports/__main__.py:36-59`, `catalog/__main__.py:82-115`, `ingest.py:436/481-501`, `snapshot.py:146-216/254-269`, `warehouse/load.py:169-250/287-317`, `warehouse/ingest_run.py:137-268`, `config.py:71-148/215-238`, `reports/resolve.py:78-187`, `tests/test_read_only.py:25-28/182-269/294-372`, `tests/fixtures/warehouse.py:19-26/93/133-157`, `README.md:117-118/128-134` and `tests/test_no_leaks.py:31-41` all resolve and say what the scope says they say. The three convergence findings hold under verification: `_writes_in()` is a source-text scan so no `WRITERS` entry is needed; `ensure_tables` really has exactly one caller and `ops/mysql-bootstrap.sql` really creates three databases, one user and zero tables; `take_snapshot` really auto-allocates and never raises with `ingest_seq=None`. `var/snapshots` holds exactly the three directories named. Ten `from ootp_ai.ingest import` sites confirmed. Two existing `__main__` entry points confirmed; no `[project.scripts]`.

Four things break. (1) The headline recommendation — refuse a second landing at an already-landed `(save_id, sim_date)` by default — is the exact design ADR 0021 §Context:21-27 calls "worse, because it blocks a legitimate and frequent operation", and inverts the second half of the request's own Desired Outcome bullet (`FEATURE_REQUEST.md:62-64`), which the scope quotes with that half cut off while asserting "A is the request's own words" and "exposed, not renegotiated". A defensible option, argued dishonestly, in a repo whose rule is that a contradiction must be stated. (2) Three acceptance criteria are not runnable as written — AC12 needs a schema with no declared tables and there is no isolation seam (`db.py:42` binds one database; the app user is granted only three named schemas), AC1 asks for a git-diff of a constant inside a file core deliberately edits, and AC7's `resolve.py` clause becomes true with no code change. (3) No automated criterion anywhere asserts `main()` returns 0 — and the non-goal that forbids `--snapshot-root`, combined with `main()`'s un-injectable `load_settings()`, is what makes that hole structural rather than incidental. (4) Two core mechanisms are specified against API that does not exist or does not fit: `snapshot._read_sim_date` is private and absent from `__all__`, and the shared function is asked to carry an `ingest_seq` argument it has no landing step to spend it on. Plus one measured number is stale: the snapshot is 52.4 MiB on disk (snapshot.py:65 and test_snapshot_semantics.py:399 both say ~55 MB), not the "~46 MB" the scope repeats five times.

### `scope-completeness`

Attacked the merged scope from both sides against the tree at `3c46111`. **On over-reach:** the scope is mostly disciplined — the `--dry-run`, `--snapshot-root`, `--save all`, free-disk, exit-code-3 and confirmation-gate drops are all correctly argued, and the three convergence findings (no `WRITERS` entry, `ensure_tables` has one caller, naive composition auto-allocates) I re-verified independently and they hold. But two "cheap folds" are not cheap: `--json` carrying per-table digests means `table_digest` (`warehouse/load.py:540-572`) fetches and hashes ~301,000 rows row-by-row as a second full pass over the landing, and the dual-allocator print calls `warehouse.ingest_run.next_ingest_seq` in direct contradiction of its own docstring ("**Must be called inside the transaction that will insert the row**", `:140-143`). **On blind spots, two findings matter more than any creep:** (1) the recommended re-run default (Option A: refuse by `(save_id, sim_date)`) is the exact design ADR 0021 §Context lines 21-27 names and rejects — *"The obvious fix — key on `(save_id, sim_date)` and refuse a re-land — is worse, because it blocks a legitimate and frequent operation"* — and it also inverts the request's own Desired Outcome bullet 4, yet `fit_verdict` asserts "No ADR is contradicted" and calls the semantics "exposed, not renegotiated"; CLAUDE.md requires a scope that diverges from an accepted ADR to say so. (2) Core's fail-fast pre-flight reads the **live save's** `teams.dat` through `snapshot._read_sim_date` (`snapshot.py:292-293`) from the CLI, *outside* the shared function AC11 brackets — so the command touches the game in a code path ADR 0001's manifest diff never covers, while AC13 claims the opposite. Also: the "one shared function, three callers" item silently merges two genuinely different compositions (`ingest_save`+parse vs `take_snapshot`+parse), and routing the fixture through `ingest_save` adds ~46 MB of re-reads (`ingest.py:494`) to the setup of a *timing* harness (`tests/test_extraction_cost.py:75`); AC14's regression module list is wrong in both directions; and AC6 proposes a fourth string-pinned source scan — the precise anti-pattern the open `tree-seam-for-remaining-guards` request exists to fix.

## Findings

### [BLOCKER] A1 — The recommended re-run default contradicts ADR 0021's stated decision and the request's own Desired Outcome, and the scope claims the opposite

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** framing · **Location:** gated_decisions[0] recommendation; fit_verdict.rationale ("ADR 0021's append-only semantics are *exposed*, not renegotiated"); vs docs/decisions/0021-bronze-landing-is-append-only.md:21-27 and :46-49; vs requests/feature-requests/ingest-command/FEATURE_REQUEST.md:62-65

**Problem:** Option A refuses a second landing keyed on `(save_id, sim_date)` unless an override flag is passed. ADR 0021 §Context:21-27 addresses that exact design by name and rejects it: "The obvious fix — key on `(save_id, sim_date)` and refuse a re-land — is worse, because it blocks a legitimate and frequent operation. The operator executes a GM action on 2024-03-07, signs a free agent, and wants to prove it landed. **The sim date has not moved.**" §Decision part 2 (:46-49) then states the positive rule: "A new look at an already-ingested `sim_date` allocates the next `ingest_seq` and lands a fresh row set alongside its predecessor." The request says both halves in one sentence at :62-64 — "Re-landing an already-landed triple still refuses loudly, **and a second look at an unchanged sim date still takes the next `ingest_seq`**". The scope's recommendation quotes only the first clause and concludes "A is the request's own words", while the fit rationale asserts nothing is renegotiated and the verdict stays "clean". Worse, the option the scope tells the operator to "reject outright" (C) is the behaviour ADR 0021 part 2 prescribes. There is a real argument for A — accidental habitual re-runs cost ~55 MB and ~301,000 unreclaimable rows, which risks[0] makes well — but it is an argument for changing an operator-facing default the ADR settled, and the scope must say that out loud. The task's own rule and CLAUDE.md's "Decisions already made — do not re-propose" both require it.

**Proposed fix:** Rewrite gated decision 1 to open with: "Option A diverges from ADR 0021 §Decision part 2 and from this request's Desired Outcome bullet 4, both of which say an unchanged sim date takes the next sequence. It is proposed anyway because ADR 0021 was written about a deliberate operator act and this is about a habitual keystroke." Quote the request's full sentence including the dropped clause. Re-label Option C as "what ADR 0021 and the request both currently specify" rather than "what naive composition does", and give it the same fair hearing as A and B. Amend fit_verdict.rationale to say the CLI default diverges from the ADR's default while the library semantics are untouched, and note in the plan that if A ships, ADR 0021 needs a dated amendment or a note recording that the command's default is stricter than the storage rule.

### [BLOCKER] A2 — AC12 (the command creates the schema it lands into) has no runnable mechanism and would destroy retained landings

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[11]; src/ootp_ai/db.py:40-42; ops/mysql-bootstrap.sql; requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:144-146

**Problem:** AC12 requires running the command "against a schema holding none of the declared tables". There is no seam that produces one. `connect_warehouse` binds `settings.mysql.database` and nothing else (`db.py:40-42`); `Settings.mysql` is a single `MySQLSettings` with one `database` field (`config.py:87-96`); the app user is granted privileges on exactly `ootp`, `ootp_dev` and `ootp_truth_real` (`ops/mysql-bootstrap.sql`) with no global rights, so a test cannot create a throwaway schema. The only way to satisfy the precondition is to DROP the eight declared tables from the configured dev schema — which destroys the landings behind `var/snapshots/OOTP-AI/2024-03-07/1`, described in `handoff-phase-8b.md` as the first ingest, and which no fixture in `tests/fixtures/warehouse.py` does (it deletes rows, never tables). It would also be a `DROP` written into the test suite immediately after ADR 0021 §Decision part 3 banned one in `src/`. As written the criterion cannot be run by the acceptance panel and cannot be run safely by anyone.

**Proposed fix:** Split it. Offline half: assert the ordering, not the outcome — monkeypatch `warehouse.load.ensure_tables` in the command module with a spy and assert it is called exactly once, before `take_snapshot`, on a `land` invocation whose later stages are stubbed. That is a one-command pass/fail. End-to-end half: it is already AC15's, which starts from "a machine whose warehouse holds no `bronze_*` tables" and is correctly marked USER-RUN. Delete the gamedata version, or if an automated end-to-end proof is genuinely wanted, scope the `.env`/grant work to give tests their own schema and say so as a cost.

### [BLOCKER] SC-01 — The recommended re-run default is the design ADR 0021 explicitly rejects, and the scope asserts no ADR is contradicted

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** framing · **Location:** gated_decisions[0] (Option A, recommended) + fit_verdict.rationale ("No ADR is contradicted" / "exposed, not renegotiated"); vs docs/decisions/0021-bronze-landing-is-append-only.md:21-27 and :46-49

**Problem:** ADR 0021 §Context is unambiguous: *"The obvious fix — key on `(save_id, sim_date)` and refuse a re-land — is **worse**, because it blocks a legitimate and frequent operation. The operator executes a GM action on 2024-03-07, signs a free agent, and wants to prove it landed. **The sim date has not moved.**"* Option A makes exactly that refusal the operator-facing default and demotes the ADR's own motivating case to a flag. §Decision part 2 states the unqualified rule the other way: *"A new look at an already-ingested `sim_date` allocates the next `ingest_seq` and lands a fresh row set alongside its predecessor."* The request's Desired Outcome bullet 4 (FEATURE_REQUEST.md:62-64) says the same: *"a second look at an unchanged sim date **still** takes the next `ingest_seq`."* The scope's own summary quotes the request's other half ("re-landing an already-landed triple still refuses loudly") as if it authorised Option A — but the triple the ADR and the request both mean is `(save_id, sim_date, ingest_seq)`, not `(save_id, sim_date)`. Meanwhile `fit_verdict` asserts "No ADR is contradicted" and "ADR 0021's append-only semantics are *exposed*, not renegotiated". CLAUDE.md: "A scope that contradicts an accepted ADR must say so explicitly rather than quietly diverging."

**Proposed fix:** Either (a) keep Option A but rewrite `fit_verdict` to say plainly that the CLI default is deliberately stricter than the library behaviour ADR 0021 prefers, name the ADR passage it departs from, and record that the ADR's motivating case (free agent signed without simming) now requires a flag — and pick a flag name that reads naturally for it (`--new-look` matches the ADR's own vocabulary far better than `--again`); or (b) adopt Option B (digest pre-flight), which is the only option that honours both ADR clauses — identical bytes are a no-op and refuse, changed bytes at an unchanged date land the next sequence automatically, which is exactly the ADR's case; or (c) adopt C with a loud warning line. Whichever ships, the gated question must present Option A as an ADR-level divergence rather than as "the safe half of ADR 0021".

### [BLOCKER] SC-02 — The pre-flight reads the live save from a code path ADR 0001's manifest diff does not bracket, while AC13 claims it does

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** risk · **Location:** tiered_scope.core ("Fail-fast ordering ... pre-flight ... -> snapshot + parse") and acceptance_criteria[12] ("ADR 0001's proof brackets the operator's path"); snapshot.py:285-293; tests/test_read_only.py:222-269

**Problem:** Core puts the sim-date pre-flight in the command, before the shared function runs, and its justification is that `snapshot._read_sim_date` can get the date cheaply. But `_read_sim_date` reads `save.path / "teams.dat"` — the **live save**, ~5 MB, in the game's own directory (`snapshot.py:292-293`). The shared function AC11's three legs bracket is snapshot + parse only. So under core as written, the operator's command opens a file under `$OOTP_SAVED_GAMES` in code that ADR 0001's manifest diff never covers. It is a read and therefore harmless today, but it is precisely the class of contact AC11 exists to prove absent, and the request's open question 5 asked about exactly this seam. Goal 3 ("the operator's path is the path ADR 0001's manifest diff brackets") and AC13 both overclaim: the diff brackets a function the command calls, not the command, and there is now game-touching code between them.

**Proposed fix:** Move the pre-flight's sim-date read inside the shared bracketed function — have it return the sim date (or a small pre-flight result) before deciding, so every read of the game directory sits inside AC11's three legs. Then restate goal 3 and AC13 accurately: "every game-touching line the command executes is inside the manifest diff; the argparse, settings, warehouse-connection and landing halves are outside it and touch no game file." If the pre-flight stays in the CLI, the scope must say so and say that it is an uncovered game read.

### [MAJOR] A3 — No automated criterion ever asserts that the command itself succeeds — and the non-goal forbidding --snapshot-root is what makes that structural

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[8] ("calls the command's library function"), [12], [14]; non_goals[7]; src/ootp_ai/reports/__main__.py:40; tests/test_read_only.py:182-193; tests/test_catalog.py:172-183

**Problem:** Every criterion that exercises a real landing deliberately routes around `main()`: AC9 "calls the command's library function", AC13 calls the shared function, AC5 monkeypatches `land_snapshot` so `main()` only ever returns 1 or 2. The single place `main([...]) == 0` is proved is AC15, which is USER-RUN. So the exit-0 path of the artifact this whole request exists to create — argument parsing, target resolution, `ensure_tables`, pre-flight, ordering, the stdout block — is never proved by a test. The non-goal that forbids `--snapshot-root` closes the obvious workaround: `main()` resolves settings through a bare `load_settings()` (the pattern at `reports/__main__.py:40`), so a gamedata test calling `main(["land", "--save-id", <probe>])` writes into the configured `snapshot_root`, accreting ~52 MB and burning a filesystem sequence on every run — precisely the accretion `tests/test_read_only.py:186-188` redirects to avoid. The precedent cuts the other way: `tests/test_catalog.py:172-183` drives `main()` end to end for exactly this reason ("a test that called `render_markdown` directly would prove the renderer works while the command stayed broken"). This is a non-goal quietly burying a hard part.

**Proposed fix:** Name the injection seam in scope rather than leaving it to the plan: `main(argv)` resolves settings then delegates to a testable `land(settings, *, save_id=None, snapshot_root=None)`, and add a gamedata criterion that monkeypatches `load_settings` in the command module to return `replace(settings, snapshot_root=tmp_path)`, calls `main(["land", "--save-id", <probe>])`, asserts it returns 0, and parses the triple out of `capsys` stdout. That keeps `--snapshot-root` off the CLI (the non-goal survives intact) while making the command's success path a pytest assertion instead of a human's.

### [MAJOR] A4 — The pre-flight depends on a private function, and lives outside the shared function AC11 brackets — contradicting goal 3

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** fit · **Location:** tiered_scope.core ("Fail-fast ordering", "Sim-date pre-flight before the copy"); goals[2]; src/ootp_ai/snapshot.py:52-63 (__all__) and :285-293; grounding_pointers

**Problem:** Two problems in one mechanism. First, `_read_sim_date` is private and absent from `snapshot.__all__` (which lists `SIM_DATE_SOURCE`, `SNAPSHOT_FILES`, `Snapshot`, `SnapshotCorrupt`, `SnapshotExists`, `SnapshotFile`, `next_ingest_seq`, `read_manifest`, `take_snapshot`, `verify_snapshot` — `snapshot.py:52-63`). The scope cites it four times as available API and never notes that it must be promoted, which understates the change surface in a repo where `reject_inside_game_roots` needed a documented "public since Phase 11, and that is the point" note to go public (`config.py:225`). Second, `_read_sim_date` opens the save's own `teams.dat` (5.3 MB, `snapshot.py:292-293`), so the pre-flight is a game-touching step that sits in the command, outside the shared function — which directly contradicts goal 3's claim that the shared function makes "the operator's path the path ADR 0001's manifest diff brackets", and non_goals[6]'s refusal to add a fourth AC11 leg means nothing will bracket it. ADR 0001 is not violated (a read changes no size, mtime or digest), but the property the scope advertises is not the property it delivers.

**Proposed fix:** State that `_read_sim_date` is promoted to public API with a docstring saying why (it is the only cheap answer to "what date would this land at?" before 52 MB is copied), and add it to `snapshot.__all__`. Then either move the pre-flight inside the shared function so AC11 genuinely brackets every game read, or amend goal 3 to say the shared function brackets the copy and the parse while the pre-flight's single header read is knowingly outside the diff — and say which.

### [MAJOR] A5 — The shared function as specified re-introduces ~50 MB of I/O per run that ingest._describe's payload parameter exists to eliminate

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** fit · **Location:** tiered_scope.core ("One shared game-touching function composing `ingest_save` and `parse_snapshot`"); src/ootp_ai/ingest.py:459 vs :202 and :488-491; tests/fixtures/warehouse.py:151

**Problem:** `ingest_save` calls `_describe(snapshot, entry, None)` for every snapshot file (`ingest.py:459`), and with `payload=None` `_describe` re-reads the whole file to look at its header (`:494`). `parse_snapshot` then reads the same four files again for the walk (`:174`) and passes the buffers in (`:202`) precisely so the header read is free. `_describe`'s own docstring records the cost: "Re-reading the four parsed files here to look at 25 bytes of header cost ~48 MB of avoidable I/O per ingest" (`:488-491`). `ingest_save(...)` followed by `parse_snapshot(...)` therefore reads the full snapshot set roughly twice — which is what `tests/test_read_only.py:254` does today, deliberately, because AC11 wants the biggest possible read surface inside its diff. But `tests/fixtures/warehouse.py:151` composes `parse_snapshot(take_snapshot(...))` and never calls `ingest_save`, avoiding it entirely. Re-pointing the fixture onto an `ingest_save`-based shared function silently adds ~50 MB of reads to roughly ten gamedata tests across three modules, for no functional gain: `parse_snapshot` rebuilds `save_id`, `sim_date`, `ingest_seq`, `human_team_id` and `sources` itself (`:195-214`), so `ingest_save`'s return value is discarded except for `.snapshot`.

**Proposed fix:** Specify the composition as `parse_snapshot(take_snapshot(save, snapshot_root=..., ingest_seq=None))` — the fixture's existing shape, which loses nothing because `parse_snapshot` recomputes the whole run — and re-point AC11's three legs onto that. If instead the `ingest_save` composition is kept because AC11 wants the double read inside its bracket, say so explicitly, and add the measured per-run I/O delta for the fixture path to the plan so the slowdown is a decision rather than a side effect.

### [MAJOR] A6 — The shared function is given an ingest_seq argument it has no landing step to spend — conflating the filesystem and warehouse allocators

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** scope-creep · **Location:** tiered_scope.core ("It must take `snapshot_root` and `ingest_seq` as library keyword arguments"); risks[4]; src/ootp_ai/warehouse/load.py:203-217; tests/fixtures/warehouse.py:19-26

**Problem:** The shared function stops before landing — that is forced, because AC11's legs call it and `test_read_only.py:240-242` refuses to pull MySQL inside ADR 0001's diff. So the only `ingest_seq` it could accept is `take_snapshot`'s filesystem sequence (`snapshot.py:171`). But the stated justification is the fixture's need, and the fixture's need is the opposite parameter: `land_snapshot(..., ingest_seq=None)` (`tests/fixtures/warehouse.py:152`, whose module docstring at :19-26 explains that a temp directory always allocates 1 on the filesystem side so the *warehouse* must allocate instead). `load.py:203-217` draws exactly this distinction. The scope's own risks[4] warns that letting the CLI's explicit-sequence policy travel with the shared function would make `landed_probe` collide at seq 1 and surface as `IngestRunExists` in unrelated grain tests — and then core specifies the parameter that invites it.

**Proposed fix:** State the split explicitly in core: the shared function takes `snapshot_root` only; `ingest_seq` is never its parameter. The sequence decision belongs to whoever calls `land_snapshot` — the CLI passes `parsed.run.ingest_seq` explicitly because its snapshot is durable, `landed_probe` passes `None` because its snapshot is transient — and both reasons are already written in `load.py:203-217`. Add a criterion asserting `landed_probe` still lands with `ingest_seq=None` after the re-point, so the risk cannot materialise silently.

### [MAJOR] SC-03 — "One shared game-touching function, three callers" merges two different compositions and adds ~46 MB of re-reads to a timing harness

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** completeness · **Location:** tiered_scope.core (shared function item) and acceptance_criteria[5]; tests/test_read_only.py:254,263,268 vs tests/fixtures/warehouse.py:151; ingest.py:459 and :494; tests/test_extraction_cost.py:75

**Problem:** The two callers being unified do not do the same thing. AC11 runs `parse_snapshot(ingest_save(...).snapshot)`; the fixture runs `parse_snapshot(take_snapshot(save, snapshot_root=Path(tmp)))` and deliberately never calls `ingest_save`. `ingest_save` builds `sources=tuple(_describe(snapshot, entry, None) ...)` (`ingest.py:459`), and `_describe` with `payload=None` re-reads each snapshot file **whole** to read 25 bytes of header (`ingest.py:494`) — the module's own docstring at `:488-492` measures this as "~48 MB of avoidable I/O per ingest". Routing the fixture through a shared function that goes via `ingest_save` therefore adds a full extra read of the snapshot to every `landed_probe` use — including `tests/test_extraction_cost.py:75`, a module-scoped fixture feeding a **cost/timing** harness that compares recorded `parse_seconds` against a re-parse with `DRIFT_FACTOR = 10.0`. The scope notices the discrepancy in `grounding_pointers` ("note it composes `parse_snapshot(take_snapshot(...))` at :151 and does **not** call `ingest_save`, which constrains the shape") but core and AC6 never resolve it.

**Proposed fix:** Settle it in scope: the shared function is `take_snapshot` + `parse_snapshot` (the fixture's existing, cheaper shape), and AC11's three legs move onto it. State that the per-file header/version guard still fires, because `parse_snapshot` calls `_describe` with the loaded buffers (`ingest.py:202`), so nothing is lost. Also state that `ingest_save` keeps a caller — `tests/test_provenance.py:231` — so it is not orphaned by the move.

### [MAJOR] SC-04 — AC14 names the wrong module set for the fixture re-point regression, omitting the two riskiest consumers

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[13]; grep of `landed_probe` importers: tests/test_extraction_cost.py:39, tests/test_parser_vs_export.py:56, tests/test_grain_contracts.py:65, tests/test_snapshot_semantics.py:65

**Problem:** AC14 asserts `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_bronze_landing.py` is green with the re-pointed `landed_probe`. `tests/test_bronze_landing.py` exists but does not import `landed_probe` — it is not a consumer. The two actual consumers AC14 omits are the ones most likely to break: `tests/test_extraction_cost.py` (a timing harness whose module-scoped fixture wraps `landed_probe`, see SC-03) and `tests/test_parser_vs_export.py:130`, which calls `landed_probe(..., which="truth_save")` and is the Tier-B export diff — the one gamedata module that lands the *standard-mode* save. A re-point that changed the fixture's behaviour would surface there first, and the criterion would not catch it.

**Proposed fix:** Rewrite AC14 against the real consumer list: `tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py`. Add an explicit sub-clause that `test_parser_vs_export.py`'s `which="truth_save"` path still works, since the shared function must keep the `which`-selectable, non-managed target the fixture depends on.

### [MAJOR] SC-05 — AC6 proposes a string-pinned source scan — the exact anti-pattern an open request exists to fix — and cannot prove what it claims

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[5]; requests/feature-requests/README.md Index row `tree-seam-for-remaining-guards` (line 119); docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md

**Problem:** AC6 asks for "a source-text assertion ... that the command module, `tests/test_read_only.py` and `tests/fixtures/warehouse.py` all import the shared function, and that `tests/fixtures/warehouse.py` no longer spells `parse_snapshot(take_snapshot(...))` by hand." The repo has an **open intake request specifically about this failure mode**: `tree-seam-for-remaining-guards` records that the existing scans are "pinned against strings, which tests the rule and not the enumeration; a mutant returning zero files leaves both green, which is the exact shape that shipped broken three times here." AC6 adds a fourth instance of it. It also does not prove its claim: a module can import a name and never call it, and "no longer spells X by hand" is satisfied by any refactor that renames the local. The scope's precedent argument ("the repo already scans its own sources in test_read_only.py, test_no_leaks.py and test_no_fixed_offsets.py") cites the very guards that request was filed against.

**Proposed fix:** Replace AC6 with a behavioural criterion: monkeypatch the shared function to record its arguments, then assert that (a) the command's library function and (b) `landed_probe` both route through it — a real call, not a string. If that is judged too heavy, drop AC6 entirely: a shared function that the fixture imports is visible in the diff and enforced by the gamedata suite going green, and a guard that cannot fail is worse than no guard here by the repo's own standard.

### [MAJOR] SC-06 — `--json` with per-table digests is not a cheap fold — it adds a full second pass over ~301,000 landed rows

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** scope-creep · **Location:** tiered_scope.cheap_folds (`--json` item) and above_and_beyond entry "A `gm/decisions/`-pasteable citation block with per-table digests" ("Fold the digests into the `--json` object"); warehouse/load.py:540-572

**Problem:** `table_digest` runs `SELECT <every column> ... ORDER BY <declared key>` for one triple and then `for row in cursor.fetchall(): hasher.update(json.dumps(row, sort_keys=True, default=str)...)`. Over the eight declared tables for one landing that is ~301,000 rows fetched into Python and JSON-serialised individually, 264,095 of them `bronze_name` (ADR 0021 §Consequences). That is a second full read of everything the landing just wrote, in the same process, on the operator's most frequent command — and the scope labels it a fold and even calls the citation-block entry "Cheap". Nothing in the scope estimates its cost, and unlike the `verify_snapshot` fold it carries no instruction to measure.

**Proposed fix:** Split the fold. Keep `--json` as the triple + per-table row counts + per-file residual bytes + `parse_seconds` (all already in hand on the returned `IngestRun`, zero extra queries). Move per-table digests to `gated`, with the note that they cost a full re-read of the landing and that `table_digest` already exists for whoever wants them later. If digests stay, add a criterion requiring the added seconds be measured and recorded, as the `verify_snapshot` fold does.

### [MAJOR] SC-07 — The dual-allocator fold calls `next_ingest_seq` in direct contradiction of its own documented contract

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** risk · **Location:** tiered_scope.cheap_folds ("Print both sequence allocators when they disagree"); warehouse/ingest_run.py:137-153

**Problem:** `warehouse.ingest_run.next_ingest_seq`'s docstring is explicit: *"**Must be called inside the transaction that will insert the row.** `FOR UPDATE` is what makes it safe against a concurrent loader, and a lock taken in a transaction that has already committed protects nothing."* The fold calls it purely to print a comparison, outside any landing transaction. That takes a gap lock in a stray transaction for a display value, and — worse — a reader who later sees the call will reasonably conclude the invariant is soft. The module's own header records that this repo already got the locking semantics of this function wrong once (`ingest_run.py:16-35`, and CLAUDE.md's "One MySQL belief that was wrong" section).

**Proposed fix:** Either drop the fold, or specify that the display value comes from a plain `SELECT COALESCE(MAX(ingest_seq),0) ... WHERE save_id=%s AND sim_date=%s` written in the command (no `FOR UPDATE`, no transaction claim) and say in the scope that `next_ingest_seq` is deliberately not reused for display. Note the pre-flight already needs this query, so the fold is nearly free if it reuses the pre-flight's result rather than the allocator.

### [MAJOR] SC-08 — AC2 pins a required subcommand against the repo's own precedent for a one-verb command, without arguing it

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** scope-creep · **Location:** acceptance_criteria[1] (`parse_args(["land"]).command == "land"`, `main([])` exits 2); src/ootp_ai/catalog/__main__.py:3-5

**Problem:** The scope treats `reports/__main__.py` as "the pattern" and mandates its required-subcommand shape. But `catalog/__main__.py` — the *second* instance of the pattern, and the one the scope itself cites as precedent elsewhere — argues the opposite in its opening lines: *"**No subcommand, deliberately.** Acceptance criterion 15 names this exact invocation, and `reports` takes a subcommand because it will grow more than one verb. This command has one job and adding `generate` to it would only make the criterion's command longer."* With `status` (gated 5, recommended: neither request builds it) and `--from-schema`/`--from-snapshot` (gated 4) both outside core, `land` is the only verb this command will ever have in v1. AC2 hard-pins the invocation string, and the scope's own risk section says that string is what `incremental-loading` will write its procedure against — so it is exactly the wrong thing to settle by pattern-matching.

**Proposed fix:** Make the subcommand a gated decision alongside module placement (they compose into one invocation string), and present the catalog docstring's argument on the no-subcommand side. If the subcommand stays, say why this command is expected to grow verbs where the catalog was not — most plausibly because gated 4 and 5 both name candidate verbs. Then AC2 pins whichever was decided.

### [MAJOR] SC-09 — Core depends five times on a private helper, and no scope item authorises promoting it

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** completeness · **Location:** tiered_scope.core ("Fail-fast ordering", "The append-only surface"), above_and_beyond ("Sim-date pre-flight before the copy"), gated_decisions[0]; snapshot.py:285-293 and snapshot.py:50-63

**Problem:** The pre-flight — which the scope promotes into core because it is "the mechanism that makes the append-only default reachable at all" — rests on `snapshot._read_sim_date`. That function is private by name and is not in `snapshot.__all__` (`:50-63`). Reaching into it cross-module is the kind of thing the plan stage will either do quietly (adding a private cross-module dependency to the operator's most-run path) or discover late and have to decide under time pressure. The non-goals explicitly forbid a ninth table, a contract edit and a parser change, but say nothing about the `snapshot` module's public surface.

**Proposed fix:** Add to core: "promote `_read_sim_date` to a public `read_sim_date` and add it to `snapshot.__all__`; it becomes the pre-flight's only game read." That is a one-line API addition, it is the honest shape, and it pairs naturally with SC-02's fix of moving the read inside the bracketed function.

### [MAJOR] SC-10 — The explicit-sequence policy plus a disposable var/ produces an off-by-N first landing the scope names only in the opposite direction

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** risk · **Location:** risks[1] ("Two independent sequence allocators"); tiered_scope.core ("Sequence policy stated rather than defaulted"); measured: var/snapshots/OOTP-AI/2024-03-07/1 exists on disk; snapshot.py:146-164

**Problem:** The scope's risk names one direction: an empty `var/` gives filesystem seq 1 while the warehouse already holds 1, so the run refuses. The other direction is the one that is true on this machine right now and it is not named. `var/snapshots/OOTP-AI/2024-03-07/1` exists (verified by directory listing). If the warehouse holds nothing for `(OOTP-AI, 2024-03-07)` — a fresh schema, a different `MYSQL_DATABASE`, a re-bootstrapped dev database — then the pre-flight passes, `take_snapshot` allocates filesystem seq **2**, and the operator's very first landing lands at `ingest_seq = 2` with no seq 1 in the warehouse. A later reader applying ADR 0021's "`ingest_seq` is a monotonic integer per `(save_id, sim_date)` **starting at 1**" (:48) reads that gap as a lost landing. The scope also leans on the filesystem allocator to preserve the snapshot/warehouse correspondence while `var/` is documented as disposable and gitignored (CLAUDE.md: "`var/` holds only what rebuilds from the save" — which a snapshot notably does not, because the save moves on).

**Proposed fix:** State both directions in the risk. Then decide in scope how the command reconciles: either allocate `max(filesystem, warehouse) + 1` and print the reasoning line when they disagreed, or keep the filesystem sequence and print an explicit "filesystem allocated N, warehouse holds M" line. Run the `SELECT save_id, sim_date, MAX(ingest_seq) FROM ingest_run GROUP BY 1,2` the scope already recommends, and record the answer in the scope so the plan starts from `measured` rather than `inferred`.

### [MINOR] A7 — The ~46 MB snapshot figure is stale by ~14%; measured, it is 52.4 MiB

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** completeness · **Location:** summary, fit_verdict, tiered_scope.core, risks[0], gated_decisions[3], above_and_beyond (six occurrences of "~46 MB"); vs src/ootp_ai/snapshot.py:65, tests/test_snapshot_semantics.py:399, tests/test_read_only.py:186-187

**Problem:** Measured on this machine: `var/snapshots/OOTP-AI/2024-03-07/1` holds `players.dat` 32,070,091 + `world.dat` 8,898,534 + `names.dat` 8,642,110 + `teams.dat` 5,326,632 + `human_managers.dat` 835 + manifest = 52.4 MiB (54.9 MB). The repo's own two current statements agree: `snapshot.py:65` says "~55 MB against a ~600 MB `.lg`" and `tests/test_snapshot_semantics.py:399` says "~55 MB across the set". The scope's "~46 MB", used six times including in the cost argument that drives the headline gated decision, comes from `tests/test_read_only.py:186-187`, which is itself stale — 46 MB is exactly the set before `world.dat` (8.9 MB) joined `SNAPSHOT_FILES` on 2026-08-16 (`snapshot.py:70-76`). A scope that instructs the reader to verify every path should not inherit a number from the one place in the repo that still carries the pre-widening figure.

**Proposed fix:** Replace every "~46 MB" with "~55 MB (measured 52.4 MiB for the managed league's landed snapshot)". Add a line to the docs-truth item in core: `tests/test_read_only.py:187`'s "46 MB directory per run" is stale and should be corrected in the same change, since `/update-docs` is a commit gate here anyway.

### [MINOR] A8 — AC1's "a diff of that constant against main is empty" is not a one-command pass/fail, and core makes the file diff non-empty by design

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[0]; tiered_scope.core ("`tests/test_read_only.py`'s three AC11 legs re-pointed ... with the docstring updated"); tests/test_read_only.py:303-317

**Problem:** Core explicitly edits `tests/test_read_only.py` — three call sites and the AC11 docstring — so `git diff main -- tests/test_read_only.py` is non-empty by construction. The criterion asks for a diff scoped to "that constant", which no single command produces; a cold agent would have to eyeball a hunk and judge whether the `WRITERS` lines moved, which is exactly the "a human eyeballs a number and nods" shape `requests/feature-requests/README.md:70-81` rules out.

**Proposed fix:** Make it an assertion. In the new `tests/test_ingest_command.py`: `from tests.test_read_only import WRITERS` then `assert WRITERS == {"snapshot.py", "reports/__main__.py", "catalog/__main__.py"}`, with a comment saying the new entry point is deliberately absent because `_writes_in` scans a module's own source text. That is one command, binary, and it stays true across the docstring edit.

### [MINOR] A9 — AC2's "main([]) exits 2" is imprecise — argparse raises SystemExit, it does not return

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[1]; src/ootp_ai/reports/__main__.py:130 (`sub.add_subparsers(dest="command", required=True)`)

**Problem:** With `required=True`, argparse calls `parser.error()` on a missing subcommand, which prints usage and raises `SystemExit(2)` from inside `_parser().parse_args(argv)` — before `main` can return anything. A test written literally against "`main([])` exits 2" (e.g. `assert main([]) == 2`) fails with an uncaught `SystemExit`, and an implementer may wrongly conclude the surface is broken and add a `try/except SystemExit` that swallows real argparse errors.

**Proposed fix:** Restate as: `with pytest.raises(SystemExit) as exc: main([])` then `assert exc.value.code == 2`. Same for any other criterion phrased as a return where argparse is the raiser.

### [MINOR] A10 — AC7's resolve.py clause is unmeasurable — the existing message becomes true with no code change

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[6] ("`src/ootp_ai/reports/resolve.py` no longer points the operator at a non-existent ingest"); goals[8]; src/ootp_ai/reports/resolve.py:179-182

**Problem:** The message today is "no landing exists for save {save_id!r}. The warehouse holds no ingest_run row for that universe at any date — run the ingest before rendering" (`resolve.py:179-182`). Once the command ships, that sentence is simply true. There is no string to remove and no objective check for "no longer points at a non-existent ingest" — a cold agent cannot turn it into a pass or a fail. The underlying intent is good (the refusal should name the actual invocation) but the criterion does not express it.

**Proposed fix:** Restate as an assertion on content: an offline test builds `_nothing_landed_message` against a stub connection returning no dates and asserts the returned string contains the literal invocation the command ships with (the same literal AC7 already requires in `README.md`), so the two cannot drift. That also makes the refusal actionable in the way `_nothing_landed_message`'s own docstring (`:171-175`) says it should be.

### [MINOR] A11 — The no-absolute-path rule covers only the success block; the ConfigError path prints absolute paths today

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** completeness · **Location:** goals[5]; acceptance_criteria[3]; src/ootp_ai/config.py:234-238 and :265-269; src/ootp_ai/reports/__main__.py:42

**Problem:** AC4 tests only the success formatter. The error path the scope adopts verbatim from `reports/__main__.py:42` is `print(f"configuration: {error}", file=sys.stderr)`, and two `ConfigError` messages embed absolute paths: `reject_inside_game_roots` interpolates `{game_root}` (`config.py:235`) and `_check_never_tracked` interpolates `{root}` (`config.py:266`). Both are reachable from `load_settings()`. An operator pasting a *failed* run into a `gm/decisions/` note or a bug report is at least as likely as pasting a successful one, and `tests/test_no_leaks.py` scans `.md` for exactly that drive-letter shape (`:38`). The scope asserts the rule as a stated, tested divergence from `reports/__main__.py:57-58` and then leaves half of it untested and unmentioned.

**Proposed fix:** Decide it in scope and say which: either (a) the rule is stdout-only and stderr is exempt because a misconfiguration message must name the offending path to be actionable — state that, and note the two `ConfigError` messages that carry one so nobody later 'fixes' them; or (b) extend AC4 to the error formatter with those two exceptions documented. Either way the sentence belongs in goals[5], which currently reads as an unqualified rule.

### [MINOR] A12 — risks[9] misstates where ingest.py is referenced: CLAUDE.md's map does not name it, and the handoffs must not be rewritten

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** fit · **Location:** risks[9] ("this request itself cites `src/ootp_ai/ingest.py:436`, CLAUDE.md's project map names the file, and `.claude/agents/data-engineer-memory.md` and several `first-sight` handoffs carry stale references"); CLAUDE.md project map; .claude/agents/data-engineer-memory.md:202

**Problem:** Verified: the only tracked reference to `ingest.py` outside `requests/` is `.claude/agents/data-engineer-memory.md:202`. CLAUDE.md's `src/ootp_ai/` map lists directories (`contracts/`, `warehouse/`, `validate/`, `reports/`, `catalog/`) and the one-line summary "Parser, landing, warehouse loading, reporting" — it does not name `ingest.py`, so a package promotion touches it not at all. Meanwhile the risk implies the `first-sight` handoffs need updating; those are dated historical records of what was believed and measured at the time, and editing them would falsify the record the repo keeps them for. The mis-citation makes gated decision 2's stated cost look larger than it is, in a scope whose whole method is verified citation.

**Proposed fix:** Correct the risk to name the single live reference (`data-engineer-memory.md:202`), note that no markdown link targets the file so `tests/test_doc_links.py` is unaffected, and state that `requests/**/reviews/` handoffs are historical and deliberately not rewritten. That strengthens Option A rather than weakening it.

### [MINOR] A13 — The ensure_tables and verify_snapshot 'gaps' were already recorded in the repo — the three-way-independent-discovery framing overstates novelty and drops useful context

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** framing · **Location:** convergence_map[1] and [7] ("a gap none of the three was asked to look for, found independently by all three"); requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:144-146 and :160-162

**Problem:** `handoff-phase-8b.md:144-146` already records, under "Still open, and named rather than left to be found": "**No tracked entry point performs an ingest** (operator-disposed to Phase 10). Until then `ensure_tables` is reachable only through a test fixture, so on a fresh machine the eight tables come into existence as a side effect of running the suite." And :160-162 records "**`verify_snapshot` has no production caller.** The digests in `ingest_run` are copied from the manifest rather than re-measured over the bytes the parse actually read." Both findings are correct, but they are re-discoveries of written repo memory, not novel panel output — and the framing costs something real: the handoff records that this was *operator-disposed to Phase 10* and that disposition was never executed, which is exactly the provenance a plan wants when deciding whether the disposition still stands.

**Proposed fix:** Add `requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:144-162` to grounding_pointers, cite it as prior art in both convergence-map entries, drop the independence framing, and surface the unexecuted Phase-10 disposition as context for gated decision 3 (the operator already once decided the entry point should exist).

### [MINOR] A14 — The 'no duplication with anything in flight' claim omits open-front-office, which puts ensure_views() beside ensure_tables and edits the bootstrap script

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** fit · **Location:** fit_verdict.rationale (final paragraph); requests/feature-requests/open-front-office/PROJECT_SCOPE.md:370-377 and :381-383; gated_decisions[2]

**Problem:** The scope dismisses `open-front-office` in one clause ("Phase B lander is a GM write channel for `gm/`, not a warehouse loader"), but its Phase B3 specifies "`ensure_views()` beside `warehouse/load.py::ensure_tables` as the only thing that touches MySQL" (`PROJECT_SCOPE.md:373-374`), and B5 adds a restricted `gm_reader` grant to `ops/mysql-bootstrap.sql` (`:381-383`) — the same file this scope reasons about. That request is `scoped` and lands after first-sight Phases 10-13, so the ordering is genuinely uncertain. Gated decision 3's answer (schema DDL implicit on every `land`) sets a precedent that will immediately be asked of views: does `ingest land` ensure the GM's views too, or does a landing leave the GM's read surface stale?

**Proposed fix:** Name `open-front-office` in the fit section alongside `incremental-loading`, and add one sentence to gated decision 3: whether the 'implicit on every run' rule is meant to extend to `ensure_views` when Phase B lands, or whether views get an explicit verb. Deciding it now costs a sentence; deciding it later costs a second migration argument.

### [MINOR] A15 — Re-pointing the fixture satisfies the letter of the request's second cost but nothing delivers the signal it asked for

**Adversary:** `fit-ac` · **Confidence:** medium · **Category:** completeness · **Location:** goals[2]; acceptance_criteria[5]; vs requests/feature-requests/ingest-command/FEATURE_REQUEST.md:33-38

**Problem:** The request's second and self-described more important cost is that "the moment someone refactors `tests/fixtures/warehouse.py` for a test's convenience, they are editing the ingestion path, **with nothing to tell them so**". Core re-points the fixture onto a shared function, which is the right structural move, but the scope never requires the warning itself. AC6 asserts an import exists; an import is not a signal. `tests/fixtures/warehouse.py`'s current docstring (:1-27) is unusually explicit about why things are the way they are, which is the repo's house style for exactly this problem — and after the re-point it would describe a composition the module no longer performs.

**Proposed fix:** Add to core: the shared function's docstring names its three callers and states that changing it changes what the operator's command does; and `tests/fixtures/warehouse.py`'s docstring gains a sentence saying the landing now goes through the operator's own path. Add a criterion asserting the fixture's docstring names the shared function, in the same style as the existing source-text guards.

### [MINOR] SC-11 — "`reports/__main__.py` prints full paths" is inaccurate on the default configuration, and the claim is load-bearing in four places

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** fit · **Location:** goals[5], tiered_scope.core ("The stdout contract"), risks[5], convergence_map ("No absolute path may reach stdout"); config.py:43; reports/__main__.py:57-58

**Problem:** The scope repeatedly cites `reports/__main__.py:57-58` as "the precedent cuts the other way — it prints full paths." It prints `path`, which is `report_dir(settings.output_root, ref) / "roster.md"`. `DEFAULT_OUTPUT_ROOT = Path("var/reports")` (`config.py:43`) is CWD-relative *on purpose* — the comment says "CWD-relative on purpose: an absolute default would be machine-specific, and this repo is public." So on a default configuration `reports render` prints `var/reports/OOTP-AI/2024-03-07/1/roster.md`, not an absolute path. The precedent does not cut the other way; it is neutral, and it already embodies the same instinct.

**Proposed fix:** Restate as: "`reports render` prints whatever `output_root` resolves to, which config.py deliberately keeps relative by default. The ingest command prints no path at all, which is a stronger version of the same rule and is stated because an ingest run's output has no path worth printing." The no-path rule and its leak-pattern criterion (AC4) are both still correct — only the justification changes.

### [MINOR] SC-12 — Roughly half of core lands in `tests/`, which is in the write-capable builder's deny set, and the scope never says so

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** completeness · **Location:** .claude/agents/data-engineer.md:154-158 (repo-level deny set includes `tests/`); requests/feature-requests/README.md Index row `first-sight` (line 120: "`tests/` is main-thread-authored because it is in the builder's deny set"); tiered_scope.core items 11, 12, 13

**Problem:** Three of the thirteen core items are test work — re-pointing `tests/fixtures/warehouse.py`, re-pointing `tests/test_read_only.py`'s AC11 legs, and a new `tests/test_ingest_command.py` — plus AC6's proposed guard. The data-engineer subagent's deny set forbids all of it ("`tests/` — the guards that catch you"), and the rulebook is explicit that a spec whose target paths fall inside the deny set must be refused rather than built. `first-sight` already hit this and recorded the workaround (main-thread authorship). The scope never mentions it, so the plan stage will either rediscover it or hand a builder a spec it must refuse.

**Proposed fix:** Add one line to grounding_pointers or risks: "three of the core items and every acceptance criterion's test live under `tests/`, which is in `.claude/agents/data-engineer.md`'s repo-level deny set — the plan must author them on the main thread, as `first-sight` did."

### [MINOR] SC-14 — AC7's `reports/resolve.py` clause is not mechanically testable as written

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[6]; reports/resolve.py:179-182

**Problem:** AC7 pairs a precise, testable README clause ("contains the literal invocation string ... does not contain the string `There is no ingest command`") with a vague one: "`src/ootp_ai/reports/resolve.py` no longer points the operator at a non-existent ingest." Nothing in the listed test run (`test_doc_links`, `test_doc_link_contract`, `test_repo_structure`, `test_catalog`) looks at `resolve.py`'s message text, so as written this half is a human eyeball — which requests/feature-requests/README.md:70-85 rules out for a non-USER-RUN criterion.

**Proposed fix:** Pin it the same way as the README half: assert `src/ootp_ai/reports/resolve.py` contains the literal invocation string the command ships with, so `_nothing_landed_message` names a command that exists. Better still, assert it on the rendered message by calling `_nothing_landed_message` against an empty result, so the string is checked where the operator reads it.

### [MINOR] SC-15 — Two non-goals that should exist are missing: no new `.env` key, and no log file

**Adversary:** `scope-completeness` · **Confidence:** medium · **Category:** completeness · **Location:** non_goals (twelve entries, neither present); config.py:111-148; tests/test_read_only.py:337 (`CREATIVE_CALLS`)

**Problem:** The non-goal list is thorough on features but silent on two things that would each undo a stated goal. (1) **No new configuration key.** Everything the command needs already resolves from `Settings`; a `OOTP_INGEST_*` key added for convenience would mean an `.env.example` change, a `config.py` change and a new `test_config.py` case, and would break the "resolve by name" symmetry with the two existing entry points. (2) **No log file.** "Progress output for the ~2.2 s parse" is deferred, but a log file is a different thing and would be a `.write_text(`/`open(` in the new module — which trips `_writes_in` and forces exactly the `WRITERS` widening goal 7 exists to avoid. Goal 7's protection is only as strong as the absence of any file write in the module, and nothing currently states that as a requirement.

**Proposed fix:** Add both as non-goals, with the second phrased as the mechanism: "the new module opens no file for writing and creates no directory — that is what keeps `WRITERS` byte-unchanged, and it is a requirement, not an accident."

### [MINOR] SC-16 — The fresh-clone USER-RUN criterion depends on optional configuration

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[14]; config.py:135-137 (`_optional_save` for `OOTP_PROBE_LEAGUE`); goals[1]

**Problem:** The headline USER-RUN criterion runs `land --save-id <probe>` then `reports render --save-id <probe>` on a machine with no `bronze_*` tables. But `probe_save` is optional configuration — `_optional_save` returns `None` when `OOTP_PROBE_LEAGUE` is unset, and `.env.example` treats the two non-managed saves as optional (README.md:121-123 says the same). A genuinely fresh clone following README's setup block has no probe. So the criterion as written is not the fresh-clone story it claims to be; it is the fresh-clone story on a machine already configured like the author's.

**Proposed fix:** Either state `OOTP_PROBE_LEAGUE` as a prerequisite of the criterion, or run the criterion against `settings.managed` (safe — the command only reads the save, and the scope's own gated decision 6 argues the harm from a mistaken target is a wasted snapshot). Keep the SD-20 probe-first rule where it belongs: on automated tests, which AC9 already pins.

### [MINOR] SC-22 — Six cheap folds on a change the request sized as one module and a README section

**Adversary:** `scope-completeness` · **Confidence:** medium · **Category:** scope-creep · **Location:** tiered_scope.cheap_folds (six entries); FEATURE_REQUEST.md:194-196 ("The work is small — the diff is plausibly one module and a README section")

**Problem:** Taken together the folds add: a second output format with its own no-path rule and tests (`--json`), a post-copy re-digest, a mode stat call and print, a second query on the refusal path, a dual-allocator comparison and print, and a README recipe. Three of the six add a code path plus a test each. Individually each is defensible; collectively they roughly double the module's surface relative to the thirteen-item core, on a command whose printed contract the scope itself says `incremental-loading` will pin and which is expensive to change afterwards. Two of the six are separately shown above to be miscosted (SC-06) or contract-violating (SC-07).

**Proposed fix:** Trim to the three that are genuinely one line each and carry no new contract: `verify_snapshot` after the copy (with the measurement the scope already requires), the mode line, and the landed-dates in the refusal message. Keep the README two-line recipe, which is documentation. Demote `--json` to core-minimal (triple + counts, no digests) or to gated, since it is the machine-readable contract `incremental-loading` will pin and therefore deserves a decision rather than a fold. Drop or rewrite the dual-allocator print per SC-07.

### [QUESTION] A16 — Unknown --save-id exits 2 here but the sibling command exits 1 for the same class of mistake

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** fit · **Location:** acceptance_criteria[2]; tiered_scope.core ("An unknown id exits 2"); src/ootp_ai/reports/__main__.py:52-55

**Problem:** `reports render --save-id typo` raises `NoSuchSnapshot` and returns 1 (`reports/__main__.py:53-55`). This scope routes an unknown ingest target to 2 — defensible (nothing was landed, so it is closer to a configuration error than a refusal) but inconsistent across two commands an operator uses in the same breath, and the scope's own error surface maps only `ConfigError` to 2. `incremental-loading` will write a procedure that branches on these codes, and the scope elsewhere argues (in dropping exit code 3) that convention consistency is worth protecting.

**Proposed fix:** Decide it explicitly and record the reason in the scope, not the plan: either 2 because the target came from `.env`/argv and nothing was attempted (and then say the convention is 'argv or .env is wrong → 2'), or 1 for symmetry with `reports render`. Whichever, state it in the same sentence as the exit-code table so the plan cannot pick the other one.

### [QUESTION] A17 — The 'no progress output for the ~2.2 s parse' non-goal is measured against the wrong number

**Adversary:** `fit-ac` · **Confidence:** medium · **Category:** scope-creep · **Location:** non_goals[9]; cheap_folds (`verify_snapshot`); src/ootp_ai/snapshot.py:307-313; docs/decisions/0021 §Consequences

**Problem:** 2.2 s is `parse_seconds` — explicitly documented as excluding snapshotting, header provenance and landing (`ingest.py:116-120`). The command's actual wall clock also includes copying ~52 MiB with a full sha256 of each file before and after (`_copy_one`, `snapshot.py:307-313` — two full digest passes), a third full digest pass if the `verify_snapshot` cheap fold ships, and inserting ~301,000 rows in one transaction. The non-goal 'no progress output' may well still be right, but it is currently argued against a number that is a small fraction of the run, on the command the operator will type most often.

**Proposed fix:** Keep the non-goal, but restate it against the measured end-to-end wall clock: require the plan to record one measured `land` duration for the probe (copy + digest + parse + land, with and without the `verify_snapshot` fold) and re-affirm 'no progress output' against that figure. The fold's cost measurement is already required; extending it to the whole run costs nothing extra.

### [QUESTION] A22 — The 'clean' fit verdict is accurate about shape but understates where the risk sits

**Adversary:** `fit-ac` · **Confidence:** medium · **Category:** fit · **Location:** fit_verdict.verdict; vs gated_decisions[0], gated_decisions[1], risks[4], risks[6]

**Problem:** 'Clean' is well supported on the axes it argues: no new table, no contract edit, no parser change, an established entry-point shape with two prior instances, no ADR contradicted *in code*. But the scope's own contents describe a change that alters an operator-facing default the ADR settled (A1), requires promoting a private function (A4), edits the repo's most expensive and least replaceable test, re-points a fixture roughly ten gamedata tests depend on, may move a 502-line module, and leaves a boundary with a neighbouring request undrawn. A reader who skims to the verdict will under-price the review this needs.

**Proposed fix:** Keep 'clean' — reshaping would be wrong — but add the qualifying sentence the summary almost makes: 'Clean in shape; the risk is concentrated in one operator-facing default and one test-suite re-point, not in the size of the diff.' That is the honest version of what the stage-plan argument in the request already says.

### [QUESTION] SC-19 — Open question: is landing the standard-mode truth save into the operator's warehouse intended, and does the scope want to say so?

**Adversary:** `scope-completeness` · **Confidence:** medium · **Category:** scope · **Location:** tiered_scope.core (target resolution over `managed`/`truth_save`/`probe_save`); tests/test_parser_vs_export.py:130; tests/test_cross_mode_format.py:119; docs/decisions/0003

**Problem:** Core's target map includes `settings.truth_save`, which is the retained **standard-mode** save. That is defensible — `landed_probe(..., which="truth_save")` already lands it today for Tier B — but the scope only mentions the truth save in the negative (the challenge-mode-refusal drop). It never states affirmatively that the operator may land a standard-mode save through this command, or why that is right given ADR 0003 makes Challenge Mode the environment. Left unstated, the mode-reporting cheap fold looks like a warning about something the command should perhaps refuse.

**Proposed fix:** Add one sentence to the target-resolution core item: landing the truth save is sanctioned and already routine (`test_parser_vs_export.py` lands it every gamedata run); the mode line reports which mode produced a landing and never refuses, because reading is read-only under either mode and the truth save is the export's only source.

### [QUESTION] SC-20 — Open question: `ensure_tables` deliberately does not repair a drifted table, and nothing tells the operator when that bites

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** risk · **Location:** gated_decisions[2] (implicit `ensure_tables`); warehouse/load.py:169-189 and :176-178

**Problem:** The scope adopts `ensure_tables` on every run and argues the blast radius is bounded because it creates and never replaces. True — but its own docstring says the consequence out loud: *"A table whose **shape** has drifted from the declaration is therefore not repaired here — that is a migration, and a migration is a decision somebody makes in the open."* On a machine whose schema predates a contract change, the command silently creates nothing, then fails inside `_write_table`/`claim_ingest_run` with a MySQL column error the operator has no context for. Today only the test fixture reaches this and a developer reads the traceback; making it the operator's routine path changes who sees it.

**Proposed fix:** Decide in scope whether the command compares declared columns against `information_schema` and refuses with a named message ("table X exists but does not match the declaration; that is a migration"), or explicitly accepts the raw MySQL error as the failure mode and says so. The gated decision's own compromise — print the tables `ensure_tables` created, since it already returns them — should ship either way; it is free and it makes the schema side effect visible.

### [QUESTION] SC-21 — Open question: gated decision 5's recommendation requires an edit to a request this scope has no authority over

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** scope · **Location:** gated_decisions[4] ("a one-sentence boundary written into **both** requests"); requests/feature-requests/incremental-loading/FEATURE_REQUEST.md:61

**Problem:** The recommendation is right — the `status` capability is claimed by `incremental-loading`'s Desired Outcome line 61 and unassigned boundaries are how a capability gets built twice or not at all. But the fix it names is an edit to another track item's intake artifact, at a stage that produces only this slug's PROJECT_SCOPE. Nothing in the recommendation says who makes that edit, when, or under which stage's gate — so the most likely outcome is that it is agreed and never written.

**Proposed fix:** Name the mechanism: the boundary sentence goes into this scope's non-goals (already done) **and** into `incremental-loading`'s FEATURE_REQUEST as a dated amendment made by the operator before this build starts — or, if that is out of bounds here, into the Index row for `incremental-loading` in requests/feature-requests/README.md, which is already edited routinely by `/commit`.

### [NIT] A18 — AC13's "exactly four manifest passes" holds only when OOTP_TRUTH_LEAGUE is configured

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[12]; tests/test_read_only.py:252-269

**Problem:** The truth-save leg is conditional (`if settings.truth_save is not None`, `:258-266`), and the module explains why it is conditional rather than a skip. On a machine with `OOTP_TRUTH_LEAGUE` unset the test performs three passes, not four, and the criterion as written is false there.

**Proposed fix:** "...performs four manifest passes when `OOTP_TRUTH_LEAGUE` is configured and three otherwise — one baseline plus one per leg run — and adds no MySQL dependency."

### [NIT] A19 — AC7 lists tests/test_repo_structure.py, which has no bearing on this change

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[6]; tests/test_repo_structure.py:12-56

**Problem:** That module asserts required docs exist, every ADR is indexed, every ADR records its cost, and ADRs are sequentially numbered. It contains no reference to `src`, `ootp_ai`, `ingest` or `__main__` (verified by grep). Running it proves nothing about a README edit or a new entry point. Harmless, but it pads the gate and implies a coverage the module does not provide.

**Proposed fix:** Drop it, or replace it with `tests/test_skill_references.py`, which does scan prose for references that could go stale when a module moves — relevant if gated decision 2 selects the package promotion.

### [NIT] A20 — AC6 adds a fourth string-pinned source scan while an open request exists to fix that class of guard

**Adversary:** `fit-ac` · **Confidence:** medium · **Category:** risk · **Location:** acceptance_criteria[5]; docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md; requests/feature-requests/README.md:119 (tree-seam-for-remaining-guards)

**Problem:** AC6 proposes a source-text assertion that three modules import the shared function. The repo has an open intake request precisely because its whole-tree scans "are pinned against strings, which tests the rule and not the enumeration", and ADR 0022 closed the obvious way to prove them non-vacuous. The scope adds one without acknowledging either. In fairness AC6's scan asserts *presence* (three imports must be found), so a mutant enumerating zero files makes it fail rather than pass — the opposite failure mode from the absence-scans that request is about — but the scope should say so rather than leave a reader to work it out.

**Proposed fix:** Either add one clause noting that AC6 is a presence assertion and therefore cannot go vacuous the way `test_read_only.py`'s and `test_no_leaks.py`'s absence scans can, or express it without a scan at all: `assert command_module.SHARED_FN is fixtures.warehouse.SHARED_FN` — an identity assertion that is stronger, shorter, and immune to a rename.

### [NIT] A21 — The Challenge-mode drop is right but re-derived; a prior recorded decision already settles it

**Adversary:** `fit-ac` · **Confidence:** high · **Category:** framing · **Location:** above_and_beyond ("Challenge-mode pre-flight via `saves.assert_challenge_mode`", tier drop); requests/feature-requests/first-sight/reviews/handoff-phase-4.md:55-56

**Problem:** The drop rationale reasons from `tests/test_cross_mode_format.py:119` and `tests/test_read_only.py:258-266` to the conclusion that an unconditional `assert_challenge_mode` would break a sanctioned path. Correct — and already decided: `handoff-phase-4.md:55-56` records "`ingest_save` does **not** call `assert_challenge_mode`: a hard requirement would block Phase 9, which must ingest the standard-mode probe. Built the smaller interpretation." Citing the prior decision is stronger than re-deriving it, and prevents the question being re-opened a third time.

**Proposed fix:** Cite `handoff-phase-4.md:55-56` in the drop rationale and in the `saves.is_challenge_mode` cheap fold, framing the fold as 'report the mode the prior decision refused to enforce' rather than as a new observation.

### [NIT] SC-13 — AC8 omits `ruff format --check`, which CI runs as a separate gate

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** acceptance · **Location:** acceptance_criteria[7]; .github/workflows/ci.yml:45-52

**Problem:** CI runs four quality steps: `ruff check .`, `ruff format --check .`, `mypy`, and `pytest -m "not gamedata"`. AC8 names ruff check and mypy but not the format check, which is a distinct gate and the one most likely to be red on a new module written by hand.

**Proposed fix:** Extend AC8 to `uv run ruff check . && uv run ruff format --check . && uv run mypy`, matching the CI job step for step.

### [NIT] SC-17 — `landed_sim_dates` already has two callers, which weakens the fold's framing

**Adversary:** `scope-completeness` · **Confidence:** high · **Category:** fit · **Location:** tiered_scope.cheap_folds ("Name the landed dates on the refusal path"); reports/resolve.py:177 and src/ootp_ai/catalog/volume.py:46,191

**Problem:** The fold's argument leans on the docstring's "exposed rather than kept private because...", implying it is exposed and unused. It is already imported and used by `catalog/volume.py:191` as well as internally at `resolve.py:177`. Immaterial to whether the fold is right (it is), but the scope elsewhere uses "zero callers in `src/`" as a real signal (for `verify_snapshot` and `saves.py`, both of which I verified genuinely have zero), so mixing a two-caller function into the same rhetorical bucket dilutes it.

**Proposed fix:** Drop the exposure framing and justify the fold on its merit: naming the landed dates makes the append-only refusal actionable the same way `_nothing_landed_message` does for the render path, reusing a function two modules already call.

### [NIT] SC-18 — The `assumed`-label grounding for dropping the OOTP-is-running spike is not verified at the cited location

**Adversary:** `scope-completeness` · **Confidence:** low · **Category:** fit · **Location:** non_goals ("Building on `flag_save_completed.dat`...") and above_and_beyond ("Spike: can the command tell that OOTP is currently running?"); docs/data-access.md:85

**Problem:** Both entries assert that "`docs/data-access.md` §1 labels the content of the unwalked files `assumed`". What I found at the cited section is a file table listing `flag_save_completed.dat` at 1,010–1,065 B with the description "Save-completion flag" and no walker; I did not locate an `assumed` label attached to it. `saves.py:110-112` separately records `measured` 2026-08-16 that `flag_save_completed.dat` is a plain-text log, which is a stronger statement than the scope's. The drop verdict is right for the other reason the entry gives — it is a measurement task with its own finding and label, i.e. a separate request — so this is a citation problem, not a conclusion problem.

**Proposed fix:** Re-verify the label before the plan cites it, or restate the justification on the ground that already holds: this is a research task producing a labelled finding, and folding it into a wiring change smuggles a spike into a plumbing diff. Keep `saves.py:110-112`'s `measured` note as the pointer for whoever picks it up.
