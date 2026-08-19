"""The declaration loader's refusal lattice — every check, reachable from a string.

`contracts/loader.py` exists to make `field_map.toml` mean something. Before it, that file
was the largest tracked contract in the repo with **no programmatic consumer**: a
misspelled `epistemc`, or a `verified` pasted from the row above, parsed clean and shipped
clean, in a file whose labels decide what a report is allowed to print.

So this module proves each refusal fires, and it does it against **synthetic declarations
built here** rather than against the real files. That is not a convenience. A guard that
can only be exercised by breaking the tracked declaration can only be proven by breaking
the repo, so nobody proves it, and it rots into a function nobody has ever seen fail.

The two exceptions are deliberate and marked: `test_the_real_declarations_load` and
`test_mutating_the_roster_key_to_player_grain_is_refused` read the tracked files, because
"the shipped declaration is valid" and "the shipped declaration would notice" are claims
about the shipped declaration.

Offline in full. No save, no MySQL, no game install — which is the point of putting the
contract guards in this phase rather than the next one.
"""

from __future__ import annotations

import pytest

from ootp_ai.contracts.loader import (
    ContractError,
    load_contracts,
    parse_contracts,
    read_declaration_text,
)

# ── minimal valid declarations, mutated per test ─────────────────────────────
#
# Small enough to read in one screen, which is what makes a mutation obviously the ONLY
# difference between a passing and a failing case.

FIELD_MAP = """
[meta]
schema_version = 1
updated = "2026-08-19"
phase = "synthetic"
covers = ["synthetic.dat"]
incomplete = []

[vocabulary]
category = ["identity", "structural", "rating-true", "rating-scouted", "contract"]
epistemic = ["measured", "verified", "inferred", "assumed", "unconfirmed"]
validator = ["none", "export-exact-all-rows"]

[[field]]
name = "widget_id"
source = "synthetic.dat"
walker = "nowhere.read_widgets"
type = "u32"
category = "identity"
epistemic = "verified"
validator = "export-exact-all-rows"

[[field]]
name = "widget_label"
source = "synthetic.dat"
walker = "nowhere.read_widgets"
type = "string"
category = "structural"
epistemic = "measured"
validator = "none"
note = "a note"

[[withheld]]
name = "widget_rating"
source = "synthetic.dat"
reason = "ADR 0012"
"""

TABLES = """
[meta]
schema_version = 1
updated = "2026-08-19"
phase = "synthetic"
tables_declared = 1

[meta.dimensions]
save = ["save_id"]
snapshot = ["sim_date", "ingest_seq"]
widget = ["widget_id"]

[vocabulary]
type = ["u32", "date", "text"]
collation = ["utf8mb4_bin"]

[[table]]
name = "bronze_widget"
grain = "one row per widget per save per snapshot"
key = ["save_id", "sim_date", "ingest_seq", "widget_id"]
source = ["synthetic.dat"]
walker = "nowhere.read_widgets"
collation = "utf8mb4_bin"
coverage = "every widget the walk frames"

[[table.column]]
name = "save_id"
type = "text"
length = 64
null = false
provenance = true

[[table.column]]
name = "sim_date"
type = "date"
null = false
provenance = true

[[table.column]]
name = "ingest_seq"
type = "u32"
null = false
provenance = true

[[table.column]]
name = "widget_id"
type = "u32"
null = false
field = "widget_id"

[[table.column]]
name = "label"
type = "text"
length = 32
null = true
field = "widget_label"
"""


def _parse(field_map: str = FIELD_MAP, tables: str = TABLES) -> None:
    parse_contracts(field_map_text=field_map, tables_text=tables)


def _refused(field_map: str = FIELD_MAP, tables: str = TABLES) -> str:
    with pytest.raises(ContractError) as raised:
        parse_contracts(field_map_text=field_map, tables_text=tables)
    return str(raised.value)


# ── the baseline, so every failure below is attributable to its mutation ─────


def test_the_synthetic_declaration_parses() -> None:
    """If this ever goes red the fixtures are broken, not the loader."""
    _parse()


def test_the_real_declarations_load() -> None:
    """The shipped `tables.toml` and `field_map.toml` agree with themselves."""
    contracts = load_contracts()
    assert len(contracts.tables) == 8, "Phase 8a declares eight tables"
    assert contracts.fields, "the field map declares no fields"


def test_the_declarations_resolve_as_package_data() -> None:
    """Resolved through `importlib.resources`, never a `parents[N]` walk.

    A path walk breaks the moment the package is installed rather than run from a
    checkout, and `.claude/agents/data-engineer.md` bans it outside test modules.
    """
    assert read_declaration_text("tables.toml").lstrip().startswith("#")
    assert "[vocabulary]" in read_declaration_text("field_map.toml")


# ── the label vocabulary: the check the field map had no consumer for ────────


