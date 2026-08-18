---
name: make-feature-request
description: >-
  Turn a new idea for this platform into a clean, well-scoped, repo-grounded feature request —
  the deliverable a fresh agent can pick up for scoping. This is where ALL new work starts,
  including every new dataset: nothing gets extracted, landed, or modeled without a request
  behind it. Use it whenever the user wants to add or change a capability: a new data source, a
  new engine mechanic, an app surface, a dataset builder, a new skill, a serving
  surface. Trigger on phrasings like "I want to ingest…", "we should have a model that…", "can
  we build…", "there's no way to answer X yet", "I keep doing this by hand", "new feature", or
  "feature request" — i.e. a gap in what the platform can do. Prefer this over jumping straight
  into implementation: capturing the request first is the cheap guardrail that makes scoping and
  planning go smoothly. Do NOT use it for quick bug fixes, work already captured in an existing
  feature-request directory, or baseball questions the existing warehouse already answers — those
  are analysis, not platform features. Tie-break: a gap in what the platform can DO is a feature
  (here); a defect IN something that already EXISTS and fails is a bug (use make-bugfix-request);
  code that ran green while producing WRONG DATA is a data incident (see
  requests/data-incidents/README.md).
---

# Make Feature Request

## What this produces and why

A single `FEATURE_REQUEST.md` in `requests/feature-requests/<slug>/` — a tight, honest statement of
**what's wanted and why**, grounded in the actual repo, that a cold agent (running
`/scope-feature`) can consume without re-discovering the codebase.

The whole point of intake is to separate the *problem* from the *solution* early. People
usually arrive with a fix already in mind ("add a column", "build a script that…"). That's
fine — capture it — but a request anchored only to the first idea quietly forecloses better
ones. So the job here is to draw out the underlying pain and the "done" state, **record the
requester's solution hunch as non-binding**, and leave the real decisions open for scoping.

Keep it light. Many of these get handled end-to-end in an hour — intake should feel like a
focused conversation, not a form. Infer from the repo what you can; ask only what you can't.

Read [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md) once for the
pipeline conventions (layout, status header, the stages downstream of this one).

---

## Step 1 — Sanity-check, then understand the ask

Intake is the cheapest place to stop work that shouldn't become a request, so gate first.
Confirm this is a real **platform** gap, and not one of:

- a **bug fix**, a **data incident**, or an **analysis question** the existing warehouse already
  answer — answer or redirect instead of opening a request;
- work **already captured** — scan `requests/feature-requests/` for an existing matching `<slug>/` and
  continue that one rather than starting a duplicate;
- an idea that **plainly collides with a hard constraint**. The common ones here: the data
  simply isn't readable, or the claim it rests on is still `unconfirmed` — check the epistemic
  labels in [`docs/data-access.md`](../../../docs/data-access.md); an unconfirmed claim is a task,
  not a fact — or the idea collides with a settled ADR (writing to the game, depending on the
  in-game export, tracking OOTP data). Don't silently write a request for a dead-on-arrival idea: name the specific
  conflicting rule and offer to **reshape it**, **drop it**, or **capture it anyway with
  the conflict recorded** (under Constraints / Open Questions) for the scope panel to weigh.
  Keep this a quick sniff-test — a full fit verdict is scoping's job, not intake's.

Then start from what's already on the table. The triggering message (and the conversation
around it) usually contains most of the request — the pain, a proposed solution, maybe a file
or dataset by name. Extract that first so you don't re-ask what the user already told you. Form
a one-line working summary of the ask and the *problem behind it*. If the user led with a
solution, note "what problem does this solve?" as the thing to confirm — don't accept the
solution as the spec yet.

**If the ask is really two or three independent capabilities** ("ingest shot charts AND build a
shot-quality mart"), name them back and **offer to split** into separate requests (one
slug each) so each is cleanly scopeable — that's the default. Fall back to capturing the
primary and parking the rest under *Not now / later* only if the user prefers one thread.
One `FEATURE_REQUEST.md` = one coherent feature.

## Step 2 — Ground it in the repo

This is the step that makes the request worth writing. Figure out **where this lives and what
it touches**, so the request lands pre-grounded:

- Which subsystem? The parser / landing / warehouse loader (`src/ootp_ai/`), a dbt model
  (`transform/`), a static reference builder (`build/` → `datasets/`), an advisor,
  serving (`app/`), a skill (`.claude/skills/`), docs (`docs/`)?
- What already exists that this overlaps, extends, or must join to? Name the datasets by
  their `ref()` name and the sources by their `source()` name; name the source-of-truth doc.
  Confirm every model or source you cite actually exists before listing it — a dead pointer is
  worse than none.
