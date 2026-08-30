# 0004 — MySQL is the warehouse

**Status:** Accepted
**Date:** 2026-08-15

## Context

The warehouse holds per-sim-date snapshots of league state plus the static
reference dimensions. It runs locally: no cloud, no credentials, no cost.

Candidates considered:

- **DuckDB** — the sibling `nba-analysis` repo's choice. Embedded, zero-admin,
  excellent dbt support (`dbt-duckdb` is first-party-quality), columnar and fast
  for analytical scans.
- **PostgreSQL** — first-class dbt adapter, mature, server-based.
- **MySQL** — OOTP ships a native "Export data directly into a MySQL database"
  action and MySQL SQL-dump generation, and documents the schema for it
  (`db_structure_*_mysql.txt`).

## Decision

**MySQL is the warehouse**, running locally.

The deciding factor is that MySQL is the one engine OOTP itself targets. The
one-time ground-truth export ([ADR 0002](0002-parse-binaries-not-export.md)) can
land directly in the warehouse in the same shape the game intends, making
parser-vs-export validation a SQL comparison inside one database rather than a
file-format reconciliation.

## Consequences

**Buys:**

- The ground-truth export loads natively, with OOTP's own documented schema, into
  the same engine the pipeline uses. Validation becomes `SELECT`-and-compare.
- A familiar, ordinary operational surface.
- A server-based engine handles concurrent readers (the front-office agents)
  against a warehouse being written by an ingestion run, which an embedded
  single-writer engine makes awkward.

**Costs:**

- **`dbt-mysql` is a community adapter**, materially less mature than
  `dbt-duckdb` or `dbt-postgres`. Expect thinner support for newer dbt features,
  slower compatibility with dbt releases, and fewer people having hit any given
  bug. This is the real price of the decision and it is accepted knowingly.
- Row-store engine on analytical workloads: slower than DuckDB for wide scans
  over snapshot history. Volume here is small enough that this is unlikely to
  bind, but it will not improve.
- Requires a running server and credentials in `.env`, versus DuckDB's single
  file. More setup, more to document, one more thing that can be down.

**Forecloses:**

- Nothing permanently. The medallion layers are SQL; if `dbt-mysql` becomes the
  binding constraint, migrating to Postgres is a real but bounded port. Supersede
  this ADR if that happens, and record what actually broke.

## Notes

The MySQL *export* being unavailable in Challenge Mode
([ADR 0003](0003-challenge-mode-league.md)) does **not** undermine this decision.
The export's value is one-time validation from a standard-mode save; the
warehouse engine choice is independent, and the parser writes to MySQL directly.

### Measured 2026-08-15 — the adapter cost is worse than estimated

The "less mature adapter" cost above was written as a prediction. It is now
measured, and it is concrete:

| Package | Latest | Pins |
|---|---|---|
| `dbt-mysql` | **1.7.0** | `dbt-core~=1.7.0` |
| `dbt-postgres` | 1.11.0 | — |
| `dbt-duckdb` | 1.11.0 | — |

Adopting `dbt-mysql` means **pinning dbt-core four minor versions behind**, on a
package whose release history between 1.1.0 and 1.7.0 is a run of alphas. There
is no `dbt-mariadb` or maintained fork on PyPI.

There is also a **cost/benefit asymmetry** this ADR did not weigh at the time.
The benefit — OOTP exporting natively into MySQL — applies to a **one-time**
ground-truth load from a disposable standard save
([ADR 0002](0002-parse-binaries-not-export.md)). The adapter cost is **permanent
and applies to every model forever**. A one-time convenience was traded against
an ongoing constraint.

**This is not yet resolved and does not need to be.** No dbt model exists, so no
dependency has been taken. The `transform` dependency group was removed from
`pyproject.toml` rather than pinned, per the repo's own rule that dependencies
arrive with the source that requires them.

The decision comes due when the first dbt model is requested. The live options:

1. Pin `dbt-core` to 1.7 and accept it.
2. Keep MySQL, drop dbt — hand-rolled SQL plus a thin runner. Loses lineage,
   tests, and docs, which is most of why dbt was wanted.
3. **MySQL as the export landing zone, Postgres as the analytical warehouse.**
   Keeps the native-export benefit exactly where it applies and buys a
   first-class adapter everywhere else. Costs a second engine.
4. Move the warehouse to Postgres outright and load the one-time export through
   a converter.

Option 3 or 4 is likely correct on the evidence. Superseding this ADR is
expected, not a failure — record what actually broke.

### Measured 2026-08-29 — the trigger fired, and dbt was deliberately not pulled

The condition above — *"the decision comes due when the first dbt model is requested"* —
has been passed in a way that paragraph did not anticipate. **A warehouse landed with no
dbt model at all** (`first-sight` Phases 8b–11: eight bronze tables in MySQL, append-only
on `(save_id, sim_date, ingest_seq)`, a per-field differential against the export, and two
reports served off it). The trigger fired sideways, so it is recorded here rather than
left for someone to notice.

**What is deferred is the tooling, not the pattern.**
[ADR 0005](0005-hybrid-data-layer.md) split the data layer by physics — *does this change
when the league is simulated?* — and that choice is honoured in full. Bronze exists and is
append-only; nothing has landed on the wrong side of the rule. What has not happened is
bronze → silver → gold **expressed in dbt**, because no silver model has been needed yet:
every consumer to date resolves a single snapshot triple and reads bronze directly.

**Why a note and not a superseding ADR.** A postponement is not a reversal. All four
options above are still live and nothing measured since narrows them, so spending ADR 0024
on "not yet" would record a decision that was not made — and would read, later, as though
one had been. The option this repo actually forbids is the third one: diverging from an
accepted ADR quietly, so the divergence is found by someone who reads the code and stops
believing the docs.

**The trigger is now sharper than it was.** It is
[`incremental-loading`](../../requests/feature-requests/incremental-loading/). The moment
the warehouse holds one league at two sim dates, a cross-snapshot fact exists, ADR 0005
puts that in silver, and options 1–4 have to be chosen between rather than deferred again.
That request's Open Questions already name this as its central gate. **Do not pre-pick an
option here** — the evidence that should decide it is exactly what that work produces.
