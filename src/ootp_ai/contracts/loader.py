"""Read the tracked declarations, and refuse one that does not hold together.

**This module validates; it does not merely parse.** That distinction is the reason it
exists. Before it, `field_map.toml` was the largest tracked contract in the project and
had *no* programmatic consumer: nothing checked a `category` against a vocabulary, and
nothing cross-checked an `epistemic` label against the validator that earned it. A typo,
or a `verified` pasted from the row above, shipped green — in a file whose labels carry
ADR 0012's withhold rule and decide what a report is allowed to print.

So every value that means something is checked against a vocabulary **declared in the
same file**, and an unknown one raises naming the field *and* the offending value.

## The grain check, which is the one worth understanding

`.claude/agents/data-engineer.md` requires a dataset to state its grain in prose *and*
enforce it with a uniqueness test, "and the two must agree". Agreement by inspection
decays. So `tables.toml` states the grain as a sentence of the form
``one row per A per B per C``, this module splits it, resolves each dimension through the
declared `[meta.dimensions]` map, and requires the union of those columns to equal the
declared key **exactly**.

A key that drifts from its sentence therefore fails to *load* — in the DDL emitter, in
the tests, and in the catalog generator alike — rather than failing to be noticed. The
failure it is aimed at is concrete: keying `bronze_team_roster` on
``(sim_date, player_id)`` collapses the 935 players who hold rows at two clubs in one
snapshot, and the roster report loses them with nothing raised.

## No cache, deliberately

Both files are small and parsing them costs a millisecond. A module-level cache would buy
nothing and would make a mutated declaration in one test leak into the next — the same
reasoning `parser/names.py` applies to its name table, for the same reason: the failure a
stale cache produces is silent.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from typing import Any, Final

__all__ = [
    "CONTRACTS_PACKAGE",
    "FIELD_MAP_FILE",
    "GRAIN_PREFIX",
    "TABLES_FILE",
    "Column",
    "ContractError",
    "Contracts",
    "FieldEntry",
    "Table",
    "WithheldEntry",
    "load_contracts",
    "parse_contracts",
    "read_declaration_text",
]

CONTRACTS_PACKAGE: Final = "ootp_ai.contracts"
FIELD_MAP_FILE: Final = "field_map.toml"
TABLES_FILE: Final = "tables.toml"

#: Every grain sentence opens with this, and what follows is the dimension list.
GRAIN_PREFIX: Final = "one row per "
_GRAIN_SEPARATOR: Final = " per "

_FIELD_REQUIRED: Final = (
    "name",
    "source",
    "walker",
    "type",
    "category",
    "epistemic",
    "validator",
)
_FIELD_OPTIONAL: Final = ("note",)
_WITHHELD_REQUIRED: Final = ("name", "source", "reason")
_TABLE_REQUIRED: Final = (
    "name",
    "grain",
    "key",
    "source",
    "walker",
    "collation",
    "coverage",
)
_TABLE_OPTIONAL: Final = ("note", "column")
_COLUMN_REQUIRED: Final = ("name", "type", "null")
_COLUMN_OPTIONAL: Final = ("length", "field", "provenance")

#: Scalar tokens whose signedness a column and its field entry must agree about. A field
#: entry's `type` is prose — "u32 in the drop-zero pre-colour run" — so only its leading
#: token is read, and only when both sides name one of these.
_SIGNED_SCALARS: Final = frozenset({"i32", "i16", "i8"})
_UNSIGNED_SCALARS: Final = frozenset({"u8", "u16", "u32"})

#: `text` is the only type carrying a width, and it must carry one: a VARCHAR whose
#: length nobody declared is a length somebody guessed.
_SIZED_TYPE: Final = "text"
_MAX_TEXT_LENGTH: Final = 1024


class ContractError(ValueError):
    """A declaration is malformed, or does not agree with itself."""


@dataclass(frozen=True, slots=True)
class FieldEntry:
    """One row of `field_map.toml` — what a landed field is and how well we know it."""

    name: str
    source: str
    walker: str
    save_type: str
    category: str
    epistemic: str
    validator: str
    note: str | None = None


@dataclass(frozen=True, slots=True)
class WithheldEntry:
    """A field deliberately not landed, and the argument for its absence."""

    name: str
    source: str
    reason: str


@dataclass(frozen=True, slots=True)
class Column:
    """One column of a declared table.

    `field` names the `field_map.toml` entry this column's values come from. A column that
    holds no save data instead declares `provenance = true` — `save_id`, `sim_date`,
    `ingest_seq`, and the label columns of `bronze_field_label`, none of which a walker
    produced.

    **Exactly one of the two, and the loader enforces it.** Letting a column carry neither
    made "no field" mean both "ours" and "nobody said", and the serving gate read that as
    renderable: measured, a `batting_ratings_talent_contact` column with its `field` line
    omitted loaded clean and rendered. Provenance is now an act rather than an absence.
    """

    name: str
    column_type: str
    nullable: bool
    length: int | None = None
    field: str | None = None
    provenance: bool = False


@dataclass(frozen=True, slots=True)
class Table:
    """One declared table: its grain in prose, its key, and the columns to emit."""

    name: str
    grain: str
    key: tuple[str, ...]
    columns: tuple[Column, ...]
    source: tuple[str, ...]
    walker: str
    collation: str
    coverage: str
    note: str | None = None

    def column(self, name: str) -> Column:
        for column in self.columns:
            if column.name == name:
                return column
        raise ContractError(f"table {self.name!r} declares no column {name!r}")

    @property
    def key_columns(self) -> tuple[Column, ...]:
        return tuple(self.column(name) for name in self.key)

    @property
    def grain_dimensions(self) -> tuple[str, ...]:
        return _split_grain(self.grain, self.name)


@dataclass(frozen=True, slots=True)
class Contracts:
    """Both declarations, parsed and checked against each other."""

    tables: tuple[Table, ...]
    fields: tuple[FieldEntry, ...]
    withheld: tuple[WithheldEntry, ...]
    dimensions: Mapping[str, tuple[str, ...]]
    column_types: tuple[str, ...]
    categories: tuple[str, ...]
    epistemics: tuple[str, ...]

    def table(self, name: str) -> Table:
        for table in self.tables:
            if table.name == name:
                return table
        raise ContractError(f"no table named {name!r} is declared")

    def field(self, name: str) -> FieldEntry:
        for entry in self.fields:
            if entry.name == name:
                return entry
        raise ContractError(f"no field named {name!r} is declared")


def read_declaration_text(filename: str) -> str:
    """Return a tracked declaration's text, resolved as package data.

    Resolved through `importlib.resources` and never through a path walk: the rule at
    `.claude/agents/data-engineer.md` is that nothing outside a test module reaches for
    the repo root, and a `parents[N]` walk breaks the moment the package is installed
    rather than run from a checkout.
    """
    return (resources.files(CONTRACTS_PACKAGE) / filename).read_text(encoding="utf-8")


def load_contracts() -> Contracts:
    """Parse and validate both tracked declarations."""
    return parse_contracts(
        field_map_text=read_declaration_text(FIELD_MAP_FILE),
        tables_text=read_declaration_text(TABLES_FILE),
    )


def parse_contracts(*, field_map_text: str, tables_text: str) -> Contracts:
    """Parse and validate declarations given as text.

    The seam the tests mutate. A guard that can only be exercised against the real file
    can only be proven by breaking the repo, so every refusal below is reachable from a
    string.
    """
    field_map = _load_toml(field_map_text, FIELD_MAP_FILE)
    tables_doc = _load_toml(tables_text, TABLES_FILE)

    categories, epistemics, validators = _field_vocabulary(field_map)
    fields = _parse_fields(field_map, categories, epistemics, validators)
    withheld = _parse_withheld(field_map)

    column_types, collations = _table_vocabulary(tables_doc)
    dimensions = _parse_dimensions(tables_doc)
    tables = _parse_tables(tables_doc, column_types, collations)

    _check_grain_matches_key(tables, dimensions)
    _check_columns_resolve_to_fields(tables, fields)
    _check_declared_table_count(tables_doc, tables)

    return Contracts(
        tables=tables,
        fields=fields,
        withheld=withheld,
        dimensions=dimensions,
        column_types=column_types,
        categories=categories,
        epistemics=epistemics,
    )


# ── parsing ──────────────────────────────────────────────────────────────────


def _load_toml(text: str, where: str) -> dict[str, Any]:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ContractError(f"{where} is not valid TOML: {error}") from error


def _field_vocabulary(
    document: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    vocabulary = document.get("vocabulary")
    if not isinstance(vocabulary, Mapping):
        raise ContractError(
            f"{FIELD_MAP_FILE} declares no [vocabulary] table, so no label can be checked "
            "against anything — which is the state this loader exists to end"
        )
    return (
        _string_tuple(vocabulary, "category", f"{FIELD_MAP_FILE} [vocabulary]"),
        _string_tuple(vocabulary, "epistemic", f"{FIELD_MAP_FILE} [vocabulary]"),
        _string_tuple(vocabulary, "validator", f"{FIELD_MAP_FILE} [vocabulary]"),
    )


def _parse_fields(
    document: Mapping[str, Any],
    categories: Sequence[str],
    epistemics: Sequence[str],
    validators: Sequence[str],
) -> tuple[FieldEntry, ...]:
    entries: list[FieldEntry] = []
    seen: set[str] = set()
    for raw in _entry_list(document, "field", FIELD_MAP_FILE):
        name = _require_str(raw, "name", f"{FIELD_MAP_FILE} [[field]]")
        where = f"{FIELD_MAP_FILE} field {name!r}"
        _check_keys(raw, _FIELD_REQUIRED, _FIELD_OPTIONAL, where)
        if name in seen:
            raise ContractError(
                f"{FIELD_MAP_FILE} declares two fields named {name!r}. Names are the key "
                "columns resolve through, so a duplicate silently points a column at "
                "whichever entry parsed last"
            )
        seen.add(name)

        category = _require_str(raw, "category", where)
        epistemic = _require_str(raw, "epistemic", where)
        validator = _require_str(raw, "validator", where)
        _check_vocabulary(category, categories, "category", where)
        _check_vocabulary(epistemic, epistemics, "epistemic", where)
        _check_vocabulary(validator, validators, "validator", where)

        entries.append(
            FieldEntry(
                name=name,
                source=_require_str(raw, "source", where),
                walker=_require_str(raw, "walker", where),
                save_type=_require_str(raw, "type", where),
                category=category,
                epistemic=epistemic,
                validator=validator,
                note=_optional_str(raw, "note", where),
            )
        )
    if not entries:
        raise ContractError(f"{FIELD_MAP_FILE} declares no fields at all")
    return tuple(entries)


def _parse_withheld(document: Mapping[str, Any]) -> tuple[WithheldEntry, ...]:
    entries: list[WithheldEntry] = []
    for raw in document.get("withheld", []) or []:
        if not isinstance(raw, Mapping):
            raise ContractError(f"{FIELD_MAP_FILE} [[withheld]] is not a table")
        name = _require_str(raw, "name", f"{FIELD_MAP_FILE} [[withheld]]")
        where = f"{FIELD_MAP_FILE} withheld {name!r}"
        _check_keys(raw, _WITHHELD_REQUIRED, (), where)
        entries.append(
            WithheldEntry(
                name=name,
                source=_require_str(raw, "source", where),
                reason=_require_str(raw, "reason", where),
            )
        )
    return tuple(entries)


def _table_vocabulary(document: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    vocabulary = document.get("vocabulary")
    if not isinstance(vocabulary, Mapping):
        raise ContractError(f"{TABLES_FILE} declares no [vocabulary] table")
    return (
        _string_tuple(vocabulary, "type", f"{TABLES_FILE} [vocabulary]"),
        _string_tuple(vocabulary, "collation", f"{TABLES_FILE} [vocabulary]"),
    )


def _parse_dimensions(document: Mapping[str, Any]) -> Mapping[str, tuple[str, ...]]:
    meta = document.get("meta")
    if not isinstance(meta, Mapping):
        raise ContractError(f"{TABLES_FILE} declares no [meta] table")
    declared = meta.get("dimensions")
    if not isinstance(declared, Mapping) or not declared:
        raise ContractError(
            f"{TABLES_FILE} declares no [meta.dimensions] map, so a grain sentence "
            "cannot be resolved to columns and the prose could say anything"
        )
    dimensions: dict[str, tuple[str, ...]] = {}
    for token, columns in declared.items():
        dimensions[str(token)] = _string_sequence(
            columns, f"{TABLES_FILE} [meta.dimensions] {token!r}"
        )
    return dimensions


def _parse_tables(
    document: Mapping[str, Any],
    column_types: Sequence[str],
    collations: Sequence[str],
) -> tuple[Table, ...]:
    tables: list[Table] = []
    seen: set[str] = set()
    for raw in _entry_list(document, "table", TABLES_FILE):
        name = _require_str(raw, "name", f"{TABLES_FILE} [[table]]")
        where = f"{TABLES_FILE} table {name!r}"
        _check_keys(raw, _TABLE_REQUIRED, _TABLE_OPTIONAL, where)
        if name in seen:
            raise ContractError(f"{TABLES_FILE} declares two tables named {name!r}")
        seen.add(name)

        collation = _require_str(raw, "collation", where)
        _check_vocabulary(collation, collations, "collation", where)

        columns = _parse_columns(raw, column_types, where)
        key = _string_tuple(raw, "key", where)
        _check_key(key, columns, where)

        tables.append(
            Table(
                name=name,
                grain=_require_str(raw, "grain", where),
                key=key,
                columns=columns,
                source=_string_tuple(raw, "source", where),
                walker=_require_str(raw, "walker", where),
                collation=collation,
                coverage=_require_str(raw, "coverage", where),
                note=_optional_str(raw, "note", where),
            )
        )
    if not tables:
        raise ContractError(f"{TABLES_FILE} declares no tables at all")
    return tuple(tables)


def _parse_columns(
    raw: Mapping[str, Any], column_types: Sequence[str], where: str
) -> tuple[Column, ...]:
    columns: list[Column] = []
    seen: set[str] = set()
    for entry in _entry_list(raw, "column", where):
        name = _require_str(entry, "name", f"{where} [[table.column]]")
        column_where = f"{where} column {name!r}"
        _check_keys(entry, _COLUMN_REQUIRED, _COLUMN_OPTIONAL, column_where)
        if name in seen:
            raise ContractError(f"{where} declares two columns named {name!r}")
        seen.add(name)

        column_type = _require_str(entry, "type", column_where)
        _check_vocabulary(column_type, column_types, "type", column_where)
        length = _optional_int(entry, "length", column_where)
        _check_length(column_type, length, column_where)

        field = _optional_str(entry, "field", column_where)
        provenance = "provenance" in entry and _require_bool(entry, "provenance", column_where)
        _check_provenance(field=field, provenance=provenance, where=column_where)

        columns.append(
            Column(
                name=name,
                column_type=column_type,
                nullable=_require_bool(entry, "null", column_where),
                length=length,
                field=field,
                provenance=provenance,
            )
        )
    if not columns:
        raise ContractError(f"{where} declares no columns")
    return tuple(columns)


# ── the checks that make the declaration hold together ───────────────────────


def _check_key(key: Sequence[str], columns: Sequence[Column], where: str) -> None:
    if not key:
        raise ContractError(f"{where} declares an empty key")
    by_name = {column.name: column for column in columns}
    for name in key:
        column = by_name.get(name)
        if column is None:
            raise ContractError(f"{where} keys on {name!r}, which it does not declare as a column")
        if column.nullable:
            # MySQL's COUNT(DISTINCT a, b, c) silently drops tuples containing NULL, so a
            # nullable key column makes the grain test under-count and pass vacuously.
            raise ContractError(
                f"{where} keys on {name!r}, which is declared nullable. Every primary-key "
                "column is NOT NULL or the uniqueness test it backs passes on fewer rows "
                "than the table holds"
            )
    if len(set(key)) != len(key):
        raise ContractError(f"{where} names a column twice in its key: {list(key)}")


def _check_grain_matches_key(
    tables: Sequence[Table], dimensions: Mapping[str, tuple[str, ...]]
) -> None:
    for table in tables:
        where = f"{TABLES_FILE} table {table.name!r}"
        tokens = _split_grain(table.grain, table.name)
        implied: set[str] = set()
        for token in tokens:
            columns = dimensions.get(token)
            if columns is None:
                raise ContractError(
                    f"{where} states its grain per {token!r}, which [meta.dimensions] does "
                    f"not declare. Known dimensions: {sorted(dimensions)}"
                )
            implied.update(columns)
        if implied != set(table.key):
            missing = sorted(implied - set(table.key))
            extra = sorted(set(table.key) - implied)
            raise ContractError(
                f"{where} says {table.grain!r}, which implies the key "
                f"{sorted(implied)}, but declares {list(table.key)}. "
                f"Missing from the key: {missing}. Not implied by the prose: {extra}. "
                "The prose and the key are one statement, and this is the drift the "
                "declaration exists to prevent"
            )


def _check_provenance(*, field: str | None, provenance: bool, where: str) -> None:
    if field is None and not provenance:
        raise ContractError(
            f"{where} names no field and is not declared `provenance = true`. Every column "
            "either carries save data — and then it has an epistemic label the serving gate "
            "reads — or it is ours, and says so. A column silent about which reads as ours "
            "by default, which is how a rating reaches a page"
        )
    if field is not None and provenance:
        raise ContractError(
            f"{where} is declared `provenance = true` and also claims field {field!r}. "
            "Provenance means no walker produced it; the two cannot both be true"
        )


def _check_columns_resolve_to_fields(tables: Sequence[Table], fields: Sequence[FieldEntry]) -> None:
    known = {entry.name: entry for entry in fields}
    for table in tables:
        for column in table.columns:
            if column.field is None:
                continue
            entry = known.get(column.field)
            if entry is None:
                raise ContractError(
                    f"{TABLES_FILE} table {table.name!r} column {column.name!r} claims field "
                    f"{column.field!r}, which {FIELD_MAP_FILE} does not declare. A column "
                    "whose provenance names nothing has no epistemic label, and "
                    "bronze_field_label would land a NULL where a belief belongs"
                )
            _check_signedness(table=table, column=column, entry=entry)


def _check_signedness(*, table: Table, column: Column, entry: FieldEntry) -> None:
    """Refuse a column whose signedness contradicts the walker that fills it.

    The failure lands wrong data rather than raising: six `bronze_player` columns were
    declared `u32` against fields the walker reads with `cursor.i32()` **on purpose**,
    because the export writes `league_id` negative on 176 real records and an unsigned read
    turns -1 into 4,294,967,295 — which looks like an id. Landing -203 into `INT UNSIGNED`
    either aborts the batch under strict mode or clamps to 0, and 0 is what the walker
    defines as "this player has no team". Neither is distinguishable from a correct parse.
    """
    declared = entry.save_type.split()[0].strip(",").lower()
    if declared in _SIGNED_SCALARS and column.column_type in _UNSIGNED_SCALARS:
        raise ContractError(
            f"{TABLES_FILE} table {table.name!r} column {column.name!r} is declared "
            f"{column.column_type!r} while field {entry.name!r} reads {declared!r}. The "
            "walker signs that read deliberately; an unsigned column turns a negative id "
            "into a very large positive one, or clamps it to the value that means 'none'"
        )
    if declared in _UNSIGNED_SCALARS and column.column_type in _SIGNED_SCALARS:
        raise ContractError(
            f"{TABLES_FILE} table {table.name!r} column {column.name!r} is declared "
            f"{column.column_type!r} while field {entry.name!r} reads {declared!r}"
        )


def _check_declared_table_count(document: Mapping[str, Any], tables: Sequence[Table]) -> None:
    meta = document.get("meta")
    if not isinstance(meta, Mapping):  # pragma: no cover — _parse_dimensions raises first
        return
    declared = meta.get("tables_declared")
    if declared is None:
        return
    if not isinstance(declared, int) or isinstance(declared, bool):
        raise ContractError(f"{TABLES_FILE} [meta].tables_declared is not an integer")
    if declared != len(tables):
        raise ContractError(
            f"{TABLES_FILE} [meta].tables_declared says {declared} but {len(tables)} tables "
            "are declared. The count is the phase's acceptance criterion; a table added "
            "without it is a table nobody sequenced"
        )


def _split_grain(grain: str, table_name: str) -> tuple[str, ...]:
    if not grain.startswith(GRAIN_PREFIX):
        raise ContractError(
            f"{TABLES_FILE} table {table_name!r} states its grain as {grain!r}, which does "
            f"not begin {GRAIN_PREFIX!r}. The sentence is parsed, not decorative"
        )
    body = grain[len(GRAIN_PREFIX) :].strip()
    if not body:
        raise ContractError(f"{TABLES_FILE} table {table_name!r} names no grain dimensions")
    return tuple(token.strip() for token in body.split(_GRAIN_SEPARATOR))


# ── typed extraction, so a malformed declaration fails here and not downstream ─


def _entry_list(document: Mapping[str, Any], key: str, where: str) -> tuple[Mapping[str, Any], ...]:
    raw = document.get(key, [])
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        raise ContractError(f"{where}: [[{key}]] is not an array of tables")
    entries: list[Mapping[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise ContractError(f"{where}: an entry of [[{key}]] is not a table")
        entries.append(entry)
    return tuple(entries)


def _check_keys(
    raw: Mapping[str, Any],
    required: Sequence[str],
    optional: Sequence[str],
    where: str,
) -> None:
    allowed = set(required) | set(optional)
    missing = [key for key in required if key not in raw]
    unknown = sorted(key for key in raw if key not in allowed)
    if not missing and not unknown:
        return
    # Both halves in one message, because the failure mode is usually one event seen from
    # two sides: `epistemc = "verified"` is an unknown key AND a missing one, and a
    # refusal naming only the absence sends the reader looking for a deleted line.
    faults = []
    if missing:
        faults.append(f"is missing {missing}")
    if unknown:
        faults.append(f"carries unknown keys {unknown}")
    raise ContractError(f"{where} {' and '.join(faults)}; allowed: {sorted(allowed)}")


def _check_vocabulary(value: str, allowed: Sequence[str], what: str, where: str) -> None:
    if value not in allowed:
        raise ContractError(
            f"{where} declares {what} {value!r}, which is not in the declared vocabulary "
            f"{list(allowed)}"
        )


def _check_length(column_type: str, length: int | None, where: str) -> None:
    if column_type == _SIZED_TYPE:
        if length is None:
            raise ContractError(f"{where} is {_SIZED_TYPE!r} and declares no length")
        if length < 1 or length > _MAX_TEXT_LENGTH:
            raise ContractError(f"{where} declares length {length}, outside 1..{_MAX_TEXT_LENGTH}")
    elif length is not None:
        raise ContractError(
            f"{where} is {column_type!r} and declares a length, which only {_SIZED_TYPE!r} carries"
        )


def _require_str(raw: Mapping[str, Any], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ContractError(f"{where} needs a non-empty string {key!r}, got {value!r}")
    return value


def _optional_str(raw: Mapping[str, Any], key: str, where: str) -> str | None:
    if key not in raw:
        return None
    return _require_str(raw, key, where)


def _require_bool(raw: Mapping[str, Any], key: str, where: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ContractError(f"{where} needs a boolean {key!r}, got {value!r}")
    return value


def _optional_int(raw: Mapping[str, Any], key: str, where: str) -> int | None:
    if key not in raw:
        return None
    value = raw[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractError(f"{where} needs an integer {key!r}, got {value!r}")
    return value


def _string_tuple(raw: Mapping[str, Any], key: str, where: str) -> tuple[str, ...]:
    if key not in raw:
        raise ContractError(f"{where} is missing {key!r}")
    return _string_sequence(raw[key], f"{where} {key!r}")


def _string_sequence(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ContractError(f"{where} is not a list of strings, got {value!r}")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ContractError(f"{where} holds {item!r}, which is not a non-empty string")
        out.append(item)
    return tuple(out)
