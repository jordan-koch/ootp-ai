# Data-engineer memory

Implementation ergonomics, learned the hard way. Read this before you build; append to it
when something costs you time that it should not cost the next session.

## What belongs here

Things that make *building* here go wrong: struct-parsing traps, library and tooling
surprises, commands that behave differently than documented, harness behaviour. Facts an
advisor would never care about but an implementer rediscovers every session.

## What routes elsewhere — do not put these here

- **Data facts** — a field's meaning or offset, what a population structurally lacks, scale
  and scout-filter behaviour, what a column actually contains. These go to
  `docs/data-access.md` via your handoff's `docs-delta` section. Never here: that file is
  audited by the doc gate and this one is not, so a data fact recorded here means the repo
  holds two answers and the gate checks one.
- **Repo-wide scar tissue** — a trap that binds every agent, not just you: `CLAUDE.md`
  Constraints & Gotchas, via `docs-delta`.
- **Decisions and their costs** — `docs/decisions/`, via `docs-delta`.

## Entry format

One bullet per entry, opening line a fixed shape so it can be checked mechanically:

```
- **YYYY-MM-DD** · `label` · <the claim> · evidence: <pointer> · tag: <routing tag>
```

Continuation lines are indented under the bullet. Keep an entry to about four lines.
`label` is one of this repo's five — `measured`, `verified`, `inferred`, `assumed`,
`unconfirmed`. An `assumed` claim written as `verified` is worse than no entry.

**Paths are inline code, never markdown links** — the link checker scans only markdown-link
syntax, so a backticked path is invisible to it. **Cite a repo artifact, never raw
environment output**: this file is committed and the repo is public.

## Length — not your problem

**There is no budget. Append freely while you work, and never prune.** Do not count the
lines in this file, do not trim it to fit, and do not weigh whether an entry is worth the
space. If something cost you time, write it down and get back to the build.

Pruning mid-build means predicting which entries later phases will need, and guessing wrong
drops the one that would have saved them. **Curation happens at `/update-docs`**, which
runs whenever this file appears in a staged diff — by a reader who has the whole change in
front of them and can tell a dead entry from a quiet one.

There used to be a 250-line ceiling here, enforced in CI, and it was removed on 2026-08-16
because it contradicted the paragraph above. A build hit it, had six things to record, and
had no legal move: forbidden to prune, unable to append. The rule now has one branch and it
is the one you are already following.

## Entries

- **2026-08-15** · `measured` · PowerShell 5.1 `Set-Content`/`Out-File` mangle UTF-8; write
  files with the Write/Edit tools instead. · evidence: `CLAUDE.md` conventions ·
  tag: tooling
- **2026-08-15** · `measured` · `uv sync` resolves *every* dependency group, not just the
  default ones, so an unsatisfiable optional group blocks the whole install. `dbt-mysql` is
  capped at 1.7.0 and pins `dbt-core~=1.7.0`. · evidence:
  `docs/decisions/0004-mysql-warehouse.md` §Notes · tag: tooling, docs-candidate
- **2026-08-16** · `measured` · MySQL `information_schema` returns UPPERCASE column names, so
  with `DictCursor` `row["table_name"]` raises `KeyError` while `row["TABLE_NAME"]` works.
  Alias every information_schema column (`SELECT table_name AS table_name`) rather than
  guessing the case. · evidence: `src/ootp_ai/db.py` uses `DictCursor` · tag: tooling
- **2026-08-16** · `verified` · A PyMySQL read-only session is `SET SESSION TRANSACTION READ
  ONLY` (SESSION scope — the bare `SET TRANSACTION READ ONLY` expires after one
  transaction), passed as `init_command`, then **read back** with
  `SELECT @@session.transaction_read_only` before the connection is handed out; an
  init_command that silently failed looks identical to one that worked. Observed `1` against
  the live instance. · evidence: `src/ootp_ai/db.py` · tag: tooling
- **2026-08-16** · `measured` · `types-PyMySQL` makes `pymysql.connections.Connection`
  `Generic[_C]` with default `Cursor`, so under mypy strict annotate the factory return as
  `Connection[DictCursor]`; a bare `Connection` is fine but loses the cursor row type. ·
  evidence: `src/ootp_ai/db.py` · tag: tooling
- **2026-08-16** · `measured` · `tests/test_no_leaks.py` iterates `git ls-files`, so a file
  you just created is **invisible to it** until the main thread commits it — a green suite
  says nothing about new files. Import `PATTERNS` from the guard and run it over the new
  paths yourself before handing off. `tests/test_doc_links.py` does **not** share this
  limitation: it uses `Path.rglob("*.md")` and sees untracked files. *(Corrected 2026-08-16
  at the doc gate — this entry originally named both guards, and the wrong half taught
  agents to work around a check that works.)* · evidence: `tests/test_no_leaks.py`
  `tracked_text_files()` vs `tests/test_doc_links.py` `markdown_files()` · tag: harness
