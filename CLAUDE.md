# CLAUDE.md — ootp-ai

## What this project is

An **AI front office for Out of the Park Baseball 25**. The agent is the General
Manager; the human is the operator who executes in-game. The claim under test is
that this front office can be **competitive** in a league it cannot cheat in.
Underneath the baseball it is a data engineering project: read a proprietary binary
format nobody has a parser for, land it, model it, and serve it.

> **This file is the engineering half.** If you are touching the club — any
> baseball decision, any action, anything in `gm/` — **read
> [`FRONT_OFFICE.md`](FRONT_OFFICE.md) first.** It holds the GM's role, the action
> economy, and what you are allowed to see. Skipping it means acting as a
> different GM than the one who made every prior decision.

## This is not the 2024 season

It looks like it. It is seeded from real baseball and **diverges from it on the
first pitch** — the two universes share a past up to the current sim date and
nothing after. So recalled knowledge about how a player's career actually went is
knowledge about **a different person**: not contraband, simply wrong, and more
wrong every week. It bites hardest on prospects, where the temptation to "already
know" is strongest and the divergence is largest.

**The warehouse is the only reliable source of truth about this universe.** Where
it holds a scout's belief rather than a fact, that is deliberate
([ADR 0012](docs/decisions/0012-scouted-ratings-only.md)) — the belief is what you
get, and it is still more reliable than remembering a different world.

## Status

**Phase 1 — the parser is real.** Boston Red Sox, `OOTP-AI`, Challenge Mode, sim
date 2024-03-07; `src/ootp_ai/` reads the save, validated field-by-field against
the game's own export. [`README.md`](README.md) carries what has landed and what
is next.

**There is still no warehouse and no reports**, so the GM cannot yet see its own
club ([ADR 0016](docs/decisions/0016-gm-reads-reports-not-queries.md)). Bronze
landing is Phase 8 of [`first-sight`](requests/feature-requests/first-sight/).

## Stack

Python 3.12, uv, ruff, mypy strict, pytest. Warehouse is **MySQL**, local
([ADR 0004](docs/decisions/0004-mysql-warehouse.md)), dbt for the medallion
layers. No cloud, no cost.

## The repo is PUBLIC — and the game's data is not ours

[ADR 0006](docs/decisions/0006-public-repo-local-data.md) binds every change:

- **Everything tracked is world-readable, forever** — including all of `gm/`.
- **OOTP's shipped data and every saved game stay out of the repo.**
  `players.csv`, the XML reference files, `.dat`, `.lg/`, snapshots, exports —
  gitignored by name and extension. They are Out of the Park Developments' IP.
- **Derived schema knowledge is ours and is tracked.** "The ratings block is 18
  contiguous u16s ordered vR, vL, potential" is our observation; a copy of
  `players.csv` is not.
- **No machine-specific paths, account ids, tokens, or personal identifiers.**
  Everything resolves from `.env`; `tests/test_no_leaks.py` fails the build.

## Project map

```
README.md           Public-facing overview, architecture, setup
CLAUDE.md           This file — the engineering half: map, stack, build rules
FRONT_OFFICE.md     The baseball half — read it before touching the club
docs/
  data-access.md      What can be read, from where, with epistemic labels
  league-rules.md     The rule environment; what it implies; what evolves
  game-mechanics.md   How the OOTP engine behaves — free to the GM, thin on purpose
  decisions/          ADRs — nineteen calls, two superseded, seventeen live
gm/                 TRACKED GM memory — charter, standing orders, ledger, decisions
requests/           Intake — feature-requests / bugfix-requests / data-incidents
.claude/skills/     Pipeline stages + /commit
.claude/agents/     Subagents — the write-capable builder, and the read-only GM
src/ootp_ai/        Parser, landing, warehouse loading
  contracts/          TRACKED field + grain declarations — derived schema, ours to keep
ops/                Repo governance, local toolchain
tests/              Structural guards + parser fixtures
var/                GITIGNORED — save snapshots, warehouse files, scratch
```

Directories appear when their phase does. `build/`, `datasets/` and `transform/`
don't exist yet — their shapes are in
[ADR 0005](docs/decisions/0005-hybrid-data-layer.md); don't create them
speculatively.

**Three of those docs carry rules, not just information.**
[`data-access.md`](docs/data-access.md) starts anything touching ingestion, and its
epistemic labels are load-bearing. [`league-rules.md`](docs/league-rules.md)
**evolves**, and says which parts the warehouse supersedes.
[`game-mechanics.md`](docs/game-mechanics.md) caps model-recalled mechanics at
`assumed` — a confidently wrong mechanics doc is worse than none.

