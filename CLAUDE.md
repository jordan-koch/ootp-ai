# CLAUDE.md — ootp-ai

## What this project is

An **AI front office for Out of the Park Baseball 25**. The agent is the General
Manager; the human is the operator who executes in-game. The claim under test is
that this front office can be **competitive** in a league it cannot cheat in.

> **This file is the engineering half.** If you are touching the club — any
> baseball decision, any action, anything in `gm/` — **read
> [`FRONT_OFFICE.md`](FRONT_OFFICE.md) first.** It holds the GM's role, the action
> economy, and what you are allowed to see. Skipping it means acting as a
> different GM than the one who made every prior decision.

Underneath the baseball, this is a data engineering project: read a proprietary
binary format nobody has a parser for, land it, model it, and serve it.

## This is not the 2024 season

It looks like it. It is seeded from real baseball and **diverges from it on the
first pitch.** The two universes share a past up to the current sim date and
nothing after.

So recalled knowledge about how a player's career actually went is knowledge about
**a different person**. Not contraband — simply wrong, and more wrong every week.
That applies to every agent here, and it bites hardest on prospects, where the
temptation to "already know" is strongest and the divergence is largest.

**The warehouse is the only reliable source of truth about this universe.** Where
it holds a scout's belief rather than a fact, that is deliberate
([ADR 0012](docs/decisions/0012-scouted-ratings-only.md)) — the belief is what you
get, and it is still more reliable than remembering a different world.

## Status

**Phase 0 — scaffolding.** Conventions, decisions and the format investigation are
landed, and **the club exists**: Boston Red Sox, `OOTP-AI`, Challenge Mode, sim
date 2024-03-07. **No pipeline code does** — `src/ootp_ai/` is a version string,
the `.dat` parser is feature request #1, and the GM therefore has no warehouse and
no reports yet ([ADR 0016](docs/decisions/0016-gm-reads-reports-not-queries.md)).

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
  contiguous u16 values ordered vR, vL, potential" is our observation; a copy of
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
  game-mechanics.md   How the OOTP engine behaves — free to the GM, and thin on purpose
  decisions/          ADRs — seventeen calls, two superseded
