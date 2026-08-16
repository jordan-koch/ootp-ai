# 0019 — Reading costs an action; a report is built once and read for free

**Status:** Accepted
**Date:** 2026-08-16

## Context

The GM receives mail in-game, and the mail turned out to be a **dial** rather than a
feed. `measured` 2026-08-16, observed by the operator: OOTP offers **12 subscription
categories** — general league news, contract news, injury news among them — and a volume
setting running from *"No news, only personal messages"* (the default, and what
`OOTP-AI` is on) up to *"News from the entire world,"* with scopings to your league or
your club in between. Mechanic recorded in
[`docs/game-mechanics.md`](../game-mechanics.md).

That created a problem the existing decisions did not price.

**Every other information lever in this project is bought.**
[ADR 0014](0014-staff-is-the-information-channel.md) says a clearer picture is bought by
hiring, never by code. [ADR 0013](0013-action-economy.md) prices depth on one player at
an action plus two weeks. **The subscription dial is neither.** It is a settings toggle
— once, free — that scales the front office's incoming information from near-silence to
the entire world. Left unpriced it is the largest free advantage in the game, and it
arrives without anyone deciding anything.

The obvious fix is to charge for reading. The obvious fix has an obvious hole: if staff
can build a report over the feed and the GM reads reports for free
([ADR 0016](0016-gm-reads-reports-not-queries.md)), then one commissioned "world news
digest" launders the firehose into permanent free access, and the price collapses.

## Decision

> **The pipe is free. Drinking from it costs an action. Staff can build a tap that is
> free to read forever — and a tap may only draw from the warehouse, never from the
> feed.**

| Step | Cost |
|---|---|
| Subscribing — turning the dial up, at any breadth or scope | **Free** |
| Reading the raw feed | **One action, each time** |
| Commissioning a report | Costs actions to build |
| Reading an existing report | **Free, thereafter** |
| Changing an existing report | **An action.** A change, not a reference. |

### The anti-laundering rule, and the test that makes it operable

**A report is sourced from the warehouse. Never from the feed.** The test is
counterfactual and it is cheap to apply:

> **Could staff build this report if the news feed were switched off entirely?**

Yes → it is infrastructure, and it is legitimate. No → it is laundering the feed, and it
is refused.

An injury report passes: the club observes its own players' health from its own data
whether or not anyone publishes an article. A "this week's league news digest" fails —
switch the feed off and there is nothing left to build from.

Note what the test does **not** do. It does not care whether a report and the feed
happen to tell the GM the same thing. Two channels converging on one fact is
convergence, not laundering; laundering is *reading the articles and republishing them*.

### Three limiters, and they are not the same limiter

The scope of a report is bounded three separate times, and conflating them produces bad
reasoning about all three:

| Limiter | Answers | Enforced by |
|---|---|---|
| **Umpire ruling** | *May* this report exist at all? | The tool grant. The `gm` agent holds `Read` and `Glob`; it cannot spawn, cannot query, cannot build. It proposes and the umpires dispose ([ADR 0017](0017-gm-is-a-subagent.md)). |
| **Action economy** | What gets built **first**? | The ledger ([ADR 0013](0013-action-economy.md)) |
| **Staff quality** | What **can** be built at all? | [ADR 0014](0014-staff-is-the-information-channel.md) |

A GM asking for one enormous report covering the whole warehouse fails at the **first**
gate and never reaches the other two. That gate is structural rather than economic,
which is the point of 0017: constraints enforced by discipline are not constraints.

### The refusal loop

**A declined proposal returns to the GM with its reason, recorded.** Without it the GM
re-proposes next period and burns its own actions relearning a decision that was already
made — and the refusal has no other copy, because the save records what happened and
never why ([ADR 0011](0011-gm-memory-is-tracked.md)).

Three properties this needs, none of them expensive:

- **The reason travels with the refusal.** *"No"* teaches nothing; *"no, because it
  would be sourced from the feed"* teaches the rule. A GM that learns the boundary stops
  proposing across it.
- **A refusal costs the GM nothing.** Proposing is not spending. If a declined proposal
  consumed an action, the GM would learn to propose only what it expected to be
  approved, and the umpires would stop hearing what it actually wants — which is the
  most useful signal the experiment produces.
- **It is durable, not conversational.** It lives in `gm/` with the rest of the club's
  memory, where a cold session finds it. A refusal remembered only in a session that has
  since ended is a refusal that will be re-proposed.

