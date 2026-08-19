"""Emit the schema **from** the declaration, so the DDL cannot disagree with the grain.

There is no `CREATE TABLE` written out anywhere in this repo, and that is the point. A
handwritten schema beside a declared grain is two statements of one fact, and the two
drift the first time somebody adds a column in a hurry. Here the key in the DDL *is* the
key in `tables.toml`, because it is read from it.

Nothing in this module connects to anything. It turns a `Contracts` into strings; landing
them is Phase 8b's job. That split is deliberate — every guard in Phase 8a runs in CI,
where there is no MySQL and never will be.

## Types are tokens, never SQL

`tables.toml` names a column's type from a closed vocabulary — `u32`, `bool01`, `text` —
and this module maps those to MySQL. A declaration that could name its own SQL type could
also name a subquery, and a tracked file would be interpolating into DDL. Every identifier
goes through `quote_ident()` for the same reason it always does here: a bare identifier
that collides with a MySQL function name is a measured, silent data incident in this
project's history.
"""

from __future__ import annotations

import re
from typing import Final

from ootp_ai.contracts.loader import Column, Contracts, Table
from ootp_ai.warehouse.sql import quote_ident

__all__ = [
    "TYPE_MAP",
    "DdlError",
    "create_all_statements",
    "create_table_statement",
    "mysql_type",
]

#: The whole vocabulary, and nothing outside it reaches SQL.
#:
#: `bool01` is `TINYINT UNSIGNED` and not `BOOLEAN` on purpose, mirroring
#: `parser/world.py`: every observed flag value is 0 or 1, but a boolean column makes the
#: day the game writes a 2 indistinguishable from the day it writes a 1, forever.
TYPE_MAP: Final[dict[str, str]] = {
    "u8": "TINYINT UNSIGNED",
    "u16": "SMALLINT UNSIGNED",
    "u32": "INT UNSIGNED",
    "i32": "INT",
    "bool01": "TINYINT UNSIGNED",
    "date": "DATE",
    "digest64": "CHAR(64)",
    "json": "JSON",
    "seconds": "DECIMAL(12,3)",
    "bytes": "BIGINT UNSIGNED",
    # Wall-clock, stored UTC. `DATETIME` rather than `TIMESTAMP` because MySQL's
    # TIMESTAMP converts on the way in and out using the session time zone, which would
    # make a landed row read differently depending on who queried it.
    "timestamp_utc": "DATETIME(6)",
}

_SIZED_TYPE: Final = "text"
_COLLATION_PATTERN: Final = re.compile(r"^[a-z0-9_]+$")
_ENGINE: Final = "InnoDB"
_CHARSET: Final = "utf8mb4"


class DdlError(ValueError):
    """The declaration asks for something this emitter cannot render as SQL."""


def mysql_type(column: Column) -> str:
    """Render one declared column's type as MySQL."""
    if column.column_type == _SIZED_TYPE:
        if column.length is None:  # pragma: no cover — the loader refuses this first
            raise DdlError(f"column {column.name!r} is {_SIZED_TYPE!r} with no length")
        return f"VARCHAR({column.length})"
    rendered = TYPE_MAP.get(column.column_type)
    if rendered is None:
        raise DdlError(
            f"column {column.name!r} declares type {column.column_type!r}, which this "
            f"emitter cannot render. Known: {sorted([*TYPE_MAP, _SIZED_TYPE])}"
        )
    return rendered


def create_table_statement(table: Table) -> str:
    """Emit `CREATE TABLE` with the declared key as the primary key.

    Every key column is emitted `NOT NULL`. The loader already refuses a nullable key
    column, so this is the second of two locks on the same door — MySQL's
    `COUNT(DISTINCT a, b, c)` drops tuples containing NULL, which would let a grain test
    pass on fewer rows than the table holds.
    """
    key = set(table.key)
    lines: list[str] = []
    for column in table.columns:
        nullable = column.nullable and column.name not in key
        constraint = "NULL" if nullable else "NOT NULL"
        lines.append(f"  {quote_ident(column.name)} {mysql_type(column)} {constraint}")
    lines.append(f"  PRIMARY KEY ({', '.join(quote_ident(name) for name in table.key)})")

    collation = _collation(table)
    return (
        f"CREATE TABLE {quote_ident(table.name)} (\n"
        + ",\n".join(lines)
        + f"\n) ENGINE={_ENGINE} DEFAULT CHARSET={_CHARSET} COLLATE={collation}"
    )


def create_all_statements(contracts: Contracts) -> tuple[str, ...]:
    """Emit one statement per declared table, in declaration order."""
    _check_every_declared_type_is_renderable(contracts)
    return tuple(create_table_statement(table) for table in contracts.tables)


def _collation(table: Table) -> str:
    # The vocabulary already bounds this, and this module still checks it rather than
    # trusting another file's contents on their way into a DDL string.
    if not _COLLATION_PATTERN.match(table.collation):
        raise DdlError(f"table {table.name!r} declares collation {table.collation!r}")
    return table.collation


def _check_every_declared_type_is_renderable(contracts: Contracts) -> None:
    """Refuse a vocabulary this emitter has fallen behind.

    Adding a type to `tables.toml` and forgetting it here would otherwise surface only
    when some future table happened to use it.
    """
    unknown = [
        column_type
        for column_type in contracts.column_types
        if column_type != _SIZED_TYPE and column_type not in TYPE_MAP
    ]
    if unknown:
        raise DdlError(
            f"tables.toml declares column types {unknown} that this emitter cannot "
            "render; add them to TYPE_MAP or drop them from the vocabulary"
        )
