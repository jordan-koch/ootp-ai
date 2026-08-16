"""Identifier quoting — the guard against a measured, silent data incident.

`select current_date from ootp_truth_real.leagues` returns the wall-clock date for
every row: MySQL parses the bare column name as the `CURRENT_DATE` function and
nothing errors. A differential harness built on that query reports the sim date as
wrong and sends the next reader hunting a parser bug that does not exist. Backticks
turn that class of collision into a plain column reference.

Identifiers are *never* parameterised by the driver — placeholders bind values, not
names — so every identifier this project puts into SQL goes through here.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = [
    "MAX_IDENTIFIER_LEN",
    "IdentifierError",
    "column_list",
    "qualified",
    "quote_ident",
]

# MySQL 8's limit for a schema, table or column name.
MAX_IDENTIFIER_LEN = 64


class IdentifierError(ValueError):
    """An identifier is empty, over-long, or carries something it must not."""


def quote_ident(name: str) -> str:
    """Return `name` as a backticked MySQL identifier, or refuse it."""
    if not name:
        raise IdentifierError("empty identifier")
    if "\x00" in name:
        raise IdentifierError(f"null byte in identifier: {name!r}")
    if "`" in name:
        # MySQL would accept a doubled backtick. Nothing here has a legitimate
        # reason to name a column that way, so an embedded backtick means a bug
        # upstream or an injection attempt — and rewriting it would hide both.
        raise IdentifierError(f"backtick in identifier: {name!r}")
    if len(name) > MAX_IDENTIFIER_LEN:
        raise IdentifierError(
            f"identifier exceeds {MAX_IDENTIFIER_LEN} characters (got {len(name)}): {name!r}"
        )
    return f"`{name}`"


def qualified(*parts: str) -> str:
    """Join and quote every part of a dotted name: `schema`.`table`."""
    if not parts:
        raise IdentifierError("qualified() needs at least one part")
    return ".".join(quote_ident(part) for part in parts)


def column_list(columns: Iterable[str]) -> str:
    """Quote each column and join them for a SELECT or an INSERT column clause."""
    quoted = [quote_ident(column) for column in columns]
    if not quoted:
        raise IdentifierError("column_list() needs at least one column")
    return ", ".join(quoted)