- **2026-08-16** · `measured` · Ruff `N818` demands an `Error` suffix on every exception
  class, but the offline suite imports `MalformedHeader`, `UnsupportedSaveVersion`,
  `SaveFilenameMismatch`, `UnexpectedEndOfData` and `NotChallengeMode` by those exact
  names. Pin the name and add a bare `# noqa: N818`; put the reason in the docstring,
  because ruff mis-parses prose appended to the noqa. · evidence:
  `src/ootp_ai/parser/errors.py` · tag: tooling
- **2026-08-16** · `measured` · mypy aborts the *entire* run with "Source file found twice
  under different module names" when a test-helper directory has no `__init__.py`
  (`synthetic` vs `fixtures.synthetic`). `--explicit-package-bases` + `MYPYPATH` makes it
  worse — `src` then resolves to the *installed* package and 18 `import-untyped` errors
  appear. The fix is an empty `tests/fixtures/__init__.py`; `uv run mypy src` is the
  partial check meanwhile. · evidence: `pyproject.toml` `files = ["src", "tests"]` ·
  tag: tooling
- **2026-08-16** · `verified` · A fix that lands in a deny-set path can still be *proved*
  without writing there: copy `pyproject.toml`, `src/` and `tests/` into the scratchpad,
  apply it in the copy, and run the repo venv's `mypy.exe` / `pytest.exe` from that
  directory. `tests/test_repo_structure.py` and `test_agent_contract.py` fail in the copy
  (they read `.gitignore`, `docs/`, `.claude/`) — expected, not signal. · evidence: this
  session's Phase 3 mypy blocker · tag: harness
- **2026-08-16** · `measured` · Ruff `RUF022` sorts `__all__` isort-style — SCREAMING_CASE,
  then CamelCase, then lowercase — not plain alphabetical, so a hand-alphabetised list
  fails. · evidence: `src/ootp_ai/saves.py` · tag: tooling
- **2026-08-16** · `verified` · The no-seek ban is enforceable *structurally*: `__slots__`
  plus a getter-only `position` property makes `hasattr(cursor, "seek")` false and
  `cursor.position = 0` an `AttributeError`. Keep `unpack_from`'s offset argument a
  **name** (`self._position`) and the AST guard needs no exemption for the primitives
  themselves. · evidence: `src/ootp_ai/parser/primitives.py` · tag: harness
- **2026-08-16** · `verified` · **A constant confirmed against a single save is not a
  constant.** Five files sampled from one save all read `7` at header offset 75 and it was
  written down as a format constant; it is the sim-date *day*, and that save sits at March
  7. Vary the **save**, not just the file, before believing any header value — and treat a
  value that is identical across files of one save as the *least* tested kind of claim. ·
  evidence: the correction note in `tests/fixtures/synthetic.py` · tag: harness
- **2026-08-16** · `verified` · When the end of a region is unmeasured, hand on the
  **cursor**, never a length. `read_header_from(cursor, name)` lets the next stage keep
  walking with no offset arithmetic, and a header object carrying no `length` /
  `body_offset` cannot tempt a later phase into a body start nobody measured. · evidence:
  `src/ootp_ai/parser/header.py` · tag: harness
- **2026-08-16** · `measured` · `addopts` already carries `-q`, so passing `-q` again
  double-quiets pytest and suppresses the `N passed` summary line entirely. Run without
  the extra flag when the handoff needs a number to cite. · evidence: `pyproject.toml`
  `addopts` · tag: tooling
- **2026-08-16** · `verified` · **Export column order is not disk order.** Searching
  `coaches.dat` for the four scout ratings as a contiguous run in the export's column order
  found nothing in 359 of 400 coaches; the disk order interleaves differently, and a
  fixed-length-group sweep found the run immediately. Sweep offsets *first*, derive the
  order from what the sweep returns, and only then build a signature. · evidence:
  `var/spike3/59_scoutfields.py` vs `53_coach_anchor.py` (both gitignored) · tag: harness
- **2026-08-16** · `verified` · A **composite landmark** — one high-entropy field plus two
  small ints at measured relative offsets — segments a variable-length record file in one
  pass and cannot lose the thread, unlike greedy "next expected id within N bytes" chaining,
  which stalled at 2,166 of 3,251 records on the same file. Index the high-entropy field
  once into a dict, then filter candidates. · evidence: `var/spike3/58_records2.py` ·
  tag: harness
