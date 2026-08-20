# Acceptance panel — first-sight Phase 9 (the differential harness, the extraction cost)

Run 2026-08-19 against the uncommitted Phase 9 tree, on branch
`implement/first-sight-phase-9` at HEAD `d34a006`.

## Panel health — no degradation

| Metric | Value |
|---|---|
| `reviewers_ok` / total | 6 / 6 |
| `verifiers_ok` / total | 5 / 5 (4 batches + the independent ledger verifier) |
| `findings_unverified` | **0** |
| `meta_ok` | 1 |
| `degraded_lenses` | *(empty)* |
| `findings_blocker_major` raw → deduped | 9 → 9 |
| blockers / majors | **0** / 6 |
| criteria met / unmet / unverifiable | 24 / 7 / 2 |
| verdict | `fix` |

Roster: `acceptance`, `fidelity`, `correctness`, `edgecases`, `parser`, `warehouse`.
1.77M subagent tokens, 512 tool calls, ~64 min wall clock.

**Nothing was refuted.** All seven blocker/major findings put to the verifier were confirmed.

## What the panel confirmed by execution, not assertion

- **Five independent reproductions of the headline.** Four lenses *and* the verifier each ran
  `-m gamedata tests/test_parser_vs_export.py` green; two additionally drove `diff_snapshot()`
  by hand against the live `ootp_dev` / `ootp_truth_real` pair and read the real output —
  259 teams × 15 columns, 18,072 players × 18, 15,672 roster rows, 3,058 calendar rows,
  30 division memberships, `clean: True`, `failures: ()`.
- It re-ran the offline gate: `511 passed`, ruff clean, mypy clean over 67 files.
- **The corrupt-and-revert demonstration really was reverted** — `git status --porcelain`
  shows nothing under `src/ootp_ai/parser/`.
- ADR checks: the new package reads no bytes and issues only `SELECT`s; the offline fixtures
  are invented (Springfield / Isotopes) rather than OOTP data; every identifier in
  `validate/` is quoted; no machine path in the new files.

**One finding was corrected rather than refuted.** The warehouse lens illustrated CF3 by
deleting `ColumnPair("park_id", …)` and claiming the suite stays green. It does not — a
fixture incidentally names `park_id`. The verifier re-ran the experiment with `nation_id`
and `weight` and got **0 failures** each, so the mechanism stands exactly as claimed and only
the illustration moved.

## The meta-audit caught a wrong `Measured` number that no lens raised

Three new sites stated *"keying the export's eight columns collapses 3,058 rows to 2,600, so
458 are genuine duplicates"*. Re-measured by the verifier, then independently by the
main thread before accepting it:

```
total rows: 3058
8-column key -> distinct: 2733  surplus: 325
4-column key -> distinct: 2600  surplus: 458
```

The 2,600 / 458 pair is **correct for the four-column key** `(league_id, start_date, type,
name)` — the Phase 5b grain argument, which is right where it stands. Phase 9 carried a true
number across to a different key. The multiset *decision* is unaffected (325 duplicates still
cancel under set semantics) and nothing executable depended on the figure — but a wrong
number labelled `Measured`, in the one phase whose thesis is that measured claims in tracked
files are true, is exactly the defect this harness exists to catch. Corrected at all sites,
with both keys and both figures now named so the transposition cannot recur.

## Confirmed findings and their dispositions

