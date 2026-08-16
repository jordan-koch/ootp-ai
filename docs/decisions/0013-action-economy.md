# 0013 — The action economy

**Status:** Accepted
**Date:** 2026-08-15

## Context

[ADR 0010](0010-main-thread-is-the-gm.md) gives the GM the chair. Without a constraint on
what it can do per unit of game time, that title has no teeth, because the GM holds an
advantage no real front office has: **it can pause time.** It can deliberate indefinitely,
scout everyone, work every trade market, and re-optimize every week at zero cost.

That breaks three things at once. A competitiveness claim is hollow if the competitor can
think forever. Every decision becomes uninteresting, because prioritization is what makes a
decision hard. And the token cost of "optimize everything every week" is unbounded, which is
how a project stops being fun to run.

Real GMs are bounded by attention and staff bandwidth, and the interesting part of the job is
spending them.

## Decision

**The organization gets a fixed budget of actions per game period. The GM allocates them.**

**An action buys information or options — never execution.**

| Free | Costs an action |
|---|---|
| Reading the warehouse | Scouting a player outside existing coverage |
| GM deliberation | Working a trade market for a specific need |
| Executing a decision already made | A deep projection run on a target |
| Staff applying a standing order | Establishing or changing a standing order |

**Standing orders are the load-bearing mechanic.** The GM spends an action setting a policy —
a lineup philosophy, a bullpen leverage rule, a development plan. Staff then apply it every
game *forever, at zero cost*, until someone changes it. Changing it costs another action.

This is how real organizations work: a GM defers to a coach and spends attention on *changing*
things, not maintaining them. It also produces the most interesting failure mode available
here — **a standing order that quietly stops being right.** The platoon policy set in April is
wrong by July, and noticing costs an action the GM would rather spend elsewhere.

### Starting parameters — all config, all expected to be wrong

- **6 actions per in-season week; 10 per offseason week.**
- **Unused actions expire.** Banking them recreates pause-time in slow motion.
- **A failed action still costs.** A scouting trip that finds nothing spent the week anyway.
- **No emergency reserve.** An ace tearing a UCL on Tuesday comes out of the same budget.
  That is exactly the prioritization pain worth having.
- **Staff quality affects the *output* of an action, never the *count*.** Letting a good
  scouting director grant extra actions is a runaway loop, and OOTP gives fixed staff slots
  anyway.

### The taxonomy is open, and the operator adjudicates

A closed list of action types cannot be written in advance — nobody has the foresight for
five to ten seasons of emergent baseball. So the list stays open, and the anti-gaming
property comes from **who rules** rather than from what is on the list:

1. **The GM proposes a ruling with reasoning, and cites the closest precedent.** It does not
   ask an open question — that would push cognitive work back onto the operator, which is the
   thing ADR 0010 exists to stop.
2. **The operator confirms or overrides.** Most are confirmations. **The overrides are the
   data** — they are where the operator's judgment diverges from the GM's model of it.
3. **Every adjudication is recorded**, cost or free, with its reasoning. A verdict without
   reasoning cannot extend to an unseen case, and unseen cases are the entire point.
4. **Ruling against a cited precedent is an overturn**, recorded as such with its reason.

**Autonomy increases on a measured signal, not a feeling:** when an action class reaches
**20 proposals with zero overrides**, it graduates to auto-approved. The GM stays instructed
to flag a materially different case rather than assume the class covers it.

## Consequences

**Buys:**

- Prioritization becomes the GM's actual job, which is what makes it a GM.
- **Staff quality becomes measurable.** Scarcity creates the denominator: twelve actions on
  the draft and three busted picks is a return on invested attention. Without scarcity,
  "should I fire the scouting director" has no evidence behind it. This is what makes
  [ADR 0012](0012-scouted-ratings-only.md) pay off.
- Token spend per period becomes bounded and predictable — roughly 200 staff engagements per
  season rather than an open-ended optimization budget.
- The doctrine bootstraps itself. An unsolvable up-front design problem becomes a data
  collection problem.

**Costs:**

- **It is a house rule. OOTP does not know about it and nothing enforces it.** The same
  structural weakness as the write allowlist in
  [ADR 0009](0009-write-capable-implementation-subagent.md): prose, not prevention. It has
  teeth only because the GM declares honestly and the ledger is written *before* the work.
- **Season one is adjudication-heavy.** Everything is novel. That is the price of the
  dataset, and the falloff curve is itself a signal about whether the taxonomy is converging.
- **The operator is in the loop every period.** Lighter than deciding baseball, but not zero,
  and it is a standing tax on playing.
- The starting numbers are guesses. Six may be crushing or generous, and nobody will know
  until a season has been played.

**Forecloses:**

- Retroactive labelling. **Declare the action, then do the work.** A ledger written after the
  fact is justification, not constraint, and the whole mechanism collapses into theatre.
- The GM defining its own action *types* unilaterally. It proposes; it does not rule.

## Notes

The ledger lives in [`gm/`](../../gm/README.md) and is tracked
([ADR 0011](0011-gm-memory-is-tracked.md)) — it must be permanent and append-only for
precedent to mean anything. **Doctrine is a query over the ledger, not a separate document**;
a maintained summary would drift from the record and then nobody could say which was true.
