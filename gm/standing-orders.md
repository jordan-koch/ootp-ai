# Standing orders

Policies the staff apply **for free, every game, until changed**. Establishing or changing one
costs an action ([ADR 0013](../docs/decisions/0013-action-economy.md)); applying one costs
nothing.

This is the mechanic that makes the action economy livable. A GM defers to a coach, and spends
scarce attention on *changing* things rather than maintaining them.

> **Status: none active.** The club exists (Boston Red Sox, `OOTP-AI`, from
> 2024-03-07) but nothing has been established yet.

## Format

One section per order.

```markdown
### <name>

- **Established:** ledger seq <n>, sim date YYYY-MM-DD
- **Owner:** which staff member applies it
- **Policy:** what they do, specifically enough to be applied without asking
- **Rationale:** why — so a later GM can tell whether the reason still holds
- **Review trigger:** the observation that should prompt revisiting it
```

## Reports

**A report is a standing order for information**, and it lives here for that
reason rather than in a second registry
([ADR 0016](../docs/decisions/0016-gm-reads-reports-not-queries.md)).

The GM never queries the warehouse. Analysis reaches it as named, refreshable
reports owned by a staff member. **Commissioning one costs an action; refreshing
it, reading it and reasoning over it are free forever** — the same shape as any
other standing order, and the reason report design is a real skill rather than a
tax.

Same format as above, with `Policy` describing what the report contains
specifically enough to be regenerated without asking:

```markdown
### <report name>

- **Established:** ledger seq <n>, sim date YYYY-MM-DD
- **Owner:** the analyst who produces and refreshes it
- **Policy:** what it contains, its grain, and what question it answers
- **Rationale:** the decision it was built to support
- **Review trigger:** the observation that should prompt revisiting it
```

The failure mode is the same one and it is worse here, because a wrong report is
harder to notice than a wrong policy: **it keeps refreshing for free, in the
correct format, with stale meaning.** The `Review trigger` is what catches it.

## Why `Established` and `Review trigger` are not optional

**A standing order that quietly stopped being right is this system's most interesting failure
mode.** The platoon policy set in April is wrong by July; nobody notices, because noticing
costs an action the GM would rather spend elsewhere, and the order keeps being applied for
free the whole time.

The sim date makes age visible at a glance. The review trigger is a pre-registered condition
that turns "should I revisit this?" from an open-ended worry into a check — which is far
cheaper to run and much harder to talk yourself out of.
