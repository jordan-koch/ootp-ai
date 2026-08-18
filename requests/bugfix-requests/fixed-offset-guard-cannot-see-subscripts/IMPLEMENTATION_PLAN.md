> **Status:** planned · created 2026-08-18 · decided · next: implement

# Implementation Plan — Give buffer indexing one home, and let the guard key on it

> **One-line goal:** the fixed-offset ban stops depending on which syntax an author reached
> for · **Target component:** `src/ootp_ai/parser/lookahead.py` (new), five parser modules,
> `tests/test_no_fixed_offsets.py`

## 1. Onboarding — read these first

This is a **bugfix**, and the thing being fixed is a guard rather than a parser.
`tests/test_no_fixed_offsets.py` is CI's half of the project's most load-bearing
invariant. It flags `.seek(<literal>)` and `unpack_from(..., <literal>)` — both
`ast.Call` — and never inspects an `ast.Subscript`, which is the spelling this parser's
byte-slicing style actually produces. Nothing in the tree is mis-parsed today; the bug is
about what the **next** change can get away with.

**What the RCA decided, and what this plan adds on top.** The RCA settled the Root tier
(one sanctioned module may index a save buffer) and the Hardening tier (re-express the two
raw constants). Phase 4 (a meta-guard) and Phase 6 (constant folding) are **this plan's
additions**, both argued below. Everything else is discharging the RCA.

| Read | Why |
|---|---|
| `requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md` | The decided artifact. **Consume it, do not re-open it.** The verdict, the two-read-paths table, the refuted docs-only option, and the three fix tiers. |
| `requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/BUGFIX_REQUEST.md` | Context. Its survey table is the false-positive budget the new rule must respect — **with one correction, below.** |
| `tests/test_no_fixed_offsets.py` | 156 lines, read in full. Both the file being fixed and the file holding the red repro. |
| `src/ootp_ai/parser/primitives.py` | The other read path. `Cursor` has no `seek` and `position` is read-only — the half that is already airtight. Its docstring's "zero exemptions" claim becomes false in Phase 3. |
| `src/ootp_ai/parser/players.py` | Carries the two instances that prompted the request, and the three-function peek family the seam absorbs. |
| `src/ootp_ai/parser/world.py` | Holds the model form to copy (`offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH`) and three sites to move. |
| `tests/test_leak_guard_scope.py` | The precedent for Phase 4. This repo has already been bitten by a scan guard that ran but proved nothing. |
| `tests/test_agent_contract.py` | Constrains the Phase 7 rulebook edit: nine literal substrings must survive, and the deny set must not move. |

**A correction to the intake's survey.** It classified every current direct-buffer read as
benign or guard-relevant and **missed one**: `src/ootp_ai/parser/header.py:114` reads
`data[0] == LEADING_NULL and data[1:_MAGIC_PREFIX_LEN] == MAGIC` — a literal absolute
offset, in the module whose own docstring (`:5-8`) claims it avoids "indexing offsets 1, 5
and 25 with literals". The widened guard **will** flag it. Phase 2 rewrites it as
`data.startswith(MAGIC_PREFIX)`, which is exactly equivalent given the length guard two
lines above.

## 2. Architecture map

The parser has **two read paths**, and the ban is enforced on only one of them.

```
consuming path          Cursor (primitives.py)        no seek, no position setter
                        -> structurally cannot seek   AIRTIGHT

search / lookahead      ~21 direct data[...] sites    guarded by NOTHING today
path                    across 5 modules              <- this plan's target
                        3 duplicate _peek_u32
```

After this plan:

```
search / lookahead      parser/lookahead.py           the ONLY sanctioned indexer
path                    every other module imports it
                        AST guard flags a buffer      keyed on MODULE, not syntax
                        subscript anywhere else
```

The guard becomes **location-keyed**: a subscript whose value is a `bytes`-annotated
parameter, carrying arithmetic or a nonzero literal in its index, is a violation unless the
module is on a two-entry allowlist (`lookahead.py`, `primitives.py`). Inside those two, a
**stricter** interior rule applies — no bare nonzero integer literal in a subscript index —
so the sanctioned module cannot become a laundry.

