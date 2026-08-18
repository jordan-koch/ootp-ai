<!-- NORMALISED: one planner emitted absolute machine paths in its file lists. Every
     occurrence of this checkout's repo root was rewritten to a repo-relative path before
     staging -- the repo is PUBLIC and tests/test_no_leaks.py bans drive letters. The guard
     could not have caught it here: it enumerates via `git ls-files`, so it is blind to an
     untracked file (see requests/bugfix-requests/leak-guard-blind-to-untracked-files/).
     Only the path prefixes changed; no other content was altered.
     REPOINTED: when this request was archived, every `requests/bugfix-requests/<slug>/`
     path in this file was rewritten to its `_done/` location so a reader can still follow
     it. `_done/` is excluded from tests/test_doc_links.py, so this was for the reader, not
     for CI. Only path prefixes changed; no agent's wording was altered.
     -->
﻿<!-- ESCAPE APPLIED: one literal occurrence of a Markdown link whose target carried a line
     suffix was written as `] (path.py:42)` (space inserted after the bracket) so that
     tests/test_doc_links.py does not read this raw panel output as a real broken link.
     That guard has no fence awareness and does not strip a :123 suffix -- the very defect
     Phase 5 of the IMPLEMENTATION_PLAN fixes. Nothing else in this file was altered. -->
<!-- Raw, unfiltered panel output. Saved by /create-implementation-plan step 3. -->

# Planning panel â€” raw planner proposals

Three divergent planners, run 2026-08-17 against
`requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md`.
Panel health: planners_ok 3, adversaries_ok 2, meta_audit_ok 1, degraded_lenses [].

## Proposal 1 â€” code-grounded

