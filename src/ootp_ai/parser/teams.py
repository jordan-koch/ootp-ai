"""`teams.dat` — a sequential walk of a file that omits every field it can.

**Read this docstring before the code.** The record layout is not a fixed sequence of
typed fields, and a reader written as if it were is wrong on most of the league while
looking right on Boston.

## The one thing that explains the whole module

**A team record omits a field entirely when its value is falsy.** An integer that is zero
is not written. A string that is empty is not written. `measured` 2026-08-16 against all
three saves on disk, with `ootp_truth_real` as the oracle for the standard-mode probe:
the pre-colour integer run is `[city_id, park_id, league_id, sub_league_id, nation_id,
human]` with zeros dropped, and that model reproduces **259 of 259** records in two
independent saves. The export's own column order scores **0 of 259**.

So the parser's job is the *inverse* of that encoding: given a run of values, work out
which fields are present. The run alone does not say. `[25, 203]` could be
`(city_id 25, league 203)`, `(park_id 25, league 203)` or `(league 25, nation 203)`, and
the difference between the first two decides whether a club is in Arizona or plays in
Chase Field.

## What makes the inverse decidable, and where it stops

Four constraints, each `measured` and each stated as a domain fact rather than a
convenience:

1. **`league_id` is never zero** — every club belongs to a league — so it is always
   written.
2. **`park_id` is never zero** — every club has a ballpark; 259 of 259 in the export,
   range 1..198 — so it is always written too. Those two together pin the run's spine.
3. **`sub_league_id` and the human flag are 0/1**, so a *written* one is exactly 1. That
   single fact eliminates every wrong reading of a four- or five-value run.
4. Anything still ambiguous is resolved against **the file's own unambiguous records**:
   a `league_id` must be one that some unambiguous record also carries, a `nation_id`
   likewise, and at most one club in a save is the human's. `measured`: exactly two
   records in each save need this, and they are the National League All-Star sides,
   whose run is `[20, 203, 1]`.

A record that survives none of that, or more than one of it, raises
`AmbiguousTeamRecord`. **Guessing here is the specific failure this project cannot
afford**: a walker fitted to the one save with an answer key scores perfectly against
that answer key and is wrong on the league we actually manage.

## The record, in the order the bytes give it

| # | Field | Status |
|---|---|---|
| 1 | `u32 team_id`, ascending across the file | `verified` |
| 2 | up to five strings — city, abbreviation, nickname, logo filename, full name | `verified`, with two slots droppable (below) |
| 3 | the drop-zero integer run above | `measured` |
| 4 | exactly three `u32` ARGB colours, alpha `0xff` | `measured` — they are never zero, so they are never dropped, which is what makes them a reliable boundary |
| 5 | `u32 level`, never zero | `measured` — 259 of 259 |
| 6 | a drop-zero `u32` array of **organisation links** | `measured` |
| 7 | a drop-zero run of `u8` flags, every one of them `0x01` | `measured` |
| 8 | `historical_id`, a length-prefixed franchise code, empty on all but 30 clubs | `measured` |
| 9 | a second short code, a zero block, the club's asset filenames, more colours — **not decoded**; the walk stops at `historical_id` | `unconfirmed` |

**The organisation links are one array with two meanings, and reading it right is what
distinguishes an affiliate from a club.** A club lists its *affiliates* there (6 or 7 for
a major-league franchise); an affiliate lists its *parent* (exactly one). Nothing in the
bytes says which, so `parent_team_id` is taken only where **both records agree** — `b`
appears in `a`'s links and `a` appears in `b`'s — with `level` giving the direction. That
is internal, needs no export, and on the standard-mode probe it reproduces the export's
`parent_team_id` for all 259 rows.

It also disposes of this walk's one soft edge. The link array ends when the next `u32`
stops looking like a team id, and a couple of the byte patterns that follow it read as
small integers and get swallowed as a spurious link — `measured`, the only values ever
swallowed across the three saves are **1** and **257**, which are one and two flag bytes
in front of an empty franchise code. Neither points back, so neither survives the mutual
test. Guessing "the first link is the parent when the level is below the top" does not
survive it either: the managed league has parented clubs eight levels down, and 55 clubs
whose spurious `1` would have made them affiliates of Arizona.

## Two slots of the string signature are droppable, and the saves disagree about which

`docs/data-access.md` records a five-string signature `verified`. It is five strings *when
all five are non-empty*. Measured:

* **26 records in each probe carry no city string** — the minor-league All-Star sides.
* **289 records in the managed league carry no logo filename**, because a
  freshly-created league has no logo assets for its minor-league clubs.

So the walk determines the string count by **parsing forward and requiring the rest of the
record to validate** — three colours are a very specific signature — and then assigns the
slots by asking whether the third string is an asset filename. **Both droppable slots land
`None` when the record does not carry them**, never `""`: the writer drops a slot whose
value is falsy, so an empty string and an absent one are indistinguishable on disk, and
"not present" is the only reading that does not assert something the bytes never said.

## Framing, and why this is a search rather than a seek

Records are separated by variable-length bodies of 1.5 KB to 60 KB that this walk does not
decode. Each record is preceded by nine zero bytes and a `0x28` byte; the walk locates the
next one by **searching forward from where it currently is**, never by jumping to an
offset, and validates each candidate by requiring the following `u32` to be a team id
greater than the last one seen. The header tail declares the record count — 259 in both
probes, 337 in the managed league — and the walk stops when it has that many, so a
mis-framed file runs out of records and raises rather than returning a short league.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.header import read_header_from
from ootp_ai.parser.primitives import Cursor, SaveDate

__all__ = [
    "BYTE_ACCOUNTING_TIER",
    "TEAMS_FILE",
    "TIER_RATIONALE",
    "AmbiguousTeamRecord",
    "TeamRecord",
    "TeamRecordLayout",
    "TeamsFile",
    "read_teams",
]

#: Sits inside the `.lg` directory, beside `players.dat` and `names.dat`.
TEAMS_FILE = "teams.dat"

#: Phase 0 pre-registered `strict` and `diagnostic`; `region-accounted` was added later for
#: `world.dat`. This walk is `diagnostic`, and the reason is in `TIER_RATIONALE` rather
#: than in a shrug.
BYTE_ACCOUNTING_TIER = "diagnostic"

TIER_RATIONALE = (
    "Reached: the header, the version guard, the six-u32 header tail with its declared "
    "record count, and every record's head — id, string signature, the drop-zero integer "
    "run, the three colours, level, the organisation links, the flag run and "
    "historical_id — for all 259 records of both probes and all 337 of the managed "
    "league. Not reached: the record BODY. Each record is followed by 1.5 KB to 60 KB of "
    "undecoded bytes (team history and season stats, on the evidence of their size), and "
    "the walk crosses them by searching forward for the next record's frame rather than "
    "by reading them. Those bytes are consumed but not accounted for, so calling this "
    "walk strict would be a false claim about roughly 85% of the file. The residual this "
    "module reports is what is left AFTER the last record's head: the final record's own "
    "body plus the file's trailing region, ~1.1 KB in the probes and ~2.3 KB in the "
    "managed league, which is well under one mean record and is the diagnostic tier's "
    "real assertion. A later attempt at strict should start from the ~344-byte "
    "bit-packed preamble between the header tail and the first record, which is constant "
    "per file type and is the most likely home of a field-type table."
)

#: Nine zero bytes and a `0x28`, immediately before every record's `team_id`. `measured` —
#: matching this and requiring an ascending, in-range team id after it locates exactly the
#: declared record count in all three saves. A search, never an offset.
_RECORD_FRAME = b"\x00" * 9 + b"\x28"

#: How many `u32`s follow the header's two wide dates before the record region.
#: A width, not an offset — the cursor walks to it and never jumps.
_HEADER_TAIL_FIELDS = 6

#: Refuse a declared record count that is not a league. Guards against reading a garbage
#: count as a loop bound and scanning a 4.5 MB file forever.
_MAX_RECORDS = 100_000

#: Three ARGB colours, always, alpha `0xff`. Because a colour is never zero it is never
#: dropped, which is what makes the run of them a dependable boundary between the integer
#: run and everything after it.
_COLOR_COUNT = 3
_ALPHA = 0xFF

#: The six-field pre-colour run is the longest legal one.
_MAX_INTEGER_RUN = 6

#: String-count shapes the signature is allowed to take. `measured`: 5 (everything
#: present), 4 (no city, or no logo) and 3 (neither). Exactly one of them validates for
#: every record in every save on disk.
_SIGNATURE_SHAPES = (3, 4, 5)

#: A club name, nickname or asset filename. Nothing measured comes close.
_MAX_STRING = 128

#: `historical_id` is a franchise abbreviation — `measured`, every value in the export is
#: 3 characters or empty, over 259 rows.
_MAX_SHORT_STRING = 8

#: The drop-zero `u8` run between the organisation links and `historical_id`. `measured`:
#: 0 to 4 bytes, and every byte written is `0x01`.
_FLAG_BYTE = b"\x01"
_MAX_FLAGS = 8

#: One club's organisation links: 6 or 7 affiliates on a top-level club, one parent on an
#: affiliate. The cap turns a lost alignment into a refusal instead of a long walk.
_MAX_LINKS = 64

#: The three fields that may follow `league_id` in the run, in the order the bytes carry
#: them. Two of them are 0/1 flags, which is what makes the inverse decidable.
_SUB_LEAGUE, _NATION, _HUMAN = 0, 1, 2


class TeamRecordLayout(SaveFormatError):  # noqa: N818
    """A valid version-25 `teams.dat` whose records are not shaped as measured.

    Distinct from the header refusals: those mean *this is not the file you think it is*,
    this one means *the file is what it claims and one of its records does not match the
    layout every save on disk shares.* A game patch is the likely cause, and the useful
    response is to re-measure rather than to loosen the reader.
    """


class AmbiguousTeamRecord(SaveFormatError):  # noqa: N818
    """A record whose omitted fields cannot be reconstructed to a single reading.

    Raised rather than resolved by preference. The drop-zero encoding means the byte
    stream is not self-describing; where the domain constraints and the file's own
    unambiguous records still leave two readings standing, picking one would put a
    plausible wrong hierarchy into bronze with nothing raised.
    """


@dataclass(frozen=True, slots=True)
class TeamRecord:
    """One club as `teams.dat` describes it.

    The field set is pinned by `tests/test_parse_teams_synthetic.py` and is a decision
    rather than an accident: every landed field is a field somebody re-validates after a
    game patch.

    **`division_id` and `allstar_team` are deliberately absent — they are not in this
    file.** Inserting `division_id` into the integer model scores 0 of 140 on the teams
    that have a non-zero one, and appending `allstar_team` scores 0 of 30 on the All-Star
    sides; each is its own discriminating subset. Division membership lives in `world.dat`
    as an explicit per-division team array, so `division_id` is derived in silver and
    never parsed. So is the standings region, which is not here either.

    **`human_team` is one flag, and its ambiguity is written down rather than resolved.**
    The last slot of the integer run is either `human_team` or `human_id`; both columns are
    1 on the single managed club and 0 everywhere else, so no oracle available can
    separate them, and 18 field orders fit the observed bytes equally well. Landing one
    flag beats landing two fields when only one was observed. A save with two human
    managers would settle it.

    `city` and `historical_id` are optional because the record does not always carry them,
    and an absent string is not the empty string: `None` means *no city name in the byte
    stream* and *no real-world franchise code*, which are different facts from `''`.

    `level`, `league_id`, `sub_league_id`, `nation_id`, `city_id`, `park_id` and
    `parent_team_id` are **not** optional, and that is load-bearing in the opposite
    direction. `measured`: `sub_league_id` 0 is the American League (242 of 259 teams) and
    `parent_team_id` 0 means "no parent" on all 34 top-level clubs. Their zeros are values
    the walker *reconstructs from the field's absence*; mapping one to `None` for tidiness
    would erase half of baseball.
    """

    team_id: int
    city: str | None
    abbr: str
    nickname: str
    logo_filename: str | None
    full_name: str
    colors: tuple[int, ...]
    city_id: int
    park_id: int
    league_id: int
    sub_league_id: int
    nation_id: int
    human_team: bool
    level: int
    parent_team_id: int
    historical_id: str | None


@dataclass(frozen=True, slots=True)
class TeamsFile:
    """Everything one walk of `teams.dat` produced, including what it could not account for.

    `residual_bytes` is the whole point of the type: a walker that returns only records
    cannot be asked how much of the file it failed to account for, and an unanswerable
    question gets answered optimistically. Read `TIER_RATIONALE` for exactly what this
    number does and does not claim.
    """

    teams: tuple[TeamRecord, ...]
    residual_bytes: int
    sim_date: SaveDate


@dataclass(frozen=True, slots=True)
class _HeaderTail:
    """The six `u32`s between the header's second wide date and the record region."""

    written_hour: int
    written_minute: int
    written_second: int
    declared_field_count: int
    declared_record_count: int
    constant: int


