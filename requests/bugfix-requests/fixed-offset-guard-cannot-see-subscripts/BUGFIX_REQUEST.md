> **Status:** intake · created 2026-08-18 · open · next: root-cause

# Bug Report — The fixed-offset guard cannot see a subscript, and the docs say it can

## Symptom

`tests/test_no_fixed_offsets.py` is the mechanical half of the fixed-offset ban (AC3). It
flags exactly two AST shapes: `.seek(<nonzero int literal>)` and `unpack_from(...)` with a
nonzero int literal as its third positional argument. **It never inspects a subscript.**

So the same wrong read — a field taken at a constant offset from a record start — is
caught when it is written one way and invisible when it is written another:

```
struct.unpack_from("<I", data, 58)          # flagged
int.from_bytes(data[record_start + 58 : record_start + 62], "little")   # silent
```

Both are the construction the ban exists to prevent, and the second is the more natural
way to write it in this codebase, because the parser passes `bytes` around rather than
file handles.

**The repo states the stronger claim in three places.** `CLAUDE.md:103` — *"The
fixed-offset ban is the rulebook's, and CI enforces it."* The guard's own docstring —
*"this scans the AST of every parser module on every CI run"* — and it describes the
ban as running *"with zero exemptions"*. `.claude/agents/data-engineer.md` calls seeking
code *"a blocker, not a style note"*. An agent reading any of those concludes the shape is
mechanically prevented. It is not.

## Reproduction attempt

**Deterministic, offline, no game data.** Import the scanner and hand it two functions
that commit the *same* defect:

```
uv run python -c "import sys; sys.path.insert(0, 'tests'); from test_no_fixed_offsets import scan_source; print(scan_source(open('x').read(), 'x'))"
```

Measured 2026-08-18, running `scan_source` over each of the two snippets above:

```
subscript    -> NONE - the guard is blind to this
unpack_from  -> ['unpack_from.py:5: unpack_from(..., 58) - a constant record-relative offset']
```

`uv run pytest tests/test_no_fixed_offsets.py` is green today and stays green with a
subscript-form offender added to any parser module.

## Expected vs Actual

- **Expected:** a read at a constant offset from a record start fails the build, whatever
  syntax expresses it — because that is what `CLAUDE.md`, the guard's docstring and the
  agent rulebook all say happens.
- **Actual:** only the `seek` and `unpack_from` spellings fail. The subscript spelling
  passes silently, and it is the spelling this parser's style makes most likely.

## Severity

**No data is wrong today, and nothing is currently mis-parsed.** Every subscript-with-a-
constant in the tree was reviewed during this intake and each one is defensible — see the
pointers below. The cost is entirely in what the guard *promises*.

That promise is load-bearing rather than cosmetic. The failure it is supposed to prevent is
the one this project calls the worst available: a fixed-offset read *passes on day-0 data
and silently returns the wrong field* for every record with a different shape. Phase 6a
declined to land `team_id` for exactly this reason — measured, reading it at a constant
offset is correct **86.9%** of the time, because `last_team_id` is dropped when zero and
everything after it shifts four bytes. An agent who writes
`data[record_start + 58 : record_start + 62]` to grab `team_id` gets a green build, a
plausible number for seven clubs in eight, and a documented assurance that the hazard is
mechanically checked.

**Not urgent, but timely:** Phase 6b of `requests/feature-requests/first-sight/` works
directly in that drop-zero region, so this is the window where the wrong shape is most
tempting to write.

## Triage

- **Verdict:** needs-full-track
- **Obviousness hint (non-binding):** the *gap* is obvious and a one-line AST visitor
  would close it. **The rule is not obvious, and a naive fix is worse than the gap.** A
  guard that flags every `data[x + N]` would fire on length-prefix arithmetic and
  date decoding all over the parser — and this guard's own docstring says *"A guard that
  cries wolf gets loosened, and a loosened guard is worse than none."* Deciding what to
  flag is the request; editing the scanner is the easy part.

## Affected Area & Pointers

1. `tests/test_no_fixed_offsets.py` — `FixedOffsetVisitor.visit_Call` is the whole
   mechanism, and `visit_Subscript` is what does not exist.
2. `CLAUDE.md:103` — the "CI enforces it" claim.
3. `.claude/agents/data-engineer.md` — the rulebook's parsing section, which owns the ban.
4. `src/ootp_ai/parser/players.py:445` and `:449` — the two instances that prompted this.

**A survey of every current instance, because the fix depends on telling them apart.**
Measured 2026-08-18 across `src/ootp_ai/parser/`:

| Where | Shape | Reading |
|---|---|---|
| `players.py:481-482`, `world.py:745-746` | `data[position + 1]`, `data[position + 2 : position + 4]` | **Benign.** Decoding the internals of a 4-byte date the caller already located. Reading a field's own bytes is not seeking within a record. |
| `teams.py:590`, `world.py:868` | `data[position + 4 : position + 4 + length]` | **Benign.** Stepping over a `u32` length prefix to reach its payload — derived from the format, not guessed. |
| `human_managers.py:204,248` | zero-run scan, array-slot indexing | **Benign.** Both widths are computed. |
| `world.py:743` | `offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH` | **Benign, and the model to copy.** A sum of *named field widths* — "walk past these fields" written arithmetically. |
| `players.py:445,449` | `position + _BIRTH_DATE_LOOKAHEAD` (12), `position + _AGE_LOOKAHEAD` (19) | **The genuinely guard-relevant case.** Raw record-relative constants, not width sums. |

## Reporter's cause-hunch (non-binding)

The guard was written against the two shapes that existed when it was written — a file
handle and `struct.unpack_from` — and the parser subsequently settled on passing `bytes`
and slicing them. The mechanism did not follow the style. Nothing about `visit_Call`
suggests subscripts were considered and excluded; they look simply absent.

## Open Questions for Diagnosis

- **Widen the guard, or narrow the docs?** A real third option, and possibly the right
  one. The ban's *structural* enforcement is `Cursor`, which exposes no `seek` and no
  absolute read by construction; the AST scan is a backstop. If the backstop cannot be
  made precise without crying wolf, the honest fix may be to correct `CLAUDE.md` and the
  rulebook to describe what it actually covers, and let the cursor carry the guarantee.
- **What rule separates a record-relative seek from legitimate width arithmetic?**
  Candidates worth weighing: flag a bare int literal but allow a Name (which would pass
  `players.py:445` — it uses a named constant — and so may be too weak); flag any constant
  addend inside a *validation* helper but not a decoding one; or require that such reads
  be confined to a named, reviewed allowlist of lookahead helpers.
- **Are validation lookaheads a category the ban should exempt outright?** The two
  `players.py` instances confirm a *candidate record start* before the cursor commits to
  it; the authoritative reads all still go through the cursor. `teams.py` does the same
  thing with `_peek_u32`. If that is a legitimate pattern, it wants a name and a rule,
  not case-by-case prose.
- **Not a regression.** The guard has had this shape since Phase 3 and the docs have made
  the stronger claim since before that.

## Stage plan

**Full pipeline.** Trigger 1 fires: the Open Questions above are non-empty and the first
is load-bearing — widening the guard and narrowing the docs are materially different
outcomes, and one of them changes a claim in `CLAUDE.md`. Trigger 3 fires too: this is a
guard every future parser change passes through, and a version of it that cries wolf gets
loosened or deleted, which would cost more than the gap it closed.
