# 0006 — Public repository, local data

**Status:** Accepted
**Date:** 2026-08-15

## Context

Both sibling repos (`nba-analysis`, `nba2k-rpg`) are public, largely because
GitHub Free requires a public repo for branch protection. The same trade is
available here.

This project differs from both in one respect that matters: it reads a commercial
game's shipped database and a user's saved games. `players.csv`, `names.xml`,
`world_default.xml`, and every `.dat` file are **Out of the Park Developments'
intellectual property**. Real-player biographical data in them originates with
third parties.

## Decision

**The repository is public. The game's data never enters it.**

Tracked: the code that reads OOTP's files, the schema knowledge we derived (field
maps, offsets, format documentation), our own derived datasets, docs, and tests.

Never tracked: `players.csv`, the XML reference files, any `.dat`, any `.lg`
directory, any save snapshot, any export output. `.gitignore` blocks these by
name and by extension.

All machine-specific locations resolve from environment variables via
`.env.example`. `tests/test_no_leaks.py` fails the build on absolute paths, home
directories, and email addresses in tracked files.

## Consequences

**Buys:**

- Branch protection on GitHub Free, so `main` is protected and CI is enforced.
- Consistency with the sibling repos — one set of habits across all three.
- The work is shareable; the data is not, which is the correct split.

**Costs:**

- **Nothing machine-specific may ever be written down in a tracked file.** Every
  path goes through `.env`, including in docs and examples. This is a permanent
  tax on every file, and the leak guard exists because the tax gets forgotten.
- Test fixtures cannot be real save files. Any committed byte sample must be
  small, derived, and defensible as our own observation rather than a copy of
  OOTP's data.
- Setup for anyone else requires them to own OOTP 25 and configure `.env`. The
  repo is not runnable from a clone alone, and the README must say so plainly.

**Forecloses:**

- Committing a sample save for reproducibility, which is genuinely inconvenient
  when debugging a parser regression. Snapshots live in gitignored `var/`, so a
  bug report references a snapshot the reader does not have.

## Notes

The distinction to hold onto: **derived schema knowledge is ours; the data is
theirs.** "The ratings block is 18 contiguous u16 values ordered vR, vL,
potential" is an observation we made and may publish. A copy of `players.csv`
is not, however convenient it would be as a fixture.
