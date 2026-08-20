> **Status:** intake · created 2026-08-19 · open · next: scope

# Feature Request — Land a league dimension, and answer for the two league ids that belong to nobody

## Problem / Motivation

**The warehouse holds 259 clubs across 17 league ids and cannot say what a single one of
those leagues *is*.** No walker lands a league dimension. Phase 5b of
[`first-sight`](../first-sight/) reached division membership and the league calendar out of
`world.dat` and stopped short of the per-league scalar blocks; nothing has gone back.

That gap has been an abstraction until now. Phase 9 turned it into a measured discrepancy
nobody can explain, and filing this request is how that finding stops living in a phase
handoff.

**Measured 2026-08-19 against `ootp_truth_real`, the standard-mode probe's export:**

- `leagues` holds **15** rows.
- `COUNT(DISTINCT league_id)` over `teams` is **17**.
- The two extra ids are **215** and **219**, carrying 2 clubs apiece and no `leagues` row.

**The four clubs were then looked at, and they are all all-star sides** — `allstar_team = 1`,
named `All-Stars`, team ids 256–259, at `level` 5 and 6, no parent club. So the honest
statement of the anomaly is narrower than "two undocumented leagues with real clubs in
them": *two league ids exist that carry nothing but all-star squads, and the export's
`leagues` table does not describe them.*

That is still a real question — a league id the export uses and does not define is either an
omission in `leagues` or a placeholder the game attaches all-star sides to — but it is a
**smaller** one, and it is bounded. It is recorded here rather than left for the scoping
panel to rediscover, because the measurement was cheap and the wrong version of it
("undocumented leagues with clubs") would have sent scoping somewhere it does not need to
go. Whether 215 and 219 should produce `bronze_league` rows at all is now the question, and
it is a decision rather than an investigation.

**This surfaced as a correctness problem, not a wish.** `first-sight`'s AC6 asserted the
differential would compare *"15 leagues"*. It cannot — there is nothing landed to compare —
and the obvious repair is a trap: restating the clause as `COUNT(DISTINCT league_id)` over
`bronze_team` yields **17**, so a *correct* parse would fail its own acceptance criterion.
AC6 was amended on 2026-08-19 to strike the clause and name the claim the harness can
enforce (`bronze_team.league_id` matches the export on 259 of 259 clubs). That amendment is
honest, and it leaves a real hole.

**The GM feels this hole directly.** `bronze_team.league_id` is an integer with no name, no
level, and no rules attached. A roster report cannot say *"Triple-A, International League"*;
it can say *"league 218"*. `docs/league-rules.md` — the document that tells the GM what
environment it is competing in — carries roster limits and service-time rules as **prose an
operator typed**, with no landed source behind any of it.

## Desired Outcome

**The warehouse can name a league and state its rules, and the 215/219 anomaly has a
recorded answer.**

Concretely, three things are true when this is done:

**A league id resolves to a league.** A report joining `bronze_team.league_id` gets at
minimum a name, an abbreviation and a level, so *"Triple-A, International League"* is a
query rather than a lookup table somebody maintains by hand.

**The rules the GM operates under have a landed source.** Active roster limit, secondary
and expanded limits, minimum service days, the draft and trade-deadline dates — the columns
`docs/league-rules.md` currently asserts from memory. Where the parse cannot reach one, it
is `unconfirmed` and withheld, not guessed.

**215 and 219 have a disposition in writing** — whether they produce `bronze_league` rows,
and on what evidence. They are known to carry only all-star sides; what is not settled is
whether `world.dat` describes them at all, and therefore whether a walk that lands 15
leagues against 17 referenced ids is complete or two rows short. Either answer is fine
written down; a silent 15-against-17 is not.

## Rough Ideas (non-binding)

- Extend `parser/world.py` to walk the per-league scalar blocks it already navigates past.
  It reaches division membership and the calendar, so the entry landmarks are established
  work rather than a new search.
- A `bronze_league` table declared in `contracts/tables.toml` like every other, keyed
  `(save_id, sim_date, ingest_seq, league_id)`, with the differential comparing it against
  `ootp_truth_real.leagues` per field by name — the harness built in Phase 9 takes a new
  `TableSpec` and nothing else.
- The 163-column export table is the *upper* bound on what could be landed and emphatically
  not a target. Land the fields with a consumer; `field_map.toml`'s `[[withheld]]` section
  records why the rest are out.
- The **structural-absence allowlist Phase 9 could not use lands here**: the export writes
  `0` for `rules_active_roster_limit` and the service-time columns on all 14 non-MLB league
  rows. That was the plan's original allowlist example and it had nowhere to apply, because
  no league row was landed. Whoever builds this inherits both the trap and the mechanism.

