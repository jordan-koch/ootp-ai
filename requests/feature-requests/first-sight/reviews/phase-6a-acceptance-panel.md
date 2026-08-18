# Acceptance panel — first-sight Phase 6a (`players.dat` walk)

Run 2026-08-18 against the uncommitted Phase 6a tree, on branch
`first-sight-phase-6-players-and-rosters` at HEAD `044c145`.

## Panel health — no degradation

| Metric | Value |
|---|---|
| `reviewers_ok` / total | 6 / 6 |
| `verifiers_ok` / total | 5 / 5 |
| `findings_unverified` | **0** |
| `meta_ok` | 1 |
| `degraded_lenses` | *(empty)* |
| `findings_blocker_major` raw → deduped | 21 → 20 |
| blockers / majors | **0** / 11 |
| criteria met / unmet / unverifiable | 11 / 20 / 3 |
| verdict | `fix` |

Roster: `acceptance`, `fidelity`, `correctness`, `edgecases`, `parser`, `warehouse`.
1.9M subagent tokens, 442 tool calls, ~43 min wall clock.

**The unmet-criteria count is expected and is not a Phase 6a result.** The panel scored
all 34 criteria of the whole 14-phase request; Phases 6b–13 have not been attempted. The
criteria that matter here are the ones this phase claimed.

## What the panel confirmed independently

Every reviewer ran the gates rather than reading them, and three re-derived the walk
themselves. Worth recording because it is stronger evidence than the diff:

- **The framing drops nothing.** Three lenses independently re-scanned all three
  `players.dat` buffers for pad-run candidates *with the ascending-id constraint removed*
  and compared against the framed set: managed 22,046 framed vs 22,045 independent
  candidates, both test saves 18,077 vs 18,076 — the difference being record one, which
  has no pad in front of it — and **zero candidates the walk failed to frame**.
- **The head really is fixed.** The export has 349 rows with `city_of_birth_id = 0`,
  2,548 with `uniform_number = 0` and 6,368 with `experience = 0`, and the parser still
  matches all 18,072 exactly — so drop-zero demonstrably does not apply inside the head.
- **The alignment window is used exactly where it should be**: `after` for all but
  92/74/74 records, and those are precisely the ids whose low byte is zero.
- **The managed save's 22,046 records are proportionate**, not over-framed: that league
  carries 337 teams against 259, i.e. 65–70 players per club in both.
- ADR 0001 holds both ways: `read_players(data: bytes)` opens no handle, and the static
  WRITERS allowlist in `test_read_only.py` scans the new module and stays green.

## Three panel claims the meta-audit REFUTED

Recorded because a synthesis that launders a wrong finding forward is worse than one that
misses a right one.

1. **"Plan step 6's `test_sequential_walk.py` player-shaped extension was skipped"** —
   several lenses said this. It is wrong. `tests/fixtures/synthetic.py`'s `make_record`
   already builds exactly that record and `test_sequential_walk.py` asserts
   `historical_id` reads identically across `contract_years` 0/1/2/5/10/40, with a
   negative control proving a fixed-offset reader fails. Pre-existing Phase 3 work, which
   is why the file is untouched. The verifier inferred absence from `git diff --stat`
   without opening the file.
2. **"`players.py` is the first module to add a constant addend to a record-relative
   peek"** — no. Committed `world.py` and `teams.py` already do it, so the AC3 guard gap
   is **pre-existing and enlarged, not introduced**.
3. **"Every offline player test would pass for a fixed-stride reimplementation"** — it
   would fail the non-ascending-id test and the impostor test. The *underlying* coverage
   gap was real and is fixed below.

## Findings acted on

| # | Finding | Outcome |
|---|---|---|
| F1 | **`historical_id` vanished.** Named by plan step 1, and AC8's only join key — the sole Tier-A validation of the names join on the league we manage. Landed nowhere, listed in neither the 6a-landed nor the 6b-deferred list, and absent from `field_map.toml`'s `[[withheld]]` block, which exists precisely to stop that. | **Fixed.** Added to the plan's 6b list with AC8's dependency stated, and to `[[withheld]]` with its measured shape (u32-length-prefixed ASCII, twice per record, ~60–80 bytes in — after the drop-zero region, hence out of reach for the same reason `team_id` is). |
| F2 | **A `measured` label the bytes falsify.** `content_digest`'s note claimed the two test saves "share one" digest. | **Fixed, and the panel was right.** Re-measured in full: all three digests are **distinct**; the two test saves agree on exactly the first **32** of 64 hex characters. My claim came from eyeballing the first twelve characters of a debug print. Corrected in `players.py` and `field_map.toml`, with the 32/32 split recorded as `unconfirmed`. |
| F3 | **The residual bound could fail on correct data and pass on broken data.** It compared the last record's leftover against the *mean* record; measured residual 1,045 vs a 1,543 mean, while records run to 9,229 bytes. | **Fixed.** Now bounded as a fraction of the file (`< 0.1%`; observed ~0.004%), which cannot go red on a long final record and still catches a walk that quit halfway. |
| F4 | **A tautological test.** Ascending/unique ids are guaranteed by the framing predicate, so asserting them re-stated the implementation. | **Fixed.** Kept and relabelled honestly as a *structural* guard against a refactor loosening the predicate, and a genuinely independent test added — the pad-run re-scan with the ascending constraint removed, which is the only check that would catch a dropped record on the managed save where no export exists. |
| F5 | **Offline coverage never built a variable-length record** — `make_players_file` applied one body to every record, so a fixed-stride reimplementation would pass every test CI runs. | **Fixed.** The builder takes per-record `bodies`; two tests added — four records spanning 7 to 4,001 bytes, and a zero-filled body that merges with the following pad run. |
| F6 | **A false docstring.** `test_parse_real_save.py` promised Phase 6's player clauses would land in it; they landed in `test_parse_players.py`. | **Fixed.** The docstring now says where each clause actually went and why. |
| F7 | **The split note sat at the head of Phase 6 while the phase's own Acceptance block still described the un-split phase**, so Phase 6 read as failed. | **Fixed.** Acceptance split into 6a (met) and 6b (outstanding). |

## Carried, not fixed

- **AC3's guard gap.** `tests/test_no_fixed_offsets.py` bans `.seek(<literal>)` and
  `unpack_from(..., <literal>)` but cannot see `data[position + CONSTANT]`. The
  meta-audit established this is pre-existing (`world.py`, `teams.py`) rather than
  introduced here, so widening the guard is a change to a committed guard affecting three
  modules — **its own request, not a quiet edit inside this phase.**
- **`field_map.toml` is not column-shaped and has no consumers or tests.** True, and by
  design: `contracts/loader.py` and `policy.py` are Phase 8 and Phase 10. The warehouse
  lens is right that it is cheapest to reshape before Phase 8 writes a loader against it;
  that belongs to Phase 8's "complete `tables.toml` and `field_map.toml`" step.
- **AC11's manifest-diff window.** `ingest_save` never calls `read_players`, so the
  largest read in the project happens outside the window AC11 measures. Phase 8 wires the
  loader; noted so it is not forgotten.
