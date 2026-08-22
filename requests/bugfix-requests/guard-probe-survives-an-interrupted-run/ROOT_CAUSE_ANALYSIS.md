> **Status:** diagnosed · created 2026-08-21 · decided · next: plan

# Root Cause Analysis — The probe is planted in the tree the guard scans

## Verdict

**`confirmed-bug`** — the cause is measured and is not in doubt: `parser_probe` writes a real
module into the same directory `test_no_fixed_offsets.py` enumerates, and the two are joined by
a path with no seam between them. The **fix** is a genuine design question, so this takes the
full track: `/create-implementation-plan` next.

**One correction to the intake matters more than the confirmation.** The report frames this as
an interrupted run leaving a survivor. That path is real and reproduced below — but it is the
*rarer* of two paths to the identical symptom, and the more common one leaves nothing behind
to find:

| | How it arises | What is left afterwards |
|---|---|---|
| **A — survivor** | a run dies between the write and the `finally` | a real `.py` in the package |
| **B — concurrent reader** | a second pytest session scans the tree while a healthy run has a probe planted | **nothing** |

Every recorded sighting whose provenance is documented is **B**. `phase-10-acceptance-panel.md`
`:84-87` records it directly: *"the lenses ran concurrently against one shared working tree, so
at least two reported reds were cross-contamination — including a `test_no_fixed_offsets`
failure caused by a sibling test writing a probe `.py` into the live package tree."* That is why
the sightings read as unexplained: the reader who went red never had the evidence, because the
planting session cleaned up correctly.

**This is load-bearing for the fix.** A sweep that removes survivors — candidate (1) in the
report — cannot touch mode B, and does not satisfy the report's own Expected either (*"a test's
fixture leaves no trace in the source tree, however it exits"*): it shortens a survivor's life
rather than preventing the trace. Any fix that leaves the plant inside the scanned tree leaves
mode B open.

## Reproduction (red)

`tests/test_guard_probe_isolation.py` — two tests, offline, deterministic, **RED on today's
code**. Run:

```
uv run pytest tests/test_guard_probe_isolation.py
```

```
FAILED tests/test_guard_probe_isolation.py::test_a_run_that_dies_inside_the_probe_leaves_no_module_behind
  AssertionError: an interrupted run left a real module inside the scanned package:
  ['src/ootp_ai/parser/_guard_scope_abort_probe.py']

FAILED tests/test_guard_probe_isolation.py::test_the_real_scan_does_not_report_a_probe_a_sibling_test_has_planted
  AssertionError: the fixture's probe is visible to the real tree-is-clean scan, so any reader
  of the package while it is planted goes red on a file no author wrote:
  ['src/ootp_ai/parser/_guard_scope_isolation_probe.py:3: data[…] — a record-relative buffer
  subscript outside the sanctioned seam; …']
```

One test per mode. The first spawns a child that enters `parser_probe` and calls `os._exit(97)`
— no `finally`, no `atexit`, no signal handler survives it — and then asserts the package holds
no probe module. The second scans the live tree while a probe is planted, which is exactly what
a concurrent reader does, without needing a second process to race.

**Both drive the real fixture rather than planting a file themselves**, and that is deliberate:
a test that plants its own module could only be made green by teaching the guard to ignore the
file, which is a fix this diagnosis does not get to choose. Driving `parser_probe` means *any*
fix that stops it poisoning the live tree turns both green.

Both clean up after themselves, and the module is `-m "not gamedata"` — no save, no MySQL, so it
runs in CI. **Not yet committed** at the time of writing; it lands with this RCA.

**Measured by hand as well, 2026-08-21**, with a survivor planted, confirming the report's own
blast-radius table:

| Gate | Result |
|---|---|
| `pytest tests/test_no_fixed_offsets.py` | **red** — names `src/ootp_ai/parser/_guard_scope_abort_probe.py:3` |
| `ruff format --check .` | **red** — `1 file would be reformatted` |
| `ruff check .` | passes |
| `pytest tests/test_fixed_offset_guard_scope.py` | passes — see Q3 below |

## Evidence (the cause)

**The writer and the reader share one path, and the reader cannot be pointed anywhere else.**

- `tests/test_fixed_offset_guard_scope.py:60` — `PARSER_DIR = REPO_ROOT / "src" / "ootp_ai" /
  "parser"`, and `:92-98` writes a real module there, yielding, then unlinking in a `finally`.
- `tests/test_no_fixed_offsets.py:97` — `SCAN_ROOT = REPO_ROOT / "src" / "ootp_ai"`;
  `:345-354` `parser_modules()` is `sorted(SCAN_ROOT.rglob("*.py"))`; `:357-363`
  `parser_module_violations()` **takes no root parameter**. There is no seam. A probe placed
  where the scan will fairly find it is therefore placed where *every other reader of the tree*
  will also find it, and the fixture has no way to ask for a different tree.
- `tests/test_no_fixed_offsets.py:569-575` — `test_no_parser_module_seeks_to_a_fixed_offset()`
  asserts that scan is empty. It is the test that goes red, and **its verdict on the planted
  file is correct**: the probe body at `test_fixed_offset_guard_scope.py:65-68` really is a
  record-relative buffer subscript. That is the trap — the message is accurate about the file
  and completely misleading about the repo.

