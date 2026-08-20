> **Status:** scoped · created 2026-08-19 · decided · next: plan

# Project Scope — Open the Front Office

## Fit Verdict

**Reshape.** All three scopers returned `reshape` independently, for the same three grounded
reasons, and the operator accepted it.

**What fits cleanly.** [`contracts/tables.toml`](../../../src/ootp_ai/contracts/tables.toml) and
[`field_map.toml`](../../../src/ootp_ai/contracts/field_map.toml) are already one declaration with
several consumers, and [`contracts/policy.py`](../../../src/ootp_ai/contracts/policy.py)'s
`column_disposition` already decides per column and fails closed on an unrecognised category.
[`warehouse/ddl.py`](../../../src/ootp_ai/warehouse/ddl.py) already emits schema *from* that
declaration, connects to nothing, routes every identifier through
[`warehouse/sql.py`](../../../src/ootp_ai/warehouse/sql.py)`::quote_ident`, and refuses a vocabulary
it has fallen behind. A view emitter is a fourth consumer written the same way.
[`ops/mysql-bootstrap.sql`](../../../ops/mysql-bootstrap.sql) is already the tracked, public home for
database-scoped grants with no GRANT OPTION. The governance half — supersede, amend, rewrite the
rulebook — is exactly what the repo's supersede-never-delete convention is built to absorb.

**Why it could not be built as written.** Three findings, each measured against the repo:

1. **The path-scoped write grant does not exist.**
   [`.claude/agents/README.md`](../../../.claude/agents/README.md) states it plainly: the harness
   gates *which tools* an agent holds — real and enforced — but nothing gates *which paths* those
   tools may touch, so a write allowlist in an agent definition is prose. A `Write` grant would put
   the GM's pen in the same tree as [`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md),
   [`.claude/agents/gm.md`](../../../.claude/agents/gm.md) and the tests pinning its own grant —
   prose protecting a *larger* capability than the prose it replaces, inside a request whose thesis
   is that prose failed.
2. **There is no query vehicle in the repo today.** Verified: no `.mcp.json`, no
   `.claude/settings.json`; `.claude/` holds only `agents/` and `skills/`. The only shipped SQL path
   is a `Bash` grant, which reaches `.env`, `players.dat`, the writable warehouse and
   `ootp_truth_real` — which [`ops/mysql-bootstrap.sql`](../../../ops/mysql-bootstrap.sql) grants the
   application user ALL PRIVILEGES on. Strictly worse than the status quo it would replace.
