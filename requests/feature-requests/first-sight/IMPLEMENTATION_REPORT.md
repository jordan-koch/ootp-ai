> **Status:** planned · created 2026-08-20 · decided · next: implement (Phase 12)

# Implementation Report — First sight, Phases 10–11: the roster report and the catalog

> **This is a PHASE report, and the request's status stays `planned` deliberately.** The
> plan sequences fourteen phases and assigns this file to Phase 12; it is opened early
> because Phase 10's acceptance panel found the standings deviation recorded in no tracked
> artifact, and a deviation with nowhere to live is how the record and the repo drift
> apart. Phases 11–13 append to it. The status grammar's `implemented` belongs to the
> phase that closes AC20 and AC21, which are the operator's and are not run yet.

> **One-line outcome:** the GM can name its own 26-man roster, and the other 200 players in
> its organisation, with real names · **Acceptance:** AC13 and AC14 met, AC14's standings
> clause retired by dated amendment · **Branch:** `implement/first-sight-phase-10`

**This is the commit the request exists for.** Before it, `gm/charter.md` was right that the
GM could read its charter and not one fact about a single player on its roster. After it,
`var/reports/OOTP-AI/2024-03-07/1/roster.md` names Rafael Devers, his age, his handedness
and his uniform number, and says which snapshot it read them from.

**Phase 10 of 14. The scope is not closed** — Phases 11 (catalog), 12 (doc truth-up) and 13
(USER-RUN acceptance) are untouched by design, so AC15, AC17's catalog half, AC18's doc
reconciliation and AC19–AC21 remain open.

## 1. Acceptance ledger

| Criterion | Verdict | Evidence |
|---|---|---|
| **AC13** — the serving gate, both directions, offline | **met** | `tests/test_withheld_fields.py` green; extended this phase by `test_report_rendering.py`'s gate section — the positive case over all 16 shipped columns, the negative over a real withheld column (`bronze_name.name_category`), and the last-position anti-vacuity case |
| **AC14 c1** — output root git-ignored, proven both ways | **met** | `test_the_resolved_output_root_is_git_ignored` + `test_the_written_report_is_git_ignored`, `-m gamedata`, green. `git check-ignore -q` exits 0 and `git ls-files` lists nothing under it |
| **AC14 c2** — exactly the configured organisation, zero others | **met** | `test_every_player_belongs_to_the_configured_organisation` green, and it now carries its own mutation proof: building the roster for a different organisation returns a **disjoint** player set. The paired `test_the_report_holds_every_player_of_the_organisation` pins 226 = `COUNT(*)`, closing the empty-report escape |
| **AC14 c3** — every player row names a person | **met** | `test_every_player_row_names_a_person` green over 481 rendered rows, 0 failures. Pattern widened to Unicode by amendment — see §3 |
| **AC14 c4** — club, `sim_date` and `ingest_seq` on line one | **met** | `test_line_one_carries_the_club_the_sim_date_and_the_ingest_seq` green; provenance is a header block under the H1 rather than literally line 1, which both test modules read |
| **AC14 c5** — standings: 30 MLB rows, W-L-pct-GB | **retired** | **Amended 2026-08-20 at the operator's direction.** No declared table carries a win-loss column. `PROJECT_SCOPE.md` AC14 and Core §13 carry the full reasoning; `IMPLEMENTATION_PLAN.md` Phase 10 step 3 is struck through |
| **AC16** — offline gate green with no game and no MySQL | **met** | `uv run pytest -m "not gamedata"` → **586 passed, 0 failed** (junit-xml). `ruff check`, `ruff format --check` (190 files), `mypy` (74 files) all clean. The four pre-existing guards green |
| **AC10 / AC11 regression** — append-only, read-only | **met** | `uv run pytest -m gamedata` → **164, 0 failed, 1 skipped** (the named `test_byte_accounting.py` strict-tier skip). Includes the Phase 9 differential, so Phase 10's own precondition held throughout |

**Not this phase's, and open:** AC15, AC17 (catalog half), AC18, AC19, AC20, AC21.

## 2. What shipped

**`src/ootp_ai/reports/`** — new package, imported by nothing that existed before.

