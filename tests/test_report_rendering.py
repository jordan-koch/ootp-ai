"""The roster report's pure half, offline — because the gamedata half has no CI signal.

`tests/test_reports.py` proves AC14 against a real warehouse and a real save, and CI has
neither. §4.1 of the plan is explicit that *"a phase proved only by `gamedata` tests has
zero CI signal — a later change can break it and nothing goes red until someone runs the
local suite."* Phase 8b answered that with `test_bronze_landing.py` and Phase 9 with
`test_export_diff.py`; this is the same argument for the same reason, and this module is
the third instance of it.

What is pure here is more than it looks: the serving gate, the club grouping, the
structural-absence markers, the handedness mapping, the snapshot path partitioning and the
date parsing all run without a database. Only the SQL does not, and the SQL is what the
gamedata module exists for.

## The two assertions that matter most

**A withheld column aborts the report**, and it does so from *any* position in the column
list. A gate that checks `columns[0]` and stops passes every naive test and ships a page
with a rating on it.

**An unmapped handedness value renders as itself.** `bats` is `verified` against the export
on all 18,072 rows today, so the mapping is right today. If a game patch ever adds a fourth
value, printing `4` sends someone to look; printing `R` is a confidently wrong fact about a
player the GM is about to trade.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fixtures.reports import NAME_PATTERN
from ootp_ai.contracts.loader import Contracts, load_contracts
from ootp_ai.contracts.policy import WithheldFieldError
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.parser.rosters import LIST_ACTIVE, LIST_ASSIGNMENT, LIST_SECONDARY
from ootp_ai.reports.__main__ import _parse_sim_date
from ootp_ai.reports.resolve import SnapshotRef, report_dir
from ootp_ai.reports.roster import (
    ABSENT,
    REPORT_COLUMNS,
    SELECTED_COLUMNS,
    Club,
    ReportColumn,
    RosterRow,
    check_renderable,
    club_display_name,
    list_label_mode,
    name_join_predicate,
    render_roster,
)

SIM_DATE = SaveDate(day=7, month=3, year=2024)

#: A column of the shipped declaration that the policy really does withhold — measured:
#: `name_category` is `u8, leading each record` and is filed as unclassified, so
#: withhold-by-default catches it. Using a real one rather than a synthetic entry means
#: this test also fails if the shipped declaration ever quietly reclassifies it.
WITHHELD_COLUMN = ReportColumn(header="Name category", table="bronze_name", column="name_category")


@pytest.fixture
def contracts() -> Contracts:
    return load_contracts()


def ref(*, ingest_seq: int = 1, human_team_id: int | None = 3) -> SnapshotRef:
    return SnapshotRef(
        save_id="Test-Save",
        sim_date=SIM_DATE,
        ingest_seq=ingest_seq,
        human_team_id=human_team_id,
    )


def player(
    *,
    player_id: int = 1,
    first: str | None = "Rafael",
    last: str | None = "Devers",
    age: int | None = 27,
    bats: int | None = 2,
    throws: int | None = 1,
    number: int | None = 11,
    team_id: int | None = 3,
    memberships: tuple[tuple[int, int], ...] = ((3, LIST_ACTIVE),),
) -> RosterRow:
    return RosterRow(
        player_id=player_id,
        first_name=first,
        last_name=last,
        age=age,
        bats=bats,
        throws=throws,
        uniform_number=number,
        team_id=team_id,
        memberships=memberships,
    )


CLUBS = {
    3: Club(team_id=3, abbr="BOS", name="Boston Red Sox", level=1),
    9: Club(team_id=9, abbr="WOR", name="Worcester Red Sox", level=2),
    22: Club(team_id=22, abbr="SAL", name="Salem Red Sox", level=5),
}


def page(rows: tuple[RosterRow, ...], *, snapshot: SnapshotRef | None = None) -> str:
    return render_roster(snapshot or ref(), rows, CLUBS, club_name="Boston Red Sox")


def section(rendered: str, heading: str) -> str:
    """One `##` section of the page, sub-headings included.

    Anchored on a newline so `## ` cannot match the `### ` club headings nested inside —
    the naive `split("## ")` matches those too and silently returns an empty section, which
    reads as "the player is missing" rather than "the test's splitter is wrong".
    """
    after = rendered.split(f"\n## {heading}")
    assert len(after) == 2, f"expected exactly one '## {heading}' section"
    return after[1].split("\n## ")[0]


# ── the serving gate ─────────────────────────────────────────────────────────


def test_every_report_column_is_renderable_against_the_shipped_declaration(
    contracts: Contracts,
) -> None:
    """The positive half. A gate that withholds everything would pass the negative alone."""
    check_renderable(contracts, REPORT_COLUMNS)


def test_a_withheld_column_aborts_the_report(contracts: Contracts) -> None:
    with pytest.raises(WithheldFieldError) as raised:
        check_renderable(contracts, (WITHHELD_COLUMN,))
    message = str(raised.value)
    assert "name_category" in message, f"the refusal must name the column: {message}"
    assert "withheld" in message


def test_the_gate_checks_every_column_and_not_merely_the_first(contracts: Contracts) -> None:
    """Anti-vacuity: the withheld column goes LAST.

    A gate that inspected `columns[0]`, or that broke out of its loop on the first
    renderable column, would pass every other test in this module and ship a page with a
    rating on it. This is the arrangement that can tell the difference.
    """
    with pytest.raises(WithheldFieldError):
        check_renderable(contracts, (*REPORT_COLUMNS, WITHHELD_COLUMN))


def test_every_declared_report_column_names_a_real_table_and_column(
    contracts: Contracts,
) -> None:
    """A column pointing at nothing cannot be gated, so it must not be declarable.

    `check_renderable` resolves through `contracts.table(...)`/`table.column(...)`, both of
    which raise on an unknown name — this pins that the shipped column list actually
    resolves, rather than relying on the gate to notice later.
    """
    for entry in REPORT_COLUMNS:
        table = contracts.table(entry.table)
        assert table.column(entry.column).name == entry.column


def test_the_gate_covers_exactly_the_columns_the_queries_select() -> None:
    """The claim "every value on the page is gated", as a test rather than a sentence.

    Congruence in both directions. A selected column missing from the gate is a value
    reaching the page unchecked — the defect the acceptance panel found, where the club
    headings printed `city`, `nickname` and `level` ungated while their sibling `abbr` was
    declared. A gated column nobody selects is the opposite failure: a guard aimed at
    nothing, reporting coverage it does not have.
    """
    gated = {(entry.table, entry.column) for entry in REPORT_COLUMNS}
    ungated = sorted(SELECTED_COLUMNS - gated)
    assert not ungated, f"these columns are selected but never gated: {ungated}"
    unselected = sorted(gated - SELECTED_COLUMNS)
    assert not unselected, f"these columns are gated but never selected: {unselected}"


def test_the_name_join_binds_every_column_of_the_declared_key(contracts: Contracts) -> None:
    """The 4x fan-out guard, and the only CI signal it has.

    `bronze_name`'s key is five columns and the join bound four, which is correct only
    while exactly one `name_space` exists — the assumption `tables.toml` explicitly refuses
    to make, since "the wrong key would collide two spaces silently". Measured by the
    panel: with a second space present, a 226-player organisation returns 904 rows under
    fabricated first/last combinations. The only assertion that would have caught it is
    `gamedata`, so CI had nothing.
    """
    predicate = name_join_predicate("fn", "first_name_index")
    for column in contracts.table("bronze_name").key:
        assert f"`{column}`" in predicate, (
            f"the name join does not bind {column!r}, which is part of bronze_name's "
            f"declared key {list(contracts.table('bronze_name').key)}"
        )


def test_the_roster_list_fallback_is_reachable_rather_than_merely_documented(
    contracts: Contracts,
) -> None:
    """SD-17, proven to fire — it was prose until the panel simulated the downgrade.

    Downgrading `roster_membership` to `unconfirmed` must stop the page printing "Active
    roster" and put a banner on it instead. Before this, `check_renderable` passed and the
    report went on printing human labels with nothing red: no code in the package had ever
    called `render_with_uncertainty` or `uncertainty_banner`.
    """
    labels, banner = list_label_mode(contracts)
    assert labels is True and banner is None, "the shipped mapping is verified; labels hold"

    downgraded = replace(
        contracts,
        fields=tuple(
            replace(field, epistemic="unconfirmed") if field.name == "roster_membership" else field
            for field in contracts.fields
        ),
    )
    labels, banner = list_label_mode(downgraded)
    assert labels is False, "a downgraded list_id mapping must stop the human labels"
    assert banner is not None and "unconfirmed" in banner

    rendered = render_roster(
        ref(),
        (player(),),
        CLUBS,
        club_name="Boston Red Sox",
        list_labels=labels,
        list_banner=banner,
    )
    assert "Active roster" not in rendered, "a downgraded mapping still printed a human label"
    assert "list_id = 2" in rendered, "the raw-id fallback heading is missing"
    assert banner in rendered, "the uncertainty banner never reached the page"


def test_a_downgraded_list_id_still_passes_the_gate_because_it_has_a_fallback(
    contracts: Contracts,
) -> None:
    """The uncertainty path is a route, not a hole.

    `list_id` is the one value allowed to be UNCERTAIN, because SD-17 pre-registered what
    to do about it. Every other column has no fallback and must still abort — otherwise
    `may_be_uncertain` would be a way to wave anything through.
    """
    downgraded = replace(
        contracts,
        fields=tuple(
            replace(field, epistemic="unconfirmed") if field.name == "roster_membership" else field
            for field in contracts.fields
        ),
    )
    check_renderable(downgraded, REPORT_COLUMNS)

    no_fallback = replace(
        contracts,
        fields=tuple(
            replace(field, epistemic="unconfirmed") if field.name == "age" else field
            for field in contracts.fields
        ),
    )
    with pytest.raises(WithheldFieldError, match="uncertain"):
        check_renderable(no_fallback, REPORT_COLUMNS)


# ── provenance on line one ───────────────────────────────────────────────────


def test_line_one_names_the_club_the_sim_date_and_the_ingest_seq() -> None:
    """All three, because the seq is what makes a citation checkable once a date repeats."""
    rendered = page((player(),), snapshot=ref(ingest_seq=4))
    head = "\n".join(rendered.splitlines()[:4])
    assert "Boston Red Sox" in head
    assert "2024-03-07" in head
    assert "4" in head
    assert "Test-Save" in head


def test_the_ingest_seq_on_the_page_follows_the_snapshot_it_rendered() -> None:
    """The seq is read from the ref, not hardcoded — the failure a constant would hide."""
    assert "**Ingest seq** 7" in page((player(),), snapshot=ref(ingest_seq=7))


# ── the grain: a player may appear more than once ────────────────────────────


def test_a_player_on_two_clubs_lists_appears_under_both() -> None:
    """The 935-player fan-out. De-duplicating would lose exactly what the grain keeps."""
    prospect = player(
        player_id=42,
        first="Roman",
        last="Anthony",
        memberships=((3, LIST_SECONDARY), (9, LIST_ASSIGNMENT)),
    )
    rendered = page((prospect,))
    assert "Roman Anthony" in section(rendered, "Secondary (40-man) roster")
    assert "Roman Anthony" in section(rendered, "Assigned to the club")


def test_a_player_on_no_list_is_named_rather_than_dropped() -> None:
    """The 176-per-save population `bronze_team_roster` structurally cannot hold."""
    unrostered = player(player_id=99, first="Ghost", last="Player", memberships=())
    rendered = page((unrostered,))
    unlisted = section(rendered, "On the organisation's books, on no roster list")
    assert "Ghost Player" in unlisted
    assert unlisted.splitlines()[0].strip() == "— 1"


def test_an_empty_list_says_so_rather_than_rendering_a_bare_heading() -> None:
    rendered = page((player(memberships=((3, LIST_ACTIVE),)),))
    injured = section(rendered, "Injured list")
    assert "No player of this organisation holds a `list_id = 4` row" in injured


# ── structural absence, never a zero and never a guess ───────────────────────


def test_absent_values_render_as_the_marker_and_not_as_zero() -> None:
    """`—`, not `0`. A missing uniform number is not number zero."""
    unknown = player(age=None, bats=None, throws=None, number=None)
    rendered = page((unknown,))
    row = next(line for line in rendered.splitlines() if "Rafael Devers" in line)
    assert row.count(ABSENT) >= 3, row
    assert "| 0 |" not in row


def test_a_player_whose_name_did_not_resolve_is_not_rendered_as_an_id() -> None:
    """A failed name join must look like a failure, not like a player called 47035."""
    nameless = player(player_id=47035, first=None, last=None)
    rendered = page((nameless,))
    row = next(line for line in rendered.splitlines() if "47035" in line)
    assert row.startswith(f"| {ABSENT} |"), row


@pytest.mark.parametrize(
    ("bats", "throws", "expected"),
    [
        (1, 1, "R/R"),
        (2, 1, "L/R"),
        (3, 1, "S/R"),
        (2, 2, "L/L"),
        (None, 1, f"{ABSENT}/R"),
        (1, None, f"R/{ABSENT}"),
    ],
)
def test_handedness_uses_the_verified_mapping(
    bats: int | None, throws: int | None, expected: str
) -> None:
    rendered = page((player(bats=bats, throws=throws),))
    row = next(line for line in rendered.splitlines() if "Rafael Devers" in line)
    assert f"| {expected} |" in row


def test_an_unmapped_handedness_value_renders_as_itself() -> None:
    """The confidently-wrong guard.

    The mapping is `verified` against the export on every row *today*. A game patch adding
    a fourth `bats` value must not silently become `R` — the one outcome that is worse than
    an unrecognised integer on the page.
    """
    rendered = page((player(bats=9, throws=1),))
    row = next(line for line in rendered.splitlines() if "Rafael Devers" in line)
    assert "| 9/R |" in row


# ── club ordering and naming ─────────────────────────────────────────────────


def test_the_human_club_is_rendered_first_then_affiliates_by_level() -> None:
    """A GM's roster opens with the major-league club, not with a rookie-league side."""
    rows = (
        player(player_id=1, last="Salem", memberships=((22, LIST_ACTIVE),)),
        player(player_id=2, last="Worcester", memberships=((9, LIST_ACTIVE),)),
        player(player_id=3, last="Boston", memberships=((3, LIST_ACTIVE),)),
    )
    rendered = page(rows)
    order = [line for line in rendered.splitlines() if line.startswith("### ")]
    assert order[0].startswith("### Boston Red Sox")
    assert order[1].startswith("### Worcester Red Sox")
    assert order[2].startswith("### Salem Red Sox")


