> **Status:** planned · created 2026-08-21 · decided · next: implement

# Implementation Plan — The guard probe plants in a tree it owns

> **One-line goal:** the fixed-offset guard's scope test stops writing into the package the
> guard scans, so neither an interrupted run nor a concurrent reader can produce a phantom
> violation · **Target component:** `tests/` only — no file under `src/` changes.

> **Authoring rule for this document and the report, and it is load-bearing.**
> `tests/test_doc_links.py` resolves every markdown link **and every bare `requests/...`
> token** against the filesystem, with no exemption for a document's own directory and
> **no exemption for a code span** — only fenced blocks are stripped (`strip_fences`). So
> every `requests/...` path that does not yet exist on disk is written inside a fence in
> this document. The one this plan certainly contains:
>
> ```
> requests/bugfix-requests/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md
> ```
>
> Non-`requests/` paths (`tests/fixtures/guard_trees.py`, `docs/decisions/0022-*.md`) are
> **not** scanned by that guard as bare tokens, so a code span is fine for them — but never
> write them as a markdown link before they exist. Run `uv run pytest tests/test_doc_links.py`
> immediately after this plan lands, before Phase 0's first edit.

## 1. Onboarding — read these first

This is a **bugfix**, and its acceptance contract is the bugfix track's, not a feature's:
the committed red reproduction goes green, a regression test is left behind, and nothing
else regresses (`requests/bugfix-requests/README.md:24-26`).

The defect is entirely inside `tests/`. No parser, warehouse, contract, catalog or report
code is implicated; no save byte is read; no MySQL is touched. What *is* at stake is the
credibility of this repo's most load-bearing structural guard — the fixed-offset ban that
[ADR 0020](../../../docs/decisions/0020-sanctioned-lookahead-seam.md) settles.
`tests/test_fixed_offset_guard_scope.py` proves that guard can be **seen to fail** by
writing a real offending module into the live `src/ootp_ai/parser/` package and removing it
in a `finally`; `tests/test_no_fixed_offsets.py` enumerates that same directory. One path,
two owners, **no seam**. Five acceptance panels have hit the resulting phantom red and
filed it zero times.

The work: give the scan a tree root, plant into a byte-faithful copy of the package instead
of the package, pay for the lost fidelity with explicit compensating assertions, apply the
same convention to the worse second site in the leak guard's scope tests, and record the
convention so a third site is never invented.

> **This change may not be delegated to the `data-engineer` subagent.** `tests/` is the
> first entry in its repo-level deny set (`.claude/agents/data-engineer.md:154-165`,
> asserted by `tests/test_agent_contract.py:76-81`), and `docs/decisions/` and `.claude/`
> are in it too. Handing it this spec produces a correct stop-and-report and zero work. The
> main thread implements it. Any read-only subagent used for review gets read-only git.

| # | File | Why |
|---|---|---|
| 1 | `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md` | The decided upstream artifact — consume it, do not re-open it. Read the two-mode table at `:17-21` first: **mode B** (a concurrent reader scanning while a *healthy* run has a probe planted) leaves nothing behind and is what every documented sighting actually was. Its fix sketch at `:139-141` is corrected in §2 below |
| 2 | `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md` | Context; its triage is settled. Its Expected at `:59-61` — *"a test's fixture leaves no trace in the source tree, however it exits"* — is the acceptance sentence. **Its mypy "80 → 81" line at `:84` is an intake-date measurement, not today's baseline** (see §6 risk 9) |
| 3 | `tests/test_fixed_offset_guard_scope.py` | The file being fixed. `PARSER_DIR` `:60`; `parser_probe` `:81-98` (clobber assert `:93`, write `:94`, yield `:96`, `finally` `:97-98`). Its docstring at `:85-86` is the fidelity argument this plan answers rather than deletes. Four plant sites: `:111`, `:126`, `:132`, `:430`. Two tests that must keep calling the guard with **no arguments**: `:137-150`, `:176-184`. Read `:9-14` — the record of two guards that were green while guarding nothing |
| 4 | `tests/test_no_fixed_offsets.py` | The guard being poisoned. `SCAN_ROOT` `:97`; `EXEMPT_MODULES` `:104-107` (two **repo-relative posix strings**); `scan_source` `:339-342`; `parser_modules` `:345-354`; `parser_module_violations` `:357-363`, whose `path.relative_to(REPO_ROOT)` at `:361` is the exact line that makes a naive package-root parameter raise `ValueError`; `test_no_parser_module_seeks_to_a_fixed_offset` `:569-575` |
| 5 | `tests/test_guard_probe_isolation.py` | The committed **red** repro — the acceptance contract itself. `ABORT_CHILD` at `:46-57` is source **text** run in a child process; `:55` calls `parser_probe(name, body)` positionally and `:83-87` asserts exit **97**. This plan is designed so that file needs **zero edits** to go green |
| 6 | `tests/test_leak_guard_scope.py` | The second, worse site. `untracked_file` `:40-53` is structurally identical; `LEAK` `:37` is a deliberately banned machine-path string, so a survivor here poisons the repo's only leak protection. Note the ten planting tests, the live-repo mkdirs at `:89` and `:183`, and the **zero-argument monkeypatch lambda at `:250-252`** that breaks on arity |
| 7 | `tests/test_no_leaks.py` | The guard that site poisons, and the seams Phase 3 threads. `git_paths` `:44-67` shells git with `cwd=REPO_ROOT` at `:62` — which is why un-sharing it needs a `git init` mirror, not a path parameter. `PATTERNS` `:37-41`; the `EXEMPT_PREFIXES` refusal at `:23-31`; `game_data_offenders` `:173-194` whose docstring at `:180-186` records the last-match-wins `.gitignore` measurement the mirror must reproduce |
| 8 | `docs/decisions/0020-sanctioned-lookahead-seam.md` | `:92-93` — *"No per-site exemption registry, ever"* — is the grounded refusal of the name-aware guard. `:95-102` records the residual controls, which this change does not touch, which is why **no ADR amendment is needed** |
| 9 | `tests/fixtures/warehouse.py` `:1-6` | Why a shared harness lives in `tests/fixtures/` and why this repo has **no `conftest.py`** anywhere (verified). Match it; don't break it |
| 10 | `pyproject.toml` | `known-first-party = ["ootp_ai", "fixtures"]` at `:88` with the recorded warm-local/cold-CI import-order failure — the reason the helper belongs under `tests/fixtures/` and nowhere else; mypy strict over `src` **and** `tests` `:91-95`; no xdist `:98-108` |

## 2. Architecture map

### 2.1 The defect

`tests/test_fixed_offset_guard_scope.py:94` writes a real `.py` into `PARSER_DIR` (`:60`),
and `tests/test_no_fixed_offsets.py:352` enumerates `SCAN_ROOT` (`:97`). One path, two
owners, no seam — `parser_module_violations()` takes no root parameter, so the fixture has
no way to ask for a different tree.

**More readers share that tree than the RCA enumerates.** `tests/test_grain_contracts.py:75`
+ `:364-367` walks it; `tests/test_read_only.py:292` + `:344-345` makes a third. Neither
plants anything, so neither is part of the cause — but teaching *one* reader about probe
filenames would leave the others unfixed. **Un-sharing the tree fixes all of them at once,
and that is the architectural argument.**

### 2.2 The seam must be a REPO root, never a scan root — a correction to the RCA's sketch

`scan_source` (`:339-342`) decides exemption by `filename in EXEMPT_MODULES`, and those are
two **repo-relative posix strings** (`:104-107`). `parser_module_violations` builds that
string at `:361` with `path.relative_to(REPO_ROOT).as_posix()`.

So `parser_modules(root=SCAN_ROOT)` as sketched at `ROOT_CAUSE_ANALYSIS.md:139-141` **does
not work**: pointing `root` at a temp *package* directory makes `:361` raise `ValueError`,
and relativising against the package root instead turns every key into
`parser/lookahead.py` — silently un-exempting the sanctioned seam, so the mirror reports
violations production does not, and the natural "fix" is to loosen the rule. All three
planners reached this independently. Prescribed shape:

