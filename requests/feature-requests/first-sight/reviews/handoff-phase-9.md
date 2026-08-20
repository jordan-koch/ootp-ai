# Handoff — first-sight Phase 9 (the differential harness, and the recorded extraction cost)

**Main-thread build**, so no data-engineer return contract is owed. Written because the
phase settled a clause the plan explicitly deferred to it, corrected two wrong statements in
a tracked declaration, and leaves Phase 10 four decisions it would otherwise rediscover.

## The headline: the parser is exact, and now says so on every run

`validate/export_diff.py` compares the **landed warehouse** against `ootp_truth_real` — not
the parser's Python objects, so the loader is under test too — and the run is clean.

**Reproduce it with `uv run pytest -m gamedata tests/test_parser_vs_export.py`.** The block
below is `DiffReport.describe()`, captured from a real run; there is no `__main__` for the
differential, by the same call the operator made in Phase 8b — Phase 10 owns the CLI and a
second entry-point pattern landing first would pre-empt it.

```
provenance: Test-Save-Standard-Mode @ 2024-03-18, human club 6
parse_seconds: 3.097

bronze_team: 259 rows compared (landed 259, export 259)
    city vs name: 259 compared, 26 allowed — ok
    abbr vs abbr: 259 compared — ok
    nickname vs nickname: 259 compared — ok
    logo_filename vs logo_file_name: 259 compared — ok
    city_id vs city_id: 259 compared — ok
    park_id vs park_id: 259 compared — ok
    league_id vs league_id: 259 compared — ok
    sub_league_id vs sub_league_id: 259 compared — ok
    nation_id vs nation_id: 259 compared — ok
    human_team vs human_team: 259 compared — ok
    level vs level: 259 compared — ok
    parent_team_id vs parent_team_id: 259 compared — ok
    historical_id vs historical_id: 259 compared, 229 allowed — ok
    color_1 vs background_color_id: 259 compared — ok
    color_3 vs text_color_id: 259 compared — ok
bronze_player: 18072 rows compared (landed 18077, export 18072)
    [18 columns, 18072 compared each — all ok]
bronze_team_roster: 15672 rows compared (landed 15672, export 15672)
    team_id / player_id / list_id: 15672 compared each — ok
bronze_league_event: 3058 rows compared (landed 3058, export 3058)
    [8 columns, 3058 compared each — all ok]
bronze_division_team: 30 rows compared (landed 30, export 34, 4 allowed by an absence rule)
    league_id / sub_league_id / division_id / team_id: 30 compared each — ok
```

**Thirty-three keyed columns plus fifteen row-spec columns, zero unexplained differences.**
The `allowed` counts are the absence rules firing at exactly their declared populations.

## The clause the plan deferred to this phase, settled

Recorded in full in the plan's Phase 9 step 3. In short:

**"15 leagues" is struck, not restated — and the obvious restatement would have been wrong.**
No walker lands a league dimension, so nothing in the warehouse answers for the export's 15
`leagues` rows. `COUNT(DISTINCT league_id)` over `bronze_team` is **17**, because clubs
reference two league ids (215, 219) that have no row in `leagues`. Writing "15" against that
column would have made a *correct* parse fail. What replaces it is the claim the landed data
supports and the harness now enforces: `bronze_team.league_id` matches the export on 259 of
259 clubs.

**The 15,672 `team_roster` figure was checked and is right.** `information_schema.TABLE_ROWS`
estimates it at 13,552; that is an InnoDB estimate, not a count. Both `world.dat` tables are
in the differential, as the flag directed.

## Two statements in `field_map.toml` were wrong, and the harness found them

Both were caught by `test_export_diff.py`'s cross-check between the harness's declared
comparison and the field map's validator token — the grain-versus-key pattern applied to
validation labels. Neither was a labelling nicety:

1. **`team_historical_id` said "Not carried by the export's `teams` table".** It is carried.
   All 30 non-empty values match exactly; the other 229 are NULL here against `''` there.
   The field was `measured` / `none` and is now `verified` / `export-exact-modulo-absence`.
2. **`team_parent_id` carried `mutual-link-agreement`**, which names how the parse *derives*
   the value rather than the strongest evidence that it is right. The derivation still
   matters — it is the only check available on a Challenge-mode save — but the token now
   names the export comparison that runs every time. The note keeps both.

A third was an over-claim rather than an error: **`team_city` carried
`export-exact-all-rows`** while its own note said 26 rows are "asserted separately by count
rather than compared". Now `export-exact-modulo-absence`, a token added this phase for
exactly this shape.

