> **Status:** diagnosed · created 2026-08-16 · decided · next: plan

# Bug Report — The leak guard cannot see a file until it is staged, so it fires only after a leak can enter history

## Symptom

`tests/test_no_leaks.py` passes on a file containing a banned pattern, for as long
as that file is untracked. Staging the same file — with **no change to its
contents** — turns the same test red.

Observed during the `first-sight` scoping run. A generated artifact carried an
absolute Windows path (`<drive>:\projects\...`, redacted here). The full offline
suite ran green. The path was found by a hand grep, not by the guard.

## Reproduction attempt

**Deterministic.** From a clean tree:

> **This block cannot quote the offending string.** The guard has no fenced-code
> exemption, so writing a real banned pattern here — even inside a fence, even in a
> report *about* the guard — turns the suite red. Substitute any entry from the
> guard's own must-catch list at `tests/test_no_leaks.py:57-64`; that file is the
> sole member of `EXEMPT`, which is why it may hold what this one may not.

```
# 1. Create an untracked Markdown file carrying a banned pattern.
#    <LEAK> = any must-catch sample, e.g. a literal Windows drive path.
echo "the snapshot lives at <LEAK>" > _leak_repro.md

# 2. Untracked — the guard is blind to it.
uv run pytest tests/test_no_leaks.py -q
#    -> 3 passed

# 3. Stage it. Contents are byte-identical.
git add _leak_repro.md

# 4. Staged — the guard now sees it.
uv run pytest tests/test_no_leaks.py -q
#    -> FAILED tests/test_no_leaks.py::test_no_machine_paths_or_identifiers
#       AssertionError: machine-specific values in tracked files:
#         _leak_repro.md:3: windows drive path: the snapshot lives at ...

# cleanup
git rm --cached _leak_repro.md; rm _leak_repro.md
```

Confirmed on branch `bugfix/leak-guard-untracked-files` at `95c6cce`, then reverted;
the tree was left clean and the suite green at 18/18.

## Expected vs Actual

- **Expected.** The guard fires while a leak is still *editable* — before it enters
  history. That expectation comes from the repo's own stated rationale, not from the
  test: `.claude/skills/commit/SKILL.md` says catching a leak before it enters
  history *"is the difference between an edit and a history rewrite"*, and CLAUDE.md
  states that `tests/test_no_leaks.py` fails the build on machine-specific paths as
  the mechanism enforcing
  [ADR 0006](../../../docs/decisions/0006-public-repo-local-data.md).
- **Actual.** `tracked_text_files()` enumerates candidates by shelling out to
  `git ls-files` (`tests/test_no_leaks.py:32-38`), which lists tracked and staged
  paths only. A newly authored file is invisible to every pattern until the moment
  it is staged.

**The honest tension, stated for diagnosis rather than stacked.** The module
docstring says *"Nothing machine-specific may be tracked"*, and by that wording the
test does exactly what it claims. The mismatch is between the guard's literal scope
and the role the workflow assigns it. **Which of those two is wrong is the decision
this track exists to make, and this report does not presume it.**

## Severity

**No data at risk. Permanent public-history risk, bounded by what the patterns cover.**

Nothing is corrupted, no money is spent, and no number reaches a baseball decision.
The cost is that the guard's warning arrives one step later than the point where it
is cheap to act on, and the repo is public — CLAUDE.md: *"Everything tracked is
world-readable, forever."*

Three findings that bear on how much this actually hurts, all confirmed while
grounding this report:

1. **There is no `gitleaks` step.** `.github/workflows/ci.yml` runs ruff, mypy and
   `pytest -m "not gamedata"` and nothing else. `tests/test_no_leaks.py` is the
   **only** leak protection in the repo. Note that `.claude/skills/commit/SKILL.md`
   twice tells the agent that `gitleaks` will catch a secret in CI. It will not.
   *That may deserve its own request — see Open Questions.*
2. **There are no git hooks.** `.git/hooks` holds only the shipped `.sample` files,
   so nothing runs between staging and the commit object being written.
3. **CI does not run on a feature-branch push.** The workflow triggers on
   `pull_request` and on `push` to `main`. A leak can therefore be committed *and
   pushed to a remote branch* with zero checks having run; the guard first fires when
   a PR is opened, by which point the content is in published history.

Against that: the escape requires an author who does not re-run the suite after
staging, and the pattern set covers machine paths, home directories and email
addresses — not credentials, which nothing scans for at all.