- **2026-08-16** · `verified` · The cheapest calibrated null for "is this value stored here"
  is the **same search with every value +1**. It costs one extra pass, needs no statistics,
  and separates a real hit from a chance hit instantly (34/34 vs 2/34 on one probe; 1,600/1,600
  vs 0/1,600 on another). Reach for it before any correlation machinery. · evidence:
  `var/spike3/61_scoutblock2.py`, `72_budget_confirm.py` · tag: harness
- **2026-08-16** · `measured` · Scoring a candidate offset on the **non-zero subset** of the
  target column is what stops a constant-zero region winning a sweep — but it does not stop a
  *non-zero* constant. Three separate sweeps this session peaked on a byte that was constant
  `2` or constant `3`. Always print the observed value distribution next to the expected one;
  a match rate alone is not a result. · evidence: `var/spike3/64_players_seg.py` ·
  tag: harness
- **2026-08-15** · `measured` · The ported panel guard
  `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` fails on arrival, and fails
  **identically** in the `nba2k-rpg` repo it came from — a pre-existing upstream defect, not
  a porting error. Six dedupe/coverage assertions. **The measurement stands; the reading does
  not — see the 2026-08-17 correction at the end of this file.** · evidence:
  `requests/bugfix-requests/verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md` (the
  originally cited `CLAUDE.md` section was removed in commit 1c47c2d) · tag: harness
- **2026-08-16** · `verified` · **"It varies across saves" is not "it is the field."** A `u32`
  in `saved_games.dat` reads 2/2/1 across the three saves, which satisfies an
  anti-hardcoding test outright — but the clubs are 4/4/6 and the split falls along
  Challenge/Challenge/Standard. Enumerate every numeric slot at u8/u16/u32 and match the
  **actual expected values**; discriminating power alone is what a mode flag has too. ·
  evidence: `src/ootp_ai/parser/saved_games.py` § *Why there is no `human_team_id` field* ·
  tag: harness
- **2026-08-16** · `verified` · A `skip(N)` width constant is defensible only inside a
  **strictly byte-accounted** walk — run to `cursor.exhausted()` and let a wrong width
  desynchronise the next length prefix and raise. That turns an unverifiable constant into
  one the file checks itself, which is why a 74-byte tail measured against a single 2,070-byte
  file is a claim rather than a guess. · evidence: `src/ootp_ai/parser/saved_games.py`
  `_HEADER_TAIL_LEN` · tag: harness
- **2026-08-16** · `measured` · Strict-ASCII `Cursor.string()` is right for a value you
  return and wrong for one you discard: an accented byte anywhere in a dropped field raises
  on someone else's machine over a string nothing reads. Pass `encoding="latin-1"` on
  `_drop_*` helpers — latin-1 maps every byte — and keep strict ASCII where a mangled value
  would be a *wrong* value. · evidence: `src/ootp_ai/parser/saved_games.py` `_drop_string` ·
  tag: tooling
- **2026-08-16** · `verified` · **A correlation sweep needs a positive control that sits
  *after* the anchor.** Three sweeps for a missing field returned zero hits and all three
  were worthless: the `team_id` control also missed, which meant the anchor drifted and the
  null result said nothing. Put a known-present field downstream of the anchor in the same
  sweep, and read a null only when the control lands. · evidence: this session's
  `teams.dat` field hunt, reported in `requests/feature-requests/first-sight/reviews/handoff-phase-5.md` ·
  tag: harness
- **2026-08-16** · `verified` · **Eyeballing three records cannot tell a fixed layout from a
  sparse one.** Reconstructing the *whole* candidate field list from the oracle and comparing
  it byte-for-byte against every located record settled in one pass what an hour of hex dumps
  could not: 232 of 233 matched, and the single miss named the exact ambiguity. Write the
  oracle-driven alignment before the third hex dump. · evidence:
  `src/ootp_ai/parser/teams.py` module docstring · tag: harness
- **2026-08-16** · `measured` · **A missing module the tests import blocks pytest
  *collection*, so "escalate and build nothing" leaves every guard in the repo unrunnable** —
  including `test_no_leaks` and `test_read_only`. When the escalation is "this cannot be
  decoded honestly", still land the module's public surface and its guards and raise a named
  `SaveFormatError` subclass from the entry point; the offline suite then goes fully green
  and only the gamedata half is red. · evidence: `src/ootp_ai/parser/teams.py`
  `UnmappedRecordLayout` · tag: harness
