> **Status:** diagnosed · created 2026-08-18 · decided · next: plan

# Root Cause Analysis — The fixed-offset guard cannot see a subscript

## Verdict

**confirmed-bug** — and it needs the full track. The *cause* is a single missing AST
visitor and would be a one-liner to close. The *rule* is not obvious, a naive fix is
demonstrably worse than the gap, and the fix touches a guard every future parser change
passes through. That is a design decision with a written scope, not a hotfix.

**The intake's third option — leave the guard and narrow the docs instead — was weighed
against measurement and is REFUTED.** See *The third option, and why it fails* below. It
was the cheapest outcome available and it does not survive the evidence.

## Reproduction (red)

`tests/test_no_fixed_offsets.py::test_the_scanner_flags_a_record_relative_subscript`,
run with `uv run pytest tests/test_no_fixed_offsets.py`.

It hands `scan_source` the same defect the module's existing `OFFENDING` fixture uses,
spelled as a slice rather than a call:

```
def read_team_id(data, record_start):
    return int.from_bytes(data[record_start + 58 : record_start + 62], "little")
```

RED on today's code:

```
AssertionError: a record-relative read at a constant offset passed the guard because
it was written as a subscript rather than a call
assert []
```

`58` is not an arbitrary number. It is the measured offset of `team_id` in a
`players.dat` record, and reading it there is correct for **86.9%** of players and
silently wrong for the rest — the exact failure Phase 6a refused to ship.

**Not yet committed.** It lands with this RCA on branch
`fix-fixed-offset-guard-subscripts`.

## Evidence (the cause)

**The proximate cause is one missing visitor.** `tests/test_no_fixed_offsets.py`'s
`FixedOffsetVisitor` defines `visit_Call` and nothing else. Python parses
`data[start + 58 : start + 62]` as an `ast.Subscript` containing an `ast.Slice`, and
`generic_visit` walks straight past it because no handler claims it. The two shapes the
visitor does flag — `.seek(<literal>)` and `unpack_from(..., <literal>)` — are both
`ast.Call`. So coverage is decided by **which syntax an author reached for**, not by what
the code does.

**The deeper cause is that the parser has two read paths and the guard only covers
spellings within one of them.** `measured` 2026-08-18 across `src/ootp_ai/parser/`:

| Module | direct-buffer reads | reads via `Cursor` |
|---|---|---|
| `world.py` | 7 | 29 |
| `players.py` | 7 | 25 |
| `human_managers.py` | 3 | 10 |
| `teams.py` | 3 | 10 |
| `header.py` | 2 | 8 |

The direct-buffer path is not incidental — it is how **every** walker does lookahead and
landmark search, spread over some twenty-five functions that take `data: bytes` and a
position (`_scan_shape`, `_scan_signature`, `_find_league_record`, `_find_calendar_array`,
`_looks_like_record`, `_peek_u32`, …). That path indexes the buffer freely and **nothing
structural constrains it at all.**

**The sharpest evidence is that the convention is already written down — three times —
and is violated in the one place that matters.** `teams.py:596`, `players.py:577` and
`world.py:874` each define a near-identical `_peek_u32`, and each docstring states the
rule in prose:

- `teams.py` — *"A lookahead at the cursor's own position, never at a constant."*
- `world.py` — *"A lookahead at a position computed from the data … never at a constant."*
- `players.py` — *"A `u32` at a **computed** position, for lookahead. Never a literal offset."*

And then `players.py:553` and `:557` call into that same family with
`position + _BIRTH_DATE_LOOKAHEAD` and `position + _AGE_LOOKAHEAD`, where those constants
are `12` and `19` (`players.py:199-200`). **Three modules assert the rule and one breaks
it, because prose is the only thing enforcing it.** That is the defect: not the two lines,
but that nothing could have caught them.

*(Citations re-grounded 2026-08-18. The intake cited `players.py:445` and `:449`; the
module grew when the club-assignment decode landed in the same PR and they are now `:553`
and `:557`. The request's Affected Area pointers are corrected accordingly.)*

## The third option, and why it fails

The intake asked, honestly, whether the right fix is to **leave the guard alone and
correct `CLAUDE.md:103` and `.claude/agents/data-engineer.md`** to describe what the scan
actually covers — on the reasoning that `parser/primitives.py`'s `Cursor` is the real
structural enforcement and the AST scan is only a backstop.

**The `Cursor` half of that is true.** `primitives.py` exposes no `seek`, no position
setter and no absolute read; `position` is a read-only property. A walk conducted through
the cursor genuinely cannot seek.

**The conclusion does not follow, because the cursor governs only the consuming reads.**
The twenty-two direct-buffer sites above never touch it. Narrowing the documentation would
therefore replace one wrong claim with another: instead of "CI enforces the ban" it would
say "the cursor enforces it", while the larger and more error-prone path — the lookahead
and search helpers, which is precisely where a record-relative constant appears — remains
covered by **nothing**. The honest version of that sentence would have to read "the ban is
enforced on the consuming path only, and the search path is unguarded", which is a
statement nobody should be comfortable shipping.

So the docs do need correcting, but as a *consequence* of whatever the guard ends up
covering — not instead of it.

## Fix posture (tiered)

- **Minimal.** Add `visit_Subscript` to `FixedOffsetVisitor`, flagging a subscript whose
  index is a `BinOp` with a nonzero integer literal operand. This turns the repro green.
  **It also fires on legitimate code**, and that is the whole problem: the intake's survey
  found the same shape used for intra-field date decoding (`players.py`, `world.py`),
  `u32` length-prefix payload reads (`teams.py:590`, `world.py:868`) and computed widths
  (`human_managers.py:204,248`). Shipping the minimal fix alone would make the guard cry
  wolf on five modules, and its own docstring says a guard that cries wolf gets loosened —
  *"and a loosened guard is worse than none."* **Do not ship this tier by itself.**

- **Root — and the planning stage's real question.** Give buffer lookahead a single
  legitimate home and let the guard key on that rather than on syntax. The three duplicate
  `_peek_u32` implementations are evidence that the seam already wants to exist: extract a
  shared lookahead module whose functions take `(data, position)` and are the *only*
  sanctioned place to index a save buffer, then flag direct indexing anywhere else. That
  is structurally checkable, removes a triplicated function, and gives "validation
  lookahead" the name the intake asked whether it deserves.

  Candidate rules the plan should weigh, with what each costs:
  - **Name-based allowlist** (`_peek_*` / `_scan_*` / `_find_*` may index; nothing else).
    Cheap and matches the existing convention across three modules — but an author can
    name anything `_peek_` and the guard believes them.
  - **Literal-vs-Name** (flag a bare int literal addend, allow a named constant).
    Would **not** catch `players.py:553`, which uses named constants. Too weak.
  - **Module-scoped** (only the shared lookahead module may index a buffer). Strongest and
    the largest diff; it is the one that would have caught this.

- **Hardening, gated not assumed.** If a lookahead seam lands, the constants that
  motivated this (`_BIRTH_DATE_LOOKAHEAD`, `_AGE_LOOKAHEAD`) are still record-relative
  offsets into a head measured as fixed-width. They are defensible and they are also
  exactly what the ban is about, so the plan should decide whether they earn an explicit,
  reviewed exemption or should be re-expressed as a sum of named field widths — the form
  `world.py:743` already uses (`offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH`)
  and the only form in the parser that is both constant-derived and self-documenting.

**What stays open either way.** Nothing in the tree is currently mis-parsed: every
existing direct-buffer read was reviewed during intake and each is either benign or
correct. This bug is about what the next change can get away with, not about a wrong
number today.
