<!-- handoff: v1 -->

## track

feature

## built

**Nothing — investigation only.** No file under `src/`, `tests/` or `docs/` was opened for
writing; analysis lives in `var/spike4/` (gitignored, `common.py` + `80`–`101`). **Those
scripts use absolute offsets deliberately** — investigation, not a parser, and none of it is
proposed for `src/`. Allowlist writes: this file, seven memory entries.

## verified

| Check | Command and actual output |
|---|---|
| Q1 — complete population, and the model on it | `84_team_records.py` → `located 259 of 259 export teams` in the standard **and** the challenge probe (the 26 city-less All-Star sides now matched on `abbr`+`nickname`, so the base is 259, not Phase 5's 233). `85_q1_models.py` → `phase5 six-field 259/259`, `total misses: 0`, and on the discriminating subsets `division_id:140/140  allstar_team:30/30  parent_team_id:199/199  level:259/259  human_id:1/1` — exact on every subset that could have refuted it. Phase 5's miss on the Cubs was a locator artefact, not a model failure. |
| Q1 — export order falsified; neither wide candidate fits; the fit is unique only up to unobservables | same run → `export column order 0/259`, `export order minus division 0/259` (not "worse"; zero). Inserting `division_id` in the export's position scores `119/259` overall and **`0/140`** on teams with a non-zero one; appending `allstar_team` scores `229/259` and **`0/30`** on the All-Star sides. Brute force over orders → **18 distinct orders tie at 259/259** (`orders scoring >=250: 85`), differing only in `human_team` vs `human_id` and in where `prevent_any_moves`/`gender` sit — both `0` on all 259 export rows. |
| Q1 — cross-save, no refit | `88_q1_crosssave.py` → `truth: 259 exact, 0 miss (human club = 6)`; `probe: 259 exact, 0 miss (human club = 4)`. Control with the human club asserted on the wrong team: `257 exact` in both — exactly the two clubs whose flag moved. |
| Q1 — `level`/`parent_team_id` reachable; colours also not in export order | `87_q1_postcolour.py` → first `u32` after the colours `== level` for **259/259**; the next `== parent_team_id` for **199/199 of the teams that have one, control(v+1) 0**. Best 3-permutation of the eight export colour columns: `237/259`, none reaching 259 — a second independent falsification of "export order = disk order". |
| Q2 — the club id is in `human_managers.dat` | `90_q2_humanmgr.py` → offsets where **all three saves hold their own club's `team_id`** are `[231, 235, 239]` at u8, u16 **and** u32, and nowhere else. `91_q2_account.py` → the same intersection at value **+1, −1, +2, +10, +100 is empty every time**. |
| Q2 — cross-file, and the manager is not the discriminator | `90` → `OOTP-AI.lg/teams.dat` has one `Boston/BOS/Red Sox` record, `team_id=4`, `runA=[10948, 9, 203, 206, 1]`; `human_managers.dat` reads 4. `91` → managed and probe agree on the club (4) with **different** managers (name indices `(3102,10596)` vs `(7632,26051)`, DOB 1985-06-12 vs 1977-03-15), while probe and truth share the manager and differ on the club. |
| Q3 — division membership is in `world.dat` | `94`/`95_world_league2.py` → `league → sub_league → division` nesting, each division a `u32` count then an explicit `team_id` array. **6 of 6 MLB divisions match the export exactly in all three saves** once All-Star sides are excluded (e.g. `(203,0,0) disk=[3,4,18,27,29] export=[3,4,18,27,29] MATCH=True`). |
| Q3 — the calendar decodes exactly, and declares its own length | `96_world_calendar.py` → walked **3,058** entries; **3,058 of 3,058 match an `ootp_truth_real.league_events` row exactly on all eight columns (100%)**. Control shifting `league_id` ±3: `1,070/3,058`. Pad constant `000000`; `seq resets: 0`. `97`/`98` → the `u32` immediately before the first entry is **3058 in all three saves**. |
| Q3/Q4 — the schedule region, and landmark uniqueness | `101_schedule2.py` → `head 6,040,015 -> end 6,519,576: body 479,557 = 12961 x 37 bytes EXACT`, identical arithmetic in the challenge probe; 12,961 is the export's exact `games` count. `98_q4_walkability.py` → `\x15\0\0\0Major League Baseball` and `\x02\0\0\0AL\x0f\0\0\0American League` each occur **exactly once** in all three saves, while bare `OPENING DAY` occurs **95 times**. |
| Phase-5 correction; nothing written to the game; tree untouched | `80_inventory.py` → header-tail field 5 is `4294967295` for `players.dat` in all three saves, so it is **not** universally a record count (it still reads 259/259/337 `teams`, 264,095 `names`, 119,847/114,944 `retired`). `uv run pytest -m gamedata tests/test_read_only.py` → `2 passed, 8 deselected in 40.10s`. `git status --porcelain` → the same ten Phase-5 lines as at session start. |

## assumed

- `ootp_truth_real` describes the standard probe only, so every Q1/Q3 claim was **re-run
  against the challenge probe with no refit**; nothing here is fitted to one save.
- The `0xff`-top-byte colour boundary held for all 259 records but a zero-alpha colour would
  break it; `world.dat` offsets here are **evidence, not interface** and no proposal reads one.

## surprised-me

- **`world.dat` is the whole world and the league config sits 62% in.** Order: world settings,
  40 languages, geography (~94k cities — most of the file), leagues, the 12,961-game schedule,
  the 3,058-entry calendar, then ~1.9 MB of high schools and colleges.
- **The calendar and schedule are the cleanest structures in the format** — count-prefixed,
  fixed-shape, self-checking. Far easier than `teams.dat`. And `u32` at file offset 169 is
  **1234 in every record file of every save** — 14 files × 3.
- Phase 5's "232 of 233" was pessimistic twice: an incomplete population *and* my own miss.

## could-not-do

- **Could not place `division_id` or `allstar_team` in `teams.dat`.** A positional sweep over
  400 offsets from head and tail of every record block, at u8/u16/u32, returned zero exhaustive
  hits; "present anywhere" is worthless at values 0–5 since the +1 control fires equally.
  Division membership is in `world.dat`; `allstar_team`'s home is unknown.
- **Could not separate `human_team` from `human_id`,** place `prevent_any_moves`/`gender`, or
  tell the three `human_managers.dat` club slots apart — those columns are constant zero or
  co-varying in the only oracle. A save with two humans settles all of them at once.
- **Did not attempt a from-the-top `world.dat` walk** (it means modelling the ~94,126-record
  city array first), and **could not decode `teams.dat` past `parent_team_id`** — drop-zeros on
  MLB clubs, literal-zeros on All-Star sides. No destructive git needed; nothing written
  outside the allowlist plus `var/spike4/`.

## docs-delta

For `/update-docs` to route into `docs/data-access.md` §4, with proposed labels.

- **`measured`, upgrades §4** — a `teams.dat` record's pre-colour integer run is `[city_id,
  park_id, league_id, sub_league_id, nation_id, human]`, zeros omitted, exact on **259 of 259
  records in two independent saves**. Export column order is **not** disk order (0 of 259), and
  `division_id`/`allstar_team` are **not** in the run (0 of 140, 0 of 30 on their non-zero
  subsets). Three `u32` ARGB colours follow, also not in export order (best 237 of 259); then
  `level` (259 of 259) and `parent_team_id` when non-zero (199 of 199, control 0) — landable.
  **`unconfirmed`:** the last slot is `human_team` or `human_id`, and `prevent_any_moves`/
  `gender` cannot be placed at all — 18 orders fit equally well.
- **`measured`, corrects the Phase-5 delta** — header-tail field 5 is **not** universally a
  record count: `players.dat` declares `0xFFFFFFFF` in all three saves (it is a count for
  `teams`, `names`, `parks`, `coaches`, `retired`). `u32` at offset 169 is `1234` everywhere.
- **`measured`** — `human_managers.dat` carries the human club's `team_id` at three consecutive
  `u32`s; they are the only slots tracking the club across all three saves, and the same
  intersection at ±1/+2/+10/+100 is empty. Which of `team_id`/`last_team_id`/`organization_id`
  each one is: `inferred`.
- **`measured`** — `world.dat` is one nested structure (`record_count = 1`) holding, in order:
  world settings, languages, geography, leagues, schedule, calendar, schools. Division
  membership lives here as `league → sub_league → division → count-prefixed array of team_id`,
  matching the export exactly on all six MLB divisions in all three saves. **All-Star sides
  appear in no division array**, so their export `sub_league_id`/`division_id` of `0` is
  **structural absence rendered as zero** — a live instance of the trap the scope names.
- **`measured`** — the calendar is a `u32`-count-prefixed array (3,058) of `u32 seq, u32
  league_id, u16 type, u8 day, u8 month, u16 year, 3 pad, u32 len + name, u8 event_over,
  u8 deleted, u8 needs_human_action, u16 real_sim_date`; all 3,058 match
  `ootp_truth_real.league_events` exactly on all eight columns, and all three saves share a
  byte-identical calendar. **`inferred`:** the ~480 KB string-free region before it is the
  schedule — count-prefixed at 12,961 and **exactly 37 bytes per record**.

## still-open

**Q4 answered.** A from-the-top `world.dat` walk is sound but is its own phase — the league
region is 62% in, behind the ~94k-record city array. **A composite landmark is sound here, and
more defensible than on `coaches.dat`, because both target regions declare their own length.**
The anchors are measured unique in all three saves; after entering, the walk reads a `u32`
count, must consume exactly that many records, and must land on the next region's boundary, so
a wrong shape desynchronises and raises — and no constant offset is involved. **But strict is
unreachable, and `diagnostic` means something weaker here than for `teams.dat`**: such a walk
never reads ~7.5 MB of 8.9 MB. **The claim I can defend is region-accounted — zero residual
within each walked region, the declared count matched exactly, un-walked prefix/suffix byte
counts recorded on the ingest row.** A third tier value or a widened `diagnostic` is a
pre-registration change and so the main thread's call.

**Recommended phase split.** *5a — finish `teams.dat`:* land the six-field run plus `level` and
`parent_team_id`; land the last slot as one `human` flag with the ambiguity named in the field
map; withhold `prevent_any_moves`/`gender`; **drop `division_id` and `allstar_team` from
`TeamRecord`** — not in this file. Tier stays `diagnostic`. *5b — `world.dat`, divisions and
calendar only:* composite-landmark entry, the division nest, the calendar. Grains `(save_id,
snapshot_date, league_id, sub_league_id, division_id)` and `(save_id, snapshot_date, league_id,
start_date, type, name)` — the second needs checking, since `league_events` carries same-day
duplicates separated only by `deleted`. Membership lands as `bronze_division_team`;
**`teams.division_id` is derived in silver from that array, never parsed.** *Deferred:* the
schedule (bounded and shaped, but nothing consumes it until the league sims), geography and
schools, the `teams.dat` body, a from-the-top walk, `allstar_team` as a parsed field.
*Pre-register one cheap test:* the club named by `human_managers.dat` equals the club
`teams.dat` flags human. **Ambiguity resolved small** (Escalation case 3): I read "what does the
league record look like" as its framing and nesting, not its 163 scalars, so the ~1,200-byte
scalar block before the sub-league count is unmapped — the §1 diff the scope already gated.
