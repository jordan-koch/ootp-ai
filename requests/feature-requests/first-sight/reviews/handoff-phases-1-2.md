<!-- handoff: v1 -->

## track

feature

## built

**Phase 1.** `src/ootp_ai/config.py` — `to_save_id`, `SaveRef`, `MySQLSettings`, `Settings`,
`load_settings`, all frozen dataclasses. The only module touching the environment;
`load_settings` takes a mapping and falls back to `.env` + `os.environ`, so nothing
downstream needs a machine. No literal path, no `parents[N]` walk. `to_save_id` slugifies
rather than validates the raw stem (two of the three real saves contain spaces) and cannot
emit a separator, drive letter or colon. Optional saves resolve to `None`; the roots default
CWD-relative and are refused under `%OneDrive%`. `src/ootp_ai/warehouse/sql.py` (plus the
package `__init__.py`) is `quote_ident` / `qualified` / `column_list`, rejecting an embedded
backtick rather than doubling it. `src/ootp_ai/db.py` holds the two factories; the
ground-truth one connects with `SET SESSION TRANSACTION READ ONLY` as `init_command`, then
*reads the setting back* and raises `ReadOnlySessionError` if it is not 1.

**Phase 2.** Spike run against the retained standard-mode save and `ootp_truth_real` as
throwaway scripts under `var/spike/` (git-ignored, untracked, every handle `"rb"`). Verdict
in `…/first-sight/reviews/spike-scouted-view.md`: **`stored`**, label `measured`, so the
pre-registered **FOUND** branch is live and **this slice still lands no ratings**. Both
pre-registered controls were run — the export's true ratings, and raw `players.csv`.

## verified

| Claim | Command | Actual output |
|---|---|---|
| Offline suite green, 60 tests, incl. the four pre-existing guards | `uv run pytest -m "not gamedata"` | `60 passed in 0.31s` |
| Lint clean | `uv run ruff check .` | `All checks passed!` |
| Format clean | `uv run ruff format --check .` | `69 files already formatted` |
| Types clean under strict, driver imported | `uv run mypy` | `Success: no issues found in 12 source files` |
| Widened marker collects, no `--strict-markers` error | `uv run pytest --collect-only -m gamedata` | `no tests collected (60 deselected) in 0.02s` |
| No `parents[N]` walk or `os.path` in `src/` | Grep `parents\[|os\.path` over `src` | one hit: a `config.py` docstring line saying not to |
| Read-only session enforced by the server, not by comment | `uv run python var/spike/01_explore_truth.py` | `session transaction_read_only = {'read_only': 1}` |
| Spike code is untracked | `git check-ignore -q var/spike/06_correlate.py` | `check-ignore exit=0` |
| Pivot rule committed strictly before the verdict (AC18) | `git log --oneline -1 -- …/spike-pivot-rule.md` | `56741e5 Pre-register the first-sight pivot rules before the spike runs`; verdict file still untracked |
| New files pass the leak and link guards, LF endings | `uv run python var/spike/13_guardcheck.py` | `leak violations: none` · `broken relative links: none` · `CRLF=False` for all six |
| Stored `u16` bands onto the exported OSA column | `uv run python var/spike/07_bands.py "<truth league>" batting_ratings_overall_contact 40` | 11 monotone bands; on the 6,600 disagreement players the stored value sits in the OSA band `6,099` times, `r(OSA)=0.973` vs `r(own)=0.801` vs `r(TRUE)=0.849` — **main-thread re-run confirms these figures** |
| ~~`overlapping=0`~~ — **corrected by the main thread** | metric is in `08_divergence.py:85`, not `07_bands.py` | It counts an overlap only when `next_min < prev_max - 1`, so it tolerates a one-unit overlap by construction. Five boundaries overlap by 1–2 stored units. Accurate claim: **no band overlaps by more than one stored unit.** Verdict unaffected; see the correction in `spike-scouted-view.md` |
| Stored value is not the true rating (`players.csv` control) | `uv run python var/spike/11_summary.py "<truth league>"` | exact match with any raw contact column: `54` of 1,544 (3.5%); mean distance `28.8` raw points |
| Own-scout view absent from the record's stable prefix | `uv run python var/spike/08_divergence.py "<truth league>"` | best predictor of `(own − OSA)` is `r=0.186` batting, `r<0.09` pitching/fielding/running |

## assumed

- **`MYSQL_TRUTH_REAL_DATABASE` and `MYSQL_PASSWORD` are optional.** `tests/test_config.py`
  requires exactly five keys and neither is among them, so an unset truth database yields
  `truth_database=None` and `connect_truth` raises `ConfigError` at use — CI has no warehouse.
