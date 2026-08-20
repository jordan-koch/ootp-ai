# Data Access

What can be read out of Out of the Park Baseball 25, from where, and how much we
actually know about it.

**Every claim here carries an epistemic label.** They are not decoration:

| Label | Means |
|---|---|
| `measured` | Observed directly from the bytes/files on disk, with the observation reproducible |
| `verified` | Measured *and* cross-checked against an independent source (in-game UI, shipped CSV, known real-world value) |
| `inferred` | Follows from measurements, but the inference itself has not been tested |
| `assumed` | Believed on the basis of convention or a single example; no evidence gathered |
| `unconfirmed` | Nobody has looked. **An unconfirmed claim is a task, not a fact.** |

Findings dated 2026-08-15 unless noted, against **OOTP 25** (`ootp25.exe`,
header version byte `0x19` = 25). Nothing here is guaranteed across a game patch —
see §8.

Paths are written as `$OOTP_INSTALL` / `$OOTP_SAVED_GAMES`. This repo is public;
see [`.env.example`](../.env.example).

---

## 1. Where saves live

`verified` — Saves are **not** under the Steam install. On Windows they land in
the user's Documents folder, which is frequently **OneDrive-redirected**:

```
$OOTP_SAVED_GAMES/
├── <League Name>.lg/          one directory per save
└── saved_games.dat            the save index
```

`measured` 2026-08-16 — **corrected.** This entry previously read `verified` and claimed
the index was *"plaintext … readable without parsing."* It is not. `saved_games.dat` is a
record file like every other: the standard header, a 74-byte file-level tail, then one
variable-length record per save built from u32-LE length-prefixed strings at **unaligned**
offsets — so a u32 scan misses them and a substring scrape finds them only by luck. It is
walked with zero residual over 2,070 bytes for three saves. Field table in the module
docstring of `src/ootp_ai/parser/saved_games.py`.

Two consequences worth carrying: it embeds an absolute user-profile path **four times per
save record**, not once; and it carries **no team id** — the human club appears as a
display name and a logo filename only, so an id must come from `teams.dat`.

`measured` 2026-08-18 — **`saved_games.dat` is the authority for a save's sim date, and
the in-game Organization screen is not.** That screen's header shows
`YESTERDAY / TODAY / TOMORROW` as *labels* against game results; its first row carrying an
actual date is the **fourth** day, three days ahead of today. Today's date is never
displayed there at all. Reading that row as the current date produced three wrongly-named
operator screenshots — off by 11, 4 and 11 days — before it was caught. The index's own
per-save dates are `OOTP-AI` 2024-03-07 and both test saves 2024-03-18, cross-checked by
weekday arithmetic against those same screenshots. **This matters beyond filenames:
`sim_date` is a key column in every bronze table, so a screen-read date would key the
warehouse three days into the future.**

Each `.lg` directory holds (`measured`):

| File | Size (example) | Content |
|---|---|---|
| `players.dat` | 25.7–32.1 MB | Player records — ratings, contracts, stats (see §4) |
| `teams.dat` | ~4.5 MB | Team records |
| `retired.dat` | ~130–150 MB | Retired players |
| `world.dat` | ~8.6 MB | Nations, states, cities — **and** the league → sub-league → division nest and the 3,058-entry league calendar (`measured`, Phase 5b) |
| `names.dat` | ~8.6 MB | Name string table |
| `coaches.dat` | ~2 MB | Coaches and staff |
| `scouting.dat` | ~2.3 MB | Scout-perceived ratings (see §5) |
| `parks.dat` | ~450 KB | Ballparks |
| `challenge.dat` | 241 B | Challenge-mode integrity hash |
| `temp/text_data.sqlite3` | ~9.7 MB | **Real SQLite** — news/history text |
| `import_export/` | — | Destination for in-game exports (see §6) |
| `news/html/` | — | Generated HTML reports (see §7) |

A full `.lg` directory is **~600 MB** (the managed league is ~727 MB). `inferred` —
snapshotting it per sim date onto cloud-synced storage would be a mistake;
snapshots belong on local disk.

`measured` — **a `*.lg` glob is not a list of saves.** The saved-games directory
contains a stray, empty directory literally named `.lg`, which matches the pattern
and is not a save. A save enumerator must confirm contents — `players.dat` and
`teams.dat` at minimum — rather than trusting the name.

