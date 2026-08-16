# Agents

Write-capable implementation subagents. One Markdown file defines one agent; the harness
registers each frontmatter-bearing `.md` here as a spawnable agent type.

This directory is the *developer* half of the manager/developer split. The main thread holds
strategy — scoping rationale, whether this is still the right shape. An agent here holds a
rulebook and builds to a spec.

## What is in here

| File | What it is |
|---|---|
| `data-engineer.md` | The definition. Human-maintained. **The agent may not edit it.** |
| `data-engineer-memory.md` | The agent's memory. It appends; humans curate. |
| `README.md` | This file. |

**One definition per agent, and the definition owns its rules.** The build rulebook lives in
`data-engineer.md`, not in [`CLAUDE.md`](../../CLAUDE.md) — deliberately, so the rules have a
single owner instead of two copies that drift. `CLAUDE.md` keeps a pointer for the main
thread, which still builds directly for the carve-outs.

**Frontmatter is the discriminator.** Exactly one file here carries YAML frontmatter with a
non-empty `name` and `description`; that is the definition. The memory file and this README
carry none and are ignored by the loader.

**The memory file is the single `.claude/` carve-out** in the agent's write allowlist, stated
there as an exact path — `.claude/agents/data-engineer-memory.md` — rather than as a prefix
rule. Everything else under `.claude/` is denied.

## Spawn protocol

The main thread runs this. It reuses stage 4's procedure
([`implement-plan/SKILL.md`](../skills/implement-plan/SKILL.md)) rather than inventing a
second mechanism, extended with two extra captures.

**1. Preconditions.**

- On a **feature branch**, never on `main`.
- The tree is **clean, or holds only the agent's own prior work.** Spawn a write-capable
  builder onto a dirty tree and a human can no longer tell the agent's writes from their own
  in the staged diff at `/commit` — which is the review gate the whole design leans on.

**2. Pre-spawn capture.** `var/tmp/` is gitignored and does not exist on a fresh clone —
create it first, or the capture silently fails.

```
New-Item -ItemType Directory -Force var/tmp
git status --porcelain
git rev-parse HEAD
git stash list
git diff HEAD --output=var/tmp/<slug>-pre.patch
```

Use git's own `--output=`, not PowerShell redirection, which would write a BOM. On a clean
tree the patch is **empty** by construction — the load-bearing captures are the status, the
untracked list, `HEAD`, and the stash list.

**3. Spawn — from a fresh session, and this is not optional.** A definition written moments
ago may not be spawnable yet: the attempt fails with *"Agent type not found"*, which reads
exactly like "this harness doesn't support agents". It is not — the registry re-scans later.
Treat that error as *not yet*.

The stronger reason is context. **The `CLAUDE.md` an agent inherits is a snapshot frozen at
its parent session's start, and can be commits behind the file on disk.** A fresh session
inherits the current file. If the agent's task depends on recent repo state, say so in the
spec and tell it to read from disk rather than trust what it was given.

Hand the agent: the spec, its declared target paths, the handoff path under
`requests/<track>-requests/<slug>/reviews/`, and the reminder that git is read-only for it —
**and that the game is read-only for everything**. Then **do not narrate its edits**: the
whole point is that the main thread does not have to.

**4. Post-run comparison.** Re-run the same captures and diff them against the pre-spawn set.
Confirm: no tracked file outside the declared allowlist was modified or deleted, nothing
pre-existing was reverted, `HEAD` unchanged, `git stash list` unchanged. Grep for one symbol
you knew existed before the spawn — a passing test does not prove your files are still there.

**Also confirm nothing under the OOTP install or saved-games directory changed.** That is
this repo's version of the unrecoverable outcome, and no test in the tree would notice it.

Save the pre/post pair into the request's committed `reviews/` trail. It must not live only
in `var/`: that is gitignored, `/commit` refuses it, and CI never sees it.

## Detection, not prevention

Say this plainly, because the design depends on nobody misreading it.

**This harness has no path-level permission system.** Agent frontmatter's `tools:` key gates
*which tools* an agent holds — that part is real and enforced — but nothing gates *which
paths* those tools may touch. The write allowlist in a definition is **prose**. An agent
that ignores it is not stopped by anything.

**It does not fail safe in the other direction either.** A harness permission layer sits
underneath the tool grant and can *deny* a write the definition explicitly allows. So the
effective permission is the intersection of the declared allowlist and a layer you cannot
see, and a blocked write is a normal outcome an agent should report rather than route around.
Do not build anything that treats a declared allowlist as authoritative in either direction.

So the feature branch, the clean-tree precondition, the pre-spawn snapshot, the post-run
comparison, and `/commit`'s staged-list-then-yes all catch a bad write **after** it happens.
Nothing prevents one. That is a deliberate, recorded trade — see
[ADR 0009](../../docs/decisions/0009-write-capable-implementation-subagent.md) — and it is
why every one of the steps above is written down rather than left to whoever remembers.
