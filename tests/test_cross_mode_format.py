"""Challenge Mode must not change the byte format — proven, not assumed.

Every row-for-row validation this project can perform runs on the **standard-mode**
save, because Challenge Mode has no export (ADR 0003, `docs/data-access.md` §6). So
without this module, *"the format does not change with mode"* stays an untested
assumption sitting underneath the entire pipeline, and the failure it guards against
is the one this project cannot afford: **a parser that works on the save we develop
against and breaks on the save we manage.**

The two test saves are a clean matched pair — both at sim date 2024-03-18, differing
essentially in mode — which is what makes the comparison worth anything.

Measured 2026-08-16, and re-asserted here so a game patch cannot quietly change it:
the only file-set difference is `challenge.dat`, nothing is *absent* from a Challenge
save, and the managed league's file set is identical to the Challenge probe's.

This module grows: Phase 5a adds `teams.dat`, Phase 5b `world.dat`, Phase 6
`players.dat`, Phase 7 `names.dat`, each asserting the same walker yields the same record
shape on both. Those four have record-level sections below. `saved_games.dat` and
`human_managers.dat` are walked by this slice and are covered only by the file-set and
header assertions at the top — stated so the list above is not read as complete.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ootp_ai.config import Settings, load_settings
from ootp_ai.parser.header import read_header
from ootp_ai.parser.names import NAMES_FILE, NamesFile, read_names
from ootp_ai.parser.players import PLAYERS_FILE, PlayersFile, read_players
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.parser.teams import TEAMS_FILE, TeamsFile, read_teams
from ootp_ai.parser.world import WORLD_FILE, WorldFile, read_world
from ootp_ai.saves import is_challenge_mode, is_record_file

pytestmark = pytest.mark.gamedata

# The stable prefix ONLY. Byte 75 begins the league sim date, which differs
# legitimately between saves (2024-03-07 managed, 2024-03-18 both probes), so
# comparing 79 bytes asserts that three different leagues share a date and fails on
# correct data. Measured: the first 75 bytes are identical across all three saves for
# all 16 shared record files.
STABLE_PREFIX_BYTES = 75


def _settings() -> Settings:
    settings = load_settings()
    if settings.truth_save is None or settings.probe_save is None:
        pytest.skip("OOTP_TRUTH_LEAGUE / OOTP_PROBE_LEAGUE unset — no matched pair to compare")
    return settings


def _dat_names(save: Path) -> set[str]:
    return {p.name for p in save.glob("*.dat")}


def test_mode_changes_the_file_set_by_exactly_challenge_dat() -> None:
    settings = _settings()
    assert settings.probe_save is not None and settings.truth_save is not None
    challenge = _dat_names(settings.probe_save.path)
    standard = _dat_names(settings.truth_save.path)

    assert challenge - standard == {"challenge.dat"}
    assert standard - challenge == set(), (
        "a file present in the standard save is MISSING from the Challenge save — "
        "the parser would be developed against data production does not have"
    )


def test_the_managed_league_has_the_same_file_set_as_the_challenge_probe() -> None:
    """Why the probe is a structural twin of production and the right dev target."""
    settings = _settings()
    assert settings.probe_save is not None
    assert _dat_names(settings.managed.path) == _dat_names(settings.probe_save.path)


def test_every_shared_dat_has_a_byte_identical_header_across_all_three_saves() -> None:
    settings = _settings()
    assert settings.probe_save is not None and settings.truth_save is not None
    saves = [settings.managed.path, settings.probe_save.path, settings.truth_save.path]

    shared = set.intersection(*(_dat_names(s) for s in saves))
    assert shared, "no shared .dat files — the comparison would be vacuous"

    for name in sorted(shared):
        if not is_record_file(saves[0] / name):
            continue
        heads = [(s / name).read_bytes()[:STABLE_PREFIX_BYTES] for s in saves]
        assert heads[0] == heads[1] == heads[2], (
            f"{name}: header differs across saves — mode or league may change the "
            "format, and the whole cross-mode assumption is unsafe"
        )


def test_every_shared_dat_parses_with_the_same_reader_in_both_modes() -> None:
    """Byte-identical headers are necessary but not sufficient — parse them."""
    settings = _settings()
    assert settings.probe_save is not None and settings.truth_save is not None

    for save in (settings.probe_save.path, settings.truth_save.path, settings.managed.path):
        for path in sorted(save.glob("*.dat")):
            # The glob also catches a text log and a ZIP; only record files carry
            # the OOTP header, and challenge.dat is a 241-byte integrity blob.
            if not is_record_file(path):
                continue
            header = read_header(path.read_bytes()[:512], path.name)
            assert header.version == 25
            assert header.filename == path.name


def test_mode_detection_agrees_with_the_file_set() -> None:
    settings = _settings()
    assert settings.probe_save is not None and settings.truth_save is not None
    assert is_challenge_mode(settings.managed.path)
    assert is_challenge_mode(settings.probe_save.path)
    assert not is_challenge_mode(settings.truth_save.path)


# ── record level: teams.dat, Phase 5 ─────────────────────────────────────────


def _matched_pair(settings: Settings) -> tuple[TeamsFile, TeamsFile]:
    """The Challenge and Standard probes' team files.

    A matched pair in the strong sense: same universe, same sim date, differing in mode
    and in which club is managed. Everything else about them should be identical, which
    is what makes a difference here meaningful rather than merely expected.
    """
    assert settings.probe_save is not None and settings.truth_save is not None
    return (
        read_teams((settings.probe_save.path / TEAMS_FILE).read_bytes()),
        read_teams((settings.truth_save.path / TEAMS_FILE).read_bytes()),
    )


def test_the_same_walker_reads_teams_dat_in_both_modes() -> None:
    """The first record-level evidence for the assumption the whole project rests on.

    Header equality was necessary but weak — it says two files start the same way, not
    that their records do. This walks 259 variable-length records in each and requires
    the walk to succeed identically, which is the claim that actually matters.
    """
    challenge, standard = _matched_pair(_settings())

    assert len(challenge.teams) == len(standard.teams), (
        f"Challenge mode yields {len(challenge.teams)} teams and Standard "
        f"{len(standard.teams)} — mode changes the record count, and every field "
        "mapping validated against the export is therefore validated against a "
        "different format than the league we manage"
    )
    # Not an equality: the two files differ by 49 bytes (their league names differ in
    # length), so identical residuals are not required. What must hold is that the
    # walker reaches the *same tier* on both — accounting for one file exactly while
    # leaving bytes in the other would mean the record shape is mode-dependent.
    assert (challenge.residual_bytes == 0) == (standard.residual_bytes == 0), (
        f"the walk leaves {challenge.residual_bytes} bytes in Challenge mode and "
        f"{standard.residual_bytes} in Standard — one of them is not fully accounted "
        "for, so the record widths differ by mode"
    )
    assert str(challenge.sim_date) == str(standard.sim_date) == "2024-03-18"


def test_the_two_modes_differ_only_in_content_not_in_shape() -> None:
    """Same clubs, same ids, same hierarchy — a different manager, and nothing else.

    The human flag is the one field that *should* differ (Boston manages the Challenge
    save, the Cubs the Standard one). Asserting that it differs while everything else
    matches is what separates "the format is identical" from "the files are identical".
    """
    challenge, standard = _matched_pair(_settings())

    def shape(parsed: TeamsFile) -> list[tuple[int, str, str, int, int, int, int, int]]:
        return sorted(
            (
                team.team_id,
                team.abbr,
                team.nickname,
                team.level,
                team.league_id,
                team.sub_league_id,
                team.park_id,
                team.parent_team_id,
            )
            for team in parsed.teams
        )

    assert shape(challenge) == shape(standard)

    managed = [
        {team.team_id for team in parsed.teams if team.human_team}
        for parsed in (challenge, standard)
    ]
    assert managed[0] != managed[1], (
        f"both probes flag the same club {managed[0]} as human; they were created to be "
        "managed by different clubs, so an identical flag means it is not being read"
    )


# ── record level: players.dat, Phase 6 ───────────────────────────────────────


def _matched_players(settings: Settings) -> tuple[PlayersFile, PlayersFile]:
    assert settings.probe_save is not None and settings.truth_save is not None
    return (
        read_players((settings.probe_save.path / PLAYERS_FILE).read_bytes()),
        read_players((settings.truth_save.path / PLAYERS_FILE).read_bytes()),
    )


def test_the_same_walker_reads_players_dat_in_both_modes() -> None:
    """The largest file in the save, walked identically in both modes.

    This matters more here than for `teams.dat`. Every field mapping in `players.py` was
    scored against the export, and **only the Standard save has one**. If the record shape
    were mode-dependent, all of that validation would apply to a format the managed league
    does not use — and Challenge Mode is the mode every real decision is made in.
    """
    challenge, standard = _matched_players(_settings())

    assert len(challenge.players) == len(standard.players), (
        f"Challenge mode yields {len(challenge.players)} player records and Standard "
        f"{len(standard.players)} — mode changes the record count, so the export-backed "
        "field mappings are not validated against the format we actually manage"
    )
    assert [p.player_id for p in challenge.players] == [p.player_id for p in standard.players], (
        "the two modes frame a different set of player ids"
    )
    assert str(challenge.sim_date) == str(standard.sim_date) == "2024-03-18"


#: Fields that cannot legitimately differ between two saves of the same universe at the
#: same sim date. A birth city or a nationality is not a roster decision. `measured`
#: 2026-08-17: all agree on every one of the 18,077 shared records. Phase 7 split the
#: opaque `name_indices` pair into the two named slots, so the count is now eight.
IMMUTABLE_PLAYER_FIELDS = (
    "first_name_index",
    "last_name_index",
    "age",
    "nation_id",
    "city_of_birth_id",
    "weight",
    "height",
    "experience",
)

#: The only birth-date disagreement between the two saves, `measured` on 6 of 18,077
#: records: one stores 29 February where the other stores the 28th **of the same leap
#: year** — seen in 1996, 2000 and 2004. Why is `unconfirmed`; a leap-day normalisation
#: somewhere in the engine is the obvious guess and nothing here depends on it.
#:
#: Pinned as a *shape* rather than a tolerance, so any other kind of birth-date
#: difference — which is what a mis-read width would produce — fails the test. An earlier
#: version pinned the literal 1996 pair and went red on 2000, which is the check working.
LEAP_DAY_DAYS = frozenset({28, 29})
LEAP_DAY_MONTH = 2


def test_the_player_head_decodes_identically_in_both_modes() -> None:
    """The head fields that cannot differ, checked on every shared record.

    This is the assertion that rules out a mode-dependent record width. If the head's
    widths differed by mode, essentially every record would disagree in every field — so
    all of `IMMUTABLE_PLAYER_FIELDS` agreeing across 18,077 records is strong evidence
    the format is one format, which is the claim the export-backed validation depends on.
    """
    challenge, standard = _matched_players(_settings())
    by_id = {p.player_id: p for p in standard.players}

    disagreements: list[str] = []
    for player in challenge.players:
        other = by_id[player.player_id]
        disagreements.extend(
            f"player {player.player_id}: {field} is "
            f"{getattr(player, field)!r} in Challenge and {getattr(other, field)!r} in Standard"
            for field in IMMUTABLE_PLAYER_FIELDS
            if getattr(player, field) != getattr(other, field)
        )

    assert not disagreements, (
        "fields that cannot differ between two saves of the same universe do differ, "
        "which means the record widths are mode-dependent:\n" + "\n".join(disagreements[:20])
    )


def test_the_two_saves_differ_only_where_content_legitimately_can() -> None:
    """The complement, and it keeps the test above from being vacuous.

    Two fields do disagree, and both are explicable. `uniform_number` is a roster
    decision and these saves manage different clubs. `date_of_birth` disagrees on
    exactly the leap day. Naming both means a *new* kind of difference — the kind a
    width bug would produce — fails here instead of being absorbed as "content".
    """
    challenge, standard = _matched_players(_settings())
    by_id = {p.player_id: p for p in standard.players}

    def is_leap_day_quirk(left: SaveDate, right: SaveDate) -> bool:
        return (
            left.year == right.year
            and left.month == right.month == LEAP_DAY_MONTH
            and {left.day, right.day} == LEAP_DAY_DAYS
        )

    odd = [
        f"player {p.player_id}: {p.date_of_birth} vs {by_id[p.player_id].date_of_birth}"
        for p in challenge.players
        if str(p.date_of_birth) != str(by_id[p.player_id].date_of_birth)
        and not is_leap_day_quirk(p.date_of_birth, by_id[p.player_id].date_of_birth)
    ]
    assert not odd, (
        "birth dates differ in a way the leap-day quirk does not explain, which is what "
        "a mis-read field width looks like:\n" + "\n".join(odd[:10])
    )

    uniform_diffs = sum(
        1 for p in challenge.players if p.uniform_number != by_id[p.player_id].uniform_number
    )
    assert uniform_diffs < len(challenge.players) // 100, (
        f"{uniform_diffs} of {len(challenge.players)} uniform numbers differ. A handful "
        "is two clubs assigning numbers differently; this many is a misread field."
    )


def test_neither_mode_declares_a_player_record_count() -> None:
    """The `0xFFFFFFFF` sentinel is a property of the format, not of one save."""
    for parsed in _matched_players(_settings()):
        assert parsed.declared_record_count is None


# ── record level: world.dat, Phase 5b ────────────────────────────────────────


def _matched_worlds(settings: Settings) -> tuple[WorldFile, WorldFile]:
    assert settings.probe_save is not None and settings.truth_save is not None
    return (
        read_world((settings.probe_save.path / WORLD_FILE).read_bytes()),
        read_world((settings.truth_save.path / WORLD_FILE).read_bytes()),
    )


def test_the_same_landmark_finds_the_same_regions_in_both_modes() -> None:
    """Entry by content has a mode-specific failure the header check cannot see.

    `teams.dat` is walked from the top, so a cross-mode difference would have to be a
    difference in record widths. `world.dat` is *entered by searching for a string*, and
    the thing that could quietly differ between modes is whether the anchor is still
    unique — a Challenge save carries `challenge.dat` and could in principle carry
    different world content too. Then the walk enters somewhere else, finds a
    plausible-looking count, and returns a different world with nothing raised.

    So both probes are walked and their regions compared as structure: same regions, same
    order, same declared counts.
    """
    challenge, standard = _matched_worlds(_settings())

    def structure(parsed: WorldFile) -> list[tuple[str, int, int]]:
        return [(r.name, r.declared_count, r.parsed_count) for r in parsed.regions]

    assert structure(challenge) == structure(standard), (
        f"the walk found {structure(challenge)} in Challenge mode and "
        f"{structure(standard)} in Standard — the landmark is resolving differently by "
        "mode, so every division and every calendar row below is from a different place "
        "in the file than the one validated against the export"
    )
    assert str(challenge.sim_date) == str(standard.sim_date) == "2024-03-18"


def test_world_dat_is_identical_in_both_modes_down_to_the_row() -> None:
    """A stronger claim than the `teams.dat` one, and deliberately so.

    `teams.dat` legitimately differs between the two probes: they are managed by different
    clubs, so the human flag *must* differ, and the cross-mode test there asserts
    everything-but-that. `world.dat` holds no per-manager state at all — leagues,
    divisions, a calendar — so there is no field with a licence to differ, and equality is
    the honest assertion rather than a lucky one.

    That makes this the cleanest cross-mode evidence in the suite: two files written by
    the same engine in two different modes, parsed by one walker, yielding identical rows.
    """
    challenge, standard = _matched_worlds(_settings())

    assert challenge.divisions == standard.divisions, (
        "division membership differs between the two modes; they are the same universe "
        "at the same sim date, so a difference here is the parser, not the game"
    )
    assert challenge.calendar == standard.calendar, (
        "the league calendars differ between the two modes. Measured 2026-08-16, the two "
        "probes' calendar arrays are byte-identical to each other — so this is a walk "
        "that entered at a different place, not a game that scheduled differently."
    )
    # Byte-identity holds between the two PROBES and nowhere else. `OOTP-AI.lg` shares the
    # same 3,058 events and differs on 233 `deleted` flags, so the equality above is a
    # cross-MODE claim, not a cross-save one. `tests/test_parse_world.py` holds the
    # managed league to the weaker statement that is actually true of it.


# ── record level: names.dat, Phase 7 ─────────────────────────────────────────


def _matched_names(settings: Settings) -> tuple[NamesFile, NamesFile]:
    assert settings.probe_save is not None and settings.truth_save is not None
    return (
        read_names((settings.probe_save.path / NAMES_FILE).read_bytes()),
        read_names((settings.truth_save.path / NAMES_FILE).read_bytes()),
    )


def test_the_same_walker_reads_names_dat_in_both_modes() -> None:
    """The completing file, and the one where the cross-mode claim is cheapest to make.

    `names.dat` is walked at the **strict** tier, so "the same walker succeeds on both"
    is a much stronger statement here than for `teams.dat` or `players.dat`: the walk
    consumes every byte of each file. A single mode-dependent field width anywhere in
    264,095 records would desynchronise the next length prefix and the walk could not
    reach the end at all.
    """
    challenge, standard = _matched_names(_settings())

    assert challenge.residual_bytes == 0
    assert standard.residual_bytes == 0
    assert len(challenge.names) == len(standard.names)
    assert challenge.declared_record_count == standard.declared_record_count
    assert len(challenge.names) == challenge.declared_record_count
    assert str(challenge.sim_date) == str(standard.sim_date) == "2024-03-18"


def test_the_name_table_is_identical_in_both_modes_down_to_the_string() -> None:
    """Equality, not merely equivalence — and the evidence is stronger than world.dat's.

    A name table holds no per-manager and no per-league state, so as with `world.dat`
    there is no field with a licence to differ. What makes this the strongest cross-mode
    assertion in the suite is that it also holds against the **managed** save: measured
    2026-08-18, all three files' record bodies are byte-identical and only their headers
    differ, at the sim date and the wall-clock write time.

    That refutes the plan's expectation that the table was per-save populated, and the
    per-save *structure* in `names.py` is kept anyway for the reason recorded there —
    shipped-data identity is not an invariant.
    """
    challenge, standard = _matched_names(_settings())

    assert challenge.names == standard.names, (
        "the two modes decode different name tables from the same universe at the same "
        "sim date, so either the walk entered at a different place or the record shape "
        "is mode-dependent"
    )


def test_the_managed_league_resolves_the_same_names_as_the_probes() -> None:
    """The claim that actually matters: production shares the probes' table.

    **This is a cross-SAVE assertion in the cross-MODE module, and it is here on
    purpose** — the same deliberate exception the `world.dat` section closes with, where
    byte-identity between the two probes is noted as *not* extending to the managed
    league. Everything else here compares two saves that differ only in mode; this one
    compares two different universes, and it earns its place because every exact
    validation of the names join runs on the standard-mode probe. If the managed
    league's table differed, all of that would validate names the Red Sox front office
    never sees.

    Compared as decoded records rather than as digests: the three files' **digests do
    differ**, entirely in the header — the sim date and the wall-clock write time.
    """
    settings = _settings()
    assert settings.truth_save is not None
    managed_bytes = (settings.managed.path / NAMES_FILE).read_bytes()
    standard_bytes = (settings.truth_save.path / NAMES_FILE).read_bytes()

    # The control that keeps this a cross-save claim. Deliberately NOT a sim-date
    # comparison: the managed league sims forward and would eventually reach the probes'
    # 2024-03-18, turning a correct parse red for a calendar reason. Distinct bytes is
    # the property that actually means "two different files", and it does not rot.
    assert managed_bytes != standard_bytes, (
        "the managed save and the standard probe hold byte-identical names.dat files, so "
        "this is not comparing two saves and proves nothing about production"
    )
    assert read_names(managed_bytes).names == read_names(standard_bytes).names, (
        "the managed league's name table differs from the export-verified probe's, so "
        "the names join is validated against a table the league we manage does not use"
    )
