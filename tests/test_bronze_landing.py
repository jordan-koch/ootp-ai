"""The loader's contract with the declaration — proven offline, against no database.

Everything else Phase 8b added needs a populated MySQL, and §4.1 is explicit about what
that costs: *"a phase proved only by `gamedata` tests has zero CI signal"*. A later change
could break the loader's column binding and nothing would go red until somebody ran the
local suite. So the part of the loader that is a pure function of the declaration — which
columns exist, which values bind to them, and what happens when the two disagree — is
tested here, through a connection that records statements instead of executing them.

## What a fake connection can and cannot prove

It proves the SQL this module *builds*: the column list comes from `tables.toml`, the
values are bound in declared order, structural absence binds as `None`, and the run row is
claimed before the first bronze row. It cannot prove MySQL accepts any of it — that is
what the `gamedata` half does, against the real server, on a real save.

Both halves are needed and neither substitutes for the other. This one runs on every push.

## The gap this closes

The Phase 8a acceptance panel carried CF22 as its largest open item: *nothing tied a
declared column set to the parser record it claims to be 1:1 with*. Adding a column to
`tables.toml` and forgetting the loader landed a silent NULL; renaming a parser field
landed a silent nothing. The loader now checks every row against the declared column set
before binding it, and the two tests below break that check in each direction.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pymysql
import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.contracts.loader import Column, Contracts, Table, load_contracts
from ootp_ai.ingest import (
    IngestRun,
    ParsedSnapshot,
    SnapshotDateMismatch,
    SourceFile,
    UndecodedRecords,
    check_decoded,
    check_sim_dates,
)
from ootp_ai.parser.names import NAMES_FILE, NameRecord, NamesFile
from ootp_ai.parser.players import PlayerRecord, PlayersFile
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.parser.rosters import RosterMembership, RostersFile
from ootp_ai.parser.teams import TEAMS_FILE, TeamRecord, TeamsFile
from ootp_ai.parser.world import CalendarEvent, DivisionMembership, WorldFile
from ootp_ai.snapshot import Snapshot
from ootp_ai.warehouse.ingest_run import (
    INGEST_RUN_TABLE,
    as_sql_date,
    ingest_run_values,
    nullable_sql_date,
)
from ootp_ai.warehouse.load import ConcurrentLandingError, LoadError, land_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent

SIM_DATE = SaveDate(day=7, month=3, year=2024)
SIM_DATE_TEXT = "2024-03-07"
#: A real calendar date for the synthetic event. Module-level because ruff's `B008` refuses
#: a constructor call in a default argument.
OPENING_DAY = SaveDate(day=28, month=3, year=2024)
#: A date the save writes where a date does not apply. `parser/world.py` accepts it for a
#: calendar record on purpose and `parser/players.py` refuses to frame a record on one.
NO_DATE = SaveDate(day=0, month=0, year=0)


# ── a connection that records rather than executes ───────────────────────────


_TABLE_IN_SQL = re.compile(r"`(?P<name>[A-Za-z_][A-Za-z0-9_]*)`")


class _FakeCursor:
    """Records every statement, and answers the two queries the loader reads back.

    It keeps a per-table row tally so `_check_counts`' `SELECT COUNT(*)` can be answered
    honestly rather than stubbed. That is what lets the count reconciliation be tested
    offline at all: a fake that always agreed would make the check untestable, which is the
    same shape as the tautological comparison the check replaced.
    """

    def __init__(self, owner: _FakeConnection) -> None:
        self.owner = owner
        self._row: dict[str, Any] | None = None

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, statement: str, params: object = None) -> int:
        self.owner.log.append(("execute", statement, [params]))
        if "COALESCE(MAX(" in statement:
            self._row = {"used": self.owner.highest_seq}
        elif "COUNT(*)" in statement:
            self._row = {"landed": self.owner.landed.get(self._table_of(statement), 0)}
        else:
            self._row = None
            if statement.startswith("INSERT INTO"):
                self.owner.landed[self._table_of(statement)] += 1
        return 1

    def executemany(self, statement: str, rows: list[tuple[object, ...]]) -> int:
        self.owner.log.append(("executemany", statement, list(rows)))
        if self.owner.deadlocks:
            # Mid-landing, which is where the measured deadlock actually struck: the second
            # loader's SELECT … FOR UPDATE returned without blocking and the INSERT lost.
            self.owner.deadlocks -= 1
            raise pymysql.err.OperationalError(1213, "Deadlock found when trying to get lock")
        self.owner.landed[self._table_of(statement)] += len(rows) - self.owner.undercount
        return len(rows)

    @staticmethod
    def _table_of(statement: str) -> str:
        match = _TABLE_IN_SQL.search(statement)
        assert match is not None, f"no quoted identifier in: {statement}"
        return match.group("name")

    def fetchone(self) -> dict[str, Any] | None:
        return self._row

    def fetchall(self) -> tuple[dict[str, Any], ...]:
        return ()


class _FakeConnection:
    """One ordered log across both call shapes, so "claimed first" is a real assertion.

    Recording `execute` and `executemany` in separate lists would make ordering between
    them unrecoverable, and the claim that the run row is written before the first bronze
    row is exactly an ordering claim.
    """

    def __init__(
        self,
        *,
        highest_seq: int = 0,
        undercount: int = 0,
        deadlocks: int = 0,
    ) -> None:
        self.highest_seq = highest_seq
        #: Rows per insert that the "server" silently fails to store, so the count
        #: reconciliation has something to disagree with.
        self.undercount = undercount
        #: How many landings deadlock before one is allowed through.
        self.deadlocks = deadlocks
        self.log: list[tuple[str, str, list[Any]]] = []
        self.landed: Counter[str] = Counter()
        self.commits = 0
        self.rollbacks = 0

    @property
    def statements(self) -> list[str]:
        return [statement for _, statement, _ in self.log]

    @property
    def inserted(self) -> list[tuple[str, list[Any]]]:
        return [(statement, rows) for kind, statement, rows in self.log if kind == "executemany"]

    def begin(self) -> None:
        """A fresh attempt starts from an empty table, exactly as a rollback leaves it."""
        self.landed.clear()

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def _land(
    connection: _FakeConnection,
    parsed: ParsedSnapshot,
    *,
    ingest_seq: int | None = None,
    contracts: Contracts | None = None,
) -> IngestRun:
    return land_snapshot(
        cast("Connection[DictCursor]", connection),
        parsed,
        ingest_seq=ingest_seq,
        contracts=contracts,
    )


# ── a parse with one record of everything, built rather than read ────────────


def make_parsed(
    *,
    historical_id: str | None = "deverra01",
    bats: int | None = 2,
    event_date: SaveDate = OPENING_DAY,
    undecoded_tails: int = 0,
) -> ParsedSnapshot:
    """One record per table, with the nullable fields controllable.

    Deliberately tiny. The claim under test is that the loader binds the declaration's
    columns, and one row proves that as well as eighteen thousand do.
    """
    snapshot = Snapshot(
        save_id="Synthetic",
        sim_date=SIM_DATE,
        ingest_seq=1,
        path=Path("nowhere"),
        files=(),
    )
    run = IngestRun(
        save_id=snapshot.save_id,
        sim_date=SIM_DATE,
        ingest_seq=1,
        human_team_id=4,
        snapshot=snapshot,
        sources=(SourceFile(name="teams.dat", size=10, sha256="a" * 64, version=25),),
        residual_bytes={"teams.dat": 0},
        parse_seconds=1.25,
    )
    return ParsedSnapshot(
        run=run,
        teams=TeamsFile(
            teams=(
                TeamRecord(
                    team_id=4,
                    city=None,
                    abbr="BOS",
                    nickname="Red Sox",
                    logo_filename=None,
                    full_name="Boston Red Sox",
                    colors=(1, 2, 3),
                    city_id=9,
                    park_id=11,
                    league_id=100,
                    sub_league_id=0,
                    nation_id=1,
                    human_team=True,
                    level=1,
                    parent_team_id=0,
                    historical_id=None,
                ),
            ),
            residual_bytes=0,
            sim_date=SIM_DATE,
        ),
        players=PlayersFile(
            players=(
                PlayerRecord(
                    player_id=31499,
                    first_name_index=7,
                    last_name_index=9,
                    date_of_birth=SaveDate(day=1, month=2, year=1996),
                    age=28,
                    nation_id=1,
                    city_of_birth_id=5,
                    weight=200,
                    height=73,
                    uniform_number=11,
                    experience=6,
                    team_id=4,
                    last_team_id=0,
                    organization_id=4,
                    last_organization_id=0,
                    league_id=-203,
                    last_league_id=0,
                    free_agent=False,
                    bats=bats,
                    throws=2,
                    historical_id=historical_id,
                ),
            ),
            residual_bytes=0,
            sim_date=SIM_DATE,
            content_digest="b" * 64,
            declared_record_count=None,
            undecoded_tails=undecoded_tails,
        ),
        rosters=RostersFile(
            memberships=(RosterMembership(team_id=4, player_id=31499, list_id=2),),
            unrostered=(),
            sim_date=SIM_DATE,
        ),
        names=NamesFile(
            names=(NameRecord(index=7, text="Rafael", category=39, usage=()),),
            residual_bytes=0,
            sim_date=SIM_DATE,
            declared_record_count=1,
        ),
        world=WorldFile(
            sim_date=SIM_DATE,
            divisions=(
                DivisionMembership(league_id=100, sub_league_id=0, division_id=0, team_ids=(4,)),
            ),
            calendar=(
                CalendarEvent(
                    seq=1,
                    league_id=100,
                    event_type=3,
                    start_date=event_date,
                    name="Opening Day",
                    event_over=0,
                    deleted=0,
                    needs_human_action=0,
                    real_sim_date=0,
                ),
            ),
            regions=(),
            file_bytes=0,
        ),
    )


@pytest.fixture(scope="module")
def contracts() -> Contracts:
    return load_contracts()


def _rows_for(connection: _FakeConnection, table: str) -> list[tuple[object, ...]]:
    for statement, rows in connection.inserted:
        if f"`{table}`" in statement:
            return rows
    raise AssertionError(f"{table} was never inserted into: {connection.inserted}")


# ── the declaration is the column list ───────────────────────────────────────


def test_every_bronze_table_is_written_with_its_declared_columns(contracts: Contracts) -> None:
    """One INSERT per table, and its column clause is the declaration's, in order."""
    connection = _FakeConnection()
    _land(connection, make_parsed(), ingest_seq=1, contracts=contracts)

    for table in contracts.tables:
        if table.name == INGEST_RUN_TABLE:
            continue  # a single-row execute, asserted separately below
        statement, rows = next(
            entry for entry in connection.inserted if f"`{table.name}`" in entry[0]
        )
        expected = ", ".join(f"`{column.name}`" for column in table.columns)
        assert expected in statement, f"{table.name} was not written with its declared columns"
        assert all(len(row) == len(table.columns) for row in rows)


