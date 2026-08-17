<!-- handoff: v1 -->

## track

feature

## built

`src/ootp_ai/parser/world.py` — the only file written. Nothing under `tests/`, `docs/`,
`.github/`, `ops/` or `.claude/` was opened for writing; `snapshot.py` and `ingest.py` are
untouched (wiring `read_world` into ingest is Phase 8). Investigation lives in
`var/spike5/` (gitignored, ten probes, `p1`–`p10`), which uses absolute offsets freely
because it is investigation and none of it is imported by `src/`.

The walk enters `world.dat` three times, and every entry is a **search validated by a
forward parse**, never an offset:

* **The league record** — the composite `<u32 21>Major League Baseball`, `measured` unique
  in all three saves. The record head is four `u32`s in front of the name; the read is
  checked by requiring the string that follows them to *be* the landmark, and by requiring
  all four to look like ids.
* **The sub-league nest** — a bounded backward scan of the 64 bytes before the composite
  `<u32 2>AL<u32 15>American League` (itself unique per save), keeping only positions from
  which the **whole** nest parses and whose span contains the landmark. `measured`: exactly
  one position validates in each save. The ~1,170 bytes of league scalars between the head
  and the nest are crossed at a width computed from the two search results.
* **The calendar** — no string can reach it (see `could-not-do`), so it is found
  structurally: the one `u32`-count-prefixed array of well-formed records with strictly
  increasing `seq` that is **maximal in both directions**. Left-maximality is what makes
  this work — without it every save yields two survivors, the array and its own last
  record; with it, exactly one.

`read_calendar(cursor)` is public and callable on 40 bytes of synthetic input, exactly as
the test module asks. It reads the count, consumes precisely that many records, refuses a
count that is not a calendar, and raises through the cursor if the region runs out. The
three flag bytes land as `int`; `event_type` lands raw with no label and no lookup table;
`deleted` rows are landed, never filtered. `division_id` was not stamped onto `TeamRecord`.

Byte accounting is declared `region-accounted` with a rationale that names what was
reached, what was not, and that a from-the-top walk behind the ~94,126-record city array
is what a later attempt should try first.

## verified

