# Feature Requests

Home for every substantial new piece of work — a parser, a dataset builder, a dbt
model, an advisor, a skill. The point is a **light, repeatable set of guardrails**
around how an idea travels from *"I want X"* to *"a cold agent can implement X"* —
without turning a one-hour change into a week of process.

> **Bugs go elsewhere.** A **defect** in existing code has its own track
> ([`../bugfix-requests/`](../bugfix-requests/)). Code that **ran green and
> produced wrong data** has a third ([`../data-incidents/`](../data-incidents/)).
> Tie-break: missing = feature, broken-that-exists = bug, ran-clean-but-wrong =
> incident.

## The pipeline

| # | Stage | Skill | Produces | Shape |
|---|---|---|---|---|
| 1 | **Intake** | `/make-feature-request` | `FEATURE_REQUEST.md` | Interview — turns a raw idea into a scoped, repo-grounded request. Fast, single-agent. |
| 2 | **Scope** | `/scope-feature` | `PROJECT_SCOPE.md` | Panel: 3 divergent scopers → merge/converge → 2 adversarial. Settles fit + testable acceptance criteria. |
| 3 | **Plan** | `/create-implementation-plan` | `IMPLEMENTATION_PLAN.md` | Panel: 3 planners → merge → 2 code-grounded adversaries + 1 meta-audit. Cold-handoff plan. |
| 4 | **Implement** | `/implement-plan` | code + `IMPLEMENTATION_REPORT.md` | Panel: core reviewers + auto-scaled specialists → execution-based verify → meta-audit. Proves every acceptance criterion by running it. |

Each stage produces one artifact and is **human-gated** — you review and edit
before invoking the next.

