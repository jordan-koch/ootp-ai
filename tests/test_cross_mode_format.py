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
