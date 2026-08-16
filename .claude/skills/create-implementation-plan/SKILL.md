---
name: create-implementation-plan
description: >-
  Turn a decided PROJECT_SCOPE into a cold-handoff IMPLEMENTATION_PLAN — a plan a fresh agent can
  execute without the author present — by running an adversarial multi-agent planning panel whose
  adversaries verify every cited file/function/line against the real code. This is stage 3 (the final
  stage) of the feature pipeline (intake → scope → plan). Use it when a PROJECT_SCOPE exists and the
  user wants the build approach: "create the implementation plan", "plan the <slug> feature/scope",
  "turn this scope into a plan", "write the IMPLEMENTATION_PLAN", or "how do we build this *now that
  it's scoped*". Stage 3 decides *how*; stage 2 (/scope-feature) decided *whether and what* — so do
  NOT use this to re-scope, for an un-scoped "how would we approach this?" (that's /scope-feature), to
  write the feature's code, or for baseball analysis questions the existing warehouse already answers.
  This skill ALSO serves the bugfix pipeline — it consumes a decided ROOT_CAUSE_ANALYSIS (under
  requests/bugfix-requests/) exactly as it does a PROJECT_SCOPE, auto-detecting the track from the artifact's path.
  If no decided upstream artifact (a PROJECT_SCOPE or a ROOT_CAUSE_ANALYSIS) exists yet, send the user to
  /scope-feature or /diagnose-bug first.
---

# Create Implementation Plan

## What this produces and why

An `IMPLEMENTATION_PLAN.md` in the resolved work-dir (`requests/<track>-requests/<slug>/` — feature or bugfix, see Step 1) — onboarding + files-to-read-first, an
architecture map, a phased plan with per-phase acceptance criteria + commit cadence, testing, decisions,
risks, a files-to-touch checklist, and the baked-in conventions — that a **cold agent can implement
without the author present**.

A plan is only as trustworthy as its citations: a step that says *"call `resolve_mon` at
`bf_analysis.py:323`"* walks the implementer into a wall if that function isn't there. So the panel's
defining rigor is **code-grounding** — its adversaries actually read/grep the repo to confirm every
cited file/function/line resolves and every claimed reuse is real:

> **3 divergent planners** (code-grounded correctness/architecture · sequencing/testability/phasing ·
> domain/convention — auto-scaling to project-convention correctness on pure-tooling features) →
> **1 merge** → **2 code-grounded adversaries** (verify every cited reference) + **1 meta-audit** (did
> the merge faithfully + completely converge the planners, without scope-creep?).

Two principles from [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md) drive it:
**greedy-but-gated** and **generate → converge → triage → you-decide** (the panel proposes; **you**
dispose). The panel runs to completion, then the **human gate is yours** — it never auto-finalizes.

---

## Step 1 — Locate the scope (and check it's ready to plan)

The panel plans from a specific **decided upstream artifact** — a `PROJECT_SCOPE.md` (feature track) or a
`ROOT_CAUSE_ANALYSIS.md` (bugfix track).

**Resolve the track + work-dir from the upstream path first** — it drives every write below: `<track>` =
`bugfix` when the upstream path is under `bugfix-requests/`, else `feature` (the default); `<work-dir>` =
`requests/<track>-requests/<slug>/`; the **track README** (whose Index you advance) is `requests/<track>-requests/README.md`.

- If the user named a slug/path, use it — `<work-dir>/PROJECT_SCOPE.md` (+ the sibling `FEATURE_REQUEST.md`)
  for a feature, or `<work-dir>/ROOT_CAUSE_ANALYSIS.md` (+ the sibling `BUGFIX_REQUEST.md`) for a bug.
- Otherwise check the **Index** in the relevant track README ([`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md)
  for a feature at `scoped`, or `requests/bugfix-requests/README.md` for a confirmed-bug RCA at `root-cause`), or
  infer from the conversation. The Index Stage cell can lag — cross-check against the artifact's own
  Status blockquote (the source of truth), not the cell alone. **If you inferred the slug, echo back the
  exact path + title and get a yes before launching** — the panel is the pipeline's heaviest.
- **If no decided upstream artifact exists, stop** — send the user to `/scope-feature` (feature) or
  `/diagnose-bug` (bug). Planning un-decided work plans work nobody decided to do.

**Disposition gate.** The Status blockquote has four fields: `<stage> · created <date> · <open|decided>
· next:`. Gate on the **3rd field (the disposition), not the stage word** — a ready scope correctly
reads `scoped · … · decided · next: plan` and a ready bugfix RCA reads `root-cause · … · decided · next:
plan`, so the stage word appearing is *expected*, not a problem.
If the disposition is `decided`, proceed. If it's `open` (gated decisions undisposed), **warn loudly**
that you'd be planning on top of unmade decisions, and offer to proceed or send the user back to finish
scoping.

## Step 2 — Run the planning panel

This is **this skill's multi-agent panel** and the pipeline's heaviest — ~7 high-effort agents (3
planners → merge → 2 code-grounded adversaries → 1 meta-audit), each reading the scope + multiple repo
files. It costs real tokens and takes several minutes; tell the user it's running and what it's doing
**before** you launch.

Run the bundled script by **absolute** path (resolve repo-root + the segment; a non-resolving path
means recompute the repo-root, not give up):

```
Workflow({
  scriptPath: "<repo-root>/.claude/skills/create-implementation-plan/plan_panel.js",
  args: { scopePath:   "<work-dir>/<upstream>",   // <upstream> = PROJECT_SCOPE.md (feature) | ROOT_CAUSE_ANALYSIS.md (bug); passed in the scopePath slot either way
          requestPath: "<work-dir>/<intake>",     // <intake> = FEATURE_REQUEST.md | BUGFIX_REQUEST.md; optional context, omit if none
          slug:        "<slug>" }
})
```

The `args` object is required in **both** modes. If the path truly won't resolve, read `plan_panel.js`
and pass its contents as the `script` parameter — but still pass `args`. The Workflow tool runs the
panel in the background and notifies you when it completes (watch with `/workflows`); the result is the
returned tool output. If it has an `"error"` key (**all planners failed** — a *merge* failure no longer
errors out: the panel now recovers it to a degraded plan, flagged in `degraded_lenses`, see Step 3), report
it and stop — the payload carries `raw_proposals`, so surface how far it got. The panel's subagents are
**read-only** (they ground in the repo but never modify files or run git).

## Step 3 — Wait for completion, check panel health, save the trail

**Wait for the structured result before continuing** — a launch acknowledgement isn't the result (it
carries `plan_draft`, `gated_decisions`, `stats`, etc.).

**Check the panel ran in full** via `stats` — expect `planners_ok` = 3, `adversaries_ok` = 2,
`meta_audit_ok` = 1. The panel auto-retries a stubbed lens once and counts it `ok` only on real
content, so these counts are honest (not fooled by a schema-valid stub); the `degraded_lenses` array
lists any lens still stubbed after the retry — treat those with the recovery below:
- **`degraded_lenses` includes `merge:fallback`** → the forced structured merge failed and the panel
  RECOVERED: `plan_draft` is a deterministic, de-duplicated UNION of the planner proposals (phases are
  prefixed by planner, e.g. `[sequencing] …`), not a true synthesis — and if the free-text best-effort
  also failed, `summary`/`architecture_map` carry a `[DEGRADED]` marker. It's usable-but-provisional:
  surface the degradation to the user, spot-check the union, and consider re-running the panel on a
  smaller input (lighter proposals) to get a real synthesis before landing it.
- **One lens dropped** → you may re-run just that role as a direct free-text `Agent` subagent (reliable
  where StructuredOutput degenerates) and fold its prose findings into the relevant array for Step 4. A
  dropped **meta-audit** is re-run by handing a fresh `Agent` the merged `plan_draft` + `raw_proposals`
  with the meta-audit mandate (it audits the *merge*, not a planner lens).
- **Two or more dropped** (the documented multi-collapse a heavy panel is *more* exposed to) → **re-run
  the whole panel**; don't hand-patch a gutted run.
- **`planners_ok < 2`** → there was no real convergence (the merge is a single-lens pass-through, and
  `convergence_map` is meaningless) — say so plainly and offer to re-run.

**Verify the code-grounding actually landed.** It's the stage's whole point but it's enforced only by
prompt, so don't take it on faith: an empty `adversary_findings` on a citation-heavy plan is *suspect*
(a degenerated adversary returns `[]`, which looks identical to "all clean"). Spot-check that a sample
of the plan's `code_references` actually resolve (you have the tools); if they don't — or the
code-grounded adversary returned nothing on a plan full of cites — re-grep yourself or re-run that
adversary as a direct `Agent` before trusting the plan.

Then write the raw, unfiltered panel output under `<work-dir>/reviews/` (the resolved track dir; Write
auto-creates it):

- `reviews/plan-proposals.md` — the returning planners' raw proposals (`raw_proposals`).
- `reviews/plan-adversarial.md` — `adversary_findings` + `meta_audit_findings` + `reviewer_summaries`
  + the `convergence_map`.

## Step 4 — Present the gate (you propose, the user disposes)

**Surface (triage)** — lead with the rigor that defines this stage:

1. **Code-grounding findings** (`adversary_findings`, the code-grounded adversary) — a dangling/wrong
   reference is **objective**, not a judgment call. Surface each with its real `file:line` and the
   correction; these get **applied automatically in Step 5** and do *not* compete for AskUserQuestion
   slots.
2. **Meta-audit findings** (`meta_audit_findings`) — did the merge scope-creep, drop a planner's
   contribution, or assert a fictional "reuse"? Surface the real ones.
3. **Executability findings** (the second adversary) — unordered phases, vague acceptance, missing steps.
4. **Convergence map** — where ≥2 planners agreed (highest signal).

**Decide (the gate)** — only the genuine judgment calls go to the user:

5. **Gated decisions** (`gated_decisions`) — resolve with **`AskUserQuestion`** (or plain prose if
   unavailable), the panel's `recommendation` first each. **Batch** — it caps at **4 questions per
   call**, so if there are more, lead with the highest-leverage and offer to accept the rest *en bloc*.
   (Code-grounding must-fixes are objective and never belong in this budget — they're applied, not asked.)

Don't pick the gated decisions yourself — that's the human gate.

## Step 5 — Finalize IMPLEMENTATION_PLAN.md

Once the user has disposed the gated decisions, write `<work-dir>/IMPLEMENTATION_PLAN.md` (the resolved
track dir) from the **section-menu** template below. **Carry the panel's `plan_draft` into the document, fold in the
user's decisions, and APPLY every confirmed code-grounding correction** — a plan that ships with a
flagged dangling reference defeats the stage. The template is a **menu**: each section is tagged
*Always* / *Default* / *Conditional*; include conditionals only when this feature needs them — a change
that touches no data carries no data-contracts section, while anything landing a new source must.

Then advance status (the file edits are expected — the read-only rule means **don't run git**, no
`commit`/`checkout`/`reset`; not "don't edit files"). Match existing text exactly:

- In the **track README** — `requests/feature-requests/README.md` for a feature, `requests/bugfix-requests/README.md` for a
  bug (the one matching the resolved track, **never** the other) — set this item's **Index** row Stage
  cell to `plan` (match the row by its `[<slug>]` link).
- The new `IMPLEMENTATION_PLAN.md` opens at stage `plan`, `next: implement`, `created` = today.

```markdown
> **Status:** plan · created <YYYY-MM-DD> · decided · next: implement
<!-- Use this README status grammar (<stage> · created · <open|decided> · next:). The two gold plans
predate it and use a freer "Status: Approved/Draft — …" line; follow this form, not theirs. -->

# Implementation Plan — <Title>

> **One-line goal:** <what shipping this delivers> · **Target component:** <the file(s)/dir(s) touched>

## 1. Onboarding — read these first  [Always]
<what the feature is + a files-to-read-first table (real paths + why), so a cold agent starts without
re-discovering the codebase.>

## 2. Architecture map  [Default — include unless it's a single-file change with no structure]
<the touched area's current structure and where the change hooks in.>

## 3. Phased implementation  [Always — the spine]
<an ordered sequence of phases. For EACH: goal · steps · acceptance criteria (objectively checkable) ·
a commit note. Each phase ends at a **gated checkpoint**: implement → green locally (`uv run pytest`,
and `uv run ruff check`) → `/commit`, which stages, checks the docs,
and asks before writing. CI re-runs the same gates on the PR.>

## 4. Testing & verification  [Always]
<how the whole thing is verified + regression safety.>

## 5. Decisions  [Always]
<the design decisions baked into the plan, with rationale (carry the scope's resolved decisions + any
the panel added) — and record any gated decisions accepted *en bloc* and how they were disposed, so the
disposition trail survives.>

## 6. Risks & gotchas  [Always]
<what could bite the implementer, and the mitigation.>

## 7. Files to touch (checklist)  [Always]
<the real-path checklist the implementer works down.>

## 8. Conventions (bake these in)  [Always — include the conventions that APPLY]
<the CLAUDE.md rules the implementer must honor: the game is read-only (no save writes, no roster
import files, no UI automation); the parser walks records sequentially and never seeks to a fixed
offset; ground truth is players.csv, never an in-game screenshot; an unvalidated field mapping is
labelled `unconfirmed`; no OOTP game data in git; paths resolve from `.env` and datasets resolve by
logical name; commits go through /commit only; subagents get read-only git. Don't force irrelevant
conventions onto a change that doesn't touch the parser or the warehouse.>

## 9. Data contracts touched  [Conditional — only if the feature adds/edits a dataset]
<the source registration, the declared grain + the test that proves it, the era coverage and which
columns are structurally absent before which season, the update semantics (merge key), and the
extraction cost. Omit entirely otherwise.>

## 10. Code-grounding verification  [Conditional — include whenever the adversaries verified references]
<the trust ledger: on a clean run a one-liner ("N cites checked, 0 corrected"); when refs were
corrected, a short table of cited-reference → verified/corrected. It's the fingerprint that the stage's
defining rigor actually ran — keep it even after the corrections are applied.>

## References  [Always]
<the key files/docs, by real path.>
```

## Step 6 — Hand off

The `IMPLEMENTATION_PLAN.md` is the deliverable — ready to hand to a fresh agent to implement. Point the
user there. Per project convention, **agents commit only through `/commit`** — suggest it to land the plan.

---

## Self-verification

**Check:** `node .claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs` — exit 0 = a failed structured merge still yields a usable degraded plan (recovery) AND the happy path leaves the fallback inert · exit 1 = RED, read its printed reason · any other status = ERROR (did not run). Run it whenever `plan_panel.js` or this file changes.

**Check:** `node .claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs` — exit 0 = with every planner succeeding and the structured merge throwing, the panel still returns a usable plan draft carrying at least one phase rather than a bare error · exit 1 = RED, read its printed reason · any other status = ERROR (did not run). Run it whenever `plan_panel.js` or this file changes.

---

## What good looks like

- **Every relative link and bare `requests/...` token you write must resolve on disk.** A live
  (non-`_done/`) artifact body is scanned by `tests/test_request_links.py`, a blocking CI
  check, so a dead pointer here fails the build rather than quietly misleading the next stage. Two
  shapes to watch: a **forward reference** to a file a later stage creates, and a deliberately
  **broken example path**. Put either inside a fenced code block (``` or ~~~, blockquoted is fine) —
  fenced content is exempt, precisely so a report can quote a dead target. Citations may carry a
  `file.py:123` suffix; `var/` targets and link titles are exempt too.

- **Every citation resolves.** The whole point of the stage is that a cold agent can trust the plan's
  file/function/line references. A shipped dangling reference is a stage failure, not a nit — and an
  empty adversary findings list on a citation-heavy plan is a red flag, not a clean bill.
- **The panel actually ran.** A degraded panel (a dropped adversary or the meta-audit) that still
  returns a tidy plan is worse than an honest "re-run it." Check `stats` first.
- **Phases a stranger could execute.** Each phase ordered, independently verifiable, with an acceptance
  criterion you could hand to a tester and a user-committed checkpoint — not "implement, then test."
- **The scope was consumed, not re-opened.** The plan builds what stage 2 decided; if a planner
  re-litigated fit/goals, the merge or an adversary should have caught it.
- **The trail survives.** Raw proposals + adversary/meta findings live in `reviews/` even after the
  plan is trimmed.
