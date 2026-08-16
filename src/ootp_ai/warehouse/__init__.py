"""Warehouse access: identifier quoting now, DDL emission and bronze landing later.

Nothing in this package writes to a game file. The ground-truth schema is opened
through an enforced read-only session; see `ootp_ai.db`.
"""
