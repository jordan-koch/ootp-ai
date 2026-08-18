> **Status:** planned · created 2026-08-16 · decided · next: implement

# Implementation Plan — First sight: land the club and tell the GM what else exists

> **One-line goal:** the GM can name its own 26-man roster with real names, and read a
> catalog telling it what else has been landed and what was deliberately withheld ·
> **Target component:** `src/ootp_ai/` (created from nothing), the `ootp` MySQL schema
> (exists, 0 tables), and the git-ignored report/catalog output root.

> **Citation convention — load-bearing, not style.** Every `file:line` citation in this
> document is a **code span, never a Markdown link**, and nothing links into `var/`.
> `tests/test_doc_links.py` resolves every relative link target in every tracked `.md`
> with no fence awareness and no `var/` exemption, so either shape turns CI red **today**.
> An open bugfix request exists (`requests/bugfix-requests/_done/doc-link-guard-mismatch/`) —
> work around it here, do not fix it. `PROJECT_SCOPE.md` adopts the same convention.
>
> **Never write an absolute path into this or any tracked file.** Finding F01 caught the
> panel's own draft doing it: 11 of 15 onboarding entries carried drive-letter paths, and
> the adversary imported the real `PATTERNS` list from `tests/test_no_leaks.py` and
> confirmed they match. The plan would have failed its own acceptance criterion 16.

## 1. Onboarding — read these first

The GM subagent exists, holds exactly `Read` and `Glob`, and can decide nothing about the
baseball club it runs. It can read its charter, the owner's goals and the league rules —
and not one fact about a single player on its roster. Everything it needs is sitting in
`OOTP-AI.lg`, and no line of code in this repo reads a byte of it.

This slice closes that. It is **not** a horizontal layer: it goes save → parser →
warehouse → report, and stops at the first thing the GM can actually act on.

**Read in this order. All paths are repo-relative.**

| # | File | Why |
|---|---|---|
| 1 | `requests/feature-requests/first-sight/PROJECT_SCOPE.md` | The decided upstream artifact. 21 acceptance criteria, 21 Core items, 9 folded-in wins, 11 disposed Decisions. **This plan implements it; it does not re-open it.** |
| 2 | `requests/feature-requests/first-sight/FEATURE_REQUEST.md` | The problem in the operator's words, and the five open data contracts the scope settled |
| 3 | `.claude/agents/data-engineer.md` | **The single owner of the build rules.** `:55-58` read-only consequence · `:69-74` the fixed-offset ban with measured evidence · `:88-90` no literal paths · `:91-92` never require a game install for a test · `:98-100` bronze is 1:1 · `:101-104` grain in prose *and* enforced · `:107-109` the two player keys · `:110-112` structural absence · `:117-120` derived knowledge is ours · `:129-130` outward-facing is user-run · `:150-156` the deny set · `:164-166` stop and report |
| 4 | `docs/data-access.md` | **Read the epistemic labels, not just the claims.** §4 the byte format · §5 the ratings trap · `:14` what `unconfirmed` obligates · `:60-63` a `*.lg` glob is not a list of saves · `:99-102` `historical_id` is `verified` · `:172-189` the header, magic at offset **1** · `:224-226` the teams 5-string signature · `:228` everything else is `unconfirmed` · `:234-238` names are indirected, encoding `unconfirmed` |
| 5 | `pyproject.toml` | `:9` `dependencies = []` · `:23` `python-dotenv` is dev-only · `:52-58` ruff selects `N`,`A`,`DTZ`,`PTH` · `:69-73` mypy strict over `src` **and** `tests` · `:78-81` `--strict-markers` with exactly one declared marker |
| 6 | `.github/workflows/ci.yml` | `:37-49` is the entire gate: ruff, ruff format, mypy, `pytest -m "not gamedata"`. **No MySQL service, no gitleaks.** |
| 7 | `tests/test_no_leaks.py`, `tests/test_repo_structure.py`, `tests/test_agent_contract.py`, `tests/test_doc_links.py` | The four guards that must stay green (AC16). `test_no_leaks.py:24-28` is the pattern list this document is scanned by |
| 8 | `docs/league-rules.md` | §1 is the verification target. **`:129` and `:295` assert a `leagues.dat` that does not exist** — Phase 12 corrects them |
| 9 | `gm/README.md` `:17-19`, `gm/standing-orders.md` `:42-50`, `.claude/agents/gm.md` | The placement rule, the report-entry format (whose `Owner:` field is why Decisions §4 exists), and the GM's two-tool delivery surface |

## 2. Architecture map

### 2.1 What exists today, measured

`src/ootp_ai/` — one file, `__init__.py`, 241 bytes. `transform/`, `build/`, `datasets/` do not exist and this feature **must not create them** (scope Non-Goals; CLAUDE.md forbids speculative directories; note `.gitignore:61` already carries an `!datasets/**` carve-out for a directory that does not exist — leave it alone). `tests/` holds four structural guards — `test_no_leaks.py`, `test_repo_structure.py`, `test_agent_contract.py`, `test_doc_links.py` — and no parser test. Baseline: `uv run pytest -m "not gamedata"` is green.

### 2.2 Target package shape, layered so each layer only depends on layers an earlier phase proved

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

### 2.3 The five seams that carry the design weight

**(a) The cursor is the fixed-offset ban.** `parser/primitives.py` exposes a `Cursor` over an in-memory `bytes` (`Path.read_bytes()`; `players.dat` is 32 MB, trivially affordable) with advancing-only readers: `u8/u16/u32/i32/f64`, `string()` (u32-LE length prefix, raw ASCII, **no terminator** — `docs/data-access.md:195`), `date()` (u8 day, u8 month, u16 year — `:196`), `color()` (u32 ARGB — `:197`), `skip(n)`, `remaining()`. It exposes **no** absolute-positioning method and no `seek`. Critically, **`header.py` uses the same cursor** — reading 1 byte, then 4, then a u32 sequentially rather than indexing offsets 1/5/25. That single decision is what lets AC3's static scan cover all of `src/ootp_ai/parser/` with **zero exemptions**; if the header reader indexes literals, the guard needs an exemption list and stops being a guard.

**(b) One declaration, three consumers.** `contracts/tables.toml` + `field_map.toml` are read by (i) `warehouse/ddl.py`, which *emits* the DDL rather than restating it, (ii) `tests/test_grain_contracts.py`, which compares the prose grain sentence to the emitted key, and (iii) `catalog/generate.py`. That triangle is what makes prose-vs-enforcement drift *structurally impossible* rather than merely discouraged — the exact obligation at `.claude/agents/data-engineer.md:101-104` ("states its grain in prose *and* enforces it with a uniqueness test, and the two must **agree**"). TOML because `tomllib` is stdlib in 3.12 (no new dependency), nothing writes the file, and per-field epistemic rationale wants comments. ADR 0006 §Notes explicitly blesses derived schema knowledge as ours and trackable — `.claude/agents/data-engineer.md:117-120` restates the line: *"A field-offset map you computed is ours and is tracked. A copy of `players.csv` is Out of the Park Developments' and is not."*

**(c) `contracts/policy.py` is the only path to a page — and it has exactly two outcomes, no bypass.** *Corrected per blocker EX-02; the panel's draft had a single gate and it was unsatisfiable.* The original rule returned false for `category == "rating-true"` **or** `epistemic in {"unconfirmed", "assumed"}`. That second clause made the plan's **own pre-registered `list_id` fallback unreachable**: the fallback renders `list_id` grouped by raw value *with a banner stating the meanings are `unconfirmed`* — a field the single gate blocks outright. Phase 10's acceptance would have been unsatisfiable, and the implementer's cheapest escape would have been to quietly upgrade the label, which is the exact error the labelling discipline exists to prevent. The same collision hits any non-rating field that has not yet earned an `inferred` label.

The corrected policy:

1. **`category == "rating-true"` → WITHHELD, no exceptions.** ADR 0012, absolute. Also withheld: `players.prone_*`, `players_value.*`, and any field the parser could not classify — CLAUDE.md's corollary is that an unclassifiable field *is treated as a true rating*, and *"probably fine" is not a classification.*
2. **A low-confidence *non-rating* field → renderable only through an explicit `render_with_uncertainty` path**, which forces the report to emit the raw value plus the `unconfirmed` banner and cannot be reached by the ordinary column route.

Both are **pure functions over a declaration**, so AC13's offline test feeds them synthetic entries — otherwise the test cannot run in CI, where no ratings have landed. AC13's negative case grows accordingly: assert a synthetic `rating-scouted` field with a proven label *is* renderable, **and** that a synthetic `unconfirmed` non-rating field is reachable *only* via `render_with_uncertainty`. A guard that blocks everything passes the positive half and delivers nothing.

**(d) Every bronze primary key carries `save_id`, `sim_date` and `ingest_seq` — the universe, the in-game date, and which attempt at that date.** *Amended after the plan was first committed; see the Amendments note at the end of §2.4.*

**`sim_date` is the in-game date, and it is the only date in any key.** The plan originally used `snapshot_date` in keys and `sim_date` in directory paths without ever stating they were the same value — a cold agent would reasonably wonder whether they differed. They do not. There is one date, it is the league's sim date, and it is named `sim_date` everywhere. Wall-clock ingestion time exists only as an attribute on `ingest_run`, never in a key: for every practical purpose you snapshot when you sim, and keying on wall-clock would fragment a single game state across re-runs.

**`save_id` separates universes.** The pipeline parses more than one — `OOTP-AI` (Boston, Challenge Mode, 2024-03-07), the retained standard-mode probe (Chicago Cubs, 2024-03-18) and the Challenge-mode twin (Boston, 2024-03-18) — and a key without it collides them. It is the save directory stem, `VARCHAR(64) NOT NULL`, validated at config time against `^[A-Za-z0-9_-]+$`. That regex does double duty: it makes it structurally impossible for an absolute path to become a `save_id` and leak into a tracked catalog.

**`ingest_seq` separates two states of the *same* in-game date**, and it exists because of a real operational case the first draft blocked. The operator executes a GM action on 2024-03-07 — signs a free agent, sets a lineup — and wants a snapshot proving it landed. The sim date has not moved. Same key, different bytes. With `(save_id, sim_date)` alone and a loud refusal on re-land, the pipeline rejects a legitimate request; the same wall is hit when a parser fix means re-landing a date already ingested. `ingest_seq` is a monotonic integer per `(save_id, sim_date)`, starting at 1. **This preserves append-only immutability rather than trading it away** — nothing is ever overwritten; a second attempt is a new row set, and the pre-action and post-action states of one sim date are both retrievable. That matters beyond convenience: this project exists to test whether the front office's decisions were good, and being able to diff the club immediately before and immediately after an executed action is evidence that cannot be reconstructed after the fact.

**Consequence for every consumer:** a query or report that omits `ingest_seq` reads an ambiguous grain once any date has been ingested twice. Reports resolve to `max(ingest_seq)` for the requested `sim_date` **by default and state the seq they read on line one**, so a `gm/decisions/` record citing a report is verifiable later rather than pointing at a moving target.

**Every PK column is declared NOT NULL** — MySQL's `COUNT(DISTINCT a,b,c)` silently drops tuples containing NULL, so a nullable PK column would make the grain test under-count and pass vacuously.

**(e) The catalog splits, and the split is what keeps it honest.** Per Decisions §3: the **structural half** (table names, grain sentences, key lists, coverage statements, withheld groups with reason and ADR, epistemic labels) generates from `tables.toml` + `field_map.toml` **alone** — no game data, no MySQL — so it is tracked, regenerates offline, survives a fresh clone, and can be asserted byte-identical to the committed copy. The **volatile half** (row counts, snapshot dates, freshness) plus `catalog.json` generate into the git-ignored root. **Recommended strengthening of the scope's marking:** because the byte-identity clause needs neither a save nor a database, split AC15 and run that clause **offline in CI** rather than under `-m gamedata`. That strictly increases what CI enforces.

### 2.4 Two path decisions that dissolve known risks at zero cost

**Reports render to `<output_root>/<save_id>/<sim_date>/<ingest_seq>/roster.md`.** Snapshot-partitioning dissolves SD-21 / Risk 10 — regenerating a report overwrites the prior snapshot's view and breaks citation integrity for any `gm/decisions/` record that cites it — because a new sim date, or a new `ingest_seq` within one date, writes a new directory, while re-rendering the same triple stays idempotent. **This is what makes a `gm/decisions/` citation verifiable months later**: the exact bytes the GM read are still on disk, not regenerated from a warehouse that has since moved on. `.gitignore:18` is a bare `var/`, and `git check-ignore -q var/reports/roster.md` exits 0 today, so AC14's ignored-root proof works as written.

**Every `file:line` citation this feature writes uses a code span, never a Markdown link, and nothing links into `var/`.** `tests/test_doc_links.py` resolves every relative link target in every tracked `.md` with no fence awareness and no `var/` exemption, so a link into the ignored output root turns CI red **today**. An open bugfix request exists (`requests/bugfix-requests/_done/doc-link-guard-mismatch/`); work around it, do not fix it here. `PROJECT_SCOPE.md:5-9` adopts the same convention for the same reason.

### 2.5 The three saves, and which question each one can answer

*Added by amendment. The first draft of this plan treated the Challenge-mode test save as a disposable target for filesystem-safety tests and missed what it actually is.*

Measured 2026-08-16 from `saved_games.dat` and the save directories:

| Save | Mode | Sim date | Human team | `.dat` files | Export? |
|---|---|---|---|---|---|
| `OOTP-AI.lg` | **Challenge** | 2024-03-07 | **Boston Red Sox** | 19 | No — Challenge Mode hides it |
| `Test Save - Challenge Mode.lg` | **Challenge** | 2024-03-18 | **Boston Red Sox** | 19 | No |
| `Test Save - Standard Mode.lg` | Standard | 2024-03-18 | Chicago Cubs | 18 | **Yes** → `ootp_truth_real` |

Three facts that follow, each load-bearing:

**(i) The Challenge-mode test save is a structural twin of production.** Same club, same mode, eleven days ahead, and its file set is **identical** to `OOTP-AI.lg`'s. It is disposable and simmable, so it is the right default target for developing and rehearsing the whole pipeline — and the right way to manufacture a multi-snapshot history for trending without ever touching the managed league. Develop here; visit production last.

**(ii) The Cubs save is the only one that can prove the parser correct.** Challenge Mode has no export (ADR 0003), so Tier B — the row-for-row differential — is *structurally confined* to the standard-mode save. That is not a gap to close; it is a permanent property of the project. Say so rather than letting a green suite imply the parser was diffed against the club we actually manage.