@dataclass(frozen=True, slots=True)
class _Shape:
    """How wide each variable region of one record is, decided before anything is read.

    Computed by looking ahead over the buffer from the cursor's own position and never
    from a constant. The cursor then consumes exactly these widths, so the reading half of
    the walk stays a plain forward sequence of typed reads.
    """

    string_count: int
    run_length: int
    link_count: int
    flag_count: int


@dataclass(frozen=True, slots=True)
class _Reading:
    """One way the drop-zero integer run could be assigned to fields."""

    city_id: int
    park_id: int
    league_id: int
    sub_league_id: int
    nation_id: int
    human_team: bool


@dataclass(frozen=True, slots=True)
class _RawTeam:
    """A record's decoded head, before the file-level pass resolves its integer run."""

    team_id: int
    city: str | None
    abbr: str
    nickname: str
    logo_filename: str | None
    full_name: str
    colors: tuple[int, ...]
    run: tuple[int, ...]
    level: int
    links: tuple[int, ...]
    historical_id: str | None


def read_teams(data: bytes) -> TeamsFile:
    """Walk a `teams.dat` buffer and return every club it declares.

    Raises:
        MalformedHeader: the buffer is truncated, or is not an OOTP record file.
        UnsupportedSaveVersion: the declared version is not the one we are proven on.
        SaveFilenameMismatch: the header names a different file.
        UnexpectedEndOfData: a read ran past the end of the buffer.
        TeamRecordLayout: a record is not shaped the way every save measured is shaped,
            or the file holds fewer records than its own header declares.
        AmbiguousTeamRecord: a record's omitted fields admit more than one reading.
    """
    cursor = Cursor(data, label=TEAMS_FILE)
    header = read_header_from(cursor, TEAMS_FILE)
    tail = _read_header_tail(cursor)

    declared = tail.declared_record_count
    if not 0 < declared <= _MAX_RECORDS:
        raise TeamRecordLayout(
            f"{TEAMS_FILE} declares {declared} records, which is not a league. The header "
            "tail is not where this walk believes it is, and every width after it would "
            "be read from the wrong place."
        )

    raw: list[_RawTeam] = []
    previous_id = 0
    while len(raw) < declared:
        frame = data.find(_RECORD_FRAME, cursor.position)
        if frame < 0:
            raise TeamRecordLayout(
                f"{TEAMS_FILE}: framed {len(raw)} records but the header declares "
                f"{declared}. The league returned would be short, which is the failure "
                "byte accounting exists to make visible."
            )
        cursor.skip(frame + len(_RECORD_FRAME) - cursor.position)

        candidate = _peek_u32(data, cursor.position)
        if candidate is None or not previous_id < candidate <= declared:
            # The frame bytes occur inside record bodies too. A candidate that is not the
            # next ascending team id is one of those, so keep searching from after it.
            continue

        raw.append(_read_record(cursor, data, declared))
        previous_id = raw[-1].team_id

    readings = _resolve(tuple(team.team_id for team in raw), tuple(team.run for team in raw))
    parents = _resolve_organisation(raw)
    teams = tuple(
        _assemble(team, reading, parents.get(team.team_id, 0))
        for team, reading in zip(raw, readings, strict=True)
    )
    _check_single_human(teams)

    return TeamsFile(teams=teams, residual_bytes=cursor.remaining(), sim_date=header.sim_date)


