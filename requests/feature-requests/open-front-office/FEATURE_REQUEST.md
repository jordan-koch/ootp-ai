> **Status:** scoped · created 2026-08-19 · decided · next: plan

# Feature Request — Open the Front Office

## Problem / Motivation

The GM apparatus is built to test a hypothesis the operator does not hold.

The information rules — the report wall
([ADR 0016](../../../docs/decisions/0016-gm-reads-reports-not-queries.md)), the
action economy ([ADR 0013](../../../docs/decisions/0013-action-economy.md)), and
the pricing patches layered on them
([0018](../../../docs/decisions/0018-retention-is-infrastructure.md),
[0019](../../../docs/decisions/0019-reading-costs-an-action.md)) — simulate a
*human* front office's attention scarcity: a tireless analyst is treated as an
unfair advantage to be metered away. The operator's actual claim under test is
**whether a robust data infrastructure plus an adaptive agent can be competitive**
— in which the agent's tirelessness is the independent variable, not a confound.
How OOTP's own AI budgets its attention is deliberately not this project's
concern: the operator is putting his own agent, tooling, and budget up against
the engine's, whatever the engine does internally. The scarcity rules are a
self-imposed handicap serving a hypothesis nobody holds.

The concrete pains, each felt before a single game has been played:

1. **Adjudication overhead is disproportionate and compounding.** ADRs 0018 and
   0019 exist mainly to patch pricing edge-cases in 0013/0016 (retention, mail),
   and every future information channel will need its own ruling. The ledger has
   one entry; the taxonomy already needed three ADRs.
2. **A flat weekly budget with expiry is the wrong shape for a bursty season.**
   0013 makes unused actions expire and forbids banking — precisely backwards for
   a workload with known peaks (deadline, draft, winter meetings) and thirty
   business-as-usual weeks. It starves the weeks that matter.
3. **The GM cannot write, so it cannot plan.** A per-invocation subagent
   ([ADR 0017](../../../docs/decisions/0017-gm-is-a-subagent.md)) with no write
   channel cannot leave itself "re-evaluate the scouting director in June," cannot
   maintain a plan toward multi-year owner goals, and cannot accumulate a
   calibration record. It has no time horizon — while being graded
   ([ADR 0015](../../../docs/decisions/0015-gm-is-employed-not-appointed.md)) on
   multi-year outcomes.
4. **The wall is coarser than the machinery beneath it.**
   [`contracts/policy.py`](../../../src/ootp_ai/contracts/policy.py)
   (`column_disposition`) already decides *per column* what is releasable, failing
   closed on anything unclassified. 0017 enforces ADR 0012 by removing all
   database access instead — protecting the answer key by forbidding the entire
   library.

### Settled decisions this deliberately collides with

Named per intake rules, for the scope panel to weigh — this request exists to
supersede or amend them, with the career-record discipline the ADRs themselves
use (supersede, never delete):

- **Supersedes:** 0016 (report wall), 0013 (action economy), 0018 and 0019 (its
  pricing patches — one insight from 0019 survives, see Open Questions).
- **Amends:** 0014 (narrowed to sensor-vs-processing — the in-game sensor cannot
  be improved by code and true-rating reconstruction stays foreclosed, but
  analytics over scouted inputs becomes the point rather than a violation);
  0017 (the GM stays a subagent; its *no-DB* foreclosure becomes a scoped grant
  and its *no-write* foreclosure becomes append-only).
- **Untouched, and load-bearing:** 0012 (scouted ratings only — enforcement gets
  *stronger*), 0015 (owner judges), 0003 (Challenge Mode), 0001 (no write-back),
  0021 (append-only bronze), 0006 (public repo).

## Desired Outcome

The weekly cycle becomes: time progresses → ingest lands the snapshot → the GM
subagent is invoked with assembled context → it **queries a scoped schema
itself**, reads its own memory, **writes** journal entries / predictions /
triggers (append-only) and revises its plan → returns proposed in-game moves →
the operator executes what he chooses and the log records each disposition.

Done looks like:

- **The GM answers a baseball question by querying, with no commissioned-report
  apparatus in the loop** — and a true rating is *physically unreachable*: the
  withheld columns are absent from the schema it can see, enforced by a database
  grant rather than prose. "What you are not allowed to see" stops being a rule
  the GM follows and becomes a fact about its connection.
