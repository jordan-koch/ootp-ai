> **Status:** implemented · created 2026-08-30 · decided · next: commit

# Project Scope — An ingest command: the pipeline has no way to be run

## Fit Verdict

**Clean** — in shape. The risk is concentrated in one operator-facing default and one
test-suite re-point, not in the size of the diff.

The pattern exists twice and names itself as such. `src/ootp_ai/reports/__main__.py:1-11`
records that entry points are deliberate and sets the shape — resolve settings, resolve the
target explicitly, act, print the triple — with a thin `main(argv) -> int` over a testable
`render(settings, ...)` and exit codes 0/1/2 at `:39-59`. `src/ootp_ai/catalog/__main__.py`
followed it once already. This is a third instance of an established shape, not a new one.

**No dataset contract re-opens.** `PARSED_FILES` (`ingest.py:66`) is unchanged, no new field
is read, and the eight declared tables in `src/ootp_ai/contracts/tables.toml` keep their
grain, keys, coverage and update semantics. ADR 0005's *does this change when the league is
simulated?* question does not fire, because the command produces no artifact of its own; it
drives the parser→bronze path already on the "yes" side. `docs/warehouse-catalog.md` must be
byte-identical afterwards.

**No parser obligation fires.** `parser/header.py` refuses a non-25 header on the way in, and
again per file in `ingest._describe`; `check_decoded` and `check_sim_dates`
(`ingest.py:235-278`) refuse a moved record layout and a mixed snapshot. The command's only
parser-facing job is to surface those refusals as an exit code instead of a traceback. No
fixed-offset seek is introduced; no epistemic label moves.

**No ADR is contradicted — but only because of how Decision 1 was resolved.** The scoping
panel recommended a default that refused a second landing keyed on `(save_id, sim_date)`.
Both adversaries independently blocked it, and the block is correct: ADR 0021 §Context:21-27
addresses that exact design **by name and rejects it** — *"The obvious fix — key on
`(save_id, sim_date)` and refuse a re-land — is **worse**, because it blocks a legitimate and
frequent operation."* §Decision part 2 states the positive rule the other way. The chosen
default (digest pre-flight) needs **no ADR amendment**: an unchanged-bytes re-run is a no-op,
not a "new look", while changed bytes at an unchanged sim date land the next sequence
automatically — which is precisely ADR 0021's motivating case. See Decisions §1.

**Two things keep it from being trivial, and both are settled here rather than deferred.**

1. **The write-allowlist entry the request budgets for is not needed.** `_writes_in()`
   (`tests/test_read_only.py:348-358`) scans a module's *own source text* for `.mkdir(`,
   `.write_text(`, `.write_bytes(`, `.touch(`, `os.makedirs` and write-mode `open(` — it is
   not a capability model. A module delegating every file creation to `snapshot.py:205`
   trips nothing. `WRITERS` (`:303-317`) stays **byte-unchanged**, which is a stronger
   outcome than allowlisting and refuses to widen ADR 0001's allowlist for zero benefit. The
   request's Scope Signals are wrong here, in the safe direction.
2. **The gap is wider than the request states.** `ensure_tables` (`warehouse/load.py:169`)
   has exactly one caller in the repo — `tests/fixtures/warehouse.py:93` — and
   `ops/mysql-bootstrap.sql` creates three databases, a user and grants but **no tables**
   (verified: its only `CREATE`s are three `CREATE DATABASE` and one `CREATE USER`). The
   test suite therefore does *two* pieces of production work, not one, and the request's own
   observable signal cannot hold unless the command creates the schema.

**No duplication with anything in flight.** `reports/__main__.py` and `catalog/__main__.py`
both only *read* a landing. `incremental-loading` claims the two-date proof, the
cross-snapshot read path and the written operator procedure, and explicitly does not claim
the vehicle. `open-front-office` Phase B puts an `ensure_views()` beside `ensure_tables` and
edits the bootstrap script — noted in Decisions §4 so the two do not collide.

**Prior art, not fresh discovery.** `requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:144-162`
already recorded the `ensure_tables` and `verify_snapshot` gaps. This scope confirms and
prices them; it did not find them first.

## Problem

Nothing outside the test suite can put data in the warehouse. `ingest_save`
(`src/ootp_ai/ingest.py:436`) and `land_snapshot` (`src/ootp_ai/warehouse/load.py:195`) are
library functions with no `__main__` behind them; `src/ootp_ai/` ships exactly two entry
points and both only *read* a landing that already exists. The de facto ingestion path is
`tests/fixtures/warehouse.py:133-157`, which composes `parse_snapshot(take_snapshot(...))` by
hand and lands it — so the snapshots now on disk and the landings behind them were produced
by running `pytest`, and `README.md:128-134` currently documents that as the setup path.

Two costs, and the second is the one that matters. The operator has no supported way to
refresh the club. And a test fixture that is load-bearing has stopped being free to change —
anyone refactoring `tests/fixtures/warehouse.py` for a test's convenience is editing the
ingestion path with nothing to tell them so.

The capability was withheld deliberately rather than forgotten, which is why this is a
feature and not a bug.

## Goals / Non-Goals

**Goals:**

1. One documented command — `uv run python -m ootp_ai.ingest land` — takes a configured save
   from disk to a landed bronze snapshot and prints the `(save_id, sim_date, ingest_seq)`
   triple it created, the same three facts `reports render` prints, so a landing and a later
   render can be tied together in a `gm/decisions/` record.
2. A fresh clone runs without `pytest`: `uv sync` → `.env` → `mysql < ops/mysql-bootstrap.sql`
   → one ingest command → `reports render` produces a roster page. This requires the command
   to call `ensure_tables`.