`measured` — `challenge.dat` is present at exactly **241 bytes** in a Challenge
Mode save and absent otherwise, and such a save's `import_export/` directory
exists but stays empty. Either is a cheap filesystem-level check for the mode,
without opening the menu.

---

## 2. Shipped reference data — `$OOTP_INSTALL/data/database/`

This is the game's own reference corpus. It is **static**: it ships with the game
and does not change as a league is simulated.

### `players.csv` — the Rosetta Stone

`verified` — ~12,855 rows, one per real player in the shipped 2024 database.
Comma-separated with a `//`-prefixed header line. Carries **raw ratings on the
internal scale** (roughly 1–1000), not the lossy 20–80 / 1–100 display scales.

Columns include (`measured`): identity and biography; `Contact/Gap/Power/Eye/
Avoid K/BABIP` split three ways (`vL`, `vR`, `Pot`); pitching ratings and a
12-pitch arsenal with potentials; fielding by position plus position experience;
personality; a 10-year contract array and a 10-year extension array; injury
proneness; and a large block of cross-reference IDs.

**This file is what makes the binary parseable.** Aligning a known player's CSV
values against `players.dat` locates the corresponding field offsets. See §4.

`verified` — It is a **day-0 snapshot only**. It never updates. It cannot serve
as a live feed, and using it as one would silently serve stale data.

### Cross-reference IDs — the join to real baseball

`verified` — `players.csv` carries `LahmanID`, `RetroID`, `BBRefID`,
`BBRefMinorID`, `gracenote_id`, `chadwick_id`, `mlb_id`, `fangraphs_id`, and
others. `verified` — the **Lahman/BBRef ID is also embedded in `players.dat`
itself** as a length-prefixed string (e.g. `deverra01`), readable by
`ootp_ai.parser.players.read_players` and exact against every `retired = 0`
export row. `measured` 2026-08-18 — the earlier "~1,712 unique" undercounted:
the probe save holds **1,920** nonempty values (matching the export's 1,920
exactly) and the managed league holds **2,137**, all distinct, all
Lahman-shaped. Each value's second occurrence sits ~300–450 bytes deeper in the
**same record**, not elsewhere in the file.

`inferred` — This cross-walks OOTP league state to Retrosheet, the Chadwick
Register, FanGraphs, and Baseball Savant. Real-world priors on real players are
available to us and not to the in-game AI.

`verified` — Generated (fictional) players carry **no** external identifier:
their `historical_id` is a zero-length string — structural absence, an empty
string rather than a missing field — covering ~90% of the population. A join on
this key silently drops the fictional majority, so it is an attribute, never a
serving-path join key.

### Engine constants

`measured` — These are the simulation's own tuning tables, not schema:

| File | Content | Why it matters |
|---|---|---|
| `financials.txt` | Salary tiers by year and player quality (`super star` … `poor`) | OOTP's own contract valuation model |
| `era_ballparks.txt` | Park factors w/ dimensions, wall heights, **LH/RH splits** | Lineup and acquisition analysis |
| `era_stats.txt` | League offensive environment by year (OBP, SLG, R/G, ERA, WHIP) | Normalization baselines for rate stats |
| `total_modifiers.txt` | Per-year simulation modifiers | Projection calibration |

`inferred` — Using the engine's published constants beats fitting our own models
against simulated outcomes.

### Dimension data

`measured` — `names.xml` (~37 MB, multi-language with nationality distributions),
`world_default.xml` (~19 MB — nations, states, ~94k cities), `schools.xml`
(~8.4 MB), `team_nick_names.xml`, `major_league_baseball.json` (league structure).

### Schema documentation

`measured` — `db_structure_ootp22_csv.txt` documents **70 tables** with field
names in order, for the CSV export path. `db_structure_*_mysql.txt` and
`*_access.txt` cover the SQL dump variants. These are genuine schema docs and
carry no data.

`inferred` — The binary serialization order tracks the documented CSV field order
closely enough to be useful as a map, but not closely enough to trust blindly.

---

## 3. The SQLite database

`verified` — `<save>.lg/temp/text_data.sqlite3` is a real, queryable SQLite file.
16 tables, all text/news content:

