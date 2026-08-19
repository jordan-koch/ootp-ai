"""`names.dat` — the string table player records point into, and the join that uses it.

## 1. Why this file exists at all

`players.dat` holds no names. It holds two `u32` indices per record, and every display
name in this project is the result of a two-file join. Until this walk landed, the
roster report could only have printed integers.

`docs/data-access.md` recorded the table's existence as `verified` and *"the index
encoding and the `names.dat` table layout"* as **`unconfirmed`** — which, per that
file's own rule, made it a task rather than a fact. This module is that task closed.

## 2. The record shape, measured

The header is the shared one (`header.py`), followed by the six-`u32` tail `teams.dat`
uses — and unlike `players.dat`, **this file declares a real record count**
(264,095 in all three saves). Then 46 zero bytes and the `u32` constant 1234, the same
preamble sentinel `players.dat` carries. Records follow with no padding between them:

| At | Field | Width |
|---|---|---|
| +0 | category | `u8` |
| +1 | length of the name | `u32` |
| +5 | the name itself, raw bytes, **no terminator** | length |
| | a `u32` that is zero on every record of every save | `u4` |
| | `index`, the value `players.dat` points with | `u32` |
| | `usage_count` | `u32` |
| | `usage_count` pairs of `u32`s | 8 each |

`verified` — the walk consumes the file to **zero residual** on all three saves and
frames exactly the count the header declares, which is what the strict tier means.

**The category byte LEADS the record; it is not a separator, and the difference is not
cosmetic.** Read as a trailing separator the walk finds 264,094 records and 8 leftover
bytes, because the final record has no byte after it. It also mis-stops at index
31,877 — the Dutch surname `'t Hart`, whose first character *is* an apostrophe
(`0x27`), the same value the first block's category byte takes. A separator that
collides with real data is not a separator.

## 3. There is ONE index space, and that was the open question

The plan pre-registered the risk that `names.dat` carried **two** tables — a
first-name space and a last-name space, each numbered from zero — because keying
`bronze_name` without a discriminator would then collide them and every collided row
would be silently wrong. It does not. Three independent measurements, all on the
standard-mode probe:

1. The header declares 264,095 records; the walk frames 264,095 with zero residual and
   `index == position + 1` for **every** one. A single monotonic run, no reset.
2. Both player slots resolve against this one table at **18,072/18,072 = 100.00%**.
3. **510 indices are used as a first name by one player and as a last name by another**,
   and both readings are correct. Two spaces could not produce that.

So `name_space` exists in the key as the pre-registered resolution says it should, and
it takes a single literal value — `SINGLE_NAME_SPACE` below. The key is right under
either outcome and the column costs nothing.

## 4. What the two u32s in the player head are, settled by brute force

`measured` — scoring every candidate mapping across all 18,072 probe players against
`ootp_truth_real`:

| Mapping | Score |
|---|---|
| `+4` as **first**, `+8` as **last** | **18,072 / 18,072 = 100.00%** |
| `+4` as last, `+8` as first | 1 / 18,072 = 0.01% |

That is the shape a correct answer has and a plausible one does not, which is why the
plan required brute force here rather than a reading of the bytes. `players.py` names
the two fields as a result; it carried them as an opaque pair until this ran.

## 5. The category byte is NOT a first/last discriminator

It is tempting: index 1..31,876 is `0x27`, 31,877..252,899 is `0x07`, and those blocks
are given names and surnames respectively. But `measured` — of the indices players
actually use as a **last** name, 6,668 point at `0x27` records. The blocks describe
where OOTP's shipped name lists sit, not what a name may be used for. So the byte lands
`unconfirmed` and nothing joins on it. Recording this is the point: a plausible reading
that scores 63% is exactly the kind of claim this project refuses.

## 6. The table is per-save by construction, and here is the honest evidence

The plan expected the three saves to hold three different tables and asked for a
resolver whose cache key includes `save_id`. **Measured, and it refutes that premise:**
all three `names.dat` files are 8,642,110 bytes with three different SHA-256 digests,
but their **record bodies are byte-identical** — all 264,095 index→string mappings
agree exactly. The digests differ only in the header, at the league sim date (byte 75)
and the wall-clock write time (bytes 99-110).

The structural rule is kept anyway, and in its **stronger** form: this module holds no
cache at all. A `NameTable` is a value object that carries the `save_id` it was built
from, so a table can only be applied to a save by a caller that names both. Identity
across today's three saves is a measured fact about shipped data, not an invariant —
a patch, a mod, or a custom name master would break it — and the failure mode it would
produce is a roster full of confident, wrong names with nothing raised.

## 7. Encoding

`verified` for every name any player carries: decoding as **latin-1** matches
`ootp_truth_real` exactly on all 18,072 rows. cp1252 scores identically, because the
two disagree on only one string in the whole table — index 259,322, which is
already-corrupt mojibake in OOTP's shipped data and is wrong under both readings.
latin-1 is chosen because it is total: it never raises, so a byte nobody has seen
cannot turn a landing into a crash, and no information is lost.

`players.csv` is **not** an exact answer key for names: it ships pure ASCII with every
accented character already replaced by `?`. That is a property of the shipped file, not
of this walk — see `tests/test_names_join_boston.py`, which folds the same way and says
so.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.header import read_header_from
from ootp_ai.parser.lookahead import U32_WIDTH, peek_u32, zero_run_width
from ootp_ai.parser.primitives import Cursor, SaveDate

__all__ = [
    "BYTE_ACCOUNTING_TIER",
    "NAMES_FILE",
    "NAME_ENCODING",
    "SINGLE_NAME_SPACE",
    "TIER_RATIONALE",
    "NameRecord",
    "NameRecordLayout",
    "NameTable",
    "NamesFile",
    "UnknownNameIndex",
    "build_name_table",
    "read_names",
]

#: Sits inside the `.lg` directory, beside `players.dat`.
NAMES_FILE = "names.dat"

BYTE_ACCOUNTING_TIER = "strict"

TIER_RATIONALE = (
    "Every byte of names.dat is consumed: the header, the six-u32 header tail with its "
    "declared record count, the 46-byte zero preamble and the 1234 constant, and then "
    "every record's category byte, length-prefixed name, zero field, index, usage count "
    "and usage pairs. The walk ends exactly at the end of the buffer on all three saves "
    "on disk and frames exactly the 264,095 records the header declares. Strict is "
    "reachable here and is not in players.dat for the reason that file's rationale gives: "
    "this record has no undecoded body. Every field width is confirmed by the fact that a "
    "wrong one desynchronises the next length prefix and the walk cannot reach the end."
)

#: The one value `name_space` takes, and why the column exists at all is in §3 above.
#: A literal rather than a bare string at every call site so that proving a second space
#: later is one edit here plus a red test, rather than a search for string constants.
SINGLE_NAME_SPACE: Final = "all"

#: How many `u32`s follow the header's two wide dates, as in `teams.dat`.
_HEADER_TAIL_FIELDS = 6

#: Where the declared record count sits within that tail. An index into a tuple the
#: cursor already read, never an offset into the buffer.
_DECLARED_COUNT_FIELD = 4

#: Between the header tail and the first record: a run of zeros and then this `u32`.
#: The same sentinel `players.dat` carries at the same place. `measured` — 46 zero bytes
#: in all three saves, but the walk searches for the constant rather than skipping a
#: width, because a constant preamble length is exactly the assumption this project bans.
_PREAMBLE_CONSTANT = 1234

#: A preamble longer than this means the constant found was a coincidence somewhere deep
#: in the file rather than the sentinel. `measured` — the real gap is 46 bytes.
_MAX_PREAMBLE_BYTES = 512

#: Refuse a declared count that is not a name table, so a garbage count cannot become a
#: loop bound. `measured` — 264,095 in all three saves.
_MAX_RECORDS = 5_000_000

#: A name longer than this is a lost walk, not a name. `measured` — the longest entry in
#: the table is well inside this bound.
_MAX_NAME_LENGTH = 64

#: Usage pairs per record. `measured` — the largest observed is far below this; the bound
#: exists so a mis-read count cannot allocate against a 8.6 MB buffer.
_MAX_USAGE_PAIRS = 256

#: `measured` — the `u32` between the name and its index is zero on every record of every
#: save (264,095 records x 3). Asserted rather than skipped: if it is ever non-zero, this
#: walk is reading a field it does not understand and the shape has changed.
_EXPECTED_ZERO = 0

#: latin-1 rather than ascii: 1,621 of 264,095 entries carry a byte above 0x7f and the
#: cursor's default would raise on every one. See §7.
NAME_ENCODING: Final = "latin-1"


class NameRecordLayout(SaveFormatError):  # noqa: N818
    """A valid version-25 `names.dat` whose records are not shaped as measured."""


class UnknownNameIndex(LookupError):  # noqa: N818 - a LookupError, named as one
    """A player points at an index the name table does not hold.

    Its own class because the two ways this can happen need different responses: a
    parser bug in the player walk, or a name table from a different save. Both are
    silent-wrong failures if resolved to a placeholder, so nothing here returns one.
    """


@dataclass(frozen=True, slots=True)
class NameRecord:
    """One entry of the string table."""

    index: int
    text: str
    #: `0x07`, `0x27`, `0x0f`, `0x17` or `0x37` in the saves measured. **Not** a
    #: first/last discriminator — see §5. Landed as an opaque integer, `unconfirmed`.
    category: int
    #: The `(u32, u32)` pairs trailing each record. The first element of each ranges
    #: 0-40 across 41 distinct values, which is name-origin-group shaped rather than
    #: nation-shaped (the world holds ~206 nations). `unconfirmed`, and nothing reads it.
    usage: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class NamesFile:
    """Every name the table declares, plus what the walk can say about itself."""

    names: tuple[NameRecord, ...]
    #: Zero on every save measured. This walker declares the **strict** tier, so a
    #: nonzero value here is a red test, not a recorded diagnostic.
    residual_bytes: int
    sim_date: SaveDate
    #: Unlike `players.dat`, this file declares a real count and the walk checks it.
    declared_record_count: int


@dataclass(frozen=True, slots=True)
class NameTable:
    """A save's name table, and the only thing that can resolve that save's indices.

    Carries the `save_id` it was built from precisely so a table cannot be applied to a
    save without a caller naming both. There is **no module-level cache** in this module
    — see §6 for why that is the stronger form of the plan's requirement rather than a
    shortcut around it.
    """

    save_id: str
    sim_date: SaveDate
    entries: dict[int, str]

    def resolve(self, index: int) -> str:
        """The string at `index`, or raise. Never a placeholder, never an empty string.

        A missing index means either the player walk read the wrong bytes or this table
        belongs to a different save. Both produce wrong names rather than missing ones,
        so neither may be absorbed into a default.
        """
        try:
            return self.entries[index]
        except KeyError:
            raise UnknownNameIndex(
                f"{self.save_id}: name index {index} is not in the {len(self.entries):,}-entry "
                f"table. Either the player walk is reading the wrong bytes, or this table "
                f"was built from a different save."
            ) from None

    def display_name(self, first_index: int, last_index: int) -> str:
        """`First Last`, both resolved. Raises rather than returning a half name."""
        return f"{self.resolve(first_index)} {self.resolve(last_index)}"

    def for_save(self, save_id: str) -> NameTable:
        """Return this table, having checked it belongs to `save_id`.

        `save_id` was decorative until this existed: a table carried the field and
        nothing ever compared it, so applying the probe's table to the managed league —
        the precise failure §6 keeps the per-save structure for — was a silent success.

        Callers that resolve names for a save they can name should route through this
        rather than reaching for `.entries` directly, so the mismatch raises at the point
        the wrong table is picked up rather than as a roster full of plausible names.
        """
        if save_id != self.save_id:
            raise UnknownNameIndex(
                f"this name table was built from {self.save_id!r} and is being used for "
                f"{save_id!r}. The tables of the saves on disk happen to be byte-identical "
                "today, so this would very likely produce correct names and prove nothing "
                "— which is exactly why it is refused rather than trusted."
            )
        return self


def build_name_table(save_id: str, data: bytes) -> NameTable:
    """Walk `data` and return a table owned by `save_id`.

    The `save_id` is a parameter and not something this module derives, because the one
    thing that must never happen is a table acquiring a save identity by inference.
    """
    parsed = read_names(data)
    entries = {record.index: record.text for record in parsed.names}
    if len(entries) != len(parsed.names):
        # Belt and braces behind `_check_index`. A dict comprehension is last-write-wins,
        # so if the index guard is ever relaxed this is the second thing that has to be
        # defeated before a collapsed table can reach a roster report.
        raise NameRecordLayout(
            f"{NAMES_FILE}: {len(parsed.names):,} records collapsed into "
            f"{len(entries):,} table entries, so at least one index is repeated and one "
            "name has been silently discarded."
        )
    return NameTable(save_id=save_id, sim_date=parsed.sim_date, entries=entries)


def _check_index(record: NameRecord, *, expected: int) -> None:
    """Hold the walk to the index property the rest of this project keys on.

    `index == position + 1` is measured on all 264,095 records of all three saves, and
    §3 offers it as one of the three proofs that there is a single index space. Prose is
    not enforcement: without this check a file with a repeated index walks clean at zero
    residual — the strict tier fully satisfied, nothing raised — and `build_name_table`'s
    dict then keeps the *last* string and silently discards the first. Every player
    pointing at that index gets a confident wrong name, which is the exact failure §6
    argues this module exists to prevent.

    It also protects a declaration that has already been written down: `bronze_name`'s
    Phase 8 key is `(save_id, sim_date, ingest_seq, name_space, name_index)`, and a
    duplicate index makes that key a lie before the table is ever built.

    Checked as `expected` rather than merely as uniqueness because monotonic-from-1 is
    the stronger measured claim, and a set membership test would cost a second pass over
    264,095 records to catch less.
    """
    if record.index != expected:
        raise NameRecordLayout(
            f"{NAMES_FILE}: the record at table position {expected} declares index "
            f"{record.index}. Indices are measured to run 1..N with no gap and no repeat "
            "in every save on disk, and both the single-index-space finding and "
            "bronze_name's declared key rest on that. A repeat in particular is silent: "
            "the table would keep one string per index and discard the other, and every "
            "player pointing there would get a confident wrong name."
        )


def read_names(data: bytes) -> NamesFile:
    """Walk a `names.dat` buffer and return every entry of the string table.

    Raises:
        MalformedHeader: the buffer is truncated, or is not an OOTP record file.
        UnsupportedSaveVersion: the declared version is not the one we are proven on.
        SaveFilenameMismatch: the header names a different file.
        UnexpectedEndOfData: a read ran past the end of the buffer.
        NameRecordLayout: the preamble or a record is not shaped as measured.
    """
    cursor = Cursor(data, label=NAMES_FILE)
    header = read_header_from(cursor, NAMES_FILE)
    tail = tuple(cursor.u32() for _ in range(_HEADER_TAIL_FIELDS))
    declared = tail[_DECLARED_COUNT_FIELD]

    if not 0 < declared <= _MAX_RECORDS:
        raise NameRecordLayout(
            f"{NAMES_FILE} declares {declared} records, which is not a name table. The "
            "header tail is not where this walk believes it is, and every width after it "
            "would be read from the wrong place."
        )

    _read_preamble(cursor, data)

    names: list[NameRecord] = []
    while len(names) < declared:
        record = _read_record(cursor)
        _check_index(record, expected=len(names) + 1)
        names.append(record)

    residual = cursor.remaining()
    if residual:
        raise NameRecordLayout(
            f"{NAMES_FILE}: framed all {declared} declared records but {residual} bytes "
            f"remain. This walker declares the {BYTE_ACCOUNTING_TIER!r} tier, which means "
            "zero residual; a leftover means a record carries a field this walk does not "
            "read, and the tier claim is false."
        )

    return NamesFile(
        names=tuple(names),
        residual_bytes=residual,
        sim_date=header.sim_date,
        declared_record_count=declared,
    )


def _read_preamble(cursor: Cursor, data: bytes) -> None:
    """Cross the zero run between the header tail and the `1234` sentinel.

    Measured as 46 bytes in all three saves, and deliberately **not** skipped by that
    width: `synthetic.py` carries the note about a "header constant" that turned out to
    be one save's sim date, and a preamble length confirmed against three saves of one
    game version has exactly that shape. The run is measured from the data instead, and
    the sentinel behind it is what says the walk arrived where it meant to.

    Both reads go through the sanctioned lookahead seam (ADR 0020) rather than indexing
    the buffer here — `names.py` is not on the allowlist, and should not be.
    """
    start = cursor.position
    run = zero_run_width(data, start, _MAX_PREAMBLE_BYTES)
    if peek_u32(data, start + run) != _PREAMBLE_CONSTANT:
        raise NameRecordLayout(
            f"{NAMES_FILE}: expected the {_PREAMBLE_CONSTANT} sentinel after the header "
            f"tail's zero run, but {run} zero bytes in there is no sentinel. The record "
            "region does not begin where this walk believes, and reading on would decode "
            "arbitrary bytes as names."
        )
    cursor.skip(run + U32_WIDTH)


def _read_record(cursor: Cursor) -> NameRecord:
    """One table entry, read as a plain forward sequence of typed reads.

    Every width here comes from the bytes themselves — the name's length prefix and the
    usage count — so there is nothing to look ahead for and the record needs no
    reconcile-then-consume pass.
    """
    category = cursor.u8()

    at = cursor.position
    text = _read_name(cursor, at)

    zero = cursor.u32()
    if zero != _EXPECTED_ZERO:
        raise NameRecordLayout(
            f"{NAMES_FILE}: the field after the name at byte {at} is {zero}, not "
            f"{_EXPECTED_ZERO}. It is zero on every record of every save measured, so a "
            "value here means this walk is no longer aligned to a record."
        )

    index = cursor.u32()
    usage_count = cursor.u32()
    if usage_count > _MAX_USAGE_PAIRS:
        raise NameRecordLayout(
            f"{NAMES_FILE}: entry {index} at byte {at} declares {usage_count} usage pairs, "
            f"above the {_MAX_USAGE_PAIRS} bound. The walk has lost alignment; reading on "
            "would consume the rest of the file as one record."
        )

    usage = tuple((cursor.u32(), cursor.u32()) for _ in range(usage_count))
    return NameRecord(index=index, text=text, category=category, usage=usage)


def _read_name(cursor: Cursor, at: int) -> str:
    """The length-prefixed name, decoded latin-1 and required to carry a character.

    A blank name resolves to a blank display name downstream, which AC9 forbids and
    which is worse than a refusal because it looks like a player with no name rather
    than a parser that lost its place.

    **Whitespace counts as blank.** Checking only `len(text) == 0` would let a
    length-prefixed run of spaces through, and `" ".strip()` downstream produces exactly
    the empty display name the zero-length check exists to stop — so the two shapes are
    refused together, here, rather than one here and one in a report layer that does not
    exist yet.
    """
    text = cursor.string(encoding=NAME_ENCODING)
    if not text.strip():
        raise NameRecordLayout(
            f"{NAMES_FILE}: the entry at byte {at} declares a blank name ({text!r}). Every "
            "entry in the table is a real string, so an empty or whitespace-only one means "
            "the walk is reading a length prefix out of the middle of some other field."
        )
    if len(text) > _MAX_NAME_LENGTH:
        raise NameRecordLayout(
            f"{NAMES_FILE}: the entry at byte {at} declares a {len(text)}-character name, "
            f"above the {_MAX_NAME_LENGTH} bound. That is a lost walk reading arbitrary "
            "bytes as a length, not a name."
        )
    return text
