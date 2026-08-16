# Feature Requests

Home for every substantial new piece of work — a parser, a dataset builder, a dbt
model, an advisor, a skill. The point is a **light, repeatable set of guardrails**
around how an idea travels from *"I want X"* to *"a cold agent can implement X"* —
without turning a one-hour change into a week of process.

> **Bugs go elsewhere.** A **defect** in existing code has its own track
> ([`../bugfix-requests/`](../bugfix-requests/)). Code that **ran green and
> produced wrong data** has a third ([`../data-incidents/`](../data-incidents/)).
> Tie-break: missing = feature, broken-that-exists = bug, ran-clean-but-wrong =
> incident.

## The pipeline

| # | Stage | Skill | Produces | Shape |
|---|---|---|---|---|
| 1 | **Intake** | `/make-feature-request` | `FEATURE_REQUEST.md` | Interview — turns a raw idea into a scoped, repo-grounded request. Fast, single-agent. |
| 2 | **Scope** | `/scope-feature` | `PROJECT_SCOPE.md` | Panel: 3 divergent scopers → merge/converge → 2 adversarial. Settles fit + testable acceptance criteria. |
| 3 | **Plan** | `/create-implementation-plan` | `IMPLEMENTATION_PLAN.md` | Panel: 3 planners → merge → 2 code-grounded adversaries + 1 meta-audit. Cold-handoff plan. |
| 4 | **Implement** | `/implement-plan` | code + `IMPLEMENTATION_REPORT.md` | Panel: core reviewers + auto-scaled specialists → execution-based verify → meta-audit. Proves every acceptance criterion by running it. |

Each stage produces one artifact and is **human-gated** — you review and edit
before invoking the next.

**All four stages run by default.** Stages 2 and 3 are skippable only by an
argument written into the request's closing **Stage plan** section and cleared
against the three hard triggers in
[`../README.md`](../README.md#weight--the-panel-is-the-default). Stage 4 still
runs either way: with no plan to consume it enters **direct-build mode**, taking
this request as the statement of intent.

## Every dataset comes from here

No file gets parsed and no dataset gets registered without a request behind it. A
dataset carries **contracts** — a grain, keys, a freshness expectation, an
upstream that can change without warning — and those are decisions, not
implementation details.

A dataset request must settle, before any code:

- **Grain.** One row per *what*? "Player per snapshot" and "player per team-stint
  per snapshot" are different tables, and the difference is invisible until a
  mid-season trade breaks a join.
- **Keys.** What makes a row unique, and is that enforceable as a test? Note that
  OOTP's internal `player_id` and the real-world Lahman ID are different keys with
  different coverage — only ~1,712 players have the latter.
- **Coverage.** Which populations does this source actually contain? Fictional
  players lack external IDs; minor leaguers lack much of what majors carry.
  Structurally-absent data is not missing data, and conflating them produces
  silently wrong aggregates.
- **Update semantics.** Append-only per snapshot, or does history get restated?
- **Which data-layer pattern.** Apply the ADR 0005 rule: *does this change when
  the league is simulated?* No → builder + `datasets/`. Yes → parser + dbt.
- **Registration.** For builder datasets, the logical name it takes in
  `datasets/manifest.json`. Consumers resolve by name; nothing hardcodes a path.

## Parser work carries an extra obligation

Anything that reads the save binaries must state, in the request:

- **What ground truth validates it**, and for which fields. `players.csv` is the
  default; a simulated ground-truth export is stronger.
- **Its epistemic labels.** A field map asserted without validation is
  `unconfirmed`, and saying so is the difference between a task and a liability.
- **How it fails.** A parser that seeks to a fixed offset will pass on day-0 data
  and corrupt everything later ([data-access.md §4](../../docs/data-access.md)).
  The request should say why this one doesn't.

## Acceptance criteria

"Testable" has a specific meaning here. A criterion is testable when a **cold
agent can run one command and get a pass or fail** — not when a human can eyeball
a number and nod.

- ✅ *`pytest tests/test_parser_teams.py` is green: all 30 MLB clubs extract with
  the abbreviations and ARGB colors pinned in `tests/fixtures/teams.json`.*
- ✅ *Parsed ratings for every player present in `players.csv` match it exactly —
  `pytest -m gamedata tests/test_rosetta.py` proves it.*
- ✅ *Re-parsing the same snapshot twice produces byte-identical output.*
- ❌ *The ratings look about right.*

Criteria only a human can prove — whether a recommendation is *good baseball*,
whether a briefing is readable — are legitimate and central to this project, but
must be **marked user-run** so the acceptance panel doesn't claim them.

## Layout

The directory **is** the unit of work:

```
feature-requests/
  <slug>/                      # kebab-case (e.g. 1-dat-parser)
    FEATURE_REQUEST.md         # stage 1
    PROJECT_SCOPE.md           # stage 2
    IMPLEMENTATION_PLAN.md     # stage 3
    IMPLEMENTATION_REPORT.md   # stage 4 — acceptance ledger + what shipped
    reviews/                   # panel working files — the provenance trail
  _done/<slug>/                # archived once it reaches a terminal stage
```

**Active-vs-done.** An item lives at the track root while in flight; when it
reaches the terminal stage — `implemented` — it moves **once** into `_done/`. The
Index keeps the row with its link pointing into `_done/`.

Every artifact opens with a status blockquote:

> **Status:** &lt;stage&gt; · created &lt;YYYY-MM-DD&gt; · &lt;open | decided&gt; · next: &lt;stage or "implement"&gt;

**Status grammar:** `intake` → `scoped` → `planned` → `implemented`

A skipped stage skips its status: an argued direct build goes `intake` →
`implemented`, and the absent artifacts are the record that it did.

## Index

| Feature | Stage | Notes |
|---|---|---|
| [first-sight](first-sight/) | intake | The `.dat` parser, warehouse landing, a data catalog, and two starting reports — the first time the GM can see its own club |
