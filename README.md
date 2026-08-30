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
> local MySQL warehouse — eight tables, two universes, landed by a command anyone can run —
> and the GM reads two reports off it: its own 226-player organisation by name, and a
> catalog of what the warehouse does and does not hold. What is still missing is everything
> that would let it *judge* a player rather than list one.

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

**That diagram is the shape, not the state.** Of it, only the left column exists:
`bronze` is landed and read directly; **silver, gold and dbt are deferred**, and the
right-hand builder column has not been built at all. The deferral is recorded, with its
trigger, on [ADR 0004](docs/decisions/0004-mysql-warehouse.md) — the pattern is honoured
and only the tooling waits.

## Design decisions

Twenty-two are recorded in [`docs/decisions/`](docs/decisions/) — twenty live, two
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
cp .env.example .env               # then fill it in — see below
mysql -u root -p < ops/mysql-bootstrap.sql   # once: schemas, the app user, grants

uv run pytest -m "not gamedata"    # the offline suite — no game, no MySQL, no save
uv run pytest -m gamedata          # needs all three

uv run python -m ootp_ai.ingest land      # snapshot, parse and land the managed save
uv run python -m ootp_ai.reports render   # the roster report, from the latest landing
uv run python -m ootp_ai.catalog          # the catalog, tracked half and generated half
```

`ingest land` is what puts something in the warehouse for the other two to read; it
prints the `(save_id, sim_date, ingest_seq)` triple it created, and `--save-id` aims it
at one of the other configured saves. **The first run creates the eight declared
tables** — and only creates them. A table whose *shape* has drifted from the declaration
is not repaired, because that is a migration and a migration is a decision somebody makes
in the open. A save byte-identical to its own most recent landing is refused before
anything is copied; `--new-look` lands it again deliberately, at the next sequence
([ADR 0021](docs/decisions/0021-bronze-landing-is-append-only.md)).

`.env` needs your OOTP install directory, your saved-games directory, the managed
league's name, local MySQL credentials, and — optionally — the two non-managed saves
(`OOTP_TRUTH_LEAGUE`, `OOTP_PROBE_LEAGUE`), a snapshot root and an output root. Every
path in this repo resolves from those; none is hardcoded, and
[`.env.example`](.env.example) documents each key and why it exists. The only runtime
dependencies are `python-dotenv` and **PyMySQL** — pure Python, so no build toolchain.

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
| `src/ootp_ai/` | Parser, landing, warehouse loading, the three entry points |
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
and loaded into MySQL. Feature request #1 is now real through **Phase 10**: the
spine, an immutable snapshot layer, walkers for `saved_games.dat`,
`human_managers.dat`, `teams.dat`, `world.dat`, `players.dat` and `names.dat`, the
roster-membership grain, the warehouse those all land in, the differential that
proves the landed rows against the game's own export, and the roster report the GM
reads.

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

**And the landing is now proven, not merely green.** The differential parses the one save
that has an export, lands it, and compares the *warehouse* against `ootp_truth_real` —
so the loader is under test alongside the walk. It runs to zero unexplained differences
over 33 keyed columns and five tables: 259 clubs, 18,072 players, 15,672 roster rows,
3,058 calendar events, 30 division memberships. Every disagreement it can report is
named **per field, with its key** — never as a pass rate, because 99.99% looks like
rounding and is 1,800 wrong players.

Three places a *correct* parse disagrees with the export are carried as named rules with
exact populations, because a CSV-shaped export cannot write NULL and fills the gap
instead: 26 clubs whose city the export replaces with a nickname, 229 with no
real-world counterpart, and four all-star sides that sit in no division. A rule that
could suppress any number of rows would be a mute button; each of these fires on exactly
as many rows as it declares, in either direction. The comparison also runs in Python
rather than SQL — the schemas are accent- *and* case-insensitive, so `Ramírez == Ramirez`
would score as a match on precisely the names most likely to be mis-decoded.

Two limits are permanent and stated rather than left for a green suite to imply. Challenge
Mode has no export, so **nothing here validates the club we actually manage** — that falls
to `players.csv`, byte accounting, cross-mode equivalence and the operator's own eyes. And
the export writes display-scale ratings, so this can never be a rating validator; the
suite fails if anyone tries to make it one.

**Phase 10 shipped the roster report, and the GM can now see its own club.**
`uv run python -m ootp_ai.reports render` writes
`<output_root>/<save_id>/<sim_date>/<ingest_seq>/roster.md` — the organisation's 226
players, real names, grouped by club and by roster list, carrying age, handedness and
uniform number, with the snapshot it read on line one. The GM does not read the
warehouse ([ADR 0016](docs/decisions/0016-gm-reads-reports-not-queries.md)), so every
column is routed through one serving gate that resolves each one's epistemic label
before a line is formatted; a rating cannot reach the page by being forgotten about.

The page also states **what it is not showing** — position, every rating, and the
standings — because a report the GM cannot price the gaps in is worse than a thin one.

**The standings report was retired rather than deferred.** No declared table carries a
win-loss column: the standings region is not in `teams.dat`, and the `world.dat` walk
reached division membership and the league calendar instead. Landing a team-record
source is owed its own request.

**The catalog landed with Phase 11.** `uv run python -m ootp_ai.catalog` writes two
halves from one generator: [`docs/warehouse-catalog.md`](docs/warehouse-catalog.md) is
tracked and carries the structure — grains, keys, coverage, the withheld groups, and
where the reports resolve — while row counts and freshness generate beside the reports
in the ignored output root. The tracked half is regenerated during the test run and
refused if a single byte differs, so it cannot be hand-edited into drift.

**Phase 12 trued the documentation up against the repo that now exists**, and three claims
turned out to be measurably false. Each is now a dated correction rather than a deletion,
because a refuted claim is more useful written down than removed. There is **no
`leagues.dat`** — a Challenge-mode save holds 19 `.dat` files and a standard-mode one 18,
and none of either set is it; the league configuration is a ~1,200-byte scalar block in
`world.dat` that remains unread. [`docs/league-rules.md`](docs/league-rules.md) §1 said the
warehouse would supersede it "the moment the parser lands" — the parser has landed and **no
declared table carries a rules column**, so §1 is still the only copy of those values. And
the standard-mode validation save is **retained, not disposable**: Tier B compares the
binaries against the export, so deleting the save would end row-for-row validation for
fictional players and roster lists, the populations `players.csv` cannot reach at all.

The same pass completed [`docs/data-access.md`](docs/data-access.md) §1's file inventory
from nine entries to nineteen — the ten it omitted included `messages.dat`, the index of
the only channel by which the GM could hear from ownership — made every `verified` label in
its field-semantics section name the test that holds it, and recorded on
[ADR 0004](docs/decisions/0004-mysql-warehouse.md) that the warehouse landed with **no dbt
model**: ADR 0005's pattern honoured in full, only its tooling deferred, with
`incremental-loading` named as the trigger that ends the deferral. The GM's report channel
opened alongside it — `gm/standing-orders.md` gained an **engineering-owned report kind**,
because no staff have been engaged and naming an analyst as the owner of a
pipeline-generated page would be fiction in precisely the field the GM uses to decide whose
read to trust.

**The pipeline can now be run by someone who is not `pytest`.** Until
[`ingest-command`](requests/feature-requests/_done/ingest-command/) landed, `ingest_save` and
`land_snapshot` were library functions with no `__main__` behind them: the two universes in
the warehouse were put there by running the gamedata suite, and this file documented that as
the setup path. `uv run python -m ootp_ai.ingest land` is the third and last entry point. It
pre-flights the save against its own most recent landing — sizes first, digests only if every
size matches — and **refuses before anything is copied** when the bytes are unchanged, so a
habitual re-run costs ~40 ms and leaves no directory behind; changed bytes at an unchanged sim
date land the next sequence with no flag, which is
[ADR 0021](docs/decisions/0021-bronze-landing-is-append-only.md)'s motivating case.

It also collapsed four hand-composed arrangements of snapshot-and-parse into one function.
The command, the landing fixture and ADR 0001's three legs all call
`ingest/read.py::read_save`, so the manifest diff that proves nothing writes to the game now
brackets **the command a human actually runs** rather than a composition that existed only
inside its own test — measured at 2:40 over 30,703 files, against a 2m35s baseline.

**Phase 13 is next and it is the operator's.** A cold `gm` subagent asked to name five of
its own players from the handed-over report alone; a by-hand confirmation that a full
ingest left the managed save byte-identical; and a spot-check of at least 20 players across
5 clubs against the game's own screens, sampled **by `player_id`, never by name**.

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
