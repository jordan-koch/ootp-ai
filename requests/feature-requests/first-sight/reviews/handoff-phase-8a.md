# Handoff — first-sight Phase 8a (contracts, DDL, and the offline grain guards)

**Main-thread build**, so no data-engineer return contract is owed; this is the
convention-following handoff every prior phase left, written because Phase 8b needs three
of its decisions and would otherwise rediscover them mid-build.

## What landed

`src/ootp_ai/contracts/` gained `__init__.py`, `tables.toml`, `loader.py`, `policy.py`;
`src/ootp_ai/warehouse/` gained `ddl.py`; `field_map.toml` was backfilled from 55 to 87
entries. Three new offline test modules, 89 tests. **No loader, no database contact, no
schema object exists yet** — `git ls-files src/ootp_ai/warehouse` still lists only
`__init__.py` and `sql.py`.

Eight declared tables: `bronze_team`, `bronze_player`, `bronze_team_roster`, `bronze_name`,
`bronze_division_team`, `bronze_league_event`, `bronze_field_label`, `ingest_run`.

## The mechanism, in one paragraph

`tables.toml` states each grain as a sentence — *"one row per player per team per roster
list per save per snapshot"*. `loader.py` splits it on `" per "`, resolves each dimension
through the declared `[meta.dimensions]` map, and requires the union of those columns to
equal the declared key **exactly**. So prose-vs-key drift fails at *load* time, in every
consumer at once, rather than failing to be noticed. `ddl.py` then emits `CREATE TABLE`
from the same declaration, and `tests/test_grain_contracts.py` asserts the emitted key
equals the declared one — the schema MySQL will hold is the schema the sentence describes.

## Decisions 8b inherits — these are the reason this file exists

1. **`ingest_run`'s repeating groups land as JSON**, not as a child table: `source_files`,
   `table_row_counts` and `residual_bytes`. A ninth table is one the plan never sequenced,
   and fixed columns would bake today's file list into the schema. `residual_bytes` is
   **per-file and must stay per-file** — the accounting tiers differ by file (strict for
   `teams.dat`/`names.dat`, diagnostic for `players.dat`, region-accounted for `world.dat`),
   so a summed total makes a strict-tier failure indistinguishable from an expected
   diagnostic residual.
2. **`parse_seconds` is NULLABLE and NULL means not-measured**, not zero. Phase 9 fills it,
   which is *after* 8b writes the first rows.
3. **There is no `game_version` column.** One was declared and had no attribute behind it;
   the per-file header version already lives inside `source_files`.
4. **Six `bronze_player` id columns are `i32`, not `u32`** — the walker signs those reads
   because the export writes `league_id` negative on 176 real records. The loader now
   refuses the unsigned spelling, so 8b cannot reintroduce it quietly.
5. **`bronze_name.name_space` takes the literal `"all"`.** One index space was measured; the
   discriminator stays because the key is correct under both outcomes and costs one column.

## Still open, and named rather than left to be found

- **The `rosters.py` → `players.py` seam.** Phase 8b step 7 expects this call "made in
  writing". It is **not made here**: `rosters.py` still imports thirteen private names from
  `players.py`, and 8a had no loader importing from both, so nothing forced the question.
  8b is the first module that does.
- **CF22 — nothing ties a declared column set to the parser record it claims to be 1:1
  with.** The largest item the acceptance panel carried. 8b materialises both sides and is
  the natural place to close it.
- **The emitted DDL has never been executed** (CF26). 8b runs it first; a syntax defect
  surfaces there.
- **`bronze_division_team`'s key admits a club in two divisions** (CF8), which its own
  coverage denies. Phase 8b step 8's `team_id`-uniqueness assertion is where that lands.
- **Position is not a `bronze_player` column** and cannot be until a later slice decodes it.
  PROJECT_SCOPE Goal 1's roster report asks for it; three of its four fields exist and this
  one does not. Recorded in the table's note so Phase 10 does not discover it.

## Coverage numbers to carry forward

| Table | Rows per snapshot | Note |
|---|---|---|
| `bronze_team` | 259 (probe) / 337 (managed) | every record, no filtering |
| `bronze_player` | 18,077 framed; 18,072 `retired = 0` | minimal field set |
| `bronze_team_roster` | 15,672 (probe) | 7,370 distinct players, not 18,072 |
| `bronze_name` | 264,095 | ~14× the rest combined, knowingly accepted |
| `bronze_division_team` | 30 | MLB's six divisions only — not a parse fault |
| `bronze_league_event` | 3,058 | including the 2,492 / 2,259 marked `deleted` |

## Disposition census

**76 renderable / 10 withheld / 1 uncertain** across 87 fields. The single uncertain field
is `calendar_real_sim_date`, whose `verified` label the acceptance panel refuted: both it
and the export are zero on every row, so the row-for-row match proved nothing about it.
The ten withheld are the crossed-but-unclassified `players.dat` spans plus the two
unread `names.dat` regions — filed `rating-true` by the withhold-by-default rule.

## The two acceptance mutations, and where they live now

Both were run physically against the tracked files and reverted, and **both are permanent
tests** rather than one-off manual steps:

- roster key → `(sim_date, player_id)`: refused, naming the table, its grain sentence and
  the four columns the prose implies that the key had lost.
- `epistemic = "verifed"` on `team_park_id`: refused, naming the field *and* the value.
