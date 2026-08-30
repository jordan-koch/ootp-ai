# Standing orders

Policies the staff apply **for free, every game, until changed**. Establishing or changing one
costs an action ([ADR 0013](../docs/decisions/0013-action-economy.md)); applying one costs
nothing.

This is the mechanic that makes the action economy livable. A GM defers to a coach, and spends
scarce attention on *changing* things rather than maintaining them.

> **Status: no policies; two reports active.** The club exists (Boston Red Sox,
> `OOTP-AI`, from 2024-03-07). No standing **policy** has been established — that takes a
> GM decision and an action, and none has been spent. What now exists is the **report
> channel**: the two engineering-owned reports below, which are infrastructure rather than
> commissioned analysis.

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

### Engineering-owned reports — a second kind, with no analyst behind it

[`staff.md`](staff.md) records that **no staff have been engaged.** So an `Owner:` line
naming an analyst on either report below would be fiction — and fiction in precisely the
field the GM uses to decide whose read to trust. A report the pipeline generates from the
save has no analyst behind it and must not borrow one.

Hence a second kind. It differs in three places and nowhere else:

- **`Owner:` is `engineering`**, not a person. Nobody answers for its *judgment*, because
  it exercises none: it renders landed columns and states which it withheld.
- **`Established:` names the phase that built it**, where an analyst report names a ledger
  seq. Commissioning a report costs an action; building one did not. Both entries below
  read `engineering-owned, no ledger seq` **deliberately** — the umpires' ledger row
  recording this channel as free infrastructure is a later act, and writing a seq before it
  exists would be inventing a decision that nobody made.
- **Refreshing is a command, not a request**, and the `Policy` line names it.

Everything else holds, and the `Review trigger` holds hardest: a pipeline report keeps
refreshing for free, in the correct format, with stale meaning — and unlike an analyst's,
it has nobody who might happen to notice.

> This is a statement about **who owns a report**, not about what the GM may reach for.
> [ADR 0016](../docs/decisions/0016-gm-reads-reports-not-queries.md) is untouched: the GM
> still never queries the warehouse.

### Roster report

- **Established:** engineering-owned, no ledger seq — `first-sight` Phase 10, sim date 2024-03-07
- **Owner:** engineering
- **Policy:** every player in the organisation — **226** at 2024-03-07 — grouped by club and
  then by roster list (*Active roster*, *Secondary (40-man) roster*, *Injured list*,
  *Assigned to the club*), each row carrying real name, age, handedness and uniform number,
  under a header block naming the `save_id`, `sim_date` and `ingest_seq` it was read from.
  It also states **what it is not showing** — position, every rating, and the standings.
  Refresh with `uv run python -m ootp_ai.reports render`, which writes
  `<OOTP_OUTPUT_ROOT>/<save_id>/<sim_date>/<ingest_seq>/roster.md`.
- **Rationale:** until this existed the GM could read its own charter and not one fact about
  a single player on its roster. It is the club's own furniture rather than analysis — a
  front office knows who is on its roster without commissioning a study.
- **Review trigger:** the first roster move executed in-game. A re-render reads the newest
  `ingest_seq`, so a report still showing a traded player means **the ingest did not run**,
  not that the trade did not happen. Second trigger: the first time the withheld list
  matters more than the shown one — that is the signal to price a ratings slice, not to
  quietly widen this page.

### Warehouse catalog

- **Established:** engineering-owned, no ledger seq — `first-sight` Phase 11, sim date 2024-03-07
- **Owner:** engineering
- **Policy:** what the warehouse holds and what it does not — every declared table with its
  grain and key, per-table row counts and freshness, and the **withheld** groups stated
  rather than omitted. Of 89 declared fields, 55 reach a page, 11 are withheld and 23 are
  read but landed by nothing. Refresh with `uv run python -m ootp_ai.catalog`; the GM's copy
  lands beside `roster.md` as `warehouse-catalog.md`, and the tracked structural half is
  [`docs/warehouse-catalog.md`](../docs/warehouse-catalog.md).
- **Rationale:** a GM who cannot price the gaps in what it sees will either over-trust a thin
  report or spend an action asking for something that does not exist. Under
  [ADR 0013](../docs/decisions/0013-action-economy.md) that mistake costs an action, so the
  shape of the absence is worth knowing precisely.
- **Review trigger:** the landed field count changing without this entry changing. The
  tracked half is regenerated during the test run and refuses to differ, so a divergence
  means the generator stopped being run — not that nothing changed.

## Why `Established` and `Review trigger` are not optional

**A standing order that quietly stopped being right is this system's most interesting failure
mode.** The platoon policy set in April is wrong by July; nobody notices, because noticing
costs an action the GM would rather spend elsewhere, and the order keeps being applied for
free the whole time.

The sim date makes age visible at a glance. The review trigger is a pre-registered condition
that turns "should I revisit this?" from an open-ended worry into a check — which is far
cheaper to run and much harder to talk yourself out of.
