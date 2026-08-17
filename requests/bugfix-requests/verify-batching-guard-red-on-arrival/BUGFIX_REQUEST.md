> **Status:** diagnosed · created 2026-08-17 · decided · next: plan

# Bug Report — The acceptance panel's verify-batching guard has never been green

## Symptom

`.claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits **1 (RED)**
on a clean checkout, with no local changes and nothing to trigger it. Its own
`SKILL.md` documents exit 0 as the expected result. The guard has never passed
here, so the property it exists to prove — that stage 4's Verify phase stays under
its cap, merges only true duplicates, and degrades honestly — is **unproven**, and
has been since the skill arrived.

Four scenarios run and print plausible diagnostics; the assertions then fail:

```
[cap+dedupe] raw=8 deduped=7 batches=4/4 verifiers=5/5 unverified=0
[dead-batch] verifiers=4/5 unverified=2/7 note="verify:b1 (2 findings left unverified)"
[rubberstmp] b1Calls=2 verifiers=4/5 unverified=2
[verifyCap ] cap=2 batches=2 unverified=0/7

RED: acceptance verify-batching guard FAILED:
  - dedupe: raw=8, expected 11
  - dedupe: deduped=7, expected 9 (the 2 cross-lens duplicate pairs must merge)
  - dedupe: expected 2 merged findings, got 1
  - dedupe: over-merged land/writer.py - 2 distinct bugs expected, got 1
  - coverage: verified_findings=7, expected 9
  - verifyCap: a tighter cap changed how many findings survived dedupe
