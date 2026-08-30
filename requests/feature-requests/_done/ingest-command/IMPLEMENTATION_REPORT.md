> **Status:** implemented · created 2026-08-30 · decided · next: commit

# Implementation Report — An ingest command: the pipeline has no way to be run

> **One-line outcome:** `uv run python -m ootp_ai.ingest land` takes a configured save
> from disk to a landed bronze snapshot and prints the `(save_id, sim_date, ingest_seq)`
> triple, so a fresh clone reaches a rendered roster without running `pytest` ·
> **Acceptance:** 19/19 criteria met — 17 agent-verified, 2 run by the operator
> 2026-08-30 · **Branch:** `file-ingest-command-request`

## 1. Acceptance ledger

**AC18 and AC19 are USER-RUN.** No agent may mark them; they were run by the operator on
2026-08-30 and are recorded below from their own output.

### Offline (CI) — 702 collected, 702 passed, 0 skipped

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| AC1 | `WRITERS` unchanged, asserted not eyeballed; both write guards pass with the new modules in `SRC.rglob` | **met** | `test_the_write_allowlist_did_not_widen` asserts the exact three-name set via a bare `from test_read_only import WRITERS`. `git diff -U0 tests/test_read_only.py` touches no line inside the `WRITERS` block |
| AC2 | argparse surface pinned; `main([])` **raises** `SystemExit(2)` | **met** | `parse_args(["land"]).command == "land"`; the four flags parse; `--sim-date`/`--snapshot-root`/`--ingest-seq`/`--force` each raise `SystemExit` (parametrised); `--from-snapshot` + `--new-look` exits 2 from the exclusive group |
| AC3 | Resolution refuses an unconfigured id **by name**; absent id → managed; a path is rejected | **met** | Four tests over `Settings` built through `load_settings(mapping)`; the message names every configured `save_id`; a filesystem path raises `UnknownSave`; `main(["land","--save-id","Nope"])` → 2 |
| AC4 | Formatter emits no absolute path; carries save_id, `YYYY-MM-DD`, seq, row counts; matches none of `PATTERNS` | **met** | Parametrised over both formats against `test_no_leaks.PATTERNS` **imported**, with a synthetic result carrying a real cwd-derived absolute snapshot path. Line one pinned: `landed Test-Save-Challenge-Mode 2024-03-07 ingest_seq 2` |
| AC5 | Refusal surface proved without a warehouse; `IngestRunExists` ≠ `ConcurrentLandingError` | **met** | Parametrised over `REFUSALS` **itself** (9 members), so a tenth added unhandled reds. The two lock-vs-landed messages asserted distinct. `ConfigError` → 2 |
| AC6 | **Both** callers route through the shared function behaviourally | **met** | One patch on `ootp_ai.ingest.read.read_save`. Command half: `land()` records exactly one call. **Fixture half: `landed_probe` records exactly one call.** Plus module identity: `vars(command)["read"] is read` |
| AC7 | `ensure_tables` called exactly once and **before** the save is read | **met** | One shared call-order log: `ensure_tables` count 1, index before `read_save`, `read_save` before `land_snapshot`, `close` last, and `commit` before `max_seq` |
| AC8 | README names the literal invocation and no longer says "There is no ingest command"; `resolve.py` names it too | **met** | `test_the_documented_invocation_names_a_command_that_exists` reads both files from disk and checks them against the command module's own `INVOCATION` constant |
| AC9 | ruff / ruff format / mypy strict green; `ingest.__all__` unchanged; ten import sites unedited | **met** | `ruff check .` clean · `ruff format --check .` 223 files · `mypy` 86 source files clean. `ingest.__all__` still 11 names; `git grep -l "from ootp_ai.ingest import"` = 10 files, none edited |

### Gamedata (probe only, SD-20) — 178 collected, 178 passed, 0 skipped

