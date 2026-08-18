"""The shared save-file header, and the version guard that refuses everything else.

Every OOTP record file opens with the same prefix. This module reads it **through the
ordinary cursor**, one field at a time, rather than indexing offsets 1, 5 and 25 with
literals. That is not stylistic tidiness: the AST guard over `src/ootp_ai/` runs with
**zero exemptions**, and a header reader full of constant offsets would need the first
one. An exemption list is how a guard stops being a guard, and this is the guard the
whole parser rests on.

The trap the header sets, measured and recorded in the format catalog, is symmetric —
both naive readings fail on the first file opened:

* a reader comparing `data[0:4]` against `b"OOTP"` sees `\\x00OOT` and rejects every
  valid save, because the magic begins at offset **1**;
* a reader taking the version as a u32 at offset 4 gets 6480 rather than 25.

Both are loud, which is the tolerable outcome. Everything in here refuses rather than
copes, for the reason the rulebook gives: a loud failure is recoverable and a silent
misparse is not.

**Where the body begins is deliberately not answered.** `measured` 2026-08-16: the
prefix through the two dates runs to byte 99, but bytes 99-110 vary per save, byte 111
is constant per *file type*, and byte 115 varies per save again — so the header
continues past everything read here and its end is `unconfirmed`. Nothing in this
module reports a length, an end, or a body offset, and nothing should be added:
a wrong body offset mis-reads every record with nothing raised. A walker that needs to
continue reading passes its own cursor to `read_header_from` and keeps walking it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ootp_ai.parser.errors import (
    MalformedHeader,
    SaveFilenameMismatch,
    UnexpectedEndOfData,
    UnsupportedSaveVersion,
)
from ootp_ai.parser.primitives import Cursor, SaveDate

__all__ = [
    "FILENAME_FIELD_LEN",
    "HEADER_CONSTANTS",
    "LEADING_NULL",
    "MAGIC",
    "STABLE_PREFIX_LEN",
    "SUPPORTED_VERSION",
    "SaveHeader",
    "looks_like_save_file",
    "read_header",
    "read_header_from",
]

LEADING_NULL = 0x00
MAGIC = b"OOTP"

#: OOTP 25 (`0x19`). The one version every field mapping in this repo was measured
#: against. A different value is refused, never guessed at.
SUPPORTED_VERSION = 25

#: The four u32s between the version and the filename. `measured` — identical
#: (11, 104, 84, 1) in all 50 record files across the three saves on disk. Their
#: meaning is unknown and nothing here depends on it; they are checked only because
#: a change in them is evidence the layout moved under us.
HEADER_CONSTANTS = (11, 104, 84, 1)

#: The self-declared filename sits in a fixed-width, null-padded field. `measured`
#: 2026-08-16 — the width is 50 bytes, which the format catalog's table does not yet
#: record. It is a field *width*, not a record offset: the cursor still walks to it.
FILENAME_FIELD_LEN = 50

#: How many leading bytes are identical across every save on disk — everything up to
#: the sim date, which is content rather than format. This is the correct span for a
#: cross-save header comparison; **it is not a body offset** and must never be used
#: as one. `measured` — identical across all 16 shared record files in three saves.
STABLE_PREFIX_LEN = 75

#: The leading null **and** the magic, as one value. Written this way because the two
#: naive readings of this header are the traps the format catalog records — checking
#: `data[0:4]` against `b"OOTP"` rejects every valid save — and a single prefix constant
#: makes both impossible to write by accident.
MAGIC_PREFIX = bytes([LEADING_NULL]) + MAGIC

_MAGIC_PREFIX_LEN = len(MAGIC_PREFIX)


@dataclass(frozen=True, slots=True)
class SaveHeader:
    """What a record file's header says about itself.

    There is deliberately **no** `length`, `end`, `size` or `body_offset` here. An
    earlier draft reported 79, which was wrong — the header continues past it and its
    true end is unmeasured. Offering a plausible number would be worse than offering
    none, because a walker that trusted it would mis-read every record silently.

    `sim_date` is the league's in-game date and `written_date` is the wall clock when
    the file was written. They are separate on purpose: a snapshot key built from the
    second would drift with the clock rather than with the league.
    """

    version: int
    filename: str
    constants: tuple[int, ...]
    sim_date: SaveDate
    written_date: SaveDate


def looks_like_save_file(data: bytes) -> bool:
    """Cheap classification: does this buffer open with the OOTP record-file magic?

    Not every `.dat` in a save directory is an OOTP record file. `measured`
    2026-08-16: `flag_save_completed.dat` is a plain-text log and `text_data.dat` is
    a ZIP archive (`PK\\x03\\x04`), so a caller that globs `*.dat` and feeds every hit
    to `read_header` gets a `MalformedHeader` on two files that were never records.
    This lets such a caller filter first instead of loosening the reader.
    """
    return data.startswith(MAGIC_PREFIX)


def read_header(data: bytes, expected_filename: str) -> SaveHeader:
    """Read and validate a record-file header from the start of `data`, or refuse.

    `expected_filename` is the name of the file actually opened. The header names
    itself, so comparing the two is a free check that the path wiring is right.

    A walker that intends to keep reading should build its own `Cursor` and call
    `read_header_from` instead — that way the walk continues from wherever the header
    stopped, with no offset arithmetic anywhere.

    Raises:
        MalformedHeader: the buffer is truncated, or is not an OOTP record file.
        UnsupportedSaveVersion: the declared version is not the one we are proven on.
        SaveFilenameMismatch: the header names a different file.
    """
    return read_header_from(Cursor(data, label=expected_filename), expected_filename)


def read_header_from(cursor: Cursor, expected_filename: str) -> SaveHeader:
    """Read the header off the front of `cursor`, leaving it positioned after it.

    The cursor is the only handoff between the header and the body. It is also why
    nothing here needs to know how long the header is: the walk simply continues.
    """
    try:
        _read_magic(cursor, expected_filename)

        version = cursor.u32()
        if version != SUPPORTED_VERSION:
            raise UnsupportedSaveVersion(version, supported=SUPPORTED_VERSION)

        constants = tuple(cursor.u32() for _ in HEADER_CONSTANTS)
        if constants != HEADER_CONSTANTS:
            raise MalformedHeader(
                f"{expected_filename}: header constants are {constants}, expected "
                f"{HEADER_CONSTANTS} — the header layout may have changed, and every "
                "field mapping downstream was measured against the old one"
            )

        declared = _read_filename(cursor, expected_filename)
        if declared != expected_filename:
            raise SaveFilenameMismatch(declared, expected_filename)

        sim_date = _read_wide_date(cursor)
        written_date = _read_wide_date(cursor)
    except UnexpectedEndOfData as exc:
        raise MalformedHeader(f"{expected_filename}: the header is truncated — {exc}") from exc

    return SaveHeader(
        version=version,
        filename=declared,
        constants=constants,
        sim_date=sim_date,
        written_date=written_date,
    )


def _read_magic(cursor: Cursor, expected_filename: str) -> None:
    """The leading null and the four magic bytes, in that order and no other."""
    leading = cursor.u8()
    if leading != LEADING_NULL:
        raise MalformedHeader(
            f"{expected_filename}: first byte is {leading:#04x}, expected a null — "
            "the magic begins at offset 1, and a file that starts with 'OOTP' is "
            "not the shape a real save has"
        )
    magic = cursor.take(len(MAGIC))
    if magic != MAGIC:
        raise MalformedHeader(
            f"{expected_filename}: magic is {magic!r}, expected {MAGIC!r} — "
            "this is not an OOTP record file"
        )


def _read_filename(cursor: Cursor, expected_filename: str) -> str:
    """The fixed-width, null-padded self-declared filename.

    The padding is asserted to be nulls: if it is not, the field width is wrong and
    every byte after it is being read from the wrong place — which is exactly the
    failure that would otherwise surface as a plausible wrong value much later.
    """
    field = cursor.take(FILENAME_FIELD_LEN)
    stem, _, padding = field.partition(b"\x00")
    if padding.strip(b"\x00"):
        raise MalformedHeader(
            f"{expected_filename}: the {FILENAME_FIELD_LEN}-byte filename field is "
            "not null-padded, so the header layout is not what was measured"
        )
    try:
        return stem.decode("ascii")
    except UnicodeDecodeError as exc:
        raise MalformedHeader(
            f"{expected_filename}: the self-declared filename is not ASCII"
        ) from exc


def _read_wide_date(cursor: Cursor) -> SaveDate:
    """Three u32s — day, month, year.

    **Not** the `u8 day, u8 month, u16 year` primitive the record bodies use; the
    header spends four bytes per component. `measured` 2026-08-16 across three saves
    and the saved-games index, which carries (0, 0, 0) for a sim date it does not
    have — so a zero date here is structural absence, which `SaveDate.as_date()`
    reports as `None` rather than inventing a day.
    """
    day = cursor.u32()
    month = cursor.u32()
    year = cursor.u32()
    return SaveDate(day=day, month=month, year=year)
