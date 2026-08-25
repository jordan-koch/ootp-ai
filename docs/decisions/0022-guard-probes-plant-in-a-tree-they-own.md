# 0022 — A guard's scope test plants only in a tree it owns

**Status:** Accepted
**Date:** 2026-08-24

## Context

This repo defends itself with whole-tree guards: [ADR 0020](0020-sanctioned-lookahead-seam.md)'s
fixed-offset ban scans `src/ootp_ai/`, and the leak guard scans everything git knows about. Both
have been proved worthless once already — a leak-guard mutant that scanned zero files left all 18
of its tests green, and a batching guard exited 1 on a clean checkout for its whole life. So each
now carries a **scope test** that plants a real offender on disk and watches the guard report it.

Both scope tests planted into the live working tree, and argued for it in as many words: *"a
`tmp_path` fixture cannot serve: the scan enumerates the package on disk, so the probe has to
exist inside it to be a fair test of what the scan actually reads."* The argument is good. The
implementation was a defect, and it presented in two ways:

- **A run that dies before its `finally`** — a tool timeout, `Ctrl-C`, a killed process — leaves a
  real file in the repository. The next run reports a violation in a file that is in neither git
  nor anyone's editor.
- **Any concurrent reader scanning that tree while a healthy run has a probe planted** sees the
  same thing, with **nothing left behind afterwards to explain it**.

The second is the one that actually happened. Acceptance panels run their lenses concurrently
against one working tree, and every sighting with a documented provenance was this: the planting
session cleaned up correctly, so the reader who went red never had the evidence. It was
**observed five times across the Phase 8a/9/10/11 artifacts and filed zero times** — the worst
ratio a defect can have, because a red nobody can reproduce gets attributed to flakiness, and a
flapping guard gets deleted rather than fixed.

CI never caught it and never will: `pyproject.toml` declares no xdist and no parallel plugin, so
within one session the plant and the scan are strictly sequential. This is a hazard on a
developer's machine and on a review panel's, which is exactly where the cost landed.

The tempting fix — teach the guard to recognise `_guard_scope*_probe.py` and report *"a fixture
survived an interrupted run"* — is a per-site exemption registry inside the enforcement of the
fixed-offset ban, which [ADR 0020](0020-sanctioned-lookahead-seam.md) forecloses outright. A
sweep that deletes survivors is worse than it looks: it cannot touch the concurrent-reader mode
at all, because that mode leaves nothing to sweep.

## Decision

**A guard's scope test may plant only in a tree it owns; a test that reads the live tree plants
nothing.**

Three parts, and the third is what stops the first two being quietly undone:

1. **The guards take a tree root**, defaulting to this repository, and every production caller
   passes nothing. For the fixed-offset scan the parameter is a **repo** root rather than a
   package root — its exemptions are keyed on repo-relative posix strings, so relativising
   against a package root would silently un-exempt the sanctioned seam and make a mirror report
   violations production does not. For the leak guard the root is a real `git init`-ed
   repository, because that guard's scope is a git index rather than a directory walk.
2. **Probes plant into a byte-faithful mirror** built under the OS temp root by
   `tests/fixtures/guard_trees.py` — the package copied file-for-file for one guard, this repo's
   `.gitignore` copied verbatim for the other. Fidelity is the point: the scan still walks a real
   tree of real modules, so the original argument is answered rather than abandoned.
3. **Compensating assertions buy back what a copy cannot prove** — that production reads the
   original. The production scan root is pinned to the live package; the mirror is asserted equal
   to it in module set *and* bytes; and the tree-is-clean tests are pinned, from their own
   source, to call the guards with no arguments. Every coverage floor and junk-directory test
   keeps observing production, each with a comment saying why.

`tests/test_probe_isolation_contract.py` enforces the convention across `tests/**/*.py`: a
creative write — `write_text`, `write_bytes`, `touch`, `mkdir`, `os.makedirs` — whose target
derives from the live checkout is a violation. AST-based, because this repo's own write guard
holds those verbs as string literals and a text scan would cry wolf on it. It lands with an
**empty allowlist**, which is only true because every site it covers was fixed first.

## Consequences

**What this buys.** Both failure modes close together, and the concurrent one — the only one that
ever actually bit — closes for the first time. Measured on one machine, 2026-08-24, with the
harness named because the harness is the part that is easy to get wrong:

