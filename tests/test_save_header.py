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
from ootp_ai.parser.header import read_header


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


def test_every_header_error_shares_one_base_so_callers_can_catch_broadly() -> None:
    from ootp_ai.parser.errors import SaveFormatError

    assert issubclass(UnsupportedSaveVersion, SaveFormatError)
    assert issubclass(SaveFilenameMismatch, SaveFormatError)
    assert issubclass(MalformedHeader, SaveFormatError)
