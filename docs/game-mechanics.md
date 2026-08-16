# Game Mechanics

How Out of the Park Baseball 25 actually behaves — the operational knowledge a real
general manager would have on his first day and never think about again.

The three documents split like this:

| Document | Answers | Varies with |
|---|---|---|
| [`data-access.md`](data-access.md) | What can be **read**, and how much we know about it | our pipeline |
| [`league-rules.md`](league-rules.md) | What can be **done** in this league | this league's configuration |
| **this document** | **How the engine behaves** when you do it | OOTP itself — the same for every league |

The distinction matters in practice. *"The trade deadline is 31 July"* is league
configuration and belongs next door. *"A trade offer sits with the other club and
resolves over several days"* is engine behaviour and belongs here. A different league
could move the deadline; no league setting makes offers resolve instantly.

Everything here is **free to the GM.** It is not analysis of our data and costs no
action under [ADR 0016](decisions/0016-gm-reads-reports-not-queries.md) — a general
manager does not spend a decision learning that scouting reports refresh in spring
training, any more than he spends one learning that the deadline exists. It is
competence at the job, not a finding about our club.

---

## Why this document exists, and why it is thin

It was created 2026-08-16, after the operator observed a scouting mechanic in-game and
this project immediately generalised it into a rule that was wrong within the hour.
The error was not carelessness. It was that **the front office knew the league's rules
and had the game's data, and did not know how to play the game** — and nothing in the
repo held that knowledge, so nobody noticed it was missing.

Expect this document to stay incomplete for a long time. That is authentic rather than
a defect: the operator is learning the game's mechanics alongside the front office,
which is a fair simulation of a general manager eleven days into a new job. **The GM's
operational competence is bounded by what is written here**, and that bound is real —
it should be felt, not papered over with recalled generalities.

## The labelling rule — stricter here than elsewhere

Every claim carries one of the repo's five labels (`measured`, `verified`, `inferred`,
`assumed`, `unconfirmed` — see [`data-access.md`](data-access.md)) **and a provenance
note**, because on this subject confidence and origin come apart in a way they do not
elsewhere:

| Provenance | Highest label it may carry |
|---|---|
| **Observed in our game**, reproducibly | `measured` — `verified` if cross-checked against a second, independent observation |
| **A third-party source** — a manual, a wiki, a forum | `unconfirmed` until someone observes it. Cite what said it. |
| **Model recall alone** | **`assumed`, never higher, and it must say so.** |

That last row is the load-bearing one. An agent's recollection of OOTP is
version-specific, thick with forum folklore, and easy to blur with real baseball. A
doc that fills up with confident-sounding recalled mechanics is **worse than no doc**,
because it would be trusted at exactly the moments this project is most exposed —
which is the same failure the parser's epistemic discipline exists to prevent, moved
one layer up.

Note this hazard is *different* from the one in
[`CLAUDE.md`](../CLAUDE.md)'s *"This is not the 2024 season"*. That rule is about
recalled knowledge of **people** — a player's real career describes a different person
in a diverged universe. Engine mechanics are not about people at all, so they do not
carry that hazard. They carry this one instead.

**Version:** everything below describes **OOTP 25** unless stated. Mechanics change
between releases; an entry carried forward to OOTP 26 is `unconfirmed` again.

---

## Scouting

### There are two channels, and they answer different questions

**Passive refresh.** `unconfirmed` — third-party source, not yet observed here.
Internal scouting reports update at **milestones**: spring training, opening day, the
offseason and similar. This is the channel that produces coverage across the whole
population. **The scouting budget raises both its accuracy and its frequency.**

**Manual request.** `measured` — observed in-game by the operator, 2026-08-16. Request
a scouting report on **one named player**; it returns after roughly **two weeks** of
game time, and requests appear to run **one at a time** rather than in parallel.

They are not substitutes. Budget buys the picture; a request buys a close look at one
name already in it. Conflating them is exactly the error that created this document.

### What a scouting report carries

`measured` — from the player Scouting tab, cross-checked against the ground-truth
export: a report is attributed to a **named scout**, carries a **report date**, and an
**accuracy grade** (`High`, `Avg`, …) which appears in the export as an integer 1–5.
Players accumulate a **history** of past reports rather than a single current one.

### Two views exist, and they are different products

`verified` — the game exposes an **OSA** view and the club's own **Head Scout** view
as a toggle on the player page, and they genuinely disagree.

`measured` — OSA is a public service: every club sees the same numbers, its accuracy
grade is a flat `3` for every player, and it **regenerates once per year**. The club's
own view updates continuously through the two channels above.