## The colour slots split, and one of them is still unknown

`team_colors` was one field entry covering three columns, labelled `measured`, with the note
*"WHICH of the three is primary, secondary or trim is `unconfirmed`"*. Every one of the
export's eight colour columns was scored against every slot over all 259 clubs:

| slot | best export match | score |
|---|---|---|
| `color_1` | `background_color_id` | **259 / 259** |
| `color_2` | `ballcaps_visor_color_id` | 237 / 259 |
| `color_3` | `text_color_id` | **259 / 259** |

So the entry is split three ways. `color_1` and `color_3` are `verified` / export-exact;
**`color_2` stays `measured` and is deliberately absent from the differential.** Comparing it
against a 237/259 candidate would ship a 22-row failure as the harness's normal state, and an
absence rule would be an allowlist standing in for an unfinished decode. `test_export_diff.py`
pins that absence as a decision so it is not read as an oversight.

The alpha byte is `0xff` on every slot of every record, so the comparison checks alpha rather
than masking it — a walk reading one byte early would otherwise compare equal on any club
whose colour survived the shift.

## The strongest single result: 176 players, two independent readings

The export marks *assigned to a club but on no roster list* by **negating `league_id`**. The
save does not: it stores the magnitude, and records the same fact in a roster-status byte
that `parser/rosters.py` reads out of an entirely different file region and surfaces as
`RostersFile.unrostered`.

Measured: the two name the **same 176 players** — not the same count, the same set — and none
of them appears in the export's own `team_roster`. That is what licenses the `magnitude`
comparison mode, so the one tolerance in the harness rests on evidence rather than on
convenience, and it is asserted on every run rather than recorded here and forgotten.

## Three absence rules, each bounded by an exact population

The plan's step 4 named `rules_active_roster_limit` and the service-time columns. **Those
columns live on the export's `leagues` table, which no walker lands**, so they are outside
the landed field set entirely and the allowlist does not mention them — inventing entries for
them would be an allowlist describing a comparison that does not happen. What is there:

| table.column | rows | why a correct parse disagrees |
|---|---|---|
| `bronze_team.city` | **26** | the save carries no city string for a generic all-star side; the export substitutes the nickname |
| `bronze_team.historical_id` | **229** | a club with no real-world counterpart has no id, and a CSV-shaped export has no NULL |
| `bronze_division_team` (whole rows) | **4** | an all-star side is in no division; the export writes division 0, which is a real division for every other club |

**The population is the point.** A rule that may suppress any number of rows is a mute
button. Each of these fires on exactly as many rows as it declares, in *either* direction —
too few is as informative as too many, because it means the export moved under a harness that
still claims to allow for it. And the city rule is tied to the export's nickname rather than
to "NULL is fine", so a club that genuinely lost its city is still a failure.

## The guard, seen to fail — §4.4's Phase 9 row

`parser/players.py` was edited to add 1 to `uniform_number` on every thousandth player id,
the differential re-run, and the edit reverted. Output:

```
1 fields disagree with the export:
  bronze_player.uniform_number (export uniform_number): 22 of 18072 rows disagree —
  player_id=115000: landed 4 vs export 3; player_id=132000: landed 1 vs export 0; ...
```

It named **the field**, the count, and the individual rows with both values, and carried no
percentage — while every other column still reported its compared count, so a reader can see
the rest of the comparison actually ran. Reverted; `git diff` on `parser/players.py` is
empty and the 14 tests are green again.

The same demonstration exists as a permanent test at two levels — injected into the pure
comparison layer offline, and injected into the real landed rows under `-m gamedata` — so it
runs on every invocation rather than once, by hand, in a phase nobody will repeat.

## A live incident, pinned rather than described

`test_the_export_sim_date_needs_a_quoted_identifier_to_be_read_at_all` measures the collision
`warehouse/sql.py` exists to prevent, on this export, today:

```
SELECT current_date   FROM leagues  -> 2026-08-19   (the CURRENT_DATE function)
SELECT `current_date` FROM leagues  -> 2024-03-18   (the league's sim date)
```

A provenance check written the obvious way would have compared the sim date against today's,
failed, and sent the next reader hunting a parser bug that does not exist. The test asserts
the two readings **differ**, so the hazard is demonstrated rather than argued.

## What Phase 10 inherits

1. **The differential must stay green before anything renders.** The plan's commit note is
   binding: a report built on an unvalidated parse is the silent-wrong-data failure the
   requests README describes. It runs in ~10 s.
