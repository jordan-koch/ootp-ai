---
name: diagnose-bug
description: >-
  Find the ROOT CAUSE of a captured bug and turn it into a ROOT_CAUSE_ANALYSIS — a confirmed cause with
  file:line evidence, a committed failing (red) reproduction, a verdict, and a tiered fix posture — that
  the reused plan/implement stages can execute. This is stage 2 of the BUGFIX pipeline (intake ->
  root-cause -> reuse plan/implement), the defect-track parallel of scope-feature. It opens with an
  OBVIOUSNESS FUNNEL: an obvious one-liner cause gets a terse inline RCA (and a true one-liner may go
  straight to fix+test); a murky cause escalates with a measurable Escalation hand-off. Use it when a
  BUGFIX_REQUEST exists and you want to know WHY it's broken: "find the root cause", "diagnose the <slug>
  bug", "why is X producing the wrong output", "run diagnosis", "what's actually causing this", or as the
  natural follow-up to /make-bugfix-request. Do NOT use it to scope or plan a FEATURE (that's
  scope-feature / create-implementation-plan), to write the fix's code for a non-trivial bug (that's
  implement-plan, after a plan), or for in-game/gameplay questions. If no BUGFIX_REQUEST.md exists yet,
  send the user to /make-bugfix-request first.
---

# Diagnose Bug

## What this produces and why

A `ROOT_CAUSE_ANALYSIS.md` in `requests/bugfix-requests/<slug>/` — a **verdict**, the **confirmed cause** with
real `file:line` evidence, a pointer to a **committed failing (red) reproduction**, and a **tiered fix
posture** — that the reused `/create-implementation-plan` + `/implement-plan` stages can consume, or that
a true one-liner can be fixed against directly.

The failure this stage exists to prevent is **fixing the symptom, not the cause** — or "fixing" code that
was never wrong. The guard is the **red reproduction**: a concrete, committed thing that fails *because of
this bug* and will pass *only when the cause is actually fixed*. The RCA is only as trustworthy as that
repro plus the evidence trail from the red symptom to the offending logic.

Read [`requests/bugfix-requests/README.md`](../../../requests/bugfix-requests/README.md) once for the track's conventions
(status grammar incl. the terminal verdicts, the defect acceptance contract, the per-substrate repro
homes, the committed-red-repro ordering).

> **v1 note:** the heavyweight **RCA adversarial panel** (a refute-the-diagnosis panel) is **deferred**.
> This skill ships the **inline-RCA path**; a genuinely murky cause is handed off via a measurable
> **Escalation** section, not a panel. Don't build or launch a panel here.

---

## Step 1 — Locate the request (and check it's ready to diagnose)

- If the user named a slug/path, use `requests/bugfix-requests/<slug>/BUGFIX_REQUEST.md`.
- Otherwise check the **Index** in [`requests/bugfix-requests/README.md`](../../../requests/bugfix-requests/README.md) for a
  bug at the `intake` stage, or infer from the conversation. **If you inferred the slug, echo back the
  exact path + title and get a yes** before diagnosing.
- **If no `BUGFIX_REQUEST.md` exists, stop** and send the user to `/make-bugfix-request`.

**Substance gate.** Open the report and confirm it carries a **Symptom** and a **Reproduction attempt** —
without something to make RED, there's nothing to diagnose. If the repro is missing or hopelessly vague,
bounce it back to `/make-bugfix-request` to firm up rather than guessing.

## Step 2 — The obviousness funnel (the gate)

Assess **obvious vs murky** — this decides how heavy the diagnosis is. The funnel is a judgment call, so
**always leave a `ROOT_CAUSE_ANALYSIS.md`** either way (even the skip path keeps a trail + a verdict).

- **Obvious** — you can point at the offending `file:line` and explain *why* it's wrong with high
  confidence, and the repro lands straight on it. Signals: a single wrong constant/comparison/branch; the
  reporter's cause-hunch checks out on a read; one suspect file. → **inline RCA**, no escalation.
  - If it's also a **true one-liner** (the fix is a line or two with no design choice), you may go
    straight to fix+test (Step 5, skip-to-fix path) — still write the (terse) RCA first.