## Established facts — do not re-investigate

Verified 2026-08-15; detail and epistemic labels in
[`docs/data-access.md`](docs/data-access.md).

- **`players.csv` ships with the game and is the Rosetta Stone** — raw, unfiltered.
- **Records contain variable-length regions** — field *order* is stable, offsets
  are not. The fixed-offset ban is the rulebook's, and CI enforces it.
- **Names are indirected** into `names.dat`; `players.dat` holds indices.
- **Real players carry their Lahman/BBRef ID** — a join key to public baseball data.
- **The export is hidden in Challenge Mode**, and caps at monthly regardless.

## Decisions already made — do not re-propose

- **No write-back of any kind** (0001). Not save edits, not roster import files,
  not UI automation. The operator executes.
- **Parser, not export** (0002). The export's only sanctioned use is one-time
  ground truth from a disposable standard save.
- **Challenge Mode** (0003). Its restrictions are constraints, not obstacles.
- **MySQL** (0004), knowingly paying for a less-mature dbt adapter.
- **Two data-layer patterns, split by physics** (0005). *Does this change when
  the league is simulated?* No → builder + `datasets/`. Yes → parser + dbt.
- **GM memory is tracked in git** (0011). `gm/` is the one inversion of the
  "local state is disposable" rule. `var/` holds only what rebuilds from the save.

**The GM-facing decisions — 0012 through 0017 — live in
[`FRONT_OFFICE.md`](FRONT_OFFICE.md).** They bind behaviour rather than code, and
0016 constrains what an agent may query. Read them before any baseball decision;
0012's parser corollary binds code instead, and is owned by the ADR itself.

## Project conventions

- **Work on a branch; land it through a PR.** `main` is protected.
- **Agents commit only through `/commit`**, never `git commit` ad hoc — not for a
  one-line change, not for an "obviously safe" one.
- **Ask before merging a PR, then merge and clean up.** Confirm protection is live
  and checks are green, ask, and on approval merge, prune and sync. **Never push
  to `main`, force-push, or amend** — those stay the operator's.
- **Subagents get read-only git** — never `checkout`/`reset`/`restore`/`clean`/
  `stash` or anything that discards working-tree state. Tell them so when
  spawning; bubble a destructive-git *need* back up.
- **Every substantial engineering change is a request.** The full pipeline is the
  default; a skip is argued in writing. See
  [requests/README.md](requests/README.md). Baseball decisions are *not* requests.
- **Work is driven from `requests/` alone — there is no `ROADMAP.md`.**
- **Label your epistemics.** *Measured*, *verified*, *inferred*, *assumed*,
  *unconfirmed* mean different things. Nearly everything known about the save
  format is a belief formed by looking at bytes; an unconfirmed claim is a task.
- **Mechanical checks live in CI; judgment lives in `/update-docs`.**
- **Vertical slices, not horizontal layers.** Save → parser → warehouse → model →
  a decision you can actually act on, before the next slice widens. A beautiful
  pipeline that has never set a lineup has failed at both of this project's goals.

## The build rulebook

**[`.claude/agents/data-engineer.md`](.claude/agents/data-engineer.md) is the
single owner of the build rules** — read it before writing pipeline code, whether
you are the agent or building directly. It owns game-is-read-only, sequential
parsing and the fixed-offset ban, ground truth and epistemic labelling, the version
guard, snapshot immutability, grain contracts and the two player keys, structural
absence, the write allowlist and the handoff contract. **Named here, not restated**
— restating one in actionable form recreates the second copy that single ownership
exists to prevent, and
[`tests/test_agent_contract.py`](tests/test_agent_contract.py) asserts each
survives. Spawn protocol: [`.claude/agents/README.md`](.claude/agents/README.md),
[ADR 0009](docs/decisions/0009-write-capable-implementation-subagent.md).

## The correctness trap that will bite

**In-game rating displays are filtered and scale-converted** — matching a displayed
value to a byte identifies the **wrong field with no error surfaced**, the likeliest
way to silently corrupt every downstream recommendation. The scales, the ground
truth and the withhold-if-unclassified rule are owned by
[`docs/data-access.md`](docs/data-access.md) §5 and
[ADR 0012](docs/decisions/0012-scouted-ratings-only.md); the rulebook binds them.
