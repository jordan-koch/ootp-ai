"""AC13 — the serving gate, proven on both sides.

ADR 0012 says the GM reads what its scouts believe and never the engine's true numbers,
and CLAUDE.md's corollary is that an unclassifiable field **is treated as a true rating**.
`contracts/policy.py` is where that becomes a function, and this is where the function is
shown to work.

## Why the negative cases are the point

A gate that withholds everything passes every "is this withheld?" test ever written and
delivers a blank page. So the suite below is deliberately symmetric:

* a `rating-true` field is withheld **whatever** its label, and
* a `rating-scouted` field with a proven label **is** renderable, and
* a low-confidence non-rating is reachable **only** through the banner path, and
* `render_with_uncertainty` refuses a field that is plainly renderable, so it cannot be
  used as a second door to the ordinary route either.

Miss any one of those and the guard is measuring its own shape rather than the policy.

## Synthetic entries, deliberately

The gate is a pure function over a `FieldEntry`, so these feed it entries built here. That
is what lets AC13 run in CI, where no rating has landed and — if ADR 0012 holds — none
ever will. The shipped `field_map.toml` is then checked as a separate, weaker claim: that
nothing in it is misfiled today.

The uncertainty branch has **one** real field: `calendar_real_sim_date`, whose label the
acceptance panel corrected from `verified` to `unconfirmed` (both it and the export are
zero on every row, so the answer key discriminates nothing). Before that correction the
branch was exercised by synthetic entries alone.

## The two fail-open holes this suite now pins

Both were found by the panel, and both released a rating rather than withholding one:

1. **`disposition()` fell through to RENDERABLE for any category it did not name** —
   `unknown`, `scouting`, `rating-potential`, `""` and even `RATING-TRUE` all rendered.
   The default is now withheld, which is what "an unclassifiable field is treated as a
   true rating" actually requires.
2. **A column with no `field` short-circuited to RENDERABLE** on the reasoning that such
   columns are provenance — which nothing enforced. A `batting_ratings_talent_contact`
   column with its `field` line omitted loaded, emitted and rendered.
"""

from __future__ import annotations

import pytest

from ootp_ai.contracts.loader import Column, Contracts, FieldEntry, load_contracts
from ootp_ai.contracts.policy import (
    LOW_CONFIDENCE,
    WITHHELD_NAME_FRAGMENTS,
    Disposition,
    WithheldFieldError,
    check_policy_covers,
    column_disposition,
    disposition,
    is_renderable,
    render_with_uncertainty,
    uncertainty_banner,
)

EVERY_EPISTEMIC = ("measured", "verified", "inferred", "assumed", "unconfirmed")


def entry(
    *,
    name: str = "synthetic_field",
    category: str = "identity",
    epistemic: str = "verified",
    validator: str = "export-exact-all-rows",
) -> FieldEntry:
    return FieldEntry(
        name=name,
        source="synthetic.dat",
        walker="nowhere.read_synthetic",
        save_type="u16",
        category=category,
        epistemic=epistemic,
        validator=validator,
    )


@pytest.fixture(scope="module")
def contracts() -> Contracts:
    return load_contracts()


# ── withheld, and no exceptions ──────────────────────────────────────────────


@pytest.mark.parametrize("epistemic", EVERY_EPISTEMIC)
def test_a_true_rating_is_withheld_whatever_its_label(epistemic: str) -> None:
    """ADR 0012 is absolute, so a `verified` true rating is withheld too.

    That case is the one worth parametrising for: proving the mapping does not license
    showing the number, and a policy keyed on confidence alone would release it.
    """
    field = entry(category="rating-true", epistemic=epistemic)
    assert disposition(field) is Disposition.WITHHELD
    assert not is_renderable(field)


