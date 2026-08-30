> **Status:** intake · created 2026-08-30 · open · next: scope

# Feature Request — The method the memory file is hiding

## Problem / Motivation

**The most transferable knowledge this project has produced is filed where nothing reads
it on purpose.**

[`.claude/agents/data-engineer-memory.md`](../../../.claude/agents/data-engineer-memory.md)
is an append-only scratchpad. Its own header says so — a build appends what cost it time
and gets back to work, and nothing prunes. That mechanism is correct and was deliberately
made so by [`agent-memory-curation`](../_done/agent-memory-curation/), which removed a CI
line ceiling because the file's rules said *append freely, never prune* and the ceiling made
that illegal at the boundary.

But the file now holds two genuinely different kinds of thing, and only one of them is a
scratchpad entry.

`measured` 2026-08-30, over all 63 entries: **42 carry `tag: harness`.** Reading them, that
tag spans two genera the tag itself does not distinguish (`inferred` — my classification,
not a mechanical one):

- **~27 are transferable format-forensics *method*** — how to crack an undocumented binary
  format at all. *The cheapest calibrated null is the same search with every value +1. A
  composite landmark segments a variable-length file in one pass where greedy chaining
  stalls. An oracle of sets cannot validate an assignment of occurrences. A state
  unpopulated in the oracle save makes a wrong rule score 100%. Group stride hits by
  `pos % N` before chaining.* None of this is about this repo. It would be true in any
  project reverse-engineering any binary format.
- **~15 are repo-coupled ergonomics** — mypy runs over `tests/` so widening a field can red
  a deny-set path; a missing module blocks pytest *collection*; a deny-set fix can be proved
  in a scratchpad copy. These are exactly what a scratchpad is for and should stay.

A **third** genus is emerging and was not predicted: four to six entries are *guard-design*
method rather than format method — *a guard that only asserts the tree is clean proves
nothing about whether it can fail; plant a probe in a tree the test owns, because a `finally`
is not the mechanism, ownership is; a guard that names a repo path only checks the paths
someone thought to scan.* Transferable, but a different subject with a different audience.

**Three costs, and the third is the one that matters.**

- **It is filed under "append freely, never prune", so it is read last.** An agent starting
  a format investigation does not open a colleague's scratchpad first. It opens `docs/`.
- **It only arrives after the mistake.** Every one of those entries exists because a build
  lost time. They are written to be read *before* the next build makes the same move, and
  the current filing guarantees the opposite order.
- **The two genera decay at opposite rates, so one file cannot be curated correctly.**
  Tooling scar tissue expires as the toolchain moves; method accumulates and gets more
  valuable with age. A curation policy tuned for one is wrong for the other, and
  [`/update-docs`](../../../.claude/skills/update-docs/SKILL.md) currently applies one policy
  to both.

**This was deferred deliberately, with a named evidence bar, which is why it is a request
and not a defect.** `agent-memory-curation` put the genus split under *Explicitly out* and
said what would justify it: *"if the new sweep repeatedly reports that a bloc of entries is
never false, never obsolete and never merges, that is the case for splitting."*

## Desired Outcome

**An agent about to reverse-engineer a `.dat` file can read the method before it starts,
from a document that is meant to be read.**

"Done" looks like:

- The transferable method has a home under `docs/`, written to be read start-to-finish
  rather than scanned as a log, and `CLAUDE.md`'s map names it.
- The memory file keeps what a scratchpad is for — repo and toolchain ergonomics — and gets
  measurably smaller without anything being lost.
- The **routing rule is updated at the point of writing**, so the next entry of this kind
  lands in the right place instead of being relocated later by a sweep. The file's header
  already routes data facts to `docs/data-access.md` and repo-wide traps to `CLAUDE.md`; a
  third destination is a change to that rule, not just a move.
- Provenance survives. Every entry carries a date and an evidence pointer, and the move must
  not cost either.

Observable signal: a cold agent handed a new binary file to crack finds the method by
reading `CLAUDE.md`'s map, without being told the memory file exists.

## Rough Ideas (non-binding)

- **`docs/format-forensics.md` is the filename the prior request already proposed.** Worth
  keeping unless scoping finds better.
- **The guard-design bloc may want a different home** — possibly beside
  [`.claude/agents/data-engineer.md`](../../../.claude/agents/data-engineer.md), which owns
  the build rules, rather than in `docs/`. Left open on purpose.
- **A moved entry might leave a one-line pointer behind, or move clean.** Pointers keep the
  scratchpad's chronology honest; a clean move keeps it short. Undecided.
