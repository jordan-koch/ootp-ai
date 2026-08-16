# Test fixtures

Committed inputs so the suite runs offline, with no OOTP install and no save file.
CI has neither and must never have either.

## The rule that governs everything here

**A fixture may contain our own derived observations. It may never contain OOTP's
shipped data.**

That line is [ADR 0006](../../docs/decisions/0006-public-repo-local-data.md), and it
is sharper than it first looks, because the convenient fixture is always the banned
one:

| Allowed | Not allowed |
|---|---|
| A field-offset map we computed | A copy of `players.csv`, trimmed or not |
| A hand-written byte string exercising a length-prefix edge case | A slice of a real `players.dat` |
| Expected values transcribed for a handful of players, cited to their source | A dump of `names.xml` |
| A synthetic record we constructed to have a 1-year contract | A real save's team block |

The distinction is authorship, not size. "The ratings block is 18 contiguous `u16`
values ordered vR, vL, potential" is an observation we made and may publish. Ten
bytes lifted out of `players.dat` are Out of the Park Developments', however few.

`tests/test_no_leaks.py::test_game_data_is_not_tracked` catches the obvious cases by
filename and extension. It cannot catch a renamed slice of a real save — that one is
on you.

## What belongs here

- **Synthetic binary records** built by hand to exercise the parser: a length-prefixed
  string at a buffer boundary, a record with an empty year-keyed block, a 1-year
  contract next to a 10-year one, a header carrying an unrecognized version byte.
- **Expected-value tables** transcribed from ground truth, each row citing where it
  came from so a future reader can re-check it.

## What does not

- Anything requiring a local install to produce. That is a `gamedata`-marked test,
  excluded from CI.
- Bulk data. Fixtures are small enough to read and reason about; if one is not, the
  test is probably asserting too much at once.

## Why synthetic beats real here

A real save's day-0 state is the *least* informative test input available: every
variable-length region is at its minimum, so a parser that seeks to a fixed offset
passes cleanly and fails later in production. Constructing records by hand is how the
awkward shapes — the empty block, the long contract, the missing external ID — get
exercised at all.
