"""AC1 — the header/version guard must REFUSE, not warn. Offline: no game, no MySQL.

The trap this guards is recorded at `docs/data-access.md:183-186` and it is unusual
in being a *symmetric* trap — both naive readings fail, and both fail on the very
first file opened:

- A reader checking `data[0:4] == b"OOTP"` sees `\\x00OOT` on every real save and
  rejects all of them.
- A reader taking the version as a u32 at offset 4 gets 6480 rather than 25.

Loud failure is the tolerable outcome (`.claude/agents/data-engineer.md:82-84`: *"a
loud failure is recoverable, a silent misparse is not"*), which is why every
assertion below is that something *raises* rather than that it copes.
"""

from __future__ import annotations

import pytest

from fixtures.synthetic import CURRENT_VERSION, make_header
from ootp_ai.parser.errors import (
    MalformedHeader,
    SaveFilenameMismatch,
    UnsupportedSaveVersion,
)
from ootp_ai.parser.header import MAGIC_PREFIX, looks_like_save_file, read_header


def test_a_valid_v25_header_parses() -> None:
    header = read_header(make_header(filename="players.dat"), expected_filename="players.dat")
    assert header.version == CURRENT_VERSION
    assert header.filename == "players.dat"


def test_the_header_carries_the_leagues_sim_date() -> None:
    """Offsets 75-86 are the sim date as three u32s — `measured` across three saves.

    This matters beyond curiosity: **every record file carries the sim date in its
    own header**, so a snapshot can key itself from the file it is already reading
    rather than from `saved_games.dat`, which embeds an absolute user-profile path
    this public repo must never render.
    """
    header = read_header(make_header(sim_date=(18, 3, 2024)), expected_filename="players.dat")
    assert (header.sim_date.day, header.sim_date.month, header.sim_date.year) == (18, 3, 2024)


def test_the_header_carries_the_wall_clock_write_date_separately() -> None:
    """Two distinct dates. Conflating them would make a snapshot key drift with the
    clock rather than with the league."""
    header = read_header(
        make_header(sim_date=(7, 3, 2024), written_date=(16, 8, 2026)),
        expected_filename="players.dat",
    )
    assert (header.sim_date.day, header.sim_date.year) == (7, 2024)
    assert (header.written_date.day, header.written_date.month, header.written_date.year) == (
        16,
        8,
        2026,
    )


def test_the_header_does_not_claim_to_know_where_records_begin() -> None:
    """`read_header` must expose no `length`/`end`/`body_offset`.

    An earlier draft asserted the body started at 79. It does not: bytes 99-110 vary
    per save, 111 is constant per file type, 115 varies per save, and where records
    actually start is still `unconfirmed`. A parser that trusted a wrong body offset
    would mis-read every record with nothing raised — so the honest interface is to
    offer no answer at all until one is measured.
    """
    header = read_header(make_header(), expected_filename="players.dat")
    for invented in ("length", "end", "size", "body_offset", "record_start"):
        assert not hasattr(header, invented), (
            f"header exposes {invented!r} — where records begin has not been measured"
        )


@pytest.mark.parametrize("version", [24, 26, 0, 6480])
def test_an_unrecognised_version_raises_by_name(version: int) -> None:
    """`UnsupportedSaveVersion` is pinned by name — the guard's whole job is to be
    identifiable when OOTP 26 ships and the byte layout may have moved."""
    with pytest.raises(UnsupportedSaveVersion):
        read_header(make_header(version=version), expected_filename="players.dat")


def test_the_unsupported_version_error_names_the_version_it_saw() -> None:
    """An error that says only 'bad version' costs the next reader a debug cycle."""
    with pytest.raises(UnsupportedSaveVersion, match="26"):
        read_header(make_header(version=26), expected_filename="players.dat")


def test_magic_at_offset_zero_is_rejected() -> None:
    """The malformed shape a naive writer produces. Real saves lead with 0x00."""
    with pytest.raises(MalformedHeader):
        read_header(make_header(magic_at_offset_zero=True), expected_filename="players.dat")


def test_a_wrong_magic_is_rejected() -> None:
    with pytest.raises(MalformedHeader):
        read_header(make_header(magic=b"XXXX"), expected_filename="players.dat")


def test_a_nonzero_leading_byte_is_rejected() -> None:
    with pytest.raises(MalformedHeader):
        read_header(make_header(leading=0x01), expected_filename="players.dat")


def test_a_filename_disagreement_is_rejected() -> None:
    """The header names its own file. That is a free check that the file on disk is
    the file we think we opened — cheap, and it catches a mis-wired path."""
    with pytest.raises(SaveFilenameMismatch):
        read_header(make_header(filename="teams.dat"), expected_filename="players.dat")


def test_the_filename_mismatch_error_names_both_sides() -> None:
    with pytest.raises(SaveFilenameMismatch, match=r"teams\.dat"):
        read_header(make_header(filename="teams.dat"), expected_filename="players.dat")


def test_a_truncated_header_raises_rather_than_reading_past_the_end() -> None:
    with pytest.raises(MalformedHeader):
        read_header(make_header()[:40], expected_filename="players.dat")


def test_an_empty_buffer_raises() -> None:
    with pytest.raises(MalformedHeader):
        read_header(b"", expected_filename="players.dat")


# ── looks_like_save_file — the cheap classifier, previously untested ─────────
#
# This had no direct coverage before 2026-08-18, which was found while rewriting it onto
# `data.startswith(MAGIC_PREFIX)`. It is the function a caller uses to filter a `*.dat`
# glob before handing anything to `read_header`, so a wrong answer here means either
# refusing a real save or feeding a ZIP to the header reader.


def test_a_real_header_looks_like_a_save_file() -> None:
    assert looks_like_save_file(make_header(filename="teams.dat"))


def test_the_prefix_is_the_leading_null_and_the_magic_together() -> None:
    """Pinned as one value, because splitting it is how both classic traps are written."""
    assert MAGIC_PREFIX == b"\x00OOTP"


def test_magic_at_offset_zero_does_not_look_like_a_save_file() -> None:
    """The symmetric trap: `b"OOTP"` at offset 0 is what a naive writer produces."""
    assert not looks_like_save_file(make_header(magic_at_offset_zero=True))


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x00",
        b"\x00OOT",  # one byte short of the prefix
        b"PK\x03\x04zipfile",  # text_data.dat really is a ZIP
        b"plain text log",  # flag_save_completed.dat really is text
    ],
)
def test_things_that_are_not_record_files_are_rejected(payload: bytes) -> None:
    """A `*.dat` glob catches two files that were never records; this is what filters them."""
    assert not looks_like_save_file(payload)


def test_the_classifier_never_raises_on_a_short_buffer() -> None:
    """It is a filter, not a guard — raising here would defeat the point of calling it."""
    for width in range(len(MAGIC_PREFIX) + 2):
        # Slicing past the end yields the whole prefix, so anything at or beyond the
        # full width is a match — the point is that no width raises.
        assert looks_like_save_file(MAGIC_PREFIX[:width]) is (width >= len(MAGIC_PREFIX))


def test_every_header_error_shares_one_base_so_callers_can_catch_broadly() -> None:
    from ootp_ai.parser.errors import SaveFormatError

    assert issubclass(UnsupportedSaveVersion, SaveFormatError)
    assert issubclass(SaveFilenameMismatch, SaveFormatError)
    assert issubclass(MalformedHeader, SaveFormatError)
