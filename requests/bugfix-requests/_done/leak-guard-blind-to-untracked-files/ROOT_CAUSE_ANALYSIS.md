> **Status:** diagnosed · created 2026-08-17 · decided · next: plan

# Root Cause Analysis — The leak guard's candidate set excludes the files most likely to leak

> **This document cannot quote the strings it is about.** `tests/test_no_leaks.py` scans
> every tracked `.md`, its `EXEMPT` set at `:16` holds exactly one entry, and that entry is
> not this file — so a real banned pattern written here turns the build red. Every example
> below is described rather than shown. That constraint is not a footnote: it is the second
> half of the same defect, recorded under *Fix posture → Hardening*.

## Verdict

**confirmed-bug**, and the request's first Open Question — *is this a defect or a feature
request?* — resolves to **defect**. Needs the full track: the cause is a one-line read, but
the direction is a real decision and one of the four candidates the request proposed is
**refuted by measurement**.

**Why not `works-as-intended`,** which the request fairly raised. The module docstring at
`tests/test_no_leaks.py:1` says *"Nothing machine-specific may be tracked"*, and by that
sentence alone the guard is correct. Three things outweigh it:

1. **It failed at its assigned job three times in one session** (2026-08-17). A planning
   agent wrote absolute machine paths into an untracked `reviews/` artifact; the full
   offline suite ran green; the paths were found only by a hand scan that *imported this
   guard's own `PATTERNS`*. Then it happened again on a second trail file, and a third time
   on an untracked report. Zero were caught by the guard.
2. **`CLAUDE.md` names this test as the enforcement mechanism for ADR 0006** — "the repo is
   PUBLIC ... `tests/test_no_leaks.py` fails the build". It is the only leak protection
   that exists (confirmed below), so its scope is not a private implementation detail.
3. **The docstring is the narrowest statement of intent in the repo, and it was written by
   the same commit that wrote the enumeration.** Accepting a guard's own self-description as
   the authority on its scope would immunise every guard against every scope complaint.

## Reproduction (red)

`tests/test_leak_guard_scope.py` — seven tests, one RED, six green as counterweights.
Offline, in CI's `-m "not gamedata"` selection. **Not yet committed.**

```
uv run pytest tests/test_leak_guard_scope.py
```

```
.F.....
FAILED tests/test_leak_guard_scope.py::test_an_untracked_file_is_visible_to_the_leak_guard
E   AssertionError: the leak guard cannot see an untracked file, so it fires only once
    the content is staged — the point at which a leak can enter history
```

The module writes a real probe file into the working tree (a `tmp_path` fixture cannot
serve — the guard enumerates *the repository*, so the probe has to live inside it) and
removes it in a `finally`. Its banned string is **assembled at runtime** so this repo never
contains a literal one outside the exempt file.

**The six green tests are deliberate and are the harder half.** They pin what a fix must
*not* do: a gitignored file must stay out of scope, and none of `.venv/`, `__pycache__/`,
`node_modules/` or `var/` may enter the candidate set. Widening enumeration is easy; widening
it without making the guard unusable — and therefore switched off — is the actual problem.
A seventh test asserts the probe string still matches a banned pattern, so the scope
assertions cannot pass vacuously if `PATTERNS` changes.

## Evidence (the cause)

`tests/test_no_leaks.py:31-48`, `tracked_text_files()`, shells out to **`git ls-files`**
(`:32-38`). That command lists the **index** — tracked and staged paths. A file that has just
been written is not in the index, so it is not in the candidate list, so `:83` never opens it
and none of the patterns at `:24-28` are ever applied to it.

The failure is therefore **not** a pattern miss. Every one of the three real leaks this
session matched `PATTERNS` perfectly — that is how the manual scan found them, by importing
those very patterns. The guard never read the bytes.

**The consequence is a timing inversion.** `.claude/skills/commit/SKILL.md:78` states the
principle the guard is supposed to serve: catching a leak before it enters history *"is the
difference between an edit and a history rewrite"*. Because the guard's visibility begins at
`git add`, its first possible warning arrives at the moment the content becomes committable.

Three amplifiers, all re-confirmed here:

- **`tests/test_no_leaks.py` is the only leak protection in the repo.** `git grep -il gitleaks`
  over `.github/`, `ops/` and `pyproject.toml` returns nothing.