**All four stages run by default.** Stages 2 and 3 are skippable only by an
argument written into the request's closing **Stage plan** section and cleared
against the three hard triggers in
[`../README.md`](../README.md#weight--the-panel-is-the-default). Stage 4 still
runs either way: with no plan to consume it enters **direct-build mode**, taking
this request as the statement of intent.

## Every dataset comes from here

No file gets parsed and no dataset gets registered without a request behind it. A
dataset carries **contracts** — a grain, keys, a freshness expectation, an
upstream that can change without warning — and those are decisions, not
implementation details.

A dataset request must settle, before any code:

- **Grain.** One row per *what*? "Player per snapshot" and "player per team-stint
  per snapshot" are different tables, and the difference is invisible until a
  mid-season trade breaks a join.
- **Keys.** What makes a row unique, and is that enforceable as a test? Note that
  OOTP's internal `player_id` and the real-world Lahman ID are different keys with
  different coverage — only ~1,712 players have the latter.
- **Coverage.** Which populations does this source actually contain? Fictional
  players lack external IDs; minor leaguers lack much of what majors carry.
  Structurally-absent data is not missing data, and conflating them produces
  silently wrong aggregates.
- **Update semantics.** Append-only per snapshot, or does history get restated?
- **Which data-layer pattern.** Apply the ADR 0005 rule: *does this change when
  the league is simulated?* No → builder + `datasets/`. Yes → parser + dbt.
- **Registration.** For builder datasets, the logical name it takes in
  `datasets/manifest.json`. Consumers resolve by name; nothing hardcodes a path.

## Parser work carries an extra obligation

Anything that reads the save binaries must state, in the request:

- **What ground truth validates it**, and for which fields. `players.csv` is the
  default; a simulated ground-truth export is stronger.
- **Its epistemic labels.** A field map asserted without validation is
  `unconfirmed`, and saying so is the difference between a task and a liability.
- **How it fails.** A parser that seeks to a fixed offset will pass on day-0 data
  and corrupt everything later ([data-access.md §4](../../docs/data-access.md)).
  The request should say why this one doesn't.

## Acceptance criteria

"Testable" has a specific meaning here. A criterion is testable when a **cold
agent can run one command and get a pass or fail** — not when a human can eyeball
a number and nod.

- ✅ *`pytest tests/test_parser_teams.py` is green: all 30 MLB clubs extract with
  the abbreviations and ARGB colors pinned in `tests/fixtures/teams.json`.*
- ✅ *Parsed ratings for every player present in `players.csv` match it exactly —
  `pytest -m gamedata tests/test_rosetta.py` proves it.*
- ✅ *Re-parsing the same snapshot twice produces byte-identical output.*
- ❌ *The ratings look about right.*

Criteria only a human can prove — whether a recommendation is *good baseball*,
whether a briefing is readable — are legitimate and central to this project, but
must be **marked user-run** so the acceptance panel doesn't claim them.

## Layout

The directory **is** the unit of work:

```
feature-requests/
  <slug>/                      # kebab-case (e.g. 1-dat-parser)
    FEATURE_REQUEST.md         # stage 1
    PROJECT_SCOPE.md           # stage 2
    IMPLEMENTATION_PLAN.md     # stage 3
    IMPLEMENTATION_REPORT.md   # stage 4 — acceptance ledger + what shipped
    reviews/                   # panel working files — the provenance trail
  _done/<slug>/                # archived once it reaches a terminal stage
```

**Active-vs-done.** An item lives at the track root while in flight; when it
reaches the terminal stage — `implemented` — it moves **once** into `_done/`. The
Index keeps the row with its link pointing into `_done/`.

Every artifact opens with a status blockquote:

> **Status:** &lt;stage&gt; · created &lt;YYYY-MM-DD&gt; · &lt;open | decided&gt; · next: &lt;stage or "implement"&gt;

**Status grammar:** `intake` → `scoped` → `planned` → `implemented`

A skipped stage skips its status: an argued direct build goes `intake` →
`implemented`, and the absent artifacts are the record that it did.

## Index

| Feature | Stage | Notes |
|---|---|---|
| [tree-seam-for-remaining-guards](tree-seam-for-remaining-guards/) | intake | Two guards walk `src/ootp_ai/` from disk — `test_grain_contracts.py`'s `historical_id` join scan and `test_read_only.py`'s write/destructive scans — and **neither can be proved to report a real file**. Both are pinned against strings, which tests the rule and not the enumeration; a mutant returning zero files leaves both green, which is the exact shape that shipped broken three times here. Newly worth filing because [ADR 0022](../../docs/decisions/0022-guard-probes-plant-in-a-tree-they-own.md) just made the obvious way to close it **forbidden** — `test_probe_isolation_contract.py` fails any test that writes into the live tree, so the door was shut before the replacement was built. The D6 follow-up the guard-probe bugfix named rather than left as an observation. **Carries a real trap:** the last fix needed a *repo* root because its exemption keys are repo-relative, while `test_read_only.py`'s allowlist is package-relative — so the correct answer there may be the opposite, and assuming symmetry is how this gets done wrong silently. Open question 1 is whether to build it at all |
| [first-sight](first-sight/) | planned | The `.dat` parser, warehouse landing, a data catalog, and the starting reports — the first time the GM can see its own club. Scoped as **reshape**: ratings decoupled behind the scouted-view spike, dbt deferred. Planned in 14 phases; `tests/` is main-thread-authored because it is in the builder's deny set. **Phase 10 landed the roster report — the GM can now name its own players — and Phase 11 the catalog, so it also knows what it is not seeing:** of 89 declared fields, 55 reach a page, 11 are withheld and 23 are read but landed by nothing. The standings half was retired by dated amendment (no declared table carries a win-loss column), and Core §14's requirement to name `players.prone_*` / `players_value.*` was retired by a second one, because AC15 forbids exactly that. **Phase 12 trued the docs up and found three claims measurably false** — there is no `leagues.dat` (19 `.dat` files in a Challenge-mode save, 18 in a standard-mode one), `league-rules.md` §1 is *not* superseded by the warehouse since no landed table carries a rules column, and the standard-mode validation save is **retained, not disposable**. It also recorded the dbt deferral on ADR 0004 and opened the GM's report channel with an engineering-owned report kind. It raised **zero** epistemic labels and says why: the claims Tier A/B settled were already at their correct labels, and the real gap was that none named the test holding it. Only Phase 13 (USER-RUN acceptance) remains, so the stage stays `planned` |
| [gm-inbox](gm-inbox/) | intake | The eight letters in `messages/` that nobody reads, including the one that hired the GM — the only channel by which it could learn what ownership thinks of it (ADR 0015). Widens `SNAPSHOT_FILES`, which is ADR 0018 tier 2. Reading personal mail ruled **free**; the open question is where that ruling stops, since a BNN prospect list arrives in the same folder |
| [agent-memory-curation](_done/agent-memory-curation/) | implemented | The `data-engineer`'s memory file hit its 250-line CI ceiling while its own rules say *append freely, never prune* — no legal move at the boundary, mid-build. Ceiling removed; curation moved to `/update-docs`, triggered on the file appearing in a staged diff. **Direct build**, argued and disposed. The genus split (method vs tooling) is explicitly deferred until a sweep produces the evidence |
| [secret-scanning](secret-scanning/) | intake | **Nothing in this repo scans for credentials.** `tests/test_no_leaks.py` covers three shapes — drive paths, home directories, email addresses — so a token, key or connection string passes untouched. No `gitleaks`, no hooks, and two skills that wrongly say otherwise (owned by `port-residue-sweep`). Routed here by the leak-guard bugfix, which fixed *when* the guard looks rather than *what* it looks for |
| [league-dimension](league-dimension/) | intake | The warehouse holds 259 clubs across **17 league ids** and cannot name a single league — `world.dat`'s per-league scalar blocks are unwalked, so `docs/league-rules.md` asserts roster limits from memory with no landed source. Filed out of `first-sight` Phase 9, which measured the gap: the export's `leagues` has 15 rows, two referenced ids (215, 219) have none, and their four clubs are all all-star sides. Also inherits the structural-absence trap Phase 9 could not use — the export writes `0` for roster limits on all 14 non-MLB leagues |
| [incremental-loading](incremental-loading/) | intake | **The warehouse has never held one league at two in-game dates.** The append-only mechanism is built and tested along the `ingest_seq` axis; the *time* axis is not — `test_a_landing_at_another_sim_date_is_left_untouched` queries for a second date and **skips loudly when it finds none**, so it has never created one, and passes today only because two different universes sit at different dates. Nothing reads across snapshots either: every consumer resolves one triple. Filed out of `first-sight` Phase 10 as its follow-up 1. Work runs against the disposable Challenge twin; simming the managed league is out. Open: whether this is the trigger that finally pulls dbt in, since ADR 0005 puts cross-snapshot facts in silver and ADR 0004 §Notes defers it |
| [ingest-command](_done/ingest-command/) | implemented | **Nothing outside the test suite can put data in the warehouse.** `ingest_save` and `land_snapshot` have no `__main__`; `src/ootp_ai/` ships two entry points and both only *read* a landing. `tests/fixtures/warehouse.py` is the de facto caller, so the two universes in the warehouse were landed by running `pytest`, and `README.md` currently documents that as the setup path. Withheld deliberately rather than forgotten — `reports/__main__.py` records that entry points are scarce and patterned — which is why this is a feature and not a bug. Found while truing the docs up in `first-sight` Phase 12. Filed standalone at the operator's direction: it builds the vehicle, [incremental-loading](incremental-loading/) drives it. Rendering stays `reports render`'s. **Scoped `clean` — in shape; the risk sits in one operator-facing default and one test-suite re-point, not in the diff.** The panel found the request's own Scope Signals wrong in the safe direction (no `WRITERS` entry is needed — `_writes_in` scans a module's own source text, so the allowlist stays byte-unchanged) and the gap *wider* than filed: `ensure_tables` has one caller and `ops/mysql-bootstrap.sql` creates **no tables**, so the test suite creates the schema as well as filling it. Both adversaries independently blocked the panel's own recommended re-run default as an ADR-level divergence — ADR 0021 §Context rejects a date-keyed refusal **by name** — so the default shipped is the **digest pre-flight**: unchanged bytes refuse, changed bytes at an unchanged sim date land the next seq automatically, no ADR amendment needed. Six gated decisions disposed; `uv run python -m ootp_ai.ingest land`, with `ingest.py` promoted to a package. **Planned in 7 phases**, and the planning panel's own headline number was wrong: it closed the scope's mandated cost decision claiming digest-before-copy wins "three orders of magnitude", when a re-measurement shows the digest costs **~2x the copy it avoids** (36-48 ms against 18-20 ms over 52.4 MiB). The decision stands on the argument that survives — copy-then-compare burns a sequence and leaves an unreclaimable 52.4 MiB directory on every refusal. Code-grounding also caught a `ParsedSnapshot \| None` that reds `mypy --strict` at both call sites, a size-only pre-flight with no representable value (`SnapshotFile.sha256` is mandatory), and an AC6 monkeypatch target that does not exist. **Implemented — 17/17 agent-verifiable criteria met, AC18/AC19 USER-RUN and unclaimed; 880 tests, 879 passed.** The acceptance panel's meta-audit earned its place twice over: the synthesis reported "two blockers raised, both refuted" when one was independently **confirmed**, and that suppressed finding was the real one — the gamedata gate was red on handover because the tests' first `main()` sat outside the `try:` that purges, so any failure stranded a full landing, and a leaked row moved the next run's sequence arithmetic under it. One such landing was found in `ootp_dev` and reclaimed. Now census-driven and 5/5 green across five runs. The panel also caught a sentence **this scope had explicitly banned** — CLAUDE.md claiming `read_save` is the only code that opens a game file, which is false — and an AC15 assertion that was a disjunction incapable of failing. `source_facts`' game reads are now inside ADR 0001's bracket at a measured cost of 2:40 against 2:42 without |
| [news-subscription-dial](news-subscription-dial/) | intake | Governance, not pipeline: ADR 0019 priced the subscription dial and the machinery does not exist. Records what the club subscribes to, enumerates the 12 categories, and gives `gm/ledger.jsonl` a vocabulary for **refusal** so a declined proposal is not re-proposed forever. Small diff, large decision surface |
| [open-front-office](open-front-office/) | scoped | Rules refactor: the experiment is infrastructure + adaptive agent, not simulated attention scarcity. Scoped as **reshape** — split into Phase A (ADRs 0022/0023, execution log, hash-chained journal, trigger loop, guards, context assembler, doc rewrites) which ships unconditionally, and Phase B (`gm_view`, the restricted grant, the GM query tool) **gated on a tool-channel spike**, because the harness has no path-level permission system and the repo has no query vehicle. The GM's write channel becomes a typed umpire-side lander, not a `Write` grant. Lands **after** first-sight Phases 10–13 |
