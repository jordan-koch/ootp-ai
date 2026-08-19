# Acceptance panel — first-sight Phase 8b (bronze landing, the ingest run, the first ingest)

Run 2026-08-19 against the uncommitted Phase 8b tree, on branch
`first-sight-phase-8b-bronze-landing` at HEAD `c71c8da`.

## Panel health — no degradation

| Metric | Value |
|---|---|
| `reviewers_ok` / total | 6 / 6 |
| `verifiers_ok` / total | 5 / 5 (4 batches + the independent ledger verifier) |
| `findings_unverified` | **0** |
| `meta_ok` | 1 |
| `degraded_lenses` | *(empty)* |
| `findings_blocker_major` raw → deduped | 14 → 14 |
| blockers / majors | **0** / 6 |
| criteria met / unmet / partial / unverifiable | 20 / 12 / — / 2 |
| verdict | `fix` |

Roster: `acceptance`, `fidelity`, `correctness`, `edgecases`, `parser`, `warehouse`.
2.02M subagent tokens, 595 tool calls, ~91 min wall clock.

**Most unmet criteria belong to Phases 9–12.** AC6, AC14, AC15, AC19 and AC18's second half
are not yet due and none counts against this phase.

## What the panel confirmed by execution, not assertion

- It re-ran the gate: `458 passed` offline, ruff clean, mypy clean over 62 files.
- It read the live schema: eight tables and nothing else; every `information_schema`
  PRIMARY index tuple equal to its declared key; `COUNT(*) == COUNT(DISTINCT key)` on all
  eight.
- It verified the roster grain on landed rows — 20,016 rows over 9,620 distinct players
  against 22,046 players — so AC5's non-collapse is a measurement, not an inference.
- ADR 0001 and ADR 0006 checked structurally: no code path writes a save, no game data
  tracked, no machine path in the new files.

**One major was downgraded on evidence rather than accepted.** The fidelity lens raised the
landing deadlock as a **blocker**, claiming landings fail "roughly one in three" and the
pipeline is "materially broken". The independent verifier refuted the *rationale*:
`PROCESSLIST` sampling caught a second client inserting into `bronze_name` concurrently —
other review agents sharing the dev warehouse — and a single-connection landing loop never
failed. The defect is real and is fixed below; the blocker framing was not supported.

## Confirmed findings and their dispositions

