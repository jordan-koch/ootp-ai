# 0003 — The managed league runs in Challenge Mode

**Status:** Accepted
**Date:** 2026-08-15

## Context

OOTP's Challenge Mode is an irreversible per-save flag. Once enabled and saved,
the database is protected: commissioner mode is off, the player editor is limited
to basic options, auto-play beyond a week is blocked during the regular season,
save-scumming is prevented by integrity hashes, and — as this project discovered
— the database export menu is hidden.

The alternative is a standard save, which keeps every tool available.

The project's claim is that an AI front office can be *competitive*. That claim is
only meaningful if the league cannot be edited underneath it.

## Decision

**The managed league runs in Challenge Mode.** Its restrictions are accepted as
permanent design constraints rather than obstacles to work around.

Disposable standard-mode saves are used freely for parser development and ground
truth. They are never the managed league.

## Consequences

**Buys:**

- The competitive claim is honest. Nothing can be edited, reloaded, or undone, so
  a good season is evidence and a bad one is too.
- Integrity hashing makes accidental corruption loud instead of silent.
- It is the more enjoyable way to play, which matters for a project that has to
  stay interesting long enough to finish a season.

**Costs:**

- **No database export, ever, in the managed league**
  ([ADR 0002](0002-parse-binaries-not-export.md)). The parser is not merely
  preferred, it is mandatory.
- No commissioner tools: we cannot inspect the league through the editor to
  resolve an ambiguity, and cannot correct a mistake caused by our own bad advice.
- Auto-play restrictions constrain how fast a season can be simulated, which
  lengthens the feedback loop for evaluating the front office.
- Save corruption is unrecoverable. Snapshots are the only backstop, which makes
  the snapshot discipline load-bearing rather than convenient.

**Forecloses:**

- Any workflow requiring commissioner mode.
- Editing league state to construct a test fixture. Fixtures come from disposable
  standard saves or from committed byte samples.

## Notes

Challenge Mode's restrictions were discovered empirically, not from
documentation. Anything else it gates is `unconfirmed` — treat a newly discovered
restriction as expected rather than as a bug.
