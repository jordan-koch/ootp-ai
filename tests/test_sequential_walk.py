"""AC2 — a sequential reader survives a variable-length region; a seeking one does not.

This is the invariant the whole parser rests on. `.claude/agents/data-engineer.md:69-74`
records the measured evidence: the same player's ratings block sat 43 bytes from one
anchor in one save and 107 in another, with byte-identical internal layout. A reader
that seeks to a constant offset passes on day-0 data — which is exactly what both
saves on disk are — and then silently returns the wrong field for every player with a
differently-shaped record.

The module carries a **negative control**: a deliberately fixed-offset reader that
must FAIL the same comparison. A test that cannot fail proves nothing, and this one
would pass trivially if `make_record` ever stopped varying its length.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import struct

import pytest
from ootp_ai.parser.errors import UnexpectedEndOfData
from ootp_ai.parser.primitives import Cursor

from fixtures.synthetic import make_record, make_string


def read_sequentially(data: bytes) -> dict[str, object]:
    """Walk the synthetic record forward, never seeking."""
    cursor = Cursor(data)
    player_id = cursor.u32()
    contract_years = cursor.u32()
    for _ in range(contract_years):
        cursor.u32()
    uniform_number = cursor.u32()
    historical_id = cursor.string()
    return {
        "player_id": player_id,
        "uniform_number": uniform_number,
        "historical_id": historical_id,
    }


def read_at_fixed_offsets(data: bytes) -> dict[str, object]:
    """The NEGATIVE CONTROL — how a plausible-looking wrong parser behaves.

    Offsets calibrated against a 1-year contract, which is what a day-0 save mostly
    contains. Nothing here raises; it simply returns different numbers.
    """
    player_id = struct.unpack_from("<I", data, 0)[0]
    uniform_number = struct.unpack_from("<I", data, 12)[0]
    name_len = struct.unpack_from("<I", data, 16)[0]
    historical_id = data[20 : 20 + name_len].decode("ascii", errors="replace")
    return {
        "player_id": player_id,
        "uniform_number": uniform_number,
        "historical_id": historical_id,
    }


# ── the invariant ────────────────────────────────────────────────────────────


def test_the_two_records_really_do_differ_in_length() -> None:
    """Guards the guard. If the fixture stopped varying, every assertion below
    would pass while testing nothing at all."""
    assert len(make_record(contract_years=1)) != len(make_record(contract_years=10))


def test_fields_after_a_variable_region_read_identically() -> None:
    short = read_sequentially(make_record(contract_years=1))
    long = read_sequentially(make_record(contract_years=10))
    assert short == long
    assert short["uniform_number"] == 34
    assert short["historical_id"] == "deverra01"


@pytest.mark.parametrize("years", [0, 1, 2, 5, 10, 40])
def test_the_walk_is_stable_across_many_shapes(years: int) -> None:
    parsed = read_sequentially(make_record(contract_years=years))
    assert parsed["player_id"] == 47035
    assert parsed["uniform_number"] == 34
    assert parsed["historical_id"] == "deverra01"


# ── the negative control ─────────────────────────────────────────────────────


def test_the_fixed_offset_reader_passes_on_the_day_zero_shape() -> None:
    """This is precisely why the bug is dangerous: it looks correct on real data."""
    assert read_at_fixed_offsets(make_record(contract_years=1))["uniform_number"] == 34


def test_the_fixed_offset_reader_silently_returns_the_wrong_field() -> None:
    """No exception. No warning. A plausible integer, and it is not the right one."""
    wrong = read_at_fixed_offsets(make_record(contract_years=10))
    assert wrong["uniform_number"] != 34, (
        "the negative control stopped failing — either make_record no longer varies "
        "its length, or the offsets were recalibrated, and AC2 is now vacuous"
    )
    assert wrong["historical_id"] != "deverra01"


# ── the primitives the walk depends on ───────────────────────────────────────


def test_a_string_is_length_prefixed_with_no_terminator() -> None:
    cursor = Cursor(make_string("Boston") + b"\xff")
    assert cursor.string() == "Boston"
    assert cursor.remaining() == 1, "the reader consumed a terminator that is not there"


def test_a_date_reads_day_month_year() -> None:
    from fixtures.synthetic import make_date

    parsed = Cursor(make_date(24, 10, 1996)).date()
    assert (parsed.day, parsed.month, parsed.year) == (24, 10, 1996)


def test_a_color_reads_as_u32_argb() -> None:
    from fixtures.synthetic import make_color

    assert Cursor(make_color(0xFFBD3039)).color() == 0xFFBD3039


def test_the_cursor_reports_what_is_left() -> None:
    cursor = Cursor(b"\x01\x02\x03\x04\x05")
    assert cursor.remaining() == 5
    cursor.u32()
    assert cursor.remaining() == 1


def test_skip_advances_without_reading() -> None:
    cursor = Cursor(b"\xaa\xbb\xcc\xdd\x2a")
    cursor.skip(4)
    assert cursor.u8() == 42


def test_reading_past_the_end_raises_rather_than_returning_garbage() -> None:
    cursor = Cursor(b"\x01\x02")
    with pytest.raises(UnexpectedEndOfData):
        cursor.u32()


def test_the_cursor_exposes_no_way_to_seek() -> None:
    """§2.3(a): the ban is structural, not a convention.

    If a `seek` ever appears here, `test_no_fixed_offsets.py`'s AST scan can be
    satisfied while the hazard walks back in through a different door.
    """
    cursor = Cursor(b"\x00" * 8)
    for forbidden in ("seek", "seek_to", "at", "goto", "set_position"):
        assert not hasattr(cursor, forbidden), f"Cursor grew a {forbidden}() method"
