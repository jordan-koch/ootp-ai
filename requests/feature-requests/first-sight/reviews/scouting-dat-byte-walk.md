<!-- handoff: v1 -->
# `scouting.dat` walked with byte accounting — the club's own view is not in this file

> Run 2026-08-16 against the retained standard-mode save and `ootp_truth_real`.
> Throwaway scripts under the git-ignored `var/spike2/`; the save was opened only via
> `Path.read_bytes()`; the warehouse side used the read-only session in
> `src/ootp_ai/db.py`. Citations are code spans, never links; nothing links into
> `var/`. No rating values are transcribed — this repo is public.

## track

feature

## built

nothing under `src/` — investigation only. Twenty-two throwaway scripts under
`var/spike2/`, which is git-ignored and not part of the deliverable. The Phase 3
`Cursor` was used as-is for the walk in `var/spike2/39_walk.py`; it needed no change,
and its refusal to move backwards caught a wrong layout hypothesis immediately.

## verified

| claim | command | output |
|---|---|---|
| The file segments with **zero residual** | `uv run python var\spike2\24_segment.py` | `file 2,349,181 B = header 182 B + 18,077 records (2,348,999 B); residual 0` |
| Record count is declared in the header | same, plus `20_boundaries.py` | u32 at file offset 178 reads `18077`, equal to the segmented record count |
| Records are delimited, not merely strided | `44_final.py` | `100.000% (18,072) delimiter fd ff ff ff @+0`; `100.000% delimiter 0x01 @+13` |
| `+14` u32 is `player_id` | `44_final.py` | `100.000% (18,072) u32 @+14 == player_id` |
| `+20` Date is the sim date; `+24..26` and `+28..30` are constant zero | `44_final.py` | `100.000% (18,072) date @+20 == 2024-03-18`, `100.000%` both zero runs |
| `+32..42` and `+43..53` are 11-slot `overall` / `talent` arrays holding **OSA's** value at `30+pc` and `41+pc` | `44_final.py` | `100.000% (18,072)` on both |
| The **club's** overall/talent is *not* in those slots | `44_final.py`, `33_landmark.py` | `33.903%` / `14.038%` overall — exactly the agree-rate; `0 / 11,945` and `0 / 15,535` on disagreeing players |
| The club's overall/talent pair is absent from the **whole record** | `32_where.py`, `33_landmark.py` | overall absent for `6,338 of 11,945 (53.1%)`; talent `10,328 of 15,535 (66.5%)`; the pair absent for `16,152 of 16,680 (96.8%)` |
| The tail frame is exact: `-7/-8/-9` are pitching misc, `-6/-5` constant | `44_final.py` | `arm_slot 100.000%`, `ground_fly 99.004%`, `velocity 97.698%`, `0x64 0x64 100.000%` |
| Batting hp bytes appear **exactly twice**, at `+64` and `+77` | `44_final.py` | `92.452%` and `93.664%`; `41_landmarks2.py` puts the pair at offset 64 for `8,274 of 8,611` hitters |
| The variable region is the pitch arsenal, **4 bytes per pitch** | `38_arsenal.py` | landmark tail offset runs `-33, -37, -41, -45, -49, -53, -57, -61` for arsenals of 0..7 |
| **No byte anywhere favours the club's view** — full sweep of every offset in a fixed-length group | `43_fixedlen.py 127` | 3,566 records, 253 offsets x 25 disagreeing columns: verdict `OSA` on every column; best own-view eta2 never exceeds the OSA eta2 at the same offset |
| Same conclusion in both frames across all lengths | `37_perspective.py` | for all 29 columns the best-OSA and best-own offsets coincide, e.g. contact `head+54 u16` OSA `0.964` vs own `0.628` |
| The file holds 5 records the export does not | `24_segment.py`, `25_frames.py` | `in file not export: 5`; those 5 are exactly the records whose `-6,-5` bytes are `0x32 0x32` rather than `0x64 0x64` |

## assumed

- That `ootp_truth_real` is a faithful oracle for both perspectives. Not re-checked
  here; `scouted-view-followup.md` records it as `measured` against the running game.
- That `pc` (the slot code) is `position` for position players and 11/12 for SP and
  RP/CL. Derived from the landmark distribution in `33_landmark.py`, not a documented
  enum, so the *labels* are `inferred` even though the offsets are exact.
- That the 14-byte inter-record block is a record **prefix**, not a suffix. Both frame
  the same bytes; prefix is parsimonious because the 182-byte file header then ends
  cleanly and the last record needs no trailing copy.
- The rulebook's ground-truth rule was applied though the spec did not restate it:
  nothing was matched against an in-game display, only the export and the file itself.

## surprised-me

- **Indexing from the record END is a second stable frame, and it is free** once the
  delimiter is known. It is what located `arm_slot` at 100% after the head frame had
  gone blind. Worth reaching for before any wider offset sweep.
- The forward-only `Cursor` earned its keep in an unusual way: `ValueError: a cursor
  only moves forward; got count=-1` was the *first* signal that my fixed-layout
  hypothesis over-ran the shortest records. A seeking reader would have read garbage.
