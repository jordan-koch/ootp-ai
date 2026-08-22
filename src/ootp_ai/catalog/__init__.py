"""The catalog — what the warehouse holds, and what it deliberately does not.

The roster report tells the GM what it *can* see. This tells it what exists at all, and
— the half a list of landed tables cannot give — **what was withheld and why**. The
request's second desired outcome is *"the GM knows what it is not seeing"*, and a gap the
GM can see is a gap it can price an action against instead of discovering by hitting it.

## Two files, split by whether they change when the league is simulated

That is ADR 0005's own question, applied to this artifact rather than to a dataset:

* **The structural half does not change** — table names, grains, keys, coverage
  populations, source files, epistemic labels, withheld groups. It is *derived schema
  knowledge*, which ADR 0006 explicitly tracks, so it lives at `docs/warehouse-catalog.md`
  and survives a fresh clone with no game, no save and no database.
* **The volume half changes with every landing** — row counts, the resolved triple, the
  landed dates, freshness. It generates into the git-ignored output root beside the
  reports, partitioned by the same snapshot triple.

**One generator produces both**, and the tracked file is byte-for-byte the volume-free
rendering of the same model. That is what lets `tests/test_catalog.py` regenerate the
structural half during the test and refuse any byte that differs — a hand edit to the
tracked file cannot survive, which is the property a tracked generated artifact needs and
the reason the split is safe to make at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

__all__ = [
    "CATALOG_JSON_FILENAME",
    "CATALOG_MARKDOWN_FILENAME",
    "DEFAULT_DOCS_ROOT",
    "TRACKED_JSON_FILENAME",
    "TRACKED_MARKDOWN_FILENAME",
]

#: The GM's copy, rendered beside `roster.md` under the snapshot-partitioned output root.
CATALOG_MARKDOWN_FILENAME: Final = "warehouse-catalog.md"

#: The machine-readable sibling of the GM's copy (scope folded-in §4). Named `catalog.json`
#: rather than after the Markdown because it is the discovery surface a future
#: umpire-spawned advisor reaches for, not a second copy of the page.
CATALOG_JSON_FILENAME: Final = "catalog.json"

#: The tracked pair, written under `docs/`. Same generator, volume omitted.
TRACKED_MARKDOWN_FILENAME: Final = "warehouse-catalog.md"
TRACKED_JSON_FILENAME: Final = "warehouse-catalog.json"

#: Where the tracked pair lives. CWD-relative for the reason `config.py` gives its own two
#: roots: an absolute default would be machine-specific, and this repo is public (ADR 0006).
#: It is not an `.env` setting because it is not a property of the machine — the tracked
#: catalog lives beside the other docs in every clone, and `tests/test_repo_structure.py`
#: requires it to. `--docs-root` overrides it, which is what lets a test drive the writer
#: without touching the committed copy.
DEFAULT_DOCS_ROOT: Final = Path("docs")
