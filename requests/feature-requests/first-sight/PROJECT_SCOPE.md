> **Status:** scoped · created 2026-08-16 · decided · next: plan

# Project Scope — First sight: land the club and tell the GM what else exists

> **Citations in this document use code spans, not Markdown links, wherever they
> carry a `file:line` suffix or point into `var/`.** Both forms fail
> `tests/test_doc_links.py` today — a live defect with an open bugfix request
> ([doc-link-guard-mismatch](../../bugfix-requests/_done/doc-link-guard-mismatch/)).
> Keep that convention until it is fixed.

## Fit Verdict

**Reshape** — and the reshape is about *sequencing and honesty*, not about whether
the work belongs here. It belongs here beyond argument:

- [`gm/charter.md`](../../../gm/charter.md) states the charter cannot be written
  because the GM has no warehouse and no reports.
- [ADR 0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md) calls
  the report-channel bootstrap severe.
- [ADR 0014](../../../docs/decisions/0014-staff-is-the-information-channel.md)'s
  own Costs section pre-authorises this exact deliverable: *"A warehouse that can
  name the roster but cannot say how good anyone is is a real possible first
  milestone."*
- Nothing duplicates it. `src/ootp_ai/` is a single `__init__.py` holding a version
  string; `transform/`, `build/` and `datasets/` do not exist; the `ootp` MySQL
  schema exists with **0 tables** (measured 2026-08-16).
- [ADR 0005](../../../docs/decisions/0005-hybrid-data-layer.md)'s boundary rule —
  *does this change when the league is simulated?* — routes every artifact here to
  the parser + warehouse side.

It is `reshape` rather than `clean` on four grounds. **Three were measured during
the panel, not inherited from the request.**

**1 — One of the two headline deliverables carries no information today.**
`select distinct g, w, l from ootp_truth_real.team_record` returns exactly one row:
`0, 0, 0`, across all 259 teams. `select count(*) from ootp_truth_real.games where
played = 1` returns **0** against 12,961 scheduled games. `saved_games.dat` puts `OOTP-AI` at 2024-03-07 and the probe save
at 2024-03-18, both before opening day. The standings report is 30 rows of 0-0. It
still ships, because the request asks for it and the team/division dimension lands
regardless, but **its acceptance asserts structure, never content**, and playoff
seeds are gated until the league sims.

**2 — Desired Outcome 3 rests on a file that does not exist.**
`docs/league-rules.md:129` and `:295` both assert a `leagues.dat`. `OOTP-AI.lg`
holds 18 `.dat` files and none is it. Two of three scopers inferred the config
therefore lives in `teams.dat`; the third located it correctly. Measured: the string
`major_league_ml_c_2024.lsdl` — exactly the `schedule_file_1` value
`docs/league-rules.md:80` records — sits at **byte 5,559,751 of `world.dat`**,
surrounded by league-shaped records containing `World Series`, `AL` and `NL`. It
does not appear anywhere in `teams.dat`. So §1 verification means reverse-engineering
an unmapped 8.9 MB fifth binary, with **no export of our Challenge Mode league to
diff against**. The guaranteed doc correction stays core; the ~30-scalar diff is gated.

**3 — The slice coupled itself to the project-threatening unknown for no gain.**
The request's Scope Signals put *"enough of `scouting.dat` to classify
true-versus-scouted"* in scope, which makes shipping **anything** conditional on
Open Question 1. But the roster report needs names, positions and roster membership;
the standings report needs W-L. Neither needs a single rating. Decoupled, the
request's own observable signal survives a FAIL verdict on the spike.

**4 — The medallion forces an open ADR as a convenience.**
[ADR 0004](../../../docs/decisions/0004-mysql-warehouse.md) §Notes records that
`dbt-mysql` caps at 1.7.0, pinning `dbt-core~=1.7.0` four minor versions behind;
that options 3 or 4 are *"likely correct on the evidence"*; and that *"the decision
comes due when the first dbt model is requested."* `pyproject.toml` deliberately
carries no transform group. Building three medallion layers to serve two reports
forces the most expensive event in this repo — an ADR re-litigation — as a
side-effect.

## Problem

The GM subagent exists, holds exactly two tools (`Read`, `Glob` — see
[`.claude/agents/gm.md`](../../../.claude/agents/gm.md) front matter), and can decide
nothing about the baseball club it runs. It can read `FRONT_OFFICE.md`, its charter,
the ledger and the league rules. It cannot name one player on its roster. Asked who
plays second base, it must answer that it does not know.

The facts are all sitting in `OOTP-AI.lg`: `players.dat` at 32,070,106 bytes,
`teams.dat` at 5,318,831, `names.dat` at 8,642,110, `scouting.dat` at 2,863,744
(measured 2026-08-16). No line of code in this repo reads a byte of any of them.

There is a second, quieter problem. Every value in `docs/league-rules.md` §1 was
measured from the league-creation screens and a throwaway probe save, not from
`OOTP-AI.lg`. Challenge Mode hides the export
([ADR 0003](../../../docs/decisions/0003-challenge-mode-league.md),
`docs/data-access.md` §6), so nothing confirms our club is configured the way we
believe it is.

## Goals / Non-Goals

**Goals**

1. **Give the GM its roster.** A Markdown report naming the Boston organizational
   roster with **real names** — grouped by roster list, carrying position, age,
   bats/throws and uniform number, with `snapshot_date` and sim date on line one so
   staleness is visible on sight. This is the request's observable signal and the
   single thing that turns the GM from mute to functional.
2. **Give the GM the menu.** A catalog generated from `information_schema` plus the
   tracked contract declaration — never hand-written — describing every landed
   table's grain, key, coverage population, row count and snapshot date, **and
   naming what was deliberately withheld and why**, so the GM prices an action
   against a known gap rather than discovering it by hitting it.
3. **Establish the parser's spine once, correctly.** Config resolved from `.env`
   only; a save enumerator that confirms `players.dat` *and* `teams.dat` exist
   rather than trusting a `*.lg` glob; a header/version guard that **raises** on an
   unrecognized version rather than misparsing; sequential record walks with no
   fixed offsets anywhere.
4. **Resolve the `names.dat` join against an independent answer key**, not an
   impression. The encoding is `unconfirmed` today (`docs/data-access.md:238`) and
   is the largest single unknown in the request.
5. **Land bronze into the empty `ootp` schema** with `snapshot_date` in every
   primary key, append-only and idempotent per snapshot, so the first sim date never
   has to be re-keyed.
6. **Settle and test all five dataset contracts** — grain, keys, coverage, update
   semantics, layer pattern — including the roster-membership grain the request
   never names, which is the fan-out that bites *today*, on an unsimmed save, with
   no trade in sight.
7. **Build a two-tier ground-truth architecture** and label every parsed field with
   the tier that proved it.