- **If this touches a dataset**, name the five contracts up front — grain, keys, era coverage,
  update semantics, and extraction cost. See
  [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md). You are
  not deciding them here; you are making sure scoping knows they are open.
- Any obvious constraints from the project rules (resolve-by-name, append-only ledger,
  grain-declared-and-tested, agents-never-commit, no bulk data in the repo) this has to live within?

Aim for **~3–6 targeted lookups** — enough to name the subsystem and the 2–4 files/datasets a
scoper opens first. You're handing the next stage a map, not designing the solution: if you're
reading code to work out *how* to build it, you've overshot — that's scoping's job.

## Step 3 — Interview to fill the gaps

Ask only what the conversation and the repo didn't already answer. Batch related questions;
don't drip them one at a time. Use `AskUserQuestion` when the choice is genuinely user-owned
and discrete (in-scope vs out, priority); use plain prose for open-ended "what does done look
like" questions — and for any discrete choice if `AskUserQuestion` isn't available. Don't ask
"which subsystem" — that's Step 2's job to infer from the repo.

The high-value gaps, roughly in priority order:

1. **The problem** — what's painful/missing today, concretely, and who feels it. (Confirm this
   even when the user led with a solution.)
2. **Desired outcome** — how they'll know it worked; the capability or experience they'd have.
3. **Scope edges** — what's explicitly *out*, and what's deliberately *later*. Boundaries are
   worth more than features; they're what keep scoping honest.
4. **Constraints / non-negotiables** the requester knows about.
5. **Open questions** they already sense but haven't resolved.

If baseball or save-format specifics matter to the request (what a stat means, how a rule change affects
comparability, which era a source covers), pin them down here rather than letting the scoping
agent guess — but don't over-design. **Label what you pinned down and how you know it**:
`measured`, `verified`, `inferred`, `assumed`, `unconfirmed`. An unconfirmed claim about an
endpoint's shape is a task for scoping, not a fact for planning to build on.

**When the ask, its boundaries, or its motivation stay ambiguous, ask before writing.** Two
specific binds to handle gracefully rather than forcing:

- **The conversation drifts into *how it's built*** ("use a SQLite DB and a new dataset…") —
  record it as a non-binding Rough Idea and defer the decision to scoping; don't resolve it here.
- **The user only has a solution** and the underlying problem won't come out after a reasonable
  ask — don't deadlock and don't fabricate a problem (the "solution in disguise" the rubric
  warns against). Capture the solution under Rough Ideas, leave Problem/Motivation as an explicit
  Open Question ("motivation not articulated — scoping to confirm before building"), and proceed.

## Step 4 — Draft the request

Propose a **slug** (kebab-case, descriptive — `box-score-foundation`, not `feature-3`).
Before creating anything, **check the slug doesn't collide**: list `requests/feature-requests/` and scan
the README Index. If a dir with that slug already exists, it's either the same feature (stop and
point the user at the existing request) or a genuine clash (disambiguate the slug) — **never
write into an existing slug dir without explicit confirmation** (git is read-only here, so a
clobbered request is hard to recover). You can fold the slug confirmation into the draft review
in Step 5 rather than asking separately.

Create `requests/feature-requests/<slug>/` and write **only** `FEATURE_REQUEST.md` (the `reviews/` dir
and the later artifacts belong to downstream stages) using the template below.

