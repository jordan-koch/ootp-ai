# Planning Panel — Raw Planner Proposals + the Recovered Merge

Run 2026-08-16 · workflow `wf_567f4abc-f44` · 3/3 planners, 2/2 adversaries, 1/1 meta-audit.
**The structured merge FAILED** (API error: response exceeded the 64,000 output-token
maximum) and the panel recovered via fallback. `degraded_lenses = [merge:fallback]`.

Consequences, recorded so a later reader is not misled: `convergence_map` and
`gated_decisions` came back EMPTY, and `plan_draft.phases` is a 36-entry
planner-prefixed UNION rather than a converged sequence. The free-text best-effort
synthesis DID succeed and carries the real converged 14-phase plan; it is reproduced
in full below and is what IMPLEMENTATION_PLAN.md was written from.

Absolute machine paths have been rewritten repo-relative (finding F01 — the raw
output carried drive-letter paths that fail `tests/test_no_leaks.py`).

---

## The recovered free-text merge (the converged plan)

# IMPLEMENTATION PLAN — `first-sight`
**Upstream artifact:** `requests/feature-requests/first-sight/PROJECT_SCOPE.md` (decided; 21 acceptance criteria, 21 Core scope items, 9 folded-in cheap wins, 11 disposed Decisions).
**Track:** feature. **Stage:** 3 of 4. **Audience:** a cold agent with no access to the author.
**Status of the code being planned against:** nothing exists. `src/ootp_ai/__init__.py` is 7 lines — a docstring reading *"Phase 0. No pipeline code yet; the .dat parser is feature request #1"* and `__version__ = "0.1.0"` at line 7. `pyproject.toml:9` is `dependencies = []`. The `ootp` MySQL schema exists with zero tables. Every module below is created from nothing.

---

## 0. How to read this plan

Three things bind every phase and are not restated inside each one.

**The game is read-only, absolutely.** ADR 0001. No code path opens anything under `$OOTP_INSTALL` or `$OOTP_SAVED_GAMES` for writing, produces a roster-import file, or automates the game UI. `.claude/agents/data-engineer.md:55-58` states the consequence in full: the managed league runs in Challenge Mode, whose saves carry an integrity hash, **one write destroys the league irreversibly, and there is no backup upstream**. Every handle is opened `"rb"`; `:60-61` adds that a snapshot under `var/` is preferred over the live save, which is why Phase 4 exists at all. This is the one unrecoverable failure in the project, so it gets a test (AC11) *and* an independent human check (AC21) rather than a promise.

**The parser walks sequentially and never seeks to a fixed offset.** `.claude/agents/data-engineer.md:69-74` calls seeking code "a blocker, not a style note", with the measured evidence: the same player's ratings block sat 43 bytes from one anchor in one save and 107 in another, with byte-identical internal layout. A fixed-offset read passes on day-0 data — which is exactly what both saves on disk are — and silently returns the wrong field for every differently-shaped record afterwards. This plan makes the ban **structural** (a cursor with no `seek` method) *and* **mechanical** (an AST scan, AC3), because a rule enforced only by review is enforced only until the next agent.

**Ground truth is `players.csv`, never a display.** `.claude/agents/data-engineer.md:75-78`: displayed ratings are scale-converted (20–80 player page, 1–100 reports, ~1–1000 storage) *and* possibly scout-filtered, so matching a screenshot value to a byte identifies the wrong field and raises nothing. `:79-81`: a field mapping with no validating test is `unconfirmed` and must say so. This slice lands **no ratings at all**, which defuses the trap rather than solving it — but the labelling discipline still governs every field that does land.

Two more repo rules the cold implementer will trip over if they are not front-loaded:

- **Commits go through `/commit` only.** Never `git commit` ad hoc, never `--amend`, never a push to `main`, never a force-push. Each phase below ends at a `/commit` gate, on a green local run of `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`. `/commit` runs the doc gate and asks before writing. The PR stays the operator's.
- **Subagents get read-only git**, and `tests/` is the **first entry** in the data-engineer's repo-level deny set (`.claude/agents/data-engineer.md:150`), followed by `.github/` (`:151`), `ops/` (`:152`), `.claude/` (`:153`), `CLAUDE.md` (`:154`), `docs/data-access.md` (`:155`) and `docs/decisions/` (`:156`). `:164-166` instructs the subagent to **stop and report** rather than build when spec targets fall inside that set. This is not advisory: hand a whole phase spec to the builder and you get an Escalation and zero tests.

**Ownership split, applied to every phase without exception.**
The implementation subagent's declared target paths are `src/ootp_ai/**` (including the tracked TOML declarations that ship inside the package) and `requests/feature-requests/first-sight/reviews/**`, and nothing else. The **main thread** authors everything under `tests/`, plus `pyproject.toml`, `.env.example`, `ops/mysql-bootstrap.sql`, `docs/**`, `gm/**`, `README.md` and `CLAUDE.md`. Parser findings that belong in `docs/data-access.md` travel back as a `## docs-delta` section in the handoff, carrying a *proposed* epistemic label, and the main thread routes them through `/update-docs` (`.claude/agents/data-engineer.md:239-249`).

---

## 1. Architecture map

### 1.1 What exists today, measured

`src/ootp_ai/` — one file, `__init__.py`, 241 bytes. `transform/`, `build/`, `datasets/` do not exist and this feature **must not create them** (scope Non-Goals; CLAUDE.md forbids speculative directories; note `.gitignore:61` already carries an `!datasets/**` carve-out for a directory that does not exist — leave it alone). `tests/` holds four structural guards — `test_no_leaks.py`, `test_repo_structure.py`, `test_agent_contract.py`, `test_doc_links.py` — and no parser test. Baseline: `uv run pytest -m "not gamedata"` is green.

### 1.2 Target package shape, layered so each layer only depends on layers an earlier phase proved

```
src/ootp_ai/
  config.py            resolve everything from .env; the only module that touches os.environ
  saves.py             enumerate saves; Challenge Mode pre-flight
  snapshot.py          copy the in-scope files + SHA-256 manifest; all parsing runs off this
  ingest.py            the ingest-run record shape (populated across phases 4/7/8)
  parser/
    primitives.py      forward-only Cursor over bytes — NO seek, NO absolute read
    header.py          shared header + version guard; UnsupportedSaveVersion
    errors.py
    teams.py  names.py  players.py  rosters.py  saved_games.py
  contracts/
    tables.toml        grain sentence + key list + coverage, per table   (TRACKED)
    field_map.toml     per field: name, type, source .dat, walker, category,
                       epistemic label, validator tier                    (TRACKED)
    loader.py          stdlib tomllib reader; resolves via importlib.resources
    policy.py          is_renderable(field) — the single serving gate
  warehouse/
    sql.py             quote_ident() — backticks every identifier
    ddl.py             emits CREATE TABLE + PRIMARY KEY *from* contracts/
    load.py            bronze landing, 1:1 with parser output
    ingest_run.py
  validate/
    export_diff.py     parser-vs-export differential, per-field by name
  reports/__main__.py  roster.py  standings.py
  catalog/__main__.py  generate.py
```

### 1.3 The five seams that carry the design weight

**(a) The cursor is the fixed-offset ban.** `parser/primitives.py` exposes a `Cursor` over an in-memory `bytes` (`Path.read_bytes()`; `players.dat` is 32 MB, trivially affordable) with advancing-only readers: `u8/u16/u32/i32/f64`, `string()` (u32-LE length prefix, raw ASCII, **no terminator** — `docs/data-access.md:195`), `date()` (u8 day, u8 month, u16 year — `:196`), `color()` (u32 ARGB — `:197`), `skip(n)`, `remaining()`. It exposes **no** absolute-positioning method and no `seek`. Critically, **`header.py` uses the same cursor** — reading 1 byte, then 4, then a u32 sequentially rather than indexing offsets 1/5/25. That single decision is what lets AC3's static scan cover all of `src/ootp_ai/parser/` with **zero exemptions**; if the header reader indexes literals, the guard needs an exemption list and stops being a guard.

**(b) One declaration, three consumers.** `contracts/tables.toml` + `field_map.toml` are read by (i) `warehouse/ddl.py`, which *emits* the DDL rather than restating it, (ii) `tests/test_grain_contracts.py`, which compares the prose grain sentence to the emitted key, and (iii) `catalog/generate.py`. That triangle is what makes prose-vs-enforcement drift *structurally impossible* rather than merely discouraged — the exact obligation at `.claude/agents/data-engineer.md:101-104` ("states its grain in prose *and* enforces it with a uniqueness test, and the two must **agree**"). TOML because `tomllib` is stdlib in 3.12 (no new dependency), nothing writes the file, and per-field epistemic rationale wants comments. ADR 0006 §Notes explicitly blesses derived schema knowledge as ours and trackable — `.claude/agents/data-engineer.md:117-120` restates the line: *"A field-offset map you computed is ours and is tracked. A copy of `players.csv` is Out of the Park Developments' and is not."*

**(c) `contracts/policy.py::is_renderable(field)` is the only path to a page.** It returns false when `category == "rating-true"` or `epistemic in {"unconfirmed", "assumed"}` — ADR 0012's parser corollary, restated in CLAUDE.md: *a field the parser cannot classify is treated as a true rating and withheld; "probably fine" is not a classification.* Make it a **pure function over a declaration** so AC13's offline test can feed it synthetic entries — otherwise the test cannot run in CI, where no ratings have landed.

**(d) Every bronze primary key carries `snapshot_date` **and** `save_id`.** The pipeline parses two different universes — `OOTP-AI` (Boston, Challenge Mode, sim date 2024-03-07) and the retained standard-mode probe (Chicago Cubs, 2024-03-18) — and a key without `save_id` collides them. Recommendation for `save_id`: the save directory stem (`OOTP-AI`), typed `VARCHAR(64) NOT NULL`, validated at config time against `^[A-Za-z0-9_-]+$`. That regex does double duty: it makes it structurally impossible for an absolute path to become a `save_id` and leak into a tracked catalog. **Every PK column is declared NOT NULL** — MySQL's `COUNT(DISTINCT a,b,c)` silently drops tuples containing NULL, so a nullable PK column would make the grain test under-count and pass vacuously.

**(e) The catalog splits, and the split is what keeps it honest.** Per Decisions §3: the **structural half** (table names, grain sentences, key lists, coverage statements, withheld groups with reason and ADR, epistemic labels) generates from `tables.toml` + `field_map.toml` **alone** — no game data, no MySQL — so it is tracked, regenerates offline, survives a fresh clone, and can be asserted byte-identical to the committed copy. The **volatile half** (row counts, snapshot dates, freshness) plus `catalog.json` generate into the git-ignored root. **Recommended strengthening of the scope's marking:** because the byte-identity clause needs neither a save nor a database, split AC15 and run that clause **offline in CI** rather than under `-m gamedata`. That strictly increases what CI enforces.

### 1.4 Two path decisions that dissolve known risks at zero cost

**Reports render to `<output_root>/<save_id>/<snapshot_date>/roster.md`.** Snapshot-partitioning dissolves SD-21 / Risk 10 — regenerating a report overwrites the prior snapshot's view and breaks citation integrity for any `gm/decisions/` record that cites it — because a new sim date writes a new directory and re-rendering the same snapshot stays idempotent. `.gitignore:18` is a bare `var/`, and `git check-ignore -q var/reports/roster.md` exits 0 today, so AC14's ignored-root proof works as written.

**Every `file:line` citation this feature writes uses a code span, never a Markdown link, and nothing links into `var/`.** `tests/test_doc_links.py` resolves every relative link target in every tracked `.md` with no fence awareness and no `var/` exemption, so a link into the ignored output root turns CI red **today**. An open bugfix request exists (`requests/bugfix-requests/_done/doc-link-guard-mismatch/`); work around it, do not fix it here. `PROJECT_SCOPE.md:5-9` adopts the same convention for the same reason.

---

## 2. Phases

Thirteen phases. Each ends at a `/commit` gate on a green local run of all four commands. Phases 5, 6 and 7 walk three different files with three different byte-accounting tiers and three different answer keys — **do not merge them into one "parser" phase**, or a failure in `players.dat` blocks a green, provable `teams.dat`.

---

### Phase 0 — Pre-register every pivot rule, before anything runs

**Goal.** Make sure no later phase can hit an unbounded research task on the critical path, and satisfy the *ordering* half of AC18 — a pivot rule written after the result is not a pivot rule.

**Steps.**
1. Write `requests/feature-requests/first-sight/reviews/spike-pivot-rule.md` naming the trigger and the consequence for each branch of the scouted-view spike: **FOUND** → ratings have a source, and a later slice may parse them; **ABSENT** → record it, withhold every rating, ship both reports anyway, and file a follow-up request against ADRs 0012 / 0014 / 0016.
2. In the same document pre-register three further fallbacks, each with a concrete trigger, not a prose intention:
   - **`list_id` semantics** (Core §9, SD-17) — if the mapping cannot reach `inferred`, land it as an opaque integer, group the roster report by raw value with a header line stating the meanings are `unconfirmed`, never print a human label, file a follow-up.
   - **`teams.dat` strict byte accounting** — if a zero-residual walk cannot be reached inside the phase, demote to the diagnostic form (record the residual, assert termination on a record boundary), write the tier rationale into the field map, file a follow-up.
   - **The `names.dat` join** (Decisions §5) — if the encoding resists, resolve names from `players.csv` at *render* time for the ~1,712 players carrying a Lahman ID; fictional players render as IDs; **nothing is tracked**.
3. Record the measured `world.dat` league-config location so Phase 12's doc correction has a citation to point at: the string `major_league_ml_c_2024.lsdl` — exactly the `schedule_file_1` value already recorded at `docs/league-rules.md:79-81` — sits at byte 5,559,751 of `world.dat`, surrounded by league-shaped records containing `World Series`, `AL` and `NL`, and appears nowhere in `teams.dat`.

**Acceptance.** The pivot-rule file exists and is committed. `git ls-files src/ootp_ai` still lists only `__init__.py`. All three fallbacks carry a concrete trigger condition. `uv run pytest -m "not gamedata"` / `ruff check` / `ruff format --check` / `mypy` clean.

**Commit note.** *"Pre-register the scouted-view pivot rule and three research fallbacks."* Main thread only, no code, zero regression surface, trivially revertible. **The commit ordering relative to Phase 2 is the evidence for AC18** — do not squash them.

---

### Phase 1 — Toolchain, config layer, DB access, marker widening

**Goal.** Make the repo able to *collect* a warehouse-touching suite at all, and establish the one config layer every later phase resolves through.

**Steps.**
1. **Widen the marker first.** `pyproject.toml:80` currently reads `gamedata: requires a local OOTP install or save.` — it says nothing about a database. Widen it to *"requires a local OOTP install, save, or warehouse"*. Do **not** add a second marker: `addopts` at `:78` carries `--strict-markers`, so an undeclared marker is a **hard collection error** — the whole suite fails to collect, which presents as a broken repo rather than a missing marker. This is the single cheapest ordering mistake available in this plan.
2. **Choose the first runtime dependencies.** `pyproject.toml:9` is `dependencies = []`, and `:11-15` carries a tracked comment asserting *"The first real dependency will arrive with the warehouse loader"* — this phase makes that sentence describe the past, so update it in the same commit. Move `python-dotenv` **out of the dev group** (`:23`) into `[project].dependencies` — the config layer imports it at runtime, so leaving it dev-only means an installed package cannot read `.env`. Add a MySQL driver. **Recommendation: `PyMySQL` + `types-PyMySQL` in the dev group** — pure Python (no C toolchain on a Windows dev box), MIT like this repo, and maintained stubs, which matters because `pyproject.toml:71-73` runs mypy `strict = true` over `files = ["src", "tests"]`. Avoid `mysqlclient` (C extension, no maintained stubs) and note `mysql-connector-python` is Oracle GPLv2-with-FOSS-exception.
3. **`src/ootp_ai/config.py`** — a frozen dataclass plus `load_settings()`. Every path resolves from `.env`; **no literal path, no `parents[N]` walk** (`.claude/agents/data-engineer.md:88-90`, whose parenthetical makes test modules the one established exception). `OOTP_SNAPSHOT_ROOT` is documented at `.env.example:25` as defaulting to `var/snapshots` and is **empty in the live `.env`** — so define the default here as a CWD-relative `Path("var/snapshots")`, validate it is creatable, and reject it if it sits under the `OneDrive` environment variable's value (`.env.example:23-24` warns against cloud-synced storage). Derive and validate `save_id` per §1.3(d).
4. **`src/ootp_ai/warehouse/sql.py`** — `quote_ident()`, backticking every identifier and rejecting an embedded backtick. This is not hygiene theatre: measured, `select current_date from ootp_truth_real.leagues` returns the wall-clock date for all 15 rows, because MySQL parses the bare column name as the `CURRENT_DATE` function and **nothing errors**. That is a data incident sitting in the exact code path Phase 9's differential will use. Add `src/ootp_ai/db.py` with a read-only `ootp_truth_real` factory and a write factory for `ootp`.
5. **`.env.example`** — add the retained standard-mode probe save and the disposable Challenge Mode probe save (a directory *and* a league name each, so neither is hardcoded), plus the report/catalog output-root key. Retire `MYSQL_TRUTH_OSA_DATABASE` (`:58`) per Decisions §10, and mirror the retirement in `ops/mysql-bootstrap.sql` by removing the `ootp_truth_osa` create and its grant — measured, that schema is empty and `ootp_truth_real.players_scouted_ratings` already carries **both** scouting perspectives from one export (36,144 rows, `scouting_coach_id ∈ {-1, 2759}`, 18,072 each), so the premise for a second export database is wrong. All `.env.example` values stay empty: `tests/test_no_leaks.py:25` flags a drive letter.
6. **MAIN THREAD tests (offline):** `tests/test_config.py` (monkeypatched environment; missing-key error; snapshot-root default; `save_id` regex) and `tests/test_db_identifiers.py` (`quote_ident("current_date")` emits a backticked identifier; an embedded backtick raises).

**Watch out.** Ruff already selects `A` at `pyproject.toml:55` — `id`, `type`, `bytes`, `list`, `format` are illegal as names, and all of them are natural in a record walker. `DTZ` at `:57` makes any naive datetime an error (*"every timestamp here is tz-aware or it is a bug"*), so use `datetime.now(UTC)` for stamps and `time.perf_counter()` for durations. `PTH` at `:58` bans `os.path`. `N` at `:52` enforces pep8 naming. These surface as a wall at the first `ruff check` if not anticipated.

**Acceptance.** `uv run pytest -m "not gamedata" tests/test_config.py tests/test_db_identifiers.py` green with no game install and no MySQL. `uv run pytest --collect-only -m gamedata` collects without a marker error. `uv run mypy` clean **with the new driver imported** — that is the proof the stub story works under strict mode. All four pre-existing guards still green. `grep -rn 'parents\[' src/` returns nothing.

**Commit note.** *"Config layer, identifier quoting, first runtime deps, widened gamedata marker."* First commit to change the dependency posture — expect `/commit`'s doc gate to flag `pyproject.toml:11-15` and README setup text. Reverting returns the repo to a zero-dependency state with no orphaned code.

---

### Phase 2 — Run the scouted-view spike; record the verdict

**Goal.** Answer `docs/data-access.md:282`'s critical-path unknown — *is the scouted view stored at all, or computed at render time* — with a written verdict, an epistemic label and byte evidence.

**Steps.**
1. Run the test written verbatim at `docs/data-access.md:292-295` and never run: pull the values in `ootp_truth_real.players_scouted_ratings` and search the probe save's `scouting.dat` (2,349,181 bytes) for them as u16 little-endian runs positioned consistently across players. Search **both** the raw ~1–1000 encoding and the display scale — a null result on one scale alone is not ABSENT.
2. Cross-check the negative case against `players.csv`-derived *true* values, so a FOUND verdict is not merely "the file contains numbers in range".
3. Run it as a **throwaway script under `var/`** (git-ignored, `.gitignore:18`), never as tracked code. The verdict document carries the method and byte evidence, which is what makes it re-runnable.
4. Write `requests/feature-requests/first-sight/reviews/spike-scouted-view.md`: verdict (`stored` | `computed` | `inconclusive`), epistemic label, byte evidence (file, offsets, player ids checked), and which pre-registered branch is now live.
5. Prepare — do not apply — a docs-delta upgrading or explicitly reaffirming the `unconfirmed` label at `docs/data-access.md:282`. That file is deny-set for the builder (`:155`) and routes through `/update-docs` in Phase 12.

**Acceptance.** The verdict file states stored-or-computed with one of the five epistemic labels and cites concrete byte evidence, not an impression. `git log --oneline -- <pivot-rule path> <verdict path>` shows the rule committed **strictly earlier** (AC18). The spike script is untracked — `git check-ignore -q` on its path exits 0.

**Commit note.** *"Record the scouted-view spike verdict."* **If the verdict is ABSENT, stop and re-confirm with the operator before continuing.** The pre-registered pivot says the slice still ships — the reports need names, positions and roster membership, and none of those needs a rating — but a FAIL verdict on the mechanic behind ADRs 0012/0014/0016 deserves an explicit go/no-go rather than a plan that carries past it silently.

---

### Phase 3 — Parser spine: cursor, header/version guard, save enumerator, and two mechanical guards

**Goal.** Establish the spine once, correctly, and prove all three of its invariants **offline** — because `.github/workflows/ci.yml:49` runs `pytest -m "not gamedata"` and a spine proved only by gamedata tests has no CI signal at all.

**Steps (builder).**
1. `parser/primitives.py` — the Cursor per §1.3(a).
2. `parser/header.py` — read via the cursor only: leading `0x00`, `b"OOTP"`, u32 version (must be 25), the four u32s (11, 104, 84, 1), then the null-padded self-declared filename, cross-checked against the file actually opened (`docs/data-access.md:172-189`). Raise `UnsupportedSaveVersion` (this exact class name is pinned by AC1) on an unrecognized version, and a distinct `SaveFilenameMismatch` on disagreement. Refuse strictly — `.claude/agents/data-engineer.md:82-84`: *"a loud failure is recoverable, a silent misparse is not."*
3. `saves.py` — a directory is a save only if **both** `players.dat` and `teams.dat` are present. `docs/data-access.md:60-63` records, `measured`, that *"a `*.lg` glob is not a list of saves"* — the saved-games root contains a stray, empty directory literally named `.lg`. Add `assert_challenge_mode()`: `challenge.dat` present at **exactly 241 bytes** (`:65-68`), a filesystem-level mode check with no menu involved, promoted to a per-run pre-flight (folded-in §6).

**Steps (main thread — tests and fixtures).**
4. `tests/fixtures/synthetic.py` — byte builders as **functions**, not data files: `make_header(version=…, filename=…)`, `make_record(contract_years=…)`. **Fixtures must not carry a `.dat` extension.** Verified: `.gitignore:31` ignores `*.dat`, but `.gitignore:62`'s `!tests/fixtures/**` is a *later* negation and git's last-match-wins, so `tests/fixtures/sample.dat` is committable; the only thing catching it is `tests/test_no_leaks.py:107`'s `banned_suffixes`, as a red build. Building bytes in code sidesteps the whole question. `tests/fixtures/README.md` also makes the affirmative argument: a real save's day-0 state is the **least** informative input available, because every variable-length region is at its minimum — precisely the condition a fixed-offset reader passes cleanly.
5. `tests/test_save_header.py` (offline, **AC1**): a valid v25 header parses; version 24 **and** version 26 each raise `UnsupportedSaveVersion` by name; a buffer with `b"OOTP"` at offset **0** is rejected (the trap at `docs/data-access.md:183-186` — a reader checking `data[0:4]` sees `\x00OOT` and rejects every valid save, and one reading the version as a u32 at offset 4 gets 6480 rather than 25); a filename mismatch is rejected.
6. `tests/test_sequential_walk.py` (offline, **AC2**): two synthetic records identical except for the length of a variable-length region — a 1-year vs a 10-year contract array — must yield identical values for every field parsed *after* that region. Include a **negative control** in the same module: a deliberately fixed-offset local reader asserted to *fail* the same comparison. A test that passes without ever being able to fail proves nothing.
7. `tests/test_no_fixed_offsets.py` (offline, **AC3**): implement with `ast`, not regex, so a comment or docstring cannot trip it. Walk every module under `src/ootp_ai/parser/`; flag any call to `.seek(<nonzero int literal>)` and any `struct.unpack_from` whose third positional argument is a nonzero integer literal. `seek(0)` stays legal; `unpack_from(fmt, buf, cursor)` with a **name** argument stays legal — the ban is on literals. Include a self-test proving the scanner flags a synthetic offending snippet.
8. `tests/test_save_enumerator.py`: offline half against a `tmp_path` tree containing a decoy empty `.lg`; `-m gamedata` half against the **disposable Challenge Mode probe first**, and only then `OOTP-AI.lg`.

**Acceptance.** The three offline modules are green with no game install and no MySQL (AC1, AC2, AC3). Introduce `f.seek(128)` into a parser module, confirm `test_no_fixed_offsets.py` goes **red**, revert. `git ls-files tests/fixtures` lists no `.dat` or `.lg` path. `mypy` clean over the new package under strict mode.

**Commit note.** *"Parser spine: cursor primitives, strict header/version guard, save enumerator, mechanical fixed-offset scan."* Scrutinise this phase's acceptance hardest — everything downstream inherits it, and these three offline tests run in CI on every subsequent PR, so a later phase that reintroduces a seek goes red immediately rather than at the next data incident.

---

### Phase 4 — Snapshot copy, provenance from data, and the ADR 0001 read-only proof

**Goal.** Get every later phase parsing a snapshot rather than the live save, and prove mechanically that nothing under the game directories was touched — **before** the phases that open the big files, not after.

**Steps.**
1. `snapshot.py` — copy **only** the in-scope set to `<snapshot_root>/<league>/<sim_date>/`: `teams.dat` (5,318,831 B), `players.dat` (32,070,106 B), `names.dat` (8,642,110 B) — ~46 MB, **not** the ~600 MB `.lg`, and explicitly not `retired.dat` (154 MB). Write a per-file size + SHA-256 manifest. Every handle `"rb"`. Refuse to overwrite an existing snapshot directory — snapshots are immutable (`.claude/agents/data-engineer.md:85-87`), which is what makes incident triage tractable and history re-parseable without the game.
2. `ingest.py` — land the ingest-run record **shape** now (source file sizes, digests, header versions, sim date, human team, and placeholders for row counts, residual bytes and parse seconds). It is not persisted until Phase 8; landing the shape here means later phases fill fields rather than inventing a schema under time pressure.
3. `parser/saved_games.py` — **correction to a `verified` claim.** `docs/data-access.md:36-38` states `saved_games.dat` is *"plaintext … readable without parsing"*; scope finding F19 contradicts this at `high` confidence. It carries the standard header and length-prefixed strings, so read it through the **same header reader plus a string walk** — never substring-scrape. It yields each save's sim date and human team.
4. **Resolve the human team from data on every run** (folded-in §7). `OOTP-AI` is Boston at 2024-03-07; the probe is the Chicago Cubs at 2024-03-18. Code that hardcodes *"we are team 6"* or *"perspective 2759 is us"* **passes on ground truth and breaks on our league, invisibly** — and the entire validation harness runs against the probe, so nothing would catch it.
5. **Hard bind:** `saved_games.dat` embeds an **absolute user-profile path** per save. Its contents may reach the warehouse ingest-run row and the generated (ignored) catalog half only. Nothing that renders it may reach a tracked file — this repo is public, and a provenance section would publish a username.
6. **MAIN THREAD:** `tests/test_read_only.py` (`-m gamedata`, **AC11**) — build a manifest of size + `mtime_ns` + SHA-256 over every file under `$OOTP_SAVED_GAMES` and `$OOTP_INSTALL`, run the full pipeline entry point, re-manifest, diff. **Zero differences.** Per SD-20 it runs against the disposable Challenge Mode probe **first** and only then `OOTP-AI.lg`. It must skip **loudly with a named reason** if the paths are unset — never pass vacuously.
7. **MAIN THREAD:** the snapshot half of `tests/test_snapshot_semantics.py` (`-m gamedata`) plus an offline assertion that the resolved snapshot root is git-ignored, proven as AC14 requires: `git check-ignore -q <path>` exits 0 **and** `git ls-files` lists nothing under it. ("Outside the git worktree" is unsatisfiable — `var/` is inside the worktree and merely ignored.)

**Acceptance.** `uv run pytest -m gamedata tests/test_read_only.py` green against the probe **and then** `OOTP-AI.lg` — zero mtime and zero digest differences across both roots. The snapshot manifest lists exactly three source files with sizes matching the measured values. `grep -rn 'open(' src/ootp_ai/` shows no write mode against any path derived from `OOTP_INSTALL` or `OOTP_SAVED_GAMES`.

**Commit note.** *"Snapshot copy + SHA-256 manifest, saved_games.dat read properly, ADR 0001 read-only proof."* **Hand the operator AC21 here rather than at the end** — confirming `OOTP-AI.lg`'s file set, sizes and mtimes by hand against the recorded manifest is far cheaper to do after a 46 MB copy than after discovering a violation post-full-parse.

---

### Phase 5 — `teams.dat` sequential walk and the team dimension

**Goal.** Land the first real walk against the file with the strongest existing ground truth, validating the walker pattern before the two hard files.

**Steps.**
1. `parser/teams.py` — sequential walk yielding `team_id`, the 5-string signature (city, abbreviation, nickname, logo filename, full name) followed by u32 ARGB colors — already `verified` at `docs/data-access.md:224-226`, with all 30 MLB clubs extracting cleanly — plus level, `parent_team_id` (so MLB clubs are distinguishable from affiliates), the sub-league/division hierarchy, and the win-loss fields the standings report needs. Note `docs/data-access.md:228` marks *everything else* in that file `unconfirmed`.
2. **Structural absence starts here and is a parser-level concept.** A field the record does not carry → `None` → SQL NULL. A field present holding zero → `0`. Bronze never converts between them (`.claude/agents/data-engineer.md:110-112`: *"Averaging across that boundary produces wrong numbers, not incomplete ones."*). This bites immediately: the export writes `0` for `rules_active_roster_limit` and the service-time columns on all **14** non-MLB league rows — 14 separate opportunities to commit this error.
3. Track consumed bytes as the walk proceeds and return a residual.
4. **MAIN THREAD:** the teams half of `tests/test_byte_accounting.py` (`-m gamedata`, **AC12**) at the **strict** tier — zero unaccounted bytes. If strict proves unreachable within the phase, apply Phase 0's pre-registered demotion rather than opening an unbounded research task on the critical path.
5. **MAIN THREAD:** the teams half of `tests/test_parse_real_save.py` (`-m gamedata`, **AC9**) — exactly 30 teams at MLB level with correct abbreviations from `OOTP-AI.lg`; 259 teams total from the probe; `team_id` unique per snapshot.
6. **MAIN THREAD:** an offline `tests/test_parse_teams_synthetic.py` against a hand-built two-team buffer, so the walker has CI signal (`.claude/agents/data-engineer.md:91-92`).

**Acceptance.** The three test selectors above green at their declared tiers, and the declared tier matches what the test actually asserts. `test_no_fixed_offsets.py` still green over the enlarged parser tree. `test_read_only.py` re-run green after a full `teams.dat` walk.

**Commit note.** *"Walk teams.dat sequentially: team dimension, hierarchy, W-L, byte accounting."* From here on, **every phase re-runs `test_read_only.py` and `test_no_fixed_offsets.py` as part of its own acceptance** — the two unrecoverable-failure guards, checked at every checkpoint for the cost of seconds.

---

### Phase 6 — `names.dat` and the join, against two independent answer keys

**Goal.** Resolve the largest single unknown in the request. `docs/data-access.md:234-238` records that names are indices into a ~264,095-entry table and labels *"the index encoding and the `names.dat` table layout"* **`unconfirmed`** — and `docs/data-access.md:14` is explicit that *"an unconfirmed claim is a task, not a fact."* A roster report of integers is not a roster report.

**Steps.**
1. `parser/names.py` — walk the observed record shape: u32 length + ASCII + u32 `0` + u32 monotonic index + three u32s + a `0x27` separator, alphabetically ordered. Strict byte accounting (zero residual).
2. **Settle the key space *before* any DDL is written.** It is genuinely unknown whether `names.dat` carries **one** index space or **two** (a first-name table and a last-name table, each alphabetically ordered with its own index from 0). If it is two and `bronze_name` is keyed `(snapshot_date, save_id, name_index)`, the spaces **collide and every collided row is silently wrong**, with nothing throwing. Pre-registered resolution: declare the key as `(snapshot_date, save_id, name_space, name_index)` with `name_space` a `NOT NULL` discriminator taking a single literal value if one space is proven. That key is correct under both outcomes and costs one column.
3. **Resolve which u32 fields in the player record are the name indices by brute force against a full answer key, not by guessing.** For each candidate u32 position the walk exposes, apply the mapping across all 18,072 probe players and score exact matches against `ootp_truth_real.players.first_name`/`.last_name`. The correct field scores ~100%; everything else scores near zero. Record the winning position and its score in `field_map.toml`.
4. **Enforce the per-save constraint structurally (SD-10).** Measured: `names.dat` is 8,642,110 bytes in **all three** saves on disk with **three different SHA-256 digests** — a fixed-size, per-save-populated table. The name table must be an object *owned by a save*, never a module-level constant, and the resolver's cache key must include `save_id`, asserted by a test. This is a silent-wrong failure with no crash: a cached probe table applied to `OOTP-AI.lg` produces a roster full of confident, wrong names.
5. **MAIN THREAD:** `tests/test_names_join.py` (`-m gamedata`, **AC7**, Tier B) — every resolved index matches `ootp_truth_real` by exact string equality, 100% of compared rows, zero unresolved indices, **every failure enumerated by name**, never an aggregate pass rate. It **skips loudly with a named reason** if `ootp_truth_real` is unreachable; verify the skip path by temporarily unsetting the key. A vacuous green here is worse than a red.
6. **Settle collation explicitly (SD-13).** `ops/mysql-bootstrap.sql` creates every schema `utf8mb4_0900_ai_ci` — accent- **and** case-**insensitive** — so an "exact" comparison performed in SQL scores `Ramírez == Ramirez` as a match, in a repo whose own export doc turns *Replace accents* **Off** specifically because it *"mangles names and breaks validation against `names.dat`"* (`docs/data-access.md:336`). **Fetch both sides into Python and compare decoded `str` with `==`**; where SQL-side comparison is unavoidable, append `COLLATE utf8mb4_bin` explicitly, and assert the choice in the test so a schema change surfaces.
7. **MAIN THREAD:** `tests/test_names_join_boston.py` (`-m gamedata`, **AC8**, Tier A) — for every player in `OOTP-AI.lg` carrying a non-empty `historical_id`, the resolved first/last name equals `players.csv`'s `FirstName`/`LastName` joined on `LahmanID`, 100% exact. **This is the only validation of the join on the league we actually manage.** Parse `players.csv` with stdlib `csv`, stripping the `//` prefix from its header line (`docs/data-access.md:79-80`).
8. **Hard bind:** never write a Lahman-ID-to-name lookup to a tracked file, in any form. `tests/test_no_leaks.py:106` catches `players.csv` by **filename only** — a renamed derived copy sails straight through into a public repo, and `tests/fixtures/README.md` says plainly that catching a renamed real slice is on the implementer.
9. **MAIN THREAD:** a `-m gamedata` test asserting the same index is **not** expected to resolve identically across the two saves, pinning the per-save finding.

**Acceptance.** AC7 and AC8 green as specified; strict zero-residual byte accounting on `names.dat`; the cache-key-includes-`save_id` structural test green; the key-space question settled and recorded with an epistemic label; `git ls-files` lists no file containing a Lahman-to-name lookup and `test_no_leaks.py` is green.

**Commit note.** *"Resolve the names.dat join against both answer keys, with the per-save constraint pinned by test."* **This is the plan's decision point.** Tell the operator explicitly which branch fired — the join resolved, or the `players.csv` render-time fallback is now live — because the roster report's shape differs between them and every later phase inherits the choice. This is also the commit that turns the roster from integers into people; the request's observable signal depends on it.

---

### Phase 7 — `players.dat` walk and roster-list extraction

**Goal.** Land the deliberately minimal player field set and the **roster-membership grain** — the fan-out the request never names, and the one that bites *today*, on an unsimmed save with no trade in sight, because a player sits on the active list **and** the 40-man simultaneously.

**Steps.**
1. `parser/players.py` — a deliberately minimal field set: `player_id`, team/organization assignment, position, uniform number, date of birth, bats/throws, the name indices, and `historical_id` (the Lahman/BBRef string, `verified` at `docs/data-access.md:99-102`, ~1,712 unique values). **No ratings, whatever the Phase 2 verdict returned.** Resist widening: every landed field is a field somebody re-validates after a game patch. The field set is a maintenance liability, not a free win.
2. `parser/rosters.py` — extraction at the `(team_id, player_id, list_id)` grain. Ground truth for the shape: `ootp_truth_real.team_roster` is **15,672 rows over 7,370 distinct players** — not 18,072 — with `list_id ∈ {1: 7370, 2: 7037, 3: 935, 4: 330}`. Derive each `list_id` value's meaning empirically against those counts; `db_structure_ootp25_mysql.txt` documents the columns but **not** the enum's semantics. If the mapping cannot reach `inferred`, fire Phase 0's fallback — a wrong human label produces a confidently wrong roster with nothing throwing.
3. **Verify, do not assume, the `players.dat` population.** The plan (and AC12's diagnostic tier, and Phase 11's coverage statements) assumes `players.dat` holds the export's `retired = 0` set of 18,072 and `retired.dat` holds the rest. That is an **inference from filenames, not a measurement.** Confirm it by record count against the export before treating it as fact.
4. Byte accounting at the **diagnostic** tier for `players.dat` (blocker F3): assert the walk terminates on a record boundary and reaches a record count matching the independent count, and **record** the residual byte count rather than asserting it is zero. Full byte accounting on a 32 MB `players.dat` is a research task, not a counter — say so in the tier rationale so a later reader does not mistake the weaker assertion for sloppiness. On `OOTP-AI.lg` there is no export, so the check degrades to boundary termination plus Phase 9's Boston sanity check; encode that degradation explicitly rather than silently skipping.
5. Append every landed field to `field_map.toml`. Anything the walk crosses but cannot classify is recorded `category = "rating-true"`, `epistemic = "unconfirmed"` — the withhold-by-default posture.
6. **MAIN THREAD:** complete `tests/test_parse_real_save.py` (**AC9**) — `player_id` unique per snapshot; Boston's roster rows **≥ 26**, not `== 26` (the club is in spring training at 2024-03-07 and a set 26 probably does not exist yet); **zero** roster rows carry a null or blank display name. Extend `test_sequential_walk.py` with a player-shaped synthetic record (1-year vs 10-year contract array) asserting `historical_id`, which sits after the variable region, reads identically. Add the parser-determinism half of `test_snapshot_semantics.py` (**AC10**): parsing the same snapshot twice is byte-identical.

**Acceptance.** AC9 green in full; AC12 green at both tiers with the residual recorded; the `list_id` label at `inferred` or better with evidence written down, or the opaque-integer fallback in force; the population claim measured; `test_read_only.py` re-run green after the largest read this project performs.

**Commit note.** *"players.dat minimal field set + team_roster membership grain with list_id derivation."* Surface the `list_id` disposition to the operator here — whether the roster report prints human list names or raw integers is a visible product decision, cheaper to settle now than to rework in Phase 10.

---

### Phase 8 — Contracts, DDL, bronze landing, and the ingest run

**Goal.** Land bronze into the empty `ootp` schema from **one** tracked declaration with **three** consumers, so grain-prose-vs-grain-enforcement drift becomes structurally impossible. The contracts land *before* the loader, so the loader is written against a declared contract rather than the contract being reverse-engineered from the loader.

**Steps.**
1. Complete `contracts/tables.toml` and `field_map.toml` per §1.3(b). Declared keys: `bronze_team` (`snapshot_date`, `save_id`, `team_id`); `bronze_player` (`snapshot_date`, `save_id`, `player_id`); `bronze_team_roster` (`snapshot_date`, `save_id`, `team_id`, `player_id`, `list_id`) — **explicitly not** `(snapshot_date, player_id)`; `bronze_name` (`snapshot_date`, `save_id`, `name_space`, `name_index`) with its own declared grain, key and coverage like every other table. Record Decisions §8 here too (ratings render at the 20–80 player-page scale) so the next slice inherits a decision rather than re-deriving one.
2. Declare `historical_id` a **nullable attribute, never a join key** in any serving path. Measured: 1,920 of 18,072 active players carry a non-empty one (10.6%) — `.claude/agents/data-engineer.md:107-109` states the consequence: *"A join on the wrong one silently drops the fictional majority and looks like it worked."* Add a static check over `src/ootp_ai/` asserting no join uses it — and **scope it to `src/` and exclude `tests/`**, because `test_names_join_boston.py` legitimately joins on LahmanID as ground truth and an unscoped guard would block its own validation.
3. `warehouse/ddl.py` emits `CREATE TABLE` and `PRIMARY KEY` **from** the declaration. Every PK column `NOT NULL` (§1.3(d)). Name-bearing tables get `CHARSET=utf8mb4 COLLATE=utf8mb4_bin`.
4. `warehouse/load.py` — bronze is **1:1 with parser output**: typing, casing, dedup only. No joins, no filtering, no semantic renaming (`.claude/agents/data-engineer.md:98-100`). Land **everything** the walk yields including all 259 teams and every minor-league population; the org filter lives in the report layer (Decisions §7). Preserve structural absence as NULL, never zero.
5. `warehouse/ingest_run.py` — **resolve the idempotency collision explicitly.** AC10 requires that loading the same snapshot twice leaves row counts and checksums unchanged, but an append-only ingest-run table adds a row and changes a count, and a wall-clock column breaks bit-identity. **Decision: key `ingest_run` on `(snapshot_date, save_id)`, and a re-land of an existing snapshot refuses loudly** — which satisfies all four AC10 clauses at once, including *"re-landing an existing snapshot id does not silently overwrite it."* An implementer who does not notice this collision will write a test that cannot pass. Columns: source file sizes, SHA-256 digests, header versions, sim date, human team, per-table row counts, residual bytes, wall-clock parse seconds (`time.perf_counter()`, never a naive `datetime` — ruff `DTZ`).
6. `bronze_field_label` (folded-in §5) — each landed field's epistemic label written into the warehouse alongside the data, keyed `(snapshot_date, save_id, table_name, column_name)`, so a future incident can ask *"what did we believe about this field the day it landed?"* as a query rather than as archaeology through the git history of `docs/data-access.md`.
7. Add `dump_parse(path)` — a deterministic, key-sorted serialization — so "parsing twice is byte-identical" is testable by hashing.
8. **MAIN THREAD tests.** `tests/test_grain_contracts.py`: the **offline** half (**AC4**) reads the declaration and the emitted DDL and asserts the prose grain sentence equals the emitted key for all four tables, and that every PK column is NOT NULL. The `-m gamedata` half (**AC5**), `test_roster_grain_is_not_player_grain`, **positively asserts** `player_id` is *not* unique within one snapshot's roster rows, and that `count(distinct player_id)` in `bronze_team_roster` is materially less than `count(*)` in `bronze_player` for the same snapshot. `tests/test_withheld_fields.py` (**AC13**, offline) keyed on declared **category**, not column-name globs, **including the negative case** — a synthetic `rating-scouted` field with a proven label *is* renderable — because a guard that blocks everything passes the positive half and delivers nothing. Keep name patterns only as a secondary check, with `talent_%` corrected to `%_talent_%` (the real columns are `batting_ratings_talent_*`; as originally written the pattern matched nothing). Complete `tests/test_snapshot_semantics.py` (**AC10**).

**Acceptance.** AC4 and AC13 green **offline** with no MySQL — these are the contracts CI actually enforces. AC5 and AC10 green under `-m gamedata`. **Mutate the declared `bronze_team_roster` key to `(snapshot_date, player_id)` locally and confirm `test_grain_contracts.py` goes red; revert.** The `ootp` schema, previously 0 tables, holds exactly the six named tables. `uv run pytest -m "not gamedata"` green with no MySQL running.

**Commit note.** *"Field map declaration + DDL emitter + bronze landing + ingest_run + the five contracts."* Reversibility here is schema-level: dropping the `ootp` tables restores the prior state, and `ops/mysql-bootstrap.sql` recreates the empty schema. This is the first phase requiring a running MySQL, so local and CI signal diverge permanently from here — which is why the contract tests were deliberately written to run offline.

---

### Phase 9 — The parser-vs-export differential harness, and the recorded extraction cost

**Goal.** Prove the parser row-for-row against an independent answer key, **per field by name**. This converts the field map's labels from beliefs into findings, and it must be green before anything is rendered for a GM to read.

**Steps.**
1. `validate/export_diff.py` — parse the probe save, land it under its own `save_id`, and diff against `ootp_truth_real` **inside one MySQL instance**, which is ADR 0004's stated rationale for choosing MySQL at all. Every identifier routes through `quote_ident()`.
2. **Assert provenance first, before any value comparison** (`tests/test_parser_vs_export.py`, `-m gamedata`, **AC6**): the parsed save's sim date is 2024-03-18 and its human team is the Chicago Cubs, matching `ootp_truth_real`. A field diff against a different universe is noise that looks like a finding.
3. Then diff: **zero** row-count and **zero** value differences over the landed field set — 259 teams, 18,072 active players (`retired = 0`), 15,672 `team_roster` rows, 15 leagues. Every mismatch listed **per field by name**; an aggregate pass rate is not acceptable output (Core §18) — it is exactly how a parser reading the adjacent u16 ships green.
4. **Add an explicit structural-absence allowlist.** The export writes `0` where the value is structurally absent (`rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows); our parser lands NULL. Without a **named per-column allowlist, each entry carrying its reason**, a *correct* parse produces 14 false mismatches — and the tempting fix is to make the parser write 0, committing precisely the error `.claude/agents/data-engineer.md:110-112` warns about.
5. Compare strings in Python on decoded `str`, per Phase 6's collation finding.
6. **Document Tier B's limits inside the test**, so a later agent extending the harness to ratings does not inherit false confidence from a green suite: Tier B is **exact** for ids, names, strings, dates, roster lists, team dimension and league config, and **bucketed** for ratings — measured, `players_batting.batting_ratings_overall_contact` has exactly **12 distinct values across 20–80**. The export is display scale and can never be an exact rating validator; a bucketed check can pass a parser reading the *adjacent* u16, which is CLAUDE.md's named correctness trap in its most dangerous form. `players.csv` (Tier A) stays load-bearing permanently.
7. **MAIN THREAD:** `tests/test_extraction_cost.py` (`-m gamedata`, **AC17**) asserts the wall-clock number **exists** and was recorded into the ingest-run row — read it back from the warehouse, not from stdout. **No threshold, no pass/fail on duration** (Decisions §6, an operator ruling: the work takes as long as it needs; the tautology objection is accepted deliberately, on the grounds that a threshold nobody has justified is worse than an honest measurement).
8. Prepare the docs-delta upgrading epistemic labels for **exactly** the fields Tier A or Tier B actually proved — everything else stays `unconfirmed` and therefore withheld by Phase 8's guard.

**Acceptance.** AC6 green with provenance pinned first. **Deliberately corrupt one parsed field and confirm the harness names *that field* in its failure output rather than reporting a percentage; revert.** A differential harness never seen to fail informatively is not yet a harness. AC17 green. `test_withheld_fields.py` still green after the label upgrades.

**Commit note.** *"Differential harness: parser vs the probe-save export, provenance-pinned and per-field."* Route the docs-delta through `/update-docs` in the same unit of work so labels and the code that earned them land together. **If the differential is not green, do not proceed to Phase 10** — a report built on an unvalidated parse is exactly the silent-wrong-data failure the requests README describes.

---

### Phase 10 — The two reports and the rendered-game-data leak guard

**Goal.** Deliver the request's observable signal — a report naming real Boston players — and extend the leak guard to cover it, because this feature is the **first thing in the repo's history that renders OOTP player data to a file**.

**Steps.**
1. `reports/__main__.py` exposing `render`, so that `uv run python -m ootp_ai.reports render` is the real entry point AC14 invokes. Output to `<output_root>/<save_id>/<snapshot_date>/` per §1.4.
2. `reports/roster.py` — the **configured organization only**, grouped by roster list, carrying position, age, bats/throws and uniform number, with `snapshot_date` and sim date on **line one** so staleness is visible on sight. The org filter lives here, never at bronze. Honour Phase 7's `list_id` disposition: no human label for a mapping below `inferred`.
3. `reports/standings.py` — 30 MLB clubs by division with W-L-pct-GB. **Expect it to carry no signal:** measured, all 259 `team_record` rows are 0-0-0 and 0 of 12,961 games are played, because both saves sit before opening day. Emit a **structural-absence marker rather than `.000`** for pct when games played is zero.
4. Route **every** report column through `contracts/policy.py::is_renderable()`. There is no second path to the page.
5. **MAIN THREAD:** `tests/test_reports.py` (`-m gamedata`, **AC14**) — the resolved output root is git-ignored, proven by `git check-ignore -q` exiting 0 **and** `git ls-files` listing nothing under it; the roster report contains rows for exactly the configured organization and **zero** belonging to any other; every player row's name matches `^[A-Za-z][A-Za-z .'-]+$` (a name, not an integer); the standings report contains 30 MLB rows grouped by division with W-L-pct-GB columns present; both files carry `snapshot_date` and sim date on line one. **Assert standings content structurally, never by value** — asserting a nonzero win total would fail on a *correct* parse, the most expensive kind of wrong test, because it sends the next agent hunting a bug in working code.
6. **MAIN THREAD:** extend `tests/test_no_leaks.py` (folded-in §1). The existing guard bans four filenames and two suffixes at `:106-107`; a Markdown roster sails straight through. Add: the report and catalog output roots resolve to git-ignored paths; and the tracked half of the catalog and field map may name source **files** (`players.dat`) but **never absolute paths** — reuse the existing `PATTERNS` at `:24-28` rather than inventing a second set. Note in a comment the known local-feedback gap: `tracked_text_files()` at `:31-48` enumerates via `git ls-files`, so an untracked artifact is invisible locally and only fails in CI. **Record it, do not fix it** — file a follow-up; it is out of scope. Run the guard *after* staging, not before.

**Acceptance.** `uv run python -m ootp_ai.reports render` writes both reports; AC14 green on all five clauses; AC13 still green offline including the negative renderable case. Read the roster report by eye once and confirm it contains recognisable Boston names, not integers — an informal check that the name-regex assertion is testing what it claims. `test_no_leaks.py::test_patterns_still_catch_real_leaks` (`:51-78`) still green — *"a guard that has been loosened until it passes is not a guard."*

**Commit note.** *"Render the roster and standings reports, gated by a category-keyed withheld-field guard."* **This is the commit the request exists for** — after it, the GM can name its own players. It is also the natural early-ship point if the slice needs to stop: Phases 11–13 add the catalog and the doc sweep, but the GM can already see its club.

---

### Phase 11 — The generated catalog and its tracked/volatile split

**Goal.** Tell the GM what exists **and what was deliberately withheld and why**, so it prices an action against a known gap rather than discovering it by hitting it. The request's second desired outcome is *"the GM knows what it is not seeing"*, and a catalog of landed tables tells it only what it can see.

**Steps.**
1. `catalog/__main__.py` so that `uv run python -m ootp_ai.catalog` (no subcommand) is the real entry point AC15 invokes. It reads `information_schema` for counts and `contracts/` for grains, keys, coverage and labels — one declaration, three consumers.
2. Split per §1.3(e). Recommended placement: `docs/warehouse-catalog.md` + `docs/warehouse-catalog.json` tracked; the volatile half plus `catalog.json` into the ignored root. **Make the tracked half byte-deterministic**: sorted ordering, no timestamps, no absolute paths, no hostnames, no git-derived values — AC15 asserts byte-identity, and any nondeterminism makes it flap.
3. **Generate coverage statements from counts**, never hand-written (folded-in §3). *"players: 18,072 rows, active only, retired excluded, 1,920 carry an external ID"* is far more useful than a table name and cannot go stale. State how many players carry **no roster row** — computed as `count(bronze_player) − count(distinct player_id in bronze_team_roster)`, roughly 10,700 of 18,072 (free agents, draft-eligible, international, unassigned) — so the GM prices *"who is available"* as a known gap.
4. The **withheld section** names the true-rating tables, `players.prone_*`, `players_value.*` and every still-`unconfirmed` field, each with its reason and its ADR. **No player-level value and no rating column name appears anywhere in the catalog.**
5. Emit `catalog.json` from the same generator (folded-in §4) — one generator, one extra writer.
6. **Add the report-path pointer to the tracked half** (Core §15, SD-11): each report's logical name, the `.env` key and relative path it resolves to, and a one-line spawn instruction the umpires read when handing the GM its reports. **As code spans, never a Markdown link into `var/`** (§1.4). Without this pointer, AC20 is unreproducible by anyone who was not in the room.
7. **MAIN THREAD:** `tests/test_catalog.py` — the **offline** half regenerates the structural section during the test and asserts it is byte-identical to the committed copy (proving it cannot be hand-edited into drift) and contains no rating column name; the `-m gamedata` half asserts every landed table appears with grain sentence, key list, coverage population, row count, source `.dat` file, epistemic label and snapshot date, and that regenerating twice is byte-identical.

**Acceptance.** AC15 green. **Hand-edit one character of the committed structural half and confirm the test goes red; revert** — that assertion exists to fire, and must be seen to. Run the generator twice and diff: zero bytes different, proving determinism rather than luck. `test_doc_links.py` and `test_no_leaks.py` still green.

**Commit note.** *"Generate the warehouse catalog: tracked structure, generated volume, explicit withheld section."* Raise the tracked-catalog **location** with the operator here if it was not settled earlier — CLAUDE.md forbids creating directories speculatively, so a new top-level `catalog/` needs an argument the operator should make. If it lands in `docs/`, decide whether it joins `tests/test_repo_structure.py`'s required-docs list (a main-thread test edit).

---

### Phase 12 — Documentation truth-up, the tracked report channel, the dbt deferral

**Goal.** Correct what is now measurably wrong, record the deferrals on the record rather than quietly, and open the report channel in `gm/`.

**Steps.**
1. **Route everything through `/update-docs`, main thread only.** `docs/data-access.md` (`:155`) and `docs/decisions/` (`:156`) are deny-set for the builder; findings arrive as a `## docs-delta` with proposed labels.
2. **AC19:** correct `docs/league-rules.md:129` (*"The parser reads `leagues.dat` directly and may recover some of these"*) and `:295` (*"Until the parser can open `leagues.dat`…"*). **No such file exists** — `OOTP-AI.lg` holds 18 `.dat` files and none is it. Record the measured `world.dat` location from Phase 0 instead. Also revisit `:26` and `:30-31`, which describe §1 as superseded by the warehouse *"the moment the parser lands"* — this slice makes that **partially, not wholly, true**, and partial supersession stated as total is the kind of doc claim that gets acted on wrongly.
3. `docs/data-access.md`: complete §1's file table (18 `.dat` files present, several unlisted, no `leagues.dat`); **downgrade the `verified` label at `:36-38`** asserting `saved_games.dat` is plaintext (finding F19 — it carries the standard header and length-prefixed strings, and embeds an absolute user-profile path); add the `names.dat` fixed-size-per-save finding at `inferred`; record `ootp_truth_osa` as empty and unnecessary; **reclassify the probe save as a retained validation asset** (folded-in §8 — ADR 0002 and `docs/data-access.md:319-320` currently call it disposable, yet every value claim in the validation strategy depends on it staying on disk, and the parser loses its only ground truth for fictional players and roster lists the day someone tidies up); and upgrade labels for **exactly** what Tier A or Tier B proved, each naming the test that proved it.
4. Append the **dbt deferral** to `docs/decisions/0004-mysql-warehouse.md` §Notes (Decisions §9): the trigger fired (a warehouse landed) and dbt was *not* pulled, with the reason — ADR 0005's **pattern** choice is honoured in full and only its **tooling** phrasing is deferred. A superseding ADR is too heavy for a postponement, but quietly diverging is the one option this repo forbids.
5. **Umpire edit, main thread:** extend `gm/standing-orders.md`'s `## Reports` format block (`:42-50`) with the new **engineering-owned report kind** (Decisions §4) — a pipeline-generated report genuinely has no analyst behind it, and `gm/staff.md` records that no staff exist, so naming an owner would be fiction. Then add the two report entries under that kind. The `Status: none active` line at `:10-11` changes.
6. Update the now-false status text: `CLAUDE.md`'s Status section (*"`src/ootp_ai/` is a version string … the GM therefore has no warehouse and no reports yet"*), `README.md`'s status/next-steps/setup (new `.env` keys, the MySQL driver, how to run the ingest and render the reports), and `gm/charter.md:10-15`, whose Status blockquote names *"no warehouse and no reports"* as the blocker. Replace `src/ootp_ai/__init__.py`'s docstring, false since Phase 3.
7. Advance the request artifacts — `PROJECT_SCOPE.md`'s status header and the track Index row at `requests/feature-requests/README.md:119` — and write `IMPLEMENTATION_REPORT.md`. `/commit` Step 4 maintains these.

**Acceptance.** `grep -rn 'leagues.dat' docs/` returns only an explicit correction note (**AC19**). **AC16:** `uv run pytest -m "not gamedata"` passes with **no** game install and **no** MySQL, and `ruff check .`, `ruff format --check .`, `mypy` are clean, with all four pre-existing guards green. `uv run pytest -m gamedata` passes **in full, in one pass** rather than phase by phase. Every upgraded label names its proving test; no label is upgraded without one.

**Commit note.** *"Truth-up the docs, record the dbt deferral, open the tracked report channel."* `/update-docs` is the doc gate. Then **ask before merging the PR** — never push `main`, never force-push, never amend.

---

### Phase 13 — USER-RUN acceptance and the umpire ledger act

**Goal.** Close the two criteria the acceptance panel must **not** claim, and land the precedent every later report request will cite. `.claude/agents/data-engineer.md:129-130`: *"Anything outward-facing is user-run. Stage it as a script and report it under `still-open`. Never run it yourself."*

**Steps.**
1. **AC20 (USER-RUN).** A cold session spawns the `gm` subagent with the roster and catalog reports in its context. That agent holds exactly `tools: Read, Glob` — a Markdown file handed into its context is the **entire delivery surface** — and its forced-read list item 8 is *"Any report or analysis handed to you for this invocation."* The returned handoff's `## situation` must name **at least five Boston players by real name**, each attributed to the report as its source, with **no roster fact appearing in `## assumed`**. Hand the operator the exact spawn instruction from Phase 11's catalog pointer.
2. **AC21 (USER-RUN).** The operator confirms `OOTP-AI.lg`'s file set, sizes and modification times are unchanged after a full ingestion run, **by hand**, against the manifest recorded in Phase 4. Deliberately redundant with `test_read_only.py`, because this is the one check in the project that must not be performed by the code it audits.
3. **The ledger row is an umpire act, not a build artifact** (Decisions §2, blocker SD-03). After delivery, the umpires append one row to `gm/ledger.jsonl` recording that the roster report and catalog are **free infrastructure** rather than a commissioned action, **with its reasoning** — ADR 0016's boundary is analytical *direction*, not existence, and a roster page and the standings are the club's own furniture. It becomes an early `seq` every later report request cites. Append-only; `.gitattributes` marks it `merge=union`. Note the ordering wrinkle: `gm/standing-orders.md:45` requires each entry to carry `**Established:** ledger seq <n>`, and the seq does not exist when Phase 12 writes the entries — land them with an explicit engineering-owned marker and leave the seq to the operator (see Open Questions).
4. File the two follow-ups the scope named but excluded: the `git ls-files` staging gap in `test_no_leaks.py`, and the GM tool-grant guard test (Decisions §11 — `.claude/agents/gm.md` grants exactly `Read, Glob` and nothing under `tests/` asserts it).

**Acceptance.** The GM handoff meets AC20's bar. The operator's by-hand check shows zero changes. One ledger row appended in the documented schema. Two follow-up requests filed. Final green on all four commands.

**Commit note.** *"USER-RUN acceptance recorded, umpire ledger row appended, follow-ups filed."* **Do not mark the request `implemented` on the acceptance panel's word alone** — AC20 and AC21 are explicitly the operator's, and `requests/feature-requests/README.md` requires human-only criteria be marked USER-RUN precisely so the panel does not claim them. Move the slug to `_done/` only after both come back green.

---

## 3. Testing and regression safety

### 3.1 The split, and why it is the most important testing decision here

CI runs exactly four commands (`.github/workflows/ci.yml`): `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -m "not gamedata"`. CI has **no** OOTP install, **no** save and **no** MySQL, and must never have any of them (ADR 0006). Therefore:

- **A phase proved only by `gamedata` tests has zero CI signal** — a later change can break it and nothing goes red until someone runs the local suite.
- **A phase proved only by offline tests has zero contact with reality.**

So every phase carries at least one of each wherever the subject allows. That is why Phases 5 and 7 add synthetic-buffer walker tests alongside their real-save tests, why the contract tests in Phase 8 were designed to compare two *artifacts* rather than query a database, and why AC15's byte-identity clause is recommended for de-marking.

**Offline (CI-enforced):** `test_config.py`, `test_db_identifiers.py`, `test_save_header.py`, `test_sequential_walk.py`, `test_no_fixed_offsets.py`, `test_parse_teams_synthetic.py`, the offline half of `test_grain_contracts.py`, `test_withheld_fields.py`, the offline half of `test_catalog.py`, plus the four pre-existing guards.

**Gamedata (local only):** `test_save_enumerator.py`, `test_read_only.py`, `test_snapshot_semantics.py`, `test_byte_accounting.py`, `test_names_join.py`, `test_names_join_boston.py`, the per-save names test, `test_parse_real_save.py`, `test_parser_vs_export.py`, `test_extraction_cost.py`, `test_reports.py`, and the gamedata halves of `test_grain_contracts.py` and `test_catalog.py`.

### 3.2 Four validation tiers, each doing a different job

- **Tier A — `players.csv`.** Exact, raw ~1–1000 scale, shipped real players only. The *only* exact rating validator, and — because it carries `FirstName`/`LastName`/`LahmanID` — a **name** validator for **our** league via the `historical_id` join. It is the only tier that touches `OOTP-AI.lg`.
- **Tier B — the probe-save export in `ootp_truth_real`.** Exact for ids, names, strings, dates, roster lists, team dimension and league config. **Bucketed for ratings** and therefore never a rating validator (12 distinct values across 20–80).
- **Tier C — byte accounting.** Strict (zero residual) for `teams.dat` and `names.dat`; diagnostic for `players.dat`. The only check that works on fields with **no** ground truth at all, which is why it earns its place.
- **Mechanical guards.** The AST fixed-offset scan, the category-keyed withheld-field guard, the read-only proof, the `historical_id`-is-not-a-join-key scan, the `quote_ident` regression, the extended leak guard.

### 3.3 Two anti-vacuity rules, both learned from findings in the scope

1. **Every differential test enumerates mismatches per field by name.** An aggregate pass rate is exactly how a parser reading the adjacent u16 ships green.
2. **Any test whose ground truth may be unreachable must skip loudly with a named reason, never pass.** A vacuous green on `test_names_join.py` is worse than a red one. Verify the skip path by temporarily unsetting the truth-database key.

### 3.4 Five guards that must be *seen* to fail

A guard nobody has observed failing is decoration. Break each once, at its own phase boundary, confirm red, revert:

| Phase | Break this | Must go red |
|---|---|---|
| 3 | Add `f.seek(128)` to a parser module | `test_no_fixed_offsets.py` |
| 3 | The in-module fixed-offset negative control | `test_sequential_walk.py` |
| 8 | Change `bronze_team_roster`'s declared key to `(snapshot_date, player_id)` | `test_grain_contracts.py` |
| 9 | Corrupt one parsed field | `test_parser_vs_export.py` — **and it must name that field** |
| 11 | Hand-edit one character of the committed structural catalog | `test_catalog.py` |

### 3.5 Regression safety and sequencing

From Phase 5 onward, **every** phase's acceptance re-runs `test_read_only.py` and `test_no_fixed_offsets.py`. The first is ADR 0001, the one unrecoverable failure in the project; the second is the silent-corruption class CLAUDE.md names as the most likely way to corrupt every downstream recommendation. Checking both at every checkpoint costs seconds and is the difference between finding a violation at a 46 MB copy and finding it after a full parse.

**Every filesystem-touching test runs against the disposable Challenge Mode probe first, and only then against `OOTP-AI.lg`** (SD-20). An identical-mode disposable save sits beside the irreplaceable one; pointing untested code at the managed league first is avoidable exposure. Encode the ordering *in the test modules*, not as prose.

The four pre-existing guards are in the offline suite and therefore re-run at every phase automatically; two of them get **extended rather than replaced** (`test_no_leaks.py` gains the rendered-game-data assertions; the `gamedata` marker declaration is widened rather than duplicated).

### 3.6 What no test here covers — stated so nobody mistakes green for complete

Ratings are entirely outside the tested surface; Phase 2 returns a verdict, not a parser. Tier B can never be an exact rating validator. Standings content is asserted structurally only, because a nonzero-win assertion would fail on a correct parse. Full byte accounting on `players.dat` is diagnostic, not strict. And `world.dat` remains unmapped with no Challenge Mode ground truth — which is why the league-config diff is gated out of this slice.

---

## 4. Risks

Ordered by expected cost, not by likelihood.

1. **`bronze_name`'s key space is unresolved and is this plan's most likely silent-wrongness bug.** Nobody has established whether `names.dat` carries one monotonic index space or two. If it is two and the DDL keys on `(snapshot_date, save_id, name_index)`, the spaces collide and every collided row is silently wrong, with nothing throwing. **Mitigation:** Phase 6 measures it before any DDL is written, and the declared key carries a `NOT NULL` `name_space` discriminator that is correct under both outcomes for the price of one column.

2. **The `names.dat` join is the largest single unknown and sits on the critical path of the headline report.** `docs/data-access.md:238` has the encoding and table layout `unconfirmed`; a roster of integers is not a roster report. **Mitigation:** brute-force against a *full* answer key (score every candidate u32 position across all 18,072 probe players) is bounded and either converges on ~100% or fails cleanly; the pre-registered `players.csv` render-time fallback resolves the ~1,712 Lahman-carrying players with nothing tracked; and the phase is sequenced *before* the players walk so the branch fires at a clean checkpoint rather than mid-report.

3. **`names.dat` content is per-save, and the failure is silent-wrong rather than a crash.** Identical 8,642,110-byte size across three saves, three different SHA-256 digests. A cached probe table applied to the managed league renders plausible wrong names into the GM's roster report. **Mitigation:** the resolver's cache key includes `save_id`, enforced by a structural test rather than by a data coincidence.

4. **The collation default already on disk defeats "exact" string comparison.** `ops/mysql-bootstrap.sql` creates all schemas `utf8mb4_0900_ai_ci` — accent- *and* case-insensitive — while AC7 and AC8 demand exact equality, in a repo whose export was deliberately configured with *Replace accents* Off so names would survive validation. **The failure looks like a pass.** **Mitigation:** compare decoded `str` in Python, or `COLLATE utf8mb4_bin` explicitly, and assert the choice in the test.

5. **The export writes `0` for structural absence on 14 non-MLB league rows.** Without a named per-column allowlist, a correct parse produces 14 false mismatches, and the tempting "fix" commits the exact error the rulebook warns about — wrong numbers, not incomplete ones.

6. **AC10's four clauses collide with an append-only `ingest_run`.** An implementer who does not notice will write a test that cannot pass. Resolved in Phase 8 by keying on `(snapshot_date, save_id)` and refusing a re-land loudly.

7. **`tests/` is the first entry in the builder's deny set.** Hand a phase's whole spec to the data-engineer subagent and its documented behaviour is to stop and report — an Escalation and **zero tests**, costing a whole phase. **Mitigation:** state the ownership split in the *spec*, not only in the plan.

8. **mypy runs strict over `src` *and* `tests`, and no runtime dependency has been chosen.** An unstubbed driver blocks the entire build at the first import; `python-dotenv` sitting dev-only breaks a non-dev install. Settle both in Phase 1, not at Phase 8 with the loader half-written.

9. **Ruff's already-selected rules bite parser code specifically.** `A` forbids `id`/`type`/`bytes`/`list`/`format` as names — all natural in a record walker. `DTZ` makes any naive datetime an error. `PTH` bans `os.path`. None is hard; each is a surprise mid-phase.

10. **Strict byte accounting on `teams.dat` is asserted by the scope, not evidenced.** The only `verified` teams.dat knowledge is the 5-string signature and ARGB colors; `docs/data-access.md:228` covers the rest of a 5.3 MB file as `unconfirmed`. **Mitigation:** the demotion is pre-registered in Phase 0 — do not let a research task gate the request's observable signal.

11. **The `players.dat` population is an inference presented as fact.** AC12's record-count assertion and Phase 11's coverage statements both rest on it. Measure it in Phase 7.

12. **`list_id` value semantics are undocumented and sit on the headline report's critical path.** A wrong human label produces a confidently wrong roster with nothing throwing. Pre-registered opaque-integer fallback.

13. **A bucketed ground truth can green-light a parser reading the adjacent field.** Deferred rather than mitigated: this slice lands no ratings, which is precisely why the scope decoupled them. Keep it that way, and keep Tier A as the permanent exact validator.

14. **The doc-link guard is live-broken in a way this feature's own artifacts trip.** Code spans everywhere; nothing links into `var/`. Do not fix it here — an open bugfix request owns it.

15. **The leak guard is blind to unstaged files.** This feature is the first to render OOTP player data to a file, so the exposure is new and the feedback loop runs the wrong way. Run the guard *after* staging; file the structural fix as a follow-up.

16. **`.gitignore`'s `*.dat` rule does not protect `tests/fixtures/`.** Verified: `!tests/fixtures/**` negates it and git's last-match-wins, so only `test_no_leaks.py:107` stops a committed `.dat` fixture — as a red build. Build fixtures as byte-builder *functions*.

17. **The standings report carries no information today**, and asserting otherwise fails on a correct parse.

18. **Reports regenerate in place unless partitioned** (SD-21) — mitigated at zero cost by the snapshot-dated output path, but note the residual: the tracked catalog's pointer names the *pattern*, not a dated path.

19. **Nobody has run any of this code.** Every cost estimate in the scope is `unconfirmed`, and Phases 5, 6 and 7 each contain a genuine research task. Decisions §6 removes the wall-clock threshold entirely, and each research task carries a pre-registered fallback, so a hard phase **degrades rather than blocks**.

20. **A degraded checkpoint is tempting and wrong.** Merging Phases 5–7 into one "parser" phase because they share a walker pattern means a failure in `players.dat` blocks a green, provable `teams.dat`. Three checkpoints cost three commits and buy three independently revertible units.

---

## 5. Open questions for the operator — settle these before Phase 1

1. **MySQL driver.** Recommendation `PyMySQL` + `types-PyMySQL` (pure Python, MIT, maintained stubs for strict mypy). Alternatives: `mysql-connector-python` (Oracle GPLv2-with-FOSS-exception, ships partial typing) or `mysqlclient` (fastest, C extension, no maintained stubs). Confirm, or state a standing preference.
2. **Phase ordering around the spike.** This plan pre-registers the pivot rule as commit #1 (Phase 0), lands config/deps/DB (Phase 1), then runs the spike (Phase 2). Core §1 says "spike first"; the reading here is that AC18's actual constraint — a verdict committed before any *ratings* code exists, and this slice contains none — is satisfied, while running the spike after the config layer avoids hardcoding paths on the very first artifact and violating Core §2. Confirm, or invert and accept a throwaway hardcoded script under `var/`.
3. **`save_id`'s definition.** Recommendation: the save directory stem (`OOTP-AI`) — stable, human-readable, already public in `gm/` documents, carries no machine-specific path. The alternative (a digest of the header/manifest) is more precise but unreadable in a report. **Confirm before the DDL is emitted; changing it later re-keys every bronze table.**
4. **Where the tracked structural catalog lives.** Recommendation `docs/warehouse-catalog.md` + `.json` (CLAUDE.md forbids speculative directories, so a top-level `catalog/` needs an argument). If `docs/`, decide whether it joins `tests/test_repo_structure.py`'s required-docs list.
5. **De-mark AC15's byte-identity clause from `gamedata`?** It derives from the tracked declaration alone. Recommendation: split AC15 so CI enforces the structural half. This *strengthens* the scope's acceptance rather than weakening it, but it changes what the stage-4 panel checks.
6. **The report/catalog output root.** A third new `.env` key (Core §19 budgeted two) or a fixed subdirectory of `OOTP_SNAPSHOT_ROOT`? AC14 only requires it be git-ignored; both satisfy that. Recommendation: a new key, matching the resolve-by-name convention. Phase 10 needs the answer; Phase 11's tracked pointer records it either way.
7. **The standing-order / ledger-seq ordering.** Decisions §2 makes the ledger row a post-delivery umpire act, while `gm/standing-orders.md:45` requires every entry to carry `**Established:** ledger seq <n>`. This plan lands the two report entries with an explicit engineering-owned marker in place of a seq and leaves the ledger row to the operator. Confirm that is the intended resolution rather than blocking the standing-orders edit until the seq exists.
8. **If Phase 2 returns ABSENT**, do the remaining phases proceed unchanged? The pre-registered pivot says yes. But a FAIL verdict on the mechanic behind ADRs 0012/0014/0016 deserves an explicit go/no-go, and a decision on whether the follow-up request is filed immediately or deferred until a ratings slice is actually proposed.
9. **`bronze_name` re-lands ~264,095 rows per save per snapshot** even though `names.dat` is fixed-size and probably immutable for a save's lifetime. The scope decided `snapshot_date` goes in **every** primary key, so this plan honours that and records the per-snapshot digest in the ingest run, so a later slice can prove immutability and de-snapshot it cheaply. Flagging the storage number, not re-litigating the decision.
10. **A note on the task brief:** it names `docs/data-sources.md` as the source-coverage document. **That file does not exist** — `docs/` contains exactly `data-access.md` and `league-rules.md`. This plan treats `docs/data-access.md` as the intended file and honours the brief's rule literally: every `unconfirmed` claim it depends on is verified by a phase *before* the phases that build on it (the scouted view in Phase 2, `saved_games.dat`'s plaintext claim in Phase 4, the `names.dat` encoding in Phase 6). Confirm the substitution before implementation starts.

---

## Raw planner proposals

---

## Lens: (unnamed lens)

### planner

code-grounded

### ok

```json
true
```

### onboarding_files

```json
{
    "path":  "requests/feature-requests/first-sight/PROJECT_SCOPE.md",
    "why":  "The decided upstream artifact. Acceptance Criteria 1-21 are the contract; Scope (tiered) Core 1-21 is the work list; Decisions 1-11 are already settled and must not be re-opened. Note its own citation convention at :5-9 (code spans, not Markdown links, for file:line and var/ targets) — the plan and every artifact this feature creates must follow it or tests/test_doc_links.py goes red."
}
```
```json
{
    "path":  ".claude/agents/data-engineer.md",
    "why":  "The single owner of the build rules and the binding contract for the implementation subagent. Load-bearing: :69 fixed-offset ban, :89 no parents[N] walk outside test modules, :91 never require a game install for a test, :98 bronze is 1:1 with parser output, :101 grain declared in prose AND proven, :150 tests/ is in the hard deny set, :157 nothing under the OOTP install or saved-games dir, :206-224 the return contract."
}
```
```json
{
    "path":  "docs/data-access.md",
    "why":  "The format catalog, with epistemic labels that are load-bearing. :36-38 saved_games.dat claimed plaintext+verified (the scope corrects this); :60-63 the stray empty `.lg` directory that breaks a glob-based enumerator; :65-68 challenge.dat at 241 bytes; :169-190 the byte-exact header layout and the offset-1 magic trap; :193-201 the primitives table; :204-215 variable-length regions; :224-226 the verified teams.dat 5-string signature; :234-239 name indirection with the encoding `unconfirmed`; :282 the critical-path unknown; :292-295 the spike test text, never run."
}
```
```json
{
    "path":  "pyproject.toml",
    "why":  "Every toolchain constraint the implementer trips over on day one. :9 `dependencies = []` (no runtime deps chosen yet — SD-14); :11-15 a tracked comment asserting the first dependency arrives with the warehouse loader, which this feature makes true and must update; :56-59 ruff selects DTZ (naive datetimes are errors) and PTH (pathlib only) and A (builtin shadowing — a real hazard in parser code); :69-73 mypy strict over BOTH src and tests; :78-81 `--strict-markers` with exactly one marker, `gamedata`, whose declaration this scope widens."
}
```
```json
{
    "path":  "tests/test_no_leaks.py",
    "why":  "The guard that decides what a fixture may be. :24-28 the leak PATTERNS; :31-48 tracked_text_files() enumerates via `git ls-files`, so an untracked artifact is invisible to it locally (the known gap the scope\u0027s Folded-in 1 names); :97-116 test_game_data_is_not_tracked bans the filenames players.csv/names.xml/world_default.xml/schools.xml and the suffixes .dat/.lg for any tracked path — which is why no fixture may be named *.dat."
}
```
```json
{
    "path":  "tests/fixtures/README.md",
    "why":  "What a fixture is allowed to contain (:14-24 the authorship test, :30-37 what belongs) and why synthetic beats real (:45-51 — a day-0 save is the least informative input because every variable-length region is at its minimum, which is exactly the condition a fixed-offset reader passes)."
}
```
```json
{
    "path":  "ops/mysql-bootstrap.sql",
    "why":  "The warehouse\u0027s actual DDL posture. :23-24 creates `ootp` with COLLATE utf8mb4_0900_ai_ci — accent-INSENSITIVE and case-insensitive, which silently makes an \u0027exact\u0027 name comparison non-exact (this is SD-13\u0027s collation decision, and it has a concrete wrong default already on disk). :30-33 and :47-49 create and grant `ootp_truth_osa`, the schema Decisions 10 retires."
}
```
```json
{
    "path":  ".env.example",
    "why":  "The config surface. :10/:16/:20/:25 the four OOTP keys (:25 documents a `var/snapshots` default that the config layer must produce WITHOUT a parents[N] walk); :51 MYSQL_DATABASE=ootp; :57-58 the two truth schemas, one of which is being retired. Two-to-three new keys land here."
}
```
```json
{
    "path":  ".github/workflows/ci.yml",
    "why":  "CI\u0027s actual condition — :37-49 runs ruff check, ruff format --check, mypy, then `pytest -m \"not gamedata\"`. Anything not runnable offline with no MySQL and no game install must carry the gamedata marker or it breaks the build."
}
```
```json
{
    "path":  "gm/standing-orders.md",
    "why":  "The tracked half of the report channel. :27-50 is the `## Reports` section and its per-report format block, which Decisions 4 requires an umpire to extend with an engineering-owned report kind before the two report entries can be written honestly (no analyst exists — gm/staff.md:5-8 says so)."
}
```
```json
{
    "path":  ".claude/agents/gm.md",
    "why":  "The entire delivery surface for this feature: :4 grants exactly `tools: Read, Glob`, and :32 forced-read item 8 is \u0027Any report or analysis handed to you for this invocation\u0027. Acceptance criterion 20 is a spawn of this agent with the two reports in context."
}
```
```json
{
    "path":  "docs/league-rules.md",
    "why":  "The documentation correction target. :129 and :295 both assert a `leagues.dat` that does not exist (grep-confirmed, both lines); :26 and :30-31 claim the warehouse supersedes §1 \u0027the moment the parser lands\u0027, which this slice partially falsifies; :79-81 records `schedule_file_1 = major_league_ml_c_2024.lsdl`, the string the scope measured inside world.dat."
}
```
```json
{
    "path":  "requests/feature-requests/README.md",
    "why":  "The handoff interface. :70-85 defines what \u0027testable\u0027 means here (one command, pass or fail) and requires human-only criteria to be marked USER-RUN so the stage-4 acceptance panel does not claim them — criteria 20 and 21 are those."
}
```

### architecture_notes

CURRENT STATE OF THE TOUCHED AREA — measured, not assumed.

`src/ootp_ai/` contains exactly one file: `__init__.py`, 7 lines, a docstring and `__version__ = "0.1.0"` (src/ootp_ai/__init__.py:7). There is no parser, no config layer, no loader, no renderer, no catalog. `transform/`, `build/`, `datasets/` do not exist and this feature deliberately does not create them (scope Non-Goals). `tests/` holds four structural guards and no parser test. `pyproject.toml:9` declares zero runtime dependencies. So this is a from-nothing build against a fully-specified set of invariants — the risk is not "does it fit the existing code", it is "does it satisfy the rulebook the first time".

THE SEAMS, and where each hooks in.

1) CONFIG SEAM — `src/ootp_ai/config.py`, new. A frozen dataclass `Settings` plus `load_settings()` that reads `.env` (python-dotenv, currently a dev-only dep at pyproject.toml:23 and must move to `[project] dependencies`) and returns resolved `Path`s. Every other module takes `Settings` as an argument; nothing else touches `os.environ`. The trap: `.env.example:25` promises OOTP_SNAPSHOT_ROOT "Defaults to var/snapshots", while `.claude/agents/data-engineer.md:89` bans a `parents[N]` walk outside test modules. Resolve the default as a CWD-relative `Path("var/snapshots")`, never via `Path(__file__).parents[...]`, and validate it: creatable, and not underneath the `OneDrive` environment variable's value (data-access.md:56-58 warns snapshots on cloud-synced storage are a mistake).

2) SAVE-DISCOVERY SEAM — `src/ootp_ai/saves.py`, new. `enumerate_saves(settings)` must confirm `players.dat` AND `teams.dat` are present inside a candidate directory rather than trusting a `*.lg` glob (data-access.md:60-63 records a stray, empty directory literally named `.lg`). `detect_challenge_mode(dir)` checks `challenge.dat` exists at exactly 241 bytes (data-access.md:65-68). Both are pre-flight, run on every invocation (Folded-in 6).

3) SNAPSHOT SEAM — `src/ootp_ai/snapshot.py`, new. Copies only the in-scope files (`teams.dat`, `players.dat`, `names.dat` — ~46 MB, not the ~600 MB `.lg`) to `<snapshot_root>/<league>/<sim_date>/` with a per-file size + SHA-256 manifest, every handle opened `"rb"`. All parsing runs against the snapshot copy, never the live save — this is what makes the read-only proof cheap and makes history re-parseable without the game (data-engineer.md:86-87).

4) PARSER SEAM — `src/ootp_ai/parser/`, new package. The load-bearing design choice: a `Cursor` over an in-memory `bytes` (`Path.read_bytes()`; 32 MB is trivially affordable) with advancing readers — `u8/u16/u32/f64`, `string()` (u32-LE length prefix, raw ASCII, no terminator — data-access.md:195), `date()` (u8 day, u8 month, u16 year — :196), `color()` (u32 ARGB — :197). No file object is ever seeked, so acceptance criterion 3's static scan for `.seek(<nonzero literal>)` is satisfiable by construction rather than by discipline. `struct.unpack_from` is called only with `cursor.offset`, a variable — the guard's second clause. Modules: `primitives.py`, `header.py` (with `UnsupportedSaveVersion`, named exactly as criterion 1 requires), `teams.py`, `players.py`, `names.py`, `rosters.py`, `saved_games.py`.

5) CONTRACT-DECLARATION SEAM — `src/ootp_ai/contracts/` with a tracked `field_map.toml` and `tables.toml` (read via stdlib `tomllib`, no new dependency). This is the single declaration with THREE consumers, which is what makes prose-vs-enforcement drift structurally impossible: (a) `warehouse/ddl.py` emits the CREATE TABLE and primary keys from it, (b) `tests/test_grain_contracts.py` reads it and compares its prose grain sentence to the emitted key, (c) `catalog/` renders it. Per field it carries name, type, source .dat, the walker function that reads it, `category` ∈ {identity, rating-true, rating-scouted, contract, structural}, `epistemic` ∈ {measured, verified, inferred, assumed, unconfirmed}, and the validator tier that produced the label. `contracts/policy.py` exposes the one function every serving path goes through: `is_renderable(field)` — false when `category == "rating-true"` or `epistemic in {"unconfirmed", "assumed"}` (ADR 0012:75-76: an unclassified rating field is withheld, "probably fine" is not a classification).

6) WAREHOUSE SEAM — `src/ootp_ai/warehouse/`. `connection.py` (PyMySQL, opened read-write only against `MYSQL_DATABASE`), `ddl.py` (generated from the declaration), `load.py` (bronze, 1:1 with parser output — typing, casing, dedup only, no joins, no filtering, no renaming; data-engineer.md:98), `ingest_run.py`, `sql.py` (a `quote_ident()` that backticks every identifier — Folded-in 2's measured incident: `select current_date from ootp_truth_real.leagues` returns the wall-clock date because MySQL parses the bare column name as the CURRENT_DATE function, and nothing errors). Tables: `bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name`, `bronze_field_label` (Folded-in 5), `bronze_ingest_run`. Every primary key carries `snapshot_date` AND `save_id` — the pipeline parses two different universes (OOTP-AI and the probe) and a key without `save_id` collides them.

7) SERVING SEAM — `src/ootp_ai/reports/` with a `__main__.py` (criterion 14 invokes `python -m ootp_ai.reports render`, which requires the package-plus-`__main__` shape, not a flat module) and `src/ootp_ai/catalog/__main__.py` (criterion 15 invokes `python -m ootp_ai.catalog`). Both write into a git-ignored root under `var/` (.gitignore:18). The org filter lives HERE, not at bronze.

8) TRACKED-DOC SEAM — the catalog splits (Decisions 3): the structural half is a tracked Markdown file generated from the contract declaration alone (so it regenerates offline, with no MySQL, and can be asserted byte-identical to the committed copy); the volatile half — row counts, snapshot dates, freshness — plus `catalog.json` generate into the ignored root. The tracked half may name source FILES (`players.dat`) but never absolute paths, because `saved_games.dat` embeds an absolute user-profile path per save and rendering it into a tracked file publishes a username to a public repo.

OWNERSHIP SPLIT, which the plan must enforce mechanically at spawn time. `tests/` is in the data-engineer's hard deny set (`.claude/agents/data-engineer.md:150`), and so are `ops/`, `.github/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md`, `docs/decisions/`. Therefore: the implementation subagent's spec declares ONLY `src/ootp_ai/**` (including the TOML declarations) and `requests/feature-requests/first-sight/reviews/**` as target paths. Everything under `tests/`, plus `docs/`, `ops/mysql-bootstrap.sql`, `.env.example`, `gm/standing-orders.md` and `pyproject.toml`, is authored by the main thread. Handing the whole spec over produces an Escalation and zero tests (scope Risk 8).

### phases

```json
{
    "name":  "Phase 1 — Pre-register the pivot rule, then run the scouted-view spike",
    "goal":  "Answer docs/data-access.md:282\u0027s critical-path unknown — is the scouted view stored or computed at render time — with a written verdict, an epistemic label and byte evidence, BEFORE any parser code exists. Scope Goal 8, acceptance criterion 18.",
    "steps":  [
                  "Write `requests/feature-requests/first-sight/reviews/spike-pivot-rule.md` FIRST, naming what FOUND and ABSENT each trigger: FOUND -\u003e ratings get a source and a later slice may parse them; ABSENT -\u003e record it, withhold every rating, ship both reports anyway and file a follow-up request against ADRs 0012/0014/0016. Commit this before running anything — a pivot rule written after the result is not a pivot rule.",
                  "Run the spike as a throwaway script under the gitignored scratch root (`var/`), never as tracked code: read the RETAINED STANDARD-MODE probe save\u0027s `scouting.dat` (2,349,181 B) into memory, pull `ootp_truth_real.players_scouted_ratings` (36,144 rows, `scouting_coach_id` in {-1, 2759}, 18,072 each), and search for the exported scouted values as u16 little-endian runs positioned consistently across players. This is the test written verbatim at docs/data-access.md:292-295 and never run.",
                  "Cross-check the negative case: confirm the same search against `players.csv`-derived TRUE values behaves differently, so a FOUND verdict is not just \u0027the file contains numbers in range\u0027.",
                  "Write `requests/feature-requests/first-sight/reviews/spike-scouted-view.md`: verdict (stored | computed | inconclusive), epistemic label, the byte evidence (file, offsets, the player ids checked), and the pivot actually taken.",
                  "Prepare a docs-delta line for `/update-docs` upgrading or explicitly reaffirming docs/data-access.md:282\u0027s `unconfirmed` label — do NOT edit that file directly; it is in the data-engineer deny set (data-engineer.md:156) and routes through the doc gate."
              ],
    "acceptance":  [
                       "`requests/feature-requests/first-sight/reviews/spike-pivot-rule.md` exists and is committed in an earlier commit than the verdict file (`git log --oneline -- \u003cboth paths\u003e` shows the ordering).",
                       "`requests/feature-requests/first-sight/reviews/spike-scouted-view.md` states stored-or-computed with one of the five epistemic labels and cites concrete byte evidence, not an impression.",
                       "No file under `src/ootp_ai/` has been created yet — `git ls-files src/ootp_ai` still lists only `__init__.py`.",
                       "The spike script lives under `var/` and is not tracked: `git check-ignore -q` on its path exits 0."
                   ],
    "commit_note":  "Two commits, in this order: (1) \u0027Pre-register the scouted-view pivot rule before the spike runs\u0027; (2) \u0027Record the scouted-view spike verdict\u0027. Both through /commit. The ordering IS the evidence for acceptance criterion 18."
}
```
```json
{
    "name":  "Phase 2 — Toolchain, config layer, save enumeration, snapshot, and the read-only proof",
    "goal":  "Stand up the dependency and config spine, make the pipeline able to find and copy a save without ever opening it for writing, and prove ADR 0001 with a test rather than a promise. Scope Core 2, 3, 5; acceptance criteria 11 and 16.",
    "steps":  [
                  "MAIN THREAD: choose and land the first runtime dependencies in `pyproject.toml`. Move `python-dotenv` from the dev group (currently pyproject.toml:23) into `[project] dependencies`, and add `PyMySQL` there plus `types-PyMySQL` to the dev group — mypy runs strict over `src` (pyproject.toml:69-73) and an unstubbed driver fails it. Do NOT pick `mysqlclient` (C extension, needs a Windows toolchain). Update the now-false tracked comment at pyproject.toml:11-15.",
                  "MAIN THREAD: widen the single declared marker at pyproject.toml:80 to \u0027requires a local OOTP install, save, or warehouse\u0027. `addopts` carries `--strict-markers` (pyproject.toml:78), so a second undeclared marker is a hard collection error — widen, do not add.",
                  "MAIN THREAD: add the new `.env.example` keys — the retained standard-mode probe save and the disposable Challenge Mode probe save (both a directory and a league name, so neither is hardcoded), plus a report/catalog output root key defaulting under `var/`. Remove `MYSQL_TRUTH_OSA_DATABASE` (.env.example:58) and the `ootp_truth_osa` create/grant at ops/mysql-bootstrap.sql:32-33 and :49 (Decisions 10; `ops/` is deny-set for the builder).",
                  "BUILDER: `src/ootp_ai/config.py` — frozen `Settings` dataclass + `load_settings()`. Every path resolves from `.env`; no literal path, no `parents[N]` walk (data-engineer.md:89). Snapshot root default is a CWD-relative `Path(\"var/snapshots\")`, validated creatable and rejected if it sits under the `OneDrive` environment variable\u0027s value.",
                  "BUILDER: `src/ootp_ai/saves.py` — `enumerate_saves()` requires BOTH `players.dat` and `teams.dat` inside a candidate directory (a `*.lg` glob is not a list of saves; data-access.md:60-63). `assert_challenge_mode()` checks `challenge.dat` is present at exactly 241 bytes (data-access.md:65-68).",
                  "BUILDER: `src/ootp_ai/snapshot.py` — `take_snapshot(settings, save)` copies ONLY `teams.dat`, `players.dat`, `names.dat` into `\u003croot\u003e/\u003cleague\u003e/\u003csim_date\u003e/`, writes a `manifest.json` of per-file size + SHA-256, opens every handle `\"rb\"`, and refuses to overwrite an existing snapshot directory.",
                  "MAIN THREAD: `tests/test_config.py` (offline — monkeypatched environment, no game install), and `tests/test_read_only.py` (`-m gamedata`) which builds a pre-run manifest of size + mtime_ns + SHA-256 over `$OOTP_SAVED_GAMES/\u003csave\u003e.lg` and `$OOTP_INSTALL/data/database`, runs the full pipeline entry point, re-manifests, and diffs. Per SD-20 it runs against the DISPOSABLE Challenge Mode probe save first and only then against `OOTP-AI.lg`."
              ],
    "acceptance":  [
                       "`uv run pytest -m \"not gamedata\"` green with no game install and no MySQL; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all clean (acceptance criterion 16).",
                       "`uv run pytest -m gamedata tests/test_read_only.py` green — zero mtime and zero digest differences, on the probe save first and OOTP-AI.lg second (criterion 11).",
                       "A snapshot directory appears under the resolved snapshot root with a manifest whose digests match the source files, and `git check-ignore -q` on that directory exits 0.",
                       "`tests/test_no_leaks.py`, `tests/test_repo_structure.py`, `tests/test_agent_contract.py`, `tests/test_doc_links.py` all still green."
                   ],
    "commit_note":  "\u0027Land the config, save-enumeration and snapshot spine, with a read-only proof for ADR 0001\u0027. Through /commit. This is the first commit that adds a runtime dependency — expect /commit\u0027s doc gate to ask about README setup text and pyproject\u0027s dependency comment."
}
```
```json
{
    "name":  "Phase 3 — Primitives, the header/version guard, and the two mechanical parser guards",
    "goal":  "Establish the parser\u0027s spine so that seeking to a fixed offset is impossible by construction rather than by review, and so an unrecognized save version raises instead of misparsing. Scope Core 4, Goal 3, Goal 9; acceptance criteria 1, 2, 3.",
    "steps":  [
                  "BUILDER: `src/ootp_ai/parser/primitives.py` — a `Cursor` over an in-memory `bytes` with advancing readers `u8/u16/u32/i32/f64`, `string()` (u32-LE length prefix, raw ASCII, no terminator — docs/data-access.md:195), `date()` (u8 day, u8 month, u16 year — :196), `color()` (u32 ARGB — :197), `skip(n)`, `remaining()`. It exposes NO absolute-positioning method. Files are read whole with `Path.read_bytes()`; no file object is ever seeked.",
                  "BUILDER: `src/ootp_ai/parser/header.py` — `read_header(cursor, expected_filename)` asserting byte 0 == 0x00, `b\"OOTP\"` at offset 1, u32 version at offset 5, then the four u32s and the null-padded self-declared filename at offset 25 (docs/data-access.md:172-181). Raises `UnsupportedSaveVersion` (this exact class name is pinned by criterion 1) when version != 25, and a distinct `SaveFilenameMismatch` when the self-declared name disagrees with the file actually opened. Refuse strictly — a loud failure is recoverable, a silent misparse is not (data-engineer.md:83-84).",
                  "BUILDER: `src/ootp_ai/contracts/` skeleton — `tables.toml` and `field_map.toml` with the schema described in the architecture map, plus `contracts/loader.py` (tomllib) and `contracts/policy.py::is_renderable()`. Populate only what phase 3 knows; later phases append.",
                  "MAIN THREAD: `tests/fixtures/synthetic.py` — a MODULE of byte builders, not data files (`make_header(version=..., filename=...)`, `make_record(contract_years=...)`). Building bytes in code sidesteps the .dat-extension ban at tests/test_no_leaks.py:106-107 entirely and matches tests/fixtures/README.md:32-37.",
                  "MAIN THREAD: `tests/test_save_header.py` (offline) — a valid v25 header parses; version 24 and version 26 each raise `UnsupportedSaveVersion`; a buffer with `b\"OOTP\"` at offset 0 is REJECTED (the offset-1 trap, data-access.md:183-186); a header whose self-declared filename disagrees with the opened file is rejected.",
                  "MAIN THREAD: `tests/test_sequential_walk.py` (offline) — two synthetic records identical except for the length of a variable-length region (a 1-year vs a 10-year contract array) must yield identical values for every field parsed AFTER that region. A fixed-offset reader cannot pass this.",
                  "MAIN THREAD: `tests/test_no_fixed_offsets.py` (offline) — an `ast`-based scan over every `.py` under `src/ootp_ai/parser/` asserting zero `.seek(\u003cnonzero int literal\u003e)` calls and zero `struct.unpack_from` with a constant int third argument. This encodes data-engineer.md:69-74 as a check rather than a convention."
              ],
    "acceptance":  [
                       "`uv run pytest tests/test_save_header.py tests/test_sequential_walk.py tests/test_no_fixed_offsets.py` green OFFLINE — no game install, no MySQL (criteria 1, 2, 3).",
                       "`git ls-files tests/fixtures` lists no path whose suffix is `.dat` or `.lg`.",
                       "`uv run mypy` clean over the new parser package under strict mode."
                   ],
    "commit_note":  "\u0027Parser spine: cursor primitives, a strict header/version guard, and the fixed-offset scan\u0027. Through /commit."
}
```
```json
{
    "name":  "Phase 4 — Sequential teams.dat walk, the roster-list grain, and save provenance",
    "goal":  "Extract the team dimension and the roster membership grain — the fan-out that bites today, on an unsimmed save, with no trade in sight — and pin which universe a parse describes. Scope Core 6, 9, Folded-in 7; feeds acceptance criteria 5, 9, 12.",
    "steps":  [
                  "BUILDER: `src/ootp_ai/parser/teams.py` — sequential walk yielding `team_id`, the verified 5-string signature (city, abbreviation, nickname, logo filename, full name — docs/data-access.md:224-226), ARGB colors, level, `parent_team_id`, the sub-league/division hierarchy, and the win/loss fields the standings report needs. Record byte accounting as the walk proceeds.",
                  "BUILDER: `src/ootp_ai/parser/rosters.py` — roster-list extraction at the `(team_id, player_id, list_id)` grain. Empirically derive what each `list_id` VALUE means by comparing against `ootp_truth_real.team_roster` (15,672 rows over 7,370 distinct players, `list_id` distribution {1: 7370, 2: 7037, 3: 935, 4: 330}). PRE-REGISTERED FALLBACK (SD-17): if the mapping cannot reach at least `inferred`, land `list_id` as an opaque integer and record that label — the report layer is then forbidden from printing a human label for it.",
                  "BUILDER: `src/ootp_ai/parser/saved_games.py` — read `$OOTP_SAVED_GAMES/saved_games.dat` through the SAME header reader plus a length-prefixed string walk. It is NOT plaintext, contrary to docs/data-access.md:36-38\u0027s `verified` claim; never substring-scrape it. Extract each save\u0027s sim date and human team. Resolve the human team from data on every run — never hardcode \u0027we are team 6\u0027 (OOTP-AI is Boston at 2024-03-07; the probe is the Chicago Cubs at 2024-03-18, so a hardcode passes on ground truth and breaks on our league, invisibly).",
                  "BUILDER: append every landed teams/roster field to `field_map.toml` with its category, epistemic label and the validator tier that produced it.",
                  "MAIN THREAD: `tests/test_parse_teams.py` (`-m gamedata`) — exactly 30 teams at MLB level with correct abbreviations; 259 teams total against the probe save; `team_id` unique per snapshot.",
                  "MAIN THREAD: `tests/test_byte_accounting.py` (`-m gamedata`), strict tier for `teams.dat` only — zero unaccounted bytes. If the strict tier proves unreachable, DEMOTE teams.dat to the diagnostic tier (record the residual, assert a record-boundary termination) and file a follow-up rather than blocking the slice; write the demotion and its reason into the field map\u0027s tier rationale."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parse_teams.py` green: 30 MLB clubs with correct abbreviations from OOTP-AI.lg, 259 teams from the probe save, `team_id` unique per snapshot.",
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py -k teams` green at whichever tier the field map declares, and the declared tier matches what the test actually asserts.",
                       "The parsed human team for OOTP-AI is Boston and for the probe save is the Chicago Cubs, both read from `saved_games.dat` rather than configured.",
                       "`field_map.toml` carries an entry for every landed teams/roster field, each with a category and an epistemic label."
                   ],
    "commit_note":  "\u0027Walk teams.dat sequentially, extract the roster-membership grain, and resolve save provenance from data\u0027. Through /commit."
}
```
```json
{
    "name":  "Phase 5 — Sequential players.dat walk with a deliberately minimal field set",
    "goal":  "Land the smallest player field set the two reports actually need, with diagnostic byte accounting. Every landed field is a maintenance liability somebody re-validates after a game patch, so the field set is deliberately narrow. Scope Core 7, 12; feeds criteria 9 and 12.",
    "steps":  [
                  "BUILDER: `src/ootp_ai/parser/players.py` — sequential walk yielding `player_id`, team/organization assignment, position, uniform number, date of birth, bats/throws, the name INDICES (unresolved at this phase), and `historical_id` (the Lahman/BBRef string, docs/data-access.md:99-102, `verified`). Nothing else. No ratings, no `prone_*`, no `players_value.*`.",
                  "BUILDER: byte accounting at the DIAGNOSTIC tier for players.dat per blocker F3 — assert the walk terminates on a record boundary and reaches a record count matching an independent count (the probe export\u0027s `retired = 0` population, 18,072), and RECORD the residual byte count rather than asserting it is zero. Full byte accounting on a 32 MB players.dat is a research task, not a counter; say so in the tier rationale.",
                  "BUILDER: on OOTP-AI.lg there is no export, so the independent count is unavailable — the check degrades to record-boundary termination plus the Boston roster sanity check in phase 8. Encode that degradation explicitly rather than silently skipping.",
                  "BUILDER: append every landed player field to `field_map.toml`. Anything the walk crosses but cannot classify is recorded with category `rating-true` and epistemic `unconfirmed` — the withhold-by-default posture ADR 0012:75-76 requires.",
                  "MAIN THREAD: extend `tests/test_sequential_walk.py` with a synthetic player-shaped record carrying a 1-year vs a 10-year contract array, asserting `historical_id` (which sits after the variable region) reads identically in both."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py -k players` green: the walk terminates on a record boundary, the probe-save record count equals 18,072, and the residual byte count is recorded (not asserted zero).",
                       "`uv run pytest tests/test_sequential_walk.py` still green offline with the player-shaped record added.",
                       "`uv run pytest tests/test_no_fixed_offsets.py` green — the new module introduced no seek and no constant-offset unpack.",
                       "No rating field, no `prone_*`, no `players_value.*` appears anywhere in `field_map.toml` as renderable."
                   ],
    "commit_note":  "\u0027Walk players.dat sequentially with a minimal field set and diagnostic byte accounting\u0027. Through /commit."
}
```
```json
{
    "name":  "Phase 6 — Resolve the names.dat join against two independent answer keys",
    "goal":  "Turn a roster of integers into a roster of names, and prove it against a full answer key rather than an impression. docs/data-access.md:238 has this `unconfirmed` and the scope calls it the largest single unknown. Scope Core 8, 17, Goal 4; acceptance criteria 7 and 8.",
    "steps":  [
                  "BUILDER: `src/ootp_ai/parser/names.py` — walk `names.dat` on the observed record shape (u32 len + ASCII + u32 0 + u32 monotonic index + three u32s + a 0x27 separator, alphabetically ordered) into an index -\u003e string table. Strict byte accounting applies here (zero residual).",
                  "BUILDER: resolve WHICH u32 fields in the player record are the name indices by brute force against a full answer key, not by guessing: for each candidate u32 position the walk exposes, apply the mapping across all 18,072 probe-save players and score exact matches against `ootp_truth_real.players.first_name`/`.last_name`. The correct index field scores ~100%; everything else scores near zero. Record the winning position and its score in `field_map.toml`.",
                  "BUILDER: guard the per-save constraint (SD-10). `names.dat` is 8,642,110 bytes in all three saves on disk with THREE different SHA-256 digests — a fixed-size, per-save-populated table. Nothing may carry a name index, an index-\u003estring expectation, or a cached name table from the probe save into the managed league. The name table is loaded per snapshot, from that snapshot\u0027s own file.",
                  "BUILDER: implement the pre-registered fallback (Decisions 5) behind a flag — if the join resists, resolve names at RENDER time from `players.csv` via the `LahmanID` \u003c-\u003e `historical_id` join for the ~1,712 real players, fictional players render as IDs, and nothing is tracked. HARD BIND: never write a Lahman-to-name lookup to a tracked file. tests/test_no_leaks.py:106 catches `players.csv` by FILENAME only, so a renamed copy sails straight through into a public repo.",
                  "MAIN THREAD: `tests/test_names_join.py` (`-m gamedata`, Tier B) — every name index the parser resolves out of the probe save matches `ootp_truth_real.players.first_name`/`.last_name` by exact string equality, 100% of compared rows, zero unresolved indices, every failure enumerated BY NAME (never an aggregate pass rate). It must SKIP LOUDLY with a named reason if `ootp_truth_real` is unreachable — a vacuous pass here is worse than a failure.",
                  "MAIN THREAD: `tests/test_names_join_boston.py` (`-m gamedata`, Tier A) — for every player in OOTP-AI.lg carrying a non-empty `historical_id`, the names.dat-resolved first/last name equals `players.csv`\u0027s `FirstName`/`LastName` joined on `LahmanID`, 100% exact. This is the only validation of the join on the league we actually manage. Parse `players.csv` with stdlib `csv`, stripping the `//` prefix from its header line (docs/data-access.md:79-80).",
                  "MAIN THREAD: settle the collation explicitly (SD-13). `ops/mysql-bootstrap.sql:24` creates the schemas with `utf8mb4_0900_ai_ci` — accent- AND case-INSENSITIVE — so an \u0027exact\u0027 comparison performed in SQL is not exact. Fetch both sides into Python and compare `str == str`; where SQL-side comparison is unavoidable, append `COLLATE utf8mb4_0900_bin` explicitly. Assert the chosen collation in the test so a schema change surfaces.",
                  "MAIN THREAD: `tests/test_names_per_save.py` (`-m gamedata`) — resolving the SAME index in the probe save and in OOTP-AI.lg is asserted NOT to be expected to yield the same string, pinning the per-save finding as a test rather than a comment."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_names_join.py` green: 100% exact match, zero unresolved indices, failures enumerated per row; it skips loudly (never passes vacuously) when `ootp_truth_real` is unreachable.",
                       "`uv run pytest -m gamedata tests/test_names_join_boston.py` green against OOTP-AI.lg for every player carrying a `historical_id` (criterion 8).",
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py -k names` green at the STRICT tier — zero unaccounted bytes in names.dat.",
                       "`git ls-files` lists no file containing a Lahman-ID-to-name lookup, and `uv run pytest tests/test_no_leaks.py` is green.",
                       "`field_map.toml` records the name-index field positions with a validator tier and an upgraded epistemic label."
                   ],
    "commit_note":  "\u0027Resolve the names.dat join against both answer keys, with the per-save constraint pinned by test\u0027. Through /commit. This is the commit that turns the roster from integers into people — the request\u0027s observable signal depends on it."
}
```
```json
{
    "name":  "Phase 7 — Bronze landing, the five contracts, snapshot semantics and extraction cost",
    "goal":  "Land parser output into the empty `ootp` schema, 1:1, append-only, idempotent per snapshot, with `snapshot_date` AND `save_id` in every primary key — and make the prose grain and the enforced key structurally unable to drift. Scope Core 10, 11, 12; acceptance criteria 4, 5, 10, 17.",
    "steps":  [
                  "BUILDER: complete `src/ootp_ai/contracts/tables.toml` with the four bronze tables and their declared keys — `bronze_team` (snapshot_date, save_id, team_id); `bronze_player` (snapshot_date, save_id, player_id); `bronze_team_roster` (snapshot_date, save_id, team_id, player_id, list_id) — NOT (snapshot_date, player_id); `bronze_name` with its own declared grain, key and coverage like every other table (SD-10 / finding F10). `save_id` is required by SD-09: the pipeline parses two different universes and a key without it collides them.",
                  "BUILDER: `src/ootp_ai/warehouse/ddl.py` emits CREATE TABLE and PRIMARY KEY from `tables.toml` — the DDL is never hand-written, so the declaration is the only place a key exists.",
                  "BUILDER: `src/ootp_ai/warehouse/load.py` — bronze is 1:1 with parser output: typing, casing, dedup only. No joins, no filtering, no semantic renaming (data-engineer.md:98). Land EVERYTHING the walk yields including the minors; the org filter lives in the report layer (Decisions 7). Preserve structural absence as NULL, never zero — the export writes `0` for `rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows, which is 14 separate opportunities to commit this error.",
                  "BUILDER: `src/ootp_ai/warehouse/ingest_run.py` — one row per snapshot recording source file sizes, SHA-256 digests, header versions, sim date, human team, per-table row counts, residual bytes and wall-clock parse seconds. Use `datetime.now(UTC)` for any wall-clock stamp; ruff\u0027s DTZ rule (pyproject.toml:57) makes a naive datetime a lint error, deliberately.",
                  "BUILDER: `bronze_field_label` (Folded-in 5) — each landed field\u0027s epistemic label written into the warehouse alongside the data, so a future incident can ask \u0027what did we believe about this field the day it landed\u0027 as a query instead of archaeology through git history.",
                  "BUILDER: idempotency — `bronze_ingest_run` carries UNIQUE(save_id, snapshot_date); re-landing an existing snapshot raises rather than silently overwriting. `dump_parse(path)` writes a deterministic, key-sorted serialization so \u0027parsing twice is byte-identical\u0027 is testable by hashing.",
                  "MAIN THREAD: `tests/test_grain_contracts.py` — the OFFLINE half reads `tables.toml` and the DDL the loader emits and asserts the prose grain sentence equals the emitted key (data-engineer.md:101, prose and enforcement cannot drift). The `-m gamedata` half, `test_roster_grain_is_not_player_grain`, POSITIVELY asserts `player_id` is NOT unique within one snapshot\u0027s roster rows, and that `count(distinct player_id)` in `bronze_team_roster` is materially less than `count(*)` in `bronze_player` for the same snapshot. Ground truth for the shape: 15,672 roster rows over 7,370 distinct players.",
                  "MAIN THREAD: `tests/test_snapshot_semantics.py` (`-m gamedata`) — loading the same snapshot twice leaves per-table row counts and checksums unchanged; loading a second `snapshot_date` leaves the first snapshot\u0027s rows bit-identical; parsing the same snapshot twice produces byte-identical parser output; re-landing an existing snapshot id does not silently overwrite it.",
                  "MAIN THREAD: `tests/test_extraction_cost.py` (`-m gamedata`) — asserts the wall-clock number EXISTS and was recorded into the ingest-run row. There is no threshold and no pass/fail on duration (Decisions 6: the operator ruled the work takes as long as it needs; the tautology objection is accepted deliberately)."
              ],
    "acceptance":  [
                       "`uv run pytest tests/test_grain_contracts.py -m \"not gamedata\"` green OFFLINE — prose grain equals emitted key for all four tables (criterion 4).",
                       "`uv run pytest -m gamedata tests/test_grain_contracts.py::test_roster_grain_is_not_player_grain` green (criterion 5).",
                       "`uv run pytest -m gamedata tests/test_snapshot_semantics.py` green on all four properties (criterion 10).",
                       "`uv run pytest -m gamedata tests/test_extraction_cost.py` green and the ingest-run row carries a non-null parse-seconds value (criterion 17).",
                       "The `ootp` schema, previously 0 tables, holds `bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name`, `bronze_field_label`, `bronze_ingest_run` and nothing else."
                   ],
    "commit_note":  "\u0027Land bronze into the ootp schema with snapshot+save keys, one declaration driving DDL and grain tests\u0027. Through /commit."
}
```
```json
{
    "name":  "Phase 8 — The parser-vs-export differential harness",
    "goal":  "Prove the parser row-for-row against the retained probe save\u0027s 72-table export, with per-field mismatch reporting. This is the only thing that makes the roster grain and the team dimension provable rather than eyeballed. Scope Core 17, 18; acceptance criteria 6 and 9.",
    "steps":  [
                  "BUILDER: `src/ootp_ai/warehouse/sql.py::quote_ident()` — backtick every identifier in every export-diff query, and reject a backtick in the input. This is not hygiene theatre: measured, `select current_date from ootp_truth_real.leagues` returns the wall-clock date for all 15 rows because MySQL parses the bare column name as the CURRENT_DATE function, and nothing errors. That is a data incident sitting in the exact code path the diff uses.",
                  "BUILDER: `src/ootp_ai/validate/export_diff.py` — parse the probe save, land it under its own `save_id`, and diff against `ootp_truth_real` inside one MySQL instance (which is ADR 0004\u0027s stated rationale for choosing MySQL at all). Report every mismatch PER FIELD BY NAME; an aggregate pass rate is not acceptable output.",
                  "MAIN THREAD: `tests/test_parser_vs_export.py` (`-m gamedata`) — FIRST assert provenance: the parsed save\u0027s sim date is 2024-03-18 and its human team is the Chicago Cubs, matching `ootp_truth_real`, proving the binaries and the export describe the same universe. Only then diff: zero row-count and zero value differences over the landed field set — 259 teams, 18,072 active players (`retired = 0`), 15,672 `team_roster` rows, 15 leagues.",
                  "MAIN THREAD: `tests/test_quote_ident.py` (offline) — the reserved-identifier regression: `quote_ident(\u0027current_date\u0027)` produces a backticked identifier, and a name containing a backtick is rejected.",
                  "MAIN THREAD: `tests/test_parse_real_save.py` (`-m gamedata`) against OOTP-AI.lg — exactly 30 teams at MLB level with correct abbreviations; `player_id` unique per snapshot; Boston\u0027s roster rows number \u003e= 26 (NOT == 26: the club is in spring training at 2024-03-07 and a set 26 probably does not exist yet); and ZERO roster rows carry a null or blank display name.",
                  "BUILDER: record in `field_map.toml` that Tier B is EXACT for ids, names, strings, dates, roster lists, team dimension and league config, and BUCKETED for ratings — measured, `players_batting.batting_ratings_overall_contact` has exactly 12 distinct values across 20-80, so the export is display scale and is NOT an exact rating validator. `players.csv` (Tier A) stays load-bearing permanently."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parser_vs_export.py` green: provenance asserted first, then zero row-count and zero value differences, with any mismatch enumerated per field by name (criterion 6).",
                       "`uv run pytest -m gamedata tests/test_parse_real_save.py` green against OOTP-AI.lg on all four assertions (criterion 9).",
                       "`uv run pytest tests/test_quote_ident.py` green offline.",
                       "Every export-diff query in `src/ootp_ai/` routes its identifiers through `quote_ident` — grep shows no bare identifier interpolated into an f-string query."
                   ],
    "commit_note":  "\u0027Differential harness: parser vs the probe-save export, provenance-pinned and per-field\u0027. Through /commit."
}
```
```json
{
    "name":  "Phase 9 — The two reports and the withheld-field guard",
    "goal":  "Give the GM its roster and the standings — the request\u0027s observable signal — and make it mechanically impossible for a true or unclassified rating to reach the page. Scope Core 13, Folded-in 1, 3; acceptance criteria 13 and 14.",
    "steps":  [
                  "BUILDER: `src/ootp_ai/reports/__main__.py` so that `uv run python -m ootp_ai.reports render` is the real entry point (criterion 14 invokes exactly this).",
                  "BUILDER: `src/ootp_ai/reports/roster.py` — the configured organization ONLY, grouped by roster list, carrying position, age, bats/throws and uniform number, with `snapshot_date` and sim date on line one so staleness is visible on sight. The org filter lives here, never at bronze. If `list_id`\u0027s value semantics did not reach at least `inferred` in phase 4, group by the RAW integer with a header line stating the meanings are `unconfirmed` — never print `active roster` or `40-man` for an unlabelled id, because a wrong label produces a confidently wrong roster with nothing throwing.",
                  "BUILDER: `src/ootp_ai/reports/standings.py` — 30 MLB clubs grouped by division with W-L-pct-GB columns. Measured, all 259 `team_record` rows are 0-0-0 and 0 of 12,961 games are played, so the content is structurally empty by design. Emit pct as a structural-absence marker rather than `.000` when games played is zero — structural absence is not zero (data-engineer.md:110-112).",
                  "BUILDER: route EVERY report column through `contracts/policy.py::is_renderable()`. There is no second path to the page.",
                  "MAIN THREAD: `tests/test_withheld_fields.py` (OFFLINE) keyed on the field map\u0027s declared CATEGORY, not on column-name globs (finding F9): no field whose category is `rating-true` and no field whose epistemic label is `unconfirmed` or `assumed` is renderable. Include the NEGATIVE test — a synthetic `rating-scouted` field with a proven label IS renderable — so the guard cannot be satisfied by blocking everything. Keep name patterns only as a secondary check, with `talent_%` corrected to `%_talent_%` (the real columns are `batting_ratings_talent_*`; as originally written the pattern matched nothing).",
                  "MAIN THREAD: `tests/test_reports.py` (`-m gamedata`) — the resolved output root is git-ignored, proven by `git check-ignore -q \u003cpath\u003e` exiting 0 AND `git ls-files` listing no file under it; the roster report contains rows for exactly the configured organization and zero rows belonging to any other; every player row\u0027s name matches `^[A-Za-z][A-Za-z .\u0027-]+$` (a name, not an integer); the standings report contains 30 MLB rows grouped by division with W-L-pct-GB columns present; both files carry `snapshot_date` and sim date on line one. Standings content is asserted STRUCTURALLY — asserting a nonzero win total would fail on a correct parse.",
                  "MAIN THREAD: extend `tests/test_no_leaks.py` (Folded-in 1) — assert the report and catalog output roots resolve to git-ignored paths, and assert the TRACKED half of the catalog and field map name source FILES but never absolute paths (reuse the existing PATTERNS at test_no_leaks.py:24-28). `saved_games.dat` embeds an absolute user-profile path for every save, so a provenance section that renders it publishes a username to a public repo. Note in a comment the known local-feedback gap: `tracked_text_files()` enumerates via `git ls-files` (test_no_leaks.py:31-48) so an untracked artifact is invisible locally and only fails in CI — a follow-up request, not in scope here."
              ],
    "acceptance":  [
                       "`uv run python -m ootp_ai.reports render` writes both reports into the git-ignored output root.",
                       "`uv run pytest -m gamedata tests/test_reports.py` green on all five assertions (criterion 14).",
                       "`uv run pytest tests/test_withheld_fields.py` green OFFLINE, including the negative renderable case (criterion 13).",
                       "The roster report names real Boston players — zero rows carry a null, blank, or integer display name.",
                       "`uv run pytest tests/test_no_leaks.py` green with the new rendered-game-data assertions."
                   ],
    "commit_note":  "\u0027Render the roster and standings reports, gated by a category-keyed withheld-field guard\u0027. Through /commit. This is the commit the request exists for — after it, the GM can name its own players."
}
```
```json
{
    "name":  "Phase 10 — The generated catalog: tracked structural half, generated volatile half",
    "goal":  "Tell the GM what exists AND what was deliberately withheld and why, so it prices an action against a known gap rather than discovering it by hitting it. Scope Core 14, 15, Folded-in 3, 4; acceptance criterion 15.",
    "steps":  [
                  "BUILDER: `src/ootp_ai/catalog/__main__.py` so that `uv run python -m ootp_ai.catalog` is the real entry point (criterion 15 invokes exactly this).",
                  "BUILDER: split the output per Decisions 3. The TRACKED structural half — table names, grain sentences, key lists, coverage statements, withheld groups with reason and ADR, epistemic labels — generates from `tables.toml` + `field_map.toml` ALONE, so it regenerates offline with no MySQL and survives a fresh clone. The VOLATILE half — row counts, snapshot dates, freshness — plus `catalog.json` (Folded-in 4, same generator, one extra writer) generate into the git-ignored output root.",
                  "BUILDER: the volatile half reads `information_schema` plus counts; nothing is hand-written. Coverage statements generate FROM COUNTS (Folded-in 3): \u0027players: 18,072 rows, active only, retired excluded, 1,920 carry an external ID\u0027 is far more useful than a table name and cannot go stale. State how many players carry NO roster row (~10,700 of 18,072 — free agents, draft-eligible, international, unassigned) so the GM prices \u0027who is available\u0027 as a known gap.",
                  "BUILDER: the withheld section names the true-rating tables, `players.prone_*`, `players_value.*` and every still-`unconfirmed` field, each with its reason and its ADR. NO player-level value and NO rating column name appears anywhere in the catalog.",
                  "BUILDER: the tracked half carries the report-path pointer (SD-11) — each report\u0027s logical name, the `.env` key and relative path it resolves to, and a one-line spawn instruction the umpires read when handing the GM its reports. As CODE SPANS, not a Markdown link into `var/`: tests/test_doc_links.py:18-38 resolves every relative link and a link into the ignored root turns CI red today. Without this pointer, acceptance criterion 20 is unreproducible by anyone who was not in the room.",
                  "MAIN THREAD: `tests/test_catalog.py` — the OFFLINE half regenerates the structural section during the test and asserts it is byte-identical to the committed copy (proving it cannot be hand-edited into drift), and asserts no rating column name appears in it. The `-m gamedata` half asserts every landed table appears with grain sentence, key list, coverage population, row count, source `.dat` file, epistemic label and snapshot date, and that regenerating twice is byte-identical."
              ],
    "acceptance":  [
                       "`uv run python -m ootp_ai.catalog` regenerates both halves; running it twice produces byte-identical output.",
                       "`uv run pytest tests/test_catalog.py -m \"not gamedata\"` green OFFLINE — the committed structural half is byte-identical to a fresh regeneration.",
                       "`uv run pytest -m gamedata tests/test_catalog.py` green on the full criterion-15 assertion set.",
                       "`uv run pytest tests/test_doc_links.py` and `tests/test_no_leaks.py` still green — the tracked catalog contains no link into `var/` and no absolute path."
                   ],
    "commit_note":  "\u0027Generate the warehouse catalog: tracked structure, generated volume, and an explicit withheld section\u0027. Through /commit."
}
```
```json
{
    "name":  "Phase 11 — Documentation truth-up, the tracked report channel, and the USER-RUN gate",
    "goal":  "Correct what is now measurably wrong, record the deferrals on the record rather than quietly, and hand the operator the two checks only a human can run. Scope Core 20, 21, Decisions 9, 10; acceptance criteria 19, 20, 21, and the final 16.",
    "steps":  [
                  "MAIN THREAD via `/update-docs`: correct `docs/league-rules.md:129` and `:295` — no `leagues.dat` exists (grep-confirmed at both lines), and the league configuration block lives in `world.dat` (the string `major_league_ml_c_2024.lsdl`, exactly the `schedule_file_1` value recorded at docs/league-rules.md:80, sits at byte 5,559,751 of OOTP-AI.lg/world.dat, surrounded by league-shaped records containing `World Series`, `AL` and `NL`; it appears nowhere in teams.dat). Also revisit `:26` and `:30-31`, which claim the warehouse supersedes §1 \u0027the moment the parser lands\u0027 — this slice makes that partially, not wholly, true.",
                  "MAIN THREAD via `/update-docs`: route the builder\u0027s `## docs-delta` into `docs/data-access.md` — the §1 file table is incomplete (18 `.dat` files present, several unlisted, no `leagues.dat`); DOWNGRADE the `verified` label at :36-38 asserting `saved_games.dat` is plaintext (it carries the standard header and length-prefixed strings); add the `names.dat` fixed-size-per-save finding with an `inferred` label; record that `ootp_truth_osa` is empty and unnecessary; and upgrade labels for EXACTLY the fields Tier A or Tier B actually proved, leaving everything else `unconfirmed` and withheld. The builder must never edit this file — it is in the deny set at data-engineer.md:156.",
                  "MAIN THREAD: append the dbt deferral to `docs/decisions/0004-mysql-warehouse.md` §Notes (Decisions 9) — the trigger fired, the note records why the adapter question was NOT pulled and that ADR 0005\u0027s PATTERN choice is honoured in full while only its TOOLING phrasing is deferred. Quietly diverging is the one option this repo forbids.",
                  "MAIN THREAD: extend `gm/standing-orders.md`\u0027s `## Reports` format block (at :42-50) with the engineering-owned report kind (Decisions 4) — a pipeline-generated report genuinely has no analyst behind it, and gm/staff.md:5-8 records that no staff exist, so naming an owner would be fiction. Then add the two report entries using that kind.",
                  "MAIN THREAD: reclassify the probe save in the docs as a RETAINED VALIDATION ASSET (Folded-in 8). ADR 0002 and docs/data-access.md:319-320 currently describe it as disposable; every value claim in the validation strategy depends on it staying on disk, and the parser loses its only ground truth for fictional players and roster lists the day someone tidies up.",
                  "MAIN THREAD: advance the request artifacts — `PROJECT_SCOPE.md` and the track Index row in `requests/feature-requests/README.md:119` — and write `IMPLEMENTATION_REPORT.md`. `/commit` Step 4 maintains these.",
                  "USER-RUN (criterion 20, the acceptance panel must NOT claim this): a cold session spawns the `gm` subagent with the roster and catalog reports in its context; the returned handoff\u0027s `## situation` section names at least five Boston players by real name, each attributed to the report as its source, with no roster fact appearing in `## assumed`.",
                  "USER-RUN (criterion 21): the operator confirms OOTP-AI.lg\u0027s file set, sizes and modification times are unchanged after a full ingestion run, by hand against the recorded manifest — an independent check that does not rely on the code that would be the thing violating it.",
                  "USER-RUN (Decisions 2, blocker SD-03): the umpires append the ledger row recording that the roster report and catalog are free infrastructure rather than a commissioned action, WITH its reasoning, because it becomes an early seq every later report request will cite. This is an umpire act, not a build artifact."
              ],
    "acceptance":  [
                       "The string `leagues.dat` appears nowhere under `docs/` except inside an explicit correction note — `grep -rn \u0027leagues.dat\u0027 docs/` returns only the correction (criterion 19).",
                       "`uv run pytest tests/test_doc_links.py tests/test_repo_structure.py tests/test_agent_contract.py tests/test_no_leaks.py` all green.",
                       "`uv run pytest -m \"not gamedata\"` passes with NO game install and NO MySQL server, and `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` are clean (criterion 16).",
                       "`gm/standing-orders.md` carries two report entries under the new engineering-owned kind, and its format block documents that kind.",
                       "`docs/decisions/0004-mysql-warehouse.md` §Notes records the dbt deferral and its trigger.",
                       "USER-RUN criteria 20 and 21 are handed to the operator with the exact commands and the spawn instruction, and are NOT claimed as passed by any agent."
                   ],
    "commit_note":  "\u0027Truth-up the docs, record the dbt deferral, and open the tracked report channel\u0027. Through /commit, with /update-docs run as its doc gate. Then ask before merging the PR — never push main, never force-push, never amend."
}
```

### testing

THE SHAPE OF THE SUITE. CI runs exactly four commands (.github/workflows/ci.yml:37-49): `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -m "not gamedata"`. CI has no OOTP install, no save and no MySQL, and must never have any of them (ADR 0006). So the suite splits in two, and the split is the single most important testing decision in this plan.

OFFLINE (runs in CI, no marker): test_save_header.py, test_sequential_walk.py, test_no_fixed_offsets.py, test_withheld_fields.py, test_quote_ident.py, test_config.py, the offline half of test_grain_contracts.py, the offline half of test_catalog.py, plus the four existing guards (test_no_leaks.py, test_repo_structure.py, test_agent_contract.py, test_doc_links.py). These carry the correctness weight that does not need data: a fixed-offset reader is caught by test_sequential_walk.py's 1-year vs 10-year contract pair, and by test_no_fixed_offsets.py's AST scan, without any save present.

GAMEDATA (excluded from CI, run explicitly): test_read_only.py, test_parse_teams.py, test_byte_accounting.py, test_names_join.py, test_names_join_boston.py, test_names_per_save.py, test_parser_vs_export.py, test_parse_real_save.py, test_snapshot_semantics.py, test_extraction_cost.py, test_reports.py, the gamedata halves of test_grain_contracts.py and test_catalog.py. The single declared marker at pyproject.toml:80 is widened to "requires a local OOTP install, save, or warehouse" rather than a second marker being added, because `addopts` carries `--strict-markers` (pyproject.toml:78) and an undeclared marker is a hard collection error.

FIXTURES ARE CODE, NOT DATA. Build synthetic byte sequences in `tests/fixtures/synthetic.py` as functions, not as committed binary files. This sidesteps the .dat-extension ban at tests/test_no_leaks.py:106-107 entirely, and matches tests/fixtures/README.md:32-37. It also produces the input a real save cannot: tests/fixtures/README.md:45-51 makes the point precisely — a day-0 save has every variable-length region at its minimum, so it is the LEAST informative input available and a fixed-offset parser passes on it cleanly.

THREE VALIDATION TIERS, and they do different jobs.
- Tier A, `players.csv`: exact, raw ~1-1000 scale, shipped real players only. The only exact rating validator, and (finding F8) the carrier of FirstName/LastName/LahmanID, which makes it a name validator for OUR league via the historical_id join. It is the only tier that touches OOTP-AI.lg.
- Tier B, the probe-save export in `ootp_truth_real`: exact for ids, names, strings, dates, roster lists, team dimension and league config; BUCKETED for ratings — measured, `batting_ratings_overall_contact` has exactly 12 distinct values across 20-80. A bucketed check can pass a parser that read the ADJACENT u16, which is CLAUDE.md's named correctness trap in its most dangerous form. Tier B is never a rating validator.
- Tier C, byte accounting: strict (zero residual) for teams.dat and names.dat; diagnostic for players.dat (record count matches an independent count, walk terminates on a record boundary, residual RECORDED not asserted zero). This is the only check that works on fields with no ground truth at all, which is why it earns its place.

TWO ANTI-VACUITY RULES, both learned from findings in the scope.
1. Every differential test enumerates mismatches PER FIELD BY NAME. An aggregate pass rate is not acceptable output — it is exactly how a parser reading the adjacent u16 ships green.
2. Any test whose ground truth may be unreachable (`ootp_truth_real` down, probe save deleted) must SKIP LOUDLY WITH A NAMED REASON, never pass. A vacuous green on test_names_join.py is worse than a red one.

SEQUENCING AGAINST THE IRREPLACEABLE SAVE (SD-20). Every filesystem-touching test — enumerator, header guard, snapshot copy, read-only proof — runs against the DISPOSABLE Challenge Mode probe save first and only then against OOTP-AI.lg. An identical-mode disposable save sits beside the irreplaceable one; pointing untested code at the managed league first is avoidable exposure, and ADR 0001 is the one unrecoverable failure in the project.

COLLATION IS A TEST DECISION, NOT A DETAIL. ops/mysql-bootstrap.sql:24 creates every schema with `utf8mb4_0900_ai_ci` — accent-insensitive and case-insensitive. A cross-schema "exact string equality" performed in SQL under that collation will report José == Jose as a match, in a repo whose own export doc (docs/data-access.md:336) turns "Replace accents" OFF specifically so names survive for validation. Compare in Python on `str`, or append `COLLATE utf8mb4_0900_bin` explicitly, and assert the choice in the test.

REGRESSION SAFETY. The four existing guards must stay green at every checkpoint, and two of them get extended rather than replaced: test_no_leaks.py gains the rendered-game-data assertions (Folded-in 1), and pyproject.toml's marker declaration is widened rather than duplicated. Per-phase cadence: implement -> `uv run pytest` (with and without the marker) -> `uv run ruff check .` -> `uv run ruff format --check .` -> `uv run mypy` -> `/commit`, which stages deliberately, runs the doc gate proportionally, and asks before writing. CI re-runs the offline subset on the PR.

### risks

- THE STRICT BYTE-ACCOUNTING TIER ON teams.dat IS ASSERTED, NOT EVIDENCED. The scope splits byte accounting strict/diagnostic by file and calls a full walk of teams.dat 'plausible' — but nothing in docs/data-access.md establishes that. The only verified teams.dat knowledge is the 5-string signature and ARGB colors (:224-226); ':228 unconfirmed — Everything else' covers the rest of a 5.3 MB file. If the strict tier proves as unbounded as players.dat, the phase blocks. MITIGATION: pre-register the demotion NOW — if strict is unreachable within the phase, demote teams.dat to the diagnostic tier, record the residual in the ingest-run row, write the tier rationale into the field map, and file a follow-up. Do not let a research task gate the request's observable signal.
- THE names.dat JOIN IS THE SINGLE LARGEST UNKNOWN AND IT SITS ON THE CRITICAL PATH OF THE HEADLINE REPORT. docs/data-access.md:238 has the index encoding and table layout `unconfirmed`, and a roster report of integers is not a roster report. MITIGATION: the brute-force-against-a-full-answer-key method (score every candidate u32 position across all 18,072 probe players) is bounded and either converges on ~100% or fails cleanly; the pre-registered fallback (Decisions 5) resolves names from players.csv at render time for the ~1,712 players carrying a Lahman ID, with fictional players rendering as IDs and NOTHING tracked.
- names.dat CONTENT IS PER-SAVE AND THIS IS A SILENT-WRONG FAILURE, NOT A CRASH. Measured: identical size (8,642,110 B) across all three saves on disk, three different SHA-256 digests. A name table or index->string expectation cached from the probe save and applied to OOTP-AI.lg produces a roster full of confident, wrong names with nothing throwing. MITIGATION: load the name table per snapshot from that snapshot's own file, and pin the finding with a test that asserts the same index is NOT expected to resolve identically in both saves.
- THE COLLATION DEFAULT ALREADY ON DISK DEFEATS 'EXACT' STRING COMPARISON. ops/mysql-bootstrap.sql:24, :31, :33 create all three schemas with utf8mb4_0900_ai_ci — accent- AND case-insensitive. Acceptance criteria 7 and 8 demand exact string equality; performed in SQL under this collation they are not exact, and the failure looks like a pass. MITIGATION: compare in Python, or COLLATE utf8mb4_0900_bin explicitly, and assert the collation in the test so a future schema change surfaces.
- A BUCKETED GROUND TRUTH CAN GREEN-LIGHT A PARSER READING THE ADJACENT FIELD. The export is display-scale: `batting_ratings_overall_contact` has exactly 12 distinct values across 20-80. This is CLAUDE.md's named correctness trap in its most dangerous form — a mis-mapped field yields a plausible number, not a crash. MITIGATION: this slice lands NO ratings at all, which is precisely why the scope decoupled them; keep it that way, and keep players.csv (Tier A) as the permanent exact validator for whenever ratings do land.
- tests/ IS IN THE BUILDER'S HARD DENY SET (.claude/agents/data-engineer.md:150). If the implementation spec hands the whole plan to the data-engineer subagent, the correct behaviour per its Escalation case 1 is to STOP and report — producing an Escalation and zero tests. MITIGATION: the spec declares only `src/ootp_ai/**` and `requests/feature-requests/first-sight/reviews/**` as target paths; every file under tests/, plus docs/, ops/, .env.example, gm/ and pyproject.toml, is authored by the main thread. State this in the spec, not just in the plan.
- mypy RUNS STRICT OVER BOTH src AND tests (pyproject.toml:69-73) AND THE FIRST RUNTIME DEPENDENCY HAS NOT BEEN CHOSEN (pyproject.toml:9, SD-14). An unstubbed MySQL driver fails the build on the first import. MITIGATION: PyMySQL plus types-PyMySQL in the dev group; python-dotenv moves from dev (pyproject.toml:23) into [project] dependencies because config.py imports it at runtime. Avoid mysqlclient — a C extension needing a Windows build toolchain.
- RUFF'S SELECTED RULES BITE PARSER CODE SPECIFICALLY. `A` (builtin shadowing, pyproject.toml:53) makes `id`, `bytes`, `list`, `type`, `format` illegal as names — all natural in a record walker. `DTZ` (:57) makes any naive datetime an error, so every wall-clock stamp in the ingest-run row needs `datetime.now(UTC)`. `PTH` (:58) bans os.path. None of these is hard, but each one is a surprise mid-phase.
- REGENERATING A REPORT OVERWRITES THE PRIOR SNAPSHOT'S VIEW (SD-21), breaking citation integrity for any gm/decisions/ record that cites it. Not solved by this slice. MITIGATION: write reports under a snapshot-dated subdirectory of the output root so a regeneration is additive rather than destructive, and note the residual gap; the tracked catalog's report pointer names the logical path, not a dated one.
- THE DOC-LINK GUARD IS LIVE-BROKEN IN A WAY THIS FEATURE'S OWN ARTIFACTS TRIP. tests/test_doc_links.py:22-37 resolves EVERY relative Markdown link in every tracked .md, including links inside code fences, and a link into `var/` cannot resolve. An open bugfix request exists (requests/bugfix-requests/_done/doc-link-guard-mismatch/). MITIGATION: every artifact this feature writes uses CODE SPANS for file:line citations and for anything under var/ — the same convention PROJECT_SCOPE.md:5-9 adopts. The tracked catalog's report pointer is a code span, never a link.
- THE tests/test_no_leaks.py FEEDBACK LOOP IS BLIND TO UNTRACKED FILES. tracked_text_files() enumerates via `git ls-files` (test_no_leaks.py:31-48), so a leak in a newly created, unstaged artifact passes locally and only fails in CI after staging. This feature is the first thing in the repo's history that renders OOTP player data to a file, so the exposure is new. MITIGATION: run the guard after staging, not before; the scope explicitly files the structural fix as a follow-up rather than in-scope work.
- THE STANDINGS REPORT CARRIES NO INFORMATION TODAY AND ASSERTING OTHERWISE FAILS ON A CORRECT PARSE. Measured: all 259 team_record rows are 0-0-0 and 0 of 12,961 games are played. A test asserting a nonzero win total would go red against a perfectly correct parser. MITIGATION: assert structure only — 30 MLB rows, division grouping, W-L-pct-GB columns present — and emit a structural-absence marker rather than `.000` for pct when games played is zero.
- list_id VALUE SEMANTICS ARE UNDOCUMENTED AND SIT ON THE CRITICAL PATH OF THE HEADLINE REPORT. db_structure_ootp25_mysql.txt gives team_roster's columns but not the enum's meanings. A wrong human label ('active roster', '40-man') produces a confidently wrong roster with nothing throwing. MITIGATION: the pre-registered fallback in scope Core 9 — land the opaque integer, group by the raw value, state `unconfirmed` in the report header, file a follow-up. Never print a label for an id whose mapping is not at least `inferred`.
- NOBODY HAS RUN ANY OF THIS CODE. Every cost estimate in the upstream scope is `unconfirmed`, including the extraction-cost expectation, and phases 4-6 each contain a genuine research task (teams record layout, players record layout, names index position). MITIGATION: Decisions 6's operator ruling removes the wall-clock threshold entirely, and each research task carries a pre-registered fallback so a hard phase degrades rather than blocks.

### files_to_touch

```json
{
    "path":  "src/ootp_ai/config.py",
    "change":  "NEW (builder). Frozen `Settings` dataclass + `load_settings()` resolving OOTP_INSTALL, OOTP_SAVED_GAMES, OOTP_LEAGUE, OOTP_SNAPSHOT_ROOT, the probe-save keys, the report-root key and the MySQL connection from `.env` only. No literal path, no `parents[N]` walk (data-engineer.md:89). Snapshot-root default is a CWD-relative `Path(\"var/snapshots\")`, validated creatable and rejected under the OneDrive env var."
}
```
```json
{
    "path":  "src/ootp_ai/saves.py",
    "change":  "NEW (builder). `enumerate_saves()` requiring BOTH players.dat and teams.dat inside a candidate directory (docs/data-access.md:60-63: a stray empty `.lg` directory exists); `assert_challenge_mode()` checking challenge.dat is exactly 241 bytes (:65-68). Both promoted to a pre-flight on every run."
}
```
```json
{
    "path":  "src/ootp_ai/snapshot.py",
    "change":  "NEW (builder). Copies only teams.dat, players.dat, names.dat (~46 MB) to `\u003croot\u003e/\u003cleague\u003e/\u003csim_date\u003e/` with a per-file size + SHA-256 manifest, every handle `\"rb\"`, refusing to overwrite an existing snapshot. All parsing runs against the snapshot, never the live save."
}
```
```json
{
    "path":  "src/ootp_ai/parser/primitives.py",
    "change":  "NEW (builder). `Cursor` over in-memory bytes with advancing-only readers: u8/u16/u32/i32/f64, `string()` (u32-LE length prefix, ASCII, no terminator), `date()` (u8 day, u8 month, u16 year), `color()` (u32 ARGB) — all four pinned at docs/data-access.md:193-201. Exposes no absolute-positioning method, so criterion 3\u0027s scan is satisfied by construction."
}
```
```json
{
    "path":  "src/ootp_ai/parser/header.py",
    "change":  "NEW (builder). `read_header()` per docs/data-access.md:172-181 — byte 0 = 0x00, b\"OOTP\" at offset 1, u32 version at offset 5, self-declared filename at offset 25. Defines `UnsupportedSaveVersion` (exact name pinned by criterion 1) and `SaveFilenameMismatch`. Refuses strictly."
}
```
```json
{
    "path":  "src/ootp_ai/parser/teams.py",
    "change":  "NEW (builder). Sequential walk: team_id, the verified 5-string signature (docs/data-access.md:224-226), ARGB colors, level, parent_team_id, sub-league/division hierarchy, win/loss fields. Byte accounting recorded as it walks."
}
```
```json
{
    "path":  "src/ootp_ai/parser/rosters.py",
    "change":  "NEW (builder). Roster-list extraction at the (team_id, player_id, list_id) grain, plus empirical derivation of list_id value semantics against ootp_truth_real.team_roster, with the SD-17 opaque-integer fallback."
}
```
```json
{
    "path":  "src/ootp_ai/parser/players.py",
    "change":  "NEW (builder). Sequential walk of a deliberately minimal field set: player_id, team/org assignment, position, uniform number, DOB, bats/throws, the name indices, historical_id. No ratings of any kind."
}
```
```json
{
    "path":  "src/ootp_ai/parser/names.py",
    "change":  "NEW (builder). names.dat walk into an index -\u003e string table on the observed record shape (u32 len + ASCII + u32 0 + u32 monotonic index + three u32s + 0x27 separator). Loaded per snapshot from that snapshot\u0027s own file — never cached across saves."
}
```
```json
{
    "path":  "src/ootp_ai/parser/saved_games.py",
    "change":  "NEW (builder). Reads saved_games.dat through the SAME header reader plus a length-prefixed string walk — it is NOT plaintext, contrary to docs/data-access.md:36-38. Yields per-save sim date and human team. Never substring-scraped; never rendered into a tracked file (it embeds an absolute user-profile path per save)."
}
```
```json
{
    "path":  "src/ootp_ai/contracts/tables.toml",
    "change":  "NEW (builder, TRACKED). The four bronze table declarations with prose grain sentence + key list + coverage population. Read by three consumers: the DDL emitter, the grain test, the catalog generator."
}
```
```json
{
    "path":  "src/ootp_ai/contracts/field_map.toml",
    "change":  "NEW (builder, TRACKED). Per field: name, type, source .dat, the walker that reads it, category (identity/rating-true/rating-scouted/contract/structural), epistemic label, and the validator tier that produced the label. ADR 0006 §Notes blesses derived schema knowledge as ours and trackable."
}
```
```json
{
    "path":  "src/ootp_ai/contracts/loader.py",
    "change":  "NEW (builder). tomllib-based reader returning typed models. Stdlib only — no new dependency."
}
```
```json
{
    "path":  "src/ootp_ai/contracts/policy.py",
    "change":  "NEW (builder). `is_renderable(field)` — the single gate every serving path goes through. False when category == \u0027rating-true\u0027 or epistemic in {\u0027unconfirmed\u0027,\u0027assumed\u0027} (ADR 0012:75-76)."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/ddl.py",
    "change":  "NEW (builder). Emits CREATE TABLE + PRIMARY KEY from tables.toml. Never hand-written, so the declaration is the only place a key exists."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/load.py",
    "change":  "NEW (builder). Bronze landing 1:1 with parser output — typing, casing, dedup only; no joins, no filtering, no semantic renaming (data-engineer.md:98). snapshot_date AND save_id in every primary key. Structural absence preserved as NULL, never zero."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/ingest_run.py",
    "change":  "NEW (builder). One row per snapshot: source file sizes, SHA-256 digests, header versions, sim date, human team, row counts, residual bytes, wall-clock parse seconds. `datetime.now(UTC)` for stamps (ruff DTZ, pyproject.toml:57)."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/sql.py",
    "change":  "NEW (builder). `quote_ident()` backticking every identifier in export-diff SQL and rejecting a backtick in input. Fixes a measured live incident: bare `current_date` parses as the CURRENT_DATE function and returns the wall-clock date with nothing erroring."
}
```
```json
{
    "path":  "src/ootp_ai/validate/export_diff.py",
    "change":  "NEW (builder). Provenance-first parser-vs-export diff inside one MySQL instance, reporting every mismatch per field by name — never an aggregate pass rate."
}
```
```json
{
    "path":  "src/ootp_ai/reports/__main__.py",
    "change":  "NEW (builder). Makes `uv run python -m ootp_ai.reports render` the real entry point required by acceptance criterion 14."
}
```
```json
{
    "path":  "src/ootp_ai/reports/roster.py",
    "change":  "NEW (builder). Configured organization only, grouped by roster list, position/age/bats-throws/uniform number, snapshot_date and sim date on line one. The org filter lives here, never at bronze."
}
```
```json
{
    "path":  "src/ootp_ai/reports/standings.py",
    "change":  "NEW (builder). 30 MLB clubs by division with W-L-pct-GB. Structural-absence marker rather than `.000` when games played is zero."
}
```
```json
{
    "path":  "src/ootp_ai/catalog/__main__.py",
    "change":  "NEW (builder). Makes `uv run python -m ootp_ai.catalog` the real entry point required by criterion 15. Writes the tracked structural half (from the declarations alone, offline) and the generated volatile half plus catalog.json into the ignored root."
}
```
```json
{
    "path":  "src/ootp_ai/__init__.py",
    "change":  "EDIT (builder). Replace the Phase-0 docstring at lines 1-5 (\u0027No pipeline code yet; the .dat parser is feature request #1\u0027) — it becomes false the moment phase 3 lands."
}
```
```json
{
    "path":  "pyproject.toml",
    "change":  "EDIT (main thread). Move python-dotenv from the dev group (:23) into [project] dependencies (:9); add PyMySQL there and types-PyMySQL to dev. Widen the single `gamedata` marker at :80 to \u0027requires a local OOTP install, save, or warehouse\u0027 — never add a second marker under --strict-markers (:78). Update the now-false comment at :11-15."
}
```
```json
{
    "path":  "tests/fixtures/synthetic.py",
    "change":  "NEW (main thread). Byte builders as FUNCTIONS, not data files — make_header(version, filename), make_record(contract_years). Sidesteps the .dat-extension ban at tests/test_no_leaks.py:106-107 entirely."
}
```
```json
{
    "path":  "tests/test_save_header.py",
    "change":  "NEW (main thread, offline). Criterion 1: v25 parses; v24 and v26 raise UnsupportedSaveVersion; magic at offset 0 rejected; filename mismatch rejected."
}
```
```json
{
    "path":  "tests/test_sequential_walk.py",
    "change":  "NEW (main thread, offline). Criterion 2: 1-year vs 10-year contract array yields identical values for every field after the variable region. A fixed-offset reader cannot pass."
}
```
```json
{
    "path":  "tests/test_no_fixed_offsets.py",
    "change":  "NEW (main thread, offline). Criterion 3: AST scan over src/ootp_ai/parser/ for `.seek(\u003cnonzero int literal\u003e)` and constant-offset `struct.unpack_from`. Encodes data-engineer.md:69-74 mechanically."
}
```
```json
{
    "path":  "tests/test_grain_contracts.py",
    "change":  "NEW (main thread). Offline half: prose grain sentence == emitted DDL key for all four tables (criterion 4). gamedata half: test_roster_grain_is_not_player_grain positively asserts player_id is NOT unique in one snapshot\u0027s roster rows (criterion 5)."
}
```
```json
{
    "path":  "tests/test_withheld_fields.py",
    "change":  "NEW (main thread, offline). Criterion 13: keyed on declared CATEGORY, not column-name globs; includes the negative case (a synthetic rating-scouted field IS renderable); name patterns only as a secondary check with `%_talent_%`, not `talent_%`."
}
```
```json
{
    "path":  "tests/test_read_only.py",
    "change":  "NEW (main thread, gamedata). Criterion 11: size + mtime_ns + SHA-256 manifest before and after a full parse, over both OOTP roots. Probe save first, OOTP-AI.lg second (SD-20)."
}
```
```json
{
    "path":  "tests/test_byte_accounting.py",
    "change":  "NEW (main thread, gamedata). Criterion 12, split by file: strict zero-residual for teams.dat and names.dat; diagnostic for players.dat (record count vs the export\u0027s retired=0 population, record-boundary termination, residual recorded)."
}
```
```json
{
    "path":  "tests/test_names_join.py",
    "change":  "NEW (main thread, gamedata). Criterion 7, Tier B: 100% exact against ootp_truth_real, zero unresolved indices, every failure enumerated, skips loudly with a named reason if the schema is unreachable, collation declared explicitly."
}
```
```json
{
    "path":  "tests/test_names_join_boston.py",
    "change":  "NEW (main thread, gamedata). Criterion 8, Tier A: the names.dat-resolved name equals players.csv FirstName/LastName joined on LahmanID for every OOTP-AI.lg player carrying a historical_id. The only validation of the join on the league we actually manage."
}
```
```json
{
    "path":  "tests/test_parser_vs_export.py",
    "change":  "NEW (main thread, gamedata). Criterion 6: provenance asserted FIRST (sim date 2024-03-18, human team Chicago Cubs), then zero row-count and zero value differences over 259 teams, 18,072 active players, 15,672 roster rows, 15 leagues."
}
```
```json
{
    "path":  "tests/test_parse_real_save.py",
    "change":  "NEW (main thread, gamedata). Criterion 9 against OOTP-AI.lg: 30 MLB teams with correct abbreviations, player_id unique per snapshot, Boston roster rows \u003e= 26 (not == 26), zero null/blank display names."
}
```
```json
{
    "path":  "tests/test_snapshot_semantics.py",
    "change":  "NEW (main thread, gamedata). Criterion 10: idempotent reload, second snapshot leaves the first bit-identical, byte-identical parser output across two runs, no silent overwrite of an existing snapshot id."
}
```
```json
{
    "path":  "tests/test_extraction_cost.py",
    "change":  "NEW (main thread, gamedata). Criterion 17: asserts the wall-clock number exists in the ingest-run row. No threshold, no pass/fail on duration (Decisions 6)."
}
```
```json
{
    "path":  "tests/test_reports.py",
    "change":  "NEW (main thread, gamedata). Criterion 14: git-ignored output root proven by `git check-ignore -q` exit 0 AND `git ls-files` empty under it; org-only rows; name regex `^[A-Za-z][A-Za-z .\u0027-]+$`; 30 MLB standings rows with W-L-pct-GB; snapshot_date and sim date on line one of both."
}
```
```json
{
    "path":  "tests/test_catalog.py",
    "change":  "NEW (main thread). Offline half: the structural section regenerates byte-identically to the committed copy and contains no rating column name. gamedata half: every landed table with grain/key/coverage/row count/source file/label/snapshot date, and a twice-regenerated byte-identical result (criterion 15)."
}
```
```json
{
    "path":  "tests/test_no_leaks.py",
    "change":  "EDIT (main thread). Add a rendered-game-data guard: the report and catalog output roots resolve to git-ignored paths, and the TRACKED catalog and field map name source FILES but never absolute paths (reuse PATTERNS at :24-28). Note the git ls-files blind spot at :31-48 in a comment — it is a filed follow-up, not in scope."
}
```
```json
{
    "path":  "docs/league-rules.md",
    "change":  "EDIT (main thread via /update-docs). Criterion 19: :129 and :295 must stop asserting a leagues.dat and must record the measured world.dat location instead. Revisit :26 and :30-31, which claim the warehouse supersedes §1 \u0027the moment the parser lands\u0027."
}
```
```json
{
    "path":  "docs/data-access.md",
    "change":  "EDIT (main thread via /update-docs ONLY — it is in the builder\u0027s deny set at data-engineer.md:156). Complete §1\u0027s file table (18 .dat files, no leagues.dat); downgrade the `verified` plaintext claim at :36-38; add the names.dat fixed-size-per-save finding as `inferred`; record ootp_truth_osa as empty and unnecessary; reclassify the probe save as a retained validation asset; upgrade labels only for fields Tier A or Tier B actually proved."
}
```
```json
{
    "path":  "docs/decisions/0004-mysql-warehouse.md",
    "change":  "EDIT (main thread). Append the dbt deferral note to §Notes (Decisions 9): the trigger fired, why it was not pulled, and that ADR 0005\u0027s pattern choice is honoured in full while only its tooling phrasing is deferred."
}
```
```json
{
    "path":  "ops/mysql-bootstrap.sql",
    "change":  "EDIT (main thread — deny set for the builder). Remove the ootp_truth_osa database creation at :32-33 and its grant at :49 (Decisions 10: measured, ootp_truth_real already carries both scouting perspectives from one export, so the premise for a second export database is wrong)."
}
```
```json
{
    "path":  ".env.example",
    "change":  "EDIT (main thread). Add the retained standard-mode probe save and the disposable Challenge Mode probe save keys (directory + league name each), plus the report/catalog output root key. Remove MYSQL_TRUTH_OSA_DATABASE at :58."
}
```
```json
{
    "path":  "gm/standing-orders.md",
    "change":  "EDIT (main thread). Extend the `## Reports` format block at :42-50 with the engineering-owned report kind (Decisions 4 — no analyst exists, gm/staff.md:5-8 says so, and naming one would be fiction), then add the roster and standings entries using it."
}
```
```json
{
    "path":  "requests/feature-requests/first-sight/reviews/spike-pivot-rule.md",
    "change":  "NEW (builder). Written and committed BEFORE the spike runs. The FOUND/ABSENT triggers and what each one changes."
}
```
```json
{
    "path":  "requests/feature-requests/first-sight/reviews/spike-scouted-view.md",
    "change":  "NEW (builder). The written verdict: stored | computed | inconclusive, with an epistemic label and byte evidence (criterion 18)."
}
```
```json
{
    "path":  "requests/feature-requests/README.md",
    "change":  "EDIT (main thread, via /commit Step 4). Advance the first-sight Index row at :119 from `scoped` to `plan`, then to `implemented` when stage 4 lands."
}
```

### code_references

```json
{
    "ref":  "src/ootp_ai/__init__.py:7",
    "claim":  "The entire package today is a docstring plus `__version__ = \"0.1.0\"`. Every module this plan names is created from nothing — there is no existing parser, config layer, loader, renderer or catalog to hook into."
}
```
```json
{
    "ref":  "pyproject.toml:9",
    "claim":  "`dependencies = []` — no runtime dependency has been chosen. SD-14\u0027s blocker is real: a MySQL driver and a .env loader must both be selected, with type stubs, before any code compiles clean under strict mypy."
}
```
```json
{
    "ref":  "pyproject.toml:11-15",
    "claim":  "A tracked comment states \u0027The first real dependency will arrive with the warehouse loader.\u0027 Phase 2 makes that sentence describe the past, so the comment must be updated in the same commit."
}
```
```json
{
    "ref":  "pyproject.toml:23",
    "claim":  "`python-dotenv\u003e=1.0` currently sits in the `dev` dependency group. The config layer imports it at runtime, so it must move into `[project] dependencies` or a non-dev install breaks."
}
```
```json
{
    "ref":  "pyproject.toml:57",
    "claim":  "ruff selects `DTZ` with the comment \u0027naive datetimes — every timestamp here is tz-aware or it is a bug\u0027. Every wall-clock stamp in the ingest-run row must use `datetime.now(UTC)` or lint fails."
}
```
```json
{
    "ref":  "pyproject.toml:53",
    "claim":  "ruff selects `A` (builtin shadowing). A record walker naturally reaches for `id`, `bytes`, `list`, `type` and `format` as local names; all of them are lint errors here."
}
```
```json
{
    "ref":  "pyproject.toml:69-73",
    "claim":  "mypy runs `strict = true` over BOTH `src` and `tests`. Every new test function needs a `-\u003e None` annotation, matching the existing guards, and every third-party import needs stubs."
}
```
```json
{
    "ref":  "pyproject.toml:78-81",
    "claim":  "`addopts = \"-q --strict-markers --strict-config\"` with exactly one declared marker, `gamedata: requires a local OOTP install or save.` An undeclared second marker is a hard collection error, which is why the scope widens this declaration rather than adding one."
}
```
```json
{
    "ref":  ".github/workflows/ci.yml:37-49",
    "claim":  "CI runs exactly ruff check, ruff format --check, mypy, and `pytest -m \"not gamedata\"`. This is the definition of \u0027offline\u0027 for acceptance criteria 1-5, 13 and 16."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:69",
    "claim":  "\u0027Never seek to a fixed offset... Code that seeks is a blocker, not a style note.\u0027 Acceptance criterion 3 turns this line into an AST scan over src/ootp_ai/parser/."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:89",
    "claim":  "\u0027never a literal path, never a `parents[N]` walk. (Test modules are the one established exception...)\u0027. This is why config.py cannot resolve the repo root from `__file__` to build the documented `var/snapshots` default."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:91",
    "claim":  "\u0027Never require a game install to satisfy a test.\u0027 The offline/gamedata split in this plan\u0027s testing section is this rule applied file by file."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:98",
    "claim":  "\u0027Bronze is 1:1 with the parser output. Typing, casing, deduplication. No joins, no business logic, no filtering, no semantic renaming.\u0027 This is why the Boston org filter lives in the report layer, not in load.py."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:101",
    "claim":  "\u0027Silver declares its grain and proves it... and the two must agree.\u0027 Acceptance criterion 4 enforces exactly this at bronze, by comparing the prose grain sentence in tables.toml against the key the DDL emitter produces."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:150",
    "claim":  "`tests/` is the first line of the repo-level deny set, above `.github/`, `ops/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md`, `docs/decisions/`. Handing a spec with test targets to the subagent produces an Escalation and zero tests."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:157",
    "claim":  "\u0027\u003canything under the OOTP install or saved-games directory\u003e\u0027 is in the deny set, cross-referenced to \u0027The game is read-only\u0027. No code path may open a save for writing."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:206-224",
    "claim":  "The return contract: one Markdown file in requests/\u003ctrack\u003e-requests/\u003cslug\u003e/reviews/, first line exactly `\u003c!-- handoff: v1 --\u003e`, eight named sections, at or under 120 lines, no diff hunks. The spike verdict and the build handoff both land here."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:239-247",
    "claim":  "Data facts never go in agent memory — they travel as `## docs-delta` with a proposed epistemic label and the main thread routes them through /update-docs. This is the only legal path for the phase-11 docs/data-access.md corrections."
}
```
```json
{
    "ref":  "docs/data-access.md:172-181",
    "claim":  "The byte-exact header: offset 0 u8 0x00, offset 1 char[4] \"OOTP\", offset 5 u32 25, then u32 11, 104, 84, 1, then the null-padded filename at offset 25. Acceptance criterion 1 is a direct transcription of this block."
}
```
```json
{
    "ref":  "docs/data-access.md:183-186",
    "claim":  "\u0027A reader that checks `data[0:4] == b\"OOTP\"` sees `\\x00OOT` and rejects a valid save; one that reads the version as a u32 at offset 4 gets 6480 rather than 25.\u0027 Criterion 1\u0027s offset-0 rejection case comes from here."
}
```
```json
{
    "ref":  "docs/data-access.md:193-201",
    "claim":  "The primitives table: string = u32-LE length prefix + raw ASCII with no terminator; date = u8 day, u8 month, u16 year; color = u32 ARGB; money = u32 whole dollars. These are the four readers Cursor must expose."
}
```
```json
{
    "ref":  "docs/data-access.md:204-215",
    "claim":  "Records contain variable-length regions, `verified` by the same player\u0027s ratings block sitting at different distances from both a leading and a trailing anchor in two saves — but field ORDER is stable across saves, which is what makes a sequential walk transfer."
}
```
```json
{
    "ref":  "docs/data-access.md:224-226",
    "claim":  "`verified` — teams.dat carries a 5-string signature (city, abbreviation, nickname, logo filename, full name) followed by u32 ARGB colors, and all 30 MLB clubs extract cleanly. This is the only verified teams.dat knowledge; :228 marks everything else `unconfirmed`, which is why strict byte accounting on that file is a risk rather than a given."
}
```
```json
{
    "ref":  "docs/data-access.md:234-238",
    "claim":  "Player names are indices into a ~264,095-entry names.dat table, and `unconfirmed` — \u0027The index encoding and the names.dat table layout. Resolving names requires a two-file join that has not been built.\u0027 This is the largest single unknown on the critical path of the headline report."
}
```
```json
{
    "ref":  "docs/data-access.md:282",
    "claim":  "`unconfirmed` — \u0027Which file holds which view, and whether the scouted view is stored at all.\u0027 The project-threatening unknown that phase 1\u0027s spike answers before any parser code exists."
}
```
```json
{
    "ref":  "docs/data-access.md:292-295",
    "claim":  "The spike\u0027s method, written and never run: export real and scouted ratings together, then search scouting.dat for the exported scouted values. Found -\u003e stored and the parser has its source; absent everywhere -\u003e computed, and there is a design problem before any rating can be served."
}
```
```json
{
    "ref":  "docs/data-access.md:60-63",
    "claim":  "`measured` — \u0027a `*.lg` glob is not a list of saves.\u0027 The saved-games directory contains a stray, empty directory literally named `.lg`. The enumerator must confirm players.dat and teams.dat are present."
}
```
```json
{
    "ref":  "docs/data-access.md:65-68",
    "claim":  "`measured` — challenge.dat is present at exactly 241 bytes in a Challenge Mode save and absent otherwise. A cheap filesystem-level mode check with no menu involved, promoted to a per-run pre-flight."
}
```
```json
{
    "ref":  "docs/data-access.md:36-38",
    "claim":  "`verified` — \u0027saved_games.dat is the index: plaintext league name, team name, league date, and the absolute path of each save. Readable without parsing.\u0027 The scope\u0027s finding F19 contradicts this at `high` confidence, so the label is downgraded in phase 11 and the file is read through the header reader instead."
}
```
```json
{
    "ref":  "docs/data-access.md:79-80",
    "claim":  "players.csv is ~12,855 rows, comma-separated, with a `//`-prefixed header line — the Tier A parser must strip that prefix or the first column name is wrong."
}
```
```json
{
    "ref":  "docs/data-access.md:99-102",
    "claim":  "`verified` — the Lahman/BBRef ID is embedded in players.dat itself as a length-prefixed string (e.g. `deverra01`), ~1,712 unique values, each appearing twice per file. This is `historical_id`, a nullable attribute and never a join key in any serving path."
}
```
```json
{
    "ref":  "docs/data-access.md:336",
    "claim":  "The export was configured with \u0027Replace accents\u0027 OFF specifically because it \u0027mangles names and breaks validation against names.dat\u0027. That care is undone if the comparison runs under an accent-insensitive collation."
}
```
```json
{
    "ref":  "ops/mysql-bootstrap.sql:23-24",
    "claim":  "`CREATE DATABASE IF NOT EXISTS ootp CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci` — accent-insensitive AND case-insensitive. An \u0027exact string equality\u0027 comparison performed in SQL under this collation is not exact, which is SD-13\u0027s unresolved collation decision sitting on disk as a wrong default."
}
```
```json
{
    "ref":  "ops/mysql-bootstrap.sql:32-33",
    "claim":  "`CREATE DATABASE IF NOT EXISTS ootp_truth_osa` plus its grant at :49 — the schema Decisions 10 retires, because ootp_truth_real already carries both scouting perspectives from one export."
}
```
```json
{
    "ref":  "tests/test_no_leaks.py:106-107",
    "claim":  "`banned_names = {\"players.csv\", \"names.xml\", \"world_default.xml\", \"schools.xml\"}` and `banned_suffixes = {\".dat\", \".lg\"}` applied to every tracked path. This is why no fixture may be named *.dat — and why a RENAMED copy of players.csv would sail straight through, which is the hard bind on the names fallback."
}
```
```json
{
    "ref":  "tests/test_no_leaks.py:31-48",
    "claim":  "`tracked_text_files()` enumerates via `git ls-files`, so the guard cannot see a new file until it is staged. A leak in an untracked rendered artifact passes locally and only fails in CI — the feedback-loop gap the scope files as a follow-up."
}
```
```json
{
    "ref":  "tests/test_no_leaks.py:24-28",
    "claim":  "The three leak PATTERNS (windows drive path, unix home path, email). The new rendered-game-data guard reuses these rather than inventing a second set, so a tracked catalog carrying an absolute path trips the existing regex."
}
```
```json
{
    "ref":  "tests/test_doc_links.py:22-37",
    "claim":  "Every `[..](..)` in every tracked .md is resolved against the filesystem, with no exemption for fenced code blocks and none for `var/` targets. A tracked Markdown link into the ignored output root turns CI red, which is why the catalog\u0027s report pointer is a code span."
}
```
```json
{
    "ref":  "tests/test_repo_structure.py:64-67",
    "claim":  "`test_var_is_gitignored` asserts a bare `var/` line in .gitignore. Combined with .gitignore:18 this is what makes acceptance criterion 14\u0027s `git check-ignore -q` assertion hold for the report output root."
}
```
```json
{
    "ref":  "tests/test_agent_contract.py:46-66",
    "claim":  "`test_rulebook_invariants_survive` pins ten invariant strings in the data-engineer definition, including \u0027fixed offset\u0027, \u0027players.csv\u0027, \u0027unconfirmed\u0027 and \u0027immutable\u0027. Any edit to that file during this feature must keep all ten present."
}
```
```json
{
    "ref":  "tests/fixtures/README.md:45-51",
    "claim":  "\u0027A real save\u0027s day-0 state is the LEAST informative test input available: every variable-length region is at its minimum, so a parser that seeks to a fixed offset passes cleanly and fails later in production.\u0027 This is the argument for synthetic byte builders over any captured bytes."
}
```
```json
{
    "ref":  ".gitignore:18",
    "claim":  "A bare `var/` rule makes the whole scratch root ignored — the basis for criterion 14\u0027s git-ignored-output-root proof."
}
```
```json
{
    "ref":  ".gitignore:62",
    "claim":  "`!tests/fixtures/**` re-includes the fixtures directory after the `*.dat` ignore at :31. So a fixture named *.dat WOULD be trackable by git and would then be caught by test_no_leaks.py:107 — the guard is the backstop, not gitignore."
}
```
```json
{
    "ref":  ".env.example:25",
    "claim":  "\u0027MUST be on local disk, not a cloud-synced folder — snapshots are ~600MB each. Defaults to var/snapshots.\u0027 The documented default the config layer must produce without a parents[N] walk."
}
```
```json
{
    "ref":  ".env.example:57-58",
    "claim":  "MYSQL_TRUTH_REAL_DATABASE and MYSQL_TRUTH_OSA_DATABASE. The second is retired by Decisions 10; the first is the Tier B validator every differential test reads."
}
```
```json
{
    "ref":  "docs/league-rules.md:129",
    "claim":  "\u0027The parser reads `leagues.dat` directly and may recover some of these.\u0027 Grep-confirmed at this exact line — one of the two false assertions acceptance criterion 19 removes."
}
```
```json
{
    "ref":  "docs/league-rules.md:295",
    "claim":  "\u0027Until the parser can open `leagues.dat`, every value here is believed rather than confirmed for our league.\u0027 Grep-confirmed at this exact line (the scope\u0027s citation is correct; adversary finding SD-27\u0027s proposed correction to :296 is wrong)."
}
```
```json
{
    "ref":  "docs/league-rules.md:26",
    "claim":  "§1 is described as \u0027Temporary. Every value is a column on the leagues row; the warehouse supersedes this the moment the parser lands.\u0027 This slice lands the parser without landing the league config, so the sentence becomes partially false on delivery — the doc gate must catch it."
}
```
```json
{
    "ref":  "docs/league-rules.md:79-81",
    "claim":  "`schedule_file_1 = major_league_ml_c_2024.lsdl` — the exact string the scope measured at byte 5,559,751 of OOTP-AI.lg/world.dat, which is what located the league configuration block outside teams.dat."
}
```
```json
{
    "ref":  "gm/standing-orders.md:42-50",
    "claim":  "The per-report format block (Established / Owner / Policy / Rationale / Review trigger). Decisions 4 requires extending it with an engineering-owned kind, because gm/staff.md:5-8 records that no staff exist and naming an owner would be fiction."
}
```
```json
{
    "ref":  "gm/README.md:19",
    "claim":  "The placement rule: \u0027Can this be rebuilt from the save? Yes -\u003e var/. No -\u003e here.\u0027 This is what routes the rendered reports into the ignored root while the DECISION that they exist stays tracked in standing-orders."
}
```
```json
{
    "ref":  ".claude/agents/gm.md:4",
    "claim":  "`tools: Read, Glob` — the entire delivery surface for this feature. The GM cannot query, cannot run a command, and cannot open a .dat; a Markdown file handed into its context is the only channel."
}
```
```json
{
    "ref":  ".claude/agents/gm.md:32",
    "claim":  "Forced-read item 8: \u0027Any report or analysis handed to you for this invocation.\u0027 Acceptance criterion 20 is a spawn that exercises exactly this line."
}
```
```json
{
    "ref":  "docs/decisions/0012-scouted-ratings-only.md:75-76",
    "claim":  "\u0027The corollary for the parser: an unclassified rating field is not \"probably fine.\" Under this ADR it is withheld until classified.\u0027 This is the rule policy.py::is_renderable() encodes."
}
```
```json
{
    "ref":  "docs/decisions/0005-hybrid-data-layer.md:66-71",
    "claim":  "The boundary rule verbatim, and the worked example that players.csv resolves as STATIC REFERENCE — \u0027its day-0 snapshot role is a use, not its nature\u0027. This is what keeps this feature off the datasets/ side and out of build/."
}
```
```json
{
    "ref":  "docs/decisions/0004-mysql-warehouse.md:94-106",
    "claim":  "The four live adapter options and \u0027The decision comes due when the first dbt model is requested.\u0027 Decisions 9 defers rather than resolves, and records the deferral as a note here rather than as a superseding ADR."
}
```
```json
{
    "ref":  "requests/feature-requests/README.md:70-85",
    "claim":  "\u0027Testable\u0027 means a cold agent runs one command and gets a pass or fail; criteria only a human can prove must be marked user-run \u0027so the acceptance panel doesn\u0027t claim them\u0027. Criteria 20 and 21 are those."
}
```
```json
{
    "ref":  "requests/feature-requests/README.md:119",
    "claim":  "The Index row for first-sight currently reads `scoped`. /commit Step 4 advances it to `plan` when the IMPLEMENTATION_PLAN lands and to `implemented` at the end of stage 4."
}
```
```json
{
    "ref":  "requests/feature-requests/first-sight/PROJECT_SCOPE.md:5-9",
    "claim":  "The citation convention this feature\u0027s artifacts must follow: code spans, not Markdown links, wherever a citation carries a file:line suffix or points into var/ — because both forms fail tests/test_doc_links.py today, a live defect with an open bugfix request."
}
```
```json
{
    "ref":  ".claude/skills/create-implementation-plan/SKILL.md:251",
    "claim":  "The skill\u0027s \u0027What good looks like\u0027 section cites `tests/test_request_links.py` as \u0027a blocking CI check\u0027. That file does not exist in this repo — the only link guard is tests/test_doc_links.py. Do not plan around a check that isn\u0027t there."
}
```

### open_questions

- The task brief names `docs/data-sources.md` as the source-coverage document. It does not exist — `Glob docs/*.md` returns exactly `docs/data-access.md` and `docs/league-rules.md`. This plan treats docs/data-access.md as the intended file, and honours the brief's rule literally: every `unconfirmed` claim it depends on is verified by a phase before the phases that build on it (the scouted view in phase 1, the names.dat encoding in phase 6, the saved_games.dat plaintext claim in phase 4). Confirm this substitution before implementation starts.
- The scope's Core 15 requires the tracked catalog to name 'the `.env` key and relative path' each report resolves to, but Core 19 budgets only TWO new .env keys (the probe save directory and the Challenge Mode probe save). A report/catalog output root key is a third. This plan adds it as required-by-Core-15 rather than as scope creep, but the operator should confirm the key's name and whether it defaults under `var/` or under OOTP_SNAPSHOT_ROOT.
- Decisions 2 makes the ledger row a USER-RUN umpire act after delivery, while gm/standing-orders.md:45 requires every entry to carry `**Established:** ledger seq <n>`. The two report entries therefore cannot cite a seq at the time they are written. This plan lands them with an explicit engineering-owned marker in place of a seq and leaves the ledger row to the operator — confirm that is the intended resolution rather than blocking the standing-orders edit until the ledger row exists.
- What exactly is `save_id`? The scope requires it in every primary key (SD-09) but never defines it. This plan uses the save directory name without the `.lg` extension (e.g. `OOTP-AI`), which is stable, human-readable, already public in gm/ documents, and carries no machine-specific path. The alternative — a digest of the save's header/manifest — is more precise but unreadable in a report. Confirm the choice before the DDL is emitted, because changing it later re-keys every bronze table.
- Strict byte accounting on teams.dat is asserted by the scope as 'plausible' with no evidence behind it; docs/data-access.md:228 marks everything beyond the 5-string signature and colors `unconfirmed` for that file. If the strict tier proves unreachable, is the pre-registered demotion (record the residual, assert record-boundary termination, file a follow-up) acceptable — or is a full teams.dat map a genuine blocker for phase 4?
- The scope treats the scouted-view spike as gating 'only the ratings half', but if the verdict is COMPUTED, ADRs 0012, 0014 and 0016 lose their data path entirely. This slice ships either way by design. Does an ABSENT verdict trigger an immediate follow-up request against those three ADRs, or is that deferred until a ratings slice is actually proposed?
- Reports are regenerated in place, which overwrites the prior snapshot's view and breaks citation integrity for any gm/decisions/ record that cites one (SD-21, explicitly flagged for the plan and not solved by the scope). This plan proposes writing under a snapshot-dated subdirectory so regeneration is additive. Confirm — it changes the path the catalog's report pointer names, and therefore what the umpires hand the GM.

---

## Lens: (unnamed lens)

### planner

sequencing

### ok

```json
true
```

### onboarding_files

```json
{
    "path":  "requests/feature-requests/first-sight/PROJECT_SCOPE.md",
    "why":  "The decided upstream artifact. Its 21 Acceptance Criteria are the phase-completion contract; its Core tier (§1-§21) is the build list; its Decisions (§1-§11) are already disposed and must NOT be re-litigated. Note the two structural constraints the phasing must honour: the Acceptance preamble\u0027s \u0027all files under tests/ are authored by the main thread\u0027, and the marker note widening `gamedata`."
}
```
```json
{
    "path":  ".claude/agents/data-engineer.md",
    "why":  "The single owner of the build rules and the only write-capable subagent. Load-bearing for phasing: `:69-72` fixed-offset ban, `:91-92` never require a game install to satisfy a test, `:98` bronze is 1:1 with parser output, `:101` grain in prose AND proved, `:117-119` no OOTP game data in git, and the deny-set fence at `:149-158` that lists `tests/` first. Every phase\u0027s subagent spec must declare targets under `src/ootp_ai/**` only."
}
```
```json
{
    "path":  "docs/data-access.md",
    "why":  "The catalog of beliefs the parser rests on, with epistemic labels that are load-bearing. `:14` defines what `unconfirmed` obligates; `:60-63` the stray `.lg` directory that breaks a glob enumerator; `:65-68` challenge.dat at 241 bytes; `:172-181` the header layout with the magic at offset 1; `:224-226` the `verified` teams.dat 5-string signature; `:238` the `unconfirmed` names.dat encoding; `:282-295` the critical-path scouted-view question and the exact test that has never been run."
}
```
```json
{
    "path":  "pyproject.toml",
    "why":  "Every gate the phases end on is configured here. `:9` `dependencies = []` (the first runtime dependency is a decision, not an import); `:69-73` mypy strict over BOTH `src` and `tests`; `:78` `--strict-markers` makes an undeclared marker a hard collection error; `:79-81` declares exactly one marker, `gamedata`, whose text must be widened in phase 1 before any warehouse test can collect."
}
```
```json
{
    "path":  ".github/workflows/ci.yml",
    "why":  "`:49` runs `uv run pytest -m \"not gamedata\"` — CI\u0027s actual condition. Any phase whose acceptance rests only on gamedata tests has no CI signal, so each phase must also carry an offline assertion. `:37-44` pin the exact lint/format/type commands a phase must be green on before /commit."
}
```
```json
{
    "path":  "tests/test_no_leaks.py",
    "why":  "The guard this feature is most likely to trip. `:31-48` enumerates via `git ls-files`, so an untracked leak passes locally and fails in CI; `:97-116` bans four filenames and the `.dat`/`.lg` suffixes — which is why fixture files must not carry a `.dat` extension, and why the folded-in extension for *rendered* game data lands here."
}
```
```json
{
    "path":  "tests/fixtures/README.md",
    "why":  "Governs every offline fixture the early phases create. `:15-28` the authorship rule (our derived observations yes, any slice of a real save no); `:32-37` what belongs — hand-built synthetic binary records; `:45-51` why synthetic beats real for the variable-length-region tests in phase 3."
}
```
```json
{
    "path":  ".env.example",
    "why":  "The config contract phase 1 extends. `:10-25` the four OOTP keys, with `OOTP_SNAPSHOT_ROOT` documented as defaulting to var/snapshots and empty in the live `.env` (verified: OOTP_INSTALL/OOTP_SAVED_GAMES/OOTP_LEAGUE set, OOTP_SNAPSHOT_ROOT empty); `:57-58` the two truth databases, of which `MYSQL_TRUTH_OSA_DATABASE` is retired by Decisions §10."
}
```
```json
{
    "path":  ".gitignore",
    "why":  "`:18` `var/` is the ignored output root the reports and the volatile catalog half must resolve inside; `:31` `*.dat`; `:62` `!tests/fixtures/**` — a later negation, so git WILL happily track `tests/fixtures/foo.dat`. `tests/test_no_leaks.py::test_game_data_is_not_tracked` is the only thing that catches it. Fixtures therefore take a non-`.dat` extension."
}
```
```json
{
    "path":  "gm/standing-orders.md",
    "why":  "`:27-50` the `## Reports` section and its five-field format block. Core §20 lands the tracked half of the report channel here, and Decisions §4 adds a new engineering-owned report kind to that format block — an umpire edit, not a builder edit, so it is sequenced as a main-thread step in the final phases."
}
```
```json
{
    "path":  ".claude/agents/gm.md",
    "why":  "`:4` `tools: Read, Glob` — the entire delivery surface for this feature; `:32` forced-read item 8 (\u0027Any report or analysis handed to you for this invocation\u0027) is the mechanism acceptance criterion 20 rides on. Read before designing the report file layout."
}
```
```json
{
    "path":  "docs/league-rules.md",
    "why":  "The doc-correction target. `:26` and `:31` claim §1 is superseded by the warehouse \u0027the moment the parser lands\u0027 and become partly false on delivery; `:79-81` records `schedule_file_1 = major_league_ml_c_2024.lsdl`, the string the scope located in `world.dat`; `:129` and `:295` both assert a `leagues.dat` that does not exist and are corrected in phase 2."
}
```
```json
{
    "path":  "requests/feature-requests/README.md",
    "why":  "The pipeline contract. `:70-85` defines what *testable* means here (one command, pass or fail) and requires human-only criteria be marked USER-RUN; `:38-57` the dataset-contract obligations every phase that lands a table must satisfy; `:119` the Index row for this slug whose Stage cell advances."
}
```
```json
{
    "path":  "ops/mysql-bootstrap.sql",
    "why":  "`:23-24` creates the empty `ootp` schema the loader lands into; `:32-33` and `:49` create and grant on `ootp_truth_osa`, which Decisions §10 retires. The utf8mb4 note at `:35-38` is the starting point for the SD-13 collation decision the differential phase has to make explicit."
}
```
```json
{
    "path":  "tests/test_agent_contract.py",
    "why":  "`:69-75` asserts `tests/` stays in the data-engineer\u0027s deny set. This is the mechanical reason every phase below splits authorship: the subagent builds `src/ootp_ai/**`, the main thread writes every test. Hand a phase\u0027s whole spec to the subagent and you get an Escalation and zero tests."
}
```

### architecture_notes

CURRENT STATE (measured 2026-08-16). `src/ootp_ai/` contains exactly one file, `src/ootp_ai/__init__.py`, whose entire body is a docstring plus `__version__ = "0.1.0"` at `:7`. `pyproject.toml:9` declares `dependencies = []`. `transform/`, `build/`, `datasets/` and `var/` do not exist as tracked things. `tests/` holds four structural guards and no parser test. The `ootp` MySQL schema exists with 0 tables. Every module below is created from nothing.

TARGET SHAPE. A layered package under `src/ootp_ai/`, ordered so each layer only depends on layers already proven by an earlier phase:

  config.py        — resolves OOTP_INSTALL / OOTP_SAVED_GAMES / OOTP_LEAGUE / OOTP_SNAPSHOT_ROOT / probe keys / MySQL from `.env` only. No literal path, no `parents[N]` outside test modules (`.claude/agents/data-engineer.md:88-90`). Validates OOTP_SNAPSHOT_ROOT is local disk, defaulting to `var/snapshots` per `.env.example:22-25`.
  db.py            — read-only connections to `ootp_truth_real` and a write connection to `ootp`. Owns the SD-13 collation decision and the folded-in backtick rule for every identifier in export-diff SQL.
  saves.py         — the enumerator. A directory is a save only if `players.dat` AND `teams.dat` are present; a `*.lg` glob is not a list of saves (`docs/data-access.md:60-63`). Also the `challenge.dat`-at-241-bytes mode check (`:65-68`).
  parser/primitives.py — a forward-only Cursor over a bytes buffer exposing u8/u16/u32/f64, length-prefixed ASCII string, `u8 day,u8 month,u16 year` date, u32 ARGB. The cursor has no `seek`; advancing is the only operation. This is the single structural reason the fixed-offset ban holds, rather than a review convention.
  parser/header.py — the shared header reader: leading 0x00, `b"OOTP"` at offset 1, u32 version at offset 5 (must be 25), null-padded self-declared filename at offset 25 cross-checked against the file opened. Raises a named `UnsupportedSaveVersion`. Every walker opens through this (`docs/data-access.md:172-189`).
  snapshot.py      — copies ONLY the in-scope ~46 MB set (players + names + teams) to `<snapshot_root>/<league>/<sim_date>/`, writes a per-file size + SHA-256 manifest, every handle `"rb"`. All parsing runs against the snapshot, never the live save.
  parser/teams.py, parser/names.py, parser/players.py, parser/rosters.py — sequential walkers, each returning plain dataclasses and a byte-accounting residual.
  contracts/       — the tracked field-map / contract declaration. Recommend TOML read with stdlib `tomllib` (Python 3.12) so it adds no dependency. ONE declaration with THREE consumers: the DDL emitter, the grain-contract test, and the catalog generator. That is what makes prose-vs-enforcement drift structurally impossible rather than merely discouraged.
  warehouse/ddl.py, warehouse/loader.py — emits `bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name` DDL from the declaration; loads append-only per (`snapshot_date`, `save_id`) partition; writes the ingest-run row.
  reports/__main__.py — `uv run python -m ootp_ai.reports render`; roster.py and standings.py render Markdown into the git-ignored output root. The organization filter lives HERE, never at bronze (`.claude/agents/data-engineer.md:98`).
  catalog/__main__.py — `uv run python -m ootp_ai.catalog`; emits the tracked structural half (deterministic, sorted, no timestamps, no absolute paths) and the volatile half + `catalog.json` into the ignored root.

WHERE THE CHANGE HOOKS INTO WHAT EXISTS. Four existing tracked files are edited rather than created: `pyproject.toml` (runtime deps + the widened `gamedata` marker text), `.env.example` (two new probe keys, retire `MYSQL_TRUTH_OSA_DATABASE`), `ops/mysql-bootstrap.sql` (drop the `ootp_truth_osa` create at `:32-33` and its grant at `:49`), and `tests/test_no_leaks.py` (the rendered-game-data extension). Two docs are corrected: `docs/league-rules.md:129` and `:295`. Everything else is new.

THE ONE ARCHITECTURAL SEAM THAT DRIVES THE PHASING. `tests/` is the first entry in the data-engineer's deny set (`.claude/agents/data-engineer.md:150`), asserted by `tests/test_agent_contract.py:69-75`. So every phase below is split: the subagent's spec declares targets under `src/ootp_ai/**` (plus the contracts declaration) and nothing else; the main thread writes the phase's tests and fixtures. A phase spec that names a `tests/` path returns an Escalation with zero code built.

### phases

```json
{
    "name":  "Phase 1 — Foundation: dependencies, config layer, DB read access, marker widening",
    "goal":  "Make the repo compile-and-collect a warehouse-touching test suite at all, and establish the one config layer every later phase resolves paths through. Contains NO parser code and NO ratings code, so it does not violate the scope\u0027s spike-first ordering — it exists first only because the spike itself needs `.env`-resolved paths and a `ootp_truth_real` connection, and hardcoding those in a scratch script would violate Core §2 on the very first artifact.",
    "steps":  [
                  "Choose and pin the first runtime dependencies in `pyproject.toml` (currently `dependencies = []` at `:9`). Two are needed: a `.env` loader (`python-dotenv` is already in the dev group at `:23` — promote it to `[project] dependencies`) and a MySQL driver. Recommend `PyMySQL` plus `types-PyMySQL` in the dev group, because `pyproject.toml:69-73` runs mypy strict over `src` AND `tests` and an unstubbed driver makes every `db.py` call an untyped-call error. Record the choice and the stub story in the plan\u0027s Decisions.",
                  "Widen the `gamedata` marker text at `pyproject.toml:80` from \u0027requires a local OOTP install or save\u0027 to \u0027requires a local OOTP install, save, or warehouse\u0027. Do this FIRST: `addopts` at `:78` carries `--strict-markers`, so until this lands every warehouse-reading test in every later phase is a hard collection error, not a failure.",
                  "Write `src/ootp_ai/config.py`: a frozen dataclass resolved once from `.env`, exposing `ootp_install`, `ootp_saved_games`, `ootp_league`, `snapshot_root`, `probe_saved_games`, `challenge_probe_league`, and the MySQL settings. No literal path, no `parents[N]` walk. `snapshot_root` defaults to `var/snapshots` (`.env.example:22-25`) and is validated as local disk — the same file warns the saved-games root may be OneDrive-redirected.",
                  "Write `src/ootp_ai/db.py`: a read-only connection factory for `ootp_truth_real` and a write factory for `ootp`. Bake in the folded-in cheap win now, at the point of creation rather than as a later retrofit: every identifier in export-diff SQL is backticked. The measured incident is `select current_date from ootp_truth_real.leagues` returning the wall-clock date for all 15 rows because MySQL parses the bare column name as the `CURRENT_DATE` function.",
                  "Add the two new keys to `.env.example` (probe save directory, disposable Challenge Mode probe league) and retire `MYSQL_TRUTH_OSA_DATABASE` at `:58` per Decisions §10. Mirror the retirement in `ops/mysql-bootstrap.sql` — delete the create at `:32-33` and the grant at `:49`.",
                  "MAIN THREAD writes `tests/test_config.py` (offline): config raises a named error on a missing required key; the snapshot-root default resolves under `var/`; no tracked module contains an absolute path (this is already covered by `tests/test_no_leaks.py` but assert the config module specifically resolves everything through `.env`).",
                  "MAIN THREAD writes `tests/test_db_identifiers.py` (offline): the SQL-building helper backticks a reserved identifier — pass it `current_date` and assert the emitted fragment is `` `current_date` ``. This is the regression test for the measured incident and it needs no database."
              ],
    "acceptance":  [
                       "`uv run pytest -m \"not gamedata\" tests/test_config.py tests/test_db_identifiers.py` is green with no game install and no MySQL server running.",
                       "`uv run pytest --collect-only -m gamedata` collects without error using a throwaway test carrying the marker — proving the widened marker declaration at `pyproject.toml:80` is in place before any later phase depends on it.",
                       "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` are all clean, including the new MySQL driver import under strict mode.",
                       "`uv run pytest -m \"not gamedata\"` — the four pre-existing guards (`test_no_leaks.py`, `test_repo_structure.py`, `test_agent_contract.py`, `test_doc_links.py`) all still green.",
                       "`grep -r MYSQL_TRUTH_OSA_DATABASE` returns hits only in an explicit retirement note, not as a live key in `.env.example` or `ops/mysql-bootstrap.sql`."
                   ],
    "commit_note":  "Green locally on all four commands, then hand to the user for `/commit`. This is the phase that changes `pyproject.toml`\u0027s dependency posture — a deliberate first, since the file\u0027s own comment at `:11-15` says the first real dependency arrives with the warehouse loader, so `/update-docs` should be expected to flag that comment for revision. Reversible: reverting this commit returns the repo to a zero-dependency state with no orphaned code."
}
```
```json
{
    "name":  "Phase 2 — The scouted-view spike, its pre-registered pivot, and the leagues.dat doc correction",
    "goal":  "Resolve or explicitly reaffirm the one `unconfirmed` claim that can invalidate ADRs 0012/0014/0016 (`docs/data-access.md:282-295`), with the kill/pivot rule committed BEFORE the spike runs — and land the guaranteed doc correction that needs no parser at all. Highest-uncertainty work, first, exactly as the scope\u0027s Core §1 requires.",
    "steps":  [
                  "FIRST, before running anything: write `requests/feature-requests/first-sight/reviews/scouted-view-spike.md` containing the pre-registered pivot rule — what FOUND means (the parser has its source; ratings become a follow-up request), what ABSENT means (record it, withhold every rating, ship the reports anyway, and `docs/data-access.md` §5 stays `unconfirmed`), and what evidence would count as either. Committing the rule before the result is what stops the verdict being written to suit whatever came back.",
                  "Run the spike as a throwaway script under `var/` (git-ignored, `.gitignore:18`), not as tracked source: read the probe save\u0027s `scouting.dat` (2,349,181 bytes) through `\"rb\"` and search for the values held in `ootp_truth_real.players_scouted_ratings` (36,144 rows, `scouting_coach_id` ∈ {-1, 2759}, 18,072 each). Search for both the raw ~1-1000 encoding and the display-scale encoding — a null result on one scale alone is not ABSENT.",
                  "Write the verdict into the same spike file: stored-or-computed, an epistemic label, the byte evidence, and which pre-registered branch is now live. Cite byte positions, never a screenshot (`.claude/agents/data-engineer.md:75-78`).",
                  "Correct `docs/league-rules.md:129` (\u0027parser reads `leagues.dat` directly\u0027) and `:295` (\u0027Until the parser can open `leagues.dat`\u0027). Neither file exists: `OOTP-AI.lg` holds 18 `.dat` files and none is it. Replace with the measured location of the league configuration block — `major_league_ml_c_2024.lsdl`, exactly the `schedule_file_1` value recorded at `docs/league-rules.md:80`, at byte 5,559,751 of `world.dat`, surrounded by league-shaped records containing `World Series`, `AL` and `NL`. Note the doc-writing route: `docs/data-access.md` is in the subagent\u0027s deny set (`.claude/agents/data-engineer.md:156`), so any data-fact deltas travel as a docs-delta through `/update-docs` — `docs/league-rules.md` is not in the deny set and may be edited directly.",
                  "MAIN THREAD writes `tests/test_doc_corrections.py` (offline): asserts the string `leagues.dat` appears nowhere under `docs/` except on a line also containing an explicit correction marker. Keep the exemption mechanism narrow and explicit — a whole-file exemption turns the guard off."
              ],
    "acceptance":  [
                       "`requests/feature-requests/first-sight/reviews/scouted-view-spike.md` exists, carries a verdict with an epistemic label and cited byte evidence, and its pivot rule appears in the file\u0027s git history at an earlier commit than the verdict — or, if landed in one commit, the file states plainly that the rule was written first.",
                       "`uv run pytest -m \"not gamedata\" tests/test_doc_corrections.py` is green: no `leagues.dat` assertion survives in `docs/` outside a marked correction note.",
                       "`docs/data-access.md` §5\u0027s `unconfirmed` label at `:282` is either upgraded with the spike\u0027s evidence or explicitly reaffirmed as still open — routed through `/update-docs`, not edited by a subagent.",
                       "`uv run pytest -m \"not gamedata\"` and `uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy` are all clean; `tests/test_doc_links.py` in particular stays green after the `docs/league-rules.md` edits.",
                       "No tracked file gained a `.dat`, a save slice, or an absolute path — `uv run pytest tests/test_no_leaks.py` green."
                   ],
    "commit_note":  "Hand to the user for `/commit`. This phase produces a decision artifact and a doc correction and no runtime code, so it is trivially reversible and carries zero regression surface. If the verdict is ABSENT, STOP HERE and re-confirm with the user before continuing: the pre-registered pivot says the slice still ships, but the user should dispose that explicitly rather than have the plan carry them past a FAIL verdict silently."
}
```
```json
{
    "name":  "Phase 3 — Parser spine: forward-only primitives, header/version guard, save enumerator, fixed-offset source guard",
    "goal":  "Establish the parser\u0027s spine once, correctly, and prove all three of its invariants OFFLINE — because `.github/workflows/ci.yml:49` runs `-m \"not gamedata\"` and a spine proved only by gamedata tests has no CI signal at all. This is the phase that makes the fixed-offset ban structural rather than a review convention.",
    "steps":  [
                  "Write `src/ootp_ai/parser/primitives.py`: a `Cursor` over a `bytes` buffer with `read_u8/u16/u32/f64`, `read_string` (u32-LE length prefix, raw ASCII, no terminator — `docs/data-access.md:195`), `read_date` (`u8 day, u8 month, u16 year`), `read_color` (u32 ARGB). Deliberately expose NO seek and NO absolute-position read: advancing is the only operation. Every field read is relative to where the walk already is.",
                  "Write `src/ootp_ai/parser/header.py`: reads the leading `0x00`, asserts `b\"OOTP\"` at offset 1, reads the u32 version at offset 5 and raises a named `UnsupportedSaveVersion` on anything but 25, then reads the null-padded self-declared filename at offset 25 and cross-checks it against the file actually opened (`docs/data-access.md:172-189`). The five fixed header words are the ONE place a constant position is legitimate; comment it so a future reader does not mistake it for permission.",
                  "Write `src/ootp_ai/saves.py`: enumerate saves by confirming `players.dat` AND `teams.dat` are present in a candidate directory, never by a `*.lg` glob — the saved-games root contains a stray empty directory literally named `.lg` (`docs/data-access.md:60-63`). Add the `challenge.dat`-at-exactly-241-bytes mode check (`:65-68`) and promote both it and the header filename cross-check to a pre-flight that runs on every invocation (folded-in cheap win #6).",
                  "MAIN THREAD builds synthetic fixtures under `tests/fixtures/`, hand-authored byte sequences, never a slice of a real save (`tests/fixtures/README.md:15-28`). Give them a non-`.dat` extension: `.gitignore:62`\u0027s `!tests/fixtures/**` negation re-includes `*.dat` from `:31`, so git would track them happily and only `tests/test_no_leaks.py:97-116` would catch it — as a red build.",
                  "MAIN THREAD writes `tests/test_save_header.py` (offline, AC1): a synthetic header with byte 0 = `0x00`, `b\"OOTP\"` at offset 1 and u32 25 at offset 5 parses; version 24 and version 26 EACH raise `UnsupportedSaveVersion` by name; a buffer whose `bytes[0:4] == b\"OOTP\"` is rejected; a header whose self-declared filename disagrees with the file opened is rejected.",
                  "MAIN THREAD writes `tests/test_sequential_walk.py` (offline, AC2): two synthetic records identical except for the length of a variable-length region — a 1-year vs a 10-year contract array — must yield identical values for every field parsed AFTER that region. Include a NEGATIVE CONTROL in the same module: a deliberately fixed-offset local reader asserted to FAIL the same comparison. Without it, a test that passes proves nothing about whether it could ever fail.",
                  "MAIN THREAD writes `tests/test_no_fixed_offsets.py` (offline, AC3): a static AST or source scan over `src/ootp_ai/parser/` finding zero `.seek(\u003cnonzero int literal\u003e)` calls and zero `struct.unpack_from` with a constant record-relative offset. This encodes `.claude/agents/data-engineer.md:69-72` as a mechanical check. Include a self-test proving the scanner flags a synthetic offending snippet, so a scanner that silently matches nothing cannot pass.",
                  "MAIN THREAD writes `tests/test_save_enumerator.py`: offline portion against a tmp_path directory tree containing a decoy `.lg` with no `.dat` files; `-m gamedata` portion running against the DISPOSABLE Challenge Mode probe save FIRST (SD-20, folded-in #9), and only then against `OOTP-AI.lg`."
              ],
    "acceptance":  [
                       "`uv run pytest -m \"not gamedata\" tests/test_save_header.py` is green with no game install (AC1), including both the version-24 and version-26 raises and both rejection cases.",
                       "`uv run pytest -m \"not gamedata\" tests/test_sequential_walk.py` is green (AC2), AND its negative control confirms the fixed-offset reader fails — run `uv run pytest tests/test_sequential_walk.py -v` and read the control test\u0027s name in the output.",
                       "`uv run pytest -m \"not gamedata\" tests/test_no_fixed_offsets.py` is green (AC3) and its scanner self-test proves it can still flag an offending pattern.",
                       "`uv run pytest -m gamedata tests/test_save_enumerator.py` is green: the stray `.lg` directory is not enumerated as a save, and the probe save is enumerated before the managed league in the test\u0027s own ordering.",
                       "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean; `uv run pytest -m \"not gamedata\"` fully green including all four pre-existing guards.",
                       "`git status` shows no new tracked file with a `.dat` extension; `uv run pytest tests/test_no_leaks.py` green."
                   ],
    "commit_note":  "Hand to the user for `/commit`. This is the phase whose acceptance a cold reviewer should scrutinise hardest, because everything downstream inherits it. Regression safety: the three offline tests here run in CI on every subsequent PR, so a later phase that introduces a seek or a fixed offset goes red immediately rather than at the next data incident. Reversible: no data has been landed and nothing has been copied off the save."
}
```
```json
{
    "name":  "Phase 4 — Snapshot copy, content-hash manifest, and the ADR 0001 read-only proof",
    "goal":  "Get every later phase parsing a snapshot rather than the live save, and prove mechanically that nothing under the game directories was touched. ADR 0001 is the one unrecoverable failure in the project, so it gets a test rather than a promise — and it lands BEFORE the phases that open the big files, not after.",
    "steps":  [
                  "Write `src/ootp_ai/snapshot.py`: copy only the in-scope set — `players.dat` (32,070,106 B), `names.dat` (8,642,110 B), `teams.dat` (5,318,831 B), ~46 MB total, NOT the ~600 MB `.lg` — into `\u003csnapshot_root\u003e/\u003cleague\u003e/\u003csim_date\u003e/`. Every handle opened `\"rb\"`. Write a per-file size + SHA-256 manifest alongside. Assert Challenge Mode from the filesystem via `challenge.dat` at exactly 241 bytes rather than from a menu.",
                  "Add the ingest-run record shape as a plain dataclass in `src/ootp_ai/ingest.py` — source file sizes, SHA-256 digests, header versions, sim date, human team, and placeholders for row counts, residual bytes and wall-clock parse time. It is not persisted to MySQL until phase 9; landing the SHAPE here means the later phases fill fields rather than inventing a schema under time pressure.",
                  "Resolve the human team and sim date FROM DATA on every run (folded-in cheap win #7), reading `saved_games.dat` through the SAME header reader plus a string walk from phase 3 — never a substring scrape. Finding F19 corrects `docs/data-access.md:36-38`: it is NOT plaintext. It also embeds an absolute user-profile path per save, so nothing that renders its contents may reach a tracked file. Measured expectation: `OOTP-AI` is Boston at 2024-03-07; the probe save is the Chicago Cubs at 2024-03-18. Any code that hardcodes \u0027we are team 6\u0027 passes on ground truth and breaks on our league, invisibly.",
                  "MAIN THREAD writes `tests/test_read_only.py` (`-m gamedata`, AC11): take a manifest of modification time + SHA-256 for every file under `$OOTP_SAVED_GAMES` and `$OOTP_INSTALL` before the run and after, and assert zero differences. Sequence it against the DISPOSABLE Challenge Mode probe save first and only then `OOTP-AI.lg` (SD-20). The test must skip loudly with a named reason if the paths are unset — never pass vacuously.",
                  "MAIN THREAD writes the snapshot half of `tests/test_snapshot_semantics.py` (`-m gamedata`): copying the same snapshot twice leaves the manifest digests unchanged; re-landing an existing snapshot directory does not silently overwrite it. The parser-output-byte-identical and warehouse-row-count halves of AC10 are added in phases 7 and 9 as their subjects come into existence.",
                  "MAIN THREAD writes an offline test asserting the resolved snapshot root is git-ignored, proven the way AC14 requires: `git check-ignore -q \u003cpath\u003e` exits 0 AND `git ls-files` lists no file under it. The earlier \u0027outside the git worktree\u0027 phrasing is unsatisfiable because `var/` is inside the worktree and merely ignored."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_read_only.py` is green against the probe save AND then `OOTP-AI.lg` — zero modification-time and zero digest differences across both game roots (AC11).",
                       "`uv run pytest -m gamedata tests/test_snapshot_semantics.py` is green for the snapshot-immutability assertions available at this phase.",
                       "`uv run pytest -m \"not gamedata\"` includes the git-ignored-root assertion and is green; running it in a clean clone with no `.env` skips rather than errors.",
                       "A snapshot directory exists under the resolved root containing exactly three `.dat` files and one manifest, and `git status` shows nothing new to stage under it.",
                       "`uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy` clean."
                   ],
    "commit_note":  "Hand to the user for `/commit`. Pair this checkpoint with acceptance criterion 21 as a USER-RUN step the user can perform now rather than at the end: the operator confirms `OOTP-AI.lg`\u0027s file set, sizes and modification times by hand against the recorded manifest — an independent check that does not rely on the code that would be the thing violating it. Doing it here, at ~46 MB of copying, is far cheaper than discovering a violation after the full parse."
}
```
```json
{
    "name":  "Phase 5 — teams.dat sequential walk and the team dimension",
    "goal":  "Land the first real walk against the file where a full byte accounting is plausible and where `docs/data-access.md:224-226` already records the signature as `verified` — so the walk is validated against an existing belief rather than establishing one. This is the lowest-risk walk and it de-risks the walker pattern before the two hard files.",
    "steps":  [
                  "Write `src/ootp_ai/parser/teams.py`: a sequential walk yielding `team_id`, the 5-string signature (city, abbreviation, nickname, logo filename, full name), ARGB colors, level, `parent_team_id` so MLB clubs are distinguishable from affiliates, the sub-league/division hierarchy, and the win-loss fields the standings report needs.",
                  "Implement byte accounting inside the walk: track consumed bytes and return a residual. For `teams.dat` the assertion is STRICT — zero unaccounted bytes — because a full walk is plausible here (blocker F3\u0027s split).",
                  "Land everything the walk yields, all 259 teams across all levels. Do not filter at bronze; `.claude/agents/data-engineer.md:98` forbids it and Decisions §7 accepts the cost. The MLB-only view is a report concern, three phases later.",
                  "Preserve structural absence as `NULL`, never zero. The export writes `0` for `rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows — 14 separate opportunities to commit this exact error, and the parser must not copy the export\u0027s habit.",
                  "MAIN THREAD writes the team half of `tests/test_parse_real_save.py` (`-m gamedata`): exactly 30 teams extract at MLB level with correct abbreviations from `OOTP-AI.lg`, run after the same walk has first succeeded against the probe save.",
                  "MAIN THREAD writes the strict half of `tests/test_byte_accounting.py` (`-m gamedata`, AC12): zero unaccounted bytes walking `teams.dat`.",
                  "MAIN THREAD adds an offline `tests/test_parse_teams_synthetic.py` exercising the walker against a hand-built synthetic two-team buffer, so the walker has CI coverage and is not proved only by gamedata tests."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parse_real_save.py -k team` is green: exactly 30 MLB-level teams with correct abbreviations out of `OOTP-AI.lg`, and the probe save\u0027s 259 total teams walk without error.",
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py -k teams` is green with a residual of exactly zero on `teams.dat`.",
                       "`uv run pytest -m \"not gamedata\" tests/test_parse_teams_synthetic.py` is green — the walker has CI signal without a game install (`.claude/agents/data-engineer.md:91-92`).",
                       "`uv run pytest -m \"not gamedata\" tests/test_no_fixed_offsets.py` still green over the enlarged `src/ootp_ai/parser/` tree — the guard now has a real walker to police.",
                       "`uv run pytest -m gamedata tests/test_read_only.py` re-run and still green after a full `teams.dat` walk.",
                       "ruff check / ruff format --check / mypy clean."
                   ],
    "commit_note":  "Hand to the user for `/commit`. Regression safety: from here on, every phase re-runs `tests/test_read_only.py` and `tests/test_no_fixed_offsets.py` as part of its own acceptance, so the two unrecoverable-failure guards are checked at every checkpoint rather than once at the end. Reversible: the walker produces in-memory objects only; nothing has been landed to MySQL yet."
}
```
```json
{
    "name":  "Phase 6 — names.dat walk and the name join, validated against two independent answer keys",
    "goal":  "Resolve the single largest unknown in the request — the `unconfirmed` `names.dat` encoding at `docs/data-access.md:238` — against a full answer key rather than an impression, and reach a go/no-go on the roster report\u0027s headline feature BEFORE the players walk depends on it. If this phase fails, the pre-registered fallback (Decisions §5) fires here, at a clean checkpoint, rather than being discovered mid-report.",
    "steps":  [
                  "Write `src/ootp_ai/parser/names.py` walking the observed structure: u32 len + ASCII + u32 `0` + u32 monotonic index + three u32s + a `0x27` separator, alphabetically ordered. Keep byte accounting strict for this file — a full walk is plausible (F3).",
                  "Bind SD-10 into the code, not just the docs: `names.dat` is 8,642,110 bytes in ALL THREE saves on disk with THREE DIFFERENT SHA-256 digests. It is a fixed-size, per-save-populated table. Nothing may carry a name index, an index→string expectation, or a cached name table from the probe save into the managed league. Make the name table an object owned by a save, never a module-level constant.",
                  "MAIN THREAD writes `tests/test_names_join.py` (`-m gamedata`, AC7): every name index the parser resolves out of the PROBE save\u0027s `players.dat` matches `ootp_truth_real.players.first_name` / `.last_name` by exact string equality, 100% of compared rows, zero unresolved indices, every failure enumerated per row — never an aggregate pass rate. Declare the collation explicitly (SD-13); `ops/mysql-bootstrap.sql:24` creates the schemas `utf8mb4_0900_ai_ci`, which is accent- and case-INSENSITIVE, so an exact-equality claim under it is weaker than it reads. Decide and state whether the comparison runs under a binary collation in SQL or as a Python string comparison after fetch. The test must skip loudly with a named reason if `ootp_truth_real` is unreachable — a vacuous pass here is the worst outcome available.",
                  "MAIN THREAD writes `tests/test_names_join_boston.py` (`-m gamedata`, AC8) — the Tier-A chain, and the ONLY validation of the join on the league we actually manage. For every player in `OOTP-AI.lg/players.dat` carrying a non-empty `historical_id`, the `names.dat`-resolved first and last name equals `players.csv`\u0027s `FirstName`/`LastName` joined on `LahmanID`, 100% exact, every failure enumerated. Measured expectation: ~1,920 of 18,072 active players carry one.",
                  "MAIN THREAD writes the SD-10 guard: a `-m gamedata` test asserting that resolving the SAME index in the probe save and in `OOTP-AI.lg` is NOT expected to yield the same string. This is a silent-wrong failure with no crash, so it needs a positive assertion, not a comment.",
                  "MAIN THREAD adds the strict `names.dat` byte-accounting case to `tests/test_byte_accounting.py`.",
                  "If the join does not reach 100% on either answer key, STOP and fire the pre-registered fallback rather than routing around it: resolve names from `players.csv` at runtime for the ~1,712 players carrying a Lahman ID, joining at render time into the git-ignored output root with NOTHING tracked. Hard bind either way — never track a Lahman-to-name lookup. `tests/test_no_leaks.py:106` catches `players.csv` by FILENAME ONLY, so a renamed derived copy sails straight through the guard into a public repo."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_names_join.py` is green: 100% exact match against `ootp_truth_real`, zero unresolved indices, and the skip path verified by temporarily unsetting the truth-database key and confirming a NAMED skip reason rather than a pass.",
                       "`uv run pytest -m gamedata tests/test_names_join_boston.py` is green: 100% exact match against `players.csv` on `LahmanID` for every Boston-save player carrying a non-empty `historical_id`, every failure enumerated by player.",
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py -k names` is green with a residual of exactly zero on `names.dat`.",
                       "The SD-10 cross-save test is green: the same index resolves differently across the two saves, asserted positively.",
                       "`uv run pytest -m \"not gamedata\"` fully green — in particular `tests/test_no_leaks.py`, since this is the first phase handling real player names.",
                       "ruff check / ruff format --check / mypy clean."
                   ],
    "commit_note":  "Hand to the user for `/commit`. THIS IS THE PLAN\u0027S DECISION POINT. Before committing, tell the user explicitly which branch fired — the join resolved, or the `players.csv` runtime fallback is now live — because the roster report\u0027s shape differs between them and every later phase inherits the choice. Reversible: if the join is wrong, only this phase\u0027s module is discarded; phases 3-5 stand."
}
```
```json
{
    "name":  "Phase 7 — players.dat walk, roster-list extraction, and the list_id semantics with its pre-registered fallback",
    "goal":  "Land the deliberately minimal player field set and the roster-membership grain — the fan-out the request never names and the one that bites TODAY, on an unsimmed save with no trade in sight, because a player sits on the active list AND the 40-man simultaneously.",
    "steps":  [
                  "Write `src/ootp_ai/parser/players.py` with a deliberately minimal field set: `player_id`, team/organization assignment, position, uniform number, date of birth, bats/throws, the name indices, and `historical_id`. Resist widening it — every landed field is a field somebody re-validates after a game patch. The field set is a maintenance liability, not a free win.",
                  "Write `src/ootp_ai/parser/rosters.py` extracting at the `team_roster` grain (`team_id`, `player_id`, `list_id`). Ground truth for the shape: `ootp_truth_real.team_roster` is 15,672 rows over 7,370 DISTINCT players — not 18,072 — with `list_id` ∈ {1: 7370, 2: 7037, 3: 935, 4: 330}.",
                  "Empirically derive what each `list_id` VALUE means, cross-referencing the counts above against `db_structure_ootp25_mysql.txt`\u0027s `team_roster` columns (which document the columns but NOT the value semantics). Label the result honestly.",
                  "FIRE THE PRE-REGISTERED FALLBACK IF NEEDED (SD-17): if the mapping cannot reach at least `inferred`, land `list_id` as an opaque integer and group the roster report by its raw value with a header line stating the meanings are `unconfirmed`, and file a follow-up request. The report NEVER prints a human label (\u0027active roster\u0027, \u002740-man\u0027) for a `list_id` whose mapping is not labelled at least `inferred` — a wrong label produces a confidently wrong roster with nothing throwing.",
                  "Apply the DIAGNOSTIC byte-accounting tier for `players.dat` (blocker F3): the walk must reach a record count matching an independent count — the export\u0027s `retired = 0` population, 18,072 for the probe save — and TERMINATE ON A RECORD BOUNDARY, with the residual byte count RECORDED in the ingest-run row rather than asserted to be zero. Full byte accounting on `players.dat` is a research task, not a counter; say so in the tier rationale so a later reader does not mistake the weaker assertion for sloppiness.",
                  "MAIN THREAD extends `tests/test_parse_real_save.py` (`-m gamedata`, AC9): against `OOTP-AI.lg`, `player_id` is unique per snapshot; Boston\u0027s roster rows number \u003e= 26 (NOT == 26 — the club is in spring training at 2024-03-07 and a set 26 probably does not exist yet); and ZERO roster rows carry a null or blank display name.",
                  "MAIN THREAD extends `tests/test_byte_accounting.py` with the diagnostic `players.dat` case (AC12): record-count match plus record-boundary termination, residual recorded not asserted-zero.",
                  "MAIN THREAD completes `tests/test_snapshot_semantics.py`\u0027s parser half (AC10): parsing the same snapshot twice produces byte-identical parser output.",
                  "MAIN THREAD adds an offline synthetic-buffer test for the players walker so it has CI signal."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parse_real_save.py` is green in full (AC9): 30 MLB teams with correct abbreviations, `player_id` unique per snapshot, Boston roster rows \u003e= 26, zero null-or-blank display names.",
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py` is green in full (AC12): strict zero on `teams.dat` and `names.dat`, record-count match plus boundary termination on `players.dat` with the residual recorded.",
                       "`uv run pytest -m gamedata tests/test_snapshot_semantics.py -k parser` is green: parsing the same snapshot twice is byte-identical.",
                       "The `list_id` mapping carries an explicit epistemic label; if it is below `inferred`, a follow-up request directory exists and the report path is wired to the opaque-integer fallback — verified by reading the field-map declaration, which is written in phase 8 and must therefore carry a placeholder entry here.",
                       "`uv run pytest -m \"not gamedata\"` green including the new synthetic players test; ruff / format / mypy clean.",
                       "`uv run pytest -m gamedata tests/test_read_only.py` re-run green after a full `players.dat` walk — the largest read this project performs."
                   ],
    "commit_note":  "Hand to the user for `/commit`. Surface the `list_id` label to the user at this checkpoint: whether the roster report will print human list names or raw integers is a visible product decision, and it is cheaper to dispose here than to rework the report in phase 11. Reversible: still nothing landed to MySQL."
}
```
```json
{
    "name":  "Phase 8 — The field-map / contract declaration, grain contracts, and the withheld-field guard",
    "goal":  "Land the ONE tracked declaration that the DDL emitter, the uniqueness tests and the catalog generator all read — three consumers, one source — so prose-vs-enforcement drift becomes structurally impossible rather than merely discouraged. This lands BEFORE the loader, so the loader is written against a declared contract rather than the contract being reverse-engineered from the loader.",
    "steps":  [
                  "Write the declaration as a tracked TOML file under `src/ootp_ai/contracts/` read with stdlib `tomllib` (Python 3.12) — no new dependency. ADR 0006 §Notes explicitly blesses derived schema knowledge as ours and trackable; `.claude/agents/data-engineer.md:117-119` draws the line at OOTP\u0027s data, not our observations.",
                  "Carry per field: name, type, the walker that reads it, category (`identity` / `rating-true` / `rating-scouted` / `contract` / `structural`), epistemic label, and the validator tier that produced the label. Record Decisions §8 here too — ratings render at the 20-80 player-page scale — so the next slice inherits a decision rather than re-deriving one, even though ratings are gated.",
                  "Declare the three grains with their keys: `bronze_team` (`snapshot_date`, `save_id`, `team_id`); `bronze_player` (`snapshot_date`, `save_id`, `player_id`); `bronze_team_roster` (`snapshot_date`, `save_id`, `team_id`, `player_id`, `list_id`) — NOT (`snapshot_date`, `player_id`). `bronze_name` carries its own declared grain, key and coverage like every other table (SD-10 / F10). The `save_id` component is required by SD-09: the pipeline parses two different universes and a key without it collides them.",
                  "Declare `historical_id` as a NULLABLE ATTRIBUTE and never a join key in any serving path — measured, 1,920 of 18,072 active players carry a non-empty one (10.6%). Add a static check asserting no join or ref condition uses it.",
                  "MAIN THREAD writes `tests/test_grain_contracts.py` (offline, AC4): read the tracked declaration and the DDL the loader emits, and assert the prose grain sentence EQUALS the key the DDL emits, encoding `.claude/agents/data-engineer.md:101`. This runs offline because it compares two artifacts, not a database.",
                  "MAIN THREAD writes `tests/test_withheld_fields.py` (offline, AC13) keyed on the declared CATEGORY, not on column-name globs (finding F9): no field whose category is `rating-true`, and no field whose epistemic label is `unconfirmed` or `assumed`, is renderable. Include a NEGATIVE test asserting a synthetic `rating-scouted` field IS renderable — without it the guard is satisfied by blocking everything, which passes and delivers nothing. Keep name patterns only as a secondary check, with `talent_%` corrected to `%_talent_%`: as written it matched no real column, since the actual columns are `batting_ratings_talent_*`.",
                  "MAIN THREAD writes the `historical_id`-is-not-a-join-key static check as an offline test."
              ],
    "acceptance":  [
                       "`uv run pytest -m \"not gamedata\" tests/test_grain_contracts.py` is green offline (AC4): every declared grain sentence matches the key the DDL emits, including all three `save_id` components.",
                       "`uv run pytest -m \"not gamedata\" tests/test_withheld_fields.py` is green offline (AC13), AND its negative test confirms a `rating-scouted` field is renderable — verify by name in `pytest -v` output, because a guard that blocks everything passes the positive half.",
                       "A deliberate local mutation of the declaration\u0027s `bronze_team_roster` key to (`snapshot_date`, `player_id`) turns `tests/test_grain_contracts.py` RED. Revert it. A contract test never demonstrated failing is not a contract test.",
                       "The static `historical_id` check is green and would flag a synthetic join using it.",
                       "`uv run pytest -m \"not gamedata\"` fully green; ruff / format / mypy clean.",
                       "`uv run pytest tests/test_no_leaks.py` green — the declaration names source FILES (`players.dat`) but no absolute path (F19)."
                   ],
    "commit_note":  "Hand to the user for `/commit`. This phase adds no runtime behaviour and is pure contract, so it is the cheapest possible checkpoint at which to catch a wrong grain — and the most expensive one to skip, because phase 9 emits DDL from it and phase 12 generates the catalog from it. Reversible in full."
}
```
```json
{
    "name":  "Phase 9 — MySQL bronze landing, snapshot keys, and the ingest-run row",
    "goal":  "Land bronze into the empty `ootp` schema, 1:1 with parser output, with `snapshot_date` AND `save_id` in every primary key — so the first sim date never has to be re-keyed and two universes never collide in one table.",
    "steps":  [
                  "Write `src/ootp_ai/warehouse/ddl.py` emitting the DDL for `bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name` FROM the phase-8 declaration. The emitter reads the declaration; it does not restate it. `tests/test_grain_contracts.py` already compares the two, so a divergence goes red rather than silent.",
                  "Write `src/ootp_ai/warehouse/loader.py`: typing, casing and dedup ONLY — no joins, no filtering, no semantic renaming (`.claude/agents/data-engineer.md:98`). Append-only per snapshot; loading a snapshot touches only its own (`snapshot_date`, `save_id`) partition; snapshots immutable. Land EVERYTHING the walk yields including all 259 teams and every minor-league population — Decisions §7, and the org filter lives in the report, three phases later.",
                  "Preserve structural absence as `NULL`, never zero, throughout the loader. This is where the 14 non-MLB league rows\u0027 `0`-valued roster and service-time columns would silently become real zeros.",
                  "Persist the ingest-run row shaped in phase 4: source file sizes, SHA-256 digests, header versions, sim date, human team, row counts, residual bytes, and a placeholder for wall-clock parse time (filled in phase 10). This is what makes a data incident triageable instead of archaeological.",
                  "Land the folded-in cheap win #5: write each field\u0027s epistemic label into a warehouse metadata table alongside the data, from the same phase-8 declaration — so a future incident can ask \u0027what did we believe about this field the day it was landed?\u0027 as a query rather than as archaeology through the git history of `docs/data-access.md`.",
                  "MAIN THREAD completes `tests/test_snapshot_semantics.py` (`-m gamedata`, AC10): loading the same snapshot twice leaves per-table row counts and checksums unchanged; loading a SECOND `snapshot_date` leaves the first snapshot\u0027s rows bit-identical; re-landing an existing `snapshot_id` does not silently overwrite it. The second-snapshot case can be synthesised by re-landing the probe save\u0027s parse under a different `save_id` and `snapshot_date`.",
                  "MAIN THREAD writes `tests/test_grain_contracts.py::test_roster_grain_is_not_player_grain` (`-m gamedata`, AC5): POSITIVELY assert `player_id` is NOT unique within one snapshot\u0027s roster rows, so a later refactor cannot silently collapse the membership grain into a player grain; and assert `count(distinct player_id)` in `bronze_team_roster` is materially LESS than `count(*)` in `bronze_player` for the same snapshot."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_grain_contracts.py::test_roster_grain_is_not_player_grain` is green (AC5): `player_id` is provably non-unique within one snapshot\u0027s roster rows, and the distinct-player count is materially below the `bronze_player` count.",
                       "`uv run pytest -m gamedata tests/test_snapshot_semantics.py` is green in full (AC10): idempotent re-load, second snapshot leaves the first bit-identical, re-landing an existing snapshot_id does not overwrite.",
                       "`select count(*)` against the `ootp` schema shows four bronze tables plus the metadata and ingest-run tables where there were 0 tables, and every primary key contains both `snapshot_date` and `save_id` — read the emitted DDL to confirm rather than trusting the loader.",
                       "`uv run pytest -m \"not gamedata\" tests/test_grain_contracts.py` still green — the offline prose-vs-DDL comparison now runs against a real emitter.",
                       "`uv run pytest -m \"not gamedata\"` fully green with no MySQL server running (AC16\u0027s condition, checked early rather than at the end); ruff / format / mypy clean."
                   ],
    "commit_note":  "Hand to the user for `/commit`. Reversibility here is at the schema level rather than the code level: dropping the `ootp` tables restores the pre-phase state, and `ops/mysql-bootstrap.sql:23-24` recreates the empty schema. Note for the user — this is the first phase that requires a running MySQL, so the local-vs-CI gate diverges here permanently; CI proves the offline half only, which is why phase 8\u0027s contract tests were deliberately written to run offline."
}
```
```json
{
    "name":  "Phase 10 — The parser-vs-export differential harness and the recorded extraction cost",
    "goal":  "Prove the parser against a real independent answer key, per field and by name, rather than by eyeball — and record the extraction-cost number the later \u0027is weekly re-ingestion viable\u0027 decision needs. This is the phase that converts the field map\u0027s labels from beliefs into findings, and it must run before anything renders to a GM.",
    "steps":  [
                  "MAIN THREAD writes `tests/test_parser_vs_export.py` (`-m gamedata`, AC6). It asserts PROVENANCE FIRST: the parsed save\u0027s sim date is 2024-03-18 and its human team is the Chicago Cubs, matching `ootp_truth_real` — proving the binaries and the export describe the same universe. A field diff against a different universe is noise that looks like a finding.",
                  "Then diff row-for-row over the landed field set: zero row-count and zero value differences across 259 teams, 18,072 active players (`retired = 0`), 15,672 `team_roster` rows, 15 leagues. Every mismatch listed PER FIELD BY NAME; an aggregate pass rate is not acceptable output (Core §18).",
                  "Bind Tier B\u0027s limits into the test\u0027s own comments so a later reader cannot over-trust it: Tier B is EXACT for ids, names, strings, dates, roster lists, the team dimension and league config, and BUCKETED for ratings — measured, `players_batting.batting_ratings_overall_contact` has exactly 12 distinct values, 20-80. It is NOT an exact rating validator, and a bucketed check can pass a parser reading the ADJACENT u16, which is CLAUDE.md\u0027s named correctness trap in its most dangerous form.",
                  "Every query in this harness backticks every identifier and is covered by the phase-1 regression test.",
                  "Write `src/ootp_ai/ingest.py`\u0027s timing so a full parse\u0027s wall-clock seconds land in the ingest-run row. MAIN THREAD writes `tests/test_extraction_cost.py` (`-m gamedata`, AC17): assert the number EXISTS and is recorded. There is no threshold and no pass/fail on duration — Decisions §6, an operator ruling, and finding F12\u0027s tautology objection is accepted deliberately on the grounds that a threshold nobody has justified is worse than an honest measurement.",
                  "Route the label upgrades as a docs-delta for `/update-docs` — upgrade `docs/data-access.md`\u0027s epistemic labels for EXACTLY the fields Tier A or Tier B actually proves, leaving everything else `unconfirmed` and therefore withheld by the phase-8 guard. Never edit `docs/data-access.md` from a subagent (`.claude/agents/data-engineer.md:156`)."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parser_vs_export.py` is green (AC6): provenance pinned to the Cubs at 2024-03-18, then zero row-count and zero value differences over the landed field set.",
                       "Deliberately corrupt one parsed field locally and confirm the harness names THAT FIELD in its failure output rather than reporting a pass rate. Revert. A differential harness never seen to fail informatively is not yet a harness.",
                       "`uv run pytest -m gamedata tests/test_extraction_cost.py` is green (AC17) and the ingest-run row for the latest snapshot carries a non-null wall-clock seconds value — read it back from the warehouse, not from stdout.",
                       "`uv run pytest -m \"not gamedata\" tests/test_withheld_fields.py` still green after the label upgrades — any field upgraded to `verified` is now renderable and any field left `unconfirmed` still is not.",
                       "`uv run pytest -m \"not gamedata\"` fully green; ruff / format / mypy clean."
                   ],
    "commit_note":  "Hand to the user for `/commit`, and route the docs-delta through `/update-docs` in the same unit of work so the epistemic labels and the code that earned them land together. This is the last phase before anything is rendered for the GM to read — if the differential is not green, do not proceed to phase 11: a report built on an unvalidated parse is exactly the silent-wrong-data failure `requests/README.md:20-32` describes."
}
```
```json
{
    "name":  "Phase 11 — The two Markdown reports and the rendered-game-data leak guard",
    "goal":  "Deliver the request\u0027s observable signal — a report naming real Boston players — and extend the leak guard to cover it, because this feature is the first thing in the repo\u0027s history that renders OOTP player data to a file.",
    "steps":  [
                  "Write `src/ootp_ai/reports/__main__.py` exposing `uv run python -m ootp_ai.reports render`, plus `roster.py` and `standings.py`. Both write to the git-ignored output root, resolved from config.",
                  "Roster report: the configured organization ONLY — the org filter lives here, never at bronze — grouped by roster list, carrying position, age, bats/throws and uniform number, with `snapshot_date` and sim date on line one so staleness is visible on sight. Honour phase 7\u0027s `list_id` disposition: no human label for a mapping below `inferred`.",
                  "Standings report: 30 MLB clubs by division with W-L-pct-GB. Ship it, but expect it to be empty of signal — measured, all 259 `team_record` rows are 0-0-0 and 0 of 12,961 games are played, because both saves sit before opening day. Playoff seeds are deferred to the first sim.",
                  "MAIN THREAD writes `tests/test_reports.py` (`-m gamedata`, AC14) asserting: the resolved output root is git-ignored, proven by `git check-ignore -q \u003cpath\u003e` exiting 0 AND `git ls-files` listing no file under it; the roster report contains rows for exactly the configured organization and ZERO rows belonging to any other; every player row\u0027s name matches `^[A-Za-z][A-Za-z .\u0027-]+$` (a name, not an integer); the standings report contains 30 MLB rows grouped by division with W-L-pct-GB columns present; and both files carry `snapshot_date` and sim date on line one.",
                  "Assert standings content STRUCTURALLY, never by value. Asserting a nonzero win total would fail on a CORRECT parse at this sim date — the most expensive kind of wrong test, because it sends the next agent hunting a bug in working code.",
                  "MAIN THREAD extends `tests/test_no_leaks.py` (folded-in #1). The existing guard at `:97-116` bans four filenames and two suffixes; a Markdown roster sails straight through. Add: the report and catalog output roots resolve to a git-ignored path; and the F19 constraint mechanically — the TRACKED half of the catalog and field map may name source FILES (`players.dat`) but NEVER absolute paths, since `saved_games.dat` embeds an absolute user-profile path for every save and a provenance section rendering it publishes a username to a public repo.",
                  "Record, do not fix, the known gap: `tracked_text_files()` at `tests/test_no_leaks.py:31-48` enumerates via `git ls-files`, so the guard does not see a new file until it is staged — a leak in an untracked artifact passes locally and fails in CI. File it as a follow-up request; it is not in scope here."
              ],
    "acceptance":  [
                       "`uv run python -m ootp_ai.reports render` writes both files, and `uv run pytest -m gamedata tests/test_reports.py` is green on all five assertions (AC14).",
                       "`git check-ignore -q \u003cresolved output root\u003e` exits 0 and `git ls-files` lists nothing under it — run both by hand as well as in the test, since this is the ADR 0006 boundary.",
                       "The roster report is read by eye once and contains recognisable Boston names, not integers — an informal check that the automated name-regex assertion is testing what it claims.",
                       "`uv run pytest -m \"not gamedata\" tests/test_no_leaks.py` is green with the extended guard, and its `test_patterns_still_catch_real_leaks` self-test at `:51-78` still passes — a guard loosened until it passes is not a guard.",
                       "`uv run pytest -m \"not gamedata\"` fully green; ruff / format / mypy clean.",
                       "A follow-up request directory exists for the `git ls-files` staging gap in the leak guard."
                   ],
    "commit_note":  "Hand to the user for `/commit`. This is the first checkpoint where the request\u0027s stated observable signal is deliverable, so it is the natural place to stop if the slice needs to ship early — phases 12 and 13 add the catalog and the doc sweep but the GM can already see its club. Flag SD-21 to the user here: regenerating a report overwrites the prior snapshot\u0027s view, breaking citation integrity for `gm/decisions/` records that cite it. Not solved in this slice; it becomes real the first time a decision record cites a report."
}
```
```json
{
    "name":  "Phase 12 — The generated catalog, its tracked/volatile split, and the report-channel pointer",
    "goal":  "Give the GM the menu — every landed table\u0027s grain, key, coverage, row count and snapshot date, AND what was deliberately withheld and why — generated from `information_schema` plus the phase-8 declaration, never hand-written, so it cannot drift from what was actually landed.",
    "steps":  [
                  "Write `src/ootp_ai/catalog/__main__.py` exposing `uv run python -m ootp_ai.catalog`. It reads `information_schema` for row counts and the phase-8 declaration for grains, keys, coverage and labels — one declaration, three consumers.",
                  "Implement Decisions §3\u0027s split: the STRUCTURAL half (table names, grains, keys, coverage statements, withheld groups, epistemic labels) is TRACKED — ADR 0006 explicitly permits tracking derived schema knowledge, so it survives a fresh clone. The VOLATILE half (row counts, snapshot dates, freshness) generates into the ignored output root. Explicitly do NOT resolve this by adding a tracked Markdown link into `var/`: `tests/test_doc_links.py:15` skips `var` when ENUMERATING files but its `test_relative_links_resolve` still resolves link TARGETS, so a tracked link into an ignored path turns CI red today.",
                  "Make the tracked half BYTE-DETERMINISTIC: sorted ordering, no timestamps, no absolute paths, no hostnames. AC15 asserts the regenerated structural section is byte-identical to the committed copy, and any nondeterminism makes that test flap.",
                  "Emit the withheld section naming the true-rating tables, `players.prone_*`, `players_value.*` and every still-`unconfirmed` field, each with its reason and ADR. The request\u0027s second desired outcome is \u0027the GM knows what it is not seeing\u0027, and a catalog of landed tables tells it only what it CAN see.",
                  "Generate per-table coverage statements FROM COUNTS, never hand-written (folded-in #3). State how many players carry NO roster row — ~10,700 of 18,072 active: free agents, draft-eligible, international, unassigned — so the GM prices \u0027who is available\u0027 as a known gap rather than discovering it by hitting it.",
                  "Emit a machine-readable `catalog.json` sibling from the same generator (folded-in #4).",
                  "Add the report-path pointer to the TRACKED half (SD-11, Core §15): each report\u0027s logical name, the `.env` key and RELATIVE path it resolves to, and a one-line spawn instruction the umpires read when handing the GM its reports. NOT a Markdown link into the ignored root — that turns CI red. Without this, acceptance criterion 20 is unreproducible by anyone who was not in the room.",
                  "MAIN THREAD writes `tests/test_catalog.py` (`-m gamedata`, AC15): the structural section is REGENERATED during the test and is byte-identical to the committed copy, proving it cannot be hand-edited into drift; every landed table appears with grain sentence, key list, coverage population, row count, source `.dat` file, epistemic label and snapshot date; the withheld groups are listed with reason and ADR; NO player-level value and NO rating column name appears anywhere in it; and regenerating twice is byte-identical."
              ],
    "acceptance":  [
                       "`uv run python -m ootp_ai.catalog` regenerates both halves and `uv run pytest -m gamedata tests/test_catalog.py` is green on every clause of AC15.",
                       "Hand-edit one character of the committed structural half locally and confirm `tests/test_catalog.py` goes RED. Revert. This is the whole point of the byte-identical assertion and it must be seen to fire.",
                       "Run the generator twice in succession and diff the two tracked outputs — zero bytes different, proving determinism rather than luck.",
                       "`uv run pytest -m \"not gamedata\" tests/test_doc_links.py` is green: the tracked catalog contains no Markdown link into the ignored output root.",
                       "`uv run pytest -m \"not gamedata\" tests/test_no_leaks.py` green: the tracked half names source files but no absolute path (F19), and contains no player-level value.",
                       "`uv run pytest -m \"not gamedata\"` fully green; ruff / format / mypy clean."
                   ],
    "commit_note":  "Hand to the user for `/commit`. Raise the tracked-catalog LOCATION with the user at this checkpoint if it was not settled earlier — `docs/warehouse-catalog.md` is the recommendation, and if it is added to `tests/test_repo_structure.py:12-24`\u0027s required-docs list that is a main-thread edit. CLAUDE.md forbids creating directories speculatively, so a new top-level `catalog/` needs an argument the user should make rather than the implementer."
}
```
```json
{
    "name":  "Phase 13 — Doc sweep, the tracked report channel, final full green, and the USER-RUN acceptance",
    "goal":  "Close every documentation claim this slice made false, land the tracked half of the report channel in `gm/standing-orders.md`, and hand the two USER-RUN criteria to the operator with everything they need to run them.",
    "steps":  [
                  "Run `/update-docs` and route every accumulated docs-delta: no `leagues.dat` exists and the league config block is in `world.dat` at the measured location (already landed in phase 2, verify it survived); `docs/data-access.md` §1\u0027s file table is incomplete — 18 `.dat` files are present and several are unlisted; the `names.dat` fixed-size-per-save finding with an `inferred` label; `saved_games.dat` is NOT plaintext, downgrading the `verified` label at `docs/data-access.md:36-38` (F19); `ootp_truth_osa` is empty and unnecessary; and the epistemic-label upgrades for exactly the fields Tier A or Tier B proved.",
                  "Correct `docs/league-rules.md:26` and `:31` (risk 11): both describe §1 as superseded by the warehouse \u0027the moment the parser lands\u0027, which this slice PARTIALLY does. Partial supersession stated as total is the kind of doc claim that gets acted on wrongly. The doc gate must catch this; name it explicitly so it does.",
                  "Record Decisions §9 as a note in ADR 0004 §Notes: dbt is deferred, here is the trigger, here is why it was not pulled. ADR 0005\u0027s PATTERN choice is honoured in full; only its TOOLING phrasing is deferred. Quietly diverging is the one option this repo forbids, so it goes on the record — a superseding ADR is too heavy for a postponement.",
                  "UMPIRE EDIT (main thread, not the builder): add the new engineering-owned report kind to `gm/standing-orders.md`\u0027s `## Reports` format block at `:42-50`, per Decisions §4 — a pipeline-generated report genuinely has no analyst behind it, and `gm/staff.md` records that no staff exist, so naming an owner would be fiction. Then add the two report entries under that kind. The file currently reads \u0027Status: none active\u0027 at `:10-11`; that line changes.",
                  "USER-RUN, per Decisions §2 and blocker SD-03: the ledger row recording that the roster report and catalog are free infrastructure rather than a commissioned action is an UMPIRE ACT, not a build artifact. It is a post-delivery step the operator performs, and it becomes an early `seq` every later report request will cite.",
                  "Confirm CI\u0027s actual condition end to end: `uv run pytest -m \"not gamedata\"` with NO game install and NO MySQL server running.",
                  "Hand the user acceptance criterion 20 with the spawn instruction from the phase-12 catalog pointer, and acceptance criterion 21 with the phase-4 manifest."
              ],
    "acceptance":  [
                       "`uv run pytest -m \"not gamedata\"` passes with no game install and no MySQL server, and `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` are all clean, with `tests/test_no_leaks.py`, `tests/test_repo_structure.py`, `tests/test_agent_contract.py` and `tests/test_doc_links.py` all still green (AC16).",
                       "`uv run pytest -m gamedata` passes in full on a machine with the install, both saves and the warehouse — every gamedata test from phases 3 through 12, run in one pass rather than phase by phase.",
                       "`uv run pytest -m \"not gamedata\" tests/test_doc_corrections.py` green (AC19), plus `docs/league-rules.md:26` and `:31` no longer overstate the supersession.",
                       "ADR 0004 §Notes carries the dbt-deferral note with its trigger, and `tests/test_repo_structure.py::test_every_adr_records_its_cost` still green.",
                       "`gm/standing-orders.md` carries the new report kind and two report entries; `tests/test_doc_links.py` green after the edit.",
                       "USER-RUN (AC20 — the acceptance panel must NOT claim this): a cold session spawns the `gm` subagent with the roster and catalog reports in its context, and the returned handoff\u0027s `## situation` names at least five Boston players by real name, each attributed to the report as its source, with no roster fact appearing in `## assumed`.",
                       "USER-RUN (AC21): the operator confirms `OOTP-AI.lg`\u0027s file set, sizes and modification times are unchanged after a full ingestion run, checked BY HAND against the recorded manifest — an independent check that does not rely on the code that would be the thing violating it."
                   ],
    "commit_note":  "Hand to the user for `/commit`, then advance the Index row at `requests/feature-requests/README.md:119` and move the slug into `_done/` only after the two USER-RUN criteria come back green. Do not mark the request `implemented` on the panel\u0027s word alone — AC20 and AC21 are explicitly the operator\u0027s, and AC21 in particular is the one check in this project that must not be performed by the code it audits."
}
```

### testing

VERIFICATION MODEL. Two suites with different jobs, and the split is not cosmetic. `.github/workflows/ci.yml:49` runs `uv run pytest -m "not gamedata"`, so the OFFLINE suite is the only thing that protects against regression on every future PR. The `-m gamedata` suite is the only thing that proves the parser is CORRECT. A phase proved only by gamedata tests has zero CI signal; a phase proved only by offline tests has zero contact with reality. Every phase above therefore carries at least one of each wherever the subject allows — which is why the walkers get synthetic-buffer tests alongside their real-save tests, and why the contract tests in phase 8 were deliberately designed to compare two artifacts rather than query a database.

MARKER PRECONDITION. `pyproject.toml:78` sets `--strict-markers` and `:79-81` declares exactly one marker whose text says 'requires a local OOTP install or save' — saying nothing about a database. Phase 1 widens it to 'install, save, or warehouse'. Until that lands, every warehouse-reading test in phases 6, 9, 10, 11 and 12 is a HARD COLLECTION ERROR, not a failure — the whole suite fails to collect, which looks like a broken repo rather than a missing marker. This is the single cheapest ordering mistake available in this plan.

TEST OWNERSHIP. `tests/` is the first entry in the data-engineer's deny set (`.claude/agents/data-engineer.md:150`), asserted by `tests/test_agent_contract.py:69-75`. Every phase's subagent spec declares targets under `src/ootp_ai/**` plus the contracts declaration and NOTHING under `tests/`. The main thread writes every test and every fixture. A spec that names a `tests/` path returns an Escalation with zero code built (`.claude/agents/data-engineer.md:258-262`), which costs a whole phase.

PER-PHASE SELECTORS, in execution order:
  P1  `uv run pytest -m "not gamedata" tests/test_config.py tests/test_db_identifiers.py`
  P2  `uv run pytest -m "not gamedata" tests/test_doc_corrections.py`
  P3  `uv run pytest -m "not gamedata" tests/test_save_header.py tests/test_sequential_walk.py tests/test_no_fixed_offsets.py` + `uv run pytest -m gamedata tests/test_save_enumerator.py`
  P4  `uv run pytest -m gamedata tests/test_read_only.py tests/test_snapshot_semantics.py`
  P5  `uv run pytest -m gamedata tests/test_parse_real_save.py -k team` + `... tests/test_byte_accounting.py -k teams` + `uv run pytest -m "not gamedata" tests/test_parse_teams_synthetic.py`
  P6  `uv run pytest -m gamedata tests/test_names_join.py tests/test_names_join_boston.py` + `... tests/test_byte_accounting.py -k names`
  P7  `uv run pytest -m gamedata tests/test_parse_real_save.py tests/test_byte_accounting.py tests/test_snapshot_semantics.py`
  P8  `uv run pytest -m "not gamedata" tests/test_grain_contracts.py tests/test_withheld_fields.py`
  P9  `uv run pytest -m gamedata tests/test_grain_contracts.py::test_roster_grain_is_not_player_grain tests/test_snapshot_semantics.py`
  P10 `uv run pytest -m gamedata tests/test_parser_vs_export.py tests/test_extraction_cost.py`
  P11 `uv run pytest -m gamedata tests/test_reports.py` + `uv run pytest -m "not gamedata" tests/test_no_leaks.py`
  P12 `uv run pytest -m gamedata tests/test_catalog.py` + `uv run pytest -m "not gamedata" tests/test_doc_links.py`
  P13 `uv run pytest -m "not gamedata"` and `uv run pytest -m gamedata` in full.

FOUR TESTS THAT MUST BE SEEN TO FAIL. A guard never observed failing is decoration, and this plan names four places to prove it, each at its own phase boundary: (1) P3's fixed-offset negative control — a deliberately seeking reader must fail `tests/test_sequential_walk.py`; (2) P8's grain mutation — changing `bronze_team_roster`'s declared key to (`snapshot_date`, `player_id`) must turn `tests/test_grain_contracts.py` red; (3) P10's field corruption — a corrupted parsed field must be named BY FIELD in the differential's output, not folded into a pass rate; (4) P12's catalog edit — a one-character hand edit of the tracked structural half must turn `tests/test_catalog.py` red. Revert each immediately.

TWO WAYS THESE TESTS CAN PASS VACUOUSLY, both of which the plan blocks explicitly. First, a `-m gamedata` test whose fixture is unreachable: `tests/test_names_join.py` (AC7) must SKIP LOUDLY WITH A NAMED REASON when `ootp_truth_real` is unreachable, and phase 6's acceptance verifies the skip path by temporarily unsetting the key. Second, `tests/test_withheld_fields.py` (AC13): a guard that blocks EVERYTHING passes the positive assertion and delivers nothing, which is why the negative test asserting a synthetic `rating-scouted` field IS renderable is not optional.

REGRESSION SAFETY ACROSS PHASES. From phase 5 onward every phase's acceptance re-runs `tests/test_read_only.py` and `tests/test_no_fixed_offsets.py`. The first is ADR 0001, the one unrecoverable failure in the project; the second is the silent-corruption class CLAUDE.md names as the most likely way to corrupt every downstream recommendation. Checking both at every checkpoint rather than once at the end costs seconds and is the difference between finding a violation at a 46 MB copy and finding it after a full parse. The four pre-existing guards — `tests/test_no_leaks.py`, `tests/test_repo_structure.py`, `tests/test_agent_contract.py`, `tests/test_doc_links.py` — are in the offline suite and therefore re-run at every phase automatically.

WHAT NO TEST HERE COVERS, stated so nobody mistakes green for complete. Ratings are entirely out of the tested surface — the phase-2 spike returns a verdict, not a parser. Tier B is BUCKETED for ratings (`batting_ratings_overall_contact` has exactly 12 distinct values, 20-80), so it can never be an exact rating validator and `players.csv` stays load-bearing permanently. Standings content is asserted STRUCTURALLY only, because all 259 `team_record` rows are 0-0-0 and 0 of 12,961 games are played — asserting a nonzero win total would fail on a correct parse. And full byte accounting on `players.dat` is diagnostic, not strict: a record-count match plus record-boundary termination, with the residual recorded rather than asserted zero.

### risks

- SEQUENCING RISK, highest: handing a whole phase's spec to the data-engineer subagent. `tests/` is the first entry in its deny set (`.claude/agents/data-engineer.md:150`), and `tests/test_agent_contract.py:69-75` asserts it stays there. Its documented behaviour when spec targets fall inside the deny set is to STOP AND REPORT (`:164`), so the phase returns an Escalation and zero code. Mitigation: every phase spec above declares targets under `src/ootp_ai/**` plus the contracts declaration only, and the main thread writes the tests. This is scope risk 8, and the plan honours it phase by phase rather than once in a preamble.
- MARKER ORDERING: `pyproject.toml:78` carries `--strict-markers` and `:80` declares `gamedata` as 'requires a local OOTP install or save' with no mention of a database. Any warehouse test written before phase 1 widens that text is a hard COLLECTION error — the entire suite fails to collect, which presents as a broken repo rather than a missing marker. Mitigation: the widening is the second step of phase 1 and is verified by a `--collect-only -m gamedata` acceptance check before any dependent phase starts.
- mypy STRICT RUNS OVER `tests` TOO (`pyproject.toml:69-73`), which is unusual and will bite on the very first test file: every test function needs `-> None`, every fixture needs annotating, and an unstubbed MySQL driver makes every `db.py` call an untyped-call error. Mitigation: phase 1 picks the driver WITH its stub story (recommend `PyMySQL` + `types-PyMySQL`) rather than discovering the problem at phase 9 when the loader is half-written. This is scope risk 9 / SD-14.
- PHASE 6 IS THE SCHEDULE RISK. The `names.dat` encoding is `unconfirmed` at `docs/data-access.md:238` and the scope calls it the largest single unknown. If it resists, the roster report — the request's entire observable signal — degrades to integers. Mitigation: the phase is placed before the players walk so the fallback (Decisions §5: resolve names from `players.csv` at runtime for the ~1,712 players carrying a Lahman ID, nothing tracked) fires at a clean checkpoint rather than being discovered while phase 11 is being written. The phase's commit note makes the branch a user-visible decision.
- PROBE-DERIVED NAME INDICES DO NOT TRANSFER, and the failure is silent rather than a crash. Measured: `names.dat` is 8,642,110 bytes in all three saves with three different SHA-256 digests — a fixed-size, per-save-populated table. A cached name table or an index→string expectation carried from the probe into the managed league produces a roster of confidently wrong names with nothing throwing. Mitigation: the name table is an object owned by a save, never a module-level constant, and phase 6 carries a positive assertion that the same index resolves DIFFERENTLY across the two saves (SD-10).
- THE BUCKETED-EXPORT TRAP, in CLAUDE.md's named form. `players_batting.batting_ratings_overall_contact` has exactly 12 distinct values, 20-80 — the export is display scale. A bucketed check can pass a parser reading the ADJACENT u16. Mitigation: this plan lands NO ratings at all, so the trap is deferred rather than mitigated; phase 10's test comments state Tier B's exact-vs-bucketed split explicitly so a later agent extending the harness to ratings does not inherit false confidence from a green suite.
- POINTING UNTESTED FILESYSTEM CODE AT `OOTP-AI.lg` FIRST. `challenge.dat` is present at 241 bytes and one write is unrecoverable with no backup upstream (`.claude/agents/data-engineer.md:53-58`). Mitigation, SD-20 / folded-in #9: phases 3, 4, 5 and 6 each run against the DISPOSABLE Challenge Mode probe save first and only then against the managed league, and the ordering is encoded in the test modules rather than left as prose. Phase 4 also hands the operator acceptance criterion 21 early, at 46 MB of copying, rather than after a full parse.
- PHASE 12'S BYTE-IDENTICAL CATALOG ASSERTION WILL FLAP on any nondeterminism — dict ordering, a timestamp, a hostname, a locale-dependent number format, or a `git`-derived value. Mitigation: sorted ordering and no timestamps in the tracked half are build requirements, not polish, and the acceptance runs the generator twice and diffs rather than trusting one pass.
- THE DOC-LINK GUARD IS BROKEN IN A WAY THIS FEATURE'S OWN ARTIFACTS TRIP (scope risk 7; open bugfix request `doc-link-guard-mismatch`). `tests/test_doc_links.py:18-38` resolves every Markdown link target, so a tracked link into the ignored output root turns CI red today. Mitigation: the catalog's report pointer carries the `.env` key and a relative path as TEXT, never as a Markdown link (SD-11), and every `file:line` citation in this plan's own artifacts uses code spans.
- STRUCTURAL ABSENCE COLLAPSING TO ZERO, with 14 separate chances to commit it. The export writes `0` for `rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows. A loader that copies the export's habit produces wrong aggregates rather than incomplete ones (`.claude/agents/data-engineer.md:111-112`). Mitigation: preserve as `NULL` never zero, stated as a step in phases 5 and 9 and surfaced in the catalog's coverage statements in phase 12.
- SD-21, FLAGGED NOT SOLVED: regenerating a report OVERWRITES the prior snapshot's view, breaking citation integrity for any `gm/decisions/` record that cites it. Nothing in this slice fixes it and nothing should — it becomes real the first time a decision record cites a report. Phase 11's commit note surfaces it to the user at the moment reports first exist.
- THE LEAK GUARD HAS A LOCAL BLIND SPOT: `tests/test_no_leaks.py:31-48` enumerates via `git ls-files`, so it does not see a new file until it is STAGED. A leak in an untracked artifact passes locally and fails in CI — which, on the first feature in this repo's history that renders OOTP player data to a file, is exactly the wrong direction for the feedback loop to run. Mitigation: recorded as a follow-up request in phase 11, explicitly out of scope here.
- FIXTURE FILES WILL BE TRACKED IF GIVEN A `.dat` EXTENSION. `.gitignore:31` ignores `*.dat` but `:62`'s `!tests/fixtures/**` is a LATER negation, and git's last-match-wins means the negation re-includes them. The only thing catching it is `tests/test_no_leaks.py:97-116`, as a red build. Mitigation: phase 3 gives every synthetic fixture a non-`.dat` extension, and the acceptance checks `git status` explicitly.
- NOBODY HAS RUN ANY OF THIS CODE (scope risk 13). Every cost estimate in the scope is `unconfirmed`, including the extraction-cost expectation. Mitigation: Decisions §6 removes the threshold entirely — the number is recorded, not asserted against — so phase 10 cannot fail on a duration nobody has justified. If a full parse turns out to take an hour, that is a recorded fact and a later decision, not a phase failure.
- A DEGRADED CHECKPOINT: it is tempting to run phases 5 through 7 as one 'parser' phase because they share a walker pattern. Do not. Each walks a different file with a different byte-accounting tier and a different ground-truth answer key, and merging them means a failure in `players.dat` blocks a green, provable `teams.dat`. Three checkpoints cost three commits and buy three independently revertible units.

### files_to_touch

```json
{
    "path":  "pyproject.toml",
    "change":  "P1: promote `python-dotenv` from the dev group at `:23` into `[project] dependencies` (currently `[] ` at `:9`); add the chosen MySQL driver plus its type stubs; WIDEN the `gamedata` marker text at `:80` from \u0027requires a local OOTP install or save\u0027 to \u0027...install, save, or warehouse\u0027. Revise the `:11-15` comment that says the first real dependency arrives with the warehouse loader."
}
```
```json
{
    "path":  ".env.example",
    "change":  "P1: add two new keys — the probe save directory and the disposable Challenge Mode probe league — and retire `MYSQL_TRUTH_OSA_DATABASE` at `:58` per Decisions §10. `OOTP_SNAPSHOT_ROOT` at `:25` is empty in the live `.env` (verified), so its `var/snapshots` default and local-disk validation become code, not a comment."
}
```
```json
{
    "path":  "ops/mysql-bootstrap.sql",
    "change":  "P1: delete the `ootp_truth_osa` create at `:32-33` and its grant at `:49`. Measured: the schema exists with 0 tables and `ootp_truth_real.players_scouted_ratings` already carries BOTH perspectives (`scouting_coach_id` ∈ {-1, 2759}, 18,072 rows each) from ONE export, so the premise behind a second export database is wrong."
}
```
```json
{
    "path":  "src/ootp_ai/config.py",
    "change":  "P1 NEW: frozen dataclass resolving every path and connection from `.env` only. No literal path, no `parents[N]` walk outside test modules (`.claude/agents/data-engineer.md:88-90`). Validates the snapshot root is local disk."
}
```
```json
{
    "path":  "src/ootp_ai/db.py",
    "change":  "P1 NEW: read-only `ootp_truth_real` and write `ootp` connection factories, with every identifier in export-diff SQL backticked — the regression fix for the measured `select current_date from ootp_truth_real.leagues` incident. Owns the SD-13 collation decision."
}
```
```json
{
    "path":  "requests/feature-requests/first-sight/reviews/scouted-view-spike.md",
    "change":  "P2 NEW: the pre-registered pivot rule written BEFORE the spike runs, then the verdict — stored or computed, with an epistemic label and cited byte evidence from `scouting.dat` searched for `ootp_truth_real.players_scouted_ratings` values."
}
```
```json
{
    "path":  "docs/league-rules.md",
    "change":  "P2: correct `:129` (\u0027parser reads `leagues.dat` directly\u0027) and `:295` (\u0027Until the parser can open `leagues.dat`\u0027) — no such file exists in the 18 `.dat` files of `OOTP-AI.lg`; the league config block is in `world.dat` at byte 5,559,751, identified by the `major_league_ml_c_2024.lsdl` string recorded at `:80`. P13: correct `:26` and `:31`, which claim §1 is superseded the moment the parser lands — this slice supersedes it only partially."
}
```
```json
{
    "path":  "src/ootp_ai/parser/primitives.py",
    "change":  "P3 NEW: a forward-only Cursor with u8/u16/u32/f64, length-prefixed ASCII string, `u8 day,u8 month,u16 year` date, u32 ARGB. Deliberately no seek and no absolute-position read — this is what makes the fixed-offset ban structural rather than a review convention."
}
```
```json
{
    "path":  "src/ootp_ai/parser/header.py",
    "change":  "P3 NEW: leading `0x00`, `b\"OOTP\"` at offset 1, u32 version at offset 5 (must be 25) raising a named `UnsupportedSaveVersion`, null-padded self-declared filename at offset 25 cross-checked against the file opened (`docs/data-access.md:172-189`)."
}
```
```json
{
    "path":  "src/ootp_ai/saves.py",
    "change":  "P3 NEW: enumerate a save by confirming `players.dat` AND `teams.dat` are present, never by a `*.lg` glob — the saved-games root holds a stray empty directory literally named `.lg` (`docs/data-access.md:60-63`). Plus the `challenge.dat`-at-241-bytes mode check as a pre-flight."
}
```
```json
{
    "path":  "src/ootp_ai/snapshot.py",
    "change":  "P4 NEW: copy only the ~46 MB in-scope set (players 32.07 + names 8.64 + teams 5.32 MB) to `\u003csnapshot_root\u003e/\u003cleague\u003e/\u003csim_date\u003e/` with a per-file size + SHA-256 manifest, every handle `\"rb\"`. All parsing runs against the snapshot, never the live save."
}
```
```json
{
    "path":  "src/ootp_ai/ingest.py",
    "change":  "P4 NEW (shape) / P9 (persist) / P10 (timing): the ingest-run record — source file sizes, SHA-256 digests, header versions, sim date, human team, row counts, residual bytes, wall-clock parse time. Resolves the human team FROM `saved_games.dat` via the shared header reader plus a string walk, never a substring scrape (F19), never hardcoded."
}
```
```json
{
    "path":  "src/ootp_ai/parser/teams.py",
    "change":  "P5 NEW: sequential walk yielding `team_id`, the 5-string signature already `verified` at `docs/data-access.md:224-226`, ARGB colors, level, `parent_team_id`, the sub-league/division hierarchy and the win-loss fields. Strict byte accounting — zero residual."
}
```
```json
{
    "path":  "src/ootp_ai/parser/names.py",
    "change":  "P6 NEW: walk the observed record shape (u32 len + ASCII + u32 `0` + u32 monotonic index + three u32s + `0x27` separator, alphabetically ordered). Strict byte accounting. The name table is an object OWNED BY A SAVE — never a module-level constant, per SD-10."
}
```
```json
{
    "path":  "src/ootp_ai/parser/players.py",
    "change":  "P7 NEW: the deliberately minimal field set — `player_id`, team/org assignment, position, uniform number, date of birth, bats/throws, the name indices, `historical_id`. Diagnostic byte accounting: record-count match plus record-boundary termination, residual recorded."
}
```
```json
{
    "path":  "src/ootp_ai/parser/rosters.py",
    "change":  "P7 NEW: extraction at the `team_roster` grain (`team_id`, `player_id`, `list_id`), plus the empirical derivation of each `list_id` value\u0027s meaning with the SD-17 fallback wired in — an opaque integer and no human label if the mapping cannot reach `inferred`."
}
```
```json
{
    "path":  "src/ootp_ai/contracts/",
    "change":  "P8 NEW: the tracked field-map / contract declaration, TOML read with stdlib `tomllib` so it adds no dependency. Per field: name, type, walker, category (`identity`/`rating-true`/`rating-scouted`/`contract`/`structural`), epistemic label, validator tier. Plus the three declared grains including the `save_id` key component (SD-09). ONE declaration, THREE consumers: DDL emitter, grain test, catalog generator."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/ddl.py",
    "change":  "P9 NEW: emits `bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name` DDL FROM the contracts declaration — it reads the declaration, it does not restate it."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/loader.py",
    "change":  "P9 NEW: typing, casing, dedup ONLY — no joins, no filtering, no semantic renaming (`.claude/agents/data-engineer.md:98`). Append-only per (`snapshot_date`, `save_id`) partition; snapshots immutable; structural absence preserved as `NULL` never zero. Also writes the per-field epistemic-label metadata table."
}
```
```json
{
    "path":  "src/ootp_ai/reports/__main__.py",
    "change":  "P11 NEW: `uv run python -m ootp_ai.reports render`, with `roster.py` and `standings.py` siblings. Writes to the git-ignored output root. The organization filter lives HERE, never at bronze."
}
```
```json
{
    "path":  "src/ootp_ai/catalog/__main__.py",
    "change":  "P12 NEW: `uv run python -m ootp_ai.catalog`. Reads `information_schema` for counts and the contracts declaration for grains/keys/labels. Emits the deterministic TRACKED structural half (sorted, no timestamps, no absolute paths, plus the report-path pointer per SD-11) and the volatile half + `catalog.json` into the ignored root."
}
```
```json
{
    "path":  "tests/test_no_leaks.py",
    "change":  "P11 MAIN-THREAD EDIT (folded-in #1): extend beyond the four filenames and two suffixes at `:106-107` to catch RENDERED game data — assert the report and catalog output roots resolve to a git-ignored path, and that the tracked catalog/field map may name source FILES but never absolute paths (F19). Keep `test_patterns_still_catch_real_leaks` at `:51-78` green."
}
```
```json
{
    "path":  "tests/ (16 new modules, ALL main-thread authored)",
    "change":  "test_config.py, test_db_identifiers.py, test_doc_corrections.py, test_save_header.py, test_sequential_walk.py, test_no_fixed_offsets.py, test_save_enumerator.py, test_read_only.py, test_snapshot_semantics.py, test_parse_teams_synthetic.py, test_byte_accounting.py, test_names_join.py, test_names_join_boston.py, test_parse_real_save.py, test_grain_contracts.py, test_withheld_fields.py, test_parser_vs_export.py, test_extraction_cost.py, test_reports.py, test_catalog.py. NONE may be written by the data-engineer subagent — `tests/` is the first entry of its deny set."
}
```
```json
{
    "path":  "tests/fixtures/",
    "change":  "P3 NEW: hand-authored synthetic byte sequences only, never a slice of a real save (`tests/fixtures/README.md:15-28`). Synthetic headers at v25/v24/v26, a magic-at-offset-0 buffer, a filename-mismatch header, and the 1-year vs 10-year contract record pair. NON-`.dat` extensions — `.gitignore:62`\u0027s negation would otherwise let git track them."
}
```
```json
{
    "path":  "gm/standing-orders.md",
    "change":  "P13 UMPIRE EDIT (main thread, not the builder): add the new engineering-owned report kind to the `## Reports` format block at `:42-50` per Decisions §4, then the two report entries. The `Status: none active` line at `:10-11` changes."
}
```
```json
{
    "path":  "docs/decisions/0004-mysql-warehouse.md",
    "change":  "P13: add a §Notes entry recording the dbt deferral — the trigger and why it was not pulled (Decisions §9). ADR 0005\u0027s PATTERN choice is honoured in full; only its TOOLING phrasing is deferred. A superseding ADR is too heavy for a postponement, but quietly diverging is the one option this repo forbids."
}
```
```json
{
    "path":  "docs/data-access.md",
    "change":  "P13, ROUTED THROUGH `/update-docs` ONLY — this file is in the subagent\u0027s deny set at `:156`. Deltas: §1\u0027s file table is incomplete (18 `.dat` files, several unlisted); `saved_games.dat` is NOT plaintext, downgrading the `verified` label at `:36-38`; the `names.dat` fixed-size-per-save finding at `inferred`; `ootp_truth_osa` retired; and label upgrades for exactly the fields Tier A or Tier B proved, everything else left `unconfirmed` and therefore withheld."
}
```
```json
{
    "path":  "requests/feature-requests/README.md",
    "change":  "P13: advance the Index row at `:119` (matched by its `[first-sight]` link) from `scoped` to `plan` when the plan lands, and to `implemented` only after the two USER-RUN criteria return green. The slug moves once into `_done/` at the terminal stage."
}
```

### code_references

```json
{
    "ref":  "src/ootp_ai/__init__.py:7",
    "claim":  "`__version__ = \"0.1.0\"` is the package\u0027s entire content besides a docstring — every module in this plan is created from nothing, which is why phase ordering carries all the risk and there is no existing code to regress against."
}
```
```json
{
    "ref":  "pyproject.toml:9",
    "claim":  "`dependencies = []` — the first runtime dependency is a decision phase 1 must make explicitly (a `.env` loader and a MySQL driver), not an import someone adds mid-phase."
}
```
```json
{
    "ref":  "pyproject.toml:78",
    "claim":  "`addopts = \"-q --strict-markers --strict-config\"` — an undeclared marker is a hard COLLECTION error, not a failure, which is why the marker widening is sequenced first."
}
```
```json
{
    "ref":  "pyproject.toml:80",
    "claim":  "The single declared marker reads \u0027requires a local OOTP install or save\u0027 and says nothing about a database. Phase 1 widens it to \u0027install, save, or warehouse\u0027 rather than adding a second marker."
}
```
```json
{
    "ref":  "pyproject.toml:69-73",
    "claim":  "mypy is `strict = true` over `files = [\"src\", \"tests\"]` — strict typing applies to the test suite too, so every new test needs annotations and the MySQL driver needs stubs."
}
```
```json
{
    "ref":  ".github/workflows/ci.yml:49",
    "claim":  "CI runs `uv run pytest -m \"not gamedata\"`, so the offline suite is the only regression protection on future PRs — every phase carries an offline assertion, not only a gamedata one."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:69-72",
    "claim":  "The fixed-offset ban with its evidence (the same player\u0027s ratings block at 43 bytes from one anchor and 107 in another). Phase 3 encodes it mechanically as `tests/test_no_fixed_offsets.py` and structurally as a Cursor with no seek."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:91-92",
    "claim":  "\u0027Never require a game install to satisfy a test\u0027 — the reason phases 5 and 7 add synthetic-buffer tests alongside their real-save tests rather than relying on `-m gamedata` alone."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:98",
    "claim":  "Bronze is 1:1 with parser output — no filtering. This is why phase 9 lands all 259 teams and every minor-league population, and the Boston-only filter waits until phase 11\u0027s report."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:101",
    "claim":  "Grain declared in prose AND proved by a uniqueness test, the two agreeing. Phase 8\u0027s `tests/test_grain_contracts.py` compares the declaration\u0027s prose sentence against the key the DDL emits."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:150",
    "claim":  "`tests/` is the FIRST line of the write-deny set. Every phase splits authorship on this — subagent builds `src/ootp_ai/**`, main thread writes tests — or the phase returns an Escalation with zero code."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:156",
    "claim":  "`docs/data-access.md` is deny-set for WRITES (reads are free), so every parser finding travels as a `## docs-delta` routed through `/update-docs` in phase 13 rather than being edited in place."
}
```
```json
{
    "ref":  "tests/test_agent_contract.py:69-75",
    "claim":  "`test_deny_set_still_protects_the_guards` asserts `tests/`, `.github/`, `ops/`, `CLAUDE.md` and `docs/decisions/` stay in the deny set — the mechanical backstop behind this plan\u0027s authorship split."
}
```
```json
{
    "ref":  "tests/test_no_leaks.py:31-48",
    "claim":  "`tracked_text_files()` enumerates via `git ls-files`, so the guard cannot see an unstaged file — a leak in an untracked artifact passes locally and fails in CI. Recorded as a follow-up in phase 11, not fixed here."
}
```
```json
{
    "ref":  "tests/test_no_leaks.py:97-116",
    "claim":  "`test_game_data_is_not_tracked` bans four filenames and the `.dat`/`.lg` suffixes. It is the only thing catching a `.dat` fixture (see the .gitignore note) and it catches `players.csv` by FILENAME ONLY — a renamed derived copy sails through, which is why Decisions §5 hard-binds against tracking a Lahman-to-name lookup."
}
```
```json
{
    "ref":  ".gitignore:31",
    "claim":  "`*.dat` is ignored — but `.gitignore:62`\u0027s later `!tests/fixtures/**` negation re-includes it, so git would track `tests/fixtures/foo.dat` happily. Phase 3\u0027s fixtures therefore take a non-`.dat` extension."
}
```
```json
{
    "ref":  ".gitignore:18",
    "claim":  "`var/` is the gitignored working root the reports, the volatile catalog half and the phase-2 spike script all write into, satisfying AC14\u0027s `git check-ignore -q` requirement."
}
```
```json
{
    "ref":  "tests/test_doc_links.py:15",
    "claim":  "`markdown_files()` skips `var` when ENUMERATING files, but `test_relative_links_resolve` still resolves link TARGETS — so a tracked Markdown link into the ignored output root turns CI red. The catalog\u0027s report pointer is text, never a link (SD-11)."
}
```
```json
{
    "ref":  "docs/data-access.md:14",
    "claim":  "\u0027`unconfirmed` — Nobody has looked. An unconfirmed claim is a task, not a fact.\u0027 This is the rule that forces phase 2 (the scouted-view spike) and phase 6 (the names encoding) to precede anything that builds on them."
}
```
```json
{
    "ref":  "docs/data-access.md:60-63",
    "claim":  "A `*.lg` glob is not a list of saves — the saved-games root holds a stray empty directory literally named `.lg`. Phase 3\u0027s enumerator confirms `players.dat` and `teams.dat` are present instead."
}
```
```json
{
    "ref":  "docs/data-access.md:65-68",
    "claim":  "`challenge.dat` is present at exactly 241 bytes in a Challenge Mode save — a filesystem-level mode check with no menu, promoted to a pre-flight in phase 3 and asserted in phase 4\u0027s snapshot step."
}
```
```json
{
    "ref":  "docs/data-access.md:172-189",
    "claim":  "The header layout: leading `0x00`, magic at offset 1 (not 0), u32 version 25 at offset 5, self-naming filename at offset 25. All four of AC1\u0027s assertions come straight from this block."
}
```
```json
{
    "ref":  "docs/data-access.md:224-226",
    "claim":  "The `teams.dat` 5-string signature is already `verified`, which is why the teams walk is sequenced first among the three files — it validates against an existing belief rather than establishing one."
}
```
```json
{
    "ref":  "docs/data-access.md:238",
    "claim":  "\u0027`unconfirmed` — The index encoding and the `names.dat` table layout.\u0027 The largest single unknown in the request, and the reason phase 6 is placed before the players walk with a pre-registered fallback."
}
```
```json
{
    "ref":  "docs/data-access.md:282-295",
    "claim":  "The critical-path question — whether the scouted view is stored at all — and the exact test that has never been run. Phase 2 runs it with the pivot rule committed first, satisfying AC18."
}
```
```json
{
    "ref":  "docs/league-rules.md:129",
    "claim":  "\u0027parser reads `leagues.dat` directly and may recover some of these\u0027 — a file that does not exist among `OOTP-AI.lg`\u0027s 18 `.dat` files. Corrected in phase 2 (AC19)."
}
```
```json
{
    "ref":  "docs/league-rules.md:295",
    "claim":  "\u0027Until the parser can open `leagues.dat`, every value here is believed rather than confirmed\u0027 — the second `leagues.dat` assertion AC19 requires removed."
}
```
```json
{
    "ref":  "docs/league-rules.md:80",
    "claim":  "Records `schedule_file_1 = major_league_ml_c_2024.lsdl` — exactly the string the scope located at byte 5,559,751 of `world.dat`, which is the corrected location phase 2 records."
}
```
```json
{
    "ref":  "docs/league-rules.md:26",
    "claim":  "\u0027the warehouse supersedes this the moment the parser lands\u0027 — becomes partly false on delivery (scope risk 11), so phase 13 corrects it alongside `:31`."
}
```
```json
{
    "ref":  ".env.example:22-25",
    "claim":  "`OOTP_SNAPSHOT_ROOT` is documented as defaulting to `var/snapshots` and warned against cloud-synced storage. Verified against the live `.env`: it is EMPTY, so phase 1 must define and validate the default rather than assume a value."
}
```
```json
{
    "ref":  ".env.example:57-58",
    "claim":  "`MYSQL_TRUTH_REAL_DATABASE` and `MYSQL_TRUTH_OSA_DATABASE`; the latter is retired in phase 1 per Decisions §10, since `ootp_truth_real` already carries both scouting perspectives from one export."
}
```
```json
{
    "ref":  "ops/mysql-bootstrap.sql:23-24",
    "claim":  "Creates the `ootp` warehouse schema (measured: 0 tables today) that phase 9\u0027s loader lands bronze into — and dropping those tables is how phase 9 is reverted."
}
```
```json
{
    "ref":  "ops/mysql-bootstrap.sql:32-33",
    "claim":  "Creates `ootp_truth_osa`, whose create and its grant at `:49` phase 1 removes."
}
```
```json
{
    "ref":  "ops/mysql-bootstrap.sql:35-38",
    "claim":  "Schemas are `utf8mb4_0900_ai_ci` — accent- and case-INSENSITIVE. Phase 6\u0027s exact-string name comparison must state its collation explicitly (SD-13) or its \u0027100% exact\u0027 claim is weaker than it reads."
}
```
```json
{
    "ref":  "gm/standing-orders.md:42-50",
    "claim":  "The `## Reports` five-field format block Decisions §4 extends with an engineering-owned report kind, and where phase 13\u0027s two report entries land."
}
```
```json
{
    "ref":  "gm/standing-orders.md:10-11",
    "claim":  "\u0027Status: none active\u0027 — the line that changes when phase 13 lands the first two report entries; useful as a one-line check that the tracked half of the report channel actually shipped."
}
```
```json
{
    "ref":  ".claude/agents/gm.md:4",
    "claim":  "`tools: Read, Glob` — the entire delivery surface for this feature. Everything phases 11 and 12 produce must be a readable file on disk; there is no query path."
}
```
```json
{
    "ref":  ".claude/agents/gm.md:32",
    "claim":  "Forced-read item 8, \u0027Any report or analysis handed to you for this invocation\u0027 — the mechanism acceptance criterion 20 rides on, which is why phase 12\u0027s tracked catalog carries the spawn instruction."
}
```
```json
{
    "ref":  "tests/fixtures/README.md:32-37",
    "claim":  "Names exactly the fixtures phase 3 needs — \u0027a length-prefixed string at a buffer boundary, a 1-year contract next to a 10-year one, a header carrying an unrecognized version byte\u0027 — so the fixture set is prescribed, not invented."
}
```
```json
{
    "ref":  "tests/fixtures/README.md:45-51",
    "claim":  "\u0027A real save\u0027s day-0 state is the LEAST informative test input available\u0027 — the argument for AC2\u0027s synthetic pair, and the reason a green parse of `OOTP-AI.lg` at 2024-03-07 proves almost nothing about fixed offsets."
}
```
```json
{
    "ref":  "docs/decisions/0005-hybrid-data-layer.md:66-71",
    "claim":  "The boundary rule verbatim and its worked example that `players.csv` resolves as STATIC REFERENCE — which is what keeps this feature off the `datasets/` side and justifies the non-goal of creating `build/` or a manifest entry."
}
```
```json
{
    "ref":  "docs/decisions/0012-scouted-ratings-only.md:57-59",
    "claim":  "\u0027A field we cannot classify must be treated as true-rating and withheld\u0027 — the ADR text phase 8\u0027s `tests/test_withheld_fields.py` enforces by declared CATEGORY rather than by column-name glob."
}
```
```json
{
    "ref":  "requests/feature-requests/README.md:70-85",
    "claim":  "Defines testable as \u0027a cold agent can run one command and get a pass or fail\u0027, and requires human-only criteria be marked user-run — which is why AC20 and AC21 are held back to phase 13 as explicitly USER-RUN."
}
```
```json
{
    "ref":  "requests/feature-requests/README.md:119",
    "claim":  "The Index row for `first-sight` at Stage `scoped` — the cell phase 13 advances, matched by its `[first-sight]` link."
}
```
```json
{
    "ref":  "requests/README.md:20-32",
    "claim":  "Explains why a wrong `u16` produces a plausible number with every test green and no stack trace — the failure class phases 5-10\u0027s ground-truth harness exists to catch, and the reason phase 10 must be green before phase 11 renders anything."
}
```

### open_questions

- WHICH MySQL DRIVER, and does it type-check under strict mypy? `pyproject.toml:69-73` runs mypy strict over `src` AND `tests`, so an unstubbed driver makes every `db.py` call an untyped-call error. Recommendation: `PyMySQL` plus `types-PyMySQL` in the dev group. Alternative: `mysql-connector-python`, which ships inline types but is a heavier dependency. This must be disposed in phase 1 — discovering it at phase 9 means rewriting the loader's signatures.
- WHERE DOES THE TRACKED STRUCTURAL CATALOG LIVE? Recommendation `docs/warehouse-catalog.md` + `docs/warehouse-catalog.json`, because CLAUDE.md forbids creating directories speculatively and a new top-level `catalog/` needs an argument. If it lands in `docs/`, decide whether it joins `tests/test_repo_structure.py:12-24`'s required-docs list — a main-thread test edit, not a builder one.
- FORMAT AND LOCATION OF THE CONTRACT DECLARATION. Recommendation: TOML under `src/ootp_ai/contracts/`, read with stdlib `tomllib` so it adds no dependency and ships inside the package. The alternative — a top-level `contracts/` directory — is more discoverable but creates a new tracked top-level dir. Whichever is chosen must be the subagent's declared target path in phases 8 onward.
- COLLATION FOR THE CROSS-SCHEMA NAME COMPARISON (SD-13). `ops/mysql-bootstrap.sql:24` creates every schema `utf8mb4_0900_ai_ci`, which is accent- AND case-insensitive — so an 'exact string equality' claim in AC7 is materially weaker than it reads, in a repo whose own export doc warns that accent replacement breaks name validation. Decide: a binary collation in the comparison SQL, or fetch-then-compare in Python. State the choice in the test.
- WHERE DOES THE RENDERED-REPORT OUTPUT ROOT RESOLVE? A new `.env` key, or a fixed subdirectory of `OOTP_SNAPSHOT_ROOT`? AC14 only requires it be git-ignored, and both satisfy that. A new key is more explicit and matches the resolve-by-name convention; a subdirectory is one fewer thing to configure. Phase 11 needs an answer, phase 12's tracked pointer records it either way.
- IS PHASE 1 PRECEDING THE SPIKE ACCEPTABLE? Core §1 says 'spike first'; this plan puts config, dependencies and DB access before it, on the grounds that the spike needs `.env`-resolved paths and a `ootp_truth_real` connection and that hardcoding them would violate Core §2 on the very first artifact. Phase 1 contains no parser code and no ratings code, so AC18's actual constraint — a verdict committed before any ratings code exists — is satisfied. Confirm the reading, or invert the two and accept a throwaway hardcoded spike script under `var/`.
- IF THE PHASE-2 SPIKE RETURNS ABSENT, does the user want the remaining 11 phases to proceed unchanged? The pre-registered pivot says yes — the reports need names, positions and roster membership, and none of those needs a single rating, so the slice ships either way. But a FAIL verdict on the mechanic behind ADRs 0012/0014/0016 is worth an explicit go/no-go rather than a plan that carries past it silently.
- SD-21 IS FLAGGED, NOT SOLVED: regenerating a report overwrites the prior snapshot's view, breaking citation integrity for any `gm/decisions/` record citing it. Nothing in this slice fixes it and nothing should — there is exactly one league state today. But the user should decide whether a follow-up request is filed now, while the reason is fresh, or when the first decision record actually cites a report.

---

## Lens: (unnamed lens)

### planner

domain-convention

### ok

```json
true
```

### onboarding_files

```json
{
    "path":  "requests/feature-requests/first-sight/PROJECT_SCOPE.md",
    "why":  "The decided upstream artifact. 21 acceptance criteria, the tiered scope, and 11 resolved Decisions. Consume it; do not re-open it. Read the Acceptance Criteria preamble first — it contains the two blockers that shape the whole plan (the widened `gamedata` marker, and `tests/` being main-thread-only)."
}
```
```json
{
    "path":  "requests/feature-requests/first-sight/FEATURE_REQUEST.md",
    "why":  "Context only. Its Scope Signals put `scouting.dat` in scope; the scope decoupled that and says why. Read it to understand what the scope deliberately reshaped, not as a requirements source."
}
```
```json
{
    "path":  ".claude/agents/data-engineer.md",
    "why":  "The single owner of the build rules and the file that binds the implementation subagent. Load-bearing lines: `:69-72` fixed-offset ban, `:91-92` never require a game install for a test, `:98` bronze is 1:1 with parser output, `:101` grain in prose AND proven, `:117-120` no OOTP game data in git, `:130` anything outward-facing is user-run, `:132-166` the write allowlist and the deny set (`tests/`, `docs/data-access.md`, `docs/decisions/` are all denied)."
}
```
```json
{
    "path":  "docs/data-access.md",
    "why":  "The format catalog, and every claim carries an epistemic label. `:173-186` the header layout and the magic-at-offset-1 trap; `:193-200` primitives; `:204-215` variable-length regions and the sequential rule; `:224-226` the `verified` teams.dat 5-string signature; `:234-238` names are indirected and the encoding is `unconfirmed`; `:280-295` the critical-path scouted-view question and the exact spike test; `:335` `Replace accents` was Off, which is why collation matters."
}
```
```json
{
    "path":  "pyproject.toml",
    "why":  "Every toolchain constraint the plan must satisfy: `:9` `dependencies = []` (no runtime dep chosen yet), `:23` python-dotenv sits in the DEV group only, `:52-60` ruff selects `A`/`DTZ`/`PTH`/`N`, `:73` mypy strict over `src` AND `tests`, `:78` `--strict-markers`, `:80` the single `gamedata` marker whose description this scope widens."
}
```
```json
{
    "path":  "tests/test_no_leaks.py",
    "why":  "The guard this feature extends. `:24-28` the leak patterns, `:31-48` `tracked_text_files()` enumerates via `git ls-files` (so it cannot see an unstaged file — a known local-feedback gap), `:97-116` `test_game_data_is_not_tracked` with `banned_suffixes` at `:107`. This is the only thing stopping a `.dat` fixture from being committed — see the .gitignore note below."
}
```
```json
{
    "path":  "tests/test_doc_links.py",
    "why":  "Live defect. `:10` one regex for all Markdown links, `:11` skips only http/mailto/#, `:15` excludes files UNDER `var/` but not links TO `var/`. A tracked Markdown link into the ignored output root turns CI red today. Every citation in the plan\u0027s own artifacts uses code spans for that reason."
}
```
```json
{
    "path":  ".gitignore",
    "why":  "`:18` `var/`, `:31` `*.dat`, `:61` `!datasets/**` (a carve-out for a directory that does not exist — do not create it), `:62` `!tests/fixtures/**`. VERIFIED by running `git check-ignore -q`: `tests/fixtures/sample.dat` exits **1** (NOT ignored — line 62 negates line 31), while `var/reports/roster.md` exits **0** (ignored). So a `.dat` fixture is committable and only `test_no_leaks.py:107` stops it."
}
```
```json
{
    "path":  "docs/league-rules.md",
    "why":  "The correction target. `:129` \"The parser reads `leagues.dat` directly\" and `:295` \"Until the parser can open `leagues.dat`\" are both false — no such file exists. `:26` and `:31` claim the warehouse supersedes §1 \"the moment the parser lands\", which this slice partially falsifies. `:79-81` records the `schedule_file_1` value found in `world.dat`."
}
```
```json
{
    "path":  "gm/standing-orders.md",
    "why":  "`:27-50` the `## Reports` section and its format block — the tracked half of the report channel lands here, and Decisions §4 requires a new engineering-owned report kind added to that format block. `:10-11` currently reads \"Status: none active\"."
}
```
```json
{
    "path":  ".claude/agents/gm.md",
    "why":  "`:4` `tools: Read, Glob` is the entire delivery surface for this feature — the GM can only read files. `:32` forced-read item 8 (\"any report or analysis handed to you\") is how the reports reach it, which is what acceptance criterion 20 exercises."
}
```
```json
{
    "path":  "docs/decisions/0004-mysql-warehouse.md",
    "why":  "`:89-106` the open dbt adapter question and the four live options. Decision §9 of the scope requires a deferral note appended to this §Notes rather than a superseding ADR. `docs/decisions/` is in the subagent\u0027s deny set, so this is main-thread work."
}
```
```json
{
    "path":  "tests/fixtures/README.md",
    "why":  "What a fixture may be: synthetic byte sequences we authored, never a slice of a real save. `:26-28` states plainly that the leak guard cannot catch a renamed real slice — that one is on the implementer."
}
```
```json
{
    ".path":  "x",
    "path":  ".github/workflows/ci.yml",
    "why":  "`:38-44` the three quality gates (`ruff check .`, `ruff format --check .`, `mypy`) and `:49` `pytest -m \"not gamedata\"`. CI has no game install and no MySQL, which is why criteria 1-5, 13 and 16 must run offline."
}
```

### architecture_notes

The repo has no pipeline code at all: `src/ootp_ai/__init__.py` is 241 bytes holding `__version__ = "0.1.0"` and a docstring saying "Phase 0. No pipeline code yet". Everything below is created from nothing. Baseline verified green: `uv run pytest -m "not gamedata"` = 18 passed.

PACKAGE SHAPE (proposed, all new under `src/ootp_ai/`):
- `config.py` — resolves `OOTP_INSTALL`, `OOTP_SAVED_GAMES`, `OOTP_LEAGUE`, `OOTP_SNAPSHOT_ROOT`, the two new probe keys, and MySQL settings from `.env` only. No literal path, no `parents[N]` walk outside test modules (`data-engineer.md:88-90`). `OOTP_SNAPSHOT_ROOT` is empty in `.env` today, so the default (`var/snapshots`) must be defined here and validated as local disk.
- `saves.py` — the enumerator. Confirms `players.dat` AND `teams.dat` exist before calling a directory a save (`data-access.md:60-63`: the saved-games root contains a stray empty directory literally named `.lg`).
- `parser/cursor.py` — a forward-only cursor over `bytes`. This is the architectural keystone: **the header reader uses the same cursor**, reading 1 byte then 4 then a u32 sequentially rather than indexing offsets 1/5/25. That is what lets the AC3 fixed-offset guard scan all of `src/ootp_ai/parser/` with ZERO exemptions. If the header reader indexes literals, the guard needs an exemption list and stops being a guard.
- `parser/header.py`, `parser/errors.py` (`UnsupportedSaveVersion`), `parser/teams.py`, `parser/names.py`, `parser/players.py`, `parser/roster.py`, `parser/saved_games.py`.
- `contracts/field_map.toml` + `contracts/__init__.py` — the tracked declaration. **One declaration, three consumers**: the DDL emitter, the grain tests, and the catalog generator. That is the mechanism that makes prose-vs-enforcement drift structurally impossible (`data-engineer.md:101`). TOML because `tomllib` is stdlib in 3.12, it is read-only (nothing writes it), and it carries comments — the epistemic rationale per field needs them. It ships inside the package so it resolves via `importlib.resources`, never a path walk.
- `warehouse/sql.py` (identifier quoting), `warehouse/ddl.py`, `warehouse/load.py`, `warehouse/ingest_run.py`.
- `reports/__main__.py` (must expose `render`, per AC14's `python -m ootp_ai.reports render`), `reports/roster.py`, `reports/standings.py`.
- `catalog/__main__.py` (AC15 invokes `python -m ootp_ai.catalog` with no subcommand), `catalog/generate.py`.

THE TWO-UNIVERSE KEY. The pipeline parses two saves — `OOTP-AI` (Boston, Challenge Mode, 2024-03-07) and the retained standard-mode probe (Chicago Cubs, 2024-03-18). Every bronze primary key carries `save_id` alongside `snapshot_date` (SD-09). Recommendation: `save_id` is the league directory stem (`OOTP-AI`), typed `VARCHAR(64) NOT NULL`, validated at config time against `^[A-Za-z0-9_-]+$`. That regex does double duty — it makes it structurally impossible for an absolute path to become a `save_id` and leak into the catalog, which is the F19 concern.

THE CATALOG SPLIT (Decisions §3). Structural half = derived schema knowledge, generated from `field_map.toml` alone with no game data and no DB → tracked, and regenerable offline. Volatile half = row counts, snapshot dates, freshness → generated into the git-ignored root. Proposed placement: `docs/warehouse-catalog.md` + `docs/warehouse-catalog.json` tracked; `var/catalog/catalog.md` + `catalog.json` generated. Consequence worth acting on: **AC15's "regenerated during the test and byte-identical to the committed copy" clause needs no game data and no MySQL, so it should run OFFLINE in CI rather than under `-m gamedata`.** Splitting AC15 that way strictly increases what CI enforces.

REPORT PATHS ARE SNAPSHOT-PARTITIONED. Render to `<output_root>/<save_id>/<snapshot_date>/roster.md`. This dissolves Risk 10 / SD-21 (regenerating overwrites the prior snapshot's view and breaks citation integrity for `gm/decisions/` records) at zero cost: a new sim date writes a new directory, and re-rendering the same snapshot is idempotent by construction. The tracked catalog's report pointer names the pattern as a code span, never as a Markdown link into `var/` — `tests/test_doc_links.py:15` excludes files under `var/` but not links to it, so a link there turns CI red today.

OWNERSHIP SPLIT — THIS IS A HARD CONSTRAINT, NOT A PREFERENCE. `.claude/agents/data-engineer.md:150-157` puts `tests/`, `.github/`, `ops/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md` and `docs/decisions/` in a hard deny set, and `:164-166` instructs the subagent to stop and report rather than build when spec targets fall inside it. So:
- Subagent-buildable: `src/ootp_ai/**` and `src/ootp_ai/contracts/field_map.toml`. Nothing else.
- Main-thread-only: every file under `tests/`, `pyproject.toml`, `.env.example`, `docs/**`, `gm/**`, `README.md`, `CLAUDE.md`, `requests/**`.
A plan that hands the whole spec to the data-engineer produces an Escalation and zero tests (Risk 8).

### phases

```json
{
    "name":  "Phase 0 — Pre-register the pivots, then run the scouted-view spike",
    "goal":  "Answer docs/data-access.md §5\u0027s critical-path question with a written verdict BEFORE any parser code exists, and pre-register every fallback the later phases might need — so no phase hits an unbounded research task on the critical path.",
    "steps":  [
                  "Write `requests/feature-requests/first-sight/SPIKE_SCOUTED_VIEW.md` containing the kill/pivot rule FIRST, before running anything: FOUND -\u003e the parser has a ratings source and ADRs 0012/0014/0016 have a data path; ABSENT -\u003e record it, withhold every rating, ship the reports anyway. The rule is written before the spike returns, not after (scope Core §1, AC18).",
                  "Run the test written at `docs/data-access.md:292-295`: pull the values in `ootp_truth_real.players_scouted_ratings` (36,144 rows, `scouting_coach_id` in {-1, 2759}, 18,072 each) and search the probe save\u0027s `scouting.dat` (2,349,181 bytes) for them. Keep the spike script in the scratchpad or `var/` — it is a one-off; the VERDICT document carries the method and byte evidence so it is re-runnable.",
                  "Record the verdict with an epistemic label and the byte evidence. Note explicitly that no ratings land in THIS slice whatever the verdict returns — the players.dat field set (Core §7) carries no rating field at all, so the verdict informs the NEXT slice.",
                  "In the same document pre-register three more fallbacks so later phases are bounded: (a) `list_id` semantics — if the mapping cannot reach `inferred`, land it as an opaque integer, group the roster report by raw value with a header line stating the meanings are `unconfirmed`, and NEVER print a human label (Core §9, SD-17); (b) `teams.dat` strict byte accounting — if a zero-residual walk cannot be reached, fall back to the same diagnostic form used for `players.dat` (record the residual, assert termination on a record boundary) rather than open-ended research; (c) the `names.dat` join — if the encoding resists, resolve names from `players.csv` at render time for the ~1,712 Lahman-carrying players, fictional players render as IDs, and NOTHING is tracked (Decisions §5).",
                  "Record the measured `world.dat` league-config location (`major_league_ml_c_2024.lsdl` at byte 5,559,751) in the same document so Phase 10\u0027s doc correction has a citation."
              ],
    "acceptance":  [
                       "`requests/feature-requests/first-sight/SPIKE_SCOUTED_VIEW.md` exists, states stored-or-computed with an epistemic label, cites byte evidence, and its kill/pivot rule appears ABOVE the verdict in the document.",
                       "`git log` shows no file under `src/ootp_ai/parser/` in the tree at this commit — the verdict genuinely precedes any parser code (AC18).",
                       "All three fallbacks (list_id, teams.dat byte accounting, names.dat) are written down with a concrete trigger condition, not as prose intentions.",
                       "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all clean (baseline: 18 passed)."
                   ],
    "commit_note":  "Spike: scouted-view verdict + pre-registered pivot rules. Main-thread only, no code. /commit."
}
```
```json
{
    "name":  "Phase 1 — Toolchain, config layer, save enumerator",
    "goal":  "Choose the first runtime dependencies, widen the pytest marker, and land config + enumeration that resolve everything by name from .env — the spine every later phase sits on.",
    "steps":  [
                  "Choose the MySQL driver. RECOMMENDATION: `PyMySQL` + `types-PyMySQL`. Rationale a cold agent can check: pure Python (no C toolchain on the Windows dev box), MIT-licensed (this repo is MIT and public), and a maintained stubs package exists — which matters because `pyproject.toml:73` runs mypy strict over `src` AND `tests`. `mysql-connector-python` is Oracle GPLv2-with-FOSS-exception; `mysqlclient` needs a build toolchain. Record the pick and its rationale in the plan\u0027s Decisions.",
                  "Move `python-dotenv` from the dev group (`pyproject.toml:23`) into `[project].dependencies` (`:9`) — it is a RUNTIME dependency of the config layer, and leaving it dev-only means the installed package cannot read `.env`. Add `PyMySQL`; add `types-PyMySQL` to the dev group.",
                  "Widen the `gamedata` marker at `pyproject.toml:80` to \"requires a local OOTP install, save, or warehouse\". Do NOT add a second marker — `addopts` carries `--strict-markers` (`:78`), so an undeclared marker is a hard collection error, and the scope explicitly chose widening over a second marker.",
                  "Add two new keys to `.env.example`: the probe-save directory and the disposable Challenge Mode probe save (Core §19). Mark `MYSQL_TRUTH_OSA_DATABASE` (`:58`) as RETIRED with a one-line reason (`ootp_truth_real` already carries both scouting perspectives from one export — the premise for a second export database is measurably wrong). Keep every value empty: `tests/test_no_leaks.py:25` will flag a drive-letter path.",
                  "Write `src/ootp_ai/config.py`: a frozen dataclass resolved from `.env` via `python-dotenv`. Resolve `OOTP_INSTALL`, `OOTP_SAVED_GAMES`, `OOTP_LEAGUE`, `OOTP_SNAPSHOT_ROOT`, the two probe keys, and MySQL connection settings. `OOTP_SNAPSHOT_ROOT` is EMPTY in `.env` today — define the default as `var/snapshots` and validate it resolves to local disk (`.env.example:23-24` warns the saved-games root may be OneDrive-redirected). Derive `save_id` as the league directory stem and validate it against `^[A-Za-z0-9_-]+$` so a path can never become a save_id.",
                  "Write `src/ootp_ai/saves.py`: an enumerator that confirms `players.dat` AND `teams.dat` exist before treating a directory as a save (`data-access.md:60-63` — a `*.lg` glob is not a list of saves; there is a stray empty `.lg` directory). Add the `challenge.dat`-at-exactly-241-bytes mode check as a filesystem-level pre-flight (`data-access.md:65-68`, folded-in #6).",
                  "MAIN THREAD writes `tests/test_config.py` and `tests/test_saves.py`, both OFFLINE: monkeypatch the environment, build a fake save tree under `tmp_path` including a stray empty `.lg` directory, and assert the enumerator rejects it. `data-engineer.md:91-92` — never require a game install to satisfy a test.",
                  "Watch the ruff rules already selected at `pyproject.toml:52-60`: `A` (no `id`, `type`, `bytes`, `format` as names — this bites a parser hard), `PTH` (pathlib only, no `os.path`), `DTZ` (any naive datetime is an error; use `datetime.date` for the sim date and `time.perf_counter()` for timing)."
              ],
    "acceptance":  [
                       "`uv run pytest -m \"not gamedata\" tests/test_config.py tests/test_saves.py` green with NO game install and NO MySQL.",
                       "`uv run mypy` clean with the new runtime dependencies — proves the driver\u0027s stubs work under strict mode.",
                       "`uv run pytest -m gamedata --collect-only` collects without a marker error, proving the widened marker parses under `--strict-markers`.",
                       "`uv run pytest -m \"not gamedata\"` still green on all four pre-existing guards (`test_no_leaks`, `test_repo_structure`, `test_agent_contract`, `test_doc_links`).",
                       "`grep -rn \u0027parents\\[\u0027 src/` returns nothing; `grep -rniE \u0027[A-Za-z]:[\\\\/]\u0027 src/` returns nothing."
                   ],
    "commit_note":  "Config layer, save enumerator, first runtime deps, widened gamedata marker. /commit."
}
```
```json
{
    "name":  "Phase 2 — Header reader, sequential cursor, and the fixed-offset guard",
    "goal":  "Land the parsing keystone offline against synthetic fixtures, and encode the fixed-offset ban as a mechanical check rather than a review convention.",
    "steps":  [
                  "Write `src/ootp_ai/parser/cursor.py` — a forward-only cursor exposing `u8`, `u32`, `string` (u32-LE length prefix, raw ASCII, no terminator — `data-access.md:195`), `date` (`u8 day, u8 month, u16 year` — `:196`), `color` (u32 ARGB — `:197`), and `remaining()`. No `seek`. The cursor is what makes byte accounting possible in later phases.",
                  "Write `src/ootp_ai/parser/header.py` using ONLY the cursor: read u8 (must be 0x00), 4 bytes (must be `b\"OOTP\"`), u32 version (must be 25), then the four u32s (11, 104, 84, 1), then the null-padded self-declared filename. Cross-check that filename against the file actually opened (`data-access.md:188`, folded-in #6). This is the design point that lets the AC3 guard run with zero exemptions.",
                  "Write `src/ootp_ai/parser/errors.py` with a named `UnsupportedSaveVersion`. It RAISES on an unrecognized version rather than parsing (`data-engineer.md:83-84` — a loud failure is recoverable, a silent misparse is not).",
                  "MAIN THREAD writes `tests/fixtures/` synthetic byte sequences. They must NOT carry a `.dat` extension. VERIFIED: `git check-ignore -q tests/fixtures/sample.dat` exits 1 — `.gitignore:62` `!tests/fixtures/**` NEGATES `.gitignore:31` `*.dat`, so such a file is committable and the ONLY thing stopping it is `tests/test_no_leaks.py:107` `banned_suffixes`. Use `.bin` or no extension. Every fixture is authored by us, never a slice of a real save (`tests/fixtures/README.md:8-9`).",
                  "MAIN THREAD writes `tests/test_save_header.py` (AC1): a synthetic header with byte 0 = 0x00, `b\"OOTP\"` at offset 1 and u32 25 at offset 5 parses; versions 24 and 26 EACH raise `UnsupportedSaveVersion` by name; a buffer whose `bytes[0:4] == b\"OOTP\"` is REJECTED (the magic-at-offset-0 trap, `data-access.md:183-186`); a header whose self-declared filename disagrees with the file opened is rejected.",
                  "MAIN THREAD writes `tests/test_sequential_walk.py` (AC2): two synthetic records identical except for the length of a variable-length region (a 1-year vs a 10-year contract array) yield IDENTICAL values for every field parsed AFTER that region. A fixed-offset reader cannot pass this.",
                  "MAIN THREAD writes `tests/test_no_fixed_offsets.py` (AC3). Implement it with `ast`, not regex, so a comment or docstring cannot trip it: walk every module under `src/ootp_ai/parser/`, flag any `Call` whose func is an `Attribute` named `seek` with a nonzero integer literal argument, and any `struct.unpack_from` whose third positional argument is a nonzero integer literal. `seek(0)` (rewind) stays legal; `unpack_from(fmt, buf, cursor)` with a NAME argument stays legal — the ban is on literals. Encodes `data-engineer.md:69-72` mechanically."
              ],
    "acceptance":  [
                       "`uv run pytest tests/test_save_header.py tests/test_sequential_walk.py tests/test_no_fixed_offsets.py` green OFFLINE — no game install, no MySQL.",
                       "`uv run pytest -m \"not gamedata\"` green (`test_no_leaks.py::test_game_data_is_not_tracked` proves no fixture carries a banned extension).",
                       "Deliberately introduce `f.seek(128)` into a parser module and confirm `tests/test_no_fixed_offsets.py` goes RED, then remove it — a guard nobody has seen fail is not a guard.",
                       "`uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .` all clean."
                   ],
    "commit_note":  "Sequential cursor, header reader + version guard, mechanical fixed-offset guard. Offline-only. /commit."
}
```
```json
{
    "name":  "Phase 3 — Snapshot step, provenance, and the ADR 0001 read-only proof",
    "goal":  "Copy the in-scope files to an immutable snapshot with a content-hash manifest, read saved_games.dat properly, and PROVE the game was not written to — the one unrecoverable failure in this project.",
    "steps":  [
                  "Write `src/ootp_ai/snapshot.py`: copy ONLY the parsed files to `\u003cOOTP_SNAPSHOT_ROOT\u003e/\u003cleague\u003e/\u003csim_date\u003e/` with a per-file size + SHA-256 manifest, every handle opened `\"rb\"`. In-scope set is ~46 MB (players 32.07 MB + names 8.64 + teams 5.32), NOT the ~600 MB `.lg` — `retired.dat` (154,088,679 B) is out of scope. All later parsing runs against the snapshot, never the live save (`data-engineer.md:60-62`).",
                  "Write `src/ootp_ai/parser/saved_games.py` for `$OOTP_SAVED_GAMES/saved_games.dat`. CRITICAL CORRECTION (scope finding F19, `high` confidence, contradicting `docs/data-access.md:36-38` which labels it `verified` plaintext): it is NOT plaintext. It carries the standard OOTP header and length-prefixed strings, so read it with the SAME header reader plus a string walk — never substring-scrape. It yields each save\u0027s sim date and human team, which is the cheapest cross-check on `snapshot_date` and the provenance pin for Tier B validation.",
                  "Resolve the human team from data on every save rather than hardcoding it (folded-in #7). `OOTP-AI`\u0027s human team is Boston at 2024-03-07; the probe\u0027s is the Chicago Cubs at 2024-03-18. Code that hardcodes \"we are team 6\" or \"perspective 2759 is us\" passes on ground truth and breaks on our league — invisible to the entire validation harness.",
                  "HARD BIND: `saved_games.dat` embeds an ABSOLUTE user-profile path for every save. Nothing that renders its contents may reach a tracked file. The absolute path may live in the warehouse ingest-run row and the generated (ignored) catalog half ONLY.",
                  "MAIN THREAD writes `tests/test_read_only.py` (AC11, `-m gamedata`): take a manifest of mtime + SHA-256 for every file under `$OOTP_SAVED_GAMES` and `$OOTP_INSTALL` before a full parse, take it again after, and assert zero differences. Per SD-20 it runs FIRST against the disposable Challenge Mode probe save and only then against `OOTP-AI.lg`.",
                  "MAIN THREAD writes the parser-determinism half of `tests/test_snapshot_semantics.py` (AC10, `-m gamedata`): parsing the same snapshot twice produces byte-identical parser output.",
                  "Sequence every filesystem-touching test against the disposable probe first (folded-in #9). An identical-mode disposable save sits beside the irreplaceable one; pointing untested code at the managed league first is avoidable exposure."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_read_only.py` green against BOTH the probe and `OOTP-AI.lg`, in that order.",
                       "The snapshot manifest lists exactly three source files with sizes matching the measured values (`teams.dat` 5,318,831 · `players.dat` 32,070,106 · `names.dat` 8,642,110 for `OOTP-AI.lg`).",
                       "`grep -rn \u0027open(\u0027 src/ootp_ai/ | grep -v \"\u0027rb\u0027\" | grep -v \u0027\\\"rb\\\"\u0027` shows no write mode against any path derived from `OOTP_INSTALL` or `OOTP_SAVED_GAMES`.",
                       "`uv run pytest -m \"not gamedata\"` still green; `uv run mypy` / `uv run ruff check .` clean."
                   ],
    "commit_note":  "Snapshot copy + SHA-256 manifest, saved_games.dat reader (header + string walk, not scraped), ADR 0001 read-only proof. /commit."
}
```
```json
{
    "name":  "Phase 4 — teams.dat sequential walk and the team dimension",
    "goal":  "Land the team dimension the standings report needs, on the file with the strongest existing ground truth, and prove the walk with strict byte accounting.",
    "steps":  [
                  "Write `src/ootp_ai/parser/teams.py`: sequential walk yielding `team_id`, the 5-string signature (city, abbreviation, nickname, logo filename, full name — already `verified` at `docs/data-access.md:224-226`), ARGB colors, level, `parent_team_id` (so MLB clubs are distinguishable from affiliates), the sub-league/division hierarchy, and the win-loss fields the standings report needs.",
                  "STRUCTURAL ABSENCE IS A PARSER-LEVEL CONCEPT, and this is where it starts. A field the record does not carry -\u003e `None` -\u003e SQL NULL. A field present holding zero -\u003e `0`. Bronze never converts between them (`data-engineer.md:111-112`). This matters immediately: the export writes `0` for `rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows — 14 separate opportunities to commit this error (scope Core §12).",
                  "MAIN THREAD writes the teams half of `tests/test_byte_accounting.py` (AC12, `-m gamedata`): STRICT form — zero unaccounted bytes for `teams.dat`. If the strict walk cannot reach zero, apply Phase 0\u0027s pre-registered fallback (diagnostic form: record the residual, assert termination on a record boundary) and record the tier rationale rather than opening an unbounded research task on the critical path.",
                  "MAIN THREAD writes the teams half of `tests/test_parse_real_save.py` (AC9, `-m gamedata`) against `OOTP-AI.lg`: exactly 30 teams extract at MLB level with correct abbreviations.",
                  "Note the standings reality up front so nobody misreads a correct parse as a broken one: measured, all 259 `team_record` rows in `ootp_truth_real` are 0-0-0 and 0 of 12,961 games have `played = 1`. Both saves sit before opening day. Standings acceptance is STRUCTURAL, never content — asserting a nonzero win total would fail on a correct parse."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parse_real_save.py -k team` green: exactly 30 MLB-level teams with correct abbreviations from `OOTP-AI.lg`.",
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py -k teams` green at the strict tier, or green at the pre-registered diagnostic tier with the residual recorded and the rationale written down.",
                       "`uv run pytest tests/test_no_fixed_offsets.py` still green — the new walker introduced no literal offsets.",
                       "`uv run pytest -m \"not gamedata\"`, `uv run mypy`, `uv run ruff check .` all clean."
                   ],
    "commit_note":  "teams.dat sequential walk: team dimension, hierarchy, W-L, strict byte accounting. /commit."
}
```
```json
{
    "name":  "Phase 5 — names.dat and the join, validated against two independent answer keys",
    "goal":  "Turn integers into names — the largest single unknown in the request, and the difference between a roster report and a list of IDs. Resolve it against answer keys, never an impression.",
    "steps":  [
                  "Write `src/ootp_ai/parser/names.py`. Structure observed and worth carrying: records read u32 len + ASCII + u32 `0` + u32 monotonic index + three u32s + a `0x27` separator, alphabetically ordered. The table is ~264,095 entries (`data-access.md:234-236`).",
                  "RESOLVE THE KEY SPACE BEFORE WRITING ANY DDL. It is genuinely unknown whether `names.dat` carries ONE index space or TWO (a first-name table and a last-name table, each alphabetically ordered with its own monotonic index starting at 0). If it is two and the DDL keys `bronze_name` on `(snapshot_date, save_id, name_index)`, the two spaces COLLIDE and every collided row is silently wrong. Pre-registered resolution: declare the key as `(snapshot_date, save_id, name_space, name_index)` with `name_space` a NOT NULL discriminator that takes a single literal value if one space is proven. That key is correct under BOTH outcomes and costs one column.",
                  "HARD CONSTRAINT (SD-10, measured): `names.dat` is 8,642,110 bytes in all three saves on disk with THREE DIFFERENT SHA-256 digests — a fixed-size, per-save-populated table. Nothing may carry a name index, an index-\u003estring expectation, or a cached name table from the probe save into the managed league. Enforce this STRUCTURALLY: the resolver\u0027s cache key must include `save_id`, and a test asserts that. A data-level test that \"the same index resolves differently in both saves\" is a smoke test that could coincidentally match — the structural check is the real guard.",
                  "MAIN THREAD writes `tests/test_names_join.py` (AC7, `-m gamedata`) — the Tier B chain: every name index the parser resolves out of the PROBE save\u0027s `players.dat` matches `ootp_truth_real.players.first_name` / `.last_name` by exact string equality, 100% of compared rows, zero unresolved indices, every failure enumerated by name. It SKIPS LOUDLY with a named reason if `ootp_truth_real` is unreachable — it must never pass vacuously.",
                  "COLLATION IS LOAD-BEARING (SD-13, Risk 12). MySQL 8\u0027s default `utf8mb4_0900_ai_ci` is accent- AND case-INSENSITIVE, so a SQL-side comparison would score `Ramirez` = `Ramírez` as equal and pass a broken join. The export was configured with `Replace accents` OFF (`data-access.md:335`), so accented names are present. RESOLUTION: pull both sides into Python and compare decoded `str` with `==`, asserting the driver charset is `utf8mb4`. If a SQL-side comparison is unavoidable, force `COLLATE utf8mb4_bin` explicitly.",
                  "MAIN THREAD writes `tests/test_names_join_boston.py` (AC8, `-m gamedata`) — the Tier A chain, and the ONLY validation of the join on the league we actually manage. For every player in `OOTP-AI.lg/players.dat` carrying a non-empty `historical_id`, the `names.dat`-resolved first and last name equals `players.csv`\u0027s `FirstName` / `LastName` joined on `LahmanID`, 100% exact, every failure enumerated.",
                  "HARD BIND (Decisions §5): never track a Lahman-to-name lookup, in any form. `tests/test_no_leaks.py:106` catches `players.csv` by FILENAME ONLY, so a renamed copy sails straight through the guard into a public repo.",
                  "If the encoding resists, invoke Phase 0\u0027s pre-registered fallback: resolve names from `players.csv` at RENDER time for Lahman-carrying players, into the git-ignored output root, with nothing tracked. Fictional players render as IDs."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_names_join.py` green: 100% exact match against `ootp_truth_real`, zero unresolved indices, and it skips loudly (never silently) when the truth schema is unreachable.",
                       "`uv run pytest -m gamedata tests/test_names_join_boston.py` green against `OOTP-AI.lg` via the `players.csv` LahmanID join.",
                       "A test asserts the name-resolver cache key includes `save_id` — the probe-to-managed-league non-transfer guard, enforced structurally rather than by a data coincidence.",
                       "The `bronze_name` key space (one index space or two) is settled and RECORDED with an epistemic label before any DDL is written.",
                       "`uv run pytest -m \"not gamedata\"`, `uv run mypy`, `uv run ruff check .` all clean."
                   ],
    "commit_note":  "names.dat walk + two-answer-key join validation (probe/export and Boston/players.csv). /commit."
}
```
```json
{
    "name":  "Phase 6 — players.dat walk and roster-list extraction",
    "goal":  "Land the deliberately minimal player field set and the roster-membership grain — the fan-out the request never names and the one that bites today.",
    "steps":  [
                  "Write `src/ootp_ai/parser/players.py`: sequential walk yielding ONLY `player_id`, team/organization assignment, position, uniform number, date of birth, bats/throws, the name indices, and `historical_id`. NO ratings, whatever the Phase 0 spike returned. Every landed field is a field somebody re-validates after a game patch — the field set is a maintenance liability, not a free win (scope Core §7).",
                  "Write `src/ootp_ai/parser/roster.py`: extract at the `team_roster` grain (`team_id`, `player_id`, `list_id`) and empirically derive what each `list_id` VALUE means. Ground truth for the shape: `ootp_truth_real.team_roster` is 15,672 rows over 7,370 DISTINCT players — not 18,072 — with `list_id` in {1: 7370, 2: 7037, 3: 935, 4: 330}.",
                  "If the `list_id` mapping cannot reach `inferred`, apply Phase 0\u0027s fallback: land it as an opaque integer, group the roster report by raw value with a header line stating the meanings are `unconfirmed`, and file a follow-up. The report NEVER prints a human label (`active roster`, `40-man`) for a `list_id` whose mapping is below `inferred` — a wrong label produces a confidently wrong roster with nothing throwing.",
                  "VERIFY, DO NOT ASSUME, THE PLAYERS.DAT POPULATION. The plan assumes `players.dat` holds the active (`retired = 0`) population and `retired.dat` holds the rest — 18,072 active in the probe. That is an INFERENCE from filenames, not a measurement, and AC12\u0027s diagnostic tier depends on it. Confirm it by record count against the export before treating it as fact; if it does not hold, the coverage statements in Phase 9 are wrong.",
                  "MAIN THREAD writes the players half of `tests/test_byte_accounting.py` (AC12, `-m gamedata`): the DIAGNOSTIC tier for `players.dat` — the walk reaches a record count matching the export\u0027s `retired = 0` population AND terminates on a record boundary, with the residual byte count RECORDED in the ingest-run row rather than asserted to be zero. Full byte accounting on `players.dat` is a research task, not a counter, and the tier rationale must say so.",
                  "MAIN THREAD completes `tests/test_parse_real_save.py` (AC9, `-m gamedata`) against `OOTP-AI.lg`: `player_id` unique per snapshot; Boston\u0027s roster rows number \u003e= 26 (NOT == 26 — the club is in spring training at 2024-03-07 and a set 26 probably does not exist yet); ZERO roster rows carry a null or blank display name."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parse_real_save.py` green in full: 30 MLB teams, unique `player_id` per snapshot, Boston roster \u003e= 26 rows, zero null/blank display names.",
                       "`uv run pytest -m gamedata tests/test_byte_accounting.py` green at both tiers (strict for teams/names, diagnostic for players) with the residual recorded.",
                       "The `list_id` value semantics reach at least `inferred` with the evidence written down, OR the opaque-integer fallback is in force and the report carries the `unconfirmed` header line.",
                       "The `players.dat` population claim is measured against the export, not assumed.",
                       "`uv run pytest tests/test_no_fixed_offsets.py` still green; `uv run pytest -m \"not gamedata\"`, `uv run mypy`, `uv run ruff check .` clean."
                   ],
    "commit_note":  "players.dat minimal field set + team_roster membership grain with list_id derivation. /commit."
}
```
```json
{
    "name":  "Phase 7 — Field map, contracts, DDL, and MySQL bronze landing",
    "goal":  "Land bronze into the empty `ootp` schema from ONE tracked declaration with THREE consumers, so grain-prose-vs-grain-enforcement drift becomes structurally impossible.",
    "steps":  [
                  "Write `src/ootp_ai/contracts/field_map.toml` — the first-class tracked artifact. Per field: name, type, the walker that reads it, category (`identity` | `rating-true` | `rating-scouted` | `contract` | `structural`), epistemic label, and the validator tier that produced the label. ADR 0006 §Notes explicitly blesses derived schema knowledge as ours and trackable, and `data-engineer.md:117-120` restates it.",
                  "Write `src/ootp_ai/warehouse/ddl.py` emitting DDL FROM the declaration. Four bronze tables — `bronze_team` (`snapshot_date`, `save_id`, `team_id`), `bronze_player` (`snapshot_date`, `save_id`, `player_id`), `bronze_team_roster` (`snapshot_date`, `save_id`, `team_id`, `player_id`, `list_id`) — explicitly NOT (`snapshot_date`, `player_id`) — and `bronze_name` (`snapshot_date`, `save_id`, `name_space`, `name_index`). EVERY primary-key column is declared NOT NULL: MySQL\u0027s `COUNT(DISTINCT a,b,c)` silently DROPS tuples containing NULL, so a nullable PK column would make the grain test under-count and pass vacuously. Name-bearing tables get `CHARSET=utf8mb4 COLLATE=utf8mb4_bin`.",
                  "Write `src/ootp_ai/warehouse/sql.py` with an `ident()` helper that backticks every identifier and REJECTS a backtick inside a name (folded-in #2). The measured live incident: `select current_date from ootp_truth_real.leagues` returns the wall-clock date for all 15 rows because MySQL parses the column name as the `CURRENT_DATE` function, with nothing erroring. Use `ident()` everywhere, including the export-diff SQL in Phase 8.",
                  "Write `src/ootp_ai/warehouse/load.py`: bronze is 1:1 with parser output — typing, casing, dedup only. NO joins, NO filtering, NO semantic renaming (`data-engineer.md:98`). Land everything the walk yields including the minors; the ORG FILTER lives in the report, not in bronze (Decisions §7).",
                  "Write `src/ootp_ai/warehouse/ingest_run.py`. RESOLVE THE IDEMPOTENCY COLLISION EXPLICITLY: AC10 requires that loading the same snapshot twice leaves row counts and checksums unchanged, but an append-only `ingest_run` would add a row and change the count. Decision: `ingest_run` is keyed (`snapshot_date`, `save_id`) and a re-land of an existing snapshot REFUSES loudly rather than overwriting or appending — which satisfies all four of AC10\u0027s clauses at once and honours \"re-landing an existing `snapshot_id` does not silently overwrite it\". Columns: source file sizes, SHA-256 digests, header versions, sim date, human team, row counts, residual bytes, wall-clock parse seconds (from `time.perf_counter()`, never `datetime` — ruff `DTZ` at `pyproject.toml:57`).",
                  "Write the field-label metadata table (folded-in #5), keyed (`snapshot_date`, `save_id`, `table_name`, `column_name`), so a future incident can ask \"what did we believe about this field the day it was landed?\" as a query rather than archaeology through the git history of `docs/data-access.md`.",
                  "MAIN THREAD writes `tests/test_grain_contracts.py`. AC4 runs OFFLINE: read the tracked declaration and the DDL the loader emits, and assert the prose grain sentence equals the key the DDL emits, and that every PK column is NOT NULL. AC5 runs `-m gamedata`: `test_roster_grain_is_not_player_grain` POSITIVELY asserts `player_id` is NOT unique within one snapshot\u0027s roster rows, and asserts `count(distinct player_id)` in `bronze_team_roster` is materially LESS than `count(*)` in `bronze_player` for the same snapshot.",
                  "MAIN THREAD writes `tests/test_withheld_fields.py` (AC13, OFFLINE), keyed on the declared CATEGORY, not column-name globs. Asserts no field whose category is `rating-true` and no field whose label is `unconfirmed` or `assumed` is renderable; includes a NEGATIVE test asserting a synthetic `rating-scouted` field IS renderable, so the guard cannot be satisfied by blocking everything. For this to run offline with no rating columns landed, make the renderability check a PURE FUNCTION over a declaration so the test can feed it synthetic entries. Name patterns survive only as a secondary check, with `talent_%` corrected to `%_talent_%` (the real columns are `batting_ratings_talent_*`).",
                  "MAIN THREAD writes the `historical_id`-is-never-a-join-key static check (Core §12). SCOPE IT TO `src/ootp_ai/` AND EXCLUDE `tests/` — `tests/test_names_join_boston.py` legitimately joins on LahmanID as ground truth, and an unscoped guard would block its own validation. Measured: 1,920 of 18,072 active players carry a non-empty `historical_id` (10.6%); a join on it silently drops the fictional majority and looks like it worked.",
                  "MAIN THREAD completes `tests/test_snapshot_semantics.py` (AC10, `-m gamedata`): loading the same snapshot twice leaves row counts and checksums unchanged; loading a second `snapshot_date` leaves the first snapshot\u0027s rows bit-identical; re-landing an existing snapshot refuses rather than silently overwriting."
              ],
    "acceptance":  [
                       "`uv run pytest tests/test_grain_contracts.py tests/test_withheld_fields.py` green OFFLINE — no MySQL, no game install (these are the contracts CI actually enforces).",
                       "`uv run pytest -m gamedata tests/test_grain_contracts.py::test_roster_grain_is_not_player_grain` green: `player_id` is provably NOT unique within a snapshot\u0027s roster rows.",
                       "`uv run pytest -m gamedata tests/test_snapshot_semantics.py` green on all four clauses.",
                       "The static check proves no join or condition under `src/ootp_ai/` uses `historical_id`.",
                       "A unit test on `ident()` asserts it emits `` `current_date` `` and raises on an embedded backtick.",
                       "`uv run pytest -m \"not gamedata\"`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .` all clean."
                   ],
    "commit_note":  "Field map declaration + DDL emitter + bronze landing + ingest_run + the five contracts, tested. /commit."
}
```
```json
{
    "name":  "Phase 8 — The parser-vs-export differential harness",
    "goal":  "Prove the parse row-for-row against an independent answer key, per field by name — the only thing that makes the names join and the roster grain provable rather than eyeballed.",
    "steps":  [
                  "MAIN THREAD writes `tests/test_parser_vs_export.py` (AC6, `-m gamedata`). It asserts PROVENANCE FIRST, before any value comparison: the parsed save\u0027s sim date is 2024-03-18 and its human team is the Chicago Cubs, matching `ootp_truth_real` — proving the binaries and the export describe the same universe. A value diff against a different universe is meaningless.",
                  "Then diff: ZERO row-count and ZERO value differences over the landed field set — 259 teams, 18,072 active players (`retired = 0`), 15,672 `team_roster` rows, 15 leagues. Every mismatch listed PER FIELD BY NAME. An aggregate pass rate is not acceptable output (Core §18).",
                  "ADD AN EXPLICIT STRUCTURAL-ABSENCE ALLOWLIST. The export writes `0` where the value is structurally absent — `rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows. Our parser lands NULL there. Without a named per-column allowlist, a CORRECT parse produces 14 false mismatches and someone \"fixes\" the parser to match the export, committing exactly the error `data-engineer.md:111-112` warns about. The allowlist is per-column and each entry carries its reason.",
                  "Use `ident()` from Phase 7 for every identifier in every export-diff query, and leave the regression test behind (folded-in #2).",
                  "Compare strings in Python on decoded `str`, not via SQL comparison, for the collation reason established in Phase 5.",
                  "THE EXPORT IS DISPLAY-SCALE AND BUCKETED and can never be an exact rating validator: measured, `players_batting.batting_ratings_overall_contact` has exactly 12 distinct values, 20-80. That is why `players.csv` stays load-bearing permanently, and why a bucketed check can pass a parser reading the ADJACENT u16 — CLAUDE.md\u0027s named correctness trap in its most dangerous form. It does not bite this slice (no ratings land) but the harness must document it so the next slice does not misuse it."
              ],
    "acceptance":  [
                       "`uv run pytest -m gamedata tests/test_parser_vs_export.py` green: provenance asserted first, then zero row-count and zero value differences over the landed field set.",
                       "A deliberately corrupted single field produces a failure message naming THAT FIELD, not a percentage — verify by temporarily perturbing one value.",
                       "The structural-absence allowlist exists, is per-column, and each entry carries a written reason.",
                       "`uv run pytest -m \"not gamedata\"`, `uv run mypy`, `uv run ruff check .` clean."
                   ],
    "commit_note":  "Parser-vs-export differential harness with provenance pin and per-field mismatch reporting. /commit."
}
```
```json
{
    "name":  "Phase 9 — The two reports, the catalog, and the tracked report channel",
    "goal":  "Turn the GM from mute to functional: a roster report naming real Boston players, a standings report, and a generated catalog that names what was deliberately withheld.",
    "steps":  [
                  "Write `src/ootp_ai/reports/` with a `__main__.py` exposing `render` (AC14 invokes `uv run python -m ootp_ai.reports render`). Roster: the CONFIGURED ORGANIZATION ONLY, grouped by roster list, with position, age, bats/throws and uniform number, and `snapshot_date` + sim date on line one so staleness is visible on sight. Standings: 30 MLB clubs by division with W-L-pct-GB.",
                  "RENDER TO `\u003coutput_root\u003e/\u003csave_id\u003e/\u003csnapshot_date\u003e/roster.md`. Snapshot-partitioning dissolves Risk 10 / SD-21 (regenerating overwrites the prior snapshot\u0027s view and breaks citation integrity for `gm/decisions/` records that cite it) at zero cost, and re-rendering the same snapshot stays idempotent.",
                  "Write `src/ootp_ai/catalog/` with a `__main__.py` (AC15 invokes `uv run python -m ootp_ai.catalog` with no subcommand). Build from `information_schema` PLUS the same tracked declaration the DDL and the uniqueness tests read — one declaration, three consumers. Emit the Markdown and a `catalog.json` sibling from the same generator (folded-in #4).",
                  "SPLIT THE CATALOG per Decisions §3: the STRUCTURAL half (table names, grains, keys, coverage statements, withheld groups, epistemic labels) is tracked — proposed `docs/warehouse-catalog.md` + `.json`; the VOLATILE half (row counts, snapshot dates, freshness) generates into the ignored output root. NOTE: the structural half needs no game data and no MySQL, so its byte-identity clause should run OFFLINE in CI rather than under `-m gamedata` — that strictly increases what CI enforces.",
                  "GENERATE COVERAGE STATEMENTS FROM COUNTS, never hand-written (folded-in #3). The catalog must state how many players carry NO roster row — computed as `count(bronze_player) - count(distinct player_id in bronze_team_roster)` per snapshot, roughly 10,700 of 18,072 active (free agents, draft-eligible, international, unassigned) — so the GM prices \"who is available\" as a KNOWN GAP rather than discovering it by hitting it.",
                  "The WITHHELD section names the true-rating tables, `players.prone_*`, `players_value.*` and every still-`unconfirmed` field, each with its reason and ADR (ADR 0012). No player-level value and no rating column name appears anywhere in the catalog.",
                  "Add the REPORT-PATH POINTER to the tracked half (Core §15, SD-11): each report\u0027s logical name, the `.env` key and relative path it resolves to, and a one-line spawn instruction the umpires read when handing the GM its reports. Write the path as a CODE SPAN, never a Markdown link into `var/` — `tests/test_doc_links.py:15` excludes files under `var/` but not links to it, so a link turns CI red today. Without this pointer, acceptance criterion 20 is unreproducible by anyone who was not in the room.",
                  "MAIN THREAD adds the tracked half of the report channel to `gm/standing-orders.md`: two entries under its `## Reports` format block (`:42-50`), using a NEW engineering-owned report kind added to that format block (Decisions §4) — a pipeline-generated report genuinely has no analyst behind it, and `gm/staff.md` records that no staff exist, so naming an owner would be fiction. Also update the `Status: none active` line at `:10-11`.",
                  "MAIN THREAD extends `tests/test_no_leaks.py` (folded-in #1): assert the report and catalog output roots resolve to a git-ignored path, and add F19\u0027s constraint mechanically — the TRACKED half of the catalog and field map may name source FILES (`players.dat`) but NEVER absolute paths, because `saved_games.dat` embeds an absolute user-profile path for every save and a provenance section that renders it publishes a username to a public repo. Record but do NOT fix the known gap: `tracked_text_files()` (`:31-48`) enumerates via `git ls-files`, so the guard cannot see a new file until it is staged — a leak in an untracked artifact passes locally and fails in CI. That is a follow-up request, not in scope here.",
                  "MAIN THREAD writes `tests/test_reports.py` (AC14, `-m gamedata`): the resolved output root is git-ignored — proven by `git check-ignore -q \u003cpath\u003e` exiting 0 AND `git ls-files` listing no file under it (VERIFIED: `git check-ignore -q var/reports/roster.md` exits 0 today); the roster report contains rows for exactly the configured organization and zero rows belonging to any other; every player row\u0027s name matches `^[A-Za-z][A-Za-z .\u0027-]+$` (a name, not an integer); the standings report contains 30 MLB rows grouped by division with W-L-pct-GB columns present; both files carry `snapshot_date` and sim date on line one. STANDINGS CONTENT IS ASSERTED STRUCTURALLY — asserting a nonzero win total would fail on a CORRECT parse.",
                  "MAIN THREAD writes `tests/test_catalog.py` (AC15) and `tests/test_extraction_cost.py` (AC17, `-m gamedata`). The extraction-cost test asserts only that the wall-clock number EXISTS and is recorded in the ingest-run row and the catalog — there is NO threshold and no pass/fail on duration (Decisions §6: the operator ruled the work takes as long as it needs)."
              ],
    "acceptance":  [
                       "`uv run python -m ootp_ai.reports render` writes both reports, and `uv run pytest -m gamedata tests/test_reports.py` green on all five clauses.",
                       "`uv run python -m ootp_ai.catalog` regenerates, and the structural half is byte-identical to the committed copy — asserted OFFLINE, so CI enforces it. Regenerating twice is byte-identical.",
                       "No player-level value and no rating column name appears anywhere in the catalog; the withheld groups are listed with reason and ADR.",
                       "`uv run pytest -m gamedata tests/test_extraction_cost.py` green: the number exists in both the ingest-run row and the catalog.",
                       "The extended `tests/test_no_leaks.py` proves the output roots are git-ignored and that no absolute path appears in the tracked catalog or field map.",
                       "`gm/standing-orders.md` carries two report entries in its documented format plus the new engineering-owned kind in the format block.",
                       "`uv run pytest -m \"not gamedata\"`, `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .` all clean."
                   ],
    "commit_note":  "Two Markdown reports, the split catalog (tracked structural + generated volatile), report-channel entries in gm/standing-orders.md, extended leak guard. /commit."
}
```
```json
{
    "name":  "Phase 10 — Documentation corrections through /update-docs",
    "goal":  "Correct what is now measurably wrong and upgrade epistemic labels for EXACTLY the fields the validation actually proved — leaving everything else `unconfirmed` and withheld.",
    "steps":  [
                  "ROUTE EVERYTHING HERE THROUGH `/update-docs`, MAIN THREAD ONLY. `docs/data-access.md` is in the data-engineer\u0027s deny set (`data-engineer.md:155`) and `docs/decisions/` at `:156`; the subagent\u0027s findings travel as a `## docs-delta` with proposed labels and the main thread routes them.",
                  "Correct `docs/league-rules.md:129` and `:295` — no `leagues.dat` exists; `OOTP-AI.lg` holds 18 `.dat` files and none is it. Record the measured location of the league configuration block: `major_league_ml_c_2024.lsdl` (exactly the `schedule_file_1` value at `:79-81`) sits at byte 5,559,751 of `world.dat`, surrounded by league-shaped records containing `World Series`, `AL` and `NL`. The same string does not appear anywhere in `teams.dat`.",
                  "Correct `docs/league-rules.md:26` and `:31` — they claim the warehouse supersedes §1 \"the moment the parser lands\", which this slice only PARTIALLY does (the league-config diff is gated, not delivered). Risk 11: these become false on delivery and the doc gate must catch it.",
                  "In `docs/data-access.md`: complete §1\u0027s file table (18 `.dat` files present, several unlisted); DOWNGRADE the `saved_games.dat` plaintext claim at `:36-38` from `verified` (finding F19 — it carries the standard header and length-prefixed strings, and embeds an absolute user-profile path); record the `names.dat` fixed-size-per-save finding with an `inferred` label; record that `ootp_truth_osa` is empty and unnecessary; reclassify the probe save as a RETAINED VALIDATION ASSET rather than disposable (folded-in #8 — every value claim in the validation strategy depends on it staying on disk, and `data-access.md:319-320` plus ADR 0002 currently call it disposable).",
                  "UPGRADE LABELS FOR EXACTLY WHAT TIER A OR TIER B PROVED, and nothing more. Everything else stays `unconfirmed` and withheld — `docs/data-access.md:14` is explicit that an unconfirmed claim is a task, not a fact, and the withheld-fields guard from Phase 7 enforces it mechanically.",
                  "Append the dbt deferral note to `docs/decisions/0004-mysql-warehouse.md` §Notes (`:89-106`): the trigger fired (a warehouse landed) and dbt was NOT pulled, with the reason — ADR 0005\u0027s PATTERN choice is honoured in full and only its TOOLING phrasing is deferred. A superseding ADR is too heavy for a postponement, but quietly diverging is the one option this repo forbids (Decisions §9).",
                  "Update `CLAUDE.md`\u0027s Status section (it currently reads \"Phase 0 — scaffolding … `src/ootp_ai/` is a version string, the `.dat` parser is feature request #1, and the GM therefore has no warehouse and no reports yet\") and `README.md`\u0027s status/next-steps. Update `gm/charter.md:10-15`, whose Status blockquote names \"no warehouse and no reports\" as the blocker.",
                  "Set the Index row in `requests/feature-requests/README.md:119` from `scoped` to `implemented`, and move the slug directory into `_done/` per `:99-105`."
              ],
    "acceptance":  [
                       "`grep -rn \u0027leagues.dat\u0027 docs/` returns nothing except an explicit correction note (AC19).",
                       "`uv run pytest tests/test_doc_links.py` green — every relative link still resolves and no new link points into `var/`.",
                       "`uv run pytest -m \"not gamedata\"` green, including `tests/test_repo_structure.py` (required docs, ADR indexing and cost recording) and `tests/test_agent_contract.py` (AC16).",
                       "Every label upgraded in `docs/data-access.md` names the test that proved it; no label is upgraded without one.",
                       "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean."
                   ],
    "commit_note":  "Doc corrections via /update-docs: leagues.dat removed, labels upgraded where earned, ADR 0004 dbt deferral note, status refresh. /commit."
}
```
```json
{
    "name":  "Phase 11 — USER-RUN acceptance and the umpire ledger act",
    "goal":  "Close the two criteria the acceptance panel must NOT claim, and land the ledger row that becomes precedent for every later report request.",
    "steps":  [
                  "AC20 (USER-RUN): a cold session spawns the `gm` subagent with the roster and catalog reports in its context (via forced-read item 8 at `.claude/agents/gm.md:32`; the agent holds only `Read, Glob` per `:4`). The returned handoff\u0027s `## situation` section must name at least five Boston players by real name, each attributed to the report as its source, with NO roster fact appearing in `## assumed`. This is the request\u0027s observable signal and the single thing that turns the GM from mute to functional.",
                  "AC21 (USER-RUN): the operator confirms `OOTP-AI.lg`\u0027s file set, sizes and modification times are unchanged after a full ingestion run, checked BY HAND against the recorded manifest — an independent check that does not rely on the code that would be the thing violating it. This is deliberately redundant with `tests/test_read_only.py` because ADR 0001 is the one unrecoverable failure in the project.",
                  "THE LEDGER ROW IS AN UMPIRE ACT, NOT A BUILD ARTIFACT (Decisions §2, blocker SD-03). After delivery, the umpires append one row to `gm/ledger.jsonl` recording that the roster report and catalog are FREE INFRASTRUCTURE rather than a commissioned action — with its REASONING, because it becomes an early `seq` every later report request will cite. ADR 0016\u0027s boundary is analytical DIRECTION, not existence; a roster page and the standings are the club\u0027s own furniture. `gm/ledger.jsonl` is append-only and `.gitattributes` marks it `merge=union`.",
                  "`data-engineer.md:130` — anything outward-facing is user-run. The implementation subagent stages these as instructions under `## still-open` and NEVER runs them itself.",
                  "File the two follow-up requests the scope named but excluded: the `tracked_text_files()` staging gap in the leak guard (folded-in #1) and the GM tool-grant guard test (Decisions §11 — `.claude/agents/gm.md` grants exactly `Read, Glob` and nothing in `tests/` asserts it)."
              ],
    "acceptance":  [
                       "USER-RUN: the GM handoff names \u003e= 5 Boston players by real name in `## situation`, each attributed to a report, with no roster fact in `## assumed`.",
                       "USER-RUN: the operator\u0027s by-hand file-set/size/mtime check on `OOTP-AI.lg` shows zero changes.",
                       "One ledger row appended to `gm/ledger.jsonl` carrying the free-infrastructure ruling AND its reasoning, in the documented schema (`gm/README.md:63-79`).",
                       "Two follow-up requests filed under `requests/feature-requests/` (or `bugfix-requests/` for the guard gap) with intake status.",
                       "Final green: `uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`."
                   ],
    "commit_note":  "USER-RUN acceptance recorded, umpire ledger row appended, follow-ups filed. /commit, then the PR is the user\u0027s."
}
```

### testing

THE CI CONDITION IS THE DESIGN CONSTRAINT. `.github/workflows/ci.yml:49` runs `uv run pytest -m "not gamedata"` on a runner with no OOTP install and no MySQL (and `data-engineer.md:91-92` forbids requiring a game install for a test). So the suite splits hard:

OFFLINE (CI-enforced, must never need a save or a database) — criteria 1-5 and 13 and 16: `test_save_header.py` (synthetic header, both bad versions, the magic-at-offset-0 rejection, the filename cross-check), `test_sequential_walk.py` (two synthetic records differing only in a variable-length region — a fixed-offset reader cannot pass it), `test_no_fixed_offsets.py` (an `ast` scan of `src/ootp_ai/parser/`), `test_grain_contracts.py` (prose-vs-DDL), `test_withheld_fields.py` (category-keyed, with a negative case), plus `test_config.py` / `test_saves.py`. RECOMMENDED CHANGE TO THE SCOPE'S MARKING: AC15's "the structural catalog section regenerates byte-identically to the committed copy" needs no game data and no MySQL — it derives from the tracked declaration alone. Move that clause OFF `-m gamedata` so CI enforces it; leave only the row-count clauses marked.

GAMEDATA (local only, run explicitly) — criteria 5-12, 14, 15, 17. The marker at `pyproject.toml:80` widens from "requires a local OOTP install or save" to "…install, save, or warehouse", because `--strict-markers` (`:78`) makes a second marker a hard collection error and the scope chose widening.

FOUR INDEPENDENT VALIDATION CHAINS, none of which substitutes for another:
1. TIER A — `players.csv`, raw ~1-1000 scale, shipped real players only. The ONLY exact rating validator, and (finding F8) the carrier of `FirstName`/`LastName`/`LahmanID`, which makes it a NAME validator for OUR league via `test_names_join_boston.py`. This is the only validation of the names join on the league we actually manage.
2. TIER B — parse the retained probe save and diff row-for-row against its 72-table export (`test_parser_vs_export.py`). EXACT for ids, names, strings, dates, roster lists, team dimension, league config. BUCKETED for ratings and therefore NOT an exact rating validator: measured, `batting_ratings_overall_contact` has exactly 12 distinct values 20-80. A bucketed check can pass a parser reading the ADJACENT u16 — CLAUDE.md's named correctness trap in its most dangerous form.
3. STRUCTURAL — byte accounting, split by file (blocker F3). STRICT zero-residual for `teams.dat` and `names.dat`; DIAGNOSTIC for `players.dat` (record count matches an independent count, walk terminates on a record boundary, residual RECORDED not asserted-zero). This is the cheapest detector for the silent-misparse class and the only check that works on fields with no ground truth.
4. MECHANICAL GUARDS — the fixed-offset scan, the withheld-field guard, the read-only proof, the `historical_id`-is-not-a-join-key scan, the `ident()` quoting regression, the extended leak guard.

TWO PROPERTIES OF THESE TESTS MATTER MORE THAN COVERAGE:
- NO VACUOUS PASSES. `test_names_join.py` must SKIP LOUDLY with a named reason when `ootp_truth_real` is unreachable, never pass silently. Every guard gets deliberately broken once and observed going red before it is trusted — a guard nobody has seen fail is not a guard.
- PER-FIELD, NEVER AGGREGATE, MISMATCH REPORTING in every differential test (Core §18). An aggregate pass rate hides exactly the single-field misparse the harness exists to catch.

REGRESSION SAFETY: the four pre-existing guards (`test_no_leaks.py`, `test_repo_structure.py`, `test_agent_contract.py`, `test_doc_links.py`) stay green through every phase — that is AC16, and the baseline is 18 passed, verified today.

### risks

- THE BRONZE_NAME KEY SPACE IS UNRESOLVED AND IS THIS PLAN'S MOST LIKELY SILENT-WRONGNESS BUG. Nobody has established whether `names.dat` carries ONE monotonic index space or TWO (first-name and last-name tables, each alphabetically ordered with its own index from 0). The scope's Core §8 describes the record structure but never settles the key space. If it is two spaces and the DDL keys on `(snapshot_date, save_id, name_index)`, the tables collide and every collided row is silently wrong — with nothing throwing. MITIGATION: Phase 5 measures it BEFORE any DDL is written, and the declared key carries a NOT NULL `name_space` discriminator that is correct under both outcomes at a cost of one column.
- THE `players.dat` POPULATION IS AN INFERENCE PRESENTED AS FACT. The plan (and AC12's diagnostic tier, and Phase 9's coverage statements) assumes `players.dat` holds exactly the export's `retired = 0` population of 18,072 and that `retired.dat` holds the rest. That follows from the filenames, not from a measurement. If it does not hold, AC12's record-count assertion fails on a CORRECT parse and the catalog's coverage numbers are wrong. MITIGATION: Phase 6 confirms it against the export before treating it as fact.
- THE SCOUTED VIEW MAY BE COMPUTED AT RENDER TIME, NOT STORED (`docs/data-access.md:282` `unconfirmed`). If so, ADRs 0012, 0014 and 0016 have no data path and the front office can read the answer key and nothing else. MITIGATION: the spike runs FIRST with its pivot rule pre-registered, and ratings are decoupled so this entire slice ships whatever the verdict returns.
- `names.dat` CONTENT IS PER-SAVE AND A PROBE-DERIVED INDEX DOES NOT TRANSFER. Measured: identical 8,642,110-byte size across three saves, three different SHA-256 digests. This is a silent-wrong failure, not a crash — a cached name table from the probe would render plausible wrong names into the GM's roster report. MITIGATION: the resolver's cache key includes `save_id`, enforced structurally by a test rather than by a data coincidence.
- CROSS-SCHEMA STRING COMPARISON UNDER MYSQL'S DEFAULT COLLATION SILENTLY PASSES A BROKEN NAMES JOIN. MySQL 8 defaults to `utf8mb4_0900_ai_ci` — accent- AND case-insensitive — and the export was configured with `Replace accents` OFF (`docs/data-access.md:335`), so accented names are present. `Ramirez` would compare equal to `Ramírez`. MITIGATION: compare decoded `str` in Python, or force `COLLATE utf8mb4_bin` explicitly. This is SD-13 and it is easy to not notice.
- THE EXPORT WRITES `0` FOR STRUCTURAL ABSENCE ON 14 NON-MLB LEAGUE ROWS. Without a named per-column allowlist in the diff harness, a CORRECT parse (landing NULL) produces 14 false mismatches — and the tempting fix is to make the parser write 0, committing exactly the error `data-engineer.md:111-112` warns about. Averaging across that boundary produces wrong numbers, not incomplete ones.
- AC10's FOUR CLAUSES COLLIDE WITH AN APPEND-ONLY `ingest_run`. "Loading the same snapshot twice leaves per-table row counts unchanged" is violated by a second ingest-run row, and the wall-clock seconds column breaks bit-identity. RESOLVED by keying `ingest_run` on (`snapshot_date`, `save_id`) and making a re-land REFUSE loudly — which also satisfies the fourth clause. An implementer who does not notice the collision will write a test that cannot pass.
- `tests/` IS IN THE DATA-ENGINEER'S HARD DENY SET (`.claude/agents/data-engineer.md:150`). If the implementation subagent is handed the whole spec, it stops and reports rather than building, and the result is an Escalation and ZERO tests. Every phase above splits `src/ootp_ai/**` (subagent) from `tests/**`, `pyproject.toml`, `.env.example`, `docs/**`, `gm/**` (main thread). `docs/data-access.md` (`:155`) and `docs/decisions/` (`:156`) are denied too — findings travel as `## docs-delta` and route through `/update-docs`.
- THE DOC-LINK GUARD IS BROKEN IN A WAY THIS FEATURE'S OWN ARTIFACTS TRIP. `tests/test_doc_links.py:10-15` applies one regex to every Markdown link with no fence awareness and no `var/` exemption. A tracked Markdown link into the ignored output root — the natural way to write the report-path pointer — turns CI red. A live bugfix request exists (`requests/bugfix-requests/_done/doc-link-guard-mismatch/`). WORK AROUND IT with code spans; do not fix it here.
- THE LEAK GUARD CANNOT SEE AN UNSTAGED FILE. `tests/test_no_leaks.py:31-48` enumerates via `git ls-files`, so a leak in an untracked artifact PASSES LOCALLY and fails in CI. This feature is the first thing in the repo's history that renders OOTP player data to a file, so the exposure is new. Also: `:106` catches `players.csv` by FILENAME ONLY — a renamed copy sails straight through into a public repo, and `tests/fixtures/README.md:26-28` says plainly that catching a renamed real slice is on the implementer.
- `.gitignore`'s `*.dat` RULE DOES NOT PROTECT `tests/fixtures/`. VERIFIED: `git check-ignore -q tests/fixtures/sample.dat` exits 1, because `.gitignore:62` `!tests/fixtures/**` negates `.gitignore:31` `*.dat`. The ONLY thing stopping a committed `.dat` fixture is `tests/test_no_leaks.py:107`. Name fixtures `.bin` or extensionless.
- MYPY RUNS STRICT OVER BOTH `src` AND `tests` (`pyproject.toml:73`) AND NO RUNTIME DEPENDENCY HAS BEEN CHOSEN (`:9` is `dependencies = []`). A driver without usable stubs blocks the entire build at Phase 1. Compounding: `python-dotenv` currently sits in the DEV group only (`:23`) while the config layer needs it at runtime.
- RUFF'S ALREADY-SELECTED RULES BITE A PARSER SPECIFICALLY (`pyproject.toml:52-60`). `A` forbids `id`/`type`/`bytes`/`format` as names — all natural in a binary walker. `DTZ` errors on any naive datetime, so the sim date must be `datetime.date` and timing must use `time.perf_counter()`. `PTH` forbids `os.path`. `N` enforces pep8 naming. These surface as a wall of failures at the first `ruff check` if not anticipated.
- STANDINGS CARRY NO INFORMATION TODAY AND A CONTENT ASSERTION WOULD FAIL ON A CORRECT PARSE. Measured: all 259 `team_record` rows are 0-0-0 and 0 of 12,961 games have `played = 1`; both saves sit before opening day. Assert structure only.
- REGENERATING A REPORT OVERWRITES THE PRIOR SNAPSHOT'S VIEW (SD-21), breaking citation integrity for `gm/decisions/` records that cite it. The scope flagged it for the plan and did not solve it. MITIGATED here at zero cost by snapshot-partitioned output paths.
- NOBODY HAS RUN ANY OF THIS CODE. Every cost estimate in the scope — including the extraction-cost expectation — is `unconfirmed`. That is why AC17 records a number with no threshold rather than asserting one (Decisions §6).

### files_to_touch

```json
{
    "path":  "src/ootp_ai/config.py",
    "change":  "NEW (subagent). Frozen dataclass resolving OOTP_INSTALL, OOTP_SAVED_GAMES, OOTP_LEAGUE, OOTP_SNAPSHOT_ROOT (default var/snapshots, validated local-disk), the two new probe keys and MySQL settings from .env only. Derives and validates save_id against ^[A-Za-z0-9_-]+$. No literal path, no parents[N]."
}
```
```json
{
    "path":  "src/ootp_ai/saves.py",
    "change":  "NEW (subagent). Save enumerator requiring players.dat AND teams.dat before treating a directory as a save; challenge.dat==241-bytes mode pre-flight."
}
```
```json
{
    "path":  "src/ootp_ai/parser/cursor.py",
    "change":  "NEW (subagent). Forward-only cursor: u8/u32/string(u32-LE len + ASCII, no terminator)/date(u8,u8,u16)/color(u32 ARGB)/remaining(). No seek method at all."
}
```
```json
{
    "path":  "src/ootp_ai/parser/header.py",
    "change":  "NEW (subagent). Header read via the cursor ONLY — 0x00, b\"OOTP\", u32 25, four u32s, null-padded self-declared filename cross-checked against the file opened. Uses no offset literals, which is what makes the AC3 guard exemption-free."
}
```
```json
{
    "path":  "src/ootp_ai/parser/errors.py",
    "change":  "NEW (subagent). UnsupportedSaveVersion and the walk-failure hierarchy. Raises rather than parsing an unrecognized version."
}
```
```json
{
    "path":  "src/ootp_ai/parser/teams.py",
    "change":  "NEW (subagent). Sequential teams.dat walk: team_id, 5-string signature, ARGB colors, level, parent_team_id, sub-league/division hierarchy, W-L fields. Structural absence -\u003e None, never 0."
}
```
```json
{
    "path":  "src/ootp_ai/parser/names.py",
    "change":  "NEW (subagent). names.dat walk and the index-\u003estring resolver. Cache key MUST include save_id. Settles the one-vs-two index-space question and records it with an epistemic label."
}
```
```json
{
    "path":  "src/ootp_ai/parser/players.py",
    "change":  "NEW (subagent). Sequential players.dat walk, minimal field set only: player_id, team/org assignment, position, uniform number, DOB, bats/throws, name indices, historical_id. NO ratings."
}
```
```json
{
    "path":  "src/ootp_ai/parser/roster.py",
    "change":  "NEW (subagent). Roster-list extraction at the (team_id, player_id, list_id) grain, plus empirical derivation of list_id value semantics with the pre-registered opaque-integer fallback."
}
```
```json
{
    "path":  "src/ootp_ai/parser/saved_games.py",
    "change":  "NEW (subagent). saved_games.dat read with the SAME header reader plus a string walk — never substring-scraped. Yields sim date and human team per save. Its absolute-path field must never reach a tracked file."
}
```
```json
{
    "path":  "src/ootp_ai/snapshot.py",
    "change":  "NEW (subagent). Copies the ~46MB in-scope set to \u003croot\u003e/\u003cleague\u003e/\u003csim_date\u003e/ with a size + SHA-256 manifest, all handles \u0027rb\u0027. Snapshots are immutable."
}
```
```json
{
    "path":  "src/ootp_ai/contracts/field_map.toml",
    "change":  "NEW (subagent — the one non-src artifact the spec declares). Per field: name, type, walker, category (identity|rating-true|rating-scouted|contract|structural), epistemic label, validator tier. ONE declaration, THREE consumers (DDL, grain tests, catalog)."
}
```
```json
{
    "path":  "src/ootp_ai/contracts/__init__.py",
    "change":  "NEW (subagent). tomllib reader resolving field_map.toml via importlib.resources, plus the pure `is_renderable(field)` predicate the offline withheld-fields test feeds synthetic entries to."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/ddl.py",
    "change":  "NEW (subagent). Emits DDL from the declaration. Every PK column NOT NULL (MySQL COUNT(DISTINCT ...) drops NULL tuples and would make the grain test pass vacuously). Name-bearing tables CHARSET=utf8mb4 COLLATE=utf8mb4_bin."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/sql.py",
    "change":  "NEW (subagent). ident() backticks every identifier and rejects an embedded backtick. Fixes the measured `select current_date from ootp_truth_real.leagues` class of incident."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/load.py",
    "change":  "NEW (subagent). Bronze landing 1:1 with parser output — typing/casing/dedup only. Lands everything the walk yields; the org filter lives in the report."
}
```
```json
{
    "path":  "src/ootp_ai/warehouse/ingest_run.py",
    "change":  "NEW (subagent). ingest_run keyed (snapshot_date, save_id), re-land REFUSES loudly. Records file sizes, SHA-256 digests, header versions, sim date, human team, row counts, residual bytes, perf_counter seconds. Plus the per-field epistemic-label metadata table."
}
```
```json
{
    "path":  "src/ootp_ai/reports/__main__.py",
    "change":  "NEW (subagent). Exposes `render` (AC14 calls `python -m ootp_ai.reports render`). Writes to \u003coutput_root\u003e/\u003csave_id\u003e/\u003csnapshot_date\u003e/ — snapshot-partitioned, which dissolves SD-21."
}
```
```json
{
    "path":  "src/ootp_ai/reports/roster.py",
    "change":  "NEW (subagent). Configured organization only, grouped by roster list, position/age/bats-throws/uniform number, snapshot_date + sim date on line one. Never prints a human label for a list_id below `inferred`."
}
```
```json
{
    "path":  "src/ootp_ai/reports/standings.py",
    "change":  "NEW (subagent). 30 MLB clubs by division, W-L-pct-GB. Content is structurally asserted only — every club is 0-0 today."
}
```
```json
{
    "path":  "src/ootp_ai/catalog/__main__.py",
    "change":  "NEW (subagent). AC15 calls `python -m ootp_ai.catalog` with no subcommand. Emits both halves and the catalog.json sibling."
}
```
```json
{
    "path":  "src/ootp_ai/catalog/generate.py",
    "change":  "NEW (subagent). Built from information_schema PLUS the tracked declaration. Coverage statements GENERATED from counts (including how many players carry no roster row). Withheld section with reason + ADR. Tracked half carries no absolute path and no rating column name."
}
```
```json
{
    "path":  "pyproject.toml",
    "change":  "MODIFY (main thread). `:9` add PyMySQL + python-dotenv to [project].dependencies; `:23` move python-dotenv out of dev-only and add types-PyMySQL to dev; `:80` widen the gamedata marker to \"requires a local OOTP install, save, or warehouse\" — do NOT add a second marker under --strict-markers."
}
```
```json
{
    "path":  ".env.example",
    "change":  "MODIFY (main thread). Add the probe-save-directory and Challenge-Mode-probe-save keys; mark MYSQL_TRUTH_OSA_DATABASE (`:58`) retired with its reason. All values stay empty — test_no_leaks.py:25 flags a drive letter."
}
```
```json
{
    "path":  "tests/test_save_header.py",
    "change":  "NEW (MAIN THREAD ONLY — tests/ is in the subagent deny set). AC1, offline."
}
```
```json
{
    "path":  "tests/test_sequential_walk.py",
    "change":  "NEW (main thread). AC2, offline — two synthetic records differing only in a variable-length region."
}
```
```json
{
    "path":  "tests/test_no_fixed_offsets.py",
    "change":  "NEW (main thread). AC3 — ast-based scan of src/ootp_ai/parser/. Bans nonzero literal seek() and literal-offset unpack_from; allows seek(0) and NAME offsets."
}
```
```json
{
    "path":  "tests/test_grain_contracts.py",
    "change":  "NEW (main thread). AC4 offline (prose == DDL key, every PK column NOT NULL) + AC5 gamedata (test_roster_grain_is_not_player_grain: player_id NOT unique within a snapshot)."
}
```
```json
{
    "path":  "tests/test_withheld_fields.py",
    "change":  "NEW (main thread). AC13 offline, category-keyed with a negative rating-scouted case. Secondary name check uses %_talent_% (the real columns are batting_ratings_talent_*)."
}
```
```json
{
    "path":  "tests/test_read_only.py",
    "change":  "NEW (main thread). AC11 gamedata — mtime + SHA-256 manifest before and after a full parse, probe FIRST then OOTP-AI.lg (SD-20)."
}
```
```json
{
    "path":  "tests/test_snapshot_semantics.py",
    "change":  "NEW (main thread). AC10 gamedata — idempotent re-load, prior snapshot bit-identical, byte-identical parser output, refuse-on-existing-snapshot."
}
```
```json
{
    "path":  "tests/test_byte_accounting.py",
    "change":  "NEW (main thread). AC12 gamedata — strict zero-residual for teams.dat/names.dat, diagnostic tier for players.dat with the residual recorded and the tier rationale written."
}
```
```json
{
    "path":  "tests/test_names_join.py",
    "change":  "NEW (main thread). AC7 gamedata — probe vs ootp_truth_real, 100% exact, zero unresolved, skips LOUDLY with a named reason. Comparison in Python on decoded str; collation declared."
}
```
```json
{
    "path":  "tests/test_names_join_boston.py",
    "change":  "NEW (main thread). AC8 gamedata — OOTP-AI.lg vs players.csv FirstName/LastName on LahmanID. The only validation of the join on the league we manage. Never track the lookup."
}
```
```json
{
    "path":  "tests/test_parse_real_save.py",
    "change":  "NEW (main thread). AC9 gamedata — 30 MLB teams, unique player_id, Boston roster \u003e= 26 (not == 26), zero null/blank display names."
}
```
```json
{
    "path":  "tests/test_parser_vs_export.py",
    "change":  "NEW (main thread). AC6 gamedata — provenance asserted FIRST (sim date 2024-03-18, human team Chicago Cubs), then zero row-count and zero value diffs, per-field mismatch naming, explicit structural-absence allowlist."
}
```
```json
{
    "path":  "tests/test_reports.py",
    "change":  "NEW (main thread). AC14 gamedata — output root git-ignored (git check-ignore -q exits 0 AND git ls-files empty), org-exclusive rows, name regex, 30 standings rows, snapshot_date + sim date on line one."
}
```
```json
{
    "path":  "tests/test_catalog.py",
    "change":  "NEW (main thread). AC15 — structural byte-identity clause OFFLINE (recommended de-marking so CI enforces it); row-count/freshness clauses gamedata. Asserts no rating column name and no player-level value appears anywhere."
}
```
```json
{
    "path":  "tests/test_extraction_cost.py",
    "change":  "NEW (main thread). AC17 gamedata — asserts the wall-clock number EXISTS in the ingest-run row and the catalog. No threshold (Decisions §6)."
}
```
```json
{
    "path":  "tests/test_config.py",
    "change":  "NEW (main thread). Offline — monkeypatched env, snapshot-root default, save_id regex validation."
}
```
```json
{
    "path":  "tests/test_saves.py",
    "change":  "NEW (main thread). Offline — a fake save tree under tmp_path including the stray empty `.lg` directory the enumerator must reject."
}
```
```json
{
    "path":  "tests/test_no_leaks.py",
    "change":  "MODIFY (main thread). Folded-in #1 — assert the report and catalog output roots resolve to a git-ignored path, and that the TRACKED catalog/field map name source FILES but never absolute paths. Record (do not fix) the git ls-files staging gap."
}
```
```json
{
    "path":  "tests/fixtures/",
    "change":  "NEW files (main thread). Synthetic byte sequences only, authored by us, never a slice of a real save. NOT named *.dat — verified that .gitignore:62 negates .gitignore:31 there, so only test_no_leaks.py:107 stops it."
}
```
```json
{
    "path":  "docs/warehouse-catalog.md",
    "change":  "NEW, TRACKED, GENERATED (main thread, via /update-docs). The structural half: table names, grains, keys, coverage statements, withheld groups, epistemic labels, plus the report-path pointer written as CODE SPANS (never a Markdown link into var/, which turns test_doc_links.py red)."
}
```
```json
{
    "path":  "docs/league-rules.md",
    "change":  "MODIFY via /update-docs (main thread). `:129` and `:295` — remove the leagues.dat assertion, record the measured world.dat location (byte 5,559,751). `:26` and `:31` — they become false on delivery (§1 is only partially superseded; the league-config diff is gated)."
}
```
```json
{
    "path":  "docs/data-access.md",
    "change":  "MODIFY via /update-docs ONLY — it is in the subagent deny set (data-engineer.md:155). Complete §1\u0027s file table (18 .dat files); downgrade the saved_games.dat plaintext claim at :36-38; add names.dat fixed-size-per-save as `inferred`; record ootp_truth_osa as empty/unnecessary; reclassify the probe as a RETAINED validation asset; upgrade labels for exactly what Tier A/B proved and nothing more."
}
```
```json
{
    "path":  "docs/decisions/0004-mysql-warehouse.md",
    "change":  "MODIFY via /update-docs (main thread; docs/decisions/ is denied to the subagent). Append the dbt deferral note to §Notes (`:89-106`): the trigger fired, dbt was not pulled, ADR 0005\u0027s pattern choice is honoured in full and only its tooling phrasing defers."
}
```
```json
{
    "path":  "gm/standing-orders.md",
    "change":  "MODIFY (main thread / umpire act). Two report entries under `## Reports` (`:42-50`), a NEW engineering-owned report kind added to the format block (Decisions §4 — no analyst exists, so naming an owner would be fiction), and the `Status: none active` line at `:10-11` updated."
}
```
```json
{
    "path":  "gm/ledger.jsonl",
    "change":  "APPEND (umpire act, USER-RUN, post-delivery — blocker SD-03). One row recording the roster report and catalog as FREE INFRASTRUCTURE with its reasoning, since it becomes the precedent every later report request cites. Append-only; .gitattributes marks it merge=union."
}
```
```json
{
    "path":  "requests/feature-requests/first-sight/SPIKE_SCOUTED_VIEW.md",
    "change":  "NEW (main thread, Phase 0). Kill/pivot rule written ABOVE the verdict, the stored-or-computed answer with byte evidence and an epistemic label, plus the three pre-registered fallbacks (list_id, teams.dat byte accounting, names.dat)."
}
```
```json
{
    "path":  "requests/feature-requests/README.md",
    "change":  "MODIFY (main thread). Index row `:119` advances scoped -\u003e plan -\u003e implemented; the slug moves once into `_done/` per `:99-105`."
}
```
```json
{
    "path":  "CLAUDE.md",
    "change":  "MODIFY via /update-docs (main thread; CLAUDE.md is in the subagent deny set). The Status section still says src/ootp_ai/ is a version string and the GM has no warehouse and no reports — both false on delivery."
}
```
```json
{
    "path":  "README.md",
    "change":  "MODIFY via /update-docs (main thread). Status, next steps, and setup (new .env keys, MySQL driver, how to run the ingest and render the reports)."
}
```
```json
{
    "path":  "gm/charter.md",
    "change":  "MODIFY (main thread). `:10-15` names \"no warehouse and no reports\" as the blocker for writing the charter; that blocker is now partially lifted."
}
```

### code_references

```json
{
    "ref":  "src/ootp_ai/__init__.py:7",
    "claim":  "The entire package today is `__version__ = \"0.1.0\"` plus a docstring reading \"Phase 0. No pipeline code yet\" — 241 bytes. Every module in this plan is created from nothing; there is no existing code to reuse."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:69-72",
    "claim":  "The fixed-offset ban, stated as a blocker rather than a style note, with the evidence: the same player\u0027s ratings block sat 43 bytes from one anchor in one save and 107 in another. AC3 encodes this as a mechanical ast scan."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:91-92",
    "claim":  "\"Never require a game install to satisfy a test.\" This is why criteria 1-5, 13 and 16 must run offline against synthetic fixtures, and why the `gamedata` marker exists as the explicit exception."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:98",
    "claim":  "Bronze is 1:1 with parser output — typing, casing, dedup; no joins, no filtering, no semantic renaming. This is why the Boston org filter lives in the report and not in the landing step (scope Decisions §7)."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:101-104",
    "claim":  "Grain must be declared in prose AND enforced with a uniqueness test, and the two must agree. AC4 tests exactly that agreement between the tracked declaration and the emitted DDL."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:111-112",
    "claim":  "\"Structural absence is not missing data.\" The basis for the parser-level rule that a field absent from a record becomes None/NULL while a present zero stays 0, and for the export-diff allowlist covering the 14 non-MLB league rows the export writes 0 into."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:150-157",
    "claim":  "The hard deny set: tests/, .github/, ops/, .claude/, CLAUDE.md, docs/data-access.md, docs/decisions/. Combined with :164-166 (\"stop and report it — do not build it\"), this forces the plan\u0027s subagent/main-thread split; handing the whole spec over yields an Escalation and zero tests."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:130",
    "claim":  "\"Anything outward-facing is user-run. Stage it as a script and report it under still-open. Never run it yourself.\" Governs AC20, AC21 and the ledger append in Phase 11."
}
```
```json
{
    "ref":  ".claude/agents/data-engineer.md:238-249",
    "claim":  "The Routing rule: data facts never go in agent memory; they travel as `## docs-delta` with a proposed epistemic label and the main thread routes them through /update-docs. This is the mechanism Phase 10 depends on."
}
```
```json
{
    "ref":  "docs/data-access.md:173-186",
    "claim":  "The header layout byte-for-byte (0x00, \"OOTP\" at offset 1, u32 25 at offset 5, then 11/104/84/1, then the null-padded filename) and the explicit warning that a reader checking data[0:4] rejects every valid save. AC1 tests both directions."
}
```
```json
{
    "ref":  "docs/data-access.md:188",
    "claim":  "\"the header names its own file\" — the cheap cross-check that the file on disk is the file we think we opened. Folded-in #6 promotes this to a pre-flight on every run."
}
```
```json
{
    "ref":  "docs/data-access.md:60-63",
    "claim":  "A `*.lg` glob is not a list of saves — the saved-games directory contains a stray empty directory literally named `.lg`. The enumerator must confirm players.dat and teams.dat exist."
}
```
```json
{
    "ref":  "docs/data-access.md:65-68",
    "claim":  "challenge.dat is present at exactly 241 bytes in a Challenge Mode save and absent otherwise — a filesystem-level mode check with no menu, promoted to a pre-flight by folded-in #6."
}
```
```json
{
    "ref":  "docs/data-access.md:224-226",
    "claim":  "The teams.dat 5-string signature (city, abbreviation, nickname, logo filename, full name) followed by u32 ARGB colors is already labelled `verified`, with all 30 MLB clubs extracting cleanly. This is the strongest existing ground truth and why teams.dat is the first walk."
}
```
```json
{
    "ref":  "docs/data-access.md:234-238",
    "claim":  "Names are indirected into a ~264,095-entry names.dat table, and the index encoding plus table layout are `unconfirmed` — the largest single unknown in the request, and the reason Phase 5 stands alone with a pre-registered fallback."
}
```
```json
{
    "ref":  "docs/data-access.md:280-295",
    "claim":  "The critical-path question (is the scouted view stored at all) and the exact spike test at :292-295 — export real and scouted together, then search scouting.dat for the exported scouted values. Phase 0 runs precisely this."
}
```
```json
{
    "ref":  "docs/data-access.md:335",
    "claim":  "The export was configured with `Replace accents` OFF because it \"mangles names and breaks validation against names.dat\". Accented names are therefore present, which is what makes MySQL\u0027s default accent-insensitive collation a silent-pass hazard for the names join."
}
```
```json
{
    "ref":  "docs/data-access.md:14",
    "claim":  "\"An unconfirmed claim is a task, not a fact.\" The obligation behind AC13\u0027s rule that any field labelled `unconfirmed` or `assumed` is non-renderable, enforced by category rather than by name globs."
}
```
```json
{
    "ref":  "pyproject.toml:9",
    "claim":  "`dependencies = []` — no runtime dependency has been chosen. Phase 1 must pick a MySQL driver and promote python-dotenv from the dev group before any code can even import cleanly."
}
```
```json
{
    "ref":  "pyproject.toml:23",
    "claim":  "python-dotenv sits in the DEV dependency group only. The config layer needs it at runtime, so leaving it there means the installed package cannot read .env."
}
```
```json
{
    "ref":  "pyproject.toml:73",
    "claim":  "`files = [\"src\", \"tests\"]` under `strict = true` — mypy runs strict over the tests too, which is why the driver\u0027s type stubs are a Phase 1 blocker rather than a nicety (Risk SD-14)."
}
```
```json
{
    "ref":  "pyproject.toml:78-81",
    "claim":  "`addopts = \"-q --strict-markers --strict-config\"` and exactly one declared marker, `gamedata: requires a local OOTP install or save`. An undeclared marker is a hard collection error, which is why the scope widens this description rather than adding a second marker."
}
```
```json
{
    "ref":  "pyproject.toml:52-60",
    "claim":  "ruff already selects A (builtin shadowing), DTZ (naive datetimes), PTH (pathlib) and N (naming). These bite a binary parser specifically: no `id`/`type`/`bytes` names, `datetime.date` for the sim date, `time.perf_counter()` for the extraction-cost timing."
}
```
```json
{
    "ref":  "tests/test_no_leaks.py:97-116",
    "claim":  "test_game_data_is_not_tracked bans four filenames and two suffixes (.dat, .lg) among tracked files. It is the only guard preventing a committed .dat fixture, and :106 catches players.csv by filename ONLY — a renamed copy passes."
}
```
```json
{
    "ref":  "tests/test_no_leaks.py:31-48",
    "claim":  "tracked_text_files() enumerates via `git ls-files`, so the guard cannot see an unstaged file. A leak in an untracked rendered report passes locally and fails in CI — recorded by folded-in #1 as a follow-up, not fixed here."
}
```
```json
{
    "ref":  ".gitignore:31",
    "claim":  "`*.dat` is gitignored — but VERIFIED by `git check-ignore -q tests/fixtures/sample.dat`, which exits 1 (NOT ignored) because .gitignore:62\u0027s `!tests/fixtures/**` negation comes later and wins. Fixtures must avoid the .dat extension by discipline, not by the ignore file."
}
```
```json
{
    "ref":  ".gitignore:18",
    "claim":  "`var/` is gitignored. VERIFIED by `git check-ignore -q var/reports/roster.md`, which exits 0 — so AC14\u0027s git-check-ignore proof works as written against the var/ output root."
}
```
```json
{
    "ref":  ".gitignore:61",
    "claim":  "`!datasets/**` is already present as a carve-out for a directory that does not exist. The scope\u0027s Non-Goals forbid creating datasets/ or a manifest entry here, so leave this rule untouched."
}
```
```json
{
    "ref":  "tests/test_doc_links.py:10-15",
    "claim":  "One regex over every Markdown link, skipping only http/mailto/#/angle-brackets, and markdown_files() excludes files UNDER var/ but not links TO var/. Confirms the live defect: the report-path pointer must use code spans, not links."
}
```
```json
{
    "ref":  ".github/workflows/ci.yml:38-49",
    "claim":  "The four gates each phase must pass locally before /commit: `ruff check .`, `ruff format --check .`, `mypy`, and `pytest -m \"not gamedata\"`. CI has no game install and no MySQL by design (ADR 0006)."
}
```
```json
{
    "ref":  "gm/standing-orders.md:42-50",
    "claim":  "The `## Reports` format block a standing order must match: Established (ledger seq + sim date), Owner, Policy, Rationale, Review trigger. Decisions §4 requires a new engineering-owned kind added here because no staff exist to name as owner."
}
```
```json
{
    "ref":  "gm/README.md:17-19",
    "claim":  "The placement rule — \"Can this be rebuilt from the save? Yes -\u003e var/. No -\u003e here.\" The rendered reports rebuild from the save (var/); the DECISION that the report exists does not (tracked)."
}
```
```json
{
    "ref":  "gm/README.md:63-79",
    "claim":  "The ledger.jsonl row schema (seq, sim_date, period, what, staff, proposed, reasoning, precedent, ruling, overridden, overturns) that the Phase 11 umpire append must match."
}
```
```json
{
    "ref":  ".claude/agents/gm.md:4",
    "claim":  "`tools: Read, Glob` — the entire delivery surface for this feature. The GM cannot query the warehouse, so a Markdown file it can Read is the only channel that works."
}
```
```json
{
    "ref":  ".claude/agents/gm.md:32",
    "claim":  "Forced-read item 8, \"Any report or analysis handed to you for this invocation\" — the hook the roster and catalog reports enter through, and what AC20 exercises."
}
```
```json
{
    "ref":  "docs/league-rules.md:129-130",
    "claim":  "\"The parser reads `leagues.dat` directly and may recover some of these\" — false; OOTP-AI.lg holds 18 .dat files and none is leagues.dat. AC19\u0027s first correction target."
}
```
```json
{
    "ref":  "docs/league-rules.md:295-296",
    "claim":  "\"Until the parser can open `leagues.dat`, every value here is believed rather than confirmed\" — AC19\u0027s second correction target. The league config block is measured at byte 5,559,751 of world.dat instead."
}
```
```json
{
    "ref":  "docs/league-rules.md:26",
    "claim":  "§1 is described as superseded by the warehouse \"the moment the parser lands\". This slice lands the parser but gates the league-config diff, so the sentence becomes false on delivery — Risk 11, and the doc gate must catch it."
}
```
```json
{
    "ref":  "docs/league-rules.md:79-81",
    "claim":  "Records `schedule_file_1 = major_league_ml_c_2024.lsdl` — the exact string the scope located at byte 5,559,751 of world.dat, which is the citation Phase 10\u0027s correction rests on."
}
```
```json
{
    "ref":  "docs/decisions/0004-mysql-warehouse.md:89-106",
    "claim":  "\"This is not yet resolved and does not need to be… The decision comes due when the first dbt model is requested,\" with four live options and options 3/4 called likely correct. Decisions §9 requires the deferral recorded as a note here rather than a superseding ADR."
}
```
```json
{
    "ref":  "docs/decisions/0005-hybrid-data-layer.md:64-71",
    "claim":  "The boundary rule verbatim — does this artifact change when the league is simulated? No -\u003e builder + datasets/. Yes -\u003e parser + dbt — and the worked example that players.csv resolves as static reference. This is what keeps this feature entirely off the datasets/ side."
}
```
```json
{
    "ref":  "tests/test_repo_structure.py:12-24",
    "claim":  "The required-docs list every phase must keep satisfied, and the shape any new tracked doc joins. Together with :64-67 (var/ must stay gitignored) and :94-103 (the GM contract files), it is part of AC16\u0027s regression set."
}
```
```json
{
    "ref":  "tests/test_agent_contract.py:46-66",
    "claim":  "test_rulebook_invariants_survive asserts the data-engineer definition still states each invariant by keyword — read-only, fixed offset, players.csv, unconfirmed, version, immutable, grain, no OOTP game data in git. Nothing in this plan may weaken that file."
}
```
```json
{
    "ref":  "tests/fixtures/README.md:8-9",
    "claim":  "\"A fixture may contain our own derived observations. It may never contain OOTP\u0027s shipped data.\" With :26-28 stating plainly that the leak guard cannot catch a renamed real slice — that one is on the implementer."
}
```
```json
{
    "ref":  "requests/feature-requests/README.md:70-85",
    "claim":  "What \"testable\" means here — a cold agent runs one command and gets pass or fail — and the rule that human-only criteria must be marked USER-RUN so the acceptance panel does not claim them. AC20 and AC21 are the two."
}
```
```json
{
    "ref":  "requests/feature-requests/README.md:119",
    "claim":  "The Index row for first-sight, currently at stage `scoped`. It advances to `plan` when the plan lands and to `implemented` when the slug moves into _done/ per :99-105."
}
```
```json
{
    "ref":  "requests/bugfix-requests/_done/doc-link-guard-mismatch/BUGFIX_REQUEST.md:20-25",
    "claim":  "The reproduction showing test_doc_links.py flagging a fenced link, a file.py:123 citation, and a var/ target as broken. Confirms the plan\u0027s artifacts must use code spans and must not link into the output root."
}
```

### open_questions

- MySQL driver: PyMySQL + types-PyMySQL (my recommendation — pure Python so no Windows build toolchain, MIT like this repo, and maintained stubs for mypy strict over src AND tests) versus mysql-connector-python (Oracle GPLv2-with-FOSS-exception, ships partial typing) versus mysqlclient (C extension, fastest, no maintained stubs). The licensing and stub story point the same way, but the operator may have a standing preference from another project.
- Where does the TRACKED structural catalog live? I propose `docs/warehouse-catalog.md` + `.json`. It is derived schema knowledge (ADR 0006 §Notes blesses tracking it) and it is NOT rebuildable from the save — it rebuilds from the tracked field-map declaration — so gm/README.md:19's placement rule puts it outside var/. But docs/ placement pulls it into /update-docs's audit surface, which may be exactly right or may be noise. Alternatives: `src/ootp_ai/contracts/catalog.md` next to the declaration, or repo root.
- Should AC15's structural-byte-identity clause be de-marked from `gamedata`? It derives from the tracked declaration alone — no game data, no MySQL — so CI could enforce it on every PR. I recommend splitting AC15 into an offline half and a gamedata half. This is a strengthening of the scope's acceptance, not a weakening, but it changes what the acceptance panel checks.
- Does `names.dat` carry ONE index space or TWO (separate first-name and last-name tables)? Unresolved anywhere in the scope, and it decides `bronze_name`'s primary key. The plan pre-registers a `name_space` discriminator column that is correct under both outcomes, but the operator should know a one-column key was deliberately not chosen.
- Is `players.dat`'s population exactly the export's `retired = 0` set (18,072 in the probe)? Assumed from filenames, never measured. AC12's diagnostic tier and the catalog's coverage statements both rest on it.
- Where does the tracked field map live — `src/ootp_ai/contracts/field_map.toml` (packaged, resolves via importlib.resources, no path walk) or a repo-root location? I recommend packaged. TOML over JSON/YAML because tomllib is stdlib in 3.12, nothing writes the file, and the per-field epistemic rationale wants comments.
- Should the Phase 0 spike script be tracked for reproducibility? I recommend NOT tracking it — it is a one-off, `ops/` is repo governance rather than research, and CLAUDE.md forbids creating directories speculatively. The verdict document carries the method and byte evidence instead. The tradeoff is that re-running it later means rewriting it.
- `bronze_name` re-lands ~264,095 rows per save per snapshot even though names.dat is fixed-size and probably immutable for a save's lifetime. The scope decided snapshot_date goes in EVERY primary key (Goal 5), so this plan honours that and records the per-snapshot digest in ingest_run so a later slice can prove immutability and de-snapshot it cheaply. Flagging the storage number rather than re-litigating the decision.

