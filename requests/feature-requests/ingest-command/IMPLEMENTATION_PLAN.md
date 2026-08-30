> **Status:** planned · created 2026-08-30 · decided · next: implement

# Implementation Plan — An ingest command: the pipeline has no way to be run

> **One-line goal:** `uv run python -m ootp_ai.ingest land` takes a configured save from disk to
> a landed bronze snapshot and prints the `(save_id, sim_date, ingest_seq)` triple, so a fresh
> clone reaches a rendered roster without running `pytest`. · **Target component:**
> `src/ootp_ai/ingest/` (new package), `src/ootp_ai/snapshot.py`,
> `src/ootp_ai/warehouse/ingest_run.py`, `tests/`, `README.md`.

## 1. Onboarding — read these first

**What this is.** The operator's first write-side entry point. It is the *third* instance of an
established shape, not a new one: `reports/__main__.py` and `catalog/__main__.py` already set the
pattern — resolve settings, resolve the target explicitly, act, print what it did — and both only
*read* a landing. Nothing outside `pytest` has ever created one.

**What it is not.** No parser change, no new field, no ninth table. `src/ootp_ai/contracts/tables.toml`
is untouched and `docs/warehouse-catalog.md` must be byte-identical afterwards. The whole risk sits
in one operator-facing default and one test-suite re-point.

| # | File | Why |
|---|---|---|
| 1 | [`PROJECT_SCOPE.md`](PROJECT_SCOPE.md) | The DECIDED upstream artifact — consume it, never re-open it. Goals, the 19 acceptance criteria, the tiered scope, Risks, and the seven Decisions |
| 2 | `src/ootp_ai/reports/__main__.py` | **Read first.** `:1-11` the rule that entry points are deliberate; `:36-59` `main(argv) -> int` and the 0/1/2 convention; `:62-73` the testable `render(settings, *, save_id=None, ...)`; `:98-99` the connection closed in `finally`; `:125-151` `_parser()` with `add_subparsers(dest="command", required=True)` at `:130` — which is why `main([])` **raises** `SystemExit(2)`; `:154-155` the `raise SystemExit(main())` guard |
| 3 | `src/ootp_ai/catalog/__main__.py` | The second instance. `:3-10` argues why it took no subcommand and why it is allowlisted by package-relative path; `:118` `_fence_docs_root`, the record of the project's only operator-typed write root and the reason `--snapshot-root` is not a flag here |
| 4 | `src/ootp_ai/ingest.py` | The 502-line module promoted verbatim in Phase 1. `:1-28` the three-way split's rationale (`:10-12`) and the no-path rule (`:25-27`); `:50-62` `__all__` — eleven names, byte-unchanged, which is why the shared function goes in a **new** module; `:161-217` `parse_snapshot`; `:235-278` the refusals to surface; `:300` `dump_parse`'s `parse_snapshot(read_manifest(path))` that `--from-snapshot` reuses; `:481-501` `_describe`, whose `:488-492` measures *"~48 MB of avoidable I/O per ingest"* |
| 5 | `src/ootp_ai/snapshot.py` | The only module in `src/` allowed to create a file. `:50-63` `__all__`; `:71-83` `SNAPSHOT_FILES` and its dated 2026-08-16 widening; `:121-127` `SnapshotFile` — **`sha256: str` is mandatory**, which shapes the pre-flight's whole design; `:146-164` the filesystem `next_ingest_seq`; `:167-216` `take_snapshot`, whose `:189-201` auto-allocation is what makes naive composition silently duplicate; `:205` the lone `mkdir`; `:219-251` `read_manifest`; `:254-279` `verify_snapshot`, zero `src/` callers today; `:285-293` `_read_sim_date`; `:296-319` `_copy_one` |
| 6 | `src/ootp_ai/warehouse/load.py` | `:68-74` why no DELETE/UPDATE exists; `:146-154` `ConcurrentLandingError` and the failure it names; `:169-189` `ensure_tables` — creates, never repairs, **one caller in the repo**; `:195-250` `land_snapshot`, its `parsed: ParsedSnapshot` (non-optional) signature, the explicit-vs-`None` `ingest_seq` contract at `:202-217`, and the deadlock retry at `:232-250`; `:540-572` `table_digest` |
| 7 | `src/ootp_ai/warehouse/ingest_run.py` | `:16-35` the **measured** correction that `SELECT … FOR UPDATE` does not serialise two allocators — read before adding any SELECT here; `:61-71` `__all__`; `:88` `_JSON_COLUMNS` (includes `source_files`, so it decodes); `:137-153` `next_ingest_seq` and its must-be-in-the-inserting-transaction docstring; `:156-198` `ingest_run_values`, where `source_files` carries per-file `size` **and** `sha256` |
| 8 | `src/ootp_ai/config.py` | `:71-84` `SaveRef` and `save_id = to_save_id(league)`; `:99-108` `Settings`; `:111` `load_settings(env)`, the mapping injection point; `:169-173` `_required_directory`, whose precondition is easy to miss; `:186-215` `reject_inside_game_roots` |
| 9 | `tests/test_config.py` `:24-36` | **The established offline-`Settings` recipe.** `_env(tmp_path, **overrides)` mkdirs `tmp_path/install` and `tmp_path/saves` and supplies the required keys. Without it, `load_settings(mapping)` raises `ConfigError` and the offline tests cannot be written |
| 10 | `tests/test_read_only.py` | `:25-28` the measured AC11 cost (2m35s, 30,703 files, ~6.4 GB); `:182-193` the `replace(settings, snapshot_root=...)` idiom and the `pytest.skip` on `ConfigError`; `:222-269` the three legs and `:240-242`'s refusal to include landing; `:303-317` `WRITERS`; `:322-334` `DESTRUCTIVE_CALLS`, `:337` `CREATIVE_CALLS`, `:348-358` `_writes_in` |
| 11 | `tests/fixtures/warehouse.py` | `:19-26` why the landings allocate from the warehouse; `:59-96` the loud-skip discipline and the lone `ensure_tables` call at `:93`; `:99-130` `purge_snapshot`; `:133-157` `landed_probe`, composing `parse_snapshot(take_snapshot(...))` at `:151` |
| 12 | `tests/test_bronze_landing.py` `:188-195`, `:761-772`, `:812-815` | The `_FakeConnection` + `cast` pattern the new offline helper tests copy, and the mutation scan the new SQL must pass |
| 13 | `docs/decisions/0021-bronze-landing-is-append-only.md` | The semantics the command surfaces. `:57-59` names the correction workflow `--from-snapshot` implements |
| 14 | [`incremental-loading`](../incremental-loading/FEATURE_REQUEST.md) | The downstream consumer that will write its procedure against this command's invocation string, flags, exit codes and output format |

**Environment prerequisites — state these before starting, not on discovery.** Phases 2, 5 and 6
**cannot be completed on a CI-shaped machine.** They need `.env` with `OOTP_PROBE_LEAGUE` set, the
probe save on disk, and a reachable MySQL carrying the `ootp_dev` schema. See §4's anti-vacuous rule:
a fully-skipped `-m gamedata` run exits 0 and is **not** a checkpoint.

