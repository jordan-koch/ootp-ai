"""`world.dat` — the division hierarchy and the league calendar, entered by landmark.

**Read this docstring before the code.** This is the first walk in the project that does
not start at the top of a file, and every choice below follows from that.

## Why entry is a search and not a seek

`world.dat` is 8.7-8.9 MB and its header declares **one** record: the world. That record
holds, in order, world settings, forty languages, ~94,000 cities, the leagues, the
schedule, the calendar, and then ~1.9 MB of high schools and colleges. The leagues sit
**62% in**, behind the city array, so a from-the-top walk means modelling ~94,000 records
that nothing in this project consumes — its own phase, and one this phase defers.

The alternative is not a fixed offset. `parser/primitives.py`'s cursor has no `seek` and
no position setter, and `tests/test_no_fixed_offsets.py` scans the AST of every module
here. What this walk does instead is **search the buffer for content, validate what it
finds by parsing forward, and refuse unless the answer is unique.** Every position it
enters at was computed from the bytes; none is a constant measured against another save.

## The three entries, and what each is worth

| Entry | Found by | Uniqueness, `measured` 2026-08-16 |
|---|---|---|
| the league record | the composite string `<u32 21>Major League Baseball` | **1** occurrence in each of the three saves on disk |
| the sub-league nest | a bounded backward scan validated by parsing the whole nest | **1** validating position in the 64 bytes before `<u32 2>AL<u32 15>American League`, which itself occurs **1** time per save |
| the calendar | a structural search: the one count-prefixed array of well-formed calendar records that is maximal in both directions | **1** validating candidate per save, out of ~43,800 motif hits and ~2,300 arrays that walk |

**Prefix and payload together, never the payload alone.** Bare `OPENING DAY` occurs 95
times in each save; the length prefix is what turns a string into a landmark.

**Zero matches and two matches are both errors, always.** A landmark walk has a failure
mode a from-the-top walk does not: find nothing, return nothing, and hand back a world
with no divisions and no calendar that is structurally indistinguishable from a league
that genuinely has neither. Nothing downstream can tell those apart, so this module
refuses instead — `human_managers.py` set that precedent and the reasoning is identical.

## The calendar's landmark is structural, which is better than a string

The calendar could not be entered by a string: the schedule that precedes it is
count-prefixed with a per-league game count — 12,961 in the probes, 16,817 in the managed
league — so its head cannot be found without already knowing the number, and the leagues
region cannot be walked forward to it without decoding the league scalar block this phase
defers.

So the calendar is found by what it *is* rather than by what it says. A candidate is a
`u32` count followed by exactly that many records that all decode — plausible date, zero
pad, printable name that fits — with strictly increasing `seq`, and it is accepted only if
it is **maximal in both directions**: nothing that parses as a calendar record follows the
last one, and no calendar record ends exactly where the count begins.

Both halves are load-bearing, and the second is the interesting one. Every record in the
array is itself a candidate head, because the four bytes in front of a record are the
previous record's tail and often read as a small count. `measured`: without left-maximality
each save yields **two** survivors — the real array, and its own last record, which
declares a count of 1 and is trivially right-maximal. With it, **exactly one**, at the
array head, in all three saves. Cost: ~0.16 s per file.

## What the walk decodes, and what it crosses without decoding

`measured` 2026-08-16 against all three saves, with `ootp_truth_real` as the oracle for
the standard-mode probe:

| Region | Status |
|---|---|
| the shared header, through the two wide dates | `verified` — `header.py` |
| six `u32` header tail; field 5 is the record count and reads **1** in all three saves | `measured` |
| league record head: `u32 league_id, u32 nation_id, u32 language_id, u32 gender` | `measured` — 203 / 206 / 0 / 0, matching the export's `leagues` row for MLB field for field |
| the league's name and abbreviation, length-prefixed | `measured` |
| ~1,170 bytes of league scalars — award names and what looks like a season template | **crossed, not decoded** (`unconfirmed`) |
| `u32 sub_league_count`, then per sub-league `u32 id`, abbr, name, `u32 gender`, `u8 dh`, `u32 division_count` | `measured` |
| per division `u32 id`, name, `u32 gender`, `u32 team_count`, then that many `u32 team_id` | `measured` — all six MLB divisions match the export exactly in all three saves |
| ~965 KB to 1.2 MB between the nest and the calendar — the other fourteen leagues and the schedule | **never read** |
| `u32 calendar_count`, then 3,058 fixed-shape events | `measured` — all 3,058 match `ootp_truth_real.league_events` on all eight exported columns; the control shifting `league_id` by ±3 scores 1,070 |
| ~1.9 MB of high schools and colleges after the calendar | **never read** |

## One league's divisions, not fifteen

The nest this walk lands is the one belonging to the league named `Major League
Baseball`. The other fourteen leagues in the file each sit behind their own unmapped
scalar block, so reaching them means the from-the-top work this phase defers. A league by
another name raises rather than returning an empty world — see the refusal note above.

## Two typing decisions that are not stylistic

**The three flag bytes land as `int`, never `bool`.** Every value observed is 0 or 1, but
*observed* is doing real work in that sentence: `bool(2)` is `True`, so a bool field makes
an unexpected value indistinguishable from a 1 forever. Bronze is 1:1 with parser output —
typing and casing, no semantic conversion — and a `gamedata` test checks the domain
against the real files, so the day the game writes something else it arrives as a red test
rather than as a `True` that used to be a 2.

**`event_type` lands raw and unlabelled.** The enum's semantics are undocumented —
`db_structure_ootp25_mysql.txt` has the column, not the meaning — and a wrong human label
produces a confidently wrong calendar that throws nothing. The same posture Phase 6 takes
with `list_id`: keep the datum, withhold the meaning until somebody reads the game screen.

**`deleted` is not "past".** `measured`: 2,492 of the 3,058 entries carry it in both
probes and 2,259 in the managed league, and deleted MLB rows are dated *after* the sim
date — the set includes a duplicate OPENING DAY and three PLAYOFFS BEGIN. Every row is
landed and filtering belongs to the report, never to the parse: a walk that dropped them
would return 566 rows and look perfectly consistent.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.header import read_header_from
from ootp_ai.parser.primitives import Cursor, SaveDate

__all__ = [
    "BYTE_ACCOUNTING_TIER",
    "TIER_RATIONALE",
    "WORLD_FILE",
    "AmbiguousWorldLandmark",
    "CalendarEvent",
    "DivisionMembership",
    "WorldFile",
    "WorldRecordLayout",
    "WorldRegion",
    "read_calendar",
    "read_world",
]

#: Sits inside the `.lg` directory beside `teams.dat`. 8.66-8.90 MB across the three saves
#: on disk — the second largest file this project reads, and the least understood.
WORLD_FILE = "world.dat"

#: Weaker than `diagnostic`, and it carries its own name so it cannot be mistaken for one.
#: The vocabulary lives in `tests/fixtures/tiers.py`, which this module cannot edit.
BYTE_ACCOUNTING_TIER = "region-accounted"

TIER_RATIONALE = (
    "Reached: the header and version guard, the six-u32 header tail with its declared "
    "record count of 1, the top league's record head, its sub-league nest with every "
    "division's explicit team array, and the whole 3,058-entry calendar. Each walked "
    "region is bounded by its own declared count and consumed to the byte, and both "
    "counts are checked twice — once by the lookahead scan that validates the entry and "
    "once by the cursor that reads it. Not reached: everything else, which is most of the "
    "file. The walk never reads the ~5.5 MB before the leagues region (world settings, "
    "forty languages and ~94,000 cities), the ~965 KB to 1.2 MB between the division nest "
    "and the calendar (the other fourteen leagues and the 12,961-game schedule), or the "
    "~1.9 MB of high schools and colleges after it; those three are reported as the "
    "un-walked prefix, gap and suffix rather than waved at. Inside the divisions region a "
    "further ~1,170 bytes of league scalars are crossed rather than decoded — award names "
    "and what looks like a season template. Calling this walk strict, or even diagnostic, "
    "would be a false claim about roughly 85% of the file. A later attempt should start "
    "with the from-the-top walk behind the ~94,126-record city array: it is the only "
    "thing that turns the un-walked prefix into a number that has been read rather than "
    "skipped, and it would also reach the other fourteen leagues' division nests, which "
    "this walk cannot see."
)

#: The league whose divisions this walk lands. A content landmark, not a constant offset:
#: the buffer is searched for it and the match is required to be unique. `measured` — one
#: occurrence in each of the three saves on disk.
_LEAGUE_NAME = "Major League Baseball"

#: The first sub-league of that league, matched as abbreviation **and** name together.
#: `measured` — one occurrence per save, where the bare payload `OPENING DAY` occurs 95
#: times. The length prefix is what makes a string a landmark.
_SUB_LEAGUE_ABBR = "AL"
_SUB_LEAGUE_NAME = "American League"

#: `u32` fields ahead of the league's name: `league_id, nation_id, language_id, gender`.
#: `measured` — 203, 206, 0, 0 in all three saves, matching the export's `leagues` row for
#: MLB field for field. They are fixed-width with no variable-length region among them,
#: which is what makes the record head reachable from its name at all; the read is
#: validated by requiring the name that follows the four to be the landmark itself.
_LEAGUE_HEAD_FIELDS = 4

#: How many `u32`s follow the header's two wide dates, as in every other record file.
_HEADER_TAIL_FIELDS = 6

#: `measured` — `world.dat` declares exactly one record in all three saves. Checked rather
#: than assumed: it is the cheapest evidence that the header tail is where this walk
#: believes it is, and every width after it would otherwise be read from the wrong place.
_WORLD_RECORD_COUNT = 1

#: How far back from the sub-league landmark the nest's own count may sit. `measured`: the
#: count and the first sub-league's id occupy the eight bytes immediately before the
#: abbreviation, and exactly one position in this window validates as a whole nest.
_NEST_SEARCH_WINDOW = 64

#: Refusals rather than long walks. Each is generous against what was measured — two
#: sub-leagues, three divisions apiece, five clubs a division.
_MAX_SUB_LEAGUES = 64
_MAX_DIVISIONS = 64
_MAX_DIVISION_TEAMS = 256
_MAX_SUB_LEAGUE_ABBR = 16
_MAX_SUB_LEAGUE_NAME = 64
_MAX_DIVISION_NAME = 64

#: One calendar record, in the order the bytes give it: `u32 seq`, `u32 league_id`,
#: `u16 event_type`, `u8 day, u8 month, u16 year`, three pad bytes, `u32 length` + name,
#: `u8 event_over`, `u8 deleted`, `u8 needs_human_action`, `u16 real_sim_date`. Everything
#: except the name is fixed width, which is what lets the lookahead validator below judge
#: a candidate record without a cursor. The decode itself is still strictly sequential.
_SEQ_WIDTH = 4
_LEAGUE_ID_WIDTH = 4
_EVENT_TYPE_WIDTH = 2
_DATE_WIDTH = 4
_EVENT_PAD_WIDTH = 3
_LENGTH_PREFIX_WIDTH = 4
_EVENT_TAIL_WIDTH = 5
_EVENT_HEAD_WIDTH = _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH + _DATE_WIDTH

#: `measured` — event names run 11 to 50 characters over all 3,058 entries of all three
#: saves. The bound is what keeps the motif search honest: a longer name in some future
#: save makes the array unfindable and raises, rather than matching somewhere else.
_MAX_EVENT_NAME = 120

#: A garbage count must refuse rather than loop. Generous: the measured calendar is 3,058.
_MAX_CALENDAR_EVENTS = 1_000_000

#: The narrowest byte pattern every calendar record shares: three zero pad bytes, then a
#: `u32` name length whose top three bytes are zero. `measured` — the pad is `000000` in
#: all 3,058 entries of all three saves. The lookahead makes the matches **overlapping**;
#: `re.finditer` without it consumes a match and can hide one starting four bytes later,
#: which is a gap a search cannot afford. This is a prefilter and nothing more: every hit
#: it produces is then validated by parsing an entire array.
_EVENT_MOTIF = re.compile(
    b"(?="
    + b"\x00" * _EVENT_PAD_WIDTH
    + b"[\x01-"
    + bytes((_MAX_EVENT_NAME,))
    + b"]"
    + b"\x00" * (_LENGTH_PREFIX_WIDTH - 1)
    + b")"
)

#: Plausibility bounds for a candidate record's date. A calendar entry may carry no date
#: at all (`0/0/0`), so zero is admitted rather than required to be a real day.
_MAX_DAY = 31
_MAX_MONTH = 12
_MIN_YEAR = 1800
_MAX_YEAR = 2200

#: An id has to fit in a `u16` to be an id. Used to refuse a league record head read from
#: the wrong place, where the four fields would be halves of doubles or of a string.
_MAX_ID = 1 << 16


class WorldRecordLayout(SaveFormatError):  # noqa: N818
    """A valid version-25 `world.dat` whose regions are not shaped as measured.

    Distinct from the header refusals: those mean *this is not the file you think it is*,
    this one means *the file is what it claims and one of its regions does not match the
    layout every save on disk shares*. A game patch is the likely cause, and the useful
    response is to re-measure rather than to loosen the reader.
    """


class AmbiguousWorldLandmark(SaveFormatError):  # noqa: N818
    """A landmark resolved to no position, or to more than one.

    **Both are errors and neither is resolvable by guessing.** Zero matches would otherwise
    return a world with no divisions and no calendar — indistinguishable downstream from a
    league that has neither. Several matches would mean taking the first, which is a coin
    flip dressed as a parse.
    """


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """One entry of the league calendar, as the file writes it.

    Nine fields: the eight the export validated, plus `seq`, which the export does not
    expose and which is the only field unique across all 3,058 entries. **The grain rests
    on `seq`** — the human-readable alternative `(league_id, start_date, event_type, name)`
    collapses 3,058 rows to 2,600, losing 458 events with nothing raised.

    `event_type` is the raw enum. No label is offered and none should be added: the
    semantics are undocumented, and a wrong human label produces a confidently wrong
    calendar that throws nothing.

    `event_over`, `deleted` and `needs_human_action` are `u8` flags landed as **integers**.
    Every observed value is 0 or 1; collapsing them to `bool` would assert a domain nothing
    has proven and would destroy the evidence the day it stops holding.

    `real_sim_date` is a `u16` whose meaning is `unconfirmed` — `measured` 0 on all 3,058
    entries of all three saves, so nothing here can say what a non-zero one would mean. It
    is landed raw because a field crossed and dropped is a field nobody can ask about later.
    """

    seq: int
    league_id: int
    event_type: int
    start_date: SaveDate
    name: str
    event_over: int
    deleted: int
    needs_human_action: int
    real_sim_date: int


@dataclass(frozen=True, slots=True)
class DivisionMembership:
    """One division, and the clubs it names.

    The array is the point. The file writes membership from the division's side — a `u32`
    count then explicit `team_id`s — while the export writes it from the club's side, as a
    `division_id` column. Neither was derived from the other, which is what makes their
    agreement worth something.

    **`teams.division_id` is derived from this in silver and never parsed.** `teams.dat`
    does not carry it (`measured`, 0 of 140 on the clubs that have a non-zero one), so a
    division stamped onto a team record could only have come from a join, and bronze does
    not join.

    Clubs that no division names are **structurally absent**, not zero. The four All-Star
    sides appear in no array at all; the export renders that as `division_id = 0`, which
    reads like a value and is not one.
    """

    league_id: int
    sub_league_id: int
    division_id: int
    team_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class WorldRegion:
    """One span of the file this walk entered, and what it claimed while it was there.

    `entered_at` is the offset of the first byte the region's walk consumed and `length` is
    how many bytes it consumed from there, so `[entered_at, entered_at + length)` is
    exactly the span the walk read and accounted for — and any byte outside every region is
    one this walk never touched.

    `declared_count` is what the region's own count prefix said; `parsed_count` is what the
    walk produced. Keeping both means the self-check is auditable after the fact rather
    than being an assertion that ran once inside the parser and left no trace. The two come
    from independent code paths — the lookahead scan that validates the entry, and the
    cursor that reads it — so their agreement is a real check rather than a tautology.
    """

    name: str
    entered_at: int
    length: int
    declared_count: int
    parsed_count: int


@dataclass(frozen=True, slots=True)
class WorldFile:
    """Everything one walk of `world.dat` produced, including what it never read.

    `file_bytes` is here so the un-walked remainder is derivable from outside rather than
    asserted by the parser about itself: a walker that supplies both halves of an identity
    can be internally consistent and still wrong about the file, while one that reports the
    size the operating system also knows cannot.
    """

    sim_date: SaveDate
    divisions: tuple[DivisionMembership, ...]
    calendar: tuple[CalendarEvent, ...]
    regions: tuple[WorldRegion, ...]
    file_bytes: int


def read_world(payload: bytes) -> WorldFile:
    """Walk `world.dat`'s two reachable regions, and report what was not walked.

    Raises:
        MalformedHeader: the buffer is truncated, or is not an OOTP record file.
        UnsupportedSaveVersion: the declared version is not the one we are proven on.
        SaveFilenameMismatch: the header names a different file.
        UnexpectedEndOfData: a read ran past the end of the buffer.
        WorldRecordLayout: the record count, a region's shape, or a declared count is not
            what every save measured holds.
        AmbiguousWorldLandmark: a landmark resolved to zero positions, or to several.
    """
    cursor = Cursor(payload, label=WORLD_FILE)
    header = read_header_from(cursor, WORLD_FILE)
    _read_header_tail(cursor)

    divisions_region, divisions = _walk_divisions(cursor, payload)
    calendar_region, calendar = _walk_calendar(cursor, payload)

    return WorldFile(
        sim_date=header.sim_date,
        divisions=divisions,
        calendar=calendar,
        regions=(divisions_region, calendar_region),
        file_bytes=len(payload),
    )


def read_calendar(cursor: Cursor) -> tuple[CalendarEvent, ...]:
    """Read a `u32`-count-prefixed calendar array from wherever the cursor stands.

    Public and callable on its own, deliberately. The landmark search needs an 8.9 MB file
    and can only run on a machine that has one; the record decoder needs 40 bytes, and the
    decoder is where a width error lives. Keeping this seam open is what gives the inner
    half of the `region-accounted` claim — *zero residual within the walked region* — a
    test that runs in CI on every change.

    **The declared count is authoritative, and the boundary check belongs to the caller.**
    This function consumes exactly what the region claims and stops: it cannot know what
    follows, because what follows is another region. An over-declared count runs off the
    end and raises; an under-declared one leaves the cursor un-exhausted, which is what
    `read_world` turns into a refusal by requiring the walk to land where it expected to.

    Raises:
        WorldRecordLayout: the declared count is not a calendar.
        UnexpectedEndOfData: the region ran out of bytes before the count was satisfied.
    """
    declared = cursor.u32()
    if declared > _MAX_CALENDAR_EVENTS:
        raise WorldRecordLayout(
            f"{WORLD_FILE}: an array declaring {declared} calendar entries is not a "
            f"calendar — the measured league carries 3,058 and the refusal is at "
            f"{_MAX_CALENDAR_EVENTS}. The walk is reading a count from the wrong place."
        )
    return tuple(_read_event(cursor) for _ in range(declared))


# ── the header tail ──────────────────────────────────────────────────────────


def _read_header_tail(cursor: Cursor) -> None:
    """Read the six `u32`s after the header's two wide dates and check the record count.

    `header.py` is explicit that the header continues past the dates and that its true end
    is `unconfirmed`, so this is a width measured for *this file* rather than a general
    claim. Field 5 is the record count and reads 1 here — the whole world is one record,
    which is the reason this file needs a landmark at all.
    """
    values = tuple(cursor.u32() for _ in range(_HEADER_TAIL_FIELDS))
    declared = values[4]
    if declared != _WORLD_RECORD_COUNT:
        raise WorldRecordLayout(
            f"{WORLD_FILE} declares {declared} records; every save measured declares "
            f"{_WORLD_RECORD_COUNT}, because the world is one nested record. A different "
            "value means the header tail is not where this walk believes it is."
        )


# ── the divisions region ─────────────────────────────────────────────────────


def _walk_divisions(
    cursor: Cursor, data: bytes
) -> tuple[WorldRegion, tuple[DivisionMembership, ...]]:
    """Enter the top league's record, cross its scalars, and read its division nest.

    Two landmarks, because the league record's head and its sub-league nest sit ~1,170
    bytes apart with an unmapped scalar block between them. The gap is crossed at a width
    computed from the two search results — never a constant, and never the same number
    asserted twice.
    """
    league_head = _find_league_record(data, cursor.position)
    nest_anchor = _find_unique(data, _sub_league_anchor(), league_head, "the sub-league")
    nest_head, declared = _find_division_nest(data, nest_anchor, league_head)

    cursor.skip(league_head - cursor.position)
    league_id = _read_league_head(cursor)

    if nest_head < cursor.position:
        raise WorldRecordLayout(
            f"{WORLD_FILE}: the sub-league nest at {nest_head} sits inside the league "
            "record's own head, so one of the two landmarks is not what it appears to be"
        )
    cursor.skip(nest_head - cursor.position)
    divisions = _read_division_nest(cursor, league_id)

    if len(divisions) != declared:  # pragma: no cover - the scan and the read agree
        raise WorldRecordLayout(
            f"{WORLD_FILE}: the nest declares {declared} divisions and the walk read "
            f"{len(divisions)}. The lookahead scan and the cursor disagree about the same "
            "bytes, so one of them is reading a different structure."
        )

    return (
        WorldRegion(
            name="divisions",
            entered_at=league_head,
            length=cursor.position - league_head,
            declared_count=declared,
            parsed_count=len(divisions),
        ),
        tuple(divisions),
    )


def _find_league_record(data: bytes, floor: int) -> int:
    """Where the top league's record begins, from the unique occurrence of its name.

    The head is `_LEAGUE_HEAD_FIELDS` `u32`s in front of the name — `league_id, nation_id,
    language_id, gender`, `measured` 203/206/0/0 and matching the export's `leagues` row
    for MLB field for field. Those four are fixed-width with no variable-length region
    among them, which is what makes the head reachable from the name at all; a record whose
    head held a string could not be entered this way and would need a different landmark.

    The proposal is checked when it is read: `_read_league_head` requires the name that
    follows the four fields to be the landmark itself, so a head proposed at the wrong
    place cannot survive.
    """
    anchor = _find_unique(data, _league_anchor(), floor, "the league")
    head = anchor - _LEAGUE_HEAD_FIELDS * _LENGTH_PREFIX_WIDTH
    if head < floor:
        raise WorldRecordLayout(
            f"{WORLD_FILE}: the league name at {anchor} leaves no room for the record head "
            "in front of it, so the match is not the league record it looks like"
        )
    return head


def _read_league_head(cursor: Cursor) -> int:
    """Consume the league record's four leading ids and its name, and return the id.

    Every field is required to look like an id, and the name is required to *be* the
    landmark. Together those refuse a head read from the wrong place: four halves of
    doubles do not all fit in a `u16`, and the string after them is not the league's name.
    """
    head = tuple(cursor.u32() for _ in range(_LEAGUE_HEAD_FIELDS))
    league_id = head[0]
    if league_id == 0 or any(value >= _MAX_ID for value in head):
        raise WorldRecordLayout(
            f"{WORLD_FILE}: the fields ahead of the league's name read {list(head)}, which "
            "are not four ids. Measured, they are league_id, nation_id, language_id and "
            "gender, and they match the export's own league row value for value."
        )

    name = cursor.string()
    if name != _LEAGUE_NAME:  # pragma: no cover - the landmark pins the name
        raise WorldRecordLayout(
            f"{WORLD_FILE}: expected {_LEAGUE_NAME!r} after the league record head and read "
            f"{name!r}, so the head is not {_LEAGUE_HEAD_FIELDS} u32s wide in this save."
        )
    return league_id


def _find_division_nest(data: bytes, anchor: int, floor: int) -> tuple[int, int]:
    """`(offset, declared_divisions)` for the sub-league array that contains `anchor`.

    A bounded backward scan, validated forward: every position in the window before the
    landmark is tried as a `u32` sub-league count, and one is kept only if the **entire**
    nest below it parses — abbreviations, names, per-division team arrays and all — and if
    its span actually contains the landmark that found it.

    `measured`: exactly one position validates in each of the three saves, at the eight
    bytes before the abbreviation — the count, then the first sub-league's id. Refusing on
    zero or several is the point; the alternative is entering something that merely looks
    like a nest and landing a plausible wrong hierarchy with nothing raised.
    """
    matches = [
        (offset, found)
        for offset in range(max(floor, anchor - _NEST_SEARCH_WINDOW), anchor)
        if (found := _scan_division_nest(data, offset, anchor)) is not None
    ]
    if len(matches) != 1:
        raise AmbiguousWorldLandmark(
            f"{WORLD_FILE}: {len(matches)} positions in the {_NEST_SEARCH_WINDOW} bytes "
            f"before the sub-league landmark at {anchor} parse as a complete sub-league "
            "nest, expected exactly one. Every save measured carries the count and the "
            "first sub-league's id immediately in front of the abbreviation."
        )
    offset, (declared, _) = matches[0]
    return offset, declared


def _scan_division_nest(data: bytes, offset: int, anchor: int) -> tuple[int, int] | None:
    """`(declared_divisions, end)` if a whole sub-league nest starts at `offset`.

    Nothing here consumes: the cursor reads the same bytes afterwards and the two are
    required to agree. This is the posture `teams.py` takes — decide every variable width
    by looking ahead, then read forward at exactly those widths.
    """
    count = _peek_u32(data, offset)
    if count is None or not 0 < count <= _MAX_SUB_LEAGUES:
        return None

    position = offset + _LENGTH_PREFIX_WIDTH
    declared = 0
    for _ in range(count):
        position += 4  # sub_league_id
        for limit in (_MAX_SUB_LEAGUE_ABBR, _MAX_SUB_LEAGUE_NAME):
            read = _scan_string(data, position, limit)
            if read is None:
                return None
            position = read
        position += 4 + 1  # gender, designated hitter
        divisions = _peek_u32(data, position)
        if divisions is None or divisions > _MAX_DIVISIONS:
            return None
        position += 4
        declared += divisions
        for _ in range(divisions):
            position += 4  # division_id
            read = _scan_string(data, position, _MAX_DIVISION_NAME)
            if read is None:
                return None
            position = read + 4  # gender
            teams = _peek_u32(data, position)
            if teams is None or teams > _MAX_DIVISION_TEAMS:
                return None
            position += 4 + 4 * teams
            if position > len(data):
                return None

    if not offset < anchor < position:
        return None
    return declared, position


def _read_division_nest(cursor: Cursor, league_id: int) -> list[DivisionMembership]:
    """Read the nest the scan validated, at the widths the file itself declares."""
    memberships: list[DivisionMembership] = []
    sub_leagues = cursor.u32()
    for _ in range(sub_leagues):
        sub_league_id = cursor.u32()
        cursor.string()  # abbreviation — not landed; the id is the key
        cursor.string()  # name — likewise
        cursor.u32()  # gender
        cursor.u8()  # designated hitter
        divisions = cursor.u32()
        for _ in range(divisions):
            division_id = cursor.u32()
            cursor.string()  # division name
            cursor.u32()  # gender
            teams = cursor.u32()
            team_ids = tuple(cursor.u32() for _ in range(teams))
            memberships.append(
                DivisionMembership(
                    league_id=league_id,
                    sub_league_id=sub_league_id,
                    division_id=division_id,
                    team_ids=team_ids,
                )
            )
    return memberships


# ── the calendar region ──────────────────────────────────────────────────────


def _walk_calendar(cursor: Cursor, data: bytes) -> tuple[WorldRegion, tuple[CalendarEvent, ...]]:
    """Find the calendar array ahead of the cursor, and read it through the cursor."""
    head, declared = _find_calendar_array(data, cursor.position)
    cursor.skip(head - cursor.position)
    events = read_calendar(cursor)

    if len(events) != declared:  # pragma: no cover - both paths read the same count
        raise WorldRecordLayout(
            f"{WORLD_FILE}: the calendar declares {declared} entries and the walk read "
            f"{len(events)}. The lookahead scan and the cursor disagree about the same "
            "bytes, so one of them is reading a different structure."
        )

    return (
        WorldRegion(
            name="calendar",
            entered_at=head,
            length=cursor.position - head,
            declared_count=declared,
            parsed_count=len(events),
        ),
        events,
    )


def _find_calendar_array(data: bytes, floor: int) -> tuple[int, int]:
    """`(offset, declared_events)` for the one count-prefixed calendar array in the file.

    No string can find this region — the schedule in front of it is prefixed with a
    per-league game count, so its head cannot be located without already knowing the
    number. So the calendar is found by what it is: a `u32` count followed by exactly that
    many records that all decode, with strictly increasing `seq`, **maximal in both
    directions**.

    Right-maximality alone leaves two survivors per save: the real array, and its own last
    record, whose preceding four bytes read as a count of 1. Left-maximality — no calendar
    record may end exactly where the count begins — removes it, and every other mid-array
    candidate with it, because a mid-array candidate always has a record ending there.
    `measured`: one survivor in each of the three saves.
    """
    matches: list[tuple[int, int]] = []
    for hit in _EVENT_MOTIF.finditer(data, floor):
        offset = hit.start() - _EVENT_HEAD_WIDTH - _LENGTH_PREFIX_WIDTH
        if offset < floor:
            continue
        found = _scan_calendar_array(data, offset)
        if found is None:
            continue
        declared, end = found
        if _scan_event(data, end) is not None or not _is_left_maximal(data, offset):
            continue
        matches.append((offset, declared))

    if len(matches) != 1:
        raise AmbiguousWorldLandmark(
            f"{WORLD_FILE}: {len(matches)} positions after byte {floor} parse as a "
            "complete, maximal calendar array, expected exactly one. Zero means the "
            "calendar was not found, and an empty calendar is indistinguishable from a "
            "league with no events; several means the array can no longer be identified by "
            "its own shape. Neither is safe to resolve by taking a match."
        )
    return matches[0]


def _scan_calendar_array(data: bytes, offset: int) -> tuple[int, int] | None:
    """`(declared, end)` if a `u32` count at `offset` is followed by that many events."""
    declared = _peek_u32(data, offset)
    if declared is None or not 0 < declared <= _MAX_CALENDAR_EVENTS:
        return None

    position = offset + _LENGTH_PREFIX_WIDTH
    previous: int | None = None
    for _ in range(declared):
        found = _scan_event(data, position)
        if found is None:
            return None
        seq, position = found
        if previous is not None and seq <= previous:
            return None
        previous = seq
    return declared, position


def _scan_event(data: bytes, offset: int) -> tuple[int, int] | None:
    """`(seq, end)` if a calendar record starts at `offset`, judged on shape alone.

    Deliberately narrow, because this is what separates the calendar from 8.9 MB of
    everything else: a date that could be a date or is absent entirely, three zero pad
    bytes, and a printable name that fits inside the buffer. The three flag bytes are
    **not** constrained — their domain is a question about the format, and a value outside
    {0, 1} should arrive as a red test rather than as a region this walk cannot find.
    """
    seq = _peek_u32(data, offset)
    if seq is None:
        return None

    pad_at = offset + _EVENT_HEAD_WIDTH
    length_at = pad_at + _EVENT_PAD_WIDTH
    if data[pad_at:length_at] != b"\x00" * _EVENT_PAD_WIDTH:
        return None

    date_at = offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH
    day = data[date_at]
    month = data[date_at + 1]
    year = int.from_bytes(data[date_at + 2 : date_at + _DATE_WIDTH], "little")
    if day > _MAX_DAY or month > _MAX_MONTH:
        return None
    if year != 0 and not _MIN_YEAR <= year <= _MAX_YEAR:
        return None

    length = _peek_u32(data, length_at)
    if length is None or not 0 < length <= _MAX_EVENT_NAME:
        return None
    name_at = length_at + _LENGTH_PREFIX_WIDTH
    end = name_at + length + _EVENT_TAIL_WIDTH
    if end > len(data):
        return None
    if any(byte < 0x20 or byte > 0x7E for byte in data[name_at : name_at + length]):
        return None
    return seq, end


def _is_left_maximal(data: bytes, offset: int) -> bool:
    """Is there no calendar record ending exactly where this candidate's count begins?

    The window is the widest record the scan admits, so it covers every record that could
    reach the count. A mid-array candidate always fails here — the previous record ends
    exactly at its head — which is what reduces thousands of self-similar candidates to the
    one array head.
    """
    boundary = offset + _LENGTH_PREFIX_WIDTH
    fixed = _EVENT_HEAD_WIDTH + _EVENT_PAD_WIDTH + _LENGTH_PREFIX_WIDTH + _EVENT_TAIL_WIDTH
    first = max(0, boundary - fixed - _MAX_EVENT_NAME)
    last = boundary - fixed - 1
    return not any(
        (found := _scan_event(data, start)) is not None and found[1] == boundary
        for start in range(first, last + 1)
    )


def _read_event(cursor: Cursor) -> CalendarEvent:
    """One calendar record, read forward with every width taken from the record itself.

    The name is length-prefixed, so every field after it sits at a different absolute
    offset in a short-named record than in a long-named one. Reading them in order is the
    only thing that makes that a non-event.
    """
    seq = cursor.u32()
    league_id = cursor.u32()
    event_type = cursor.u16()
    start_date = cursor.date()
    cursor.skip(_EVENT_PAD_WIDTH)
    name = cursor.string()
    event_over = cursor.u8()
    deleted = cursor.u8()
    needs_human_action = cursor.u8()
    real_sim_date = cursor.u16()
    return CalendarEvent(
        seq=seq,
        league_id=league_id,
        event_type=event_type,
        start_date=start_date,
        name=name,
        event_over=event_over,
        deleted=deleted,
        needs_human_action=needs_human_action,
        real_sim_date=real_sim_date,
    )


# ── landmarks and lookahead ──────────────────────────────────────────────────


def _league_anchor() -> bytes:
    """The league's name as it appears on disk: `u32` length prefix **and** payload."""
    return _prefixed(_LEAGUE_NAME)


