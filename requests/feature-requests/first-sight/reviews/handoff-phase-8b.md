# Handoff — first-sight Phase 8b (bronze landing, the ingest run, and the first ingest)

**Main-thread build**, so no data-engineer return contract is owed. Written because the
phase's acceptance requires the landed row counts to be **read back from the `ingest_run`
row and recorded here**, and because Phase 9 inherits four decisions it would otherwise
rediscover mid-build.

## What landed

`src/ootp_ai/warehouse/` gained `load.py` and `ingest_run.py`; `ingest.py` gained
`ParsedSnapshot`, `parse_snapshot`, `dump_parse` and the two agreement gates;
`tests/` gained `test_bronze_landing.py` (39 offline tests) and `fixtures/warehouse.py`.
`git ls-files src/ootp_ai/warehouse` now lists `__init__.py`, `ddl.py`, `ingest_run.py`,
`load.py`, `sql.py` — the inverse of Phase 8a's check.

**The warehouse holds real data for the first time.** `ootp_dev` carries the eight declared
tables and nothing else, populated from two saves.

## The first ingest, read back from `ingest_run`

Both rows are still queryable; these numbers come from `read_ingest_run`, not from stdout.

| | `OOTP-AI` @ 2024-03-07 seq 1 | `Test-Save-Challenge-Mode` @ 2024-03-18 seq 1 |
|---|---|---|
| `human_team_id` | 4 | 4 |
| `parse_seconds` | 2.236 | 2.116 |
| `bronze_team` | 337 | 259 |
| `bronze_player` | 22,046 | 18,077 |
| `bronze_team_roster` | 20,016 | 15,721 |
| `bronze_name` | 264,095 | 264,095 |
| `bronze_division_team` | 30 | 30 |
| `bronze_league_event` | 3,058 | 3,058 |
| `bronze_field_label` | 96 | 96 |
| `ingest_run` | 1 | 1 |
| `residual_bytes` | names 0 · players 1,002 · teams 2,274 · world 8,698,702 | names 0 · players 958 · teams 1,137 · world 8,457,883 |

Landing takes ~5 s on top of the parse. The **standard-mode probe is deliberately not
landed** — Phase 9 step 1 lands it under its own `save_id` as part of the differential
harness, and doing it here would pre-empt that phase's own setup.

**The end-to-end answer works.** Boston at 2024-03-07 resolves to **33 / 26 / 30 / 7**
across the four roster lists — the split the operator verified by hand in Phase 6b — and
joining `bronze_team_roster` → `bronze_player` → `bronze_name` twice returns real names
with uniform numbers and ages. That join is a *query*, not a bronze transformation.

## How to reproduce it — there is no entry point, by decision

**Operator-disposed 2026-08-19: no `__main__` in this phase.** The plan never sequenced
one and CLAUDE.md forbids speculative modules; Phase 10 owns the CLI. So the exact
composition is recorded here instead, because "the first real ingest" being reproducible
only from an untracked script is the cold-handoff gap plan §1 exists to close:

```python
settings = load_settings()
connection = connect_warehouse(settings)
ensure_tables(connection)
# ...or take_snapshot(save, snapshot_root=settings.snapshot_root) for a fresh one
snapshot = read_manifest(settings.snapshot_root / save_id / sim_date / seq)
parsed = parse_snapshot(snapshot)
run = land_snapshot(connection, parsed, ingest_seq=snapshot.ingest_seq)
```

**Pass the snapshot's own `ingest_seq` whenever a durable snapshot is on disk.** That is
what keeps the snapshot directory and the warehouse row naming the same attempt. Omitting
it allocates the next free sequence from the warehouse, which is right only when the
snapshot is transient — a parse into a temporary directory always allocates 1 on the
filesystem side, and landing that number blindly would collide with an unrelated earlier
landing. The tests take the second path deliberately; the operator takes the first.

## Step 6, measured — the number decides it, not the aesthetics

