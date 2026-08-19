"""The single gate between a landed field and a page. Two outcomes, no bypass.

ADR 0012 is absolute about ratings: the GM reads what its scouts believe, never the
engine's true numbers, and CLAUDE.md's corollary is that an **unclassifiable field is
treated as a true rating** — "probably fine" is not a classification. This module is where
that stops being a paragraph.

## Why there are two renderable outcomes and not one

The first draft of this policy had a single gate that refused
``category == "rating-true"`` **or** ``epistemic in {"unconfirmed", "assumed"}``. That
second clause made the plan's own pre-registered fallbacks unreachable: the `list_id`
fallback renders roster groups by raw value *with a banner saying the meanings are
unconfirmed*, and a single gate blocks that field outright. The cheapest escape from an
unsatisfiable gate is to quietly upgrade a label — which is the exact failure the
labelling discipline exists to prevent.

So a low-confidence **non-rating** field is renderable only through
`render_with_uncertainty`, which forces the raw value plus a banner and cannot be reached
by the ordinary column route. A low-confidence **rating** has no such path: withheld is
withheld.

## What this module is not

It is not a formatter and it holds no data. Every function here is pure over a
`FieldEntry`, which is what lets the AC13 guard feed it synthetic entries and run in CI —
where no rating has landed and none ever will.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from ootp_ai.contracts.loader import Column, Contracts, FieldEntry, Table

__all__ = [
    "KNOWN_CATEGORIES",
    "LOW_CONFIDENCE",
    "NON_RATING_CATEGORIES",
    "RATING_CATEGORIES",
    "UNCERTAINTY_MARK",
    "WITHHELD_NAME_FRAGMENTS",
    "Disposition",
    "WithheldFieldError",
    "check_policy_covers",
    "column_disposition",
    "disposition",
    "is_renderable",
    "render_with_uncertainty",
    "uncertainty_banner",
]

#: Categories that describe a rating. `rating-true` is banned outright; `rating-scouted`
#: is what ADR 0012 says the GM may see — but only once its mapping has been proven.
RATING_CATEGORIES: Final = frozenset({"rating-true", "rating-scouted"})

#: Categories that describe something other than a rating. Enumerated rather than
#: inferred, because **the default is withheld**: a category this module has never heard
#: of is treated as a true rating, exactly as CLAUDE.md's corollary requires.
#:
#: The first draft got this backwards and fell through to RENDERABLE. Measured on the
#: shipped declaration, that released `unknown`, `scouting`, `rating-potential`, `""` and
#: even the case variant `RATING-TRUE` — release-by-default, in the module whose own
#: docstring quotes the opposite rule. The loader's vocabulary is not a second line of
#: defence here: it lives in the same tracked file whose author would be adding the
#: category, so two edits in one commit would pass both.
NON_RATING_CATEGORIES: Final = frozenset({"identity", "structural", "contract"})

#: Every category this module has an opinion about. `check_policy_covers` asserts the
#: declaration adds none this set is missing.
KNOWN_CATEGORIES: Final = RATING_CATEGORIES | NON_RATING_CATEGORIES

#: Labels that mean "we have not shown this is what we think it is". `docs/data-access.md`
#: is explicit that an unconfirmed claim is a task, not a fact.
LOW_CONFIDENCE: Final = frozenset({"unconfirmed", "assumed"})

#: The **secondary** check, and secondary is load-bearing: the category is the gate, and
#: these fragments only catch a field whose category someone got wrong. `_talent_` rather
#: than `talent_` because the real columns are `batting_ratings_talent_*` — the leading
#: form matched nothing at all, which is a guard that passes by never firing.
WITHHELD_NAME_FRAGMENTS: Final = ("prone_", "players_value", "_talent_")

#: Appended to every value that reaches a page through the uncertainty path, so the
#: caller cannot emit the raw value and forget the banner.
UNCERTAINTY_MARK: Final = " (unconfirmed)"


class Disposition(StrEnum):
    """What a field may do on a page."""

    RENDERABLE = "renderable"
    UNCERTAIN = "uncertain"
    WITHHELD = "withheld"


class WithheldFieldError(RuntimeError):
    """Something tried to render a field this policy does not release."""


def disposition(entry: FieldEntry) -> Disposition:
    """Decide what `entry` may do on a page.

    Withheld beats everything, and low confidence routes a non-rating to the banner path.
    """
    if _name_is_withheld(entry.name):
        return Disposition.WITHHELD
    if entry.category not in KNOWN_CATEGORIES:
        # Withhold-by-default, and the only branch here that is a *posture* rather than a
        # rule. An unrecognised category is an unclassified field, and CLAUDE.md's
        # corollary is that an unclassified field is treated as a true rating.
        return Disposition.WITHHELD
    if entry.category == "rating-true":
        return Disposition.WITHHELD
    if entry.epistemic in LOW_CONFIDENCE:
        # A rating we have not proven is not a candidate for a banner. The banner exists
        # for a field whose VALUE is solid and whose MEANING is not — `list_id` grouped by
        # raw integer. An unproven rating fails on both counts.
        if entry.category in RATING_CATEGORIES:
            return Disposition.WITHHELD
        return Disposition.UNCERTAIN
    return Disposition.RENDERABLE


def is_renderable(entry: FieldEntry) -> bool:
    """True only for the ordinary column route.

    Deliberately narrow: a field that needs the banner is **not** renderable, so a report
    that asks this question and takes yes for an answer can never print an unconfirmed
    value bare.
    """
    return disposition(entry) is Disposition.RENDERABLE


def render_with_uncertainty(entry: FieldEntry, value: object) -> str:
    """Render a low-confidence non-rating field, banner attached, or refuse.

    The only path to a page for a field `is_renderable` rejects — and it refuses anything
    the policy withholds, so it cannot be used as a way around the gate.
    """
    decided = disposition(entry)
    if decided is not Disposition.UNCERTAIN:
        raise WithheldFieldError(
            f"field {entry.name!r} is {decided.value}, not {Disposition.UNCERTAIN.value}; "
            "render_with_uncertainty is the path for a low-confidence non-rating field, "
            "never a way to release one this policy withholds"
        )
    return f"{value}{UNCERTAINTY_MARK}"


def uncertainty_banner(entry: FieldEntry) -> str:
    """The header line a report must carry when it renders `entry` through the banner."""
    decided = disposition(entry)
    if decided is not Disposition.UNCERTAIN:
        raise WithheldFieldError(
            f"field {entry.name!r} is {decided.value} and needs no uncertainty banner"
        )
    return (
        f"{entry.name}: raw values only — the mapping is {entry.epistemic} "
        f"(validator: {entry.validator}), so no label is offered and none should be read in"
    )


def column_disposition(contracts: Contracts, table: Table, column: Column) -> Disposition:
    """Decide a declared column, resolving its provenance through the field map.

    A column declared `provenance` is ours rather than the game's — `save_id`, `sim_date`,
    `ingest_seq`, and the label columns of `bronze_field_label`. Those are renderable: a
    report that could not print the snapshot it read from would be worse than useless,
    because a `gm/decisions/` record citing it could not be checked later.

    **The name check runs first, and on the COLUMN name.** It used to run only against a
    field entry's name, which left the fragment backstop guarding a surface no report ever
    reads — measured, a `batting_ratings_talent_contact` column with its `field` line
    simply omitted loaded clean, emitted into the DDL and returned renderable, while
    `_name_is_withheld` on the same string returned True the whole time. The loader now
    refuses a column that is neither declared provenance nor tied to a field, and this is
    the second lock on that door.
    """
    if _name_is_withheld(column.name):
        return Disposition.WITHHELD
    if column.field is None:
        return Disposition.RENDERABLE
    return disposition(contracts.field(column.field))


def check_policy_covers(contracts: Contracts) -> None:
    """Refuse a declaration whose vocabulary this policy has fallen behind.

    `warehouse/ddl.py` already does exactly this for column types, and the two are one
    rule: a token added to a tracked vocabulary and not taught to its consumer is a token
    whose behaviour nobody chose. Here the stakes are higher than an unrenderable type —
    an uncategorised field is released or withheld by accident.

    `disposition()` fails closed regardless, so this is the *loud* half rather than the
    safe half: without it a new category silently withholds every field under it, which
    is safe and looks like a bug in the report.
    """
    unknown = sorted(set(contracts.categories) - KNOWN_CATEGORIES)
    if unknown:
        raise WithheldFieldError(
            f"field_map.toml declares categories {unknown} that contracts/policy.py does "
            "not classify as rating or non-rating. Every field under them is withheld by "
            "default until the policy says which they are"
        )
    missing_labels = sorted(LOW_CONFIDENCE - set(contracts.epistemics))
    if missing_labels:
        raise WithheldFieldError(
            f"contracts/policy.py treats {missing_labels} as low confidence, but the "
            "declaration no longer offers those labels, so the uncertainty path is dead"
        )


def _name_is_withheld(name: str) -> bool:
    lowered = name.lower()
    return any(fragment in lowered for fragment in WITHHELD_NAME_FRAGMENTS)
