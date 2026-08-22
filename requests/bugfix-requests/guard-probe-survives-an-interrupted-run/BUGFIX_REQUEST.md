> **Status:** diagnosed · created 2026-08-21 · decided · next: plan

# Bug Report — A test plants real modules inside `src/ootp_ai/parser/`, and a survivor reddens the fixed-offset guard on a file nobody wrote

## Symptom

`uv run pytest tests/test_no_fixed_offsets.py` fails, naming a source file that is not in
git and that nobody wrote:

```text
AssertionError: fixed-offset reads found — these pass on day-0 data and silently return
the wrong field on any record with a different shape:
  src/ootp_ai/parser/_guard_scope_probe.py:3: data[…] — a record-relative buffer
  subscript outside the sanctioned seam; read through parser/lookahead.py or walk with
  a Cursor
```

The reader goes looking for `_guard_scope_probe.py`, finds it in the package, and cannot
find it in the history. The message is a correct description of the planted file's
contents and a completely misleading description of the repo's state — it presents as a
fixed-offset violation in the parser, which is the single defect class this project treats
as most expensive.

**It has been observed five times and filed zero times.** It appears in the Phase 8a,
Phase 9 (twice), Phase 10 and Phase 11 acceptance artifacts; Phase 10's implementation
report records it as follow-up 3 and Phase 11's panel hit it twice more, costing a reviewer
a false alarm each time.

## Reproduction attempt

**Deterministic.** The natural occurrence is intermittent — it needs a run to be
interrupted — but the resulting state is trivially reproducible, which is what diagnosis
needs:

1. Write a file at `src/ootp_ai/parser/_guard_scope_probe.py` containing the body the
   test itself plants (`tests/test_fixed_offset_guard_scope.py:65-68`):

   ```python
   def read_team_id(data: bytes, record_start: int) -> int:
       return int.from_bytes(data[record_start + 58 : record_start + 62], "little")
   ```

2. `uv run pytest tests/test_no_fixed_offsets.py` → **red**, with the message above.
3. `uv run ruff format --check .` → **red**, `1 file would be reformatted`.
4. `git status --porcelain --untracked-files=all` → `?? src/ootp_ai/parser/_guard_scope_probe.py`.
5. Delete the file; everything is green again.

**How the state arises naturally.** `tests/test_fixed_offset_guard_scope.py:81-98` defines
a `parser_probe` context manager that writes a **real** `.py` module into the **live**
`src/ootp_ai/parser/` directory and removes it in a `finally`. Four modules are planted
across that file's tests, all matching `_guard_scope*_probe.py`. Anything that prevents the
`finally` from completing — an agent tool timeout, a `Ctrl-C`, or on Windows an AV scanner
holding a handle on a freshly-written `.py` — leaves a real offending module inside the
package. `tests/test_no_fixed_offsets.py:97` sets `SCAN_ROOT = REPO_ROOT / "src" /
"ootp_ai"`, so the guard walks the same live directory the probe was planted in.

## Expected vs Actual

- **Expected:** a test's fixture leaves no trace in the source tree, however it exits. The
  fixed-offset guard reports violations that exist in tracked code, so a red run means
  somebody committed a fixed-offset read.
- **Actual:** an interrupted run leaves a real module in `src/ootp_ai/parser/`, and the next
  run reports a fixed-offset violation in a file that is in neither git nor anyone's editor.

## Severity

**Above cosmetic, below data corruption.** Nothing is landed wrongly, no money is spent,
and no number reaches a decision — the parser is untouched and the warehouse never sees it.

What it costs is **trust in the guard**, and that is not a small currency here. This is the
guard the implementation plan names as one that *must be seen to fail*, and the same plan
warns that **"a flapping guard gets deleted rather than fixed."** Five sightings without a
filed request is the first half of that sentence happening.

Two CI gates go red on a phantom file, and the measurement is worth recording because it is
narrower than the Phase 11 panel reported (it claimed ruff, mypy, pytest and the leak guard
were all poisoned — measured 2026-08-21, with the offender body planted):

| Gate | Result | Note |
|---|---|---|
| `pytest tests/test_no_fixed_offsets.py` | **red** | the headline symptom |
| `ruff format --check .` | **red** | `1 file would be reformatted` |
| `ruff check .` | passes | |
| `mypy` | passes | but silently widens its source set, 80 → **81** files |
| `pytest tests/test_no_leaks.py` | passes | it *enumerates* the file; this body carries no machine path |

The blast radius depends on the planted body, and the four probe bodies differ — so a
different survivor may redden a different set. Only the fixed-offset guard is red for all
of them, because being flagged by it is what every offender body is written to do.

