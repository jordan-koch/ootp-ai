# Ops

Repo governance and local toolchain.

## Branch protection

`main` is protected. [`branch-protection.json`](branch-protection.json) is the
source of truth for that configuration — it is applied by hand, and this file is
how it gets restored if it is ever lost or changed in the GitHub UI.

```bash
gh api -X PUT repos/:owner/:repo/branches/main/protection \
  --input ops/branch-protection.json
```

> **`required_status_checks.contexts` matches CI job *display names*, not job
> ids.** Rename a job in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
> without updating this file and every PR waits forever for a check that never
> reports, with no error explaining why. Change both in the same commit.

`enforce_admins: true` is deliberate: it means **nobody** merges past a red
check, which is what makes it safe for an agent to open and merge a PR.

## Local toolchain

```bash
uv sync                 # dependencies
cp .env.example .env    # then fill in — see ADR 0006
uv run pytest           # structural guards; add -m gamedata for save-backed tests
uv run ruff check .
uv run mypy
```

**The `gamedata` marker** covers tests that need a real OOTP install or save.
They are excluded from CI, which has neither and must never have either. Run
them locally before opening a PR that touches the parser — CI cannot catch a
parser regression for you.

## MySQL

The warehouse ([ADR 0004](../docs/decisions/0004-mysql-warehouse.md)) runs
locally. Credentials live in `.env`; nothing is tracked. No cloud resource in
this project should ever cost money — if a future phase introduces one, it needs
an ADR and an auto-suspend story before it lands.