**(iii) Mode changes the file set by exactly one file, and the parser must prove that rather than assume it.** Measured: the only difference between the Challenge and Standard test saves is `challenge.dat` (present in Challenge, absent in Standard); nothing is *missing* from a Challenge save. The `teams.dat` headers of all three saves are **byte-identical** for their first 30 bytes: `00 4f 4f 54 50 19 00 00 00 0b 00 00 00 68 00 00 00 54 00 00 00 01 00 00 00` + `teams`. That is strong evidence Challenge Mode is a *gameplay* restriction — no export, no commissioner tools, an integrity hash — and not a storage format change. **But it is `inferred` from headers and file sets, not `verified` at record level**, and the whole risk this project cannot afford is a parser that works on the save we develop against and breaks on the save we manage.

So it becomes a test. The two test saves sit at the **same sim date (2024-03-18)**, which is an unusually clean matched pair: parse both with the *same* walker and assert their structural equivalence. Built incrementally — file sets and headers in Phase 3, and each walker phase (5, 6, 7) adds its own file to the assertion as it lands. This converts the mode-independence claim from `assumed` to `verified` at near-zero cost, because both saves already exist.

**What Challenge-mode saves *can* be validated against**, given no export — four channels, not three:

1. **Tier A** — `players.csv` joined on the embedded Lahman ID proves identity and names for the ~1,712 real players on Boston directly, exactly and offline.
2. **Byte accounting** — a residual-free walk proves the reader consumed what it should.
3. **Cross-mode equivalence** — proves the format did not shift between the save we develop against and the save we manage.
4. **Operator spot-check against the game itself.** *Added by amendment; the first draft omitted this and understated Challenge-mode validation as a result.* The operator can open any screen in the game, and can build **custom in-game reports**. That is a real answer key for a Challenge save — not mechanical, but neither is it an impression.

### The rule for channel 4, and it is narrow on purpose

**In-game displays are valid ground truth for every field this slice lands, and remain banned for ratings.** Those are not in tension; they concern different field classes, and conflating them would erode the project's single most dangerous correctness trap.

**Banned, permanently** (`docs/data-access.md` §5; `.claude/agents/data-engineer.md:75-78`): ratings. They pass through **two** lossy transforms before reaching the screen — scale conversion (20–80 on the player page, 1–100 in reports, ~1–1000 in storage) *and* scout filtering. Matching a displayed rating to a byte identifies the **wrong field with no error surfaced**. Ground truth for a rating is `players.csv`, which is raw. Nothing in this amendment softens that.

**Valid, because neither transform touches them** — and this is precisely the field set the slice lands, since it withholds every rating by design: first and last name · position · bats/throws · uniform number · date of birth and age · team and organization assignment · roster-list membership · team city, nickname, abbreviation and colors · league and division structure · W-L records · contract dollars. A player's uniform number is 34 on the screen and 34 in the bytes. There is no scale to convert and no scout standing between the value and the display.

**Why this is safe rather than a leak.** `FRONT_OFFICE.md:83` — *"The operator is not your analytics department."* The operator's view is deliberately wider than the GM's, and the wall between them is architectural: the GM reads reports built from scouted data ([ADR 0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md), [ADR 0012](../../../docs/decisions/0012-scouted-ratings-only.md)), while the operator reads screens to verify the *pipeline*. Perfect information used to check whether a parser landed the right byte is engineering; the same information routed into a baseball decision would be the violation. Keep the channel labelled.

**Scope boundary, stated so it is not crossed by accident.** The operator *reading* a screen or a custom in-game report and confirming values by hand is a **USER-RUN check with no code**, and is in scope. **Any code that parses `news/html/` is out of scope** — the scope rules out the in-game HTML report path explicitly, and building a test that reads a generated report would cross that line and needs a scope amendment first, not a pull request.

> **Amendments applied after the first commit of this plan** (`acc5575`), each at the operator's direction: `ingest_seq` added to every bronze key and `snapshot_date` renamed to `sim_date` (§2.3(d)); this §2.5 and the cross-mode equivalence test; a separate `ootp_dev` landing schema for development (Phase 1); a written spawn contract for handing the GM its reports (Phase 11); and the operator's in-game spot-check recognised as a fourth validation channel (§2.5, Phase 13 step 5). A world-state or "situation" artifact was **considered and deliberately rejected** — it would be a third report, which the scope rules out as a non-goal, and the thin-sight tension is the thing the experiment is testing.
>
> **Amended again 2026-08-17, ahead of Phase 6 starting.** The operator settled the `list_id`
> enum by reading the game and supplying a full-organization screenshot, so Phase 6's research
> step is closed before the phase begins and the roster report may print human labels. Two things
> that came back are wider than the plan assumed and are recorded at the head of Phase 6: the
> roster fan-out is **cross-team**, not merely cross-list, so *"who is on Boston's roster"* has
> three correct answers; and the **60-day IL drops a player from the 40-man**, so the 40-man
> cannot be derived from the other lists. Phase 6's user-run check is now **one screenshot asked
> for at the START of the phase** rather than a five-player spot-check at its acceptance — the
> Dodgers image settled the enum in a single pass and surfaced two league-wide invariants nobody
> had proposed. Evidence: `requests/feature-requests/first-sight/reviews/list-id-semantics.md`.

---


## 3. Phased implementation

Fourteen phases (0–13). Each ends at a `/commit` gate on a green local run of `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy`. Phases 5, 6 and 7 walk three different files with three different byte-accounting tiers and three different answer keys — **do not merge them into one `parser` phase**, or a failure in `players.dat` blocks a green, provable `teams.dat`.

> **Correction applied (blocker MERGE-03).** The panel's merge crossed two planners' orderings and produced a **mutually blocking pair**: its names phase needed the player walk's name indices, while its players phase needed the names resolver for the blank-display-name assertion. Neither could close. Per the operator's disposition the original code-grounded ordering is restored — **`players.dat` walks first** (minimal field set, `historical_id`, raw name **indices**, no display names), **then** `names.dat` and the join. **AC9's `zero blank display names` clause moves with it, into the names phase**, since that is the phase that can satisfy it.

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
3. **`src/ootp_ai/config.py`** — a frozen dataclass plus `load_settings()`. Every path resolves from `.env`; **no literal path, no `parents[N]` walk** (`.claude/agents/data-engineer.md:88-90`, whose parenthetical makes test modules the one established exception). `OOTP_SNAPSHOT_ROOT` is documented at `.env.example:25` as defaulting to `var/snapshots` and is **empty in the live `.env`** — so define the default here as a CWD-relative `Path("var/snapshots")`, validate it is creatable, and reject it if it sits under the `OneDrive` environment variable's value (`.env.example:23-24` warns against cloud-synced storage). Derive and validate `save_id` per §2.3(d).
4. **`src/ootp_ai/warehouse/sql.py`** — `quote_ident()`, backticking every identifier and rejecting an embedded backtick. This is not hygiene theatre: measured, `select current_date from ootp_truth_real.leagues` returns the wall-clock date for all 15 rows, because MySQL parses the bare column name as the `CURRENT_DATE` function and **nothing errors**. That is a data incident sitting in the exact code path Phase 9's differential will use. Add `src/ootp_ai/db.py` with a read-only `ootp_truth_real` factory and a write factory for `ootp`.
5. **`.env.example`** — add the retained standard-mode probe save and the disposable Challenge Mode probe save (a directory *and* a league name each, so neither is hardcoded), plus the report/catalog output-root key. Retire `MYSQL_TRUTH_OSA_DATABASE` (`:58`) per Decisions §10, and mirror the retirement in `ops/mysql-bootstrap.sql` by removing the `ootp_truth_osa` create and its grant — measured, that schema is empty and `ootp_truth_real.players_scouted_ratings` already carries **both** scouting perspectives from one export (36,144 rows, `scouting_coach_id ∈ {-1, 2759}`, 18,072 each), so the premise for a second export database is wrong. All `.env.example` values stay empty: `tests/test_no_leaks.py:25` flags a drive letter.
   **Amendment — separate the development landing schema.** `MYSQL_DATABASE` currently reads `ootp` and every save lands there, so isolation between the probe universes and production rests on the `save_id` **column** alone: a `SELECT` that forgets it silently mixes universes, and nothing catches that. Document `ootp_dev` as the development value and `ootp` as production, add the `ootp_dev` create and grant to `ops/mysql-bootstrap.sql` beside the existing ones, and **default the development workflow to `ootp_dev`**. This costs one env value and zero code. `save_id` stays in every key regardless — the schema split is defence in depth, not a replacement for the discriminator, and the Phase 9 differential still runs cross-schema inside one MySQL instance exactly as ADR 0004 intends.
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
1. `parser/primitives.py` — the Cursor per §2.3(a).
2. `parser/header.py` — read via the cursor only: leading `0x00`, `b"OOTP"`, u32 version (must be 25), the four u32s (11, 104, 84, 1), then the null-padded self-declared filename, cross-checked against the file actually opened (`docs/data-access.md:172-189`). Raise `UnsupportedSaveVersion` (this exact class name is pinned by AC1) on an unrecognized version, and a distinct `SaveFilenameMismatch` on disagreement. Refuse strictly — `.claude/agents/data-engineer.md:82-84`: *"a loud failure is recoverable, a silent misparse is not."*
3. `saves.py` — a directory is a save only if **both** `players.dat` and `teams.dat` are present. `docs/data-access.md:60-63` records, `measured`, that *"a `*.lg` glob is not a list of saves"* — the saved-games root contains a stray, empty directory literally named `.lg`. Add `assert_challenge_mode()`: `challenge.dat` present at **exactly 241 bytes** (`:65-68`), a filesystem-level mode check with no menu involved, promoted to a per-run pre-flight (folded-in §6).

**Steps (main thread — tests and fixtures).**
4. `tests/fixtures/synthetic.py` — byte builders as **functions**, not data files: `make_header(version=…, filename=…)`, `make_record(contract_years=…)`. **Fixtures must not carry a `.dat` extension.** Verified: `.gitignore:31` ignores `*.dat`, but `.gitignore:62`'s `!tests/fixtures/**` is a *later* negation and git's last-match-wins, so `tests/fixtures/sample.dat` is committable; the only thing catching it is `tests/test_no_leaks.py:107`'s `banned_suffixes`, as a red build. Building bytes in code sidesteps the whole question. `tests/fixtures/README.md` also makes the affirmative argument: a real save's day-0 state is the **least** informative input available, because every variable-length region is at its minimum — precisely the condition a fixed-offset reader passes cleanly.
5. `tests/test_save_header.py` (offline, **AC1**): a valid v25 header parses; version 24 **and** version 26 each raise `UnsupportedSaveVersion` by name; a buffer with `b"OOTP"` at offset **0** is rejected (the trap at `docs/data-access.md:183-186` — a reader checking `data[0:4]` sees `\x00OOT` and rejects every valid save, and one reading the version as a u32 at offset 4 gets 6480 rather than 25); a filename mismatch is rejected.
6. `tests/test_sequential_walk.py` (offline, **AC2**): two synthetic records identical except for the length of a variable-length region — a 1-year vs a 10-year contract array — must yield identical values for every field parsed *after* that region. Include a **negative control** in the same module: a deliberately fixed-offset local reader asserted to *fail* the same comparison. A test that passes without ever being able to fail proves nothing.
7. `tests/test_no_fixed_offsets.py` (offline, **AC3**): implement with `ast`, not regex, so a comment or docstring cannot trip it. Walk every module under `src/ootp_ai/parser/`; flag any call to `.seek(<nonzero int literal>)` and any `struct.unpack_from` whose third positional argument is a nonzero integer literal. `seek(0)` stays legal; `unpack_from(fmt, buf, cursor)` with a **name** argument stays legal — the ban is on literals. Include a self-test proving the scanner flags a synthetic offending snippet.
8. `tests/test_save_enumerator.py`: offline half against a `tmp_path` tree containing a decoy empty `.lg`; `-m gamedata` half against the **disposable Challenge Mode probe first**, and only then `OOTP-AI.lg`.
9. **MAIN THREAD — `tests/test_cross_mode_format.py` (`-m gamedata`), the first half.** *Added by amendment; see §2.5.* The two test saves sit at the **same sim date (2024-03-18)** and differ essentially in mode, which is a matched pair worth exploiting. Assert at this phase: their `.dat` file sets differ by **exactly `{challenge.dat}`** and nothing is absent from the Challenge save; `OOTP-AI.lg`'s file set is **identical** to the Challenge test save's; the header of each shared `.dat` is byte-identical across all three saves; and `assert_challenge_mode()` returns true for the two Challenge saves and false for the standard one. Each walker phase extends this module with its own file. **Why this is not ceremony:** every row-for-row validation this project can perform runs on the *standard* save, because Challenge Mode has no export — so without this test, "the format does not change with mode" stays an assumption underneath the entire pipeline, and the failure it guards against is a parser that works on the save we develop against and breaks on the save we manage.

**Acceptance.** The three offline modules are green with no game install and no MySQL (AC1, AC2, AC3). Introduce `f.seek(128)` into a parser module, confirm `test_no_fixed_offsets.py` goes **red**, revert. `git ls-files tests/fixtures` lists no `.dat` or `.lg` path. `mypy` clean over the new package under strict mode.

**Commit note.** *"Parser spine: cursor primitives, strict header/version guard, save enumerator, mechanical fixed-offset scan."* Scrutinise this phase's acceptance hardest — everything downstream inherits it, and these three offline tests run in CI on every subsequent PR, so a later phase that reintroduces a seek goes red immediately rather than at the next data incident.

---


### Phase 4 — Snapshot copy, provenance from data, and the ADR 0001 read-only proof

**Goal.** Get every later phase parsing a snapshot rather than the live save, and prove mechanically that nothing under the game directories was touched — **before** the phases that open the big files, not after.

**Steps.**
1. `snapshot.py` — copy **only** the in-scope set to `<snapshot_root>/<league>/<sim_date>/`: `teams.dat` (5,318,831 B), `players.dat` (32,070,106 B), `names.dat` (8,642,110 B) — ~46 MB, **not** the ~600 MB `.lg`, and explicitly not `retired.dat` (154 MB). *(Superseded in Phase 5: the set grew to five files and ~55 MB, adding `world.dat` and `human_managers.dat` under ADR 0018 tier 2. The three-file figure below describes what Phase 4 built, not the current set.)* Write a per-file size + SHA-256 manifest. Every handle `"rb"`. Refuse to overwrite an existing snapshot directory — snapshots are immutable (`.claude/agents/data-engineer.md:85-87`), which is what makes incident triage tractable and history re-parseable without the game.
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

