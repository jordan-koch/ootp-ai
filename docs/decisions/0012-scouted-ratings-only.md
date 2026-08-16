# 0012 — The GM sees scouted ratings, never true ratings

**Status:** Accepted
**Date:** 2026-08-15

## Context

[ADR 0007](0007-advisory-front-office.md) left this open, and
[ADR 0010](0010-main-thread-is-the-gm.md) made it urgent. While advisors merely *advised a
human*, feeding them true ratings could be rationalized as giving a person a better tool. Now
the main thread **is** the decision-maker, and the question is no longer ergonomic.

OOTP stores at least two views of a player's ability
([`data-access.md` §5](../data-access.md)):

- **True ratings** — what the player actually is.
- **Scouted ratings** — what this organization's scouts believe, filtered through scouting
  accuracy, with a separate ~2.3 MB `scouting.dat` and an OSA-vs-Head-Scout toggle in the UI.

A real front office only ever has the second. Scouting accuracy is a staff attribute the
organization invests in.

## Decision

**The GM and every advisor see only what the organization can actually see in-game: scouted
ratings, at the scale the game displays them.**

True ratings are out of bounds even where the parser can reach them. If a field turns out to
hold true values, it is parsed, labelled, and **withheld from the advisory layer** — not
surfaced because it happens to be available.

## Consequences

**Buys:**

- **The competitiveness claim survives.** A GM reasoning from true ratings is not competing;
  it is reading the answer key, and any resulting record would prove nothing. This is the
  whole point.
- **Scouting becomes a real subsystem with real stakes.** Hiring a better scouting director,
  and measuring whether he was worth it, only means something if scouting is the sole channel
  to player ability. Combined with [ADR 0013](0013-action-economy.md), scout quality becomes
  measurable: actions spent, outcomes returned.
- **Uncertainty is modelled rather than assumed away.** The interesting front-office
  decisions — pay for the tools or the performance, trust the org's read against the market's
  — only exist under imperfect information.
- It matches how the operator experiences the game, so GM and operator reason about the same
  player.

**Costs:**

- **The GM will be wrong about players, sometimes badly, and that is working as intended.**
  A bust is not necessarily a bug, which makes debugging genuinely harder: a bad outcome
  might be a parser fault, a bad decision, or an accurate scouting miss. Data incidents in
  this area need care ([`requests/data-incidents/`](../../requests/data-incidents/README.md)).
- Some analysis is simply unavailable. "Which of our prospects is actually best" has no
  answer here, only a belief.
- The parser still has to identify true-rating fields precisely enough to *exclude* them,
  which is more work than ignoring them would be. A field we cannot classify must be treated
  as true-rating and withheld.

**Forecloses:**

- Any "just for calibration" exception. A true-rating peek that informs a decision has
  contaminated the experiment, and there is no way to un-know it. If true ratings are ever
  needed to validate the parser, that work happens in tests against fixtures — never in the
  advisory path.

## Notes

`docs/data-access.md` §5 records that **we do not yet know which file holds which**. Until
that is `verified`, the safe default is that anything the parser surfaces may be true
ratings, and the advisory layer should consume ratings only through the scouted-view path
once one exists.

The corollary for the parser: an unclassified rating field is not "probably fine." Under this
ADR it is withheld until classified.
