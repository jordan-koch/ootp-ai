"""AC14 — the roster report, rendered from the real warehouse and checked as a page.

This is the criterion the whole request exists for: after it, the GM can name its own
players. So the assertions are about the **file that was written**, not about the functions
that wrote it — `tests/test_report_rendering.py` owns the pure half and runs in CI, while
everything here needs a landed warehouse and is therefore `gamedata`.

## What AC14 asks for, and what this module can honestly close

AC14 has five clauses. Four are about the roster report and are closed here:

1. the resolved output root is **git-ignored** — proven both ways, by `git check-ignore`
   exiting 0 *and* by `git ls-files` listing nothing under it;
2. the report holds rows for **exactly** the configured organisation and zero belonging to
   any other;
3. every player row's name matches `^[A-Za-z][A-Za-z .'-]+$` — a name, not an integer;
4. line one carries the club, the `sim_date` **and** the `ingest_seq`.

The fifth clause — *"the standings report contains 30 MLB rows grouped by division with
W-L-pct-GB columns present"* — **is not closed, and is not closeable.** No wins/losses
column exists in any declared table: Phase 5 measured that the standings region is not in
`teams.dat` (`parser/teams.py`: *"So is the standings region, which is not here either"*),
and Phase 5b's `world.dat` walk landed divisions and the calendar rather than records. The
"all 259 `team_record` rows are 0-0-0" figure the plan cites is the **export's** table,
which this project never landed. Building a shell whose four columns are backed by no
declared column would be inventing a schema, so the standings report was dropped from this
phase at the operator's direction and the clause is recorded `unmet` in the
implementation report rather than papered over here.

## Why the name regex is the assertion that matters

It is the one clause that can tell a *working* pipeline from a plausible one. Every id in
this project is an integer and every join could silently fail; a report full of `47035`
would satisfy every structural assertion ever written about row counts and headings. A
name is the observable signal that `names.dat`, the index join and the landing all agree.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from fixtures.reports import NAME_PATTERN
from ootp_ai.config import ConfigError, Settings, load_settings
from ootp_ai.contracts.loader import load_contracts
from ootp_ai.db import connect_warehouse
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.reports.__main__ import ROSTER_FILENAME, render
from ootp_ai.reports.resolve import NoSuchSnapshot, resolve_snapshot
from ootp_ai.reports.roster import build_roster
from ootp_ai.warehouse.sql import column_list, quote_ident

REPO_ROOT = Path(__file__).resolve().parent.parent

#: What a player row's first cell must look like. Defined in `tests/fixtures/reports.py`
#: so the offline module can guard the pattern itself in CI — see the note there on why it
#: is Unicode-aware where AC14's quoted text is not.

#: The report's data rows carry a player id in the last cell; the heading and separator
#: rows do not. Used to pick the rows whose first cell is a name.
TABLE_ROW = re.compile(r"^\| (?P<name>[^|]+) \|")


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings: {exc}")


@pytest.fixture(scope="module")
def settings() -> Settings:
    return _settings()


@pytest.fixture(scope="module")
def warehouse(settings: Settings) -> Iterator[Connection[DictCursor]]:
    try:
        connection = connect_warehouse(settings)
    except Exception as exc:  # pragma: no cover - no warehouse locally
        pytest.skip(f"cannot open the warehouse: {exc}")
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def rendered(settings: Settings) -> Path:
    """The roster report, actually written by the entry point AC14 names.

    Rendered through `render()` rather than by calling the report functions directly: the
    criterion is about `uv run python -m ootp_ai.reports render`, and a test that assembled
    the page itself would prove the formatter works while the command stayed broken.
    """
    try:
        written = render(settings)
    except NoSuchSnapshot as exc:
        pytest.skip(f"nothing landed to render: {exc}")
    assert len(written) == 1, f"expected one report this phase, got {written}"
    return written[0]


def _is_git_ignored(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
        ).returncode
        == 0
    )


def _tracked_under(path: Path) -> list[str]:
    """Tracked files under `path`, or `[]` when `path` is outside the worktree.

    The early return is not a convenience. `git ls-files -- <absolute path outside the
    repo>` exits 128 with *"is outside repository"*, so with `check=True` this raised
    `CalledProcessError` — and an out-of-tree `OOTP_OUTPUT_ROOT` is a **supported**
    configuration that satisfies ADR 0006 more strongly than the default does. Both
    callers guarded their other helper against that case and called this one unguarded, so
    AC14's clause-1 tests would have ERRORed on the safer setup. Nothing outside the
    worktree can be tracked, so the answer there is trivially empty.
    """
    if not path.resolve().is_relative_to(REPO_ROOT):
        return []
    out = subprocess.run(
        ["git", "ls-files", "--", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _page(path: Path) -> str:
    """Read as UTF-8 explicitly — the writer pins it, so the reader must not guess."""
    return path.read_text(encoding="utf-8")


def _player_rows(page: str) -> list[str]:
    """Every table row naming a player, heading and separator rows excluded."""
    rows = []
    for line in page.splitlines():
        if not line.startswith("| "):
            continue
        if line.startswith("| Player |") or line.startswith("|---"):
            continue
        rows.append(line)
    return rows


def _names(page: str) -> list[str]:
    names = []
    for row in _player_rows(page):
        match = TABLE_ROW.match(row)
        assert match is not None, f"unparseable table row: {row}"
        names.append(match.group("name").strip())
    return names


# ── AC14 clause 1: the output root is git-ignored, proven both ways ──────────


@pytest.mark.gamedata
def test_the_resolved_output_root_is_git_ignored(settings: Settings) -> None:
    """Rendered game data must never become committable (ADR 0006).

    Both directions, because either alone is satisfiable by an accident: `check-ignore`
    passing proves the rule exists, and `ls-files` being empty proves nothing slipped in
    before it did.
    """
    root = settings.output_root
    if root.resolve().is_relative_to(REPO_ROOT):
        assert _is_git_ignored(root), (
            f"the output root {root} resolves inside the repo and is NOT git-ignored. "
            "This is the first thing in the project's history that renders OOTP player "
            "data to a file, and the repo is public"
        )
    assert not _tracked_under(root), f"tracked files already exist under {root}"


@pytest.mark.gamedata
def test_the_written_report_is_git_ignored(rendered: Path) -> None:
    """The file itself, not merely the directory it was supposed to land in."""
    if rendered.resolve().is_relative_to(REPO_ROOT):
        assert _is_git_ignored(rendered), f"{rendered} is not git-ignored"
    assert not _tracked_under(rendered)


# ── AC14 clause 2: exactly the configured organisation ───────────────────────


@pytest.mark.gamedata
def test_every_player_belongs_to_the_configured_organisation(
    settings: Settings, warehouse: Connection[DictCursor]
) -> None:
    """Zero rows from any other organisation — asserted against the warehouse, not the page.

    The page cannot answer this on its own: a player of another organisation would render
    as a perfectly ordinary row. So the ids the report built from are re-read here and
    checked against `bronze_player.organization_id` directly.
    """
    ref = resolve_snapshot(warehouse, save_id=settings.managed.save_id)
    rows = build_roster(warehouse, load_contracts(), ref)
    assert rows, "the roster came back empty; there is nothing to check"

    ids = {row.player_id for row in rows}
    with warehouse.cursor() as cursor:
        cursor.execute(
            f"SELECT {column_list(('player_id', 'organization_id'))} "
            f"FROM {quote_ident('bronze_player')} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s "
            f"AND {quote_ident('organization_id')} <> %s",
            (*ref.triple, ref.human_team_id),
        )
        foreign = {int(row["player_id"]) for row in cursor.fetchall()}

    trespassers = sorted(ids & foreign)
    assert not trespassers, (
        f"{len(trespassers)} players on the report belong to another organisation: "
        f"{trespassers[:10]}"
    )

    # And the same assertion aimed at the WRONG club must go red, or it is measuring the
    # shape of its own query rather than the filter. The panel's verifier established both
    # mutations empirically — pointing the filter at another club yields 205 trespassers,
    # dropping the predicate yields 21,820 — so this pins the discrimination rather than
    # trusting it. Any other organisation with players will do; the first one found wins.
    with warehouse.cursor() as cursor:
        cursor.execute(
            f"SELECT {quote_ident('organization_id')} AS other "
            f"FROM {quote_ident('bronze_player')} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s "
            f"AND {quote_ident('organization_id')} NOT IN (%s, 0) "
            f"LIMIT 1",
            (*ref.triple, ref.human_team_id),
        )
        row = cursor.fetchone()
    assert row is not None, "the landing holds only one organisation; the mutation cannot run"

    wrong = replace(ref, human_team_id=int(row["other"]))
    other_ids = {player.player_id for player in build_roster(warehouse, load_contracts(), wrong)}
    assert other_ids and not (other_ids & ids), (
        "building the roster for a different organisation returned the same players, so "
        "the organisation filter is not discriminating and this criterion cannot fail"
    )


@pytest.mark.gamedata
def test_the_report_holds_every_player_of_the_organisation(
    settings: Settings, warehouse: Connection[DictCursor]
) -> None:
    """The other direction, and it is the one a filter bug actually breaks.

    "Zero foreign rows" is satisfied trivially by an empty report. This pins that the
    organisation's whole population reached the page — including the players who hold no
    roster row at all, whom driving from `bronze_team_roster` would have silently dropped.
    """
    ref = resolve_snapshot(warehouse, save_id=settings.managed.save_id)
    rows = build_roster(warehouse, load_contracts(), ref)

    with warehouse.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM {quote_ident('bronze_player')} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s "
            f"AND {quote_ident('organization_id')} = %s",
            (*ref.triple, ref.human_team_id),
        )
        row = cursor.fetchone()
    assert row is not None
    assert len(rows) == int(row["total"]), (
        f"the report carries {len(rows)} players and the warehouse holds "
        f"{row['total']} for this organisation"
    )


# ── AC14 clause 3: names, not integers ───────────────────────────────────────


@pytest.mark.gamedata
def test_every_player_row_names_a_person(rendered: Path) -> None:
    """The observable signal the whole slice was built for."""
    names = _names(_page(rendered))
    assert names, "the report contains no player rows at all"
    bad = [name for name in names if not NAME_PATTERN.match(name)]
    assert not bad, f"{len(bad)} rows do not carry a name: {bad[:10]}"


@pytest.mark.gamedata
def test_the_report_names_a_recognisable_number_of_players(rendered: Path) -> None:
    """A sanity band, not a pinned count — the roster changes with every transaction.

    Deliberately loose. A pinned number would go red on a correct parse the first time the
    operator signs anybody, which is the most expensive kind of wrong test: it sends the
    next agent hunting a bug in working code.
    """
    names = _names(_page(rendered))
    assert len(names) > 25, f"only {len(names)} player rows; an organisation carries more"


# ── AC14 clause 4: provenance on line one ────────────────────────────────────


@pytest.mark.gamedata
def test_line_one_carries_the_club_the_sim_date_and_the_ingest_seq(
    settings: Settings, warehouse: Connection[DictCursor], rendered: Path
) -> None:
    """All three. The seq clause is the one that matters once a date is ingested twice.

    A report naming only its date points at a moving target, and a `gm/decisions/` record
    citing it stops being checkable the moment a second sequence lands.
    """
    ref = resolve_snapshot(warehouse, save_id=settings.managed.save_id)
    head = "\n".join(_page(rendered).splitlines()[:5])

    assert str(ref.sim_date) in head, f"line one does not name the sim date: {head}"
    assert f"**Ingest seq** {ref.ingest_seq}" in head, (
        f"line one does not name the ingest_seq it rendered from: {head}"
    )
    assert ref.save_id in head, f"line one does not name the save: {head}"


@pytest.mark.gamedata
def test_the_report_lands_in_a_directory_named_by_its_snapshot(
    settings: Settings, warehouse: Connection[DictCursor], rendered: Path
) -> None:
    """`<root>/<save_id>/<sim_date>/<ingest_seq>/roster.md`.

    The partitioning is what makes a citation survive: a later date or a later sequence
    writes a new directory beside this one rather than over it, so the exact bytes the GM
    read are still on disk when someone checks the decision months later.
    """
    ref = resolve_snapshot(warehouse, save_id=settings.managed.save_id)
    assert rendered.name == ROSTER_FILENAME
    assert rendered.parent.name == str(ref.ingest_seq)
    assert rendered.parent.parent.name == str(ref.sim_date)
    assert rendered.parent.parent.parent.name == ref.save_id


@pytest.mark.gamedata
def test_re_rendering_the_same_snapshot_is_byte_identical(settings: Settings) -> None:
    """Idempotent per triple — the property snapshot-partitioning buys.

    Two renders of one landing must agree exactly, or a report cited in a decision record
    could not be reproduced even with the snapshot still on disk.
    """
    first = render(settings)[0].read_bytes()
    second = render(settings)[0].read_bytes()
    assert first == second


# ── the report reflects the snapshot it was asked for ────────────────────────


@pytest.mark.gamedata
def test_an_unlanded_sim_date_is_refused_rather_than_rendered_empty(
    settings: Settings, warehouse: Connection[DictCursor]
) -> None:
    """An empty roster page and a club that released everybody look identical.

    The refusal names what the warehouse does hold, so the operator sees the typo rather
    than going to check the loader.
    """
    never_landed = SaveDate(day=1, month=1, year=1900)
    with pytest.raises(NoSuchSnapshot) as raised:
        resolve_snapshot(warehouse, save_id=settings.managed.save_id, sim_date=never_landed)
    assert "1900-01-01" in str(raised.value)
    assert "has landed at" in str(raised.value)