- **Murky** — multiple plausible causes, an intermittent/heisenbug, a cause that spans several modules,
  or you've already guessed wrong once. → **inline RCA with a required Escalation section** (Step 4). Do
  not sink unbounded time into a murky cause here; record the candidates and escalate.

Don't burn effort proving obviousness; bias toward writing the artifact and moving.

## Step 3 — Reproduce RED, then get it landed (the ordering matters)

The repro is the through-line. Write it before the RCA that references it, so the pointer is stable:

1. **Pick the substrate's repro home** (per `requests/bugfix-requests/README.md`): Python code → a
   pytest case in `tests/` asserting the *deterministic* wrong value (not a sampled or stochastic
   one); a dataset builder → a test against a cached fixture, never a live pull; a
   source-contract assumption → a schema test on the source, so the next upstream change fails
   loudly; CI or workflow config → an assertion or fixture that would have caught it.
2. **Write it + run it + confirm it's RED** against the current (buggy) code — `uv run pytest` fails,
   goes red on the new test. **A repro that's green today proves nothing**, and it
   usually means the diagnosis is wrong rather than the bug being absent.
3. **Use committed fixtures only** — never a live API call (CI excludes them, and an external source
   blocks impolite clients) and never anything from `var/`, which is gitignored and machine-local.
   See [`tests/fixtures/README.md`](../../../tests/fixtures/README.md).
4. **Agents do not commit.** Tell the user the repro is red and ask them to commit it before you
   write the RCA that points at it. If they'd rather land it all at once, that's fine — say so in
   the RCA's Reproduction section instead of citing a hash.

If you genuinely **cannot** make it reproduce, that's the `cannot-reproduce` verdict (Step 4) — record
what you tried and close it; don't fabricate a red repro.

## Step 4 — Write the ROOT_CAUSE_ANALYSIS.md

Render the **verdict**, then write `requests/bugfix-requests/<slug>/ROOT_CAUSE_ANALYSIS.md` from the template.
The verdict drives the Status blockquote and what happens next:

