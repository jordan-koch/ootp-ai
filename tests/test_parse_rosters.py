"""The roster-membership grain — offline against synthetic bytes, then the real saves.

**The offline half is the half CI runs**, and for this grain it earns its place twice
over: the solve is where every wrong roster would be born, and the reconciliation is the
check that makes a wrong roster impossible to emit silently. Both are pinned here against
buffers whose contents the fixture controls.

The gamedata half carries Phase 6b's acceptance criteria: the full-oracle exactness of
the grain on the standard save, the three league invariants the `list_id` settlement left
behind (26 exactly, 40 never exceeded, list 1 is 1:1), and Boston's exact counts from the
operator's `OOTP-AI.lg` screenshot — 33 / 26 / 30 / 7 over 96 rows and 34 distinct
players, asserted against the save they are true of and no other.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from fixtures.synthetic import (
    PLAYER_STATUS_ACTIVE_BIT,
    PLAYER_STATUS_INJURED_BIT,
    PLAYER_STATUS_SECONDARY_BIT,
    make_player_head,
    make_players_file,
    make_teams_spans_file,
    make_u32_run,
)
from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.db import connect_truth
from ootp_ai.parser.players import PLAYERS_FILE
from ootp_ai.parser.rosters import (
    LIST_ACTIVE,
    LIST_ASSIGNMENT,
    LIST_INJURED,
    LIST_SECONDARY,
    AmbiguousRosterMembership,
    RosterLayoutMismatch,
    RostersFile,
    read_rosters,
)
from ootp_ai.parser.teams import (
    TEAMS_FILE,
    TeamRecordLayout,
    read_team_record_spans,
    read_teams,
)

SIM = (18, 3, 2024)

#: `measured` 2026-08-18 against `ootp_truth_real.team_roster`: the whole table, and the
#: per-list split the plan recorded. Pinned exactly — a drift in any direction is a
#: different league, not noise.
TRUTH_ROSTER_ROWS = 15_672
TRUTH_ROSTER_PLAYERS = 7_370
TRUTH_ROWS_BY_LIST = {1: 7_370, 2: 7_037, 3: 935, 4: 330}

#: The assigned-but-listless population the export marks with a negative `league_id` —
#: the same 176 `test_parse_players.py` pins from the assignment side.
TRUTH_UNROSTERED = 176

#: Boston (`team_id` 4) in `OOTP-AI.lg` at 2024-03-07, read off the operator's
#: Organization → Overview screenshot and reconciled by arithmetic
#: (`IMPLEMENTATION_PLAN.md` Phase 6). True for exactly that club in exactly that save
#: on exactly that date — the near-twin challenge save agrees today and must not be
#: asserted from this table.
BOSTON = 4
BOSTON_MANAGED_BY_LIST = {1: 33, 2: 26, 3: 30, 4: 7}
BOSTON_MANAGED_ROWS = 96
BOSTON_MANAGED_PLAYERS = 34

#: A league rule, not a snapshot fact: every MLB club carries exactly this many active
#: players, and the 40-man never exceeds its name.
ACTIVE_ROSTER_SIZE = 26
SECONDARY_ROSTER_CAP = 40
MLB_CLUBS = 30


# ── offline: builders for a two-club organisation ────────────────────────────
#
# Club 1 is the organisation's top club, club 2 its affiliate. The five players cover
# every membership state the solve distinguishes: active, injured, a 40-man prospect
# assigned to the affiliate (the cross-team fan-out), rostered-but-inactive (the state
# the managed save has 154 of and the test saves have none of), and assigned-but-
# unrostered (the negative-`league_id` population).

_ACTIVE = 1 << PLAYER_STATUS_ACTIVE_BIT
_SECONDARY = 1 << PLAYER_STATUS_SECONDARY_BIT
_INJURED = 1 << PLAYER_STATUS_INJURED_BIT

_FILLER = b"\xee" * 8


def _players_buffer() -> bytes:
    heads = (
        # Active at the top club: rows {1, 2}, twice in club 1's array.
        make_player_head(
            player_id=100,
            sim_date=SIM,
            assignments={"team_id": 1, "organization_id": 1, "league_id": 203},
            tail=True,
            status=_ACTIVE,
        ),
        # Injured at the top club: rows {1, 4}.
        make_player_head(
            player_id=101,
            sim_date=SIM,
            assignments={"team_id": 1, "organization_id": 1, "league_id": 203},
            tail=True,
            status=_INJURED,
        ),
        # The cross-team fan-out: assigned and active at the affiliate, on the top
        # club's 40-man. Rows {1, 2} at club 2 and {3} at club 1 — one player, two
        # clubs, three rows.
        make_player_head(
            player_id=102,
            sim_date=SIM,
            assignments={"team_id": 2, "organization_id": 1, "league_id": 204},
            tail=True,
            status=_SECONDARY,
        ),
        # Rostered but inactive: multiplicity 1, no bits — rows {1} and nothing else.
        make_player_head(
            player_id=103,
            sim_date=SIM,
            assignments={"team_id": 2, "organization_id": 1, "league_id": 204},
            tail=True,
            status=0,
        ),
        # Assigned but unrostered: the measured marker (a non-zero
        # `last_organization_id` naming his own organisation), no rows at all.
        make_player_head(
            player_id=104,
            sim_date=SIM,
            assignments={
                "team_id": 1,
                "organization_id": 1,
                "league_id": 203,
                "last_organization_id": 1,
                "last_league_id": 234,
            },
            tail=True,
            status=0,
        ),
    )
    return make_players_file(heads, sim_date=SIM)


def _teams_buffer(
    club_one_array: tuple[int, ...] = (100, 100, 101, 101, 102, 104),
    sim_date: tuple[int, int, int] = SIM,
) -> bytes:
    return make_teams_spans_file(
        (
            (1, _FILLER + make_u32_run(club_one_array) + _FILLER),
            (2, _FILLER + make_u32_run((102, 102, 103)) + _FILLER),
        ),
        sim_date=sim_date,
    )


def test_the_five_membership_states_resolve_to_the_operator_settled_lists() -> None:
    parsed = read_rosters(_teams_buffer(), _players_buffer())
    rows = {(m.team_id, m.player_id, m.list_id) for m in parsed.memberships}
    assert rows == {
        (1, 100, LIST_ASSIGNMENT),
        (1, 100, LIST_ACTIVE),
        (1, 101, LIST_ASSIGNMENT),
        (1, 101, LIST_INJURED),
        (2, 102, LIST_ASSIGNMENT),
        (2, 102, LIST_ACTIVE),
        (1, 102, LIST_SECONDARY),
        (2, 103, LIST_ASSIGNMENT),
    }
    assert parsed.unrostered == ((1, 104),)


def test_the_result_is_sorted_and_deterministic() -> None:
    """AC10's parser half for this grain: same bytes, byte-identical result."""
    teams, players = _teams_buffer(), _players_buffer()
    first = read_rosters(teams, players)
    assert first == read_rosters(teams, players)
    assert list(first.memberships) == sorted(
        first.memberships, key=lambda row: (row.team_id, row.list_id, row.player_id)
    )


