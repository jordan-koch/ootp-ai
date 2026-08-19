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
> and working walkers for six of the save's binaries. Every team record of the
> validation save matches the game's own export field-by-field, so does every
> entry of the league calendar, so does every biographical field of all 18,072
> players the export knows about — plus five it does not — and so does every
> player's **name**, resolved through a two-file join. All of it now lands in a
> local MySQL warehouse — eight tables, two universes — and the reports the GM
> actually reads are the one thing still missing.

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

Twenty-one are recorded in [`docs/decisions/`](docs/decisions/) — nineteen live, two
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

**Node** is needed only for the agent skills' own guards, which CI also runs —
see [`ops/README.md`](ops/README.md). Nothing in `src/` requires it.

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

Phase 0 landed the conventions, the format investigation, and the managed league,
plus a one-time ground-truth export captured from a disposable standard-mode save
and loaded into MySQL. Feature request #1 is now real through **Phase 8b**: the
spine, an immutable snapshot layer, walkers for `saved_games.dat`,
`human_managers.dat`, `teams.dat`, `world.dat`, `players.dat` and `names.dat`, the
roster-membership grain, and the warehouse those all land in.

The `players.dat` walk frames every player record on disk — 18,077 in each test save
and 22,046 in the managed league, which carries 337 clubs rather than 259 — and lands
a deliberately minimal field set — the biographical head, the club assignment, a
player's handedness and his Lahman ID — with every field checked against
**every** row of the ground-truth export rather than a sample. The record turned
out to be presence-mask-governed: a falsy field is simply not written (and
handedness revealed a second pattern, written-unless-default), so those fields
sit at offsets that move from record to record, and reading them at a fixed
offset happens to be right about 87% of the time — exactly the kind of
nearly-correct this project treats as worse than an error. Position and role are
deliberately **not** landed: the byte the save stores provably disagrees with
the export's derived closer role, and a mapping below exact does not ship.

The roster grain — which players sit on which club's active roster, 40-man and
injured list — reproduces the export's 15,672-row membership table exactly, by
combining stored per-player status bits with each club's membership array and
refusing loudly whenever the two files disagree.

**The roster is now people rather than integers.** `names.dat` is a 264,095-entry
string table with a single index space, walked to zero residual, and the two `u32`s
in each player record turn out to be the first- and last-name indices in that order —
established by scoring every candidate mapping across all 18,072 players of the
validation save rather than by reading the bytes, since the correct assignment scores
100% and the reverse one scores 0.01%. Names resolve exactly against the export, and
against `players.csv` for the real players on Boston.

**The warehouse has a shape, and it is declared rather than written.** Eight
tables state their grain as a sentence — *"one row per player per team per roster
list per save per snapshot"* — and the loader parses that sentence, resolves each
dimension to columns, and requires the union to equal the declared key exactly. The
same declaration emits the `CREATE TABLE`s, so the schema MySQL holds is the schema
the sentence describes, and prose-versus-enforcement drift fails at load time rather
than failing to be noticed. Every landed field carries an epistemic label checked
against a declared vocabulary, because until it did, nothing read those labels at all
and a mistyped one would have shipped green.

**Bronze is landed.** Two universes sit in the warehouse — the managed league at
2024-03-07 and its Challenge-mode twin eleven days later — 337 and 259 clubs, 22,046
and 18,077 players, 20,016 and 15,721 roster rows, 264,095 names apiece, keyed on
`(save_id, sim_date, ingest_seq)` so two states of the same in-game date can both be
kept. The store is **append-only**: re-landing a triple refuses loudly, a second look
at an unchanged sim date takes the next sequence, and nothing is ever overwritten —
which is what lets the club immediately before and immediately after an executed
decision both be retrieved and diffed. Every column the loader binds comes from the
declaration and every table is counted back out of the schema before the transaction
commits, so a provenance row cannot misdescribe its own landing.

The join works end to end: Boston's roster at 2024-03-07 resolves to 33 / 26 / 30 / 7
across assignment, active, 40-man and injured lists — the split the operator verified
by hand — with real names, uniform numbers and ages.

**Next are the two reports.** The GM does not read the warehouse
([ADR 0016](docs/decisions/0016-gm-reads-reports-not-queries.md)), so bronze existing
is not yet the GM seeing its club — a rendered roster is. Between here and there sit
the parser-versus-export differential, which proves the landed rows field by field
against the game's own export, and the report layer that reads them.

Verifying that the managed league is configured the way
[`docs/league-rules.md`](docs/league-rules.md) claims was the intended second job
and remains deferred, though the reason has narrowed. The league configuration
does not live in a `leagues.dat` — there is no such file — and the 8.9 MB
`world.dat` that holds it is now entered and partly mapped: its division hierarchy
and its 3,058-entry league calendar both land, validated against the export. What
is still unread is the ~1,200-byte scalar block holding the rules themselves.

## Related repos — references, not dependencies

Local checkouts; none is upstream and nothing here consumes anything from them.

- **`nba-analysis`** — style template: toolchain, ADR format, request tracks, CI,
  the medallion pattern, the `data-engineer` agent.
- **`nba2k-rpg`** — process sibling: `.claude/skills/` and the tracked-local-state
  inversion `gm/` uses were ported from it.
- **`pokemon-lab`** — data-layer sibling: `build/` → `datasets/` + `manifest.json`
  resolve-by-name, for static reference data.

## License

MIT. This covers the code and the schema knowledge derived by observation. It
does not cover, and this repository does not redistribute, any Out of the Park
Developments data.