- **`confirmed-bug`** → `diagnosed · … · decided · next: plan` (needs the full track) **or**
  `… · next: fix` (a true one-liner you'll fix in Step 5).
- **`works-as-intended`** → `closed-works-as-intended · … · next: none` (the code is right; record *why*
  the expectation was off).
- **`cannot-reproduce`** → `cannot-reproduce · … · next: none` (record what you tried).
- **`actually-a-feature`** → `redirected-to-feature · … · next: <feature-slug>` — **redirect ownership
  (D4):** intake did a cheap sniff; the RCA holds the **authoritative** verdict. Emit a pointer to
  `/make-feature-request` (this is a capability gap, not a defect).

```markdown
> **Status:** diagnosed · created <YYYY-MM-DD> · decided · next: <plan | fix | none | <feature-slug>>

# Root Cause Analysis — <Title>

## Verdict
<confirmed-bug | works-as-intended | cannot-reproduce | actually-a-feature> — <one line on what it means
for this bug + which downstream path it takes.>

## Reproduction (red)
<pointer to the failing reproduction: the exact test/fixture + how to run it + the RED output it
currently produces. e.g.
`tests/test_parse_world.py::test_a_count_prefixed_calendar_decodes_and_consumes_its_region_exactly`
via `uv run pytest` (fails: expected 3058 calendar entries, got 2600). Note whether it is
already committed.
(Omit only for cannot-reproduce / works-as-intended, with a note why.)>

## Evidence (the cause)
<the actual root cause, citing real file:line. Trace from the red symptom to the offending logic and show
WHY it produces the wrong result — not just where. Distinguish the cause from the symptom.>

## Fix posture (tiered)
- **Minimal:** <the smallest change that makes the repro green without regressing the existing baseline.>
- **Root:** <the fuller fix if the minimal one only treats a facet — note other sites the same wrong rule
  lives in, so the report can say what stays open.>
- **Hardening:** <adjacent guards worth considering — gated, not assumed.>
```

**If the cause is MURKY**, append the required Escalation section (the panel is deferred, so this is the
hand-off — AC4 (a)/(b)/(c)):

```markdown
## Escalation (murky cause — RCA panel deferred)
- **(a) Why murky:** <why the cause isn't obvious, with file:line evidence of the candidate causes weighed.>
- **(b) Verdict:** needs-deeper-diagnosis
- **(c) Follow-up:** the refute-the-diagnosis RCA panel is NOT built in v1 (see
  requests/feature-requests/_done/bugfix-pipeline/). Escalate by hand-investigating the candidates above, or by standing
  up that deferred panel. Until then this bug is NOT ready to plan.
```

## Step 5 — Record, then take the right exit

Register the bug and advance status (in-place edits; **don't run git** — `/commit` handles that):

- Update the `BUGFIX_REQUEST.md` Status blockquote and the **Index** row in
  [`requests/bugfix-requests/README.md`](../../../requests/bugfix-requests/README.md) (match by the `| Bug | Stage | Notes |`
  header) to `diagnosed` (or the terminal stage word) — the track README's grammar at
  `requests/bugfix-requests/README.md` is the contract, per `requests/README.md`.

Then exit by verdict:

- **Confirmed-bug, needs the full track** → hand off: *"Run `/create-implementation-plan` to plan the
  fix."* The reused planning stage auto-detects the bugfix track from the path and grounds against this
  RCA.
- **Confirmed-bug, true one-liner (`next: fix`)** → fix it now: make the minimal change, confirm the red
  repro goes **GREEN** and **nothing else regresses** (`uv run pytest` and, if models changed,
  `uv run pytest` clean), then suggest `/commit`. The regression test
  is already left behind (it's the repro). Record the fix in the RCA's Fix-posture (Minimal, applied).
- **Murky** → the Escalation section is the deliverable; the bug waits for the follow-up. Hand the RCA
  and red repro to the user to land.
- **Terminal (works-as-intended / cannot-reproduce / actually-a-feature)** → the RCA *is* the close;
  for `actually-a-feature`, point at `/make-feature-request`.

Per project convention, **agents commit only through `/commit`** — never `git commit` ad hoc, and never
merge. `/commit` pushes the branch itself; opening the PR stays the user's. End the turn by suggesting
`/commit`. Any subagent you spawn gets **read-only git**
(never checkout/reset/restore/clean/stash/commit).

---

## What good looks like

- **Every relative link and bare `requests/...` token you write must resolve on disk.** A live
  (non-`_done/`) artifact body is scanned by `tests/test_doc_links.py`, a blocking CI
  check, so a dead pointer here fails the build rather than quietly misleading the next stage. Two
  shapes to watch: a **forward reference** to a file a later stage creates, and a deliberately
  **broken example path**. Put either inside a fenced code block (``` or ~~~, blockquoted is fine) —
  fenced content is exempt, precisely so a report can quote a dead target. Citations may carry a
  `file.py:123` suffix; `var/` targets and link titles are exempt too.

- **A committed red repro the fix must flip.** The diagnosis's teeth. Asserted deterministically (not a
  sampled value), committed before the RCA cites it, RED on today's code.
- **Cause distinguished from symptom.** The Evidence traces *why*, with real `file:line` — so the fix
  targets the cause, not the surface.
- **An honest verdict.** "Not a bug" / "can't reproduce" closed *with the trail* is a real outcome, not a
  failure — it stops the same false alarm being re-chased.
- **The funnel always leaves an artifact.** Even an obvious one-liner gets a terse RCA; even a murky cause
  gets a measurable Escalation, not a shrug.
- **The fix posture names what stays open.** If the same wrong rule lives in other files, say so — so the
  downstream report doesn't read "closed" when only one facet was fixed.