def test_the_universal_triple_is_bound_first_on_every_row(contracts: Contracts) -> None:
    """Plan §2.3(d) at the value level: the universe, the date, and which attempt.

    Every declared key opens with these three, so a row whose first three bound values are
    anything else would be landing under a key that does not describe it.
    """
    connection = _FakeConnection()
    _land(connection, make_parsed(), ingest_seq=3, contracts=contracts)

    for table in contracts.tables:
        if table.name == INGEST_RUN_TABLE:
            continue
        for row in _rows_for(connection, table.name):
            assert row[:3] == ("Synthetic", SIM_DATE_TEXT, 3)


def test_structural_absence_binds_as_null_and_not_as_zero(contracts: Contracts) -> None:
    """`.claude/agents/data-engineer.md`: NULL, never zero.

    `city` is `None` on a club that has no city string and `historical_id` is `None` on a
    record whose tail was not decoded. Landing either as `0` or `""` would turn *"we did
    not read this"* into a value, which is the failure the rulebook names as worse than a
    gap because nothing downstream can tell the two apart.
    """
    connection = _FakeConnection()
    _land(connection, make_parsed(historical_id=None, bats=None), ingest_seq=1, contracts=contracts)

    team = contracts.table("bronze_team")
    row = _rows_for(connection, "bronze_team")[0]
    assert row[[column.name for column in team.columns].index("city")] is None

    player = contracts.table("bronze_player")
    names = [column.name for column in player.columns]
    player_row = _rows_for(connection, "bronze_player")[0]
    assert player_row[names.index("historical_id")] is None
    assert player_row[names.index("bats")] is None


