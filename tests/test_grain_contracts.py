"""AC4 and AC5 — the declared grain, the emitted key, and the grain the warehouse holds.

Three guards about the same failure: a table whose prose says one thing and whose key does
another, so a query returns fewer rows than the data holds and looks like it worked.

Two of them are offline and run in CI — the declaration against the emitted DDL, and the
`historical_id` join scan. The third is `-m gamedata` and lands a real snapshot, because
the declaration agreeing with the DDL says nothing about whether the loader wrote the rows
that shape describes.

## Why the grain check reads two artifacts and not one

`.claude/agents/data-engineer.md` requires a dataset to state its grain in prose *and*
enforce it with a uniqueness test, "and the two must agree". This asserts the agreement
against the **emitted DDL** rather than against the declaration alone, because the
declaration agreeing with itself is not the claim worth making — the claim worth making is
that the schema MySQL will hold is the schema the sentence describes. `warehouse/ddl.py`
sits between them, so a bug there is exactly what this catches.

## And the second guard, which is about a different kind of wrong

`historical_id` is the Lahman/BBRef id, and **1,920 of 18,072 active players carry one**.
`.claude/agents/data-engineer.md:107-109` names the consequence of joining on it: *"A join
on the wrong one silently drops the fictional majority and looks like it worked."* Ten
percent of a roster is enough rows to look like a working report.

So no join in `src/ootp_ai/` may use it — and the scan is scoped to `src/` **because
`tests/` legitimately joins on it**. `tests/test_names_join_boston.py` matches parsed names
against `players.csv` on the LahmanID, which is ground truth and is the whole point of that
test. An unscoped guard would forbid its own validation, and
`test_the_guard_would_flag_the_test_that_legitimately_joins` proves the scoping is
load-bearing rather than decorative.

## What the join scanner cannot see

- **A join whose SQL is assembled from fragments, or bound to a name first.**
  `"... ON p." + column + " = ..."` defeats it, and so does a module constant passed to
  `execute()` later: SQL is judged only where a string literal is handed to a call.
  Scanning every string constant instead was tried first and flagged six **docstrings**,
  two of which exist to explain this very rule — which is how a guard gets loosened until
  it catches nothing.
- **A join through a helper.** `match_on(players, key=lambda p: p.historical_id)` passes —
  the value reaches a callable as a plain argument and nothing here does dataflow.
- **A join keyed on the string rather than the attribute.** `row["historical_id"]` is
  deliberately *not* flagged: reading a column by name is how bronze lands it, and flagging
  it would fire on the loader that legitimately writes the column.

Each is a known hole rather than an unnoticed one. The categorical protection is that
`historical_id` is declared a nullable attribute in `tables.toml`, and the report layer
routes through `contracts/policy.py`; this scan is the mechanical backstop under that.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from fixtures.warehouse import landed_probe, settings_or_skip, warehouse_or_skip
from ootp_ai.config import Settings
from ootp_ai.contracts.loader import Contracts, load_contracts
from ootp_ai.ingest import IngestRun, ParsedSnapshot
from ootp_ai.warehouse.ddl import create_all_statements, create_table_statement
from ootp_ai.warehouse.ingest_run import as_sql_date
from ootp_ai.warehouse.load import landed_tables
from ootp_ai.warehouse.sql import quote_ident

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "src" / "ootp_ai"

#: `world.dat` reaches MLB's six divisions and stops. Pinned so a walk that started
#: finding more — or fewer — says so rather than quietly changing the table's meaning.
MLB_DIVISIONS = 6

#: The eight tables Phase 8a promised. Spelled out rather than counted, because "eight
#: tables" is satisfied by eight wrong ones.
DECLARED_TABLES = (
    "bronze_team",
    "bronze_player",
    "bronze_team_roster",
    "bronze_name",
    "bronze_division_team",
    "bronze_league_event",
    "bronze_field_label",
    "ingest_run",
)

_PRIMARY_KEY = re.compile(r"PRIMARY KEY \(([^)]*)\)")
_COLUMN_LINE = re.compile(r"^\s*`(?P<name>[^`]+)`\s+(?P<sql>.+?)\s+(?P<null>NOT NULL|NULL),?$")


@pytest.fixture(scope="module")
def contracts() -> Contracts:
    return load_contracts()


def _emitted_key(statement: str) -> tuple[str, ...]:
    match = _PRIMARY_KEY.search(statement)
    assert match is not None, f"no PRIMARY KEY in:\n{statement}"
    return tuple(part.strip().strip("`") for part in match.group(1).split(","))


def _emitted_columns(statement: str) -> dict[str, tuple[str, bool]]:
    """Column name -> (rendered type, nullable), read back out of the emitted SQL."""
    columns: dict[str, tuple[str, bool]] = {}
    for line in statement.splitlines():
        match = _COLUMN_LINE.match(line)
        if match is not None:
            columns[match.group("name")] = (match.group("sql"), match.group("null") == "NULL")
    return columns


# ── AC4: the prose, the key and the DDL are one statement ────────────────────


def test_the_declaration_names_the_eight_tables_the_phase_promised(contracts: Contracts) -> None:
    assert tuple(table.name for table in contracts.tables) == DECLARED_TABLES


def test_every_table_states_a_grain_its_key_implies(contracts: Contracts) -> None:
    """The declaration's own check, spent here rather than trusted.

    `loader.py` refuses a mismatch at load time, so a green `load_contracts()` already
    proves it. This restates the union explicitly so a reader of the *test* can see what
    "the prose equals the key" means without reading the loader.
    """
    for table in contracts.tables:
        implied: set[str] = set()
        for dimension in table.grain_dimensions:
            implied.update(contracts.dimensions[dimension])
        assert implied == set(table.key), (
            f"{table.name}: {table.grain!r} implies {sorted(implied)}, key is {list(table.key)}"
        )


def test_every_key_opens_with_the_provenance_triple_in_order(contracts: Contracts) -> None:
    """Plan §2.3(d), which was prose with nothing holding it.

    Every bronze key carries the universe, the in-game date, and which attempt at that
    date. The grain sentence cannot enforce this on its own: dimensions resolve through a
    map declared in the same file, so sentence and key can always be brought back into
    agreement by editing the map. The panel proved it — adding `date = ["sim_date"]`,
    restating `bronze_name`'s grain "per save per date" and dropping `ingest_seq` loads
    cleanly and emits a key without it.

    What that costs is the case the amendment exists for: a second snapshot of an
    unchanged sim date — the operator executing a GM action and proving it landed — either
    collides on the primary key or overwrites the pre-action state.

    **Order, not membership.** A primary key is ordered and MySQL indexes it that way, so
    this also pins the leftmost-prefix behaviour every later query depends on.
    """
    for table in contracts.tables:
        assert table.key[:3] == ("save_id", "sim_date", "ingest_seq"), (
            f"{table.name} keys on {list(table.key)}; §2.3(d) requires every key to open "
            "with (save_id, sim_date, ingest_seq)"
        )


def test_the_emitted_key_is_the_declared_key(contracts: Contracts) -> None:
    """Order included: a primary key is an ordered thing and MySQL indexes it that way."""
    for table, statement in zip(contracts.tables, create_all_statements(contracts), strict=True):
        assert _emitted_key(statement) == table.key, f"{table.name} emitted the wrong key"


def test_every_primary_key_column_is_emitted_not_null(contracts: Contracts) -> None:
    """`COUNT(DISTINCT a, b, c)` drops tuples containing NULL.

    A nullable key column would make every grain test count fewer rows than the table
    holds and pass — green, and wrong, in the direction nobody checks.
    """
    for table in contracts.tables:
        columns = _emitted_columns(create_table_statement(table))
        for name in table.key:
            assert name in columns, f"{table.name}: key column {name} was not emitted"
            assert not columns[name][1], f"{table.name}.{name} is a key column emitted NULL"


def test_a_nullable_attribute_is_still_emitted_nullable(contracts: Contracts) -> None:
    """The other half, so the NOT NULL assertion above cannot pass by emitting all-NOT NULL.

    A guard that would pass on a schema with no nullable columns at all is not reading the
    declaration, and structural absence must survive landing as NULL rather than as zero.
    """
    columns = _emitted_columns(create_table_statement(contracts.table("bronze_player")))
    # NOT "NULL for fictional players" — `parser/players.py` is explicit that a fictional
    # player's historical_id is `""`, never None. NULL means the record's tail was not
    # decoded, which is a different fact, and collapsing the two in 8b would turn "we did
    # not read this" into "this player has no real-world counterpart".
    assert columns["historical_id"][1], "a record whose tail was not decoded lands NULL"
    assert columns["bats"][1], "an unread handedness is absent, not a value"


def test_name_bearing_tables_collate_binary(contracts: Contracts) -> None:
    """`utf8mb4_0900_ai_ci` scores `Ramírez == Ramirez` as a match.

    The schemas are created with that collation, so any table holding a name has to
    override it or an "exact" comparison run in SQL is not exact at all.
    """
    for name in ("bronze_name", "bronze_team", "bronze_player"):
        statement = create_table_statement(contracts.table(name))
        assert "COLLATE=utf8mb4_bin" in statement, f"{name} does not collate binary"


def test_every_column_that_claims_a_field_resolves_to_one(contracts: Contracts) -> None:
    """Provenance, so `bronze_field_label` can land a belief rather than a NULL."""
    for table in contracts.tables:
        for column in table.columns:
            if column.field is not None:
                entry = contracts.field(column.field)
                assert entry.name == column.field


def test_the_two_world_tables_are_declared(contracts: Contracts) -> None:
    """Phase 5b's output, added to the declaration by the 2026-08-19 amendment.

    Without `bronze_division_team` there is no division source in the warehouse at all —
    `teams.dat` provably does not carry `division_id` — so Phase 10's standings could not
    group by division no matter how it was written.
    """
    divisions = contracts.table("bronze_division_team")
    assert divisions.source == ("world.dat",)
    assert "division_id" in divisions.key

    events = contracts.table("bronze_league_event")
    assert "seq" in events.key, "the calendar's key is seq; the readable alternative loses 458 rows"


def test_the_field_map_no_longer_declares_itself_incomplete() -> None:
    """`[meta].incomplete` named `teams.dat` and `world.dat`; Phase 8a is the backfill."""
    from ootp_ai.contracts.loader import read_declaration_text

    text = read_declaration_text("field_map.toml")
    assert "incomplete = []" in text, "the field map still declares an outstanding backfill"


def test_every_landed_source_file_has_field_entries(contracts: Contracts) -> None:
    """The backfill, asserted by content rather than by the meta key alone."""
    sources = {entry.source for entry in contracts.fields}
    for expected in ("teams.dat", "players.dat", "names.dat", "world.dat"):
        assert expected in sources, f"{expected} has no field-map entries"


# ── the historical_id join scanner ───────────────────────────────────────────

_JOIN_KEY = "historical_id"


def _is_sql_naming_the_join_key(text: str) -> bool:
    """True for a string that is a query joining or selecting on `historical_id`.

    Two markers, not one: prose in this repo says "from" and "select" constantly, and the
    pair that means SQL is `select`+`from` or `join`+`on`.
    """
    lowered = text.lower()
    if _JOIN_KEY not in lowered:
        return False
    return ("select" in lowered and "from" in lowered) or ("join" in lowered and " on " in lowered)


def _names_the_join_key(node: ast.expr) -> bool:
    """True if this expression is the `historical_id` VALUE (not the string "historical_id")."""
    if isinstance(node, ast.Attribute):
        return node.attr == _JOIN_KEY
    if isinstance(node, ast.Name):
        return node.id == _JOIN_KEY or node.id.endswith(f"_{_JOIN_KEY}")
    if isinstance(node, ast.BoolOp):
        # `player.historical_id or ""` — the idiom for feeding a lookup a total key.
        return any(_names_the_join_key(value) for value in node.values)
    return False


class _JoinScanner(ast.NodeVisitor):
    """Flag the three shapes a join on `historical_id` actually takes here."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    def _flag(self, node: ast.AST, what: str) -> None:
        line = getattr(node, "lineno", 0)
        self.violations.append(f"{self.filename}:{line}: {what}")

    def visit_Dict(self, node: ast.Dict) -> None:
        for key in node.keys:
            if key is not None and _names_the_join_key(key):
                self._flag(node, f"dict keyed on {_JOIN_KEY}")
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        if _names_the_join_key(node.key):
            self._flag(node, f"dict comprehension keyed on {_JOIN_KEY}")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if _names_the_join_key(node.slice):
            self._flag(node, f"lookup subscripted by {_JOIN_KEY}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"get", "pop", "setdefault"}
            and node.args
            and _names_the_join_key(node.args[0])
        ):
            self._flag(node, f"mapping lookup on {_JOIN_KEY}")
        # SQL is judged only where it is HANDED TO SOMETHING. Scanning every string
        # constant flagged six docstrings on the first run — including two that exist to
        # explain this very rule — which is precisely how a guard gets loosened until it
        # catches nothing. A query reaches MySQL through a call or it does not run.
        for argument in node.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                if _is_sql_naming_the_join_key(argument.value):
                    self._flag(argument, f"SQL naming {_JOIN_KEY}")
        self.generic_visit(node)


