# Scouted view — follow-up findings, and an open question for ADR 0014

> Investigated 2026-08-16 by the main thread, after the Phase 2 spike verdict in
> `spike-scouted-view.md`. This is **evidence for a decision, not a decision.** It
> exists because the spike's second half came back `inferred` and negative, and that
> half is the mechanic [ADR 0014](../../../../docs/decisions/0014-staff-is-the-information-channel.md)
> rests on.
>
> Citations are code spans, never Markdown links, and nothing links into `var/`.

## Summary

The spike established that **OSA is stored** in `scouting.dat` (`measured`) and that
the organization's own scouted view is **not present at any fixed offset** in the
record's stable prefix (`inferred`). Four follow-up hypotheses were tested. Three
were refuted, one was confirmed, and a fifth consideration — supplied by the
operator from the game's own settings — materially weakens how much any of it proves.

**The verdict is unchanged and the open half stays open.** What changed is that we
now know *why* it is hard to settle, and *when* it would be easy.

## Confirmed

**The export is a faithful oracle for both perspectives** (`measured`). Spot-checked
against the running game on a named prospect on the Cubs' board: the export's
`batting_ratings_talent_*` columns reproduce the in-game display **exactly**, for the
Head Scout view and the OSA view independently, on a player where the two disagree on
four of five ratings. (Values not transcribed here — this repo is public and they are
Out of the Park Developments' data. The check re-runs in seconds against
`ootp_truth_real`.)

This matters beyond the immediate question: it validates Tier B for *ratings at
display scale*, which nothing had established. It also confirms `scouting_accuracy`
1–5 is the `ACC High/Avg/…` grade the game shows on the player's Scouting tab.

Also confirmed: `scouting_coach_id = -1` is OSA and `2759` is the **club's own
scouting director** — verified from `ootp_truth_real.coaches`, where 2759 resolves to
a coach with `occupation = 6` on `team_id = 6`, the probe save's human club. The
perspective labelling in the spike was correct, and is not an artefact of the export
having been taken with *Show real player ratings*.

## Refuted

**1. That the perspectives were mislabelled** (`measured`). See above. If `-1` had
been the club's aggregate view and `2759` an individual scout, the spike's conclusion
would have inverted. It does not.

**2. That `scouting.dat` covers only players the club has actually scouted**
(`measured`). It holds one record for every one of the 18,072 active players, ids
ascending. More decisively: on the 6,600 players where the two exported perspectives
disagree, the stored value follows **OSA** — and it does so at the same rate inside
the Cubs' own organisation (80 of 85) as outside it (6,327 of 6,515). If the file
held "what we know", the club's own 255 players are where its own read would surface.
It does not surface. Bands for this test were fitted on the 11,472 *agreeing* players
so the mapping is not biased toward either perspective.

**3. That the record carries a per-player scouting date or a variable-length report
history** (`measured`). The record does carry a date at **+6**, decoding cleanly as
the documented `u8 day, u8 month, u16 year` primitive — but it reads **2024-03-18 for
all 18,071 records**, i.e. the sim date, a snapshot stamp. And record length does not
vary with club affiliation: mean stride 129.9 bytes inside the Cubs' organisation
against 130.0 outside it. A variable-length run of dated reports would show up in
both places. It shows up in neither.

The game certainly *has* dated, attributed, accuracy-graded reports — the Scouting tab
shows them, with a named scout, a report date, and a "Past Reports" list. They are
simply not in this file.

## The byte budget — the strongest structural argument

`measured`. `scouting.dat` is 2,349,181 bytes holding 18,072 player records, ≈130
bytes each.

| | bytes |
|---|---|
| available per player | **130** |
| one perspective, 133 rating columns as `u16` | 266 |
| two perspectives as `u16` | 532 |
| one perspective as `u8` | 133 |
| the 76 non-split columns alone, as `u16` | 152 |

**Nothing fits.** Not two perspectives, not one, not even the overall-only subset.
This is a capacity argument and is therefore **immune to the variable-length caveat**
that keeps the offset sweeps at `inferred`: the budget is fixed however the fields are
laid out. It follows that most of the export's 133 scouted columns — the 27 talent,
15 vsL and 15 vsR splits especially — are **generated at export time for both
perspectives** (`inferred`).