def test_an_array_that_disagrees_with_the_status_bits_is_refused() -> None:
    """The reconciliation is the product, not a nicety — a wrong count must raise.

    An extra occurrence of player 100 makes his multiplicity solve to two active
    entries, which no roster means. Emitting either file's reading alone would be a
    guess, and the refusal is what makes every wrong call visible.
    """
    with pytest.raises(AmbiguousRosterMembership):
        read_rosters(
            _teams_buffer(club_one_array=(100, 100, 100, 101, 101, 102, 104)), _players_buffer()
        )


def test_two_different_snapshots_are_refused() -> None:
    """A roster built across two sim dates would mix two states of the league."""
    with pytest.raises(RosterLayoutMismatch, match="different snapshots"):
        read_rosters(_teams_buffer(sim_date=(7, 3, 2024)), _players_buffer())


def test_an_assigned_player_with_an_unreadable_tail_is_refused() -> None:
    """The legacy tail shape yields `None` in `read_players`; here it must refuse.

    `read_players` can honestly report an unreadable tail as `None` — nothing downstream
    of it invents facts from the gap. This walk cannot: the status byte sits past the
    tail, and a membership emitted without reading it would be a membership invented.
    """
    heads = (
        make_player_head(
            player_id=100,
            sim_date=SIM,
            assignments={"team_id": 1, "organization_id": 1, "league_id": 203},
        ),
    )
    with pytest.raises(RosterLayoutMismatch, match="identity tail"):
        read_rosters(_teams_buffer(club_one_array=(100,)), make_players_file(heads, sim_date=SIM))


