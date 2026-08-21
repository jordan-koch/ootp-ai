"""`uv run python -m ootp_ai.reports render` — the operator's entry point.

Deliberately the *only* one. Phase 9 declined to give the differential a `__main__` so
that this would be the first, and the pattern it sets is the one every later report
follows: resolve settings, resolve a snapshot explicitly, render, write under the
snapshot's own directory, and print the triple it used.

The command prints where it wrote and which landing it read. That output is what the
umpire pastes when handing the report to the GM, so it names the club, the `sim_date` and
the `ingest_seq` — the three things a `gm/decisions/` record needs to be checkable later.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ootp_ai.config import ConfigError, Settings, load_settings
from ootp_ai.contracts.loader import load_contracts
from ootp_ai.contracts.policy import WithheldFieldError, check_policy_covers
from ootp_ai.db import connect_warehouse
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.reports.resolve import NoSuchSnapshot, report_dir, resolve_snapshot
from ootp_ai.reports.roster import (
    build_roster,
    club_display_name,
    fetch_clubs,
    list_label_mode,
    render_roster,
)

ROSTER_FILENAME = "roster.md"


def main(argv: list[str] | None = None) -> int:
    """Render the reports for one landing. Returns a process exit code."""
    args = _parser().parse_args(argv)
    try:
        settings = load_settings()
    except ConfigError as error:
        print(f"configuration: {error}", file=sys.stderr)
        return 2

    try:
        sim_date = _parse_sim_date(args.sim_date)
    except ValueError as error:
        print(f"--sim-date: {error}", file=sys.stderr)
        return 2

    try:
        written = render(settings, save_id=args.save_id, sim_date=sim_date)
    except (NoSuchSnapshot, WithheldFieldError, ValueError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1

    for path in written:
        print(path)
    return 0


def render(
    settings: Settings,
    *,
    save_id: str | None = None,
    sim_date: SaveDate | None = None,
) -> list[Path]:
    """Write every report for one landing and return the paths, in write order.

    `save_id` defaults to the managed league — the club this front office runs. It is
    still overridable, because the disposable Challenge-mode twin is the right target for
    rehearsing a render without touching the managed league's output tree.
    """
    contracts = load_contracts()
    # The declaration may have grown a category since this code was written. Fail loudly
    # here rather than letting `disposition()` withhold every field under it — which is
    # safe, and looks exactly like a bug in the report.
    check_policy_covers(contracts)

    resolved_save = settings.managed.save_id if save_id is None else save_id
    connection = connect_warehouse(settings)
    try:
        ref = resolve_snapshot(connection, save_id=resolved_save, sim_date=sim_date)
        rows = build_roster(connection, contracts, ref)
        clubs = fetch_clubs(connection, ref)
        # SD-17's pre-registered fallback: human roster-list labels only while the mapping
        # holds at least `inferred`, raw ids plus a banner otherwise. Decided from the
        # declaration on every render rather than assumed once.
        labels, banner = list_label_mode(contracts)
        page = render_roster(
            ref,
            rows,
            clubs,
            club_name=club_display_name(clubs, ref.human_team_id),
            list_labels=labels,
            list_banner=banner,
        )
    finally:
        connection.close()

    directory = report_dir(settings.output_root, ref)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ROSTER_FILENAME
    # UTF-8 explicitly and newline="\n": the dev platform is Windows and the report is
    # read by an agent, diffed, and hashed. A CRLF that varies by platform would make two
    # identical renders compare unequal.
    path.write_text(page, encoding="utf-8", newline="\n")
    return [path]


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
        prog="python -m ootp_ai.reports",
        description="Render the front office's reports from a landed warehouse snapshot.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    render_command = sub.add_parser(
        "render",
        help="render the reports for one landing",
        description=(
            "Renders from one landed snapshot. Without --sim-date the most recent landing "
            "for the save is used, and the resolved triple is printed and written onto "
            "line one of every report."
        ),
    )
    render_command.add_argument(
        "--save-id",
        default=None,
        help="the universe to render. Defaults to the managed league from .env.",
    )
    render_command.add_argument(
        "--sim-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="the in-game date to render. Defaults to the most recent one landed.",
    )
    return parser


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
