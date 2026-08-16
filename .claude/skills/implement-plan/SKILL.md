---
name: implement-plan
description: >-
  Execute a decided IMPLEMENTATION_PLAN — actually write the code/data/skill — then prove it with a
  context-aware adversarial ACCEPTANCE panel that verifies every acceptance criterion by running it,
  not by asserting it, before handing off to /commit. This is stage 4 (the final stage) of the
  feature pipeline (intake → scope → plan → implement). Use it when an IMPLEMENTATION_PLAN.md exists
  and the user wants it built: "implement the <slug> plan", "build the <slug> feature now that it's
  planned", "execute the IMPLEMENTATION_PLAN", "do the implementation", or as the natural follow-up to
  /create-implementation-plan. The panel auto-scales its reviewers to what the change touches
  (parser, dbt models, a dataset builder, a new skill). Stage 4 builds *what stage 3 planned* — so do
  NOT use this to re-plan (that's /create-implementation-plan) or re-scope (/scope-feature), and do NOT
  use it for baseball analysis questions. It serves BOTH tracks — a feature's
  IMPLEMENTATION_PLAN (under requests/feature-requests/) or a bugfix's (under requests/bugfix-requests/), auto-detected from
  the path; for a bugfix run, "done" = the red repro goes green + a regression test is left behind. It also
  has a DIRECT-BUILD MODE for work whose intake artifact carries an argued stage skip (ADR 0008): the
  request stands in for the plan and the adversarial panel runs at full strength on the diff. If there is
  no IMPLEMENTATION_PLAN.md and no argued skip, send the user to /create-implementation-plan first (or
  /scope-feature / /diagnose-bug if there isn't even a decided upstream artifact).
---

# Implement Plan

## What this produces and why

Working, **reviewed** code (or models, or a new skill) that satisfies *every* acceptance criterion the
plan promised — built from a decided `IMPLEMENTATION_PLAN.md`, put through a context-aware adversarial
**acceptance panel**, then handed to **`/commit`**, the repo's only sanctioned committer — it stages,
checks the docs, and asks before writing. The feature ends at status `implemented`.

A plan is a promise; an implementation either keeps it or quietly doesn't. The failure this stage exists
to prevent is a feature that *looks* done — green tests, tidy diff — but ships with acceptance
criterion 4 silently unmet, or a bug on the one edge case nobody exercised. So the panel's defining
rigor is **verification by execution**: its reviewers don't take "criterion met" on faith, they *run*
`uv run pytest`, or the domain core against a fixture, and read the real
output. A claimed-met criterion that isn't is a **blocker**, exactly like a dangling citation is a
blocker at stage 3.

> **Implement** the plan's phases in order (each self-verified) → **snapshot** the tree → a
> context-aware **acceptance panel** (4 core reviewers + auto-scaled specialists → execution-based
> **verify** → **meta-audit**) → **you dispose** the judgment calls → **`/commit`**.

Two principles from [`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md) carry through:
**greedy-but-gated** (objective fixes are applied; scope-growing calls go to you) and **generate →
converge → triage → you-decide** — the panel proposes, **you** dispose. It never auto-finalizes.

---

## Step 1 — Locate the plan (and check it's ready to implement)

This stage executes one specific **`IMPLEMENTATION_PLAN.md`** — on either track.

**Resolve the track + work-dir from the plan's path first** (it drives every write below): `<track>` =
`bugfix` when the path is under `bugfix-requests/`, else `feature` (the default); `<work-dir>` =
`requests/<track>-requests/<slug>/`; the **track README** (whose Index you advance) is `requests/<track>-requests/README.md`.

- If the user named a slug/path, use `<work-dir>/IMPLEMENTATION_PLAN.md` (+ the sibling upstream artifact —
  `PROJECT_SCOPE.md` for a feature or `ROOT_CAUSE_ANALYSIS.md` for a bug, which carries the acceptance
  criteria — and the intake doc for context).
- Otherwise check the **Index** in the relevant track README ([`requests/feature-requests/README.md`](../../../requests/feature-requests/README.md),
  or `requests/bugfix-requests/README.md`) for an item at the `plan` stage, or infer from the conversation. The Index Stage cell can lag —
  cross-check against the artifact's own Status blockquote (the source of truth). **If you inferred the
  slug, echo back the exact path + title and get a yes before launching** — this run *mutates the repo*,
  so it's the heaviest of all four stages.
- **If no `IMPLEMENTATION_PLAN.md` exists, check for an argued skip before stopping.** Per
  [ADR 0008](../../../docs/decisions/0008-panels-by-default.md) the panel stages are the default, but
  an intake artifact may carry a **Stage plan** section arguing a skip. Open it and read that section:

  - **An argued skip, disposed by the user** → **direct-build mode** (below). The intake artifact is
    the statement of intent; its Status blockquote should read `… · decided · next: implement`.
  - **No Stage plan section, or one that proposes the full pipeline, or a skip the user hasn't
    disposed** → **stop** and send the user to `/create-implementation-plan` (or back to
    `/scope-feature` / `/diagnose-bug` if there isn't even a decided upstream artifact).

  **This branch is not a shortcut, and must not become one.** Implementing an unplanned change still
  builds work nobody sequenced — the *only* thing that makes it legitimate is an argument someone
  wrote down and the user disposed. A missing plan is not by itself permission; a missing plan plus a
  missing Stage plan is the case this stage refuses.

**Direct-build mode.** Everything downstream is unchanged except what the panel is handed:
`planPath` takes the **intake artifact** (`FEATURE_REQUEST.md` or `ROOT_CAUSE_ANALYSIS.md`) and
`scopePath` is **omitted** — the panel already degrades to a single intent document. Step 3's
phase-by-phase walk becomes a straight build against the request's Desired Outcome and Scope
Signals; honor *Explicitly out* as the boundary a plan's §7 checklist would otherwise supply.

Be honest about what the ledger then is: criteria **derived** from a Desired Outcome, `source:
request`, not a promise-kept check against numbered criteria. That's expected — an item needing
numbered criteria trips ADR 0008's first trigger and never reaches this branch. Say so in the report
rather than presenting a derived ledger as if it were a scoped one.

**Disposition gate.** The Status blockquote reads `<stage> · created <date> · <open|decided> · next:`.
Gate on the **3rd field (disposition), not the stage word** — a ready plan reads `plan · … · decided ·
next: implement`, so the word `plan` appearing is *expected*. If `decided`, proceed. If `open` (gated
decisions left undisposed), **warn loudly** that you'd be building on unmade decisions, and offer to
proceed or send the user back to finish planning.

**Respect the plan's own boundaries.** Read it in full first. If it **defers** phases (a v1 cut, a
"Rollout" section, phases marked deferred), implement only the active set — do not build deferred work
unless the plan was explicitly re-activated. The plan is **decided**: consume it, don't re-open its
phases, decisions, or acceptance criteria (that was stages 2–3).

## Step 2 — Set up a safe workspace

This stage writes to the tree, so isolate it. Confirm a clean starting state (`git status`), and **work
on a feature branch**, never the default branch directly (`git switch -c implement/<slug>` off
`master`/`main` if you aren't already on one) — the data-arch refactor ran 8 commits on a branch before
the user merged, and that's the pattern. Tell the user which branch you're on.

## Step 3 — Implement the plan, phase by phase

Walk the plan's **§3 Phased implementation IN ORDER** — do not big-bang. For each phase:

1. **Implement** its steps, honoring the plan's **§7 files-to-touch** checklist and **§8 conventions**
   literally (the cold-handoff plan baked them in so you can't violate CLAUDE.md by following it).
2. **Self-verify** the phase's own acceptance criteria *by running them* — `uv run pytest`,
   the domain core against a fixture. Read the **actual output**; do not
   assume green. A red check stops the phase — fix before moving on.
3. **Trust but verify the plan's citations.** Stage 3 code-grounded them, but the repo may have drifted
   since. Before relying on a cited `file:line`/function, confirm it still resolves; re-ground if it
   moved (and note the drift for the final report).

Honor the repo's hard constraints as you build (the relevant specialist reviewer will check each):

- **Resolve by name.** Datasets resolve through `datasets/manifest.json` — never a literal path. Game
  and save locations resolve from `.env` — never a hardcoded path or a `parents[N]` walk.
- **The game is read-only.** Nothing writes a save, a roster import file, or automates the game UI
  (ADR 0001). A Challenge Mode save carries an integrity hash that one write destroys irreversibly.
- **The parser walks records sequentially and never seeks to a fixed offset.** Records carry
  variable-length regions; a fixed-offset read passes on day-0 data and silently corrupts everything
  after it.
- **Ground truth is `players.csv`, never an in-game screenshot.** Displayed ratings are
  scale-converted and possibly scout-filtered; matching one to a byte identifies the wrong field with
  no error raised. A field mapping with no validating test is `unconfirmed`, and must say so.
- **No OOTP game data in git** (ADR 0006). A model whose declared grain has no test is not green.
- **Epistemics are labelled.** `unconfirmed` beliefs about an external source are tasks, not facts. Code that
  assumes an unverified source shape is a blocker until someone has actually pulled it.
- **Anything outward-facing is user-run.** Pushes, merges, and branch-protection changes. Stage it and route it to
  the user; take verification from their pasted output. Don't auto-run-and-confirm an outward-facing step.
- **Windows dev, Linux CI.** `.gitattributes` normalizes line endings. Don't write files with
  PowerShell's `Set-Content`/`Out-File` — in PS 5.1 they mangle UTF-8. Use the file-editing tools.

Implement *all* active phases this way, accumulating one working-tree diff (you'll run **one** panel at
the end and hand the whole thing to the user — for a very large or risky build you may instead ask the
user to commit a completed phase as a checkpoint, but that's the exception, not the default).

## Step 4 — Snapshot, then run the acceptance panel

**Snapshot first (safety net, not a commit).** Before spawning any subagent, save the uncommitted change
so a stray revert can't lose it: write the diff to gitignored scratch —
`git diff HEAD > var/tmp/<slug>-pre-review.patch` and record any untracked files. The panel's subagents
are read-only *by instruction*, but instructions aren't enforcement: a write-capable review agent once
ran `git checkout` and silently wiped uncommitted work while a vacuous selftest passed green. The patch
(plus the feature branch) is the belt to that suspenders.

**Bucket the diff into touched areas**: from `git status --porcelain` +
`git diff HEAD --stat`, note which of `src` (parser, landing, warehouse loading) · `transform`
(dbt models) · `datasets`/`build` (static reference builders) · `tests` · `skills`
(`.claude/skills/`) · `ci` (`.github/workflows/`) · `config` (`pyproject.toml`) · `docs` the change
touches. This list drives which **specialist reviewers** the panel spins up — show the user the roster
before launching.

**The roster self-scales, which is why there is no economy mode.** Specialists are matched to the
touched areas, so a small change draws the four core reviewers and perhaps one specialist while a
sprawling one draws the full bench. The size of the work already governs the size of the panel —
resist adding a "quick" variant, which would be a second and worse control over the same variable
(ADR 0008). `verifyCap` is the one legitimate lever, and it bounds fan-out, not coverage.

Then run the bundled panel by **absolute** path (resolve repo-root + the segment):

```
Workflow({
  scriptPath: "<repo-root>/.claude/skills/implement-plan/acceptance_panel.js",
  args: { planPath:  "<work-dir>/IMPLEMENTATION_PLAN.md",   // DIRECT-BUILD MODE: the intake artifact instead — FEATURE_REQUEST.md | ROOT_CAUSE_ANALYSIS.md
          scopePath: "<work-dir>/<upstream>",   // <upstream> = PROJECT_SCOPE.md | ROOT_CAUSE_ANALYSIS.md — the acceptance source, passed in the scopePath slot; omit if none (always omitted in direct-build mode)
          slug:      "<slug>",
          touchedAreas: ["transform","src", ...],                  // from the bucketing above
          verifyCap: 4 }                                           // OPTIONAL — max verify-batch agents (default 4); raise for a sprawling diff, lower to economize
})
```

`args` is required in both modes. If the path won't resolve, read `acceptance_panel.js` and pass its
contents as `script` — but still pass `args`. The panel runs in the background (watch with
`/workflows`); the result is the returned tool output. If it has an `"error"` key (**all reviewers
failed** — a *synthesis* failure no longer errors out: the panel now recovers it to a degraded
acceptance report, flagged by `synthesize:fallback` + `meta:skipped-degraded` in `degraded_lenses`),
report it and stop. A recovered (degraded) report is reconciliation-free — its ledger is the surviving
cross-check verbatim and its verdict is forced to `fix` (never `go`); treat the verdict as provisional
and re-run before trusting it.
**The panel's subagents are read-only** — they `git diff`/grep/read and *run* selftests to verify, but
modify no file and run no working-tree-mutating git.

## Step 5 — Check panel health, re-verify integrity, save the trail

**Wait for the structured result** (a launch ack isn't it). Then:

**Check the panel ran in full** via `stats` — `reviewers_ok` should equal the roster size; `meta_ok` = 1.

The verify counts read at **two levels**, and you need both. `verifiers_ok` / `verifiers_total` count
verify **agents** — at most `verify_cap` (default 4) location-grouped *batch* verifiers, each adjudicating
several findings, **plus the standalone independent acceptance-ledger verifier** (so a zero-finding run
still has 1). Agents being green does *not* mean every finding got checked: that is
**`findings_unverified`, which must be 0**. Anything above 0 means a batch died or skipped an id, and
`degraded_lenses` names the batch **and how many findings it took down** (`verify:b2 (3 findings left
unverified)`). `findings_blocker_major_raw` vs `_deduped` shows how many cross-lens duplicates were
merged before fan-out — a merged finding keeps every raising reviewer in its `reviewers`, so a large gap
there is normal convergence, not lost signal.

If `degraded_lenses` lists `verify:ledger`, the independent double-ledger cross-check did **not** run that
pass — treat the ledger as single-source (auditor-only) and re-run if you need the redundancy. The panel
auto-retries a stubbed lens once and counts it `ok` only on real content, so the counts are honest; that
includes a **rubber-stamped batch** (every row sharing one blob of evidence), which is rejected rather
than accepted.
Recover as stage 3 does: **one** dropped lens → re-run just that role as a direct free-text `Agent`
(reliable where StructuredOutput degenerates) and fold its findings in; **two or more** → re-run the
panel; if the **acceptance** lens itself dropped, you have no ledger — re-run it before trusting any
verdict. For a dropped **verify batch**, re-run just that batch's findings (they're the ones marked
`unverified` in `verified_findings`) — don't let them reach the ledger as if they'd been checked. An
**empty findings list on a substantial diff is suspect** (a degenerated adversary returns `[]`,
indistinguishable from "all clean") — spot-check before believing it.

**Re-verify tree integrity.** A subagent had Bash; don't trust a green panel blindly. Re-check `git
status` against your snapshot and grep for a couple of symbols you implemented — confirm nothing was
reverted (a passing selftest does *not* prove your code is still there; assertions for missing symbols
are skipped, not failed).

**Save the trail** under `<work-dir>/reviews/` (the resolved track dir; Write auto-creates it):
`reviews/implementation-review.md` — the acceptance ledger + confirmed findings + verify results +
meta-audit + reviewer summaries.

## Step 6 — Present the gate (you propose, the user disposes)

**Surface (triage)** — lead with the rigor that defines this stage:

1. **The acceptance ledger** (`acceptance_ledger`) — every criterion as **met / partial / unmet** with
   the **evidence** (the command output or `file:line` that proves it), reconciled against the
   execution-verifier. An unmet or only-partial criterion on the core path is **objective** — it gets
   fixed, it does not go to a vote.
2. **Confirmed findings** (`confirmed_findings`, verify-confirmed only) — real bugs, convention
   violations, missing edge-case handling, each with a grounded location and fix.
3. **Meta-audit** (`meta_findings`) — did the synthesis drop a confirmed blocker, or is a criterion
   covered by *no* reviewer (a verification gap)?

**Decide & act:**

- **Auto-fix objective blockers** — unmet/partial acceptance criteria and verify-confirmed bugs get
  fixed in the tree now, then **re-verified** (re-run the affected reviewer/selftest; for a big change,
  re-run the panel). Mirror stage 3: objective must-fixes are applied, not asked.
- **Route genuine judgment calls** (`gated_decisions`) to **`AskUserQuestion`** (panel's recommendation
  first), e.g. a plan deviation that might be intentional, a trade-off, an above-and-beyond fold-in.
  Cap **4 per call**; lead with the highest-leverage and offer the rest *en bloc*.
- **Surface manual gates + user-run steps** — any acceptance check a selftest can't cover (a real-mon
  spot-check), and any **system/global step you staged for the user** (Step 3): list them explicitly so
  they aren't silently skipped.

## Step 7 — Finalize & hand off

Write `<work-dir>/IMPLEMENTATION_REPORT.md` (the resolved track dir) from the template below — the acceptance ledger
is its spine (it's the `N/N criteria met` line the gold features carry). Then advance status (file edits
are expected — the read-only rule is for *subagents*; **don't run git** here):

- In the **track README** — `requests/feature-requests/README.md` for a feature, `requests/bugfix-requests/README.md` for a
  bug (the resolved track, **never** the other) — set this item's **Index** row Stage cell to
  `implemented` (match the row by its `[<slug>]` link).
- The report opens at `implemented · created <today> · decided · next: commit`.

Then **hand off to `/commit`** — per project convention, never `git commit` ad hoc. `/commit` runs the
doc checks (a build like this almost always warrants the full `/update-docs` sweep), shows the staged
list, and asks — then commits and pushes the branch on your yes. Opening the PR stays the user's. CI
re-runs the mechanical gates there; a red check is **stop-and-fix**, not a retry-loop.

```markdown
> **Status:** implemented · created <YYYY-MM-DD> · decided · next: commit

# Implementation Report — <Title>

> **One-line outcome:** <what now works> · **Acceptance:** <N>/<N> criteria met · **Branch:** implement/<slug>
> <direct-build runs add: **Mode:** direct build — no PROJECT_SCOPE/IMPLEMENTATION_PLAN, per the argued
> Stage plan in the intake artifact. Criteria below are derived from its Desired Outcome.>

## 1. Acceptance ledger  [Always — the spine]
<a table: criterion · met / partial / unmet · evidence (command output / file:line). This is the proof.>

## 2. What shipped  [Always]
<the phases implemented + the files touched, against the plan's §7 checklist.>

## 3. Deviations from the plan  [Always — even if "none"]
<where the implementation departed from the plan and why; any phase deferred.>

## 4. Verification & edge cases  [Always]
<what the panel ran to verify, the edge cases exercised, regression safety.>

## 5. Findings resolved  [Conditional — if the panel raised any]
<the confirmed blockers/majors and how each was fixed (or disposed).>

## 6. Manual gates & user-run steps  [Conditional — if any]
<acceptance checks needing a human, and any system/global step staged for the user to run.>

## 7. Hand-off  [Always]
<what's needed to land it (/commit, then the user's push + PR); note any follow-up scope the build
surfaced.>
```

---

## Self-verification

**Check:** `node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs` — exit 0 = a failed synthesis still yields a usable degraded acceptance report with the meta-audit skipped (recovery) AND the happy path leaves the fallback inert with the meta-audit running · exit 1 = RED, read its printed reason · any other status = ERROR (did not run). Run it whenever `acceptance_panel.js` or this file changes.

**Check:** `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` — exit 0 = the Verify phase stays under its cap, merges only true duplicates, groups findings by location, adjudicates each against its own id, and degrades honestly when a batch dies or rubber-stamps · exit 1 = RED, read its printed reason · any other status = ERROR (did not run). Run it whenever `acceptance_panel.js` or this file changes.

---

## What good looks like

- **Every acceptance criterion is verified by execution, not asserted.** The ledger cites real output.
  A green test the panel didn't re-run is not proof.
- **The panel actually ran.** A degraded panel (a dropped acceptance lens, a silent stub) that still
  returns a tidy verdict is worse than an honest "re-run it." Check `stats` and `degraded_lenses` first;
  an empty findings list on a big diff is a red flag, not a clean bill.
- **Reviewers never touched the tree.** Read-only subagents, snapshot taken, integrity re-checked after.
- **The plan was consumed, not re-opened.** You built what stage 3 sequenced; deviations are conscious
  and recorded, deferred phases stayed deferred. In direct-build mode the request's *Explicitly out*
  is the boundary that a plan's checklist would have been — respect it the same way.
- **A direct build said it was one.** The report names the mode and the argued skip behind it, and its
  ledger is labelled as derived from a Desired Outcome rather than dressed up as scoped criteria.
- **Outward-facing steps went to the human.** Anything that pushes, merges, changes repo settings, or writes to
  prod was staged for the user to run, not executed and "confirmed."
- **It handed off, it didn't commit.** The user is the committer; the report + `implemented` status
  + the `reviews/` trail are the deliverables.
