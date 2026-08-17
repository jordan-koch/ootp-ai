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

This module grows: Phase 5 adds `teams.dat`, Phase 6 `players.dat`, Phase 7
`names.dat`, each asserting the same walker yields the same record shape on both.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ootp_ai.config import Settings, load_settings
from ootp_ai.parser.header import read_header
from ootp_ai.parser.teams import TEAMS_FILE, TeamsFile, read_teams
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