> **AMENDED 2026-08-16, after the first build escalated and a recon pass answered it.**
> The original phase assumed `teams.dat` carries a fixed field sequence including
> `division_id`, `allstar_team` and the standings. **It does not**, and the phase is now
> split. What changed, all `measured` against all three saves with `ootp_truth_real` as
> oracle and re-run on a second save with no refit:
>
> - **A team record omits an integer field entirely when its value is zero.** The
>   pre-colour run is `[city_id, park_id, league_id, sub_league_id, nation_id, human]`,
>   zeros dropped — exact on **259 of 259** records in two independent saves. The
>   export's column order scores **0 of 259**, a second falsification of "export order is
>   disk order" after the `coaches.dat` finding.
> - **`division_id` and `allstar_team` are not in the file.** Inserting `division_id`
>   scores 0 of 140 on the teams that have a non-zero one; appending `allstar_team`
>   scores 0 of 30 on the All-Star sides. Those are the subsets that could refute them,
>   which is why a 232/233 overall fit was not evidence either way.
> - **`level` (259/259) and `parent_team_id` (199/199, control 0) are landable** — after
>   the three ARGB colours, which are themselves not in export order.
> - **The last slot is `human_team` or `human_id` and no oracle can separate them.**
>   18 field orders tie at 259/259, differing only there and in where the
>   constant-zero `prevent_any_moves`/`gender` sit. One flag lands; the ambiguity is
>   recorded rather than resolved by preference.
> - **26 of 259 records carry no city string**, so the `verified` five-string signature
>   is four strings on the minor-league All-Star sides.
> - **`human_managers.dat` names the managed club directly** — 835 bytes, offsets
>   231/235/239, reading 4/4/6 across the three saves, with the same intersection at
>   ±1/+2/+10/+100 empty. This takes the hardest field off the critical path.
> - **Header-tail field 5 is a record count for `teams`/`names`/`parks`/`coaches`/
>   `retired` but *not* universally** — `players.dat` declares `0xFFFFFFFF`.
> - **`world.dat` holds division membership and the league calendar**, and the operator
>   disposed widening `SNAPSHOT_FILES` to reach them (ADR 0018 tier 2, 2026-08-16).
>
> **Phase 5a is `teams.dat` + `human_managers.dat`. Phase 5b is `world.dat`.** Full
> evidence in `reviews/handoff-phase-5.md` and `reviews/handoff-phase-5-recon.md`.

**Goal.** Land the first real walk against the file with the strongest existing ground truth, validating the walker pattern before the two hard files.

**Steps.**
1. `parser/teams.py` — sequential walk yielding `team_id`, the 5-string signature (city, abbreviation, nickname, logo filename, full name) followed by u32 ARGB colors — already `verified` at `docs/data-access.md:224-226`, with all 30 MLB clubs extracting cleanly — plus level, `parent_team_id` (so MLB clubs are distinguishable from affiliates), the sub-league/division hierarchy, and the win-loss fields the standings report needs. Note `docs/data-access.md:228` marks *everything else* in that file `unconfirmed`.
2. **Structural absence starts here and is a parser-level concept.** A field the record does not carry → `None` → SQL NULL. A field present holding zero → `0`. Bronze never converts between them (`.claude/agents/data-engineer.md:110-112`: *"Averaging across that boundary produces wrong numbers, not incomplete ones."*). This bites immediately: the export writes `0` for `rules_active_roster_limit` and the service-time columns on all **14** non-MLB league rows — 14 separate opportunities to commit this error.
3. Track consumed bytes as the walk proceeds and return a residual.
4. **MAIN THREAD:** the teams half of `tests/test_byte_accounting.py` (`-m gamedata`, **AC12**) at the **strict** tier — zero unaccounted bytes. If strict proves unreachable within the phase, apply Phase 0's pre-registered demotion rather than opening an unbounded research task on the critical path.
5. **MAIN THREAD:** the teams half of `tests/test_parse_real_save.py` (`-m gamedata`, **AC9**) — exactly 30 teams at MLB level with correct abbreviations from `OOTP-AI.lg`; 259 teams total from the probe; `team_id` unique per snapshot.
6. **MAIN THREAD:** an offline `tests/test_parse_teams_synthetic.py` against a hand-built two-team buffer, so the walker has CI signal (`.claude/agents/data-engineer.md:91-92`).

**Acceptance.** The three test selectors above green at their declared tiers, and the declared tier matches what the test actually asserts. `test_no_fixed_offsets.py` still green over the enlarged parser tree. `test_read_only.py` re-run green after a full `teams.dat` walk. **Extend `tests/test_cross_mode_format.py`** (§2.5): the same walker parses `teams.dat` from the Challenge and Standard test saves — both at 2024-03-18 — and yields the same record shape, field ordering and byte-accounting tier, differing only in content. This is the first record-level evidence that Challenge Mode does not change the format.

**Commit note.** *"Walk teams.dat sequentially: team dimension, hierarchy, W-L, byte accounting."* From here on, **every phase re-runs `test_read_only.py` and `test_no_fixed_offsets.py` as part of its own acceptance** — the two unrecoverable-failure guards, checked at every checkpoint for the cost of seconds.

---


### Phase 5b — `world.dat`: the division hierarchy and the league calendar

> **AMENDED 2026-08-16, on completion.** Three claims below were carried in from the Phase 5
> recon and the build falsified all three. They are struck here rather than edited in place,
> because in each case the *shape* of the error matters more than the number — and in each
> case the false version was the one that made the managed league look like the probes.
>
> - **The calendar is NOT byte-identical across all three saves.** The two probes are
>   byte-identical to each other; `OOTP-AI.lg` differs in exactly **233 bytes, every one of
>   them a `deleted` flag**. The shipped calendar is common; deletion is per-universe state.
> - **`deleted` is 2,492, not 2,482 — and it is per save.** The export agrees at 2,492
>   (`SUM(deleted <> 0)`); `OOTP-AI.lg` reads 2,259. Step 6's single number was wrong by ten
>   against the answer key *and* wrong in kind about the league we manage.
> - **The schedule's 37-byte stride does not reproduce.** Both probes give
>   `479,557 = 12,961 × 37` exactly; `OOTP-AI.lg` gives `622,233 = 16,817 × 37 + 4`. Crossing
>   it to reach the calendar was therefore rejected — exact in the two universes with an
>   export, four bytes off in the one without, which is this project's signature failure
>   shape. The calendar is entered by its own structural landmark instead.
>
> Two further findings, neither a correction: **`needs_human_action` totals 112 in every
> save**, of which three survive undeleted in the probes and **ten** in `OOTP-AI.lg` (it
> still holds live duplicate Trading Deadlines and Rule 5 Drafts) — so the managed club
> faces more of these dates than the probe suggested. And the walk lands **MLB's six
> divisions only**; the other fourteen leagues each sit behind their own unmapped scalar
> block. Full evidence in `reviews/handoff-phase-5b.md`, which **supersedes the `world.dat`
> rows of `reviews/handoff-phase-5-recon.md`'s docs-delta** — route the corrected version
> at Phase 12, not the original.

**Goal.** Reach the two structures `teams.dat` turned out not to hold, and land the calendar that tells the front office which dates it is required to show up for.

**Steps.**
1. `parser/world.py` — **composite-landmark entry, not a fixed offset.** The league region sits ~62% into an 8.9 MB file whose header declares `record_count = 1`, behind a ~94,000-record city array, so a from-the-top walk is its own project and seeking is banned outright. Enter by locating a length-prefixed string matched on **prefix and payload together** — `\x15\0\0\0Major League Baseball` and `\x02\0\0\0AL\x0f\0\0\0American League` each occur exactly once in all three saves, while bare `OPENING DAY` occurs 95 times — then walk sequentially forward. Both target regions declare their own count, so the walk is self-checking after entry: read the count, consume exactly that many records, land on the next region's boundary.
2. **Division membership**, nested `league → sub_league → division → u32 count + explicit team_id array`. Matches the export exactly on all six MLB divisions in all three saves. Lands as `bronze_division_team`; **`teams.division_id` is derived in silver from that array and never parsed**, which is what makes Phase 5a's omission of it correct rather than a gap.
3. **All-Star sides appear in no division array.** Their export `sub_league_id`/`division_id` of `0` is **structural absence rendered as zero** — a live instance of the trap the scope names, and the thing that lets the top-league count tighten from 34 to 30.
4. **The league calendar**, a `u32`-count-prefixed array (3,058) of `u32 seq, u32 league_id, u16 type, u8 day, u8 month, u16 year, 3 pad, u32 len + name, u8 event_over, u8 deleted, u8 needs_human_action, u16 real_sim_date`. All 3,058 entries match `ootp_truth_real.league_events` exactly on all eight columns, and the calendar is byte-identical across all three saves.
5. **The grain is `(save_id, sim_date, ingest_seq, event_seq)`, and this is not a preference.** `seq` is unique across all 3,058 entries and the export does not expose it. The human-readable alternative `(league_id, start_date, type, name)` collapses 3,058 rows to 2,600 — **458 events lost with nothing raised.** Declare the key on `seq`.
6. **`deleted` is not "past".** 2,482 of 3,058 rows carry it and every deleted MLB row is dated *after* the sim date; the set includes a duplicate OPENING DAY and three PLAYOFFS BEGIN. Land it as an attribute and let the report filter; do not filter at parse time, and do not treat it as history.
7. **`needs_human_action` is the field this phase is for.** Three live MLB events carry it — First-Year Player Draft (2024-07-11), Trading Deadline (2024-07-31), Rule 5 Draft (2024-12-13). It is the game's own answer to which dates the front office must act on, which [ADR 0013](../../../docs/decisions/0013-action-economy.md) currently answers by our judgment alone. Land it; do not build doctrine on it in this phase.
8. **MAIN THREAD:** `tests/test_parse_world.py`, the world half of `tests/test_byte_accounting.py` at the **`region-accounted`** tier, and the world half of `tests/test_cross_mode_format.py`. Tighten `test_parse_real_save.py`'s top-league count from 34 to 30.

**Acceptance.** All 3,058 calendar entries match the export on all eight columns, with the control (shifting `league_id` ±3) scoring materially worse. All six MLB divisions match on membership in all three saves. `region-accounted` holds: zero residual within each walked region, both declared counts matched, un-walked prefix and suffix byte counts recorded. `test_read_only.py` and `test_no_fixed_offsets.py` green after a full `world.dat` read.

**Deferred, explicitly.** The 12,961-game schedule (bounded and shaped — exactly 37 bytes per record — but nothing consumes it until the league sims), geography, schools, the `teams.dat` record body, a from-the-top walk, and the ~1,200-byte league scalar block that is the `docs/league-rules.md` §1 diff the scope already gated.

**Commit note.** *"world.dat: composite-landmark entry, division membership, and the 3,058-entry league calendar."*

---


### Phase 6 — `players.dat` walk and roster-list extraction

> **SPLIT 2026-08-17 into 6a and 6b, at the operator's disposition.** The trigger the
> second amendment below pre-registered fired: the phase's two halves turned out to be
> two jobs against two files, and the second is a research task of its own. Per risk 20's
> logic — three checkpoints cost three commits and buy three independently revertible
> units — the phase splits rather than widens.
>
> **Phase 6a — LANDED.** `parser/players.py`, the record framing, the fixed head, byte
> accounting at the diagnostic tier, `contracts/field_map.toml`, and the tests. Nine
> fields land `verified` against **every** `retired = 0` row of the export, not a sample:
> `player_id`, `date_of_birth`, `age`, `nation_id`, `city_of_birth_id`, `weight`,
> `height`, `uniform_number`, `experience`, plus the name-index pair carried
> `unconfirmed`.
>
> **Phase 6b — DEFERRED, and it owns three things.** (1) The **drop-zero region** that
> begins after `experience`, which is where `team_id`, `organization_id`, `league_id`,
> `position`, `role`, `bats` and `throws` live. (2) **`historical_id`** — see below.
> (3) `parser/rosters.py` and the `(team_id, player_id, list_id)` grain from `teams.dat`.
> **AC9's roster clauses move to 6b with it** — Boston's 26 / 30 / 7 / 33 counts cannot
> be asserted until the roster grain exists.
>
> **`historical_id` is called out separately because it nearly went unrecorded**, and it
> is the costliest thing here to lose track of. Step 1 names it; **AC8 depends on it** as
> the join key for the only Tier-A validation of the names join on the league we actually
> manage. It is `measured` as a `u32`-length-prefixed ASCII string appearing twice per
> record, ~60-80 bytes in — which puts it *after* the drop-zero region, so it is out of
> reach for exactly the same reason `team_id` is. **AC8 cannot be attempted until 6b
> lands it**, and Phase 7 must not be started on the assumption that it exists.
>
> **Two of this phase's premises were refuted by measurement and are corrected below**,
> because both would otherwise have become acceptance criteria that a correct parse fails:
> the file declares no record count, and it holds 18,077 records rather than 18,072.

> **AMENDED 2026-08-17 — `list_id` is SETTLED, and the fan-out is wider than this phase assumed.**
> The operator read the Dodgers organization screen in the standard-mode probe and supplied a
> full-organization screenshot. Step 2's research task is therefore **done before the phase
> starts**; do not re-derive it. Full evidence, method and the falsifiable cross-checks are in
> `requests/feature-requests/first-sight/reviews/list-id-semantics.md`.
>
> | `list_id` | Meaning | Scope |
> |---|---|---|
> | 1 | **Current team assignment** | every player, exactly once |
> | 2 | **Active roster** of the club he is assigned to | any level |
> | 3 | **Secondary (40-man) roster** | **MLB level only** |
> | 4 | **Injured list** | any level |
>
> **The fan-out is cross-team, not just cross-list.** This phase's Goal below says a player sits
> on the active list *and* the 40-man. True, and incomplete: a prospect on the parent club's
> 40-man but assigned to Triple-A holds `list_id = 3` under the **MLB club** and `1, 2` under the
> **affiliate** — three rows, two `team_id`s, one player. Measured on the Dodgers: 103 roster rows
> over 39 distinct players. A naive join from `teams` double-counts prospects, and *"who is on
> Boston's roster"* has three different correct answers.
>
> **The 60-day IL drops a player from the 40-man**, which is why some injured players carry
> `1 + 4` and others `1 + 3 + 4`. Consequence: the 40-man must be counted from `list_id = 3`
> directly — deriving it as active + injured + prospects over-counts by the 60-day population
> (58 players league-wide).