## Triage

- **Verdict:** needs-full-track
- **Obviousness hint (non-binding):** the *mechanism* is a one-line read —
  `git ls-files` at `tests/test_no_leaks.py:32-38`. The **fix is not**, and that is
  the whole difficulty. Widening enumeration to the working tree naively would pull
  in `.venv/`, `__pycache__/`, `var/` and every gitignored scratch file, which is
  presumably why it was written this way. This is the same shape as the sibling
  defect in [doc-link-guard-mismatch](../_done/doc-link-guard-mismatch/): the cheap part is
  seeing it, the real part is choosing which direction to correct.

## Affected Area & Pointers

Repo tooling and the commit gate. A cold diagnosis agent opens, in order:

1. `tests/test_no_leaks.py` — `tracked_text_files()` at `:31-48` is the whole of the
   enumeration logic; `PATTERNS` at `:24-28`; `EXEMPT` / `EXEMPT_PREFIXES` at
   `:16-18`, which exist because the guard must not trip on its own source and would
   need rethinking under any wider scan.
2. [`.claude/skills/commit/SKILL.md`](../../../.claude/skills/commit/SKILL.md) — the
   staging step, which is where the expectation of pre-history catching is stated,
   and where the incorrect `gitleaks` claim lives.
3. [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml) — confirms the
   guard is blocking, confirms no secret scanner, and carries a comment at `:22-24`
   recording that the `git ls-files` dependency is **deliberate**: the checkout needs
   the real repo *"not a detached blob export."* Any fix must keep CI working.

## Reporter's cause-hunch (non-binding)

The enumeration choice looks intentional rather than accidental — `git ls-files` is
the cheapest way to get "files that matter, minus everything ignored", and the CI
comment shows someone reasoned about it. If so this is less a coding error than a
scope that was never revisited once agents began generating large artifacts directly
into the tree. Explicitly non-binding; diagnosis is free to find otherwise.

## Open Questions for Diagnosis

1. **Is this a defect or a feature request?** The docstring's wording is satisfied by
   the current behaviour. If the answer is "the guard is correct and the workflow
   should stage earlier", the fix is a skill change, not a test change — and this
   report should be reclassified. Rendering that verdict is stage 2's job.
2. **Which direction?** Widen the guard to scan untracked-but-not-ignored files; add
   a pre-commit hook; add a real secret scanner; or change `/commit` to stage before
   it verifies. These produce materially different repos, and more than one may be
   right.
3. **How does a wider scan avoid scanning junk?** `git status --porcelain
   --untracked-files=all` respects `.gitignore` and may be the drop-in — unverified.
   Whether `EXEMPT_PREFIXES` still behaves under it is unknown.
4. **Should the absent `gitleaks` be folded in here or filed separately?** A skill
   promising a check that does not exist is symptom-for-symptom identical to
   `doc-link-guard-mismatch`'s symptom A. Two ported-guard drifts and this makes a
   third instance of the same pattern — the sibling report's own third open question
   asks whether the drift is systemic. This may be the evidence that it is.
   Related and found while writing this report: **`test_no_leaks.py` has no
   fenced-code exemption either.** That makes two Markdown-scanning guards in this
   repo with the same gap, and it has a concrete cost — a bug report about a leak
   cannot quote the leak it is reporting, which is exactly the *"so a report can
   quote a dead target"* rationale the skills give for fence exemption. Whether the
   two guards should share one exemption policy is worth settling once, not twice.
5. **Not a regression.** The guard and the CI workflow arrived together in the
   scaffolding commit, so this has been true since day one. It went unnoticed because
   nothing generated sizeable artifacts into the tree until the scoping panels began
   writing `reviews/` files.

## Stage plan

**Full pipeline.**

**Trigger 1 fires, decisively.** Open Questions came out non-empty and not
cosmetically: the first asks whether this is a bug at all, and the second asks which
of four materially different repos we want. Neither is something a fix should assume.

**Trigger 2 clears** — the reproduction is deterministic and takes four commands.

**Trigger 3 fires weakly.** The guard is a blocking CI check and the sole enforcement
mechanism of ADR 0006, which is a pillar. Loosening it wrongly is not merely costly:
it is the check standing between a public repo and permanently published content.
Trigger 1 alone is sufficient, so no argument for skipping stage 3 is available.
