# 0011 — GM memory is tracked in git

**Status:** Accepted
**Date:** 2026-08-15

## Context

[ADR 0010](0010-main-thread-is-the-gm.md) makes the main thread the GM. A GM without
continuity across sessions is a GM with amnesia — worse than the advisory model it replaced,
because at least a human carried the thread.

Everywhere else in this repo, local state is disposable and gitignored. `var/` holds save
snapshots and the warehouse, and both are **regenerable**: the snapshots re-copy from the
save, the warehouse rebuilds from the snapshots.

The GM's memory is not like that, and the reason is specific:

> **The save records what happened. It never records why the GM chose it.**

You cannot re-derive *"we passed on the extension because we projected the comp market to
soften"* from `players.dat`. That reasoning exists in exactly one place, and if it is lost it
is lost permanently. The same is true of standing orders, staff evaluations, and every
adjudication in the action ledger.

This is the identical argument that makes `careers/**/events.jsonl` tracked in the sibling
`nba2k-rpg` repo against every other convention in it.

## Decision

**`gm/` is tracked in git.** It is the one place this repo inverts the "local state is
disposable" rule, and the inversion is deliberate.

It holds the charter, standing orders, decision records, the action ledger, and staff notes.
Contract and layout: [`gm/README.md`](../../gm/README.md).

Its mirror stays intact: **`var/` holds only regenerable things.** A file that cannot be
rebuilt from the save does not belong there.

## Consequences

**Buys:**

- The GM survives a context reset. A fresh session reads `gm/` and is the same GM — which is
  what makes ADR 0010's context ceiling survivable instead of fatal.
- Decision rationale is durable, diffable, and reviewable. `git log` over `gm/decisions/`
  is the GM's own history of how its thinking changed.
- The action ledger accumulates into precedent ([ADR 0013](0013-action-economy.md)), which
  requires it to be permanent and append-only.
- Staff evaluation becomes possible across seasons rather than within one.

**Costs:**

- **The repo is public, so every GM decision is world-readable forever.** That is acceptable
  here — it is a baseball save — but it is a genuine constraint, and nothing operational,
  personal, or machine-specific may leak into a decision record.
  `tests/test_no_leaks.py` covers `gm/` like everything else.
- **`gm/` will grow for as long as the experiment runs**, and unlike `var/` it can never be
  cleared. Ten seasons of weekly ledger entries is real volume. Mitigation is format
  discipline — JSONL for the ledger, one file per decision, no prose dumps.
- **A `.gitignore` rule added carelessly can shadow the carve-out** and silently stop backing
  up the only copy of the GM's reasoning. `tests/test_repo_structure.py` guards it; if that
  test fails it is not being pedantic.

**Forecloses:**

- Putting GM state in `var/`. If a future phase wants a derived read-model over the ledger,
  *that* goes in `var/` — but the ledger itself never does.

## Notes

The distinction to hold onto, because it decides every future placement question:

> **Can this be rebuilt from the save?** Yes → `var/`. No → `gm/`, tracked.

A projection is regenerable. The decision to trust it over the scouting report is not.