**Anti-vacuous:** every gate below ran with `-rs`, zero skips. `test_ingest_command.py`'s
gamedata half is 5 tests and passed **5/5 on five separate runs**, with a warehouse census
after each confirming `ingest_run` returned to its two legitimate landings every time.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| AC10 | The command's own success path returns 0 | **met** | `main(["land","--save-id",<probe>,"--new-look"])` → 0, triple parsed off stdout line one |
| AC11 | `read_ingest_run` finds the exact triple; `table_row_counts` **equal** `run.row_counts`; `bronze_player` holds that many | **met** | Driven through `land()` so the `LandingResult` is in hand — `main()` returns only an int and could never compare the middle clause. All three asserted |
| AC12 | A second invocation refuses, names the triple, and creates **no** directory and **no** row | **met** | Directory count identical before/after **and** the `ingest_run` census identical — the refusal fires before 52.4 MiB is copied |
| AC13 | Changed bytes at an unchanged sim date land with **no flag** | **met** | Simulated by moving the prior landing's digest, never by editing a save. Both sequences persist; `verdict: changed` asserted |
| AC14 | `--new-look` lands identical bytes at `previous + 1`; the first triple's `table_digest` unchanged | **met** | Per-table digest over all 8 declared tables either side, with an explicit read-view refresh between — without which the comparison is vacuous |
| AC15 | `--from-snapshot` re-lands without reading the game; a row appears; the output **states** the sequence relationship | **met** | Manifest diff over both game roots across the invocation → 0 differences. The sequence line is asserted **present**, naming the directory's number and which way the two went |
| AC16 | ADR 0001's proof brackets every game read; 4 manifest passes with truth configured; no MySQL | **met** | `test_a_full_run_touches_nothing_under_the_game_directories` green, **2:40** wall clock; `test_the_manifest_is_not_vacuous` green alongside |
| AC17 | Nothing regressed in the real `landed_probe` consumer set | **met** | `test_snapshot_semantics` · `test_grain_contracts` · `test_extraction_cost` · `test_parser_vs_export` — 40 passed, 0 skipped, including the `which="truth_save"` path |

### USER-RUN — run by the operator 2026-08-30

Both were run by the operator, not by an agent, and are recorded from their output.

**The empty schema needed no destruction to reach.** `ops/mysql-bootstrap.sql` creates
`ootp` — the production warehouse — alongside `ootp_dev`, and every landing to date had
gone to `ootp_dev`, so `ootp` held **0 tables**. Pointing one run at it with
`$env:MYSQL_DATABASE='ootp'` gave a genuinely virgin warehouse, needed no root, and left
the two real landings in `ootp_dev` untouched. The report's earlier claim that AC18 "cannot
be staged" was wrong, and so was the acceptance panel's — both assumed reaching an empty
schema meant dropping `ootp_dev`'s tables.

| # | Criterion | Verdict | Operator's evidence |
|---|---|---|---|
| AC18 | Fresh machine: `uv sync` → bootstrap → `ingest land` → `reports render` produces `roster.md`, `pytest` never invoked | **met** | `land --save-id Test-Save-Challenge-Mode` → exit 0, `landed Test-Save-Challenge-Mode 2024-03-18 ingest_seq 2`, and **`tables created:` naming all eight** — the command built the schema rather than assuming it. `reports render` → `var/reports/Test-Save-Challenge-Mode/2024-03-18/2/roster.md`, 25,050 bytes, 616 lines, resolving the sequence the ingest had just created. `pytest` invoked at no point |
| AC19 | The printed ingest output pasted into a scratch `.md` leaves `tests/test_no_leaks.py` green | **met** | The verbatim block written to `ac19-scratch.md` at the repo root (untracked, and the guard does scan untracked files); `uv run pytest tests/test_no_leaks.py -q -rs` → 6 passed, 0 skipped. Scratch file removed afterwards |

**AC18 also produced the first live instance of CF-11**, the divergence direction the
original `sequences_diverged` predicate could not detect. A snapshot directory for the probe
already sat at seq 1 on disk while `ootp` held nothing, so the filesystem allocated 2 and the
landed sequence *equalled* the directory number — making `ingest_seq != snapshot_dir_seq`
false. The widened predicate caught it and the command said so in terms:

```
sequence: snapshot directory 2, warehouse held 0 — landed 2. The filesystem was ahead
of the warehouse, so the landed sequence is gapped — this is not a lost landing.
```

Unfixed, the first operator run against a virgin warehouse would have landed at sequence 2
in silence, and the next reader applying ADR 0021's *"starting at 1"* would have had a
missing landing to account for. The panel rated it reachable in principle; it was reachable
on the first attempt.

## 2. What shipped

All seven phases, against the plan's §7 checklist. 10 files modified, 3 new.