```python
PACKAGE_RELATIVE = Path("src") / "ootp_ai"
SCAN_ROOT = REPO_ROOT / PACKAGE_RELATIVE                       # keep: the production constant
def parser_modules(tree_root: Path = REPO_ROOT) -> list[Path]
def parser_module_violations(tree_root: Path = REPO_ROOT) -> list[str]   # relative_to(tree_root)
```

A mirror laid out as `<tmp>/src/ootp_ai/...` then yields **byte-identical** repo-relative
strings: allowlist keys, the interior stricter rule and the reported message all behave
exactly as in production.

### 2.3 The fidelity trade, resolved by compensation (gated decision 2, disposed)

`parser_probe`'s docstring (`:85-86`) argues *"the scan enumerates the package on disk, so
the probe has to exist inside it to be a fair test of what the scan actually reads."* That
is true of an **empty** `tmp_path` and false of a **faithful copy**: `shutil.copytree` the
real package and the scan still rglobs a real tree, opens the package's 37 real modules, and
reports a real offender among real neighbours. Measured: 37 files / 551,657 bytes.

What the copy genuinely loses is the assertion that *production* points at the live package.
Buy it back, in the same commit, with **three compensating assertions** — the operator
disposed these as non-negotiable:

- **(a)** `guard.SCAN_ROOT == REPO_ROOT / "src" / "ootp_ai"`, and a no-argument
  `parser_modules()` returns only paths under it.
- **(b)** the mirror's module set **equals** the live one's, and the copies are
  **byte-identical** — so a `copytree` that drops a subpackage, or decays into one lone
  file, fails loudly.
- **(c)** `test_no_parser_module_seeks_to_a_fixed_offset` is asserted **from its own source**
  to call `parser_module_violations()` with no arguments, so nobody can quietly point
  production at a mirror.

Together those assert strictly *more* than the live plant ever did — the live plant never
checked where the default root pointed.

### 2.4 The fixture signature is load-bearing and must NOT change

`ABORT_CHILD` (`tests/test_guard_probe_isolation.py:46-57`) is source **text** executed in a
child process; `:55` calls `parser_probe("_guard_scope_abort_probe.py", OFFENDER)`
positionally and `:83-87` asserts the child exited exactly `97`. **ruff and mypy see nothing
inside that string.** A required third parameter makes the child die on `TypeError` → exit 1,
and the repro then fails with *"the child never reached the probe"* — which reads as a broken
test rather than the bug, and whose cheapest wrong fix is relaxing the exit-code check.

```python
@contextmanager
def mirrored_package() -> Iterator[Path]        # plain contextmanager, NOT a pytest fixture
@contextmanager
def parser_probe(name: str, body: str, tree_root: Path | None = None) -> Iterator[str]
    # tree_root=None -> the fixture builds and owns a private mirror
```

**Consequence, and it is the strongest evidence the track's contract can produce:
`tests/test_guard_probe_isolation.py` needs zero edits and goes green on the fix alone.**
Structural safety is bought better than by a required parameter: after Phase 1 no code path
from `parser_probe` reaches `PARSER_DIR` at all, and that is assertable.

Call sites that need the root open the mirror themselves:

```python
with mirrored_package() as tree, parser_probe(name, OFFENDER, tree_root=tree) as rel:
    violations = guard.parser_module_violations(tree)
```

### 2.5 The second site is the same shape with a worse survivor

`tests/test_leak_guard_scope.py:40-53` writes into `REPO_ROOT / relative` (`:47`) with the
same name-keyed clobber assert and the same `finally`. It plants at the repo root (`:73`),
under `requests/bugfix-requests/` (`:119-120`), as a `.dat` under `tests/fixtures/` (`:174`)
and under `var/tmp` (`:89`, `:183`) — and its bodies carry a **deliberately banned
machine-path string** built at `:37`. `phase-7-acceptance-panel.md:63` recorded it racing
`test_doc_links` (CF-14) and carried it forward unfixed.

Un-sharing it is harder because the guard's scope is a **git index**, not a directory walk:
`git_paths` shells `git ls-files -z --cached --others --exclude-standard` with
`cwd=REPO_ROOT` (`:62`). So the mirror is a `git init`-ed temp repo carrying a **verbatim
copy** of the real `.gitignore`, because `game_data_offenders`'s own measurement
(`tests/test_no_leaks.py:180-186`) depends on git's last-match-wins negations.

**That parity was unconfirmed; the panel measured it (2026-08-21, this tree)** — a `git init`
temp repo with the copied `.gitignore` returns *identical* `git check-ignore --no-index`
verdicts on all seven probed paths, and `git ls-files` worked there **with no commits and no
configured identity**:

```
_leak_guard_probe.md                        not ignored
var/tmp/x.md                                ignored
tests/fixtures/x.dat                        NOT ignored   <- the !tests/fixtures/** negation
datasets/x.dat                              NOT ignored
x.lg                                        ignored
players.csv                                 ignored
requests/bugfix-requests/_nested_probe.md   not ignored
```

The two marked `NOT` are the load-bearing ones: they are where git's last-match-wins
negations decide the verdict, and they are what `tests/test_no_leaks.py:180-186` measures.
Phase 3 re-pins all seven as an executable control rather than trusting this paragraph.

### 2.6 The one-sentence convention

**A guard's scope test may plant only in a tree it owns; a test that reads the live tree
plants nothing.**

## 3. Phased implementation

Six phases. Each ends green on the four gates and hands to `/commit`. **Phase 1 alone closes
the filed bug** — if everything after it were abandoned, the repo is strictly better.

**Before Phase 0.** Confirm `git rev-parse --abbrev-ref HEAD` is a feature branch and not
`main` (`main` is protected and five checkpoints would be unlandable), and that the tree is
clean. This plan lands with the Index row at `requests/bugfix-requests/README.md` moved
`diagnosed → planned` in the same commit, so `/commit`'s status check has nothing to flag at
the first checkpoint.

**Every command in this plan must be PowerShell-safe.** `grep` does not exist here; use
`Select-String`, or better, put the assertion in a test so CI enforces it forever instead of
a human checking once.

---

### Phase 0 — Open the tree seam and prove a mirror is the same tree (no behaviour change; the repro stays red)

**Goal.** Add the seam as a pure default-argument addition that changes nothing for any
existing caller, and discharge by measurement the two claims every later phase rests on.

**Steps.**

