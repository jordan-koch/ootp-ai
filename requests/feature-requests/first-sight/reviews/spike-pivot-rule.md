# Pre-registered pivot rules — first-sight

> **Written 2026-08-16, before the scouted-view spike was run and before any code
> under `src/ootp_ai/` existed.** That ordering is the point: a pivot rule written
> after the result is not a pivot rule, it is a rationalisation. `git log` on this
> file versus `spike-scouted-view.md` is the evidence for acceptance criterion 18.

Four questions in this slice have genuinely unknown answers, and three of them sit
on the critical path of the headline deliverable. Each is registered here with a
**concrete trigger** and the **consequence that follows**, so that when one fires
nobody has to decide under time pressure what it means.

Citations use code spans rather than Markdown links — `tests/test_doc_links.py`
resolves every relative link target in every tracked `.md` and has no fence
awareness, so a `file:line` citation written as a link fails the build. See
`requests/bugfix-requests/_done/doc-link-guard-mismatch/`.

---

## 1. The scouted-view spike — is the scouted rating view stored, or computed at render time?

**Status: unresolved.** `docs/data-access.md` §5 labels this `unconfirmed` and calls
it the critical-path task. It is the one unknown that can invalidate the project's
central mechanic rather than merely cost time.

**The test**, written verbatim at `docs/data-access.md:288-295` and never run: pull
the values in `ootp_truth_real.players_scouted_ratings` (36,144 rows,
`scouting_coach_id ∈ {-1, 2759}`, 18,072 each) and search the standard-mode probe
save's `scouting.dat` (2,349,181 bytes) for them as u16 little-endian runs
positioned consistently across players. Search **both** the raw ~1–1000 encoding and
the display scale — a null result on one scale alone is not ABSENT. Cross-check the
negative case against `players.csv`-derived *true* values, so a FOUND verdict is not
merely "the file contains numbers in range".

### If FOUND — the scouted view is stored

Ratings have a source. `scouting.dat` is the file a later slice parses, and
[ADR 0012](../../../../docs/decisions/0012-scouted-ratings-only.md),
[ADR 0014](../../../../docs/decisions/0014-staff-is-the-information-channel.md) and
[ADR 0016](../../../../docs/decisions/0016-gm-reads-reports-not-queries.md) have a data
path. **Nothing in this slice changes** — first-sight still lands no ratings. The
verdict is recorded, `docs/data-access.md` §5's label is upgraded through the doc
gate, and the gated ratings work (`coaches.dat`, the internal→display scale dataset,
the OSA-vs-own-scout divergence column) becomes a real candidate for the next slice
rather than a conditional one.

### If ABSENT — the scouted view is computed at render time

**This slice still ships, unchanged and in full.** That is the entire reason ratings
were decoupled from it during scoping: the roster report needs names, positions and
roster membership, and the standings report needs W-L. Neither needs one rating.
The request's observable signal survives a FAIL verdict.

What follows instead:

1. **Record it** with byte evidence and an epistemic label in `spike-scouted-view.md`.
2. **Withhold every rating**, which is already this slice's posture — so no code changes.
3. **File a follow-up request immediately**, not deferred until a ratings slice is
   proposed (plan Decision P9). It is filed against ADRs 0012, 0014 and 0016
   together, because a computed-at-render-time view means the front office can read
   the true ratings and nothing else — which inverts the information asymmetry those
   three decisions were built to create. That is a design problem to solve, and the
   worst outcome is that it goes quiet.
4. **Do not route around it.** No "we'll approximate the scouted view by adding
   noise to true ratings." That would be inventing the club's information channel
   rather than reading it, and it would make every downstream evaluation a fiction
   with a plausible number attached.

### If INCONCLUSIVE

Treat as ABSENT for the purposes of this slice — ship, withhold, file — but say
`inconclusive` in the verdict rather than `computed`, and state what would settle
it. An unconfirmed claim is a task, not a fact (`docs/data-access.md:14`).

---

## 2. `list_id` semantics — what do the roster-list enum values mean?

**Trigger:** the mapping from `list_id` values to human meanings (active roster,
40-man, minor-league tiers) cannot be established to at least `inferred`.

