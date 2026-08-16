> **Status:** intake · created 2026-08-16 · open · next: scope

# Feature Request — Give the news subscription dial a state, a price in practice, and a way to be told no

## Problem / Motivation

**[ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md) priced a lever that
has no state, no inventory, and no mechanism.** The ruling landed today; the machinery it
assumes does not exist.

`measured` 2026-08-16, observed in-game by the operator: OOTP offers **12 subscription
categories** — general league news, contract news and injury news among them — and a
volume setting running from *"No news, only personal messages"* up to *"News from the
entire world,"* with scopings to your league or your club between. Three concrete gaps
follow, and none is about parsing:

**Nothing records what the club is subscribed to.** `OOTP-AI` is on the default, which is
a fact currently written down in exactly one place: `docs/game-mechanics.md`, in prose,
as an aside. The GM reads `gm/` to learn its own situation, and its own information
posture is not there. A front office that cannot say what it subscribes to cannot reason
about whether to change it.

**Nine of the twelve categories have never been named.** Any argument about coverage —
what the club would gain by widening, what it is blind to now — is currently an argument
about a list nobody has written down.

**The ledger cannot record a refusal.** `gm/ledger.jsonl`'s schema carries
`proposed`/`ruling` with values like `free` and `cost`, which express *how much* a thing
costs. There is no value expressing **"no, you may not have this at all."** ADR 0019
requires that a declined proposal return to the GM with its reason, and the artifact that
would carry it has no vocabulary for it. Without that, the GM re-proposes next period and
spends its own attention relearning a decision already made — the exact failure
[ADR 0011](../../../docs/decisions/0011-gm-memory-is-tracked.md) exists to prevent, since
the save records what happened and never why.

**Be honest about the shape of this request:** its engineering surface is small — tracked
text files and a schema field. Its *decision* surface is not, because it touches the
action economy, the ledger's contract, and what the GM is permitted to ask for.

## Desired Outcome

The dial has a **known state**, a **complete inventory**, and a **working refusal path**.

Concretely, three things are true when this is done:

**The GM can find out what it currently receives** by reading `gm/`, without asking the
operator and without an action, the same way it reads its standing orders.

**A proposal to change the dial has somewhere to land.** The GM proposes; the umpires
rule; the ruling is recorded whichever way it goes, including *no*.

**A refusal teaches the boundary.** The observable signal: the GM is declined once, and in
a later period proposes something different rather than the same thing again — and a cold
spawn can see why, because the reason is in `gm/` rather than in a conversation that
ended.

## Rough Ideas (non-binding)

- Subscription state as a section in
  [`gm/standing-orders.md`](../../../gm/standing-orders.md) rather than a new file — it is
  a policy set once and applied until changed, which is what that document is for.
- A `refused` value in the ledger's `ruling` field, with the existing `reasoning` field
  carrying the why. The schema already has the slot; it is the vocabulary that is missing.
- The twelve categories enumerated into
  [`docs/game-mechanics.md`](../../../docs/game-mechanics.md) as a table, `measured`, from
  the operator reading the screen.

Scoping is free to reject all of this. In particular, "a section in standing orders" may
be wrong if subscription state turns out to be something the GM should not be able to set
unilaterally.

## Scope Signals

- **In:** enumerating the 12 categories; recording current subscription state somewhere
  the GM reads; extending the ledger's ruling vocabulary to express refusal; documenting
  who may propose a dial change and how it is executed.
- **Explicitly out:** parsing, rendering or landing any news content — that is a separate
  request that does not exist yet, and this one deliberately does not create it.
  Re-pricing anything [ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md)
  settled. The personal-message channel, which is
  `requests/feature-requests/gm-inbox/`. Any change to the action budget itself
  ([ADR 0013](../../../docs/decisions/0013-action-economy.md)).
- **Not now / later:** actually turning the dial up. Nothing should widen the subscription
  until there is somewhere for the content to go, and until Open Question 2 is answered —
  raising it may be irreversible.

## Affected Area & Pointers

**Governance and tracked GM memory, not the pipeline.** No file under `src/ootp_ai/` is
expected to change.

A cold scoping agent reads, in order:

1. [`docs/decisions/0019-reading-costs-an-action.md`](../../../docs/decisions/0019-reading-costs-an-action.md)
   — the ruling this implements. Its *refusal loop* section is the spec.
