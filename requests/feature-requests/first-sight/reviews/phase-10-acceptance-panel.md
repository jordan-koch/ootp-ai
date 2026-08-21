# Acceptance panel — first-sight Phase 10 (the roster report, and the standings that could not be built)

Run 2026-08-20 against the uncommitted Phase 10 tree, on branch
`implement/first-sight-phase-10` at HEAD `855a5fe`.

## Panel health — no degradation

| Metric | Value |
|---|---|
| `reviewers_ok` / total | 6 / 6 |
| `verifiers_ok` / total | 5 / 5 (4 batches + the independent ledger verifier) |
| `findings_unverified` | **0** |
| `meta_ok` | 1 |
| `degraded_lenses` | *(empty)* |
| `findings_blocker_major` raw → deduped | 26 → 24 |
| blockers / majors | **1** / 7 |
| criteria met / unmet / unverifiable | 23 / 19 / 3 (of 45) |
| verdict | `fix` |

Roster: `acceptance`, `fidelity`, `correctness`, `edgecases`, `parser`, `warehouse`.
1.89M subagent tokens, 536 tool calls, ~47 min wall clock.

**Most of the 19 unmet criteria are not Phase 10's.** AC15 (catalog), AC17's catalog half,
AC18's doc reconciliation, AC19, AC20 and AC21 belong to Phases 11–13 and are untouched by
design. The two that *are* this phase's are AC14's standings clause and Core §13.

## One finding refuted and dropped

**fidelity F3 — "AC14's organisation test is tautological and cannot fail"** — was put to a
verifier and **refuted by mutation testing against the live landing**: pointing the filter
at the wrong club goes red (205 trespassers), dropping the predicate goes red (21,820).
The test computes its `foreign` set independently from `ref.human_team_id` rather than from
`build_roster`'s parameter, so it does discriminate. Only a wrong-*column* mutation
survives, and the sibling test at `:223` catches that (34 ≠ 226). AC14 clause 2 stands.

The verifier's salvage was nevertheless taken: a mutation assertion now builds the roster
for a different organisation in-process and requires a disjoint player set, so the
criterion carries its own proof of discrimination rather than relying on a sibling.

## The blocker is a missing amendment, not missing code

**S0 — the standings report was never built and AC14 was narrowed with no amendment in any
tracked artifact.** The engineering reason was verified five independent ways: no declared
table carries wins, losses, games played or pct; `parser/teams.py:237` records that the
standings region is not in `teams.dat`; Phase 5b's `world.dat` walk reached division
membership and the calendar rather than team records; and the "all 259 `team_record` rows
are 0-0-0" figure the plan cites is the **export's** table, which this project never landed.

So the code is right and the record is wrong. The only trace of the deviation was a
docstring in `tests/test_reports.py` citing an `IMPLEMENTATION_REPORT.md` that does not
exist, while AC6, AC8 and AC12 each carry a dated *"Amended … at the operator's direction"*
block. **Gated to the operator** — the same disposition Phase 9 gave CF5, and for the same
reason: an acceptance contract the builder edits to match its own output is not a contract.

The panel also names a root cause worth keeping: Phase 5's acceptance criteria never
checked for the win-loss fields plan line 324 assigned to it. That is a lesson about phase
acceptance, not about standings.

## Confirmed findings and their dispositions

