"""The differential's comparison layer, exercised OFFLINE — this phase's CI signal.

Not in the plan's §7 checklist, and added under §4.1's rule, which is the same argument
Phase 8b made when it added `test_bronze_landing.py`: *"a phase proved only by `gamedata`
tests has zero CI signal"*. Phase 9's headline artifact is `test_parser_vs_export.py`, which
needs a save, a warehouse and an export — none of which CI has or may ever have (ADR 0006).
Without this module the entire comparison layer could be broken by a later refactor and
nothing would go red until somebody ran the local suite.

So everything here drives the **pure** half of `validate/export_diff.py` with synthetic
rows: the comparison modes, the absence rules and their populations, the two row-set
mechanisms, and the cross-check that ties the harness's spec to the tracked declaration.

**The rows below are invented.** They are shaped like the export's and carry no game data
(ADR 0006); the real populations live in the `gamedata` module, where the real answer key
is.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from ootp_ai.contracts.loader import load_contracts
from ootp_ai.contracts.policy import RATING_CATEGORIES
from ootp_ai.validate.export_diff import (
    ABSENCE_RULES,
    DIVISION_SPEC,
    ROW_SPECS,
    SPECS,
    AbsenceRule,
    ColumnPair,
    RowSpec,
    TableSpec,
    argb_hex,
    compare_keyed,
    compare_rows,
    exact,
    magnitude,
)


def _team(team_id: int, **overrides: Any) -> dict[str, Any]:
    """A landed `bronze_team` row, invented."""
    row: dict[str, Any] = {
        "team_id": team_id,
        "city": "Springfield",
        "abbr": "SPR",
        "nickname": "Isotopes",
        "logo_filename": "spr.png",
        "city_id": 1,
        "park_id": 2,
        "league_id": 100,
        "sub_league_id": 0,
        "nation_id": 3,
        "human_team": 0,
        "level": 1,
        "parent_team_id": 0,
        "historical_id": None,
        "color_1": 0xFF112233,
        "color_3": 0xFF445566,
    }
    row.update(overrides)
    return row


def _export_team(team_id: int, **overrides: Any) -> dict[str, Any]:
    """The same club as the export would write it, invented."""
    row: dict[str, Any] = {
        "team_id": team_id,
        "name": "Springfield",
        "abbr": "SPR",
        "nickname": "Isotopes",
        "logo_file_name": "spr.png",
        "city_id": 1,
        "park_id": 2,
        "league_id": 100,
        "sub_league_id": 0,
        "nation_id": 3,
        "human_team": 0,
        "level": 1,
        "parent_team_id": 0,
        "historical_id": "",
        "allstar_team": 0,
        "background_color_id": "#112233",
        "text_color_id": "#445566",
    }
    row.update(overrides)
    return row


#: The team spec with its two absence-rule populations reduced to what these fixtures use.
#: The rules themselves are the shipped ones; only the counts are re-declared, because a
#: population of 229 cannot be demonstrated with three synthetic clubs.
def _rules(city: int, historical: int, divisions: int = 4) -> tuple[AbsenceRule, ...]:
    counts = {
        ("bronze_team", "city"): city,
        ("bronze_team", "historical_id"): historical,
        ("bronze_division_team", None): divisions,
    }
    return tuple(
        AbsenceRule(
            table=rule.table,
            column=rule.column,
            reason=rule.reason,
            population=counts[(rule.table, rule.column)],
            allows=rule.allows,
        )
        for rule in ABSENCE_RULES
    )


_TEAM_SPEC = SPECS[0]
_ROSTER_SPEC = ROW_SPECS[0]
_EVENT_SPEC = ROW_SPECS[1]


def _sized(spec: TableSpec | RowSpec, export_rows: int) -> Any:
    """The shipped spec with its export population resized to a fixture's scale.

    The specs pin the real answer key's populations — 259 clubs, 18,072 players — and the
    comparison now **enforces** that pin, which is the whole point of it. A three-club
    fixture therefore has to say so. Resized rather than zeroed, so these tests still run
    against a live pin and a fixture that drifts from its own declaration still goes red.
    """
    return replace(spec, export_rows=export_rows)


# ── the comparison modes ─────────────────────────────────────────────────────


def test_exact_does_not_equate_absence_with_a_zero_or_an_empty_string() -> None:
    """The single most load-bearing property of the whole harness.

    If `exact` folded `None` into `""` or into `0`, every structural-absence disagreement
    would compare equal, the absence rules would never fire, their populations would never
    be checked, and the harness would report a clean run over a parser that had started
    writing zeros where the save says nothing. The rules are only meaningful because the
    comparison they qualify is strict.
    """
    assert not exact(None, "")
    assert not exact(None, 0)
    assert not exact("", 0)
    assert not exact(0, None)
    assert exact(None, None)
    assert exact("", "")


def test_exact_is_accent_and_case_sensitive_which_the_schema_collation_is_not() -> None:
    """SD-13. The schemas are `utf8mb4_0900_ai_ci`; this comparison must not be."""
    assert not exact("Ramirez", "Ramírez")
    assert not exact("rodon", "Rodon")
    assert exact("Ramírez", "Ramírez")


def test_exact_spans_the_two_column_widths_the_same_number_lands_in() -> None:
    """Our `TINYINT UNSIGNED` against the export's `smallint` is one number, not two."""
    assert exact(34, 34)
    assert not exact(34, 35)


