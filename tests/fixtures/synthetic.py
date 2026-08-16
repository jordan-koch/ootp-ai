"""Synthetic byte builders for parser tests.

**Functions, not data files.** `.gitignore:31` ignores `*.dat`, but `.gitignore:62`'s
`!tests/fixtures/**` is a *later* negation and git's last-match-wins, so a
`tests/fixtures/sample.dat` would in fact be committable — the only thing catching
it is `tests/test_no_leaks.py`'s banned suffixes, as a red build. Building the bytes
in code sidesteps the question entirely, and ADR 0006 keeps OOTP's data out of the
repo at any size for any reason.

`tests/fixtures/README.md` makes the affirmative argument too: a real save's day-0
state is the **least** informative input available, because every variable-length
region is at its minimum — precisely the condition under which a fixed-offset reader
passes cleanly and then corrupts everything later.

Header layout below is `measured` (2026-08-16), byte-for-byte against `teams.dat`,
`players.dat`, `names.dat`, `world.dat` and `scouting.dat` in an OOTP 25 save. Note
`docs/data-access.md` §4 documents the fields but not the filename field's WIDTH;
that is recorded here and routed to the doc gate.
"""

from __future__ import annotations

import struct

# ── Header layout, measured ──────────────────────────────────────────────────
LEADING_NULL = 0x00
MAGIC = b"OOTP"
CURRENT_VERSION = 25

MAGIC_OFFSET = 1
VERSION_OFFSET = 5
FILENAME_OFFSET = 25
FILENAME_FIELD_LEN = 50
TRAILING_U32_OFFSET = 75
HEADER_LEN = 79

# The four constants between the version and the filename. Identical in every .dat
# file measured; their meaning is unknown and this project does not depend on it.
HEADER_CONSTANTS = (11, 104, 84, 1)
TRAILING_U32 = 7


def make_header(
    *,
    version: int = CURRENT_VERSION,
    filename: str = "players.dat",
    magic: bytes = MAGIC,
    leading: int = LEADING_NULL,
    magic_at_offset_zero: bool = False,
) -> bytes:
    """Build a save-file header.

    `magic_at_offset_zero` builds the *malformed* shape a naive reader assumes —
    `b"OOTP"` at offset 0 with no leading null. `docs/data-access.md:183-186` records
    why that matters: a reader checking `data[0:4]` against `b"OOTP"` sees `\\x00OOT`
    on a real save and rejects every valid file, while one reading the version as a
    u32 at offset 4 gets 6480 rather than 25.
    """
    encoded = filename.encode("ascii")
    if len(encoded) > FILENAME_FIELD_LEN:
        raise ValueError(f"filename exceeds the {FILENAME_FIELD_LEN}-byte field: {filename!r}")
    name_field = encoded.ljust(FILENAME_FIELD_LEN, b"\x00")

    body = (
        magic
        + struct.pack("<I", version)
        + b"".join(struct.pack("<I", value) for value in HEADER_CONSTANTS)
        + name_field
        + struct.pack("<I", TRAILING_U32)
    )
    if magic_at_offset_zero:
        return body
    return bytes([leading]) + body


def make_string(value: str) -> bytes:
    """u32-LE length prefix, raw ASCII, **no terminator** (`docs/data-access.md:195`)."""
    encoded = value.encode("ascii")
    return struct.pack("<I", len(encoded)) + encoded


def make_date(day: int, month: int, year: int) -> bytes:
    """u8 day, u8 month, u16 year (`docs/data-access.md:196`)."""
    return struct.pack("<BBH", day, month, year)


def make_color(argb: int) -> bytes:
    """u32 ARGB (`docs/data-access.md:197`)."""
    return struct.pack("<I", argb)


def make_record(
    *,
    player_id: int = 47035,
    contract_years: int = 1,
    uniform_number: int = 34,
    historical_id: str = "deverra01",
    salary: int = 27_500_000,
) -> bytes:
    """A synthetic record with a **variable-length region in the middle**.

    This is the shape the whole fixed-offset ban exists for. `contract_years` changes
    the record's length, so every field *after* the contract array sits at a
    different absolute offset in a 1-year record than in a 10-year one. A sequential
    reader is unaffected; a reader that seeks to a constant offset returns the wrong
    field with nothing raised.

    Measured on the real thing (`.claude/agents/data-engineer.md:69-74`): the same
    player's ratings block sat 43 bytes from one anchor in one save and 107 in
    another, with byte-identical internal layout.
    """
    if contract_years < 0:
        raise ValueError("contract_years must not be negative")
    return (
        struct.pack("<I", player_id)
        + struct.pack("<I", contract_years)
        + b"".join(struct.pack("<I", salary) for _ in range(contract_years))
        + struct.pack("<I", uniform_number)
        + make_string(historical_id)
    )
