# 0014 — Staff quality is the information channel

**Status:** Accepted
**Date:** 2026-08-15

## Context

[ADR 0012](0012-scouted-ratings-only.md) settled *which* view of a player the front office
gets: the scouted one, never the true one. It did not settle **how good that view is**. It
treated scouting as a filter without saying what determines the filter's strength.

OOTP answers that question itself. The accuracy of what an organization sees is a function of
the people it employs to look — scouting director, scouts, coaches — each carrying ratings the
game displays on the 20–80 scale. That is a shipped mechanic, not a house rule, and the project
has to decide whether to lean on it or route around it.

The temptation to route around it is real, and from the inside it does not look like cheating.
ADR 0012 forecloses the obvious version — reading the true-rating byte "just for calibration."
It says nothing about the subtler one: **building** our way to better information. A model that
regresses scouted ratings against outcomes to back out the truth. A join to real-world Statcast
data that tells us what our scout could not. An inference layer whose output happens to be more
accurate than the scouting department that is supposed to be our only eyes.

Each of those satisfies the letter of ADR 0012 while dissolving its point.

## Decision

**The fidelity of everything the front office sees is a function of staff quality, and the only
sanctioned way to improve it is to hire better staff.**

Stated as the rule it has to be applied as:

> **If the front office wants a clearer picture, the answer is always a personnel move, never a
> code change.**

Three things follow directly:

- **The scouted view is the primary rating source, not a post-filter.** The parser reads what
  the organization believes as a first-class value. True ratings are the thing it must identify
  precisely enough to *exclude*. A naive implementation gets this backwards — reads the true
  value and filters it — and the result is indistinguishable from correct until it is far too
  late to unwind.
- **Staff are a first-class input.** `coaches.dat` is not organizational furniture. It describes
  the resolution of the front office's entire picture.
- **Improving fidelity is an in-game act.** Hiring a better scouting director is executed by the
  operator with club money, at the speed of the game's hiring cycle. It is not something the
  pipeline can deliver.

## Consequences

**Buys:**

- **Staff budget becomes an information budget.** Money spent on scouts is money not spent on
  players, and it buys *resolution* rather than wins. In ordinary OOTP play staff hiring is an
  afterthought; here it is a primary lever.
- **It makes [ADR 0013](0013-action-economy.md) pay off further than 0013 anticipated.** That
  ADR has staff quality affecting the *output* of an action. This extends it: staff quality also
  sets the fidelity of everything read for **free**. A good scouting director is not merely
  better on the trips he is sent on — he makes the whole warehouse sharper.
- **The parser gets a clearer correctness target.** Its job is not to be maximally truthful. It
  is to be maximally faithful to *what the organization sees*. That is a testable property;
  "as accurate as possible" is not.
- **Failure diagnosis gains a branch that is actually actionable.** A bad outcome was a bad read,
  a bad decision, or an underinvested scouting department. The first two are genuinely hard to
  separate ([`gm/staff.md`](../../gm/staff.md)); the third is a line item.
- **It closes the loophole before it opens.** A rule discovered mid-season, after someone has
  already built the model, is a rule that gets argued about instead of followed.

**Costs:**

- **It creates a hard dependency on an unsolved problem.** [`data-access.md` §5](../data-access.md)
  records as `unconfirmed` which file holds true ratings and which holds scouted. Under this ADR
  the front office cannot be served a single rating until that is `verified`. A warehouse that
  can name the roster but cannot say how good anyone is is a real possible first milestone.
- **Early seasons may be genuinely low-resolution, by design.** If the inherited staff is poor,
  the GM starts close to blind and will make defensible decisions on bad information. That is the
  mechanic working, and it will not feel like it.
- **A whole class of legitimate-looking engineering work is now off-limits**, and the boundary
  has to be defended in review every time — because it will always arrive framed as "this is just
  a better model."
- **It is prose, not prevention.** The same structural weakness as
  [ADR 0009](0009-write-capable-implementation-subagent.md)'s write allowlist and 0013's action
  economy. Nothing in the harness stops an inference layer from being built. It holds because it
  is written down and because a reviewer knows to look for it.

**Forecloses:**

- Any code path that surfaces a truer value than the organization's staff can see.
- Inference layers whose purpose is reconstructing true ratings from observables.
- Overriding a scouted rating with a parsed one on the grounds that the scout is obviously wrong.
  Sometimes the scout is obviously wrong. That is the game.
- Treating better tooling as a substitute for a better scouting department.

## Notes

**The real-world cross-walk survives, with a boundary.** [`data-access.md` §2](../data-access.md)
records that real players carry their Lahman/BBRef ID into the save, cross-walking the league to
Retrosheet, FanGraphs and Baseball Savant. That data is **public record** and stays free to hold —
a real front office has Savant open too. But it describes the *real* player, and the simulated one
diverges from him on the first pitch. So a real-world prior is an **input to an evaluation, never
a substitute for one**, and under [ADR 0013](0013-action-economy.md) turning it into an evaluation
of a specific player is an action. The cross-walk is a research asset, not a back door to the
answer key.

`inferred`, and worth confirming early: that scouting accuracy tracks staff ratings closely enough
for hiring to be a meaningfully graded lever rather than a step function. If it turns out to be
nearly binary, the information-budget tradeoff above is much less interesting than this ADR
assumes.

This **extends** [ADR 0012](0012-scouted-ratings-only.md) rather than superseding it. 0012's core —
the GM never sees true ratings — is unchanged. This says where the alternative comes from, and
closes the paths around it.