- **2026-08-16** · `verified` · A refusing parser must not be wired into `ingest_save`:
  `tests/test_read_only.py` calls it, so a raise there converts the ADR 0001 proof from
  green to error and the one signal worth protecting disappears. Leave the seam unwired and
  say so at the construction site. · evidence: `src/ootp_ai/ingest.py` `human_team_id=None` ·
  tag: harness
- **2026-08-16** · `verified` · **A model that scores 100% is not a unique model — enumerate
  the orders that tie, and the tie set *is* the ambiguity statement.** Brute-forcing every
  field order under a drop-zeros rule returned 18 distinct orders all scoring 259/259; they
  differed only where the oracle column is constant-zero across the whole population and
  therefore unplaceable in principle. Report the tie set, never the first hit. · evidence:
  `var/spike4/85_q1_models.py` (gitignored) · tag: harness
- **2026-08-16** · `verified` · **`information_schema` yields a field list for a table the
  export left empty.** `ootp_truth_real.human_managers` has 0 rows and 33 columns, and that
  column list was the oracle that named the fields of an 835-byte binary nothing else
  described. An empty oracle table is still an oracle. · evidence: `var/spike4/89_schema.py`
  (gitignored) · tag: harness
- **2026-08-16** · `verified` · **To break a confound across saves, intersect "offsets where
  *this* save holds *its own* expected value" and run the same intersection at value+delta.**
  Three saves confounded club-with-mode; the intersection was exactly 3 offsets at delta 0
  and **empty at every other delta tried**. Stronger than any single-save sweep and it costs
  one loop. · evidence: `var/spike4/91_q2_account.py` (gitignored) · tag: harness
- **2026-08-16** · `verified` · **A fixed-width array is byte-accountable by arithmetic
  alone: `(end - start) % count == 0`.** One line settled a 479,557-byte region as
  12,961 x 37 exactly, with no walk and no offsets trusted — and the two candidate endpoints
  were both found by searching for the *count* as a `u32`. Reach for the divisibility check
  before writing a walker for a region you only need to bound. · evidence:
  `var/spike4/101_schedule2.py` (gitignored) · tag: harness
- **2026-08-16** · `verified` · **A `u32` count immediately preceding an array is a
  self-validating landmark.** Enter at a content anchor, read the count, walk forward, and
  assert the walk yields exactly that many records and lands on the next region's boundary.
  That recovers most of what strict byte accounting buys **inside a region** without walking
  the 62% of the file that precedes it. · evidence: `var/spike4/96_world_calendar.py`
  (gitignored) · tag: harness
- **2026-08-16** · `measured` · Scratch under `var/` can import the real config/db layer with
  `sys.path.insert(0, parents[2] / "src")` and `uv run --project <repo> python script.py`
  from the scratch directory — no install, no editable wheel, and `connect_truth` enforces
  the read-only session for free. · evidence: `var/spike4/common.py` (gitignored) ·
  tag: tooling
- **2026-08-16** · `verified` · **A forward-only cursor and a variable layout reconcile by
  deciding widths with lookahead, then consuming them.** `_scan_shape(data, cursor.position)`
  returns counts; the cursor then does plain typed reads. Cross an undecoded region with
  `data.find(frame, cursor.position)` + `cursor.skip(hit - cursor.position)` — no seek, AST
  guard green, zero exemptions. · evidence: `src/ootp_ai/parser/teams.py` · tag: harness
- **2026-08-16** · `verified` · **Backtrack over the small shape space; do not sniff
  content.** Trying each plausible field count and requiring a *downstream* structural
  signature to validate resolved every record in three saves; "the logo ends in `.png`"
  resolved two of three. · evidence: `src/ootp_ai/parser/teams.py` `_scan_signature` ·
  tag: harness
- **2026-08-16** · `verified` · **Promote a two-sided cross-check into the decoder.** Keeping
  only *reciprocated* parent/child links settled the direction **and** discarded every value
  a soft terminator had swallowed — 199/199 vs the oracle. Agreement between two records is
  evidence, not just validation. · evidence: `src/ootp_ai/parser/teams.py`
  `_resolve_organisation` · tag: harness
- **2026-08-16** · `measured` · **PowerShell mangles UTF-8 when it *edits*, not just when it
  writes.** `Get-Content f | Out-File -Encoding utf8 f` to drop a line double-encoded all 35
  non-ASCII lines and ruff/pytest stayed green. Repair: `text.encode("cp1252")
  .decode("utf-8")`. Use Edit for deletions. · evidence: this session's `teams.py` repair ·
  tag: tooling
- **2026-08-16** · `measured` · **Widening a field to `T | None` can turn `uv run mypy` red
  inside `tests/`**, which is deny-set: mypy runs over `src` *and* `tests`, so `len(x)` or
  `y in x` on the attribute becomes an error you cannot fix. Grep the test tree for the
  attribute before changing its type. · evidence: `pyproject.toml` `files` · tag: harness
