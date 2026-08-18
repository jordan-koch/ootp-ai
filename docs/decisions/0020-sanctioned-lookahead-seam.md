# 0020 — One sanctioned seam may index a save buffer; everywhere else walks

**Status:** Accepted
**Date:** 2026-08-18

## Context

The fixed-offset ban is this project's oldest correctness rule and the one with the
largest blast radius. Records carry **variable-length regions**, so a field read at a
constant offset is right for one record shape and silently wrong for every other —
`measured`, the same player's ratings block sat 43 bytes from one anchor in one save and
107 in another with a byte-identical internal layout. Nothing raises. Every downstream
recommendation inherits the error.

Enforcement was in two halves, and only one of them worked.

The **structural** half is `Cursor` — no `seek`, no position setter, no absolute read.
That half is sound and is not what this ADR changes.

The **mechanical** half was `tests/test_no_fixed_offsets.py`, which scanned the AST of
every parser module. It inspected `ast.Call` and nothing else, so it caught
`unpack_from("<I", data, 58)` and was blind to `data[start + 58 : start + 62]` — the same
wrong read, and the one this codebase actually produces, because every walker holds
`bytes` rather than a file handle. Meanwhile `CLAUDE.md`, `header.py` and
`primitives.py` all described the ban as mechanically enforced with **zero exemptions**,
which was a stronger claim than the code supported. `header.py`'s own classifier read
`data[0]` and `data[1:5]` — two literal offsets in the module whose docstring claimed it
avoided exactly that, invisible to the guard for the entire life of both.

The hard part was never the visitor. It was **the rule**. A guard that flagged every
`data[x + N]` would fire on legitimate code across five modules: intra-field date
decoding, stepping over a `u32` length prefix to reach its payload, and `world.py`'s
composition of an offset from named field widths — which is what a sequential walk looks
like written arithmetically. The guard's own docstring says a guard that cries wolf gets
loosened, and a loosened guard is worse than none.

Three candidate rules were weighed ([`ROOT_CAUSE_ANALYSIS.md`][rca]). A name-based
allowlist of `_peek_*`/`_scan_*` helpers was declined as a registry that could be
satisfied by adding entries. Literal-vs-`Name` was declined as too weak — the real
instances used *named* constants, so it would have caught nothing.

[rca]: ../../requests/bugfix-requests/_done/fixed-offset-guard-cannot-see-subscripts/ROOT_CAUSE_ANALYSIS.md

## Decision

**Exactly one module may index a save buffer. Everywhere else walks with a `Cursor`.**

`src/ootp_ai/parser/lookahead.py` is that seam: a small, bounds-checked surface —
`peek_u8`, `peek_u32`, `peek_bytes`, `peek_date_parts`, `zero_run_width`,
`peek_length_prefixed_ascii` — that refuses a short read rather than truncating.
`primitives.py` is allowlisted alongside it because `Cursor.take` indexes the buffer the
cursor owns. **Two entries, and the count is asserted by a test.**

The rule keys on **location, not syntax**, because no syntactic rule separates a
record-relative seek from the width arithmetic the parser is legitimately full of.

Three mechanisms follow from that, each blind to what the next one catches:

1. **Calls** — `.seek(<literal>)` and `unpack_from(…, <literal>)`. The original.
2. **Subscripts** — a buffer subscript carrying arithmetic or a nonzero literal, outside
   the allowlist. A parameter annotated `bytes` is a buffer; so is a direct alias of one.
3. **Positions handed to the seam** — because once every read goes through `lookahead.py`,
   a caller can commit the original defect without indexing anything at all:
   `peek_u32(data, position + _TEAM_ID_OFFSET)`. The constant is judged on whether it is a
   **distance to travel** or an **address to land on**: a bare integer not named as a span
   is flagged, a span-named one passes, and one *derived* from named field widths passes
   because it is not a literal at all.

**Inside the allowlisted modules a stricter rule applies** — no bare nonzero integer
literal in a buffer subscript, at all. Being sanctioned is the reason to be tighter, not
looser; an unconditional permission would make the seam a laundering route for exactly the
constants the ban exists to stop.

## Consequences

**What this buys.** The rule is one sentence, so it survives being retold. The defect that
prompted it is now caught in both of its spellings, and the third mechanism catches the
class rather than the two instances. `players.py`'s two validation lookaheads were
re-expressed as sums of named field widths and are now defensible *mechanically* rather
than by prose — the same call site was a violation before and is legal after, with no
change to the call. Four latent bugs surfaced during the migration, including two reads
that returned a **smaller number silently** past the end of a buffer rather than raising.

**What it costs.** Every parser module now depends on the seam, so a bug in
`lookahead.py` is a bug everywhere — which is why it is small, bounds-checked, and the
only place the rule permits the hazard. The allowlist is a standing invitation to add a
third entry; the asserted count is what makes that a decision rather than a diff. And the
third mechanism's span/offset distinction is **name-based**, so an offset called
`_TEAM_ID_WIDTH` evades it. That is a deliberate mislabel rather than a slip, and
inferring intent from a number is not available.

**What it forecloses.** No per-site exemption registry, ever. A registry lets a guard be
satisfied by adding entries, which is how a guard stops being one.

**What it does not claim.** The guard's docstring names **six** things it cannot see, and
`tests/test_fixed_offset_guard_scope.py` pins every one as an executable control so a
future edit that widens or closes one fails loudly. Five are remote — they require writing
something the surrounding code gives no reason to write. **One is not:** a position
composed into a local before the call (`at = offset + 58; peek_u32(data, at)`) passes, and
that shape is ordinary, readable code which `world.py` writes *correctly* from named
widths. Any rule strict enough to catch the bad version fires on the good one. Closing it
needs dataflow analysis inside a test module, and that cost was declined.

A green build is therefore **evidence, not proof**. The structural half — a cursor that
cannot seek — remains the half that cannot be argued with.
