> **Status:** intake · created 2026-08-20 · open · next: scope

# Feature Request — Incremental loading: land once, then build on it as the season moves

## Problem / Motivation

**The warehouse has never held the same league at two different in-game dates.** Every
snapshot landed so far sits at a single date per universe, and the whole point of this
project is a front office whose decisions are judged over a season.

The *storage mechanism* for this exists and is tested. `(save_id, sim_date, ingest_seq)` is
in every bronze key, re-landing a triple refuses, and a second `ingest_seq` at one date
lands alongside its predecessor rather than over it
([ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md)). What has never
been exercised is the **other axis** — the one the season actually moves along.

Three concrete gaps, measured against the tree as it stands:

1. **No test lands one league at two sim dates.** The test that looks like it does —
   `test_a_landing_at_another_sim_date_is_left_untouched` in
   `tests/test_snapshot_semantics.py` — *queries* for an already-landed run at a different
   date and **skips loudly when it finds none**. It has never created the second date. It
   passes today only because two *different universes* happen to sit at different dates
   (the probes at 2024-03-18, the managed league at 2024-03-07), so what it actually proves
   is that two universes do not collide — which its sibling
   `test_two_universes_at_one_sim_date_land_side_by_side` already proves. The time axis is
   untested.

2. **Nothing reads across snapshots.** Every consumer resolves to exactly one triple and
   reads within it — `validate/export_diff.py`, and `reports/resolve.py` which was written
   for the roster report. There is no path that takes two triples and says what differs.
   The GM therefore cannot be told *who improved*, *who got hurt*, or *what changed since
   the last look*, no matter how many snapshots are landed.

3. **The sim-forward-and-re-land loop has never been run end to end, and no phase stages
   it.** It is inherently operator work — the game is read-only to this project
   ([ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md)), so nothing here
   can advance a save's date. Nobody has yet sat down, simmed a save forward, re-landed it,
   and confirmed the pipeline does what its design says.

The cost of finding this later is the thing. Every gap above is cheap to close now, while
one snapshot exists and nothing depends on the answer. Discovered after the GM has been
reading reports for a month, a defect in the time axis means a corrupted history of exactly
the decisions this project exists to evaluate — and history is the one thing that cannot be
re-derived from a save that has moved on.

## Desired Outcome

**Someone can sim a save forward, land it, and prove the earlier snapshot is untouched — and
a consumer can ask what changed between two landings.**

Concretely, "done" looks like:

- The disposable Challenge-mode twin holds **two landed sim dates**, and the earlier one is
  demonstrably byte-identical after the later one arrives. The proof creates the second
  date rather than hoping to find one, so it cannot pass by skipping.
- There is **one documented way to name two snapshots and get their differences** — at
  whatever grain scoping settles. Not a report; the thing a report would be built on.
- The operator has a **written, repeatable procedure** for the sim-forward-and-re-land loop,
  including what to check afterwards, so it is a routine rather than an expedition.
- Anyone reading the warehouse can answer *"what does this universe hold, and at which
  dates?"* without inspecting directories.

The observable signal: land the twin at date A, sim it, land it at date B, and get a truthful
answer to *"what changed between A and B"* — with the A snapshot provably unmodified.

## Rough Ideas (non-binding)

- **`reports/resolve.py` is probably the seam.** It already resolves one triple and exposes
  `landed_sim_dates()`, which answers "what dates does this save hold". A two-snapshot
  resolver is a small step from it — but it currently lives under `reports/`, and a
  cross-snapshot read path may not belong there.
- **The comparison machinery may already half-exist.** `validate/export_diff.py` compares two
  row sets keyed on the same columns and reports differences per field by name. It was built
  to compare *landed rows against an export*; comparing *landed rows against other landed
  rows* is the same shape with a different right-hand side. Worth looking at before writing
  anything new — though it is also a 57 KB module built for a different purpose, and reuse
  could easily be the wrong call.
- **Plan §2.5(i) of `first-sight` already named the approach**: the Challenge twin is *"the
  right way to manufacture a multi-snapshot history for trending without ever touching the
  managed league."* It was never sequenced into a phase.

All non-binding. Scoping is free to route this differently.

## Scope Signals

- **In:** landing one league at two sim dates and proving the first survives; a read path
  that takes two snapshots and reports what differs; the operator's sim-forward procedure,
  written down and staged as USER-RUN; making "what dates does this save hold" answerable.
