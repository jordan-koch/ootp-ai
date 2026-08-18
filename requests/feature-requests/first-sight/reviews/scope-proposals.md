# Scoping Panel — Raw Scoper Proposals

Verbatim output of the three divergent scopers, before the merge converged them.
Run 2026-08-16 · workflow `wf_dcaa2bed-78d` · 3/3 scopers returned · 0 degraded lenses.

Kept unfiltered on purpose: this records what was *considered*, separate from what
survived into PROJECT_SCOPE.md.

---

## Lens: (unnamed lens)

### scoper

fit

### ok

```json
true
```

### fit

```json
{
    "verdict":  "reshape",
    "rationale":  "It belongs here beyond any doubt — but the slice as written needs restructuring in three specific places.\n\nWHY IT BELONGS. README.md:128-139 names this exact work as what\u0027s next. gm/charter.md:10-15 says the charter cannot be written because \u0027the GM has no warehouse and no reports.\u0027 ADR 0014\u0027s own Costs section (docs/decisions/0014-staff-is-the-information-channel.md:71-74) predicts precisely this deliverable: \u0027A warehouse that can name the roster but cannot say how good anyone is is a real possible first milestone.\u0027 ADR 0016:92-95 calls the report-channel bootstrap \u0027severe\u0027 and this closes it. There is nothing to duplicate: src/ootp_ai/__init__.py is 7 lines of version string, build/ datasets/ transform/ do not exist, and the `ootp` MySQL database exists with 0 tables (measured 2026-08-16 via information_schema against the local server).\n\nRESHAPE 1 — SEQUENCING. The FR\u0027s own Open Question 1 (is the scouted view stored or computed?) is project-threatening, and the FR puts it in the same slice as the deliverable. It does not have to be. A roster report needs names, positions and team; a standings report needs W/L. Neither needs a single rating. Decoupling the two reports from the ratings half means the observable signal in the FR\u0027s Desired Outcome survives even if Q1 comes back \u0027computed\u0027. The spike should run first and gate only the ratings work.\n\nRESHAPE 2 — LAYERING. The FR\u0027s Rough Ideas propose \u0027bronze, conform in silver, serve gold.\u0027 ADR 0004 §Notes:88-106 records that the dbt adapter question is unresolved, that adopting dbt-mysql pins dbt-core four minor versions behind permanently, that \u0027Option 3 or 4 is likely correct on the evidence\u0027, and that \u0027the decision comes due when the first dbt model is requested.\u0027 pyproject.toml:26-29 says the same. Building three medallion layers to serve two reports forces the most expensive kind of decision this repo has — an ADR re-litigation — in exchange for a convenience. Recommend bronze landed by the Python loader (bronze is 1:1 with parser output per .claude/agents/data-engineer.md:99-101, i.e. a loader concern, not a transformation) and the two reports rendered from hand SQL, with dbt deferred as a gated enhancement. This is a narrow, stated divergence from ADR 0005 — the work stays in 0005\u0027s parser+warehouse family; only the medallion layering is postponed.\n\nRESHAPE 3 — A FALSE PREMISE. docs/league-rules.md:129-131 says \u0027The parser reads leagues.dat directly.\u0027 Measured 2026-08-16: OOTP-AI.lg contains 18 .dat files and none of them is leagues.dat (challenge.dat 241B, coaches.dat, faces.dat, flag_save_completed.dat, games_in_progress.dat, human_managers.dat, messages.dat, names.dat 8,642,110B, offers.dat, parks.dat, players.dat 32,070,106B, retired.dat, scouting.dat 2,863,744B, storylines.dat, teams.dat 5,318,831B, text_data.dat, trades.dat, weather.dat, world.dat). League configuration is presumably inside teams.dat — `unconfirmed`. The §1 verification deliverable has to be re-shaped around that, and the doc corrected either way.\n\nONE ASSET THE FR DOES NOT NAME, and it is the most important one. `Test Save - Standard Mode.lg` is still on disk with every .dat intact (measured: players.dat 28,653,312B, scouting.dat 2,349,181B, names.dat 8,642,110B — byte-identical in size to our league\u0027s) and its import_export/mysql folder survives. That is a PAIRED binary+export: the same league state as ootp_truth_real (72 tables, sim date 2024-03-18, measured). It is the only ground truth that reaches fictional players, minor leaguers, and the scouted view — players.csv reaches none of them. It should be the spine of parser validation, not a footnote."
}
```

### goals

- Give the GM sight of its own club: a roster report naming the Boston Red Sox 26-man roster and a standings report, both rendered as Markdown files the `gm` subagent can open with the only two tools it holds (Read, Glob — .claude/agents/gm.md:4).
- Establish the parser as a real, validated component of src/ootp_ai: a sequential record walker over teams.dat, players.dat, names.dat and scouting.dat that refuses an unrecognized save version rather than misparsing it.
- Establish the warehouse landing path into the `ootp` MySQL database (currently 0 tables, measured) with declared, PK-enforced, test-proven grains and append-only per-snapshot semantics.
- Answer docs/data-access.md §5's critical-path question — whether the scouted rating view is stored in scouting.dat or computed at render time — using the paired probe save plus ootp_truth_real.players_scouted_ratings (36,144 rows across exactly two perspectives, scouting_coach_id -1 and 2759; measured), and record the answer with an epistemic label.
- Resolve the names.dat indirection so a roster report contains names rather than integers, validated against a full answer key (ootp_truth_real.players.first_name/last_name for all 18,072 active players; measured).
- Generate a machine-produced catalog of what has been landed — table, grain, key, coverage, snapshot date — from warehouse metadata plus the tracked contract declaration, so it cannot drift from what was actually landed.
- Confirm or correct docs/league-rules.md §1 against values parsed from OOTP-AI.lg, and correct §2's factually wrong claim that a leagues.dat exists.
- Upgrade docs/data-access.md's epistemic labels for every field the parser validates, and leave everything unvalidated explicitly `unconfirmed` and withheld.

### non_goals

- No dbt project, no transform/ directory, no dbt-mysql dependency. ADR 0004 §Notes:88-106 leaves the adapter open and says the decision comes due with the first dbt model; this slice deliberately does not force it. Divergence from ADR 0005's medallion is narrow and stated, not silent.
- No build/ directory, no datasets/, no datasets/manifest.json. Nothing in this request is static reference data under ADR 0005's rule: names.dat lives in the save and grows as fictional players are generated, so it is a save fact. players.csv IS static reference but is used only as test ground truth, so it needs no builder and no registration. CLAUDE.md forbids creating these speculatively.
- No advisors of any kind, and no third report. FR Scope Signals.
- No serving of another organization's data to the GM. Bronze lands everything the files contain (data-engineer.md:99-101 forbids filtering at bronze); the REPORT is where the org filter lives.
- No retired.dat (154,088,679 B in our save, measured), no statistical history, no text_data.sqlite3 newspaper, no news/html ingestion path.
- No incremental/weekly re-ingestion machinery. One snapshot exists (2024-03-07, unsimmed). Snapshot_date is in every key so the second snapshot is cheap, but the scheduling is not built.
- No write of any kind to anything under OOTP_INSTALL or OOTP_SAVED_GAMES. ADR 0001. One write to a Challenge Mode save is unrecoverable.
- No true ratings, no injury-proneness (prone_*), no players_value.* reachable from the report layer. ADR 0012; a field that cannot be classified is withheld.
- No network tool on anything this creates — no WebFetch, no WebSearch. And nothing this creates grants the GM a shell (which would be a superset of a web tool).
- No second ground-truth export. ootp_truth_osa exists and is empty (measured); filling it needs an in-game run by the operator and is deferred.
- No player-per-team-stint table. It is undefinable at one snapshot and is deferred until snapshots > 1.

### acceptance_criteria

- `uv run pytest tests/test_save_header.py` is green in CI (offline, no install): synthetic header fixtures prove the version guard. A header with `\x00OOTP` + u32 25 at offset 5 parses; version 24 and version 26 each raise a named UnsupportedSaveVersion; a header with the magic at offset 0 instead of 1 raises rather than parsing; a header whose embedded filename disagrees with the file opened raises. Fixture files must NOT carry a .dat extension or tests/test_no_leaks.py::test_game_data_is_not_tracked (which bans the suffix outright, line 111) goes red.
- `uv run pytest tests/test_sequential_walk.py` is green in CI (offline): synthetic records carrying a 1-year contract array, a 10-year contract array, and an empty year-keyed block all yield identical rating-block values — a fixed-offset reader cannot pass this. Plus a source guard asserting no module under src/ootp_ai/parser/ calls .seek() with a nonzero integer literal.
- `uv run pytest -m gamedata tests/test_rosetta_players_csv.py` is green: for every real player resolvable in both $OOTP_INSTALL/data/database/players.csv and the parsed probe save, all 18 rating-block values match exactly, with zero mismatches over a compared population the test prints. No in-game display value is used anywhere in the comparison.
- `uv run pytest -m gamedata tests/test_parser_vs_export.py` is green: parsing `Test Save - Standard Mode.lg` and diffing against the ootp_truth_real database yields zero row-count and zero value differences over the landed field set — specifically 259 teams, 18,072 active players, and 36,144 scouted-rating rows spanning exactly two distinct scouting_coach_id values (-1 and 2759). These are the counts measured in ootp_truth_real on 2026-08-16.
- `uv run pytest -m gamedata tests/test_names_join.py` is green: at least 99% of the probe save's 18,072 active players resolve through names.dat to the exact first_name/last_name held in ootp_truth_real.players, and the test enumerates every failure rather than reporting a rounded rate.
- `uv run pytest tests/test_grain_contracts.py` is green (offline, against the tracked contract declaration; the live-DB half runs under -m gamedata): every landed table's declared PK is unique and non-null — (snapshot_date, team_id), (snapshot_date, player_id), (snapshot_date, player_id, scout_perspective) — AND the prose grain string in the declaration is asserted equal to the PK the DDL emits, so prose and enforcement cannot drift (data-engineer.md:102-105).
- `uv run pytest -m gamedata tests/test_snapshot_semantics.py` is green: loading the same snapshot twice leaves per-table row counts and per-table checksums unchanged; loading a second snapshot_date leaves the first snapshot's rows bit-identical; and the snapshot directory under OOTP_SNAPSHOT_ROOT has identical file mtimes and SHA-256 digests before and after a full parse (the read-only proof for ADR 0001).
- `uv run pytest tests/test_withhold_list.py` is green (offline): no column reachable by the report renderers appears in the withheld set — the true-rating tables, prone_arm/back/leg/overall, and players_value.* (column names confirmed present in ootp_truth_real.players) — and any field whose declared epistemic label is `unconfirmed` or `assumed` is renderable=false by construction rather than by review.
- `uv run python -m ootp_ai.reports render --snapshot 2024-03-07` writes roster.md and standings.md, and `uv run pytest -m gamedata tests/test_reports.py` asserts: the resolved output root came from .env and lies under var/ (never a git-tracked path); roster.md contains exactly the configured organization's active-roster rows and zero rows belonging to any other organization; standings.md contains 30 rows; and every player row carries a name rather than an integer.
- `uv run python -m ootp_ai.catalog` regenerates the catalog from information_schema plus the tracked contract declaration, and `uv run pytest -m gamedata tests/test_catalog.py` asserts every landed table appears with its grain, key, coverage statement and snapshot date, that no player-level value appears in it, and that regenerating it twice is byte-identical.
- `uv run pytest -m gamedata tests/test_extraction_cost.py` records the wall-clock of a full OOTP-AI.lg parse into the run manifest and asserts it under a stated budget, so the FR's 'extraction cost' contract is a measured number rather than a guess.
- CI stays green end to end: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest -m "not gamedata"` all pass with no test requiring a game install or a MySQL server (data-engineer.md:92-93), and tests/test_no_leaks.py + tests/test_doc_links.py remain green — meaning no tracked Markdown links into var/, which is a live CI failure mode recorded in requests/bugfix-requests/_done/doc-link-guard-mismatch.
- USER-RUN (cannot be claimed by the acceptance panel): a cold session spawns the `gm` subagent with the two rendered reports and it returns a gm-handoff:v1 whose `## situation` names real Boston players with a cited source, and whose `## assumed` does not contain 'I do not know who plays second base'.

