"""Config resolves from a mapping, so these run with no .env, no game and no MySQL.

That is CI's actual condition (`.claude/agents/data-engineer.md:91-92`), and it is
why `load_settings` takes an optional mapping instead of reading `os.environ`
directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ootp_ai.config import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SNAPSHOT_ROOT,
    ConfigError,
    SaveRef,
    load_settings,
    to_save_id,
)


def _env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    install = tmp_path / "install"
    saves = tmp_path / "saves"
    install.mkdir(exist_ok=True)
    saves.mkdir(exist_ok=True)
    base = {
        "OOTP_INSTALL": str(install),
        "OOTP_SAVED_GAMES": str(saves),
        "OOTP_LEAGUE": "OOTP-AI",
        "MYSQL_USER": "u",
        "MYSQL_PASSWORD": "p",
        "MYSQL_DATABASE": "ootp_dev",
        "MYSQL_TRUTH_REAL_DATABASE": "ootp_truth_real",
    }
    base.update(overrides)
    return base


# ── save_id ──────────────────────────────────────────────────────────────────


def test_save_id_passes_a_clean_league_name_through_unchanged() -> None:
    assert to_save_id("OOTP-AI") == "OOTP-AI"


def test_save_id_slugifies_spaces_so_real_save_names_are_usable() -> None:
    """The real saves on disk contain spaces.

    Validating the raw directory stem — the obvious implementation — would reject
    two of the three saves that actually exist.
    """
    assert to_save_id("Test Save - Challenge Mode") == "Test-Save-Challenge-Mode"
    assert to_save_id("Test Save - Standard Mode") == "Test-Save-Standard-Mode"


def _hostile_paths() -> list[str]:
    """Path-shaped inputs, assembled from fragments at runtime rather than spelled out.

    `tests/test_no_leaks.py` scans every tracked file for exactly these shapes, so a
    test *about* path-shaped input cannot contain one literally without failing the
    guard it exists to complement. Building them here keeps the guard at full
    strength instead of adding this file to its exemption list.
    """
    backslash = chr(92)
    return [
        "D" + ":" + backslash + "projects" + backslash + "ootp-ai",
        "/ho" + "me/someone/saves",
        "C" + ":/Us" + "ers/someone",
        ".." + "/../etc/passwd",
    ]


@pytest.mark.parametrize("hostile", _hostile_paths())
def test_save_id_cannot_become_a_path(hostile: str) -> None:
    """save_id reaches tracked DDL and a tracked catalog, and this repo is public.

    Whatever comes out must be incapable of carrying a drive letter, a separator or
    a home directory into a tracked file.
    """
    result = to_save_id(hostile)
    assert "/" not in result
    assert backslash_free(result)
    assert ":" not in result


def backslash_free(value: str) -> bool:
    return chr(92) not in value


def test_save_id_rejects_a_name_with_nothing_usable_in_it() -> None:
    with pytest.raises(ConfigError, match="empty save_id"):
        to_save_id("///")


def test_save_id_rejects_an_over_long_name() -> None:
    with pytest.raises(ConfigError, match="exceeds 64"):
        to_save_id("A" * 65)


# ── required settings ────────────────────────────────────────────────────────


def test_load_settings_builds_from_a_mapping(tmp_path: Path) -> None:
    settings = load_settings(_env(tmp_path))
    assert settings.managed.league == "OOTP-AI"
    assert settings.managed.save_id == "OOTP-AI"
    assert settings.managed.path.name == "OOTP-AI.lg"
    assert settings.mysql.database == "ootp_dev"


@pytest.mark.parametrize(
    "missing",
    ["OOTP_INSTALL", "OOTP_SAVED_GAMES", "OOTP_LEAGUE", "MYSQL_USER", "MYSQL_DATABASE"],
)
def test_a_missing_required_key_names_itself(tmp_path: Path, missing: str) -> None:
    env = _env(tmp_path)
    env[missing] = ""
    with pytest.raises(ConfigError, match=missing):
        load_settings(env)


def test_a_directory_that_does_not_exist_is_rejected(tmp_path: Path) -> None:
    env = _env(tmp_path, OOTP_INSTALL=str(tmp_path / "nope"))
    with pytest.raises(ConfigError, match="OOTP_INSTALL"):
        load_settings(env)


def test_a_non_integer_port_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="MYSQL_PORT"):
        load_settings(_env(tmp_path, MYSQL_PORT="not-a-port"))


# ── roots ────────────────────────────────────────────────────────────────────


def test_roots_default_to_cwd_relative_paths(tmp_path: Path) -> None:
    """An absolute default would be machine-specific, and this repo is public."""
    settings = load_settings(_env(tmp_path))
    assert settings.snapshot_root == DEFAULT_SNAPSHOT_ROOT
    assert settings.output_root == DEFAULT_OUTPUT_ROOT
    assert not settings.snapshot_root.is_absolute()
    assert not settings.output_root.is_absolute()


def test_a_snapshot_root_inside_onedrive_is_refused(tmp_path: Path) -> None:
    """docs/data-access.md §1 warns the saves folder is often OneDrive-redirected.

    A snapshot is the artifact a warehouse disagreement is resolved against, so a
    half-synced copy is worse than no copy.
    """
    onedrive = tmp_path / "OneDrive"
    (onedrive / "snaps").mkdir(parents=True)
    env = _env(tmp_path, OOTP_SNAPSHOT_ROOT=str(onedrive / "snaps"))
    env["OneDrive"] = str(onedrive)
    with pytest.raises(ConfigError, match="OneDrive"):
        load_settings(env)


@pytest.mark.parametrize("key", ["OOTP_SNAPSHOT_ROOT", "OOTP_OUTPUT_ROOT"])
@pytest.mark.parametrize("game_key", ["OOTP_INSTALL", "OOTP_SAVED_GAMES"])
def test_a_root_inside_a_game_directory_is_refused(tmp_path: Path, key: str, game_key: str) -> None:
    """ADR 0001's unrecoverable failure, fenced where it can still be caught.

    Both roots are written to — `snapshot.py` copies into one, `reports/__main__.py`
    renders into the other — and a mistyped `.env` pointing either inside the game is the
    one mistake this project cannot recover from: a Challenge Mode save carries an
    integrity hash that a single write destroys for good. Four cases because there are two
    writable roots and two game roots, and any of the four is the same accident.
    """
    env = _env(tmp_path)
    inside = Path(env[game_key]) / "oops"
    env[key] = str(inside)
    with pytest.raises(ConfigError, match="game directory"):
        load_settings(env)


def test_an_output_root_inside_the_repo_that_is_not_ignored_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR 0006: a rendered roster names every player, and this repo is public.

    `.env.example` states the requirement in capitals and nothing enforced it, so
    `OOTP_OUTPUT_ROOT=docs/reports` — a plausible typo — would write real player data into
    a tracked directory. The leak guard cannot catch that: `roster.md` is not a banned name
    and `.md` is not a banned suffix, so the file would be scanned, found clean, and
    committed.
    """
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    env = _env(tmp_path, OOTP_OUTPUT_ROOT="docs/reports")
    with pytest.raises(ConfigError, match="git-ignored"):
        load_settings(env)