| Harness | Before | After |
|---|---|---|
| A reader loop (`test_no_fixed_offsets.py`) against a planter loop (`test_fixed_offset_guard_scope.py`), 12 rounds | 2 of 12 red | 0 of 12 |
| 3 concurrent sessions of `test_fixed_offset_guard_scope.py` x 4 rounds | 10 of 12 red | 0 of 12 |
| 3 concurrent sessions of `test_leak_guard_scope.py` x 4 rounds | not measured | 0 of 12 |
| 2 concurrent full offline suites x 3 rounds | not measured | 0 of 6 |

**The second row is the one that matters, and it is there because the first row was not enough.**
Two loops over *different* modules can never put two sessions inside the same module at once, so
that harness is structurally incapable of observing a collision between two copies of the same
test — and an assertion added by this very change turned out to be red 10 of 12 rounds under the
harness that can. Solo runs were green throughout, and CI is single-session, so nothing
mechanical would ever have reported it. A measurement is only as good as the shape it can fail
in; the implementation report records both forms so the next reader does not repeat the blind one.

A run killed mid-suite now leaves the repository clean. The convention is enforced rather than
remembered, so a third instance fails a test instead of costing a sixth reviewer an afternoon.
And the guards themselves are untouched: no rule, no allowlist, no residual and no message
changed. That last point was checked by a **hand-run mutation** on 2026-08-24 — a real survivor
planted in the live package, the reported violation string compared against the pre-change one
and found identical — not by a standing test. The mutation was reverted; nothing of it ships.

**What it costs, and the cost is real.** The end-to-end tests now read a **copy** of the package
rather than the package. That is a genuine reduction in fidelity, and it is bought back by
assertion rather than by construction — three compensating tests that a future refactor could
delete without any other test noticing. **Two helper trees now exist that must be kept faithful**:
a `copytree` that dropped a subpackage, or a `.gitignore` copy that drifted, would move a guard's
scope while every test still passed. Both are pinned (bytes equality for one, seven pairwise
ignore verdicts for the other), but a pin is a thing that can rot. There is a runtime cost too —
about 0.3 s per mirror, roughly 2.5 s across the fixed-offset scope module — and a `git init`
subprocess in the leak-guard tests, which is a new dependency on git being present and sanely
configured wherever the suite runs.

**And the shared tree did not disappear; it moved.** Mirrors live under the OS temp root, which
is machine-global, so anything that *searches* that root rather than being handed its own tree
reintroduces this defect one directory up — which is exactly what one assertion in the first cut
of this change did. Mirrors therefore carry the creating process's pid in their prefix, a fixture
hands its tree to the test rather than being found by a glob, and the one place that cannot use
either — a child process killed by `os._exit`, where `TemporaryDirectory`'s finalizer never runs —
is pointed at a directory pytest reaps. Measured: that child stranded a 646 KB tree per suite run
before, and zero after.

**What it forecloses.** No guard in this repo may learn the filenames of its own test fixtures.
That was the cheap fix here and it stays refused, at both sites; ADR 0020 already forbids a
per-site exemption registry, and this decision is what makes one unnecessary rather than merely
banned. Deleting sweeps are also foreclosed as *fixes* — a sweep may report, never tidy, because
silently removing a survivor destroys the evidence the next reader needs.

**What it does not claim.** Nothing here is retroactive. A checkout that ran the pre-fix code and
died inside a probe still has a real file in it, and no design change reaches backwards.
`tests/test_guard_probe_isolation.py` reports such a survivor by name and tells the reader to
delete it — it does not delete it, and probe filenames are deliberately not gitignored, because
an untracked file in `git status` is the signal that identified this defect in the first place.
The contract guard's taint analysis follows names, not values: a live path routed through a
function call before being written to is invisible to it, the same dataflow cost
`tests/test_no_fixed_offsets.py` declined for its own hoisted-read residual. The case that
matters most — a caller handing a fixture the live repo root, which restores the original defect
exactly — is covered from the other side instead, by a runtime refusal on every plant.

Nor is the guard's verb set the whole of "creating a file". It covers `write_text`,
`write_bytes`, `touch`, `mkdir`, `os.mkdir`, `os.makedirs`, write-mode `open` in both spellings,
and the `shutil` copy family keyed on its destination; it does not see `from os import makedirs`
followed by a bare call, or a write to a bare relative-path literal. That list is maintained in
the guard's own module docstring, which is where a reader will be standing when it matters.