@pytest.mark.parametrize("epistemic", sorted(LOW_CONFIDENCE))
def test_an_unproven_scouted_rating_is_withheld_rather_than_bannered(epistemic: str) -> None:
    """The banner is for a solid value with an unknown meaning, not for an unproven rating.

    A rating we have not shown we are reading correctly fails on both counts, so it takes
    the withheld branch rather than the uncertainty one.
    """
    assert (
        disposition(entry(category="rating-scouted", epistemic=epistemic)) is Disposition.WITHHELD
    )


@pytest.mark.parametrize(
    "category", ["unknown", "scouting", "rating-potential", "", "RATING-TRUE", "identity "]
)
def test_a_category_the_policy_does_not_know_is_withheld(category: str) -> None:
    """**Withhold-by-default, which the first draft had backwards.**

    Every value here was measured returning `renderable` before the fix, at
    `epistemic = "verified"` — including the case variant of the one category that is
    banned outright and a trailing-space variant of a legitimate one. The loader's
    vocabulary is not a second line of defence: it lives in the same tracked file whose
    author would be adding the category, so one commit passes both gates.
    """
    field = entry(category=category, epistemic="verified")
    assert disposition(field) is Disposition.WITHHELD
    assert not is_renderable(field)


def test_the_policy_classifies_every_category_the_declaration_declares(
    contracts: Contracts,
) -> None:
    """The loud half of the same rule, mirroring `ddl.py`'s guard for column types.

    Failing closed is safe and silent: a new category would withhold every field under it
    and look like a bug in the report. This makes the omission say so.
    """
    check_policy_covers(contracts)


@pytest.mark.parametrize("fragment", WITHHELD_NAME_FRAGMENTS)
def test_a_fieldless_column_named_like_a_rating_is_withheld(
    contracts: Contracts, fragment: str
) -> None:
    """The column-name surface the fragment check was corrected for but never guarded.

    `_name_is_withheld` had exactly one call site and was only ever passed a *field* name,
    so the backstop could not see the door a fieldless column opened. The loader now
    refuses a column that declares neither `field` nor `provenance`; this is the second
    lock, and it holds even for a column that somehow reached the gate.
    """
    table = contracts.table("bronze_player")
    planted = Column(
        name=f"batting_ratings{fragment}contact", column_type="u8", nullable=True, provenance=True
    )
    assert column_disposition(contracts, table, planted) is Disposition.WITHHELD


@pytest.mark.parametrize("fragment", WITHHELD_NAME_FRAGMENTS)
def test_the_name_fragments_catch_a_miscategorised_rating(fragment: str) -> None:
    """The secondary check, and secondary is load-bearing.

    The category is the gate. These fragments exist for the day someone files
    `batting_ratings_talent_contact` as `structural` — a wrong category should not be
    enough on its own to put a true rating on a page.
    """
    field = entry(name=f"batting_ratings{fragment}contact", category="structural")
    assert disposition(field) is Disposition.WITHHELD


def test_the_talent_fragment_is_the_corrected_one() -> None:
    """`talent_%` matched nothing; the real columns are `batting_ratings_talent_*`.

    A pattern that cannot match is a guard that passes by never firing, which is why the
    plan corrected it to `%_talent_%`. Both halves asserted, so a "simplification" back to
    the leading form turns this red.
    """
    real_column = "batting_ratings_talent_contact"
    assert not real_column.startswith("talent_"), "the leading pattern would match nothing"
    assert "_talent_" in real_column
    assert "_talent_" in WITHHELD_NAME_FRAGMENTS


# ── renderable, which is the half a blanket ban would also pass ──────────────


def test_a_proven_scouted_rating_is_renderable() -> None:
    """**AC13's negative case.** ADR 0012 withholds the truth, not the scout's opinion.

    If this ever goes red the gate has become a blanket ban, and the front office has no
    ratings at all — which passes every withholding test and delivers nothing.
    """
    field = entry(name="scouted_contact", category="rating-scouted", epistemic="verified")
    assert disposition(field) is Disposition.RENDERABLE
    assert is_renderable(field)