def scan_source(source: str, filename: str = "<test>") -> list[str]:
    scanner = _JoinScanner(filename)
    scanner.visit(ast.parse(source, filename=filename))
    return scanner.violations


OFFENDERS = {
    "dict comprehension": "index = {player.historical_id: player for player in players}\n",
    "dict literal": "index = {player.historical_id: player}\n",
    "subscript lookup": "matched = by_lahman[record.historical_id]\n",
    "mapping get": 'want = csv_names.get(player.historical_id or "")\n',
    "sql join": (
        'cursor.execute("SELECT p.name FROM players p '
        'JOIN roster r ON p.historical_id = r.historical_id")\n'
    ),
}

INNOCENTS = {
    "landing the column": "row = (player.player_id, player.historical_id)\n",
    "a None check": "if player.historical_id is None:\n    pass\n",
    "reading it by column name": 'value = row["historical_id"]\n',
    "naming it in a column list": 'columns = ["player_id", "historical_id"]\n',
    "joining on the right key": "index = {player.player_id: player for player in players}\n",
    "prose about the rule": '"""Never join on historical_id: select from the 10.6% and you lose the rest."""\n',
}


@pytest.mark.parametrize("label", sorted(OFFENDERS))
def test_the_scanner_flags_a_synthetic_join(label: str) -> None:
    assert scan_source(OFFENDERS[label]), f"{label} was not flagged"


