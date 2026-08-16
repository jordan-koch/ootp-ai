"""MySQL connection factories, deliberately asymmetric.

`ootp` / `ootp_dev` is the warehouse the parser writes. `ootp_truth_real` is the
one-time export from the retained standard-mode save — the only artifact that can
prove the parser correct row-for-row, because Challenge Mode has no export
(ADR 0003). Rebuilding it costs a save rebuild plus an export run, so it is opened
with `SET SESSION TRANSACTION READ ONLY` and the setting is *read back and
asserted*: a comment saying "don't write here" is not a control.

Nothing in this module opens a game file. The game is read-only at a different
layer entirely (ADR 0001); this is about not corrupting the answer key.
"""

from __future__ import annotations

from typing import Final

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from ootp_ai.config import ConfigError, Settings

__all__ = [
    "ReadOnlySessionError",
    "connect_truth",
    "connect_warehouse",
]

# SESSION scope, not the bare `SET TRANSACTION READ ONLY`, which would apply to the
# next transaction only and silently expire after one statement.
_READ_ONLY_STATEMENT: Final = "SET SESSION TRANSACTION READ ONLY"
_READ_ONLY_PROBE: Final = "SELECT @@session.transaction_read_only AS read_only"


class ReadOnlySessionError(RuntimeError):
    """A connection that must be read-only came back writable."""


def connect_warehouse(settings: Settings) -> Connection[DictCursor]:
    """Open the writable warehouse schema. The caller owns the transaction."""
    return _connect(settings, settings.mysql.database, read_only=False)


def connect_truth(settings: Settings) -> Connection[DictCursor]:
    """Open the ground-truth export schema with writes refused by the server."""
    database = settings.mysql.truth_database
    if database is None:
        raise ConfigError(
            "MYSQL_TRUTH_REAL_DATABASE is unset, so the ground-truth schema cannot be opened"
        )
    return _connect(settings, database, read_only=True)


def _connect(settings: Settings, database: str, *, read_only: bool) -> Connection[DictCursor]:
    connection: Connection[DictCursor] = pymysql.connect(
        host=settings.mysql.host,
        port=settings.mysql.port,
        user=settings.mysql.user,
        password=settings.mysql.password,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        # A read-only session has nothing to commit; the loader manages its own.
        autocommit=read_only,
        init_command=_READ_ONLY_STATEMENT if read_only else None,
    )
    if read_only:
        _assert_read_only(connection, database)
    return connection


def _assert_read_only(connection: Connection[DictCursor], database: str) -> None:
    """Read the setting back. An init_command that silently failed looks identical."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(_READ_ONLY_PROBE)
            row = cursor.fetchone()
    except Exception:
        connection.close()
        raise

    if row is None or int(row["read_only"]) != 1:
        connection.close()
        raise ReadOnlySessionError(
            f"session on {database} is not read-only; refusing to hand out the connection"
        )
