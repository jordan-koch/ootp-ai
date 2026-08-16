# Staff

The front office roster, and how each member has performed against the actions spent on them.

> **Status: no staff engaged.** The club exists (Boston Red Sox, `OOTP-AI`, from
> 2024-03-07) and carries inherited staff, but none has been engaged and no
> analytics capability exists yet
> ([ADR 0016](../docs/decisions/0016-gm-reads-reports-not-queries.md)).

## Why this file can exist at all

Under [ADR 0013](../docs/decisions/0013-action-economy.md) actions are scarce, and scarcity
creates the denominator. Twelve actions spent on the draft and three busted picks is a
**return on invested attention**. Without scarcity, "should I fire the scouting director" has
no evidence behind it — a bad report just gets re-run for free.

Combined with [ADR 0012](../docs/decisions/0012-scouted-ratings-only.md), where scouting is
the *only* channel to player ability, scout quality stops being a number on a staff card and
becomes something the GM can actually audit.

## Format

One section per staff member.

```markdown
### <role> — <name>

- **Hired:** sim date, and the ledger seq of the decision
- **Ratings:** what the game says about them (scouted, like everything else)
- **Actions spent:** running count, by period
- **Record:** what the work produced, and whether it held up
- **Assessment:** the GM's current read, dated
```

## The attribution problem — read before judging anyone

**A bad outcome does not prove bad staff work**, and this is the hardest evaluation problem
in the project. A busted pick can be:

- an accurate scouting read on a player who got hurt or stalled,
- a good read the GM overruled,
- a genuinely bad read,
- or a parser fault feeding everyone wrong numbers
  ([`requests/data-incidents/`](../requests/data-incidents/README.md)).

Under scouted-ratings-only, being wrong about players is *working as intended* some of the
time. So:

- **Judge process against sample, never a single outcome.** One bust is noise.
- **Record the read at the time**, in the decision record, so a later assessment compares
  against what was actually said rather than against memory.
- **Rule out the parser first.** A staff member cannot be blamed for numbers that were wrong
  before they saw them.