## Triage

- **Verdict:** `needs-full-track`
- **Obviousness hint (optional, non-binding):** the *cause* is not in doubt — it is
  `parser_probe`'s reliance on a `finally` for cleanup in a directory a sibling test scans.
  What is in doubt is the **fix**, and that is a genuine design question rather than a
  one-liner. See Open Questions.

## Affected Area & Pointers

**Subsystem:** `tests/` only. No parser, warehouse or report code is implicated — the
planted file is a fixture artifact, not a defect in `src/`.

| # | File | Why |
|---|---|---|
| 1 | `tests/test_fixed_offset_guard_scope.py` `:81-98` | `parser_probe` — the fixture that plants into the live tree and cleans up in a `finally`. Its docstring argues the live tree is **necessary**, and that argument is the crux |
| 2 | `tests/test_no_fixed_offsets.py` `:97` | `SCAN_ROOT` — the guard walks the same directory. `parser_module_violations()` takes no root parameter |
| 3 | [ADR 0020](../../../docs/decisions/0020-sanctioned-lookahead-seam.md) | The decision the guard enforces. Any fix that narrows what the guard reads is trading against this |

Also relevant: `requests/feature-requests/first-sight/reviews/phase-11-acceptance-panel.md`
(CF-19, the most recent sighting, with the live failure text) and
`requests/feature-requests/first-sight/IMPLEMENTATION_REPORT.md` (follow-up 3, the Phase 10
record).

## Reporter's cause-hunch (non-binding)

The fixture is correct about *what* it needs and wrong about *how durable* its cleanup is.
`parser_probe`'s docstring says:

> A `tmp_path` fixture cannot serve: the scan enumerates the package on disk, so the probe
> has to exist inside it to be a fair test of what the scan actually reads.

That is a real argument — the test exists to prove the scan finds an offender *in the
place it actually looks*, and a probe in `tmp_path` proves something weaker. The defect is
that a `try/finally` is treated as a durable guarantee when the failure mode is precisely
the process not surviving to run it.

Two candidate shapes, and they trade differently:

1. **Sweep before the suite.** A session-scoped autouse fixture that unlinks any surviving
   `_guard_scope*_probe.py` and logs what it removed — then keep the existing
   `assert not path.exists()` so a survivor is still surfaced rather than silently tidied.
   Preserves the end-to-end property completely; leaves the window open *within* a run.
2. **Parameterise the scan root.** Expose a `scan_tree(root)` seam so the probe is planted
   and scanned in `tmp_path`. Closes the window entirely, and weakens the one test that
   proves the guard reads the real package.

Non-binding. Diagnosis may find a third, and may find that (1) and (2) are not exclusive.

## Open Questions for Diagnosis

1. **Is planting in the live tree load-bearing, or is the docstring's argument stronger
   than it needs to be?** If `parser_module_violations()` gained a root parameter, would
   `test_the_scan_reports_a_planted_offender_in_the_real_tree` still prove what its name
   claims — or would it become a test that the scan reads *a* directory rather than *the*
   directory?
2. **Is a survivor detectable without being confusable?** The failure message is accurate
   and misleading at once. Should the guard recognise a `_guard_scope*_probe.py` name and
   fail with *"a test fixture survived an interrupted run; delete it"* instead? That is a
   guard knowing about its own test, which is usually a smell.
3. **Why has this never been caught by the `assert not path.exists()` at `:93`?** That
   assertion refuses to clobber an existing probe — so a survivor should make the *next*
   run of the probe test fail loudly rather than the guard fail confusingly. Does it, and
   is the guard simply collected first?
4. **Does the same hazard exist elsewhere?** Anything else that writes into a scanned tree
   and cleans up in a `finally` has the same shape. A sweep is worth aiming at the class if
   there is one.

## Stage plan

**Full pipeline.** Two of the three hard triggers fire, and either alone is enough:

1. **Open Questions is non-empty** — four of them, and the first is a real design question
   the fix turns on rather than a detail.
2. **The reproduction is reliable** — a deterministic plant-and-run makes it red on demand,
   and the natural intermittency does not block the red-to-green evidence the track's
   definition of done requires. **This trigger clears.**
3. **It touches something expensive to reverse** — the fix modifies the enforcement of the
   fixed-offset ban, which `CLAUDE.md` calls *"the rulebook's"* and which
   [ADR 0020](../../../docs/decisions/0020-sanctioned-lookahead-seam.md) settles. Candidate
   fix (2) narrows what the guard reads. Weakening the project's most load-bearing
   structural guard in order to stop a fixture flake is exactly the trade that needs a
   panel rather than a judgement call.

No skip is available and none is proposed.