| Phase | Landed |
|---|---|
| 1 | `ingest.py` → `ingest/__init__.py`, **byte-identical** (`rename (100%)`, `0 0` numstat); `read_sim_date` and `source_facts` published, `__all__` sorted |
| 2 | `ingest/read.py` — `read_save`, `PriorLanding`, `SaveReading`, `SaveUnchanged`, and the two pure comparison functions; `landed_probe` and AC11's three legs re-pointed onto it |
| 3 | `latest_landing` + `landed_max_seq` in `warehouse/ingest_run.py`, both lock-free, beside the `FOR UPDATE` allocator they contrast with; JSON decoding factored to one owner |
| 4–6 | `ingest/__main__.py` — `main`/`land`, `UnknownSave`, `LandingResult`, both formatters, the nine-member refusal tuple, the digest pre-flight, sequence reconciliation, `--from-snapshot` |
| 7 | README's gap blockquote retired and the invocation documented; `resolve.py` names a command that exists; CLAUDE.md Status + map; the `incremental-loading` boundary amendment; the stale "46 MB" corrected |

**Not touched, as the plan required:** `contracts/tables.toml`, `docs/warehouse-catalog.md`/`.json`,
`ops/mysql-bootstrap.sql`, `.env.example`, `[project.scripts]` (absent, stays absent), every
parser module. `git diff --stat` over the first three is empty.

## 3. Deviations from the plan

1. **Phases 4, 5 and 6 were implemented in one pass.** Phase 4's own spec requires writing
   the full `land()` body, so its two placeholders would have been written and deleted
   inside the same working-tree diff with no checkpoint between them. Each phase's
   acceptance criteria were still verified separately, and all are in §1.

2. **Per-phase `/commit` checkpoints were consolidated into one hand-off.** The plan ends
   each phase at a `/commit`; the `/implement-plan` skill's default is to accumulate one
   diff and run one panel. Took the skill's default.

3. **The plan's own Phase 1 sweep command is malformed.** `Select-String -Pattern … -Recurse`
   is not valid — `Select-String` has no `-Recurse`. Used the ripgrep-backed Grep tool,
   which works regardless of `rg` being off PATH. The sweep found exactly the 10 import
   sites the plan predicted.