The consequence is the mechanic
[ADR 0014](decisions/0014-staff-is-the-information-channel.md) rests on: OSA sells
*breadth* it cannot afford to make accurate, and the club sells *depth* it can only
afford in a few places. **Neither is "the truth", and they can agree while both being
wrong.** Which to trust on a given player is a judgement, not a calculation — see
`requests/feature-requests/first-sight/reviews/scouted-view-followup.md`.

### Open — each changes how large the lever is

- **How steeply does budget scale accuracy versus frequency?** The source says both;
  nothing has measured it. `unconfirmed`
- **Is the two-week request turnaround fixed, or a function of the scouting
  director's ability?** If it scales with staff, staff quality buys *throughput* as
  well as resolution — a second information lever ADR 0014 does not name.
  `unconfirmed`
- **Do more scouts allow requests to run in parallel?** If so, headcount and director
  quality are materially different purchases. `unconfirmed`
- **What produced the accuracy distribution we observe at league creation?** Own
  organisation never below 3, other MLB clubs flat at 2, 266 players elsewhere at
  level 4. It cannot be manual requests — the league is eleven days old — so it is
  either seeded at creation or the passive channel working. `unconfirmed`

---

## Mail, and the volume dial nobody has turned

The game delivers mail to the general manager. `measured` — observed in-game by the
operator, 2026-08-16, and cross-checked against the save on disk.

**It is a subscription, not a feed.** There are **12 subscription categories** covering
different subjects — general league news, contract news and injury news among them; the
remaining nine have not been enumerated here and should be, before anyone reasons about
coverage.

**Volume is a setting with a wide range.** It runs from **"No news, only personal
messages"** — which is the **default**, and is what this league is on — up to **"News
from the entire world."** Between those sit granular restrictions: your league, your
team, and similar scopings.

### Why that default matters more than it looks

What sits in the save today is therefore the **floor, not the ceiling**. `measured` —
at the default setting `OOTP-AI.lg/messages/` holds **8 plain-text files totalling
8,056 bytes**, plus a 1,129-byte `messages.dat` index carrying the standard save header.
Even at the floor, one of those eight is a ranked league-wide prospect list.

`unconfirmed` — whether raising the setting backfills history or only changes what
arrives from that point on. The difference decides whether the dial is reversible.

### The mechanic this exposes, stated but not settled here

Every other information lever in this project is bought. Staff quality is bought by
hiring ([ADR 0014](decisions/0014-staff-is-the-information-channel.md)); depth on one
player is bought with an action and two weeks
([ADR 0013](decisions/0013-action-economy.md)). **This one is bought with a settings
toggle, once, for free** — and it scales from near-silence to the whole world.

That is a genuine asymmetry and it is a *decision*, not a mechanic, so it is not
settled here. It belongs to whoever files the mail request. Three things it has to
answer, none of which this document may answer for it:

- **Who owns the dial** — the GM, or the umpires?
- **Does reading mail cost an action?** Mail arrives unbidden and a real general
  manager reads his own inbox, which argues free. A ranked prospect list arriving
  weekly for nothing argues otherwise.
- **Is the setting itself a one-time choice or a standing one?** A dial that can be
  turned up the week it becomes useful is a different instrument from one set at hire.

`inferred` — reading cost is likely to bind on **volume** rather than on access. At the
floor it is eight short letters; at "the entire world" it is a firehose that no context
window reads in full, which turns "read the mail" into a summarisation problem and a
selection problem at the same time.

---

## Actions that resolve later

`inferred` — from the manual scouting request, and expected to generalise.

A manual scouting request costs its action **immediately** and returns information
**two weeks later**. The same shape appears to recur across the game's other levers:
trade offers sit with the other club, contract negotiations run over days, hires take
effect on a cycle.

This is engine behaviour, so it lives here. What it *implies* for how this front
office should play — that latency is a second currency, that the GM must form a thesis
before he needs it, that an early cheap read can beat a late deep one — is a strategic
consequence and lives in [`league-rules.md`](league-rules.md) §3.

**Unverified for anything except scouting.** The generalisation is plausible and
unobserved; each lever needs its own entry before anyone relies on it.

---

## How this document grows

Add an entry when a mechanic is **observed**, or when a source claims one and the
claim would change a decision. Carry the provenance note. Do not add an entry because
it sounds right.

When an `unconfirmed` third-party claim is later observed in-game, upgrade the label
and say who observed it — the same discipline
[`data-access.md`](data-access.md) applies to the save format, for the same reason.
