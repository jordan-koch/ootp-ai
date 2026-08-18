---
name: commit
description: >-
  Stage the current work, check the docs still describe it, show you exactly what's about to land,
  and commit once you say yes. This is the ONLY sanctioned path by which an agent commits in this
  repo — never run `git commit` ad hoc. Use it whenever a unit of work is finished: "commit this",
  "commit the changes", "let's land this", "/commit", or as the natural end of a pipeline stage.
  It stages deliberately (never a blind `git add -A`), refuses to stage secrets or bulk data, runs
  the doc-drift checks proportionally to what changed, keeps the `requests/` artifact statuses and
  track Index rows in step with what actually landed, proposes a message, and asks before writing anything.
  On approval it commits and pushes the feature branch. It does NOT open the PR, never pushes
  `main`, and never force-pushes — those stay yours. It does NOT run lint, types, tests; CI owns
  those and runs them on the PR.
---

# Commit

## What this produces and why

One commit, on a branch, containing exactly what you meant to land — after the docs have been
checked against it and you've seen the staged list.

The rule this replaces was "agents never commit," which was correct about the risk and wrong about
the friction. The actual hazard isn't an agent committing; it's an agent committing **something you
didn't see**: a stray credential, a 400MB Parquet file, a half-finished refactor swept up by
`git add -A`. So the guard is *deliberate staging plus an explicit yes*, not a blanket prohibition.

**Keep this skill lightweight.** It is a gate, not a pipeline. If it grows a panel, something has
gone wrong.

---

## Step 1 — Survey

```
git status --porcelain --untracked-files=all
git diff HEAD --stat
git branch --show-current
```

**Read the actual diff**, not just the file list. You're about to describe it in a commit message,
and a message that misdescribes its diff is worse than no message.

**Branch check.** If the current branch is `main`, say so and stop for a decision. `main` is
protected and work is supposed to land by PR. Offer to create a branch — `git switch -c
<descriptive-slug>` — and note that this is cheap now and annoying later. Proceed on `main` only if
the user explicitly says to.

## Step 2 — Stage deliberately

**Never `git add -A` or `git add .` without reading the untracked list first.** That single habit
is the one this skill exists to prevent.

Go through the untracked and modified files and decide, per file, whether it belongs in this
commit. Then stage by path.

**Refuse to stage** any of these, and say why rather than staging quietly:

| Refuse | Because |
|---|---|
| Anything under `var/` | Gitignored working root — regenerable, machine-local |
| `.env`, `*.pem`, `*.key`, credentials | This repo is **public**; a leaked secret is permanent in history |
| `*.parquet`, `*.sqlite`, `*.db` outside `tests/fixtures/` | The repo holds code, config and docs — not bulk data |
| `players.csv`, `*.dat`, `*.xml` reference files, anything under a `.lg/` | **OOTP's data is not ours** (ADR 0006) — never tracked, at any size |
| `var/`, `node_modules/`, `.venv/`, `__pycache__/` | Generated or machine-local |
| Anything you can't explain the presence of | If you don't know why it changed, neither will the reviewer |

Most of these are already in `.gitignore`. If one shows up as untracked anyway, that's a
`.gitignore` gap worth fixing in this same commit — say so.

Then sanity-check what you staged:

```
git diff --cached --stat
```

Then run the leak guard:

```
uv run pytest tests/test_no_leaks.py
```

It sees untracked files, so it is worth running **before** staging too — the earlier it fires,
the cheaper the fix. It covers machine paths, home directories and email addresses.

**It does not scan for credentials, and nothing else in this repo does either.** So read the
staged diff yourself for anything resembling a token, an account ID, a bucket name, or a
connection string — catching one *before* it enters history is the difference between an edit
and a history rewrite. A credential scanner is filed as
`requests/feature-requests/secret-scanning/`; until it lands, that read is the only thing
standing between a pasted secret and a public repo.

## Step 3 — Doc drift, proportional to the change

