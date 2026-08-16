> **Status:** intake · created 2026-08-16 · open · next: scope

# Feature Request — First sight: land the club and tell the GM what else exists

## Problem / Motivation

**The GM agent exists and can decide nothing.**

It holds `Read` and `Glob`. There is no warehouse of our league, no reports, and
no way for it to learn anything about the baseball team it runs. It can read its
own charter, the owner's goals, and the league's rules — and not one fact about a
single player on its roster. Asked who should play second base, it would have to
say it does not know who plays second base.

Meanwhile the save holds all of it. `OOTP-AI.lg` carries a 30 MB `players.dat`,
a 5 MB `teams.dat`, 2.7 MB of `scouting.dat` and an 8 MB name table, and nothing
in this repo can read a byte of it.

There is a second, quieter problem. Everything in
[`docs/league-rules.md`](../../../docs/league-rules.md) §1 is `measured` **from the
creation screens and a throwaway probe save**, not from our league. Challenge Mode
has no export, so there is no way to confirm the club is configured the way we
believe it is. Every plan built on those values is built on belief.

## Desired Outcome

Three things are true when this is done.

**The GM can see its own club.** It can name the 26-man roster and read the
standings. Not analysis — the two things a general manager cannot function without
knowing.

**The GM knows what it is not seeing.** A catalog describes what has been landed —
grain, coverage, freshness — without exposing the data itself. The GM reads the
menu for free and decides whether any of it is worth an action
([ADR 0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md)). That
tension is the point: relying on thin sight versus spending to see further is a
strategy we want the GM to *choose*, not one we pre-decide for it.

**We can confirm the league is what we think it is.** Parsed values from
`OOTP-AI.lg` are diffed against `docs/league-rules.md` §1, and the differences —
or their absence — are recorded.

The observable signal: a cold session spawns the `gm` agent, and it returns a
handoff whose `## situation` section contains real players with real names.

## Rough Ideas (non-binding)

- Sequential record walk, never fixed offsets. Land to MySQL bronze 1:1 with
  parser output, conform in silver, serve gold.
- The catalog generated from warehouse metadata rather than hand-written, so it
  cannot drift from what was actually landed.
- Ground truth is the loaded `ootp_truth_real` export plus `players.csv`.
- The two starting reports are gold models rendered to Markdown the GM can read.

Scoping is free to reject all of this.

## Scope Signals

- **In:** `teams.dat`, `players.dat`, the `names.dat` join, enough of
  `scouting.dat` to classify true-versus-scouted, landing to the `ootp` warehouse,
  the catalog, and exactly two reports — roster and standings.
- **Explicitly out:** advisors of any kind. Any third report. Serving another
  organization's data to the GM. `retired.dat`. Statistical history. The in-game
  HTML report path ([`data-access.md`](../../../docs/data-access.md) §7). Anything
  that writes to the game.
- **Not now / later:** incremental weekly ingestion and snapshot discipline — the
  league is unsimmed at 2024-03-07, so there is exactly one state to land and
  re-ingestion has nothing to prove yet. Also later: the newspaper
  (`text_data.sqlite3`), and any dbt layering beyond what these two reports need.

## Affected Area & Pointers

Parser and landing, and it creates most of the pipeline from nothing.

A cold scoping agent reads, in order:

1. [`docs/data-access.md`](../../../docs/data-access.md) — §4 for the format, §5
   for the ratings trap. **Read the epistemic labels, not just the claims.**
2. [`.claude/agents/data-engineer.md`](../../../.claude/agents/data-engineer.md) —
   the build rulebook, and the single owner of the parsing invariants
3. [`docs/league-rules.md`](../../../docs/league-rules.md) — §1 is the verification
   target
4. [`src/ootp_ai/`](../../../src/ootp_ai/) — currently a version string and nothing else

`transform/`, `build/` and `datasets/` do not exist; their shapes are in
[ADR 0005](../../../docs/decisions/0005-hybrid-data-layer.md).

Ground truth already loaded: `ootp_truth_real` in MySQL, 72 tables from a
disposable standard-mode save, including `players_scouted_ratings` at 36,144 rows
across two scouting perspectives.