# ── reading one record ───────────────────────────────────────────────────────


def _read_record(cursor: Cursor, data: bytes, declared: int) -> _RawTeam:
    """Consume one record's head through the cursor, at widths decided by lookahead."""
    shape = _scan_shape(data, cursor.position, declared)

    team_id = cursor.u32()
    strings = tuple(cursor.string() for _ in range(shape.string_count))
    run = tuple(cursor.u32() for _ in range(shape.run_length))
    colors = tuple(cursor.color() for _ in range(_COLOR_COUNT))
    level = cursor.u32()
    links = tuple(cursor.u32() for _ in range(shape.link_count))
    for _ in range(shape.flag_count):
        cursor.u8()
    franchise_code = cursor.string()
    if franchise_code and not franchise_code.isalnum():
        raise TeamRecordLayout(
            f"{TEAMS_FILE}: team {team_id} carries {franchise_code!r} where a franchise "
            "code belongs. Every value the export holds is three alphanumeric characters "
            "or empty, so this is bytes from somewhere else being read as a string."
        )

    city, abbr, nickname, logo_filename, full_name = _assign_signature(team_id, strings)
    return _RawTeam(
        team_id=team_id,
        city=city,
        abbr=abbr,
        nickname=nickname,
        logo_filename=logo_filename,
        full_name=full_name,
        colors=colors,
        run=run,
        level=level,
        links=links,
        historical_id=franchise_code or None,
    )


