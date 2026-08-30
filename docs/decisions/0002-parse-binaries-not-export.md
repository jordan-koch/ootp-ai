# 0002 — Ingest by parsing save binaries, not the in-game export

**Status:** Accepted
**Date:** 2026-08-15

## Context

OOTP 25 ships a database export under Database Tools: CSV files, an MS Access SQL
dump, and a direct-to-MySQL export, covering 70 documented tables. That is an
obvious ingestion path and it is well documented by the game itself.

Two facts disqualify it as *the* path
([data-access.md §6](../data-access.md)):

1. **It is hidden in Challenge Mode.** Verified by comparing the same menu across
   a challenge and a standard save: the six export actions are absent from the
   challenge save while every surrounding item is present. The managed league
   runs in Challenge Mode ([ADR 0003](0003-challenge-mode-league.md)).
2. **Its automation ceiling is monthly.** "Automatic Data Dump Settings" offers
   monthly and yearly. Nothing daily. A front office advising on lineups needs
   state fresher than that, which means a human clicking Export every sim day.

Separately, the save binaries were found to be unencrypted and uncompressed, with
conventional little-endian primitives, and `players.csv` ships with the game
carrying raw ratings for every real player — enough ground truth to map the
binary's fields.

## Decision

**Ingestion is our own parser reading the save's `.dat` files directly.**

The in-game export retains exactly one sanctioned use: a **one-time ground-truth
artifact generated from a disposable standard-mode save**, used to validate the
parser. It is never part of the running pipeline.

## Consequences

**Buys:**

- Works in Challenge Mode, where the export does not exist.
- Fully automated, on our schedule, with the game closed. No human in the
  ingestion loop.
- Complete access — the parser is not limited to the 70 tables the export chose
  to expose.
- The ingestion layer is genuinely ours, which was a stated project goal.

**Costs:**

- **We own a reverse-engineered format.** Every field is a mapping we derived and
  must validate. There is no vendor contract and no error message when we get one
  wrong — a mis-mapped `u16` yields a plausible number, not a crash.
- **A game patch can invalidate the field map** ([data-access.md §8](../data-access.md)).
  Mitigated but not solved by `players.csv` shipping alongside the binaries and
  re-deriving the ground truth.
- Records carry variable-length regions, so parsing is sequential and slower to
  write than a fixed-offset reader would be.
- Substantially more up-front work than pointing dbt at an exported schema.

**Forecloses:**

- Depending on the export in any automated path. If a future change makes the
  pipeline require a manual in-game click, that is a violation of this ADR.

## Notes

The validation strategy matters as much as the decision. `players.csv` maps
fields; a ground-truth export from a *simulated* standard save is what proves the
parser against mutated, non-day-0 data — grown stat arrays, injuries, roster
churn. Day-0 state is the least informative possible test case, because every
variable-length region is at its minimum.

### Correction 2026-08-29 — "disposable" is wrong, and it was load-bearing

The Decision above says the export is generated *"from a **disposable** standard-mode
save."* The **export** is one-time; the **save** is not disposable, and calling it that
invited deleting the one artifact that keeps this ADR's central cost — *"we own a
reverse-engineered format … there is no error message when we get one wrong"* — under
observation.

`measured` — Tier B compares the parsed **binaries** against the exported tables. The
export alone proves nothing; it is the answer key, and the save is the question. Delete
the save and row-for-row validation ends for **fictional players and roster lists** —
precisely the populations `players.csv` cannot reach, since a generated player carries no
external identifier at all. Rebuilding costs a save rebuild plus an export run, and the
rebuilt league would be a *different* one, so every measured population in
[`data-access.md`](../data-access.md) would have to be re-established.

**It is a retained project asset.** `.env`'s `OOTP_TRUTH_LEAGUE` names it and says so.
The genuinely disposable save is the other one — the Challenge Mode twin at
`OOTP_PROBE_LEAGUE`, which is simmable, re-creatable, and is where every
filesystem-touching test runs first.

This corrects the wording, not the decision: parsing remains the ingestion path and the
export remains barred from every automated path.
