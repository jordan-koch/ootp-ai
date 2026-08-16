# 0008 — The panel is the default

**Status:** Accepted
**Date:** 2026-08-15

## Context

The intake pipeline has four stages (intake → scope → plan → implement), and
stages 2 and 3 each spawn an adversarial multi-agent panel. Panels are the
expensive part.

The tempting design is to pre-register ceremony: mark each planned work item as
"small" or "large" up front and let the small ones skip stages. The sibling
`nba2k-rpg` repo tried exactly that — a ★ and a size estimate on every roadmap
row — and removed it, because both were guessed *before the work existed*.

This repo has a sharper reason to be careful. Most of what it builds rests on
beliefs about a reverse-engineered binary format
([`data-access.md`](../data-access.md)). Work that looks small ("just read one
more field") can rest on an `unconfirmed` claim that nobody has tested, and the
failure mode is a plausible wrong number rather than an error.

## Decision

**The full pipeline runs unless a skip is argued in writing**, in the request's
closing **Stage plan** section. The burden of proof is on the cheap path, never
on the panel.

**Three hard triggers foreclose the argument entirely** — any one and the panel
runs:

1. Intake's **Open Questions** came out non-empty.
2. **Explicitly out** couldn't be filled.
3. It touches something **expensive to reverse** — a settled ADR, the parser's
   field map, a dataset contract, a warehouse grain, or anything another request
   pins.

Ceremony is never decided in advance of a written request. The rubric lives in
[`requests/README.md`](../../requests/README.md#weight--the-panel-is-the-default),
which is its single owner; this ADR owns the decision, not the details.

## Consequences

**Buys:**

- Ceremony is decided against something written, by someone who has read it,
  rather than guessed against an idea nobody has articulated yet.
- Trigger 3 protects exactly what this project is most likely to break quietly:
  the field map and the warehouse grains.
- The triggers are mechanical. Trigger 1 in particular is just "did the intake
  agent write anything in Open Questions" — no judgment required.

**Costs:**

- **Small work pays a real tax.** A one-field parser addition can draw a full
  scoping and planning panel because it touches the field map. That is the
  intended trade, and it will feel wrong on the day it happens.
- Panels cost tokens and wall-clock. On a hobby project that is a genuine
  constraint on how much gets built.
- Writing a skip argument is itself work, so the cheap path is not actually
  cheap for genuinely trivial changes.

**Forecloses:**

- Pre-registering ceremony on unwritten work. No size estimates, no ★ column,
  no "this one's small" decided before the request exists.

## Notes

**A skip is not shipping unreviewed.** `/implement-plan` has a direct-build mode
that takes the intake artifact in place of a plan, and its adversarial reviewers
are derived from what the diff touched rather than from the plan — so they run at
full strength either way.

What a skip genuinely forfeits is **verification by execution against numbered
acceptance criteria**, because a skipped item never wrote any. That is the
content of the decision, not a gap in it: an item that needs numbered criteria
trips trigger 1 and never reaches the branch.

**Entry.** This governs work that gets a request at all. Typo fixes, dependency
bumps, and doc edits never enter the pipeline.