@pytest.mark.parametrize("label", sorted(INNOCENTS))
def test_the_scanner_does_not_cry_wolf(label: str) -> None:
    """A guard that fires on legitimate code gets loosened, and a loosened guard is worse."""
    assert scan_source(INNOCENTS[label]) == [], f"{label} was flagged and should not be"


def source_modules() -> list[Path]:
    modules = sorted(SCAN_ROOT.rglob("*.py"))
    assert modules, f"no modules found under {SCAN_ROOT} — the scan root is wrong"
    return modules


def test_no_module_in_src_joins_on_the_historical_id() -> None:
    violations: list[str] = []
    for module in source_modules():
        violations.extend(
            scan_source(
                module.read_text(encoding="utf-8"), module.relative_to(REPO_ROOT).as_posix()
            )
        )
    assert violations == [], "a join on historical_id drops the fictional majority:\n" + "\n".join(
        violations
    )


def test_the_guard_would_flag_the_test_that_legitimately_joins() -> None:
    """**Why the scan is scoped to `src/`, demonstrated rather than asserted.**

    `tests/test_names_join_boston.py` joins parsed names to `players.csv` on the LahmanID
    — that join *is* the ground truth Tier A rests on. Running the guard over `tests/`
    would forbid the validation the guard exists to protect, so the scoping is a
    correctness requirement, not an optimisation. If this ever goes green, that test has
    stopped joining on the id and this rationale needs rewriting.
    """
    boston = REPO_ROOT / "tests" / "test_names_join_boston.py"
    assert scan_source(boston.read_text(encoding="utf-8"), boston.name), (
        "the Tier A test no longer joins on the LahmanID"
    )


