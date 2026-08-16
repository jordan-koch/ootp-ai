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

`enforce_admins: true` is deliberate: it means **nobody** merges past a red check,
which is what makes it safe for an agent to open and merge a PR. **Protection is
the guard, not the permission** — the agent still asks first, then merges and
cleans up on approval. See [CLAUDE.md](../CLAUDE.md) §Project conventions.

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

### Standing it up

```powershell
winget install Oracle.MySQL --version 8.4.9
& "$env:ProgramFiles\MySQL\MySQL Server 8.4\bin\mysql_configurator.exe"
```

The MSI only lays down binaries. The **configurator** is what creates the data
directory, writes `my.ini`, and registers the service — skipping it leaves you
with a `bin/` folder and no server.

> **Skip the configurator's "user accounts" step.** Its DB Admin role grants
> `SUPER`, `FILE`, `SHUTDOWN`, `RELOAD` and `CREATE USER` on `*.*`
> `WITH GRANT OPTION` — a near-root account for a pipeline that touches three
> databases. Use [`mysql-bootstrap.sql`](mysql-bootstrap.sql), which is
> database-scoped and localhost-only.

```powershell
# edit CHANGE_ME first, then put the same password in .env as MYSQL_PASSWORD
mysql -u root -p < ops/mysql-bootstrap.sql
```

> **Store the root password in a password manager, not in `.env`.** It is not a
> one-time credential — grants, user management and recovery all need it. If
> `.env` is its only copy, deleting that line loses it, and the way back in is a
> service stop plus an `--init-file` reset.

### Repairing a locked-out application user

`REVOKE ALL PRIVILEGES ON *.* FROM 'ootp_ai'@'localhost'` **also removes the
database-scoped grants**, not just the global ones — observed, and it leaves the
account at bare `USAGE` with `Access denied` on every database. No data is lost;
`REVOKE` never touches a schema.

[`mysql-bootstrap.sql`](mysql-bootstrap.sql) is the repair: its
`CREATE DATABASE IF NOT EXISTS` and `CREATE USER IF NOT EXISTS` are no-ops
against an existing install, and its three `GRANT`s restore access. Run it as
root.

### Bind to loopback

The configurator leaves `bind_address` **unset**, which means `*` — every
interface — and it adds inbound firewall rules for 3306 and 33060. A local-only
warehouse wants none of that. Under `[mysqld]` in `my.ini`:

```ini
bind-address=127.0.0.1,::1
mysqlx_bind_address=127.0.0.1
```

Both loopbacks, so a client that resolves `localhost` to `::1` still connects.
Then, from an **elevated** shell:

```powershell
Restart-Service MySQL84
netsh advfirewall firewall delete rule name="Port 3306"
netsh advfirewall firewall delete rule name="Port 33060"
```

`my.ini` is UTF-8 and contains a stray U+2212 in a comment. Rewrite it as UTF-8
with CRLF endings or the server will refuse to start on a mangled line.

### Authentication

MySQL 8.4 defaults to `caching_sha2_password` and ships `mysql_native_password`
**disabled**. An older client — the game's built-in export connector is the one
that matters here — may not speak the newer plugin, and the failure presents as
*wrong credentials* rather than *unsupported auth*. If that happens, add
`mysql_native_password=ON` to `my.ini`, restart, and recreate the user
`IDENTIFIED WITH mysql_native_password`.

Connect to `localhost` or `127.0.0.1`, never the machine name or a LAN address —
after the bind change, nothing else reaches the server.