def test_a_fictional_players_empty_id_is_not_collapsed_into_null(contracts: Contracts) -> None:
    """The other side of the same distinction, and it is a different fact.

    `parser/players.py` is explicit that a fictional player carries `""` — a zero-length
    prefix, present and empty — while NULL means the tail was never decoded. A loader that
    normalised one into the other would make *"this player has no real-world counterpart"*
    indistinguishable from *"we did not read this record"*.
    """
    connection = _FakeConnection()
    _land(connection, make_parsed(historical_id=""), ingest_seq=1, contracts=contracts)

    names = [column.name for column in contracts.table("bronze_player").columns]
    assert _rows_for(connection, "bronze_player")[0][names.index("historical_id")] == ""


def test_a_negative_league_id_lands_as_it_was_read(contracts: Contracts) -> None:
    """The six signed id columns, at the value level rather than the type level.

    The export writes `league_id` negative on 176 real records and the walker signs those
    reads on purpose. An unsigned column turns -203 into a very large positive number or
    clamps it to 0 — and 0 is what the walker defines as "no team".
    """
    connection = _FakeConnection()
    _land(connection, make_parsed(), ingest_seq=1, contracts=contracts)

    names = [column.name for column in contracts.table("bronze_player").columns]
    assert _rows_for(connection, "bronze_player")[0][names.index("league_id")] == -203