# ── AC5: the grain, asserted against rows that are really in MySQL ───────────
#
# Everything above compares two artifacts and needs no database. What follows lands a real
# snapshot and asks the warehouse itself, because the declaration agreeing with the DDL
# says nothing about whether the loader wrote the rows that shape describes.


@pytest.fixture(scope="module")
def settings() -> Settings:
    return settings_or_skip()


@pytest.fixture(scope="module")
def warehouse(settings: Settings) -> Iterator[Connection[DictCursor]]:
    with warehouse_or_skip(settings) as connection:
        yield connection


@pytest.fixture(scope="module")
def landed(
    settings: Settings, warehouse: Connection[DictCursor]
) -> Iterator[tuple[ParsedSnapshot, IngestRun]]:
    """One real landing, shared by every test below and removed afterwards."""
    with landed_probe(settings, warehouse) as pair:
        yield pair


def _scalars(
    connection: Connection[DictCursor], statement: str, params: tuple[object, ...]
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        row = cursor.fetchone()
    assert row is not None, f"no row from: {statement}"
    return dict(row)


def _triple(run: IngestRun) -> tuple[object, ...]:
    return (run.save_id, as_sql_date(run.sim_date), run.ingest_seq)


_WHERE_TRIPLE = "WHERE save_id = %s AND sim_date = %s AND ingest_seq = %s"


@pytest.mark.gamedata
def test_the_schema_holds_exactly_the_declared_tables(
    warehouse: Connection[DictCursor],
) -> None:
    """The phase's acceptance, read from the server rather than from the emitter.

    "Exactly" in both directions: a declared table missing means the loader wrote
    somewhere it should not have, and an extra one means something landed that no
    declaration describes — which is the state `contracts/tables.toml` exists to make
    impossible.
    """
    assert landed_tables(warehouse) == tuple(sorted(DECLARED_TABLES))


@pytest.mark.gamedata
def test_every_landed_column_is_a_declared_column(
    contracts: Contracts, warehouse: Connection[DictCursor]
) -> None:
    """The declaration, the emitted DDL and the live schema, all one column list.

    The Phase 8a panel recorded that nothing tied a declared column set to anything real
    (CF22). The offline half now ties the declaration to the emitted SQL; this ties it to
    the table MySQL actually holds, which is the copy the loader binds against.
    """
    with warehouse.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name "
            "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION"
        )
        live: dict[str, list[str]] = {}
        for row in cursor.fetchall():
            live.setdefault(str(row["table_name"]), []).append(str(row["column_name"]))

    for table in contracts.tables:
        assert tuple(live[table.name]) == tuple(column.name for column in table.columns), (
            f"{table.name} in the schema does not carry the declared columns in order"
        )