- `resolve.py` — which snapshot a report renders from, and where it writes. Takes an
  explicit `sim_date`, defaults to the most recent landed, resolves `max(ingest_seq)`
  within it, and partitions output as `<root>/<save_id>/<sim_date>/<ingest_seq>/`. Refuses
  rather than rendering an empty page, naming the dates the warehouse *does* hold.
- `roster.py` — the report. Drives from `bronze_player.organization_id`, joins the roster
  rows on, groups each list by club, and derives every stated figure from the rows in hand.
- `__main__.py` — `uv run python -m ootp_ai.reports render`, with `--save-id`/`--sim-date`.
- `__init__.py`.

**Tests** — `tests/test_report_rendering.py` (offline, the pure half), `tests/test_reports.py`
(`-m gamedata`, AC14), `tests/fixtures/reports.py` (the shared name pattern, so CI guards it).

**Modified** — `src/ootp_ai/config.py` (two new refusals), `tests/test_config.py`,
`tests/test_no_leaks.py`, `tests/test_read_only.py`.

## 3. Deviations from the plan

1. **`standings.py` was not built.** Retired by dated amendment in both artifacts. No
   declared table carries wins, losses, games played or pct: the standings region is not in
   `teams.dat` and `world.dat` yielded divisions and the calendar. The plan's "all 259
   `team_record` rows are 0-0-0" cites the **export's** table, never landed — which is what
   made the step look satisfiable. **Root cause recorded:** plan line 324 assigned the
   win-loss fields to Phase 5, and Phase 5's acceptance never asserted them.
2. **`resolve.py` added.** The plan gave `__main__.py`, `roster.py`, `standings.py` and
   assumed each report carried its own snapshot resolution. Splitting it out is the seam
   Phase 11's catalog reuses and the one a compare-two-dates report would hook into.
3. **`test_report_rendering.py` and `fixtures/reports.py` added.** §4.1's argument, third
   instance after 8b and 9: `test_reports.py` is entirely `gamedata`, so the gate, the
   grouping, the absence markers, the handedness mapping and AC14's own name pattern would
   have had zero CI signal.
4. **The name regex widened to Unicode** — carried in the same amendment, because the
   pattern is quoted verbatim in AC14.
5. **Every roster list is grouped by club.** Rendered flat, the first run announced *"Active
   roster — 213"* for a club whose active roster holds 26. Arithmetically right, and a
   plain falsehood as English.
6. **`tests/test_read_only.py`'s write allowlist was narrowed, not widened.** It matched
   `path.name`, so allowlisting `__main__.py` would have released *every* `__main__.py` —
   including Phase 11's `catalog/__main__.py`. It now matches package-relative paths.

## 4. Verification & edge cases

**Executed, not asserted.** Offline **586 passed**; gamedata **164, 1 named skip**; ruff,
format and mypy clean. The report was re-rendered end to end after every fix.

**One guard was seen to fail before being trusted.** `check_renderable` was temporarily
narrowed to `columns[:1]`: the last-position test went red while the naive same-column test
stayed **green**, which is exactly why the last-position arrangement earns its place.
Reverted.

**Edge cases exercised offline:** a player on two clubs' lists appears under both; a player
on no list is named rather than dropped; `None` age/bats/throws/number render as `—` and
never `0`; an unresolved name renders as `—` rather than as its id; an unmapped handedness
integer renders as itself rather than as a letter; a club the landing does not name sorts
last rather than raising; a downgraded `roster_membership` takes the SD-17 fallback while a
downgraded `age` aborts; a second `ingest_seq` and a later `sim_date` each write a distinct
directory.

**Informal check the plan asks for:** read by eye. Devers #11 L/R, Story #10, Casas #36 L/R,
Yoshida #7 L/R, Jansen #74 S/R, Duran #16, Bello #66, Houck #89. Boston's 26 active + 7
injured = 33 assigned, which reconciles.

## 5. Findings resolved

Panel: 6/6 reviewers, 5/5 verifiers, **0 findings unverified**, no degraded lenses, 1
blocker + 7 majors confirmed, one finding refuted by mutation testing and dropped. Full
detail in `reviews/phase-10-acceptance-panel.md`. Summary of the majors:

