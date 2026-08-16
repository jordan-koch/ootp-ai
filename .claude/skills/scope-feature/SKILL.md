---
name: scope-feature
description: >-
  Turn a captured FEATURE_REQUEST into a well-scoped, repo-fit PROJECT_SCOPE with testable
  acceptance criteria — by running an adversarial multi-agent scoping panel. This is stage 2 of the
  feature pipeline (intake → scope → plan). Use it whenever a feature request exists and the user
  wants to scope it: decide whether it fits the repo, settle what's in/out, surface above-and-beyond
  enhancements, or pin down acceptance criteria. Trigger on "scope this feature", "scope the <slug>
  request", "run the scoping panel", "is this worth building / does it fit", "what should the scope
  be", "turn this request into a scope". Do NOT use it to write the implementation plan itself —
  that's stage 3 (/create-implementation-plan): scoping decides *whether and what*; planning decides
  *how*. So if a PROJECT_SCOPE already exists and the user wants the build approach / file-by-file
  steps, that's stage 3, not this. Also not for writing code or in-game/gameplay questions. If no
  FEATURE_REQUEST exists yet, send the user to /make-feature-request first.
---

# Scope Feature

## What this produces and why

A `PROJECT_SCOPE.md` in `requests/feature-requests/<slug>/` — a repo-fit verdict, crisp goals/non-goals,
**testable** acceptance criteria, a tiered (greedy-but-gated) scope, the above-and-beyond ideas
worth keeping, the risks, repo-grounding pointers for the plan, and the gated decisions **you**
resolve — that `/create-implementation-plan` can consume cold.

Scoping is where a request either earns its place or gets reshaped. Doing it with one agent's
single perspective is how blind spots and quiet scope-creep slip through. So this skill runs a
**deterministic adversarial panel** (a bundled workflow) instead:

> **3 divergent scopers** (repo-fit · ambitious/above-and-beyond · risk/YAGNI) → **1 merge** that
> converges + tiers + builds a convergence map → **2 adversaries** that attack fit, acceptance-criteria
> testability, scope-creep, and blind spots.

Two principles from [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md) drive it:
**greedy-but-gated** (propose everything; expensive/scope-growing ideas are tiered and deferred for
your call, never silently folded) and **generate → converge → triage → you-decide** (the panel
proposes; **you** dispose the gated decisions). The panel runs to completion, then the **human gate
is yours** — it never auto-finalizes the scope.

---

## Step 1 — Locate the request (and check it's worth scoping)

The panel scopes a specific `FEATURE_REQUEST.md`. Resolve it:

- If the user named a slug or path, use `requests/feature-requests/<slug>/FEATURE_REQUEST.md`.
- Otherwise check the **Index** in [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md)
  for a request at the `intake` stage, or infer from the conversation. **If you *inferred* the slug
  rather than being told it, echo back the exact request path + title and get a yes before launching** —
  the panel is expensive and will silently scope whatever request it's handed.
- **If no `FEATURE_REQUEST.md` exists for this idea, stop** and send the user to `/make-feature-request`.

**Substance gate.** Open the request and confirm it actually carries a **Problem**, a **Desired
Outcome**, and **Affected Area & Pointers**. The scopers ground in the request — a thin or hollow one
yields a hollow scope and burns a ~6-agent run on vapor. If it's too thin, bounce it back to
`/make-feature-request` to flesh out rather than scoping it.

## Step 2 — Run the scoping panel

This is the **sanctioned multi-agent step** — the panel *is* the skill. It spins up ~6 high-effort
agents (3 scopers → merge → 2 adversaries), costs real tokens, and takes a few minutes. Tell the user
it's running and what it's doing **before** you launch it.

