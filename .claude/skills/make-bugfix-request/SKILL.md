---
name: make-bugfix-request
description: >-
  Turn a DEFECT in this platform's existing code, config, or tooling into a clean, repro-grounded bug
  report — the deliverable a fresh agent can pick up for root-cause analysis. This is stage 1 of the
  BUGFIX pipeline (intake -> root-cause -> reuse plan/implement), the parallel of make-feature-request for
  things that are BROKEN rather than missing. Use it whenever something that already exists FAILS: an
  builder that errors, a parser that raises on a save it should read, a CI workflow that passes when it shouldn't, a
  path resolution that breaks, a skill that misfires, "this used to work", a regression, a crash or
  traceback. It captures symptom + a reproduction attempt + expected-vs-actual + severity, and triages
  obvious-hotfix vs needs-the-full-track vs actually-a-feature. Prefer this over an ad-hoc fix: a defect
  with no recorded repro, cause, or regression guard is how the same bug comes back. Do NOT use it for a
  missing CAPABILITY (something that doesn't exist yet — that's a feature, use make-feature-request), for
  WRONG DATA produced by a run that went green (that's a data incident — see
  requests/data-incidents/README.md), or for a defect already captured in an existing
  requests/bugfix-requests/ directory. Tie-break: did anything actually fail? If the pipeline was green
  and the output is still wrong, it is an incident, not a bug.
---

# Make Bugfix Request

## What this produces and why

A single `BUGFIX_REQUEST.md` in `requests/bugfix-requests/<slug>/` — a tight, honest statement of **what's broken,
how to make it happen, and how much it hurts**, grounded in the actual repo, that a cold agent (running
`/diagnose-bug`) can pick up without re-discovering the symptom.