| # | Severity | Finding | Disposition |
|---|---|---|---|
| S0 | blocker | **The standings deviation is recorded nowhere tracked.** Verified five ways that the code decision is right; the artifacts still assert two reports | **GATED to the operator.** Amendment drafted for `PROJECT_SCOPE.md` AC14 + Core §13 and `IMPLEMENTATION_PLAN.md` Phase 10 step 3 |
| S1 | major | **The serving gate was not exhaustive and its docstring said it was.** `city`, `nickname`, `level`, `list_id` and `team_id` reached the page ungated while their sibling `abbr` was declared — internally inconsistent, not merely short. A verifier simulated downgrading `roster_membership` to `unconfirmed`: `check_renderable` **still passed** and the page kept printing "Active roster" with no banner. Nothing in the package had ever called `render_with_uncertainty`, so SD-17's pre-registered fallback was documented as honoured and was unreachable | **Fixed.** `REPORT_COLUMNS` widened to 16 entries; `SELECTED_COLUMNS` added and asserted **congruent in both directions** offline; `list_label_mode()` implements the fallback for real, and a test drives the downgrade end to end and requires the banner on the page |
| S2 | major | **The name join bound four of `bronze_name`'s five key columns**, omitting `name_space` — the exact assumption `tables.toml` refuses to make. Measured by two verifiers: with a second space present, a 226-player organisation returns **904 rows** (exactly 4x) under fabricated first/last combinations. The only assertion that would catch it is `gamedata`, so CI had none | **Fixed.** `name_join_predicate()` binds the full key from `SINGLE_NAME_SPACE`, and an **offline** test enumerates `bronze_name`'s declared key and requires every column to appear in the predicate |
| S3 | major | **The page printed "Measured, 935 players span two clubs"** — the probe save's global 40-man row count, wrong for this landing by ~27x, in the `Measured` register, four sections under the page's own promise that *"every figure below is that snapshot and no other."* Second instance: "Measured at 176 per save" inside an organisation-scoped section. **And the suite protected the error** — `test_..._appear_twice` asserted `"935" in page` | **Fixed.** Both figures computed from the rows in hand; the page now reads *"1 of this organisation's 226 players"*. The literal-935 assertion is replaced by one that builds two spanning players and requires the rendered count to equal 2 |
| S4 | major | **`OOTP_OUTPUT_ROOT` was not fenced away from the game directories**, though `_is_within` already existed with one call site, and **`render()` — the project's second file writer — sits outside the ADR 0001 runtime manifest proof** | **Fixed (fence).** `_root()` now refuses either root resolving inside `$OOTP_INSTALL` or `$OOTP_SAVED_GAMES`, with four parametrised offline tests. **Carried (proof):** extending the manifest-diff window to call `render()` is recorded below rather than done |
| S5 | major | **Nothing at runtime stopped `render()` writing real player names into a tracked directory of a public repo.** `.env.example` states the requirement in capitals; a grep for `check-ignore` across `src/` returned one **comment**. The leak guard cannot substitute — `roster.md` is not a banned name and `.md` is not a banned suffix, so the file would be scanned, found clean, and committed | **Fixed.** `_check_never_tracked()` refuses an in-worktree output root git would not ignore; a root outside the worktree passes unconditionally, which is the safer case `.env.example` already blesses. Offline tests both ways |
| S6 | major | **AC14's name regex is ASCII-only while `names.dat` is latin-1.** Measured: 1,623 landed entries carry a non-ASCII character and **all 1,623 fail** the pattern. Green today only because Boston's books hold none; the first international signing turns it red **on a correct render** | **Fixed, and flagged as a scope amendment.** Widened to `^[^\W\d_][\w .'-]+$` with `re.UNICODE`, moved to `tests/fixtures/reports.py` so **CI** guards it, with parametrised cases pinning that `José Ramírez` and `Yū Darvish` pass while `47035` and the absence marker still fail. The pattern is quoted verbatim in AC14, so the widening rides with S0's amendment |
| S7 | major | **`_tracked_under()` raised `CalledProcessError` on an out-of-repo output root**, so AC14's clause-1 tests would ERROR on a supported, *safer* configuration. Both callers guarded their other helper against that case and called this one unguarded | **Fixed.** Early return of `[]` when the path is outside the worktree — nothing outside it can be tracked |

## Meta-audit — three findings about the panel, not the work

- **M2 is the one that matters: `tests/test_reports.py`, the phase's own acceptance module,
  was executed by no reviewer.** The lenses are read-only and it writes a file. The main
  thread ran it (10 passed) both before and after the fixes, so the gap is in the panel's
  coverage rather than in the evidence — but a panel that cannot run the acceptance module
  cannot claim the acceptance criterion, and it is recorded here so the next phase's
  reviewers are told to use `render()`'s return value rather than skipping it.
- **M1: three lenses reported offline pass counts that are arithmetically impossible on this
  tree**, and the merge laundered them into an unqualified "offline suite green". The main
  thread's own counts are the ones used in this document, taken from `--junit-xml`:
  **586 offline** and **164 gamedata / 1 skipped**.
- **M5: the lenses ran concurrently against one shared working tree**, so at least two
  reported reds were cross-contamination — including a `test_no_fixed_offsets` failure
  caused by a sibling test writing a probe `.py` into the live package tree. That probe
  hazard is the same shape as Phase 9's CF24 and is still unfiled.

## Post-fix verification

`ruff check` / `ruff format --check` (190 files) / `mypy` (74 files) clean.
**Offline 586 passed, 0 failed** (560 before the fixes; 520 after Phase 9).
**Gamedata 164, 0 failed, 1 skipped** — the skip is `test_byte_accounting.py`'s strict-tier
assertion, named and expected.

The report was re-rendered end to end after every fix. It carries 226 organisation players
across eight clubs, Boston's active roster reads 26 and its assigned 33 against 26 active +
7 injured, and the multi-club figure now reads **1** — computed — where it read 935.

**One guard was seen to fail before being trusted.** `check_renderable` was temporarily
narrowed to `columns[:1]`; the last-position test went red while the naive same-column test
stayed green, which is the arrangement earning its place. Reverted.

## Carried, not fixed

- **S0's amendments** — operator's call, per the AC6 / AC8 / AC12 precedent.
- **S4's second half** — calling `render()` inside `test_read_only.py`'s manifest-diff
  window. The static allowlist covers it today and was *narrowed* in this diff (bare
  filename → package-relative path) so `reports/__main__.py` does not pre-authorise Phase
  11's `catalog/__main__.py`.
- **The stray-probe hazard** (M5, and Phase 9's CF24) — still worth its own bugfix request.
- **A team-record source** — the follow-up S0 names; `world.dat`'s unmapped per-league
  blocks are the candidate, and it pairs naturally with `league-dimension`.
- **Incremental loading across sim dates** — raised by the operator before the panel ran.
  `test_a_landing_at_another_sim_date_is_left_untouched` *finds* a second date
  opportunistically and skips loudly when there is none; no test lands one league at two
  dates, and nothing reads across snapshots.
