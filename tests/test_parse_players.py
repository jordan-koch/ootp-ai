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
    PLAYER_DIGEST_LEN,
    make_player_head,
    make_players_file,
    player_age_on,
)
from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.db import connect_truth
from ootp_ai.parser.errors import MalformedHeader
from ootp_ai.parser.players import (
    # Private on purpose, imported on purpose: the independent-framing test below has to
    # re-derive candidates with the walk's own validity rule but WITHOUT its sequencing.
    # Re-implementing the rule here would test a copy of it rather than what ships.
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