## Scope Signals

- **In:** a league dimension parsed from `world.dat`; its contract declaration and DDL; its
  differential coverage against the export; a written answer on league ids 215 and 219;
  correcting whatever `docs/league-rules.md` asserts that the landed data contradicts.
- **Explicitly out:** ratings of any kind, including `avg_rating_*` — ADR 0012 is untouched
  by this and the export's rating columns are display-scale. League *financials* and
  league-history tables. Anything that would widen `SNAPSHOT_FILES`. Re-opening
  `first-sight`'s amended AC6.
- **Not now / later:** sub-league and division *names* — `world.dat` carries them and
  `bronze_division_team` already lands the memberships, so naming divisions is a natural
  follow-on but a separate decision about scope.

## Affected Area & Pointers

**Parser and warehouse.** ADR 0005's split puts this squarely on the parser + dbt side: it
changes when the league is simulated.

A cold scoping agent reads, in order:

1. [`docs/data-access.md`](../../../docs/data-access.md) — the epistemic labels and what is
   known about `world.dat`. Note §*league-rules* asserts a `leagues.dat` that does not exist
2. `src/ootp_ai/parser/world.py` — the landmark-entered walk that already reaches division
   membership and the calendar, and stops short of the per-league blocks
3. `src/ootp_ai/contracts/tables.toml` — the eight declared tables and the grain-versus-key
   agreement a ninth would have to satisfy
4. `src/ootp_ai/validate/export_diff.py` — the Phase 9 differential, which a new `TableSpec`
   plugs into, and its `ABSENCE_RULES` mechanism
5. [`requests/feature-requests/first-sight/reviews/handoff-phase-9.md`](../first-sight/reviews/handoff-phase-9.md)
   — where the 15-vs-17 measurement is recorded
6. [`docs/league-rules.md`](../../../docs/league-rules.md) — the prose this would give a
   source, and the document that says which parts the warehouse supersedes

## Constraints / Non-negotiables

- **Sequential walk, no fixed offsets.** `world.dat` is landmark-entered and region-accounted;
  a per-league block reached by a computed offset is the silent-corruption class CLAUDE.md
  names.
- **Bronze is 1:1 with the walk.** Every league the walk frames lands, including the ones
  nobody manages. Filtering belongs to the report layer.
- **Structural absence is NULL, never zero** — and this is the request where the export's
  14 zero-filled non-MLB league rows finally have a landed counterpart to be compared
  against.
- **An unclassifiable field is withheld.** The export has 163 league columns; landing a
  number whose meaning is a guess is worse than not landing it.
- **`docs/league-rules.md` evolves and says which parts the warehouse supersedes.** Where
  the landed data disagrees with the prose, the prose is corrected — with the measurement,
  not silently.

## Open Questions for Scoping

1. **Does `world.dat` describe leagues 215 and 219, and should they land?** Narrowed from
   "what are they" by the measurement above: all four of their clubs are all-star sides, so
   these are not undocumented leagues full of players. What remains is a decision — if the
   file carries blocks for them, landing 17 rows is 1:1 with the walk and correct; if it
   carries 15, then the export references two ids it does not define and *that* is the fact
   to record. The one outcome to refuse is landing 15 and saying nothing about the other
   two.
2. **Which of the 163 export columns have a consumer?** The GM's actual needs are roster
   limits, service time, and the calendar dates it plans around. A defensible minimum beats
   a wide landing nobody validated.
3. **Does the level hierarchy come from here or from `bronze_team.level`?** Clubs already
   carry `level`, verified export-exact on 259/259. Whether the league's own level is a
   second source or the same fact seen twice matters for whether they can ever disagree.
4. **Does this supersede `docs/league-rules.md` §1, or annotate it?** The doc's own rule is
   that the warehouse supersedes it where they overlap; nobody has had to exercise that yet.
5. **Is a league dimension enough for the roster report to name a level, or does it need
   sub-league and division names too?** Bears on whether the deferred naming work above
   should be pulled in rather than split.

## Stage plan

**Full pipeline — intake → scope → plan → implement.** No stage skip is argued, and
[ADR 0008](../../../docs/decisions/0008-panels-by-default.md)'s first trigger applies
directly: this needs numbered acceptance criteria, and the criterion for "the league
dimension is complete" cannot be written until Open Question 1 is settled from the bytes. A
build started before then either lands 15 rows and quietly drops two referenced ids, or
lands 17 and invents a shape for two blocks nobody has read — both the wrong-data failure
this project ranks worse than a gap. Open Question 2 (which of 163 export columns have a
consumer) is the other reason: a wide landing nobody validated is exactly what the scoping
panel exists to cut back.
