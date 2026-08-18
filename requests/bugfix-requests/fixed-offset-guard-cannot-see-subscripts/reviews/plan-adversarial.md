# Planning panel — adversarial findings and meta-audit

Unfiltered. 27 adversary findings, 19 meta-audit findings, 6 gated decisions.
One blocker, applied before the plan was written.
Panel health: {"planners_ok": 3, "adversaries_ok": 2, "meta_audit_ok": 1, "findings": 46, "blockers": 1, "majors": 14}
Degraded lenses: []

> **Machine paths stripped.** The panel's subagents emit absolute paths; this repo is
> public and `tests/test_no_leaks.py` refuses them (ADR 0006). Paths here are
> repo-relative. Nothing else was altered.

## Reviewer summaries

```json
[
  {
    "reviewer": "code-grounded",
    "kind": "adversary",
    "summary": "CODE-GROUNDED VERIFICATION of every reference the plan cites. I read (not skimmed) tests/test_no_fixed_offsets.py in full, src/ootp_ai/parser/{primitives,players,teams,world,human_managers,header,__init__}.py at every cited line, tests/{test_leak_guard_scope,test_sequential_walk,test_agent_contract,test_parse_players,test_parse_real_save,test_byte_accounting}.py, tests/fixtures/synthetic.py, pyproject.toml, .github/workflows/ci.yml, CLAUDE.md, docs/data-access.md, .claude/agents/data-engineer.md, requests/bugfix-requests/README.md, and both upstream artifacts; I ran `uv run pytest tests/test_no_fixed_offsets.py` and enumerated src/ootp_ai/*.py./n/nVERDICT: the plan's citation accuracy is unusually high — I found NO fictional file, function, symbol, or claimed-reuse. Every one of the ~60 code_references resolves. Spot-verified highlights: FixedOffsetVisitor really does define only `_nonzero_literal` (:36-41) and `visit_Call` (:43) with `generic_visit` at :62; the red repro is genuinely RED with the exact message quoted (4 passed, 1 failed at :124); the three `_peek_u32` copies exist at teams.py:596 / players.py:577 / world.py:874 with the quoted docstrings, players' alone carrying the `position < 0` guard at :579; `_GAP_AFTER_BIRTH_DATE` really is at :244, twenty-five lines BELOW `_AGE_LOOKAHEAD` at :220 (the NameError trap is real); the Phase 5 arithmetic checks out exactly against `_read_record`:451-456 AND against `make_player_head`'s byte assembly at synthetic.py:289-295 (birth at 12, age at 19) AND against the record+55 mask cross-check at :264; all five `teams._peek_u32` call sites and all seven `world._peek_u32` call sites match; 17 modules under src/ootp_ai (floor of 12 is sound); every cry-wolf control (`tail[4]`, `run[base + 1]`, `pattern[_LENGTH_PREFIX_WIDTH:]`, `values[4]`, `payload[/"manifest_version/"]`, `raw[-1].team_id`) is real at the line given; ci.yml:46/49/52/57 and pyproject.toml:91-95/98-108 are exact; test_agent_contract.py:62's `/"fixed offset/"` needle and :76-81's deny set are real./n/nWhat I DID find is a different class of defect: the plan's rule SPECIFICATION has two gaps that will stall Phase 2/6 mid-flight, plus several acceptance criteria that are unsatisfiable or self-contradictory as written. Nothing rises to blocker — the ordering thesis, the seam design, and the phase gating all survive."
  },
  {
    "reviewer": "executability",
    "kind": "adversary",
    "summary": "Executability & sequencing review, grounded by reading every file the plan cites and by running `uv run pytest tests/test_no_fixed_offsets.py` (1 failed, 4 passed — repro confirmed red), `uv run ruff check .` (green) and a full enumeration of `data[`/`buf[` sites under `src/ootp_ai/` (21 code sites outside primitives.py — the plan's measurement is exactly right, as are its `_peek_u32` call-site lists, world.py:202-209, players.py:219-220/244/451-456, test_agent_contract.py:62/76-81, ci.yml:46/49/52/57, pyproject.toml:91-95/98-108, and the 17-module count). The MIGRATE-FIRST/WIDEN-SECOND spine is correct and is the plan's best decision; the annotation-grounded rule genuinely has zero false positives on the tree I checked; `tests/fixtures/synthetic.py` imports nothing from `ootp_ai`, so Phase 5's pin test is a real independent check rather than a circular one. The plan is strong on WHAT and weak on a handful of HOWs that a cold agent cannot supply. Seven issues would actually stop or mislead an implementer: (1) Phase 4's central test calls a whole-tree scan callable that does not exist and that no phase creates — `test_no_fixed_offsets.py` exposes only `scan_source`, unlike `test_no_leaks.py` which exposes the four functions that make its meta-guard possible; (2) Phase 1's /"copy the date decode verbatim from world.py:744-746/" produces code that Phase 3's own stricter interior rule then flags, a collision that surfaces two phases after the gate that would have caught it; (3) Phase 6's rule never states what happens to a position argument that is a local — the phase's acceptance is green or catastrophically red depending on an unstated default; (4) Phase 2 is declared the one delegable phase while its own steps edit `tests/test_save_header.py`, which is in the subagent deny set; (5) Phase 2's acceptance grep is falsified by a docstring line the plan itself preserves; (6) the Phase 3 subscript rule is evaded by a two-line local hoist that is idiomatic in this very parser (world.py:738-740), and the plan documents that residual only for Phase 6; (7) the gamedata gates — the plan's only oracle — pass vacuously when saves are absent. The rest are cost, precision and citation issues."
  },
  {
    "reviewer": "meta-audit",
    "kind": "meta_audit",
    "summary": "META-AUDIT OF THE MERGE (not the repo). I read the decided RCA in full, then verified the merged plan's load-bearing citations against the working tree at df17337 on branch `fix-fixed-offset-guard-subscripts`. The merge's grounding is unusually good: every line number I spot-checked resolved — tests/test_no_fixed_offsets.py:26/:36-41/:43/:62/:96-99/:115-127/:143-155, players.py:219-220/:244/:383/:451-456/:540-561/:572-592, teams.py:581-605 (the five `_peek_u32` call sites at :375/:509/:559/:571/:587 are exactly five), world.py:202-209/:725-761/:844+:851/:859-883 (seven call sites, exactly as listed), human_managers.py:196-250, header.py:5-8/:79/:103-114, primitives.py, test_agent_contract.py:62/:76-81/:84-95, test_leak_guard_scope.py:1-21/:40-53, ci.yml:46/49/52/57/66-78, pyproject.toml:91-95/98-108, docs/data-access.md:228-230/275-282/284-289, bugfix README:24-26/45/51/53. The 17-module count and the 21-site inventory both check out; `looks_like_save_file` genuinely has no test (only caller saves.py:119), correcting planner 1's unverified claim. Convergence on the load-bearing calls — migrate-then-widen, annotation-keyed detection, raw-not-validating shared date, gamedata-invisible-to-CI, subagent deny set — is faithful and well argued./n/nWhere the merge is weaker is at its edges. It invented a whole phase the RCA never named (Phase 6, constant folding), gated it, and then recommended shipping it — while leaving the equally novel Phase 4 ungated. It silently dropped one planner's entire Phase 1 (the census) and three of that planner's and planner 3's recorded open questions, including a direct planner-vs-planner disagreement about editing docs/data-access.md. It carries two internal contradictions that will actually bite a cold implementer: a Phase 2 acceptance grep that primitives.py:140 fails by construction, and a Phase 6 legality rule stated two incompatible ways, the stricter of which fires on a line Phase 2 itself writes into human_managers.py. And it calls things cheap or behaviour-preserving that the tree shows are neither. Most seriously, its own D4 (no per-site exemptions) makes the bugfix's acceptance contract unreachable on a machine without local OOTP saves — a consequence the merge never states."
  }
]
```


## Convergence map

```json
[
  {
    "theme": "MIGRATE FIRST, WIDEN SECOND — the lookahead seam must land and every caller must be rewired BEFORE `visit_Subscript` exists.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three arrived at the same phase ordering from different starting points, and the sequencing and domain lenses both stated the consequence explicitly: the moment the visitor exists, the whole-tree scan at tests/test_no_fixed_offsets.py:143 goes red on ~ten legitimate lines across five modules, and the implementer facing a broken build reaches for the loosening the guard's own docstring warns about at :9-10. Independent convergence on an ORDERING (rather than a component) is the strongest kind here, because ordering is the thing a cold implementer is most likely to get wrong by instinct."
  },
  {
    "theme": "One new module `src/ootp_ai/parser/lookahead.py` as the single sanctioned home for buffer indexing, with the guard keyed on MODULE PATH rather than on syntax or on a helper-name convention.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "This is the RCA's Root tier, but all three planners independently reached the same argument for why the diff is small rather than large: three byte-identical `_peek_u32` copies (teams.py:596, players.py:577, world.py:874), two near-identical `_scan_string`, two copies of the same raw date decode. Extracting them is deleting duplication, not inventing architecture — and each of the three copies carries a docstring asserting the rule in prose, which all three planners read as the seam announcing itself."
  },
  {
    "theme": "The buffer must be identified by TYPE ANNOTATION (`bytes`-annotated parameter), never by a hardcoded name list — and each planner produced its own measured false positives to prove it.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Three independent greps of the same tree produced three complementary counterexamples: snapshot.py:227 (`payload[/"manifest_version/"]` on a JSON dict) and teams.py:382 (`raw[-1].team_id`) kill the naive name set; players.py:383 and human_managers.py:154 (`tail[4]`) kill the wider 'any subscript in a bytes-param function' rule. Two planners also noted the same defence: mypy strict over `src` and `tests` (pyproject.toml:91-95) makes dropping an annotation loud, so evading the guard requires failing a second independent check."
  },
  {
    "theme": "Do NOT share a validating `peek_date` — world.py:749 admits `year == 0` where players.py:592 rejects it, so the shared primitive must return raw unjudged fields.",
    "planners": [
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Both planners found this by reading BOTH call sites rather than assuming two similarly-named helpers were interchangeable, and both named the same consequence: a naive collapse would silently narrow `_scan_event`'s accept set and break the calendar walk with nothing raised. That is a silent parse change introduced by the fix for a silent-parse-change bug — the single most embarrassing failure mode available here, and the one a cold implementer is most likely to walk into while 'tidying up duplication'."
  },
  {
    "theme": "CI structurally cannot prove the refactor, because `.github/workflows/ci.yml:57` runs `pytest -m /"not gamedata/"` — so the only oracle is a LOCAL baseline captured before the first edit.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three reached the same conclusion and two escalated it to a stop condition: an implementer without local saves cannot complete the refactor phases to acceptance. This inverts the normal instinct that a green PR means safety, and it is exactly the kind of thing a cold agent assumes rather than checks. The domain lens added the operational form — capture the numbers first, diff them at every gate — which is what makes 'unchanged' checkable rather than asserted."
  },
  {
    "theme": "Most of this work CANNOT be delegated to the write-capable data-engineer subagent, because its deny set covers `tests/` and `CLAUDE.md`.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three located the same enforcement (tests/test_agent_contract.py:76-81) and the same stated reason at :77 — 'An agent that can edit the tests that catch it is the core failure mode.' A plan that quietly assumed the subagent could do the work would stall at Phase 3. Convergence here is about a process constraint that is invisible from the code and only readable from the contract test."
  },
  {
    "theme": "Correcting the four overclaiming documents is HALF THE FIX, not optional polish — and dropping it leaves a NEW false claim where the old one was.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three traced the same specific consequence: primitives.py:12-13's 'zero exemptions' becomes false the moment an allowlist exists. The RCA refuted the docs-only option precisely because it would replace one wrong claim with another (:101-108); shipping the guard without Phase 7 does exactly that, from the other direction. Two planners also independently found the constraint that Phase 7 must respect — tests/test_agent_contract.py:62's literal `/"fixed offset/"` needle."
  },
  {
    "theme": "The guard must be SEEN TO FAIL — mutation checks run by hand, reverted, never committed, and recorded verbatim.",
    "planners": [
      "code-grounded",
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "All three cited the repo's own institutional memory rather than general good practice: test_no_fixed_offsets.py:103 ('A guard never seen to fail is not a guard'), tests/test_sequential_walk.py:10-12's negative control, and .github/workflows/ci.yml:66-69 recording that `verify_batching_guard.mjs` was RED from the day it landed and nothing noticed for the life of the skill. The domain lens went further and made the meta-guard a whole phase, modelled on tests/test_leak_guard_scope.py — the same shape this repo adopted after the previous guard bugfix."
  },
  {
    "theme": "The two lookahead constants derive EXACTLY from `_read_record`'s field order (4+4+4 = 12; +4+3 = 19), and `_GAP_AFTER_BIRTH_DATE` must be MOVED above them or the module raises NameError at import.",
    "planners": [
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "Both derived the same arithmetic from players.py:451-456 and both flagged the ordering trap independently — the gap constants sit at :244-247, twenty-five lines below the lookaheads at :219-220. That failure presents as a collection error taking the whole suite down, i.e. as a broken repo rather than a missed edit, which is the worst way for a cold implementer to meet it. Both also insisted the OFFLINE pin (`== 12`, `== 19`) be the first line of defence so a mis-derivation fails before the gamedata run."
  },
  {
    "theme": "The `_WIDTH` / `_GAP_` declared-span convention is already in force at world.py:743 and players.py:244-247, and is the legal form a record-relative constant may take.",
    "planners": [
      "sequencing",
      "domain-convention"
    ],
    "why_high_signal": "The RCA named world.py:743 as 'the model to copy' but did not turn it into a rule. Two planners independently proposed doing exactly that, and the tree confirms the convention is unbroken: world.py:202-209 defines seven `_WIDTH` constants and derives an eighth from four of them. A convention that already holds everywhere is a convention a guard can encode without a migration — which is what makes Phase 6 cheap enough to be worth having."
  }
]
```


## Adversary findings

```json
[
  {
    "id": "F1",
    "title": "peek_length_prefixed's proposed return shape forces callers to write `position + 4`, which Phase 6's own rule then flags",
    "severity": "major",
    "confidence": "high",
    "category": "spec-gap",
    "location": "src/ootp_ai/parser/teams.py:590",
    "problem": "Phase 1 specifies `peek_length_prefixed(data, position, limit) -> tuple[int, int] | None` and Phase 2 says to rewrite teams.py `_scan_string` (:581-593) and world.py `_scan_string` (:859-871) over `peek_length_prefixed` + `is_printable_ascii`. But both real implementations need the PAYLOAD START, not just `(length, end)`: teams.py:590 reads `payload = data[position + 4 : position + 4 + length]` and world.py:868 is identical. With `(length, end)` returned, the rewritten caller must compute the payload start itself as `is_printable_ascii(data, position + 4, length)` — a bare nonzero int literal as the second positional argument of a lookahead call, which is EXACTLY what Phase 6's declared-span rule flags (`position + 4` bottoms out in a bare literal that is not a `_WIDTH` or `_GAP_` name). Neither teams.py nor players.py defines a `_LENGTH_PREFIX_WIDTH`; only world.py does, at :207. So Phase 2 as written produces code that Phase 6 turns red, and the implementer has no stated escape.",
    "proposed_fix": "Change the Phase 1 surface: either have `peek_length_prefixed` return `(payload_start, end)` (teams' caller then derives `length = end - payload_start`), or add a single `peek_length_prefixed_ascii(data, position, limit)` to lookahead.py that does the prefix read, the bounds check and the printability filter in one call, returning `(length, end)` — which collapses BOTH `_scan_string` bodies to one line and eliminates the `position + 4` arithmetic entirely. Additionally, export `LENGTH_PREFIX_WIDTH` from lookahead.py alongside `U8_WIDTH`/`U32_WIDTH`/`DATE_WIDTH` so any residual caller arithmetic is a declared span.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F2",
    "title": "Phase 6's constant-folding rule is under-specified for non-constant leaves and for multiplication, and will cry wolf on the code Phase 2 just wrote",
    "severity": "major",
    "confidence": "high",
    "category": "spec-gap",
    "location": "src/ootp_ai/parser/human_managers.py:248",
    "problem": "Phase 6 defines legality only over module-level constants: a Name is legal iff it ends `_WIDTH`, begins `_GAP_`, or derives recursively from such names; 'A Name whose definition bottoms out in a bare nonzero int literal that is not itself a declared span is an OFFSET, and is flagged.' Two shapes fall outside that spec entirely. (a) LEAVES WITH NO MODULE-LEVEL DEFINITION: after Phase 2, human_managers.py:248 becomes `peek_u32(data, offset + slot * _U32_WIDTH)` where `offset` is a parameter and `slot` a comprehension variable; neither appears in the module-constant table, and the spec never says whether an unknown Name is legal. Read one way the rule flags every ordinary call site in the parser. (b) MULTIPLICATION: the spec speaks only of 'addends', but `slot * _U32_WIDTH` is a `Mult` BinOp — the same shape already exists at human_managers.py:228 (`CLUB_SLOTS * 4`). The plan's own DERIVED_INNOCENT/WIDTH_SUM_INNOCENT fixtures are all pure addition, so the fixtures cannot surface either gap.",
    "proposed_fix": "State both rules explicitly in the Phase 6 step and add fixtures for them: (a) a Name absent from the module-level constant table is LEGAL (it is a runtime value, not a constant) — and note that this is the same boundary as the already-documented local-variable residual, not a new hole; (b) a `Mult` node is legal iff at least one operand is a declared span and neither operand is a bare nonzero literal, so `slot * _U32_WIDTH` passes and `slot * 4` does not. Add a `RUNTIME_LEAF_INNOCENT` fixture (`peek_u32(data, offset + slot * _U32_WIDTH)` with `_U32_WIDTH = 4` at module level) and a `BARE_MULT_OFFENDER` (`peek_u32(data, offset + slot * 4)`).",
    "reviewer": "code-grounded"
  },
  {
    "id": "F3",
    "title": "Phase 2's acceptance grep is unsatisfiable and contradicts the sweep step three lines above it",
    "severity": "minor",
    "confidence": "high",
    "category": "acceptance-criteria",
    "location": "src/ootp_ai/parser/primitives.py:140",
    "problem": "Phase 2's sweep step says 'The only surviving buffer-subscript hits must be inside `parser/lookahead.py` and `primitives.py:140`', but its acceptance bullet says /"`grep -rn 'data/[' src/ootp_ai/` returns hits only in `parser/lookahead.py`/". primitives.py:140 is `return self._data[start : start + count]` — the substring `_data[` matches the regex `data/[`, so the grep will always return that hit. A cold implementer treating the acceptance bullet literally would try to 'fix' `Cursor.take`, which every other part of the plan forbids ('`Cursor` is untouched by this entire plan').",
    "proposed_fix": "Reword the acceptance to match the step: /"`grep -rn 'data/[' src/ootp_ai/` returns hits only in `parser/lookahead.py` and the single known line `parser/primitives.py:140` (`self._data[start : start + count]` inside `Cursor.take`, which is an attribute read on the cursor's own buffer and is deliberately untouched)./" Or make the grep exclude it: `grep -rn '[^_.]data/[' src/ootp_ai/`.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F4",
    "title": "primitives.py does not need an allowlist entry under the plan's own rule, and Phase 4 hardcodes the redundant exemption into a test",
    "severity": "minor",
    "confidence": "high",
    "category": "design",
    "location": "src/ootp_ai/parser/primitives.py:140",
    "problem": "The Phase 3 rule flags an `ast.Subscript` whose VALUE is an `ast.Name` bound to a `bytes`-annotated parameter. primitives.py's only buffer subscript is `self._data[start : start + count]` at :140 — an `ast.Attribute`, never an `ast.Name` — and `self._data = data` at :84 assigns to an Attribute target, so the plan's alias tracking ('a local bound by a single-target Assign') does not bind it either. The plan concedes this itself in code_references: the line 'survives on two independent grounds'. So `ALLOWED_TO_INDEX` needs exactly ONE entry, not two. Meanwhile Phase 4 asserts '`ALLOWED_TO_INDEX` has exactly two entries', freezing a redundant exemption into a regression test — against the plan's own D4 rationale, which spent three lines rewriting `header.looks_like_save_file` specifically to avoid adding a second exemption.",
    "proposed_fix": "Either (a) drop `primitives.py` from `ALLOWED_TO_INDEX`, make Phase 4's integrity test assert exactly ONE entry, and add a Phase 4 cry-wolf control proving `self._data[start : start + count]` is unflagged on its own merits under the filename `src/ootp_ai/parser/primitives.py`; or (b) keep the entry and say plainly in the Phase 3 step WHY — that it is defence-in-depth against a future `Cursor` refactor that binds the buffer to a local — so the next reader does not read it as an oversight. Do not leave the choice implicit.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F5",
    "title": "The per-phase gate claims to run 'in CI's own order' but bare `uv run pytest` is not CI's command — pyproject carries no marker filter",
    "severity": "minor",
    "confidence": "high",
    "category": "testing",
    "location": "pyproject.toml:100",
    "problem": "`addopts = /"-q --strict-markers --strict-config/"` (pyproject.toml:100) contains NO `-m` filter, so a bare `uv run pytest` collects and runs the gamedata-marked tests too. CI runs `uv run pytest -m /"not gamedata/"` (.github/workflows/ci.yml:57). The testing section says 'THE PER-PHASE GATE, identical every time and in CI's own order (.github/workflows/ci.yml:46-57): `uv run pytest` → …', and Phase 1's step says to record baselines from '`uv run pytest -q` AND `uv run pytest -m gamedata -q`' as if the first were the offline half. On a machine with saves the two runs overlap; on a machine without them, the Phase 1 acceptance 'reports EXACTLY ONE failure' is measuring a different set than CI will.",
    "proposed_fix": "Split the gate explicitly: the CI-mirroring command is `uv run pytest -m /"not gamedata/"` and belongs at every phase gate; `uv run pytest -m gamedata` is the additional local-only oracle required by Phases 1, 2 and 5. State that a bare `uv run pytest` runs both, and use it only for the Phase 1 combined baseline. Restate Phase 1's 'exactly one failure' acceptance against `uv run pytest -m /"not gamedata/"`.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F6",
    "title": "The intake survey table the plan designates as the false-positive budget carries a second stale citation the plan does not correct",
    "severity": "minor",
    "confidence": "high",
    "category": "citation-drift",
    "location": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/BUGFIX_REQUEST.md:102",
    "problem": "The plan's onboarding tells the implementer that BUGFIX_REQUEST.md:100-106 'is the false-positive budget the new rule has to respect', and corrects exactly one stale row ('the two instances it cites as players.py:445,449 are now :553,:557'). But row one at :102 cites `players.py:481-482` for the intra-date decode, and those lines today are `age=age,` / `nation_id=nation_id,` inside the `PlayerRecord(...)` construction in `_read_record`; the decode it means is now at players.py:588-590. Phase 7's acceptance test — 'someone who reads only that docstring must be able to predict, for each of the six shapes in BUGFIX_REQUEST.md:100-106, whether it is flagged' — sends a cold reader to a dead line. (The intake itself is history and must not be edited; the plan is the place to carry the correction.)",
    "proposed_fix": "Extend the onboarding note on BUGFIX_REQUEST.md to correct BOTH rows: `players.py:481-482` → `players.py:588-590`, and `players.py:445,449` → `players.py:553,:557`. Note that `world.py:745-746`, `teams.py:590`, `world.py:868`, `human_managers.py:204,248` and `world.py:743` in that table are all still accurate as of 2026-08-18 (I re-verified each), so only those two rows have drifted.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F7",
    "title": "Phase 7's 'never edit requests/ artifacts' rule leaves an IN-FLIGHT plan asserting zero exemptions",
    "severity": "minor",
    "confidence": "high",
    "category": "doc-consistency",
    "location": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1083",
    "problem": "Phase 7 correctly forbids rewriting landed `requests/` artifacts and its grep acceptance passes anything under `requests/` as history. But `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1083` states the ban is enforced '(a forward-only cursor with no `seek`) *and* mechanically (an AST scan over the whole parser tree, zero exemptions)' — and that plan is NOT history: its Phase 6b and Phase 8 are still open work (the repo's task list carries 'Decode position, role, bats, throws and historical_id' and 'Build parser/rosters.py' as pending, and CLAUDE.md's Status section points at first-sight as the live track). An implementer executing first-sight after this bugfix lands will read a live instruction asserting an invariant that is no longer true. The blanket rule as written silently exempts it.",
    "proposed_fix": "Distinguish LANDED artifacts (history — never edit) from IN-FLIGHT ones (live guidance — must stay true). Add a Phase 7 step: append a dated correction note under `first-sight/IMPLEMENTATION_PLAN.md`'s Phase 3 section (do not rewrite the original sentence) recording that as of this bugfix the scan carries a named allowlist, and cite this bugfix's slug. Same treatment for `first-sight/reviews/handoff-phase-3.md:18` if that handoff is still being consumed.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F8",
    "title": "The plan overstates the `_is_club_landmark` bounds hazard — the only caller already bounds the range",
    "severity": "minor",
    "confidence": "high",
    "category": "correctness",
    "location": "src/ootp_ai/parser/human_managers.py:228",
    "problem": "The plan's Phase 2 step and its risks list both frame the `_is_club_landmark` migration as dangerous: 'a short slice near the buffer end returns a smaller integer rather than raising, so a truncated buffer could have produced a plausible landmark id'. But `_is_club_landmark` (:242) has exactly one caller, `_distance_to_club` (:214), whose comprehension at :226-230 iterates `range(position, len(data) - CLUB_SLOTS * 4 + 1)` — every offset it passes is already guaranteed to leave `CLUB_SLOTS * 4` bytes. No short slice is reachable from production code, so the `None` branch introduced by `peek_u32` is unreachable in practice, not a behaviour-change risk. Overstating it costs the implementer review time on the phase with the real risk. Separately, the plan's `_U32_WIDTH = 4` introduction covers :244 and :248 but not the `CLUB_SLOTS * 4` at :228, leaving a bare 4 in the same function family.",
    "proposed_fix": "Rewrite the step and the risk entry: the `None` branch must still be handled (mypy strict requires it, and it is a strict safety improvement for any future caller), but note that `_distance_to_club`:228 already guarantees the slice fits, so the migration cannot change what the walk accepts on any real buffer — the gamedata baseline will confirm this trivially. Extend `_U32_WIDTH` to :228 as well so the whole landmark family reads in named widths.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F9",
    "title": "Decision D1's enumeration of lines that go red on early widening is imprecise in both directions",
    "severity": "nit",
    "confidence": "high",
    "category": "grounding",
    "location": "src/ootp_ai/parser/world.py:744",
    "problem": "D1's rationale lists 'players.py:588-590, teams.py:590, world.py:744-746/759/868, human_managers.py:248, header.py:114' as the ~ten legitimate lines that would go red. Checked against the plan's own rule (Name-valued subscript on a `bytes` param, index containing a BinOp or a nonzero literal): players.py:588 is `day = data[position]` — a lone Name index, NOT flagged; world.py:744 is `day = data[date_at]` — likewise NOT flagged; world.py:740 (`data[pad_at:length_at]`, both bare Names) is in the architecture_map's site list but is also NOT flagged. Conversely the list omits human_managers.py:244 (`data[offset : offset + 4]`), human_managers.py:204 (`data[position + width]`) and teams.py:522 (`data[position : position + 1]`), all of which WOULD fire. The count ('roughly ten') and the conclusion (migrate first) are correct; the enumeration is not.",
    "proposed_fix": "Replace the list with the verified one: players.py:589, :590, :581; teams.py:522, :590, :605; world.py:745, :746, :759, :868, :883; human_managers.py:204, :244, :248; header.py:114 — fourteen lines across five modules. Add one sentence noting that players.py:588, world.py:740 and world.py:744 are lone-Name indices the rule does not flag, and that migrating them in Phase 2 is discipline rather than compulsion — which is the same asymmetry D3 already documents for world.py:844.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F10",
    "title": "Phase 3's interior rule for allowlisted modules is self-contradictory as stated",
    "severity": "nit",
    "confidence": "medium",
    "category": "spec-gap",
    "location": "tests/test_no_fixed_offsets.py:43",
    "problem": "Phase 3 says: 'Inside the allowlist: skip the buffer-name check but flag any bare nonzero int literal in a buffer subscript index.' If the buffer-name check is skipped, nothing defines what makes a subscript a 'buffer subscript' inside an allowlisted module — the rule collapses to 'any subscript with a nonzero literal index', which would fire on ordinary tuple/list indexing. It happens to be harmless today (primitives.py's `unpack_from(...)[0]` uses literal 0, excluded by `_nonzero_literal` at :39, and `self._data[start : start + count]` at :140 has no literal), but lookahead.py will contain the first real test of it and the implementer has no stated rule to code against.",
    "proposed_fix": "State the interior rule concretely: inside an allowlisted module, flag a subscript whose value is an `ast.Name` that is a `bytes`-annotated parameter (the SAME buffer test as outside) when the index contains a bare nonzero int literal, regardless of whether a BinOp is present. That keeps one buffer-identification mechanism, makes `data[position + 4]` illegal and `data[position + U32_WIDTH]` legal inside lookahead.py, and leaves ordinary tuple indexing untouched everywhere.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F11",
    "title": "Phase 7's grep sweep for 'CI enforces' hits an unrelated true claim, and the acceptance wording would force an edit to it",
    "severity": "nit",
    "confidence": "high",
    "category": "acceptance-criteria",
    "location": "tests/test_snapshot_semantics.py:24",
    "problem": "Phase 7 says: 'Grep the whole tree for surviving overclaims — `zero exemptions`, `CI enforces`, `never inspects a subscript`. Every hit must be either corrected or inside a `requests/` artifact recording history.' I ran that grep. `tests/test_snapshot_semantics.py:24` reads '…no game, so CI enforces all three' — a true statement about the snapshot-semantics tests, unrelated to the fixed-offset ban and not inside `requests/`. The acceptance as worded gives the implementer only two options for it, both wrong.",
    "proposed_fix": "Scope the sweep to the subject: grep for the three phrases and require every hit to be (a) about the fixed-offset ban AND corrected, (b) inside a `requests/` artifact recording history, or (c) about a different subject and left alone. Name `tests/test_snapshot_semantics.py:24` explicitly as the known (c) so the implementer does not have to re-adjudicate it.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F12",
    "title": "The rulebook is listed among the four 'overclaiming' documents, but its ban statement makes no claim about the mechanism",
    "severity": "nit",
    "confidence": "high",
    "category": "grounding",
    "location": ".claude/agents/data-engineer.md:69-74",
    "problem": "The plan's summary and Phase 7 goal say 'Four live claims in the tree are currently stronger than the mechanism' and Phase 7's steps then edit CLAUDE.md:103, data-engineer.md:69-74, primitives.py:11-13 and header.py:5-8. I read :69-74 in full: it states the rule ('Never seek to a fixed offset… Code that seeks is a blocker, not a style note') and its measured evidence (43 bytes vs 107). It makes NO claim about what enforces the rule, so it is not an overclaim — Phase 7's edit there is an ADDITION (naming the seam), not a correction. Only three documents actually overclaim: CLAUDE.md:103 ('CI enforces it'), primitives.py:12-13 and header.py:6 (both 'zero exemptions').",
    "proposed_fix": "Say 'three live overclaims plus one addition' in the summary and in Phase 7's goal, and mark the data-engineer.md step as an addition. It matters because Phase 7's step for that file is the one carrying the CI-red hazard (test_agent_contract.py:62's literal `/"fixed offset/"` needle) — an implementer who believes it is 'correcting a false claim' is likelier to rewrite the sentence than to append to it.",
    "reviewer": "code-grounded"
  },
  {
    "id": "F13",
    "title": "Phase 5's constant move orphans one gap constant from the comment that documents all four",
    "severity": "nit",
    "confidence": "high",
    "category": "maintainability",
    "location": "src/ootp_ai/parser/players.py:240",
    "problem": "Phase 5 says to MOVE `_GAP_AFTER_BIRTH_DATE` (:244) above the lookahead definitions at :219-220. That constant is the first of a four-constant block (:244-247) sharing one `#:` comment at :240-243 ('Unclassified spans inside the fixed head, named so the walk reads as a sequence of fields… Each is bytes the walk crosses and does not interpret — recorded in `contracts/field_map.toml` as unclassified, per the withhold-by-default rule.'). Moving one member out separates it from the rationale and from the field_map cross-reference that governs it.",
    "proposed_fix": "Move the WHOLE block — the comment at :240-243 plus all four constants at :244-247 — above the lookahead comment at :214, and place the three new width constants (`_PLAYER_ID_WIDTH`, `_NAME_INDEX_WIDTH`, `_DATE_WIDTH`) immediately beside them under their own `#:` comment. The lookahead definitions then read top-to-bottom as widths → gaps → derived lookaheads, which is the order `_read_record`:451-456 walks them in.",
    "reviewer": "code-grounded"
  },
  {
    "id": "EX-01",
    "title": "Phase 4's planted-offender test calls a whole-tree scan function that does not exist and no phase creates it",
    "severity": "blocker",
    "confidence": "high",
    "category": "missing-step",
    "location": "tests/test_no_fixed_offsets.py:143-155 (and plan Phase 4, step 2)",
    "problem": "Phase 4's central test says: /"call the REAL whole-tree scan (not `scan_source` on a string), assert the probe is named in the violations/". No such callable exists. I read `tests/test_no_fixed_offsets.py` in full: the only module-level functions are `scan_source` (:65-68) and the test functions. The whole-tree scan logic — rglob, the vacuous-pass assertion, the repo-relative posix filename, the accumulation into `violations` — is INLINE inside `test_no_parser_module_seeks_to_a_fixed_offset` (:143-155), and that function `assert`s rather than returning. So a cold implementer cannot write the Phase 4 assertion at all: importing and calling `guard.test_no_parser_module_seeks_to_a_fixed_offset()` raises `AssertionError` on the planted probe instead of yielding a list to search. The contrast with the precedent the plan tells them to copy is exact and damning: `tests/test_leak_guard_scope.py` works only because `test_no_leaks.py` exposes `scannable_text_files()`, `machine_path_violations()`, `git_paths()` and `game_data_offenders()` as callables (used at test_leak_guard_scope.py:74, :152, :175, :210, :233). Phase 3's steps — which are the last time the plan touches this file before Phase 4 — never prescribe the extraction. The same gap sinks Phase 4's coverage floor, which the plan writes as `len(sorted(SCAN_ROOT.rglob('*.py'))) >= 12`: that re-derives the candidate set inside the meta-guard rather than asserting the guard's own, so it survives exactly the mutant class the precedent exists to catch (test_leak_guard_scope.py:224-238 records a guard whose set collapsed to 9 files with every membership test still green).",
    "proposed_fix": "Add an explicit step to PHASE 3 (not Phase 4 — the file is 'finished' by then): extract two module-level functions in `tests/test_no_fixed_offsets.py` — `parser_modules() -> list[Path]` (the rglob plus the non-empty assertion) and `parser_module_violations() -> list[str]` (the loop building the repo-relative posix filename and calling `scan_source`) — and reduce `test_no_parser_module_seeks_to_a_fixed_offset` to `violations = parser_module_violations(); assert not violations, ...`, leaving its message text unchanged. Then rewrite Phase 4's steps to `import test_no_fixed_offsets as guard` and assert against `guard.parser_module_violations()` for the planted probe and `len(guard.parser_modules()) >= 12` for the floor, so both meta-assertions run through the same code the real test runs.",
    "reviewer": "executability"
  },
  {
    "id": "EX-02",
    "title": "Phase 1's /"copy the date decode verbatim/" produces code that Phase 3's own interior rule flags, and Phase 1's declared surface has no names to fix it with",
    "severity": "major",
    "confidence": "high",
    "category": "phase-collision",
    "location": "plan Phase 1 (/"Copy bodies from their current homes/") vs plan Phase 3 (/"Inside the allowlist … flag any bare nonzero int literal/"); source at src/ootp_ai/parser/world.py:744-746",
    "problem": "Phase 1 instructs: /"Copy bodies from their current homes rather than rewriting them: … the raw date decode from world.py:744-746/". That body is `day = data[date_at]`, `month = data[date_at + 1]`, `year = int.from_bytes(data[date_at + 2 : date_at + _DATE_WIDTH], ...)` — two bare nonzero int literals (`+ 1`, `+ 2`) inside a buffer subscript index. Phase 3 then installs a STRICTER interior rule: /"Inside the allowlist: … flag any bare nonzero int literal in a buffer subscript index — the stricter interior rule that forces `position + U32_WIDTH` over `position + 4`/". So `lookahead.peek_date_fields`, written exactly as Phase 1 prescribes, is a violation the moment Phase 3 lands. Phase 1's declared surface (`U8_WIDTH`, `U32_WIDTH`, `DATE_WIDTH`) contains no name that expresses '+1' or '+2' inside a date, so the fix is not a substitution — it requires inventing constants (`_DAY_WIDTH = 1`, `_MONTH_WIDTH = 1`) that no phase mentions. Phase 1's acceptance (/"EXACTLY ONE failure and it is the repro/") is satisfied, so the collision is invisible for two phases, and Phase 3's only guidance is the one-line /"Fix up `lookahead.py` if the interior rule flags it, replacing any bare literal widths with the named constants from Phase 1/" — which names constants that do not cover this case. The same trap applies to `teams.py:522`'s `data[position : position + 1]` migrating to a `peek_bytes` width and to `players.py:589`'s `+ 1`.",
    "proposed_fix": "Extend Phase 1's declared surface to the field widths the interior rule will demand, and say so in the step that copies the date decode: add `_DAY_WIDTH = 1` and `_MONTH_WIDTH = 1` (or a single `_U8_FIELD`) alongside `U8_WIDTH`/`U32_WIDTH`/`DATE_WIDTH`, and write `peek_date_fields` as `data[position]`, `data[position + _DAY_WIDTH]`, `data[position + _DAY_WIDTH + _MONTH_WIDTH : position + DATE_WIDTH]`. Add to Phase 1's acceptance: 'no bare nonzero int literal appears in any subscript index in `lookahead.py`' — a checkable statement the implementer can verify at the Phase 1 gate rather than discovering at Phase 3.",
    "reviewer": "executability"
  },
  {
    "id": "EX-03",
    "title": "Phase 6's rule never states what happens to a position argument that is a local, and the phase's acceptance is green or red depending on that unstated default",
    "severity": "major",
    "confidence": "high",
    "category": "underspecified-rule",
    "location": "plan Phase 6, steps 1-3; call sites at src/ootp_ai/parser/world.py:752, :734, :865 and src/ootp_ai/parser/players.py:549",
    "problem": "Phase 6 says: collect module-level constants; a Name addend is legal iff it ends `_WIDTH` / begins `_GAP_` or derives recursively from such; /"A Name whose module-level definition bottoms out in a bare nonzero int literal that is not itself a declared span is an OFFSET, and is flagged./" It never says what happens to a Name that has NO module-level definition — i.e. a local. That is not an edge case, it is the majority of the checked call set after Phase 2: `peek_u32(data, length_at)` (world.py:752), `peek_u32(data, offset)` (world.py:734), `peek_u32(data, position)` (world.py:865, teams.py:587, teams.py:509), `peek_u32(data, position)` (players.py:549), `peek_u32(data, cursor)` (teams.py:559, :571). If the implementer defaults an unresolvable Name to 'flag' — a defensible reading of a guard whose whole ethos is refuse-rather-than-cope — Phase 6's own acceptance criterion (/"test_no_parser_module_seeks_to_a_fixed_offset green over the real tree — zero false positives/") goes red on eight-plus legitimate sites, and the implementer is in exactly the loosen-the-rule position the plan spent Phase 1-2 avoiding. If they default to 'skip', the phase works. The plan documents the CONSEQUENCE of skipping (the local-hoist residual) in a later step, but never states the rule that produces it.",
    "proposed_fix": "Add an explicit step to Phase 6: 'A Name in the position argument that is not defined at module level is SKIPPED, not flagged — it is a walk-computed local, which is the legal case. Only a Name resolvable to a module-level definition is judged, and only then by the declared-span test. A bare int literal in the argument is always flagged regardless of scope.' Then add a fourth fixture — `LOCAL_POSITION_INNOCENT`, world.py:752's exact shape (`length_at` computed in the function body) — asserting it is NOT flagged, so the default has its own witness alongside FOLDED_OFFENDER / WIDTH_SUM_INNOCENT / DERIVED_INNOCENT.",
    "reviewer": "executability"
  },
  {
    "id": "EX-04",
    "title": "Phase 2 is declared the one delegable phase, but its own steps edit tests/test_save_header.py, which is in the subagent's deny set",
    "severity": "major",
    "confidence": "high",
    "category": "internal-contradiction",
    "location": "plan Phase 2 (header.py step) and plan Decisions (/"only Phase 2's `src/` rewiring may be delegated/"); enforced at tests/test_agent_contract.py:76-81",
    "problem": "The plan's commit note for Phase 2 says /"This is the only phase eligible for delegation to the write-capable subagent/", and the Decisions section says /"Phases 1 and 5 also add tests, so their src and test halves would have to be split. Only Phase 2 is cleanly delegable./" But Phase 2's own header.py step says: /"`looks_like_save_file` has NO direct unit test today … add one to tests/test_save_header.py covering the OOTP prefix, a wrong magic, a magic at offset zero, and a buffer shorter than the prefix/", and files_to_touch assigns `tests/test_save_header.py` to Phase 2. I verified the premise (grep for `looks_like_save_file` in `tests/test_save_header.py` returns nothing; its only caller is `src/ootp_ai/saves.py:119`) — the test genuinely needs adding. But `tests/` is asserted into the data-engineer's write deny set by `test_deny_set_still_protects_the_guards` (tests/test_agent_contract.py:76-81, rationale at :77 'An agent that can edit the tests that catch it is the core failure mode'). So Phase 2 is exactly as un-delegable as Phases 1 and 5, by the plan's own reasoning. A cold agent that delegates Phase 2 on the plan's word will get a subagent that silently drops the header test or violates its allowlist.",
    "proposed_fix": "Either (a) strike the delegation claim and mark Phase 2 main-thread like the rest, or (b) split Phase 2 explicitly: '2a — src/ rewiring, delegable to the data-engineer subagent with the gamedata baseline in the handoff; 2b — main-thread, add the `looks_like_save_file` unit test to tests/test_save_header.py.' Whichever is chosen, make the Phase 2 commit note say which half the subagent may touch, and repeat the read-only-git constraint (never checkout/reset/restore/clean/stash) since Phase 2 is the phase most likely to want a revert.",
    "reviewer": "executability"
  },
  {
    "id": "EX-05",
    "title": "Phase 2's acceptance grep is falsified by a docstring line the plan itself preserves, and contradicts its own sweep step",
    "severity": "major",
    "confidence": "high",
    "category": "unverifiable-acceptance",
    "location": "plan Phase 2 acceptance (/"`grep -rn 'data/[' src/ootp_ai/` returns hits only in `parser/lookahead.py`/"); counterexamples at src/ootp_ai/parser/header.py:13 and src/ootp_ai/parser/primitives.py:140",
    "problem": "I ran the enumeration. `data[` under `src/ootp_ai/` matches 23 lines, and two of them survive Phase 2 by design: `src/ootp_ai/parser/header.py:13` — `* a reader comparing `data[0:4]` against `b/"OOTP/"` sees `/x00OOT` and rejects every` — which is prose inside the module docstring that Phase 7 explicitly keeps (it is the trap the module documents), and `src/ootp_ai/parser/primitives.py:140` — `return self._data[start : start + count]`, which the plan states repeatedly must stay exactly as it is. So the stated criterion cannot be met and the implementer cannot tell a real miss from a designed survivor. Worse, the plan contradicts itself two bullets earlier: the Phase 2 sweep step says 'The only surviving buffer-subscript hits must be inside `parser/lookahead.py` and `primitives.py:140`' — which is right about primitives and still wrong about header.py:13. A text grep is also the wrong instrument here on the guard's own reasoning (tests/test_no_fixed_offsets.py:7-10: 'AST, not regex, deliberately: a regex over source text trips on the word `seek` inside a docstring or a comment').",
    "proposed_fix": "Replace the grep criterion with the mechanism the change exists to build: at the Phase 2 gate, run a throwaway script under `var/` (gitignored, never committed) that implements the Phase 3 predicate — `ast.Subscript` whose value is a `bytes`-annotated parameter Name and whose index carries a BinOp or nonzero literal — over `src/ootp_ai/` and assert zero hits outside `lookahead.py` and `primitives.py`. Keep a grep only as a secondary sanity check, written to exclude the two designed survivors by name: `grep -rn /"data/[/" src/ootp_ai/ | grep -v /"parser/lookahead.py/" | grep -v /"parser/primitives.py:140/" | grep -v /"parser/header.py:13/"`.",
    "reviewer": "executability"
  },
  {
    "id": "EX-06",
    "title": "The Phase 3 subscript rule is evaded by a two-line local hoist that is idiomatic in this parser, and the plan documents that residual only for Phase 6",
    "severity": "major",
    "confidence": "high",
    "category": "coverage-gap",
    "location": "plan Phase 3 (rule + docstring steps) and plan Testing (/"WHAT IS DELIBERATELY NOT TESTED/"); real shape at src/ootp_ai/parser/world.py:738-740",
    "problem": "The rule flags a subscript whose index 'contains an `ast.BinOp` or a nonzero int literal'. Hoisting the arithmetic one line up defeats it entirely: `at = record_start + 58` then `return data[at : at + 4]` — the slice's bounds are then a lone Name and a Name+Name BinOp with no literal; the first bound is not flagged and the rule would have to rely on `at + 4`'s literal, which a second hoist (`end = at + 4`) removes. This is not a contrived shape. It is exactly what `world.py:738-740` already does — `pad_at = offset + _EVENT_HEAD_WIDTH`, `length_at = pad_at + _EVENT_PAD_WIDTH`, `if data[pad_at:length_at] != ...` — and I confirmed by walking the rule over all 21 sites that world.py:740, world.py:744, players.py:424, players.py:529, players.py:574 and players.py:588 are all lone-Name indices the rule does not fire on today. The plan's residual list names only two holes: the rename hole and 'Phase 6's local-variable hole — `at = position + 58; peek_u32(data, at)`', attributing the local hole to the CALL rule alone. The subscript rule has the identical hole and the plan's Phase 3 docstring step never says so — which reproduces, at a smaller altitude, precisely the overclaiming this bugfix exists to end. A related unstated gap: the rule keys on `ast.Name` values only, so `self._buf[start + 58]` (an `ast.Attribute`, the shape `primitives.py:140` already uses) is never flagged anywhere, allowlisted or not.",
    "proposed_fix": "Add the local hoist and the attribute-value shape to Phase 3's docstring step as named residuals, in the same plain terms the plan uses for Phase 6's. Then pin both in Phase 4 as explicit KNOWN-RESIDUAL controls — a fixture doing `at = start + 58; return data[at : at + 4]` asserted NOT flagged with a comment saying it is a documented hole and why (closing it needs dataflow analysis inside a test module), and the same for `self._buf[start + 58]`. Pinning the hole is what stops the next reader assuming there isn't one, and matches the treatment the plan already gives the alias case.",
    "reviewer": "executability"
  },
  {
    "id": "EX-07",
    "title": "The gamedata gates — the plan's only oracle — pass vacuously when the saves are unavailable",
    "severity": "major",
    "confidence": "medium",
    "category": "environment-assumption",
    "location": "plan Phase 1 (baseline + stop condition) and every phase's `uv run pytest -m gamedata … -q` acceptance; marker at pyproject.toml:101-107",
    "problem": "The plan's whole behaviour-preservation argument rests on gamedata runs, correctly, because `.github/workflows/ci.yml:57` runs `-m /"not gamedata/"`. But every gamedata acceptance is phrased as a green/pass condition — e.g. Phase 1: '`uv run pytest -m gamedata tests/test_read_only.py -q` green — zero mtime and zero digest differences'; Phase 2: '`uv run pytest -m gamedata -q` green'. On a machine with no OOTP install the gamedata tests skip (they are marker-selected and their fixtures resolve settings from `.env`), pytest exits 0, and 'green' is satisfied without a single byte of the save being read. The plan's stop-condition — 'IF THE GAMEDATA SUITE CANNOT RUN … STOP HERE' — therefore depends entirely on the implementer noticing skips in `-q` output, which is the least visible thing pytest prints. A cold agent that gets `0 failed` and moves on will ship the two riskiest phases with no oracle at all, which is the single outcome the plan names as unacceptable.",
    "proposed_fix": "Make every gamedata criterion count-based rather than exit-code-based. In Phase 1, record the PASSED COUNT of `uv run pytest -m gamedata -q` (not just the pass/fail split) in the baseline and the commit body, and add: 'if that count is 0, or the run reports skips instead of passes, the saves are not available on this machine — STOP and hand back to the operator.' In Phases 2 and 5, phrase acceptance as 'the gamedata run reports the SAME passed count as the Phase 1 baseline, and zero skips' rather than 'green'. Run those gates without `-q` (or with `-rs`) so skips are visible.",
    "reviewer": "executability"
  },
  {
    "id": "EX-08",
    "title": "Re-running the 2m35s / 6.4 GB read-only test at every phase gate costs ~18 minutes for four phases that cannot possibly regress it",
    "severity": "minor",
    "confidence": "high",
    "category": "gate-cost",
    "location": "plan Testing (/"Every phase: `uv run pytest -m gamedata tests/test_read_only.py` — ADR 0001, re-checked at every gate rather than once/"); cost recorded at tests/test_read_only.py docstring (/"**2m35s** for the pair, over 30,703 files and ~6.4 GB hashed three times/")",
    "problem": "The plan makes ADR 0001's read-only check a criterion on all seven phases. The test's own docstring records the price: 2m35s, 30,703 files, ~6.4 GB hashed three times per run, and it ingests both the disposable probe and the managed league to do it. Phases 3, 4, 6 and 7 touch only `tests/`, `CLAUDE.md`, `.claude/agents/`, `docs/` and prose — no code path in any of them opens a file, and the plan itself says so ('Not because this phase touches the parser — it does not'). That is roughly 10 wasted minutes and, more importantly, four gates whose most expensive criterion carries no information. A gate that is expensive and known-uninformative is the gate an implementer starts skipping, and once skipped the Phase 2 and Phase 5 runs — where it genuinely matters, because those phases rewrite the code that opens saves — go with it.",
    "proposed_fix": "Scope the read-only check to the phases that can move it: Phase 2, Phase 5, and once more at the branch tip in Phase 7's full-bar run. For Phases 1, 3, 4 and 6 replace it with a cheap statement of why it cannot regress ('this phase adds no code path that opens a file'), so the reasoning is recorded rather than the run repeated.",
    "reviewer": "executability"
  },
  {
    "id": "EX-09",
    "title": "Phase 2 has no mechanical completeness check, and Phase 3's /"the RULE is wrong, not the site/" instruction misdirects when Phase 3 fires on a site Phase 2 simply missed",
    "severity": "minor",
    "confidence": "medium",
    "category": "sequencing",
    "location": "plan Phase 2 acceptance vs plan Phase 3 acceptance (/"If it fires on a benign site the RULE is wrong, not the site; do not add an exemption to make it pass/")",
    "problem": "Phase 2's completeness is verified only by greps (see EX-05) and by the existing suite passing — neither of which detects a migration site left behind, because a surviving `data[position + 4 : ...]` still works perfectly. The mechanical proof of Phase 2 lives in Phase 3's acceptance ('test_no_parser_module_seeks_to_a_fixed_offset green over the whole real tree, with ZERO false positives — which is the proof Phase 2 actually finished'). But that same criterion is immediately followed by 'If it fires on a benign site the RULE is wrong, not the site.' Those two sentences give opposite instructions for the same observation. A cold agent that sees the scan fire on, say, a `_scan_string` payload slice it forgot to migrate has been told by the plan that the rule is wrong — and the natural next move is to weaken the rule, which is the exact failure the guard's docstring warns about at tests/test_no_fixed_offsets.py:9-10.",
    "proposed_fix": "Make the triage explicit in Phase 3's acceptance: 'If the scan fires, first check whether the site is one of the six cry-wolf shapes enumerated in Phase 4 (players.py:383, human_managers.py:154, teams.py:624, world.py:844, primitives.py:140, snapshot.py:227). If it is NOT one of those, Phase 2 was incomplete — go back and migrate the site. Only if it IS one of those is the rule wrong. Under no circumstances add an exemption.' And give Phase 2 the prospective-rule scratch check from EX-05 so the incompleteness is caught at its own gate.",
    "reviewer": "executability"
  },
  {
    "id": "EX-10",
    "title": "Phase 7's sweep rule exempts everything under requests/ as history, leaving the /"zero exemptions/" claim live in an ACTIVE feature plan",
    "severity": "minor",
    "confidence": "high",
    "category": "docs-scope",
    "location": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1083 (and plan Phase 7, /"Do NOT rewrite the now-dated 'zero exemptions' phrase inside landed `requests/` artifacts/")",
    "problem": "I grepped the tree for `zero exemptions`. Live hits outside the bugfix's own artifacts: `src/ootp_ai/parser/primitives.py:12` and `src/ootp_ai/parser/header.py:6` (both correctly scheduled for Phase 7), `.claude/agents/data-engineer-memory.md:241` (correctly left as ledger history), and `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1083` — 'no `seek`) *and* mechanically (an AST scan over the whole parser tree, zero exemptions)'. That last one is not history: `first-sight` is the repo's live feature track (CLAUDE.md names Bronze landing as its Phase 8, still ahead, and the session started on branch `first-sight-phase-6-players-and-rosters`), so it is a plan a cold agent will read and act on. Phase 7's acceptance — 'every hit must be either corrected or inside a `requests/` artifact recording history' — classifies it as history and leaves it standing, which is the same category of false live claim the phase exists to eliminate.",
    "proposed_fix": "Split Phase 7's sweep rule by whether the artifact is still executable rather than by directory: a `requests/` artifact for a track marked `fixed`/`done` is history and is left alone; a plan for a track still in flight is a live instruction and gets the same one-line correction as primitives.py. Name `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1083` explicitly in the Phase 7 steps so the judgment is made once, in the plan, rather than re-litigated at the gate.",
    "reviewer": "executability"
  },
  {
    "id": "EX-11",
    "title": "Phases 1 and 2 end at a /commit gate with the suite red, and /commit pushes the branch — the plan never says to hold the PR",
    "severity": "minor",
    "confidence": "high",
    "category": "process",
    "location": "plan Phase 1 and Phase 2 commit notes; .github/workflows/ci.yml:3-6 (`on: pull_request`)",
    "problem": "The plan is honest that `uv run pytest` is not fully green at the end of Phases 1 and 2 ('exactly one failure, and it is the repro'), and that is the right call — xfailing the repro would hide the acceptance contract. But the `/commit` skill 'commits and pushes the feature branch' and CI triggers on `pull_request`. If a PR is already open on `fix-fixed-offset-guard-subscripts`, Phases 1 and 2 each push a commit whose CI run is red on `uv run pytest -m /"not gamedata/"` (the repro is offline, so CI sees it), for reasons that look identical to a broken build. Nothing in the plan tells the implementer to hold the PR until Phase 3, and the plan's own convention list correctly notes the PR stays the operator's — which makes it exactly the kind of thing an implementer might do 'helpfully' at Phase 1.",
    "proposed_fix": "Add one line to Phase 1's commit note and repeat it in Phase 2: 'Do NOT open the PR yet. The committed repro is offline and stays red until Phase 3, so CI would report red for two commits for a reason that is by design. The PR is the operator's and should be opened at the earliest after Phase 3, when `uv run pytest -q` is fully green.'",
    "reviewer": "executability"
  },
  {
    "id": "EX-12",
    "title": "Decision D1's rationale cites specific lines the proposed rule would not actually flag",
    "severity": "nit",
    "confidence": "high",
    "category": "citation-accuracy",
    "location": "plan Decisions D1 (/"goes red on roughly ten legitimate lines … players.py:588-590, teams.py:590, world.py:744-746/759/868, human_managers.py:248, header.py:114/")",
    "problem": "The MIGRATE-FIRST ordering is right and is the plan's most valuable decision — I walked the proposed rule over all 21 direct-index sites and 13 of them do fire, so the ordering is genuinely load-bearing. But three of the specific lines cited as evidence do not fire under the rule the plan itself proposes: `players.py:588` is `day = data[position]` (a lone Name — no BinOp, no literal), `world.py:744` is `day = data[date_at]` (same), and `world.py:740` (cited elsewhere in the plan) is `data[pad_at:length_at]` (two lone Names). `header.py:114` fires only on its second subscript — `data[0]` is a zero literal, excluded by `_nonzero_literal`'s `node.value != 0` test at tests/test_no_fixed_offsets.py:39. A cold implementer who verifies the rationale before trusting the ordering will find it does not hold as stated, which corrodes trust in the citations that DO hold — and this plan's value is almost entirely in its citations.",
    "proposed_fix": "Restate D1's evidence as the lines that actually fire: players.py:581, :589, :590; teams.py:522, :590, :605; world.py:745, :746, :759, :868, :883; human_managers.py:204, :244, :248; header.py:114 (second subscript only). Thirteen sites across five modules is a stronger argument than 'roughly ten' and has the advantage of being checkable.",
    "reviewer": "executability"
  },
  {
    "id": "EX-13",
    "title": "Phase 5's mutation check overstates that the offline pin is the first failure, and Phase 7 cites six survey rows where there are five",
    "severity": "nit",
    "confidence": "high",
    "category": "precision",
    "location": "plan Phase 5 acceptance (/"confirm the new OFFLINE pin test goes red BEFORE any gamedata test does/") and plan Phase 7 (/"the six shapes in BUGFIX_REQUEST.md:100-106/")",
    "problem": "Two small precision issues that cost an implementer a moment of doubt at a gate. (a) Phase 5's mutation — 'make `_PLAYER_ID_WIDTH` 5' — propagates through both derived constants (`_BIRTH_DATE_LOOKAHEAD` 13, `_AGE_LOOKAHEAD` 20), so `_looks_like_record` stops framing synthetic records and a large slice of the OFFLINE `tests/test_parse_players.py` suite goes red alongside the pin, not after it. The pin is not 'the first line of defence' in the sense of being the only or earliest failure; the true claim is the weaker and still-sufficient 'the pin fails offline, so the mis-derivation is caught without a gamedata run'. (b) BUGFIX_REQUEST.md:100-106 is a table with a header row, a separator row and FIVE data rows (players/world date decode, teams/world length prefix, human_managers, world.py:743, players.py:445-449) — the plan's docstring test says six.",
    "proposed_fix": "(a) Rephrase Phase 5's criterion as 'the new offline pin goes red, so the mis-derivation is caught by CI-visible tests and needs no gamedata run to detect — other offline players tests will go red with it, which is expected.' (b) Change 'the six shapes' to 'the five shapes'.",
    "reviewer": "executability"
  },
  {
    "id": "EX-14",
    "title": "Phase 4's probe writes a Python module into the scanned package without the precedent's collision guard or a serial-run constraint",
    "severity": "nit",
    "confidence": "medium",
    "category": "test-hygiene",
    "location": "plan Phase 4 (planted-offender step); precedent at tests/test_leak_guard_scope.py:47-53",
    "problem": "Phase 4 plants `src/ootp_ai/parser/_guard_probe.py` — a real module inside the very tree the guard rglobs — and relies on `unlink(missing_ok=True)` in `finally`. The precedent it copies does slightly more: `untracked_file` at tests/test_leak_guard_scope.py:48 asserts `not path.exists()` BEFORE writing, 'refusing to clobber it', and the plan's step never mentions that assertion. Separately, while the probe exists, `test_no_parser_module_seeks_to_a_fixed_offset` would see it if the two ran concurrently; serially they cannot overlap, but the plan does not say the gate must be a serial run, and any future `-n auto` would turn this into an intermittent failure in the guard the whole change exists to protect. The plan's own risk list flags the stray-file hazard but not the clobber guard or the concurrency assumption.",
    "proposed_fix": "Add to Phase 4's step: assert the probe path does not already exist before writing (mirroring tests/test_leak_guard_scope.py:48), and add a comment in the new module stating that this gate must be run serially — the probe is visible to `parser_module_violations()` for the life of the context manager, so a parallel runner would make the real whole-tree test flaky. Keep the `git status --porcelain` check at the phase gate as the plan already prescribes.",
    "reviewer": "executability"
  }
]
```


## Meta-audit findings

```json
[
  {
    "id": "MERGE-01",
    "title": "Phase 6 is invented beyond the RCA's tiers, gated, then recommended for shipping",
    "severity": "major",
    "confidence": "high",
    "category": "scope-creep",
    "location": "merged plan phases[5] 'Phase 6 — Fold module constants' + gated_decisions[1] (G2); measured against requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md:113-147",
    "problem": "The RCA names exactly three tiers: Minimal (:115-122, forbidden alone), Root (:124-139, the lookahead seam + module-scoped rule), and Hardening (:141-147, explicitly scoped to `_BIRTH_DATE_LOOKAHEAD`/`_AGE_LOOKAHEAD` and explicitly 'gated not assumed'). Merged Phase 5 discharges Hardening. Phase 6 — a module-level constant table, a recursive declared-span legality rule, import-resolved call-set detection, three fixtures and a convention-is-stated test — appears nowhere in the RCA. The merge does gate it (G2), but G2's recommendation is 'SHIP IT', and the phase is presented as numbered Phase 6 of 7 with Phase 7's docstring pass depending on its final rule set and Phase 6's own acceptance re-verifying Phase 4's meta-guard. That is the exact pattern of a gated item promoted into the default plan: an operator who never disposes G2 gets the work by inertia.",
    "proposed_fix": "Keep G2 but flip its default: state that Phase 6 is NOT executed unless the operator disposes G2 affirmatively at the Phase 5 gate, and renumber it as an appendix phase after Phase 7 (or mark it 'Phase 6 (optional)'). Pre-write both Phase 7 docstring variants — with and without the fold — so dropping it costs no rework. Also add one line to the summary distinguishing what the RCA decided (Root + Hardening) from what this plan adds on top (Phase 4 and Phase 6).",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-02",
    "title": "Phase 2 acceptance grep is unsatisfiable — primitives.py:140 matches `data[`",
    "severity": "major",
    "confidence": "high",
    "category": "internal-contradiction",
    "location": "merged plan phases[1] Phase 2 acceptance criterion 4 vs Phase 2 step 8 ('Sweep'); real line src/ootp_ai/parser/primitives.py:140",
    "problem": "Phase 2's step 8 says the only surviving buffer-subscript hits must be inside `parser/lookahead.py` AND `primitives.py:140`. Phase 2's acceptance criterion then says `grep -rn 'data/[' src/ootp_ai/` must return hits only in `parser/lookahead.py`. Verified: primitives.py:140 is `return self._data[start : start + count]`, and the pattern `data/[` matches inside `_data[`. The acceptance criterion is therefore unsatisfiable without editing `Cursor` — which every other part of the plan forbids ('Cursor is untouched by this entire plan', files_to_touch primitives.py; Decision D4; conventions). A cold implementer treats acceptance criteria literally and is either blocked or does the forbidden edit.",
    "proposed_fix": "Rewrite the criterion as: `grep -rn 'data/['` src/ootp_ai/ returns hits only in `parser/lookahead.py` and the single known line `parser/primitives.py:140` (`self._data[...]`, an Attribute inside the allowlisted cursor). Or specify the anchored pattern `(^|[^_])data/[` and state that primitives.py:140 is deliberately excluded by the underscore.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-03",
    "title": "Phase 6's declared-span rule is stated two incompatible ways, and the strict reading fires on a line Phase 2 writes",
    "severity": "major",
    "confidence": "high",
    "category": "internal-contradiction",
    "location": "merged plan architecture_map ('permitting only addends whose names are declared spans') vs phases[5] Phase 6 step 2; lands on src/ootp_ai/parser/human_managers.py:248 as rewritten by phases[1] Phase 2 step 5",
    "problem": "The architecture map states the fold permits ONLY addends whose names are declared spans (`_WIDTH` suffix / `_GAP_` prefix). Phase 6 step 2 states something narrower: a Name is illegal iff its MODULE-LEVEL definition bottoms out in a bare nonzero int that is not a declared span — leaving a Name with no module-level binding unspecified. These disagree, and the disagreement lands on real code the plan itself creates. Verified: human_managers.py:248 currently reads `int.from_bytes(data[offset + 4 * slot : offset + 4 * slot + 4], 'little')` inside a comprehension over `slot in range(1, CLUB_SLOTS)`; Phase 2 step 5 rewrites it as `peek_u32(data, offset + slot * _U32_WIDTH)`. Under the architecture-map reading `slot` is not a declared span and the call is flagged. Phase 6's acceptance demands 'zero false positives' on the real tree, so the implementer's only green paths are to weaken the rule mid-phase (the exact failure the guard's docstring warns about at tests/test_no_fixed_offsets.py:9-10) or to add an exemption that Decision D4 forbids.",
    "proposed_fix": "Settle it in Phase 6 step 2 and mirror the wording into the architecture map: a Name with no module-level binding is a runtime value, not a constant, and is IGNORED by the fold (only module-level bare-int constants are resolved). Then add `human_managers._is_club_landmark`'s post-Phase-2 shape — `peek_u32(data, offset + slot * _U32_WIDTH)` with `slot` a comprehension variable — as a fourth named Phase 6 fixture (`SLOT_ARITHMETIC_INNOCENT`), alongside FOLDED_OFFENDER / WIDTH_SUM_INNOCENT / DERIVED_INNOCENT.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-04",
    "title": "The plan never states that its own D4 makes the acceptance contract unreachable without local OOTP saves",
    "severity": "major",
    "confidence": "high",
    "category": "cost-unrealism",
    "location": "merged plan decisions[3] (D4, no per-site exemption registry) + decisions[0] (migrate first, widen second) + phases[0] Phase 1 step 2 (stop condition)",
    "problem": "The merge chose a two-module path allowlist and explicitly refused the per-site exemption registry that planner 2 proposed (EXEMPT_SITES). Combined with D1 (migrate before widening, because the whole-tree scan at tests/test_no_fixed_offsets.py:143 goes red on ~ten legitimate lines otherwise), this makes Phase 3 hard-dependent on Phase 2, and Phase 2's acceptance requires a local gamedata run that CI structurally cannot do (verified .github/workflows/ci.yml:57 runs `-m /"not gamedata/"`). Consequence, never stated anywhere in the plan: on a machine without a local OOTP install, the bugfix track's contract at requests/bugfix-requests/README.md:24-26 — 'the red reproduction goes green' — cannot be reached at all. Phase 1 step 2 tells the implementer to stop and hand back, but only after step 1 has ordered a baseline capture that may be impossible, and it frames the stop as being about Phases 2 and 5 rather than about the whole fix. Planner 2's registry was the only design any planner offered that would have decoupled the guard fix from the refactor, and the merge dropped it without noting this cost.",
    "proposed_fix": "Move the gamedata-availability check to Phase 0, before the baseline capture, and state the consequence plainly: with no local saves, no phase of this plan is completable and the red repro stays red — hand back immediately. Then add a gated decision recording the fallback the merge rejected: a narrow, written, per-site exemption registry (planner 2's EXEMPT_SITES, with `test_the_exemption_registry_is_small`) would let Phase 3 land ahead of the migration on an offline machine, at the cost of the precedent D4 exists to prevent. Let the operator choose rather than discovering the dead end at Phase 1.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-05",
    "title": "Planner 2's entire census phase was dropped with no recorded rationale",
    "severity": "major",
    "confidence": "high",
    "category": "dropped-signal",
    "location": "merged plan phases[] (no census phase; merge starts at the lookahead seam) — dropped from proposals[1] 'Phase 1 — Census: pin what actually indexes a save buffer' and its open_questions OQ4",
    "problem": "Planner 2 proposed a first phase that adds a `BufferIndexVisitor`, pins the `(module, function)` inventory as a literal frozenset with `test_the_buffer_index_inventory_is_the_known_set`, reconciles the count against the RCA's own table (ROOT_CAUSE_ANALYSIS.md:55-64, which counts reads-per-module while a subscript census counts sites — they differ by construction), and flagged in OQ4 that this pin imposes real friction on unrelated future work (first-sight Phase 6b works in exactly this region). The merge carries none of it — not the phase, not the diagnosis-vs-guard reconciliation, not the OQ. Meanwhile the merged plan's central architectural bet ('the surface is SMALL... 21 direct-buffer index sites, measured by grep on 2026-08-18') rests on a hand grep that nothing in the plan pins or re-derives. Some of the census is genuinely subsumed by Phase 3 (after widening, a new indexing site IS a violation) and planner 2's stated motivation — surviving a rename of the buffer variable — is closed by the merge's annotation-keyed rule. But none of that reasoning is written down, so a reader cannot tell whether the drop was considered or accidental.",
    "proposed_fix": "Add a short decision entry: 'The census is deliberately not carried. After Phase 3 a new buffer-indexing site is a guard violation rather than an inventory drift, so the pin would duplicate the guard; and it would fire on legitimate first-sight Phase 6b work (planner 2 OQ4). The 21-site figure is measured 2026-08-18 and is a starting inventory, not an invariant.' If the operator wants the reconciliation, add it as a one-off note in IMPLEMENTATION_REPORT.md rather than a standing test.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-06",
    "title": "Phase 2 is called 'behaviour-preserving by construction' while prescribing three deliberate behaviour widenings",
    "severity": "major",
    "confidence": "high",
    "category": "cost-unrealism",
    "location": "merged plan phases[1] Phase 2 goal ('Behaviour-preserving by construction') vs its own steps 5 and 6 and risks[7]",
    "problem": "The goal line and the acceptance ('if a parser test had to change, the refactor was not behaviour-preserving — revert') assert construction-level safety, but three prescribed changes are real behaviour changes the plan elsewhere admits: (a) the unified negative-position guard — verified players.py:579 rejects `position < 0` while teams.py:603 and world.py:881 do not, so callers of the teams/world variants change semantics from Python's from-the-end indexing to `None`; (b) `_is_club_landmark`'s new `None` branches, which the plan itself calls a change in branch structure feeding the exactly-one-match refusal at human_managers.py:231-238; (c) `looks_like_save_file` rewritten to `startswith`. Each is defensible, but stacking all three inside the single largest and highest-silent-failure phase, under a goal that says nothing can change, gives a cold implementer no way to tell a real regression from a sanctioned widening.",
    "proposed_fix": "Restate the goal as 'behaviour-preserving on every input any current caller produces, with exactly three deliberate widenings, each named and individually argued in the commit body'. List the three under a 'Deliberate widenings' heading in the phase, and add an acceptance line requiring each to be recorded with the reason no current caller can reach the changed branch. Keep 'no existing parser test may be edited' as-is — it is the right stop signal.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-07",
    "title": "Phase 4 (the meta-guard) is un-gated novel work, inverting the plan's own gating logic",
    "severity": "minor",
    "confidence": "high",
    "category": "scope-creep",
    "location": "merged plan phases[3] 'Phase 4 — Guard the guard'; contrast gated_decisions[1] (G2 gates Phase 6)",
    "problem": "Phase 4 adds a whole new test module with eight distinct sub-tests (planted disk probe, coverage floor, allowlist integrity, allowlist-not-exempt-from-everything, filename-vs-content discrimination, alias evasion, six cry-wolf controls) plus two hand mutation checks. The RCA never names it; its acceptance contract asks for 'a regression test', singular (requests/bugfix-requests/README.md:24-26). It is well justified by repo precedent (tests/test_leak_guard_scope.py, verified at 253 lines with the untracked_file contextmanager at :40-53) and by the batching-guard history recorded at .github/workflows/ci.yml:66-69. But the merge gated the RCA-adjacent invention (Phase 6) and left the wholly-novel one un-gated, which is backwards: Phase 4 is the larger discretionary surface.",
    "proposed_fix": "Either (a) add a gated decision for Phase 4's scope, splitting it into a core the plan ships unconditionally (planted probe + allowlist integrity + three cry-wolf controls lifted from players.py:383, teams.py:624, world.py:844) and a discretionary half (coverage floor, discrimination test, alias-evasion test) the operator can cut; or (b) state explicitly in Phase 4's goal why it is not gated — that a scan guard this repo has already been bitten by twice is not optional here — so the asymmetry with G2 reads as a decision rather than an oversight.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-08",
    "title": "Phase 6 is called 'cheap' when the merge itself sizes it as a full phase",
    "severity": "minor",
    "confidence": "high",
    "category": "cost-unrealism",
    "location": "merged plan gated_decisions[1] (G2: 'it is cheap: a module-level constant table, a recursive legality test, three fixtures')",
    "problem": "G2's cost estimate omits most of what Phase 6's own steps require: resolving the checked call set from `ast.ImportFrom` with `asname` handling; a recursive fold over derived module constants with a stated termination argument; the `_WIDTH`/`_GAP_` convention plus `test_the_declared_span_convention_is_stated` asserting it against the guard's own docstring; three fixtures; a written residual; and an acceptance mutation that reverts Phase 5 in the working tree and restores it. Only one of the three planners proposed this at all, and that planner sized it as a full numbered phase, not a cheap addendum. Calling it cheap in the gate blurb biases the operator's disposition of a decision the merge otherwise handles carefully.",
    "proposed_fix": "Replace 'it is cheap' in G2 with the honest sizing: 'it is one full phase — roughly the work of Phase 3 again, in a test module — and it is the one phase that can be dropped without leaving a false claim behind.' Leave the recommendation (ship / cut) to the operator on that basis.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-09",
    "title": "'Copy bodies from their current homes rather than rewriting them' is false for three of the eight helpers",
    "severity": "minor",
    "confidence": "high",
    "category": "cost-unrealism",
    "location": "merged plan phases[0] Phase 1 step 6; measured against src/ootp_ai/parser/teams.py:581-593, world.py:759 and world.py:859-871",
    "problem": "The step reduces Phase 1's risk by promising verbatim transplants, and names sources for five helpers. Two of those sources do not exist in the promised shape. Verified: there is no `is_printable_ascii(data, position, width)` anywhere — teams.py:591 and world.py:759 both iterate an already-materialised slice (`any(byte < 0x20 or byte > 0x7E for byte in payload)`), so the shared helper is a re-shaping, not a copy. `peek_length_prefixed(data, position, limit)` likewise re-shapes teams.py:587-589's length-plus-bounds half and must introduce a named length-prefix width that neither source has. `is_zero_run` and `zero_run_width` have no verbatim source either (world.py:740 compares against `b'/x00' * _EVENT_PAD_WIDTH`; human_managers.py:204 is a three-condition while loop). Only `peek_u8` (players.py:572-574), `peek_u32` (players.py:577-581) and the raw date decode (world.py:744-746) are true copies.",
    "proposed_fix": "Split the step into two lists: COPY VERBATIM (`peek_u8`, `peek_u32`, `peek_date_fields`) and RE-SHAPE, naming the source line and what changes (`peek_bytes`, `peek_length_prefixed` ← teams.py:587-589, `is_printable_ascii` ← teams.py:591 / world.py:759, `is_zero_run` ← world.py:740, `zero_run_width` ← human_managers.py:204). Require a passing unit test in tests/test_lookahead.py for every re-shaped helper before any caller moves onto it in Phase 2.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-10",
    "title": "A planner-vs-planner disagreement about editing docs/data-access.md was resolved silently",
    "severity": "minor",
    "confidence": "high",
    "category": "dropped-signal",
    "location": "merged plan phases[6] Phase 7 step 5 + files_to_touch['docs/data-access.md']; dropped from proposals[1] Phase 6 step 5 ('docs/data-access.md — NO EDIT')",
    "problem": "Planner 1 wanted a line appended after the blockquote at docs/data-access.md:228-230 naming where enforcement lives. Planner 2 argued affirmatively for NO EDIT, on the grounds that the file's per-claim epistemic labels are load-bearing and an unnecessary edit costs their credibility — 'do not invent a change here to look thorough'. The merge adopted planner 1 without recording that the other view existed or why it lost. Verified the underlying facts both planners cite: :228-230 is a `verified`-labelled claim about the FORMAT, and this bugfix changes none of its evidence — which is exactly planner 2's point. This is a doc the project treats as rule-bearing (CLAUDE.md: 'its epistemic labels are load-bearing'), so a silent resolution is the wrong shape.",
    "proposed_fix": "Add a decision entry recording both positions and the call, or promote it to gated_decisions. If the append stays, add an explicit instruction that the appended sentence is a pointer to enforcement and carries no epistemic label of its own, so it cannot be read as strengthening or qualifying the `verified` claim above it.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-11",
    "title": "`zero_run_width`'s end-of-buffer semantics are unspecified, and a behaviour-preserving rewrite depends on them",
    "severity": "minor",
    "confidence": "high",
    "category": "spec-gap",
    "location": "merged plan phases[0] Phase 1 steps 3-4 and its test list; consumed by phases[1] Phase 2 step 5 against src/ootp_ai/parser/human_managers.py:196-211",
    "problem": "Phase 1 specifies `zero_run_width(data, position, limit) -> int` and its test list covers only 'stopping exactly at its limit'. Phase 2 then rewrites `_pad_width`'s loop onto it and claims the `_MAX_PAD` refusal at :206-210 is preserved. Verified, the current loop has THREE stop conditions: `width < _MAX_PAD`, `position + width < len(data)`, and `data[position + width] == 0`. The refusal keys on `width >= _MAX_PAD`. If `zero_run_width` returns `limit` when it runs off the end of the buffer instead of the count of zeros actually seen, a truncated file that today returns a short width and proceeds would start raising ManagerRecordLayout — a behaviour change inside a phase whose whole claim is that there are none.",
    "proposed_fix": "Specify in Phase 1: `zero_run_width` returns the count of consecutive zero bytes starting at `position`, stopping at `limit` OR the end of the buffer, whichever comes first — it never reports zeros it did not read. Add the end-of-buffer case to tests/test_lookahead.py alongside the limit case, and add a Phase 2 acceptance line that `_pad_width` still returns a short width (not a refusal) on a buffer that ends inside the pad run.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-12",
    "title": "Planner 3's open question on `peek_bytes` error semantics was dropped, not decided",
    "severity": "minor",
    "confidence": "high",
    "category": "dropped-signal",
    "location": "merged plan phases[0] Phase 1 step 3 (prescribes `None`); dropped from proposals[2] open_questions[1]",
    "problem": "Planner 3 raised a real API question: should `peek_bytes` return `None` past the end (consistent with the three existing `_peek_*` families) or RAISE, since every current call site already length-guards first — verified at teams.py:588 (`length is None or length > limit or position + 4 + length > len(data)`) and world.py:866 — so a raising version would surface a truncated file more loudly rather than degrading it to a `None` branch. The merge prescribes `None` in Phase 1 without recording the alternative or the argument for it. Given the plan's own risk that `peek_u32`'s new `None` changes branch structure in `_is_club_landmark`, the question is live rather than academic.",
    "proposed_fix": "Add a short decision entry: `None` is chosen for consistency with the three families being replaced and because Phase 2 must be behaviour-preserving; the raising alternative is recorded and rejected for this change. Add a note that if any Phase 2 call site ends up silently ignoring a `None` return, that is a signal to revisit — mypy strict over src and tests (pyproject.toml:91-95, verified) makes an ignored `None` hard to hide but not impossible.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-13",
    "title": "Planner 2's explicit 'README.md — NO EDIT, confirm by reading' step was dropped, leaving Phase 7 with no verdict on it",
    "severity": "minor",
    "confidence": "medium",
    "category": "dropped-signal",
    "location": "merged plan phases[6] Phase 7 (README.md never mentioned; absent from files_to_touch); dropped from proposals[1] Phase 6 step 6",
    "problem": "Planner 2 explicitly examined README.md's architecture paragraph, concluded it describes parser capabilities rather than enumerating modules, and recorded 'NO EDIT — confirm by reading before deciding' as a step. The merge drops both the conclusion and the check. Phase 7 runs `/update-docs`, whose job includes checking README's status and architecture against reality, and the plan adds a new module to the parser package plus a `parser/__init__.py:3` edit changing 'three modules' to four. A cold implementer reaching Phase 7 has no recorded position on whether README needs a matching edit, and will either skip it or make an unnecessary one.",
    "proposed_fix": "Restore the step in Phase 7: read README.md's architecture section, confirm it names capabilities (forward-only cursor, header/version guard, snapshot layer) rather than parser modules, and record 'no edit needed' in the commit body — the same treatment the plan already gives docs/data-access.md's `verified` blockquote.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-14",
    "title": "Phase 6 ships a rule with no demonstrated catch on the real tree, framed as closing a class",
    "severity": "question",
    "confidence": "medium",
    "category": "cost-unrealism",
    "location": "merged plan phases[5] Phase 6 goal and acceptance criterion 3; measured against src/ootp_ai/parser/world.py:738-759 as rewritten by Phase 2",
    "problem": "Phase 6's goal says it closes the class of record-relative constants handed as call arguments, and G2 says without it 'the next author can write `_TEAM_ID_OFFSET = 58; peek_u32(data, position + _TEAM_ID_OFFSET)` and pass'. That is true of the inline-module-constant shape only. Verified: after Phase 2, world's real position arguments are LOCALS — `pad_at`/`length_at` at :738-739, `date_at` at :743, `name_at` at :755 — which the module-level fold never resolves, and the plan's own residual admits `at = position + 58; peek_u32(data, at)` evades it. Meanwhile the only real-tree sites the fold can reach are players.py:553 and :557, which Phase 5 has already made legal. So the phase's sole demonstrated catch is a mutation the implementer introduces themselves (Phase 6 acceptance criterion 3, reverting Phase 5). That may still be worth shipping as prospective coverage, but the framing overstates it — which is the same overclaiming the whole request exists to fix.",
    "proposed_fix": "Reword Phase 6's goal to what it does: 'closes the inline module-constant addend shape (players.py:553's exact form) and nothing wider; after Phase 5 there is no real-tree site it fires on, so its value is prospective.' Keep the residual note but promote it from the guard docstring into the phase goal, and carry the same qualification into Phase 7's docstring wording so no document claims the argument case is fully covered.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-15",
    "title": "Three width constants for four bytes — the seam's own duplication rationale is undercut",
    "severity": "nit",
    "confidence": "high",
    "category": "consistency",
    "location": "merged plan phases[0] Phase 1 step 3 (`U32_WIDTH`, `DATE_WIDTH` in lookahead.py) vs phases[1] Phase 2 step 5 (`_U32_WIDTH` in human_managers.py) vs phases[4] Phase 5 step 4 (`_DATE_WIDTH` in players.py)",
    "problem": "The seam's stated justification is collapsing duplication (three `_peek_u32` bodies, two `_scan_string`, two date decodes). The plan then creates three separately-declared names for the same four bytes: `U32_WIDTH` and `DATE_WIDTH` in lookahead.py, `_U32_WIDTH` in human_managers.py, `_DATE_WIDTH` in players.py — while world.py already has its own `_DATE_WIDTH = 4` at :205 (verified). Neither the choice nor its consequence for Phase 6's leaf rule (a locally re-declared `_WIDTH` name is a legal addend, so nothing breaks) is stated.",
    "proposed_fix": "Either have players.py and human_managers.py import `U32_WIDTH`/`DATE_WIDTH` from lookahead rather than re-declaring, or add one sentence to the architecture map: per-module `_WIDTH` constants are deliberately kept local because they name that module's field, not a primitive's size, and Phase 6's leaf rule accepts either. Pick one and say so; silence here will produce a fourth spelling in the next parser phase.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-16",
    "title": "Phase 7 instructs an edit to header.py:13, which is accurate prose the change does not falsify",
    "severity": "nit",
    "confidence": "high",
    "category": "citation-precision",
    "location": "merged plan phases[6] Phase 7 step 4 and files_to_touch['src/ootp_ai/parser/header.py']; real lines src/ootp_ai/parser/header.py:5-8 and :13-14",
    "problem": "Phase 7 says to correct the 'zero exemptions' claim 'and update the bullet at :13 so the example it warns about is not the construction the module contained'. Verified: :13-14 warns about a NAIVE reader comparing `data[0:4]` against `b/"OOTP/"` and seeing `/x00OOT` — a construction this module never contained, that describes the format's real trap, and that stays exactly true after the `startswith` rewrite. The false claim is confined to :5-8 ('reads through the ordinary cursor ... rather than indexing offsets 1, 5 and 25 with literals' + 'zero exemptions'), which line 114's `data[0] == LEADING_NULL and data[1:_MAGIC_PREFIX_LEN] == MAGIC` contradicts. Both planner 3 and the merge repeat this misreading; a cold implementer will edit correct prose.",
    "proposed_fix": "Cut the `:13` half of the step. Replace with: 'confirm :13-14 still reads true — it describes a naive reader's error, not this module's code, and the startswith rewrite does not touch it. Only :5-8 is false and needs correcting.'",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-17",
    "title": "Phase 4's cry-wolf control names world.py:844 but not the identical :851",
    "severity": "nit",
    "confidence": "high",
    "category": "completeness",
    "location": "merged plan phases[3] Phase 4 step 8 (cry-wolf controls) vs files_to_touch['src/ootp_ai/parser/world.py'] and code_references['src/ootp_ai/parser/world.py:844,851']",
    "problem": "Verified: `pattern[_LENGTH_PREFIX_WIDTH:]` appears twice, at world.py:844 and world.py:851, both inside `_find_unique`'s refusal messages. The merge's code_references and files_to_touch both name the pair; Phase 4's cry-wolf control step names only :844. In a plan whose entire method is exhaustive citation so a cold implementer can check each site, the single-line reference invites a partial verification.",
    "proposed_fix": "Change the control's comment to name both occurrences: 'world.py:844 and :851 — the same shape, twice'. Trivial, but it keeps Phase 4's controls in one-to-one correspondence with the surviving real lines they protect.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-18",
    "title": "Phase 2's new `looks_like_save_file` test is new coverage folded into the riskiest phase",
    "severity": "nit",
    "confidence": "high",
    "category": "scope-creep",
    "location": "merged plan phases[1] Phase 2 step 6 and files_to_touch['tests/test_save_header.py']",
    "problem": "The merge is right on the fact — verified, `looks_like_save_file` is defined at header.py:103, exported at :50, called only at saves.py:119, and no test file references it (the merge correctly declined planner 1's unverified claim that test_parse_world.py:344 and test_parse_teams_synthetic.py:227 probe it). But adding four new cases for a function the bug never touched sits inside the phase whose acceptance is 'the gamedata baseline reproduces exactly and no existing test changed'. New test files landing in that same commit muddy the signal, and the rewrite it protects is the one Phase 2 change that could have been deferred entirely.",
    "proposed_fix": "Move the header rewrite and its new test into Phase 1 (a pure addition phase, and the test is offline/synthetic), or split them into their own small commit before Phase 2's parser rewiring. Either way Phase 2's diff stays purely mechanical rewiring, which is what its acceptance assumes.",
    "reviewer": "meta-audit"
  },
  {
    "id": "MERGE-19",
    "title": "The two central cautions are restated four to seven times each",
    "severity": "nit",
    "confidence": "high",
    "category": "dedup",
    "location": "merged plan: 'migrate first, widen second' in summary, decisions[0], risks[6], convergence_map[0], Phase 3 commit_note; 'CI cannot see gamedata' in summary, Phase 1 step 1, Phase 2 acceptance, testing (three separate paragraphs), risks[1], convergence_map[4]",
    "problem": "Both points are correct and load-bearing, and repeating a stop-condition once for emphasis is good cold-handoff practice. Seven copies is not: it inflates a plan a cold agent must read end to end before Phase 1, and it makes the genuinely single-copy items (the NameError trap at players.py:244, the `slot` ambiguity, the unsatisfiable grep) harder to spot in the same visual weight. The merge inherited the repetition from all three proposals rather than converging it.",
    "proposed_fix": "State each once in its owning section — ordering in decisions[0], the CI gap in the testing section's 'THE GAP CI CANNOT COVER' paragraph — and elsewhere cross-reference rather than restate ('see D1', 'see Testing §gap'). Reclaim the space for the per-phase traps, which are what a cold implementer actually loses time to.",
    "reviewer": "meta-audit"
  }
]
```


## Gated decisions

```json
[
  {
    "question": "Does this warrant an ADR under `docs/decisions/`? It settles a rule every future parser change passes through and creates the first module in the parser's history to carry a standing exemption.",
    "recommendation": "YES — a short ADR, raised at the Phase 7 gate rather than decided inside the implementation. Two planners raised this independently and the argument is the same: the next agent who finds the guard inconvenient will look for the reasoning, and a test-module docstring is the wrong place to keep it. The counter-argument is real — the repo has nineteen ADRs and this is arguably an elaboration of the existing ban rather than a new decision — but the allowlist is genuinely new and its rationale (why annotation-grounded, why two modules, why the interior rule) is the kind of thing that decays into folklore without a decision record. Either way this is main-thread work: `docs/decisions/` is in the data-engineer subagent's deny set (tests/test_agent_contract.py:80).",
    "related": [
      "Phase 7",
      "src/ootp_ai/parser/lookahead.py",
      "tests/test_no_fixed_offsets.py"
    ]
  },
  {
    "question": "Ship Phase 6 (the module-constant folding rule over lookahead call arguments), or stop after Phase 5 and rely on the width-sum rewrite plus review?",
    "recommendation": "SHIP IT. Without Phase 6, the guard still cannot see the exact shape that prompted this request — a record-relative constant handed as an argument (players.py:553, :557) — and the next author can write `_TEAM_ID_OFFSET = 58; peek_u32(data, position + _TEAM_ID_OFFSET)` and pass. Phase 5 makes today's two instances defensible; only Phase 6 makes the CLASS checked. It is grounded in a convention already unbroken in the tree (world.py:202-209, players.py:244-247), and it is cheap: a module-level constant table, a recursive legality test, three fixtures. The honest cost is one more moving part in a test module and a residual it must document (a position computed into a LOCAL still evades it). If the operator wants to cut scope, this is the ONLY phase that can be dropped without leaving a false claim behind — cut it, and Phase 7's docstring must say the argument case is caught by review and by the named-width form, not by the scan.",
    "related": [
      "Phase 5",
      "Phase 6",
      "Phase 7",
      "src/ootp_ai/parser/players.py:553"
    ]
  },
  {
    "question": "How far should Phase 2 be split? Twenty-odd sites in five modules is a large single commit for a repo whose convention is vertical slices.",
    "recommendation": "SPLIT IT BY MODULE — players / teams / world / human_managers+header — into four commits, unless the operator prefers one. The acceptance criteria hold unchanged per slice, and four smaller reverts beat one large one on the phase carrying the highest silent-failure risk in the plan. The cost is four gamedata runs instead of one, which is minutes. The counter-argument is that the seam is only coherent once every caller is on it, and a half-migrated tree is a state nobody wants to be interrupted in — but each module is independently complete, so that state is never entered. Operator's call on appetite; the plan is written so either choice works without rewriting a step.",
    "related": [
      "Phase 2",
      "src/ootp_ai/parser/players.py",
      "src/ootp_ai/parser/teams.py",
      "src/ootp_ai/parser/world.py"
    ]
  },
  {
    "question": "In Phase 3, should the repro fixture `SUBSCRIPT_OFFENDER` be annotated `data: bytes`, or should the rule keep a bare-name fallback over `{data, buf, buffer}` — or both?",
    "recommendation": "BOTH, each with its own failing witness, which is what the plan prescribes. The fixture at tests/test_no_fixed_offsets.py:96-99 declares `def read_team_id(data, record_start)` with no annotation, so a purely annotation-grounded rule would turn the repro green only by accident of the fallback — and shipping only the annotation rule means the repro passes for the wrong reason. Annotating the fixture is defensible (every real walker annotates; the fixture mirrors the parser's style) and the narrow fallback closes the unannotated case at almost no cost, provided it skips string-constant indices so snapshot.py's dict shape stays clear. If the implementer would rather ship one mechanism, that is a REAL narrowing of coverage and should come back here rather than be decided silently in the diff.",
    "related": [
      "Phase 3",
      "tests/test_no_fixed_offsets.py:96-99"
    ]
  },
  {
    "question": "Should the guard also treat `bytearray` and `memoryview` annotations as buffers?",
    "recommendation": "NO, not now. Every buffer parameter in the tree today is annotated `bytes` — verified across all 17 modules under `src/ootp_ai/` — so adding the branches is speculative, and CLAUDE.md is explicit that abstractions appear when their phase does. The counter-argument is real: a future streaming reader would evade the rule by annotation alone, and adding two names to an accepted-annotation set costs one line. My call is to leave the set at `{bytes}` and NAME the gap in the guard's docstring, so it is a known bounded residual rather than an oversight — the same treatment the rename hole and the local-variable hole get. If the operator would rather pay one line now than remember later, widening the set is safe and changes nothing in the current tree.",
    "related": [
      "Phase 3",
      "tests/test_no_fixed_offsets.py"
    ]
  },
  {
    "question": "`world.py:844` and `:851` slice `pattern[_LENGTH_PREFIX_WIDTH:]` — a `bytes`-annotated parameter that is not a save buffer. The rule lets it through because the index is a lone Name. Is that asymmetry acceptable, or should the rule flag every subscript on every `bytes` parameter?",
    "recommendation": "ACCEPT THE ASYMMETRY, and name it in the docstring so nobody later reads it as an oversight. Requiring arithmetic-or-a-literal is a principled narrowing — a fixed-offset read IS arithmetic-or-literal indexing, and a lone-Name index carries no constant. Flagging every subscript on every `bytes` parameter would either cry wolf on these two error-message slices or force a rewrite of `_find_unique`'s refusal messages, which is pure scope creep into code that has nothing to do with this bug. The honest consequence, which Phase 7's docstring must carry: 'no buffer subscripts outside the seam' is a Phase-2 DISCIPLINE goal, while the guard enforces the narrower 'no arithmetic or literal buffer subscript outside the seam'. If the operator wants the stronger invariant mechanically enforced, it costs a rewrite of world.py:833-856 and should be its own request.",
    "related": [
      "Phase 2",
      "Phase 3",
      "src/ootp_ai/parser/world.py:844"
    ]
  }
]
```