- **2026-08-16** · `verified` · **A structural landmark beats a string landmark when the
  string is not unique.** The calendar could not be entered by any string (`OPENING DAY`
  occurs 95 times) but is trivially identifiable by *shape*: one count-prefixed array of
  self-consistent records, maximal in both directions. 43,813 motif hits reduce to exactly
  one candidate per save in 0.16 s. · evidence: `src/ootp_ai/parser/world.py`
  `_find_calendar_array` · tag: harness
- **2026-08-16** · `verified` · **Right-maximality alone is not uniqueness — every record in
  a count-prefixed array is a candidate head**, because the four bytes in front of a record
  are the previous record's tail and often read as a small count. The array's own last
  record declares `count=1`, walks, and is right-maximal. The fix is a bounded
  **left-maximality** test: no record may end exactly where the count begins. Two survivors
  become one. · evidence: `src/ootp_ai/parser/world.py` `_is_left_maximal` · tag: harness
- **2026-08-16** · `measured` · **`re.finditer` is non-overlapping, which can hide the very
  match a byte-motif search needs.** A seven-byte motif consumed at offset *n* hides one
  starting at *n+4*. Wrap the pattern in a zero-width lookahead `(?=…)` — 33,564 hits become
  43,813, cost 0.06 s over 8.9 MB. · evidence: `src/ootp_ai/parser/world.py` `_EVENT_MOTIF` ·
  tag: tooling
- **2026-08-16** · `measured` · **PowerShell `Measure-Object -Line` does not count blank
  lines**, so it disagrees with Python's `splitlines()` and with `(Get-Content …).Count` —
  observed 235 against 250 on the same file. Use `.Count` whenever the number is the
  question rather than a rough size. · evidence: `tests/test_agent_contract.py`
  `test_memory_entries_carry_an_epistemic_label`, which counts with `splitlines()` ·
  tag: tooling
- **2026-08-16** · `verified` · **Two decode paths over the same bytes is a cheap, real
  cross-check.** The lookahead scan that validates an entry and the cursor that then reads
  it produce `declared_count` and `parsed_count` independently, so a `WorldRegion`'s
  self-audit is not a tautology the way `len(list)` against its own count would be. ·
  evidence: `src/ootp_ai/parser/world.py` `_walk_divisions` · tag: harness
- **2026-08-16** · `measured` · **A landmark's offset can coincide across saves and still not
  be a constant.** The MLB league name sits at byte 5,548,618 in *both* the managed league
  and the Challenge probe — two independently created universes — and at 5,547,958 in the
  standard probe. An offset that agrees in two of three saves is the most dangerous kind of
  near-constant. · evidence: `var/spike5/p1_landmarks.py` (gitignored) · tag: harness
- **2026-08-17** · `verified` · **The 2026-08-15 entry above read the batching guard's failure
  backwards.** Its cause is local: two fixture keys in
  `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` named a sibling repo's
  lenses, `FINDINGS_BY_LENS[lensKey] || []` swallowed them, and 3 of 11 findings vanished
  before dedupe — all six assertions cascade from that. Re-keying two words turns it green
  with `acceptance_panel.js` byte-untouched. The earlier entry's *measurement* (it fails
  identically in `nba2k-rpg`) stands and was not re-tested here; what is refuted is its
  reading of that as "a pre-existing upstream defect, not a porting error" — two
  separately-adapted copies failing identically is exactly what a porting error in the
  shared inherited part looks like. · evidence:
  `requests/bugfix-requests/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md` ·
  tag: harness
- **2026-08-17** · `measured` · **A guard that names a repo path only checks the paths someone
  thought to scan.** `tests/test_skill_references.py` globbed `*.md` under `.claude/skills/`
  and was therefore blind to the panel `.js` files — which is where three references to a
  `docs/data-sources.md` that never existed here sat, inside the prompt three planning agents
  ground themselves in. Widening the glob found all three in one run. · evidence:
  `tests/test_skill_references.py` `skill_documents` · tag: harness
- **2026-08-17** · `measured` · **Backticks inside a JS template literal terminate it, and
  panel prose lives in template literals.** Editing a mandate string in `plan_panel.js` to add
  a backticked term broke three sibling `.mjs` guards at once with `Illegal return statement`.
  The guards caught it in seconds; nothing in CI would have. Prefer plain words in panel
  prose, and run the `.mjs` guards after any panel edit. · evidence:
  `.claude/skills/create-implementation-plan/plan_panel.js` · tag: tooling