> **AMENDED 2026-08-17 (second) — the roster grain is in `teams.dat`, not `players.dat`.**
> This phase's title pairs the player walk with "roster-list extraction" as though they were one
> job against one file. **Measured, they are two jobs against two files**, and the second is the
> harder one. Reconnaissance on the standard-mode snapshot, before any build:
>
> - **The roster ids are in `teams.dat`.** Boston's (`team_id` 4) export roster ids appear there as
>   a dense **stride-4 `u32` array** spanning roughly 384 bytes — 96 slots against the export's
>   96 roster rows (33 + 26 + 30 + 7) — with values repeating exactly as a per-list encoding
>   predicts, since a player on lists 1, 2 and 3 must appear three times. The array is **unaligned**
>   relative to the file, which is expected: every string here is `u32`-length-prefixed, so nothing
>   is 4-byte aligned. `measured`. That this array **is** `team_roster` is `inferred` — the sub-list
>   boundaries and any length prefixes are not yet decoded, and one non-player value sits inside the
>   run.
> - **It sits in the region Phase 5 chose not to decode.** `parser/teams.py`'s docstring records
>   that records are separated by *"variable-length bodies of 1.5 KB to 60 KB that this walk does
>   not decode"* and that everything past `historical_id` is `unconfirmed`. So `rosters.py` is an
>   **extension of the `teams.dat` walker**, not a by-product of the player walk. Sequence it
>   accordingly, and expect it to inherit that file's drop-zero encoding.
> - **It cannot be derived from player columns, and the near-miss is the trap.** Tested against
>   `ootp_truth_real`: `list 1` vs `players.team_id > 0` differs by **176 rows** (7,370 vs 7,546,
>   all at `level` 1); `list 4` vs `injury_is_injured = 1 AND team_id > 0` differs by **3** (330 vs
>   332, 329 agreeing); `list 3` agrees with `organization_id` on all 935 rows but
>   `organization_id` is populated for every player in an org, so it identifies the club and not the
>   membership. A rule that is 97–99% right reproduces the answer key well enough to look finished
>   and is wrong on a roster somewhere — **derive nothing here; read the array.**
>
> **Consequence for sequencing.** The player walk (steps 1, 3, 4) is independent and can land
> first; `rosters.py` (step 2) depends on decoding further into the team record. If the sub-list
> framing resists inside this phase, that is the case for splitting the phase rather than widening
> it — Phase 0's opaque-integer fallback covered a wrong *label*, not an undecodable *array*, so it
> does not apply. **`measured` / `inferred` as labelled above; nothing here is `verified`.**

**Goal.** Land the deliberately minimal player field set and the **roster-membership grain** — the fan-out the request never names, and the one that bites *today*, on an unsimmed save with no trade in sight, because a player sits on the active list **and** the 40-man simultaneously — and, as the amendment above records, under two different clubs at once.

**Steps.**
1. `parser/players.py` — a deliberately minimal field set: `player_id`, team/organization assignment, position, uniform number, date of birth, bats/throws, the name indices, and `historical_id` (the Lahman/BBRef string, `verified` at `docs/data-access.md:99-102`, ~1,712 unique values). **No ratings, whatever the Phase 2 verdict returned.** Resist widening: every landed field is a field somebody re-validates after a game patch. The field set is a maintenance liability, not a free win.
2. `parser/rosters.py` — extraction at the `(team_id, player_id, list_id)` grain, **reading the array in `teams.dat` per the second amendment above, not deriving it from player fields.** Ground truth for the shape: `ootp_truth_real.team_roster` is **15,672 rows over 7,370 distinct players** — not 18,072 — with `list_id ∈ {1: 7370, 2: 7037, 3: 935, 4: 330}`, and it is a **pure key triple with no payload columns**, which is why it has to be read as a membership array rather than reconstructed from attributes. `db_structure_ootp25_mysql.txt` documents the columns but **not** the enum's semantics.

   **Resolve `list_id` by asking the operator to read the roster screen — do this FIRST, before any empirical derivation.** *Amended; the first draft sent this straight to open-ended research and put an unbounded tail on the critical path of the headline report.* The game shows, directly and unambiguously, which players sit on the active roster, which on the 40-man, and which in each minor-league tier. The operator reads it; the enum is settled in minutes and lands at `verified` rather than `inferred`. Bound the ask so it is cheap to answer: hand over a handful of `player_id`s per observed `list_id` value and ask which list the game shows each on. Cross-tabbing against the export's counts (`{1: 7370, 2: 7037, 3: 935, 4: 330}`) then becomes a *confirmation* of a known answer rather than an attempt to infer one from four integers.

   This is channel 4 from §2.5, and it is squarely inside the safe class — roster membership is neither scale-converted nor scout-filtered. Keep Phase 0's opaque-integer fallback registered in case the operator is unavailable, but it should now be the unlikely branch rather than the expected one. The reason the fallback exists at all is unchanged: **a wrong human label produces a confidently wrong roster with nothing throwing**, so the report prints no human label for any mapping below `inferred`.

   **This step is CLOSED as of 2026-08-17** — see the amendment at the head of this phase. The
   mapping is `verified`, so **Phase 0's opaque-integer fallback is retired for this field** and
   the roster report **may print human labels**. Do not spend a step re-deriving it. What the
   read left behind, and what this phase should assert instead:

   - **Every one of the 30 MLB clubs has exactly 26 rows at `list_id = 2`.** Zero exceptions
     across the probe export. This is the sharpest assertion available on the roster grain — a
     walker that transposed two list values would not land on 26 thirty times — and it is a
     league *rule*, so it should hold in the managed save too.
   - **No MLB club exceeds 40 rows at `list_id = 3`** (probe: min 27, max 37, mean 31.2).
   - **`list_id = 1` is 1:1 with players** — 7,370 rows over 7,370 distinct players, which is
     also the total distinct players in `team_roster`. A second list-1 row for any player means
     the walk has mis-framed a record.
   - Do **not** assert the probe's 58/118 short-vs-60-day IL split against `OOTP-AI.lg`; that is
     a state of one universe on one date, not a rule.
3. ~~**Verify, do not assume, the `players.dat` population.**~~ **MEASURED 2026-08-17 — and the assumption was wrong.** The plan assumed `players.dat` holds the export's `retired = 0` set of **18,072**. It holds **18,077**. The five extras are `player_id` 42001, 49008, 50468, 50469 and 132324, and **none appears anywhere in the export at any `retired` value** — so this is a strict superset, not a filtering difference within a shared population.

   They are real records, not mis-framed bytes, on four independent grounds: each carries the same 26-byte padding every record does; each has a length (1,152–1,320 bytes) inside the normal distribution; each has a coherent birth date, age, nationality, height and weight; and **the same five ids appear in both test saves**. On the evidence — blank uniform numbers, ages 18 to 25 — they look like an unrevealed amateur or international pool; *which* filter the export applies is `unconfirmed` and nothing depends on knowing.

   **Consequence, and it is not cosmetic.** AC12's record-count assertion and Phase 11's coverage statements both rest on 18,072. A test asserting that number **fails on a correct parse**, which is the most expensive kind of wrong test — it sends the next agent hunting a bug in working code. Both constants are now pinned in `tests/test_byte_accounting.py` as `TRUTH_ACTIVE_PLAYERS = 18_072` (what the export holds) and `TRUTH_PLAYER_RECORDS = 18_077` (what the file holds), deliberately as two different numbers.

   **A second premise went with it: the file declares no record count.** `teams.dat` puts its count in the fifth `u32` of the header tail and the walk uses it as a loop bound, so a mis-framed file raises. `players.dat` puts `0xFFFFFFFF` there in all three saves. The walk therefore has **no in-file oracle**, which is why its diagnostic tier is weaker than `teams.dat`'s and why the record-boundary check carries the whole load on the managed save.
4. Byte accounting at the **diagnostic** tier for `players.dat` (blocker F3): assert the walk terminates on a record boundary and reaches a record count matching the independent count, and **record** the residual byte count rather than asserting it is zero. Full byte accounting on a 32 MB `players.dat` is a research task, not a counter — say so in the tier rationale so a later reader does not mistake the weaker assertion for sloppiness. On `OOTP-AI.lg` there is no export, so the check degrades to boundary termination plus Phase 9's Boston sanity check; encode that degradation explicitly rather than silently skipping.
5. Append every landed field to `field_map.toml`. Anything the walk crosses but cannot classify is recorded `category = "rating-true"`, `epistemic = "unconfirmed"` — the withhold-by-default posture.
6. **MAIN THREAD:** advance `tests/test_parse_real_save.py` (**AC9, partial**) — `player_id` unique per snapshot; **Boston's exact per-list counts from the USER-RUN table below — 26 / 30 / 7 / 33, 96 rows over 34 distinct players.** *(Amended 2026-08-17: this was `≥ 26`, hedged on the guess that "a set 26 probably does not exist yet" in spring training. The operator's `OOTP-AI` screenshot reads 26/26 and 30/40, so the guess was wrong and the inequality is retired — it would have passed on a walk that found 27.)* **AC9's `zero roster rows carry a null or blank display name` clause does NOT belong here** — no display name exists until Phase 7 resolves the join, so asserting it now would fail on a correct parse. It moves to Phase 7, per the MERGE-03 correction. Extend `test_sequential_walk.py` with a player-shaped synthetic record (1-year vs 10-year contract array) asserting `historical_id`, which sits after the variable region, reads identically. Add the parser-determinism half of `test_snapshot_semantics.py` (**AC10**): parsing the same snapshot twice is byte-identical.

**Acceptance — SPLIT with the phase, 2026-08-17.** *This block described the un-split phase and is now divided so neither half inherits the other's criteria.*

**6a (met).** AC9's `player_id` uniqueness clause green — in `tests/test_parse_players.py`, not `test_parse_real_save.py`, because the players walk needed an offline half and that module is `gamedata` end to end; AC12 green at the diagnostic tier with the residual **recorded and bounded as a fraction of the file**, not against a mean record; **`tests/test_cross_mode_format.py` extended to `players.dat`** — identical record counts and id lists across both test saves, with the seven fields that cannot legitimately differ asserted equal on all 18,077 (§2.5); the population claim **measured and the plan corrected** (18,077, not 18,072); `test_read_only.py` re-run green after the largest read this project performs.

**6b (outstanding).** The three `list_id` invariants against the standard-mode export (26 exactly, 40 not exceeded, list 1 is 1:1) and Boston's exact counts against `OOTP-AI.lg` — **both need `parser/rosters.py`, which does not exist yet**; `historical_id` landed, without which **AC8 cannot be attempted at all**; `position`, `bats`/`throws` and the team/organisation assignment out of the drop-zero region; and the **USER-RUN screenshot check** below, which is a check *of the roster grain* and so has nothing to verify until 6b lands it.

**USER-RUN — ask for the Boston organization screenshot FIRST, before writing the walker.**
*Amended 2026-08-17: this replaces "an early operator spot-check of ~5 Boston players", which
was the right instinct and the wrong instrument.* One screenshot of the **Organization →
Overview** page for the managed club is strictly better than a per-player read, and it is
cheaper for the operator — one screen, one image, no transcription:

- It carries **panel headers that are countable claims**. On the Dodgers those read
  *Active Roster (26/26)*, *Secondary (40-man) Roster (35/40)* and an Injured List, and all
  three reconciled exactly against the export by arithmetic — a far stronger check than eight
  players looking plausible.
- It shows **every affiliate at once** (AAA/AA/A+/A/R and the DSL clubs), which is where the
  cross-team fan-out is visible. A single-club read cannot show it.
- It shows the **Injured List with an `IL Time Left` column**, which is what distinguishes the
  60-day population from the short IL.
- It shows name, position, age and uniform number for the whole org, so the field-level
  spot-check the old criterion wanted falls out of the same image.

**Where operator screenshots live.** `var/operator/screenshots/`, named
`<sim-date>-<save>-<club>-<screen>.png`. Three properties, each load-bearing:

- **`var/` is gitignored, and that is the point, not a convenience.** A game screenshot is Out of
  the Park Developments' data and [ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md)
  bars it from this public repo at any size. Dropping it here makes that automatic instead of
  something an implementer has to remember at `/commit`.
- **`tests/test_doc_links.py` exempts `var/` targets**, so this plan and the review artifacts may
  name the path in prose without turning a blocking CI check red — while the binary itself stays
  untracked. Naming the file is how the evidence stays checkable.
- **The sim date and the club belong in the filename.** A roster screenshot is true for exactly
  one club on exactly one date; an undated one silently becomes wrong the first time the league
  sims, and there is nothing in the image to catch it.

**The three exhibits now on disk**, one per save, all supplied 2026-08-17:

| File under `var/operator/screenshots/` | Save | Club shown |
|---|---|---|
| `2024-03-18-test-save-standard-mode-dodgers-organization.png` | `truth_save` — *Test Save - Standard Mode* (Cubs) | **Dodgers** org page |
| `2024-03-18-test-save-challenge-mode-boston-organization.png` | `probe_save` — *Test Save - Challenge Mode* | Boston org page |
| `2024-03-07-ootp-ai-boston-organization.png` | **`managed` — `OOTP-AI.lg`** | Boston org page |

> **The sim dates in those names are corrected, and the correction is the finding.** All three
> arrived named for a date the save is not on — off by 11, 4 and 11 days. **The Organization
> screen's header never displays the current date.** Its block reads
> `YESTERDAY / TODAY / TOMORROW` as *labels* against game results, and the first row carrying an
> actual date is the **fourth** day — three days out. Reading that row as "today" is what produced
> all three names.
>
> Measured instead from `saved_games.dat` via `parser/saved_games.py`: `OOTP-AI` **2024-03-07**,
> *Test Save - Challenge Mode* **2024-03-18**, *Test Save - Standard Mode* **2024-03-18**. Both
> Boston images then cross-check by weekday arithmetic against their own headers — `OOTP-AI` shows
> `SAT. MAR. 9 · SUN. MAR. 10 · MON. MAR. 11`, and 9 March 2024 was a Saturday, which places today
> at Thursday the 7th; the challenge test save shows `WED. MAR. 20 (OPENING DAY) · THU. MAR. 21`,
> placing today at Monday the 18th. Two independent confirmations, one per image.
>
> **`saved_games.dat` is the authority for `sim_date`; a screenshot is not.** That matters beyond
> filenames, because `sim_date` is a key column in every bronze table (§2.3(d)) — a screen-read
> date would key the warehouse three days into the future. `docs/data-access.md` should carry this
> at `measured` via the Phase 12 docs-delta.

**The standard-mode exhibit is a Cubs save showing another club's org page**, which is why it
carries *Show Ratings (D. Kantrovitz)* — the Cubs' scouting director, not the Dodgers'. It is the
evidence behind `requests/feature-requests/first-sight/reviews/list-id-semantics.md` and nothing
in this phase re-derives it.

**Ask for it at the START of the phase, not at its acceptance.** The Dodgers image settled
`list_id` in one pass and surfaced two invariants nobody had proposed; the equivalent Boston
image is the cheapest available insurance against a mis-mapped field, and a field found wrong
here costs one phase rather than the five it would cost at Phase 13 (§2.5 channel 4).

