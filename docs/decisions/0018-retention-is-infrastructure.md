# 0018 — Retention is infrastructure; analysis over history is commissioned

**Status:** Accepted
**Date:** 2026-08-16

## Context

[ADR 0016](0016-gm-reads-reports-not-queries.md) settled that the organization reads
the warehouse and the GM reads reports, and its Notes drew the line as *"infrastructure
is free; analytical direction is not — building a printing press is not the same as
commissioning an article."*

That metaphor does not obviously resolve **retention**. Snapshotting rosters and stats
reads as press. Retaining every scouted rating so that, three seasons from now, the GM
can ask *"has my scouting director been any good?"* reads to a reasonable person like
something he ought to have to ask for. The two feel different, and 0016 does not say
which side of the line they fall on.

It is not a hypothetical. The question arrived from the operator's own working life:
an organization discovering it had been serving current data only, and being asked to
start retaining history — a real cost, a real request, and one that could not be
satisfied retroactively.

That last clause is the whole problem, and it breaks an assumption the action economy
rests on.

**[ADR 0013](0013-action-economy.md)'s scarcity works because actions are recoverable.**
A period's actions not spent on a thing can be spent on it next period. The cost is
delay, and delay is survivable. **Retention is not recoverable.** A sim date not
captured can never be captured. Charging an action for it does not create a strategic
choice; it creates a **foresight trap**, in which the GM is penalised in 2027 for
failing to predict in 2024 which question he would eventually want to ask — about a
scouting director he had not yet hired.

## Decision

> **Keeping what we already read is infrastructure. Reading something new is a
> request. Asking history a question is commissioned.**

Three tiers, and the test is *where the work is*:

| Tier | Example | Cost |
|---|---|---|
| **Retain what the parser already reads** | every landed snapshot stays; nothing is overwritten or pruned | **Free.** Infrastructure. |
| **Widen what the parser reads** | a new file, a new field, per-scout report history | A **feature request** through `requests/`. If the GM asks for it, **also an action** — he is directing capability, not just receiving it. |
| **Analyse the retained history** | "model my scouting director's performance across three seasons" | **Commissioned. Costs an action**, exactly as 0016 requires. |

Three things follow:

- **The append-only grain is the mechanism, and it is already chosen.** Bronze is keyed
  `(save_id, sim_date, ingest_seq)` and never overwritten, so retention costs nothing
  marginal — it is the absence of a delete, not the presence of a feature.
- **Discovery stays free.** Under 0016 the GM reads the catalog for nothing, so the
  catalog states what is retained and since when. He learns the history exists without
  paying, and pays when he asks it a question. Charging for retention *and* hiding it
  would be a trap twice over.
- **Retention is not a licence to widen.** A slice may not land a field *because it
  might be useful later*. That is tier 2 wearing tier 1's clothes, and it is how a
  parser's field set grows without anyone deciding — every landed field is a field
  somebody re-validates after a game patch.

### The dynamic this produces, which is the point

A GM asking today for a report on his scouting director's track record should be told:
**it costs an action, it needs an ingestion slice, and the history starts accumulating
now — so a meaningful answer is two seasons away.**

That is what a real front office hears, and it is a better decision than either "free"
or "one action." It prices *investing now for information later*, with a lag the GM has
to weigh against the pennant race — and it means a GM who thinks about instrumentation
early is genuinely better off, which is 0016's compounding-returns argument extended
through time rather than a new claim.

## Consequences

**Buys:**

- **It removes an irreversible penalty from a system built on recoverable ones.** Every
  other cost in [ADR 0013](0013-action-economy.md) is a delay. This one would have been
  a permanently closed door, and closed by imperfect prophecy rather than bad judgement.
- **It makes [ADR 0014](0014-staff-is-the-information-channel.md) checkable against its
  own claim.** "Money spent on scouts buys resolution" stops being doctrine and becomes
  something the club can be *wrong* about and find out — but only if the reads were kept
  at the time. Retention is the precondition for the front office grading itself.
- **It keeps the price where the work is.** Not deleting rows is not work. Building an
  ingestion path is. Producing an analysis is. The tiers track effort rather than intuition.
- **It gives snapshot history a third named use.** Citation integrity and the
  pre/post-action diff were the first two; grading a forecaster against outcomes is the
  third, and it was not foreseen when the grain was chosen.

**Costs:**

- **The warehouse grows monotonically, and nothing here bounds it.** Append-only with no
  prune means storage rises with every sim date, forever. No retention policy is set by
  this decision, and one will eventually be needed — at which point *deleting* history
  becomes a decision with the same irreversibility this ADR was written to avoid.
- **It hands the GM a capability no real front office gets for free.** A perfect,
  costless memory of every read ever taken is not what an actual organization has —
  the operator's own workplace is the counterexample. This decision accepts that
  unrealism deliberately, because the alternative punishes foresight rather than judgement.
- **The tier-2 boundary will be argued.** "We're already reading the file, so this field
  is free" is exactly the shape of a plausible-sounding widening, and it has to be
  refused in review every time.
- **It is prose, not prevention** — the same weakness as 0016, 0014 and 0009. Nothing in
  the harness distinguishes retaining from widening. It holds because it is written down.

**Forecloses:**

- Charging the GM an action to keep data the pipeline already produces.
- Pruning or overwriting a landed snapshot as a routine matter, rather than as a decision.
- Landing a field speculatively on the grounds that retention is free — the field itself
  is not.
- Answering an analytical question over retained history for free because "the data was
  already there." The data being there is exactly what this ADR made free; the question
  is still 0016's.

## Notes

**This clarifies [ADR 0016](0016-gm-reads-reports-not-queries.md) rather than superseding
it.** 0016's decision stands unchanged; this says which side of its press/article line
retention falls on, and why the usual cost reasoning does not transfer.

`unconfirmed`, and worth settling before the warehouse is large: what the actual growth
rate is per sim date, and therefore when a retention policy stops being theoretical. The
first landed snapshot makes it measurable.