- **The GM can leave itself a future.** A note written in April ("circle back on
  this prospect in June") is served back to it in June without anyone
  remembering to do so.
- **The reasoning record is tamper-evident.** The GM can always write something
  new and can never change what it already wrote — its April belief survives
  contact with its July results, which is what makes calibration measurable.
- **The plan is revisable and the revisions are the artifact.** The GM maintains
  a plan toward the owner's goals; git history is the supersession chain; each
  revision states why it changed.
- **Execution is the only metered thing.** The ledger becomes an execution log —
  proposed / executed / deferred / declined, with reasons — replacing budget
  adjudication. *Declare before doing* survives: reasoning is written before
  outcomes are known.
- Observable signals a cold agent can check: a CI test proving no withheld
  column is reachable from the GM's grant; a CI test failing on any retroactive
  edit to an append-only `gm/` file; a round-trip test that a trigger written at
  sim date N is served at sim date N+k.

## Rough Ideas (non-binding)

- `gm_view` schema of views generated from
  [`contracts/policy.py`](../../../src/ootp_ai/contracts/policy.py)
  `column_disposition` over the declared tables — same single-declaration pattern
  as [`warehouse/ddl.py`](../../../src/ootp_ai/warehouse/ddl.py). A MySQL user
  with `SELECT` on that schema and nothing else; its DSN in `.env`, resolved only
  by the GM's tooling.
- GM tool grant grows from `Read, Glob` to include a SQL query tool bound to the
  restricted DSN, plus whatever write mechanism scoping picks (see Open
  Questions).
- New `gm/` artifacts (names illustrative): a journal (`journal.jsonl`,
  append-only, structured envelope — sim date, kind, subject, optional trigger —
  plus prose body), predictions (`{subject, claim, resolve_by, resolution}`,
  GM-authored, umpire-resolved), a trigger queue (dated triggers only in v1;
  mandatory disposition on fire: act / defer with new date / close with reason;
  recurring-vs-one-shot explicit at write time), and a mutable `plan.md`.
- Append-only CI guard: a test that the protected files only ever grow
  (`merge=union` interaction to be worked out).
- Weekly context assembly: charter + current plan + fired triggers + standing
  orders + a one-line index of journal/decisions with pull-on-demand, rather
  than the full history.
- The Phase 10 reports of [first-sight](../first-sight/IMPLEMENTATION_PLAN.md)
  become seed views in `gm_view`; the Phase 11 catalog becomes the GM's data
  dictionary (withheld = absent from schema, so its withheld section shrinks to
  an explanation).

## Scope Signals

- **In:** the ADR set (supersessions and amendments above); `gm_view` generation
  and grant; the GM agent definition
  ([`.claude/agents/gm.md`](../../../.claude/agents/gm.md) — tools and return
  contract); the `gm/` memory structures and their CI guards; the ledger's
  conversion to an execution log;
  [`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md) rewritten around all of it;
  explicit dispositions for the pinned work named below.
- **Explicitly out:** any change to 0012, 0015, 0003, 0001, 0021, or 0006; any
  widening of what the parser reads (no new files or fields —
  [gm-inbox](../gm-inbox/) remains its own request); building analytics or
  models *for* the GM (directing that is the GM's job once this lands); a
  condition-evaluating trigger engine (dated triggers only); any change to
  in-game staff mechanics (0014's sensor half stands: hiring better scouts is
  still the only way to a clearer sensor).
- **Not now / later:** SQL-condition triggers evaluated at ingest; a drift
  ritual (replay a past decision with reasoning stripped, compare); a warehouse
  retention policy; per-invocation token instrumentation (cheap and worth doing
  early — scoping decides whether it rides along or files separately).

## Affected Area & Pointers

Rules and docs first, code second — the diff is mostly governance:

- [`docs/decisions/`](../../../docs/decisions/) — 0013, 0016, 0018, 0019
  superseded; 0014, 0017 amended; new ADR(s) authored (one vs several is an open
  question).
- [`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md) — the shared rulebook; "what you
  are allowed to see" and the action economy sections rewritten.
- [`.claude/agents/gm.md`](../../../.claude/agents/gm.md) — tool grant, the
  read-on-invocation list, the return contract (currently built around
  proposing action-economy rulings), and every prohibition that cites a
  superseded ADR. [`tests/test_agent_contract.py`](../../../tests/test_agent_contract.py)
  guards agent-contract invariants and will need to track the changes.
- [`gm/README.md`](../../../gm/README.md) — the memory contract: new artifacts,
  scope table (career vs club), ledger schema.
  [`gm/ledger.jsonl`](../../../gm/ledger.jsonl) — one entry exists; migration
  or continuation is an open question.
- [`src/ootp_ai/contracts/policy.py`](../../../src/ootp_ai/contracts/policy.py)
  and [`src/ootp_ai/warehouse/ddl.py`](../../../src/ootp_ai/warehouse/ddl.py) —
  the disposition logic and the DDL-from-declaration pattern `gm_view`
  generation extends. The serving-gate seam (§2.3 of the
  [first-sight plan](../first-sight/IMPLEMENTATION_PLAN.md)) changes shape:
  the gate moves from "report page" to "schema boundary."
- **Pinned/interacting work:** [first-sight](../first-sight/) Phases 10–11
  (reports and catalog — reshaped, not discarded);
  [gm-inbox](../gm-inbox/) and
  [news-subscription-dial](../news-subscription-dial/) — both priced in
  action-economy vocabulary that this request retires; both need re-framing or
  explicit deferral.

## Data Contracts

The new surfaces carry contracts; stated as questions for scoping:

- **`gm_view`** — grain per view (inherit bronze grain, or serve
  `max(ingest_seq)`-latest by default with history opt-in?); which of the eight
  declared tables reach it at all; how a withheld column's absence is
  distinguished from a not-yet-landed one (the catalog's job?).
- **Journal / predictions / triggers** — grain (one row per entry? keyed how —
  seq, sim date + seq?); update semantics (append-only, mechanically enforced);
  who writes which fields (GM authors intent and claims; umpires author
  resolutions and outcomes); coverage (career-scoped vs club-scoped, per
  [`gm/README.md`](../../../gm/README.md)'s existing split).
- **Execution log** — schema (what/proposed/disposition/reason at minimum);
  whether it continues `ledger.jsonl`'s seq space or opens a new file.

## Constraints / Non-negotiables

- **ADR 0012 is absolute and its enforcement must not weaken in the handover** —
  the withhold-by-default posture (an unclassified field is a true rating)
  moves intact from the report gate to the schema boundary.
- **The repo is public (0006).** Everything in `gm/` is world-readable; the
  restricted DSN and credentials live in `.env`;
  [`tests/test_no_leaks.py`](../../../tests/test_no_leaks.py) binds.
- **The game stays read-only (0001); the operator executes everything.**
- **Owner goals remain the sole scorecard (0015).** The GM's plan is method,
  not objective — it never becomes a second success criterion, and where it
  knowingly trades owner satisfaction now for position later it must say so in
  advance.
- **Reconstructing true ratings from observables stays foreclosed** (0014's
  surviving core). Analytics over scouted inputs and realized outcomes is in;
  regression toward the answer key is out.
- **Append-only means append-only.** The GM never edits what it wrote; a
  correction is a new entry. Same discipline as bronze (0021) and the ADRs.
- **Declare before doing survives 0013's retirement** — reasoning is recorded
  before outcomes are known, or the record is justification rather than
  evidence.
- Grain declared and tested for anything landed; agents commit only through
  `/commit`; subagents get read-only git.

## Open Questions for Scoping

1. **first-sight sequencing.** Phase 10 is next up in a *planned* request. Does
   this land first (reports become seed views), after (reports ship then
   convert), or does first-sight absorb the `gm_view` work as an amended phase?
2. **GM write mechanism.** A `Write`/`Edit` grant scoped to specific `gm/`
   paths, or the GM returns structured output and the umpires land it? The
   first is enforcement-by-grant (this request's whole theme); the second keeps
   0017's pen-holding intact. Related: can the harness scope a write grant by
   path at all?
3. **GM query mechanism.** Which tool executes SQL, how the restricted DSN
   reaches it and nothing else does, and what stops the GM reading `.env`.
4. **Ledger continuity.** Seq 1 is career-scoped doctrine under a cost model
   being retired. Continue the file with a new schema, or close it and open the
   execution log beside it?
5. **What survives of 0019.** Its feed-vs-warehouse insight ("infrastructure
   can never replace what only the world knows") and its refusal loop (declined
   proposals return with reasons — now a disposition in the execution log) both
   look worth keeping even with the pricing gone. Where do they land?
6. **One ADR or several** — the information model (open the DB, retire the
   economy) and the memory model (append-only GM writes) are separable
   decisions with separate reasoning.
7. **Append-only CI mechanics** — how to assert "this file only grew" robustly
   across branches and `merge=union`.
8. **Context assembly ownership** — where the weekly invocation-context builder
   lives (a skill, a module under `src/ootp_ai/`, or umpire procedure), and
   what it includes by default.
9. **History exposure** — does the GM see full snapshot history in `gm_view`
   by default, or latest-per-sim-date with history explicit? (Retention is
   free per 0018's reasoning; the question is the default ergonomics, not the
   right to look.)

## Stage plan

**Full pipeline.** Trigger 3 fires several times over: this supersedes four
settled ADRs and amends two more, rewrites the shared rulebook
([`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md)), changes the serving-gate seam
of a *planned* request (first-sight), and re-frames two other requests currently
in intake. Trigger 1 also fires — nine open questions. No skip is available or
wanted; the operator explicitly asked for the panels to hunt edge-cases.

This stays **one request** — the information model and the memory model amend
the same ADRs and the same rulebook, and the panels' value is in their
interaction. Operator disposition, 2026-08-19: splitting, if any, happens at
the *implementation* stage as distinct phases, not here.