`measured` — On a freshly created save, only `player_history` is populated
(76,401 rows across 26,308 players — transaction and draft log lines). Every
other table (`league_news`, `league_transactions`, `team_news`, `game_logs`,
`league_injuries`, drafts, `team_development`) is at **0 rows** until the league
is simulated.

`verified` — The row count cross-checks exactly against the in-game Database
screen (`Player_history records = 76401`).

`unconfirmed` — Whether OOTP holds a write lock on this file while the game is
running. Read with `mode=ro` and expect to need the game closed.

---

## 4. The binary `.dat` format

`verified` — Not compressed, not encrypted. Entropy 4.5–5.6 bits/byte with 17–38%
printable bytes — nowhere near the ~8.0 of compressed or encrypted data.

### Header

`measured` — byte-for-byte against `players.dat` and `teams.dat` in an OOTP 25
save, identical in both:

```
offset  0 : u8       0x00               leading null — NOT part of the magic
offset  1 : char[4]  "OOTP"             magic
offset  5 : u32      25                 version (0x19) — the version guard's anchor
offset  9 : u32      11
offset 13 : u32      104
offset 17 : u32      84
offset 21 : u32      1
offset 25 : char[]   filename            null-padded, e.g. "players.dat"
```

> **The magic begins at offset 1, not offset 0.** A reader that checks
> `data[0:4] == b"OOTP"` sees `\x00OOT` and rejects a valid save; one that reads
> the version as a u32 at offset 4 gets 6480 rather than 25. Both fail loudly,
> which is the tolerable outcome — but both fail, and on the first file opened.

`measured` — the header names its own file (`players.dat`, `teams.dat`). That is
a cheap cross-check that the file on disk is the file we think we opened.

### Primitives

| Type | Encoding | Evidence |
|---|---|---|
| String | u32-LE length prefix, raw ASCII, **no terminator** | `verified` — `06 00 00 00` + `Boston` |
| Date | `u8 day, u8 month, u16 year` | `verified` — `18 0a cc 07` = 24 Oct 1996, matches the UI |
| Color | u32 ARGB | `verified` — `0xffbd3039` = `#BD3039`, the correct Red Sox red |
| Rating | u16, internal ~1–1000 scale | `verified` — aligned against `players.csv` |
| Money | u32 (whole dollars) | `verified` — `e0 9d a3 01` = 27,500,000 |
| Stat / salary series | IEEE 754 f64 in year-keyed blocks (year as u16) | `measured` |

### Record structure

`verified` — Records contain **variable-length regions** (contract arrays, stat
history, name-dependent strings). Two saves carrying the same player had the
ratings block at different distances from both a leading and a trailing anchor.

> **The parser must walk records sequentially. It must never seek to a fixed
> offset.** A table of hardcoded offsets will appear to work on a day-0 save and
> break silently on the first player with a different contract length.

`verified` — Field **order** is stable across saves, and the ratings sub-block is
byte-identical in internal layout (stride pattern `+2,+2,+2,+2,+3,+2,…`). A
parser built against one save's ground truth transfers to another.

### Confirmed field semantics

`verified` — For `players.dat`, aligned against `players.csv`: Player ID (u32),
date of birth, uniform number, the 18-value rating block (`vR` group, then `vL`
group, then potentials, contiguous u16), the contract salary array, contract
signing date, contract end year, and the Lahman ID string. Twitter handle is a
length-prefixed string (it is *not* a name — see below).

`verified` — For `teams.dat`: a 5-string signature (city, abbreviation, nickname,
logo filename, full name) followed by three u32 ARGB colors. **Scope corrected
2026-08-19: all 259 clubs, not the 30 MLB ones** — Phase 9's differential compares
every landed team column against `ootp_truth_real.teams` on every record, so the
claim now rests on the whole file rather than on the league we looked at first.

`verified` — **Two of the three color slots are identified**, measured over all 259
clubs against every color column the export exposes: the **first** equals
`background_color_id` and the **third** equals `text_color_id`, 259 of 259 each. Alpha
is `0xff` on every slot of every record, so the comparison checks it rather than
masking it — a walk reading one byte early would otherwise match any club whose color
survived the shift.

`measured` — **The middle color slot is not identified.** Its best candidate,
`ballcaps_visor_color_id`, reaches 237 of 259 and nothing reaches 259. It is
deliberately excluded from the differential: comparing it against a near-miss would
ship a 22-row failure as the harness's normal state, and an allowlist entry would be an
allowlist standing in for an unfinished decode. The next attempt starts from 237.

