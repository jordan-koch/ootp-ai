> **Status:** implemented · created 2026-08-24 · decided · next: commit

# Implementation Report — The guard probe plants in a tree it owns

> **One-line outcome:** neither an interrupted run nor a concurrent reader can produce a
> phantom fixed-offset or leak violation, because no scope test writes into a tree another
> reader scans · **Acceptance:** 41/41 criteria met · **Branch:**
> `guard-probe-survives-an-interrupted-run`

## 1. Acceptance ledger

The bugfix track's contract first, then the plan's per-phase acceptance. Every row is evidence
from a command that was run, not an assertion that it would pass.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| U1 | The committed red reproduction goes green | **met** | `uv run pytest tests/test_guard_probe_isolation.py` → 5 passed. Before: 2 failed |
| U2 | …with that file's assertions **unedited** | **met** | `git diff HEAD -U0 -- tests/test_guard_probe_isolation.py \| Select-String '^-'` returns exactly one line: the `--- a/…` header. Zero source lines deleted or changed; the file's diff is purely additive |
| U3 | A regression test is left behind | **met** | Three layers: the residue detector + AST fixture-reach + ADR-0020 refusal in `tests/test_guard_probe_isolation.py`; `test_no_probe_is_ever_written_into_the_live_package`; and the class-level `tests/test_probe_isolation_contract.py`, which reports exactly the four historical offenders when run against the `HEAD` blobs |
| U4 | Nothing else regresses | **met** | 644 passed / 0 failed offline, vs a 613-test baseline of 611 passed + the 2 red repro tests. No test lost (name-set diff vs `HEAD` shows only the two plan-mandated renames). Concurrency re-measured — see §4 |
| P0 | Seam added; repro stays **red**; 37 modules / 0 violations; mypy 82 | **met** | Phase 0 gate run: 74 passed on the four-module selector; repro still 2 failed; `modules 37 / violations 0`; `Success: no issues found in 82 source files` |
| P1 | Repro green unedited; mode A exit 97 with no survivor; mode B improved; mutations 1/2/3/7 watched to die | **met** | See §4. Abort child exit **97**, zero survivors in `src/ootp_ai/parser/` |
| P2 | Residue detector names a survivor; guard's own message **unchanged** | **met** | With a hand-planted survivor, the residue test names the file *and* `test_no_parser_module_seeks_to_a_fixed_offset` reports `…_probe.py:3: data[…] — a record-relative buffer subscript outside the sanctioned seam; read through parser/lookahead.py or walk with a Cursor` — byte-identical to the pre-fix message in `ROOT_CAUSE_ANALYSIS.md:52` |
| P3 | Leak site moved; no test lost; no assertion message edited; mutations 4/5 | **met** | 15 → 18 test functions, zero removed. `git diff -U1 tests/test_no_leaks.py` is five signatures, five call sites and one docstring — no `PATTERNS`, `keep`, `EXEMPT` or `EXEMPT_PREFIXES` change, no assertion message touched |
| P3b | Parity: the mirror ignores what this repo ignores | **met** | All seven verdicts identical pairwise, plus the non-ASCII enumeration property. **No off-ramp taken** |
| P4 | Contract guard green, **zero** allowlist entries, mutation 6 | **met** | 19 passed; `EXEMPT_MODULES == ()`; mutation 6 killed three seen-to-fail tests |
| P5 | ADR 0022 written, indexed, states its cost; memory appended; doc gates green | **met** | `uv run pytest tests/test_doc_links.py tests/test_repo_structure.py tests/test_agent_contract.py tests/test_no_leaks.py` → 21 passed. Memory diff: **12 insertions, 0 deletions** at first append, all subsequent corrections also appends |
| G | Four gates, final | **met** | `ruff check` clean · `ruff format --check` 210 files · `mypy` **83 source files** (baseline 81 + `guard_trees.py` + `test_probe_isolation_contract.py`) · `pytest -m "not gamedata"` 644 passed |
| N1 | **No file under `src/` changes** | **met** | `git diff --name-only HEAD` lists no `src/` path |
| N2 | Scanning rules untouched | **met** | 6 `CRY_WOLF` entries and 5 documented-hole tests present and unchanged |

## 2. What shipped

All six phases, `tests/` and `docs/` only.

- **`tests/test_no_fixed_offsets.py`** — `PACKAGE_RELATIVE`; `tree_root` on `parser_modules`
  and `parser_module_violations`, defaulting to `REPO_ROOT`; `relative_to(tree_root)` with the
  comment recording why the parameter is a **repo** root and not a package root. No rule,
  allowlist, residual or message changed.
