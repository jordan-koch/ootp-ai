# 0021 — Bronze landing is append-only; a landed snapshot is never modified

**Status:** Accepted
**Date:** 2026-08-19

## Context

This project exists to test whether an AI front office makes good decisions. That question
is only answerable after the fact, and only if the state each decision was made from
survives — so the warehouse is not merely a cache of the current league. It is the record
against which a past decision is re-examined.

[ADR 0018](0018-retention-is-infrastructure.md) established that retention is
infrastructure. This is the storage rule that follows from it, and it was forced by a
collision the `first-sight` plan found before any code existed. The scope demanded that
loading the same snapshot twice leave row counts and checksums unchanged. An append-only
run table adds a row and a wall-clock column breaks bit-identity, so the two clauses
cannot both hold under any keying that treats a re-load as an update. An implementer who
does not notice writes a test that cannot pass.

The obvious fix — key on `(save_id, sim_date)` and refuse a re-land — is worse, because it
blocks a legitimate and frequent operation. The operator executes a GM action on
2024-03-07, signs a free agent, and wants to prove it landed. **The sim date has not
moved.** Same key, different bytes. The same wall is hit when a parser fix means re-reading
a date already ingested. Under that key the pipeline refuses the exact request the project
most needs to serve: the club immediately before and immediately after an executed
decision, side by side.

There is a second reason not to reach for an update path. `.claude/agents/data-engineer.md`
makes a snapshot immutable on the filesystem side, and the warehouse is rebuildable from a
snapshot while a snapshot is not rebuildable from the game — Challenge Mode has no undo.
If the two disagree, the snapshot is right. That triage only works if the warehouse cannot
have been edited in place.

## Decision

**`(save_id, sim_date, ingest_seq)` is immutable once written, and nothing in
`src/ootp_ai/warehouse/` may modify or remove a landed row.**

Three parts, and the third is what keeps the first two true:

1. **Re-landing an already-landed triple refuses loudly** (`IngestRunExists`), naming the
   triple. Nothing is ever overwritten, so *"loading the same snapshot twice leaves row
   counts and checksums unchanged"* holds trivially rather than by comparison — the second
   attempt never writes.
2. **A new look at an already-ingested `sim_date` allocates the next `ingest_seq`** and
   lands a fresh row set alongside its predecessor. `ingest_seq` is a monotonic integer per
   `(save_id, sim_date)` starting at 1, and it joins every bronze primary key. This
   *preserves* immutability rather than trading it away.
3. **The warehouse package holds no `DELETE`, `UPDATE`, `TRUNCATE`, `DROP` or upsert
   path**, and an AST scan over `src/ootp_ai/warehouse/` asserts it. Tests that need to
   clean up after themselves write their own statement, under `tests/`, where it is
   visible. A convenience `purge()` added to the loader because a script needed it is
   precisely how this property stops being true, and the scan is what makes adding one a
   decision rather than a diff.

A correction is therefore **a new landing, never an edit**. A parser fix re-lands the same
snapshot at the next sequence, and both readings stay on disk — which is the honest record
of what was believed when, and is what a differential harness compares.

## Consequences

**What this buys.** The pre-action and post-action states of one in-game date are both
retrievable, which is evidence this project specifically exists to collect and which cannot
be reconstructed after the fact. A `gm/decisions/` record citing a report can be checked
months later against rows that have not moved. Warehouse-versus-snapshot disagreement stays
decidable. And AC10's four clauses stop fighting each other: byte-identity across a repeat
load is a consequence of the refusal rather than a separate thing to engineer.

**What it costs, and the largest cost is unglamorous.** `bronze_name` re-lands **264,095
rows per save per snapshot** even though `names.dat` is fixed-size and its record bodies
are byte-identical across saves — measured. Uniform bronze grain was judged worth the disk;
the per-snapshot digest is recorded in the ingest-run row so a later slice can prove
immutability and de-snapshot that one table cheaply. Storage grows monotonically and
nothing here reclaims it: **no retention policy exists**, and dropping old sequences is
future work that will need its own argument. A wrong parse's rows stay landed forever,
superseded rather than repaired, so a reader must know to resolve to `max(ingest_seq)` —
reports do so by default and state on line one which sequence they read.

**What it forecloses.** No upsert, no "fix it in place", no idempotent re-run that quietly
rewrites. Any future silver or gold model must resolve a sequence explicitly rather than
assuming one row per `(save_id, sim_date)`; a query that omits `ingest_seq` reads an
ambiguous grain the moment any date is ingested twice. That is a real ergonomic tax, paid
deliberately.

**What it does not claim.** The scan judges string literals handed to a call inside one
package. SQL assembled from fragments, bound to a module constant and executed later, or
issued by a future package outside `warehouse/` is invisible to it — and MySQL itself
enforces nothing here, so an operator at a client can delete whatever they like. The
categorical protection is the primary key, which turns a colliding write into an error
rather than an overwrite; the scan is the mechanical backstop under a convention, not a
proof.