`verified` — **`teams.historical_id` IS carried by the export**, 30 of 30 non-empty
values exact. `contracts/field_map.toml` asserted the opposite for months and Phase 9's
differential caught it; the correction is recorded here because a *refuted* claim is
more useful written down than deleted. The other 229 clubs have no real-world
counterpart: the save carries nothing, the export writes `''`, and a bounded rule covers
exactly those 229. Note the asymmetry with the player-level field, which lands `""` for a
fictional player and reserves NULL for an undecoded tail — two facts the player walk
keeps apart and the team walk has no way to distinguish.

`verified` — `parent_team_id` now carries export-exact evidence on all 259 clubs in
addition to the mutual-link derivation that produced it. The derivation still matters:
it is the only check available on a Challenge-mode save, where there is no export at all.

`unconfirmed`, and **reaffirmed** 2026-08-19 rather than upgraded — three fields the
differential compares and still cannot settle, because the oracle cannot discriminate:
`team_human_flag` (both `human_team` and `human_id` are 1 on the single managed club and
0 everywhere else, so 18 field orders fit equally well), `human_manager_team_id` (three
consecutive identical `u32`s; nothing says which slot is which), and
`calendar_real_sim_date` (exact on all 3,058 events — and 0 on **both sides of every
row**, so a parser reading an adjacent zero scores identically). A green comparison is
not evidence when the answer key holds one value.

`unconfirmed` — Everything else. The overwhelming majority of both files is still
unmapped.

### `players.dat`: the population, the missing count, and the fixed head

All `measured` 2026-08-18 against `ootp_truth_real` and all three saves on disk, by
`src/ootp_ai/parser/players.py`.

**The file holds more players than the export does, and the difference is not slack.**
`measured` — 18,077 records against the export's `retired = 0` population of 18,072.
The five extras are `player_id` 42001, 49008, 50468, 50469 and 132324, and **none
appears anywhere in the export at any `retired` value.** They are real records, not
mis-framed bytes: each carries the same 26-byte padding every record does, each has an
ordinary length (1,152–1,320 bytes), each has a coherent birth date, age, nationality,
height and weight, and the same five ids appear in **both** test saves. The relationship
is a strict superset. On the evidence — blank uniform numbers, ages 18 to 25 — they look
like an unrevealed amateur or international pool; *which* filter the export applies is
`unconfirmed`. **The practical consequence: "row count equals 18,072" is the wrong
assertion, and a coverage statement built on it describes a population the warehouse does
not hold.**

Since Phase 9 those five are pinned **by id** rather than by count
(`validate/export_diff.py::PARSED_ONLY_PLAYER_IDS`), because a count of five also passes
for a walk that lost five real players and invented five garbage records — a mis-framing
that shifts identity need not drop a row.

**The file does not declare its record count.** `measured`, all three saves — where
`teams.dat` puts a record count in the fifth `u32` of its header tail, `players.dat` puts
`0xFFFFFFFF`. A walk over this file therefore has **no in-file oracle** to check its own
framing against, which is why its byte accounting is weaker than `teams.dat`'s and why
the managed league, having no export either, relies on a record-boundary check alone.

**The record head is fixed for 37 bytes; the drop-zero region begins after it.**
`verified` against **every** `retired = 0` export row (18,072 of 18,072, exact match, not
sampled): `u32 player_id`, then two `u32`s, then `date_of_birth` (`u8` day, `u8` month,
`u16` year), `u8 age`, `u8 nation_id`, `u32 city_of_birth_id`, `u16 weight`, `u8 height`,
`u8 uniform_number`, `u8 experience`, with four short unclassified spans between them.
The two `u32`s at +4 and +8 are `first_name_index` and `last_name_index`, in that order —
`verified` 2026-08-18 against all 18,072 export rows. They were `unconfirmed` until
Phase 7 scored every candidate mapping across the full population rather than reading the
bytes: `+4` as first and `+8` as last matched **18,072 / 18,072 = 100.00%**, the opposite
assignment matched **1 / 18,072**, and neither direction left an index unresolved. See
*Names are indirected* below.

