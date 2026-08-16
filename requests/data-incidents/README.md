# Data Incidents

**Everything ran green and the data is wrong.**

This track exists because of one property of this project: the parser reads a
**reverse-engineered binary format**. There is no schema to violate, no vendor
contract, and no error to raise. A mis-mapped field returns a value of the right
type in a plausible range — and it is simply wrong.

## This is not a bug

| | Bug | Data incident |
|---|---|---|
| Something failed | Yes — traceback, red test, non-zero exit | No. Everything was green |
| Reproduction | Run the thing, watch it break | There is nothing to "break" — it produces output happily |
| Found by | The pipeline | **Disagreeing with reality** |
| Fix proves itself by | Red repro goes green | A value now reconciles against an independent source |

**Tie-break:** did anything actually fail? If the pipeline was green and the
output is still wrong, it is an incident.

## How these get found

An incident is always a **contradiction with an independent source**. Name the
source in the report:

- **`players.csv`** — raw, unfiltered, ships with the game. The strongest check
  available for anything in a day-0 state.
- **The ground-truth export** — from a disposable standard-mode save, ideally a
  simulated one. Checks the parser against *mutated* data, which day-0 cannot.
- **The in-game UI** — but read
  [data-access.md §5](../../docs/data-access.md) first. Displayed ratings are
  scale-converted and possibly scout-filtered; a UI mismatch may be a display
  transform, not a parser fault.
- **Real-world baseball** — via the embedded Lahman ID. A player's real career
  line is a free sanity check on a stat block.
- **Internal consistency** — team payroll that doesn't sum to its contracts, a
  roster that doesn't reconcile to a team's player count, a rate stat outside
  `[0, 1]`.

## What a report must carry

1. **The wrong value**, and where it surfaced (table, column, key).
2. **The independent source** it contradicts, and that source's value.
3. **Blast radius** — how far downstream it flowed. A bad rating that reached a
   recommendation the GM executed is a different severity from one caught in
   bronze.
4. **When it entered.** Was it always wrong, or did it start at a snapshot? A
   value that changed correctness without a code change points at a game patch
   invalidating the field map ([data-access.md §8](../../docs/data-access.md)).
5. **Epistemic label** on the claim that it *is* wrong. "This looks too high" is
   `assumed` and is a task; "this contradicts `players.csv` row 39655" is
   `verified`.

## The obligation a bug doesn't carry

**Fixing forward is only half the work.** Snapshots already landed were parsed
with the old field map. Every incident owes a **backfill plan** alongside the
fix: which snapshots are affected, whether they can be re-parsed from the
retained save copies, and which downstream models must be rebuilt.

If a snapshot's source save is gone, say so. Data that cannot be re-derived is a
permanent hole in the history, and the front office should not be reasoning over
it as though it were sound.

## Layout

One directory per incident, `_done/` for terminal items — matching the sibling
tracks. Index below.

## Index

_No incidents yet._