def test_a_club_the_landing_does_not_name_sorts_last_rather_than_raising() -> None:
    """An unresolvable id is a data question, not a reason to withhold the whole page."""
    rows = (
        player(player_id=1, last="Stranger", memberships=((777, LIST_ACTIVE),)),
        player(player_id=2, last="Boston", memberships=((3, LIST_ACTIVE),)),
    )
    rendered = page(rows)
    headings = [line for line in rendered.splitlines() if line.startswith("### ")]
    assert headings[0].startswith("### Boston Red Sox")
    assert "team 777" in headings[-1]


@pytest.mark.parametrize(
    ("team_id", "clubs", "expected"),
    [
        (3, CLUBS, "Boston Red Sox"),
        (None, CLUBS, "unknown club"),
        (404, CLUBS, "team 404"),
        (7, {7: Club(team_id=7, abbr="AAS", name="", level=9)}, "AAS"),
    ],
)
def test_club_display_name_falls_back_through_what_exists(
    team_id: int | None, clubs: dict[int, Club], expected: str
) -> None:
    """26 of 259 records carry no city, so every fallback here is a real save's case."""
    assert club_display_name(clubs, team_id) == expected


# ── the page says what it is not showing ─────────────────────────────────────


def test_the_page_names_position_as_not_landed() -> None:
    """The request's second outcome: the GM prices a gap it can see."""
    rendered = page((player(),))
    assert "## What this page does not show" in rendered
    assert "**Position.** Not landed" in rendered


