> **Status:** intake · created 2026-08-24 · open · next: scope

# Feature Request — The remaining whole-tree guards cannot be seen to fail on disk

## Problem / Motivation

Two guards in this repo enumerate `src/ootp_ai/` from disk and report what they find, and
**neither can be proved to actually report a real file**:

- `tests/test_grain_contracts.py:75` — `SCAN_ROOT = REPO_ROOT / "src" / "ootp_ai"`, walked at
  `:364-367`, enforcing that no module in `src/` joins on the `historical_id`.
- `tests/test_read_only.py:292` — `SRC = …/src/ootp_ai`, walked by `_source_files()` at `:345`,
  enforcing the write allowlist and the destructive-call ban that
  [ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md) rests on.

Both are pinned against **strings**: `test_the_scanner_flags_a_synthetic_join` (`:354`) and
`test_the_write_guards_still_catch_a_real_offender` (`:389`) hand source text to a scanner and
check the verdict. That proves the *rule* works. It proves nothing about whether the
**enumeration** works — whether the walk opens the files it claims to, whether a filter
silently swallows the package, whether the scan is reading anything at all.

This repo has been bitten by exactly that gap three times, and the record is in
`tests/test_fixed_offset_guard_scope.py:9-14`: a leak-guard mutant that scanned zero files left
all 18 of its tests green, and a batching guard exited 1 on a clean checkout for its whole life.
Both were invisible until someone planted something real on disk. The fixed-offset guard and the
leak guard now have that disk-level proof. These two do not, and the asymmetry is not deliberate
— it is where the last fix stopped.

**What makes this newly worth filing rather than a standing nice-to-have:** the fix that just
landed ([ADR 0022](../../../docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md)) makes
the obvious way to get that proof **forbidden**. `tests/test_probe_isolation_contract.py` now
fails any test that writes into the live tree, so an author who wants to prove either guard on
disk has no legal move until the seam exists. The door was closed without the replacement being
built.

It was also filed for a second reason. That bugfix's own report observes that *"observed five
times, filed zero times"* is the failure the request documents — so noting this in a report and
walking away would repeat it.

## Desired Outcome

Both guards can be **seen to fail against a real file on disk**, the same standard
`tests/test_fixed_offset_guard_scope.py` and `tests/test_leak_guard_scope.py` are now held to,
without any test writing into the tree this repo actually ships.

The observable signal: a mutation that makes either scan enumerate nothing kills a test that is
green today. Concretely — set `_source_files()` to return `[]`, and something goes red.

Secondary, and cheaper to judge: the two modules stop being the odd ones out. Four guards walk
`src/ootp_ai/`; two now take a tree root and two do not, which is the kind of half-applied
convention the next author has to read all four to understand.

## Rough Ideas (non-binding)

The shape the last fix used, offered only as a starting point — scoping should confirm it fits
before adopting it:

- Give each scan a defaulted root parameter, production callers passing nothing, pinned from the
  tests' own source so nobody quietly points production at a copy.
- Reuse `mirrored_package()` from `tests/fixtures/guard_trees.py` rather than growing a third
  tree builder.
- Keep every coverage floor and cry-wolf control observing **production**, per that fix's P6.

**A trap worth carrying forward, and it is the reason this may not be a copy-paste job.** For the
fixed-offset guard the root had to be a **repo** root, not a package root, because its exemption
keys are repo-relative posix strings — relativising against the package root silently un-exempted
the sanctioned seam. `tests/test_read_only.py`'s `WRITERS` allowlist is keyed on paths relative to
`SRC` (package-relative, changed for that reason during first-sight Phase 10), so the correct
answer there may be the **opposite** of the last one. Assuming symmetry is the way to get this
wrong.

## Scope Signals

- **In:** a tree-root seam for `tests/test_grain_contracts.py`'s join scan and
  `tests/test_read_only.py`'s write/destructive scans; disk-level seen-to-fail coverage for
  both; the compensating assertions that keep production reading the live package.