| # | Severity | Finding | Disposition |
|---|---|---|---|
| CF1 | major | **`diff_snapshot` never called `check_provenance`.** AC6, plan step 2 and two docstrings all say provenance is asserted before any value comparison; the public entry point did not do it. Verified behaviourally — an AST walk of the body and a stubbed run both showed zero calls against 10 SQL statements issued. The guarantee held only because one test sat above the others in one file, and the handoff hands Phase 10's render gate exactly this entry point | **Fixed**: `human_team_id` parameter added and `check_provenance` called as the first statement. A gamedata test drives the entry point with a wrong club and requires `ProvenanceMismatch` |
| CF2 | major | **`compare_keyed` reported CLEAN when a walk lost EVERY parsed-only row.** The report was built by iterating rows that were not there, so `parsed_only = 5` with zero extras produced an empty tuple and `clean = True`. The only counter-check was `-m gamedata`, which CI never runs | **Fixed**: the count discrepancy is now a fault in its own right, in both directions, with the wording *"fewer is as informative as more"*. Offline test added |
| CF3 | major | **The declaration cross-check ran one direction only.** Every guard enumerated *from* the harness, so deleting a `ColumnPair` narrowed AC6 with nothing going red — proven by deleting `bronze_team.nation_id` and `bronze_player.weight` in-process, 0 failures each, while `field_map.toml` still claimed `export-exact-all-rows`. This phase's own headline discovery (`team_historical_id`) is proof the link drifts silently | **Fixed**: `test_every_export_validated_field_is_actually_compared_by_something` enumerates from the contracts side; seven exemptions in `PROVED_ELSEWHERE`, each naming the artifact that earns it, plus a test that no exemption is stale |
| CF4 | major | **A `Measured` duplicate figure misattributed at three sites** (see above) | **Fixed** at all three plus `IMPLEMENTATION_PLAN.md:1002`; both keys now named with their own figures. Line 373's four-column claim was already right and was left alone |
| CF5 | major | **`PROJECT_SCOPE.md` AC6 was never amended** — the contract of record still asserts "15 leagues" and "18,072 active players" in the present tense after the phase measured both wrong. Breaks the in-place-amendment precedent the same document uses at AC8 and AC12. Compounding: the plan's justifying sentence *"a separate request with an owner"* is untrue — no such request exists | **GATED to the operator.** Both existing amendments say "at the operator's direction"; an acceptance contract the builder edits to match its own output is not a contract |
| CF6 | major | **Plan step 8's docs-delta was not prepared.** Twelve `##` headings in the handoff and none is `docs-delta`; `git status --porcelain docs` empty. The phase earned one, and the commit note binds it to the same unit of work | **Fixed**: a full `## docs-delta` section, each entry naming the test that earned it, including the three upgrades considered and **declined** so Phase 12 does not re-open them |
| CF7 | minor | **`export_rows` was declared on every spec and read by no production code** — and `DIVISION_SPEC`'s value was already wrong (30, our landed count, where the export returns 34). A lens demonstrated the vacuity live: `compare_rows` over an empty fetch against a spec pinning 15,672 returned clean | **Fixed by enforcing rather than deleting**, which also gives the offline suite an anti-narrowing signal it did not have. `DIVISION_EXPORT_CLUBS = 34` added as a distinct constant |
| CF8 | minor | **One shared `allowed` counter judged every whole-row rule against the sum**, so two rules of population 1 matching one row each would both report 2 and turn a correct run red. Mirror gap: a whole-row rule on a keyed table could never match a column, so its population was never checked at all | **Fixed**: per-rule tallies, rows claimed by two rules reported, orphaned rules named, and the whole-row predicate narrowed to the one side it can see |
| CF9 | minor | **The "no rating is compared" guard blocked `rating-true` but not `rating-scouted`** — the dangerous half, since the export's ratings are scale-converted *and* scout-filtered | **Fixed**: imports `policy.RATING_CATEGORIES`, so a third rating category is covered automatically |
| CF10 | minor | **The keyed fetch collapsed duplicate keys silently** while the row-set path reports them. The export side is not ours and carries no uniqueness guarantee, so a duplicate would present as a short population — the right symptom, the wrong problem | **Fixed**: `_key_by` raises `DuplicateKeys` naming the repeated values |
| CF11 | minor | **Three of five tables emitted no per-column output**, so a clean `bronze_league_event` line was indistinguishable from one whose eight columns were never in scope — and the test that checks the report iterated only `SPECS` | **Fixed**: row specs emit one `ColumnResult` per column; `describe()` states the suppression count; the test iterates all specs |
| CF12 | minor | **Four ad-hoc queries in the test module used bare identifiers**, including `name` — a MySQL keyword — in the very module that demonstrates the collision | **Fixed**: all four route through `quote_ident` / `column_list`; the deliberately-bare `current_date` is commented as the one exception |
| CF13 | minor | **The five parser-only players were pinned by count, not identity.** Five lost and five invented also totals five | **Fixed**: `PARSED_ONLY_PLAYER_IDS`, asserted as a set; the ids were already public in `docs/data-access.md` |
| CF14 | minor | `RowSpec.fields` paired to columns by unenforced position, and the docstring was already false for the roster spec (3 columns → 1 field) | **Fixed**: set-equality test against what the columns resolve to |
| CF15 | minor | **AC11's read-only proof never exercised `truth_save`**, which Phase 9 makes a routinely parsed save | **Fixed**: a third leg between the probe and the managed league, skipped by name when unset |
| CF16 | minor | The nullable `bronze_league_event.start_date` path has zero coverage and no named rule | **Fixed**: the measured zero is now pinned as a stated fact rather than a silence |
| CF17 + CF18 | minor | `CLAUDE.md`'s map and `README.md`'s status do not know `validate/` exists; `docs/data-access.md` under-claims what the differential proved | **Carried into `/update-docs`**, which owns both; recorded in the handoff's docs-delta |
| CF19 | nit | `field_map.toml`'s `[meta].phase` still read "Phase 8a" | **Fixed**, with a comment saying what the key records |
| CF20 | nit | A subsumed assertion in the offline corruption test could not fail (`"2" in ...` satisfied by the key) | **Fixed**: distinctive export value, asserts the rendered pair |
| CF21 | nit | Docstring said "six bronze tables"; the assertion names five | **Fixed**, and names why `bronze_name` is the sixth and excluded |
| CF22 | nit | "Probe" named two different saves — the `PROBE_*` constants described the one `.env` calls `OOTP_TRUTH_LEAGUE` | **Fixed**: renamed `TRUTH_SAVE_*` throughout |
| CF23 | nit | No way to run the differential outside pytest; the handoff quoted a transcript no committed code produces | **Partly fixed**: the block is labelled and the reproduction command named. A `__main__` is **declined** — Phase 10 owns the CLI, the same call the operator made in Phase 8b |
| CF24 | nit | An interrupted pytest run leaves a leak-guard probe at the repo root and reddens the next run elsewhere | **Carried** — out of scope, worth a bugfix request |
| CF25 | question | `bronze_league_event.seq` is a key column with no oracle, so a permuted walk passes AC6 | **Answered in code**: a gamedata test pins that `seq` is unique and contiguous — the self-consistency available without an oracle — and the limit is stated |

## Post-fix verification

`ruff check` / `ruff format --check` / `mypy` clean over 67 files.
**Offline 520 passed** (511 at panel time, 481 after Phase 8b).
**Gamedata 153 passed, 1 skipped** — the skip is `test_byte_accounting.py`'s strict-tier
assertion, named and expected.

The differential was re-run end to end after every fix and is clean, with a materially better
report: all five tables now itemise their compared columns, and the four suppressed all-star
sides are stated rather than left as 34 minus 30.

## Carried, not fixed

- **CF5** — the `PROJECT_SCOPE.md` AC6 amendment and the unowned league-dimension gap.
  **Operator's call**; both existing amendments in that file were made at their direction.
- **CF17 / CF18** — `CLAUDE.md`, `README.md` and `docs/data-access.md`, owned by
  `/update-docs` inside the `/commit` gate. Must not land uncorrected.
- **CF24** — the leak-guard probe file, worth its own bugfix request.
- **AC17 is `partial` and stays that way**: its text names the ingest-run row *and the
  catalog*, and the catalog is Phase 11. Not a Phase 9 defect, and the wording is left alone
  deliberately so the reminder survives.
