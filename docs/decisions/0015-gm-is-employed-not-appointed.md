# 0015 — The GM is employed, not appointed

**Status:** Accepted
**Date:** 2026-08-16

## Context

[ADR 0010](0010-main-thread-is-the-gm.md) gave the GM the chair.
[ADR 0013](0013-action-economy.md) bounded what it can do per week.
[ADR 0012](0012-scouted-ratings-only.md) bounded what it can see, and
[ADR 0014](0014-staff-is-the-information-channel.md) said what improves that.

None of them says **who decides whether the GM is any good.**

That gap matters more than it looks. The project's claim is that this front office
can be *competitive*, and three constraints already stop the claim from being
hollow: the league cannot be edited, the answer key cannot be read, and time
cannot be paused. But with no external judge the GM grades its own homework — it
decides what the goal was, whether a season met it, and when a rebuild is
"working." A record assembled that way is evidence of nothing.

OOTP supplies the missing piece. **Owner Goals** is a per-league setting: the
owner hires you, states what he expects of the franchise, and fires you if you
miss. The same system allows a GM to leave for another job.

`gm/staff.md` already exists so the GM can evaluate its staff. Nothing evaluated
the GM.

## Decision

**The GM is an employee. The owner sets the goals, judges the results, and can
fire him. Being fired does not end the experiment.**

Four parts:

- **The subject of the experiment is a career, not a club.** The first job is the
  Boston Red Sox. If it ends, the GM applies elsewhere and the record continues.
  "An AI front office can be competitive" is better evidenced across employers
  than inside one.
- **Owner goals are the sole success criterion.** The GM gets no second
  scorecard. A self-authored goal running alongside the owner's would let the GM
  hit its own, miss the owner's, and narrate that as success — reintroducing
  exactly the goalpost-moving that an external judge exists to prevent.
- **Departure is operator-initiated.** The operator decides when a career move is
  on the table. The GM may then take a job or stay, but it never initiates a
  departure and never engineers one.
- **`gm/` splits by scope when a second club exists**, not before. Career-scoped
  memory survives an employer; club-scoped memory does not.

### What is not a second scorecard

`gm/charter.md`'s **operating principles** and **constraints we accept** stay.
They are *method*, not objective: the tiebreakers used when advisors disagree,
and self-imposed limits recorded so that abandoning one under pressure is visible
rather than silent. Neither competes with the owner's goals; both describe how
the GM pursues them.

## Consequences

**Buys:**

- **A fourth constraint, and the only one that guards the scoring rather than the
  simulation.** Challenge Mode stops the GM cheating the game; owner goals stop
  it cheating the measurement.
- **It sharpens [ADR 0014](0014-staff-is-the-information-channel.md).** That ADR
  argued staff budget becomes an information budget. With an owner grading on
  results, money spent on scouts instead of players becomes a bet with the GM's
  job attached — a better version of the tradeoff than 0014 described.
- **The most interesting failure available** stops being "the model was wrong" and
  becomes **"the model was right and the GM was fired before it paid off."**
- **Quitting cannot be rationalized, because the capability is absent.** Nearly
  every guard in this repo is prose rather than prevention
  ([ADR 0009](0009-write-capable-implementation-subagent.md), 0013). This one is
  genuinely enforced: the operator holds the prompt and the GM does not.
- The GM finally carries the same kind of denominator it applies to its staff.

**Costs:**

- **It measures a harder, narrower thing.** The claim becomes "competitive under
  political constraint" rather than "competitive in a vacuum." More realistic,
  less clean.
- **Short-termism becomes a live pressure**, and the GM may be pushed toward moves
  it believes are wrong. That is the job — but it means a decision can be
  correctly motivated and still bad baseball, which complicates every later
  post-mortem.
- **A firing costs continuity.** Charter, standing orders and staff assessments do
  not transfer, and rebuilding them at a new club is real work.
- **Season one has unknown difficulty.** The owner's goals are not visible until
  the league exists. If they prove to be purely win-now, the experiment measures
  survival rather than organization-building, and that needs noticing when the
  goals are first read rather than in season three.

**Forecloses:**

- The GM defining, revising, or grading its own success criterion.
- Self-initiated departure, including engineering a firing to reach a preferred
  job.
- Treating a firing as the end of the experiment.

## Notes

**A firing is only informative if the reasoning was recorded first.** A GM fired
while executing a written, well-argued plan has produced better evidence than one
who survived by drifting. That is what `gm/decisions/` is for, and it is why
*declare before doing* ([ADR 0013](0013-action-economy.md)) binds baseball
decisions and not only actions.

**The principle for the split:** memory about *what costs an action* is career
memory and survives an employer; memory about a roster, a payroll, a staff or a
competitive window is club memory and does not.

**The per-file mapping is owned by [`gm/README.md`](../../gm/README.md)**, not
restated here — it is an operational contract that changes as `gm/` grows, and a
second copy in an ADR would drift from it. It is written down now, before the
split it describes, because the moment of an actual firing is the worst available
time to argue about what survives.