The plan required a measurement rather than a judgment, so: `players.dat` is **25,667,300
bytes** (the plan's "32 MB" was an estimate), and on the probe

| | seconds |
|---|---|
| a second `read_bytes()` of `players.dat` | **0.004** |
| `read_teams` | 0.01 |
| `read_players` | 0.46 |
| `read_rosters` (teams spans + a second players walk) | 0.56 |

**The buffer is now read once and shared**, which is free and safe because `bytes` is
immutable — the plan's caution about "a shared mutable buffer between two walkers" does
not apply in Python. It saves 4 ms: the OS page cache had already absorbed the second read,
so the I/O the deferral worried about was never the cost.

**The second *walk* stays**, and the measurement is not the only reason. It costs ~0.5 s of
a ~2.2 s parse, which would be worth reclaiming — but `read_rosters` cannot consume
`read_players`' output, because it reads a field `PlayerRecord` does not carry: the
roster-status byte, 22 bytes past the second historical string. Collapsing the walks would
mean landing that byte on `PlayerRecord`, and it is an unclassified flag byte the serving
gate would have to withhold. The cost is real and the alternative is worse.

## Decisions Phase 9 inherits

1. **`parse_seconds` is already filled**, contrary to Phase 8a's handoff. The plan's step 3
   lists it as a column with the implementation note (`time.perf_counter()`), so 8b
   measures it. **It covers the walk only** — reading the four parsed files and the five
   walker calls plus the agreement checks — and excludes snapshotting, header provenance
   and landing. AC17 can read it back and assert existence without measuring anything new.
2. **The `ingest_run` row is claimed first, and the whole landing is one transaction.** A
   colliding load fails on one small insert rather than part-way through 264,095 name rows.
3. **Row counts are read back out of the schema before commit**, per table, including
   `ingest_run` itself. Phase 9's AC17 and Phase 11's catalog are both specified to trust
   `table_row_counts`, so it is a measurement rather than a restatement.
4. **Contention costs a retry, not a landing.** Measured during review: two concurrent
   loaders deadlock deterministically, and `FOR UPDATE` does **not** serialise them —
   InnoDB gap locks are mutually compatible. The primary key is what prevents an overwrite.
   `land_snapshot` retries 1213/1205 three times with a re-allocated sequence and raises
   `ConcurrentLandingError` — never `IngestRunExists`, which means something else entirely.

## The `rosters.py` → `players.py` seam — settled, as the plan asked

**They stay private.** The deferral rested on a premise that turned out false: nothing
outside `parser/` reaches for them. `warehouse/load.py` binds `PlayerRecord` and
`RosterMembership` — the public dataclasses — through `ingest.ParsedSnapshot`, and touches
no private name in either module, so the loader never forced the question. The thirteen
names are record-head widths and framing helpers, not a data contract; a public version
would invite a third module to depend on the layout rather than on the records. Recorded in
`parser/rosters.py`'s docstring, where the next reader of that import list will find it.

## Deviations, each argued rather than noticed

- **AC10 clause 2** ("a second `snapshot_date` leaves the first bit-identical") is closed
  literally by `test_a_landing_at_another_sim_date_is_left_untouched`, which digests an
  already-landed triple at another date before and after a fresh landing. An earlier draft
  substituted two `ingest_seq` of one date and argued it was strictly harder; **that
  argument was wrong** and the review caught it — two sequences and two dates each differ
  in exactly one key column. Both tests now exist and the docstring says which is which.
- **Two test files joined §7's checklist** (`test_bronze_landing.py`,
  `fixtures/warehouse.py`), recorded in the plan with the §4.1 argument.
- **`bronze_league_event.start_date` is now nullable.** `parser/world.py` accepts
  `year == 0` for a calendar record on purpose — "a calendar record with no date is
  structural absence" — and the declaration had nowhere to put it. Zero rows carry one on
  the saves that exist; the offline test proves the path.
- **Four coverage statements were corrected** against what actually landed, plus two the
  review caught afterwards. The managed league is the larger universe (337 clubs, 22,046
  players) and three statements described only the probes.
- **`PROJECT_SCOPE` AC12 was amended** (operator-disposed): the strict byte-accounting tier
  applies to `names.dat` alone; `teams.dat` and `players.dat` are diagnostic.

## Still open, and named rather than left to be found

- **No tracked entry point performs an ingest** (operator-disposed to Phase 10). Until
  then `ensure_tables` is reachable only through a test fixture, so on a fresh machine the
  eight tables come into existence as a side effect of running the suite.
- **Warehouse tests share the development schema** (operator-disposed). `purge_snapshot`
  now deletes `ingest_run` first and is scoped to the declared tables, so an interrupted
  purge leaves detectable orphans rather than a lying provenance row — but a killed process
  still leaves ~300,000 rows that only hand-written SQL will clear.
- **`bronze_field_label` persists `name_category` as `rating-true`.** That is CLAUDE.md's
  corollary to ADR 0012 doing withhold-by-default duty, not a claim about the byte; the
  field-map entry now says so. Whether the category vocabulary should gain an
  `unclassified` member is a change to the serving gate's posture and belongs to whoever
  revisits ADR 0012.
- **`ensure_tables` never repairs a drifted table.** A table created once with a weaker key
  would stay wrong forever. `test_the_live_primary_key_is_the_declared_key` now reads
  `information_schema.STATISTICS` and would catch it, but the repair is still a migration
  nobody has designed.
- **`verify_snapshot` has no production caller.** The digests in `ingest_run` are copied
  from the manifest rather than re-measured over the bytes the parse actually read.

## Coverage numbers to carry forward

| Table | Managed league | Probe | Note |
|---|---|---|---|
| `bronze_team` | 337 | 259 | every record, no filtering |
| `bronze_player` | 22,046 | 18,077 | minimal field set; no position |
| `bronze_team_roster` | 20,016 | 15,721 | **176 assigned-but-unrostered players hold no row** |
| `bronze_name` | 264,095 | 264,095 | ~6–7× the rest combined |
| `bronze_division_team` | 30 | 30 | MLB's six divisions only |
| `bronze_league_event` | 3,058 | 3,058 | deleted events included |
| `bronze_field_label` | 96 | 96 | every column of all eight tables |

## Gate at handoff

`ruff check` / `ruff format --check` / `mypy` clean over 62 files. **Offline 481 passed**
(353 before Phase 8, 442 after 8a), **gamedata 131 passed, 1 skipped** — the skip is
`test_byte_accounting.py`'s strict-tier assertion, named and expected. The offline suite
was re-run with `MYSQL_PORT` pointed at a closed port and stayed green, so AC16's
"no MySQL" clause is a measurement here rather than an argument.