def test_the_name_space_discriminator_lands_its_literal(contracts: Contracts) -> None:
    """One index space was measured; the column stays because the key is correct either way."""
    names = [column.name for column in contracts.table("bronze_name").columns]
    connection = _FakeConnection()
    _land(connection, make_parsed(), ingest_seq=1, contracts=contracts)
    assert _rows_for(connection, "bronze_name")[0][names.index("name_space")] == "all"


def test_a_label_row_lands_for_every_declared_column(contracts: Contracts) -> None:
    """`bronze_field_label` is a record about the landing and it must be complete."""
    connection = _FakeConnection()
    _land(connection, make_parsed(), ingest_seq=1, contracts=contracts)

    expected = sum(len(table.columns) for table in contracts.tables)
    assert len(_rows_for(connection, "bronze_field_label")) == expected


# ── and what happens when the two disagree ───────────────────────────────────


def _with_extra_column(contracts: Contracts, table_name: str) -> Contracts:
    """The same declaration with one undeclared-by-any-builder column added."""
    tables = tuple(
        replace(
            table,
            columns=(
                *table.columns,
                Column(name="scouted_potential", column_type="u8", nullable=True, provenance=True),
            ),
        )
        if table.name == table_name
        else table
        for table in contracts.tables
    )
    return replace(contracts, tables=tables)


def test_a_column_the_loader_does_not_fill_is_refused(contracts: Contracts) -> None:
    """**CF22, in the direction that used to land a silent NULL.**

    Adding a column to `tables.toml` and forgetting the loader is the easy mistake: the
    DDL emits it, the insert omits it, MySQL fills the default, and a column nobody wrote
    reads as data nobody questions. It now refuses on the first row, naming the column.
    """
    connection = _FakeConnection()
    with pytest.raises(LoadError) as raised:
        _land(
            connection,
            make_parsed(),
            ingest_seq=1,
            contracts=_with_extra_column(contracts, "bronze_team"),
        )
    assert "scouted_potential" in str(raised.value)
    assert connection.rollbacks == 1 and connection.commits == 0


def test_a_declared_table_nobody_builds_is_refused(contracts: Contracts) -> None:
    """The same failure one level up: a table declared and never filled looks landed.

    An empty table is indistinguishable from a table whose population happens to be zero,
    which is exactly how a report ends up truthfully saying there are no divisions.
    """
    extra = Table(
        name="bronze_unbuilt",
        grain="one row per team per save per snapshot",
        key=("save_id", "sim_date", "ingest_seq", "team_id"),
        columns=(
            Column(name="save_id", column_type="text", nullable=False, length=64, provenance=True),
            Column(name="sim_date", column_type="date", nullable=False, provenance=True),
            Column(name="ingest_seq", column_type="u32", nullable=False, provenance=True),
            Column(name="team_id", column_type="u32", nullable=False, provenance=True),
        ),
        source=("teams.dat",),
        walker="nowhere",
        collation="utf8mb4_bin",
        coverage="none",
    )
    with pytest.raises(LoadError, match="bronze_unbuilt"):
        _land(
            _FakeConnection(),
            make_parsed(),
            ingest_seq=1,
            contracts=replace(contracts, tables=(*contracts.tables, extra)),
        )


