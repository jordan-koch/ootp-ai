> **Status:** intake · created 2026-08-16 · open · next: scope

# Feature Request — The GM's inbox: read the mail the club actually receives

## Problem / Motivation

**The club is being written to and nobody is reading it.**

`OOTP-AI.lg/messages/` holds eight plain-text letters, 8,056 bytes, addressed to the
general manager. `message1.txt` is the letter that hired it — *"Boston to GM Candidate
Merrick: You're Hired"* — and the GM has never seen it. Nothing in this repo reads a byte
of that directory, and the Phase 4 snapshot layer copies three files that do not include
it.

That is a gap with a specific shape.
[ADR 0015](../../../docs/decisions/0015-gm-is-employed-not-appointed.md) makes the GM
**employed rather than appointed** — someone other than the GM decides whether it
succeeded — and mail is the channel through which an employer says so. Today the GM can
read its own charter, its standing orders and the owner's goals, all of which *we* wrote.
It cannot read anything the club's own world has said to it. If ownership were losing
patience, the front office would have no way to find out.

There is a second, smaller motivation that turns out to matter more than it looks. The
letters are **not just prose**. Every entity in them carries an inline reference:

```
<Boston:team#4>   <Justin Connell:player#25004>   <Claude Merrick:manager#1>
```

`measured` 2026-08-16 — the ground-truth export gives Boston `team_id` **4**, and the
token reads `team#4`. That is strong evidence the mail uses the **same id space** as
`teams.dat` and `players.dat`, which makes it joinable to the warehouse rather than a
parallel pile of text. It also means the mail already knows the GM's own in-game
identity: `manager#1`.

## Desired Outcome

The GM reads its inbox the way it reads its charter — as part of a period's free
material, not as a purchase.

**The observable signal:** a cold `gm` spawn has the current inbox in its context, and
can cite a specific message in a `gm/decisions/` record. The stronger signal, later: the
GM changes a decision because of something ownership said.

Secondarily, the mail's entity references resolve to real players and clubs rather than
staying as raw tokens, so a letter about a prospect connects to the prospect.

## Rough Ideas (non-binding)

- A `parser/messages.py` reading `messages.dat` as the index (it carries the standard
  save header — `measured`: version 25, the four constants, self-declared filename, sim
  date `(7, 3, 2024)`) and the eight `messages/message*.txt` files as the bodies.
- Widen `SNAPSHOT_FILES` in `src/ootp_ai/snapshot.py` so mail is snapshotted with
  everything else and a period's inbox is retained rather than read live.
- Render to the git-ignored output root alongside the roster and standings reports, so
  the GM reads a file rather than being handed raw save contents.
- Resolve the `<Name:type#id>` tokens against the warehouse once the `teams.dat` and
  `players.dat` walkers land.

Scoping is free to reject all of this.

## Scope Signals

- **In:** `messages/message*.txt`, `messages.dat`, the `<Name:type#id>` token format,
  widening the snapshot set to retain mail, and getting the result in front of the GM.
- **Explicitly out:** the newspaper (`temp/text_data.sqlite3`), `news/html/` and
  `news/txt/` — all three are separate bodies of content with their own price under
  [ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md). The subscription
  dial, which is its own request (`requests/feature-requests/news-subscription-dial/`).
  Anything that writes to the game. Any advisor built over the mail.
- **Not now / later:** resolving tokens against warehouse rows — that needs the
  `teams.dat`, `players.dat` and `names.dat` walkers, which are `first-sight` Phases 5–7.
  Landing the token format and leaving the ids unresolved is a complete first slice.
  Also later: mail history across many sim dates, which has nothing to trend yet.

## Affected Area & Pointers

Parser and snapshot, plus the GM's reading path. It is a small vertical slice that
touches one new file and widens one existing constant.

A cold scoping agent reads, in order:

1. [`docs/decisions/0019-reading-costs-an-action.md`](../../../docs/decisions/0019-reading-costs-an-action.md)
   — prices every inbound channel, and the ruling below rests on it
2. [`docs/game-mechanics.md`](../../../docs/game-mechanics.md) § *Mail, and the volume
   dial nobody has turned* — what the game actually does, `measured` from in-game
3. [`src/ootp_ai/snapshot.py`](../../../src/ootp_ai/snapshot.py) — `SNAPSHOT_FILES` is
   the constant this widens, and its comment argues against widening casually
4. [`src/ootp_ai/parser/saved_games.py`](../../../src/ootp_ai/parser/saved_games.py) —
   the closest existing walker, and the model for reading a small index file
5. [`FRONT_OFFICE.md`](../../../FRONT_OFFICE.md) §*The action economy* and §*What you are
   allowed to see* — where the GM's free reading is defined