def test_the_multi_club_count_describes_the_rows_rendered() -> None:
    """The figure is computed, not remembered — and this test can now tell the difference.

    It previously asserted `"935" in page(...)`, which protected the error rather than
    catching it: 935 is the probe save's global 40-man row count, wrong for any real
    landing by roughly 27x, printed in the `Measured` register a few lines under the page's
    own promise that every figure on it comes from this snapshot.
    """
    spanning = (
        player(
            player_id=1, last="Spanning", memberships=((3, LIST_SECONDARY), (9, LIST_ASSIGNMENT))
        ),
        player(player_id=2, last="Also", memberships=((3, LIST_SECONDARY), (22, LIST_ASSIGNMENT))),
        player(player_id=3, last="Single", memberships=((3, LIST_ACTIVE),)),
    )
    rendered = page(spanning)
    assert "2 of this organisation's 3 players appear under more than one club" in rendered


def test_a_roster_with_no_fan_out_says_zero_rather_than_a_remembered_number() -> None:
    rendered = page((player(memberships=((3, LIST_ACTIVE),)),))
    assert "0 of this organisation's 1 players" in rendered
    assert "935" not in rendered


def test_the_page_names_the_standings_as_not_landed() -> None:
    """The gap the operator chose to ship with, stated on the page rather than left blank.

    Phase 10 dropped the standings report because no declared table carries a W-L column.
    A GM that cannot see the standings should be told they do not exist, not left to infer
    it from an absence.
    """
    assert "Win-loss records and the standings" in page((player(),))