def test_nothing_commits_when_a_table_refuses(contracts: Contracts) -> None:
    """One transaction, so a half-landed universe is not a state the warehouse can hold."""
    connection = _FakeConnection()
    with pytest.raises(LoadError):
        _land(
            connection,
            make_parsed(),
            ingest_seq=1,
            contracts=_with_extra_column(contracts, "bronze_player"),
        )
    assert connection.commits == 0


# ── the run row: claimed first, and carrying what the run measured ───────────


def test_the_run_row_is_claimed_before_any_bronze_row(contracts: Contracts) -> None:
    """A colliding load should fail on one small insert, not part-way through 264,095.

    It is also the ordering that makes the refusal meaningful: the primary key is what
    refuses, so claiming it late would mean bronze rows were already written when the
    collision surfaced and the rollback had more to undo.
    """
    connection = _FakeConnection()
    _land(connection, make_parsed(), ingest_seq=1, contracts=contracts)

    writes = [index for index, sql in enumerate(connection.statements) if "INSERT INTO" in sql]
    assert len(writes) > 1, "only one INSERT was issued; nothing is being ordered here"
    assert f"`{INGEST_RUN_TABLE}`" in connection.statements[writes[0]], (
        f"the first write was {connection.statements[writes[0]]!r}, not the run row"
    )


def test_an_omitted_seq_is_allocated_from_the_warehouse(contracts: Contracts) -> None:
    """`None` means "take the next one", and the read is a locking one.

    A snapshot taken into a temporary directory always allocates 1 on the filesystem side,
    so landing that number blindly would collide with an unrelated earlier landing. The
    `FOR UPDATE` matters as much as the maximum: computed in a prior statement, two
    concurrent loaders allocate the same sequence and land two row sets under one key.
    """
    connection = _FakeConnection(highest_seq=4)
    run = _land(connection, make_parsed(), contracts=contracts)

    assert run.ingest_seq == 5
    allocation = next(sql for sql in connection.statements if "COALESCE(MAX(" in sql)
    assert "FOR UPDATE" in allocation


def test_the_returned_run_carries_the_counts_that_landed(contracts: Contracts) -> None:
    """So a caller never has to assume what was written, or read it off a log line."""
    run = _land(_FakeConnection(), make_parsed(), ingest_seq=1, contracts=contracts)

    assert run.row_counts["bronze_team"] == 1
    assert run.row_counts["bronze_player"] == 1
    assert run.row_counts[INGEST_RUN_TABLE] == 1
    assert run.row_counts["bronze_field_label"] == sum(
        len(table.columns) for table in contracts.tables
    )


def test_the_run_values_keep_the_repeating_groups_per_file() -> None:
    """`residual_bytes` is JSON per file, and summing it would hide a real failure.

    The accounting tier differs by file by design — strict for `names.dat` alone,
    diagnostic for `teams.dat` and `players.dat`, region-accounted for `world.dat`. A
    single total makes a strict-tier failure arithmetically indistinguishable from an
    expected diagnostic residual, and *which walker left bytes unaccounted for* stops
    being answerable.
    """
    values = ingest_run_values(make_parsed().run, ingest_seq=2)

    assert values["ingest_seq"] == 2
    assert '"teams.dat"' in str(values["residual_bytes"])
    assert '"sha256"' in str(values["source_files"])
    ingested_at = values["ingested_at"]
    assert isinstance(ingested_at, datetime)
    assert ingested_at.tzinfo is not None, "a naive ingestion timestamp is a ruff DTZ bug"


def test_an_unmeasured_parse_stays_null_rather_than_becoming_zero() -> None:
    """NULL is "not measured"; 0.000 is "instantaneous". They must not read alike."""
    run = replace(make_parsed().run, parse_seconds=None)
    assert ingest_run_values(run, ingest_seq=1)["parse_seconds"] is None


