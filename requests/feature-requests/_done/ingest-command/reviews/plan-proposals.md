# Plan panel — raw planner proposals

Verbatim output of the three divergent planners (code-grounded / sequencing / domain-convention).
Recorded as the provenance trail; the finalized plan may differ. Lines naming a file a later
stage creates are fenced so `tests/test_doc_links.py` exempts them; the text is unchanged.

## Planner: `code-grounded`

### Architecture notes

CURRENT STRUCTURE OF THE TOUCHED AREA

`src/ootp_ai/` ships exactly two entry points and both only READ a landing:
- `reports/__main__.py` (155 lines) — `main(argv) -> int` at :36 over a testable `render(settings, *, save_id, sim_date) -> list[Path]` at :62; argparse built by `_parser()` at :125 with a required subcommand at :130; exit codes 0 / 1 (`NoSuchSnapshot`, `WithheldFieldError`, `ValueError`) / 2 (`ConfigError`, bad `--sim-date`).
- `catalog/__main__.py` (271 lines) — the same shape without a subcommand, plus `_fence_docs_root` at :118 for its operator-typed write root.

The parse-and-land path is three library layers with no caller outside `pytest`:
1. `snapshot.take_snapshot(save, *, snapshot_root, ingest_seq=None)` (`snapshot.py:167`) — reads the sim date from `teams.dat`'s header via `_read_sim_date` (:285), allocates a FILESYSTEM sequence via `next_ingest_seq` (:146) when `ingest_seq is None`, `mkdir`s `<root>/<save_id>/<sim_date>/<seq>/` at :205, copies the five `SNAPSHOT_FILES` (:77-83) through `_copy_one` (:296) which digests the SOURCE before copying, and writes `manifest.json`.
2. `ingest.parse_snapshot(snapshot)` (`ingest.py:161`) — reads the four `PARSED_FILES` off the snapshot COPY, runs five walkers, `check_sim_dates` + `check_decoded`, and returns `ParsedSnapshot` with a filled `IngestRun` (`residual_bytes`, `parse_seconds`, `sources`).
3. `warehouse.load.land_snapshot(connection, parsed, *, ingest_seq=None)` (`load.py:195`) — one transaction, run row claimed first, `_check_counts` read-back, bounded deadlock retry at :233-250.

`ingest_save` (`ingest.py:436`) composes step 1 plus provenance only and is NOT what the fixture uses — `_describe(..., payload=None)` at :481-501 re-reads each file whole for 25 bytes of header, its own docstring measuring "~48 MB of avoidable I/O per ingest".

THE THREE SEAMS THE CHANGE HOOKS INTO

Seam A — the module/package boundary. `src/ootp_ai/ingest.py` is a MODULE, so `python -m ootp_ai.ingest` would execute it as `__main__` while every package-qualified import re-imports it as `ootp_ai.ingest`, giving two `ParsedSnapshot` classes and a silent `isinstance` failure across `warehouse/load.py:90`. Promotion to `src/ootp_ai/ingest/__init__.py` (verbatim) + `src/ootp_ai/ingest/__main__.py` removes the hazard and is import-transparent: `pyproject.toml:51-52` declares `packages = ["src/ootp_ai"]`, so hatchling needs no edit, and all TEN existing `from ootp_ai.ingest import …` sites survive unchanged — verified by grep: `src/ootp_ai/warehouse/load.py:90`, `src/ootp_ai/warehouse/ingest_run.py:57`, `tests/test_bronze_landing.py:44`, `tests/test_extraction_cost.py:41`, `tests/fixtures/warehouse.py:43`, `tests/test_grain_contracts.py:68`, `tests/test_parser_vs_export.py:59`, `tests/test_provenance.py:30`, `tests/test_read_only.py:46`, `tests/test_snapshot_semantics.py:73`.

Seam B — the shared game-touching function. Today `tests/fixtures/warehouse.py:151` composes `parse_snapshot(take_snapshot(save, snapshot_root=Path(tmp)))` and `tests/test_read_only.py:254/263/268` composes `parse_snapshot(ingest_save(...).snapshot)`. A new `src/ootp_ai/ingest/read.py::read_save(...)` becomes the single function that performs EVERY game read the command makes — the sim-date header read, the pre-flight digests, and the copy — and gets three callers: the command, the fixture, and AC11's three legs. It is placed in its own module, NOT in `ingest/__init__.py`, because AC9 pins `ingest.__all__` byte-unchanged.

Seam C — the pre-flight's warehouse read. `ingest_run.source_files` (built at `ingest_run.py:180-191`) carries per-file `size` and `sha256`, and `_copy_one` computes both on the SOURCE side (`snapshot.py:307-308`), so the stored digests are the save's own — the pre-flight can compare directly with no snapshot in hand. The lookup itself (`latest_ingest_seq` + `read_ingest_run`) stays OUTSIDE `read_save`, so no MySQL dependency enters ADR 0001's guard (`test_read_only.py:240-242` refuses exactly that).

WHAT THE COMMAND DOES, IN FAIL-FAST ORDER
settings → resolve target by configured save name → `connect_warehouse` → `ensure_tables` → pre-flight (`latest_ingest_seq`, `read_ingest_run`, digest compare) → `read_save` (copy + parse) → `verify_snapshot` → `land_snapshot(…, ingest_seq=<the filesystem sequence>)` → print the triple + row counts. MySQL down must fail before ~52 MB is copied; a snapshot with no landing behind it is an orphan.

MEASURED, TODAY, 2026-08-30 (the query the scope required before planning)
`SELECT save_id, sim_date, MAX(ingest_seq) FROM ingest_run GROUP BY 1,2` returns exactly two rows: `OOTP-AI` / 2024-03-07 / 1 and `Test-Save-Challenge-Mode` / 2024-03-18 / 1. `var/snapshots/` holds three trees: `OOTP-AI/2024-03-07/1`, `Test-Save-Challenge-Mode/2024-03-18/1`, `Test-Save-Standard-Mode/2024-03-18/1`. So two pairs are in step and the truth save drifts — filesystem seq 1 exists with NO warehouse row, so a first `land` there takes filesystem seq 2 with no seq 1. The scope's Risks §4 table is confirmed unchanged. The managed league's landed snapshot measures 54,939,056 bytes = 52.4 MiB across five files plus the manifest, confirming the ~52 MB figure and the staleness of `tests/test_read_only.py:187`'s "46 MB" comment.

WHAT MUST NOT MOVE
`tests/test_read_only.py`'s `WRITERS` (:303-317) stays byte-unchanged — `_writes_in` (:348-358) scans a module's own SOURCE TEXT for `.mkdir(`, `.write_text(`, `.write_bytes(`, `.touch(`, `os.makedirs` and write-mode `open(`; a module that delegates every file creation to `snapshot.py:205` trips nothing. `src/ootp_ai/contracts/tables.toml` is untouched and `docs/warehouse-catalog.md` must be byte-identical afterwards. No parser change, no fixed-offset seek, no epistemic label moves.

### Files to read first

- `requests/feature-requests/ingest-command/PROJECT_SCOPE.md` — The decided upstream artifact. Consume it; do not re-litigate. Its Goals (:85-117), Acceptance Criteria (:168-272), tiered Scope (:274-340) and Decisions (:564-638) are the contract this plan executes. Read its 'Affected Area & Pointers' table at :531-562 before touching code.
- `src/ootp_ai/reports/__main__.py` — READ FIRST. The pattern every entry point in this repo copies. :1-11 the rule that entry points are deliberate; :36-59 `main(argv) -> int` and the 0/1/2 exit convention; :62-108 the testable `render(settings, *, save_id=None, sim_date=None)`; :125-151 argparse with `add_subparsers(dest="command", required=True)` at :130; :154-155 the `raise SystemExit(main())` guard.
- `src/ootp_ai/catalog/__main__.py` — The second instance. :1-25 argues why it took no subcommand (heard and overruled by Scope Decision §2); :82-115 shows the same 0/1/2 error funnel with `ConfigError` → 2 and a named-exception tuple → 1; :118-146 `_fence_docs_root` is the record of the project's only operator-typed write root, and the reason `--snapshot-root` is dropped.
- `src/ootp_ai/ingest.py` — The 502-line module being promoted to a package verbatim. :50-62 `__all__` (must stay byte-unchanged, AC9); :66 `PARSED_FILES`; :161-217 `parse_snapshot`; :235-278 `check_sim_dates` / `check_decoded` — two of the refusals to surface; :281-300 `dump_parse`, the `read_manifest` → `parse_snapshot` composition `--from-snapshot` reuses; :436-460 `ingest_save`; :481-501 `_describe` and its measured '~48 MB of avoidable I/O per ingest' warning, which is why the shared function composes `take_snapshot + parse_snapshot` instead.
- `src/ootp_ai/snapshot.py` — The only module in `src/` allowed to create a file. :50-63 `__all__` (gains `read_sim_date`); :146-164 the FILESYSTEM `next_ingest_seq`; :167-216 `take_snapshot` — :189-191 is the auto-allocation that makes naive composition silently duplicate, :196-201 the `SnapshotExists` refusal that only fires on an explicit seq, :205 the lone `mkdir`; :219-251 `read_manifest`; :254-279 `verify_snapshot` (zero `src/` callers today); :285-293 `_read_sim_date` → promoted; :296-319 `_copy_one`, which digests the SOURCE side — so `ingest_run.source_files` really does carry the save's own digests.
- `src/ootp_ai/warehouse/load.py` — :68-74 why no DELETE/UPDATE exists; :159-166 `landed_tables`; :169-189 `ensure_tables` (creates, never repairs — :176-178); :195-250 `land_snapshot`, whose docstring at :203-217 is the explicit-vs-`None` `ingest_seq` decision this plan turns on, and :232-250 the deadlock retry that re-allocates per attempt and therefore only helps the `None` branch; :540-572 `table_digest` and its cost (why per-table digests are NOT in `--json`).
- `src/ootp_ai/warehouse/ingest_run.py` — :16-35 the measured correction that `SELECT … FOR UPDATE` does not serialise two allocators — read before writing any new SELECT here; :137-153 `next_ingest_seq`, whose contract is 'must be called inside the transaction that will insert the row' (which is why the pre-flight gets its OWN plain SELECT); :156-198 `ingest_run_values` — `source_files` carries per-file `name`, `size`, `sha256`, `version`, the exact material the digest pre-flight compares; :201-235 `claim_ingest_run` / `IngestRunExists`; :238-268 `read_ingest_run`.
- `src/ootp_ai/config.py` — :71-85 `SaveRef` with `path` and `save_id = to_save_id(league)` — the property that makes the disk-side and warehouse-side vocabularies the same string; :99-108 `Settings` with `managed` / `truth_save` / `probe_save`; :111-148 `load_settings(env)` — the mapping injection point offline tests use; :215-239 `reject_inside_game_roots`.
- `tests/test_read_only.py` — ADR 0001's proof and two structural guards. :25-32 the measured 2m35s / 30,703 files cost; :182-193 the `replace(settings, snapshot_root=tmp_path)` idiom AC10 reuses; :222-269 the three legs to re-point and :240-242's explicit refusal to include landing; :303-317 `WRITERS` (must stay byte-unchanged); :337-358 `CREATIVE_CALLS` and `_writes_in` — it strips `#` comments but NOT docstrings, so prose naming a banned call reds the guard.
- `tests/fixtures/warehouse.py` — The de facto ingestion path today. :19-26 why landings pass `ingest_seq=None` (a temp directory always allocates 1 on the filesystem side); :81-96 the loud-skip discipline and the repo's ONLY `ensure_tables` caller at :93; :99-130 `purge_snapshot`; :133-157 `landed_probe`, which composes `parse_snapshot(take_snapshot(save, snapshot_root=Path(tmp)))` at :151 and lands with `_land(connection, parsed)` at :152 — no explicit seq.
- `docs/decisions/0021-bronze-landing-is-append-only.md` — The semantics the command surfaces without changing. §Context:21-27 rejects a `(save_id, sim_date)`-keyed refusal BY NAME as 'worse'; §Decision parts 1-3 at :42-55; :57-59 names the correction workflow `--from-snapshot` serves ('a parser fix re-lands the same snapshot at the next sequence'); §Consequences :70-78 the 264,095-rows figure and 'no retention policy exists'.
- `ops/mysql-bootstrap.sql` — Verify for yourself: three `CREATE DATABASE` (:23, :30, :42), one `CREATE USER` (:54), database-scoped grants (:57-63). NO tables. This is what makes `ensure_tables` load-bearing for the fresh-clone criterion and what makes an automated empty-schema test unrunnable.
- `src/ootp_ai/reports/resolve.py` — :78-94 `landed_sim_dates` (reused on the refusal path); :168-187 `_nothing_landed_message` — the refusal-message pattern to copy, and the line at :181 telling the operator to 'run the ingest before rendering' that this change must make true.
- `tests/test_no_leaks.py` — :37-41 `PATTERNS` — the exact list the offline output test must IMPORT rather than restate (AC4). Note :21 `EXEMPT` and :31 that there is deliberately no fenced-code exemption.
- `README.md` — :109-119 the setup fence to extend; :128-134 the 'There is no ingest command' blockquote to delete (AC8).

### Phases

#### Phase 1 — Phase 1 — Promote `ingest` to a package; publish `read_sim_date`

**Goal:** `python -m ootp_ai.ingest` becomes hostable and the pre-flight gains its cheap sim-date read, with ZERO behaviour change. Nothing else in this plan is safe to write until this move is proven inert.

**Steps:**

- Before touching anything, run `git log --oneline -1` and `uv run pytest -m "not gamedata"` to record the green baseline. Read-only git only — never checkout/reset/restore/clean/stash.
- Create `src/ootp_ai/ingest/` and write `src/ootp_ai/ingest/__init__.py` as a VERBATIM copy of today's `src/ootp_ai/ingest.py` (502 lines, docstring at :1-28 through `_describe` ending at :501). Do not reflow, re-sort or 'tidy' a single line — the diff must be reviewable as a move.
- Delete `src/ootp_ai/ingest.py`. Git may record this as delete+add (Scope Risks §12); that is expected and is not a reason to change the approach.
- Prove the move is byte-exact: `git show HEAD:src/ootp_ai/ingest.py > <scratchpad>/ingest_before.py` then compare against `src/ootp_ai/ingest/__init__.py` (`Compare-Object (Get-Content A) (Get-Content B)` must return nothing). Read-only git.
- In `src/ootp_ai/snapshot.py`, rename `_read_sim_date` (:285) to `read_sim_date`, update its single caller at :185, and add `"read_sim_date"` to `__all__` (:50-63) between `"read_manifest"` and `"take_snapshot"` — ruff's RUF022 wants `__all__` sorted. Extend its docstring with one sentence saying why it is public: it is the only cheap answer to *what date would this land at?* before ~52 MB is copied.
- Confirm `ingest.__all__` (`ingest/__init__.py:50-62`) is byte-unchanged and that all ten `from ootp_ai.ingest import …` sites are unedited: `rg -n "from ootp_ai\.ingest import"` must return exactly the ten listed in the architecture notes.
- Do NOT rewrite `.claude/agents/data-engineer-memory.md:202`. That file is append-only (`.claude/agents/data-engineer-memory.md:41`) and its dated `verified` entry records what was true on 2026-08-16. Nothing in CI chases that path — `tests/test_doc_links.py:48,153-155` chases markdown links and bare `requests/…` tokens only, and `tests/test_agent_contract.py` does not validate evidence paths. If you want the promotion on the record, APPEND one dated entry instead.

**Acceptance:**

- `uv run python -c "import ootp_ai.ingest as m; print(m.__name__, bool(m.__path__))"` prints `ootp_ai.ingest True` (a package). Do not print `__file__` — it is an absolute path and `tests/test_no_leaks.py` scans anything that lands in a tracked file.
- `Compare-Object` between the pre-move `HEAD` blob and `src/ootp_ai/ingest/__init__.py` returns no differences.
- `rg -c "from ootp_ai\.ingest import"` across the repo totals 10 files, none of them edited in this diff.
- `snapshot.__all__` differs from HEAD by exactly one added entry, `read_sim_date`; `rg -n "_read_sim_date"` returns nothing.
- `uv run pytest -m "not gamedata"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` are all green.
- `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_provenance.py` is green (smoke over the move; `test_provenance.py:30` is the one remaining `ingest_save` consumer).

**Commit note:** Promote ingest.py to a package and publish read_sim_date. A verbatim 502-line move plus one rename: `python -m ootp_ai.ingest` on a MODULE would execute it as `__main__` while package-qualified imports re-import it as `ootp_ai.ingest`, producing two `ParsedSnapshot` classes and a silent `isinstance` failure across `warehouse/load.py:90` (label: inferred from Python import semantics, not reproduced). `snapshot._read_sim_date` becomes public because the digest pre-flight needs the sim date before ~52 MB is copied. `ingest.__all__` byte-unchanged; all ten import sites untouched. No behaviour change.

#### Phase 2 — Phase 2 — The shared game-touching seam, with the fixture and AC11 re-pointed onto it

**Goal:** One function performs every game read the operator's command makes, and it has three callers — so the test suite and the operator cannot drift. ADR 0001's manifest-diff proof brackets that function directly.

**Steps:**

- Write `src/ootp_ai/ingest/read.py`. Public surface: a frozen `SaveReading` dataclass and `read_save(save: SaveRef, *, snapshot_root: Path, prior_source_files: Sequence[Mapping[str, object]] | None = None, refuse_unchanged: bool = False) -> SaveReading`. It (a) calls `snapshot.read_sim_date(save)`, (b) when `prior_source_files` is given, compares each entry's `size` via `(save.path / name).stat().st_size` FIRST and only digests with `snapshot._digest`-equivalent streaming when every size matches, (c) returns early with `parsed=None` when nothing changed and `refuse_unchanged` is True — BEFORE `take_snapshot` runs, so no directory is created and no 52 MB is copied, (d) otherwise calls `take_snapshot(save, snapshot_root=snapshot_root)` and `parse_snapshot(...)` and returns both.
- `SaveReading` fields: `sim_date: SaveDate`, `verdict: str` (one of `"no-prior"`, `"changed"`, `"unchanged"`), `detail: str` (e.g. `"players.dat is 32,070,091 bytes; the last landing recorded 32,069,988"` — a FILE NAME and two integers, never a path), `parsed: ParsedSnapshot | None`. Document the invariant in the docstring: `parsed is None` if and only if `verdict == "unchanged" and refuse_unchanged`.
- `read_save` takes NO `ingest_seq` parameter — the sequence decision belongs to whoever calls `land_snapshot` (Scope Core, and `load.py:203-217`). It opens no warehouse connection and creates no file of its own; `take_snapshot` owns the only `mkdir`.
- Its module docstring names its three callers by path — `src/ootp_ai/ingest/__main__.py`, `tests/fixtures/warehouse.py::landed_probe`, `tests/test_read_only.py`'s AC11 legs — and states that changing it changes what the operator's command does. CRITICAL: that docstring must NOT contain the literal substrings `.mkdir(`, `.write_text(`, `.write_bytes(`, `.touch(`, `os.makedirs`, `.unlink(` or `.rename(`. `tests/test_read_only.py::_writes_in` (:348-358) strips `#` comments but NOT docstrings, so prose naming a banned call reds `test_only_allowlisted_modules_can_write_a_file`. Write 'creates no directory of its own' rather than naming the call.
- Re-point `tests/fixtures/warehouse.py::landed_probe` (:151). Import the MODULE, not the name — `from ootp_ai.ingest import read` — and call `read.read_save(save, snapshot_root=Path(tmp))`, then `_land(connection, reading.parsed)`. Keep all three test-only powers exactly where they are: the `TemporaryDirectory` at :149, the implicit `ingest_seq=None` at the LANDING call at :152 (do not pass a sequence — a temp directory always allocates 1 on the filesystem side, :19-26), and `purge_snapshot` in `finally` at :154-156. Add one sentence to its docstring saying the landing path is now shared with the operator's command.
- Re-point `tests/test_read_only.py`'s three legs at :254, :263 and :268 from `parse_snapshot(ingest_save(settings.X, settings=settings).snapshot)` to `read.read_save(settings.X, snapshot_root=settings.snapshot_root)`. Same probe → truth → managed order; no fourth leg; no MySQL. Update the import at :46 and rewrite the paragraph at :237-242 to say the guard now brackets every game read the operator's command makes, and why landing stays outside it.
- The module-attribute call style (`read.read_save(...)`) is load-bearing, not cosmetic: it is what lets a single `monkeypatch.setattr(read, "read_save", spy)` observe BOTH callers in AC6. A `from … import read_save` would bind the name in each module at import time and a one-site patch would silently miss the other.
- Create `tests/test_ingest_command.py` with its OFFLINE half only for now. Author it on the MAIN THREAD — `tests/` is in the write-capable builder's deny set (`.claude/agents/data-engineer.md:154-157`). Include: AC1's `WRITERS` assertion, and AC6's behavioural routing test (spy on `read.read_save`, drive `landed_probe` with stubbed warehouse work, assert a recorded call). NOTE a correction to AC1's literal wording: spell the import `from test_read_only import WRITERS`, not `from tests.test_read_only import WRITERS` — there is no `tests/__init__.py` and no `conftest.py` anywhere in the repo, so pytest's prepend import mode puts `tests/` itself on `sys.path`, which is exactly how `tests/test_extraction_cost.py:39` reaches `from fixtures.warehouse import …`.

**Acceptance:**

- `uv run pytest tests/test_read_only.py tests/test_ingest_command.py` (offline) is green, and `WRITERS` is byte-unchanged: the new test asserts `WRITERS == {"snapshot.py", "reports/__main__.py", "catalog/__main__.py"}` with a comment saying the new modules are deliberately absent because they create no file (AC1).
- `uv run pytest -m gamedata tests/test_read_only.py` is green. `test_a_full_run_touches_nothing_under_the_game_directories` still performs FOUR manifest passes with `OOTP_TRUTH_LEAGUE` configured and THREE without, and `test_the_manifest_is_not_vacuous` stays green alongside it (AC16).
- `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py` is green (AC17). Explicitly re-check that `test_parser_vs_export.py:130`'s `which="truth_save"` path still works and that `landed_probe` still lands with no explicit sequence.
- AC6 holds behaviourally, not by string scan: the spy records a call from the command's `land(...)` and a call from `landed_probe`.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` green.

**Commit note:** One shared game-touching function, with the fixture and ADR 0001's proof re-pointed onto it. `ingest/read.py::read_save` performs every game read the operator's command makes — the sim-date header read, the pre-flight digests, and the copy — and takes the prior landing's `source_files` as a plain argument so the warehouse lookup stays outside AC11's diff (`test_read_only.py:240-242` refuses a MySQL dependency in that guard by name). It takes no `ingest_seq`: that decision belongs to whoever calls `land_snapshot`. `landed_probe` keeps its temp-directory root, its warehouse-allocated sequence and its purge; `WRITERS` byte-unchanged.

#### Phase 3 — Phase 3 — The pre-flight's warehouse lookup and the digest comparison

**Goal:** The command can ask, cheaply and before any copy, 'has this save changed since the last landing at this sim date, and are the two sequence allocators in step?' — using a plain SELECT that cannot repeat this repo's one measured locking mistake.

**Steps:**

- Add `latest_ingest_seq(connection, *, save_id: str, sim_date: SaveDate) -> int` to `src/ootp_ai/warehouse/ingest_run.py`: `SELECT COALESCE(MAX(ingest_seq), 0) AS used FROM ingest_run WHERE save_id = %s AND sim_date = %s`, identifiers through `quote_ident`, values bound, NO `FOR UPDATE`, taking a `Connection` rather than a cursor. Add `"latest_ingest_seq"` to `__all__` between `"ingest_run_values"` and `"next_ingest_seq"`.
- Its docstring must state, in terms, why it is not `next_ingest_seq`: that one runs `FOR UPDATE` and its contract at :140-143 requires it be called inside the transaction that inserts the row, and this repo has already got that function's locking semantics wrong once (:16-35). This is a display/pre-flight read outside any transaction, and a lock taken in a transaction that has already committed protects nothing.
- Write the comparison helper inside `ingest/read.py` (it is a game read, so it belongs behind the AC11 bracket): given `prior_source_files` — the decoded JSON list from `read_ingest_run(...)["source_files"]`, each entry carrying `name`, `size`, `sha256`, `version` per `ingest_run.py:180-191` — stat every `SNAPSHOT_FILES` entry, return `"changed"` on the first size mismatch WITHOUT digesting, and only fall through to streaming sha256 when every size agrees.
- Add offline unit tests to `tests/test_ingest_command.py` covering the comparison against a synthetic `prior_source_files` list and a `tmp_path` fake save: identical bytes → `unchanged`; one byte changed at the same size → `changed` via digest; one file grown → `changed` via the size fast path with no digest performed (assert the fast path by spying on the digest helper).
- Confirm the append-only AST scan still passes: `tests/test_bronze_landing.py::test_no_module_in_the_warehouse_can_mutate_a_landed_row` globs `src/ootp_ai/warehouse/*.py` (:812-815) and matches SQL SHAPES (:761-772) — a `SELECT … COALESCE(MAX(...))` has no `SET`, so it is clean by construction.

**Acceptance:**