- **No git hooks.** `.git/hooks` holds only the shipped samples.
- **CI does not run on a feature-branch push** — `.github/workflows/ci.yml:3-6` triggers on
  `pull_request` and on push to `main`. A leak can be committed *and pushed* with no check
  having run.

### Two corrections to the intake report

Recorded rather than carried forward, because both were checked:

- **`gitleaks` is promised once, not twice.** One occurrence, `.claude/skills/commit/SKILL.md:78`.
  The claim is still false — no such step exists — but the count was wrong.
- **Open Question 3's candidate is refuted.** `git status --porcelain --untracked-files=all`
  is **not an enumeration of the repository**; it reports only *changed* entries. Measured on
  a clean tree it returns **0 paths**, and with one untracked file present it returns **1**.
  Substituting it would silently reduce the guard from scanning 140 files to scanning only
  what happened to be dirty — a catastrophic coverage regression that would still pass every
  existing test, since the existing tests assert only that no violation is found.

### The idiom that does work, measured

`git ls-files --cached --others --exclude-standard` — the canonical "tracked plus untracked,
minus ignored" form:

| Check | Result |
|---|---|
| Clean tree | 140 paths, identical to `git ls-files` |
| With one untracked probe | 141 — the probe **is** included |
| `.venv/`, `__pycache__/`, `node_modules/`, `var/` | **0 entries each** |
| A probe under `var/tmp/` | **absent** — `.gitignore` respected |
| `.env` | **absent** (gitignored) — it legitimately holds machine paths |
| `.env.example` | present — the `!.env.example` negation is honoured |

That last pair matters more than it looks: a widening that pulled in `.env` would put the
guard in permanent conflict with a file whose whole job is machine-specific values.

## Fix posture (tiered)

**Minimal.** Swap the enumeration at `tests/test_no_leaks.py:33` to
`git ls-files --cached --others --exclude-standard`. Measured above to flip the red test and
keep all six counterweights green. Note `.github/workflows/ci.yml:22-24` records that the
`git ls-files` dependency is deliberate — CI needs the real repo, "not a detached blob
export". The proposed form has the same requirement, so that comment stays true.

**Root.** The minimal fix moves the guard's first warning from `git add` to "any test run",
which is better but still not the stated goal of catching a leak *before it can enter
history*. Whether that goal needs more than the test — a pre-commit hook, or `/commit`
scanning before it stages — is the direction question below. Note also that
`test_game_data_is_not_tracked` at `:97-116` enumerates via `git ls-files` **a second time**
and has the same blindness for `.dat`/`.lg` files; a fix touching only `tracked_text_files()`
leaves that one open.

**Gated decision — for the plan, not the fix.** The request's Open Question 2 lists four
directions and they are not mutually exclusive:

> (a) widen the guard's enumeration · (b) add a pre-commit hook · (c) add a real secret
> scanner · (d) change `/commit` to stage before it verifies.
>
> **Recommendation: (a) now, and (d) as a one-line ordering note.** (a) is measured, small,
> and moves detection to every local test run. (d) is nearly free — `/commit` already runs
> the guard, and running it *after* staging is a sentence in the skill — and it closes the
> gap for anyone who does not run the suite first. **(b) is the one I would not take**: a
> hook lives outside version control, so it protects only the machine that installed it,
> which is the same class of "protection that isn't there" as the missing `gitleaks`. (c) is
> genuinely valuable and genuinely separate — the patterns cover machine paths, home
> directories and email addresses, and **nothing in this repo scans for credentials at all** —
> but it is a new capability, not a defect, and belongs on the feature track.

**Hardening (gated).** `tests/test_no_leaks.py` has **no fenced-code exemption**, which is why
neither the intake report nor this RCA can quote the string it is reporting. Its sibling
`tests/test_doc_links.py` gained exactly that exemption on 2026-08-17. Two Markdown-scanning
guards in one repo with opposite policies is a decision worth making once; the counter-argument
is real, though — a fence exemption in a *leak* guard is a way to smuggle a credential past it,
which is not true of a link checker. Recommend settling it explicitly rather than by drift.

## What this does not close

- **The false `gitleaks` claim at `.claude/skills/commit/SKILL.md:78`** is a fourth instance of
  the ported-artifact drift class and belongs in
  `requests/bugfix-requests/port-residue-sweep/`, not here. Filing it as a fifth request
  would fragment the same finding across three trackers.
- **A real secret scanner** is a feature-track item, per the recommendation above.
- **`test_game_data_is_not_tracked`'s** parallel blindness, unless the plan folds it in.