## The operator's correction, and why it weakens all of the above

`measured` from the game's own league settings, supplied by the operator:
**OSA ratings regenerate once per year; the club's own scouting updates continuously.**

This league sits at 2024-03-18, eleven days from creation, with OSA freshly
generated — so the two views agree more often now than they are likely to later.
Every discriminating test above therefore ran with the fewest disagreeing players this
league will ever offer.

The disagreement-subset test remains valid, because it conditions on the 6,600 players
where the two views *already* differ. But a null result — "the club's view is not
here" — is weaker evidence at day 11 than the same null would be at mid-season.

> **Two things that must not be conflated, and an earlier draft of this section did.**
>
> **Agreement is not accuracy.** OSA and the head scout are two *independent, noisy
> estimates* of the same hidden rating. They do not begin correct and drift apart;
> they can agree while both being wrong, and be wrong in different directions.
> Convergence tells us nothing about which is closer to the truth.
>
> **Only one of those questions is ours to ask.** How often they differ is a
> *discriminability* property, and it is all the parsing question needs — to identify
> which view a stored field holds, it is enough that the two disagree somewhere.
> Which view is *right* is an accuracy question, answerable only against true ratings,
> which [ADR 0012](../../../../docs/decisions/0012-scouted-ratings-only.md) forbids us
> from serving and the operator has ruled out landing at all. **That question is
> deliberately closed, and later divergence does not open it.**

### The disagreement is the product, not noise to be resolved

This follows directly, and no artifact currently records it, so it is written here
before a later phase quietly assumes otherwise.

When both views can be served, the front office must receive **both, with their
provenance** — who filed it, on what date, at what accuracy grade — and **must not be
handed a blended "best estimate."** Merging them would destroy exactly the judgement
the experiment exists to observe:

> *Do I trust a stale report from a mediocre scouting director, or OSA on this player?
> Should I hire a better director, add scouts, or push budget at scouting one league
> in particular?*

That is [ADR 0014](../../../../docs/decisions/0014-staff-is-the-information-channel.md)'s
mechanic seen from the GM's chair, and [ADR 0016](../../../../docs/decisions/0016-gm-reads-reports-not-queries.md)'s
information economy in its concrete form. A pipeline that averages the two, or picks
the "better" one on the GM's behalf, has made the club's central strategic decision in
a transform — silently, and with no baseball reasoning behind it.

Practical consequence for whichever slice serves ratings: carry the **report date and
the accuracy grade alongside every scouted value**, and never collapse the two
perspectives into one column. A stale high-accuracy report and a fresh low-accuracy
one are different evidence, and only the GM is positioned to weigh them.

### They are not competing estimates. They are different products.

The operator's account of the in-game economics, recorded because it explains why the
two views exist at all:

> OSA's mandate is **breadth** — some rating for every player, which no organisation
> has the resources to do accurately. The club's lever is **allocation**: scout one
> player every day and you will know him as well as your scouting director is capable
> of knowing anyone — and you will know only him.

So the GM's question is not "which number is better." It is **"where have I bought
depth, and was that the right place to buy it?"** Coverage, recency and accuracy stop
being metadata about a rating and become the thing the GM is actually managing. The
`ACC` grade and the report date are not provenance decoration; they are the readout on
where the scouting budget went.

**Therefore the absence of a club report is a fact, not missing data.** A player the
organisation has never looked at is a player about whom we have *only* the public
view — and that is decision-relevant, not a gap to be filled or defaulted. This is the
highest-stakes instance yet of the parser rule that structural absence lands as `NULL`
and never as zero, and it extends to the report layer: a blank club view must read to
the GM as **"we have never scouted him"**, never as "unknown" and never silently
back-filled with OSA.

Two consequences worth carrying forward:

- **The catalog's coverage statement becomes decision-relevant.** "How many players
  carry a club scouting report, and how recent" is a number the GM prices an action
  against, not a row count.
