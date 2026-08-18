# `list_id` semantics — settled by operator reading, 2026-08-17

Phase 6 of `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` requires the
`team_roster.list_id` enum to be resolved before the roster report can print a human label.
The plan directs that it be settled by **asking the operator to read the roster screen**
rather than inferred from counts, because *"a wrong human label produces a confidently wrong
roster with nothing throwing"*.

That read has happened. **Epistemic label: `verified`** — a direct reading of the game's own
roster screen, cross-checked against `ootp_truth_real` on four falsifiable predictions.

## The mapping

| `list_id` | Meaning | Scope |
|---|---|---|
| 1 | **Current team assignment** — the club a player is actually rostered with | Every player, exactly once |
| 2 | **Active roster** of whichever club he is assigned to | Any team level |
| 3 | **Secondary (40-man) roster** | **MLB level only** |
| 4 | **Injured list** | Any team level |

A player's rows therefore answer three independent questions — *which club*, *what standing
there*, and *is he on the parent club's 40-man* — and the second and third can point at
different teams.

## Method

The operator loaded the standard-mode save (Chicago Cubs, 2024-03-18 — the only save
with an export, so every answer is checkable) and opened the **Los Angeles Dodgers** roster
page. **Call it the standard-mode save, never "the probe save":** `config.Settings` binds
`truth_save` to *Test Save - Standard Mode* and `probe_save` to *Test Save - Challenge Mode*, so
the loose word names the wrong file — and the file it names is a Boston challenge-mode save that
is a near-twin of the managed league.
Eight players were chosen because their export rows fall into four distinct
list-membership signatures, so a single screen read discriminates all four values at once.
The operator was **not told the hypothesis first**, to keep the reading independent.

| Player | Operator read the screen as | Export rows (team 15) |
|---|---|---|
| Mookie Betts | Active + 40 Man | 1, 2, 3 |
| Austin Barnes | Active + 40 Man | 1, 2, 3 |
| Walker Buehler | Injured List + 40 Man | 1, 3, 4 |
| Blake Treinen | Injured List + 40 Man | 1, 3, 4 |
| Clayton Kershaw | Injured List | 1, 4 |
| Tony Gonsolin | Injured List | 1, 4 |
| J.P. Feyereisen | Triple A + 40 Man | 3 |
| Dalton Rushing | Triple A + 40 Man | 3 |

The operator also supplied the rule that makes the table consistent: **anyone on the Active
Roster is on the 40-man by default.**

## The four cross-checks, all confirmed

1. **`list_id = 1` is exactly one row per player.** 7,370 rows over 7,370 distinct players,
   and 7,370 is also the total distinct players anywhere in `team_roster`. Every player has
   exactly one, so it cannot be a roster *tier* — it is the assignment itself.
2. **The decisive prediction.** Feyereisen and Rushing hold `list_id = 3` at the Dodgers but
   **no** `list_id = 1` there. If list 1 is assignment, they must hold it at the affiliate.
   Measured: both hold `list_id` 1 **and** 2 at team 52 (Oklahoma City, level 2). Assigned to
   Triple-A, active at Triple-A, on the parent club's 40-man — matching the screen exactly.
3. **`list_id = 3` occurs at MLB level only** — all 935 rows sit on level-1 clubs. The 40-man
   is an MLB-only construct, so a minor-league team can never carry one.
4. **`list_id = 4` occurs at every level** (1, 2, 3, 4, 6). An injured list is not
   MLB-specific, which is what distinguishes it from list 3.

League-wide counts, consistent throughout: `{1: 7370, 2: 7037, 3: 935, 4: 330}`.

## The strongest check: the screen's own panel counts reconcile exactly

The operator supplied a full-organization screenshot, which turns the reading into
**arithmetic across three independent panels** rather than a per-player spot-check.

> **The exhibit, so this reading stays checkable.**
> `var/operator/screenshots/2024-03-18-test-save-standard-mode-dodgers-organization.png` —
> gitignored, because a game screenshot is OOTP's data
> ([ADR 0006](../../../../docs/decisions/0006-public-repo-local-data.md)), so the path is recorded
> rather than the image tracked.
>
> The save is the **Cubs'** and the page is the **Dodgers'** — which is why every panel reads
> *Show Ratings (D. Kantrovitz)*, the Cubs' scouting director. The 2024-03-18 date is `measured`
> from `saved_games.dat`, not read off the screen: the Organization header shows
> `YESTERDAY / TODAY / TOMORROW` as labels and its first dated row is three days out, so a date
> taken from that screen runs ahead of the save.

The Dodgers' 39 distinct players partition as:

| Export signature | Players | Panel it corresponds to |
|---|---|---|
| 1 + 2 + 3 | 26 | *Los Angeles Active Roster* header reads **(26/26 Players)** |
| 1 + 3 + 4 | 4 | Injured List, still carrying a 40-man row |
| 1 + 4 | 4 | Injured List, **no** 40-man row |
| 3 only | 5 | on the 40-man while assigned to Oklahoma City |

**40-man total = 26 + 4 + 5 = 35**, and the panel header reads *Secondary (40-man) Roster
(**35/40** Players)*. The Injured List panel shows **8** MLB-level rows = 4 + 4. Three headers,
three matches, no fitting.

## The 60-day IL drops a player from the 40-man

This is what distinguishes the `1+3+4` group from the `1+4` group, and it is a real baseball
rule the engine models faithfully.

