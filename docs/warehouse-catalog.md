# Warehouse catalog — what is landed, and what is deliberately not

> **Generated. Do not edit by hand.** `uv run python -m ootp_ai.catalog` rewrites this file from `src/ootp_ai/contracts/tables.toml` and `src/ootp_ai/contracts/field_map.toml`. `tests/test_catalog.py` rebuilds it during the test run and refuses any byte that differs, so a hand edit here is red before it is stale.

This is the **structural half**: table names, grains, keys, coverage populations, source files, epistemic labels, the withheld groups and where the rendered reports land. It is derived schema knowledge, which ADR 0006 tracks deliberately, so it survives a fresh clone with no game, no save and no database.

**No figure on this page is computed from a landing.** Row counts, snapshot dates and freshness generate into the git-ignored output root beside the reports — see *Where the reports are*, below. Read that copy to learn what a particular snapshot holds; read this one to learn what the warehouse is *shaped* like.

**The coverage notes below do quote numbers, and those numbers are historical.** They are measured records copied from `src/ootp_ai/contracts/tables.toml`, describing the save they were measured on — usually the probe. They are *not* this warehouse's current contents and will disagree with the generated copy whenever the league has moved. Where the two differ, the generated copy is the one that counted.

## The tables

8 tables are declared, carrying 96 columns between them.

Of 89 declared fields, **55 can reach a page** — bound to a declared column *and* released by the serving gate. 11 are withheld by the gate, and 23 are read by a walker but claimed by no column, so nothing lands them and nothing can print them. All three groups are accounted for under *What is withheld* below.

### `bronze_division_team`