def _assign_signature(
    team_id: int, strings: tuple[str, ...]
) -> tuple[str | None, str, str, str | None, str]:
    """Put the strings a record actually carries into the five slots it may have.

    The signature drops any slot whose value is empty, so the count alone is not enough.
    The logo filename is the one slot with a recognisable shape — lowercase, no spaces, a
    short alphabetic extension — and asking whether the third string looks like one
    separates *no city* from *no logo*, which are the two droppable slots measured.

    **Both droppable slots return `None`, never `""`.** A dropped slot is absent from the
    byte stream, and the writer's own rule means an empty string and an absent one are
    the same thing on disk — so the only honest reading is "not present". Landing `""`
    would say the club's logo filename *is* the empty string, which is a different claim
    and a false one. It matters here rather than being a nicety: 289 of the managed
    league's 337 records drop the logo, against **zero** in either probe, so this is a
    code path the export can never validate and a wrong value would reach a report
    unchallenged.
    """
    if len(strings) == 5:
        city, abbr, nickname, logo, full_name = strings
        return city, abbr, nickname, logo, full_name
    if len(strings) == 4 and _is_asset_name(strings[2]):
        abbr, nickname, logo, full_name = strings
        return None, abbr, nickname, logo, full_name
    if len(strings) == 4:
        city, abbr, nickname, full_name = strings
        return city, abbr, nickname, None, full_name
    if len(strings) == 3:
        abbr, nickname, full_name = strings
        return None, abbr, nickname, None, full_name
    raise TeamRecordLayout(  # pragma: no cover - _scan_shape only admits 3, 4 or 5
        f"{TEAMS_FILE}: team {team_id} carries {len(strings)} signature strings"
    )


