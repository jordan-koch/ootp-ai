> **Status:** intake · created 2026-08-17 · open · next: scope

# Feature Request — Nothing in this repo scans for credentials

## Problem

The repo is public and there is **no credential scanning of any kind**. Verified
2026-08-17 with `git grep -il gitleaks` over `.github/`, `ops/` and `pyproject.toml`:
nothing. `.git/hooks` holds only the shipped samples. CI runs ruff, mypy, pytest and the
node skill guards, and nothing else.

`tests/test_no_leaks.py` is the only leak protection that exists, and its `PATTERNS`
cover exactly three shapes: Windows drive paths, unix home directories, and email
addresses. A token, an API key, a connection string, a private key block or an account id
passes it untouched — not because the guard is weak, but because it was never asked to
look for those.

**A skill still tells agents this is already handled.** `.claude/skills/update-docs/SKILL.md`
lists `gitleaks` among the mechanical checks that "moved to CI, where it runs on every PR
and cannot be skipped". It is false. A second occurrence in `.claude/skills/commit/SKILL.md`
was removed on 2026-08-17 while its surrounding paragraph was being rewritten. The
remaining prose is owned by `requests/bugfix-requests/port-residue-sweep/` as instance 7
and is not this request's to fix — but it is the reason to think the gap is *believed
closed*, which is worse than a gap known to be open.

## Why now

`requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/` routed this here rather
than folding it in. Its ROOT_CAUSE_ANALYSIS is explicit: a real scanner is "genuinely
valuable and genuinely separate" — a new capability, not a defect in an existing one.
That fix widened *when* the existing guard can see a file; it did nothing about *what* it
looks for, and it would have been dishonest to let closing it imply otherwise.

The exposure is also about to grow. `requests/feature-requests/first-sight/` is the first
work to render game data to files, and its own risk register notes the exposure is new.

## Desired outcome

A credential scan that runs where it cannot be skipped, with a false-positive posture
this repo can actually live with — the existing guard's history shows that a check which
cries wolf gets worked around rather than fixed.

## Scope signals

- **CI is the enforcement point**, since there are no hooks and a feature-branch push
  runs nothing (`.github/workflows/ci.yml` triggers on `pull_request` and push to `main`).
- **The existing guard is the model for the seam, not the mechanism.** It exposes
  `git_paths()` and two helpers so tests can assert against them; a scanner should be as
  testable, and should be *seen to fail* before it is trusted.
- **A tool, not a hand-rolled regex set.** Credential detection is a solved problem with
  maintained rule sets; three patterns written by hand is what the repo has now.
- **Entropy scanning needs an allowlist strategy before it is switched on**, or the first
  green build is the last one anybody believes.

## Explicitly out

- The false `gitleaks` prose in the two skills — owned by `port-residue-sweep`.
- **The existing guard's scope, both halves** — settled by the leak-guard bugfix on
  2026-08-17. It enumerates tracked, staged and merely-written files, and its `keep` set
  gained `.js`/`.mjs`/`.jsonl` in the same fix, which brought the eight panel scripts and
  `gm/ledger.jsonl` into scope. Measured after: **144 of 148 enumerated paths are scanned.**
  What this request is about is *what the patterns look for*, not where they look.
- Retroactively scanning history. This request is about stopping the next one; a history
  audit is a different job with a different risk profile.

## Open questions

- **Which tool**, and does it need to run offline? CI has network; a pre-commit path may
  not.
- **What is the failure posture** — block the PR, or annotate? A blocking check nobody can
  satisfy gets disabled, which is how the repo ends up back here.
- **Does it replace or complement `tests/test_no_leaks.py`?** That guard also enforces
  ADR 0006's no-game-data rule, which no credential scanner knows about, so "replace" is
  probably wrong.
- **Does the same scan run over `var/`?** It is gitignored and full of machine-specific
  values by design, so almost certainly not — but a scratch file with a real token in it
  is still a real token on disk.

## Stage plan

**Full pipeline.** Trigger 1: the Open Questions above are non-empty and the failure
posture question is load-bearing — a blocking scanner and an advisory one are materially
different repos. Trigger 3 fires too: this touches CI, which every future change passes
through.
