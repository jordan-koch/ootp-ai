"""The `teams.dat` walker's contract, provable with no game installed.

This is the CI half of Phase 5. Everything here runs offline, so a later change that
breaks the walker's *shape* — its refusals, its field set, its honesty about how much
of the file it accounted for — goes red on every PR rather than on the one machine
that has a save.

**What this module deliberately does not do is hand-build a `teams.dat` record.** The
record layout is being measured in this phase, not before it, and a fixture asserting a
layout nobody has read yet would be a guess wearing a test's clothes — green when the
parser agrees with the guess, red when the parser is right. The variable-length
invariant is therefore proven where the real bytes are, in
`tests/test_byte_accounting.py::test_team_records_are_not_all_the_same_length`, and
the fixed-offset ban is enforced structurally by `tests/test_no_fixed_offsets.py`.
What is left for here is everything that does not need the layout, which is more than
it sounds like.

The load-bearing one is the **tier declaration**. `teams.dat` is 4.5 MB across ~259
records — roughly 17.5 KB per team, against the 2,070 bytes of the whole saved-games
index. A zero-residual walk of it is a genuinely harder claim, and Phase 0
pre-registered a demotion to the diagnostic tier precisely so a research task cannot
park itself on the critical path. The hazard a demotion carries is that it happens
quietly, so it is made expensive to hide: the parser must *declare* its tier, the
declaration must be one of the values `tests/fixtures/tiers.py` pre-registers, and a
demotion must carry a written rationale. `tests/test_byte_accounting.py` then holds the
declaration to whatever the real file actually does.

The tier vocabulary moved to `tests/fixtures/tiers.py` in Phase 5b, when `world.dat`
needed the same guard: three modules declaring a tier against four private copies of the
legal set is how a vocabulary starts disagreeing with itself.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import get_args, get_origin, get_type_hints

import pytest

from fixtures.synthetic import make_header
from fixtures.tiers import KNOWN_TIERS
from ootp_ai.parser.errors import (
    MalformedHeader,
    SaveFilenameMismatch,
    SaveFormatError,
    UnsupportedSaveVersion,
)
from ootp_ai.parser.teams import (
    BYTE_ACCOUNTING_TIER,
    TEAMS_FILE,
    TIER_RATIONALE,
    TeamRecord,
    TeamsFile,
    read_teams,
)

#: Fields whose zero is a **value**, not an absence, so none of them may be typed
#: optional — and this bites harder here than anywhere else in the parser, because
#: `teams.dat` **omits an integer field entirely when its value is zero**. The walker
#: therefore reconstructs the zero from the field's absence. Getting that backwards —
#: landing `None` because the bytes held nothing — would erase the American League
#: (`sub_league_id` 0 on 242 of 259 teams) and every top-level club's parentlessness.
ZERO_IS_A_VALUE = (
    "level",
    "league_id",
    "sub_league_id",
    "parent_team_id",
    "city_id",
    "park_id",
    "nation_id",
)

#: String slots the writer is measured to drop, which must therefore be optional. An
#: earlier version of this module listed only `city` and `historical_id`, and the gap
#: was not academic: `logo_filename` shipped landing `""` on **289 of the managed
#: league's 337 records** while both probes carry a logo on every record — so the
#: export could never have caught it and no test asked. Anything the walk can find
#: missing belongs here, whether or not a probe happens to exercise it.
DROPPABLE_STRINGS = ("city", "logo_filename", "historical_id")


def _field_names(cls: type) -> frozenset[str]:
    assert is_dataclass(cls), f"{cls.__name__} is expected to be a dataclass"
    return frozenset(f.name for f in fields(cls))


def _is_optional(annotation: object) -> bool:
    return type(None) in get_args(annotation) and get_origin(annotation) is not None


# ── the field set is a decision, not an accident ─────────────────────────────


def test_a_team_record_carries_what_teams_dat_actually_holds_and_no_more() -> None:
    """Pinned so widening it is a deliberate edit to this file.

    **Four fields left this set on 2026-08-16, and the removals are the finding.**
    `division_id` and `allstar_team` are not in `teams.dat`: the six-field integer
    model reproduces 259 of 259 records in two independent saves, while inserting
    `division_id` scores 0 of 140 on the teams that have a non-zero one and appending
    `allstar_team` scores 0 of 30 on the All-Star sides — its own discriminating
    subset in each case. Division membership lives in `world.dat` as an explicit
    per-division team array, so `division_id` is **derived in silver, never parsed**.
    The standings region is not here either.

    `human_id` is gone for a different reason: the last slot of the integer run is
    either it or `human_team`, and no oracle can separate them — both columns are 1 on
    the single human club and 0 everywhere else. Landing one flag whose ambiguity is
    written down beats landing two fields when only one was observed.
    """
    assert _field_names(TeamRecord) == {
        "team_id",
        "city",
        "abbr",
        "nickname",
        "logo_filename",
        "full_name",
        "colors",
        "city_id",
        "park_id",
        "league_id",
        "sub_league_id",
        "nation_id",
        "human_team",
        "level",
        "parent_team_id",
        "historical_id",
    }


def test_a_meaningful_zero_cannot_be_typed_as_an_absence() -> None:
    """The structural-absence rule, enforced at the type rather than in review.

    `.claude/agents/data-engineer.md`: *"Structural absence is not missing data …
    averaging across that boundary produces wrong numbers, not incomplete ones."* The
    inverse error is the one available here — the record carries these fields on every
    team, and every value they hold is real. Making one optional invites the `or None`
    that silently deletes a sub-league.
    """
    hints = get_type_hints(TeamRecord)
    for name in ZERO_IS_A_VALUE:
        assert not _is_optional(hints[name]), (
            f"TeamRecord.{name} became optional. Its zero is a value, not an absence — "
            "sub_league_id 0 is the American League and parent_team_id 0 is every "
            "top-level club. Bronze must land 0, and the meaning of 0 is silver's job."
        )


def test_a_string_the_record_does_not_carry_is_none_rather_than_empty() -> None:
    """The other direction, and it is not symmetric with the integers.

    A string that is **absent from the byte stream** is `None`. Two live cases:
    `historical_id` is `''` on the All-Star clubs in the export, and — measured —
    **26 of 259 records carry no city string at all**, so the `verified` five-string
    signature is four strings on the minor-league All-Star sides. Landing `''` would
    make "no real-world franchise" indistinguishable from a franchise whose code is
    the empty string, and would hide that a quarter-of-a-hundred records have a
    different shape from the rest.
    """
    hints = get_type_hints(TeamRecord)
    for name in DROPPABLE_STRINGS:
        assert _is_optional(hints[name]), (
            f"{name} must be optional. The writer drops a string slot whose value is "
            "falsy, so an absent one and an empty one are the same bytes — and `''` "
            "asserts the club's value IS the empty string, which the file never said."
        )


def test_the_integers_and_the_strings_disagree_about_what_absence_means() -> None:
    """Both rules are right, and holding both at once is the whole trick.

    An omitted **integer** means zero, because the writer drops zero-valued integers.
    An omitted **string** means absent, because the writer has no such rule for
    strings. Applying either rule to the other kind of field produces a confidently
    wrong record with nothing raised, so the two are asserted together rather than in
    separate tests where one could quietly be deleted.
    """
    hints = get_type_hints(TeamRecord)
    integers = [name for name in ZERO_IS_A_VALUE if not _is_optional(hints[name])]
    strings = [name for name in DROPPABLE_STRINGS if _is_optional(hints[name])]
    assert len(integers) == len(ZERO_IS_A_VALUE)
    assert len(strings) == len(DROPPABLE_STRINGS)


def test_the_file_result_reports_what_it_could_not_account_for() -> None:
    """A walker that returns only records cannot be asked how much it missed."""
    assert _field_names(TeamsFile) == {"teams", "residual_bytes", "sim_date"}


# ── the tier declaration ─────────────────────────────────────────────────────


def test_the_byte_accounting_tier_is_declared_and_known() -> None:
    assert BYTE_ACCOUNTING_TIER in KNOWN_TIERS, (
        f"{BYTE_ACCOUNTING_TIER!r} is not a pre-registered tier. Phase 0 registered "
        f"exactly {sorted(KNOWN_TIERS)}; inventing a third is how a weakening ships "
        "without anyone disposing it."
    )


def test_a_demoted_tier_has_to_say_why() -> None:
    """The demotion is allowed. Doing it silently is not.

    The failure this guards is not a wrong number, it is a lost decision: six months
    on, `diagnostic` with no rationale is indistinguishable from nobody having tried.
    """
    if BYTE_ACCOUNTING_TIER == "strict":
        return
    assert len(TIER_RATIONALE.strip()) >= 80, (
        "the teams walk is at the diagnostic tier with no written rationale. Say what "
        "was reached, what was not, and what a later attempt should try first."
    )


def test_the_module_names_the_file_it_reads() -> None:
    assert TEAMS_FILE == "teams.dat"


# ── refusals ─────────────────────────────────────────────────────────────────


def test_a_file_that_is_not_a_save_is_refused() -> None:
    with pytest.raises(MalformedHeader):
        read_teams(b"not an OOTP file at all")


def test_the_magic_at_offset_zero_trap_is_refused() -> None:
    """`docs/data-access.md` §4: the magic begins at offset 1, after a leading null."""
    with pytest.raises(MalformedHeader):
        read_teams(make_header(filename=TEAMS_FILE, magic_at_offset_zero=True))


def test_a_future_game_version_is_refused_rather_than_guessed_at() -> None:
    """A patched game may move the layout. Every mapping here was measured on 25."""
    with pytest.raises(UnsupportedSaveVersion):
        read_teams(make_header(filename=TEAMS_FILE, version=26))


def test_a_header_naming_a_different_file_is_refused() -> None:
    """The free check that the path wiring is right, applied to this walker too."""
    with pytest.raises(SaveFilenameMismatch):
        read_teams(make_header(filename="players.dat"))


def test_an_empty_buffer_is_refused_rather_than_read_as_zero_teams() -> None:
    """Zero teams is a plausible-looking answer and a catastrophic one."""
    with pytest.raises(MalformedHeader):
        read_teams(b"")


def test_a_truncated_file_raises_instead_of_returning_a_short_league() -> None:
    """The whole argument for byte accounting, in one assertion.

    A walk that stops early and returns what it has produces a league missing clubs,
    with nothing raised and no way to notice downstream. `saved_games.py` established
    the pattern: run to exhaustion and let a lost alignment raise.
    """
    header_only = make_header(filename=TEAMS_FILE, sim_date=(18, 3, 2024))
    with pytest.raises(SaveFormatError):
        read_teams(header_only + b"\x01\x02\x03")
