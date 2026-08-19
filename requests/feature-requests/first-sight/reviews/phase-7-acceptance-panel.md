# Acceptance panel — first-sight Phase 7 (names.dat and the join)

Run 2026-08-18 against the uncommitted Phase 7 tree, on branch
`first-sight-phase-7-names-join` at HEAD `cdcb88e`.

## Panel health — no degradation

| Metric | Value |
|---|---|
| `reviewers_ok` / total | 6 / 6 |
| `verifiers_ok` / total | 5 / 5 (4 batches + the independent ledger verifier) |
| `findings_unverified` | **0** |
| `meta_ok` | 1 |
| `degraded_lenses` | *(empty)* |
| `findings_blocker_major` raw → deduped | 14 → 14 |
| blockers / majors | **0** / 5 |
| criteria met / unmet / unverifiable | 16 / 14 / 2 |
| verdict | `fix` |

Roster: `acceptance`, `fidelity`, `correctness`, `edgecases`, `parser`, `warehouse`.
1.85M subagent tokens, 507 tool calls, ~46 min wall clock.

**Most unmet criteria are Phases 8–12's, not Phase 7's.** AC4/5/6/13/14/15/17/19 and the
warehouse half of AC10 belong to phases that have not started; no code in this diff
attempts them. AC12 stays `partial` because `teams.dat` is `diagnostic` — pre-existing
Phase 0 debt, untouched here.

## What the panel confirmed by execution, not assertion

- It re-ran the gate rather than inheriting it: ruff / format / mypy clean, offline suite
  green across **seven consecutive runs**, Phase 7 gamedata modules 70 passed / 1 skipped.
- Its runs wrote nothing — `git status --porcelain` byte-identical afterward,
  `var/snapshots` still dated 8/17 with no new seq allocated.
- No ADR 0001 risk, no fixed-offset violation (`names.py` reaches the buffer only through
  the ADR 0020 seam with caller-computed positions), no game data tracked.
- Strict zero-residual byte accounting on `names.dat` is real and is checked against the
  file's **own declared count** (264,095 framed == 264,095 declared), not against itself.
- AC7 exact at 18,072/18,072, with the swapped-slot reading refuted as a **live negative
  control** rather than merely unchosen.
- **The meta-auditor closed AC16 itself.** Neither ledger had exercised the
  environment-independence half. It set the install/save/league vars to a nonexistent
  path and MySQL to an unreachable host — `config.py:149` uses `load_dotenv(override=False)`
  so the shell wins — and got 346 passed, matching the clean-env count. Marker discipline
  holds; the merged report had claimed it before anyone showed it.

## Confirmed findings and their dispositions

| # | Severity | Finding | Disposition |
|---|---|---|---|
| CF-01 | major | `build_name_table`'s dict comprehension is last-write-wins, and nothing enforced index uniqueness. Reproduced by three verifiers independently: a file with indices `[1, 1, 3]` frames three records at **zero residual** — strict tier satisfied, nothing raised — and yields a two-entry table with one string silently discarded. The exact failure `names.py` §6 claims to prevent, with zero CI signal, and `bronze_name`'s declared Phase 8 key rests on the unenforced property | **Fixed**: `_check_index` holds every record to `index == position + 1` and refuses by name and position; `build_name_table` re-checks `len(entries) == len(names)` as belt-and-braces. Four offline refusals added — repeated index, gap, index 0, and the collapse guard |
| CF-02 | major | AC8's "100% exact" is not met and cannot be on correct data, but the renegotiation lives only in a test docstring while `PROJECT_SCOPE.md:248` still says "100% exact" | **Operator decision (GD-1)** — see below |
| CF-03 | major | Three refuted plan premises never written back; no `handoff-phase-7.md` | **Operator decision (GD-2)**. The meta-audit found the handoff premise itself wrong — see *Meta-audit* |
| CF-04 | major | `docs/data-access.md:287-289` and `:367-368` now assert the negation of a `verified` field-map entry, with no docs-delta carrier | **Operator decision (GD-2)** |
| CF-05 | major | The fictionalised-league carve-out absorbs 28 of 33 managed disagreements (85%) via a rule the export-verified control save has **zero rows** to corroborate, and its size was pinned by nothing. Failure scenario the panel constructed: a parse fault confined to one affiliate classifies *that affiliate* as fictionalised and excuses itself, while the residual comparison still holds at five and the bimodality guard stays blind (it only flags rates in 5–50%; a broken league sits near 100%) | **Fixed**: `MANAGED_FICTIONALISED_LEAGUES = 1` and `MANAGED_FICTIONALISED_ROWS = 28` pinned and asserted; a new test asserts the probe's population in the excused league is below the floor, scoping the verified-control argument to the rows it actually covers. Neither assertion names a league id |
| CF-06 | minor | The rule treated structurally-absent league (`None`) as a league — one rate crossing the threshold would exempt the entire ~10,700 free-agent/unassigned population in a single step | **Fixed**: `None` excluded from classification, with the reason recorded |
| CF-07 | minor | `names_declared_record_count` labelled `verified` but cross-checked only against the same file | **Fixed**: demoted to `measured`, with the distinction spelled out — `verified` in this repo means scored against an *independent* answer key |
| CF-08 | minor | The no-module-level-cache guard was blind to `functools.lru_cache` — the likeliest spelling of the cache it forbids | **Fixed**: also rejects any module-level callable exposing `cache_info` |
| CF-09 | minor | The SD-13 collation choice was argued in prose and never asserted | **Fixed**: a test round-trips every accented export name and asserts an accent-stripped variant does **not** compare equal, so pushing the comparison into SQL turns it red |
| CF-10 | minor | `_probe(settings)` called inside two list comprehensions, re-parsing ~40 MB per residual row | **Fixed**: hoisted in both places |
| CF-11 | minor | A whitespace-only name was accepted by the walker, and AC9's roster check had a dead disjunct that could not see it | **Fixed**: the walker refuses on `not text.strip()`, so the shape cannot depend on a report layer that does not exist yet |
| CF-12 | minor | The swapped-slot refutation asserted a bound 180× looser than the value it was derived from | **Fixed**: pinned at the measured `SWAPPED_SLOT_MATCHES = 1` |
| CF-13 | minor | `NameTable.save_id` was decorative — nothing enforced that a table is applied to the save it came from | **Fixed**: `for_save(save_id)` refuses a mismatch, plus an offline test. The tables being byte-identical today is precisely why the mismatch had to be refused rather than trusted |
| CF-14 | nit | `test_doc_links` races with leak-guard probe files planted in the repo root | **Not mine, and not fixed here.** Pre-existing; the meta-audit confirmed CI is single-process (`ci.yml:57`, no xdist) so it is unreachable there. Carried as a follow-up |
| CF-15 | minor | The new cross-mode docstring claimed Phase 7 covers every file this slice walks; two walked files have no record-level section | **Fixed**: the docstring now names `saved_games.dat` and `human_managers.dat` as header-level only |
| CF-16 | minor | A cross-SAVE assertion in the cross-MODE module, with a sim-date guard that would go red once the managed league sims to 2024-03-18 | **Fixed**: the guard is now "the two files' bytes differ", which does not rot; the deliberate exception is labelled, mirroring the `world.dat` section's precedent |
| CF-17 | minor | `IMMUTABLE_PLAYER_FIELDS` is eight entries while three pieces of prose said seven | **Fixed** |
| CF-18 | minor | No offline test joined a synthetic `players.dat` to a synthetic `names.dat` despite both fixtures existing | **Fixed**: two offline tests, with the indices deliberately non-adjacent so only a correct slot assignment renders the expected name, plus a negative control |
| CF-19 | nit | `test_a_nonzero_preamble_is_refused` described behaviour the walker did not have and duplicated the test above it | **Fixed**: the fixture gained `preamble_prefix`, and the test now puts content *inside* the zero run — genuinely distinct from removing the sentinel |
| CF-20 | nit | `__all__` omitted `build_name_table` and `NAME_ENCODING` | **Fixed** |
| CF-21 | nit | A bare assert on a shipped-install row count would fail without explaining itself | **Fixed** |

