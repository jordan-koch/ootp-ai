> **Status:** implemented · created 2026-08-17 · decided · next: commit

# Implementation Report — The leak guard now sees files that are not yet staged

> **One-line outcome:** the repo's only leak protection stops enumerating the git index and
> starts seeing what exists · **Acceptance:** the bugfix contract met at Phase 1, all six
> phases landed · **Branch:** `fix-leak-guard-untracked-blindness`
>
> Banned strings are described, never quoted — `tests/test_no_leaks.py` has no fenced-code
> exemption, and refusing one was a decision of this fix (§5 D3 of the plan), not an oversight.

## 1. Acceptance ledger

The bugfix track's contract is *the red repro goes green + a regression test is left behind +
nothing else regresses.* Every row verified by running it, and independently re-run by the
acceptance panel's execution verifier.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| U1 | The red repro goes GREEN | **met** | `208 passed, 62 deselected`, from a baseline of `1 failed, 196 passed`. Green *because of the fix*, not vacuously: `git ls-files` = 146 vs the widened form = 147, the delta being a file this run itself wrote and the pre-fix enumeration could not see |
| U2 | A regression test is left behind | **met** | `tests/test_leak_guard_scope.py` grew 7 → 21 tests |
| U3 | Nothing else regresses | **met** | ruff, `ruff format --check`, `mypy` (40 files) all clean; five `.mjs` guards exit 0; deselected count unchanged at 62, so no marker moved |
| U4 | The ledger row exists | **met** | This table |
| P0 | Baseline recorded on a clean tree | **met** | Clean tree at `0826da6`; `1 failed, 196 passed, 62 deselected`; both enumerations **146 = 146** |
| P1 | Argv swap; repro green without touching it | **met** | One file in the diff; `197 passed`; `tests/test_leak_guard_scope.py` absent from that commit's changes |
| P2 | Encoding + deleted-path hardening, seen to fail | **met** | See §4 — the falsification transcript is preserved below, which is where the plan required it |
| P3 | Second enumeration + `.gitignore` hole | **met** | `foo.lg` now ignored, `roster.lg/x.txt` still ignored; `game_data_offenders()` seam added with three tests |
| P4 | Rename, messages byte-identical | **met** | 10 sites renamed; a scripted diff confirmed **zero** assertion messages changed beyond the identifier; `git grep tracked_text_files -- tests/` returns nothing |
| P5 | Three prose corrections | **met** | With one deviation, recorded in §3 |
| P6 | Record and close | **met** | This report; statuses and the `_done/` move belong to `/commit` Step 4 |

## 2. What shipped

**The fix is one argv.** `tests/test_no_leaks.py` enumerates
`git ls-files --cached --others --exclude-standard` instead of bare `git ls-files`. On a clean
tree that is the identical set, so the widening costs nothing and buys sight of exactly the
files most likely to carry a fresh leak.

Everything else is hardening the widening made necessary or hygiene it made obvious:

- **`git_paths()`** — a shared enumeration seam with `-z` and an explicitly pinned UTF-8
  decode, replacing `text=True`.
- **`is_file()` guard** on the read, because `--cached` still lists tracked-but-deleted paths.
- **`machine_path_violations()` and `game_data_offenders()`** — seams so tests can assert the
  guard *reports*, not merely that it enumerates.
- **Both enumerations widened**, not just the pattern scan.
- **`.gitignore`** now ignores a plain `*.lg` file, not only an `*.lg/` directory.
- **The `keep` suffix set** gained `.js`/`.mjs`/`.jsonl` and is now case-folded. Coverage went
  from 134 scanned to **144 of 148 enumerated**.
- **`tracked_text_files` → `scannable_text_files`**, because a function named for the scope it
  no longer has is how the next agent talks themselves into narrowing it back.
- **Prose**: `/commit`'s staging step, two stale first-sight lines, and the `gitleaks` count in
  `port-residue-sweep`.
- **`requests/feature-requests/secret-scanning/`** filed — the RCA routed a real credential
  scanner to the feature track, and closing without filing would have quietly retired it.

## 3. Deviations from the plan

- **Six commit-gated phases landed as one diff.** `/implement-plan` prescribes one accumulated
  diff and one panel; the plan prescribed a checkpoint per phase. The skill governs the stage.
  Cost, stated plainly: Phase 1's *"`git diff --stat` lists exactly one file"* is not
  reconstructible from history. It **was** checked live at the time, and the property it
  protects — that the repro passed on its own terms rather than by being rewritten — is
  independently evidenced by the 146-vs-147 enumeration measurement in U1.