- **Explicitly out:** any change to what either guard *considers* a violation — the
  `historical_id` join rule, the `WRITERS` allowlist, `DESTRUCTIVE_CALLS`, `CREATIVE_CALLS`, the
  open-mode rule. This is about what the scan can be proved to read, not what it judges. Also
  out: any change under `src/`, and any change to the fixed-offset or leak guards, which are
  done.
- **Not now / later:** a shared base for all four whole-tree scanners. Three of them
  (`test_no_fixed_offsets`, `test_grain_contracts`, `test_read_only`) walk the same directory
  with three separate globs, and unifying that is a bigger and separate argument than adding a
  parameter to two of them.

## Affected Area & Pointers

`tests/` only. No parser, warehouse, contract, catalog or report code; no save byte; no MySQL.

A cold scoping agent should read, in this order:

1. `tests/test_read_only.py` — `SRC` `:292`, `WRITERS` `:303-317` (package-relative keys, and
   the comment saying why), `_source_files()` `:344-345`, `_writes_in` `:348-358`, and the
   string-level pin at `:389-402`.
2. `tests/test_grain_contracts.py` — `SCAN_ROOT` `:75`, `scan_source` `:326`, the walk at
   `:364-367`, and the seven `@pytest.mark.gamedata` tests that mean a bare module selector
   lands a real snapshot in MySQL.
3. `tests/fixtures/guard_trees.py` — `mirrored_package()`, `assert_owned`, `OPEN_MIRRORS`, and
   the module docstring stating the convention.
4. `tests/test_probe_isolation_contract.py` — the rule that now forbids the old approach, and
   its own honest list of what it does not cover.
5. `requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/IMPLEMENTATION_REPORT.md`
   — §3 deviations and §4's two concurrency harnesses. The second harness is the one that
   matters: a measurement that cannot observe the property it is cited for is worse than none.

## Constraints / Non-negotiables

- **No `src/` change.** Neither guard's subject moves.
- **No rule, allowlist or assertion message weakened** to fit a harness. The last fix pinned this
  with a mutation that plants a real survivor and checks the reported message is byte-identical;
  the same standard applies.
- **Every coverage floor keeps observing production.** A floor measured on a mirror is a floor on
  the mirror.
- **`tests/` is in the `data-engineer` subagent's deny set**
  (`.claude/agents/data-engineer.md`, asserted by `tests/test_agent_contract.py`), so this is
  main-thread work and cannot be delegated to the write-capable builder.
- mypy runs strict over `tests/`, and ruff's `PTH` rules apply there.

## Open Questions for Scoping

1. **Is this worth building at all?** Neither guard has ever shipped broken, both have
   string-level seen-to-fail, and the enumeration each uses is four lines of `rglob`. The honest
   case against is that the three historical failures were all *rule* or *scope* mutations that
   string-level pins would not have caught either — so the argument rests on the enumeration
   being the untested half, not on a near-miss. Scoping should be willing to close this as
   "documented asymmetry, deliberately left".
2. **Repo root or package root, per module?** See the trap under Rough Ideas. The two modules may
   genuinely need different answers, and getting it wrong silently un-exempts an allowlist rather
   than failing loudly.
3. **Does `test_grain_contracts.py`'s `gamedata` half complicate the seam?** Its scan is offline
   but the module is not, and the selector must carry `-m "not gamedata"` or a bare run lands a
   real snapshot in MySQL.
4. **Is `mirrored_package()` the right tree for a write-guard test**, given that guard's subject
   is *writing*? A mirror that a test then writes into is a different exercise from a mirror it
   only reads, and `assert_owned` exists precisely to keep those apart.
5. **Does the third scanner want the same treatment?** `tests/test_no_leaks.py` already has a
   repo parameter; `test_no_fixed_offsets.py` has a tree root. If these two land differently
   again, there are four conventions across four files.

## Stage plan

**Full pipeline.** Trigger 1 fires: Open Questions came out non-empty, and the first of them is
whether to build this at all — which is exactly the call `/scope-feature` exists to make, and not
one intake should pre-empt. Trigger 2 is clear (*Explicitly out* is filled and sharp). Trigger 3
is arguable rather than clear: the work touches no ADR, grain or field map, but question 2 is a
silent-failure mode with a measured precedent, which is the kind of thing a panel is cheaper than
a rediscovery.
