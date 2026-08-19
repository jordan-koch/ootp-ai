"""Warehouse access: identifier quoting, DDL emission, and bronze landing.

Nothing in this package writes to a game file. The ground-truth schema is opened
through an enforced read-only session; see `ootp_ai.db`.

Landing is append-only. Nothing here holds a `DELETE` or an `UPDATE` path, because the
property that makes a past decision re-examinable is that a landed snapshot stays exactly
as it landed.
"""
