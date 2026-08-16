# League Rules

The rule environment every baseball decision sits inside. `docs/data-access.md`
says what can be *read*; this says what can be *done*.

> **Snapshot: league creation, sim date 2024-03-07.** League `OOTP-AI`,
> Boston Red Sox, Challenge Mode.
> **These rules are not constants.** The league is configured to evolve — roster
> sizes, IL length, the DH rule, **free-agency service requirements**, the run
> environment, expansion and relocation can all change without warning. See
> §4. Do not treat a value here as current without checking it.

This document deliberately does **not** transcribe everything. Award names,
milestone thresholds, All-Star ceremony details and Hall of Fame procedure are
recorded nowhere here because they change no decision. What is here is what
changes a decision.

---

## How to read this

Three parts, with different lifespans:

| § | Part | Lifespan |
|---|---|---|
| 1 | **Queryable config** | Temporary. Every value is a column on the `leagues` row; the warehouse supersedes this the moment the parser lands |
| 2 | **Unqueryable config** | **Permanent.** Not present in the export — this document is the only copy |
| 3 | **What it implies** | **Permanent.** Never in the save, in any form ([ADR 0011](decisions/0011-gm-memory-is-tracked.md)) |

The split matters. §1 is scaffolding and should be deleted when it stops being
needed. §2 and §3 are the reason this file exists.

---

## 1. Queryable configuration

`measured` — from the league creation screens, and cross-checked against the
`leagues` row where noted. Column names given so the diff is mechanical.

### Roster and service time

| Rule | Value | Column |
|---|---|---|
| Active roster | 26 | `rules_active_roster_limit` |
| Secondary (40-man) | 40 | `rules_secondary_roster_limit` |
| Expanded (September) | 28 | `rules_expanded_roster_limit` |
| Days for one service year | 172 | `rules_min_service_days` |
| Service years to free agency | **6** | `rules_fa_minimum_years` |
| Service years to arbitration | **3** | `rules_salary_arbitration_minimum_years` |
| Minor-league free agency | 6 years | `rules_minor_league_fa_minimum_years` |
| Waiver period | 3 days | `rules_waiver_period_length` |
| DFA period | 7 days | `rules_dfa_period_length` |
| Minor-league option years | enabled | `rules_minor_league_options` |
| Rule 5 draft | enabled | `rules_rule_5` |

### Money

| Rule | Value | Column |
|---|---|---|
| Hard salary cap | **none** | `rules_salary_cap` = 0 |
| Luxury tax rate | 20% | `rules_luxury_tax` |
| Soft cap | 140% of average payroll | `rules_luxury_sharing_cap` |
| Revenue sharing | 48% of income | `rules_revenue_sharing_tax` |
| National media | **fixed, identical for all clubs** | `rules_national_media_contract_fixed` |
| Owner controls budget | **yes — locked on** | `rules_owner_decides_budget` |
| FA compensation | QO / later-round picks (2017 CBA) | `rules_fa_compensation` |

### Trading and acquisition

| Rule | Value | Column |
|---|---|---|
| Draft pick trading | **disabled** | `rules_draft_pick_trading` |
| Trade deadline | 31 July | `trade_deadline_date` |
| Amateur draft rounds | 20 | `rules_amateur_draft_rounds` |
| Games per team | 162 | `rules_schedule_games_per_team` |
| Balanced schedule | **no** — division-weighted | `rules_schedule_balanced` |
| Interleague | enabled | `rules_schedule_inter_league` |

`measured` — year one runs on a real MLB schedule file
(`schedule_file_1 = major_league_ml_c_2024.lsdl`), so the balanced/unbalanced
setting governs *generated* schedules in later seasons, not 2024.

### Playoffs

`measured` — from `league_playoffs`, matching real 2024 MLB exactly:

| Round | Name | Format |
|---|---|---|
| 0 | Wildcard Series | best-of-3 |
| 1 | Division Series | best-of-5 |
| 2 | League Championship Series | best-of-7 |
| 3 | World Series | best-of-7 |

`max_round` 4, `num_wild_cards` 3. Three division winners plus three wild cards
per league — **12 of 30 clubs qualify**, and the top two seeds bye past the
wildcard round.

---

## 2. Unqueryable configuration — this document is the only copy

`measured` from the creation screens. **Not present on the `leagues` row**, so
there is nothing to diff against and nothing that supersedes this.

