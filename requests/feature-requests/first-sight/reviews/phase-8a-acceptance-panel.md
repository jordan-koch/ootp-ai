# Acceptance panel — first-sight Phase 8a (contracts, DDL, and the offline grain guards)

Run 2026-08-19 against the uncommitted Phase 8a tree, on branch
`first-sight-phase-8a-contracts-ddl` at HEAD `6d66aee`.

## Panel health — no degradation

| Metric | Value |
|---|---|
| `reviewers_ok` / total | 6 / 6 |
| `verifiers_ok` / total | 5 / 5 (4 batches + the independent ledger verifier) |
| `findings_unverified` | **0** |
| `meta_ok` | 1 |
| `degraded_lenses` | *(empty)* |
| `findings_blocker_major` raw → deduped | 16 → 16 |
| blockers / majors | **0** / 6 |
| criteria met / unmet / partial / unverifiable | 17 / 7 / 5 / 6 |
| verdict | `fix` |

Roster: `acceptance`, `fidelity`, `correctness`, `edgecases`, `parser`, `warehouse`.
2.02M subagent tokens, 533 tool calls, ~51 min wall clock.

**Most unmet criteria are Phases 8b–12's, not 8a's.** AC5, AC6, AC14, AC15, AC17 and AC19
belong to phases that have not started; no code in this diff attempts them. AC20/AC21 are
USER-RUN by the scope's own instruction and the panel claims nothing about them. Three
Phase-8a-specific rows fell short and all three are fixed below.

## What the panel confirmed by execution, not assertion

- It re-ran the gate rather than inheriting it: `426 passed, 118 deselected`, ruff clean,
  mypy clean over 58 files.
- `git ls-files src/ootp_ai/warehouse` → `__init__.py`, `sql.py` only, so **"8a writes no
  loader"** holds mechanically.
- A grep of the three new `src` modules for `open(|write|connect|.seek(|unpack_from|
  subprocess` returns two docstring hits and nothing else: **no ADR 0001 risk, no
  fixed-offset surface, no database contact.**
- It emitted all eight `CREATE TABLE`s and read them: every key opens
  `(save_id, sim_date, ingest_seq)`, every PK column renders `NOT NULL`.

**Two panel majors were refuted by execution rather than accepted.** The claim that
`ingest_run`'s `ai_ci` collation would break every `save_id` join with `ER_1267` was run
read-only against the live MySQL 8.4.9 — `join_ok=1, resolved=utf8mb4_bin` — because
MySQL resolves equal-coercibility `_bin`/`_ci` operands of one charset to `_bin`. The
"verifier" that confirmed it had reproduced a different coercibility class. Carried
instead as minor CF11 (the real consequence: `ingest_run`'s PK case-folds `save_id` while
the six bronze PKs do not). The claim that the 176 assigned-but-unrostered players are lost
was likewise refuted on the committed fixture — the population is the exact anti-join of
landed columns.

## Confirmed findings and their dispositions

| # | Severity | Finding | Disposition |
|---|---|---|---|
| CF1 | major | **The serving gate was fail-open on category.** Any category `disposition()` did not literally name fell through to RENDERABLE — reproduced with `unknown`, `scouting`, `rating-potential`, `""` and even the case variant `RATING-TRUE`, all at `epistemic = "verified"`. Release-by-default, in the module whose own docstring quotes the opposite rule. The loader's vocabulary is not defence in depth: it lives in the same tracked file whose author would add the category | **Fixed**: `NON_RATING_CATEGORIES` enumerated and unknown → WITHHELD; `check_policy_covers()` added, mirroring `ddl.py`'s identical guard for column types. Six parametrised cases pin it |
| CF2 | major | **A column with no `field` short-circuited to RENDERABLE.** 39 columns used that door. A `batting_ratings_talent_contact` column with its `field` line omitted loaded clean, emitted into the DDL and rendered — while `_name_is_withheld` on the same string returned True the whole time, because it had one call site and was only ever passed a *field* name | **Fixed**: `provenance = true` is now an explicit declaration and the loader refuses a column carrying neither it nor a `field`; the name check moved to the front of `column_disposition` and now sees column names |
| CF3 | major | `calendar_real_sim_date` was labelled `verified` against its own walker's `unconfirmed` and the Phase 5b handoff's explicit proposal. The validator is vacuous — **both sides are zero on every row**, so a parser reading an adjacent zero u16 scores identically | **Fixed**: `unconfirmed` / `none` with the argument recorded. It becomes the uncertainty path's **first real field**, retiring that branch's synthetic-only caveat |
| CF4 | major | Six `bronze_player` columns declared `u32` against fields the walker reads `cursor.i32()` **on purpose** — the export writes `league_id` negative on 176 records and a green offline test asserts `league_id == -203`. Landing -203 into `INT UNSIGNED` aborts the batch or clamps to 0, and 0 means "no team" | **Fixed**: the six are `i32`, and `_check_signedness` now refuses the whole class at load time |
| CF5 | major | `ingest_run` contradicted the `IngestRun` dataclass three ways: `parse_seconds NOT NULL` against `float \| None` whose own comment says None is not zero; `residual_bytes` one scalar against a per-file `Mapping` whose accounting tier differs by file; `game_version` a column with **no attribute anywhere in the repo** | **Fixed**: nullable, JSON, and dropped respectively — each argued in the table's note |
| CF6 | major | Plan §2.3(d)'s provenance-triple invariant was prose with nothing holding it. Proved: adding `date = ["sim_date"]` to the dimension map and restating a grain "per save per date" loads cleanly and emits a key without `ingest_seq` | **Fixed**: an ordered `key[:3]` assertion over all eight tables |
| CF7 | minor | Plan step 8a.1's Decisions §8 record (ratings render at the 20–80 player-page scale) was silently skipped — **P8a-7 unmet** | **Fixed**: recorded in the `[[withheld]] ratings` entry, where the next slice will look |
| CF9 | minor | `[meta].incomplete = []` overclaimed: `human_managers.dat` and `saved_games.dat` are parsed with zero field entries, and the first feeds a declared column — **P8a-4 partial** | **Fixed**: the club id is now declared (`human_manager_team_id`, `inferred`); the rest is named in `incomplete`, whose meaning is now stated |
| CF19 | minor | `team_human_flag` labelled `verified` although `teams.py` records the slot as irreducibly ambiguous (`human_team` vs `human_id`, both 1/0 identically, 18 field orders fit) | **Fixed**: `measured`, with the ambiguity in the note — the same honesty `world_league_head` already applied |
| CF20 | minor | A tracked test gave the wrong reason for `historical_id` being nullable, inviting 8b to collapse `""` into NULL | **Fixed** |
| CF21 | minor | Two VARCHAR widths narrower than the parser's own accepted bounds (`_MAX_STRING = 128`, `_TAIL_STRING_MAX_LEN = 40`) | **Fixed** |
| CF23 | minor | `bronze_player`'s coverage pointed readers at `[[withheld]]` for six fields that have no such entry | **Fixed**: the two kinds of absence are now distinguished |
| CF12 | minor | `bronze_team_roster.source` packed two filenames into one string inside a list built to hold two | **Fixed** |
| CF25 | nit | The plan's Phase 5b step still named the calendar key `event_seq` while the declaration ships `seq` | **Fixed** in the plan |
| CF8, CF10, CF11, CF13–CF18, CF22, CF24, CF26, CF27 | minor/nit | Carried, not fixed — see *Carried* below |

