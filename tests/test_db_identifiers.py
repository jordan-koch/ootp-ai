"""Identifier quoting — the guard against a measured, silent data incident.

`select current_date from ootp_truth_real.leagues` returns the wall-clock date for
every row, because MySQL parses the bare column name as the CURRENT_DATE function.
Nothing errors. A differential harness built on that query reports the sim date as
wrong and sends the next agent hunting a parser bug that does not exist.

Offline: no MySQL, no game.
"""

from __future__ import annotations

import pytest

from ootp_ai.warehouse.sql import (
    MAX_IDENTIFIER_LEN,
    IdentifierError,
    column_list,
    qualified,
    quote_ident,
)


def test_a_plain_identifier_is_backticked() -> None:
    assert quote_ident("team_id") == "`team_id`"


@pytest.mark.parametrize(
    "keyword",
    ["current_date", "year", "position", "level", "status", "rank", "group"],
)
def test_the_keyword_columns_that_caused_the_incident_are_quoted(keyword: str) -> None:
    """Every one of these appears in the export's own column vocabulary."""
    assert quote_ident(keyword) == f"`{keyword}`"


def test_an_embedded_backtick_is_rejected_not_escaped() -> None:
    """MySQL would accept a doubled backtick.

    Nothing here has a legitimate reason to name a column that way, so an embedded
    backtick means a bug upstream or an injection attempt — and silently rewriting
    it would hide both.
    """
    with pytest.raises(IdentifierError, match="backtick"):
        quote_ident("bad`name")


def test_an_injection_attempt_is_rejected() -> None:
    with pytest.raises(IdentifierError, match="backtick"):
        quote_ident("x` ; DROP TABLE bronze_team; --")


def test_an_empty_identifier_is_rejected() -> None:
    with pytest.raises(IdentifierError, match="empty"):
        quote_ident("")


def test_a_null_byte_is_rejected() -> None:
    with pytest.raises(IdentifierError, match="null byte"):
        quote_ident("a\x00b")


def test_an_over_long_identifier_is_rejected() -> None:
    with pytest.raises(IdentifierError, match=str(MAX_IDENTIFIER_LEN)):
        quote_ident("a" * (MAX_IDENTIFIER_LEN + 1))


def test_an_identifier_at_the_limit_is_allowed() -> None:
    name = "a" * MAX_IDENTIFIER_LEN
    assert quote_ident(name) == f"`{name}`"


def test_qualified_quotes_every_part() -> None:
    assert qualified("ootp_dev", "bronze_team") == "`ootp_dev`.`bronze_team`"


def test_qualified_rejects_a_bad_part() -> None:
    with pytest.raises(IdentifierError):
        qualified("ootp_dev", "bad`table")


def test_qualified_requires_at_least_one_part() -> None:
    with pytest.raises(IdentifierError):
        qualified()


def test_column_list_quotes_each_column() -> None:
    assert column_list(["save_id", "sim_date", "ingest_seq"]) == (
        "`save_id`, `sim_date`, `ingest_seq`"
    )


def test_column_list_requires_at_least_one_column() -> None:
    with pytest.raises(IdentifierError):
        column_list([])
