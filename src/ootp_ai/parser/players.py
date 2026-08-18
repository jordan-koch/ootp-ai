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
13.1%, and the split falls exactly on whether `last_team_id` is zero.

**This is why nothing past `experience` is landed here.** Reading `team_id` at a
constant offset scores ~87% — high enough to look finished against a spot-check and
wrong for one club in eight, which is precisely the failure the fixed-offset ban exists
to prevent. Resolving the drop-zero region is real work and it is not this walk's.

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
| +4, +8 | two `u32`s, both inside `names.dat`'s index range | `unconfirmed` — see below |
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

**The two `u32`s at +4 and +8 are deliberately not named.** They are the plausible home
of the first- and last-name indices: both fall inside `names.dat`'s ~264,095-entry range
in every record sampled. That is suggestive and it is not proof, and *which* is which is
not established at all. Phase 7 resolves them by brute force against a full answer key,
which is the only way to tell a correct mapping from a plausible one. Until then they
are carried as an opaque pair, because a field named `first_name_index` is a claim and
this walk has not earned it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.header import read_header_from
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
    "(a zero run, a u32 constant and a length-prefixed 64-character digest), and every "
    "record's 37-byte fixed head, for all 18,077 records of both test saves and all "
    "22,046 of the managed league. Not reached: the rest of each record. A record runs "
    "1,018 to 9,229 bytes and this walk decodes the first 37, crossing the remainder by "
    "searching forward for the next record's zero-run frame rather than by reading it. "
    "Calling this walk strict would be a false claim about roughly 97% of the file. "
    "Two things make the diagnostic assertion weaker here than in teams.dat and both are "
    "the file's doing rather than the walk's: the header declares 0xFFFFFFFF instead of a "
    "record count, so there is no in-file oracle to check the framed count against; and "
    "the residual reported is what remains after the LAST record's head, which is that "
    "record's own undecoded body plus the file tail. A later attempt at strict has to "
    "start by resolving the drop-zero region that begins after `experience` — the same "
    "encoding teams.dat uses, and the reason team_id is not landed here."
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

#: Where the birth date and the age sit inside the fixed head. These are **validation
#: lookaheads**, not field reads: the walk confirms a candidate record start by checking
#: the three-way agreement described in the docstring, then hands the cursor a plain
#: sequential read. The same pattern `teams.py` uses to confirm a framed team id before
#: committing to it.
_BIRTH_DATE_LOOKAHEAD = 12
_AGE_LOOKAHEAD = 19

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

#: Unclassified spans inside the fixed head, named so the walk reads as a sequence of
#: fields rather than a series of magic skips. Each is bytes the walk crosses and does
#: not interpret — recorded in `contracts/field_map.toml` as unclassified, per the
#: withhold-by-default rule.
_GAP_AFTER_BIRTH_DATE = 3
_GAP_AFTER_AGE = 1
_GAP_AFTER_NATION = 5
_GAP_AFTER_HEIGHT = 1


class PlayerRecordLayout(SaveFormatError):  # noqa: N818
    """A valid version-25 `players.dat` whose records are not shaped as measured.

    Distinct from the header refusals: those mean *this is not the file you think it
    is*, this one means *the file is what it claims and its records do not match what
    every save on disk was measured to hold*.
    """


@dataclass(frozen=True, slots=True)
class PlayerRecord:
    """One player's fixed head. Deliberately minimal — see the module docstring.

    No ratings, by design and permanently (ADR 0012). No `team_id`, `position`, `bats`
    or `throws` either, which is a *this walk* limit rather than a policy one: those sit
    past the drop-zero region and cannot yet be read without guessing.
    """

    player_id: int
    #: The two `u32`s at +4 and +8, in file order. Almost certainly the name indices;
    #: which is first and last is **unconfirmed** and Phase 7 settles it. Carried as a
    #: pair precisely so nothing downstream can mistake a position for a proof.
    name_indices: tuple[int, int]
    date_of_birth: SaveDate
    age: int
    nation_id: int
    city_of_birth_id: int
    weight: int
    height: int
    uniform_number: int
    experience: int


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
        players.append(_read_record(cursor))
        previous_id = players[-1].player_id
        start = _next_record_start(data, cursor.position, previous_id, header.sim_date)

    return PlayersFile(
        players=tuple(players),
        residual_bytes=cursor.remaining(),
        sim_date=header.sim_date,
        content_digest=digest,
        declared_record_count=None if declared == NO_DECLARED_COUNT else declared,
    )


def _read_preamble(cursor: Cursor, data: bytes) -> str:
    """Cross the zero run, the `u32` constant and the digest, and return the digest.

    The zero run's width is taken from the bytes rather than from a constant: it is 46
    in every save measured, and a walk that hardcoded 46 would silently mis-read the
    first record on the day it changed. The buffer is passed alongside the cursor
    because the cursor exposes no lookahead by construction — it can only consume — so
    "advance while the next byte is zero" has to read the byte before deciding.
    """
    while cursor.remaining() and data[cursor.position] == 0:
        cursor.skip(1)

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


def _read_record(cursor: Cursor) -> PlayerRecord:
    """Consume one record's fixed head as a plain forward sequence of typed reads.

    Every `skip` below crosses bytes the walk does not interpret. They are named rather
    than inlined so the head reads as the field sequence it is, and so a later reader
    who classifies one of them knows exactly where it lives.
    """
    player_id = cursor.u32()
    name_indices = (cursor.u32(), cursor.u32())
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

    return PlayerRecord(
        player_id=player_id,
        name_indices=name_indices,
        date_of_birth=date_of_birth,
        age=age,
        nation_id=nation_id,
        city_of_birth_id=city_of_birth_id,
        weight=weight,
        height=height,
        uniform_number=uniform_number,
        experience=experience,
    )


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

        after = run + len(_PAD_RUN)
        while after < len(data) and data[after] == 0:
            after += 1

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
    player_id = _peek_u32(data, position)
    if player_id is None or not previous_id < player_id <= _MAX_PLAYER_ID:
        return False

    birth = _peek_date(data, position + _BIRTH_DATE_LOOKAHEAD)
    if birth is None or not _MIN_BIRTH_YEAR <= birth.year <= _MAX_BIRTH_YEAR:
        return False

    stated_age = _peek_u8(data, position + _AGE_LOOKAHEAD)
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


def _peek_u8(data: bytes, position: int) -> int | None:
    """A byte at a **computed** position, for lookahead. Never a literal offset."""
    return None if position < 0 or position >= len(data) else data[position]


def _peek_u32(data: bytes, position: int) -> int | None:
    """A `u32` at a **computed** position, for lookahead. Never a literal offset."""
    if position < 0 or position + 4 > len(data):
        return None
    return int.from_bytes(data[position : position + 4], "little")


def _peek_date(data: bytes, position: int) -> SaveDate | None:
    """A `u8 day, u8 month, u16 year` at a computed position, or `None` if not a date."""
    if position < 0 or position + 4 > len(data):
        return None
    day = data[position]
    month = data[position + 1]
    year = int.from_bytes(data[position + 2 : position + 4], "little")
    candidate = SaveDate(day=day, month=month, year=year)
    return candidate if candidate.as_date() is not None else None