def test_magnitude_accepts_the_negated_league_id_and_nothing_else() -> None:
    """The export's one signed encoding, and it must stay that narrow.

    `magnitude` exists for the 176 rows where the export negates `league_id` to mark a
    player assigned to a club but on no roster list. A tolerance any wider would accept a
    genuinely wrong id that happened to be the negation of the right one.
    """
    assert magnitude(203, -203)
    assert magnitude(203, 203)
    assert not magnitude(203, -204)
    assert not magnitude(204, -203)


def test_argb_hex_checks_the_alpha_rather_than_masking_it_away() -> None:
    """Alpha is the one byte whose expected value is known for every record.

    Masking it unconditionally would let a walk reading one byte early compare equal on
    any club whose colour survived the shift, which is the silent-wrongness this project
    ranks worse than a crash.
    """
    assert argb_hex(0xFF112233, "#112233")
    assert argb_hex(0xFF112233, "#112233".lower())
    assert not argb_hex(0x00112233, "#112233"), "a transparent colour is not an opaque one"
    assert not argb_hex(0xFF112234, "#112233")


# ── the keyed comparison ─────────────────────────────────────────────────────


def test_a_clean_run_is_clean_and_reports_no_failures() -> None:
    ours = {n: _team(n) for n in (1, 2, 3)}
    theirs = {n: _export_team(n) for n in (1, 2, 3)}

    result = compare_keyed(ours, theirs, _sized(_TEAM_SPEC, 3), _rules(city=0, historical=3))

    assert result.clean, (result.columns, result.rule_faults)
    assert result.compared_rows == 3
    assert not result.rule_faults


def test_a_mismatch_names_the_field_the_row_and_both_values() -> None:
    """AC6's output contract, and §4.4's Phase 9 row: it must NAME the field.

    This is the deliberate corruption at the layer where it can be a permanent test rather
    than a one-off manual act. One column of one row is falsified; the failure output must
    identify that column by name, that row by key, and both values — and must not anywhere
    reduce the run to a rate.
    """
    ours = {n: _team(n) for n in (1, 2, 3)}
    ours[2]["park_id"] = 999
    theirs = {n: _export_team(n) for n in (1, 2, 3)}
    # A distinctive export value: with the default 2, asserting `"2" in ...` was satisfied by
    # the `team_id=2` in the key and could not have failed.
    theirs[2]["park_id"] = 4242

    report = compare_keyed(ours, theirs, _sized(_TEAM_SPEC, 3), _rules(city=0, historical=3))
    assert not report.clean

    park = next(column for column in report.columns if column.column == "park_id")
    assert len(park.mismatches) == 1
    assert "team_id=2" in park.mismatches[0]
    assert "landed 999 vs export 4242" in park.mismatches[0]

    # Every other column stayed clean, so the report points at one field rather than
    # reporting that "the teams table" disagrees.
    assert [column.column for column in report.columns if not column.clean] == ["park_id"]


