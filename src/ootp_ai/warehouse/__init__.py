"""Warehouse access: identifier quoting and DDL emission now, bronze landing later.

Nothing in this package writes to a game file. The ground-truth schema is opened
through an enforced read-only session; see `ootp_ai.db`.
"""
