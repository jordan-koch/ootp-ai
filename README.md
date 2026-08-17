# ootp-ai

An AI front office for **Out of the Park Baseball 25**.

**The agent is the General Manager.** It owns decisions, priorities, staff, and
outcomes. A roster of specialist advisors — scouting, pitching, hitting,
analytics, payroll, pro scouting — reads a warehouse built from the league's own
save files and reports to it. They disagree in public; the GM adjudicates.

The human is the **operator**: he executes decisions in-game, reports outcomes
honestly, and rules on what costs an action. He does not make baseball decisions.

The question is whether that front office can be **competitive** in a league it
cannot cheat in — and three constraints are what make the question mean anything:

- **Challenge Mode.** The league cannot be edited, reloaded, or undone.
- **Scouted ratings only.** The GM sees what a real front office sees — its own
  scouts' beliefs, not the answer key.
- **An action economy.** The GM cannot pause time. The organization gets a fixed
  budget of actions per week and has to prioritize, exactly like a real one.

> **Phase 1 — the parser is real.** The managed club exists — Boston Red Sox,
> Challenge Mode, from 2024-03-07 — and the code that reads its save does too:
> a forward-only cursor, a header and version guard, an immutable snapshot layer,
> and working walkers for four of the save's binaries. Every team record of the
> validation save matches the game's own export field-by-field, and so does every
> entry of the league calendar. No warehouse and no reports yet, so the GM still
> cannot see its own club.

## Why it's interesting

OOTP is a database wearing a baseball uniform, but it doesn't hand you the
database. Its save files are a proprietary binary format with no public parser,
and the game's built-in export is **hidden in Challenge Mode** — the one mode
where a competitiveness claim actually means something.

So the project reads the binaries itself. That turned out to be tractable:

- Save files are unencrypted and uncompressed — conventional little-endian
  structs with u32-length-prefixed strings.
- `players.csv`, which ships with the game, carries raw unfiltered ratings for
  ~12,855 real players. Aligning it against the binary is what makes field
  mapping possible.
- Real players carry their **Baseball-Reference / Lahman ID** inside the save
  (`deverra01`), which cross-walks the league to Retrosheet, the Chadwick
  Register, FanGraphs, and Statcast — real-world priors the in-game AI doesn't
  have.

Full findings, with epistemic labels on every claim, in
[`docs/data-access.md`](docs/data-access.md).

## Architecture

```
  OOTP save (.dat)                  OOTP install (data/database/)
   read-only, per sim date           static reference + engine constants
          │                                        │
          │ our parser                             │ build/build-*.py
          ▼                                        ▼
   bronze ─→ silver ─→ gold                   datasets/ + manifest.json
      (dbt, MySQL warehouse)                  (resolved by logical name)
          │                                        │
          └────────────────┬───────────────────────┘
                           ▼
              front office — specialist advisors
                           │
                           ▼
                  GM briefing → you execute
```

Two data-layer patterns, split by one rule: *does this change when the league is
simulated?* No → builder + `datasets/`. Yes → parser + dbt medallion.
([ADR 0005](docs/decisions/0005-hybrid-data-layer.md))

## Design decisions

Nineteen are recorded in [`docs/decisions/`](docs/decisions/) — seventeen live, two
superseded. The ones that shape everything else:

| ADR | Decision | Why |
|---|---|---|
| [0001](docs/decisions/0001-read-only-no-write-back.md) | Never write to the game | Kills the hardest problem; keeps Challenge Mode safe |
| [0002](docs/decisions/0002-parse-binaries-not-export.md) | Parse binaries, not the export | The export is gated in Challenge Mode and caps out at monthly |
| [0017](docs/decisions/0017-gm-is-a-subagent.md) | The GM is a subagent; we are umpires | Constraints enforced by discipline are not constraints |
| [0011](docs/decisions/0011-gm-memory-is-tracked.md) | GM memory is tracked in git | The save records what happened, never why |
| [0012](docs/decisions/0012-scouted-ratings-only.md) | Scouted ratings only | True ratings are the answer key; reading it proves nothing |
| [0013](docs/decisions/0013-action-economy.md) | The action economy | Pausing time is an advantage no real GM has |
| [0014](docs/decisions/0014-staff-is-the-information-channel.md) | Staff quality is the information channel | A clearer picture is bought by hiring, never by code |
| [0015](docs/decisions/0015-gm-is-employed-not-appointed.md) | The GM is employed, not appointed | Someone other than the GM has to decide whether it succeeded |
| [0016](docs/decisions/0016-gm-reads-reports-not-queries.md) | The GM reads reports, never the warehouse | A GM with a tireless analyst on infinite call isn't a GM |

## Setup

**You need your own copy of OOTP 25.** This repo contains no game data — none is
tracked, by design ([ADR 0006](docs/decisions/0006-public-repo-local-data.md)) —
so it is not runnable from a clone alone.

```bash
uv sync
cp .env.example .env      # then fill in your install + save paths
uv run pytest
```

`.env` needs your OOTP install directory, your saved-games directory, the league
name, and local MySQL credentials. Every path in this repo resolves from those;
none is hardcoded.

Standing up the local MySQL warehouse — install, bootstrap script, and the
server settings worth changing — is documented in
[`ops/README.md`](ops/README.md).

## Repo layout

| Path | What |
|---|---|
| `docs/` | Data access findings + architecture decisions |
| `gm/` | **Tracked** GM memory — charter, standing orders, action ledger, decisions |
| `requests/` | Work intake — feature / bugfix / data-incident tracks |
| `src/ootp_ai/` | Parser, landing, warehouse loading |
| `ops/` | Repo governance, local toolchain |
| `tests/` | Structural guards + parser fixtures |
| `var/` | Gitignored — snapshots, warehouse, scratch |

`gm/` inverts the usual "local state is disposable" rule on purpose: the save
records what happened, never *why* the GM chose it, and that reasoning has no
other copy.

`build/` + `datasets/` (static reference builders) and `transform/` (dbt) arrive
with the phases that need them.

## Status and what's next

Phase 0 landed the conventions, the format investigation, and the managed league.
The one-time ground-truth export has been captured from a disposable standard-mode
save and loaded into MySQL.

Next is the parser, now **scoped** as feature request #1: read `teams.dat` and
`players.dat` sequentially, resolve names against `names.dat`, and land the result
— validated field-by-field against `players.csv` and that export. Its first
genuinely useful job is telling the GM who is on its roster, which is the thing it
currently cannot say at all.

Scoping reshaped the request. Verifying that the managed league is configured the
way [`docs/league-rules.md`](docs/league-rules.md) claims was the intended second
job, and is now deferred: the league configuration turned out not to live in a
`leagues.dat` at all — there is no such file — and recovering it means mapping an
8.9 MB `world.dat` with no Challenge Mode export to check against.

## License

MIT. This covers the code and the schema knowledge derived by observation. It
does not cover, and this repository does not redistribute, any Out of the Park
Developments data.