def test_the_failure_text_names_the_column_and_never_a_pass_rate() -> None:
    """§4.3's first anti-vacuity rule, asserted rather than promised."""
    from ootp_ai.validate.export_diff import DiffReport

    ours = {n: _team(n) for n in (1, 2)}
    ours[1]["abbr"] = "XXX"
    theirs = {n: _export_team(n) for n in (1, 2)}

    lines = DiffReport(
        tables=(compare_keyed(ours, theirs, _sized(_TEAM_SPEC, 2), _rules(city=0, historical=2)),)
    ).failures()

    assert len(lines) == 1
    assert "bronze_team.abbr" in lines[0]
    assert "team_id=1" in lines[0]
    assert "XXX" in lines[0]
    assert "%" not in lines[0], (
        "the failure output carries a percentage. An aggregate is exactly how a parser "
        "reading the adjacent field ships green"
    )


def test_an_absence_rule_suppresses_only_the_shape_it_names() -> None:
    """The city rule is tied to the nickname, not to "NULL is fine".

    Club 1 is an all-star side the export fills from its nickname — allowed. Club 2 has a
    NULL city against a real, different export name — a genuine disagreement, and a rule
    written as *"our NULL always passes"* would have swallowed it.
    """
    ours = {
        1: _team(1, city=None),
        2: _team(2, city=None),
    }
    theirs = {
        1: _export_team(1, name="All-Stars", nickname="All-Stars", allstar_team=1),
        2: _export_team(2, name="Shelbyville", nickname="Shelbyvillians"),
    }

    result = compare_keyed(ours, theirs, _sized(_TEAM_SPEC, 2), _rules(city=1, historical=2))

    city = next(column for column in result.columns if column.column == "city")
    assert city.allowed == 1
    assert len(city.mismatches) == 1
    assert "team_id=2" in city.mismatches[0]


def test_a_rule_whose_population_moved_is_itself_reported() -> None:
    """The property that stops the allowlist being a mute button.

    A rule declaring 26 rows that now matches 27 means either the export changed or
    something the rule was never written for has started matching it. Both need a human,
    and neither may pass quietly — so the count moving is a failure in its own right, in
    the direction of *fewer* as well as more.
    """
    ours = {1: _team(1, city=None)}
    theirs = {1: _export_team(1, name="All-Stars", nickname="All-Stars", allstar_team=1)}

    result = compare_keyed(ours, theirs, _sized(_TEAM_SPEC, 1), _rules(city=5, historical=1))

    assert not result.clean
    assert any("allowed 1 rows against a declared population of 5" in f for f in result.rule_faults)


def test_rows_the_export_does_not_carry_are_expected_but_counted() -> None:
    """`players.dat` frames five records the export has never heard of.

    Expected — so a landing that carries exactly the declared number of extras is clean —
    and *counted*, so a landing that grew a sixth is not. The distinction being kept is
    "the walk sees more than the export" from "the walk invented a record".
    """
    spec = TableSpec(
        table="bronze_player",
        export_table="players",
        key="player_id",
        export_key="player_id",
        columns=(ColumnPair("age", "age", "age", "export-exact-all-rows"),),
        parsed_only=1,
    )
    theirs = {1: {"player_id": 1, "age": 30}}

    clean = compare_keyed(
        {1: {"player_id": 1, "age": 30}, 2: {"player_id": 2, "age": 21}}, theirs, spec
    )
    assert clean.clean, clean.ours_only

    grown = compare_keyed(
        {
            1: {"player_id": 1, "age": 30},
            2: {"player_id": 2, "age": 21},
            3: {"player_id": 3, "age": 19},
        },
        theirs,
        spec,
    )
    assert not grown.clean
    assert len(grown.ours_only) == 2