- **The loop is measurable across snapshots.** Reallocating scouting is a GM action
  under [ADR 0013](../../../../docs/decisions/0013-action-economy.md); its effect
  should appear in the next snapshot as changed accuracy and recency on a specific
  population. The `(save_id, sim_date, ingest_seq)` grain already supports that
  comparison, which is a use for snapshot history nobody had named when it was chosen.

### The allocation signal is real, and it is in the accuracy field

`measured`, and it **retracts an inference an earlier draft of this document made.**
That draft argued: the club's view has exactly 18,072 rows — every active player,
including thousands in leagues the Cubs have never scouted — and a genuine
report-based system would be *sparse*, so density is evidence the export materialises
it. **That reasoning was wrong**, and the operator's counter-hypothesis beats it:
the game does not model "unscouted" as *absence*. It models it as **low accuracy**.
Everyone has a view; how much it is worth is the readout.

The distribution of `scouting_accuracy` for the club's view is exactly what allocation
predicts, and OSA's is flat by comparison (constant `3` for all 18,072 rows):

| population | acc 1 | acc 2 | acc 3 | acc 4 | acc 5 | total |
|---|---|---|---|---|---|---|
| Cubs organisation | 0 | 0 | 210 | 25 | 20 | **255** |
| other MLB clubs | 0 | 929 | 1 | 0 | 0 | **930** |
| everyone else | 2,407 | 8,710 | 5,504 | 266 | 0 | **16,887** |

Read it as a scouting budget. Your own organisation never drops below 3. Other MLB
clubs sit uniformly at 2 — you watch them play, you do not scout them. Out in the wider
world most players sit at 1–2, and **266 sit at 4**: players the club deliberately
went and looked at. That is the lever, visible in the data.

The display mapping is confirmed against the game: `ACC High` → stored `4`,
`ACC Avg` → stored `3` (`measured`, spot-checked on two Cubs players and one outside
prospect).

**So the honest statement is:** density is *expected* under this model and is not
evidence of anything. Whether the club's view — or the accuracy behind it — is
*stored* remains open.

`inferred`: a sweep of every byte offset in the record's stable prefix found **no
field carrying the accuracy distribution**. The best apparent match (+7, 31.6%) is a
**false positive** and is recorded here as a caution: its observed values are
`{3: 18070}` — the *month* byte of the sim date, agreeing by coincidence with every
player whose accuracy happens to be 3. A naive best-match search reports it as a find.

This is consistent with a storage model that fits the byte budget comfortably: the
save stores OSA's annual snapshot plus the club's **scouting allocation settings**,
and derives per-player accuracy — and from it the club's view — at render time. If
that is right, the allocation lever may be readable even where its per-player result
is not. **All of it stays `inferred` until the record is walked sequentially**, since
every sweep in this document is blind past the first variable-length region.

### What this closes: the scouting loop can grade itself

Recorded now because the *capability* is seasons away but the **retention decision it
depends on is immediate.**

If accuracy is the allocation readout, the loop closes on itself:

> allocate scouting budget → accuracy moves → the club's read is recorded →
> the season happens → **compare the read to what actually occurred** → conclude the
> scouting department is worth its cost, or is not → reallocate.

That makes [ADR 0014](../../../../docs/decisions/0014-staff-is-the-information-channel.md)
*self-evaluating*. Its central claim — money spent on scouts buys resolution — stops
being an article of faith and becomes a measurable one, which is the whole premise of
this project applied to one of its own decisions.

**The line that must not be crossed, and it is easy to cross by accident.** The
backtest compares a past scouted read against **realized outcomes** — performance,
development, what the player turned out to be. It must **never** compare a scouted
read against the **true rating**. The second is trivially easy (`players.csv` is right
there, raw), looks like the more direct measurement, and is precisely the inference
layer 0014 forecloses: it reconstructs the answer key and calls it evaluation.
Grading a forecaster against what happened is legitimate; grading it against the
hidden truth is reading the truth. Only the first is available to a real front office.

**Two failure modes, two different remedies**, which is why "in either direction"
matters:

- **Bias** — reads consistently high or consistently low. A systematic tilt in the
  person. The fix is personnel.