**Carry the load-bearing sections — they're the whole point of intake, so don't omit them:**
**Problem**, **Desired Outcome**, **Scope Signals** (especially *Explicitly out* — if you can't
fill it, interview more rather than dropping it), and **Affected Area & Pointers** (at minimum
the touched subsystem and the concrete files/datasets a cold scoping agent reads first — this is
Step 2's grounding, carried into the request). *Open Questions* may be empty only if you
genuinely surfaced none (say so). *Rough Ideas* is the one section to drop when there are none.

**Then decide the Stage plan — the last section you write, and never optional.** Per
[ADR 0008](../../../docs/decisions/0008-panels-by-default.md) the full pipeline is the
**default**; a skip is an exception you argue for. Check the three hard triggers in
[`requests/README.md`](../../../requests/README.md) against the request you just wrote — any one
of them fires and the panel runs, with no argument available:

1. **Open Questions came out non-empty.**
2. **Explicitly out couldn't be filled.**
3. **It touches something expensive to reverse** — a settled ADR, a pillar, the event schema, a
   dataset contract, a warehouse grain, the parser's field map, or anything another request pins.

Clear all three and you may *propose* a skip, stating which triggers it cleared and why the work
is genuinely bounded. The user disposes it at the Step 5 handoff.

> **Note the incentive this creates, and don't take it.** Triggers 1 and 2 are sections *you*
> just wrote, so under-reporting an open question or hand-waving an *Explicitly out* is now the
> path to less ceremony. That is the one dishonesty this rule can't catch mechanically. Write
> those two sections as if the Stage plan didn't exist — then read them.

```markdown
> **Status:** intake · created <YYYY-MM-DD> · open · next: scope

# Feature Request — <Title>

## Problem / Motivation
<What's painful or missing today, described independently of any solution — what's slow,
error-prone, impossible, or annoying right now, and who feels it. Concrete examples beat
abstractions.>

## Desired Outcome
<What "done" looks like in plain terms — the capability or experience once it exists, and the
observable signal that it worked. Not how it's built, and NOT formal/testable acceptance
criteria (those are scope's job, pipeline stage 2).>

## Rough Ideas (non-binding)
<The requester's solution hunches — approaches, tools, data sources. Explicitly non-binding:
scoping is free to propose something better. Omit if there are none.>

## Scope Signals
- **In:** <what this should cover>
- **Explicitly out:** <what this is NOT — the guard against scope creep>
- **Not now / later:** <adjacent ideas deliberately deferred>

## Affected Area & Pointers
<Which part of the repo this touches, and the concrete files / datasets (by logical name) /
sources / docs a cold scoping agent should read first. The grounding from Step 2.>

## Data Contracts (datasets only — omit otherwise)
<The five open contracts, stated as questions rather than answers: grain, keys, era coverage,
update semantics, extraction cost. Scoping decides them; intake makes sure they're on the table.>

## Constraints / Non-negotiables
<Hard rules this must respect — project conventions, compatibility limits, data-source rules.>

## Open Questions for Scoping
<The genuinely unresolved decisions to hand downstream. Don't paper over them — naming them
is more useful than a false sense of certainty.>

## Stage plan
<REQUIRED, and written last. State which stages run. The default is all four.

If the panel runs, one line is enough — name the trigger that fired:
  "Full pipeline. Trigger 3: defines the event schema every later item pins."

If proposing a skip, argue it: name all three triggers and how each was cleared, and say what
makes the work bounded. Stage 4 still runs in direct-build mode, with this request standing in
for the plan.>
```

## Step 5 — Confirm, record, hand off

1. Show the draft (or a tight summary) and let the user correct it — they know the problem
   better than you do. Iterate until it reads true.
2. Write the file, then register it: add a row to the **Index** table in
   [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md) using the literal
   columns under that file's `## Index` heading:
   `| [<slug>](<slug>/) | intake | <one-line note> |`
   The status blockquote in the request is the source of truth for stage; the Index `Stage`
   cell mirrors it (`intake` is just the initial value — downstream stages advance both). If the
   *feature itself* is a pipeline stage (e.g. a request to build another skill), say so in the
   Notes so the row isn't confused with this request's own intake stage.
3. Point at the next step, and **lead with the Stage plan** — it's the one thing here the user
   may want to overrule. If the panel runs (the default): *"Run `/scope-feature` when you're
   ready to scope this."* If you proposed a skip, **say so explicitly and show the argument**,
   so the exception is visible rather than inferred from what you didn't do. Either way, don't
   start the next stage yourself — that's a separate, human-gated stage.

Per project convention, **agents commit only through `/commit`** — never `git commit` ad hoc. End
your turn by suggesting `/commit` when the user wants the request landed.

---

## What good looks like

- **Every relative link you write must resolve on disk.** Live (non-`_done/`) artifact bodies are
  scanned by `tests/test_doc_links.py`, a blocking CI check, so a dead pointer fails the build
  rather than quietly misleading the next stage. Two shapes to watch: a **forward reference** to a
  file a later stage creates, and a deliberately **broken example path**. Put either inside a fenced
  code block (``` or ~~~, blockquoted is fine) — fenced content is exempt, precisely so a report can
  quote a dead target. Citations may carry a `file.py:123` suffix; `var/` targets are exempt too.

- **Problem stated independently of the fix.** If the Problem section only makes sense once
  you've read the Rough Ideas, it's a solution in disguise — rewrite it around the pain.
- **Honest boundaries.** An explicit "out of scope" and "not now" is the highest-signal part
  of a request. A request with no edges will balloon in scoping.
- **Grounded.** Real file and dataset names, resolved from the repo — not "the relevant data."
- **Open questions left open.** Hand the hard calls to scoping with their uncertainty intact;
  don't fabricate decisions intake isn't equipped to make.
- **Right altitude.** It says *what* and *why*, gestures at *how*, and stops. The how is
  scoping's and planning's job — over-specifying here just pre-commits to one path.
- **The Stage plan argues, or it says "full pipeline" and stops.** A skip proposed without
  naming all three cleared triggers is not an argument, it's a preference. When in doubt, the
  panel runs — that's the default precisely so the uncertain case resolves without a debate.
