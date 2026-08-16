# Standing orders

Policies the staff apply **for free, every game, until changed**. Establishing or changing one
costs an action ([ADR 0013](../docs/decisions/0013-action-economy.md)); applying one costs
nothing.

This is the mechanic that makes the action economy livable. A GM defers to a coach, and spends
scarce attention on *changing* things rather than maintaining them.

> **Status: none active.** No league exists yet.

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

## Why `Established` and `Review trigger` are not optional

**A standing order that quietly stopped being right is this system's most interesting failure
mode.** The platoon policy set in April is wrong by July; nobody notices, because noticing
costs an action the GM would rather spend elsewhere, and the order keeps being applied for
free the whole time.

The sim date makes age visible at a glance. The review trigger is a pre-registered condition
that turns "should I revisit this?" from an open-ended worry into a check — which is far
cheaper to run and much harder to talk yourself out of.