8. **Answer `docs/data-access.md` §5's critical-path question** — is the scouted
   view stored or computed at render time — with a written pass/fail spike **before
   any parser code**, and a pivot rule registered before the spike runs.
9. **Leave behind mechanical enforcement rather than prose**: a fixed-offset source
   guard, a withheld-field regression guard, a read-only proof for ADR 0001, and
   byte-accounting assertions as the cheapest detector for the silent-misparse class.
10. **Correct the documentation that is now measurably wrong** and upgrade
    `docs/data-access.md`'s epistemic labels for exactly the fields the paired-save
    validation actually proves — leaving everything else `unconfirmed` and withheld.
11. **Record a measured extraction-cost number** against the ingest run, so the later
    *"is weekly re-ingestion viable"* decision has evidence instead of a guess.

**Non-Goals**

- **No dbt project, no `transform/`, no `dbt-mysql` dependency, no silver or gold
  dbt layer.** Stated as a narrow, deliberate divergence from ADR 0005's *tooling*
  phrasing — not a silent one. The **pattern** choice (parser side, not builder
  side) is honoured in full. See Decisions §9.
- **No `build/`, no `datasets/`, no manifest entry.** `players.csv` *is* static
  reference but is used only as test ground truth, so it needs no builder and no
  registration. CLAUDE.md forbids creating these speculatively.
- **No advisors of any kind, and no ruling on their network posture.** The request's
  observation that *a shell is a superset of a web tool* is correct and belongs in a
  doc; [ADR 0017](../../../docs/decisions/0017-gm-is-a-subagent.md) makes advisors
  umpire-spawned on a GM commission.
- **No third report.** Two is the deliberate "how thin is thin" setting; widening it
  is a GM action under ADR 0016, not an engineering default.
- **No serving of another organization's data to the GM.** Bronze lands everything
  the walk yields — filtering at bronze is forbidden by
  `.claude/agents/data-engineer.md:98` — and the **report** is where the org filter
  lives.
- **No `retired.dat`** (154,088,679 bytes, measured), no career or statistical
  history, no game logs, no transactions, no `text_data.sqlite3` newspaper, no
  `news/html` path.
- **No true ratings, no `players.prone_*`, no `players_value.*`** reachable from any
  report or the catalog's GM-readable section
  ([ADR 0012](../../../docs/decisions/0012-scouted-ratings-only.md)). A field that
  cannot be classified is withheld — *"probably fine"* is not a classification.
- **No incremental or weekly re-ingestion machinery**, no scheduler, no CDC, no
  retention policy. Exactly one league state exists. Snapshot **keys** are in scope;
  snapshot **orchestration** is not.
- **No write of any kind** to anything under `$OOTP_INSTALL` or `$OOTP_SAVED_GAMES`
  — no save edit, no roster import file, no UI automation, no export triggered
  against `OOTP-AI`. ADR 0001, ADR 0003. `challenge.dat` is present at 241 bytes and
  one write is unrecoverable.
- **No second ground-truth export.** Measured: `ootp_truth_osa` exists with **0
  tables**, while `ootp_truth_real.players_scouted_ratings` already carries **both**
  perspectives from **one** export (`scouting_coach_id` ∈ {-1, 2759}, 18,072 rows
  each). The premise behind a second export database is wrong; say so rather than
  asking the operator to run one.
- **No parser performance work.** If a full parse is slow, record the number and stop.
- **No player-per-team-stint table.** Undefinable at one snapshot on an unsimmed
  league; the snapshot *is* the stint resolution today, and a mid-season trade will
  appear as a `team_id` change between two snapshots.
- **No committed OOTP data of any kind.** Every offline fixture is a synthetic byte
  sequence we authored, never a slice of a real save
  ([ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md)).

## Acceptance Criteria

Criteria 1–5 and 16 run **offline** — no game install, no MySQL — because that is
CI's actual condition. Criteria marked `-m gamedata` are excluded from CI by
`.github/workflows/ci.yml`.

> **Marker note (blocker F4/SD-02).** `pyproject.toml` declares exactly one marker,
> `gamedata`, defined as *"requires a local OOTP install or save"* — saying nothing
> about a database — and `addopts` carries `--strict-markers`, making an undeclared
> marker a hard collection error. **This scope widens the `gamedata` declaration to
> "requires a local OOTP install, save, or warehouse"** rather than adding a second
> marker. Every warehouse-reading test carries it.

> **Test ownership (blocker F2).** `tests/` is in the hard **deny set** of
> [`.claude/agents/data-engineer.md`](../../../.claude/agents/data-engineer.md), which
> instructs the subagent to stop and report rather than build when spec targets fall
> inside it. **All files under `tests/` are authored by the main thread.** The
> implementation subagent's spec declares only `src/ootp_ai/**` and the field-map
> declaration as target paths. Stage 3 must split the work this way.

1. `uv run pytest tests/test_save_header.py` is green **offline**: a synthetic header
   with byte 0 = `0x00`, `b"OOTP"` at offset 1 and u32 `25` at offset 5 parses;
   version 24 and version 26 each raise a named `UnsupportedSaveVersion`; a buffer
   whose `bytes[0:4] == b"OOTP"` (magic at offset 0) is **rejected**; and a header
   whose self-declared filename at offset 25 disagrees with the file actually opened
   is rejected. Fixture files must **not** carry a `.dat` extension or
   `tests/test_no_leaks.py` goes red.
2. `uv run pytest tests/test_sequential_walk.py` is green **offline**: two synthetic
   records identical except for the length of a variable-length region (a 1-year vs
   a 10-year contract array) yield identical values for every field parsed **after**
   that region. A fixed-offset reader cannot pass this test.
3. `uv run pytest tests/test_no_fixed_offsets.py` is green: a static source scan finds
   zero `.seek(<nonzero int literal>)` calls and zero `struct.unpack_from` with a
   constant record-relative offset anywhere under `src/ootp_ai/parser/`. Encodes
   `data-engineer.md:69-72` as a mechanical check rather than a review convention.
4. `uv run pytest tests/test_grain_contracts.py` is green **offline**: it reads the
   tracked contract declaration and the DDL the loader emits, and asserts the prose
   grain sentence equals the key the DDL emits, so prose and enforcement cannot drift
   (`data-engineer.md:101`). Declared keys: `bronze_team` (`snapshot_date`,
   `save_id`, `team_id`); `bronze_player` (`snapshot_date`, `save_id`, `player_id`);
   `bronze_team_roster` (`snapshot_date`, `save_id`, `team_id`, `player_id`,
   `list_id`) — **not** (`snapshot_date`, `player_id`). The `save_id` component is
   required by SD-09: the pipeline parses two different universes and a key without
   it collides them.
