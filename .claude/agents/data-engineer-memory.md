# Data-engineer memory

Implementation ergonomics, learned the hard way. Read this before you build; append to it
when something costs you time that it should not cost the next session.

## What belongs here

Things that make *building* here go wrong: struct-parsing traps, library and tooling
surprises, commands that behave differently than documented, harness behaviour. Facts an
advisor would never care about but an implementer rediscovers every session.

## What routes elsewhere — do not put these here

- **Data facts** — a field's meaning or offset, what a population structurally lacks, scale
  and scout-filter behaviour, what a column actually contains. These go to
  `docs/data-access.md` via your handoff's `docs-delta` section. Never here: that file is
  audited by the doc gate and this one is not, so a data fact recorded here means the repo
  holds two answers and the gate checks one.
- **Repo-wide scar tissue** — a trap that binds every agent, not just you: `CLAUDE.md`
  Constraints & Gotchas, via `docs-delta`.
- **Decisions and their costs** — `docs/decisions/`, via `docs-delta`.

## Entry format

One bullet per entry, opening line a fixed shape so it can be checked mechanically:

```
- **YYYY-MM-DD** · `label` · <the claim> · evidence: <pointer> · tag: <routing tag>
```

Continuation lines are indented under the bullet. Keep an entry to about four lines.
`label` is one of this repo's five — `measured`, `verified`, `inferred`, `assumed`,
`unconfirmed`. An `assumed` claim written as `verified` is worse than no entry.

**Paths are inline code, never markdown links** — the link checker scans only markdown-link
syntax, so a backticked path is invisible to it. **Cite a repo artifact, never raw
environment output**: this file is committed and the repo is public.

## The budget — two numbers, two jobs

**~120 physical lines is the curation target**, enforced by judgment at the `/update-docs`
sweep before merge. **250 is the runaway ceiling**, enforced mechanically in CI.

**Append freely while you work. Never prune.** Pruning mid-build means predicting which
entries later phases will need, and guessing wrong drops the one that would have saved them.
Curation is the human's job, at the doc gate, with the whole build visible.

## Entries

- **2026-08-15** · `measured` · PowerShell 5.1 `Set-Content`/`Out-File` mangle UTF-8; write
  files with the Write/Edit tools instead. · evidence: `CLAUDE.md` conventions ·
  tag: tooling
- **2026-08-15** · `measured` · `uv sync` resolves *every* dependency group, not just the
  default ones, so an unsatisfiable optional group blocks the whole install. `dbt-mysql` is
  capped at 1.7.0 and pins `dbt-core~=1.7.0`. · evidence:
  `docs/decisions/0004-mysql-warehouse.md` §Notes · tag: tooling, docs-candidate
- **2026-08-15** · `measured` · The ported panel guard
  `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` fails on arrival, and fails
  **identically** in the `nba2k-rpg` repo it came from — a pre-existing upstream defect, not
  a porting error. Six dedupe/coverage assertions. · evidence: `CLAUDE.md` Outstanding
  scaffolding work · tag: harness