@pytest.mark.gamedata
def test_the_live_primary_key_is_the_declared_key(
    contracts: Contracts, warehouse: Connection[DictCursor]
) -> None:
    """**The last open link in declaration → emitted DDL → live schema.**

    The offline half proves the declaration against the SQL the emitter writes, and the
    column check above proves the declaration against the columns MySQL holds. Neither
    reads the live PRIMARY KEY — and the key is what actually enforces every declared
    grain, so a table created once with a weaker one would stay wrong forever: `ensure_tables`
    skips a table that already exists, by design, because dropping one would destroy landed
    rows a `gm/decisions/` record may cite. The only symptom would be duplicate rows in a
    table whose declaration claims uniqueness.

    Order included. A primary key is ordered and MySQL indexes it that way, so the
    leftmost-prefix behaviour every later query depends on is part of the claim.
    """
    with warehouse.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name "
            "FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME = 'PRIMARY' "
            "ORDER BY TABLE_NAME, SEQ_IN_INDEX"
        )
        live: dict[str, list[str]] = {}
        for row in cursor.fetchall():
            live.setdefault(str(row["table_name"]), []).append(str(row["column_name"]))

    for table in contracts.tables:
        assert tuple(live.get(table.name, ())) == table.key, (
            f"{table.name} is keyed {live.get(table.name)} in the schema but declares "
            f"{list(table.key)} — the grain the declaration claims is not the grain MySQL "
            "enforces"
        )


@pytest.mark.gamedata
def test_roster_grain_is_not_player_grain(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """**AC5, and it asserts the positive rather than the absence of a problem.**

    `player_id` is *not* unique within one snapshot's roster rows, and that is the whole
    reason the table is keyed `(team_id, player_id, list_id)`. A later refactor that
    "simplified" the key to `(sim_date, player_id)` would collapse the players who hold a
    row at two clubs at once, and the roster report would lose them with nothing raised.
    Asserting non-uniqueness is what makes that refactor fail here instead of in a report
    nobody can check.

    The second clause is the same claim from the other side: roster rows cover far fewer
    distinct players than the player table holds, because roughly ten thousand active
    players — free agents, draft-eligible, international, unassigned — carry no roster row
    at all. A loader that invented a row per player would satisfy the first clause and
    fail this one.
    """
    _, run = landed
    roster = _scalars(
        warehouse,
        f"SELECT COUNT(*) AS rows_landed, COUNT(DISTINCT player_id) AS players "
        f"FROM {quote_ident('bronze_team_roster')} {_WHERE_TRIPLE}",
        _triple(run),
    )
    players = _scalars(
        warehouse,
        f"SELECT COUNT(*) AS rows_landed FROM {quote_ident('bronze_player')} {_WHERE_TRIPLE}",
        _triple(run),
    )

    assert roster["rows_landed"] > 0, "nothing landed, so nothing below proves anything"
    assert roster["players"] < roster["rows_landed"], (
        "player_id is unique within the snapshot's roster rows, so the membership grain "
        "has collapsed into a player grain — the cross-club rows are gone"
    )
    assert 0 < roster["players"] < players["rows_landed"] * 3 // 4, (
        f"{roster['players']} distinct rostered players against "
        f"{players['rows_landed']} players: the unrostered majority has vanished"
    )