def _is_asset_name(value: str) -> bool:
    """Does this string look like a shipped asset filename rather than a club name?

    Deliberately narrow: a dot, no spaces, no capitals, and a short alphabetic extension.
    `arizona_diamondbacks.png` and `_all-stars.png` pass; `Clippers`, `AS1` and
    `St. Louis Cardinals` do not, and those are the strings that would otherwise be
    mistaken for a logo.
    """
    _, dot, extension = value.rpartition(".")
    return bool(dot) and " " not in value and value == value.lower() and extension.isalpha()


# ── deciding the widths, by lookahead only ───────────────────────────────────


def _scan_shape(data: bytes, start: int, declared: int) -> _Shape:
    """Work out every variable width in the record beginning at `start`.

    Nothing here consumes; every read is at an offset computed from `start`, which is the
    cursor's own position. The walk never moves backwards and never uses a constant offset
    — what it does is decide, before reading, how wide each region is.
    """
    body = start + 4
    shapes = [
        found
        for count in _SIGNATURE_SHAPES
        if (found := _scan_signature(data, body, count)) is not None
    ]
    if len(shapes) != 1:
        raise TeamRecordLayout(
            f"{TEAMS_FILE}: the record at {start} admits {len(shapes)} string-count "
            "readings. Exactly one should place the three ARGB colours, so either the "
            "signature or the colour block is not where this walk expects it."
        )
    string_count, run_length, after_colors = shapes[0]

    position = after_colors + 4  # level
    link_count = 0
    while True:
        value = _peek_u32(data, position)
        if value is None or not 0 < value <= declared:
            break
        link_count += 1
        position += 4
        if link_count > _MAX_LINKS:
            raise TeamRecordLayout(
                f"{TEAMS_FILE}: the organisation link array of the record at {start} "
                f"passed {_MAX_LINKS} entries without ending. No club has that many "
                "affiliates; the walk has lost alignment earlier in the record."
            )

    flag_count = 0
    while flag_count < _MAX_FLAGS and data[position : position + 1] == _FLAG_BYTE:
        flag_count += 1
        position += 1

    if _scan_string(data, position, _MAX_SHORT_STRING) is None:
        raise TeamRecordLayout(
            f"{TEAMS_FILE}: the record at {start} does not carry a franchise code where "
            f"one is expected — after {link_count} organisation links and {flag_count} "
            "flag bytes, the next field is not a short printable string. Every record in "
            "every save measured carries one, empty on all but the 30 real franchises."
        )

    return _Shape(
        string_count=string_count,
        run_length=run_length,
        link_count=link_count,
        flag_count=flag_count,
    )


