"""`players.dat` — a sequential walk of the largest file this project reads.

**Read this docstring before the code.** Three things about this file are not what a
reader would assume, and each one is a silent-wrongness bug if assumed wrong.

## 1. The file does not declare how many records it holds

`teams.dat` puts its record count in the fifth `u32` of the header tail, and
`teams.py` uses it as a loop bound — so a mis-framed file runs out of records and
raises rather than returning a short league. **`players.dat` puts `0xFFFFFFFF` there**,
`measured` in all three saves on disk. That is a sentinel, not a count.

The consequence is structural: **this walk has no in-file oracle.** It cannot assert
"I framed as many records as the file says exist", because the file says nothing. What
it can assert is that the walk terminates on a record boundary having consumed the
buffer, and it reports the count it reached so a caller with an independent count — the
export, for the one save that has one — can compare. Anything stronger would be a claim
the bytes do not support.

### …and the export is not that oracle either

The plan assumed `players.dat` holds exactly the export's `retired = 0` population of
18,072. **`measured`: it holds 18,077**, and the five extras are not a rounding error in
the reading — they are `player_id` 42001, 49008, 50468, 50469 and 132324, and **none of
them appears anywhere in the export**, at any `retired` value.

They are real records rather than mis-framed bytes, on four independent grounds: each is
preceded by the same 26-byte padding every other record is; each has a record length
(1,152 to 1,320 bytes) squarely inside the normal distribution; each carries a coherent
birth date, age, nationality, height and weight; and **the same five ids appear in both
test saves**. A false frame satisfies none of that, let alone all of it twice.

So the relationship is one of **strict superset**: the parse contains every export row
and five the export does not know about. The reading that fits is that the game's DB
export applies a filter this file does not — the five look like an unrevealed amateur or
international pool, on the evidence of blank uniform numbers and ages 18 to 25 — but *which*
filter is `unconfirmed` and nothing here depends on knowing. What matters downstream is
that **"row count equals 18,072" is the wrong assertion**, and a coverage statement built
on it would describe a population the warehouse does not actually hold.

## 2. Records are variable-length, and the drop-zero rule is why

`measured` against the standard-mode export, 18,072 records: the shortest is 1,018
bytes and the longest 9,229. The head is fixed through `experience`; after that the
record uses the **same drop-zero encoding `teams.dat` uses** — a field whose value is
falsy is not written at all.

The proof is a clean natural experiment. `last_team_id` sits immediately before
`team_id`. A player who has never changed clubs has `last_team_id = 0`, and for that
player the field is **absent**, so `team_id` lands four bytes earlier. `measured`:
`team_id` sits at record+58 for 86.9% of rostered players and record+62 for the other
13.1%, and the split falls exactly on whether `last_team_id` is zero. **Reading
`team_id` at a constant offset therefore scores ~87%** — high enough to look finished
against a spot-check and wrong for one club in eight.

**The region is not guessed at, it is read from a presence mask.** The byte at
record+55 is a six-bit map over six `u32` fields, written in bit order with absent ones
skipped, each field followed by its `last_` counterpart:

| bit | field | | bit | field |
|---|---|---|---|---|
| 0 | `team_id` | | 3 | `last_organization_id` |
| 1 | `last_team_id` | | 4 | `league_id` |
| 2 | `organization_id` | | 5 | `last_league_id` |

`verified` — the mask takes exactly six values across all three saves (`0x00`, `0x14`,
`0x15`, `0x2a`, `0x37`, `0x3f`), each maps to one zero-ness signature with no
exceptions, and decoding it this way reproduces all six columns on **every** `retired = 0`
export row.

**The second mask at record+56 is a presence mask too, and it governs the tail.**
Bit 0 is `free_agent` (`verified` 18,072/18,072). The rest, `verified` the same way —
every presence bit agrees with the export's zero-ness on every `retired = 0` row, and
the decoded values match exactly:

| bit | governs | width |
|---|---|---|
| 2 | nickname `names.dat` index | `u32` |
| 3 | `second_nation_id` | `u32` |
| 4 | `language_ids0` | `u16` |
| 5 | `language_ids1` | `u16` |
| 6 | `bats` | `u8` |
| 7 | `throws` | `u8` |

The fields are written in **ascending bit order**, absent ones skipped — the same
convention as the assignment mask. Getting that order wrong is exactly a 99%-fit trap:
an oracle-driven parse that read the languages before the second nation scored
17,899/18,072 and the 173 failures were precisely the records carrying both.

**`bats` and `throws` are drop-DEFAULT, not drop-zero.** Neither is ever zero; the
writer instead elides the *majority* value 1 (right-handed). Bit set means the byte is
written and holds 2 or 3 (`bats`) or 2 (`throws`); bit clear means the value **is** 1.
`verified`: reconstructing them this way matches the export on all 18,072 rows, and the
bit-set populations equal the not-1 populations exactly in all three saves.

**The byte at record+57 is a third mask** (it is not a value; its observed values 2, 6,
14, 34, 38 decompose on bits). Bit 1 is set on every record of every save on disk
(58,200 of 58,200) — meaning unknown, treated as a shape sentinel. Bit 2 governs one
unclassified `u8` that takes values 1-3 (present on ~6% of records, overwhelmingly the
real-player minority; meaning `unconfirmed`, withheld). Bit 5 governs a `u32` that
matches `loan_league_id` on every export row. Bit 3 appears on a handful of records and
governs **no bytes** — proven by the strings behind it still parsing exactly.

After that run come **two `u32`-length-prefixed strings, back to back**:
`historical_id` (the Lahman/BBRef join key, e.g. `deverra01`) and
`historical_team_id`. Both `verified` against every `retired = 0` export row — empty
string included: the ~90% of players with no real-world identity carry a zero-length
prefix, not an absent field. The walk reads `historical_id` and deliberately exposes
nothing else from this region; the rest is crossed and recorded in the field map.

**The tail is validated before it is consumed.** `_scan_tail` walks the mask-declared
widths with lookaheads and only then lets the cursor consume them. If anything
disagrees — an unknown mask bit, a written `bats` outside {2, 3}, a string that is not
printable ASCII — the walk consumes nothing past the assignment run, reports
`bats`/`throws`/`historical_id` as `None`, and counts the record in
`PlayersFile.undecoded_tails`. On every save on disk that count is **zero**; a nonzero
count means the format changed and the landing gate must refuse, not guess.

**Still out of reach: `position` and `role`.** They sit past the historical strings,
beyond a 13-byte mostly-zero span (`unconfirmed`), the four injury-proneness bytes
(`measured` at that spot: they equal `prone_overall/leg/back/arm` on all 18,072 rows),
and a further mask-shaped region this walk does not decode. Within fixed-shape subsets
the role byte is exact — three shape groups scored 2,872/2,872, 371/371 and 317/317 at
group-specific offsets — but the shape rule is not derived, a fixed offset scores ~50%
across the population, and the export's `role = 13` (closer) is **not stored in that
byte at all** (the save holds 12 there for 197 of 229 closers, so the export's 13 looks
derived from depth-chart data elsewhere). Landing either field at less than exact is the
failure this project cannot afford, so neither is landed.

## 3. Framing is a search for a zero run, not a separator byte

`teams.dat` frames on nine zeros and a `0x28`. That pattern appears 1,402 times in a
27.9 MB `players.dat` against 18,072 records, so it is not the player frame.

What is `measured` — on all 18,071 gaps between consecutive records — is that **every
record start is preceded by at least 24 zero bytes.** Records are zero-padded to a
boundary this walk does not model. So the walk searches forward for that run and then
*validates* the candidate, exactly as `teams.py` validates a framed team id:

* the `u32` is strictly greater than the previous player id,
* the four bytes at the birth-date position parse as a real calendar date, and
* **the age byte agrees with that date and the file's own sim date.**

The third is what makes it exact, and it was added because the first two were not
enough. `measured`: an ascending id plus a parseable date accepted a false start
5.2 MB in, where 26 bytes of padding happen to be followed by `589825` and a "date" of
2048-04-01. The walk took it, and because every subsequent real id was smaller than
589825, it then silently returned **2,693 records instead of 18,072** — a short league
with every field it *did* read decoding perfectly. That is exactly the failure mode this
project cannot afford, and no spot-check would have caught it.

The age relation kills it. `measured` across all 18,072 records: the age byte equals the
whole years between the birth date and the sim date, **exactly, with zero exceptions**.
A false start must now line up three mutually-constrained fields by chance rather than
one, and the impostor above fails immediately — it claims age 64 for someone born in
2048. With this in place the walk frames **every one of the export's 18,072 rows**, plus
the five genuine records the export omits, and every field it reads matches the export
exactly on all 18,072.

**The candidate window exists because a player id can begin with a zero byte.** Ids are
little-endian, so player 256 is `00 01 00 00` and its own first byte is swallowed by the
padding run. The walk therefore tries the four alignments that could start a `u32` whose
top byte is zero, and takes the one that validates. Without that, every id whose low
byte is zero would be mis-framed.

## The record head, in the order the bytes give it

Offsets are stated for orientation only — **the walk reads these in sequence through the
cursor and never indexes them.**

| At | Field | Status |
|---|---|---|
| +0 | `u32 player_id`, ascending across the file | `verified` — 18,072 of 18,072 |
| +4 | `u32 first_name_index` into `names.dat` | `verified` — 18,072 of 18,072 |
| +8 | `u32 last_name_index` into `names.dat` | `verified` — 18,072 of 18,072 |
| +12 | `date_of_birth` (`u8` day, `u8` month, `u16` year) | `verified` — 18,072 of 18,072 |
| +16 | 3 bytes | unclassified |
| +19 | `u8 age` | `verified` |
| +20 | 1 byte | unclassified |
| +21 | `u8 nation_id` | `verified` |
| +22 | 5 bytes | unclassified |
| +27 | `u32 city_of_birth_id` | `verified` |
| +31 | `u16 weight` | `verified` |
| +33 | `u8 height` | `verified` |
| +34 | 1 byte | unclassified |
| +35 | `u8 uniform_number` | `verified` |
| +36 | `u8 experience` | `verified` |

Every row marked `verified` was scored against **every** `retired = 0` row of
`ootp_truth_real.players` — not a spot-check — and matched exactly.

**The two `u32`s at +4 and +8 are named as of Phase 7, and were not before.** They were
carried as an opaque pair — a field called `first_name_index` is a claim, and until it
was scored the walk had not earned it. Phase 7 scored it by brute force against the full
export population rather than by reading the bytes, which is the only way to tell a
correct mapping from a plausible one:

| Mapping | Score against `ootp_truth_real.players` |
|---|---|
| `+4` as **first**, `+8` as **last** | **18,072 / 18,072 = 100.00%** |
| `+4` as last, `+8` as first | 1 / 18,072 = 0.01% |

Zero unresolved indices in either direction. The join itself, the one-index-space
finding behind it and the encoding live in `parser/names.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.header import read_header_from
from ootp_ai.parser.lookahead import (
    DATE_WIDTH,
    U8_WIDTH,
    U16_WIDTH,
    U32_WIDTH,
    peek_date_parts,
    peek_length_prefixed_ascii,
    peek_u8,
    peek_u32,
    zero_run_width,
)
from ootp_ai.parser.primitives import Cursor, SaveDate

__all__ = [
    "BYTE_ACCOUNTING_TIER",
    "NO_DECLARED_COUNT",
    "PLAYERS_FILE",
    "TIER_RATIONALE",
    "PlayerRecord",
    "PlayerRecordLayout",
    "PlayersFile",
    "read_players",
]

#: Sits inside the `.lg` directory, beside `teams.dat` and `names.dat`.
PLAYERS_FILE = "players.dat"

#: What the header tail carries where `teams.dat` carries a record count. `measured` —
#: identical in all three saves. Exposed because a caller that wants to know whether the
#: count is trustworthy should be able to ask rather than infer it from a magic number.
NO_DECLARED_COUNT = 0xFFFFFFFF

BYTE_ACCOUNTING_TIER = "diagnostic"

TIER_RATIONALE = (
    "Reached: the header, the version guard, the six-u32 header tail, the file preamble "
    "(a zero run, a u32 constant and a length-prefixed 64-character digest), every "
    "record's 37-byte fixed head, the mask-governed club-assignment block, and the "
    "mask-governed identity tail through the two historical strings, for all 18,077 "
    "records of both test saves and all 22,046 of the managed league — roughly the "
    "first 70 to 100 bytes of each record. Not reached: the rest. A record runs 1,018 "
    "to 9,229 bytes, and the walk crosses the remainder by searching forward for the "
    "next record's zero-run frame rather than by reading it. Calling this walk strict "
    "would be a false claim about roughly 95% of the file. Two things make the "
    "diagnostic assertion weaker here than in teams.dat and both are the file's doing "
    "rather than the walk's: the header declares 0xFFFFFFFF instead of a record count, "
    "so there is no in-file oracle to check the framed count against; and the residual "
    "reported is what remains after the LAST record's decoded region, which is that "
    "record's own undecoded body plus the file tail. A later attempt at strict has to "
    "start by deriving the shape rule of the region past the historical strings — the "
    "13-byte span, the proneness quad, and the flag bytes that govern the "
    "position/role piece, per the module docstring."
)

#: How many `u32`s follow the header's two wide dates. A width, not an offset.
_HEADER_TAIL_FIELDS = 6

#: Between the header tail and the first record: a zero run, a `u32` whose meaning is
#: unknown, then a length-prefixed 64-character hex digest. `measured` — the same shape
#: in all three saves, and the digest differs between the managed league and the two test
#: saves, which is what a per-save content fingerprint would do.
_PREAMBLE_CONSTANT = 1234
_DIGEST_LENGTH = 64

#: The zero padding before every record start. `measured` on all 18,071 gaps in the
#: standard-mode save: never fewer than 24. Used as a search pattern, never as an offset.
_PAD_RUN = b"\x00" * 24

#: A player id is little-endian, so up to three of its leading bytes can be zero and get
#: swallowed by the padding run. These are the alignments a record start can take once
#: the run has been located. Bounded, and every candidate is validated before it is used.
_ALIGNMENT_WINDOW = 4

#: The widths of the head fields the lookaheads step over. `_NAME_INDEX_COUNT` is 2 because
#: the head carries two `u32` name indices at +4 and +8 — first then last, `verified` by
#: Phase 7. Only the count matters here: these constants exist so a lookahead can step
#: over the fields to reach the birth date, not so anything can jump to one.
_PLAYER_ID_WIDTH = U32_WIDTH
_NAME_INDEX_WIDTH = U32_WIDTH
_NAME_INDEX_COUNT = 2

#: Unclassified spans inside the fixed head, named so the walk reads as a sequence of
#: fields rather than a series of magic skips. Each is bytes the walk crosses and does
#: not interpret — recorded in `contracts/field_map.toml` as unclassified, per the
#: withhold-by-default rule.
#:
#: The block sits above the lookaheads rather than in field order further down, because
#: `_AGE_LOOKAHEAD` derives from `_GAP_AFTER_BIRTH_DATE` and Python resolves module-level
#: names in order — declared later, the module raises `NameError` at import.
_GAP_AFTER_BIRTH_DATE = 3
_GAP_AFTER_AGE = 1
_GAP_AFTER_NATION = 5
_GAP_AFTER_HEIGHT = 1

#: Where the birth date and the age sit inside the fixed head. These are **validation
#: lookaheads**, not field reads: the walk confirms a candidate record start by checking
#: the three-way agreement described in the docstring, then hands the cursor a plain
#: sequential read. The same pattern `teams.py` uses to confirm a framed team id before
#: committing to it.
#:
#: **Written as sums of named field widths, not as 12 and 19.** Both spellings compute the
#: same number; only this one says *why* it is that number, and only this one moves when a
#: field ahead of it does. It is the form `world.py` already uses to step over a known run
#: of fields, and re-expressing these two is what the bugfix request that widened
#: `tests/test_no_fixed_offsets.py` set out to earn — a raw record-relative constant is
#: indistinguishable from the fixed-offset read the ban exists to prevent, whatever its
#: prose defence. Read them against the head walk in `_read_record`: id, then the two name
#: indices, and you are at the birth date; the date and the gap that follows it, and you
#: are at the age. `tests/test_parse_players.py` pins both against a synthetic head.
_BIRTH_DATE_LOOKAHEAD = _PLAYER_ID_WIDTH + _NAME_INDEX_COUNT * _NAME_INDEX_WIDTH
_AGE_LOOKAHEAD = _BIRTH_DATE_LOOKAHEAD + DATE_WIDTH + _GAP_AFTER_BIRTH_DATE

#: Refuse an id that is not a player id, so a lost alignment raises instead of walking a
#: 32 MB buffer to its end inventing records. Deliberately loose — the real work is done
#: by the age/birth-date agreement, not by guessing how high ids will go in a save
#: nobody has created yet.
_MAX_PLAYER_ID = 10_000_000

#: Wide on purpose: this rejects bytes that are not a date at all, and nothing more.
#: Narrowing it to the observed 1983-2008 would reject a legends league on a save this
#: parser has never seen, which is a worse failure than the one it would prevent.
_MIN_BIRTH_YEAR = 1800
_MAX_BIRTH_YEAR = 2200

#: The age byte is stored, not derived, so it can in principle disagree with the birth
#: date by a day's rounding. `measured`: it never does — the agreement is exact for all
#: 18,072 records. The tolerance is here so a rounding change in a future OOTP build
#: degrades to a slightly weaker frame check rather than to a parser that reads nothing.
_AGE_TOLERANCE = 1

#: Between `experience` and the assignment block. Fourteen bytes of high-entropy values in
#: the 60-200 range — personality and injury-proneness territory on the evidence of the
#: export's column list, which makes them **rating-shaped and therefore withheld**
#: (ADR 0012: an unclassifiable field is treated as a true rating).
_GAP_AFTER_EXPERIENCE = 14

#: A `u32` immediately before the assignment masks. **It is not a constant, and that
#: nearly went wrong.** It reads 203 for every one of the 18,077 records in *both* test
#: saves, which is exactly what a format constant looks like — and the managed league
#: carries six distinct values there. Asserting 203 would have passed every test
#: available and broken on the only save that matters. Crossed, not interpreted;
#: `unconfirmed`. `tests/fixtures/synthetic.py` records the same lesson about a different
#: field: vary the save before believing a constant.
_UNCLASSIFIED_BEFORE_MASKS = 4

#: The assignment presence mask, at record+55. Six bits over six `u32` fields, written in
#: bit order with absent ones skipped. `verified` against every `retired = 0` export row:
#: the mask takes exactly six values across all three saves — 0x00, 0x14, 0x15, 0x2a,
#: 0x37, 0x3f — and each maps to one zero-ness signature with no exceptions.
#:
#: The pairing is what makes the order guessable in the first place: each field is
#: followed by its `last_` counterpart.
_ASSIGNMENT_BITS: tuple[str, ...] = (
    "team_id",
    "last_team_id",
    "organization_id",
    "last_organization_id",
    "league_id",
    "last_league_id",
)

#: The second mask, at record+56. Every bit below is `verified` against all 18,072
#: `retired = 0` export rows — presence agrees with the export's zero-ness and the
#: decoded values match exactly. Fields are written in ascending bit order. Bit 1 has
#: never been observed set (58,200 records, three saves); a record carrying it fails
#: `_scan_tail` rather than being guessed at.
_FREE_AGENT_BIT = 0
_NICKNAME_INDEX_BIT = 2
_SECOND_NATION_BIT = 3
_FIRST_LANGUAGE_BIT = 4
_SECOND_LANGUAGE_BIT = 5
_BATS_BIT = 6
_THROWS_BIT = 7

_KNOWN_FLAG_BITS = (
    (1 << _FREE_AGENT_BIT)
    | (1 << _NICKNAME_INDEX_BIT)
    | (1 << _SECOND_NATION_BIT)
    | (1 << _FIRST_LANGUAGE_BIT)
    | (1 << _SECOND_LANGUAGE_BIT)
    | (1 << _BATS_BIT)
    | (1 << _THROWS_BIT)
)

#: The third mask, at record+55+3 (record+57) — formerly crossed as an unclassified
#: byte, and its observed values (2, 6, 14, 34, 38) decompose exactly on these bits.
#: Bit 1 is set on every record of every save measured; its meaning is unknown and it
#: is required as a sentinel, so a save that stops setting it degrades loudly (every
#: tail lands `None`) instead of misparsing. Bit 3 governs no bytes — the strings
#: behind it parse exactly on the records that carry it. Bits 0, 4, 6 and 7 have never
#: been observed and fail the scan.
_TAIL_SENTINEL_BIT = 1
_TAIL_EXTRA_BYTE_BIT = 2
_TAIL_MARKER_BIT = 3
_TAIL_LOAN_BIT = 5

_KNOWN_TAIL_BITS = (
    (1 << _TAIL_SENTINEL_BIT)
    | (1 << _TAIL_EXTRA_BYTE_BIT)
    | (1 << _TAIL_MARKER_BIT)
    | (1 << _TAIL_LOAN_BIT)
)

#: What an elided `bats`/`throws` byte means. Drop-DEFAULT, not drop-zero: neither
#: field is ever zero, and the writer skips the majority value instead. `verified` —
#: absent-means-1 reproduces the export on all 18,072 rows.
_DEFAULT_SIDE = 1

#: The values a *written* byte may hold, `measured` across all three saves (58,200
#: records): a written `bats` is 2 or 3, a written `throws` is 2, and the unclassified
#: bit-2 byte is 1, 2 or 3. Anything else fails the tail scan — these sets are what
#: makes the validation mean something on a save with no export behind it.
_WRITTEN_BATS = frozenset({2, 3})
_WRITTEN_THROWS = frozenset({2})
_TAIL_EXTRA_VALUES = frozenset({1, 2, 3})

#: Cap on the two historical strings' declared lengths. The longest observed
#: `historical_id` is 9 characters; 40 is slack without letting a garbage length walk
#: the file.
_TAIL_STRING_MAX_LEN = 40


class PlayerRecordLayout(SaveFormatError):  # noqa: N818
    """A valid version-25 `players.dat` whose records are not shaped as measured.

    Distinct from the header refusals: those mean *this is not the file you think it
    is*, this one means *the file is what it claims and its records do not match what
    every save on disk was measured to hold*.
    """


@dataclass(frozen=True, slots=True)
class PlayerRecord:
    """One player's head, club assignment, and identity tail. Deliberately minimal.

    No ratings, by design and permanently (ADR 0012). No `position` or `role` — a *this
    walk* limit rather than a policy one: they sit past further variable content whose
    shape rule is not yet derived, and the module docstring records how close the decode
    got and where it breaks.
    """

    player_id: int
    #: The `u32` at +4. `verified` 18,072/18,072 against the export by Phase 7's brute
    #: force; the opposite assignment scored 1/18,072. Resolve it through a
    #: `parser.names.NameTable` built from **the same save** — the index means nothing
    #: without one.
    first_name_index: int
    #: The `u32` at +8, `verified` the same way.
    last_name_index: int
    date_of_birth: SaveDate
    age: int
    nation_id: int
    city_of_birth_id: int
    weight: int
    height: int
    uniform_number: int
    experience: int

    # ── club assignment, from the presence mask at record+55 ─────────────────
    #
    # **Zero here means zero, not "missing".** The encoding elides a field whose value is
    # falsy, so an absent field and a field holding 0 are the same statement: this player
    # has no team. That is why these are plain ints rather than `int | None` — unlike the
    # droppable *string* slots in `teams.py`, where absent and empty really are
    # indistinguishable and `None` is the only honest reading.
    team_id: int
    last_team_id: int
    organization_id: int
    last_organization_id: int
    #: **The save stores this positive; the export renders it negative on 176 records.**
    #: This is what the bytes hold, not what the export prints. `inferred`: those 176 are
    #: exactly the players carrying a `team_id` with no `list_id = 1` row in
    #: `team_roster`, so the sign appears to mark "attached to a club but not rostered".
    #: A consumer that needs the export's convention must apply it deliberately.
    league_id: int
    last_league_id: int
    #: From bit 0 of the second mask at record+56. `verified` 18,072/18,072.
    free_agent: bool

    # ── the identity tail, validated before it is consumed ───────────────────
    #
    # **`None` on any of these three means one thing only: the record's tail did not
    # match the measured shape and the walk refused to guess.** It is not a default and
    # it is not structural absence — `PlayersFile.undecoded_tails` counts it, and on
    # every save on disk that count is zero. Structural absence looks different:
    # a fictional player's `historical_id` is `""`, never `None`.

    #: 1 = right, 2 = left, 3 = switch. `verified` against every `retired = 0` export
    #: row. Stored drop-default: the byte exists only when the value is not 1.
    bats: int | None
    #: 1 = right, 2 = left. Same encoding, same verification.
    throws: int | None
    #: The Lahman/BBRef string join key (`deverra01`). `verified` on all 18,072 export
    #: rows including the empty ones. **`""` is a fact — this player has no real-world
    #: identity — and covers ~90% of the population**; a join on this key silently drops
    #: the fictional majority, which is why it is an attribute here and never a key.
    historical_id: str | None


@dataclass(frozen=True, slots=True)
class PlayersFile:
    """Every player record the file declares, plus what the walk can say about itself."""

    players: tuple[PlayerRecord, ...]
    #: Bytes left after the last record's head — that record's undecoded body plus the
    #: file tail. Recorded rather than asserted to be zero; see `TIER_RATIONALE`.
    residual_bytes: int
    sim_date: SaveDate
    #: The 64-character hex digest from the file preamble.
    #:
    #: **Corrected 2026-08-18.** An earlier note here claimed the two test saves "share
    #: one" digest. They do not, and the claim came from comparing the first twelve
    #: characters of a debug print. `measured` in full: all three saves carry **distinct**
    #: digests, and the two test saves agree on exactly the first **32** hex characters
    #: before diverging. That 32/32 split is itself the interesting part — it is what two
    #: concatenated 128-bit values would look like when the saves share a lineage and
    #: differ in content — but what it *is* remains `unconfirmed`, and nothing here
    #: depends on it.
    content_digest: str
    #: `None` when the header carries the `0xFFFFFFFF` sentinel, which is every save
    #: measured. A count here would mean a later OOTP build started declaring one.
    declared_record_count: int | None
    #: How many records' identity tails failed `_scan_tail`'s validation and were left
    #: unconsumed, with `bats`/`throws`/`historical_id` reported as `None`. **Zero on
    #: every save measured** (58,200 records across three saves). Nonzero means the
    #: format changed under this walk; a landing gate must treat that as a refusal,
    #: because the alternative is averaging over records the parser admits it could
    #: not read.
    undecoded_tails: int


def read_players(data: bytes) -> PlayersFile:
    """Walk a `players.dat` buffer and return every player record's fixed head.

    Raises:
        MalformedHeader: the buffer is truncated, or is not an OOTP record file.
        UnsupportedSaveVersion: the declared version is not the one we are proven on.
        SaveFilenameMismatch: the header names a different file.
        UnexpectedEndOfData: a read ran past the end of the buffer.
        PlayerRecordLayout: the preamble or a record is not shaped as measured.
    """
    cursor = Cursor(data, label=PLAYERS_FILE)
    header = read_header_from(cursor, PLAYERS_FILE)
    tail = tuple(cursor.u32() for _ in range(_HEADER_TAIL_FIELDS))
    declared = tail[4]

    digest = _read_preamble(cursor, data)

    # The FIRST record follows the preamble directly, with no padding in front of it —
    # the zero run this walk frames on sits *before* the preamble, not before record one.
    # Searching for a pad run here would step straight over the first player.
    players: list[PlayerRecord] = []
    previous_id = 0
    if not _looks_like_record(data, cursor.position, previous_id, header.sim_date):
        raise PlayerRecordLayout(
            f"{PLAYERS_FILE}: the bytes after the preamble are not a player record. "
            "The preamble is not where this walk believes it ends, so every width "
            "after it would be read from the wrong place."
        )

    start: int | None = cursor.position
    while start is not None:
        cursor.skip(start - cursor.position)
        players.append(_read_record(cursor, data))
        previous_id = players[-1].player_id
        start = _next_record_start(data, cursor.position, previous_id, header.sim_date)

    return PlayersFile(
        players=tuple(players),
        residual_bytes=cursor.remaining(),
        sim_date=header.sim_date,
        content_digest=digest,
        declared_record_count=None if declared == NO_DECLARED_COUNT else declared,
        undecoded_tails=sum(1 for player in players if player.historical_id is None),
    )


def _read_preamble(cursor: Cursor, data: bytes) -> str:
    """Cross the zero run, the `u32` constant and the digest, and return the digest.

    The zero run's width is taken from the bytes rather than from a constant: it is 46
    in every save measured, and a walk that hardcoded 46 would silently mis-read the
    first record on the day it changed. The buffer is passed alongside the cursor
    because the cursor exposes no lookahead by construction — it can only consume — so
    "advance while the next byte is zero" has to read the byte before deciding.
    """
    while peek_u8(data, cursor.position) == 0:
        cursor.skip(U8_WIDTH)

    marker = cursor.u32()
    if marker != _PREAMBLE_CONSTANT:
        raise PlayerRecordLayout(
            f"{PLAYERS_FILE}: the preamble constant is {marker}, expected "
            f"{_PREAMBLE_CONSTANT}. The region between the header tail and the first "
            "record is not the shape every save on disk carries."
        )

    digest = cursor.string()
    if len(digest) != _DIGEST_LENGTH:
        raise PlayerRecordLayout(
            f"{PLAYERS_FILE}: the preamble digest is {len(digest)} characters, expected "
            f"{_DIGEST_LENGTH}. The walk would start reading records mid-field."
        )
    return digest


def _read_record(cursor: Cursor, data: bytes) -> PlayerRecord:
    """Consume one record's fixed head as a plain forward sequence of typed reads.

    Every `skip` below crosses bytes the walk does not interpret. They are named rather
    than inlined so the head reads as the field sequence it is, and so a later reader
    who classifies one of them knows exactly where it lives.

    `data` rides along for the identity tail, whose widths are decided by lookahead
    before the cursor consumes them — the same reconcile-then-consume pattern
    `teams.py` uses, because the cursor exposes no lookahead by construction.
    """
    player_id = cursor.u32()
    first_name_index = cursor.u32()
    last_name_index = cursor.u32()
    date_of_birth = cursor.date()

    cursor.skip(_GAP_AFTER_BIRTH_DATE)
    age = cursor.u8()

    cursor.skip(_GAP_AFTER_AGE)
    nation_id = cursor.u8()

    cursor.skip(_GAP_AFTER_NATION)
    city_of_birth_id = cursor.u32()
    weight = cursor.u16()
    height = cursor.u8()

    cursor.skip(_GAP_AFTER_HEIGHT)
    uniform_number = cursor.u8()
    experience = cursor.u8()

    cursor.skip(_GAP_AFTER_EXPERIENCE)
    cursor.skip(_UNCLASSIFIED_BEFORE_MASKS)
    assignment_mask = cursor.u8()
    flag_mask = cursor.u8()
    tail_mask = cursor.u8()
    assignments = _read_assignments(cursor, assignment_mask)

    bats: int | None
    throws: int | None
    historical_id: str | None
    scan = _scan_tail(data, cursor.position, flag_mask, tail_mask)
    if scan is None:
        # The tail is not the measured shape. Consume nothing past the assignment run —
        # the framing search recovers the next record regardless — and say so with
        # `None`, never with a default that would read as a fact.
        bats = None
        throws = None
        historical_id = None
    else:
        bats, throws, prefix_width = scan
        cursor.skip(prefix_width)
        historical_id = cursor.string()
        # `historical_team_id`, verified against the export but deliberately not
        # exposed — consumed only so the cursor leaves the record's decoded region
        # on a field boundary.
        cursor.string()

    return PlayerRecord(
        player_id=player_id,
        first_name_index=first_name_index,
        last_name_index=last_name_index,
        date_of_birth=date_of_birth,
        age=age,
        nation_id=nation_id,
        city_of_birth_id=city_of_birth_id,
        weight=weight,
        height=height,
        uniform_number=uniform_number,
        experience=experience,
        free_agent=bool(flag_mask & (1 << _FREE_AGENT_BIT)),
        bats=bats,
        throws=throws,
        historical_id=historical_id,
        **assignments,
    )


def _scan_tail(
    data: bytes, position: int, flag_mask: int, tail_mask: int
) -> tuple[int, int, int] | None:
    """Validate the identity tail at `position` and return `(bats, throws, width)`.

    `width` is the distance from `position` to the `historical_id` length prefix — the
    bytes the cursor may then consume without interpreting. `None` means the tail does
    not match the measured shape and **nothing must be consumed**: an unknown mask bit,
    a written value outside its measured set, or a string that is not printable ASCII
    all land here, because each one means the widths below are widths of a different
    format.

    Decide-with-lookahead, then consume-with-cursor: this function reads through the
    sanctioned seam and moves nothing, so a refusal is free. On every save on disk it
    accepts all records — 18,077 + 18,077 + 22,046, zero refusals — so a `None` in the
    wild is a format change, not noise.
    """
    if flag_mask & ~_KNOWN_FLAG_BITS:
        return None
    if not tail_mask & (1 << _TAIL_SENTINEL_BIT):
        return None
    if tail_mask & ~_KNOWN_TAIL_BITS:
        return None

    at = position
    if flag_mask & (1 << _NICKNAME_INDEX_BIT):
        at += U32_WIDTH
    if flag_mask & (1 << _SECOND_NATION_BIT):
        at += U32_WIDTH
    if flag_mask & (1 << _FIRST_LANGUAGE_BIT):
        at += U16_WIDTH
    if flag_mask & (1 << _SECOND_LANGUAGE_BIT):
        at += U16_WIDTH

    bats = _DEFAULT_SIDE
    if flag_mask & (1 << _BATS_BIT):
        written = peek_u8(data, at)
        if written is None or written not in _WRITTEN_BATS:
            return None
        bats = written
        at += U8_WIDTH

    throws = _DEFAULT_SIDE
    if flag_mask & (1 << _THROWS_BIT):
        written = peek_u8(data, at)
        if written is None or written not in _WRITTEN_THROWS:
            return None
        throws = written
        at += U8_WIDTH

    if tail_mask & (1 << _TAIL_EXTRA_BYTE_BIT):
        written = peek_u8(data, at)
        if written is None or written not in _TAIL_EXTRA_VALUES:
            return None
        at += U8_WIDTH

    if tail_mask & (1 << _TAIL_LOAN_BIT):
        at += U32_WIDTH

    first = peek_length_prefixed_ascii(data, at, _TAIL_STRING_MAX_LEN)
    if first is None:
        return None
    _, after_first = first
    if peek_length_prefixed_ascii(data, after_first, _TAIL_STRING_MAX_LEN) is None:
        return None
    return bats, throws, at - position


def _read_assignments(cursor: Cursor, mask: int) -> dict[str, int]:
    """Read the `u32`s the assignment mask says are present, in bit order.

    A bit that is clear does not mean "unknown" — it means the field's value is zero and
    the writer elided it. So the absent case yields 0 rather than `None`, which is both
    what the export holds and what the domain means: no team.

    The reads are signed. `measured`: the export carries negatives in these columns, and
    reading them unsigned would turn a -1 into 4,294,967,295 — a plausible-looking id.
    """
    values = dict.fromkeys(_ASSIGNMENT_BITS, 0)
    for bit, field in enumerate(_ASSIGNMENT_BITS):
        if mask & (1 << bit):
            values[field] = cursor.i32()
    return values


# ── framing ──────────────────────────────────────────────────────────────────


def _next_record_start(
    data: bytes, position: int, previous_id: int, sim_date: SaveDate
) -> int | None:
    """Search forward for the next record start, or `None` at the end of the file.

    A search, never a jump. The zero-run pattern locates a *candidate*; the candidate is
    only accepted once it passes `_looks_like_record`, because the same run occurs inside
    record bodies several times per record.
    """
    search_from = position
    while True:
        run = data.find(_PAD_RUN, search_from)
        if run < 0:
            return None

        # Extend to the end of the maximal zero run. `zero_run_width` requires a limit —
        # an unbounded scan over 32 MB is how a mis-framed walk becomes a hang — and
        # `len(data) - after` is exactly the old loop's bound, so this is the same scan
        # rather than a new cap that could leave `after` mid-run.
        after = run + len(_PAD_RUN)
        after += zero_run_width(data, after, limit=len(data) - after)

        for candidate in range(after - _ALIGNMENT_WINDOW + 1, after + 1):
            if candidate >= position and _looks_like_record(data, candidate, previous_id, sim_date):
                return candidate

        # Not a record start. Resume after this run rather than re-finding it.
        search_from = after if after > search_from else search_from + 1


def _looks_like_record(data: bytes, position: int, previous_id: int, sim_date: SaveDate) -> bool:
    """Does a record begin here? All three checks are required, and each earns its place.

    An ascending id alone is far too weak on a 32 MB buffer — small integers are
    everywhere. An ascending id plus a parseable date is *nearly* enough and that is the
    dangerous part: it accepted one impostor and silently truncated the league to 15% of
    its size. The age agreement is what closes it, because a run of bytes has to satisfy
    three mutually-constrained fields at once to survive.
    """
    player_id = peek_u32(data, position)
    if player_id is None or not previous_id < player_id <= _MAX_PLAYER_ID:
        return False

    birth = _peek_valid_date(data, position + _BIRTH_DATE_LOOKAHEAD)
    if birth is None or not _MIN_BIRTH_YEAR <= birth.year <= _MAX_BIRTH_YEAR:
        return False

    stated_age = peek_u8(data, position + _AGE_LOOKAHEAD)
    implied_age = _years_between(birth, sim_date)
    if stated_age is None or implied_age is None:
        return False
    return abs(stated_age - implied_age) <= _AGE_TOLERANCE


def _years_between(birth: SaveDate, on: SaveDate) -> int | None:
    """Whole years from `birth` to `on`, or `None` if either is not a real date."""
    start, end = birth.as_date(), on.as_date()
    if start is None or end is None:
        return None
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def _peek_valid_date(data: bytes, position: int) -> SaveDate | None:
    """A real calendar date at `position`, or `None` if those bytes are not one.

    The *reading* moved to `lookahead.peek_date_parts`; the *validation* stays here,
    because it is not shared. `world.py` treats a zero year as legitimate structural
    absence in a calendar record while this walk rejects it when framing a player — so the
    seam hands back raw parts and each caller applies its own rule.
    """
    parts = peek_date_parts(data, position)
    if parts is None:
        return None
    day, month, year = parts
    candidate = SaveDate(day=day, month=month, year=year)
    return candidate if candidate.as_date() is not None else None
