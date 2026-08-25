# Acceptance panel — guard-probe-survives-an-interrupted-run

Run 2026-08-24 against the completed implementation of all six phases, before any Phase 5
bookkeeping existed. Roster auto-scaled to the touched areas (`tests`, `docs`).

## Panel health

| | |
|---|---|
| Reviewers | **5 / 5 ok** — acceptance, fidelity, correctness, edgecases, parser |
| Verify agents | **5 / 5 ok** (4 location-grouped batches + the independent ledger verifier) |
| Findings unverified | **0** |
| Meta-audit | **1 / 1** |
| Degraded lenses | **none** |
| Blocker/major findings, raw → deduped | 21 → 19 |
| Criteria | 41 total · 26 met · 12 unmet · 3 unverifiable *(at panel time — all 41 met after the fix round; see the report)* |
| Verdict | **fix** (not `go`, not `no-go`) |

Nothing was refuted: every blocker and major that reached independent verification came back
`confirmed`.

## Verdict rationale, as returned

> Not `go`: one confirmed blocker remains, reproduced independently (10 of 12 concurrent rounds
> red), and it recreates the very defect class this request exists to retire. Four Phase 5
> acceptance criteria are outright unmet. Not `no-go`: the implementation is faithful, not
> off-plan — Phases 0–4 land the prescribed shapes exactly. The remaining work is bounded.

## Confirmed findings, and what was done

| ID | Sev | Finding | Resolution |
|---|---|---|---|
| S1 | **blocker** | The anti-vacuity test globbed the machine-global OS temp root and asserted `== 1` — this bug relocated from `src/ootp_ai/parser/` to the temp root. Measured red 10/12 across three concurrent sessions, green solo, invisible to single-session CI | **Fixed.** Replaced with an in-process `OPEN_MIRRORS` registry: the fixture hands the test its tree instead of the test searching for it. Re-measured 0/12 |
| S2 | major | Phase 5's evidence half skipped — no report, Index row still `planned`, statuses unadvanced | **Fixed.** `IMPLEMENTATION_REPORT.md` written; Index row and all three status blockquotes advanced to `fixed` |
| S3 | major | ADR 0022 claimed, present tense, a standing "mutation test" that does not exist | **Fixed.** Reworded to a dated hand-run mutation, citing the report |
| S4 | major | The contract guard missed write-mode `open`, the `shutil` copy family and `os.mkdir` (an ordering short-circuit), and its limits section did not say so | **Fixed.** Verb set widened, keyed on the destination argument for `shutil`; binding forms extended to `for`/`with`/walrus; limits section rewritten |
| S5 | major | The abort child stranded a ~646 KB mirror per suite run, unbounded — 107 trees measured | **Fixed.** Mirrors honour a parent-directory environment variable; the repro points it at pytest's `tmp_path`. Measured delta 0 |
| S6 | major | Nothing stopped a caller handing either fixture the live repo root — the cheapest path back into the bug, invisible to every guard added here | **Fixed.** `assert_owned` refuses the repo root and anything under it, at both sites, at every plant |
| S7 | major | A `measured` concurrency claim in an accepted ADR and in agent memory, produced by a harness structurally incapable of observing the property | **Fixed.** Re-measured in a harness that can collide; ADR and memory restated with the harness named beside each number |
| S8 | major | `CLAUDE.md` and `README.md` still said twenty-one ADRs | **Fixed.** Both now twenty-two / twenty live |
| S9 | minor | `__file__` as a taint seed cried wolf on a temp write merely *named* after the test module | **Fixed.** Rule keyed on the base of the path expression; that shape added as a cry-wolf control |
| S10 | minor | The no-exemption-registry refusal was evadable by the exact spelling it guards | **Fixed.** Second AST clause over the strings the guard actually uses, docstrings stripped |
| S11 | minor | The leak-guard half of the ADR's "refusal at both sites" was prose, not a test | **Fixed.** ADR wording narrowed to what is tested |
| S12 | minor | The isolation test blamed the fixture for older-revision residue | **Fixed.** Snapshots the glob, asserts no *new* entries |
| S13 | minor | Compensating assertion (a)'s second half was structurally unfailable | **Fixed.** Expected set rebuilt independently of the shared constant |
| S14 | nit | Plan arithmetic: Phase 2 acceptance says "4 passed", the module correctly has 5 | Recorded as a deviation |
| S15 | question | Three stronger-than-planned deviations existed only as code comments | Recorded as deviations in the report |

## Meta-audit

Six findings against the panel's own synthesis. Two changed what was done:

1. **major** — *Gated decision 3 declares the "do not edit the repro" constraint expired on
   evidence that does not exist yet; following it would destroy the RCA's strongest acceptance
   evidence.* Heeded. The S5 fix uses an environment variable rather than the recommended extra
   `argv` element, so `ABORT_CHILD` is untouched, it still calls the fixture with two positional
   arguments, and it still exercises the default-root path. Verified after the fix round: the
   repro file's diff against `HEAD` still contains **zero deleted lines**.
2. **major** — *The merge normalizes seven plan mutations to six, dropping exactly the one that
   pins the test the blocker orders rewritten.* Heeded. Mutation 7 was re-run against the
   **rewritten** anti-vacuity test and still kills it.
3. **major** — three plan-named "must keep observing PRODUCTION" leak-side tests scored by
   neither ledger. Re-checked directly: all three call their helpers with no root argument.
4. **minor** — nothing-else-regresses #3 scored by nobody. Measured: 613 → 644 tests, +22 added
   and 2 formerly-red now passing, none lost.
5. **minor** — parser lens GP-09's unexplained non-zero exit; now explained by S1.
6. **minor** — gated decision 2 recommended widening the verb set without measuring the risk the
   plan singles out. The meta-auditor ran it: safe, but only under destination keying. That is
   the keying used.

## What the panel got right that the plan did not

The plan's §4 mode-B recipe runs a reader loop over one module against a planter loop over
another, so two sessions can never be inside the same module at once. Every "after" number
produced by it was true and could not have observed S1. The panel ran the harness the RCA's own
narrative describes — concurrent sessions of the same suite — and the blocker surfaced in the
first pass, across four independent agents with four different harnesses.
