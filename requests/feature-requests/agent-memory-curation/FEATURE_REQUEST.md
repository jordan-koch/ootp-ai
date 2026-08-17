> **Status:** intake · created 2026-08-16 · decided · next: implement

# Feature Request — Move agent-memory curation from CI to the doc gate

## Problem / Motivation

The `data-engineer` subagent hit a state with no legal move.

`.claude/agents/data-engineer-memory.md` tells it, in bold: **"Append freely while you
work. Never prune."** Pruning is explicitly reserved for the human at the `/update-docs`
sweep, on the stated grounds that pruning mid-build means predicting which entries later
phases will need. Meanwhile `tests/test_agent_contract.py::test_memory_file_under_runaway_ceiling`
asserts the file is `<= 250` lines.

On 2026-08-16 the file reached exactly 250. The Phase 5b builder had six new entries to
record, could not append without turning a CI guard red, and was forbidden to prune. It
spent time counting lines, then routed the entries into its handoff instead — a sensible
recovery, but an improvised one: **no rule describes what to do at the ceiling.** The same
thing was observed at least once earlier in the day, before the boundary was reached, in
the milder form of an agent spending build time measuring a file it should never have been
thinking about.

The deeper defect is not the number. **The cap is enforced against the wrong actor.** The
agent is the one party that cannot see whether an entry is redundant — it cannot see future
phases — and is the one party forbidden to act on the answer. Both the judgment and the
authority live with the curator at the doc gate. A hard gate on the writer can therefore
only ever produce a deadlock; it cannot produce curation.

The failure modes are also asymmetric, and the guard is on the wrong side of that
asymmetry. Without it, the file grows between sweeps and someone reads more markdown —
a graceful, visible cost, and one `/commit`'s staged-diff read already surfaces. With it,
an agent stops recording findings in the middle of the heaviest implementation work this
repo will do. Phases 6 through 13 of `first-sight` are still ahead, including
`players.dat`, `names.dat` and the names join — the three places most likely to generate
exactly the kind of hard-won ergonomics this file exists to carry.

Left alone, this bites on every remaining phase.

## Desired Outcome

**The `data-engineer` never thinks about the size of its memory file again.** It appends
what it learned, and stops. No counting, no trimming, no branch to take at a boundary.

Curation moves to the place that already exists for it: `/update-docs`, which is the
judgment half of the commit gate and already owns exactly this kind of question — is this
prose still true, did this claim get refuted, does this label still hold. It gains a
section for the memory file.

The observable signals that it worked:

- An agent can append to the memory file at any length without any test going red.
- A sweep that runs over a diff touching the memory file reports what it audited — stale
  pointers, entries that became false, entries that should have routed to
  `docs/data-access.md` — in the same `UPDATED / FLAGGED / CLEAN` shape as its other checks.
- The trigger is deterministic: no one has to *remember* to audit it.

## Rough Ideas (non-binding)

- Delete `MEMORY_CEILING` and `test_memory_file_under_runaway_ceiling` from
  `tests/test_agent_contract.py`. **Keep `test_memory_entries_carry_an_epistemic_label`** —
  that guard is about the correctness of an entry's content, not its budget, and it is
  exactly what CI should hold.
- Rewrite the memory file's `## The budget — two numbers, two jobs` section. It currently
  informs the agent of two numbers it should not be thinking about.
- Fix the consequential passage in `.claude/agents/data-engineer.md`. It justifies the
  (correct) absence of a handoff cap *by contrast with* the memory cap — "the reason the
  memory file and `CLAUDE.md` do carry caps is that they are loaded into someone's context
  on every invocation." The reasoning survives; `CLAUDE.md` remains its only live example.
- Add a `/update-docs` section. Questions a machine cannot answer, in the style of the
  rest of that skill: did an entry become **false** (toolchain moved, cited artifact
  renamed)? Is an entry actually a **data fact** that should have routed to
  `docs/data-access.md`? Are two entries the same finding?

  **That first question is not hypothetical — two entries currently fail it.** One entry
  exists *solely* to repair another's stale pointer, after a `saved_games.py` docstring
  section was renamed: the finding is fine, but the file now spends four lines telling the
  reader that four earlier lines point at the wrong heading. And the 2026-08-16 entry
  claiming *"`tests/test_no_leaks.py` and `tests/test_doc_links.py` iterate `git ls-files`,
  so a file you just created is invisible to both guards"* is **half wrong**: `test_no_leaks.py`
  does iterate `git ls-files`, but `test_doc_links.py` uses `Path.rglob("*.md")` and sees
  untracked files perfectly well. The wrong half costs an agent time rather than producing
  a bug — it teaches distrust of a guard that works — which is precisely the kind of decay
  no CI check will ever catch and a reader with the diff in front of them catches in
  seconds. Found while writing this request, by re-reading the guard the entry names.
- **A curation rule worth stating explicitly: prefer deleting falsified entries over
  merging live ones.** Each entry carries a date and an evidence pointer; deleting a dead
  entry costs nothing, while merging two live ones costs provenance that cannot be
  reconstructed. Length is never by itself a reason to merge. Where a merge is genuinely
  right, keep both dates and both pointers as sub-bullets.