## Meta-audit — five findings, two of which corrected the panel

1. **MA1 (major): sampling reported as coverage.** P8a-14's evidence read "85 of 86 entries
   hold up under spot-checking" and named one bad label, while the same report confirmed a
   second (CF19) at minor severity. The label audit never enumerated the 59 `verified`
   entries. **Both bad labels are fixed here**; the enumeration gap is carried.
2. **MA2 (minor): a reviewer finding was dropped** — the roster key's spelling is pinned
   only by a precondition `assert` with a misleading failure message. CF6's fix does not
   cover `list_id`. Carried.
3. **MA3 (minor): AC16's "with no MySQL" clause was upgraded from the verifier's honest
   `partial` to `met` on a static argument nobody executed.** The reasoning is sound and it
   is an argument, not a measurement. Recorded rather than papered over.
4. **MA4 (nit): the summary said seven majors; the array holds six.**
5. **MA5 (nit): one lens reported a 414-test baseline where every other run saw 426**, with
   no reconciliation.

## Guards seen to fail, then reverted

| Broke | Went red |
|---|---|
| `bronze_team_roster` key → `(sim_date, player_id)` in the tracked file | the grain guard, naming the table, its sentence, and the four missing columns |
| `epistemic = "verifed"` planted on `team_park_id` | the loader, naming the field **and** the value |

Both reverted, and both are now permanent in-memory tests rather than one-off manual steps.

## Post-fix verification

`ruff check` / `ruff format --check` / `mypy` clean; offline suite **442 passed** (up from
426 at panel time, 353 before the phase). Disposition census after the fixes:
**76 renderable / 10 withheld / 1 uncertain** across 87 fields and 8 tables.

## Carried, not fixed

Recorded here rather than silently dropped:

- **CF8** — `bronze_division_team`'s key admits the club-in-two-divisions fan-out its own
  coverage denies; Phase 8b's planned `team_id`-uniqueness test is where that becomes an
  assertion.
- **CF10** — a column's `field` is never checked against its table's `source`, so
  `bronze_field_label` could record a belief from the wrong file.
- **CF11** — `ingest_run` and `bronze_field_label` collate `ai_ci`, so their `save_id` PKs
  case-fold while the six bronze keys do not.
- **CF13** — `walker` and `source` remain the only unvalidated values in the field map.
- **CF14/CF15/CF16/CF17** — the `ingest_run` grain sentence is tautological; the grain guard
  compares sets (partly closed by CF6's ordered check); the vocabulary mutation is committed
  only against the synthetic map; the join scanner ignores keyword arguments and f-strings.
- **CF18** — unclassified regions are filed `rating-true`, so `bronze_field_label` will
  persist a belief known to be a placeholder.
- **CF22** — nothing ties a declared column set to the parser record it claims to be 1:1
  with. **This is the largest carried item** and it is 8b's natural home, where the loader
  materialises both sides.
- **CF26** — the emitted DDL is never executed, so a syntax defect would first surface
  mid-ingest in 8b.
- **CF27** — the offline suite left stale leak-guard probe files once; two tests failed on
  first run and passed on re-run. Same shape as Phase 7's CF-14, still unfiled.
