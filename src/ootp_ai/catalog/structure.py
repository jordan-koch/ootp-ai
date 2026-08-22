"""The structural half of the catalog, built from the tracked declarations alone.

No connection, no snapshot, no clock. Everything here is a pure function of
`contracts/tables.toml` and `contracts/field_map.toml`, which is what makes the tracked
file byte-deterministic and therefore assertable: `tests/test_catalog.py` rebuilds this
model during the test run and refuses any byte that differs from the committed copy.

**Determinism is a property of this module, not of a convention.** Tables sort by name
rather than by declaration order, every derived list is sorted, and nothing here reads a
timestamp, a path, a hostname or git. A single non-deterministic value would make the
byte-identity assertion flap, and a flapping guard gets deleted.

## Why the withheld summary is truncated by a rule rather than by hand

Acceptance criterion 15 requires that **no rating column name appears anywhere in the
catalog**, and the declared reasons are working notes that name them freely — the
`position, role` entry cites the `prone_*` quad in its second sentence, because that is
where the decode actually stops. Reproducing the reason verbatim would publish exactly
the names the serving gate exists to keep off a page.

So the summary takes whole sentences from the head of the reason while two conditions
hold: the sentence carries no withheld name fragment, and the result stays inside a
budget. The declaration keeps the full argument; the catalog carries as much of it as it
can say safely, and names where the rest is. The alternative — a hand-written one-liner
per group — is the thing scope folded-in §3 rules out for coverage statements, and it
would go stale the same way.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Final

from ootp_ai.catalog import CATALOG_MARKDOWN_FILENAME
from ootp_ai.contracts.loader import Contracts, FieldEntry, Table
from ootp_ai.contracts.policy import (
    RATING_CATEGORIES,
    WITHHELD_NAME_FRAGMENTS,
    Disposition,
    column_disposition,
    disposition,
)
from ootp_ai.reports.__main__ import ROSTER_FILENAME

__all__ = [
    "RATING_NAME_PATTERN",
    "SUMMARY_BUDGET",
    "ColumnNote",
    "FieldNote",
    "ReportPointer",
    "Structure",
    "TableEntry",
    "WithheldGroup",
    "build_structure",
    "has_withheld_fragment",
    "is_rating",
    "summarise_reason",
]

#: How many characters of a declared reason the catalog will reproduce. Whole sentences
#: only, so the cut never lands mid-clause. Generous enough that today's two groups keep
#: their real argument and small enough that the catalog stays a catalog.
SUMMARY_BUDGET: Final = 400

#: The env key every rendered artifact resolves under. Named rather than valued: the value
#: is a machine path, and this file is tracked in a public repo (ADR 0006, finding F19).
OUTPUT_ROOT_KEY: Final = "OOTP_OUTPUT_ROOT"

#: `<save_id>/<sim_date>/<ingest_seq>/` — the partitioning `reports/resolve.py` produces,
#: written as a shape rather than as a resolved path for the same reason.
SNAPSHOT_PARTITION: Final = "<save_id>/<sim_date>/<ingest_seq>"

_SENTENCE_SPLIT: Final = re.compile(r"(?<=\.)\s+")
_ADR_MENTION: Final = re.compile(r"\bADR (\d{4})\b")

#: A rating **identifier**, as opposed to the English word. The catalog's second line of
#: defence, and it exists because the first one could not fail.
#:
#: `WITHHELD_NAME_FRAGMENTS` is three substrings, and `contracts/policy.py` is explicit
#: that it is *"the **secondary** check … the category is the gate"*. For a landed column
#: there is a category to gate on; for prose there is not, so the fragment list was the
#: only check — and the guard asserting the catalog is clean used the same three
#: substrings the redactor removes, which is a test that cannot fail. Proven by injection
#: at the Phase 11 panel: a `FieldEntry(name="batting_ratings_contact", category=
#: "rating-true")` rendered its name onto the page with the guard green.
#:
#: Widening the fragment list was the wrong fix — adding `rating` would redact the English
#: word and gut the `ratings` group's own reason. This matches the shape a decoded rating
#: column actually has and nothing else: verified against the shipped catalog, where
#: `rating-true`, `ratings` and *"a stored rating"* all fail to match because none is an
#: identifier.
RATING_NAME_PATTERN: Final = re.compile(r"\b\w*_ratings?_\w+\b|\b\w+_rating\b")


@dataclass(frozen=True, slots=True)
class ColumnNote:
    """A declared column the serving gate does not release on the ordinary route."""

    column: str
    disposition: str
    category: str
    epistemic: str

    @property
    def reason(self) -> str:
        """Why the gate decided that, generated from the label rather than written."""
        if self.category == "rating-true":
            return (
                f"category `{self.category}`, label `{self.epistemic}` — an unclassified "
                "field is recorded as a true rating (ADR 0012's corollary), and a true "
                "rating never reaches a page"
            )
        return (
            f"category `{self.category}`, label `{self.epistemic}` — the value is landed "
            "and its meaning is not established, so it renders only with an uncertainty "
            "banner and never as a bare value"
        )


@dataclass(frozen=True, slots=True)
class FieldNote:
    """A declared field the gate withholds, named so the gap is visible."""

    name: str
    source: str
    disposition: str
    category: str
    epistemic: str


@dataclass(frozen=True, slots=True)
class TableEntry:
    """One declared table as the catalog describes it, with no volume attached."""

    name: str
    grain: str
    key: tuple[str, ...]
    source: tuple[str, ...]
    walker: str
    coverage: str
    note: str | None
    column_count: int
    provenance_columns: int
    served_columns: int
    withheld_columns: tuple[ColumnNote, ...]
    label_counts: tuple[tuple[str, int], ...]

    @property
    def weakest_label(self) -> str | None:
        """The least-confident epistemic label any column of this table carries.

        The single most useful thing a GM can know about a table it is about to act on:
        an aggregate over columns that are individually `verified` is `verified`, and one
        containing a single `unconfirmed` column is not, however many verified siblings
        it has.
        """
        order = ("unconfirmed", "assumed", "inferred", "measured", "verified")
        present = {label for label, _ in self.label_counts}
        for label in order:
            if label in present:
                return label
        return None


@dataclass(frozen=True, slots=True)
class WithheldGroup:
    """A group of fields deliberately not landed, and as much of the argument as is safe."""

    name: str
    source: str
    summary: str
    truncated: bool
    adrs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportPointer:
    """Where a rendered report lands, as a shape rather than as a resolved path.

    Scope Core §15 (SD-11). Without this the USER-RUN acceptance criterion 20 — spawn the
    GM with the reports in its context — is unreproducible by anyone who was not in the
    room, because nothing tracked says where the reports are or what the umpire says when
    handing them over.
    """

    logical_name: str
    filename: str
    env_key: str
    partition: str
    command: str

    @property
    def relative_path(self) -> str:
        return f"{self.partition}/{self.filename}"


@dataclass(frozen=True, slots=True)
class Structure:
    """The whole volume-free catalog.

    **A declared field is in exactly one of three states, and the first version of this
    model knew only two.** It counted `served` as *every* field the policy would render,
    whether or not any table actually had a column for it — so the page announced *"78 of
    89 declared fields reach a page"* when the true figure was 55, and its next clause,
    *"the rest are named under What is withheld"*, was false for the 23 it had
    miscounted. On the one artifact whose stated purpose is telling the GM what it is not
    seeing, the error ran toward understating the gap.

    So the three states are now explicit and the counts are derived from membership rather
    than from disposition alone:

    * **served** — bound to a declared column *and* renderable;
    * **withheld** — bound or not, but the policy will not release it;
    * **unexposed** — renderable, and bound to no column. The walker reads it and nothing
      lands it. `tables.toml`'s own coverage note calls these *"entries the walker
      verified and chose not to surface, because every exposed field is a field a report
      may print and none of the six has a consumer"* — which is a gap worth pricing, not
      a rounding error.
    """

    tables: tuple[TableEntry, ...]
    withheld_groups: tuple[WithheldGroup, ...]
    withheld_fields: tuple[FieldNote, ...]
    withheld_rating_counts: tuple[tuple[str, int], ...]
    unexposed_fields: tuple[FieldNote, ...]
    reports: tuple[ReportPointer, ...]
    field_count: int
    bound_field_count: int
    served_field_count: int

    @property
    def withheld_field_count(self) -> int:
        """Every field the policy will not release, named or counted."""
        return len(self.withheld_fields) + sum(count for _, count in self.withheld_rating_counts)


def is_rating(entry: FieldEntry) -> bool:
    """Whether the declaration classifies `entry` as a rating of either kind.

    **The structural rule the catalog's rating clause now rests on.** A category is a
    decision somebody recorded in `field_map.toml`; a regex is a guess about spelling. So
    the page never prints the name of a rating-category field, whatever it happens to be
    called, and `RATING_NAME_PATTERN` is the backstop for prose — where there is no
    category to consult — rather than the rule itself.
    """
    return entry.category in RATING_CATEGORIES


def has_withheld_fragment(text: str) -> bool:
    """Whether `text` carries a name the serving policy treats as withheld on sight.

    Two predicates, and the second is why this is not circular. The fragment list is the
    one `contracts/policy.py` gates columns with — reused rather than copied, so a
    fragment added there because a rating slipped past starts redacting the catalog in the
    same commit. `RATING_NAME_PATTERN` covers the shape that list cannot: a decoded rating
    column nobody has thought to add a fragment for.
    """
    lowered = text.lower()
    if any(fragment in lowered for fragment in WITHHELD_NAME_FRAGMENTS):
        return True
    return RATING_NAME_PATTERN.search(lowered) is not None


def summarise_reason(reason: str, *, budget: int = SUMMARY_BUDGET) -> tuple[str, bool]:
    """As much of a declared reason as the catalog can safely reproduce.

    Returns the summary and whether anything was left behind, so the page can say so
    rather than presenting a truncation as the whole argument.
    """
    paragraph = reason.split("\n\n", 1)[0].strip()
    sentences = [part.strip() for part in _SENTENCE_SPLIT.split(paragraph) if part.strip()]

    kept: list[str] = []
    for sentence in sentences:
        if has_withheld_fragment(sentence):
            break
        candidate = " ".join([*kept, sentence])
        if kept and len(candidate) > budget:
            break
        kept.append(sentence)

    if not kept:
        # The first sentence itself names a withheld column. Nothing to quote, and saying
        # so beats an empty cell that reads as "no reason was given".
        return ("The declared reason names withheld columns and is not reproduced here.", True)
    return (" ".join(kept), len(kept) < len(sentences) or paragraph != reason.strip())


def build_structure(contracts: Contracts) -> Structure:
    """The volume-free catalog model, sorted into a deterministic order."""
    tables = tuple(
        _table_entry(contracts, table) for table in sorted(contracts.tables, key=lambda t: t.name)
    )

    groups = tuple(
        _withheld_group(name=entry.name, source=entry.source, reason=entry.reason)
        for entry in sorted(contracts.withheld, key=lambda entry: entry.name)
    )

    # Membership, not disposition. A field the policy would happily render is still not on
    # any page if no declared column claims it, and conflating the two is what made the
    # headline count wrong by 23.
    bound = {
        column.field
        for table in contracts.tables
        for column in table.columns
        if column.field is not None
    }

    ordered = sorted(contracts.fields, key=lambda entry: entry.name)
    withheld = [entry for entry in ordered if disposition(entry) is not Disposition.RENDERABLE]
    unexposed = [
        entry
        for entry in ordered
        if disposition(entry) is Disposition.RENDERABLE and entry.name not in bound
    ]

    # A rating-category field is COUNTED, never named — the structural half of AC15's
    # no-rating-name clause. Naming one is what withholding it currently causes, which is
    # backwards: the shipped entries are harmless placeholders, and the first genuinely
    # decoded true rating would be published into a public tracked file by the same code
    # path that exists to keep it off a page.
    rating_sources: Counter[str] = Counter(entry.source for entry in withheld if is_rating(entry))

    return Structure(
        tables=tables,
        withheld_groups=groups,
        withheld_fields=tuple(_note(entry) for entry in withheld if not is_rating(entry)),
        withheld_rating_counts=tuple(sorted(rating_sources.items())),
        unexposed_fields=tuple(
            _note(entry, "unexposed") for entry in unexposed if not is_rating(entry)
        ),
        reports=_report_pointers(),
        field_count=len(contracts.fields),
        bound_field_count=len(bound),
        served_field_count=sum(
            1
            for entry in contracts.fields
            if entry.name in bound and disposition(entry) is Disposition.RENDERABLE
        ),
    )


def _note(entry: FieldEntry, decided: str | None = None) -> FieldNote:
    return FieldNote(
        name=entry.name,
        source=entry.source,
        disposition=disposition(entry).value if decided is None else decided,
        category=entry.category,
        epistemic=entry.epistemic,
    )


def _table_entry(contracts: Contracts, table: Table) -> TableEntry:
    withheld: list[ColumnNote] = []
    labels: Counter[str] = Counter()
    provenance = 0

    for column in table.columns:
        if column.provenance:
            provenance += 1
            continue
        entry = contracts.field(_field_of(column.field, table.name, column.name))
        labels[entry.epistemic] += 1
        decided = column_disposition(contracts, table, column)
        if decided is not Disposition.RENDERABLE:
            withheld.append(
                ColumnNote(
                    column=column.name,
                    disposition=decided.value,
                    category=entry.category,
                    epistemic=entry.epistemic,
                )
            )

    return TableEntry(
        name=table.name,
        grain=table.grain,
        key=table.key,
        source=table.source,
        walker=table.walker,
        coverage=table.coverage,
        note=table.note,
        column_count=len(table.columns),
        provenance_columns=provenance,
        served_columns=len(table.columns) - len(withheld),
        withheld_columns=tuple(sorted(withheld, key=lambda note: note.column)),
        # Sorted by label name, not by count: a tie in counts would otherwise order by
        # whatever `Counter` saw first, which is declaration order wearing a disguise.
        label_counts=tuple(sorted(labels.items())),
    )


def _field_of(field: str | None, table_name: str, column_name: str) -> str:
    if field is None:  # pragma: no cover - the loader refuses such a column
        raise ValueError(
            f"{table_name}.{column_name} is neither provenance nor tied to a field; "
            "contracts/loader.py refuses that shape, so reaching here means the "
            "declaration was parsed by something else"
        )
    return field


def _withheld_group(*, name: str, source: str, reason: str) -> WithheldGroup:
    summary, truncated = summarise_reason(reason)
    return WithheldGroup(
        name=name,
        source=source,
        summary=summary,
        truncated=truncated,
        # Scanned over the WHOLE reason, not the summary: the governing ADR is often cited
        # in a later sentence, and a group losing its ADR because the quote was trimmed
        # would drop exactly the pointer the plan asks each entry to carry.
        adrs=tuple(sorted(set(_ADR_MENTION.findall(reason)))),
    )


def _report_pointers() -> tuple[ReportPointer, ...]:
    """The rendered reports, named from the modules that write them.

    Imported rather than repeated: renaming `roster.md` changes this pointer in the same
    commit, and `tests/test_catalog.py` asserts the pointer names a file the renderer
    actually writes. A hand-kept path here would be right on the day it was written and
    silently wrong afterwards.
    """
    return (
        ReportPointer(
            logical_name="organisation roster",
            filename=ROSTER_FILENAME,
            env_key=OUTPUT_ROOT_KEY,
            partition=SNAPSHOT_PARTITION,
            command="uv run python -m ootp_ai.reports render",
        ),
        ReportPointer(
            logical_name="warehouse catalog",
            filename=CATALOG_MARKDOWN_FILENAME,
            env_key=OUTPUT_ROOT_KEY,
            partition=SNAPSHOT_PARTITION,
            command="uv run python -m ootp_ai.catalog",
        ),
    )