**The mechanism is deliberately not specified here.** Whether this is a ledger column, a
`gm/decisions/` record or a standing-orders line is an implementation question that the
mail feature request settles. This ADR fixes only that the loop must close.

### The dynamic this produces, which is the point

Infrastructure can replace the feed for anything **the club can observe itself.** It can
never replace it for anything **only the world knows** — rumours, other clubs'
intentions, commentary, what the writers think of you.

So the feed does not decay into something a GM buys his way out of. It keeps permanent,
irreducible value for exactly the information that has no warehouse column, and the
tension runs in both directions:

- **Pay per read** — cheap now, expensive forever, works on day one, and is the *only*
  route to world-knowledge.
- **Build infrastructure** — expensive now, free forever, shaped to your needs, and only
  ever covers what the club can observe.

That is a real buy-versus-build decision with no dominant strategy, which is what this
project wants the GM to have to make.

## Consequences

**Buys:**

- **It closes the hole it was written for without amending
  [ADR 0014](0014-staff-is-the-information-channel.md).** A wide subscription with no
  staff is worse than useless — a firehose that costs an action every time you drink.
  The only way to convert breadth into something consumable is to have someone build the
  tap. Staff remains the information channel, now for a second and independent reason:
  not just *resolution* on a player, but *legibility* of a feed.
- **It generalises [ADR 0018](0018-retention-is-infrastructure.md) rather than sitting
  beside it.** Two independent rulings — retention, and now mail — landed on the same
  shape: the pipe is free, drinking costs an action, a commissioned tap is free
  thereafter. This ADR states the principle those two are instances of, so the third
  channel does not need a third ruling.
- **It prices the dial without banning it.** The GM may subscribe to the entire world on
  day one. It will simply find that it cannot afford to read it, which is a lesson rather
  than a rule.
- **The mutation clause stops "free forever" from meaning "free to evolve forever."**
  Reading your dashboard and asking your analyst to rebuild it are different asks, and
  the second is where the work is.

**Costs:**

- **The counterfactual test is a judgement, and it will be argued.** *"This report is
  about injuries, and injuries are in the warehouse"* is true of a report that in fact
  summarises injury articles. Someone has to actually ask whether it survives the feed
  being switched off, every time.
- **It prices a channel nobody has read yet.** No mail has been ingested; the 8,056
  bytes on disk are the floor of a dial nobody has turned. The pricing is therefore
  `inferred` from the mechanic rather than from experience with its volume, and the
  first real subscription may show that one-action-per-read is far too coarse a unit for
  something that arrives weekly.
- **It adds a bookkeeping obligation.** The refusal loop is a thing that must be
  maintained, and an unmaintained one is worse than none — a GM told "no" once and never
  reminded will re-propose exactly as if the loop did not exist.
- **It is prose, not prevention**, on the laundering rule specifically. The tool grant
  genuinely prevents the GM from building anything; nothing prevents an *umpire* from
  approving a report sourced from the feed. It holds because it is written down.

**Forecloses:**

- A report sourced from the news feed, at any breadth, for any reason.
- Charging the GM for turning the subscription dial, or capping which categories it may
  subscribe to.
- Treating an amendment to an existing report as a free reference.
- Declining a GM proposal without returning the reason to it.
- Charging the GM an action for making a proposal that is then refused.

## Notes

**This extends [ADR 0016](0016-gm-reads-reports-not-queries.md) and generalises
[ADR 0018](0018-retention-is-infrastructure.md); it supersedes neither.** 0016 settled
that the GM reads reports rather than querying; 0018 priced retention; this prices an
inbound channel that is neither, and states the rule all three share.

`unconfirmed` — the remaining nine subscription categories have not been enumerated, and
should be before anyone reasons about coverage.

`unconfirmed` — whether raising the volume setting backfills history or only changes what
arrives from that point on. The difference decides whether the dial is reversible, and
therefore whether subscribing early is itself a strategy.

**Open, and left to the mail feature request:** whether a commissioned report is
*standing* (regenerating each period, free to read forever) or a *snapshot* of one
moment. A standing report is closer to how a real front office works — you pay a person
once and get a briefing every Monday — but it means the commissioning decision is the
expensive one and everything after it is cheap, which should be stated rather than
discovered when the GM holds twelve standing reports and no actions.