# ── offline: the refusal lattice, pinned branch by branch ────────────────────
#
# The module's thesis is refuse-loudly, and a refusal that only gitignored scratch
# probes ever exercised is one a refactor can weaken with the suite staying green. Each
# test below is the committed form of a probe the acceptance panel ran by hand.


def _one_player_buffers(
    *,
    array: tuple[int, ...],
    assignments: dict[str, int],
    status: int,
) -> tuple[bytes, bytes]:
    """A single-club, single-player scenario for exercising one solve branch."""
    heads = (
        make_player_head(
            player_id=104, sim_date=SIM, assignments=assignments, tail=True, status=status
        ),
    )
    teams = make_teams_spans_file(((1, _FILLER + make_u32_run(array) + _FILLER),), sim_date=SIM)
    return teams, make_players_file(heads, sim_date=SIM)


@pytest.mark.parametrize(
    ("last_org", "last_league"),
    [
        (2, 234),  # a FOREIGN former organisation — the traded-player shape
        (1, 203),  # own organisation but the wrong league
    ],
)
def test_a_blurred_unrostered_marker_is_refused_not_classified(
    last_org: int, last_league: int
) -> None:
    """The panel's traded-player probe, committed.

    A rostered-but-inactive player traded across organisations carries a non-zero
    `last_organization_id` that is NOT his own organisation. Classifying him unrostered
    on non-zero-ness alone silently drops his list-1 row — and the multiset
    reconciliation provably cannot catch it, because both readings contribute exactly
    one array entry. The full signature must match or the walk must refuse.
    """
    teams, players = _one_player_buffers(
        array=(104,),
        assignments={
            "team_id": 1,
            "organization_id": 1,
            "league_id": 203,
            "last_organization_id": last_org,
            "last_league_id": last_league,
        },
        status=0,
    )
    with pytest.raises(AmbiguousRosterMembership, match="signature"):
        read_rosters(teams, players)


def test_the_marker_alongside_status_bits_is_refused() -> None:
    """A combination no save on disk exhibits must raise, not pick a reading."""
    teams, players = _one_player_buffers(
        array=(104,),
        assignments={
            "team_id": 1,
            "organization_id": 1,
            "league_id": 203,
            "last_organization_id": 1,
            "last_league_id": 234,
        },
        status=_INJURED,
    )
    with pytest.raises(AmbiguousRosterMembership, match="alongside"):
        read_rosters(teams, players)


def test_an_active_bit_that_disagrees_with_the_multiplicity_is_refused() -> None:
    """The redundant storage is redundant on purpose — a disagreement means one of the
    two stored facts is no longer what it was measured to be."""
    teams, players = _one_player_buffers(
        array=(104,),  # multiplicity 1 — but the status byte claims an active entry
        assignments={"team_id": 1, "organization_id": 1, "league_id": 203},
        status=_ACTIVE,
    )
    with pytest.raises(AmbiguousRosterMembership, match="redundant storage"):
        read_rosters(teams, players)


def test_a_missing_cross_club_entry_fails_the_reconciliation() -> None:
    """The final per-club multiset check is the product, and this pins it.

    Player 102 is on club 1's 40-man, so club 1's array owes him an entry. An array
    without it means the two files no longer corroborate each other — the walk must
    refuse rather than emit whichever reading it likes better.
    """
    with pytest.raises(AmbiguousRosterMembership, match="disagree"):
        read_rosters(_teams_buffer(club_one_array=(100, 100, 101, 101, 104)), _players_buffer())