def test_a_zero_date_is_refused_for_a_key_column() -> None:
    """A save writes 0/0/0 where a date does not apply, and that is structural absence.

    `sim_date` is a key column, so a 0/0/0 reaching it would key a whole snapshot on a
    date that does not exist. `date(0, 0, 0)` is not constructible and MySQL's
    `'0000-00-00'` is only accepted under a permissive `sql_mode`, so the refusal is made
    here where it can name the value.
    """
    with pytest.raises(ValueError, match="not a calendar date"):
        as_sql_date(NO_DATE)
    assert as_sql_date(SIM_DATE) == SIM_DATE_TEXT


def test_the_same_zero_date_becomes_null_for_an_attribute() -> None:
    """The other converter, and the distinction is the whole point of having two.

    The strict one's reasoning — "a key column can never legitimately hold one" — is true
    of key columns and of nothing else. Applied to an attribute it turns absence into a
    crash, which is neither of the two things the rulebook allows absence to become.
    """
    assert nullable_sql_date(NO_DATE) is None
    assert nullable_sql_date(SIM_DATE) == SIM_DATE_TEXT


def test_a_date_less_calendar_event_lands_null_rather_than_aborting(
    contracts: Contracts,
) -> None:
    """**A walker-sanctioned value must have somewhere to land.**

    `parser/world.py`'s scanner accepts `year == 0` for a calendar record on purpose, and
    says why: a calendar record with no date is structural absence. Landing it through the
    key-column converter aborted the whole ~300,000-row ingest over one row, and reported
    it with a message about keys — so absence became neither NULL nor zero but a crash, in
    a module whose own docstring names the first two as the only options.
    """
    connection = _FakeConnection()
    _land(connection, make_parsed(event_date=NO_DATE), ingest_seq=1, contracts=contracts)

    names = [column.name for column in contracts.table("bronze_league_event").columns]
    assert _rows_for(connection, "bronze_league_event")[0][names.index("start_date")] is None
    assert connection.commits == 1


def test_the_calendar_start_date_is_declared_nullable(contracts: Contracts) -> None:
    """The declaration has to agree, or a corrected loader still has nowhere to put it."""
    assert contracts.table("bronze_league_event").column("start_date").nullable


# ── the gate the parser delegates here ───────────────────────────────────────


def test_a_snapshot_with_undecoded_tails_refuses_to_land(contracts: Contracts) -> None:
    """**`parser/players.py` delegates this refusal outright; Phase 8b is the delegate.**

    "On every save on disk that count is zero; a nonzero count means the format changed and
    the landing gate must refuse, not guess." Before this, the gate did not exist: a
    snapshot with a moved tail layout landed and committed, with `bats`, `throws` and
    `historical_id` NULL for an unknown fraction of records and a run row that looked
    perfectly healthy.
    """
    with pytest.raises(UndecodedRecords, match="3 player records"):
        check_decoded(make_parsed(undecoded_tails=3).players)


def test_a_fully_decoded_walk_passes_the_gate() -> None:
    """The other half, so the gate cannot be satisfied by refusing everything."""
    check_decoded(make_parsed().players)


# ── the sim dates the five walkers each read for themselves ──────────────────


def test_files_that_agree_about_the_sim_date_pass() -> None:
    check_sim_dates(SIM_DATE, {TEAMS_FILE: SIM_DATE, NAMES_FILE: SIM_DATE})


def test_a_file_declaring_a_different_sim_date_is_refused() -> None:
    """**A mixed snapshot, which lands wrong rows rather than raising.**

    Every bronze row is keyed on one date, read from `teams.dat`. The claim that every
    record file carries the same one is labelled *measured* in `snapshot.py` — and in this
    project a belief nothing checks is a task. Proven reachable in review: swapping in
    another save's `names.dat` and `world.dat` produced no exception at all, and 264,095
    name rows would have landed under a date that does not describe them.
    """
    other = SaveDate(day=18, month=3, year=2024)
    with pytest.raises(SnapshotDateMismatch) as raised:
        check_sim_dates(SIM_DATE, {TEAMS_FILE: SIM_DATE, NAMES_FILE: other})

    message = str(raised.value)
    assert NAMES_FILE in message and "2024-03-18" in message and "2024-03-07" in message
    assert TEAMS_FILE not in message, "only the disagreeing files should be named"