@pytest.mark.gamedata
def test_a_club_sits_in_exactly_one_division(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The division twin — the opposite shape, catching the opposite fault.

    Where the roster grain fans out on purpose, this one must not: a club sits in one
    division, so `team_id` **is** unique within a snapshot. A membership array consumed
    twice, or a nest walked from the wrong anchor, is precisely what would put a club in
    two divisions, and it would look like more data rather than like a bug.
    """
    _, run = landed
    counts = _scalars(
        warehouse,
        f"SELECT COUNT(*) AS rows_landed, COUNT(DISTINCT team_id) AS clubs "
        f"FROM {quote_ident('bronze_division_team')} {_WHERE_TRIPLE}",
        _triple(run),
    )
    assert counts["rows_landed"] > 0, "no division rows landed"
    assert counts["clubs"] == counts["rows_landed"], (
        f"{counts['rows_landed']} division rows over {counts['clubs']} clubs — a club is "
        "in two divisions, which means an array was consumed twice"
    )


@pytest.mark.gamedata
def test_the_division_table_lands_only_the_reach_of_the_walk(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """Thirty rows against 259 clubs is the documented reach, not a parse fault.

    `world.dat`'s other fourteen leagues each sit behind their own unmapped scalar block,
    and the four All-Star sides appear in no division array at all. **Structural absence
    is a missing row here, never a zero**: `division_id` counts from 0 within its
    sub-league, so East is genuinely division 0 and a loader that wrote 0 to mean "none"
    would file every unplaced club into the AL East with nothing raised. The absence is
    therefore asserted as a row count, which is the only form it can take in this table.

    Six divisions, and the count is over the whole `(league, sub_league, division)` triple
    rather than over `division_id` alone — which takes only three values, because the two
    sub-leagues each number their divisions from zero.
    """
    _, run = landed
    counts = _scalars(
        warehouse,
        "SELECT COUNT(*) AS rows_landed, COUNT(DISTINCT team_id) AS clubs, "
        "COUNT(DISTINCT league_id, sub_league_id, division_id) AS divisions "
        f"FROM {quote_ident('bronze_division_team')} {_WHERE_TRIPLE}",
        _triple(run),
    )
    teams = _scalars(
        warehouse,
        f"SELECT COUNT(*) AS rows_landed FROM {quote_ident('bronze_team')} {_WHERE_TRIPLE}",
        _triple(run),
    )
    assert counts["divisions"] == MLB_DIVISIONS
    assert counts["clubs"] < teams["rows_landed"], (
        f"every one of the {teams['rows_landed']} clubs landed a division row, so the "
        "walk is reaching further than the six MLB divisions it is proven on — or the "
        "loader invented rows for clubs no array names"
    )


@pytest.mark.gamedata
def test_the_field_labels_record_what_was_believed_on_the_day(
    contracts: Contracts,
    warehouse: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> None:
    """`bronze_field_label` is a record *about* a landing, and it must be complete.

    One row per column of every table the ingest wrote — including the provenance columns,
    whose NULL labels are themselves the answer to *"where did this come from"*. The point
    of the table is that a future incident asks what we believed about a field the day it
    landed as a **query**, rather than as archaeology through the git history of
    `docs/data-access.md`, and a partial record cannot answer that.
    """
    _, run = landed
    declared = {(table.name, column.name) for table in contracts.tables for column in table.columns}
    with warehouse.cursor() as cursor:
        cursor.execute(
            f"SELECT table_name, column_name, field_name, source_file, category, "
            f"epistemic, validator FROM {quote_ident('bronze_field_label')} {_WHERE_TRIPLE}",
            _triple(run),
        )
        rows = {(str(r["table_name"]), str(r["column_name"])): r for r in cursor.fetchall()}

    assert set(rows) == declared, (
        f"labels missing for {sorted(declared - set(rows))}; "
        f"labels for undeclared columns {sorted(set(rows) - declared)}"
    )

    landed_label = rows[("bronze_player", "player_id")]
    entry = contracts.field("player_id")
    assert landed_label["field_name"] == entry.name
    assert landed_label["source_file"] == entry.source
    assert landed_label["epistemic"] == entry.epistemic
    assert landed_label["validator"] == entry.validator

    provenance = rows[("bronze_player", "save_id")]
    assert provenance["field_name"] is None, "save_id is ours; no walker produced it"
    assert provenance["epistemic"] is None
