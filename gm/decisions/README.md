# Decisions

One file per significant decision. Named `YYYY-MM-DD-<slug>.md` using the **sim date**, not
the wall-clock date — the GM's history is in league time.

> **Club:** Boston Red Sox, league `OOTP-AI`, first sim date 2024-03-07.

## What gets a record

Calls worth revisiting: acquisitions and trades, extensions and non-tenders, promotions and
demotions, staff hires and firings, changes of direction, and any deliberate departure from
the [charter](../charter.md).

Not every action needs one. A scouting sweep that found nothing interesting is a ledger entry,
not a decision record.

## Format

```markdown
# <what was decided>

- **Sim date:** YYYY-MM-DD
- **Ledger:** seq <n> (the action(s) this rests on)
- **Staff input:** who said what — including who disagreed

## Decision
What we are doing.

## Why
The reasoning, against the charter's window and principles.

## What I expect
The observable outcome, stated concretely enough to be wrong.

## What would make this a mistake
The signal that would mean this was the wrong call.

## Outcome
_Added later._ What actually happened, and what it says about the reasoning.
```

## The two sections that carry the weight

**"What I expect"** must be concrete enough to be *wrong*. "He'll help the rotation" cannot
be evaluated. "He's a 3-WAR arm over the next two seasons, and we're buying the 2027–28
window, not 2025" can be.

**"Staff input", including the dissent.** Advisors disagree in public
([ADR 0010](../../docs/decisions/0010-main-thread-is-the-gm.md)), and recording only the advice
that was taken destroys the record's value — you lose the ability to ask, later, whether the
advisor who objected was right. That is how staff evaluation gets its evidence.

**Outcome is appended, never rewritten.** A decision that looks bad later stays as written. A
GM that quietly edits its own reasoning after the result is in has stopped keeping a record.
