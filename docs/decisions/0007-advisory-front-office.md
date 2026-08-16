# 0007 — The front office advises; the human GM executes

**Status:** Accepted
**Date:** 2026-08-15

## Context

Given [ADR 0001](0001-read-only-no-write-back.md) (no write-back), the system's
output is recommendations. The open question was what *shape* those take.

Two framings:

- **One oracle.** A single model reads the warehouse and emits the best decision
  for each question. Simple, one prompt, one answer.
- **A front office.** Several specialists with distinct remits — scouting,
  pitching, hitting, analytics, payroll, pro scouting — each reading the same
  warehouse, each producing recommendations within their domain.

The user's framing settled it: *"I am the GM, but I don't make decisions, I just
execute on the suggestions from my team. Hire experts, you know?"*

## Decision

**The system is a front office of specialist advisors.** Each has a defined
remit, reads the shared warehouse, and produces recommendations in its domain.
The human GM is the executive and the hands.

**Specialists are permitted — expected — to disagree.** Conflicting
recommendations are surfaced to the GM as a conflict, not silently merged into a
consensus.

## Consequences

**Buys:**

- Specialists carry narrow, deep context instead of one prompt trying to hold
  scouting, payroll, and bullpen management simultaneously.
- Disagreement is information. A Capologist objecting to the Pro Scout's trade
  target tells the GM something a merged answer would erase — and it is the part
  that makes the system feel like a front office rather than a recommender.
- Each specialist is independently testable against its own domain outcomes.
- It maps cleanly onto agents/skills, which the reference repos already use.

**Costs:**

- **More expensive per decision** — several specialists where one call would do.
- **Conflicts land on the GM.** Surfacing disagreement rather than resolving it
  moves work to the human, and a system that emits five contradictory
  recommendations per sim day is worse than one that emits a clear answer. There
  must be a limit on how much unresolved conflict is acceptable; it is not yet
  known what it is.
- Shared context across specialists risks drift — two advisors reasoning from
  differently-stale reads of the warehouse would produce fake disagreement, which
  is worse than no disagreement.

**Forecloses:**

- A single-oracle design. Adding a "chief of staff" that merges recommendations
  into one answer would recreate it and is not a small change — it would need to
  supersede this ADR.

## Notes

One question is deliberately open and needs settling before any specialist is
built: **do the advisors see true ratings or scout-perceived ratings?**

Scouted ratings are the honest Challenge Mode experience — a real front office
has imperfect information, and scouting accuracy is itself a lever the GM
invests in. True ratings would be quietly cheating, and would make any
competitiveness claim meaningless.

This is not settled here because [data-access.md §5](../data-access.md) records
that we do not yet know which file holds which. It is on the critical path and
gets its own ADR once the parser can tell them apart.