## 2. Architecture map

Today the pipeline's write side is a set of library functions with no caller but `pytest`:

```
save on disk ──▶ take_snapshot ──▶ parse_snapshot ──▶ land_snapshot ──▶ bronze_*
                (snapshot.py)      (ingest.py)        (warehouse/load.py)
                       ▲                  ▲                   ▲
                       └──────────────────┴───────────────────┘
                        only callers: tests/fixtures/warehouse.py:151-152
                                      tests/test_read_only.py:254,263,268
```

After this change:

```
ingest/__main__.py::main(argv) -> int          ← argparse, exit codes, formatters
        └── land(settings, *, save_id, ...) -> LandingResult
              ├── connect_warehouse ─▶ ensure_tables            (warehouse, no game)
              ├── latest_landing(connection, save_id=...)       (warehouse, no game)
              ├── ingest/read.py::read_save(save, *, snapshot_root, previous)
              │      └── EVERY game read lives here ─── also called by
              │          tests/test_read_only.py's 3 AC11 legs  (previous=None)
              │          tests/fixtures/warehouse.py::landed_probe (previous=None)
              ├── landed_max_seq ─▶ seq = max(dir_seq, warehouse_max + 1)
              ├── verify_snapshot(copy)                         (snapshot, no game)
              └── land_snapshot(parsed, ingest_seq=seq)
```

**The seam that matters.** `read_save` is the *only* function that touches the game directory, and
the warehouse lookup happens **outside** it — the prior landing arrives as plain data. That is what
lets ADR 0001's manifest diff bracket every game read the command makes without pulling MySQL into
the one test the project cannot afford to lose (`tests/test_read_only.py:240-242` refuses that in
terms).

## 3. Phased implementation

Each phase ends **green locally** — `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy` — and is landed via `/commit`, which stages deliberately, runs the doc checks and asks
before writing. CI re-runs the same gates on the PR.

---

### Phase 1 — Promote `ingest` to a package; publish `read_sim_date` and `source_facts`

**Goal.** A pure structural move with zero behaviour change, landed alone so the diff a reviewer
reads for the real work is not 502 lines of moved file.

**Steps.**

1. **Find every reference before the move.** `rg` is **not on PATH on this machine** — use
   `Select-String -Pattern 'ingest\.py' -Path . -Recurse` (unqualified, not just path-qualified
   forms, which misses bare filename mentions). Expected dispositions:
   - `.claude/agents/data-engineer-memory.md:202` — a **bare path in an evidence line, no line
     number**. Correct it, and per that file's own append-freely rule at `:41`, *append* a dated
     line recording the move rather than rewriting surrounding prose.
   - Anything under `requests/**/` — **do not rewrite, at all.** Not the `reviews/` handoffs and not
     this request's own FEATURE_REQUEST or PROJECT_SCOPE. They are the record of what was believed
     when.
2. `git mv src/ootp_ai/ingest.py src/ootp_ai/ingest/__init__.py`. No content edit. Git may record
   delete+add rather than a rename; that is expected.
3. In `snapshot.py`: rename `_read_sim_date` (`:285-293`) to public `read_sim_date`, update its
   single caller at `:185`, and add a docstring saying why it is public — it is the only cheap answer
   to *what date would this land at?* before 52.4 MiB is copied (measured 0.005 s).
4. Add public `source_facts(save) -> tuple[SnapshotFile, ...]` to `snapshot.py`, reusing the private
   `_digest` (`:322-328`) so digest logic stays in one module.
5. Insert both into `snapshot.__all__` **in sorted order** (ruff RUF022): `read_manifest` <
   `read_sim_date` < `source_facts` < `take_snapshot`.

**Acceptance.**

- `uv run python -c "import ootp_ai.ingest as m; print(m.__name__, bool(m.__path__), len(m.__all__))"`
  prints `ootp_ai.ingest True 11`. **Do not print `__file__`** — it is an absolute path.
- Byte-exactness proved by content hash, never by a redirect that would corrupt the baseline:
  `git show HEAD:src/ootp_ai/ingest.py | git hash-object --stdin` equals
  `git hash-object src/ootp_ai/ingest/__init__.py`.
- `Select-String 'from ootp_ai\.ingest import'` totals 10 files, **none edited in this diff**.
  `Select-String '_read_sim_date'` returns nothing.
- `uv run python -c "import ootp_ai.snapshot as s; assert 'read_sim_date' in s.__all__ and 'source_facts' in s.__all__"` exits 0.
- Re-run the allocator query (§6 risk 3) and record the result. The reconciliation rule is correct
  under either outcome, so nothing downstream is blocked either way.
- `uv run pytest -m "not gamedata"` + the four gates green; `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_provenance.py`
  green — `test_provenance.py` is the one remaining `ingest_save` consumer.

**Commit note.** *Promote ingest.py to a package and publish read_sim_date and source_facts.* A
verbatim 502-line move plus two API promotions. `python -m ootp_ai.ingest` on a *module* would execute
it as `__main__` while every package-qualified import re-imports it as `ootp_ai.ingest`, producing two
`ParsedSnapshot` classes and a silent `isinstance` failure across `warehouse/load.py:90` (label:
`inferred` from Python import semantics, not reproduced — and the promotion is required regardless,
because a module cannot host a `__main__`).

---

### Phase 2 — The shared game-touching function, with `landed_probe` and ADR 0001's proof re-pointed

**Goal.** One function performs every game read the command will make, and the two existing callers
route through it — **before any command exists**, so a failure has exactly one candidate cause. This
is the phase that could weaken the one test the project cannot afford to lose.

**Steps.**

1. Create `src/ootp_ai/ingest/read.py` with:
   - `PriorLanding` — the prior landing as plain data: `sim_date`, `files: tuple[SnapshotFile, ...]`,
     `ingest_seq`. No warehouse import in this module.
   - `SaveReading` — `parsed: ParsedSnapshot` (**non-optional**), `verdict: Literal["no-prior", "changed"]`,
     `snapshot_dir_seq: int`, `mode: str`. The unchanged case *raises*; it never returns a reading with
     no parse, and the docstring states that invariant in one sentence so the deleted alternative
     cannot be re-derived.
   - `SaveUnchanged(Exception)` — carries the prior triple, so the caller can name it.
   - **Two pure comparison functions, not one with two modes.** `SnapshotFile.sha256` is a mandatory
     `str` (`snapshot.py:121-127`), so there is no way to represent "size known, digest not computed":
     - `reason_from_sizes(previous, sim_date, sizes) -> str | None` — compares the sim date and the
       per-file sizes only. **The sha256 comparison is structurally unreachable here.**
     - `reason_from_digests(previous, current) -> str | None` — the digest comparison, called only
       when every size matched.
   - `read_save(save, *, snapshot_root, previous=None) -> SaveReading`.
2. `read_save`'s body, in order: `read_sim_date(save)` → `is_challenge_mode(save)` (**report, never
   refuse**) → if `previous is None`, skip straight to the copy → else `reason_from_sizes(...)`; if it
   returns a reason, proceed; if not, `source_facts(save)` then `reason_from_digests(...)`; if *that*
   returns nothing, raise `SaveUnchanged` → `take_snapshot(...)` → `parse_snapshot(...)`.