def _sub_league_anchor() -> bytes:
    """The first sub-league's abbreviation and name, matched as one composite.

    Either alone would be far too common — `AL` is two bytes. Together, and with both
    length prefixes, they occur exactly once per save.
    """
    return _prefixed(_SUB_LEAGUE_ABBR) + _prefixed(_SUB_LEAGUE_NAME)


def _prefixed(value: str) -> bytes:
    return struct.pack("<I", len(value)) + value.encode("ascii")


def _find_unique(data: bytes, pattern: bytes, floor: int, what: str) -> int:
    """The one position at or after `floor` where `pattern` occurs, or a refusal.

    A search, never a seek: the walk scans forward from where it already stands and the
    answer is a position discovered in the data. Requiring uniqueness is what makes it
    safe — the quiet failure available to a landmark walk is finding nothing and returning
    an empty world, and the noisy one is finding several and taking the first.
    """
    first = data.find(pattern, floor)
    if first < 0:
        raise AmbiguousWorldLandmark(
            f"{WORLD_FILE}: {what} landmark {pattern[_LENGTH_PREFIX_WIDTH:]!r} does not "
            f"occur after byte {floor}. Refusing rather than returning a world with no "
            "divisions and no calendar, which nothing downstream could tell apart from a "
            "league that has neither."
        )
    if data.find(pattern, first + 1) >= 0:
        raise AmbiguousWorldLandmark(
            f"{WORLD_FILE}: {what} landmark {pattern[_LENGTH_PREFIX_WIDTH:]!r} occurs more "
            f"than once after byte {floor}. It was measured unique in all three saves on "
            "disk; taking the first match would be a guess about which region the walk is "
            "entering."
        )
    return first


def _scan_string(data: bytes, position: int, limit: int) -> int | None:
    """The offset just past a length-prefixed printable ASCII string, or `None`.

    Printability is what keeps this from firing on integer data: the high bytes of a small
    `u32` are nulls, and a null is not a character a division's name contains.
    """
    length = _peek_u32(data, position)
    if length is None or length > limit or position + 4 + length > len(data):
        return None
    payload = data[position + 4 : position + 4 + length]
    if any(byte < 0x20 or byte > 0x7E for byte in payload):
        return None
    return position + 4 + length


def _peek_u32(data: bytes, position: int) -> int | None:
    """The `u32` at `position` without consuming it, or `None` past the end.

    A lookahead at a position computed from the data — a landmark match, or a width the
    file itself declared — never at a constant. The cursor stays forward-only, and every
    width it is later asked to advance by was decided here.
    """
    if position + 4 > len(data):
        return None
    return int.from_bytes(data[position : position + 4], "little")