def test_losing_every_declared_parsed_only_row_is_reported_not_silently_clean() -> None:
    """The downward half of the same guard, which was silent until the acceptance panel.

    The report was built by iterating the extra rows, so with `parsed_only = 5` and **no**
    extras there was nothing to list: the branch fired, produced an empty tuple, and the run
    came back `clean`. A walk that stopped framing the five records the export has never
    carried is exactly as interesting as one that grew a sixth — and it is the direction
    with no rows left to name, which is why it needs saying explicitly.

    Lives here, offline, because the only live counter-check was `-m gamedata` and CI runs
    `-m "not gamedata"`.
    """
    spec = TableSpec(
        table="bronze_player",
        export_table="players",
        key="player_id",
        export_key="player_id",
        columns=(ColumnPair("age", "age", "age", "export-exact-all-rows"),),
        parsed_only=5,
    )
    rows = {1: {"player_id": 1, "age": 30}}

    result = compare_keyed(rows, rows, spec)

    assert not result.clean, "losing every parsed-only row reported a clean run"
    assert any("parsed_only of 5" in fault for fault in result.rule_faults)
    assert any("Fewer is as informative as more" in fault for fault in result.rule_faults)


def test_an_export_side_smaller_than_its_pin_is_reported() -> None:
    """`export_rows` is enforced, not decorative — and this is the offline signal for it.

    It was documented as *the* anti-narrowing guarantee and read by no production code, so a
    `WHERE` clause added to a fetch would have made the suite greener. The real pin lived in
    the `gamedata` module, which CI never runs.
    """
    spec = TableSpec(
        table="bronze_team",
        export_table="teams",
        key="team_id",
        export_key="team_id",
        columns=(ColumnPair("abbr", "abbr", "team_abbr", "export-exact-all-rows"),),
        export_rows=259,
    )
    row = {"team_id": 1, "abbr": "SPR"}

    result = compare_keyed({1: row}, {1: row}, spec)

    assert not result.clean
    assert any("against a pinned 259" in fault for fault in result.rule_faults)


def test_an_export_row_that_did_not_land_is_a_failure_with_no_allowance() -> None:
    """The asymmetry is the point: extra rows have an argument, missing ones do not."""
    spec = TableSpec(
        table="bronze_player",
        export_table="players",
        key="player_id",
        export_key="player_id",
        columns=(ColumnPair("age", "age", "age", "export-exact-all-rows"),),
        parsed_only=0,
    )
    result = compare_keyed({}, {1: {"player_id": 1, "age": 30}}, spec)

    assert not result.clean
    assert result.theirs_only == ("player_id=1",)


# ── the row-set comparisons ──────────────────────────────────────────────────


def _membership(team_id: int, player_id: int, list_id: int) -> dict[str, Any]:
    return {"team_id": team_id, "player_id": player_id, "list_id": list_id}


def test_a_roster_row_present_on_one_side_only_is_named_whole() -> None:
    """A membership has no attribute to disagree about, so the row IS the finding."""
    ours = [_membership(1, 10, 1), _membership(1, 11, 1)]
    theirs = [_membership(1, 10, 1), _membership(1, 12, 1)]

    result = compare_rows(ours, theirs, _sized(_ROSTER_SPEC, len(theirs)))

    assert not result.clean
    assert any("player_id=11" in row for row in result.ours_only)
    assert any("player_id=12" in row for row in result.theirs_only)


def test_a_duplicate_in_a_table_declared_unique_is_reported_rather_than_absorbed() -> None:
    """A set difference cannot see a duplicate, so it is checked for separately.

    `bronze_team_roster` is keyed and therefore unique by construction, but the export side
    is not ours and a walk that emitted a row twice would set-difference to nothing.
    """
    ours = [_membership(1, 10, 1), _membership(1, 10, 1)]
    theirs = [_membership(1, 10, 1)]

    result = compare_rows(ours, theirs, _sized(_ROSTER_SPEC, len(theirs)))

    assert not result.clean
    assert any("duplicate rows in a table declared unique" in fault for fault in result.rule_faults)