- `uv run pytest tests/test_bronze_landing.py tests/test_ingest_command.py tests/test_db_identifiers.py` is green.
- `latest_ingest_seq` returns 1 for `('OOTP-AI', 2024-03-07)` and 0 for `('Test-Save-Standard-Mode', 2024-03-18)` against the dev schema — the drift the plan's reconciliation rule exists for.
- The size fast path is proved, not assumed: the digest helper is not called when a size differs.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` green.

**Commit note:** A plain, non-locking allocator read for the pre-flight, and the digest comparison behind it. `latest_ingest_seq` is deliberately NOT `next_ingest_seq`: that one is `FOR UPDATE` and must run inside the inserting transaction (`ingest_run.py:137-143`), and this repo's docstring at :16-35 records the measurement that proved the obvious belief about it wrong. The comparison reads `source_files`' per-file `size` first and digests only when every size agrees, so a changed save almost always settles without a second read of 52 MB.

#### Phase 4 — Phase 4 — The command: `uv run python -m ootp_ai.ingest land`

**Goal:** An operator can take a configured save from disk to a landed bronze snapshot in one command, see the triple it created, and get every library refusal by name with a non-zero exit.

**Steps:**

- Write `src/ootp_ai/ingest/__main__.py` in the shape `reports/__main__.py` sets: a module docstring recording why this entry point exists and what it deliberately does NOT do (no render, no `--force`, no `--snapshot-root`, no scheduling); `main(argv: list[str] | None = None) -> int`; a testable `land(settings: Settings, *, save_id: str | None = None, snapshot_root: Path | None = None, new_look: bool = False, from_snapshot: Path | None = None) -> LandingResult`; `_parser()`; and `if __name__ == "__main__": raise SystemExit(main())` with the same `# pragma: no cover` note as `reports/__main__.py:154`.
- Argparse surface, pinned by AC2: `prog="python -m ootp_ai.ingest"`, `add_subparsers(dest="command", required=True)`, one `land` verb carrying `--save-id`, `--new-look`, `--from-snapshot DIR` and `--json`. There is NO `--sim-date` (the in-game date is read from `teams.dat`'s header, never supplied), no `--snapshot-root`, no `--ingest-seq`, no `--force`.
- Target resolution by configured save name only: build `{ref.save_id: ref for ref in (settings.managed, settings.truth_save, settings.probe_save) if ref is not None}` (`config.py:99-108`; the `None`s are what a fresh clone and CI have). Absent `--save-id` resolves to `settings.managed`. An unknown id — including anything that looks like a filesystem path — exits 2 with a message naming every configured `save_id`. No `saves.enumerate_saves` sweep.
- Fail-fast ordering, in this exact sequence because it is not the natural one: `load_settings()` → resolve target → `connect_warehouse(settings)` → `ensure_tables(connection)` (printing any table it created) → pre-flight → `read_save` → `verify_snapshot(reading.parsed.run.snapshot.path)` → `land_snapshot(...)`. MySQL down must fail before 52 MB is copied; a snapshot with no landing behind it is an orphan.
- The pre-flight: `sim_date = snapshot.read_sim_date(save)`; `warehouse_max = latest_ingest_seq(...)`; if `warehouse_max > 0`, `prior = read_ingest_run(connection, save_id=…, sim_date=…, ingest_seq=warehouse_max)` and pass `prior["source_files"]` into `read_save(..., refuse_unchanged=not new_look)`. Unchanged bytes → exit 1 with a message naming the existing triple, the landed dates from `reports.resolve.landed_sim_dates`, and `--new-look`. Changed bytes → proceed and say which file changed and how. `--new-look` → proceed regardless.
- Sequence policy, and the reconciliation Scope Risks §4 hands to this plan: pass the FILESYSTEM sequence explicitly — `land_snapshot(connection, reading.parsed, ingest_seq=reading.parsed.run.ingest_seq)` — so the snapshot directory and the landed row name the same attempt, which is precisely what `load.py:203-217` says the explicit branch is for. ALWAYS print both allocators when they disagree ('filesystem allocated N, the warehouse holds M'). AND refuse in the pre-flight, before the copy, when the filesystem sequence would be ≤ `warehouse_max`: that landing is guaranteed to raise `IngestRunExists` after paying 52 MB, and moving the same refusal earlier is not a change to landing semantics. Say in the message that `var/snapshots/` is documented as disposable and may have been cleared.
- `--from-snapshot DIR` re-lands an existing snapshot with no game read at all: `verify_snapshot(dir)` then `parse_snapshot(read_manifest(dir))` — the composition `dump_parse` already uses at `ingest.py:300` — then `land_snapshot(connection, parsed)` with `ingest_seq=None`, so the warehouse allocates the NEXT sequence. That is ADR 0021's named correction workflow (:57-59, 'a parser fix re-lands the same snapshot at the next sequence') and it keeps the deadlock retry effective on this path. The output states EVERY TIME whether the landed `ingest_seq` still matches the snapshot directory's number (Scope Decision §3).
- The stdout contract: the RESOLVED `save_id` (printed, never assumed — `.env` and the warehouse can disagree), the `sim_date` as `YYYY-MM-DD`, the `ingest_seq`, the per-table row counts from the returned `IngestRun`, any tables `ensure_tables` created, and the save's mode from `saves.is_challenge_mode(save.path)` — reported, never refused, because `tests/test_cross_mode_format.py:119` pins the retained truth save as standard-mode by design. NO ABSOLUTE PATH on stdout, ever; for `--from-snapshot` echo the directory's integer name, not its path. The rule is stdout-only: a `ConfigError` on STDERR may name the offending path, because a misconfiguration message that doesn't is not actionable.
- Factor the human output into a separate `render_result(result: LandingResult) -> str` that `main` prints, so AC4 can call it with a synthetic `IngestRun` and no warehouse.
- `--json`: a single `json.dumps(payload, sort_keys=True, indent=2)` block carrying only what is already on the returned `IngestRun` — `save_id`, `sim_date`, `ingest_seq`, `row_counts`, `residual_bytes`, `parse_seconds`, plus `challenge_mode`, `tables_created`, `source_changed` and (for `--from-snapshot`) `snapshot_ingest_seq`. Zero extra queries. Per-table `table_digest` values are DEFERRED, not folded — `load.py:540-572` re-reads every column of every row (~301,000 for one landing, 264,095 of them `bronze_name`) and that is a second full read of everything the landing just wrote. Under `--json` the human block is suppressed so stdout stays parseable.
- The error surface, caught by name in ONE explicit tuple because these share no base class: `SnapshotExists` and `SnapshotCorrupt` (`ootp_ai.snapshot`), `SnapshotDateMismatch` and `UndecodedRecords` (`ootp_ai.ingest`), `SaveFormatError` (`ootp_ai.parser.errors`), `IngestRunExists` (`ootp_ai.warehouse.ingest_run`), `ConcurrentLandingError` and `LoadError` (`ootp_ai.warehouse.load`) → printed to stderr as `f"{type(error).__name__}: {error}"` and exit 1. `ConfigError` → exit 2. Add an offline test asserting the tuple has all eight members by name, so a future refactor that drops one turns a refusal into a traceback loudly.
- Close the connection in a `finally`, matching `reports/__main__.py:98-99` and `catalog/__main__.py:187-188`.
- Extend `tests/test_ingest_command.py`: offline for AC2 (`_parser().parse_args(["land"]).command == "land"`; the four flags exist; the four forbidden options do not; `with pytest.raises(SystemExit) as exc: main([])` then `assert exc.value.code == 2`), AC3 (via `load_settings(mapping)` — the injection point at `config.py:111`), AC4 (importing `PATTERNS` from `test_no_leaks`, not restating it), AC5 (monkeypatched `land_snapshot` raising `IngestRunExists` then `ConcurrentLandingError`, messages DISTINCT per `load.py:146-154`; monkeypatched `load_settings` raising `ConfigError` → 2), AC7 (a spy proving `ensure_tables` is called exactly once and before `take_snapshot`).
- Add the `gamedata` half of `tests/test_ingest_command.py`, PROBE ONLY (SD-20 — never the managed league in an automated test): AC10 (monkeypatch `load_settings` IN THE COMMAND MODULE to return `replace(settings, snapshot_root=tmp_path)`, the idiom at `test_read_only.py:193`; assert `main(["land", "--save-id", <probe>]) == 0` and parse the triple out of `capsys`), AC11, AC12, AC13 (mutate a byte in a COPIED fixture save or monkeypatch the pre-flight's digest source — never edit a real save), AC14, AC15. Every one runs `purge_snapshot` in `finally`.

**Acceptance:**

- `uv run pytest tests/test_ingest_command.py` (offline) green, covering AC1-AC7.
- `uv run pytest -m gamedata tests/test_ingest_command.py` green, covering AC10-AC15 against the probe only.
- AC12 specifically: a second invocation against unchanged bytes returns non-zero, names the existing triple and `--new-look`, and creates NO new `ingest_run` row and NO new snapshot directory — assert the directory count under the temp snapshot root is unchanged, proving the refusal fired before 52 MB was copied.
- AC14 specifically: `--new-look` lands identical bytes at `previous + 1`, and `warehouse.load.table_digest` over every declared table for the FIRST triple is identical before and after — the assertion shape of `tests/test_snapshot_semantics.py::test_two_sequences_of_one_sim_date_both_persist` (:537-577).
- `uv run pytest -m gamedata tests/test_read_only.py` still green and still at the same manifest-pass count — the command added no game read outside `read_save`.
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all green.

**Commit note:** An ingest command: `uv run python -m ootp_ai.ingest land`. One verb that pre-flights, snapshots, parses and lands, over the shared game-touching function AC11 already brackets. The re-run default is the digest pre-flight (Scope Decision §1): unchanged bytes refuse and cost nothing, changed bytes at an unchanged sim date land the next sequence automatically with no flag — ADR 0021's motivating free-agent case — and `--new-look` lands identical bytes deliberately. The eight library refusals reach the operator by name with exit 1; `ConfigError` and an unknown `--save-id` exit 2. No absolute path reaches stdout. `WRITERS` byte-unchanged: this module opens no file for writing and creates no directory.

#### Phase 5 — Phase 5 — Retire the documented gap and true the docs up

**Goal:** Every document that describes the absent capability, or tells the operator to run a command that did not exist, now tells the truth — and the boundary with `incremental-loading` is written into both requests so the `status` half is not lost to mutual assumption.

**Steps:**

- Delete `README.md:128-134`'s 'There is no ingest command' blockquote in full.
- Extend the setup fence at `README.md:109-119` with the literal invocation string the command ships with — `uv run python -m ootp_ai.ingest land` — placed BEFORE the `reports render` line, plus one plain sentence that the first run creates the eight declared tables, so `mysql -u root -p < ops/mysql-bootstrap.sql` (which creates databases and a user but no tables) is no longer a half-finished setup.
- Correct `src/ootp_ai/reports/resolve.py:179-182`. `_nothing_landed_message` already tells the operator to 'run the ingest before rendering'; make it name the command by its literal invocation string so the advice is actionable.
- Add a dated amendment to `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md` recording the boundary from Scope Decision §5: this request owns the disk-and-refusal half (what save, what sim date, is it already landed — delivered by the landed-dates line on the refusal path); `incremental-loading` owns the warehouse-inventory half (its Desired Outcome :54-65, especially :61). Neither builds a `status` verb now.
- Pass `CLAUDE.md` through `/update-docs`: its Status paragraph still says 'serves two reports' and 'Only Phase 13 remains', and its `src/ootp_ai/` project map lists `contracts/`, `warehouse/`, `validate/`, `reports/` and `catalog/` but no `ingest/`. Judge, do not mechanically edit.
- Advance the request artifacts: `requests/feature-requests/ingest-command/PROJECT_SCOPE.md`'s status header, the new `IMPLEMENTATION_PLAN.md`'s header, and the Index row for `[ingest-command]` at `requests/feature-requests/README.md:126`. `/commit` keeps these in step with what actually landed.
- Add AC8's assertions to the offline half of `tests/test_ingest_command.py`: `README.md` contains the literal invocation string and does NOT contain `There is no ingest command`; `src/ootp_ai/reports/resolve.py` contains that same literal string. Keep the literal in one module-level constant the test and the command both read, so the two cannot drift.

**Acceptance:**

- `uv run pytest tests/test_doc_links.py tests/test_doc_link_contract.py tests/test_catalog.py tests/test_skill_references.py tests/test_repo_structure.py tests/test_no_leaks.py tests/test_ingest_command.py` is green (AC8).
- `docs/warehouse-catalog.md` is byte-identical to HEAD — `git diff --stat docs/warehouse-catalog.md` is empty. No edit to `src/ootp_ai/contracts/tables.toml`, no ninth table, no new column.
- `rg -n "There is no ingest command" README.md` returns nothing; `rg -n "python -m ootp_ai.ingest land" README.md src/ootp_ai/reports/resolve.py` returns at least one hit in each.
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` green.

**Commit note:** Retire the documented gap the command just closed. README's blockquote said the setup path was `pytest`; it now names the command, and notes that the first run creates the declared tables — `ops/mysql-bootstrap.sql` creates three databases and a user and no tables at all. `reports/resolve.py`'s 'run the ingest before rendering' now names a command that exists. The `status`-verb boundary with `incremental-loading` is written into both requests so it is not lost to mutual assumption (Scope Decision §5).

#### Phase 6 — Phase 6 — Measure, record, and hand the USER-RUN criteria over

**Goal:** The three numbers this scope obliged the plan to produce are on the record, and the two criteria only a human can run are handed to the operator with their prerequisites stated.

**Steps:**

- Measure and record the digest pre-flight's cost on the managed league: wall-clock for the size-only fast path (5 `stat` calls) and for the full sha256 path over 54,939,056 bytes. Both against the alternative the scope asked to be priced — copy-then-compare, which spends the 52 MB copy and a filesystem sequence before refusing.
- Measure and record `verify_snapshot`'s added seconds after the copy (Scope's cheap-fold measurement obligation). State honestly what it buys: `_copy_one` (`snapshot.py:296-319`) already digests source and destination and compares them seconds earlier in the same process, so a third digest of the same bytes can essentially only catch storage that failed between the two — the value is that ADR 0021's snapshot-is-authoritative triage now rests on a snapshot proved intact at landing time, which `first-sight/reviews/handoff-phase-8b.md:160-161` recorded as missing. If the measured cost is material, record the number and say so rather than quietly dropping the fold.
- Measure end-to-end wall clock for one `land` against the probe, so Scope non-goal 'progress output is out' is restated against the real number rather than against the ~2.2 s parse alone (Scope Risks A17).
- Correct the stale figure in `tests/test_read_only.py:187` — the comment says '46 MB directory per run'; the measured snapshot is 52.4 MiB (54,939,056 bytes across five files plus the manifest, measured 2026-08-30). A comment-only edit; do not change the test's behaviour.
- Write the numbers into the request's `IMPLEMENTATION_REPORT.md` with epistemic labels — every one of them is `measured`, with the date and the machine-independent details (byte counts, file counts), never a path.
- Hand AC18 and AC19 to the operator with the prerequisite stated: AC18 run against the probe needs `OOTP_PROBE_LEAGUE` configured; run against `settings.managed` it is safe because the command only ever reads the save (`reject_inside_game_roots` fences the write roots and AC11 proves it by diff over 30,703 files). AC19 is the paste-into-a-scratch-`.md` leak check. The acceptance panel may NOT claim either.

**Acceptance:**

- Three measured numbers recorded with dates and labels: pre-flight fast path, pre-flight full-digest path, `verify_snapshot` after the copy — plus end-to-end wall clock for one `land`.
- `tests/test_read_only.py:187`'s size figure matches the measured 52.4 MiB, and `uv run pytest tests/test_read_only.py` stays green.
- AC18 and AC19 are written out verbatim as operator instructions with their prerequisites, and are explicitly marked USER-RUN.
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` green.

**Commit note:** Record the measurements this scope obliged the plan to produce, and correct one stale figure. The snapshot is 52.4 MiB, not the 46 MB `test_read_only.py:187` has claimed since Phase 3 — understated by ~14%. The digest pre-flight's two paths and `verify_snapshot`'s added seconds are on the record with dates, so the trade the re-run default makes is priced rather than asserted. AC18 and AC19 stay the operator's.

### Testing

HOW THE WHOLE THING IS VERIFIED

Three tiers, and the split matters because two of them cannot run in CI.

1. OFFLINE (runs in CI on every PR, `uv run pytest -m "not gamedata"`). Covers AC1-AC9. Everything here is exercisable from a dict via `load_settings(mapping)` (`config.py:111`), a `tmp_path` fake save, and monkeypatched library calls. Specifically: the `WRITERS` byte-identity assertion; the argparse surface pin including `pytest.raises(SystemExit)` with `exc.value.code == 2` for a missing subcommand (argparse RAISES rather than returning, so "returns 2" would never fire); target resolution over a `Settings` with `truth_save`/`probe_save` set to `None`; the result formatter checked against `PATTERNS` IMPORTED from `test_no_leaks` rather than restated; the refusal surface with `land_snapshot` monkeypatched to raise `IngestRunExists` then `ConcurrentLandingError`, asserting the two messages are DISTINCT (`load.py:146-154` names conflating them as a real failure — an operator told "already landed" for a contention loss goes looking for a landing that never happened); the eight-member exception tuple asserted by name; the `ensure_tables`-before-`take_snapshot` spy; and AC6's behavioural routing spy.

2. GAMEDATA, PROBE ONLY (`uv run pytest -m gamedata`, never in CI, never against the managed league in an automated test — SD-20). Covers AC10-AC17. The new `tests/test_ingest_command.py` gamedata half proves the exit-0 path, one real landing read back through `read_ingest_run`, the unchanged-bytes refusal creating neither a row nor a directory, changed-bytes landing automatically, `--new-look` at `previous + 1` with the first triple's `table_digest`s unmoved, and `--from-snapshot` re-landing with the game directory's manifest unchanged. Every one purges in `finally`.

3. REGRESSION SAFETY — the re-point is the riskiest thing in this change. `read_save` acquires ~10 gamedata tests across four modules in one move, so a defect in it reds all of them at once. The specific regression set to run after Phase 2 and again after Phase 4: `uv run pytest -m gamedata tests/test_read_only.py tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py`. Note the panel's own draft named `tests/test_bronze_landing.py` here and that was wrong — it does not import `landed_probe`; the two riskiest real consumers are `test_extraction_cost.py` (a timing harness, `DRIFT_FACTOR = 10.0` at :57) and `test_parser_vs_export.py` (the Tier-B export diff, which lands the STANDARD-mode truth save at :130).

THE THREE THINGS MOST LIKELY TO BREAK SILENTLY, AND HOW EACH IS CAUGHT

(a) The fixture's sequence policy travelling with the shared function. `landed_probe` lands with no explicit sequence because a temp directory always allocates 1 on the filesystem side (`tests/fixtures/warehouse.py:19-26`). If the CLI's explicit-sequence policy leaks into `read_save`, `landed_probe` starts colliding at seq 1 and the failure appears as `IngestRunExists` in unrelated grain tests. Caught because `read_save` has no `ingest_seq` parameter at all — the sequence decision is made only at the `land_snapshot` call site, and AC17 asserts `landed_probe` still lands with `ingest_seq=None`.

(b) AC11 getting more expensive. It is the most expensive test in the repo — 2m35s over 30,703 files, ~6.4 GB hashed three times, measured 2026-08-16 (`test_read_only.py:25-32`). Caught by asserting the manifest-pass count is unchanged (four with `OOTP_TRUTH_LEAGUE` configured, three without) and that no fourth leg and no MySQL dependency were added.

(c) A docstring tripping the write guard. `_writes_in` (`test_read_only.py:348-358`) scans SOURCE TEXT and strips only `#` comments, so the sentence "this module never calls .mkdir(" in a docstring would red `test_only_allowlisted_modules_can_write_a_file`. Caught immediately by running `uv run pytest tests/test_read_only.py` offline after every new docstring.

PER-PHASE CADENCE. Every phase ends at a `/commit`-gated checkpoint on a green local run: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` (strict over `src` and `tests`), plus the phase's own named gamedata command where one applies. `/commit` is the ONLY sanctioned path — never `git commit` ad hoc, never merge, never amend, never push `main`; the PR stays the operator's. Subagents get read-only git and `tests/` is in the write-capable builder's deny set (`.claude/agents/data-engineer.md:154-157`), so every test file in this plan is authored on the main thread, as `first-sight` did.

### Risks

- THE NAIVE COMPOSITION IS SILENTLY WRONG, AND IT IS THE OBVIOUS ONE. `take_snapshot` with `ingest_seq=None` allocates the next free FILESYSTEM sequence and never raises (`snapshot.py:189-201`); `SnapshotExists` fires only when a sequence is named explicitly (:196). So `land = snapshot + parse + land` composed the obvious way does NOT surface ADR 0021's refusal — it lands a full duplicate, 52.4 MiB on disk and ~301,000 rows, with no retention policy to reclaim either. Shipping documentation claiming a protection the code does not provide is the specific failure to avoid. Mitigation: the pre-flight runs BEFORE `take_snapshot`, and AC12 asserts no new directory appears.
- THE PRE-FLIGHT COSTS A SECOND READ OF THE SAVE, AND THE PLAN COMMITS TO PAYING IT. Digest-before-copy reads the save twice (digest, then `shutil.copy2`); copy-then-compare spends the 52.4 MiB copy and a filesystem sequence before refusing. This plan takes digest-before-copy, because the point of the refusal is to cost the operator nothing — mitigated by the size fast path, since a changed save almost always changes file sizes. Phase 6 measures both and records the numbers rather than asserting the choice.
- `--new-look` IS REQUIRED FOR A CASE ADR 0021 NAMES EXPLICITLY. ADR 0021:57-59: 'A parser fix re-lands the same snapshot at the next sequence' — same bytes, same date, deliberate. Under the digest pre-flight that path refuses without the flag. This is the honest cost of Scope Decision §1 and must be documented AT THE FLAG's help text, not discovered by an operator mid-correction.
- TWO INDEPENDENT SEQUENCE ALLOCATORS, WITH ONE LIVE INSTANCE OF DRIFT — re-measured 2026-08-30 and unchanged from the scope's table. `snapshot.next_ingest_seq` (`snapshot.py:146`) counts directories under the gitignored, disposable `var/snapshots`; `warehouse.ingest_run.next_ingest_seq` (`ingest_run.py:137`) reads `MAX(ingest_seq)` from MySQL. Measured: `OOTP-AI` 2024-03-07 fs 1 / warehouse 1 (in step); `Test-Save-Challenge-Mode` 2024-03-18 fs 1 / warehouse 1 (in step); `Test-Save-Standard-Mode` 2024-03-18 fs 1 / warehouse NO ROW (drift). So a first `land` against the truth save takes filesystem seq 2 with no seq 1, and a later reader applying ADR 0021's 'monotonic integer … starting at 1' reads the gap as a lost landing. The opposite direction is not currently instantiated but is reachable: delete `var/` (documented as disposable) and the first run claims seq 1 and hits `IngestRunExists` on a landing the operator never made. Mitigation: keep the filesystem sequence (so the two stores name the same attempt, per `load.py:203-217`), ALWAYS print both numbers when they disagree, and refuse pre-copy when the filesystem sequence would be ≤ the warehouse maximum.
- AN EXPLICIT `ingest_seq` WEAKENS THE DEADLOCK RETRY, INVISIBLY. `land_snapshot` retries on 1213/1205 and re-allocates the sequence each attempt (`load.py:232-250`), which only works on the `ingest_seq=None` branch. The command therefore has weaker contention behaviour than the fixture it shares a path with: a lost race surfaces as a refusal rather than a recovery. Unlikely in a single-operator setup; stated so it is a trade rather than an inheritance. `--from-snapshot` uses `None` and keeps the retry.
- CONFLATING CONTENTION WITH A REFUSAL. `load.py:146-154` names this failure in terms. `IngestRunExists` means 'this snapshot is already in the warehouse'; `ConcurrentLandingError` means 'somebody else is writing right now'. The command must print them distinctly, and AC5 asserts the two messages differ.
- RE-POINTING THE FIXTURE COUPLES ~10 GAMEDATA TESTS TO ONE NEW FUNCTION. A defect in `read_save` reds `test_snapshot_semantics.py`, `test_grain_contracts.py`, `test_extraction_cost.py` and `test_parser_vs_export.py` at once. The fixture's loud-skip discipline (`tests/fixtures/warehouse.py:81-96`, 'Never a vacuous pass') must survive unchanged — a fixture that skips silently when MySQL is down reports that the grain holds without having looked.
- THE `ingest_save` COMPOSITION WOULD HAVE ADDED ~50 MB OF READS TO A TIMING HARNESS. `_describe(..., payload=None)` (`ingest.py:481-501`) re-reads each file whole for 25 bytes of header; its own docstring measures '~48 MB of avoidable I/O per ingest'. This plan composes `take_snapshot + parse_snapshot` instead — the fixture's existing, cheaper shape. `ingest_save` is not orphaned: `tests/test_provenance.py:30` still imports and calls it.
- A DOCSTRING CAN RED THE WRITE GUARD. `_writes_in` (`tests/test_read_only.py:348-358`) strips `#` comments but not docstrings, so writing `.mkdir(`, `.write_text(`, `.write_bytes(`, `.touch(`, `os.makedirs`, `.unlink(` or `.rename(` in PROSE inside `ingest/read.py` or `ingest/__main__.py` fails `test_only_allowlisted_modules_can_write_a_file`. This is a live hazard precisely because those modules' docstrings need to explain that they create no file. Phrase it as 'creates no directory of its own', never by naming the call.
- ABSOLUTE PATHS REACHING TRACKED FILES. `saved_games.dat` embeds a user-profile path per save; `gm/` is tracked and public; `tests/test_no_leaks.py:37-41` scans for drive letters, home directories and email addresses. State the precedent accurately: `reports render` prints whatever `output_root` resolves to, which `config.py:42-43` deliberately keeps RELATIVE by default. This command prints no path at all — a stronger form of the same rule, not a divergence from a path-printing sibling. The `ConfigError`-on-stderr exemption exists because a misconfiguration message that does not name the offending path is not actionable.
- THE MANAGED LEAGUE IS THE DEFAULT TARGET AND THERE IS NO AUTOMATED GUARD AGAINST IT (Scope Decision §6). The structural protection holds — nothing in `src/` opens a game file for writing, `reject_inside_game_roots` (`config.py:215-239`) fences the write roots, and AC11 proves it by diff over 30,703 files — so the realistic harm is a wasted snapshot and a landing under the wrong `save_id`, recoverable and immediately visible in the printed triple. Stated so the silence is a decision. Every automated test targets the probe.
- PACKAGE PROMOTION IS A 502-LINE MOVE GIT MAY RECORD AS DELETE+ADD. All ten `from ootp_ai.ingest import …` sites survive unchanged, but line-numbered prose does not. Do NOT rewrite historical `requests/**/reviews/` handoffs — they are the record of what was believed when. And do NOT rewrite `.claude/agents/data-engineer-memory.md:202` in place: that file is append-only by its own rule at :41, and nothing in CI chases the path.
- INGESTING WHILE OOTP IS RUNNING IS ONLY PARTIALLY GUARDED. `_copy_one` (`snapshot.py:296-319`) digests each source before and after the copy, and `check_sim_dates` (`ingest.py:235-258`) refuses a mixed snapshot. Neither catches a mid-write change ACROSS files at an unchanged sim date. A CLI makes this reachable outside a deliberate `-m gamedata` run — exactly when the operator is least likely to have quit the game first. Whether the command can detect a running game is explicitly NOT in scope: `docs/data-access.md:85,95` labels `flag_save_completed.dat`'s content `assumed`, and this repo forbids building on an assumed claim.
- MAKING LANDING ONE KEYSTROKE ACCELERATES A COST NOBODY HAS BOUNDED. `bronze_name` re-lands 264,095 rows per snapshot (ADR 0021 §Consequences:70-74); no retention policy exists; ADR 0018 leaves the per-date growth rate `unconfirmed`. This plan does not fix it and must not appear to.
- THE DOWNSTREAM CONTRACT IS BEING PINNED BY THIS DIFF. `incremental-loading` will write its operator procedure against whatever invocation string, flag names, exit codes and output format ship. All four are cheap now and expensive after — which is why `--json` is folded in: it gives that request a stable contract instead of a print format to grep.
- `ensure_tables` DOES NOT REPAIR A DRIFTED TABLE (`load.py:169-189`, and its docstring at :176-178 says so) and nothing tells the operator when that bites. Accepted as a known limitation (Scope Decision §4), stated in the command's docstring, not fixed here. When `open-front-office` Phase B lands an `ensure_views()` beside it, whether the implicit rule extends is THAT request's decision.

### Files to touch

- `src/ootp_ai/ingest.py` — DELETE — moved verbatim to `src/ootp_ai/ingest/__init__.py` (Phase 1). Git may record delete+add rather than a rename; that is expected.
- `src/ootp_ai/ingest/__init__.py` — NEW — today's 502-line `ingest.py` moved byte-for-byte. `__all__` (:50-62 in the original) stays unchanged, so all ten `from ootp_ai.ingest import …` sites import without edit (Phase 1).
- `src/ootp_ai/ingest/read.py` — NEW — the shared game-touching seam. `SaveReading` + `read_save(save, *, snapshot_root, prior_source_files=None, refuse_unchanged=False)`. Performs every game read the command makes: the sim-date header read, the pre-flight size/digest comparison, and the copy via `take_snapshot`. Takes NO `ingest_seq`, opens no warehouse connection, creates no file of its own (Phase 2).
- `src/ootp_ai/ingest/__main__.py` — NEW — the command. `main(argv) -> int` over a testable `land(settings, *, save_id=None, snapshot_root=None, new_look=False, from_snapshot=None)`, `_parser()` with a required `land` subcommand carrying `--save-id`, `--new-look`, `--from-snapshot`, `--json`, a separately testable `render_result(...)`, the eight-exception tuple, and exit codes 0/1/2 (Phase 4).
- `src/ootp_ai/snapshot.py` — Rename `_read_sim_date` (:285) to public `read_sim_date`; update its single caller at :185; add `"read_sim_date"` to `__all__` (:50-63) between `"read_manifest"` and `"take_snapshot"`; extend its docstring with why it is public (Phase 1).
- `src/ootp_ai/warehouse/ingest_run.py` — Add `latest_ingest_seq(connection, *, save_id, sim_date) -> int` — a plain, non-locking `SELECT COALESCE(MAX(ingest_seq), 0)` — with a docstring saying why it is NOT `next_ingest_seq` (:137-143's in-transaction `FOR UPDATE` contract, and :16-35's measured correction). Add it to `__all__` between `"ingest_run_values"` and `"next_ingest_seq"` (Phase 3).
- `src/ootp_ai/reports/resolve.py` — Correct `_nothing_landed_message` at :179-182 so 'run the ingest before rendering' names the literal invocation string the command ships with (Phase 5, AC8).
- `tests/fixtures/warehouse.py` — Re-point `landed_probe` at :151 onto `read.read_save(save, snapshot_root=Path(tmp))`, keeping the `TemporaryDirectory` (:149), the no-explicit-sequence landing (:152) and `purge_snapshot` in `finally` (:154-156). Update the import at :43-44 and add one docstring sentence saying the landing path is now shared with the operator's command. MAIN-THREAD AUTHORED — `tests/` is in the builder's deny set (Phase 2).
- `tests/test_read_only.py` — Re-point the three AC11 legs at :254, :263 and :268 onto `read.read_save(...)`; update the import at :46; rewrite the docstring paragraph at :237-242 to say the guard now brackets every game read the operator's command makes and why landing stays outside it. No fourth leg, no MySQL, no change to the manifest-pass count. `WRITERS` (:303-317) BYTE-UNCHANGED. Also correct the stale '46 MB' figure at :187 to the measured 52.4 MiB (Phases 2 and 6).
- `tests/test_ingest_command.py` — NEW — offline half (AC1-AC9) and a `gamedata` half against the PROBE only (AC10-AC15). MAIN-THREAD AUTHORED. Import `WRITERS` as `from test_read_only import WRITERS` and `PATTERNS` as `from test_no_leaks import PATTERNS` — there is no `tests/__init__.py` and no `conftest.py`, so pytest's prepend import mode puts `tests/` on `sys.path`, matching `tests/test_extraction_cost.py:39` (Phases 2, 3, 4, 5).
- `README.md` — Delete the `There is no ingest command` blockquote at :128-134 in full; extend the setup fence at :109-119 with `uv run python -m ootp_ai.ingest land` before the `reports render` line, plus a sentence noting the first run creates the eight declared tables (Phase 5).
- `CLAUDE.md` — Judged through `/update-docs`, not mechanically edited: the Status paragraph and the `src/ootp_ai/` project map, which lists `contracts/`, `warehouse/`, `validate/`, `reports/` and `catalog/` but no `ingest/` (Phase 5).
- `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md` — Add a dated amendment recording the `status`-verb boundary from Scope Decision §5: this request owns the disk-and-refusal half; that one owns the warehouse-inventory half (its :54-65, especially :61). Neither builds the verb now (Phase 5).
- `requests/feature-requests/ingest-command/IMPLEMENTATION_PLAN.md` — NEW — this plan. Opens `> **Status:** planned · created 2026-08-30 · decided · next: implement`.
- `requests/feature-requests/ingest-command/PROJECT_SCOPE.md` — Status header advanced from `scoped · … · decided · next: plan` to reflect that the plan exists.
- `requests/feature-requests/README.md` — Index row for `[ingest-command]` at :126 — Stage cell `scoped` → `planned`, then `implemented` when the work lands. `/commit` keeps this in step.
```text
- `requests/feature-requests/ingest-command/IMPLEMENTATION_REPORT.md` — NEW at stage 4 — the acceptance ledger plus Phase 6's measured numbers with dates and epistemic labels.
```
- `.claude/agents/data-engineer-memory.md` — OPTIONAL, and APPEND ONLY. Do not rewrite :202's dated entry — the file's own rule at :41 is append-freely-never-prune, and nothing in CI chases that path. If the promotion is worth recording, append one dated `verified` entry.

### Code references cited

- `src/ootp_ai/reports/__main__.py:36-59` — `main(argv: list[str] | None = None) -> int` with the 0/1/2 convention — `ConfigError` and a bad `--sim-date` return 2, `NoSuchSnapshot`/`WithheldFieldError`/`ValueError` return 1 as `f"{type(error).__name__}: {error}"` on stderr, success prints and returns 0. The shape the ingest command copies exactly.
- `src/ootp_ai/reports/__main__.py:125-151` — `_parser()` builds a `prog="python -m ootp_ai.reports"` parser and calls `add_subparsers(dest="command", required=True)` at :130 — which is why `main([])` RAISES `SystemExit(2)` rather than returning 2, and why AC2 must use `pytest.raises`.
- `src/ootp_ai/catalog/__main__.py:118-134` — `_fence_docs_root` is the record of the project's only operator-typed write root: it shipped with no validation at all while `.env`-supplied roots had been fenced since Phase 3. This is the precedent that drops `--snapshot-root` from the CLI.
- `src/ootp_ai/ingest.py:50-62` — `__all__` lists eleven names ending `parse_snapshot`. AC9 requires it byte-unchanged across the package promotion, which is why the shared function goes in a new `ingest/read.py` rather than into `ingest/__init__.py`.
- `src/ootp_ai/ingest.py:481-501` — `_describe(snapshot, entry, payload)` re-reads each file whole when `payload is None`; its docstring measures that at '~48 MB of avoidable I/O per ingest'. Confirmed by reading — this is why the shared function composes `take_snapshot + parse_snapshot` rather than `ingest_save`.
- `src/ootp_ai/ingest.py:300` — `dump_parse` is `_serialize(parse_snapshot(read_manifest(path)))` — the exact `read_manifest` → `parse_snapshot` composition `--from-snapshot` reuses, so that path needs no new parsing code.
- `src/ootp_ai/snapshot.py:189-201` — `take_snapshot` calls `next_ingest_seq(...)` when `ingest_seq is None` and only raises `SnapshotExists` when the resulting directory already exists — so an auto-allocating composition never surfaces ADR 0021's refusal and silently lands a duplicate. Verified line by line.
- `src/ootp_ai/snapshot.py:205` — `snapshot_dir.mkdir(parents=True)` is the single `mkdir` in `src/ootp_ai/`, which is why a module delegating file creation to `snapshot.py` needs no `WRITERS` entry.
- `src/ootp_ai/snapshot.py:307-308` — `_copy_one` computes `size = source.stat().st_size` and `digest = _digest(source)` on the SOURCE side before `shutil.copy2`. So the `size`/`sha256` stored in `ingest_run.source_files` are the save's own values, and the digest pre-flight can compare against them directly without a snapshot in hand. This is the fact the whole pre-flight design rests on.
- `src/ootp_ai/snapshot.py:285-293` — `_read_sim_date(save: SaveRef) -> SaveDate` reads `teams.dat` whole and returns `read_header(...).sim_date`. It has exactly one caller (:185), so promoting it to `read_sim_date` is a two-line rename plus an `__all__` entry.
- `src/ootp_ai/snapshot.py:254-269` — `verify_snapshot(snapshot_dir)`'s docstring says it is 'Called after landing a snapshot' — a sentence with zero callers in `src/` today, which `requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:160-161` already recorded as an open gap.
- `src/ootp_ai/warehouse/load.py:169-189` — `ensure_tables(connection, contracts=None)` creates any declared table the schema is missing and returns the created names; :176-178 states it deliberately does not repair a drifted table. Its only caller in the repo is `tests/fixtures/warehouse.py:93` — verified by grep.
- `src/ootp_ai/warehouse/load.py:203-217` — `land_snapshot`'s docstring is the explicit-vs-`None` `ingest_seq` decision: an integer claims exactly that sequence and refuses with `IngestRunExists`, and is the right call 'whenever the snapshot is the artifact you want the row to point at, which keeps the two stores naming the same attempt'; `None` allocates from the warehouse inside the transaction and is right when the snapshot is transient.
- `src/ootp_ai/warehouse/load.py:232-250` — The bounded deadlock retry re-allocates the sequence on each attempt, which only helps the `ingest_seq=None` branch — so passing an explicit sequence knowingly weakens contention behaviour (Risks §5).
- `src/ootp_ai/warehouse/load.py:146-154` — `ConcurrentLandingError`'s docstring names the exact failure the command must avoid: 'Telling an operator the first when the second is true sends them looking for a landing that never happened.' AC5's distinctness assertion follows directly.
- `src/ootp_ai/warehouse/load.py:540-572` — `table_digest` selects every column of every row for one triple ordered by the declared key and hashes each JSON-serialised row — a second full read of everything a landing just wrote. This is why per-table digests are deferred out of `--json` and why AC14's before/after assertion is affordable only as a test.
- `src/ootp_ai/warehouse/ingest_run.py:16-35` — The measured correction that `SELECT … FOR UPDATE` does not serialise two allocators — two connections both allocated `ingest_seq = 1` in 0.000 s, and the primary key is what actually prevents an overwrite. Read before adding any new SELECT to this module.
- `src/ootp_ai/warehouse/ingest_run.py:137-153` — `next_ingest_seq(cursor, save_id, sim_date)` takes a CURSOR and its docstring requires it be called inside the transaction that will insert the row. The pre-flight therefore needs its own plain connection-level SELECT rather than reusing this.
- `src/ootp_ai/warehouse/ingest_run.py:180-191` — `ingest_run_values` serialises `source_files` as a sorted JSON list of `{name, size, sha256, version}` per file — the exact material the digest pre-flight compares, including the `size` that makes the fast path possible.
- `src/ootp_ai/warehouse/ingest_run.py:238-268` — `read_ingest_run(connection, *, save_id, sim_date, ingest_seq)` decodes the three JSON columns and returns `None` if the triple never landed — the function the pre-flight uses once it knows the maximum sequence, and the one AC11 reads a landing back through.
- `src/ootp_ai/config.py:99-108` — `Settings` carries `managed: SaveRef`, `truth_save: SaveRef | None`, `probe_save: SaveRef | None` — so the target map must skip the `None`s a fresh clone and CI will have.
- `src/ootp_ai/config.py:111-113` — `load_settings(env: Mapping[str, str] | None = None)` takes a mapping and falls back to `.env` + `os.environ` — the injection point AC3's offline test uses to build a `Settings` with an unconfigured `save_id`.
- `src/ootp_ai/config.py:42-43` — `DEFAULT_SNAPSHOT_ROOT = Path("var/snapshots")` and `DEFAULT_OUTPUT_ROOT = Path("var/reports")` are CWD-relative on purpose because the repo is public — so the 'reports prints full paths' claim is false and must not be repeated; it prints whatever `output_root` resolves to, which stays relative by default.
- `src/ootp_ai/saves.py:81-84` — `is_challenge_mode(save: Path) -> bool` is a `is_file()` plus a 241-byte size check — the cheap, report-only mode line, and its module docstring at :10-15 says the check is 'cheap enough to run on every ingest'.
- `src/ootp_ai/parser/errors.py:25` — `SaveFormatError` is defined here, not in `parser/header.py` — the command's exception tuple must import it from `ootp_ai.parser.errors`.
- `src/ootp_ai/reports/resolve.py:78-94` — `landed_sim_dates(connection, *, save_id)` returns every landed in-game date oldest-first, and its docstring says it is public precisely because 'what does the warehouse hold for this universe' is the first question a second snapshot raises. Reused verbatim on the refusal path.
- `src/ootp_ai/reports/resolve.py:179-182` — `_nothing_landed_message` already tells the operator to 'run the ingest before rendering' — a sentence naming a command that does not exist, and the one AC8 requires this change to make true.
- `tests/test_read_only.py:303-317` — `WRITERS = {"snapshot.py", "reports/__main__.py", "catalog/__main__.py"}` as package-relative paths, with the comment at :299-302 recording that a bare `__main__.py` entry would have released every `__main__.py` in the tree. AC1 pins this set byte-unchanged.
- `tests/test_read_only.py:348-358` — `_writes_in(text)` matches write-mode `open(` via a regex and then scans `text.splitlines()` for `CREATIVE_CALLS`, stripping only `#` comments (`line.split("#", 1)[0]`). Docstrings are NOT stripped — so prose naming `.mkdir(` in a new module reds the guard. Verified by reading the function.
- `tests/test_read_only.py:240-242` — The AC11 docstring refuses landing inside the guard in terms: 'pulling a warehouse dependency into ADR 0001's guard would let an unrelated outage silence the one test the project cannot afford to lose.' This is why the pre-flight's warehouse lookup stays outside `read_save`.
- `tests/test_read_only.py:254,263,268` — The three legs each call `parse_snapshot(ingest_save(settings.X, settings=settings).snapshot)` in probe → truth → managed order, with the truth leg conditional on `settings.truth_save is not None` — hence four manifest passes when `OOTP_TRUTH_LEAGUE` is configured and three otherwise.
- `tests/test_read_only.py:182-193` — `_settings(tmp_path)` returns `replace(settings, snapshot_root=tmp_path / "snapshots")` after a `pytest.skip` on `ConfigError` — the idiom AC10 reuses to keep `--snapshot-root` off the CLI while making the exit-0 path a pytest assertion. Its comment at :187 says '46 MB directory per run', which the measured 52.4 MiB corrects.
- `tests/fixtures/warehouse.py:149-156` — `landed_probe` opens a `TemporaryDirectory`, calls `parse_snapshot(take_snapshot(save, snapshot_root=Path(tmp)))` at :151, lands with `_land(connection, parsed)` at :152 with no explicit sequence, and purges in `finally`. The three test-only powers to preserve, verbatim.
- `tests/fixtures/warehouse.py:93` — `ensure_tables(connection)` inside `warehouse_or_skip` — the repo's ONLY caller, confirmed by grep. Combined with `ops/mysql-bootstrap.sql` creating no tables, this is what makes the fresh-clone criterion unmeetable without the command calling `ensure_tables` itself.
- `tests/test_bronze_landing.py:761-772,812-815` — `_MUTATING_SQL` matches SQL shapes (`DELETE FROM`, `DROP TABLE|SCHEMA|…`, `TRUNCATE TABLE`, `REPLACE INTO`, `ON DUPLICATE KEY`, `UPDATE … SET`) and `_warehouse_sources()` globs `src/ootp_ai/warehouse/*.py`. A `SELECT COALESCE(MAX(ingest_seq), 0)` with no `SET` passes by construction — `FOR UPDATE` is exempt for the same reason.
- `tests/test_snapshot_semantics.py:537-577` — `test_two_sequences_of_one_sim_date_both_persist` lands a second time, asserts `second.ingest_seq > first.ingest_seq`, asserts the first landing's digests are unchanged, and purges in `finally` — the exact assertion shape AC14 copies for `--new-look`.
- `tests/test_extraction_cost.py:39,57,75` — The timing harness imports `landed_probe`, carries `DRIFT_FACTOR = 10.0`, and builds a module-scoped fixture from it — one of the two riskiest consumers of the re-point, and the reason a cheap `read_save` matters.
- `tests/test_parser_vs_export.py:56,130` — The Tier-B export diff imports `landed_probe` and drives it with `which="truth_save"` — it lands the STANDARD-mode save, which is why challenge-mode ENFORCEMENT is dropped and only reporting is folded in.
- `tests/test_no_leaks.py:37-41` — `PATTERNS` is a module-level `list[tuple[str, re.Pattern[str]]]` covering windows drive paths, unix home paths and email addresses — the exact list AC4 imports rather than restates.
- `tests/test_doc_links.py:48,153-155` — `BARE_REQUEST_TOKEN` matches only `requests/…` tokens and the resolver checks `(REPO_ROOT / token).exists()`. Nothing chases `src/ootp_ai/ingest.py` in prose, so the package promotion cannot red the doc-link build.
- `tests/test_repo_structure.py:12-30` — `test_required_docs_exist` pins a fixed list of documents and does NOT pin README content — so AC8's README assertions need the new `tests/test_ingest_command.py`, not an edit here.
- `ops/mysql-bootstrap.sql:23,30,42,54,57-63` — Three `CREATE DATABASE`, one `CREATE USER`, database-scoped `GRANT ALL PRIVILEGES` on three named schemas. No `CREATE TABLE` anywhere, and no rights to create a throwaway schema — verified by reading the whole 66-line file.
- `docs/decisions/0021-bronze-landing-is-append-only.md:21-27` — ADR 0021 names a `(save_id, sim_date)`-keyed refusal by design and calls it 'worse, because it blocks a legitimate and frequent operation'. This is what makes the digest pre-flight the only option needing no ADR amendment.
- `docs/decisions/0021-bronze-landing-is-append-only.md:57-59` — 'A parser fix re-lands the same snapshot at the next sequence, and both readings stay on disk' — the correction workflow `--from-snapshot` implements, and the reason it lands with a warehouse-allocated sequence rather than the directory's number.
- `pyproject.toml:51-52` — `[tool.hatch.build.targets.wheel] packages = ["src/ootp_ai"]` — a whole-package declaration, so promoting `ingest.py` to `ingest/` needs no packaging edit. `[project.scripts]` is absent, confirming `uv run python -m ootp_ai.<package>` as the established invocation.
- `pyproject.toml:95,99-108` — mypy runs strict over `["src", "tests"]` and pytest declares exactly one marker, `gamedata`, under `--strict-markers` — so the new tests must be fully annotated and may only use that marker.
- `.claude/agents/data-engineer.md:154-157` — The repo-level deny set for the write-capable builder includes `tests/` ('the guards that catch you'), which is why every test file in this plan is authored on the main thread.
- `requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:144-146,156-161` — Prior art, not fresh discovery: 'No tracked entry point performs an ingest … on a fresh machine the eight tables come into existence as a side effect of running the suite', '`ensure_tables` never repairs a drifted table', and '`verify_snapshot` has no production caller'. All three were recorded here first.

### Open questions

- AC1's literal import spelling is wrong for this repo's layout. It says `from tests.test_read_only import WRITERS`, but there is no `tests/__init__.py` and no `conftest.py` anywhere in the tree, so pytest's prepend import mode puts `tests/` itself on `sys.path` — which is exactly how `tests/test_extraction_cost.py:39` reaches `from fixtures.warehouse import …`. The plan prescribes `from test_read_only import WRITERS`. Confirm by running it in Phase 2; if the dotted form also resolves, either is acceptable, but the sys.path-proven spelling is the one to ship.
- Where `verify_snapshot` belongs — inside `read_save` or only in the command's `land()`. The plan puts it in `land()`, OUTSIDE the shared function, on two grounds: it reads the snapshot copy rather than the game, so it changes neither AC11's manifest diff nor its bracket; and putting it inside would add a full 52.4 MiB re-digest to every `landed_probe` call, i.e. to the timing harness at `tests/test_extraction_cost.py:75` and the Tier-B diff at `tests/test_parser_vs_export.py:130`, on every `-m gamedata` run. If Phase 6's measurement shows the cost is trivial, moving it inside is defensible — but it is a decision, not a detail.
- Whether the pre-copy reconciliation refusal (refuse when the filesystem sequence would be ≤ the warehouse maximum) is inside this scope. The plan says yes and argues it: Scope Risks §4 explicitly hands the reconciliation choice to the plan, and this is not a change to landing semantics — it is `IngestRunExists`, moved earlier and made cheap, so the operator does not pay 52.4 MiB and an orphan directory for a refusal that was knowable from two integers. Flag it to the operator at the gate; it is the one place this plan goes past the scope's literal 'print the reasoning line'.
- What `--from-snapshot` should do when the snapshot's own directory number is already landed in the warehouse. With `ingest_seq=None` (this plan's choice, following ADR 0021:57-59) the re-land simply takes the next warehouse sequence and `IngestRunExists` is never reached on that path — which means Scope Decision §3's claim that `--from-snapshot` is 'the only way the `IngestRunExists` refusal is reachable through the command' no longer holds once the pre-copy reconciliation lands. AC5 proves that refusal by monkeypatching `land_snapshot`, so nothing untestable follows; but the scope's sentence should be read as superseded rather than silently contradicted.
- Whether the `--json` payload should carry a `verdict` field naming the pre-flight outcome (`no-prior` / `changed` / `unchanged`). It costs nothing and gives `incremental-loading` the discriminator that a distinct exit code 3 was dropped for. The plan includes `source_changed` as a boolean; a three-valued field is strictly more informative and is cheaper to add now than after that request writes its procedure against the shape.

## Planner: `sequencing`

### Architecture notes

The change is a third instance of an established shape, wrapped around existing library code. Nothing new is parsed, no contract moves, and `docs/warehouse-catalog.md` must be byte-identical afterwards.

**Current shape.** `src/ootp_ai/` ships two entry points and both only READ a landing: `reports/__main__.py` and `catalog/__main__.py`. The ingestion path itself is three library calls nobody composes outside `tests/`: `snapshot.take_snapshot(save, snapshot_root=...)` (snapshot.py:167) -> `ingest.parse_snapshot(snapshot)` (ingest.py:161) -> `warehouse.load.land_snapshot(connection, parsed, ingest_seq=...)` (load.py:195). The only composer is `tests/fixtures/warehouse.py:151-152`.

**Where the new code hooks in.** Four seams, in dependency order:

1. `src/ootp_ai/ingest.py` becomes `src/ootp_ai/ingest/__init__.py` (content byte-identical) so that `python -m ootp_ai.ingest` can resolve a `__main__`. This is import-transparent for all ten `from ootp_ai.ingest import ...` sites (tests/fixtures/warehouse.py:43, tests/test_bronze_landing.py:44, tests/test_grain_contracts.py:68, tests/test_extraction_cost.py:41, tests/test_provenance.py:30, tests/test_parser_vs_export.py:59, tests/test_read_only.py:46, tests/test_snapshot_semantics.py:73, src/ootp_ai/warehouse/load.py:90, src/ootp_ai/warehouse/ingest_run.py:57).

2. A NEW module `src/ootp_ai/ingest/read.py` holds the one shared game-touching function. It does NOT go into `ingest/__init__.py`, because AC9 requires `ingest.__all__` (ingest.py:50-62) be unchanged and because a new module keeps the Phase-1 move a pure rename that git can detect. Its three callers are the command's `land()`, `tests/fixtures/warehouse.py::landed_probe`, and `tests/test_read_only.py`'s three AC11 legs.

3. A NEW module `src/ootp_ai/ingest/__main__.py` holds `main(argv) -> int` over a testable `land(settings, *, save_id=None, snapshot_root=None, new_look=False, from_snapshot=None, as_json=False) -> IngestRun`. It creates no file and opens nothing for writing — every directory it needs comes from `snapshot.py:205` — which is what keeps `tests/test_read_only.py:303-317`'s `WRITERS` byte-unchanged, since `_writes_in` (`:344-358`) is a scan of a module's own source text, not a capability model.

4. `src/ootp_ai/warehouse/ingest_run.py` gains one read-only helper, `latest_ingest_seq(connection, *, save_id, sim_date) -> int`, a plain `SELECT COALESCE(MAX(ingest_seq), 0) ... WHERE save_id=%s AND sim_date=%s` with NO `FOR UPDATE`. It is deliberately not `next_ingest_seq` (`:137-153`), whose docstring at `:140-143` requires it be called inside the inserting transaction.

**The pre-flight's data path, and why it is sound.** `_copy_one` (snapshot.py:296-319) digests the SOURCE at `:308` and refuses at `:313` unless the destination matches, so the `sha256` values that reach `ingest_run.source_files` (ingest_run.py:180-191) are provably the save's own bytes at copy time. Comparing today's save-side sizes and digests against a prior landing's `source_files` is therefore a valid same-bytes test. The lookup composes two existing public functions: `latest_ingest_seq(...)` to find the sequence, then `read_ingest_run(connection, save_id=..., sim_date=..., ingest_seq=...)` (ingest_run.py:238-268), which decodes `source_files` from JSON because it is in `_JSON_COLUMNS` (`:88`).

**The one structural tension the plan resolves.** Goal 3 requires every game-touching line to sit inside one shared function, while Core requires the warehouse lookup to stay outside it. But the sim date must be read from the game BEFORE the warehouse can be queried for that date's prior landing. The plan resolves this with a callback parameter rather than a plain value: `read_save(save, *, snapshot_root, prior_landing=None, new_look=False)` where `prior_landing` is `Callable[[SaveDate], Sequence[Mapping[str, object]] | None] | None`. `read_save` reads the sim date (game), invokes the callback (warehouse — supplied by the command, `None` at both test call sites), digests (game), refuses or copies (game), parses. AC11's legs and `landed_probe` pass `None`, so no MySQL dependency enters ADR 0001's guard, and the manifest-pass count stays 4-with-truth / 3-without. `snapshot._read_sim_date` is still promoted to public `read_sim_date` and added to `snapshot.__all__` (snapshot.py:50-63), because the command's own error paths and any future `status` verb need the cheap answer to *what date would this land at?* without ~52 MB being copied.

**What stays where.** `purge_snapshot` never moves into `src/` (warehouse/load.py:68-74 names a convenience purge as exactly how append-only stops being true). No `DELETE`/`UPDATE` is added under `src/ootp_ai/warehouse/`; `tests/test_bronze_landing.py:818-829` scans that package and would fail. `ingest_save` (ingest.py:436) keeps its caller in `tests/test_provenance.py:30` and is not orphaned.

### Files to read first

- `requests/feature-requests/ingest-command/PROJECT_SCOPE.md` — The decided upstream artifact. Read the whole thing; the phases below implement its Core tier and its 19 acceptance criteria verbatim. Decisions §1 (digest pre-flight), §2 (package promotion), §3 (--from-snapshot), §4 (implicit ensure_tables), §5 (no status verb), §6 (managed default, no prompt) are settled and must not be re-opened.
- `src/ootp_ai/reports/__main__.py` — The pattern this command is the third instance of. `:1-11` records that entry points are deliberate; `:36-59` is the `main(argv) -> int` shape with the 0/1/2 convention; `:62-73` is the testable `render(settings, *, save_id=None, ...)`; `:125-151` is argparse with `required=True` on the subparser, which is why `main([])` raises SystemExit(2) rather than returning.
- `src/ootp_ai/ingest.py` — The 502-line module being promoted to `ingest/__init__.py` in Phase 1. `:50-62` is the `__all__` that AC9 requires be left unchanged (so the new shared function goes in a NEW module, not here); `:161-217` `parse_snapshot`; `:281-300` `dump_parse`, whose `read_manifest` -> `parse_snapshot` composition is exactly what `--from-snapshot` reuses; `:481-501` `_describe` and its measured ~48 MB warning, which is why the shared function is take_snapshot+parse_snapshot and NOT `ingest_save`.
- `src/ootp_ai/snapshot.py` — Everything the pre-flight needs and the trap it avoids. `:167-216` `take_snapshot` — `:189-191` auto-allocates the next filesystem sequence and never raises, which is why naive composition silently lands a duplicate; `:205` is the `mkdir` that keeps `WRITERS` unchanged; `:285-293` `_read_sim_date` (promoted to public `read_sim_date` in Phase 2); `:296-319` `_copy_one`, which digests the SOURCE at `:308` and proves the copy identical at `:313` — that proof is what makes comparing today's save digests against a prior landing's `source_files` valid.
- `src/ootp_ai/warehouse/ingest_run.py` — `:156-198` `ingest_run_values` — `source_files` at `:180-191` carries per-file `name`, `size`, `sha256`, `version`, which is the entire material the digest pre-flight compares against. `:238-268` `read_ingest_run` decodes it back (`_JSON_COLUMNS` at `:88` includes `source_files`). `:137-153` `next_ingest_seq` is deliberately NOT reused: `:140-143` requires it be called inside the inserting transaction, and CLAUDE.md records that this repo already got its locking semantics wrong once.
- `src/ootp_ai/warehouse/load.py` — `:169-189` `ensure_tables` — one caller in the whole repo (`tests/fixtures/warehouse.py:93`), and `:176-178` states it creates but never repairs a drifted table. `:195-250` `land_snapshot`; `:203-217` is the explicit-vs-None `ingest_seq` contract the command must choose deliberately; `:232-250` is the deadlock retry that only re-allocates on the `None` branch.
- `tests/test_read_only.py` — ADR 0001's proof, and the phase-2 re-point target. `:222-269` is AC11 with its three legs at `:254`, `:263`, `:268`; `:240-242` explicitly refuses to include landing and says why. `:303-317` is `WRITERS`, which AC1 requires stay byte-identical; `:344-358` `_writes_in` is a source-TEXT scan, which is why a module that delegates all file creation to `snapshot.py` needs no allowlist entry. `:182-193` is the `replace(settings, snapshot_root=tmp)` idiom AC10 reuses.
- `tests/fixtures/warehouse.py` — The de facto ingestion path being replaced. `:133-157` `landed_probe` composes `parse_snapshot(take_snapshot(...))` at `:151` and lands with `ingest_seq=None` at `:152`; `:19-26` explains why `None` is required there (a temp directory always allocates 1 on the filesystem side). Its three test-only powers — the TemporaryDirectory root, `ingest_seq=None`, and `purge_snapshot` in `finally` at `:154-156` — must survive the re-point unchanged.
- `tests/fixtures/README.md` — `:44-49` — this repo has NO conftest.py anywhere, `fixtures` is declared first-party in pyproject.toml, and the house import form is `from fixtures.warehouse import ...`; a `from tests.fixtures...` form 'passes locally and fails elsewhere'. This directly corrects the scope's AC1, which spells the import as `from tests.test_read_only import WRITERS`.
- `ops/mysql-bootstrap.sql` — Verify for yourself, as the scope instructs. Three `CREATE DATABASE` (`:23`, `:30`, `:42`), one `CREATE USER` (`:54`), database-scoped grants only (`:57-63`). No tables and no rights to create a throwaway schema — this is what makes implicit `ensure_tables` load-bearing for Goal 2, and what makes an automated empty-schema test unrunnable (hence AC18 is USER-RUN).
- `docs/decisions/0021-bronze-landing-is-append-only.md` — `:21-27` rejects the date-keyed refusal BY NAME ('the obvious fix ... is worse'), which is why the default is the digest pre-flight and not a `(save_id, sim_date)` refusal. `:42-55` states the three parts, including `:50-55`'s AST scan over `src/ootp_ai/warehouse/` that any new query in that package must pass.
- `tests/test_bronze_landing.py` — `:761-772` `_MUTATING_SQL` and `:812-829` the scan that enforces ADR 0021 §3 over `src/ootp_ai/warehouse/*.py`. A new `SELECT COALESCE(MAX(ingest_seq), 0) ...` there is safe (`:847` explicitly exempts the locking read), but the implementer must know the scan exists before adding SQL. It also carries the `_FakeConnection` pattern the offline tests copy.

### Phases

#### Phase 1 — Phase 0 — Measure the three assumed numbers before building on them

**Goal:** Turn the four claims the design rests on from `assumed` into `measured`, and settle the sequence-reconciliation rule, BEFORE any code depends on them. The scope's own Affected Area section closes with 'Before writing the plan, run one query' — this phase runs it and the three it forgot.

**Steps:**

```text
- M1 — Allocator drift. Run `SELECT save_id, sim_date, MAX(ingest_seq) FROM ingest_run GROUP BY 1, 2;` against `MYSQL_DATABASE` and list `var/snapshots/<save_id>/<sim_date>/`. Reproduce the three-row table in Risks §4 of the scope and confirm or correct it. This decides Phase 5's reconciliation rule.
- M2 — The size fast path's real hit rate. `docs/data-access.md:71-91` records `names.dat` at a byte-identical 8,642,110 B across all three saves on disk, and `storylines.dat`, `weather.dat`, `games_in_progress.dat`, `trades.dat` and `offers.dat` likewise. Measure, for the probe save, today's `stat().st_size` for each of the five `SNAPSHOT_FILES` (snapshot.py:77-83) against the `source_files` sizes of its most recent `ingest_run` row. Record how many of the five differ. If zero or one differ on a genuinely simmed save, the fast path rarely settles anything and the digest is the common case, not the exception — say so, with the number.
- M3 — Cost of a full source-side digest. Time SHA-256 over all five `SNAPSHOT_FILES` of the probe save (the pre-flight's worst case). Compare against the ~52 MB `shutil.copy2` that `take_snapshot` performs. Risks §2 requires the plan to pick digest-before-copy or copy-then-compare and SAY WHICH, with numbers on both sides.
- M4 — Cost of `verify_snapshot`. Time `snapshot.verify_snapshot(path)` (snapshot.py:254-279) over an existing landed snapshot directory. This is the folded-in cheap win's measurement obligation; the scope says 'The plan measures the added seconds and records the number.'
- Write all four numbers, each with an epistemic label and today's date, into `requests/feature-requests/ingest-command/reviews/measurements.md`. Nothing under `src/` changes in this phase.
- Choose and record the sequence-reconciliation rule from M1's result: either `max(filesystem_seq, warehouse_max + 1)` with a printed reasoning line, or the filesystem sequence with a printed 'filesystem allocated N, warehouse holds M' line. Both satisfy the scope; M1 decides which is honest.
```

**Acceptance:**

- `reviews/measurements.md` exists and carries four numbered measurements, each labelled `measured <YYYY-MM-DD>` per CLAUDE.md's epistemics rule.
- M1's table names all three saves on disk and states, for each, whether the filesystem sequence and `MAX(ingest_seq)` agree — matching or explicitly correcting the scope's Risks §4 table.
- M3 records both a digest-before-copy figure and a copy-then-compare figure, and the file states which was chosen and why.
- The sequence-reconciliation rule is written as one sentence a Phase 5 implementer can code from without re-deciding.
- `git status` shows changes only under `requests/feature-requests/ingest-command/reviews/`. `uv run pytest -m "not gamedata"`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` are green (unchanged — this phase touches no Python).

**Commit note:** Measure the four numbers the ingest command's design assumes: allocator drift across all three saves, the size fast path's real hit rate, source-side digest cost against the ~52 MB copy, and verify_snapshot's added seconds. No code.

#### Phase 2 — Phase 1 — Promote `ingest.py` to a package, byte-for-byte

**Goal:** Make `python -m ootp_ai.ingest` able to host a `__main__` without changing one line of behaviour, and prove the promotion is import-transparent. Done first and alone because it is a 502-line move with a wide blast radius and zero logic — mixing it with anything else makes the diff unreviewable.

**Steps:**

- Find every reference to the old path BEFORE moving. `grep -rn 'ootp_ai/ingest\.py\|ootp_ai\.ingest'` over the repo. The single live line-numbered reference is `.claude/agents/data-engineer-memory.md:202` (evidence line citing `src/ootp_ai/ingest.py`).
- Move `src/ootp_ai/ingest.py` to `src/ootp_ai/ingest/__init__.py` with content byte-identical — no reflow, no import reorder, no docstring edit. Prefer `git mv` run by the operator so history records a rename; a plain filesystem move is acceptable and git will record delete+add.
- Correct `.claude/agents/data-engineer-memory.md:202` to `src/ootp_ai/ingest/__init__.py`.
- Do NOT rewrite any `requests/**/reviews/` handoff or IMPLEMENTATION_REPORT that cites `ingest.py:NNN`. Those are the record of what was believed when (scope Risks §12).
- Leave all ten `from ootp_ai.ingest import ...` sites untouched.

**Acceptance:**

- `uv run pytest -m "not gamedata"` is green — in particular `tests/test_provenance.py`, `tests/test_bronze_landing.py`, `tests/test_contracts_loader.py`, `tests/test_agent_contract.py` and `tests/test_doc_links.py`.
- `uv run python -c "import ootp_ai.ingest as m; print(sorted(m.__all__))"` prints exactly `['IngestRun', 'PARSED_FILES', 'ParsedSnapshot', 'SnapshotDateMismatch', 'SourceFile', 'UndecodedRecords', 'check_decoded', 'check_sim_dates', 'dump_parse', 'ingest_save', 'parse_snapshot']` — the same eleven names as ingest.py:50-62.
- `git diff -M --stat` shows the move as a rename with zero content delta (or, if git recorded delete+add, `git show :src/ootp_ai/ingest/__init__.py | diff - <the pre-move file>` is empty).
- `uv run ruff check . && uv run ruff format --check .` and `uv run mypy` are green.
- `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py` is green — proving the promotion did not break the gamedata importers either.

**Commit note:** Promote src/ootp_ai/ingest.py to a package so `python -m ootp_ai.ingest` can host an entry point. Content byte-identical; all ten importers unchanged; the one live line-numbered reference in the agent memory corrected.

#### Phase 3 — Phase 2 — The one shared game-touching function, with ADR 0001's proof re-pointed onto it

**Goal:** Establish the single function through which every game read the operator's command makes will pass, and move ADR 0001's manifest-diff proof and the test fixture onto it — BEFORE any command exists to call it. Ordered second because it is the phase that could weaken the one test the project cannot afford to lose, and it must be proved green on its own.

**Steps:**

- Promote `snapshot._read_sim_date` (snapshot.py:285-293) to public `read_sim_date`, add it to `snapshot.__all__` (snapshot.py:50-63), and give it a docstring saying why it is public: it is the only cheap answer to *what date would this land at?* before ~52 MB is copied. Update its one internal caller at snapshot.py:185.
- Add a public source-side facts helper to `snapshot.py`: `source_facts(save: SaveRef) -> tuple[SnapshotFile, ...]` — `stat().st_size` and `_digest()` for each of `SNAPSHOT_FILES`, reusing the existing private `_digest` (snapshot.py:322-328) rather than promoting it. It lives in `snapshot.py` because that module already owns both the digest helper and the `SnapshotFile` type. Add it to `__all__`. It reads only; it creates nothing, so `WRITERS` is untouched.
- Create `src/ootp_ai/ingest/read.py` with `read_save(save, *, snapshot_root, prior_landing=None, new_look=False) -> ParsedSnapshot` and its own `__all__` — NOT added to `ingest.__all__`, which AC9 requires be unchanged. Body, in this exact order: (1) `sim_date = read_sim_date(save)`; (2) if `prior_landing` is not None and not `new_look`, call `prior_landing(sim_date)` and, when it returns a source list, compare it against `source_facts(save)` and raise `SourceUnchanged` when they match; (3) `snapshot = take_snapshot(save, snapshot_root=snapshot_root)`; (4) `return parse_snapshot(snapshot)`. `ingest_seq` is NEVER a parameter — the sequence decision belongs to whoever calls `land_snapshot`.
- Define `SourceUnchanged` in `ingest/read.py` with a docstring that quotes ADR 0021's position: an unchanged-bytes re-run is a no-op, not a new look, and `--new-look` is the override the ADR's own vocabulary names.
- Put the pure comparison in the same module as a separately-testable function: `sources_match(prior: Sequence[Mapping[str, object]], current: Sequence[SnapshotFile]) -> bool`. Three rules, each with a test: a file in `current` absent from `prior` means CHANGED (never unchanged) — this is what protects against the 2026-08-16 `SNAPSHOT_FILES` widening; any size mismatch returns False without any digest being consulted; only when every size matches are the `sha256` values compared.
- `read_save`'s docstring names its three callers by path and states that changing it changes what the operator's command does.
- Re-point `tests/test_read_only.py`'s three AC11 legs (`:254`, `:263`, `:268`) from `parse_snapshot(ingest_save(...).snapshot)` onto `read_save(save, snapshot_root=settings.snapshot_root)`. Update the test docstring at `:233-243` to say the guard now brackets every game read the operator's command makes, and keep `:240-242`'s statement of why landing stays outside. No fourth leg, no MySQL, no change to the manifest-pass count.
- Re-point `tests/fixtures/warehouse.py::landed_probe:151` onto `read_save(save, snapshot_root=Path(tmp))`, leaving `_land(connection, parsed)` at `:152` with `ingest_seq` still defaulting to `None`, the `TemporaryDirectory` at `:149`, and `purge_snapshot` in `finally` at `:154-156` exactly as they are. Add one sentence to its docstring saying the landing path is now shared with the operator's command.
- Author every test on the main thread. `tests/` is in the write-capable builder's deny set (`.claude/agents/data-engineer.md:154-157`).

**Acceptance:**

- Offline, in a new `tests/test_ingest_command.py`: `sources_match` returns True on identical lists; False when one size differs, proved by passing a digest-comparison that would raise if reached; False when one sha256 differs; False when `current` names a file `prior` does not; False on an empty `prior`. `uv run pytest -m "not gamedata" tests/test_ingest_command.py` is green.
- `uv run python -c "import ootp_ai.snapshot as s; assert 'read_sim_date' in s.__all__ and 'source_facts' in s.__all__"` exits 0, and `uv run python -c "import ootp_ai.ingest as m; print(len(m.__all__))"` still prints 11.
- `uv run pytest tests/test_read_only.py` (offline half) is green and `WRITERS` is byte-unchanged — `git diff tests/test_read_only.py` shows no line inside `:303-317`.
- `uv run pytest -m gamedata tests/test_read_only.py` is green, and its wall clock is recorded and is not materially above the 2m35s baseline at `tests/test_read_only.py:25-28`. `test_the_manifest_is_not_vacuous` is green alongside it.
- `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py` is green — the full real `landed_probe` consumer set. Explicitly confirm `test_parser_vs_export.py:130`'s `which="truth_save"` path still works and `landed_probe` still lands with `ingest_seq=None`.
- A gamedata test asserts the routing behaviourally, not by string scan: `monkeypatch.setattr("fixtures.warehouse.read_save", spy)` where `spy` wraps and delegates to the real function, then `landed_probe` is driven and exactly one recorded call is asserted.
- `uv run ruff check . && uv run ruff format --check .` and `uv run mypy` are green.

**Commit note:** One shared game-touching function (ingest/read.py::read_save) composing take_snapshot + parse_snapshot, with snapshot.read_sim_date and snapshot.source_facts promoted to public API. ADR 0001's three AC11 legs and tests/fixtures/warehouse.py::landed_probe both re-pointed onto it; WRITERS byte-unchanged; manifest-pass count unchanged.

#### Phase 4 — Phase 3 — The warehouse side of the pre-flight, as library code with no CLI

**Goal:** Add the single read-only query the pre-flight and the dual-allocator line both need, and prove it offline against a fake cursor. Kept separate from Phase 4 so that ADR 0021's mutation scan over `src/ootp_ai/warehouse/` is exercised against the new SQL in isolation.

**Steps:**

- Add `latest_ingest_seq(connection, *, save_id, sim_date) -> int` to `src/ootp_ai/warehouse/ingest_run.py` and to its `__all__` (`:61-71`). Body: `SELECT COALESCE(MAX(`ingest_seq`), 0) AS used FROM `ingest_run` WHERE `save_id` = %s AND `sim_date` = %s` — every identifier through `quote_ident`, both values bound, and NO `FOR UPDATE`.
- Its docstring must state, in terms, that this is deliberately not `next_ingest_seq` (`:137-153`): that function's contract at `:140-143` requires it be called inside the transaction that inserts the row, and CLAUDE.md records that this repo already got its locking semantics wrong once. This function answers 'what does the warehouse hold' outside any transaction, and its answer is a display value and a pre-flight input, never a claim.
- Add a small `prior_landing_sources(connection, *, save_id, sim_date) -> list[dict] | None` helper — composed from `latest_ingest_seq` plus the existing `read_ingest_run` (`:238-268`), returning `None` when the sequence is 0. This is the callable the command hands to `read_save` as `prior_landing`. Put it in `src/ootp_ai/ingest/read.py` or a sibling under `ingest/`, NOT under `warehouse/`, so the warehouse package gains exactly one new function.
- Do not touch `land_snapshot`, `claim_ingest_run`, `ingest_run_values` or the retry.

**Acceptance:**

- `uv run pytest -m "not gamedata" tests/test_bronze_landing.py` is green — in particular `test_no_module_in_the_warehouse_can_mutate_a_landed_row` (`:818`), which now scans the new SELECT and must pass, and the guard's own self-test which pins `'SELECT MAX(ingest_seq) FROM ingest_run FOR UPDATE'` as innocent (`:847`).
- An offline test in `tests/test_ingest_command.py` drives `latest_ingest_seq` against a fake cursor in the `_FakeConnection` style already used in `tests/test_bronze_landing.py`, asserting: 0 when the table holds no row for the pair; N when it holds N; and that the emitted statement contains no `FOR UPDATE` (a string assertion on the executed statement is legitimate here because the absence IS the contract).
- An offline test asserts `prior_landing_sources` returns `None` when `latest_ingest_seq` yields 0, and returns the decoded `source_files` list otherwise — proving the JSON decode path (`ingest_run.py:263-267`) is used rather than a raw string being compared.
- `uv run python -c "from ootp_ai.warehouse.ingest_run import latest_ingest_seq"` exits 0 and `latest_ingest_seq` appears in that module's `__all__`.
- `uv run pytest -m "not gamedata"`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` are green.

**Commit note:** One read-only warehouse helper for the ingest pre-flight: latest_ingest_seq, a plain MAX(ingest_seq) SELECT with no FOR UPDATE, deliberately not the in-transaction allocator. Plus the prior-landing source lookup that composes it with read_ingest_run.

#### Phase 5 — Phase 4 — The command: argparse, target resolution, error surface, output contract — all provable offline

**Goal:** Ship `uv run python -m ootp_ai.ingest land` with everything a test can prove without a game, a save or MySQL. Ordered before the gamedata phase so that seven of the nine offline acceptance criteria go green in CI first, and the gamedata run has a known-good CLI to exercise.

**Steps:**

- Create `src/ootp_ai/ingest/__main__.py` following `src/ootp_ai/reports/__main__.py` exactly: a module docstring recording why this entry point exists and that it creates no file (which is what keeps `WRITERS` unchanged, and is a requirement rather than an accident); `main(argv: list[str] | None = None) -> int`; a testable `land(settings, *, save_id=None, snapshot_root=None, new_look=False, from_snapshot=None) -> IngestRun`; `_parser()`; and `if __name__ == "__main__": raise SystemExit(main())`.
- `_parser()`: `prog="python -m ootp_ai.ingest"`, `sub = parser.add_subparsers(dest="command", required=True)` matching reports/__main__.py:130, one `land` subparser carrying `--save-id`, `--new-look` (store_true), `--from-snapshot` (metavar DIR), `--json` (store_true). Add NOTHING else — no `--sim-date` (the in-game date is read from `teams.dat`'s header, never supplied), no `--snapshot-root`, no `--ingest-seq`, no `--force`.
- Target resolution: build `{ref.save_id: ref for ref in (settings.managed, settings.truth_save, settings.probe_save) if ref is not None}` — skipping the `None`s a fresh clone and CI will have (config.py:104-105). Absent `--save-id` resolves to `settings.managed`. An unknown id returns exit 2 with a message naming every configured `save_id`. No `saves.enumerate_saves` sweep, so a filesystem path passed as `--save-id` is simply not found and is rejected.
- Fail-fast ordering, written as a comment because it is not the natural order: settings -> target -> `connect_warehouse` -> `ensure_tables` -> pre-flight -> `read_save` -> `land_snapshot`. MySQL down must fail before ~52 MB is copied; a snapshot with no landing behind it is an orphan.
- Error surface, caught by explicit name because they share no base class. `ConfigError` -> 2. A tuple of `(IngestRunExists, ConcurrentLandingError, SnapshotExists, SnapshotCorrupt, SnapshotDateMismatch, SaveFormatError, UndecodedRecords, LoadError, SourceUnchanged)` -> 1, printed as `f"{type(error).__name__}: {error}"` on stderr. Import `SaveFormatError` from `ootp_ai.parser.errors`.
- The stdout contract: the RESOLVED `save_id` (printed, not assumed — `.env` and the warehouse can disagree), the `sim_date` as `YYYY-MM-DD`, the `ingest_seq`, and the per-table row counts from the returned `IngestRun`. NO absolute path on stdout. State in a comment that the rule is stdout-only and that a `ConfigError` on stderr may name the offending path, because a misconfiguration message that does not is not actionable.
- Author `tests/test_ingest_command.py`'s offline half on the main thread. Note the import spelling: this repo has no conftest.py and `tests/` is on sys.path via pytest's prepend mode (`tests/fixtures/__init__.py:4`), so the pin is `from test_read_only import WRITERS`, NOT the `from tests.test_read_only import ...` form the scope's AC1 writes — `tests/fixtures/README.md:47-49` records that the latter 'passes locally and fails elsewhere'. If ruff's isort classifies `test_read_only` as third-party and reorders it, add `"test_read_only"` to `known-first-party` in `pyproject.toml:88` rather than fighting the formatter.

**Acceptance:**

- AC2: `_parser().parse_args(["land"]).command == "land"`; `--save-id`, `--new-look`, `--from-snapshot` and `--json` all parse; each of `--sim-date`, `--snapshot-root`, `--ingest-seq`, `--force` raises `SystemExit`; and `with pytest.raises(SystemExit) as exc: main([])` gives `exc.value.code == 2`.
- AC3: with `Settings` built through `load_settings(mapping)` (config.py:111) and monkeypatched into the command module, an unknown `--save-id` returns 2 and the error names every configured `save_id`; absent `--save-id` resolves to `settings.managed`; a filesystem path passed as `--save-id` is rejected rather than resolved.
- AC4: given a synthetic `IngestRun` and a snapshot root, the printed success block carries the `save_id`, the `sim_date` as `YYYY-MM-DD`, the `ingest_seq` and the per-table row counts, and matches NONE of `tests/test_no_leaks.py`'s `PATTERNS` (`:37-41`) — imported (`from test_no_leaks import PATTERNS`), not restated. `uv run pytest tests/test_no_leaks.py` stays green.
- AC5: with `land_snapshot` monkeypatched to raise `IngestRunExists`, `main(["land"])` returns 1 and the message names the triple; with it raising `ConcurrentLandingError`, the message is DISTINCT from the `IngestRunExists` one (load.py:146-154 warns that conflating them sends the operator looking for a landing that never happened); with `load_settings` raising `ConfigError`, `main(["land"])` returns 2. A parametrised test walks the whole nine-exception tuple and asserts each yields 1 rather than a traceback.
- AC6 (command half): `ootp_ai.ingest.__main__`'s `read_save` reference is monkeypatched with a recording spy, `land(...)` is driven with `land_snapshot` stubbed, and exactly one recorded call is asserted — behavioural, not a source scan.
- AC7: a spy records call order on a `land` invocation whose later stages are stubbed, and asserts `ensure_tables` appears exactly once and at an index before `read_save`.
- AC1: `from test_read_only import WRITERS; assert WRITERS == {"snapshot.py", "reports/__main__.py", "catalog/__main__.py"}`, with a comment saying the new module is deliberately absent because it creates no file. `uv run pytest tests/test_read_only.py` is green with the new module present in `SRC.rglob("*.py")` — both `test_only_allowlisted_modules_can_write_a_file` and `test_the_pipeline_contains_no_destructive_filesystem_call` pass.
- AC9: `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` (strict over `src` and `tests`, pyproject.toml:93-95) are green. `uv run pytest -m "not gamedata"` is green with no new skips.

**Commit note:** uv run python -m ootp_ai.ingest land: argparse with a required subcommand, target resolution by configured save name, fail-fast ordering, the nine-exception refusal surface at exit 1, ConfigError at 2, and a stdout contract carrying no absolute path. Nine offline criteria proved in CI; WRITERS byte-unchanged.

#### Phase 6 — Phase 5 — The re-run default, the sequence policy, and --from-snapshot, proved against real bytes

**Goal:** Wire the pre-flight and the explicit-sequence policy end to end and prove all six gamedata criteria against the PROBE save only. This is the phase where the operator-facing default that `incremental-loading` will write its procedure against actually becomes real.

**Steps:**

- Wire `prior_landing_sources(connection, save_id=..., ...)` into `land()` as the `prior_landing` callable handed to `read_save`, and pass `new_look=args.new_look` through.
- On `SourceUnchanged`, print a refusal naming the existing triple, the flag `--new-look`, and (folded in) the landed dates via `reports.resolve.landed_sim_dates` (resolve.py:78-94), in the shape `_nothing_landed_message` (`:168-187`) sets for the render path. Exit 1. Crucially the refusal must fire BEFORE `take_snapshot` is called, so no ~52 MB is copied and no filesystem sequence is consumed.
- Sequence policy: pass the snapshot directory's own `ingest_seq` EXPLICITLY to `land_snapshot` (load.py:203-217's first bullet), reconciled per Phase 0's recorded rule. Add a comment stating the cost the scope carries into the plan: the deadlock retry at load.py:232-250 re-allocates per attempt, which only helps on the `None` branch, so an explicit sequence means a lost race surfaces as `ConcurrentLandingError` rather than a recovery. Unlikely in a single-operator setup; stated so it is a trade rather than an inheritance.
- `--from-snapshot <dir>`: `parse_snapshot(read_manifest(dir))` — the composition `dump_parse` already uses at ingest/__init__.py:300 — then `land_snapshot`, touching no game file at all. The output must state EXPLICITLY, every time, whether the landed `ingest_seq` still matches the snapshot directory's number.
- Add the gamedata half of `tests/test_ingest_command.py`, targeting `settings.probe_save` only (SD-20). Never the managed league in an automated test.
- For AC13, simulate changed bytes by mutating a byte in a COPIED fixture save, or by monkeypatching the pre-flight's digest source. Never by editing a real save (ADR 0001).

**Acceptance:**

- AC10: with `load_settings` monkeypatched IN THE COMMAND MODULE to return `replace(settings, snapshot_root=tmp_path)` — the idiom at `tests/test_read_only.py:182-193` — `main(["land", "--save-id", <probe>])` returns 0 and the triple parses out of `capsys` stdout.
- AC11: `read_ingest_run(...)` returns a row at exactly the triple the function RETURNED; its `table_row_counts` equal the returned `run.row_counts`; `bronze_player` holds exactly that many rows for the triple. `purge_snapshot` runs in `finally`.
- AC12: a second invocation against a save whose bytes are unchanged since the last landing at that sim date returns non-zero, names the existing triple, the landed dates and `--new-look`, and creates NO new `ingest_run` row and NO new snapshot directory — asserted by listing `tmp_path` before and after, which proves the refusal fired before the copy.
- AC13: changed bytes at an unchanged sim date land automatically, with no flag. `read_ingest_run` finds BOTH sequences.
- AC14: `--new-look` lands identical bytes deliberately at `previous + 1`, and `warehouse.load.table_digest` (load.py:540-572) over every declared table for the FIRST triple is identical before and after — the same assertion shape as `tests/test_snapshot_semantics.py:537`'s `test_two_sequences_of_one_sim_date_both_persist`.
- AC15: `--from-snapshot <dir>` re-lands an existing snapshot without re-reading the game — the game directory's manifest (via `tests/test_read_only.py::manifest`) is unchanged across the invocation, a new `ingest_run` row appears, and the output states explicitly whether the landed `ingest_seq` still matches the directory's number.
- AC16 regression: `uv run pytest -m gamedata tests/test_read_only.py::test_a_full_run_touches_nothing_under_the_game_directories` is green, still performing four manifest passes when `OOTP_TRUTH_LEAGUE` is configured and three otherwise, and adding no MySQL dependency.
- AC17 regression: `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py` is green.
- `uv run pytest -m "not gamedata"`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` are green.

**Commit note:** The digest pre-flight (unchanged bytes refuse and name --new-look; changed bytes at an unchanged sim date land the next sequence automatically), the explicit-sequence policy with its weakened-retry cost stated, and --from-snapshot for the correction workflow ADR 0021 names. Six gamedata criteria proved against the probe.

#### Phase 7 — Phase 6 — The four cheap folds, each carrying its measurement or its refusal-to-refuse

**Goal:** Add the folded-in wins as one separately revertible phase, so that a cheap win that turns out not to be cheap can be dropped without touching the core.

**Steps:**

- `snapshot.verify_snapshot(snapshot.path)` after the copy, inside `read_save`. Its own docstring (snapshot.py:257-258) says it is 'Called after landing a snapshot' and that sentence is currently false — it has zero callers in `src/`. Record the added seconds against Phase 0's M4 baseline in the phase handoff.
- Print the save's mode from `saves.is_challenge_mode` (saves.py:81-84), whose module docstring at `:10-15` says the check is 'cheap enough to run on every ingest'. It REPORTS, never refuses: `tests/test_cross_mode_format.py:119` pins the retained truth save as standard-mode by design and it is parsed on every gamedata run, so `assert_challenge_mode` must NOT be called.
- Print both sequence allocators when they disagree, using `latest_ingest_seq` from Phase 3 for the display value.
- `--json`: the triple, per-table row counts, per-file residual bytes and `parse_seconds` — all already on the returned `IngestRun` (ingest/__init__.py:108-120), zero extra queries. Per-table `table_digest` values are explicitly NOT included: `table_digest` (load.py:540-572) fetches every column of every row for the triple, ~301,000 rows of which 264,095 are `bronze_name`, which is a second full read of everything the landing just wrote.
- The no-absolute-path rule applies to the `--json` block exactly as it does to the human block.

**Acceptance:**

- Offline: a test builds a tmp directory with and without a 241-byte `challenge.dat` and asserts the mode line reads correctly in both, and that NEITHER causes a non-zero exit — the report-only rule.
- Offline: `json.loads` of the `--json` block yields exactly the five documented keys, the `sim_date` is `YYYY-MM-DD`, and the serialised text matches none of `tests/test_no_leaks.py`'s `PATTERNS`.
- Offline: the dual-allocator line is emitted only when the two numbers differ, asserted in both directions against a fake cursor.
- Gamedata: `uv run pytest -m gamedata tests/test_ingest_command.py` is green and the phase handoff records `verify_snapshot`'s measured added seconds against Phase 0's M4 figure.
- Gamedata: `uv run pytest -m gamedata tests/test_cross_mode_format.py tests/test_parser_vs_export.py` is green — proving the mode line did not become a refusal that would break ingestion of the retained standard-mode truth save.
- `uv run pytest -m "not gamedata"`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` are green.

**Commit note:** Four folded-in wins: verify_snapshot after the copy with its cost measured, a report-only Challenge-mode line, landed dates and the dual-allocator line on the refusal path, and a --json block built from the returned IngestRun with zero extra queries. Per-table digests deliberately left out.

#### Phase 8 — Phase 7 — Retire the documented gap and true the docs up

**Goal:** Make every sentence in the repo that describes this gap false, and make `reports/resolve.py`'s existing advice true. Done last among the code phases because the invocation string, flag names, exit codes and output format are only stable once Phases 4-6 have shipped — and `incremental-loading` will write its procedure against all four.

**Steps:**

- Delete `README.md:128-134`'s 'There is no ingest command' blockquote in full.
- Extend the setup fence at `README.md:109-119` with `uv run python -m ootp_ai.ingest land` placed BEFORE the `reports render` line, plus a sentence noting that the first run creates the eight declared tables — which is what makes the fresh-clone path hold in one command rather than two.
- Correct `src/ootp_ai/reports/resolve.py:179-182`: `_nothing_landed_message` currently ends 'run the ingest before rendering'. Replace with the literal invocation string the command ships with, so the message names a command that exists.
- Add the boundary sentence to `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md` as a DATED amendment: this request owns the disk-and-refusal half (what save, what sim date, is it already landed), `incremental-loading` owns the warehouse-inventory half (its `:61`, 'what does this universe hold, and at which dates'). Neither builds a `status` verb now.
- Pass CLAUDE.md's Status paragraph and its `src/ootp_ai/` project-map entry through `/update-docs`, and set the `ingest-command` Index row in `requests/feature-requests/README.md:126` to `implemented`.
- Do NOT regenerate `docs/warehouse-catalog.md`. No contract changed; it must be byte-identical.

**Acceptance:**

- AC8, asserted in `tests/test_ingest_command.py`: `README.md` contains the literal invocation string the command ships with, and does NOT contain the string `There is no ingest command`; `src/ootp_ai/reports/resolve.py` contains that same literal invocation string. Both assertions read the files fresh — no fixture copy.
- `uv run pytest tests/test_doc_links.py tests/test_doc_link_contract.py tests/test_catalog.py tests/test_skill_references.py tests/test_repo_structure.py tests/test_no_leaks.py` is green.
- `git diff --stat docs/warehouse-catalog.md docs/warehouse-catalog.json src/ootp_ai/contracts/tables.toml` is EMPTY — no ninth table, no new column, no contract edit.
- `git diff tests/test_read_only.py` shows no change inside `:303-317`, so `WRITERS` is byte-unchanged across the entire change, not merely at Phase 4.
- `uv run pytest -m "not gamedata"` is green; `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` are green.
- The Index row for `ingest-command` and the artifact's own Status blockquote agree, per requests/feature-requests/README.md:106-113.

**Commit note:** Retire the documented gap: README's 'there is no ingest command' blockquote deleted and the command added to the setup fence, reports/resolve.py's 'run the ingest before rendering' made true, the status-verb boundary written into incremental-loading as a dated amendment, and CLAUDE.md trued up. warehouse-catalog.md byte-identical.

#### Phase 9 — Phase 8 — USER-RUN acceptance (the acceptance panel may not claim these)

**Goal:** Prove the request's own observable signal on a real machine — the one thing no automated test in this repo can run, because `ops/mysql-bootstrap.sql` grants are database-scoped to three named databases with no rights to create a throwaway schema, so an empty-warehouse precondition is unrunnable in pytest.

**Steps:**

- Hand the operator AC18's exact sequence: `uv sync` -> `mysql -u root -p < ops/mysql-bootstrap.sql` -> `uv run python -m ootp_ai.ingest land --save-id <target>` -> `uv run python -m ootp_ai.reports render --save-id <target>`, with `pytest` never invoked. State the prerequisite: if run against the probe, `OOTP_PROBE_LEAGUE` must be configured; otherwise run it against `settings.managed`, which is safe because the command only reads the save.
- Hand the operator AC19: paste the printed ingest output into a scratch `.md` file inside the repo and run `uv run pytest tests/test_no_leaks.py`.
- Record both outcomes in the IMPLEMENTATION_REPORT's acceptance ledger, marked USER-RUN, so the acceptance panel does not claim them.

**Acceptance:**

- AC18: a `roster.md` exists under the output root at `<output_root>/<save_id>/<sim_date>/<ingest_seq>/` (the partitioning `reports/resolve.report_dir` at resolve.py:125-133 produces), with `pytest` never having been invoked in the sequence.
- AC19: `uv run pytest tests/test_no_leaks.py` is green with the pasted ingest output present in a scratch `.md` inside the worktree — proving the stdout contract's no-absolute-path rule survives contact with a tracked, public repo.
- Both are recorded in the acceptance ledger as USER-RUN with the operator's result, not asserted by an agent.

**Commit note:** Record the two USER-RUN acceptance results: the fresh-clone path from uv sync to a rendered roster with pytest never invoked, and the printed ingest output leaving the leak guard green when pasted into the repo.

### Testing

**One new test module, split by what it needs.** `tests/test_ingest_command.py` carries an offline half that runs in CI (no game, no save, no MySQL) and a `-m gamedata` half that targets the PROBE save only, per SD-20. Every test in it is authored on the main thread — `tests/` is in the write-capable builder's deny set (`.claude/agents/data-engineer.md:154-157`), exactly as `first-sight` handled it.

**Per-phase selectors, in order.** Phase 0: no pytest (measurement only), but the four existing gates must stay green. Phase 1: `uv run pytest -m "not gamedata"` plus `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py` to prove the promotion is import-transparent on both sides. Phase 2: `uv run pytest tests/test_read_only.py` offline, then `uv run pytest -m gamedata tests/test_read_only.py` (the 2m35s one) and the full `landed_probe` consumer set — `tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py`. Phase 3: `uv run pytest -m "not gamedata" tests/test_bronze_landing.py tests/test_ingest_command.py`. Phase 4: `uv run pytest -m "not gamedata"` whole. Phase 5: `uv run pytest -m gamedata tests/test_ingest_command.py` plus the AC16/AC17 regression set. Phase 6: adds `tests/test_cross_mode_format.py`. Phase 7: `tests/test_doc_links.py tests/test_doc_link_contract.py tests/test_catalog.py tests/test_skill_references.py tests/test_repo_structure.py tests/test_no_leaks.py`.

**How the criteria are actually verified rather than asserted.** Three of the scope's criteria were rewritten by its own adversaries away from string scans, and the plan honours that. AC6 (both callers route through the shared function) is a monkeypatched recording spy that WRAPS and delegates to the real function, driven once from `land()` and once from `landed_probe` — not a source-text grep, because `tree-seam-for-remaining-guards` exists precisely because that class of guard cannot fail. AC7 (`ensure_tables` called once and before the copy) is a call-order list, not an import check. AC4 and AC19 IMPORT `tests/test_no_leaks.py`'s `PATTERNS` (`:37-41`) rather than restating them, so a widening of the leak guard automatically widens this test. AC1 imports `WRITERS` from `tests/test_read_only.py` and pins the exact three-element set, with the import spelled `from test_read_only import WRITERS` — this repo has no conftest.py anywhere and `tests/` is on `sys.path` via pytest's prepend mode (`tests/fixtures/__init__.py:4`), so the `from tests....` form the scope's AC1 writes would not resolve; `tests/fixtures/README.md:47-49` records that exact hazard.

**Regression safety, and where it is concentrated.** The single most dangerous edit is the `landed_probe` re-point, because it couples roughly ten gamedata tests across four modules to one new function: a defect in `read_save` reds all of them at once. Two guards against that. First, the re-point happens in Phase 2 ALONE, with no command in existence yet, so a failure has exactly one candidate cause. Second, the fixture's three test-only powers are asserted explicitly rather than assumed to survive: the `TemporaryDirectory` snapshot root, `ingest_seq=None` at the LANDING call (never at `read_save`, which has no such parameter), and `purge_snapshot` in `finally`. AC17's sub-clause requires that `tests/test_parser_vs_export.py:130`'s `which="truth_save"` path still works — that path lands the STANDARD-mode save, which is why the Challenge-mode fold must report and never refuse.

**The second concentration is AC11 itself**, the most expensive test in the repo at 2m35s over 30,703 files with ~6.4 GB hashed three times (`tests/test_read_only.py:25-28`). The plan adds no fourth leg and no MySQL dependency to it — the re-pointed legs pass `prior_landing=None`, so the pre-flight's warehouse lookup never runs inside the bracket. Phase 2's acceptance requires the wall clock be recorded and not materially above baseline; the fixture's loud-skip discipline (`tests/fixtures/warehouse.py:82-96`, "Never a vacuous pass") must survive unchanged, and `test_the_manifest_is_not_vacuous` must stay green beside it.

**Three things that must be byte-identical at the end, checked with git rather than eyeballed:** `tests/test_read_only.py:303-317`'s `WRITERS`, `docs/warehouse-catalog.md` (+ `.json`), and `src/ootp_ai/contracts/tables.toml`. Each is a `git diff --stat` assertion in Phase 7's acceptance.

### Risks

- **The pre-flight's seam is where Goals 3 and Core disagree, and the plan must not paper over it.** Goal 3 requires every game-touching line inside one shared function; Core requires the warehouse lookup outside it. But the sim date must be read from the game BEFORE the warehouse can be asked for that date's prior landing. A plain `prior_source_files` argument forces the command to call `read_sim_date(save)` itself — a game read OUTSIDE the bracket, which breaks AC16 in letter. The plan's resolution is a callback (`prior_landing: Callable[[SaveDate], ...] | None`), which keeps every game read inside `read_save` while both test call sites pass `None` and touch no MySQL. If the implementer prefers the plain-value shape, AC16's docstring must be amended to say the bracket covers the copy and the parse but not the sim-date probe — and that amendment is a decision, not a detail.
- **The size fast path may be near-useless, and Phase 0's M2 exists to find out before it is trusted.** `docs/data-access.md:71-91` records `names.dat` at a byte-identical 8,642,110 B across all three saves on disk, and five more files at single fixed sizes. If a simmed save leaves `players.dat` and `teams.dat` at unchanged sizes too, every pre-flight digests ~52 MB and the mitigation the scope's Risks §2 leans on ("a changed save almost always changes file sizes") is `assumed` rather than measured. Build the fast path either way — it is free — but do not document a cost it does not deliver.
- **A prior landing from before the 2026-08-16 SNAPSHOT_FILES widening has fewer `source_files` entries than today's five.** A naive comparison that only checks the files present in `prior` would report UNCHANGED on a save whose `world.dat` or `human_managers.dat` had never been digested. `sources_match` must treat any file in today's `SNAPSHOT_FILES` that `prior` does not name as CHANGED. This is a real state on disk, not a hypothetical: the widening is dated in `snapshot.py:71-76`.
- **`take_snapshot` with `ingest_seq=None` auto-allocates and never raises** (snapshot.py:189-201). `SnapshotExists` fires only when a sequence is named explicitly. So `land = snapshot + parse + land`, composed the obvious way, does not surface ADR 0021's refusal at all — it lands a full duplicate, ~52 MB on disk and ~301,000 rows, with no retention policy to reclaim either. Shipping documentation that claims a protection the code does not provide is the specific failure this plan orders Phase 5 to avoid.
- **Two independent sequence allocators, with one live instance of drift.** `snapshot.next_ingest_seq` (snapshot.py:146-164) counts directories under the gitignored, disposable `var/snapshots`; `warehouse.ingest_run.next_ingest_seq` reads `MAX(ingest_seq)` from MySQL. The scope measured the truth save as drifted — a surviving snapshot directory whose warehouse rows were purged by `landed_probe`'s `finally`. Phase 0's M1 re-measures because the warehouse may have moved since. The opposite direction is equally possible and not currently instantiated: delete `var/` (documented as disposable) and the first run claims seq 1 and hits `IngestRunExists` on a landing the operator never made.
- **Passing an explicit `ingest_seq` weakens the deadlock retry, invisibly.** `land_snapshot` retries on 1213/1205 and re-allocates the sequence each time (load.py:232-250), which only works on the `ingest_seq=None` branch. The command therefore has weaker contention behaviour than the fixture it replaces: a lost race surfaces as `ConcurrentLandingError` rather than a recovery. Unlikely in a single-operator setup; it must be stated in the code as a trade rather than inherited silently.
- **Conflating contention with a refusal.** `warehouse/load.py:146-154` names this failure in terms: an operator told "already landed" for a `ConcurrentLandingError` goes looking for a landing that never happened. AC5 requires the two messages be provably distinct, and a shared `except (IngestRunExists, ConcurrentLandingError)` handler with one message would pass a naive test.
- **The nine refusal exceptions share no base class.** `SnapshotExists` and `SnapshotCorrupt` derive from `Exception` (snapshot.py:100, :113), `SnapshotDateMismatch` and `UndecodedRecords` from `Exception` (ingest.py:148, :220), `IngestRunExists` from `Exception` (ingest_run.py:91), `LoadError` and `ConcurrentLandingError` from `RuntimeError` (load.py:142, :146), and `SaveFormatError` from `Exception` (parser/errors.py:25). A tuple that misses one turns a refusal into a traceback for the operator. Parametrise the test over the tuple so adding a tenth exception without handling it fails.
- **Re-pointing the fixture can silently change its sequence policy, and the failure surfaces somewhere else.** `landed_probe` lands with `ingest_seq=None` because a temp directory always allocates 1 on the filesystem side (`tests/fixtures/warehouse.py:19-26`). If the CLI's explicit-sequence policy travels with the shared function, `landed_probe` starts colliding at seq 1 and the failure appears as `IngestRunExists` in unrelated grain tests. This is precisely why `read_save` has NO `ingest_seq` parameter — the sequence decision stays with whoever calls `land_snapshot`.
- **`ingest_save` would have added ~50 MB of reads to a timing harness.** `_describe(..., payload=None)` re-reads each file whole for 25 bytes of header, measured at ~48 MB of avoidable I/O per ingest (ingest.py:488-492). The shared function is `take_snapshot` + `parse_snapshot`, never `ingest_save`, and `tests/test_extraction_cost.py` (with `DRIFT_FACTOR = 10.0` at `:57`) is in the regression set specifically because it is the harness that would notice.
- **AC11 must not get more expensive.** 2m35s over 30,703 files and ~6.4 GB hashed three times, measured 2026-08-16 (`tests/test_read_only.py:25-28`). No fourth leg, no MySQL dependency, no change to the manifest-pass count. `tests/test_read_only.py:240-242` refuses a warehouse dependency in terms: pulling one into ADR 0001's guard would let an unrelated MySQL outage silence the one test the project cannot afford to lose.
- **Package promotion is a 502-line move git may record as delete+add.** All ten `from ootp_ai.ingest import ...` sites survive unchanged, but line-numbered prose does not. Find every reference BEFORE the move; the single live one is `.claude/agents/data-engineer-memory.md:202`. Historical `requests/**/reviews/` handoffs must NOT be rewritten — they are the record of what was believed when.
- **Running a plain module under `-m` is why promotion is the right answer, and it is `inferred` rather than reproduced.** `python -m ootp_ai.ingest` on a MODULE executes it as `__main__` while its package-qualified imports re-import it as `ootp_ai.ingest`, giving two `ParsedSnapshot` classes and a silent `isinstance` failure across the boundary with `warehouse/load.py:90`. Label it `inferred` in any docstring that mentions it.
- **Ingesting while OOTP is running is only partially guarded.** `_copy_one` digests each source before and after the copy (snapshot.py:308-313) and `check_sim_dates` refuses a mixed snapshot (ingest.py:235-258). Neither catches a mid-write change ACROSS files at an unchanged sim date. A CLI makes this reachable outside a deliberate `-m gamedata` run — exactly when the operator is least likely to have quit the game first. `docs/data-access.md:226-227` labels the write-lock question `unconfirmed`; do not build on it, and do not fold a running-game spike into a wiring change.
- **Making landing one keystroke accelerates a cost nobody has bounded.** `bronze_name` re-lands 264,095 rows per snapshot, no retention policy exists, and ADR 0018 leaves the per-date growth rate `unconfirmed`. Per-table row counts are the honest measurable this command can print; a disk-bytes figure needs its own `information_schema` query and belongs to the retention argument.
- **The downstream contract is being pinned by this diff.** `incremental-loading` will write its operator procedure against whatever invocation string, flag names, exit codes and output format ship. All four are cheap now and expensive after — which is why Phase 7 (docs) comes last and why `--json` exists at all, giving that request a stable contract instead of a print format to grep.
- **Roughly half of Core lands in `tests/`, which is in the write-capable builder's deny set** (`.claude/agents/data-engineer.md:154-157`). Every test must be authored on the main thread. If a spawned builder is handed a spec whose target paths fall inside its deny set, its own contract requires it to stop and report rather than build.
- **`ensure_tables` does not repair a drifted table** (load.py:176-178) and nothing tells the operator when that bites. Accepted as a known limitation, stated in the command's docstring and in README's setup line, not fixed here. When `open-front-office` Phase B lands an `ensure_views()` beside it, whether the implicit rule extends is THAT request's decision.
- **The `WRITERS` import spelling in the scope's AC1 does not resolve in this repo.** The scope writes `from tests.test_read_only import WRITERS`; there is no conftest.py anywhere and no `tests/__init__.py`, so the working form is `from test_read_only import WRITERS` under pytest's prepend import mode. `tests/fixtures/README.md:47-49` records that the `from tests....` shape 'passes locally and fails elsewhere'. Ruff's isort may classify the bare module as third-party (`pyproject.toml:88` declares only `ootp_ai` and `fixtures` first-party); if `uv run ruff check .` reorders it, add `test_read_only` to `known-first-party` rather than adding a noqa.

### Files to touch

- `src/ootp_ai/ingest.py -> src/ootp_ai/ingest/__init__.py` — Phase 1. Move, content byte-identical. No edit to `__all__` (`:50-62`), no reflow, no import reorder. Prefer `git mv` so history records a rename.
- `src/ootp_ai/ingest/read.py` — Phase 2, NEW. `read_save(save, *, snapshot_root, prior_landing=None, new_look=False) -> ParsedSnapshot` — the one shared game-touching function, composing `read_sim_date` -> optional pre-flight -> `take_snapshot` -> `parse_snapshot`. No `ingest_seq` parameter, ever. Plus `SourceUnchanged` and the pure `sources_match(prior, current) -> bool`. Its own `__all__`; deliberately NOT added to `ingest.__all__` (AC9). Phase 3 adds `prior_landing_sources(connection, *, save_id, sim_date)` here or in a sibling under `ingest/`.
- `src/ootp_ai/ingest/__main__.py` — Phase 4, NEW. `main(argv) -> int` over `land(settings, *, save_id=None, snapshot_root=None, new_look=False, from_snapshot=None) -> IngestRun`, plus `_parser()`. Opens no file for writing and creates no directory — that is what keeps `WRITERS` byte-unchanged, and it is a requirement rather than an accident. Phase 5 adds the pre-flight wiring, the explicit-sequence policy and `--from-snapshot`; Phase 6 adds the mode line, the landed-dates refusal, the dual-allocator line and `--json`.
- `src/ootp_ai/snapshot.py` — Phase 2. Promote `_read_sim_date` (`:285-293`) to public `read_sim_date` and add it to `__all__` (`:50-63`), updating the caller at `:185`. Add public `source_facts(save) -> tuple[SnapshotFile, ...]` reusing the private `_digest` (`:322-328`). No change to `take_snapshot`, `read_manifest`, `verify_snapshot` or `_copy_one`.
- `src/ootp_ai/warehouse/ingest_run.py` — Phase 3. Add `latest_ingest_seq(connection, *, save_id, sim_date) -> int` — a plain `SELECT COALESCE(MAX(ingest_seq), 0)` with NO `FOR UPDATE` — and its `__all__` entry (`:61-71`). Docstring states why it is not `next_ingest_seq` (`:140-143`). Nothing else in the module changes; `tests/test_bronze_landing.py:818` scans this package for mutating SQL.
- `src/ootp_ai/reports/resolve.py` — Phase 7. `_nothing_landed_message` (`:179-182`) currently says 'run the ingest before rendering'. Replace with the literal invocation string the command ships with, so the message names a command that exists. No other change; `landed_sim_dates` (`:78-94`) is reused as-is by the refusal path.
- `tests/test_read_only.py` — Phase 2. Re-point the three AC11 legs (`:254`, `:263`, `:268`) onto `read_save`; update the test docstring at `:233-243`. `WRITERS` (`:303-317`) must end byte-unchanged, and Phase 7's acceptance checks that with git.
- `tests/fixtures/warehouse.py` — Phase 2. Re-point `landed_probe:151` onto `read_save(save, snapshot_root=Path(tmp))`, leaving `_land(connection, parsed)` at `:152` with `ingest_seq` still `None`, the `TemporaryDirectory` at `:149` and `purge_snapshot` in `finally` at `:154-156`. One sentence added to the docstring saying the landing path is now shared with the operator's command. `purge_snapshot` never moves into `src/`.
- `tests/test_ingest_command.py` — NEW, grown across Phases 2-7 and authored on the main thread. Offline half: `sources_match` rules (Phase 2), `latest_ingest_seq` and `prior_landing_sources` against a fake cursor (Phase 3), AC1-AC7 (Phase 4), the mode/JSON/dual-allocator folds (Phase 6), AC8's README and resolve.py literals (Phase 7). Gamedata half: AC10-AC15 against the probe only (Phase 5), verify_snapshot's measured cost (Phase 6).
- `README.md` — Phase 7. Delete the `:128-134` blockquote in full; add `uv run python -m ootp_ai.ingest land` to the setup fence at `:109-119`, before the `reports render` line, plus a sentence that the first run creates the eight declared tables.
- `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md` — Phase 7. A dated amendment carrying the status-verb boundary: this request owns the disk-and-refusal half, `incremental-loading` owns the warehouse-inventory half (its `:61`). The mechanism the scope's Decision §5 names, so the capability is not lost to mutual assumption.
```text
- `requests/feature-requests/ingest-command/reviews/measurements.md` — Phase 0, NEW. The four measurements — allocator drift across all three saves, the size fast path's real hit rate, source-side digest cost against the ~52 MB copy, and `verify_snapshot`'s added seconds — each labelled `measured <YYYY-MM-DD>`, plus the chosen sequence-reconciliation rule as one codeable sentence.
```
- `.claude/agents/data-engineer-memory.md` — Phase 1. Correct the evidence path at `:202` from `src/ootp_ai/ingest.py` to `src/ootp_ai/ingest/__init__.py`. The only live line-numbered reference to the moved file; historical `requests/**/reviews/` handoffs are deliberately left alone.
- `CLAUDE.md` — Phase 7, via `/update-docs`. The Status paragraph (which currently says only Phase 13 of first-sight remains) and the `src/ootp_ai/` project-map entry, which should now name the ingest package's entry point alongside `reports/` and `catalog/`.
- `requests/feature-requests/README.md` — Phase 7. Set the `ingest-command` Index row (`:126`) Stage cell to `implemented`, matching the artifact's own Status blockquote.
- `pyproject.toml` — Phase 4, ONLY IF ruff's isort reorders the `from test_read_only import WRITERS` line: add `test_read_only` to `known-first-party` (`:88`). Do not change `files`, `markers` or `strict` — inventing a second pytest marker is a hard collection error under `--strict-markers` (`:100-107`).

### Code references cited

- `src/ootp_ai/reports/__main__.py:36-59` — The `main(argv) -> int` shape and the 0/1/2 exit convention the new command copies: `ConfigError` printed to stderr and returning 2, the domain refusals printed as `f"{type(error).__name__}: {error}"` and returning 1, success printing and returning 0.
- `src/ootp_ai/reports/__main__.py:130` — `sub = parser.add_subparsers(dest="command", required=True)` — required, which is why AC2 must use `pytest.raises(SystemExit)` with `.code == 2` for `main([])` rather than expecting a return value.
- `src/ootp_ai/catalog/__main__.py:118-134` — `_fence_docs_root` — the record of what happened to the project's only operator-typed write root, and the reason `--snapshot-root` is dropped from the CLI and served by a library keyword argument instead.
- `src/ootp_ai/ingest.py:50-62` — `__all__` holds exactly eleven names. AC9 requires it unchanged, which is why `read_save` goes into a new `ingest/read.py` rather than into the promoted `__init__.py`.
- `src/ootp_ai/ingest.py:281-300` — `dump_parse` composes `parse_snapshot(read_manifest(path))` at `:300` — the exact composition `--from-snapshot` reuses to re-land without touching the game.
- `src/ootp_ai/ingest.py:488-492` — `_describe`'s docstring measures ~48 MB of avoidable I/O per ingest when `payload is None`. This is why the shared function is `take_snapshot` + `parse_snapshot` and never `ingest_save`.
- `src/ootp_ai/ingest.py:436-460` — `ingest_save` stops at the copy and is not orphaned by this change — `tests/test_provenance.py:30` still imports and calls it.
- `src/ootp_ai/snapshot.py:189-201` — `take_snapshot` allocates the next free filesystem sequence when `ingest_seq is None` and never raises; `SnapshotExists` fires only on an explicitly named sequence. This is the auto-allocation that makes naive composition silently land a duplicate.
- `src/ootp_ai/snapshot.py:205` — `snapshot_dir.mkdir(parents=True)` — the only directory creation in the pipeline's path. A command that delegates every file creation here trips none of `_writes_in`'s verbs, so `WRITERS` needs no new entry.
- `src/ootp_ai/snapshot.py:285-293` — `_read_sim_date` reads `teams.dat` whole (~5 MB) and returns the header's sim date. Promoted to public `read_sim_date` in Phase 2 and added to `__all__` at `:50-63`.
- `src/ootp_ai/snapshot.py:296-319` — `_copy_one` digests the SOURCE at `:308` and refuses at `:313` unless the destination matches — which is what makes a prior landing's `source_files` digests provably the save's own bytes, and the pre-flight comparison sound.
- `src/ootp_ai/snapshot.py:254-279` — `verify_snapshot`'s docstring says 'Called after landing a snapshot' — a sentence that is currently false, since it has zero callers in `src/`. Phase 6 makes it true and measures the added seconds.
- `src/ootp_ai/warehouse/load.py:169-189` — `ensure_tables` creates any missing declared table and returns the ones created; `:176-178` states it deliberately does not repair a drifted table. Its only caller in the repo is `tests/fixtures/warehouse.py:93`.
- `src/ootp_ai/warehouse/load.py:203-217` — `land_snapshot`'s docstring: an integer `ingest_seq` claims exactly that sequence and refuses with `IngestRunExists`; `None` allocates from the warehouse inside the transaction. The command passes an integer; `landed_probe` keeps `None`.
- `src/ootp_ai/warehouse/load.py:232-250` — The bounded deadlock retry re-allocates the sequence each attempt, which only helps on the `None` branch — so an explicit sequence means a lost race surfaces as `ConcurrentLandingError` rather than a recovery.
- `src/ootp_ai/warehouse/load.py:146-154` — `ConcurrentLandingError`'s docstring: telling an operator 'already landed' when this fired sends them looking for a landing that never happened. AC5 requires the two messages be provably distinct.
- `src/ootp_ai/warehouse/load.py:540-572` — `table_digest` fetches every column of every row for the triple, ordered by the declared key, and JSON-serialises each — which is why per-table digests are excluded from `--json` and used only in AC14's before/after assertion.
- `src/ootp_ai/warehouse/ingest_run.py:180-191` — `ingest_run_values` writes `source_files` as JSON carrying per-file `name`, `size`, `sha256` and `version` — the entire material the digest pre-flight compares against.
- `src/ootp_ai/warehouse/ingest_run.py:137-153` — `next_ingest_seq` runs `FOR UPDATE` and its docstring at `:140-143` requires it be called inside the transaction that inserts the row. This is why Phase 3 adds a separate `latest_ingest_seq` instead of reusing it.
- `src/ootp_ai/warehouse/ingest_run.py:88` — `_JSON_COLUMNS` includes `source_files`, so `read_ingest_run` (`:238-268`) hands the pre-flight a decoded list of dicts rather than a JSON string.
- `src/ootp_ai/config.py:99-108` — `Settings` carries `managed: SaveRef` and `truth_save` / `probe_save` as `SaveRef | None` — so target resolution must skip the `None`s a fresh clone and CI will have.
- `src/ootp_ai/config.py:111` — `load_settings(env: Mapping[str, str] | None = None)` is the mapping injection point offline tests need to build a `Settings` with no `.env`, no game and no MySQL.
- `src/ootp_ai/reports/resolve.py:179-182` — `_nothing_landed_message` already tells the operator to 'run the ingest before rendering' — the sentence this change must make true by naming a command that exists.
- `src/ootp_ai/saves.py:81-84` — `is_challenge_mode` is a `stat()` on a 241-byte marker; the module docstring at `:10-15` says the check is 'cheap enough to run on every ingest'. Phase 6 reports it and never calls `assert_challenge_mode`, which would break the retained standard-mode truth save.
- `tests/test_read_only.py:303-317` — `WRITERS` holds exactly `snapshot.py`, `reports/__main__.py`, `catalog/__main__.py`. AC1 pins this set and Phase 7 checks with git that no line inside the range changed.
- `tests/test_read_only.py:344-358` — `_source_files` walks `SRC.rglob("*.py")` and `_writes_in` scans a module's own source TEXT for `.write_text(`, `.write_bytes(`, `.touch(`, `.mkdir(`, `os.makedirs` and write-mode `open(`. It is not a capability model, which is why a module delegating to `snapshot.py:205` needs no allowlist entry.
- `tests/test_read_only.py:240-242` — AC11's docstring refuses to include landing in terms: pulling a warehouse dependency into ADR 0001's guard would let an unrelated MySQL outage silence the one test the project cannot afford to lose.
- `tests/test_read_only.py:254` — The probe leg — `parse_snapshot(ingest_save(settings.probe_save, settings=settings).snapshot)` — the first of three call sites Phase 2 re-points onto `read_save`. The others are `:263` (truth) and `:268` (managed).
- `tests/test_read_only.py:182-193` — `_settings` builds real settings then `replace(settings, snapshot_root=tmp_path / "snapshots")`. AC10 names this exact idiom for keeping `--snapshot-root` off the CLI while making the exit-0 path a pytest assertion.
- `tests/fixtures/warehouse.py:149-156` — `landed_probe` opens a `TemporaryDirectory`, composes `parse_snapshot(take_snapshot(save, snapshot_root=Path(tmp)))` at `:151`, lands with `_land(connection, parsed)` at `:152` (so `ingest_seq` defaults to `None`), and purges in `finally`. All three powers must survive the re-point unchanged.
- `tests/fixtures/warehouse.py:93` — `ensure_tables(connection)` inside `warehouse_or_skip` — the ONE caller of `ensure_tables` in the entire repo, which is what makes the test suite create the schema as well as fill it.
- `tests/fixtures/README.md:44-49` — This repo deliberately has no conftest.py anywhere; `fixtures` is declared first-party in pyproject.toml and the house import is `from fixtures.warehouse import ...`, while a `from tests.fixtures...` form 'passes locally and fails elsewhere'. This corrects the scope's AC1 import spelling.
- `tests/fixtures/__init__.py:4` — Records that pytest's `prepend` import mode puts `tests/` on `sys.path` — the mechanism that makes `from test_read_only import WRITERS` resolve and `from tests.test_read_only import ...` not.
- `tests/test_no_leaks.py:37-41` — `PATTERNS` — the three compiled regexes (windows drive path, unix home path, email address). AC4 imports this list rather than restating it, so a widening of the leak guard automatically widens the output test.
- `tests/test_bronze_landing.py:761-772` — `_MUTATING_SQL` matches DELETE FROM / DROP TABLE|SCHEMA|... / TRUNCATE TABLE / REPLACE INTO / ON DUPLICATE KEY / UPDATE ... SET. Phase 3's plain SELECT passes; `:847` explicitly pins the locking read as innocent.
- `tests/test_bronze_landing.py:812-815` — `_warehouse_sources` globs `src/ootp_ai/warehouse/*.py` — the scan root is the warehouse package only, so a new pre-flight module placed under `ingest/` is outside it while `latest_ingest_seq` in `ingest_run.py` is inside it and must pass.
- `tests/test_snapshot_semantics.py:537` — `test_two_sequences_of_one_sim_date_both_persist` — the assertion shape AC14 copies for proving `--new-look` leaves the first triple's per-table digests identical.
- `tests/test_extraction_cost.py:57` — `DRIFT_FACTOR = 10.0` — the timing harness that would notice if the shared function added avoidable I/O to the parse path. In Phase 2's and Phase 5's regression set for exactly that reason.
- `tests/test_parser_vs_export.py:130` — `landed_probe(settings, connection, which="truth_save")` — the Tier-B export diff lands the STANDARD-mode save through the fixture, which is why the Challenge-mode fold must report and never refuse.
- `ops/mysql-bootstrap.sql:23-63` — Three `CREATE DATABASE` (`:23`, `:30`, `:42`), one `CREATE USER` (`:54`), database-scoped grants only (`:57-63`). No tables and no rights to create a throwaway schema — which is what makes implicit `ensure_tables` load-bearing and AC18 USER-RUN rather than automated.
- `README.md:128-134` — The 'There is no ingest command' blockquote Phase 7 deletes; `:109-119` is the setup fence the command is added to, before the `reports render` line at `:117`.
- `docs/decisions/0021-bronze-landing-is-append-only.md:21-27` — Rejects the date-keyed refusal BY NAME — 'The obvious fix — key on (save_id, sim_date) and refuse a re-land — is worse' — which is why the shipped default is the digest pre-flight and needs no ADR amendment.
- `docs/data-access.md:71-91` — The .dat inventory with per-file sizes: `names.dat` at a byte-identical 8,642,110 B across all three saves, and `storylines.dat`, `weather.dat`, `games_in_progress.dat`, `trades.dat`, `offers.dat` likewise fixed — the measurement Phase 0's M2 uses to price the size fast path honestly.
- `docs/data-access.md:226-227` — 'Whether OOTP holds a write lock on this file while the game is running' is labelled `unconfirmed`. Nothing in this plan may build on it, and the running-game spike stays a separate request.
- `.claude/agents/data-engineer-memory.md:199-202` — The single live line-numbered reference to `src/ootp_ai/ingest.py`, which Phase 1's move must correct. No markdown link targets the file, so `tests/test_doc_links.py` is unaffected.
- `requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:144-146` — Prior art: 'No tracked entry point performs an ingest ... on a fresh machine the eight tables come into existence as a side effect of running the suite.' `:160-161` records `verify_snapshot` having no production caller. Both gaps were named here first.
- `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md:61` — 'Anyone reading the warehouse can answer what does this universe hold, and at which dates' — the warehouse-inventory half that request owns, and the boundary Phase 7's dated amendment writes down.
- `pyproject.toml:88` — `known-first-party = ["ootp_ai", "fixtures"]` — the isort declaration that may need `test_read_only` added when AC1's import lands, and `:100-107` records that inventing a second pytest marker is a hard collection error under `--strict-markers`.

### Open questions

- **The pre-flight seam: callback or plain argument?** The plan recommends `prior_landing: Callable[[SaveDate], Sequence[Mapping] | None] | None` so that Goal 3 ('every game-touching line inside one shared function') and Core ('the warehouse lookup stays outside it') are both literally true, with both test call sites passing `None`. The scope's Core text says 'a plain argument', which forces the command to call `read_sim_date(save)` itself — a game read outside AC11's bracket. If the implementer takes the plain-argument shape, AC16's docstring must be amended to say the bracket covers the copy and the parse but not the sim-date probe. Decide before Phase 2 is written; it is the only structural choice in the change.
- **The sequence-reconciliation rule.** Phase 0's M1 measures the drift; the scope leaves the rule to the plan. `max(filesystem_seq, warehouse_max + 1)` with a printed reasoning line never produces a gap but can skip a number; the filesystem sequence with a printed 'filesystem allocated N, warehouse holds M' line is honest but can hand the operator an `IngestRunExists` on a landing they never made. Recommend deciding from M1's actual table rather than in advance.
- **Does `sources_match` compare `version` as well as `size` and `sha256`?** `source_files` carries a header version per file (ingest_run.py:180-191). A patched game that moved a file's layout without changing its size or digest is not a real shape, so the plan compares size then sha256 only — but say so explicitly in the docstring so a later reader does not read the omission as an oversight.
- **Where the source-side digest helper lives.** The plan puts `source_facts(save)` in `snapshot.py` because that module already owns `_digest` and `SnapshotFile`. The alternative — promoting `_digest` to a public `file_digest` and building the tuple in `ingest/read.py` — widens `snapshot.__all__` less but scatters the digest logic. Confirm the choice before Phase 2 so the `__all__` edit is made once.
- **Whether `read_sim_date` still needs to be public under the callback shape.** With the callback, `read_save` calls it internally and no external caller strictly needs it. The scope promotes it to public API regardless (Decisions §7), and the plan keeps that promotion — but if the implementer takes the plain-argument shape it becomes load-bearing rather than merely available, and the docstring should say which.

## Planner: `domain-convention`

### Architecture notes

## What exists, and where the new code hooks in

`src/ootp_ai/` ships exactly two entry points today, and both only READ a landing:
`reports/__main__.py` (roster) and `catalog/__main__.py` (catalog). The write half of the
pipeline — `snapshot.take_snapshot` -> `ingest.parse_snapshot` -> `warehouse.load.land_snapshot`
— has no `__main__` behind it, and its only caller in the repo is
`tests/fixtures/warehouse.py::landed_probe` (`:151`). `warehouse.load.ensure_tables`
(`load.py:169`) likewise has exactly one caller, `tests/fixtures/warehouse.py:93`, and
`ops/mysql-bootstrap.sql` creates three databases and a user but **no tables** — so the test
suite currently does two pieces of production work, not one.

This change adds a third entry point over that existing code. No parser change, no new field,
no edit to `src/ootp_ai/contracts/tables.toml`, and `docs/warehouse-catalog.md` must be
byte-identical afterwards.

## The shape

    src/ootp_ai/ingest/            (ingest.py, promoted to a package)
      __init__.py   today's ingest.py, moved VERBATIM. __all__ unchanged (ingest.py:50-62),
                    so all ten `from ootp_ai.ingest import ...` sites import without edit.
      read.py       NEW — the ONE shared game-touching function, plus the pure pre-flight
                    comparison and the refusal it raises. Imported by __main__.py,
                    tests/fixtures/warehouse.py and tests/test_read_only.py.
      __main__.py   NEW — argparse + `main(argv) -> int` + testable `land(settings, ...)`
                    + the two pure formatters. Opens no file, creates no directory.

**Why a package and not a module.** `python -m ootp_ai.ingest` on a *module* would execute it
as `__main__` while `warehouse/load.py:90`'s `from ootp_ai.ingest import ParsedSnapshot`
re-imports it as `ootp_ai.ingest` — two distinct `ParsedSnapshot` classes and a silent
`isinstance` failure across the boundary. Label: `inferred` from Python import semantics, not
reproduced here. Promotion removes the hazard structurally and is import-transparent.

## The seam, and why AC11 can bracket it

`ingest/read.py::read_save(save, *, snapshot_root, previous=None) -> SaveRead` performs
**every** game read the command makes, in this order:

1. `snapshot.read_sim_date(save)` — the promoted public helper; ~5 MB of `teams.dat` for a
   25-byte header, and the only cheap answer to *what date would this land at?*
2. `saves.is_challenge_mode(save.path)` — a `stat()` of `challenge.dat` (`saves.py:81-84`);
   reports, never refuses (`tests/test_cross_mode_format.py:119` pins that the retained truth
   save is standard-mode by design and it is parsed on every gamedata run).
3. The digest pre-flight, **only when `previous is not None`** — size fast path first, then
   SHA-256, then `SaveUnchanged` if nothing moved. When `previous is None` there is no digest
   work at all, which is what keeps `landed_probe` and AC11 exactly as expensive as they are
   today (Risks: AC11 is 2m35s over 30,703 files and must not grow).
4. `snapshot.take_snapshot(save, snapshot_root=...)` — the ~52 MB copy.
5. `ingest.parse_snapshot(snapshot)` — the walk.

It has **no `ingest_seq` parameter**. The sequence decision belongs to whoever calls
`land_snapshot`, and keeping it out is what stops the CLI's explicit-sequence policy from
travelling into `landed_probe` and colliding at seq 1 in unrelated grain tests.

Everything else — argparse, `load_settings`, `connect_warehouse`, `ensure_tables`, the two
warehouse read helpers, the sequence reconciliation, `land_snapshot`, `verify_snapshot`,
printing — sits OUTSIDE `read_save` and touches no game file. That is the accurate form of
Goal 3, and it is why AC11 stays MySQL-free.

## The circular dependency, and the query that dissolves it

The digest pre-flight needs the prior landing's `source_files`; the obvious lookup is keyed on
`(save_id, sim_date)`, but the sim date is itself a game read — so a plain-argument
`previous` would force that read outside `read_save` and falsify Goal 3.

**The lookup is therefore keyed on `save_id` alone** — the most recent landing for the
universe, `ORDER BY sim_date DESC, ingest_seq DESC LIMIT 1`. The equivalence argument, which
must be written into the docstring: the sim date is read out of `teams.dat`'s header, and
`teams.dat` is one of the five digested files, so **unchanged bytes imply an unchanged sim
date**. Whenever the refusal should fire, the latest landing for the save *is* the latest
landing at that date. When the two differ, `read_save` sees a sim-date mismatch and reports
"changed" without digesting — the correct answer and the cheap one.

## Sequence allocation — the drift is real, and re-measured

Two independent allocators exist: `snapshot.next_ingest_seq` counts directories under the
gitignored `var/snapshots`; `warehouse.ingest_run.next_ingest_seq` reads `MAX(ingest_seq)`
from MySQL. Re-measured 2026-08-30 against the dev schema and `var/snapshots/`, confirming
the scope's table exactly:

| pair | filesystem | warehouse | |
|---|---|---|---|
| `OOTP-AI` 2024-03-07 | seq 1 | MAX 1 | in step |
| `Test-Save-Challenge-Mode` 2024-03-18 | seq 1 | MAX 1 | in step |
| `Test-Save-Standard-Mode` 2024-03-18 | seq 1 | **no row** | **drift, live** |

The command reconciles: `seq = max(snapshot_dir_seq, warehouse_max + 1)`, passed EXPLICITLY
to `land_snapshot`. In every in-step case that equals the filesystem-allocated sequence, so
the scope's core sentence holds unchanged; in the drift case it never blocks a legitimate
landing and never hands the operator an `IngestRunExists` for a landing they never made. When
the two disagree the output says so, and when the landed sequence diverges from the snapshot
directory's number the output says that too — the same sentence `--from-snapshot` prints.

## Fail-fast ordering (stated because it is not the natural order)

settings -> target -> warehouse connection -> `ensure_tables` -> prior-landing lookup ->
`read_save` (sim date, mode, pre-flight, copy, parse) -> `verify_snapshot` -> sequence
reconciliation -> `land_snapshot` -> print.

MySQL down must fail before ~52 MB is copied. A snapshot with no landing behind it is an
orphan, and nothing in this project reclaims one.

### Files to read first

- `requests/feature-requests/ingest-command/PROJECT_SCOPE.md` — The decided upstream artifact. Consume it, do not re-open it: Goals 1-9, the 19 acceptance criteria (10-17 are gamedata/probe-only, 18-19 are USER-RUN and the acceptance panel may not claim them), the tiered scope, and Decisions §1-§7. Every plan phase below traces to a numbered criterion in it.
- `src/ootp_ai/reports/__main__.py` — READ FIRST. The entry-point pattern this is the third instance of. `:1-11` records that entry points are deliberate; `:36-59` is the thin `main(argv) -> int` with the 0/1/2 exit convention; `:62-73` the testable `render(settings, *, save_id=None, ...)`; `:125-151` argparse with `add_subparsers(dest="command", required=True)`. Copy this shape.
- `src/ootp_ai/catalog/__main__.py` — The second instance, and two lessons: `:1-11` argues why it took no subcommand and why it is allowlisted by package-relative path; `:118-134` `_fence_docs_root` is the record of the project's only operator-typed write root, and the reason this command grows no `--snapshot-root` flag.
- `src/ootp_ai/ingest.py` — Moves verbatim to `ingest/__init__.py` in Phase 1. `:50-62` `__all__` (must not change), `:66` `PARSED_FILES`, `:161-217` `parse_snapshot`, `:235-278` `check_sim_dates`/`check_decoded`, `:281-300` `dump_parse` (the `read_manifest` -> `parse_snapshot` composition `--from-snapshot` reuses), `:436-460` `ingest_save`, `:481-501` `_describe` and its measured ~48 MB warning.
- `src/ootp_ai/snapshot.py` — `:50-63` `__all__` (where `read_sim_date` is added), `:146-164` the FILESYSTEM `next_ingest_seq`, `:167-216` `take_snapshot` — its `ingest_seq=None` auto-allocation is what makes naive composition land a silent duplicate — `:205`'s `mkdir` (why no WRITERS entry is needed), `:219-251` `read_manifest`, `:254-279` `verify_snapshot` (zero `src/` callers today), `:285-293` `_read_sim_date` (one caller, at `:185`), `:296-319` `_copy_one`.
- `src/ootp_ai/warehouse/load.py` — `:159-166` `landed_tables`, `:169-189` `ensure_tables` (creates and never repairs; one caller in the repo), `:195-250` `land_snapshot` and `:203-217`'s explicit-vs-`None` sequence contract, `:232-250` the bounded deadlock retry that only helps on the `None` branch, `:287-317` the in-transaction count read-back, `:540-572` `table_digest` and its cost.
- `src/ootp_ai/warehouse/ingest_run.py` — `:91-100` `IngestRunExists`, `:137-153` the WAREHOUSE `next_ingest_seq` and its must-be-inside-the-transaction contract (do NOT reuse it), `:156-198` `ingest_run_values` — `source_files` carries per-file `name`/`size`/`sha256`/`version`, which is exactly the material the digest pre-flight compares against — `:201-235` `claim_ingest_run`, `:238-268` `read_ingest_run`. Phase 4 adds two read helpers here.
- `src/ootp_ai/config.py` — `:56-68` `to_save_id` normalises to `[A-Za-z0-9_-]`, which is why printing a `save_id` can never leak a path; `:71-84` `SaveRef.path`/`.save_id`; `:99-108` `Settings` and its three `SaveRef` slots (`managed`, `truth_save`, `probe_save`, the last two optional); `:111-148` `load_settings(env)` — the mapping injection point every offline test uses.
- `tests/test_read_only.py` — ADR 0001's proof. `:182-193` the `replace(settings, snapshot_root=tmp_path)` idiom, `:222-269` the three AC11 legs to re-point and `:240-242`'s explicit refusal to pull landing (and therefore MySQL) into the guard, `:303-317` `WRITERS` (three entries, to stay byte-identical), `:344-358` `_source_files`/`_writes_in` — the source-text scan that makes a new allowlist entry unnecessary.
- `tests/fixtures/warehouse.py` — The de facto ingestion path today. `:19-27` why landings allocate from the warehouse, `:81-96` the loud-skip discipline and the repo's ONLY `ensure_tables` call at `:93`, `:99-130` `purge_snapshot` (stays in tests forever), `:133-157` `landed_probe` — it composes `parse_snapshot(take_snapshot(...))` at `:151` and does not call `ingest_save`.
- `tests/fixtures/README.md` — `:44-49`: there is no `conftest.py` anywhere in this repo and the house import is `from fixtures.warehouse import ...` — a `from tests.fixtures...` form 'passes locally and fails elsewhere'. This is why AC1's literal `from tests.test_read_only import WRITERS` must be written `from test_read_only import WRITERS` (the form `tests/test_leak_guard_scope.py:34` and `tests/test_doc_link_contract.py:23` already use).
- `docs/decisions/0021-bronze-landing-is-append-only.md` — The semantics the command surfaces and must not renegotiate. `:21-27` rejects a `(save_id, sim_date)`-keyed refusal BY NAME as 'worse'; `:42-55` the three positive parts; `:70-78` the 264,095-rows-per-snapshot cost and 'no retention policy exists'.
- `ops/mysql-bootstrap.sql` — Verify for yourself: three `CREATE DATABASE` (`:23`, `:30`, `:42`), one `CREATE USER` (`:54`), database-scoped grants only. NO tables. This is what makes `ensure_tables` load-bearing for Goal 2's fresh-clone criterion, and what makes an automated empty-schema test unrunnable.
- `README.md` — `:109-119` the setup fence to extend (the two existing `uv run python -m ootp_ai.<pkg>` lines are `:117-118`); `:128-134` the 'There is no ingest command' blockquote this change deletes. AC8 pins both.
- `src/ootp_ai/reports/resolve.py` — `:78-94` `landed_sim_dates` (reused on the refusal path), `:168-187` `_nothing_landed_message` — the refusal-message pattern to copy, and `:181-182`'s 'run the ingest before rendering', the sentence this change makes true.

### Phases

#### Phase 1 — Phase 1 — Promote `ingest.py` to a package; make `read_sim_date` public

**Goal:** A pure structural move that changes no behaviour, landed on its own so that the diff a reviewer reads for the real work is not 502 lines of moved file. `python -m ootp_ai.ingest` becomes hostable without the double-import hazard, and the pre-flight gains its cheap sim-date read.

**Steps:**

- Create `src/ootp_ai/ingest/` and move `src/ootp_ai/ingest.py` to `src/ootp_ai/ingest/__init__.py` **verbatim** — not one character of content changed. Use a plain filesystem move (PowerShell `Move-Item`), not `git mv`: `/commit` stages the delete and the add, and git may record the move as delete+add regardless (this is expected, not a mistake).
- Do NOT add any import of the new sibling modules to `__init__.py`. It stays byte-identical to today's `ingest.py`, which is what keeps `ingest.__all__` (`ingest.py:50-62`) unchanged and every one of the ten `from ootp_ai.ingest import ...` sites importing without edit.
- In `src/ootp_ai/snapshot.py`, rename `_read_sim_date` (`:285-293`) to `read_sim_date`, update its single caller at `:185`, and add `"read_sim_date"` to `__all__` (`:50-63`, alphabetical: it sorts between `next_ingest_seq` and `read_manifest`). Extend its docstring with why it is public: it is the only cheap answer to *what date would this land at?* before ~52 MB is copied. Verified: no other module and no test references `_read_sim_date`.
- Correct the one live line-numbered prose reference to the moved file: `.claude/agents/data-engineer-memory.md:202`, which cites `src/ootp_ai/ingest.py` `human_team_id=None`. Change the path to `src/ootp_ai/ingest/__init__.py`. **Do NOT rewrite any `requests/**/reviews/` handoff** — those are the record of what was believed when.
- Run the full offline suite plus the two cheapest gamedata modules to prove the move is inert.

**Acceptance:**

- `uv run pytest -m "not gamedata"` green; `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` green.
- `uv run python -c "import ootp_ai.ingest as m; print(sorted(m.__all__))"` prints exactly the eleven names at `ingest.py:50-62` — `PARSED_FILES, IngestRun, ParsedSnapshot, SnapshotDateMismatch, SourceFile, UndecodedRecords, check_decoded, check_sim_dates, dump_parse, ingest_save, parse_snapshot`.
- `uv run python -c "from ootp_ai.snapshot import read_sim_date"` succeeds and `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_provenance.py` is green.
- `git status` shows `src/ootp_ai/ingest.py` deleted and `src/ootp_ai/ingest/__init__.py` added, and no other `src/` file changed except `snapshot.py`.
- `git diff` on the moved content is empty when compared body-to-body (e.g. `git show HEAD:src/ootp_ai/ingest.py` diffed against the new file yields nothing).

**Commit note:** Promote ingest.py to a package and make read_sim_date public — a structural move with no behaviour change, so the entry point can be hosted at `python -m ootp_ai.ingest` without the module/`__main__` double-import hazard.

#### Phase 2 — Phase 2 — The shared game-touching function, and the two re-points

**Goal:** One function performs every game read the command will make, and the two existing callers — `tests/fixtures/warehouse.py::landed_probe` and `tests/test_read_only.py`'s three AC11 legs — route through it. No CLI yet, so the seam is proved before anything depends on it.

**Steps:**

- Write `src/ootp_ai/ingest/read.py`. Public surface: `PriorLanding` (frozen dataclass: `save_id: str`, `sim_date: SaveDate`, `ingest_seq: int`, `files: tuple[SourceFile, ...]` — plain data, built by the caller, so no warehouse code enters this module), `SaveRead` (frozen dataclass: `parsed: ParsedSnapshot`, `challenge_mode: bool`, `preflight_seconds: float`), `SaveUnchanged` (Exception, `# noqa: N818` matching the house style of `SnapshotExists`/`IngestRunExists`, carrying the prior triple), `reason_to_land(previous, sim_date, current) -> str | None` (PURE — no I/O), and `read_save(save, *, snapshot_root, previous=None) -> SaveRead`.
- `read_save` body, in this exact order: (1) `sim_date = read_sim_date(save)`; (2) `challenge = is_challenge_mode(save.path)`; (3) **if `previous is not None`**, survey the five `SNAPSHOT_FILES` with `Path.stat()` for sizes only, and call `reason_to_land`; a `None` return raises `SaveUnchanged`; (4) `snapshot = take_snapshot(save, snapshot_root=snapshot_root)`; (5) `return SaveRead(parsed=parse_snapshot(snapshot), ...)`. **When `previous is None` no digest is computed at all** — that is what keeps AC11 and `landed_probe` exactly as expensive as they are today.
- `reason_to_land(previous, sim_date, current)` returns a human string naming WHY the save changed, or `None` meaning nothing moved and the landing should refuse. Order of checks: sim-date mismatch first (no digesting needed); then the file *set* (a name in one and not the other); then sizes; only if every size matches does the caller digest and re-call for the sha256 comparison. Structure it so the digest work is the caller's (`read_save`'s) and the comparison is pure — that is what makes AC13's logic CI-testable without a game.
- Digest with `hashlib.sha256` streamed in 1 MiB chunks, matching `snapshot._digest` (`snapshot.py:322-328`). Do NOT import the private helper; a four-line local copy with a comment naming the sibling is preferable to widening `snapshot`'s private surface, and `snapshot.py` is the only allowlisted writer — importing from it is fine, but keep this module's own text free of any write verb.
- The module docstring must name its three callers (`ingest/__main__.py`, `tests/fixtures/warehouse.py::landed_probe`, `tests/test_read_only.py`'s AC11 legs) and state outright that changing this function changes what the operator's command does.
- Re-point `tests/fixtures/warehouse.py::landed_probe` (`:133-157`): replace `parse_snapshot(take_snapshot(save, snapshot_root=Path(tmp)))` at `:151` with `read_save(save, snapshot_root=Path(tmp)).parsed`. Keep all three test-only powers exactly where they are — the `TemporaryDirectory` snapshot root, `ingest_seq=None` at the `_land(...)` call, and `purge_snapshot` in `finally`. Add one sentence to its docstring saying the landing path is now shared with the operator's command.
- Re-point `tests/test_read_only.py`'s three legs (`:254`, `:263`, `:268`): each becomes `read_save(<save>, snapshot_root=settings.snapshot_root)`. Drop the now-unused `ingest_save` import if nothing else in the module uses it (`parse_snapshot` becomes unused too — check both). Update the test docstring (`:230-243`): the guard now brackets every game read the operator's command makes, landing is still deliberately outside it, and the leg is now CHEAPER than before because `ingest_save`'s `_describe(..., payload=None)` re-read of ~48 MB per leg is gone (`ingest.py:481-501`) — and no game-read coverage is lost, because those re-reads were of the snapshot COPY, not the save.
- Add `tests/test_ingest_command.py` with its first two tests (offline): the WRITERS assertion and the sharing-identity assertion. **Author this on the main thread** — `tests/` is in the write-capable builder's deny set (`.claude/agents/data-engineer.md:157`).
- The WRITERS test: `from test_read_only import WRITERS` — the house form (`tests/test_leak_guard_scope.py:34`, `tests/test_doc_link_contract.py:23`), NOT `from tests.test_read_only import ...`, which `tests/fixtures/README.md:44-49` records as the form that 'passes locally and fails elsewhere' because this repo has no `conftest.py` anywhere. Assert `WRITERS == {"snapshot.py", "reports/__main__.py", "catalog/__main__.py"}` with a comment saying the new modules are deliberately absent because they create no file.
- The sharing test: `import test_read_only`, `import fixtures.warehouse`, `from ootp_ai.ingest import read`, then `assert test_read_only.read_save is fixtures.warehouse.read_save is read.read_save`. This is the identity half of AC6 and cannot pass vacuously; the recorded-call half arrives in Phase 4 once `land()` exists.

**Acceptance:**

- `uv run pytest -m "not gamedata"` green, including the two new tests; ruff and mypy green.
- `uv run pytest tests/test_read_only.py` green — specifically `test_only_allowlisted_modules_can_write_a_file` and `test_the_pipeline_contains_no_destructive_filesystem_call` pass with `ingest/read.py` present in `SRC.rglob("*.py")`, and `WRITERS` is byte-unchanged (AC1).
- `uv run pytest -m gamedata tests/test_read_only.py::test_a_full_run_touches_nothing_under_the_game_directories` green, and `test_the_manifest_is_not_vacuous` green alongside it. The test still performs four `_manifests` passes with `OOTP_TRUTH_LEAGUE` configured and three without (AC16).
- `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py` green — the real `landed_probe` consumer set, including `test_parser_vs_export.py:130`'s `which="truth_save"` path (AC17).
- Offline unit tests for `reason_to_land` cover: identical sources -> `None`; a sim-date mismatch -> a reason naming both dates, with no digest consulted; one size changed -> a reason naming the file; equal sizes with one sha256 changed -> a reason naming the file; a file present in one set and not the other -> a reason. All five run in CI with no game and no MySQL.

**Commit note:** One shared function performs every game read the ingest command will make; landed_probe and ADR 0001's three AC11 legs now route through it, so the guard brackets the operator's path rather than a sibling of it.

#### Phase 3 — Phase 3 — The CLI surface: argparse, target resolution, exit codes, formatters

**Goal:** Everything a test can prove without a game and without MySQL: the flag set, resolution by configured save name, the two output formats, and the eight-plus-one refusal surface mapped onto exit codes.

**Steps:**

- Write `src/ootp_ai/ingest/__main__.py` following `reports/__main__.py:36-59` exactly: a thin `main(argv: list[str] | None = None) -> int` over a testable `land(settings, *, save_id=None, snapshot_root=None, new_look=False, from_snapshot=None) -> LandingResult`, with `_parser()` at the bottom and `if __name__ == "__main__": raise SystemExit(main())`.
- `_parser()`: `prog="python -m ootp_ai.ingest"`, `sub = parser.add_subparsers(dest="command", required=True)`, one `land` subcommand. Options: `--save-id` (default None), `--new-look` (`store_true`), `--from-snapshot` (metavar `DIR`), `--json` (`store_true`). `--new-look` and `--from-snapshot` go in an `add_mutually_exclusive_group()` — a snapshot re-land has no digest pre-flight to override, so the combination is meaningless and argparse's own exit-2 message says so better than a runtime check would. **No `--sim-date`, no `--snapshot-root`, no `--ingest-seq`, no `--force`.** The `--new-look` help text must name the cost the scope accepts openly: a deliberate re-land of identical bytes (a parser fix) needs this flag.
- Target resolution, in `land()`: build `{ref.save_id: ref for ref in (settings.managed, settings.truth_save, settings.probe_save) if ref is not None}` — skipping the `None`s a fresh clone and CI will have (`config.py:99-108`). Absent `--save-id`, use `settings.managed`. An unknown id raises a `ValueError` naming every configured `save_id`, which `main` maps to exit **2**. A filesystem path passed as `--save-id` falls out of the same exact-match lookup with no special case — do not add one.
- `LandingResult`: a frozen dataclass carrying `run: IngestRun`, `created_tables: tuple[str, ...]`, `snapshot_ingest_seq: int`, `challenge_mode: bool`, `filesystem_seq: int`, `warehouse_max_seq: int`, `preflight_seconds: float`, `verify_seconds: float`. **No path field, deliberately** — the same defence `ingest.py:25-27` uses for `IngestRun`: the type has nowhere to put one.
- Two pure formatters, both taking only a `LandingResult`: `format_result(result) -> str` and `format_json(result) -> str`. Line one of the human form is pinned: `landed <save_id> <YYYY-MM-DD> ingest_seq <n>` — machine-parseable so AC10 can read the triple out of `capsys`. Then: the save mode line, any tables created, the snapshot-sequence match/divergence sentence (printed EVERY time, stating whether the landed `ingest_seq` still matches the snapshot directory's number), the dual-allocator line only when the two disagree, per-table row counts, and the timings. `format_json` emits the triple, `row_counts`, `residual_bytes`, `parse_seconds`, the mode, the created tables and both sequences — all already on the returned `IngestRun`, zero extra queries. **Per-table digests are NOT included**: `table_digest` (`load.py:540-572`) re-reads every column of every row, ~301,000 rows for one landing, on the operator's most frequent command.
- The output rule is **stdout-only**: no absolute path may reach stdout in either format. A `ConfigError` on stderr MAY name the offending path, because a misconfiguration message that does not is not actionable. Both halves in a comment so neither is later 'fixed' by mistake.
- Exception mapping in `main()`, caught **by name** because they share no base class: `ConfigError` -> 2; `ValueError` from target resolution -> 2; and `IngestRunExists`, `ConcurrentLandingError`, `SnapshotExists`, `SnapshotCorrupt`, `SnapshotDateMismatch`, `SaveFormatError`, `UndecodedRecords`, `LoadError`, `SaveUnchanged` -> 1, printed as `f"{type(error).__name__}: {error}"` on stderr. A tuple that misses one turns a refusal into a traceback.
- Extend `tests/test_ingest_command.py` with the offline half: the argparse pins, the resolution tests (via `load_settings(mapping)` — the injection point at `config.py:111` exists for exactly this), the formatter/leak test, and the refusal-surface tests with `land_snapshot` monkeypatched.

**Acceptance:**

- AC2: `_parser().parse_args(["land"]).command == "land"`; `--save-id`, `--new-look`, `--from-snapshot`, `--json` all parse; `parse_args(["land", "--sim-date", "x"])`, `--snapshot-root`, `--ingest-seq` and `--force` each raise `SystemExit`; `with pytest.raises(SystemExit) as exc: main([])` then `assert exc.value.code == 2` (argparse RAISES on a missing required subcommand, it does not return).
- AC3: with `Settings` built through `load_settings(mapping)`, an unmatched `--save-id` returns **2** and the stderr string names every configured `save_id`; absent `--save-id` resolves to `settings.managed`; a filesystem path passed as `--save-id` is rejected rather than resolved.
- AC4: given a synthetic `IngestRun` and a `LandingResult`, `format_result(...)` and `format_json(...)` match **none** of `test_no_leaks.PATTERNS` — imported (`from test_no_leaks import PATTERNS`), not restated — and both carry the `save_id`, the `sim_date` as `YYYY-MM-DD`, the `ingest_seq` and the per-table row counts. `uv run pytest tests/test_no_leaks.py` stays green.
- AC5: with `land_snapshot` monkeypatched to raise `IngestRunExists`, `main(["land"])` returns 1 and the message names the triple; with `ConcurrentLandingError`, the message is **distinct** from the `IngestRunExists` one (`load.py:146-154` warns that conflating them sends the operator looking for a landing that never happened); with `load_settings` raising `ConfigError`, `main(["land"])` returns 2.
- `uv run pytest -m "not gamedata"`, ruff, ruff format --check and mypy all green. No test in this phase opens a game file or a database.

**Commit note:** The ingest command's surface — one `land` verb, resolution by configured save name, the 0/1/2 exit convention, and two path-free output formats — all provable in CI without a game or a warehouse.

#### Phase 4 — Phase 4 — Wire the real path: ensure_tables, the digest pre-flight, sequence reconciliation, landing

**Goal:** `uv run python -m ootp_ai.ingest land` actually lands, refuses correctly on unchanged bytes, and lands automatically on changed bytes at an unchanged sim date — ADR 0021's motivating case, flowing without a flag.

**Steps:**

- Add two read helpers to `src/ootp_ai/warehouse/ingest_run.py`, both plain `SELECT`s, both added to `__all__`: `latest_landing(connection, *, save_id) -> dict[str, Any] | None` (`ORDER BY sim_date DESC, ingest_seq DESC LIMIT 1`, JSON columns decoded exactly as `read_ingest_run` does at `:262-268`) and `landed_max_seq(connection, *, save_id, sim_date) -> int` (`SELECT COALESCE(MAX(ingest_seq), 0) ... WHERE save_id=%s AND sim_date=%s`, **no `FOR UPDATE`**). `landed_max_seq`'s docstring must contrast it with `next_ingest_seq` (`:137-153`) and say why that one is deliberately not reused: it requires the transaction that inserts the row, and this repo has already got that function's locking semantics wrong once (see the module docstring at `:16-35`).
- Wire `land()` in the fail-fast order: `connect_warehouse(settings)` -> `ensure_tables(connection)` (capture the returned tuple of created tables) -> `latest_landing(connection, save_id=resolved)` -> build a `PriorLanding` from the row (`sim_date` arrives as a driver `datetime.date`; convert with a three-line local `SaveDate(day=..., month=..., year=...)`, the same shape as `reports/resolve._as_save_date`) -> `read_save(save, snapshot_root=..., previous=None if new_look else prior)` -> `verify_snapshot(parsed.run.snapshot.path)` -> reconcile the sequence -> `land_snapshot(connection, parsed, ingest_seq=seq)`. Close the connection in `finally`, matching `reports/__main__.py:98-99`.
- `--new-look` is implemented as `previous=None`: it does not disable a check, it declines to tell the reader what landed before. One line, and the flag's whole semantics.
- Sequence reconciliation: `seq = max(parsed.run.ingest_seq, landed_max_seq(...) + 1)`, passed explicitly to `land_snapshot`. `parsed.run.ingest_seq` is the filesystem-allocated number the snapshot directory carries. Record both numbers on the `LandingResult` so the formatter can print the divergence line, and comment the cost: an explicit sequence means the bounded deadlock retry (`load.py:232-250`) re-allocates a number this call ignores, so a lost race surfaces as a refusal rather than a recovery (Risks §5 of the scope, inherited knowingly).
- `SaveUnchanged`'s message is the actionable one: name the existing triple, the dates the warehouse holds for this save (`reports.resolve.landed_sim_dates(connection, save_id=...)`, the same fold `_nothing_landed_message` uses at `:177`), and `--new-look`. Build the message in `land()`, where the connection is, not inside `read_save` — `read_save` raises with the triple it was handed and `land()` re-raises or enriches. Keep the warehouse out of `ingest/read.py` entirely.
- **Measure and record, in the module docstring of `ingest/read.py` and in the phase handoff**: the wall-clock cost of the pre-flight digest over the ~52 MB of `SNAPSHOT_FILES`, the cost of `verify_snapshot` after the copy, and the size-fast-path cost when a size differs (which should be milliseconds). The scope carries a measurement obligation for both; a number nobody wrote down is the same as no measurement.
- Extend `tests/test_ingest_command.py`: the `ensure_tables` spy, the AC6 recorded-call half, and the gamedata half against the **probe only** (SD-20 — never the managed league in an automated test).
- AC6's recorded-call half, spelled out because `from X import y` binds a name and monkeypatching the source module does not rebind it: monkeypatch **both** `ootp_ai.ingest.__main__.read_save` and `fixtures.warehouse.read_save` with one recorder, drive `land(...)` and `landed_probe(...)`, and assert each produced a recorded call. Phase 2's `is`-identity assertion is what proves they are the same function; this proves both callers actually reach it.

**Acceptance:**

- AC7: with `read_save` and `land_snapshot` stubbed, a spy on `ensure_tables` records exactly one call, and it happens **before** the first `take_snapshot`/`read_save` call. Assert ordering with a shared call log, not with two separate counters.
- AC6: the recorded-call test passes for both callers, and Phase 2's identity assertion still holds.
- AC10 (gamedata, probe): monkeypatch `load_settings` **in the command module** to return `replace(settings, snapshot_root=tmp_path)` — the idiom at `tests/test_read_only.py:193` — then `main(["land", "--save-id", <probe save_id>])` returns **0** and the triple parses out of `capsys` stdout.
- AC11 (gamedata): `read_ingest_run(...)` returns a row at exactly the triple the function RETURNED; its `table_row_counts` equal `run.row_counts`; `bronze_player` holds exactly that many rows for the triple. `purge_snapshot` runs in `finally`.
- AC12 (gamedata): a second invocation against a save whose bytes are unchanged since the last landing at that sim date returns non-zero, names the existing triple and `--new-look`, and creates **no** new `ingest_run` row and **no** new snapshot directory — proving the refusal fires before ~52 MB is copied. Assert the snapshot root's directory count is identical before and after.
- AC13 (gamedata): with a synthetic `PriorLanding` whose one sha256 differs from the save's, `land` proceeds and `read_ingest_run` finds both sequences. Never by editing a real save.
- AC14 (gamedata): `--new-look` lands identical bytes at `previous + 1`, and `warehouse.load.table_digest` over every declared table for the **first** triple is identical before and after — the same assertion shape as `tests/test_snapshot_semantics.py:537`'s `test_two_sequences_of_one_sim_date_both_persist`.
- `uv run pytest -m "not gamedata"`, ruff, ruff format --check, mypy green; `uv run pytest -m gamedata tests/test_bronze_landing.py` green (`test_no_module_in_the_warehouse_can_mutate_a_landed_row` at `:818` still passes with the two new SELECT helpers present in `warehouse/`).
- The measured pre-flight and `verify_snapshot` seconds are written into `ingest/read.py`'s docstring and the phase handoff.

**Commit note:** The ingest command lands for real: ensure_tables on every run, a digest pre-flight that refuses only on unchanged bytes, and a sequence reconciled across the filesystem and warehouse allocators.

#### Phase 5 — Phase 5 — `--from-snapshot`: the correction workflow, without re-reading the game

**Goal:** Re-land an existing snapshot at the next free sequence without touching the one tree ADR 0001 protects — the correction ADR 0021 names by name (`a parser fix re-lands the same snapshot at the next sequence`), which no entry point can perform today.

**Steps:**

- In `land()`, when `from_snapshot` is set, take the `snapshot.read_manifest(dir)` -> `parse_snapshot(...)` route — the same composition `ingest.dump_parse` uses at `:300` — and skip `read_save` entirely. No game read of any kind occurs on this path, and there is no digest pre-flight (a snapshot IS a prior copy; there is nothing to compare it against).
- The save mode is unknown on this path: the snapshot does not carry `challenge.dat` (`SNAPSHOT_FILES`, `snapshot.py:77-83`). Make `LandingResult.challenge_mode` `bool | None` and have the formatter print `save mode: not recorded (re-landed from a snapshot)` rather than guessing. A `False` here would read as 'standard mode' and be wrong.
- Reconcile the sequence identically: `seq = max(snapshot.ingest_seq, landed_max_seq(...) + 1)`. The output states, **every time**, whether the landed `ingest_seq` still matches the snapshot directory's number — matching or diverging, the sentence is always printed, so its absence can never be read as agreement.
- `SnapshotCorrupt` from `read_manifest` (`snapshot.py:248-251`) and from a `verify_snapshot` call on the named directory reach the operator by name with exit 1; they are already in Phase 3's exception tuple.
- Do not fence `--from-snapshot` against the game roots: it is a READ root, not a write root, and `reject_inside_game_roots` (`config.py:215-238`) exists for write roots. Say so in a comment so the next reader does not add a check that would refuse a legitimate read.
- Add the AC15 gamedata test.

**Acceptance:**

- AC15 (gamedata, probe): land a probe snapshot into `tmp_path`, then `main(["land", "--from-snapshot", str(snapshot_dir)])` — the game directory's manifest (via `test_read_only.manifest`/`differences`) is unchanged across the invocation, a new `ingest_run` row appears, and stdout states explicitly whether the landed `ingest_seq` still matches the snapshot directory's number. `purge_snapshot` cleans up both landings in `finally`.
- `main(["land", "--from-snapshot", "x", "--new-look"])` exits 2 from argparse's mutually-exclusive group.
- A nonexistent or manifest-less directory produces `SnapshotCorrupt: ...` on stderr and exit 1, not a traceback.
- `uv run pytest -m "not gamedata"`, ruff, ruff format --check, mypy green.

**Commit note:** `--from-snapshot` re-lands an existing snapshot at the next free sequence without re-reading the game — ADR 0021's named correction workflow, with the sequence relationship stated every time.

#### Phase 6 — Phase 6 — Retire the documented gap and write the boundary down

**Goal:** Every document that describes this gap stops describing it, and the sentence in `reports/resolve.py` that already tells the operator to 'run the ingest before rendering' becomes true.

**Steps:**

- `README.md`: delete the `:128-134` blockquote outright — not soften it. Add the command to the setup fence at `:109-119`, above the two existing `uv run python -m ...` lines, plus one prose line noting that the first run creates the eight declared tables (`ops/mysql-bootstrap.sql` creates the databases and the user; it creates no tables). The literal invocation string in the README must be exactly the one the command ships with.
- `src/ootp_ai/reports/resolve.py:179-182`: extend `_nothing_landed_message`'s first branch to name the command — the same literal invocation string — so the instruction points at something that exists.
- `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md`: add the boundary sentence as a **dated amendment** (Decisions §5 makes writing it in both places the mechanism that stops the `status` capability being lost to mutual assumption). This request owns the disk-and-refusal half — what save, what sim date, is it already landed, delivered by the landed-dates fold on the refusal path; `incremental-loading` owns the warehouse-inventory half (its `:61`).
- `CLAUDE.md`: the Status paragraph currently says `src/ootp_ai/` 'serves two reports'; the project map's `src/ootp_ai/` entry has no ingest line. Both go through `/update-docs` rather than being hand-edited to taste — that skill is the judgment half of the commit gate and owns exactly this.
- Do NOT touch `src/ootp_ai/contracts/tables.toml`, `docs/warehouse-catalog.md`, `ops/mysql-bootstrap.sql`, `.env.example` or `pyproject.toml`. No new `.env` key, no `[project.scripts]`.
- Add the AC8 documentation test to `tests/test_ingest_command.py`, and re-run the four doc guards.

**Acceptance:**

- AC8: a test asserts `README.md` contains the literal invocation string the command ships with and does **not** contain `There is no ingest command`; and that `src/ootp_ai/reports/resolve.py` contains that same literal string. Define the string once as a module constant in the command module and import it in the test, so the three copies cannot drift.
- `uv run pytest tests/test_doc_links.py tests/test_doc_link_contract.py tests/test_catalog.py tests/test_skill_references.py` green.
- `git diff --stat docs/warehouse-catalog.md docs/warehouse-catalog.json` is empty — byte-identical, as the scope requires.
- `uv run pytest -m "not gamedata"`, ruff, ruff format --check, mypy green.
- `/update-docs` reports no remaining drift in CLAUDE.md's Status paragraph or its `src/ootp_ai/` map entry.

**Commit note:** Retire the documented ingest gap: README names the command, resolve.py's 'run the ingest before rendering' becomes true, and the status-verb boundary with incremental-loading is written into both requests.

#### Phase 7 — Phase 7 — Full sweep, measurements recorded, USER-RUN criteria handed over

**Goal:** Prove nothing regressed across the whole gamedata surface, record the numbers the scope obliged the plan to measure, and hand AC18/AC19 to the operator without the acceptance panel claiming them.

**Steps:**

- Run the complete offline suite and the complete gamedata suite. The gamedata run costs ~2m35s for AC11 alone (measured 2026-08-16 over 30,703 files and ~6.4 GB hashed three times) plus the rest — budget for it and do not interrupt it.
- Record in the phase handoff: the measured pre-flight digest seconds, the `verify_snapshot` seconds, the end-to-end wall clock of one `land` against the probe, and the snapshot size. Correct the stale figure while you are there: `tests/test_read_only.py:187`'s comment says '46 MB directory per run'; the panel measured 52.4 MiB for the managed league's landed snapshot on 2026-08-30. Update that comment, and `tests/test_extraction_cost.py:46`'s '~46 MB across four files' only if you have re-measured the four PARSED_FILES specifically — do not propagate a number you did not measure.
- Confirm `ingest_save` is still exercised: `tests/test_provenance.py:30` imports it and remains its caller. It is not orphaned by the AC11 re-point.
- Write the USER-RUN criteria out for the operator verbatim, with their prerequisite: AC18 needs `OOTP_PROBE_LEAGUE` configured if run against the probe; otherwise run it against `settings.managed`, which is safe because the command only reads the save.
- Hand off to `/commit`, then the PR. **Never push to `main`, never force-push, never amend** — and the PR itself stays the operator's.

**Acceptance:**

- AC9: `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` (strict, over `src` and `tests`) green; `ingest.__all__` unchanged; every one of the ten `from ootp_ai.ingest import ...` sites imports without edit.
- AC16: `uv run pytest -m gamedata tests/test_read_only.py::test_a_full_run_touches_nothing_under_the_game_directories` green with its legs calling `read_save` in probe -> truth -> managed order; four manifest passes with `OOTP_TRUTH_LEAGUE` configured, three without; no MySQL dependency added; `test_the_manifest_is_not_vacuous` green alongside it.
- AC17: `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py` green. Explicitly: `test_parser_vs_export.py:130`'s `which="truth_save"` path still works, and `landed_probe` still lands with `ingest_seq=None` — all three of its test-only powers unchanged.
- `uv run pytest` (both markers) green end to end.
- AC18 and AC19 are stated as USER-RUN in the handoff and are NOT claimed as passed by any agent.

**Commit note:** Full offline and gamedata sweep green; pre-flight, verify and end-to-end costs measured and recorded; the two USER-RUN acceptance criteria handed to the operator.

### Testing

## The shape of the verification

**Offline (CI, every PR) — `tests/test_ingest_command.py`, the offline half.** Nine of the
nineteen criteria are provable with no game, no save and no MySQL, because
`config.load_settings(env)` (`config.py:111`) takes a mapping and every side effect is
injected. This half covers: the argparse surface (AC2), target resolution by configured save
name including the exit-2 unknown-id path (AC3), the two formatters against
`test_no_leaks.PATTERNS` imported rather than restated (AC4), the refusal surface with
`land_snapshot` monkeypatched (AC5), the `WRITERS` byte-identity assertion (AC1), the
shared-function identity assertion (AC6, first half), the `ensure_tables`-before-copy spy
(AC7), the README/resolve.py literal-string assertions (AC8), and five pure unit tests over
`reason_to_land` covering the sim-date, file-set, size and digest branches — which is what
makes AC13's *logic* testable in CI even though its end-to-end proof needs a game.

**Gamedata (probe only, run explicitly) — `tests/test_ingest_command.py`, the second half.**
`pytestmark = pytest.mark.gamedata`. SD-20 governs: every automated test targets the
disposable Challenge-mode probe, never the managed league. `load_settings` is monkeypatched
**in the command module** to return `replace(settings, snapshot_root=tmp_path)` — the idiom
at `tests/test_read_only.py:193` — which is how `--snapshot-root` stays off the CLI while the
exit-0 path is still a pytest assertion. Every landing is purged in `finally` via
`fixtures.warehouse.purge_snapshot`; without it each run adds ~301,000 rows to the dev schema.

**Regression safety — the three surfaces this change can break silently.**

1. **ADR 0001's proof.** `tests/test_read_only.py`'s AC11 legs are re-pointed onto `read_save`
   in Phase 2, not Phase 6, precisely so the guard is validated before anything depends on the
   seam. The manifest-pass count must not change (four with `OOTP_TRUTH_LEAGUE`, three
   without), no MySQL dependency may enter it (`:240-242` refuses that in terms), and
   `test_the_manifest_is_not_vacuous` must stay green beside it — a guard over an empty file
   set passes without proving anything.
2. **The `landed_probe` consumer set.** Re-pointing the fixture couples ~10 gamedata tests
   across four modules to one new function, so a defect in `read_save` reds all of them at
   once. The four modules — `test_snapshot_semantics.py` (`:65`, `:437`, `:597`),
   `test_grain_contracts.py` (`:65`, `:421`), `test_extraction_cost.py` (`:39`, `:75`, a
   timing harness with `DRIFT_FACTOR = 10.0`) and `test_parser_vs_export.py` (`:56`, `:130`,
   the Tier-B export diff, which lands the **standard-mode** truth save) — are run as a block
   at the end of Phases 2, 4 and 7. Note `test_bronze_landing.py` does **not** import
   `landed_probe` and is not in this set.
3. **The write and append-only guards.** `tests/test_read_only.py`'s `_writes_in`
   (`:348-358`) scans a module's own source text for `.mkdir(`, `.write_text(`,
   `.write_bytes(`, `.touch(`, `os.makedirs` and write-mode `open(`. Neither new module may
   contain any of them: `ingest/read.py` delegates every file creation to
   `snapshot.take_snapshot` (`snapshot.py:205`), and `ingest/__main__.py` writes nothing at
   all. That is what keeps `WRITERS` at three entries and refuses to widen ADR 0001's
   allowlist for zero benefit. Separately, `tests/test_bronze_landing.py:818`'s AST scan over
   `src/ootp_ai/warehouse/*.py` (`:812-815`) must stay green with the two new `SELECT` helpers
   present — they are reads, and `_MUTATING_SQL` (`:761-772`) matches only DELETE/DROP/
   TRUNCATE/REPLACE/ON DUPLICATE/UPDATE...SET shapes.

**The gate at every phase boundary.** `uv run pytest -m "not gamedata"` -> `uv run ruff check
.` -> `uv run ruff format --check .` -> `uv run mypy` -> the phase's own gamedata subset ->
then `/commit`, which stages deliberately, runs the doc-drift checks, and asks before writing.
Agents commit **only** through `/commit`, never `git commit` ad hoc, not for a one-line
change. CI re-runs the same gates on the PR; opening and merging the PR stays the operator's.

**What no agent may claim.** AC18 (fresh-machine `uv sync` -> bootstrap -> ingest -> render
produces a `roster.md` with `pytest` never invoked) and AC19 (the printed output pasted into a
scratch `.md` leaves `tests/test_no_leaks.py` green) are USER-RUN. AC18's precondition — an
empty schema — is genuinely unrunnable in an automated test: the app user's grants are
database-scoped to three named databases with no right to create a throwaway schema
(`ops/mysql-bootstrap.sql:54-63`), so the only way to meet it in code would be to `DROP` the
declared tables from the dev schema, destroying the first landed ingest via a `DROP` written
into tests days after ADR 0021 §3 banned one in `src/`.

### Risks

```text
- **The naive composition gets the re-run default wrong SILENTLY, and that is the specific failure to avoid.** `take_snapshot` with `ingest_seq=None` allocates the next free FILESYSTEM sequence and never raises (`snapshot.py:189-201`); `SnapshotExists` fires only when a sequence is named explicitly. So `land = snapshot + parse + land`, composed the obvious way, does not surface ADR 0021's refusal — it lands a full duplicate, ~52 MB on disk and ~301,000 rows, with no retention policy to reclaim either. Shipping a README that claims a protection the code does not provide is worse than shipping no command. Mitigation: the digest pre-flight is Phase 4's first wiring step and AC12 asserts that no snapshot directory is created on the refusal path.
- **The pre-flight costs a second read of the save, and the plan picks digest-before-copy.** The alternative — copy first, then compare — spends the ~52 MB copy and a filesystem sequence before refusing, which defeats the entire point of a refusal that is supposed to cost the operator nothing. The size fast path (`source_files` carries `size` as well as `sha256`, `ingest_run.py:180-191`) settles 'changed' without digesting in the common case, because a changed save almost always changes file sizes. Both costs must be MEASURED and the numbers written down in Phase 4; a measurement obligation nobody discharged is the same as no measurement.
- **`--new-look` is required for a case ADR 0021 names explicitly.** *'A parser fix re-lands the same snapshot at the next sequence'* — same bytes, same date, deliberate. Under the digest pre-flight that path refuses without the flag. This is the honest cost of the chosen default and it must be documented AT the flag's help text, not discovered by an operator mid-correction.
- **Two independent sequence allocators, with one live instance of drift — re-measured 2026-08-30.** `Test-Save-Standard-Mode` at 2024-03-18 has a snapshot directory at seq 1 and **no `ingest_run` row** (its warehouse rows were purged by `landed_probe`'s `finally` while the directory survived). Under a naive filesystem-only policy a first landing there takes seq 2 with no seq 1, and a later reader applying ADR 0021's *'monotonic integer ... starting at 1'* reads the gap as a lost landing. The opposite direction is not currently instantiated but is one `rm -rf var/` away: the filesystem would claim seq 1 and the command would hit `IngestRunExists` on a landing the operator never made. The `max(filesystem, warehouse) + 1` reconciliation handles both and prints its reasoning. Re-run `SELECT save_id, sim_date, MAX(ingest_seq) FROM ingest_run GROUP BY 1, 2;` against `var/snapshots/` if the warehouse has moved since.
- **An explicit `ingest_seq` weakens the deadlock retry, invisibly.** `land_snapshot` retries on MySQL 1213/1205 and re-allocates the sequence each attempt (`load.py:232-250`), which only works on the `ingest_seq=None` branch. The command therefore has weaker contention behaviour than the fixture it shares a path with: a lost race surfaces as a refusal rather than a recovery. Unlikely in a single-operator setup; stated so it is a trade rather than an inheritance.
- **Conflating contention with a refusal.** `load.py:146-154` names this failure in terms: an operator told 'already landed' for a `ConcurrentLandingError` goes looking for a landing that never happened. AC5 asserts the two messages are distinct; do not collapse them into one handler for tidiness.
- **Re-pointing the fixture can silently change its sequence policy, and the failure surfaces somewhere else.** `landed_probe` lands with `ingest_seq=None` because a temp directory always allocates 1 on the filesystem side. If the CLI's explicit-sequence policy travels with the shared function, `landed_probe` starts colliding at seq 1 and the failure appears as `IngestRunExists` in unrelated grain tests. This is exactly why `read_save` has NO `ingest_seq` parameter. The fixture's loud-skip discipline (`tests/fixtures/warehouse.py:82-96`, *'Never a vacuous pass'*) must survive unchanged.
- **`from X import y` binds a name — monkeypatching the source module does not rebind it.** AC6's recorded-call test must patch both `ootp_ai.ingest.__main__.read_save` and `fixtures.warehouse.read_save`. Patching only `ootp_ai.ingest.read.read_save` records zero calls and the test passes or fails for the wrong reason. The `is`-identity assertion is what proves sharing; the recorded calls prove reach.
- **`from tests.test_read_only import WRITERS` will not import.** This repo has no `conftest.py` anywhere and `tests/` contains no `__init__.py`; the house form is a top-level import (`import test_no_leaks as guard`, `tests/test_leak_guard_scope.py:34`). `tests/fixtures/README.md:44-49` records that the dotted form 'passes locally and fails elsewhere'. AC1's literal spelling is illustrative; write `from test_read_only import WRITERS`.
- **AC11 is the most expensive test in the repo and must not get more expensive** — 2m35s over 30,703 files, ~6.4 GB hashed three times, measured 2026-08-16. `read_save` must do no digest work when `previous is None`, which is the case for all three legs. As a bonus the legs get CHEAPER: dropping `ingest_save` removes `_describe(..., payload=None)`'s measured ~48 MB of avoidable re-reads per leg (`ingest.py:481-501`) — of the snapshot COPY, so no game-read coverage is lost.
- **The managed league is the default target and there is no automated guard against it.** The structural protection holds — nothing in `src/` opens a game file for writing, `reject_inside_game_roots` fences the write roots, and AC11 proves it by manifest diff — so the realistic harm is a wasted snapshot and a landing under the wrong `save_id`, recoverable and immediately visible in the printed *resolved* `save_id`. Stated so the silence is a decision rather than an oversight.
- **Ingesting while OOTP is running is only partially guarded.** `_copy_one` digests each source before and after its own copy (`snapshot.py:296-319`) and `check_sim_dates` refuses a mixed snapshot, but neither catches a mid-write change ACROSS files at an unchanged sim date. A CLI makes this reachable outside a deliberate `-m gamedata` run — exactly when the operator is least likely to have quit the game first. A spike on whether OOTP is running is explicitly NOT in scope: `docs/data-access.md:95` labels `flag_save_completed.dat`'s content `assumed`, and this repo's label table forbids building on an assumed claim.
- **Making landing one keystroke accelerates a cost nobody has bounded.** `bronze_name` re-lands 264,095 rows per snapshot, no retention policy exists, and ADR 0018 leaves the per-date growth rate `unconfirmed`. The command prints per-table row counts, which is the measurable it can honestly produce; a disk-bytes figure needs its own `information_schema` query and belongs to the retention argument both ADR 0018 and ADR 0021 defer.
- **The downstream contract is being pinned by this diff.** `incremental-loading` will write its operator procedure against whatever invocation string, flag names, exit codes and output format ship. All four are cheap now and expensive after — which is why the human line-one format and the `--json` field set are specified here rather than left to taste, and why `--json` (not a print format to grep) is the stable machine contract.
- **`ensure_tables` does not repair a drifted table** (`load.py:169-189` — it creates and never replaces) and nothing tells the operator when that bites. Accepted as a known limitation, not fixed here; a migration is a decision somebody makes in the open. When `open-front-office` Phase B puts an `ensure_views()` beside it, whether the implicit rule extends is THAT request's decision.
- **Roughly half of this work lands in `tests/`, which is in the write-capable builder's deny set** (`.claude/agents/data-engineer.md:154-171`). Every test file must be authored on the main thread, as `first-sight` did. If a subagent is spawned for the `src/` half, tell it explicitly that it gets read-only git — never `checkout`/`reset`/`restore`/`clean`/`stash` — and bubble any destructive-git need back up.
- **The package promotion may be recorded by git as delete + add** (a 502-line move). All ten `from ootp_ai.ingest import ...` sites survive unchanged, but line-numbered prose does not. The single live reference to correct is `.claude/agents/data-engineer-memory.md:202`; no Markdown link targets the file, and `tests/test_doc_links.py` checks only `[text](target)` links and bare `requests/...` tokens (`:20`, `:48`), so CI is unaffected. **Historical `requests/**/reviews/` handoffs must NOT be rewritten** — they are the record of what was believed when.
```

### Files to touch

- `src/ootp_ai/ingest.py` — DELETED — moved verbatim to `src/ootp_ai/ingest/__init__.py` (Phase 1). Not edited, moved.
- `src/ootp_ai/ingest/__init__.py` — NEW (the move). Byte-identical to today's `ingest.py`. `__all__` (`:50-62`) unchanged; adds no import of its new siblings.
- `src/ootp_ai/ingest/read.py` — NEW. The one shared game-touching function: `read_save(save, *, snapshot_root, previous=None) -> SaveRead`, plus `PriorLanding`, `SaveRead`, `SaveUnchanged` and the pure `reason_to_land`. No `ingest_seq` parameter. No warehouse import. No write verb in its own source text, so `WRITERS` stays byte-unchanged.
- `src/ootp_ai/ingest/__main__.py` — NEW. `main(argv) -> int` over `land(settings, *, save_id=None, snapshot_root=None, new_look=False, from_snapshot=None)`, `_parser()`, `LandingResult`, `format_result`, `format_json`, and the module constant holding the literal invocation string. Opens no file and creates no directory — a requirement, not an accident.
- `src/ootp_ai/snapshot.py` — `_read_sim_date` (`:285-293`) promoted to public `read_sim_date`; caller at `:185` updated; name added to `__all__` (`:50-63`); docstring gains why it is public.
- `src/ootp_ai/warehouse/ingest_run.py` — Two new read-only helpers added to `__all__`: `latest_landing(connection, *, save_id)` (most recent landing for a save, JSON decoded) and `landed_max_seq(connection, *, save_id, sim_date)` (plain `SELECT COALESCE(MAX(...))`, no `FOR UPDATE`, docstring contrasting it with `next_ingest_seq` at `:137-153`). No DELETE, UPDATE or upsert path added.
- `src/ootp_ai/reports/resolve.py` — `_nothing_landed_message` (`:168-187`): the 'run the ingest before rendering' branch at `:179-182` now names the literal command, making the sentence true.
- `tests/fixtures/warehouse.py` — `landed_probe` (`:133-157`) re-pointed onto `read_save` at `:151`; all three test-only powers unchanged (temp snapshot root, `ingest_seq=None` at the landing call, `purge_snapshot` in `finally`); docstring gains one sentence saying the landing path is now shared with the operator's command.
- `tests/test_read_only.py` — The three AC11 legs (`:254`, `:263`, `:268`) re-pointed onto `read_save`; unused `ingest_save`/`parse_snapshot` imports removed; test docstring (`:230-243`) updated to say the guard now brackets every game read the command makes and why landing stays outside it. `WRITERS` (`:303-317`) BYTE-UNCHANGED. The stale '46 MB directory per run' comment at `:187` corrected to ~52 MB.
- `tests/test_ingest_command.py` — NEW. Offline half (CI) + gamedata half against the probe only. Authored on the main thread — `tests/` is in the builder's deny set.
- `README.md` — The `:128-134` 'There is no ingest command' blockquote deleted; the command added to the setup fence at `:109-119`; one line noting the first run creates the eight declared tables.
- `CLAUDE.md` — Status paragraph ('serves two reports') and the `src/ootp_ai/` project-map entry updated — through `/update-docs`, not by hand.
- `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md` — Dated amendment carrying the status-verb boundary sentence: this request owns the disk-and-refusal half, `incremental-loading` owns the warehouse-inventory half (its `:61`).
- `requests/feature-requests/README.md` — The `[ingest-command]` Index row's Stage cell: `scoped` -> `planned` at stage 3, then `implemented` at stage 4, matched by the `[<slug>]` link.
- `requests/feature-requests/ingest-command/IMPLEMENTATION_PLAN.md` — NEW — this plan, opening `> **Status:** planned · created 2026-08-30 · decided · next: implement`.
- `.claude/agents/data-engineer-memory.md` — `:202`'s evidence path `src/ootp_ai/ingest.py` corrected to `src/ootp_ai/ingest/__init__.py`. The single live line-numbered reference to the moved file.
- `DO NOT TOUCH` — `src/ootp_ai/contracts/tables.toml`, `docs/warehouse-catalog.md` + `.json` (must be byte-identical), `ops/mysql-bootstrap.sql`, `.env.example` (no new key), `pyproject.toml` (no `[project.scripts]`), and every `requests/**/reviews/` handoff.

### Code references cited

- `src/ootp_ai/reports/__main__.py:36-59` — The entry-point pattern to copy: `main(argv: list[str] | None = None) -> int`, `ConfigError` -> print to stderr -> return 2, domain refusals -> `f"{type(error).__name__}: {error}"` -> return 1, success -> print -> return 0. Verified.
- `src/ootp_ai/reports/__main__.py:130` — `sub = parser.add_subparsers(dest="command", required=True)` — the required subcommand that makes `main([])` RAISE `SystemExit(2)` rather than return 2. Verified; AC2 depends on it.
- `src/ootp_ai/snapshot.py:189-201` — `take_snapshot` allocates the next free filesystem sequence when `ingest_seq is None` and raises `SnapshotExists` only when a sequence is named explicitly — the auto-allocation that makes naive composition land a silent duplicate. Verified.
- `src/ootp_ai/snapshot.py:285-293` — `_read_sim_date(save)` reads `teams.dat`'s header for the league's in-game date. Exactly one caller, at `:185`; grep confirms no test references it, so promotion to `read_sim_date` is safe. Verified.
- `src/ootp_ai/snapshot.py:254-279` — `verify_snapshot` re-digests every manifest file; its docstring says 'Called after landing a snapshot', which has zero `src/` callers today and is therefore currently false. Verified.
- `src/ootp_ai/warehouse/load.py:169-189` — `ensure_tables` creates any declared table the schema is missing, commits, and returns the names created; it deliberately does not repair a drifted table. Its only caller in the repo is `tests/fixtures/warehouse.py:93`. Verified by grep.
- `src/ootp_ai/warehouse/load.py:203-217` — `land_snapshot`'s `ingest_seq` contract: an integer claims exactly that sequence and refuses with `IngestRunExists`; `None` allocates from the warehouse inside the transaction. The choice is the caller's because only the caller knows whether a durable snapshot is on disk. Verified.
- `src/ootp_ai/warehouse/load.py:232-250` — The bounded deadlock retry re-allocates the sequence on each attempt, which only helps on the `ingest_seq=None` branch — hence the command's weaker contention behaviour. Verified.
- `src/ootp_ai/warehouse/ingest_run.py:137-153` — `next_ingest_seq` uses `FOR UPDATE` and its docstring requires it be called inside the transaction that inserts the row. Deliberately NOT reused by the pre-flight; a plain `SELECT COALESCE(MAX(...))` helper is added instead. Verified.
- `src/ootp_ai/warehouse/ingest_run.py:180-191` — `source_files` stores per-file `name`, `size`, `sha256` and `version` — the exact material the digest pre-flight needs, with `size` giving the cheap fast path. Verified.
- `src/ootp_ai/warehouse/ingest_run.py:262-268` — `read_ingest_run` decodes the three JSON columns because PyMySQL hands a JSON column back as text. The new `latest_landing` helper must do the same. Verified.
- `src/ootp_ai/config.py:56-68` — `to_save_id` normalises a league name to `[A-Za-z0-9_-]`, which is why printing a resolved `save_id` can never carry a drive letter, a separator or a home directory into stdout. Verified.
- `src/ootp_ai/config.py:111` — `load_settings(env: Mapping[str, str] | None = None)` — the mapping injection point AC3's offline resolution tests use. Verified.
- `src/ootp_ai/saves.py:81-84` — `is_challenge_mode(save)` is a `stat()` of `challenge.dat` against a measured 241 bytes; the module docstring (`:10-15`) calls it 'cheap enough to run on every ingest'. It is a game touch, so it lives inside the shared bracketed function. Verified.
- `tests/test_read_only.py:303-317` — `WRITERS` holds exactly three package-relative paths — `snapshot.py`, `reports/__main__.py`, `catalog/__main__.py`. AC1 asserts this set unchanged. Verified byte-for-byte.
- `tests/test_read_only.py:348-358` — `_writes_in` scans a module's OWN source text for write-mode `open(`, `.write_text(`, `.write_bytes(`, `.touch(`, `.mkdir(` and `os.makedirs` — it is not a capability model, so a module delegating file creation to `snapshot.py` trips nothing and needs no allowlist entry. Verified.
- `tests/test_read_only.py:240-242` — The AC11 docstring refuses in terms to include landing: pulling a warehouse dependency into ADR 0001's guard would let an unrelated MySQL outage silence the one test the project cannot afford to lose. Verified.
- `tests/fixtures/warehouse.py:151` — `landed_probe` composes `parse_snapshot(take_snapshot(save, snapshot_root=Path(tmp)))` — the cheaper shape the shared function copies, and it does NOT call `ingest_save`. Verified.
- `tests/fixtures/README.md:44-49` — This repo deliberately has no `conftest.py` anywhere, `fixtures` is declared first-party in `pyproject.toml:88`, and the dotted `from tests....` form 'passes locally and fails elsewhere' — so AC1's cross-test import must be written `from test_read_only import WRITERS`. Verified.
- `tests/test_bronze_landing.py:812-815` — The ADR 0021 append-only AST scan is scoped to `src/ootp_ai/warehouse/*.py` only, so the new modules under `src/ootp_ai/ingest/` are outside it — and the two new `SELECT` helpers inside `warehouse/` are reads, which `_MUTATING_SQL` (`:761-772`) does not match. Verified.
- `tests/test_snapshot_semantics.py:537` — `test_two_sequences_of_one_sim_date_both_persist` is the existing assertion shape AC14 copies for the `--new-look` digest-stability check. Verified by grep.
- `tests/test_extraction_cost.py:57,75` — `DRIFT_FACTOR = 10.0` and `landed_probe(settings, warehouse, which="probe_save")` — the timing harness is one of the two riskiest real consumers of the re-pointed fixture. `parse_seconds` measures only the walk, so the pre-flight cannot perturb it, but the fixture passes `previous=None` and does no digest work at all. Verified.
- `tests/test_parser_vs_export.py:130` — `landed_probe(settings, connection, which="truth_save")` — the Tier-B export diff lands the STANDARD-mode save through the fixture, which is why the folded-in mode line must report and never refuse. Verified by grep.
```text
- `tests/test_doc_links.py:20,48` — The link guard checks only `[text](target)` Markdown links and bare `requests/...` tokens; a bare `src/ootp_ai/ingest.py` written in prose is not checked, so the package move cannot redden CI — but `.claude/agents/data-engineer-memory.md:202` is still corrected for truth. Verified.
```
- `ops/mysql-bootstrap.sql:23,30,42,54` — Three `CREATE DATABASE`, one `CREATE USER`, database-scoped grants only — and NO `CREATE TABLE` anywhere in the file. This is what makes `ensure_tables` load-bearing for the fresh-clone criterion and what makes an automated empty-schema test unrunnable. Verified by reading the whole file.
- `README.md:117-118,128-134` — The setup fence's two existing `uv run python -m ootp_ai.<pkg>` lines, and the 'There is no ingest command' blockquote AC8 requires deleted. Verified.
- `src/ootp_ai/reports/resolve.py:179-182` — `_nothing_landed_message`'s empty-warehouse branch already tells the operator to 'run the ingest before rendering' — the sentence this change makes true. Verified.
- `src/ootp_ai/contracts/tables.toml` — Eight declared tables, confirmed by running `load_contracts()`: bronze_team, bronze_player, bronze_team_roster, bronze_name, bronze_division_team, bronze_league_event, bronze_field_label, ingest_run. Untouched by this change; `docs/warehouse-catalog.md` must be byte-identical afterwards. Verified by execution.
- `docs/decisions/0021-bronze-landing-is-append-only.md:21-27` — ADR 0021 names a `(save_id, sim_date)`-keyed refusal BY NAME and calls it 'worse, because it blocks a legitimate and frequent operation'. This is why the default is the digest pre-flight and why no ADR amendment is needed. Verified.
- `docs/data-access.md:95` — The content column for `flag_save_completed.dat` and its siblings is `assumed` from the filename with nothing having opened them — which is why the 'is OOTP running?' spike is out of scope rather than folded in. Verified.
- `measured 2026-08-30 — `SELECT save_id, sim_date, MAX(ingest_seq) FROM ingest_run GROUP BY 1,2` vs `var/snapshots/`` — Two rows in the warehouse (`OOTP-AI` 2024-03-07 seq 1; `Test-Save-Challenge-Mode` 2024-03-18 seq 1) against three snapshot directory trees — `Test-Save-Standard-Mode` 2024-03-18 has a seq-1 directory and NO warehouse row. The scope's drift table is confirmed live, which is what the `max(filesystem, warehouse) + 1` reconciliation exists to handle.

### Open questions

- **`--from-snapshot` and `IngestRunExists`.** AC15 requires that a `--from-snapshot` re-land produce *a new `ingest_run` row*, which forces the `max(dir_seq, warehouse_max + 1)` reconciliation on that path — and that in turn means `IngestRunExists` is no longer reachable through the command except by losing a race. Scope Decisions §3 states in passing that `--from-snapshot` is 'the only way the `IngestRunExists` refusal is reachable through the command'. The plan follows the acceptance criterion (which is binding) over the incidental claim, and records the divergence here rather than silently resolving it. Confirm at review, or the alternative is: claim the directory's own number, refuse with `IngestRunExists` on collision, and require `--new-look` to advance — at the cost of AC15 needing that flag.
- **Where the two new read helpers live.** The plan puts `latest_landing` and `landed_max_seq` in `src/ootp_ai/warehouse/ingest_run.py`, beside the table they read and beside `next_ingest_seq`, whose docstring warns against exactly the misuse a distant sibling would invite. The precedent cuts both ways: `reports/resolve.py:78-94` writes its own `ingest_run` SQL outside `warehouse/`. If keeping `warehouse/` byte-stable matters more, the helpers move into `ingest/__main__.py` with no other change.
- **`--new-look` and `--from-snapshot` as a mutually exclusive argparse group.** Chosen because a snapshot re-land has no digest pre-flight to override, so the combination is meaningless and argparse's own message is better than a runtime check. It is slightly stricter than the scope requires (AC2 only asks that both flags exist). If a future verb wants them combinable, the group is one line to remove.
- **How much the human stdout block should carry.** The plan puts `residual_bytes` in `--json` only, keeping the human form to the triple, mode, created tables, the sequence sentence, row counts and timings. `incremental-loading` gets its stable contract from `--json`; if the operator wants residuals on screen too, that is a one-line formatter change, cheap now and cheap later.
- **Whether the stale ~46 MB figures outside `tests/test_read_only.py:187` get corrected in this change.** The plan corrects that one comment (the panel measured 52.4 MiB for the managed league's landed snapshot on 2026-08-30) but deliberately does not touch `tests/test_extraction_cost.py:46`'s '~46 MB across four files', which describes the four PARSED_FILES rather than the five-file snapshot and has not been independently re-measured. Correcting a number nobody re-measured would be the same defect in the other direction.