Run the checks in proportion to what actually changed — this is the step that keeps the gate
lightweight.

**Run the full [`/update-docs`](../update-docs/SKILL.md) sweep** when the change touches anything
the docs describe:

- a new or changed directory (the `CLAUDE.md` project map)
- a new convention, constraint, or gotcha (the rules sections)
- a new dataset, external source, or a changed grain (dataset docs, and its manifest entry)
- a completed phase or a changed setup step (`README.md`)
- anything contradicting an accepted ADR
- a source claim that moved from `unconfirmed` to `verified` (`docs/data-access.md`)
- a request artifact whose status advanced (the track Index rows)
- **`.claude/agents/data-engineer-memory.md` appearing in the staged diff** — that file has
  no size guard in CI on purpose, so the sweep's audit of it is the only curation it ever
  gets. The trigger is the file's presence, not a judgment about whether the entries look
  fine; an agent appended, so a human reads.

**Otherwise, do the two-minute version yourself:**

```
uv run pytest tests/test_doc_links.py -q
```

plus a read of `CLAUDE.md`'s project map against the tree. A typo fix in a test does not need the
full sweep, and pretending it does is how a gate becomes something people route around.

If `/update-docs` flags something needing your judgment — a superseded ADR, a grain/test mismatch —
**stop and surface it.** Those are not commit-blockers by policy, but they're decisions, and a
commit is a bad place to make one silently.

## Step 4 — Request status

**This repo has no `ROADMAP.md`.** Work is driven from `requests/` alone, so the status record
this skill owns is the **request artifacts and their track Index rows** — the two places that go
stale the moment work lands.

Every artifact opens with a status blockquote, and each track README carries an **Index** table.
**This skill owns keeping the two in agreement.** Nowhere else in the pipeline is guaranteed to run
at the moment work actually lands, so if the gate doesn't advance them, they rot.

Check the staged diff against the request the work belongs to, and update in the same commit:

| Signal in the diff | What to update |
|---|---|
| A new artifact landed (`PROJECT_SCOPE.md`, `IMPLEMENTATION_PLAN.md`, …) | The artifact's own status blockquote, and the track Index row's Stage cell |
| The work reached its terminal stage — `implemented` / `fixed` | The Index row, **and** move the directory once into `_done/` with the Index link repointed |
| Nothing matches a request | Leave every status alone |

**Status grammar** is the track README's, not this skill's: feature work runs
`intake → scoped → planned → implemented`; bugfix work runs `intake → diagnosed → planned → fixed`.
An argued stage skip ([ADR 0008](../../../docs/decisions/0008-panels-by-default.md)) skips its
status too — the absent artifact is the record that it did.

**Match on what's actually in the tree, not the branch name.** A branch called `dat-parser` that
only lands a `FEATURE_REQUEST` is at `intake`, not `implemented`.

Two rails, because this is a record rather than a plan:

- **Never mark ahead.** A request is `implemented` when the commit that completes it is being made,
  not when a plan says it will be.
- **Never mark down silently.** If work already recorded as terminal looks regressed or reverted,
  stop and surface it. Walking a status backwards is a decision, not bookkeeping.

If the change is a doc edit, a typo fix, or otherwise maps to no request, say "no request change"
and move on. Most commits are this.

Stage the artifact and its track README by path if you edited them — the status belongs in the same
commit as the work it describes, not in a tidy-up commit afterwards.

## Step 5 — Propose, then ask

Show the user four things:

```
STAGED    — the file list, grouped by area, with the stat line
DOCS      — what the drift check did: updated / flagged / clean
REQUESTS  — which request statuses moved, and to what — or "no request change"
MESSAGE   — the proposed commit message
```

**Message format:** an imperative subject line under ~72 characters saying what the commit *does*,
and — when the change isn't self-evident — a body explaining *why*, wrapped at 72. The diff already
shows what changed; the body is for what the diff can't say.