def _scan_signature(data: bytes, position: int, count: int) -> tuple[int, int, int] | None:
    """`(count, run_length, end)` if `count` strings are followed by a run and 3 colours.

    The three colours are the validator, and they are a strong one: alpha `0xff` on three
    consecutive `u32`s, immediately after at most six values that all have a zero high
    byte. Trying each plausible string count against it is what lets the walk tolerate a
    dropped city or a dropped logo without being told which.
    """
    cursor = position
    for _ in range(count):
        read = _scan_string(data, cursor, _MAX_STRING)
        if read is None or read[0] == 0:
            return None
        cursor = read[1]

    run_length = 0
    while True:
        value = _peek_u32(data, cursor)
        if value is None:
            return None
        if value >> 24 == _ALPHA:
            break
        run_length += 1
        cursor += 4
        if run_length > _MAX_INTEGER_RUN:
            return None

    colors = 0
    while True:
        value = _peek_u32(data, cursor)
        if value is None or value >> 24 != _ALPHA:
            break
        colors += 1
        cursor += 4
    if colors != _COLOR_COUNT:
        return None
    return count, run_length, cursor


def _scan_string(data: bytes, position: int, limit: int) -> tuple[int, int] | None:
    """`(length, end)` for a length-prefixed printable ASCII string, or `None`.

    Printability is the filter that keeps this from firing on integer data: the low bytes
    of a team id run are nulls, and a null is not a character a club name contains.
    """
    length = _peek_u32(data, position)
    if length is None or length > limit or position + 4 + length > len(data):
        return None
    payload = data[position + 4 : position + 4 + length]
    if any(byte < 0x20 or byte > 0x7E for byte in payload):
        return None
    return length, position + 4 + length