gm/                 TRACKED GM memory — charter, standing orders, ledger, decisions
requests/           Intake — feature-requests / bugfix-requests / data-incidents
.claude/skills/     Pipeline stages + /commit
.claude/agents/     Subagents — the write-capable builder, and the read-only GM
src/ootp_ai/        Parser, landing, warehouse loading
ops/                Repo governance, local toolchain
tests/              Structural guards + parser fixtures
var/                GITIGNORED — save snapshots, warehouse files, scratch
```

Directories appear when their phase does. `build/`, `datasets/`, and `transform/`
don't exist yet — their shapes are in
[ADR 0005](docs/decisions/0005-hybrid-data-layer.md); don't create them
speculatively.

## Important locations

- **[FRONT_OFFICE.md](FRONT_OFFICE.md)** — **read before any session that touches
  the club.** The GM's role, the action economy, what you may see, and where the
  club's memory lives ([ADR 0011](docs/decisions/0011-gm-memory-is-tracked.md)).
- **[docs/data-access.md](docs/data-access.md)** — start here for anything
  touching ingestion. Every claim carries an epistemic label, and the labels are
  load-bearing: most of this repo rests on beliefs about a binary format.
- **[docs/league-rules.md](docs/league-rules.md)** — the rule environment every
  baseball decision sits inside. **The rules evolve**; the document says which
  parts the warehouse supersedes and which parts exist nowhere else.
- **[docs/game-mechanics.md](docs/game-mechanics.md)** — how the OOTP engine
  *behaves*, as distinct from what this league is configured to allow. Free to the
  GM: it is competence at the job, not analysis of our data. **Deliberately thin**,
  and it enforces a stricter labelling rule than the other docs — model-recalled
  mechanics may never rank above `assumed`, because a confidently wrong mechanics
  doc is worse than none.
- **[docs/decisions/](docs/decisions/)** — read before proposing anything
  structural. Seventeen ADRs, two superseded.
- **[requests/README.md](requests/README.md)** — the intake contract and the
  three-track split. Each track's README owns its own layout.

## Established facts — do not re-investigate

Verified 2026-08-15. Full detail and epistemic labels in
[`docs/data-access.md`](docs/data-access.md).

- **Save binaries are plain** — not encrypted, not compressed; primitives decoded.
- **`players.csv` ships with the game and is the Rosetta Stone** — ~12,855 real
  players, raw unfiltered ratings. It is what located the ratings block.
- **Records contain variable-length regions.** Parse sequentially; **never seek
  to a fixed offset.** Field *order* is stable across saves; offsets are not.
- **Names are indirected** into `names.dat`. `players.dat` holds indices.
- **Real players carry their Lahman/BBRef ID** (`deverra01`), ~1,712 unique — a
  join key to Retrosheet, Chadwick, FanGraphs, Statcast.
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
one of them (0016) constrains what an agent may query. Read them before making a
baseball decision; 0012's parser corollary is restated below under the correctness
trap because it binds code too.

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
- **Label your epistemics.** *Measured*, *verified*, *inferred*, *assumed*,
  *unconfirmed* mean different things. Nearly everything known about the save
  format is a belief formed by looking at bytes; an unconfirmed claim is a task.
- **Mechanical checks live in CI; judgment lives in `/update-docs`.**

## The build rulebook

**[`.claude/agents/data-engineer.md`](.claude/agents/data-engineer.md) is the
single owner of the build rules** — read it before writing pipeline code, whether
you are the agent or building directly. Topics it owns: game-is-read-only;
sequential parsing and the fixed-offset ban; ground truth and epistemic labelling;
the version guard; snapshot immutability; grain contracts and the two player keys;
structural absence; the write allowlist; the handoff contract.

Named here, not restated — restating one in actionable form recreates the second
copy that single ownership exists to prevent.
[`tests/test_agent_contract.py`](tests/test_agent_contract.py) asserts each
survives. Spawn protocol and its limits:
[`.claude/agents/README.md`](.claude/agents/README.md),
[ADR 0009](docs/decisions/0009-write-capable-implementation-subagent.md).

## Outstanding scaffolding work

- **No `ROADMAP.md`.** Work is driven from `requests/` alone; `/commit`'s Step 4
  maintains request statuses and Index rows instead.
- **A ported panel guard fails on arrival** —
  `.claude/skills/implement-plan/tests/verify_batching_guard.mjs`. It fails
  **identically** in `nba2k-rpg`, so it is an upstream defect. Diagnose before
  trusting stage 4's verify batching.
- **The dbt adapter question is open** —
  [ADR 0004](docs/decisions/0004-mysql-warehouse.md) §Notes. Due with the first
  dbt model, not before.

## The correctness trap that will bite

**In-game rating displays are filtered and scale-converted** — 20–80 on the player
page, 1–100 in reports, ~1–1000 in storage. Matching a displayed value to a byte
identifies the **wrong field with no error surfaced**, which is the single most
likely way to silently corrupt every downstream recommendation. Ground truth is
`players.csv`, which is raw. Detail: [`docs/data-access.md`](docs/data-access.md) §5.

A field the parser cannot classify is treated as a true rating and **withheld** —
"probably fine" is not a classification.

## Related repos — references, not dependencies

None is upstream; nothing here consumes anything from them. Local checkouts, paths
in `.env.example` — this repo is public.

- **`nba-analysis`** — style template: toolchain, ADR format, request tracks, CI,
  the medallion pattern, the `data-engineer` agent.
- **`nba2k-rpg`** — process sibling: `.claude/skills/` and the tracked-local-state
  inversion `gm/` uses were ported from it.
- **`pokemon-lab`** — data-layer sibling: `build/` → `datasets/` + `manifest.json`
  resolve-by-name, for static reference data.

## Context on the operator

Data engineer. Thinks in systems and pushes back well on design. Wanted to own the
ingestion rather than accept a vendor's export — hence
[ADR 0002](docs/decisions/0002-parse-binaries-not-export.md), chosen deliberately.

His role in the club is in [`FRONT_OFFICE.md`](FRONT_OFFICE.md).

This is a **fun side project**. Size scope for sustained enjoyment, not
completeness. That does *not* mean light process.

## How to help

- **Check `docs/data-access.md` before assuming anything about the save format.**
  It is a catalog of beliefs, and it says which ones are which.
- **Read the ADRs before proposing anything structural.** Fifteen live decisions;
  re-litigating one is the most expensive thing that can happen here.
- **Vertical slices, not horizontal layers.** Save → parser → warehouse → model →
  a decision you can actually act on, before the next slice widens. A beautiful
  pipeline that has never set a lineup has failed at both of this project's goals.
- **The parser is where correctness risk concentrates.** A mis-mapped field yields
  a plausible number, not a crash. Ground-truth validation is not a later phase.
