# CLAUDE.md — ootp-ai

## What this project is

An **AI front office for Out of the Park Baseball 25**. The league is managed by
a staff of specialist advisors — scouting, pitching, hitting, analytics, payroll,
pro scouting — reading a warehouse built from the save's own files. The human is
the GM: he executes, he does not decide.

The claim being tested is that this front office can be **competitive** in a
Challenge Mode league. That claim is only meaningful because the league cannot be
edited underneath it ([ADR 0003](docs/decisions/0003-challenge-mode-league.md)).

Underneath the baseball, this is a data engineering project: read a proprietary
binary format nobody has a parser for, land it, model it, and serve it.

## Status

**Phase 0 — scaffolding — in progress.** The repo, conventions, and the findings
from the format investigation are landed. **No pipeline code exists yet.**
`src/ootp_ai/` is a version string. The `.dat` parser is feature request #1 and
has not been built.

What *is* established is in [`docs/data-access.md`](docs/data-access.md), and it
is substantial — the format is decoded far enough to know the project is
feasible. Read it before proposing anything about ingestion.

## Stack

Python 3.12, uv, ruff, mypy strict, pytest. Warehouse is **MySQL**, local
([ADR 0004](docs/decisions/0004-mysql-warehouse.md)), with dbt for the medallion
layers. No cloud, no credentials beyond a local DB user, no cost.

## The repo is PUBLIC — and the game's data is not ours

[ADR 0006](docs/decisions/0006-public-repo-local-data.md) binds every change:

- **Everything tracked is world-readable, forever.**
- **OOTP's shipped data and every saved game stay out of the repo.**
  `players.csv`, the XML reference files, `.dat` files, `.lg` directories,
  snapshots, exports — all gitignored by name and extension. They are Out of the
  Park Developments' intellectual property.
- **Derived schema knowledge is ours and is tracked.** "The ratings block is 18
  contiguous u16 values ordered vR, vL, potential" is our observation. A copy of
  `players.csv` is not.
- **No machine-specific absolute paths, account ids, tokens, or personal
  identifiers in tracked files.** Everything resolves from `.env`;
  `.env.example` lists the keys. `tests/test_no_leaks.py` fails the build on
  drive-letter paths, home directories, and email addresses.

## Project map

```
README.md           Public-facing overview, architecture, setup
CLAUDE.md           This file — onboarding map + the rules to work by
docs/
  data-access.md      What can be read, from where, with epistemic labels
  decisions/          ADRs — seven settled calls
requests/           Intake — feature-requests / bugfix-requests / data-incidents
.claude/skills/     Pipeline stages + /commit
.claude/agents/     The write-capable build subagent — and the rulebook it owns
src/ootp_ai/        Parser, landing, warehouse loading
ops/                Repo governance, local toolchain
tests/              Structural guards + parser fixtures
var/                GITIGNORED — save snapshots, warehouse files, scratch
```

Directories appear when their phase does. `build/` and `datasets/` (the static
reference pattern), `transform/` (dbt), and `agents/` don't exist yet — the
shapes they'll take are described in
[ADR 0005](docs/decisions/0005-hybrid-data-layer.md), but don't create them
speculatively.

## Important locations

- **[docs/data-access.md](docs/data-access.md)** — start here for anything
  touching ingestion. Every claim carries an epistemic label, and the labels are
  load-bearing: most of this repo rests on beliefs about a binary format.
- **[docs/decisions/](docs/decisions/)** — read before proposing anything
  structural. Seven ADRs cover write-back, ingestion path, Challenge Mode, the
  warehouse, the data-layer split, repo scope, and the front-office shape.
- **[requests/README.md](requests/README.md)** — the intake contract and the
  three-track split. Each track's README is authoritative for its own layout.

## Established facts — do not re-investigate

Verified 2026-08-15. Full detail and epistemic labels in
[`docs/data-access.md`](docs/data-access.md).

- **Save binaries are not encrypted or compressed.** `\x00OOTP` magic, version
  byte `0x19` (25), entropy 4.5–5.6 bits/byte.
- **Primitives are decoded**: u32-length-prefixed strings, `u8 day / u8 month /
  u16 year` dates, u32 ARGB colors, u16 ratings on a ~1–1000 internal scale, u32
  whole-dollar money, f64 stat series in year-keyed blocks.
- **`players.csv` ships with the game and is the Rosetta Stone.** ~12,855 real
  players with raw unfiltered ratings. Aligning it to `players.dat` is what
  located the ratings block.
- **Records contain variable-length regions.** Parse sequentially; **never seek
  to a fixed offset.** Field *order* is stable across saves; absolute offsets
  are not.
- **Names are indirected** into `names.dat` (~264k entries). `players.dat` holds
  indices, not names.
- **Real players carry their Lahman/BBRef ID** (`deverra01`) inside
  `players.dat`, ~1,712 unique — a join key to Retrosheet, Chadwick, FanGraphs,
  Statcast.
- **The export is hidden in Challenge Mode**, and its automation ceiling is
  monthly regardless.

## Decisions already made — do not re-propose

- **No write-back of any kind** (0001). Not save edits, not roster import files,
  not UI automation. The GM executes.
- **Parser, not export** (0002). The export's only sanctioned use is one-time
  ground truth from a disposable standard save.
- **Challenge Mode** (0003). Its restrictions are constraints, not obstacles.
- **MySQL** (0004), knowingly paying for a less-mature dbt adapter.
- **Two data-layer patterns, split by physics** (0005). The rule: *does this
  change when the league is simulated?* No → builder + `datasets/`. Yes → parser
  + dbt medallion.
