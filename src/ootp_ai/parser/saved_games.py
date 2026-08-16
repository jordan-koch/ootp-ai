"""The saved-games index — a real record file, not the plaintext the catalog claims.

`docs/data-access.md` §1 records, `verified`, that `saved_games.dat` is *"plaintext …
readable without parsing"*. **That is wrong.** `measured` 2026-08-16: the file carries
the standard OOTP header (leading null, `OOTP`, version 25, the four constants, the
self-declared filename, two wide dates) followed by one variable-length record per save,
built from u32-LE length-prefixed strings with no terminator. Strings sit at unaligned
offsets, so a u32 scan misses them and a substring scrape finds them only by luck. It is
read here the same way every other file in this project is read: header first, then a
forward-only walk.

**It embeds an absolute user-profile path four times per save.** Those are walked past
and dropped. `SavedGameEntry` has **no field they could be stored in** — the defence is
that the value is unrepresentable, not that callers remember to strip it, because this
repo is public and a provenance section that published a username would be permanent
(ADR 0006).

**Its own header's sim date is `(0, 0, 0)`.** The index is not a league, so it has no
in-game date of its own — structural absence, which `SaveDate.as_date()` reports as
`None`. The per-save sim dates below are a different field, inside the records.

## Layout, `measured` against the only index on disk

One file, 2,070 bytes, listing three saves — so every width below is measured against
**three records in one file**, which is a thin sample for a shape claim. What raises it
above a guess is that the walk is **strictly byte-accounted**: it consumes the buffer
exactly, with zero residual, and every one of the three records has identical widths in
its unclassified regions. A wrong width anywhere would desynchronise the very next
length prefix and raise rather than return a plausible wrong value.

After the shared header comes a 74-byte file-level tail — `header.py` documents that the
header continues past the two dates and that its true end is `unconfirmed`, so this is
recorded as *this file's* tail and nothing more. Then, per save:

| # | Field | Status |
|---|---|---|
| 1 | league name (`u32` + ASCII) | used |
| 2 | absolute path | **dropped** |
| 3 | sim date (`u8` day, `u8` month, `u16` year) | used |
| 4 | 3 bytes, zero in all three saves | unclassified |
| 5 | parent league display name | dropped |
| 6 | parent league logo filename | dropped |
| 7 | absolute path | **dropped** |
| 8 | 2 bytes, zero in all three saves | unclassified |
| 9 | save directory name (league name + `.lg`) | dropped |
| 10 | `u8`, 0/0/1 across the three saves | unclassified |
| 11 | wall-clock save date | dropped |
| 12 | 3 bytes — hour, minute, second | dropped |
| 13 | absolute path | **dropped** |
| 14 | date + 3 bytes; all zero in one of the three | unclassified |
| 15 | date + 3 bytes; all zero in the same save | unclassified |
| 16 | `u32`, zero in all three | unclassified |
| 17 | `u8`, zero in all three | unclassified |
| 18 | `u32`, 2/2/1 across the three saves | unclassified — **see below** |
| 19 | human team display name | used |
| 20 | human team logo filename | dropped |
| 21 | absolute path | **dropped** |

## Why `human_team_id` is always `None`

The index identifies the human team **by display name and logo filename only. There is
no team id in it.** Every numeric slot in all three records was enumerated at `u8`, `u16`
and `u32` widths and compared against ground truth — the export gives Boston `team_id` 4
and the Cubs `team_id` 6 — and **no slot holds that triple.**

Field 18 is the trap, and it is worth naming because it would have passed the test. It
reads 2, 2, 1 across the three saves, which separates the two Boston saves from the Cubs
save and therefore satisfies *"a constant cannot produce all three"*. It is not a team
id: 2 and 1 are not 4 and 6, and the same split falls exactly along **Challenge, Challenge,
Standard** — corroborated by field 10, which reads 0, 0, 1 on the same boundary. Reading
it as a team would have produced a confidently wrong number with a green test behind it,
which is the single failure this project cannot afford.

So the honest answer at this phase is `None`. The human team is recoverable — the export
schema carries `human_team` and `human_id` on `teams` — but from `teams.dat`, which is
Phase 5's walker, not from here. `None` here is **structural absence, not a placeholder
zero**: the field the index would need does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass

from ootp_ai.parser.errors import UnexpectedEndOfData
from ootp_ai.parser.header import read_header_from
from ootp_ai.parser.primitives import Cursor, SaveDate

__all__ = [
    "SAVED_GAMES_FILE",
    "SavedGameEntry",
    "read_saved_games",
]

#: Sits at the **root** of the saved-games directory, beside the `.lg` directories
#: rather than inside one.
SAVED_GAMES_FILE = "saved_games.dat"

#: Bytes between the end of the shared header and the first record. `header.py` is
#: explicit that the header continues past the two dates and that its end is
#: `unconfirmed`, so this is a width measured for *this file*, not a general claim.
#: A wrong value here desynchronises the first length prefix and raises immediately.
_HEADER_TAIL_LEN = 74

#: Unclassified fixed-width regions, in the order the walk crosses them. Widths, not
#: offsets — the cursor never jumps, it only advances by what it has just accounted for.
_PAD_AFTER_SIM_DATE = 3
_PAD_AFTER_LEAGUE_PATH = 2
_TIME_OF_DAY_LEN = 3
_PAD_AFTER_DATE = 3
_UNCLASSIFIED_TAIL_LEN = 9


@dataclass(frozen=True, slots=True)
class SavedGameEntry:
    """One save as the index describes it: which league, when, managed by whom.

    Four fields, and the one absence is as deliberate as the presences.

    **No path field.** The record embeds an absolute user-profile path four times over,
    and this type is what guarantees none of them can reach a warehouse row, a rendered
    report or a tracked catalog. A later phase cannot leak what it cannot construct.

    `human_team_id` is `None` on every entry read from a real index — the file carries no
    team id at all. See the module docstring for what was checked and why the obvious
    candidate is not one.

    `human_team_name` is the club's **display string**, and it is carried for exactly one
    purpose: to check Phase 5's answer. `teams.dat` resolves the human club from a flag on
    the team record, and this is the only independent statement of which club that should
    be — a second file, read by a different walker, agreeing or not. That makes it a
    **cross-check, never a join key.** Joining on it would be a join by display name
    across two universes, and the id exists precisely so nothing has to.

    It is `None` rather than `""` when the index carries no club: an empty length-prefixed
    string is structural absence, and a zero-length name is not a name.
    """

    league: str
    sim_date: SaveDate
    human_team_id: int | None
    human_team_name: str | None


def read_saved_games(data: bytes) -> tuple[SavedGameEntry, ...]:
    """Walk the whole index and return one entry per listed save.

    The walk is strictly byte-accounted: it runs until the buffer is exactly consumed,
    so a width that is wrong anywhere raises instead of returning a shorter list that
    looks like a smaller machine.

    Raises:
        SaveFormatError: the header is not a version-25 OOTP record header, or a record
            ran past the end of the buffer — which means the layout is not the one this
            module was measured against, and nothing it returned could be trusted.
    """
    cursor = Cursor(data, label=SAVED_GAMES_FILE)
    read_header_from(cursor, SAVED_GAMES_FILE)
    cursor.skip(_HEADER_TAIL_LEN)

    entries: list[SavedGameEntry] = []
    while not cursor.exhausted():
        try:
            entries.append(_read_entry(cursor))
        except UnexpectedEndOfData as exc:
            raise UnexpectedEndOfData(
                f"{SAVED_GAMES_FILE}: record {len(entries)} ran past the end of the "
                f"index, so the record layout is not the one measured — {exc}"
            ) from exc
    return tuple(entries)


def _read_entry(cursor: Cursor) -> SavedGameEntry:
    """One save's record, field by field, in the order the bytes appear.

    Every `_drop_*` call consumes a real field and returns nothing. That is the point:
    a field with no caller cannot be rendered, logged or landed by accident, and the
    absolute paths in this record are three of them.
    """
    league = cursor.string()
    _drop_path(cursor)

    sim_date = cursor.date()
    cursor.skip(_PAD_AFTER_SIM_DATE)

    _drop_string(cursor)  # parent league display name
    _drop_string(cursor)  # parent league logo filename
    _drop_path(cursor)
    cursor.skip(_PAD_AFTER_LEAGUE_PATH)

    _drop_string(cursor)  # save directory name — the league name plus the save suffix
    cursor.u8()  # mode-shaped flag, unclassified
    cursor.date()  # wall-clock save date, not the league's
    cursor.skip(_TIME_OF_DAY_LEN)  # hour, minute, second
    _drop_path(cursor)

    # Two dates that are populated in two of the three saves and zero in the third.
    # Unclassified, and left that way: a plausible meaning is not a measurement.
    cursor.date()
    cursor.skip(_PAD_AFTER_DATE)
    cursor.date()
    cursor.skip(_PAD_AFTER_DATE)

    # Includes the 2/2/1 field the module docstring names. Deliberately not read into
    # `human_team_id`: it splits Challenge from Standard, not Boston from Chicago.
    cursor.skip(_UNCLASSIFIED_TAIL_LEN)

    # Strict ASCII, like `league` and unlike every `_drop_string` above: this one is
    # returned, and a mangled club name is a wrong club name rather than a cosmetic
    # blemish. A non-ASCII club elsewhere in the world raises here, loudly, which is the
    # outcome this project prefers to a silently substituted character.
    human_team_name = cursor.string() or None
    _drop_string(cursor)  # human team logo filename
    _drop_path(cursor)

    return SavedGameEntry(
        league=league,
        sim_date=sim_date,
        human_team_id=None,
        human_team_name=human_team_name,
    )


def _drop_path(cursor: Cursor) -> None:
    """Consume an embedded absolute filesystem path without producing a value.

    Named separately from `_drop_string` so the walk documents the record's true shape
    while making it obvious at every call site that nothing escapes. The bytes are
    consumed and discarded; they are never returned, formatted or raised.
    """
    _drop_string(cursor)


def _drop_string(cursor: Cursor) -> None:
    """Consume a length-prefixed string this parser has no use for.

    Decoded `latin-1` rather than the cursor's strict ASCII default, deliberately and
    only here: latin-1 maps every byte, so a discarded field can never fail the walk.
    An accented username in an embedded path, or an accented league logo filename, would
    otherwise raise on someone else's machine over a value nothing reads. The *returned*
    league name keeps strict ASCII, because there a mangled name is a wrong name.
    """
    cursor.string(encoding="latin-1")
