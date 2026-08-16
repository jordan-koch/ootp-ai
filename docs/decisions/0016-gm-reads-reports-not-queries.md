# 0016 — The organization reads the warehouse; the GM reads reports

**Status:** Accepted
**Date:** 2026-08-16

> **Amended in effect by [ADR 0017](0017-gm-is-a-subagent.md).** The decision below
> stands unchanged, but its Costs section says *"it is prose, not prevention —
> nothing stops the GM opening a database."* That stopped being true when the GM
> became a subagent holding no shell. The belief is left as written because it is
> the record of what was believed; this note is the correction.
>
> **Clarified by [ADR 0018](0018-retention-is-infrastructure.md).** The Notes below
> draw the line as *"building a printing press is not the same as commissioning an
> article,"* which does not obviously resolve **retention** — keeping a scouted read
> so a question can be asked of it in three seasons. 0018 places retention on the
> press side, and gives the reason this decision's cost model does not supply:
> retention is *irreversible*, so charging for it would penalise foresight rather
> than judgement.

## Context

[ADR 0010](0010-main-thread-is-the-gm.md) gave the GM the chair and put a roster
of advisors underneath it, "reading a warehouse built from the save's own files"
and reporting up. [ADR 0013](0013-action-economy.md) then listed **"reading the
warehouse"** as free.

That phrasing is ambiguous, and the ambiguity was not theoretical. On 2026-08-16,
deciding whether to accept an owner's proposed goal swap, the GM queried the
ground-truth database itself and computed league-wide fan-interest percentiles to
inform the call — the incident is recorded in the limitation section of the
decision record `gm/decisions/2024-03-07-decline-fan-interest-goal.md` (ledger
seq 1). That is the analytics director's work, performed by the GM, at an
organization with no analytics director employed.

The decision happened to survive removing that analysis — the load-bearing
argument came from the owner's own goals screen. That was luck. Next time the
number would be load-bearing.

The ambiguity has to close **before** the warehouse exists. Once it does, the
temptation is constant, the act is invisible, and every individual instance looks
harmless.

## Decision

> **The organization reads the warehouse. The GM reads reports.**

- **The GM never queries the warehouse directly for a baseball purpose.** No
  exceptions, no "just this once."
- Information reaches the GM as **reports**: named, refreshable analytical
  products owned by a named staff member.
- **Commissioning a report costs an action.** Refreshing it, reading it, and
  reasoning over it are free, forever, until it is changed.
- **A one-off question no existing report answers also costs an action** —
  deliberately the same price, so that building durable capability is the better
  buy and ad-hoc asking is the worse one.
- **Reports are standing orders for information.** They live in
  [`gm/standing-orders.md`](../../gm/standing-orders.md) in the same format, with
  the same `Established` seq and `Review trigger` discipline.
- **The operator is not an analytics department.** He relays events and outcomes —
  results, transactions, injuries, owner communications, in-game notifications.
  He does not answer analytical questions on the GM's behalf.

### The test, for cases this list does not name

**What is the output used for?** If it informs a *baseball* decision, it is
analysis and needs a report. If it informs *pipeline construction* — what a field
means, whether a value is stored or computed, whether the parser is correct — it is
engineering, and the engineering hat reads whatever it needs.

The practical tell: **engineering findings land in `docs/`; baseball findings land
in `gm/`.** A query result being written into a decision record means the line has
already been crossed.

## Consequences

**Buys:**

- **ADR 0010's role split becomes real rather than aspirational.** Advisors that
  the GM routinely bypasses are decoration.
- **Information becomes a strategic investment.** *Which reports exist* is now a
  genuine decision, made under scarcity, with compounding returns. A GM who
  commissions the right things early is permanently better informed than one who
  does not — which is exactly how this works in reality.
- **It closes the largest remaining hole in the competitiveness claim.** Not the
  answer key — [ADR 0012](0012-scouted-ratings-only.md) handles that — but a
  tireless analyst on infinite call, which is an advantage no front office has.
- **The report registry inherits standing orders' best warning**: a report that
  quietly stopped measuring the right thing, refreshed for free all season because
  refreshing is free and noticing costs an action.
- **It sharpens [ADR 0014](0014-staff-is-the-information-channel.md) again.** Staff
  quality already set the *fidelity* of what the GM sees. Now the analytics team's
  output determines *what the GM can see at all*.

**Costs:**

- **Questions will go unanswered.** Something genuinely useful may stay unknown
  because no report covers it and commissioning one competes with the pennant race.
  That is the mechanism working, and it will not feel like it.
- **The bootstrap is severe.** Until the parser and warehouse exist there is no
  report channel at all. The GM is nearly blind in exactly the period when the
  operator, with the game's canned reports in front of him, can see everything.
- **Friction on every novel question.** The correct answer is usually "commission
  the report," which is slower than looking.
- **It is prose, not prevention** — like [ADR 0009](0009-write-capable-implementation-subagent.md)'s
  write allowlist and 0013's action economy. Nothing stops the GM opening a
  database. It holds because it is written down and because a query in a transcript
  is visible after the fact.

**Forecloses:**

- The GM issuing SQL, opening the warehouse, or reading save files directly to
  answer a baseball question.
- "Just this once" lookups, on the same posture as ADR 0012's foreclosed
  calibration exception.
- Routing an analytical question through the operator to avoid commissioning it.

## Notes

**Infrastructure is free; analytical direction is not.** The parser, the
warehouse, and the machinery that renders a report are engineering, go through
`requests/`, and cost no actions. What costs an action is *directing the analytics
team to produce a specific analysis*. Building a printing press is not the same as
commissioning an article.

**The front office's analysis is private.** Reports built on our own warehouse are
invisible in-game, so the operator cannot see them. That is realistic — an owner
does not read the analytics department's models — and it means whatever novel
views this front office builds are genuinely its own work rather than a restatement
of what the game already displays.
