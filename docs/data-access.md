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
| `world.dat` | ~8.6 MB | Nations, states, cities |
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
itself** as a length-prefixed string (e.g. `deverra01`), ~1,712 unique values,
each appearing twice per file.

`inferred` — This cross-walks OOTP league state to Retrosheet, the Chadwick
Register, FanGraphs, and Baseball Savant. Real-world priors on real players are
available to us and not to the in-game AI.

`unconfirmed` — Whether generated (fictional) players receive any stable external
identifier. Observed real-player IDs number ~1,712 against ~18,000 active
players, so most players almost certainly have none.

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
logo filename, full name) followed by team colors as u32 ARGB. All 30 MLB clubs
extract cleanly with correct abbreviations and colors.

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
The two `u32`s at +4 and +8 are the plausible home of the name indices — both fall inside
`names.dat`'s index range — but that is `unconfirmed`, and *which* is first and which is
last is not established at all.

**After `experience`, the record uses the same drop-zero encoding `teams.dat` uses** — a
field whose value is falsy is not written. The natural experiment: `last_team_id` sits
immediately before `team_id`, and for a player who never changed clubs it is absent, so
`team_id` lands four bytes earlier. `measured` — `team_id` sits at record+58 for 86.9% of
rostered players and record+62 for the rest, splitting exactly on that. **Reading
`team_id` at a constant offset therefore scores ~87%**, which is high enough to pass a
spot-check and wrong for one club in eight. `team_id`, `organization_id`, `league_id`,
`position`, `role`, `bats`, `throws` and `historical_id` all live past that boundary and
are consequently **not yet readable**.

**The age byte is an invariant, not just a field.** `measured` — it equals the whole years
between `date_of_birth` and the save's sim date, exactly, for all 18,072 records with zero
exceptions. That three-way agreement is what makes record framing exact on a file with no
declared count: an ascending id plus a parseable date alone accepted a false record start
and silently truncated a walk to 2,693 records, with every field it did read decoding
perfectly.

### Names are indirected

`verified` — Player names are **not** stored in `players.dat`. It holds indices
into `names.dat`, a ~264,095-entry string table (the count cross-checks against
the in-game Database screen). Searching `players.dat` for a player's surname
returns only their Twitter handle.

`unconfirmed` — The index encoding and the `names.dat` table layout. Resolving
names requires a two-file join that has not been built.

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