## Data Contracts

Open, for scoping to settle:

- **Grain.** One row per player per snapshot? Per player per team-stint per
  snapshot? They differ exactly when a mid-season trade happens.
- **Keys.** OOTP's `player_id` covers everyone; the Lahman ID covers ~1,712 of
  ~18,000. A join on the wrong one silently drops the fictional majority.
- **Coverage.** Which populations land — majors only, or the five minor-league
  tiers under MLB too? Fictional players have no external ID; minor leaguers lack
  fields the majors carry. **Structural absence is not missing data.**
- **Update semantics.** Append-only per snapshot, or restated? Only one snapshot
  exists today, which makes this easy to get wrong cheaply.
- **Extraction cost.** How long a full parse takes, and whether that makes weekly
  re-ingestion viable later.

## Constraints / Non-negotiables

- **Walk records sequentially. Never seek to a fixed offset.** Variable-length
  regions mean a fixed offset passes on day-0 data and silently returns the wrong
  field later.
- **Guard the version byte.** The header's magic starts at **offset 1**, not 0 —
  a reader checking `data[0:4]` rejects every valid save.
- **Ground truth is `players.csv` and the loaded export, never an in-game display.**
- **The game is read-only.** One write to a Challenge Mode save is unrecoverable.
- **Serve scouted ratings only** ([ADR 0012](../../../docs/decisions/0012-scouted-ratings-only.md)).
  The withhold list is the three true rating tables plus `players.prone_*` and
  `players_value.*`. A field that cannot be classified is withheld.
- **No OOTP data in git** ([ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md)).
  Derived field maps are ours and are tracked; save contents are not.
- Resolve paths by name from `.env`. Tests must pass without a game install.
- **No agent this creates gets network access** — no `WebFetch`, no `WebSearch`.
  We are in March 2024 in a game modelled on real baseball, and an agent that can
  read how the season actually went has the answer key to the *future*, which is
  worse than true ratings. Note the gap this does not close: **a shell is a
  superset of a web tool**, so anything granted `PowerShell` has network whether
  or not it is named. That matters most for advisors, which are out of scope here
  and will need the question answered before the first one is built.

## Open Questions for Scoping

1. **Is the scouted rating view stored, or computed at render time?**
   [`data-access.md`](../../../docs/data-access.md) §5 has this `unconfirmed`, and
   it is the one that can break the project: if OOTP generates it on the fly, the
   parser cannot reproduce it and ADRs 0012, 0014 and 0016 have no data path at
   all. The test is written in §5 and has not been run.
2. **How is `names.dat` encoded?** `unconfirmed`. Without the join every player is
   an integer, and a roster report of integers is not a roster report. This may be
   the largest single unknown in the request.
3. **Which populations land?** Five minor-league tiers sit under MLB. Landing them
   widens the catalog for free (the GM cannot read what it has not commissioned),
   but multiplies parse cost and coverage edge cases.
4. **Where does the catalog live and what regenerates it?** It describes the
   warehouse, so it is rebuildable and belongs in `var/` by the placement rule in
   [`gm/README.md`](../../../gm/README.md) — but the GM's forced-read list points
   at it, and a fresh clone will not have one.
5. **How thin is thin?** Roster and standings is the proposal. Too thin and the
   GM burns early actions on things any GM would already have; too rich and the
   information-strategy tension we want never appears.
6. **How is `docs/league-rules.md` §1 verified** when there is no export to diff
   against, and what happens to the document when parsed values disagree with it?

## Stage plan

**Full pipeline.** Two triggers fire, either alone sufficient:

**Trigger 1** — Open Questions is not merely non-empty, it contains a
project-threatening unknown. Question 1 asks whether the central mechanic has a
data path.

**Trigger 3** — this defines the parser's field map, the warehouse grain, and the
dataset contracts in one go, and it pins
[`docs/league-rules.md`](../../../docs/league-rules.md). The parser's field map is
called out by name in the bugfix track's own README as the case where a wrong fix
is unrecoverable rather than merely costly: nothing throws, a plausible number
flows into a rating, into a recommendation, into a decision the GM executes.