| # | Severity | Finding | Disposition |
|---|---|---|---|
| CF-01 | major | **A date-less calendar event aborted the entire ingest.** `parser/world.py` accepts `year == 0` for a calendar record *on purpose* — "a calendar record with no date is structural absence" — while `as_sql_date` refused it, on a docstring that reasons only about key columns, applied to two columns that are in no key. Zero statements issued: the abort happened before the transaction opened. `start_date` was also declared `null = false`, so a corrected loader still had nowhere to put it | **Fixed**: `nullable_sql_date` added and routed to `start_date`; `as_sql_date` kept for the three key sites with its reasoning now true of where it is used; the declaration is nullable with the world.py citation. Two offline tests pin both halves |
| CF-02 | major | **The landing gate the parser delegates to was never built.** `parser/players.py` says a nonzero `undecoded_tails` "means the format changed and the landing gate must refuse, not guess" — Phase 8b *is* the landing gate, and a grep of `warehouse/` and `ingest.py` for the name returned nothing. Driven directly, a degraded snapshot **committed cleanly** | **Fixed**: `ingest.check_decoded` raises `UndecodedRecords` before any row is built. Posture operator-disposed 2026-08-19: **hard refuse**, no soft-landing column |
| CF-03 | major | **All eight tables were keyed on `teams.dat`'s sim date**, with the other four walkers' own dates read and discarded. Proven reachable: swapping another save's `names.dat` and `world.dat` in produced no exception, and 264,095 name rows would have landed under a date that does not describe them. `parser/rosters.py` already refuses the teams↔players case for this exact reason | **Fixed**: `ingest.check_sim_dates` compares all four against the manifest and names every disagreeing file and both dates. Two offline tests |
| CF-04 | major | **The concurrency contract was misdescribed and unhandled.** The docstring claimed `FOR UPDATE` makes a second allocator block; two controlled experiments measured the opposite — both transactions allocated seq 1 in 0.000 s, and the loser failed on the INSERT with 1213. No 1213/1205/retry handling existed anywhere in `warehouse/`, so any contention cost a multi-second landing | **Fixed both halves**: the docstring now says what holds (the primary key is the guarantee; gap locks are mutually compatible), and `land_snapshot` retries 1213/1205 three times with a re-allocated sequence, raising `ConcurrentLandingError` — never `IngestRunExists`. Two offline tests |
| CF-05 | major | **The phase handoff was never written**, and two shipped files cited it. `ingest.py` carried the sentence "The measurement is in the phase handoff" — a dangling citation to a document that did not exist, which `test_doc_links.py` cannot catch because it is prose. Every prior phase produced one | **Fixed**: `reviews/handoff-phase-8b.md`, carrying both `ingest_run` rows read back, the step-6 measurement, the seam decision and the deviations |
| CF-06 | major | **Two files new in this diff asserted `teams.dat` is walked strict-tier**; `parser/teams.py` declares `diagnostic` and the landed residual is 2,274 / 1,137. Introduced *by the change that corrected four analogous statements elsewhere* | **Fixed** in all three places including the pre-existing copy in `tables.toml` |
| CF-07 | minor | AC12 required strict byte accounting for `teams.dat` against a walker that declares diagnostic, with no amendment connecting them | **Fixed**: dated amendment added to `PROJECT_SCOPE.md` AC12, operator-disposed |
| CF-09 + MA-01 | nit + major | **Two coverage statements were left stale in the edit that corrected four others** — `tables.toml`'s division table and `load.py`'s own module docstring. The meta-audit caught the second, which CF-09's single-line fix would have missed | **Fixed both**: the division coverage names both denominators; `load.py` now states no populations at all and points at the declaration, which is the pattern the rest of the repo follows |
| CF-10 | minor | **The gamedata structural-absence test was vacuous** — `SUM(bats IS NULL)` and `SUM(historical_id IS NULL)` are both 0 on every save, so two of its three assertions were `0 == 0` and would pass against a loader that coerced NULL to a default | **Fixed**: re-anchored on `bronze_team.city`, which genuinely lands NULL, with a guard that the population is non-empty and a `rows_landed > 0` check before the coercions |
| CF-11 | minor | AC10's second clause was substituted with two `ingest_seq` of one date and sold as *strictly harder*. The reasoning does not hold — two sequences and two dates each differ in exactly one key column | **Fixed**: the literal clause is now closed by `test_a_landing_at_another_sim_date_is_left_untouched`, and the docstring states the trade honestly |
| CF-12 | minor | **The row-count reconciliation was near-tautological**: `executemany`'s return compared against `len(rows)`, both derived from one Python list | **Fixed**: `_check_counts` runs a `COUNT(*)` per declared table inside the transaction, `ingest_run` included. Offline test drives an under-counting cursor |
| CF-14 | minor | **Append-only was asserted in three docstrings and enforced by nothing.** Every other load-bearing rule in this repo has a scanner | **Fixed**: an AST scan over `warehouse/` for mutating SQL at call sites, with four positive and five negative cases. It cried wolf on two docstrings on first run — the same failure the `historical_id` scanner learned — and now judges only string literals handed to a call |
| CF-15 + MA-02 | minor | Warehouse tests land ~300k rows into the schema holding the real ingest, cleaned by a `finally`; `purge_snapshot` swept every table in the schema and deleted `ingest_run` **last**, so an interrupted purge left a run row describing rows that were gone | **Mitigated** (separate test schema declined, operator-disposed): `ingest_run` is deleted first so an interruption leaves detectable orphans, and the sweep is scoped to the declared tables so future dbt models are untouched |
| CF-16 | nit | The run-row count assertion skipped `bronze_division_team` and `bronze_field_label` — the only two whose counts are not a `len()` of a walker tuple | **Fixed** |
| CF-17 | nit | `dump_parse` omitted `unrostered`, both declared record counts, `undecoded_tails`, `content_digest` and the world regions — walker outputs a nondeterministic walk could vary without the digest noticing | **Fixed**: a `diagnostics` block covers all of them |
| CF-18 | minor | `bronze_team_roster`'s coverage did not declare the **176 assigned-but-unrostered players** it drops — a different absence from the ~10,700 unassigned, and one a query for "who is in Boston's organisation" would silently miss | **Fixed** in the table's note, pointing at `bronze_player.organization_id` |
| CF-19 | nit | `fixtures/warehouse.__all__` omitted `save_or_skip`, which another module imports by name | **Fixed** |
| CF-20 | minor | AC11's read-only proof called only `ingest_save`, which this phase's own edit made explicit "stops there" — so the ADR 0001 guard ran a strictly smaller pipeline than the one that exists | **Fixed**: it now drives `parse_snapshot` between the manifests. Landing stays out deliberately — it writes to MySQL, not the game, and a warehouse outage must not silence this test |
| CF-21 | minor | `_describe` re-read all five files in full to look at 25 bytes of header — ~48 MB of avoidable I/O per ingest, *after* the timer stopped, so it never appeared in the number Phase 9 will decide from | **Fixed**: the loaded buffers are passed in; `parse_seconds`' docstring now states what the span covers |
| CF-22 | minor | Nothing asserted the **live** primary key equals the declared key, and `ensure_tables` deliberately never repairs a drifted table — so one created with a weaker key would stay wrong forever | **Fixed**: a gamedata test reads `information_schema.STATISTICS` and compares the ordered tuple |
| CF-23 | minor | `bronze_field_label` now persists `name_category` as `rating-true`, which it is not | **Documented**: the field-map entry records that the category is CLAUDE.md's withhold-by-default corollary doing duty, not a claim about the byte. Adding an `unclassified` category is a change to ADR 0012's posture and is carried, not made here |
| CF-24 | nit | Two test files were added outside the plan's §7 checklist | **Fixed**: both added with the §4.1 argument |
| CF-08 | minor | `CLAUDE.md` and `README.md` still say nothing is landed in the warehouse | **Carried into `/commit`**, which is where `/update-docs` — the gate that owns exactly this drift — runs. Must not land uncorrected |
| CF-13 | minor | No tracked entry point performs an ingest | **Deferred to Phase 10, operator-disposed.** The exact composition is recorded in the handoff so the first ingest is reproducible from a tracked artifact |