- **`tests/fixtures/guard_trees.py`** (new) — `mirrored_package()` (byte-faithful `copytree`,
  probe residue excluded, zero-violations assertion before yielding) and `mirrored_repo()`
  (`git init`, `.gitignore` copied verbatim with `copy2`, never commits), plus `assert_owned`
  and the `OPEN_MIRRORS` registry.
- **`tests/test_fixed_offset_guard_scope.py`** — `parser_probe` gains an optional trailing
  `tree_root` and **keeps its two-positional call shape and plain-`str` yield**; the fidelity
  docstring is replaced rather than left standing; four plant sites moved onto mirrors; two
  tests renamed off `…_in_the_real_tree`; six tests added; the two production-observing tests
  keep their no-argument calls, each with a comment saying why.
- **`tests/test_guard_probe_isolation.py`** — assertions untouched; residue detector (both
  sites), AST fixture-reach test, and the ADR-0020 refusal added.
- **`tests/test_no_leaks.py`** / **`tests/test_leak_guard_scope.py`** — five keyword-defaulted
  signatures (`repo` keyword-only on `git_paths`); ten planting tests moved onto mirrors; the
  two live `mkdir`s deleted; the monkeypatch lambda given its defaulted parameter; three tests
  added; four deliberately kept on the real repo.
- **`tests/test_probe_isolation_contract.py`** (new) — the AST convention guard, empty allowlist.
- **`docs/decisions/0022-…md`** (new, indexed), **`tests/fixtures/README.md`**,
  **`.claude/agents/data-engineer-memory.md`** (append-only), and the ADR counts in
  **`CLAUDE.md`** / **`README.md`**.

## 3. Deviations from the plan

Seven, each deliberate. The first is the one that matters.

1. **Phase 1 step 10's locating mechanism was a plan defect, and was replaced.** The plan
   prescribed asserting that *"exactly one path matching `ootp_guard_mirror_*/…/<name>` exists
   under `tempfile.gettempdir()`"*. That root is **machine-global** while `TemporaryDirectory`
   is per-process, so the assertion counts sibling sessions' trees and trees stranded by older
   interrupted runs. Implemented as written, it measured **10 of 12 red** across three
   concurrent sessions — while staying green solo, and invisible to single-session CI. It was
   this request's own defect, relocated from `src/ootp_ai/parser/` to `%TEMP%`, inside the
   change that exists to retire it. Replaced with an in-process `OPEN_MIRRORS` registry: the
   fixture hands the test its tree instead of the test searching the world for it, which is
   strictly stronger anti-vacuity (it pins the exact path, not a count) and immune to both
   siblings and survivors. **Found by the acceptance panel, not by me.**
2. **Phase 2 step 4's `_guard_scope` token check was unsatisfiable as written.** That token is a
   substring of the sibling module's own filename, `test_fixed_offset_guard_scope.py`, which the
   guard legitimately cites four times — the criterion would have been red on arrival, and its
   cheapest wrong fix is deleting the guard's cross-references. Keyed on the probe **filename
   shape** instead, plus an AST clause over the strings the module actually uses (docstrings
   stripped) so `startswith("_guard_scope")` cannot slip through either.
3. **Phase 2 ships 5 tests where its acceptance line says 4.** The plan's own steps 1, 3 and 4
   each add one to a module that already had two. The acceptance arithmetic was wrong, not the
   step list.
4. **Phase 4's allowlist is empty, not one self-exemption.** The plan expected the contract
   module to need exempting because it contains the strings it bans; making the rule AST-based
   removed the need, since those strings are constants a parse tree does not confuse with calls.
5. **`__file__` is a taint seed alongside `REPO_ROOT`.** Measured while building the guard:
   five suite bindings resolve a root from `__file__` without ever naming `REPO_ROOT` —
   `tests/test_read_only.py`'s `SRC` among them — so the narrower rule had a real hole.
6. **The contract guard's verb set went beyond `CREATIVE_CALLS`.** The plan pinned it to
   `tests/test_read_only.py:337`; that module also defines and pins an `open`-mode rule at
   `:339-341`, and `(PARSER_DIR / name).open("w")` is an ordinary spelling of exactly the fixed
   defect. Added write-mode `open` (both spellings), `os.mkdir` (a plain ordering bug — `mkdir`
   is also a method name and matched the wrong branch first), the `shutil` copy family keyed on
   its **destination**, and the `for` / `with` / walrus binding forms.
