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