```
Add teams.dat parser and ARGB colour fixture

Records carry variable-length regions, so the reader walks them
sequentially rather than seeking. The fixture pins all 30 MLB clubs
against players.csv, since a mis-mapped u16 returns a plausible number
rather than an error.
```

Then **ask, explicitly, and wait.** Not a rhetorical "shall I commit?" trailing a wall of text — a
real question with the staged list visible above it. The user's yes is the gate.

That one yes covers **commit and push** (Steps 6 and 7). Say so when you ask, so the scope of the
approval is on screen rather than assumed.

## Step 6 — Commit

On approval, **write the message to a file and commit with `-F`.** Not `-m`:

1. Write the full message — subject, blank line, body — to `var/commit-msg.txt` **using the `Write`
   tool**, not a shell redirect.
2. ```
   git commit -F var/commit-msg.txt
   ```
3. Delete the file. `var/` is gitignored, so a leftover is harmless, but a stale message is a trap
   for the next run.

**Why not `-m`.** Windows PowerShell 5.1 rebuilds the argument list for native executables, and a
double quote *inside* a here-string or a quoted `-m` argument terminates the argument early. A
message containing `"..."`, a backtick, or a token that looks like a switch gets split, and git
receives the fragment as a flag — the observed failure was ``unknown switch `D'`` from a body that
mentioned `-D`. It fails loudly rather than committing something wrong, but it fails every time and
the workaround is not obvious mid-commit.

**Why the `Write` tool and not `Out-File`/`Set-Content`.** Both default to UTF-8 **with a BOM** in
PowerShell 5.1, and git copies the BOM into the message as literal leading characters. `Write`
emits UTF-8 without one, so em-dashes and accented names survive intact.

`var/commit-msg.txt` is repo-relative on purpose. Never write an absolute path into a tracked file —
`tests/test_no_leaks.py` fails the build on drive letters and home directories, and this repo is
public.

Hard rails, no exceptions without an explicit request:

- **Never `--no-verify`.** If a hook fails, that's the hook working.
- **Never `--amend`.** Amending rewrites history that may already be pushed. A follow-up commit is
  almost always right; if the user genuinely wants an amend, they'll say so.
- **Never `-A` at this stage.** Staging happened in Step 2, deliberately — plus the doc and
  request files you edited in Steps 3–4, staged by path.

## Step 7 — Push the branch

The user's yes in Step 5 covers the commit **and** pushing it. Push without asking again:

```
git push -u origin <branch>
```

`-u` on the first push of a branch, plain `git push` after. Then report the short SHA and the
PR-creation URL the remote hands back.

Three limits, and they are not negotiable without an explicit request:

- **Never push `main`.** If Step 1 was overridden and the commit landed on `main`, stop here and
  hand the command back. Protection will reject it anyway; better to say so than to generate a
  confusing rejection.
- **Never force-push.** Not `--force`, not `--force-with-lease`. Rewriting published history is the
  user's call, always.
- **Never open the PR.** Push, then hand over the URL. Opening it — title, body, reviewers — is a
  judgment call the user makes.

Pushing runs CI only if a PR exists; a first push to a fresh branch triggers nothing, because the
workflow fires on `pull_request` and on `push` to `main`. Say so rather than leaving the user
watching for a run that will never start.

---

## What good looks like

- **Nothing landed that the user didn't see.** The staged list was shown before the yes, not after.
- **Staging was per-path, not wholesale.** `git add -A` appears nowhere in the transcript.
- **The message describes the diff.** Someone reading `git log` in six months learns why, not just
  what.
- **The doc check was sized to the change.** Full sweep on a new model; link check on a typo fix.
- **The `requests/` statuses still describe reality.** An artifact's status blockquote and its
  track Index row agree, and both moved in the same commit as the work — never marked ahead of the
  work, never walked backwards without asking.
- **No OOTP game data was staged.** Not a `players.csv`, not a `.dat`, not a save snapshot — at
  any size, for any reason (ADR 0006).
- **It committed and stopped there.** No push to `main`, no PR, no merge, no amend, no
  force-push, no `--no-verify`.
