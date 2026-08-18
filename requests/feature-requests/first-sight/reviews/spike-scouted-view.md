# Scouted-view spike — verdict

> Run 2026-08-16 against the retained standard-mode save and `ootp_truth_real`, the
> only save/export pair that can answer this. The pivot rules were committed first
> (`56741e5`), before this file existed or anything ran — that ordering is AC18.
>
> Citations are code spans, never Markdown links, and nothing links into `var/`.
> See `requests/bugfix-requests/_done/doc-link-guard-mismatch/`.

## Verdict: `stored`

`measured` — **The scouted rating view is stored in `scouting.dat`, on the raw
~1–1000 scale, one variable-length record per player.** The export's
`players_scouted_ratings` rows for `scouting_coach_id = -1` — the OSA public
scouting view — are a display-scale rendering of values that are physically present
in the save.

`inferred` — **The organization's own scouted view (`scouting_coach_id = 2759`) is
not stored in the stable prefix of that record, and nothing in that prefix predicts
its divergence from OSA.** Weaker label on purpose: see *Caveat* below.

## The pre-registered branch now live

**FOUND** (`spike-pivot-rule.md` §1). Ratings have a source; `scouting.dat` is the
file a later slice parses; ADRs 0012 / 0014 / 0016 have a data path.
**Nothing in this slice changes — first-sight still lands no ratings.**

The FOUND branch's obligations: record the verdict (this file), upgrade
`docs/data-access.md` §5's `unconfirmed` label through the doc gate (Phase 12), and
the gated ratings work becomes a real candidate for a later slice.

## Method

Values were pulled from `ootp_truth_real.players_scouted_ratings` (36,144 rows;
`scouting_coach_id ∈ {-1, 2759}`, 18,072 each) and searched for in the save's
`scouting.dat` (2,349,181 bytes), as `docs/data-access.md:292-295` specifies. Run as
throwaway scripts under the git-ignored `var/`, never as tracked code; every handle
`"rb"`; the warehouse side used the enforced read-only session in
`src/ootp_ai/db.py`.

**Both scales were searched, as pre-registered.** The naive search — the exported
values as literal u16 runs — was abandoned once measured: *the export writes ratings
on the 20–80 display scale, not the raw scale* (11–13 distinct values per column,
min 20, max 80). Searching for those byte patterns matches noise everywhere, so a
null result on that scale would have meant nothing. The raw-scale search was run
instead, in the direction that carries information: locate the stored value, then
test which exported view it maps onto.

## Byte evidence

- **Header** — `scouting.dat` carries the standard header: `00 4f 4f 54 50` then
  version `19 00 00 00` (25), then `0b/68/54/01` and the self-declared filename
  `scouting.dat`. Byte-identical for the first 40 bytes across all three saves.
- **Records** — all 18,072 `player_id`s from the export appear as `u32`-LE in
  ascending order, first at byte 196, last at byte 2,349,062, 119 bytes of tail.
  Stride between consecutive ids is **123–137 bytes** (mode 127) — variable-length
  records averaging 130 B, consistent with `docs/data-access.md:289`'s ~128 B guess.
- **The mapping** — the `u16`-LE at **+40 from the id field** maps onto the exported
  OSA `batting_ratings_overall_contact` in **11 monotone bands**: stored
  1–38 → display 20, 39–108 → 25, 109–182 → 30, 183–254 → 35, 253–318 → 40,
  317–373 → 45, 372–411 → 50, 410–433 → 55, 433–453 → 60, 454–472 → 65, 504 → 75.
  `r = 0.979`. Same structure at `+44` → overall power (`r = 0.982`, 11 bands) and
  `+46` → overall eye (`r = 0.983`, 12 bands).

  **Correction, main thread, after re-running `07_bands.py`.** An earlier draft of
  this document said "zero overlap", and the handoff cited `overlapping=0`. Both
  overstate it, and the second mis-cites its source: the metric is computed in
  `08_divergence.py:85`, not `07_bands.py`, and it counts an overlap only when
  `next_min < prev_max - 1` — **it tolerates a one-unit overlap by construction.**
  Five boundaries do in fact overlap by one or two stored units: 253–254, 317–318,
  372–373, 410–411, and 433. The accurate claim is **"no band overlaps by more than
  one stored unit."**

  That correction *strengthens* the reading rather than weakening it. If display is
  a rounded function of the stored value, adjacent bands sharing their boundary
  value is exactly what rounding produces; perfectly disjoint bands would be
  slightly too clean. The contrast that carries the argument is unaffected and is
  visible in the same output: the own-scout bands run 1–199, 1–231 and 1–247 for
  display 20, 25 and 30 — overlapping wildly — and the TRUE bands likewise. Only the
  OSA bands form a step function.
- **The same value appears twice per record**, at `+40` and `+53`, identical for
  1,017 of 1,544 real players and within a point or two otherwise — two views of one
  rating (plausibly vsL/vsR), not two scouting perspectives.

## The negative controls, both of them

**1. Against the export's TRUE ratings.** At `+40`, `r(OSA) = 0.979` beats
`r(own scout) = 0.913` and `r(TRUE) = 0.873`. Restricted to the 6,600 players whose
two exported perspectives *disagree* on contact, the stored value sits in the OSA
band rather than the own-scout band **6,099 times (92.4%)**, and `r(OSA) = 0.973` vs
`r(TRUE) = 0.849`. If the file mirrored true ratings, TRUE would win.

**2. Against `players.csv`, which is raw and ships with the game** — the control the
pivot rule named. For the 1,544 players matched save → export → `players.csv` by
Lahman ID: the stored value at `+40` **never** equals the player's raw true contact
(0 of 1,544 against `Contact vL`; 54 of 1,544, 3.5%, against *any* raw contact
column — chance), while occupying the same scale (stored 1–504, median 196; raw true
24–502, median 195) at a mean absolute distance of **28.8 raw points**, with only
13.5% within 5 points. Same scale, near but never equal, banding onto the *scouted*
column: that is a scouted estimate, not the answer key.

## What is not stored, and the caveat that keeps it `inferred`

No offset in the record's stable prefix tracks the own-scout view better than the
OSA offset does, and the best predictor of `(own − OSA)` anywhere in that prefix is
`r = 0.19` for batting and `r < 0.09` for pitching, fielding and running — i.e.
nothing. `scouting_accuracy` (1–5 for the club's coach, constant 3 for OSA) has no
correlate either (best `r = 0.116`).

**Caveat, and it is why this half is `inferred` rather than `measured`:** the sweep
indexed offsets relative to the id field, which is only valid while nothing
variable-length intervenes. Records *are* variable-length, so fields past the first
variable region shift per player — visible in the results as pitching, fielding and
running ratings failing to band at any fixed offset even though they are certainly
in there somewhere. **Absence at a fixed offset is not absence from the file.** A
sequential walker may well find the own-scout view. Nothing here should be read as
proof it is computed at render time, and no offset in this document may be
hardcoded into a parser.

## What would settle the open half

A sequential walk of one `scouting.dat` record with byte accounting, then the same
banding test against `scouting_coach_id = 2759`. That is a later slice's work
(this one lands no ratings), but it is the question ADR 0014 rests on: if the club's
own read is computed rather than stored, "staff is the information channel" has no
data path even though OSA does. **Recommend filing that as a follow-up now** rather
than when a ratings slice is proposed.
