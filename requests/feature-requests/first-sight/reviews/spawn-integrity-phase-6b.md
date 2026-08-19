# Spawn integrity — Phase 6b's two data-engineer builds

The spawn protocol's pre/post captures (`.claude/agents/README.md` §Spawn protocol),
recorded so the comparison survives outside gitignored `var/`. Branch
`first-sight-phase-6b-rosters-and-identity`; `HEAD` was `d548902` before, between and
after both spawns, with `git stash list` empty throughout.

## Spawn 1 — the `players.dat` identity tail (`handoff-phase-6b-players.md`)

- **Pre:** clean tree, empty `var/tmp/first-sight-6b-pre.patch` by construction, no
  untracked files.
- **Post:** modified `src/ootp_ai/parser/players.py`,
  `src/ootp_ai/contracts/field_map.toml`, `.claude/agents/data-engineer-memory.md`;
  untracked `requests/feature-requests/first-sight/reviews/handoff-phase-6b-players.md`.
  All four inside the declared allowlist; `tests/`, `docs/`, `.github/`, `teams.py`
  untouched. Pre-existing symbols (`_ASSIGNMENT_BITS`, `read_players`) still present.
- Post-capture with spawn 1's work included: `var/tmp/first-sight-6b-pre2.patch`
  (36,639 bytes) — the belt protecting spawn 1's uncommitted work through spawn 2.

## Spawn 2 — `list_id` recovery and `rosters.py` (`handoff-phase-6b-rosters.md`)

- **Pre:** the tree above (spawn 1's work only), captured in `pre2.patch`.
- **Post:** added `src/ootp_ai/parser/rosters.py`; modified `src/ootp_ai/parser/teams.py`
  (span extension only — `read_teams` and every landed field untouched),
  `src/ootp_ai/contracts/field_map.toml`, the memory file; untracked handoff. Spawn 1's
  `players.py` diff byte-identical before and after (same 295/33 stat, symbols intact).
  All writes inside the declared allowlist.

## Game directories

`tests/test_read_only.py` ran green inside each spawn's own verification battery and in
the main thread's post-build gamedata run — zero mtime and zero digest differences across
the OOTP install and saved-games roots, which is this repo's version of the
unrecoverable outcome.
