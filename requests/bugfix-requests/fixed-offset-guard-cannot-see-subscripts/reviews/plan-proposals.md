# Planning panel — raw proposals

Unfiltered output of the three planners, kept as the provenance trail.
Panel health: {"planners_ok": 3, "adversaries_ok": 2, "meta_audit_ok": 1, "findings": 46, "blockers": 1, "majors": 14}
Degraded lenses: []

> **Machine paths stripped.** The panel's subagents emit absolute paths; this repo is
> public and `tests/test_no_leaks.py` refuses them (ADR 0006). Paths here are
> repo-relative. Nothing else was altered.

## Planner 1

```json
{
  "planner": "code-grounded",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Its verdict (confirmed-bug, full track), its refutation of the docs-only third option, and its three fix tiers (Minimal / Root / Hardening) are consumed, not re-litigated. The 'Root' tier explicitly names the rule choice as 'the planning stage's real question' — this plan answers it."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/BUGFIX_REQUEST.md",
      "why": "Context only. Its 'Affected Area & Pointers' survey table (lines 100-106) is the inventory of every current direct-buffer read and the judgment on each; Phase 2 works down that list. Two of its citations have drifted — see code_references."
    },
    {
      "path": "tests/test_no_fixed_offsets.py",
      "why": "The guard itself, and the whole change surface for Phase 3. `FixedOffsetVisitor` (line 29), `visit_Call` (line 43), `scan_source` (line 65), the committed red repro `test_the_scanner_flags_a_record_relative_subscript` (line 115) and the real scan `test_no_parser_module_seeks_to_a_fixed_offset` (line 143). Note SCAN_ROOT (line 26) is `src/ootp_ai` only."
    },
    {
      "path": "src/ootp_ai/parser/primitives.py",
      "why": "The Cursor — the *structural* half of the ban. Read lines 1-19 (the module docstring) and lines 96-104 (`position` is a read-only property, no setter). Lines 12-13 claim the AST guard runs 'with zero exemptions'; that sentence becomes false the moment an allowlisted module exists and must be rewritten in Phase 5."
    },
    {
      "path": "src/ootp_ai/parser/players.py",
      "why": "Carries both hazards. `_looks_like_record` (line 540) hands record-relative constants to lookahead helpers at lines 553 and 557; the constants are defined at lines 219-220; `_peek_u8`/`_peek_u32`/`_peek_date` (lines 572, 577, 584) are three of the helpers Phase 1 extracts; `_read_record` (line 444) is the head layout Phase 4's arithmetic must agree with."
    },
    {
      "path": "src/ootp_ai/parser/teams.py",
      "why": "Holds the second `_peek_u32` (line 596) — whose docstring at line 599 states the rule in prose — and `_scan_string` (line 581), which is a near-duplicate of world.py's. Both move to the new lookahead module in Phase 2."
    },
    {
      "path": "src/ootp_ai/parser/world.py",
      "why": "Holds the third `_peek_u32` (line 874) and the second `_scan_string` (line 859). Also line 743 — `offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH` — which the RCA names as 'the model to copy' and which Phase 4 imitates in players.py."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "why": "The single owner of the build rules. Lines 69-74 own the fixed-offset ban and are one of the two doc claims the RCA says must be corrected as a consequence of what the guard ends up covering. Its write allowlist (see tests/test_agent_contract.py:76-81) denies `tests/` and `CLAUDE.md` — a hard constraint on who may execute Phases 3 and 5."
    },
    {
      "path": "tests/test_sequential_walk.py",
      "why": "AC2, the sibling guard, and the house style for 'a guard must be seen to fail' — `read_at_fixed_offsets` (line 44) is a deliberate negative control, and `test_the_cursor_exposes_no_way_to_seek` (line 145) already names test_no_fixed_offsets.py as the thing that must not be satisfiable while the hazard walks in another door. It lives in `tests/`, outside SCAN_ROOT, and must stay that way."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "why": "The precedent set by the previous guard bugfix in this repo: a second test module that owns the guard's *scope* separately from its *patterns*, with a runtime-constructed probe. Lines 1-21 explain why scope and pattern fail differently. Phase 3's new tests follow this shape."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The pipeline contract. Line 24: /"'Done' means the red reproduction goes green and a regression test is left behind./" Line 45 gives the status grammar (`intake` → `diagnosed` → `planned` → `fixed`); line 51 is the Index row this work advances."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "The gate the local cadence mirrors: `uv run ruff check .` (line 46), `uv run ruff format --check .` (line 49), `uv run mypy` (line 52), `uv run pytest -m /"not gamedata/"` (line 57). CI cannot run the gamedata tests, so the refactor's strongest regression evidence only exists on the operator's machine."
    }
  ],
  "architecture_notes": "CURRENT STRUCTURE OF THE TOUCHED AREA/n/nThe fixed-offset ban is enforced by two mechanisms that cover disjoint code, and the gap between them is the bug./n/n1. The structural half — `src/ootp_ai/parser/primitives.py`. `Cursor` (line 73) has `__slots__ = (/"_data/", /"_label/", /"_position/")`, a single mutation point `_advance` (line 115), and `position` exposed as a read-only property (line 96) with no setter. There is no `seek`, no absolute read. `tests/test_sequential_walk.py:145` asserts the absence by name. A walk conducted through the cursor genuinely cannot seek — the RCA concedes this and so do I./n/n2. The mechanical half — `tests/test_no_fixed_offsets.py`. `FixedOffsetVisitor` (line 29) defines exactly one handler, `visit_Call` (line 43), matching `.seek(<nonzero int literal>)` and `unpack_from(..., <nonzero int literal>)`. `scan_source` (line 65) parses and walks; `test_no_parser_module_seeks_to_a_fixed_offset` (line 143) runs it over `SCAN_ROOT.rglob(/"*.py/")` where `SCAN_ROOT = src/ootp_ai` (line 26). An `ast.Subscript` has no handler, so `generic_visit` walks past it./n/nTHE SECOND READ PATH, WHICH NEITHER MECHANISM COVERS/n/nEvery walker in `src/ootp_ai/parser/` holds `data: bytes` alongside its cursor and indexes it directly for lookahead, landmark search and framing. Measured by grep over `src/ootp_ai/` on 2026-08-18, nineteen sites index a buffer outside `primitives.py`:/n/n  players.py:424, 529, 574, 581, 588, 589, 590/n  teams.py:522, 590, 605/n  world.py:740, 744, 745, 746, 759, 868, 883/n  human_managers.py:204, 244, 248/n  header.py:114/n/nThe cursor governs none of them and the AST scan sees none of them. Three of those sites are the *same function copy-pasted*: `_peek_u32` at `teams.py:596`, `world.py:874` and `players.py:577`, each with a docstring asserting the rule in prose (/"never at a constant/"). Two more are near-duplicates: `_scan_string` at `teams.py:581` (returns `(length, end)`) and `world.py:859` (returns `end`). The seam already wants to exist./n/nTWO HAZARDS, NOT ONE — and the plan must keep them apart/n/nH1 — direct buffer indexing at a record-relative constant. The repro's shape: `data[record_start + 58 : record_start + 62]`. An `ast.Subscript`. Catchable./n/nH2 — a record-relative constant handed *as an argument* to a sanctioned lookahead helper. `players.py:553` reads `_peek_date(data, position + _BIRTH_DATE_LOOKAHEAD)` and `:557` reads `_peek_u8(data, position + _AGE_LOOKAHEAD)`, with the constants 12 and 19 at `players.py:219-220`. These are `ast.Call` nodes whose actual indexing happens inside the helper against a parameter. **No `visit_Subscript`, and no module-scoping rule, catches H2** — the RCA's line /"Module-scoped … is the one that would have caught this/" is true of H1 and not of H2, and a plan that conflates them ships a guard whose docs overclaim exactly the way today's do. H2 is what the RCA's Hardening tier is really about./n/nWHERE THE CHANGE HOOKS IN — the chosen rule/n/nDetection is **module-scoped plus type-grounded**, not syntax-grounded:/n/n  (a) A new module `src/ootp_ai/parser/lookahead.py` becomes the single sanctioned home for indexing a save buffer. It absorbs the three `_peek_u32`, the two `_scan_string`, `_peek_u8`, `_peek_date`, the zero-run scan and the printable-ASCII scan./n  (b) `FixedOffsetVisitor` gains `visit_FunctionDef`/`visit_AsyncFunctionDef` to track, on a stack, which parameter names of the enclosing function are annotated `bytes`, and `visit_Subscript` to flag any subscript whose object is such a name — in any module under `src/ootp_ai/` except an ALLOWLIST of `{src/ootp_ai/parser/lookahead.py, src/ootp_ai/parser/primitives.py}`./n/nWhy type-grounded rather than the RCA's name-based allowlist (`_peek_*`/`_scan_*`/`_find_*` may index): the RCA itself notes an author can name anything `_peek_` and the guard believes them. Annotation-grounding is defeatable only by dropping the `bytes` annotation, which mypy strict (`pyproject.toml:91-95`, `strict = true`, `files = [/"src/", /"tests/"]`) makes loud rather than silent./n/nWhy NOT the second, syntax-based net (flag any subscript whose index is a BinOp with a nonzero int literal) as a belt-and-braces addition: it cries wolf on real code today. `teams.py:624` reads `park_id, league_id = run[base], run[base + 1]` where `run: tuple[int, ...]` — benign tuple indexing, and the guard's own docstring (lines 9-10) says /"a guard that cries wolf gets loosened, and a loosened guard is worse than none./" Rejected on measured evidence, not taste./n/nWhy the object-name set must not be the naive `{data, buf, buffer, payload, raw}`: `src/ootp_ai/snapshot.py:227,239,242-244` index a JSON dict named `payload`, and `src/ootp_ai/parser/teams.py:382` reads `raw[-1].team_id` off a list of records. The annotation rule excludes both by construction. A bare-name fallback, if kept at all, must be limited to `{data, buf, buffer}` and must skip string-constant indices./n/nTwo sites need naming rather than mechanism. `primitives.py:140` indexes `self._data[start : start + count]` — an `ast.Attribute`, not a Name parameter, so the rule never sees it; `primitives.py` is allowlisted anyway so the intent is explicit rather than accidental. `header.py:114` reads `data[0] == LEADING_NULL and data[1:_MAGIC_PREFIX_LEN] == MAGIC` inside `looks_like_save_file(data: bytes)` (line 103) — a file-magic check at the file's own head, which is not a record-relative offset. It moves behind `peek_u8`/`peek_bytes` so the rule stays exemption-free; the literal `0` and `1` survive as call arguments, which the guard deliberately does not police./n/nWHAT THE GUARD STILL WILL NOT DO, and must therefore say/n/nAfter this change the guard covers H1 completely and H2 not at all. That is the honest sentence the RCA demanded and it must replace `CLAUDE.md:103`, `.claude/agents/data-engineer.md:69-74`, `primitives.py:12-13` (/"zero exemptions/" — false once an allowlist exists), `tests/test_no_fixed_offsets.py:1-18` and the blockquote at `docs/data-access.md:228-230`. H2 is instead answered by construction in Phase 4: re-express the two constants as sums of named field widths, the form `world.py:743` already uses, with a test binding them to the layout `_read_record` (players.py:444) actually walks.",
  "phases": [
    {
      "name": "Phase 1 — Give buffer lookahead one legitimate home",
      "goal": "Land `src/ootp_ai/parser/lookahead.py` as the single sanctioned place to index a save buffer, with its own unit tests. No caller changes yet, so nothing can regress.",
      "steps": [
        "Create `src/ootp_ai/parser/lookahead.py`. Its module docstring must state the rule the three duplicate `_peek_u32` docstrings state in prose today (`teams.py:599`, `world.py:877`, `players.py:578`): every position is computed from the data or from a landmark, never a constant measured against a different save. It must also say plainly that this module is the guard's ALLOWLIST and that a function added here is exempt from a check nothing else in `src/ootp_ai/` is — so a reviewer knows an addition here costs more than an addition elsewhere.",
        "Implement, all fully annotated for mypy strict: `peek_u8(data: bytes, position: int) -> int | None`; `peek_u32(data: bytes, position: int) -> int | None`; `peek_bytes(data: bytes, position: int, width: int) -> bytes | None`; `peek_date(data: bytes, position: int) -> SaveDate | None`; `zero_run_width(data: bytes, position: int, limit: int) -> int`; `is_zero_run(data: bytes, position: int, width: int) -> bool`; `is_printable_ascii(data: bytes, position: int, width: int) -> bool`; `scan_string(data: bytes, position: int, limit: int) -> tuple[int, int] | None`.",
        "Copy the bodies verbatim from their current homes rather than rewriting them: `peek_u32` from `players.py:577-581` (identical to `teams.py:596-605` and `world.py:874-883` except that players.py additionally guards `position < 0` — keep the strictest form, the `position < 0` guard, in the shared version); `peek_u8` from `players.py:572-574`; `peek_date` from `players.py:584-592`; `scan_string` from `teams.py:581-593`, which is the richer of the two return shapes (`(length, end)`) and a superset of `world.py:859-871`'s (`end`).",
        "`peek_date` imports `SaveDate` from `ootp_ai.parser.primitives` — check the resulting import direction does not create a cycle (`primitives.py` imports only `ootp_ai.parser.errors`, line 27, so `lookahead` → `primitives` is safe and `primitives` must not import `lookahead`).",
        "Write `tests/test_lookahead.py`: bounds behaviour at both ends (a negative position, a position past the end, a read that straddles the end all return `None` rather than a short or garbage value), `peek_date` returning `None` for bytes that are not a date, `scan_string` refusing a non-printable payload and refusing a length that overruns the buffer, `zero_run_width` stopping at `limit`. All synthetic bytes; no game data, no MySQL."
      ],
      "acceptance": [
        "`uv run pytest` green, including the new `tests/test_lookahead.py`.",
        "`uv run ruff check .` and `uv run ruff format --check .` clean.",
        "`uv run mypy` clean under strict.",
        "`tests/test_no_fixed_offsets.py` is unchanged and still has exactly one failing test — the committed repro at line 115. Nothing else in the suite has changed status.",
        "Grep confirms the three `_peek_u32` definitions still exist at `teams.py`, `world.py`, `players.py` — this phase adds, it does not yet delete."
      ],
      "commit_note": "Give buffer lookahead a single legitimate home"
    },
    {
      "name": "Phase 2 — Route every direct buffer read through it",
      "goal": "Move all nineteen direct-index sites in `src/ootp_ai/` outside `primitives.py` onto `lookahead.py`, deleting the triplicated `_peek_u32` and the duplicated `_scan_string`. Behaviour-preserving by construction; the existing parser suite is the proof.",
      "steps": [
        "`players.py`: replace `_peek_u8` (572-574), `_peek_u32` (577-581) and `_peek_date` (584-592) with imports from `lookahead`. Rewrite `players.py:424` (`data[cursor.position] == 0`) and `players.py:529` (`data[after] == 0`) as `peek_u8(...) == 0`. Update the four call sites at 549, 553, 557 and `_read_preamble` accordingly. Do NOT touch the values of `_BIRTH_DATE_LOOKAHEAD`/`_AGE_LOOKAHEAD` in this phase — that is Phase 4.",
        "`teams.py`: delete `_peek_u32` (596-605) and `_scan_string` (581-593); import from `lookahead`. Update the five `_peek_u32` call sites (375, 509, 559, 571, 587) and the `_scan_string` call at 552. Rewrite `teams.py:522` (`data[position : position + 1] == _FLAG_BYTE`) as `peek_bytes(data, position, 1) == _FLAG_BYTE`.",
        "`world.py`: delete `_peek_u32` (874-883) and `_scan_string` (859-871); import from `lookahead`. Update the seven `_peek_u32` call sites (574, 588, 599, 708, 734, 752, 865). `_scan_string` now returns `(length, end)` where world's callers expect `end` — take `[1]` at each call site, or unpack; find them by grep before editing, do not assume there is only one. Rewrite `world.py:740` (`data[pad_at:length_at] != b/"/x00/" * _EVENT_PAD_WIDTH`) as `not is_zero_run(data, pad_at, _EVENT_PAD_WIDTH)`, `world.py:744-746` (the day/month/year decode) as a single `peek_date(data, date_at)` — note this changes the shape of `_scan_event`'s validation, so keep the `_MAX_DAY`/`_MAX_MONTH`/`_MIN_YEAR`/`_MAX_YEAR` checks (747-750) operating on the returned `SaveDate`, and preserve the `year != 0` special case exactly — and `world.py:759` as `is_printable_ascii(data, name_at, length)`.",
        "`human_managers.py`: rewrite `_pad_width`'s loop (204) as `zero_run_width(data, position, _MAX_PAD)`, keeping the `width >= _MAX_PAD` refusal at 206-210 intact. Rewrite `_is_club_landmark` (244, 248) onto `peek_u32`, preserving the `None`-vs-zero distinction — `peek_u32` returns `None` past the end where `int.from_bytes` on a short slice would silently return a small integer, so the rewritten function must treat `None` as 'not a landmark'.",
        "`header.py`: rewrite `looks_like_save_file` (114) as `peek_u8(data, 0) == LEADING_NULL and peek_bytes(data, 1, _MAGIC_PREFIX_LEN - 1) == MAGIC`. Keep the `len(data) < _MAGIC_PREFIX_LEN` early return at 112-113 or let the `None` returns carry it — either is correct, but state which in a comment, because `test_parse_world.py:344` and `test_parse_teams_synthetic.py:227` both probe this path.",
        "Update `src/ootp_ai/parser/__init__.py:3` — 'The spine is three modules and one rule' is now four.",
        "Run the full local suite INCLUDING the gamedata-marked tests (CI cannot: `.github/workflows/ci.yml:57` runs `-m /"not gamedata/"`). The field-by-field export comparisons — `test_parse_players.py:525`, `test_parse_players.py:579`, `test_parse_real_save.py:446`, `test_parse_real_save.py:538`, `test_parse_real_save.py:599` — plus the byte-accounting totals in `tests/test_byte_accounting.py` are what actually prove this refactor changed nothing."
      ],
      "acceptance": [
        "`uv run pytest` (full, gamedata included) green with **zero edits to any existing parser test**. If a parser test had to change, the refactor was not behaviour-preserving and must be reverted rather than accommodated.",
        "`grep -rn 'data/[' src/ootp_ai/` returns hits only in `parser/lookahead.py`. `grep -rn '_peek_u32' src/ootp_ai/` returns nothing.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all clean.",
        "`tests/test_byte_accounting.py::test_every_byte_is_either_inside_a_walked_region_or_reported_as_un_walked` and `::test_the_player_walk_consumes_essentially_the_whole_file` report the same numbers as before the phase — record them before starting so the comparison is possible."
      ],
      "commit_note": "Route every buffer read through the lookahead seam"
    },
    {
      "name": "Phase 3 — Widen the guard to the rule, and turn the repro green",
      "goal": "Teach `FixedOffsetVisitor` the scope rule: a subscript on a `bytes`-annotated parameter is a violation anywhere under `src/ootp_ai/` outside the allowlist. The committed red repro goes green and the regression tests are left behind.",
      "steps": [
        "In `tests/test_no_fixed_offsets.py`, add `ALLOWED_TO_INDEX: frozenset[str] = frozenset({/"src/ootp_ai/parser/lookahead.py/", /"src/ootp_ai/parser/primitives.py/"})`. The real scan at line 149 already passes `path.relative_to(REPO_ROOT).as_posix()` as the filename, so the allowlist keys match without further plumbing, and the synthetic fixtures (which pass names like `/"subscript.py/"`) are never accidentally exempt.",
        "Give `FixedOffsetVisitor.__init__` a `self._bytes_params: list[set[str]]` stack and an `self._allowed: bool` computed from `filename in ALLOWED_TO_INDEX`.",
        "Add `visit_FunctionDef` and `visit_AsyncFunctionDef`: push the set of parameter names (`args.args + args.posonlyargs + args.kwonlyargs`) whose annotation is `ast.Name(id=/"bytes/")`, union it with the enclosing frame so a nested def still sees its closure, `generic_visit`, then pop. Do not forget `generic_visit` — omitting it is exactly the failure mode being fixed.",
        "Add `visit_Subscript`: if `self._allowed`, `generic_visit` and return. Otherwise, if `isinstance(node.value, ast.Name)` and `node.value.id` is in the current frame's set, append a violation naming the file, line, the buffer name, and the fact that only `parser/lookahead.py` may index a save buffer. Then `generic_visit`.",
        "Handle the repro fixture: `SUBSCRIPT_OFFENDER` (lines 96-99) reads `def read_team_id(data, record_start)` with NO annotation, so the annotation rule alone will not fire on it. Two lawful options — annotate the fixture `data: bytes` (it is a synthetic offender written to mirror the parser's real style, and every real walker does annotate), or add a narrow bare-name fallback `{/"data/", /"buf/", /"buffer/"}` that skips string-constant indices. Prefer annotating the fixture and adding the fallback, and add a THIRD fixture proving each path independently: one annotated-but-oddly-named, one unannotated-and-named-`data`. Do not silently pick one and leave the other hazard uncovered.",
        "Add the regression tests, in the shape `tests/test_leak_guard_scope.py` established: (a) the same offending source scanned under the filename `src/ootp_ai/parser/lookahead.py` yields NO violations, and under `src/ootp_ai/parser/players.py` yields one — this proves the allowlist, not the content, is the discriminator; (b) a source containing `run[base + 1]` where `run: tuple[int, ...]` yields no violations (the anti-cry-wolf case, grounded in the real `teams.py:624`); (c) a source containing `payload[/"manifest_version/"]` yields no violations (the real `snapshot.py:227` shape); (d) `ALLOWED_TO_INDEX` names only files that exist on disk — an allowlist entry for a deleted file is a silent hole.",
        "Update the module docstring (lines 1-18). It currently says the ban runs on `.seek` and `unpack_from` and that only 'a hardcoded number is the hazard'. It must now describe the scope rule, name the allowlist, and state explicitly that a record-relative constant handed to a lookahead helper — `players.py`'s H2 shape — is NOT caught by this scan and is answered by Phase 4's arithmetic instead.",
        "Leave `SCAN_ROOT` at `src/ootp_ai` (line 26). Do not widen it to `tests/`: `tests/test_sequential_walk.py:44-58` is a deliberate negative control that indexes `data[20 : 20 + name_len]`, and flagging it would either break AC2 or force the exemption this design refuses. Say so in a comment at line 26."
      ],
      "acceptance": [
        "`uv run pytest tests/test_no_fixed_offsets.py` fully green — including `test_the_scanner_flags_a_record_relative_subscript`, which was RED on arrival (`AssertionError: … passed the guard because it was written as a subscript rather than a call / assert []`).",
        "`test_no_parser_module_seeks_to_a_fixed_offset` green over the real `src/ootp_ai/` tree, i.e. Phase 2 actually finished.",
        "The guard is SEEN TO FAIL: temporarily add `def read_team_id(data: bytes, record_start: int) -> int: return int.from_bytes(data[record_start + 58 : record_start + 62], /"little/")` to `src/ootp_ai/parser/players.py`, confirm `test_no_parser_module_seeks_to_a_fixed_offset` goes red naming `players.py`, then remove it. Record the observed failure text in the implementation report.",
        "The anti-cry-wolf tests (b) and (c) pass, and the full `uv run pytest` shows no new failures anywhere.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean — mypy is strict over `tests/` too (`pyproject.toml:95`), so the visitor's new stack and handlers need complete annotations."
      ],
      "commit_note": "Teach the guard where a save buffer may be indexed"
    },
    {
      "name": "Phase 4 — Retire the two raw record-relative constants",
      "goal": "Answer the hazard the guard structurally cannot see (H2) by construction rather than by promise: re-express `_BIRTH_DATE_LOOKAHEAD` and `_AGE_LOOKAHEAD` as sums of named field widths, in the form `world.py:743` already uses, and bind them to the layout `_read_record` walks.",
      "steps": [
        "Add named width constants to `src/ootp_ai/parser/players.py` beside the existing gap constants at 244-247: `_PLAYER_ID_WIDTH = 4`, `_NAME_INDEX_WIDTH = 4`, `_DATE_WIDTH = 4`, `_AGE_WIDTH = 1`. Each mirrors a `Cursor` read in `_read_record` (players.py:451-456): `cursor.u32()`, two `cursor.u32()`, `cursor.date()`, `cursor.u8()`.",
        "Replace `players.py:219` `_BIRTH_DATE_LOOKAHEAD = 12` with `_PLAYER_ID_WIDTH + 2 * _NAME_INDEX_WIDTH` (= 4 + 8 = 12) and `players.py:220` `_AGE_LOOKAHEAD = 19` with `_BIRTH_DATE_LOOKAHEAD + _DATE_WIDTH + _GAP_AFTER_BIRTH_DATE` (= 12 + 4 + 3 = 19). `_GAP_AFTER_BIRTH_DATE = 3` already exists at line 244 — move the width constants above line 219 so the definitions resolve in order.",
        "Rewrite the comment at players.py:214-218. It currently justifies the constants as 'validation lookaheads, not field reads'. That justification stands, but it must now also say the constants are derived rather than measured, and that the guard does not and cannot check the argument to a lookahead call — this arithmetic is what stands in for it.",
        "Add `test_the_validation_lookaheads_agree_with_the_head_the_walk_reads` to `tests/test_parse_players.py`. Build a synthetic record with the existing fixture helper used by `test_every_head_field_survives_the_walk` (tests/test_parse_players.py:91), then assert the byte at `_AGE_LOOKAHEAD` in that record equals the age the walk returned and the four bytes at `_BIRTH_DATE_LOOKAHEAD` decode to the date it returned. This is the test that fails if a future field is inserted into the head and someone forgets the lookahead — which is the whole point.",
        "Cross-check the arithmetic against the mask offset already documented at `players.py:264`: 'The assignment presence mask, at record+55.' Summing every width and gap in `_read_record` from 19 gives 19+1+1+1+5+4+2+1+1+1+1+14+4 = 55. If your named widths do not reproduce 55, one of them is wrong — fix the width, not the test."
      ],
      "acceptance": [
        "`uv run pytest` green, including all gamedata tests and specifically `test_parse_players.py::test_age_agrees_with_the_birth_date_in_every_record_of_every_save` (line 470) and `::test_every_landed_field_matches_the_export_exactly` (line 525) — the framing must be byte-identical to before.",
        "`_BIRTH_DATE_LOOKAHEAD == 12` and `_AGE_LOOKAHEAD == 19` still hold; assert both explicitly in the new test so a wrong re-expression cannot pass quietly.",
        "No bare integer literal remains as an addend to a position in `src/ootp_ai/parser/players.py` outside a width/gap constant definition.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean."
      ],
      "commit_note": "Express the record-relative lookaheads as named field widths"
    },
    {
      "name": "Phase 5 — Make every claim about the ban true",
      "goal": "Correct the five places that overclaim what is mechanically enforced, so the repo describes the guard that now exists. The RCA's refutation of the docs-only option said the docs still need correcting, as a consequence of what the guard covers — this is that consequence.",
      "steps": [
        "`CLAUDE.md:103` — 'The fixed-offset ban is the rulebook's, and CI enforces it.' Replace with a sentence that survives scrutiny: CI enforces that only `parser/lookahead.py` indexes a save buffer, and `Cursor` cannot seek by construction; a constant offset handed to a lookahead helper is caught by review and by the named-width form, not by the scan. Keep it to the file's one-line bullet register.",
        "`.claude/agents/data-engineer.md:69-74` — the rulebook's owning statement. Extend it with what the two mechanisms cover and the seam's name, and with the instruction that new buffer indexing goes in `parser/lookahead.py` or not at all. CRITICAL: `tests/test_agent_contract.py:62` requires the literal string 'fixed offset' to survive in the definition text (lower-cased match) — do not paraphrase it out.",
        "`src/ootp_ai/parser/primitives.py:12-13` — 'That is also what lets the AST guard over `src/ootp_ai/` run with zero exemptions: there is no legitimate seek anywhere for it to have to allow.' This is now false. Rewrite: the cursor still cannot seek, and the AST guard now confines buffer indexing to one reviewed module rather than allowing none.",
        "`docs/data-access.md:228-230` — the blockquote 'The parser must walk records sequentially. It must never seek to a fixed offset.' The claim stays and keeps its `verified` label (it is a claim about the format, not about the guard); add a following line naming where enforcement actually lives, so a reader does not infer total mechanical coverage. Do not upgrade or invent an epistemic label here — the format claim's evidence is unchanged by this bugfix.",
        "`requests/bugfix-requests/README.md:51` — set the `fixed-offset-guard-cannot-see-subscripts` Index row's Stage cell to `fixed` and add a note recording what the disposition actually was: the guard was widened AND the docs were narrowed, because the widened guard's coverage is real but partial.",
        "Advance the status blockquotes on `BUGFIX_REQUEST.md:1`, `ROOT_CAUSE_ANALYSIS.md:1` and `IMPLEMENTATION_PLAN.md:1` per the grammar at `requests/bugfix-requests/README.md:45`, and write `IMPLEMENTATION_REPORT.md` in the same directory.",
        "Consider whether this warrants an ADR under `docs/decisions/`. It settles a rule that every future parser change passes through and it creates a module with a standing exemption — the bar `CLAUDE.md` sets for an ADR. Raise it with the operator rather than deciding it inside the implementation; `docs/decisions/` is in the data-engineer subagent's deny set anyway.",
        "Run `/update-docs` before `/commit` so the doc gate sees this phase's edits as a set."
      ],
      "acceptance": [
        "`uv run pytest` green — specifically `tests/test_agent_contract.py::test_rulebook_invariants_survive`, `tests/test_doc_links.py` and `tests/test_doc_link_contract.py`, since this phase edits linked prose and every bare `requests/...` token in a live artifact body must resolve on disk.",
        "No file in the repo still says the ban runs 'with zero exemptions' or that 'CI enforces it' without qualification — grep for both phrasings.",
        "`requests/bugfix-requests/README.md`'s Index row and the three artifact status blockquotes agree with each other and with what landed.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` clean.",
        "The whole suite is green on a clean run from the branch tip, and the branch is ready for a PR the operator opens."
      ],
      "commit_note": "Say what the fixed-offset ban actually enforces"
    }
  ],
  "testing": "VERIFICATION SPINE/n/nThe bugfix track's acceptance contract is fixed by `requests/bugfix-requests/README.md:24` — the red repro goes green, a regression test is left behind, nothing else regresses. Concretely:/n/n1. THE RED REPRO. `tests/test_no_fixed_offsets.py::test_the_scanner_flags_a_record_relative_subscript` (line 115) is committed and RED today; I ran it to confirm: `uv run pytest tests/test_no_fixed_offsets.py` gives 4 passed, 1 failed with `AssertionError: a record-relative read at a constant offset passed the guard because it was written as a subscript rather than a call / assert []`. It must be GREEN at the end of Phase 3 with its assertion untouched. Rewriting the assertion to fit the implementation would void the contract./n/n2. THE REGRESSION TESTS LEFT BEHIND. Phase 3 adds four, following the shape `tests/test_leak_guard_scope.py` established for the previous guard bugfix in this repo: the allowlist discriminates by filename and not by content (same source, two filenames, two outcomes); a `tuple[int, ...]` subscript with a literal addend is not flagged (grounded in the real `teams.py:624`); a string-keyed dict subscript is not flagged (grounded in the real `snapshot.py:227`); every `ALLOWED_TO_INDEX` entry names a file that exists. Phase 1 adds `tests/test_lookahead.py`; Phase 4 adds the lookahead-agrees-with-the-head test to `tests/test_parse_players.py`./n/n3. THE GUARD MUST BE SEEN TO FAIL. This repo's culture insists on it — `tests/test_sequential_walk.py:10-12` carries a negative control for exactly this reason, and `test_no_fixed_offsets.py:102` is named `test_the_scanner_flags_a_synthetic_offender` with the docstring /"A guard never seen to fail is not a guard./" Phase 3's acceptance includes a manual mutation: paste the offending function into `src/ootp_ai/parser/players.py`, watch `test_no_parser_module_seeks_to_a_fixed_offset` go red naming the file and line, remove it. Record the observed output verbatim in `IMPLEMENTATION_REPORT.md`./n/n4. NOTHING ELSE REGRESSES — and this is where the real risk sits, because Phase 2 rewrites nineteen call sites in five parser modules. The proof is that the existing suite passes with ZERO edits to any existing parser test. The load-bearing ones are the export comparisons and the byte accounting: `tests/test_parse_players.py:525` (`test_every_landed_field_matches_the_export_exactly`), `:579` (club assignment on every row), `:470` (age agrees with birth date in every record of every save), `tests/test_parse_real_save.py:446` (every parsed team matches the export field by field), `:538` (division arrays), `tests/test_byte_accounting.py:268` and `:371`. Record the byte-accounting numbers before Phase 2 starts so /"unchanged/" is checkable rather than asserted./n/nLOCAL VS CI — A GAP THE IMPLEMENTER MUST NOT MISS/n/n`.github/workflows/ci.yml:57` runs `uv run pytest -m /"not gamedata/"`, because CI has no OOTP install and must not (ADR 0006). Most of the strongest regression evidence for Phase 2 — the export comparisons in `test_parse_real_save.py` and the gamedata half of `test_parse_players.py` — is gamedata-marked. **Run the FULL local suite, unfiltered, at every phase gate.** A green PR is not evidence the refactor preserved behaviour; only the operator's machine can produce that evidence, and the implementation report must state that it was produced./n/nPER-PHASE GATE/n/nEach phase ends at the same checkpoint before `/commit`: `uv run pytest` (full, gamedata included) → `uv run ruff check .` → `uv run ruff format --check .` (CI runs the format check at ci.yml:49; a plan that only runs `ruff check` will pass locally and fail CI) → `uv run mypy` (strict, over `src` and `tests`, per `pyproject.toml:91-95`). Then `/commit`, which stages deliberately, runs the doc-drift checks and asks before writing. Never `git commit` ad hoc. The PR stays the operator's./n/nWHAT IS DELIBERATELY NOT TESTED/n/nThe guard's rename hole. An author who writes `def f(b): return b[start + 58]` with no `bytes` annotation and a name outside the bare-name fallback defeats the scan. This is a known, bounded residual and it is documented rather than chased — chasing it means dataflow analysis in a test module, which is a maintenance liability larger than the gap. mypy strict makes dropping the annotation loud; the shrunken surface (one small reviewed module) makes the review cheap. Say this in the docstring rather than implying total coverage — implying total coverage is the bug being fixed.",
  "risks": [
    "THE BIGGEST RISK IS PHASE 2, NOT THE GUARD. Nineteen call sites across five parser modules get rewritten in one phase, and the modules are the ones that produce every number the front office will ever see. Mitigation: copy bodies verbatim in Phase 1 rather than rewriting them, and treat 'an existing parser test had to change' as a stop signal — revert, do not accommodate. If Phase 2 feels large, split it by module (players / teams / world / human_managers+header) into separate commits; the phase's acceptance criteria hold unchanged for each slice.",
    "`_scan_string` UNIFICATION CHANGES A RETURN SHAPE. `teams.py:581` returns `(length, end)`; `world.py:859` returns `end`. Unifying on the tuple means every world.py caller must take `[1]`. A missed call site becomes a `tuple` where an `int` was expected — mypy strict catches it, but only if the annotation is right. Grep for every caller before editing; do not assume the count.",
    "`peek_u32` HAS A `None` WHERE `int.from_bytes` HAD A NUMBER. `human_managers.py:244` currently reads `int.from_bytes(data[offset : offset + 4], /"little/")` on a slice that may be short near the buffer end — Python returns a small integer, not an error. `peek_u32` returns `None` there. That is strictly better, but it changes the branch structure of `_is_club_landmark` (242-250), which feeds a refusal that raises when it finds anything other than exactly one match (231-238). Get the `None` branch right or the landmark search can start refusing a save it used to read.",
    "`world.py:744-750` IS NOT A PURE `peek_date` SUBSTITUTION. The current code decodes day/month/year and then applies bounds (`_MAX_DAY`, `_MAX_MONTH`) plus a `year != 0` escape (line 749) that admits an absent date. `players.py`'s `_peek_date` (584-592) instead returns `None` unless `SaveDate.as_date()` succeeds — and `as_date()` on 0/0/0 returns `None` (primitives.py:58-67). So a naive swap would reject the absent-date events that `_scan_event`'s docstring (728-732) explicitly says must be admitted. Keep the raw-field access via `peek_u8`/`peek_u32` here, or give `lookahead` a `peek_raw_date` that returns the three integers without judging them.",
    "THE DATA-ENGINEER SUBAGENT CANNOT EXECUTE PHASES 3 AND 5. Its write allowlist denies `tests/`, `CLAUDE.md`, `.github/`, `ops/` and `docs/decisions/` — asserted by `tests/test_agent_contract.py:76-81`, and the reason given at line 77 is 'An agent that can edit the tests that catch it is the core failure mode.' Phase 3 edits `tests/test_no_fixed_offsets.py`; Phase 5 edits `CLAUDE.md`. Those phases are main-thread work. Phases 1, 2 and 4 are subagent-eligible.",
    "THE GUARD COULD STILL CRY WOLF ON CODE NOT YET WRITTEN. The rule forbids a `bytes` parameter from being indexed outside one module. A future walker that legitimately wants a one-off slice will hit it and the pressure will be to loosen the rule — which the guard's own docstring (lines 9-10) says is worse than none. Mitigation: the escape hatch is 'add a named helper to `lookahead.py`', which is cheap and reviewable. Say so in the violation message itself, not only in the docstring, so the person who hits it is told what to do instead.",
    "AN ALLOWLIST IS AN EXEMPTION AND `primitives.py` CURRENTLY BOASTS THERE ARE NONE. Lines 12-13 will be false from Phase 3 onward. If Phase 5 is deferred or dropped, the repo ends up with a *new* false claim in place of the old one — precisely the failure the RCA refuted the docs-only option for. Phase 5 is not optional polish; it is half the fix.",
    "THE H2 HAZARD SURVIVES AND SOMEONE WILL ASSUME IT DOESN'T. `players.py:553` and `:557` pass record-relative constants into lookahead helpers, and after this change the guard still cannot see them. Phase 4 makes those two defensible by construction, but it does not make the *class* mechanically checked. Every doc touched in Phase 5 must say that explicitly. Overclaiming here reproduces the exact bug at a different altitude.",
    "BRANCH STATE. Work is on `fix-fixed-offset-guard-subscripts`; the RCA landed as `df17337`. `main` is protected. Agents never push `main`, never force-push, never amend, and never open the PR — those stay the operator's (CLAUDE.md, project conventions).",
    "NO GAME DATA MAY ENTER GIT. Nothing in this change should produce a fixture from a real save, but Phase 2's debugging naturally reaches for one. `tests/test_no_leaks.py` fails the build on a machine path or a game artifact; it now enumerates untracked files too (see `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/`), so a scratch file written into the repo will trip it before it is staged. Keep scratch under `var/`."
  ],
  "files_to_touch": [
    {
      "path": "src/ootp_ai/parser/lookahead.py",
      "change": "NEW. The single sanctioned home for indexing a save buffer. Holds `peek_u8`, `peek_u32`, `peek_bytes`, `peek_date`, `zero_run_width`, `is_zero_run`, `is_printable_ascii`, `scan_string`, all `(data: bytes, position: int, …)`. Its docstring states that it is the guard's allowlist and that an addition here costs more than an addition elsewhere. Phase 1."
    },
    {
      "path": "tests/test_lookahead.py",
      "change": "NEW. Unit tests for the seam: bounds at both ends, negative positions, straddling reads returning `None`, `peek_date` refusing non-dates, `scan_string` refusing non-printable payloads and overrunning lengths, `zero_run_width` honouring its limit. Synthetic bytes only. Phase 1."
    },
    {
      "path": "src/ootp_ai/parser/players.py",
      "change": "Delete `_peek_u8` (572-574), `_peek_u32` (577-581), `_peek_date` (584-592); import from `lookahead`. Rewrite the direct index at 424 (`data[cursor.position] == 0`) and 529 (`data[after] == 0`). Phase 4: add `_PLAYER_ID_WIDTH`/`_NAME_INDEX_WIDTH`/`_DATE_WIDTH`/`_AGE_WIDTH` and re-express `_BIRTH_DATE_LOOKAHEAD` (219) and `_AGE_LOOKAHEAD` (220) as sums of them; rewrite the justifying comment at 214-218. Phases 2 and 4."
    },
    {
      "path": "src/ootp_ai/parser/teams.py",
      "change": "Delete `_peek_u32` (596-605) and `_scan_string` (581-593); import from `lookahead`. Update the five `_peek_u32` call sites (375, 509, 559, 571, 587) and the `_scan_string` call at 552. Rewrite the flag-byte compare at 522. Phase 2."
    },
    {
      "path": "src/ootp_ai/parser/world.py",
      "change": "Delete `_peek_u32` (874-883) and `_scan_string` (859-871); import from `lookahead`. Update the seven `_peek_u32` call sites (574, 588, 599, 708, 734, 752, 865) and every `_scan_string` caller for the changed return shape. Rewrite the pad check at 740, the date decode at 744-746 (see the risk about the `year != 0` escape at 749), and the printable scan at 759. Leave the named-width sum at 743 exactly as it is — it is the model Phase 4 copies. Phase 2."
    },
    {
      "path": "src/ootp_ai/parser/human_managers.py",
      "change": "Rewrite `_pad_width`'s zero-run loop (204) onto `zero_run_width`, keeping the `_MAX_PAD` refusal at 206-210. Rewrite `_is_club_landmark` (244, 248) onto `peek_u32`, handling the new `None` return as 'not a landmark'. Phase 2."
    },
    {
      "path": "src/ootp_ai/parser/header.py",
      "change": "Rewrite `looks_like_save_file`'s magic check at 114 onto `peek_u8`/`peek_bytes`, keeping the behaviour `test_parse_world.py:344` and `test_parse_teams_synthetic.py:227` probe. Note in a comment that offset 0 is a file head, not a record-relative offset. Phase 2."
    },
    {
      "path": "src/ootp_ai/parser/__init__.py",
      "change": "Line 3: 'The spine is three modules and one rule' — now four modules. Name `lookahead` and what it is for. Phase 2."
    },
    {
      "path": "tests/test_no_fixed_offsets.py",
      "change": "THE CORE CHANGE. Add `ALLOWED_TO_INDEX`, `visit_FunctionDef`/`visit_AsyncFunctionDef` (a stack of `bytes`-annotated parameter names) and `visit_Subscript` to `FixedOffsetVisitor` (29-62). Annotate `SUBSCRIPT_OFFENDER` (96-99) and add the two discriminating fixtures. Add the four regression tests. Rewrite the module docstring (1-18) to describe the scope rule, the allowlist, and what it still does not cover. Comment `SCAN_ROOT` (26) with why `tests/` stays out. Phase 3. MAIN THREAD ONLY — denied to the data-engineer subagent."
    },
    {
      "path": "tests/test_parse_players.py",
      "change": "ADD ONLY, never edit an existing test. New `test_the_validation_lookaheads_agree_with_the_head_the_walk_reads`, asserting `_BIRTH_DATE_LOOKAHEAD == 12`, `_AGE_LOOKAHEAD == 19` and that the bytes at each offset in a synthetic record decode to what the walk returned. Phase 4."
    },
    {
      "path": "CLAUDE.md",
      "change": "Line 103 — 'The fixed-offset ban is the rulebook's, and CI enforces it.' Replace with the true, narrower claim. Phase 5. MAIN THREAD ONLY."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "change": "Lines 69-74 — extend the ban's owning statement with what each mechanism covers, the seam's name, and the instruction that new buffer indexing goes in `parser/lookahead.py`. Preserve the literal string 'fixed offset' (required by `tests/test_agent_contract.py:62`). Phase 5."
    },
    {
      "path": "src/ootp_ai/parser/primitives.py",
      "change": "Lines 12-13 — 'the AST guard over `src/ootp_ai/` run[s] with zero exemptions' becomes false. Rewrite to: the cursor still cannot seek, and the guard now confines buffer indexing to one reviewed module. Do not touch the class. Phase 5."
    },
    {
      "path": "docs/data-access.md",
      "change": "Lines 228-230, the 'must never seek to a fixed offset' blockquote in §Record structure. Keep the format claim and its `verified` label unchanged; append a line naming where enforcement actually lives so a reader does not infer total mechanical coverage. Phase 5."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "Line 51 — set the `fixed-offset-guard-cannot-see-subscripts` Index row Stage cell to `fixed` and record the disposition: the guard was widened AND the docs narrowed, because coverage is real but partial. Phase 5 (also handled by `/commit`)."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/IMPLEMENTATION_PLAN.md",
      "change": "NEW — this plan. Opens at `planned · created 2026-08-18 · decided · next: implement`."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/IMPLEMENTATION_REPORT.md",
      "change": "NEW at Phase 5. Must carry the verbatim output of the seen-to-fail mutation from Phase 3 and the before/after byte-accounting numbers from Phase 2."
    }
  ],
  "code_references": [
    {
      "ref": "tests/test_no_fixed_offsets.py:29-62 (`FixedOffsetVisitor`)",
      "claim": "Defines `_nonzero_literal` (36) and `visit_Call` (43) and nothing else. Confirmed by reading: there is no `visit_Subscript`, no `visit_FunctionDef`, so `generic_visit` (62) walks past every subscript. This is the proximate cause exactly as the RCA states it."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:115-127",
      "claim": "The committed red reproduction `test_the_scanner_flags_a_record_relative_subscript`. I ran `uv run pytest tests/test_no_fixed_offsets.py`: 4 passed, 1 failed, `AssertionError: a record-relative read at a constant offset passed the guard because it was written as a subscript rather than a call / assert []`. RED confirmed on the branch tip."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:26 (`SCAN_ROOT`)",
      "claim": "`SCAN_ROOT = REPO_ROOT / /"src/" / /"ootp_ai/"` — the real scan (143-155) covers `src/` only, not `tests/`. This is why `tests/test_sequential_walk.py`'s deliberate negative control is not flagged, and why the allowlist must be keyed on posix paths under `src/ootp_ai/`."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:149",
      "claim": "The real scan already passes `path.relative_to(REPO_ROOT).as_posix()` as `scan_source`'s filename, so a path-keyed allowlist needs no new plumbing and the synthetic fixtures (filenames like `/"subscript.py/"`) can never be accidentally exempt."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:12-13",
      "claim": "/"That is also what lets the AST guard over `src/ootp_ai/` run with zero exemptions: there is no legitimate seek anywhere for it to have to allow./" Verified verbatim. This sentence becomes false the moment `lookahead.py` is allowlisted, and Phase 5 must rewrite it."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:96-104",
      "claim": "`position` is a read-only property with the docstring 'Read-only on purpose: there is no setter'. The RCA's concession that the Cursor half of the third option is true is correct — confirmed by reading the class body: no `seek`, no position setter, `_advance` (115) is the single mutation point."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:553 and :557",
      "claim": "`birth = _peek_date(data, position + _BIRTH_DATE_LOOKAHEAD)` and `stated_age = _peek_u8(data, position + _AGE_LOOKAHEAD)` inside `_looks_like_record` (540). Both are `ast.Call` nodes, NOT subscripts — so neither `visit_Subscript` nor a module-scoping rule catches them. The RCA's line 'Module-scoped … is the one that would have caught this' holds for the repro's shape and not for these two."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:219-220",
      "claim": "`_BIRTH_DATE_LOOKAHEAD = 12` and `_AGE_LOOKAHEAD = 19`. CORRECTION: the RCA cites these at `players.py:199-200`; they are at 219-220. Lines 199-203 hold `_PREAMBLE_CONSTANT` and `_DIGEST_LENGTH`. Stale citation, corrected here."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:451-456 and :244-247, :262, :264",
      "claim": "The head layout that makes Phase 4's arithmetic checkable: `cursor.u32()` (id, 4) + two `cursor.u32()` (name indices, 8) = 12, the birth-date offset; + `cursor.date()` (4) + `_GAP_AFTER_BIRTH_DATE = 3` (244) = 19, the age offset. Summing every subsequent width and gap through `_UNCLASSIFIED_BEFORE_MASKS = 4` (262) gives 55, which matches the comment at 264 ('The assignment presence mask, at record+55') exactly. The arithmetic closes."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:572-592",
      "claim": "`_peek_u8` (572), `_peek_u32` (577) and `_peek_date` (584) — the three helpers Phase 1 extracts. `_peek_u32` here carries a `position < 0` guard that `teams.py:596-605` and `world.py:874-883` do not; the shared version must keep the strictest form."
    },
    {
      "ref": "src/ootp_ai/parser/teams.py:596-605",
      "claim": "The second `_peek_u32`, with the docstring at 599: 'A lookahead at the cursor's *own* position, never at a constant.' The prose rule the RCA says is written three times and enforced nowhere — confirmed verbatim."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:874-883",
      "claim": "The third `_peek_u32`, docstring at 877: 'A lookahead at a position computed from the data … never at a constant.' Byte-for-byte the same body as teams.py's. Three copies confirmed."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:743",
      "claim": "`date_at = offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH`, with the widths defined at 202-204 (4, 4, 2). The RCA's 'model to copy' — confirmed, and it is the form Phase 4 applies to players.py's two constants."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:744-750",
      "claim": "The date decode the RCA's survey calls benign. CORRECTION: the intake table cites this shape at `players.py:481-482`; players.py:481-482 is actually `age=age, nation_id=nation_id` inside the `PlayerRecord` construction. The real date decode in players.py is at 588-590, inside `_peek_date`. Second stale citation, corrected."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:749",
      "claim": "`if year != 0 and not _MIN_YEAR <= year <= _MAX_YEAR: return None` — an absent date (year 0) is deliberately admitted here, per the docstring at 728-732. `players.py`'s `_peek_date` (584-592) rejects it, because `SaveDate.as_date()` (primitives.py:58-67) returns `None` for 0/0/0. A naive `peek_date` substitution in `_scan_event` would break the calendar walk."
    },
    {
      "ref": "src/ootp_ai/parser/teams.py:624",
      "claim": "`park_id, league_id = run[base], run[base + 1]` where `run: tuple[int, ...]`. A subscript with a nonzero int-literal addend on a non-buffer object — the concrete evidence that the RCA's 'Minimal' tier, or any literal-addend syntax rule, cries wolf on code that is already in the tree."
    },
    {
      "ref": "src/ootp_ai/snapshot.py:227,239,242-244",
      "claim": "`payload[/"manifest_version/"]`, `payload[/"files/"]`, `payload[/"save_id/"]`, `payload[/"sim_date/"]`, `payload[/"ingest_seq/"]` — a JSON dict, not a buffer. Why the detection rule must be annotation-grounded rather than keyed on the variable name `payload`."
    },
    {
      "ref": "src/ootp_ai/parser/header.py:103-114 (`looks_like_save_file`)",
      "claim": "`return data[0] == LEADING_NULL and data[1:_MAGIC_PREFIX_LEN] == MAGIC` on a `data: bytes` parameter — a literal-offset subscript that the new rule WILL flag, and that is legitimate (a file-magic check at the file head, not a record-relative read). It moves behind `peek_u8`/`peek_bytes` so no exemption is needed. Covered by `tests/test_parse_world.py:344` and `tests/test_parse_teams_synthetic.py:227`."
    },
    {
      "ref": "src/ootp_ai/parser/human_managers.py:244,248",
      "claim": "`int.from_bytes(data[offset : offset + 4], /"little/")` and `int.from_bytes(data[offset + 4 * slot : offset + 4 * slot + 4], /"little/")` inside `_is_club_landmark` — computed widths, benign, but they read past the buffer end as a short slice rather than refusing. `peek_u32` returns `None` there, which changes the branch structure of a function feeding the exactly-one-match refusal at 231-238."
    },
    {
      "ref": "tests/test_agent_contract.py:62",
      "claim": "`/"never seek to a fixed offset/": /"fixed offset/"` in the `required` dict of `test_rulebook_invariants_survive`. Phase 5's rewrite of `.claude/agents/data-engineer.md:69-74` must keep the literal lower-cased substring 'fixed offset' or this test goes red."
    },
    {
      "ref": "tests/test_agent_contract.py:76-81",
      "claim": "`test_deny_set_still_protects_the_guards` asserts `tests/`, `.github/`, `ops/`, `CLAUDE.md` and `docs/decisions/` all appear in the agent's write-allowlist deny set, with the rationale 'An agent that can edit the tests that catch it is the core failure mode.' This is why Phases 3 and 5 are main-thread work."
    },
    {
      "ref": "tests/test_sequential_walk.py:44-58 and :145-153",
      "claim": "`read_at_fixed_offsets` is a deliberate negative control indexing `data[20 : 20 + name_len]`, and `test_the_cursor_exposes_no_way_to_seek` already names `test_no_fixed_offsets.py` as the guard that must not be satisfiable while the hazard walks in another door. Both are the reason `SCAN_ROOT` must stay at `src/` — widening it to `tests/` would flag AC2's own control."
    },
    {
      "ref": ".github/workflows/ci.yml:46,49,52,57",
      "claim": "CI's four gates: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -m /"not gamedata/"`. The format check is separate from the lint check, and the gamedata exclusion means the export-comparison regression evidence for Phase 2 exists only locally."
    },
    {
      "ref": "pyproject.toml:91-95",
      "claim": "`[tool.mypy] strict = true`, `files = [/"src/", /"tests/"]`. The new visitor handlers in `tests/test_no_fixed_offsets.py` and the new `tests/test_lookahead.py` need complete annotations, not just the `src/` code."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:1-21",
      "claim": "The house precedent from the previous guard bugfix: a second module owning the guard's SCOPE separately from its patterns, because 'a bad pattern produces a false negative on a file the guard read, while a bad scope produces a false negative on a file the guard never opened.' Phase 3's allowlist tests follow this shape."
    },
    {
      "ref": "requests/bugfix-requests/README.md:24,45,51",
      "claim": "The acceptance contract ('the red reproduction goes green and a regression test is left behind'), the status grammar (`intake` → `diagnosed` → `planned` → `fixed`), and the Index row Phase 5 advances."
    }
  ],
  "open_questions": [
    "DOES THIS WARRANT AN ADR? The change settles a rule every future parser change passes through and creates a module carrying a standing exemption. That is the bar `CLAUDE.md` sets for `docs/decisions/`. Recommend raising it with the operator at Phase 5 rather than deciding it inside the implementation — `docs/decisions/` is in the data-engineer subagent's deny set (`tests/test_agent_contract.py:80`), so it is main-thread work either way. My inclination: yes, a short ADR, because the allowlist is the first exemption the parser has ever carried and a future agent will want to know why.",
    "THE FIXTURE-ANNOTATION QUESTION IN PHASE 3, step 5. `SUBSCRIPT_OFFENDER` (tests/test_no_fixed_offsets.py:96-99) declares `def read_team_id(data, record_start)` with no annotation, so a purely annotation-grounded rule does not fire on it and the repro would go green only by accident of the bare-name fallback. The plan prescribes doing BOTH (annotate the fixture AND keep a narrow `{data, buf, buffer}` fallback, each proved by its own fixture). If the implementer would rather ship one mechanism, that is a real narrowing of coverage and should come back to the operator, not be decided silently.",
    "SHOULD `lookahead.py` BE A SEPARATE MODULE OR PART OF `primitives.py`? Recommend separate, and the plan assumes it. `primitives.py`'s entire docstring claim (lines 1-19) is that it exposes no absolute read; putting absolute reads in the same file makes that claim locally false and gives the allowlist two entries where one would do. But it is a judgment call and reversing it is cheap before Phase 2 starts, expensive after.",
    "HOW FAR SHOULD PHASE 2 BE SPLIT? Nineteen sites in five modules is a large single commit for a repo whose convention is vertical slices. Splitting by module (players / teams / world / human_managers+header) gives four gates instead of one and four smaller reverts. The plan's acceptance criteria hold unchanged per slice. Operator's call on appetite.",
    "DOES `world.py`'s `_scan_event` DATE DECODE MOVE AT ALL? It admits year 0 (line 749) where `players.py`'s `_peek_date` refuses it. Either give `lookahead` a `peek_raw_date` returning three unjudged integers, or leave `_scan_event` reading via `peek_u8`/`peek_u32` and accept that its date assembly stays local. The second is smaller and honest; the first is tidier. Not decided here because it changes the seam's API surface.",
    "IS THE RENAME HOLE ACCEPTABLE? An unannotated `def f(b): return b[start + 58]` defeats the scan. The plan documents it rather than chasing it, on the grounds that dataflow analysis inside a test module is a worse liability than the residual and that mypy strict makes dropped annotations loud. If the operator wants it closed, the next-cheapest step is to also flag any subscript on ANY name inside a module that imports `lookahead` — cheap, but it needs measuring against the tree first, and `teams.py:624` says that class of rule cries wolf.",
    "SHOULD THE GUARD EVENTUALLY SCAN `tests/`? Today it cannot, because `tests/test_sequential_walk.py:44-58` is a deliberate fixed-offset negative control. If a future phase wants coverage there, the control needs its own narrow exemption — which is the shape this design is refusing. Left open, recommended against."
  ]
}
```


## Planner 2

```json
{
  "planner": "sequencing",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. CONSUME it, do not re-open it. Verdict `:5-14`, red repro `:16-42`, the cause (`visit_Call` and nothing else) `:46-53`, the two-read-paths measurement table `:55-64`, the refuted third option `:90-111`, the tiered fix posture `:113-147`. The Root tier at `:124-139` is what this plan builds; the Hardening tier at `:141-147` is Phase 4."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/BUGFIX_REQUEST.md",
      "why": "Context only. Its `:97-106` survey table classifies EVERY current direct-buffer site as benign/guard-relevant — that table is the false-positive budget the new rule must respect. Note its `:93-95` line-number correction (the module grew; `:445/:449` are now `:553/:557`)."
    },
    {
      "path": "tests/test_no_fixed_offsets.py",
      "why": "156 lines, read in full — it is the file being fixed AND the file that holds the red repro. Docstring `:1-18` (carries the now-false 'zero exemptions' claim and the load-bearing 'a loosened guard is worse than none' at `:9-10`), `FixedOffsetVisitor` `:29-62` (`visit_Call` at `:43` is the whole mechanism), `scan_source` `:65-68`, fixtures `:73-99`, the RED test `:115-127`, the real tree scan `:143-155`."
    },
    {
      "path": "src/ootp_ai/parser/primitives.py",
      "why": "The OTHER read path, and the reason the RCA refused the docs-only fix. `Cursor` exposes no seek, no position setter, no absolute read (`:91-104`). Its docstring `:11-13` asserts the AST guard runs 'with zero exemptions' — a claim Phase 3 or Phase 6 must make true or correct. `:140` is a names-only slice inside the cursor that the new rule must NOT fire on."
    },
    {
      "path": "src/ootp_ai/parser/players.py",
      "why": "Where the guard-relevant case lives. `_BIRTH_DATE_LOOKAHEAD = 12` / `_AGE_LOOKAHEAD = 19` at `:219-220` with their justification `:216-218`; used at `:553` and `:557` inside `_looks_like_record` `:540-561`; the three peek helpers `_peek_u8` `:572-574`, `_peek_u32` `:577-581`, `_peek_date` `:584-592`; the head read order `_read_record` `:444-490` and `_GAP_AFTER_BIRTH_DATE = 3` at `:244` — together these are the exact derivation Phase 4 needs."
    },
    {
      "path": "src/ootp_ai/parser/world.py",
      "why": "Holds the model to copy AND two sites to move. `:743` is the only constant-derived, self-documenting form in the parser (`offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH`); `:744-746` duplicates players.py's raw date decode; `_scan_string` `:859-871` duplicates teams.py's; `_peek_u32` `:874-883` is the third copy."
    },
    {
      "path": "src/ootp_ai/parser/teams.py",
      "why": "The second `_peek_u32` `:596-605` (its docstring `:599-601` states the rule in prose — one of the three assertions the RCA cites), `_scan_string` `:581-593`, and the flag-run compare `:522` (`data[position : position + 1] == _FLAG_BYTE`, a literal-1 subscript that must survive the refactor byte-identically)."
    },
    {
      "path": "src/ootp_ai/parser/human_managers.py",
      "why": "`_pad_width` `:196-211` (names-only index — must stay legal) and `_is_club_landmark` `:242-250` (bare literal 4 twice — becomes `peek_u32`). These are the RCA's 'both widths are computed' benign cases."
    },
    {
      "path": "src/ootp_ai/parser/header.py",
      "why": "`looks_like_save_file` `:103-114` reads the file magic at absolute file offsets 0 and 1. This is the ONE legitimate absolute read in the tree and it decides whether the repo can keep saying 'zero exemptions'. See Open Question 1."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "why": "The single owner of the build rules. The fixed-offset bullet is `:69-74` ('a blocker, not a style note'); `:284` repeats it in the spec-conflict policy. Phase 6 edits `:69-74` only. Note its Write allowlist DENIES `tests/` — the write-capable subagent cannot build most of this; the main thread does."
    },
    {
      "path": "tests/test_agent_contract.py",
      "why": "`test_rulebook_invariants_survive` `:53-73` requires the literal substring 'fixed offset' to remain in the rulebook — a Phase 6 rewrite that drops the phrase turns CI red. `:76-81` pins the deny set."
    },
    {
      "path": "docs/data-access.md",
      "why": "Read the per-claim epistemic labels before trusting anything. `:251-282` — 'The record head is fixed for 37 bytes' is `verified` against 18,072 of 18,072 export rows, which is why Phase 4 needs no new byte measurement; `:284-287` is the drop-zero region and the 86.9% figure the repro encodes."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "why": "The track contract. Definition of done `:24-26` ('the red reproduction goes green and a regression test is left behind'), status grammar `:45`, and the Index row this work advances at `:51`."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "The gates, in order: `:46` ruff check, `:49` ruff format --check, `:52` mypy, `:57` `pytest -m /"not gamedata/"`. That last flag is the plan's single biggest risk: CI CANNOT prove the Phase 2 refactor, because every real-save test is excluded."
    }
  ],
  "architecture_notes": "THE SHAPE OF THE PROBLEM/n/nThe parser has exactly two ways to touch a save buffer./n/n1. The CONSUMING path — `Cursor` (`src/ootp_ai/parser/primitives.py:73-178`). Structurally safe: no `seek`, no `position` setter (`:91-104`), no absolute read. A walk conducted through it cannot seek, by construction./n2. The SEARCH path — some two dozen module-private helpers that take `(data: bytes, position: int)` and index the buffer directly: `_peek_u32`, `_peek_u8`, `_peek_date`, `_scan_string`, `_scan_shape`, `_looks_like_record`, `_pad_width`, `_is_club_landmark`, `_find_*`. Nothing structural constrains this path at all./n/n`tests/test_no_fixed_offsets.py` is supposed to be the backstop over both, and it defines `visit_Call` and nothing else (`:43-62`). A subscript is an `ast.Subscript`, not an `ast.Call`, so `generic_visit` walks past it — the whole search path is invisible to the guard./n/nWHAT ACTUALLY INDEXES A BUFFER TODAY (measured 2026-08-18 by grep over `src/ootp_ai/`, 26 lines, 6 modules)/n/n- `world.py:740,744,745,746,759,868,883`/n- `players.py:424,529,574,581,588,589,590`/n- `teams.py:522,590,605`/n- `human_managers.py:204,244,248`/n- `header.py:114`/n- `primitives.py:140` (inside `Cursor.take` — names only)/n- plus three `bytes.find` landmark searches (`world.py:841,849`, `players.py:524`, `teams.py:366`) which are searches, not indexed reads/n/nThe surface is SMALL. That is the plan's central bet: the RCA's /"module-scoped is the strongest rule and the largest diff/" is largest only in principle — after the duplicate helpers collapse, the residue is under ten lines./n/nTHE DUPLICATION THE SEAM ALREADY WANTS/n/nThree byte-identical `_peek_u32` implementations (`teams.py:596-605`, `players.py:577-581`, `world.py:874-883`), two near-identical `_scan_string` (`teams.py:581-593` returns `(length, end)`; `world.py:859-871` returns `end`), and two copies of the same raw date decode (`players.py:588-590`, `world.py:744-746`). Extracting them is not new architecture — it is deleting three copies of one function./n/nWHERE THE CHANGE HOOKS IN/n/nA new `src/ootp_ai/parser/lookahead.py` becomes the ONLY sanctioned place to index a save buffer. `parser/__init__.py` is a docstring and a `__future__` import (14 lines) and re-exports nothing, so nothing needs registering there. The guard then keys on MODULE rather than on syntax: inside `lookahead.py` an integer literal in an index is expected; anywhere else in `src/ootp_ai/` it is a fixed-offset read./n/nTHE RULE, IN TWO INCREMENTS (this is why there are two guard phases, not one)/n/n- Increment A (Phase 3) — SUBSCRIPT rule. Flag `buffer[... <nonzero int literal> ...]` outside `lookahead.py`. Catches the red repro. Does NOT catch `players.py:553`, because that is a Call whose offset is a Name./n- Increment B (Phase 5) — POSITION-ARGUMENT rule with module-constant folding. A Name bound at module level to a bare int counts as a literal when it appears in a position expression, UNLESS it follows the declared-span convention the parser already uses: a name ending `_WIDTH` or beginning `_GAP_`. Grounded in `world.py:743` (`_SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH`), `world.py:746` (`_DATE_WIDTH`), `world.py:755` (`_LENGTH_PREFIX_WIDTH`), `players.py:244-247` (`_GAP_AFTER_*`). This is the increment that would have caught `players.py:553` — and it is why Phase 4 (re-expressing `_BIRTH_DATE_LOOKAHEAD`/`_AGE_LOOKAHEAD` as width sums) must land FIRST, or the tree is red at its own checkpoint./n/nRejected: Literal-vs-Name alone (RCA `:135-136` — too weak, misses `players.py:553`). Rejected: name-based allowlist alone (RCA `:132-134` — an author can name anything `_peek_`). Rejected: shipping the Minimal tier by itself (RCA `:115-122` — fires on five modules)./n/nWHAT THE GUARD MUST TREAT AS THE BUFFER/n/nDo NOT hardcode `{/"data/", /"buf/"}`. Derive the buffer set per-function from the AST: a parameter annotated `bytes`. Every search helper in the tree matches (`data: bytes` in `players.py:513`, `:540`, `:572`, `:577`, `:584`; same in `teams.py`, `world.py`, `human_managers.py`, `header.py:103`). A future walker that names its buffer `raw` is then still covered./n/nNOT IN SCOPE, EXPLICITLY/n/nNo save is read or written by any of this — the whole change is a test module, one new pure-function parser module, and mechanical rewiring. No dbt model, no dataset, no `.env` path, no `datasets/manifest.json`. `docs/data-access.md` carries no claim this invalidates (its 37-byte fixed-head claim at `:275-279` is `verified` and Phase 4 preserves the measured values 12 and 19 by pinning them in a test).",
  "phases": [
    {
      "name": "Phase 1 — Census: pin what actually indexes a save buffer",
      "goal": "Turn the RCA's measured inventory into a CI-checked fact BEFORE designing a rule on top of it. Highest-uncertainty item first: the new rule's whole viability is 'does it have zero false positives on the real tree', and that question cannot be answered without an exact, machine-derived inventory. No behaviour changes; no parser file is touched.",
      "steps": [
        "In `tests/test_no_fixed_offsets.py`, add a second AST pass alongside `FixedOffsetVisitor` (`:29`): `BufferIndexVisitor`, which records every `ast.Subscript` whose `value` is a `Name` that is a parameter of the enclosing `FunctionDef` annotated `bytes`. Derive the buffer names from the annotation, NOT from a hardcoded name list — see the architecture note. Record `(module_relpath, enclosing_function, shape)`.",
        "Classify each site's `shape` as one of: `names-only` (every element of the index is a Name or an attribute), `literal` (an inline nonzero int literal appears anywhere in the index or in either bound of an `ast.Slice`), or `folded` (a Name that a module-level `NAME = <int literal>` assignment binds to a bare nonzero int).",
        "Add `test_the_buffer_index_inventory_is_the_known_set`: assert the `(module, function)` pairs equal a pinned `frozenset` in the test module, with a docstring dated 2026-08-18 and labelled `measured`. Key on `(module, function)`, never on line number — line numbers move on every edit and a brittle pin is a guard that gets deleted.",
        "Derive the pinned set by running the census, not by copying this plan. As of 2026-08-18 the sites live in `world.py` (`_read_event`, `_scan_string`, `_peek_u32`), `players.py` (`_read_padding`-style zero scans around `:424`/`:529`, `_peek_u8`, `_peek_u32`, `_peek_date`), `teams.py` (the flag-run loop at `:522`, `_scan_string`, `_peek_u32`), `human_managers.py` (`_pad_width`, `_is_club_landmark`), `header.py` (`looks_like_save_file`) and `primitives.py` (`Cursor.take`). Confirm each by running the census and fix any divergence in the pin, not in this list.",
        "Add `test_the_census_counts_agree_with_the_diagnosis`: assert the per-module count of buffer-indexing FUNCTIONS, and record in the docstring that the RCA's table (`ROOT_CAUSE_ANALYSIS.md:55-64`) counted reads-per-module while this counts indexed-subscript sites, so the two numbers differ by construction. An unexplained divergence between a diagnosis and a guard is how the guard loses its authority.",
        "Do not add a pytest marker. `pyproject.toml:100` carries `--strict-markers` and `:101-107` says widen the one `gamedata` marker, never add a second — an invented marker is a hard COLLECTION error that presents as a broken repo."
      ],
      "acceptance": [
        "`uv run pytest tests/test_no_fixed_offsets.py` — the four pre-existing green tests stay green, the two new census tests pass, and `test_the_scanner_flags_a_record_relative_subscript` (`:115-127`) is STILL RED. Phase 1 deliberately does not fix the bug.",
        "Seen-to-fail check (run by hand, then revert — do not commit the mutant): add `x = data[position + 7]` to any function in `src/ootp_ai/parser/world.py` that already takes `data: bytes`; if that function is already in the pinned set the inventory stays green, so instead add a NEW function `def _mutant(data: bytes, position: int) -> int: return data[position + 7]` — the inventory test must go red naming `world._mutant`.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all green.",
        "The pinned set is written as a literal `frozenset` in the test module — greppable, reviewable in a diff, and not computed from the tree it is meant to constrain."
      ],
      "commit_note": "Hand to `/commit`. Suggested message: /"Pin what actually indexes a save buffer, before widening the ban/". Reversible in full — this phase adds tests only and touches nothing under `src/`."
    },
    {
      "name": "Phase 2 — Extract parser/lookahead.py, the one sanctioned home for buffer indexing",
      "goal": "Give buffer lookahead a single legitimate home (RCA Root tier, `:124-131`) and collapse three copies of `_peek_u32`, two copies of `_scan_string` and two copies of the raw date decode. Behaviour-preserving refactor: after this phase the residue of buffer-indexing outside the new module is names-only arithmetic plus one absolute magic read.",
      "steps": [
        "Create `src/ootp_ai/parser/lookahead.py`. Module docstring must state, in this order: this is the ONLY sanctioned place in `src/ootp_ai/` to index a save buffer; every function takes `(data: bytes, position: int)` and returns `None` past the end rather than raising; a lookahead is not a seek because `position` is always supplied by a walk that computed it from bytes it already read; and the AST guard keys on this module by path.",
        "Implement, all pure and fully annotated for `mypy --strict`: `peek_u8(data, position) -> int | None`; `peek_u32(data, position) -> int | None`; `peek_bytes(data, position, count) -> bytes | None`; `peek_date_fields(data, position) -> tuple[int, int, int] | None` returning RAW `(day, month, year)` with NO validation; `peek_length_prefixed(data, position, limit) -> tuple[int, int] | None` returning `(length, end)` for a u32-LE length-prefixed run.",
        "CRITICAL — `peek_date_fields` must NOT validate. `players.py:584-592` rejects a non-date by returning `None`; `world.py:744-750` keeps the raw fields and range-checks day/month/year itself, explicitly allowing `year == 0`. A shared validating `peek_date` would silently change `world._read_event`'s accept set. Keep the raw primitive shared and leave each caller's validation where it is: `players._peek_date` becomes a four-line wrapper over `peek_date_fields` that still returns `SaveDate | None`.",
        "Rewire, deleting the old bodies: `teams.py:596-605`, `world.py:874-883`, `players.py:577-581` (all three `_peek_u32`) and `players.py:572-574` (`_peek_u8`) → import from `lookahead`. Preserve each deleted docstring's rule statement by folding it into `lookahead.py`'s docstring — three modules assert that rule in prose (`teams.py:599-601`, `world.py:877-879`, `players.py:578`) and the prose must not be lost, only relocated.",
        "Rewrite `teams._scan_string` (`:581-593`) and `world._scan_string` (`:859-871`) over `peek_length_prefixed`. Keep their DIFFERENT return types (`teams` returns `(length, end)`, `world` returns `end`) and keep the printability filter in each caller — it is what stops them firing on integer data and its rationale is in each docstring.",
        "Rewrite `world.py:744-746` as `peek_date_fields(data, date_at)`, keeping the `_MAX_DAY`/`_MAX_MONTH`/`_MIN_YEAR`/`_MAX_YEAR` checks at `:747-750` byte-for-byte.",
        "Rewrite `human_managers._is_club_landmark` (`:242-250`) over `peek_u32`. Introduce `_U32_WIDTH = 4` locally rather than inlining `4 * slot`; the slot arithmetic then reads `offset + slot * _U32_WIDTH`.",
        "Rewrite `teams.py:522` as `peek_bytes(data, position, _FLAG_WIDTH) == _FLAG_BYTE` with `_FLAG_WIDTH = 1`. Keep the comparison against the same `_FLAG_BYTE` bytes object — do not convert it to an int comparison, which would change what a short buffer at the end of the file compares as.",
        "Leave `header.looks_like_save_file` (`:112-114`) ALONE in this phase. It is the one absolute read and its disposition is Open Question 1, decided before Phase 3.",
        "Do NOT move `_looks_like_record` out of `players.py`. `tests/test_parse_players.py:36-48` imports it by name, with a comment explaining that re-implementing the rule in the test would test a copy of it. Moving it breaks that import."
      ],
      "acceptance": [
        "`uv run pytest` — full offline suite green, with no test edited to accommodate the refactor except the Phase 1 census pin (which is updated in this same commit and must now show the peek helpers living in `lookahead`).",
        "`uv run pytest -m gamedata` GREEN on all three local saves. This is the ONLY proof the walk is unchanged: `.github/workflows/ci.yml:57` runs `-m /"not gamedata/"`, so CI cannot see this. If the saves are not available on this machine, DO NOT COMMIT this phase — hand it back to the operator.",
        "Specifically: `uv run pytest tests/test_parse_players.py -m gamedata`, `tests/test_parse_real_save.py`, `tests/test_parse_world.py`, `tests/test_byte_accounting.py` all green, and `tests/test_parse_teams_synthetic.py`, `tests/test_sequential_walk.py` green offline.",
        "`grep -c /"_peek_u32/" src/ootp_ai/parser/` shows exactly one definition, in `lookahead.py`.",
        "`uv run mypy` strict green — the new module is a public seam and must be fully typed.",
        "The Phase 1 census test still passes with its pin updated, and the update is a SHRINKING of the out-of-module set. If the set grew, the refactor went the wrong way."
      ],
      "commit_note": "Hand to `/commit`. Suggested message: /"Give buffer lookahead one home, and delete the three copies of it/". Reversible: pure refactor, no rule change yet, the guard is unchanged and the repro is still red."
    },
    {
      "name": "Phase 3 — The subscript rule, and the exemption registry that must be seen to fail",
      "goal": "Turn the RCA's red repro GREEN — the acceptance contract of the bugfix track (`requests/bugfix-requests/README.md:24-26`) — without crying wolf on any of the surviving benign sites.",
      "steps": [
        "Add `visit_Subscript` to `FixedOffsetVisitor` (`tests/test_no_fixed_offsets.py:29-62`). Flag when the subscripted value is a `bytes`-annotated parameter of the enclosing function AND a nonzero int `Constant` appears anywhere in the index — including in either bound or the step of an `ast.Slice`. Reuse `_nonzero_literal` (`:36-41`); its bool exclusion at `:39` matters (`True` is an `int` in Python).",
        "Scope by module. `scan_source` (`:65`) already receives a filename and the real scan builds a repo-relative POSIX path at `:149`; add `SANCTIONED_LOOKAHEAD = /"src/ootp_ai/parser/lookahead.py/"` and skip the subscript rule for that path only. Assert in the docstring that the exemption is by PATH, so renaming the module does not silently widen the ban.",
        "Add `EXEMPT_SITES`: an explicit `dict[tuple[str, str], str]` mapping `(relpath, function_name)` to a written reason. Populate it per Open Question 1's disposition — either zero entries (if `header.looks_like_save_file` was rewritten over `peek_bytes`) or exactly one, `(/"src/ootp_ai/parser/header.py/", /"looks_like_save_file/")`, reason: the OOTP record-file magic sits at absolute file offsets 0-3, which is a file-start classification and not a record-relative read (`header.py:103-114`).",
        "Add these tests, each of which fails for a different reason: `test_the_scanner_allows_a_name_only_index` (feed it `world.py:740`'s exact shape, `data[pad_at:length_at]`); `test_the_scanner_allows_the_sanctioned_lookahead_module` (feed `SUBSCRIPT_OFFENDER` with filename `src/ootp_ai/parser/lookahead.py` and assert `[]`); `test_every_exempt_site_still_exists` (each `EXEMPT_SITES` key resolves to a real file containing a function of that name, so a stale exemption fails loudly rather than quietly widening the guard); `test_the_exemption_registry_is_small` pinning `len(EXEMPT_SITES)` to its exact value, so any future loosening shows up as a diff on a number.",
        "Rewrite the module docstring `:1-18`. The 'zero exemptions' framing must go — replace it with what the guard now covers (both spellings, both read paths, one named module, N named sites) and keep the `:9-10` warning about a guard that cries wolf, because it is the reason for every design choice above.",
        "Update `SUBSCRIPT_OFFENDER`'s comment block (`:90-95`) from 'the spelling this parser's style makes likeliest and the guard cannot see' to past tense, and keep the 86.9% measurement — it is the evidence for why the rule exists."
      ],
      "acceptance": [
        "`uv run pytest tests/test_no_fixed_offsets.py` — FULLY green, including `test_the_scanner_flags_a_record_relative_subscript` (`:115-127`), which fails today at `:124` with `assert []`. This is the bug's acceptance contract, satisfied here.",
        "`uv run pytest tests/test_no_fixed_offsets.py::test_no_parser_module_seeks_to_a_fixed_offset` green over the whole real tree — ZERO false positives. If it fires on a benign site the rule is wrong, not the site; do not add an exemption to make it pass.",
        "Seen-to-fail check (run by hand, revert, do not commit): paste `SUBSCRIPT_OFFENDER`'s body as a function into `src/ootp_ai/parser/players.py`; the real scan must go red naming `src/ootp_ai/parser/players.py:<line>`.",
        "Exemption is load-bearing: delete the `EXEMPT_SITES` entry (if any) and the real scan goes red; restore it. An exemption that changes nothing is decoration.",
        "`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` green.",
        "`uv run pytest` full offline suite green — nothing else regressed."
      ],
      "commit_note": "Hand to `/commit`. Suggested message: /"Teach the fixed-offset guard to read a subscript/". This is the phase that closes the bug; the remaining phases close the class."
    },
    {
      "name": "Phase 4 — Re-express the two record-relative constants as sums of named field widths",
      "goal": "Remove the last raw record-relative offsets from the parser (RCA Hardening tier, `:141-147`), using the `world.py:743` form — the only shape in the parser that is both constant-derived and self-documenting. Must land BEFORE Phase 5's rule, or Phase 5's own checkpoint is red.",
      "steps": [
        "Derive the sums from `players._read_record` (`:444-456`), which is the authority on the head's field order: `cursor.u32()` player_id, `cursor.u32(), cursor.u32()` name indices, `cursor.date()`, `cursor.skip(_GAP_AFTER_BIRTH_DATE)`, `cursor.u8()` age.",
        "Add width constants to `players.py` beside the existing `_GAP_*` block (`:240-247`): `_U32_WIDTH = 4`, `_DATE_WIDTH = 4`, `_NAME_INDEX_COUNT = 2`. Then rewrite `:219-220` as `_BIRTH_DATE_LOOKAHEAD = _U32_WIDTH + _U32_WIDTH * _NAME_INDEX_COUNT` and `_AGE_LOOKAHEAD = _BIRTH_DATE_LOOKAHEAD + _DATE_WIDTH + _GAP_AFTER_BIRTH_DATE`. These evaluate to 12 and 19, the measured values (`_GAP_AFTER_BIRTH_DATE = 3` at `:244`).",
        "Add `test_the_lookahead_offsets_are_the_measured_ones` to the OFFLINE half of `tests/test_parse_players.py` (before the `:347` gamedata divider): assert `_BIRTH_DATE_LOOKAHEAD == 12` and `_AGE_LOOKAHEAD == 19`, with a docstring saying the SUM is documentation and the NUMBERS are the fact — `verified` against 18,072 of 18,072 export rows (`docs/data-access.md:275-279`). A mis-derived sum must fail here, not in a save nobody re-parses.",
        "Update the comment block at `:216-220`. It currently justifies the constants as validation lookaheads; add that they are now derived from the head's own field widths and that the derivation is only safe because the 37-byte head is `verified` fixed-width — cite the label, not just the claim.",
        "Do NOT touch `_looks_like_record`'s logic (`:540-561`) or the tolerance at `:238`. This phase changes how two numbers are written, nothing about what the walk accepts."
      ],
      "acceptance": [
        "`uv run pytest tests/test_parse_players.py` green offline, including the new pin test.",
        "`uv run pytest -m gamedata` green — these two constants drive the framing check on a 32 MB buffer, so a mis-derivation shows up as a wrong record count, not a crash. `tests/test_parse_players.py::test_the_walk_holds_every_player_the_export_knows_about` and `::test_the_file_holds_five_records_the_export_does_not` are the sharpest two.",
        "Deliberately break one addend (change `_NAME_INDEX_COUNT` to 1) and confirm the new pin test goes red BEFORE any gamedata test does; revert. The offline pin must be the first line of defence.",
        "`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` all green."
      ],
      "commit_note": "Hand to `/commit`. Suggested message: /"Write the two record-relative lookaheads as the widths they are made of/". Independently reversible; the guard is unchanged in this phase."
    },
    {
      "name": "Phase 5 — The position-argument rule: a named constant that is really an offset",
      "goal": "Close the case Phase 3 structurally cannot — `players.py:553` and `:557`, where the offset is a Name, not a literal. This is the increment that makes the ban cover what the RCA called 'the genuinely guard-relevant case'.",
      "steps": [
        "Extend the scanner with a module-level constant table: collect every top-level `NAME = <int Constant>` assignment in the file being scanned (`ast.Module.body` only — not nested scopes, where a local is a computed width).",
        "Add the declared-span convention: a Name is a legal addend if its identifier ends with `_WIDTH` or starts with `_GAP_`. Anything else that folds to a bare nonzero int is an offset. This is not invented — it is the convention already in force at `world.py:743` (`_SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH`), `world.py:746` (`_DATE_WIDTH`), `world.py:755` (`_LENGTH_PREFIX_WIDTH`), and `players.py:244-247` (`_GAP_AFTER_*`).",
        "Apply the rule to POSITION expressions: the second positional argument of any call to a `lookahead.peek_*` function or a module-private `_peek_*` / `_scan_*` / `_find_*` helper, plus the existing `unpack_from` third-arg case at `:54-60`, plus any subscript index caught by Phase 3's visitor.",
        "Add fixtures that make the rule seen-to-fail in both directions: `FOLDED_OFFENDER` — a module defining `_TEAM_ID_OFFSET = 58` and calling `_peek_u32(data, position + _TEAM_ID_OFFSET)`, which must be flagged; and `WIDTH_SUM_INNOCENT` — `world.py:743`'s exact shape with `_SEQ_WIDTH = 4` etc. defined at module level, which must NOT be flagged.",
        "Add `test_the_declared_span_convention_is_stated`: assert the guard's own docstring names both accepted forms (`_WIDTH`, `_GAP_`). The convention must have exactly one written home, and it is the guard, not prose scattered across three modules.",
        "Keep the suffix set NARROW — `_WIDTH` and `_GAP_` only. Do not add `_LEN`, `_SIZE` or `_COUNT` speculatively; widening the allowlist is exactly how a guard gets loosened (`:9-10`)."
      ],
      "acceptance": [
        "`uv run pytest tests/test_no_fixed_offsets.py` fully green, including both new fixtures.",
        "`uv run pytest tests/test_no_fixed_offsets.py::test_no_parser_module_seeks_to_a_fixed_offset` green over the real tree — proving zero false positives on the whole parser AFTER Phase 4's rewrite.",
        "THE PROOF THIS PHASE WORKS: temporarily revert Phase 4 in the working tree (set `_BIRTH_DATE_LOOKAHEAD = 12` back to a bare literal) and confirm the real-tree scan goes RED naming `src/ootp_ai/parser/players.py:553`. Restore Phase 4. If it does not go red, the rule does not do what this phase exists for.",
        "`uv run pytest` full offline suite green; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` green.",
        "Run `uv run pytest -m gamedata` once here too — not because this phase touches the parser (it does not) but because it is the last checkpoint before the docs phase, and a clean gamedata run is what licenses the claims Phase 6 writes down."
      ],
      "commit_note": "Hand to `/commit`. Suggested message: /"Fold module constants, so a named offset is still an offset/". Reversible on its own — reverting leaves Phase 3's subscript rule and Phase 4's width sums intact."
    },
    {
      "name": "Phase 6 — Make every written claim about the ban true",
      "goal": "The RCA's closing position (`:110-111`): the docs get corrected as a CONSEQUENCE of what the guard now covers. Four claims in the tree are currently stronger than the mechanism; after this phase each says exactly what is enforced, by what, over which path.",
      "steps": [
        "`CLAUDE.md:103` — 'The fixed-offset ban is the rulebook's, and CI enforces it.' Now defensible, but say over what: name both read paths (the cursor and the sanctioned lookahead module) in one line. CLAUDE.md is a map, not a spec — do not restate the rule here; the rulebook owns it (`CLAUDE.md:148-157` is explicit that restating a rule in actionable form recreates the second copy single ownership exists to prevent).",
        "`.claude/agents/data-engineer.md:69-74` — add the seam: buffer indexing lives in `src/ootp_ai/parser/lookahead.py`; indexing a save buffer anywhere else is the blocker. The literal substring 'fixed offset' MUST survive — `tests/test_agent_contract.py:53-73` greps for it and a rewrite that drops the phrase turns CI red.",
        "`src/ootp_ai/parser/primitives.py:11-13` — 'That is also what lets the AST guard over `src/ootp_ai/` run with zero exemptions' is false as of Phase 3. Correct it to name the exemption count and where the registry lives, or (if Open Question 1 was disposed toward rewriting the header magic) state that the count is still zero and say what makes that true now.",
        "`tests/test_no_fixed_offsets.py:1-18` — re-read the docstring end to end against the final rule set. It was rewritten in Phase 3 before Phase 5's rule existed; it must now describe both increments.",
        "`docs/data-access.md` — NO EDIT. Checked: its fixed-head claim (`:275-279`) is `verified` and Phase 4 preserved the measured values. Do not invent a change here to look thorough; the file's epistemic labels are load-bearing and an unnecessary edit costs their credibility. (`.claude/agents/data-engineer.md:262-264` denies the subagent writes to it anyway.)",
        "`README.md:22-29` — NO EDIT. It describes the parser's capabilities ('a forward-only cursor, a header and version guard, an immutable snapshot layer') and does not enumerate parser modules, so a new internal module does not touch it. Confirm by reading before deciding.",
        "`requests/bugfix-requests/README.md:51` — set this item's Index row Stage cell to `fixed` and trim the row's note to what actually landed. `/commit`'s doc gate checks the Index rows against the artifacts' status headers, so let it drive the artifact status blockquotes.",
        "Grep the whole tree for surviving overclaims: `zero exemptions`, `CI enforces`, `never inspects a subscript`. Every hit must be either corrected or inside a `requests/` artifact recording history (those are a record of what was believed and must NOT be rewritten)."
      ],
      "acceptance": [
        "`uv run pytest tests/test_agent_contract.py` green — every rulebook invariant still stated (`:53-73`), deny set intact (`:76-81`).",
        "`uv run pytest tests/test_doc_links.py` green — every path cited in the new prose resolves. Note the guard's known sharp edge: a Markdown link whose target carries a `:123` line suffix turns it red, so write every `file:line` citation as an inline code span, never a link.",
        "`grep -rn /"zero exemptions/" .` returns only `requests/` artifacts (history) — no live claim survives.",
        "`uv run pytest` full offline suite green; `uv run pytest -m gamedata` green; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` green.",
        "The four node skill guards still pass (`.github/workflows/ci.yml:70-78`) — untouched by this work, but they are part of the green bar CI enforces.",
        "Read the final guard docstring aloud against the code: someone who reads only the docstring must be able to predict, for each of the six shapes in `BUGFIX_REQUEST.md:100-106`, whether it is flagged. If they cannot, the docstring is not done."
      ],
      "commit_note": "Hand to `/commit`. Suggested message: /"Say what the ban actually enforces, now that it does/". Then the PR is the user's: ask before merging, never push `main`, never force-push."
    }
  ],
  "testing": "HOW THE WHOLE THING IS VERIFIED/n/nThe acceptance contract for this track is fixed (`requests/bugfix-requests/README.md:24-26`): the red reproduction goes green, a regression test is left behind, nothing else regresses. Concretely:/n/n1. THE RED REPRO. `uv run pytest tests/test_no_fixed_offsets.py::test_the_scanner_flags_a_record_relative_subscript`. Confirmed RED on today's tree at commit df17337 (`AssertionError: ... assert []`, at `tests/test_no_fixed_offsets.py:124`; 1 failed, 4 passed). It goes green in Phase 3 and must stay green through Phases 4-6./n/n2. THE REGRESSION TESTS LEFT BEHIND. Six, each failing for a different reason: the census inventory (Phase 1) fails when a NEW function starts indexing a buffer; `test_the_scanner_flags_a_record_relative_subscript` fails when the subscript visitor is removed; `test_the_scanner_does_not_cry_wolf` (`:110-112`) and the new name-only/sanctioned-module tests fail when the rule over-fires; `test_every_exempt_site_still_exists` fails when an exemption goes stale; `test_the_exemption_registry_is_small` fails when someone loosens the guard; `test_the_lookahead_offsets_are_the_measured_ones` (Phase 4) fails when a width sum is mis-derived./n/n3. SEEN-TO-FAIL, NOT ASSUMED. Every phase carries a mutation check run by hand and reverted, never committed. This repo has been bitten twice by guards that were green and blind (`requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/`, `_done/verify-batching-guard-red-on-arrival/` — the latter was RED from the day it landed and nothing noticed for the life of the skill). A new guard that has never been observed to fire is the same failure with a different name./n/nPER-PHASE SELECTORS/n/n- Phase 1: `uv run pytest tests/test_no_fixed_offsets.py -k inventory or census`/n- Phase 2: `uv run pytest` (full offline) THEN `uv run pytest -m gamedata` — specifically `tests/test_parse_players.py`, `tests/test_parse_real_save.py`, `tests/test_parse_world.py`, `tests/test_byte_accounting.py`/n- Phase 3: `uv run pytest tests/test_no_fixed_offsets.py`/n- Phase 4: `uv run pytest tests/test_parse_players.py` then `uv run pytest tests/test_parse_players.py -m gamedata`/n- Phase 5: `uv run pytest tests/test_no_fixed_offsets.py` plus the Phase-4-revert mutation/n- Phase 6: `uv run pytest tests/test_agent_contract.py tests/test_doc_links.py` plus the full bar/n/nTHE GATE AT EVERY CHECKPOINT/n/n`uv run pytest` · `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy` — the same four CI runs, in the same order (`.github/workflows/ci.yml:46-57`). Then hand to `/commit`. Never `git commit` ad hoc; `/commit` stages deliberately, runs the doc gate, and asks before writing./n/nREGRESSION SAFETY, AND THE ONE GAP CI CANNOT COVER/n/n`.github/workflows/ci.yml:57` runs `pytest -m /"not gamedata/"`. Every test that reads a real save is therefore invisible to CI by design (ADR 0006 — the game's data cannot be in the repo). Phase 2 is a refactor of code that only real saves exercise end to end. So:/n/n- Phase 2 MUST NOT be committed without a green local `uv run pytest -m gamedata` against all three saves. If the saves are unavailable on the machine doing the work, stop and hand the phase back to the operator. A green CI on Phase 2 proves almost nothing about Phase 2./n- Phases 1, 3, 5 and 6 are offline-only and CI covers them completely./n- Phase 4 changes two numbers that only matter on a 32 MB buffer; the offline pin test is the first line of defence precisely so a mis-derivation fails before the gamedata run./n/nWHAT /"NOTHING ELSE REGRESSES/" MEANS HERE/n/nThe strongest available evidence that the Phase 2 refactor preserved behaviour is `tests/test_parse_players.py::test_every_landed_field_matches_the_export_exactly` and `::test_the_club_assignment_matches_the_export_on_every_row`, plus `tests/test_parse_real_save.py::test_every_parsed_team_matches_the_export_field_by_field` — field-by-field agreement with the game's own export on the truth save. If those three are green after Phase 2, the search path still finds the same records.",
  "risks": [
    "CI CANNOT SEE THE REFACTOR. `.github/workflows/ci.yml:57` excludes the `gamedata` marker, so a green PR proves nothing about whether Phase 2 broke the walk over a real 32 MB `players.dat`. Mitigation: Phase 2's acceptance requires a local `uv run pytest -m gamedata` on all three saves, and the phase is not committable without it. Do not rationalise a skip because 'it is only a refactor' — the export-agreement tests are the only oracle this project has.",
    "CRYING WOLF IS WORSE THAN THE GAP. The guard's own docstring says so at `tests/test_no_fixed_offsets.py:9-10`, and the RCA refuses the Minimal tier for exactly this (`:115-122`). If Phase 3 or Phase 5 fires on a benign site, the fix is the RULE, not a new exemption. Adding exemptions to make a red scan pass is how this guard dies. `test_the_exemption_registry_is_small` exists to make that visible in a diff.",
    "THE BUFFER-NAME HEURISTIC IS THE WEAK JOINT. If the scanner keys on the identifiers `data`/`buf`, a future walker naming its buffer `raw` or `blob` is invisible again — the same class of bug, one rename away. Mitigation, baked into Phase 1: derive the buffer set from the enclosing function's `bytes` annotation, and let the census inventory fail on any NEW function that indexes one, regardless of what it calls it.",
    "PHASE ORDER IS LOAD-BEARING BETWEEN 4 AND 5. Landing Phase 5's constant-folding rule before Phase 4's width-sum rewrite makes `players.py:553` fire on the real tree, so the phase's own checkpoint is red and the implementer is tempted to weaken the rule to get green. Do not merge or reorder them. Phase 5's acceptance deliberately re-introduces the Phase 4 state as a mutation to PROVE the ordering was necessary.",
    "SHARING `peek_date` WOULD SILENTLY CHANGE WHAT `world._read_event` ACCEPTS. `players.py:584-592` returns `None` for a non-date; `world.py:744-750` keeps the raw fields and explicitly allows `year == 0`. Collapsing them into one validating helper narrows world's accept set with nothing raised — a silent parse change, which is the exact failure class this whole request is about. Phase 2 shares only the RAW `peek_date_fields`.",
    "`tests/test_parse_players.py:36-48` IMPORTS `_looks_like_record` FROM `players.py` BY NAME, with a comment saying re-implementing the rule in the test would test a copy of it. Moving that function into the new lookahead module breaks the import and, worse, invites someone to duplicate the rule in the test. Leave it where it is — `lookahead.py` holds primitives, not framing logic.",
    "SCOPE CREEP INTO THE PARSER. `src/ootp_ai/parser/` is validated field-by-field against the game's export and every line of it carries a reasoned docstring. Phase 2 is mechanical rewiring only: no new validation, no tightened range check, no 'while I was in there'. Every behaviour change in a parser module in this work is a defect until proven otherwise.",
    "DO NOT INVENT A PYTEST MARKER. `pyproject.toml:100` sets `--strict-markers` and `:101-107` warns that an invented marker is a hard COLLECTION error — the whole suite fails to collect and presents as a broken repo rather than a missing marker. Widen `gamedata`, never add a sibling.",
    "THE DOC PHASE CAN BREAK CI TWO WAYS. `tests/test_agent_contract.py:53-73` requires the literal substring 'fixed offset' to survive in the rulebook, and `tests/test_doc_links.py` turns red on a Markdown link whose target carries a `:123` suffix. Write every citation as an inline code span, and re-read the rulebook edit against the required-substring table before committing.",
    "REWRITING HISTORY IN `requests/`. The RCA and the intake record what was BELIEVED at diagnosis time, including the now-obsolete 'never inspects a subscript'. Phase 6's grep sweep must correct live claims only — an artifact edited to match the fix destroys the trail the track exists to keep.",
    "NO PART OF THIS TOUCHES A SAVE, BUT THE HABIT MATTERS. `lookahead.py` must take `bytes` and never a path or a handle, exactly as `parser/__init__.py:8-11` requires of the whole package — that is what keeps every read `/"rb/"` by construction, and a Challenge Mode save's integrity hash is destroyed irreversibly by one write."
  ],
  "files_to_touch": [
    {
      "path": "tests/test_no_fixed_offsets.py",
      "change": "The centre of the work, touched in four phases. P1: add `BufferIndexVisitor` + the pinned census tests. P3: add `visit_Subscript`, `SANCTIONED_LOOKAHEAD`, `EXEMPT_SITES` and four new rule tests; rewrite the `:1-18` docstring off the 'zero exemptions' claim. P5: module-level constant folding, the `_WIDTH`/`_GAP_` declared-span convention, `FOLDED_OFFENDER` and `WIDTH_SUM_INNOCENT` fixtures. P6: final docstring pass. Never weaken `test_the_scanner_flags_a_record_relative_subscript` (`:115-127`) to fit the fix."
    },
    {
      "path": "src/ootp_ai/parser/lookahead.py",
      "change": "NEW (Phase 2). The only sanctioned place in `src/ootp_ai/` to index a save buffer. `peek_u8`, `peek_u32`, `peek_bytes`, `peek_date_fields` (raw, unvalidated), `peek_length_prefixed`. Pure functions over `(data: bytes, position: int)`, `None` past the end, fully annotated for mypy strict. Its docstring absorbs the rule statements currently duplicated in three `_peek_u32` docstrings."
    },
    {
      "path": "src/ootp_ai/parser/players.py",
      "change": "P2: delete `_peek_u8` (`:572-574`) and `_peek_u32` (`:577-581`); reduce `_peek_date` (`:584-592`) to a validating wrapper over `lookahead.peek_date_fields`. P4: add `_U32_WIDTH`/`_DATE_WIDTH`/`_NAME_INDEX_COUNT` beside `:240-247` and rewrite `_BIRTH_DATE_LOOKAHEAD`/`_AGE_LOOKAHEAD` (`:219-220`) as width sums; refresh the `:216-220` comment. Leave `_looks_like_record` (`:540-561`) in this module — a test imports it by name."
    },
    {
      "path": "src/ootp_ai/parser/teams.py",
      "change": "P2: delete `_peek_u32` (`:596-605`); rewrite `_scan_string` (`:581-593`) over `lookahead.peek_length_prefixed`, keeping its `(length, end)` return and its printability filter; rewrite the flag-run compare at `:522` as `peek_bytes(data, position, _FLAG_WIDTH) == _FLAG_BYTE`."
    },
    {
      "path": "src/ootp_ai/parser/world.py",
      "change": "P2: delete `_peek_u32` (`:874-883`); rewrite `_scan_string` (`:859-871`) over `peek_length_prefixed`, keeping its `end`-only return; rewrite the raw date decode at `:744-746` as `peek_date_fields`, leaving the `:747-750` range checks byte-for-byte. Leave `:743` alone — it is the model the whole plan copies."
    },
    {
      "path": "src/ootp_ai/parser/human_managers.py",
      "change": "P2: rewrite `_is_club_landmark` (`:242-250`) over `lookahead.peek_u32` with a named `_U32_WIDTH`, removing both bare `4`s. `_pad_width` (`:196-211`) is names-only and stays as it is."
    },
    {
      "path": "src/ootp_ai/parser/header.py",
      "change": "Phase 3, and ONLY if Open Question 1 is disposed toward rewriting: `looks_like_save_file` (`:112-114`) reads the magic over `lookahead.peek_bytes` so the exemption registry stays empty. Otherwise this file is not touched and gains the single `EXEMPT_SITES` entry instead."
    },
    {
      "path": "src/ootp_ai/parser/primitives.py",
      "change": "P6, prose only: `:11-13` claims the AST guard runs 'with zero exemptions'. Correct it to match whatever Phase 3 actually shipped. No code change — `Cursor` is untouched by this work."
    },
    {
      "path": "tests/test_parse_players.py",
      "change": "P4: add `test_the_lookahead_offsets_are_the_measured_ones` to the OFFLINE half (before the `:347` gamedata divider), pinning 12 and 19 as the `verified` measurement. Do not disturb the import block at `:36-48`."
    },
    {
      "path": "CLAUDE.md",
      "change": "P6, one line: `:103` — say which paths CI now enforces the ban over. Keep it a map entry; the rulebook owns the rule."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "change": "P6: extend the fixed-offset bullet at `:69-74` with the lookahead seam. The substring 'fixed offset' must survive — `tests/test_agent_contract.py:62` greps for it."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "P6: set the `fixed-offset-guard-cannot-see-subscripts` Index row (`:51`) Stage cell to `fixed` and trim the note to what landed. `/commit`'s doc gate keeps the artifact status blockquotes in step."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/IMPLEMENTATION_PLAN.md",
      "change": "NEW — this plan itself, opening at `> **Status:** planned · created 2026-08-18 · decided · next: implement`. Written before Phase 1 and committed with it."
    }
  ],
  "code_references": [
    {
      "ref": "tests/test_no_fixed_offsets.py:43",
      "claim": "`visit_Call` is the entire mechanism — the class defines no other visitor, so `generic_visit` walks past every `ast.Subscript`. This is the proximate cause and the single place Phase 3 adds `visit_Subscript`."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:115-127",
      "claim": "The committed red reproduction, `test_the_scanner_flags_a_record_relative_subscript`. Verified RED by running `uv run pytest tests/test_no_fixed_offsets.py` on 2026-08-18: 1 failed, 4 passed, `AssertionError ... assert []` at `:124`."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:9-10",
      "claim": "/"A guard that cries wolf gets loosened, and a loosened guard is worse than none/" — the guard's own docstring, and the constraint that rules out the RCA's Minimal tier and drives the module-scoped design."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:143-155",
      "claim": "`test_no_parser_module_seeks_to_a_fixed_offset` — the real scan. It rglobs `src/ootp_ai/*.py`, builds a repo-relative POSIX path at `:149`, and asserts empty. The path at `:149` is what Phase 3's module scoping keys on."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:36-41",
      "claim": "`_nonzero_literal` — reusable by the subscript visitor as-is, including its `bool` exclusion at `:39` (a Python `bool` is an `int`)."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:219-220",
      "claim": "`_BIRTH_DATE_LOOKAHEAD = 12` and `_AGE_LOOKAHEAD = 19` — the two raw record-relative constants Phase 4 re-expresses as width sums. Their justification is at `:216-218`."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:553",
      "claim": "`_peek_date(data, position + _BIRTH_DATE_LOOKAHEAD)` — the RCA's 'genuinely guard-relevant case'. It is a Call with a Name offset, so no subscript rule can catch it; Phase 5's constant folding is what does."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:557",
      "claim": "`_peek_u8(data, position + _AGE_LOOKAHEAD)` — the second instance, same shape, same phase."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:451-456",
      "claim": "`_read_record`'s head sequence — `u32` id, two `u32` name indices, `date()`, `skip(_GAP_AFTER_BIRTH_DATE)`, `u8` age. This is the authority for Phase 4's derivation: 4 + 4 + 4 = 12, and 12 + 4 + 3 = 19."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:244",
      "claim": "`_GAP_AFTER_BIRTH_DATE = 3` — the third addend in `_AGE_LOOKAHEAD`, already named, already in the declared-span convention Phase 5 accepts."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:572-592",
      "claim": "`_peek_u8`, `_peek_u32` and `_peek_date` — three of the helpers Phase 2 moves. `_peek_date` at `:584-592` validates and returns `None` for a non-date; `world.py` does not, which is why only the raw primitive is shared."
    },
    {
      "ref": "src/ootp_ai/parser/teams.py:596-605",
      "claim": "The second `_peek_u32`. Its docstring `:599-601` — /"A lookahead at the cursor's own position, never at a constant/" — is one of the three prose statements of the rule the RCA cites as evidence the seam already wants to exist."
    },
    {
      "ref": "src/ootp_ai/parser/teams.py:581-593",
      "claim": "`_scan_string` returning `(length, end)`, with the bare-literal payload read at `:590` (`data[position + 4 : position + 4 + length]`) that Phase 2 moves behind `peek_length_prefixed`."
    },
    {
      "ref": "src/ootp_ai/parser/teams.py:522",
      "claim": "`while flag_count < _MAX_FLAGS and data[position : position + 1] == _FLAG_BYTE` — a literal-1 subscript comparing against a bytes object. Phase 2 rewrites it via `peek_bytes` and must NOT convert it to an int comparison."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:743",
      "claim": "`date_at = offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH` — the only form in the parser that is both constant-derived and self-documenting. It is the model Phase 4 copies and the shape Phase 5's `_WIDTH` convention is derived from."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:744-750",
      "claim": "The raw date decode plus its own range checks, which explicitly allow `year == 0` at `:749`. Sharing a validating `peek_date` here would narrow the accept set silently — the reason Phase 2 shares only `peek_date_fields`."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:859-883",
      "claim": "`_scan_string` (returning `end` only) and the third `_peek_u32`, whose docstring `:877-879` states the rule a third time. Both collapse into `lookahead.py` in Phase 2."
    },
    {
      "ref": "src/ootp_ai/parser/human_managers.py:242-250",
      "claim": "`_is_club_landmark` — two bare `4`s at `:244` and `:248` (`data[offset + 4 * slot : offset + 4 * slot + 4]`). Phase 2 rewrites both over `peek_u32` with a named `_U32_WIDTH`."
    },
    {
      "ref": "src/ootp_ai/parser/human_managers.py:196-211",
      "claim": "`_pad_width` — `data[position + width]` where `width` is a loop variable. Names-only, legal under the new rule, and the RCA's 'both widths are computed' benign case."
    },
    {
      "ref": "src/ootp_ai/parser/header.py:112-114",
      "claim": "`looks_like_save_file` reads `data[0]` and `data[1:_MAGIC_PREFIX_LEN]` — the file magic at absolute file offsets. The literal `1` is the ONLY site in the tree that a correct subscript rule flags but should not; it decides whether the exemption registry has zero entries or one (Open Question 1)."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:11-13",
      "claim": "/"That is also what lets the AST guard over `src/ootp_ai/` run with zero exemptions: there is no legitimate seek anywhere for it to have to allow./" A claim about the guard, in a parser module, that Phase 3 may falsify and Phase 6 must reconcile."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:91-104",
      "claim": "`Cursor.position` is a read-only property with no setter — the structural half of the ban the RCA confirmed is genuinely true (`ROOT_CAUSE_ANALYSIS.md:96-99`), and the reason the docs-only third option was refuted rather than dismissed."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:140",
      "claim": "`return self._data[start : start + count]` inside `Cursor.take` — a names-only buffer index that the new rule must not fire on. The Phase 1 census records it; the Phase 3 rule ignores it."
    },
    {
      "ref": "src/ootp_ai/parser/__init__.py:1-14",
      "claim": "The package `__init__` is a docstring plus `from __future__ import annotations` and re-exports nothing, so `lookahead.py` needs no registration. Its `:8-11` rule — nothing in this package opens a file — binds the new module too."
    },
    {
      "ref": "tests/test_parse_players.py:36-48",
      "claim": "Imports `_PAD_RUN` and `_looks_like_record` from `players.py` by name, with a comment at `:37-39` explaining that re-implementing the rule in the test would test a copy of it. Moving `_looks_like_record` breaks this import."
    },
    {
      "ref": "tests/test_parse_players.py:347-349",
      "claim": "The `# ── the real saves ──` divider and `_gamedata = pytest.mark.gamedata` — the boundary Phase 4's new pin test must land BEFORE, so it runs in CI."
    },
    {
      "ref": "tests/test_agent_contract.py:53-73",
      "claim": "`test_rulebook_invariants_survive` greps the rulebook for ten literal substrings including `/"fixed offset/"` at `:62`. Phase 6's rulebook edit must keep the phrase or CI goes red."
    },
    {
      "ref": ".claude/agents/data-engineer.md:69-74",
      "claim": "The fixed-offset bullet the guard's docstring cites by line — /"Code that seeks is a blocker, not a style note/" — and the single place Phase 6 adds the lookahead seam."
    },
    {
      "ref": ".github/workflows/ci.yml:57",
      "claim": "`uv run pytest -m /"not gamedata/"` — CI excludes every real-save test, so it cannot prove the Phase 2 refactor. The largest risk in the plan and the reason Phase 2 has a local-only acceptance gate."
    },
    {
      "ref": ".github/workflows/ci.yml:46-52",
      "claim": "The other three gates in order — `ruff check .`, `ruff format --check .`, `mypy` — the exact local bar every phase checkpoint must clear before `/commit`."
    },
    {
      "ref": "pyproject.toml:98-107",
      "claim": "`testpaths = [/"tests/"]`, `addopts = /"-q --strict-markers --strict-config/"`, and the `gamedata` marker with its in-file warning that inventing a second marker is a hard COLLECTION error. Widen, never add."
    },
    {
      "ref": "docs/data-access.md:275-279",
      "claim": "/"The record head is fixed for 37 bytes; the drop-zero region begins after it/" — labelled `verified` against every `retired = 0` export row, 18,072 of 18,072, exact match, not sampled. This is why Phase 4 needs no new byte measurement: the fixed-head premise the two lookahead constants rest on is already verified, not assumed."
    },
    {
      "ref": "docs/data-access.md:284-287",
      "claim": "The drop-zero encoding after `experience`, and the measurement that `team_id` sits at record+58 for 86.9% of players — the number the red repro encodes and the concrete harm the ban exists to prevent."
    },
    {
      "ref": "requests/bugfix-requests/README.md:24-26",
      "claim": "/"'Done' means the red reproduction goes green and a regression test is left behind./" The track's acceptance contract, satisfied at Phase 3 and hardened through Phase 5."
    },
    {
      "ref": "requests/bugfix-requests/README.md:51",
      "claim": "The Index row for this bug, currently at Stage `diagnosed`. Phase 6 advances it to `fixed`."
    },
    {
      "ref": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md:124-139",
      "claim": "The Root tier and its three candidate rules with costs — name-based allowlist (too trusting), Literal-vs-Name (too weak, misses `players.py:553`), module-scoped (strongest, largest diff). This plan builds module-scoped, and Phase 2 is what makes the diff small."
    },
    {
      "ref": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/BUGFIX_REQUEST.md:100-106",
      "claim": "The survey table classifying every current direct-buffer site as benign or guard-relevant. It is the false-positive budget: after Phase 2 and Phase 4, every row in it must be green under the new rule."
    }
  ],
  "open_questions": [
    "OQ1 — ZERO EXEMPTIONS OR ONE? `header.looks_like_save_file` (`header.py:112-114`) reads the OOTP magic at absolute file offsets 0 and 1. Option A: register it in `EXEMPT_SITES` with a written reason, and correct `primitives.py:11-13` to say 'one named exemption'. Option B: rewrite it over `lookahead.peek_bytes(data, 0, _MAGIC_PREFIX_LEN)`, keeping the exemption registry EMPTY and the 'zero exemptions' claim literally true. Recommendation: B — it costs three lines, keeps a claim the repo has made since Phase 3 honest, and removes the only place a future author can point at as precedent for adding a second exemption. Must be disposed BEFORE Phase 3, because it decides whether `EXEMPT_SITES` ships with an entry.",
    "OQ2 — HOW WIDE IS THE DECLARED-SPAN CONVENTION? Phase 5 accepts a Name ending `_WIDTH` or beginning `_GAP_` as a legal addend. `_LEN`, `_SIZE`, `_COUNT` and `_STRIDE` are all plausible future spellings and none is in the tree today. Recommendation: ship `_WIDTH` and `_GAP_` only and let the first real site that needs another suffix argue for it in a diff. Widening an allowlist speculatively is how a guard loosens without anyone deciding to loosen it.",
    "OQ3 — PUBLIC OR PRIVATE NAMES IN `lookahead.py`? The functions it absorbs are all module-private today (`_peek_u32`, `_peek_u8`, `_peek_date`). As a cross-module seam they must be importable, so this plan names them `peek_u32` etc. without the underscore. That makes them part of `ootp_ai.parser`'s internal API surface even though nothing outside the package should call them. Recommendation: unprefixed, with a docstring line stating the module is package-internal and not re-exported from `parser/__init__.py`.",
    "OQ4 — SHOULD THE CENSUS INVENTORY BE A GUARD OR A REPORT? Phase 1 pins the `(module, function)` set, so ANY new buffer-indexing function fails CI until someone updates the pin. That is deliberate friction and it is the thing that survives a rename of the buffer variable — but it will fire on legitimate new parser work (Phase 6b of `first-sight` works in exactly this region). Recommendation: keep it a hard guard; the failure message should say plainly that a new indexing site is expected to be reviewed and added, which is the whole point. Flagged because it is a cost the operator pays on unrelated future work.",
    "OQ5 — DOES THE `_UNCLASSIFIED_BEFORE_MASKS` FAMILY NEED THE SAME TREATMENT? `players.py:253` (`_GAP_AFTER_EXPERIENCE = 14`) and `:262` (`_UNCLASSIFIED_BEFORE_MASKS = 4`) are bare ints, but they are `skip()` widths consumed by the CURSOR, never position addends, so Phase 5's rule never sees them and they are correct as written. Confirmed by reading `_read_record` (`:455-474`). Recorded here only so a future reader does not re-open it — no action."
  ]
}
```


## Planner 3

```json
{
  "planner": "domain-convention",
  "ok": true,
  "onboarding_files": [
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md",
      "why": "The decided upstream artifact. Read the Verdict, the Reproduction (red) block, the Evidence section, and especially the tiered Fix posture at lines 113-147 — it forbids shipping the minimal `visit_Subscript` tier alone and names the three candidate rules with their costs. Consume it; do not re-litigate the verdict."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/BUGFIX_REQUEST.md",
      "why": "Context only. Its 'Affected Area & Pointers' table (lines 97-106) is the surveyed inventory of every current direct-buffer read and whether each is benign — the classification the new rule has to reproduce. Note the RCA re-grounded two citations (players.py:445/:449 are now :553/:557)."
    },
    {
      "path": "tests/test_no_fixed_offsets.py",
      "why": "The file being fixed. `FixedOffsetVisitor` (lines 29-62) is the whole mechanism and defines only `visit_Call`; `SUBSCRIPT_OFFENDER` (lines 96-99) and `test_the_scanner_flags_a_record_relative_subscript` (lines 115-127) are the committed red repro; `test_no_parser_module_seeks_to_a_fixed_offset` (lines 143-155) is the real whole-tree scan whose `SCAN_ROOT` is `src/ootp_ai`."
    },
    {
      "path": "src/ootp_ai/parser/primitives.py",
      "why": "The Cursor — the structural half of the ban. It exposes no `seek` and `position` is a read-only property (lines 96-104). Its docstring at lines 11-13 makes the 'zero exemptions' claim that this change makes false and that Phase 6 must correct. `Cursor.take` at line 140 is the one buffer subscript that legitimately survives."
    },
    {
      "path": "src/ootp_ai/parser/players.py",
      "why": "Carries the defect that prompted the request: `_looks_like_record` calls `_peek_date(data, position + _BIRTH_DATE_LOOKAHEAD)` and `_peek_u8(data, position + _AGE_LOOKAHEAD)` at lines 553 and 557, with those constants at lines 219-220. Its `_peek_u8`/`_peek_u32`/`_peek_date` (lines 572-592) are the richest of the three duplicated lookahead families."
    },
    {
      "path": "src/ootp_ai/parser/teams.py",
      "why": "Holds the second duplicate `_peek_u32` (lines 596-605) whose docstring states the rule in prose — 'A lookahead at the cursor's own position, never at a constant.' Also `_scan_shape` (line 485) and the flag-byte scan at line 522, both migration sites."
    },
    {
      "path": "src/ootp_ai/parser/world.py",
      "why": "Holds the third duplicate `_peek_u32` (lines 874-883), the inline event-date decode at lines 744-746, and — at line 743 — the ONLY form in the parser that is both constant-derived and self-documenting (`offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH`), which Phase 5 copies."
    },
    {
      "path": "src/ootp_ai/parser/header.py",
      "why": "The site the RCA's survey table did not classify. `looks_like_save_file` at line 114 reads `data[0]` and `data[1:_MAGIC_PREFIX_LEN]` — a literal absolute offset — while the module docstring (lines 3-8) claims the module avoids 'indexing offsets 1, 5 and 25 with literals' under a guard with 'zero exemptions'. Widening the guard turns this line red; Phase 2 owns it."
    },
    {
      "path": "tests/test_leak_guard_scope.py",
      "why": "The precedent to copy, not invent. It is the meta-guard for the repo's other AST/scan guard, and its final section (lines 196-238) exists because a mutant that scanned zero files left the whole suite green. The `untracked_file` contextmanager (lines 40-53) and the coverage floor (lines 224-238) are the two patterns Phase 4 reuses."
    },
    {
      "path": "tests/test_agent_contract.py",
      "why": "Constrains the Phase 6 doc edits. `test_rulebook_invariants_survive` (lines 53-73) requires the literal substring 'fixed offset' to survive in the agent definition; `test_deny_set_still_protects_the_guards` (lines 76-81) requires `tests/` and `CLAUDE.md` to stay in the data-engineer's deny set — which is why this work cannot be delegated to that subagent; `test_memory_entries_carry_an_epistemic_label` (lines 84-95) fixes the shape of the ledger entry."
    },
    {
      "path": "docs/data-access.md",
      "why": "Read lines 251-287. The 37-byte fixed head is labelled `verified` against 18,072 of 18,072 export rows — that is the claim Phase 5's width-sum re-expression rests on, so no verification phase is needed. Lines 284-287 record the 86.9% `team_id` measurement that makes the repro's `58` a real number."
    },
    {
      "path": ".github/workflows/ci.yml",
      "why": "Defines what CI actually enforces: `ruff check`, `ruff format --check`, `mypy`, and `pytest -m /"not gamedata/"` (lines 45-57). CI never sees a save, so the gamedata half of the proof that this refactor changed no behaviour has to be run locally by the implementer and recorded."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "why": "The build rulebook and the single owner of the fixed-offset ban (lines 69-74). Phase 6 edits this section; the Write allowlist section further down denies `tests/`, which decides who may do Phases 3, 4 and 6."
    }
  ],
  "architecture_notes": "THE SHAPE OF THE DEFECT, RESTATED AS ARCHITECTURE/n/nThe parser has two read paths and the guard covers spellings within only one of them./n/n1. The CONSUMING path — `Cursor` in `src/ootp_ai/parser/primitives.py`. Structurally unable to seek: no `seek` method, no position setter, `position` is a read-only property (primitives.py:96-104), every read goes through `_advance` (primitives.py:115-131). This half of the ban is airtight and needs no work./n/n2. The SEARCH path — some two dozen module-level helpers that take `(data: bytes, position: int)` and index the buffer directly: `_scan_shape` (teams.py:485), `_scan_signature` (teams.py:542), `_find_league_record` (world.py:490), `_find_calendar_array` (world.py:667), `_scan_event` (world.py:725), `_looks_like_record` (players.py:540), `_pad_width` (human_managers.py:196), `_is_club_landmark` (human_managers.py:242), and three separately-written `_peek_u32`s. Nothing structural constrains this path at all, and it is precisely where a record-relative constant appears./n/nThe RCA's Root tier says: give that path a single legitimate home and let the guard key on the home rather than on syntax. This plan takes that tier, plus the Hardening tier, and skips the Minimal tier as instructed (ROOT_CAUSE_ANALYSIS.md:113-122)./n/nTHE SEAM: `src/ootp_ai/parser/lookahead.py`/n/nOne new module, the only place under `src/ootp_ai/` allowed to index a save buffer, alongside `primitives.py` (which owns the consuming path). It absorbs three duplicated `_peek_u32` implementations — teams.py:596, players.py:577, world.py:874 — whose docstrings already state the same rule in three different sentences. Triplication is the evidence the seam wanted to exist./n/nProposed surface, sized to the thirteen real migration sites and nothing more (CLAUDE.md: directories and abstractions appear when their phase does):/n/n  U8_WIDTH, U32_WIDTH, DATE_WIDTH        named widths, so nothing inside indexes with a bare literal/n  peek_u8(data, position)   -> int | None/n  peek_u32(data, position)  -> int | None/n  peek_bytes(data, position, width) -> bytes | None/n  peek_date_parts(data, position) -> tuple[int, int, int] | None/n  peek_date(data, position) -> SaveDate | None/n  is_zero_run(data, position, width) -> bool/n  zero_run_width(data, position, limit) -> int/n/n`peek_date_parts` and `peek_date` are deliberately two functions: `world.py:749` accepts `year == 0` as a valid event date and `players.py:592` rejects it, so a single /"is this a date/" helper would have to pick one caller's rule and silently change the other's framing. Parts returns raw bytes-as-numbers with no judgement; `peek_date` is players' stricter wrapper. Every helper returns `None`/`False` out of bounds — never raises, never wraps — and bounds-checks BOTH ends, taking the strictest of the three existing variants (players.py:579 rejects a negative position; teams.py:603 and world.py:881 do not)./n/nTHE RULE THE GUARD ENFORCES/n/nWeighing the RCA's three candidates (ROOT_CAUSE_ANALYSIS.md:132-140) against what is actually in the tree:/n/n- Name-based allowlist (`_peek_*`/`_scan_*`/`_find_*` may index): rejected. An author names anything `_peek_` and the guard believes them — the RCA's own objection, and it is right./n- Literal-vs-Name (flag a bare int addend, allow a named constant): rejected. Would not catch players.py:553, which uses `_BIRTH_DATE_LOOKAHEAD`. The RCA calls this too weak and the code confirms it./n- Module-scoped: taken. It is the one that would have caught this./n/nImplemented as: in a module whose repo-relative posix path is not in `EXEMPT_MODULES`, flag any `ast.Subscript` whose value is a Name that is a BUFFER for the enclosing function — where /"buffer/" means a parameter annotated `bytes`, plus any local directly aliased from one (`buf = data`). Inside the exempt modules the call-shape checks still apply, and a second, STRICTER rule applies: a bare nonzero int literal anywhere in a buffer subscript index is a violation even there, forcing `lookahead.py` to write `position + U32_WIDTH`, not `position + 4`. The one module with an exemption is the most disciplined module in the tree — the honest inverse of /"an exemption list is how a guard stops being a guard/" (header.py:6-8)./n/nWHY ANNOTATION-KEYED, MEASURED RATHER THAN ASSUMED/n/nI checked the alternative — /"flag any arithmetic subscript inside a function that has a bytes parameter/" — against the real tree and it cries wolf twice: `tail[4]` at players.py:383 and `declared_records = tail[4]` at human_managers.py:154 are tuple subscripts inside `read_players(data: bytes)` and `read_human_manager(data: bytes)`. Keying on the annotated parameter name instead gives ZERO false positives across all 17 modules under `src/ootp_ai/`. Specifically it does not fire on: `pattern[_LENGTH_PREFIX_WIDTH:]` (world.py:844 — `pattern` is a bytes param but the index is a lone Name with no arithmetic and no literal, so the arithmetic/literal condition also has to hold); `self._data[start : start + count]` (primitives.py:140 — an Attribute, and an exempt module anyway); `run[base + 1]`/`run[base + 2 :]` (teams.py:624-625 — a tuple in a function with no bytes param); `values[0..5]` (teams.py:774-779)./n/nThe annotation key is also not evadable by dropping the annotation: mypy runs strict over `src` and `tests` (pyproject.toml:91-95), so an unannotated parameter fails the build. Two independent guards would have to fail together. The one residual evasion — aliasing through a derived expression rather than a direct assignment — is closed for the direct case and documented with a test for the rest./n/nWHAT THIS CHANGE IS NOT/n/nIt lands no dataset, no dbt model, no new source, and touches nothing in `datasets/` (which does not exist yet, per CLAUDE.md's project map). There is no grain to declare, no `datasets/manifest.json` logical name to register, no coverage window, no merge key, no pull cost, no `var/cache/` entry. Section 9 of the plan template is omitted on purpose, not by oversight. The conventions that DO bind here are project conventions, and they are enumerated in the Conventions section.",
  "phases": [
    {
      "name": "Phase 1 — The lookahead seam, with players.py as its first client",
      "goal": "Give buffer indexing one sanctioned home, prove it in isolation, and retire the first of three duplicated `_peek_u32` families — with a recorded behaviour baseline so the rest of the refactor is provably behaviour-preserving.",
      "steps": [
        "BEFORE editing anything, capture the baseline. Run `uv run pytest -q` and `uv run pytest -m gamedata -q` locally and record the pass counts, the player/team record counts from `tests/test_parse_real_save.py`, and the byte-accounting residuals from `tests/test_byte_accounting.py`. CI never runs the gamedata half (`.github/workflows/ci.yml:57` runs `-m /"not gamedata/"`), so this local record is the ONLY evidence the refactor changed no behaviour. Paste it into the phase's commit body.",
        "Create `src/ootp_ai/parser/lookahead.py`. The module docstring must state three things: that this is the one module under `src/ootp_ai/` permitted to index a save buffer; why (three separately-written `_peek_u32`s at `teams.py:596`, `players.py:577`, `world.py:874`, each with a docstring asserting the same rule in prose, is the seam announcing itself); and that it is guarded MORE strictly than the rest of the tree, so every width inside it is a named constant.",
        "Define the surface named in the architecture notes: `U8_WIDTH`, `U32_WIDTH`, `DATE_WIDTH`; `peek_u8`, `peek_u32`, `peek_bytes`, `peek_date_parts`, `peek_date`, `is_zero_run`, `zero_run_width`. Declare `__all__`. Import `SaveDate` from `ootp_ai.parser.primitives` (which imports only `ootp_ai.parser.errors`, so no cycle). Nothing speculative — add only what the migration sites in Phases 1-2 consume.",
        "Bounds-check both ends in every helper: `position < 0 or position + width > len(data)` returns `None`/`False`. This is the strictest of the three current variants — `players.py:579` rejects a negative position, `teams.py:603` and `world.py:881` do not. Say in a comment that unifying upward is deliberate and that no current caller passes a negative position, so it cannot change behaviour.",
        "Write `tests/test_lookahead.py`, offline and synthetic (no game data, no MySQL): a happy path per helper; out-of-bounds returning `None`; negative position returning `None`; `zero_run_width` hitting its limit; and the structural-absence case — `peek_date_parts` on a 0/0/0 date returns `(0, 0, 0)` while `peek_date` returns `None`, matching `SaveDate.as_date`'s contract at `primitives.py:58-67`.",
        "Migrate `players.py` only. Delete `_peek_u8`, `_peek_u32` and `_peek_date` (`players.py:572-592`) and import the shared versions. Replace `data[cursor.position] == 0` (`players.py:424`) and `data[after] == 0` (`players.py:529`) with `peek_u8`. Leave `_BIRTH_DATE_LOOKAHEAD` and `_AGE_LOOKAHEAD` (`players.py:219-220`) untouched — Phase 5 owns them, and changing them here would confound the baseline comparison.",
        "Run the gate: `uv run ruff check`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest -q`, then `uv run pytest -m gamedata -q` locally."
      ],
      "acceptance": [
        "`src/ootp_ai/parser/lookahead.py` exists and `tests/test_lookahead.py` is green offline.",
        "No `def _peek_` remains in `src/ootp_ai/parser/players.py` (verify by grep; the file had three at lines 572, 577 and 584).",
        "`uv run mypy` is clean under strict mode over both `src` and `tests` (pyproject.toml:91-95), and `uv run ruff check` plus `uv run ruff format --check .` are clean — CI runs all three (ci.yml:45-52).",
        "`uv run pytest -m gamedata -q` locally reproduces the step-1 baseline EXACTLY: same record counts, same byte-accounting residuals. A single changed number means the refactor moved the framing and must be reverted, not explained.",
        "`uv run pytest -m gamedata tests/test_read_only.py -q` passes with zero mtime and zero digest differences under both roots — ADR 0001, re-checked at every checkpoint per the standing rule at `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:928`.",
        "`uv run pytest -q` reports EXACTLY ONE failure and it is `tests/test_no_fixed_offsets.py::test_the_scanner_flags_a_record_relative_subscript`. That test stays red until Phase 3 by design — the guard cannot widen before the tree is migrated, or the whole-tree scan goes red instead. Use `--deselect tests/test_no_fixed_offsets.py::test_the_scanner_flags_a_record_relative_subscript` for a clean intermediate run, and a full run to confirm nothing else broke."
      ],
      "commit_note": "Give buffer lookahead one home, and make players.py its first client. Body carries the gamedata baseline numbers. Land through `/commit` — never `git commit` ad hoc, and the PR stays the operator's."
    },
    {
      "name": "Phase 2 — Route the remaining four modules through the seam",
      "goal": "Leave zero direct buffer subscripts under `src/ootp_ai/parser/` outside `lookahead.py` and `primitives.py`, so the guard can be widened in Phase 3 without going red on legitimate code.",
      "steps": [
        "`teams.py`: delete `_peek_u32` (lines 596-605) and import it. Replace `data[position : position + 1] == _FLAG_BYTE` (line 522) with a `peek_u8` comparison against the flag's integer value. Replace `payload = data[position + 4 : position + 4 + length]` (line 590) with `peek_bytes(data, position + LENGTH_PREFIX_WIDTH, length)` and handle the `None` case as the existing bounds test at line 588 already does.",
        "`world.py`: delete `_peek_u32` (lines 874-883) and import it. Replace `data[pad_at:length_at] != b/"/x00/" * _EVENT_PAD_WIDTH` (line 740) with `not is_zero_run(data, pad_at, _EVENT_PAD_WIDTH)`. Replace the inline date decode at lines 744-746 with `peek_date_parts(data, date_at)` — keeping world's own validity rule at lines 747-750 intact, including its acceptance of `year == 0`, which is exactly why `peek_date_parts` passes judgement back to the caller. Replace `data[name_at : name_at + length]` (line 759) and `data[position + 4 : position + 4 + length]` (line 868) with `peek_bytes`. Leave `pattern[_LENGTH_PREFIX_WIDTH:]` at line 844 alone — it slices a locally constructed search pattern for an error message, not a save buffer, and the Phase 3 rule does not fire on it.",
        "`human_managers.py`: replace `data[position + width] == 0` (line 204) with `peek_u8`, or better, replace the whole `_pad_width` body with `zero_run_width(data, position, _MAX_PAD)` and keep its refusal at lines 206-210. Replace both `int.from_bytes(data[...], /"little/")` calls in `_is_club_landmark` (lines 244 and 248) with `peek_u32(data, offset)` and `peek_u32(data, offset + U32_WIDTH * slot)`; mypy strict will force the new `None` branches, which is a strict safety improvement over today's unchecked slice.",
        "`header.py`: add a module constant `MAGIC_PREFIX = bytes([LEADING_NULL]) + MAGIC` and rewrite `looks_like_save_file` (line 114) as `return data.startswith(MAGIC_PREFIX)`. This is exactly equivalent given the length guard at lines 112-113 and `_MAGIC_PREFIX_LEN = 1 + len(MAGIC)` at line 79. Keep the early return — it documents intent even though `startswith` is already False on a short buffer. Update the module docstring's second bullet (line 13) so the example it warns about is not the code it now contains.",
        "Sweep for stragglers: grep `src/ootp_ai/` for `data[`, `payload[`, `buf[`. The only surviving hits must be `primitives.py:140` and whatever is inside `lookahead.py`.",
        "Run the full gate again including `uv run pytest -m gamedata -q` locally and compare against the Phase 1 baseline."
      ],
      "acceptance": [
        "Grep over `src/ootp_ai/` for a subscript on a `bytes` parameter returns hits only in `src/ootp_ai/parser/lookahead.py` and `src/ootp_ai/parser/primitives.py`.",
        "Zero `def _peek_u32` definitions remain anywhere in `src/ootp_ai/parser/` outside `lookahead.py` — there were three (teams.py:596, players.py:577 removed in Phase 1, world.py:874).",
        "Offline suite green: `tests/test_save_header.py`, `tests/test_parse_players.py`, `tests/test_parse_teams_synthetic.py`, `tests/test_parse_world.py` (offline half), `tests/test_sequential_walk.py`. `tests/test_parse_players.py::test_records_of_different_lengths_all_decode` (line 137) matters most here — it is the offline test a constant-stride reimplementation fails.",
        "`uv run pytest -m gamedata -q` locally still reproduces the Phase 1 baseline exactly, across `tests/test_parse_real_save.py`, `tests/test_byte_accounting.py`, `tests/test_cross_mode_format.py` and the gamedata half of `tests/test_parse_world.py`.",
        "ADR 0001 re-checked: `uv run pytest -m gamedata tests/test_read_only.py -q` green, zero mtime and zero digest differences.",
        "`uv run ruff check`, `uv run ruff format --check .`, `uv run mypy` all clean. Full `uv run pytest -q` still has exactly the one expected failure."
      ],
      "commit_note": "Route every buffer read in the parser through the lookahead seam; read the file magic with startswith. Land through `/commit`."
    },
    {
      "name": "Phase 3 — Widen the guard, and turn the red repro green",
      "goal": "Make the ban independent of which syntax an author reached for. This is the phase that discharges the RCA's acceptance contract.",
      "steps": [
        "In `tests/test_no_fixed_offsets.py`, add `EXEMPT_MODULES = frozenset({/"src/ootp_ai/parser/lookahead.py/", /"src/ootp_ai/parser/primitives.py/"})`, matched against the repo-relative posix path the real scan already constructs at line 149. Write the reason above it in prose: the cursor owns the consuming path and the lookahead module owns the search path; everything else reads a buffer through one of them.",
        "Extend `FixedOffsetVisitor` (lines 29-62). Leave `visit_Call` exactly as it is — the `.seek(<literal>)` and `unpack_from(..., <literal>)` checks must keep firing in every module, exempt ones included, so nothing regresses. Add `visit_FunctionDef` (and `visit_AsyncFunctionDef` for completeness) to compute the enclosing function's BUFFER NAMES: every parameter whose annotation is the bare Name `bytes`, plus any local bound by a single-target `Assign` whose value is a Name already in that set. Add `visit_Subscript` that flags a subscript whose value is a Name in the buffer set AND whose index contains an `ast.BinOp` or a nonzero integer literal.",
        "Apply the stricter interior rule: when the filename IS exempt, skip the buffer-name check but flag any bare nonzero integer literal appearing in a buffer subscript index. This is what forces `lookahead.py` to write `position + U32_WIDTH` rather than `position + 4`, and it is the argument that the one exemption does not soften the ban.",
        "Track nesting honestly. Buffer names are per-function; restore the outer function's set when leaving a nested one, so a helper defined inside a walker does not inherit `data`.",
        "Fix up `lookahead.py` if the interior rule flags it — replacing any literal widths with the named constants defined in Phase 1.",
        "Run `uv run pytest tests/test_no_fixed_offsets.py -q` and confirm all five tests pass, then the full gate."
      ],
      "acceptance": [
        "`uv run pytest tests/test_no_fixed_offsets.py -q` is fully green — `test_the_scanner_flags_a_record_relative_subscript` (line 115) now passes. This is the RCA's acceptance contract: the red repro goes green.",
        "The three pre-existing scanner tests pass UNMODIFIED: `test_the_scanner_flags_a_synthetic_offender` (line 102), `test_the_scanner_does_not_cry_wolf` (line 110), `test_prose_about_seeking_does_not_trip_the_scanner` (line 130). If any needed editing to pass, the new rule is wrong — none of their fixtures contains a subscript.",
        "`test_no_parser_module_seeks_to_a_fixed_offset` (line 143) is green over the whole tree with the widened rule — the proof that Phases 1 and 2 finished the migration.",
        "Manual red-check, recorded in the commit body: paste `data[record_start + 58 : record_start + 62]` into a non-exempt parser module, confirm the whole-tree scan reports it with the right `file:line`, revert. This is the same procedure the first-sight plan used for this guard (`requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:920`).",
        "`uv run pytest -q` is now fully green with no deselects. `ruff check`, `ruff format --check .`, `mypy` clean."
      ],
      "commit_note": "Teach the fixed-offset guard to see a subscript, and give buffer lookahead one sanctioned home. Land through `/commit`."
    },
    {
      "name": "Phase 4 — Guard the guard",
      "goal": "Make the widened scan SEEN TO FAIL and seen not to cry wolf, so the next agent has grounds to trust it. Without this the suite proves only that the guard runs, which is the exact failure the leak guard was already bitten by.",
      "steps": [
        "Create `tests/test_fixed_offset_guard_scope.py`, modelled on `tests/test_leak_guard_scope.py`. Its docstring should say why it is a separate module: `test_no_fixed_offsets.py` owns WHAT counts as a fixed-offset read; this owns WHERE the scan looks and whether it can fail at all — and the second fails invisibly.",
        "Planted-offender test, the end-to-end property: using a `try/finally` contextmanager in the spirit of `tests/test_leak_guard_scope.py:40-53`, write `src/ootp_ai/parser/_guard_probe.py` containing the offending subscript, call the REAL whole-tree scan (not `scan_source` on a string), assert the probe is named in the violations, and unlink it in `finally` unconditionally. This proves the scan reads real modules from disk, which every string-fixture test above it assumes.",
        "Coverage floor: assert `len(sorted(SCAN_ROOT.rglob(/"*.py/"))) >= 12`. There are 17 today. The floor is deliberately well below the real count so ordinary churn never trips it — it exists to catch a collapse, the mutant class documented at `tests/test_leak_guard_scope.py:224-238`.",
        "Exemption integrity: assert `EXEMPT_MODULES` has exactly two entries and that each resolves to an existing file under `REPO_ROOT`. A typo'd exemption fails loudly (the module gets scanned) but an over-broad one — say `src/ootp_ai/parser/` — would silently exempt the whole package.",
        "Exempt is not exempt from everything: assert `scan_source` on a `.seek(128)` snippet still flags when handed the filename `src/ootp_ai/parser/lookahead.py`, and that a bare `data[position + 4]` inside an exempt module IS flagged by the stricter interior rule while `data[position + U32_WIDTH]` is not.",
        "Alias evasion: assert a snippet doing `buf = data` then `buf[start + 58 : start + 62]` is flagged. Add a docstring noting the residual limitation — an alias produced by an expression rather than a direct assignment is not tracked — so the next reader knows the boundary rather than assuming there is none.",
        "Cry-wolf controls, each asserting `scan_source(...) == []`, and each lifted from a REAL line so the test says what it is protecting: `tail[4]` inside a `bytes`-param function (the shape at `players.py:383` and `human_managers.py:154`); `run[base + 1]` inside a function with no `bytes` parameter (`teams.py:624`); `pattern[_LENGTH_PREFIX_WIDTH:]` (`world.py:844`); `self._data[start : start + count]` (`primitives.py:140`); a plain `data[position]`.",
        "Perform and record the mutant check by hand: delete `visit_Subscript`, confirm the new module goes red, restore. Note the result in the commit body — a guard never seen to fail is not a guard."
      ],
      "acceptance": [
        "`uv run pytest tests/test_fixed_offset_guard_scope.py -q` green, and the working tree is clean afterwards — `git status --porcelain` shows no leftover `_guard_probe.py`. A leftover would now also be caught by `tests/test_no_leaks.py`, which since the leak-guard fix enumerates untracked files too (`requests/bugfix-requests/README.md:53`), but the `finally` unlink is what must be relied on.",
        "Removing `visit_Subscript` turns the new module RED (recorded, then restored). Removing the exemption lookup turns the whole-tree scan RED. Both mutants die.",
        "Every cry-wolf control passes, and each names the real `file:line` it is derived from in a comment.",
        "Full gate green: `uv run pytest -q`, `uv run ruff check`, `uv run ruff format --check .`, `uv run mypy`."
      ],
      "commit_note": "Guard the guard: prove the subscript scan can fail, and prove it does not cry wolf. Land through `/commit`."
    },
    {
      "name": "Phase 5 — Express the two record-relative lookaheads as sums of named field widths",
      "goal": "Close the RCA's Hardening tier: the two constants that motivated the whole request stop being raw record-relative offsets and become the self-documenting form the parser already uses elsewhere.",
      "steps": [
        "Confirm the epistemic footing before touching anything. `docs/data-access.md:275-278` labels the 37-byte fixed head `verified` — exact against every one of 18,072 `retired = 0` export rows, not sampled. This plan therefore depends on a `verified` claim and needs no verification phase ahead of it. Do NOT upgrade or restate any label while editing.",
        "Derive the values from the read order in `_read_record` (`players.py:451-456`): `u32 player_id` + two `u32` name indices = 12, which is `_BIRTH_DATE_LOOKAHEAD`; plus the 4-byte date plus `_GAP_AFTER_BIRTH_DATE` (3) = 19, which is `_AGE_LOOKAHEAD`. Both derivations are exact.",
        "Introduce named widths (`_PLAYER_ID_WIDTH`, `_NAME_INDEX_WIDTH`, `_NAME_INDEX_COUNT`) and rewrite `players.py:219-220` as `_BIRTH_DATE_LOOKAHEAD = _PLAYER_ID_WIDTH + _NAME_INDEX_WIDTH * _NAME_INDEX_COUNT` and `_AGE_LOOKAHEAD = _BIRTH_DATE_LOOKAHEAD + DATE_WIDTH + _GAP_AFTER_BIRTH_DATE`. This is the form at `world.py:743` — the only one in the parser that is both constant-derived and self-documenting.",
        "MOVE `_GAP_AFTER_BIRTH_DATE` (currently `players.py:244`) above the lookahead definitions, or the module raises `NameError` at import. This is the concrete trap in this phase; the gap constants at lines 244-247 currently sit 25 lines BELOW the lookaheads.",
        "Update the comment at `players.py:216-218` so it describes a width sum rather than a pair of measured offsets, keeping its correct point that these are validation lookaheads confirming a candidate record start, not field reads.",
        "Add to `tests/test_parse_players.py`: build a head with `make_player_head` (`tests/fixtures/synthetic.py:242`) using explicit `birth=` and `age=`, then assert `peek_date(head, _BIRTH_DATE_LOOKAHEAD)` and `peek_u8(head, _AGE_LOOKAHEAD)` return exactly what the fixture wrote. Also assert `_BIRTH_DATE_LOOKAHEAD == 12` and `_AGE_LOOKAHEAD == 19`, so the re-expression is proven value-identical rather than merely prettier. Offline, no game data."
      ],
      "acceptance": [
        "The new offline test in `tests/test_parse_players.py` passes: the derived offsets land on the birth date and age the synthetic fixture wrote, and both still equal 12 and 19.",
        "`uv run pytest -m gamedata -q` locally reproduces the Phase 1 baseline record counts exactly. If framing moved, the counts move — this is the check that catches a mis-derived width.",
        "`uv run pytest -q`, `ruff check`, `ruff format --check .`, `mypy` all green.",
        "No epistemic label anywhere was strengthened by this phase; the plan consumed a `verified` claim and added none."
      ],
      "commit_note": "Express the players.dat lookaheads as sums of named field widths, per the verified 37-byte head. Land through `/commit`."
    },
    {
      "name": "Phase 6 — Correct the live claims, append to the ledger, close the request",
      "goal": "Make every load-bearing sentence about the ban true again — as a consequence of what the guard now covers, which is the order the RCA insists on — and advance the request through the pipeline's status grammar.",
      "steps": [
        "`CLAUDE.md:103`: replace /"The fixed-offset ban is the rulebook's, and CI enforces it/" with a sentence that survives inspection — the ban is enforced twice, structurally by a cursor that cannot seek and mechanically by an AST scan that lets exactly one sanctioned lookahead module index a save buffer.",
        "`.claude/agents/data-engineer.md:69-74`: keep the rule and add the new mechanism (index a save buffer only through `parser/lookahead.py`; everything else walks the cursor). CONSTRAINT: the literal substring `fixed offset` must survive — `tests/test_agent_contract.py:62` asserts it, along with nine sibling needles at lines 60-71. Do NOT touch the Write-allowlist deny set; `tests/test_agent_contract.py:76-81` requires `tests/`, `.github/`, `ops/`, `CLAUDE.md` and `docs/decisions/` to remain in it.",
        "`src/ootp_ai/parser/primitives.py:11-13`: the /"zero exemptions/" claim is now false. Rewrite it to say the cursor's structural guarantee is what lets the AST scan hold the search path to a single sanctioned module, itself guarded more strictly than the tree around it.",
        "`src/ootp_ai/parser/header.py:5-8`: same claim, same correction — and the paragraph should now describe reading the magic with `startswith` rather than warning against /"indexing offsets 1, 5 and 25 with literals/" in a module that until Phase 2 indexed offset 1 with a literal.",
        "`tests/test_no_fixed_offsets.py:1-18`: extend the module docstring to describe both mechanisms — the two call shapes and the buffer-subscript rule — and to name `tests/test_fixed_offset_guard_scope.py` as the module that proves it can fail. Keep the /"AST, not regex/" paragraph; it is still the reason.",
        "APPEND — never edit — a dated entry to `.claude/agents/data-engineer-memory.md`, in the exact shape specified at lines 23-33: `- **YYYY-MM-DD** · `verified` · <claim> · evidence: <inline-code path> · tag: harness`. `tests/test_agent_contract.py:84-95` checks the date prefix and that the backticked label is one of the five. Paths inline code, never markdown links.",
        "Do NOT rewrite the stale /"zero exemptions/" phrase inside the existing ledger entry at `.claude/agents/data-engineer-memory.md:237-241`, nor the same phrase in landed request artifacts (`requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:1083`, `requests/feature-requests/first-sight/reviews/handoff-phase-3.md:18`). Those are a log of what was true when they landed. A docstring is a live claim; a ledger entry is history.",
        "Advance the pipeline status. Both `BUGFIX_REQUEST.md` and `ROOT_CAUSE_ANALYSIS.md` status blockquotes move to `fixed`, per the grammar at `requests/bugfix-requests/README.md:45`; the Index row at `requests/bugfix-requests/README.md:51` moves its Stage cell to `fixed`; write the `IMPLEMENTATION_REPORT.md` the layout at lines 28-39 expects, and move the directory under `_done/`. `/commit` keeps statuses and Index rows in step — confirm it did rather than assuming.",
        "Run `/update-docs`, then `/commit`."
      ],
      "acceptance": [
        "`uv run pytest tests/test_agent_contract.py -q` green — every rulebook invariant needle survived and the deny set is intact.",
        "`uv run pytest tests/test_doc_links.py -q` green — no link broken by the move to `_done/`, and no new bare `requests/...` token points at something that does not exist.",
        "No sentence anywhere in `CLAUDE.md`, `.claude/agents/data-engineer.md`, `src/ootp_ai/parser/primitives.py`, `src/ootp_ai/parser/header.py` or `tests/test_no_fixed_offsets.py` still claims the scan runs with zero exemptions. Grep for /"zero exemptions/" and confirm the only survivors are the historical ones deliberately left alone.",
        "The ledger gained exactly one new entry and lost none.",
        "Full gate green: `uv run pytest -q`, `uv run ruff check`, `uv run ruff format --check .`, `uv run mypy`. `/update-docs` reports no drift."
      ],
      "commit_note": "Say what the fixed-offset guard actually enforces, and close the request. Land through `/commit`; the PR and the merge stay the operator's."
    }
  ],
  "testing": "THE ACCEPTANCE CONTRACT (bugfix track)/n/nPer `requests/bugfix-requests/README.md:25-26`, done means the red reproduction goes green, a regression test is left behind, and nothing else regresses. Concretely:/n/n1. RED GOES GREEN. `tests/test_no_fixed_offsets.py::test_the_scanner_flags_a_record_relative_subscript` (line 115) is confirmed RED on the current tree — I ran `uv run pytest tests/test_no_fixed_offsets.py -q` and it fails with `AssertionError: a record-relative read at a constant offset passed the guard because it was written as a subscript rather than a call / assert []`, exactly as the RCA records at lines 31-35. Phase 3 turns it green without editing the test./n/n2. THE REGRESSION TEST LEFT BEHIND is not one test but two tiers. The repro itself is the direct guard. `tests/test_fixed_offset_guard_scope.py` (Phase 4) is the meta-guard, and it is the more important of the two: it proves the scan reads real modules from disk, has not silently collapsed its candidate set, and does not fire on the five legitimate shapes that exist in the tree today./n/n3. NOTHING ELSE REGRESSES, in two halves that fail differently./n/n   OFFLINE, and therefore CI-enforced (`.github/workflows/ci.yml:45-57` runs `ruff check`, `ruff format --check`, `mypy`, and `pytest -m /"not gamedata/"`): `tests/test_lookahead.py` (new), `tests/test_fixed_offset_guard_scope.py` (new), `tests/test_no_fixed_offsets.py`, `tests/test_sequential_walk.py`, `tests/test_save_header.py`, `tests/test_parse_players.py`, `tests/test_parse_teams_synthetic.py`, the offline half of `tests/test_parse_world.py`, `tests/test_agent_contract.py`, `tests/test_doc_links.py`, `tests/test_no_leaks.py`, `tests/test_leak_guard_scope.py`. The load-bearing one for this refactor is `tests/test_parse_players.py::test_records_of_different_lengths_all_decode` (line 137) — records spanning 7 to 4,001 bytes, the offline test a constant-stride reimplementation fails./n/n   GAMEDATA, local only, run by the implementer and RECORDED: `tests/test_parse_real_save.py`, `tests/test_byte_accounting.py`, `tests/test_cross_mode_format.py`, the gamedata half of `tests/test_parse_world.py`, and `tests/test_read_only.py`. CI cannot run these — it has no OOTP install and must not have one (ADR 0006) — so the baseline-versus-after comparison is the only evidence the migration preserved behaviour. This is why Phase 1 step 1 captures the baseline BEFORE the first edit./n/nTHE BEHAVIOUR-PRESERVATION PROOF, stated as a number rather than a feeling: the player and team record counts and the byte-accounting residuals from the gamedata suite must be IDENTICAL before Phase 1 and after Phases 2 and 5. Those numbers are derived by walking real saves and, for the standard-mode save, cross-checked against the game's own export — the sanctioned ground truth under ADR 0002, never an in-game screenshot. A single moved number means the framing shifted and the phase is reverted, not rationalised./n/nMUTATION CHECKS, performed by hand and recorded in the commit body (the practice `tests/test_leak_guard_scope.py:196-200` exists because of):/n- Phase 3: paste `data[record_start + 58 : record_start + 62]` into a non-exempt parser module; the whole-tree scan must report it at the right `file:line`. Revert./n- Phase 3: `f.seek(128)` in a parser module still fails, as it did at `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:920`. Revert./n- Phase 4: delete `visit_Subscript`; the new meta-guard module must go red. Restore./n- Phase 4: broaden `EXEMPT_MODULES` to a directory prefix; the exemption-integrity test must go red. Restore./n/nPER-PHASE GATE, identical every time: `uv run pytest`, `uv run ruff check`, `uv run mypy`, plus `uv run ruff format --check .` because CI runs it too (ci.yml:48-49) and it is the easiest way to fail a PR after a green local run. Then `/commit`, which stages deliberately, runs the doc-drift checks and asks before writing. Phases 1 and 2 additionally require a local `uv run pytest -m gamedata -q`./n/nONE HONEST WRINKLE IN THE CADENCE: `uv run pytest` is not fully green at the end of Phases 1 and 2, because the committed repro must stay red until the tree is migrated and the guard widened in Phase 3. The gate for those two phases is therefore /"exactly one failure, and it is `test_the_scanner_flags_a_record_relative_subscript`/". Use `--deselect` for a clean run and a full run to confirm nothing else broke. Do not xfail the repro to make the run tidy — that hides the acceptance contract.",
  "risks": [
    "SEQUENCING TRAP — widening the guard before migrating the tree. The obvious instinct is to fix the scanner first, since that is where the bug is. Do not: the moment `visit_Subscript` exists, `test_no_parser_module_seeks_to_a_fixed_offset` (tests/test_no_fixed_offsets.py:143) goes red on roughly ten legitimate lines across five modules, and the implementer is staring at a broken build with no obvious way back. Migrate (Phases 1-2), then widen (Phase 3). This ordering is the single most important thing in the plan.",
    "THE REFACTOR IS THE REAL RISK, NOT THE SCANNER. Thirteen call sites in the framing and landmark-search code are being rewritten, and framing code fails silently: a walk that finds 15% of the league still returns a tidy list of records. The mitigation is entirely the gamedata baseline captured in Phase 1 step 1 — and CI cannot run it. An implementer without a local OOTP save CANNOT complete Phases 1, 2 or 5 to acceptance and must stop and say so rather than shipping on the offline half.",
    "UNIFYING THE BOUNDS CHECKS IS A BEHAVIOUR CHANGE, however small. `players.py:579` rejects a negative position; `teams.py:603` and `world.py:881` do not. The shared helper takes the strict version, so a call site that today would index with a negative position and get Python's from-the-end semantics will now get `None`. No current caller does this, but say so in a comment and let mypy strict force every new `None` branch rather than papering over one with a cast or an `assert`.",
    "`human_managers.py:244` CURRENTLY HAS NO BOUNDS CHECK. `int.from_bytes` on a short slice returns a smaller number rather than raising, so a truncated buffer would have produced a plausible landmark id. Moving to `peek_u32` makes that impossible — a strict improvement, but it changes the type and forces new branches in `_is_club_landmark` (lines 242-250). Read the whole function before editing; the `all(...)` comprehension at line 247 needs care.",
    "NAMEERROR IN PHASE 5. `_GAP_AFTER_BIRTH_DATE` is defined at `players.py:244`, twenty-five lines BELOW `_AGE_LOOKAHEAD` at line 220. Deriving the lookahead from the gap without moving the gap definition first raises at import and takes the whole suite down at collection.",
    "A GUARD THAT CRIES WOLF GETS LOOSENED — the failure mode the guard's own docstring names (tests/test_no_fixed_offsets.py:9-10) and the reason the RCA forbids the minimal tier. Every rule variant must be checked against the five real shapes that must stay legal: `tail[4]` (players.py:383, human_managers.py:154), `run[base + 1]` (teams.py:624), `pattern[_LENGTH_PREFIX_WIDTH:]` (world.py:844), `self._data[start : start + count]` (primitives.py:140), and a plain `data[position]`. Phase 4 pins all five. If a proposed refinement breaks one of them, the refinement is wrong.",
    "THE EXEMPTION IS THE NEW ATTACK SURFACE. `EXEMPT_MODULES` is the thing a future agent loosens when the guard becomes inconvenient — exactly what `header.py:6-8` warns about. Two defences: the exemption-integrity test (exactly two entries, each resolving to a real file), and the stricter interior rule that makes the exempt module the most disciplined one in the tree. Neither is optional.",
    "THIS WORK CANNOT BE DELEGATED TO THE WRITE-CAPABLE SUBAGENT. `.claude/agents/data-engineer.md`'s Write allowlist denies `tests/`, `CLAUDE.md`, `.github/` and `docs/decisions/` — and `tests/test_agent_contract.py:76-81` asserts it stays that way, because an agent that can edit the tests that catch it is the core failure mode. Phases 3, 4 and 6 are main-thread work. Phases 1, 2 and 5 touch only `src/` and could be delegated, but the handoff must carry the baseline numbers or the delegation buys nothing.",
    "STRAY PROBE FILES. Phase 4 writes a real module into `src/ootp_ai/parser/` and deletes it in `finally`. If an interrupted run leaves one behind, the whole-tree scan reports a violation in a file nobody wrote, which reads as a catastrophic regression. Use `try/finally` with `unlink(missing_ok=True)`, mirroring `tests/test_leak_guard_scope.py:47-53`, and check `git status --porcelain` at the phase gate.",
    "TIMING PRESSURE AGAINST PHASE 6B OF first-sight. The intake notes (BUGFIX_REQUEST.md:73-75) that Phase 6b works directly in the drop-zero region where the wrong shape is most tempting. The temptation is to ship Phase 3 and stop. Phases 4 and 6 are what make the guard trustworthy and its documentation true; a widened guard nobody has seen fail, described by a sentence that is still wrong, has closed the letter of the bug and none of it.",
    "DO NOT LET THE REFACTOR GROW. Tempting adjacents that are explicitly out of scope: folding the duplicated printability check (teams.py:591, world.py:869) into the shared module; unifying the three near-identical `_scan_string` implementations; adding `find_from` to wrap `bytes.find`. None is needed by a migration site, `bytes.find` is a method call the guard never touches, and CLAUDE.md says abstractions appear when their phase does."
  ],
  "files_to_touch": [
    {
      "path": "src/ootp_ai/parser/lookahead.py",
      "change": "NEW. The one sanctioned home for indexing a save buffer. Exports U8_WIDTH/U32_WIDTH/DATE_WIDTH, peek_u8, peek_u32, peek_bytes, peek_date_parts, peek_date, is_zero_run, zero_run_width — all bounds-checked on both ends, all returning None/False rather than raising. Every width inside it is a named constant, because the guard's stricter interior rule forbids a bare literal here."
    },
    {
      "path": "src/ootp_ai/parser/players.py",
      "change": "Delete `_peek_u8`/`_peek_u32`/`_peek_date` (lines 572-592) and import them. Replace `data[cursor.position] == 0` (line 424) and `data[after] == 0` (line 529) with peek_u8. Phase 5: re-express `_BIRTH_DATE_LOOKAHEAD`/`_AGE_LOOKAHEAD` (lines 219-220) as sums of named widths, moving `_GAP_AFTER_BIRTH_DATE` (line 244) above them, and update the comment at lines 216-218."
    },
    {
      "path": "src/ootp_ai/parser/teams.py",
      "change": "Delete `_peek_u32` (lines 596-605) and import it. Replace the flag-byte slice comparison at line 522 with a peek_u8 comparison, and the payload slice at line 590 with peek_bytes."
    },
    {
      "path": "src/ootp_ai/parser/world.py",
      "change": "Delete `_peek_u32` (lines 874-883) and import it. Replace the zero-pad comparison at line 740 with is_zero_run, the inline date decode at lines 744-746 with peek_date_parts (keeping world's own year==0-tolerant validation at lines 747-750), and the two payload slices at lines 759 and 868 with peek_bytes. Leave `pattern[_LENGTH_PREFIX_WIDTH:]` at line 844 alone — a constructed search pattern, not a save buffer."
    },
    {
      "path": "src/ootp_ai/parser/human_managers.py",
      "change": "Replace the zero-scan at line 204 with zero_run_width (keeping the refusal at lines 206-210), and both `int.from_bytes(data[...])` reads in `_is_club_landmark` (lines 244, 248) with peek_u32 — handling the new None branches mypy strict will require."
    },
    {
      "path": "src/ootp_ai/parser/header.py",
      "change": "Add `MAGIC_PREFIX = bytes([LEADING_NULL]) + MAGIC` and rewrite `looks_like_save_file` (line 114) as `data.startswith(MAGIC_PREFIX)` — equivalent given the length guard at lines 112-113 and `_MAGIC_PREFIX_LEN` at line 79. Phase 6: correct the 'zero exemptions' paragraph at lines 5-8 and the bullet at line 13 that warns against the construction this module contained."
    },
    {
      "path": "src/ootp_ai/parser/primitives.py",
      "change": "Phase 6 only, docstring lines 11-13: the 'zero exemptions' claim becomes false when a sanctioned lookahead module exists. Rewrite to say the cursor's structural guarantee is what lets the AST scan hold the search path to one module, itself guarded more strictly. No code change — `Cursor.take` (line 140) stays exactly as it is."
    },
    {
      "path": "tests/test_no_fixed_offsets.py",
      "change": "Add EXEMPT_MODULES; add `visit_FunctionDef` (buffer-name collection from `bytes`-annotated parameters plus direct aliases, with correct restore on exit) and `visit_Subscript` to FixedOffsetVisitor (lines 29-62); add the stricter bare-literal rule that applies inside exempt modules. Leave `visit_Call` and the three pre-existing scanner tests untouched. Phase 6: extend the module docstring to describe both mechanisms and point at the new meta-guard."
    },
    {
      "path": "tests/test_fixed_offset_guard_scope.py",
      "change": "NEW. The meta-guard, modelled on tests/test_leak_guard_scope.py: planted-offender test against the real disk scan with try/finally cleanup, module-count floor (>= 12; 17 today), exemption-integrity test (exactly two entries, each a real file), 'exempt is not exempt from everything', alias-evasion coverage with its limitation documented, and five cry-wolf controls each derived from a real line in the tree."
    },
    {
      "path": "tests/test_lookahead.py",
      "change": "NEW. Offline, synthetic, no game data and no MySQL. Happy path, out-of-bounds None, negative-position None, limit-hit for zero_run_width, and the structural-absence case where peek_date_parts returns (0,0,0) while peek_date returns None."
    },
    {
      "path": "tests/test_parse_players.py",
      "change": "Phase 5: add an offline test that builds a head with make_player_head (tests/fixtures/synthetic.py:242) and asserts the derived `_BIRTH_DATE_LOOKAHEAD` and `_AGE_LOOKAHEAD` land on the birth date and age the fixture wrote, and that they still equal 12 and 19."
    },
    {
      "path": "CLAUDE.md",
      "change": "Line 103: replace 'The fixed-offset ban is the rulebook's, and CI enforces it' with what CI actually enforces after this change — a cursor that cannot seek, plus an AST scan that lets exactly one sanctioned module index a save buffer."
    },
    {
      "path": ".claude/agents/data-engineer.md",
      "change": "Lines 69-74: add the new mechanism to the fixed-offset rule (index a save buffer only through parser/lookahead.py). The literal substring 'fixed offset' must survive (tests/test_agent_contract.py:62), and the Write-allowlist deny set must not be touched (tests/test_agent_contract.py:76-81)."
    },
    {
      "path": ".claude/agents/data-engineer-memory.md",
      "change": "APPEND one dated `verified` entry in the exact shape at lines 23-33, tag harness. Do NOT edit the existing entry at lines 237-241 whose 'zero exemptions' phrase this change dates — a ledger is a log, not a live claim."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/IMPLEMENTATION_PLAN.md",
      "change": "NEW — this plan, opening at `planned · created <today> · decided · next: implement` per the status grammar at requests/bugfix-requests/README.md:45."
    },
    {
      "path": "requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/IMPLEMENTATION_REPORT.md",
      "change": "NEW, Phase 6. Carries the gamedata baseline-versus-after numbers and the recorded mutation-check results — the evidence CI structurally cannot produce."
    },
    {
      "path": "requests/bugfix-requests/README.md",
      "change": "Index row at line 51: Stage cell to `planned` when this plan lands, then `fixed` at Phase 6, with the directory moved under `_done/` per the layout at lines 28-39. /commit keeps statuses and Index rows in step — verify rather than assume."
    }
  ],
  "code_references": [
    {
      "ref": "tests/test_no_fixed_offsets.py:29-62",
      "claim": "`FixedOffsetVisitor` defines only `visit_Call`; `generic_visit` at line 62 walks past every `ast.Subscript` because no handler claims it. This is the proximate cause, exactly as the RCA states."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:115-127",
      "claim": "The committed red reproduction. I ran `uv run pytest tests/test_no_fixed_offsets.py -q` and confirmed it fails today with `AssertionError: ... assert []`. Committed on branch `fix-fixed-offset-guard-subscripts` in `df17337`."
    },
    {
      "ref": "tests/test_no_fixed_offsets.py:143-155",
      "claim": "The real whole-tree scan. `SCAN_ROOT` is `src/ootp_ai` (line 26), it rglobs `*.py` (line 144), refuses to pass vacuously on an empty set (line 145), and builds the repo-relative posix path at line 149 — which is the string `EXEMPT_MODULES` will be matched against."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:11-13",
      "claim": "States that the AST guard 'run[s] with zero exemptions: there is no legitimate seek anywhere for it to have to allow'. This claim becomes false the moment a sanctioned lookahead module exists, and Phase 6 must correct it."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:96-104",
      "claim": "`position` is a read-only property with no setter — the structural half of the ban the RCA credits, and the reason the consuming path needs no work."
    },
    {
      "ref": "src/ootp_ai/parser/primitives.py:140",
      "claim": "`Cursor.take` returns `self._data[start : start + count]` — a buffer subscript with arithmetic that must stay legal. It survives on two independent grounds: the value is an Attribute, not a Name, and `primitives.py` is exempt."
    },
    {
      "ref": "src/ootp_ai/parser/header.py:114",
      "claim": "`looks_like_save_file` reads `data[0] == LEADING_NULL and data[1:_MAGIC_PREFIX_LEN] == MAGIC` — a nonzero literal absolute offset that the widened guard WILL flag. The RCA's survey table did not classify it. Phase 2 rewrites it as `data.startswith(MAGIC_PREFIX)`, which is exactly equivalent given the length guard at lines 112-113."
    },
    {
      "ref": "src/ootp_ai/parser/header.py:5-8",
      "claim": "Claims the module avoids 'indexing offsets 1, 5 and 25 with literals' because the guard runs with 'zero exemptions' — while line 114 indexes offset 1 with a literal. Both halves need correcting in Phase 6."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:553",
      "claim": "`_peek_date(data, position + _BIRTH_DATE_LOOKAHEAD)` — one of the two instances that prompted the request. Uses a NAMED constant, which is why the RCA rules out the literal-vs-Name candidate as too weak."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:557",
      "claim": "`_peek_u8(data, position + _AGE_LOOKAHEAD)` — the second instance."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:219-220",
      "claim": "`_BIRTH_DATE_LOOKAHEAD = 12` and `_AGE_LOOKAHEAD = 19`, raw record-relative constants. Phase 5 re-expresses them as width sums."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:451-456",
      "claim": "The read order that derives both constants exactly: u32 player_id + two u32 name indices = 12, then a 4-byte date plus `_GAP_AFTER_BIRTH_DATE` (3) = 19. This is what makes the Phase 5 re-expression arithmetic rather than a guess."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:244-247",
      "claim": "`_GAP_AFTER_BIRTH_DATE = 3` and its siblings are defined 25 lines BELOW the lookaheads. Phase 5 must move them above or the module raises NameError at import."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:572-592",
      "claim": "`_peek_u8`, `_peek_u32`, `_peek_date` — the richest of the three duplicated lookahead families, and the only one that rejects a negative position (line 579). The shared module takes this stricter form."
    },
    {
      "ref": "src/ootp_ai/parser/players.py:383",
      "claim": "`declared = tail[4]` — a nonzero-literal tuple subscript inside `read_players(data: bytes)`. This is the measured false positive that rules out the wider 'any subscript inside a bytes-param function' rule and forces the annotation-keyed design."
    },
    {
      "ref": "src/ootp_ai/parser/human_managers.py:154",
      "claim": "`declared_records = tail[4]` inside `read_human_manager(data: bytes)` — the second such false positive, confirming the finding is not a one-off."
    },
    {
      "ref": "src/ootp_ai/parser/human_managers.py:242-250",
      "claim": "`_is_club_landmark` reads `int.from_bytes(data[offset : offset + 4], ...)` at line 244 and `data[offset + 4 * slot : ...]` at line 248 with NO bounds check — `int.from_bytes` on a short slice returns a smaller number silently. Migrating to `peek_u32` is a strict safety improvement, and mypy strict will force the new None branches."
    },
    {
      "ref": "src/ootp_ai/parser/teams.py:596-605",
      "claim": "The second duplicate `_peek_u32`, whose docstring says 'A lookahead at the cursor's own position, never at a constant.' It does not reject a negative position, unlike players'."
    },
    {
      "ref": "src/ootp_ai/parser/teams.py:624-625",
      "claim": "`run[base]`, `run[base + 1]`, `run[base + 2 :]` inside `_readings(run: tuple[int, ...])` — arithmetic subscripts on a tuple in a function with no bytes parameter. They must stay legal, and Phase 4 pins that."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:743",
      "claim": "`date_at = offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH` — the only form in the parser that is both constant-derived and self-documenting, and the model Phase 5 copies for players.py."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:744-746",
      "claim": "An inline date decode duplicating players' `_peek_date`. Note world validates with `year != 0` tolerance at line 749 while players' `_peek_date` rejects it (players.py:592) — which is why `lookahead.peek_date_parts` returns raw parts and leaves the judgement to the caller."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:874-883",
      "claim": "The third duplicate `_peek_u32`. Three near-identical implementations across three modules are the RCA's evidence that the seam already wanted to exist."
    },
    {
      "ref": "src/ootp_ai/parser/world.py:844",
      "claim": "`pattern[_LENGTH_PREFIX_WIDTH:]` inside `_find_unique(data: bytes, pattern: bytes, ...)`. A bytes-annotated parameter that is NOT a save buffer, sliced for an error message. The proposed rule does not fire on it because the index carries neither arithmetic nor a nonzero literal — a real constraint the rule had to satisfy."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:196-238",
      "claim": "The precedent for Phase 4: this repo's other scan guard needed a separate module proving it can fail, after a mutant scanning zero files left all 18 tests green. The planted-leak test and the coverage floor are the two patterns to reuse."
    },
    {
      "ref": "tests/test_leak_guard_scope.py:40-53",
      "claim": "The `untracked_file` contextmanager — writes a real probe into the working tree and always unlinks it in `finally`. Phase 4's planted-offender test needs the same discipline, since its probe lands inside `src/ootp_ai/parser/`."
    },
    {
      "ref": "tests/test_agent_contract.py:53-73",
      "claim": "`test_rulebook_invariants_survive` requires the literal substring 'fixed offset' (line 62) plus nine siblings to remain in the agent definition. This constrains the Phase 6 edit to data-engineer.md."
    },
    {
      "ref": "tests/test_agent_contract.py:76-81",
      "claim": "The data-engineer's deny set must keep `tests/`, `.github/`, `ops/`, `CLAUDE.md`, `docs/decisions/`. This is why Phases 3, 4 and 6 cannot be delegated to the write-capable subagent — it is not allowed to edit the guard that catches it."
    },
    {
      "ref": "tests/test_agent_contract.py:84-95",
      "claim": "Every ledger entry must open `- **YYYY-MM-DD**` and carry a backticked label from {measured, verified, inferred, assumed, unconfirmed}. Fixes the shape of the Phase 6 memory append."
    },
    {
      "ref": ".claude/agents/data-engineer-memory.md:23-33",
      "claim": "The entry format, and the instruction that the file is appended to. Line 3-4: 'append to it when something costs you time'. Phase 6 appends; it does not edit line 241's now-dated 'zero exemptions' phrase."
    },
    {
      "ref": "docs/data-access.md:275-282",
      "claim": "'The record head is fixed for 37 bytes' is labelled `verified` against every one of 18,072 `retired = 0` export rows, exact and not sampled. Phase 5's width-sum derivation rests on this, so no verification phase is required ahead of it."
    },
    {
      "ref": "docs/data-access.md:284-287",
      "claim": "The drop-zero measurement behind the repro's `58`: `last_team_id` is elided when zero, so `team_id` sits at record+58 for 86.9% of players. This is why the repro's constant is a real hazard rather than an arbitrary number."
    },
    {
      "ref": "CLAUDE.md:103",
      "claim": "'The fixed-offset ban is the rulebook's, and CI enforces it' — the claim the RCA shows is stronger than the mechanism. Phase 6 corrects it as a consequence of what the guard ends up covering, not instead of widening it."
    },
    {
      "ref": ".claude/agents/data-engineer.md:69-74",
      "claim": "The rulebook's fixed-offset ban, calling seeking code 'a blocker, not a style note', with the measured evidence (the same ratings block at 43 bytes from one anchor and 107 in another)."
    },
    {
      "ref": ".github/workflows/ci.yml:45-57",
      "claim": "CI runs `ruff check`, `ruff format --check`, `mypy`, and `pytest -m /"not gamedata/"`. The gamedata half never runs in CI, which is why the behaviour-preservation baseline must be captured and recorded locally."
    },
    {
      "ref": "pyproject.toml:91-95",
      "claim": "mypy strict over both `src` and `tests`. Every parameter in `src/` is therefore annotated, which is what makes the annotation-keyed guard rule non-evadable without failing a second, independent check."
    },
    {
      "ref": "tests/test_parse_players.py:137-156",
      "claim": "`test_records_of_different_lengths_all_decode` — records spanning 7 to 4,001 bytes, offline. The one offline test a constant-stride reimplementation of the walker fails, and therefore the most load-bearing regression check for the Phase 1-2 migration."
    },
    {
      "ref": "tests/fixtures/synthetic.py:242-256",
      "claim": "`make_player_head` takes explicit `birth=` and `age=` keywords — everything Phase 5's offset-derivation test needs, offline and with no game data in git (ADR 0006)."
    },
    {
      "ref": "requests/bugfix-requests/README.md:45",
      "claim": "Status grammar `intake -> diagnosed -> planned -> fixed`, and lines 25-26 define done as 'the red reproduction goes green and a regression test is left behind'."
    },
    {
      "ref": "requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md:928",
      "claim": "The standing rule that every phase re-runs `test_read_only.py` and `test_no_fixed_offsets.py` — the two unrecoverable-failure guards. This plan inherits it in every phase's acceptance."
    }
  ],
  "open_questions": [
    "Does the sanctioned-lookahead rule warrant an ADR? It is a structural invariant every future parser change passes through, and CLAUDE.md routes 'decisions and their costs' to `docs/decisions/`. My recommendation: yes, a short ADR, because the next agent who finds the guard inconvenient will look for the reasoning and a test docstring is the wrong place to keep it. Against: the repo has nineteen ADRs and this is arguably an elaboration of the existing ban rather than a new decision. The implementer should raise it at the Phase 6 gate rather than deciding silently either way.",
    "Should `peek_bytes` return `bytes | None` or raise on an out-of-range read? The plan proposes `None` for consistency with the three existing `_peek_*` families, but every call site currently guards the length itself first (teams.py:588, world.py:866), so a raising version would surface a truncated file more loudly. Consistency wins in this plan; flag it if a call site ends up ignoring the None.",
    "Should the guard also recognise `bytearray` and `memoryview` annotations as buffers? Nothing in the tree uses either today (every buffer parameter is annotated `bytes`), so adding them now is speculative — but a future streaming reader would evade the rule by annotation alone. Cheap to add as a set of accepted annotation names; the implementer should decide whether adding an unused branch or leaving a known gap is the smaller sin.",
    "The alias-tracking in `visit_FunctionDef` covers `buf = data` but not `buf = data[start:]` or a buffer passed into a nested closure. Phase 4 documents the limit with a test. Is documenting it sufficient, or should the rule flag ANY subscript on a local assigned from a subscript of a buffer? The latter would catch the derived-slice case at the cost of a rule nobody can hold in their head.",
    "`world.py:740`'s `data[pad_at:length_at]` and `world.py:844`'s `pattern[_LENGTH_PREFIX_WIDTH:]` both pass the proposed rule on their own merits (no arithmetic, no nonzero literal). Phase 2 migrates the first anyway for uniformity and leaves the second. That asymmetry is defensible — one reads a save buffer, one slices a constructed pattern — but it means 'no buffer subscripts outside the seam' is a Phase-2 goal rather than something the guard enforces. Worth naming explicitly in the guard's docstring so nobody later reads the gap as an oversight."
  ]
}
```
