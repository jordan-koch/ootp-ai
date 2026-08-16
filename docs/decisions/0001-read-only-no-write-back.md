# 0001 — The system never writes to the game

**Status:** Accepted
**Date:** 2026-08-15

## Context

The project's goal is an AI-run front office. The obvious architecture has the AI
both *deciding* and *executing*: read league state, choose a lineup, apply it.

OOTP exposes no API. Three write paths were considered:

1. **Edit the save binaries directly.** Technically reachable — the `.dat` files
   are unencrypted (see [data-access.md §4](../data-access.md)). But Challenge
   Mode saves carry a SHA-256 integrity hash in `challenge.dat` and a second hash
   inside `players.dat`; writing invalidates the save irreversibly.
2. **The roster text round-trip.** OOTP documents "Exports all rosters to a text
   file. You can edit this text file and re-import it to easily perform
   transactions." A supported channel that never touches the binaries.
3. **Nothing.** The AI advises; a human executes in-game.

## Decision

**The system is read-only with respect to the game.** It never writes a save
file, never writes a roster import file, and never automates the game's UI.

Its output is *recommendations*. The human GM executes them.

## Consequences

**Buys:**

- The single hardest engineering problem — reverse-engineering a *write* format
  well enough to produce files OOTP will accept without corrupting a league —
  disappears entirely.
- Challenge Mode stays viable ([ADR 0003](0003-challenge-mode-league.md)). No
  integrity hash is ever at risk.
- Every failure mode is recoverable. A wrong recommendation costs one bad
  decision, not a destroyed save.
- The project's interesting problems (ingestion, modeling, evaluation) get the
  effort instead.

**Costs:**

- **Every decision requires human execution.** The GM does the clicking. For a
  full season this is real, sustained effort, and it caps how many decisions the
  system can usefully emit per sim day. A recommendation nobody has time to
  execute is worth nothing.
- We cannot close the loop automatically, so we cannot A/B test strategies at
  machine speed. Evaluation is limited to what gets played.
- Reproducibility is weaker: the state the AI recommended against and the state
  actually reached can diverge through execution error, and we may not detect it.

**Forecloses:**

- Any autonomous-agent framing. This is a decision-support system, and the
  roadmap should not drift toward autonomy without superseding this ADR.
- Roster-file format reverse engineering. Do not start it.

## Notes

Path 2 remains *technically* available and was rejected on cost, not on
feasibility. If execution burden becomes the binding constraint on the project,
superseding this ADR for the narrow case of bulk roster moves is the argument to
make — and it needs its own ADR, because Challenge Mode's hashes make the blast
radius of a mistake unusually large.
