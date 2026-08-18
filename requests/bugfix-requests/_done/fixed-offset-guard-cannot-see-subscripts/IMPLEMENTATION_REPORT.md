> **Status:** fixed · created 2026-08-18 · decided · next: commit

# Implementation Report — The fixed-offset guard now sees the spelling this codebase uses

> **One-line outcome:** a ban that was enforced against `.seek(128)` and blind to
> `data[start + 58 : start + 62]` now keys on **location** — one sanctioned module may index
> a save buffer — and says out loud what it still cannot see · **Acceptance:** the bugfix
> contract met at Phase 3, all eight phases landed · **Branch:**
> `fix-fixed-offset-guard-subscripts`
>
> The corrections to `CLAUDE.md`, `header.py` and `primitives.py` were deliberately **not**
> made until Phase 7, because they are a consequence of what the guard ended up covering.
> Making them first would have been the cheap fix the RCA refused.

## 1. Acceptance ledger

The bugfix track's contract is *the red repro goes green + a regression test is left behind
+ nothing else regresses.* Every row verified by running it.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| U1 | The red repro goes GREEN | **met** | `test_the_scanner_flags_a_record_relative_subscript`, red at `df17337`, green at `827c528` — **with its assertion never edited**. Offline suite went from exactly one failure to zero |
| U2 | A regression test is left behind | **met** | `tests/test_fixed_offset_guard_scope.py`, new at `184d555` with 28 tests, 32 after Phase 6. The guard's own suite went 5 → 12 |
| U3 | Nothing else regresses | **met** | Gamedata `81 passed, 1 skipped` at **every phase**, identical to the Phase 0 baseline. ruff, `ruff format --check`, mypy (45 files, strict over `src` *and* `tests`) clean throughout |
| U4 | The ledger row exists | **met** | This table |
| P0 | Baseline on a clean tree | **met** | `98fdd7a`. Managed **22,046 / 1,012 / 337**; standard **18,077 / 1,012 / 259**; challenge **18,077 / 968 / 259**; 3,058 calendar events each |
| P1 | The seam exists, nothing uses it | **met** | `f520f85` — `parser/lookahead.py`, 179 lines, imported by nothing |
| P2 | Four modules migrated, split by module (G3) | **met** | `d133fb2` `a0837d9` `1754d8e` `4c8a1ce`. Baseline reproduced **exactly** at each of the four gates |
| P3 | The rule widens; the repro flips | **met** | `827c528`. Whole-tree scan green with **zero false positives** — independently the proof P2 finished |
| P4 | The guard is guarded | **met** | `184d555`. Two mutants recorded dying; see §4 |
| P5 | The Hardening tier discharged | **met** | `039ac3c`. Both motivating constants re-expressed as width sums; four addend mutants caught **offline** |
| P6 | The class is checked, not the instances | **met** | `3153cfb`. Five plan-named fixtures behave as named |
| P7 | No document claims coverage the guard lacks | **met** | This phase. `test_agent_contract` green |

## 2. What shipped

**The fix is a change of question.** The guard used to ask *what syntax is this?* and now
asks *which module is doing it?* — because no syntactic rule separates a record-relative
seek from the width arithmetic the parser is legitimately full of, and the RCA measured that
a naive widening fires on ~10 legitimate lines across five modules.

Three mechanisms, each blind to what the next one catches:

- **Calls** — `.seek(<literal>)`, `unpack_from(…, <literal>)`. The original, unchanged.
- **Subscripts** — a buffer subscript carrying arithmetic or a nonzero literal, outside a
  two-entry allowlist. Inside those two, a *stricter* interior rule: no bare literal at all.
- **Positions handed to the seam** — because once every read goes through `lookahead.py`, a
  caller can commit the original defect while indexing nothing.

Supporting work the migration made necessary:

- **`parser/lookahead.py`** — the sanctioned surface. Refuses short reads rather than
  truncating; `peek_date_parts` deliberately does *not* validate, because a calendar record
  tolerates 0/0/0 and a player record being framed must not.
- **`players.py`'s two validation lookaheads** re-expressed as sums of named field widths.
- **[ADR 0020](../../../../docs/decisions/0020-sanctioned-lookahead-seam.md)**, and prose
  corrections in four places that had described the ban as enforced with *zero exemptions*.

## 3. Deviations from the plan

**Three plan citations had drifted** and were re-grounded before use: `players.py:383 → 390`
(`tail[4]`), `teams.py:624 → 609` (`run[base + 1]`), `world.py:844 → 856`
(`pattern[_LENGTH_PREFIX_WIDTH:]`). The lines were unchanged; Phases 2–3 moved them.

**The plan's stated residual was wrong, and writing the control found it.** Phase 4 was to
pin *"a position hoisted into a local — `data[at : at + 4]` passes."* It does not pass: the
slice's upper bound still carries arithmetic, and so does `data[at : at + _WIDTH]`. Only a
read whose **every** index component is a bare name slips through. The guard is *stronger*
than the plan and my own Phase 3 docstring described it as being. Corrected in both, and the
residual is now bounded from both sides so the overbroad claim cannot drift back.