- **Advisors disagree in public** (0007). Conflicts surface to the GM; they are
  never silently merged.

## Project conventions

- **Work on a branch; land it through a PR.** `main` is protected. Never commit
  to `main` directly.
- **Agents commit only through `/commit`.** Never run `git commit` ad hoc — not
  for a one-line change, not for an "obviously safe" one. **Never merge, push to
  `main`, force-push, or amend** — those stay the user's.
- **Subagents get read-only git.** When spawning any subagent, tell it git is
  read-only — never `checkout`/`reset`/`restore`/`clean`/`stash` or anything that
  discards working-tree state. Bubble a destructive-git *need* back up.
- **Every substantial change is a request.** Nothing gets parsed, landed, or
  modeled without an intake artifact behind it. The full pipeline is the default;
  a skip is argued in writing. See [requests/README.md](requests/README.md).
- **Label your epistemics.** *Measured*, *verified*, *inferred*, *assumed*,
  *unconfirmed* mean different things. This matters more here than in a typical
  repo: nearly everything known about the save format is a belief we formed by
  looking at bytes. An unconfirmed claim is a task, not a fact.
- **Mechanical checks live in CI; judgment lives in `/update-docs`.** Lint,
  types, tests, and the leak guard run on every PR.

## The build rulebook

**The rulebook for parser, landing, and warehouse work lives in
[`.claude/agents/data-engineer.md`](.claude/agents/data-engineer.md), which is its
single owner** — read it before writing pipeline code, whether you are the agent
or the main thread building directly. What it owns, by topic: the game-is-read-only
absolute; sequential parsing and the fixed-offset ban; ground truth and epistemic
labelling; the format version guard; snapshot immutability; grain contracts and the
two player keys; structural absence; the write allowlist and its deny set; and the
handoff return contract.

These rules are named here, not restated. A reader learns what is in the rulebook
and goes and reads it — a rule restated here in actionable form would recreate the
second copy that single ownership exists to prevent.
[`tests/test_agent_contract.py`](tests/test_agent_contract.py) asserts each one is
still written down. Spawn protocol and its limits:
[`.claude/agents/README.md`](.claude/agents/README.md) and
[ADR 0009](docs/decisions/0009-write-capable-implementation-subagent.md).

## Outstanding scaffolding work

- **No `ROADMAP.md`.** Work is driven from `requests/` alone; `/commit`'s Step 4
  maintains request statuses and track Index rows instead. Revisit if the request
  set outgrows it.
- **A ported panel guard fails on arrival.**
  `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` fails six dedupe
  and coverage assertions — and fails **identically** in the `nba2k-rpg` repo it
  came from, so this is an upstream defect, not a porting error. The other four
  panel guards pass. Diagnose before trusting stage 4's verify batching.
- **The dbt adapter question is open** — see
  [ADR 0004](docs/decisions/0004-mysql-warehouse.md) §Notes. It comes due with
  the first dbt model, not before.

## The correctness trap that will bite

**In-game rating displays are filtered and scale-converted.** The player page
shows 20–80, reports show 1–100, storage is ~1–1000 — and a separate
`scouting.dat` means what you see may be the *scout's belief*, not the true
value.

Matching a screenshot rating to a byte can identify the **wrong field with no
error surfaced**. Ground truth comes from `players.csv`, which is raw. This is
written down because it is the single most likely way to silently corrupt every
downstream recommendation.

Its unsettled twin: **should the advisors see true or scouted ratings?** Scouted
is the honest Challenge Mode experience. Unresolved on purpose — see
[ADR 0007](docs/decisions/0007-advisory-front-office.md) notes.

## Related repos — references, not dependencies

Neither is upstream; nothing here consumes anything from either. Local checkouts,
paths not recorded here — this repo is public. `.env.example` lists the keys.

- **`nba-analysis`** — NBA lakehouse. The **style template**: toolchain, ADR
  format, request tracks, structural tests, CI, and the medallion pattern this
  repo borrows for snapshot facts.
- **`nba2k-rpg`** — NBA 2K progression layer. The **process sibling**: the
  `.claude/skills/` pipeline here was ported from it.
- **`pokemon-lab`** — Gen 3 Pokémon tooling. The **data-layer sibling**: the
  `build/build-*.py` → `datasets/` + `manifest.json` resolve-by-name pattern this
  repo borrows for static reference data.

## Context on the user

Data engineer. Thinks in systems and pushes back well on design. Wants to own the
ingestion rather than accept a vendor's export — which is why
[ADR 0002](docs/decisions/0002-parse-binaries-not-export.md) exists and why the
harder path was chosen deliberately, not by accident.

This is a **fun side project**. That governs scope — size it for sustained
enjoyment, not completeness. It does *not* mean light process.

## How to help

- **Check `docs/data-access.md` before assuming anything about the save format.**
  It is a catalog of beliefs, and it says which ones are which.
- **Read the ADRs before proposing anything structural.** Seven decisions are
  settled; re-litigating them is the most expensive thing that can happen here.
- **Vertical slices, not horizontal layers.** Every phase goes save → parser →
  warehouse → model → a recommendation a GM can act on, before the next one
  widens. A beautiful pipeline that has never produced a lineup has failed at
  both of this project's goals.
- **The parser is where correctness risk concentrates.** A mis-mapped field
  yields a plausible number, not a crash. Validation against ground truth is not
  optional and is not a later phase.