@pytest.mark.parametrize("category", ["identity", "structural", "contract"])
def test_a_proven_non_rating_is_renderable(category: str) -> None:
    assert is_renderable(entry(category=category, epistemic="measured"))


def test_provenance_columns_are_renderable(contracts: Contracts) -> None:
    """A report that could not print the snapshot it read from would be unciteable.

    `save_id`, `sim_date` and `ingest_seq` carry no field-map entry because no walker
    produced them; they are ours, and line one of every report names them.
    """
    table = contracts.table("bronze_team")
    for name in ("save_id", "sim_date", "ingest_seq"):
        column = table.column(name)
        assert column.field is None
        assert column_disposition(contracts, table, column) is Disposition.RENDERABLE


# ── the uncertainty path, and the two doors it does not open ─────────────────


@pytest.mark.parametrize("epistemic", sorted(LOW_CONFIDENCE))
def test_a_low_confidence_non_rating_is_reachable_only_through_the_banner(epistemic: str) -> None:
    """The corrected two-outcome policy, in one test.

    A single gate refusing `rating-true` OR low confidence made the plan's own
    pre-registered `list_id` fallback unreachable — and the cheapest escape from an
    unsatisfiable gate is to quietly upgrade a label, which is the exact failure the
    labelling discipline exists to prevent.
    """
    field = entry(name="list_id", category="structural", epistemic=epistemic, validator="none")
    assert disposition(field) is Disposition.UNCERTAIN
    assert not is_renderable(field), "the ordinary column route must not reach it"
    assert render_with_uncertainty(field, 3) == "3 (unconfirmed)"


def test_the_banner_names_the_label_and_the_validator() -> None:
    """So a reader can tell *how* unconfirmed, and go re-run the check that said so."""
    field = entry(name="list_id", category="structural", epistemic="unconfirmed", validator="none")
    banner = uncertainty_banner(field)
    assert "list_id" in banner
    assert "unconfirmed" in banner
    assert "none" in banner


def test_render_with_uncertainty_refuses_a_withheld_field() -> None:
    """Not a back door. The banner path releases nothing the gate withholds."""
    field = entry(category="rating-true", epistemic="unconfirmed")
    with pytest.raises(WithheldFieldError) as raised:
        render_with_uncertainty(field, 70)
    assert field.name in str(raised.value)
    assert "withheld" in str(raised.value)


def test_render_with_uncertainty_refuses_a_plainly_renderable_field() -> None:
    """Not a front door either.

    If a proven field could take the banner path, every report could stamp
    "(unconfirmed)" on solid data and the marker would stop meaning anything.
    """
    with pytest.raises(WithheldFieldError):
        render_with_uncertainty(entry(), "Boston")


def test_the_banner_refuses_a_field_that_does_not_need_one() -> None:
    with pytest.raises(WithheldFieldError):
        uncertainty_banner(entry())


# ── the shipped declaration, checked as the weaker separate claim ────────────


def test_no_true_rating_in_the_shipped_map_is_renderable(contracts: Contracts) -> None:
    withheld = [field.name for field in contracts.fields if not is_renderable(field)]
    assert withheld, "nothing in the shipped map is withheld, which cannot be right"
    for field in contracts.fields:
        if field.category == "rating-true":
            assert not is_renderable(field), f"{field.name} is a true rating and reaches a page"


def test_every_unclassified_region_is_withheld(contracts: Contracts) -> None:
    """ "Probably fine" is not a classification.

    The crossed-but-unclassified spans of `players.dat` and the two unread `names.dat`
    regions are filed `rating-true` precisely so this holds — the withhold-by-default
    posture, asserted rather than assumed.
    """
    for name in ("unclassified_before_masks", "name_category", "name_usage_pairs"):
        assert disposition(contracts.field(name)) is Disposition.WITHHELD


