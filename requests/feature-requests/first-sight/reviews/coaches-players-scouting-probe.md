<!-- handoff: v1 -->
# `coaches.dat` and `players.dat` probed — the coach's scouting ability is stored, the per-player accuracy is not found, and the allocation lever is in `teams.dat`

> Run 2026-08-16 against the retained standard-mode save and `ootp_truth_real`. Throwaway
> scripts under the git-ignored `var/spike3/`; every save file opened only via
> `Path.read_bytes()`; the warehouse side used the read-only session in `src/ootp_ai/db.py`.
> No rating values, budget figures or names are transcribed — offsets and counts only.

## track

feature

## built

nothing under `src/` — investigation only. Twenty-four throwaway scripts under
`var/spike3/`, which is git-ignored and not part of the deliverable.

## verified

| claim | command | output |
|---|---|---|
| `coaches.dat` segments with **zero residual** | `uv run python var\spike3\73_capacity.py` | `sum of gaps + prologue: 2,011,522 (file 2,011,522)`; 3,240 anchored records |
| Coach framing: `coach_id` is a u16 **12 bytes before** the DOB primitive | `58_records2.py` | `unique composite anchors: 3,240 / 3,251 (ambiguous 0)`; `offsets ascending with coach_id: 3239/3239`; 3,229 exact record lengths, min 240 max 11,921 |
| The coach's **scouting ability block is stored**, contiguous u8 | `61_scoutblock2.py` | measured order `zero=0` of 1,600 coaches with a non-zero run; `each value +1` control `0 (0.000%)`; reversed order misses 1,164 |
| Disk order is `scout_amateur_preference, scout_major, scout_minor, scout_amateur, scout_international` | `59_scoutfields.py`, `61_scoutblock2.py` | four fixed-length groups agree; `swap intl/amateur` control scores 17.75% |
| `teach_hitting` / `teach_pitching` sit at run+8 / run+9 | `61_scoutblock2.py` | `1333/1333 (100.000%)` both |
| The block is **not at a fixed offset** — a variable region precedes it | `61_scoutblock2.py` | run offset from record start: 30 distinct values, min 79 max 117 |
| `coaches.dat` **cannot** hold a per-player accuracy vector | `73_capacity.py` | largest coach record 11,921 B; 18,072 active players need ≥18,072 B at one byte each |
| `players.dat` framing: `player_id` is a u32 **12 bytes before** the DOB primitive | `63_players_frame2.py`, `64_players_seg.py` | `1.0` at delta −12 u32; then `anchored records: 18,072 of 18,072`, `anchored more than once: 0`, `file order equals player_id order: True` |
| Player record sizes | `64_players_seg.py` | min 1,235 max 9,229 mean 1,585.5; 241 B before the first record, 1,316 B after the last |
| **No scouting-accuracy field** in either validated frame | `64_players_seg.py` | head best `+57 rate=0.4873 observed=[(2, 16983), (6, 1082)]` — a near-constant 2; tail best `−391 rate=0.2906 observed=[(3, 15853), …]` — a constant 3 |
| Same negative inside the largest fixed-length group | `65_players_group.py` | length 1,339, 221 records; best `+57 rate=0.4118 observed=[(2, 221)]` |
| The players head frame is only validated to ≈+37 | `66_control.py` | 100% at `nation_id +21`, `city_of_birth_id +27 u32`, `weight +31 u16`, `height +33`, `uniform_number +35`, `experience +36`; `team_id`/`league_id`/`organization_id` never exceed 0.79 at any offset or width |
| The export's `batting_ratings_*` are **display scale**, so exact-match byte searches are void | `68_signature.py` | `contact value range: {lo: 20, hi: 75}`; the positive control — OSA's five batting u16s in `scouting.dat`, all 120 permutations — scores `0.000` |
| The export names **no** per-league or per-region scouting priority | `70_where_budget.py` | 13 columns match `scout`, 0 match `coverage`; the only allocation-shaped one is `team_financials.scouting_budget` |
| The scouting **budget is stored, in `teams.dat`** | `71_budget_probe.py`, `72_budget_confirm.py` | 34/34 teams' `scouting_budget` present as i32 (`players.dat` 9/34, `retired.dat` 5/34 by chance on far larger files); `+1` control 2/34; all 34 teams' scouting and draft budgets sit within 64 B of each other |
| The budgets form one per-team i32 block | `72_budget_confirm.py` | around one team's `scouting_budget`: `intl_fa_budget −20`, `development_budget +16`, `draft_budget +20` |

## assumed

- That `ootp_truth_real` is a faithful oracle. Not re-checked here; `scouted-view-followup.md`
  records it as `measured` against the running game.
- That the coach record **starts** at the `coach_id` field rather than that field being a
  suffix of the previous record. Both frame the same bytes; the prologue then ends cleanly at
  173, which is parsimonious but not proof.
- That the five coach bytes mean what the export's column names say. The *order* is measured;
  the *semantics* are the export's and are inherited, not independently checked.
- The rulebook's rules the spec did not restate were applied anyway: nothing was matched
  against an in-game display, and no offset here may be hardcoded — both files carry variable
  regions and every landmark found is relative.

## surprised-me

- **Export column order is not disk order.** Searching for the four scout ratings as a
  contiguous run in the export's order found nothing in 359 of 400 coaches; the disk puts
  `amateur` before `international`. A fixed-length-group sweep found it in one pass. Sweep
  first, derive the order from the sweep, build the signature last.
- **A composite landmark segments a variable-length file in one pass and cannot desync.**
  Greedy "next expected id within N bytes" chaining stalled at 2,166 of 3,251 records on the
  identical data; DOB + two small ints at measured relative offsets got 3,240.
