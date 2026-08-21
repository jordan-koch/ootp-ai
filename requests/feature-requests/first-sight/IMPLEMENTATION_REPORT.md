> **Status:** planned · created 2026-08-20 · decided · next: implement (Phase 11)

# Implementation Report — First sight, Phase 10: the roster report

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