def test_a_foreign_value_splitting_the_array_is_refused() -> None:
    """A garbage u32 inside the membership run breaks it into two runs, neither of
    which holds every assigned player — zero candidates, loud refusal."""
    split = (100, 100, 101, 999_999, 101, 102, 104)
    with pytest.raises(RosterLayoutMismatch, match="candidate membership arrays"):
        read_rosters(_teams_buffer(club_one_array=split), _players_buffer())


def test_an_assigned_club_with_no_team_record_is_refused() -> None:
    """Players naming a club the teams file does not hold means mixed files."""
    heads = (
        make_player_head(
            player_id=100,
            sim_date=SIM,
            assignments={"team_id": 3, "organization_id": 3, "league_id": 204},
            tail=True,
            status=0,
        ),
    )
    with pytest.raises(RosterLayoutMismatch, match="no record for club"):
        read_rosters(_teams_buffer(), make_players_file(heads, sim_date=SIM))


def test_a_span_walk_that_frames_fewer_records_than_declared_refuses() -> None:
    """The fixture's `declared_count` lie-parameter, finally told to someone."""
    lying = make_teams_spans_file(
        ((1, _FILLER + make_u32_run((100,)) + _FILLER),), sim_date=SIM, declared_count=2
    )
    with pytest.raises(TeamRecordLayout, match="framed 1 records"):
        read_team_record_spans(lying)


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


def _rosters(save: SaveRef) -> RostersFile:
    teams_path = save.path / TEAMS_FILE
    players_path = save.path / PLAYERS_FILE
    if not teams_path.is_file() or not players_path.is_file():
        pytest.skip(f"{save.league} is missing {TEAMS_FILE} or {PLAYERS_FILE}")
    return read_rosters(teams_path.read_bytes(), players_path.read_bytes())


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
def test_the_grain_reproduces_the_export_exactly() -> None:
    """Tier B for this grain: every row, no extras, no misses, never a rate."""
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    parsed = _rosters(settings.truth_save)
    got = {(m.team_id, m.player_id, m.list_id) for m in parsed.memberships}

    with _truth_cursor(settings) as cursor:
        cursor.execute("SELECT team_id, player_id, list_id FROM team_roster")
        expected = {(row["team_id"], row["player_id"], row["list_id"]) for row in cursor.fetchall()}

    assert len(expected) == TRUTH_ROSTER_ROWS
    assert len(parsed.memberships) == TRUTH_ROSTER_ROWS, "duplicate rows inside the parse"
    missing = expected - got
    extra = got - expected
    assert not missing and not extra, (
        f"{len(missing)} export rows missing, {len(extra)} rows invented; e.g. "
        f"{sorted(missing)[:3]} / {sorted(extra)[:3]}"
    )
    assert parsed.unrostered != (), "the unrostered population vanished"
    assert len(parsed.unrostered) == TRUTH_UNROSTERED


@_gamedata
def test_the_league_invariants_hold_on_every_save() -> None:
    """The rules the `list_id` settlement left behind, checked where no export exists.

    These are league *rules*, so they must hold on the managed save too — and they are
    the sharpest structural evidence available there: a walk that transposed two list
    values would not land thirty clubs on exactly 26.
    """
    settings = _settings()
    for label, save in _saves(settings):
        parsed = _rosters(save)
        triples = {(m.team_id, m.player_id, m.list_id) for m in parsed.memberships}
        assert len(triples) == len(parsed.memberships), (
            f"{label}: duplicate roster rows — the declared grain is not enforced"
        )
        by_list: dict[int, Counter[int]] = {list_id: Counter() for list_id in TRUTH_ROWS_BY_LIST}
        players_by_list: dict[int, set[int]] = {list_id: set() for list_id in TRUTH_ROWS_BY_LIST}
        for row in parsed.memberships:
            by_list[row.list_id][row.team_id] += 1
            players_by_list[row.list_id].add(row.player_id)

        assignments = by_list[LIST_ASSIGNMENT]
        assert sum(assignments.values()) == len(players_by_list[LIST_ASSIGNMENT]), (
            f"{label}: a player holds two assignment rows — the walk mis-framed a record"
        )

        secondary = by_list[LIST_SECONDARY]
        assert len(secondary) == MLB_CLUBS, (
            f"{label}: {len(secondary)} clubs carry a 40-man roster, expected {MLB_CLUBS}"
        )
        oversized = {club: n for club, n in secondary.items() if n > SECONDARY_ROSTER_CAP}
        assert not oversized, f"{label}: 40-man over its cap at {oversized}"

        wrong_active = {
            club: by_list[LIST_ACTIVE][club]
            for club in secondary
            if by_list[LIST_ACTIVE][club] != ACTIVE_ROSTER_SIZE
        }
        assert not wrong_active, (
            f"{label}: MLB clubs without exactly {ACTIVE_ROSTER_SIZE} active players: "
            f"{wrong_active}"
        )