**The `finally` is not the cause; it is the mitigation that mode A defeats.** The cause is
mutating shared state that a sibling reads. Mode A is that mutation outliving the process; mode
B is a second reader observing it mid-flight. Both are measured above.

**Why it has never reddened CI, and never will as written.** `pyproject.toml:98-108` declares
`testpaths`, `addopts = "-q --strict-markers --strict-config"` and one marker — **no xdist, no
parallel plugin** — so within a single session the plant and the scan are strictly sequential.
`phase-7-acceptance-panel.md:63` records the same conclusion for the sibling hazard: *"the
meta-audit confirmed CI is single-process … so it is unreachable there."* This is a
multi-session hazard on a developer's or an acceptance panel's machine, which is precisely why
it has cost reviewer time five times and never once cost a build.

**Open question 3, answered by measurement — why `assert not path.exists()` at `:93` never
caught it.** Two reasons, both measured today:

1. **It is keyed on the exact name.** With a survivor named `_guard_scope_abort_probe.py`
   present, `tests/test_fixed_offset_guard_scope.py` is **fully green (32 passed)** while
   `tests/test_no_fixed_offsets.py` is red. Rename that same survivor to
   `_guard_scope_probe.py` and `:93` fires correctly:
   `AssertionError: _guard_scope_probe.py already exists; refusing to clobber it`. A real
   survivor is always one of the four names the module plants, so the assertion does fire — but
   only in a run that **collects that module**, and the recorded sightings ran the guard alone
   or read the summary line, where the guard's own failure is the louder and more alarming one.
2. **It is structurally blind to mode B.** In the concurrent case the planting session is
   healthy and `:93` is satisfied; the red appears in a different process entirely.

**Open question 4, answered — the hazard class has a second, worse site.**
`tests/test_leak_guard_scope.py:40-53` is the same shape: `untracked_file` writes a real file
into the live repo and cleans up in a `finally`, with the same name-keyed clobber assert at
`:48`. It plants at the repo root (`:73`), several directories deep under
`requests/bugfix-requests/` (`:119-120`) and under `var/tmp` (`:89-90`) — and its probe bodies
carry a **deliberately banned machine-path string** built at `:37`, so a survivor there reddens
`tests/test_no_leaks.py`, the repo's only leak protection. `phase-7-acceptance-panel.md:63`
already recorded it racing `test_doc_links` (CF-14) and carried it forward unfixed. A fix aimed
at `parser_probe` alone leaves this open, and the report should say so rather than read as
"closed".

**Not implicated:** `src/` is untouched — no parser, warehouse or report code is involved — and
[ADR 0020](../../../docs/decisions/0020-sanctioned-lookahead-seam.md)'s rule is not at issue.
What is at issue is where the test that proves the rule does its work.

## Fix posture (tiered)

- **Minimal — un-share the tree.** Give the scan a root parameter
  (`parser_modules(root=SCAN_ROOT)` / `parser_module_violations(root=…)`, defaulting to the live
  package) and plant the probe into a temporary tree instead of `src/ootp_ai/parser/`. That
  flips both repro tests, closes A and B together, and is the only shape measured here that
  closes B at all. **It is also the trade the plan stage must actually decide**, because
  `test_fixed_offset_guard_scope.py:85-86` argues the live tree is necessary: *"the scan
  enumerates the package on disk, so the probe has to exist inside it to be a fair test of what
  the scan actually reads."* That argument is strong, and the cheap version of this fix weakens
  the one test proving the guard reads the real package. A middle path exists and is worth
  costing: copy the real package into the temp tree and plant beside it, so the probe still sits
  among real modules on disk while sharing nothing — plus a compensating assertion that the
  production scan root **is** the live package. `test_the_module_set_has_a_floor` (`:137-150`)
  must keep running against the real one either way, or the fix buys a vacuous guard.
- **Root — the class, not the instance.** Apply the same treatment to `untracked_file` in
  `tests/test_leak_guard_scope.py`, whose survivor is worse (a banned string at the repo root,
  and the guard it poisons is the only leak protection there is). One shared convention for
  "probe a guard without mutating what the guard reads" is what stops a third site being
  invented; two independent fixes are the outcome to avoid.
- **Hardening — gated, not assumed.** (a) A session-scoped sweep that removes **and reports**
  any surviving `_guard_scope*_probe.py`. It cannot fix either mode on its own and must not be
  sold as the fix — its only real value is cleaning survivors left by *older* revisions, which
  no design change can do retroactively. (b) Teaching the guard to recognise a probe name and
  fail with *"a test fixture survived an interrupted run; delete it"* (the report's Q2). It
  makes the message honest but is a guard knowing about its own test, and it is the one option
  that trades directly against the fixed-offset ban's enforcement — the reason this request's
  stage plan called for a panel rather than a judgement call.

**What this diagnosis does not settle**, and hands to the plan: whether the fidelity argument at
`:85-86` survives a parameterised root or needs the copy-the-package variant; whether the
name-aware guard message is acceptable at all; and whether the leak-guard site is fixed in the
same change or filed as its own follow-up. All three are design calls with real trade-offs, and
none is blocked by missing evidence.