**DELIVERED 2026-08-17 — and it reconciles.** `2024-03-07-ootp-ai-boston-organization.png` is the
Organization → Overview page of `OOTP-AI.lg`, Challenge Mode, Boston, 0-0, 2nd in the AL East.
Read off it (roster membership, names, positions, ages — the safe class only):

| Panel | Header |
|---|---|
| Boston Active Roster | **26/26 Players** |
| Secondary (40-man) Roster | **30/40 Players** |
| Injured List | 7 MLB rows, plus 5 affiliate rows below a separator |
| Worcester (IL, AAA) · Portland (EL, AA) · Greenville (SAL, A+) | 26 · 26 · 26 Pl. |
| Salem (CAR, A) · Boston FCL (R) · DSL Blue · DSL Red | 24 · 28 · 30 · 27 Pl. |
| Designated for Assignment · Waivers | both empty |

**The arithmetic closes, exactly as it did on the Dodgers.** Of the 7 MLB injured, four read
`61 days (60)` — Fulmer, Giolito, Hendriks, Murphy — and three read `11`/`16 days` — Grissom,
Mata, Refsnyder. The 40-man panel carries a **TEAM column**, and Cooper Criswell appears there as
`WOR (IL, AAA)`: on Boston's 40-man while assigned to Worcester. So
**26 active + 3 short-IL + 1 affiliate-assigned = 30**, the 40-man header, with the four 60-day
players excluded — the second independent confirmation of the 60-day rule, on a different club, a
different save and a different game mode from the one that produced it.

**This replaces the `>= 26` smoke test with exact, falsifiable counts for `OOTP-AI.lg`.** Boston is
`team_id` 4. Assert all of these in Phase 6, and treat any one of them missing as a mis-framed walk
rather than a tolerance to widen:

| Quantity at Boston | Expected | Where it comes from |
|---|---|---|
| rows at `list_id = 2` | **26** | Active Roster header |
| rows at `list_id = 3` | **30** | Secondary (40-man) header |
| rows at `list_id = 4` | **7** | Injured List, MLB rows only |
| rows at `list_id = 1` | **33** | 26 active + 7 injured — injured keep their assignment |
| total `team_roster` rows | **96** | 33 + 26 + 30 + 7 |
| distinct players | **34** | 33 assigned + Criswell, who is on the 40-man but assigned to WOR |

**The spring-training hedge was wrong and is retired.** This phase's step 6 assumed *"a set 26
probably does not exist yet"* at 2024-03-07. The screen says 26/26. The club carries a full active
roster eleven days before opening day, so the weaker assertion bought nothing and would have
passed on a walk that found 27.

**The two Boston saves are near-twins and must not be conflated.** `OOTP-AI` (03-07) and the
challenge test save (03-18) both show Boston at 26/26 and 30/40 with the same seven injured
players and the same diagnoses; they differ in affiliate assignments (Salem 24 vs 26; Coffey and
Dobbins at Worcester in one, Alexander and Jacques in the other). Same club, same mode, eleven
days and two universes apart — so a test asserting the table above must name **which save** it
loaded, and `test_cross_mode_format.py` compares *format*, never counts.

**Ratings are not part of this check and never will be** (§2.5). The screen shows rating
columns; they are scale-converted and scout-filtered, and matching one to a byte identifies the
wrong field with no error surfaced. Read names, numbers, positions, ages and roster membership
from it — nothing else.

**Commit note.** *"players.dat minimal field set + team_roster membership grain with list_id derivation."* ~~Surface the `list_id` disposition to the operator here~~ — **settled 2026-08-17**: the report prints human labels, because the mapping is `verified`. What still needs surfacing at this checkpoint is the *cross-team* fan-out, since it changes what the roster report can honestly claim: Phase 10 must say **which** roster it is showing (assignment, active, or 40-man) rather than implying a canonical one exists.

---


### Phase 7 — `names.dat` and the join, against two independent answer keys

**Goal.** Resolve the largest single unknown in the request. `docs/data-access.md:234-238` records that names are indices into a ~264,095-entry table and labels *"the index encoding and the `names.dat` table layout"* **`unconfirmed`** — and `docs/data-access.md:14` is explicit that *"an unconfirmed claim is a task, not a fact."* A roster report of integers is not a roster report.

**Steps.**
1. `parser/names.py` — walk the observed record shape: u32 length + ASCII + u32 `0` + u32 monotonic index + three u32s + a `0x27` separator, alphabetically ordered. Strict byte accounting (zero residual).
2. **Settle the key space *before* any DDL is written.** It is genuinely unknown whether `names.dat` carries **one** index space or **two** (a first-name table and a last-name table, each alphabetically ordered with its own index from 0). If it is two and `bronze_name` is keyed `(save_id, sim_date, ingest_seq, name_index)` — that is, without a `name_space` discriminator — the spaces **collide and every collided row is silently wrong**, with nothing throwing. Pre-registered resolution: declare the key as `(save_id, sim_date, ingest_seq, name_space, name_index)`, with `name_space` a `NOT NULL` discriminator taking a single literal value if one space is proven. That key is correct under both outcomes and costs one column.
3. **Resolve which u32 fields in the player record are the name indices by brute force against a full answer key, not by guessing.** For each candidate u32 position the walk exposes, apply the mapping across all 18,072 probe players and score exact matches against `ootp_truth_real.players.first_name`/`.last_name`. The correct field scores ~100%; everything else scores near zero. Record the winning position and its score in `field_map.toml`.
4. **Enforce the per-save constraint structurally (SD-10).** Measured: `names.dat` is 8,642,110 bytes in **all three** saves on disk with **three different SHA-256 digests** — a fixed-size, per-save-populated table. The name table must be an object *owned by a save*, never a module-level constant, and the resolver's cache key must include `save_id`, asserted by a test. This is a silent-wrong failure with no crash: a cached probe table applied to `OOTP-AI.lg` produces a roster full of confident, wrong names.
5. **MAIN THREAD:** `tests/test_names_join.py` (`-m gamedata`, **AC7**, Tier B) — every resolved index matches `ootp_truth_real` by exact string equality, 100% of compared rows, zero unresolved indices, **every failure enumerated by name**, never an aggregate pass rate. It **skips loudly with a named reason** if `ootp_truth_real` is unreachable; verify the skip path by temporarily unsetting the key. A vacuous green here is worse than a red.
6. **Settle collation explicitly (SD-13).** `ops/mysql-bootstrap.sql` creates every schema `utf8mb4_0900_ai_ci` — accent- **and** case-**insensitive** — so an "exact" comparison performed in SQL scores `Ramírez == Ramirez` as a match, in a repo whose own export doc turns *Replace accents* **Off** specifically because it *"mangles names and breaks validation against `names.dat`"* (`docs/data-access.md:336`). **Fetch both sides into Python and compare decoded `str` with `==`**; where SQL-side comparison is unavoidable, append `COLLATE utf8mb4_bin` explicitly, and assert the choice in the test so a schema change surfaces.
7. **MAIN THREAD:** `tests/test_names_join_boston.py` (`-m gamedata`, **AC8**, Tier A) — for every player in `OOTP-AI.lg` carrying a non-empty `historical_id`, the resolved first/last name equals `players.csv`'s `FirstName`/`LastName` joined on `LahmanID`, 100% exact. **This is the only validation of the join on the league we actually manage.** Parse `players.csv` with stdlib `csv`, stripping the `//` prefix from its header line (`docs/data-access.md:79-80`).
8. **Hard bind:** never write a Lahman-ID-to-name lookup to a tracked file, in any form. `tests/test_no_leaks.py:106` catches `players.csv` by **filename only** — a renamed derived copy sails straight through into a public repo, and `tests/fixtures/README.md` says plainly that catching a renamed real slice is on the implementer.
9. **MAIN THREAD:** a `-m gamedata` test asserting the same index is **not** expected to resolve identically across the two saves, pinning the per-save finding.
10. **MAIN THREAD — AC9's remaining clause, moved here by the MERGE-03 correction.** Complete `tests/test_parse_real_save.py` by asserting **zero roster rows carry a null or blank display name** against `OOTP-AI.lg`. This clause lives here and not in Phase 6 because no display name exists until this phase resolves the join — asserting it earlier would fail on a correct parse, which is the most expensive kind of wrong test: it sends the next agent hunting a bug in working code. **AC9 is only fully green at the end of this phase**, not at the end of Phase 6.

**Acceptance.** AC7 and AC8 green as specified; AC9 now green **in full**, including the display-name clause moved here; strict zero-residual byte accounting on `names.dat`; **`tests/test_cross_mode_format.py` extended to `names.dat`, completing the cross-mode assertion** — with the format-equivalence claim in `docs/data-access.md` upgraded from `assumed` to `verified` via the Phase 12 docs-delta, or explicitly left open if any file disagrees (§2.5); the cache-key-includes-`save_id` structural test green; the key-space question settled and recorded with an epistemic label; `git ls-files` lists no file containing a Lahman-to-name lookup and `test_no_leaks.py` is green.

**Commit note.** *"Resolve the names.dat join against both answer keys, with the per-save constraint pinned by test."* **This is the plan's decision point.** Tell the operator explicitly which branch fired — the join resolved, or the `players.csv` render-time fallback is now live — because the roster report's shape differs between them and every later phase inherits the choice. This is also the commit that turns the roster from integers into people; the request's observable signal depends on it.

---


### Phase 8 — Contracts, DDL, bronze landing, and the ingest run

**Goal.** Land bronze into the empty `ootp` schema from **one** tracked declaration with **three** consumers, so grain-prose-vs-grain-enforcement drift becomes structurally impossible. The contracts land *before* the loader, so the loader is written against a declared contract rather than the contract being reverse-engineered from the loader.

**Steps.**
1. Complete `contracts/tables.toml` and `field_map.toml` per §2.3(b). Declared keys: `bronze_team` (`save_id`, `sim_date`, `ingest_seq`, `team_id`); `bronze_player` (`save_id`, `sim_date`, `ingest_seq`, `player_id`); `bronze_team_roster` (`save_id`, `sim_date`, `ingest_seq`, `team_id`, `player_id`, `list_id`) — **explicitly not** `(sim_date, player_id)`; `bronze_name` (`save_id`, `sim_date`, `ingest_seq`, `name_space`, `name_index`) with its own declared grain, key and coverage like every other table. Record Decisions §8 here too (ratings render at the 20–80 player-page scale) so the next slice inherits a decision rather than re-deriving one.
2. Declare `historical_id` a **nullable attribute, never a join key** in any serving path. Measured: 1,920 of 18,072 active players carry a non-empty one (10.6%) — `.claude/agents/data-engineer.md:107-109` states the consequence: *"A join on the wrong one silently drops the fictional majority and looks like it worked."* Add a static check over `src/ootp_ai/` asserting no join uses it — and **scope it to `src/` and exclude `tests/`**, because `test_names_join_boston.py` legitimately joins on LahmanID as ground truth and an unscoped guard would block its own validation.
3. `warehouse/ddl.py` emits `CREATE TABLE` and `PRIMARY KEY` **from** the declaration. Every PK column `NOT NULL` (§2.3(d)). Name-bearing tables get `CHARSET=utf8mb4 COLLATE=utf8mb4_bin`.
4. `warehouse/load.py` — bronze is **1:1 with parser output**: typing, casing, dedup only. No joins, no filtering, no semantic renaming (`.claude/agents/data-engineer.md:98-100`). Land **everything** the walk yields including all 259 teams and every minor-league population; the org filter lives in the report layer (Decisions §7). Preserve structural absence as NULL, never zero.
5. `warehouse/ingest_run.py` — **resolve the idempotency collision explicitly.** AC10 requires that loading the same snapshot twice leaves row counts and checksums unchanged, but an append-only ingest-run table adds a row and changes a count, and a wall-clock column breaks bit-identity. **Decision (amended — see §2.3(d)): key `ingest_run` on `(save_id, sim_date, ingest_seq)`.** The two operations are different and must not be conflated:
   - **Re-loading an already-landed `(save_id, sim_date, ingest_seq)` refuses loudly.** That triple is immutable once written. This is what satisfies AC10's four clauses, including *"re-landing an existing snapshot id does not silently overwrite it"* — nothing is ever overwritten, so byte-identity across a repeated load holds trivially.
   - **Taking a *new* snapshot of an already-ingested `sim_date` allocates the next `ingest_seq`** and lands a fresh row set alongside the previous one. This is a legitimate, expected operation — the operator executes a GM action without simming and wants to prove it landed, or a parser fix means re-reading a date already ingested. The first draft's key blocked it.

   `ingest_seq` is allocated by the loader as `max(ingest_seq) + 1` for the `(save_id, sim_date)` pair, starting at 1, **inside the same transaction as the row insert** — computing it in a prior statement races with itself if two loads ever run concurrently, and the failure mode is two row sets silently sharing a key. An implementer who does not notice this whole collision will write a test that cannot pass.

   Columns: source file sizes, SHA-256 digests, header versions, sim date, human team, per-table row counts, residual bytes, wall-clock parse seconds (`time.perf_counter()`, never a naive `datetime` — ruff `DTZ`), and the wall-clock ingestion timestamp as a **tz-aware attribute, never part of the key**.

   **Add one assertion to the grain tests:** two snapshots of the same `(save_id, sim_date)` at different `ingest_seq` both persist, and neither is mutated by the arrival of the other. The immutability claim is only worth making if something is seen to enforce it.
6. `bronze_field_label` (folded-in §5) — each landed field's epistemic label written into the warehouse alongside the data, keyed `(save_id, sim_date, ingest_seq, table_name, column_name)`, so a future incident can ask *"what did we believe about this field the day it landed?"* as a query rather than as archaeology through the git history of `docs/data-access.md`.
7. Add `dump_parse(path)` — a deterministic, key-sorted serialization — so "parsing twice is byte-identical" is testable by hashing.
8. **MAIN THREAD tests.** `tests/test_grain_contracts.py`: the **offline** half (**AC4**) reads the declaration and the emitted DDL and asserts the prose grain sentence equals the emitted key for all four tables, and that every PK column is NOT NULL. The `-m gamedata` half (**AC5**), `test_roster_grain_is_not_player_grain`, **positively asserts** `player_id` is *not* unique within one snapshot's roster rows, and that `count(distinct player_id)` in `bronze_team_roster` is materially less than `count(*)` in `bronze_player` for the same snapshot. `tests/test_withheld_fields.py` (**AC13**, offline) keyed on declared **category**, not column-name globs, **including the negative case** — a synthetic `rating-scouted` field with a proven label *is* renderable — because a guard that blocks everything passes the positive half and delivers nothing. Keep name patterns only as a secondary check, with `talent_%` corrected to `%_talent_%` (the real columns are `batting_ratings_talent_*`; as originally written the pattern matched nothing). Complete `tests/test_snapshot_semantics.py` (**AC10**).