3. **A prior landing predating the dated 2026-08-16 `SNAPSHOT_FILES` widening names fewer than five
   files.** `reason_from_sizes` must treat any file in *today's* `SNAPSHOT_FILES` that `previous` does
   not name as **changed**. This is a real state on disk, not a hypothetical.
4. `read_save` reads `teams.dat` twice per call — once for `read_sim_date`, once inside
   `take_snapshot`. Accept it and say so in the docstring: the duplicate ~5 MB read is the price of
   `take_snapshot` keeping its single-argument contract.
5. **`read_save` takes no `ingest_seq` parameter, ever.** The sequence decision belongs only to
   whoever calls `land_snapshot`.
6. **Docstring hazard.** `_writes_in` (`tests/test_read_only.py:348-358`) and
   `test_the_pipeline_contains_no_destructive_filesystem_call` (`:375-386`) scan source *text* and
   strip only `#` comments — **not docstrings**. No literal from `DESTRUCTIVE_CALLS` (`:322-334`) or
   `CREATIVE_CALLS` (`:337`) may appear anywhere in this module's source, prose included. Write
   "creates no directory of its own", never the call name.
7. **The call style, which is load-bearing for AC6.** Both call sites do `from ootp_ai.ingest import read`
   and call `read.read_save(...)`. Under this style a *single* patch on `ootp_ai.ingest.read.read_save`
   is observed by every caller — which is exactly what makes AC6's recorder impossible to get wrong.
8. Re-point `tests/fixtures/warehouse.py:151` onto `read.read_save(save, snapshot_root=Path(tmp)).parsed`,
   keeping the `TemporaryDirectory` root, the `ingest_seq=None` landing at `:152` and `purge_snapshot`
   in `finally` exactly as they are.
9. Re-point `tests/test_read_only.py`'s three legs at `:254`, `:263`, `:268` onto `read.read_save(...)`
   with `previous=None`, and rewrite the docstring paragraph at `:237-242`. No fourth leg, no MySQL, no
   change to the manifest-pass count.

**Acceptance.**