@_gamedata
def test_boston_matches_the_operator_screenshot_in_the_managed_save() -> None:
    """Phase 6b's headline acceptance: the club we actually manage, counted exactly.

    The expected table is true of `OOTP-AI.lg` at 2024-03-07 and asserted only there.
    The challenge save is a near-twin that happens to agree today; asserting it from
    this table would conflate two universes (`IMPLEMENTATION_PLAN.md` Phase 6).
    """
    settings = _settings()
    parsed = _rosters(settings.managed)

    boston = [m for m in parsed.memberships if m.team_id == BOSTON]
    counts = Counter(m.list_id for m in boston)
    assert dict(counts) == BOSTON_MANAGED_BY_LIST
    assert len(boston) == BOSTON_MANAGED_ROWS
    assert len({m.player_id for m in boston}) == BOSTON_MANAGED_PLAYERS


@_gamedata
def test_parsing_the_same_save_twice_is_identical() -> None:
    """AC10's determinism half, on the save with the least room for luck."""
    settings = _settings()
    save = settings.truth_save or settings.managed
    teams_path = save.path / TEAMS_FILE
    players_path = save.path / PLAYERS_FILE
    if not teams_path.is_file() or not players_path.is_file():
        pytest.skip(f"{save.league} is missing {TEAMS_FILE} or {PLAYERS_FILE}")
    teams_data = teams_path.read_bytes()
    players_data = players_path.read_bytes()
    assert read_rosters(teams_data, players_data) == read_rosters(teams_data, players_data)


@_gamedata
def test_the_span_walk_and_the_decoded_walk_frame_the_same_clubs() -> None:
    """The two frame searches resume differently; this pins that they never diverge.

    `read_team_record_spans` resumes after a candidate id, `read_teams` after a decoded
    head — so a frame pattern inside a head could in principle be seen by one and not
    the other. No save on disk exhibits one; this is the assertion that keeps it true.
    """
    settings = _settings()
    for label, save in _saves(settings):
        teams_path = save.path / TEAMS_FILE
        if not teams_path.is_file():
            pytest.skip(f"{save.league} has no {TEAMS_FILE} on this machine")
        data = teams_path.read_bytes()
        span_ids = [span.team_id for span in read_team_record_spans(data)]
        decoded_ids = [team.team_id for team in read_teams(data).teams]
        assert span_ids == decoded_ids, f"{label}: the two frame searches diverged"


@_gamedata
def test_the_unrostered_players_are_exactly_the_negative_league_id_population() -> None:
    """The two findings corroborate: the export's sign marker and the missing rows are
    one population, so the parse's `unrostered` must equal the export's negative set."""
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured")
    parsed = _rosters(settings.truth_save)

    with _truth_cursor(settings) as cursor:
        cursor.execute("SELECT player_id, team_id FROM players WHERE retired = 0 AND league_id < 0")
        expected = {(row["team_id"], row["player_id"]) for row in cursor.fetchall()}

    assert set(parsed.unrostered) == expected
    assert len(expected) == TRUTH_UNROSTERED