## 3. Phased implementation

**Ordering is load-bearing: MIGRATE FIRST, THEN WIDEN.** Widening before migrating turns
the real whole-tree scan red on roughly ten legitimate lines across five modules and hands
the implementer a broken build with no obvious way back.

Every phase ends at a `/commit` gate on `uv run pytest`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run mypy` — and re-runs
`uv run pytest -m gamedata tests/test_read_only.py`, because ADR 0001 is re-checked at
every gate in this plan, not once.

---

### Phase 0 — Confirm the oracle exists, before anything else

**Goal.** This plan's only proof that the migration changed nothing is a local `gamedata`
run, and CI cannot provide it — `.github/workflows/ci.yml` runs
`pytest -m "not gamedata"`. If the saves are not on this machine, **no phase of this plan
is completable**, and discovering that at Phase 2 wastes the migration.

**Steps.**
1. Run `uv run pytest -m gamedata -rs` — **without `-q`**, so skips are visible.
2. Record the **passed count** and the **skip count**.

**Acceptance.** The passed count is greater than zero and the skip count is zero. **If the
run reports skips instead of passes, STOP and hand back to the operator** — the saves are
unavailable and this plan cannot be verified. *(Measured 2026-08-18: the saves are present
on this machine, so this is a guard against a different machine, not an expected stop.)*

**Commit note.** No commit. This is a precondition check.

---

### Phase 1 — Land `lookahead.py` as a pure addition

**Goal.** Capture the baseline, then add the seam with **no caller changes**, so nothing
can regress.

**Steps.**
1. Record the **gamedata baseline** in numbers a later phase can diff: passed count, and
   the record counts and byte-accounting figures the player and team walks report.
2. Write `src/ootp_ai/parser/lookahead.py`. Surface:
   `peek_u8`, `peek_u32`, `peek_bytes`, `peek_date_parts`, `zero_run_width`,
   `peek_length_prefixed_ascii`, plus the declared spans `U8_WIDTH`, `U32_WIDTH`,
   `DATE_WIDTH`, `LENGTH_PREFIX_WIDTH`, `DAY_WIDTH`, `MONTH_WIDTH`.
   - Take the **strictest** existing form: `players.py`'s `_peek_u32` rejects a negative
     position; `teams.py`'s and `world.py`'s do not. The shared one rejects it.
   - `peek_date_parts` returns **raw parts**, not a validated date — `world.py` tolerates
     `year == 0` where `players.py` rejects it, so the judgement stays with the caller.
   - **`peek_length_prefixed_ascii(data, position, limit)` does the prefix read, the bounds
     check and the printability filter in one call**, returning `(length, end)`. This
     collapses both `_scan_string` bodies to one line and removes the `position + 4`
     arithmetic that Phase 6's own rule would otherwise flag.
3. Write `tests/test_lookahead.py` — offline, synthetic, no game data, no MySQL. Happy
   path, out-of-bounds `None`, negative-position `None`, `zero_run_width` hitting its
   limit, and the structural-absence case where `peek_date_parts` returns `(0, 0, 0)`.

**Acceptance.**
- `uv run pytest tests/test_lookahead.py` green.
- **No bare nonzero integer literal appears in any subscript index in `lookahead.py`** —
  checkable at this gate rather than discovered at Phase 3, which is why the width
  constants are declared now.
- The three `_peek_u32` definitions still exist. This phase **adds**; it does not delete.
- `uv run pytest` reports **exactly one** failure, the Phase 3 repro. **Do not `xfail` it**
  — that hides the acceptance contract.
- Full lint/format/mypy clean; ADR 0001 re-checked.

**Commit note.** *"Add the sanctioned lookahead seam, with nothing yet using it."*

---

### Phases 2a–2d — Rewire the five modules, one module per commit

**Goal.** Leave **zero** direct buffer subscripts under `src/ootp_ai/` outside
`lookahead.py` and `primitives.py`.

**Split into four commits — 2a `players.py`, 2b `teams.py`, 2c `world.py`,
2d `human_managers.py` + `header.py`** *(operator's disposition, G3)*. Each module is
independently complete, so a half-migrated tree is never entered, and four small reverts
beat one large one on the phase carrying the highest silent-failure risk in the plan.

**Goal, stated honestly.** Behaviour-preserving **on every input any current caller
produces, with exactly three deliberate widenings**, each named and individually argued in
its commit body:

| Widening | Why no current caller reaches the changed branch |
|---|---|
| Unified negative-position rejection | `teams.py`/`world.py` callers never pass a negative position; the shared form returns `None` where Python would have indexed from the end. |
| `_is_club_landmark` gains `None` branches | It currently calls `int.from_bytes` on a possibly-short slice with **no bounds check**, which returns a smaller number silently. mypy strict will force the branches. A strict safety improvement. |
| `looks_like_save_file` → `startswith` | Exactly equivalent given the length guard at `header.py:112-113`. |

**Steps, per module.** Delete the local `_peek_*`, import from `lookahead`, replace each
direct subscript with the corresponding call. `world.py:844`'s
`pattern[_LENGTH_PREFIX_WIDTH:]` is **left alone** — it slices a constructed search
pattern, not a save buffer.

**Delegation.** Only the `src/` rewiring may be handed to the `data-engineer` subagent, and
**2d's `tests/test_save_header.py` addition may not** — `tests/` is in that agent's deny
set. Say which half in the handoff, and repeat the read-only-git constraint: this is the
phase most likely to want a revert.

**Acceptance, per slice.**
- `uv run pytest` and `uv run pytest -m gamedata -rs` green **with zero edits to any
  existing parser test.** If a parser test had to change, the refactor was not
  behaviour-preserving — **revert it, do not accommodate it.**
- The gamedata run reports the **same passed count as the Phase 0/1 baseline and zero
  skips** — a green exit code is not enough, because a skipped run also exits green.
- The record counts and byte-accounting numbers reproduce the baseline **exactly.** One
  changed number means the framing moved.
- Offline, the sharpest single check is
  `tests/test_parse_players.py::test_records_of_different_lengths_all_decode` — the one
  offline test a constant-stride reimplementation fails.
- **Verification of the sweep is an AST check, not a grep.** A bare
  `grep -rn 'data\[' src/ootp_ai/` is **unsatisfiable** — `primitives.py:140`
  (`self._data[...]`) and `header.py:13` (a docstring) both match by design. Instead, at
  the 2d gate run a throwaway script under `var/` (gitignored, never committed)
  implementing the Phase 3 predicate over `src/ootp_ai/`, and assert zero hits outside the
  two allowlisted modules.

**Commit notes.** *"Move &lt;module&gt; onto the lookahead seam."* Each names its widenings.

---

### Phase 3 — Widen the guard, and give it callable seams

**Goal.** Make the ban independent of syntax. **This is the phase that discharges the
bugfix track's acceptance contract.**

**Steps.**
1. Add `visit_FunctionDef` to `FixedOffsetVisitor`: collect the names of parameters
   annotated `bytes`, plus direct aliases (`buf = data`). Restore the previous set on exit
   — nested functions must not leak their buffer names outward.
2. Add `visit_Subscript`: flag a subscript whose value is a collected buffer name **and**
   whose index carries a `BinOp` or a nonzero integer literal. A lone `Name` index is
   legal *(G6 — accept the asymmetry; `pattern[_LENGTH_PREFIX_WIDTH:]` carries no
   constant)*.
3. Keep a narrow **bare-name fallback** over `{data, buf, buffer}` for unannotated
   parameters, skipping string-constant indices *(G4 — ship both mechanisms, each with its
   own failing witness; the repro fixture is unannotated, so an annotation-only rule would
   turn it green by accident)*. The accepted-annotation set stays `{bytes}` *(G5)*.
4. Add `EXEMPT_MODULES = ("src/ootp_ai/parser/lookahead.py", "src/ootp_ai/parser/primitives.py")`,
   matched against the repo-relative posix path the scan already builds. Inside them, apply
   the **stricter interior rule**: no bare nonzero integer literal in a subscript index.
5. **Extract two module-level callables** — `parser_modules() -> list[Path]` (the rglob
   plus the non-empty assertion) and `parser_module_violations() -> list[str]` (the loop) —
   and reduce `test_no_parser_module_seeks_to_a_fixed_offset` to
   `violations = parser_module_violations(); assert not violations, ...` with its message
   text unchanged. **Without this, Phase 4 cannot be written at all**: the whole-tree scan
   is currently inline and asserts rather than returning, so there is nothing to call. This
   is the precedent `tests/test_no_leaks.py` already sets by exposing its own seams.

**Acceptance.**
- `tests/test_no_fixed_offsets.py` **fully green**, including
  `test_the_scanner_flags_a_record_relative_subscript`. **Its assertion must be untouched**
  — rewriting it to fit the implementation voids the contract.
- The three pre-existing scanner tests pass **unmodified**. None of their fixtures contains
  a subscript, so if any needed editing the new rule is wrong.
- `test_no_parser_module_seeks_to_a_fixed_offset` green over the whole real tree with
  **zero false positives** — the proof Phase 2 actually finished. **If it fires on a benign
  site the RULE is wrong, not the site. Do not add an exemption to make it pass.**
- **SEEN TO FAIL, recorded verbatim in the commit body:** add
  `def read_team_id(data: bytes, record_start: int) -> int: return int.from_bytes(data[record_start + 58 : record_start + 62], "little")`
  to a parser module, confirm the whole-tree scan goes red, remove it.
- **Second mutation, also recorded:** `f.seek(128)` in a parser module still fails, proving
  the pre-existing call rule survived the new handlers.
- `uv run pytest` now **fully green with no deselects.**

**Commit note.** *"Flag a record-relative buffer subscript, wherever it is spelled."*

---

### Phase 4 — Guard the guard

**Goal.** Make the widened scan **seen to fail** and **seen not to cry wolf**.

**Not gated, and that is deliberate.** The meta-audit noted the asymmetry with Phase 6 and
asked for it to read as a decision: **this repo has been bitten twice by a scan guard that
ran and proved nothing** — the leak guard's no-op mutant left all 18 tests green, and the
batching guard exited 1 on a clean checkout for its whole life. A third instance is not a
discretionary nicety.

**Steps.** New `tests/test_fixed_offset_guard_scope.py`, modelled on
`tests/test_leak_guard_scope.py`:
1. **Planted-offender test** against the real disk scan via `parser_module_violations()`,
   writing a probe into `src/ootp_ai/parser/` and removing it in `finally` — the
   `untracked_file` contextmanager pattern.
2. **Coverage floor** — `len(parser_modules()) >= 12` (17 today), so a scan that starts
   finding nothing goes red.
3. **Allowlist integrity** — exactly two entries, each naming a file that exists.
4. **Exempt is not exempt from everything** — the interior bare-literal rule still fires
   inside an allowlisted module.
5. **Cry-wolf controls**, each derived from a real line and named with it:
   `players.py:383` (`tail[4]`), `teams.py:624` (`run[base + 1]`), `world.py:844`
   (`pattern[_WIDTH:]`), plus the `startswith` form.
6. **Known-residual controls, pinned rather than left implicit** — a local hoist
   (`at = start + 58; data[at : at + 4]`) and an attribute value (`self._buf[start + 58]`)
   are asserted **not** flagged, with a comment saying each is a documented hole and why
   closing it needs dataflow analysis inside a test module. Pinning the hole is what stops
   the next reader assuming there isn't one.

**Acceptance.** Module green; `git status --porcelain` clean afterwards — a leftover probe
would now also trip `tests/test_no_leaks.py`, which enumerates untracked files. Removing
`visit_Subscript` turns this module red; broadening the allowlist turns the integrity test
red. **Both mutants die, recorded, then restored.**

**Commit note.** *"Prove the widened guard can fail, and does not cry wolf."*

---

### Phase 5 — Discharge the Hardening tier

**Goal.** The two constants that motivated the request stop being raw record-relative
offsets and become the self-documenting form the parser already uses at `world.py:743`.

**Steps.** Re-express `_BIRTH_DATE_LOOKAHEAD = 12` as
`_PLAYER_ID_WIDTH + 2 * _NAME_INDEX_WIDTH` and `_AGE_LOOKAHEAD = 19` as
`_BIRTH_DATE_LOOKAHEAD + DATE_WIDTH + _GAP_AFTER_BIRTH_DATE`. The derivation is arithmetic,
not a guess: the head read order gives `u32 player_id` + two `u32` name indices = 12, then
a 4-byte date plus a 3-byte gap = 19. **Move `_GAP_AFTER_BIRTH_DATE` above them** or the
module raises `NameError` at import.

**Acceptance.**
- A new **offline** test asserts the derived offsets land on the birth date and age the
  synthetic fixture wrote, and that both still equal 12 and 19.
- Break one addend, confirm the **offline** pin goes red **before** any gamedata test does,
  then revert. The offline pin must be the first line of defence.
- The gamedata run reproduces the baseline counts exactly, with zero skips.
- No bare integer literal remains as an addend to a position in `players.py` outside a
  width or gap constant **definition**.
- **No epistemic label was strengthened** — this phase consumed a `verified` claim and
  added none.

**Commit note.** *"Derive the player head offsets from named field widths."*

---

### Phase 6 — Fold module constants *(operator disposed: SHIP IT)*

**Goal.** Close the one hazard a subscript rule structurally cannot see: a record-relative
constant handed as an **argument** — `peek_u32(data, position + _TEAM_ID_OFFSET)` — which
is exactly the shape at `players.py:553,557` that prompted the request. Without it, the
next author can reintroduce the defect and pass.

**This is the plan's addition, not the RCA's**, and it was gated. The operator disposed it
affirmatively; it ships.

**Steps.** Over calls into the lookahead surface, judge the position argument:
1. Build the module-level constant table (bare int assignments), resolving imports with
   `asname` handling.
2. **A `Name` not defined at module level is SKIPPED, not flagged** — it is a
   walk-computed local, which is the legal case. Only a module-resolvable `Name` is judged.
3. **A bare nonzero int literal in the argument is always flagged**, regardless of scope.
4. **`Mult` is legal iff at least one operand is a declared span and neither is a bare
   nonzero literal** — so `slot * U32_WIDTH` passes and `slot * 4` does not.

**Fixtures, each with its own witness:** `FOLDED_OFFENDER`, `WIDTH_SUM_INNOCENT`,
`DERIVED_INNOCENT`, `LOCAL_POSITION_INNOCENT` (`world.py:752`'s exact shape), and
`SLOT_ARITHMETIC_INNOCENT` (`human_managers._is_club_landmark`'s post-Phase-2 shape).

**Acceptance.** All five fixtures behave as named; the whole-tree scan stays green; the
residual (a position computed into a local still evades it) is **written into the guard's
docstring**, not left implicit.

**Commit note.** *"Judge the constant handed to a lookahead, not just the subscript."*

---

### Phase 7 — Make every written claim about the ban true

**Goal.** The RCA's closing position: the docs get corrected as a **consequence** of what
the guard covers, not instead of widening it.

**Steps.**
1. `CLAUDE.md:103` — replace *"the fixed-offset ban is the rulebook's, and CI enforces it"*
   with what CI now actually enforces: a cursor that cannot seek, plus an AST scan that
   lets exactly one sanctioned module index a save buffer.
2. `src/ootp_ai/parser/primitives.py:11-13` and `src/ootp_ai/parser/header.py:5-8` — both
   assert "zero exemptions", which Phase 3 falsifies. Rewrite; no code change.
3. `.claude/agents/data-engineer.md` — add the mechanism to the fixed-offset rule. **The
   literal substring `fixed offset` must survive** and the Write-allowlist deny set must
   not be touched, or `tests/test_agent_contract.py` goes red.
4. **Write a short ADR** *(operator disposed: yes, G1)* recording the sanctioned-lookahead
   rule — why annotation-grounded, why two modules, why the interior rule. Add it to the
   ADR index. `docs/decisions/` is main-thread only.
5. Append one dated `verified` entry to `.claude/agents/data-engineer-memory.md`. **Do not
   edit the existing entry whose "zero exemptions" phrase this change dates** — a ledger is
   a log, not a live claim.
6. Write the implementation report, carrying the baseline-versus-after numbers and the
   recorded mutation results — evidence CI structurally cannot produce:

   ```
   requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/IMPLEMENTATION_REPORT.md
   ```

**Acceptance.** No document claims coverage the guard does not have. `test_agent_contract`
green. The request reaches `fixed` and moves to `_done/`.

**Commit note.** *"Make the ban's documentation match its mechanism."*

## 4. Testing & verification

**The red repro is the spine:** `test_the_scanner_flags_a_record_relative_subscript`, red
at `df17337`, green at Phase 3, and its assertion is never edited.

**The gamedata baseline is the only proof the migration changed nothing**, and CI cannot
provide it. Every gamedata gate is **count-based, not exit-code-based** — a skipped run
exits green, so acceptance is "same passed count as baseline, zero skips", run with `-rs`.

**Seen to fail, three times, each recorded:** the widened rule (Phase 3), the meta-guard's
two mutants (Phase 4), and the offset derivation (Phase 5).

**Deliberately not tested, and named in the guard's docstring rather than left implicit:**
a position hoisted into a local before indexing; an attribute-valued buffer
(`self._buf[...]`); a buffer annotated `bytearray` or `memoryview` (nothing in the tree
uses either); a parameter renamed away from the `{data, buf, buffer}` fallback set while
also unannotated.

## 5. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Migrate first, widen second** | Widening first turns the real scan red on ~10 legitimate lines across 5 modules and hands the implementer a broken build. |
| D2 | **Location-keyed rule, not syntax-keyed** | The RCA rejected literal-vs-Name as too weak — the real instances use *named* constants. Keying on the module makes the rule statable in one sentence. |
| D3 | **Exactly two allowlisted modules** | `lookahead.py` because it is the seam; `primitives.py` because `Cursor.take` indexes its own buffer. Both carry the stricter interior rule so neither becomes a laundry. |
| D4 | **No per-site exemption registry** | A registry would let the guard be satisfied by adding entries, which is how a guard stops being one. The cost is that this plan cannot be completed without local saves — hence Phase 0. |
| D5 | **The census phase is deliberately dropped** | One planner proposed pinning the 21-site inventory as a test. After Phase 3 a new buffer-indexing site is a *guard violation* rather than an inventory drift, so the pin would duplicate the guard — and it would fire on legitimate first-sight Phase 6b work. The 21 figure is a starting inventory, not an invariant. |
| G1 | **Write a short ADR** | Operator-disposed. The allowlist is genuinely new and its rationale decays into folklore without a decision record. |
| G2 | **Ship Phase 6** | Operator-disposed. Phase 5 makes today's two instances defensible; only Phase 6 makes the *class* checked. |
| G3 | **Split Phase 2 by module** | Operator-disposed. Four small reverts beat one large one on the riskiest phase. |
| G4 | **Annotation rule *and* bare-name fallback** | Operator-disposed en bloc. The repro fixture is unannotated; an annotation-only rule would turn it green by accident. |
| G5 | **Accepted annotations stay `{bytes}`** | Operator-disposed en bloc. Nothing in the tree uses `bytearray`/`memoryview`; the gap is named in the docstring. |
| G6 | **A lone-`Name` index stays legal** | Operator-disposed en bloc. "No buffer subscripts outside the seam" is a Phase-2 *discipline* goal; the guard enforces the narrower "no arithmetic or literal buffer subscript outside the seam". |

## 6. Risks & gotchas

1. **Phase 2 is the silent-failure risk, and CI cannot see it.** Mitigated by the
   count-based gamedata baseline, the four-way split, and the rule that no existing parser
   test may be edited.
2. **`header.py:114` was missed by the intake survey.** It is a literal absolute offset the
   widened guard will flag. Phase 2d rewrites it — if that is skipped, Phase 3 goes red on
   a line nobody expected.
3. **`_GAP_AFTER_BIRTH_DATE` is defined *below* the lookaheads.** Phase 5 must move it or
   the module raises `NameError` at import.
4. **mypy is strict over `tests/` too.** The new visitor stack and the meta-guard need
   complete annotations.
5. **The guard being modified is the thing under test.** Every phase re-runs the real
   whole-tree scan, and Phase 4 exists because a guard that only runs proves nothing.
6. **A leftover Phase 4 probe would be committed.** It lands inside `src/ootp_ai/parser/`;
   the `finally` cleanup is not optional, and `test_no_leaks.py` now sees untracked files.

## 7. Files to touch (checklist)

- [ ] `src/ootp_ai/parser/lookahead.py` — **new**, the sanctioned indexer
- [ ] `src/ootp_ai/parser/players.py` · `teams.py` · `world.py` · `human_managers.py` · `header.py` — rewired, one commit each (2a–2d)
- [ ] `src/ootp_ai/parser/primitives.py` — Phase 7 docstring only, **no code change**
- [ ] `tests/test_no_fixed_offsets.py` — the visitor, the allowlist, the two extracted callables
- [ ] `tests/test_fixed_offset_guard_scope.py` — **new**, the meta-guard
- [ ] `tests/test_lookahead.py` — **new**, offline unit tests
- [ ] `tests/test_save_header.py` — a `looks_like_save_file` unit test (**main-thread**, 2b)
- [ ] `tests/test_parse_players.py` — the Phase 5 offline offset pin
- [ ] `CLAUDE.md` · `.claude/agents/data-engineer.md` · `.claude/agents/data-engineer-memory.md` — Phase 7
- [ ] `docs/decisions/` — the new ADR, plus its index row
- [ ] `requests/bugfix-requests/README.md` — Index row to `fixed`, directory to `_done/`

## 8. Conventions (bake these in)

- **The game is read-only.** Every gate re-runs `test_read_only.py`. Nothing here opens a
  save for writing; the migration touches only how buffers already in memory are indexed.
- **Never seek to a fixed offset** — the invariant this plan is *strengthening*, so the
  implementation must not violate it while doing so.
- **`tests/` is in the `data-engineer` subagent's deny set.** Every test file here is
  main-thread authored. Only the `src/` half of Phase 2 may be delegated.
- **Subagents get read-only git** — never `checkout`/`reset`/`restore`/`clean`/`stash`.
  Phase 2 is the phase most likely to want a revert; it goes through the operator.
- **Commits go through `/commit` only.** Never `--amend`, never `--no-verify`, never a push
  to `main`.
- **No OOTP game data in git.** Every fixture here is synthetic; the `var/` sweep script is
  gitignored and never committed.

## 10. Code-grounding verification

The panel's code-grounded adversary and the meta-audit verified every cited reference
against the tree at `df17337`. **41 citations checked; 1 blocker and 14 majors raised, all
applied above.** The corrections that changed the plan's substance:

| Cited | Verdict |
|---|---|
| Phase 4 calls a whole-tree scan callable | **Corrected — it does not exist.** The scan is inline and asserts; Phase 3 now extracts `parser_modules()` and `parser_module_violations()`. |
| The intake's survey is the complete false-positive budget | **Corrected — `header.py:114` was missed.** A literal absolute offset the widened guard will flag. |
| `grep -rn 'data\[' src/ootp_ai/` returns hits only in `lookahead.py` | **Corrected — unsatisfiable.** `primitives.py:140` and `header.py:13` match by design; replaced with an AST predicate check. |
| Phase 2 is "behaviour-preserving by construction" | **Corrected —** it prescribes three deliberate widenings, now named and individually argued. |
| Phase 2 is delegable to the subagent | **Corrected —** its `tests/test_save_header.py` step is in the deny set; split into a delegable `src/` half and a main-thread test half. |
| gamedata gates are green/red | **Corrected —** a skipped run also exits green; every gate is now count-based with zero skips required. |
| `peek_length_prefixed` returning `length` | **Corrected —** it forced callers to write `position + 4`, which Phase 6 would flag; returns `(length, end)`. |

## References

- `requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md` — the decided artifact
- `requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/reviews/plan-proposals.md` — the three planners, unfiltered
- `requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/reviews/plan-adversarial.md` — 27 adversary findings, 19 meta-audit findings, 6 gated decisions
- `tests/test_leak_guard_scope.py` — the meta-guard precedent
- `tests/test_agent_contract.py` — what the Phase 7 rulebook edit may not break
