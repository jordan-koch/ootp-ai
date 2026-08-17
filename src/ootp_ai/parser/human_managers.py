"""`human_managers.dat` — 835 bytes that name the club we manage, and nothing else does.

Three files in a save have an opinion about who the human is, and only this one gives an
**id**. `saved_games.dat` carries a display string ("Chicago" — which is two clubs).
`teams.dat` reaches the answer through the last slot of a variable-length integer run
whose fields are omitted when zero, which is a long way to travel for one flag. This file
holds the club id outright, in a buffer small enough to read end to end.

## What the walk decodes, and what it consumes without decoding

`measured` 2026-08-16 against all three saves, with `ootp_truth_real.human_managers` as
the oracle for the standard-mode probe:

| Region | Status |
|---|---|
| the shared header, through the two wide dates | `verified` — `header.py` |
| six `u32` header tail; field 5 is the record count and reads **1** in all three saves | `measured` |
| a run of zero bytes, then the `1234` sentinel every record file carries at that point | `measured` |
| `u32` manager id, `u32` first-name index, `u32` last-name index, `u8/u8/u16` date of birth | `measured` — the export's `Jim Smith`, born 1977-03-15, reads (7632, 26051) and 15/3/1977 |
| a drop-zero scalar run — age, nation, weight, height, personality — **not decoded** | `unconfirmed` |
| **three consecutive `u32`s, all holding the managed club** | `measured` |
| everything after the club — languages, an obfuscated credential blob, settings | **not decoded** |

## Why one `team_id` and not three

The export's column list has `team_id`, `last_team_id` and `organization_id` as separate
integers, and the three slots this file holds are **byte-identical in every save on
disk** — 4/4/4, 4/4/4, 6/6/6. No oracle available here can say which slot is which, and
guessing an order would land three fields where only one was observed. So the walk takes
the **first** of the three, because it is the one the drop-zero field order puts first
and because `last_team_id` and `organization_id` are the two that can legitimately differ
from the club currently managed — a manager who changed clubs, or an affiliate assignment.
Landing the first slot is therefore the reading that stays correct when they diverge, and
the divergence is exactly the event that would make this parser raise rather than lie: the
landmark below requires all three to agree. `inferred`, and recorded as such.

## Why a landmark rather than a from-the-top walk

The scalar run between the date of birth and the club is drop-zero encoded — the same
mechanism `teams.py` documents — and this file has one record, so there is no second
record to cross-check a field order against. Rather than guess at ~20 unlabelled scalars,
the walk enters at a landmark that is **measured unique**: the only position in any of the
three files where three consecutive `u32`s hold the same non-zero value is offset 231, and
it holds 4, 4 and 6 — the two Boston saves and the Cubs save. That uniqueness holds at
every bound tested, from `value <= 999` up to `value < 2**24`, so it is not an artifact of
a tight filter.

**This is a search, not a seek.** The walk never jumps to 231; it scans forward from where
the decoded head left off and stops at the first match, and refuses if there is not exactly
one. A save whose manager has moved clubs mid-career would break the landmark and **raise**,
which is the recoverable failure — see `ManagerRecordLayout`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.header import read_header_from
from ootp_ai.parser.primitives import Cursor, SaveDate

__all__ = [
    "CLUB_SLOTS",
    "HUMAN_MANAGERS_FILE",
    "HumanManager",
    "ManagerRecordLayout",
    "read_human_manager",
]

#: Sits inside the `.lg` directory beside `teams.dat`. 835-859 bytes across the three
#: saves on disk — the smallest record file this project reads.
HUMAN_MANAGERS_FILE = "human_managers.dat"

#: How many consecutive `u32`s hold the club. All three agree in every save measured, and
#: that agreement is what makes the landmark unique — so it is asserted, not assumed.
CLUB_SLOTS = 3

#: How many `u32`s follow the header's two wide dates, as in every other record file.
_HEADER_TAIL_FIELDS = 6

#: `measured` — `u32` 1234 sits immediately after the zero pad in **every** record file of
#: every save (14 files x 3). It is the cheapest available proof that the walk is still
#: aligned after the pad, so it is checked rather than skipped.
_RECORD_SENTINEL = 1234

#: A generous cap on the zero pad between the header tail and the sentinel. `measured`: 46
#: bytes in all three saves. The cap exists so a corrupt file runs out of patience rather
#: than out of buffer.
_MAX_PAD = 256

#: The largest value the club landmark will accept. Team ids run 1..N for a few hundred N;
#: this is loose on purpose, because the landmark's uniqueness was measured at bounds from
#: 999 to 2**24 and did not depend on the bound.
_MAX_TEAM_ID = 1 << 24


class ManagerRecordLayout(SaveFormatError):  # noqa: N818
    """A valid `human_managers.dat` whose club could not be located unambiguously.

    Distinct from the header refusals: those mean *this is not the file you think it is*,
    this one means *the file is what it claims and its one record is not shaped the way
    every save measured was shaped.* The likely cause is a manager whose current club,
    previous club and organization no longer agree — at which point the landmark is gone
    and a walk that picked "the first plausible id" would be inventing an answer.
    """


@dataclass(frozen=True, slots=True)
class HumanManager:
    """The one human manager a save carries, as far as this walk decodes it.

    `team_id` is the field the rest of the pipeline exists to get: every ingest run is
    stamped with the club it was taken from, and `ingest.py` resolves it from here rather
    than from a constant. Code that hardcoded *"we are team 6"* would pass on the probe the
    parser is developed against and break invisibly on the managed league.

    `first_name_index` and `last_name_index` are indices into `names.dat`, not names —
    resolving them is Phase 7's job and this type deliberately does not pretend otherwise.

    `undecoded_bytes` is the honest half of the record: the walk consumes the whole file,
    but a large part of it is consumed rather than read. A reader that wants to know how
    much of the 835 bytes actually carries meaning here can ask.
    """

    manager_id: int
    team_id: int
    first_name_index: int
    last_name_index: int
    date_of_birth: SaveDate
    undecoded_bytes: int


def read_human_manager(data: bytes) -> HumanManager:
    """Walk a `human_managers.dat` buffer end to end and return the club it names.

    The walk finishes with the cursor exactly at the end of the buffer — zero residual —
    which is what a file this small should be held to. That is a statement about *reaching*
    the end, not about understanding every byte on the way: `HumanManager.undecoded_bytes`
    reports how much was consumed without being read, and the module docstring says which
    regions those are.

    Raises:
        MalformedHeader: the buffer is truncated, or is not an OOTP record file.
        UnsupportedSaveVersion: the declared version is not the one we are proven on.
        SaveFilenameMismatch: the header names a different file.
        UnexpectedEndOfData: a read ran past the end of the buffer.
        ManagerRecordLayout: the record count is not 1, the sentinel is missing, or the
            club landmark is absent or ambiguous.
    """
    cursor = Cursor(data, label=HUMAN_MANAGERS_FILE)
    read_header_from(cursor, HUMAN_MANAGERS_FILE)

    tail = tuple(cursor.u32() for _ in range(_HEADER_TAIL_FIELDS))
    declared_records = tail[4]
    if declared_records != 1:
        raise ManagerRecordLayout(
            f"{HUMAN_MANAGERS_FILE} declares {declared_records} records; this walk is "
            "measured against the single-human case only. A save with two human managers "
            "would also settle which of the three club slots is which — refusing rather "
            "than reading the first record and calling it the answer."
        )

    cursor.skip(_pad_width(data, cursor.position))
    sentinel = cursor.u32()
    if sentinel != _RECORD_SENTINEL:
        raise ManagerRecordLayout(
            f"{HUMAN_MANAGERS_FILE}: expected the {_RECORD_SENTINEL} sentinel after the "
            f"zero pad and found {sentinel}. The walk has lost alignment before it read "
            "anything, so nothing after this point would mean what it says."
        )

    manager_id = cursor.u32()
    first_name_index = cursor.u32()
    last_name_index = cursor.u32()
    date_of_birth = cursor.date()

    scalars = _distance_to_club(data, cursor.position)
    cursor.skip(scalars)
    club = tuple(cursor.u32() for _ in range(CLUB_SLOTS))

    trailing = cursor.remaining()
    cursor.skip(trailing)
    if not cursor.exhausted():  # pragma: no cover - skip(remaining) leaves nothing
        raise ManagerRecordLayout(f"{HUMAN_MANAGERS_FILE}: the walk did not reach the end")

    return HumanManager(
        manager_id=manager_id,
        team_id=club[0],
        first_name_index=first_name_index,
        last_name_index=last_name_index,
        date_of_birth=date_of_birth,
        undecoded_bytes=scalars + trailing,
    )


def _pad_width(data: bytes, position: int) -> int:
    """How many zero bytes sit between the header tail and the sentinel.

    A width read off the data, never a constant: the walk counts zeros until it finds a
    byte that is not one. `measured` 46 in all three saves, but nothing here depends on
    that number being 46 — only on the sentinel that follows agreeing.
    """
    width = 0
    while width < _MAX_PAD and position + width < len(data) and data[position + width] == 0:
        width += 1
    if width >= _MAX_PAD:
        raise ManagerRecordLayout(
            f"{HUMAN_MANAGERS_FILE}: more than {_MAX_PAD} zero bytes follow the header "
            "tail, so the record region was never reached"
        )
    return width


def _distance_to_club(data: bytes, position: int) -> int:
    """Bytes from `position` to the landmark, or a refusal naming what was found instead.

    The landmark is `CLUB_SLOTS` consecutive `u32`s holding one identical non-zero value.
    Scanned at every byte alignment, because nothing guarantees the drop-zero scalar run
    ahead of it is a whole number of words. `measured`: exactly one match in each of the
    three saves, at every bound from 999 to 2**24.

    Refusing on a second match is the point. Two matches means the uniqueness this entry
    rests on has stopped holding, and picking the first would be a coin flip dressed as a
    parse.
    """
    matches = [
        offset
        for offset in range(position, len(data) - CLUB_SLOTS * 4 + 1)
        if _is_club_landmark(data, offset)
    ]
    if len(matches) != 1:
        raise ManagerRecordLayout(
            f"{HUMAN_MANAGERS_FILE}: found {len(matches)} positions where "
            f"{CLUB_SLOTS} consecutive u32s hold the same non-zero id, expected exactly "
            "one. Every save measured has the managed club written three times in a row; "
            "a manager who has changed clubs would not, and this walk refuses rather "
            "than guessing which of several candidates is the club."
        )
    return matches[0] - position


def _is_club_landmark(data: bytes, offset: int) -> bool:
    """`CLUB_SLOTS` consecutive `u32`s, all equal, all a plausible team id."""
    first = int.from_bytes(data[offset : offset + 4], "little")
    if not 0 < first <= _MAX_TEAM_ID:
        return False
    return all(
        int.from_bytes(data[offset + 4 * slot : offset + 4 * slot + 4], "little") == first
        for slot in range(1, CLUB_SLOTS)
    )
