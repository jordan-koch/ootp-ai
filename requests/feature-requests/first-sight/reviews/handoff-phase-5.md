<!-- handoff: v1 -->

## track

feature

## built

`src/ootp_ai/parser/teams.py` — the header half of the walk, and a refusal instead of the
record half. It validates the header, the version, the self-declared filename, and reads
the six-`u32` header tail (a new find: field 5 is the **record count**). It then raises
`UnmappedRecordLayout`, a module-local `SaveFormatError` subclass, on every real save.
The public surface the tests import is complete and pinned: `TEAMS_FILE`,
`BYTE_ACCOUNTING_TIER = "diagnostic"`, `TIER_RATIONALE`, `TeamStandings`, `TeamRecord`,
`TeamsFile`, `read_teams`. The module docstring carries the measured layout table, the
blocker, and the three things a later attempt should try first.

**Why a refusal and not a walker: a team record writes its integer fields only when their
value is non-zero, and the mechanism that says which are present is not in the record,
not adjacent to it, and was not found.** Details under `could-not-do`.

`src/ootp_ai/parser/saved_games.py` — `human_team_id` removed from `SavedGameEntry` and
its construction; the module and class docstrings rewritten so the finding stays and the
dead field goes. `human_team_name` untouched.

`src/ootp_ai/ingest.py` — `_resolve_human_team` deleted rather than moved behind the
teams walk, since there is nothing to move it behind; `human_team_id=None` is set at the
construction site with the reason inline, and the `IngestRun.human_team_id` docstring now
names the real blocker.

## verified

| Check | Command and actual output |
|---|---|
| Offline suite green | `uv run pytest -m "not gamedata"` → `149 passed, 42 deselected in 0.84s`. All 10 offline teams tests pass, including both tier tests and all six refusals. |
| Gamedata half, honestly red | `uv run pytest -m gamedata tests/test_parse_teams_synthetic.py tests/test_byte_accounting.py tests/test_parse_real_save.py tests/test_cross_mode_format.py tests/test_provenance.py` → `21 failed, 10 passed, 1 skipped, 18 deselected in 1.36s`. Every failure is `UnmappedRecordLayout` out of `read_teams`, except `test_an_ingest_run_resolves_its_own_provenance` (`assert None is not None`). |
| Fixed-offset ban | `uv run pytest tests/test_no_fixed_offsets.py` → `4 passed in 0.03s` over the enlarged tree. |
| ADR 0001 | `uv run pytest -m gamedata tests/test_read_only.py` → `2 passed, 8 deselected in 41.15s`. Zero mtime and zero digest differences under both roots, probe then managed. |
| Lint | `uv run ruff check .` → `All checks passed!` |
| Format | `uv run ruff format --check .` → `102 files already formatted` |
| Types | `uv run mypy` → `Success: no issues found in 33 source files` |
| Leak guard over untracked new paths | imported `PATTERNS` from `tests/test_no_leaks.py`, scanned `parser/teams.py`, `ingest.py`, `parser/saved_games.py` and this handoff → `no matches` |
| Record count is real | scratch read of the header tail: `teams.dat` declares 259 / 259 / 337 (standard, challenge, managed); `parks.dat` 199 / 199 / 267; `names.dat` **264095** in all three, matching the figure `docs/data-access.md` already records from the in-game Database screen. Export says `SELECT COUNT(*) FROM teams` = 259. |
| The omission, cross-save | scratch decode of Boston and the Cubs in all three saves: Challenge → Boston `[10948, 9, 203, 206, 1]`, Cubs `[13181, 11, 203, 1, 206]`; Standard → Boston `[10948, 9, 203, 206]`, Cubs `[13181, 11, 203, 1, 206, 1]`; `OOTP-AI` → Boston carries the trailing `1`. Five integers each in the Challenge save and the fourth is `nation_id` on one club and `sub_league_id` on the other. |
| Head field list, 233 records | scratch alignment of every located record against the export: `[city_id, park_id, league_id, sub_league_id, nation_id, human]` with zeros omitted reproduced the byte stream exactly for **232 of 233**; the one miss is the Cubs, where `human_team` and `human_id` are both 1 and only one integer is written. |
| 26 records have no city string | signature scan located 233 of 259 records; the 26 misses are all minor-league All-Star sides whose city name is absent from the byte stream, not empty in it. |
| `division_id` / `allstar_team` / standings | three correlation sweeps (record start, the `cdcdcdcd` marker, the second `.oi` asset name) over windows up to 2,400 bytes at `u8`/`u16`/`u32` → zero exact hits for any of them. The `team_id` positive control also failed from the two body anchors, so the body is variable-shaped and the sweep is **inconclusive, not a proof of absence**. |

## assumed

- The six `u32`s after the header's second wide date are a tail of *this* file, on the
  same footing `parser/saved_games.py` puts its 74-byte tail on. `header.py` says the
  header's true end is `unconfirmed` and I did not change that.
- Field 4 of that tail (121 for `teams.dat`) is a per-record field count. It is constant
  per file type — 121 teams, 13 parks, 33 coaches, 5 names — which is suggestive and not
  a measurement. Labelled `inferred`.