- Add the trigger to `/commit` Step 3's full-sweep table: **the memory file appearing in
  the staged diff.** Not "a handoff landed" — the file itself, which needs no inference.

## Scope Signals

- **In:** removing the CI ceiling; relocating curation to `/update-docs` with a real
  section and a deterministic trigger; repairing the two documents whose prose depends on
  the cap existing.
- **Explicitly out:** **splitting the memory file by genus.** Roughly 16 of its 38 entries
  are transferable format-forensics *method* (`the +1 calibrated null`, `export column
  order is not disk order`, `a 100% model is not a unique model — enumerate the ties`)
  rather than implementation ergonomics, and they have the opposite growth curve: tooling
  scar tissue expires as the toolchain moves, method accumulates and gets more valuable
  with age. A separate home — `docs/format-forensics.md` — is plausibly right. It is out
  of scope here because it should be built on evidence rather than on one afternoon's
  reading: if the new sweep repeatedly reports that a bloc of entries is never false,
  never obsolete and never merges, *that* is the case for splitting. Also out: changing
  the entry format, changing what routes to `docs/data-access.md`, and any change to the
  `gm/` memory files, which are a different mechanism under ADR 0011.
- **Not now / later:** a first real curation pass over the 38 accumulated entries. The
  gate has not run since Phase 3 — nine phases of deferred curation landed on one file,
  which is why the ceiling was reached in two days. Curating is the *next* sweep's job,
  not this request's; this request builds the mechanism that makes the sweep able to do it.

## Affected Area & Pointers

Process and agent contract — no pipeline code, no parser, no warehouse.

- `tests/test_agent_contract.py` — `MEMORY_CEILING`, `test_memory_file_under_runaway_ceiling`,
  and the neighbouring `test_memory_entries_carry_an_epistemic_label` that must survive.
- `.claude/agents/data-engineer-memory.md` — the `## The budget — two numbers, two jobs`
  section, and the file whose 38 entries are the evidence for the whole request.
- `.claude/agents/data-engineer.md` — the handoff-length passage that reasons from the
  memory cap's existence.
- `.claude/skills/update-docs/SKILL.md` — Step 2 gains the section.
- `.claude/skills/commit/SKILL.md` — Step 3 gains the trigger.

## Constraints / Non-negotiables

- **The repo is public** (ADR 0006). The memory file is tracked, so its entries must keep
  citing repo artifacts rather than raw environment output. Nothing here relaxes that.
- **`tests/` is in the `data-engineer`'s deny set**, so this change is main-thread work by
  construction — the agent cannot remove its own guard, and that property must survive.
- **Epistemic labelling stays mechanically enforced.** Removing the budget guard must not
  remove the content guard beside it.
- **`/update-docs` does not run lint, types or tests.** Its own rules say the mechanical
  half belongs to CI. A curation section must therefore be judgment-shaped, not a line
  count relocated into prose.

## Open Questions for Scoping

None outstanding. The one question that existed — *if CI stops enforcing this and
`/update-docs` is discretionary, what makes the audit actually fire* — is answered above by
triggering on the memory file's presence in the staged diff, which is deterministic and
needs no inference.

Recorded rather than asked, because it is a judgment the implementation should make
visible rather than resolve silently: the curation section will have **no number in it at
all**. The `~120-line curation target` currently in the memory file could be retained as
non-binding guidance for the curator. The argument against is that a number is what turned
a judgment into an arithmetic exercise once already.

## Stage plan

**Direct build. Stages 2 and 3 skipped, argued below; stage 4 runs with this request
standing in for the plan.**

Against the three hard triggers in [`requests/README.md`](../../README.md):

1. **Open Questions came out non-empty?** No. The single open question — the forcing
   function once CI stops enforcing — was surfaced and answered before this was written,
   and the answer is in *Rough Ideas*. The one remaining item is flagged for visibility,
   not for resolution.
2. **Explicitly out couldn't be filled?** No. It is filled, and with the substantive item:
   the genus split is the obvious adjacent change and it is deliberately deferred, with
   the evidence standard that would justify it named.
3. **Touches something expensive to reverse?** No. It deletes one test and one constant and
   edits four prose passages. No ADR covers the memory ceiling; nothing pins it; no data
   is landed, no grain declared, no field map touched. Re-adding the guard is a one-line
   revert, and the file it guards is tracked, so nothing is lost even if the change proves
   wrong.

What bounds the work: five files, all process artifacts, all readable in one sitting; the
defect is fully diagnosed; the fix is subtraction plus prose. The main-thread constraint is
structural rather than procedural — `tests/` is the builder's deny set, so this cannot be
delegated regardless of which stages run.

**One fold-in, unrelated but discovered in the same files.** `/update-docs` Step 1 and
`/commit` Step 3 both instruct running `uv run pytest tests/test_request_links.py`. **That
file does not exist** — the guard is `tests/test_doc_links.py`. The dead command was hit
during the Phase 5b commit. Two one-word corrections in files this request already opens;
folding them in rather than opening a request to fix a filename.