### core_scope

- SPIKE FIRST, and it gates only the ratings half. Run docs/data-access.md §5's written test using the assets that now exist: search `Test Save - Standard Mode.lg/scouting.dat` (2,349,181 B, on disk) for the scouted values held in ootp_truth_real.players_scouted_ratings (36,144 rows, two perspectives). Found -> the parser has its source and ADRs 0012/0014/0016 have a data path. Absent -> record it, withhold every rating, and ship the two reports anyway. Written kill/pivot rule before any parser code is written.
- Config layer in src/ootp_ai: resolve OOTP_INSTALL, OOTP_SAVED_GAMES, OOTP_LEAGUE, OOTP_SNAPSHOT_ROOT and MySQL settings from .env only — no literal path, no parents[N] walk outside test modules. Must handle the measured trap that a `*.lg` glob is not a list of saves: the saved-games root contains a stray empty directory literally named `.lg` (verified on disk 2026-08-16), so the enumerator confirms players.dat and teams.dat exist before accepting a save.
- Snapshot step: copy the .lg directory to an immutable, per-sim-date location under OOTP_SNAPSHOT_ROOT with a manifest carrying per-file size and SHA-256, opening every source file 'rb'. Assert Challenge Mode from the filesystem via challenge.dat at exactly 241 bytes (measured in OOTP-AI.lg) rather than from a menu. All parsing runs against the snapshot, never the live save.
- Header/version guard as a shared primitive: magic at offset 1 (not 0), u32 version == 25 at offset 5, and the header's embedded filename cross-checked against the file opened. Measured directly on OOTP-AI.lg/teams.dat on 2026-08-16: `00 4f 4f 54 50 19 00 00 00 0b 00 00 00 68 00 00 00 54 00 00 00 01 00 00 00` + "teams.dat" null-padded — byte-for-byte what docs/data-access.md §4 claims.
- Sequential record walkers for teams.dat, players.dat, names.dat and scouting.dat. No fixed offsets anywhere. Each parsed field carries a declared epistemic label in the tracked contract declaration; anything not validated against players.csv or ootp_truth_real ships `unconfirmed` and is not renderable.
- names.dat join, brute-forced against a full answer key rather than guessed: the probe save's names.dat plus ootp_truth_real.players.first_name/last_name for all 18,072 active players. This is the FR's own 'largest single unknown' and it is the blocker for the roster report specifically.
- Landing to the `ootp` MySQL database (empty today) as bronze, 1:1 with parser output — typing, casing, dedup only, no joins, no filtering, no semantic renaming. Tables: teams, players, player_scouted_ratings, names, team_record. snapshot_date is part of every primary key. Loading a snapshot replaces only that snapshot's partition; it never restates another.
- The five contracts, settled and enforced, not merely written down. GRAIN: one row per team per snapshot; one row per player per snapshot; one row per player PER SCOUTING PERSPECTIVE per snapshot (the grain the FR did not name — collapsing the two perspectives would destroy the OSA-vs-ours gap ADR 0014 depends on). The snapshot is the stint resolution: a mid-season trade appears as a team_id change between two snapshots, and player-per-team-stint is deferred. KEYS: OOTP's player_id is the only universal key; the Lahman/BBRef historical_id is a nullable attribute and is never a join key in the serving path — measured, only 1,920 of 18,072 active players in ootp_truth_real carry a non-empty one (10.6%). COVERAGE: the full active population across all 15 leagues — MLB (level 1) plus AAA (2), AA (3), A (4, five leagues) and Rookie/complex (6, three leagues), with 34/32/36/72/81 teams by level plus 4 teams belonging to no league at all; retired players excluded. Structural absence is preserved as NULL, not zero: minor-league leagues rows carry rules_active_roster_limit = 0 in the export and that is absence, not a 26-man limit of nothing. UPDATE SEMANTICS: append-only per snapshot, snapshots immutable. LAYER PATTERN: parser + warehouse for everything here; nothing in this request is static reference data.
- Two report renderers producing Markdown under var/ from .env-resolved paths — roster (our organization only) and standings. Neither depends on a single rating, so neither is blocked by the spike's outcome. They must never write to a tracked path: a rendered roster is OOTP's and third parties' player data, and ADR 0006 keeps that out of a public repo regardless of format.
- A generated catalog describing grain, keys, coverage and freshness for every landed table, built from information_schema plus the same tracked contract declaration the DDL and the uniqueness tests read — one declaration, three consumers, so drift is structurally impossible. Rendered to var/ alongside the reports.
- The tracked half of the report channel: two entries in gm/standing-orders.md under its `## Reports` format (owner, policy incl. grain, rationale, review trigger, established seq), plus the ledger row that establishes the precedent. gm/README.md's placement rule splits it exactly here — the rendered report rebuilds from the save so it goes to var/; the DECISION that this report exists does not, so it is tracked.
- docs/league-rules.md verification, tiered honestly. Guaranteed: correct §2's claim that a leagues.dat exists (it does not — 18 .dat files measured in OOTP-AI.lg, none of them leagues.dat), and record which §1 rows the parser could and could not reach, each with a label. Best-effort: extract the league configuration block from teams.dat and diff §1's 25 named columns against it.
- Doc gate output: docs/data-access.md label upgrades for every field the paired-save validation actually proves, §5's critical-path question resolved or explicitly still open, CLAUDE.md's Status and Project map updated, README.md's Status-and-what's-next updated. Routed through /update-docs, never written by the builder — docs/data-access.md is in the data-engineer agent's deny set (data-engineer.md:156) and findings travel as a docs-delta with a proposed label.

### enhancements

```json
{
    "title":  "Make the paired-save differential the primary validation harness, not a one-off test",
    "rationale":  "`Test Save - Standard Mode.lg` and the ootp_truth_real database describe the SAME league state (sim date 2024-03-18, measured). That pairing is the only ground truth that reaches fictional players, minor leaguers and the scouted view — players.csv reaches none of them, covering only ~12,855 real players. Built as a reusable harness (parse -\u003e stage -\u003e one SQL diff report per table), it becomes the regression net for every future parser field and the thing that makes ADR 0002\u0027s \u0027no vendor, no error message\u0027 cost survivable. Built as a single test it gets rewritten from scratch on the next request.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Per-file SHA-256 snapshot manifest with the parse run recorded against it",
    "rationale":  "data-engineer.md\u0027s snapshot-immutability rule exists so data-incident triage is tractable: if the warehouse and the snapshot disagree, the warehouse is wrong. That only works if a row can be traced to the exact bytes that produced it. Cheap now, impossible to retrofit onto snapshots already taken.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Extend tests/test_no_leaks.py to catch rendered game data in tracked files",
    "rationale":  "The existing guard (line 106-113) bans four filenames and two suffixes. A roster report is Markdown — it sails straight through, and it is exactly the artifact this feature starts producing. One careless `git add` republishes OOTP\u0027s and third parties\u0027 player data from a public repo. The guard should assert the report/catalog output roots resolve outside the git worktree.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "challenge.dat and header-filename assertions promoted to a pre-flight check on every run",
    "rationale":  "Both are measured, both cost microseconds, and both catch the class of error where the pipeline is pointed at the wrong save — which under ADR 0003 is the error whose consequences are unrecoverable.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Catalog carries a per-table coverage statement generated from the data, not written by hand",
    "rationale":  "The FR wants the GM to know what it is NOT seeing. \u0027players: 18,072 rows, active only, retired excluded, 1,920 carry an external ID\u0027 is far more useful to a GM deciding whether to spend an action than a table name — and generated from counts it cannot go stale.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Settle the ADR 0004 dbt adapter question and build silver/gold as dbt models",
    "rationale":  "ADR 0004 §Notes already says option 3 (MySQL landing + Postgres analytics) or option 4 (Postgres outright) is \u0027likely correct on the evidence\u0027 and that superseding the ADR is expected rather than a failure. Doing it here would put the medallion on a first-class adapter from day one. It is excluded from core because it forces an ADR supersession to serve two reports, and because a second engine is real operational weight for a fun side project.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "Land coaches.dat as the staff/sensor dimension",
    "rationale":  "ADR 0014:44-46 states plainly that coaches.dat \u0027is not organizational furniture — it describes the resolution of the front office\u0027s entire picture,\u0027 and the scouted-ratings table already keys on scouting_coach_id (measured: coach 2759 is our head scout\u0027s perspective). Without it the two perspectives are two anonymous integers. Excluded because it widens the parser surface and the FR puts advisors out of scope.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "Run the second ground-truth export into the empty ootp_truth_osa database",
    "rationale":  "The database exists with 0 tables (measured) because ops/mysql-bootstrap.sql created it. An OSA-view export would let us prove which of the two exported perspectives corresponds to which in-world source, rather than inferring it from scouting_coach_id = -1. Excluded because it needs an in-game export run by the operator on a disposable save, which is his time, not the build\u0027s.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "Parse the leagues/divisions structure well enough to verify all of docs/league-rules.md §1",
    "rationale":  "§1\u0027s 25 columns are the FR\u0027s third desired outcome, and §4 argues that diffing rules_fa_minimum_years each offseason is the cheapest guard the club has against a rule change that reprices the entire farm. Held out of core only because there is no leagues.dat to read — the block has to be found inside teams.dat first, and that discovery cost is unbounded.",
    "cost":  "grows-build"
}
```

### risks