## Meta-audit — five findings, and two of them corrected the panel

The meta-auditor did not merely rubber-stamp the merge:

1. **AC16 was upgraded partial→met with the auditor's caveat silently deleted.** Neither
   ledger had exercised the environment-independence half. The meta-auditor ran it (above)
   and closed it honestly, so the verdict lands correctly — but flagged that the merged
   report asserted it on evidence nobody had, which is the exact failure this pipeline
   exists to catch.
2. **The missing-handoff finding rests on a precondition nobody tested.** The eight-section
   handoff is the **data-engineer subagent's return contract**
   (`.claude/agents/data-engineer.md` §Return contract), not a phase-completion requirement
   on main-thread work — and four of Phase 7's ten steps are prefixed **MAIN THREAD**,
   including both join test modules and the AC9 clause. This build was main-thread. If no
   subagent was spawned, no handoff is owed, the builder's deny set does not apply, and the
   correct route for the docs is the one Phase 6a (`f640bef`) and Phase 6b (`cdcb88e`) both
   took: `/update-docs` in the same commit.
3. **Gated decision 2 mis-located the ADR 0006 exposure.** It claimed name strings sit in
   `field_map.toml`; a grep shows that file carries **zero** name strings — only counts and
   block boundaries, squarely inside ADR 0006's derived-knowledge carve-out. The real
   exposure is three places: `tests/test_parse_names.py`, one comment in
   `tests/fixtures/synthetic.py`, and one docstring line in `names.py`.
4. **Completeness gap in the panel itself:** `field_map.toml` is the diff's largest tracked
   contract change (+95 lines, four new `verified` labels) and has **zero programmatic
   consumers** — nothing parses it, nothing checks a `category` against the declared
   vocabulary, nothing cross-checks a label against the validator that earned it. A typo or
   a pasted `verified` would ship green. No lens raised it as a finding; Phase 8's
   `contracts/loader.py` is where it gets one.
5. Ledger schema glitch: AC12's `source` reads `partial-scope` where every other row reads
   `scope` — a verdict value bleeding into a provenance field in a machine-consumable
   artifact.

## Guards seen to fail, then reverted

| Broke | Went red |
|---|---|
| Swapped the two name slots in `players.py` | `test_names_join.py` — 18,071/18,072 disagreeing, **named per player** |
| Planted a module-level `dict` in `names.py` | `test_names_py_holds_no_module_level_cache`, naming the container |

Both reverted; the gate re-ran clean afterward.

## Post-fix verification

After CF-01 / CF-05 / CF-06 / CF-07 / CF-08 / CF-09 / CF-10 / CF-11 / CF-12 / CF-13 /
CF-15 / CF-16 / CF-17 / CF-18 / CF-19 / CF-20 / CF-21: `ruff check` / `ruff format --check`
/ `mypy` clean, offline suite **353 passed** (up from 346), gamedata **118 passed, 1
skipped** (up from 115; the skip is the pre-existing `teams.dat` diagnostic-tier skip).