| Rule | Value | Why it matters |
|---|---|---|
| **Super 2 deadline** | top 22% | Service-time manipulation is live: holding a prospect past the cutoff saves an arbitration year |
| **Draft lottery** | 18 teams eligible, top 6 picks drawn, revealed at Winter Meetings | Tanking has a bad expected return — see §3 |
| Lottery odds | 16.50% each for the worst three; 13.25 / 10.00 / 7.50 / 5.50 / 3.90 / 2.70 / 1.80 … 0.23% at 18th | The worst record in baseball buys a 1-in-6 shot, not a pick |
| **10/5 rule** | enabled | 10 years' service with 5 at the current club = full no-trade rights |
| **Trading injured players** | **enabled** — deliberate deviation, see §5 | Buying low on health is available |
| Waiver trades after deadline | disabled | 31 July is a hard wall |
| Trading recently drafted players | 1-year hold | |
| Contract years maximum | 15 | Mega-deals are structurable |
| Contract opt-outs | allowed | Long deals carry opt-out risk |
| Qualifying offers | max 1 per career | |
| Posting system | disabled | No NPB/KBO posting channel |
| **Draft pool reveal** | 90 days pre-draft — **12 April** | The annual scouting crunch, mid-season |
| Draft signing | advanced negotiation on, $4.13M slot baseline, 5 rounds negotiable | Draft strategy includes bonus allocation |
| Cash maximum in trades | $16,000,000 | Caps salary-dump trades |
| Minimum batters faced | 3 | No specialist relievers |
| Designated hitter | universal (both leagues) | |
| Minimum salary | $720,000 | |
| Minor-league assignment refusal | veterans retain the right | Optioning is not unilateral |
| Minor-league depth charts | built on **potential** ratings | The farm plays prospects, not filler |
| Post-season eligibility | 40-man roster | September decisions have October consequences |

`inferred` — "not in the export" is not the same as "not in the save." The
parser reads `leagues.dat` directly and may recover some of these. Re-check when
it can.

---

## 3. What this implies

Not in the save, in any form. This is the durable half.

### This league is built for sustained contention

Three rules point the same direction:

- Draft picks **cannot be traded**
- The draft is a **lottery** — the worst record in baseball buys a 1-in-6 shot
- **12 of 30 clubs** make the playoffs

Every one of them penalizes tearing down. You cannot buy picks, you cannot
reliably lose your way into them, and a roughly .500 team stays in the postseason
conversation all summer. Add an owner who judges results annually
([ADR 0015](decisions/0015-gm-is-employed-not-appointed.md)) and the conclusion is
unambiguous: **boom-bust rebuild cycles are the wrong strategy here. Perpetual
competitiveness is the right one.**

Two consequences that bite in July:

- **Selling is rare and expensive to justify.** Within five games of a wild card,
  a teardown is an argument with the owner you will probably lose — and losing it
  costs the job, not just the argument.
- **The bye is worth more than the standings suggest.** The top two seeds skip a
  best-of-3, which is close to a coin flip regardless of how good you are. Moving
  from the third seed to the second buys far more October than the same one game
  moving fourth to third. A model that treats wins as fungible gets this wrong.

And once in, it is a lottery: a best-of-3 opener can end a 100-win season in
48 hours. *Get in and take your chances* is legitimate here — arguably optimal.

### Scouting and development are the talent engine

**Draft picks cannot be traded, and the draft is a lottery.** Together those
close both shortcuts: you cannot buy picks, and you cannot reliably lose your way
to them either — 18 teams in the draw with the worst three capped at 16.50% means
bottoming out buys a coin flip, not a franchise player.

What remains is scouting, development, and trading surplus for prospects. That
puts the whole weight of the operation on the quality of our information, which
is exactly the bet [ADR 0014](decisions/0014-staff-is-the-information-channel.md)
describes.

### The scouting budget is priced in players

Scouting comes out of the same budget as payroll, and the owner sets that budget.
League baselines: $9M scouting, $13.5M player development, ~$158M average payroll,
$8M for an "average quality" player.

**Our scouting department costs roughly two average major leaguers. Doubling it
costs two more.** That is ADR 0014's central tradeoff, denominated in players
rather than adjectives.

`measured`, from a probe save rather than ours — league average scouting spend is
5.6% of budget, and the spread is enormous: Oakland at 13.8%, the Yankees at 1.9%.
The club that cannot buy players buys knowledge instead. Where Boston sits on that
curve is a live decision, not a default.

### The owner is the wall, not the tax

The soft cap is **140% of the league's average payroll** — a moving number, not a
fixed one, so the threshold rises as payrolls inflate. At the starting average of
$158.1M that is roughly $221M, taxed at a flat 20%: going $20M over costs $4M.
Real MLB escalates past 50% with surcharges; this does not.