def _peek_u32(data: bytes, position: int) -> int | None:
    """The `u32` at `position` without consuming it, or `None` past the end.

    A lookahead at the cursor's *own* position, never at a constant. The cursor stays
    forward-only and every width the cursor is then asked to advance by was computed from
    these bytes.
    """
    if position + 4 > len(data):
        return None
    return int.from_bytes(data[position : position + 4], "little")


# ── the drop-zero inverse ────────────────────────────────────────────────────


def _readings(run: tuple[int, ...]) -> tuple[_Reading, ...]:
    """Every assignment of `run` to the six-field integer run that the domain allows.

    `park_id` and `league_id` are never zero, so they are always written and always sit
    together; `city_id` may precede them; `sub_league_id`, `nation_id` and the human flag
    may follow in that order. A written `sub_league_id` or human flag is exactly 1,
    because both are 0/1 fields and a zero would have been dropped.
    """
    found: list[_Reading] = []
    for carries_city in (False, True):
        base = 1 if carries_city else 0
        if len(run) < base + 2:
            continue
        park_id, league_id = run[base], run[base + 1]
        rest = run[base + 2 :]
        for present in itertools.combinations((_SUB_LEAGUE, _NATION, _HUMAN), len(rest)):
            assigned = dict(zip(present, rest, strict=True))
            if assigned.get(_SUB_LEAGUE, 1) != 1 or assigned.get(_HUMAN, 1) != 1:
                continue
            found.append(
                _Reading(
                    city_id=run[0] if carries_city else 0,
                    park_id=park_id,
                    league_id=league_id,
                    sub_league_id=assigned.get(_SUB_LEAGUE, 0),
                    nation_id=assigned.get(_NATION, 0),
                    human_team=bool(assigned.get(_HUMAN, 0)),
                )
            )
    return tuple(found)


def _resolve(team_ids: tuple[int, ...], runs: tuple[tuple[int, ...], ...]) -> list[_Reading]:
    """Pick one reading per record, using the file's unambiguous records as the evidence.

    Two records per save need this — the National League All-Star sides, whose run is
    `[20, 203, 1]` and whose trailing `1` is `sub_league_id`, `nation_id` or the human
    flag on the local constraints alone. The file settles it: nation 1 appears nowhere
    else, league 20 appears nowhere else, and some other club already carries the human
    flag. Nothing here is a preference; every filter is a fact the same file states
    somewhere unambiguous.
    """
    candidates = [_readings(run) for run in runs]
    settled = [choices[0] for choices in candidates if len(choices) == 1]
    leagues = {reading.league_id for reading in settled}
    nations = {reading.nation_id for reading in settled if reading.nation_id}
    human_found = any(reading.human_team for reading in settled)

    resolved: list[_Reading] = []
    for team_id, run, choices in zip(team_ids, runs, candidates, strict=True):
        narrowed = choices
        if len(narrowed) > 1:
            narrowed = tuple(
                reading
                for reading in narrowed
                if reading.league_id in leagues
                and (not reading.nation_id or reading.nation_id in nations)
                and (not reading.human_team or not human_found)
            )
        if len(narrowed) != 1:
            raise AmbiguousTeamRecord(
                f"{TEAMS_FILE}: team {team_id}'s integer run {list(run)} admits "
                f"{len(narrowed)} readings after the file's own unambiguous records were "
                "applied. Landing one of them would put a plausible wrong league, park or "
                "nation into bronze with nothing raised."
            )
        resolved.append(narrowed[0])
    return resolved