# ── contention, which costs a retry and not a landing ────────────────────────


def test_a_deadlocked_landing_retries_and_succeeds(contracts: Contracts) -> None:
    """A deadlock rolls everything back, so retrying is safe — nothing was committed.

    Measured in review: two concurrent loaders deadlock deterministically, and `FOR UPDATE`
    does not serialise them. Without the retry, any second writer — another agent, a CI
    runner, an operator re-driving a slow ingest — costs the whole multi-second landing.
    """
    connection = _FakeConnection(deadlocks=1)
    run = _land(connection, make_parsed(), contracts=contracts)

    assert run.ingest_seq == 1
    assert connection.commits == 1, "the retry did not commit"
    assert connection.rollbacks == 1, "the failed attempt did not roll back"


def test_persistent_contention_gives_up_by_a_different_name(contracts: Contracts) -> None:
    """`ConcurrentLandingError`, never `IngestRunExists`.

    The two mean opposite things — *somebody else is writing right now* against *this
    snapshot is already in the warehouse* — and telling an operator the second when the
    first is true sends them looking for a landing that never happened.
    """
    connection = _FakeConnection(deadlocks=99)
    with pytest.raises(ConcurrentLandingError, match="Nothing was committed"):
        _land(connection, make_parsed(), contracts=contracts)
    assert connection.commits == 0


# ── the counts in the run row are read back, not restated ────────────────────


def test_a_table_holding_fewer_rows_than_claimed_refuses(contracts: Contracts) -> None:
    """**The reconciliation, given something it can actually disagree with.**

    Comparing `executemany`'s return value to `len(rows)` compares two derivations of one
    Python list and can fire only on a driver anomaly. Counting the rows back out of the
    schema can fire on a landing that genuinely holds a different number — which is what
    the docstring promised and what Phase 9 and Phase 11 are specified to trust.
    """
    connection = _FakeConnection(undercount=1)
    with pytest.raises(LoadError, match="misdescribe its own landing"):
        _land(connection, make_parsed(), ingest_seq=1, contracts=contracts)
    assert connection.commits == 0 and connection.rollbacks == 1


def test_a_team_with_the_wrong_number_of_colours_refuses(contracts: Contracts) -> None:
    """Three ARGB colours per club, asserted rather than sliced.

    A club with two would otherwise land whatever followed as its third colour, which is a
    plausible number rather than an error.
    """
    parsed = make_parsed()
    broken = replace(parsed.teams.teams[0], colors=(1, 2))
    parsed = replace(parsed, teams=replace(parsed.teams, teams=(broken,)))

    with pytest.raises(LoadError, match="colours"):
        _land(_FakeConnection(), parsed, ingest_seq=1, contracts=contracts)


# ── append-only, enforced rather than asserted in prose ──────────────────────

#: Statements that would mutate or remove a landed row, matched as SQL **shapes** rather
#: than as keywords. A bare `\bDROP\b` flagged `ddl.py`'s "drop them from the vocabulary"
#: on the first run — the keyword alone is ordinary English, and a guard that fires on
#: prose is a guard somebody will delete. `FOR UPDATE` is exempt by construction: the
#: update form requires a `SET`, which a locking read does not have.
_MUTATING_SQL = re.compile(
    r"DELETE\s+FROM"
    r"|DROP\s+(TABLE|SCHEMA|DATABASE|INDEX|COLUMN)"
    r"|TRUNCATE\s+TABLE"
    r"|REPLACE\s+INTO"
    r"|ON\s+DUPLICATE\s+KEY"
    # The table name may be an interpolation, which joining leaves as whitespace — so the
    # name between UPDATE and SET is optional. `SET` is what distinguishes a write from the
    # `FOR UPDATE` locking read, and a locking read never has one.
    r"|UPDATE\s+\S*\s*SET\b",
    re.IGNORECASE,
)