**First resort, and it should almost always succeed: ask the operator to read the
in-game roster screen.** The game shows directly which players sit on which list.
This is validation channel 4 in the plan's §2.5 — roster membership is neither
scale-converted nor scout-filtered, so the display is authoritative for it. Hand
over a handful of `player_id`s per observed `list_id` value and ask which list the
game shows each on. Expect this to land at `verified` in minutes.

**Second resort:** cross-tab against the export's counts —
`ootp_truth_real.team_roster` is 15,672 rows over 7,370 distinct players with
`list_id ∈ {1: 7370, 2: 7037, 3: 935, 4: 330}`. Note that list 1's count equals the
distinct-player count exactly, which is itself a strong hint.

**Fallback, if both fail:**

- Land `list_id` as an **opaque integer**. Do not guess a label.
- Group the roster report by the **raw value**, with a header line stating plainly
  that the meanings are `unconfirmed`.
- **Never print a human label** for any mapping below `inferred`. A wrong label
  produces a confidently wrong roster with nothing throwing — the failure class
  `requests/README.md` built a third track for.
- File a follow-up.

---

## 3. `teams.dat` strict byte accounting — can the walk reach zero residual?

**Trigger:** a zero-residual walk of `teams.dat` cannot be reached inside Phase 5.

**Fallback:** demote to the **diagnostic** tier — assert the walk terminates on a
record boundary and reaches a record count matching an independent count, and
**record** the residual byte count rather than asserting it is zero. Write the tier
rationale into `field_map.toml` so a later reader does not mistake the weaker
assertion for sloppiness. File a follow-up.

**Do not** widen the parsed field set purely to consume bytes. Every landed field is
a field somebody re-validates after a game patch; the field set is a maintenance
liability, not a free win.

---

## 4. The `names.dat` join — does the index encoding resist?

**Trigger:** the name-index encoding cannot be resolved against an answer key.
`docs/data-access.md:238` labels both the index encoding and the table layout
`unconfirmed`, and the feature request calls this the largest single unknown.

**Fallback (plan Decision P5, operator-disposed):** resolve names from
`players.csv` at **render time** for the ~1,712 players carrying a Lahman ID —
`historical_id` is embedded in `players.dat` itself and is `verified` at
`docs/data-access.md:99-102`. Fictional players render as IDs. The report is
degraded but not useless, and the degradation is visible on the page rather than
hidden.

**Hard bind, and it is absolute:** never write a Lahman-ID-to-name lookup to a
tracked file, in any form, under any name. `tests/test_no_leaks.py:106` catches
`players.csv` by **filename only** — a renamed derived copy sails straight through
the guard into a public repo. This is Out of the Park Developments' data
([ADR 0006](../../../../docs/decisions/0006-public-repo-local-data.md)). Resolution
happens at render time, into the git-ignored output root, and nothing persists.

---

## 5. Measured, for Phase 12's documentation correction

Recorded here so the correction has a citation to point at rather than a memory.

**There is no `leagues.dat`.** `docs/league-rules.md:129` and `:295` both assert one.
`OOTP-AI.lg` holds 19 `.dat` files and none is it.

**The league configuration block is in `world.dat`.** The string
`major_league_ml_c_2024.lsdl` — exactly the `schedule_file_1` value
`docs/league-rules.md` §1 records — sits at **byte 5,559,751** of
`OOTP-AI.lg/world.dat`, surrounded by league-shaped records containing
`World Series`, `AL` and `NL`. The same string does **not** appear anywhere in
`teams.dat`, which is where two of the three scoping planners inferred it would be.

**`saved_games.dat` is not plaintext**, contrary to `docs/data-access.md:36-38`
which records that as `verified`. It carries the standard OOTP header and
length-prefixed strings, and it embeds an absolute user-profile path for every save
— so nothing that renders its contents may reach a tracked file.

**Mode changes the save's file set by exactly one file.** The only difference
between the Challenge and Standard test saves is `challenge.dat`; nothing is
*missing* from a Challenge save. `OOTP-AI.lg` and `Test Save - Challenge Mode.lg`
have identical file sets, and the `teams.dat` headers of all three saves are
byte-identical for their first 30 bytes. This is `inferred` at header level and is
promoted to a test in Phases 3, 5, 6 and 7 rather than assumed.