3. **Two settled-ADR collisions the request did not name.** Generating serving views from
   `contracts/` is [ADR 0004](../../../docs/decisions/0004-mysql-warehouse.md) §Notes option 2 ("keep
   MySQL, drop dbt — hand-rolled SQL plus a thin runner") landing in
   [ADR 0005](../../../docs/decisions/0005-hybrid-data-layer.md)'s dbt serving slot; and
   `field_map.toml`'s `name_category` entry pre-registers an `unclassified` category belonging to
   "whoever revisits ADR 0012" — which this request is, while declaring 0012 out of scope.

**The reshape.** Split into a **Phase A that ships unconditionally** (the ADRs, execution log,
journal, trigger loop, guards, context assembler, doc rewrites) and a **Phase B gated on a
tool-channel spike** (`gm_view`, the grant, the GM query tool). Convert the GM's write channel from
a path-scoped `Write` grant into a **typed umpire-side lander** — which keeps
[ADR 0017](../../../docs/decisions/0017-gm-is-a-subagent.md)'s pen-holding intact *and* makes
append-only mechanically true, because the only writer is code that can only append.

Not `poor` — the governance argument is legitimate and the infrastructure goes with the grain.
Not `clean` — half the enforcement story was prose about a capability nobody had checked.

## Problem

The GM apparatus was built to test a hypothesis the operator does not hold.
[ADR 0013](../../../docs/decisions/0013-action-economy.md) (action economy),
[0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md) (report wall) and their pricing
patches [0018](../../../docs/decisions/0018-retention-is-infrastructure.md) and
[0019](../../../docs/decisions/0019-reading-costs-an-action.md) simulate a *human* front office's
attention scarcity, treating a tireless analyst as an advantage to be metered away. The operator's
actual claim under test is whether robust data infrastructure plus an adaptive agent can be
competitive in a league it cannot cheat in — with the agent's tirelessness as the independent
variable rather than a confound. How OOTP's own AI budgets its attention is deliberately not this
project's concern.

Four costs follow, each felt before a single game has been played: adjudication overhead compounds
(three ADRs and one ledger row); a flat weekly budget with expiry is the wrong shape for a bursty
season; a per-invocation subagent with no write channel has no time horizon while being graded on
multi-year outcomes ([ADR 0015](../../../docs/decisions/0015-gm-is-employed-not-appointed.md)); and
the wall is coarser than the machinery beneath it — `column_disposition` already decides
releasability per column and fails closed, yet 0017 enforces
[ADR 0012](../../../docs/decisions/0012-scouted-ratings-only.md) by removing all database access,
protecting the answer key by forbidding the entire library.

## Goals / Non-Goals

**Goals**

1. Retire the attention-scarcity apparatus outright — supersede 0013 and its pricing patches
   0018/0019 — so no future information channel needs its own pricing ruling.
2. Replace the report wall with a **schema boundary**: a `gm_view` schema generated from
   `column_disposition` over the declared tables, so a withheld column is physically absent from the
   GM's schema rather than declined by prose.
3. Make ADR 0012's withhold-by-default posture **strictly stronger** at the handover: the same
   fail-closed function that gates a report page gates the SELECT list, backed by the
   `WITHHELD_NAME_FRAGMENTS` text-level backstop over emitted SQL and a live-schema diff.
4. Create a restricted MySQL user with SELECT on `gm_view.*` and nothing else, so that even if every
   prose rule failed the connection cannot reach `ootp`, `ootp_dev`, or `ootp_truth_real`.
5. **Prove, before committing to the grant**, that a `gm`-shaped subagent can hold a query tool that
   reaches the restricted schema, takes no caller-supplied connection parameters, and is grantable
   in `tools:` frontmatter without also granting `Bash`. If it cannot be proven, the grant half does
   not ship and the retirement half still does.
6. Give the GM a durable, tamper-evident memory it authors and can never revise — one append-only,
   hash-chained journal carrying notes, dated triggers and pre-registered claims, plus an execution
   log — so an April belief survives contact with July results.
7. Close the trigger loop mechanically: a note written at sim date N is served back at N+k by a pure
   function over the journal, with nobody remembering to look.
8. Replace the action ledger with an execution log whose only subject is what the operator actually
   did — proposed / executed / deferred / declined, each with a reason — preserving *declare before
   doing* (0013's surviving core) and 0019's refusal loop (its durable half).
9. Pin the GM's tool grant in CI. Measured: zero tests under `tests/` reference
   [`.claude/agents/gm.md`](../../../.claude/agents/gm.md) today.
10. Land the ADR record with the repo's career-record discipline — supersede and amend by writing new
    ADRs and adding supersession blockquotes, never deleting text, with
    [`docs/decisions/README.md`](../../../docs/decisions/README.md)'s status table kept in step and
    asserted by a test.
11. Give explicit written dispositions to the three pinned requests — [first-sight](../first-sight/)
    Phases 10–13, [gm-inbox](../gm-inbox/), [news-subscription-dial](../news-subscription-dial/).

**Non-Goals**

1. A `Write` or `Edit` grant for the GM at any path scope. The harness cannot enforce path scoping.
   The umpires keep the pen; the GM's return envelope is its authorship.
2. Any change to ADRs 0012, 0015, 0003, 0001, 0021 or 0006. In particular **no `unclassified`
   category is added to `field_map.toml`'s vocabulary in this slice**, even though the
   `name_category` entry invites it — the deferral is stated in the new ADR rather than left silent.
   **One measured exception is forced and must be handled rather than declared away:** ADR 0012's
   Buys section contains a clause reading *"Combined with ADR 0013, scout quality becomes measurable:
   actions spent, outcomes returned"*. Retiring 0013 invalidates a clause of an ADR this scope calls
   untouched. It is resolved by **annotation, not edit** — 0022 records that 0012's measurability
   claim now rests on the execution log's token/wall-clock denominator, and 0012 receives the
   standard amended-in-effect blockquote at its head, the same shape 0016 already carries. No line of
   0012's body changes.
3. Widening what the parser reads. No new `.dat` file, no new field, no change to `SNAPSHOT_FILES`.
4. Landing ratings of any kind. This slice builds the wall in advance and says so.
5. Reconstructing true ratings from observables. ADR 0014's surviving core stands.
6. A condition-evaluating trigger engine. Dated one-shots only.
7. Building analytics, models, advisors or reports *for* the GM.
8. Introducing dbt. ADR 0004's dbt question is **forced** by this work but not answered by it — the
   scope appends to 0004's Notes rather than resolving the adapter choice.
9. Silver or gold layers, or any reshaping transformation in `gm_view` beyond disposition filtering,
   `save_id` pinning and `max(ingest_seq)` resolution.
10. A general shell or a general database tool for the GM.
11. Rewriting or absorbing first-sight Phases 10–13.
12. Migrating `gm/ledger.jsonl` seq 1 into the new execution log.
13. A warehouse retention policy or any pruning of landed snapshots.
14. Writing the GM's baseball content — the competitive window, the first plan, the first
    predictions. **The apparatus lands empty and the GM fills it.**
15. Fixing [`tests/test_no_leaks.py`](../../../tests/test_no_leaks.py)'s general credential coverage —
    [secret-scanning](../secret-scanning/) owns that.

## Acceptance Criteria

Every criterion is tagged by phase. **Phase A's set is complete and sufficient on its own** — a
Phase-A-only ship is a defined, acceptable end state.

### Phase A — ships unconditionally

1. **[A] OFFLINE** — every append-only file under `gm/` verifies as a hash chain in a pure pytest
   with no git history and no network: each entry's `seq` is the prior entry's `seq` plus one and its
   `prev` equals the SHA-256 of the prior line's exact bytes, with line 1 carrying `prev: null`. The
   suite includes a fixture whose middle entry has been retroactively edited, and **that fixture must
   go red**. (Chosen because `.github/workflows/ci.yml` pins `fetch-depth: 1`, so a merge-base prefix
   check cannot run today, and `merge=union` does not preserve base-as-prefix anyway.)
2. **[A] OFFLINE** — trigger round-trip against a temporary `gm/` root, no MySQL and no save: a
   trigger written at sim date N with `resolve_by` = N+k is ABSENT from the assembled context at
   N+k-1, PRESENT at N+k, PRESENT still at N+k+1 while its disposition is unrecorded, and absent once
   closed with a disposition. All four assertions in one test.
3. **[A] OFFLINE** — the context assembler exits non-zero, naming the entry `seq`, when a fired
   trigger has no disposition recorded; and no journal entry carries both a `claim` and a
   `resolution`, with every entry bearing a `resolution` carrying `author: "umpire"` — the mechanical
   half of ADR 0015 surviving, so the GM cannot grade its own homework.
4. **[A] OFFLINE** — every line of every `gm/*.jsonl` artifact validates against its declared
   envelope, with an unknown key, a missing required key and a wrong scalar type each failing,
   reported per file per line number rather than as one boolean; each artifact's declared key is
   unique across the file; and the prose grain sentence in [`gm/README.md`](../../../gm/README.md)
   resolves to that same key list — the prose-versus-key agreement
   [`contracts/loader.py`](../../../src/ootp_ai/contracts/loader.py)`::_check_grain_matches_key`
   already enforces for bronze, applied to GM memory.
5. **[A] OFFLINE** — no tracked file under `gm/` contains a row of OOTP player data. A journal or
   execution entry referencing warehouse content carries a query string and a
   `(save_id, sim_date, ingest_seq)` triple; the envelope validator refuses an entry whose body
   matches the result-set shapes the guard enumerates.
6. **[A] OFFLINE** — `uv run pytest tests/test_agent_contract.py -k gm` is green:
   [`.claude/agents/gm.md`](../../../.claude/agents/gm.md)'s YAML frontmatter `tools:` value parses
   to an exact expected list string-for-string, and `Bash`, `Write`, `Edit`, `Task` and
   `NotebookEdit` are asserted ABSENT by name. Net-new coverage — measured, zero tests reference
   `gm.md` today.
7. **[A] OFFLINE** — while Phase B has not shipped, the same guard asserts `gm.md`'s `tools:` value
   is **unchanged** (still exactly `Read, Glob`), so the retirement half cannot silently widen the
   grant.
8. **[A] OFFLINE** — a doc guard asserts the retired rules survive ONLY as history:
   [`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md),
   [`.claude/agents/gm.md`](../../../.claude/agents/gm.md),
   [`gm/README.md`](../../../gm/README.md) and
   [`gm/standing-orders.md`](../../../gm/standing-orders.md) contain no live statement of "6 actions
   per in-season week" or "commissioning a report costs an action"; ADRs 0013, 0018 and 0019 each
   still exist on disk, each carries a `**Status:** Superseded by <n>` line, and the matching row in
   [`docs/decisions/README.md`](../../../docs/decisions/README.md) says the same thing — both parsed,
   so a supersession recorded in one place and not the other is red. **ADR 0016 is asserted *amended*
   rather than superseded in Phase A** (its pricing is retired; its report channel stands until
   Phase B replaces it).
9. **[A] OFFLINE** — every execution-log row carries a token count and a wall-clock field, asserted
   present and numeric by the envelope validator. This is the replacement denominator for the
   retired action economy and it ships unconditionally, not behind the gate.
10. **[A] OFFLINE** — `uv run pytest -m 'not gamedata'` passes with no game install and no MySQL;
    `ruff check .`, `ruff format --check .` and `uv run mypy` are clean. Specifically green:
    `test_repo_structure.py::test_every_adr_is_indexed` and `::test_adrs_are_sequentially_numbered`
    with the new ADRs numbered consecutively from 0022;
    [`tests/test_doc_links.py`](../../../tests/test_doc_links.py) over every rewritten `.md`;
    [`tests/test_no_leaks.py`](../../../tests/test_no_leaks.py) over the new `.jsonl` files with a
    positive sample added to `test_patterns_still_catch_real_leaks` and a negative sample proving it
    does not fire on the repo's own prose.
11. **[A] USER-RUN** — the operator confirms by hand that `OOTP-AI.lg`'s file set, sizes and
    modification times are unchanged after a full weekly cycle including memory landing, and that no
    pre-existing line of any `gm/` file changed in the resulting diff. ADR 0001 and the append-only
    claim, checked by the one party that is not the code being audited.

### Phase B — gated on the tool-channel spike

12. **[B] OFFLINE** — `uv run pytest tests/test_gm_view.py -m 'not gamedata'` is green with no MySQL.
    Fed **synthetic** contracts containing (a) a `rating-true` column, (b) a `rating-scouted` column
    labelled `unconfirmed`, (c) a column whose category is absent from `policy.KNOWN_CATEGORIES`, and
    (d) a proven `identity` column, the emitted `CREATE OR REPLACE VIEW` text contains the name of
    (d) and NONE of (a), (b), (c) — asserted per column BY NAME with mismatches enumerated, never as
    a count. **The synthetic half is load-bearing**: measured, the shipped declaration has zero
    `rating-scouted` fields and one landed withheld column, so a test over real contracts alone would
    pass on a schema with nothing to withhold.
13. **[B] OFFLINE** — over the real shipped declaration, in two parts, **with no pinned scalar
    count**. *Part one, an invariant that survives new columns:* for every table that has an emitted
    view, the set of view columns sourced from declared columns equals exactly the RENDERABLE set for
    that table, asserted by name with mismatches enumerated. *Part two, a frozen exception ledger
    asserted by name:* the tables deliberately not served (`bronze_name`, with its reason), the two
    non-renderable landed columns (`bronze_name.name_category` withheld,
    `bronze_league_event.real_sim_date` uncertain), and every view column that is a derived
    expression rather than a declared column (the resolved name), each with the argument for its
    presence — the same `LANDED_BUT_WITHHELD` / `LANDED_UNDER_BANNER` discipline
    [`tests/test_withheld_fields.py`](../../../tests/test_withheld_fields.py) already uses.
14. **[B] OFFLINE** — the view emitter RAISES on a `Disposition` member it does not handle, mirroring
    `warehouse/ddl.py::_check_every_declared_type_is_renderable` and
    `contracts/policy.py::check_policy_covers`. A test introduces an unhandled disposition and
    asserts the raise, not a silent pass-through.
15. **[B] OFFLINE** — no emitted view SQL string contains any fragment in
    `contracts.policy.WITHHELD_NAME_FRAGMENTS` (`prone_`, `players_value`, `_talent_`): a text-level
    backstop over the generated statements.
16. **[B] OFFLINE** — every emitted `CREATE ... VIEW` body references **exactly one schema**, the
    configured warehouse schema, asserted by parsing qualified identifiers out of the generated text,
    with `ootp_truth_real` and the truth-database `.env` value named as forbidden literals; and every
    statement carries an **explicit, pinned `DEFINER` / `SQL SECURITY` clause** rather than relying on
    the server default. (`SQL SECURITY INVOKER` breaks read-through entirely, so DEFINER is required
    and must be a deliberate, tested choice.)
17. **[B] GAMEDATA** — the definer-rights read-through and the `SHOW VIEW` privilege behaviour are
    **measured on a real connection before the ADR states its enforcement claim.** MySQL view
    privilege semantics are `assumed`, not verified, and this repo has already been burned once by an
    obviously-true MySQL belief.
18. **[B] GAMEDATA** — `uv run pytest -m gamedata tests/test_gm_grant.py` is green. Connecting as the
    restricted GM user, EACH of the following is enumerated by name and raises a MySQL access-denied
    error (1044/1142): `SELECT 1 FROM ootp.bronze_player`, `SELECT 1 FROM ootp_dev.bronze_player`,
    `SELECT 1 FROM ootp_truth_real.players_scouted_ratings`, `SELECT 1 FROM mysql.user`, an INSERT
    into a `gm_view` view, an UPDATE, a DELETE, and a CREATE TABLE in `gm_view`; **and** a SELECT
    against every emitted view succeeds. The positive clause matters — the negative half alone would
    pass on a user with no grants at all.
19. **[B] GAMEDATA** — querying `information_schema.columns` as the restricted user returns ZERO rows
    for `table_schema IN ('ootp','ootp_dev','ootp_truth_real')`, and
    `SELECT @@session.transaction_read_only` returns 1, read back and asserted rather than assumed —
    the same proof [`src/ootp_ai/db.py`](../../../src/ootp_ai/db.py) already performs.
20. **[B] GAMEDATA** — for every emitted view, `COUNT(*)` equals
    `COUNT(DISTINCT <declared bronze key minus ingest_seq>)` per `(save_id, sim_date)`; the
    `ingest_seq` each row carries equals `MAX(ingest_seq)` for its `(save_id, sim_date)`; and every
    row's `save_id` equals the single configured managed save.
21. **[B] OFFLINE** — the query tool's public entry point exposes no `host`, `user`, `password`,
    `database` or DSN parameter, asserted by signature inspection. This is what makes the GM's ability
    to `Read` the repo-root `.env` harmless: **a credential it can read is a credential it cannot
    use.**
22. **[B] USER-RUN** — a cold session spawns the `gm` subagent with only the assembled weekly context
    and its granted tools. It answers one named baseball question by issuing at least one query
    itself; the executed SQL is present in the query log; its returned handoff names the view it read
    and cites the `(save_id, sim_date, ingest_seq)` triple its answer resolved to; and no roster or
    club fact appears under `## assumed`. Marked user-run — "answered it well" is a judgment the
    acceptance panel must not claim.

## Scope (tiered)

### Core (must)

**PHASE A — ships unconditionally.**

- **A1 — THREE ADRs across two phases, split along the dependency boundary.** Numbered consecutively
  (`test_adrs_are_sequentially_numbered` forbids gaps, so the Phase B number **must not be reserved
  in advance**). **0022 = the attention model**: supersedes 0013 and retires 0018/0019's pricing while
  re-homing 0018's retention-is-irreversible / foresight-trap argument and 0019's feed-vs-warehouse
  insight and refusal loop; **amends** 0014 to sensor-vs-processing; **amends** 0016 to retire report
  *pricing* while leaving its report *channel* standing. **0023 = the memory model**: append-only GM
  authorship, the execution log, the trigger loop, and 0017's no-write foreclosure narrowed to a
  typed lander. Both depend on nothing. Each opens with a pointer to the other. Both carry an
  explicit Costs section recording that **nothing now bounds GM deliberation** (0013's Buys claimed
  "roughly 200 staff engagements per season rather than an open-ended optimization budget") and that
  instrumentation measures rather than bounds.
- **A2 — the execution log.** Close [`gm/ledger.jsonl`](../../../gm/ledger.jsonl) with a note in
  [`gm/README.md`](../../../gm/README.md) — seq 1 stays where it is; its `free` ruling under a retired
  model is the one piece of history the repo has. Open `gm/execution-log.jsonl` at seq 1 with a
  declared schema: `seq`, `prev` (hash), `sim_date`, `what`, `proposed_by`, `disposition` in
  {executed, deferred, declined, superseded}, `reason` (mandatory, non-empty on `declined`),
  `supersedes`, plus the token and wall-clock fields. Re-point
  [`gm/standing-orders.md`](../../../gm/standing-orders.md)'s `Established: ledger seq <n>` convention
  at the new file.
- **A3 — the journal, ONE file.** `gm/journal.jsonl`, append-only, hash-chained, umpire-landed from
  the GM's structured return. Envelope: `seq`, `prev`, `sim_date`, `author` in {gm, umpire}, `kind` in
  {note, trigger, claim, resolution}, `subject`, `resolve_by` (nullable sim date), `refers_to`
  (nullable seq), `body`. One schema covers notes, dated triggers, pre-registered claims and their
  umpire-authored resolutions; a trigger's disposition on fire is a NEW entry referring to it, never
  an edit. **Rejected as speculative:** a separate `predictions.jsonl` — a second schema and a second
  guard for zero capability.
- **A4 — the write mechanism, RESHAPED.** The GM emits journal / trigger / claim / execution entries
  inside its return contract as a machine-parseable block; a typed lander under `src/ootp_ai/`
  validates the envelope and appends. Keeps ADR 0017's pen-holding intact and makes append-only
  **mechanically** true, because the sole writer is code that can only append. 0023 states plainly
  that this is a partial concession on the request's enforcement-by-grant theme, and why.
- **A5 — the guards.** `tests/test_gm_memory.py`: hash-chain integrity (with a red fixture proving it
  fires), the trigger round-trip, the no-self-resolution assertion, and per-line envelope validation —
  all pure functions over fixture files so they run offline at `fetch-depth: 1`. **Resolve the
  `.gitattributes` collision explicitly:** `merge=union` and a hash chain are incompatible (union
  interleaves and would break `prev` links; it also silently drops byte-identical duplicate lines), so
  the new files take **no** union driver and a conflict is the honest outcome for a single-operator
  repo — reversing a convention `gm/README.md` documents as deliberate, and saying so.
- **A6 — the agent-contract guard.** Extend
  [`tests/test_agent_contract.py`](../../../tests/test_agent_contract.py), today scoped to
  `data-engineer.md` alone, to parse `gm.md`'s frontmatter and assert its exact `tools:` set with the
  dangerous grants named as forbidden. Lands in Phase A even though the grant does not widen until
  Phase B — **it is the test that makes Phase B's widening reviewable.**
- **A7 — the context assembler as a MODULE** under `src/ootp_ai/`, invoked by a thin skill. Reads
  `gm/` and returns the invocation context (charter, triggers due at this sim date, standing refusals,
  standing orders, a one-line index of journal and decisions with pull-on-demand). In code because it
  carries the trigger round-trip and fired-without-disposition criteria, and a procedure written in
  prose cannot be asserted. Resolves the current sim date **from the ingest run, never wall-clock**.
  This is the first programmatic consumer of `gm/`.
- **A8 — doc rewrites, each in the same commit as its guard.** The surface is **wider than the
  request estimated**; the adversary re-derived it and the list below is the corrected one.
  `FRONT_OFFICE.md`: the four-constraint table's "Pause time" row, the whole `## The action economy`
  section, `## What you are allowed to see`, and the retired bullets under `## Decisions already
  made` — **at least eight statements break, not four**, so the rewrite is costed against a full
  read rather than a spot edit. `.claude/agents/gm.md`: the forced-read list (item 3 currently sends
  the GM to a file about to close), the return contract's `## period` section and its
  `proposed: cost|free` / `precedent` fields, and the prohibitions. `gm/README.md`: layout,
  career-vs-club table, new schemas, and `### What a period is`, which becomes vestigial.
  `gm/standing-orders.md`: **the whole file, not just its `## Reports` block** — its preamble and the
  `Established: ledger seq <n>` format are equally 0013-priced.
  **[`gm/staff.md`](../../../gm/staff.md) — missing from the request's list entirely**, and its whole
  *"Why this file can exist at all"* section is built on 0013's scarcity denominator plus 0016.
  `CLAUDE.md`: the line naming 0016 as constraining what an agent may query.
  `docs/decisions/README.md`: the status table.
- **A10 — re-home the three surviving mechanics the supersession would otherwise drop by silence.**
  0013's **standing-order lever** (set a policy once, staff apply it free until changed) and its
  **20-proposals autonomy graduation** both retain force under the new model even though the pricing
  does not. 0019's **first limiter** — *"may this analysis exist at all"*, which 0019 describes
  explicitly as structural rather than economic — is enforced by the tool grant and survives the
  other two limiters being retired. Each is re-stated in 0022 or 0023 with its origin cited. The
  request already flagged 0018's foresight trap and 0019's refusal loop; these three were not on
  that list and are the same class of loss.
- **A9 — written dispositions for the pinned work.** **first-sight ships Phases 10–13 as planned
  FIRST**; this request converts its two reports into seed views and reshapes its catalog into the
  served dictionary afterwards. [gm-inbox](../gm-inbox/): one line recording that its ADR 0018 tier-2
  pricing argument evaporates and it becomes a plain parser-widening slice.
  [news-subscription-dial](../news-subscription-dial/): its central gap (the ledger has no vocabulary
  for refusal) is solved for free by the `declined` disposition, so it shrinks to the twelve-category
  inventory plus the subscription-state record.

**PHASE B — gated.**

- **B1 — THE TOOL-CHANNEL SPIKE, a gate rather than a step.** Before any `gm_view` work, prove in a
  throwaway branch that a `gm`-shaped subagent can hold a query tool that (i) executes SQL against a
  restricted schema, (ii) takes no caller-supplied connection parameters, and (iii) is grantable in
  `tools:` frontmatter alongside `Read, Glob` **without** also granting `Bash`. Record the result with
  an epistemic label in `reviews/`. **If the spike fails, Phase B does not ship and Phase A stands
  alone.**
- **B2 — the third ADR**, authored and accepted **only if the spike passes**: supersedes 0016 outright
  and amends 0017's no-DB foreclosure into a scoped grant. If the spike fails, 0016 stands amended-only
  and the honest recorded end state is *better reports under a retired economy*.
- **B3 — `gm_view` generation.** A pure emitter beside `warehouse/ddl.py` turning
  `(Contracts, column_disposition)` into `CREATE OR REPLACE VIEW gm_view.<name>` selecting exactly the
  RENDERABLE columns — withheld columns **absent from the SELECT list**, never nulled or aliased away
  — every identifier through `quote_ident`, connecting to nothing; plus `ensure_views()` beside
  `warehouse/load.py::ensure_tables` as the only thing that touches MySQL. Every view resolves
  `max(ingest_seq)` per `(save_id, sim_date)` and carries a baked `WHERE save_id = <managed>`
  predicate. `bronze_name` is not served raw (264,095 rows per save per snapshot, and it holds the
  single withheld landed column); names resolve into the player view as text.
- **B4 — `Disposition.UNCERTAIN` at the schema boundary: PRESENT, with the label in the alias**
  (`real_sim_date__unconfirmed`), so the banner obligation survives into a surface that cannot render
  banners. The emitter REFUSES an unhandled `Disposition` rather than defaulting, and a test pins it.
- **B5 — THE GRANT.** `ops/mysql-bootstrap.sql` gains a restricted `gm_reader`@localhost with SELECT
  on `gm_view.*` and nothing on `ootp`, `ootp_dev`, `ootp_truth_real` or `mysql`; localhost-bound, no
  GRANT OPTION. **A separate `.env` key names the source schema, and the generator refuses to build
  views over `ootp_dev` at all.** Keys added to `.env.example` with empty values and resolved through
  [`config.py`](../../../src/ootp_ai/config.py)'s existing pattern, reached by exactly one factory
  that asserts a read-only session by reading `@@session.transaction_read_only` back.
- **B6 — the enforcement claim written honestly.** The ADR states in its own text that (a) the
  boundary is only as good as the hand-maintained field map — a rating mislabelled `identity` is
  released with no error surfaced, the correctness trap CLAUDE.md names as the project's most
  dangerous — and (b) measured on the shipped declaration, exactly one landed column is withheld and
  no rating has landed, **so the wall is prospective insurance rather than a tested barrier.**
- **B7 — the query log**, written by the TOOL rather than by the GM: every statement executed, with
  sim date, row count and invocation id, appended to `gm/queries.jsonl`. The audit backstop for
  anything the grant cannot reach.

### Folded in (cheap wins)

1. A `gm_view.withheld_columns` view generated from the same `column_disposition` pass — table,
   column, reason, governing ADR — so the GM prices a gap rather than discovering it by hitting one.
2. A `gm_view.data_dictionary` view served from the already-landed `bronze_field_label`, which carries
   `category`, `epistemic`, `validator` and `source_file` per landed column as of the day it landed.
3. A `_history` sibling per view alongside the latest-resolving default — retention is free under
   0018's reasoning, and this makes the right to look back ergonomic.
4. Emit the `GRANT SELECT ON gm_view.<view>` statements from the same declaration that emits the
   views, and assert applied grants match the emitted set — otherwise a hand-maintained grant list
   fails in the invisible direction.
5. Extend the ADR 0021 mutation scan at `tests/test_bronze_landing.py` to cover `DROP VIEW`, which
   passes today by omission — or house the emitter outside `warehouse/`.
6. A byte-deterministic committed snapshot of the emitted view SQL asserted in CI, the same trick
   first-sight Phase 11 uses on the catalog's structural half: any widening of the GM's schema appears
   as a reviewable diff at `/commit`.
7. A live-schema conformance test (`-m gamedata`) reading `information_schema.columns` for `gm_view`
   and diffing it against `column_disposition` over `load_contracts()` — catches a view hand-created
   outside the emitter.
8. Session guardrails on the GM connection: `MAX_STATEMENT_TIME`, an enforced row cap, and the
   read-back read-only assertion.
9. A worked query cookbook in the GM's forced-read list — resolve the latest seq, diff two seqs of one
   sim date, and the roster fan-out. Not optional: see risk R4.
10. Standing refusals served back at every invocation — `disposition = declined` requires a non-empty
    reason and the assembler surfaces prior declines. Zero new machinery, and it delivers ADR 0019's
    durable refusal loop.
11. One paragraph in first-sight's catalog generator explaining that `gm_view` omits **both** withheld
    and not-yet-landed columns, and pointing at the section that distinguishes them.
12. A dated *what changed* note in `gm/` for the GM's first post-refactor invocation, stating what was
    retired, what survives, and where seq 1's reasoning went. The GM is per-invocation and has no
    memory of the transition.

### Gated — resolved

All ten panel decisions plus the charter question were disposed by the operator on 2026-08-19; see
**Decisions** below.

## Above & Beyond

| Proposal | Tier |
|---|---|
| `gm_view.withheld_columns` — serve the negative space, never the values | cheap fold |
| `gm_view.data_dictionary` from the landed `bronze_field_label` | cheap fold |
| Latest-resolving views (**core**) alongside `_history` views (cheap fold) | core / cheap fold |
| Pin every GM view to the managed `save_id` | **core** |
| A worked query cookbook in the GM's forced-read list | cheap fold |
| Session guardrails — read-only session, statement timeout, row cap | cheap fold |
| A query provenance log — the replacement denominator for the retired economy | **core** |
| Per-invocation token and turn instrumentation | **core** (operator promoted from gated) |
| Emit GRANT statements from the same declaration that emits the views | cheap fold |
| Extend the ADR 0021 mutation scan to cover `DROP VIEW` | cheap fold |
| Byte-deterministic committed snapshot of emitted view SQL | cheap fold |
| Standing refusals served back at every invocation | cheap fold |
| A dated *what changed* migration note for the first post-refactor invocation | cheap fold |
| Hash-chain the append-only files instead of diffing against the merge base | **core** |
| A prediction resolver and a calibration report | deferred |
| A `/gm-week` skill running the whole cycle end to end | deferred |
| Write `gm/charter.md` as part of this work | **deferred** (operator: charter content is baseball content) |
| Mirror the GM's own memory into `gm_view` as queryable views | dropped — premature |
| A decision-replay harness (the "drift ritual") | dropped — zero invocations exist to replay |

## Data Contracts

`gm_view` is a served surface over declared bronze tables, so the five contracts are inherited rather
than invented — but they must be **stated**, because the pipeline README makes them mandatory and the
request left coverage and update semantics blank.

| Contract | Disposition |
|---|---|
| **Grain** | Inherited from each source table's declared grain in `tables.toml`, **minus `ingest_seq`**, which the view resolves rather than exposes as a dimension. A `_history` sibling keeps the full declared grain including `ingest_seq`. Asserted by AC20. |
| **Keys** | The source table's declared key with `ingest_seq` dropped for the latest-resolving view; unchanged for the `_history` sibling. Enforced the way `test_grain_contracts.py` already enforces bronze's. |
| **Coverage** | **One universe only** — every view carries a baked `WHERE save_id = <managed>`, so coverage is the managed save's population, not the warehouse's. Three saves are landed; two are deliberately unreachable. Per-table population statements are carried through from `tables.toml`'s coverage lines, including the structural-absence cases (≈10,700 of 18,072 players carry no roster row). |
| **Update semantics** | **Read-through, not materialized.** Views hold no rows; the underlying bronze remains append-only per ADR 0021, so a view's content changes only when a new snapshot lands. `CREATE OR REPLACE` on regeneration, never `DROP` (see cheap fold 5 — the mutation scan does not currently cover `DROP VIEW`). |
| **Extraction cost** | Zero marginal — no new parsing, no new landing, no new file read. The cost is generation and grant maintenance, both emitted from the declaration. |

**Not settled here, for the plan:** whether the latest-resolving view resolves `max(ingest_seq)` in
the view body or via a generated helper view, and whether `_history` ships in the first Phase B
increment or follows.

## Risks & Unknowns

1. **The enforcement claim rests entirely on an unverified harness capability** — `unconfirmed`, and
   the load-bearing unknown. If a project-scoped query tool cannot be registered and named in `tools:`
   while excluding everything else, the only remaining path is `Bash`, which makes the request's
   central claim false in the most dangerous direction. This is why Phase B is gated on a spike that
   costs about an hour and decides half the scope.
2. **The GM can already read `.env` today, and nobody has written it down.** Measured: `.env` exists
   at the repo root, is gitignored, and the harness has no path-level permission system — so the GM's
   `Read` grant reaches it, and it holds `MYSQL_PASSWORD` and `MYSQL_TRUTH_REAL_DATABASE`. Harmless
   today only because the GM holds no tool that can use a credential; the sharpest hole the moment it
   does. **Pre-existing**, and mitigated by AC21.
3. **The wall guards an empty room today.** Measured: 8 tables, 96 columns, 94 renderable, ONE
   withheld — `bronze_name.name_category`, filed `rating-true` purely to do withhold-by-default duty.
   The field map declares 48 `identity`, 31 `structural`, 10 `rating-true` and **zero
   `rating-scouted`**. An ADR claiming the GM "physically cannot reach a true rating" without stating
   that no true rating is in the warehouse is technically true, rhetorically misleading, and will be
   cited later as though it had been tested.
4. **Grain fan-out will bite a SQL-writing agent on its first query.** `bronze_team_roster`'s grain is
   one row per player per team per roster list per snapshot; Boston at 2024-03-07 resolves to 33/26/30/7
   across four lists for a ~40-man organization, and roughly 10,700 of 18,072 players carry no roster
   row at all. The obvious `JOIN bronze_player ON player_id` produces a silent 2–4× fan-out and "who is
   on Boston's roster" comes back as a confident wrong answer. **The report wall incidentally prevented
   this by putting an author in between.**
5. **There may never be ratings to serve.** `docs/data-access.md` labels as `unconfirmed` whether the
   scouted view is stored at all — if OOTP computes it at render time, the parser cannot reproduce it.
   A GM handed a query tool today can ask about names, ages, handedness, club assignment, roster-list
   membership and division structure, and nothing about how good anyone is. **Expect the first
   querying GM to be underwhelmed; that is not the grant failing.**
6. **Schema-boundary enforcement is only as honest as the field map.** A field mislabelled `identity`
   when it is a rating is released with no error surfaced. The wall moves the enforcement point; it
   does not improve the classification.
7. **Retiring the economy removes the only bound and the only denominator.** Execution is metered under
   the new model; deliberation is not. Deliberate and consistent with the operator's hypothesis, but it
   must be an accepted cost written into 0022's Costs section.
8. **Superseding four ADRs at once risks dropping a load-bearing clause.** 0018 carries the
   foresight-trap argument and 0019 the anti-laundering counterfactual and feed-vs-warehouse asymmetry;
   both retain force even though their pricing does not. **This is the largest governance diff in the
   repo's history.**
9. **The branch is mid-flight self-contradictory.** Rewriting seven docs and two intake requests in step
   means `test_doc_links.py` and any new guard will fire on intermediate commits. Sequence each doc
   rewrite and its guard into the **same** commit.
10. **`merge=union` and a hash chain are incompatible**, and `.gitattributes` currently sets union on the
    ledger. Two branches appending both chain off the same `prev` and the merged file is a silent fork.
    The seq allocator has the same shape as the MySQL lesson in CLAUDE.md's closing section — two
    writers both read the same max. **The chain IS the collision detector**, and that should be stated
    as the mechanism rather than discovered.
11. **Context assembly becomes the new single point of failure.** What reaches the invocation IS the
    GM's world. A trigger silently not served, a refusal dropped — each produces a GM reasoning
    confidently from an incomplete past with no error surfaced. Same failure shape as a parser reading
    the adjacent u16, and it deserves the same per-item enumerated testing.
12. **Tracked, public GM memory meets a query tool.** A GM that can query and write can paste OOTP
    player rows into a tracked file, and `test_no_leaks.py`'s three patterns will not see it. Mitigated
    by AC5, which is a **new** guard rather than an existing one.
13. **The operator may be in the loop more, not less.** The new model asks for execution dispositions,
    claim resolutions and trigger dispositions every week; the ledger currently holds one entry. Nothing
    measures before-versus-after, and a heavier weekly tax would be an ironic outcome.
14. **The plan-as-second-scorecard risk is only partly testable.** The mechanical guard catches the
    crude version; a GM that only pre-registers claims it expects to win is not catchable by CI and must
    be named as an accepted cost in 0023.
15. **MySQL view privilege semantics are `assumed`, not verified.** Covered by AC17, which must run
    before the ADR states its claim.
16. **ADR 0004's dbt question is forced but not answered.** `gm_view` is ADR 0004 §Notes option 2
    arriving without a decision; the scope appends to 0004's Notes using the mechanism first-sight
    Phase 12 step 4 already planned.
17. **Two core items conflict with each other and the plan must resolve the conflict, not discover
    it.** (a) Baking `WHERE save_id = <managed>` into every view forces the emitter to read
    configuration, but `warehouse/ddl.py`'s "connects to nothing" is precisely the property being
    copied — and a CI with no `.env` cannot then produce the byte-deterministic committed SQL of
    cheap fold 6. Likely resolution: the managed `save_id` is a parameter passed *into* a still-pure
    emitter, with the committed snapshot generated against a fixed placeholder. (b) Emitting per-view
    `GRANT` statements (cheap fold 4) collides with the schema-level `GRANT SELECT ON gm_view.*` in
    B5. Pick one; two grant surfaces is the drift the fold exists to prevent.
18. **Most of Phase A is main-thread work, and `gm/` is not protected from the builder.** Measured:
    `docs/decisions/`, `tests/`, `ops/`, `.claude/` and `CLAUDE.md` are all in the `data-engineer`
    agent's deny set, so the ADRs, the guards, the bootstrap change and the agent-definition edits
    cannot be delegated — the same constraint first-sight already records for `tests/`. Conversely
    **`gm/` is *not* in that deny set**, which a hash-chained append-only `gm/` needs it to be. Adding
    it is a one-line change to the agent definition and belongs in Phase A.

## Affected Area & Pointers

1. **The governance target, read first** — `docs/decisions/` 0013, 0016 (note the supersession
   blockquote shape at its head, which the new ADRs must reproduce), 0018, 0019, 0014, 0017, and
   [`docs/decisions/README.md`](../../../docs/decisions/README.md) (status table; 21 ADRs exist, so the
   new ones start at 0022 with no gap).
2. **ADRs that constrain without being touched** — 0012 (and its parser corollary), 0015, 0021, 0011,
   0006, 0001. Plus the two this request **collides with unnamed**:
   [0005](../../../docs/decisions/0005-hybrid-data-layer.md) (assigns front-office serving models to the
   dbt medallion) and [0004](../../../docs/decisions/0004-mysql-warehouse.md) §Notes (option 2).
3. **The disposition seam** — [`contracts/policy.py`](../../../src/ootp_ai/contracts/policy.py) in full:
   `Disposition`, `disposition()`, `column_disposition()`, `check_policy_covers()`,
   `WITHHELD_NAME_FRAGMENTS`, `KNOWN_CATEGORIES`/`NON_RATING_CATEGORIES`. Its module docstring explains
   why there are TWO renderable outcomes and why the second cannot survive into a banner-less surface.
4. **The declaration and its emitter** —
   [`contracts/tables.toml`](../../../src/ootp_ai/contracts/tables.toml),
   [`contracts/field_map.toml`](../../../src/ootp_ai/contracts/field_map.toml) (read `name_category`'s
   comment — it pre-registers the `unclassified` category and routes it to whoever revisits ADR 0012),
   [`contracts/loader.py`](../../../src/ootp_ai/contracts/loader.py),
   [`warehouse/ddl.py`](../../../src/ootp_ai/warehouse/ddl.py) (**the pattern to copy**),
   [`warehouse/sql.py`](../../../src/ootp_ai/warehouse/sql.py),
   [`warehouse/load.py`](../../../src/ootp_ai/warehouse/load.py) (where `ensure_views()` goes).
5. **The connection and config seam** — [`ops/mysql-bootstrap.sql`](../../../ops/mysql-bootstrap.sql)
   (the three databases and why; the application grant, which includes ALL PRIVILEGES on
   `ootp_truth_real`), [`src/ootp_ai/db.py`](../../../src/ootp_ai/db.py) (the read-back read-only
   assertion to mirror), [`src/ootp_ai/config.py`](../../../src/ootp_ai/config.py) (the only module that
   touches the environment), `.env.example`, `.gitignore`.
6. **The agent and harness seam** — [`.claude/agents/gm.md`](../../../.claude/agents/gm.md) in full
   (frontmatter `tools: Read, Glob`; forced-read list; prohibitions; return contract with its
   `proposed: cost|free` and `precedent` fields), and
   [`.claude/agents/README.md`](../../../.claude/agents/README.md) — the *Detection, not prevention*
   section, **which is the measured answer to the request's Open Question 2**.
7. **The rulebook and memory contract** — [`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md),
   [`gm/README.md`](../../../gm/README.md), [`gm/ledger.jsonl`](../../../gm/ledger.jsonl) (one entry),
   [`gm/standing-orders.md`](../../../gm/standing-orders.md), [`gm/charter.md`](../../../gm/charter.md)
   (Status: unwritten, blocker named as "no warehouse and no reports"),
   [`gm/staff.md`](../../../gm/staff.md), [`gm/decisions/`](../../../gm/decisions/).
8. **The guards that will fire** — [`tests/test_agent_contract.py`](../../../tests/test_agent_contract.py)
   (scoped to `data-engineer.md` alone; **zero references to `gm.md` anywhere under `tests/`**),
   [`tests/test_withheld_fields.py`](../../../tests/test_withheld_fields.py) (the withhold-by-default
   assertions and the `LANDED_BUT_WITHHELD` / `LANDED_UNDER_BANNER` exception lists any view test must
   name), [`tests/test_grain_contracts.py`](../../../tests/test_grain_contracts.py),
   [`tests/test_bronze_landing.py`](../../../tests/test_bronze_landing.py) (the mutation scan; `DROP VIEW`
   is absent from the alternation),
   [`tests/test_repo_structure.py`](../../../tests/test_repo_structure.py) (required docs, ADR indexing
   and sequential numbering, the `!gm/**` carve-out),
   [`tests/test_doc_links.py`](../../../tests/test_doc_links.py),
   [`tests/test_no_leaks.py`](../../../tests/test_no_leaks.py), `.github/workflows/ci.yml`
   (`fetch-depth: 1` — the reason a git-history append-only guard cannot run today), `.gitattributes`
   (`gm/ledger.jsonl merge=union`).
9. **The pinned work** — [first-sight IMPLEMENTATION_PLAN.md](../first-sight/IMPLEMENTATION_PLAN.md),
   specifically §2.3 (the `max(ingest_seq)` convention and the catalog's tracked/volatile split),
   Phase 10 ("the commit the request exists for"), Phase 11 (the catalog and its required-docs
   sequencing note), Phase 12 step 4 (the dbt deferral mechanism), Phase 13 steps 1–4 (AC20, AC21, the
   umpire ledger act, and the GM tool-grant guard follow-up). Plus [gm-inbox](../gm-inbox/),
   [news-subscription-dial](../news-subscription-dial/), and the Index rows in
   [requests/feature-requests/README.md](../README.md).
10. **The epistemic ground** — [`docs/data-access.md`](../../../docs/data-access.md): the label table,
    the scouted-view critical-path task (still `unconfirmed`, and the reason it may be unbuildable),
    `real_sim_date`, and the population caveat on "18,072 rows". Also
    [`README.md`](../../../README.md) for the measured Boston roster-list fan-out.
11. **Not a dataset pointer** — there is no `datasets/` directory and no manifest in this repo yet.
    `gm_view` is **not** a builder dataset: it changes when the league is simulated, so ADR 0005 places
    it on the parser+dbt side, and it ships as generated views under the recorded dbt deferral rather
    than as a third serving pattern arriving unannounced.

## Decisions

Disposed by the operator, 2026-08-19.

| # | Decision | Resolution | Rationale |
|---|---|---|---|
| 1 | Fit verdict | **Accept the reshape** | Two of three named enforcement mechanisms are refuted by the repo. Phase A delivers ~2/3 of the value with zero unverified dependencies; proceeding as written would ship a request whose central claim is false. |
| 2 | first-sight sequencing | **After** — first-sight ships Phases 10–13, then convert | Phase 10 is one commit away and is the project's own vertical-slice rule; Phase 13's AC20 produces the only measured baseline of what a GM can do under the report wall. Cost — Phase 12/13 write artifacts in the retiring vocabulary — is cheap to supersede. |
| 3 | GM query mechanism | **Spike first; then a purpose-built read-only tool. Never `Bash`. Reports as the honest fallback.** | Tool grants are the one thing the harness enforces. A tool holding the DSN internally and exposing no connection parameter is genuine enforcement and neutralises the pre-existing `.env` hole. `Bash` is strictly worse than the status quo. |
| 4 | ADR structure | **Split along the phase boundary** — 0022 (attention) + 0023 (memory) in Phase A; the information model as a third ADR in Phase B only if the spike passes | Both adversaries flagged the panel's own recommendation as a blocker: no accepted ADR may assert an enforcement mechanism whose existence is still `unconfirmed`. If the spike fails, "better reports under a retired economy" is exactly what the record says. |
| 5 | Ledger continuity | **Close `gm/ledger.jsonl`; open the execution log beside it** | Unanimous across all three scopers. Rewriting a tracked append-only file to fit a new schema is precisely the retroactive edit this request exists to prevent. Seq 1 stays, never edited; `standing-orders.md`'s `Established:` convention re-points. |
| 6 | `Disposition.UNCERTAIN` at the schema boundary | **Present, with the label in the alias** (`real_sim_date__unconfirmed`); the emitter refuses an unhandled disposition | The banner obligation survives into a surface with no banner channel. One column affected today, so deciding either way is cheap — but it must not be defaulted by whoever writes the generator. |
| 7 | A mutable `plan.md` | **No — `gm/charter.md` already carries the role** | The charter is club-scoped, mutable, and its own header requires changes be recorded as decision records with reasoning: a revisable plan with a git supersession chain. A fourth artifact duplicates the role. Limitation acknowledged: no CI check can assert a diff carries a reason, whatever file holds it. |
| 8 | OOTP player data in tracked `gm/` | **Bounded** — a journal entry cites a query and a `(save_id, sim_date, ingest_seq)` triple, never a pasted result set | `gm/` is world-readable forever while rendered game data is deliberately routed to a gitignored root. Stronger than the frozen-report property it replaces, because append-only bronze makes the citation re-runnable. Enforced by AC5. |
| 9 | Which schema `gm_view` reads | **A separate `.env` key; the generator refuses to build over `ootp_dev`; every view carries a baked `save_id` predicate** | `MYSQL_DATABASE` is the value that swaps. A GM silently pointed at `ootp_dev` would be managing a different universe — the exact failure the schema split was created to prevent, arriving through a new door. |
| 10 | Token / turn instrumentation | **Rides along** — one token field and one wall-clock field per execution-log row, Phase A, unconditional | Retiring 0013 deletes the only cost bound and makes the operator's own hypothesis unfalsifiable: "tirelessness is the independent variable" needs tirelessness measured. Also answers adversary finding A2-03 — the denominator replacement cannot sit behind the gate. Honest limit stated in 0022: instrumentation measures, it does not bound. |
| 11 | Write `gm/charter.md` in this slice | **No — deferred to the GM's first invocation** | Competitive window and operating principles are baseball content. Under ADR 0017 umpires do not bat; the charter is the GM's first act once the apparatus lands, not an engineering deliverable. Non-goal 14 stands. |

**Blocker findings folded into this scope rather than deferred:** F01/A2-01 (ADR placement contradicted
the phase split → decision 4), F02 (AC2's pinned count of 94 was arithmetically incompatible with not
serving `bronze_name` — the adversary measured the real number as 88 plus a joined name column that is
not a declared column at all → rewritten as an invariant plus a frozen exception ledger, AC13), F03 (no
criterion tested the view bodies or `DEFINER` semantics → AC16 and AC17), A2-02 (criteria were not
phase-partitioned → every criterion now tagged, and AC7 added), A2-03 (the denominator replacement sat
behind the gate → decision 10 moves it to Phase A).

**Major findings folded in after a second pass over the adversary summaries**, each a defect in this
scope rather than in the request: ADR 0012's Buys clause is invalidated by 0013's retirement while 0012
is declared untouched (→ non-goal 2's annotation carve-out); `gm/staff.md` was missing from the
doc-rewrite surface and `gm/standing-orders.md` was scoped too narrowly (→ A8); 0013's standing-order
lever and autonomy graduation and 0019's structural first limiter were being dropped by silence (→ A10);
the five dataset contracts were never stated (→ the Data Contracts section); two core items conflict
with each other (→ risk 17); and `gm/` sits outside the builder's deny set while `docs/decisions/`,
`tests/`, `ops/` and `.claude/` sit inside it (→ risk 18).

## Panel Trail

Raw, unfiltered panel output: [`reviews/scope-proposals.md`](reviews/scope-proposals.md) (the three
scopers' proposals) and [`reviews/scope-adversarial.md`](reviews/scope-adversarial.md) (64 adversary
findings and the convergence map). Panel run `wf_854b2b93-a5a`, 2026-08-19 — 3/3 scopers, 2/2
adversaries, no degraded lenses, ~946k subagent tokens.