# ── the snapshot seam an incremental warehouse turns on ──────────────────────


def test_report_dir_partitions_by_the_whole_triple() -> None:
    assert report_dir(Path("out"), ref(ingest_seq=2)) == Path("out/Test-Save/2024-03-07/2")


def test_a_second_sequence_of_one_date_writes_beside_the_first_not_over_it() -> None:
    """Re-rendering must never overwrite the bytes a past decision was made from."""
    first = report_dir(Path("out"), ref(ingest_seq=1))
    second = report_dir(Path("out"), ref(ingest_seq=2))
    assert first != second
    assert first.parent == second.parent


def test_a_later_sim_date_writes_a_different_directory() -> None:
    """The time-progression axis, which is the other half of append-only."""
    later = SnapshotRef(
        save_id="Test-Save",
        sim_date=SaveDate(day=14, month=3, year=2024),
        ingest_seq=1,
        human_team_id=3,
    )
    assert report_dir(Path("out"), ref()) != report_dir(Path("out"), later)


def test_re_rendering_the_same_triple_is_idempotent_in_its_path() -> None:
    assert report_dir(Path("out"), ref()) == report_dir(Path("out"), ref())


# ── the date argument ────────────────────────────────────────────────────────


def test_an_absent_sim_date_means_the_latest_landed() -> None:
    assert _parse_sim_date(None) is None


