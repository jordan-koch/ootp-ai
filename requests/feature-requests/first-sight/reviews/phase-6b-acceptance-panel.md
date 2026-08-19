# Acceptance panel — first-sight Phase 6b (identity tail + roster grain)

Run 2026-08-18 against the uncommitted Phase 6b tree, on branch
`first-sight-phase-6b-rosters-and-identity` at HEAD `d548902`.

## Panel health — no degradation

| Metric | Value |
|---|---|
| `reviewers_ok` / total | 6 / 6 |
| `verifiers_ok` / total | 5 / 5 (4 batches + the independent ledger verifier) |
| `findings_unverified` | **0** |
| `meta_ok` | 1 |
| `degraded_lenses` | *(empty)* |
| `findings_blocker_major` raw → deduped | 6 → 6 |
| blockers / majors | **0** / 3 |
| criteria met / unmet / unverifiable | 10 / 15 / 2 |
| verdict | `fix` |

Roster: `acceptance`, `fidelity`, `correctness`, `edgecases`, `parser`, `warehouse`.
1.6M subagent tokens, 278 tool calls, ~26 min wall clock.

**The unmet criteria are Phases 7–12's, not 6b's.** The panel scored the whole request;
every unmet row is owned by a phase that has not started, none silently claimed. Auditor
and verifier ledgers reconciled with zero verdict conflicts.

## What the panel confirmed by execution, not assertion

- Both sessions independently re-ran the full gate: offline suite green, ruff / format /
  mypy clean, gamedata green against all three saves.
- The grain reproduces `ootp_truth_real.team_roster` **exactly** — 15,672 rows, 0
  missing, 0 extra; `unrostered` equals the export's negative-`league_id` set (176).
- Boston resolves to the operator-verified 33 / 26 / 30 / 7 over 96 rows and 34 players
  on `OOTP-AI.lg` specifically; the three league invariants hold on all three saves.
- `historical_id` is export-exact on all 18,072 rows — AC8 unblocked.
- The ADR 0001 read-only proof re-ran green after the deepest walk the project performs;
  both AST fixed-offset guards cover the enlarged tree (`rosters.py` statically confirmed
  in scope, indexing only through the ADR 0020 seam); the leak guard scans the untracked
  handoffs too.
- No finding was refuted. Fidelity's one unresolvable row (could not re-run
  `test_read_only` itself) was closed by both other sessions executing it green.

## Confirmed findings and their dispositions

| # | Severity | Finding | Disposition |
|---|---|---|---|
| CF-1 | major | The unrostered-marker fence tested only `last_organization_id != 0` where docstring, field map and handoff promise the full signature; three probes showed a cross-org traded rostered-inactive player silently losing his list-1 row — the one wrong call the multiset reconciliation cannot catch. Latent today (176/176 match the full signature), live at the first trade | **Fixed pre-commit** (the panel's recommendation): `_PlayerStatus` carries `last_league_id`; the solve requires own-org + league 234 + zero status + one entry, refusing anything else by name. Offline probe tests added (`test_a_blurred_unrostered_marker_is_refused_not_classified`, both blur shapes). Gamedata re-run: 15,672/15,672 holds, all three saves clean |
| CF-2 | major | The plan still asserted "rosters.py cannot be written yet" / "AC8 still cannot be attempted" beside the tree that falsifies both — no completion amendment | **Fixed**: dated `PHASE 6b LANDED` amendment appended per the plan's convention, superseding both sentences; the `6b (outstanding)` block annotated closed |
| CF-3 | major | `position`/`role` correctly refused, but scope Goal 1 / Phase 10 step 2 still promise a position column with no data path and no recorded disposition | **Disposed by the operator (GD-2)**: Phase 10 gated on one bounded decode attempt against the `teams.dat` depth-chart region; on failure the report ships without the column, the catalog names the gap, a follow-up request is filed. Recorded in the amendment |
| CF-4 | minor | Six loud-refusal branches verified only by gitignored scratch probes | **Fixed**: offline pins added for the reconciliation raise, the split array, the marker-plus-status conflict, the active-bit/multiplicity disagreement, the missing club record, and the span walk's declared-count lie (retiring the fixture's dead parameter); plus a gamedata test that the span walk and `read_teams` frame identical club sets on every save |
| CF-5 | minor | `docs/data-access.md`'s ~1,712 `historical_id` figure contradicted by the landed measurement (1,920 / 2,137) | Routed to `/update-docs` at the commit gate with the six queued docs-delta items from the players handoff and the six from the rosters handoff |
| CF-6 | nit | `rosters.py` imports thirteen private underscore names from `players.py` as its layout seam | Accepted as the single-source-of-truth trade; promoting a public seam is Phase 8's call, noted in the handoff's still-open |
| CF-7 | nit | `read_rosters` walks the 32 MB `players.dat` a second time (~0.7 s) | Deferred to Phase 8's ingest wiring, where AC17's extraction-cost number will measure it explicitly |
| CF-8 | nit | No grain-uniqueness assertion on the export-less saves | **Fixed**: the per-save invariant loop now asserts the `(team_id, player_id, list_id)` triple unique on every save |
| CF-9 | question | The stored-bits + multiplicity mechanism vs the plan's "read the array" letter — the builder's escalation flag was undispositioned | **Ratified by the operator (GD-1)**, recorded in the amendment |

## Gated decisions

| # | Question | Operator's call (2026-08-18) |
|---|---|---|
| GD-1 | Ratify the stored-bits + multiplicity + reconciliation mechanism against the plan's "read the array" letter? | **Ratified** — the array-order premise was refuted by measurement; every input is a stored fact; the result is oracle-exact |
| GD-2 | Phase 10's position column: ship without it, or gate on a decode attempt? | **Gate on one bounded decode attempt** against the depth-chart region at the exact-or-nothing standard; ship without the column on failure, with the gap named and a follow-up filed |
| GD-3 | Fix the CF-1 fence pre-commit or defer? | Fixed pre-commit per the panel's recommendation — the code now agrees with its three documented contracts |

## Meta-audit

Two internal-consistency notes about the merged report itself (the CF-1 "blocks
/commit" headline vs GD-3's defer option, since mooted by fixing it; nine
verifier-only ledger rows not duplicated into the merged ledger — all of them `met`).
No dropped blocker, no uncovered criterion.

## Post-fix verification

After the CF-1 / CF-4 / CF-8 fixes: offline suite green (the roster module grew to
eighteen offline tests), `ruff check` / `ruff format --check` / `mypy` clean, and the
gamedata roster suite green — six tests including the full-oracle exactness, the
invariants on all three saves, Boston's managed counts, and the new span-agreement pin.