1. **Record the baseline before editing anything**, PowerShell-safe — write a two-line
   script into the scratchpad and run `uv run python <script>` rather than a `-c` one-liner
   with embedded quotes. Record `len(parser_modules())` and `len(parser_module_violations())`
   (measured 2026-08-21: **37 and 0**) and `uv run mypy`'s trailing `Success: no issues found
   in N source files` line (measured 2026-08-21 on a clean tree: **81** = 37 `src` + 44
   `tests`). **That recorded number is the only baseline** — the intake's "80" predates the
   repro landing.
2. In `tests/test_no_fixed_offsets.py`, add `PACKAGE_RELATIVE = Path("src") / "ootp_ai"` and
   redefine `SCAN_ROOT = REPO_ROOT / PACKAGE_RELATIVE`. **Keep the name `SCAN_ROOT`** — it is
   the constant compensating assertion (a) pins.
3. `parser_modules(tree_root: Path = REPO_ROOT)` globs `tree_root / PACKAGE_RELATIVE`. Keep
   the non-vacuity assert at `:353`; make its message name the **resolved** root so a
   mis-laid mirror fails loudly instead of passing empty.
4. `parser_module_violations(tree_root: Path = REPO_ROOT)` passes it down and changes `:361`
   to `relative_to(tree_root)`. Add a comment there recording **why the parameter is a repo
   root and not a package root** (§2.2) — that is the line a future refactor will get wrong.
5. Extend both docstrings with the convention and cite this request directory. State that
   production callers pass nothing, on purpose.
6. **Touch no rule.** `FixedOffsetVisitor`, `EXEMPT_MODULES`, `scan_source`, every pinned
   residual and `test_no_parser_module_seeks_to_a_fixed_offset` are untouched in this whole
   plan.
7. Create `tests/fixtures/guard_trees.py` with
   `@contextmanager def mirrored_package() -> Iterator[Path]`:
   `tempfile.TemporaryDirectory(prefix="ootp_guard_mirror_", ignore_cleanup_errors=True)`,
   then `shutil.copytree(REPO_ROOT / "src" / "ootp_ai", root / "src" / "ootp_ai",
   ignore=shutil.ignore_patterns("__pycache__", "_guard_scope*_probe.py"))`, yielding the
   temp **repo root** (not the package dir). **A plain context manager, never a pytest
   fixture** — Phase 1's abort child imports it in a bare process where `tmp_path` does not
   exist. `pathlib` not `os.path` (ruff PTH), fully annotated (mypy strict over `tests/`).
   - **The probe-exclusion in `ignore_patterns` is load-bearing**: without it a survivor from
     an older revision is copied into every mirror, and the new tests report a violation
     nobody planted.
   - Before yielding, assert the fresh mirror reports **zero** violations. That restores real
     meaning to the clobber assert (see Phase 1 step 2).
8. The helper's module docstring is the operative statement of the convention, and justifies
   its siting the way `tests/fixtures/warehouse.py:1-6` does.
9. **Write the import line down, literally** — it is the second-sharpest trap here:
   `from fixtures.guard_trees import mirrored_package`. That is the house pattern at ~20 call
   sites and the only form that works inside the abort child, which does
   `sys.path.insert(0, str(Path(sys.argv[1]) / "tests"))`. A `from tests.fixtures...` or
   relative form passes under pytest and kills the child with `ImportError` → exit 1 → the
   repro fails with *"the child never reached the probe"*.
10. Add `test_the_production_scan_root_is_the_live_package()` — compensating assertion (a).
    Assert exactly two things: `guard.SCAN_ROOT == REPO_ROOT / "src" / "ootp_ai"`, and a
    no-argument `parser_modules()` returns only paths under it. **Do not re-assert the
    allowlist strings** — `test_an_allowlisted_path_matches_what_the_real_scan_builds`
    (`:176-184`) already does exactly that; add a one-line comment pointing at it so the
    pairing is visible rather than duplicated.
11. Add `test_the_mirror_holds_the_same_modules_as_the_live_package()` — compensating
    assertion (b): set equality of repo-relative paths **and** `read_bytes()` equality per
    module. Its docstring must say it runs on a mirror with **nothing planted**, or the
    equality is false by exactly one entry.
12. Add `test_the_mirror_reports_a_planted_offender_with_the_real_path_string()`: inside a
    mirror, write `OFFENDER` to `<tree>/src/ootp_ai/parser/_guard_scope_seam_probe.py` and
    assert `parser_module_violations(tree)` names exactly
    `src/ootp_ai/parser/_guard_scope_seam_probe.py`. **This is the single riskiest assumption
    in the plan** — if it fails, stop and re-plan rather than loosening anything.
13. Add `test_the_tree_is_clean_test_takes_the_default_root()` — compensating assertion (c),
    via `inspect.getsource` matching `parser_module_violations\(\s*\)`.
14. Leave every existing caller unchanged; `tests/test_guard_probe_isolation.py` is untouched.
15. **Run the abort child by hand now**, before Phase 1 changes anything (`uv run python
    <script> <repo-root>`, expect exit **97**), to prove the import path still works under the
    added dependency.
16. **Record the pre-fix mode-B baseline while the bug is still live** (see §4 for the exact
    form) — the after-run needs something to be compared against.
17. Measure and record the `copytree` wall time and the runtime delta on the scope module. If
    the module's runtime grows by more than ~5 s, adopt a session-scoped mirror with per-test
    subdirectories and write down why.

**Acceptance.**

- `uv run pytest -m "not gamedata" tests/test_fixed_offset_guard_scope.py tests/test_no_fixed_offsets.py tests/test_grain_contracts.py` green. **The marker filter is not optional** — `tests/test_grain_contracts.py` carries seven `@pytest.mark.gamedata` tests (`:442`, `:456`, `:482`, `:518`, `:561`, `:586`, `:624`) that land a real snapshot into MySQL, and a bare module selector runs them.
- `uv run pytest tests/test_guard_probe_isolation.py` is **still RED on both tests**. A seam that accidentally turned the repro green would mean the repro is not measuring what it claims.
- `uv run pytest tests/test_doc_links.py` green — the plan document's own fences hold.
- `parser_modules()` still returns 37, `parser_module_violations()` still returns 0.
- Four gates clean; mypy reports **baseline + 1** (the new helper), i.e. 82.
- `git status --porcelain --untracked-files=all` shows **no path under `src/`**, **no `_guard_scope*_probe.py` anywhere**, and beyond that only this phase's intended edits. `git diff --name-only` contains no `src/` path.

**Commit note.** *"Give the fixed-offset scan a tree_root, and prove a copied tree is the
same tree."* Purely additive — every existing call site uses the default, so this reverts
cleanly and leaves the bug exactly as it was.

---

### Phase 1 — Plant in the mirror: the committed repro goes GREEN, unedited

**Goal.** The probe never touches `src/ootp_ai/parser/` again, closing mode A and mode B
together.

**Steps.**

1. Rewrite `parser_probe` to `(name: str, body: str, tree_root: Path | None = None)`. When
   `tree_root` is None it opens its own `mirrored_package()` and owns it for the life of the
   context. **It must stay callable with two positional arguments and must keep yielding a
   plain `str`** — `f"src/ootp_ai/parser/{name}"` — so every `rel in v` assertion at `:113`,
   `:127`, `:432` and `tests/test_guard_probe_isolation.py:112` keeps matching.
2. Keep the clobber assert (`:93`) **and add a comment saying what it now is**: near-vacuous
   against a freshly built mirror by construction, retained for the caller-supplied
   `tree_root` path where two probes in one mirror would collide. Silently converting a live
   check into a tautology is the failure mode `:9-14` exists to refuse; say it out loud.
3. **Replace** the fidelity paragraph at `:85-86` — do not delete it silently and do not
   leave it standing, since it is now false as written. State the replacement: the probe sits
   among the package's **37 real modules**, byte-identical, on a real disk tree; what changed
   is that the package is one nothing else reads. Name the three compensating assertions.
4. Re-document `PARSER_DIR` (`:60`): it survives with a changed role — the live package the
   probe must never reach, and the thing `tests/test_guard_probe_isolation.py:60-62` globs.
5. Move the four plant sites onto mirrors, passing the same tree to the fixture **and** the
   scan: `:104-116`, `:119-127`, `:130-134`, `:421-434`.
   - **`test_the_probe_is_removed_even_though_the_scan_read_it` (`:130-134`) needs the
     two-context form for correctness, not symmetry.** Open `mirrored_package()` in an
     **outer** `with`, the probe in an inner one, and assert against
     `tree / "src" / "ootp_ai" / "parser" / "_guard_scope_cleanup_probe.py"` after the inner
     block exits and before the outer one does. If it uses the default root, the tempdir dies
     with the context and `not path.exists()` passes whether or not the `finally` ran — the
     one assertion in the module that proves cleanup happens would become vacuous.
6. **Rename the two tests whose names would become lies** — `..._in_the_real_tree` at `:104`
   and `:421` → `..._in_a_real_package_on_disk`. A test name that overclaims is this bug in
   miniature; rename in the same commit as the move.
7. Restate the obsolete rationale at `:131` (a leftover no longer breaks the next lint/mypy
   run, because the tree it dirties is disposable), the module docstring at `:18`, and the
   stale *"it has been covering 18"* at `:147` (measured: 37). **The `>= 12` floor at `:146`
   does not move** — it exists to catch a collapse, not to track a number.
8. Leave `test_the_module_set_has_a_floor` (`:145`) and
   `test_an_allowlisted_path_matches_what_the_real_scan_builds` (`:180`) calling the guard
   with **no arguments**, against the live package, and add a one-line comment at each saying
   why. `ROOT_CAUSE_ANALYSIS.md:150` is explicit that moving them buys a vacuous guard, and
   they are exactly the lines a future refactor would "tidy" onto the mirror.
9. Add `test_no_probe_is_ever_written_into_the_live_package()`: drive `parser_probe` with no
   `tree_root` and assert `sorted(PARSER_DIR.glob("_guard_scope*_probe.py")) == []` **during
   and after** the with-block. Its docstring must name Phase 2's residue detector and say why
   they are not the same test (this one drives the fixture; that one observes the tree at
   module scope).
10. **Add the anti-vacuity test the merge dropped.** After the fix, a `parser_probe` that
    planted *nothing at all* would satisfy every assertion above — the exact "green while
    guarding nothing" shape this module was written to refuse. So assert, inside the
    default-root with-block, that exactly one path matching
    `ootp_guard_mirror_*/src/ootp_ai/parser/<name>` exists under `tempfile.gettempdir()`, and
    that a scan of that tree names the yielded `rel`. Add "delete the `write_text` and watch
    this die" to the mutation list.
11. **Do not edit `tests/test_guard_probe_isolation.py`.** Optionally append one line to its
    module docstring recording that it now passes and what fixed it. If you find yourself
    changing an assertion there to get green, **the fix is wrong, not the test**.
12. **Run the mutations before trusting any of it** (§4).

**Acceptance.**

- `uv run pytest tests/test_guard_probe_isolation.py` **green, with that file's assertions unedited.** This is the RCA's acceptance contract.
- **Mode A, by hand:** run the abort child, confirm exit **97**, then confirm `src/ootp_ai/parser/` holds no `_guard_scope*_probe.py`.
- **Mode B, measured** in the form §4 prescribes, with the round count recorded and compared against Phase 0's pre-fix baseline.
- Mutations 1, 2, 3 and 6 recorded as watched-to-die, and **after each revert** `git status --porcelain --untracked-files=all` shows no probe path and `uv run pytest tests/test_no_fixed_offsets.py` is green.
- `uv run pytest -m "not gamedata"` green; four gates clean; mypy still 82.
- The six `CRY_WOLF` entries (`:229-270`) and the five `..._is_a_documented_hole` tests (`:285`, `:324`, `:338`, `:371`, `:391`) are present and unchanged in rule. *(Use those two counts, not a single figure: the module docstring at `:28` says five while ADR 0020`:95` says six — a pre-existing discrepancy that belongs to `/update-docs`, not to this request.)*

**Commit note.** *"Plant the fixed-offset probe in a mirrored package, not in the package."*
**This is the shippable fix.**

---

### Phase 2 — A survivor names itself (hardening (a), gate disposed 2026-08-21: report-only)

**Goal.** If an older revision left a probe behind — the one case no design change reaches
retroactively — the run says so **by name, from a sibling test**, so ADR 0020's
no-exemption-registry rule stays untouched and the guard's verdict is unchanged.

> **Gate.** `ROOT_CAUSE_ANALYSIS.md:157-164` marks this tier *gated, not assumed*. The
> operator disposed it on 2026-08-21: **report-only accepted; the sweep declined; the
> name-aware guard message declined outright.** This phase builds only the accepted half.

**Steps.**

1. Add `test_no_probe_residue_is_present_in_the_working_tree()` to
   `tests/test_guard_probe_isolation.py`, reusing `_planted_probes()` (`:60-62`) over the
   **live** `PARSER_DIR`. The message names the file, says it is a fixture artifact from an
   interrupted run of an **older** revision, says to delete it, and points at this request.
2. **It reports and deletes nothing**, and its docstring says why: a sweep fixes neither
   mode, silent tidying destroys the evidence the next reader needs, and it would need this
   repo's first `conftest.py`. **Do not gitignore `_guard_scope*_probe.py`** — that would
   remove `git status --porcelain --untracked-files=all` as a detection signal, which is the
   signal the intake used to identify the phantom.
3. Add `test_the_probe_fixture_cannot_reach_the_live_package()` — the structural half of the
   convention, and **it must be AST-based, not a substring check**. `parser_probe` legitimately
   contains the literal `"src/ootp_ai/parser/"` in its yield and discusses the live package in
   its rewritten docstring, so a text scan cries wolf on code this very plan mandates. Parse
   `inspect.getsource(parser_probe)`, walk it, and assert no `ast.Name` with `id` in
   `{"PARSER_DIR", "REPO_ROOT"}` appears — which ignores strings, docstrings and comments by
   construction.
4. **Make the ADR-0020 check a test, not a shell command.** Assert that
   `Path("tests/test_no_fixed_offsets.py").read_text()` contains no `_guard_scope` token — the
   guard learned no probe names, and a prose criterion checked once never fires again.
5. Extend the module docstring of `tests/test_guard_probe_isolation.py` with the resolution:
   the seam, the mirror, and the explicit refusal to teach the guard probe names, citing ADR
   0020 `:92-93`. **Record there that the mode-B repro's ongoing regression value drops after
   the fix** — post-fix, `leaked == []` is satisfied by a fixture that does nothing — and name
   what carries the property instead: Phase 1's steps 9 and 10, and Phase 0's step 12.
6. Add a comment near `parser_module_violations` recording that the guard deliberately does
   **not** recognise probe filenames, and why, so a future reader does not re-propose it.

**Acceptance.** `uv run pytest tests/test_guard_probe_isolation.py` — 4 passed. With a
hand-planted `src/ootp_ai/parser/_guard_scope_probe.py`: the residue test is red and names the
file and the cause, **and** `test_no_parser_module_seeks_to_a_fixed_offset` is also red with
its message **unchanged from today's**. Delete the plant; both green. Four gates clean.

**Commit note.** *"A surviving probe now names itself, from a sibling test rather than the
guard."*

---

### Phase 3 — The class, not the instance: the leak-guard probe stops writing into the live repo

**Goal.** Apply the same convention to the worse second site, so a survivor can no longer drop
a deliberately banned machine-path string into the repo root.

> **Ordered so no step depends on a later one.** The panel's draft put the parity control
> first, where it could not compile.

**Steps.**

1. Add `mirrored_repo() -> Iterator[Path]` to `tests/fixtures/guard_trees.py`: a tempdir,
   `git init -q` (capture output; do not assume a default branch name and **never `git
   commit`** — CI has no configured identity), copy `REPO_ROOT/.gitignore` **verbatim**, and
   `mkdir` the directories the probes address (`var/tmp`, `tests/fixtures`,
   `requests/bugfix-requests`, `datasets`).
   - Copy the `.gitignore` with `shutil.copy2`, **not** `write_text` — `copy2` is outside
     Phase 4's verb set and is already pinned as deliberately allowed by
     `tests/test_read_only.py:402`, so the helper does not trip the guard it enables.
2. Thread the root through `tests/test_no_leaks.py`. **Write the signatures literally** —
   `git_paths` is variadic, so its parameter is necessarily **keyword-only**, and the obvious
   wrong spelling binds `"--cached"` to `repo` and runs git in a directory named `--cached`:

   ```python
   def git_paths(*args: str, repo: Path = REPO_ROOT) -> list[str]
   def scannable_text_files(repo: Path = REPO_ROOT) -> list[Path]
   def machine_path_violations(repo: Path = REPO_ROOT) -> list[str]
   def game_data_offenders(repo: Path = REPO_ROOT) -> list[str]
   def is_git_ignored(rel: str, repo: Path = REPO_ROOT) -> bool
   ```

   Update `cwd=REPO_ROOT` at `:62`, `REPO_ROOT / rel` at `:103`, `relative_to(REPO_ROOT)` at
   `:149`, `cwd` at `:229`, and the internal calls at `:100`, `:148`, `:192` (by keyword).
   **Change no pattern, no `keep` set, no `EXEMPT` (`:21`) and no `EXEMPT_PREFIXES` (`:31`)** —
   the last being deliberately empty is a decision with its own written cost at `:23-31`.
3. Land the parity control: `test_the_mirror_repo_ignores_what_this_repo_ignores()`, pinning
   all seven verdicts pairwise (§2.5). **Include the non-ASCII enumeration property** among
   the pins, because the test that depends on it (`:127-141`) moves onto the mirror in step 4.
4. **STOP HERE for the off-ramp decision.** If any verdict differs on this machine or in CI,
   or `mirrored_repo` proves unstable (git availability, `safe.directory`, init warnings),
   **revert steps 1-2 and stop after Phase 2** — then file the leak-guard site **loudly**: a
   new bugfix request with its own Index row, never a sentence in a report. Do not half-land
   it, and do not weaken a leak-guard assertion to fit the harness.
5. Rewrite `untracked_file` (`:40-53`) to `(relative: str, body: str, root: Path | None = None)`
   — same shape as `parser_probe`, root **last** and optional. Keep the clobber assert and the
   `finally` verbatim; rewrite the docstring the way Phase 1 rewrote `parser_probe`'s.
6. Move the ten planting tests onto `mirrored_repo()`, passing the same root to the guard call
   in the same test: `:64-78`, `:81-94`, `:113-124`, `:127-141`, `:158-162`, `:165-178`,
   `:181-185`, `:188-193`, `:203-215`, `:218-221`. **Delete the two
   `(REPO_ROOT / "var" / "tmp").mkdir(...)` lines at `:89` and `:183`** — `mirrored_repo`
   creates them.
7. **Fix the monkeypatch arity at `:250-252` in the same edit**: `lambda: [...]` becomes
   `lambda repo=REPO_ROOT: [...]`. Once `scannable_text_files` takes a parameter,
   `machine_path_violations` calls the lambda with an argument and it raises `TypeError` — red
   for an unrelated reason, and the cheapest wrong fix is deleting the test, which would
   restore the crash its docstring at `:244-248` records.
8. **Keep on the real repo, with no root argument, each with a comment saying why:**
   `test_the_probe_string_is_one_the_guard_actually_bans` (`:56-61`),
   `test_no_ignored_directory_leaks_into_the_candidate_set` (`:97-105`),
   `test_enumeration_yields_no_empty_entries` (`:144-155`), and
   `test_the_candidate_set_has_a_floor` (`:224-238`). The floor is also the compensation for
   the mirror being near-empty: **the mirror proves enumeration semantics, the real repo proves
   scale.**
9. Add `test_the_production_enumeration_root_is_the_repo()` — and make it non-vacuous the way
   Phase 0's twin is: pin via `inspect.getsource` that `test_no_machine_paths_or_identifiers`
   and `test_game_data_is_not_tracked` call their helpers with **no arguments**, not merely
   that a defaulted call equals an explicit one.
10. Add `test_the_leak_probe_fixture_cannot_reach_the_live_repo()`, AST-based, mirroring
    Phase 2 step 3.
11. Extend the residue detector to refuse `_leak_guard*probe*` residue at the four sites the
    module plants into. **Hardcode the four repo-relative globs** with a comment citing
    `tests/test_leak_guard_scope.py:73`, `:90`, `:120`, `:174` as their origin — a residue
    detector that imported the module whose residue it hunts would fail to collect if that
    module ever broke.

**Acceptance.**

- `uv run pytest tests/test_leak_guard_scope.py tests/test_no_leaks.py tests/test_doc_links.py` green with **no test lost**. **No pre-existing assertion message is edited** — read the diff hunk by hunk; an edited message inside a mechanical rename is how a weakening gets laundered (the in-repo precedent is recorded in the leak-guard fix's own implementation review).
- During and after the run, and after killing a run mid-suite, `git status --porcelain --untracked-files=all` shows no `_leak_guard*` path at the repo root, under `requests/bugfix-requests/`, under `var/tmp` or under `tests/fixtures/`.
- `Select-String -Path tests\test_leak_guard_scope.py -Pattern 'REPO_ROOT'` shows no remaining **write, mkdir or plant target** — only read-side uses (the floor, the junk-directory tests, the parity pins).
- Mode B for this site, measured in §4's form. This is what closes CF-14.
- Mutations 4 and 5 recorded as watched-to-die.
- Four gates clean; mypy still 82.

**Commit note.** *"Probe the leak guard in a repo it does not protect."* Independently
revertible; reverting leaves Phase 1's fix intact.

---

### Phase 4 — One convention, enforced: no test creates files in a tree a guard reads (SEVERABLE)

**Goal.** Make a third instance unrepresentable rather than merely discouraged.

> **Void if Phase 3 took its off-ramp.** A contract guard whose allowlist names the very site
> that was severed is a guard satisfied by adding entries — the shape ADR 0020 `:92-93`
> forecloses. If Phase 3 was severed, skip this phase, record that the convention is
> prose-plus-helper-docstring only, and attach the guard to the follow-up request instead.

**Steps.**

1. Create `tests/test_probe_isolation_contract.py`. Rule: within `tests/**/*.py`, a
   **creative** write — `.write_text(`, `.write_bytes(`, `.touch(`, `.mkdir(`, `os.makedirs`
   — whose target derives from a name bound to `REPO_ROOT`, directly or through a module
   constant such as `PARSER_DIR`, is a violation.
   - **`.unlink(` is deliberately NOT in the verb set**, and the exclusion is what keeps the
     zero-allowlist claim true: `tests/test_guard_probe_isolation.py:97` deletes a survivor
     under the live `PARSER_DIR`, and Phase 2 keeps that block exactly as it is. Deleting a
     probe that should not exist is not planting one. The verb set then matches
     `tests/test_read_only.py:337`'s `CREATIVE_CALLS` exactly — an in-repo precedent rather
     than a new list.
2. **AST-first, never grep.** `tests/test_read_only.py:337` holds those verbs as string
   literals and `:398` asserts on a literal `.write_bytes(` line; a text scan cries wolf on
   the repo's own write guard. `FixedOffsetVisitor` demonstrates the derived-name tracking to
   imitate.
3. Expose the rule through a `scan_source(source, filename)`-shaped seam so the guard can be
   asserted to **report**, not merely to enumerate.
4. Pin it against a planted offender string (the shape `:92-94` used to have) **and four**
   cry-wolf controls drawn from real lines: a write under `tmp_path`
   (`tests/test_snapshot_semantics.py:119-124`); a write under a fixture-built root
   (`tests/test_save_enumerator.py:39-44`); a `REPO_ROOT`-derived **path construction that is
   read, not written** (`tests/test_no_leaks.py:103`); and — the shape this plan's own helper
   introduces — a write whose **target** is mirror-derived while its **source argument** is
   `REPO_ROOT`-derived. The rule keys on the target expression, and that fourth control is
   what proves it.
5. Exempt exactly one file — the contract module itself, which necessarily contains the
   strings it bans — following `tests/test_no_leaks.py:21`'s single-entry precedent, and
   assert the exemption count the way `test_the_allowlist_is_exactly_two_entries` does.
6. Land with **zero other allowlist entries**. Measured: the complete set of `REPO_ROOT`-derived
   creative writes under `tests/` is `test_fixed_offset_guard_scope.py:94`,
   `test_leak_guard_scope.py:49`, and the two mkdirs at `test_leak_guard_scope.py:89,183` — all
   four removed by Phases 1 and 3. **A non-empty allowlist here means an earlier phase left
   something behind.**
7. Run mutation 6: make the rule return `[]` and confirm the seen-to-fail tests die; restore.

**Acceptance.** `uv run pytest tests/test_probe_isolation_contract.py` green with zero
allowlist entries beyond the self-exemption. The guard is seen to fail: the planted offender
reports, the four cry-wolf controls do not fire, the no-op mutation was watched to kill the
module. Four gates clean; mypy reports **baseline + 2**, i.e. 83. `git diff --name-only`
still contains no `src/` path.

**Commit note.** *"Guard the guards: no test creates files in a tree a guard reads."* Fully
severable.

---

### Phase 5 — Record the convention where it binds the next agent, and close the request

**Steps.**

1. **APPEND** a dated `measured` entry to `.claude/agents/data-engineer-memory.md`. **Do not
   edit the 2026-08-18 entry at `:351-356`**, which prescribes the superseded pattern — the
   file is append-only by its own contract (`:39-53`), and `:340-350` shows the house form for
   dating a prior entry. Use the bullet shape at `:25-37` with a valid epistemic label
   (`tests/test_agent_contract.py:84-95` fails the build without one) and inline-code paths,
   never markdown links.
2. Write ADR 0022 at `docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md` (0001–0021
   exist). The decision: a guard's scope test plants only in a tree it owns; a test that reads
   the live tree plants nothing; fidelity is bought with a byte-faithful copy plus a
   compensating assertion that production reads the original. It **must** carry a
   `## Consequences` section stating the **cost** in as many words —
   `tests/test_repo_structure.py:43-57` fails an ADR that only lists benefits. Name the cost
   honestly: the end-to-end test now reads a copy, and two helper trees exist that must be kept
   faithful. Index it in `docs/decisions/README.md` and keep the numbering sequential.
3. **Do not edit ADR 0020.** Its `:95-102` leans on residual controls that run `scan_source`
   over strings, untouched here. Record the not-invalidated judgement in the report rather than
   amending an accepted ADR.
4. Add a bullet to `tests/fixtures/README.md` naming the **class**, not a second instance:
   shared test harnesses imported by name — `synthetic.py`, `warehouse.py`, `reports.py`,
   `tiers.py`, `guard_trees.py` — with the no-`conftest.py` reasoning cited to
   `tests/fixtures/warehouse.py`. The directory already holds four such modules while the
   README describes committed data fixtures only.
5. Write the implementation report:

   ```
   requests/bugfix-requests/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md
   ```

   It carries: the red→green evidence with the repro file unedited; the mode-A exit-97 run; the
   mode-B round counts for both sites, against Phase 0's pre-fix baseline; the copytree and
   `git init` timings; the seven parity verdicts; all six mutations watched to die; the
   unchanged 37-modules/0-violations baseline; the note that the mode-B repro's regression value
   drops post-fix and what carries it instead; and an explicit section on **what was refused and
   why** — the sweep as a fix, and the name-aware guard message.
   - **Describe temp locations by shape only** — *"a `TemporaryDirectory` under the OS temp
     root, prefixed `ootp_guard_mirror_`"* — never by absolute path. `tests/test_no_leaks.py:38`
     bans a drive-lettered path and `:39` a `/Users/` path, `.md` is in the scanned set, and
     `EXEMPT_PREFIXES` is deliberately empty (`:23-31`). A report about a leak cannot quote the
     leak.
6. **File the deferred follow-up** rather than leaving it as an observation: giving
   `tests/test_grain_contracts.py` and `tests/test_read_only.py` the same `tree_root` seam for
   symmetry. Neither plants anything, so neither is part of this cause — file it through
   `/make-feature-request`. *"Observed five times, filed zero times"* is the failure this very
   request documents.
7. Do **not** retro-edit the `BUGFIX_REQUEST.md` or `ROOT_CAUSE_ANALYSIS.md` bodies — they quote
   the old docstring and that is the historical record. Advance their status blockquotes, and
   move the Index row in `requests/bugfix-requests/README.md` from `planned` to `fixed`, with the
   note amended to record the two-site outcome (or the Phase 3 off-ramp, if taken).
8. Check whether `first-sight`'s follow-up 3 — the Phase 10 record of this sighting — should now
   be marked resolved, and let `/update-docs` judge the rest of the doc surface, including
   whether `CLAUDE.md`'s project-map line for `tests/` needs anything. **Do not restate the new
   convention inside `CLAUDE.md`'s build-rulebook section** — that file names the rulebook rather
   than restating it.
9. Land through `/commit`, then **ask** before opening the PR.

**Acceptance.** `uv run pytest tests/test_doc_links.py tests/test_repo_structure.py
tests/test_agent_contract.py` green. The memory file has exactly one **more** entry and zero
changed lines above it — `git diff` shows an append only. The Index row and all four artifact
status blockquotes agree. `/update-docs` reports no outstanding drift, with the
ADR-0020-not-invalidated judgement **recorded rather than assumed**. Final full gate on a clean
tree in one pass. `git diff --name-only main` lists no path under `src/`.

**Commit note.** *"Record the probe-isolation convention: ADR 0022, a superseding memory entry,
and the two refusals."*

## 4. Testing & verification

**Red → green, exactly.** `uv run pytest tests/test_guard_probe_isolation.py` fails both tests
today. After **Phase 1** both pass **with that file's assertions unedited**. Phase 0 must *not*
turn it green — that is an acceptance criterion in its own right.

**Four gates per checkpoint, mirroring CI (`.github/workflows/ci.yml:45-57`):**

```
uv run ruff check .
uv run ruff format --check .      <- not optional: the intake's second red gate
uv run mypy                       <- strict over tests/ too
uv run pytest -m "not gamedata"
```

**The working-tree gate, stated as a property rather than "prints nothing"** — every checkpoint
runs with the phase's own uncommitted edits, so an absolute reading is unsatisfiable. After a
full suite run, `git status --porcelain --untracked-files=all` must show **no path under
`src/`**, **no `_guard_scope*_probe.py` anywhere**, and **no `_leak_guard*` path** at the repo
root, `var/tmp/`, `requests/bugfix-requests/` or `tests/fixtures/` — beyond that, only the
phase's intended edits.

**mypy file count per phase** (read from the trailing `Success: no issues found in N source
files` line; baseline measured 2026-08-21 = **81**): 82 after Phase 0, unchanged through Phases
1–3, 83 after Phase 4.

### Two things that must be MEASURED, not asserted

No single-session run can prove either — `pyproject.toml:98-108` declares no xdist and no
parallel plugin, which is exactly why this has cost five reviewers and zero builds.

1. **Mode A, durability.** Run the abort child directly; confirm exit **97** (any other code
   means it never reached the probe); confirm no probe remains.
2. **Mode B, concurrency — with a concrete form and a pass/fail definition.** Launch
   `uv run pytest tests/test_no_fixed_offsets.py -m "not gamedata"` in a **background** loop
   while running `uv run pytest tests/test_fixed_offset_guard_scope.py` in a foreground loop.
   **Red = any non-zero exit in either loop across N rounds**, N ≥ 10, with both exit-code
   streams recorded. Run it once at the end of Phase 0 (bug live — this is the reproduction) and
   again after Phase 1 (must be uneventful). After Phase 3, the same against
   `tests/test_leak_guard_scope.py` vs `tests/test_no_leaks.py tests/test_doc_links.py`.
   **"Green in CI" is not evidence for this property.**

### Mutation testing is mandatory here, not a nicety

`tests/test_fixed_offset_guard_scope.py:9-14` records two guards that were green while guarding
nothing. Six mutations, each applied, observed, reverted, and recorded:

| # | Mutation | Must kill |
|---|---|---|
| 1 | `mirrored_package` yields `REPO_ROOT` | the repro, with its two original messages |
| 2 | the mirror copies only `__init__.py` | the mirror set/bytes equality test |
| 3 | hand-plant a real survivor | `test_no_fixed_offsets`, message **unchanged** — the guard is not weakened |
| 4 | `untracked_file` points back at `REPO_ROOT` | the extended residue detector |
| 5 | `scannable_text_files` returns `[]` | `test_the_guard_actually_reports_a_planted_leak` |
| 6 | Phase 4's rule returns `[]` | its seen-to-fail tests |
| 7 | delete `parser_probe`'s `write_text` | Phase 1 step 10's anti-vacuity test |

**Scope each mutation run to one module**, and after every revert require a clean
`git status --porcelain --untracked-files=all` **and** a green `tests/test_no_fixed_offsets.py`
before continuing — mutation 1 restores this very bug on the implementer's tree, and an
interrupted mutation run leaves a survivor that poisons every later measurement in the phase.

### Untouched and load-bearing — must keep observing PRODUCTION

`test_the_module_set_has_a_floor` (`:145`), `test_an_allowlisted_path_matches_what_the_real_scan_builds`
(`:180`), `test_the_candidate_set_has_a_floor` (leak side, `>= 80`),
`test_no_ignored_directory_leaks_into_the_candidate_set`, `test_enumeration_yields_no_empty_entries`.
Moving any of them onto a mirror buys a vacuous guard.

### Nothing-else-regresses, in order of strength

1. **No file under `src/` changes** — `git diff --name-only` carrying no `src/` path. It also
   means the `gamedata` suites cannot regress, so their absence from the local gate is sound
   rather than convenient.
2. **The scanning rules are untouched** — the six `CRY_WOLF` entries and the five documented-hole
   tests still pass and are still present; the leak guard's `PATTERNS`, `keep`, `EXEMPT` and
   `EXEMPT_PREFIXES` are unchanged.
3. **Before/after pass counts** from `--junit-xml`, not a summary line, differing only by tests
   deliberately added or renamed.

### Out of scope, and it must stay that way

No `gamedata` run, no MySQL, no save, no `players.csv`. `uv run pytest -m gamedata` is not
evidence for anything here. If a `gamedata` test fails, something else is wrong — do not absorb
it into this request.

### What the suite cannot prove, stated plainly

Nothing here proves a probe never survives on a machine running a revision from **before**
Phase 1 — no design change is retroactive. Phase 2's residue detector is the only coverage of
that case, and it reports rather than sweeps on purpose.

## 5. Decisions

**Disposed by the operator, 2026-08-21** (all six followed the panel's recommendation):

| # | Decision | Disposition |
|---|---|---|
| D1 | Does the leak-guard site land here or become its own request? | **Here, as Phase 3**, with a measured parity control and an explicit off-ramp |
| D2 | Is a byte-faithful copy sufficient fidelity? | **Accept the copy**, with the three compensating assertions treated as non-negotiable |
| D3 | Hardening (a) sweep, and (b) a name-aware guard message | **(a) report-only, no sweep, no gitignore entry. (b) declined outright** on ADR 0020 `:92-93` |
| D4 | Is Phase 4's AST contract guard in scope? | **In, and severable**, AST-based, zero allowlist |
| D5 | ADR 0022, or a lighter record? | **Write ADR 0022**; do not amend ADR 0020; do not restate in `CLAUDE.md` |
| D6 | Extend the seam to `test_grain_contracts.py` / `test_read_only.py`? | **No** — file it as a named follow-up instead (Phase 5 step 6) |

**Baked into the plan by the panel:**

| # | Decision | Rationale |
|---|---|---|
| P1 | The seam is a **repo** root, not a scan root — a correction to `ROOT_CAUSE_ANALYSIS.md:139-141` | The exemption key is a repo-relative posix string built at `:361`; a package root raises `ValueError`, and relativising against it silently un-exempts the sanctioned seam. All three planners reached this independently |
| P2 | `parser_probe` keeps its **two-positional call shape** and its plain-`str` yield | `ABORT_CHILD` is source text invisible to ruff and mypy. This is what makes the committed repro go green **unedited** — the strongest red→green evidence available |
| P3 | Structural safety comes from there being **no code path** from the fixture to the live tree, asserted from source — not from a required parameter | Same enforcement, no cost to the repro |
| P4 | The mirror builders are **plain context managers** in `tests/fixtures/guard_trees.py` — never pytest fixtures, never a `conftest.py` | The abort child imports them in a bare process with no `tmp_path`; `fixtures` is declared first-party at `pyproject.toml:88`, where the warm-local/cold-CI import-order failure is recorded; this repo has no `conftest.py` anywhere, deliberately |
| P5 | `.unlink(` is **excluded** from Phase 4's verb set | Otherwise the zero-allowlist claim is false on day one: the repro's own `finally` deletes a survivor under the live `PARSER_DIR`. Deleting a probe that should not exist is not planting one, and the resulting verb set matches `tests/test_read_only.py:337` exactly |
| P6 | Every coverage floor and junk-directory test keeps observing **production**, with a comment saying so | `ROOT_CAUSE_ANALYSIS.md:150`; these are the exact lines a future refactor would "tidy" onto a mirror |
| P7 | Tests whose names would become lies are **renamed in the same commit** as the move, and obsolete docstrings are **replaced**, not left standing | A name that overclaims is this bug in miniature |
| P8 | No `src/` change, no rule change, no ADR 0020 amendment | The rule is not at issue; **where the test that proves it does its work** is |

## 6. Risks & gotchas

1. **The signature trap.** `ABORT_CHILD` calls `parser_probe` positionally inside a string ruff and mypy cannot see. A required parameter makes the child exit 1 and the repro fail with *"the child never reached the probe"* — reading as a broken test. Mitigation: P2. If a future change must alter the signature, `ABORT_CHILD` changes in the same hunk.
2. **The exemption string fails silently.** Relativise against a package root and the two sanctioned modules stop being exempt inside the mirror; the mirror then reports violations production does not, and the natural "fix" is to loosen the rule. Mitigations: P1, Phase 0 step 12, and keeping `:176-184` on production.
3. **A mirror that is not a real package is the weakening the fixture warned about.** The vacuity assert at `:353` catches an *empty* mirror but not a **one-file** one. Mitigation: Phase 0 step 11 (set **and** bytes equality) plus mutation 2.
4. **A live survivor gets copied into every mirror.** Residue from an older revision is inside `src/ootp_ai/parser/`, so a faithful copy inherits it and the new tests report a violation nobody planted. Mitigation: the probe-exclusion in `ignore_patterns` plus the zero-violations assertion before yielding (Phase 0 step 7).
5. **Weakening the guard to close the bug is the failure this request exists to prevent.** Nothing here changes `FixedOffsetVisitor`, `EXEMPT_MODULES`, `scan_source` or any residual, and mutation 3 exists to prove it.
6. **ADR 0020 `:92-93` forecloses the tempting message fix.** If the residue test feels indirect, an implementer may reach for teaching the guard about `_guard_scope*_probe.py`. That is a per-site exemption registry, explicitly foreclosed, and after Phase 1 it is unreachable dead code inside the fixed-offset ban's enforcement.
7. **The monkeypatch at `tests/test_leak_guard_scope.py:250-252` breaks on arity** the moment `scannable_text_files` takes a parameter — red for an unrelated reason, and the cheapest wrong fix deletes a test that guards a real crash.
8. **`mirrored_repo` shells out to git, and CI is where it will surprise you.** Ownership/`safe.directory`, default-branch hints and git availability differ between a Windows dev box and ubuntu-latest. **Never `git commit` in the mirror** — CI has no configured identity. If it is flaky, take the off-ramp: an intermittently red guard *is* the defect being fixed.
9. **`--exclude-standard` reads more than `.gitignore`** — `.git/info/exclude` and any global excludes file also apply. The measured parity held on this tree; a machine with a global excludes file could differ, which is what the seven pinned verdicts and the off-ramp exist for.
10. **The mypy baseline in the intake is stale.** `BUGFIX_REQUEST.md:84`'s "80 → 81" was measured before the repro landed; a clean tree today reports **81**. An implementer who trusts 80 will read a clean checkout as carrying a survivor and go hunting for a phantom — the exact cost this request exists to stop.
11. **A rename or signature change can launder a weakened assertion.** Ten leak-guard tests and four fixed-offset tests move. Read the diff hunk by hunk; the only messages that may change are the ones this plan names.
12. **Do not build either mirror inside the repo working tree.** A mirror under `var/` recreates the bug at one remove — `tests/test_grain_contracts.py:364-367` and the leak guard's own enumeration would both see it. Tempdirs only, and the per-process temp root is precisely what closes mode B.
13. **The abort child leaks one tempdir per run, by design.** `os._exit(97)` kills the finalizer, so a ~551 KB mirror survives in the OS temp directory. That is inherent to reproducing an uninterruptible death and is harmless — it is outside the repo, which is the whole point. Use the `ootp_guard_mirror_` prefix so it is identifiable, and record it in the report **by shape, never by absolute path** (risk 15).
14. **Windows cleanup can raise.** An AV handle on a freshly written `.py` is one of this bug's own named causes; `shutil.rmtree` on a tempdir can hit it too. `ignore_cleanup_errors=True` — and never widen that tolerance to any repo-side assertion.
15. **The report can redden the leak guard.** Quoting a mirror's absolute path in a tracked `.md` trips `tests/test_no_leaks.py:38-39`, in the very change whose Phase 3 re-roots that guard's own scope tests. Describe temp locations by shape.
16. **Forward references break a blocking check.** `test_doc_links` resolves bare `requests/...` tokens with no exemption for a document's own directory and **no code-span exemption** — only fences. The report path this plan names is fenced for that reason.
17. **mypy is strict over `tests/` and ruff runs `PTH` there.** Every new helper, parameter and context manager needs full annotations; `pathlib`, never `os.path`.
18. **Phase 5's artifact gates fail late if ignored.** A new ADR must be indexed, sequentially numbered and must state its **cost**; a memory entry must carry a valid epistemic label in the exact bullet shape and use inline-code paths, never markdown links.

## 7. Files to touch (checklist)

- [ ] `tests/test_no_fixed_offsets.py` — Phase 0: `PACKAGE_RELATIVE`, `tree_root` on both functions, `relative_to(tree_root)` at `:361` with the why-comment; Phase 2: one comment. **No rule change.**
- [ ] `tests/fixtures/guard_trees.py` — **new**, Phase 0 (`mirrored_package`) and Phase 3 (`mirrored_repo`). Plain context managers; docstring states the convention.
- [ ] `tests/test_fixed_offset_guard_scope.py` — Phase 0 adds four tests; Phase 1 rewrites `parser_probe`, replaces the fidelity docstring, moves four plant sites, renames two tests, truths up `:18`/`:131`/`:147`, adds two tests.
- [ ] `tests/test_guard_probe_isolation.py` — **assertions NOT edited** (it goes green on Phase 1 alone). Phase 2 adds the residue detector, the AST fixture assertion, the ADR-0020 token check and a docstring paragraph.
- [ ] `tests/test_no_leaks.py` — Phase 3: five literal signatures, `repo` keyword-only on `git_paths`. No pattern/`keep`/`EXEMPT`/`EXEMPT_PREFIXES` change.
- [ ] `tests/test_leak_guard_scope.py` — Phase 3: `untracked_file` gains an optional trailing `root`; ten tests move; the two live mkdirs deleted; **the monkeypatch lambda gains a defaulted parameter**; three tests added; four stay on the real repo.
- [ ] `tests/test_probe_isolation_contract.py` — **new**, Phase 4, severable, AST-based, one self-exemption.
- [ ] `.claude/agents/data-engineer-memory.md` — Phase 5, **append only**.
- [ ] `docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md` — **new**, Phase 5, with a `## Consequences` section stating the cost.
- [ ] `docs/decisions/README.md` — Phase 5, index the ADR.
- [ ] `tests/fixtures/README.md` — Phase 5, one bullet naming the harness class.
- [ ] `requests/bugfix-requests/README.md` — Index row `diagnosed → planned` with this plan, `planned → fixed` at Phase 5.
- [ ] `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md` · `ROOT_CAUSE_ANALYSIS.md` — status blockquotes only; bodies are the historical record.
- [ ] the implementation report — **new**, Phase 5 (path fenced in §3).
- [ ] `tests/test_grain_contracts.py` — **NOT TOUCHED**, listed so nobody touches it (D6).
- [ ] `tests/test_read_only.py` — **NOT TOUCHED**; read only as the template for Phase 4's controls and the reason that guard must be AST-based.
- [ ] `docs/decisions/0020-sanctioned-lookahead-seam.md` — **NOT TOUCHED, deliberately.**

## 8. Conventions (bake these in)

- **The game is read-only (ADR 0001).** This change adds two file-*writing* helpers, so the rule binds sharply: both target a `tempfile` directory or a caller-supplied mirror root and nothing else, and neither ever resolves a path from `.env`. `tests/test_read_only.py`'s write allowlist covers `src/` only, so this one is on the implementer.
- **The fixed-offset ban is the subject, not a bystander.** No rule, allowlist, residual or message changes. The `OFFENDER` body stays exactly as it is — it is the shape the rule exists to catch.
- **Label your epistemics.** The two claims this plan rests on were `unconfirmed` and are now `measured` (2026-08-21): 37 modules / 0 violations, and the seven identical ignore verdicts. Each is re-pinned as an executable control rather than left as prose.
- **No OOTP game data in git (ADR 0006).** Nothing here adds a fixture file. The leak guard *is* that rule's enforcement, which is why Phase 3 may not weaken a single one of its assertions to fit the harness.
- **No machine-specific path, account id or token anywhere** — `tests/test_no_leaks.py` fails the build, and `tests/test_leak_guard_scope.py:37` shows the house pattern for a banned string that must be constructed rather than written.
- **Paths resolve from `.env`; nothing here does** — every root is `REPO_ROOT` or a tempdir. Do not create `datasets/` or `transform/`.
- **Agents commit only through `/commit`**, never `git commit` ad hoc. `/commit` does not run lint, types or tests — that is yours locally and CI's on the PR.
- **Subagents get read-only git**, and this change may not be delegated to the write-capable subagent at all (§1).
- **Anything outward-facing is user-run.** `/commit` pushes the branch; **ask** before opening the PR, and again before merging. Never push `main`, force-push or amend. Every mutation in §4 is applied, observed and **reverted** — none of them ships.

## 9. Code-grounding verification

The panel submitted **104 code references**; two code-grounded adversaries and one meta-audit
returned **47 findings (0 blockers, 13 majors)** against the merged draft, and every one is
either applied above or recorded as disposed. Panel health: planners 3/3, adversaries 2/2,
meta-audit 1/1, no degraded lenses.

**Independently re-verified by the main thread before this plan was written** — five citations
sampled, all five resolving exactly:

| Cited reference | Verified |
|---|---|
| `tests/test_grain_contracts.py` gamedata marks | ✅ exactly `:442`, `:456`, `:482`, `:518`, `:561`, `:586`, `:624` |
| "there is no `conftest.py` anywhere" | ✅ none in the repo |
| `docs/decisions/0020-sanctioned-lookahead-seam.md:92-93` | ✅ *"No per-site exemption registry, ever"* |
| `docs/decisions/0020-sanctioned-lookahead-seam.md:95-102` | ✅ the six named residuals |
| `.claude/agents/data-engineer-memory.md:351-356` | ✅ within the file's 415 lines |

**Corrections applied to the panel's draft, by class:** the `-m "not gamedata"` filter on every
selector naming `tests/test_grain_contracts.py` (CG-01); `.unlink(` dropped from Phase 4's verb
set so the zero-allowlist claim is true (CG-02 / EX-02); the fixture-reach assertion made AST-based
rather than textual (CG-03 / EX-05 / MA-02); the fabricated "eight pinned residuals" replaced with
the two counts that exist (CG-04 / EX-07 / MA-01); the mypy baseline corrected to 81 and given a
per-phase expectation (CG-05 / EX-09); the working-tree gate restated as a property (CG-06); the
cleanup test given the outer-mirror form so it cannot go tautological (CG-07); the doc-links risk
narrowed to its real trigger (CG-08 / EX-04); the fixtures README bullet aimed at the class (CG-09);
absolute temp paths banned from the report (CG-10); a duplicated assertion dropped (CG-11); "37" made
unambiguous (CG-12); a fourth cry-wolf control added for the shape this plan's own helper introduces
(CG-13); Phase 3 reordered so no step depends on a later one (EX-01); `grep` replaced with
`Select-String` or an in-test assertion (EX-03); the literal import line written down (EX-06); the
clobber assert's new near-vacuity documented (EX-08); the mode-B run given an executable form and a
pass/fail definition (EX-10); the `diagnosed → planned` Index move assigned (EX-11); the mirror taught
to exclude survivors (EX-12); the baseline command made PowerShell-safe (EX-13); post-mutation
cleanliness required (EX-14); the branch prerequisite stated (EX-15); the residue globs hardcoded
(EX-16); the repro's post-fix regression value recorded honestly (EX-17); the dropped anti-vacuity
coverage restored as Phase 1 step 10 and mutation 7 (MA-03); bytes-equality added to the fidelity test
(MA-04); the `--exclude-standard` risk restored (MA-05); the non-ASCII property kept among the parity
pins (MA-06); the five leak-side signatures written literally with `repo` keyword-only (MA-07); the
production-enumeration test made non-vacuous (MA-08); Phase 2's gate recorded as disposed rather than
assumed (MA-09); the two residue tests required to name each other (MA-11); the copytree cost given a
threshold and fallback (MA-13); the cry-wolf control relabelled a path construction (MA-14); the
laundered-message precedent cited (MA-15); the `CLAUDE.md` map disposition handed to `/update-docs`
(MA-16); Phase 4 voided if Phase 3 takes its off-ramp (MA-17).

**One panel artifact recorded rather than acted on:** the convergence map claims all three planners
refused a deleting sweep; one in fact proposed an optional one (MA-12). The disposition is unchanged —
the operator declined the sweep — but the map overstates unanimity, and the raw proposals are the
record.

## References

- `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/ROOT_CAUSE_ANALYSIS.md` — the decided upstream artifact
- `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/BUGFIX_REQUEST.md` — the symptom, the measured blast radius, the stage plan
- `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/reviews/plan-proposals.md` — the three planners, unfiltered
- `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/reviews/plan-adversarial.md` — 47 findings, the meta-audit, the convergence map
- [ADR 0020](../../../docs/decisions/0020-sanctioned-lookahead-seam.md) — the rule the poisoned guard enforces, and the foreclosure that refuses the name-aware fix
- `.claude/agents/data-engineer.md` — the build rulebook and the deny set that keeps this on the main thread
