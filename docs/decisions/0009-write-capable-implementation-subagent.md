# 0009 — A write-capable implementation subagent

**Status:** Accepted
**Date:** 2026-08-15

## Context

Every other subagent in this repo is read-only. That rule exists because of a recorded
incident in a sibling project: *a write-capable review agent ran `git checkout` and silently
wiped uncommitted work while a vacuous selftest passed green.*

But build work has a different shape from review work. When the main thread implements a
plan directly, it narrates every edit into its own context — and a large parser build spends
most of its context on file-by-file detail that the manager does not need and that crowds out
the scoping rationale it does.

The alternative is a **manager/developer split**: the main thread holds strategy and hands a
decided spec to an agent that holds a build rulebook, then reads back a fixed-format handoff
instead of a diary.

That requires an agent that can write files.

## Decision

**One write-capable implementation subagent — `data-engineer` — defined in
[`.claude/agents/data-engineer.md`](../../.claude/agents/data-engineer.md), which is the
single owner of the build rulebook.**

It is bounded by a **prose write allowlist**, a **prose deny set**, an absolute
**git-is-read-only** rule, an absolute **the-game-is-read-only** rule, and a fixed
**return contract** whose `verified` rows must cite real command output.

The main thread runs a **spawn protocol** around it: feature branch only, clean tree,
pre-spawn snapshot, post-run comparison, evidence committed to the request's `reviews/`
trail.

## Consequences

**Buys:**

- The manager's context stays on the decisions. A build no longer costs the main thread a
  file-by-file read of its own work.
- The rulebook gets a single owner. Build rules live in the agent definition rather than
  duplicated into `CLAUDE.md`, so they cannot drift apart.
- Spec-triage mode makes a bad plan cheap to discover before anyone spends a build on it.
- The handoff's `verified` table forces execution-grounded claims rather than assertions.

**Costs:**

- **The allowlist is prose, and nothing enforces it.** This harness has no path-level
  permission system: `tools:` gates which tools an agent holds, never which paths they touch.
  An agent that ignores the allowlist is not stopped by anything.
- **It does not fail safe in the other direction either.** A permission layer underneath the
  tool grant can *deny* a write the definition explicitly allows, so effective permission is
  the intersection of the allowlist and a layer nobody can see.
- The spawn protocol is real overhead — snapshot, compare, commit the evidence — on every
  build, and it is the kind of overhead that gets skipped when someone is in a hurry.
- Trusting the `verified` table is load-bearing. An agent that fabricates a row defeats the
  whole design, and the main thread by construction is not re-reading the work.

**Forecloses:**

- Treating a declared allowlist as authoritative in either direction. Nothing built on top
  of this may assume the bound is enforced.

## Notes

**This is detection, not prevention, and the distinction must not be blurred.** The feature
branch, the clean-tree precondition, the pre-spawn snapshot, the post-run comparison, and
`/commit`'s staged-list-then-yes all catch a bad write *after* it happens. Nothing prevents
one.

This repo carries one failure mode the sibling projects do not: **a write to the game is
unrecoverable.** The managed league runs in Challenge Mode
([ADR 0003](0003-challenge-mode-league.md)), whose saves carry an integrity hash, and there is
no upstream to restore from. The post-run comparison therefore checks the OOTP install and
saved-games directories as well as the repo — no test in the tree would notice that damage.