Run the bundled script (don't hand-roll the orchestration). Pass it by path — an **absolute** path
avoids any cwd ambiguity (resolve repo-root + the segment):

```
Workflow({
  scriptPath: "<repo-root>/.claude/skills/scope-feature/scope_panel.js",
  args: { requestPath: "requests/feature-requests/<slug>/FEATURE_REQUEST.md",
          featureDir:  "requests/feature-requests/<slug>/",
          slug:        "<slug>" }
})
```

If the path doesn't resolve, read `scope_panel.js` and pass its contents as the `script` parameter
instead. The Workflow tool runs the panel in the background and notifies you when it completes (watch
it with `/workflows`); the full structured result is the returned tool output. If that result has an
`"error"` key (**all scopers failed** — a *merge* failure no longer errors out: the panel now recovers
it to a degraded scope, flagged by `merge:fallback` in `degraded_lenses`), report it and stop — don't
fabricate a scope from a failed run. A recovered (degraded) scope is a deterministic, de-duplicated
UNION of the scopers, not a synthesis: its `fit_verdict` is deliberately never `clean` — surface the
degradation, verify the fit, and consider re-running before planning.

## Step 3 — Wait for completion, check panel health, save the trail

**Wait for the workflow to actually return its structured result before continuing** — a launch
acknowledgement is not the result. The real result carries `fit_verdict`, `acceptance_criteria`,
`gated_decisions`, etc.

**Check the panel actually ran in full** before trusting it: inspect `stats.scopers_ok` and
`stats.adversaries_ok`. If fewer than 3 scopers or fewer than 2 adversaries returned, the adversarial
premise was *degraded* — say so plainly and offer to re-run, rather than building a scope on a thin
panel that still *looks* complete. The panel auto-retries a stubbed lens once and counts it `ok` only
on real (non-placeholder) content, so these counts are trustworthy; the `degraded_lenses` array names
any lens that still stubbed after the retry — check it, and recover a dead lens with a direct free-text
`Agent` rather than a full re-run.

Then write the raw, unfiltered panel output as the provenance trail under
`requests/feature-requests/<slug>/reviews/` (the Write tool auto-creates the dir):

- `reviews/scope-proposals.md` — the 3 scopers' raw proposals (`raw_proposals`).
- `reviews/scope-adversarial.md` — the adversaries' findings (`adversary_findings` + `adversary_summaries`)
  and the `convergence_map`.

Keep these verbatim — they record what the panel said, separate from what you and the user keep.

## Step 4 — Present the gate (you propose, the user disposes)

Lead with the high-signal material; triage the rest (there's no automated verify pass here, so apply
judgment — promote `blocker`/`major` findings and ones both adversaries raised; bundle nits):

1. **Fit verdict** (`fit_verdict`) — headline it. **If it's `reshape` or `poor`, the fit verdict IS
   the first decision you put to the user** (proceed-with-caveats / reshape / drop) — not merely a
   headline. Never finalize a non-clean fit without the user disposing it; that's this skill's most
   damaging failure mode.
2. **Convergence map** (`convergence_map`) — where ≥2 scopers independently agreed (highest signal).
3. **Tiered scope** (`tiered_scope`) — core / cheap folds / gated — plus the surviving `above_and_beyond`.
4. **Adversary findings** — the confirmed/high-severity ones with their fixes; note any you judge
   overstated rather than passing every nit through.
5. **Gated decisions** (`gated_decisions`) — resolve these with **`AskUserQuestion`** (or plain prose
   if it isn't available), the panel's `recommendation` as the first option each. **Batch** related
   ones — `AskUserQuestion` takes up to **4 questions per call**, so if the panel emitted more than 4,
   lead with the fit decision + the highest-leverage calls in the first round, and offer to accept the
   panel's recommendations *en bloc* for the low-stakes remainder.

Don't auto-apply adversary fixes or pick the gated decisions yourself — that's the human gate.

## Step 5 — Finalize PROJECT_SCOPE.md

Once the user has disposed the gated decisions, write `requests/feature-requests/<slug>/PROJECT_SCOPE.md` from
the template below. **Carry the panel's `tiered_scope` and `above_and_beyond` verbatim, then move only
the items the user re-tiered** — don't re-derive the tiering and risk drifting from what you presented.
Populate **Affected Area & Pointers** from the panel's `grounding_pointers` plus the request's pointers.

Then advance status. These are **in-place edits** — git is read-only here, so match existing text
exactly rather than rewriting:

- Set the request's Status blockquote to `scoped`.
- In [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md), update this feature's **Index**
  row — locate it by its `[<slug>]` link and set the Stage cell to `scoped`:
  `| [<slug>](<slug>/) | scoped | <one-line note> |`. If the feature being built is *itself a pipeline
  stage*, keep the Notes clarifying that, so its Stage isn't confused with this row's lifecycle stage.
- The new `PROJECT_SCOPE.md` opens at stage `scoped`, `next: plan`. Use **today's** date for its
  `created` (it's a new artifact; the request keeps its own date). Status is `decided` once the gated
  calls are disposed — or if there were none to dispose.

```markdown
> **Status:** scoped · created <YYYY-MM-DD> · decided · next: plan

# Project Scope — <Title>

## Fit Verdict
<one of clean / reshape / poor — and why, grounded in the repo. If the user chose to reshape or
proceed despite a poor fit, record that decision and its rationale here.>

## Problem
<the restated problem this scope solves.>

## Goals / Non-Goals
- **Goals:** <what this delivers>
- **Non-Goals:** <explicit edges — what it deliberately does not do>

## Acceptance Criteria
<numbered, each objectively TESTABLE — state how you'd verify it. e.g. "running scope_panel.js on
slug X emits a fit_verdict and ≥3 acceptance_criteria" — NOT "the panel works well". These seed the
plan's verification.>

## Scope (tiered)
- **Core (must):** <the irreducible build>
- **Folded in (cheap wins):** <low-risk enhancements included>
- **Gated — resolved:** <the judgment calls, with the user's decision on each>

## Above & Beyond
<the surviving ambitious proposals worth keeping, each tagged core / cheap / gated / deferred.>

## Risks & Unknowns
<what could go wrong or is still unknown, for the plan to de-risk.>

## Affected Area & Pointers
<the target component(s), and the concrete files / datasets (by manifest name) / docs the stage-3
implementation plan should read FIRST — carried from the request's pointers, refined by the panel's
repo-fit findings (the workflow's `grounding_pointers`). The gold IMPLEMENTATION_PLANs open with this,
so a cold plan agent can start without re-discovering the codebase.>

## Decisions
<each gated decision and how the user resolved it + a one-line rationale — the disposition record.>

## Panel Trail
<one line pointing at reviews/scope-proposals.md and reviews/scope-adversarial.md.>
```

## Step 6 — Hand off

Stage 3 turns the scope into an implementation plan via `/create-implementation-plan` — run it when
you're ready to turn this scope into a cold-handoff plan. Per project convention, **agents commit only
through `/commit`** — suggest it to land the scope. The PR stays the user's.

---

## Self-verification

**Check:** `node .claude/skills/scope-feature/tests/merge_fallback_guard.mjs` — exit 0 = a failed structured merge still yields a usable degraded scope (recovery) AND the happy path leaves the fallback inert · exit 1 = RED, read its printed reason · any other status = ERROR (did not run). Run it whenever `scope_panel.js` or this file changes.

---

## What good looks like

- **The panel actually ran.** A degraded panel (a dropped scoper or adversary) that still returns a
  tidy-looking scope is worse than an honest "it didn't run — re-run it." Check `stats` first.
- **An honest fit verdict, disposed.** A scope that can't say plainly whether the feature belongs here
  — and make you decide reshape/drop if not — isn't doing its job. Lead with fit; gate it.
- **Acceptance criteria you could hand to a tester.** "Works well" is not a criterion; an objectively
  checkable statement is.
- **Greed that's gated, not laundered.** Every ambitious idea is visible and tiered; the expensive
  ones are decisions the user made, not defaults the panel slipped in.
- **The trail survives.** The raw proposals and adversary findings live in `reviews/` even after the
  scope is trimmed — so a future reader can see what was considered and why it was cut.