2. **`parse_seconds` is measured, recorded and read back** — 2.0–3.1 s across runs. AC17
   asserts it exists, is not NULL and is not zero, and that an independent re-parse lands
   within an order of magnitude — which is the half a stored number cannot assert about
   itself. **There is no threshold and adding one is a scope change** (Decisions §6); the
   only bound is a 900 s unit-mistake catch, and a test pins that it stays 100× away from
   the measurement.

   **AC17 stands at `partial`, and that is not a Phase 9 defect.** Its text names *"the
   ingest-run row **and the catalog**"*; the catalog is Phase 11 and is not due yet. The
   ingest-run half is met and executed. The wording is deliberately left alone — rewriting
   it now would erase the reminder that Phase 11 owes something. This is the opposite call
   from AC6, whose clauses are not merely early but measured to be wrong.
3. **Tier B is confined to the Cubs probe, permanently.** Challenge Mode has no export
   (ADR 0003), so nothing here validates `OOTP-AI.lg`. Do not let a green suite imply the
   parser was diffed against the club we manage; Tier A, byte accounting, cross-mode
   equivalence and the operator's spot-check are what cover it.
4. **Tier B is never a rating validator**, and that is now mechanical rather than prose:
   `test_export_diff.py` fails if any compared field's category is `rating-true`.

## Still open, and named rather than left to be found

- **`color_2` is unidentified.** Best candidate `ballcaps_visor_color_id` at 237/259. The
  next attempt starts from the field-map note rather than from scratch.
- **`bronze_team.historical_id` lands NULL where `bronze_player.historical_id` lands `""`**
  for the same semantic — no real-world counterpart. The player walk keeps NULL for "the
  tail did not decode", a distinction the team walk has no way to draw. Making them agree is
  a **landing** change and a re-land, not a differential change, so it is recorded here
  rather than made under cover of a validation phase.
- **`team_full_name` has no answer key and never will from this export** — the export carries
  `name`, `nickname` and `abbr` but no assembled full name. Stays `measured` / `none`, and
  `test_export_diff.py` pins that it is not compared.
- **`calendar_real_sim_date` is compared and proves nothing.** Both sides are 0 on all 3,058
  rows, so a parser reading an adjacent zero `u16` scores identically. Its validator token
  stays `none` — `RowSpec` carries a validator **per field** rather than one per table
  precisely so a green row comparison could not quietly promote it. What would settle it is a
  mid-season save with a partially-simulated calendar.
- **`team_human_flag` was considered for upgrade and declined.** Its note records that both
  export columns (`human_team`, `human_id`) are 1 on the single managed club and 0 elsewhere,
  so the answer key cannot separate the two readings. That argument is untouched by this
  phase; the label stays `measured`. Same for `human_manager_team_id`, where three consecutive
  identical slots leave no oracle able to say which is which.
- **The differential does not cover `bronze_name`.** The export has no string table;
  name *values* are validated through `players.first_name`/`last_name` by AC7
  (`test_names_join.py`), which is a different module and a different criterion.

## docs-delta

**Route through `/update-docs`; do not edit `docs/` directly** — it is in the data-engineer
deny set. Each entry names the test that earned it.

**`docs/data-access.md` — the `teams.dat` sentence.** It currently reads *"followed by team
colors as u32 ARGB. All 30 MLB clubs extract cleanly with correct abbreviations and colors"*,
which now under-claims on two axes — scope and slot identity:

- The 5-string signature and the whole team dimension are `verified` at **259 clubs**, not
  30 — `tests/test_parser_vs_export.py::test_the_differential_is_clean_over_every_landed_field`.
- The three colour slots are **background / unidentified / text**. `color_1` equals the
  export's `background_color_id` and `color_3` equals `text_color_id` on **259 of 259**;
  both are `verified` / `export-exact-all-rows`. `color_2` is `measured` and unidentified —
  every one of the export's eight colour columns was scored against it and the best,
  `ballcaps_visor_color_id`, reaches 237/259. Record the near-miss so the next attempt starts
  from it.
- Alpha is `0xff` on every slot of every record, so the comparison checks it rather than
  masking it (`argb_hex`).

**`docs/data-access.md` — `teams.historical_id` is carried by the export.** The field map
asserted the opposite for months. All 30 non-empty values match exactly; the other 229 are
NULL here against `''` there, under a bounded absence rule. Now `verified` /
`export-exact-modulo-absence`.

**`docs/data-access.md` — `teams.parent_team_id` now carries export-exact evidence** in
addition to the mutual-link derivation, which remains the only check available on a
Challenge-mode save.