The point of intake is to **separate the symptom from the cause**, and to start the **reproduction** —
the through-line of the whole track. People often arrive with a cause already guessed ("the pagination
logic is dropping rows"). Capture that hunch, but don't enshrine it: a request anchored to the first guess
forecloses the real diagnosis. The job here is to pin the *observable* defect + the steps that trigger it,
record the reporter's cause-hunch as non-binding, and leave the verdict to `/diagnose-bug`.

Keep it light. A one-line typo fix shouldn't need a ceremony — capture it, triage it `obvious-hotfix`,
and move on. Read [`requests/bugfix-requests/README.md`](../../../requests/bugfix-requests/README.md) once for the track's
conventions (layout, status grammar, the defect acceptance contract, the stages downstream).

---

## Step 1 — Sanity-check, then understand the ask

Intake is the cheapest place to stop work that shouldn't become a bug report, so gate first. Confirm this
is a real **defect in something that already exists**, and not one of:

- a **missing capability** — a tool/dataset/skill that doesn't exist yet. That's a *feature*; redirect to
  `/make-feature-request`. **Do a cheap sniff only** (the authoritative bug-vs-feature verdict is
  `/diagnose-bug`'s job): if it's plainly "build me X", redirect; if it's genuinely ambiguous ("X handles
  every case but this one"), capture it as a bug and let diagnosis render the verdict.
- a **data incident** — the run went green and the numbers are wrong. Nothing failed, so there is no
  crash to diagnose; the question is which of four layers diverged, and it owes a restatement plan this
  track doesn't. Redirect to [`requests/data-incidents/README.md`](../../../requests/data-incidents/README.md).
  **Cheap sniff only:** if something visibly errored, it's a bug — even if bad data came out too.
- an **analysis question** — a baseball answer the existing warehouse already produces. That's using the
  platform, not a defect in it.
- work **already captured** — scan `requests/bugfix-requests/` for a matching `<slug>/` and continue that one.

Then start from what's on the table. The triggering message usually carries most of the report — the
symptom, maybe a guessed cause, a file or command by name. Extract that first. Form a one-line working
summary of the *observable* defect (not the guessed cause).

## Step 2 — Reproduce, then ground it in the repo

This is the step that makes the report worth writing — it starts the repro that the whole track rides on.

- **Attempt a reproduction.** Get the exact inputs + the command or skill invocation that triggers it,
  and capture the **actual output** vs what was **expected**. If it won't reproduce reliably, say so and
  record the conditions where it appeared (intermittent / specific inputs / "after I changed Y"). You are
  not fixing it — you're pinning what a diagnosis agent must make go RED.
- **Ground it.** Which subsystem does the symptom point at — extraction/landing
  (`src/ootp_ai/`), a dbt model (`transform/`), a dataset builder (`build/`), CI (`.github/workflows/`), a skill
  (`.claude/skills/`), or project config (`pyproject.toml`)? Name the
  1–3 files a cold diagnosis agent opens first. A best guess is fine; RCA confirms it. Aim for **~2–5
  targeted lookups** — enough to point, not to diagnose. If you're reading deep to work out *why*, you've
  overshot — that's `/diagnose-bug`'s job.

## Step 3 — Interview to fill the gaps

Ask only what the conversation and the repo didn't already answer. Batch related questions. The
high-value gaps:

1. **Symptom** — the incorrect behavior/output, concretely. A pasted wrong number/traceback beats a
   paraphrase.
2. **Reproduction** — the minimal steps/inputs. Is it deterministic or intermittent?
3. **Expected vs actual** — what *should* happen, and the source of that expectation (a mechanic, a
   hand-calc, a prior correct run).
4. **Severity** — how much it hurts + urgency. Rank above cosmetic anything that **corrupts or drops
   landed data**, **spends cloud money unexpectedly**, or **produces a number someone might act on**.
   The ledger is append-only for a reason; a defect that mutates a recorded event is the worst class here.
5. **Regression?** — did it used to work? What changed — a recent commit, a dependency bump, or an
   **upstream API change**? That last one is uniquely likely here and uniquely easy to miss, since
   an external source ships breaking changes without notice.

If baseball or save-format specifics matter (a stat the model computes wrongly), pin the *expected* behavior here —
and say where the expectation comes from — so diagnosis has a target. But don't diagnose.

## Step 4 — Draft the report

Propose a **slug** (kebab-case, descriptive — `extractor-drops-final-page`, not `bug-3`). Before creating
anything, **check the slug doesn't collide**: list `requests/bugfix-requests/` and scan its README Index. Never
write into an existing slug dir without explicit confirmation (git is read-only here, so a clobbered
report is hard to recover). Fold the slug confirmation into the Step-5 review.

Create `requests/bugfix-requests/<slug>/` and write **only** `BUGFIX_REQUEST.md` (the `reviews/` dir + later
artifacts belong downstream) using the template below. **Carry the load-bearing sections:** **Symptom**,
**Reproduction attempt**, **Expected vs Actual**, **Severity**, **Triage**, **Affected Area & Pointers**.

**Then decide the Stage plan — written last, never optional.** Per
[ADR 0008](../../../docs/decisions/0008-panels-by-default.md) the full pipeline is the **default** and a
skip is argued for. On this track the Stage plan governs **stage 3** (the plan panel): stage 2 has its
own obviousness funnel, and stage 4 always runs. The three hard triggers in
[`requests/README.md`](../../../requests/README.md) map to a defect like this — any one fires and the
plan panel runs, no argument available:

1. **Open Questions for Diagnosis came out non-empty.**
2. **The reproduction isn't reliable.** A fix you can't trigger on demand has unknown edges — this is
   the bugfix analogue of an unfillable *Explicitly out*, and it also means the red-to-green evidence
   the track's definition of done requires can't be produced.
3. **It touches something expensive to reverse** — a settled ADR, a pillar, the event schema, a dataset
   contract, a warehouse grain, or anything another request pins. **A defect in the parser's field map always
   fires this one**: the ledger has no upstream, so a wrong fix is unrecoverable rather than merely
   costly (see the track README's note on ledger bugs).

Clear all three and you may *propose* skipping stage 3, saying which triggers cleared and why the fix
is bounded. The user disposes it at the Step 5 handoff.

> **Note the incentive, and don't take it.** Triggers 1 and 2 are sections *you* just wrote. Write the
> Open Questions and the Reproduction attempt as if the Stage plan didn't exist — then read them.

```markdown
> **Status:** intake · created <YYYY-MM-DD> · open · next: root-cause

# Bug Report — <Title>

## Symptom
<What's observably wrong — the incorrect behavior/output, concretely. What you saw, where. A pasted
wrong value / traceback beats a paraphrase.>

## Reproduction attempt
<The exact steps / inputs / command or skill invocation that triggers it. If it won't reproduce
reliably, say so + the conditions where it appeared. This is the through-line — diagnosis confirms it
RED, the fix proves it GREEN.>

## Expected vs Actual
- **Expected:** <what should happen, and why you expect it — a mechanic, a hand-calc, a prior run>
- **Actual:** <what happens instead>

## Severity
<How much it hurts + urgency: data-corruption / wrong-output-that-misleads-a-decision / cosmetic. Note
if it corrupts landed data, spends cloud money, or produces a number someone might act on.>

## Triage
- **Verdict:** <obvious-hotfix | needs-full-track | actually-a-feature>
- **Obviousness hint (optional, non-binding):** <if you can already see the cause or it's a one-liner,
  say so — diagnose-bug's funnel uses this as a starting read, not a binding call.>

## Affected Area & Pointers
<Which part of the repo the symptom points at, and the concrete file(s) a cold diagnosis agent opens
first. A best guess is fine — RCA confirms it.>

## Reporter's cause-hunch (non-binding)
<Any guess at the cause. Explicitly non-binding: diagnosis is free to find something else. Omit if none.>

## Open Questions for Diagnosis
<What's unsure — is it a regression (what changed?), input-dependent, intermittent? Naming the unknown
beats a false certainty.>

## Stage plan
<REQUIRED, and written last. Which stages run. Default is all of them; this section governs stage 3.

If the plan panel runs, one line naming the trigger is enough:
  "Full pipeline. Trigger 3: the defect is in the parser's field map — every landed snapshot inherits it."

If proposing to skip stage 3, argue it: all three triggers, how each cleared, and what bounds the
fix. Stage 4 still runs in direct-build mode, with the ROOT_CAUSE_ANALYSIS standing in for the plan.>
```

## Step 5 — Confirm, record, hand off

1. Show the draft (or a tight summary) and let the reporter correct it — they saw the symptom, you
   didn't. Iterate until the **Reproduction attempt** reads true (it's what diagnosis will run).
2. Write the file, then register it: add a row to the **Index** table in
   [`requests/bugfix-requests/README.md`](../../../requests/bugfix-requests/README.md). Match the table by its
   `| Bug | Stage | Notes |` header (reference it by the header text, not a line number):
   `| [<slug>](<slug>/) | intake | <one-line note> |`. The status blockquote in the report is the source
   of truth for stage; the Index cell mirrors it.
3. Point at the next step: *"Run `/diagnose-bug` when you're ready to find the root cause."* Don't start
   diagnosing yourself — that's a separate, human-gated stage. **If your Stage plan proposed skipping
   stage 3, say so explicitly and show the argument** — an exception the user has to infer from a
   missing artifact isn't surfaced.

Per project convention, **agents commit only through `/commit`.** Suggest it when they want the report
landed.

---

## What good looks like

- **Every relative link and bare `requests/...` token you write must resolve on disk.** A live
  (non-`_done/`) artifact body is scanned by `tests/test_request_links.py`, a blocking CI
  check, so a dead pointer here fails the build rather than quietly misleading the next stage. Two
  shapes to watch: a **forward reference** to a file a later stage creates, and a deliberately
  **broken example path**. Put either inside a fenced code block (``` or ~~~, blockquoted is fine) —
  fenced content is exempt, precisely so a report can quote a dead target. Citations may carry a
  `file.py:123` suffix; `var/` targets and link titles are exempt too.

- **Symptom stated independently of the cause.** If the Symptom only makes sense once you've read the
  cause-hunch, it's a diagnosis in disguise — rewrite it around what was *observed*.
- **A real reproduction.** The single highest-value field. "It's wrong sometimes" is not a repro; "run
  `X` with input `Y`, get `Z`, expected `W`" is.
- **Honest severity.** A defect that corrupts a parsed field outranks a cosmetic typo — say
  which, so diagnosis and the funnel can pace themselves.
- **Grounded.** Real file/command names, not "the relevant code."
- **Right altitude.** It says *what's broken* and *how to trigger it*, gestures at *where*, and stops.
  The *why* is diagnosis's job.
