"""A `*.lg` glob is not a list of saves, and mode is a filesystem fact.

`docs/data-access.md:60-63` records, `measured`, that the saved-games root contains a
stray, empty directory literally named `.lg`. It matches the glob and is not a save,
so enumeration confirms contents rather than trusting a name.

`:65-68` records that `challenge.dat` is present at **exactly 241 bytes** in a
Challenge Mode save and absent otherwise — a mode check with no menu involved, which
matters because ADR 0003's restrictions are the environment the whole project runs
in and one write to such a save is unrecoverable.

The offline half builds a synthetic tree and needs no game. The `gamedata` half runs
against the **disposable Challenge-mode probe first** and only then the managed
league (plan §2.5 / SD-20): pointing untested code at the irreplaceable save when an
identical-mode disposable one sits beside it is avoidable exposure.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ootp_ai.saves import (
    CHALLENGE_DAT_SIZE,
    NotChallengeMode,
    assert_challenge_mode,
    enumerate_saves,
    is_challenge_mode,
    is_save_dir,
)

from ootp_ai.config import load_settings

# ── offline ──────────────────────────────────────────────────────────────────


def _make_save(root: Path, name: str, *, challenge: bool = False, partial: bool = False) -> Path:
    path = root / f"{name}.lg"
    path.mkdir(parents=True)
    (path / "teams.dat").write_bytes(b"\x00")
    if not partial:
        (path / "players.dat").write_bytes(b"\x00")
    if challenge:
        (path / "challenge.dat").write_bytes(b"\x00" * CHALLENGE_DAT_SIZE)
    return path


def test_a_real_save_is_recognised(tmp_path: Path) -> None:
    assert is_save_dir(_make_save(tmp_path, "OOTP-AI"))


def test_the_stray_dot_lg_directory_is_not_a_save(tmp_path: Path) -> None:
    """The measured trap. It matches `*.lg` and contains nothing."""
    (tmp_path / ".lg").mkdir()
    assert not is_save_dir(tmp_path / ".lg")
    assert enumerate_saves(tmp_path) == []


def test_a_directory_missing_players_dat_is_not_a_save(tmp_path: Path) -> None:
    """BOTH files are required — teams.dat alone is not enough."""
    assert not is_save_dir(_make_save(tmp_path, "Half", partial=True))


def test_enumeration_skips_decoys_and_returns_real_saves_sorted(tmp_path: Path) -> None:
    (tmp_path / ".lg").mkdir()
    (tmp_path / "not-a-save").mkdir()
    _make_save(tmp_path, "Zulu")
    _make_save(tmp_path, "Alpha")
    _make_save(tmp_path, "Broken", partial=True)

    found = [p.name for p in enumerate_saves(tmp_path)]
    assert found == ["Alpha.lg", "Zulu.lg"]


def test_enumerating_a_missing_root_raises_rather_than_returning_empty(tmp_path: Path) -> None:
    """An empty list would read as 'no saves' when the truth is 'wrong path'."""
    with pytest.raises(FileNotFoundError):
        enumerate_saves(tmp_path / "does-not-exist")


def test_challenge_mode_is_detected_from_the_filesystem(tmp_path: Path) -> None:
    assert is_challenge_mode(_make_save(tmp_path, "Managed", challenge=True))


def test_a_standard_save_has_no_challenge_dat(tmp_path: Path) -> None:
    assert not is_challenge_mode(_make_save(tmp_path, "Standard"))


def test_a_challenge_dat_of_the_wrong_size_is_not_accepted(tmp_path: Path) -> None:
    """241 bytes exactly. A different size means something we do not understand."""
    path = _make_save(tmp_path, "Odd")
    (path / "challenge.dat").write_bytes(b"\x00" * (CHALLENGE_DAT_SIZE + 1))
    assert not is_challenge_mode(path)


def test_assert_challenge_mode_raises_on_a_standard_save(tmp_path: Path) -> None:
    with pytest.raises(NotChallengeMode):
        assert_challenge_mode(_make_save(tmp_path, "Standard"))


def test_assert_challenge_mode_passes_on_a_challenge_save(tmp_path: Path) -> None:
    assert_challenge_mode(_make_save(tmp_path, "Managed", challenge=True))


# ── gamedata: the disposable probe FIRST, the managed league second ──────────


@pytest.mark.gamedata
def test_the_disposable_challenge_probe_is_a_challenge_save() -> None:
    settings = load_settings()
    if settings.probe_save is None:
        pytest.skip("OOTP_PROBE_LEAGUE is not set — cannot exercise the probe save")
    assert is_save_dir(settings.probe_save.path)
    assert_challenge_mode(settings.probe_save.path)


@pytest.mark.gamedata
def test_the_retained_standard_save_is_not_a_challenge_save() -> None:
    settings = load_settings()
    if settings.truth_save is None:
        pytest.skip("OOTP_TRUTH_LEAGUE is not set — cannot exercise the truth save")
    assert is_save_dir(settings.truth_save.path)
    assert not is_challenge_mode(settings.truth_save.path)


@pytest.mark.gamedata
def test_the_managed_league_is_a_challenge_save() -> None:
    settings = load_settings()
    assert is_save_dir(settings.managed.path)
    assert_challenge_mode(settings.managed.path)


@pytest.mark.gamedata
def test_enumeration_finds_the_managed_league_and_skips_the_stray() -> None:
    settings = load_settings()
    found = {p.stem for p in enumerate_saves(settings.saved_games)}
    assert settings.managed.league in found
    assert "" not in found, "the stray '.lg' directory was enumerated as a save"