- **The three docs that carry rules already have a stated shape**
  ([`CLAUDE.md`](../../../CLAUDE.md): *"Three of those docs carry rules, not just
  information"*). A fourth would join that set, or deliberately not.

All non-binding.

## Scope Signals

- **In:** relocating the transferable-method bloc out of the memory file into a tracked
  `docs/` home; updating the routing rule in the memory file's header so the next such entry
  is written in the right place; the `CLAUDE.md` map entry; whatever
  [`/update-docs`](../../../.claude/skills/update-docs/SKILL.md) must say to curate two files
  with different decay rates instead of one with one policy.
- **Explicitly out:**
  - **A curation pass over the entries that stay behind.** Operator's disposition at intake:
    *relocation only*. A move is mechanical; a judgment call over 63 entries is a different
    job with a different risk profile, and merging them makes the diff unreviewable.
  - **Changing the entry format.** The `date · label · claim · evidence · tag` shape is not
    this request's to renegotiate.
  - **Changing what routes to [`docs/data-access.md`](../../../docs/data-access.md).** That
    boundary is settled and was already out of scope for the prior request.
  - **Any change to `gm/` memory.** A different mechanism under ADR 0011, and not this.
  - **Re-adding a size ceiling of any kind**, to either file. `agent-memory-curation`
    removed it for a reason that still holds.
- **Not now / later:** back-filling method entries from the `first-sight` phase handoffs,
  which almost certainly contain method that never reached the memory file at all; and any
  attempt to generalise the document for a *different* repo.

## Affected Area & Pointers

**Subsystem:** `docs/` and `.claude/` — prose and routing rules. **No pipeline code, no
dataset, no parser change, no landed data.** The one mechanical risk is the doc-link and
skill-reference guards, which read both directories.

A cold scoping agent should open, in this order:

| # | File | Why |
|---|---|---|
| 1 | [`.claude/agents/data-engineer-memory.md`](../../../.claude/agents/data-engineer-memory.md) | The subject. `:1-55` is the header — the append-freely rule at `:39-53` and, critically, the **routing rule at `:14-27`** that this request changes. `## Entries` is the 63-entry bloc to classify |
| 2 | [`agent-memory-curation`](../_done/agent-memory-curation/FEATURE_REQUEST.md) | The prior request that deferred exactly this, named `docs/format-forensics.md` as the plausible home, and set the evidence bar this request has to be measured against |
| 3 | [`.claude/skills/update-docs/SKILL.md`](../../../.claude/skills/update-docs/SKILL.md) | Owns the curation policy — the memory-file section, the merge rule, and the "length is never by itself a reason" clause. A second file needs a second policy or an argued shared one |
| 4 | [`CLAUDE.md`](../../../CLAUDE.md) | The project map, and the *"Three of those docs carry rules"* paragraph a fourth document would join. **Also: the file is at 199 of a 200-line budget, so a map entry must be paid for by a cut** |
| 5 | [`.claude/agents/data-engineer.md`](../../../.claude/agents/data-engineer.md) | Single owner of the build rules, and the candidate home for the guard-design bloc. Its contract is asserted by [`tests/test_agent_contract.py`](../../../tests/test_agent_contract.py) |
| 6 | [`docs/data-access.md`](../../../docs/data-access.md) | The routing destination that already exists, and the model for what a rules-carrying `docs/` file looks like — including its epistemic-label discipline |

## Constraints / Non-negotiables

- **Provenance is the thing being moved, not just the text.** Every entry carries a date and
  an evidence pointer. `/update-docs` states the rule in terms: *"Deleting a falsified entry
  costs nothing. Merging two live ones costs provenance."* A relocation that flattens 27
  dated observations into undated prose destroys exactly what makes them trustworthy.
- **Epistemic labels are load-bearing** and every entry carries one. If the new document
  adopts `docs/`'s conventions, the labels must survive the move intact, not be re-derived.
- **The repo is public** ([ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md)).
  The method is *ours* — derived observation, explicitly trackable — but several entries cite
  gitignored `var/spike*/` scripts as evidence. Those pointers are already dead to a reader
  and a `docs/` file makes that more visible, not less.
- **`CLAUDE.md` is at 199 lines against a 200-line budget.** Adding a map entry means cutting
  something, and the budget is enforced by reading, not by CI.
- **`tests/test_doc_links.py` and `tests/test_skill_references.py` are blocking**, and both
  scan the directories this touches.
- **Agents commit only through `/commit`.**

## Open Questions for Scoping

1. **One home or two?** Format forensics and guard design are both transferable method but
   different subjects. Operator's disposition at intake: **let scoping decide**, with the
   evidence recorded rather than the boundary pre-drawn.
2. **Is the evidence bar actually met?** The prior request said *"if the new sweep
   **repeatedly** reports…"*. There has been **one** sweep (2026-08-30), which found 51/51
   citations resolving, zero merges proposed, and exactly one entry falsified — and that one
   is instructive rather than damaging: the entry's *method claim survived* while its
   repo-specific binding rotted, which is the split thesis in miniature. The bloc also grew
   from "roughly 16 of 38" to ~27 of 42 with no decay. **Two observations, not "repeatedly".**
   Scoping should decide whether that clears the bar its predecessor set, or whether this
   waits for another sweep. Recording the shortfall rather than papering over it.
3. **Does a moved entry leave a pointer behind?** Chronology versus brevity; affects whether
   the memory file actually gets smaller.
4. **Does the new document keep the log format, or become prose?** A log preserves dates and
   pointers cheaply; prose is what "written to be read start-to-finish" implies. They may not
   be compatible, and Desired Outcome asks for both.
5. **Who curates the new file, and against what policy?** `/update-docs` audits the memory
   file because nothing else does. If method never expires, its curation question is not
   "is this still true" but "is this still findable", which is a different sweep.
6. **Should the entries whose evidence is a gitignored `var/spike*/` script be re-pointed
   before the move?** Roughly six cite scripts no reader can open.

## Stage plan

**Full pipeline.** Trigger 1 fires: **Open Questions came out non-empty** — six, and
question 2 is load-bearing, because it asks whether this request should exist *yet* against
a bar its predecessor set deliberately. That is exactly the call a scope panel's fit verdict
is for, and it is not one intake should make for itself.

Trigger 3 fires as well. The request **changes a routing rule that two other documents
bind** — the memory file's own header and `/update-docs`'s curation section — and creates a
tracked document that becomes authoritative for agents. Getting the boundary wrong is not
expensive to *undo*, but it is expensive to *notice*: a method file nobody routes to decays
into a second scratchpad, which is the failure this request exists to fix.

Trigger 2 is cleared — *Explicitly out* is filled, and with the substantive item (the
curation pass, disposed by the operator at intake).

No skip is available and none is proposed.