- **`load_settings` creates nothing.** The plan says "validate it is creatable"; I check the
  path is not an existing file rather than `mkdir`-ing, because config that makes directories
  as a side effect of being read scatters them during collection. The OneDrive refusal also
  covers `output_root`, not only the snapshot root the plan named — same failure mode.
- **The spike's greedy ascending-`player_id` anchoring is correct.** Self-validating: all
  18,072 ids matched in order at a 123–137 byte stride, and misaligned anchors could not
  produce zero-overlap bands. Spec was silent on it, so per the rulebook the spike ran
  read-only off the live saves with `"rb"` handles and wrote nothing under the game roots.

## surprised-me

- **The MySQL export writes ratings on the 20–80 display scale, not the raw scale** (11–13
  distinct values, min 20, max 80). The pre-registered method — search `scouting.dat` for the
  exported values — is unrunnable as literally written: those byte patterns match noise
  everywhere. Searching the other direction (locate the stored value, then test which view it
  bands onto) worked and is strictly stronger.
- `information_schema` returns UPPERCASE column names, so `DictCursor` rows `KeyError` on
  `table_name`. Alias every one.
- `test_no_leaks.py` and `test_doc_links.py` iterate `git ls-files`, so a file you just wrote
  is invisible to both until committed — a green suite says nothing about new files. I ran the
  guards over mine by hand.
- The same stored rating appears **twice per record**, at `+40` and `+53`, identical for 1,017
  of 1,544 real players — two views of one rating, not two scouting perspectives.

## could-not-do

- **I could not add `OOTP_TRUTH_LEAGUE` / `OOTP_PROBE_LEAGUE` / `OOTP_OUTPUT_ROOT` to the
  live `.env`** — outside my declared target paths. It still carries the retired
  `MYSQL_TRUTH_OSA_DATABASE` and none of the three new keys, so each spike script takes the
  league name as `argv[1]` and resolves its root through `settings.saved_games`. Nothing is
  hardcoded, but until `.env` is updated, `load_settings().truth_save` is `None`. No denied
  path was requested, no destructive git operation needed, no package missing.

## docs-delta

Route through `/update-docs`; I wrote nothing in `docs/`.

1. **`docs/data-access.md:282` §5 — `unconfirmed` → `measured`.** The scouted view **is
   stored** in `scouting.dat`, raw scale, one variable-length record per player; cite the
   verdict file for byte evidence. The own-scout half stays open at `inferred`.
2. **New, and it hits §5's trap directly (`measured`):** the in-game **MySQL/CSV export is
   itself scale-converted to 20–80**; `players.csv` is raw and the export is not, so Phase 9's
   differential compares a raw value to a display value unless it converts first.
3. **`scouting.dat` structure (`measured`):** standard header, version `0x19`, self-declared
   filename, byte-identical across all three saves; 18,072 records in the standard-mode probe,
   ids ascending, stride 123–137 B (mode 127), 119-byte tail; the managed league's file is
   2,863,744 B against the probes' 2,349,181 B. **Record the offsets with an explicit
   never-hardcode note** — they hold only in the stable prefix, and pitching/fielding/running
   ratings visibly did *not* band at any fixed offset.
4. **`players.csv` vocabulary (`measured`):** the vs-RHP contact column is spelled
   **`Contact Vr`** — there is no `Contact vR`, though `Power vR`, `Eye vR` and `BABIP vR`
   do, so a reader assuming the pattern gets an empty column and no error. Needs `latin-1`.
5. **Ground-truth population shapes (`measured`):** `players_scouted_ratings` is 137 columns
   × 36,144 rows (two perspectives, 18,072 each) and carries `scouting_accuracy` — 1–5 for
   the club's own coach, **constant 3 for OSA**. `players` and the three `players_*ing`
   rating tables hold **132,990** rows against 18,072 active players, so they include retired
   players; averaging across that boundary is the structural-absence error, not a gap.

## still-open

- **The verdict's second half deserves a follow-up request now.** OSA has a data path; whether
  the organization's *own* read is stored is unresolved, and that is the mechanic ADR 0014
  rests on. Settling it needs a sequential walk of one record with byte accounting.
- **Operator action, user-run:** update the live `.env` per the committed `.env.example`, and
  run `ops/mysql-bootstrap.sql`'s `ootp_dev` create/grant if it has not been run.
- **Smaller interpretation taken:** "connection factories" became exactly two functions plus
  the read-only assertion — no pooling, no context managers, no cursor helpers. The wider
  reading is a cheap follow-up if the loader wants it.
- Phase 2's commit note asks for a go/no-go **only if the verdict is ABSENT**. It is
  `stored`, so Phase 3 is unblocked. `var/spike/01–13*.py` stay untracked; the verdict
  document carries the method so it re-runs without them.