**The luxury tax will rarely be what stops us. The owner's budget will.** Any plan
built on "we'll just eat the tax" is answering the wrong constraint.

### Market matters, but the floor is real

Revenue spreads 4.42x across the league and budget 3.35x. But national media money
is **identical for every club**, and for a small-market team that fixed share is
the majority of its media revenue. With 48% revenue sharing on top, a poor job is
a harder job rather than an unwinnable one.

That matters under [ADR 0015](decisions/0015-gm-is-employed-not-appointed.md):
it is most of what makes a career across employers a fair test rather than a
lottery on which owner hires you.

### Roster construction, specifically

- **Three-batter minimum** means every reliever must survive both handedness
  splits. Bullpen evaluation is a two-dimensional query against the vsL/vsR
  columns in `players_scouted_ratings`, not a single number.
- **Option years plus veterans' right to refuse assignment** makes roster
  flexibility finite and expiring. A player out of options cannot be quietly
  stashed.
- **Rule 5 plus a 40-man limit** forces a real protection decision every December.

### The annual collision

Draft pool reveals **12 April**; draft is **11 July**; deadline is **31 July**.
Roughly thirteen in-season weeks where amateur scouting competes directly with
the pennant race, ending with the two biggest decisions of the year three weeks
apart. This recurs every season and deserves a standing order rather than being
re-litigated each spring.

### Year one is inherited

Hired **7 March**. The league's first game is **20 March** — but that is the
Seoul Series, two clubs only. **Boston opens 28 March**, so there are three weeks
of spring training, not two days. No inaugural fantasy draft.

That is real runway for an organizational assessment before anything counts:
final cuts, the opening-day 26, a first scouted read on the roster and the top of
the farm, and an honest judgment about the competitive window. It is nowhere near
enough to change what this team *is*. The first real construction opportunity is
the July deadline, then the 2024–25 winter.

`measured` — regular season ends **29 September**; the All-Star break falls in
mid-July, three days after the amateur draft and seventeen before the deadline.

**2024 is a diagnostic season, not a built one** — though the owner is under no
obligation to see it that way, which is itself worth knowing.

Boston plays in the **AL East** on a division-weighted schedule.

---

## 4. The rules evolve — and the flags are not readable

`measured` — automatic league evolution is **enabled**, covering: active roster
size, secondary roster size, IL length, the designated hitter rule, **free-agency
minimum service**, offensive and pitching environment, expansion, relocation, and
team nickname changes.

`measured` — **the evolution flags themselves are not columns on the `leagues`
row.** We cannot verify from data that evolution is on.

`inferred` — but we do not need to. Everything that would actually hurt us is a
column: if free agency moves from six years to five, `rules_fa_minimum_years`
changes from 6 to 5 and a diff catches it. **Detection beats
configuration-reading here**, and it does not depend on the game notifying anyone.

> **The most dangerous one is FA minimum service.** It reprices every prospect in
> the system at once, and under §3 the farm is our primary talent engine. A plan
> built on six years of control is silently wrong the day it becomes five.

This is the first genuine candidate for a standing order: **every offseason, diff
the live `leagues` row against this snapshot; any change escalates.** Reading the
warehouse is free ([ADR 0013](decisions/0013-action-economy.md)), so the check
costs nothing to run.

---

## 5. Deliberate deviations from default

Everything else is an OOTP default, kept on purpose.

| Setting | Default | Ours | Why |
|---|---|---|---|
| Allow trading of injured (>7 days) players | disabled | **enabled** | MLB permits trading players on the IL, so the default is the less realistic option. It also restores *buying low on health* — a decision with no input but our own medical staff's read, since [ADR 0012](decisions/0012-scouted-ratings-only.md) withholds injury proneness. Exactly the class of decision this project exists to make interesting |

---

## 6. Pending

- **Cross-verification against *our* league.** Everything in §1 is `measured`
  from the creation screens and from a **probe save**, not from `OOTP-AI.lg`
  itself — the managed league is Challenge Mode, so there is no export to read.
  Until the parser can open `leagues.dat`, every value here is believed rather
  than confirmed for our league. That diff is the first real job for the parser.
- **Owner goals.** Not visible until the club exists. Read them carefully: if they
  are purely win-now, the experiment measures survival more than
  organization-building, and that needs noticing at the time rather than in
  season three ([ADR 0015](decisions/0015-gm-is-employed-not-appointed.md)).
