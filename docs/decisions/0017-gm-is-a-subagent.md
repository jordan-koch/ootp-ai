# 0017 — The GM is a subagent; the main thread and operator are umpires

**Status:** Accepted
**Date:** 2026-08-16
**Supersedes:** [0010](0010-main-thread-is-the-gm.md)

## Context

[ADR 0010](0010-main-thread-is-the-gm.md) put the GM in the main thread and
explicitly **considered and rejected** the alternative this ADR now adopts:

> An alternative was considered: a **GM subagent** acting as orchestrator.
> Rejected. It puts indirection between the operator and the decision-maker, it
> hits nesting limits when it needs to spawn staff, and the operator should be
> able to *talk to* the GM rather than file tickets with it.

Three things have happened since that make the trade come out differently.

**Prose failed a live test.** Every information constraint in this repo is
enforced by the GM's own discipline —
[ADR 0016](0016-gm-reads-reports-not-queries.md) says so in its own Costs section,
as do [0013](0013-action-economy.md) and
[0009](0009-write-capable-implementation-subagent.md). ADR 0016 exists **because
the constraint was violated within hours of the surrounding rules being written**:
the GM queried the ground-truth database to settle a baseball question. It did not
feel like cheating. It felt like diligence. That is exactly why prose does not
hold — the violation is invisible from the inside.

Agent `tools:` grants are *not* prose. They are enforced by the harness
([`.claude/agents/README.md`](../../.claude/agents/README.md)). A GM without a
shell cannot open a database, whatever it believes about its own diligence.

**ADR 0010's predicted cost arrived early.** It warned that the main thread's
context would hold "league state, advisor output, *and* the engineering work" and
that "over a season that is a great deal." That is already true after a single
session in which **zero games have been played**.

**The adjudication loop never existed.** ADR 0013 describes the GM proposing a
ruling and the operator confirming or overriding. In practice the same agent
proposed rulings to itself and the operator rubber-stamped them. There was never
an independent proposer — only one party wearing both hats politely.

## Decision

**The GM is a subagent. The main thread and the operator are umpires.**

**The GM agent** holds `Read` and `Glob` and nothing else — no shell, no database,
no ability to spawn. It reads [`FRONT_OFFICE.md`](../../FRONT_OFFICE.md),
[`gm/`](../../gm/README.md), and whatever reports it has been given. It proposes
actions with reasoning in a fixed return format. It never executes, never spawns,
and never writes to `gm/`.

**The umpires** are the main thread and the operator together. They run the
experiment: adjudicate cost and feasibility, spawn advisors when the GM
commissions one, hold the pen on `gm/`, build and repair the apparatus, and
enforce the rules. **Umpires do not bat.**

**Advisors are subagents the umpires spawn on the GM's commission.** The GM asks
for a scouting read; the umpires rule on the cost and spawn a specialist that may
touch the warehouse; its report goes back. The GM never held a query tool at any
point.

**Two staffs, and they are not in competition:**

| | What it is | What it costs |
|---|---|---|
| **In-game personnel** | The **sensor** — determines what the data *says*. A weak scouting director yields a weak `players_scouted_ratings` | Club money, spent by the operator |
| **Repo agents** | The **processing** — determines what we *learn* from it | Actions only |

The ordering has teeth: **a brilliant analyst cannot compensate for a bad
scout**, because it can only read what the sensor produced. That is
[ADR 0014](0014-staff-is-the-information-channel.md) enforced structurally rather
than promised. The inverse — an excellent scouting director whose reports nobody
analyses — is a real failure mode a GM can commit.

### Answering ADR 0010's three objections

**"It puts indirection between the operator and the decision-maker."** That
indirection is now the point. It is what isolates the experimental subject, and
0010's own Costs section complained that the GM "wears two hats" — indirection is
how that stops being true.

**"It hits nesting limits when it needs to spawn staff."** Dissolved by design
rather than worked around: the GM never spawns. It commissions, and the umpires
spawn. Nesting never arises.

**"The operator should be able to talk to the GM rather than file tickets."**
Partly conceded — conversational access is genuinely lost. Three things soften it.
ADR 0013 already required *declare before doing*, which is a written protocol
rather than a chat. A written proposal with reasoning is better evidence than a
conversation. And the operator still talks to the umpires, who hold the rules.

## Consequences

**Buys:**

- **[ADR 0016](0016-gm-reads-reports-not-queries.md) becomes enforced rather than
  promised.** The single most important constraint on the GM stops depending on
  the GM's self-restraint, which had already failed once.
- **The experimental subject is isolated.** "An AI front office was competitive"
  is currently confounded by the same agent having built the pipeline, chosen the
  league settings, and written the rules it plays under. A tool-restricted agent
  fed only what the organization produces is something you can point at.
- **The adjudication loop finally has two parties.** The GM proposes; the umpires
  rule. That is the mechanic ADR 0013 always described.
- **Advisor disagreement becomes real.** Two independently spawned specialists can
  genuinely disagree. Personas inside one context cannot — they can only perform
  disagreement, which ADR 0010's best property deserved better than.
- **The main thread is freed completely.** It can query anything, run ad-hoc
  analysis, repair the warehouse, and hold information the GM never sees.
  Asymmetric information between a front office and its ownership is realistic.
- Context pressure resolves. League state and engineering stop sharing a window.

**Costs:**

- **Every baseball decision becomes a spawn** — slower, more expensive, and with
  no ability to interrupt mid-reasoning.
- **The GM's reasoning moves into a transcript that may go unread.** Today the
  operator corrects the GM continuously, and that is how three errors were caught
  in one session. The return contract must therefore demand *reasoning*, not
  conclusions — and reading it is now a real obligation rather than a byproduct.
- **Continuity depends entirely on `gm/`.** ADR 0011 was already a precondition;
  it is now the only thread. A per-invocation agent cannot coast on conversational
  context — which is a discipline improvement and a fragility at the same time.
- **Two more moving parts to maintain**: an agent definition and a return
  contract, both of which can drift from the rules they implement.
- The operator loses the ability to simply talk to his GM.

**Forecloses:**

- The GM touching a database, for any reason, including a good one.
- The GM spawning anything.
- The GM writing to `gm/`.
- **The main thread making baseball decisions.** Umpires do not bat. If the main
  thread finds itself deciding which of two players to promote, this ADR is being
  violated exactly as ADR 0010 was.

## Notes

**[ADR 0009](0009-write-capable-implementation-subagent.md) needs revisiting.** It
decided on "one write-capable implementation subagent," which stops being an
accurate description once advisors exist.

**The action economy is the tuning lever.** If the GM does too much too quickly,
the fix is fewer actions or dearer items — not new prohibitions. But **record each
adjustment with its reasoning, and prefer to turn it between seasons rather than
during one.** Tuning mid-season makes seasons incomparable, and the competitiveness
claim is the thing being measured. Umpires do not move the strike zone mid-game.

**[`FRONT_OFFICE.md`](../../FRONT_OFFICE.md) is the shared rulebook**, not the
agent's private one. The GM reads it to know the rules; the umpires read it to
enforce them. Folding it into the agent definition would put the referee in the
position of reading the player's copy over his shoulder.

**What ADR 0010 got right survives.** Staff disagree in public and the GM
adjudicates; the human is out of the baseball loop; the operator's execution and
honest reporting remain load-bearing, and remain the one input nothing in this
repo can verify.