```

Note that the failures point **in two directions at once**: the guard complains
that two duplicate pairs failed to merge *and* that `land/writer.py` was
over-merged, in the same run. It is not a single-sided miscount.

## Reproduction attempt

**Deterministic.** From the repo root, with no arguments and no fixtures to set up:

```
node .claude/skills/implement-plan/tests/verify_batching_guard.mjs
```

Exit code 1, output exactly as pasted above. Reproduced 2026-08-17 on Node
v24.15.0, Windows 11. *(measured)*

**Two contrast checks, both run the same day:**

- **The sibling guard passes.** `node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs`
  exits **0 (GREEN)**. The defect is specific to the verify-batching guard, not to
  the panel harness or the way these guards are invoked. *(measured)*
- **It fails identically in `nba2k-rpg`.** The same command in the sibling repo
  produces **byte-identical stdout** and exit 1 — same four diagnostic lines, same
  six failure lines, same numbers. *(measured; previously an unverified claim
  carried in `CLAUDE.md`)*

**But the two copies are not the same file.** Against `nba2k-rpg`,
`acceptance_panel.js` differs by 13 insertions / 12 deletions and
`verify_batching_guard.mjs` by 6 / 6. Two separately-adapted copies producing
byte-identical failure output means the divergence is cosmetic and the defective
logic is the shared, inherited part. *(measured)*

## Expected vs Actual

- **Expected:** exit 0. `.claude/skills/implement-plan/SKILL.md` line 309 states
  the contract directly — "exit 0 = the Verify phase stays under its cap, merges
  only true duplicates, groups findings by location, adjudicates each against its
  own id, and degrades honestly when a batch dies or rubber-stamps · exit 1 = RED,
  read its printed reason · any other status = ERROR (did not run)." It further
  instructs: "Run it whenever `acceptance_panel.js` or this file changes."
- **Actual:** exit 1, on every run, with no changes made. A check that can never
  go green cannot gate anything; it can only be ignored.

## Severity

**No data at risk; a verification property is unproven.** Nothing is corrupted, no
save is touched, no money is spent, and no number reaches a baseball decision.

The cost is that stage 4's adversarial acceptance panel — the project's main
defence against an implementation that merely *looks* done — has an unverified
Verify phase. If `acceptance_panel.js` really does drop findings or over-merge
distinct bugs at the same file, then findings can be reported as verified without
having been verified, which is precisely the failure the panel exists to prevent
and precisely the kind that surfaces no error.

**Second-order and arguably worse:** the skill instructs the agent to run this
guard after every change to `acceptance_panel.js`. The instruction is currently
un-followable. A standing RED that everyone learns to step over trains the habit
of stepping over RED.

Not urgent — no warehouse exists yet, so few implementations have passed through
the panel — but it should be settled before stage 4 starts carrying real
parser and dbt work.

## Triage

- **Verdict:** needs-full-track
- **Obviousness hint (optional, non-binding):** not obvious, and specifically not a
  one-liner. `raw=8, expected 11` says three findings are missing before dedupe even
  runs, while the merge assertions disagree with each other about direction. At
  least two independent things look wrong, and which side of the guard/panel pair
  holds the defect is undecided.

## Affected Area & Pointers

A skill's verification tooling. A cold diagnosis agent opens, in order:

1. `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` — the guard and
   its fixture; the `raw=8 vs expected 11` gap starts here
2. `.claude/skills/implement-plan/acceptance_panel.js` — the dedupe and batching
   logic under test
3. `.claude/skills/implement-plan/SKILL.md` around line 309 — the stated contract
   both files are supposed to satisfy

`.claude/skills/implement-plan/tests/merge_fallback_guard.mjs` is worth reading as
the known-good sibling: same harness, same repo, GREEN.

## Reporter's cause-hunch (non-binding)

The guard and the panel were ported together from a sibling repo and appear to
disagree about the fixture. `raw=8, expected 11` reads like a fixture that lost
three findings in the port, or a guard whose expectations were written against a
different fixture than the one it now feeds in — in which case the merge
assertions downstream are counting against a set that no longer exists, and the
contradictory under-merge/over-merge pair is an artifact of that rather than two
separate bugs. Explicitly non-binding: diagnosis is free to find the panel at
fault instead.

This is the same porting-drift shape as `doc-link-guard-mismatch`, whose own Open
Questions already names this guard and asks whether the drift generalises.

## Open Questions for Diagnosis

- **Which side is wrong — the guard or the panel?** Fixing the guard's expectations
  to match the panel's behaviour and fixing the panel to match the guard produce
  materially different repos, and only one of them preserves the property
  `SKILL.md` promises. This must be decided, not assumed.
- **Where do the three missing raw findings go?** `raw=8, expected 11` is upstream
  of every other failure. If that one gap explains the rest, this is much smaller
  than it looks; if it doesn't, there are at least two defects here.
- **Is the under-merge/over-merge contradiction one bug or two?** The same run
  reports both. That is either a single miscount viewed from two assertions, or
  genuinely broken merge logic.
- **Is there a known-green baseline anywhere?** Both copies we have are RED and no
  upstream source has been established. Without one, "what correct looks like" has
  to be derived from `SKILL.md`'s prose rather than from a passing run.
- **Should this be diagnosed alongside `doc-link-guard-mismatch`?** Both are ported
  guards that describe behaviour this repo does not have. If the port dropped or
  mismatched artifacts systematically, one diagnosis covering the port may beat two
  covering symptoms.
- **Not a regression.** The guard arrived RED in the scaffolding port; there is no
  commit here at which it worked.

## Stage plan

**Full pipeline.** Trigger 1: Open Questions came out non-empty, and the first one
is load-bearing — whether the defect is in the guard's expectations or in
`acceptance_panel.js`'s dedupe decides which artifact gets rewritten, and a fix
that guesses wrong makes the guard green while leaving the real defect in place.
That is the worst available outcome, because it retires the only signal that
would have caught it.

Trigger 3 also fires, weakly: `acceptance_panel.js` is shared verification logic
that every future `/implement-plan` run passes through. Loosening the panel to
satisfy the guard would silently disable adversarial verification for all
downstream work, and nothing would surface the loss.

Trigger 2 clears — the reproduction is a single deterministic command with
byte-identical output across two repos.