def test_the_calendar_is_a_multiset_because_the_export_repeats_events() -> None:
    """Measured: 458 of 3,058 export events are exact duplicates of another row.

    Under set semantics a walk that dropped one of a duplicated pair would compare equal
    to a walk that kept both, and 458 lost events would report clean.
    """
    event = {
        "league_id": 1,
        "start_date": "2024-01-02",
        "event_type": 1,
        "event_over": 0,
        "deleted": 1,
        "name": "Inaugural Draft",
        "needs_human_action": 1,
        "real_sim_date": 0,
    }
    exported = dict(event)
    exported["type"] = exported.pop("event_type")

    kept_both = compare_rows(
        [event, dict(event)], [exported, dict(exported)], _sized(_EVENT_SPEC, 2)
    )
    assert kept_both.clean

    dropped_one = compare_rows([event], [exported, dict(exported)], _sized(_EVENT_SPEC, 2))
    assert not dropped_one.clean, (
        "a walk that lost one of a duplicated pair compared equal, which is the exact "
        "failure the multiset mode exists to catch"
    )
    assert len(dropped_one.theirs_only) == 1


def test_the_division_rule_suppresses_an_all_star_side_and_counts_it() -> None:
    """The plan's pre-registered structural-absence case, on the column it lands on.

    The export writes `division_id = 0` for a club in no division, and 0 is a real division
    for every other club — so absence here has to be a missing row, and the rule is what
    keeps that from reading as a parse fault.
    """
    ours = [{"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 7}]
    theirs = [
        {"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 7, "allstar_team": 0},
        {"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 99, "allstar_team": 1},
    ]

    result = compare_rows(
        ours, theirs, _sized(DIVISION_SPEC, 2), _rules(city=0, historical=0, divisions=1)
    )

    assert result.clean, (result.theirs_only, result.rule_faults)


def test_two_whole_row_rules_on_one_table_keep_separate_tallies() -> None:
    """Each rule against its own population, not against the sum.

    A single shared counter judged every rule against the total: two rules of population 1
    matching one row each both reported having allowed 2, turning a **correct** run red —
    and, in the other direction, a rule over-firing could be hidden by a sibling that
    under-fired. Latent with today's single whole-row rule, which is why it is pinned here
    rather than discovered by the second one.
    """
    first = AbsenceRule(
        table="bronze_division_team",
        column=None,
        reason="an invented rule, for this test only",
        population=1,
        allows=lambda row: int(row.get("allstar_team") or 0) == 1,
    )
    second = AbsenceRule(
        table="bronze_division_team",
        column=None,
        reason="a second invented rule that matches a different row",
        population=1,
        allows=lambda row: int(row.get("team_id") or 0) == 98,
    )
    ours = [{"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 7}]
    theirs = [
        {"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 7, "allstar_team": 0},
        {"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 99, "allstar_team": 1},
        {"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 98, "allstar_team": 0},
    ]

    result = compare_rows(ours, theirs, _sized(DIVISION_SPEC, 3), (first, second))

    assert result.clean, result.rule_faults
    assert result.suppressed == 2


def test_a_whole_row_rule_on_a_keyed_table_is_reported_as_orphaned() -> None:
    """The mirror gap: it can never match a column, so its population is never checked.

    `compare_keyed` resolves one rule per column, and a `column is None` rule matches no
    column — so it sat in the applicable list forever, never firing and never verified. A
    rule nobody checks is indistinguishable from a rule that was deleted.
    """
    orphan = AbsenceRule(
        table="bronze_team",
        column=None,
        reason="a whole-row rule pointed at a column-by-column table",
        population=1,
        allows=lambda _row: True,
    )
    row = {"team_id": 1, "abbr": "SPR"}
    spec = TableSpec(
        table="bronze_team",
        export_table="teams",
        key="team_id",
        export_key="team_id",
        columns=(ColumnPair("abbr", "abbr", "team_abbr", "export-exact-all-rows"),),
        export_rows=1,
    )

    result = compare_keyed({1: row}, {1: row}, spec, (orphan,))

    assert not result.clean
    assert any("can never fire" in fault for fault in result.rule_faults)


def test_a_row_spec_reports_the_columns_it_compared() -> None:
    """CF11: a clean row-spec table printed one row-count line and nothing else.

    A `bronze_league_event` run comparing all eight columns and one comparing none looked
    identical in the report, so a reader auditing a green run had no evidence the columns
    were in scope.
    """
    ours = [_membership(1, 10, 1)]
    theirs = [_membership(1, 10, 1)]

    result = compare_rows(ours, theirs, _sized(_ROSTER_SPEC, 1))

    assert result.clean
    assert [column.column for column in result.columns] == list(_ROSTER_SPEC.columns), (
        "a row spec emitted no per-column result, so a clean run is indistinguishable in "
        "the report from one that compared no columns at all"
    )


def test_a_real_club_missing_from_a_division_is_not_suppressed() -> None:
    """The negative half: the rule may only reach an all-star side."""
    ours: list[dict[str, Any]] = []
    theirs = [
        {"league_id": 1, "sub_league_id": 0, "division_id": 0, "team_id": 7, "allstar_team": 0},
    ]

    result = compare_rows(
        ours, theirs, _sized(DIVISION_SPEC, 1), _rules(city=0, historical=0, divisions=0)
    )

    assert not result.clean
    assert any("team_id=7" in row for row in result.theirs_only)


# ── the tie between the harness and the tracked declaration ──────────────────


def _all_pairs() -> list[tuple[str, str, str]]:
    """Every (table, field, validator) the harness claims, from both spec kinds."""
    claims: list[tuple[str, str, str]] = []
    for spec in SPECS:
        claims.extend((spec.table, pair.field, pair.validator) for pair in spec.columns)
    for row_spec in (*ROW_SPECS, DIVISION_SPEC):
        claims.extend((row_spec.table, field, validator) for field, validator in row_spec.fields)
    return claims


def test_every_compared_column_carries_the_validator_its_field_map_entry_declares() -> None:
    """The grain-versus-key pattern, applied to the validation labels.

    Two artifacts state one fact — the harness says *"I compare this column exactly"* and
    `field_map.toml` says *"this field is validated export-exact"* — and they are checked
    against each other rather than kept in step by hand.

    **The direction matters.** The harness does not *read* the label to decide how to
    compare; that would let somebody silence a failing column by editing a label, which is
    precisely backwards. It declares its comparison independently and this test requires
    the two to agree.
    """
    contracts = load_contracts()
    disagreements = [
        f"{table}: field {field!r} is declared {contracts.field(field).validator!r} and the "
        f"differential compares it as {validator!r}"
        for table, field, validator in _all_pairs()
        if contracts.field(field).validator != validator
    ]
    assert not disagreements, "\n".join(disagreements)


def test_every_compared_column_is_a_column_the_declaration_actually_lands() -> None:
    """A harness comparing a column nobody lands would fail at the SELECT, later."""
    contracts = load_contracts()
    for spec in SPECS:
        declared = {column.name for column in contracts.table(spec.table).columns}
        missing = sorted({spec.key, *spec.compared_columns} - declared)
        assert not missing, f"{spec.table} does not declare {missing}"
    for row_spec in (*ROW_SPECS, DIVISION_SPEC):
        declared = {column.name for column in contracts.table(row_spec.table).columns}
        missing = sorted(set(row_spec.columns) - declared)
        assert not missing, f"{row_spec.table} does not declare {missing}"


def test_every_compared_column_resolves_to_the_field_the_harness_names() -> None:
    """Ties `ColumnPair.field` to `tables.toml`'s own `field =` line for that column."""
    contracts = load_contracts()
    for spec in SPECS:
        table = contracts.table(spec.table)
        for pair in spec.columns:
            assert table.column(pair.column).field == pair.field, (
                f"{spec.table}.{pair.column} resolves to field "
                f"{table.column(pair.column).field!r}, but the differential attributes its "
                f"validator to {pair.field!r} — so a label upgrade would land on the wrong "
                "field entry"
            )


#: Fields whose `export-*` validator is earned somewhere OTHER than this harness. Each one
#: names the artifact that earns it, because a blanket exemption list is how the reverse
#: check below stops meaning anything.
PROVED_ELSEWHERE: tuple[tuple[str, str], ...] = (
    ("team_record_id", "the key both sides are aligned on; a wrong one misaligns every column"),
    ("player_id", "the key both sides are aligned on"),
    ("first_name_index", "AC7 — tests/test_names_join.py resolves every index against the export"),
    ("last_name_index", "AC7 — tests/test_names_join.py"),
    ("name_index", "AC7 — tests/test_names_join.py"),
    ("name_text", "AC7 — tests/test_names_join.py, exact on 100% of compared rows"),
    ("human_manager_team_id", "check_provenance, which runs before every diff"),
)


def test_every_export_validated_field_is_actually_compared_by_something() -> None:
    """The cross-check in the direction the forward one cannot see: deletions.

    Every other guard here enumerates *from the harness*, so removing a `ColumnPair` narrows
    AC6 and nothing goes red — the panel proved it by deleting `bronze_team.nation_id` and
    `bronze_player.weight` in-process and getting zero failures either time, while
    `field_map.toml` went on claiming `export-exact-all-rows` for both.

    This phase's own headline discovery is why that matters: `team_historical_id` carried
    "Not carried by the export's teams table" for months while the export carried it. The
    link between a validator token and the thing that earns it drifts silently unless
    something enumerates from the declaration side.

    An eighth exemption therefore has to be argued in writing, which is the property the
    forward direction already had.
    """
    contracts = load_contracts()
    compared = {field for _table, field, _validator in _all_pairs()}
    exempt = {name for name, _why in PROVED_ELSEWHERE}

    unearned = sorted(
        f"{table.name}.{column.name} -> field {column.field!r} claims "
        f"{contracts.field(column.field).validator!r}"
        for table in contracts.tables
        for column in table.columns
        if column.field is not None
        and contracts.field(column.field).validator.startswith("export-")
        and column.field not in compared
        and column.field not in exempt
    )
    assert not unearned, (
        "these fields carry an export-* validator that nothing in the differential earns:\n"
        + "\n".join(unearned)
        + "\n\nEither compare them, or add them to PROVED_ELSEWHERE naming the artifact "
        "that does."
    )


def test_every_exemption_names_a_field_that_still_exists_and_still_claims_one() -> None:
    """A stale exemption is worse than none — it excuses a field nobody is checking."""
    contracts = load_contracts()
    compared = {field for _table, field, _validator in _all_pairs()}
    for name, why in PROVED_ELSEWHERE:
        assert why, f"{name} is exempt with no reason given"
        entry = contracts.field(name)
        assert entry.validator.startswith("export-"), (
            f"{name} is exempted from the differential but no longer claims an export "
            f"validator (it says {entry.validator!r}), so the exemption is dead weight"
        )
        assert name not in compared, (
            f"{name} is both exempted and compared. One of the two is stale, and an "
            "exemption that overlaps the real coverage hides how much is really exempt"
        )


def test_every_row_spec_names_exactly_the_fields_its_columns_resolve_to() -> None:
    """`RowSpec.fields` is tied to `columns` by nothing but the author's care — so tie it.

    **Set equality, not position.** The roster spec's three columns all resolve to the one
    `roster_membership` field, so a one-entry-per-column reading is already false for it.
    What must hold is that the fields named are exactly the fields the declared columns
    resolve through — which goes red on a reorder, an added column, or a dropped entry.
    """
    contracts = load_contracts()
    for spec in (*ROW_SPECS, DIVISION_SPEC):
        table = contracts.table(spec.table)
        resolved = {table.column(column).field for column in spec.columns}
        named = {field for field, _validator in spec.fields}
        assert named == resolved, (
            f"{spec.table} compares columns resolving to {sorted(str(f) for f in resolved)} "
            f"but attributes its validators to {sorted(named)}"
        )


def test_a_duplicate_key_on_either_side_is_refused_rather_than_collapsed() -> None:
    """CF10: `{row[key]: row}` drops rows silently, and the population then comes back short.

    Our side is protected by the bronze primary key; the export side is not ours and carries
    no such guarantee. A duplicated export row would otherwise present as a smaller-than-
    pinned population — a true symptom reported as entirely the wrong problem, in the one
    module whose purpose is refusing to pass vacuously.
    """
    from ootp_ai.validate.export_diff import DuplicateKeys, _key_by

    rows = [{"team_id": 1, "abbr": "SPR"}, {"team_id": 1, "abbr": "SHL"}]
    with pytest.raises(DuplicateKeys) as caught:
        _key_by(rows, "team_id", where="teams")
    assert "2 rows under 1 distinct team_id" in str(caught.value)

    assert _key_by([rows[0]], "team_id", where="teams") == {1: rows[0]}


def test_the_absence_rules_name_columns_that_exist() -> None:
    """A rule on a column nobody declares can never fire, and would never be noticed."""
    contracts = load_contracts()
    for rule in ABSENCE_RULES:
        declared = {column.name for column in contracts.table(rule.table).columns}
        if rule.column is not None:
            assert rule.column in declared, f"{rule.table} declares no {rule.column!r}"


def test_no_rating_column_is_compared_anywhere_in_the_harness() -> None:
    """Tier B can never be a rating validator, and this is the mechanical half of saying so.

    The export writes display scale — measured, `batting_ratings_overall_contact` carries
    12 distinct values across 20-80 — so a bucketed comparison passes a parser reading the
    adjacent `u16`. The prose says this; this makes extending the harness to a rating turn
    the suite red instead of turning a belief green.

    **Both rating categories, via the set `contracts/policy.py` already owns.** This tested
    `!= "rating-true"` and let `rating-scouted` straight through — the dangerous half, since
    the export's ratings are scale-converted *and* scout-filtered, which is exactly the
    scouted case. Importing the set also means a third rating category, if one is ever
    declared, is covered without anybody remembering to come back here.
    """
    contracts = load_contracts()
    for table, field, _validator in _all_pairs():
        category = contracts.field(field).category
        assert category not in RATING_CATEGORIES, (
            f"{table} compares {field!r}, whose category is {category!r}. Tier B is bucketed "
            "for ratings and can green-light a parser reading the adjacent field; "
            "`players.csv` is the only exact rating validator and always will be"
        )


def test_the_colour_slot_the_export_cannot_identify_is_not_compared() -> None:
    """Measured: `color_2` matches none of the export's eight colour columns on all 259.

    Its best candidate reaches 237. Comparing it would ship a 22-row failure as the
    harness's normal state; allowlisting it would be an allowlist standing in for an
    unfinished decode. So it is absent, and this pins that absence as a decision.
    """
    compared = {pair.column for pair in _TEAM_SPEC.columns}
    assert "color_1" in compared
    assert "color_3" in compared
    assert "color_2" not in compared, (
        "color_2 is being compared against an export column nothing has identified it with"
    )
    assert load_contracts().field("team_color_slot_2").epistemic == "measured"


def test_full_name_is_not_compared_because_the_export_has_no_such_column() -> None:
    """Recorded as a decision so its absence is not read as an oversight."""
    assert "full_name" not in {pair.column for pair in _TEAM_SPEC.columns}
    assert load_contracts().field("team_full_name").validator == "none"


def test_the_calendar_sequence_is_not_compared_because_the_export_omits_it() -> None:
    """`seq` is the file's own field, and that is why the key had to come from the bytes."""
    assert "seq" not in _EVENT_SPEC.columns
    assert len(_EVENT_SPEC.columns) == len(_EVENT_SPEC.export_columns) == 8


@pytest.mark.parametrize("spec", [*SPECS, *ROW_SPECS, DIVISION_SPEC])
def test_every_spec_pins_the_population_it_expects(spec: TableSpec | RowSpec) -> None:
    """A comparison that never states its expected size cannot notice comparing nothing."""
    assert spec.export_rows > 0, f"{spec.table} declares no expected export population"