**`docs/data-access.md` — the `players.dat` population.** 18,077 framed against the export's
18,072 active, with the five extras pinned by **id** (`PARSED_ONLY_PLAYER_IDS`), not by
count. The ids are already recorded in that file; this ties the code to them.

**Three upgrades considered and DECLINED — record the reaffirmation so Phase 12 does not
re-open them.** Each is held down by an argument this phase does not touch:

| field | why it stays where it is |
|---|---|
| `team_human_flag` (`measured`) | both export columns are 1 on the single managed club and 0 elsewhere, so the answer key cannot separate `human_team` from `human_id` |
| `human_manager_team_id` (`inferred`) | three consecutive identical `u32`s; no oracle can say which slot is which |
| `calendar_real_sim_date` (`unconfirmed`) | compared and exact on all 3,058 rows — and **both sides are 0 on every row**, so it discriminates nothing. `RowSpec` carries a validator per field precisely so a green row comparison could not promote it |

**`CLAUDE.md` project map and `README.md` status** do not yet know `src/ootp_ai/validate/`
exists. One line under `warehouse/`: *"Tier B — the landed warehouse diffed against the
export, per field by name. Not on the ingest path."*

## The acceptance panel, and what it changed

Six reviewers, five verifiers, **0 findings unverified, 0 blockers, 6 majors**. Nothing was
refuted; the differential's headline was reproduced independently five times, including two
hand-driven `diff_snapshot()` runs.

**The meta-audit caught a wrong `Measured` number that no lens raised, and it was mine.**
Three new sites said *"keying the export's eight columns collapses 3,058 rows to 2,600, so
458 are genuine duplicates"*. Re-measured — by the verifier and then independently here —
the eight compared columns collapse to **2,733**, losing **325**. The 2,600/458 pair is
correct for the *four-column* key and is what the Phase 5b grain argument uses; Phase 9
carried a true number across to a different key. The multiset decision is unaffected. All
sites now name both keys with their own figures.

**Five majors were fixes to the guard rather than to the data**, which is the right shape
for a phase whose thesis is that the harness must not pass vacuously:

| # | What was wrong | Now |
|---|---|---|
| CF1 | `diff_snapshot` never called `check_provenance` — "provenance before any comparison" held only because one test sat above the others in one file. Phase 10's render gate is told to call this entry point | asserted as the function's first statement, with a test driving the entry point |
| CF2 | `compare_keyed` reported **clean** when a walk lost *every* declared parsed-only row: the report was built by iterating rows that were not there | the count discrepancy is a fault in its own right, in both directions, with an offline test |
| CF3 | Every cross-check enumerated *from the harness*, so deleting a `ColumnPair` narrowed AC6 silently — proven by deleting two and getting zero failures | a reverse check enumerates from `field_map.toml`; seven exemptions, each naming the artifact that earns it |
| CF7 | `export_rows` was documented as *the* anti-narrowing guarantee and read by nothing — and `DIVISION_SPEC`'s value was already wrong (30, our count, where the export returns 34) | enforced in both comparison functions; the offline suite now has an anti-narrowing signal it did not have |
| CF8 | One shared `allowed` counter judged every whole-row rule against the sum; and a whole-row rule on a keyed table could never fire, so its population was never checked | per-rule tallies, orphaned rules reported, and the whole-row predicate narrowed to the one side it can see |

Ten minors and nits were also fixed: `rating-scouted` now blocked via `policy.RATING_CATEGORIES`
(the *dangerous* half was sailing through), duplicate keys refused rather than collapsed,
row specs emit per-column output, the four ad-hoc SQL queries in the test module route
through `quote_ident`, the five extras pinned by identity, `PROBE_*` renamed `TRUTH_SAVE_*`
(two saves were sharing the word), a subsumed assertion made able to fail, and the read-only
proof extended to the truth save — which Phase 9 turned into a routinely parsed save.

**One nit is carried, not fixed** (CF24): an interrupted pytest run can leave a leak-guard
probe file at the repo root and turn the next run red in an unrelated module. Out of scope
here; worth a bugfix request.

## Gate at handoff

`ruff check` / `ruff format --check` / `mypy` clean over 67 source files.
**Offline 520 passed** (481 after Phase 8b; 39 new in `test_export_diff.py`, nine of them
added closing the panel's findings).
**Gamedata 153 passed, 1 skipped** (131 + 1 after Phase 8b; 22 new — AC6's 17 and AC17's 5).
The skip is `test_byte_accounting.py`'s strict-tier assertion, named and expected:
*"the teams walk is declared 'diagnostic', not strict"*.
