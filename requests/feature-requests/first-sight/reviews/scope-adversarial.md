# Scoping Panel — Adversarial Findings & Convergence Map

Run 2026-08-16 · workflow `wf_dcaa2bed-78d`.
Panel health: **3/3 scopers, 2/2 adversaries, 0 degraded lenses.**
Findings: 55 total — 7 blocker, 26 major.

Verbatim. Findings the operator judged overstated are still recorded here; the
disposition lives in PROJECT_SCOPE.md, not in this file.

## Convergence map — where independent scopers agreed

### Run the scouting.dat stored-vs-computed spike FIRST, with a pre-registered pivot rule, and let it gate only the ratings half

**Scopers:** fit, ambitious, minimalist

Unanimous, and each arrived from a different direction: repo-fit from schedule risk, ambitious from byte evidence (~130 B/player), minimalist from cost (a query plus a byte search). The FR itself flags it as the project-threatening unknown (Open Question 1, Trigger 1). Three independent lenses agreeing that the deliverable should be DECOUPLED from it — rather than merely sequenced before it — is the strongest structural signal in the panel.

### There is no leagues.dat, and docs/league-rules.md asserts one twice

**Scopers:** fit, ambitious, minimalist

All three enumerated the .lg directory independently and got the same 18-file list. I re-verified it. This kills the cheap path to Desired Outcome 3 and makes two tracked doc claims (league-rules.md:129 and :295) factually wrong. Note the panel then SPLIT on the replacement: fit and ambitious both inferred teams.dat; minimalist located the config marker in world.dat. I searched both files — world.dat byte 5,559,751, teams.dat not found — so the minority view is the correct one, and any plan built on the majority guess would have opened the wrong binary.

### Keep dbt out of this slice; ADR 0004's adapter decision must not be forced as a convenience

**Scopers:** fit, ambitious, minimalist

Unanimous on the diagnosis even though the ambitious scoper still wanted the medallion. ADR 0004 §Notes and pyproject.toml's deliberately-absent transform group say the same thing, and CLAUDE.md's Outstanding scaffolding work names it. Three scopers independently identifying that the FR's 'bronze, conform in silver, serve gold' Rough Idea would trigger the most expensive event in this repo — an ADR re-litigation — to serve two reports is decisive.

### The still-on-disk probe save paired with its loaded export is the real ground truth, and the FR under-sells it

**Scopers:** fit, ambitious, minimalist

Two scopers called it the highest-leverage asset in the repo; the third built its entire names-join criterion on it while flagging it could not verify it read-only. I verified both halves: binaries intact, ootp_truth_real loaded with 72 tables and matching counts, and saved_games.dat pins both to 03/18/2024. players.csv covers ~12,855 shipped real players and validates NO name, roster list, team dimension or league config — so this pairing is the only thing that makes the core deliverables provable rather than eyeballed.

### The names.dat join is the hard blocker and must be validated against an independent answer key, never an impression

**Scopers:** fit, ambitious, minimalist

The FR calls it the largest single unknown; data-access.md:238 labels it `unconfirmed`. All three made 100%-or-enumerate-every-failure the criterion rather than a rate, and the minimalist added the sharpest operational detail: the test must SKIP LOUDLY if ground truth is unreachable, because a gamedata test that quietly skips is how an unvalidated parser ships labelled `verified`.

### Header magic is at offset 1 and the version guard must REFUSE, not warn

**Scopers:** fit, ambitious, minimalist

All three specified the same synthetic-fixture test set (v24 rejected, v26 rejected, magic-at-offset-0 rejected, filename mismatch rejected) offline with no game install. Two independently measured the exact byte string. I confirmed it on two different .dat files. This is the rare invariant where three scopers produced a criterion that is already implementable verbatim.

### The two reports need an action-economy ruling BEFORE delivery, with a ledger row

**Scopers:** fit, ambitious, minimalist

All three flagged that ADR 0016's infrastructure-is-free / direction-costs boundary is genuinely ambiguous for a roster and a standings page, and that this becomes an early ledger seq every later request will cite. Repo-fit named it the risk an engineering panel would underweight — which is exactly right, and is why it is a gated decision rather than a scope line.

### historical_id is a nullable ATTRIBUTE, never a join key

**Scopers:** fit, ambitious, minimalist

All three landed on the same enforcement shape: a static check that no join or ref condition uses it. Coverage measured identically by two and re-verified by me at 1,920 of 18,072 active (10.6%). The FR warns a join on the wrong key silently drops the fictional majority; making it a source-level guard rather than a convention is the converged answer.

### Catalog placement has no clean answer and needs an explicit ruling

**Scopers:** fit, ambitious

Both independently identified the three-way squeeze: gm/README.md:19's placement rule sends it to var/; var/ is gitignored so a fresh clone has nothing; and tests/test_doc_links.py fails CI on a tracked Markdown link into var/ (a live defect with an open bugfix request). The FR raises it as Open Question 4 without resolving it. Both proposed the same split — structural tracked, volatile generated — and both correctly called it a compromise rather than a win.

### Nothing may hardcode the human team or the scouting perspective

**Scopers:** ambitious, minimalist

The ambitious scoper measured the probe's human team as the Cubs; I confirmed it from saved_games.dat (Cubs at 03/18/2024 vs Boston at 03/07/2024). This is the specific failure mode where code PASSES on ground truth and breaks on the league we actually manage — invisible to the entire validation harness, which is what makes it worth carrying forward as a named constraint rather than a code-review note.

### Structural absence must land as NULL, never zero

**Scopers:** fit, ambitious

Both cited the same measured evidence — the export writes 0 for rules_active_roster_limit and the service-time columns on all 14 non-MLB league rows — and both connected it to data-engineer.md's rule that conflating the two produces silently wrong AGGREGATES rather than visibly incomplete ones. It is also the coverage question the FR raises without answering.

## Adversary summaries

### fit-ac

I re-ran the scope's headline measurements myself rather than inheriting them, and most of them hold: OOTP-AI.lg has exactly 18 .dat files with no leagues.dat (players.dat 32,070,106 / teams.dat 5,318,831 / names.dat 8,642,110 / scouting.dat 2,863,744 / world.dat 8,898,534 / challenge.dat 241 / retired.dat 154,088,679); `major_league_ml_c_2024.lsdl` is at byte 5,559,751 of world.dat and IndexOf = -1 in teams.dat; the header is byte-for-byte `00 4f 4f 54 50 19 00 00 00 0b 00 00 00 68 00 00 00 54 00 00 00 01 00 00 00` + a self-naming filename on both world.dat and teams.dat; the export's team_record is 259 rows all g/w/l/t = 0; players_batting has exactly 132,990 rows with 12 distinct `batting_ratings_overall_contact` values (20,25,30,35,40,45,50,55,60,65,70,80); players_scouted_ratings is 36,144 rows split exactly 18,072/18,072 across scouting_coach_id -1 and 2759; team_roster is 15,672 rows with list_id {1:7370, 2:7037, 3:935, 4:330}; saved_games.dat pins OOTP-AI to Boston/03-07-2024 and the probe to the Cubs/03-18-2024. The measured core of the reshape is sound and the fit verdict ("belongs here, needs reshaping") is right.

Three things do not survive the check. (1) The acceptance criteria contradict the scope's own deliverable and each other: criterion 13 demands the report output root lie OUTSIDE the git worktree while the core says "two Markdown reports under var/", and criteria 4/5/12 need a live MySQL warehouse but are not `-m gamedata`, which breaks criterion 16 and CI. (2) The scope's ground-truth story is weaker than it claims and it under-uses what is actually on disk: players.csv carries FirstName/LastName/NickName alongside Player ID and LahmanID (231 columns, verified in the install), which the scope repeatedly says cannot validate names — and via the `verified` historical_id it validates names in OUR league, not only the probe's; meanwhile team_roster covers only 7,370 DISTINCT players out of 18,072 active (measured), not the "15,672 rows over 18,072 active players" the scope implies. (3) Two non-goals bury real work: "no second ground-truth export" conflates a redundant OSA export (correctly unnecessary) with ADR 0002 §Notes' explicit requirement for an export from a SIMULATED standard save — both saves have zero games played, so the entire Tier-B harness is built on what ADR 0002 and tests/fixtures/README.md both call the least informative possible test input; and the tail-consumed assertion is costed as "a counter and an assertion" when data-access.md:228 says the overwhelming majority of players.dat is unmapped, so consuming it to the end requires near-complete record-length knowledge. Separately, the demotion of Desired Outcome 3 rests on an argument the scope's own Tier-B architecture refutes (the probe's world.dat carries the same league block at byte 5,559,091 AND has a 15-row `leagues` export with 57 rules_* columns to diff against), and README.md:137-139 names that verification as the parser's "first genuinely useful job".

### scope-completeness

SCOPE DISCIPLINE & COMPLETENESS. I re-ran the merged scope's load-bearing measurements before attacking it, and they hold: `major_league_ml_c_2024.lsdl` is at byte 5,559,751 of OOTP-AI.lg/world.dat and absent from teams.dat (IndexOf -1); all 259 `ootp_truth_real.team_record` rows are 0/0/0 with 0 of 12,961 games played; `players_batting.batting_ratings_overall_contact` has exactly 12 distinct values over 132,990 rows; `team_roster` is 15,672 rows with list_id {1:7370, 2:7037, 3:935, 4:330}; 18,072 active players, 1,920 with a historical_id; schemas `ootp` and `ootp_truth_osa` exist with zero tables; `players_scouted_ratings` carries both perspectives (-1 and 2759) at 18,072 each; OOTP_SNAPSHOT_ROOT is empty in .env. The factual base is sound, so my attack is on shape, not truth.

(A) OVER-REACH. "Core" is 20 workstreams, ~13 new test modules and 20 acceptance criteria for the repo's first line of pipeline code, in a project whose own CLAUDE.md says to size scope for sustained enjoyment and build vertical slices. Three items are frameworks wearing slice clothing: the field-map declaration with three consumers (a schema compiler), the "reusable" two-tier ground-truth harness (n=1 consumer, and Tier A validates nothing in the core field set once ratings are cut), and the warehouse metadata label table (a third copy of a label the repo's own routing rule exists to keep singular). The read-only proof hashes $OOTP_INSTALL and $OOTP_SAVED_GAMES — advertised as microseconds, actually multi-GB per run. And the gating is not honest in two directions: the spike is presented as a gate but, with ratings decoupled, gates nothing in this slice; and three "gated" items trigger on the spike verdict, which arrives mid-build, so they can be pulled in without the human disposing them.

(B) BLIND SPOTS. Two blockers are internal contradictions a cold stage-3 agent cannot resolve: reports land "under var/" and simultaneously "outside the git worktree" (var/ is inside it — `git check-ignore` returns `.gitignore:18:var/`); and criteria 4 and 12 need a populated MySQL while criterion 16 requires the same run to pass with no MySQL, against a pyproject that declares exactly one marker (`gamedata: requires a local OOTP install or save`) under `--strict-markers`. Beyond those: the gm/standing-orders.md report entry cannot be written because its format demands an Owner and gm/staff.md says no staff is engaged; nothing owns handing the GM its report paths, which is the FR's headline signal; bronze's PK has no save/league identifier while the plan parses two universes; collation is unaddressed although the export doc explicitly warns accents break the names validation; the first runtime dependency is named as a risk but never chosen under mypy strict; and README.md:98's `uv run pytest` breaks on a fresh clone the moment gamedata tests exist.