- **The serving gate was not exhaustive and its docstring said it was** — five values
  reached the page ungated, and a simulated downgrade of `roster_membership` left
  `check_renderable` passing while the page kept printing "Active roster". SD-17's fallback
  was documented as honoured and unreachable. Fixed: 16 gated columns, congruence asserted
  both ways, `list_label_mode()` implements the fallback and a test drives it end to end.
- **The name join bound 4 of `bronze_name`'s 5 key columns** — measured 4x fan-out (904
  rows for 226 players) with a second name space. Fixed, with offline coverage.
- **The page printed "Measured, 935 players span two clubs"** — the probe save's global
  figure, wrong here by ~27x, in the `Measured` register, under the page's own promise that
  every figure is from this snapshot. **The test asserted `"935" in page`**, protecting the
  error. Both figures now computed; the page reads *"1 of this organisation's 226 players"*.
- **The output root was not fenced** against the game directories or against a tracked
  in-repo path. Both fences added at config time, with offline tests both ways.
- **`_tracked_under()` raised** on an out-of-repo output root — a supported, safer
  configuration. Fixed.

## 6. Manual gates & user-run steps

- **AC20 / AC21 are Phase 13's and remain open** — the GM-subagent handoff and the
  by-hand file-set check.
- **Nothing outward-facing was run.** No push, no merge, no PR.

## 7. Hand-off

Next: **`/commit`** (which runs `/update-docs` — `CLAUDE.md`'s Status still says *"Phase 10
is the two reports"* and *"the GM still cannot see its own club"*, and `README.md` does not
know `reports/` exists). Then the PR is the operator's.

**Follow-ups this phase surfaced, none filed yet:**

1. **Incremental loading across sim dates** — raised by the operator before the panel ran.
   `test_a_landing_at_another_sim_date_is_left_untouched` *finds* a second date
   opportunistically and skips loudly when absent; no test lands one league at two dates,
   and nothing reads across snapshots. **Agreed to file after this commits.**
2. **A team-record source** — what S0's amendment owes. `world.dat`'s unmapped per-league
   blocks are the candidate; pairs with `league-dimension`, already at intake for the same
   blocks.
3. **The stray-probe hazard** — an interrupted run leaves a probe file that reddens a later
   unrelated run. Phase 9 raised it as CF24 and it is still unfiled; the Phase 10 panel hit
   it again, as a spurious `test_no_fixed_offsets` red from a concurrent lens.
4. **`render()` inside the ADR 0001 manifest-diff window** — the runtime proof brackets
   `ingest_save` and `parse_snapshot` only, so the project's second file writer is covered
   by the static allowlist alone.
5. **The GM tool-grant guard test** — Phase 13 already owes this one.

---

# Phase 11 — the generated catalog and its tracked/volatile split

> **One-line outcome:** the GM can read what the warehouse holds **and what was deliberately
> withheld and why** · **Acceptance:** AC15 met on all seven clauses after the panel's fixes;
> AC16 re-proved with no game install and no MySQL · **Branch:** `implement/first-sight-phase-11`

**Phase 11 of 14.** Phases 12 (doc truth-up, the dbt deferral) and 13 (USER-RUN acceptance)
remain, so AC18's doc reconciliation and AC19–AC21 stay open and the request stays `planned`.

## 1. Acceptance ledger