5. `uv run pytest -m gamedata tests/test_grain_contracts.py::test_roster_grain_is_not_player_grain`
   is green: it **positively asserts** that `player_id` is *not* unique within one
   snapshot's roster rows, so a later refactor cannot silently collapse the membership
   grain into a player grain. It also asserts `count(distinct player_id)` in
   `bronze_team_roster` is materially **less** than `count(*)` in `bronze_player` for
   the same snapshot. Ground truth for the shape: `ootp_truth_real.team_roster` is
   15,672 rows over **7,370 distinct players** — not 18,072 — with `list_id` ∈
   {1: 7370, 2: 7037, 3: 935, 4: 330} (measured; corrects finding F7).
6. `uv run pytest -m gamedata tests/test_parser_vs_export.py` is green: parsing the
   probe save and diffing against `ootp_truth_real` yields **zero** row-count and
   **zero** value differences over the landed field set — 259 teams, 18,072 active
   players (`retired = 0`), 15,672 `team_roster` rows, 15 leagues. Every mismatch is
   listed **per field by name**; an aggregate pass rate is not acceptable output. The
   test **first** asserts provenance: the parsed save's sim date is 2024-03-18 and its
   human team is the Chicago Cubs, matching `ootp_truth_real` — proving the binaries
   and the export describe the same universe.
7. `uv run pytest -m gamedata tests/test_names_join.py` is green: every name index the
   parser resolves out of the probe save's `players.dat` matches
   `ootp_truth_real.players.first_name` / `.last_name` by exact string equality, 100%
   of compared rows, zero unresolved indices, every failure enumerated. The test
   **skips loudly with a named reason** if `ootp_truth_real` is unreachable — it must
   never pass vacuously. String comparison declares its collation explicitly (SD-13).
8. `uv run pytest -m gamedata tests/test_names_join_boston.py` is green — **the Tier-A
   chain that validates our own league, added by finding F8.** For every player in
   `OOTP-AI.lg/players.dat` carrying a non-empty `historical_id`, the
   `names.dat`-resolved first and last name is checked against `players.csv`'s
   `FirstName` / `LastName` joined on `LahmanID`, every failure enumerated. This runs
   against **Boston**, not the Cubs probe, and is the only validation of the join on
   the league we actually manage.

   > **Amended 2026-08-18, at the operator's direction, after Phase 7 measured the
   > answer key.** This criterion originally read *"100% exact"*. That is **unachievable
   > on correct data**, and a parser scoring it would be the suspicious one:
   > `players.csv` ships **pure ASCII**, with every accented character already replaced
   > by `?` — the file literally contains `Rod?n`, and carries zero bytes above 0x7F. So
   > 25 players per save cannot match a correctly-parsed name, and five more disagree in
   > renderings the shipped CSV and the save simply differ on (a short-form given name
   > against a formal one, a generational suffix, a surname particle's capitalisation,
   > and two fictionalised identities).
   >
   > **The replacement is stronger than a softened percentage, not weaker.** It is:
   > every resolved name must equal the CSV after **one declared, mechanical
   > normalization** — non-ASCII to `?`, which is what the CSV provably does — and every
   > remaining disagreement must be either inside a league the data itself shows to
   > carry fictionalised identities (bounded by pinned constants, no league id named in
   > the test), or a member of a residual set **identical to the one the standard-mode
   > probe shows**. That probe's parse is independently verified at 18,072/18,072
   > against the export, so a disagreement surviving there is the CSV's, not the
   > parser's — and a real parse fault could not make two universes' residual sets line
   > up. Zero unresolved indices and zero blank names remain absolute.
   >
   > Evidence: `requests/feature-requests/first-sight/reviews/phase-7-acceptance-panel.md`,
   > and the module docstring of `tests/test_names_join_boston.py`.
9. `uv run pytest -m gamedata tests/test_parse_real_save.py` is green against
   `OOTP-AI.lg`: exactly 30 teams extract at MLB level with correct abbreviations;
   `player_id` is unique per snapshot; Boston's roster rows number **>= 26** (not
   `== 26` — the club is in spring training at 2024-03-07 and a set 26 probably does
   not exist yet); and **zero** roster rows carry a null or blank display name.
10. `uv run pytest -m gamedata tests/test_snapshot_semantics.py` is green: loading the
    same snapshot twice leaves per-table row counts and checksums unchanged; loading a
    second `snapshot_date` leaves the first snapshot's rows bit-identical; parsing the
    same snapshot twice produces byte-identical parser output; and re-landing an
    existing `snapshot_id` does not silently overwrite it.
11. `uv run pytest -m gamedata tests/test_read_only.py` is green: no file under
    `$OOTP_SAVED_GAMES` or `$OOTP_INSTALL` has a modification time or SHA-256 digest
    different from the pre-run manifest, taken before and after a full parse. **It runs
    first against the disposable Challenge Mode probe save** and only then against
    `OOTP-AI.lg` (SD-20). ADR 0001 is the one unrecoverable failure in the project, so
    it gets a test rather than a promise.