My own new measurement, which the scope does not have: names.dat is 8,642,110 bytes in all three saves on disk but its SHA-256 differs in each. That refutes the scope's stated reason for routing it to the parser side ("grows as fictional players are generated" — it does not grow), keeps the routing conclusion intact, and surfaces an unnamed hazard twin to "never hardcode the human team": a name index resolved on the probe save does not mean the same string in OOTP-AI. Also measured: OOTP-AI.lg holds 19 .dat files, not the 18 the scope asserts twice, and a third save — `Test Save - Challenge Mode.lg` — exists and is never mentioned, though it is the obviously safer target for the read-only proof than the irreplaceable managed league.

## Findings

### BLOCKER (7)

#### [F1] Criterion 13 demands the report output live outside the git worktree; the scope's own core puts it in var/, which is inside

*adversary:* fit-ac · *confidence:* high · *category:* acceptance

**Location:** acceptance_criteria[13] vs tiered_scope.core ("Two Markdown reports under var/") and goals[0]; var/ is a directory at `<repo-root>/var` [absolute path redacted — CLAUDE.md bans machine-specific paths in tracked files], gitignored by .gitignore line `var/`

**Problem.** Criterion 13 asserts "the output root resolved from .env lies OUTSIDE the git worktree". The core deliverable, goals[0], and gm/README.md:19's placement rule all put the rendered reports under `var/` — which is INSIDE the worktree (it is a repo-root directory, merely gitignored). As written the criterion fails by construction against a correct implementation, and a cold implementing agent must either break the placement rule or break the test. The same sentence in tiered_scope.core contains both halves of the contradiction: "Two Markdown reports under var/, rendered from .env-resolved paths that lie outside the git worktree."

**Proposed fix.** Replace the criterion's condition with the one that actually protects ADR 0006: assert that the resolved report root is git-ignored (`git check-ignore -q <path>` returns 0) AND that `git ls-files` lists no file under it. That is mechanically checkable, is true for var/, and is the property that matters — no rendered OOTP data becomes tracked. Delete "outside the git worktree" from both the criterion and the core bullet.

#### [F2] Every acceptance criterion lands a new file under tests/, which is in the designated builder's hard deny set — and no owner is named

*adversary:* fit-ac · *confidence:* high · *category:* fit

**Location:** .claude/agents/data-engineer.md:150 ("You must never write to, repo-level deny: tests/ — the guards that catch you") and :164-165 ("If the spec's target paths fall inside the deny set, stop and report it"); asserted by tests/test_agent_contract.py::test_deny_set_still_protects_the_guards

**Problem.** Fourteen of the twenty acceptance criteria name a new pytest module under tests/ (test_save_header.py, test_sequential_walk.py, test_no_fixed_offsets.py, test_grain_contracts.py, test_parser_vs_export.py, test_names_join.py, test_parse_real_save.py, test_snapshot_semantics.py, test_read_only.py, test_tail_consumed.py, test_withheld_columns.py, test_reports.py, test_catalog.py, test_extraction_cost.py). The repo's single owner of the build rules forbids the write-capable subagent from writing anything under tests/, and instructs it to STOP and report rather than build when spec targets fall in the deny set. The scope never says who authors these files. As drafted, handing this to the data-engineer produces an Escalation case 1 handoff and zero tests.

**Proposed fix.** Add an explicit handoff clause to the scope: all files under tests/ are authored by the main thread, not the implementation subagent, and the subagent's spec declares only src/ootp_ai/** and the field-map declaration as target paths. State it in the scope so stage 3 splits the work correctly rather than discovering the deny at build time. If the intent is instead to amend data-engineer.md's deny set, that is a separate request and must be named as one.

#### [F3] The unparsed-byte tail assertion is costed as trivial but requires near-complete record-length knowledge of a file the repo documents as unmapped

*adversary:* fit-ac · *confidence:* high · *category:* scope-creep

**Location:** acceptance_criteria[11]; above_and_beyond[1] ("it costs a counter and an assertion"); contradicted by docs/data-access.md:228 ("`unconfirmed` — Everything else. The overwhelming majority of both files is still unmapped")

**Problem.** Criterion 11 requires every sequential walk to consume its file to the end with zero unaccounted bytes. That is only achievable if the walker can size EVERY region of every record — including all the fields the scope deliberately excludes under "a DELIBERATELY MINIMAL field set". players.dat is 32,070,106 bytes across ~18,000 records whose layout data-access.md says is overwhelmingly unmapped; skipping an unknown variable-length region exactly is the same problem as parsing it. The scope simultaneously promises a minimal field set AND full byte accounting, and prices the second at 'a counter'. This is the largest cost mis-estimate in the draft and it sits in the core tier.