@pytest.mark.parametrize(
    ("label", "bad"),
    [
        ("category", 'category = "identiy"'),
        ("epistemic", 'epistemic = "verifed"'),
        ("validator", 'validator = "export-exact"'),
    ],
)
def test_an_unknown_label_is_refused_by_name_and_by_value(label: str, bad: str) -> None:
    """A typo in a label must name the field AND the offending value.

    Naming only the file would send a reader through 650 lines by eye; naming only the
    value would not say which entry carried it.
    """
    original = {
        "category": 'category = "identity"',
        "epistemic": 'epistemic = "verified"',
        "validator": 'validator = "export-exact-all-rows"',
    }[label]
    message = _refused(field_map=FIELD_MAP.replace(original, bad, 1))
    assert "widget_id" in message, "the refusal does not name the field"
    assert bad.split('"')[1] in message, "the refusal does not name the offending value"
    assert label in message


def test_a_field_map_with_no_vocabulary_is_refused() -> None:
    """The vocabulary is what makes a label checkable; without it nothing is."""
    stripped = FIELD_MAP.replace("[vocabulary]", "[unused]", 1)
    assert "vocabulary" in _refused(field_map=stripped)


def test_a_misspelled_key_is_refused_rather_than_ignored() -> None:
    """`epistemc = "verified"` would otherwise leave the entry with no label at all.

    Silently. TOML does not care, and a loader that only reads the keys it knows would
    hand back an entry whose `epistemic` came from a default nobody chose.
    """
    message = _refused(
        field_map=FIELD_MAP.replace('epistemic = "measured"', 'epistemc = "measured"', 1)
    )
    assert "epistemc" in message


def test_two_fields_with_one_name_are_refused() -> None:
    """Names are what a column's `field` resolves through."""
    doubled = (
        FIELD_MAP
        + """
[[field]]
name = "widget_id"
source = "other.dat"
walker = "nowhere.read_others"
type = "u32"
category = "identity"
epistemic = "measured"
validator = "none"
"""
    )
    assert "widget_id" in _refused(field_map=doubled)


# ── the grain check ──────────────────────────────────────────────────────────


def test_a_key_that_drifts_from_its_grain_sentence_is_refused() -> None:
    """The failure this whole file exists for, in miniature."""
    drifted = TABLES.replace(
        'key = ["save_id", "sim_date", "ingest_seq", "widget_id"]',
        'key = ["save_id", "sim_date", "ingest_seq"]',
        1,
    )
    message = _refused(tables=drifted)
    assert "widget_id" in message
    assert "one row per widget per save per snapshot" in message


def test_a_grain_sentence_that_drifts_from_its_key_is_refused() -> None:
    """The same check from the other side — prose is not decoration."""
    drifted = TABLES.replace(
        'grain = "one row per widget per save per snapshot"',
        'grain = "one row per save per snapshot"',
        1,
    )
    assert "widget_id" in _refused(tables=drifted)


def test_an_undeclared_grain_dimension_is_refused() -> None:
    """A sentence may only use dimensions the declaration maps to columns."""
    invented = TABLES.replace(
        'grain = "one row per widget per save per snapshot"',
        'grain = "one row per gadget per save per snapshot"',
        1,
    )
    message = _refused(tables=invented)
    assert "gadget" in message


def test_a_grain_that_is_not_a_sentence_is_refused() -> None:
    unparsed = TABLES.replace(
        'grain = "one row per widget per save per snapshot"',
        'grain = "widgets, keyed by save"',
        1,
    )
    assert "one row per" in _refused(tables=unparsed)


def test_mutating_the_roster_key_to_player_grain_is_refused() -> None:
    """**The acceptance criterion's own mutation, run against the tracked file.**

    Phase 8a's acceptance says to change `bronze_team_roster`'s key to
    `(sim_date, player_id)` by hand and confirm the suite goes red. Doing it in memory is
    strictly better: the check runs on every CI run instead of once, and nobody has to
    remember to revert a tracked file.

    The mutation is the real defect, not a toy: 935 players hold a list-3 row at their
    organisation *and* a row at another club in the same snapshot, so a player-grained key
    collapses them and the roster report loses players with nothing raised.
    """
    tables = read_declaration_text("tables.toml")
    roster_key = '"save_id", "sim_date", "ingest_seq", "team_id", "player_id", "list_id"'
    assert roster_key in tables, "the roster key is not spelled the way this test mutates"

    message = _refused(
        field_map=read_declaration_text("field_map.toml"),
        tables=tables.replace(roster_key, '"sim_date", "player_id"', 1),
    )
    assert "bronze_team_roster" in message
    assert "one row per player per team per roster list per save per snapshot" in message


# ── keys, columns and types ──────────────────────────────────────────────────


def test_a_key_naming_a_column_that_is_not_declared_is_refused() -> None:
    message = _refused(
        tables=TABLES.replace(
            'key = ["save_id", "sim_date", "ingest_seq", "widget_id"]',
            'key = ["save_id", "sim_date", "ingest_seq", "widget_uuid"]',
            1,
        )
    )
    assert "widget_uuid" in message