- **The two files share a record prologue shape**: an id, two u32s, then the DOB primitive at
  id+12, then age at DOB+7 and `nation_id` at DOB+9. That the same relative layout opens both
  a coach and a player record is worth expecting in the next file opened.
- The constant-byte false positive recurred **three more times** (a constant `2` at +57
  scoring 0.49 and 0.41, a constant `3` in the tail scoring 0.29). Scoring on the non-zero
  subset stops a zero constant winning but does nothing about a non-zero one.

## could-not-do

- **Could not validate any frame for `players.dat` past ≈+37.** The BBRef-id anchor was tried
  as a second frame and failed its own control — 366 distinct offsets and no column above
  0.74 (`69_bbref_frame.py`). So the accuracy negative holds for the validated head prefix,
  the tail frame and one fixed-length group, and **not** for the record interior.
- **The perspective sweep in `65_players_group.py` is void** and must not be cited: it
  exact-matched display-scale export values against raw storage bytes, the same mistake
  `68_signature.py` then caught with a failing positive control. `players.dat` has therefore
  **not** been tested for either scouted view's rating values.
- Did not resolve what occupies coach bytes between the head and the scout block, nor the
  variable region that starts by +58 in a player record. Both are guesses I declined to make.
- No `numpy`/`pandas`, so every sweep is pure Python; that bounded breadth, not any verdict.
- `docs/league-rules.md` is staged modified in the working tree and `HEAD` moved during this
  session. Neither is mine — I wrote only to `var/spike3/`, my memory file and this handoff.

## docs-delta

For `docs/data-access.md` §5, routed through `/update-docs`.

**`coaches.dat` structure** (`measured`): 2,011,522 B; a 173-byte prologue then 3,251
variable-length coach records, zero residual. Lengths 240–11,921 B, mean 618.7. A record
opens with `coach_id` as a **u16**; the `u8 day, u8 month, u16 year` DOB primitive sits 12
bytes later, `age` u8 at DOB+7, `nation_id` u8 at DOB+9. A variable region follows, then a
contiguous u8 run — `scout_amateur_preference, scout_major, scout_minor, scout_amateur,
scout_international` — with `teach_hitting`, `teach_pitching` 8 and 9 bytes past its start.
The run sits 79–117 bytes into the record across 30 distinct offsets, so **it must be walked
to, never seeked to**.

**`players.dat` structure** (`measured`): 28,653,312 B; 241 B before the first record, 18,072
records, 1,316 B after the last. Lengths 1,235–9,229 B, mean 1,585.5; file order equals
`player_id` order. `player_id` is a **u32** 12 bytes before the DOB primitive; then `age` u8
at DOB+7, `nation_id` u8 at DOB+9, `city_of_birth_id` u32 at DOB+15, `weight` u16 at DOB+19,
`height` u8 at DOB+21, `uniform_number` u8 at DOB+23, `experience` u8 at DOB+24. The head
frame is validated only that far: `team_id`, `league_id` and `organization_id` are at no fixed
head offset, so a **variable region begins before DOB+46** (`inferred`).

**The export's `players_scouted_ratings.batting_ratings_*` columns are on the 20–80 display
scale, not the storage scale** (`measured` — observed range 20..75). They therefore cannot be
used for exact-match byte identification; `scouting.dat`'s OSA batting run, which is known to
be stored, scores 0.000 against them across all 120 field permutations. Only the columns
`scouting.dat` matched exactly — `overall`, `talent` — are raw-comparable. This is the
CLAUDE.md scale trap in its concrete, testable form.

**The per-player scouting accuracy is not in `coaches.dat`** (`measured`, by capacity): the
largest coach record is 11,921 B and a per-player value over 18,072 active players needs at
least 18,072 B. **It was not found in `players.dat`** (`inferred`, weaker): absent from the
validated head prefix, from the tail frame, and from every offset of the largest fixed-length
group, where each apparent hit is a constant byte agreeing by coincidence — but the record
interior is not covered by any validated frame.

**The scouting allocation lever is stored, in `teams.dat`** (`measured`): every one of the 34
teams' `scouting_budget` appears as an i32, against a `+1` control of 2/34, and each team's
budgets cluster inside 64 bytes as one block — `intl_fa_budget`, `scouting_budget`,
`development_budget`, `draft_budget` at relative −20/0/+16/+20. `team_roster_staff.head_scout`
resolves the club's scouting director. **No per-league or per-region scouting priority exists
as an export column at all** (`measured`), so nothing in the save can be identified as one
without an answer key.

## still-open

- **`teams.dat` is now the highest-value next probe, and it is cheap.** The budget block is
  located to within 64 bytes and `team_financials` gives 46 columns of answer key. That would
  make ADR 0014's lever *readable* — the GM could see where the scouting money went — even
  though the per-player result of spending it is still not found.
- **`players.dat` has not been tested for either scouted view.** Doing it properly needs a
  raw-scale oracle: either `overall`/`talent`, which `scouting.dat` proved are raw, or the
  band-fitting `37_perspective.py` used. That is the follow-up, and it is not a re-run.
- Extending the players head frame past DOB+46 needs the variable region walked sequentially,
  which is Phase 5–7 work rather than a spike.
- I took the **smaller interpretation** of "probe both files": I established framing and
  tested for the accuracy fingerprint, and stopped short of mapping either record. The larger
  reading — a field map for `coaches.dat`, whose framing would now support one — is
  deliberately not done, per the brief's warning about a wrong map.
- Nothing here is user-run; no outward-facing script was produced.
