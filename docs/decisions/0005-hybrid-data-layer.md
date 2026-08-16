# 0005 — Builders for static reference, dbt medallion for snapshot facts

**Status:** Accepted
**Date:** 2026-08-15

## Context

This project's data splits cleanly into two populations with different physics:

**Static reference data** — `players.csv`, `names.xml`, `world_default.xml`,
`schools.xml`, and the engine constant tables (`financials.txt`,
`era_ballparks.txt`, `era_stats.txt`, `total_modifiers.txt`). These ship with the
game. They change when the game is patched and at no other time. They have no
history, no grain question, no update semantics.

**Snapshot facts** — everything parsed out of the save: rosters, ratings,
contracts, stats, standings, transactions. These change every sim date, and their
value is largely in how they change over time.

The two reference repos solve these differently. `pokemon-lab` uses
`build/build-*.py` → `datasets/` with a `manifest.json` registry resolved by
logical name. `nba-analysis` uses a DuckDB + dbt medallion (bronze/silver/gold).

## Decision

**Use each pattern where its physics fit.**

- **Static reference → builders.** `build/build-*.py` scripts produce tracked
  artifacts under `datasets/`, registered in `datasets/manifest.json` and
  resolved **by logical name, never by hardcoded path**.
- **Snapshot facts → dbt medallion** in MySQL ([ADR 0004](0004-mysql-warehouse.md)):
  bronze (faithful landing of parser output), silver (conformed, grain-declared),
  gold (serving models for the front office).

## Consequences

**Buys:**

- Never-changing shipped files don't get routed through a transformation pipeline
  designed for mutating facts, where incremental logic and snapshot semantics are
  pure overhead.
- The genuinely temporal data gets dbt's lineage, tests, and grain contracts,
  which is exactly where correctness risk lives.
- Reference data resolves by name, so relocating a dataset is a one-line manifest
  edit rather than a search-and-replace.

**Costs:**

- **Two mental models in one repo.** A contributor must know which population a
  dataset belongs to before knowing how to add it. The boundary must be stated in
  `CLAUDE.md` and defended in review.
- Two toolchains to maintain — Python builders and dbt — each with its own
  testing story.
- The boundary will be tested by genuinely ambiguous cases. `players.csv` is the
  sharpest: it is static reference data *and* a day-0 fact snapshot.

**Forecloses:**

- Nothing structural. Either pattern can absorb the other's territory later if
  the split proves wrong.

## Notes

The boundary rule, stated once so it can be applied:

> **Does this artifact change when the league is simulated?**
> No → builder + `datasets/`. Yes → parser + dbt medallion.

`players.csv` resolves as **static reference**: it does not change when the league
is simulated. Its day-0 snapshot role is a *use*, not its nature — and treating it
as a fact source is precisely the mistake that would serve stale ratings.