- **Variance** — reads scattered around the outcome without direction. Insufficient
  looks. The fix is budget or coverage.

Accuracy should predict variance; it says nothing about bias. A high-accuracy scout
who is reliably optimistic is a different problem from a low-accuracy one, and
collapsing them into "our scouting is bad" loses the actionable half.

**What it requires of us now.** A backtest is only possible if the read *as it stood
at the time* was retained. A warehouse holding only the current scouted rating can
never answer "what did we believe in March?" The append-only
`(save_id, sim_date, ingest_seq)` grain already preserves exactly that — **a third use
for snapshot history that nobody had named when the grain was chosen.** The
consequence is that retention must be right from the first landed snapshot; history
not captured is not recoverable later, and by the time the backtest is worth running,
the seasons it needs will already have passed.

It also suggests a model that fits every measurement above:

> `scouting.dat` is **the OSA annual snapshot** — precisely the kind of artefact that
> needs compact, uniform, per-player persistence between regenerations — while the
> club's own view is derived from dated report history held elsewhere, or computed.

That model explains the uniform record size, the sim-date stamp, the absence of
per-player report structure, and why the one rating field found bands onto OSA.

## The open question for ADR 0014

0014's decision is that *"if the front office wants a clearer picture, the answer is
always a personnel move, never a code change"*, and its observable is the **gap
between OSA and the organization's own read**. OSA is public and identical for all
thirty clubs; it does not sharpen when we hire.

If the club's own view cannot be parsed, three consequences follow, and none is
cosmetic:

- Every rating the warehouse can serve is the one **every AI club already has**.
- Hiring a scouting director produces **nothing observable** in our data, so 0014's
  first stated Buy — *"staff budget becomes an information budget"* — is false.
- The failure looks like success: reports render, tests pass, and the staff lever is
  silently inert.

Note **[ADR 0012](../../../../docs/decisions/0012-scouted-ratings-only.md) survives
either way.** OSA is a *scouted* view, not the true one, so the GM never sees the
answer key. It is specifically 0014 that loses its mechanism.

**Every route to the club's own view is currently blocked or foreclosed:**

| Route | Status |
|---|---|
| Parse it from the save | Not found; may not be stored |
| Compute it from true ratings + scout accuracy | **Foreclosed by 0014 itself** as an inference layer — and it requires landing the true ratings the operator has ruled out |
| Read it from an export | **Challenge Mode has no export** (ADR 0003), and our league is Challenge Mode |
| Read it from the in-game display | Works — the operator can see it — but it is the HTML/screen path the scope rules out, and it does not scale to 18,072 players |

## What would settle it, in order of cost

1. **A sequential walk of one `scouting.dat` record with byte accounting.** Every test
   in this document swept *fixed offsets*, which goes blind past the first
   variable-length region. This is the Phase 5–7 technique and is not new machinery.
   It converts "not found at a fixed offset" into "accounted for, byte by byte".
2. **Re-run the discriminating tests on a later snapshot**, once OSA has gone stale and
   scouting has had time to move the club's read. Cheap, requires only that the league
   be simmed, and turns the weakest evidence here into the strongest.
3. Only if both fail: an ADR-level decision about whether 0014 survives, and on what.

## Recommended now, independent of the above

**Amend ADR 0012 to the strong form: the parser never *maps* true-rating fields.**
Today's rule permits landing them and forbids serving them — the withhold is policy,
enforced by a field-map category and a guard, and a query that forgets the guard sees
them. Bronze is 1:1 with parser output and cannot filter, so if the parser does not
read them, nothing downstream can leak them, and the guard becomes a schema assertion
rather than a promise.

The parser must still *identify* true ratings precisely — 0014 requires that, to
exclude them — so they stay in the field map as `category = "rating-true"`. Known
address, contents never read.

This costs nothing today, because this slice lands no ratings at all. That is exactly
why it is the right moment to do it.

`players.csv` is unaffected: it is raw, it is Tier A ground truth in tests, and 0012
already permits true ratings there. Tests are not the warehouse and not the advisory
path.