4. **The plan's byte-exactness recipe reports a false mismatch.** `git show HEAD:… | git
   hash-object --stdin` piped through PowerShell re-encodes line endings, so the hashes
   differ for encoding reasons. `git diff --cached -M --numstat` → `0 0` and
   `rename (100%)` is the correct proof and is what §1 cites.

5. **Three prose mentions of `ingest.py` were left alone** — `tests/test_extraction_cost.py:25`,
   `src/ootp_ai/validate/export_diff.py:118`, `src/ootp_ai/parser/human_managers.py:114`.
   The plan anticipated only `data-engineer-memory.md:202`. All three are informal module
   references in comments; the last is in a parser module, which the plan's do-not-touch
   list forbids editing. Left as a follow-up rather than fixed inconsistently.

6. **`reason` was added to `SaveReading`, by operator disposition** — a plan amendment,
   recorded in `IMPLEMENTATION_PLAN.md` §5 (§5 of this report).

## 4. Verification & edge cases

**Every criterion in §1 was verified by execution**, and the acceptance panel independently
re-ran the offline suite and the quality gates.

| Gate | Result |
|---|---|
| `uv run pytest` (both markers) | **880 collected, 879 passed, 1 skipped** — the skip is `test_byte_accounting.py:123`, pre-existing and unrelated (the teams walk is declared diagnostic) |
| `uv run ruff check .` | clean |
| `uv run ruff format --check .` | 223 files formatted |
| `uv run mypy` (strict, src + tests) | 86 source files, clean |
| `-m gamedata tests/test_ingest_command.py` | **5/5 passed on five separate runs**, census clean after each |

**Measurements taken, with dates and labels** — the plan made three of these binding:

| What | Figure | Label |
|---|---|---|
| `verify_snapshot` over the landed snapshot (5 files, 54,938,202 B) | **52.7 / 30.4 / 28.5 ms** | `measured` 2026-08-30 — upgrades plan Decision 5 from `inferred` |
| AC11 manifest diff, before the added pre-flight leg | 2:42 | `measured` 2026-08-30 |
| AC11 manifest diff, **after** the added leg | **2:40** | `measured` 2026-08-30 |
| Allocator re-query (plan Phase 1 obligation) | 3 filesystem pairs; `OOTP-AI` fs 1 / wh 1, `Test-Save-Challenge-Mode` fs 1 / wh 1, `Test-Save-Standard-Mode` fs 1 / **no warehouse row** | `measured` 2026-08-30 — unchanged from the plan's table |

**On AC11's cost, the plan's prediction was wrong about magnitude.** It expected the legs to
get *cheaper* by dropping `ingest_save`'s ~48 MB re-read. That saving is ~0.25% of the
~19 GB this test hashes across three manifest passes, so it is far below run-to-run
variance: measured 2:42 against a 2m35s baseline taken 2026-08-16, and 2:40 after *adding*
a digest pass. The direction of the reasoning was sound; the effect is not observable, and
recording it as an improvement would have been recording noise as a result.

**Edge cases exercised:** a landing older than the 2026-08-16 `SNAPSHOT_FILES` widening
(names 3 files, not 5 → treated as changed); equal sizes escalating to the digest rather
than reporting unchanged; a same-size edit; a save byte-identical to its landing; a missing
in-scope file; a `--from-snapshot` directory with no manifest; an unreachable warehouse; a
`Settings` with both validation saves `None` (the fresh-clone shape); `--save-id` combined
with `--from-snapshot`.

## 5. Findings resolved

The acceptance panel ran **healthy** — 6/6 reviewers, 5/5 verify agents, meta-audit ok,
**0 findings left unverified**, no degraded lenses. It returned `fix` with 0 confirmed
blockers and 13 majors; its meta-audit then raised a blocker against the *synthesis*.

**The meta-audit was right, and it matters.** Three findings were raised at blocker
severity; the synthesis reported "TWO BLOCKERS WERE RAISED AND BOTH ARE REFUTED" while one
(V7) had been independently **confirmed**. Two verifiers had traced the gamedata flakiness
to a second agent session hitting the same schema — true, but not the whole cause. V7's
verifier recorded the datum that broke that story: *AC14 failed in isolation from one
warehouse state and passed from another*, with no concurrent session. That pointed at the
real defect.

| Finding | Resolution |
|---|---|
| **V7 (confirmed blocker)** — the plan's own Phase 5 gamedata gate was red on handover | **Fixed.** Root cause was mine: the first `main()` sat outside the `try:` whose `finally` purged, so any failure stranded a full landing — and a leaked row raises the warehouse maximum, moving the *next* run's sequence arithmetic under it. Replaced with a census-driven `_reclaiming` context manager that asks the warehouse what is actually there instead of trusting a triple parsed from stdout. **A stranded landing (`Test-Save-Challenge-Mode` 2024-03-18 seq 2) was found in `ootp_dev` and reclaimed — 18,077 rows.** Now 5/5 green across five runs with a clean census each time |
| CF-01 — AC6's fixture half never written | **Fixed.** `landed_probe` now drives the same single patch and records one call |
| CF-02 — AC15's sequence relationship stated only on divergence, guarded by an assertion that could not fail | **Fixed.** `sequence_line()` prints on every run; the test asserts the line is present, names the directory's number, and says which way the two went |
| CF-03 — an unreachable MySQL exits on a bare traceback | **Fixed.** `pymysql.err.Error` → exit 2 with a message naming `mysql-bootstrap.sql`. This is AC18's own first step |
| CF-04 — `source_facts`' game reads sit outside **both** ADR 0001 guards | **Fixed** (operator-disposed). AC11's probe leg now calls `read_save` a second time with a `PriorLanding` built from its own manifest, exercising the digest path inside the bracket. No new leg, no new manifest pass; 2:40 vs 2:42 |
| CF-05 / CF-13 — the gamedata tests leak a landing on failure and are not isolatable | **Fixed** — same `_reclaiming` change as V7 |
| CF-06 — the explicit `ingest_seq` forfeits the retry, and the code comment claimed it "never collides and never refuses" | **Fixed** (policy **kept**, operator-disposed). The false comment is replaced with the honest trade; a stale-read-view window before `landed_max_seq` was also closed with an explicit commit |
| CF-07 — Scope Core's "say why" computed and discarded | **Fixed** (operator-disposed, plan amended). `reason` flows through `SaveReading` → `LandingResult` → both formats and `JSON_KEYS`, null-never-absent |
| CF-08 — CLAUDE.md and three docstrings claim `read_save` is the only code that opens a game file; the scope **explicitly banned** that sentence | **Fixed.** Narrowed in all four places to the accurate form, naming `ingest_save`, `take_snapshot`, `read_sim_date`, `source_facts` and `saves.is_record_file` as the code that still does |
| CF-09 — no report, no ledger, three unrecorded measurements | **Fixed** — this document |
| CF-10 — `--new-look` reports `no-prior` on a save with prior landings | **Fixed.** `land()` supplies the intent; `LandingVerdict` is a closed typed set |
| CF-11 — divergence silent in the direction that is live on this machine | **Fixed.** The predicate now tests both allocators, and the gapped case has its own sentence |
| CF-14 — `--save-id` silently ignored with `--from-snapshot` | **Fixed** — refused with exit 2 |
| CF-15 — AC11's row-count clause and AC12's `ingest_run` clause stated but unasserted | **Fixed** — both now asserted |
| CF-16 — a missing in-scope file escapes as a bare `FileNotFoundError` | **Fixed** — raised as `SaveFormatError` naming the file |
| MA-3 — a Core scope must (`read_save`'s docstring names its three callers) audited by nobody | **Fixed** — the docstring now names all three and states that changing it changes what the operator's command does |
| **V8, V16 (refuted)** — "the reconciliation collides"; "the suite is intermittently red because of the implementation" | **Not carried.** Both were traced to a concurrent agent session plus the leak above; five clean runs after the fix. Recorded in `reviews/implementation-review.md` rather than dropped |

**Deliberately not fixed:** CF-12 (`latest_landing` keys on `save_id` alone) — plan Decision 1
chose this so the pre-flight needs no game read outside ADR 0001's bracket, and the gap needs
a save reverted to an earlier date than the warehouse maximum, which no current workflow
produces. Documented, not redesigned, per the panel's own recommendation. CF-17/CF-19/CF-20
are cosmetic and left.

## 6. Manual gates & user-run steps — discharged 2026-08-30

Both ran green; the evidence is in §1. Recorded here is how to repeat them, because the
route matters more than the result.

**AC18 — the fresh-clone walk-through.** The prerequisite is a warehouse holding no
`bronze_*` tables, and `ops/mysql-bootstrap.sql:23` already creates one: `ootp`, the
production schema, which had never been landed into. One env var redirects a single run:

```
$env:MYSQL_DATABASE='ootp'
uv run python -m ootp_ai.ingest land --save-id <probe>
uv run python -m ootp_ai.reports render --save-id <probe>
```

No root, nothing dropped, `ootp_dev`'s two real landings untouched. *Prerequisite:* running
against the probe needs `OOTP_PROBE_LEAGUE` configured; `settings.managed` is also safe,
because the command only reads the save. Afterwards, drop the eight tables from `ootp` to
return it to empty — the app user has the grant, so this needs no root either, and the data
is one landing of a disposable twin, re-derivable from the snapshot still on disk.

**AC19 — the leak check.** Paste the printed ingest output into a scratch `.md` at the repo
root and run `uv run pytest tests/test_no_leaks.py`. The guard **does** scan untracked
files, so the scratch file does not need committing — which is the point, since committing
it is exactly what the check exists to make unnecessary.

**An earlier claim in this report was wrong and is corrected above.** It said AC18 "cannot
be staged by an agent" because reaching an empty schema would mean dropping `ootp_dev`'s
tables. The acceptance panel said the same. Both had read `mysql-bootstrap.sql`'s grants
and neither noticed it creates a second, unused warehouse — the answer was in the file the
argument cited.

## 7. Hand-off

Ready for `/commit`, which stages deliberately, runs the doc checks and asks before
writing. The push follows on that yes; **opening the PR stays the operator's**, and CI
re-runs the offline gates there.

**Follow-up this build surfaced, none blocking:**

- Three prose mentions of `ingest.py` are now stale (§3.5); one is in a parser module the
  plan fenced.
- CF-12's `latest_landing` keying gap is documented, not closed.
- The static write-guard scans for *writes* only, so a module that only **reads** a game
  file is invisible to it. CF-04 closed the one instance by test; the general shape is a
  candidate for `tree-seam-for-remaining-guards`.
- `bronze_name` re-lands 264,095 rows per landing and no retention policy exists
  ([ADR 0018](../../../../docs/decisions/0018-retention-is-infrastructure.md)). Making landing
  one keystroke accelerates a cost nobody has bounded; this build did not fix it and must
  not appear to.

**Panel trail:** [`reviews/implementation-review.md`](reviews/implementation-review.md) —
the ledger, all 20 confirmed findings, the 25 verify verdicts, the meta-audit, and the
reviewer summaries, verbatim, including the parts later shown wrong.