6. [`gm/ledger.jsonl`](../../../gm/ledger.jsonl) — `seq` 1 is the precedent the pricing
   ruling below was decided from

## Data Contracts

Open, for scoping to settle:

- **Grain.** One row per message per snapshot? Messages appear to persist across sim
  dates, so a naive per-snapshot grain re-lands the same eight letters every week.
- **Keys.** There is no obvious message id yet. `messages.dat`'s body is unclassified;
  whether it carries a stable identifier is unknown, and a key derived from the filename
  (`message3.txt`) is a position, not an identity — it will be wrong the moment the
  folder rotates.
- **Coverage.** Eight messages at eleven days old, at the game's **default** subscription
  setting. This is the floor of the dial, not a steady state.
- **Update semantics.** Unknown, and load-bearing — see Open Question 1.
- **Extraction cost.** Trivial. 8,056 bytes of text plus a 1,129-byte index.

## Constraints / Non-negotiables

- **Reading personal mail is free** — operator ruling, 2026-08-16, decided from
  `gm/ledger.jsonl` `seq` 1: *"any owner-initiated dialogue that presents complete terms"*
  is free. Mail arrives unbidden and complete. **This does not extend to the news feed**,
  which [ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md) prices at an
  action per read — and see Open Question 3, where the boundary is genuinely unclear.
- **Widening the snapshot set is tier 2 under
  [ADR 0018](../../../docs/decisions/0018-retention-is-infrastructure.md)** — *"widen what
  the parser reads"* is a feature request **and**, if the GM asks for it, an action. This
  request is that request; the action is the umpires' call.
- **No report may be sourced from the news feed**
  ([ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md)). The test is
  whether staff could build it with the feed switched off. Mail is not the feed, but a
  report *over* mail needs the test applied honestly rather than assumed to pass.
- **No OOTP data in git** ([ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md)).
  The letters are Out of the Park Developments' content. They render to the ignored output
  root, and no message text may reach a tracked file — including a test fixture.
- **The game is read-only** ([ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md)).
  Mail may not be marked read, deleted, or replied to.
- **Paths resolve from `.env`**; tests pass with no game installed.
- **No network access for anything this builds.** The mail names real players in a
  diverged universe; an agent that can look up how their careers actually went holds the
  answer key to a different world.

## Open Questions for Scoping

1. **Does `messages/` accumulate or rotate?** Eight files at eleven days old. If OOTP caps
   the folder and drops the oldest, **mail is being lost right now**, and
   [ADR 0018](../../../docs/decisions/0018-retention-is-infrastructure.md)'s
   irreversibility argument applies directly — a letter not captured can never be
   captured. That would change this from a nice slice to a time-sensitive one. `unconfirmed`.
2. **What does `messages.dat`'s body encode?** It carries the standard header and then
   small integers — plausibly per-message type, date and read state, `inferred` from one
   file and untested. Without a stable id it is unclear what keys a message.
3. **The class boundary is genuinely muddy, and it is the sharpest question here.**
   `message1.txt` is the owner hiring the GM. `message5.txt` is the **BNN Top 100
   Prospects list** — a ranked, league-wide scouting product that nobody would call
   owner-initiated dialogue. They sit in the same folder and arrive at the same default
   setting. The free ruling is clean for the first and arguable for the second, and the
   files carry no class marker, so *something* has to decide. Note the incentive: a
   free-to-read channel that happens to deliver a ranked prospect list is the cheapest
   scouting the club will ever get, and that is exactly the kind of accident this project
   should not benefit from silently.
4. **Do the entity tokens really share the warehouse's id space?** `team#4` matching
   Boston's `team_id` 4 is one corroborated instance. `player#25004` and `manager#1` are
   unchecked, and `manager` may be an id space this project has never read.
5. **Does the token format survive a name containing `<`, `>` or `:`?** The delimiters are
   unescaped as far as anyone has looked. A parser that assumes they are safe is one
   apostrophe away from a wrong join.

## Stage plan

**Full pipeline.** Two triggers fire, either alone sufficient.

**Trigger 1** — Open Questions is non-empty, and Question 1 is potentially time-sensitive
rather than merely unresolved.

**Trigger 3** — it widens `SNAPSHOT_FILES`, which is governed by
[ADR 0018](../../../docs/decisions/0018-retention-is-infrastructure.md)'s tier-2 rule and
whose own source comment argues that a snapshot is *"three named files, never a directory
sweep."* Widening it is exactly the *"we're already reading the directory, so this file is
free"* shape that ADR calls out as needing refusal in review. It also lands a new grain
and a new key with no obvious identifier, and Question 3 puts pressure on
[ADR 0019](../../../docs/decisions/0019-reading-costs-an-action.md) on the same day it
was accepted — which is a reason to scope it properly, not a reason to assume the ADR
already covered it.