def _assemble(team: _RawTeam, reading: _Reading, parent_team_id: int) -> TeamRecord:
    return TeamRecord(
        team_id=team.team_id,
        city=team.city,
        abbr=team.abbr,
        nickname=team.nickname,
        logo_filename=team.logo_filename,
        full_name=team.full_name,
        colors=team.colors,
        city_id=reading.city_id,
        park_id=reading.park_id,
        league_id=reading.league_id,
        sub_league_id=reading.sub_league_id,
        nation_id=reading.nation_id,
        human_team=reading.human_team,
        level=team.level,
        parent_team_id=parent_team_id,
        historical_id=team.historical_id,
    )


# ── the organisation tree, read from both ends ───────────────────────────────


def _resolve_organisation(raw: list[_RawTeam]) -> dict[int, int]:
    """Which club each club is an affiliate of, taken only where both records agree.

    **The link array is the same field on both sides of the relation**: a parent lists its
    affiliates and an affiliate lists its parent, in the same slot. So the relation is only
    believed when it is *mutual* — `b` appears in `a`'s links **and** `a` appears in `b`'s.
    Direction then comes from `level`: the deeper club is the affiliate.

    That mutuality is what disposes of this walk's one soft edge without a heuristic. The
    link array is terminated by "the next `u32` stops looking like a team id", and three
    byte patterns that follow it read as small integers and get swallowed as a spurious
    link. `measured`: across all three saves the only values ever swallowed are **1** and
    **257** — one flag byte before an empty franchise code, and two. Neither points back,
    so neither survives here. On the standard-mode probe the surviving relation reproduces
    the export's `parent_team_id` for **all 259 rows**, and it does so with no oracle,
    which is what makes it usable on the managed league.

    Raises:
        TeamRecordLayout: two clubs claim each other at the same level, so the relation has
            no direction; or one club is claimed as an affiliate by two parents.
    """
    links = {team.team_id: team.links for team in raw}
    level = {team.team_id: team.level for team in raw}

    parents: dict[int, int] = {}
    for team_id, linked in links.items():
        for other in linked:
            if other == team_id or team_id not in links.get(other, ()):
                continue
            if level[other] == level[team_id]:
                raise TeamRecordLayout(
                    f"{TEAMS_FILE}: teams {team_id} and {other} each list the other as an "
                    f"organisation link and both sit at level {level[team_id]}, so there "
                    "is no way to say which is the affiliate. Landing one direction would "
                    "invert half an organisation."
                )
            child, parent = (team_id, other) if level[team_id] > level[other] else (other, team_id)
            if parents.setdefault(child, parent) != parent:
                raise TeamRecordLayout(
                    f"{TEAMS_FILE}: team {child} is claimed as an affiliate by both "
                    f"{parents[child]} and {parent}. A club belongs to one organisation."
                )
    return parents


# ── checks the file can run on itself ────────────────────────────────────────


def _check_single_human(teams: tuple[TeamRecord, ...]) -> None:
    """At most one club per save is the human's — the premise every consumer relies on."""
    flagged = [team.team_id for team in teams if team.human_team]
    if len(flagged) > 1:
        raise AmbiguousTeamRecord(
            f"{TEAMS_FILE}: {len(flagged)} clubs carry the human flag {flagged}. One save "
            "has one human manager, so the last slot of the integer run is not the flag "
            "this walk believes it is."
        )


def _read_header_tail(cursor: Cursor) -> _HeaderTail:
    """Read the six `u32`s that follow the header's two wide dates.

    `header.py` is explicit that the header continues past the dates and that its true end
    is `unconfirmed`, so this is a width measured for *this file* rather than a general
    claim. Field 5 is the record count — 259 in both probes against the export's
    `SELECT COUNT(*) FROM teams` = 259, and 337 in the managed league.
    """
    values = tuple(cursor.u32() for _ in range(_HEADER_TAIL_FIELDS))
    return _HeaderTail(
        written_hour=values[0],
        written_minute=values[1],
        written_second=values[2],
        declared_field_count=values[3],
        declared_record_count=values[4],
        constant=values[5],
    )