def test_a_nullable_key_column_is_refused() -> None:
    """MySQL's `COUNT(DISTINCT a, b, c)` drops tuples containing NULL.

    So a nullable key column makes the grain test count fewer rows than the table holds
    and pass — the most expensive shape of green there is.
    """
    nullable_key = TABLES.replace(
        """[[table.column]]
name = "widget_id"
type = "u32"
null = false""",
        """[[table.column]]
name = "widget_id"
type = "u32"
null = true""",
        1,
    )
    message = _refused(tables=nullable_key)
    assert "widget_id" in message
    assert "NOT NULL" in message


def test_an_unknown_column_type_is_refused() -> None:
    message = _refused(
        tables=TABLES.replace(
            'type = "u32"\nnull = false\nfield = "widget_id"',
            'type = "u128"\nnull = false\nfield = "widget_id"',
            1,
        )
    )
    assert "u128" in message


def test_an_unknown_collation_is_refused() -> None:
    message = _refused(
        tables=TABLES.replace(
            'collation = "utf8mb4_bin"\ncoverage', 'collation = "latin1_swedish_ci"\ncoverage', 1
        )
    )
    assert "latin1_swedish_ci" in message


def test_a_text_column_with_no_length_is_refused() -> None:
    """A VARCHAR whose width nobody declared is a width somebody guessed."""
    message = _refused(tables=TABLES.replace('type = "text"\nlength = 32\n', 'type = "text"\n', 1))
    assert "length" in message


def test_a_non_text_column_carrying_a_length_is_refused() -> None:
    message = _refused(
        tables=TABLES.replace(
            'name = "ingest_seq"\ntype = "u32"\nnull = false',
            'name = "ingest_seq"\ntype = "u32"\nlength = 8\nnull = false',
            1,
        )
    )
    assert "length" in message


def test_a_column_claiming_a_field_nobody_declared_is_refused() -> None:
    """A column with no resolvable provenance has no epistemic label.

    `bronze_field_label` would then land a NULL where a belief belongs, which is the one
    thing that table exists to prevent.
    """
    message = _refused(
        tables=TABLES.replace('field = "widget_label"', 'field = "widget_caption"', 1)
    )
    assert "widget_caption" in message


def test_a_column_that_is_neither_provenance_nor_a_field_is_refused() -> None:
    """**The hole the acceptance panel found, closed at the declaration.**

    "No field" used to mean two different things — *this column is ours* and *nobody said
    what this column is* — and the serving gate read both as renderable. Measured: a
    `batting_ratings_talent_contact` column with its `field` line omitted loaded clean,
    emitted into the DDL and returned renderable, while the policy's own name-fragment
    check on that exact string returned True the whole time.

    Provenance is now an act. A column says which it is or it does not load.
    """
    orphaned = TABLES.replace('null = true\nfield = "widget_label"', "null = true", 1)
    message = _refused(tables=orphaned)
    assert "label" in message
    assert "provenance" in message


def test_a_column_claiming_both_provenance_and_a_field_is_refused() -> None:
    """They are exclusive: provenance means no walker produced it."""
    both = TABLES.replace(
        'null = true\nfield = "widget_label"',
        'null = true\nfield = "widget_label"\nprovenance = true',
        1,
    )
    assert "cannot both be true" in _refused(tables=both)


def test_an_unsigned_column_over_a_signed_field_is_refused() -> None:
    """The `u32` over `cursor.i32()` contradiction, caught at load rather than at landing.

    Six `bronze_player` columns shipped this way in the first draft. The walker signs those
    reads on purpose — the export writes `league_id` negative on 176 real records, and a
    currently-green offline test asserts `player.league_id == -203`. Landing -203 into
    `INT UNSIGNED` either aborts the batch under strict mode or clamps it to 0, which is
    the value the walker uses for "this player has no team".
    """
    signed_field = FIELD_MAP.replace(
        'name = "widget_id"\nsource = "synthetic.dat"\nwalker = "nowhere.read_widgets"\ntype = "u32"',
        'name = "widget_id"\nsource = "synthetic.dat"\nwalker = "nowhere.read_widgets"\ntype = "i32, negative on 176 real records"',
        1,
    )
    message = _refused(field_map=signed_field)
    assert "widget_id" in message
    assert "i32" in message


def test_the_declared_table_count_must_match_the_tables_declared() -> None:
    """`tables_declared` is the phase's acceptance criterion, kept honest by the loader."""
    message = _refused(tables=TABLES.replace("tables_declared = 1", "tables_declared = 2", 1))
    assert "tables_declared" in message


def test_a_declaration_with_no_tables_is_refused() -> None:
    empty = "\n".join(TABLES.splitlines()[: TABLES.splitlines().index("[[table]]")])
    assert "no tables" in _refused(tables=empty + "\n")


def test_malformed_toml_is_refused_by_name() -> None:
    assert "not valid TOML" in _refused(tables=TABLES + "\nthis is not toml\n")
