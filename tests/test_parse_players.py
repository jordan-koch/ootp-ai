"""The `players.dat` walk — offline against synthetic bytes, then against the real saves.

**The offline half is the half CI runs.** `-m gamedata` is deselected there, so if the
framing logic were only exercised against real saves, every push would be testing nothing
about this walker. The synthetic tests below pin the framing rules directly.

The one they exist for above all others is
`test_a_run_whose_age_contradicts_its_birth_date_is_not_a_record`. The first version of
this walker validated a candidate record start on two conditions — an ascending id and a
parseable date — and that was very nearly enough. `measured`: it accepted one impostor
5.2 MB into the standard-mode save, where 26 bytes of padding are followed by `589825`
and a "date" of 2048-04-01. Because every subsequent real id was smaller than 589825,
the walk then returned **2,693 records instead of 18,072** — and every field it did read
decoded perfectly against the export. A short league that looks entirely healthy is the
single worst outcome available here, so the condition that closes it gets a named test.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from fixtures.synthetic import (
    PLAYER_ASSIGNMENT_BITS,
    PLAYER_DIGEST_LEN,
    make_player_head,
    make_players_file,
    player_age_on,
)
from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.db import connect_truth
from ootp_ai.parser.errors import MalformedHeader
from ootp_ai.parser.lookahead import peek_date_parts, peek_u8
from ootp_ai.parser.players import (
    # Private on purpose, imported on purpose: the independent-framing test below has to
    # re-derive candidates with the walk's own validity rule but WITHOUT its sequencing.
    # Re-implementing the rule here would test a copy of it rather than what ships.
    _AGE_LOOKAHEAD,
    _BIRTH_DATE_LOOKAHEAD,
    _PAD_RUN,
    BYTE_ACCOUNTING_TIER,
    NO_DECLARED_COUNT,
    PLAYERS_FILE,
    PlayerRecordLayout,
    PlayersFile,
    _looks_like_record,
    read_players,
)

SIM = (18, 3, 2024)

#: `measured` 2026-08-17 against `ootp_truth_real`. The export's `retired = 0` population
#: is 18,072; the file holds five more, and these are their ids. They are pinned by value
#: rather than counted loosely so that a change in either direction is visible: a walker
#: that started dropping real records and a game patch that started exporting these would
#: otherwise look identical from a count alone.
EXTRA_BEYOND_THE_EXPORT = frozenset({42001, 49008, 50468, 50469, 132324})
TRUTH_ACTIVE_PLAYERS = 18_072
TRUTH_PLAYER_RECORDS = TRUTH_ACTIVE_PLAYERS + len(EXTRA_BEYOND_THE_EXPORT)

#: `measured` 2026-08-18 — the export writes `league_id` negative on exactly this many
#: records while the save stores it positive. Those records are precisely the players
#: carrying a `team_id` with no `list_id = 1` row in `team_roster` (7,546 against 7,370),
#: which is what makes the sign look like an attached-but-not-rostered marker
#: (`inferred`). Pinned as an exact count, never a tolerance.
LEAGUE_ID_NEGATED_BY_THE_EXPORT = 176


# ── offline: the two lookaheads the framing rests on ─────────────────────────
#
# These sit first because everything below depends on them. `_looks_like_record` reads the
# birth date and the age at these offsets to decide whether a candidate position is a
# record at all — so if either is wrong the walk does not return bad fields, it returns the
# wrong NUMBER OF RECORDS, which is how the 2,693-of-18,072 truncation happened during
# development. A gamedata test would catch that too, but only against a save CI never has.


def test_the_head_lookaheads_land_on_the_fields_they_name() -> None:
    """The semantic pin: the derived offsets reach the birth date and age actually written.

    This is what makes the derivation trustworthy rather than merely tidy. Written as sums
    of named field widths (`players.py`), the two offsets can now drift if a width is
    mistyped — so they are checked against a head whose contents the fixture controls,
    rather than against the numbers they used to be.
    """
    birth = (26, 6, 1996)
    head = make_player_head(birth=birth, sim_date=SIM)

    assert peek_date_parts(head, _BIRTH_DATE_LOOKAHEAD) == birth
    assert peek_u8(head, _AGE_LOOKAHEAD) == player_age_on(birth, SIM)


def test_the_derived_lookaheads_still_equal_the_measured_offsets() -> None:
    """The numeric pin: the arithmetic must still come out at the values that were measured.

    Weaker than the test above and faster to read in a failure — a broken addend shows up
    here as a plain number, which is the first thing anyone will want to see.
    """
    assert (_BIRTH_DATE_LOOKAHEAD, _AGE_LOOKAHEAD) == (12, 19)


# ── offline: the framing rules ───────────────────────────────────────────────


def test_a_two_record_file_yields_both_records() -> None:
    data = make_players_file(
        (
            make_player_head(player_id=3, sim_date=SIM),
            make_player_head(player_id=5, sim_date=SIM),
        ),
        sim_date=SIM,
    )
    parsed = read_players(data)
    assert [p.player_id for p in parsed.players] == [3, 5]


def test_the_first_record_is_found_even_though_nothing_pads_it() -> None:
    """It follows the preamble directly. A pad-run search alone would step over it."""
    data = make_players_file((make_player_head(player_id=7, sim_date=SIM),), sim_date=SIM)
    parsed = read_players(data)
    assert [p.player_id for p in parsed.players] == [7]


def test_every_head_field_survives_the_walk() -> None:
    head = make_player_head(
        player_id=1234,
        name_indices=(11, 22),
        birth=(26, 6, 1996),
        sim_date=SIM,
        nation_id=206,
        city_of_birth_id=38609,
        weight=187,
        height=188,
        uniform_number=34,
        experience=5,
    )
    (player,) = read_players(make_players_file((head,), sim_date=SIM)).players
    assert player.player_id == 1234
    assert player.name_indices == (11, 22)
    assert (player.date_of_birth.day, player.date_of_birth.month) == (26, 6)
    assert player.date_of_birth.year == 1996
    assert player.age == player_age_on((26, 6, 1996), SIM)
    assert player.nation_id == 206
    assert player.city_of_birth_id == 38609
    assert player.weight == 187
    assert player.height == 188
    assert player.uniform_number == 34
    assert player.experience == 5


def test_a_run_whose_age_contradicts_its_birth_date_is_not_a_record() -> None:
    """The regression test for the 2,693-instead-of-18,072 truncation.

    The impostor has everything the first two checks asked for: an id that ascends and a
    date that parses. Its age cannot belong to that date, and that is the whole defence.
    """
    impostor = make_player_head(player_id=589_825, birth=(1, 4, 2048), sim_date=SIM, age=64)
    real = make_player_head(player_id=25_757, sim_date=SIM)
    data = make_players_file(
        (make_player_head(player_id=25_755, sim_date=SIM), impostor, real), sim_date=SIM
    )

    framed = [p.player_id for p in read_players(data).players]
    assert 589_825 not in framed, "the impostor was framed as a record"
    assert framed == [25_755, 25_757], (
        "rejecting the impostor must not also cost the real record that follows it"
    )


def test_records_of_different_lengths_all_decode() -> None:
    """The property the fixed-offset ban exists for, exercised **offline**.

    Every other offline test here gives each record the same body, so a fixed-stride
    reimplementation of the walker would pass them all — and the offline half is the only
    half CI runs. Real records span 1,018 to 9,229 bytes. These four span 7 to 4,001, so
    a walker that advanced by a constant lands mid-record on the second one.
    """
    ids = [10, 20, 30, 40]
    data = make_players_file(
        tuple(make_player_head(player_id=i, uniform_number=i, sim_date=SIM) for i in ids),
        sim_date=SIM,
        bodies=(b"\x5a" * 7, b"\x5a" * 913, b"\x5a" * 64, b"\x5a" * 4001),
    )
    parsed = read_players(data)
    assert [p.player_id for p in parsed.players] == ids
    assert [p.uniform_number for p in parsed.players] == ids, (
        "a field after the variable region decoded differently per record, which is "
        "exactly what a constant stride produces"
    )


def test_a_body_full_of_zeros_does_not_swallow_the_next_record() -> None:
    """A zero body merges with the following pad run; the walk must still find the record.

    This is the fixture's own warning made into a test: the default body is non-zero
    precisely so it cannot mask a boundary error, which means the zero case is untested
    unless something asks for it.
    """
    data = make_players_file(
        (
            make_player_head(player_id=11, sim_date=SIM),
            make_player_head(player_id=12, sim_date=SIM),
        ),
        sim_date=SIM,
        bodies=(b"\x00" * 200, b"\xab" * 64),
    )
    assert [p.player_id for p in read_players(data).players] == [11, 12]


def test_an_absent_assignment_field_reads_as_zero_not_as_missing() -> None:
    """Drop-zero elides a falsy value, so absent and zero are the same statement.

    A free agent has no team. That is a fact about the player, not a gap in the file, so
    the walk must not dress it up as `None` — unlike `teams.py`'s droppable string slots,
    where absent and empty really are indistinguishable.
    """
    head = make_player_head(player_id=9, sim_date=SIM)  # no assignments -> mask 0x00
    (player,) = read_players(make_players_file((head,), sim_date=SIM)).players
    assert player.team_id == 0
    assert player.organization_id == 0
    assert player.league_id == 0
    assert player.last_team_id == 0
    assert player.free_agent is False


@pytest.mark.parametrize(
    "assignments",
    [
        {"team_id": 4, "organization_id": 4, "league_id": 203},
        {"organization_id": 16, "league_id": 204},
        {"last_team_id": 172, "last_organization_id": 16, "last_league_id": 234},
        {
            "team_id": 4,
            "last_team_id": 172,
            "organization_id": 4,
            "league_id": 203,
            "last_league_id": 234,
        },
        {
            "team_id": 16,
            "last_team_id": 172,
            "organization_id": 16,
            "last_organization_id": 16,
            "league_id": 203,
            "last_league_id": 234,
        },
    ],
)
def test_every_mask_shape_round_trips(assignments: dict[str, int]) -> None:
    """The five non-empty masks observed in the real saves, built and read back.

    The fixture computes the mask from which values are non-zero — the same rule the
    writer uses — so a round trip here exercises the bit ordering rather than a
    hand-copied byte.
    """
    head = make_player_head(player_id=11, sim_date=SIM, assignments=assignments)
    (player,) = read_players(make_players_file((head,), sim_date=SIM)).players
    for field in PLAYER_ASSIGNMENT_BITS:
        assert getattr(player, field) == assignments.get(field, 0), field


def test_a_negative_assignment_value_survives() -> None:
    """The reads are signed. Unsigned would turn -1 into a plausible-looking id.

    `measured`: the export carries negative values in these columns, so this is not a
    hypothetical — reading them as `u32` yields 4,294,967,295, which looks like data.
    """
    head = make_player_head(
        player_id=13, sim_date=SIM, assignments={"team_id": 4, "league_id": -203}
    )
    (player,) = read_players(make_players_file((head,), sim_date=SIM)).players
    assert player.league_id == -203
    assert player.team_id == 4


def test_the_free_agent_bit_is_read_from_the_second_mask() -> None:
    heads = (
        make_player_head(player_id=20, sim_date=SIM, free_agent=True),
        make_player_head(player_id=21, sim_date=SIM, free_agent=False),
    )
    players = read_players(make_players_file(heads, sim_date=SIM)).players
    assert [p.free_agent for p in players] == [True, False]


def test_the_mask_governs_the_read_even_when_it_disagrees_with_the_values() -> None:
    """The mask is authoritative, not the values — which is what makes framing work.

    Built with a mask claiming only `team_id` while three values are supplied: the walk
    must consume exactly one `u32` and leave the rest to the record body, because a walk
    that inferred the count from anything else would desynchronise the next record.
    """
    head = make_player_head(
        player_id=31,
        sim_date=SIM,
        assignments={"team_id": 7, "organization_id": 7, "league_id": 203},
        assignment_mask=0b000001,
    )
    following = make_player_head(player_id=32, sim_date=SIM)
    parsed = read_players(make_players_file((head, following), sim_date=SIM)).players
    assert [p.player_id for p in parsed] == [31, 32]
    assert parsed[0].team_id == 7
    assert parsed[0].organization_id == 0, "a clear bit must not consume a value"


# ── offline: the identity tail ───────────────────────────────────────────────
#
# The tail is validate-then-consume: `_scan_tail` accepts only the measured shape, and
# anything else must land `None` + a counted `undecoded_tails` while the framing search
# carries on to the next record. Both halves need offline pins — the accept path because
# it is the decode, and the refuse path because a degrade that silently stopped counting
# would let a format change read as a league full of nameless right-handers.


def test_a_valid_identity_tail_round_trips() -> None:
    head = make_player_head(
        player_id=17,
        sim_date=SIM,
        tail=True,
        bats=2,
        throws=2,
        historical_id="deverra01",
        historical_team_id="BOS",
    )
    parsed = read_players(make_players_file((head,), sim_date=SIM))
    (player,) = parsed.players
    assert player.bats == 2
    assert player.throws == 2
    assert player.historical_id == "deverra01"
    assert parsed.undecoded_tails == 0


def test_an_elided_side_reads_as_the_default_and_an_empty_id_as_a_fact() -> None:
    """Drop-DEFAULT: a clear bit means the value IS 1, and `""` means no real identity.

    Neither may surface as `None` — `None` is reserved for a tail the walk refused, and
    conflating it with the fictional majority's empty string would make the degrade
    counter unreadable.
    """
    head = make_player_head(player_id=19, sim_date=SIM, tail=True)
    parsed = read_players(make_players_file((head,), sim_date=SIM))
    (player,) = parsed.players
    assert player.bats == 1
    assert player.throws == 1
    assert player.historical_id == ""
    assert parsed.undecoded_tails == 0


def test_a_legacy_tail_is_refused_counted_and_does_not_break_framing() -> None:
    """The degrade path itself, pinned.

    The default fixture record is the pre-decode legacy shape — its third-mask byte is
    the gap fill, which lacks the sentinel bit. The walk must answer it with `None`
    three times over, count it, and still frame the record that follows.
    """
    data = make_players_file(
        (
            make_player_head(player_id=23, sim_date=SIM),
            make_player_head(player_id=29, sim_date=SIM),
        ),
        sim_date=SIM,
    )
    parsed = read_players(data)
    assert [p.player_id for p in parsed.players] == [23, 29]
    assert all(p.bats is None for p in parsed.players)
    assert all(p.throws is None for p in parsed.players)
    assert all(p.historical_id is None for p in parsed.players)
    assert parsed.undecoded_tails == 2


def test_a_written_side_outside_its_measured_set_degrades_to_none() -> None:
    """A written `bats` of 5 is a format change, not a value — refuse, count, continue.

    The fixture writes the out-of-set byte exactly as asked; sanitising it there would
    make this test impossible to express.
    """
    data = make_players_file(
        (
            make_player_head(player_id=31, sim_date=SIM, tail=True, bats=5),
            make_player_head(player_id=37, sim_date=SIM, tail=True, bats=3),
        ),
        sim_date=SIM,
    )
    parsed = read_players(data)
    assert [p.player_id for p in parsed.players] == [31, 37]
    assert parsed.players[0].bats is None
    assert parsed.players[0].historical_id is None
    assert parsed.players[1].bats == 3, "refusing one tail must not poison the next"
    assert parsed.undecoded_tails == 1


def test_a_non_ascending_id_is_not_a_record() -> None:
    data = make_players_file(
        (
            make_player_head(player_id=500, sim_date=SIM),
            make_player_head(player_id=400, sim_date=SIM),
            make_player_head(player_id=600, sim_date=SIM),
        ),
        sim_date=SIM,
    )
    assert [p.player_id for p in read_players(data).players] == [500, 600]


def test_an_id_whose_low_byte_is_zero_is_still_framed() -> None:
    """Ids are little-endian, so player 256 begins with a zero byte.

    Without the alignment window that byte is swallowed by the padding run and every
    such record is mis-framed. 256, 512 and 65536 all have this shape.
    """
    ids = [256, 512, 65_536]
    data = make_players_file(
        tuple(make_player_head(player_id=i, sim_date=SIM) for i in ids), sim_date=SIM
    )
    assert [p.player_id for p in read_players(data).players] == ids


def test_the_walk_reports_the_sentinel_as_no_declared_count() -> None:
    data = make_players_file((make_player_head(sim_date=SIM),), sim_date=SIM)
    assert read_players(data).declared_record_count is None


def test_a_real_declared_count_would_be_reported_rather_than_swallowed() -> None:
    """If a later OOTP build starts declaring a count, the walk must surface it."""
    data = make_players_file((make_player_head(sim_date=SIM),), sim_date=SIM, declared_count=1)
    assert read_players(data).declared_record_count == 1
    assert NO_DECLARED_COUNT == 0xFFFFFFFF


def test_the_digest_is_carried_off_the_preamble() -> None:
    digest = "F0" * (PLAYER_DIGEST_LEN // 2)
    data = make_players_file((make_player_head(sim_date=SIM),), sim_date=SIM, digest=digest)
    assert read_players(data).content_digest == digest


def test_a_wrong_preamble_constant_refuses() -> None:
    data = make_players_file((make_player_head(sim_date=SIM),), sim_date=SIM, preamble_constant=999)
    with pytest.raises(PlayerRecordLayout, match="preamble constant"):
        read_players(data)


def test_a_short_digest_refuses_rather_than_reading_records_mid_field() -> None:
    data = make_players_file((make_player_head(sim_date=SIM),), sim_date=SIM, digest="AB")
    with pytest.raises(PlayerRecordLayout, match="digest"):
        read_players(data)


def test_bytes_after_the_preamble_that_are_not_a_record_refuse() -> None:
    data = make_players_file((make_player_head(sim_date=SIM),), sim_date=SIM)
    # Corrupt the first record's birth date so nothing valid follows the preamble.
    broken = bytearray(data)
    start = data.index(make_player_head(sim_date=SIM))
    broken[start + 12 : start + 16] = b"\xff\xff\xff\xff"
    with pytest.raises(PlayerRecordLayout, match="not a player record"):
        read_players(bytes(broken))


def test_the_wrong_file_is_refused_by_the_header() -> None:
    with pytest.raises(MalformedHeader):
        read_players(b"not a save at all")


def test_the_tier_is_declared_diagnostic() -> None:
    """A `strict` claim here would be false about ~97% of the file."""
    assert BYTE_ACCOUNTING_TIER == "diagnostic"


# ── the real saves ───────────────────────────────────────────────────────────

_gamedata = pytest.mark.gamedata


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"save configuration unavailable: {exc}")


def _saves(settings: Settings) -> list[tuple[str, SaveRef]]:
    named = [("managed", settings.managed)]
    if settings.truth_save is not None:
        named.append(("standard", settings.truth_save))
    if settings.probe_save is not None:
        named.append(("challenge", settings.probe_save))
    return named


def _walk(save: SaveRef) -> PlayersFile:
    path = save.path / PLAYERS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {PLAYERS_FILE} on this machine")
    return read_players(path.read_bytes())


@contextmanager
def _truth_cursor(settings: Settings) -> Iterator[Any]:
    try:
        connection = connect_truth(settings)
    except ConfigError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"ground-truth export unavailable: {exc}")
    try:
        with connection.cursor() as cursor:
            yield cursor
    finally:
        connection.close()


@_gamedata
def test_the_ascending_unique_invariant_survives_a_refactor() -> None:
    """A **structural** guard, and labelled as one so nobody mistakes it for evidence.

    Ascent and uniqueness cannot fail while `_looks_like_record` enforces
    `previous_id < player_id`: this re-states the implementation rather than testing the
    data. It is kept because it is exactly what goes red if a later refactor loosens that
    predicate — but it says nothing about whether the walk found every record, which is
    the question that matters. The next test answers that one independently.
    """
    settings = _settings()
    for label, save in _saves(settings):
        parsed = _walk(save)
        ids = [p.player_id for p in parsed.players]
        assert ids, f"{label}: the walk returned no players"
        assert len(ids) == len(set(ids)), f"{label}: duplicate player ids"
        assert ids == sorted(ids), f"{label}: ids are not ascending"


@_gamedata
def test_the_walk_frames_every_candidate_the_file_offers() -> None:
    """The test that would actually catch a walk silently dropping records.

    Independent of the walk's own sequencing: it re-scans the whole buffer for every
    position that passes the birth-date and age checks **with the ascending constraint
    removed**, and requires the walk to have framed all of them. A walker that skipped
    records — the 2,693-instead-of-18,072 failure — leaves candidates behind here, and
    this is the only check in the suite that would see it on the managed save, where no
    export exists to compare against.

    The one legitimate difference is record 1, which follows the preamble with no pad run
    in front of it and so is unreachable by a pad-run scan. It is asserted as *exactly*
    that one, not tolerated as slack.
    """
    settings = _settings()
    for label, save in _saves(settings):
        path = save.path / PLAYERS_FILE
        if not path.is_file():
            pytest.skip(f"{save.league} has no {PLAYERS_FILE} on this machine")
        data = path.read_bytes()
        parsed = read_players(data)
        framed = {p.player_id for p in parsed.players}

        independent: set[int] = set()
        position = 0
        while True:
            run = data.find(_PAD_RUN, position)
            if run < 0:
                break
            after = run + len(_PAD_RUN)
            while after < len(data) and data[after] == 0:
                after += 1
            for candidate in range(after - 3, after + 1):
                # previous_id=0 removes the ascending constraint entirely.
                if candidate >= 0 and _looks_like_record(data, candidate, 0, parsed.sim_date):
                    independent.add(int.from_bytes(data[candidate : candidate + 4], "little"))
            position = max(after, run + 1)

        missed = independent - framed
        assert not missed, (
            f"{label}: the walk never framed {len(missed)} record starts that satisfy "
            f"its own validity test, e.g. {sorted(missed)[:5]}. It is returning fewer "
            "players than the file holds."
        )
        assert framed - independent == {parsed.players[0].player_id}, (
            f"{label}: the walk framed records a pad-run scan cannot see, beyond the "
            "expected first record"
        )


@_gamedata
def test_no_save_declares_a_player_record_count() -> None:
    """`players.dat` carries the sentinel where `teams.dat` carries a count."""
    settings = _settings()
    for label, save in _saves(settings):
        assert _walk(save).declared_record_count is None, (
            f"{label} declares a record count — the walk gained an in-file oracle it "
            "has never had, and the byte-accounting rationale needs revisiting"
        )


@_gamedata
def test_age_agrees_with_the_birth_date_in_every_record_of_every_save() -> None:
    """The invariant framing rests on, checked on the saves with no export behind them."""
    settings = _settings()
    for label, save in _saves(settings):
        parsed = _walk(save)
        sim = parsed.sim_date
        wrong = [
            p.player_id
            for p in parsed.players
            if p.age
            != player_age_on(
                (p.date_of_birth.day, p.date_of_birth.month, p.date_of_birth.year),
                (sim.day, sim.month, sim.year),
            )
        ]
        assert not wrong, f"{label}: {len(wrong)} records disagree, first {wrong[:5]}"


@_gamedata
def test_the_walk_holds_every_player_the_export_knows_about() -> None:
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    parsed = _walk(settings.truth_save)
    with _truth_cursor(settings) as cursor:
        cursor.execute("SELECT player_id FROM players WHERE retired = 0")
        expected = {row["player_id"] for row in cursor.fetchall()}

    got = {p.player_id for p in parsed.players}
    assert len(expected) == TRUTH_ACTIVE_PLAYERS
    assert not expected - got, f"{len(expected - got)} export players were never framed"


@_gamedata
def test_the_file_holds_five_records_the_export_does_not() -> None:
    """A strict superset, and the five extras are pinned by id rather than by count.

    They are real records: standard padding, ordinary lengths, coherent biography, and
    the same five ids in both test saves. The plan assumed this file was exactly the
    export's `retired = 0` set; it is not, and any coverage statement saying so is wrong.
    """
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    parsed = _walk(settings.truth_save)
    with _truth_cursor(settings) as cursor:
        cursor.execute("SELECT player_id FROM players")
        every_exported = {row["player_id"] for row in cursor.fetchall()}

    got = {p.player_id for p in parsed.players}
    assert got - every_exported == EXTRA_BEYOND_THE_EXPORT
    assert len(parsed.players) == TRUTH_PLAYER_RECORDS


@_gamedata
def test_every_landed_field_matches_the_export_exactly() -> None:
    """Tier A: exact equality on every compared row, with failures named, never a rate."""
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    parsed = {p.player_id: p for p in _walk(settings.truth_save).players}

    with _truth_cursor(settings) as cursor:
        cursor.execute(
            "SELECT player_id, age, nation_id, city_of_birth_id, weight, height,"
            " uniform_number, experience, DAY(date_of_birth) AS d,"
            " MONTH(date_of_birth) AS m, YEAR(date_of_birth) AS y"
            " FROM players WHERE retired = 0"
        )
        rows = cursor.fetchall()

    mismatches: list[str] = []
    for row in rows:
        player = parsed[row["player_id"]]
        actual = {
            "age": player.age,
            "nation_id": player.nation_id,
            "city_of_birth_id": player.city_of_birth_id,
            "weight": player.weight,
            "height": player.height,
            "uniform_number": player.uniform_number,
            "experience": player.experience,
            "birth_day": player.date_of_birth.day,
            "birth_month": player.date_of_birth.month,
            "birth_year": player.date_of_birth.year,
        }
        wanted = {
            "age": row["age"],
            "nation_id": row["nation_id"],
            "city_of_birth_id": row["city_of_birth_id"],
            "weight": row["weight"],
            "height": row["height"],
            "uniform_number": row["uniform_number"],
            "experience": row["experience"],
            "birth_day": row["d"],
            "birth_month": row["m"],
            "birth_year": row["y"],
        }
        mismatches.extend(
            f"player {row['player_id']}: {field} parsed {actual[field]!r}, export {wanted[field]!r}"
            for field in wanted
            if actual[field] != wanted[field]
        )

    assert len(rows) == TRUTH_ACTIVE_PLAYERS
    assert not mismatches, "parser disagrees with the export:\n" + "\n".join(mismatches[:20])


@_gamedata
def test_the_club_assignment_matches_the_export_on_every_row() -> None:
    """The mask decode, held to the whole answer key rather than a sample.

    `league_id` is compared by magnitude and the sign difference is asserted to be
    **exactly** the 176 records the export writes negative — not tolerated as slack. The
    save stores those positive; imitating the export's rendering would be fitting the
    parser to the artifact instead of the bytes.
    """
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    parsed = {p.player_id: p for p in _walk(settings.truth_save).players}

    with _truth_cursor(settings) as cursor:
        cursor.execute(
            "SELECT player_id, team_id, last_team_id, organization_id,"
            " last_organization_id, league_id, last_league_id, free_agent"
            " FROM players WHERE retired = 0"
        )
        rows = cursor.fetchall()

    exact = (
        "team_id",
        "last_team_id",
        "organization_id",
        "last_organization_id",
        "last_league_id",
    )
    mismatches: list[str] = []
    negated = 0
    for row in rows:
        player = parsed[row["player_id"]]
        mismatches.extend(
            f"player {row['player_id']}: {field} parsed {getattr(player, field)!r}, "
            f"export {row[field]!r}"
            for field in exact
            if getattr(player, field) != (row[field] or 0)
        )
        if player.free_agent != bool(row["free_agent"]):
            mismatches.append(f"player {row['player_id']}: free_agent disagrees")

        wanted_league = row["league_id"] or 0
        if player.league_id != wanted_league:
            if player.league_id == -wanted_league:
                negated += 1
            else:
                mismatches.append(
                    f"player {row['player_id']}: league_id parsed "
                    f"{player.league_id!r}, export {wanted_league!r}"
                )

    assert len(rows) == TRUTH_ACTIVE_PLAYERS
    assert not mismatches, "assignment decode disagrees with the export:\n" + "\n".join(
        mismatches[:20]
    )
    assert negated == LEAGUE_ID_NEGATED_BY_THE_EXPORT, (
        f"{negated} records differ from the export by sign, expected "
        f"{LEAGUE_ID_NEGATED_BY_THE_EXPORT}. That population is not slack — it is the "
        "set the export marks as attached-but-not-rostered, and a change in it is a "
        "change in what the sign means."
    )


@_gamedata
def test_the_identity_tail_matches_the_export_on_every_row() -> None:
    """`bats`, `throws`, `historical_id` — Tier A, all 18,072 rows, failures named."""
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    parsed = {p.player_id: p for p in _walk(settings.truth_save).players}

    with _truth_cursor(settings) as cursor:
        cursor.execute(
            "SELECT player_id, bats, throws, historical_id FROM players WHERE retired = 0"
        )
        rows = cursor.fetchall()

    mismatches: list[str] = []
    for row in rows:
        player = parsed[row["player_id"]]
        wanted = {
            "bats": row["bats"],
            "throws": row["throws"],
            "historical_id": row["historical_id"] or "",
        }
        actual = {
            "bats": player.bats,
            "throws": player.throws,
            "historical_id": player.historical_id,
        }
        mismatches.extend(
            f"player {row['player_id']}: {field} parsed {actual[field]!r}, export {wanted[field]!r}"
            for field in wanted
            if actual[field] != wanted[field]
        )

    assert len(rows) == TRUTH_ACTIVE_PLAYERS
    assert not mismatches, "identity tail disagrees with the export:\n" + "\n".join(mismatches[:20])


@_gamedata
def test_no_save_leaves_an_identity_tail_undecoded() -> None:
    """`undecoded_tails` must be zero everywhere — nonzero is a format change, and this
    is the test that turns it into a red build instead of a league of `None`s.

    The value-range and distinctness clauses are the halves that still bite on
    `OOTP-AI.lg`, where no export exists: a decode that drifted would surface as an
    impossible side value or a duplicated join key long before anyone read a report.
    """
    settings = _settings()
    for label, save in _saves(settings):
        parsed = _walk(save)
        assert parsed.undecoded_tails == 0, (
            f"{label}: {parsed.undecoded_tails} records' identity tails were refused — "
            "the format changed under the walk, and landing this save would average "
            "over records the parser admits it could not read"
        )
        bad_sides = [
            p.player_id for p in parsed.players if p.bats not in (1, 2, 3) or p.throws not in (1, 2)
        ]
        assert not bad_sides, f"{label}: impossible bats/throws on {bad_sides[:5]}"
        nonempty = [p.historical_id for p in parsed.players if p.historical_id]
        assert len(nonempty) == len(set(nonempty)), (
            f"{label}: duplicate historical_id values — the join key is not a key"
        )


@_gamedata
def test_a_free_agent_carries_no_club_and_a_rostered_player_does() -> None:
    """An internal consistency check that needs no export, so it runs on every save.

    This is the half that still works on `OOTP-AI.lg`, where there is nothing to compare
    against — a decode that drifted would show up as free agents holding team ids.
    """
    settings = _settings()
    for label, save in _saves(settings):
        parsed = _walk(save)
        contradictions = [p.player_id for p in parsed.players if p.free_agent and p.team_id != 0]
        assert not contradictions, (
            f"{label}: {len(contradictions)} players are flagged free agents while "
            f"holding a team id, e.g. {contradictions[:5]}"
        )
        assert any(p.team_id for p in parsed.players), (
            f"{label}: not one player carries a team id, so the mask decode is reading "
            "nothing at all"
        )


@_gamedata
def test_parsing_the_same_bytes_twice_gives_an_identical_result() -> None:
    """AC10's parser half. Frozen dataclasses, so equality is structural."""
    settings = _settings()
    save = settings.truth_save or settings.managed
    path = save.path / PLAYERS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {PLAYERS_FILE} on this machine")
    data = path.read_bytes()
    assert read_players(data).players == read_players(data).players


@_gamedata
def test_records_are_not_all_the_same_length() -> None:
    """If they were, the drop-zero warning in the docstring would be a fiction.

    Proven through the walk rather than by measuring the file: the residual plus every
    head cannot account for the file, so the bodies vary. Cheaply: the file is far larger
    than a fixed-width reading of it would be.
    """
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    save = settings.truth_save
    parsed = _walk(save)
    size = (save.path / PLAYERS_FILE).stat().st_size
    mean_body = size / len(parsed.players)
    assert mean_body > 1_000, (
        "a 37-byte head per record would fit in a fraction of this file; the remainder "
        "is the undecoded body the diagnostic tier is honest about"
    )