## Meta-audit — four findings, one of which caught a dropped major

1. **MA-01 (major): a dropped signal that mattered.** The `parser` lens raised
   `load.py:7-9` carrying the same stale-population error as CF-09, and it vanished from
   the merged report. CF-09's fix was scoped to one line in `tables.toml`, so a fixer
   working the merged report would have closed it and left the loader's docstring
   asserting probe populations as universal facts. **Both are fixed.**
2. **MA-02 (minor): a dropped purge-ordering fix.** `purge_snapshot` deleted `ingest_run`
   last, so an interrupted purge left precisely the lying provenance row `load.py` says
   must never exist. One-line fix, applied.
3. **MA-03 (minor): four cross-cutting ledger rows dropped**, including a `partial`.
   ADR 0001, ADR 0006 and the grain-uniqueness cross-check were each independently
   verified and survived only as prose. Recorded here so the positive evidence is
   attributable: no code path writes a save; nothing OOTP-owned is tracked;
   `COUNT(*) == COUNT(DISTINCT key)` holds on all eight tables with totals reconciling to
   the parser counts exactly.
4. **MA-04 (minor): the verdict rationale undercounted the majors**, naming three of five
   and omitting CF-04, CF-06 and CF-08's must-fix status. The triage above works from the
   findings array rather than the rationale.

## Post-fix verification

`ruff check` / `ruff format --check` / `mypy` clean over 62 files. **Offline 481 passed**
(up from 458 at panel time, 442 after Phase 8a). **Gamedata 131 passed, 1 skipped** — the
skip is `test_byte_accounting.py`'s strict-tier assertion, named and expected.

The schema was dropped and recreated from the corrected declaration and the first ingest
re-run, so the landed rows are the ones the amended contract describes. Zero calendar rows
carry a NULL `start_date` on the saves that exist — CF-01 was latent, which is why it
would have surfaced later rather than never.

## Carried, not fixed

- **CF-08** — the four stale status sentences in `CLAUDE.md` and `README.md`, owned by
  `/update-docs` inside the `/commit` gate.
- **CF-13** — no tracked ingest entry point (Phase 10).
- **CF-15** — warehouse tests share the development schema; mitigated, not isolated.
- **CF-23** — whether the category vocabulary should gain an `unclassified` member.
- **`ensure_tables` never repairs a drifted table** — the live-key guard now detects it,
  but the migration is undesigned.
- **`verify_snapshot` has no production caller**, so the digests in `ingest_run` are copied
  from the manifest rather than re-measured over the bytes the parse read.
