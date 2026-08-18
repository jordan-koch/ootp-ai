"""The sanctioned lookahead seam — offline, synthetic, no game data and no MySQL.

Every one of these runs in CI, which is the point: the seam is about to become the only
place in the parser allowed to index a save buffer, so its own edge cases cannot be left
to `-m gamedata` tests that CI never sees.

The cases that earn their place are the **boundaries**, because that is where the three
predecessor implementations disagreed with each other. One rejected a negative position
and two did not; none of them agreed on what to do with a short read. Those disagreements
were invisible while each module carried its own copy.
"""

from __future__ import annotations

import pytest

from ootp_ai.parser.lookahead import (
    DATE_WIDTH,
    DAY_WIDTH,
    LENGTH_PREFIX_WIDTH,
    MONTH_WIDTH,
    U8_WIDTH,
    U16_WIDTH,
    U32_WIDTH,
    YEAR_WIDTH,
    peek_bytes,
    peek_date_parts,
    peek_length_prefixed_ascii,
    peek_u8,
    peek_u32,
    zero_run_width,
)

BUF = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])


# ── the declared spans ───────────────────────────────────────────────────────


def test_the_declared_spans_are_the_widths_the_format_actually_uses() -> None:
    """Named widths are the whole point — an offset must be expressible as their sum."""
    assert (U8_WIDTH, U16_WIDTH, U32_WIDTH) == (1, 2, 4)
    assert DATE_WIDTH == DAY_WIDTH + MONTH_WIDTH + YEAR_WIDTH == 4
    assert LENGTH_PREFIX_WIDTH == U32_WIDTH


# ── peek_u8 / peek_u32 ───────────────────────────────────────────────────────


def test_peek_u8_reads_without_consuming() -> None:
    assert peek_u8(BUF, 0) == 0x01
    assert peek_u8(BUF, 3) == 0x04
    assert peek_u8(BUF, 0) == 0x01, "a peek must not advance anything"


def test_peek_u32_is_little_endian() -> None:
    assert peek_u32(BUF, 0) == 0x04030201


@pytest.mark.parametrize("position", [len(BUF), len(BUF) + 1, 10_000])
def test_peek_past_the_end_is_none_not_an_exception(position: int) -> None:
    assert peek_u8(BUF, position) is None
    assert peek_u32(BUF, position) is None


def test_a_u32_that_only_partly_fits_is_none() -> None:
    """The boundary that matters: three bytes available where four are needed."""
    assert peek_u32(BUF, len(BUF) - U32_WIDTH) is not None
    assert peek_u32(BUF, len(BUF) - U32_WIDTH + 1) is None


@pytest.mark.parametrize("position", [-1, -4, -10_000])
def test_a_negative_position_is_out_of_bounds_not_an_index_from_the_end(
    position: int,
) -> None:
    """Python would return real bytes here. That is the trap.

    Two of the three predecessor implementations allowed it. A negative position means the
    caller's arithmetic went wrong, and returning plausible data hides exactly the class of
    bug this module exists to make visible.
    """
    assert peek_u8(BUF, position) is None
    assert peek_u32(BUF, position) is None
    assert peek_bytes(BUF, position, U8_WIDTH) is None
    assert peek_date_parts(BUF, position) is None
    assert zero_run_width(BUF, position, limit=8) == 0


# ── peek_bytes ───────────────────────────────────────────────────────────────


def test_peek_bytes_returns_exactly_the_width_asked_for() -> None:
    assert peek_bytes(BUF, 2, 3) == bytes([0x03, 0x04, 0x05])


def test_peek_bytes_refuses_a_short_read_rather_than_truncating() -> None:
    """A short slice is the silent failure: int.from_bytes on it returns a smaller number."""
    assert peek_bytes(BUF, len(BUF) - 2, 2) is not None
    assert peek_bytes(BUF, len(BUF) - 2, 3) is None


def test_a_negative_width_is_refused() -> None:
    assert peek_bytes(BUF, 0, -1) is None


# ── peek_date_parts ──────────────────────────────────────────────────────────


def test_peek_date_parts_reads_day_month_then_a_u16_year() -> None:
    raw = bytes([26, 6, 0xCC, 0x07])  # 1996 == 0x07CC
    assert peek_date_parts(raw, 0) == (26, 6, 1996)


def test_peek_date_parts_does_not_validate() -> None:
    """Structural absence reaches the caller intact, because callers disagree about it.

    `world.py` treats a zero year as legitimate in a calendar record; `players.py` rejects
    it when framing. A shared validator would have had to break one of them.
    """
    assert peek_date_parts(bytes(DATE_WIDTH), 0) == (0, 0, 0)
    assert peek_date_parts(bytes([99, 77, 0xFF, 0xFF]), 0) == (99, 77, 65535)


def test_a_date_that_only_partly_fits_is_none() -> None:
    raw = bytes([26, 6, 0xCC])
    assert peek_date_parts(raw, 0) is None


# ── zero_run_width ───────────────────────────────────────────────────────────


def test_zero_run_width_counts_only_leading_zeros() -> None:
    raw = bytes([0, 0, 0, 9, 0])
    assert zero_run_width(raw, 0, limit=10) == 3
    assert zero_run_width(raw, 3, limit=10) == 0


def test_zero_run_width_stops_at_its_limit() -> None:
    """The limit is required, not decorative — an unbounded scan over 32 MB is a hang."""
    assert zero_run_width(bytes(1000), 0, limit=8) == 8


def test_zero_run_width_stops_at_the_end_of_the_buffer() -> None:
    assert zero_run_width(bytes(3), 0, limit=100) == 3


# ── peek_length_prefixed_ascii ───────────────────────────────────────────────


def _string(value: str) -> bytes:
    return len(value).to_bytes(U32_WIDTH, "little") + value.encode("ascii")


def test_a_length_prefixed_string_reports_its_length_and_its_end() -> None:
    """Returning `end` is why no caller has to write `position + 4` and reintroduce a constant."""
    raw = _string("Red Sox") + b"trailing"
    assert peek_length_prefixed_ascii(raw, 0, limit=64) == (7, LENGTH_PREFIX_WIDTH + 7)


def test_an_empty_string_is_legal_and_ends_after_its_prefix() -> None:
    assert peek_length_prefixed_ascii(_string(""), 0, limit=64) == (0, LENGTH_PREFIX_WIDTH)


def test_a_non_printable_payload_is_refused() -> None:
    """The filter that stops a string scan firing on integer data."""
    raw = LENGTH_PREFIX_WIDTH.to_bytes(U32_WIDTH, "little") + bytes([0x00, 0x01, 0x41, 0x42])
    assert peek_length_prefixed_ascii(raw, 0, limit=64) is None


def test_a_length_beyond_the_limit_is_refused() -> None:
    """Without the cap, a garbage u32 read as a length walks the rest of the file."""
    raw = _string("a longer club name than the caller expects")
    assert peek_length_prefixed_ascii(raw, 0, limit=8) is None


def test_a_payload_that_runs_off_the_end_is_refused() -> None:
    raw = (99).to_bytes(U32_WIDTH, "little") + b"short"
    assert peek_length_prefixed_ascii(raw, 0, limit=1000) is None


def test_a_truncated_length_prefix_is_refused() -> None:
    assert peek_length_prefixed_ascii(b"\x02\x00", 0, limit=64) is None