12. `uv run pytest -m gamedata tests/test_byte_accounting.py` is green, **split by file
    per blocker F3**: the strict form — zero unaccounted bytes — applies only to
    `teams.dat` and `names.dat`, where a full walk is plausible. For `players.dat` the
    assertion is weaker but still diagnostic: the walk reaches a record count matching
    an independent count (the export's `retired = 0` population for the probe save) and
    **terminates on a record boundary**, with the residual byte count *recorded* in the
    ingest-run row rather than asserted to be zero. Full byte accounting on
    `players.dat` is a research task, not a counter, and the tier rationale says so.
13. `uv run pytest tests/test_withheld_fields.py` is green **offline**, keyed on the
    field map's declared **category** — not on column-name globs (finding F9). Asserts:
    no field whose category is `rating-true`, and no field whose epistemic label is
    `unconfirmed` or `assumed`, is renderable. Includes a **negative** test asserting a
    synthetic `rating-scouted` field *is* renderable, so the guard cannot be satisfied
    by blocking everything. Name patterns survive only as a secondary check, with
    `talent_%` corrected to `%_talent_%` — as written it matched no real column, since
    the actual columns are `batting_ratings_talent_*`.
14. `uv run python -m ootp_ai.reports render` writes the two reports, and
    `uv run pytest -m gamedata tests/test_reports.py` asserts: the resolved output root
    is **git-ignored** — proven by `git check-ignore -q <path>` exiting 0 **and**
    `git ls-files` listing no file under it (blocker F1/SD-01; the earlier "outside the
    git worktree" phrasing was unsatisfiable, since `var/` is inside the worktree and
    merely ignored); the roster report contains rows for exactly the configured
    organization and zero rows belonging to any other; every player row's name matches
    `^[A-Za-z][A-Za-z .'-]+$` (a name, not an integer); the standings report contains
    30 MLB rows grouped by division with W-L-pct-GB columns present; and both files
    carry `snapshot_date` and sim date on line one. **Standings content is asserted
    structurally** — measured, all 259 `team_record` rows are 0-0-0 and 0 of 12,961
    games are played, so asserting a nonzero win total would fail on a *correct* parse.
15. `uv run python -m ootp_ai.catalog` regenerates the catalog, and
    `uv run pytest -m gamedata tests/test_catalog.py` asserts: the structural section is
    regenerated during the test and is byte-identical to the committed copy (proving it
    cannot be hand-edited into drift); every landed table appears with a grain sentence,
    key list, coverage population, row count, source `.dat` file, epistemic label and
    snapshot date; the withheld groups are listed with reason and ADR; **no player-level
    value and no rating column name appears anywhere in it**; and regenerating twice is
    byte-identical. The coverage statement states how many players carry **no** roster
    row (~10,700 of 18,072 active — free agents, draft-eligible, international,
    unassigned), so the GM prices "who is available" as a known gap.
16. `uv run pytest -m "not gamedata"` passes with **no** game install and **no** MySQL
    server, and `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`
    are clean, with `tests/test_no_leaks.py`, `tests/test_repo_structure.py`,
    `tests/test_agent_contract.py` and `tests/test_doc_links.py` all still green.
17. `uv run pytest -m gamedata tests/test_extraction_cost.py` emits wall-clock seconds
    for a full parse of the in-scope files into the ingest-run row and the catalog.
    **The assertion is that the number exists and is recorded — there is no threshold.**
    See Decisions §6: the operator ruled the work takes as long as it needs.
18. The **scouted-view spike** has a written verdict committed *before any ratings code
    exists*, stating stored-or-computed with an epistemic label and citing the byte
    evidence, and `docs/data-access.md` §5's `unconfirmed` label is either upgraded or
    explicitly reaffirmed as still open. A FAIL verdict triggers the pre-registered
    pivot rather than being routed around.
19. `docs/league-rules.md:129` and `:295` no longer assert a `leagues.dat`, and the
    corrected text records the measured location of the league configuration block in
    `world.dat`. Verified by `tests/test_doc_links.py` staying green plus a grep
    asserting the string `leagues.dat` appears nowhere in `docs/` except as an explicit
    correction note.
20. **USER-RUN** (the acceptance panel must not claim this): a cold session spawns the
    `gm` subagent with the roster and catalog reports in its context, and the returned
    handoff's `## situation` section names at least five Boston players by real name,
    each attributed to the report as its source, with no roster fact appearing in
    `## assumed`.
21. **USER-RUN**: the operator confirms `OOTP-AI.lg`'s file set, sizes and modification
    times are unchanged after a full ingestion run, checked by hand against the recorded
    manifest — an independent check that does not rely on the code that would be the
    thing violating it.

## Scope (tiered)

### Core (must)

1. **Spike first, gating only the ratings half.** Run the test written at
   `docs/data-access.md:288-295` against assets confirmed on disk: search the probe
   save's `scouting.dat` (2,349,181 bytes) for the values in
   `ootp_truth_real.players_scouted_ratings` (36,144 rows, perspectives -1 and 2759,
   18,072 each). **FOUND** → the parser has its source and ADRs 0012/0014/0016 have a
   data path. **ABSENT** → record it, withhold every rating, ship the reports anyway.
   The kill/pivot rule is **written before the spike runs**, not after it returns.
2. **Config layer** resolving `OOTP_INSTALL`, `OOTP_SAVED_GAMES`, `OOTP_LEAGUE`,
   `OOTP_SNAPSHOT_ROOT` and the MySQL connection from `.env` only. No literal path, no
   `parents[N]` walk outside test modules. `OOTP_SNAPSHOT_ROOT` is **empty** in `.env`
   today (measured) — the default must be defined and validated as local disk, since
   `.env.example` warns the saved-games root may be OneDrive-redirected.
3. **A save enumerator** that confirms `players.dat` **and** `teams.dat` exist before
   treating a directory as a save. Measured trap: the saved-games root contains a stray
   empty directory literally named `.lg`, so a `*.lg` glob is not a list of saves.
4. **Shared header reader and version guard**: leading `0x00`, `b"OOTP"` at offset 1,
   u32 version at offset 5 (must equal 25), self-declared filename at offset 25
   cross-checked against the file opened. Verified byte-for-byte on `OOTP-AI.lg`'s
   `teams.dat` and `world.dat`: `00 4f 4f 54 50 19 00 00 00 0b 00 00 00 68 00 00 00 54
   00 00 00 01 00 00 00` + the null-padded filename. **Refuses strictly**; an
   unrecognized version raises rather than parsing.
5. **Snapshot step**: copy only the parsed files to the snapshot root under
   `<league>/<sim_date>/` with a per-file size + SHA-256 manifest, every handle opened
   `"rb"`. The in-scope set is **~46 MB** (players 32.07 + names 8.64 + teams 5.32), not
   the ~600 MB `.lg`, because `retired.dat` is out. Assert Challenge Mode from the
   filesystem via `challenge.dat` at exactly 241 bytes rather than from a menu. All
   parsing runs against the snapshot, never the live save.
6. **Sequential `teams.dat` walk**: `team_id`, the 5-string signature (city,
   abbreviation, nickname, logo filename, full name), ARGB colors, level and
   `parent_team_id` so MLB clubs are distinguishable from affiliates, plus the
   sub-league/division hierarchy and the win-loss fields the standings report needs.
   `docs/data-access.md:223-226` already records the 5-string signature as `verified`.
7. **Sequential `players.dat` walk with a deliberately minimal field set**: `player_id`,
   team/organization assignment, position, uniform number, date of birth, bats/throws,
   the name indices, and `historical_id`. Every landed field is a field somebody
   re-validates after a game patch — the field set is a maintenance liability, not a
   free win.
8. **The `names.dat` join**, brute-forced against a full answer key rather than guessed.
   Structure observed and worth carrying: records read u32 len + ASCII + u32 `0` + u32
   monotonic index + three u32s + a `0x27` separator, alphabetically ordered.
   **Constraint added by SD-10:** `names.dat` is 8,642,110 bytes in *all three* saves on
   disk with **three different SHA-256 digests** — a fixed-size, per-save-populated
   table. Nothing may carry a name index, an index→string expectation, or a cached name
   table from the probe save into the managed league, and a test asserts that resolving
   the same index in both saves is **not** expected to yield the same string.
9. **Roster-list extraction** at the `team_roster` grain (`team_id`, `player_id`,
   `list_id`), including empirically deriving what each `list_id` **value** means.
   **Fallback pre-registered (SD-17):** if the mapping cannot reach at least `inferred`,
   land `list_id` as an opaque integer, group the roster report by its raw value with a
   header line stating the meanings are `unconfirmed`, and file a follow-up. The report
   **never** prints a human label (`active roster`, `40-man`) for a `list_id` whose
   mapping is not labelled at least `inferred` — a wrong label produces a confidently
   wrong roster with nothing throwing.
10. **MySQL bronze landing** into the `ootp` schema, 1:1 with parser output — typing,
    casing, dedup only; no joins, no filtering, no semantic renaming
    (`data-engineer.md:98`). Tables: `bronze_team`, `bronze_player`,
    `bronze_team_roster`, `bronze_name`. `snapshot_date` **and `save_id`** in every
    primary key; loading a snapshot touches only its own partition. `bronze_name`
    carries its own declared grain, key and coverage like every other table (SD-10 /
    finding F10).
11. **One ingest-run row per snapshot** recording source file sizes, SHA-256 digests,
    header versions, sim date, human team, row counts, residual bytes and wall-clock
    parse time. This is what makes a data incident triageable instead of archaeological.
12. **The five contracts, settled and enforced.**
    - **Grain:** team per snapshot; player per snapshot; **player per team per
      roster-list per snapshot** — the membership grain the request never names and the
      fan-out that bites today, since a player sits on the active list *and* the 40-man.
    - **Keys:** `player_id` is the only universal key. `historical_id` is a **nullable
      attribute and never a join key** in any serving path — measured, 1,920 of 18,072
      active players carry a non-empty one (10.6%). A static check asserts no join or
      `ref` condition uses it.
    - **Coverage:** preserve structural absence as `NULL`, **never zero**. The export
      writes `0` for `rules_active_roster_limit` and the service-time columns on all 14
      non-MLB league rows — 14 separate opportunities to commit this error.
    - **Update semantics:** append-only per snapshot; snapshots immutable.
    - **Layer pattern:** parser + warehouse for everything here; nothing in this request
      is static reference data.
13. **Two Markdown reports** rendered to the git-ignored output root. Roster: the
    configured organization only, grouped by roster list, `snapshot_date` and sim date on
    line one. Standings: 30 MLB clubs by division with W-L-pct-GB — shipped, but its
    acceptance is structural because measured today every club is 0-0.
14. **A generated catalog** built from `information_schema` plus the **same tracked
    contract declaration** the DDL and the uniqueness tests read — one declaration, three
    consumers, so drift is structurally impossible. Includes a **withheld** section
    naming the true-rating tables, `players.prone_*`, `players_value.*` and every still-
    `unconfirmed` field, each with its reason and ADR. **Split per Decisions §3:** the
    structural half is tracked; row counts, snapshot dates and freshness generate into the
    ignored output root.
15. **A report-path pointer in the tracked half of the catalog** (SD-11): each report's
    logical name, the `.env` key and relative path it resolves to, and a one-line spawn
    instruction the umpires read when handing the GM its reports. **Not** a Markdown link
    into the ignored root — that turns CI red today. Without this, acceptance criterion 20
    is unreproducible by anyone who was not in the room.
16. **The field map / contract declaration as a first-class tracked artifact**, carrying
    per field: name, type, the walker that reads it, category (`identity` /
    `rating-true` / `rating-scouted` / `contract` / `structural`), epistemic label, and
    the validator tier that produced the label. ADR 0006 §Notes explicitly blesses
    derived schema knowledge as ours and trackable.
17. **Two-tier ground-truth harness.** **Tier A:** `players.csv` — exact, raw ~1–1000
    scale, shipped real players only, and (finding F8) **carries `FirstName`/`LastName`**,
    making it a name validator for our own league via the `LahmanID` join. **Tier B:**
    parse the probe save whose binaries are on disk and diff row-for-row against its
    72-table export. Tier B is **exact** for ids, names, strings, dates, roster lists,
    team dimension and league config, and **bucketed** for ratings — measured,
    `batting_ratings_overall_contact` has exactly 12 distinct values 20–80 — so it is
    **not** an exact rating validator.
18. **Per-field, never aggregate, mismatch reporting** in every differential test.
19. **New `.env` keys** naming the probe save directory and the disposable Challenge Mode
    probe save, so both resolve by name and neither is hardcoded.
20. **The tracked half of the report channel**: entries in `gm/standing-orders.md` under
    its `## Reports` format, using the **new engineering-owned report kind** established
    in Decisions §4. The rendered report rebuilds from the save so it goes to the ignored
    root; the **decision** that the report exists does not, so it is tracked.
21. **Documentation corrections routed through `/update-docs`**, never written by the
    builder (`docs/data-access.md` is in the data-engineer's deny set): no `leagues.dat`
    exists and the league config block is in `world.dat` at the measured location;
    `docs/data-access.md` §1's file table is incomplete (18 `.dat` files present, several
    unlisted); the `names.dat` fixed-size-per-save finding with an `inferred` label;
    `ootp_truth_osa` is empty and unnecessary; and label upgrades for exactly the fields
    Tier A or Tier B actually proves, with everything else left `unconfirmed` and withheld.

### Folded in (cheap wins)

1. **Extend `tests/test_no_leaks.py` to catch *rendered* game data in tracked files.**
   The existing guard bans four filenames and two suffixes — a Markdown roster sails
   straight through, and this feature is the first thing in the repo's history that
   renders OOTP player data to a file. Assert the report and catalog output roots resolve
   to a git-ignored path. **Add finding F19's constraint mechanically:** the **tracked**
   half of the catalog and field map may name source **files** (`players.dat`) but **never
   absolute paths** — those live only in the generated half and the warehouse ingest-run
   row. `saved_games.dat` embeds an absolute user-profile path for every save, so a
   provenance section that renders it publishes a username to a public repo.
   **Note a real gap in the local feedback loop:** `tracked_text_files()` enumerates via
   `git ls-files`, so the guard does not see a new file until it is staged — a leak in an
   untracked artifact passes locally and fails in CI. Worth a follow-up request; it is not
   in scope here.
2. **Backtick every identifier in export-diff SQL, plus one regression test.** A measured
   live instance: `select current_date from ootp_truth_real.leagues` returns the
   wall-clock date for all 15 rows because MySQL parses the column name as the
   `CURRENT_DATE` function, with nothing erroring — a textbook data incident sitting in
   the exact code path the league-rules diff would use.
3. **Per-table coverage statements generated from counts, not hand-written.** *"players:
   18,072 rows, active only, retired excluded, 1,920 carry an external ID"* is far more
   useful to a GM pricing an action than a table name, and generated from counts it
   cannot go stale.
4. **A machine-readable `catalog.json` alongside the Markdown**, from the same generator.
   The GM reads Markdown; future umpire-spawned advisors will want to discover tables and
   grains without re-reading prose. *(Adversary SD-16 called this YAGNI for advisors this
   scope forbids; kept because it is one extra writer from an existing generator and the
   alternative is a hand-maintained second copy.)*
5. **Write each field's epistemic label into a warehouse metadata table** alongside the
   data, not only into docs. A future incident can then ask *"what did we believe about
   this field the day it was landed?"* as a query instead of archaeology through the git
   history of `docs/data-access.md`.
6. **`challenge.dat` (241 bytes) and the header self-naming filename check promoted to a
   pre-flight on every run.** Both cost microseconds and both catch the class of error
   where the pipeline is pointed at the wrong save — which under ADR 0003 is the error
   whose consequences are unrecoverable.
7. **Resolve the human team from data on every save rather than hardcoding it.** Measured
   from `saved_games.dat`: `OOTP-AI`'s human team is Boston at 2024-03-07; the probe
   save's is the **Chicago Cubs** at 2024-03-18. Any code that hardcodes *"we are team
   6"* or *"perspective 2759 is us"* passes on ground truth and breaks on our league —
   invisible to the entire validation harness.
8. **Reclassify the probe save in the docs as a retained validation asset.** Every value
   claim in the validation strategy depends on it staying on disk; ADR 0002 and
   `docs/data-access.md` §6 currently describe it as disposable, and the parser loses its
   only ground truth for fictional players and roster lists the day someone tidies up.
9. **Sequence every filesystem-touching test against the disposable Challenge Mode probe
   save first** (SD-20) — enumerator, header guard, snapshot copy, read-only proof — and
   only then against `OOTP-AI.lg`. An identical-mode disposable save sits beside the
   irreplaceable one; pointing untested code at the managed league first is avoidable
   exposure.

### Gated — resolved

| Gated item | Disposition |
|---|---|
| Land `coaches.dat` as the staff/sensor dimension | **Deferred**, gated on the spike verdict. Without it the two scouting perspectives are two anonymous integers — but it only matters if the spike passes, and advisors are out of scope. |
| Full `docs/league-rules.md` §1 diff | **Deferred.** Requires reverse-engineering `world.dat` (8,898,534 bytes, unmapped) to recover ~30 scalars with no Challenge Mode export to validate against. §4's own proposal is an offseason standing order first due ~2024-10, so deferring costs nothing. **The doc correction stays core.** |
| Standings with playoff seeds and the top-two bye flag | **Deferred** to the first sim. `docs/league-rules.md` §3 argues the bye is worth more than the standings suggest — but at 0-0 across all 30 clubs, seeds are noise dressed as analysis. |
| Minor-league populations in the roster report | **Deferred.** Bronze lands them by the walk so the marginal cost is a filter change, but serving five tiers multiplies structural-absence edge cases exactly when nothing consumes them. |
| Settle ADR 0004's adapter question; build silver/gold as dbt models | **Deferred** — see Decisions §9. |
| Internal→display rating-scale mapping as a builder dataset | **Deferred.** Correctly routed to the builder side by ADR 0005 (it changes only on a game patch), and it would put every rating through one audited artifact — but it depends entirely on the spike passing and it creates `datasets/`, the repo's first builder. Measurement recorded so the next request starts from it. |
| OSA-vs-own-scout divergence as a first-class column | **Deferred**, gated on both the spike and `coaches.dat`. ADR 0014's central empirical claim; nearly free once both perspectives are parsed. |
| A report **registry** rather than two bespoke renderers | **Deferred.** Speculative generalisation from n=2, and it presumes an answer to *"how thin is thin"* by making report proliferation cheap — which is the tension the project exists to create. |
| Run the second export into `ootp_truth_osa` | **Not doing it; retiring the schema and its `.env` key.** Measured: `ootp_truth_real` already carries both perspectives from one export, so the premise is wrong. |

## Above & Beyond

The surviving ambitious proposals, with the tier each landed in:

- **Full parser-vs-export differential harness against the retained probe save** —
  *core*. Not an enhancement: `players.csv` alone validates no roster list, no team
  dimension and no league config, so this is the only thing that makes the names join and
  the roster grain provable rather than eyeballed.
- **Byte-accounting assertions on every walk** — *core, but re-tiered in cost*. The
  cheapest structural detector for the silent-misparse class, and the only check that
  works on fields with no ground truth. Split strict/diagnostic by file per blocker F3.
- **Snapshot content-hash manifest and a read-only proof** — *core*. Impossible to
  retrofit onto snapshots already taken, and ADR 0001 is the one unrecoverable failure in
  the project.
- **Extraction-cost benchmark as a recorded metric** — *core*, threshold removed per
  Decisions §6.
- **Field map as a tracked declaration rather than Python constants** — *core*. Three
  consumers of one declaration is how grain-prose-vs-grain-enforcement drift becomes
  structurally impossible. Registering it in `datasets/manifest.json` is the part **not**
  folded — that creates the repo's first builder.
- **Catalog names what is withheld, not just what is landed** — *cheap fold*. The
  request's second desired outcome is *"the GM knows what it is not seeing"*, and a
  catalog of landed tables tells it only what it can see.
- **Reserved-identifier guard for export-diff queries** — *cheap fold*. A measured live
  incident, not a hypothetical.
- **`catalog.json` sibling** — *cheap fold*.
- **Epistemic label landed alongside the data** — *cheap fold*.
- **Retire `ootp_truth_osa`** — *cheap fold* for the doc/`.env` change; the formal key
  retirement was the gated half and is resolved as *do it*.
- **Internal→display rating-scale dataset**, **`coaches.dat`**, **playoff seeds**, **the
  report registry**, **OSA-vs-scout divergence**, **dbt silver/gold** — all *gated and
  deferred*, dispositions in the table above.
- **Publish the field map as a public contribution** — **dropped**. It buys this project
  nothing: it does not make the GM see its club and does not validate a byte. Publishing
  a field map before the paired-save validation has upgraded its labels would be
  publishing beliefs as findings — the precise error this repo's labelling discipline
  exists to prevent. Revisit once the labels are earned.

## Risks & Unknowns

1. **The scouted view may be computed at render time, not stored.** `unconfirmed`
   (`docs/data-access.md:282`). If so, ADRs 0012, 0014 and 0016 have no data path and the
   front office can read the answer key and nothing else. *Mitigation:* spike first, pivot
   rule written before it runs, ratings decoupled so the slice ships either way.
2. **The `names.dat` encoding may resist.** `unconfirmed` (`:238`), and the largest single
   unknown. *Mitigation:* Decisions §8 — resolve from `players.csv` at runtime for players
   carrying a Lahman ID.
3. **`names.dat` content is per-save.** Measured: identical size across three saves, three
   different digests. A probe-derived index does **not** transfer. This is a silent-wrong
   failure, not a crash.
4. **The `list_id` enum has no documented value semantics.** Open-ended research on the
   critical path of the headline report. *Mitigation:* fallback pre-registered in Core §9.
5. **The export is display-scale and bucketed.** It can never be the exact rating
   validator, so `players.csv` stays load-bearing permanently — and a bucketed check can
   pass a parser reading the *adjacent* u16, which is CLAUDE.md's named correctness trap
   in its most dangerous form.
6. **`world.dat` is unmapped and has no Challenge Mode ground truth.** Why the §1 diff is
   gated rather than core.
7. **The doc-link guard is broken in a way this feature's own artifacts trip.** Fenced
   links, `file.py:123` citations and `var/` targets all fail. A live bugfix request
   exists; this document works around it with code spans.
8. **`tests/` is in the builder's deny set.** If stage 3 hands the whole spec to the
   data-engineer, the result is an Escalation and zero tests. Ownership is stated in the
   Acceptance Criteria preamble; the plan must honour it.
9. **`mypy` runs strict over both `src` and `tests`, and the first runtime dependency has
   not been chosen** (SD-14). A MySQL driver and a `.env` loader both need selecting, with
   type stubs, before any code compiles clean.
10. **Regenerating a report overwrites the prior snapshot's view** (SD-21), breaking
    citation integrity for `gm/decisions/` records that cite it. Not solved here; flagged
    for the plan.
11. **`docs/league-rules.md:26` and `:31` become false on delivery** — they describe §1 as
    superseded by the warehouse "the moment the parser lands", which this slice partially
    does. The doc gate must catch it.
12. **Cross-schema exact string comparison with no collation decision** (SD-13), in a repo
    whose export doc warns that accent replacement breaks name validation.
13. **Nobody has run any of this code.** Every cost estimate in this scope is
    `unconfirmed`, including the extraction-cost expectation.

## Affected Area & Pointers

A cold stage-3 planning agent reads these **first**, in order.

**Target components.** `src/ootp_ai/` (one file today, `__init__.py`, holding a version
string — parser, config, loader, report renderer and catalog generator are all created
from nothing); the `ootp` MySQL schema (exists, 0 tables); the git-ignored output root for
rendered artifacts; [`gm/standing-orders.md`](../../../gm/standing-orders.md) for the
tracked half of the report channel.

1. [`docs/data-access.md`](../../../docs/data-access.md) — **read the epistemic labels,
   not just the claims.** §4 for the byte format and primitives; §5 for the ratings trap
   and the critical-path spike, whose test is written at `:288-295` and has never been
   run; `:238` for the `unconfirmed` `names.dat` encoding; `:99-102` for the `verified`
   `historical_id`; `:223-226` for the `verified` `teams.dat` 5-string signature; `:14`
   for what `unconfirmed` obligates.
2. [`.claude/agents/data-engineer.md`](../../../.claude/agents/data-engineer.md) — the
   single owner of the build rules. Load-bearing lines: `:69-72` the fixed-offset ban;
   `:91-92` never require a game install to satisfy a test; `:98` bronze is 1:1 with
   parser output; `:101` silver declares its grain in prose **and** proves it; `:117-119`
   no OOTP game data in git, ever; `:132-164` the write allowlist and deny set — note
   `docs/data-access.md` is in the deny set, so findings travel as a docs-delta through
   `/update-docs`.
3. [`FEATURE_REQUEST.md`](FEATURE_REQUEST.md) — the five open Data Contracts, the
   Constraints, and the six Open Questions. Its Scope Signals put `scouting.dat` in scope;
   this document decouples that and says why.
4. [`requests/feature-requests/README.md`](../README.md) — the handoff interface, what
   *testable* means here, and the rule that human-only criteria are **marked USER-RUN** so
   the acceptance panel does not claim them.
5. [ADR 0005](../../../docs/decisions/0005-hybrid-data-layer.md) §Notes — the boundary
   rule verbatim, and its worked example that `players.csv` resolves as **static
   reference**. This is what keeps this feature off the `datasets/` side.
6. [ADR 0004](../../../docs/decisions/0004-mysql-warehouse.md) §Notes — the four live
   adapter options and *"the decision comes due when the first dbt model is requested."*
   Read before writing any transform.
7. The six ADRs that bind this feature directly:
   [0001](../../../docs/decisions/0001-read-only-no-write-back.md),
   [0002](../../../docs/decisions/0002-parse-binaries-not-export.md),
   [0003](../../../docs/decisions/0003-challenge-mode-league.md),
   [0006](../../../docs/decisions/0006-public-repo-local-data.md),
   [0012](../../../docs/decisions/0012-scouted-ratings-only.md),
   [0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md).
8. [`docs/league-rules.md`](../../../docs/league-rules.md) — §1 is the verification target,
   §3 for why the playoff bye is decision-relevant, §4 for the offseason cadence.
   **Correction required at `:129` and `:295`.**
9. [`gm/README.md`](../../../gm/README.md) `:17-19` — the placement rule (*"Can this be
   rebuilt from the save? Yes → `var/`. No → here"*).
10. [`.claude/agents/gm.md`](../../../.claude/agents/gm.md) — front matter `tools: Read,
    Glob` (the entire delivery surface for this feature), and forced-read item 8, *"any
    report or analysis handed to you for this invocation."*
11. `tests/test_no_leaks.py` (`:97-113` is the game-data guard), `tests/test_doc_links.py`
    (fails on tracked Markdown links into `var/` — live defect),
    `tests/test_repo_structure.py`, `tests/test_agent_contract.py`. All four stay green.
12. `tests/fixtures/README.md` — what a fixture may be, given `.dat` and `.lg` are
    gitignored by extension.
13. `.env.example` and `.env` — `OOTP_INSTALL`, `OOTP_SAVED_GAMES`, `OOTP_LEAGUE`,
    `OOTP_SNAPSHOT_ROOT` (**empty today**), `MYSQL_DATABASE` (= `ootp`),
    `MYSQL_TRUTH_REAL_DATABASE`, `MYSQL_TRUTH_OSA_DATABASE` (retiring). Two new keys
    required: the probe save directory and the Challenge Mode probe save.

**The save itself** (read-only, never write) — `$OOTP_SAVED_GAMES/OOTP-AI.lg`:
`teams.dat` 5,318,831 B · `players.dat` 32,070,106 B · `names.dat` 8,642,110 B ·
`scouting.dat` 2,863,744 B · `world.dat` 8,898,534 B · `challenge.dat` 241 B ·
`retired.dat` 154,088,679 B (out of scope). **18 `.dat` files, no `leagues.dat`.**

**`$OOTP_SAVED_GAMES/saved_games.dat`** — carries each save's sim date and human team; the
cheapest available cross-check on `snapshot_date` and the provenance pin for Tier B.
**Correction (finding F19, `high` confidence):** it is **not plaintext**, contrary to
`docs/data-access.md` §1, which records that as `verified`. It carries the standard OOTP
header and length-prefixed strings, so it is read by the **same header reader plus a string
walk — never substring-scraped**, which is the fragile approach this repo's discipline
forbids. It also **embeds an absolute user-profile path for every save**, so nothing that
renders its contents may reach a tracked file. The doc-correction item in Core §21 covers
downgrading the `verified` label.

**The retained validation asset** — the standard-mode probe save. Binaries intact
(`players.dat` 28,653,312 B, `names.dat` 8,642,110 B, `teams.dat` 4,554,317 B,
`scouting.dat` 2,349,181 B) plus its `import_export/mysql` folder, paired with
`ootp_truth_real`.

**The disposable Challenge Mode probe save** — same mode as the managed league, 19 `.dat`
files. Every filesystem-touching test runs here first (SD-20).

**`ootp_truth_real`** (MySQL, 72 tables, verified 2026-08-16): teams 259 · players 132,990
of which 18,072 active (`retired = 0`) and 1,920 carrying a non-empty `historical_id` ·
`players_scouted_ratings` 36,144 across `scouting_coach_id` ∈ {-1, 2759} at 18,072 each ·
`team_roster` 15,672 rows over **7,370 distinct players**, `list_id` ∈ {1: 7370, 2: 7037,
3: 935, 4: 330} · leagues 15 · `team_record` 259 rows **all 0-0-0** · games 12,961 with
`played = 1` on **zero**. `players_batting.batting_ratings_overall_contact` has exactly
**12 distinct values, 20–80** — the export is display scale.

**`$OOTP_INSTALL/data/database/players.csv`** — Tier A ground truth, raw and unfiltered at
~1–1000 scale, the **only** exact rating validator, and (finding F8) carrier of
`FirstName` / `LastName` / `LahmanID`. Also `db_structure_ootp25_mysql.txt`, which gives
the export's table and column layout including `team_roster`'s columns — but **not**
`list_id`'s value semantics.

**Measured, and it overturns two scopers:** the league configuration block is in
`world.dat`, not `teams.dat`. `major_league_ml_c_2024.lsdl` — exactly the `schedule_file_1`
value `docs/league-rules.md` §1 records — is at **byte 5,559,751** of
`OOTP-AI.lg/world.dat`, surrounded by league-shaped records containing `World Series`,
`AL` and `NL`. The same string does not appear anywhere in `teams.dat`.

## Decisions

1. **Fit verdict — accept all four reshapes.** Ratings decouple behind the spike gate;
   standings ship with structural-only acceptance; the full §1 diff demotes to gated with
   the doc correction staying core; dbt defers. *Rationale:* the reshaped core still
   delivers the request's stated observable signal — a GM handoff naming real Boston
   players — and delivers it **whatever the spike returns**, which the request as written
   does not.
2. **The roster report and catalog are free infrastructure, not a commissioned action.**
   *Rationale:* a roster page and the standings are the club's own furniture; ADR 0016's
   boundary is analytical *direction*, not existence. Recorded as a ledger row **with its
   reasoning**, because it becomes an early seq every later report request will cite.
   Per blocker SD-03 the ledger row is **an umpire act, not a build artifact** — it is a
   USER-RUN step after delivery, not something the builder writes.
3. **The catalog splits: structural half tracked, volatile half generated.** Table names,
   grains, keys, coverage statements, withheld groups and epistemic labels are **derived
   schema knowledge**, which ADR 0006 explicitly permits tracking — so they survive a
   fresh clone. Row counts, snapshot dates and freshness generate into the ignored output
   root. *Rationale:* a genuine compromise, not a win — two files, one of which can go
   stale. Explicitly **not** resolved by adding a tracked Markdown link into `var/`: that
   turns CI red today.
4. **An engineering-owned report is a distinct kind, with its own template line.**
   *Rationale:* a pipeline-generated report genuinely has no analyst behind it, and
   `gm/staff.md` records that no staff exist — naming an owner would be fiction. Requires
   an umpire edit to `gm/standing-orders.md`'s format block, which this scope budgets for.
5. **If the `names.dat` join resists, resolve names from `players.csv` at runtime.** For
   the ~1,712 players carrying a Lahman ID, join at render time into the git-ignored
   output root with nothing tracked — ADR 0006 does not force integers onto the page.
   Fictional players still render as IDs. *Rationale:* finding F8 overturned the merge's
   more pessimistic answer. **Hard bind either way: never track a Lahman-to-name lookup.**
   `tests/test_no_leaks.py` catches `players.csv` by **filename only**, so a renamed copy
   sails straight through the guard into a public repo.
6. **No wall-clock budget for a full parse.** *Operator ruling:* "the work will take as
   long as it needs." The extraction-cost criterion records the number into the ingest-run
   row and the catalog; there is **no threshold and no pass/fail on duration**. Finding
   F12 called a number-exists criterion a tautology and that objection stands — it is
   accepted deliberately, on the grounds that a threshold nobody has justified is worse
   than an honest measurement. The number still informs the later *"is weekly re-ingestion
   viable"* decision.
7. **Land everything the walk yields; report Boston only.** *Rationale:*
   `data-engineer.md:98` forbids filtering at bronze, and re-parsing later to add the
   minors costs more than landing them once. Accepted cost: 14 non-MLB league rows carry
   `0` for roster and service-time columns, giving 14 chances to commit the
   structural-absence-is-not-zero error.
8. **Ratings render at the 20–80 player-page scale**, decided now even though ratings are
   gated. *Rationale:* ADR 0012 says *"at the scale the game displays them"*; 20–80 is the
   scale a human GM reasons in and the one the export corroborates. Recorded in the field
   map with its label so the next slice inherits a decision rather than re-deriving one.
9. **Deferring dbt is recorded as a note in ADR 0004 §Notes** — the trigger, and why it
   was not pulled. *Rationale:* a superseding ADR is heavy for a postponement, and ADR
   0005's **pattern** choice is honoured in full; only its *tooling* phrasing is deferred.
   But quietly diverging is the one option this repo forbids, so it goes on the record.
10. **The probe save is reclassified as a retained validation asset**, and
    `ootp_truth_osa` is **retired** along with its `.env` key. *Rationale:* every value
    claim in the validation strategy depends on the probe staying on disk; and
    `ootp_truth_real` already carries both scouting perspectives from one export, so the
    premise behind a second export database is measurably wrong.
11. **The GM tool-grant guard test is out of scope here and filed as its own request.**
    `.claude/agents/gm.md` grants exactly `Read, Glob` and nothing in `tests/` asserts it.
    *Rationale:* this feature creates the report channel but not an advisor, so the gap
    does not widen here; folding it in would blur an already-large slice.

## Panel Trail

Raw, unfiltered panel output — what was *considered*, separate from what survived:
[`reviews/scope-proposals.md`](reviews/scope-proposals.md) (the three scopers' verbatim
proposals) and [`reviews/scope-adversarial.md`](reviews/scope-adversarial.md) (the
convergence map, both adversary summaries, and all 55 findings by severity).

Panel health: **3/3 scopers, 2/2 adversaries, 0 degraded lenses** — 55 findings, 7
blockers, 26 majors. Run 2026-08-16.
