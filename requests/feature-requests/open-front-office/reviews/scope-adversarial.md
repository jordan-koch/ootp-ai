# Scope Panel - Adversarial Findings and Convergence Map

> Verbatim output of the two adversaries, plus the merge stage's convergence map.
> Panel run 2026-08-19, wf_854b2b93-a5a - 64 findings (6 blocker, 27 major).

## Adversary summaries

```json
[
    {
        "adversary":  "fit-ac",
        "summary":  "I verified the merged scope\u0027s repo-fit claims against the tree and they hold up unusually well: `.claude/` contains only `agents/` and `skills/` (no `.mcp.json`, no `settings.json`); `.claude/agents/README.md:104-107` says verbatim what the scope quotes; `ops/mysql-bootstrap.sql:63` does grant ALL PRIVILEGES on `ootp_truth_real`; `contracts/policy.py:89-95/164-184/180/82` are all where the scope says; `tests/test_bronze_landing.py:763` really does omit `DROP VIEW`; `.github/workflows/ci.yml:24` pins `fetch-depth: 1`; `.gitattributes` really does set `gm/ledger.jsonl merge=union`; ADR 0004 §Notes option 2 is verbatim \"Keep MySQL, drop dbt\"; 21 ADRs exist so 0022/0023 is right; and zero tests reference `gm.md`. I reproduced the disposition measurement myself and got 8/96/94/1/1 exactly, and the field-map category split 48/31/10/0 exactly. The framing is honest about the biggest embarrassment (the wall guards one byte). So the fit verdict \"reshape\" is sound and I am not attacking it.\n\nWhat I am attacking is internal coherence and acceptance-criteria testability, where the scope is materially weaker than its grounding. Three things rise to blocker: (1) ADR 0022 is placed in Phase A although the scope\u0027s own splitting rationale says 0022\u0027s decision depends on Phase B\u0027s unverified capability — so Phase A would land an ADR that supersedes the report wall while the GM still reads reports; (2) AC2\u0027s \"94 renderable over all 8 tables\" is arithmetically incompatible with the core scope\u0027s decision not to serve `bronze_name` (I measured the real number as 88, plus a joined name column that is not a declared column at all), so the headline offline criterion is unsatisfiable as written; (3) the request\u0027s central promise — \"physically unreachable, enforced by a database grant rather than prose\" — reduces under MySQL DEFINER-rights view semantics to \"unreachable given correct view text\", and no acceptance criterion anywhere checks that an emitted view body references only the configured warehouse schema. The grant is real; it just does not constrain what a definer-rights view may read.\n\nBelow that, a cluster of ACs are vacuous, self-contradictory, or aimed at the wrong artifact — AC4\u0027s fragment backstop is provably tautological given `policy.py:180` already applies the same fragments to column names (\"a guard that passes by never firing\", which `policy.py:81` names as the failure to avoid); AC10\u0027s hash-chain guard would go red on the existing `gm/ledger.jsonl`, which has no `prev` key and which the same scope says not to migrate; AC12 asserts over fields the declared journal envelope does not have. And two non-goals bury real work: the write-grant foreclosure closes the request\u0027s own Open Question 2 on an unverified prose claim while the twin question gets a spike, and the leak-guard non-goal hands credential coverage to `secret-scanning` while leaving the *new* vector the scope itself discovered — OOTP player rows in world-readable `gm/` — with no owner, no core item and no AC."
    },
    {
        "adversary":  "scope-completeness",
        "summary":  "I re-derived the merged scope\u0027s load-bearing measurements and citations before attacking it, and most hold: 8 tables / 96 columns / 94 renderable / 1 withheld (`bronze_name.name_category`) / 1 uncertain (`bronze_league_event.real_sim_date`) reproduces exactly; the field map is 48 `identity` / 31 `structural` / 10 `rating-true` / 0 `rating-scouted` across 89 fields; `.claude/` really holds only `agents/` and `skills/` (no `.mcp.json`, no `settings.json`); `.claude/agents/README.md:104-107`, `ops/mysql-bootstrap.sql:63`, `.gitattributes:26`, `.github/workflows/ci.yml:24`, `tests/test_bronze_landing.py:763`, `policy.py:180`, `README.md:194` all say what the scope says they say. The reshape verdict is correct and the risk register is unusually good. My attack lands in two places.\n\n(A) SCOPE DISCIPLINE. The tiering has three real defects rather than a general over-reach. First, an internal contradiction at the top: gated decision 4 argues the two-ADR split is a *dependency* split because 0022\u0027s enforcement claim rests on the unverified harness capability — and then `tiered_scope.core` puts **both** ADRs in \"PHASE A\", the unconditional half. That makes the gate dishonest at its most load-bearing point. Second, the `_history` sibling per view is filed `cheap_fold` while doubling the view set, the grant list, the grain tests and the committed SQL snapshot — for a warehouse holding one sim date. Third, three items promoted or folded into core actively contradict each other: baking `WHERE save_id = \u003cmanaged\u003e` into every view forces the emitter to read `.env` (it currently reads only `Contracts`, and `ddl.py`\u0027s docstring makes \"connects to nothing\" the property worth copying), which kills the byte-deterministic committed-SQL fold in a CI that has no `.env`; and emitting per-view `GRANT` statements collides with the schema-level `GRANT SELECT ON gm_view.*` the same scope puts in `ops/mysql-bootstrap.sql`.\n\n(B) COMPLETENESS. The scope enumerates its doc-rewrite surface and gets it materially wrong in the direction that matters. `gm/staff.md` is absent from the list, yet its entire \"Why this file can exist at all\" section is built on ADR 0013\u0027s scarcity denominator plus 0016. `gm/standing-orders.md` is scoped to its `## Reports` block only, while lines 3-8 and the `Established: ledger seq \u003cn\u003e` format are equally 0013-priced. `FRONT_OFFICE.md`\u0027s rewrite is costed at four spots when at least eight statements break. Worse, ADR **0012:41-42** — declared untouched and \"strictly stronger\" — contains a Buys clause that reads *\"Combined with ADR 0013, scout quality becomes measurable: actions spent, outcomes returned\"*, so retiring 0013 invalidates a clause of an ADR the non-goals forbid touching. Three surviving mechanics are dropped by silence: 0013\u0027s standing-order lever and its 20-proposals autonomy graduation, and 0019\u0027s *first* limiter (\"may this analysis exist at all\", explicitly described there as structural rather than economic). The scope names 0018\u0027s foresight trap and 0019\u0027s refusal loop as needing re-homing but not these. Beyond doctrine: the five dataset contracts for `gm_view` are never settled as a block (coverage and update semantics are simply absent, and the pipeline README makes them mandatory); the acceptance criteria are not partitioned by phase, so a Phase-A-only ship has no defined done-ness; the only replacement denominator lives entirely in the gated half while the retirement is unconditional; nothing constrains post-hoc query fishing, which is the direct analogue of the retroactive-labelling failure 0013 forecloses; and the scope never notices that `docs/decisions/`, `tests/`, `ops/`, `.claude/` and `CLAUDE.md` are all in the `data-engineer` builder\u0027s deny set (`.claude/agents/data-engineer.md:154-165`), making most of Phase A main-thread work — while `gm/` is *not* in that deny set, which a hash-chained append-only `gm/` needs it to be."
    }
]
```

## Findings

```json
[
    {
        "id":  "F01",
        "title":  "ADR 0022 is placed in Phase A but its decision depends on Phase B — the scope contradicts its own splitting rationale",
        "severity":  "blocker",
        "confidence":  "high",
        "category":  "framing",
        "location":  "tiered_scope.core bullet 1 (\"PHASE A — TWO ADRs, numbered 0022 and 0023\") vs. fit_verdict (\"0023 depends on nothing, 0022\u0027s enforcement claim depends on an unverified harness capability\") vs. gated_decisions[3] (\"both accepted together\")",
        "problem":  "The scope\u0027s stated reason for splitting into two ADRs is a dependency split: 0023 needs nothing, 0022 needs the tool-channel spike. It then puts BOTH ADRs in Phase A, which it defines as shipping unconditionally, and gated decision 4 says they are \"both accepted together\". These cannot all be true. Concretely, if Phase A ships and the spike fails, the repo lands an accepted ADR 0022 that supersedes ADR 0016 (the report wall) and amends ADR 0017\u0027s no-DB foreclosure \"into a scoped grant\" — while no grant exists and the GM is still reading reports. `docs/decisions/README.md:6-7` calls re-litigating a settled decision the most expensive thing that can happen here; an ADR whose Decision section describes a mechanism that was never built is worse than the wall it retired, because a later reader cannot tell which parts are live. This is not a wording problem: it is the load-bearing sequencing decision of the whole reshape, and the reshape is the headline gated decision the operator is being asked to accept.",
        "proposed_fix":  "Split the ADR set along the phase boundary, not along the topic boundary. Phase A lands 0022 as the ATTENTION model only — supersede 0013/0018/0019, retire the budget, install the execution log — plus 0023 as the memory model; both genuinely depend on nothing. The 0016 supersession and the 0017 no-DB amendment become 0024, authored and accepted in Phase B only if the spike passes. If the spike fails, 0016 stands unamended and the honest end state the scope already describes (\"better reports under a retired economy\") is exactly what the ADR record says. Then fix gated decision 4\u0027s \"both accepted together\" to \"0022 and 0023 together in Phase A; 0024 in Phase B or not at all\", and renumber accordingly (`tests/test_repo_structure.py::test_adrs_are_sequentially_numbered` forbids gaps, so 0024 must not be reserved in advance).",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F02",
        "title":  "AC2\u0027s \"94 renderable over all 8 tables\" is arithmetically incompatible with the core scope\u0027s decision not to serve bronze_name",
        "severity":  "blocker",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[1] (\"for all 8 tables in `load_contracts()` and all 96 declared columns … pinned against the measured baseline (94 renderable)\") vs. tiered_scope.core PHASE B gm_view bullet (\"`bronze_name` is not served raw … names resolve into the player view as text\")",
        "problem":  "I measured the per-table renderable counts against the shipped declaration: bronze_team 21/21, bronze_player 24/24, bronze_team_roster 6/6, bronze_name 6/7, bronze_division_team 7/7, bronze_league_event 11/12, bronze_field_label 10/10, ingest_run 9/9. If `bronze_name` is not served, the served renderable total is 88, not 94, and only 7 views exist rather than 8. Worse, the player view is then to carry a resolved name column that is not a declared column of `bronze_player` at all — so the AC\u0027s core assertion (\"each emitted view\u0027s SELECT list equals exactly the set where `column_disposition(...) is Disposition.RENDERABLE`\") is false by construction for the one view the GM will actually use most. As written the headline offline criterion cannot pass, and an implementer will resolve the contradiction silently in whichever direction is easier.",
        "proposed_fix":  "Rewrite AC2 in two parts and drop the count. Part one, an invariant that survives new columns: for every table that HAS an emitted view, the set of view columns sourced from declared columns equals exactly the RENDERABLE set for that table, asserted by name with mismatches enumerated. Part two, a frozen exception ledger asserted by name — the tables deliberately not served (`bronze_name`, with its reason), the two non-renderable landed columns (`bronze_name.name_category` withheld, `bronze_league_event.real_sim_date` uncertain), and every view column that is a derived expression rather than a declared column (the resolved name), each with the argument for its presence. That is the same LANDED_BUT_WITHHELD / LANDED_UNDER_BANNER discipline `tests/test_withheld_fields.py:309-331` already uses. Delete \"94\": a pinned scalar goes red when `league-dimension` adds a legitimate column, which trains people to bump the number.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F03",
        "title":  "\"Physically unreachable, enforced by a grant\" reduces to view-text correctness under MySQL DEFINER semantics, and no criterion tests the view bodies",
        "severity":  "blocker",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "goals[1]-[3]; acceptance_criteria[4] and [5] (the two GAMEDATA grant criteria); risks[16] (\"MYSQL VIEW PRIVILEGE SEMANTICS ARE `assumed`\"); FEATURE_REQUEST.md:76-79 (\"a fact about its connection\")",
        "problem":  "The grant AC enumerates schema-level denials — `ootp`, `ootp_dev`, `ootp_truth_real`, `mysql`, plus INSERT/UPDATE/DELETE/CREATE — and an information_schema-invisibility check. All good, all testable. But a MySQL view created by the application user runs with DEFINER rights by default, and that definer holds ALL PRIVILEGES on `ootp_truth_real` (`ops/mysql-bootstrap.sql:63`). That is precisely what makes the read-through to bronze work; it also means a `gm_view` view whose body selects from `ootp_truth_real.players_scouted_ratings` would serve the answer key to the restricted user, and every AC in the set would still be green. The enforcement point is therefore the emitted SQL text, not the grant — which is one level below prose, not above it. The scope names the semantics as `assumed` in risks[16] and then writes goals[1]-[3] and the ADR\u0027s enforcement claim as though the grant were the boundary. This is the single place where the request\u0027s central promise is overstated in the merged scope.",
        "proposed_fix":  "Add two acceptance criteria and one ADR sentence. OFFLINE: every emitted `CREATE ... VIEW` statement\u0027s body references exactly one schema — the configured warehouse schema — asserted by parsing qualified identifiers out of the generated text, with `ootp_truth_real` and the truth-database `.env` value named as forbidden literals; and every statement carries an explicit, pinned `DEFINER` / `SQL SECURITY` clause rather than relying on the server default (note that `SQL SECURITY INVOKER` breaks read-through entirely, so DEFINER is required and must be a deliberate, tested choice). GAMEDATA: measure the definer-rights read-through and the `SHOW VIEW` privilege behaviour on a real connection before the ADR states its claim — the repo has already been burned once by an obviously-true MySQL belief (CLAUDE.md\u0027s closing `SELECT … FOR UPDATE` section). And in ADR 0022/0024\u0027s own text, state the boundary honestly: \"the grant makes every schema but one unreachable; within that schema the boundary is the generated view text, which is machine-generated from the same declaration and asserted in CI.\"",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F04",
        "title":  "AC10\u0027s hash-chain guard goes red on the existing gm/ledger.jsonl, which the same scope says not to migrate",
        "severity":  "major",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[9] (\"every append-only file under `gm/` verifies as a hash chain … each entry\u0027s `seq` is the prior entry\u0027s `seq` plus one and its `prev` equals the SHA-256 of the prior line\u0027s exact bytes, with line 1 carrying `prev: null`\") vs. non_goals (\"Migrating `gm/ledger.jsonl` seq 1 into the new execution log\") and gated_decisions[4] (\"CLOSE IT … Keep the file, keep seq 1, never edit it\")",
        "problem":  "I read `gm/ledger.jsonl`. It holds exactly one line and its keys are seq, sim_date, period, what, staff, proposed, reasoning, precedent, ruling, overridden, overturns. There is no `prev` key. AC10 quantifies over \"every append-only file under `gm/`\", so on the day it lands it fails against the one append-only file that already exists — and the only ways to make it green are to edit seq 1 (the exact retroactive edit the request exists to make impossible) or to weaken the guard by hand after it goes red, which the repo\u0027s own phrasing at first-sight Phase 10 calls out: a guard loosened until it passes is not a guard.",
        "proposed_fix":  "Scope the quantifier explicitly and in the AC text: \"every file listed in a tracked `CHAINED_FILES` constant — `gm/journal.jsonl` and `gm/execution-log.jsonl` today — verifies as a hash chain\", plus a second assertion that `gm/ledger.jsonl` is present, unchanged in line count, and explicitly excluded with its exclusion reason recorded in `gm/README.md`. Keep the tampered-middle-entry red fixture. Also state in the AC what `prev`\u0027s input bytes are — the prior line including or excluding its trailing newline, and whether the line is the serialized JSON as written or a canonical re-serialization — because two implementations will disagree and the chain is worthless if the verifier and the lander normalize differently.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F05",
        "title":  "The write-grant non-goal closes the request\u0027s Open Question 2 on unverified prose, while the twin question gets a spike",
        "severity":  "major",
        "confidence":  "high",
        "category":  "framing",
        "location":  "non_goals[0] (\"A `Write` or `Edit` grant for the GM at any path scope\") vs. tiered_scope.core \"PHASE B GATE — THE TOOL-CHANNEL SPIKE\"; FEATURE_REQUEST.md:222-226 (\"Related: can the harness scope a write grant by path at all?\"); `.claude/agents/README.md:104-113`",
        "problem":  "The scope treats `.claude/agents/README.md:104` (\"This harness has no path-level permission system\") as a measured refutation of the write grant, and simultaneously treats the absence of `.mcp.json`/`settings.json` as merely `unconfirmed` for the query tool — spiking one and foreclosing the other on the same class of evidence. Two problems. First, that README line is repo prose with no epistemic label and no test behind it, and the very next paragraph (`:109-113`) says a harness permission layer DOES sit underneath the tool grant and can deny a write the definition allows — which is a deny-side path mechanism the scope never engages with, in a repo that has never created a `settings.json` to try. Second, the request asks the question directly and the scope answers it \"no\" without doing the hour of work it is willing to spend on the sibling question. Even where I agree with the destination — the umpire-side lander is the better design — the argument in the ADR record will be built on an unverified claim, in a request whose whole thesis is that unverified prose enforcement failed.",
        "proposed_fix":  "Fold the write half into the same one-hour spike: create a throwaway `.claude/settings.json` with a deny rule outside `gm/`, spawn a Write-granted agent, and record measured/refuted with a label in the request\u0027s `reviews/` trail. Then argue the lander on its own merits, which stand regardless of the outcome and are the stronger argument anyway: append-only is mechanically true only when the sole writer is code that can only append, and a hash chain has a single legitimate allocator. Rewrite the non-goal\u0027s justification to lead with that, and demote the harness claim to a supporting note carrying whatever label the spike returns.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F06",
        "title":  "AC4 is provably vacuous — column_disposition already applies the same fragments to column names",
        "severity":  "major",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[3] (\"no emitted view SQL string contains any fragment in `contracts.policy.WITHHELD_NAME_FRAGMENTS`\"); `src/ootp_ai/contracts/policy.py:180` (`if _name_is_withheld(column.name): return Disposition.WITHHELD`); `policy.py:80-82`",
        "problem":  "The emitter selects exactly the columns where `column_disposition` returns RENDERABLE, and `column_disposition`\u0027s FIRST branch withholds any column whose name contains `prone_`, `players_value` or `_talent_`. So no emitted SELECT list can ever contain a fragment-bearing column name — the AC passes on every possible input, including a broken emitter, as long as the emitter filters at all. That is exactly the failure `policy.py:81` documents about the earlier `talent_` form: \"the leading form matched nothing at all, which is a guard that passes by never firing.\" Shipping a second instance of the named anti-pattern inside the acceptance set for a request about enforcement is a bad look, and it also means goals[2]\u0027s \"backed by the `WITHHELD_NAME_FRAGMENTS` text-level backstop over the emitted SQL\" claims protection that does not exist.",
        "proposed_fix":  "Point the backstop at the surface `column_disposition` cannot see, which is the surface the core scope creates: emitted ALIASES and derived EXPRESSIONS — the resolved name column joined from `bronze_name`, the `real_sim_date__unconfirmed` alias if that ruling is taken, any `_history` view, and the `withheld_columns` / `data_dictionary` folds. Assert the fragments against the full generated statement text INCLUDING those, and make the test non-vacuous by mutation: a companion test that removes the disposition filter from a synthetic emitter and asserts the fragment check goes red. If neither is wanted, delete AC4 and remove the backstop claim from goals[2] rather than keeping a criterion that cannot fail.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F07",
        "title":  "\"ADR 0012\u0027s posture becomes STRICTLY STRONGER\" is false as a total-surface claim and will be cited as tested",
        "severity":  "major",
        "confidence":  "high",
        "category":  "framing",
        "location":  "goals[2] (\"Make ADR 0012\u0027s withhold-by-default posture STRICTLY STRONGER at the handover, not merely preserved\"); problem_restatement (\"0012 … untouched with 0012\u0027s enforcement getting *stronger*\"); FRONT_OFFICE.md:67-72 and `.claude/agents/gm.md:47-49`",
        "problem":  "Today the GM holds `tools: Read, Glob` and no database reaches it at all — a strictly smaller reachable surface than any grant. After Phase B it holds SELECT on a schema. The enforcement MECHANISM for the columns it may read improves (a function decides instead of a paragraph); the TOTAL surface grows from zero to one schema, and the failure mode changes from \"the GM asks for something and is refused\" to \"the GM reads a mislabelled column with no error surfaced\" — which CLAUDE.md names as the project\u0027s most dangerous correctness trap and which the scope\u0027s own risks[4] concedes the wall does not improve. \"Strictly stronger\" is the kind of sentence that gets quoted back three ADRs later as though it had been measured, in a repo whose 0016 already carries a blockquote correcting exactly this species of overclaim (`0016:6-11`: \"it is prose, not prevention … That stopped being true\").",
        "proposed_fix":  "Reword to what is true and testable: \"the enforcement point for a withheld column moves from a report author\u0027s compliance to a generated schema, and the same fail-closed function decides both — while the GM\u0027s reachable data surface grows from nothing to one filtered schema, and the classification the boundary depends on remains hand-maintained.\" Put the second clause in ADR 0022/0024\u0027s Costs section, where `tests/test_repo_structure.py::test_every_adr_records_its_cost` will at least confirm a Costs section exists. Pair it with the measured fact the scope already has: 10 `rating-true` fields, all unclassified byte spans, zero `rating-scouted`, one withheld landed column.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F08",
        "title":  "The request\u0027s \"revisable plan\" outcome is delivered by no goal, no core item and no acceptance criterion",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "FEATURE_REQUEST.md:86-88 (\"**The plan is revisable and the revisions are the artifact.**\") and :114 (\"a mutable `plan.md`\") vs. gated_decisions[6] (\"DO NOT ADD `plan.md`\"); `gm/charter.md:10-15`",
        "problem":  "Pain 3 in the request is \"The GM cannot write, so it cannot plan\", and one of the five \"Done looks like\" bullets is the revisable plan. The scope\u0027s answer is gated decision 7: don\u0027t add `plan.md`, `gm/charter.md` already does that job. But I read charter.md — it is club-scoped, explicitly \"Status: unwritten\", a template, and describes standing goals and philosophy, not a plan toward the owner\u0027s multi-year goals with dated revisions. Meanwhile writing the charter is itself pushed to `gated`, and \"Writing the GM\u0027s baseball content — the competitive window, the first plan\" is a non-goal. Net: the scope routes the request\u0027s plan requirement to an artifact that does not exist, is not in core scope to create, and would not be the same thing if it did. Zero of the seventeen acceptance criteria touch plan revision. The trigger/journal machinery gives the GM a memory but not a horizon, which was the pain.",
        "proposed_fix":  "Make the disposition explicit rather than implied. Either (a) fold plan entries into the journal envelope as a fourth `kind` — `plan`, with the current plan derived as the latest `plan` entry, each carrying a mandatory `supersedes` seq and a `why_changed` body, which costs one enum value and no new file and gives a testable AC (\"the derived current plan equals the latest `plan` entry; every `plan` entry after the first carries a non-empty `why_changed` and a resolvable `supersedes`\"); or (b) state plainly in the scope and in ADR 0023 that the revisable plan is DEFERRED, that pain 3 is only two-thirds addressed in this slice, and which request will carry it. What is not acceptable is the current state, where the request\u0027s own stated outcome quietly evaporates into a gated question about a file that is empty.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F09",
        "title":  "OOTP player data in world-readable gm/ is identified as a new hole and assigned to nobody",
        "severity":  "major",
        "confidence":  "high",
        "category":  "risk",
        "location":  "risks[11] (\"TRACKED, PUBLIC GM MEMORY MEETS A QUERY TOOL\"); gated_decisions[7] (the citation rule); non_goals last item (\"Fixing `tests/test_no_leaks.py`\u0027s general credential coverage — the `secret-scanning` request owns that\"); `requests/feature-requests/README.md:122`",
        "problem":  "The scope correctly discovers a vector the request never names: a GM that can both query and write can put OOTP roster rows into `gm/journal.jsonl`, which ADR 0011\u0027s carve-out makes tracked and ADR 0006 makes world-readable forever — while first-sight deliberately routes every rendered roster to a gitignored root (`.env.example`: \"MUST be git-ignored: a rendered roster is OOTP\u0027s player data and this repo is public\"). The mitigation lives only in gated_decisions[7] as a recommendation. It appears in no goal, no core item and no acceptance criterion; and the non-goal hands leak coverage to `secret-scanning`, whose Index row at `requests/feature-requests/README.md:122` scopes it to \"a token, key or connection string\" — credentials, not game data. So the one hard constraint the request lists as non-negotiable (\"The repo is public (0006)\") is protected, for the new vector this request creates, by nothing at all.",
        "proposed_fix":  "Promote the citation rule from a gated recommendation into core, with an acceptance criterion of its own: every `gm/*.jsonl` line\u0027s envelope permits a `cites` field carrying a `(save_id, sim_date, ingest_seq)` triple and a view name, and the lander REFUSES an entry body matching a player-data shape — at minimum, a run of pipe-delimited or comma-delimited rows, or any line containing a value that resolves to a `bronze_player.player_id` in the configured save. Ship it as a positive-and-negative test (a citing entry lands; a pasted result set is refused, reported by file and line). If the operator instead wants to allow player rows in `gm/`, that is a written amendment to ADR 0006\u0027s reasoning, which the scope correctly says must not happen by default.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F10",
        "title":  "No acceptance criterion covers the umpire-side lander\u0027s refusal path — the write channel\u0027s only enforcement point",
        "severity":  "major",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "tiered_scope.core \"PHASE A — the write mechanism, RESHAPED\" (\"a typed lander under `src/ootp_ai/` validates the envelope and appends\"); acceptance_criteria[9] through [12]",
        "problem":  "The reshape\u0027s central concession is to replace a Write grant with a typed lander, on the argument that \"the sole writer is code that can only append\" — which makes the lander the entire enforcement surface for GM authorship. Four criteria then test the FILES (hash chain, trigger round-trip, no self-resolution, per-line envelope validation) and none tests the LANDER. Every one of those file-level checks passes on a file the lander never touched, and none of them exercises the path where a GM return contains a malformed block, an entry claiming `author: \"umpire\"`, a `resolution` co-authored with its `claim`, a `seq` that skips, a `prev` that does not chain, a duplicate `seq`, or two entries landed concurrently. The no-self-resolution rule in AC12 is asserted over the file, so a GM that emits an umpire-authored resolution is caught only if someone later runs the guard — after the record is already written and, by the request\u0027s own rule, unrevisable.",
        "proposed_fix":  "Add one offline criterion enumerating the lander\u0027s refusals, each by name and each with a positive counterpart: a well-formed GM block appends exactly one line and advances the chain; and the lander refuses, without writing anything, an entry with an unknown key, a missing required key, `author: \"umpire\"` on a GM-emitted entry, a `resolution` in the same block as its `claim`, a `seq` that is not prior+1, a `prev` that does not match, and a body over a declared size cap. Assert atomicity explicitly — a refused block leaves the file byte-identical — because a partial append breaks the chain permanently and there is no legal repair under append-only. Also state the concurrency posture: the chain is the collision detector (the scope says this in risks[8]) so the lander must verify the tail immediately before appending, not at load time.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F11",
        "title":  "AC12 asserts over `claim` and `resolution` as entry fields; the declared journal envelope has no such fields",
        "severity":  "major",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[11] (\"no journal entry carries both a `claim` and a `resolution`, with every entry bearing a `resolution` carrying `author: \\\"umpire\\\"`\") vs. tiered_scope.core \"PHASE A — the journal, ONE file\" (envelope: `seq`, `prev`, `sim_date`, `author`, `kind` in {note, trigger, claim, resolution}, `subject`, `resolve_by`, `refers_to`, `body`)",
        "problem":  "In the declared envelope, `claim` and `resolution` are VALUES of `kind`, not keys. An entry therefore cannot \"carry both a claim and a resolution\" — the condition the AC forbids is already impossible, so half the criterion is vacuous, and the other half (\"every entry bearing a `resolution`\") does not parse against the schema at all. This matters beyond wording because AC12 is the mechanical half of the ADR 0015 survival — the guarantee that the GM cannot grade its own homework — and it is currently written against a schema that does not exist. An implementer will guess, and the likely guess (test `kind`) does not actually catch the failure: the real failure is a `kind: resolution` entry whose `author` is `gm`, or a resolution landed in the same lander call as its claim.",
        "proposed_fix":  "Restate against the declared envelope: every entry with `kind == \"resolution\"` has `author == \"umpire\"` and a `refers_to` that resolves to an earlier entry with `kind == \"claim\"`; no entry with `kind == \"claim\"` has `author == \"umpire\"`; no claim and its resolution share a lander invocation (assert via a landed-at ordering field or by rejecting a block containing both); and the assembler exits non-zero naming the `seq` when a `kind == \"trigger\"` entry whose `resolve_by` has passed has no later entry referring to it. Then add the accepted cost the scope already identified in risks[13] — a GM that only pre-registers claims it expects to win is not catchable by any of this — to ADR 0023\u0027s Costs rather than leaving the impression AC12 covers it.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F12",
        "title":  "The doc guard under-covers the retired surface, and its Status-line pattern does not match the repo\u0027s actual supersession format",
        "severity":  "major",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[13]; `FRONT_OFFICE.md:31`, `:47-65`, `:67-91`, `:93-111`; `.claude/agents/gm.md:47-49`, `:51-52`, `:120-122`; `gm/README.md:81-121`; `gm/standing-orders.md` (## Reports); `docs/decisions/0010-main-thread-is-the-gm.md:3`",
        "problem":  "Two defects. (a) Coverage: the guard forbids three phrases — \"6 actions per in-season week\", \"commissioning a report costs an action\", \"you read reports, never the warehouse\". I read the four files it covers and the retired surface is much larger: `FRONT_OFFICE.md:31`\u0027s \"Pause time | ADR 0013 — attention is budgeted\" table row; \"10 per offseason week\" at `:49-50`; `## What you are allowed to see`\u0027s \"you hold no shell and no database tool\" at `:69-70`; the `## Decisions already made` bullet for 0017 at `:95-98` (\"You never spawn, never query, never write to `gm/`\") and the 0014 bullet at `:105-107`, neither of which the scope\u0027s rewrite list even names — it says \"the two retired bullets\" when four are affected; `.claude/agents/gm.md:47-49` (\"You hold no shell and no database access\"), `:51-52` (\"You cannot write\"), `:120-122` (\"Never query a database…\", \"Never write to `gm/`\"); `gm/README.md:81-121`\u0027s entire \"What a period is\" section, which the scope\u0027s core calls vestigial but the guard never checks; and `CLAUDE.md`\u0027s 0016 line, which the rewrite list names but the guard omits. A negative-phrase guard over a subset is also trivially satisfiable by rewording. (b) Format: the AC expects `**Status:** Superseded by \u003cn\u003e`, but the repo\u0027s one existing example is `docs/decisions/0010-main-thread-is-the-gm.md:3` — `**Status:** **Superseded by [0017](0017-gm-is-a-subagent.md)**`, nested bold around a Markdown link. A literal match fails on the repo\u0027s own convention.",
        "proposed_fix":  "Make the guard positive and exhaustive rather than a phrase blacklist: assert that each rewritten file contains the NEW governing statement (by a stable marker string the rewrite introduces) and that the specific retired constructs are gone, enumerated per file with the line ranges above — including `gm/README.md`\u0027s period section and `CLAUDE.md`\u0027s 0016 line. For the ADR half, parse the Status line with a regex tolerant of the repo\u0027s actual form (`\\*{0,2}Status:\\*{0,2}\\s*\\*{0,2}Superseded by \\[?(\\d{4})`) and cross-check the captured number against `docs/decisions/README.md`\u0027s table row for the same ADR, which is the drift the AC is actually aimed at. Also correct the core scope\u0027s \"the two retired bullets under `## Decisions already made`\" to name all four.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F13",
        "title":  "The cheaper alternative for pains 1 and 2 — amend ADR 0013\u0027s budget shape — is never raised or rejected on the record",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "framing",
        "location":  "problem_restatement; FEATURE_REQUEST.md:26-33 (pains 1 and 2); goals[0]; `docs/decisions/README.md:6-7`",
        "problem":  "The request lists four pains. Pain 3 (no write channel) and pain 4 (the wall is coarser than the machinery) genuinely require new mechanism. Pains 1 and 2 do not: \"adjudication overhead compounds\" and \"a flat weekly budget with expiry is the wrong shape for a bursty season\" are both complaints about 0013\u0027s PARAMETERS — expiry, banking, the per-channel ruling requirement — and both would be substantially addressed by a single amending ADR that lets actions bank, sets a season-shaped budget, and declares information channels free by default. That alternative is nowhere in the merged scope: not in the fit verdict, not in gated decision 1\u0027s framing of proceed-as-written / reshape / drop, not in the ADR plan. Given that this is the largest governance diff in the repo\u0027s history and `docs/decisions/README.md:6-7` says re-litigating settled decisions is the most expensive thing that can happen here, the operator is being asked to accept a four-ADR supersession without the smaller option on the table. The retirement may still be right — the hypothesis argument is the operator\u0027s to hold and needs no empirical justification — but that argument only reaches the attention METAPHOR; it does not by itself argue that pains 1 and 2 need retirement rather than repair.",
        "proposed_fix":  "Add the alternative to gated decision 1 as a named fourth option (\"amend 0013 rather than retire it: banking, a season-shaped budget, information-free-by-default\") and reject it on the record with the reason. The strongest available reason is already in the scope\u0027s own material and should be stated: the operator\u0027s hypothesis makes the metaphor itself wrong, so repairing its parameters keeps paying adjudication cost for a simulation nobody wants — and pains 3 and 4 are untouched by any amendment, so the diff is incurred either way. Recording the rejection costs a paragraph and is exactly what the repo\u0027s supersede-never-delete discipline is for.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F14",
        "title":  "gm_view is claimed both to BE ADR 0005\u0027s gold serving layer and NOT to be a transformation layer",
        "severity":  "major",
        "confidence":  "high",
        "category":  "fit",
        "location":  "fit_verdict finding (3) (\"ADR 0005 assigns serving models for the front office to the dbt medallion; `gm_view` IS that layer arriving without dbt\") vs. non_goals (\"Silver or gold medallion layers, or any reshaping transformation in `gm_view` beyond disposition filtering, `save_id` pinning and `max(ingest_seq)` resolution. A view that pivots or conforms is a transformation layer, which is dbt\u0027s job under ADR 0005\"); `docs/decisions/0005-hybrid-data-layer.md:31-33`; `docs/decisions/0004-mysql-warehouse.md:97-98`",
        "problem":  "I verified both citations: 0005:33 does say \"gold (serving models for the front office)\" and 0004 §Notes option 2 is verbatim \"Keep MySQL, drop dbt — hand-rolled SQL plus a thin runner.\" But the scope then holds two incompatible positions. If `gm_view` is the gold layer arriving without dbt, the non-goal disclaiming transformation is a distinction without a difference and the 0004 Notes append is mandatory. If `gm_view` is only a grant boundary — a filtered passthrough — then it is not a serving model at all, there is no 0004/0005 collision, and the append is optional. The scope asserts both, which leaves the implementer to decide how much ADR paperwork this needs. Complicating it: `max(ingest_seq)` resolution IS a semantic transformation — it is what makes the view not 1:1 with bronze — so the non-goal\u0027s own carve-out concedes the point it denies.",
        "proposed_fix":  "Pick the honest reading and write it once. I would take: `gm_view` is a GRANT BOUNDARY with three declared, non-reshaping behaviours (disposition filter, `save_id` pin, latest-seq resolution) and is deliberately NOT the gold layer — no conforming, no pivoting, no cross-table modelling, one view per served table plus the two dictionary folds. Then the 0004 Notes append is still worth making but the trigger is different and should be stated as such: \"a second consumer of hand-rolled SQL landed and dbt was again not pulled\". Also resolve the overlap with first-sight Phase 12 step 4, which already appends a dbt deferral to that same §Notes — say whether this amends that note or adds a second dated one.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F15",
        "title":  "AC1\u0027s unknown-category case and AC3\u0027s fail-loud requirement pull in opposite directions",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[0] (synthetic case (c): \"a column whose category is absent from `policy.KNOWN_CATEGORIES`\") vs. acceptance_criteria[2] (\"the view emitter RAISES … mirroring `warehouse/ddl.py::_check_every_declared_type_is_renderable` and `contracts/policy.py::check_policy_covers`\")",
        "problem":  "AC1(c) requires the emitter to EMIT a view whose SELECT list omits the unknown-category column — i.e. to fall through to `disposition()`\u0027s withhold-by-default branch at `policy.py:108-112`. AC3 requires the emitter to mirror `check_policy_covers`, which RAISES on exactly that input (`policy.py:199-205`). Both cannot hold. I checked: `check_policy_covers` is called from nowhere in `src/` today — only `tests/test_withheld_fields.py:142` — so the choice is genuinely open, and the scope does not make it. I also confirmed the synthetic case is constructible at all: `loader._check_vocabulary` validates a category against the `[vocabulary]` table declared in the same file, so synthetic text can legally declare and use a novel category through `parse_contracts`.",
        "proposed_fix":  "State the emitter\u0027s posture explicitly in the scope: the emitter does NOT call `check_policy_covers` and relies on `disposition()` failing closed, so AC1(c) tests the silent-and-safe path; a SEPARATE criterion asserts that the view-generation ENTRY POINT (the thing `ensure_views()` calls) does call `check_policy_covers` first and raises, which is the loud half `policy.py:196-198` says is the point of having both. That gives two criteria that agree, and it reproduces the exact belt-and-braces `ddl.py:109-111` already uses.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F16",
        "title":  "AC3 has no stated mechanism and Python enums cannot have a member \"introduced\"",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[2] (\"A test that introduces an unhandled disposition asserts the raise\"); `src/ootp_ai/contracts/policy.py:89-95` (`class Disposition(StrEnum)`)",
        "problem":  "`Disposition` is a closed `StrEnum` with three members. A test cannot add a fourth at runtime in any clean way, so \"introduces an unhandled disposition\" has no obvious implementation and an implementer will either skip the criterion or write something that does not test the branch. The criterion is the right idea — it is the guard that makes the UNCERTAIN ruling non-silent — but as written a cold agent cannot execute it.",
        "proposed_fix":  "Name the mechanism in the AC: monkeypatch the emitter module\u0027s reference to `column_disposition` to return a sentinel object that is not a `Disposition` member, call the emitter, and assert it raises with a message naming the offending column and the unrecognised value. Add the companion: with the sentinel replaced by each real member in turn, all three are handled and none falls through to a default branch — so adding a fourth member later cannot be silently absorbed.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F17",
        "title":  "AC7\u0027s save_id clause is tautological against the view\u0027s own baked WHERE predicate, and mislabels ingest_run\u0027s key",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[6] (\"every row\u0027s `save_id` equals the single configured managed save … `COUNT(DISTINCT \u003cdeclared bronze key minus ingest_seq\u003e)`\"); tiered_scope.core PHASE B (\"carries a baked `WHERE save_id = \u003cmanaged\u003e` predicate\")",
        "problem":  "If every view bakes `WHERE save_id = \u003cmanaged\u003e`, then asserting that every returned row carries that `save_id` is a restatement of the predicate — it cannot fail while the predicate is present, and it also cannot detect the predicate\u0027s absence if the warehouse happens to hold only one save. The check is only meaningful because three saves are landed (OOTP-AI, the standard-mode probe, the Challenge twin), and the AC does not say so. Separately, `ingest_run` is one of the eight declared tables and is not a bronze table; \"declared bronze key\" does not describe it (its key is `save_id, sim_date, ingest_seq`, which minus `ingest_seq` is exactly the latest-resolution grain, so the assertion works — but the wording will confuse an implementer enumerating tables).",
        "proposed_fix":  "Make the save_id clause non-vacuous by requiring the fixture warehouse to hold at least two distinct `save_id` values and asserting the view\u0027s row count is strictly less than the underlying table\u0027s for at least one table — proving the filter excludes rather than merely matching. Pair it with an offline assertion that the predicate literal is present in every emitted statement and resolves from the dedicated config key (not `MYSQL_DATABASE`). And change \"declared bronze key\" to \"the table\u0027s declared key\" so `ingest_run` is covered without ambiguity.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F18",
        "title":  "AC8 pins an \"exact expected list\" without saying which phase\u0027s list",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[7]; tiered_scope.core \"PHASE A — the agent-contract guard\" (\"Lands in Phase A even though the grant does not widen until Phase B\"); `.claude/agents/gm.md:4` (`tools: Read, Glob`)",
        "problem":  "The criterion says the `tools:` value \"parses to an exact expected list string-for-string\" and that `Bash`, `Write`, `Edit`, `Task`, `NotebookEdit` are absent by name. It does not say what the expected list IS, and it must be two different things across the two phases: `Read, Glob` in Phase A, `Read, Glob, \u003cquery tool\u003e` in Phase B. Since the whole stated purpose of landing this guard early is to make Phase B\u0027s widening reviewable as a diff, leaving the expected value unstated defeats the purpose — an implementer could write the guard as \"contains Read and Glob\", which would go green on a widened grant.",
        "proposed_fix":  "State both values in the AC: Phase A pins the constant to exactly `Read, Glob`; Phase B\u0027s widening is a one-line change to that constant in the test file, deliberately visible in the PR diff, and the forbidden-name assertions (`Bash`, `Write`, `Edit`, `Task`, `NotebookEdit`) are unchanged across both. Add that the assertion is equality against the parsed list, never membership.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F19",
        "title":  "AC9 inspects a Python signature, but the harness-enforced surface is the tool\u0027s exposed schema",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "acceptance",
        "location":  "acceptance_criteria[8] (\"the query tool\u0027s public entry point exposes no `host`, `user`, `password`, `database` or DSN parameter, asserted by signature inspection\"); gated_decisions[2] (\"a project-scoped read-only tool registered in a tracked `.mcp.json`\")",
        "problem":  "If the vehicle turns out to be an MCP server — the scope\u0027s own recommended outcome — what the GM can pass is the MCP tool\u0027s declared input schema, not the Python function\u0027s signature. A Python entry point with a clean signature can still sit behind a server that forwards arbitrary parameters, and conversely a helper with a `database=` default is harmless if the exposed schema has one `statement` field. The criterion is aimed one layer below the thing it needs to prove. It also carries a reasoning claim worth tightening: \"a credential it can read is a credential it cannot use\" holds only for as long as the GM holds no other tool that can open a socket — true today, and worth stating as a condition rather than a property.",
        "proposed_fix":  "Assert over whichever artifact the spike settles on, and say so conditionally in the AC: if MCP, the tool\u0027s declared input schema has exactly one property (the statement) and no connection-shaped property, read from the tracked `.mcp.json`; if a Python entry point, signature inspection as written. Add the standing condition as a second clause of AC8 rather than a claim in AC9: the GM\u0027s `tools:` list contains no tool capable of opening a network connection other than the named query tool.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F20",
        "title":  "Goals are not tagged by phase, so a failed gate silently invalidates an unmarked subset",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "framing",
        "location":  "goals[0] through goals[10]; tiered_scope.gated[0] (the headline reshape)",
        "problem":  "Eleven goals are listed flat. Four of them (goals[1], [2], [3], [4]) are unreachable if the tool-channel spike fails, and goals[4] is itself the spike. The operator is being asked in gated decision 1 to accept a reshape whose defining property is that a third of the work is conditional, but the goal list does not show which third — so a reader checking \"did we deliver the goals?\" after a failed spike has no way to see that four were never in play. The acceptance criteria have the same problem in reverse: they are labelled OFFLINE / GAMEDATA / USER-RUN, which is the right axis for how they run, but not for whether they exist.",
        "proposed_fix":  "Tag each goal and each acceptance criterion `[A]` or `[B]`, and add one sentence under the fit verdict: \"if the spike fails, goals 2-5 and acceptance criteria 1-7, 9 and 16 do not apply; the request is delivered at Phase A and the ADR record says so.\" This costs nothing and makes the gated decision reviewable as a decision rather than as a mood.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F21",
        "title":  "Nothing reconciles first-sight Phase 12\u0027s 0016-vocabulary standing orders and Phase 13\u0027s retiring-schema ledger row",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "gated_decisions[1] (\"The cost of going second is that Phase 12 writes 0016-shaped standing orders and Phase 13 appends a ledger row in the retiring schema — both cheap to supersede\"); `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1107`; `gm/standing-orders.md` (## Reports)",
        "problem":  "The scope recommends letting first-sight finish first and calls the resulting debris \"cheap to supersede\", but no core item supersedes it and no AC checks that it was. Concretely, first-sight Phase 13 step 3 appends a ledger row in the schema this request closes, and Phase 12 writes report entries into `gm/standing-orders.md` under a `## Reports` block whose text prices commissioning at an action and cites 0016. The doc guard (AC13) would catch Phase 12\u0027s entries only if they happen to repeat one of its three blacklisted phrases, which entries written to a template will not. There is also a live thread the scope names in gated decision 5 and then does not put anywhere: `gm/standing-orders.md`\u0027s `**Established:** ledger seq \u003cn\u003e` convention will point at a file that has stopped growing.",
        "proposed_fix":  "Add a core Phase A item: reconcile the first-sight residue — rewrite the `## Reports` block\u0027s cost language, re-point the `Established:` convention at the execution log (and say what happens to entries already citing a ledger seq), and record in `gm/README.md` that ledger seq rows 1..n are historical doctrine under a retired model. Give it the AC it needs: `gm/standing-orders.md` contains no `Established: ledger seq` reference that does not also resolve in the closed ledger, and every entry created after the cutover cites an execution-log seq.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F22",
        "title":  "Gated decision 2\u0027s justification overclaims what first-sight AC20 measures",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "framing",
        "location":  "gated_decisions[1] (\"Phase 13\u0027s AC20 produces the only measured baseline of what a GM can do under the report wall, against which \u0027scarcity is a confound\u0027 becomes testable rather than argued\"); `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1105`",
        "problem":  "I read AC20. It requires the returned handoff\u0027s `## situation` to name at least five Boston players by real name, each attributed to the report, with no roster fact in `## assumed`. That is a delivery-surface smoke test — it proves a Markdown file reached the agent and the agent cited it. It is not a measurement of decision quality, information throughput, or anything against which \"attention scarcity is a confound\" could be evaluated, and one run of it produces no baseline in any statistical sense. Using it as the decisive third reason for a sequencing recommendation dresses a naming test as an experimental control. The recommendation itself is fine and the other two reasons (Phase 10 is one commit away; the vertical-slice rule) carry it comfortably.",
        "proposed_fix":  "Downgrade the third reason to what it supports: \"AC20 establishes that the report channel works end to end, which is the thing this request converts — converting a channel that has never been exercised would leave two unknowns tangled.\" If the operator actually wants scarcity-as-confound to be testable, that needs a stated before/after measure defined now (queries issued per invocation, distinct facts cited, decisions proposed), which the scope\u0027s own risks[12] already gestures at when it worries the operator may end up more in the loop, not less — and which nothing in the scope currently measures.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F23",
        "title":  "The \"re-runnable citation is stronger than frozen report bytes\" claim fails under CREATE OR REPLACE VIEW",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "framing",
        "location":  "gated_decisions[7] (\"The citation rule is also STRONGER than the report files\u0027 frozen-bytes property it replaces, because append-only bronze makes the citation re-runnable rather than merely archived\"); `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:113`; tiered_scope.core PHASE B (\"`CREATE OR REPLACE VIEW`\")",
        "problem":  "first-sight:113 states the property being replaced precisely: reports are snapshot-partitioned so \"the exact bytes the GM read are still on disk, not regenerated from a warehouse that has since moved on.\" A `(save_id, sim_date, ingest_seq)` citation is re-runnable only if the QUERY and the VIEW DEFINITION are also pinned. The core scope specifies `CREATE OR REPLACE VIEW`, so a view\u0027s column set and semantics can change under a citation with nothing recording it — a disposition flip, a `_history` change, or the UNCERTAIN alias ruling would each silently alter what a re-run returns. The claim as written is not stronger; it is a different property with a new failure mode, and the scope asks for it to be written into ADR 0022 as an improvement.",
        "proposed_fix":  "Either pin the definition — the byte-deterministic committed snapshot of emitted view SQL (already a cheap_fold) becomes the thing a citation implicitly references, with a version or content hash recorded alongside the `(save_id, sim_date, ingest_seq)` triple in the journal envelope — or state the trade honestly in the ADR: the bytes are no longer frozen, the data is, and the view definition\u0027s history lives in git. The first is one extra field on an envelope that is being designed anyway.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F24",
        "title":  "AC13\u0027s prose-grain check requires a doc convention no core item introduces",
        "severity":  "nit",
        "confidence":  "medium",
        "category":  "acceptance",
        "location":  "acceptance_criteria[12] (\"the prose grain sentence in `gm/README.md` resolves to that same key list — the prose-versus-key agreement `contracts/loader.py::_check_grain_matches_key` already enforces for bronze\"); `src/ootp_ai/contracts/loader.py:476-500` and `:577-586` (`GRAIN_PREFIX = \"one row per \"`)",
        "problem":  "The mechanism being borrowed only works because `tables.toml` grain sentences are required to start with the literal `one row per ` and to be composed of tokens declared in `[meta.dimensions]` (`loader.py:65`, `:577-586`). Nothing in `gm/README.md` uses that form today, and the core scope\u0027s doc-rewrite list for `gm/README.md` names layout, the career-vs-club table, the new schemas and the period section — not the adoption of a parseable grain sentence. So the AC depends on a convention that no work item creates.",
        "proposed_fix":  "Add to the `gm/README.md` rewrite item: each new artifact\u0027s section opens with a grain sentence in the `one row per …` form over a small declared dimension vocabulary local to `gm/`, and say where that vocabulary lives. Alternatively, if that is heavier than it is worth for three files, weaken the AC to \"the key list declared for each artifact is stated in `gm/README.md` and matches the envelope\u0027s declared key, compared as sets\" — which gets the anti-drift value without importing the whole grain grammar.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F25",
        "title":  "Citation slip: the anti-speculation quote is at gm/README.md:52, not :51",
        "severity":  "nit",
        "confidence":  "high",
        "category":  "fit",
        "location":  "tiered_scope.core PHASE A journal bullet (\"against `gm/README.md:51`\u0027s own anti-speculation rule\"); above_and_beyond \"Mirror the GM\u0027s own memory into `gm_view`\" (\"`gm/README.md:51`: \\\"don\u0027t build the tenure structure speculatively\\\"\"); actual: `gm/README.md:51-52`",
        "problem":  "Line 51 is \"**The directory does not split until a second club exists.** One employer, one flat\"; the quoted fragment \"don\u0027t build the tenure structure speculatively\" is on line 52. Trivial in isolation, but this scope\u0027s credibility rests on the fact that essentially every other citation I checked resolved exactly (`policy.py:180`, `:82`, `:89-95`; `ops/mysql-bootstrap.sql:63`; `tests/test_bronze_landing.py:763`; `ci.yml:24`; `FRONT_OFFICE.md:31/:47-65/:67-91`; `.gitignore:4`; `gm.md:4`), and a cold implementer who checks one citation and finds it off by one will start distrusting the rest.",
        "proposed_fix":  "Change both occurrences to `gm/README.md:51-52`. While there, note that `docs/decisions/README.md` currently lists 21 rows and the scope\u0027s numbering claim (new ADRs at 0022/0023) is correct — I verified the file count.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F26",
        "title":  "Should Phase B also be gated on the scouted-view spike, given the served surface may hold nothing decision-relevant?",
        "severity":  "question",
        "confidence":  "high",
        "category":  "scope-creep",
        "location":  "risks[3] (\"THERE MAY NEVER BE RATINGS TO SERVE\"); `docs/data-access.md` §5 critical-path task (`unconfirmed` — \"Which file holds which view, and whether the scouted view is stored at all\"); non_goals (\"Landing ratings of any kind\")",
        "problem":  "I confirmed the data-access claim: the critical-path task is still labelled `unconfirmed`, and it names the outright failure — if OOTP computes the scouted view at render time, \"the front office would be able to read the answer key and nothing else.\" Combined with the measured field map (zero `rating-scouted`, 10 unclassified `rating-true` byte spans) and the non-goal against landing ratings, Phase B delivers a carefully-enforced boundary around names, ages, handedness, club assignment, roster-list membership and division structure. The scope names this in risks and then does not let it touch the gating decision, which is gated on the tool channel alone. It is a legitimate answer that the boundary is cheaper to build before the answer key arrives than to retrofit after — but the operator should be choosing that knowingly, alongside the alternative of shipping Phase A now and Phase B after the scouted-view spike returns, when the boundary would have something to guard and the acceptance tests would not need a synthetic planted column to be non-vacuous.",
        "proposed_fix":  "Raise it as an explicit eleventh gated decision with both options priced: (a) Phase B on the tool-channel spike alone, accepting that the wall is prospective and that AC1\u0027s synthetic case is doing all the real work — cheaper now, and the schema boundary exists the day a rating lands; (b) Phase B additionally gated on the scouted-view spike, so the boundary is built against a real withheld population — later, but every acceptance criterion is then non-vacuous over real contracts. Recommend (a) with the reasoning already in the scope, but record the choice rather than inheriting it.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F27",
        "title":  "AC16 buries a machine-checkable clause inside a USER-RUN criterion",
        "severity":  "question",
        "confidence":  "medium",
        "category":  "acceptance",
        "location":  "acceptance_criteria[15] (\"the executed SQL is present in the query log; its returned handoff names the view it read and cites the `(save_id, sim_date, ingest_seq)` triple\"); `requests/feature-requests/README.md:83-85`",
        "problem":  "`requests/feature-requests/README.md:83-85` says human-only criteria must be marked USER-RUN \"so the acceptance panel doesn\u0027t claim them\" — and the scope correctly marks this one. But it bundles three clauses of different kinds: whether the GM answered a baseball question well (judgment, correctly user-run), whether the executed SQL landed in `gm/queries.jsonl` (mechanical), and whether the handoff names its view and cites a triple (mechanically parseable from the returned Markdown against a declared handoff grammar). Bundling means the mechanical clauses only ever get checked when the operator sits down, and the query log — which the scope promotes to core as the replacement denominator for the retired action economy — otherwise has no acceptance criterion at all.",
        "proposed_fix":  "Split it. Keep the judgment clause USER-RUN. Move the two mechanical clauses into an offline criterion over a captured handoff fixture plus a captured query-log fixture: the handoff parses against the declared return grammar, every factual claim in `## situation` carries a citation, every citation names an existing `gm_view` view and a well-formed `(save_id, sim_date, ingest_seq)` triple, and every statement the fixture run executed appears in `gm/queries.jsonl` with its sim date, row count and invocation id. That also gives the query log the coverage its promotion to core implies.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "F28",
        "title":  "The DROP VIEW mutation-scan gap is a cheap_fold, but ensure_views() is the only thing touching MySQL",
        "severity":  "question",
        "confidence":  "high",
        "category":  "scope-creep",
        "location":  "above_and_beyond \"Extend the ADR 0021 mutation scan to cover `DROP VIEW`\" (tier: cheap_fold); `tests/test_bronze_landing.py:763`; tiered_scope.core PHASE B (\"`CREATE OR REPLACE VIEW` … plus `ensure_views()` beside `warehouse/load.py::ensure_tables` as the only thing that touches MySQL\")",
        "problem":  "I confirmed the banned pattern at `tests/test_bronze_landing.py:763` is `DROP\\s+(TABLE|SCHEMA|DATABASE|INDEX|COLUMN)` — `DROP VIEW` passes by omission. The scope files the fix as a cheap fold. But the core scope simultaneously puts the new MySQL-touching code (`ensure_views()`) inside `warehouse/`, which is the package the ADR 0021 mutation scan exists to police, and specifies `CREATE OR REPLACE VIEW` — one editor\u0027s convenience away from a drop-and-recreate. That makes the guard extension a precondition of the core work rather than an optional improvement: the whole point of the scan is that a destructive statement in `warehouse/` becomes a decision rather than a diff, and shipping new destructive-capable code into that package while the guard has a hole in exactly the relevant keyword is the sequencing this repo normally refuses.",
        "proposed_fix":  "Promote it into Phase B core alongside the emitter, as one line in the alternation plus a positive sample in the scan\u0027s own \"still catches real mutations\" fixture set (the pattern `tests/test_bronze_landing.py:843` already uses for `DROP TABLE`). Alternatively house the emitter in a sibling package outside `warehouse/` and record why in the ADR — but then say explicitly that the ADR 0021 scan does not cover it, so the exemption is a decision rather than an accident.",
        "adversary":  "fit-ac"
    },
    {
        "id":  "A2-01",
        "title":  "ADR 0022 is placed in unconditional Phase A while the scope\u0027s own gating argument says it depends on the spike",
        "severity":  "blocker",
        "confidence":  "high",
        "category":  "gating-honesty",
        "location":  "tiered_scope.core item 1 (\"PHASE A — TWO ADRs, numbered 0022 and 0023\") vs gated_decisions[3] rationale",
        "problem":  "Gated decision 4 argues the two-ADR split is a DEPENDENCY split in these words: \"0023 depends on nothing and can ship whatever the spike returns, while 0022\u0027s enforcement claim depends on an unverified harness capability. One ADR holds the cheap two-thirds hostage to the spike.\" The core list then puts BOTH ADRs in \"PHASE A\", which the scope defines as shipping unconditionally. If the spike fails, Phase A has landed an accepted ADR that amends ADR 0017\u0027s no-DB foreclosure into \"a scoped grant\" that does not exist and cannot be built — an ADR describing a capability the repo lacks, in a docs/decisions/ tree whose whole discipline is that a recorded decision is load-bearing. This is the single most important gate in the scope and it is contradicted by the item list two paragraphs away.",
        "proposed_fix":  "Split the ADRs across the phases the dependency argument already draws: 0023 (memory model) lands in Phase A; 0022 (information model) lands in Phase B, gated on the spike. If the operator wants the economy retired unconditionally, split 0022 again — a Phase-A ADR that retires 0013/0018/0019 and supersedes 0016\u0027s report wall with NOTHING but a stated gap, and a Phase-B ADR that installs the schema boundary. Either way, no accepted ADR may assert an enforcement mechanism whose existence is still `unconfirmed`.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-02",
        "title":  "Acceptance criteria are not partitioned by phase, so a Phase-A-only ship has no defined done-ness",
        "severity":  "blocker",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria (18 items, none phase-tagged) vs tiered_scope.core\u0027s Phase A / Phase B split",
        "problem":  "The scope\u0027s headline recommendation is a two-phase build where Phase B may never ship. Six of the eighteen acceptance criteria are pure Phase B (all four GAMEDATA grant/view/grain criteria, the emitter-raises criterion, the WITHHELD_NAME_FRAGMENTS text backstop, the two synthetic/real disposition criteria, the query-tool signature criterion, and the USER-RUN querying-GM criterion). None is labelled. requests/feature-requests/README.md defines testable as \"a cold agent can run one command and get a pass or fail\" — a cold agent handed this scope after a failed spike cannot determine whether the work is done, because more than a third of the criteria are unsatisfiable by construction and nothing says so.",
        "proposed_fix":  "Tag every criterion `[Phase A]` or `[Phase B]`, and state explicitly that Phase A\u0027s acceptance set is complete and sufficient on its own. Add one Phase-A criterion that currently has no analogue: an offline assertion that `.claude/agents/gm.md`\u0027s tools value is UNCHANGED (still exactly `Read, Glob`) when Phase B has not shipped, so the retirement half cannot silently widen the grant.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-03",
        "title":  "Phase A retires the attention denominator unconditionally; its only replacement lives entirely in the gated half",
        "severity":  "blocker",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "tiered_scope.core Phase A (retire 0013/0018/0019) vs Phase B (\"the query log, written by the TOOL\"); above_and_beyond[6] tiered `core`; docs/decisions/0013-action-economy.md:78-81; gm/staff.md:10-20",
        "problem":  "The scope correctly identifies (risk 6, convergence theme 10) that ADR 0013\u0027s load-bearing product was the DENOMINATOR — \"twelve actions on the draft and three busted picks is a return on invested attention\" — and correctly promotes the query log to core as its replacement. But the retirement is Phase A and the query log is Phase B. If the spike fails, the repo ships a state where `gm/staff.md`\u0027s stated reason for existing is dead (\"Under ADR 0013 actions are scarce, and scarcity creates the denominator... Without scarcity, \u0027should I fire the scouting director\u0027 has no evidence behind it\") and nothing has replaced it. The execution log meters EXECUTION, which is not attention, and the scope says so itself. The gating is therefore honest about the query channel and dishonest about the consequence of retiring the economy without one.",
        "proposed_fix":  "Move the denominator obligation into Phase A explicitly: either (a) the Phase-A execution log carries the token/wall-clock fields from gated decision 10 unconditionally rather than as a ride-along, and 0022/0023 states that this is the denominator now; or (b) Phase A rewrites `gm/staff.md` to state plainly that scout-quality attribution has no quantitative denominator until Phase B lands, with the review trigger named. Do not ship a Phase A that deletes a measurement three ADRs depend on and defers the replacement behind a gate.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-04",
        "title":  "`gm/staff.md` is absent from the doc-rewrite list although its entire rationale is ADR 0013 plus 0016",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "gm/staff.md:5-20 (Status blockquote cites ADR 0016; \"## Why this file can exist at all\" cites ADR 0013); tiered_scope.core \"PHASE A — doc rewrites\" enumerates FRONT_OFFICE.md, .claude/agents/gm.md, gm/README.md, gm/standing-orders.md, CLAUDE.md, docs/decisions/README.md",
        "problem":  "`gm/staff.md`\u0027s subtitle is \"how each member has performed against the actions spent on them\"; its format block requires \"**Actions spent:** running count, by period\"; its Status blockquote blames the absence of analytics capability on ADR 0016; and its central section is titled \"Why this file can exist at all\" and is an argument from 0013\u0027s scarcity. Every one of those becomes false or vestigial under this request, and the file is one of five that `tests/test_repo_structure.py::test_gm_contract_files_exist` asserts must exist. The scope\u0027s own doc-guard acceptance criterion checks four files for retired phrases and `gm/staff.md` is not among them, so the retired vocabulary survives in a tracked GM-memory file that the GM reads every invocation (`.claude/agents/gm.md:28`).",
        "proposed_fix":  "Add `gm/staff.md` to the Phase A doc-rewrite list and to the doc-guard acceptance criterion\u0027s file set. Its \"Actions spent\" field and \"Why this file can exist at all\" section need an explicit disposition — either a new denominator (per A2-03) or a written statement that attribution is qualitative until one exists.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-05",
        "title":  "Retiring 0013 invalidates a Buys clause of ADR 0012, which the non-goals forbid touching",
        "severity":  "major",
        "confidence":  "high",
        "category":  "fit",
        "location":  "docs/decisions/0012-scouted-ratings-only.md:41-42; non_goals[1] (\"Any change to ADRs 0012, 0015, 0003, 0001, 0021 or 0006\")",
        "problem":  "ADR 0012\u0027s Consequences/Buys reads: \"Combined with [ADR 0013](0013-action-economy.md), scout quality becomes measurable: actions spent, outcomes returned.\" Superseding 0013 makes that clause false. This repo\u0027s own discipline for exactly this situation is visible at `0016-gm-reads-reports-not-queries.md:6-11` — a blockquote at the top of the affected ADR saying \"The decision below stands unchanged, but its Costs section says X... That stopped being true when Y. The belief is left as written because it is the record of what was believed; this note is the correction.\" The scope declares 0012 untouched AND declares 0012\u0027s enforcement \"strictly stronger\", while leaving an invalidated clause in it. The risk register notices the dependency (risk 6) but the non-goal still forbids the fix.",
        "proposed_fix":  "Carve the exception into the non-goal: 0012\u0027s DECISION is untouched, but 0012 receives a correction blockquote of exactly the 0016:6-11 shape recording that its Buys clause depended on a now-retired economy. Same treatment for 0014:56-59 (\"It makes ADR 0013 pay off further than 0013 anticipated\"), which is inside the ADR already being amended. Add a doc-guard assertion that both blockquotes exist.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-06",
        "title":  "`gm/standing-orders.md`\u0027s rewrite is scoped to the `## Reports` block; the file\u0027s framing and entry format are equally 0013-priced",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "gm/standing-orders.md:3-8 and :20 and :45; tiered_scope.core Phase A doc rewrites (\"`gm/standing-orders.md`: the `## Reports` block that prices commissioning at an action\")",
        "problem":  "The file opens: \"Policies the staff apply for free, every game, until changed. Establishing or changing one costs an action (ADR 0013); applying one costs nothing. This is the mechanic that makes the action economy livable.\" That is lines 3-8, outside the `## Reports` block the scope names. Both entry-format templates require `**Established:** ledger seq \u003cn\u003e`, and gated decision 5 correctly spots that the ledger stops growing — but the core doc-rewrite bullet does not carry that fix, so the two halves of the scope disagree about how much of this file changes. first-sight\u0027s own planning table (IMPLEMENTATION_PLAN.md P8) already treats `gm/standing-orders.md:45` as a live constraint, so a stale `Established:` convention will collide with work in flight.",
        "proposed_fix":  "Widen the bullet to the whole file: the opening framing, both `Established:` templates (re-pointed at the execution log\u0027s seq space), and the `## Reports` block. Note in the same bullet whether standing orders survive at all as a concept — see A2-07.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-07",
        "title":  "Two of ADR 0013\u0027s mechanics — standing orders and the 20-proposal autonomy graduation — are dropped by silence",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "docs/decisions/0013-action-economy.md:34-41 (\"Standing orders are the load-bearing mechanic\") and :69-72 (\"when an action class reaches 20 proposals with zero overrides, it graduates to auto-approved\"); risks[6] names only 0018\u0027s foresight trap and 0019\u0027s insights as needing re-homing",
        "problem":  "The scope\u0027s supersession risk bullet is careful about 0018 and 0019 and silent about 0013\u0027s own non-pricing content. Two mechanics die with it. (1) Standing orders: 0013 calls them \"the load-bearing mechanic\" and identifies the failure mode the repo cares most about — \"a standing order that quietly stops being right\" — which `gm/standing-orders.md:56-65` builds its `Review trigger` discipline on. Under a retired economy, does a standing order still exist as an instrument, and does changing one still require anything? (2) The autonomy graduation rule is the ONLY mechanism in the repo by which the GM earns increased autonomy on a measured signal rather than a feeling; the new model has proposal dispositions but no graduation. Neither is named in goals, non-goals, core, or risks.",
        "proposed_fix":  "Give each an explicit written disposition in 0022: standing orders survive as an instrument with their `Review trigger` discipline intact and no price (recommended — the failure mode is orthogonal to scarcity), and the graduation rule either re-homes onto the execution log\u0027s disposition history or is recorded as deliberately discarded with the reason. Add both to the doc-guard acceptance criterion so a supersession that drops them turns red.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-08",
        "title":  "Baking `save_id` (and a source schema) into every view breaks the pure-emitter property and the byte-determinism fold it is scoped beside",
        "severity":  "major",
        "confidence":  "high",
        "category":  "scope-creep",
        "location":  "above_and_beyond[3] (\"Pin every GM view to the managed `save_id`\", tier core); tiered_scope.core Phase B (\"carries a baked `WHERE save_id = \u003cmanaged\u003e` predicate\"); tiered_scope.cheap_folds[5] (byte-deterministic committed view SQL asserted in CI); src/ootp_ai/warehouse/ddl.py:8-10; src/ootp_ai/config.py:1-15; .env.example (`MYSQL_DATABASE=ootp_dev`)",
        "problem":  "Three scope items are mutually incompatible and the scope treats all three as settled. `ddl.py` is praised — correctly — because \"Nothing in this module connects to anything. It turns a `Contracts` into strings\", which is what lets its entire guard suite run in CI. A view emitter that bakes `WHERE save_id = \u0027\u003cmanaged\u003e\u0027` must call `config.load_settings()`, whose `_required(values, \"OOTP_LEAGUE\")` raises with no `.env` — and CI has none by design (`config.py:8-10`: \"CI has no `.env`, no game and no MySQL\"). The same applies to schema qualification: a view in `gm_view` selecting from bronze must name the source schema, and `MYSQL_DATABASE` is env-resolved and defaults to `ootp_dev` in `.env.example`. So the emitted SQL is machine-dependent, and a committed byte-identical snapshot asserted in CI cannot exist. The scope promotes the save_id pin to core on a genuinely good argument and never notices it costs the property it praises.",
        "proposed_fix":  "Separate the pure text from the bound text. The emitter stays pure over `(Contracts, disposition)` and emits views with the save-id predicate and schema name as declared placeholders; a thin binder resolves them at `ensure_views()` time from settings. Commit and byte-assert the PLACEHOLDER form in CI; assert the BOUND form against `information_schema` under `-m gamedata`. State in the scope which artifact each acceptance criterion refers to, because \u0027the emitted view SQL\u0027 now means two different strings.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-09",
        "title":  "The advisor roster\u0027s fate is never stated, although both 0016 and 0017 hinge on it",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "completeness",
        "location":  "docs/decisions/0016-gm-reads-reports-not-queries.md:78-80 (\"ADR 0010\u0027s role split becomes real rather than aspirational. Advisors that the GM routinely bypasses are decoration\"); docs/decisions/0017-gm-is-a-subagent.md:58-74 (advisors are the party that may touch the warehouse; the two-staffs table prices repo agents in \"Actions only\"); FRONT_OFFICE.md:11-15 and :62-63",
        "problem":  "Under 0017, advisors are the ONLY entity permitted to query, they are what the GM commissions, and repo agents cost actions. This request gives the GM the query channel and abolishes the currency. That leaves the advisor roster with no exclusive capability and no price — precisely the \"decoration\" outcome 0016 named as the thing it existed to prevent. The scope\u0027s non-goals say only \"Building analytics, models, advisors or reports FOR the GM... Directing that becomes the GM\u0027s job\", which is a statement about who directs, not about whether advisors remain an instrument. `FRONT_OFFICE.md:11-15` describes the roster in its opening paragraph and :62-63 (\"Advisors have domains... That is why you cannot commission one omniscient analyst — not price, expertise\") sits inside the action-economy section slated for deletion, so a live ADR-0017 property gets deleted as collateral.",
        "proposed_fix":  "0022 must state whether advisors survive and as what. Recommended: they survive as JUDGMENT (a spawned specialist reasoning in its domain), not as a data-access channel, and 0017\u0027s two-staffs table\u0027s repo-agent row reprices from \"Actions only\" to free-but-logged. Preserve the \u0027advisors have domains, and the limit is expertise not price\u0027 clause by relocating it out of the deleted section rather than losing it.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-10",
        "title":  "No non-goal, risk, or rule constrains post-hoc query fishing — the direct analogue of the retroactive labelling 0013 forecloses",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "goals[7] and non_goals (preserve \"declare before doing\" for execution only); docs/decisions/0013-action-economy.md:100-103 (\"Forecloses: Retroactive labelling. Declare the action, then do the work\"); risks[13] covers only the plan-as-second-scorecard variant",
        "problem":  "Under 0013+0016 the GM declared what information it wanted BEFORE receiving it, and an author stood between the question and the number. Both go. Information is now free, unlimited and self-served, so the GM can issue queries until one supports a conclusion and then write the journal entry. The scope preserves \"declare before doing\" only for execution, and its one nearby risk (\"a GM that only pre-registers claims it expects to win\") is about claim selection, not about querying after the conclusion is formed. This is the same failure shape 0013 explicitly forecloses, arriving through the door this request opens, and it is not named anywhere in the scope.",
        "proposed_fix":  "Add it as a named risk AND give it the one mechanical grip available: the query log (already core) is timestamped and per-invocation, so a Phase-B acceptance criterion can assert that every journal entry citing a number names a query present in `gm/queries.jsonl` for the SAME invocation. Then state plainly in 0022 that ordering WITHIN an invocation is not observable and is an accepted cost — rather than leaving the gap unnamed.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-11",
        "title":  "`gm_view`\u0027s five dataset contracts are never settled as a block; coverage and update semantics are simply absent",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "requests/feature-requests/README.md:39-56 (grain / keys / coverage / update semantics / data-layer pattern, \"before any code\"); scope settles grain and keys inside acceptance_criteria[6] and the pattern inside grounding_pointers[11], and settles neither coverage nor update semantics anywhere",
        "problem":  "The pipeline contract this scope must satisfy requires five contracts stated as decisions, not scattered through criteria. Two are missing outright. COVERAGE matters acutely here and the scope\u0027s own risk register proves it: `bronze_team_roster` is one row per player per team per list (Boston resolves to 33/26/30/7 for a ~40-man org, README.md:194), roughly 10,700 of 18,072 players carry no roster row, `bronze_name` is 264,095 entries, and `bronze_field_label` describes only what had landed the day it landed. A SQL-writing agent handed views with no served coverage statement will produce confidently wrong aggregates — the scope names the risk and then does not turn it into a contract. UPDATE SEMANTICS is equally unstated: bronze is append-only but a view is `CREATE OR REPLACE`, so the served surface is RESTATED while the data beneath it is appended. Nothing says so, and the frozen-bytes property the reports had (see A2-19) depends on it.",
        "proposed_fix":  "Add a Data Contracts block to the scope that states, per served view: grain (one row per \u003cwhat\u003e per (save_id, sim_date) at max(ingest_seq)), key, coverage (which populations carry rows and which are structurally absent, sourced from the catalog rather than restated), update semantics (bronze append-only; view definitions restated on redeploy, with the committed SQL snapshot as the history), and the ADR 0005 placement already argued. Add an acceptance criterion that every emitted view\u0027s coverage statement is served — the `data_dictionary`/`withheld_columns` folds are the natural home.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-12",
        "title":  "The live-schema conformance test is the only guard against a hand-created definer view over `ootp_truth_real`, and it is filed as an optional cheap fold",
        "severity":  "major",
        "confidence":  "high",
        "category":  "risk",
        "location":  "tiered_scope.cheap_folds[6] (live-schema conformance test, `-m gamedata`); risks[15] (view privilege semantics `assumed`); ops/mysql-bootstrap.sql:57-63",
        "problem":  "MySQL views run with DEFINER rights by default — that is the mechanism by which `gm_reader`, holding SELECT on `gm_view` and nothing else, reads through to bronze. The same mechanism means ANY view placed in `gm_view` by the definer account reads through to whatever the definer can reach, and the definer (`ootp_ai@localhost`) holds ALL PRIVILEGES on `ootp_truth_real` — the answer key. The GRANT therefore does not prevent the answer key reaching the GM; the only thing preventing it is that no such view exists, and the only thing that would NOTICE one is the conformance test the scope files as optional. Every other enforcement claim in the scope is stated as structural; this one is the actual load-bearing lock and it is discretionary.",
        "proposed_fix":  "Promote the live-schema conformance test to core Phase B and widen it: it must assert not only that `gm_view`\u0027s column set equals `column_disposition` over `load_contracts()`, but that no view in `gm_view` references any schema other than the single configured warehouse schema (parse `information_schema.views.view_definition`). Additionally require the emitter to create views with `SQL SECURITY DEFINER` explicitly and record the privilege semantics as `verified` by that test rather than `assumed`.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-13",
        "title":  "The `_history` sibling per view is not a cheap fold and is speculative at one landed sim date",
        "severity":  "major",
        "confidence":  "high",
        "category":  "scope-creep",
        "location":  "tiered_scope.cheap_folds[2]; above_and_beyond[2] (\"The `_history` sibling is the cheap-fold half\"); gm/README.md:51-52 (\"don\u0027t build the tenure structure speculatively\")",
        "problem":  "A `_history` sibling per view doubles the emitted view set, the GRANT set, the grain acceptance criterion\u0027s iteration, the committed byte-identical SQL snapshot, and the live-schema conformance diff. The warehouse currently holds ONE sim date (2024-03-07) per save, so a history view returns exactly what the latest-resolving view returns — the capability is unexercisable and untestable in any interesting way. Its stated justification is \"retention is free under 0018\u0027s reasoning\", which argues for KEEPING the rows (already true, bronze is append-only) rather than for serving a second view over them. The scope elsewhere applies exactly the right standard to the same shape of idea — it drops the `gm/` memory mirror as \"premature by the repo\u0027s own standard\" citing gm/README.md:51 — and does not apply it here.",
        "proposed_fix":  "Move to `gated` or `drop`. The right to look back is preserved by the underlying tables and by the cookbook\u0027s \u0027diff two seqs of one sim date\u0027 worked example, which the scope already funds. Revisit when a second sim date has landed and a GM has actually wanted the history.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-14",
        "title":  "Most of Phase A is in the `data-engineer` builder\u0027s deny set, and the scope never names the authorship split",
        "severity":  "major",
        "confidence":  "high",
        "category":  "completeness",
        "location":  ".claude/agents/data-engineer.md:154-165 (deny set: `tests/`, `.github/`, `ops/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md`, `docs/decisions/`); compare requests/feature-requests/README.md:119 which records for first-sight that \"`tests/` is main-thread-authored because it is in the builder\u0027s deny set\"",
        "problem":  "Six of the core Phase A items land inside the builder\u0027s repo-level deny set: two ADRs and the `docs/decisions/README.md` status table (`docs/decisions/`), every new and extended guard (`tests/test_gm_memory.py`, `tests/test_agent_contract.py`, `tests/test_gm_view.py`, `tests/test_gm_grant.py`), the `gm.md` rewrite (`.claude/`), the `CLAUDE.md` line, and the `gm_reader` grant (`ops/mysql-bootstrap.sql`). The builder is instructed to \"stop and report it\" if spec targets fall inside the deny set. first-sight\u0027s Index row records this constraint explicitly for its own build; this scope does not, which will surface as a mid-build stop rather than as a planning input — and it materially changes the effort shape, because the main thread authors the majority of the diff.",
        "proposed_fix":  "Add an explicit authorship note to the scope: which core items are builder-eligible (`src/ootp_ai/` modules, `gm/` artifacts, `FRONT_OFFICE.md`) and which are main-thread-only. This is a scoping-stage fact about how the work is shaped, not an implementation detail, and its absence is what would let a plan assign the whole thing to one agent.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-15",
        "title":  "`gm/` is not in the builder\u0027s deny set — a hash-chained append-only `gm/` needs it to be",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "risk",
        "location":  ".claude/agents/data-engineer.md:146-165 (allowlist and deny set; `gm/` appears in neither); tiered_scope.core Phase A (hash-chained journal, execution log, umpire-side lander)",
        "problem":  "The write-capable builder\u0027s deny set names `tests/`, `.github/`, `ops/`, `.claude/`, `CLAUDE.md`, `docs/data-access.md` and `docs/decisions/`. `gm/` is absent, so a builder given a spec whose target paths include `gm/` may write there. Today that is nearly harmless — `gm/` holds one ledger line and some templates. After this request it holds a hash chain whose integrity is the mechanism delivering the request\u0027s literal promise (\"tamper-evident\"), and whose only writer is supposed to be the typed lander. A builder appending or reformatting a line breaks the chain, and the acceptance criterion that catches it will fire long after the fact and name the wrong culprit.",
        "proposed_fix":  "Add `gm/` to the builder\u0027s repo-level deny set in Phase A, in the same commit as the chain, with the reason stated (the sole appender is the lander). Extend `tests/test_agent_contract.py`\u0027s rulebook-invariant guard to assert the `gm/` deny line survives — the same guard shape that already protects `tests/` and `.claude/`.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-16",
        "title":  "An acceptance criterion requires `test_no_leaks.py` to catch a credential shape that its own non-goal assigns to the `secret-scanning` request",
        "severity":  "major",
        "confidence":  "high",
        "category":  "acceptance",
        "location":  "acceptance_criteria[14] (\"a positive sample added to `test_patterns_still_catch_real_leaks` proving the guard catches the new `.env` key shape\") vs non_goals[14] (\"Fixing `tests/test_no_leaks.py`\u0027s general credential coverage — the `secret-scanning` request owns that\"); tests/test_no_leaks.py:37-41",
        "problem":  "`test_no_leaks.py`\u0027s PATTERNS list holds exactly three regexes: Windows drive path, unix home path, email address. A new `.env` key such as `MYSQL_GM_PASSWORD=` matches none of them, and no pattern in the file resembles a credential. Satisfying the acceptance criterion therefore REQUIRES adding a credential pattern — which is precisely the coverage the non-goal hands to the `secret-scanning` request (requests/feature-requests/README.md:122 records that request\u0027s whole premise as \"a token, key or connection string passes untouched\"). One of the two must give. As written, the acceptance panel will either fail the criterion or approve scope the non-goal forbids.",
        "proposed_fix":  "Rewrite the criterion to what is actually in scope and actually testable: `.env.example` gains the new keys with EMPTY values, and `test_no_leaks.py` runs green over the new `.jsonl` artifacts (already in its keep set at :85-98) with no new pattern added. Add the credential-pattern need as a written input to the `secret-scanning` request instead — the same \u0027explicit disposition for pinned work\u0027 treatment the scope already gives `gm-inbox` and `news-subscription-dial`.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-17",
        "title":  "Two contradictory homes for the GM grant — schema-level in bootstrap.sql and per-view emitted from the declaration",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "scope-creep",
        "location":  "tiered_scope.core Phase B (\"`ops/mysql-bootstrap.sql` gains a restricted `gm_reader`@localhost with SELECT on `gm_view.*`\") vs tiered_scope.cheap_folds[3] (\"Emit the `GRANT SELECT ON gm_view.\u003cview\u003e` statements from the same declaration... and assert the applied grants match the emitted set\")",
        "problem":  "A schema-level `GRANT SELECT ON gm_view.*` and a generated set of per-view `GRANT SELECT ON gm_view.\u003cview\u003e` are alternatives, not complements. If the schema-level grant is applied, `mysql.tables_priv` holds no per-view rows and the fold\u0027s assertion (\"applied grants match the emitted set\") fails against a correctly configured warehouse — the most expensive kind of wrong test, because it sends the next agent hunting a bug in working code. If instead only per-view grants are applied, the tracked bootstrap file no longer describes the GM\u0027s actual access, breaking the property the scope praises it for (`ops/mysql-bootstrap.sql` is \"the tracked, public home for database-scoped grants\"). The fold\u0027s own justification — that a hand-maintained grant list drifts from a generated view set — is only true under the per-view model.",
        "proposed_fix":  "Pick one and say so. Recommended: schema-level `GRANT SELECT ON gm_view.*` in `ops/mysql-bootstrap.sql` (simpler, cannot drift open when a view is added, and the live-schema conformance test of A2-12 is what actually bounds what is IN the schema), and drop the per-view GRANT emission fold entirely. If the operator prefers per-view, remove the schema-level grant from bootstrap and say that the emitter owns DCL as well as DDL.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-18",
        "title":  "ADR 0019\u0027s first limiter — \"may this analysis exist at all\", structural rather than economic — disappears with nothing named in its place",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "completeness",
        "location":  "docs/decisions/0019-reading-costs-an-action.md:65-76 (\"Three limiters, and they are not the same limiter\"; the first is \"Umpire ruling — *May* this report exist at all? Enforced by the tool grant\"); goals[7] and risks name only 0019\u0027s refusal loop and feed-vs-warehouse insight as surviving",
        "problem":  "0019 is explicit that its three limiters are different things and that conflating them produces bad reasoning about all three. This request retires the second (action economy) deliberately and correctly, and preserves the third (staff quality) via 0014\u0027s amendment. It abolishes the FIRST without naming it: once the GM issues its own SQL, no umpire rules on whether a given analysis may exist. 0019 calls that gate \"structural rather than economic, which is the point of 0017\", and the anti-laundering rule (\u0027a tap may only draw from the warehouse, never from the feed\u0027) is enforced by it. The scope\u0027s query log is an audit trail read after the fact, not a gate. This is a genuine and probably acceptable loss — but the scope\u0027s own convergence theme says the panel exists to find what intake missed, and this is a whole limiter.",
        "proposed_fix":  "Name it in 0022 as a deliberate removal with the reason (the operator\u0027s hypothesis is that the agent\u0027s analytical throughput is the independent variable). State what remains: the schema boundary bounds WHAT can be read, the query log records WHAT WAS read, and nothing gates WHETHER an analysis may exist. Note the consequential coupling for `gm-inbox`: 0019\u0027s anti-laundering rule was enforced by this gate, so if a news feed ever lands, the rule needs a new mechanism — a sentence in `gm-inbox`\u0027s disposition, which the scope already funds.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-19",
        "title":  "The \u0027citation is stronger than frozen bytes\u0027 claim depends on view definitions being immutable, and `CREATE OR REPLACE` makes them mutable",
        "severity":  "major",
        "confidence":  "medium",
        "category":  "risk",
        "location":  "gated_decisions[7] (\"the citation rule is also STRONGER than the report files\u0027 frozen-bytes property it replaces, because append-only bronze makes the citation re-runnable rather than merely archived\"); first-sight IMPLEMENTATION_PLAN.md:113 (snapshot-partitioned report paths: \"the exact bytes the GM read are still on disk, not regenerated from a warehouse that has since moved on\"); tiered_scope.core Phase B (`CREATE OR REPLACE VIEW`)",
        "problem":  "first-sight deliberately partitions reports by `(save_id, sim_date, ingest_seq)` so that a `gm/decisions/` record citing one can be checked against the exact bytes months later. The scope proposes replacing that with a citation to the same triple, and asserts the replacement is STRONGER because bronze is append-only. That holds for the ROWS and not for the QUERY: a citation resolves through a view whose definition is replaced whenever a category, a disposition or a column changes, so re-running a July citation in October can return a different column set — silently, since the triple still resolves. The property is recoverable, but only via the committed byte-deterministic SQL snapshot (currently a cheap fold, and see A2-08 for why it may not be buildable as scoped).",
        "proposed_fix":  "Either (a) make the committed view-SQL snapshot core and require a citation to name the commit or content hash of the view definition alongside the data triple, or (b) drop the \u0027strictly stronger\u0027 claim from 0022 and record it honestly as a different tradeoff — re-runnable but not frozen — with the reports\u0027 frozen-bytes property named as what was given up.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-20",
        "title":  "ADR 0017\u0027s Notes name the action economy as the tuning lever and disprefer new prohibitions; the amendment must say what the lever is now",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "docs/decisions/0017-gm-is-a-subagent.md:144-148 (\"The action economy is the tuning lever. If the GM does too much too quickly, the fix is fewer actions or dearer items — not new prohibitions... Umpires do not move the strike zone mid-game\")",
        "problem":  "0017 is being amended, and one of its Notes designates the very thing this request retires as the project\u0027s sole tuning lever, while explicitly dispreferring the alternative (new prohibitions). After this request the GM cannot be slowed down by any recorded mechanism. Separately, 0017 warns against moving the strike zone mid-experiment — which this request does, though at the only defensible moment (zero games played). Neither point appears in the scope\u0027s treatment of the 0017 amendment.",
        "proposed_fix":  "The 0017 amendment must answer both: name what the tuning lever is now (recommended: nothing bounds deliberation, and the query log plus token instrumentation are measurement rather than a lever — which the scope\u0027s own risk 6 already concedes), and record that the retirement lands before the first game precisely because 0017 forbids moving the zone mid-season.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-21",
        "title":  "The `FRONT_OFFICE.md` rewrite surface is undercounted — at least eight statements break, four are named",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "FRONT_OFFICE.md:11-21, :31, :47-65, :67-91, :95-98, :103, :110, :119-120, :129; tiered_scope.core Phase A doc rewrites names :31, :47-65, :67-91 and \"the two retired bullets\"",
        "problem":  "Verified against the file: beyond the three named spans and the two bullets at :103 and :110, the following also break — the opening paragraph (:11-15) describing advisors \"reading a warehouse built from the save\u0027s own files\" and (:19) the operator \"rules on what costs an action\"; the ADR-0017 bullet at :95-98 whose closing clause is \"You never spawn, never query, never write to `gm/`\" (two of three change); the `Where the club lives` pointer at :119-120 (\"`gm/ledger.jsonl` — every adjudication, cost or free. Doctrine is a query over this file\") pointing at a closing file; and :129 pricing `game-mechanics.md` at \"no action\". The scope says \"the two retired bullets\", which is an undercount of three.",
        "proposed_fix":  "Re-enumerate the FRONT_OFFICE.md spans in the core item, and make the doc-guard acceptance criterion check the surviving text for the additional retired strings (\"rules on what costs an action\", \"never query\", \"costs no action\", \"Doctrine is a query over this file\") rather than only the three currently listed.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-22",
        "title":  "The row cap is unspecified as truncate-or-refuse, and truncation produces the exact silent-wrong-answer the scope warns about",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "risk",
        "location":  "tiered_scope.cheap_folds[7] (\"Session guardrails on the GM connection: `MAX_STATEMENT_TIME`, an enforced row cap\"); risks[10] (grain fan-out producing \"a confident wrong answer\")",
        "problem":  "The scope funds a row cap and does not say what happens at the boundary. A cap that silently truncates hands a per-invocation agent a partial result set with no signal, which is worse than a slow query and is the same failure class the scope spends a whole risk bullet on: the GM answers \"who is on Boston\u0027s roster\" confidently and wrongly. A cap that refuses is safe but must be distinguishable from an empty result. `MAX_STATEMENT_TIME` has the same shape — MySQL returns a partial result plus an error on timeout in some paths.",
        "proposed_fix":  "Specify: the row cap REFUSES with a named error identifying the cap, never truncates, and the refusal is written to the query log. Add it to the tool\u0027s acceptance criteria alongside the no-connection-parameters signature assertion, which is already there.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-23",
        "title":  "`withheld_columns` and `data_dictionary` are two views, two grants and two tests doing one job",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "scope-creep",
        "location":  "tiered_scope.cheap_folds[0] and [1]; above_and_beyond[0] and [1]",
        "problem":  "`gm_view.withheld_columns` is generated from the `column_disposition` pass (table, column, reason, ADR). `gm_view.data_dictionary` is served from `bronze_field_label`, which already carries `category`, `epistemic`, `validator` and `source_file` per landed column. The two overlap substantially — a withheld column\u0027s `category` and `epistemic` are exactly what the dictionary would carry — and each independently needs a grant row, a grain assertion, a coverage statement and a conformance-diff entry. Filing both as cheap folds understates the marginal cost, and they will drift: one is generated from the live declaration and the other from what landed on a past date, so they can disagree about the same column with nothing erroring.",
        "proposed_fix":  "Ship one view. Recommended: the generated `withheld_columns`/dictionary view from `column_disposition` over `load_contracts()` (live, cannot drift from what was excluded), and expose `bronze_field_label`\u0027s as-of-landing labels only if a case for the historical view actually arises. If both ship, add an acceptance criterion that they agree on every column present in both, or the drift is unobservable.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-24",
        "title":  "The journal has no career-vs-club scope row, which `gm/README.md`\u0027s contract requires of every file",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "gm/README.md:43-49 (scope table assigning career or club to each of the five artifacts, recorded \"before the split it describes — because the moment of an actual firing is the worst possible time to argue about what survives\"); tiered_scope.core Phase A records career-vs-club only for the execution log",
        "problem":  "The scope explicitly records the execution log\u0027s career-vs-club scope and says nothing about the journal\u0027s. The journal is the largest new artifact and the one whose scope is genuinely ambiguous: notes and dated triggers about a specific roster are club-scoped, pre-registered calibration claims about the GM\u0027s own judgment are career-scoped (ADR 0015 makes the experiment a career), and they share one file and one hash chain. gm/README.md\u0027s own reasoning is that this must be settled before it matters.",
        "proposed_fix":  "Settle it in the scope: recommended, the journal is career-scoped as a FILE (one chain, one seq space, survives a firing) with each entry\u0027s subject carrying club context — because splitting a hash chain on employment change is a migration nobody wants. Add the row to `gm/README.md`\u0027s scope table in Phase A and add both new files to the acceptance criterion that checks prose grain against declared keys.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-25",
        "title":  "No acceptance criterion asserts the re-homed 0018/0019 arguments actually survive into the new ADRs",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "acceptance",
        "location":  "risks[6] (\"A supersession that does not explicitly re-home them loses reasoning it took two ADRs to reach\"); acceptance_criteria[13] checks only that retired PHRASES are absent and supersession lines present",
        "problem":  "The scope identifies losing 0018\u0027s foresight-trap argument and 0019\u0027s feed-vs-warehouse asymmetry and refusal loop as a named risk of the largest governance diff in the repo\u0027s history, then provides no criterion that would catch it. The doc guard as written is purely negative — it proves the old rules are gone, not that the surviving reasoning arrived. `tests/test_repo_structure.py::test_every_adr_records_its_cost` will not help; it only greps for the word \"cost\".",
        "proposed_fix":  "Extend the doc-guard criterion with a positive half: 0022 must contain identifiable statements of (a) retention-is-irreversible-so-charging-penalises-foresight, (b) infrastructure-can-never-replace-what-only-the-world-knows, (c) the refusal loop\u0027s three properties, and (d) the disposition of 0013\u0027s standing-order lever and graduation rule (per A2-07). Assert by named substring, the same mechanism the negative half uses.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-26",
        "title":  "No acceptance criterion covers the execution log\u0027s own rules, including `declined` requiring a non-empty reason",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "acceptance",
        "location":  "tiered_scope.core Phase A (execution-log schema: \"`reason` (mandatory, non-empty on `declined`)\"); acceptance_criteria[12] covers only generic per-line envelope validation across `gm/*.jsonl`",
        "problem":  "The execution log is the artifact replacing the ledger and carrying ADR 0019\u0027s refusal loop, and its one substantive rule — a decline must carry its reason, because \u0027the reason travels with the refusal\u0027 is what makes the loop work — has no test. The generic envelope criterion validates keys, types and unknown fields; a `declined` row with `reason: \"\"` satisfies all three.",
        "proposed_fix":  "Add one criterion: a `declined` entry with an empty or missing `reason` fails validation, asserted with a red fixture; and the context assembler surfaces every prior `declined` entry, asserted by the same temporary-`gm/`-root harness the trigger round-trip criterion already builds.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-27",
        "title":  "The new `gm/` artifacts should join `test_gm_contract_files_exist`, which currently does not even cover the ledger",
        "severity":  "minor",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "tests/test_repo_structure.py:94-103 (asserts gm/README.md, charter.md, standing-orders.md, staff.md, decisions/README.md — `gm/ledger.jsonl` is absent)",
        "problem":  "The repo has a guard whose stated purpose is \"A GM with no charter or ledger contract is a GM with amnesia\", and it does not list the ledger. This scope introduces two files whose absence would break the context assembler at runtime with no CI signal. Cheap to close in the same commit; invisible until the first cold invocation otherwise.",
        "proposed_fix":  "Add `gm/journal.jsonl` and `gm/execution-log.jsonl` to `test_gm_contract_files_exist` in Phase A, and add `gm/ledger.jsonl` while the file is open — a one-line fix to a guard that has been half-blind since it was written.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-28",
        "title":  "Latest-seq resolution inside a view materialises over 264k-row `bronze_name`, and the interaction with the statement timeout is unmeasured",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "risk",
        "location":  "tiered_scope.core Phase B (\"Every view resolves `max(ingest_seq)` per `(save_id, sim_date)`\"); tiered_scope.cheap_folds[7] (`MAX_STATEMENT_TIME`); ops/mysql-bootstrap.sql:24 (`utf8mb4_0900_ai_ci` — confirms MySQL 8.0+, so CTEs and window functions ARE available)",
        "problem":  "MySQL 8.0 makes the latest-seq view expressible (window function or CTE), which is good news the scope does not state. But a view whose definition contains a window function or a derived table cannot be merged into the outer query, so MySQL materialises it into a temporary table on every access. Against `bronze_name` at 264,095 rows per save per snapshot, a `gm_view` query joining names into a roster question pays that materialisation each time, under a `MAX_STATEMENT_TIME` the scope also funds. The scope treats view privilege semantics as `assumed` and flags them for measurement (good) but treats view PERFORMANCE as a non-question.",
        "proposed_fix":  "Record MySQL 8.0+ as a verified prerequisite (the collation in bootstrap.sql establishes it). Measure one representative latest-resolving query against the real warehouse during Phase B and record the number with an epistemic label before setting `MAX_STATEMENT_TIME`, rather than picking a timeout and discovering the interaction on the GM\u0027s first invocation. If materialisation is the problem, the honest fallback — serve the raw bronze grain and put latest-seq resolution in the cookbook — is a scope decision, not an implementation one.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-29",
        "title":  "`gm/decisions/` and the one existing decision record cite retiring doctrine and are not in the rewrite list",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "completeness",
        "location":  "gm/decisions/2024-03-07-decline-fan-interest-goal.md (the incident ADR 0016:27-33 was written from, cited as \"ledger seq 1\"); gm/decisions/README.md; tiered_scope.core Phase A doc rewrites",
        "problem":  "The GM\u0027s forced-read list sends it to `gm/decisions/` every invocation (`.claude/agents/gm.md:29`). The one record there is the fan-interest decision whose limitation section records the very database query that caused ADR 0016 to be written, and it cites ledger seq 1 in a file that is closing. Under the new model that record\u0027s limitation is no longer a limitation. Leaving it unannotated means the GM reads, every week, a record implying a rule that no longer exists — the same failure the scope\u0027s own \u0027what changed\u0027 migration-note fold exists to prevent, in the file the GM actually reads.",
        "proposed_fix":  "Fold into the migration note rather than editing the record (it is history and the repo does not edit those): the dated `what changed` note must explicitly re-point ledger-seq citations at the execution log and state that the fan-interest record\u0027s limitation describes a retired rule. Add `gm/decisions/README.md` to the rewrite list if its schema references the ledger.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-30",
        "title":  "`gm/charter.md`\u0027s Status blockquote names ADR 0016 as the blocker this request removes",
        "severity":  "nit",
        "confidence":  "high",
        "category":  "completeness",
        "location":  "gm/charter.md:10-15 (\"The blocker is no longer the league; it is that the GM has no warehouse and no reports ([ADR 0016])\")",
        "problem":  "gated_decisions[6] discusses whether the charter\u0027s CONTENT gets written in this slice, and correctly leaves that to the operator. But independent of that call, the Status blockquote itself becomes false the moment 0016 is superseded — it names a blocker that no longer exists and cites a superseded ADR as the reason. The charter is forced-read item 2 for every GM invocation.",
        "proposed_fix":  "Update the Status blockquote in Phase A regardless of whether the charter body is written: either \u0027the blocker is removed and the charter is owed\u0027 or \u0027the blocker is removed pending Phase B\u0027. Add `gm/charter.md` to the doc-guard\u0027s file set for the retired-phrase check.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-31",
        "title":  "Operator load is named as a risk with no baseline, no criterion and no accepted-cost statement",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "acceptance",
        "location":  "risks[12] (\"THE OPERATOR MAY BE IN THE LOOP MORE, NOT LESS... Nothing in the request measures before-versus-after\"); docs/decisions/0013-action-economy.md:94-96 (\"The operator is in the loop every period... a standing tax on playing\")",
        "problem":  "The scope identifies the ironic outcome — a request motivated by compounding adjudication overhead producing a heavier weekly tax — and then leaves it as a risk with no disposition. The new model asks the operator for execution dispositions, claim resolutions and trigger dispositions every week where the old one asked for cost rulings. There is no baseline (the ledger holds one row), no criterion, and no statement accepting the cost. A risk with no owner and no measurement is a prediction, not a decision.",
        "proposed_fix":  "Convert to a written accepted cost in 0022\u0027s Costs section with a review trigger (e.g. \u0027if a weekly cycle takes the operator longer than the pre-retirement cycle after four weeks, reopen\u0027), or add a lightweight measurement to the execution log (one wall-clock field per cycle) alongside the token instrumentation gated decision 10 already proposes. `test_every_adr_records_its_cost` greps for the word \u0027cost\u0027 and will not notice an omitted one.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-32",
        "title":  "Nothing bounds an umpire handing the GM a number from `ootp_truth_real`; 0019 named the analogous hole and this scope does not",
        "severity":  "minor",
        "confidence":  "medium",
        "category":  "risk",
        "location":  "docs/decisions/0019-reading-costs-an-action.md:156-158 (\"It is prose, not prevention, on the laundering rule specifically. The tool grant genuinely prevents the GM from building anything; nothing prevents an *umpire* from approving a report sourced from the feed\"); goals[3] (the grant \"cannot reach... `ootp_truth_real`\")",
        "problem":  "The scope\u0027s third goal frames the restricted grant as meaning that \"even if every prose rule failed the connection cannot reach `ootp_truth_real`\". True of the connection, and the strongest thing in the request. But the umpires retain ALL PRIVILEGES on that schema (`ops/mysql-bootstrap.sql:63`) and hand the GM its context every week. The residual channel is exactly the one 0019 was careful to name about itself, and 0022 will read as claiming more than it delivers if it does not name the same residual.",
        "proposed_fix":  "One sentence in 0022\u0027s Costs: the grant closes the GM\u0027s own channel to the answer key and does not close the umpires\u0027; that half remains prose, exactly as 0019 recorded for its laundering rule, and it holds because the assembled context is authored by code (the context assembler) rather than pasted by hand — which is a real strengthening worth naming.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-33",
        "title":  "Open question: does the rendered-report channel survive alongside `gm_view`, get retired, or both?",
        "severity":  "question",
        "confidence":  "high",
        "category":  "scope",
        "location":  "non_goals[10] (\"Rewriting or absorbing first-sight Phases 10–13... They ship as planned; this request converts their output afterwards\") vs tiered_scope.core Phase B (\"first-sight ... converts their two reports into `gm_view` seed views\"); first-sight IMPLEMENTATION_PLAN.md:1041 and :1065 (the `ootp_ai.reports` entry point and the tracked report-path pointer / spawn instruction)",
        "problem":  "\u0027Convert\u0027 is ambiguous and the scope uses it three ways. first-sight builds a real renderer (`python -m ootp_ai.reports render`), a snapshot-partitioned ignored output root asserted by AC14, and a tracked report-path pointer plus spawn instruction that Phase 11 step 6 says AC20 is unreproducible without. If `gm_view` seed views replace the reports, all three become dead code and a tracked doc section describing a channel nobody uses. If they coexist, the GM has two surfaces for the same facts that can disagree (a report rendered at seq 2 versus a view resolving to seq 3), and the scope\u0027s non-goal about serving-layer transformations does not say which is canonical.",
        "proposed_fix":  "Settle it in the scope: recommended, the reports SURVIVE as the umpires\u0027 hand-off surface and the frozen-bytes citation channel (A2-19), and `gm_view` is the GM\u0027s self-serve surface; both resolve to `max(ingest_seq)` by the same convention, and a report states the seq it read so the two are reconcilable. If instead the reports retire, say so and add their removal — and the removal of Phase 11\u0027s pointer section — to the Phase B item list.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-34",
        "title":  "Open question: the Phase B spike has no owner, no timebox artifact and no recorded failure disposition path",
        "severity":  "question",
        "confidence":  "medium",
        "category":  "scope",
        "location":  "tiered_scope.core (\"PHASE B GATE — THE TOOL-CHANNEL SPIKE... Record the result with an epistemic label in the request\u0027s `reviews/` trail\")",
        "problem":  "The gate is the most consequential item in the scope — it decides roughly a third of the build — and it is specified as \u0027prove in a throwaway branch\u0027 with a `reviews/` destination and no owner, no artifact name, no success criteria beyond three clauses, and no statement of who is permitted to run it. It cannot be a builder task: `.claude/` is in the builder\u0027s deny set (A2-14), so registering a tool and editing `gm.md`\u0027s frontmatter is main-thread-only. first-sight\u0027s Phase 0 shows the shape the repo actually uses for this (a pre-registered pivot rule committed strictly before the verdict, asserted by `git log` ordering as AC18).",
        "proposed_fix":  "Give the spike the first-sight Phase 0 treatment: a pre-registered pass/fail rule committed BEFORE the spike runs, a named verdict artifact under `requests/feature-requests/open-front-office/reviews/`, main-thread ownership stated explicitly, and the three clauses restated as binary checks. Then the gate is auditable rather than a judgment made by whoever ran it.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-35",
        "title":  "Open question: `FRONT_OFFICE.md` is writable by the builder while being the umpires\u0027 rulebook",
        "severity":  "question",
        "confidence":  "low",
        "category":  "risk",
        "location":  ".claude/agents/data-engineer.md:154-165 (deny set omits FRONT_OFFICE.md); .claude/agents/README.md:22-28 (\"The GM is the deliberate exception: its rules live in FRONT_OFFICE.md because the umpires read the same copy to adjudicate it\")",
        "problem":  "`CLAUDE.md` and `docs/decisions/` are denied to the builder because they are the manager\u0027s and the main thread\u0027s. `FRONT_OFFICE.md` is the same class of artifact — the shared rulebook both the GM and the umpires read — and it is not denied. This request rewrites it substantially, which is the moment the omission is cheapest to notice. Low severity because the builder has no reason to touch it and the deny set is prose anyway; raised because the scope\u0027s whole theme is that prose enforcement failed and this is a prose gap adjacent to the one it is fixing.",
        "proposed_fix":  "Ask the operator whether `FRONT_OFFICE.md` should join the builder\u0027s deny set alongside `gm/` (A2-15). If yes, land both lines in the same Phase A commit and pin them in `tests/test_agent_contract.py`. If no, record why — that the rulebook is engineering-adjacent enough to be builder-editable is a defensible call, but it should be a call.",
        "adversary":  "scope-completeness"
    },
    {
        "id":  "A2-36",
        "title":  "The core \u0027thin skill\u0027 invoking the context assembler and the gated `/gm-week` skill are the same artifact at two tiers",
        "severity":  "nit",
        "confidence":  "medium",
        "category":  "scope-creep",
        "location":  "tiered_scope.core Phase A (\"the context assembler as a MODULE under `src/ootp_ai/`, invoked by a thin skill\") vs tiered_scope.gated[12] (\"A `/gm-week` skill running the whole cycle end to end (assemble, spawn, validate envelope, land, stop for dispositions)\")",
        "problem":  "Core funds a skill that assembles context; gated defers a skill that assembles context, spawns, validates and lands. The first is the first step of the second, and once the lander and the assembler both exist as modules the marginal cost of the gated version is small — which means either the gated item is cheaper than its gating implies, or the core \u0027thin skill\u0027 is doing more than \u0027thin\u0027 suggests and should be sized. The scope\u0027s own argument for gating `/gm-week` (\u0027the core scope already puts the lander and the assembler in code, which is where the assertions live\u0027) is also an argument that the remaining skill is thin.",
        "proposed_fix":  "Name the core skill\u0027s exact surface (one command, prints assembled context to stdout, no spawn, no write) so the tier boundary is legible, and restate the gated item as \u0027the orchestration and landing steps on top of it\u0027 rather than \u0027the whole cycle\u0027, so the operator is choosing between two clearly different sizes.",
        "adversary":  "scope-completeness"
    }
]
```

## Convergence map

```json
[
    {
        "theme":  "RESHAPE, not clean and not poor — the mechanical half fits the repo\u0027s grain; the enforcement half is partly unbuildable",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "Three lenses that normally disagree on ambition returned the same verdict for the same reasons. No scoper argued the feature should be dropped, and none argued it could be built as written. That is the strongest possible signal that the request\u0027s motivation is sound and its mechanism needs surgery."
    },
    {
        "theme":  "The harness has NO path-level permission system, so a `Write` grant scoped to `gm/` paths is prose enforcement inside a request whose thesis is that prose failed",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "All three cited `.claude/agents/README.md:104-113` verbatim and independently. This is not an opinion — it is a measured statement in the repo\u0027s own documentation that directly refutes the first option of the request\u0027s Open Question 2. All three converged on the same replacement: structured return plus an umpire-side typed lander, which keeps ADR 0017\u0027s pen-holding AND makes append-only mechanically true because the sole writer is code that can only append."
    },
    {
        "theme":  "There is NO query vehicle in this repo today, and `Bash` is disqualified — this must be spiked before it is planned",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "All three verified the same absence (no `.mcp.json`, no `.claude/settings.json`) and reached the same disqualification: a Bash grant hands the GM `.env`, the writable warehouse and `ootp_truth_real` in one move, which is strictly WORSE than ADR 0016\u0027s prose wall. The minimalist made it a hard gate; the fit scoper called it the single highest-value thing to settle before planning. Converging on \u0027this decides half the scope\u0027 from three directions is why it is the headline gated decision\u0027s second clause."
    },
    {
        "theme":  "The wall guards an empty room — measured, one withheld column of 96, and zero `rating-scouted` fields declared",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "All three independently ran or read the same measurement and got the same numbers (I reproduced it: 8 tables, 96 columns, 94/1/1). All three drew the same two conclusions: build it anyway (far cheaper before the answer key arrives than retrofitted after), but the ADR must say so plainly, and the acceptance test must plant a SYNTHETIC `rating-true` column or it passes on a schema with nothing to withhold. That last point is a concrete test-design requirement three lenses reached separately."
    },
    {
        "theme":  "`Disposition.UNCERTAIN` has no mapping onto a two-valued schema, and this is a decision the request never raises",
        "scopers":  [
                        "fit",
                        "ambitious"
                    ],
        "why_high_signal":  "Both scopers found the same structural gap in the request itself: the policy has three outcomes because a report page can carry a banner (`render_with_uncertainty`, `uncertainty_banner`), and a SQL view has no banner channel. Both noted exactly one landed column is affected, so deciding costs almost nothing now and becomes a silent default made by whoever writes the generator otherwise. A gap two independent scopers found that intake missed is the definition of what a scoping panel is for."
    },
    {
        "theme":  "Hash-chain the append-only files rather than diffing against git history",
        "scopers":  [
                        "fit",
                        "minimalist"
                    ],
        "why_high_signal":  "Both reached it from a mechanical constraint rather than a preference: `.github/workflows/ci.yml` pins `fetch-depth: 1`, so a merge-base check cannot run today, and `merge=union` interleaves so a prefix test would false-fail even with full history. Both also spotted that `merge=union` and a hash chain are mutually incompatible and that the new files must therefore accept conflicts — reversing a convention `gm/README.md:60-61` documents as deliberate. A cheaper AND stronger mechanism that also delivers the request\u0027s literal word, \u0027tamper-evident\u0027."
    },
    {
        "theme":  "Two ADRs, not one — and the split is a dependency split, not a stylistic one",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "All three recommended two against the request\u0027s own agnosticism, and the minimalist supplied the decisive argument the other two implied: the memory model depends on nothing while the information model depends on an unverified harness capability, so one ADR holds the cheap two-thirds hostage to the spike. The fit scoper added the historical evidence — 0017 carrying two decisions is what produced 0018 and 0019 as patches."
    },
    {
        "theme":  "Close `gm/ledger.jsonl`, do not migrate it",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "Unanimous, with the same reasoning: rewriting a tracked append-only file to fit a new schema is exactly the retroactive edit this request exists to make impossible, and it is the repo\u0027s own supersede-never-edit discipline applied to GM memory. Seq 1\u0027s actual reasoning — choosing between options the owner already presented is free — survives as doctrine even though its currency does not."
    },
    {
        "theme":  "Nothing in `tests/` asserts anything about `.claude/agents/gm.md` — the guard that makes every other enforcement claim checkable",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "All three measured the same zero and all three independently connected it to first-sight Phase 13 step 4, which already filed it as a follow-up. It is the one guard that must land BEFORE the grant widens, because it is what makes the widening reviewable in a diff. Unanimous and already owed."
    },
    {
        "theme":  "Retiring the economy removes the denominator ADR 0012 and 0014 lean on, and something must replace it",
        "scopers":  [
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "Both identified that 0013\u0027s load-bearing product was not the budget but the measurement it enabled — \u0027twelve actions on the draft and three busted picks is a return on invested attention\u0027 — which 0012\u0027s Buys section uses to make scout quality assessable. Both converged on a query/provenance log written BY THE TOOL rather than by the GM as the replacement, and both argued it should not be optional. That is why I promoted it from enhancement to core."
    },
    {
        "theme":  "Let first-sight ship Phases 10–13 first; convert afterwards",
        "scopers":  [
                        "fit",
                        "ambitious",
                        "minimalist"
                    ],
        "why_high_signal":  "Unanimous, from three different angles: it is one commit from \u0027the commit the request exists for\u0027; its Phase 11 wires the catalog into the required-docs guard in the same commit as the generator; and — the fit scoper\u0027s sharpest point — its Phase 13 AC20 produces the only measured baseline of what a GM can do under the report wall, without which \u0027scarcity is a confound\u0027 stays argued rather than testable. The cost of going second (Phase 12 writes 0016-shaped standing orders, Phase 13 appends a ledger row in the retiring schema) is cheap to supersede."
    },
    {
        "theme":  "The GM\u0027s DSN cannot be the application DSN, and `gm_view` must be pinned to one universe",
        "scopers":  [
                        "fit",
                        "ambitious"
                    ],
        "why_high_signal":  "Both noticed that `ops/mysql-bootstrap.sql:57-63` grants the application user ALL PRIVILEGES on `ootp_truth_real` — the ground-truth export holding true ratings — so without a separate restricted user the GM reaches the answer key simply by connecting. Both also flagged that `MYSQL_DATABASE` swaps between `ootp` and `ootp_dev`, so a GM pointed at the dev schema manages a different universe with nothing erroring: the exact failure the schema split was built to prevent, arriving through a new door."
    }
]
```