The Injured List panel's *IL Time Left* column reads `16 days` for Buehler, Gage, Sheehan and
Treinen — all of whom hold `list_id = 3`. It reads `61 days (60)` for Gonsolin, Graterol,
Kershaw and May — none of whom do. A 60-day IL placement frees the 40-man spot, so the player
keeps his assignment (`list_id = 1`) and his IL row (`4`) while losing his secondary-roster
row (`3`).

**Consequence:** the 40-man roster is not "the 26 active plus reserves". Counting it from
`list_id = 3` is correct; deriving it as *active + injured + prospects* would over-count by
however many players sit on the 60-day IL.

The same panel lists injured affiliate players below a separator — Frasso and Ryan at OKC
(AAA), Crowell at RAN (A), Brown at ALA1 (R) — which is why `list_id = 4` appears at team
levels 2, 3, 4 and 6 and not only at MLB.

## Confirmed a second time, on the league we actually manage

The operator supplied the same screen for **`OOTP-AI.lg` at 2024-03-07**
(`var/operator/screenshots/2024-03-07-ootp-ai-boston-organization.png`). This is a stronger
replication than a second club would be, because it changes three variables at once: a different
club, a different save, and **Challenge Mode instead of Standard**. There is no export behind it,
so it confirms the *rules* rather than re-deriving them.

Boston's headers read *Active Roster (**26/26**)* and *Secondary (40-man) Roster (**30/40**)*, over
seven MLB-level injured rows. Those seven split by *IL Time Left* exactly as the Dodgers' eight
did — `61 days (60)` for Fulmer, Giolito, Hendriks and Murphy; `11`/`16 days` for Grissom, Mata and
Refsnyder — and the 40-man panel's TEAM column shows Cooper Criswell at `WOR (IL, AAA)`, the
cross-team fan-out visible in one cell.

**26 active + 3 short-IL + 1 affiliate-assigned = 30.** The four 60-day players are excluded, which
is the same rule closing the same arithmetic on the other side of a mode boundary. The two findings
this document rests on — the **cross-team fan-out** and the **60-day IL dropping a player from the
40-man** — therefore hold in Challenge Mode, which is the mode every real decision will be made in.

Expected in `OOTP-AI.lg` at `team_id` 4, and asserted by Phase 6: `list_id` 1 → 33 rows, 2 → 26,
3 → 30, 4 → 7; **96 rows over 34 distinct players.**

## League-wide invariants worth asserting in Phase 6

Measured across all 259 teams of the standard-mode export. Each is a hard number that a mis-parsed
`list_id` would break immediately, which makes them better acceptance criteria than a row
count:

- **Every one of the 30 MLB clubs has exactly 26 rows at `list_id = 2`.** Zero exceptions.
  That is the active-roster limit, and it is the single sharpest assertion available: a
  walker that mixed up two list values would almost certainly not land on 26 thirty times.
- **No MLB club exceeds 40 rows at `list_id = 3`** — min 27, max 37, mean 31.2. The cap is
  respected and clubs sit under it in spring, so an off-by-one in the enum would likely push
  some club over 40.
- **`list_id = 1` is 1:1 with players** — 7,370 rows, 7,370 distinct players, which is also
  the total distinct players in `team_roster`.
- **60-day IL, league-wide:** 58 MLB-level `list_id = 4` rows have no `list_id = 3` row,
  against 118 that do. Both populations are large enough that a parse dropping either would
  be visible.

Note these are properties of the **standard-mode** export at 2024-03-18. The 26 and the 40 are league
*rules* and should hold in the managed save too; the 58/118 split is a state of that universe
on that date and must not be asserted against `OOTP-AI.lg`.

## Player flags, noted but not landed

The screen's legend records per-player markers this slice does **not** parse, listed so a
later reader knows they exist rather than rediscovering them: `*` on the 40-man · `+` out of
minor-league options · `#` Rule 5 eligible · `!` must be on the active roster · `&` playoff
eligible · `^` right to refuse a minors assignment · `"` contract with majors option.
`unconfirmed` as to where any of these live in the save; none is in Phase 6's field set.

## Consequence for the grain — wider than the plan anticipated

The plan names the fan-out as *"a player sits on the active list **and** the 40-man
simultaneously"*. That is true and it is not the whole shape.

**A player can also appear under two different `team_id`s at once.** A prospect on the parent
club's 40-man but assigned to Triple-A holds `list_id = 3` under the MLB club and
`list_id = 1, 2` under the affiliate — three rows, two teams, one player. Measured on the
Dodgers: **103 roster rows over 39 distinct players.**

Three consequences the report layer has to honour:

- **"Who is on Boston's roster" has no single answer.** It resolves differently for list 1
  (assignment), list 2 (active) and list 3 (40-man), and the roster report must say which one
  it is showing rather than implying a canonical roster exists.
- **A naive join from `teams` to `team_roster` double-counts prospects**, because a 40-man
  prospect is attached to two clubs.
- **The plan's `>= 26` assertion for Boston is now explicable rather than defensive.** 26 is
  the active-roster size, which is `list_id = 2` — the Dodgers' list-2 group is exactly 26.
  A count against list 1 or list 3 would be a different number and a different claim.

## Disposition

The roster report **may print human labels** — Active Roster, 40-man, Injured List, and the
assigned club — since the mapping is `verified` rather than `inferred`. Phase 0's
opaque-integer fallback is **not** in force and can be retired for this field.

`docs/data-access.md` should carry this mapping with its `verified` label; route it through
`/update-docs` at Phase 12 with the rest of the first-sight docs-delta, per the plan's
deny-set rule for that file.
