"""A forward-only cursor over a save buffer. There is no way to seek, deliberately.

Records in an OOTP save carry **variable-length regions** — contract arrays, stat
history, length-prefixed strings — so a field read at a constant offset from any
anchor is right for one record shape and wrong for every other, with nothing raised.
The measured evidence: the same player's ratings block sat 43 bytes from one anchor
in one save and 107 in another, with a byte-identical internal layout.

Every reader here advances the cursor and only advances it. The class exposes no
`seek`, no `position` setter, and no absolute read — the ban is **structural rather
than a convention**, so it survives the next agent who has a good reason. This is the
half of the ban that cannot be argued with: there is no legitimate seek anywhere,
so the AST guard over `src/ootp_ai/` never has to allow one.

Reading a buffer *without* the cursor is a separate question, and there the guard
does keep a short allowlist — **this module is on it**, because `take` below indexes
the buffer the cursor owns. Two modules, a stricter rule inside them, and a named
list of what the scan cannot see: `tests/test_no_fixed_offsets.py` and
[ADR 0020](../../../docs/decisions/0020-sanctioned-lookahead-seam.md).

Buffers are read whole (`Path.read_bytes()`) rather than streamed. The largest file
this project reads is ~32 MB, so the memory is free and it keeps the cursor a pure
function of a `bytes` object — no file handle, no mode, nothing that could be opened
for writing by accident.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import date

from ootp_ai.parser.errors import UnexpectedEndOfData

__all__ = ["Cursor", "SaveDate"]

# Little-endian, compiled once. `unpack_from` is always called with a *name* as its
# offset — the cursor's own position — never a literal, which is the distinction the
# fixed-offset guard draws.
_U8 = struct.Struct("<B")
_U16 = struct.Struct("<H")
_U32 = struct.Struct("<I")
_I32 = struct.Struct("<i")
_F64 = struct.Struct("<d")
_DATE = struct.Struct("<BBH")

_STRING_PREFIX = _U32


@dataclass(frozen=True, slots=True)
class SaveDate:
    """A date as the save stores it: `u8 day, u8 month, u16 year`.

    Kept as three integers rather than converted eagerly to `datetime.date` because
    the save writes 0/0/0 where a date does not apply, and `date` cannot represent
    that. Collapsing the two would turn **structural absence** into a wrong value —
    a player with no contract end date would acquire one.
    """

    day: int
    month: int
    year: int

    def as_date(self) -> date | None:
        """The calendar date, or `None` when the record carries no date at all.

        `None` means the field is structurally absent and must land as SQL NULL,
        never as a zero or an epoch.
        """
        try:
            return date(self.year, self.month, self.day)
        except ValueError:
            return None

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


class Cursor:
    """Forward-only reader over an in-memory save buffer.

    Read one field, advance by exactly its width, read the next. A caller that wants
    to skip an uninteresting region calls `skip(n)` with a width it computed from the
    bytes it already read — never a constant measured against a different save.
    """

    __slots__ = ("_data", "_label", "_position")

    def __init__(self, data: bytes, *, label: str = "<buffer>") -> None:
        self._data = data
        self._label = label
        self._position = 0

    def __repr__(self) -> str:
        return f"Cursor({self._label!r}, position={self._position}, remaining={self.remaining()})"

    @property
    def label(self) -> str:
        """What this buffer is, for error messages. Usually a filename."""
        return self._label

    @property
    def position(self) -> int:
        """Bytes consumed so far.

        Read-only on purpose: there is no setter, so a caller cannot restore a saved
        position and turn the cursor into a seeking reader through the back door.
        Byte accounting reads this; nothing writes it.
        """
        return self._position

    def remaining(self) -> int:
        return len(self._data) - self._position

    def exhausted(self) -> bool:
        """True when the walk consumed the buffer exactly — the zero-residual case."""
        return self.remaining() == 0

    # ── movement ─────────────────────────────────────────────────────────────

    def _advance(self, count: int) -> int:
        """Consume `count` bytes and return where they started.

        The single place the position changes, so the bounds check cannot be
        forgotten by a reader added later.
        """
        if count < 0:
            raise ValueError(f"a cursor only moves forward; got count={count}")
        start = self._position
        end = start + count
        if end > len(self._data):
            raise UnexpectedEndOfData(
                f"{self._label}: wanted {count} bytes at position {start}, "
                f"but only {self.remaining()} remain — the walk has lost alignment"
            )
        self._position = end
        return start

    def skip(self, count: int) -> None:
        """Advance without interpreting. The width must come from the data."""
        self._advance(count)

    def take(self, count: int) -> bytes:
        """Consume and return `count` raw bytes."""
        start = self._advance(count)
        return self._data[start : start + count]

    # ── primitives ───────────────────────────────────────────────────────────

    def u8(self) -> int:
        return int(_U8.unpack_from(self._data, self._advance(_U8.size))[0])

    def u16(self) -> int:
        return int(_U16.unpack_from(self._data, self._advance(_U16.size))[0])

    def u32(self) -> int:
        return int(_U32.unpack_from(self._data, self._advance(_U32.size))[0])

    def i32(self) -> int:
        return int(_I32.unpack_from(self._data, self._advance(_I32.size))[0])

    def f64(self) -> float:
        return float(_F64.unpack_from(self._data, self._advance(_F64.size))[0])

    def string(self, *, encoding: str = "ascii") -> str:
        """A u32-LE length prefix followed by raw characters and **no terminator**.

        `encoding` is a parameter rather than a constant because the encoding of
        `names.dat` is recorded `unconfirmed` in the format catalog: accented names
        exist, and the walker that resolves them will have to state what it assumed.
        Defaulting to strict ASCII means a non-ASCII byte raises here instead of
        being silently replaced — a mangled name is a wrong name.
        """
        length = int(_STRING_PREFIX.unpack_from(self._data, self._advance(_STRING_PREFIX.size))[0])
        return self.take(length).decode(encoding)

    def date(self) -> SaveDate:
        """`u8 day, u8 month, u16 year` — four bytes, in that order."""
        day, month, year = _DATE.unpack_from(self._data, self._advance(_DATE.size))
        return SaveDate(day=int(day), month=int(month), year=int(year))

    def color(self) -> int:
        """A u32 ARGB colour, returned as an integer (`0xffbd3039` is Red Sox red)."""
        return self.u32()