- **Explicitly out:**
  - **Any specific trend report.** No "who improved", no "injury watch", no standings-over-
    time page. Designing the trend surface before the GM has ever read a second snapshot
    and said what it wanted would be guessing, and this project's whole method is to let
    the GM hit the limit of thin sight first.
  - **Silver or gold modelling.** Conforming, deduplicating or restating across snapshots is
    a layer this request does not build.
  - **Retention or pruning policy.** How long snapshots are kept, and whether `bronze_name`'s
    264,095 rows per landing eventually get compacted, is a separate decision —
    [ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md) already
    records the disk cost as knowingly accepted.
  - **Simming the managed league.** `OOTP-AI` is not a test fixture; advancing it is a real
    front-office act. All work here runs against the disposable twin.
  - **Anything that writes to a save.** Unchanged and permanent
    ([ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md)).
- **Not now / later:** a GM-facing "what changed" report, once the GM has read a second
  snapshot and said what it actually needs; automating the operator's loop; landing the
  managed league at a second date, which happens naturally when the season starts.

> **Amendment 2026-08-30 — the vehicle now exists, and this request drives it.**
> [`ingest-command`](../_done/ingest-command/) shipped `uv run python -m ootp_ai.ingest land`,
> which is the invocation the sim-forward procedure is written against. The boundary
> between the two requests is a **status verb**: `ingest-command` built the act of landing
> and stops there; everything about *sequencing* landings — simming forward, the two-date
> proof, answering "what dates does this save hold" — is this request's, unchanged.
>
> Four things it pinned that this request should not renegotiate, only consume: the
> invocation string above; the flags `--save-id`, `--json`, `--new-look` and
> `--from-snapshot`; the exit codes (0 landed, 1 refused by name on stderr, 2 the command,
> `.env`, or the warehouse `.env` names is wrong — an unreachable MySQL included); and the
> `--json` payload, whose key set is owned by `INVOCATION`'s module as `JSON_KEYS`.
>
> **The discriminator is `verdict`, and its vocabulary is closed.** A successful landing
> carries one of `no-prior` · `changed` · `new-look` · `from-snapshot` (the module's
> `LandingVerdict`); the refusal path emits a `{"verdict": "unchanged", …}` envelope on
> stdout with the exception name on stderr and exit 1, so a driver never has to parse
> prose. Alongside it, **`reason`** carries *why* the pre-flight decided the save had
> moved — e.g. `"players.dat is 32,078,633 bytes against 32,070,091 landed"` — and is
> `null`, never absent, on the three verdicts where no comparison was made.
>
> Re-running against an unchanged save already refuses before anything is copied, so the
> procedure does **not** need to guard against that itself. One thing it *should* know:
> the landed sequence is `max(snapshot_dir_seq, warehouse_max_seq + 1)` and is passed
> explicitly, so a lost race surfaces as `IngestRunExists` rather than as a retry —
> re-running the command recovers it, because the maximum is re-read.

## Affected Area & Pointers

**Subsystem:** `src/ootp_ai/` (warehouse loading and a new or extended read path) plus
`tests/`. No parser change — this reads what walkers already produce.

A cold scoping agent should open, in this order:

| # | File | Why |
|---|---|---|
| 1 | [ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md) | The governing decision. Note its *"What it forecloses"*: **"Any future silver or gold model must resolve a sequence explicitly"** — this request is the first consumer that clause was written for |
| 2 | `tests/test_snapshot_semantics.py` | The existing multi-snapshot proofs and the exact shape of the gap. `test_a_landing_at_another_sim_date_is_left_untouched` is the test that skips; `test_two_sequences_of_one_sim_date_both_persist` is what the time-axis version should look like |
| 3 | `src/ootp_ai/reports/resolve.py` | `resolve_snapshot()` and `landed_sim_dates()` — the current one-triple resolver and the likely seam |
| 4 | `src/ootp_ai/warehouse/load.py` `:195` | `land_snapshot()` — how a landing is claimed and written |
| 5 | `src/ootp_ai/validate/export_diff.py` | Existing per-field comparison machinery, built for a different right-hand side |
| 6 | `src/ootp_ai/contracts/tables.toml` | The eight declared tables and their keys — every one carries the triple |
| 7 | `tests/fixtures/warehouse.py` `:99` | `purge_snapshot()` — how a test landing is cleaned up, which a two-date test will need |
| 8 | [ADR 0005](../../../docs/decisions/0005-hybrid-data-layer.md) | The medallion split, and the rule *"does this artifact change when the league is simulated?"* — cross-snapshot facts are definitionally the **yes** side |

