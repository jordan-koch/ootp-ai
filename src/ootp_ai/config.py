"""Settings resolved from the environment — the only module here that reads it.

Two rules shape this file, and both are load-bearing rather than stylistic:

* **Resolve by name, never hardcode.** Every path comes from `.env` through this
  module. No literal path, no `parents[N]` walk to find the repo root
  (`.claude/agents/data-engineer.md`, "Resolve by name, never hardcode").
* **`load_settings` takes a mapping.** CI has no `.env`, no game and no MySQL, so
  the settings layer has to be exercisable from a dict. Reading `os.environ`
  directly would make every downstream test require a machine.

`save_id` is derived here and reaches tracked DDL and a tracked catalog, so it is
normalised to `[A-Za-z0-9_-]` and can never carry a drive letter, a separator or a
home directory into a public repo.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

__all__ = [
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_SNAPSHOT_ROOT",
    "ConfigError",
    "MySQLSettings",
    "SaveRef",
    "Settings",
    "load_settings",
    "reject_inside_game_roots",
    "to_save_id",
]

# CWD-relative on purpose: an absolute default would be machine-specific, and this
# repo is public. Both live under `var/`, which is gitignored.
DEFAULT_SNAPSHOT_ROOT = Path("var/snapshots")
DEFAULT_OUTPUT_ROOT = Path("var/reports")

SAVE_ID_MAX_LEN = 64
SAVE_EXTENSION = ".lg"

_UNSAFE_IN_SAVE_ID = re.compile(r"[^A-Za-z0-9_-]+")
_HYPHEN_RUN = re.compile(r"-{2,}")


class ConfigError(Exception):
    """A setting is missing, malformed, or points somewhere it must not."""


def to_save_id(league: str) -> str:
    """Normalise a league name into a `save_id` safe for a key and a tracked file.

    The real saves on disk contain spaces and a dash separator, so validating the
    raw directory stem — the obvious implementation — would reject two of the three
    saves that exist. Slugify instead, then assert the result is clean.
    """
    slug = _HYPHEN_RUN.sub("-", _UNSAFE_IN_SAVE_ID.sub("-", league)).strip("-")
    if not slug:
        raise ConfigError("empty save_id: the league name holds no usable characters")
    if len(slug) > SAVE_ID_MAX_LEN:
        raise ConfigError(f"save_id exceeds {SAVE_ID_MAX_LEN} characters (got {len(slug)})")
    return slug


@dataclass(frozen=True, slots=True)
class SaveRef:
    """One save universe: the league name, the root it sits under, and its id."""

    league: str
    root: Path

    @property
    def path(self) -> Path:
        return self.root / f"{self.league}{SAVE_EXTENSION}"

    @property
    def save_id(self) -> str:
        return to_save_id(self.league)


@dataclass(frozen=True, slots=True)
class MySQLSettings:
    """Connection settings. `truth_database` is optional — CI has no warehouse."""

    host: str
    port: int
    user: str
    password: str
    database: str
    truth_database: str | None


@dataclass(frozen=True, slots=True)
class Settings:
    install: Path
    saved_games: Path
    managed: SaveRef
    truth_save: SaveRef | None
    probe_save: SaveRef | None
    snapshot_root: Path
    output_root: Path
    mysql: MySQLSettings


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build `Settings` from `env`, or from `.env` + the process environment."""
    values = _process_environment() if env is None else env

    install = _required_directory(values, "OOTP_INSTALL")
    saved_games = _required_directory(values, "OOTP_SAVED_GAMES")

    managed = SaveRef(league=_required(values, "OOTP_LEAGUE"), root=saved_games)
    # Validated eagerly: a bad league name must fail here, not at the first key write.
    _ = managed.save_id

    onedrive = _optional(values, "OneDrive")
    game_roots = (install, saved_games)
    snapshot_root = _root(values, "OOTP_SNAPSHOT_ROOT", DEFAULT_SNAPSHOT_ROOT, onedrive, game_roots)
    output_root = _root(values, "OOTP_OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT, onedrive, game_roots)
    _check_never_tracked(output_root, "OOTP_OUTPUT_ROOT")

    return Settings(
        install=install,
        saved_games=saved_games,
        managed=managed,
        truth_save=_optional_save(
            values, "OOTP_TRUTH_LEAGUE", "OOTP_TRUTH_SAVED_GAMES", saved_games
        ),
        probe_save=_optional_save(
            values, "OOTP_PROBE_LEAGUE", "OOTP_PROBE_SAVED_GAMES", saved_games
        ),
        snapshot_root=snapshot_root,
        output_root=output_root,
        mysql=MySQLSettings(
            host=_optional(values, "MYSQL_HOST") or "localhost",
            port=_port(values),
            user=_required(values, "MYSQL_USER"),
            password=_optional(values, "MYSQL_PASSWORD") or "",
            database=_required(values, "MYSQL_DATABASE"),
            truth_database=_optional(values, "MYSQL_TRUTH_REAL_DATABASE"),
        ),
    )


def _process_environment() -> Mapping[str, str]:
    """Load `.env` without clobbering anything already exported in the shell."""
    load_dotenv(override=False)
    return os.environ


def _optional(values: Mapping[str, str], key: str) -> str | None:
    value = values.get(key, "").strip()
    return value or None


def _required(values: Mapping[str, str], key: str) -> str:
    value = _optional(values, key)
    if value is None:
        raise ConfigError(f"{key} is required and is unset or empty; see .env.example")
    return value


def _required_directory(values: Mapping[str, str], key: str) -> Path:
    path = Path(_required(values, key))
    if not path.is_dir():
        raise ConfigError(f"{key} does not name an existing directory")
    return path


def _port(values: Mapping[str, str]) -> int:
    raw = _optional(values, "MYSQL_PORT")
    if raw is None:
        return 3306
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError("MYSQL_PORT must be an integer") from exc


def _root(
    values: Mapping[str, str],
    key: str,
    default: Path,
    onedrive: str | None,
    game_roots: tuple[Path, ...] = (),
) -> Path:
    """Resolve an output root, refusing a cloud-synced, in-game, or unusable location.

    Not created here. Configuration that mkdirs as a side effect of being read
    scatters directories during test collection.
    """
    raw = _optional(values, key)
    root = default if raw is None else Path(raw)

    if root.exists() and not root.is_dir():
        raise ConfigError(f"{key} points at an existing file, not a directory")

    if onedrive:
        # A snapshot is the artifact a warehouse disagreement is resolved against,
        # so a half-synced copy is worse than no copy (docs/data-access.md §1).
        synced = Path(onedrive).expanduser()
        if _is_within(root, synced):
            raise ConfigError(f"{key} sits under OneDrive; snapshots must be on local disk")

    reject_inside_game_roots(root, key=key, game_roots=game_roots)
    return root


def reject_inside_game_roots(root: Path, *, key: str, game_roots: tuple[Path, ...] = ()) -> None:
    """Refuse a write root that resolves inside the game install or the saved games.

    ADR 0001's unrecoverable failure, fenced at the only place that can see it. The roots
    this guards are written to — `snapshot.py` copies into one, `reports/__main__.py`
    renders into another, `catalog/__main__.py` into two — and a mistyped path pointing
    any of them inside the game is the one mistake this project has no recovery from: a
    Challenge Mode save carries an integrity hash that a single write destroys for good.
    Refusing costs two lines; the alternative was trusting the operator's typing.

    **Public since Phase 11, and that is the point.** `--docs-root` is the project's first
    operator-supplied write root — every other one arrives through `.env` and was already
    fenced here — and it shipped unvalidated, so a tab-completion slip between two
    directories the operator types often would have created files under the managed save.
    A second copy of this check in the catalog would have been a second thing to keep in
    step; one function with two callers cannot drift.
    """
    for game_root in game_roots:
        if _is_within(root, game_root):
            raise ConfigError(
                f"{key} resolves inside a game directory ({game_root}). Nothing this "
                "project runs may write under the install or the saved games (ADR 0001); "
                "one write to a Challenge Mode save is unrecoverable"
            )


def _check_never_tracked(root: Path, key: str) -> None:
    """Refuse an output root inside the worktree that git would not ignore (ADR 0006).

    A rendered roster names every player in the organisation. `.env.example` states in
    capitals that the root must be git-ignored and, until this check, nothing enforced it —
    so `OOTP_OUTPUT_ROOT=docs/reports`, a plausible typo or a deliberate "I want to read
    these in my editor", would write real player data into a tracked directory of a public
    repo. The leak guard could not catch it: `roster.md` is not a banned name and `.md` is
    not a banned suffix, so the file would be opened, found free of machine paths, and
    reported clean.

    A root **outside** the worktree passes unconditionally — that is the safer
    configuration `.env.example` already blesses, and git cannot answer for it.
    """
    if not _is_within(root, Path.cwd()):
        return
    probe = root / ".probe"
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", str(probe)],
        capture_output=True,
        check=False,
    )
    if ignored.returncode == 0:
        return
    raise ConfigError(
        f"{key} resolves to {root}, which is inside the repository and is NOT git-ignored. "
        "A rendered report names real players and this repo is public (ADR 0006); point it "
        "at an ignored path such as var/reports, or somewhere outside the worktree"
    )


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        return candidate.resolve().is_relative_to(parent.resolve())
    except OSError:  # pragma: no cover - resolution failure means "not under it"
        return False


def _optional_save(
    values: Mapping[str, str],
    league_key: str,
    root_key: str,
    default_root: Path,
) -> SaveRef | None:
    """A validation save the offline suite and CI do not have. Absence degrades."""
    league = _optional(values, league_key)
    if league is None:
        return None
    root = _optional(values, root_key)
    ref = SaveRef(league=league, root=default_root if root is None else Path(root))
    _ = ref.save_id
    return ref