- **The `gitleaks` sentence in `/commit` was removed.** The plan said explicitly not to touch
  either occurrence, because `port-residue-sweep` owns them. Phase 5 rewrote the surrounding
  paragraph and the false sentence went with it. **Kept rather than reverted** — restoring a
  claim known to be false to preserve a tracker's tidiness is the wrong trade — and that
  request's evidence was corrected to say one occurrence remains, not two.
- **`/commit`'s change is longer than the planned "one sentence, not a restructure".** Deleting
  the manual eyeball, as §5 D8 literally said, would have overstated what the automated check
  buys: the guard does not scan for credentials and nothing else does either. The added text
  says so.
- **The suffix widening was not in the plan.** Raised by the panel, disposed by the operator
  mid-review. Measured clean across all 12 affected files before it landed.
- **The plan said Phase 4 touches "four call sites"; there were ten**, because Phases 2–3 added
  tests between the plan being written and the rename running. Not a change of intent — the
  plan's number was simply stale by the time it was executed.

## 4. Verification & edge cases

**The encoding failure mode, demonstrated in both directions** — the plan required this to be
*watched failing*, and this transcript is where it is preserved:

```
FIXED   (-z + explicit utf-8): True
UNFIXED (text=True, no -z)   : False
   what the unfixed call saw : ['"caf\303\251_bite_probe.md"']
```

Git C-quotes the non-ASCII path *including the surrounding double quotes*, so its apparent
suffix is `.md"`, which fails the `keep` test — the file is dropped **silently**. Preferred
encoding on this machine measures as `cp1252`, so `-z` alone would not have closed it.

**The guard is now seen to fail.** Mutating the scan to a no-op (`if not path.is_file() or
True:`) previously left all 18 guard tests green. After the `machine_path_violations()` seam
and three new tests:

```
no-op scan mutant : 1 failed, 17 passed
restored          : 21 passed
```

**Edge cases exercised:** a nested untracked directory (the shape all three real leaks
actually had — none was at the repo root); a non-ASCII filename; a tracked-but-deleted path; a
suffix outside `keep`; the trailing-NUL split; a gitignored probe under `var/tmp/`; an
untracked `.dat` under `tests/fixtures/`; a plain `.lg` file; and a coverage floor that fails
if the candidate set collapses.

**Not verified:** the `-m gamedata` selection needs the real save and was not run. CI runs
`-m "not gamedata"` only, so this is the full checkable surface.

## 5. Findings resolved

The panel ran at full strength — 7/7 reviewers, 5/5 verifiers, `findings_unverified` **0**, no
degraded lenses — returning 20 confirmed findings, **zero blockers**, 7 majors.

| Finding | Resolution |
|---|---|
| **No test ever watches the guard go red** — a mutant scanning zero files left all 18 tests green | `machine_path_violations()` seam + 3 tests. Mutant now dies. **This was the real one**, and it violated the plan's own §4 standard |
| **No coverage floor** — the set could collapse 134 → 9 undetected | A floor test at ≥ 80, deliberately far below the real count so churn never trips it |
| **12 files enumerated but never opened** | `keep` widened; 144 of 148 now scanned |
| **first-sight `:623`/`:626` still order filing this very follow-up** | Amended; Phase 5 had caught only `:561` and `:757` |
| **`/commit`'s new sentence re-taught the belief the fix removes**, and contradicted itself three lines apart | Rewritten |
| **The guard still described itself as scanning "tracked" files** | Module docstring and both assertion messages corrected — the exact narrow self-description Phase 4 existed to eliminate |
| Case-sensitive suffix match; tautological empty-entry assertion; `port-residue-sweep` count still saying six | All corrected |

**One finding the panel refuted and dropped:** a reviewer claimed the inverted `is_file()`
mutant survives the suite. It does not — measured `1 failed, 14 passed`. The panel corrected
its own lens rather than passing it forward, and the underlying coverage gap was carried on a
different, reproduced mutant.

## 6. Manual gates & user-run steps

None. Everything here is checkable locally and by CI. The one outward-facing step is the PR,
which stays the operator's.

## 7. Hand-off

`/commit` next. It owns the status blockquotes, both Index rows and the `_done/` move — and
**expect the bare-token scan to name every stale reference to this directory once it moves**;
that is the archive workflow working, not a problem.

**What this does not close:**

- **`requests/feature-requests/secret-scanning/`** — nothing in this repo scans for
  credentials. The patterns cover machine paths, home directories and email addresses only.
- **`requests/bugfix-requests/port-residue-sweep/`** — seven instances, including the one
  remaining false `gitleaks` promise at `update-docs/SKILL.md:25`.
- **`--exclude-standard` honours ignore files that are not in version control** (a global
  excludes file, `.git/info/exclude`). Measured by the panel: a global `*.md` rule collapses
  the candidate set. Nobody in this repo has such a rule today; recorded because a future
  contributor might.