| Criterion | Verdict | Evidence |
|---|---|---|
| **AC15-a** `uv run python -m ootp_ai.catalog` regenerates the catalog, no subcommand | met | `--help` shows `[-h] [--save-id] [--sim-date] [--docs-root] [--structure-only]`; the real run wrote 4 files, exit 0 |
| **AC15-b** structural section regenerated in-test, byte-identical to the committed copy | met | `test_the_tracked_markdown_is_exactly_what_the_generator_produces` compares `read_bytes()` against a live render; green |
| **AC15-c** proving it cannot be hand-edited into drift | met | **Seen to fail.** One character flipped in `docs/warehouse-catalog.md` → red, `At index 432 diff: b'G' != b'g'`; reverted → green. Also staged as `test_the_comparison_can_actually_fail` |
| **AC15-d** every landed table with grain, key, coverage, row count, source `.dat`, label, snapshot date | met | `test_every_landed_table_carries_its_row_count_and_snapshot_date`, green under `-m gamedata` against the real landing |
| **AC15-e** withheld groups listed with reason and ADR | met | Both groups render with a redaction-bounded reason and their ADRs. **The `players.prone_*` / `players_value.*` half was retired by dated amendment** — see §3 |
| **AC15-f** no player-level value, no rating column name, anywhere in it | met | Name scan now covers the **whole** landed population (22,046 two-token display names) not a `LIMIT 500` window, and every `player_id ≥ 10,000`; rating scan covers all four files by three predicates |
| **AC15-g** regenerating twice is byte-identical | met | Two full runs, SHA-256 on all four files: identical. The test no longer compares a file with itself |
| **AC15-h** coverage statement prices the players no roster list holds | met | Page states **12,426**, recomputed independently by the test. The plan's ~10,700 was the *probe's* figure — computing rather than remembering is what caught it |
| **AC16** offline suite with no game and no MySQL; ruff, format, mypy clean | met | Re-run with `OOTP_INSTALL` unresolvable and MySQL on a closed port: `ConfigError: OOTP_INSTALL does not name an existing directory`, suite exit 0. The meta-audit was right that nobody had checked this |
| **AC11** ADR 0001 read-only guard, re-run for this phase | met | `pytest tests/test_read_only.py -m gamedata` exit 0 — mandatory per phase because this diff widens the write allowlist |
| **AC17** catalog carries the extraction cost | met | Generated half renders `**Parse cost** — 2.236 s`, read from the `ingest_run` row |
| **AC18–AC21** | not this phase | Phases 12–13; AC20/AC21 are USER-RUN and the panel must not claim them |

## 2. What shipped

- `src/ootp_ai/catalog/` — `__init__.py`, `structure.py` (pure over the declarations),
  `volume.py` (the only half needing a connection), `render.py` (one renderer, both halves),
  `__main__.py` (the only writer).
- `docs/warehouse-catalog.md` + `.json` — generated, tracked, byte-deterministic.
- `tests/test_catalog.py` — 24 offline, 9 `gamedata`. Main-thread-authored: `tests/` is in
  the builder's deny set.
- `tests/test_repo_structure.py` — `docs/warehouse-catalog.md` joins the required-docs list
  **in this commit, not one earlier**, per the plan's load-bearing sequencing note.
- `tests/test_read_only.py` — `catalog/__main__.py` joins the writer allowlist.
- `src/ootp_ai/config.py` — `reject_inside_game_roots` factored out of `_root`.
- `CLAUDE.md` — two map lines; the Status rewrite stays Phase 12's.

## 3. Deviations from the plan

1. **`generate.py` became `structure.py` / `volume.py` / `render.py`.** Load-bearing, not
   cosmetic: it is what lets `--structure-only` run with no `.env`, no save and no database.
   Plan checklist amended at `IMPLEMENTATION_PLAN.md`, following the `resolve.py` precedent.
2. **`information_schema` supplies existence, not counts.** The plan says "reads
   `information_schema` for counts"; `TABLE_ROWS` is an InnoDB *estimate* and counts every
   landing rather than one triple. Counts are `COUNT(*)` scoped to the resolved triple.
3. **The withheld section names no rating-category field, and no `players.prone_*` /
   `players_value.*`.** AC15 and Core §14 cannot both be satisfied. Recorded as a dated
   amendment under Core §14 in `PROJECT_SCOPE.md` rather than resolved in silence — which is
   what the first implementation did, and what the panel caught.
4. **Players-with-no-roster-row uses `NOT EXISTS`**, not the plan's sketched subtraction: the
   subtraction assumes every roster row names a player the same landing holds.
5. **`--structure-only` added.** Not in the plan's steps. Without it, a contributor with no
   MySQL cannot regenerate the file CI now requires to exist.

## 4. Verification & edge cases

Everything below was **run**, not asserted. Offline suite 611 tests exit 0; catalog
`gamedata` 9 tests exit 0; ruff, ruff format, mypy clean; `test_read_only.py -m gamedata`
exit 0; determinism confirmed by SHA-256 across two full generator runs.

