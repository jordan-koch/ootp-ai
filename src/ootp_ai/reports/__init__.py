"""Rendered reports — the only surface the GM ever reads (ADR 0016).

The GM does not query the warehouse. It reads Markdown that this package wrote, which
is what makes the serving gate in `contracts/policy.py` a real boundary rather than a
convention: there is one path to a page and it runs through here.

Two rules shape every module in this package:

* **The organisation filter lives here, never at bronze.** Bronze is 1:1 with what the
  walker produced (`.claude/agents/data-engineer.md`), so "only our club" is a reporting
  decision and belongs at the reporting layer.
* **Every column is checked against the policy before it is rendered.** Not by
  inspection — `roster.py` declares its columns as data and `check_renderable` refuses
  the whole report if any one of them is withheld.
"""

from __future__ import annotations

from ootp_ai.reports.resolve import (
    NoSuchSnapshot,
    SnapshotRef,
    report_dir,
    resolve_snapshot,
)

__all__ = [
    "NoSuchSnapshot",
    "SnapshotRef",
    "report_dir",
    "resolve_snapshot",
]