def scan_for_mutation(source: str, filename: str = "<test>") -> list[str]:
    """Flag SQL that mutates, but only where a string literal is handed to a call.

    **Judged at the call site, exactly as the `historical_id` scanner is judged**, and for
    the reason that scanner learned the hard way: a line-based version of this guard
    flagged two docstrings on its first run — including the one in `warehouse/__init__.py`
    that states the very rule — which is precisely how a guard gets loosened until it
    catches nothing. A statement reaches MySQL through a call or it does not run.

    The known hole is the same one too: SQL assembled from fragments, or bound to a module
    constant and passed later, is invisible here. This is the mechanical backstop under a
    convention, not a proof.
    """
    flagged: list[str] = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if not isinstance(node, ast.Call):
            continue
        for argument in [*node.args, *(keyword.value for keyword in node.keywords)]:
            # An argument's literal pieces are joined before matching, because an f-string
            # splits `UPDATE {table} SET x` into constants that each look harmless. The
            # interpolations become a space, which is exactly the join a reader would make.
            statement = " ".join(_string_pieces(argument))
            if _MUTATING_SQL.search(statement):
                line = getattr(argument, "lineno", 0)
                flagged.append(f"{filename}:{line}: {statement.strip()[:80]}")
    return flagged


def _string_pieces(node: ast.expr) -> list[str]:
    """Every literal string inside an expression, f-strings and concatenations included."""
    pieces: list[str] = []
    for inner in ast.walk(node):
        if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
            pieces.append(inner.value)
    return pieces


def _warehouse_sources() -> list[Path]:
    modules = sorted((REPO_ROOT / "src" / "ootp_ai" / "warehouse").glob("*.py"))
    assert modules, "the warehouse package has no modules — the scan root is wrong"
    return modules


def test_no_module_in_the_warehouse_can_mutate_a_landed_row() -> None:
    """**The invariant this phase is named after, given a scanner like every other one.**

    `warehouse/__init__.py` states that nothing here holds a DELETE or an UPDATE path, and
    `load.py` explains that a delete helper written "just for tests" is how the property
    quietly stops being true — which is why `purge_snapshot` lives under `tests/`. Every
    other load-bearing rule in this repo has a mechanical guard behind it; this one had
    prose. The first convenience `purge()` added because a script needed it would break
    append-only with a green suite.
    """
    offenders: list[str] = []
    for module in _warehouse_sources():
        offenders.extend(scan_for_mutation(module.read_text(encoding="utf-8"), module.name))
    assert offenders == [], (
        "a warehouse module can now mutate a landed row, and append-only is the property "
        "that makes a past decision re-examinable:\n" + "\n".join(offenders)
    )


MUTATIONS = {
    "a delete": 'cursor.execute(f"DELETE FROM {quote_ident(name)} WHERE save_id = %s")',
    "an update": 'cursor.execute("UPDATE ingest_run SET parse_seconds = 0")',
    "an update split by an f-string": 'cursor.execute(f"UPDATE {quote_ident(t)} SET city = %s")',
    "an upsert": 'cursor.execute("INSERT INTO bronze_team ... ON DUPLICATE KEY UPDATE city = %s")',
    "a truncate": 'cursor.execute("TRUNCATE TABLE bronze_name")',
    "a drop": 'cursor.execute("DROP TABLE bronze_name")',
}

INNOCENT = {
    "the locking read": 'cursor.execute("SELECT MAX(ingest_seq) FROM ingest_run FOR UPDATE")',
    "an insert": 'cursor.execute("INSERT INTO bronze_team (save_id) VALUES (%s)")',
    "prose about the rule": '"""Nothing here holds a DELETE or an UPDATE path."""',
    "a comment": "# never DELETE from a landed table\nvalue = 1\n",
    # The real false positive this scanner produced on its first run.
    "English that happens to say drop": (
        'raise DdlError(f"column {name} declares {kind}; add it to TYPE_MAP or drop it '
        'from the vocabulary")'
    ),
}


@pytest.mark.parametrize("label", sorted(MUTATIONS))
def test_the_append_only_scan_catches_a_mutation(label: str) -> None:
    """A guard nobody has seen fail is decoration (plan §4.4)."""
    assert scan_for_mutation(MUTATIONS[label]), f"{label} was not flagged"


@pytest.mark.parametrize("label", sorted(INNOCENT))
def test_the_append_only_scan_does_not_cry_wolf(label: str) -> None:
    """It already did once, on this module's own docstrings. That is why it uses the AST."""
    assert scan_for_mutation(INNOCENT[label]) == [], f"{label} was flagged and should not be"
