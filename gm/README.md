# GM memory

**This directory is TRACKED in git.** Everywhere else in this repo local state is disposable
and gitignored — `var/` holds only things that rebuild from the save. This is the one
deliberate inversion, and the reason is
[ADR 0011](../docs/decisions/0011-gm-memory-is-tracked.md):

> The save records what happened. It never records *why* the GM chose it.

You cannot re-derive "we passed on the extension because we projected the comp market to
soften" from `players.dat`. That reasoning exists in exactly one place. Losing this directory
loses the GM.

**Do not add a `.gitignore` rule that shadows this carve-out.**
`tests/test_repo_structure.py` fails if one appears, and it is not being pedantic.

## The placement rule

> **Can this be rebuilt from the save?** Yes → `var/`. No → here.

A projection is regenerable. The decision to trust it over the scouting report is not.

## Layout

```
gm/
├── README.md            this file — the contract
├── charter.md           standing goals, competitive window, org philosophy
├── standing-orders.md   active policies staff apply for free until changed
├── staff.md             the roster, and how each has performed per action spent
├── ledger.jsonl         append-only: every action proposed, adjudicated, and spent
└── decisions/           one file per significant decision — what, why, what was expected
```

## Scope — career vs club

The GM is an **employee**, and the experiment follows the *career* rather than one
club ([ADR 0015](../docs/decisions/0015-gm-is-employed-not-appointed.md)). A firing
does not end it. So each file here has a scope, and it is recorded now — before the
split it describes — because the moment of an actual firing is the worst possible
time to argue about what survives.

| File | Scope | Why |
|---|---|---|
| `ledger.jsonl` | **career** | Action doctrine is about what costs an action, not about an employer |
| `charter.md` | club | Competitive window and philosophy belong to one organization |
| `standing-orders.md` | club | Policies a specific staff applies to a specific roster |
| `staff.md` | club | The people the GM employed there |
| `decisions/` | club, with career-scoped lessons | The call was club-specific; what it taught is not |

**The directory does not split until a second club exists.** One employer, one flat
layout — don't build the tenure structure speculatively.

## `ledger.jsonl` — the action ledger

Append-only, one JSON object per line, newest last. It records **every adjudication**,
whether the ruling was *cost* or *free* — a free ruling is precedent too, and dropping those
would leave the doctrine half-blind.

The file does not exist yet; it appears with the first declared action. `.gitattributes`
already marks it `merge=union` so two branches appending different entries both keep them.

```json
{"seq":1,"sim_date":"2024-03-18","period":"2024-W12","what":"Build draft board, rounds 1-3","staff":"scouting-director","proposed":"cost","reasoning":"New scouting work on players outside existing coverage.","precedent":null,"ruling":"cost","overridden":false,"overturns":null}
```

| Field | Meaning |
|---|---|
| `seq` | Monotonic. What `precedent` and `overturns` cite. |
| `sim_date` | In-game date. **Not** wall-clock — that would break replay. |
| `period` | The budget period this spends from. |
| `what` | The work, concretely. "Scouting" is not an entry; "scout the Cardinals' AA arms" is. |
| `staff` | Which advisor does the work, or `gm` for the GM's own. |
| `proposed` | The GM's proposed ruling: `cost` or `free`. |
| `reasoning` | **Why** — the part that generalizes. A verdict alone cannot extend to an unseen case. |
| `precedent` | `seq` of the closest prior ruling, or `null` if genuinely first-of-kind. |
| `ruling` | What the operator actually ruled. |
| `overridden` | `true` when `ruling` differs from `proposed`. These are the valuable rows. |
| `overturns` | `seq` of a precedent deliberately ruled against, with the reason in `reasoning`. |

### What a period is

[ADR 0013](../docs/decisions/0013-action-economy.md) budgets **6 actions per
in-season week and 10 per offseason week** but does not define the boundary.
Operator ruling, 2026-08-16:

> **The season runs from the day of the first league game — any team — until the
> end of our club's involvement in the playoffs.** Everything else is offseason.

Deliberately asymmetric. The start is league-wide because once games are being
played the market is live whether or not we are playing; the end is club-specific
because once we are eliminated the attention is genuinely free. **Spring training
is offseason**, which is what the first ruling under this rule established.

**The week runs Monday to Sunday.** Actions are granted each Monday and expire
unspent at the end of the period.

**A week that straddles a boundary takes the in-season rate** — if any day in the
Monday–Sunday window falls inside the season, the whole week is in-season. This
errs toward scarcity, deliberately.

Worked example, 2024 (league starts Thu 7 Mar; league opener Wed 20 Mar; Boston
opens Thu 28 Mar):

| Period | Rate | Why |
|---|---|---|
| Mar 7–10 | 10 | Partial opening week, granted in full — one-off, **no precedent value** |
| Mar 11–17 | 10 | Offseason |
| Mar 18–24 | **6** | Contains the 20th, though Boston is idle until the 28th |
| Mar 25–31 | 6 | In-season |

Twenty offseason actions before the season starts.

The asymmetry pays in both directions at the other end. Miss the playoffs and the
week after our last game runs at 10 while the rest of the league plays October.
Reach the World Series and roughly four extra weeks run at 6 instead of 10 —
**about 20 actions of offseason attention is the price of a deep run.**

This is recorded here rather than in `ledger.jsonl` because the ledger's schema
adjudicates *actions* as cost or free, and this rules on a *period*. It is not a
doctrine summary — it defines a term the ledger's `period` field depends on.

### Two rules that make it mean anything

**Declare before doing.** The entry is written *before* the work, not after. A ledger written
afterwards is justification rather than constraint, and the mechanism collapses into theatre
([ADR 0013](../docs/decisions/0013-action-economy.md)).

**Doctrine is a query, never a document.** Do not maintain a summary of "what counts as an
action" — it would drift from the ledger and then nobody could say which was true. To learn
the current doctrine, read the ledger.

## `standing-orders.md`

The policies staff apply for free until changed. Each carries the `seq` of the action that
established it and the sim date, so its age is visible — **a standing order that quietly
stopped being right is this system's most interesting failure mode**, and age is the first
clue.

## `decisions/`

One file per significant decision: what was decided, why, what was expected to happen, and —
added later — what actually did. The gap between the last two is the GM's own performance
record.

Not every action needs one. A decision record is for calls worth revisiting: acquisitions,
extensions, promotions, firings, changes of direction.

## This repo is public

Everything here is world-readable, forever. It is a baseball save, so that is fine — but
nothing operational, personal, or machine-specific belongs in a decision record.
`tests/test_no_leaks.py` covers this directory like every other.