- THE PROJECT-THREATENING ONE: if the spike shows the scouted view is computed at render time rather than stored in scouting.dat, ADRs 0012, 0014 and 0016 have no data path and the front office can read the answer key and nothing else (docs/data-access.md:281-295). The reshape mitigates the schedule risk by decoupling the two reports from ratings, but it does not mitigate the design risk. The written pivot rule has to exist before the spike runs, not after it returns.
- names.dat's index encoding is `unconfirmed` and is the roster report's hard blocker — 'a roster report of integers is not a roster report.' Mitigated by a full answer key (18,072 known names in ootp_truth_real against the probe save's own names.dat), but if the encoding is a hash or a per-save permuted table rather than a positional index, the brute-force may not converge.
- There is no leagues.dat. docs/league-rules.md:129-131 asserts the parser will read one; measured, it does not exist. The §1 verification deliverable rests on finding the league configuration block inside teams.dat, and that discovery cost is genuinely unbounded — which is why §1 is tiered rather than promised.
- ootp_truth_real describes a DIFFERENT universe. Its player_ids, team_ids and ratings belong to the probe league at 2024-03-18, not to OOTP-AI at 2024-03-07. It validates the DECODER, never our club's values. Treating a probe value as a fact about our roster is the exact category error CLAUDE.md's 'This is not the 2024 season' warns about, one level down.
- The probe save is 11 days simmed past its start and our league is unsimmed. ADR 0002 §Notes says day-0 state is the least informative possible test input because every variable-length region is at its minimum. The probe is only marginally better — game_logs is at 0 rows (measured), so neither save exercises grown stat arrays. A parser that passes both could still break on the first genuinely simulated snapshot.
- DOCTRINE RISK, and it is the one an engineering panel will underweight: shipping two reports as infrastructure hands the GM information it did not commission. ADR 0016:110-116 says infrastructure is free and analytical direction is not, which supports it — but the boundary is a precedent, it becomes ledger seq 2, and every later request will cite it. Get it ruled and recorded, or the report channel opens with an unadjudicated exception at its root.
- PUBLIC-REPO RISK. This feature is the first thing in the repo's history that renders OOTP's player data to a file. ADR 0006 keeps that out of a public repo, and the existing guard only catches four filenames and two suffixes — a Markdown roster is invisible to it.
- tests/test_doc_links.py fails CI on any tracked Markdown link into var/ (a live defect, requests/bugfix-requests/_done/doc-link-guard-mismatch symptom B, which names `var/snapshots/2024-03-07/` as a reproduction). Pointing the GM's forced-read list at a var/ path via a tracked link turns CI red, and on a fresh clone the target does not exist at all. The GM must be handed report paths at spawn time by the umpires.
- FIRST DEPENDENCY. pyproject.toml:9 has `dependencies = []` and lines 11-15 say the first real dependency arrives with the warehouse loader. This is that moment, and the choice of MySQL driver plus mypy-strict stubs is a small permanent commitment on a repo that has taken none.
- A mis-mapped u16 raises nothing. requests/README.md:20-31 is explicit that this failure mode has no reproduction and no stack trace, and it is why the bugfix track exists. Any field that reaches a report without paired-save validation behind it is a liability wearing the shape of a feature.
- SCALE. players.dat is 32,070,106 bytes and holds ~18,072 active players plus references into a 154 MB retired.dat we are not landing. Name indices or historical_ids may point outside the landed population; those are structurally absent and must be NULL, never dropped and never zero.
- The reports could be too thin (the GM burns early actions re-asking for things any GM already has) or too rich (the information-strategy tension the project exists to create never appears). The FR's Open Question 5 is a design question no test settles, and only a played week answers it.

### open_questions

- Does the spike's answer change the SCOPE or only the labels? If scouting.dat proves to hold the scouted view, does landing player_scouted_ratings stay in this slice, or does it become slice two now that the reports no longer depend on it?
- Is shipping two uncommissioned reports free infrastructure or a commissioned analysis? Recommend free, with a ledger row and the reasoning that a roster and the standings are what a GM has on his desk without asking — but this is an umpire ruling (ADR 0013), not an engineering call, and it sets precedent for every report that follows.
- Does deferring silver/gold need an ADR? ADR 0005 says snapshot facts go to a dbt medallion. This scope keeps the pattern and postpones the layering. A note in ADR 0004 §Notes recording the trigger seems proportionate; a superseding ADR seems heavy for a postponement. The operator should choose, because quietly diverging is the one option the repo forbids.
- Where exactly does the GM get its report paths? Recommend the umpires pass them at spawn time and gm/standing-orders.md carries the registry, because .claude/agents/gm.md:16-33 is a tracked forced-read list and a link into var/ turns CI red today. But that means a cold session must know to do it, which is a new umpire obligation nothing currently records.
- Which rating scale do the reports render? ADR 0012 says 'at the scale the game displays them,' which is 20-80 on the player page and 1-100 in reports (docs/data-access.md §5) against ~1-1000 in storage. A wrong choice here does not fail a test — it just makes every number the GM sees mean something other than what it says.
- Is `Test Save - Standard Mode.lg` safe to keep? Every value claim in this scope's validation strategy depends on it staying on disk and unsimmed. It is described as disposable in ADR 0002 and docs/data-access.md §6; it should be reclassified as a retained validation asset, or the parser loses its only ground truth for fictional players the day someone tidies it up.
- What is the acceptable parse-time budget? The FR asks for extraction cost as a contract but names no number. It should be stated before the build so criterion 11 is a threshold rather than a rubber stamp.
- Does anything need to guard the GM's tool grant? The FR notes a shell is a superset of a web tool. The `gm` agent holds only Read and Glob today (.claude/agents/gm.md:4) and nothing in tests/ asserts that. tests/test_agent_contract.py guards the data-engineer definition only — an equivalent guard on the GM's grant may belong here or may belong in its own request.

---

## Lens: (unnamed lens)

### scoper

ambitious

### ok

```json
true
```

### fit

```json
{
    "verdict":  "clean",
    "rationale":  "This is the canonical ADR 0005 case and the repo is shaped for it. The boundary rule — \u0027does this artifact change when the league is simulated?\u0027 (docs/decisions/0005-hybrid-data-layer.md, Notes) — answers YES for every artifact the request names: rosters, ratings, standings, league config. So it is parser + dbt medallion in MySQL (ADR 0004), which is exactly what CLAUDE.md\u0027s project map reserves src/ootp_ai/ and transform/ for. It is also the vertical slice CLAUDE.md asks for (\u0027save -\u003e parser -\u003e warehouse -\u003e model -\u003e a decision you can actually act on\u0027) rather than a horizontal layer, and it satisfies ADR 0016/0017 by delivering reports to a Read+Glob-only GM rather than query access. The request\u0027s own Stage plan correctly fires triggers 1 and 3 in requests/README.md §Weight.\n\nTwo things must be said out loud rather than diverged from quietly.\n\n(1) It FORCES a deferred ADR decision. docs/decisions/0004-mysql-warehouse.md §Notes says the dbt-adapter question \u0027comes due when the first dbt model is requested\u0027 and lists four live options. This request is that moment. Verified: pyproject.toml lines 26-29 deliberately carry no `transform` dependency group. The scope cannot ship without disposing that question, and CLAUDE.md §Outstanding scaffolding work names it too.\n\n(2) It CORRECTS an accepted doc. docs/league-rules.md §6 says \u0027Until the parser can open leagues.dat, every value here is believed.\u0027 Measured today: there is no leagues.dat. The OOTP-AI.lg and \u0027Test Save - Standard Mode.lg\u0027 directories contain coaches, faces, flag_save_completed, games_in_progress, human_managers, messages, names, offers, parks, players, retired, scouting, storylines, teams, text_data, trades, weather, world (+ challenge.dat in OOTP-AI only) and nothing else. Inferred: league/sub_league/division records live inside teams.dat, since the export emits leagues, sub_leagues, divisions and teams from one file. §6 and §2\u0027s \u0027The parser reads leagues.dat directly\u0027 both need a correction routed through /update-docs.\n\nBeyond fit, the request materially UNDER-SELLS the assets already on disk, and an ambitious scope should exploit them (see enhancements): the disposable standard-mode probe save that produced ootp_truth_real still exists at OOTP_SAVED_GAMES/\u0027Test Save - Standard Mode.lg\u0027, which turns parser validation from \u0027spot-check against players.csv\u0027 into a full row-for-row differential against a 72-table export of the very same bytes."
}
```

### goals

- Give the GM sight: a cold `gm` subagent spawn returns a handoff whose `## situation` names real Red Sox players with real names and cites a report, not integers — the request's own observable signal.
- Land a first vertical slice of the pipeline that is correct rather than merely present: sequential-walk parser for teams.dat, players.dat, names.dat and scouting.dat -> immutable snapshot -> bronze/silver/gold in the `ootp` MySQL schema -> two rendered Markdown reports.
- Close, or definitively fail, the project-threatening unknown FIRST: is the scouted rating view stored in the save, or computed at render time (docs/data-access.md §5, request Open Question 1). Nothing downstream is built until a written pass/fail spike answers it.
- Resolve names.dat so a roster report is a roster report: a two-file index join that produces first/last names validated field-for-field against 132,990 export rows.
- Settle the five dataset contracts — grain, keys, coverage, update semantics, data-layer pattern — as declared-and-tested facts, not prose, per requests/feature-requests/README.md §Every dataset comes from here.
- Build a two-tier ground-truth validation architecture and label every parsed field with the tier that proved it: Tier A `players.csv` (raw ~1-1000, exact, shipped real players only); Tier B the `ootp_truth_real` export of the still-on-disk probe save (exact for identity/names/rosters/config/standings, BUCKETED for ratings).
- Make ADR 0012 mechanically enforced rather than promised: a withhold ledger plus a test asserting no gold model or report template can reference a true-rating column, `players.prone_*` or `players_value.*`.
- Generate a warehouse catalog from warehouse metadata so it cannot drift, and make it describe what was WITHHELD as well as what was landed — so the GM can see the shape of its own blindness and price an action against it (ADR 0016).
- Pin docs/league-rules.md §1 against parsed values from OOTP-AI.lg and record the diff (or its absence) with a date, discharging §6's 'first real job for the parser'.
- Fail loudly on an unrecognized save version rather than misparsing it, and make the header self-check (magic at offset 1, version 25 at offset 5, self-naming filename at offset 25) a precondition of every file open.
- Answer the extraction-cost contract with a measured number, so the later 'is weekly re-ingestion viable' decision has evidence.
- Dispose ADR 0004's deferred dbt-adapter question in writing, since this is the first dbt model.

### non_goals

- Any advisor, of any domain. The request puts them explicitly out and ADR 0017 makes them umpire-spawned on a GM commission — they need the network/shell question answered first (request Constraints, last bullet).
- A third report. Two — roster and standings — is the deliberate 'how thin is thin' setting; widening it is a GM action under ADR 0016, not an engineering decision.
- Serving any other organization's roster or ratings to the GM. Landing 259 teams is a warehouse fact; exposing 29 other clubs' players in a GM-readable report is not.
- retired.dat. Measured: 141-147 MB and 114,918 rows in the export — it triples parse cost for zero day-0 decision value.
- Statistical history, career stats, game logs, transactions. Measured: on a fresh save every text_data table except player_history is at 0 rows (docs/data-access.md §3), and the league is unsimmed at 2024-03-07.
- The in-game HTML report path (docs/data-access.md §7) and text_data.sqlite3 / text_data.dat (the newspaper).
- Incremental or weekly re-ingestion, scheduling, or change-data-capture. Exactly one league state exists; snapshot KEYS are in scope, snapshot ORCHESTRATION is not.
- Any write to the game, of any kind — no save edits, no roster import files, no UI automation, no export triggered against OOTP-AI (ADR 0001, ADR 0003; challenge.dat is present at 241 bytes in OOTP-AI.lg and one write is unrecoverable).
- True ratings anywhere in the serving layer. They exist in the ground-truth schema and in tests against fixtures, and nowhere else (ADR 0012 Forecloses).
- Network access for anything this creates. No WebFetch, no WebSearch — and no new agent gets PowerShell, because a shell is a superset of a web tool.
- Committing any OOTP data. No .dat, no players.csv, no export dump, no save snapshot (ADR 0006; .gitignore lines 25-31 block these by name and extension, so fixtures must be derived JSON).
- Re-litigating ADR 0002 (parser not export), ADR 0003 (Challenge Mode), or ADR 0012 (scouted only). The export's only sanctioned role here is ground truth from the disposable standard-mode save.
- Building transform/, build/ or datasets/ beyond what these two reports and the field map actually need — CLAUDE.md forbids creating them speculatively.

### acceptance_criteria

- `uv run pytest tests/test_save_header.py` is green: the reader accepts a header whose byte 0 is 0x00, bytes 1-4 are b'OOTP', and u32 at offset 5 == 25; and raises `UnsupportedSaveVersion` (not a parse result) for version 24, version 26, a b'OOTP' at offset 0, and a header whose self-named filename at offset 25 disagrees with the file actually opened. Runs offline against derived byte fixtures — no game install (data-engineer.md: 'Never require a game install to satisfy a test').
- `uv run pytest tests/test_no_fixed_offsets.py` is green: a static check over src/ootp_ai/parser/** finds zero calls to `seek(<int literal>)` on a record-relative handle and zero module-level offset-table constants keyed to a record start. Encodes the invariant as a test rather than a review convention.
- `uv run pytest tests/test_parser_names.py -m gamedata` is green: every name index the parser resolves out of the probe save's players.dat matches `ootp_truth_real.players.first_name` / `.last_name` for all 132,990 rows, exact string equality, zero mismatches, zero unresolved indices.
- `uv run pytest tests/test_parser_vs_export.py -m gamedata` is green: parsing 'Test Save - Standard Mode.lg' and diffing against `ootp_truth_real` yields zero mismatches on player_id set (18,072 active), teams (259 rows: team_id, name, nickname, abbr, league_id, sub_league_id, division_id, level, parent_team_id), team_record (259 rows: g/w/l/pct/gb/pos), leagues (15 rows, every `rules_*` column named in docs/league-rules.md §1), and team_roster (15,672 rows at grain team_id+player_id+list_id).
- `uv run pytest tests/test_rosetta_ratings.py -m gamedata` is green: for every player present in BOTH players.csv and the parsed probe save, all 18 values of the ratings block match players.csv EXACTLY on the raw ~1-1000 scale — no tolerance, no bucketing. This is the only exact rating validator and it is Tier A.
- `uv run pytest tests/test_rating_scale.py -m gamedata` is green: applying the derived internal->display mapping to parsed raw ratings reproduces the export's display values for >=99.9% of (player, rating) pairs, and the mapping's codomain is exactly the 12 observed buckets {20,25,30,35,40,45,50,55,60,65,70,80}. Any pair outside tolerance is listed by name in the failure message rather than averaged away.
- `uv run pytest tests/test_scouting_spike.py -m gamedata` is green OR the spike's written verdict is recorded as a blocking finding: it asserts scouting.dat length is an exact integer multiple of the per-player stride against the active-player count, and that parsed per-perspective scouted values reproduce `ootp_truth_real.players_scouted_ratings` (after scale conversion) for both `scouting_coach_id` values, for >=99% of players. A FAIL here stops the build and escalates — it is not routed around.
- `uv run pytest tests/test_grain.py` is green: uniqueness holds on (snapshot_id, player_id) for silver_player; on (snapshot_id, team_id) for silver_team and silver_team_record; on (snapshot_id, league_id) for silver_league; on (snapshot_id, team_id, player_id, list_id) for silver_player_roster_assignment; and on (snapshot_id, player_id, scouting_perspective) for silver_player_scouted_ratings. Each model's docstring/YAML grain sentence is asserted to match the tested key — the two must AGREE, not merely both exist.
- `uv run pytest tests/test_grain.py::test_player_is_not_unique_in_roster` is green: it asserts that player_id is NOT unique within a single snapshot's roster assignments — measured, 37 players appear under two team_ids on a day-0 un-simmed save. This is a positive assertion that the team-stint grain is real, so a later refactor cannot silently collapse it.
- `uv run pytest tests/test_keys.py` is green: player_id is non-null and covers 100% of landed players; the Lahman/BBRef id is nullable, its null rate is recorded in the catalog, and a static check finds zero JOIN/ref conditions in transform/models/** using it as a key. Measured coverage to assert against: 1,920 of 18,072 active (10.6%).
- `uv run pytest tests/test_structural_absence.py` is green: for the 14 non-MLB leagues, every `rules_*` roster/service column lands as NULL rather than 0 (measured: the export writes 0 for rules_active_roster_limit, rules_fa_minimum_years and rules_salary_arbitration_minimum_years on all 14), and any silver/gold aggregate over those columns excludes NULLs explicitly.
- `uv run pytest tests/test_snapshot_immutable.py` is green: landing the same snapshot_id twice raises rather than overwriting; the snapshot manifest's content hash of the source .dat set is recorded and re-verified before parse; and parsing the same snapshot twice produces byte-identical parser output.
- `uv run pytest tests/test_withhold.py` is green: no model under transform/models/gold/**, no report template, and no catalog entry marked GM-readable references any column classified `true-rating`, `unclassified`, `players.prone_*`, or `players_value.*`. A field with epistemic label `unconfirmed` and category `rating` is asserted to be in the withhold ledger (ADR 0012's parser corollary).
- `uv run pytest tests/test_reports.py` is green: the roster report renders exactly 26 player rows for the club named by OOTP_LEAGUE's human team; every row's name field matches `^[A-Za-z][A-Za-z .'-]+$` (i.e. it is a name, not an integer); no rendered numeric column is sourced from a withheld field; and the standings report renders 30 rows carrying division, W-L, pct, GB and playoff seed including the top-two bye flag.
- `uv run pytest tests/test_catalog.py` is green: the catalog is REGENERATED from warehouse information_schema during the test and the regenerated structural section is byte-identical to the tracked copy (proving it cannot drift by hand); every landed table has a grain sentence, a coverage population, a key list, an epistemic label and a source .dat file; and every withheld field group is listed with its reason.
- `uv run pytest tests/test_league_rules_diff.py -m gamedata` is green: every `rules_*` value in docs/league-rules.md §1 is diffed against the parsed OOTP-AI league record and the result — agreement or a named list of differences — is written to a dated artifact. The query layer is asserted to backtick reserved identifiers; a regression case proves `current_date` returns the league's sim date and not the wall-clock date. (Measured trap: unquoted `select current_date from leagues` returned 2026-08-16 for all 15 rows because MySQL parsed it as the CURRENT_DATE function.)
- `uv run pytest tests/test_no_leaks.py tests/test_repo_structure.py tests/test_agent_contract.py tests/test_doc_links.py` stays green after the change, and `uv run pytest -m "not gamedata"` passes with no game install and no MySQL server present — CI's actual condition.
- `uv run pytest tests/test_extraction_cost.py -m gamedata` is green and EMITS a number: wall-clock seconds for a full parse of the in-scope files, recorded in the catalog. The assertion is that the number exists and is recorded, not that it beats a threshold nobody has justified.
- USER-RUN (marked so the acceptance panel does not claim it): a cold session spawns the `gm` subagent with the two reports attached; its returned handoff's `## situation` names real Boston players with real names, cites the report as the source for each factual claim, and its `## assumed` section is empty of roster facts. Per requests/feature-requests/README.md, criteria only a human can prove must be marked user-run.
- USER-RUN: the OOTP-AI.lg save's file set, sizes and modification times are unchanged before and after a full ingestion run — the read-only guarantee, checked by the operator against a recorded manifest rather than asserted by the code that would violate it.

### core_scope

- A **spike-first gate**: before any modeling, a written spike answers docs/data-access.md §5's critical-path question with a pass/fail. Strong prior evidence already gathered (see risks): scouting.dat is 2,349,181 bytes = 129.99 bytes per active player against the export's 18,072 actives, and at offset 228 carries two adjacent near-identical u16 sequences (0x0161,0x01aa,0x01a4,0x0162,0x0154,... vs the same with 0x0155) plus two adjacent near-identical byte sequences — measured. Inferred: two stored perspectives per player at internal scale. The spike converts this from inference to verified or kills the design.
- **Save-file reader core** in src/ootp_ai/: header validation (magic at offset 1, u32 version==25 at offset 5, self-naming filename at offset 25 cross-checked against the file opened) raising `UnsupportedSaveVersion` on any mismatch; primitive decoders for u32-length-prefixed ASCII strings, u8/u8/u16 dates, u32 ARGB colors, u16 ratings, u32 money, f64 year-keyed series (docs/data-access.md §4).
- **Sequential record walkers** for teams.dat (leagues, sub_leagues, divisions, teams, team_record), players.dat (identity, name indices, DOB, uniform number, ratings block, contract array, Lahman/BBRef id), names.dat (the string table), scouting.dat (per-perspective scouted ratings). No fixed offsets, no seek-to-constant; a leftover-bytes tail check at the end of every file as the cheap silent-misparse detector.
- **names.dat join**: resolve the u32 index players.dat holds into the name table. Measured structure to build against — records read `u32 len` + ASCII + `u32 0` + `u32 monotonic index` + three u32s + a 0x27 separator, alphabetically ordered ('A.C.','A.J.','AHei','Aad','Aalto','Aamir','Aanand','Aapo' carrying indices 1..8).
- **Snapshot manager**: copy the in-scope .dat files from the live .lg to OOTP_SNAPSHOT_ROOT/<league>/<sim_date>/ with a content-hash manifest; parse the snapshot, never the live save; refuse to overwrite an existing snapshot_id. Measured cost win: the in-scope files total ~53 MB (players 30.6 + names 8.2 + world 8.5 + teams 5.1 + scouting 2.7 + coaches 2.3) versus ~600 MB for the whole directory, because retired.dat (147 MB) is out.
- **Bronze landing** into the `ootp` MySQL schema (measured: currently 0 tables), 1:1 with parser output plus snapshot_id — typing, casing, dedup only. No joins, no filtering, no semantic renaming.
- **Silver conformance** with declared-and-tested grain: silver_player (snapshot_id, player_id); silver_team (snapshot_id, team_id); silver_team_record (snapshot_id, team_id); silver_league (snapshot_id, league_id); silver_player_roster_assignment (snapshot_id, team_id, player_id, list_id); silver_player_scouted_ratings (snapshot_id, player_id, scouting_perspective).
- **Gold serving models** for exactly two products: the club's active roster and the MLB standings — the only two the reports need.
- **Two rendered Markdown reports** the GM reads with its Read/Glob grant: `Active Roster` (26 players, names, position, age, bats/throws, scouted ratings at display scale, contract) and `Standings` (30 clubs by division, W-L-pct-GB, seed, top-two bye flag). Registered in gm/standing-orders.md in the report format that file already defines.
- **Generated warehouse catalog** built from information_schema plus the field map: per table, its grain sentence, key list, coverage population, row count, source .dat file, epistemic label, and freshness. Plus a **withhold section** naming what was deliberately not served and why.
- **The field map as a first-class artifact** carrying, per field: name, type, the walker that reads it, category (identity / rating-true / rating-scouted / contract / structural), epistemic label, and the validator that produced the label. This is derived schema knowledge and is ours to track (ADR 0006 Notes).
- **Two-tier ground-truth harness.** Tier A: players.csv, exact, raw ~1-1000 scale, shipped real players only. Tier B: the `ootp_truth_real` export (measured: 72 tables, 2.28M rows) diffed against a parse of the probe save that produced it — exact for ids, names, strings, dates, money, team assignment, roster lists, league config, standings; BUCKETED for ratings and therefore not usable as an exact rating validator.
- **A new .env key naming the probe save directory** (e.g. OOTP_TRUTH_SAVE) so the Tier B harness resolves by name and never hardcodes 'Test Save - Standard Mode' — CLAUDE.md's resolve-from-.env rule and tests/test_no_leaks.py.
- **docs/league-rules.md §1 verification**: diff every `rules_*` value against the parsed OOTP-AI league record and record the result with a date. Measured enabling fact: every column §1 names exists on the export's `leagues` table (rules_active_roster_limit, rules_secondary_roster_limit, rules_expanded_roster_limit, rules_min_service_days, rules_fa_minimum_years, rules_salary_arbitration_minimum_years, rules_minor_league_fa_minimum_years, rules_waiver_period_length, rules_dfa_period_length, rules_minor_league_options, rules_rule_5, rules_salary_cap, rules_luxury_tax, rules_luxury_sharing_cap, rules_revenue_sharing_tax, rules_national_media_contract_fixed, rules_owner_decides_budget, rules_fa_compensation, rules_draft_pick_trading, trade_deadline_date, rules_amateur_draft_rounds, rules_schedule_games_per_team, rules_schedule_balanced, rules_schedule_inter_league), so the diff is mechanical.
- **A written disposition of ADR 0004's adapter question** — pin dbt-core 1.7, drop dbt, MySQL-landing + Postgres-analytics, or move to Postgres — landed as an ADR amendment or a new ADR before the first model merges.
- **A docs correction routed through /update-docs**: docs/league-rules.md §2 and §6 both assert a `leagues.dat` that does not exist; docs/data-access.md §1's file table omits faces/flag_save_completed/games_in_progress/human_managers/messages/offers/storylines/text_data/trades/weather and lists `temp/text_data.sqlite3` without noting the sibling `text_data.dat`.
- **Coverage decision, stated and tested**: land all 15 leagues (levels 1-6), all 259 teams, all 18,072 active players. Minor-league league rows carry structural NULLs, not zeros.

### enhancements

```json
{
    "title":  "Full parser-vs-export differential harness against the probe save that is still on disk",
    "rationale":  "The single highest-leverage asset in this repo and the request barely mentions it. Measured: OOTP_SAVED_GAMES contains \u0027Test Save - Standard Mode.lg\u0027 (players.dat 27.33 MB, names.dat 8.24 MB, teams.dat 4.34 MB, scouting.dat 2.24 MB) AND `ootp_truth_real` holds a 72-table, 2,278,481-row export of that same league state. That means the parser can be validated row-for-row, field-for-field, against 132,990 player rows, 259 teams, 15,672 roster rows and 15 league rows — not spot-checked. players.csv alone covers ~12,855 shipped real players at day-0 and cannot validate names, roster lists, standings, or league config at all. This harness is the difference between \u0027the ratings look about right\u0027 and a cold agent running one command. It also becomes the permanent regression suite for every future parser change and every game patch.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "Derive and register an internal-\u003edisplay rating-scale dataset, and make the correctness trap a test",
    "rationale":  "CLAUDE.md names scale conversion as \u0027the single most likely way to silently corrupt every downstream recommendation\u0027 and offers only a prose warning. Measured today: the export\u0027s true-rating column players_batting.batting_ratings_overall_contact has exactly 12 distinct values spanning 20-80 (20:81893, 25:14514, 30:23858, 35:7036, 40:2624, 45:1752, 50:932, 55:277, 60:74, 65:24, 70:5, 80:1) — the export is display-scale, not raw. So the export cannot validate exact rating bytes, and the mapping between raw u16 and display bucket is knowable by fitting parsed players.csv values against the export. Materialize that mapping as a builder dataset under datasets/ registered by name in datasets/manifest.json (ADR 0005: it changes only on a game patch, so it is a builder, not a dbt model). Every rating the GM ever sees passes through one audited, tested, named artifact instead of an inline constant.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Field map as a tracked, named dataset rather than code constants",
    "rationale":  "ADR 0006 Notes explicitly blesses this: \u0027The ratings block is 18 contiguous u16 values ordered vR, vL, potential\u0027 is our observation and may be published. Making the field map data — name, type, category, epistemic label, validating tier — rather than Python constants means (a) the withhold test can read it, (b) the catalog can render it, (c) a game patch becomes a data change plus a re-validation run instead of a code rewrite, and (d) docs/data-access.md\u0027s §4 \u0027Confirmed field semantics\u0027 section stops being a hand-maintained second copy. It is also the artifact the bugfix track\u0027s README says is the case where a wrong fix is unrecoverable — making it inspectable is a direct mitigation.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "Catalog names what is WITHHELD, not just what is landed",
    "rationale":  "The request wants \u0027the GM knows what it is not seeing.\u0027 A catalog of landed tables only tells it what it CAN see. Listing the withheld groups — true-rating tables, players.prone_*, players_value.*, and every field whose classification is still `unconfirmed` — with the reason and the ADR, means the GM can price an action against a known gap rather than discovering the gap by hitting it. This is directly the information-strategy tension ADR 0016 exists to create, and it costs one extra generated section.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Report renderer as a registry, so report #3 costs a template rather than a build",
    "rationale":  "Reports are the ONLY channel to the GM under ADR 0016, and gm/standing-orders.md already defines a report as (name, owner, policy, rationale, review trigger). Building two bespoke scripts wastes that. A registry where a report = (name, owner, gold model, template, review trigger) makes commissioning a report a genuine GM action with a real, small marginal cost — which is exactly the economy ADR 0013 wants — instead of an engineering request every time. It also lets the catalog enumerate available reports.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "`parse --stats` with an unparsed-byte tail assertion on every file",
    "rationale":  "requests/README.md is explicit that the parser\u0027s failure mode has \u0027no reproduction in the usual sense and no stack trace\u0027 — it returns a plausible number. A sequential walker that consumed N-k of N bytes has almost certainly mis-sized a record. Asserting the tail is empty (or a known constant footer) is the cheapest possible detector for the exact failure class this repo fears most, and it costs a counter and an assertion.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Snapshot content-hash manifest and a read-only proof for the Challenge Mode save",
    "rationale":  "data-engineer.md makes snapshot immutability an invariant precisely so that \u0027if the warehouse and the snapshot disagree, the warehouse is wrong.\u0027 Recording a per-file content hash at snapshot time also gives the operator a cheap, independent way to prove no ingestion run ever touched OOTP-AI.lg — where challenge.dat is present at 241 bytes and one write is unrecoverable (ADR 0001, ADR 0003). Bonus measured win: the in-scope file set is ~53 MB, not the ~600 MB docs/data-access.md §1 warns about, because retired.dat is out — so snapshots are cheap enough to keep many.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Land coaches.dat now, report nothing from it",
    "rationale":  "The scouting perspective key is a coach id, not a label. Measured: players_scouted_ratings.scouting_coach_id takes exactly two values, -1 (18,072 rows, scouting_accuracy uniformly 3.0) and 2759 (18,072 rows, mean accuracy 2.2186), and coach 2759 resolves via the coaches table to Dan Kantrovitz, occupation 6, team 6 — the human club\u0027s scouting director in that probe save. Without coaches.dat the parser must hardcode \u0027the club\u0027s own scout is coach X\u0027, which is exactly the brittleness ADR 0014 will punish. coaches.dat is 2.26 MB and the walk is the same machinery. Serving it to the GM stays out of scope; landing it does not.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Standings report carries seeds and the bye flag, not just W-L",
    "rationale":  "docs/league-rules.md §3 argues at length that \u0027the bye is worth more than the standings suggest\u0027 — 12 of 30 qualify, top two seeds skip a best-of-3 coin flip — and warns that \u0027a model that treats wins as fungible gets this wrong.\u0027 A standings table that renders only W-L-GB hands the GM exactly the model the rules document says is wrong. Adding seed and bye-eligibility is a few lines of gold SQL and makes the report decision-relevant on the day it ships.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Reserved-identifier guard for every export-diff query",
    "rationale":  "Measured live: `select league_id, name, current_date from ootp_truth_real.leagues` returned 2026-08-16 — the wall-clock date — for all 15 rows, because MySQL parsed the column name as the CURRENT_DATE function. Nothing errored. That is a textbook data incident (requests/README.md\u0027s \u0027ran green and the data is wrong\u0027) sitting in the exact code path the league-rules diff harness will use, and the diff would have silently reported the sim date as wrong. A backtick-everything rule plus one regression test closes a whole class.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Record the OSA-vs-own-scout divergence as a first-class silver column",
    "rationale":  "ADR 0014\u0027s central claim is that the gap between the public OSA view and the organization\u0027s own read is \u0027an observable measure of what the scouting department adds.\u0027 Measured on the probe export: for overall_contact alone, 8,261 of 18,072 OSA rows and 9,019 of 18,072 own-scout rows differ from the true value, with mean absolute gaps of 2.60 and 2.91 display points. Landing both perspectives side by side with a computed divergence is nearly free once both are parsed, and it is the foundation of every future \u0027was the scouting director worth it\u0027 analysis. Serving it is a later GM commission; landing it now costs one model.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Machine-readable catalog sibling (catalog.json) alongside the Markdown",
    "rationale":  "The GM holds Read and Glob and reads Markdown. Future advisors — which the umpires spawn under ADR 0017 — will want to discover tables, grains and reports programmatically without re-reading prose. Emitting both from one generator costs a second writer and prevents a later hand-maintained second copy, which is the drift failure the request explicitly wants the catalog to avoid.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Retire or document ootp_truth_osa rather than asking the operator to run a second export",
    "rationale":  "Measured: `ootp_truth_osa` exists as a database with 0 tables, and .env.example lines 57-58 provision it as a separate export target on the theory that two rating views need two exports. That premise is wrong — ootp_truth_real.players_scouted_ratings already carries BOTH perspectives from a single export, keyed by scouting_coach_id, which is exactly what docs/data-access.md §6 predicted (\u0027Show real player ratings together with Additional complete scouted ratings ... yields both views for the same rows out of one snapshot\u0027). Saying so in the scope saves the operator a disposable-save rebuild and an export run, and removes a permanently empty database from the setup docs.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Land the epistemic label alongside the data, not only in docs",
    "rationale":  "Every parsed column carries a label in the field map; writing that label into a warehouse metadata table means a future data incident can ask \u0027what did we believe about this field on the day it was landed?\u0027 rather than archaeology through git history of docs/data-access.md. It is the difference between a triageable incident and a guess, and requests/data-incidents/ exists specifically because this failure class has no stack trace.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "Extraction-cost benchmark emitted as a recorded metric",
    "rationale":  "The request lists extraction cost as an open data contract and the answer determines whether weekly re-ingestion is viable — a decision that is currently pure guesswork. Emitting per-file parse wall-clock from the existing gamedata test run costs a timer and turns a future architecture decision into a measured one. It also gives the first real data point on whether landing five minor-league tiers was affordable.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Publish the field map and format findings as the repo\u0027s public contribution",
    "rationale":  "ADR 0006 draws the line at derived schema knowledge being ours and publishable, and CLAUDE.md opens by noting this is \u0027a proprietary binary format nobody has a parser for.\u0027 Once the field map is a tracked dataset with epistemic labels and a validating tier, a short docs page makes it genuinely useful to people outside this repo at essentially zero marginal cost — and it costs nothing in-project because the artifact exists either way.",
    "cost":  "cheap"
}
```

### risks

- **The scouting spike can still fail.** Evidence is strong but inferred, not verified. Measured: scouting.dat is 129.99 bytes per active player — but ~130 bytes cannot hold the ~135 rating columns the export emits per perspective, let alone two perspectives. Inferred: scouting.dat stores a compact per-player perception seed/summary and OOTP expands it at render time, OR the full scouted block lives inside players.dat. If neither reproduces the export's scouted values, ADRs 0012, 0014 and 0016 have no data path and this request stops being a parser task and becomes a design problem. The scope must gate on the spike and pre-register what a FAIL triggers rather than discovering it at implementation time.
- **The export cannot validate exact ratings, and a bucketed test can pass a wrong parse.** Measured: 12 distinct display values, 20-80. A parser that reads the adjacent u16 — a different rating entirely — will land in the same bucket often enough to pass a 99% bucketed check. Mitigation is layered: the exact players.csv tier, the unparsed-byte tail check, and per-field (not aggregate) mismatch reporting. Aggregating this test into a single pass rate would recreate exactly the trap CLAUDE.md warns about.
- **The probe save is Cubs-managed, not Boston.** Measured: ootp_truth_real.teams has human_team=1 on team_id 6 (Chicago Cubs), and the own-scout perspective is coach 2759. Any code or test that hardcodes 'perspective 2759 is us' or 'team 4 is us' passes on ground truth and breaks on OOTP-AI. The human team must be resolved from data on both saves.
- **ADR 0004's adapter question is genuinely unresolved and blocks the medallion.** Measured: dbt-mysql caps at 1.7.0 and pins dbt-core~=1.7.0, four minor versions behind; pyproject.toml deliberately carries no transform group. The scope forces a call that ADR 0004 itself flags as likely to supersede the ADR. Deferring it inside the build means the first dbt model lands on an unargued dependency.
- **Catalog placement has no clean answer.** gm/README.md's placement rule ('can this be rebuilt from the save? yes -> var/') sends it to var/, which is gitignored (.gitignore line 18) and therefore absent on a fresh clone — yet the GM's forced-read list points at it and the GM holds only Read and Glob. Splitting structural (tracked) from volatile (var/) is the proposed resolution and it is a genuine compromise, not a clean win: two files, one of which can be stale.
- **Landing five minor-league tiers multiplies coverage edge cases.** Measured: 15 leagues, 259 teams, and every non-MLB league row carries 0 for the roster/service rules columns. Conflating those zeros with real values is the 'structural absence is not missing data' failure the data-engineer rulebook names, and it produces wrong aggregates rather than incomplete ones. Every one of the 14 non-MLB rows is an opportunity to get this wrong.
- **Roster list semantics are unknown.** Measured: team_roster.list_id takes values 1,2,3,4 (7,370 / 7,037 / 935 / 330 rows) and for Boston in the probe save yields 33 / 26 / 30 / 7. list_id=2 giving exactly 26 is suggestive of the active roster, but that is inferred from one club. Building the roster report on a guessed list_id would put a wrong 26-man roster in front of the GM with nothing throwing — the exact failure requests/README.md describes.
- **Snapshot storage on cloud-synced Documents.** docs/data-access.md §1 records the saved-games directory as frequently OneDrive-redirected and warns that snapshotting there would be a mistake. OOTP_SNAPSHOT_ROOT must be validated as local disk at runtime, not assumed.
- **.gitignore blocks .dat by extension (line 31), so no binary fixture can be committed.** Every offline test fixture must be a derived, defensible artifact (JSON field maps, small synthetic byte sequences we authored) rather than a slice of OOTP's files (ADR 0006 Costs: 'Test fixtures cannot be real save files'). This constrains how the header and primitive tests are written and is easy to violate accidentally.
- **One write to OOTP-AI.lg is unrecoverable.** challenge.dat is present at 241 bytes; there is no upstream backup. Every file handle in this feature must open 'rb', and the snapshot-first discipline exists precisely so the live save is touched by a copy operation and nothing else.
- **docs/league-rules.md §1 may disagree with parsed values and the document has no procedure for that.** §1 declares its own lifespan as 'temporary — the warehouse supersedes this the moment the parser lands', but nobody has decided whether a disagreement means the doc was wrong, the parser is wrong, or the league drifted. Resolving a disagreement by editing the doc to match the parser would destroy the only independent check on the parser.
- **Report content is a GM-visible information-policy decision disguised as an engineering one.** Which columns appear on the roster report determines how much the GM sees for free, which is the 'how thin is thin' tension the request wants preserved. An engineer optimizing for a useful report will make it too rich, and the tension the project is built around quietly disappears with nothing failing.

### open_questions

- Does the scouting spike pass? Specifically: does the ~130-byte-per-player scouting.dat block reproduce the export's players_scouted_ratings for BOTH perspectives after scale conversion, or does it hold only a perception seed with the rest expanded at render time? And if it holds only one perspective, where does the OSA view live? Pre-register the FAIL branch before building.
- What do team_roster.list_id values 1, 2, 3 and 4 actually mean? Boston's probe-save counts are 33 / 26 / 30 / 7. Resolve against OOTP's own db_structure_ootp22_csv.txt (docs/data-access.md §2 records it as documenting 70 tables with field names in order) or the in-game roster screens — NOT by assuming 26 means active.
- Which ADR 0004 option is taken — pin dbt-core 1.7, drop dbt for hand-rolled SQL plus a runner, MySQL-as-landing + Postgres-as-warehouse, or Postgres outright? ADR 0004 §Notes says options 3 or 4 are 'likely correct on the evidence' and that superseding is expected, not a failure.
- Where does the catalog live, given var/ is gitignored and the GM holds only Read and Glob? Proposed: structural half tracked (it is derived schema knowledge, which ADR 0006 permits), volatile half generated into var/, with the GM told to tolerate the second being absent. Needs an explicit ruling.
- Do all 15 leagues and 259 teams land in v1, or only MLB with the minors gated to a follow-up? Landing everything widens the catalog for free under ADR 0016 (the GM cannot commission what it does not know exists) but multiplies the structural-absence surface from 1 league row to 15.
- What happens to docs/league-rules.md §1 when parsed values disagree with it? Proposed: the warehouse supersedes (§1 says so itself), the diff is recorded as a dated artifact, and §1 is deleted rather than corrected — but a disagreement is also the strongest available signal that the PARSER is wrong, and deleting the doc destroys that check. Which reading wins needs deciding before the diff runs, not after.
- Is the Lahman/BBRef id in players.dat the same value as the export's players.historical_id? Measured coverage differs — docs/data-access.md §2 records ~1,712 unique in the managed save's players.dat, while the probe export shows 1,920 of 18,072 active players carrying historical_id. Same field with different populations, or two different identifiers?
- How much does the roster report show? Every scouted rating, or a deliberately narrow subset? This is the 'how thin is thin' question and it is a GM-facing policy call the operator should make, not an engineering default.
- Should the report registry write into gm/standing-orders.md automatically, or does an umpire land it by hand? gm/ is the umpires' pen (ADR 0017) and no automated process currently writes there — a generator that does would be the first.
- Does the sim date come from the parsed league record, saved_games.dat (docs/data-access.md §1 records it as plaintext and readable without parsing), or both cross-checked? The snapshot_id depends on it, and getting it from one source with no check is how a snapshot lands under the wrong date.
- Is `ootp_truth_osa` retired, or kept for a future OSA-only export variant? Measured: it currently has 0 tables and ootp_truth_real already carries both perspectives. Keeping it means keeping two .env keys and a setup step that buys nothing.
- Does the version guard refuse anything other than 25, or does it accept a range with a warning? data-engineer.md says 'refuse an unrecognized version rather than misparsing it' — refuse-strictly is the safe reading, but it also means a game patch bricks ingestion until someone re-validates. That is probably correct and should be stated as such rather than discovered.

---

## Lens: (unnamed lens)

### scoper

minimalist

### ok

```json
true
```

### fit

```json
{
    "verdict":  "reshape",
    "rationale":  "The PATTERN fits cleanly: everything here changes when the league is simulated, so ADR 0005\u0027s rule routes it to parser + warehouse, not builder + datasets/. Nothing in the request contradicts a settled ADR. But as written the slice bundles three unbounded items onto one vertical cut and one of its two headline deliverables is measurably empty. (1) STANDINGS ARE EMPTY. Measured 2026-08-16: OOTP-AI.lg/temp/text_data.sqlite3 contains exactly one table, game_logs, at 0 rows; sim date is 2024-03-07 and the league\u0027s first game is 2024-03-20 (docs/league-rules.md:236). Every club is 0-0. A standings report on this snapshot carries zero bits. (2) THE league-rules §1 DIFF HAS NO CHEAP SOURCE. Measured: there is NO leagues.dat in OOTP-AI.lg, nor in either test save — the full file list is challenge/coaches/faces/flag_save_completed/games_in_progress/human_managers/messages/names/offers/parks/players/retired/scouting/storylines/teams/text_data/trades/weather/world. The league-config marker string `major_league_ml_c_2024` (the schedule_file_1 value cited at docs/league-rules.md:80) sits at byte 5,559,751 of world.dat — a file docs/data-access.md:45 describes only as \u0027Nations, states, cities\u0027. So Desired Outcome 3 requires reverse-engineering a FOURTH unmapped 8.9 MB binary to recover ~30 scalar fields, with no ground truth for our league because Challenge Mode has no export. docs/league-rules.md:130 asserts \u0027the parser reads leagues.dat directly\u0027 — that file does not exist. (3) RATINGS COUPLE THE SLICE TO THE PROJECT-THREATENING UNKNOWN. The request puts \u0027enough of scouting.dat to classify true-versus-scouted\u0027 in scope, which makes shipping anything conditional on Open Question 1 (data-access.md §5, unconfirmed). ADR 0014\u0027s own Costs section pre-authorizes the cut: \u0027A warehouse that can name the roster but cannot say how good anyone is is a real possible first milestone.\u0027 (4) A dbt MEDALLION FORCES AN OPEN ADR. ADR 0004 §Notes says the dbt-mysql-vs-Postgres decision \u0027comes due when the first dbt model is requested\u0027 — building one here drags an unresolved architecture call into a request already carrying two unknowns. Reshaped, the core is small and genuinely solves the stated problem: the GM cannot name a single player, and naming players needs identity + roster membership + the names.dat join and nothing else."
}
```

### goals

- Give the GM its roster: a single Markdown report under var/ naming Boston's organizational roster with real player names, roster-list membership, position, age and uniform number — no ratings of any kind.
- Give the GM the menu: a generated catalog under var/ describing every landed table (grain, key, row count, coverage, snapshot date) so the GM can see what exists without seeing the data, per ADR 0016.
- Establish the parser's non-negotiable spine once, correctly: config resolved from .env, a save enumerator that confirms contents rather than trusting a *.lg glob, a header reader whose magic is at offset 1 and whose u32 version at offset 5 must equal 25, and a sequential record walk with no fixed offsets.
- Prove the names.dat join against an independent source — ootp_truth_real.players.first_name/last_name — rather than against a screenshot, so 'the roster has real names' is an assertion and not an impression.
- Land bronze into the MySQL `ootp` schema with snapshot_date in every primary key, append-only and idempotent per snapshot, so the first sim date does not have to be re-keyed later.
- Settle and test the three bronze grains in writing, especially the roster-membership grain that the request does not mention and that is the join most likely to fan out silently.
- Leave behind a regression guard that fails if any rating-shaped column is ever landed, so ADR 0012's withhold rule is enforced by a test from the first commit rather than by prose.

### non_goals

- A standings report. Measured: 0 games played (game_logs = 0 rows), so all 30 clubs are 0-0. Revisit after the first sim; the team dimension will already be landed, so this is a cheap follow-up, not a rewrite.
- Any rating, from any file. No scouting.dat parse, no true/scouted classification, no OSA. This is what makes the slice unblockable by Open Question 1.
- Any dbt model, any silver or gold layer, any transform/ directory. Bronze lands via the loader's own DDL. This keeps ADR 0004 §Notes' adapter decision closed until a request actually needs it.
- The docs/league-rules.md §1 diff. There is no leagues.dat; the config lives inside an unmapped world.dat and there is no export for our Challenge Mode league to diff against. The proposed standing order in league-rules.md §4 is an OFFSEASON cadence — first due ~2024-10 — so there is no urgency.
- datasets/, build/, or a manifest.json entry. ADR 0005 routes this to the parser side; CLAUDE.md says do not create those directories speculatively.
- retired.dat (154 MB), storylines.dat, coaches.dat, parks.dat, world.dat, text_data.sqlite3, and the news/html report path.
- Snapshot machinery beyond copying the three parsed files into var/snapshots/<sim_date>/ and recording an ingest-run row. No incremental logic, no diffing, no retention policy, no weekly scheduler.
- Advisors of any kind, and any decision about their network posture. The request's observation that a shell is a superset of a web tool is correct and belongs in a doc, not in this build.
- Parser performance work. If a full parse is slow, record the number and stop — optimization is a separate request.
- Naming fictional or minor-league players in the report. Bronze lands whatever the walk yields; the REPORT serves Boston's organization only.

### acceptance_criteria

- `uv run pytest tests/test_save_header.py` is green, offline, with no game install: a synthetic header with a leading 0x00, magic 'OOTP' at offset 1 and u32 25 at offset 5 parses; headers carrying version 24 and version 26 each raise UnsupportedSaveVersion; a buffer whose bytes[0:4] == b'OOTP' (no leading null) is rejected; and a header whose self-declared filename disagrees with the file opened is rejected.
- `uv run pytest tests/test_sequential_walk.py` is green: two synthetic player records identical except for the size of a variable-length region (a 1-year vs a 10-year contract array, per tests/fixtures/README.md:37) yield identical values for every field parsed after that region.
- A static guard test passes: no module under src/ootp_ai/parser/ contains a seek() with a literal integer argument or a struct.unpack_from with a constant offset. A fixed offset is a blocker per .claude/agents/data-engineer.md:68-72, and this makes it mechanical.
- `uv run pytest tests/test_grain.py` is green: each landed table's declared grain constant in code matches an enforced uniqueness assertion, and bronze_team_roster's key is exactly (snapshot_date, team_id, player_id, list_id) — not (snapshot_date, player_id).
- `uv run pytest tests/test_withheld_columns.py` is green: no column in any landed table matches the withhold patterns (%_ratings_%, prone_%, talent_%, players_value%). Trivially satisfied by this slice, and left behind as the ADR 0012 regression guard for the next one.
- `uv run pytest -m gamedata tests/test_parse_real_save.py` is green against OOTP-AI.lg: exactly 30 teams extract at MLB level with the correct abbreviations; player_id is unique per snapshot; Boston's active + 40-man roster rows number >= 26 (NOT == 26 — see risks); and ZERO roster rows have a null or blank display name.
- `uv run pytest -m gamedata tests/test_names_join.py` is green: for every player_id present in both the parsed 'Test Save - Standard Mode' binaries and ootp_truth_real.players, the parsed first and last name equal the exported first_name/last_name for 100% of rows. The test SKIPS LOUDLY with a named reason if ootp_truth_real is absent — it never passes vacuously.
- `uv run pytest -m gamedata tests/test_idempotent.py` is green: parsing and loading the same snapshot twice produces identical row counts and identical per-table checksums, and does not alter any other snapshot's rows.
- `uv run pytest tests/test_catalog.py` is green: every table present in the warehouse appears in the generated catalog with a grain string, a key, a row count and a snapshot_date; and the catalog text contains no rating column names.
- `uv run pytest tests/test_no_leaks.py tests/test_repo_structure.py` remains green: no tracked file gains a machine path, no .dat or .lg is tracked, and the !gm/** carve-out survives.
- A file-mtime assertion passes: no file under $OOTP_SAVED_GAMES or $OOTP_INSTALL has a modification time newer than the start of the parse run. ADR 0001 is the one failure that is unrecoverable, so it gets a test rather than a promise.
- USER-RUN: a cold session spawns the `gm` agent with var/reports/roster.md and var/reports/catalog.md in its context, and the returned handoff's `## situation` section names at least five Boston players by real name, each attributed to the roster report. This is an LLM output, not an assertion — the acceptance panel must not claim it.

### core_scope

- src/ootp_ai/config.py — resolves OOTP_INSTALL, OOTP_SAVED_GAMES, OOTP_LEAGUE, OOTP_SNAPSHOT_ROOT and the MySQL connection from .env. No literal paths, no parents[N] walks outside test modules.
- A save enumerator that confirms players.dat and teams.dat exist before treating a directory as a save. Measured 2026-08-16: the saved-games root contains a stray directory literally named `.lg` alongside OOTP-AI.lg and two test saves, exactly as docs/data-access.md:60-63 warns.
- A header reader and version guard shared by every .dat: leading 0x00, char[4] 'OOTP' at offset 1, u32 version at offset 5 (must be 25), and the header's self-declared filename cross-checked against the file opened. I verified this byte layout myself against teams.dat, players.dat, world.dat, names.dat and scouting.dat in OOTP-AI.lg — all five identical.
- A snapshot step that copies ONLY the three parsed files (players.dat 32,070,106 B; teams.dat 5,318,831 B; names.dat 8,642,110 B — ~46 MB, not the full ~727 MB .lg) into var/snapshots/<sim_date>/, opens them 'rb', and never writes to the game.
- A sequential teams.dat walk yielding team_id, the 5-string signature (city, abbreviation, nickname, logo filename, full name), ARGB colors, and level / parent_team_id so MLB clubs can be distinguished from affiliates. docs/data-access.md:223-226 already records this as `verified`.
- A sequential players.dat walk yielding a DELIBERATELY MINIMAL field set: player_id, team/organization assignment, position, uniform number, date of birth, the name indices, and historical_id (the Lahman string). Every field landed is a field somebody re-validates after a game patch (docs/data-access.md §8) — the field set is a maintenance liability, not a free win.
- The names.dat join: index encoding + string-table layout, validated to 100% against ootp_truth_real.players.first_name/last_name (VARCHAR(50) each — measured from db_structure_ootp25_mysql.txt in the install). This is the single riskiest must-have and it is why the slice is worth running the full pipeline on.
- Roster-list extraction mirroring the export's team_roster grain (team_id, player_id, list_id), including empirically deriving what each list_id VALUE means by cross-tabbing counts in ootp_truth_real.team_roster — the list with exactly 40 rows per MLB club is the 40-man. Assuming the enum is the class of silent error requests/README.md:20-31 exists for.
- A MySQL loader writing three bronze tables into the `ootp` schema (ops/mysql-bootstrap.sql already creates it): bronze_teams keyed (snapshot_date, team_id); bronze_players keyed (snapshot_date, player_id); bronze_team_roster keyed (snapshot_date, team_id, player_id, list_id). Plus one _ingest_run row per snapshot recording source file sizes, hashes, header versions and wall-clock parse time.
- var/reports/roster.md — Boston's organization, grouped by roster list, first line carrying the snapshot_date and sim date so staleness is visible on sight.
- var/reports/catalog.md — generated from information_schema plus the ingest-run row and the grain constants declared in code, so it cannot drift from what was landed. States coverage explicitly, including what is NOT there (no ratings, no stats, no standings, no minor-league report).
- Offline synthetic fixtures under tests/fixtures/ per that directory's README: a bad-version header, a no-leading-null header, a short-vs-long variable-length record pair. Our constructions, never a slice of a real save.
- Documentation corrections routed through the doc gate: that no leagues.dat exists and league config lives in world.dat; that docs/league-rules.md:130 is wrong about leagues.dat; that db_structure_ootp25_mysql.txt (72 CREATE TABLE statements) exists in the install and supersedes the ootp22_csv doc cited at docs/data-access.md:133; and that docs/data-access.md §3's '16 tables, player_history 76,401 rows' does NOT hold for OOTP-AI.lg, whose text_data.sqlite3 has one table (game_logs, 0 rows).

### enhancements

```json
{
    "title":  "Run the scouting.dat stored-vs-computed spike BEFORE this build, as a separate throwaway investigation",
    "rationale":  "docs/data-access.md:280-295 already writes the test and nobody has run it. Both halves are on disk right now: \u0027Test Save - Standard Mode.lg\u0027 still holds players.dat (28,653,312 B), scouting.dat (2,349,181 B) and a non-empty import_export/, and its export is claimed to be in ootp_truth_real. The spike needs a query and a byte search, no production code, and its only deliverable is an epistemic label change in §5. It matters because the ANSWER RESHAPES THE NEXT REQUEST: \u0027stored\u0027 means the rating path is a normal parse; \u0027computed at render time\u0027 means ADRs 0012/0014/0016 have no data path and something has to be redesigned. Cheapest possible way to learn the most dangerous thing.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Doc-only correction sweep for the four claims measured wrong or missing today",
    "rationale":  "No leagues.dat; league config strings live in world.dat; db_structure_ootp25_mysql.txt exists and is a better map than the ootp22 doc currently cited; §3\u0027s SQLite row counts are save-specific. In a repo whose entire discipline is epistemic labelling, four known-stale claims are cheap to fix and expensive to trip over later.",
    "cost":  "cheap"
}
```
```json
{
    "title":  "Standings report",
    "rationale":  "Genuinely one of the two things a GM needs — just not on 2024-03-07, when it is 30 rows of 0-0. Needs the sub_league/division hierarchy and team win-loss fields mapped out of the binary, which is real work for zero present-day information. Reopen the moment the league sims past opening day; the team dimension will already be landed.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "world.dat league-config walk and the docs/league-rules.md §1 diff",
    "rationale":  "This is Desired Outcome 3, and I am recommending it be cut from the core rather than dropped forever. It requires mapping an 8.9 MB file nobody has looked at, to recover ~30 scalars, with no export for our league to validate against — the standard-save export describes a DIFFERENT league. league-rules.md §4\u0027s own proposal is an offseason standing order, first due ~2024-10. Deferring costs nothing and buys a bounded scope now.",
    "cost":  "grows-build"
}
```
```json
{
    "title":  "Minor-league populations in the roster report",
    "rationale":  "The data is already landed by the walk, so the marginal cost is a filter change — but serving five tiers multiplies coverage edge cases (structural absence of fields the majors carry) precisely when nothing yet consumes them. Under ADR 0016 the GM cannot read what it has not commissioned, so width bought now is width nobody asked for. Add it with the first request that needs a prospect.",
    "cost":  "grows-build"
}
```

### risks

- THE NAMES JOIN IS THE SINGLE POINT OF FAILURE AND IT IS UNCONFIRMED. docs/data-access.md:238-240 labels the names.dat index encoding and table layout `unconfirmed`; the request itself calls it 'the largest single unknown'. If it does not fall out, the roster report is integers and the stated problem is unsolved. Mitigation to write into the scope: the fallback is historical_id (the Lahman string, embedded in players.dat, ~1,712 unique, `verified` at docs/data-access.md:99-102), which on a 2024-seeded day-0 save covers essentially the whole MLB population. But turning `deverra01` into 'Rafael Devers' needs a name source, and the only local one is players.csv — OOTP's IP. See the next risk.
- ADR 0005 AND ADR 0006 COLLIDE ON THE FALLBACK PATH. .gitignore:58-62 tracks datasets/** on the stated grounds that they are 'OUR derived artifacts (field maps, offsets, lookups), not OOTP's shipped files'. A Lahman-ID-to-name lookup built from players.csv is a verbatim reproduction of OOTP's shipped content wearing a derived-dataset hat, and tests/test_no_leaks.py::test_game_data_is_not_tracked only catches it by FILENAME — a renamed lookup sails straight through. If the names join fails, do not resolve it by tracking a name table. Print the Lahman ID, fail the acceptance criterion honestly, and file a follow-up.
- THE GROUND TRUTH THE WHOLE VALIDATION RESTS ON IS UNVERIFIED FROM MY SEAT. The request asserts ootp_truth_real is loaded with 72 tables and players_scouted_ratings at 36,144 rows. MySQL84 is running (measured), but its data directory is ACL-denied and I read no credentials, so I confirmed neither. Independently: db_structure_ootp25_mysql.txt in the install contains exactly 72 CREATE TABLE statements, which is consistent — that is corroboration, not confirmation. Add a preflight that fails loudly, never skips silently: a gamedata test that quietly skips is how an unvalidated parser ships labelled `verified`.
- THE EXPORT AND THE BINARIES MUST COME FROM THE SAME SAVE, AND NOTHING RECORDS THAT THEY DO. 'Test Save - Standard Mode.lg' still has its players.dat/names.dat on disk, but if ootp_truth_real was exported from some other disposable save, the names-join test compares two universes. Worst case it PASSES on the ~1,712 real players (whose identities are stable across saves) and fails only on fictional ones — a partial pass that looks like a bug in the fictional path. Pin the provenance in the scope.
- 'THE 26-MAN ROSTER' PROBABLY DOES NOT EXIST ON 2024-03-07. The club is in spring training; docs/league-rules.md:240 lists 'final cuts, the opening-day 26' as still ahead. `inferred`: the save holds a spring roster and a 40-man, not a set 26. An acceptance criterion asserting exactly 26 rows will fail on a CORRECT parse and send someone hunting a bug that isn't there. Assert >= 26 and assert list membership instead.
- list_id IS AN UNDOCUMENTED ENUM AND GUESSING IT PRODUCES A CONFIDENTLY WRONG REPORT. db_structure_ootp25_mysql.txt gives team_roster(team_id, player_id, list_id SMALLINT) with no value semantics. Label the wrong integer 'active roster' and the GM reads a plausible, wrong 26. Nothing throws. This is exactly the failure class requests/README.md:20-31 built a third track for.
- THE ROSTER JOIN FANS OUT IF THE GRAIN IS TAKEN AS 'PLAYER PER SNAPSHOT'. A player sits on more than one list (active AND 40-man), so bronze_players x bronze_team_roster on player_id alone multiplies rows. The request's Data Contracts section frames the grain question entirely around mid-season trades and never mentions roster-list membership — which is the fan-out that bites TODAY, on an unsimmed save, with no trade in sight.
- ADR 0004 IS AN UNRESOLVED DECISION SITTING DIRECTLY IN THE BLAST RADIUS. Its §Notes says dbt-mysql is capped at 1.7.0 and pins dbt-core~=1.7.0, four minor versions behind, and that the call 'comes due when the first dbt model is requested'. The request's Rough Ideas propose bronze/silver/gold. Building any dbt model here forces that call inside a request already carrying two project-threatening unknowns, and pyproject.toml:26-29 deliberately has no transform group. Keep dbt out; say so in writing as a stated partial divergence from ADR 0005's 'dbt medallion' phrasing (the PATTERN choice — parser side, not builder side — is honoured; the TOOLING is deferred).
- ADR 0016's COST BOUNDARY IS AMBIGUOUS FOR THESE TWO REPORTS AND WILL BE ARGUED ABOUT ON DELIVERY. ADR 0016 Notes says infrastructure is free and directing analysis costs an action; gm/standing-orders.md:29-31 says a report IS a standing order for information, which costs an action to commission. Roster and catalog are the club's own roster page — what any GM sees on day one without asking. The scope should propose they be ruled FREE infrastructure with a ledger row recording the ruling, rather than leaving the first delivery to trip the action economy.
- REPORT ROT. var/reports/roster.md is a plain file with no expiry. The GM reads it as current and gm.md:57-67 forbids inventing numbers but cannot detect a stale source. Harmless while the league is unsimmed; dangerous the week after the first sim. Minimal mitigation only: snapshot_date and sim date on line one. Do NOT build a freshness framework in this slice.
- PARSE COST IS UNMEASURED. ~46 MB across three files, walked sequentially in pure Python with per-field struct calls (pyproject.toml:11-15 deliberately keeps the parser stdlib-only). Nobody has run it; `unconfirmed`. Set a budget in the scope — if a full parse exceeds ~10 minutes, record the number and stop rather than optimizing inside this request.
- docs/data-sources.md DOES NOT EXIST. The scoping brief names it; the repo has docs/data-access.md. Anyone following the brief literally finds nothing and may conclude the source documentation is missing rather than misnamed.
- docs/data-access.md §3 IS ALREADY KNOWN-STALE FOR OUR LEAGUE. It records 16 SQLite tables with player_history at 76,401 rows, cross-checked against the in-game Database screen. OOTP-AI.lg/temp/text_data.sqlite3 has ONE table (game_logs, 0 rows) — measured today. The claim was true of a probe save. Out of scope to fix here, but it is a live example of a `measured` label that was measured somewhere else, which is the exact error mode this repo's labelling discipline exists to prevent.
- A SILENT MISPARSE PASSES EVERY TEST BY CONSTRUCTION. Grab the wrong u16 and you get a plausible number, no exception, and green tests all the way into a GM decision. The only real defence in this slice is that it lands almost nothing subjective — identity, membership, and names, all of which have an independent ground truth to disagree with. That is a feature of the minimal cut, not an accident, and it is the strongest single argument for cutting ratings out of it.

### open_questions

- Is ootp_truth_real actually loaded, from WHICH save, and with which export options? The names-join acceptance criterion is unverifiable until this is answered, and I could not confirm it read-only (MySQL84 running; data directory ACL-denied).
- Do var/reports/roster.md and var/reports/catalog.md cost the GM an action, or are they free infrastructure under ADR 0016 Notes? Needs an umpire ruling and a ledger row BEFORE delivery, not after.
- If the names.dat join does not fall out, does the slice ship with Lahman IDs in place of names, or does it not ship? I recommend the former plus a failed criterion recorded honestly — but the request's own success signal is 'real players with real names', so this is the operator's call.
- What is the acceptable wall-clock budget for a full parse before it becomes a problem rather than a number?
- Should the scouting.dat stored-vs-computed spike run BEFORE this build rather than inside it? I think yes — its answer reshapes the next request, and it costs a query plus a byte search.
- Where does the league record actually live inside world.dat, and is it reachable by a sequential walk at all? Not needed for this slice; needed before docs/league-rules.md §1 can ever be verified.

