"""`uv run python -m ootp_ai.catalog` — regenerate both halves of the catalog.

**No subcommand, deliberately.** Acceptance criterion 15 names this exact invocation, and
`reports` takes a subcommand because it will grow more than one verb. This command has
one job and adding `generate` to it would only make the criterion's command longer.

This is the project's third file writer and the second to write game-derived content, so
it is on the `tests/test_read_only.py` allowlist by name — `catalog/__main__.py`, not a
bare `__main__.py`, since Phase 10 narrowed that list to package-relative paths precisely
so this module could not allowlist itself in advance.

## What it writes, and which half needs a warehouse

* **The tracked half** — `docs/warehouse-catalog.md` + `.json` — is a pure function of the
  contract declarations. It needs no `.env`, no game, no save and no database, which is
  why `--structure-only` exists: a contributor with none of those can still regenerate the
  file `tests/test_repo_structure.py` requires to be present and `tests/test_catalog.py`
  requires to be byte-identical to what the generator produces.
* **The GM's copy** — `warehouse-catalog.md` + `catalog.json` under the snapshot-partitioned
  output root — needs a landing to describe, and says which one on line one.

There is no degraded mode in between. A run that could not reach the warehouse fails
loudly rather than writing the structural half and calling it a catalog: a page with no
counts looks exactly like a warehouse holding no rows.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from ootp_ai.catalog import (
    CATALOG_JSON_FILENAME,
    CATALOG_MARKDOWN_FILENAME,
    DEFAULT_DOCS_ROOT,
    TRACKED_JSON_FILENAME,
    TRACKED_MARKDOWN_FILENAME,
)
from ootp_ai.catalog.render import render_json, render_markdown
from ootp_ai.catalog.structure import build_structure
from ootp_ai.catalog.volume import fetch_volume
from ootp_ai.config import ConfigError, Settings, load_settings, reject_inside_game_roots
from ootp_ai.contracts.loader import load_contracts
from ootp_ai.contracts.policy import WithheldFieldError, check_policy_covers
from ootp_ai.db import connect_warehouse
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.reports.resolve import NoSuchSnapshot, report_dir, resolve_snapshot

__all__ = ["CatalogFiles", "generate", "main", "write_tracked_catalog"]


@dataclass(frozen=True, slots=True)
class CatalogFiles:
    """What a run wrote, by role rather than by filename.

    **The two Markdown files share a basename**, and that is not an accident worth
    renaming away: `warehouse-catalog.md` is the right name for the tracked schema
    document *and* for the GM's copy sitting beside `roster.md`. It does mean a caller
    picking a path out of a flat list by `path.name` gets whichever came first — measured,
    the first version of `tests/test_catalog.py` did exactly that and spent four
    assertions checking the tracked file while believing it was checking the landing.

    Returning roles instead of a list makes that mistake unavailable rather than
    documented.
    """

    tracked_markdown: Path
    tracked_json: Path
    catalog_markdown: Path | None = None
    catalog_json: Path | None = None

    @property
    def paths(self) -> tuple[Path, ...]:
        """Every file written, in write order."""
        written = [self.tracked_markdown, self.tracked_json]
        written.extend(path for path in (self.catalog_markdown, self.catalog_json) if path)
        return tuple(written)


def main(argv: list[str] | None = None) -> int:
    """Regenerate the catalog. Returns a process exit code."""
    args = _parser().parse_args(argv)
    docs_root = Path(args.docs_root)

    try:
        sim_date = _parse_sim_date(args.sim_date)
    except ValueError as error:
        print(f"--sim-date: {error}", file=sys.stderr)
        return 2

    try:
        if args.structure_only:
            _fence_docs_root(docs_root)
            written = write_tracked_catalog(docs_root)
        else:
            settings = load_settings()
            _fence_docs_root(docs_root, settings)
            written = generate(
                settings,
                docs_root=docs_root,
                save_id=args.save_id,
                sim_date=sim_date,
            )
    except ConfigError as error:
        print(f"configuration: {error}", file=sys.stderr)
        return 2
    except (NoSuchSnapshot, WithheldFieldError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1

    for path in written.paths:
        print(path)
    return 0


def _fence_docs_root(docs_root: Path, settings: Settings | None = None) -> None:
    """Refuse a `--docs-root` inside the game, before a single byte is written.

    `--docs-root` is the only write root in this project that an operator types on the
    command line rather than declaring in `.env`, and it shipped with no validation at
    all — while `OOTP_SNAPSHOT_ROOT` and `OOTP_OUTPUT_ROOT` have been fenced against the
    game directories since Phase 3. `--docs-root "$OOTP_SAVED_GAMES/OOTP-AI.lg"` is a
    plausible slip between two directories the operator types often, and it would have
    created files under a Challenge Mode save (ADR 0001).

    **`--structure-only` resolves settings anyway, and only for this check.** That mode
    deliberately needs no `.env` — a fresh clone must be able to regenerate the tracked
    file — so a failure to load is not fatal here: no `.env` means no configured game
    roots, and a machine with neither cannot write into them. What it must not do is skip
    the check when the roots *are* knowable, which is the case on the machine where the
    slip is possible.
    """
    resolved = settings
    if resolved is None:
        try:
            resolved = load_settings()
        except ConfigError:
            # No .env, so no game roots exist to be inside. `write_tracked_catalog` still
            # runs — that is the whole point of --structure-only.
            return
    reject_inside_game_roots(
        docs_root, key="--docs-root", game_roots=(resolved.install, resolved.saved_games)
    )


def write_tracked_catalog(docs_root: Path) -> CatalogFiles:
    """Write the structural half, and only that. No warehouse, no `.env`, no save."""
    contracts = load_contracts()
    check_policy_covers(contracts)
    structure = build_structure(contracts)

    docs_root.mkdir(parents=True, exist_ok=True)
    markdown = docs_root / TRACKED_MARKDOWN_FILENAME
    document = docs_root / TRACKED_JSON_FILENAME
    _write(markdown, render_markdown(structure))
    _write(document, render_json(structure))
    return CatalogFiles(tracked_markdown=markdown, tracked_json=document)


def generate(
    settings: Settings,
    *,
    docs_root: Path = DEFAULT_DOCS_ROOT,
    save_id: str | None = None,
    sim_date: SaveDate | None = None,
) -> CatalogFiles:
    """Write both halves and return what was written, by role.

    `save_id` defaults to the managed league, matching `reports.render`: the disposable
    Challenge-mode twin is the right target for rehearsing a generation without touching
    the managed league's output tree.
    """
    contracts = load_contracts()
    # The declaration may have grown a category since this code was written. Fail loudly
    # rather than letting `disposition()` withhold every field under it — which is safe,
    # and reads as a catalog that has quietly stopped describing half the warehouse.
    check_policy_covers(contracts)
    structure = build_structure(contracts)

    resolved_save = settings.managed.save_id if save_id is None else save_id
    connection = connect_warehouse(settings)
    try:
        ref = resolve_snapshot(connection, save_id=resolved_save, sim_date=sim_date)
        volume = fetch_volume(connection, contracts, ref)
    finally:
        connection.close()

    tracked = write_tracked_catalog(docs_root)

    directory = report_dir(settings.output_root, ref)
    directory.mkdir(parents=True, exist_ok=True)
    page = directory / CATALOG_MARKDOWN_FILENAME
    document = directory / CATALOG_JSON_FILENAME
    _write(page, render_markdown(structure, volume))
    _write(document, render_json(structure, volume))
    return CatalogFiles(
        tracked_markdown=tracked.tracked_markdown,
        tracked_json=tracked.tracked_json,
        catalog_markdown=page,
        catalog_json=document,
    )


def _write(path: Path, text: str) -> None:
    """UTF-8 and `\\n`, explicitly.

    The dev platform is Windows and both halves are hashed, diffed and byte-compared — the
    tracked one by `tests/test_catalog.py` on every run, in CI, on Linux. A CRLF that
    varied by platform would make two identical generations compare unequal and turn the
    byte-identity assertion into a flake, which is how a guard ends up deleted.
    """
    path.write_text(text, encoding="utf-8", newline="\n")


def _parse_sim_date(raw: str | None) -> SaveDate | None:
    """`YYYY-MM-DD` as the save's own date type, or `None` for "the latest landed"."""
    if raw is None:
        return None
    parts = raw.split("-")
    if len(parts) != 3:
        raise ValueError(f"expected YYYY-MM-DD, got {raw!r}")
    try:
        year, month, day = (int(part) for part in parts)
    except ValueError as error:
        raise ValueError(f"expected YYYY-MM-DD, got {raw!r}") from error
    return SaveDate(day=day, month=month, year=year)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ootp_ai.catalog",
        description=(
            "Regenerate the warehouse catalog: the tracked structural half under docs/, "
            "and the GM's copy under the snapshot-partitioned output root."
        ),
    )
    parser.add_argument(
        "--save-id",
        default=None,
        help="the universe to describe. Defaults to the managed league from .env.",
    )
    parser.add_argument(
        "--sim-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="the in-game date to describe. Defaults to the most recent one landed.",
    )
    parser.add_argument(
        "--docs-root",
        default=str(DEFAULT_DOCS_ROOT),
        metavar="DIR",
        help=(
            "where the tracked half is written. Defaults to the repository's docs/ "
            "directory, resolved relative to the working directory."
        ),
    )
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help=(
            "write only the tracked structural half. Needs no .env, no save and no "
            "warehouse, so a fresh clone can regenerate the committed file."
        ),
    )
    return parser


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
