"""The one sanctioned place to index a save buffer.

**Read this before adding a function here, and before indexing `bytes` anywhere else.**

## Why this module exists

The fixed-offset ban is enforced twice, and until now the two mechanisms covered disjoint
code. `Cursor` (`parser/primitives.py`) is *structurally* unable to seek: no `seek`, no
position setter, `position` is a read-only property. That half is airtight, and it covers
every **consuming** read.

It does not cover the parser's other read path. Every walker also *looks ahead* — to frame
a record, to validate a candidate, to find a landmark — and that path indexes the buffer
directly. `measured` 2026-08-18: twenty-one such sites across five modules, including
three separately-written, near-identical `_peek_u32` implementations whose docstrings each
asserted the rule in prose ("never at a constant") while one module's caller passed a
constant. Nothing checked them, because `tests/test_no_fixed_offsets.py` inspected only
`ast.Call` and never an `ast.Subscript`.

Prose asserted three times and broken once is what a missing mechanism looks like. So the
rule moves from prose into structure: **buffer indexing lives here, and the guard flags it
anywhere else.** The guard keys on the module rather than on syntax, which is what makes
it statable in one sentence and impossible to evade by choosing a different spelling.

## The rules this module lives under

1. **It is one of exactly two allowlisted modules** (the other is `primitives.py`, whose
   `Cursor.take` indexes its own buffer). An allowlist of two is small enough to audit;
   `tests/test_fixed_offset_guard_scope.py` asserts the size and that each entry is real.
2. **A stricter interior rule applies here.** No bare nonzero integer literal may appear in
   a subscript index in this file. Being sanctioned is not a licence — it is the reason the
   discipline has to be *tighter* here, or the seam becomes a laundry. Every width below is
   named so that arithmetic reads as "walk past these fields" rather than "jump to 12".
3. **Every function takes a position the caller computed and returns `None` past the end.**
   None of them advances anything, and none knows where a record starts. They cannot seek,
   because they have nothing to seek *in* — they are given a position or they do nothing.

## What is deliberately NOT here

No function validates a value. `peek_date_parts` returns raw `(day, month, year)` and
leaves the judgement to the caller, because the callers genuinely disagree: `world.py`
treats `year == 0` as legitimate structural absence in a calendar record, and
`players.py` rejects it when framing a player. A shared validator would have had to pick
one and silently break the other.
"""

from __future__ import annotations

__all__ = [
    "DATE_WIDTH",
    "DAY_WIDTH",
    "LENGTH_PREFIX_WIDTH",
    "MONTH_WIDTH",
    "U8_WIDTH",
    "U16_WIDTH",
    "U32_WIDTH",
    "YEAR_WIDTH",
    "peek_bytes",
    "peek_date_parts",
    "peek_length_prefixed_ascii",
    "peek_u8",
    "peek_u32",
    "zero_run_width",
]

#: Declared spans. These exist so that every offset in this repo can be written as a sum of
#: field widths — the form `world.py` already uses and the only one that is both
#: constant-derived and self-documenting. A width is a fact about the format; an offset is
#: a guess about where you are.
U8_WIDTH = 1
U16_WIDTH = 2
U32_WIDTH = 4

DAY_WIDTH = U8_WIDTH
MONTH_WIDTH = U8_WIDTH
YEAR_WIDTH = U16_WIDTH
#: `u8 day, u8 month, u16 year` — four bytes, in that order.
DATE_WIDTH = DAY_WIDTH + MONTH_WIDTH + YEAR_WIDTH

#: A string is a `u32` length followed by raw characters and **no terminator**.
LENGTH_PREFIX_WIDTH = U32_WIDTH

#: Printable ASCII, inclusive. The filter that stops a string scan firing on integer data:
#: the high bytes of a small `u32` are nulls, and a null is not a character a club or
#: division name contains.
_FIRST_PRINTABLE = 0x20
_LAST_PRINTABLE = 0x7E


def _in_bounds(data: bytes, position: int, width: int) -> bool:
    """Is `width` bytes at `position` inside the buffer?

    A negative position is out of bounds, not a from-the-end index. Python would happily
    return the wrong bytes for one; `measured`, the three predecessor implementations
    disagreed about this and only one rejected it. The strictest reading wins: a negative
    position means the caller's arithmetic went wrong, and returning data would hide it.
    """
    return position >= 0 and position + width <= len(data)


def peek_u8(data: bytes, position: int) -> int | None:
    """The byte at `position` without consuming it, or `None` past the end."""
    if not _in_bounds(data, position, U8_WIDTH):
        return None
    return data[position]


def peek_u32(data: bytes, position: int) -> int | None:
    """The little-endian `u32` at `position` without consuming it, or `None`."""
    if not _in_bounds(data, position, U32_WIDTH):
        return None
    return int.from_bytes(data[position : position + U32_WIDTH], "little")


def peek_bytes(data: bytes, position: int, width: int) -> bytes | None:
    """`width` raw bytes at `position`, or `None` if they do not all fit.

    Returns `None` rather than a short slice. A truncated read is the failure mode that
    hides: `int.from_bytes` on three bytes returns a smaller number with nothing raised,
    which is how a lost alignment becomes a plausible wrong value instead of an error.
    """
    if width < 0 or not _in_bounds(data, position, width):
        return None
    return data[position : position + width]


def peek_date_parts(data: bytes, position: int) -> tuple[int, int, int] | None:
    """`(day, month, year)` at `position`, **unvalidated**, or `None` past the end.

    Deliberately raw. The save writes 0/0/0 where a date does not apply, and callers
    disagree about whether that is legitimate — a calendar record tolerates it, a player
    record being framed does not. Handing back the parts keeps that judgement where the
    context is.
    """
    if not _in_bounds(data, position, DATE_WIDTH):
        return None
    day = data[position]
    month = data[position + DAY_WIDTH]
    year_at = position + DAY_WIDTH + MONTH_WIDTH
    year = int.from_bytes(data[year_at : year_at + YEAR_WIDTH], "little")
    return day, month, year


def zero_run_width(data: bytes, position: int, limit: int) -> int:
    """How many consecutive zero bytes start at `position`, counting no further than `limit`.

    `limit` is required rather than optional: an unbounded scan over a 32 MB buffer is how
    a mis-framed walk turns into a long wait instead of a refusal. A caller that hits the
    limit is being told its assumption is wrong, not given a bigger number.
    """
    if position < 0:
        return 0
    width = 0
    while width < limit and position + width < len(data) and data[position + width] == 0:
        width += 1
    return width


def peek_length_prefixed_ascii(data: bytes, position: int, limit: int) -> tuple[int, int] | None:
    """`(length, end)` for a length-prefixed printable-ASCII string, or `None`.

    Does the prefix read, the bounds check and the printability filter in one call, and
    returns the **end offset** as well as the length so no caller has to re-derive it by
    adding the prefix width back. That is not a convenience: a caller writing
    `position + 4` would be reintroducing exactly the constant this module exists to
    remove.

    `limit` caps the declared length. Without it a garbage `u32` read as a length walks
    the rest of the file.
    """
    length = peek_u32(data, position)
    if length is None or length > limit:
        return None
    payload = peek_bytes(data, position + LENGTH_PREFIX_WIDTH, length)
    if payload is None:
        return None
    if any(byte < _FIRST_PRINTABLE or byte > _LAST_PRINTABLE for byte in payload):
        return None
    return length, position + LENGTH_PREFIX_WIDTH + length