**Phase 6's discrimination rule was underdetermined by the plan.** It called for a table of
module-level bare-int assignments, but `_TEAM_ID_OFFSET = 58` and `LENGTH_PREFIX_WIDTH = 4`
are structurally identical and only the first is a defect. The code settles it on whether a
constant is a *distance to travel* or an *address to land on* — see ADR 0020. This makes
Phase 5 load-bearing rather than cosmetic: a **derived** constant is not a literal at all,
so the same call site is a violation before that phase and legal after, with no change to
the call.

**Two acceptance criteria were met in substance rather than literally**, recorded rather
than ticked. Phase 5's *"no bare integer literal as an addend to a position"* leaves two
`+ 1`s in `players.py` — both half-open-range corrections, neither a field offset. Phase 5's
*"zero skips"* leaves one: `test_byte_accounting.py:114`, pre-existing and structural, about
the **teams** walk's declared tier.

## 4. Seen to fail — the falsification transcript

CI cannot produce this evidence: it runs the guard against a clean tree, where a working
guard and a guard that reports nothing are indistinguishable. **Ten mutations**, each
recorded, each restored.

| Phase | Mutation | Result |
|---|---|---|
| 3 | Plant `data[record_start + 58 : …]` in `players.py` | RED — buffer subscript outside the seam |
| 3 | Plant `handle.seek(128)` | RED — the original mechanism survived the rewrite |
| 3 | Plant the *same* bare read **inside** `lookahead.py` | RED under the interior rule, while the named-width form beside it stays green |
| 4 | Remove `visit_Subscript` | 9 failed, 23 passed |
| 4 | Add a third allowlist entry | 2 failed — the count test, **and** the location-rule test whose "outside" example is `players.py` |
| 5 | `_NAME_INDEX_COUNT` 2 → 3 | RED **offline**, both pins by name |
| 5 | `_PLAYER_ID_WIDTH` u32 → u8 | RED offline |
| 5 | `_NAME_INDEX_WIDTH` u32 → u8 | RED offline |
| 5 | `_GAP_AFTER_BIRTH_DATE` 3 → 4 | RED offline |
| 6 | Neutralise the folded-constant rule | 2 failed |

Phase 5's four ran with `-m gamedata` **deselected** on purpose. CI deselects gamedata, so a
pin that lived only there would leave a broken derivation green on every PR.

## 5. Baseline versus after

| | Before | After `3153cfb` |
|---|---|---|
| Offline suite | 348 passed, 1 **failed**, 1 skipped — at `4c8a1ce`, the last commit before the widening. The one failure is the repro, red since `df17337` | **390 passed**, 0 failed, 1 skipped |
| Gamedata | 81 passed, 1 skipped — Phase 0 baseline at `98fdd7a` | **81 passed, 1 skipped** — unchanged at every one of the eight phases |
| Managed league | 22,046 / 1,012 / 337 | identical |
| Standard save | 18,077 / 1,012 / 259 | identical |
| Challenge save | 18,077 / 968 / 259 | identical |
| Save-buffer reads outside the seam | 21 | **0** — `primitives.Cursor.take` indexes the buffer the cursor owns and is allowlisted; `world.py`'s two `pattern[…]` slices read a constructed search pattern, not a save buffer |

## 6. Four latent bugs found on the way

None was the reported defect; all were found by migrating code the guard could not see.

1. **`header.py`'s classifier read `data[0]` and `data[1:5]`** — two literal absolute offsets,
   in the module whose docstring claimed it avoided exactly that. **My RCA survey missed this
   site entirely**; the planning panel's code-grounded adversary found it. Had it been
   skipped, Phase 3's whole-tree scan would have gone red on a line nobody expected.
2. **`human_managers._is_club_landmark` called `int.from_bytes` on a raw slice.** Past the end
   of a buffer that returns a **smaller number silently** rather than raising, so a truncated
   file could have produced a landmark match out of bytes that were never there. The caller
   bounds its own range, so nothing reached it.
3. **The same class of silent-short-read** in the module migrated at `a0837d9`.
4. **`looks_like_save_file` had no direct test coverage at all** — found while rewriting it.
   It is the function that filters a `*.dat` glob before anything reaches `read_header`, so a
   wrong answer means refusing a real save or feeding a ZIP to the header reader. Now covered,
   including the two real non-record files a glob catches: a ZIP and a text log.

## 7. What stays open

**The guard names six things it cannot see**, each pinned as an executable control so a
future edit that widens or closes one fails loudly rather than drifting.

Five are remote — they require writing something the surrounding code gives no reason to
write. **One is not.** A position composed into a local before the call —
`at = offset + 58; peek_u32(data, at)` — passes, and that shape is ordinary readable code
which `world.py:750` writes *correctly* from three named widths. Any rule strict enough to
catch the bad version fires on the good one. Closing it needs dataflow analysis inside a test
module; that cost was declined, deliberately and on the record.

So a green build here is **evidence, not proof**. The structural half — a `Cursor` with no
`seek`, no position setter and no absolute read — remains the half that cannot be argued
with, and the AST scan remains the backstop the RCA always said it was.

---

**A note on this file's own links.** They are written for `_done/`, which is where it lives,
because the move happens in the same commit that creates it. Its siblings in `_done/` are not
so lucky: several carry `../../../docs/...`, correct at the live path and dead one directory
short of the repo root ever since they moved. `tests/test_doc_links.py` exempts `_done/`, so
nothing caught it. Not fixed here — it is a different request's worth of edits across several
closed reports, and quietly rewriting archived artifacts to fix a link is how a record stops
being one.
