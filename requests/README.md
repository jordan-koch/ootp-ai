# Requests

The project's work intake — three parallel tracks under one inbox. Every
substantial change enters here.

| Track | For | Start with |
|---|---|---|
| **[feature-requests/](feature-requests/)** | New capability — a parser, a dataset, a dbt model, an advisor, a skill | `/make-feature-request` |
| **[bugfix-requests/](bugfix-requests/)** | A defect in existing code, config, or tooling | `/make-bugfix-request` |
| **[data-incidents/](data-incidents/)** | Everything ran green and **the data is wrong** | see that track's README |

Each track's **README is the contract** — layout, status grammar, the live Index,
and the `_done/` archive convention. The back half
(`/create-implementation-plan` → `/implement-plan`) is shared and auto-detects
the track from the artifact's path.

## Why three tracks and not two

A code defect and a data defect look similar and triage completely differently —
and in this repo the distinction is unusually sharp.

The parser reads a **reverse-engineered binary format**. When it grabs the wrong
`u16`, nothing throws. There is no schema to violate and no vendor to complain.
It returns a number that is the right type, in a plausible range, and simply
wrong — and it flows into a rating, into a recommendation, into a decision the GM
executes. Every test stays green the whole way.

That failure mode has no reproduction in the usual sense and no stack trace. It
is found by *disagreeing with reality*: a value that contradicts `players.csv`,
a rating that contradicts the in-game UI, a stat line that doesn't reconcile.

See [data-incidents/README.md](data-incidents/README.md).

## Principles

Two rules run through every panel in every track:

- **Greedy, but gated.** Agents propose *everything* — generating options is
  cheap, so be ambitious. Scope-growing or expensive ideas get **tiered and
  deferred for your decision**, never silently folded into the build.
- **Generate → converge → triage → you decide.** Adversarial agents record *all*
  findings with severity and confidence and never self-censor. The merge step
  builds the convergence map and surfaces the gated calls. **You** dispose them —
  the panel proposes, you decide.

And one that matters more here than in a typical repo:

- **Label your epistemics.** *Measured*, *verified*, *inferred*, *assumed*,
  *unconfirmed* are different words and mean different things. Nearly everything
  known about the save format is a belief formed by looking at bytes. A request
  that says "contract years are a fixed 10-element array" when nobody has checked
  is a liability. Say `unconfirmed` and it becomes a task.

## Weight — the panel is the default

Not every change needs every stage. But **which changes don't is decided here,
against a written request — never in advance.**
[ADR 0008](../docs/decisions/0008-panels-by-default.md) settles this; this
section is the rubric it points to.

> **The full pipeline runs unless a skip is argued in writing.** The burden of
> proof is on the cheap path.

**Entry.** This governs work that gets a request at all. Typo fixes, dependency
bumps, and doc edits never enter the pipeline.

**Three hard triggers. Any one and the panel runs; no argument is available:**

| | Trigger | Why it's disqualifying |
|---|---|---|
| 1 | Intake's **Open Questions** came out non-empty | That *is* a blurry edge, and it's mechanical — the agent already wrote it down |
| 2 | **Explicitly out** couldn't be filled | Intake already treats an empty one as "interview more". Still empty means the edges aren't known |
| 3 | It touches something **expensive to reverse** | A settled ADR, the parser's field map, a dataset contract, a warehouse grain, or anything another request pins |

Clear all three and a skip becomes *available* — at the cost of a written
argument in the request's closing **Stage plan** section, naming which triggers
it cleared.

**Skipping doesn't mean shipping unreviewed.** `/implement-plan` has a
direct-build mode that takes the intake artifact in place of a plan, and its
adversarial reviewers are derived from what the diff touched, so they run at full
strength.

See [CLAUDE.md](../CLAUDE.md) for where this sits in the repo.