2. [`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md) §*The action economy* — `:53-54` already
   establishes standing orders as the set-once lever, and `:55-57` the declare-before-doing
   protocol this must fit inside
3. [`gm/ledger.jsonl`](../../../gm/ledger.jsonl) — the live schema, one row. Note `ruling`,
   `overridden` and `overturns` already exist
4. [`gm/README.md`](../../../gm/README.md) — owns the ledger's schema and which files
   survive a rebuild
5. [`gm/standing-orders.md`](../../../gm/standing-orders.md) — the candidate home for
   subscription state
6. [`docs/game-mechanics.md`](../../../docs/game-mechanics.md) §*Mail, and the volume dial
   nobody has turned* — everything currently known about the dial
7. [`docs/decisions/0017-gm-is-a-subagent.md`](../../../docs/decisions/0017-gm-is-a-subagent.md)
   — why the GM proposing rather than executing is enforced rather than requested

## Constraints / Non-negotiables

- **The GM proposes; it cannot execute**
  ([ADR 0017](../../../docs/decisions/0017-gm-is-a-subagent.md)). It holds `Read` and
  `Glob`. Whatever this builds, the GM's half of it is a proposal in a handoff, and the
  operator's half is pressing the button in-game.
- **A refusal must cost the GM nothing**
  ([ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md)). If declined
  proposals consumed actions, the GM would learn to propose only what it expected to be
  approved — and the umpires would stop hearing what it actually wants, which is the most
  useful signal this experiment produces.
- **`gm/` is tracked and world-readable**
  ([ADR 0011](../../../docs/decisions/0011-gm-memory-is-tracked.md),
  [ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md)). Subscription state
  is ours and is trackable; no message or article text may land beside it.
- **The ledger is append-only.** A refusal is a new row, never an edit to an old one.
- **`docs/game-mechanics.md` enforces a stricter labelling rule than the other docs** —
  model-recalled mechanics may never rank above `assumed`. The twelve categories must be
  enumerated by someone reading the screen, not recalled.

## Open Questions for Scoping

1. **What are the other nine categories?** Three are known: general league news, contract
   news, injury news. This cannot be answered from the repo — it needs the operator in the
   settings screen. `unconfirmed`.
2. **Does raising the volume backfill history, or only change what arrives from that point
   on?** This decides whether the dial is **reversible**, and therefore whether subscribing
   early is itself a strategy the GM should be reasoning about. If it does not backfill,
   the decision has the same irreversibility that
   [ADR 0018](../../../docs/decisions/0018-retention-is-infrastructure.md) was written to
   handle, and the foresight-trap argument applies. `unconfirmed`.
3. **Where does subscription state live, and who owns it?** Standing orders implies the GM
   sets it. A separate umpire-owned file implies it is done *to* the club. ADR 0019 says
   subscribing is free, which argues the GM may propose freely — but free is not the same
   as unilateral, and the GM cannot press the button regardless.
4. **Does raising the dial change what lands in `messages/`?** If feed content starts
   arriving in the folder the operator ruled free to read, the free ruling silently becomes
   a free firehose. This is a **hard dependency** with
   `requests/feature-requests/gm-inbox/` Open Question 3, and neither request can settle it
   alone. `unconfirmed`.
5. **Is a refusal a ledger row, a `gm/decisions/` record, or both?** The ledger is
   adjudications; `gm/decisions/` is the GM's own reasoning. A refusal is an umpire act
   about a GM proposal and sits awkwardly between them.
6. **What happens to a refusal when the answer would change later?** *"No, not yet"* and
   *"no, never"* are different, and a GM that treats the first as the second stops asking
   for things it should eventually get.

## Stage plan

**Full pipeline.** Two triggers fire.

**Trigger 1** — Open Questions is non-empty, and two of them (1 and 2) cannot be answered
from the repo at all; they need the operator in-game.

**Trigger 3** — it changes the schema of
[`gm/ledger.jsonl`](../../../gm/ledger.jsonl), which is append-only and which
[ADR 0011](../../../docs/decisions/0011-gm-memory-is-tracked.md) makes the one piece of
state in this project with no other copy. It also implements a section of an ADR accepted
the same day, and Open Question 4 can put pressure back on
[ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md)'s free ruling for
personal mail.

**Worth flagging to whoever scopes this:** the engineering here is small enough that the
panel may feel heavy for it. That is the correct outcome anyway — the cost of this request
is concentrated in decisions about the action economy and the ledger contract, which is
exactly what the panel is for, and is not reduced by the diff being short.
