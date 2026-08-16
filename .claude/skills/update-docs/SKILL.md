---
name: update-docs
description: >-
  Bring the project's documentation back into agreement with the repo that now exists — the
  judgment half of the commit gate, called by /commit or run on its own. Checks that CLAUDE.md's map and
  rules still describe reality, that README.md's status/next-steps/setup are still true, that no
  accepted ADR was silently invalidated, that docs/data-access.md's epistemic labels reflect what
  has actually been verified, that every dataset's documented grain matches a test that proves
  it, and that the requests/ Index rows match their artifacts' status headers. Use it whenever a
  unit of work is finished and about to be committed, or on request: "update the docs", "check for
  doc drift", "are the docs still accurate", "run the doc gate", "did this invalidate an ADR". Do
  NOT use it to run lint, types, tests, or secret scanning — those are
  mechanical and belong to CI, which runs them on every PR. Do NOT use it to commit — that is
  /commit's job, and this skill is one of its steps.
---

# Update Docs

## What this produces and why

An updated set of project docs that describe the repo **as it now is**, plus a short report of what
changed and what needs the user's judgment.

This is the surviving half of a conventional pre-commit gate. Everything mechanical — `ruff`,
`mypy`, `pytest`, `gitleaks` — moved to CI, where it runs on every PR and
cannot be skipped. What CI *can't* check is whether the prose still tells the truth.

That matters more here than in most repos. **Most of this codebase is written by agents reading
these docs as authoritative.** A `CLAUDE.md` that describes a directory layout the repo no longer
has doesn't produce an error; it produces an agent confidently building in the wrong place. Doc
drift here is a correctness problem, not a tidiness problem.

> **Naming note.** This skill is deliberately *not* called `pre-commit` — that name belongs to the
> Python git-hook framework, and two things by that name in the repo whose premise is unambiguous
> docs would be its own small joke. See [`CLAUDE.md`](../../../CLAUDE.md).

---

## Step 1 — See what actually changed

```
git status --porcelain
git diff HEAD --stat
git diff HEAD
```

Read the real diff, not the commit message's summary of it. Bucket it: `transform` · `src` ·
`tests` · `skills` · `ci` · `config` · `docs` · `requests`.

The bucket list drives which checks below are load-bearing. A docs-only change doesn't need the
grain audit; a new dataset needs it most.

**Then run the one mechanical check this skill owns**, because it is about docs rather than code:

```
uv run pytest tests/test_request_links.py -q
```

Dead relative links in process artifacts are a doc-drift failure that happens to be mechanizable.
Everything else mechanical belongs to CI — do not re-run it here.

## Step 2 — The checks

Work through these against the diff. Each is a question a machine can't answer.

### CLAUDE.md — does it describe this repo?

- **The project map.** Does every directory in the tree block exist? Does every directory that now
  exists appear? The repo grows by phase, and the map is supposed to show *what is*, with
  README's "Status and what's next" carrying *what will be*.
- **The rules.** Did this change establish, alter, or break a convention the rules section states?
  A new convention that lives only in a PR description is a convention that will be violated next
  week.
- **Constraints & Gotchas.** Did this change discover a new trap, or retire an existing one? This
  section is the repo's scar tissue — it should grow when something bites.
- **The line budget.** `CLAUDE.md` stays **under 200 lines**. Check it:
  `(Get-Content CLAUDE.md | Measure-Object -Line).Lines`. Over budget means cutting, not
  reformatting — the file is a map, and a map that takes an hour to read is not a map.

### README.md — is it still true?

- The **status blockquote** and **"Status and what's next"** — did this change complete a phase, or
  start one? These are the first things a visitor reads and the first things to go stale.
- The **setup steps** — would a fresh clone still work by following them exactly? A new dependency,
  a new required env var, or a changed command invalidates them.
- The **architecture table** — does it still describe what the code does?

### ADRs — did this invalidate one?