**After `experience`, the record is presence-mask-governed, and it is decoded through
the identity tail.** `verified` 2026-08-18 against every `retired = 0` export row: the
byte at record+55 is a six-bit mask over the club-assignment `i32`s (`team_id`,
`organization_id`, `league_id` and their `last_` twins, written in bit order, absent
means zero); record+56's bit 0 is `free_agent` and its bits 2–7 govern six optional
fields in ascending bit order (nickname index, second nation, two language ids,
`bats`, `throws`); record+57 is a third mask (bit 1 a required sentinel, bit 2 one
unclassified byte, bit 5 a loan `u32`); then `historical_id` and `historical_team_id`
follow as consecutive length-prefixed strings, empty-string for players without one.
The original natural experiment stands as the warning: `team_id` sits at record+58 for
86.9% of rostered players and record+62 for the rest, so **a constant-offset read
scores ~87%** — high enough to pass a spot-check and wrong for one club in eight.

**A second elision pattern exists: drop-DEFAULT.** `verified` — `bats` and `throws`
are never zero; the writer instead elides the majority value **1** (right-handed),
with the presence bit carrying the elision. A drop-zero scorer structurally cannot
find such a field — the mask bit, not the value rule, is the invariant to hunt first.

**Still not readable: `position` and `role` — and the export's closer role is not in
the file.** `measured` — the save stores 12 (RP) in the role byte for 197 of 229
export closers, so the export's `role = 13` appears **derived** from depth-chart data
outside `players.dat` (`inferred`). The four `prone_*` bytes sit 13 bytes past
`historical_team_id` (byte-exact on all 18,072 rows; ratings-adjacent, withheld), and
`hsc_status` sits beside the role byte within the one decoded shape group — both
located, neither landed.

**The age byte is an invariant, not just a field.** `measured` — it equals the whole years
between `date_of_birth` and the save's sim date, exactly, for all 18,072 records with zero
exceptions. That three-way agreement is what makes record framing exact on a file with no
declared count: an ascending id plus a parseable date alone accepted a false record start
and silently truncated a walk to 2,693 records, with every field it did read decoding
perfectly.

### The roster-membership grain spans two files

`verified` 2026-08-18 — `team_roster`'s `(team_id, player_id, list_id)` triple is
recoverable **exactly** from save structure: a per-player **roster-status byte** in
`players.dat` (22 bytes past `historical_team_id`; bit 2 = org-top-club active,
bit 3 = secondary/40-man, bit 4 = injured list, bit 5 = 60-day placement) combined
with the **membership array** each `teams.dat` record carries, consumed as a
multiset. `ootp_ai.parser.rosters.read_rosters` reproduces the export 15,672/15,672
and reconciles every club's array against the reconstruction, refusing on any
disagreement.

`measured` — the membership array (stride-4 `u32`s, ~record+1150..1520, moves per
team) equals the club's roster rows plus one entry per assigned-but-unrostered
player, on every club of every save. **Its order is container noise and carries no
information**: the two test saves hold identical Boston rosters serialized in
different orders, so no positional decode exists — recorded so no later session
re-attempts one. The multiplicity is load-bearing: only it distinguishes a
rostered-but-inactive minor leaguer from an active one, a state with 154 instances
in the managed save and zero in either test save.

`measured` — the **176 assigned-but-unrostered players** (rendered with a negative
`league_id` by the exporter; the save stores it positive) are marked by
`last_organization_id == own organisation` + `last_league_id == 234` + a zero status
byte. This is a **day-0 fact**: after a cross-organisation transaction, rostered
players with a non-zero `last_organization_id` will exist, so the parser matches the
full signature or refuses — re-measure the marker at the first post-transaction
snapshot.