- **AC1:** `from test_read_only import WRITERS` (**bare**, not dotted — there is no `conftest.py`
  anywhere and no `tests/__init__.py`; pytest's prepend mode puts `tests/` on `sys.path`), then
  `assert WRITERS == {"snapshot.py", "reports/__main__.py", "catalog/__main__.py"}`, with a comment
  saying the new modules are deliberately absent because they create no file. `git diff tests/test_read_only.py`
  shows no line changed inside `:303-317`.
- Six offline unit tests over the two comparison functions, no game and no MySQL: a sim-date mismatch
  → a reason, with `source_facts` spied and proved unconsulted; one size changed → a reason, no digest
  performed; a file in today's `SNAPSHOT_FILES` absent from `previous` → a reason; **equal sizes →
  `reason_from_sizes` returns `None`** (i.e. escalates to digesting) rather than a reason; equal sizes
  with one sha256 changed → `reason_from_digests` returns a reason; fully identical → `None`, and
  `read_save` raises `SaveUnchanged`.
- The soundness guard is green: `SIM_DATE_SOURCE in SNAPSHOT_FILES` — this is what keeps Decision 1's
  derivation from rotting silently.
- `uv run pytest -m gamedata tests/test_read_only.py` green: still **four** manifest passes with
  `OOTP_TRUTH_LEAGUE` configured and **three** without; `test_the_manifest_is_not_vacuous` green
  alongside (AC16). Record the wall clock — it should be slightly **below** the 2m35s baseline, because
  the legs no longer pay `ingest_save`'s ~48 MB re-read.
- `uv run pytest -m gamedata tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py`
  green — the **real** `landed_probe` consumer set (AC17). Explicitly confirm `test_parser_vs_export.py:130`'s
  `which="truth_save"` path still works and that `landed_probe` still lands with `ingest_seq=None`.
- The four gates green.

**Commit note.** *One shared game-touching function, with the fixture and ADR 0001's proof re-pointed
onto it.* `read_save` performs every game read the operator's command makes and takes the prior landing
as plain data, so the warehouse lookup stays outside AC11's diff. It takes no `ingest_seq`. `WRITERS`
byte-unchanged; the manifest-pass count unchanged, and the legs get cheaper by ~48 MB each because the
composition is `take_snapshot + parse_snapshot`, not `ingest_save`.

---

### Phase 3 — The two read-only warehouse helpers

**Goal.** Add the two plain SELECTs the pre-flight and the dual-allocator line need, proved offline
against a fake cursor, kept separate so ADR 0021's mutation scan is exercised against the new SQL in
isolation.

**Steps.**

1. Add to `src/ootp_ai/warehouse/ingest_run.py`:
   - `latest_landing(connection, *, save_id)` — the save's most recent landing, JSON columns decoded
     as at `:262-268`. Returns `None` when the save has never landed.
   - `landed_max_seq(connection, *, save_id, sim_date)` — a plain
     `SELECT COALESCE(MAX(ingest_seq), 0) …` with **no `FOR UPDATE`**.
2. They live **here, beside `next_ingest_seq`** (`:137-153`), precisely so a future reader meets the
   `FOR UPDATE` contrast at the point of temptation. Both docstrings cite the measured correction at
   `:16-35`.
3. `__all__` in sorted order (RUF022): `ingest_run_values`, `landed_max_seq`, `latest_landing`,
   `next_ingest_seq`.

**Acceptance.**

- `uv run pytest -m "not gamedata" tests/test_bronze_landing.py` green — in particular
  `test_no_module_in_the_warehouse_can_mutate_a_landed_row` (`:818`), whose `_MUTATING_SQL` (`:761-772`)
  matches `UPDATE … SET` among others. A `SELECT COALESCE(MAX(...))` has no `SET`, so it passes by
  construction.
- Offline tests against a fake cursor, wrapping each helper in a local `_FakeConnection`-typed shim
  that `cast`s, mirroring `tests/test_bronze_landing.py:188-195`: `landed_max_seq` returns 0 with no
  row and N when it holds N, and the emitted statement contains **no** `FOR UPDATE` — a string
  assertion is legitimate here because the *absence* is the contract.
- `latest_landing` returns `None` for an unlanded save, and otherwise a mapping whose `source_files`
  is a decoded `list`, not a JSON string.
- The four gates green.

**Commit note.** *Two plain, non-locking warehouse reads for the ingest pre-flight.* Deliberately not
`next_ingest_seq` — that one is `FOR UPDATE` and must run inside the inserting transaction, and this
module's docstring records the measurement that proved the obvious belief about it wrong.

---

### Phase 4 — The command: argparse, resolution, the full `land()` skeleton, formatters

**Goal.** Ship everything a test can prove with no game, no save and no MySQL — **including `land()`'s
body**, so AC5/AC6/AC7 are genuinely provable against stubs rather than depending on Phase 5.

**Steps.**

1. Create `src/ootp_ai/ingest/__main__.py`: `main(argv) -> int` over a testable
   `land(settings, *, save_id=None, snapshot_root=None, new_look=False, from_snapshot=None) -> LandingResult`.
2. **Write the full `land()` skeleton now**: `connect_warehouse` → `ensure_tables` (capture the created
   tuple, do **not** print at call time) → `read_save(..., previous=None)` → `land_snapshot(..., ingest_seq=None)`
   → format and print. Phase 5 replaces only the `previous=None` and the `ingest_seq=None`.
3. `_parser()` with a required `land` subcommand carrying `--save-id`, `--new-look`, `--from-snapshot`,
   `--json`. `--new-look` and `--from-snapshot` are **mutually exclusive** at the argparse level: a
   snapshot re-land has no digest pre-flight to override.
4. Target resolution over `{ref.save_id: ref}` across the three `SaveRef` slots, skipping the `None`s a
   fresh clone will have. An unknown id raises `UnknownSave(ValueError)` — **a distinct type defined in
   this module**, caught in its own `except` returning **2**, because the established convention maps a
   bare `ValueError` to 1 and resolution failure is an argv/`.env` problem.
5. `LandingResult` carries **two** sequence fields with names that say where each came from:
   `snapshot_dir_seq: int` (allocated by `take_snapshot`, or read off the directory name on
   `--from-snapshot`) and `warehouse_max_seq: int`.
6. `format_result` and `format_json`, both pure. Line one of the human output is pinned so a test can
   parse the triple. **No absolute path on stdout**; a `ConfigError` on stderr may name the offending
   path, because a misconfiguration message that does not is not actionable. `--json` carries the
   triple, per-table row counts, per-file residual bytes, `parse_seconds`, `verdict`, and — per
   Decision 4 — the two sequence numbers whenever they diverge. Per-table digests stay out.
7. The **nine-exception tuple**, caught by name: `ConfigError` → 2, `UnknownSave` → 2; `SaveFormatError`,
   `SnapshotExists`, `SnapshotCorrupt`, `SnapshotDateMismatch`, `UndecodedRecords`, `SaveUnchanged`,
   `IngestRunExists`, `ConcurrentLandingError`, `LoadError` → 1 with `f"{type(error).__name__}: {error}"`.
8. Build offline `Settings` from a `tmp_path`-backed mapping **in the shape of `tests/test_config.py:24-36`'s
   `_env`** — it mkdirs the two directories `_required_directory` (`config.py:169-173`) insists exist.
   Add `OOTP_TRUTH_LEAGUE`/`OOTP_PROBE_LEAGUE` for the multi-save cases and omit both for the fresh-clone
   case AC3 requires.

**Acceptance** — AC2, AC3, AC4, AC5, AC6 (command half), AC7 and AC9. **AC1 landed in Phase 2 and AC8
lands in Phase 7**, so this phase turns seven of the nine offline criteria green, not all nine.

- **AC2:** `_parser().parse_args(["land"]).command == "land"`; the four flags parse; each of
  `--sim-date`, `--snapshot-root`, `--ingest-seq`, `--force` raises `SystemExit`;
  `with pytest.raises(SystemExit) as exc: main([])` then `assert exc.value.code == 2` (argparse
  **raises**; "returns 2" would never fire); `main(["land", "--from-snapshot", "x", "--new-look"])`
  exits 2 from the mutually-exclusive group.
- **AC3:** an unmatched `--save-id` returns 2 and stderr names every configured `save_id`; absent
  `--save-id` resolves to `settings.managed`; a filesystem path passed as `--save-id` is rejected; a
  `Settings` whose `truth_save` and `probe_save` are `None` still resolves the managed league.
- **AC4:** `format_result(...)` and `format_json(...)` each carry the `save_id`, the `sim_date` as
  `YYYY-MM-DD`, the `ingest_seq` and the per-table row counts, and match **none** of
  `from test_no_leaks import PATTERNS` — imported, not restated. `json.loads(format_json(...))` yields
  exactly the documented key set.
- **AC5:** a parametrised test walks the whole exception tuple and asserts each yields its documented
  code rather than a traceback, so adding a tenth without handling it fails loudly. `IngestRunExists`
  and `ConcurrentLandingError` produce **provably distinct** messages.
- **AC6 (command half):** `monkeypatch.setattr(ootp_ai.ingest.read, "read_save", recorder)` — **one
  patch, on the source module attribute**, with a recorder that wraps and delegates. Drive `land(...)`
  with `land_snapshot` stubbed and assert exactly one recorded call. Plus a module-identity assertion
  on the **modules**, not the functions: `assert ootp_ai.ingest.__main__.read is ootp_ai.ingest.read`,
  so a future `from … import read_save` refactor reds the test instead of silencing it.
- **AC7:** one shared call-order log proves `ensure_tables` is called exactly once, at an index
  **before** `read_save`. Assert ordering with the single log, not with two counters.
- **AC9:** `uv run pytest -m "not gamedata"` green with no new skips; the four gates green. No new
  pytest marker — `--strict-markers` makes a second one a hard collection error.

**Commit note.** *The ingest command's surface and its full land() skeleton.* A required subcommand,
resolution by configured save name, the 0/1/2 convention with a distinct `UnknownSave`, a
nine-member refusal tuple caught by name, and two path-free output formats — the human one pinned on
line one so a test can parse the triple, and `--json` giving `incremental-loading` a stable contract
instead of a print format to grep.

---

### Phase 5 — Wire the real path: pre-flight, reconciliation, verify, landing

**Goal.** The command actually lands; refuses on unchanged bytes *before anything is copied*; and lands
automatically on changed bytes at an unchanged sim date — ADR 0021's motivating case, flowing without a
flag. Proved against the **probe only**.

**Steps.**

1. Replace Phase 4's two placeholders: `latest_landing(connection, save_id=<resolved>)` → a
   `PriorLanding` → `read_save(..., previous=prior)`; and
   `seq = max(reading.snapshot_dir_seq, landed_max_seq(...) + 1)` passed **explicitly** to
   `land_snapshot`.
2. `--new-look` bypasses the pre-flight by passing `previous=None`.
3. Call `verify_snapshot(reading.parsed.run.snapshot.path)` from `land()` — **outside** `read_save`,
   because it reads the snapshot *copy*, not the game (Decision 5). Time the real call and record it.
4. On the refusal path, emit the machine-readable envelope on stdout when `--json` is set —
   `{"verdict": "unchanged", "save_id": …, "sim_date": …, "ingest_seq": <existing>}` — with the
   exception name still on stderr and the exit still 1 (Decision 6).
5. Name the landed dates on the refusal message, reusing `reports/resolve.landed_sim_dates`.
6. Emit the dual-allocator line only when the two numbers differ, and carry both into `--json`
   whenever they do (Decision 4).

**Acceptance** — and note which entry point each criterion uses, because `main()` returns only an exit
code while the cleanup needs the run object.

- **AC10** (via `main()`): monkeypatch `load_settings` **in the command module** to return
  `replace(settings, snapshot_root=tmp_path)`, then `main(["land", "--save-id", <probe>])` returns
  **0** and the triple parses out of `capsys` stdout line one. Cleanup reconstructs the run from the
  parsed triple via a local `_purge_triple(connection, save_id, sim_date, ingest_seq)` helper.
- **AC11** (via `land()` → `LandingResult.run`): `read_ingest_run(...)` returns a row at exactly the
  triple returned; its `table_row_counts` equal `run.row_counts`; `bronze_player` holds exactly that
  many rows for the triple.
- **AC12** (via `main()`): a second invocation against an unchanged save returns non-zero, names the
  existing triple, the landed dates and `--new-look`, and the directory count under `tmp_path` is
  **identical before and after** — which is what proves the refusal fired before 52.4 MiB was copied.
- **AC13** (via `land()`): with a `PriorLanding` whose one sha256 differs, `land` proceeds with no flag
  and `read_ingest_run` finds both sequences.
- **AC14** (via `land()`): `--new-look` lands identical bytes at `previous + 1`, and `table_digest` over
  every declared table for the **first** triple is identical before and after.
- The `--json` refusal envelope: an offline test asserts `json.loads(stdout)["verdict"] == "unchanged"`
  with a non-zero exit.
- **AC6 (fixture half):** the same single `ootp_ai.ingest.read.read_save` patch, driving `landed_probe`,
  records one call.
- The dual-allocator line is asserted offline in both directions against a fake cursor.
- **AC16/AC17 regression** as in Phase 2, plus `uv run pytest -m gamedata tests/test_cross_mode_format.py`
  — proving the mode line **reports and did not become a refusal**.

**Commit note.** *The ingest command lands for real.* `ensure_tables` on every run before the copy; a
digest pre-flight that refuses only on unchanged bytes; changed bytes at an unchanged sim date landing
the next sequence automatically with no flag; and a sequence reconciled as `max(filesystem, warehouse+1)`,
which equals the filesystem number in both in-step pairs measured 2026-08-30 and neither collides nor
refuses in the one live drift case.

---

### Phase 6 — `--from-snapshot`: the correction workflow, without re-reading the game

**Goal.** Re-land an existing snapshot at the next free sequence without touching the tree ADR 0001
protects — the correction `docs/decisions/0021-bronze-landing-is-append-only.md:57-59` names, which no
entry point can perform today.

**Steps.** Reuse `dump_parse`'s existing composition — `ingest.py:300` is literally
`_serialize(parse_snapshot(read_manifest(path)))`, so this needs no new parsing code. Read the directory's
own sequence off its name, reconcile it the same way, and state the relationship every time. Report the
save mode as **not recorded** rather than guessed: a snapshot carries no `challenge.dat`.

**Acceptance.**

- **AC15** (gamedata, probe): land a probe snapshot into `tmp_path`, then
  `main(["land", "--from-snapshot", str(snapshot_dir)])` — the game directory's manifest is **unchanged**
  across the invocation (via `test_read_only.manifest` / `differences`), a new `ingest_run` row appears,
  and stdout states explicitly whether the landed `ingest_seq` matches the directory's number.
  `purge_snapshot` cleans up both landings in `finally`.
- A nonexistent or manifest-less directory produces `SnapshotCorrupt: …` on stderr and exit 1, not a
  traceback — proved offline against a `tmp_path`.
- No absolute path in the `--from-snapshot` output, asserted against the imported `PATTERNS`.
- The four gates green; `uv run pytest -m gamedata tests/test_ingest_command.py` green.

**Commit note.** *`--from-snapshot` re-lands an existing snapshot without re-reading the game.* The
sequence relationship to the directory's own number is stated every time, matching or diverging, so
silence never reads as agreement. This path also passes an explicit sequence, so like the normal path it
forfeits `load.py:232-250`'s per-attempt re-allocation.

---

### Phase 7 — Retire the documented gap, record the measurements, hand over the USER-RUN criteria

**Goal.** Every sentence in the repo describing this gap stops being true, `reports/resolve.py`'s advice
starts being true, and the numbers are on the record with dates and labels. **Last** among the code
phases because the invocation string, flag names, exit codes and output format are only stable once
Phases 4–6 ship — and `incremental-loading` will write its procedure against all four.

**Steps.** Delete `README.md:128-134`'s blockquote in full; add the invocation to the setup fence before
the `reports render` line, plus one sentence noting the first run creates the eight declared tables and
that `ensure_tables` does **not** repair a drifted one. Point `reports/resolve.py`'s `_nothing_landed_message`
at the literal invocation string. The string is **duplicated by necessity** — the anti-drift device is
AC8, which reads the constant from the command module and asserts the literal appears in both files; do
**not** import the constant into `resolve.py`. Add the status-verb boundary as a dated amendment to
[`incremental-loading`](../incremental-loading/FEATURE_REQUEST.md). Correct `tests/test_read_only.py:186`'s
stale "46 MB" to the measured 52.4 MiB. Pass CLAUDE.md's Status paragraph and `src/ootp_ai/` map entry
through `/update-docs` rather than hand-editing.

**Acceptance.**

- **AC8:** a test asserts `README.md` contains the literal invocation string (read from the command
  module's own constant) and does **not** contain `There is no ingest command`; and that
  `src/ootp_ai/reports/resolve.py` contains that same literal.
- `git diff --stat docs/warehouse-catalog.md docs/warehouse-catalog.json src/ootp_ai/contracts/tables.toml`
  is **empty**.
- `git diff tests/test_read_only.py` shows no change inside `:303-317` across the entire change.
- `uv run pytest` (both markers) green end to end; the four gates green.
- The Index row and the artifact's Status blockquote agree, and `/update-docs` reports no remaining drift.
- **AC18 and AC19 are written out as operator instructions with their prerequisites and marked USER-RUN
  in the acceptance ledger — recorded when the operator runs them, never asserted by an agent.**

**Commit note.** *Retire the documented gap the command just closed, and record what it cost.*

## 4. Testing & verification

**One new module, split by what it needs.** `tests/test_ingest_command.py` carries an offline half that
runs in CI and a `-m gamedata` half targeting the **probe only** (SD-20). Every test in it is authored on
the **main thread** — `tests/` is in the write-capable builder's repo-level deny set
(`.claude/agents/data-engineer.md:154,157`), exactly as `first-sight` handled it. Only the declared
`gamedata` marker may be used.

**The import spelling, which the scope gets wrong for this repo.** AC1 writes
`from tests.test_read_only import WRITERS`. That does not resolve: verified, there is **no `conftest.py`
anywhere** and **no `tests/__init__.py`**; pytest's prepend mode puts `tests/` itself on `sys.path`. The
house form is bare — `import test_no_leaks as guard` (`tests/test_leak_guard_scope.py:34`),
`import test_doc_links as guard` (`tests/test_doc_link_contract.py:23`). Write
`from test_read_only import WRITERS` and `from test_no_leaks import PATTERNS`. If ruff's isort classifies
the bare module as third-party, add it to `known-first-party` rather than a `noqa`.

**The anti-vacuous rule — this one is load-bearing.** `_settings()` skips on `ConfigError`,
`warehouse_or_skip` skips when MySQL is unreachable, and `save_or_skip` skips per missing save. pytest
reports a **fully-skipped `-m gamedata` run as green with exit 0.** So every gamedata gate must be run
with `-rs`, the phase handoff must record the collected/passed/skipped counts, and **a gate with zero
passed gamedata tests is not a checkpoint** — the phase stops and the run is handed to the operator.

**Per-phase selectors.**

| Phase | Selector |
|---|---|
| 1 | `-m "not gamedata"`, then `-m gamedata tests/test_snapshot_semantics.py tests/test_provenance.py` |
| 2 | `tests/test_read_only.py tests/test_ingest_command.py` offline; then `-m gamedata tests/test_read_only.py` (the 2m35s one) and the full consumer set `tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py tests/test_parser_vs_export.py` |
| 3 | `-m "not gamedata" tests/test_bronze_landing.py tests/test_ingest_command.py tests/test_db_identifiers.py` |
| 4 | `-m "not gamedata"` whole |
| 5 | `-m gamedata tests/test_ingest_command.py` plus the AC16/AC17 block and `tests/test_cross_mode_format.py` |
| 6 | the same, plus AC15 |
| 7 | `tests/test_doc_links.py tests/test_doc_link_contract.py tests/test_catalog.py tests/test_skill_references.py tests/test_repo_structure.py tests/test_no_leaks.py`, then `uv run pytest` (both markers) |

**How the criteria are verified rather than asserted.** Three of the scope's criteria were rewritten by
its own adversaries away from string scans, and this plan honours that. **AC6** is a monkeypatched
recording spy that wraps and delegates — one patch on `ootp_ai.ingest.read.read_save`, driven once from
`land()` and once from `landed_probe` — plus an identity assertion on the *modules*. **AC7** is a shared
call-order log. **AC12** asserts a directory count, which is what makes "the refusal fired before the
copy" observable rather than asserted.

## 5. Decisions

1. **The pre-flight's warehouse lookup is keyed on `save_id` alone** — the save's most recent landing —
   not on `(save_id, sim_date)`. It is the only shape satisfying both Goal 3 and Core's literal "prior
   landing as a plain argument": a date-keyed lookup needs the sim date, which is itself a game read, so
   it would force `read_sim_date` outside the bracket and falsify AC16 in letter. The equivalence is
   sound and now *guarded*: the sim date comes from `teams.dat`'s header, `teams.dat` is one of the five
   digested `SNAPSHOT_FILES`, so unchanged bytes imply an unchanged sim date — and Phase 2 asserts
   `SIM_DATE_SOURCE in SNAPSHOT_FILES` offline so the derivation cannot rot silently.
2. **Digest-before-copy, not copy-then-compare — and the panel's stated reason was wrong.** The merge
   claimed the digest wins "by roughly three orders of magnitude". Re-measured on this machine
   2026-08-30 over the landed snapshot's five files (54,938,202 bytes, warm cache, three runs): size
   survey **0.21 / 0.41 / 0.22 ms**; full SHA-256 **48.2 / 36.9 / 35.4 ms**; `shutil.copy2` of the same
   bytes **19.6 / 18.4 / 17.9 ms**. **The digest is ~2x more expensive than the copy it avoids**, and it
   cannot be otherwise — a digest reads 52.4 MB, a copy reads and writes it, so the ceiling on any such
   advantage is ~2x and it runs the wrong way. The merge appears to have transposed the size-survey
   figure onto the full-digest claim. The decision stands on the argument that survives measurement:
   **copy-then-compare burns a filesystem `ingest_seq` and leaves an unreclaimable 52.4 MiB directory
   under `var/snapshots` on every refusal**, and no retention policy exists to reclaim it.
3. **The size fast path settles the *changed* direction cheaply and cannot fire on the refusal path at
   all.** Measured 2026-08-30: of the managed league's five files only `players.dat` differs between the
   live save and its landing (32,078,633 live vs 32,070,091 landed) — 4 of 5 give no signal. And when
   the operator re-runs against a genuinely unchanged save, *every* size matches by definition, so the
   comparison always falls through to the full digest before it can refuse. **A refusal therefore costs
   ~40 ms and creates no directory** — trivial for an operator, but not "nothing", and the plan must not
   say "nothing".
4. **The command reconciles the two allocators as `seq = max(snapshot_dir_seq, landed_max_seq + 1)`,
   passed explicitly.** It never refuses and never collides. But `snapshot.py:16-19` states that a
   snapshot's directory path is *"the same three components, in the same order, as every bronze primary
   key"*, and in a divergent case the landed sequence is **not** the directory's number — so the snapshot
   backing a triple sits at a path that triple does not address, which is exactly what ADR 0021's
   snapshot-is-authoritative triage depends on. Accepted deliberately, on condition that the divergence
   is **recorded in the `--json` payload**, not only printed to stdout prose the operator may not save.
5. **`verify_snapshot` is called from `land()`, outside the shared function.** It reads the snapshot
   *copy*, not the game, so putting it inside a function whose docstring claims to be the game-read
   bracket muddies the claim AC16 rests on; and it would add a re-digest to every `landed_probe` call,
   including the timing harness and the Tier-B diff, on every gamedata run. Its cost is `inferred` from
   an equivalent-volume digest, **not** measured on `verify_snapshot` itself — Phase 5 times the real
   call and records it.
6. **`--json` carries a `verdict`, and the refusal path emits a JSON envelope too.** Two reviewers
   independently found that `verdict`'s only interesting value was unreachable: the unchanged case
   raises, so no `LandingResult` is built and `format_json` is never called. Rather than ship a field
   promising a discriminator the control flow forbids, the refusal path emits
   `{"verdict": "unchanged", …}` on stdout with the exception name still on stderr and exit still 1.
7. **`read_save` has no `ingest_seq` parameter, ever.** All three planning lenses reached this
   independently, and the failure it prevents surfaces somewhere else entirely: if the CLI's
   explicit-sequence policy travelled with the shared function, `landed_probe` would start colliding at
   seq 1 and the symptom would appear as `IngestRunExists` in unrelated grain tests.
8. **Two pure comparison functions, not one with a mode flag.** `SnapshotFile.sha256` is a mandatory
   `str`, so a single signature cannot express "size known, digest not computed". An implementer filling
   `""` would get a spurious mismatch on every file, the digest branch would never be reached, and **the
   pre-flight would never refuse** — the plan's own worst risk, arriving silently.
9. **`SaveReading.parsed` is non-optional; the unchanged case raises `SaveUnchanged`.** The merged draft
   superimposed two planners' incompatible control flows, keeping both `parsed: … | None` and a raising
   branch. Under the raising design `parsed` can never be `None`, so the Optional was dead API that
   nonetheless reds `mypy --strict` at `land_snapshot(parsed: ParsedSnapshot)` and at
   `reading.parsed.run.snapshot.path`.
10. **AC15 supersedes the scope's incidental sentence** that `--from-snapshot` is the only way
    `IngestRunExists` is reachable through the command. A binding acceptance criterion outranks a
    descriptive clause in a decision's prose; the refusal still reaches the operator by name (AC5) and is
    still genuinely reachable by losing a race. Recorded as a supersession so the scope's sentence is not
    later read as a defect.
11. **The nine refusal exceptions are caught in one explicit tuple, walked by a parametrised test.** They
    share no base class — `snapshot.py:100,113`, `ingest.py:148,220`, `ingest_run.py:91` and
    `parser/errors.py:25` derive from `Exception`; `load.py:142,146` derive from `RuntimeError`.
12. **The Challenge-mode line reports and never refuses.** `tests/test_parser_vs_export.py:130` lands the
    retained **standard-mode** save through the shared path on every gamedata run; a refusal would break
    the Tier-B export diff.
13. **`tests/test_extraction_cost.py:46`'s stale "~46 MB" is corrected only if the probe's files are
    re-measured** during the Phase 5 or 6 gamedata run. Correcting a number nobody re-measured on the save
    it describes is the same defect in the other direction.
14. **No measurement-only phase.** The numbers this plan's obligation named were measured while writing it
    and are carried as facts with dates and labels. Only the allocator table can drift between now and
    implementation, so Phase 1 re-runs exactly that query.

## 6. Risks & gotchas

1. **The naive composition is silently wrong, and it is the obvious one.** `take_snapshot` with
   `ingest_seq=None` auto-allocates and never raises, so `snapshot + parse + land` composed the obvious
   way does not surface ADR 0021's refusal — it lands a full duplicate, 52.4 MiB and ~301,000 rows, with
   nothing to reclaim either. *Mitigation:* the pre-flight runs before `take_snapshot`, and AC12 asserts
   the directory count is unchanged on the refusal path.
2. **A prior landing predating the dated 2026-08-16 `SNAPSHOT_FILES` widening names fewer than five
   files.** A comparison checking only the files `previous` names would report *unchanged* for a save
   whose `world.dat` was never digested. Any file in today's `SNAPSHOT_FILES` that `previous` does not
   name is **changed**, with its own offline test.
3. **Two allocators, one live instance of drift.** Re-measured 2026-08-30: `OOTP-AI` 2024-03-07 fs 1 /
   warehouse 1; `Test-Save-Challenge-Mode` 2024-03-18 fs 1 / warehouse 1; **`Test-Save-Standard-Mode`
   2024-03-18 fs 1 / no warehouse row** — its rows were purged by `landed_probe`'s `finally` while the
   directory survived. The opposite direction is one `rm -rf var/` away. `max(fs, warehouse+1)` handles
   both, but the resulting sequence **gap** remains and a later reader applying ADR 0021's "starting at
   1" can read it as a lost landing. Surfaced, not eliminated — hence Decision 4's `--json` requirement.
4. **An explicit `ingest_seq` weakens the deadlock retry, invisibly.** `land_snapshot` re-allocates per
   attempt, which only works on the `None` branch. The command therefore has weaker contention behaviour
   than the fixture it shares a path with. State it in the code as a trade rather than inheriting it.
5. **Conflating contention with a refusal.** `load.py:146-154` names this in terms. A shared
   `except (IngestRunExists, ConcurrentLandingError)` with one message passes a naive test and fails an
   operator.
6. **Re-pointing the fixture couples ~10 gamedata tests across four modules to one new function.** A
   defect in `read_save` reds all four at once. The fixture's loud-skip discipline must survive unchanged.
7. **AC11 must not get more expensive** — 2m35s, 30,703 files, ~6.4 GB hashed three times. No fourth leg,
   no MySQL, no change to the manifest-pass count.
8. **A docstring can red the write guard.** `_writes_in` strips only `#` comments, not docstrings. The
   hazard is live precisely because the honest thing to write in the new modules' docstrings is the thing
   that fails the build.
9. **`from X import y` binds a name.** Both call sites import the **module** and call `read.read_save(...)`,
   which is what makes the single patch on `ootp_ai.ingest.read.read_save` sufficient — patching
   `__main__.read_save` would raise `AttributeError`, or with `raising=False` would silently set an
   attribute nothing reads and record zero calls, so the test would pass for the wrong reason.
10. **A fully-skipped gamedata run exits 0.** See §4's anti-vacuous rule. Phases 2, 5 and 6 cannot be
    completed on a CI-shaped machine.
11. **`load_settings(mapping)` has a precondition.** `_required_directory` raises unless `OOTP_INSTALL` and
    `OOTP_SAVED_GAMES` name directories that **exist**. Use `tests/test_config.py:24-36`'s `_env` recipe.
12. **Absolute paths reaching tracked files.** State the precedent accurately: `reports render` prints
    whatever `output_root` resolves to, which `config.py` deliberately keeps **relative** by default. This
    command prints no path at all — a stronger form of the same rule, not a divergence.
13. **The managed league is the default target and there is no automated guard** (Scope Decision 6). The
    structural protection holds, so the realistic harm is a wasted snapshot and a landing under the wrong
    `save_id` — recoverable, and immediately visible in the printed **resolved** `save_id`. Every
    automated test targets the probe.
14. **Ingesting while OOTP is running is only partially guarded.** `_copy_one` digests each source before
    and after its own copy and `check_sim_dates` refuses a mixed snapshot, but neither catches a mid-write
    change *across* files at an unchanged sim date. Detection is out of scope on the ground the repo
    actually carries: `docs/data-access.md:85` records `flag_save_completed.dat` with **no read content at
    all**, and this repo forbids building on an `assumed` claim. (The `unconfirmed` write-lock note at
    `:226-227` is about the SQLite text-data file, not the save's `.dat` files — do not cite it for this.)
15. **Making landing one keystroke accelerates a cost nobody has bounded.** `bronze_name` re-lands 264,095
    rows per snapshot; no retention policy exists. Per-table row counts are the honest measurable; this
    plan does not fix the growth and must not appear to.
16. **The downstream contract is being pinned by this diff.** `incremental-loading` writes its procedure
    against whatever invocation string, flag names, exit codes and output format ship — which is why the
    line-one format and the `--json` field set are specified here rather than left to taste, and why the
    docs phase comes last.
17. **`ensure_tables` does not repair a drifted table** and nothing tells the operator when that bites.
    Accepted (Scope Decision 4), stated in the command's docstring and README's setup line, not fixed.
18. **Roughly half of core lands in `tests/`, which is in the builder's deny set.** Every test file is
    authored on the main thread; a spawned builder handed a spec targeting `tests/` must stop and report.
19. **`rg` is not on PATH on this machine.** Use `Select-String`. Several natural verification commands
    assume `rg` and will fail silently-looking.
20. **Do not rewrite path citations inside `requests/`** — not the `reviews/` handoffs and not this
    request's own artifacts. They are the record of what was believed when, and four now name
    `src/ootp_ai/ingest.py`, which is correct for the date they carry.

## 7. Files to touch (checklist)

- [ ] `src/ootp_ai/ingest.py` → **moved** to `src/ootp_ai/ingest/__init__.py`, byte-identical (Phase 1)
- [ ] `src/ootp_ai/ingest/read.py` — **new**: `read_save`, `PriorLanding`, `SaveReading`, `SaveUnchanged`,
      `reason_from_sizes`, `reason_from_digests` (Phase 2)
- [ ] `src/ootp_ai/ingest/__main__.py` — **new**: `main`, `land`, `_parser`, `UnknownSave`,
      `LandingResult`, `format_result`, `format_json`, the invocation-string constant (Phase 4)
- [ ] `src/ootp_ai/snapshot.py` — `read_sim_date` public + caller at `:185`; new `source_facts`; two
      `__all__` entries in sorted order (Phase 1)
- [ ] `src/ootp_ai/warehouse/ingest_run.py` — `latest_landing`, `landed_max_seq`, `__all__` sorted (Phase 3)
- [ ] `src/ootp_ai/reports/resolve.py` — `_nothing_landed_message` names the literal invocation (Phase 7)
- [ ] `tests/fixtures/warehouse.py` — `landed_probe` re-pointed at `:151`; module import at `:43-44`; one
      docstring sentence. **Main-thread authored** (Phase 2)
- [ ] `tests/test_read_only.py` — three legs re-pointed at `:254`, `:263`, `:268`; import at `:46`;
      docstring at `:237-242`; the stale "46 MB" at `:186`. **`WRITERS` byte-unchanged** (Phases 2, 7)
- [ ] `tests/test_ingest_command.py` — **new**, grown across Phases 2–7, **main-thread authored**
- [ ] `README.md` — blockquote at `:128-134` deleted; setup fence extended (Phase 7)
- [ ] `CLAUDE.md` — Status paragraph and the `src/ootp_ai/` map, judged through `/update-docs` (Phase 7)
- [ ] [`incremental-loading`](../incremental-loading/FEATURE_REQUEST.md) — dated boundary amendment (Phase 7)
- [ ] `.claude/agents/data-engineer-memory.md` — correct the bare path at `:202`, **append** a dated line
      rather than rewriting (Phase 1)
- [ ] `pyproject.toml` — **only if** ruff's isort reorders a bare cross-test import: add it to
      `known-first-party`. Do not touch `files`, `markers` or `strict`
- [ ] **Do not touch:** `src/ootp_ai/contracts/tables.toml`, `docs/warehouse-catalog.md` / `.json`,
      `ops/mysql-bootstrap.sql`, `.env.example`, `[project.scripts]` (absent, stays absent), every
      `requests/**/` citation, and every parser module

## 8. Conventions (bake these in)

- **The game is read-only** (ADR 0001). No code path writes a save, a roster import file, or automates
  the UI. `read_save` is the only function that opens anything under the game roots, and it only reads.
- **`snapshot.py` is the only module allowed to create a file.** Both new modules delegate every write to
  it, which is why `WRITERS` stays byte-unchanged — a stronger outcome than allowlisting.
- **Bronze is append-only** (ADR 0021). No `--force`, no upsert, no `DELETE`/`UPDATE` in
  `src/ootp_ai/warehouse/`. A correction is a new landing.
- **Resolve by name, never by path.** The target comes from the configured `SaveRef`s; `--save-id` selects
  among them; a filesystem path is rejected.
- **No absolute path in tracked output.** stdout carries none at all; stderr's `ConfigError` may name the
  offending path because it must to be actionable.
- **Label your epistemics.** Every number in this plan carries `measured` with a date, or `inferred` with
  what it was inferred from. The `verify_snapshot` cost is `inferred` until Phase 5 times the real call.
- **Agents commit only through `/commit`** — never `git commit` ad hoc, never `--amend`, never a push to
  `main`. The PR stays the operator's.
- **Subagents get read-only git**, and `tests/` is in the write-capable builder's deny set — every test
  file here is authored on the main thread.
- **USER-RUN means user-run.** AC18 and AC19 are recorded when the operator runs them. No agent may claim
  them.

## 9. Code-grounding verification

The panel's two adversaries and its meta-audit checked the merged draft's **83 cited references** against
the repo, and I re-verified the ones driving the largest rewrites. The trust ledger:

| Cited claim | Verdict |
|---|---|
| `SnapshotFile.sha256` optional enough for a size-only pass | **Corrected** — it is a mandatory `str` (`snapshot.py:121-127`); split into two pure functions (Decision 8) |
| `land_snapshot` accepts `ParsedSnapshot \| None` | **Corrected** — signature is non-optional (`load.py:195-201`); `SaveReading.parsed` made non-optional (Decision 9) |
| `from tests.test_read_only import WRITERS` resolves | **Corrected** — no `conftest.py` anywhere, no `tests/__init__.py`; bare import is the house form |
| `monkeypatch ootp_ai.ingest.__main__.read_save` | **Corrected** — no such attribute under module-import style; one patch on `ootp_ai.ingest.read.read_save` (§4) |
| `rg` available for the pre-move sweep | **Corrected** — not on PATH on this machine; use `Select-String` |
| Digest-before-copy wins "three orders of magnitude" | **Corrected** — re-measured; the digest costs ~2x the copy. Decision stands on a different argument (Decision 2) |
| Size fast path "confirmed" by a real save | **Qualified** — 1 of 5 files moved, and it cannot fire on the refusal path at all (Decision 3) |
| Phase 4's acceptance provable without Phase 5's work | **Corrected** — Phase 4 now writes the full `land()` skeleton |
| `--json verdict` reaches the consumer | **Corrected** — unreachable as drafted; refusal path now emits an envelope (Decision 6) |
| `data-access.md:226-227` covers the save write-lock | **Corrected** — that note is about the SQLite text-data file; `:85` is the right citation |
| Allocator table (3 pairs, 1 drift) | **Confirmed** — re-measured independently, unchanged |
| `ingest.py:300` is `parse_snapshot(read_manifest(path))` | **Confirmed** — `--from-snapshot` needs no new parsing code |
| `_describe(payload=None)` costs ~48 MB per ingest | **Confirmed** — and re-pointing AC11's legs off `ingest_save` makes them *cheaper* |
| `ensure_tables` has one caller; bootstrap creates no tables | **Confirmed** |

## References

- [`PROJECT_SCOPE.md`](PROJECT_SCOPE.md) · [`FEATURE_REQUEST.md`](FEATURE_REQUEST.md)
- Panel trail: [`reviews/plan-proposals.md`](reviews/plan-proposals.md) ·
  [`reviews/plan-adversarial.md`](reviews/plan-adversarial.md) ·
  [`reviews/scope-proposals.md`](reviews/scope-proposals.md) ·
  [`reviews/scope-adversarial.md`](reviews/scope-adversarial.md)
- [ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md) ·
  [ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md) ·
  [ADR 0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md) ·
  [ADR 0018](../../../docs/decisions/0018-retention-is-infrastructure.md) ·
  [ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md)
- [`docs/data-access.md`](../../../docs/data-access.md) · [`CLAUDE.md`](../../../CLAUDE.md) ·
  [`.claude/agents/data-engineer.md`](../../../.claude/agents/data-engineer.md)
- Downstream consumer: [`incremental-loading`](../incremental-loading/FEATURE_REQUEST.md)
