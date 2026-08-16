"""Finding saves on disk, and answering "is this Challenge Mode?" without a menu.

Two measured facts shape this module.

**A `*.lg` glob is not a list of saves.** The saved-games root holds a stray, empty
directory named literally `.lg`. It matches the pattern and contains nothing, so
enumeration confirms *contents* — `players.dat` and `teams.dat` at minimum — rather
than trusting a name.

**Mode is a filesystem fact.** `challenge.dat` is present at exactly 241 bytes in a
Challenge Mode save and absent otherwise. That makes the pre-flight check cheap
enough to run on every ingest, which matters more here than anywhere else in the
pipeline: the managed league runs in Challenge Mode, its save carries an integrity
hash, and one write destroys it irreversibly with no upstream backup. Everything
this module does is a read.
"""

from __future__ import annotations

from pathlib import Path

from ootp_ai.parser.header import MAGIC, looks_like_save_file

__all__ = [
    "CHALLENGE_DAT",
    "CHALLENGE_DAT_SIZE",
    "REQUIRED_FILES",
    "SAVE_SUFFIX",
    "NotChallengeMode",
    "assert_challenge_mode",
    "enumerate_saves",
    "is_challenge_mode",
    "is_record_file",
    "is_save_dir",
]

SAVE_SUFFIX = ".lg"

#: Both must be present. `teams.dat` alone is not a save — a partially-copied
#: directory would otherwise enumerate as one and fail much later, in the parser.
REQUIRED_FILES = ("players.dat", "teams.dat")

CHALLENGE_DAT = "challenge.dat"

#: `measured` — exactly 241 bytes when present. A different size means the file is
#: something this project has not seen, and claiming Challenge Mode on the strength
#: of a filename alone would be a claim about the one save that cannot be replaced.
CHALLENGE_DAT_SIZE = 241

_MAGIC_PROBE_LEN = 1 + len(MAGIC)


class NotChallengeMode(Exception):  # noqa: N818
    """A save that must be in Challenge Mode is not.

    The `…Error` suffix ruff's N818 wants is skipped because the offline suite
    imports this name; the test pins the interface and the naming rule yields.

    Raised by the per-run pre-flight. ADR 0003 makes Challenge Mode the environment
    the whole project runs in, so a save that is not in it is a different experiment.
    """


def is_save_dir(path: Path) -> bool:
    """True when `path` is a directory holding the files a save must have."""
    return path.is_dir() and all((path / name).is_file() for name in REQUIRED_FILES)


def enumerate_saves(root: Path) -> list[Path]:
    """Every save directory under `root`, sorted by name.

    Raises `FileNotFoundError` when `root` does not exist, rather than returning an
    empty list: "no saves here" and "that is the wrong path" are different answers,
    and only one of them is worth acting on.
    """
    if not root.is_dir():
        raise FileNotFoundError(f"saved-games root is not a directory: {root}")
    return sorted(path for path in root.glob(f"*{SAVE_SUFFIX}") if is_save_dir(path))


def is_challenge_mode(save: Path) -> bool:
    """True when the save carries a `challenge.dat` of exactly the expected size."""
    marker = save / CHALLENGE_DAT
    return marker.is_file() and marker.stat().st_size == CHALLENGE_DAT_SIZE


def assert_challenge_mode(save: Path) -> None:
    """Pre-flight for anything that touches the managed league.

    Raises:
        NotChallengeMode: `challenge.dat` is absent, or is not the expected size.
    """
    marker = save / CHALLENGE_DAT
    if not marker.is_file():
        raise NotChallengeMode(
            f"{save.name}: no {CHALLENGE_DAT} — this save is not in Challenge Mode"
        )
    size = marker.stat().st_size
    if size != CHALLENGE_DAT_SIZE:
        raise NotChallengeMode(
            f"{save.name}: {CHALLENGE_DAT} is {size} bytes, expected {CHALLENGE_DAT_SIZE} — "
            "the mode marker is not the shape this project has measured"
        )


def is_record_file(path: Path) -> bool:
    """True when `path` opens with the OOTP record-file magic.

    `measured` 2026-08-16: a save directory's `*.dat` glob catches two files that are
    not record files at all — `flag_save_completed.dat` is a plain-text log and
    `text_data.dat` is a ZIP archive. Anything iterating the glob and parsing headers
    should filter through this rather than teaching the header reader to shrug.

    Opened `"rb"`, five bytes, no write mode anywhere near the game's directories.
    """
    if not path.is_file():
        return False
    with path.open("rb") as handle:
        return looks_like_save_file(handle.read(_MAGIC_PROBE_LEN))