`measured` — two more structures bound the array inside a team record: the club's
**coaching-staff id array** immediately after it (Boston standard: 10 ids, exact set
match against the export's `coaches` for team 4, owner and GM included), and the
**depth-chart/lineup region** at ~record+260..990 (four lineup groups of
`u32 player_id + u8 fielding position` at stride 5 near record+800) — the likeliest
home of the derived closer role above. Located, not decoded. And per club,
`list2 = list1 − list4 − {1}-only` holds with zero exceptions in the export.

### Names are indirected

`verified` — Player names are **not** stored in `players.dat`. It holds indices
into `names.dat`, a **264,095**-entry string table (the header declares that count,
the walk frames exactly that many, and it cross-checks against the in-game Database
screen). Searching `players.dat` for a player's surname returns only their Twitter
handle.

`verified` 2026-08-18 — **The index encoding and the table layout.** The join is built
(`ootp_ai.parser.names`) and resolves every name of all 18,072 `retired = 0` export rows
exactly. The record is a `u8` category, a `u32`-length-prefixed name, a `u32` that is
always zero, the `u32` index, a `u32` usage count and that many `(u32, u32)` pairs. The
walk is **strict** — zero residual on all three saves.

Four things about it are worth carrying, because each is a trap someone else would
otherwise re-enter:

- **The category byte LEADS its record.** Read as a trailing separator the walk finds
  264,094 records with 8 bytes left over, and mis-stops at index 31,877 — the Dutch
  surname `'t Hart`, whose first character *is* an apostrophe (`0x27`), the value the
  byte itself takes in the preceding block. A separator that collides with real data is
  not a separator.
- **There is ONE index space**, not a first-name and a last-name table. Indices run
  1..264,095 with no reset, and **510 of them serve as a first name for one player and a
  last name for another**, resolving correctly through the same table in both roles.
- **The category byte is `unconfirmed` and is not a first/last discriminator**, despite
  looking exactly like one: indices 1..31,876 are `0x27` and 31,877..252,899 are `0x07`,
  which read as a given-name block and a surname block. Of the indices players use as a
  **last** name, 6,668 point at `0x27` records.
- **Encoding is latin-1** (`verified` on the same 18,072 rows). 1,621 entries carry a
  byte above 0x7F, so strict ASCII refuses the file; cp1252 scores identically on every
  name a player carries.

`measured` 2026-08-18 — **The table is the same in all three saves.** The files are
8,642,110 bytes each with three *different* SHA-256 digests, but their record bodies are
byte-identical; the digests differ only in the header, at the sim date and the wall-clock
write time. Treat this as a fact about shipped data rather than an invariant — a patch, a
mod or a custom name master would break it, and the parser keeps the table a per-save
object for that reason.

⚠️ **`players.csv` is not an exact answer key for names.** It ships **pure ASCII**, with
every accented character already replaced by `?` — the file literally contains `Rod?n`.
Validating a name against it requires the same fold; see AC8 in the `first-sight`
`PROJECT_SCOPE.md`. This is the mirror of the export setting at the *Replace accents* row
below, and it is the shipped file's property, not something a run can turn off.

### `world.dat` — one record, entered by landmark, mostly unread

**There is no `leagues.dat`.** The league structure lives here, and this section replaces
the assumption that it did not.

`measured` 2026-08-19 — **The file is 8,898,534 bytes in the managed league and 8,657,715
in the probe, and declares exactly ONE record.** That single fact drives the whole reading
strategy: a one-record file has no record loop to walk and no count to iterate, so a
sequential walk from the header reaches the interesting regions only by crossing megabytes
of undecoded bytes. The walker instead **enters at landmarks** — unique byte patterns it
requires to resolve to exactly one position, refusing rather than guessing when a pattern
matches zero times or several.

`measured` — **The walk therefore reads 199,832 bytes and leaves ~8.5 MB untouched**, and
the walked span is *identical* in both saves. That is why the byte-accounting tier is
**`region-accounted`** rather than strict or diagnostic: "residual" is not the right
question for a walk that never claimed to read the file. Zero residual is required *within*
each region, each region's own declared count must match what the walk produced, and the
un-walked remainder is recorded as a number rather than waved at. The tier vocabulary
(`tests/fixtures/tiers.py`) keeps `region-accounted` a separate word from `diagnostic`
precisely so the weaker claim cannot be read as the stronger one.

Two regions are mapped, and both land in the warehouse.

`verified` 2026-08-19 — **The division hierarchy.** The nest is
league → sub-league → division → `u32` count + an explicit `team_id` array, and the array
is the point: a division that knew only its own id would prove nothing. It reproduces the
export's club-side `division_id` exactly, which is worth more than an ordinary match
because **the two were written from opposite sides** — ours from the league's membership
array, the export's from each club's own record.

⚠️ **`teams.dat` does not carry `division_id` at all** — `measured`, 0 of 140 on the clubs
that have a non-zero one. A division stamped onto a team record could therefore only have
come from a join, so `bronze_division_team` is the warehouse's **only** division source and
`teams.division_id` is a silver derivation.

**Reach: MLB's six divisions and its thirty clubs, and no further.** The other fourteen
leagues each sit behind their own unmapped scalar block. Thirty rows against a club count
of 259 (probe) or 337 (managed) is the documented reach of the walk, not a parse fault.
The four All-Star sides appear in no division array at all and are **structurally absent —
a missing row, never division zero**, because `division_id` counts from 0 within its
sub-league and East really is division 0.

`verified` 2026-08-19 — **The league calendar.** 3,058 entries in every save on disk,
spanning 60 distinct `league_id` values, of which **2,259 (managed) / 2,492 (probe) carry a
`deleted` flag**. Bronze lands all of them; a walk that dropped the deleted ones would
return 566 rows and look perfectly consistent. Eight of its nine fields match the export
row for row.

Two traps in that record, each one someone else would otherwise re-enter:

- **The key is the file's own `seq`, which the export does not expose.** The readable
  alternative — `(league_id, start_date, event_type, name)` — collapses 3,058 rows to
  2,600, losing 458 with nothing raised. The key had to be settled from the bytes because
  the answer key has no column for it.
- **`year == 0` is legitimate here**, and is rejected in `players.dat` for the opposite
  reason. A calendar record with no date is structural absence; a player record framed on
  a zero year is a mis-frame. A landing that refuses the zero rather than storing NULL
  turns one absent date into a failed ingest.

`unconfirmed` — **`real_sim_date`**, the `u16` closing each event, reads 0 on all 3,058
entries of all three saves **and** 0 in the export. A row-for-row match therefore proves
nothing about it: a parser reading an adjacent zero `u16` scores identically. It lands, and
`contracts/policy.py` renders it only behind an uncertainty banner until a mid-season save
with a partially-simulated calendar says what it means.

**Still unread: the ~1,200-byte scalar block holding the league rules themselves** —
roster limits, service-time thresholds, the schedule shape. That block is what
[`league-rules.md`](league-rules.md) §1 would be verified against, which is why that
verification remains deferred rather than merely unscheduled.

---

## 5. Ratings are shown through filters — a correctness trap

`verified` — In-game rating displays pass through **two** lossy transforms before
reaching the screen:

1. **Scale conversion.** The player page renders 20–80; the Top Prospects report
   renders 1–100; storage is ~1–1000. Three different numbers for one value.
2. **Scout filtering.** The player page has an `OSA Ratings` / `Head Scout`
   toggle and a `Scouting Accuracy` field. A separate ~2.3 MB `scouting.dat`
   exists.

`inferred` — The save therefore holds *true* ratings and *scout-perceived*
ratings as distinct values, and an in-game screenshot generally shows the latter.

### There are three rating views, not two

`measured` — The export configuration screen (§6) names **three mutually
exclusive** rating views, plus an independent fourth option that adds a further
set of columns. That is the sharpest evidence available that the game
distinguishes:

| View | What it is | Who holds it in-world |
|---|---|---|
| **Real** | True ratings | Nobody |
| **OSA** | The in-game public scouting service | Every club, identically |
| **Scouted** | This organization's own read, at its staff's resolution | Us |

`inferred` — The middle tier is **public record**. OSA is published and every club
sees the same numbers, so it does not sharpen when we hire better scouts. The gap
between OSA and the organization's own read is therefore an observable measure of
what the scouting department adds
([ADR 0014](decisions/0014-staff-is-the-information-channel.md)).

> **Never use a screenshot rating as ground truth for field mapping.** Matching
> a displayed value to a byte can identify the wrong field with no error
> surfaced. Use `players.csv`, which is raw and unfiltered.

### The critical-path task

`unconfirmed` — **Which file holds which view, and whether the scouted view is
stored at all.** If OOTP computes it at render time from true ratings plus a
scout-accuracy seed, the parser cannot reproduce it, and
[ADR 0012](decisions/0012-scouted-ratings-only.md) and
[ADR 0014](decisions/0014-staff-is-the-information-channel.md) have no data path —
the front office would be able to read the answer key and nothing else.

`inferred` — `scouting.dat` at ~2.3 MB across ~18,000 players (~128 B each) is
consistent with a stored per-player block. That is a guess, not a finding.

The test: export real *and* scouted ratings together (§6), then search
`scouting.dat` for the exported scouted values. Found → stored, and the parser has
its source. Absent everywhere → computed, and there is a design problem to solve
before any rating can be served.

---

## 6. The in-game export — gated in Challenge Mode

`verified` — Under **Database Tools** on the Database screen, OOTP 25 offers six
export actions: `Configure SQL dump for MS Access`, `Configure SQL dump for
MySQL`, `Configure data export to CSV files`, `Create SQL dump for MS Access`,
`Create SQL dump for MySQL`, `Export data to CSV files`, and `Export data
directly into a MySQL database`.

`verified` — **In a Challenge Mode save, all six are hidden.** The menu otherwise
reproduces the game's own translation-file ordering exactly, with only that
consecutive block absent; `Open data import/export folder` survives. Confirmed by
comparing the same menu in a standard save, where all six appear.

`measured` — Automatic export scheduling ("Automatic Data Dump Settings") offers
**monthly and yearly only**. There is no daily option.

`inferred` — The export cannot be the ingestion path for this project: the target
league is Challenge Mode (ADR 0003), where it does not exist, and even where it
does exist its cadence ceiling is a manual click. See ADR 0002.

Its remaining legitimate use is as a **one-time ground-truth artifact from a
disposable standard-mode save**, used to validate the parser.

### Export configuration

`measured` — The MySQL/CSV export configuration screen carries the options below.
The three `Show … ratings` entries are **mutually exclusive**; `Additional
complete scouted ratings` is independent and combines with them.

| Option | Disposition for ground truth |
|---|---|
| `Show OSA player ratings` | The public scouting service's view (§5) |
| `Show real player ratings` | True ratings — the answer key |
| `Show no player ratings` | Ratings omitted entirely |
| `Additional complete scouted ratings` | Adds the organization's own scouted view alongside |
| `add full message text to messages table` | **On** — this is the news/message body text |
| `Replace accents` | **Off** — mangles names and breaks validation against `names.dat` |
| `Use INSERT IGNORE commands` | **Off** — silently drops rows from a reference that exists to be trusted |
| `Include field names in inserts` | **On** — without it columns are positional, which is the fixed-offset failure in SQL form |
| `Insert NULL if empty` | **On** — `NULL` and `''` are structural absence vs. empty, and conflating them produces wrong aggregates |
| `Insert DROP TABLE command` | Safe only in a dedicated schema — see the warning below |

`measured` — `Show real player ratings` together with `Additional complete scouted
ratings` exports successfully, yielding both views for the same rows out of one
snapshot. **That is the artifact that resolves §5**, and it is why the two views
need no alignment work: they come from a single export of a single league state.

`verified` — True ratings in a ground-truth export are sanctioned. ADR 0012 permits
them "in tests against fixtures, never in the advisory path." They live in the
ground-truth schema and the test suite; nothing in the serving layer joins to them.

> **The export never writes to the warehouse schema.** `ootp` belongs to the parser
> ([ADR 0004](decisions/0004-mysql-warehouse.md)); ground truth lands in its own
> schema, only ever from a disposable standard-mode save. Two reasons, and the
> second is louder: mixing them destroys the provenance line that makes a data
> incident triageable, and with `DROP TABLE` enabled a second export into a shared
> database **destroys the first**. One schema per export variant.

---

## 7. HTML reports

`verified` — `<save>.lg/news/html/` receives generated reports. Tables are clean
`<table class="data sortable">` markup, and **OOTP's internal IDs are embedded in
the hrefs** (`player_47035.html`, `team_3.html`).

`inferred` — This is a viable secondary ingestion and ground-truth path that
works inside Challenge Mode, since report generation is not a commissioner tool.
Ratings in reports are scale-converted (see §5).

`unconfirmed` — Which reports can be generated on demand vs. only at the annual
almanac, and whether the full site (standings, box scores, transactions, player
pages) can be produced without the almanac. The nav links in a generated report
reference all of these, but only the one requested report was written to disk.

---

## 8. Durability of all of this

`assumed` — None of the byte-level findings survive a game patch by right. The
header carries a version byte (`0x19` = 25); a format change would most likely
bump it, but that is untested.

`inferred` — The mitigation is that `players.csv` ships alongside the binaries
and is patched with them, so it re-derives the ground truth needed to re-map the
parser. The Rosetta Stone renews itself.

`unconfirmed` — Whether OOTP 26 changes the layout at all.