- `BYTE_ACCOUNTING_TIER = "diagnostic"` is declared for a file the walk reads none of.
  The spec pre-registered the tier for a partial *walk*, not for a refusal; diagnostic is
  the only honest one of the two available values, and `TIER_RATIONALE` says so plainly.
- The spec did not say to validate against `players.csv` here and nothing in this phase
  touches ratings, so that rule had nothing to bite on. `ootp_truth_real` was the oracle
  throughout, opened through `connect_truth` (read-only session, asserted).

## surprised-me

- A record file's header tail declares its own record count, and `names.dat`'s value is
  the exact 264,095 the catalog already records from a completely different source. That
  is a free, strong self-check for every future walker and it was three lines away.
- The managed league has **337** teams, not 259. Nothing was going to catch that: the
  only test with a hard count runs against the probe.
- `0xcdcdcdcd` appears inside team records — MSVC's uninitialised-heap fill. Parts of
  this file are a raw struct dump, not a clean serializer's output.
- The trap the brief named landed one level deeper than written: an integer that varies
  across saves and tracks the human club is still not the field, because on the next
  record it is a different field.

## could-not-do

**The record layout is not what Phase 5 was planned against, and this is the blocker.**
`measured` against all three saves with the export as oracle: a team record's integer
fields are written **only when non-zero**. Two records with the same number of integers
can carry different fields. No presence bitmap was found — not in the record, not in the
15 bytes before it (only 8 distinct patterns across 233 records, and MLB clubs and
All-Star sides with different field sets share one), not in the file-level preamble.

Consequences, all of which need the main thread rather than me:

- `division_id` and `allstar_team` were **not located in the file at all**, and both are
  non-optional in the pinned `TeamRecord`. `world.dat` (8.6 MB, not in `SNAPSHOT_FILES`)
  is the obvious home for division membership — that is league structure, not a team
  attribute. **The snapshot file set may need to grow, which is an ADR-adjacent call.**
- The standings region (`pos`, `magic_number`) was not located either.
- 26 of 259 records carry no city string, so even the `verified` five-string signature is
  four strings on those clubs.
- Therefore `tests/test_parse_real_save.py`'s field-by-field clause, the byte-accounting
  walk clauses and both new `test_cross_mode_format.py` clauses cannot be satisfied
  honestly this phase. The tests are **not wrong**; the plan's assumption is. I did not
  edit them — they are in my deny set — and I did not build around them.
- `ingest.py`'s `_resolve_human_team` could not be moved behind the teams walk as the
  spec asked, because `read_teams` refuses. Calling it from `ingest_save` would also have
  turned `tests/test_read_only.py` from a green ADR 0001 proof into an error, which is
  the one signal worth protecting. `human_team_id` stays `None`.
- No destructive git needed; nothing outside the declared allowlist was written.

## docs-delta

For `/update-docs` to route into `docs/data-access.md` §4, which currently records the
5-string signature `verified` and everything else `unconfirmed`:

- **`measured`** — after the two wide dates, every record file carries six `u32`s: write
  hour, minute, second; a per-file-type constant (121 `teams`, 13 `parks`, 33 `coaches`,
  5 `names`); a **record count** (259 teams in both probes, 337 in `OOTP-AI`; 199/267
  parks; 264,095 names — matching the catalog's own name-table figure); and `3289089`.
- **`inferred`** — the per-file-type constant is a field count per record.
- **`measured`** — a team record is `u32 team_id`, then the string signature, then
  integers, then three `u32` ARGB colours. It is preceded by a `0x28` byte, and records
  run in ascending `team_id` order.
- **`measured`, and it downgrades the catalog's optimism** — a team record's integer
  fields are written **only when non-zero**, so the field set is not fixed and the byte
  stream is not self-describing to any reader we have. Evidence: `[city_id, park_id,
  league_id, sub_league_id, nation_id, human]` with zeros dropped reproduces 232 of 233
  records exactly, and the same five-integer run means different fields on two clubs in
  one file.
- **`measured`** — the five-string signature is **four strings on the 26 minor-league
  All-Star sides**: the city name is absent from the stream, not empty in it.
- **`unconfirmed`, and now a named task** — `division_id`, `allstar_team` and the
  standings region are not in `teams.dat` anywhere the sweeps looked. `world.dat` next.
- **`measured`** — `0xcdcdcdcd` (MSVC uninitialised-heap fill) appears inside team
  records, so parts of the file are a raw struct dump.

## still-open

- **Phase 5 needs re-planning, and the shape of the re-plan is a main-thread call.** Two
  branches I can see: widen the phase to `world.dat` and solve the presence mechanism, or
  narrow the Phase 5 field set to what the head yields unambiguously and amend the tests.
  I took neither — both edit files in my deny set.
- I read the smaller interpretation of "land the team dimension" throughout: no
  heuristic decode. A walker that guessed which integer is `sub_league_id` would have
  matched the export on the standard probe — the save it was fitted to — and been wrong
  on the league we manage, with a green test behind it.
- `snapshot.py` still copies three files. If `world.dat` is needed, that list and the
  ~46 MB figure in the plan both move. Nothing user-run was produced.