| Check | Command and actual output |
|---|---|
| Offline suite, no game and no MySQL | `uv run pytest -m "not gamedata"` → `171 passed, 61 deselected in 0.91s`. The 20 offline tests of `tests/test_parse_world.py` are inside it, including the four synthetic-calendar cases and the six dataclass-shape cases. |
| Whole gamedata suite | `uv run pytest -m gamedata` → `1 failed, 59 passed, 1 skipped, 171 deselected in 48.91s`. The one failure is `test_parse_world.py::test_deleted_is_an_attribute_of_a_future_event_and_not_a_synonym_for_past`, and it is a **spec constant, not the walk** — see `could-not-do`. The skip is `test_byte_accounting.py::test_the_walk_accounts_for_every_byte_when_it_claims_to`, skipped by its own design because `teams.py` declares `diagnostic`. |
| The world tests against the three saves | `uv run pytest -m gamedata tests/test_parse_world.py -q` → `..F......` — 8 passed, 1 failed. Passing: the 3,058-entry count, `seq` uniqueness plus the 2,600 readable-key collapse, the flag domain, the three human-action dates, no club in two divisions, both regions audited, the constant-offset control, and two-reads-agree. |
| Region accounting, both directions | `uv run pytest -m gamedata tests/test_byte_accounting.py tests/test_cross_mode_format.py -q` → `s..................` — 18 passed, 1 skipped. Includes `test_every_byte_is_either_inside_a_walked_region_or_reported_as_un_walked`, `test_a_region_accounted_claim_is_not_an_under_claim_either` and `test_the_un_walked_prefix_and_suffix_are_recorded_rather_than_waved_at`. |
| AC9 at full strength, including the 34→30 tightening | `uv run pytest -m gamedata tests/test_parse_real_save.py -q` → `..................` — 18 passed. That set includes `test_the_managed_league_is_thirty_clubs_once_the_divisions_say_which_ones`, `test_the_four_records_no_division_claims_are_the_all_star_sides`, `test_the_managed_league_renders_the_thirty_abbreviations_of_real_baseball` and the export-backed `test_the_division_arrays_match_the_exports_division_column`. **MySQL was reachable — nothing in this run skipped.** |
| The two unrecoverable-failure guards, after full reads of `world.dat` | `uv run pytest -m gamedata tests/test_read_only.py -q` → `..` (2 passed); `uv run pytest tests/test_no_fixed_offsets.py -q` → `....` (4 passed). Zero mtime and zero digest differences under both roots, with the AST scan run over the enlarged parser tree. |
| Lint, format, types | `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `110 files already formatted` (37 Python files plus 73 markdown, this handoff among them — it read `109` before the handoff existed) · `uv run mypy src tests` → `Success: no issues found in 37 source files`. |
| The calendar decode against a source I did not write | `var/spike5/p7_verify.py` (gitignored), driving the **shipped** `read_world`: `league_id +0: 3058 of 3058 entries match an export row exactly on all eight columns`. Controls: `league_id -3: 1070` and `league_id +3: 1070`. Export side: `SELECT COUNT(*) FROM ootp_truth_real.league_events` = `3058`. |
| Division membership against the same oracle, with a control | same run: `parsed 6 divisions, export 6, exact match=True` against `SELECT sub_league_id, division_id, team_id FROM ootp_truth_real.teams WHERE league_id = 203 AND allstar_team = 0`. Control adding 1 to every parsed `team_id`: `match=False`. All six divisions carry the same five clubs in all three saves. |
| The crossed sub-league / division scalars are the fields they look like | `var/spike5/p8_subleagues.py` → `sub_leagues` row for 203: `sub_league_id 0, name 'American League', abbr 'AL', gender 0, designated_hitter 1`, and disk holds `id, abbr, name, gender(0), dh(1)` — note the export's column order is `(name, abbr)` and disk is `(abbr, name)`. `divisions` row: `division_id 0, name 'East Division', gender 0`; disk holds `id, name, gender(0)` then the team array. |
| The league record head, against the export's own league row | `var/spike5/p4_prototype.py` → `league head 5,548,602 league_id=203 mid=206 z1=0 z2=0` in all three saves, and `MLB league row: {'league_id': 203, 'name': 'Major League Baseball', 'abbr': 'MLB', 'nation_id': 206, 'language_id': 0, 'gender': 0, …}`. Four `u32`s, four matching values, one league row. |
| Landmark uniqueness, per save | `var/spike5/p1_landmarks.py` → `MLB name occurrences=1`, `AL composite occurrences=1`, `OPENING DAY occurrences=95` in **each** of managed / truth / probe. Offsets differ across saves: the MLB name sits at `5,548,618` (managed and probe) and `5,547,958` (truth). |
| The calendar's structural landmark is unique, and why | `var/spike5/p5_discrepancies.py` → per save, `right-maximal=2 left-maximal=1`, and the rejected candidate is always the array's own **last record** (`count_off=6,954,461 count=1 end=6,954,511` in the managed league — the same `end` as the real array). Same result at window 146 and at window 512. Upstream of that: `motif hits 33,564 → 7,488 plausible counts → 2,253 arrays that fully walk → 2 right-maximal → 1`. |
| Region accounting, in bytes, per save | `var/spike5/p7_verify.py`. **managed** `8,898,534` B: divisions `[5,548,602, 5,550,200)` len `1,598` declared 6 parsed 6; calendar `[6,756,277, 6,954,511)` len `198,234` declared 3058 parsed 3058; prefix `5,548,602`, gap `1,206,077`, suffix `1,944,023`, un-walked `8,698,702` (97.8%). **truth** `8,661,828` B: divisions `[5,547,942, 5,549,540)`; calendar `[6,519,598, 6,717,832)`; prefix `5,547,942`, gap `970,058`, suffix `1,943,996`, un-walked 97.7%. **probe** `8,657,688` B: divisions `[5,548,602, 5,550,200)`; calendar `[6,515,458, 6,713,692)`; prefix `5,548,602`, gap `965,258`, suffix `1,943,996`, un-walked 97.7%. Walked bytes are `199,832` in all three. |
| The three counts the brief asked me to confirm or contradict | `var/spike5/p7_verify.py`. **3,058 — confirmed**, in all three saves, with 3,058 distinct `seq` (min 1, max 3058). **2,600 — confirmed**, in all three saves, for `(league_id, start_date, event_type, name)`. **2,482 — contradicted**: I read `deleted` on `2,492` entries in truth and probe and `2,259` in the managed league, and the export agrees with me — `SELECT SUM(deleted <> 0) FROM ootp_truth_real.league_events` = `2492`, `SELECT COUNT(*) … GROUP BY deleted` → `deleted=0: 566, deleted=1: 2492`. |
| `deleted` is not history, in every save | `var/spike5/p7_verify.py` → deleted rows dated after the sim date: `2,224` of 2,259 (managed, sim 2024-03-07) and `2,453` of 2,492 (both probes, sim 2024-03-18). First five deleted MLB rows after the sim date, identical in all three: `Trading Deadline 2024-07-31`, `Regular Season Ends 2024-09-30`, `PLAYOFFS BEGIN 2024-10-02`, `PLAYOFFS BEGIN 2024-10-07`, `OPENING DAY 2024-04-05`. So the *second* assertion of the failing test would pass in all three saves. |
| `needs_human_action`, the field the phase is for | `var/spike5/p9_human_action.py` → **112 flagged in all three saves**, of which live (not deleted) in league 203: exactly **3**, identical across saves down to `seq` and `event_type` — `2024-07-11 type=2 seq=255 First-Year Player Draft`, `2024-07-31 type=5 seq=261 Trading Deadline`, `2024-12-13 type=4 seq=1227 Rule 5 Draft`. The managed league additionally has 7 live flagged events in leagues `221, 237, 238, 240, 253`; the probes have none outside 203. |
| The flag domain, and `real_sim_date` | `var/spike5/p7_verify.py` → `flag byte values seen: [0, 1]` and `real_sim_date values: [0]` in all three saves, over all 3,058 entries. Export cross-check: `SUM(event_over <> 0)` = `10` and `SUM(needs_human_action <> 0)` = `112`, matching the parse. |
| The calendar is **not** byte-identical across all three saves | `var/spike5/p5_discrepancies.py` → the 198,234-byte spans hash `5f08c87fba81c85b` for truth **and** probe, `aa5602fd3902038e` for managed; `managed vs truth: differ at 233 byte positions, first at +6,672, last at +98,051`. 2,492 − 2,259 = **233**, so the whole difference is `deleted` flags. `p7_verify.py` confirms at row level: `probe vs truth: calendar equal=True`, `managed vs truth: calendar equal=False`, `divisions equal=True` for every pair. |
| Determinism and cost | `test_two_reads_of_the_same_unchanged_file_agree` PASSED; `p7_verify.py` reports `parsed in 0.13s` for each of the three saves (8.7–8.9 MB read plus the whole-file structural search). |
| Nothing machine-specific in files `git ls-files` cannot see yet | `var/spike5/p10_leakscan.py`, importing `PATTERNS` from `tests/test_no_leaks.py` → `world.py: scanned 883 lines`, `handoff-phase-5b.md: scanned 265 lines`, `total matches: 0`. Both files are untracked, so `test_no_leaks.py` and `test_doc_links.py` are blind to them until `/commit`; the handoff carries no markdown links by construction. |
| The tree holds one new file and no test edits | `git status --porcelain` → `?? src/ootp_ai/parser/world.py` alongside the five pre-existing ` M tests/…` lines and the two pre-existing `?? tests/…` lines that were there when I started. No file under `tests/` was written. |

## assumed

- **The pad is three zero bytes and the name is printable ASCII ≤ 120 characters.** Both are
  used by the *search* validator, so a save that violates either makes the calendar
  unfindable and raises — loud, not silent. `measured` support: the pad is `000000` on all
  3,058 entries of all three saves (every one of them parsed under a validator that
  requires it), and name lengths run **11 to 50** (`var/spike5/p6_bounds.py`). The bound of
  120 is my margin, not a measurement.
- **The four `u32`s ahead of the league name belong to that record, in the order
  `league_id, nation_id, language_id, gender`.** The *values* are `measured` (203/206/0/0 in
  all three saves, matching the export's `leagues` row). The *order* is `inferred` beyond
  the first two: `language_id` and `gender` are both `0` here, so nothing distinguishes them
  from each other or from any other zero column. Only `league_id` is landed, and it is
  cross-checked downstream — `test_the_division_arrays_match_the_exports_division_column`
  and the managed league's 30-club test both go red if it is wrong, in two universes.
- **`seq` is strictly increasing within the array.** Used as a search validator.
  `measured`: 3,058 distinct values running 1…3058 with no repeats, in all three saves. A
  future save with a gap still parses; one with a *decrease* would not be found.
- **The sub-league nest's `gender` (`u32`) and designated-hitter (`u8`) are crossed at
  measured widths, not decoded.** Confirmed by shape — a wrong width desynchronises the very
  next length prefix — and by value against the export (`gender 0`, `designated_hitter 1`).
  Neither is landed.
- **`world.dat`'s header sim date is the league's.** `measured` — `2024-03-07` for the
  managed league and `2024-03-18` for both probes, which is what
  `tests/test_cross_mode_format.py` asserts and what `test_deleted_…` compares against.
- **The suffix is high schools and colleges** — `inferred`, carried over from the Phase 5
  recon. Nothing in this phase read those 1.94 MB; all I measured is that they exist and
  how many there are.

## surprised-me

Memory candidates. **I could not append them** — see `could-not-do`; they are written out
here in the memory file's own entry format so the operator can paste them at the doc gate.

- **2026-08-16** · `verified` · **A structural landmark beats a string landmark when the
  string is not unique.** The calendar could not be entered by any string (`OPENING DAY`
  occurs 95 times) but is trivially identifiable by *shape*: one count-prefixed array of
  self-consistent records, maximal in both directions. 43,813 motif hits reduce to exactly
  one candidate per save in 0.16 s. · evidence: `src/ootp_ai/parser/world.py`
  `_find_calendar_array` · tag: harness
- **2026-08-16** · `verified` · **Right-maximality alone is not uniqueness — every record in
  a count-prefixed array is a candidate head**, because the four bytes in front of a record
  are the previous record's tail and often read as a small count. The array's own last
  record declares `count=1`, walks, and is right-maximal. The fix is a bounded
  **left-maximality** test: no record may end exactly where the count begins. Two survivors
  become one. · evidence: `var/spike5/p5_discrepancies.py` (gitignored) · tag: harness
- **2026-08-16** · `measured` · **`re.finditer` is non-overlapping, which can hide the very
  match a byte-motif search needs.** A seven-byte motif consumed at offset *n* hides one
  starting at *n+4*. Wrap the pattern in a zero-width lookahead `(?=…)` — 33,564 hits become
  43,813, cost 0.06 s over 8.9 MB. · evidence: `src/ootp_ai/parser/world.py` `_EVENT_MOTIF` ·
  tag: tooling
- **2026-08-16** · `measured` · **PowerShell `Measure-Object -Line` does not count blank
  lines** — it reported 235 for a file `Get-Content …).Count` and `str.splitlines()` both
  put at 250, which is exactly a CI ceiling. Use `.Count` when a guard's number is the
  question. · evidence: `tests/test_agent_contract.py` `MEMORY_CEILING` · tag: tooling
- **2026-08-16** · `verified` · **Two decode paths over the same bytes is a cheap, real
  cross-check.** The lookahead scan that validates an entry and the cursor that then reads
  it produce `declared_count` and `parsed_count` independently, so a `WorldRegion`'s
  self-audit is not a tautology the way `len(list)` against its own count would be. ·
  evidence: `src/ootp_ai/parser/world.py` `_walk_divisions` · tag: harness
- **2026-08-16** · `measured` · **A landmark's offset can coincide across saves and still not
  be a constant.** The MLB league name sits at byte 5,548,618 in *both* the managed league
  and the Challenge probe — two independently created universes — and at 5,547,958 in the
  standard probe. An offset that agrees in two of three saves is the most dangerous kind of
  near-constant. · evidence: `var/spike5/p1_landmarks.py` (gitignored) · tag: harness

## could-not-do

- **One gamedata test is red and I did not touch it.**
  `tests/test_parse_world.py::test_deleted_is_an_attribute_of_a_future_event_and_not_a_synonym_for_past`
  asserts `len(deleted) == DELETED_EVENTS` with `DELETED_EVENTS = 2482`. I measure **2,492**
  (truth, probe) and **2,259** (managed). The export agrees with my decode:
  `SUM(deleted <> 0)` over `ootp_truth_real.league_events` is `2492`, and my parse of the
  same save matches the export on all 3,058 rows across all eight columns. So the constant
  looks like a transposition of 2,492 — **and it cannot be repaired by changing the number
  alone**, because the managed league genuinely differs: the calendar is *not* byte-identical
  across all three saves (233 bytes differ, and 2,492 − 2,259 = 233, all of them `deleted`
  flags). A single per-save equality cannot hold. The test's *second* assertion — that some
  deleted event is dated after the sim date — passes in all three saves (2,224 / 2,453 /
  2,453). This is yours to fix; per the brief I did not edit toward my own numbers.
- **Could not append to `.claude/agents/data-engineer-memory.md`.** It is at exactly **250**
  lines and `tests/test_agent_contract.py::test_memory_file_under_runaway_ceiling` asserts
  `<= 250`, so one appended line turns a guard red. The memory file says *append freely,
  never prune*, and pruning is the operator's job at `/update-docs` — so the six entries are
  in `surprised-me` above, pre-formatted, and nothing was written to that file.
- **Could not reach the other fourteen leagues' division nests.** Each league record carries
  its own unmapped ~1,170-byte scalar block between its head and its sub-league count, and
  the block's width is not derivable (MLB's four award-name strings are part of it, and a
  minor league need not have four). Only the league named `Major League Baseball` is landed.
  `tests/test_parse_real_save.py`'s docstring for the division test says *"the minor-league
  nests are landed but unvalidated"* — with this walker they are **not landed at all**, and
  the sentence should be corrected when the constant above is.
- **Could not reach the calendar through the schedule, and did not report a `schedule`
  region.** The schedule's head is a `u32` game count — 12,961 in the probes, **16,817** in
  the managed league — so it cannot be found without already knowing the number, and the
  ~490 KB between the division nest and it is undecoded league data. Worse, the 37-byte
  record width does **not** reproduce in the managed league: in truth and probe the distance
  from the head to the trailing count is exactly `count × 37` (`479,557 = 12,961 × 37`), but
  in the managed league it is `622,233`, which is `16,817 × 37 + 4`
  (`var/spike5/p5_discrepancies.py`). Crossing it would have been unsafe in the one universe
  that has no export. So the walk uses the calendar's own structural landmark instead —
  which the brief calls the cleaner of the two options — and `regions` holds two entries,
  not three. `KNOWN_REGIONS` permits this; `REQUIRED_REGIONS` is satisfied.
- **Could not decode the ~1,170-byte league scalar block, the ~965 KB–1.2 MB gap, the 1.94 MB
  suffix, or the ~5.5 MB prefix.** All four are reported as numbers rather than read. What
  would settle the prefix is the from-the-top walk behind the ~94,126-record city array —
  named in `TIER_RATIONALE` as the thing a later attempt should try first.
- **Could not identify `real_sim_date`.** It is `0` on all 3,058 entries of all three saves,
  so no save on disk discriminates it. Landed raw, labelled `unconfirmed`. What would settle
  it: a save taken mid-season, where a partially-simulated calendar might populate it.
- No destructive git operation was needed. Nothing was written outside
  `src/ootp_ai/parser/world.py`, this handoff, and `var/spike5/`.

## docs-delta

For `/update-docs` to route into `docs/data-access.md` §4, with proposed labels. I did not
edit that file.

- **`measured`, new** — `world.dat` holds the world as **one** record (header-tail field 5 is
  `1` in all three saves) and is entered by landmark. The top league's record begins with
  four `u32`s — `league_id, nation_id, language_id, gender` — reading 203/206/0/0 and
  matching the export's `leagues` row field for field, followed by the length-prefixed name
  and abbreviation. **`inferred`:** the order of `language_id` and `gender`, which are both
  zero and therefore unplaceable in principle from this data.
- **`measured`, new** — division membership nests
  `league → sub_league → division → u32 count + explicit team_id array`. A sub-league record
  is `u32 id`, abbreviation, name, `u32 gender`, `u8 designated_hitter`, `u32 division_count`;
  a division record is `u32 id`, name, `u32 gender`, `u32 team_count`, then that many
  `u32 team_id`. All six MLB divisions match the export exactly in all three saves, with the
  control (every `team_id` + 1) failing. **The export's column order is again not disk
  order**: `sub_leagues` exports `(name, abbr)` and the disk writes `(abbr, name)`.
- **`measured`, new** — the league calendar is a `u32`-count-prefixed array of
  `u32 seq, u32 league_id, u16 event_type, u8 day, u8 month, u16 year, 3 zero pad,
  u32 length + name, u8 event_over, u8 deleted, u8 needs_human_action, u16 real_sim_date`.
  3,058 entries, 198,234 bytes, in all three saves; all 3,058 match
  `ootp_truth_real.league_events` on all eight exported columns, control `league_id ± 3`
  scores 1,070. `seq` runs 1…3058, is unique, and is **not in the export**.
  **`unconfirmed`:** `event_type`'s enum semantics (33 distinct values observed) and
  `real_sim_date` (0 on every row of every save).
- **`measured`, corrects the Phase 5 recon and the plan** — the calendar is **not**
  byte-identical across all three saves. Truth and probe are byte-identical to each other;
  the managed league differs in exactly **233** bytes, all of them `deleted` flags
  (2,492 set in the probes, 2,259 in the managed league). The recon's "2,482" is wrong in
  both senses: the export's own count is 2,492, and no single number holds across saves.
- **`measured`, new** — `needs_human_action` is set on **112** of the 3,058 entries in all
  three saves, but 109 of those are also `deleted` in the probes (102 in the managed league).
  The live, top-league set is exactly three and is identical across saves down to `seq`:
  First-Year Player Draft (2024-07-11, `event_type` 2, `seq` 255), Trading Deadline
  (2024-07-31, type 5, seq 261), Rule 5 Draft (2024-12-13, type 4, seq 1227). The managed
  league carries seven further live flagged events in leagues 221/237/238/240/253.
- **`measured`, new** — `deleted` is not a tombstone for the past: 2,224 of the managed
  league's 2,259 deleted rows are dated *after* its sim date, including a duplicate
  `OPENING DAY` and two further `PLAYOFFS BEGIN`. Any consumer filtering on it is filtering
  live schedule.
- **`measured`, corrects the Phase 5 recon's `inferred` schedule claim** — the schedule is
  count-prefixed at a **per-league** game count (12,961 in both probes, 16,817 in the managed
  league). The 37-byte record width reproduces exactly in the probes
  (`479,557 = 12,961 × 37`) and **does not** in the managed league, where the same
  arithmetic leaves 4 bytes over (`622,233 = 16,817 × 37 + 4`). The width should stay
  `inferred` and is now known not to be universal.
- **`measured`, new** — landmark uniqueness in `world.dat`, for anyone entering it later:
  `<u32 21>Major League Baseball` and `<u32 2>AL<u32 15>American League` occur exactly once
  per save; `<u32 11>OPENING DAY` occurs 95 times. Region offsets differ per save, but the
  MLB landmark lands at the *same* byte in the managed league and the Challenge probe
  (5,548,618) and a different one in the standard probe (5,547,958) — a coincidence worth
  recording, because it is exactly the shape a false "constant" takes.

## still-open

- **Ambiguity resolved small (Escalation case 3): one league's divisions, not fifteen.** The
  reading I took is "land the division nest the phase's landmarks identify" — MLB's. The
  reading I did not take is "land every league's nest", which needs the league scalar block
  decoded fifteen times over and is the from-the-top work Phase 5b defers. Everything the
  tests assert is satisfied by the smaller reading, and `bronze_division_team` will simply
  hold six rows per snapshot until somebody widens it.
- **The failing test and the test-side docstring are yours to fix**, and I would fix them
  together: `DELETED_EVENTS` cannot be a single per-save constant, and the division test's
  "minor-league nests are landed but unvalidated" is not true of this walker. A shape that
  would work: assert `deleted` is a *majority* of the calendar and pin the export's 2,492
  only for the save that has an export.
- **`test_a_constant_offset_would_not_have_found_these_regions` passes, but only just.** The
  divisions region enters at the same byte (5,548,602) in the managed league and the
  Challenge probe; the calendar's three entry points are all different, which is what carries
  the assertion. If a future save pair ever agreed on both, the test would go red on a
  correct walk — worth knowing before it happens.
- **Phase 8 wiring is not done, by instruction.** `read_world` is not called from
  `ingest.py`, so the ingest row carries no world counts and no un-walked prefix/suffix
  numbers yet. Those numbers exist on `WorldFile.regions` and `WorldFile.file_bytes`,
  ready to be recorded: walked bytes are 199,832 and un-walked 8.46–8.70 MB per save.
- **The search cost is ~0.13 s per save**, dominated by the whole-file motif scan. If a later
  phase reads `world.dat` many times in one run, cache the `WorldFile` rather than the
  buffer — the gamedata suite currently parses it about 30 times and takes 49 s in total.
- **Nothing outward-facing was produced or run**, so there is no user-run step from this
  phase. The operator-facing question this phase *creates* is for ADR 0013: the game names
  exactly three dates the front office must act on, and one of them (2024-07-31) already sits
  inside the current season.