- **Grain** — one row per club per division per save per snapshot
- **Key** — `save_id`, `sim_date`, `ingest_seq`, `league_id`, `sub_league_id`, `division_id`, `team_id`
- **Source** — `world.dat`
- **Walker** — `ootp_ai.parser.world.read_world`
- **Columns** — 7 of 7 columns reach a page; 3 are provenance (ours, not the game's).
- **Epistemic labels** — verified 4.
- **Coverage (as declared)** — MLB's SIX divisions only — the thirty clubs those arrays name. The other fourteen leagues each sit behind their own unmapped scalar block in `world.dat` and are not reached; thirty rows against a club count of 259 on the probes and 337 in the managed league is the documented reach of the walk, not a parse fault. The four All-Star sides appear in no division array at all: structurally absent, and absence here is a MISSING ROW — never division zero, because `division_id` counts from 0 within its sub-league and East really is division 0.
- **Note** — `teams.division_id` is DERIVED from this array in silver and never parsed — `teams.dat` provably does not carry it (0 of 140 on the clubs with a non-zero one), so a division stamped onto a team record could only have come from a join, and bronze does not join. This table is therefore the only division source in the warehouse.

### `bronze_field_label`

- **Grain** — one row per landed column per save per snapshot
- **Key** — `save_id`, `sim_date`, `ingest_seq`, `table_name`, `column_name`
- **Source** — `contracts/field_map.toml`
- **Walker** — `ootp_ai.contracts.loader.load_contracts`
- **Columns** — 10 of 10 columns reach a page; 10 are provenance (ours, not the game's).
- **Epistemic labels** — none: every column is provenance rather than a belief about a game fact.
- **Coverage (as declared)** — Every column of every table this ingest wrote — 96 of them, all eight tables including this one and `ingest_run` — with the epistemic label the field map carried ON THE DAY IT LANDED. Not a game fact: a record of what we believed about one. `ingest_run` is in rather than out because its `human_team_id` resolves from `human_managers.dat` and carries a real label, and a rule that skipped the table would drop that belief on a technicality about the table's name.
- **Note** — This table exists so a future data incident can ask *what did we believe about this field the day it landed?* as a query rather than as archaeology through the git history of `docs/data-access.md`. It is the one table whose source is a tracked file rather than a save.

### `bronze_league_event`

- **Grain** — one row per calendar event per save per snapshot
- **Key** — `save_id`, `sim_date`, `ingest_seq`, `seq`
- **Source** — `world.dat`
- **Walker** — `ootp_ai.parser.world.read_calendar`
- **Columns** — 11 of 12 columns reach a page; 3 are provenance (ours, not the game's).
- **Epistemic labels** — measured 1, unconfirmed 1, verified 7. Weakest: `unconfirmed` — which is what the table as a whole is worth, however many better-evidenced columns sit beside it.
- **Coverage (as declared)** — All 3,058 entries, including the 2,492 (probe) / 2,259 (managed league) carrying `deleted`. Every row lands and filtering belongs to the report: a walk that dropped the deleted ones would return 566 rows and look perfectly consistent.
- **Note** — Keyed on `seq` and not on the readable alternative. `(league_id, start_date, event_type, name)` collapses 3,058 rows to 2,600 — 458 events lost with nothing raised. `seq` is the file's own field and the export does not expose it, which is precisely why the key had to be settled from the bytes rather than from the answer key.
- **Not served** —
  - `real_sim_date` is **uncertain**: category `structural`, label `unconfirmed` — the value is landed and its meaning is not established, so it renders only with an uncertainty banner and never as a bare value.

### `bronze_name`

- **Grain** — one row per name-table entry per save per snapshot
- **Key** — `save_id`, `sim_date`, `ingest_seq`, `name_space`, `name_index`
- **Source** — `names.dat`
- **Walker** — `ootp_ai.parser.names.read_names`
- **Columns** — 6 of 7 columns reach a page; 4 are provenance (ours, not the game's).
- **Epistemic labels** — unconfirmed 1, verified 2. Weakest: `unconfirmed` — which is what the table as a whole is worth, however many better-evidenced columns sit beside it.
- **Coverage (as declared)** — All 264,095 entries the file declares and the walk frames, per save per snapshot — measured on landing, roughly seven times the combined row count of the other bronze tables on a probe and six times in the managed league. The volume is knowingly accepted (field_map.toml records the decision and its named fallback); uniform bronze grain is worth more than the disk.
- **Note** — `name_space` is the pre-registered discriminator and takes the single literal value 'all'. It stays in the key even though ONE space was measured: the key is correct under both outcomes and costs one column, while the wrong key would collide two spaces silently. The variable-length usage pairs are consumed for byte accounting and land nowhere — a repeating group with no confirmed meaning is not a column.
- **Not served** —
  - `name_category` is **withheld**: category `rating-true`, label `unconfirmed` — an unclassified field is recorded as a true rating (ADR 0012's corollary), and a true rating never reaches a page.

### `bronze_player`

- **Grain** — one row per player per save per snapshot
- **Key** — `save_id`, `sim_date`, `ingest_seq`, `player_id`
- **Source** — `players.dat`
- **Walker** — `ootp_ai.parser.players.read_players`
- **Columns** — 24 of 24 columns reach a page; 3 are provenance (ours, not the game's).
- **Epistemic labels** — verified 21.
- **Coverage (as declared)** — Every record the walk frames — 18,077 in each test save, of which the export's `retired = 0` population is 18,072, and 22,046 in the managed league, which carries 337 clubs rather than 259. A deliberately minimal field set: the biographical head, the club assignment, handedness, and the Lahman id.

  Absences come in two kinds and the difference matters. **Ratings, position and role** carry a [[withheld]] entry in field_map.toml arguing why each is out. **Six crossed-but-unexposed fields** — second_nation_id, the two language ids, the nickname index, loan_league_id and historical_team_id — are ordinary [[field]] entries the walker verified and chose not to surface, because every exposed field is a field a report may print and none of the six has a consumer.
- **Note** — The name INDICES land, not the names. A display name exists only once a `NameTable` built from the SAME save resolves them (`bronze_name`), which is why the two tables are useless apart.

  **THE ROSTER REPORT CANNOT SHOW POSITION FROM THIS TABLE**, and that is worth saying here rather than discovering in Phase 10. PROJECT_SCOPE Goal 1 asks for a roster carrying position, age, bats/throws and uniform number; three of the four are columns above and `position` is not, because it is not exactly readable yet (`parser/players.py`: the role byte is exact only within fixed-shape groups whose shape rule is underived, and the export's closer role is not stored in it at all). Landing it at 97% would be the failure mode this project treats as worse than an error. The [[withheld]] entry records how far the decode got so the next attempt starts there.

### `bronze_team`

- **Grain** — one row per team per save per snapshot
- **Key** — `save_id`, `sim_date`, `ingest_seq`, `team_id`
- **Source** — `teams.dat`
- **Walker** — `ootp_ai.parser.teams.read_teams`
- **Columns** — 21 of 21 columns reach a page; 3 are provenance (ours, not the game's).
- **Epistemic labels** — measured 3, verified 15. Weakest: `measured` — which is what the table as a whole is worth, however many better-evidenced columns sit beside it.
- **Coverage (as declared)** — Every record the walk frames — 259 in each probe save, 337 in the managed league — with no filtering whatever. Bronze lands all of it including every minor-league club; the organisation filter lives in the report layer, never here.
- **Note** — `parent_team_id` is 0 for the 34 top-level clubs and that zero is a VALUE, not structural absence — `parser/teams.py` argues the distinction explicitly, and it is the one place in this schema where a zero must not be read as a missing field.

### `bronze_team_roster`

- **Grain** — one row per player per team per roster list per save per snapshot
- **Key** — `save_id`, `sim_date`, `ingest_seq`, `team_id`, `player_id`, `list_id`
- **Source** — `teams.dat`, `players.dat`
- **Walker** — `ootp_ai.parser.rosters.read_rosters`
- **Columns** — 6 of 6 columns reach a page; 3 are provenance (ours, not the game's).
- **Epistemic labels** — verified 3.
- **Coverage (as declared)** — 15,672 rows on the standard-mode probe, reproducing `ootp_truth_real.team_roster` exactly; measured on landing, 15,721 on the Challenge-mode twin and 20,016 in the managed league, whose 337 clubs carry more rosters. Covers 7,370 DISTINCT players on the probe, not 18,072: roughly 10,700 active players — free agents, draft-eligible, international, unassigned — carry no roster row at all, and that absence is the data, not a gap.
- **Note** — The key is the whole point of the table. `(sim_date, player_id)` would be wrong: 935 players hold a list-3 row at their organisation AND a row at another club in the same snapshot, so a player-grained key silently collapses them.

  **176 players per save are assigned to a club and hold no list membership**, and they are absent from this table by design — a different absence from the ~10,700 above, who are assigned to nobody. The export marks the population with a negative `league_id`; `parser/rosters.py` surfaces it as `RostersFile.unrostered` and the loader drops it, because a roster-LIST table has no row to give a player who is on no list. **A query asking "who is in Boston's organisation" from this table alone misses them**; club assignment lives in `bronze_player.team_id` / `organization_id`.

### `ingest_run`

- **Grain** — one row per ingest attempt
- **Key** — `save_id`, `sim_date`, `ingest_seq`
- **Source** — `snapshot manifest`, `human_managers.dat`
- **Walker** — `ootp_ai.warehouse.ingest_run`
- **Columns** — 9 of 9 columns reach a page; 8 are provenance (ours, not the game's).
- **Epistemic labels** — inferred 1.
- **Coverage (as declared)** — One row per landing. The triple is IMMUTABLE once written: re-loading an already-landed triple refuses loudly, while a new snapshot of an already-ingested `sim_date` allocates the next `ingest_seq` and lands a fresh row set alongside the previous one. Nothing is ever overwritten, which is what makes AC10's byte-identity clause hold trivially.
- **Note** — The repeating groups land as JSON rather than as a child table: the phase declares eight tables and a ninth would be one the plan never sequenced, while flattening them into fixed columns would bake today's file list into a schema that changes whenever SNAPSHOT_FILES does. Flagged for the operator as a judgment call, not slipped in. The wall-clock ingestion timestamp is an ATTRIBUTE and never part of the key.

  `residual_bytes` is JSON for the same reason and it was a scalar BIGINT until review caught it: `IngestRun.residual_bytes` is a `Mapping[str, int]`, and the accounting TIER differs per file by design — strict zero-residual for names.dat ALONE, diagnostic for teams.dat and players.dat, region-accounted for world.dat. (Corrected in Phase 8b: this said "strict for teams.dat and names.dat", while `parser/teams.py` declares `diagnostic` and the landed residual is 2,274 managed / 1,137 probe. Two diagnostic files make the argument stronger — a sum would never be zero, so nobody could tell which file moved.) Summing across files makes a strict-tier FAILURE arithmetically indistinguishable from an expected diagnostic residual, and the incident question *which walker left bytes unaccounted for* stops being answerable from the warehouse.

  `parse_seconds` is NULLABLE, and that is the structural-absence rule rather than laziness: `IngestRun.parse_seconds` is `float | None` and the plan fills it in Phase 9, AFTER 8b writes the first rows. NOT NULL would leave 8b writing 0.000, which is indistinguishable from an instantaneous parse.

  There is NO `game_version` column. One was declared here and review found no such attribute anywhere in the repo — the header version is per file and already lives inside `source_files`. A column with nothing behind it is a NULL waiting for an argument.

## What is withheld, and why

The half a list of landed tables cannot give you. A gap named here is a gap the GM can price an action against; a gap discovered by hitting it is a wasted action and a wrong belief in between.

### Groups never landed

| Group | Source | ADR | Why |
|---|---|---|---|
| position, role | `players.dat` | — | Not refused — not yet EXACTLY readable, and landed at less than exact they would be the 97-99% failure this project cannot afford. *(…)* |
| ratings | `players.dat` | ADR 0012 | ADR 0012, permanent. Two lossy transforms sit between a stored rating and any display — scale conversion and scout filtering — so matching a displayed value to a byte identifies the wrong field with no error surfaced. This slice lands no ratings whatever the Phase 2 spike returned. *(…)* |

The full argument for each is in `src/ootp_ai/contracts/field_map.toml` under `[[withheld]]`. What is reproduced above stops at the first sentence naming a column this catalog may not print — the declaration is a working note and names them freely, and a catalog that quoted it whole would publish exactly the names the serving gate exists to keep off a page.

### Rating-category fields — counted, never named

10 declared fields carry a rating category and are withheld. **This catalog does not print their names**, and that is structural rather than editorial: an **unclassified** field is recorded as a true rating rather than as *unknown* — ADR 0012's withhold-by-default posture, in which *probably fine* is not a classification — so naming every withheld field is exactly what would publish the first genuinely decoded true rating. The declaration holds the names; `src/ootp_ai/contracts/field_map.toml` is where an engineer reads them.

| Source | Withheld fields |
|---|---:|
| `names.dat` | 2 |
| `players.dat` | 8 |

### Other fields the serving gate does not release

1 declared field whose category is not a rating. These are named: the value is landed and only its *meaning* is unsettled, so knowing which one it is costs nothing and tells the GM where the page is guessing.

| Field | Source | Decision | Category | Label |
|---|---|---|---|---|
| `calendar_real_sim_date` | `world.dat` | uncertain | `structural` | `unconfirmed` |

### Read, but landed by nothing

23 declared fields that the serving gate would release and **no declared column claims**. The walker reads them and proves them; nothing lands them, so nothing can print them. They are here because a field somebody verified and chose not to surface is a gap the GM can price — and because counting them as served is precisely the mistake this section exists to stop repeating.

| Field | Source | Category | Label |
|---|---|---|---|
| `calendar_flag_typing` | `world.dat` | `structural` | `measured` |
| `content_digest` | `players.dat` | `structural` | `measured` |
| `historical_team_id` | `players.dat` | `identity` | `verified` |
| `language_ids0` | `players.dat` | `identity` | `verified` |
| `language_ids1` | `players.dat` | `identity` | `verified` |
| `loan_league_id` | `players.dat` | `identity` | `verified` |
| `name_table_save_ownership` | `names.dat` | `structural` | `measured` |
| `names_declared_record_count` | `names.dat` | `structural` | `measured` |
| `nickname_index` | `players.dat` | `identity` | `verified` |
| `roster_status_active` | `players.dat` | `structural` | `verified` |
| `roster_status_injured` | `players.dat` | `structural` | `verified` |
| `roster_status_secondary` | `players.dat` | `structural` | `verified` |
| `roster_status_sixty_day` | `players.dat` | `structural` | `verified` |
| `second_nation_id` | `players.dat` | `identity` | `verified` |
| `tail_mask` | `players.dat` | `structural` | `measured` |
| `team_membership_array` | `teams.dat` | `structural` | `measured` |
| `team_organisation_links` | `teams.dat` | `structural` | `measured` |
| `team_pre_colour_run` | `teams.dat` | `structural` | `measured` |
| `team_string_signature` | `teams.dat` | `structural` | `measured` |
| `unrostered_assignment_marker` | `players.dat` | `structural` | `measured` |
| `world_declared_record_count` | `world.dat` | `structural` | `measured` |
| `world_landmark_entry` | `world.dat` | `structural` | `measured` |
| `world_league_head` | `world.dat` | `structural` | `measured` |

## Where the reports are

Rendered reports are **not** in this repository and never will be: they name real players, and this repo is public (ADR 0006). They resolve under a git-ignored root named by an `.env` key, partitioned by the snapshot triple they were rendered from — so a later date or a later sequence writes a new directory beside the old one rather than over it, and the exact bytes the GM read are still on disk when a decision citing them is checked months later.

| Report | Resolves under | Path within it | Rendered by |
|---|---|---|---|
| organisation roster | `$OOTP_OUTPUT_ROOT` | `<save_id>/<sim_date>/<ingest_seq>/roster.md` | `uv run python -m ootp_ai.reports render` |
| warehouse catalog | `$OOTP_OUTPUT_ROOT` | `<save_id>/<sim_date>/<ingest_seq>/warehouse-catalog.md` | `uv run python -m ootp_ai.catalog` |

## The spawn contract

What the umpire says when handing the GM its reports. The `gm` subagent holds exactly `Read` and `Glob` and cannot query anything (ADR 0016), so its context is the whole delivery surface — an attachment nobody framed is an attachment the GM cannot date, attribute or trust. Fill in the blanks; add nothing analytical.

```text
You are the General Manager of <club>, in league <league>.

Attached for this invocation:
  - <report name> — rendered from save <save_id>, sim date <YYYY-MM-DD>,
    ingest_seq <n>.
  - <report name> — same landing.

The reports describe that landing and no other. Anything that has happened in
the league since is not in them.

Period: <period>. Actions available: <n of m>. Actions already spent: <list>.

Return your handoff in the standard sections.
```

**Every blank is a fact the GM cannot otherwise obtain.** The sim date and `ingest_seq` are on line one of each report, but the *period* and the *action budget* are not in any report and the GM has no way to read them — an invocation that omits them is asking for a plan against an unknown budget.
