# 0010 — The main thread is the GM; the human is the operator

**Status:** **Superseded by [0017](0017-gm-is-a-subagent.md)**
**Date:** 2026-08-15
**Supersedes:** [0007](0007-advisory-front-office.md)

> The rejection of a GM subagent recorded below was reversed by
> [ADR 0017](0017-gm-is-a-subagent.md), which answers each of the three objections
> directly. The reversal was forced by a live failure: the information constraint
> this ADR left to the GM's own discipline was violated within hours of being
> written down. What survives is that advisors disagree in public, the GM
> adjudicates, and the human stays out of the baseball loop.

## Context

[ADR 0007](0007-advisory-front-office.md) put the human in the GM's chair: specialist
advisors produce recommendations, disagreement surfaces as a conflict, the human
adjudicates and executes. Three problems with that came out of using it.

**It left the hardest job with the person who didn't want it.** ADR 0007's own Costs
section flagged this and left it open:

> Conflicts land on the GM... a system that emits five contradictory recommendations per
> sim day is worse than one that emits a clear answer. There must be a limit on how much
> unresolved conflict is acceptable; it is not yet known what it is.

There is no good answer while the adjudicator is a human who has said plainly that he does
not want to make baseball decisions.

**It made the experiment unmeasurable.** If a human arbitrates conflicting advice, that
human's baseball judgment is inside the loop, and "can an AI front office be competitive"
becomes a question about a hybrid. The claim this project exists to test needs the human
*out* of the decision.

**It gave nothing a reason to improve.** An advisor that answers questions never develops a
motive to fix its own operations, because someone else owns the outcome. A GM who owns
results has an obvious one: *my scouting director keeps missing on college arms — change how
he weights tools against performance.*

An alternative was considered: a **GM subagent** acting as orchestrator. Rejected. It puts
indirection between the operator and the decision-maker, it hits nesting limits when it
needs to spawn staff, and the operator should be able to *talk to* the GM rather than file
tickets with it.

## Decision

**The main thread is the General Manager.** It owns decisions, priorities, staff, and
outcomes.

**The human is the operator.** Three responsibilities, all of them real:

1. **Execution.** Carries out the GM's decisions in-game. The system cannot write to the
   game ([ADR 0001](0001-read-only-no-write-back.md)), so the operator is the only path
   from decision to league state.
2. **Honest reporting.** Reports what actually happened, including misexecution.
3. **Adjudication.** Rules on what costs an action
   ([ADR 0013](0013-action-economy.md)).

Advisors remain, and ADR 0007's best property survives: **staff still disagree in public.**
What changed is the audience. Disagreement now surfaces to the GM, which adjudicates it,
acts, and records why — instead of landing on a human as an unresolved conflict.

## Consequences

**Buys:**

- Someone owns the decision. Conflict resolution has a home.
- The competitiveness claim becomes testable, because human judgment is out of the loop.
- A self-improvement motive exists for the first time: the GM has a reason to invest in its
  own front office, and [ADR 0013](0013-action-economy.md) gives it a currency to invest.
- The documentation describes what actually happens. Writing "the human GM decides" while
  the human intends to rubber-stamp would have been a documented fiction, and fictions rot.

**Costs:**

- **The main thread's context now holds league state, advisor output, *and* the engineering
  work.** Over a season that is a great deal. The mitigation is not a subagent — it is that
  GM memory must be good enough to reconstitute the GM from files, so context exhaustion is
  survivable rather than fatal. This makes
  [ADR 0011](0011-gm-memory-is-tracked.md) a precondition rather than a convenience.
- **The GM wears two hats.** It runs the club and it builds the platform. Those need
  different paperwork: engineering goes through `requests/`, baseball decisions do not.
  Routing a lineup change through intake → scope → plan → implement would be absurd.
- **Operator fidelity becomes a silent failure mode.** The GM reasons from the state the
  operator reports. A misexecuted move or an unreported outcome makes everything downstream
  wrong, with no test in this repo that could catch it.
- A fresh session with poor memory is a GM with amnesia — **strictly worse** than ADR 0007,
  where at least the human carried continuity.

**Forecloses:**

- Routing baseball judgment through the operator. If the GM finds itself asking the operator
  which of two players to promote, that is this ADR being violated, not a helpful check-in.
  Adjudication ([ADR 0013](0013-action-economy.md)) is the *only* judgment the operator owns.

## Notes

**On "dumb operator."** The role was proposed under that name and the name is rejected while
the role is kept. Execution fidelity is a genuine responsibility — the same class of hazard
as transcription error in a hand-entered system — and calling the role dumb invites treating
a bad report as unimportant. It is the one input the entire system cannot verify.
