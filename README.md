# ootp-ai

An AI front office for **Out of the Park Baseball 25**.

A staff of specialist advisors — scouting, pitching, hitting, analytics, payroll,
pro scouting — reads a warehouse built from a league's own save files and
recommends what the club should do. A human plays GM: he executes the
recommendations, he does not make the calls.

The question the project is trying to answer is whether that front office can be
**competitive** in a league it cannot cheat in.

> **Phase 0 — scaffolding.** Conventions, decisions, and the results of the save
> format investigation are landed. No pipeline code exists yet. The `.dat` parser
> is the first feature request.

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

Seven are settled and recorded in [`docs/decisions/`](docs/decisions/). The ones
that shape everything else:

| ADR | Decision | Why |
|---|---|---|
| [0001](docs/decisions/0001-read-only-no-write-back.md) | Never write to the game | Kills the hardest problem; keeps Challenge Mode safe |
| [0002](docs/decisions/0002-parse-binaries-not-export.md) | Parse binaries, not the export | The export is gated in Challenge Mode and caps out at monthly |
| [0003](docs/decisions/0003-challenge-mode-league.md) | Challenge Mode | A competitiveness claim needs a league you can't edit |
| [0007](docs/decisions/0007-advisory-front-office.md) | Advisors disagree in public | A Capologist objecting to a trade is information, not noise |

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

## Repo layout

| Path | What |
|---|---|
| `docs/` | Data access findings + architecture decisions |
| `requests/` | Work intake — feature / bugfix / data-incident tracks |
| `src/ootp_ai/` | Parser, landing, warehouse loading |
| `ops/` | Repo governance, local toolchain |
| `tests/` | Structural guards + parser fixtures |
| `var/` | Gitignored — snapshots, warehouse, scratch |

`build/` + `datasets/` (static reference builders) and `transform/` (dbt) arrive
with the phases that need them.

## Status and what's next

Phase 0 landed the conventions and the format investigation. Next is the parser,
entering through the normal intake pipeline as feature request #1: read
`teams.dat` and `players.dat` sequentially, resolve names against `names.dat`,
and land the result — validated field-by-field against `players.csv` and against
a one-time ground-truth export taken from a disposable standard-mode save.

## License

MIT. This covers the code and the schema knowledge derived by observation. It
does not cover, and this repository does not redistribute, any Out of the Park
Developments data.