Edge cases now covered that were not: a declared table this landing did not write (renders
"not landed by this run", never a zero); a `--docs-root` inside the game (refused, writes
nothing); a decoded rating name (caught by category *and* by shape); the two Markdown halves
sharing a basename (addressed by role, not by `path.name`).

## 5. Findings resolved

All 13 panel findings were confirmed by independent verification; 10 were major. Every one
is fixed. Full detail in `reviews/phase-11-acceptance-panel.md`.

| ID | What was wrong | Fix |
|---|---|---|
| CF-01 | *"78 of 89 declared fields reach a page"* was false by 23 — `served` counted policy-renderable, never asking whether a column claimed the field. On the artifact whose job is showing the GM its blind spots, and erring toward understating them | Three states — served (55), withheld (11), unexposed (23) — summing to 89, asserted by a test that re-derives them |
| CF-02 | The player-value guard sampled 500 consecutive names from one alphabetical band (0.2%), while 29 real landed names appear verbatim on the page — near-blind *and* one window-shift from a false red | Whole population, two-token display names, via `name_join_predicate` |
| CF-03 | The tracked half declared it carries no row counts, then printed 15 stale ones from `tables.toml` coverage prose | Claim corrected to *"no figure on this page is computed from a landing"*, with the historical numbers signposted |
| CF-04 | The withheld section could never name `players.prone_*` / `players_value.*`; the unbuildable contract was resolved in silence | Dated amendment under Core §14 |
| CF-05 | The rating guard shared its predicate with the redactor it audits. Injection proved `batting_ratings_contact` renders green — and the suite would then **require** its publication | Structural rule (rating-category fields counted, never named) + `RATING_NAME_PATTERN` as an independent backstop; the requiring test reconciled |
| CF-06 | `--docs-root` was an unvalidated write root — the only one not fenced against the game (ADR 0001) | `reject_inside_game_roots`, one function, two callers, with a test that sees the refusal fire |
| CF-07 | The GM's copy stated 10,700 and 12,426 for one population under a header promising every figure is this landing | Header scoped to *computed* figures; coverage prose relabelled "as declared" |
| CF-08 | The regenerate-twice test compared a file with itself — two runs writing different bytes still passed | Bytes captured before the second run overwrites them |
| CF-09 | Landed-ness came from schema existence, so a historical landing rendered structural absence as **zero** — this project's cardinal sin | Derived from `ingest_run.table_row_counts` |
| CF-10 | The rating scan never ran against the GM's copy or `catalog.json` | Shared `assert_no_rating_name` over all four files |

**Found while fixing, not by the panel:** the new name query omitted `name_space` from its
join — the exact defect `reports/roster.py:name_join_predicate` documents. Correct today only
because one name space is landed, and it made the query unable to use the primary key: it had
not finished in ten minutes. Using the documented predicate returns in 0.25 s.

## 6. Manual gates & user-run steps

- **AC20 / AC21 remain Phase 13's** and are the operator's. The spawn contract this phase
  adds to the tracked catalog is what makes AC20 reproducible.
- Nothing outward-facing was run. No push, no merge, no PR.

## 7. Hand-off

`/commit` next. Follow-ups this phase surfaced or inherits:

1. **The stray-probe hazard is now three-for-three unfiled** — Phase 9 raised it as CF24,
   Phase 10 recorded it as follow-up 3, and the Phase 11 panel hit it twice more as CF-19.
   It reddens `test_no_fixed_offsets` on a phantom file. It needs a bugfix request.
2. **Landing ratings vs. withholding them** — the operator raised whether the withhold-at-
   parse posture is paying for itself, given that `open-front-office` Phase B already scopes
   a `gm_view` schema + restricted grant built **from** `column_disposition`. Re-evaluate
   after this lands. Note the spike verdict (`reviews/spike-scouted-view.md`): the *scouted*
   view is `stored` and `measured` in `scouting.dat` — so the GM's legitimate ratings are
   blocked by an unparsed file, not by ADR 0012.
3. **`render()` and now the catalog sit outside the ADR 0001 manifest-diff window** —
   inherited from Phase 10, and this phase adds a second writer covered by the static
   allowlist alone.