7. **`assert_owned` was added, which the plan did not call for.** Both fixtures validated
   nothing about a caller-supplied root, so `parser_probe(name, body, tree_root=REPO_ROOT)`
   restored the original defect exactly and no guard added here could see it. It lives in
   `guard_trees.py` rather than inline precisely so the AST fixture-reach tests stay green.

**Not done, deliberately:** the plan's D6 follow-up (extending the seam to
`test_grain_contracts.py` and `test_read_only.py`) is not filed yet — see §6.

## 4. Verification & edge cases

### The two things the plan said must be MEASURED

**Mode A — durability.** The abort child (`os._exit(97)` inside the probe, which no `finally`,
`atexit` hook or signal handler survives) exits **97** and leaves **zero** probe modules in
`src/ootp_ai/parser/`. Before the fix the same run left `_guard_scope_abort_probe.py` behind —
reproduced by hand at Phase 0.

**Mode B — concurrency.** Two harnesses, and the difference between them is the finding:

| Harness | Before | After |
|---|---|---|
| Reader loop (`test_no_fixed_offsets.py`) vs planter loop (`test_fixed_offset_guard_scope.py`), 12 rounds | **2 of 12 red** | 0 of 12 |
| 3 concurrent sessions of `test_fixed_offset_guard_scope.py` × 4 rounds | **10 of 12 red** | 0 of 12 |
| 3 concurrent sessions of `test_leak_guard_scope.py` × 4 rounds | not measured | 0 of 12 |
| 2 concurrent full offline suites × 3 rounds | not measured | 0 of 6 |

Row 1 is the plan's prescribed form and it reproduced the **original** bug: the planter stream
was fully green while the reader went red twice, which is exactly the RCA's point — the planting
session is healthy and leaves nothing behind, so the reader who goes red never has the evidence.

**Row 2 exists because row 1 is structurally blind.** Two loops over *different* modules can
never put two sessions inside the same module at once, so that harness cannot observe two copies
of one test colliding — which is precisely what deviation 1 was. Both "before" figures were
measured on this machine with the same script; solo runs were green in every configuration.
**Record for the next reader: when claiming a concurrency property, name the harness beside the
number and check it can actually fail.**

### Mutations, all applied, observed and reverted

| # | Mutation | Killed |
|---|---|---|
| 1 | `mirrored_package` yields `REPO_ROOT` | the repro, with **both original messages** verbatim |
| 2 | the mirror copies only `__init__.py` | the set-equality half of the fidelity test (28 modules named missing) |
| 2b | one mirrored file's bytes altered | the **bytes**-equality half, separately |
| 3 | a real survivor hand-planted in the live package | `test_no_fixed_offsets`, message **unchanged** — the guard was not weakened |
| 4 | `untracked_file` points back at `REPO_ROOT` | the extended residue detector **and** `tests/test_no_leaks.py` itself, via a banned machine-path string landing at the repo root |
| 5 | `scannable_text_files` returns `[]` | `test_the_guard_actually_reports_a_planted_leak` |
| 6 | the contract rule returns `[]` | its three seen-to-fail tests |
| 7 | `parser_probe`'s `write_text` deleted | the anti-vacuity test, with its intended message, plus three others |
| 8 | the pre-fix temp-root glob restored | 10 of 12 concurrent rounds — the before/after pair for deviation 1 |

After every revert: `git status --porcelain --untracked-files=all` clean of probe paths and
`tests/test_no_fixed_offsets.py` green.

### Other measured facts

- **Mirror cost:** 0.31 s, 37 files, 551,657 bytes per package mirror (five rounds, ±0.007 s).
  Well under the plan's 5 s fallback threshold; no session-scoped mirror needed.
- **Stranded mirrors:** the abort child's `os._exit` skips `TemporaryDirectory`'s finalizer by
  design, which stranded a ~646 KB tree in the OS temp root **per suite run, forever** — 108 had
  accumulated. Fixed: mirrors now honour an environment variable naming their parent directory,
  and the repro points it at pytest's `tmp_path`, whose retention policy reaps it. Measured
  **delta 0** across a run afterwards. The 108 pre-existing trees are outside the repository and
  were not swept. Plan risk 13's "~551 KB" figure was the *package* size; the tree on disk is
  646 KB.
- **A cry-wolf control I wrote reddened the leak guard**, correctly. One of the new control
  strings bound a **single-letter** name in a `with` statement, so the source read as that
  letter, a colon, then an escaped newline — which is the Windows-drive-path shape, and exactly
  the escape-sequence false positive `tests/test_no_leaks.py:33-36` documents. Renaming the
  binding to a word fixed it. Described rather than quoted here, because `EXEMPT_PREFIXES` is
  deliberately empty and there is no fenced-code exemption: **this report tripped the same guard
  on its own first draft**, for quoting the string in this very bullet.