def test_every_declared_column_resolves_to_a_disposition(contracts: Contracts) -> None:
    """There is no third answer and no column without one.

    Phase 10 routes every report column through this gate, so a column the gate cannot
    decide would be a column with no policy at all.
    """
    for table in contracts.tables:
        for column in table.columns:
            assert isinstance(column_disposition(contracts, table, column), Disposition)


#: Columns bronze lands whose field the policy withholds — each with the argument for
#: landing it. **Landing and rendering are different acts**, and this is the seam: bronze
#: is 1:1 with what the walker read, while the gate decides what reaches a page. An entry
#: here is a deliberate act with a reason attached, which is the opposite of a column
#: nobody noticed.
LANDED_BUT_WITHHELD = {
    "bronze_name.name_category": (
        "The u8 leading each names.dat record. Withheld because it is unclassified — the "
        "obvious given-name/surname reading is REFUTED (6,668 of the indices players use "
        "as a last name point at 0x27 records) — and landed because it is evidence: "
        "keeping the byte lets a later slice re-examine it as a query instead of a "
        "re-parse. Nothing joins on it and the gate keeps it off every page."
    ),
}


#: Landed columns whose field renders only behind the uncertainty banner. Same discipline
#: as above and a different outcome: the value is solid, the meaning is not.
LANDED_UNDER_BANNER = {
    "bronze_league_event.real_sim_date": (
        "The u16 closing each calendar event. Measured 0 on all 3,058 entries of all three "
        "saves AND 0 in the export, so the row-for-row match proves nothing about it — a "
        "parser reading an adjacent zero u16 scores identically. Landed because the walk "
        "read it and dropping it would lose the evidence; rendered only under a banner "
        "until a mid-season save with a partially-simulated calendar says what it means."
    ),
}


def _landed_columns_by_disposition(contracts: Contracts, wanted: Disposition) -> set[str]:
    return {
        f"{table.name}.{column.name}"
        for table in contracts.tables
        for column in table.columns
        if column.field is not None and column_disposition(contracts, table, column) is wanted
    }


@pytest.mark.parametrize(
    ("wanted", "allowlist"),
    [
        (Disposition.WITHHELD, LANDED_BUT_WITHHELD),
        (Disposition.UNCERTAIN, LANDED_UNDER_BANNER),
    ],
    ids=["withheld", "under-banner"],
)
def test_landed_non_renderable_columns_are_exactly_the_argued_ones(
    contracts: Contracts, wanted: Disposition, allowlist: dict[str, str]
) -> None:
    """A column the gate will not print plainly has to be argued for, not noticed later.

    The rule is not "withheld fields are never landed" — bronze keeps what the walk read,
    and a consumed-but-unclassified region is evidence. The rule is that each one is listed
    with its reason, so adding the next costs a sentence rather than a shrug.
    """
    landed = _landed_columns_by_disposition(contracts, wanted)
    assert landed == set(allowlist), (
        f"landed {wanted.value} columns changed; add the new one with its argument, or stop "
        f"landing it. Unlisted: {sorted(landed - set(allowlist))}. "
        f"Listed but no longer landed: {sorted(set(allowlist) - landed)}"
    )
    for reason in allowlist.values():
        assert len(reason) > 80, "an argument that short is not an argument"


def test_the_uncertainty_path_has_a_real_field_and_not_only_synthetic_ones(
    contracts: Contracts,
) -> None:
    """`calendar_real_sim_date`, the label the Phase 8a panel corrected.

    It was declared `verified` on a validator that discriminates nothing — both sides of
    the comparison are zero on every row — inside the change that built a loader to stop
    exactly that. Pinning it here means the banner branch is exercised against the shipped
    declaration and not only against entries this file builds.
    """
    field = contracts.field("calendar_real_sim_date")
    assert field.epistemic == "unconfirmed"
    assert disposition(field) is Disposition.UNCERTAIN
    assert "0" in render_with_uncertainty(field, 0)
