# Architecture Decision Records

One file per settled decision. An ADR records **why a choice was made and what it
cost** — the cost line is not optional, and an ADR without one is incomplete.

**Read these before proposing anything structural.** Re-litigating a settled
decision is the most expensive thing that can happen in this repo.

| # | Decision | Status |
|---|---|---|
| [0001](0001-read-only-no-write-back.md) | The system never writes to the game | Accepted |
| [0002](0002-parse-binaries-not-export.md) | Ingest by parsing save binaries, not the in-game export | Accepted |
| [0003](0003-challenge-mode-league.md) | The managed league runs in Challenge Mode | Accepted |
| [0004](0004-mysql-warehouse.md) | MySQL is the warehouse | Accepted |
| [0005](0005-hybrid-data-layer.md) | Builders for static reference, dbt medallion for snapshot facts | Accepted |
| [0006](0006-public-repo-local-data.md) | Public repository, local data | Accepted |
| [0007](0007-advisory-front-office.md) | The front office advises; the human GM executes | **Superseded by 0010** |
| [0008](0008-panels-by-default.md) | The panel is the default; a skip is argued in writing | Accepted |
| [0009](0009-write-capable-implementation-subagent.md) | One write-capable implementation subagent | Accepted |
| [0010](0010-main-thread-is-the-gm.md) | The main thread is the GM; the human is the operator | **Superseded by 0017** |
| [0011](0011-gm-memory-is-tracked.md) | GM memory is tracked in git | Accepted |
| [0012](0012-scouted-ratings-only.md) | The GM sees scouted ratings, never true ratings | Accepted |
| [0013](0013-action-economy.md) | The action economy | Accepted |
| [0014](0014-staff-is-the-information-channel.md) | Staff quality is the information channel | Accepted |
| [0015](0015-gm-is-employed-not-appointed.md) | The GM is employed, not appointed | Accepted |
| [0016](0016-gm-reads-reports-not-queries.md) | The organization reads the warehouse; the GM reads reports | Accepted |
| [0017](0017-gm-is-a-subagent.md) | The GM is a subagent; the main thread and operator are umpires | Accepted |
| [0018](0018-retention-is-infrastructure.md) | Retention is infrastructure; analysis over history is commissioned | Accepted |
| [0019](0019-reading-costs-an-action.md) | Reading costs an action; a report is built once and read for free | Accepted |
| [0020](0020-sanctioned-lookahead-seam.md) | One sanctioned seam may index a save buffer; everywhere else walks | Accepted |

## Format

```markdown
# NNNN — Title

**Status:** Proposed | Accepted | Superseded by NNNN
**Date:** YYYY-MM-DD

## Context
What forced the decision. What was true at the time.

## Decision
What we chose, stated plainly.

## Consequences
What this buys. **What it costs.** What it forecloses.
```

Supersede rather than edit. A decision that turned out wrong is a record worth
keeping — write the new ADR, mark the old one superseded, and say what changed.