**Proposed fix.** Split the criterion by file and by achievability. Keep the strict form only where a full walk is plausible (teams.dat at 5.3 MB, names.dat as a flat string table) and downgrade players.dat to a weaker but still-diagnostic assertion: the walk must reach a record count that matches an independent count (the export's retired=0 population for the probe save) and must terminate at a record boundary, with the residual byte count RECORDED in the ingest-run row rather than asserted to be zero. Re-state the cost honestly in the tier rationale: full byte accounting on players.dat is a research task, not a counter.

#### [F4] Three criteria require a live MySQL warehouse but are not gamedata-marked, so they contradict criterion 16 and would break CI

*adversary:* fit-ac · *confidence:* high · *category:* acceptance

**Location:** acceptance_criteria[4], [5], [12] vs [16]; .github/workflows/ci.yml:49 runs `uv run pytest -m "not gamedata"`; pyproject.toml declares the `gamedata` marker; .claude/agents/data-engineer.md:91-92

**Problem.** Criteria 4 and 5 are written as plain `uv run pytest tests/test_grain_contracts.py` and assert properties of LANDED tables (declared PK unique and non-null, player_id non-unique within a snapshot's roster rows) — which requires a populated `ootp` schema. Criterion 12 asserts "no column in any landed table ... matches the withhold patterns", same requirement. Criterion 16 states `uv run pytest -m "not gamedata"` must pass with NO game install and NO MySQL server, which is exactly what CI runs. CI has no MySQL service. As written, three criteria are mutually exclusive with a fourth and would turn the build red.

**Proposed fix.** Split each of the three into two tests: an OFFLINE half that reads the tracked contract declaration and the DDL the loader emits and asserts prose-grain equals emitted-key and that the withhold rules are well-formed (no MySQL needed, runs in CI), and a `-m gamedata` half that asserts the same properties against the live warehouse. Mark the warehouse halves `gamedata` explicitly in the criterion text so the acceptance panel does not try to run them in CI.

#### [SD-01] Reports land "under var/" and "outside the git worktree" — var/ is inside the worktree, so these cannot both hold

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** scope goals[0] + tiered_scope.core ("Two Markdown reports under var/") vs acceptance_criteria[12] ("the output root resolved from .env lies OUTSIDE the git worktree"); .gitignore:18; .env.example:22-25; gm/README.md:17-19

**Problem.** Three parts of the scope disagree about where rendered output goes. goals[0] and the core tier both say var/. acceptance_criteria[12] requires the .env-resolved output root to lie OUTSIDE the git worktree. Measured 2026-08-16: `git check-ignore -v var/reports/roster.md` returns `.gitignore:18:var/` — var/ is a GITIGNORED directory INSIDE the worktree, not outside it. .env.example:24 documents `OOTP_SNAPSHOT_ROOT` as "Defaults to var/snapshots", and gm/README.md:19's placement rule ("Can this be rebuilt from the save? Yes -> var/") sends regenerable artifacts there by contract. A cold stage-3 agent must pick one reading, and either choice makes an acceptance criterion unsatisfiable or breaks the repo's own placement rule.

**Proposed fix.** Settle on var/ (it is what the placement rule, .env.example and every other repo convention say) and rewrite criterion 13 to assert what actually protects ADR 0006: the resolved output root is under a path matched by .gitignore, proven by shelling `git check-ignore -q <resolved path>` and asserting exit 0. Delete the "outside the git worktree" phrasing everywhere it appears.

#### [SD-02] Criteria 4 and 12 require a populated MySQL; criterion 16 requires the same selection to pass with no MySQL, and no marker exists for "needs a database"

*adversary:* scope-completeness · *confidence:* high · *category:* acceptance

**Location:** acceptance_criteria[3] (test_grain_contracts), [11] (test_withheld_columns), [15] (`uv run pytest -m "not gamedata"` with NO game install and NO MySQL); pyproject.toml:78-81; .github/workflows/ci.yml (pytest step)

**Problem.** Criterion 4 asserts "every landed table's declared PK is unique and non-null" and criterion 12 asserts "no column in any landed table ... matches the withhold patterns". Both read the warehouse. Neither carries the `gamedata` marker, so both are collected by criterion 16's `-m "not gamedata"` run, which criterion 16 explicitly requires to pass with NO MySQL server present — which is exactly what CI does (.github/workflows/ci.yml runs `uv run pytest -m "not gamedata"` on ubuntu-latest with no database service). pyproject.toml:80 declares exactly one marker and defines it as "requires a local OOTP install or save" — saying nothing about a database — and addopts carries `--strict-markers`, so inventing an undeclared `warehouse` marker is a hard collection error. The scope never settles whether database-dependent tests reuse `gamedata` or need a new marker.

**Proposed fix.** Settle it in the scope: either (a) widen the `gamedata` marker's declared meaning in pyproject.toml to "requires a local OOTP install, save, or warehouse" and mark criteria 4 and 12 `-m gamedata`, or (b) add a second declared marker and say so, since --strict-markers makes an undeclared one fatal. Then split criteria 4 and 12 into a schema-only half (reads the tracked field-map declaration, runs offline, stays in CI) and a data half (queries the warehouse, marked). The offline half is the one that actually protects against regression on a machine that has no game.

#### [SD-03] The gm/standing-orders.md report entry cannot be written: its format requires an Owner and gm/staff.md records that no staff exists

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** tiered_scope.core ("entries in gm/standing-orders.md under its existing `## Reports` format (Established / Owner / Policy ...) plus the ledger row"); gm/standing-orders.md:42-50; gm/staff.md:5-8; gm/README.md:125-127; .claude/agents/gm.md:51-52

**Problem.** The core tier commits to writing report entries into gm/standing-orders.md and a ledger row. The template at gm/standing-orders.md:42-50 requires `Established: ledger seq <n>, sim date`, and `Owner: the analyst who produces and refreshes it`. gm/staff.md:5-8 states "Status: no staff engaged ... no analytics capability exists yet". There is no analyst to name, so a required field of a tracked contract cannot be filled. Separately, the ledger row is not engineering output: gm/README.md:125-127 requires "Declare before doing" and the schema's `ruling` field is "what the operator actually ruled"; gm.md:51-52 says the umpires hold the pen on gm/. A builder writing a ledger row is authoring an adjudication that has not happened.

**Proposed fix.** Remove the ledger row from core entirely — it is an umpire act, not a build artifact. Reframe the standing-orders entry as a USER-RUN step performed by the operator after delivery, and add a gated decision that names the actual open question: can a report exist with no staff owner, or must an engineering-owned report be a distinct kind with its own template line? Whichever answer, note it requires an edit to gm/standing-orders.md's format block, which the scope currently does not budget for.

### MAJOR (26)

#### [F5] The 'no second ground-truth export' non-goal buries ADR 0002's actual requirement — an export from a SIMULATED save

*adversary:* fit-ac · *confidence:* high · *category:* non-goals

**Location:** non_goals[11]; docs/decisions/0002-parse-binaries-not-export.md:66-70 ("a ground-truth export from a *simulated* standard save is what proves the parser against mutated, non-day-0 data... Day-0 state is the least informative possible test case"); tests/fixtures/README.md:47-51 says the same thing

**Problem.** The non-goal is argued entirely against a SECOND export for the OSA perspective, and on that narrow point it is right (I confirmed players_scouted_ratings carries scouting_coach_id -1 and 2759 at 18,072 rows each from one export). But it is worded as a blanket refusal to run another export, and under that wording the scope quietly forecloses the thing ADR 0002 §Notes explicitly calls for. Measured: the probe save's team_record is 259 rows of 0-0-0 and its games are all unplayed, so the entire Tier-B harness — which the scope promotes to core and calls 'the only thing that makes the names join and the roster grain provable' — is built on day-0 data where every variable-length region is at its minimum. That is precisely the input against which a fixed-offset reader passes cleanly. The standard-mode save is disposable by ADR 0002 and is not the managed league, so simming it forward costs nothing this project cares about.

**Proposed fix.** Narrow the non-goal to what is actually being refused: 'no second export for a second RATING PERSPECTIVE — one export already carries both.' Then add a core or cheap-fold item, marked USER-RUN: sim the disposable standard-mode save forward some weeks and re-export, giving a Tier-B target with grown contract/stat arrays, non-zero team_record, and roster churn. Note in the scope that the current probe pins the DECODER's field ORDER but cannot exercise variable-length growth, and say so in the epistemic labelling of any field validated only against it.

#### [F6] Desired Outcome 3 is demoted on a rationale the scope's own Tier-B architecture refutes, and README names it the parser's first useful job

*adversary:* fit-ac · *confidence:* high · *category:* framing

**Location:** fit_verdict RESHAPE 2 and tiered_scope.gated[1]; contradicted by README.md:137-139 and by my own measurement of the probe save

**Problem.** The scope gates the league-rules §1 diff because it 'means reverse-engineering an 8.9 MB fifth binary ... with NO export of our Challenge Mode league to validate against.' The second half is true for OOTP-AI and irrelevant, because it is equally true for teams.dat and players.dat, which the scope keeps in core on exactly the Tier-B logic it declines to apply here. I measured: the probe save's world.dat (8,661,801 B) carries the same league block at byte 5,559,091, and its export ships `leagues.mysql.sql` with 15 rows and 165 columns including 57 `rules_*` columns, `schedule_file_1`, `rules_active_roster_limit` and `rules_fa_minimum_years` — i.e. an exact, row-for-row answer key for the world.dat league decoder. Meanwhile README.md:137-139 states the parser's 'first genuinely useful job is verifying that the managed league is configured the way docs/league-rules.md claims'. The scope's fit_verdict cites README as naming first-sight the blocker but omits that README also names this specific outcome as the point.

**Proposed fix.** Either (a) move a MINIMAL world.dat leagues walk into core — enough to recover the ~30 §1 scalars, validated Tier-B against ootp_truth_real.leagues on the probe save exactly as teams.dat is — or (b) keep it gated but rewrite the rationale to the honest one (it is a fifth binary and a wider parser surface inside an already-large slice), drop the false 'nothing to validate against' claim, and record the measured validation path so the next request starts from it. Also correct the fit_verdict's README citation.

#### [F7] Roster coverage is misstated: team_roster covers 7,370 distinct players, not 18,072

*adversary:* fit-ac · *confidence:* high · *category:* completeness

**Location:** acceptance_criteria[5] ("ootp_truth_real.team_roster is 15,672 rows over 18,072 active players"), risks[4], grounding_pointers; measured by me from Test Save - Standard Mode.lg/import_export/mysql/team_roster.mysql.sql

**Problem.** I parsed the export directly: 15,672 (team_id, player_id, list_id) tuples over 7,370 DISTINCT player_ids, with list_id {1:7370, 2:7037, 3:935, 4:330}. The list_id=1 count equals the distinct-player count exactly, so every rostered player appears once in list 1 and roughly half appear again in list 2. The scope's phrasing 'over 18,072 active players' invites the reader to conclude the roster table covers the active population; it covers 40.8% of it. About 10,700 active players — free agents, draft-eligible, international, unassigned — have NO roster row at all. This is a coverage fact the FR asks the scope to settle ('Which populations land ... structural absence is not missing data'), and getting it wrong propagates: an inner join from bronze_player to bronze_team_roster silently drops the majority of players, which is the exact failure data-engineer.md:108-112 names.

**Proposed fix.** Correct the number in criterion 5 and in the coverage contract, and add a positive assertion to the grain tests: `count(distinct player_id) in bronze_team_roster` is materially LESS than `count(*) in bronze_player` for the same snapshot, with both numbers recorded in the catalog's per-table coverage statement. Add an explicit sentence to the catalog spec: how many players carry no roster row, so the GM can price 'who is available' as a known gap rather than discovering it.

#### [F8] players.csv carries FirstName/LastName — the scope repeatedly says it validates no name, and thereby misses the only offline name validator that works on OUR league

*adversary:* fit-ac · *confidence:* high · *category:* fit

**Location:** convergence_map[3] ("players.csv covers ~12,855 shipped real players and validates NO name, roster list, team dimension or league config"), above_and_beyond[0], goals[3], gated_decisions[7]; refuted by the header of $OOTP_INSTALL/data/database/players.csv (231 columns, verified today)

**Problem.** players.csv's header includes `//Player ID`, `Team ID`, `Team Name`, `LastName`, `FirstName`, `NickName`, `LahmanID`, `RetroID`, `BBRefID`. It is an exact, install-shipped, offline name table for ~12,855 real players. The scope asserts the opposite three times and builds its entire names-join validation on the probe save's export. This matters beyond an error of fact: docs/data-access.md:99-102 records as `verified` that the Lahman ID is embedded in players.dat itself (~1,712 unique). That gives a complete validation chain that runs against OOTP-AI.lg, not just the probe — parse historical_id from players.dat, join players.csv on LahmanID, compare to the names.dat-resolved string. The scope's Tier-B path validates the DECODER on a Cubs universe; this path validates the join on OUR club, which is the thing the FR's observable signal actually depends on.

**Proposed fix.** Add a Tier-A names criterion to core: for every player in OOTP-AI.lg's players.dat carrying a non-empty historical_id, the names.dat-resolved first and last name equals players.csv's FirstName/LastName joined on LahmanID, 100% exact, every failure enumerated. Correct the three places that claim players.csv cannot validate names. Also revisit gated_decisions[7]: the 'ship with Lahman IDs instead of names' fallback is more pessimistic than the repo allows — a report rendered into gitignored var/ may resolve real names from players.csv at RUNTIME with nothing tracked, so ADR 0006 does not force integers on the page.

#### [F9] The withhold patterns are wrong in both directions: `talent_%` matches no real column and `%_ratings_%` would block the scouted view ADR 0012 permits

*adversary:* fit-ac · *confidence:* high · *category:* acceptance

**Location:** acceptance_criteria[12] (patterns `%_ratings_%`, `prone_%`, `talent_%`, `players_value%`); real column names measured from the export: `batting_ratings_talent_contact`, `batting_ratings_overall_contact`, `prone_overall/leg/back/arm`

**Problem.** Two concrete defects. (a) `talent_%` as a LIKE pattern matches nothing — the actual true-talent columns are `batting_ratings_talent_*`, so the pattern silently protects nothing while reading as if it does. That is precisely the class of vacuously-green guard the repo's own bugfix track exists for. (b) `%_ratings_%` matches `players_scouted_ratings.batting_ratings_overall_contact` just as readily as the true-rating tables — i.e. the guard the scope describes as 'the ADR 0012 regression guard' would, on the next slice, block the one rating view ADR 0012:25-26 explicitly permits. The guard is also vacuous today because this slice lands no ratings at all, so nothing catches either bug before it matters.

**Proposed fix.** Key the guard on the field map's declared CATEGORY (identity / rating-true / rating-scouted / contract / structural), which the scope's own field-map artifact already carries, not on column-name globs. Assert: no field whose category is rating-true, and no field whose epistemic label is `unconfirmed` or `assumed`, is renderable. Keep name patterns only as a belt-and-braces secondary check and fix `talent_%` to `%_talent_%`. Add one negative test asserting a synthetic rating-scouted field IS renderable, so the guard cannot be satisfied by blocking everything.

#### [F10] bronze_name is listed as a landed table but has no declared grain, key, or coverage — and its source layout is the one `unconfirmed` item

*adversary:* fit-ac · *confidence:* high · *category:* completeness

**Location:** tiered_scope.core ("Tables: bronze_team, bronze_player, bronze_team_roster, bronze_name") vs acceptance_criteria[4], which declares keys only for the other three; docs/data-access.md:238 labels the names.dat table layout `unconfirmed`

**Problem.** The scope's own headline requirement is that all five dataset contracts are settled and TESTED for every landed table, and criterion 4 asserts prose grain equals emitted key so the two cannot drift. bronze_name is landed but is missing from the key list, so it is the one table where prose and enforcement are free to diverge — and it is the table sourced from the file the repo labels `unconfirmed`, holding ~264,095 entries. If the index encoding turns out to be non-positional (a hash, or a per-save permuted table — a failure mode the scope itself raises in risks[1]), the grain is not even 'one row per name index' and nothing would catch it.

**Proposed fix.** Declare bronze_name's grain and key explicitly in the scope (candidate: one row per name-table index per snapshot, key (snapshot_date, name_index), plus a stated position on whether first-name and last-name tables are one table or two — which the spike must answer before the DDL is written), add it to criterion 4's key list, and give it a coverage statement (row count vs the ~264,095 cross-checked against the in-game Database screen at data-access.md:234).

#### [F11] Criterion 6 pre-commits to an exact row-count equality between players.dat's population and the export's retired=0 subset that nobody has measured

*adversary:* fit-ac · *confidence:* medium · *category:* acceptance

**Location:** acceptance_criteria[6] ("ZERO row-count and ZERO value differences ... 259 teams, 18,072 active players (retired=0), 15,672 team_roster rows, 15 leagues")

**Problem.** The 18,072 figure is the export's `retired = 0` population (I confirmed it independently: players_scouted_ratings has exactly 18,072 distinct player_ids across each of two perspectives). The criterion assumes players.dat contains exactly that set. Nothing in docs/data-access.md establishes it; retired.dat is a separate 148 MB file, but there is no evidence that the active/retired split in the binaries is the same partition the export's `retired` flag draws. A size sanity check is only suggestive (28,653,312 / 18,072 ≈ 1,585 B per record, plausible). If players.dat also carries, say, the draft pool or unassigned internationals, the criterion FAILS ON A CORRECT PARSE and sends someone hunting a bug that is not there — the same trap the scope correctly identifies for the 26-man roster in risks[6].

**Proposed fix.** Weaken the row-count clause to a measured-then-pinned form: the first run RECORDS the parsed count and the criterion asserts the parsed set is a superset-or-equal of the export's retired=0 set with every symmetric difference enumerated by player_id and classified (retired flag, roster status, league). Only after that classification is written down does the count become a pinned equality. Keep 'ZERO VALUE differences over the landed field set for the intersecting population' as the hard assertion — that half is safe today.

#### [F12] The extraction-cost criterion is a tautology; the only real threshold is parked in gated_decisions

*adversary:* fit-ac · *confidence:* high · *category:* acceptance

**Location:** acceptance_criteria[15] ("The assertion is that the number exists and is recorded — not that it beats a threshold nobody has yet justified") vs gated_decisions[5], which proposes 10 minutes

**Problem.** A test whose assertion is 'a timer produced a number' cannot fail for any implementation, so it is not an acceptance criterion — it is a logging requirement dressed as one. The FR lists extraction cost as one of five open data contracts precisely so the weekly-re-ingestion question gets an answer; a criterion that cannot fail settles nothing. Meanwhile the scope's own gated_decisions[5] recommends stating 10 minutes BEFORE the build 'so the extraction-cost criterion is a threshold rather than a rubber stamp' — the draft names the defect and then ships it anyway.

**Proposed fix.** Fold the threshold into the criterion: assert wall-clock for a full parse of the in-scope ~46 MB set is under the agreed budget AND that the number is written to the ingest-run row and rendered in the catalog. Add the pre-registered consequence the scope already wants: exceeding it triggers a new request rather than optimization inside this one. If the operator declines to set a number, mark the criterion USER-RUN rather than leaving an unfailable test in the panel's list.

#### [SD-04] The field map as a tracked declaration with three consumers is a schema compiler folded into core, for four tables

*adversary:* scope-completeness · *confidence:* high · *category:* scope-creep

**Location:** tiered_scope.core ("field map / contract declaration as a first-class tracked artifact ... one declaration, three consumers, so drift is structurally impossible"); above_and_beyond[4] tier "core"; acceptance_criteria[3] and [13]

**Problem.** Core commits to a tracked declaration carrying per field: name, type, walker, category, epistemic label and validator tier — and then to THREE consumers reading it: the DDL emitter, the catalog generator, and the uniqueness/withhold tests. That is a schema-definition system. The justified payload is four bronze tables (bronze_team, bronze_player, bronze_team_roster, bronze_name) over a deliberately minimal field set the scope itself describes as "a maintenance liability, not a free win". ADR 0006's Notes carve-out blesses TRACKING derived schema knowledge; it does not require making it executable. Emitting DDL from a declaration is the expensive third of this, and it is the one with no second consumer to justify generalisation. CLAUDE.md's guidance is vertical slices and sizing for sustained enjoyment.

**Proposed fix.** Keep the tracked field-map declaration (it is genuinely ADR 0006's carve-out and it feeds the catalog and the withhold check honestly). Move DDL-emitted-from-declaration to gated: write four CREATE TABLEs by hand this slice, and have the grain test assert the hand DDL agrees with the declaration rather than being generated from it. That preserves the anti-drift property at a fraction of the build, and the generator becomes justified when the second parser slice adds tables.

#### [SD-05] "Two-tier ground-truth harness as a reusable component, not a one-off test" is speculative generalisation, and Tier A validates nothing this slice lands

*adversary:* scope-completeness · *confidence:* high · *category:* scope-creep

**Location:** tiered_scope.core ("Two-tier ground-truth harness as a reusable component, not a one-off test"); above_and_beyond[0] tier "core"; goals[6]

**Problem.** Two problems compound. First, the phrasing is explicit framework-building with one consumer — the stated justification is "built as one test it gets rewritten next request", which is the textbook YAGNI argument. Second, and sharper: Tier A is players.csv, whose value is exact raw ratings, and this scope cuts ratings out of core entirely. Against the core field set (player_id, team assignment, position, uniform number, DOB, bats/throws, name indices, historical_id) players.csv can corroborate DOB, uniform number and the Lahman ID for ~12,855 shipped real players and nothing else — Tier B covers all of that and more, exactly. So the "two-tier architecture is a requirement, not a nicety" argument, which the summary uses as reshape justification #3, is an argument about the NEXT slice, not this one.

**Proposed fix.** Demote to: write the parser-vs-export differential test for this slice's field set, plainly, as a test. Record in the scope (with the measured 12-distinct-values evidence) WHY a second exact tier will be mandatory the moment ratings enter, so the next request inherits the finding. Extract a harness when a second consumer exists. Drop Tier A from this slice's core or reduce it to the narrow DOB/uniform/Lahman cross-check it can actually perform, and say which.

#### [SD-06] The read-only proof hashes the entire OOTP install and saved-games tree, and is advertised as costing microseconds

*adversary:* scope-completeness · *confidence:* high · *category:* scope-creep

**Location:** acceptance_criteria[9] ("no file under $OOTP_SAVED_GAMES or $OOTP_INSTALL has a modification time or SHA-256 digest different from the pre-run manifest"); tiered_scope.cheap_folds ("challenge.dat ... and the header self-naming filename check promoted to a pre-flight ... Both cost microseconds")

**Problem.** Criterion 10 requires a SHA-256 manifest over every file under both $OOTP_SAVED_GAMES and $OOTP_INSTALL, taken before AND after a full parse. Measured 2026-08-16: the saved-games root alone contains four save directories; OOTP-AI.lg carries retired.dat at 154,088,679 bytes and players.dat at 32,070,106, and there are two further test saves plus a Challenge Mode probe. $OOTP_INSTALL is a full commercial game install. Digesting all of that twice per run is a multi-gigabyte job on every invocation of a test the scope treats as a cheap invariant. The microseconds claim in cheap_folds is about a different check (challenge.dat), but it sits adjacent and reinforces the impression that this is free.

**Proposed fix.** Scope the read-only proof to what the run actually touches: SHA-256 over the files the parser opens (the ~46 MB in-scope set) plus mtime+size only over the rest of the league directory, and drop $OOTP_INSTALL from the digest entirely (nothing in this slice opens it except players.csv, if Tier A survives SD-05). State the measured byte total the manifest covers so the criterion has a known cost.

#### [SD-07] The spike is presented as a gate but, with ratings decoupled from core, it gates nothing in this slice

*adversary:* scope-completeness · *confidence:* high · *category:* framing

**Location:** tiered_scope.core[0] ("SPIKE FIRST, GATING ONLY THE RATINGS HALF"); non_goals ("No true ratings ... reachable from any report or the catalog"); acceptance_criteria[16]; convergence_map[0]

**Problem.** Reshape #3 and convergence theme #1 both rest on decoupling: nothing in core depends on the spike's answer. The non-goals then remove ratings from every deliverable. So the spike's verdict — PASS or FAIL — changes nothing that ships in this slice. It is a valuable independent investigation producing a docs-delta, but calling it a gate is inaccurate, and it creates the impression the slice is conditional when it is not. The scope also never states what changes on a PASS verdict, which is the tell: a gate with no branch is not a gate.

**Proposed fix.** Relabel it: "an independent spike, run inside this slice because the assets are on disk and the answer is project-threatening, producing a written verdict and a docs-delta. It gates nothing in this request; it gates the NEXT one." Then state explicitly, in one line, what a PASS unlocks (the ratings slice, coaches.dat, the scale dataset) and what a FAIL triggers, and note that either way the acceptance criteria for first-sight are unchanged.

#### [SD-08] Three gated items trigger on the spike verdict, which arrives mid-build — so they can be pulled in without the human disposing them

*adversary:* scope-completeness · *confidence:* high · *category:* scope-creep

**Location:** tiered_scope.gated ("Land coaches.dat ... GATED on the spike verdict"; "Record the OSA-vs-own-scout divergence ... Gated behind both"; "Derive and register an internal->display rating-scale mapping ... depends entirely on the spike passing"); requests/README.md:38-44

**Problem.** requests/README.md:38-44 states the standing principle: scope-growing ideas are "tiered and deferred for your decision, never silently folded into the build", and "the panel proposes, you decide". A gate whose trigger condition is evaluated DURING the build by the builder is not deferred to a human — the spike runs as core item 1, its verdict lands mid-request, and a builder reading "gated on the spike verdict" has a written licence to start on coaches.dat the moment it passes. That converts three gated items into conditional core.

**Proposed fix.** Restate every one of these as gated on the OPERATOR'S DISPOSITION AFTER the spike verdict is reported, not on the verdict itself, and add a sentence to the core spike item: "the spike's only in-request output is a written verdict and a docs-delta; no code follows from it in this request regardless of the answer."

#### [SD-09] bronze's declared PKs carry no save/league identifier while the plan parses two different universes

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** acceptance_criteria[3] (keys: bronze_team (snapshot_date, team_id); bronze_player (snapshot_date, player_id); bronze_team_roster (snapshot_date, team_id, player_id, list_id)); acceptance_criteria[5] (parse `Test Save - Standard Mode.lg` and diff); risks ("THE PROBE SAVE IS CUBS-MANAGED AND DESCRIBES A DIFFERENT UNIVERSE")

**Problem.** The slice settles a grain contract — the most expensive-to-reverse artifact requests/README.md:73 names — with snapshot_date as the only universe discriminator, while simultaneously requiring the parser to process a SECOND save (the probe, human team Chicago Cubs) whose player_ids and team_ids are a different universe. The contract works today only by accident: OOTP-AI is at 2024-03-07 and the probe at 2024-03-18, so the dates happen to differ. Nothing in the scope says whether the probe's parser output lands in bronze or stays in memory. If it lands, the catalog's coverage statements and criterion 8's "exactly 30 teams at MLB level" are computed over two universes; if it does not, the loader path is never exercised by the differential test that is supposed to prove it.

**Proposed fix.** Settle it explicitly. Recommended: add a `save_id` (or `league_id`) column to every bronze PK, resolved from the .env key naming the save, so the contract is correct by construction rather than by calendar coincidence; and state that the probe's rows land in a separate schema or carry a distinct save_id and are excluded from every report and catalog coverage count by a WHERE clause the catalog declares. Alternatively state plainly that the differential test compares parser output in memory and never lands, and accept that the loader is proven only against the managed save.

#### [SD-10] names.dat is byte-identical in SIZE across three saves but differs in CONTENT — the scope's stated ADR 0005 routing reason is measurably wrong, and a probe-derived name index does not transfer

*adversary:* scope-completeness · *confidence:* high · *category:* risk

**Location:** non_goals ("names.dat lives in the save and grows as fictional players are generated, so it is a save fact, not static reference"); tiered_scope.core (names.dat join); risks ("nothing may hardcode the human team")

**Problem.** Measured by me 2026-08-16 across all three saves on disk: names.dat is 8,642,110 bytes in OOTP-AI.lg, in `Test Save - Standard Mode.lg` AND in `Test Save - Challenge Mode.lg`, with three DIFFERENT SHA-256 digests. Two consequences the scope misses. (1) The justification it gives for routing names.dat to the parser side — "it grows as fictional players are generated" — is refuted: three independently created saves produce an identical-size table. The routing CONCLUSION survives (content differs per save, so it is a save fact) but the reason recorded in a non-goal is an unlabelled assumption the measurement contradicts, and this repo's whole labelling discipline exists to stop exactly that. (2) A fixed-size table with per-save content means the index->string mapping is per-save. The scope names the hazard's twin ("nothing may hardcode the human team or the scouting perspective") but never its sibling: a name index resolved and validated on the probe save does not denote the same string in OOTP-AI, so no probe-derived index, cached lookup or golden expectation may be carried into the managed league's path.

**Proposed fix.** Replace the non-goal's reasoning with the measurement: "names.dat is 8,642,110 bytes in all three saves on disk with three different SHA-256 digests (measured 2026-08-16) — a fixed-size, per-save-populated table, not a growing one. It is therefore a save fact and routes to the parser side under ADR 0005, and its content is per-save." Add a named constraint alongside the human-team one: nothing may carry a name index, an index->string expectation, or a cached name table from the probe save into the managed league, and add an assertion that resolving the same index in both saves is NOT expected to yield the same string. Route the finding to docs/data-access.md through the doc gate with an `inferred` label on the fixed-size claim.

#### [SD-11] Nothing owns handing the GM its report paths — the FR's headline observable signal has no delivery mechanism

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** acceptance_criteria[18] (USER-RUN: cold session spawns the gm subagent ... names at least five Boston players); .claude/agents/gm.md:32 and :4; gated_decisions[2] ("have the umpires hand the GM its report paths at spawn time")

**Problem.** The entire feature is justified by one signal: a cold `gm` spawn returns a handoff naming real Boston players. .claude/agents/gm.md:4 grants only `Read, Glob`, and its forced-read item 8 is "Any report or analysis handed to you for this invocation" — so the mechanism exists in principle, but the scope's own gated decision routes report delivery to "the umpires hand the GM its report paths at spawn time" and calls it "a new umpire obligation nothing currently records". Nothing in the scope creates that record either. The tracked half was assigned to gm/standing-orders.md, which SD-03 shows cannot be written as specified. So the deliverable ships and the signal is unreproducible by anyone who was not in the room.

**Proposed fix.** Add a core deliverable that is genuinely cheap and closes the loop: a tracked, generated pointer the umpires read at spawn time — a short section in the tracked half of the catalog listing each report's logical name and the .env key + relative path it resolves to, with a one-line spawn instruction. Do NOT make it a Markdown link into var/ (see SD-12). Then criterion 19 becomes reproducible: the operator follows a written procedure rather than remembering one.

#### [SD-12] The scope names the var/-link half of the doc-link defect but not the `file.py:123` half, and its own artifacts are saturated with line-suffixed citations

*adversary:* scope-completeness · *confidence:* high · *category:* risk

**Location:** risks ("tests/test_doc_links.py FAILS CI ON ANY TRACKED MARKDOWN LINK INTO var/"); requests/bugfix-requests/_done/doc-link-guard-mismatch/BUGFIX_REQUEST.md:18-26 and :45-55; tests/test_doc_links.py:10 and :33-37

**Problem.** The open bugfix request records THREE constructs that trip the live guard: links inside fenced code blocks, citations carrying a `file.py:123` line suffix, and `var/` targets. The scope's risk register names only the var/ one. Every artifact this pipeline produces downstream — PROJECT_SCOPE.md, IMPLEMENTATION_PLAN.md, IMPLEMENTATION_REPORT.md, the data-engineer's handoff under reviews/ — is tracked Markdown scanned by tests/test_doc_links.py, and this scope's prose cites roughly forty `path:line` references. Any one of them written as a Markdown link turns CI red before a byte of parser code is written. The BUGFIX_REQUEST itself notes it was "written around the defect, by using code spans instead of links" — that workaround is nowhere in this scope. Separately the scope's risk phrasing is imprecise: the guard fails when the link TARGET does not resolve on disk, which is why it is green locally and red on a fresh clone.

**Proposed fix.** Add an explicit authoring constraint to the scope, binding on every downstream artifact: cite files as inline code spans (`src/ootp_ai/parser.py` line 42), never as Markdown links, and never link a var/ target. Restate the risk precisely: test_doc_links.py resolves every relative Markdown link target against the filesystem, so a var/ target passes on the dev machine and fails on a fresh clone, and a `:line` suffix fails everywhere.

#### [SD-13] Cross-schema exact string comparison with no collation decision, in a repo whose export doc says accents break names validation

*adversary:* scope-completeness · *confidence:* high · *category:* risk

**Location:** acceptance_criteria[6] (names match ootp_truth_real.players.first_name/.last_name "by exact string equality, 100% of compared rows"); acceptance_criteria[5]; docs/data-access.md:336 (`Replace accents` — Off, "mangles names and breaks validation against names.dat"); tiered_scope.core (MySQL bronze landing)

**Problem.** The slice writes the repo's first DDL and immediately asserts exact string equality between a bronze table it creates and ootp_truth_real tables the GAME's exporter created, with whatever charset and collation that dump chose. The scope settles types, keys, grain, coverage and update semantics but never charset or collation. MySQL 8.4 raises "Illegal mix of collations" on a cross-collation comparison, or compares under coercion rules that silently differ for accented characters — and docs/data-access.md:336 already records that accent handling is the specific thing that "breaks validation against names.dat". A collation mismatch will surface as name-join failures on exactly the accented players and will look indistinguishable from a parser bug, which is the silent-misparse class requests/README.md:20-31 built a whole track for.

**Proposed fix.** Settle it in the scope as a sixth contract alongside the five: bronze DDL pins `CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs` (accent- and case-sensitive, so the comparison is honest), and the differential query states its collation explicitly with `COLLATE` on the join predicate. Add an acceptance sub-assertion that at least one accented name is present in the compared population and matches, so the check cannot pass vacuously on an ASCII-only sample.

#### [SD-14] The first runtime dependency is named as a risk but never chosen, under mypy strict over both src and tests

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** risks ("THE FIRST DEPENDENCY LANDS HERE ... The MySQL driver plus mypy-strict stubs"); pyproject.toml:9-15 and :69-73; .github/workflows/ci.yml (`uv sync --all-extras --dev`, then `uv run mypy`)

**Problem.** pyproject.toml:9 is `dependencies = []` with a comment stating the first real dependency arrives with the warehouse loader. This slice is that loader. The scope flags the commitment as a risk and stops there. The choice is not a stage-3 implementation detail: mypy is `strict = true` over `files = ["src", "tests"]`, and the three candidates behave differently — `mysqlclient` needs a C toolchain (fine on ubuntu CI, painful on the Windows dev box), `mysql-connector-python` ships uneven inline types, `PyMySQL` is pure-Python but needs `types-PyMySQL` added to the dev group or strict mode fails on every import. CI runs `uv sync --all-extras --dev` then `uv run mypy`, so a wrong choice reddens the build for a reason unrelated to the feature.

**Proposed fix.** Name the driver in the scope with its rationale and its typing story, and state which dependency group it goes in (runtime, not dev — the loader needs it at runtime) plus any `types-*` stub that must join the dev group. Recommend PyMySQL + types-PyMySQL for a pure-Python install that works identically on the Windows dev machine and ubuntu CI, and record it as the first entry under pyproject's "dependencies arrive with the source that requires them" comment.

#### [SD-15] The warehouse metadata label table is a third copy of a fact the repo's routing rule exists to keep singular

*adversary:* scope-completeness · *confidence:* medium · *category:* scope-creep

**Location:** tiered_scope.cheap_folds ("Write each field's epistemic label into a warehouse metadata table alongside the data, not only into docs"); above_and_beyond[8]; .claude/agents/data-engineer.md:238-251

**Problem.** data-engineer.md:249-251 states the reason data facts route to docs/data-access.md and nowhere else: "A data fact that lands only in memory means the repo holds two answers and the gate checks one." This fold creates a THIRD home for every epistemic label — docs/data-access.md (audited by /update-docs), the tracked field-map declaration (SD-04), and now a MySQL table (audited by nothing, rebuilt by the loader, invisible to the doc gate). The stated benefit, answering "what did we believe the day it was landed", is already served by the ingest-run row plus git history of the tracked field map, both of which are in core.

**Proposed fix.** Drop it, or reduce it to a generated projection: if the label lands in the warehouse at all, it is written BY the loader FROM the tracked field-map declaration in the same run, never authored, and the catalog states that the warehouse copy is derived. Say explicitly which artifact is authoritative when they disagree — the tracked declaration — so a future data incident has a resolution rule rather than three answers.

#### [SD-16] catalog.json is folded in for advisors the same scope forbids

*adversary:* scope-completeness · *confidence:* medium · *category:* scope-creep

**Location:** tiered_scope.cheap_folds ("Emit a machine-readable catalog.json ... future umpire-spawned advisors will want to discover tables and grains"); above_and_beyond[7]; non_goals ("No advisors of any kind"); CLAUDE.md project map ("don't create them speculatively")

**Problem.** The sole named consumer of catalog.json is "future umpire-spawned advisors", which this scope's own non-goals put entirely out of scope. The GM holds Read and Glob and reads Markdown. So the fold ships a second serialization with zero consumers in this slice, and it is not free: acceptance criterion 14 already demands byte-identical regeneration of the Markdown, and a JSON sibling doubles that assertion surface and creates a second thing that can drift from information_schema.

**Proposed fix.** Move to gated, disposed together with the first advisor request that actually needs programmatic discovery. If the operator wants it now, argue it on a consumer that exists in this slice — there isn't one.

#### [SD-17] Deriving list_id semantics is open-ended research folded into core with no fallback, and it blocks the headline report

*adversary:* scope-completeness · *confidence:* high · *category:* risk

**Location:** tiered_scope.core ("Roster-list extraction ... INCLUDING empirically deriving what each list_id VALUE means"); risks ("list_id IS AN UNDOCUMENTED ENUM"); acceptance_criteria[12] (roster.md "grouped by roster list")

**Problem.** Core commits to empirically deriving an undocumented enum's value semantics by cross-tabbing against ootp_truth_real.team_roster and the install's db_structure file — which the scope itself says gives "no value semantics". Measured 2026-08-16 the distribution is {1:7370, 2:7037, 3:935, 4:330} over 15,672 rows and 18,072 active players. Deriving what those mean is genuine research with an unbounded tail, it sits on the critical path of the FR's headline deliverable (roster.md "grouped by roster list"), and the scope pre-registers a fallback for the names join (gated_decisions[7]) but none for this. If the enum resists, the roster report either groups by a bare integer or blocks.

**Proposed fix.** Pre-register the fallback in the scope, alongside the names one: if the list_id mapping cannot be established to a `verified` or at minimum `inferred` label, land list_id as an opaque integer, group roster.md by its raw value with a header line stating the meanings are `unconfirmed`, and file a follow-up. Add a positive assertion that the report NEVER prints a human label ('active roster', '40-man') for a list_id whose mapping is not labelled at least `inferred` — a wrong label produces a confidently wrong roster with nothing throwing, which is the exact failure class requests/README.md:20-31 describes.

#### [SD-18] The scope defers the FR's third Desired Outcome without ever saying so in the acceptance criteria

*adversary:* scope-completeness · *confidence:* high · *category:* framing

**Location:** requests/feature-requests/first-sight/FEATURE_REQUEST.md:40-42 (Desired Outcome 3) and :152-153 (Open Question 6); tiered_scope.gated ("The full docs/league-rules.md §1 diff"); acceptance_criteria[17]

**Problem.** The FR states three things that are true when this is done; the third is "We can confirm the league is what we think it is", with §1's values diffed against parsed values "and the differences — or their absence — recorded". The reshape demotes that to gated on well-evidenced grounds (I re-verified the world.dat location myself). But the acceptance criteria never state that Desired Outcome 3 is NOT delivered. Criterion 18 only requires the leagues.dat doc correction. An operator reading the criteria list, or an acceptance panel checking it, cannot see that a third of the FR's stated outcome was deferred. Separately, FR Open Question 6's second half — "what happens to the document when parsed values disagree with it?" — is never answered anywhere in the scope.

**Proposed fix.** Add an explicit non-goal: "Desired Outcome 3 (confirming the league's configuration against docs/league-rules.md §1) is NOT delivered by this slice; only the two measurably-wrong doc claims are corrected. The diff moves to gated because the configuration block is in world.dat, an 8.9 MB unmapped binary with no export of our Challenge Mode league to validate against." And answer Open Question 6 in one sentence now, before it can be argued at delivery: parsed values supersede §1 and the doc records the parsed value with a `verified` label plus the superseded belief, per league-rules.md:26.

#### [SD-19] league-rules.md:26 and :31 become false on delivery and nobody has scoped fixing them

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** docs/league-rules.md:26 ("the warehouse supersedes this the moment the parser lands") and :31 ("§1 is scaffolding and should be deleted when it stops being needed"); tiered_scope.core (Documentation corrections)

**Problem.** league-rules.md's own 'How to read this' table states that §1 is "Temporary. Every value is a column on the `leagues` row; the warehouse supersedes this the moment the parser lands." This slice lands the parser and does NOT supersede §1 — the league config is in world.dat and the diff is gated (SD-18). So a tracked doc claim flips from true-in-anticipation to false-in-fact on the day this ships, and the scope's documentation-corrections item lists four deltas without including it.

**Proposed fix.** Add it to the core doc-correction set: amend league-rules.md:26 to say the warehouse supersedes §1 when the parser can read the league configuration block, which this slice does not do, with a pointer to the gated work. Cheap, and it prevents a future reader concluding from :26 that §1 is already superseded and stale.

#### [SD-20] A Challenge Mode probe save exists and is never mentioned, while every gamedata test is aimed at the irreplaceable managed league

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** grounding_pointers (lists only OOTP-AI.lg and `Test Save - Standard Mode.lg`); acceptance_criteria[7] (test_parse_real_save against OOTP-AI.lg), [9] (test_read_only), [8] (test_snapshot_semantics); docs/decisions/0003-challenge-mode-league.md; .claude/agents/data-engineer.md:55-58

**Problem.** Measured 2026-08-16, the saved-games root contains four entries: the stray `.lg` directory, `OOTP-AI.lg` (19 .dat files), `Test Save - Standard Mode.lg` (18 .dat files), and `Test Save - Challenge Mode.lg` (19 .dat files). The scope never mentions the third save. It is the obviously correct target for first exercising the enumerator, the header guard, the challenge.dat==241 mode detection and above all the read-only proof — a disposable save in the SAME mode as the managed league, where a mistake costs nothing. data-engineer.md:55-58 states one write to the managed league is irreversible with no backup upstream. Pointing the first read-only proof of untested code at the irreplaceable save, when an identical-mode disposable one sits beside it, is an avoidable exposure.

**Proposed fix.** Add `Test Save - Challenge Mode.lg` to the grounding pointers with its measured shape, and add a core sequencing constraint: every filesystem-touching test — enumerator, header guard, snapshot copy, read-only proof — runs first against the disposable Challenge Mode save and only then against OOTP-AI.lg. Add a .env key for it alongside the proposed OOTP_TRUTH_SAVE so it resolves by name.

#### [SD-21] Regenerating the report overwrites the prior snapshot's view, breaking citation integrity for gm/decisions records

*adversary:* scope-completeness · *confidence:* medium · *category:* completeness

**Location:** tiered_scope.core ("Two Markdown reports under var/"); risks ("REPORT ROT ... Do NOT build a freshness framework in this slice"); gm/README.md:140-147; docs/decisions/0011-gm-memory-is-tracked.md

**Problem.** The reports are named roster.md and standings.md with no snapshot dimension in the path, so the next ingestion at a new sim date overwrites them. gm/decisions/ records are required to state "what was decided, why, what was expected" and .claude/agents/gm.md:62-64 requires every factual claim in a GM handoff to be traceable to something it read. Once the report a decision cited has been overwritten, the citation is unresolvable and the decision record cannot be audited against what was actually in front of the GM — which is precisely the failure ADR 0011 exists to prevent. The scope's REPORT ROT risk names staleness (the GM reading an old report as current) but not the inverse and more damaging one (the record pointing at a view that no longer exists).

**Proposed fix.** Put snapshot_date in the report path — var/reports/<snapshot_date>/roster.md — and optionally a stable `latest` pointer for the umpires to hand the GM. This is a path-construction change, not a freshness framework, so it does not violate the scope's own non-goal, and it makes the append-only/immutable semantics the scope already settles for the warehouse hold for the serving layer too.

### MINOR (14)

#### [F13] The fixed-offset static scan bans an idiom nobody writes and misses the one that actually breaks

*adversary:* fit-ac · *confidence:* high · *category:* acceptance

**Location:** acceptance_criteria[3]; the invariant it encodes is .claude/agents/data-engineer.md:69-74

**Problem.** The scan looks for `.seek(<nonzero int literal>)` and `struct.unpack_from` with a constant record-relative offset. Both are trivially avoided while remaining exactly as wrong: `RATINGS_OFF = 43` then `unpack_from(FMT, buf, RATINGS_OFF)` passes, as does `f.seek(record_start + 43)`. Conversely `f.seek(pos)` with a computed pos is the normal, correct sequential idiom, so the check's true-positive rate on real code is close to zero. Presenting it as 'encoding data-engineer.md:69-72 as a mechanical check rather than a review convention' overclaims what a mechanical check can do here.

**Proposed fix.** Keep the scan as a cheap tripwire but stop claiming it enforces the invariant, and add the check that actually can: criterion 2's differential fixture test is the real guard, so strengthen it — two synthetic records differing in the length of a variable-length region must agree on every field parsed after it, AND a third fixture where the region grows past a byte boundary that shifts alignment. Additionally ban module-level integer constants whose names match `_OFF(SET)?$` inside src/ootp_ai/parser/, which catches the named-constant workaround.

#### [F14] Criteria 17 and 18 are not mechanically checkable as written

*adversary:* fit-ac · *confidence:* high · *category:* acceptance

**Location:** acceptance_criteria[17] ("has a WRITTEN VERDICT committed ... stating stored-or-computed with an epistemic label") and [18] ("a grep asserting the string `leagues.dat` appears nowhere in docs/ except as an explicit correction note")

**Problem.** requests/feature-requests/README.md:70-72 defines testable as 'a cold agent can run one command and get a pass or fail'. Criterion 17 requires a human to read a document and judge whether it states a verdict and carries a label. Criterion 18's 'except as an explicit correction note' is an unbounded exception — a grep cannot distinguish a correction note from a residual wrong claim, so the check either fails on the correction itself or passes on anything.

**Proposed fix.** Make 17 file-and-grammar checkable: assert a file exists at a named path, its first line matches the handoff/verdict marker, and it contains exactly one of the tokens `stored` / `computed` / `inconclusive` together with one of the five epistemic labels — then mark the JUDGMENT half USER-RUN. For 18, drop the prose exception and assert instead that no line in docs/ matches `leagues\.dat` UNLESS that line also contains a fixed sentinel token (e.g. `[corrected 2026-08]`), which is grep-able. Both are then one command with a pass/fail.

#### [F15] The test_doc_links.py mechanism is mis-stated, and the real failure mode (green locally, red in CI) is more dangerous than the one described

*adversary:* fit-ac · *confidence:* high · *category:* fit

**Location:** acceptance_criteria[16] ("it fails on any tracked Markdown link into var/"), risks[12]; actual behaviour at tests/test_doc_links.py:15 and :33-36

**Problem.** The guard is `REPO_ROOT.rglob("*.md")` filtered on `.git` and `var` not being path PARTS — it scans every Markdown file in the worktree, tracked or not, and it fails only when the link TARGET does not resolve on disk. So a tracked link to `var/reports/roster.md` passes on the developer's machine the moment the report has been rendered, and fails in CI and on any fresh clone where var/ is empty. That is strictly worse than 'fails on any link into var/', because the failure is invisible to the person who introduced it. It also means the PROJECT_SCOPE.md and IMPLEMENTATION_PLAN.md themselves are scanned even before they are committed.

**Proposed fix.** Restate the risk accurately in the scope, and make the mitigation explicit rather than implied: no tracked Markdown may link into var/ at all, including gm/standing-orders.md's report entries — the entry names the report and its owner, and the PATH reaches the GM only via the umpires at spawn time. Add that umpire obligation as a named deliverable (it currently exists nowhere), and add a guard-side assertion to the criterion: `git ls-files '*.md' | xargs grep -l '](.*var/'` returns nothing.

#### [F16] The read-only proof as specified hashes the entire game install and saved-games tree

*adversary:* fit-ac · *confidence:* medium · *category:* acceptance

**Location:** acceptance_criteria[10] ("no file under $OOTP_SAVED_GAMES or $OOTP_INSTALL has a modification time or SHA-256 digest different from the pre-run manifest")

**Problem.** $OOTP_SAVED_GAMES holds three .lg directories including two retired.dat files at 154,088,679 and 148,283,289 bytes plus a 56 MB export tree; $OOTP_INSTALL is a full Steam game directory. SHA-256 over all of it, twice per test run, is minutes of I/O for a test that will be run repeatedly. The criterion is right in principle — ADR 0001 is the one unrecoverable failure and deserves a test rather than a promise — but as scoped it will be disabled by whoever has to wait for it, which is how guards die.

**Proposed fix.** Scope the digest set to what the run actually touches plus a cheap tripwire on the rest: SHA-256 for every file the parser opens (the ~46 MB in-scope set plus challenge.dat and saved_games.dat), and size+mtime only for everything else under both roots. Keep the full-digest form available behind an explicit flag for the USER-RUN check in criterion 20.

#### [F17] A third save exists — 'Test Save - Challenge Mode.lg', Boston, 03/18/2024 — and the scope never mentions it

*adversary:* fit-ac · *confidence:* high · *category:* completeness

**Location:** $OOTP_SAVED_GAMES enumeration (measured today: `.lg`, `OOTP-AI.lg`, `Test Save - Challenge Mode.lg`, `Test Save - Standard Mode.lg`, `saved_games.dat`); saved_games.dat records it as Boston Red Sox, 03/18/2024

**Problem.** The scope's save enumerator design, its `.lg`-glob trap discussion, and its 'nothing may hardcode the human team' constraint all reason over a two-save world. There are three. The Challenge Mode probe is the closer structural analogue to OOTP-AI (same mode, same club, same challenge.dat presence) and is the only save on which the challenge-mode preflight can be tested POSITIVELY without touching the managed league. Omitting it also means the enumerator's acceptance is under-specified: 'confirms players.dat and teams.dat exist' must return three saves, not two.

**Proposed fix.** Name all three saves in the scope's grounding pointers, and add to the enumerator criterion that it returns exactly the three real saves and excludes the stray `.lg` directory. Use Test Save - Challenge Mode.lg as the positive fixture for the challenge.dat/241-byte preflight and for exercising the ADR 0001 read-only proof, so the first real exercise of that code path is not against OOTP-AI.lg.

#### [F19] saved_games.dat is called PLAINTEXT and used as a test oracle; it is a headered binary containing absolute OneDrive user paths

*adversary:* fit-ac · *confidence:* high · *category:* risk

**Location:** grounding_pointers ("$OOTP_SAVED_GAMES/saved_games.dat — PLAINTEXT and readable with no parser"), cheap_folds ("Resolve the human team FROM DATA"), acceptance_criteria[6] provenance assertion; measured: the file opens `00 'OOTP' ...` with the same header shape as the .dat files and embeds an absolute user-profile path (`<drive>:\Users\<user>\OneDrive\Documents\...` — rendered with placeholders here; the literal form trips this repo's own leak guard) for every save

**Problem.** Two issues. (a) It is not plaintext — it carries the standard OOTP header and length-prefixed strings; 'readable with no parser' means substring-scraping a binary, which is exactly the fragile approach this repo's discipline forbids, and it is being proposed as the oracle for criterion 6's provenance assertion and for the human-team resolution. (b) Every record embeds an absolute user-profile path. Any tracked artifact that quotes or renders those — a catalog's provenance section, an ingest-run dump pasted into a handoff, a docs correction — trips tests/test_no_leaks.py's `windows drive path` pattern (line 25) and fails CI, and worse, publishes a username to a public repo.

**Proposed fix.** Rewrite the pointer to say saved_games.dat shares the standard header and is parsed by the same header reader plus a string walk — not scraped. Add an explicit constraint to the catalog and field-map specs: the TRACKED half may name source FILES (`players.dat`) but never absolute paths; absolute paths live only in the var/ half and the warehouse ingest-run row. Add that to the withheld/leak criterion so it is mechanically checked rather than remembered.

#### [F20] The dbt deferral is characterised as diverging from ADR 0005's 'tooling phrasing'; the medallion is in ADR 0005's Decision, not its Notes

*adversary:* fit-ac · *confidence:* high · *category:* framing

**Location:** non_goals[0] and fit_verdict RESHAPE 4; docs/decisions/0005-hybrid-data-layer.md:31-34 — the Decision section reads "Snapshot facts → dbt medallion in MySQL: bronze (faithful landing of parser output), silver (conformed, grain-declared), gold (serving models)"

**Problem.** The scope repeatedly softens this to 'ADR 0005's *tooling* phrasing' and asserts 'the PATTERN choice is honoured in full'. The pattern choice (parser side, not builder side) genuinely is honoured — but dbt and the three named layers are in the Decision, which is the binding part of an ADR, not a note. The brief this scope answers requires that a scope contradicting an accepted ADR say so explicitly rather than quietly diverging; describing a Decision-section divergence as a phrasing matter is the soft version of quiet. Separately, hand-rolled SQL plus a thin runner is verbatim ADR 0004 §Notes option 2, so the slice is not deferring the adapter decision so much as provisionally taking one of the four live options.

**Proposed fix.** State it plainly in the non-goal: this slice diverges from ADR 0005's Decision by landing bronze without dbt, honours 0005's builder-vs-parser boundary rule in full, and provisionally exercises ADR 0004 §Notes option 2 without adopting it. Keep gated_decisions[8]'s recommendation (a note in ADR 0004 §Notes recording the trigger and why it was not pulled) but extend it to ADR 0005, and let the operator pick the weight.

#### [F22] The MySQL-side measurements cannot be reproduced from the repo and should carry an inherited label rather than a measured one

*adversary:* fit-ac · *confidence:* medium · *category:* risk

**Location:** fit_verdict ("the `ootp` MySQL schema exists with 0 tables (measured via information_schema...)"), non_goals[11] ("ootp_truth_osa exists with 0 tables"), and every ootp_truth_real row count

**Problem.** I could verify the row counts and column shapes from the export .sql files still on disk — and they match the scope exactly (259 team_record rows all zero, 132,990 players_batting rows with 12 distinct contact values, 36,144 scouted rows split 18,072/18,072, 15,672 roster tuples, 15 leagues) — but I could not reach the MySQL server, so the claims that specifically concern the SERVER state cannot be checked: that `ootp` exists with 0 tables, that `ootp_truth_osa` exists with 0 tables, and that ootp_truth_real is actually loaded with all 72 tables rather than merely dumped to disk. Two scope decisions rest on these: 'land bronze into the empty `ootp` schema' and 'retire ootp_truth_osa, the premise is measurably wrong'.

**Proposed fix.** Relabel the three server-state claims from `measured` to `measured, not re-verified` with the date, and make the first thing the implementation does a preflight that asserts them (schema `ootp` exists and is empty, `ootp_truth_real` has 72 tables with the recorded row counts) so a stale belief fails loudly at run one instead of producing a confusing landing error. The export-file-derived counts can stay `measured` — I reproduced them.

#### [F23] The ADR 0012 non-goals imply classification work that this slice does not do, making the withhold guard vacuous by design

*adversary:* fit-ac · *confidence:* high · *category:* non-goals

**Location:** non_goals[7] ("A field that cannot be classified is withheld — 'probably fine' is not a classification"), acceptance_criteria[12] ("Trivially satisfied by this slice"); ADR 0012:57-59 places the classification burden on the parser

**Problem.** ADR 0012's cost section is explicit that 'the parser still has to identify true-rating fields precisely enough to *exclude* them, which is more work than ignoring them would be.' By decoupling ratings entirely, this slice does none of that work — and the non-goal is phrased in the language of active withholding, which reads as though classification is happening and being enforced. It is not: nothing rating-shaped is parsed, so nothing is withheld, and the guard is green because the set it checks is empty. That is a legitimate reshape but the non-goal describes it as compliance rather than as deferral.

**Proposed fix.** Rewrite the non-goal to say what is true: this slice parses no rating field of any kind, so ADR 0012's classification obligation is DEFERRED, not satisfied, and the withhold guard is a forward-dated regression net rather than evidence of compliance. Add the deferral as a named follow-up so the next request inherits it as an open obligation rather than assuming it was discharged here.

#### [SD-22] Extending test_no_leaks to catch rendered game data cannot fire, because it only scans tracked files

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** tiered_scope.cheap_folds ("Extend tests/test_no_leaks.py to catch RENDERED game data in tracked files"); tests/test_no_leaks.py:31-48 and :97-116

**Problem.** tests/test_no_leaks.py builds its scan set from `git ls-files` (line 32-38) and its game-data guard checks only tracked paths (line 99-116). The reports land in var/, which is gitignored, so there is nothing for either check to see. The proposed extension can therefore only ever fire AFTER someone has run `git add -f` on a report — at which point the .gitignore rule and /commit's refusal have already both been overridden deliberately. As written the fold buys close to nothing while reading like a real guard, which is worse than an absent one.

**Proposed fix.** Replace it with a check that can actually fail: assert that the resolved report and catalog output roots are gitignored, by shelling `git check-ignore -q <resolved path>` and asserting exit 0 (this also satisfies SD-01). Keep it in the offline, unmarked test set by resolving the path from .env with a documented default rather than requiring the file to exist.

#### [SD-23] README.md's setup block runs bare `uv run pytest`, which stops working on a fresh clone the moment gamedata tests exist

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** README.md:95-99; pyproject.toml:78-81; .github/workflows/ci.yml

**Problem.** README.md:98 tells a new user to run `uv run pytest` with no marker filter. Today that is safe: all four test modules are structural and offline. This feature introduces the repo's first `gamedata`-marked tests (and, per SD-02, database-dependent ones), so the documented setup command will start erroring for anyone following the README on a machine without a save or a warehouse. The scope's documentation-corrections item lists four deltas and README is not among them.

**Proposed fix.** Add README.md:98 to the core doc-correction set: change the setup command to `uv run pytest -m "not gamedata"` and add one line explaining that the marked tests need a local OOTP install and warehouse. It is a two-line edit routed through /update-docs with the rest.

#### [SD-24] Measured file count is wrong: OOTP-AI.lg holds 19 .dat files, not 18, and text_data.dat is undocumented

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** fit_verdict.rationale and summary ("OOTP-AI.lg holds 18 .dat files", stated twice); convergence_map[1] ("the same 18-file list"); tiered_scope.core (doc correction: "docs/data-access.md §1's file table is incomplete (18 .dat files present)"); docs/data-access.md:39-55

**Problem.** Measured 2026-08-16: OOTP-AI.lg contains 19 files with a .dat extension. The scope's own enumeration lists 19 names (challenge, coaches, faces, flag_save_completed, games_in_progress, human_managers, messages, names, offers, parks, players, retired, scouting, storylines, teams, text_data, trades, weather, world) while its prose says 18, in three places including the convergence map's claim that three scopers independently produced the same 18-file list. This matters more than arithmetic usually would because the scope proposes CORRECTING docs/data-access.md §1's file table using this list, so the wrong count would be landed as a `measured` claim. Separately, `text_data.dat` (3,262,337 bytes, at the save root) is distinct from the `temp/text_data.sqlite3` that data-access.md:52 documents, and neither the scope nor §1 accounts for it — while the scope's non-goals exclude only "text_data.sqlite3".

**Proposed fix.** Correct the count to 19 everywhere, and note the comparison shape: `Test Save - Standard Mode.lg` holds 18 and `Test Save - Challenge Mode.lg` holds 19, consistent with challenge.dat being the mode-dependent file (data-access.md:65-68). Add `text_data.dat` to the §1 correction as a distinct file from temp/text_data.sqlite3, and extend the non-goal to name both.

#### [SD-25] The dbt deferral diverges from ADR 0005's Decision text, not from incidental phrasing, and the scope soft-pedals it

*adversary:* scope-completeness · *confidence:* high · *category:* fit

**Location:** non_goals ("Stated as a narrow divergence from ADR 0005's tooling phrasing"); fit_verdict ("only its 'dbt medallion' tooling phrasing is deferred"); docs/decisions/0005-hybrid-data-layer.md:31-34

**Problem.** ADR 0005's Decision section — not its Notes, not incidental phrasing — reads: "Snapshot facts -> dbt medallion in MySQL (ADR 0004): bronze (faithful landing of parser output), silver (conformed, grain-declared), gold (serving models for the front office)." The scope's deferral is a divergence from that Decision as written. Describing it three times as a divergence from "tooling phrasing" understates it, and CLAUDE.md's instruction to scopers is that a scope contradicting an accepted ADR must say so explicitly rather than quietly diverging. Half-saying it is the failure mode the rule targets. (The reasoning behind the deferral is sound — ADR 0004:89-106 is explicit that no dependency has been taken and the call comes due with the first dbt model.)

**Proposed fix.** Restate it plainly in the non-goals and in gated_decisions[8]: "This slice does not implement ADR 0005's Decision as written. Bronze lands through a hand-rolled loader and the two reports are served by hand SQL; no silver or gold dbt layer exists. ADR 0005's boundary RULE (parser side, not builder side) is honoured in full; its named implementation is deferred." Leave the amendment-vs-supersession weight to the operator as already proposed.

#### [SD-26] The withhold guard's column-name patterns are the weak half and will be trivially bypassed by the next field named contact_vr

*adversary:* scope-completeness · *confidence:* medium · *category:* acceptance

**Location:** acceptance_criteria[11] (patterns `%_ratings_%`, `prone_%`, `talent_%`, `players_value%`); docs/decisions/0012-scouted-ratings-only.md:57-59 and :77

**Problem.** Criterion 12 pairs two mechanisms: a name-pattern blacklist and a field-map category/label check. The pattern half matches the EXPORT's column naming (players_batting.batting_ratings_overall_contact), not the parser's — our own field map is free to name a field `contact_vr`, `pot_power`, or `stuff`, none of which matches any pattern. Since the scope also acknowledges the criterion is "trivially satisfied today", the risk is that the pattern half creates false confidence in a guard that is only as good as future naming discipline. ADR 0012:57-59 requires withholding by CLASSIFICATION ("a field we cannot classify must be treated as true-rating and withheld"), which the category half implements correctly and the pattern half does not.

**Proposed fix.** Make the category/label check the primary and sole assertion — no field whose declared category is rating-true or unclassified, and no field whose epistemic label is `assumed` or `unconfirmed`, is renderable — and keep the name patterns only as a secondary belt-and-braces check explicitly documented as non-authoritative. Add the assertion that every landed field HAS a category, so an unclassified field fails the build rather than defaulting to renderable.

### NIT (4)

#### [F18] Several cited line numbers are off by one to five, and two are cited as ranges that do not contain the quoted text

*adversary:* fit-ac · *confidence:* high · *category:* fit

**Location:** scope cites docs/league-rules.md:295 (actual :296), docs/data-access.md:223-226 (the 5-string signature is :224-226), docs/data-access.md:288-295 (the test is :292-295; :289 is the ~128 B/player inference), tests/test_no_leaks.py lines 97-113 (the function runs 97-116)

**Problem.** The scope's authority rests substantially on precise citation, and the adversarial and planning stages verify cited lines against the real files. Off-by-one citations cost a cold agent a re-read each time and, at :288-295, blur a `measured` claim into an `inferred` one — :289's 2.3 MB / ~128 B-per-player figure is explicitly labelled 'a guess, not a finding' in the source, while the scope cites the range as if it were the test.

**Proposed fix.** Correct the four citations. For the data-access.md §5 pointer specifically, cite :292-295 for the test and cite :289 separately with its own label, so the spike's brief does not inherit an inference as evidence.

#### [F21] Two facts already recorded in docs are presented as fresh measurements, which inflates the apparent novelty of the reshape

*adversary:* fit-ac · *confidence:* high · *category:* framing

**Location:** tiered_scope.core ("Measured trap: the saved-games root contains a stray empty directory literally named `.lg`") and ("Assert Challenge Mode from the filesystem via challenge.dat at exactly 241 bytes"); both are already `measured` in docs/data-access.md:60-63 and :65-68

**Problem.** The scope's rhetorical weight rests on 'three of which I confirmed by measurement today rather than inheriting from a scoper'. Re-presenting two already-documented `measured` facts as new measurements dilutes that signal and makes it harder for the next stage to tell which claims genuinely need re-verification. It is a labelling error of the kind this repo treats as substantive — an inherited fact restated as a fresh observation.

**Proposed fix.** Cite both to docs/data-access.md:60-63 and :65-68 with their existing labels, and reserve 'measured today' for the claims that genuinely are new: the 18-file enumeration with no leagues.dat, the world.dat byte offset and teams.dat absence, the header bytes on world.dat, the team_record all-zeros, the 12 distinct rating buckets, the coach-id split, and the roster list_id distribution.

#### [F24] The docs-routing claim is inaccurate for docs/league-rules.md, which is not in the builder's deny set

*adversary:* fit-ac · *confidence:* high · *category:* fit

**Location:** tiered_scope.core ("Documentation corrections routed through /update-docs, never written by the builder (docs/data-access.md is in the data-engineer's deny set)"); the deny set at .claude/agents/data-engineer.md:147-158 lists docs/data-access.md and docs/decisions/ only

**Problem.** The parenthetical gives one file's deny as the reason for a rule covering several corrections, two of which land in docs/league-rules.md — a file the builder may write. The routing conclusion is still right (docs/data-access.md IS denied, and label changes are exactly the docs-delta case the Routing section at :238-251 exists for), but the stated reason does not cover the league-rules.md corrections, so a cold agent following the rule literally may either over-apply it or, noticing the gap, edit league-rules.md directly and bypass the doc gate.

**Proposed fix.** State the two reasons separately: docs/data-access.md changes are denied outright and travel as `## docs-delta` with a proposed epistemic label; docs/league-rules.md changes are permitted to the builder but are routed through /update-docs anyway because §1's values are the verification TARGET of this request and changing them is a judgment call, not a mechanical edit.

#### [SD-27] Citation line numbers drift: league-rules.md's second leagues.dat claim is at :296, not :295

*adversary:* scope-completeness · *confidence:* high · *category:* completeness

**Location:** acceptance_criteria[17] and fit_verdict ("docs/league-rules.md:129 and :295"); actual docs/league-rules.md:129 and :296

**Problem.** Verified by reading the file: `leagues.dat` appears at line 129 ("parser reads `leagues.dat` directly") and line 296 ("Until the parser can open `leagues.dat`"), not 295. Line 295 is the preceding sentence about the probe save. Small, but acceptance criterion 18 is keyed to those numbers and a cold stage-3 agent editing "line 295" edits the wrong sentence. More generally, every line number in the scope will drift the moment any of these files is edited — and this scope proposes editing several of them.

**Proposed fix.** Correct :295 to :296, and change the criterion's anchor from line numbers to the quoted strings, e.g. "the sentences containing 'parser reads leagues.dat directly' and 'Until the parser can open leagues.dat' no longer assert that file exists". A grep on the literal string `leagues.dat` is the durable assertion; a line number is not.

### QUESTION (4)

#### [F25] Open question: does an all-zeros standings report satisfy the FR's 'read the standings', or is it an honest non-goal?

*adversary:* fit-ac · *confidence:* high · *category:* framing

**Location:** FEATURE_REQUEST.md:29-31 ("It can name the 26-man roster and read the standings"); measured: all 259 team_record rows are g/w/l/t = 0 and no games are played in either save

**Problem.** The scope keeps the standings report and makes its acceptance purely structural — which is correct given the measurement. But that leaves a deliverable whose entire information content on delivery day is thirty club names and their division. The scope defends it on two grounds ('the FR asks for it' and 'the team dimension lands anyway'), and both are weak: the FR asked for standings because a GM needs them, not because a table shape is wanted, and the team/division dimension lands in bronze regardless of whether a report renders it. Shipping it risks exactly what the scope warns against in risks[7] — treating its delivery as evidence the pipeline works.

**Proposed fix.** Put the choice explicitly to the operator rather than resolving it silently: (a) ship it as scoped with structural-only acceptance and a rendered note on line one that the league is unsimmed, or (b) move it to gated alongside seeds and byes, land the team/division dimension in bronze anyway, and spend the freed acceptance surface on the roster report's coverage statement — which, given F7, has real content to add. Option (b) also removes an acceptance criterion that cannot distinguish a working parser from a broken one.

#### [F26] Open question: the action-economy ruling is the right gate, but ADR 0016's Notes may already answer it and the scope does not say so

*adversary:* fit-ac · *confidence:* medium · *category:* framing

**Location:** gated_decisions[1]; docs/decisions/0016-gm-reads-reports-not-queries.md:111-115 ("Infrastructure is free; analytical direction is not. The parser, the warehouse, and the machinery that renders a report are engineering... What costs an action is *directing the analytics team to produce a specific analysis*") vs :44 ("Commissioning a report costs an action") and gm/standing-orders.md:35-37

**Problem.** The scope treats this as genuinely open and recommends ruling the reports free. It is more nearly settled than that: ADR 0016's Notes name 'the machinery that renders a report' as free engineering, while its Decision names commissioning a report as an action, and gm/standing-orders.md:45 requires every report entry to carry an `Established: ledger seq <n>`. So a report entry cannot be written without a ledger row, which means the ruling is forced by the artifact format regardless of which way it goes. The scope should say that the format compels a ledger row and that the only open question is `cost` vs `free`, not whether an adjudication happens.

**Proposed fix.** Reframe the gated decision: the ledger row is mandatory (standing-orders format requires a seq), and the operator is ruling only on cost-vs-free. Recommend `free` on the Notes' infrastructure reading, with the reasoning recorded in the row — and note that ledger seq 1 is currently the only entry and was also ruled `free`, so this becomes seq 2 and the precedent chain starts here. That is a smaller, sharper decision than the one the scope currently poses.

#### [SD-28] Open question: what does the catalog publish for a table that failed its grain test?

*adversary:* scope-completeness · *confidence:* medium · *category:* completeness

**Location:** acceptance_criteria[13] (catalog regenerated from information_schema plus the contract declaration); .claude/agents/data-engineer.md:113 ("Layer promotion is gated on tests. A layer that fails its tests must not feed the next."); docs/decisions/0016-gm-reads-reports-not-queries.md:37-44

**Problem.** The catalog is generated from information_schema, so a table that landed but FAILED its uniqueness or coverage test still appears in it, with a row count and a grain sentence, and the GM reads it as an available capability. data-engineer.md:113 forbids a failing layer feeding the next, but the catalog is not obviously 'the next layer' and the scope never rules on it. The GM would then price an action against a table that is known-broken, which is a worse outcome than the gap it was built to expose.

**Proposed fix.** Rule it in the scope: the catalog carries a per-table validation status generated from the last test run, and a table whose grain or coverage assertion failed is listed under the WITHHELD section with its failure reason rather than in the available section. One extra generated field, and it makes the catalog honest about the thing it exists to be honest about.

#### [SD-29] Open question: is the aggregate build size proportionate for the repo's first pipeline slice?

*adversary:* scope-completeness · *confidence:* medium · *category:* scope-creep

**Location:** tiered_scope.core (20 workstreams); acceptance_criteria (20 criteria, ~13 new test modules); tests/ (4 modules today); CLAUDE.md ("fun side project. Size scope for sustained enjoyment, not completeness" and "Vertical slices, not horizontal layers")

**Problem.** Setting aside the individual over-reaches above (SD-04, SD-05, SD-06, SD-15, SD-16), the aggregate deserves a decision of its own. The core tier is 20 workstreams; the acceptance list implies roughly thirteen new test modules against the four that exist today, plus four bronze tables, two renderers, a catalog generator with two output formats, a tracked declaration with three consumers, a ground-truth harness, a snapshot manifest, an ingest-run table and five documentation deltas. Every individual item is defensible and most are well-argued. The question is whether the sum is a vertical slice or a horizontal platform, in a repo whose own guidance is to size for sustained enjoyment and whose author is one person doing this for fun.

**Proposed fix.** Put the aggregate in front of the operator as its own gated decision, with a concrete smaller cut for comparison: config + enumerator + header guard + teams/players/names walks + four hand-written bronze tables + the differential test against the probe + roster.md + a single-format generated catalog + the doc corrections. That cut still delivers the FR's observable signal and every one of the five contracts; SD-04, SD-05, SD-15 and SD-16 are what separates it from the current core. Let the human choose the size rather than discovering it during the build.