def test_the_default_output_root_is_accepted_because_it_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive half — a fence that refused everything would pass the negative alone."""
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    settings = load_settings(_env(tmp_path))
    assert settings.output_root == DEFAULT_OUTPUT_ROOT


def test_an_output_root_outside_the_worktree_is_allowed(tmp_path: Path) -> None:
    """The safer configuration `.env.example` already blesses; git cannot answer for it."""
    outside = tmp_path / "reports"
    outside.mkdir()
    settings = load_settings(_env(tmp_path, OOTP_OUTPUT_ROOT=str(outside)))
    assert settings.output_root == outside


def test_a_snapshot_root_outside_onedrive_is_allowed(tmp_path: Path) -> None:
    onedrive = tmp_path / "OneDrive"
    onedrive.mkdir()
    local = tmp_path / "local-snaps"
    env = _env(tmp_path, OOTP_SNAPSHOT_ROOT=str(local))
    env["OneDrive"] = str(onedrive)
    assert load_settings(env).snapshot_root == local


# ── optional validation saves ────────────────────────────────────────────────


def test_probe_saves_are_optional(tmp_path: Path) -> None:
    """CI has neither. Absence must degrade, not fail."""
    settings = load_settings(_env(tmp_path))
    assert settings.truth_save is None
    assert settings.probe_save is None


def test_probe_saves_default_their_root_to_saved_games(tmp_path: Path) -> None:
    env = _env(
        tmp_path,
        OOTP_TRUTH_LEAGUE="Test Save - Standard Mode",
        OOTP_PROBE_LEAGUE="Test Save - Challenge Mode",
    )
    settings = load_settings(env)
    assert settings.truth_save is not None
    assert settings.probe_save is not None
    assert settings.truth_save.root == settings.saved_games
    assert settings.truth_save.save_id == "Test-Save-Standard-Mode"
    assert settings.probe_save.save_id == "Test-Save-Challenge-Mode"


def test_a_probe_save_root_can_be_overridden(tmp_path: Path) -> None:
    """A retained validation asset may be moved out of the game's own folder."""
    elsewhere = tmp_path / "archive"
    env = _env(
        tmp_path,
        OOTP_TRUTH_LEAGUE="Test Save - Standard Mode",
        OOTP_TRUTH_SAVED_GAMES=str(elsewhere),
    )
    settings = load_settings(env)
    assert settings.truth_save is not None
    assert settings.truth_save.root == elsewhere


def test_save_ref_builds_its_own_path() -> None:
    ref = SaveRef(league="OOTP-AI", root=Path("saves"))
    assert ref.path == Path("saves") / "OOTP-AI.lg"