Read [`docs/decisions/`](../../../docs/decisions/) against the change. If the work contradicts an
accepted ADR:

- **Do not edit the accepted ADR.** Write a new one that supersedes it and set the old one's status
  to `superseded by NNNN`. The record of what was believed at the time is the entire value; editing
  it destroys that.
- Add the new ADR to the Index table in [`docs/decisions/README.md`](../../../docs/decisions/README.md).
- **Flag this to the user rather than doing it silently.** Superseding an ADR is a real
  architectural decision, not a documentation chore.

If the change makes a *new* decision that isn't recorded anywhere — a choice someone would
reasonably ask "why did you do it that way" about — that's a missing ADR. Propose it.

### docs/data-access.md — are the epistemics honest?

Every claim in that file carries a label: `measured`, `verified`, `documented`, or `unconfirmed`.

- Did this change **verify** something previously unconfirmed? Promote the label and say how it was
  checked. This is the most commonly missed update in the repo, and the most valuable — the file
  starts out entirely `unconfirmed`, and it only becomes trustworthy by being promoted deliberately.
- Did it **refute** something? Say so plainly. A claim that turned out false is more useful
  recorded than deleted.
- Did it discover a new gotcha — an unverified field mapping, a variable-length-record trap, a
  true-vs-scouted ratings hazard, a population that structurally lacks a field?

### Model documentation — does the declared grain match a test that proves it?

For every dataset the diff touched:

1. Read its `schema.yml` description. What grain does it *claim*?
2. Read its tests. Is there a uniqueness assertion that *proves*
   that exact grain?
3. Do they agree?

A model claiming "one row per player per game" while its uniqueness test covers only `game_id` is
documented wrongly, tested wrongly, or both — and it will fan out a join eventually. **This is a
blocker, not a note.** Report it and stop; don't paper over it by editing the prose to match a
weaker test.

Also check: does every new model and column carry a description at all? An undocumented column in
a repo built on documentation is a gap.

### requests/ — do the Index rows match the artifacts?

For any request the change touched: the artifact's **Status blockquote** is the source of truth;
the track README's Index `Stage` cell mirrors it. Reconcile them. Confirm a terminal-stage item
moved into `_done/` and that its Index link points there.

### The editor's pen

Finally, read `CLAUDE.md` and `README.md` as prose. Tighten what's flabby, cut what's redundant,
fix what's stale. These two files are read more than any others in the repo — by agents on every
task, and by anyone evaluating the project. They deserve to be well written.

## Step 3 — Report, then hand back

Make the edits you're confident in. For anything requiring judgment — a superseded ADR, a
grain/test mismatch, a convention that should change — **propose, don't decide.**

Report in three buckets:

```
UPDATED   — what you changed, and why
FLAGGED   — what needs the user's call, with your recommendation
CLEAN     — what you checked and found accurate (so the user knows the sweep ran)
```

The `CLEAN` bucket matters: a report listing only problems is indistinguishable from a sweep that
didn't run.

Then **stop.** This skill does not commit. If it was called by [`/commit`](../commit/SKILL.md),
return control there. If it was run on its own, end the turn by telling the user the docs are current
and suggesting `/commit` to land the change.

---

## What good looks like

- **It caught something.** A sweep over a real change that reports zero drift is possible but
  uncommon. If everything is clean, say which files you actually opened — an unfalsifiable "all
  good" is worthless.
- **ADRs were superseded, never rewritten.** The one irreversible mistake available here.
- **A grain/test mismatch was reported, not reconciled.** Editing the prose to match a weak test
  hides the bug instead of fixing it.
- **Epistemic labels moved in the right direction.** `unconfirmed` → `verified` when something was
  actually checked; never the reverse by omission.
- **It didn't duplicate CI.** No lint, no type check, no test run beyond the link guard, no
  build. Those are already gated where they can't be skipped.
- **It handed off, it didn't commit.**