**Acceptance.** AC4 and AC13 green **offline** with no MySQL — these are the contracts CI actually enforces. AC5 and AC10 green under `-m gamedata`. **Mutate the declared `bronze_team_roster` key to `(sim_date, player_id)` locally and confirm `test_grain_contracts.py` goes red; revert.** The `ootp` schema, previously 0 tables, holds exactly the six named tables. `uv run pytest -m "not gamedata"` green with no MySQL running.

**Commit note.** *"Field map declaration + DDL emitter + bronze landing + ingest_run + the five contracts."* Reversibility here is schema-level: dropping the `ootp` tables restores the prior state, and `ops/mysql-bootstrap.sql` recreates the empty schema. This is the first phase requiring a running MySQL, so local and CI signal diverge permanently from here — which is why the contract tests were deliberately written to run offline.

---


### Phase 9 — The parser-vs-export differential harness, and the recorded extraction cost

**Goal.** Prove the parser row-for-row against an independent answer key, **per field by name**. This converts the field map's labels from beliefs into findings, and it must be green before anything is rendered for a GM to read.

**Steps.**
1. `validate/export_diff.py` — parse the probe save, land it under its own `save_id`, and diff against `ootp_truth_real` **inside one MySQL instance**, which is ADR 0004's stated rationale for choosing MySQL at all. Every identifier routes through `quote_ident()`.
2. **Assert provenance first, before any value comparison** (`tests/test_parser_vs_export.py`, `-m gamedata`, **AC6**): the parsed save's sim date is 2024-03-18 and its human team is the Chicago Cubs, matching `ootp_truth_real`. A field diff against a different universe is noise that looks like a finding.
3. Then diff: **zero** row-count and **zero** value differences over the landed field set — 259 teams, 18,072 active players (`retired = 0`), 15,672 `team_roster` rows, 15 leagues. Every mismatch listed **per field by name**; an aggregate pass rate is not acceptable output (Core §18) — it is exactly how a parser reading the adjacent u16 ships green.
4. **Add an explicit structural-absence allowlist.** The export writes `0` where the value is structurally absent (`rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows); our parser lands NULL. Without a **named per-column allowlist, each entry carrying its reason**, a *correct* parse produces 14 false mismatches — and the tempting fix is to make the parser write 0, committing precisely the error `.claude/agents/data-engineer.md:110-112` warns about.
5. Compare strings in Python on decoded `str`, per Phase 7's collation finding.
6. **Document Tier B's limits inside the test**, so a later agent extending the harness to ratings does not inherit false confidence from a green suite: Tier B is **exact** for ids, names, strings, dates, roster lists, team dimension and league config, and **bucketed** for ratings — measured, `players_batting.batting_ratings_overall_contact` has exactly **12 distinct values across 20–80**. The export is display scale and can never be an exact rating validator; a bucketed check can pass a parser reading the *adjacent* u16, which is CLAUDE.md's named correctness trap in its most dangerous form. `players.csv` (Tier A) stays load-bearing permanently.
7. **MAIN THREAD:** `tests/test_extraction_cost.py` (`-m gamedata`, **AC17**) asserts the wall-clock number **exists** and was recorded into the ingest-run row — read it back from the warehouse, not from stdout. **No threshold, no pass/fail on duration** (Decisions §6, an operator ruling: the work takes as long as it needs; the tautology objection is accepted deliberately, on the grounds that a threshold nobody has justified is worse than an honest measurement).
8. Prepare the docs-delta upgrading epistemic labels for **exactly** the fields Tier A or Tier B actually proved — everything else stays `unconfirmed` and therefore withheld by Phase 8's guard.

**Acceptance.** AC6 green with provenance pinned first. **Deliberately corrupt one parsed field and confirm the harness names *that field* in its failure output rather than reporting a percentage; revert.** A differential harness never seen to fail informatively is not yet a harness. AC17 green. `test_withheld_fields.py` still green after the label upgrades.

**Commit note.** *"Differential harness: parser vs the probe-save export, provenance-pinned and per-field."* Route the docs-delta through `/update-docs` in the same unit of work so labels and the code that earned them land together. **If the differential is not green, do not proceed to Phase 10** — a report built on an unvalidated parse is exactly the silent-wrong-data failure the requests README describes.

---


### Phase 10 — The two reports and the rendered-game-data leak guard

**Goal.** Deliver the request's observable signal — a report naming real Boston players — and extend the leak guard to cover it, because this feature is the **first thing in the repo's history that renders OOTP player data to a file**.

**Steps.**
1. `reports/__main__.py` exposing `render`, so that `uv run python -m ootp_ai.reports render` is the real entry point AC14 invokes. Output to `<output_root>/<save_id>/<sim_date>/<ingest_seq>/` per §2.4.
2. `reports/roster.py` — the **configured organization only**, grouped by roster list, carrying position, age, bats/throws and uniform number, with the **club, `sim_date` and the `ingest_seq` it rendered from on line one** so staleness and provenance are visible on sight. The org filter lives here, never at bronze. Honour Phase 7's `list_id` disposition: no human label for a mapping below `inferred`.
3. `reports/standings.py` — 30 MLB clubs by division with W-L-pct-GB. **Expect it to carry no signal:** measured, all 259 `team_record` rows are 0-0-0 and 0 of 12,961 games are played, because both saves sit before opening day. Emit a **structural-absence marker rather than `.000`** for pct when games played is zero.
4. Route **every** report column through `contracts/policy.py::is_renderable()`. There is no second path to the page.
5. **MAIN THREAD:** `tests/test_reports.py` (`-m gamedata`, **AC14**) — the resolved output root is git-ignored, proven by `git check-ignore -q` exiting 0 **and** `git ls-files` listing nothing under it; the roster report contains rows for exactly the configured organization and **zero** belonging to any other; every player row's name matches `^[A-Za-z][A-Za-z .'-]+$` (a name, not an integer); the standings report contains 30 MLB rows grouped by division with W-L-pct-GB columns present; both files carry the club, `sim_date` and `ingest_seq` on line one — the seq clause matters, because once any date has been ingested twice a report that does not name its seq points at a moving target. **Assert standings content structurally, never by value** — asserting a nonzero win total would fail on a *correct* parse, the most expensive kind of wrong test, because it sends the next agent hunting a bug in working code.
6. **MAIN THREAD:** extend `tests/test_no_leaks.py` (folded-in §1). The existing guard bans four filenames and two suffixes at `:106-107`; a Markdown roster sails straight through. Add: the report and catalog output roots resolve to git-ignored paths; and the tracked half of the catalog and field map may name source **files** (`players.dat`) but **never absolute paths** — reuse the existing `PATTERNS` at `:24-28` rather than inventing a second set. ~~Note in a comment the known local-feedback gap...~~ **Amended 2026-08-17: that gap is closed.** The follow-up this step said to file became `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/`, and the guard now enumerates `--cached --others --exclude-standard`, so an untracked artifact **is** visible locally. The function is called `scannable_text_files()` and its enumeration seam is `git_paths()`; do not re-add a comment describing the old limitation. Running the guard after staging is still the habit — `/commit` now says so explicitly — but it is no longer load-bearing for detection.

**Acceptance.** `uv run python -m ootp_ai.reports render` writes both reports; AC14 green on all five clauses; AC13 still green offline including the negative renderable case. Read the roster report by eye once and confirm it contains recognisable Boston names, not integers — an informal check that the name-regex assertion is testing what it claims. `test_no_leaks.py::test_patterns_still_catch_real_leaks` (`:51-78`) still green — *"a guard that has been loosened until it passes is not a guard."*

**Commit note.** *"Render the roster and standings reports, gated by a category-keyed withheld-field guard."* **This is the commit the request exists for** — after it, the GM can name its own players. It is also the natural early-ship point if the slice needs to stop: Phases 11–13 add the catalog and the doc sweep, but the GM can already see its club.

---


### Phase 11 — The generated catalog and its tracked/volatile split

**Goal.** Tell the GM what exists **and what was deliberately withheld and why**, so it prices an action against a known gap rather than discovering it by hitting it. The request's second desired outcome is *"the GM knows what it is not seeing"*, and a catalog of landed tables tells it only what it can see.

**Steps.**
1. `catalog/__main__.py` so that `uv run python -m ootp_ai.catalog` (no subcommand) is the real entry point AC15 invokes. It reads `information_schema` for counts and `contracts/` for grains, keys, coverage and labels — one declaration, three consumers.
2. Split per §2.3(e). Recommended placement: `docs/warehouse-catalog.md` + `docs/warehouse-catalog.json` tracked; the volatile half plus `catalog.json` into the ignored root. **Make the tracked half byte-deterministic**: sorted ordering, no timestamps, no absolute paths, no hostnames, no git-derived values — AC15 asserts byte-identity, and any nondeterminism makes it flap.
3. **Generate coverage statements from counts**, never hand-written (folded-in §3). *"players: 18,072 rows, active only, retired excluded, 1,920 carry an external ID"* is far more useful than a table name and cannot go stale. State how many players carry **no roster row** — computed as `count(bronze_player) − count(distinct player_id in bronze_team_roster)`, roughly 10,700 of 18,072 (free agents, draft-eligible, international, unassigned) — so the GM prices *"who is available"* as a known gap.
4. The **withheld section** names the true-rating tables, `players.prone_*`, `players_value.*` and every still-`unconfirmed` field, each with its reason and its ADR. **No player-level value and no rating column name appears anywhere in the catalog.**
5. Emit `catalog.json` from the same generator (folded-in §4) — one generator, one extra writer.
6. **Add the report-path pointer to the tracked half** (Core §15, SD-11): each report's logical name, the `.env` key and relative path it resolves to, and a one-line spawn instruction the umpires read when handing the GM its reports. **As code spans, never a Markdown link into `var/`** (§2.4). Without this pointer, AC20 is unreproducible by anyone who was not in the room.
7. **Write the spawn contract beside the pointer** (amendment, Decision P16). The pointer says *where the reports are*; it does not say *what the umpire says when handing them over*, and the GM holds only `Read` and `Glob` — so whatever the umpire puts in its context is the entire delivery surface. Record a short fill-in-the-blanks template covering: the **sim date and `ingest_seq`** the attached reports were rendered from, the club, which reports are attached, and the period and action budget in force. This is the umpire's framing message, not an artifact the pipeline generates — it costs nothing, needs no code, and is **free infrastructure under ADR 0016** because it conveys existence and provenance rather than analytical direction.
   > **Deliberately not built: a world-state or "situation" document** carrying record, payroll, roster count and upcoming milestones. That is a **third report**, and the scope rules it out as a non-goal — *"Two is the deliberate 'how thin is thin' setting."* The GM already receives the sim date and its club on line one of both reports, and the standing world (league rules, structure, the action economy) is in its forced-read list. Watching the GM hit the limit of thin sight is the experiment; pre-empting it is not. Revisit only as a scope amendment, on evidence.
7. **MAIN THREAD:** `tests/test_catalog.py` — the **offline** half regenerates the structural section during the test and asserts it is byte-identical to the committed copy (proving it cannot be hand-edited into drift) and contains no rating column name; the `-m gamedata` half asserts every landed table appears with grain sentence, key list, coverage population, row count, source `.dat` file, epistemic label and snapshot date, and that regenerating twice is byte-identical.

**Acceptance.** AC15 green. **Hand-edit one character of the committed structural half and confirm the test goes red; revert** — that assertion exists to fire, and must be seen to. Run the generator twice and diff: zero bytes different, proving determinism rather than luck. `test_doc_links.py` and `test_no_leaks.py` still green.

8. **MAIN THREAD — add `docs/warehouse-catalog.md` to `tests/test_repo_structure.py`'s required-docs list** (`test_required_docs_exist`, the list at `:13-23`). Decision P5: the operator chose the stronger option, so the catalog's *absence* fails CI from here on.
   > **Sequencing, and it is load-bearing.** This test edit must land in **this phase's commit — the same one that adds the generator and the generated file — and not one commit earlier.** `test_required_docs_exist` asserts the file is present on disk; adding the entry before the generator exists turns CI red on every intervening commit, and the failure reads as a broken repo rather than a missing artifact. Add the entry and the file together, or not yet.

**Commit note.** *"Generate the warehouse catalog: tracked structure, generated volume, explicit withheld section."* The tracked-catalog location is **settled** — Decision P5 puts it at `docs/warehouse-catalog.md` + `.json`, using a directory that already exists so CLAUDE.md's ban on speculative directories needs no argument, and it joins the required-docs guard in this same commit.

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
4. File the follow-up the scope named but excluded: ~~the `git ls-files` staging gap in `test_no_leaks.py`~~ **(already filed and FIXED 2026-08-17 as `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/` — do not file it again)**, and the GM tool-grant guard test (Decisions §11 — `.claude/agents/gm.md` grants exactly `Read, Glob` and nothing under `tests/` asserts it).
5. **USER-RUN — the Challenge-mode spot-check** (amendment, §2.5 channel 4). This is the closest thing `OOTP-AI.lg` can have to AC6's differential, which cannot run there because Challenge Mode has no export. The operator samples **at least 20 players across at least 5 clubs** — including at least one minor-league affiliate and at least one fictional player with no `historical_id`, since those are the rows Tier A cannot reach — and confirms against the game's own screens: name, position, bats/throws, uniform number, age/DOB, club, and roster-list membership. Then at least 5 teams: city, nickname, abbreviation, division, and W-L. **Sample by `player_id`, not by name** — `docs/data-access.md` §7 records that OOTP's internal ids are embedded in report hrefs (`player_47035.html`, `team_3.html`), so the operator can tie a screen to a warehouse row with no ambiguity, and a same-named player cannot produce a false match. **Ratings are not part of this check and never will be** (§2.5). Record the sample and the result in `IMPLEMENTATION_REPORT.md`; a mismatch is a data incident, not a test failure, and files as one.

**Acceptance.** The GM handoff meets AC20's bar. The operator's by-hand check shows zero changes. One ledger row appended in the documented schema. **One** follow-up request filed — the GM tool-grant guard test; the leak-guard one was filed and fixed on 2026-08-17. Final green on all four commands.

**Commit note.** *"USER-RUN acceptance recorded, umpire ledger row appended, follow-ups filed."* **Do not mark the request `implemented` on the acceptance panel's word alone** — AC20 and AC21 are explicitly the operator's, and `requests/feature-requests/README.md` requires human-only criteria be marked USER-RUN precisely so the panel does not claim them. Move the slug to `_done/` only after both come back green.

---


## 4. Testing & verification



### 4.1 The split, and why it is the most important testing decision here

CI runs exactly four commands (`.github/workflows/ci.yml`): `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -m "not gamedata"`. CI has **no** OOTP install, **no** save and **no** MySQL, and must never have any of them (ADR 0006). Therefore:

- **A phase proved only by `gamedata` tests has zero CI signal** — a later change can break it and nothing goes red until someone runs the local suite.
- **A phase proved only by offline tests has zero contact with reality.**

So every phase carries at least one of each wherever the subject allows. That is why Phases 5 and 6 add synthetic-buffer walker tests alongside their real-save tests, why the contract tests in Phase 8 were designed to compare two *artifacts* rather than query a database, and why AC15's byte-identity clause is recommended for de-marking.

**Offline (CI-enforced):** `test_config.py`, `test_db_identifiers.py`, `test_save_header.py`, `test_sequential_walk.py`, `test_no_fixed_offsets.py`, `test_parse_teams_synthetic.py`, the offline half of `test_grain_contracts.py`, `test_withheld_fields.py`, the offline half of `test_catalog.py`, plus the four pre-existing guards.

**Gamedata (local only):** `test_save_enumerator.py`, `test_read_only.py`, `test_snapshot_semantics.py`, `test_byte_accounting.py`, `test_names_join.py`, `test_names_join_boston.py`, the per-save names test, `test_parse_real_save.py`, `test_parser_vs_export.py`, `test_extraction_cost.py`, `test_reports.py`, and the gamedata halves of `test_grain_contracts.py` and `test_catalog.py`.

### 4.2 Four validation tiers, each doing a different job

- **Tier A — `players.csv`.** Exact, raw ~1–1000 scale, shipped real players only. The *only* exact rating validator, and — because it carries `FirstName`/`LastName`/`LahmanID` — a **name** validator for **our** league via the `historical_id` join. It is the only tier that touches `OOTP-AI.lg`.
- **Tier B — the probe-save export in `ootp_truth_real`.** Exact for ids, names, strings, dates, roster lists, team dimension and league config. **Bucketed for ratings** and therefore never a rating validator (12 distinct values across 20–80).
- **Tier C — byte accounting.** Strict (zero residual) for `teams.dat` and `names.dat`; diagnostic for `players.dat`. The only check that works on fields with **no** ground truth at all, which is why it earns its place.
- **Mechanical guards.** The AST fixed-offset scan, the category-keyed withheld-field guard, the read-only proof, the `historical_id`-is-not-a-join-key scan, the `quote_ident` regression, the extended leak guard.

### 4.3 Two anti-vacuity rules, both learned from findings in the scope

1. **Every differential test enumerates mismatches per field by name.** An aggregate pass rate is exactly how a parser reading the adjacent u16 ships green.
2. **Any test whose ground truth may be unreachable must skip loudly with a named reason, never pass.** A vacuous green on `test_names_join.py` is worse than a red one. Verify the skip path by temporarily unsetting the truth-database key.

### 4.4 Five guards that must be *seen* to fail

A guard nobody has observed failing is decoration. Break each once, at its own phase boundary, confirm red, revert:

| Phase | Break this | Must go red |
|---|---|---|
| 3 | Add `f.seek(128)` to a parser module | `test_no_fixed_offsets.py` |
| 3 | The in-module fixed-offset negative control | `test_sequential_walk.py` |
| 8 | Change `bronze_team_roster`'s declared key to `(sim_date, player_id)` | `test_grain_contracts.py` |
| 9 | Corrupt one parsed field | `test_parser_vs_export.py` — **and it must name that field** |
| 11 | Hand-edit one character of the committed structural catalog | `test_catalog.py` |

### 4.5 Regression safety and sequencing

From Phase 5 onward, **every** phase's acceptance re-runs `test_read_only.py` and `test_no_fixed_offsets.py`. The first is ADR 0001, the one unrecoverable failure in the project; the second is the silent-corruption class CLAUDE.md names as the most likely way to corrupt every downstream recommendation. Checking both at every checkpoint costs seconds and is the difference between finding a violation at a 46 MB copy and finding it after a full parse.

**Every filesystem-touching test runs against the disposable Challenge Mode probe first, and only then against `OOTP-AI.lg`** (SD-20). An identical-mode disposable save sits beside the irreplaceable one; pointing untested code at the managed league first is avoidable exposure. Encode the ordering *in the test modules*, not as prose.

The four pre-existing guards are in the offline suite and therefore re-run at every phase automatically; two of them get **extended rather than replaced** (`test_no_leaks.py` gains the rendered-game-data assertions; the `gamedata` marker declaration is widened rather than duplicated).

### 4.6 What no test here covers — stated so nobody mistakes green for complete

Ratings are entirely outside the tested surface; Phase 2 returns a verdict, not a parser. Tier B can never be an exact rating validator. Standings content is asserted structurally only, because a nonzero-win assertion would fail on a correct parse. Full byte accounting on `players.dat` is diagnostic, not strict. And `world.dat` remains unmapped with no Challenge Mode ground truth — which is why the league-config diff is gated out of this slice.

---


## 5. Decisions

The scope's eleven disposed Decisions carry forward unchanged and are not restated here —
read them in `requests/feature-requests/first-sight/PROJECT_SCOPE.md` §Decisions. The
decisions **this stage** added or settled:

| # | Decision | Rationale |
|---|---|---|
| P1 | **Phase order: pivot rule → config/deps → spike**, not spike literally first | Scope Core §1 says "spike first"; AC18's actual constraint is that a verdict is committed before any *ratings* code exists, and this slice contains none. Running the spike after the config layer avoids hardcoding paths in the very first artifact, which would violate Core §2. *Operator-disposed.* |
| P2 | **`save_id` is the save directory stem** (`OOTP-AI`), `VARCHAR(64) NOT NULL`, validated against `^[A-Za-z0-9_-]+$` | Stable, human-readable, already public in `gm/` documents. The regex does double duty: it makes it structurally impossible for an absolute path to become a `save_id` and leak into a tracked catalog. **Changing this later re-keys every bronze table.** *Operator-disposed.* |
| P3 | **First runtime dependencies: `PyMySQL` + `types-PyMySQL`**, and `python-dotenv` moves from the dev group into `[project].dependencies` | Pure Python (no C toolchain on Windows), MIT like this repo, maintained stubs — which matters because mypy runs `strict` over `src`. `mysqlclient` has no maintained stubs; `mysql-connector-python` is Oracle GPLv2-with-FOSS-exception. *Operator-disposed.* |
| P4 | **Restore players-before-names ordering** (blocker MERGE-03) | The merged phases were mutually blocking. The code-grounded planner ordered players first *deliberately*, so the brute-force index search had real records to search. AC9's display-name clause moves into the names phase. *Operator-disposed.* |
| P5 | **The tracked catalog lands in `docs/`, AND joins `tests/test_repo_structure.py`'s required-docs list** | Uses a directory that already exists, so no speculative-directory argument is needed, and the guard makes its absence fail CI. **Sequencing consequence, load-bearing:** the required-docs entry must land in the *same commit* as the generator that produces the file (Phase 11) — adding it earlier turns CI red on every intervening commit. *Operator-disposed; the operator chose the stronger option over the recommendation.* |
| P6 | **Split AC15's byte-identity clause to run offline in CI** | It derives from the tracked declaration alone and needs neither a save nor a database. This strictly *increases* what CI enforces rather than weakening the scope. *Accepted en bloc.* |
| P7 | **The report/catalog output root is a third new `.env` key** | Matches the resolve-by-name convention rather than hardcoding a subdirectory of the snapshot root. Core §19 budgeted two keys; this is the third. *Accepted en bloc.* |
| P8 | **Standing-orders entries land with an explicit engineering-owned marker where the ledger seq goes** | `gm/standing-orders.md:45` requires `**Established:** ledger seq <n>`, and the seq does not exist when Phase 12 writes the entries — the ledger row is an umpire act performed after delivery (Decisions §2, blocker SD-03). *Accepted en bloc.* |
| P9 | **On an ABSENT spike verdict, file the follow-up request immediately** rather than deferring it until a ratings slice is proposed | A FAIL on the mechanic behind ADRs 0012/0014/0016 is exactly the finding that should not go quiet. *Accepted en bloc.* |
| P10 | **`is_renderable()` splits into two rules** (blocker EX-02) | As drafted, a single gate blocking every `unconfirmed` field made the plan's *own* pre-registered `list_id` fallback unreachable — that fallback renders a field labelled `unconfirmed` by design. The implementer's cheapest escape would have been to quietly upgrade the label, the exact error the discipline exists to prevent. See §2 seam (c). |
| P11 | **`bronze_name` is keyed `(save_id, sim_date, ingest_seq, name_space, name_index)`** | It is genuinely unknown whether `names.dat` carries one index space or two. That key is correct under **both** outcomes and costs one column; the alternative silently collides every row if the answer is two. |
| P12 | **`ingest_run` is keyed `(save_id, sim_date, ingest_seq)`; re-loading an existing triple refuses loudly, a new snapshot of an existing `sim_date` allocates the next seq** | Resolves a real collision: AC10 demands byte-identity across a re-load, but an append-only ingest table adds a row and a wall-clock column breaks it. An implementer who misses this writes a test that cannot pass. |
| P13 | **`ingest_seq` joins every bronze primary key, and `snapshot_date` is renamed `sim_date` throughout** | *Amendment, operator-directed after the first commit.* The plan used two names for one value and never said they were the same; there is one date and it is the in-game sim date. `ingest_seq` exists because keying on `(save_id, sim_date)` alone **blocks a legitimate operation** — snapshotting after an executed GM action on a date that has not advanced, or re-landing after a parser fix. It preserves append-only immutability rather than trading it away, and makes the pre-action and post-action states of one sim date both retrievable — evidence this project specifically exists to collect. See §2.3(d). |
| P14 | **Development lands into a separate `ootp_dev` schema; `ootp` is production** | Isolation was by `save_id` **column** alone, so a `SELECT` that forgot it silently mixed universes. `MYSQL_DATABASE` is already an `.env` key, so the split costs one env value and zero code. *Amendment.* |
| P15 | **`Test Save - Challenge Mode.lg` is the primary development target, and cross-mode format equivalence is proven by test rather than assumed** | It is a structural twin of production — same club, same mode, identical file set, disposable and simmable. And the risk this project cannot afford is a parser that works on the save we develop against and breaks on the save we manage. See §2.5. *Amendment.* |
| P17 | **In-game screens are a fourth validation channel for Challenge-mode saves, valid for every field this slice lands and permanently banned for ratings** | *Amendment.* The first draft treated Challenge Mode as validatable only by construction. But the operator can open any screen and build custom in-game reports, and **none of the fields this slice lands is scale-converted or scout-filtered** — a uniform number is 34 on the screen and 34 in the bytes. Ratings stay banned as ground truth for the unchanged reason (two lossy transforms, wrong field identified with no error surfaced). Safe because the operator is not the GM: `FRONT_OFFICE.md:83`. Concretely, it settles the `list_id` enum in minutes instead of by inference. See §2.5. |
| P16 | **A written spawn contract, not a world-state artifact** | The umpire's framing message (sim date, club, which reports are attached, the action budget) is free infrastructure under ADR 0016. A richer "situation" document would be a **third report**, which the scope rules out as a non-goal — the thin-sight tension is what the experiment tests. *Amendment; the richer artifact was considered and deliberately rejected.* |

**Informational, recorded not re-litigated:** `bronze_name` re-lands ~264,095 rows per save
per snapshot even though `names.dat` is fixed-size and probably immutable for a save's
lifetime. The scope decided `sim_date` goes in every primary key, so this plan honours
that and records the per-snapshot digest in the ingest run, so a later slice can prove
immutability and de-snapshot it cheaply. Also: the panel brief named `docs/data-sources.md`,
which **does not exist** — `docs/` holds `data-access.md` and `league-rules.md`. This plan
treats `docs/data-access.md` as intended.

## 6. Risks & gotchas



Ordered by expected cost, not by likelihood.

1. **`bronze_name`'s key space is unresolved and is this plan's most likely silent-wrongness bug.** Nobody has established whether `names.dat` carries one monotonic index space or two. If it is two and the DDL keys on `(save_id, sim_date, ingest_seq, name_index)` without a `name_space` discriminator, the spaces collide and every collided row is silently wrong, with nothing throwing. **Mitigation:** Phase 6 measures it before any DDL is written, and the declared key carries a `NOT NULL` `name_space` discriminator that is correct under both outcomes for the price of one column.

2. **The `names.dat` join is the largest single unknown and sits on the critical path of the headline report.** `docs/data-access.md:238` has the encoding and table layout `unconfirmed`; a roster of integers is not a roster report. **Mitigation:** brute-force against a *full* answer key (score every candidate u32 position across all 18,072 probe players) is bounded and either converges on ~100% or fails cleanly; the pre-registered `players.csv` render-time fallback resolves the ~1,712 Lahman-carrying players with nothing tracked; and the phase is sequenced *before* the players walk so the branch fires at a clean checkpoint rather than mid-report.

3. **`names.dat` content is per-save, and the failure is silent-wrong rather than a crash.** Identical 8,642,110-byte size across three saves, three different SHA-256 digests. A cached probe table applied to the managed league renders plausible wrong names into the GM's roster report. **Mitigation:** the resolver's cache key includes `save_id`, enforced by a structural test rather than by a data coincidence.

4. **The collation default already on disk defeats "exact" string comparison.** `ops/mysql-bootstrap.sql` creates all schemas `utf8mb4_0900_ai_ci` — accent- *and* case-insensitive — while AC7 and AC8 demand exact equality, in a repo whose export was deliberately configured with *Replace accents* Off so names would survive validation. **The failure looks like a pass.** **Mitigation:** compare decoded `str` in Python, or `COLLATE utf8mb4_bin` explicitly, and assert the choice in the test.

5. **The export writes `0` for structural absence on 14 non-MLB league rows.** Without a named per-column allowlist, a correct parse produces 14 false mismatches, and the tempting "fix" commits the exact error the rulebook warns about — wrong numbers, not incomplete ones.

6. **AC10's four clauses collide with an append-only `ingest_run`.** An implementer who does not notice will write a test that cannot pass. Resolved in Phase 8 by keying on `(save_id, sim_date, ingest_seq)`: re-loading an existing triple refuses loudly, while a *new* snapshot of an already-ingested `sim_date` allocates the next seq and lands alongside. **The seq allocation must happen inside the insert's transaction** — computed separately it races with itself, and the failure is two row sets silently sharing a key.

7. **`tests/` is the first entry in the builder's deny set.** Hand a phase's whole spec to the data-engineer subagent and its documented behaviour is to stop and report — an Escalation and **zero tests**, costing a whole phase. **Mitigation:** state the ownership split in the *spec*, not only in the plan.

8. **mypy runs strict over `src` *and* `tests`, and no runtime dependency has been chosen.** An unstubbed driver blocks the entire build at the first import; `python-dotenv` sitting dev-only breaks a non-dev install. Settle both in Phase 1, not at Phase 8 with the loader half-written.

9. **Ruff's already-selected rules bite parser code specifically.** `A` forbids `id`/`type`/`bytes`/`list`/`format` as names — all natural in a record walker. `DTZ` makes any naive datetime an error. `PTH` bans `os.path`. None is hard; each is a surprise mid-phase.

10. **Strict byte accounting on `teams.dat` is asserted by the scope, not evidenced.** The only `verified` teams.dat knowledge is the 5-string signature and ARGB colors; `docs/data-access.md:228` covers the rest of a 5.3 MB file as `unconfirmed`. **Mitigation:** the demotion is pre-registered in Phase 0 — do not let a research task gate the request's observable signal.

11. ~~**The `players.dat` population is an inference presented as fact.**~~ **Measured 2026-08-17 in Phase 6a, and the inference was wrong.** The file holds **18,077** records against the export's **18,072**; five records exist that the export does not carry at all. The risk was real and it fired — AC12 and Phase 11 must use the file's count, not the export's, or a correct parse goes red. Both numbers are now pinned separately in `tests/test_byte_accounting.py`. A second premise fell with it: `players.dat` declares `0xFFFFFFFF` where `teams.dat` declares a record count, so this walk has no in-file oracle at all.

12. **`list_id` value semantics are undocumented and sit on the headline report's critical path.** A wrong human label produces a confidently wrong roster with nothing throwing. Pre-registered opaque-integer fallback.

13. **A bucketed ground truth can green-light a parser reading the adjacent field.** Deferred rather than mitigated: this slice lands no ratings, which is precisely why the scope decoupled them. Keep it that way, and keep Tier A as the permanent exact validator.

14. **The doc-link guard is live-broken in a way this feature's own artifacts trip.** Code spans everywhere; nothing links into `var/`. Do not fix it here — an open bugfix request owns it.

15. ~~**The leak guard is blind to unstaged files.**~~ **Fixed 2026-08-17** — the structural fix this risk asked to be filed as a follow-up landed as `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/`. `tests/test_no_leaks.py` now enumerates `--cached --others --exclude-standard`, so it sees a rendered report before it is staged. The residual risk is unchanged and still worth naming: **this feature is the first to render OOTP player data to a file**, so the exposure is new. The guard covers machine paths, home directories and email addresses — it does **not** scan for credentials, and nothing else does either.

16. **`.gitignore`'s `*.dat` rule does not protect `tests/fixtures/`.** Verified: `!tests/fixtures/**` negates it and git's last-match-wins, so only `test_no_leaks.py:107` stops a committed `.dat` fixture — as a red build. Build fixtures as byte-builder *functions*.

17. **The standings report carries no information today**, and asserting otherwise fails on a correct parse.

18. **Reports regenerate in place unless partitioned** (SD-21) — mitigated at zero cost by the snapshot-dated output path, but note the residual: the tracked catalog's pointer names the *pattern*, not a dated path.

19. **Nobody has run any of this code.** Every cost estimate in the scope is `unconfirmed`, and Phases 5, 6 and 7 each contain a genuine research task. Decisions §6 removes the wall-clock threshold entirely, and each research task carries a pre-registered fallback, so a hard phase **degrades rather than blocks**.

20. **A degraded checkpoint is tempting and wrong.** Merging Phases 5–7 into one "parser" phase because they share a walker pattern means a failure in `players.dat` blocks a green, provable `teams.dat`. Three checkpoints cost three commits and buy three independently revertible units.

---



## 7. Files to touch (checklist)

> **Correction applied (blocker MERGE-02).** The panel's merged list concatenated three
> proposals without reconciliation, naming the same module twice under conflicting paths —
> `primitives.py` *and* `cursor.py`, `load.py` *and* `loader.py`, `rosters.py` *and*
> `roster.py` — plus seven pure duplicates with different change descriptions. Handing that
> to the builder yields two cursors and two loaders, or an Escalation. Below is the single
> deduped list, keyed to the architecture map. **One entry per path, each with an owner.**

**Builder-owned — `src/ootp_ai/**` only.** This is the subagent's entire declared target set.

- [ ] `src/ootp_ai/config.py` · `saves.py` · `snapshot.py` · `ingest.py` · `db.py`
- [ ] `src/ootp_ai/parser/primitives.py` — the forward-only `Cursor`; **no `seek`, no absolute read**
- [ ] `src/ootp_ai/parser/header.py` · `errors.py` · `saved_games.py`
- [ ] `src/ootp_ai/parser/teams.py` · `players.py` · `rosters.py` · `names.py`
- [ ] `src/ootp_ai/contracts/tables.toml` · `field_map.toml` — **tracked declarations**
- [ ] `src/ootp_ai/contracts/loader.py` · `policy.py`
- [ ] `src/ootp_ai/warehouse/sql.py` · `ddl.py` · `load.py` · `ingest_run.py`
- [ ] `src/ootp_ai/validate/export_diff.py`
- [ ] `src/ootp_ai/reports/__main__.py` · `roster.py` · `standings.py`
- [ ] `src/ootp_ai/catalog/__main__.py` · `generate.py`
- [ ] `src/ootp_ai/__init__.py` — replace the docstring, false from Phase 3 onward

**Main-thread-owned — every path below is in the builder's deny set or is a guard.**

- [ ] `tests/fixtures/synthetic.py` — byte builders as **functions**, never `.dat` files
- [ ] `tests/test_save_header.py` · `test_sequential_walk.py` · `test_no_fixed_offsets.py`
- [ ] `tests/test_cross_mode_format.py` — **amendment**; built across Phases 3, 5, 6 and 7
- [ ] `tests/test_config.py` · `test_db_identifiers.py` · `test_save_enumerator.py`
- [ ] `tests/test_read_only.py` · `test_snapshot_semantics.py` · `test_byte_accounting.py`
- [ ] `tests/test_parse_teams_synthetic.py` · `test_parse_real_save.py`
- [ ] `tests/test_names_join.py` · `test_names_join_boston.py`
- [ ] `tests/test_grain_contracts.py` · `test_withheld_fields.py`
- [ ] `tests/test_parser_vs_export.py` · `test_extraction_cost.py`
- [ ] `tests/test_reports.py` · `test_catalog.py`
- [ ] `tests/test_no_leaks.py` — **extend**, do not rewrite; reuse the existing `PATTERNS`
- [ ] `tests/test_repo_structure.py` — add the catalog to required-docs **in Phase 11 only** (P5)
- [ ] `pyproject.toml` — widen the marker **first**; deps; update the comment at `:11-15`
- [ ] `.env.example` — three new keys; retire `MYSQL_TRUTH_OSA_DATABASE`; all values empty
- [ ] `ops/mysql-bootstrap.sql` — drop the `ootp_truth_osa` create and grant
- [ ] `docs/warehouse-catalog.md` + `.json` — generated, tracked, byte-deterministic
- [ ] `docs/data-access.md` · `docs/league-rules.md` · `docs/decisions/0004-mysql-warehouse.md` — **via `/update-docs` only**
- [ ] `gm/standing-orders.md` — the engineering-owned report kind + two entries (umpire edit)
- [ ] `README.md` · `CLAUDE.md` · `gm/charter.md` — status text, false on delivery
- [ ] this request's `IMPLEMENTATION_REPORT.md` + the track Index row — the stage-4
      artifact, fenced here because it does not exist until Phase 12 writes it and
      `tests/test_doc_links.py` now resolves bare `requests/...` tokens:

      ```
      requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md
      ```

## 8. Conventions (bake these in)

- **The game is read-only.** No save writes, no roster-import files, no UI automation, no
  export triggered against `OOTP-AI`. Every handle `"rb"`. One write to a Challenge Mode
  save is unrecoverable and there is no backup upstream.
- **Walk sequentially; never seek to a fixed offset.** Enforced structurally (a cursor with
  no `seek`) *and* mechanically (an AST scan over the whole parser tree, zero exemptions).
- **Ground truth is `players.csv` and the probe-save export — never an in-game display.**
  A field mapping with no validating test is `unconfirmed` and must say so.
- **An unclassifiable field is treated as a true rating and withheld.** "Probably fine" is
  not a classification.
- **No OOTP game data in git, at any size, for any reason.** Every offline fixture is a
  synthetic byte sequence we authored. `tests/test_no_leaks.py` catches `players.csv` by
  **filename only** — a renamed derived copy sails straight through.
- **Paths resolve from `.env`.** No literal path, no `parents[N]` walk outside test modules.
- **Commits go through `/commit` only.** Never `git commit` ad hoc, never `--amend`, never
  `--no-verify`, never a push to `main`, never a force-push. Ask before merging the PR.
- **Subagents get read-only git** and must never `checkout`/`reset`/`restore`/`clean`/`stash`.
- **Ruff will bite early:** `A` bans `id`/`type`/`bytes`/`list`/`format` as names — all
  natural in a record walker; `DTZ` makes any naive datetime an error; `PTH` bans `os.path`.

## 9. Data contracts touched

Four bronze tables, each declaring its grain in `contracts/tables.toml` and proving it in
`tests/test_grain_contracts.py` — the same declaration emitting the DDL, so prose and
enforcement cannot drift.

| Table | Grain | Key |
|---|---|---|
| `bronze_team` | one row per team per save per snapshot | `save_id, sim_date, ingest_seq, team_id` |
| `bronze_player` | one row per player per save per snapshot | `save_id, sim_date, ingest_seq, player_id` |
| `bronze_team_roster` | one row per player per team per **roster list** per save per snapshot | `save_id, sim_date, ingest_seq, team_id, player_id, list_id` |
| `bronze_name` | one row per name-table entry per save per snapshot | `save_id, sim_date, ingest_seq, name_space, name_index` |

**Keys.** `player_id` is the only universal key. `historical_id` is a **nullable attribute,
never a join key** — measured, 1,920 of 18,072 active players carry one (10.6%), so a join
on it silently drops the fictional majority and looks like it worked. A static check asserts
no join in `src/` uses it, **scoped to exclude `tests/`** — `test_names_join_boston.py`
legitimately joins on `LahmanID` as ground truth.

**Coverage.** Bronze lands everything the walk yields — all 259 teams and every
minor-league population; filtering at bronze is forbidden. The org filter lives in the
report layer. `bronze_team_roster` covers **7,370 distinct players, not 18,072**: ~10,700
active players (free agents, draft-eligible, international, unassigned) carry **no roster
row at all**, which the catalog states explicitly.

**Structural absence is preserved as NULL, never zero.** The export writes `0` for
`rules_active_roster_limit` and the service-time columns on all 14 non-MLB league rows —
14 separate chances to commit this error, and the differential harness carries a named
per-column allowlist so a *correct* parse does not produce 14 false mismatches.

**Update semantics.** Append-only; nothing is ever overwritten. Re-loading an existing
`(save_id, sim_date, ingest_seq)` refuses loudly, while a **new** snapshot of an
already-ingested `sim_date` allocates the next `ingest_seq` and lands alongside its
predecessor — so the pre-action and post-action states of a single in-game date are both
retrievable. Reports resolve to `max(ingest_seq)` by default and state which seq they read.

**Layer pattern.** Parser + warehouse for everything here (ADR 0005). Nothing in this
request is static reference data, so no `datasets/` entry and no builder.

**Extraction cost.** Measured and recorded into the ingest-run row and the catalog. **No
threshold** — the operator ruled the work takes as long as it needs.

## 10. Code-grounding verification

The panel submitted **104 code references** for grounding. Two code-grounded adversaries
verified them against the real repo and returned 42 findings, so the lens did not degenerate
into a vacuous clean bill.

**Independently re-verified by the main thread before this plan was written** — six
citations sampled at random, all six resolving exactly as claimed:

| Cited reference | Verified |
|---|---|
| `.claude/agents/data-engineer.md:55-58` | ✅ "one write destroys the league irreversibly, and there is no backup upstream" |
| `.claude/agents/data-engineer.md:69-74` | ✅ the ban, with the measured "43 bytes from one anchor in one save and 107 in another" |
| `.claude/agents/data-engineer.md:98-104` | ✅ bronze 1:1; silver states grain in prose *and* enforces it |
| `.claude/agents/data-engineer.md:150-156` | ✅ deny set: `tests/`, `.github/`, `ops/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md`, `docs/decisions/` |
| `gm/standing-orders.md:42-50` | ✅ the format block requiring `**Established:** ledger seq <n>` and `**Owner:** the analyst who produces and refreshes it` |
| `.gitignore:61` | ✅ `!datasets/**` carve-out for a directory that does not exist |

**Corrections applied to the panel's draft:** F01 (absolute paths → repo-relative,
everywhere), EX-02 (the single serving gate split in two — see §2 seam (c) and Decisions
P10), MERGE-02 (`files_to_touch` deduped against the architecture map), MERGE-03 (phases 6
and 7 reordered — see §3).

> **Panel degradation, recorded honestly.** The structured merge **failed** — it exceeded
> the 64,000 output-token maximum — and the panel recovered via its fallback. Planners,
> adversaries and the meta-audit all returned in full (3/3, 2/2, 1/1), and the free-text
> synthesis carrying the converged 14-phase plan survived intact; this document is written
> from it. But `convergence_map` and `gated_decisions` came back **empty**, and six of the
> nine blockers are consequences of that failure rather than defects in the planners'
> thinking. **Empty convergence here is a degradation artifact, not evidence the planners
> disagreed.** The gate content was recovered from the synthesis's own operator-questions
> section. If this plan proves thin in execution, that is where to look first.

## References

- `requests/feature-requests/first-sight/PROJECT_SCOPE.md` — the decided upstream artifact
- `requests/feature-requests/first-sight/FEATURE_REQUEST.md` — the problem statement
- `requests/feature-requests/first-sight/reviews/plan-proposals.md` — the three planners' raw proposals **and the recovered free-text merge in full**
- `requests/feature-requests/first-sight/reviews/plan-adversarial.md` — 62 findings, the meta-audit, and all 104 submitted code references
- `.claude/agents/data-engineer.md` — the build rulebook and the deny set
- `docs/data-access.md` · `docs/league-rules.md` — the format beliefs and the rule environment
- `docs/decisions/` — 0001, 0002, 0003, 0004, 0005, 0006, 0012, 0016 bind this feature directly