- A "value absent from the record" rate is a calibrated null: 53.1% absence for a
  1..208 integer in a ~127-byte record is what `(1 - 1/208)^127` predicts almost
  exactly. That turns a negative into a measurement.
- Chaining records by "next expected id within N bytes" loses the thread the first
  time the file holds a record the answer key does not. Segment on the delimiter,
  then diff the id sets.

## could-not-do

- **Could not reach a zero-residual walk of a single record.** Roughly 23-26 of ~130
  bytes are unaccounted; sizes and locations are in `docs-delta`. I stopped rather
  than guessing what they are, per the brief.
- The one place where an assumed-fixed layout demonstrably breaks: the pitching
  `(balk, hp, wild_pitch)` triple sits at `+88` for 8,160 records and `+90` for
  7,178 (`45_triple.py`), so **a 2-byte region between `+80` and the pitching block
  varies and I did not resolve what it is.** Every offset past `+79` is therefore
  `inferred` at best and must not be hardcoded.
- No `numpy`/`scipy`/`pandas` in the environment, so every statistic here is pure
  Python. That capped the sweep at eta-squared over quantile bins rather than a full
  rank-correlation matrix. It did not change any verdict, but it bounded the breadth.

## docs-delta

For `docs/data-access.md` §5, routed through `/update-docs`.

**`scouting.dat` file structure** (`measured`): 182-byte header, then 18,077
fixed-delimited variable-length player records, zero residual. The record count is a
u32 at file offset 178. Records are delimited by a 14-byte block beginning
`fd ff ff ff` and ending `0x01`; the `player_id` u32 follows it. Ids ascend; the file
holds 5 players the export's `players_scouted_ratings` does not.

**Record layout** (offsets are from the delimiter start, and are `inferred` past +79;
none may be hardcoded into a parser):

| bytes | width | content | label |
|---|---|---|---|
| +0..13 | 14 | delimiter; first 4 bytes constant, remaining 10 vary (2-46 distinct each) | `measured` structure, `unconfirmed` meaning |
| +14 | u32 | `player_id` | `measured` |
| +18 | u16 | unknown, 8,366 distinct values | `unconfirmed` |
| +20 | Date | sim date, identical in every record | `measured` |
| +24..26, +28..30 | 6 | constant zero | `measured` |
| +27 | u8 | unknown, 15 distinct | `unconfirmed` |
| +31 | u8 | position-shaped code, 1..12, **not** equal to the export's `position` | `inferred` |
| +32..42 | u8[11] | `overall` per position/role slot; export's `overall` is element `30+pc` | `measured` |
| +43..53 | u8[11] | `talent` per slot; export's `talent` is element `41+pc` | `measured` |
| +54..66 | 13 | batting current: 5 u16, u8 hp at +64, u16 | `inferred` |
| +67..79 | 13 | batting talent: same shape, u8 hp at +77 | `inferred` |
| +80..83 | 4 | bunt, bunt-for-hit, gb/fb hitter type | `inferred` |
| +84..101 | 18 | two 9-byte pitching blocks (3 u16 + 3 u8), current then talent | `inferred`, position varies by 2 bytes |
| next 9-12 | var | fielding then running ratings; size varies for reasons not established | `inferred` |
| next 4n | var | pitch arsenal, exactly 4 bytes per pitch | `measured` sizing, `unconfirmed` content |
| last 9 | 9 | velocity, ground_fly, arm_slot, `0x64 0x64`, then 4 bytes with byte -4 equal to byte -1 in 89.1% | `measured` for the first five |

**The organization's own scouted view is not stored in `scouting.dat`** (`measured`,
upgraded from `inferred`). This is capacity plus accounting rather than a failed
search: every rating group appears exactly twice per record, as a current/talent pair
and never as a second perspective; the raw `overall` and `talent` grades carry OSA's
value at a deterministic offset in 18,072/18,072 records and the club's value in zero
of the 11,945 and 15,535 records where the two disagree; and a sweep of *every* byte
offset in a fixed-length record group, against 25 columns on which the two views
already disagree, favours OSA everywhere. The day-11 similarity caveat does not apply
— every test conditions on players where the views already differ.

**`pitching_ratings_babip` is entirely NULL in the export** (`measured`) — structural
absence, not missing data.

## still-open

- **This rules out `scouting.dat` only.** The club's view may still be stored
  elsewhere; `coaches.dat` and `players.dat` were not opened. That is the next cheap
  probe and it is the one ADR 0014 rests on.
- I took the **smaller interpretation** of "account for every byte": I accounted for
  the record's *regions* and identified the fields I could support, rather than
  pinning every field's meaning. The larger reading — a complete named field map —
  needs the 2-byte variation and the 9-12 byte block resolved first, and a wrong map
  is the one error this project cannot recover from.
- Re-running `44_final.py` on a mid-season snapshot costs minutes and would retire
  the follow-up doc's recommendation 2 outright.
- The `overall`/`talent` per-slot arrays are a useful find independent of this
  question: a scouted positional-fit grade for all 12 slots, which is what a lineup
  or position-change recommendation wants.
- Nothing was run that a user must run. No outward-facing script was produced.
