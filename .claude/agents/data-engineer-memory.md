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

## The budget — two numbers, two jobs

**~120 physical lines is the curation target**, enforced by judgment at the `/update-docs`
sweep before merge. **250 is the runaway ceiling**, enforced mechanically in CI.

**Append freely while you work. Never prune.** Pruning mid-build means predicting which
entries later phases will need, and guessing wrong drops the one that would have saved them.
Curation is the human's job, at the doc gate, with the whole build visible.

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
- **2026-08-16** · `measured` · `tests/test_no_leaks.py` and `tests/test_doc_links.py` iterate
  `git ls-files`, so a file you just created is **invisible to both guards** until the main
  thread commits it — a green suite says nothing about new files. Import `PATTERNS` from the
  guard and run it over the new paths yourself before handing off. · evidence:
  `tests/test_no_leaks.py` `tracked_text_files()` · tag: harness
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
- **2026-08-15** · `measured` · The ported panel guard
  `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` fails on arrival, and fails
  **identically** in the `nba2k-rpg` repo it came from — a pre-existing upstream defect, not
  a porting error. Six dedupe/coverage assertions. · evidence: `CLAUDE.md` Outstanding
  scaffolding work · tag: harness