def test_a_sim_date_round_trips_through_its_text_form() -> None:
    parsed = _parse_sim_date("2024-03-07")
    assert parsed is not None
    assert str(parsed) == "2024-03-07"


@pytest.mark.parametrize("raw", ["2024-03", "07-03-2024-1", "not-a-date", "2024/03/07", ""])
def test_a_malformed_sim_date_is_refused(raw: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        _parse_sim_date(raw)


# ── AC14's name pattern, guarded offline so the widening cannot be undone ────


@pytest.mark.parametrize(
    "name",
    [
        "Rafael Devers",
        "Tyler O'Neill",
        "de la Cruz Jr.",
        "José Ramírez",
        "Carlos Rodón",
        "Yū Darvish",
        "Ángel Álvarez",
    ],
)
def test_the_name_pattern_accepts_a_name_in_any_script(name: str) -> None:
    """`names.dat` is latin-1 and the landed table holds 1,623 accented entries.

    An ASCII-only pattern is green only while the organisation happens to hold none of
    them, and turns red on a *correct* render the first time one arrives.
    """
    assert NAME_PATTERN.match(name), f"{name!r} is a name and must pass"


@pytest.mark.parametrize("value", ["47035", "—", "0", "_hidden", "3Com", " leading"])
def test_the_name_pattern_still_rejects_everything_that_is_not_a_name(value: str) -> None:
    """The property the assertion exists for, preserved through the widening.

    The whole point is that no id can satisfy it — widening to Unicode must not widen to
    digits.
    """
    assert not NAME_PATTERN.match(value), f"{value!r} is not a name and must fail"