```json
{
  "planner": "code-grounded",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Its Verdict (line 19-24) settles the load-bearing question by experiment: the FIXTURE is wrong, acceptance_panel.js is correct. Its Fix posture (lines 174-214) is the tiered menu these phases execute. Do not re-litigate it."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md",
      "why": "Context only. Its 'Affected Area & Pointers' (lines 103-115) lists the three files to open in order, and its Open Questions (131-151) are all answered in the RCA."
    },
    {
      "path": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs",
      "why": "THE file being fixed. 293 lines. The fixture is at :40-64, the silent-swallow at :78, the stale roster comment at :150, and the four scenarios at :184-283. Read it in full before editing."
    },
    {
      "path": ".claude/skills/implement-plan/acceptance_panel.js",
      "why": "The code under test â€” READ IT, DO NOT EDIT IT. The lens roster is at :189-209 (CORE at :189-194, SPEC_DEFS at :196-202, AREA_TO_SPEC at :203-207). The dedupe the guard falsely accused is at :298-333. safeAgent at :139-146 swallows every throw â€” that constrains how Phase 2 fails loudly."
    },
    {
      "path": "tests/test_skill_references.py",
      "why": "The committed red reproduction (landed on this branch at 0ed70d5). Two tests, both RED today. It is direction-independent by design (docstrings at :48-54 and :84-96 say so) â€” it is the regression guard the RCA's acceptance contract requires, and it must NOT be rewritten to fit the fix."
    },
    {
      "path": "requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md",
      "why": "The sibling RCA that owns the GATED decision. Its line 97-98 rules that the six-reference correction is 'common to both readings and is the only part safe to do early' â€” that is the authority under which Phase 3 acts without pre-deciding the gate."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The track contract. The pipeline table (:14-18), the acceptance rule at :25-26 ('done' = red repro green + regression test left behind), the status grammar at :45, and the Index row for this slug at :53 that Phase 6 advances."
    },
    {
      "path": ".claude/skills/create-implementation-plan/SKILL.md",
      "why": "Stage-3 contract. Step 5 (:158-231) is the section menu this plan was written from; :167-173 prescribes the status/Index advance. Note :251 is itself one of the six files this plan repairs."
    },
    {
      "path": "CLAUDE.md",
      "why": "The conventions that bind the implementer: agents commit only through /commit, work on a branch, subagents get read-only git, no OOTP game data in git."
    }
  ],
  "architecture_notes": "TOUCHED AREA: the stage-4 acceptance-panel harness under `.claude/skills/implement-plan/`, plus five sibling SKILL.md files that carry the same port residue. NOTHING in `src/ootp_ai/`, no dbt model, no dataset, no save file, no `.env` path. The game is not read, let alone written.\n\nCURRENT STRUCTURE\n\n`acceptance_panel.js` (the code under test â€” CORRECT, do not edit) is a single top-level-await module the harness evaluates with `agent/parallel/pipeline/phase/log/args/budget` injected. Its lens roster is assembled at `:189-209`:\n  - `CORE` (`:189-194`) â€” four always-on reviewers keyed `acceptance`, `fidelity`, `correctness`, `edgecases`.\n  - `SPEC_DEFS` (`:196-202`) â€” six specialists keyed `parser`, `warehouse`, `builder`, `skill-quality`, `infra-cost`. (Five entries; `infra-cost` and `builder` included.)\n  - `AREA_TO_SPEC` (`:203-207`) â€” `src: ['parser','warehouse']`, `transform: ['warehouse']`, `datasets`/`build`: `['builder']`, `tests: ['parser']`, `skills: ['skill-quality']`, `ci`/`config`: `['infra-cost']`, `docs: []`.\n  - `specKeys` (`:208`) = `AREAS.flatMap(...)` deduped; `ROSTER` (`:209`) = CORE + matched specialists.\nPhase 1 (`:249-263`) spawns one agent per roster entry labelled `review:<key>`. Phase 2 dedupes blocker/major findings (`dedupeFindings`, `:312-333`), buckets them by normalized location (`bucketByLocation`, `:339-355`), and packs them into at most `VERIFY_CAP` batch agents (`:370-375`).\n\n`verify_batching_guard.mjs` (the ARTIFACT THAT IS WRONG) does not import the panel â€” it reads its source at `:34` and re-evaluates it inside a `new Function(...)` at `:155-159`, injecting a stub `agent`. The stub (`makeAgent`, `:163-179`) dispatches on the panel's real label: `:172` `if (label.startsWith('review:')) return reviewFor(label.slice('review:'.length))`.\n\nTHE SEAM â€” AND THE DEFECT\n\n`reviewFor` (`:77-93`) resolves the lens through a plain object lookup with an `|| []` fallback:\n    const spec = FINDINGS_BY_LENS[lensKey] || []\n`FINDINGS_BY_LENS` (`:40-64`) is keyed by six lens names, two of which â€” `'data-contract'` (`:54`) and `extraction` (`:58`) â€” are a SIBLING repo's vocabulary. This repo's panel never asks for them, so their 3 findings (2 + 1 of the fixture's 11) never enter the run. The `|| []` means no throw, no warning, no `undefined` â€” just an empty review.\n\n`RAW_TOTAL` (`:65`) is computed from the fixture object (11), and `DEDUPED_TOTAL` (`:66`) from that (9). Scenario 1 (`:199-200`) compares the panel's real `stats.findings_blocker_major_raw` (8) against 11, and every one of the six failure lines cascades from that gap â€” including `over-merged land/writer.py` at `:208`, which is not an over-merge at all: the second `writer.py` bug lives at `:59` under `extraction` and was never raised.\n\nTHE HOOK POINT FOR THE FIX\n\nTwo words at `:54` and `:58`. `makeArgs` (`:145-153`) passes `touchedAreas: ['transform','src','skills']`, which resolves through `AREA_TO_SPEC` to exactly `warehouse`, `parser`, `skill-quality` â€” so `'data-contract' -> warehouse` and `extraction -> parser` is the only mapping that makes the fixture's 11 findings reachable. The stale comment at `:150` still teaches the wrong names and must move with them.\n\nI INDEPENDENTLY RE-RAN THE RCA'S DECISIVE EXPERIMENT (scratchpad copy, `PANEL` repointed at the tracked panel, only those two keys renamed, `acceptance_panel.js` byte-untouched):\n    [cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0\n    [dead-batch] verifiers=4/5 unverified=3/9 note=\"verify:b1 (3 findings left unverified)\"\n    [rubberstmp] b1Calls=2 verifiers=4/5 unverified=3\n    [verifyCap ] cap=2 batches=2 unverified=0/9\n    GREEN ... EXIT=0\nConfirmed. The panel is correct; the fixture was wrong.\n\nWHY THE ROOT FIX CANNOT LIVE IN `reviewFor`\n\nThe obvious hardening â€” make `reviewFor` throw on an unknown key â€” DOES NOT WORK, and this is the single most important architectural constraint in this plan. `reviewFor` runs inside the stub `agent`, which the panel invokes only through `safeAgent` (`acceptance_panel.js:139-146`):\n    try { return await agent(prompt, opts) } catch (e) { log(...); return null }\nEvery throw is swallowed and downgraded to a failed lens. Worse, `reviewFor` is only ever called for keys the roster ASKED for â€” it can never observe the actual defect, which is a fixture key nothing asks for. The invariant has to be checked at the guard's own module scope, in two directions: (a) every `FINDINGS_BY_LENS` key exists in the panel's declared roster, derived from `SRC` rather than duplicated; and (b) every `FINDINGS_BY_LENS` key was actually REQUESTED during Scenario 1 (tracked in a `Set` inside `reviewFor`, asserted after the run). Direction (b) is the precise one â€” a valid-but-unrequested key such as `builder` would still contribute zero.\n\nTHE PYTHON HALF\n\n`tests/test_skill_references.py` (committed at 0ed70d5) already owns direction (a) from outside: `LENS_KEY` at `:37` is `\\bkey:\\s*'([a-z0-9-]+)'` applied to the panel source, and `FIXTURE_LENS` at `:40` is `^ {2}'?([a-z0-9-]+)'?:\\s*\\[` applied to the fixture block that `fixture_lens_keys()` (`:72-76`) carves out by splitting on `const FINDINGS_BY_LENS = {` and `\\n}\\n`. This constrains the EDIT: the new keys must stay at exactly two-space indent, and the closing `}` of the fixture object must stay at column 0. Quoted or unquoted both parse.\n\nTHE SECOND CLUSTER â€” PORTED REFERENCES\n\n`tests/test_skill_references.py::test_every_test_file_a_skill_names_exists` scans `.claude/skills/**/*.md` for `tests/test_[a-z0-9_]+\\.py` tokens (regex at `:32`) and asserts each resolves. I enumerated every such token in the repo: exactly seven are dead â€” six `tests/test_request_links.py` and one `tests/test_extract_pagination.py`. They fall into two categories that must be handled differently:\n  - CATEGORY A, pure command invocations with no promise attached: `commit/SKILL.md:104` and `update-docs/SKILL.md:56`, both `uv run pytest tests/test_request_links.py -q`. Direction-neutral, safe to repoint.\n  - CATEGORY B, the \"What good looks like\" bullet, which names the guard AND promises three exemptions it does not have: `make-bugfix-request/SKILL.md:199`, `make-feature-request/SKILL.md:246`, `diagnose-bug/SKILL.md:176`, `create-implementation-plan/SKILL.md:251`. Repointing the NAME alone here attaches a false promise to a real file.\nThe correct target is `tests/test_doc_links.py` under BOTH readings of the doc-link gate â€” confirmed independently by `acceptance_panel.js:200`, whose skill-quality mandate already names `tests/test_doc_links.py` as the mechanical link check.\n\nTHE THIRD CLUSTER â€” DOMAIN RESIDUE IN `diagnose-bug/SKILL.md`\n\n`:117-118` cites `tests/test_extract_pagination.py::test_all_pages_landed` failing with \"expected 1230 games, got 1000\" â€” there is no pagination in a save-file parser and 1,230 is an NBA regular season. `:97`, `:107` and `:150` write the status word `root-cause`, against `requests/bugfix-requests/README.md:45` and `commit/SKILL.md:133`, which both give the grammar as `intake -> diagnosed -> planned -> fixed`.\n\nWHAT MUST NOT MOVE: `acceptance_panel.js` (proven correct), `tests/test_skill_references.py` (the direction-independent repro), `tests/test_doc_links.py` (owned by the gated doc-link decision, a separate request).",
  "phases": [
    {
      "name": "Phase 1 â€” Re-key the batching guard's fixture to this repo's lenses",
      "goal": "The red `.mjs` guard goes GREEN with `acceptance_panel.js` byte-untouched, and the second red pytest assertion goes green. This is the RCA's Minimal step 1, and it is the step everything else is ordered behind.",
      "steps": [
        "Read `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` in full (293 lines) before touching it.",
        "Confirm the baseline is red: `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` -> exit 1 with `raw=8, expected 11` and five more lines; `uv run pytest tests/test_skill_references.py -q` -> 2 failed.",
        "Edit `:54`: `  'data-contract': [` -> `  warehouse: [`. Keep EXACTLY two leading spaces â€” `tests/test_skill_references.py:40` parses fixture keys with `^ {2}'?([a-z0-9-]+)'?:\\s*\\[` and a different indent makes the guard stop seeing the key at all.",
        "Edit `:58`: `  extraction: [` -> `  parser: [`. Same two-space constraint.",
        "Do NOT reflow the fixture object. `fixture_lens_keys()` at `tests/test_skill_references.py:75` carves the block by splitting on the literal `const FINDINGS_BY_LENS = {` and `\\n}\\n`, so the opening line and the column-0 closing brace at `:64` must stay exactly as they are.",
        "Edit the stale roster comment at `:150`: `// -> data-contract + extraction + skill-quality specialists` -> `// -> warehouse + parser + skill-quality specialists`. This is the mapping `acceptance_panel.js:203-207` actually performs for `touchedAreas: ['transform','src','skills']` (transform->warehouse, src->parser+warehouse, skills->skill-quality).",
        "Leave the per-entry comments at `:55` (`// dup of fidelity[1]`) and `:59` (`// same file, different bug`) alone â€” both are still accurate after the re-key.",
        "Run `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` and read the four diagnostic lines, not just the exit code.",
        "Run `git diff --stat` and confirm `acceptance_panel.js` appears ZERO times. If it appears, stop: the RCA (lines 122-126) names 'fixing the panel to satisfy the guard' as the worst available outcome."
      ],
      "acceptance": [
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 and prints `GREEN: verify batching stays under the cap ...`",
        "Its first diagnostic line reads exactly `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` (measured independently by the planner on a scratchpad copy of this exact change).",
        "`[dead-batch]` reads `verifiers=4/5 unverified=3/9`, `[rubberstmp]` reads `unverified=3`, `[verifyCap ]` reads `cap=2 batches=2 unverified=0/9`.",
        "`uv run pytest tests/test_skill_references.py::test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines -q` passes.",
        "`git diff --stat` lists exactly one changed file: `.claude/skills/implement-plan/tests/verify_batching_guard.mjs`. `acceptance_panel.js` is untouched.",
        "`node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs` still exits 0 (the known-good sibling has not regressed).",
        "`uv run ruff check .` and `uv run mypy` are clean (no Python changed, but the gate runs anyway)."
      ],
      "commit_note": "Re-key the batching guard's fixture to this repo's lenses\n\nTwo fixture entries named a sibling repo's specialists â€” data-contract and\nextraction â€” which this panel never asks for. `FINDINGS_BY_LENS[k] || []`\nswallowed them, costing 3 of 11 findings before dedupe ran, and all six\nfailure lines followed. acceptance_panel.js is untouched: it was right."
    },
    {
      "name": "Phase 2 â€” Make an unreachable fixture lens fail loudly instead of miscounting",
      "goal": "Close the mechanism that hid the bug for the whole life of the skill. The RCA's Root step 4: the next roster rename must produce a named error, not a miscount attributed to the code under test.",
      "steps": [
        "Understand the constraint FIRST: do NOT make `reviewFor` (`:77-93`) throw. `acceptance_panel.js:139-146` wraps every agent call in `safeAgent`, whose `catch` swallows the throw and returns `null`, degrading the lens. Worse, `reviewFor` is only called for keys the roster ASKED for, so it structurally cannot observe an orphaned fixture key. The assertion belongs at the guard's module scope.",
        "Add DIRECTION A, immediately after the `RAW_TOTAL`/`DEDUPED_TOTAL` constants at `:65-66` and before the first scenario: derive the panel's declared lens keys from the already-loaded `SRC` (`:34`) with `[...SRC.matchAll(/\\bkey:\\s*'([a-z0-9-]+)'/g)].map(m => m[1])` â€” the same shape `tests/test_skill_references.py:37` uses â€” and if any `Object.keys(FINDINGS_BY_LENS)` entry is absent from that set, print a RED block naming the unknown key(s) and the panel's real roster, then `process.exit(1)` before any scenario runs.",
        "Guard the derivation itself: if zero lens keys parse out of `SRC`, that is a drifted regex, not a green run â€” fail with that message rather than vacuously passing (this mirrors the assertions at `tests/test_skill_references.py:99-100`).",
        "Add DIRECTION B, the precise invariant: declare a module-level `const REQUESTED = new Set()` and add `REQUESTED.add(lensKey)` as the first line of `reviewFor` (`:78`). After Scenario 1's block closes (`:226`), assert every `Object.keys(FINDINGS_BY_LENS)` entry is in `REQUESTED`; push a failure that says the fixture key was never requested by this run's roster and that the counts below are a FIXTURE defect, not a panel defect. This catches a key that is valid in the panel but not in this run's `touchedAreas` (e.g. `builder`) â€” which direction A cannot see.",
        "Extend the guard's header comment block (`:1-27`) with a fifth pinned property describing the fixture/roster agreement, so the file teaches the invariant it now enforces.",
        "Prove the new check bites: copy the guard to the scratchpad directory, repoint its `PANEL` const (`:33`) at the tracked panel by absolute path, rename the `warehouse:` key back to `data-contract:`, and run it. It must exit 1 with the NEW named message and must NOT reach `raw=8, expected 11`.",
        "Do not add the check to `merge_fallback_guard.mjs` â€” it passes `touchedAreas: []` (`:90`) and has no lens-keyed fixture, so there is nothing to check."
      ],
      "acceptance": [
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` still exits 0 with the same four diagnostic lines as Phase 1.",
        "A scratchpad copy with one fixture key renamed back to `data-contract` exits 1, and its first printed failure NAMES the unknown key and points at the fixture â€” the string `raw=8, expected 11` does not appear.",
        "A scratchpad copy whose fixture gains a key valid in the panel but outside this run's roster (e.g. `builder:`) also exits 1, via the direction-B assertion.",
        "The panel's lens roster is READ from `acceptance_panel.js`, not restated â€” `grep -c \"warehouse\\|parser\" ` on the new check shows no hardcoded roster list.",
        "`git diff --stat` still shows `acceptance_panel.js` unchanged.",
        "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run mypy` all green."
      ],
      "commit_note": "Fail loudly on a fixture lens the panel never asks for\n\nThe guard now derives the panel's roster from acceptance_panel.js and\nrefuses a fixture key that is not in it, and refuses a key no lens in the\nrun actually requested. The check lives at module scope because safeAgent\nswallows any throw raised inside the stub agent."
    },
    {
      "name": "Phase 3 â€” Repoint the six dead `tests/test_request_links.py` references",
      "goal": "The first half of the red repro goes green. The RCA's Minimal step 2 â€” deliberately ordered after Phase 1, and executed WITHOUT pre-deciding the doc-link request's gated question.",
      "steps": [
        "Re-read `requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:95-98` â€” it is the authority for doing this now: the reference correction is 'common to both readings and is the only part safe to do early'. The target is `tests/test_doc_links.py` under either reading; `acceptance_panel.js:200` already names it as the mechanical link check.",
        "CATEGORY A â€” pure invocations, name-only edit. `.claude/skills/commit/SKILL.md:104` and `.claude/skills/update-docs/SKILL.md:56`, both `uv run pytest tests/test_request_links.py -q` -> `uv run pytest tests/test_doc_links.py -q`. Nothing else in those blocks changes.",
        "CATEGORY B â€” the 'What good looks like' bullet in four files: `.claude/skills/make-bugfix-request/SKILL.md:199`, `.claude/skills/make-feature-request/SKILL.md:246`, `.claude/skills/diagnose-bug/SKILL.md:176`, `.claude/skills/create-implementation-plan/SKILL.md:251`. Repoint the name to `tests/test_doc_links.py` AND apply the disposition of Open Question 1 below.",
        "RECOMMENDED disposition for Category B (settle with the user before writing): repoint the name, and replace the three exemption PROMISES with a factual statement of what the guard does today plus a bare pointer to the open request â€” e.g. 'today that guard exempts only http(s)://, mailto:, # and angle-bracket placeholders; fenced content, a file.py:123 suffix and var/ targets are NOT exempt, so keep citations as code spans until requests/bugfix-requests/_done/doc-link-guard-mismatch/ settles whether it grows them.' This describes the current state rather than ruling on the gate: under reading (a) the note is deleted when the exemptions land; under reading (b) it becomes permanent prose. Neither is made cheaper.",
        "Write that pointer as a BARE token, not a Markdown link â€” `tests/test_doc_links.py:15` excludes only `var/` from the files it scans, and a link whose target does not resolve turns CI red.",
        "Verify the facts you are about to assert by reading `tests/test_doc_links.py:10-33` yourself: `SKIP_PREFIXES` at `:11` is the complete prefix list, the angle-bracket skip is at `:28`, `:30` strips a `#fragment` but not a `:123` suffix, and `:15` excludes `var/` from files SCANNED, which is not the same as exempting `var/` as a target.",
        "Do NOT edit `tests/test_doc_links.py`. Its contract is the gated decision and belongs to the other request.",
        "Re-run the enumeration to confirm you got all six: search `.claude/skills` for `tests/test_[a-z0-9_]+\\.py` and check each hit resolves. Exactly one dead token should remain â€” `tests/test_extract_pagination.py` at `diagnose-bug/SKILL.md:117`, which Phase 4 owns."
      ],
      "acceptance": [
        "`uv run pytest tests/test_skill_references.py -q` -> `test_every_test_file_a_skill_names_exists` no longer reports any `tests/test_request_links.py` line (it may still report the single `test_extract_pagination.py` line until Phase 4).",
        "`uv run pytest tests/test_doc_links.py -q` passes â€” no new broken relative link was introduced by the edits.",
        "Exactly six files changed in this phase, all under `.claude/skills/`. `tests/test_doc_links.py` is NOT among them.",
        "Every statement the four Category-B bullets make about `tests/test_doc_links.py` is true of the file as it exists at `tests/test_doc_links.py:10-33`.",
        "`uv run ruff check .` and `uv run mypy` clean."
      ],
      "commit_note": "Point the six skills at the link guard that actually exists\n\ntests/test_request_links.py has never existed here; the guard is\ntests/test_doc_links.py. The four 'What good looks like' bullets now\ndescribe what that guard really exempts and point at the open doc-link\nrequest, so the gated decision on growing its contract stays open."
    },
    {
      "name": "Phase 4 â€” De-port the residue in diagnose-bug/SKILL.md",
      "goal": "The red repro goes fully GREEN, and the template a cold agent copies from stops teaching a sibling repo's domain and a status word the track does not use. RCA Minimal step 3 + Root step 5.",
      "steps": [
        "Edit `.claude/skills/diagnose-bug/SKILL.md:117-118`: replace `tests/test_extract_pagination.py::test_all_pages_landed` / 'expected 1230 games, got 1000' with an in-domain example naming a test that EXISTS here. Suggested: `tests/test_parse_world.py::test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key` (a real test â€” `tests/test_parse_world.py:179`) failing with 'expected 8 columns, got 7'.",
        "Note WHY the replacement must name a real file even though it sits inside a fenced ```markdown block: `tests/test_skill_references.py` has NO fence awareness (regex at `:32` runs line-by-line over the raw text) â€” that absence is precisely the doc-link defect this repo is still carrying.",
        "Edit the status word at three sites, per `requests/bugfix-requests/README.md:45` and `commit/SKILL.md:133`, which agree the grammar is `intake -> diagnosed -> planned -> fixed`: `:97` `root-cause Â· â€¦ Â· decided Â· next: plan` -> `diagnosed Â· â€¦`; `:107` the template blockquote `> **Status:** root-cause Â· created â€¦` -> `> **Status:** diagnosed Â· created â€¦`; `:150` `header) to \\`root-cause\\` (or the terminal stage word)` -> `` `diagnosed` ``.",
        "Leave `:7` alone â€” that occurrence is in the frontmatter description naming the pipeline shape ('intake -> root-cause -> reuse plan/implement'), not a status word, and rewording frontmatter is a triggering change.",
        "Confirm both live artifacts in this request directory already carry `diagnosed` in their status blockquotes (they do â€” line 1 of each), so the skill and the tree now agree."
      ],
      "acceptance": [
        "`uv run pytest tests/test_skill_references.py -q` -> 2 passed, 0 failed. THE RED REPRO IS GREEN. This is the RCA's acceptance contract.",
        "No `tests/test_[a-z0-9_]+\\.py` token anywhere under `.claude/skills/` names a file that does not exist.",
        "Searching `.claude/skills/diagnose-bug/SKILL.md` for `root-cause` returns only the frontmatter occurrence at `:7`.",
        "`uv run pytest -m \"not gamedata\"` fully green; `uv run ruff check .` and `uv run mypy` clean.",
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` and `node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs` both still exit 0."
      ],
      "commit_note": "Re-ground the diagnose-bug template in this repo\n\nIts worked example cited a pagination test failing on 1,230 games â€” an NBA\nseason, in a save-file parser. Its status word said root-cause where the\ntrack README and /commit both say diagnosed. Both are sibling-repo residue\nin a template cold agents copy from."
    },
    {
      "name": "Phase 5 â€” OPTIONAL, GATED: run the .mjs guards in CI",
      "goal": "Stop the guards from silently rotting red again â€” which is the defect class itself. RCA Hardening step 7, which the RCA explicitly marks *unconfirmed* and says must be measured rather than asserted. Include this phase only if the user disposes Open Question 2 as in-scope.",
      "steps": [
        "MEASURE THE UNCONFIRMED CLAIM FIRST. The RCA's own words: 'GitHub's ubuntu-latest image ships node, so this is plausibly a one-line step â€” unconfirmed, and it should be measured rather than asserted.' Do not build on it. Remove the risk instead of measuring it: add an explicit `actions/setup-node` step rather than relying on a preinstalled runtime.",
        "Read `.github/workflows/ci.yml` in full â€” it is 49 lines, one job `quality`. Existing steps: checkout `:20-24`, install uv `:26-29`, python `:31-32`, sync `:34-35`, ruff lint `:37-38`, ruff format `:40-41`, mypy `:43-44`, pytest `:46-49`.",
        "Insert a `Set up Node` step (pinned major version) and a `Skill guards` step after `:49`, running all three: `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs`, `node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs`, `node .claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs`, `node .claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs`, `node .claude/skills/scope-feature/tests/merge_fallback_guard.mjs`. Chain them so any non-zero exit fails the step â€” do not let a swallowed exit code make the step pass vacuously.",
        "DO NOT change the job's display name at `:17` (`name: Lint, types, tests`). `ops/branch-protection.json` pins the required context to exactly that string, and a rename leaves every PR waiting forever on a check that never reports. If the name genuinely must change, `ops/branch-protection.json` changes in the SAME commit. (This is the panel's own infra-cost rule, `acceptance_panel.js:201` item 5.)",
        "Confirm the guards need no network, no `uv`, and no game install â€” they read only tracked files under `.claude/skills/`, so nothing lands behind the `gamedata` marker and nothing violates ADR 0006.",
        "Prove the step is not vacuous: on the PR, temporarily re-key one fixture entry and confirm the CI step goes red, then revert."
      ],
      "acceptance": [
        "The new CI step runs on the PR and exits 0 with all five guards' GREEN output visible in the log.",
        "`ops/branch-protection.json` still pins `\"Lint, types, tests\"` and the job's `name:` at `.github/workflows/ci.yml:17` is unchanged.",
        "A deliberately re-keyed fixture makes the step exit non-zero (demonstrated once, then reverted) â€” the step fails on the condition it claims to check.",
        "The workflow requires no OOTP install and adds no secret, token, or machine-specific absolute path.",
        "`uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run mypy` all still green locally."
      ],
      "commit_note": "Run the skill guards in CI\n\nThe batching guard was red from the day it landed and nothing noticed,\nwhich is the defect class this request is about. Node is installed\nexplicitly rather than assumed off the runner image; the job display name\nis unchanged so branch protection keeps reporting."
    },
    {
      "name": "Phase 6 â€” Advance the track record",
      "goal": "Leave the requests/ artifacts and the Index agreeing with what actually landed, per `create-implementation-plan/SKILL.md:167-173` and the /commit doc gate.",
      "steps": [
        "Set the Index row Stage cell for `[verify-batching-guard-red-on-arrival]` in `requests/bugfix-requests/README.md:53` to the plan-stage word â€” see Open Question 3 before choosing between `plan` and `planned`.",
        "Do NOT touch the `doc-link-guard-mismatch` row at `:51`: that request's gated decision is still open and this work did not settle it.",
        "Update the status blockquotes on `BUGFIX_REQUEST.md:1` and `ROOT_CAUSE_ANALYSIS.md:1` in this directory to the plan stage, `next: implement`.",
        "Add a short 'What stays open' note recording that the doc-link guard's contract is still undecided and the code-span citation convention remains load-bearing (the RCA already says so at lines 216-222 â€” do not restate it, point at it).",
        "Run `/commit`. Agents commit only through `/commit` â€” never `git commit`, never merge, never amend, never push `main`. The PR stays the user's."
      ],
      "acceptance": [
        "`requests/bugfix-requests/README.md`'s Index row for this slug matches the artifacts' status headers, so the /commit doc gate passes without a drift complaint.",
        "`uv run pytest tests/test_doc_links.py -q` and `uv run pytest tests/test_skill_references.py -q` are green after the artifact edits.",
        "The `doc-link-guard-mismatch` and `leak-guard-blind-to-untracked-files` Index rows are byte-unchanged.",
        "Full local gate green: `uv run pytest -m \"not gamedata\"`, `uv run ruff check .`, `uv run mypy`, plus both implement-plan `.mjs` guards at exit 0."
      ],
      "commit_note": "Advance verify-batching-guard-red-on-arrival to the plan stage\n\nIndex row and artifact status headers moved together; the doc-link\nrequest's row is deliberately untouched â€” its gated decision is still open."
    }
  ],
  "testing": "THE ACCEPTANCE CONTRACT (bugfix track, `requests/bugfix-requests/README.md:25-26`): the red repro goes GREEN + a regression test is left behind + nothing else regresses.\n\nRED REPRO â€” two things, both currently red, both must go green:\n1. `uv run pytest tests/test_skill_references.py` â€” 2 failed today. `test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` clears in Phase 1; `test_every_test_file_a_skill_names_exists` clears in Phases 3+4 (it reports SEVEN dead references â€” six `test_request_links.py`, one `test_extract_pagination.py` â€” so Phase 3 alone leaves it red, which is expected and is not a regression).\n2. `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` â€” exit 1 today with six failure lines; exit 0 from Phase 1 onward. This is the human-readable check and stays the primary symptom test.\n\nREGRESSION TEST LEFT BEHIND: `tests/test_skill_references.py`, already committed on this branch at 0ed70d5 and in CI's `-m \"not gamedata\"` selection. It is DIRECTION-INDEPENDENT by design (docstrings at `:48-54` and `:84-96`) and must NOT be rewritten to fit the fix â€” rewriting it would retire the only signal that would catch the bug again. Phase 2 adds the complementary in-guard half: a fixture key nothing requests fails loudly at the guard's own module scope, which the Python test cannot see (it checks fixture âŠ† panel; direction B checks fixture âŠ† this-run's-roster).\n\nNOTHING ELSE REGRESSES:\n- `node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs` â€” the known-good sibling (`BUGFIX_REQUEST.md:48-50` measured it green). Must stay exit 0 after every phase.\n- `uv run pytest -m \"not gamedata\"` â€” the full CI selection. Nothing in Phases 1-6 touches `src/ootp_ai/`, so the 18 parser/structural modules should be unaffected; if any moves, stop and find out why.\n- `uv run pytest tests/test_doc_links.py` â€” the edits in Phases 3-4 and the plan artifact itself are Markdown; a link whose target does not resolve turns this red. WRITE CITATIONS AS CODE SPANS, not links. This is not stylistic: the guard has no fence awareness (`test_doc_links.py:10`) and does not strip a `:123` suffix (`:30`), so an ordinary `[file] (path.py:42)` citation fails the build. Both RCAs in this diagnosis adopted the code-span convention for exactly this reason.\n- `uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy` â€” mypy is `strict = true` over `files = [\"src\", \"tests\"]` (`pyproject.toml:91-95`), so any Python touched must keep full annotations.\n- `git diff --stat` must show `.claude/skills/implement-plan/acceptance_panel.js` UNCHANGED through every phase. Make this an explicit check, not an assumption: the RCA (lines 122-126) identifies editing the panel to satisfy the guard as the worst available outcome, because it would rename this repo's `parser`/`warehouse` lenses into a sibling's vocabulary and loosen a dedupe (`acceptance_panel.js:317`, the `jaccard >= 0.5` requirement) that is already correct.\n\nPER-PHASE CADENCE (prescribed, not optional): implement -> run the phase's acceptance checks -> `uv run pytest -m \"not gamedata\"` + `uv run ruff check .` + `uv run mypy` green locally -> both `.mjs` guards at exit 0 -> `/commit`, which stages deliberately, runs the doc gate, and asks before writing. CI re-runs the same gates on the PR. Agents never run `git commit` ad hoc, never merge, never amend, never push `main`; subagents get read-only git.\n\nHOW TO PROVE PHASE 2's CHECK ISN'T VACUOUS: copy `verify_batching_guard.mjs` into the scratchpad directory, repoint its `PANEL` const (`:33`) at the tracked panel by absolute path, and mutate one fixture key. This is exactly how the RCA's decisive experiment was run and how the planner independently reproduced it. It touches no repo file.\n\nOUT OF SCOPE, DELIBERATELY: `tests/test_doc_links.py`'s contract (the doc-link request's gated decision), generalising `tests/test_skill_references.py` beyond two token classes (RCA Hardening 6 â€” defer to the doc-link plan, which owns the same hardening item), and a sweep of the remaining ported artifacts for domain residue (RCA Hardening 8 â€” a separate intake).",
  "risks": [
    "THE BIG ONE â€” editing `acceptance_panel.js` to satisfy the guard. It is the outcome both the RCA (lines 122-126) and the BUGFIX_REQUEST's Stage plan (lines 160-165) name as the worst available: it would rename this repo's `parser`/`warehouse` lenses into a sibling's vocabulary and loosen the `jaccard(titleTokens) >= 0.5` merge condition at `acceptance_panel.js:317` that is already correct, silently disabling adversarial verification for every future /implement-plan run. MITIGATION: `git diff --stat` must show the panel unchanged, checked as an explicit acceptance criterion in Phases 1, 2 and 6.",
    "Phase 2's obvious implementation is wrong. Making `reviewFor` throw on an unknown key looks like the natural fix and does nothing: `acceptance_panel.js:139-146` (`safeAgent`) catches every throw and returns null, and `reviewFor` is only ever called for keys the roster already asked for â€” it structurally cannot see an orphaned fixture key. MITIGATION: the assertions live at the guard's module scope, in both directions, and Phase 2 proves each bites by mutating a scratchpad copy.",
    "The fixture edit silently breaks the Python regex. `tests/test_skill_references.py:40` matches `^ {2}'?([a-z0-9-]+)'?:\\s*\\[` â€” exactly two leading spaces â€” and `:75` carves the block on the literals `const FINDINGS_BY_LENS = {` and `\\n}\\n`. Reflowing the object, reindenting, or moving the closing brace off column 0 makes the guard parse zero keys. It would then pass VACUOUSLY on the `unknown = fixture - panel` assertion, which is worse than red. MITIGATION: `:99` already asserts `fixture` is non-empty; keep the edit to the two key tokens and nothing else.",
    "Phase 3 attaches a false promise to a real file. The four Category-B bullets promise fence exemption, `file.py:123` suffixes and `var/` targets â€” none of which `tests/test_doc_links.py` implements (`:11` is the complete prefix list; `:30` strips `#` but not `:123`; `:15` excludes `var/` from files SCANNED, which is a different thing from exempting it as a target). Repointing the NAME alone makes the misinformation more credible, not less. MITIGATION: Open Question 1 must be disposed before Phase 3 is written.",
    "Phase 3 pre-decides someone else's gate. The doc-link request's ruling â€” grow the guard vs. correct the skills â€” is explicitly the one call a fix must not make on its own authority (`doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:79-93`). MITIGATION: the recommended wording DESCRIBES the guard's current behaviour and points at the open request; it does not delete a promise as wrong nor assert it will be honoured, so neither reading gets cheaper.",
    "The plan document and the skill edits can turn `tests/test_doc_links.py` red themselves. Any Markdown link written during this work must resolve on disk with no fence exemption and no `:line` stripping. MITIGATION: code spans everywhere, the convention both RCAs in this diagnosis already adopted and stated at their heads.",
    "Phase 5 rests on an explicitly *unconfirmed* claim â€” that `ubuntu-latest` ships node. The RCA flags it and says measure, don't assert. MITIGATION: install node explicitly with a pinned `actions/setup-node` step rather than relying on the runner image, which removes the claim from the dependency chain instead of testing it.",
    "Phase 5 can stall every future PR. `ops/branch-protection.json` pins the required context to the exact string `\"Lint, types, tests\"` (`.github/workflows/ci.yml:17`). Renaming the job to reflect the new step leaves PRs waiting forever on a check that never reports â€” the failure `ci.yml:13-15` warns about in its own comment. MITIGATION: do not rename; if it must change, both files change in one commit.",
    "Phase 5 can add a vacuous step. A chained `run:` that swallows a non-zero exit passes without checking anything, which is the same class of defect as the standing-red guard. MITIGATION: demonstrate the step going red on a deliberately re-keyed fixture, then revert.",
    "Fixing only Phase 1 and calling it done. `test_every_test_file_a_skill_names_exists` reports seven dead references; Phase 3 clears six and Phase 4 clears the seventh. A run that stops after Phase 3 leaves the repro red and the acceptance contract unmet.",
    "Phase 4's replacement example must name a file that exists even though it sits inside a fenced ```markdown block â€” `tests/test_skill_references.py:32` has no fence awareness. Naming an invented test there re-creates the exact defect being fixed. `tests/test_parse_world.py:179` is a verified real target."
  ],
  "files_to_touch": [
    {
      "path": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs",
      "change": "Phase 1: `:54` `'data-contract': [` -> `warehouse: [`; `:58` `extraction: [` -> `parser: [`; `:150` comment `-> data-contract + extraction + skill-quality specialists` -> `-> warehouse + parser + skill-quality specialists`. Keep two-space indent and the column-0 closing brace at `:64`. Phase 2: after `:66`, derive the panel's lens keys from `SRC` and hard-exit on an unknown fixture key; add `REQUESTED.add(lensKey)` at `:78` and assert after Scenario 1 that every fixture key was requested; extend the header comment block `:1-27` with the new pinned property."
    },
    {
      "path": ".claude/skills/implement-plan/acceptance_panel.js",
      "change": "DO NOT EDIT â€” read only. Proven correct by the RCA's experiment and independently re-verified by the planner. Its roster (`:189-209`), `safeAgent` (`:139-146`) and `dedupeFindings` (`:312-333`) are the constraints Phases 1-2 are written against. Any diff here is a stop-the-line signal."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "change": "Phase 3, Category A: `:104` `uv run pytest tests/test_request_links.py -q` -> `tests/test_doc_links.py`. Nothing else. (`:133`'s status grammar is already correct and is the authority Phase 4 cites.)"
    },
    {
      "path": ".claude/skills/update-docs/SKILL.md",
      "change": "Phase 3, Category A: `:56` `uv run pytest tests/test_request_links.py -q` -> `tests/test_doc_links.py`. Nothing else."
    },
    {
      "path": ".claude/skills/make-bugfix-request/SKILL.md",
      "change": "Phase 3, Category B: `:199` repoint to `tests/test_doc_links.py` and apply the Open Question 1 disposition to the three exemption promises in the same bullet (`:199-204`)."
    },
    {
      "path": ".claude/skills/make-feature-request/SKILL.md",
      "change": "Phase 3, Category B: `:246` repoint to `tests/test_doc_links.py` and apply the same disposition to its bullet (`:245-250`). Note this file's variant omits the 'link titles' clause the other three carry."
    },
    {
      "path": ".claude/skills/create-implementation-plan/SKILL.md",
      "change": "Phase 3, Category B: `:251` repoint to `tests/test_doc_links.py` and apply the same disposition to its bullet (`:250-256`). Self-referential â€” this is the skill that produced this plan."
    },
    {
      "path": ".claude/skills/diagnose-bug/SKILL.md",
      "change": "Phase 3, Category B: `:176` repoint + disposition. Phase 4: `:117-118` replace the `tests/test_extract_pagination.py::test_all_pages_landed` / '1230 games' example with an in-domain one naming a real file (`tests/test_parse_world.py:179` is verified); `:97`, `:107`, `:150` `root-cause` -> `diagnosed`. Leave `:7` (frontmatter description) alone."
    },
    {
      "path": ".github/workflows/ci.yml",
      "change": "Phase 5 ONLY, gated on Open Question 2. Append an explicit `actions/setup-node` step plus a step chaining the five `.mjs` guards after `:49`. Do NOT change `name: Lint, types, tests` at `:17` â€” `ops/branch-protection.json` pins that exact string. File is 49 lines, one job."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md",
      "change": "NEW â€” the stage-3 deliverable, written from the section menu at `.claude/skills/create-implementation-plan/SKILL.md:175-231`. Sections 1-8 + 10 + References; SECTION 9 (data contracts) IS OMITTED â€” this change adds no source, no dataset, no grain, and touches nothing under `src/ootp_ai/` or `transform/`. Status blockquote per `requests/bugfix-requests/README.md:43`."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "Phase 6: this slug's Index row Stage cell at `:53` -> the plan-stage word (see Open Question 3). Leave `:51` (doc-link) and `:52` (leak-guard) byte-unchanged."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md",
      "change": "Phase 6: status blockquote at `:1` advanced to the plan stage, `next: implement`."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md",
      "change": "Phase 6: status blockquote at `:1` advanced. Body is DECIDED â€” do not revise the verdict, the evidence or the fix posture."
    },
    {
      "path": "tests/test_skill_references.py",
      "change": "DO NOT EDIT. The committed, direction-independent red repro (landed at 0ed70d5). Rewriting it to fit the fix retires the only guard that catches this class. Read `:32`, `:37`, `:40`, `:75` â€” they constrain how the .mjs fixture may be edited."
    },
    {
      "path": "tests/test_doc_links.py",
      "change": "DO NOT EDIT. Its contract is the gated decision owned by `requests/bugfix-requests/_done/doc-link-guard-mismatch/`. Read `:10-33` to state its behaviour accurately in Phase 3."
    }
  ],
  "code_references": [
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:54",
      "claim": "`  'data-contract': [` â€” a fixture lens keyed to a sibling repo's specialist. Contributes 2 findings that never enter the run. Phase 1 renames it to `warehouse:`, preserving the two-space indent."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:58",
      "claim": "`  extraction: [` â€” the second orphaned lens, contributing the 1 finding (`src/ootp_ai/land/writer.py:60`) whose absence the guard misreports as an over-merge. Phase 1 renames it to `parser:`."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:78",
      "claim": "`const spec = FINDINGS_BY_LENS[lensKey] || []` â€” the silent swallow. An unknown key returns an empty review: no throw, no warning, no undefined. This is the mechanism Phase 2 closes; `REQUESTED.add(lensKey)` goes here, but the assertion does NOT."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:150",
      "claim": "`touchedAreas: ['transform', 'src', 'skills'],   // -> data-contract + extraction + skill-quality specialists` â€” the comment still teaches the wrong lens names. Phase 1 corrects it to `warehouse + parser + skill-quality`."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:65-66",
      "claim": "`RAW_TOTAL` (11) and `DEDUPED_TOTAL` (9) are computed from the fixture object, which is why the guard's expectations were right and its inputs were wrong. Phase 2 inserts the roster-derivation check immediately after these."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:172",
      "claim": "`if (label.startsWith('review:')) return reviewFor(label.slice('review:'.length))` â€” the stub dispatches on the panel's REAL label, which is why the fixture must speak the panel's vocabulary rather than the reverse."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:199-209",
      "claim": "The six failing assertions. `:199` `raw !== RAW_TOTAL`, `:200` `deduped !== DEDUPED_TOTAL`, `:202` `merged.length !== 2`, `:208` the false over-merge on writer.py, `:212` coverage, and `:281` the verifyCap comparison â€” all downstream of the 3 lost findings."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:33-34",
      "claim": "`const PANEL = join(HERE, '..', 'acceptance_panel.js')` and `const SRC = readFileSync(PANEL, 'utf8')` â€” Phase 2 reuses this already-loaded source to derive the roster, and the scratchpad verification technique repoints `PANEL` at an absolute path."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:196-202",
      "claim": "`SPEC_DEFS` â€” the specialist roster this repo actually defines: `parser`, `warehouse`, `builder`, `skill-quality`, `infra-cost`. Neither `data-contract` nor `extraction` appears."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:203-207",
      "claim": "`AREA_TO_SPEC` â€” `src: ['parser','warehouse']`, `transform: ['warehouse']`, `skills: ['skill-quality']`. This is what makes `warehouse`/`parser` the only correct re-key for `touchedAreas: ['transform','src','skills']`."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:139-146",
      "claim": "`safeAgent` â€” `try { return await agent(...) } catch { log(...); return null }`. Every throw inside the stub agent is swallowed, which is why Phase 2's assertion must live at the guard's module scope rather than inside `reviewFor`."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:317",
      "claim": "`const hit = out.find(o => o._loc === loc && jaccard(o._toks, toks) >= 0.5)` â€” the dedupe requires title overlap in addition to a matching normalized location, which is exactly why `writer.py:42` and `writer.py:60` are correctly kept apart. Loosening this to satisfy the guard is the worst available outcome."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:298-301",
      "claim": "`normLocation` strips a trailing `:line` â€” the reason two findings in the same file share a bucket, and the half of the dedupe the guard's over-merge complaint appeared to indict."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:200",
      "claim": "The skill-quality specialist mandate already names `tests/test_doc_links.py` as the mechanical link check â€” independent in-repo confirmation that it, not `test_request_links.py`, is Phase 3's correct target."
    },
    {
      "ref": ".claude/skills/implement-plan/SKILL.md:309",
      "claim": "The guard's stated contract: exit 0 = the Verify phase stays under its cap, merges only true duplicates ... 'Run it whenever acceptance_panel.js or this file changes.' The instruction is currently un-followable; Phase 1 makes it followable."
    },
    {
      "ref": "tests/test_skill_references.py:37",
      "claim": "`LENS_KEY = re.compile(r\"\\bkey:\\s*'([a-z0-9-]+)'\")` â€” the panel-roster derivation Phase 2 mirrors in JavaScript, so the roster keeps one home instead of gaining a hardcoded copy."
    },
    {
      "ref": "tests/test_skill_references.py:40",
      "claim": "`FIXTURE_LENS = re.compile(r\"^ {2}'?([a-z0-9-]+)'?:\\s*\\[\", re.MULTILINE)` â€” requires EXACTLY two leading spaces on a fixture key. Constrains the Phase 1 edit; quoted and unquoted both parse."
    },
    {
      "ref": "tests/test_skill_references.py:75",
      "claim": "`source.split(\"const FINDINGS_BY_LENS = {\", 1)[1].split(\"\\n}\\n\", 1)[0]` â€” the fixture block is carved by literal delimiters, so the opening line and the column-0 closing brace at the guard's `:64` must survive the edit unchanged."
    },
    {
      "ref": "tests/test_skill_references.py:32",
      "claim": "`TEST_REFERENCE = re.compile(r\"tests/test_[a-z0-9_]+\\.py\")` applied line-by-line with no fence awareness â€” which is why Phase 4's replacement example must name a real file even inside a fenced ```markdown block."
    },
    {
      "ref": "tests/test_doc_links.py:11",
      "claim": "`SKIP_PREFIXES = (\"http://\", \"https://\", \"mailto:\", \"#\")` â€” the complete exemption list, plus the angle-bracket placeholder skip at `:28`. The three exemptions four skills promise are absent, which Phase 3's wording must not misstate."
    },
    {
      "ref": "tests/test_doc_links.py:30",
      "claim": "`clean = target.split(\"#\", 1)[0].strip()` â€” a `#fragment` is stripped, a `:123` line suffix is not, so an ordinary `file.py:42` citation written as a link fails the build. The reason every citation in this plan is a code span."
    },
    {
      "ref": "tests/test_doc_links.py:15",
      "claim": "`\"var\" not in p.parts` excludes `var/` from the files SCANNED â€” not from valid link TARGETS. Two different exemptions; Phase 3's prose must not conflate them."
    },
    {
      "ref": ".claude/skills/diagnose-bug/SKILL.md:117-118",
      "claim": "`tests/test_extract_pagination.py::test_all_pages_landed` ... `(fails: expected 1230 games, got 1000)` â€” sibling-repo residue in a template cold agents copy from. There is no pagination in a save-file parser and 1,230 is an NBA regular season."
    },
    {
      "ref": ".claude/skills/diagnose-bug/SKILL.md:97",
      "claim": "``**`confirmed-bug`** -> `root-cause Â· â€¦ Â· decided Â· next: plan` `` â€” the status word the track does not use."
    },
    {
      "ref": ".claude/skills/diagnose-bug/SKILL.md:107",
      "claim": "`> **Status:** root-cause Â· created <YYYY-MM-DD> Â· decided Â· next: <plan | fix | none | <feature-slug>>` â€” the template blockquote a cold agent copies verbatim."
    },
    {
      "ref": ".claude/skills/diagnose-bug/SKILL.md:150",
      "claim": "``header) to `root-cause` (or the terminal stage word)`` â€” the third site, in the Step-5 record instruction."
    },
    {
      "ref": "requests/bugfix-requests/README.md:45",
      "claim": "`**Status grammar:** intake -> diagnosed -> planned -> fixed` â€” the track contract, and per `requests/README.md:12` the authority over the skill. Phase 4 aligns the skill to it."
    },
    {
      "ref": ".claude/skills/commit/SKILL.md:133",
      "claim": "`bugfix work runs intake -> diagnosed -> planned -> fixed` â€” the second artifact agreeing with the track README against the skill, making it two-against-one."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:172-173",
      "claim": "Step 5 instructs setting the Index Stage cell to `plan` and opening the plan at stage `plan` â€” which does not match the bugfix track's `planned`. A fourth instance of the same drift class, surfaced during planning; see Open Question 3."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:219-222",
      "claim": "Section 9 (data contracts) is `[Conditional â€” only if the feature adds/edits a dataset]`. This change adds none, so the plan omits it â€” a deliberate menu choice, not an oversight."
    },
    {
      "ref": ".github/workflows/ci.yml:46-49",
      "claim": "The pytest step, `run: uv run pytest -m \"not gamedata\"`. The repro module is in this selection, so the regression guard runs on every PR. The file has 49 lines and no node step."
    },
    {
      "ref": ".github/workflows/ci.yml:13-17",
      "claim": "`# Job display names are matched by ops/branch-protection.json ... Change both in the same commit.` followed by `name: Lint, types, tests`. `ops/branch-protection.json` pins that exact string in `required_status_checks.contexts` â€” Phase 5 must not rename it."
    },
    {
      "ref": "pyproject.toml:91-95",
      "claim": "`[tool.mypy]` with `strict = true` and `files = [\"src\", \"tests\"]` â€” the repro module is under strict typing, so any Python edited in these phases must keep full annotations."
    },
    {
      "ref": "tests/test_parse_world.py:179",
      "claim": "`def test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key() -> None:` â€” a real, in-domain test that resolves, suitable as Phase 4's replacement for the NBA pagination example."
    },
    {
      "ref": "requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:95-98",
      "claim": "'step 2 is common to both readings and is the only part safe to do early' â€” the explicit authority for Phase 3 correcting the six references without pre-deciding the gated decision at that document's `:82-93`."
    }
  ],
  "open_questions": [
    "GATED â€” how far does Phase 3 go on the four Category-B bullets? Repointing `tests/test_request_links.py` -> `tests/test_doc_links.py` is safe under both readings of the doc-link gate. But those same bullets (`make-bugfix-request/SKILL.md:199-204`, `make-feature-request/SKILL.md:245-250`, `diagnose-bug/SKILL.md:176-181`, `create-implementation-plan/SKILL.md:250-256`) promise three exemptions the real guard does not implement, and attaching a false promise to a REAL file is arguably worse than a dangling name. RECOMMENDATION: repoint the name and replace the promises with a factual description of `tests/test_doc_links.py:10-33` as it exists plus a bare pointer to the open request â€” a description of the current state, not a ruling, so neither reading of the gate becomes cheaper. ALTERNATIVE: repoint the name only and leave the promises untouched, deferring everything to the doc-link plan. The user disposes.",
    "SCOPE â€” is Phase 5 (running the `.mjs` guards in CI) in or out? The RCA files it under Hardening, 'worth considering, not assumed'. IN FAVOUR: the guard was red from the day it arrived and nothing noticed for the life of the skill â€” that IS the defect class, and `tests/test_skill_references.py` only catches lens-key drift, not a guard that breaks for any other reason. AGAINST: it widens a bugfix into CI work and the RCA's supporting claim (that `ubuntu-latest` ships node) is explicitly *unconfirmed*. RECOMMENDATION: include it, with node installed explicitly rather than assumed â€” that removes the unconfirmed claim from the dependency chain instead of merely testing it.",
    "A FOURTH INSTANCE, found while planning (not in the RCA). `create-implementation-plan/SKILL.md:172-173` instructs setting the Index Stage cell to `plan` and opening the plan at stage `plan`, but the bugfix track grammar at `requests/bugfix-requests/README.md:45` and `commit/SKILL.md:133` is `intake -> diagnosed -> planned -> fixed` â€” `planned`, not `plan`. Same class as the `root-cause`/`diagnosed` mismatch Phase 4 fixes. Should Phase 6 write `planned` (following the track README, per `requests/README.md:12`), and should the skill be corrected in this request or filed as a fourth intake? RECOMMENDATION: write `planned` in Phase 6 and file the skill correction separately, so this request does not grow a fourth unrelated edit.",
    "Should Phase 2's direction-A check live in the `.mjs` at all, given `tests/test_skill_references.py::test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` already enforces it in CI? ARGUMENT FOR: the confusing miscount surfaces in the `.mjs` output, so that is where the honest diagnosis belongs â€” and direction B (a key valid in the panel but not requested by this run's roster) is not covered by the Python test at all. ARGUMENT AGAINST: two enforcement points for one invariant. RECOMMENDATION: keep both, since neither restates the roster â€” both derive it from `acceptance_panel.js`.",
    "The RCA's Hardening 6 (generalise `tests/test_skill_references.py` from two token classes to every repo path a skill names) appears in BOTH RCAs (`doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:104-106`). Confirm it is deferred to the doc-link plan rather than done twice or dropped by each request assuming the other owns it.",
    "RCA Hardening 8 â€” a deliberate sweep for remaining sibling-repo domain residue. Two instances turned up by accident in one sitting, plus the fourth above during planning, which is now weak-but-growing evidence a sweep would find more. Out of scope here; should it be filed as a new intake before this request closes?"
  ]
}
```

## Proposal 2 â€” sequencing

```json
{
  "planner": "sequencing",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Its Verdict (the fixture is wrong, the panel is correct), its per-failure-line table, and its tiered fix posture (Minimal 1-3, Root 4-5, Hardening 6-8) are the spine of every phase below. CONSUME it; do not re-open which side is wrong â€” that was settled by experiment at its lines 102-115."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md",
      "why": "Context only. Its Open Questions are all answered by the RCA; read it for the original six failure lines (lines 22-29) so you recognise the RED output when you reproduce it."
    },
    {
      "path": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs",
      "why": "The defective artifact â€” 293 lines, the only file Phases 1 and 2 touch. The fixture is `FINDINGS_BY_LENS` at lines 40-64; the silent-swallow is `FINDINGS_BY_LENS[lensKey] || []` at line 78; the stale teaching comment is at line 150."
    },
    {
      "path": ".claude/skills/implement-plan/acceptance_panel.js",
      "why": "The code under test, and the file you MUST NOT change. Read `CORE` (lines 189-194), `SPEC_DEFS` (196-202) and `AREA_TO_SPEC` (203-207) to see why the panel's lenses for `touchedAreas: ['transform','src','skills']` are warehouse + parser + skill-quality. Read `dedupeFindings` (312-323) to confirm the jaccard >= 0.5 gate at line 317 is already correct."
    },
    {
      "path": "tests/test_skill_references.py",
      "why": "The committed red repro â€” the acceptance contract of this whole plan. Two tests: `test_every_test_file_a_skill_names_exists` (line 47) and `test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` (line 84). Both RED today. Note its `FIXTURE_LENS` regex at line 40 â€” it matches two-space-indented, optionally-quoted keys, so the Phase 1 re-key stays parseable."
    },
    {
      "path": "requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md",
      "why": "The sibling RCA that OWNS the gated decision this plan must not make. Its lines 79-98 establish that repointing the six references is common to BOTH readings (safe here), while the exemption/bare-token/promise-prose work is gated (out of scope here)."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The track contract. Line 45 carries the status grammar `intake -> diagnosed -> planned -> fixed` that Phase 4 enforces, and line 24 states the bugfix definition of done: red repro green + regression test left behind."
    },
    {
      "path": "tests/test_doc_links.py",
      "why": "39 lines, the guard that actually exists. Read it to understand why every citation in the plan document you write must be a CODE SPAN and never a Markdown link: `LINK` at line 10 has no fence awareness, and line 30 strips a `#fragment` but not a `:123` line suffix."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "The CI contract Phases 5-6 touch. The single `quality` job's display name is at lines 19-20; the four gates are ruff (37-38), ruff format (40-41), mypy (43-44), pytest with `-m \"not gamedata\"` (46-49). There is NO node step today â€” that absence is the whole of Hardening item 7."
    },
    {
      "path": "tests/test_no_leaks.py",
      "why": "Read before writing the plan document or any note: line 25 bans a Windows drive path in ANY tracked text file. The scratchpad recipes in Phases 2 and 6 use absolute paths â€” those live in your scratchpad only and must never be pasted into a tracked artifact."
    }
  ],
  "architecture_notes": "WHAT THIS CHANGE IS. A tooling repair, entirely inside `.claude/skills/` plus one pytest module and (optionally) one CI step. It touches no parser, no dbt model, no dataset, no game data, and no save file. The parser/ground-truth/fixed-offset/manifest conventions therefore do NOT apply and must not be padded into the plan; three conventions DO apply and are listed in the Conventions section.\n\nTHE MECHANISM, IN ONE PARAGRAPH. `verify_batching_guard.mjs` loads `acceptance_panel.js` as text at its line 34 and executes it inside a `new Function(...)` at lines 155-159, feeding it a stub `agent`. The stub dispatches reviewer calls at line 172 via `reviewFor(label.slice('review:'.length))`, and `reviewFor` at line 78 resolves the fixture with `FINDINGS_BY_LENS[lensKey] || []`. The panel, for the guard's `touchedAreas: ['transform','src','skills']` (line 150), assembles its roster from `CORE` (acceptance, fidelity, correctness, edgecases â€” `acceptance_panel.js:189-194`) plus specialists resolved through `AREA_TO_SPEC` (`:203-207`): transform -> warehouse, src -> parser+warehouse, skills -> skill-quality. So the panel asks for exactly `fidelity, correctness, edgecases, warehouse, parser, skill-quality`. The fixture is keyed `fidelity, correctness, edgecases, 'data-contract', extraction, 'skill-quality'`. Two keys are a sibling repo's vocabulary; `|| []` returns an empty review for each, three of eleven findings never enter the run, and all six failure lines follow.\n\nVERIFIED INDEPENDENTLY BY THIS PLANNING PASS (measured 2026-08-17). I copied the guard to a scratchpad, repointed only its `HERE` constant, re-keyed `'data-contract' -> warehouse` and `extraction -> parser`, and ran it with `acceptance_panel.js` byte-untouched. Output: `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` ... `GREEN`, exit 0. The RCA's decisive experiment reproduces. The minimal fix is two words and it is proven, not argued.\n\nBASELINE, MEASURED TODAY, so every phase has a number to move. `uv run pytest -m \"not gamedata\"` -> `2 failed, 170 passed, 62 deselected`; the two failures are exactly the repro module. `uv run ruff check .` -> All checks passed. `uv run ruff format --check .` -> 115 files already formatted. `uv run mypy` -> Success, 38 source files. The other four skill guards (`create-implementation-plan/tests/merge_failure_repro.mjs`, `create-implementation-plan/tests/merge_fallback_guard.mjs`, `implement-plan/tests/merge_fallback_guard.mjs`, `scope-feature/tests/merge_fallback_guard.mjs`) all exit 0. Local node is v24.15.0.\n\nTWO INDEPENDENT DEFECT FAMILIES SHARE THIS SLUG, AND THEY SEQUENCE DIFFERENTLY. (A) The batching-guard fixture â€” proven, self-contained, zero gating: Phases 1-2. (B) The stale cross-references the repro's first test catches â€” six `tests/test_request_links.py` pointers plus a `tests/test_extract_pagination.py` example and a status-word drift: Phases 3-4. Family B sits adjacent to the doc-link request's GATED decision, so this plan does the part both readings share (repoint the pointer at the guard that exists) and deliberately does NOT touch the promise prose around it.\n\nWHERE THE PLAN DELIBERATELY IMPROVES ON THE RCA'S ROOT ITEM 4. The RCA suggests deriving the fixture's expected lens keys by reading them out of `acceptance_panel.js`. `tests/test_skill_references.py:79-81` already does exactly that in Python, with a regex (`LENS_KEY`, line 37) that can drift. Doing it a second time inside the `.mjs` would be a second regex on the same source. The guard has something strictly better available: it already records every agent call in `calls` (`verify_batching_guard.mjs:163-166`), so it can assert against the labels the panel ACTUALLY dispatched. No regex, no second copy of the roster, and it fails in the exact direction that matters â€” a fixture key nobody asked for. That is the Phase 2 design.\n\nA SEVENTH DRIFT INSTANCE FOUND WHILE GROUNDING (the RCA names six references plus the pagination example plus the status word). `make-bugfix-request/SKILL.md:130` templates `> **Status:** intake ... next: root-cause`, and `create-implementation-plan/SKILL.md:56` and `:65` both teach `root-cause` as the disposition-gate stage word. Fixing only `diagnose-bug/SKILL.md` leaves three files still teaching the wrong grammar. Phase 4 covers all of them.\n\nCITATION CONVENTION FOR THE PLAN DOCUMENT ITSELF. Write every `file:line` as a code span, never as a Markdown link. `tests/test_doc_links.py` is a blocking CI check and resolves relative link targets with no fence awareness (`:10`) and no `:123` suffix stripping (`:30`), so the ordinary shape turns CI red. Both RCAs and the first-sight plan already do this. This is a workaround for the doc-link defect, not a fix for it.",
  "phases": [
    {
      "name": "Phase 1 â€” Re-key the batching guard's fixture to this repo's lenses (the proven minimal fix)",
      "goal": "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 for the first time in this repo's history, and the repro's second test goes green â€” with `acceptance_panel.js` byte-untouched. This is the RCA's Minimal step 1, already proven green twice (RCA lines 102-115, and re-measured during planning).",
      "steps": [
        "Reproduce the RED first, so you have the before/after in hand: run `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` and record the six failure lines and exit 1. Then run `uv run pytest -m \"not gamedata\"` and record `2 failed, 170 passed, 62 deselected`.",
        "In `.claude/skills/implement-plan/tests/verify_batching_guard.mjs`, edit line 54 exactly: `  'data-contract': [` becomes `  warehouse: [`. The quotes go away because `warehouse` needs none; `tests/test_skill_references.py:40`'s `FIXTURE_LENS` regex matches quoted and unquoted alike, so either form parses.",
        "Edit line 58 exactly: `  extraction: [` becomes `  parser: [`.",
        "Edit the stale teaching comment at line 150. `    touchedAreas: ['transform', 'src', 'skills'],   // -> data-contract + extraction + skill-quality specialists` becomes `... // -> warehouse + parser + skill-quality specialists`. This comment is how the next reader learns the wrong names; leaving it re-seeds the defect.",
        "Leave the inline trailing comments at lines 55 (`// dup of fidelity[1]`) and 59 (`// same file, different bug`) alone â€” they describe the fixture's shape, which is unchanged, and they are the reason the dedupe assertions are meaningful.",
        "Judgment call, surfaced as an open question rather than done silently: the header comment at line 13 says findings arrive 'across 7 lenses' while the fixture defines 6. Correct to 6 only if the user says so.",
        "DO NOT open `.claude/skills/implement-plan/acceptance_panel.js` for editing. The RCA's whole verdict is that the panel is correct; a diff there means you fixed the wrong side. Its dedupe at `:312-323` â€” specifically the `jaccard(o._toks, toks) >= 0.5` gate at `:317` â€” is the property the guard falsely accused it of violating."
      ],
      "acceptance": [
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0. Paste the stdout; its first line must read exactly `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` and the last must start `GREEN:`. The numbers are the check â€” a green exit with `raw=8` would mean something else changed.",
        "`uv run pytest tests/test_skill_references.py::test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines -q` passes.",
        "`uv run pytest -m \"not gamedata\"` reports `1 failed, 171 passed, 62 deselected` â€” exactly one net test flipped, and the remaining failure is `test_every_test_file_a_skill_names_exists`, Phase 3's target. Any other movement is an unintended regression.",
        "`git diff --stat` (a read; permitted) lists `.claude/skills/implement-plan/tests/verify_batching_guard.mjs` and nothing else. `acceptance_panel.js` must not appear.",
        "The three sibling guards still exit 0: `.claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/implement-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/scope-feature/tests/merge_fallback_guard.mjs`. They share the panel harness, so they are the cross-check that nothing structural moved.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all green (no Python changed, so these should be unchanged from baseline)."
      ],
      "commit_note": "Checkpoint. Hand to the user with `/commit` â€” never `git commit` ad hoc. Suggested message: `fix(skills): re-key the batching guard's fixture to this repo's lenses`. The body should carry the before/after diagnostic lines (`raw=8` -> `raw=11`) because that pair is the evidence the fix is the right one. Fully reversible: two words and a comment."
    },
    {
      "name": "Phase 2 â€” Make an unasked fixture lens fail loudly instead of miscounting (the root fix)",
      "goal": "The mechanism that hid this defect for the guard's entire life cannot hide the next roster rename. A fixture key the panel never asks for must produce a named, self-explaining failure â€” not a silent zero-finding review that surfaces downstream as a miscount blamed on the code under test.",
      "steps": [
        "Read `verify_batching_guard.mjs:163-179` (`makeAgent`) to confirm every agent call is recorded into `calls` as `{ label, prompt }`. This is the observation channel the assertion uses.",
        "In Scenario 1 (the block at lines 185-226), after `const r = await runPanel(makeAgent(calls), makeArgs())`, derive what the panel actually asked for: collect the review labels out of `calls`, strip the `review:` prefix, and build a Set.",
        "Add a failure for every key in `Object.keys(FINDINGS_BY_LENS)` that is NOT in that Set. Push it onto the existing `fails` array (declared at line 181) so it prints through the existing RED reporter at lines 285-292. The message must name the offending key AND list the lenses the panel did ask for â€” the reader's next question is always 'then what should it be?'.",
        "Place this assertion FIRST in Scenario 1's checks, before the cap/dedupe assertions at lines 193-217. Ordering matters: an unasked lens invalidates every count below it, so it should be the first line the reader sees, not the seventh.",
        "Deliberately KEEP `|| []` at line 78. Do not throw inside `reviewFor`. A throw there aborts the run inside `pipeline`/`parallel`'s catch handlers (lines 132-141) and you lose every diagnostic line â€” the loudness belongs in the assertion, which prints, not in the lookup, which is swallowed by design.",
        "Prefer this call-observation form over regexing `acceptance_panel.js` for its lens keys. `tests/test_skill_references.py:79-81` already carries a regex over that source (`LENS_KEY`, line 37); a second one in the `.mjs` is a second thing to drift. Record this as a plan decision â€” it is a conscious deviation from the RCA's Root item 4 phrasing, achieving the same one-home property by a sturdier route."
      ],
      "acceptance": [
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` still exits 0 with the same four diagnostic lines as Phase 1. The new assertion must be inert on a correct tree.",
        "PROVE IT IS NOT VACUOUS â€” this is the acceptance criterion that matters, and the repo's own infra-cost mandate (`acceptance_panel.js:201`, item 4) names a vacuously-passing check as worse than none. Copy the guard to your scratchpad directory, replace its `HERE` constant (line 32) with an absolute path to `.claude/skills/implement-plan/tests` so it still resolves the real tracked panel, then re-break the copy by renaming `warehouse:` back to `'data-contract':`. Run the copy: it must exit 1 AND the FIRST printed failure must name `data-contract` as a lens the panel never asked for. Paste that output as evidence.",
        "Do the same negative check for `parser` -> `extraction`. Both keys, not just one â€” a one-sided assertion is how the original defect had two instances and one symptom.",
        "The scratchpad copy stays in the scratchpad. `git status --porcelain` (a read) shows only `verify_batching_guard.mjs` modified. Do NOT paste the absolute scratchpad path into any tracked file â€” `tests/test_no_leaks.py:25` bans a Windows drive path in tracked text and it is a blocking CI check.",
        "`uv run pytest -m \"not gamedata\"` still `1 failed, 171 passed, 62 deselected` (no Python changed). The three sibling `.mjs` guards still exit 0. ruff / ruff format / mypy green."
      ],
      "commit_note": "Checkpoint. `/commit`. Suggested message: `fix(skills): the batching guard names an unasked fixture lens instead of miscounting`. Put the re-broken-copy output in the body â€” it is the proof the new assertion bites. Reversible: the assertion is additive and deleting it returns to Phase 1's state."
    },
    {
      "name": "Phase 3 â€” Point the six stale references at the guard that exists, and re-ground the pagination example",
      "goal": "The repro's first test goes green, which completes this slug's acceptance contract: `uv run pytest tests/test_skill_references.py` -> 2 passed. Six skills stop instructing agents to run a file that has never existed, and `diagnose-bug`'s worked example stops teaching a sibling repo's domain.",
      "steps": [
        "This phase is the RCA's Minimal step 2, which its own text flags as 'the one step that must not move first'. That is an ORDERING constraint, and it is satisfied: Phases 1-2 are landed and committed before this begins.",
        "Replace the token `tests/test_request_links.py` with `tests/test_doc_links.py` at exactly six sites, each verified by grep during planning: `.claude/skills/commit/SKILL.md:104`, `.claude/skills/create-implementation-plan/SKILL.md:251`, `.claude/skills/diagnose-bug/SKILL.md:176`, `.claude/skills/make-bugfix-request/SKILL.md:199`, `.claude/skills/make-feature-request/SKILL.md:246`, `.claude/skills/update-docs/SKILL.md:56`.",
        "Re-ground the sibling-repo example at `.claude/skills/diagnose-bug/SKILL.md:117-118`. It currently cites `tests/test_extract_pagination.py::test_all_pages_landed` failing with 'expected 1230 games, got 1000' â€” there is no pagination in a save-file parser and 1,230 is an NBA regular season. Replace with a real module and a real test name from this repo, e.g. `tests/test_doc_links.py::test_relative_links_resolve`, and a failure message in this domain. Whatever you cite MUST exist on disk, because `test_every_test_file_a_skill_names_exists` will now be green and will police it forever.",
        "DO NOT TOUCH THE PROSE AROUND THOSE REFERENCES. The 'What good looks like' bullets that promise fenced-content exemption, `file.py:123` suffixes, `var/` targets, and a bare-`requests/...`-token scan (see `.claude/skills/create-implementation-plan/SKILL.md:250-256` as the canonical instance) are the subject of the GATED decision in `requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:79-93`. Editing them here decides that call by implication, which both RCAs name as the worst available outcome. Change the reference token only.",
        "The repoint is safe under BOTH readings of that gated decision: `doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:95-98` states that correcting the references is common to (a) and (b), and both RCAs argue against renaming the guard to `test_request_links.py` (it scans all Markdown, not just `requests/`). Record this reasoning in the plan's Decisions section so the next reader does not re-litigate it."
      ],
      "acceptance": [
        "`uv run pytest tests/test_skill_references.py -q` -> `2 passed`. THE RED REPRO IS NOW FULLY GREEN â€” this is the bugfix track's definition of done per `requests/bugfix-requests/README.md:24`, together with the regression guard the repro module itself is.",
        "`uv run pytest -m \"not gamedata\"` -> `172 passed, 62 deselected`, zero failures. Compare against the recorded baseline of `2 failed, 170 passed`.",
        "`grep -rn \"test_request_links\\|test_extract_pagination\" .claude/ requests/ docs/ *.md` returns nothing outside the two RCA documents, which quote the strings as evidence of the defect and must keep them.",
        "Review `git diff -U0 .claude/skills/` line by line and confirm every changed line is either the reference token or the pagination example. If a promise-prose line appears in that diff, revert it â€” you have crossed into the gated decision.",
        "The four `.mjs` guards still exit 0; ruff / ruff format / mypy green."
      ],
      "commit_note": "Checkpoint, and the most important one â€” this is the commit where the RCA's acceptance contract is met. `/commit`. Suggested message: `fix(skills): point the six stale link-guard references at tests/test_doc_links.py`. The body should state explicitly that the doc-link gated decision was NOT taken here and remains with its own request, so the trail survives. `/commit`'s doc gate will also want the `requests/bugfix-requests/README.md` Index row for this slug advanced â€” let it."
    },
    {
      "name": "Phase 4 â€” Settle the bugfix status-word grammar against the track README, with a guard",
      "goal": "The skill stops emitting a status word the track contract does not define, and a test stops it coming back. The RCA's Root item 5, widened to the three additional sites found while grounding this plan.",
      "steps": [
        "Establish the contract: `requests/bugfix-requests/README.md:45` gives the grammar `intake -> diagnosed -> planned -> fixed`, and `requests/README.md:12` says each track's README IS the contract. That is the authority; the skills are the consumers.",
        "Fix `.claude/skills/diagnose-bug/SKILL.md` at three sites: `:97` (`root-cause` in the confirmed-bug disposition), `:107` (the Status blockquote template), and `:150` (the instruction to advance the Index row 'to `root-cause`'). All three become `diagnosed`.",
        "Fix `.claude/skills/make-bugfix-request/SKILL.md:130` â€” its template reads `> **Status:** intake ... next: root-cause`, which should be `next: diagnosed`. Found during planning; the RCA does not enumerate it.",
        "Fix `.claude/skills/create-implementation-plan/SKILL.md:56` and `:65` â€” both teach `root-cause` as the stage word the disposition gate expects to see. Leaving these means the downstream skill still trains agents on the wrong word even after `diagnose-bug` is corrected. Found during planning.",
        "Do NOT touch the frontmatter `description:` fields. `diagnose-bug/SKILL.md:7` and `make-bugfix-request/SKILL.md:5-6` say 'intake -> root-cause -> reuse plan/implement' â€” that is the PIPELINE STAGE's name (matching the track README's own table row at `:17`, 'Root cause'), not a status word. A description edit is a triggering-behaviour change (the skill-quality mandate at `acceptance_panel.js:200`, item 1) and does not belong in a status-grammar fix.",
        "Add a third test to `tests/test_skill_references.py`: parse the bugfix track README's `**Status grammar:**` line into a set of stage words, then assert that every `> **Status:**` template line inside the bugfix-track skills (`diagnose-bug`, `make-bugfix-request`) carries a stage word from that set, and that no SKILL.md instructs advancing a status to a word outside it. Write it to be RED before the edits above and GREEN after, and demonstrate both.",
        "SCOPE THE GUARD NARROWLY, ON PURPOSE. There are exactly six `> **Status:**` template lines across all skills; two violate the bugfix grammar. The feature track has its own separate divergence (`create-implementation-plan/SKILL.md:176` uses stage word `plan` where the feature README says `planned`; `implement-plan/SKILL.md:272` uses `implemented`). Those are real but are NOT this RCA's finding â€” a guard broad enough to catch them turns red on work nobody scoped. Keep it bugfix-track-only and file the feature-track divergence as its own intake.",
        "The new test must satisfy `mypy --strict` (pyproject sets `strict = true` with `files = [\"src\", \"tests\"]`) and `ruff format --check`. Annotate the return type as `-> None` like its two siblings, and run `uv run ruff format tests/test_skill_references.py` before the gates."
      ],
      "acceptance": [
        "Demonstrate the guard bites: add the test FIRST, run `uv run pytest tests/test_skill_references.py -q`, and paste the RED output naming `diagnose-bug/SKILL.md:107` and `make-bugfix-request/SKILL.md:130`. Then make the SKILL.md edits and paste the GREEN run. A guard added after its subject is already fixed has never been observed to fail and is not yet a guard.",
        "`grep -rn \"root-cause\" .claude/skills/` returns only genuine prose uses â€” the two frontmatter pipeline descriptions and 'root-cause analysis' as an English phrase â€” and never a status word or a `next:` value. Enumerate the survivors in the report so a reader can check the judgment.",
        "`uv run pytest -m \"not gamedata\"` -> `173 passed, 62 deselected`, zero failures.",
        "`uv run mypy` -> Success (the count rises from 38 to 38 â€” the module already exists; it must not drop). `uv run ruff check .` and `uv run ruff format --check .` green.",
        "The four `.mjs` guards still exit 0."
      ],
      "commit_note": "Checkpoint. `/commit`. Suggested message: `fix(skills): the bugfix status grammar is the track README's â€” diagnosed, not root-cause`. Note in the body that four files were corrected, not one, and that the feature-track `plan`/`planned` divergence was found and deliberately left for its own intake. Reversible; the guard is additive."
    },
    {
      "name": "Phase 5 â€” VERIFY the unconfirmed node-on-the-runner claim (measurement, not assertion)",
      "goal": "Settle by measurement whether GitHub's `ubuntu-latest` image ships node. The RCA's Hardening item 7 states this is *unconfirmed* and 'should be measured rather than asserted' (its lines 209-211). Phase 6 depends on the answer, so it cannot start until this phase produces a real CI log line. THIS PHASE EXISTS ONLY TO TURN A BELIEF INTO A FACT.",
      "steps": [
        "Understand why this cannot be verified locally. Local node is v24.15.0 â€” measured during planning â€” and that says exactly nothing about the runner image. `.github/workflows/ci.yml` has no node step and no `actions/setup-node` anywhere; the whole `quality` job runs `uv`-managed Python and nothing else (steps at `:22-49`).",
        "Add ONE temporary probe step to `.github/workflows/ci.yml`, placed after 'Sync dependencies' (`:34-35`) and before 'Ruff (lint)' (`:37`): a step named something like 'Probe: node availability (temporary)' whose run line is `node --version`. Keep it a separate step so its log block is unmistakable, and put the word temporary in the step name so a reviewer knows it is not staying.",
        "Add no `continue-on-error`. If node is absent, the job SHOULD go red â€” that is the measurement, and swallowing it produces the vacuous pass the repo's own infra-cost mandate calls out.",
        "THIS IS A MANUAL GATE. Agents do not push and do not open PRs (CLAUDE.md: 'Never push to `main`, force-push, or amend â€” those stay the operator's'; the PR stays the user's). Hand the branch to the user, ask them to push and let CI run, and ask them to paste the probe step's log block plus the run URL.",
        "Record the measurement in the plan's Decisions section with an epistemic label: `measured <date>` plus the version string, or `measured <date> â€” absent`. Do not write 'ubuntu-latest ships node' as a fact without the log line behind it.",
        "Confirm no branch-protection change is needed: `ops/branch-protection.json` matches on the JOB display name and its `contexts` array is exactly `[\"Lint, types, tests\"]`, which is the `quality` job's `name:` at `ci.yml:19-20`. Adding a STEP does not change a job display name. Verified during planning by reading both files."
      ],
      "acceptance": [
        "A pasted CI log block from a real run showing either a version string from `node --version`, or the step failing with 'node: command not found'. Plus the run URL. There is no local substitute and no acceptable inference â€” the log line IS the acceptance criterion.",
        "`git diff .github/workflows/ci.yml` shows exactly one added step and no other change. In particular the `-m \"not gamedata\"` pytest selector at `:49` and the job name at `:19-20` are untouched.",
        "`git diff ops/branch-protection.json` is empty.",
        "Local gates still green: `uv run pytest -m \"not gamedata\"` -> 173 passed; ruff, ruff format, mypy clean. All four `.mjs` guards exit 0."
      ],
      "commit_note": "Checkpoint, then a wait. `/commit` the probe (suggested: `chore(ci): probe node availability on the runner (temporary)`), hand the branch to the user to push, and STOP until the log line comes back. Do not begin Phase 6 on an assumption about the answer â€” that is precisely the failure mode the RCA labelled unconfirmed. Trivially reversible: Phase 6 replaces or deletes the probe."
    },
    {
      "name": "Phase 6 â€” [GATED on Phase 5's measurement] Run the four skill guards in CI",
      "goal": "The `.mjs` guards stop being run-by-hand-if-someone-remembers. The RCA's Hardening item 7, unblocked only once Phase 5 produced a real log line. A guard that only runs when an agent chooses to run it is how this one stayed red from arrival.",
      "steps": [
        "BRANCH ON PHASE 5'S MEASUREMENT. If node was present: replace the probe step with the real guard step. If node was absent: either add `actions/setup-node` ahead of the guard step, or drop this phase entirely and record why â€” both are legitimate; guessing is not.",
        "Replace the temporary probe with a step named e.g. 'Skill guards (node)', placed after the pytest step (`ci.yml:46-49`) so the cheap Python gates fail first. Run all four guards: `.claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs`, `.claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/implement-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/implement-plan/tests/verify_batching_guard.mjs`, and `.claude/skills/scope-feature/tests/merge_fallback_guard.mjs` â€” five files, verified present by glob during planning.",
        "Make the step fail on the FIRST non-zero exit, and make each guard's name visible in the log. A loop that swallows an exit code, or a glob that silently matches nothing, is the vacuous check `acceptance_panel.js:201` item 4 names as worse than no check.",
        "Do not add a new JOB. A new job introduces a new display name that `ops/branch-protection.json` does not list, and `ci.yml:15-18` warns in-file that a rename leaves PRs waiting forever for a check that never reports. Adding a step to the existing `quality` job keeps `contexts: [\"Lint, types, tests\"]` correct with no edit. If you nonetheless add a job, `ops/branch-protection.json` MUST change in the same commit.",
        "Note for the reviewer: this adds a non-Python toolchain to a Python-only CI. It requires no local OOTP install and no warehouse, so it does not collide with the `gamedata` marker rule at `pyproject.toml`'s `[tool.pytest.ini_options]` â€” the guards are pure Node with no network and no game data."
      ],
      "acceptance": [
        "A CI run log showing the guards step executing and naming all five guard files, exiting 0. Paste it with the run URL.",
        "PROVE THE STEP IS NOT VACUOUS before asking for the push: re-break the scratchpad copy from Phase 2 and run the same command shape against it locally, showing a non-zero exit and the failing guard named. A step that would pass even with a red guard underneath it is worse than nothing.",
        "`git diff ops/branch-protection.json` is empty (step added to the existing job), OR it changed in this same commit with the new job's display name.",
        "All local gates green: `uv run pytest -m \"not gamedata\"` -> 173 passed; ruff, ruff format, mypy clean; all guards exit 0 locally."
      ],
      "commit_note": "Checkpoint. `/commit` (suggested: `ci: run the five skill guards on every PR`), then hand to the user to push and confirm the run. Reversible by deleting the step. If Phase 5 measured node absent and the user declines `setup-node`, SKIP this phase and record the decision with its measurement â€” a recorded skip is a result, not a gap."
    },
    {
      "name": "Phase 7 â€” [OPTIONAL, user-gated] Bounded sweep for remaining ported-domain residue",
      "goal": "The RCA's Hardening item 8: 'Two instances found by accident in one sitting is weak evidence that a deliberate pass would find none.' Convert accident into a bounded, recorded pass â€” without turning a fix into an open-ended audit.",
      "steps": [
        "Time-box and scope-box this. Grep `.claude/skills/` only, for a fixed vocabulary list agreed with the user up front â€” sibling-repo domain terms (`nba`, `2k`, `pagination`, `season` used with basketball counts like 1230/82), sibling lens names (`data-contract`, `extraction`), and repo paths that do not resolve.",
        "For each hit, classify into exactly one of three buckets: (i) unambiguous residue with a one-word in-domain correction â€” fix here; (ii) a real behavioural question â€” file a new intake via `/make-bugfix-request`, do not decide it here; (iii) a false positive â€” record why, so the next sweep does not re-open it.",
        "Record the full classification table in the IMPLEMENTATION_REPORT even where the answer was 'nothing found'. A negative result is the point of the phase: it converts the RCA's 'weak evidence' into a measured statement about coverage.",
        "Do NOT extend `tests/test_skill_references.py` from two token classes to every repo path a skill names. That is Hardening item 6 here and is explicitly GATED in `requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:104-106`; it belongs to that request's plan.",
        "If the sweep produces zero bucket-(i) hits, land the report entry and skip the code commit. An empty finding is still a phase outcome."
      ],
      "acceptance": [
        "A classification table in the report covering every grep hit, each in one of the three buckets with a one-line reason.",
        "Every bucket-(i) item fixed; every bucket-(ii) item has a real `requests/bugfix-requests/<slug>/BUGFIX_REQUEST.md` on disk, not a TODO in prose.",
        "`uv run pytest -m \"not gamedata\"` still green at 173 passed (or higher if a fix added a test); ruff, ruff format, mypy green; all guards exit 0."
      ],
      "commit_note": "Checkpoint. `/commit` (suggested: `docs(skills): sweep the ported skills for sibling-repo domain residue`). If the sweep found nothing to change, there is nothing to commit beyond the report â€” say so plainly rather than manufacturing a diff. Fully reversible."
    }
  ],
  "testing": "HOW THE WHOLE THING IS VERIFIED\n\nThe acceptance contract is the bugfix track's, stated at `requests/bugfix-requests/README.md:24`: the red reproduction goes green, a regression test is left behind, and nothing else regresses. All three have concrete numbers here.\n\nTHE RED REPRO, AND ITS EXACT SELECTORS\n`tests/test_skill_references.py` is committed and RED today (verified this session â€” the RCA's note that it was 'not yet committed' is stale; `git ls-files` returns it and the tree is clean).\n- `uv run pytest tests/test_skill_references.py::test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines -q` â€” goes green in PHASE 1.\n- `uv run pytest tests/test_skill_references.py::test_every_test_file_a_skill_names_exists -q` â€” goes green in PHASE 3.\n- `uv run pytest tests/test_skill_references.py -q` -> `2 passed` is the whole contract, met at the end of Phase 3.\n\nTHE HUMAN-READABLE CHECK, WHICH IS NOT A PYTEST\n`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs`, exit 0, with the first diagnostic line reading `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`. Assert the NUMBERS, not just the exit code: a green exit still showing `raw=8` would mean the assertions were weakened rather than the fixture fixed, which is the outcome both RCAs name as the worst available. `.claude/skills/implement-plan/SKILL.md:309` is the contract this satisfies.\n\nTHE REGRESSION TEST LEFT BEHIND â€” three layers, deliberately\n1. `test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` (Python, runs in CI, already committed) catches a future roster rename from outside.\n2. The Phase 2 assertion inside the `.mjs` catches it at the point of use, with a message that names the unasked lens instead of a miscount. This is the one that would have saved the original diagnosis.\n3. The Phase 4 status-grammar test catches the third instance's class.\nLayers 1 and 3 run under `uv run pytest -m \"not gamedata\"` â€” offline, no game install, no warehouse â€” so CI executes them on every PR today. Layer 2 runs in CI only if Phase 6 lands.\n\nTHE NUMBERS, PHASE BY PHASE (baseline measured this session: `2 failed, 170 passed, 62 deselected`)\n- After Phase 1: `1 failed, 171 passed, 62 deselected`\n- After Phase 2: unchanged (`1 failed, 171 passed`) â€” no Python touched\n- After Phase 3: `172 passed, 62 deselected`, zero failures\n- After Phase 4: `173 passed, 62 deselected`\nAny deviation from these is an unintended regression, not a rounding difference. Record the tally line at every checkpoint.\n\nTHE FULL LOCAL GATE, RUN AT EVERY PHASE BOUNDARY\n`uv run pytest -m \"not gamedata\"` Â· `uv run ruff check .` Â· `uv run ruff format --check .` Â· `uv run mypy`. Baseline for the last three, measured this session: All checks passed / 115 files already formatted / Success: no issues found in 38 source files. `ruff format --check` is a distinct CI gate at `ci.yml:40-41` and is the most commonly forgotten one â€” run `uv run ruff format` on any Python you write before the gate.\n\nREGRESSION SAFETY FOR THE PANEL ITSELF\nThe strongest guarantee is structural: `acceptance_panel.js` is never edited, so the panel's behaviour cannot have changed. Verify it by inspection at every checkpoint â€” `git diff --stat` must not list it. The four sibling guards (`create-implementation-plan/tests/merge_failure_repro.mjs`, `create-implementation-plan/tests/merge_fallback_guard.mjs`, `implement-plan/tests/merge_fallback_guard.mjs`, `scope-feature/tests/merge_fallback_guard.mjs`) share the same `new Function`-over-panel-source harness and all exit 0 at baseline; re-run all four at every checkpoint as the cross-check that nothing structural moved.\n\nNEGATIVE TESTING IS AN ACCEPTANCE CRITERION, NOT A NICETY\nPhases 2, 4 and 6 each require demonstrating the new check RED before it is GREEN. For the `.mjs` this means a scratchpad copy with its `HERE` constant repointed at the real tracked panel and the fixture re-broken â€” the technique used during planning to reproduce the RCA's decisive experiment. For Phase 4 it means adding the test before the SKILL.md edits. A check that has never been observed to fail is a check nobody has verified; that is exactly how the batching guard shipped red and stayed red.\n\nMYPY STRICT COVERS TESTS\n`pyproject.toml` sets `strict = true` with `files = [\"src\", \"tests\"]`, so the Phase 4 test needs a `-> None` annotation and fully-typed helpers, matching `tests/test_skill_references.py:43`, `:47`, `:72`, `:79`, `:84`.",
  "risks": [
    "THE SINGLE LARGEST RISK: fixing the wrong side. If any edit lands in `.claude/skills/implement-plan/acceptance_panel.js`, this plan has failed even if every test is green â€” the RCA's verdict is that the panel is CORRECT, and `acceptance_panel.js:317`'s `jaccard(o._toks, toks) >= 0.5` gate is specifically the property the guard falsely accused it of violating. Loosening it to satisfy the guard as originally written would silently disable adversarial dedupe for every future `/implement-plan` run and nothing would surface the loss. MITIGATION: treat `acceptance_panel.js` appearing in `git diff --stat` as a hard stop, checked at every phase boundary.",
    "Phase 3 sits one line away from the doc-link request's GATED decision. The six references live inside 'What good looks like' bullets that also promise fence exemption, `file.py:123` suffixes, `var/` targets, and a bare-token scan (canonical instance: `.claude/skills/create-implementation-plan/SKILL.md:250-256`). Editing that prose while you are already in the file would decide `requests/bugfix-requests/_done/doc-link-guard-mismatch/`'s gated call by implication â€” the outcome both RCAs name as worst. MITIGATION: `git diff -U0 .claude/skills/` reviewed line by line as a Phase 3 acceptance criterion; only the reference token and the pagination example may appear.",
    "The plan document you write is itself scanned by two blocking CI checks, and both bite. (a) `tests/test_doc_links.py:10` has no fence awareness and `:30` strips a `#fragment` but not a `:123` suffix, so a Markdown link to a `file.py:123` citation turns CI red â€” write every citation as a CODE SPAN. (b) `tests/test_no_leaks.py:25` bans any Windows drive path in a tracked text file, so the scratchpad recipes in Phases 2 and 6 must never be pasted verbatim into the plan or the report.",
    "Phase 4's status-grammar guard is the phase most likely to over-reach. There are six `> **Status:**` template lines across the skills and the feature track carries its own divergence â€” `create-implementation-plan/SKILL.md:176` uses stage word `plan` where `requests/feature-requests/README.md` says `planned`, and `implement-plan/SKILL.md:272` uses `implemented`. A guard broad enough to catch those goes red on work nobody scoped. MITIGATION: scope the guard to the bugfix track only, and file the feature-track divergence as its own intake rather than fixing it in passing.",
    "Phase 4 must not touch skill frontmatter. `diagnose-bug/SKILL.md:7` and `make-bugfix-request/SKILL.md:5-6` contain the string 'root-cause' inside their `description:` fields, where it names the PIPELINE STAGE (matching `requests/bugfix-requests/README.md:17`'s 'Root cause' row), not a status word. A description edit changes when the skill triggers â€” a real behavioural change, flagged as a bug class by the skill-quality mandate at `acceptance_panel.js:200` item 1 â€” and has no place in a status-grammar fix. The new guard must be written so it does not flag them.",
    "Phase 6's CI step is the classic vacuous-pass shape. A loop that swallows a non-zero exit, or a glob that matches nothing, produces a green check that proves nothing â€” named explicitly as a bug class by the infra-cost mandate at `acceptance_panel.js:201` item 4. MITIGATION: the phase's acceptance requires demonstrating the step FAILING against a re-broken copy before it is trusted green.",
    "Adding a new CI JOB (rather than a step) would silently break branch protection: `ops/branch-protection.json` lists `contexts: [\"Lint, types, tests\"]`, which is the `quality` job's display name at `ci.yml:19-20`, and `ci.yml:15-18` warns in-file that a mismatch leaves PRs waiting forever for a check that never reports. MITIGATION: add a STEP to the existing job; if a job is genuinely needed, `ops/branch-protection.json` changes in the same commit.",
    "Hardening item 7 (node in CI) rests on an UNCONFIRMED claim â€” the RCA says so at its lines 209-211 â€” and local node v24.15.0 is not evidence about the runner image. MITIGATION: Phase 5 exists solely to measure it, produces a CI log line as its only acceptance criterion, and Phase 6 is explicitly gated on that measurement. Do not collapse the two phases to save a commit.",
    "The RCA contains one stale claim, corrected during planning: its line 30 says the repro is 'not yet committed', but `git ls-files tests/test_skill_references.py` returns it and the working tree is clean â€” it landed with the RCA. Do not re-create the file. Its line 168 also refers to a CLAUDE.md note recording the guard as known-red; that note is gone as of commit 1c47c2d ('Trim CLAUDE.md to its owners and file the panel-guard defect'), verified by grep, so no CLAUDE.md cleanup is needed and none should be invented.",
    "Phase 1's edit must keep `tests/test_skill_references.py:40`'s `FIXTURE_LENS` regex matching. It is anchored to exactly two leading spaces with an optional quote: `^ {2}'?([a-z0-9-]+)'?:\\s*\\[`. Re-indenting the fixture, or adding a key on a continued line, makes `fixture_lens_keys()` parse nothing â€” and the test's own line 99 guard (`parsed no lens keys out of the guard's fixture`) would then fire, which is the right failure but a confusing one if you were not expecting it.",
    "Do not fold phases together to reduce commits. Each phase here is independently reversible and each answers a different question; a single combined commit makes 'which change made the guard green' unanswerable, which is the exact ambiguity that made this bug expensive to diagnose in the first place."
  ],
  "files_to_touch": [
    {
      "path": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs",
      "change": "PHASE 1: line 54 `  'data-contract': [` -> `  warehouse: [`; line 58 `  extraction: [` -> `  parser: [`; line 150's trailing comment `// -> data-contract + extraction + skill-quality specialists` -> `// -> warehouse + parser + skill-quality specialists`. Optionally line 13's '7 lenses' -> 6 (user-gated). PHASE 2: add an assertion in Scenario 1 (lines 185-226) that every `FINDINGS_BY_LENS` key was actually dispatched as a `review:<key>` label, pushed onto `fails` (line 181) FIRST, before the cap/dedupe checks. Keep `|| []` at line 78."
    },
    {
      "path": ".claude/skills/implement-plan/acceptance_panel.js",
      "change": "DO NOT EDIT. Listed here so the checklist records it as a deliberate non-touch. The RCA's verdict is that this file is correct; its appearance in `git diff --stat` is a hard stop."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "change": "PHASE 3: line 104, `tests/test_request_links.py` -> `tests/test_doc_links.py`. Nothing else."
    },
    {
      "path": ".claude/skills/create-implementation-plan/SKILL.md",
      "change": "PHASE 3: line 251, `tests/test_request_links.py` -> `tests/test_doc_links.py` â€” the reference token ONLY; the surrounding promise prose at lines 250-256 is the doc-link request's gated decision and must not move. PHASE 4: lines 56 and 65, `root-cause` -> `diagnosed` in the disposition-gate examples."
    },
    {
      "path": ".claude/skills/diagnose-bug/SKILL.md",
      "change": "PHASE 3: line 176, `tests/test_request_links.py` -> `tests/test_doc_links.py`; lines 117-118, replace the `tests/test_extract_pagination.py::test_all_pages_landed` / 'expected 1230 games, got 1000' example with a real in-domain module+test that exists on disk. PHASE 4: lines 97, 107 and 150, `root-cause` -> `diagnosed`. Leave the frontmatter description at line 7 alone."
    },
    {
      "path": ".claude/skills/make-bugfix-request/SKILL.md",
      "change": "PHASE 3: line 199, `tests/test_request_links.py` -> `tests/test_doc_links.py`. PHASE 4: line 130's template `next: root-cause` -> `next: diagnosed`. Leave the frontmatter description at lines 5-6 alone."
    },
    {
      "path": ".claude/skills/make-feature-request/SKILL.md",
      "change": "PHASE 3: line 246, `tests/test_request_links.py` -> `tests/test_doc_links.py`. Reference token only."
    },
    {
      "path": ".claude/skills/update-docs/SKILL.md",
      "change": "PHASE 3: line 56, `tests/test_request_links.py` -> `tests/test_doc_links.py`. Reference token only."
    },
    {
      "path": "tests/test_skill_references.py",
      "change": "PHASE 4: add a third test asserting the bugfix-track skills' `> **Status:**` templates carry a stage word from `requests/bugfix-requests/README.md:45`'s grammar, and that no SKILL.md instructs advancing a status to a word outside it. Scope to `diagnose-bug` and `make-bugfix-request` only. Must be `-> None`-annotated for mypy strict and `ruff format`-clean. The two existing tests are NOT modified â€” they are the repro and must stay direction-independent."
    },
    {
      "path": ".github/workflows/ci.yml",
      "change": "PHASE 5: add one temporary `node --version` probe step between 'Sync dependencies' (lines 34-35) and 'Ruff (lint)' (line 37), no `continue-on-error`. PHASE 6 (gated): replace the probe with a real step after pytest (lines 46-49) running the five `.mjs` guards, failing on the first non-zero exit. Add a STEP to the existing `quality` job â€” never a new job."
    },
    {
      "path": "ops/branch-protection.json",
      "change": "Expected to be UNCHANGED. Its `contexts` is `[\"Lint, types, tests\"]`, matching the `quality` job's display name at `ci.yml:19-20`; adding a step does not change it. Listed so Phase 6 can assert an empty diff â€” and so that if a new job is ever added instead, this file changes in the SAME commit per the in-file warning at `ci.yml:15-18`."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "Index row for `verify-batching-guard-red-on-arrival` advances `diagnosed` -> `plan` when the plan lands, then -> `fixed` when the fix lands. `/commit`'s doc gate handles this; do not hand-edit ahead of it."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md",
      "change": "NEW â€” the stage-3 deliverable. Opens `> **Status:** plan Â· created <today> Â· decided Â· next: implement`. Every `file:line` written as a CODE SPAN, never a Markdown link (`tests/test_doc_links.py` would turn CI red otherwise). No absolute/drive paths anywhere in it (`tests/test_no_leaks.py:25`)."
    }
  ],
  "code_references": [
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:54",
      "claim": "Reads `  'data-contract': [` â€” a sibling repo's lens key. Phase 1 changes it to `  warehouse: [`. Read and confirmed verbatim."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:58",
      "claim": "Reads `  extraction: [`. Phase 1 changes it to `  parser: [`. Read and confirmed verbatim."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:78",
      "claim": "`const spec = FINDINGS_BY_LENS[lensKey] || []` â€” the silent swallow. Phase 2 deliberately LEAVES this alone; a throw here is caught by `pipeline`/`parallel` (lines 132-141) and loses every diagnostic."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:150",
      "claim": "`touchedAreas: ['transform', 'src', 'skills'],   // -> data-contract + extraction + skill-quality specialists` â€” the comment still teaches the wrong lens names. Phase 1 corrects it to `warehouse + parser + skill-quality`."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:163-179",
      "claim": "`makeAgent` records `{ label, prompt }` for every call into `calls`. This is the observation channel Phase 2's assertion uses to check which lenses the panel actually asked for â€” no regex over the panel source required."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:181",
      "claim": "`const fails = []` â€” the failure accumulator whose contents print through the RED reporter at lines 285-292. Phase 2's assertion pushes onto it rather than throwing."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:203-207",
      "claim": "`AREA_TO_SPEC` maps `src -> ['parser','warehouse']`, `transform -> ['warehouse']`, `skills -> ['skill-quality']`. This is why the guard's `touchedAreas` resolve to warehouse + parser + skill-quality, and why `warehouse`/`parser` are the correct re-key targets."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:196-202",
      "claim": "`SPEC_DEFS` defines exactly `parser`, `warehouse`, `builder`, `skill-quality`, `infra-cost`. No `data-contract`, no `extraction` anywhere in this repo's panel."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:317",
      "claim": "`const hit = out.find(o => o._loc === loc && jaccard(o._toks, toks) >= 0.5)` â€” the title-overlap gate that keeps two distinct bugs at the same file apart. Correct as written; the file must not be edited."
    },
    {
      "ref": ".claude/skills/implement-plan/SKILL.md:309",
      "claim": "States the guard's contract: exit 0 = the Verify phase stays under its cap, merges only true duplicates, groups by location, adjudicates each against its own id, degrades honestly. This is the property Phase 1 makes true."
    },
    {
      "ref": "tests/test_skill_references.py:47",
      "claim": "`test_every_test_file_a_skill_names_exists` â€” RED today; goes green in Phase 3. Verified red by running `uv run pytest tests/test_skill_references.py` this session."
    },
    {
      "ref": "tests/test_skill_references.py:84",
      "claim": "`test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` â€” RED today with `['data-contract', 'extraction']`; goes green in Phase 1. Verified red this session."
    },
    {
      "ref": "tests/test_skill_references.py:40",
      "claim": "`FIXTURE_LENS = re.compile(r\"^ {2}'?([a-z0-9-]+)'?:\\s*\\[\", re.MULTILINE)` â€” matches two-space-indented keys, quoted or not, so the Phase 1 re-key to unquoted `warehouse:`/`parser:` stays parseable. Re-indenting the fixture would break it."
    },
    {
      "ref": "tests/test_doc_links.py:10",
      "claim": "`LINK = re.compile(r\"\\[[^\\]]*\\]\\(([^)]+)\\)\")` â€” one regex over raw file text, no fence state. Why the plan document must use code spans, not Markdown links, for its citations."
    },
    {
      "ref": "tests/test_doc_links.py:30",
      "claim": "`clean = target.split(\"#\", 1)[0].strip()` â€” strips a `#fragment` but not a `:123` line suffix, so a linked `file.py:123` citation asks `Path.exists()` about a file that cannot exist."
    },
    {
      "ref": "tests/test_no_leaks.py:25",
      "claim": "`(\"windows drive path\", re.compile(r\"(?<![A-Za-z0-9])[A-Za-z]:[\\\\/]{1,2}[A-Za-z0-9_.\\-]\"))` â€” a blocking CI check banning drive paths in tracked text. The scratchpad recipes in Phases 2 and 6 must stay out of tracked artifacts."
    },
    {
      "ref": ".github/workflows/ci.yml:19-20",
      "claim": "`quality:` / `name: Lint, types, tests` â€” the job display name that `ops/branch-protection.json` matches on. Phases 5-6 add STEPS to this job, never a new job."
    },
    {
      "ref": ".github/workflows/ci.yml:37-49",
      "claim": "The four gates in order â€” ruff check, ruff format --check, mypy, pytest -m \"not gamedata\". There is no node step and no `actions/setup-node`; that absence is exactly what Hardening item 7 addresses and what Phase 5 measures."
    },
    {
      "ref": "ops/branch-protection.json",
      "claim": "`\"contexts\": [\"Lint, types, tests\"]` â€” a single entry matching the job name. Read in full this session; Phase 6 asserts it is unchanged."
    },
    {
      "ref": "requests/bugfix-requests/README.md:45",
      "claim": "`**Status grammar:** intake -> diagnosed -> planned -> fixed` â€” the contract Phase 4 enforces and the source the new guard parses."
    },
    {
      "ref": "requests/bugfix-requests/README.md:24",
      "claim": "'Done' means the red reproduction goes green and a regression test is left behind â€” this plan's acceptance contract, met at the end of Phase 3 with the guards from Phases 2 and 4 as the regression layer."
    },
    {
      "ref": "requests/README.md:12",
      "claim": "\"Each track's README is the contract\" â€” the authority that settles `diagnosed` over `root-cause` in Phase 4, two artifacts against one."
    },
    {
      "ref": ".claude/skills/diagnose-bug/SKILL.md:107",
      "claim": "`> **Status:** root-cause Â· created <YYYY-MM-DD> Â· decided Â· next: ...` â€” the template that keeps producing the wrong status word. Phase 4 changes it to `diagnosed`."
    },
    {
      "ref": ".claude/skills/diagnose-bug/SKILL.md:117-118",
      "claim": "Cites `tests/test_extract_pagination.py::test_all_pages_landed` failing with 'expected 1230 games, got 1000' â€” sibling-repo residue (no pagination in a save-file parser; 1,230 is an NBA regular season). Phase 3 re-grounds it."
    },
    {
      "ref": ".claude/skills/make-bugfix-request/SKILL.md:130",
      "claim": "`> **Status:** intake Â· created <YYYY-MM-DD> Â· open Â· next: root-cause` â€” a SEVENTH drift instance the RCA does not enumerate, found by grep during planning. Phase 4 changes `next:` to `diagnosed`."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:56",
      "claim": "Teaches `requests/bugfix-requests/README.md` for a confirmed-bug RCA 'at `root-cause`' â€” a downstream consumer of the wrong grammar. Phase 4 corrects it, or the fix is incomplete."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:65",
      "claim": "'a ready bugfix RCA reads `root-cause Â· â€¦ Â· decided Â· next: plan`' â€” the second downstream instance. Phase 4 corrects it."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:250-256",
      "claim": "The 'What good looks like' bullet that both names `tests/test_request_links.py` (Phase 3 fixes the token) and promises fence-exemption, `file.py:123` suffixes and `var/` targets (GATED â€” Phase 3 must not touch this prose)."
    },
    {
      "ref": ".claude/skills/create-implementation-plan/SKILL.md:175-231",
      "claim": "The stage-3 section MENU the plan document is written from. Sections 1-8 and References are Always/Default; section 9 (Data contracts) is Conditional and MUST BE OMITTED here â€” this change adds no dataset and touches no source. Section 10 (Code-grounding verification) is included, since adversaries verify the citations."
    },
    {
      "ref": "requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:95-98",
      "claim": "'step 2 is common to both readings and is the only part safe to do early' â€” the authority for Phase 3 repointing the six references without deciding the gated call."
    },
    {
      "ref": "requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:79-93",
      "claim": "The gated decision itself â€” extend the guard vs correct the skills. Explicitly OUT of this plan's scope; recorded as a non-goal so the implementer does not take it by implication."
    },
    {
      "ref": "pyproject.toml [tool.mypy]",
      "claim": "`strict = true`, `files = [\"src\", \"tests\"]` â€” the Phase 4 test must be fully annotated. Confirmed: `uv run mypy` reports Success on 38 source files at baseline."
    },
    {
      "ref": "pyproject.toml [tool.pytest.ini_options]",
      "claim": "`addopts = \"-q --strict-markers --strict-config\"` and a single `gamedata` marker. `--strict-markers` means inventing a new marker is a hard COLLECTION error â€” do not add one; every test in this plan is offline and unmarked."
    }
  ],
  "open_questions": [
    "Does Phase 3 belong in THIS slug's plan at all, or does the reference repoint move to `requests/bugfix-requests/_done/doc-link-guard-mismatch/`? RECOMMENDATION: land it here. `tests/test_skill_references.py::test_every_test_file_a_skill_names_exists` is half of this slug's red repro and cannot go green without it, and `doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md:95-98` says the repoint is common to both readings of that request's gated decision. This is the plan's single most consequential sequencing call â€” take it to the user gate.",
    "Phase 4 scope: bugfix track only, or also settle the feature track's divergence? `create-implementation-plan/SKILL.md:176` templates stage word `plan` where `requests/feature-requests/README.md` says `planned`, and `implement-plan/SKILL.md:272` templates `implemented` (correct for the feature grammar, wrong for the bugfix one â€” and that skill serves BOTH tracks). RECOMMENDATION: bugfix-track only here, keeping the guard narrow, and file the feature-track divergence as its own intake. Widening the guard turns it red on work nobody scoped.",
    "Is Phase 6 (node in CI) wanted at all? It adds a second toolchain to a deliberately Python-only CI to run five guards that today run by hand. The counter-argument is the RCA's own second-order finding: a check nobody is forced to run is how this one stayed red from arrival. Neither Phase 5 nor Phase 6 is required for the acceptance contract â€” both are Hardening. RECOMMENDATION: run Phase 5 regardless (it costs one throwaway step and converts an unconfirmed belief into a measured fact, which is worth having recorded either way), and let the measurement inform the Phase 6 decision.",
    "`verify_batching_guard.mjs:13` says findings arrive 'across 7 lenses' while `FINDINGS_BY_LENS` defines 6 keys. Correct it to 6, or leave it as prose about the panel's roster rather than the fixture's? A one-word accuracy fix in a comment, but it is comment drift in exactly the file this bug was about. RECOMMENDATION: correct it, in Phase 1, alongside the line-150 comment.",
    "Should Phase 7's residue sweep run at all, and against what vocabulary list? The RCA's Hardening item 8 argues 'two instances found by accident in one sitting is weak evidence that a deliberate pass would find none.' The risk is an unbounded audit. RECOMMENDATION: run it with the grep vocabulary agreed with the user IN ADVANCE, and bucket rather than fix â€” anything needing judgment becomes its own intake.",
    "Phase 2's design deviates from the RCA's Root item 4 wording. The RCA suggests deriving expected lens keys from `acceptance_panel.js`; this plan instead asserts against the review labels the panel actually dispatched (available in `calls`), because `tests/test_skill_references.py:37` already carries a regex over that source and a second one is a second thing to drift. RECOMMENDATION: accept the deviation â€” same one-home property, sturdier mechanism â€” but it is a conscious departure from a decided artifact and should be acknowledged at the gate, not slipped in.",
    "NOT A QUESTION, A CORRECTION TO RECORD: `docs/data-sources.md` does not exist in this repo. The equivalent is `docs/data-access.md`. Neither is relevant here â€” this change touches no source, no endpoint, no dataset â€” so the plan carries NO data-contracts section (menu item 9 is Conditional and correctly omitted). The one genuinely unconfirmed claim in scope is the node-on-the-runner belief, and Phase 5 exists solely to measure it before Phase 6 builds on it."
  ]
}
```

## Proposal 3 â€” domain-convention

```json
{
  "planner": "domain-convention",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Its Verdict (the guard's fixture is wrong, the panel is right), its tiered fix posture (Minimal 1-3, Root 4-5, Hardening 6-8), and its gated decision are CONSUMED by this plan, not re-opened."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/BUGFIX_REQUEST.md",
      "why": "Context only: the original six failure lines and the two contrast checks (merge_fallback_guard.mjs green, byte-identical failure in nba2k-rpg)."
    },
    {
      "path": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs",
      "why": "The artifact being fixed. Read lines 32-34 (HERE/PANEL/SRC), 40-64 (the FINDINGS_BY_LENS fixture), 65-66 (RAW_TOTAL/DEDUPED_TOTAL derived from it), 78 (the `|| []` that swallows an unknown key), 145-153 (makeArgs + the stale comment), 172 (the dispatch on the panel's real label)."
    },
    {
      "path": ".claude/skills/implement-plan/acceptance_panel.js",
      "why": "The code under test â€” DO NOT MODIFY IT. Lines 189-194 (4 CORE lenses), 196-202 (5 SPEC_DEFS), 203-209 (AREA_TO_SPEC -> specKeys -> ROSTER) are the authoritative lens roster; 298-317 is the dedupe the RCA proved correct."
    },
    {
      "path": "tests/test_skill_references.py",
      "why": "The committed red repro. Two tests, both RED today. Line 32 is the `tests/test_*.py` token regex, 37 the panel's `key: '...'` regex, 40 the fixture-key regex, 47 and 84 the two assertions this fix must flip."
    },
    {
      "path": "tests/test_doc_links.py",
      "why": "39 lines, blocking in CI, no fence awareness and no `:line` handling (lines 10, 11, 15, 28, 30). It constrains how the plan document and every artifact you write must be written â€” code spans, never Markdown links â€” and it is the guard the six broken skill references should be pointed at."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The track contract (requests/README.md:12). Line 45 gives the status grammar `intake -> diagnosed -> planned -> fixed`; line 53 is this bug's Index row, which /commit keeps in step with the artifacts."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "why": "Its `## Write allowlist` section deny-lists `tests/`, `.github/`, `ops/` and all of `.claude/` except one memory file. EVERY file this fix touches is inside that deny set, so the write-capable subagent may not build this â€” the main thread must."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "why": "Lines 151-155 carry a now-falsified entry (`a pre-existing upstream defect, not a porting error`) citing a CLAUDE.md section that no longer exists. Line 41 forbids pruning: correct it by APPENDING, never by editing. Line 28 fixes the entry shape."
    },
    {
      "path": "tests/test_agent_contract.py",
      "why": "Line 80 pins the subagent deny set; lines 84-95 mechanically require a valid epistemic label on every appended memory entry. Both fire on this change."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "Lines 37-49 are the whole quality job: ruff, ruff format, mypy, pytest -m \"not gamedata\". There is NO node step today â€” that absence is the Hardening item, and ops/branch-protection.json:5 pins the job's display name `Lint, types, tests`."
    },
    {
      "path": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md",
      "why": "Read only its first line. It is the in-repo precedent for the status header (`planned Â· created â€¦ Â· decided Â· next: implement`) and for the code-span citation convention this plan must also use."
    }
  ],
  "architecture_notes": "WHAT THIS CHANGE IS, AND WHAT IT IS NOT\n\nThis bugfix touches NO data. Nothing is parsed, landed, modelled, or pulled; no dataset is created; there is no grain, no key, no coverage window, no update semantics, and no pull cost. `datasets/` and `datasets/manifest.json` do not exist in this repo yet and CLAUDE.md forbids creating them speculatively, so resolve-by-name has no surface here. The plan therefore carries NO data-contracts section, and the correctness lens that matters is PROJECT-CONVENTION correctness â€” which is where the real traps in this change live.\n\nTHE HARNESS UNDER REPAIR\n\n`.claude/skills/implement-plan/acceptance_panel.js` is stage 4's adversarial acceptance panel. Its reviewer roster is assembled in one place: four always-on CORE lenses (`acceptance`, `fidelity`, `correctness`, `edgecases`, lines 189-194) plus specialists selected from `SPEC_DEFS` (`parser`, `warehouse`, `builder`, `skill-quality`, `infra-cost`, lines 196-202) via `AREA_TO_SPEC` at 203-207 and `specKeys`/`ROSTER` at 208-209. Exactly nine `key: '...'` declarations exist in the file and nowhere else â€” I grepped and counted them â€” which is what makes deriving the roster from the source safe.\n\n`.claude/skills/implement-plan/tests/verify_batching_guard.mjs` is a black-box guard, not a unit test. It reads the panel's source at line 33-34, strips the `export const meta` prefix, and evaluates it inside a `new Function(...)` at 154-160 with a stubbed `agent`. The stub dispatches on the panel's REAL label (`reviewFor(label.slice('review:'.length))`, line 172) into a fixture keyed by lens name (`FINDINGS_BY_LENS`, lines 40-64). Two of those six keys â€” `'data-contract'` at :54 and `extraction` at :58 â€” are a sibling repo's vocabulary. This repo's panel never asks for them, so `FINDINGS_BY_LENS[lensKey] || []` at :78 returns an empty review with no error, no warning, and no undefined. Three of the fixture's eleven findings evaporate before dedupe runs, and `RAW_TOTAL`/`DEDUPED_TOTAL` at :65-66 â€” computed from the fixture, not from what the panel received â€” keep asserting 11/9 against a run that only ever saw 8/7. All six failure lines fall out of that single gap.\n\nI re-verified the RCA's decisive experiment independently rather than taking it on faith. From a scratchpad copy with `PANEL` repointed at the tracked `acceptance_panel.js`, re-keying `'data-contract'` -> `warehouse` and `extraction` -> `parser` and changing nothing else produces `raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` and exit 0. (measured 2026-08-17, Node v24.15.0, Windows 11.) I also prototyped the Root-tier hardening in the scratchpad: a roster check derived from the panel source plus a strict `reviewFor` stays green on the fixed fixture, and when I regressed the two keys back to the sibling names it exits 1 with `ERROR: fixture names lenses acceptance_panel.js does not define: [\"data-contract\",\"extraction\"]` instead of six miscounts blaming the panel. Both hardening pieces are proven, not proposed. The repo working tree was not modified.\n\nWHY `touchedAreas` MATTERS. `makeArgs` at :150 passes `touchedAreas: ['transform','src','skills']`. Through `AREA_TO_SPEC` that yields `warehouse` (transform), `parser` + `warehouse` (src, deduped) and `skill-quality` (skills) â€” so `warehouse` and `parser` are exactly the two specialists the fixture was silently failing to feed. The trailing comment on that same line still teaches the sibling names and is the third and last site carrying the wrong vocabulary; a repo-wide grep for `data-contract|extraction` under `.claude/` returns only :54, :58, :150 plus unrelated prose about extraction cost. The blast radius is three lines in one file.\n\nTHE CONVENTION SEAM THAT DECIDES WHO BUILDS THIS\n\nEvery path this fix touches â€” `.claude/skills/**`, `tests/**`, `.github/workflows/ci.yml` â€” is inside the write-capable subagent's repo-level deny set in `.claude/agents/data-engineer.md` (`## Write allowlist`), and `tests/test_agent_contract.py:80` asserts that deny set survives. The definition's own instruction is to STOP and report if a spec's targets fall in the deny set. So this plan is implemented by the main thread directly. Any read-only subagent spawned to ground a step gets read-only git (never checkout/reset/restore/clean/stash/commit), per CLAUDE.md.\n\nTHE DOC-LINK WORKAROUND CONSTRAINS THE PLAN DOCUMENT ITSELF\n\n`tests/test_doc_links.py` scans every tracked `*.md` outside `var/` (line 15) with one regex over raw text (line 10). It has no fence state, so a Markdown link inside a code fence is indistinguishable from a live one, and line 30 strips only a `#fragment`, never a `:123` suffix. Consequence for the implementer: in the IMPLEMENTATION_PLAN, in the IMPLEMENTATION_REPORT, and in any Index-row edit, write every file citation as an inline CODE SPAN, never as a Markdown link. Both RCAs in this diagnosis declare that convention at their heads and the first-sight plan does the same. This is a live workaround for an undecided sibling defect, not a style preference.\n\nTHE STATUS-GRAMMAR SEAM (a fourth port-drift instance, found while planning)\n\n`requests/README.md:12` makes each track README the contract. `requests/bugfix-requests/README.md:45` and `.claude/skills/commit/SKILL.md:133` both give `intake -> diagnosed -> planned -> fixed`. But `.claude/skills/create-implementation-plan/SKILL.md:172` tells the author to set the Index Stage cell to `plan` and its template at :176 opens the plan at `Status: plan`. The in-repo precedent contradicts the skill: `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` line 1 reads `planned Â· created 2026-08-16 Â· decided Â· next: implement`. Note the distinction precisely, because it is easy to get wrong: the STAGE word is past-tense (`diagnosed`, `planned`) while the `next:` slot names the stage about to run (`next: plan`, `next: implement`) â€” so the existing `next: plan` usages are correct and only the stage-word usages are drift. This is the same defect class as the RCA's third instance (`diagnose-bug/SKILL.md`'s `root-cause`), found in a second skill.\n\nWHAT MUST NOT MOVE\n\n`acceptance_panel.js` is not edited by this plan. The RCA settled by experiment that the panel is correct and that \"fixing\" it would rename this repo's `parser` and `warehouse` lenses into a sibling's vocabulary and loosen a dedupe (`jaccard >= 0.5` at :317) that is already right. Likewise, the doc-link guard's CONTRACT â€” fence exemption, `file.py:123` suffix, `var/` targets, the bare-token scan â€” belongs to `requests/bugfix-requests/_done/doc-link-guard-mismatch/` and stays undecided here. Only the file-NAME token on the seven broken references is direction-independent, and that request's own RCA says so (\"step 2 is common to both readings and is the only part safe to do early\").",
  "phases": [
    {
      "name": "Phase 1 â€” Re-key the fixture to this repo's lenses (Minimal, RCA step 1)",
      "goal": "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 for the first time, with `acceptance_panel.js` byte-for-byte untouched â€” and the falsified memory entry is corrected by appending, per that file's own no-prune rule.",
      "steps": [
        "Record the baseline before touching anything: run `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` and paste its exit-1 output plus the six failure lines into the eventual IMPLEMENTATION_REPORT. Also run the four sibling guards (`.claude/skills/implement-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/scope-feature/tests/merge_fallback_guard.mjs`, `.claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs`) â€” all four exit 0 today (measured 2026-08-17, Node v24.15.0), and they are your no-regression baseline.",
        "In `.claude/skills/implement-plan/tests/verify_batching_guard.mjs`, change line 54 from `'data-contract': [` to `warehouse: [` and line 58 from `extraction: [` to `parser: [`. Unquoted is fine and preferred â€” both are valid JS identifiers, and `tests/test_skill_references.py:40`'s `FIXTURE_LENS` regex accepts quoted or unquoted at two-space indent. Do NOT rename `'skill-quality'`, which needs its quotes.",
        "Fix the stale teaching comment on line 150: `// -> data-contract + extraction + skill-quality specialists` becomes `// -> warehouse + parser + skill-quality specialists`. Trace it once against `acceptance_panel.js:203-209` so you are asserting a mapping you actually read, not copying this plan.",
        "Confirm the vocabulary is gone: grep `.claude/` for `data-contract|extraction` and expect only unrelated prose about extraction cost in `make-feature-request/SKILL.md`, `create-implementation-plan/SKILL.md` and `make-bugfix-request/SKILL.md:69` â€” no hits in `verify_batching_guard.mjs`.",
        "Do NOT open `.claude/skills/implement-plan/acceptance_panel.js` in an editor. `git diff --stat` at the end of this phase must show it absent from the diff; that absence is the RCA's central claim made checkable.",
        "Append (never edit, never prune â€” `.claude/agents/data-engineer-memory.md:41`) one correcting entry in the exact shape at that file's line 28, dated today, labelled `verified`, tagged `harness`, citing `requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/ROOT_CAUSE_ANALYSIS.md` as an inline code span, and stating that the 2026-08-15 entry at lines 151-155 was wrong: the identical failure in `nba2k-rpg` is not evidence of an upstream defect but of two copies sharing the same sibling-repo fixture keys, and the entry's own evidence pointer (a CLAUDE.md section) no longer exists."
      ],
      "acceptance": [
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 and prints `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0` followed by the GREEN line. (Independently reproduced in a scratchpad copy at plan time â€” this is the expected output, not a guess.)",
        "All four sibling `.mjs` guards still exit 0.",
        "`git diff --name-only` does NOT list `.claude/skills/implement-plan/acceptance_panel.js`.",
        "`uv run pytest tests/test_skill_references.py::test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` passes.",
        "`uv run pytest tests/test_agent_contract.py` passes â€” proving the appended memory entry carries a valid epistemic label (guard at `tests/test_agent_contract.py:84-95`).",
        "`uv run pytest`, `uv run ruff check`, `uv run mypy` all green.",
        "`uv run pytest tests/test_skill_references.py::test_every_test_file_a_skill_names_exists` is STILL RED â€” expected at this checkpoint, and the proof that Phase 2 has not moved first."
      ],
      "commit_note": "Re-key the batching guard's fixture to this repo's lenses. Two fixture keys named a sibling repo's specialists; `|| []` swallowed them; all six failure lines followed from the three findings lost. `acceptance_Ð¿Ð°Ð½el.js` untouched â€” deliberately. Land via /commit; expect the doc gate to trigger on `data-engineer-memory.md` appearing in the staged diff (`commit/SKILL.md:96-99`) and read the appended entry."
    },
    {
      "name": "Phase 2 â€” Point the seven broken skill references at files that exist (Minimal, RCA steps 2 and 3)",
      "goal": "The second red repro test goes green by correcting only the FILE-NAME token on each reference â€” the part that is direction-independent under both readings of the doc-link gated decision.",
      "steps": [
        "Do not start this phase until Phase 1 is committed. The RCA is explicit that this is the one step that must not move first.",
        "Replace the token `tests/test_request_links.py` with `tests/test_doc_links.py` at exactly six sites, verified by grep at plan time: `.claude/skills/commit/SKILL.md:104`, `.claude/skills/create-implementation-plan/SKILL.md:251`, `.claude/skills/diagnose-bug/SKILL.md:176`, `.claude/skills/make-bugfix-request/SKILL.md:199`, `.claude/skills/make-feature-request/SKILL.md:246`, `.claude/skills/update-docs/SKILL.md:56`.",
        "Change the file name and NOTHING ELSE on those lines. Do not touch the surrounding sentences that promise fence exemption, a `file.py:123` suffix, `var/` targets, or a bare-token scan. Those promises are the subject of `requests/bugfix-requests/_done/doc-link-guard-mismatch/`'s gated decision and are not this request's to settle. Renaming the guard TO `test_request_links.py` is the one option that is off the table: it scans all Markdown, not just `requests/`, so the ported name misdescribes it (that request's RCA, its Fix-posture blockquote).",
        "Re-ground the worked example at `.claude/skills/diagnose-bug/SKILL.md:117-118`. `tests/test_extract_pagination.py::test_all_pages_landed` failing with `expected 1230 games, got 1000` is a sibling repo's NBA season in a template a cold agent copies from; there is no pagination in a save-file parser. Replace it with a real test in this repo â€” `tests/test_byte_accounting.py::test_the_team_count_matches_the_export_on_the_only_save_that_has_one` is a genuine one (verified present at line 154 of that file) and its plausible red reads as a team-count mismatch against the export.",
        "Re-run the grep from `tests/test_skill_references.py:32` in your head: any `tests/test_*.py` token anywhere in any `.claude/skills/**/*.md`, in a code span or not, must resolve on disk."
      ],
      "acceptance": [
        "`uv run pytest tests/test_skill_references.py` â€” BOTH tests pass. This is the bugfix track's acceptance contract (`requests/bugfix-requests/README.md:24`) met in full: the red repro is green.",
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` still exits 0.",
        "A grep for `test_request_links` across the repo returns hits ONLY inside `requests/bugfix-requests/*/ROOT_CAUSE_ANALYSIS.md` and `BUGFIX_REQUEST.md` (the historical record, which must not be rewritten) â€” zero hits under `.claude/skills/`.",
        "A grep for `test_extract_pagination` returns zero hits under `.claude/skills/`.",
        "`uv run pytest`, `uv run ruff check`, `uv run mypy` all green â€” including `tests/test_doc_links.py`, which scans the files you just edited."
      ],
      "commit_note": "Point six skills at the link guard that exists and re-ground the diagnose-bug worked example in this repo's domain. File-name token only; the promised exemptions stay untouched and belong to the doc-link request's gated decision."
    },
    {
      "name": "Phase 3 â€” Make the guard fail loudly instead of miscounting (Root, RCA step 4)",
      "goal": "The mechanism that hid this defect is removed: an unknown lens key can never again present itself as a defect in the code under test. Derived from `acceptance_panel.js`, so the roster has one home.",
      "steps": [
        "In `verify_batching_guard.mjs`, after `SRC` is read (line 34) and after `FINDINGS_BY_LENS` is declared (line 64), add a startup roster check: parse the panel's lens keys out of `SRC` with `/\\bkey:\\s*'([a-z0-9-]+)'/g` (exactly nine matches today â€” the four CORE at :190-193 and the five SPEC_DEFS at :197-201, and no other `key: '` anywhere in the file; I grepped and counted), then exit 1 with an `ERROR:` line naming any fixture key the panel does not define, plus the panel's actual roster. Also exit 1 if the parse yields zero keys â€” a silently-drifted regex must fail, not pass vacuously.",
        "Replace the `|| []` at line 78 with a strict lookup: if `lensKey` is not a key of `FINDINGS_BY_LENS`, print `ERROR: the panel asked for lens '<key>' the fixture does not define` and exit 1. This is the opposite direction from the startup check and both are needed â€” the startup check catches a fixture key the panel dropped, the strict lookup catches a panel key the fixture lacks.",
        "Verify the hardening is actually wired rather than dead code: temporarily re-key `warehouse` back to `'data-contract'` and `parser` back to `extraction` IN A SCRATCHPAD COPY (never in the repo), run it, and confirm it now exits 1 with the ERROR diagnostic naming the two keys instead of six failure lines blaming the panel's dedupe. Then discard the scratchpad copy. I ran exactly this at plan time and it produced `ERROR: fixture names lenses acceptance_panel.js does not define: [\"data-contract\",\"extraction\"]` followed by the panel's nine lenses.",
        "Refresh the guard's header comment (lines 1-27) only where it is now wrong, and keep the `RUN:` line at :26 exact â€” `.claude/skills/implement-plan/SKILL.md:309` quotes that command verbatim.",
        "Leave `RAW_TOTAL`/`DEDUPED_TOTAL` at :65-66 derived from the fixture as they are. With the roster check in front of them they can no longer disagree with what the panel received, which is the whole point."
      ],
      "acceptance": [
        "`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` exits 0 with the same four diagnostic lines as Phase 1.",
        "A deliberately corrupted scratchpad copy (either direction: a fixture key the panel lacks, or a fixture missing a lens the panel asks for) exits 1 with an `ERROR:` line that names the offending key â€” and NOT with the six dedupe/coverage failure lines. Paste both outputs into the report; this is the phase's real deliverable.",
        "`uv run pytest tests/test_skill_references.py` still passes â€” its `FIXTURE_LENS` regex at line 40 still finds the fixture block, so the two guards agree rather than one masking the other.",
        "`uv run pytest`, `uv run ruff check`, `uv run mypy` all green."
      ],
      "commit_note": "Fail loudly on a lens key the panel does not define, derived from acceptance_panel.js. Without this, the next roster rename reproduces this bug exactly (RCA, Root tier step 4)."
    },
    {
      "name": "Phase 4 â€” Settle the status-word grammar against the track contract (Root, RCA step 5)",
      "goal": "The skills stop teaching a status vocabulary the track READMEs do not use, and a mechanical guard stops the fifth instance.",
      "steps": [
        "Read `requests/README.md:12` first â€” each track's README is the contract, and that sentence is what decides this. Then `requests/bugfix-requests/README.md:45` (`intake -> diagnosed -> planned -> fixed`), `requests/feature-requests/README.md:110` (`intake -> scoped -> planned -> implemented`), and `.claude/skills/commit/SKILL.md:133`, which already agrees with both.",
        "Correct `.claude/skills/diagnose-bug/SKILL.md` at lines 97, 107 and 150: the RCA's stage word is `diagnosed`, not `root-cause`. Line 7 (the frontmatter description's `intake -> root-cause -> reuse plan/implement`) describes the PIPELINE stages rather than an artifact's status word â€” decide deliberately whether to touch it and say which you chose in the report; leaving it is defensible, changing it silently is not.",
        "Correct `.claude/skills/create-implementation-plan/SKILL.md` at line 172 (Index Stage cell `plan` -> `planned`) and line 176 (the template header `Status: plan` -> `Status: planned`). This is a fourth instance of the same class, found while planning; the in-repo precedent is `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` line 1. Confirm with the operator before landing it if you would rather keep this request narrow â€” it is the same one-word defect, but it was not enumerated in the RCA.",
        "Do NOT touch the `next: <stage>` slots. `next: plan`, `next: implement`, `next: fix` name the stage about to run and are correct as written; only the past-tense STAGE word was drifting. Getting this backwards would break every artifact header in the repo.",
        "Add a small mechanical guard â€” a new test in `tests/test_skill_references.py` (it is already the home for 'a ported artifact must describe the repo it lives in') â€” asserting that any status blockquote a skill template emits uses only stage words the track READMEs define. Parse the allowed words out of the two READMEs' `**Status grammar:**` lines rather than hardcoding a second copy, and fail if the parse yields nothing. That is the same one-declaration-many-consumers shape as Phase 3."
      ],
      "acceptance": [
        "Grepping `.claude/skills/` for a status blockquote whose stage word is `root-cause` or a bare `plan` returns zero hits.",
        "The new grammar test is RED when a stage word is reverted (demonstrate it once in the working tree, then restore) and GREEN on the corrected tree.",
        "`uv run pytest`, `uv run ruff check`, `uv run mypy` all green.",
        "The two track READMEs are unmodified â€” the contract was read, not edited."
      ],
      "commit_note": "Reconcile the skills' status vocabulary with the track READMEs, which requests/README.md:12 makes the contract, and add the guard that keeps them reconciled."
    },
    {
      "name": "Phase 5 â€” Run the .mjs guards in CI (Hardening, RCA step 7 â€” VERIFY BEFORE BUILDING ON IT)",
      "goal": "The five node guards become a blocking check instead of an instruction nobody runs â€” with the node-availability claim MEASURED rather than asserted, exactly as the RCA demands.",
      "steps": [
        "The RCA labels this *unconfirmed*: `ci.yml:37-49` has no node step, and 'GitHub's ubuntu-latest image ships node' is a belief, not a measurement. Verify it FIRST, in the same PR, before anything depends on it: add `node --version` as the first command of the new step and read the actual CI log on the PR run. If node is absent, the correct outcome is to add `actions/setup-node` â€” not to make the step skip, which would pass vacuously.",
        "Add ONE step to the EXISTING `quality` job in `.github/workflows/ci.yml`, after the pytest step at :46-49. Do NOT add a new job: `ops/branch-protection.json:5` pins the required context to the display name `Lint, types, tests`, and a new job would be invisible to branch protection until that file changed too (the exact trap `acceptance_panel.js:201`'s infra-cost mandate item 5 warns about).",
        "The step must run all five guards and fail if ANY exits non-zero â€” enumerate them explicitly rather than globbing, so a guard deleted from the tree fails the step instead of shrinking the loop to zero and passing: `.claude/skills/implement-plan/tests/verify_batching_guard.mjs`, `.claude/skills/implement-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/scope-feature/tests/merge_fallback_guard.mjs`, `.claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs`. All five exit 0 locally after Phase 3 (four were measured green at plan time; the fifth is what this request fixes).",
        "Confirm nothing here needs an OOTP install or touches `var/` â€” these guards are pure node over tracked files, so they belong in the default CI selection and not behind the `gamedata` marker.",
        "This file is inside the write-capable subagent's deny set (`.github/`). The main thread edits it."
      ],
      "acceptance": [
        "The PR's CI log shows the node version printed and all five guards reporting exit 0 in a step inside the `Lint, types, tests` job.",
        "Deliberately breaking one guard locally makes the equivalent local command sequence non-zero â€” demonstrate the step actually fails on the condition it claims to check, then restore.",
        "`ops/branch-protection.json` is unmodified, and the job display name at `ci.yml:17` is unchanged.",
        "`uv run pytest`, `uv run ruff check`, `uv run mypy` all green."
      ],
      "commit_note": "Run the five node skill guards in CI's existing quality job. Node availability on ubuntu-latest measured on this PR's own run, not assumed."
    },
    {
      "name": "Phase 6 â€” Record: statuses, Index, and what stays open",
      "goal": "The request's paper trail matches what landed, and the two genuinely-open threads are named rather than quietly inherited.",
      "steps": [
        "Set the `IMPLEMENTATION_PLAN.md` header to `planned Â· created <today> Â· decided Â· next: implement` (the track grammar, matching `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` line 1) â€” not the `plan` the stage-3 template currently prescribes, which Phase 4 corrects.",
        "Update the Index row at `requests/bugfix-requests/README.md:53` Stage cell as the work advances: `diagnosed` -> `planned` -> `fixed`. `/commit` owns this (`commit/SKILL.md:114-138`); let it, and never mark ahead.",
        "Write the IMPLEMENTATION_REPORT with the before/after guard output pasted verbatim, including the deliberately-corrupted-copy runs from Phase 3. A green guard nobody has seen fail is a guard nobody has tested.",
        "State plainly what this request does NOT close: `requests/bugfix-requests/_done/doc-link-guard-mismatch/`'s gated decision is still open, so the code-span citation convention remains mandatory for every artifact; and `requests/bugfix-requests/leak-guard-blind-to-untracked-files/` is untouched.",
        "Consider â€” do not assume â€” the RCA's Hardening item 8 (sweep the remaining ported artifacts for domain residue of the `1230 games` kind). Two instances found by accident in one sitting is weak evidence that a deliberate pass would find none. If you do not run it, say so and leave it as a follow-up rather than implying the sweep happened.",
        "EVERY citation you write in these documents is an inline code span, never a Markdown link. `tests/test_doc_links.py` has no fence awareness (line 10) and does not strip a `:123` suffix (line 30), so an ordinary citation turns CI red. This is a live workaround, and forgetting it is how this phase fails."
      ],
      "acceptance": [
        "`uv run pytest tests/test_doc_links.py` passes with the new documents in the tree.",
        "`uv run pytest tests/test_skill_references.py` passes.",
        "The Index row's Stage cell and every artifact's Status blockquote agree, and both use the track README's grammar.",
        "Full local green: `uv run pytest`, `uv run ruff check`, `uv run mypy`."
      ],
      "commit_note": "Record the fix: statuses, Index row, and the report â€” with what stays open named explicitly."
    }
  ],
  "testing": "THE ACCEPTANCE CONTRACT (bugfix track, `requests/bugfix-requests/README.md:24`): the red repro goes green, a regression test is left behind, and nothing else regresses.\n\nRED -> GREEN. `tests/test_skill_references.py` holds both repro tests and is already committed on this branch (contrary to the RCA's note that it was not yet landed â€” I ran it: both fail today, and `git status` is clean). `test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` flips in Phase 1; `test_every_test_file_a_skill_names_exists` flips in Phase 2. Both are offline, deterministic, and inside CI's `-m \"not gamedata\"` selection.\n\nTHE REGRESSION TESTS LEFT BEHIND. The repro module IS the regression guard for the two token classes it covers, and it is direction-independent by construction â€” it asserts only that an artifact's references resolve against the repo it lives in, which holds whichever way the sibling doc-link decision goes. Phase 3 adds a second, complementary guard inside the `.mjs` itself (loud failure on an undefined lens key, derived from `acceptance_panel.js`), and Phase 4 adds a third (status words parsed from the track READMEs). Each of the three derives its expectation from the single upstream declaration rather than pinning a second copy â€” that is what stops the next rename from reproducing the bug.\n\nTHE HUMAN-READABLE CHECK stays `node .claude/skills/implement-plan/tests/verify_batching_guard.mjs`. Expected after Phase 1: `[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0`, `[dead-batch] verifiers=4/5 unverified=3/9`, `[rubberstmp] b1Calls=2 verifiers=4/5 unverified=3`, `[verifyCap ] cap=2 batches=2 unverified=0/9`, then GREEN and exit 0. I reproduced that exact output from a scratchpad copy at plan time, so it is a measurement rather than a prediction.\n\nNEGATIVE TESTING IS MANDATORY, NOT OPTIONAL. Phases 3, 4 and 5 each require demonstrating the new guard FAILING on the condition it claims to catch before accepting it green. A guard that has only ever been observed passing is exactly the artifact this whole request is about â€” `verify_batching_guard.mjs` had only ever been observed failing, and nobody checked which side was wrong for months. Do the corruption experiments in the scratchpad directory (`.mjs`) or in the working tree with an immediate restore (Python), never in a commit.\n\nNO-REGRESSION BASELINE. The four sibling guards all exit 0 today (measured 2026-08-17, Node v24.15.0): `.claude/skills/implement-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/scope-feature/tests/merge_fallback_guard.mjs`, `.claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs`, `.claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs`. Re-run all four at every checkpoint. `git diff --name-only` must never list `.claude/skills/implement-plan/acceptance_panel.js`.\n\nPER-PHASE CADENCE. Every phase ends at a gated checkpoint: implement -> green locally on `uv run pytest`, `uv run ruff check` and `uv run mypy` -> the guard runs above -> `/commit`, which stages deliberately, runs the doc gate and asks before writing. Agents commit only through `/commit` â€” never `git commit` ad hoc, not for a two-word change. `/commit` pushes the feature branch; opening and merging the PR stay the operator's, and `main` is never pushed, force-pushed, or amended. Expect the doc gate to trigger in Phase 1 on `.claude/agents/data-engineer-memory.md` appearing in the staged diff (`commit/SKILL.md:96-99`) â€” that trigger is the file's presence, so it is expected, not a problem.\n\nWHAT CANNOT BE TESTED HERE. The panel's real behaviour under live agents is not exercised by any of this; the guard stubs every agent. Phase 1 restores a proof about the panel's batching arithmetic and degradation paths, not a proof that stage 4 finds bugs.",
  "risks": [
    "THE BIGGEST RISK IS FIXING THE WRONG SIDE, AND IT IS ALREADY RETIRED â€” DO NOT REOPEN IT. The RCA settled by experiment that `acceptance_panel.js` is correct: re-keying two fixture entries turns the guard green with the panel untouched. Editing the panel to satisfy the guard as originally written would rename this repo's `parser` and `warehouse` lenses into a sibling's vocabulary AND loosen a dedupe that is already right (`jaccard >= 0.5` at `acceptance_panel.js:317` is precisely what keeps `writer.py:42` and `writer.py:60` apart). Both requests name that as the worst available outcome. If any step tempts you toward the panel, stop.",
    "THE WRITE-CAPABLE SUBAGENT MAY NOT BUILD THIS. Every path here â€” `.claude/skills/**`, `tests/**`, `.github/workflows/ci.yml` â€” is in the repo-level deny set in `.claude/agents/data-engineer.md` (`## Write allowlist`), pinned by `tests/test_agent_contract.py:80`. Its own instruction is to STOP and report if the spec's targets fall inside it. The main thread implements this directly. Read-only subagents are fine for grounding and get read-only git (never checkout/reset/restore/clean/stash/commit).",
    "THE PLAN DOCUMENT CAN TURN CI RED BY EXISTING. `tests/test_doc_links.py` scans every tracked `*.md` outside `var/` with one regex and no fence awareness (lines 10, 15) and strips only `#fragments`, not `:123` suffixes (line 30). Write every citation as an inline code span. Both RCAs and the first-sight plan declare this convention at their heads for exactly this reason. It is the defect this request is a sibling of, working as a tax on the request itself.",
    "SCOPE BLEED INTO THE UNDECIDED DOC-LINK CONTRACT. Phase 2 corrects a file-NAME token on seven lines. It is tempting, while editing those sentences, to also 'fix' the promises about fenced content, `file.py:123`, `var/` targets, or the bare-token scan. Those promises are `requests/bugfix-requests/_done/doc-link-guard-mismatch/`'s gated decision, which the operator has not disposed. Touching them decides it by implication â€” the outcome that request explicitly names as the worst.",
    "A KNOWN CONSEQUENCE OF PHASE 2, ACCEPTED KNOWINGLY. Pointing six skills at `tests/test_doc_links.py` makes a still-false promise more concrete: the sentence now names a real guard that does not implement the exemptions it describes. That is strictly better than naming a file that does not exist at all (which produces a pytest collection error the moment an agent obeys), and it is direction-independent. But say so in the report rather than letting it read as fully fixed.",
    "THE ROSTER-DERIVATION REGEX IS ITSELF A DRIFT SURFACE. Phase 3 parses `key: '...'` out of `acceptance_panel.js`; `tests/test_skill_references.py:37` and `:40` already do the same for the panel and the fixture. Three regexes over source text can all silently match nothing if the panel's style changes. Every one of them must fail loudly on an empty parse â€” `test_skill_references.py:99-100` already does exactly that (`parsed no lens keys ... the regex has drifted`); mirror that assertion in the `.mjs`, or you have replaced a silent miscount with a silent no-op.",
    "THE CI NODE STEP IS THE ONE UNCONFIRMED CLAIM IN THE RCA, AND IT IS LOAD-BEARING FOR PHASE 5. `ci.yml:37-49` has no node step today; 'ubuntu-latest ships node' is a belief. Verify it on the PR's own run (print `node --version`) before treating the step as protection. A step that skips when node is missing would pass vacuously â€” worse than no check, per the infra-cost mandate at `acceptance_panel.js:201` item 4.",
    "A NEW CI JOB WOULD SILENTLY STALL EVERY PR. `ops/branch-protection.json:5` requires the context `Lint, types, tests`. Adding a job rather than a step, or renaming the job at `ci.yml:17`, leaves PRs waiting on a check that never reports â€” the trap the comment at `ci.yml:13-15` spells out. Add a STEP to the existing job.",
    "THE MEMORY FILE IS APPEND-ONLY AND THE ENTRY SHAPE IS MECHANICALLY CHECKED. `.claude/agents/data-engineer-memory.md:41` says append freely and never prune; `tests/test_agent_contract.py:84-95` fails any dated entry without one of the five epistemic labels. Correct the falsified 2026-08-15 entry at lines 151-155 by appending a new dated entry, not by rewriting it. Rewriting history in the ledger is the same failure as marking a status down silently.",
    "STATUS-WORD PRECISION. `plan`/`planned` and `root-cause`/`diagnosed` are drift only in the past-tense STAGE slot; `next: plan` and `next: implement` are correct as written. Getting the direction backwards in Phase 4 would break the header of every artifact in `requests/`, and the guard you add would then enforce the wrong grammar repo-wide.",
    "NOTE FOR THE COLD IMPLEMENTER: `docs/data-sources.md` DOES NOT EXIST in this repo. The analogous document is `docs/data-access.md` (listed in `CLAUDE.md`'s project map, with the epistemic labels that matter). Nothing in this change touches it â€” no data source is added, read, or characterised â€” so no docs-delta is owed to it. Do not invent an entry there to look thorough."
  ],
  "files_to_touch": [
    {
      "path": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs",
      "change": "Phase 1: line 54 `'data-contract': [` -> `warehouse: [`; line 58 `extraction: [` -> `parser: [`; line 150 comment -> `// -> warehouse + parser + skill-quality specialists`. Phase 3: add a startup roster check derived from `SRC` (fail loudly, and fail on an empty parse) and replace the `|| []` at line 78 with a strict lookup that exits 1 naming the missing key."
    },
    {
      "path": ".claude/skills/implement-plan/acceptance_panel.js",
      "change": "DO NOT MODIFY. Listed here so its absence from the diff is deliberate and checkable â€” it is the RCA's central claim. Read lines 189-209 (the lens roster) and 298-317 (the dedupe) to ground Phases 1 and 3."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "change": "Phase 1: APPEND one dated, `verified`-labelled, `harness`-tagged entry correcting the falsified claim at lines 151-155. Never edit or prune an existing entry (that file's line 41)."
    },
    {
      "path": ".claude/skills/commit/SKILL.md",
      "change": "Phase 2: line 104, `tests/test_request_links.py` -> `tests/test_doc_links.py`. Nothing else â€” line 133 already states the correct status grammar."
    },
    {
      "path": ".claude/skills/update-docs/SKILL.md",
      "change": "Phase 2: line 56, `tests/test_request_links.py` -> `tests/test_doc_links.py`."
    },
    {
      "path": ".claude/skills/make-feature-request/SKILL.md",
      "change": "Phase 2: line 246, `tests/test_request_links.py` -> `tests/test_doc_links.py`. Leave the surrounding exemption promises alone."
    },
    {
      "path": ".claude/skills/make-bugfix-request/SKILL.md",
      "change": "Phase 2: line 199, `tests/test_request_links.py` -> `tests/test_doc_links.py`. Leave the surrounding exemption promises alone."
    },
    {
      "path": ".claude/skills/diagnose-bug/SKILL.md",
      "change": "Phase 2: line 176 `tests/test_request_links.py` -> `tests/test_doc_links.py`; lines 117-118 re-ground the worked example on `tests/test_byte_accounting.py::test_the_team_count_matches_the_export_on_the_only_save_that_has_one` with a domain-true failure line (drop `1230 games`). Phase 4: lines 97, 107, 150 `root-cause` -> `diagnosed`; decide deliberately about the frontmatter at line 7."
    },
    {
      "path": ".claude/skills/create-implementation-plan/SKILL.md",
      "change": "Phase 2: line 251 `tests/test_request_links.py` -> `tests/test_doc_links.py`. Phase 4 (confirm with the operator â€” a fourth instance found while planning, not enumerated in the RCA): line 172 Index Stage cell `plan` -> `planned`; line 176 template header `Status: plan` -> `Status: planned`. Leave line 65's `next: plan` alone."
    },
    {
      "path": "tests/test_skill_references.py",
      "change": "Phase 4: add the status-grammar test, parsing the allowed stage words out of the two track READMEs' `**Status grammar:**` lines rather than hardcoding them, and failing on an empty parse the way lines 99-100 already do. Do not weaken either existing test â€” they are the repro."
    },
    {
      "path": ".github/workflows/ci.yml",
      "change": "Phase 5: add ONE step to the existing `quality` job after the pytest step at lines 46-49 that prints `node --version` and then runs all five `.mjs` guards by explicit path, failing on any non-zero exit. Do not add a job; do not rename the job at line 17."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "Phase 6: the Index row at line 53 â€” Stage cell `diagnosed` -> `planned` -> `fixed` as the work advances. `/commit` owns this; never mark ahead. The grammar at line 45 is the contract and is not edited."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/IMPLEMENTATION_PLAN.md",
      "change": "New. Opens `planned Â· created <today> Â· decided Â· next: implement`. Every citation an inline code span, never a Markdown link."
    },
    {
      "path": "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/IMPLEMENTATION_REPORT.md",
      "change": "New, at the end of Phase 6: before/after guard output verbatim, the deliberately-corrupted-copy runs, and what stays open (the doc-link gated decision; the untouched leak-guard request; Hardening item 8 if not run)."
    },
    {
      "path": "ops/branch-protection.json",
      "change": "DO NOT MODIFY. Listed so Phase 5 stays a step inside `Lint, types, tests` rather than a new job that branch protection cannot see."
    }
  ],
  "code_references": [
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:54",
      "claim": "`  'data-contract': [` â€” the first of two fixture keys naming a sibling repo's lens. Becomes `warehouse:`."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:58",
      "claim": "`  extraction: [` â€” the second. Becomes `parser:`. It holds the single finding at `src/ootp_ai/land/writer.py:60` whose absence produced the phantom 'over-merged land/writer.py' failure line."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:78",
      "claim": "`const spec = FINDINGS_BY_LENS[lensKey] || []` â€” the swallow. An unknown key returns an empty review with no error, so three of eleven findings vanished before dedupe. Phase 3 makes it exit 1."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:150",
      "claim": "`touchedAreas: ['transform', 'src', 'skills'],   // -> data-contract + extraction + skill-quality specialists` â€” the third and last site carrying the wrong vocabulary; the comment still teaches it."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:65-66",
      "claim": "`RAW_TOTAL` (11) and `DEDUPED_TOTAL` (9) are computed from the fixture, not from what the panel received â€” which is why the mismatch surfaced as six assertions about the panel rather than one about the fixture."
    },
    {
      "ref": ".claude/skills/implement-plan/tests/verify_batching_guard.mjs:172",
      "claim": "`if (label.startsWith('review:')) return reviewFor(label.slice('review:'.length))` â€” the stub dispatches on the panel's real lens label, which is why the fixture's key names must match the panel's roster exactly."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:189-194",
      "claim": "The four CORE lenses: `acceptance`, `fidelity`, `correctness`, `edgecases`."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:196-202",
      "claim": "`SPEC_DEFS` â€” the five specialists this repo actually defines: `parser`, `warehouse`, `builder`, `skill-quality`, `infra-cost`. Neither `data-contract` nor `extraction` appears."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:203-209",
      "claim": "`AREA_TO_SPEC` maps the guard's `['transform','src','skills']` to `warehouse`, `parser`, `skill-quality` â€” the exact two lenses the fixture was failing to feed, plus the one it fed correctly."
    },
    {
      "ref": ".claude/skills/implement-plan/acceptance_panel.js:298-317",
      "claim": "`normLocation` drops a trailing `:line` (line 300), but `:317` also requires `jaccard(titleTokens) >= 0.5` before merging â€” the dedupe the guard falsely accused of over-merging, and which must not be loosened."
    },
    {
      "ref": "tests/test_skill_references.py:47",
      "claim": "`test_every_test_file_a_skill_names_exists` â€” RED today (7 broken references across 6 skill files); flips in Phase 2."
    },
    {
      "ref": "tests/test_skill_references.py:84",
      "claim": "`test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines` â€” RED today with `['data-contract', 'extraction']`; flips in Phase 1. Verified by running `uv run pytest tests/test_skill_references.py` on the current tree."
    },
    {
      "ref": "tests/test_skill_references.py:99-100",
      "claim": "Both regex parses assert non-empty before comparing â€” the pattern Phase 3's `.mjs` roster check must copy so a drifted regex fails loudly instead of passing vacuously."
    },
    {
      "ref": "tests/test_doc_links.py:10",
      "claim": "`LINK = re.compile(r\"\\[[^\\]]*\\]\\(([^)]+)\\)\")` â€” one regex over raw text, no fence state, so a Markdown link inside a code fence is scanned as live. This is why every citation in the plan must be a code span."
    },
    {
      "ref": "tests/test_doc_links.py:30",
      "claim": "`clean = target.split(\"#\", 1)[0]` â€” a `#fragment` is stripped, a `:123` line suffix is not, so a cited line number stays part of the path and can never resolve."
    },
    {
      "ref": "tests/test_agent_contract.py:80",
      "claim": "Asserts `tests/`, `.github/`, `ops/`, `CLAUDE.md`, `docs/decisions/` all remain in the data-engineer's deny set â€” the guard behind 'the main thread implements this, not the subagent'."
    },
    {
      "ref": "tests/test_agent_contract.py:84-95",
      "claim": "`test_memory_entries_carry_an_epistemic_label` â€” the mechanical check the Phase 1 appended memory entry must satisfy (one of `measured|verified|inferred|assumed|unconfirmed` in backticks)."
    },
    {
      "ref": ".claude/agents/data-engineer-memory.md:151-155",
      "claim": "The 2026-08-15 entry calling this 'a pre-existing upstream defect, not a porting error', with evidence pointing at a `CLAUDE.md` section that no longer exists. Falsified by the RCA; corrected by appending, per line 41's no-prune rule."
    },
    {
      "ref": ".claude/agents/data-engineer.md Â§ Write allowlist",
      "claim": "Repo-level deny list includes `tests/`, `.github/`, `ops/`, and `.claude/` except the one memory file, with the standing instruction to stop and report if a spec's targets fall inside it. Every file in this plan does."
    },
    {
      "ref": ".github/workflows/ci.yml:37-49",
      "claim": "The complete quality job: ruff check, ruff format --check, mypy, `pytest -m \"not gamedata\"`. No node step â€” the gap Phase 5 fills, and the RCA's one *unconfirmed* claim."
    },
    {
      "ref": "ops/branch-protection.json:5",
      "claim": "`\"Lint, types, tests\"` is the single required status context, matching `ci.yml:17`. Phase 5 must add a step to that job, never a new job."
    },
    {
      "ref": "requests/README.md:12",
      "claim": "'Each track's README is the contract' â€” the sentence that settles the status-word conflict in favour of the track READMEs over the skills."
    },
    {
      "ref": "requests/bugfix-requests/README.md:45",
      "claim": "`intake -> diagnosed -> planned -> fixed`, corroborated by `.claude/skills/commit/SKILL.md:133`; contradicted by `.claude/skills/diagnose-bug/SKILL.md:97,107,150` and `.claude/skills/create-implementation-plan/SKILL.md:172,176`."
    },
    {
      "ref": "requests/bugfix-requests/README.md:24",
      "claim": "'Done means the red reproduction goes green and a regression test is left behind' â€” this plan's acceptance contract, per the bugfix track."
    },
    {
      "ref": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1",
      "claim": "`> **Status:** planned Â· created 2026-08-16 Â· decided Â· next: implement` â€” the in-repo precedent proving `planned`, not `plan`, is the correct stage word."
    },
    {
      "ref": ".claude/skills/implement-plan/SKILL.md:309",
      "claim": "The contract the guard is supposed to satisfy, quoting the run command verbatim â€” so the guard's `RUN:` line at `verify_batching_guard.mjs:26` and its path must not change."
    },
    {
      "ref": "tests/test_byte_accounting.py:154",
      "claim": "`test_the_team_count_matches_the_export_on_the_only_save_that_has_one` â€” a real test in this repo, the domain-true replacement for the `test_extract_pagination.py` / `1230 games` example at `diagnose-bug/SKILL.md:117-118`."
    }
  ],
  "open_questions": [
    "Should `.claude/skills/create-implementation-plan/SKILL.md:172,176` be corrected from `plan` to `planned` inside THIS request? It is the same one-word port-drift class as the RCA's third instance, and it is provably wrong against `requests/README.md:12` + both track READMEs + the first-sight plan's own header â€” but the RCA enumerated only `diagnose-bug`. Recommendation: include it, because leaving it means the very next planner writes the wrong word again and the Phase 4 guard would then be red on a file the plan declined to touch. Operator's call.",
    "Does `.claude/skills/diagnose-bug/SKILL.md:7` (frontmatter, `intake -> root-cause -> reuse plan/implement`) count as drift? It names the PIPELINE stage rather than an artifact's status word, and the track README's own pipeline table at lines 14-18 labels stage 2 'Root cause'. Recommendation: leave it and say so, rather than changing it silently.",
    "Phase 2 makes six skills name a guard that exists but does not implement the exemptions those same sentences promise. Should a one-clause pointer to `requests/bugfix-requests/_done/doc-link-guard-mismatch/` be added alongside each corrected name, or does that bleed into the other request's undisposed decision? Recommendation: no pointer; record the known-incomplete state in the IMPLEMENTATION_REPORT instead, where it cannot be mistaken for a promise.",
    "Should the Phase 5 CI step run all five `.mjs` guards, or only the two under `implement-plan`? All five exit 0 locally today, so the broad version costs nothing now â€” but it makes any future skill guard a blocking CI check by default, which is a policy choice ('mechanical checks live in CI') rather than a fix. Recommendation: all five, enumerated explicitly so a deleted guard fails the step rather than shrinking a glob to zero.",
    "Is the RCA's Hardening item 8 (sweep the remaining ported artifacts for sibling-repo domain residue) in or out? Two instances were found by accident in one sitting, which is weak evidence that a deliberate pass would find none â€” but it is an open-ended search with no acceptance criterion. Recommendation: out of this request, filed as a fresh intake so it gets its own scope rather than expanding this one silently.",
    "Should Phase 3's strict `reviewFor` `process.exit(1)` or `throw`? Exiting is louder and matches the guard's existing exit-code contract at lines 285-292; throwing would be caught by the harness's own `try/catch` in `pipeline`/`parallel` (lines 132-141) and could be swallowed. Recommendation: exit, and verify by corrupting a scratchpad copy â€” I confirmed the exit form produces a clean `ERROR:` diagnostic."
  ]
}
```