Also relevant: `first-sight`'s §2.5 (the three saves and what each can prove) and Phase 10's
`IMPLEMENTATION_REPORT.md`, which records this gap as follow-up 1.

## Data Contracts

This adds no new landed dataset — it reads the eight that exist. But a cross-snapshot read
path has contracts of its own, and scoping should settle them rather than let them emerge:

- **Grain of a difference.** One row per *what*? Per changed field, per changed entity, or
  per entity-with-a-changed-field? These are three different answers and the choice decides
  what a consumer can ask.
- **Which snapshots are comparable.** Two triples of the same `save_id` obviously. Across
  `save_id`s — never, or with a stated caveat? **`names.dat` is fixed-size and per-save
  populated** (scope SD-10): the same name index resolves to different strings in different
  saves, so a cross-save comparison of name-bearing columns is confidently wrong rather than
  merely imprecise.
- **What "changed" means for a row that appears in only one snapshot.** A drafted player, a
  released one, a club that gained an affiliate. Structural absence again, and this project's
  rule is that absence is never zero.
- **Whether the read path resolves `max(ingest_seq)` or demands an explicit one.** ADR 0021
  says a consumer must resolve a sequence explicitly; the roster report defaults to the
  latest and *states* what it read. Which convention governs here is a decision.
- **Cost.** The two-snapshot comparison runs over `bronze_name`'s ~264,095 rows per landing
  unless deliberately excluded.

## Constraints / Non-negotiables

- **The game is read-only** ([ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md)).
  Nothing here sims, writes or automates. The sim step is the operator's, always.
- **Bronze is append-only and immutable per triple**
  ([ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md)). No upsert, no
  fix-in-place. A correction is a new landing.
- **The GM reads reports, never a query**
  ([ADR 0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md)). Whatever this
  builds is infrastructure the umpires and future reports consume — it is not a GM-facing
  surface, and if it ever becomes one that is a report, gated like any other.
- **Every landed value reaching a page routes through `contracts/policy.py`.** If any part of
  this renders, the serving gate applies unchanged.
- **Grain declared in prose *and* enforced by a test, and the two must agree.**
- **A test must not pass by skipping.** The defect being fixed here is precisely a guard that
  reports success when it had nothing to look at, so any new proof must construct its own
  preconditions.

## Open Questions for Scoping

1. **Does this pull dbt in, or honour the deferral?**
   [ADR 0005](../../../docs/decisions/0005-hybrid-data-layer.md) assigns snapshot facts to a
   dbt medallion and puts cross-snapshot conforming squarely in **silver**;
   [ADR 0004](../../../docs/decisions/0004-mysql-warehouse.md) §Notes defers dbt, and
   `first-sight` Phase 12 is scheduled to record that deferral formally. This request is the
   strongest trigger yet. **Left open deliberately** — it touches two settled ADRs and is
   exactly the call the scoping panel exists to weigh. *(Operator's disposition at intake:
   record it, don't pre-decide it.)*
2. **Where does a cross-snapshot read path live?** `reports/` is wrong if it is not a report.
   A new `src/ootp_ai/compare/`? An extension of `validate/`? CLAUDE.md forbids speculative
   directories, so this needs deciding rather than defaulting.
3. **Is `export_diff.py` reused, extended, or left alone?** It does the right *shape* of work
   and was built for a different purpose. Reuse risks contorting a validation module into a
   general comparison engine; not reusing risks two per-field differs.
4. **How does the second snapshot get created in a test?** Landing the same parsed snapshot
   under a different `sim_date` is easy and fake — the bytes are identical, so nothing
   actually changed. A genuine second date needs the operator to have simmed. Does the
   automated test use a synthesised second date, with the real one covered by a USER-RUN
   check? That split has precedent (AC11 and AC21 are deliberately redundant) but should be
   chosen, not stumbled into.
5. **What is the smallest useful difference output?** Row counts per table would be trivial
   and nearly useless; per-field differences across ~300,000 rows is a lot of output nobody
   reads. Where between those does this land?

## Stage plan

**Full pipeline.** All three hard triggers fire, and any one of them would be enough:

1. **Open Questions is non-empty** — five of them, including one that turns on two settled
   ADRs.
2. **Explicitly out is filled**, so this trigger is *cleared* — but it does not save the
   others.
3. **It touches things expensive to reverse.** ADR 0021's append-only guarantee, the dbt
   deferral recorded against ADR 0004, ADR 0005's medallion split, and a new read-path
   contract that later reports and the GM's own history would pin.

No skip is available and none is proposed.