- **The mirror's ignore parity** holds on all seven probed paths, including the two
  (`tests/fixtures/x.dat`, `datasets/x.dat`) where git's last-match-wins negations decide it.

### What the suite still cannot prove

Nothing here is retroactive: a checkout that ran the pre-fix code and died inside a probe still
has a real file in it. The residue detector reports such a survivor by name at both sites and
declines to delete it — a sweep fixes neither mode, and silently tidying destroys the evidence
the next reader needs.

## 5. Findings resolved

The acceptance panel (5/5 reviewers, 5/5 verifiers, 0 findings unverified, no degraded lenses)
returned **15 confirmed findings: 1 blocker, 7 majors**. All 15 are addressed.

| ID | Finding | Resolution |
|---|---|---|
| S1 | **blocker** — the anti-vacuity test globs the machine-global temp root | Fixed; see deviation 1 |
| S2 | Phase 5's evidence half skipped | This report; statuses and the Index row advanced |
| S3 | ADR 0022 claimed a standing "mutation test" that does not exist | Reworded to a dated hand-run, citing this report |
| S4 | The contract guard missed write-mode `open`, `shutil` copies, `os.mkdir` | Verb set widened + the limits section rewritten; see deviation 6 |
| S5 | ~646 KB stranded per suite run, unbounded | Eliminated; measured delta 0 |
| S6 | Nothing stopped a caller handing the fixtures the live repo root | `assert_owned`; refuses `REPO_ROOT` and any path under it, at both sites |
| S7 | A `measured` concurrency claim the measurement refuted | Re-measured in a harness that can collide; ADR and memory restated with the harness named |
| S8 | `CLAUDE.md` / `README.md` still said twenty-one ADRs | Both corrected to twenty-two / twenty live |
| S9 | `__file__` as a seed cried wolf on `tmp_path / Path(__file__).name` | Rule keyed on the **base** of the path expression; that shape added as a fifth cry-wolf control |
| S10 | The no-registry refusal was evadable via `startswith("_guard_scope")` | Second, AST-based clause over the strings the guard actually uses |
| S11 | The leak-guard half of the "refusal at both sites" claim was prose | ADR wording narrowed to what is actually tested |
| S12 | The isolation test blamed the fixture for older-revision residue | Now snapshots the glob and asserts no **new** entries |
| S13 | Compensating assertion (a)'s second half was unfailable | Expected set rebuilt independently of `PACKAGE_RELATIVE` |
| S14 | Plan arithmetic: "4 passed" vs 5 | Recorded as deviation 3 |
| S15 | Three deviations existed only as code comments | Recorded as deviations 2, 4 and 5 |

**The blocker is the substantive one.** It is worth stating plainly: implementing a decided plan
faithfully reproduced this request's own defect class one directory up, and the single-session
gates that this bug taught us to distrust all passed. The panel caught it because it ran the
harness the plan's own §4 did not.

## 6. Manual gates & user-run steps

- **`/commit` is next** and is the only sanctioned committer here. Pushing the branch is its
  job; **opening the PR and merging stay yours.**
- **The D6 follow-up is not filed.** Plan Phase 5 step 6 asks for a feature request extending
  the `tree_root` seam to `tests/test_grain_contracts.py` and `tests/test_read_only.py` for
  symmetry. Neither plants anything, so neither is part of this cause. Filing it needs
  `/make-feature-request`, which is a separate pipeline run — flagged rather than skipped
  silently, because *"observed five times, filed zero times"* is the failure this very request
  documents.
- **108 stranded `ootp_guard_mirror_*` trees (~70 MB)** remain in the OS temp root from runs
  predating the fix. Outside the repository, harmless, and not swept — say the word and they go.

## 7. Hand-off

`/commit` next; it will run the doc gate over a diff that touches `CLAUDE.md`, `README.md`, two
`README`s, an ADR and the agent memory. **ADR 0020 is deliberately untouched** and is *not*
invalidated by this change: its `:95-102` residual controls run `scan_source` over strings, which
this change does not alter, and its `:92-93` refusal of a per-site exemption registry is what
this change makes unnecessary rather than contradicts — now mechanical, in
`test_the_guard_has_not_learned_the_probe_filenames`.

Follow-ups this change surfaced:

1. **D6** — the symmetry seam, above.
2. **The contract guard's known gaps** are listed in its own module docstring
   (`from os import makedirs`, bare relative-path literals, taint across a call boundary). None
   is reachable by accident; each is a decision recorded rather than an oversight.