3. **Every game-touching line the command executes sits inside one shared function that
   `tests/test_read_only.py`'s AC11 legs call.** The argparse, settings, warehouse-connection
   and landing halves are outside that function and touch no game file. This is the accurate
   form of the claim; see Risks for why the loose form ("the manifest diff brackets the
   operator's path") is not true and must not be written.
4. The append-only re-run behaviour is settled deliberately rather than by composition
   accident, because whatever ships becomes the contract `incremental-loading` writes its
   repeatable procedure against.
5. Target resolution is by configured save name, never a filesystem path: `--save-id` matches
   `SaveRef.save_id` across `settings.managed` / `truth_save` / `probe_save`
   (`config.py:99-108`), defaulting to the managed league exactly as `reports render` and
   `catalog` do.
6. No machine-specific absolute path reaches **stdout**, because that output is the artifact
   most likely to be pasted into a tracked, public `gm/decisions/` record.
7. `tests/test_read_only.py`'s `WRITERS` allowlist is left byte-unchanged.
8. The library's refusals surface by name and are softened none: `IngestRunExists`,
   `ConcurrentLandingError`, `SnapshotExists`, `SnapshotCorrupt`, `SnapshotDateMismatch`,
   `SaveFormatError`, `UndecodedRecords`, `LoadError` each reach the operator as
   `type(error).__name__: message` with a non-zero exit.
9. The documented gap is retired: `README.md:128-134`'s "There is no ingest command"
   blockquote deleted, the command named in the setup fence, and
   `reports/resolve.py:180-182` — which already tells the operator to *"run the ingest before
   rendering"* — made true.

**Non-Goals:**

- **Rendering.** `reports render` is the render entry point and stays so (ADR 0016). At most
  README shows the two lines together; there is no `--then-render` flag.
- **The sim-forward-and-re-land procedure, the two-date proof, and any cross-snapshot read or
  diff.** All claimed by `incremental-loading`. This request builds the vehicle; that one
  drives it.
- **A `status` verb.** Neither request builds it now. This one owns the disk-and-refusal half
  (what save, what sim date, is it already landed); `incremental-loading` owns the
  warehouse-inventory half. This boundary is written into **both** requests — see Decisions §5.
- **Any change to landing semantics.** `ingest_seq` allocation, the `IngestRunExists`
  refusal, the primary key that actually prevents an overwrite, and the bounded deadlock
  retry (`warehouse/load.py:232-250`) are settled by ADR 0021 and exposed here, not
  renegotiated. No `--force`, no `--overwrite`, no upsert, no `DELETE`/`UPDATE` added to
  `src/ootp_ai/warehouse/`.
- **A ninth table, a new column, or any edit to `src/ootp_ai/contracts/tables.toml`.**
  `docs/warehouse-catalog.md` must be byte-identical after this work.
- **Any parser change.** Every byte this moves is already read by walkers under test.
- **Schema migration or drift repair.** `ensure_tables` creates and never replaces, and
  deliberately does not repair a table whose shape has drifted (`load.py:176-189`). That
  limitation is accepted and stated, not fixed here — see Decisions §4.
- **Extending AC11's manifest diff to include landing, or adding the command as a fourth
  bracketed leg.** `tests/test_read_only.py:240-242` refuses the first in terms — pulling a
  warehouse dependency into ADR 0001's guard would let an unrelated MySQL outage silence the
  one test the project cannot afford to lose. The second would add another full manifest pass
  to a test measured at **2m35s over 30,703 files and ~6.4 GB hashed three times**.
- **A `--snapshot-root`, `--ingest-seq` or `--saved-games` CLI flag.** The first two exist
  only to serve tests and are served by library keyword arguments instead. The third would
  let an operator aim the pipeline at an unfenced location; `catalog/__main__.py:118-134`
  records what happened to the project's only other operator-typed write root.
- **A new `.env` key.** Everything resolves from the three `SaveRef`s that already exist.
- **A log file, or any file the new module creates itself.** The new module opens no file for
  writing and creates no directory — that is what keeps `WRITERS` byte-unchanged, and it is a
  requirement, not an accident.
- **A `[project.scripts]` console entry point.** `uv run python -m ootp_ai.<package>` is the
  established invocation and `pyproject.toml` declares no `[project.scripts]`.
- **Landing more than one save per invocation.** Progress output is also out — but see A17 in
  Risks: the non-goal is restated against measured end-to-end wall clock, not against the
  ~2.2 s parse alone.
- **A retention, pruning or purge policy, and any purge helper in `src/`.** `purge_snapshot`
  stays in `tests/fixtures/warehouse.py:99`; `warehouse/load.py:69-74` names a convenience
  purge as exactly how append-only stops being true.
- **Anything that writes to a save, automates the game, reads an in-game screenshot as truth,
  or schedules/watches/daemonises a run** (ADR 0001, ADR 0002).
- **Building on `flag_save_completed.dat` or any other unwalked `.dat`.** Whether the command
  can tell OOTP is running is a research task producing a labelled finding; folding it in
  would smuggle a spike into a wiring change.
- **A GM-facing surface.** This is an operator/umpire command; ADR 0016 keeps the GM on
  reports, and landing a save costs no GM action.

## Acceptance Criteria

Rewritten from the panel's draft where the adversaries showed a criterion was untestable,
unrunnable, or proved the wrong thing. Every rewrite is recorded in Decisions §7.

**Offline (CI):**

1. `uv run pytest tests/test_read_only.py` is green and `WRITERS` is unchanged — asserted, not
   eyeballed: the new `tests/test_ingest_command.py` does `from tests.test_read_only import
   WRITERS` and `assert WRITERS == {"snapshot.py", "reports/__main__.py",
   "catalog/__main__.py"}`, with a comment saying the new module is deliberately absent
   because it creates no file. Both `test_only_allowlisted_modules_can_write_a_file` and
   `test_the_pipeline_contains_no_destructive_filesystem_call` pass with the new module
   present in `SRC.rglob("*.py")`.
2. The argparse surface is pinned: `_parser().parse_args(["land"]).command == "land"`;
   `--save-id`, `--new-look`, `--from-snapshot` and `--json` exist; **no** `--sim-date`,
   `--snapshot-root`, `--ingest-seq` or `--force` option exists (the in-game date is read from
   `teams.dat`'s header, never supplied). `with pytest.raises(SystemExit) as exc: main([])`
   then `assert exc.value.code == 2`, because the subcommand is required and argparse
   *raises* rather than returns.
3. Target resolution refuses an unconfigured id **by name**. With `Settings` built through
   `load_settings(mapping)` (the injection point at `config.py:111` exists for exactly this),
   a `save_id` matching none of `managed`/`truth_save`/`probe_save` returns exit code **2**
   and an error string naming every configured `save_id`; absent `--save-id` resolves to
   `settings.managed`; a filesystem path passed as `--save-id` is rejected rather than
   resolved.
4. The result formatter emits no absolute path. Given a synthetic `IngestRun` and a snapshot
   root, the printed success block carries the `save_id`, the `sim_date` as `YYYY-MM-DD`, the
   `ingest_seq` and the per-table row counts, and matches **none** of
   `tests/test_no_leaks.py::PATTERNS` (`:37-41`) — imported, not restated.
   `uv run pytest tests/test_no_leaks.py` stays green.
5. The refusal surface is proved without a warehouse. With `land_snapshot` monkeypatched to
   raise `IngestRunExists`, `main(["land"])` returns 1 and the message names the triple; with
   it raising `ConcurrentLandingError`, the message is **distinct** from the `IngestRunExists`
   one (`warehouse/load.py:146-154` warns that conflating them sends the operator looking for
   a landing that never happened); with `load_settings` raising `ConfigError`,
   `main(["land"])` returns 2.
6. Both callers route through the shared function **behaviourally, not by string scan**:
   monkeypatch the shared function to record its arguments, then assert that the command's
   `land(...)` and `tests/fixtures/warehouse.py::landed_probe` each produce a recorded call.
   (The panel's draft proposed a source-text scan; `tree-seam-for-remaining-guards` exists
   because that class of guard cannot fail. See Decisions §7.)
7. `ensure_tables` is called exactly once and **before** `take_snapshot`, proved by a spy on a
   `land` invocation whose later stages are stubbed.
8. `README.md` contains the literal invocation string the command ships with and does **not**
   contain `There is no ingest command`; `src/ootp_ai/reports/resolve.py` contains that same
   literal invocation string, so `_nothing_landed_message` names a command that exists.
   `uv run pytest tests/test_doc_links.py tests/test_doc_link_contract.py tests/test_catalog.py
   tests/test_skill_references.py` is green and `docs/warehouse-catalog.md` is unchanged.
9. `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` (strict, over `src`
   and `tests`) are green over the promoted `ingest` package — `ingest.__all__`
   (`ingest.py:50-62`) unchanged, and every one of the ten existing `from ootp_ai.ingest
   import ...` sites importing without edit.

**Gamedata (probe only — SD-20; never the managed league in an automated test):**

10. **The command's own success path returns 0.** Monkeypatch `load_settings` *in the command
    module* to return `replace(settings, snapshot_root=tmp_path)` — the idiom already used at
    `tests/test_read_only.py:193` — call `main(["land", "--save-id", <probe>])`, assert it
    returns **0**, and parse the triple out of `capsys` stdout. This keeps `--snapshot-root`
    off the CLI while making the exit-0 path a pytest assertion rather than a human's.
11. One landing through the operator's own path really lands: `read_ingest_run(...)` returns a
    row at exactly the triple the function *returned*, its `table_row_counts` equal the
    returned `run.row_counts`, and `bronze_player` holds exactly that many rows for the
    triple. `purge_snapshot` runs in `finally`.
12. **The chosen re-run default holds.** A second invocation against a save whose bytes are
    unchanged since the last landing at that sim date returns non-zero, names the existing
    triple and the `--new-look` flag, and creates **no** new `ingest_run` row and **no** new
    snapshot directory — proving the refusal fires *before* ~52 MB is copied.
13. **Changed bytes at an unchanged sim date land automatically**, with no flag — ADR 0021's
    motivating case. Simulated by landing, then mutating a byte in a *copied* fixture save (or
    by monkeypatching the pre-flight's digest source), never by editing a real save.
    `read_ingest_run` finds both sequences.
14. **`--new-look` lands identical bytes deliberately** at `previous + 1`, and
    `warehouse.load.table_digest` over every declared table for the **first** triple is
    identical before and after — the same assertion shape as
    `tests/test_snapshot_semantics.py::test_two_sequences_of_one_sim_date_both_persist`.
15. **`--from-snapshot <dir>` re-lands an existing snapshot** without re-reading the game:
    the game directory's manifest is unchanged across the invocation, a new `ingest_run` row
    appears, and the output states explicitly whether the landed `ingest_seq` still matches
    the snapshot directory's number.
16. **ADR 0001's proof brackets every game read.** `uv run pytest -m gamedata
    tests/test_read_only.py::test_a_full_run_touches_nothing_under_the_game_directories` is
    green with its legs calling the **same shared function** the command calls, in the same
    probe → truth → managed order; the test performs four manifest passes when
    `OOTP_TRUTH_LEAGUE` is configured and three otherwise, and adds no MySQL dependency.
    `test_the_manifest_is_not_vacuous` stays green alongside it.
17. **Nothing regressed in the real `landed_probe` consumer set** — `uv run pytest -m gamedata
    tests/test_snapshot_semantics.py tests/test_grain_contracts.py tests/test_extraction_cost.py
    tests/test_parser_vs_export.py` is green (the panel's draft named `test_bronze_landing.py`,
    which does not import `landed_probe`; the two riskiest real consumers are the timing
    harness and the Tier-B export diff). Explicitly: `test_parser_vs_export.py`'s
    `which="truth_save"` path still works, and `landed_probe` still lands with
    `ingest_seq=None`, keeping all three of its test-only powers unchanged.

**USER-RUN (the acceptance panel may not claim these):**

18. On a machine whose warehouse holds no `bronze_*` tables: `uv sync` → `mysql -u root -p <
    ops/mysql-bootstrap.sql` → `uv run python -m ootp_ai.ingest land --save-id <target>` →
    `uv run python -m ootp_ai.reports render --save-id <target>` produces a `roster.md` under
    the output root, with `pytest` never invoked. **Prerequisite:** if run against the probe,
    `OOTP_PROBE_LEAGUE` must be configured; otherwise run it against `settings.managed`, which
    is safe because the command only reads the save.
19. The printed ingest output, pasted into a scratch `.md` file inside the repo, leaves
    `uv run pytest tests/test_no_leaks.py` green.

## Scope (tiered)

**Core (must):**

- **One command, one verb**: `uv run python -m ootp_ai.ingest land`, which pre-flights,
  snapshots, parses and lands in a single act. The library keeps its deliberate three-way
  split (`ingest.py:10-12`) for callers; the CLI does not mirror it. Structured as a thin
  `main(argv) -> int` over a testable `land(settings, *, save_id=None, snapshot_root=None,
  ...)` a test can call without a subprocess.
- **`src/ootp_ai/ingest.py` promoted to a package** — `ingest/__init__.py` (today's module
  moved verbatim) plus `ingest/__main__.py`.
- **One shared game-touching function**, composing `take_snapshot` + `parse_snapshot` — the
  fixture's existing, cheaper shape, **not** via `ingest_save`. It performs *every* game read
  the command makes: the sim-date header read, the pre-flight digests, and the copy. It takes
  the prior landing's `source_files` as a plain argument (or `None`), so the warehouse lookup
  that produces it stays outside the function and outside AC11's diff. It takes
  `snapshot_root` as a library keyword argument; **`ingest_seq` is never its parameter** — the
  sequence decision belongs to whoever calls `land_snapshot`. Its docstring names its three
  callers and states that changing it changes what the operator's command does.
- **`snapshot._read_sim_date` promoted to a public `read_sim_date`** and added to
  `snapshot.__all__`, with a docstring saying why: it is the only cheap answer to *what date
  would this land at?* before ~52 MB is copied.
- **The digest pre-flight** (Decisions §1): resolve the sim date, look up the latest
  `ingest_run` for `(save_id, sim_date)`, and compare the save's files against its
  `source_files`. Cheap fast path first — `source_files` stores `size` as well as `sha256`
  (`warehouse/ingest_run.py:180-191`), so a size mismatch settles "changed" without digesting.
  Unchanged bytes refuse, naming the existing triple, the landed dates and `--new-look`;
  changed bytes land the next sequence and say why; `--new-look` lands regardless.
- **Target resolution by configured save name, never a path.** Build `{ref.save_id: ref}` over
  the three `SaveRef` slots (skipping the `None`s a fresh clone and CI will have). Unknown id
  → exit **2**, naming what *is* configured. No `saves.enumerate_saves` sweep of the
  saved-games root.
- **Fail-fast ordering, stated because it is not the natural order**: settings → target →
  warehouse connection → `ensure_tables` → pre-flight → snapshot + parse → land. MySQL down
  must fail before ~52 MB is copied; a snapshot with no landing behind it is an orphan.
- **`ensure_tables(connection)` on every run, before the copy**, printing any table it created.
- **Sequence policy stated rather than defaulted**: the operator's snapshot is durable, so the
  filesystem-allocated `ingest_seq` is passed **explicitly** to `land_snapshot`
  (`warehouse/load.py:203-217`). The cost is real and carried into the plan: the deadlock
  retry at `load.py:233-250` re-allocates per attempt, which only helps on the `None` branch,
  so an explicit sequence means a lost race surfaces as a refusal rather than a recovery.
- **The stdout contract**: the *resolved* `save_id` (printed, not assumed — `.env` and the
  warehouse can disagree), the `sim_date`, the `ingest_seq`, and the per-table row counts from
  the returned `IngestRun`. **No absolute path.** The rule is **stdout-only**; a `ConfigError`
  on stderr may name the offending path, because a misconfiguration message that doesn't is
  not actionable. Both halves stated so neither is later "fixed" by mistake.
- **The error surface, caught by name** — `ConfigError` → 2; the eight refusal exceptions → 1
  with `type(error).__name__: message`. They share no base class, so a tuple that misses one
  turns a refusal into a traceback. The version guard needs no new code.
- **`--from-snapshot <dir>`** (Decisions §3): re-land an existing snapshot via
  `snapshot.read_manifest` without touching the game. The output states explicitly, every
  time, whether the landed `ingest_seq` still matches the snapshot directory's number.
- **`tests/fixtures/warehouse.py::landed_probe` re-pointed** onto the shared function, keeping
  its three test-only powers exactly where they are — the `TemporaryDirectory` snapshot root,
  `ingest_seq=None` at the *landing* call, and `purge_snapshot` in `finally`. None becomes CLI
  surface; `purge_snapshot` never moves into `src/`. Its docstring gains a sentence saying the
  landing path is now shared with the operator's command.
- **`tests/test_read_only.py`'s three AC11 legs re-pointed** onto the same shared function,
  docstring updated to say the guard now brackets every game read the command makes and why
  landing stays outside it. No fourth leg, no MySQL, no change to the manifest-pass count.
- **`tests/test_ingest_command.py`** — an offline half in CI and a `gamedata` half against the
  **probe only**.
- **Docs trued up in the same change**: `README.md:128-134`'s blockquote deleted, the command
  added to the setup fence, a line noting the first run creates the declared tables,
  `reports/resolve.py:180-182` corrected, the boundary sentence added to
  `incremental-loading/FEATURE_REQUEST.md` as a dated amendment, and CLAUDE.md's Status
  paragraph and `src/ootp_ai/` map entry passed through `/update-docs`.

**Folded in (cheap wins):**

- **`--json`**, trimmed: the triple, per-table row counts, per-file residual bytes and
  `parse_seconds` — all already on the returned `IngestRun`, **zero extra queries** — under the
  same no-absolute-path rule. Gives `incremental-loading` a stable contract instead of a print
  format to grep. (Per-table digests are *not* folded in; see Above & Beyond.)
- **`snapshot.verify_snapshot(snapshot.path)` after the copy.** It has zero callers in `src/`
  while its own docstring (`snapshot.py:254-260`) says it is *"Called after landing a
  snapshot."* That sentence is currently false. ADR 0021's snapshot-is-authoritative triage is
  only sound if the snapshot was proved intact at landing time. **The plan measures the added
  seconds and records the number.**
- **Print the save's mode** from `saves.is_challenge_mode` — `saves.py:11-15` says the check is
  *"cheap enough to run on every ingest"* and there has never been an ingest to run it on. It
  **reports, never refuses**: `tests/test_cross_mode_format.py:119` asserts the retained truth
  save is standard-mode by design, and it is parsed on every gamedata run. Landing the truth
  save is sanctioned and already routine.
- **Name the landed dates on the refusal path**, reusing `reports/resolve.landed_sim_dates` —
  making the append-only refusal actionable the way `_nothing_landed_message` does for the
  render path.
- **Print both sequence allocators when they disagree** — but the display value comes from a
  plain `SELECT COALESCE(MAX(ingest_seq), 0) ... WHERE save_id=%s AND sim_date=%s`, reusing the
  pre-flight's own query. `warehouse.ingest_run.next_ingest_seq` is **deliberately not reused**:
  its docstring requires it be called inside the transaction that inserts the row, and this
  repo has already got that function's locking semantics wrong once.

**Gated — resolved:** see Decisions. All six were disposed by the operator on 2026-08-30.

## Above & Beyond

- **Digest pre-flight (refuse only on unchanged bytes)** — *core.* Promoted from the panel's
  gated tier by Decision §1: it is the only option honouring both ADR 0021 clauses.
- **`--from-snapshot <dir>`** — *core.* Promoted by Decision §3.
- **Sim-date pre-flight before the copy** — *core.* The mechanism that makes any re-run default
  reachable at all.
- **`--json` machine-readable output** — *cheap fold*, trimmed to zero-extra-query fields.
- **`verify_snapshot` after the copy** — *cheap fold*, with a measurement obligation.
- **Save-mode line from `saves.is_challenge_mode`** — *cheap fold*, report-only.
- **Landed dates in the refusal message** — *cheap fold.*
- **Dual-allocator disagreement line** — *cheap fold*, via the pre-flight's own query.
- **Per-table `table_digest` values in the `--json` block** — *deferred.* Not cheap:
  `table_digest` (`warehouse/load.py:540-572`) fetches every column of every row ordered by the
  declared key and JSON-serialises each one — ~301,000 rows for one landing, 264,095 of them
  `bronze_name`. That is a second full read of everything the landing just wrote, on the
  operator's most frequent command. `table_digest` already exists for whoever wants them later.
- **An `ingest status` verb** — *deferred by boundary*, not by cost. See Decisions §5.
- **`--no-land` / `--dry-run`** — *dropped.* On the request's own Not-now list, and its
  strongest argument (letting AC11 bracket the operator's path without MySQL) is already
  delivered by the shared function, which AC11 calls directly.
- **Challenge-mode *enforcement* via `saves.assert_challenge_mode`** — *dropped.* The reporting
  half is folded in; refusing would break ingestion of the retained standard-mode truth save,
  which `test_cross_mode_format.py:119` pins. A prior decision already settled this
  (`first-sight/reviews/handoff-phase-4.md:55-56`); this is not a new observation.
- **`--snapshot-root` override** — *dropped.* Its only justification is serving the re-pointed
  fixture, and a library keyword argument serves that without becoming operator surface. It
  would also be the project's second operator-typed write root; `catalog/__main__.py:118-134`
  records what happened to the first.
- **Free-disk pre-flight** — *dropped.* No recorded incident, no measured near-miss; the failure
  it prevents is a visible orphan directory. If it ever happens, it is a bugfix request with a
  repro.
- **`--save all` across configured saves** — *dropped.* On the request's Not-now list; cheap to
  add later against a settled single-save contract.
- **A spike on whether OOTP is currently running** — *dropped.* `docs/data-access.md` §1 labels
  the content of `flag_save_completed.dat` `assumed`, and this repo's label table forbids
  building on an assumed claim. A separate request, not a line item here. *(The panel's
  adversary flagged that this label should be re-verified at the cited location before the plan
  leans on it; the drop stands on the second ground — a research task does not belong in a
  wiring change.)*
- **Per-landing warehouse growth in bytes** — *dropped.* Core already prints per-table row
  counts, which is the measurable this command can honestly produce; a disk-bytes figure needs
  its own `information_schema` query and belongs to the retention argument ADR 0018 and ADR
  0021 both defer.
- **A distinct exit code (3) for the append-only refusal** — *dropped.* `--json` gives
  `incremental-loading` that discriminator without breaking the 0/1/2 convention both existing
  entry points set, and `type(error).__name__` is already on stderr.
- **A `--yes-managed` confirmation** — *dropped.* See Decisions §6.

## Risks & Unknowns

1. **The re-run default is the expensive decision, and the naive composition gets it wrong
   silently.** `take_snapshot` with `ingest_seq=None` allocates the next free *filesystem*
   sequence and never raises (`snapshot.py:189-201`); `SnapshotExists` fires only when a
   sequence is named explicitly. So `land = snapshot + parse + land` composed the obvious way
   does **not** surface ADR 0021's refusal — it lands a full duplicate, ~52 MB on disk and
   ~301,000 rows, with no retention policy to reclaim either. Shipping documentation that
   claims a protection the code does not provide is the specific failure to avoid.
2. **The chosen pre-flight costs a second read of the save, or a wasted copy — the plan must
   pick and say which.** Digest-before-copy reads the save twice (digest, then
   `shutil.copy2`); copy-then-compare spends the ~52 MB copy and a filesystem sequence before
   refusing. This scope's preference is **digest-before-copy**, because the point of the
   refusal is to cost the operator nothing — mitigated by the size fast path, since a changed
   save almost always changes file sizes. The plan measures both and records the numbers.
3. **`--new-look` is required for a case ADR 0021 names explicitly.** *"A parser fix re-lands
   the same snapshot at the next sequence"* — same bytes, same date, deliberate. Under the
   digest pre-flight that path refuses without the flag. This is the honest cost of Decision
   §1 and must be documented at the flag, not discovered.
4. **Two independent sequence allocators, and one live instance of drift — `measured`
   2026-08-30, correcting the panel.** `snapshot.next_ingest_seq` counts directories under the
   gitignored, disposable `var/snapshots`; `warehouse.ingest_run.next_ingest_seq` reads
   `MAX(ingest_seq)` from MySQL. The panel asserted the two were out of step *by construction*,
   because every landing came from a `TemporaryDirectory` snapshot that no longer exists. **That
   is wrong for two of the three pairs.** Measured:

   | pair | filesystem | warehouse | |
   |---|---|---|---|
   | `OOTP-AI` 2024-03-07 | seq 1 | `MAX(ingest_seq)` 1 | in step |
   | `Test-Save-Challenge-Mode` 2024-03-18 | seq 1 | `MAX(ingest_seq)` 1 | in step |
   | `Test-Save-Standard-Mode` 2024-03-18 | seq 1 | **no row** | **drift** |

   So the operator's first `land` against the managed league is consistent, and the hazard is
   narrower than the panel claimed but real. The one live instance is the **truth save**: its
   warehouse rows were purged by `landed_probe`'s `finally` while its snapshot directory
   survived, so a first landing there takes filesystem seq **2** with no seq 1 — and a later
   reader applying ADR 0021's *"monotonic integer … starting at 1"* reads the gap as a lost
   landing. The opposite direction remains possible and is not currently instantiated: delete
   `var/` (documented as disposable) and the first run claims seq 1 and hits `IngestRunExists`
   on a landing the operator never made. **The plan must decide how the command reconciles** —
   allocate `max(filesystem, warehouse) + 1` and print the reasoning line, or keep the
   filesystem sequence and print "filesystem allocated N, warehouse holds M". Re-run
   `SELECT save_id, sim_date, MAX(ingest_seq) FROM ingest_run GROUP BY 1, 2;` against
   `var/snapshots/` if the warehouse has moved since.
5. **An explicit `ingest_seq` weakens the deadlock retry, invisibly.** `land_snapshot` retries
   on 1213/1205 and re-allocates the sequence each time, which only works on the
   `ingest_seq=None` branch. The command therefore has weaker contention behaviour than the
   fixture it replaces. Unlikely in a single-operator setup; stated so it is a trade rather
   than an inheritance.
6. **Conflating contention with a refusal.** `load.py:146-154` names this failure in terms: an
   operator told "already landed" for a `ConcurrentLandingError` goes looking for a landing
   that never happened.
7. **Re-pointing the fixture can silently change its sequence policy, and the failure surfaces
   somewhere else.** The fixture lands with `ingest_seq=None` because a temp directory always
   allocates 1 on the filesystem side. If the CLI's explicit-sequence policy travels with the
   shared function, `landed_probe` starts colliding at seq 1 and the failure appears as
   `IngestRunExists` in unrelated grain tests. AC17's explicit sub-clause exists for this. The
   re-point also couples ~10 gamedata tests across four modules to one new function, so a
   defect in it reds all of them at once; the fixture's loud-skip discipline
   (`:82-96`, *"Never a vacuous pass"*) must survive unchanged.
8. **The `ingest_save` composition would have added ~50 MB of reads to a timing harness.**
   `_describe(..., payload=None)` re-reads each file whole for 25 bytes of header — its own
   docstring measures *"~48 MB of avoidable I/O per ingest"*. Core specifies
   `take_snapshot + parse_snapshot` instead. `ingest_save` is not orphaned by this —
   `tests/test_provenance.py` still calls it, and AC11's legs keep whatever read surface they
   need by construction.
9. **Absolute paths reaching tracked files.** `saved_games.dat` embeds a user-profile path per
   save; `gm/` is tracked and public; `tests/test_no_leaks.py:37-41` scans `.md` for drive
   letters, home directories and email addresses. Note the precedent claim must be stated
   accurately: `reports render` prints whatever `output_root` resolves to, which `config.py`
   deliberately keeps **relative** by default. This command prints no path at all, which is a
   stronger form of the same rule, not a divergence from a path-printing sibling.
10. **AC11 is the most expensive test in the repo and must not get more expensive** — 2m35s
    over 30,703 files, ~6.4 GB hashed three times, measured 2026-08-16.
11. **The managed league is the default target and there is no automated guard against it.**
    The structural protection holds (nothing in `src/` opens a game file for writing;
    `reject_inside_game_roots` fences the write roots; AC11 proves it by diff), so the
    realistic harm is a wasted snapshot and a landing under the wrong `save_id` — recoverable
    and immediately visible in the printed triple. Stated so the silence is a decision.
12. **Package promotion is a 502-line move git may record as delete+add.** All ten
    `from ootp_ai.ingest import ...` sites survive unchanged, but line-numbered prose does not.
    The single live reference to correct is `.claude/agents/data-engineer-memory.md:202`; no
    markdown link targets the file, so `tests/test_doc_links.py` is unaffected. **Historical
    `requests/**/reviews/` handoffs must NOT be rewritten** — they are the record of what was
    believed when. Find every reference *before* the move.
13. **Running a plain module under `-m` is why promotion is the right answer.** `python -m
    ootp_ai.ingest` on a *module* executes it as `__main__` while its package-qualified imports
    re-import it as `ootp_ai.ingest` — two `ParsedSnapshot` classes and a silent `isinstance`
    failure across the boundary with `warehouse/load.py:90`. Label: `inferred` from Python
    import semantics; not reproduced here.
14. **Ingesting while OOTP is running is only partially guarded.** `_copy_one` digests each
    source before and after the copy, and `check_sim_dates` refuses a mixed snapshot. Neither
    catches a mid-write change *across* files at an unchanged sim date. A CLI makes this
    reachable outside a deliberate `-m gamedata` run — exactly when the operator is least
    likely to have quit the game first.
15. **Making landing one keystroke accelerates a cost nobody has bounded.** `bronze_name`
    re-lands 264,095 rows per snapshot; no retention policy exists; ADR 0018 leaves the
    per-date growth rate `unconfirmed`.
16. **The downstream contract is being pinned by this diff.** `incremental-loading` will write
    its operator procedure against whatever invocation string, flag names, exit codes and
    output format ship. All four are cheap now and expensive after. That, not the size of the
    diff, is why the request correctly refuses a stage skip.
17. **`ensure_tables` does not repair a drifted table** (`load.py:176-189`) and nothing tells
    the operator when that bites. Accepted as a known limitation (Decisions §4), not fixed.
18. **Roughly half of core lands in `tests/`, which is in the write-capable builder's deny
    set** (`.claude/agents/data-engineer.md`). The plan must author every test on the main
    thread, as `first-sight` did.
19. **Two figures in the repo are stale and one is corrected here.** The snapshot is
    **~52 MB** (the panel measured 52.4 MiB for the managed league's landed snapshot,
    2026-08-30) — every "~46 MB" in the request and in `tests/test_read_only.py:187`'s
    "46 MB directory per run" comment is understated by ~14%. The panel's `parse_seconds`
    figure is also not the whole story; see A17 in the panel trail.

## Affected Area & Pointers

**Target component:** `src/ootp_ai/` — one new entry point over existing ingest and warehouse
code, plus `tests/` and `README.md`. **No parser change and no new landed data.** No dataset is
created, so no `datasets/manifest.json` name is taken and no builder is written.

Read in this order:

| # | File | Why |
|---|---|---|
| 1 | `src/ootp_ai/reports/__main__.py` | **Read first.** `:1-11` the rule that entry points are deliberate; `:36-59` `main(argv) -> int` and the 0/1/2 convention; `:62-80` the testable `render(settings, *, save_id=None, ...)`; `:125-151` argparse with a required subcommand |
| 2 | `src/ootp_ai/catalog/__main__.py` | The second instance, and two lessons: `:1-11` argues why it took *no* subcommand and why it is allowlisted by package-relative path; `:118-134` the record of the project's only operator-typed write root |
| 3 | `src/ootp_ai/ingest.py` | `:1-28` the three-way split's rationale (`:10-12`) and the no-path rule (`:25-27`); `:66` `PARSED_FILES`; `:235-278` the refusals to surface; `:281-300` `dump_parse` (the `read_manifest` → `parse_snapshot` composition `--from-snapshot` reuses); `:436-460` `ingest_save`; `:481-501` `_describe` and its measured ~48 MB warning |
| 4 | `src/ootp_ai/snapshot.py` | `:50-63` `__all__` (where `read_sim_date` must be added); `:146-164` filesystem `next_ingest_seq`; `:167-216` `take_snapshot` — **the auto-allocation that makes naive composition silently duplicate** — and `:205`'s `mkdir`, which is why no `WRITERS` entry is needed; `:219-251` `read_manifest`; `:254-269` `verify_snapshot` (zero `src/` callers); `:285-293` `_read_sim_date`; `:296-319` `_copy_one` |
| 5 | `src/ootp_ai/warehouse/load.py` | `:60-75` the deadlock retry and why no `DELETE`/`UPDATE` exists; `:159-189` `landed_tables` / `ensure_tables` (**one caller in the repo**); `:195-250` `land_snapshot`, `:203-217`'s explicit-vs-`None` sequence argument, `:232-250`'s retry; `:287-317` the in-transaction row-count read-back; `:540-572` `table_digest` and its cost |
| 6 | `src/ootp_ai/warehouse/ingest_run.py` | `:137-153` the *warehouse* allocator and its must-be-in-the-transaction contract; `:156-198` `ingest_run_values` — **`source_files` carries per-file `size` and `sha256`**, the material the pre-flight needs; `:201-235` `claim_ingest_run`; `:238-268` `read_ingest_run` |
| 7 | `src/ootp_ai/config.py` | `:71-84` `SaveRef` and `save_id = to_save_id(league)` — the property making the disk-side and warehouse-side vocabularies the same string; `:99-108` `Settings`; `:111-148` `load_settings(env)`, the mapping injection point offline tests need; `:186-215` `reject_inside_game_roots` |
| 8 | `tests/test_read_only.py` | `:1-33` the measured AC11 cost; `:182-193` the `replace(settings, snapshot_root=...)` idiom; `:222-269` the three legs and `:240-242`'s explicit refusal to include landing; `:294-317` `WRITERS` and its comment; `:337-372` `_writes_in` — **the source-text scan that makes a new allowlist entry unnecessary** |
| 9 | `tests/fixtures/warehouse.py` | `:1-27` why the delete lives in tests and why landings allocate from the warehouse; `:59-96` the loud-skip discipline and the lone `ensure_tables` call at `:93`; `:99-130` `purge_snapshot`; `:133-157` `landed_probe` — it composes `parse_snapshot(take_snapshot(...))` at `:151` and does **not** call `ingest_save` |
| 10 | The real `landed_probe` consumers | `tests/test_parser_vs_export.py:56,130` (Tier-B, lands the **standard-mode** save), `tests/test_extraction_cost.py:39,75` (a **timing harness**, `DRIFT_FACTOR = 10.0`), `tests/test_grain_contracts.py:65,421`, `tests/test_snapshot_semantics.py:65,437,597` |
| 11 | `src/ootp_ai/reports/resolve.py` | `:78-94` `landed_sim_dates`; `:168-187` `_nothing_landed_message` — the refusal-message pattern to copy, and the line telling the operator to *"run the ingest before rendering"* that this change must make true |
| 12 | `ops/mysql-bootstrap.sql` | Verify for yourself: three `CREATE DATABASE`, one `CREATE USER`, database-scoped grants only. **No tables, and no rights to create a throwaway schema** — this is what makes `ensure_tables` load-bearing and what makes an automated empty-schema test unrunnable |
| 13 | `docs/decisions/0021-bronze-landing-is-append-only.md` | The semantics the command surfaces. §Context:21-27 rejects the date-keyed refusal **by name**; §Decision parts 1–3; §Consequences' 264,095-rows figure and *no retention policy exists* |
| 14 | ADRs `0001`, `0006`, `0016`, `0018` | The constraints binding the output contract, target resolution and the growth argument. `0005` should be read only to confirm its question does not open |
| 15 | `README.md:103-141` | The setup section: `:128-134` the blockquote to delete, `:117-118` the fence to extend |
| 16 | `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md` | The downstream consumer. Its Desired Outcome `:54-65` (especially `:61`) claims the warehouse-inventory half; its Explicitly-out `:90-104` confirms it does not claim the vehicle. **The boundary amendment lands here** |
| 17 | `requests/feature-requests/first-sight/reviews/handoff-phase-8b.md:144-162` | Prior art: the `ensure_tables` and `verify_snapshot` gaps were already recorded here |
| 18 | `tests/test_no_leaks.py:31-41` | `PATTERNS` is the exact list an offline output test should **import** rather than restate |

**Before writing the plan, run one query:** `SELECT save_id, sim_date, MAX(ingest_seq) FROM
ingest_run GROUP BY 1, 2;` against the dev schema, and compare it to what is on disk under
`var/snapshots/`. See Risks §4.

## Decisions

**1. The re-run default: refuse only when the source bytes are unchanged.** *(Digest
pre-flight — the panel's Option B.)* The panel recommended refusing by `(save_id, sim_date)`,
and both adversaries independently blocked it as an ADR-level divergence. They were right, and
I verified it: ADR 0021 §Context:21-27 names that exact design and calls it *"worse"*, and
§Decision part 2 states the positive rule the other way. The request's own sentence says both
halves — the triple it means in *"re-landing an already-landed triple still refuses loudly"* is
`(save_id, sim_date, ingest_seq)`, which is part 1 and already automatic. The digest pre-flight
is the only option honouring both clauses, and so needs **no ADR amendment**: an
unchanged-bytes re-run is a no-op rather than a "new look", while changed bytes at an unchanged
sim date land the next sequence automatically — ADR 0021's motivating free-agent case, flowing
without a flag. The override is **`--new-look`**, matching the ADR's own vocabulary. Two costs
accepted openly: a second read of the save (Risks §2, mitigated by the size fast path) and the
parser-fix re-land needing the flag (Risks §3).

**2. Invocation: `uv run python -m ootp_ai.ingest land`,** promoting `src/ootp_ai/ingest.py`
to a package. Naming it `warehouse` would name only the last third of what the command does,
and the first two thirds are the half ADR 0001 cares about; a top-level `__main__` would
introduce a third invocation convention the request declines. Promotion is import-transparent
and avoids the double-import hazard (Risks §13). SC-08's counter-argument was surfaced and
heard — `catalog/__main__.py:3-5` argues against a subcommand for a one-verb command — and the
subcommand ships anyway, keeping symmetry with `reports render` and leaving room for verbs
`incremental-loading` may add.

**3. `--from-snapshot <dir>` ships in v1.** It is the correction workflow ADR 0021 names, no
entry point can perform it today, and without it a correction means re-copying ~52 MB from the
one tree ADR 0001 protects. It is also the only way the `IngestRunExists` refusal is reachable
*through the command* rather than only in tests. Its sub-decision is settled rather than left
open: the landed `ingest_seq` may diverge from the snapshot directory's number, and the output
**states so explicitly every time it does**.

**4. `ensure_tables` runs implicitly on every `land`,** printing any table it created. It
creates and never replaces, so the blast radius is bounded to "the eight declared tables
exist", and implicit is what makes the fresh-clone criterion hold in one command rather than
two. Two things stated rather than assumed: it deliberately does **not** repair a drifted table,
which is accepted here as a limitation (Risks §17); and when `open-front-office` Phase B lands
an `ensure_views()` beside it, whether the implicit rule extends is **that** request's decision,
not one this scope makes in advance.

**5. No `status` verb — and the boundary is written down in both requests.** This request owns
the disk-and-refusal half: what save, what sim date, is it already landed — delivered by the
landed-dates fold on the refusal path, which is the whole benefit at a fraction of the cost.
`incremental-loading` owns the warehouse-inventory half (*"what does this universe hold, and at
which dates"*, its `:61`). Leaving it unassigned is how the capability is lost to mutual
assumption, so the mechanism is named: the boundary sentence goes into this scope's non-goals
**and** into `incremental-loading/FEATURE_REQUEST.md` as a dated amendment, as part of this
work's doc-truth item.

**6. The default target stays the managed league, with no confirmation prompt.** Symmetry with
`reports render` and `catalog` is worth more than the protection would be, because the
protection is close to zero: the command only ever reads the save, `reject_inside_game_roots`
fences the write roots, and AC11 proves by manifest diff over 30,703 files that the pipeline
touches nothing under either game root. Two mitigations stay in core: the command prints the
*resolved* `save_id` rather than assuming the operator knows which universe `.env` names, and
every automated test targets the probe (SD-20).

**7. Adversary fixes folded in without a separate gate**, because each corrected a factual or
testability defect rather than posing a judgment call. Verified directly before folding:
AC12's empty-schema precondition is **unrunnable** — grants are database-scoped to three named
databases with no rights to create a throwaway schema, so the only way to meet it is to `DROP`
the declared tables from the dev schema, destroying the first landed ingest via a `DROP`
written into tests days after ADR 0021 §3 banned one in `src/` (split into AC7 + AC18); the
`landed_probe` consumer list was wrong (`test_bronze_landing.py` does not import it; the
timing harness and the Tier-B export diff do); `_describe(..., payload=None)` really does
re-read each file whole. Also folded: the pre-flight's game reads move **inside** the shared
bracketed function and `_read_sim_date` is promoted to public API; the shared function drops
its `ingest_seq` parameter; AC6 becomes a behavioural assertion rather than a fourth
string-pinned source scan (`tree-seam-for-remaining-guards` exists because that class of guard
cannot fail); the dual-allocator line uses a plain `SELECT` rather than `next_ingest_seq`;
per-table digests leave the cheap-fold tier; `pytest.raises(SystemExit)` replaces "returns 2";
the unknown-`--save-id` exit code is **2**, on the convention *argv or `.env` is wrong → 2*;
the no-absolute-path rule is **stdout-only** with stderr's `ConfigError` exempt; and the
"reports prints full paths" claim is corrected — it prints whatever `output_root` resolves to,
which stays relative by default.

## Panel Trail

Raw, unfiltered panel output: [`reviews/scope-proposals.md`](reviews/scope-proposals.md) (the
three scopers' proposals) and
[`reviews/scope-adversarial.md`](reviews/scope-adversarial.md) (the convergence map and all 44
adversary findings — 4 blockers, 12 majors — including the ones this scope judged overstated).
Panel health: 3/3 scopers, 2/2 adversaries, no degraded lenses.
