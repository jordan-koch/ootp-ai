"""AC3 — the fixed-offset ban, enforced mechanically instead of by review.

`.claude/agents/data-engineer.md:69-74` calls seeking code *"a blocker, not a style
note"*. A rule enforced only by review is enforced only until the next agent, so this
scans the AST of every parser module on every CI run.

**AST, not regex**, deliberately: a regex over source text trips on the word `seek`
inside a docstring or a comment — and this file's own neighbours are full of prose
explaining why seeking is forbidden. A guard that cries wolf gets loosened, and a
loosened guard is worse than none.

What is banned is a **literal** offset. `cursor.seek(0)` stays legal (a rewind is not
a fixed-offset read) and `struct.unpack_from(fmt, buf, position)` with a *name* stays
legal — that is a sequential walk carrying its own cursor. Only a hardcoded number is
the hazard.

## Three mechanisms, because each is blind to what the next one catches

Until 2026-08-18 this scanned **calls only** — `.seek(...)` and `unpack_from(...)`, both
`ast.Call`. A subscript was never inspected, so the identical defect passed or failed on
syntax alone:

```
struct.unpack_from("<I", data, 58)                      # caught
int.from_bytes(data[start + 58 : start + 62], "little")  # silent
```

and the silent spelling is the one this codebase produces, because every walker holds
`bytes` rather than a file handle. So there is now a second mechanism, and it keys on
**location** rather than on syntax: exactly one module may index a save buffer, and a
buffer subscript anywhere else is a violation.

**`EXEMPT_MODULES` is two entries and must stay small enough to audit.** Inside them a
*stricter* interior rule applies — no bare nonzero integer literal in a buffer subscript
at all — because being sanctioned is the reason to be tighter, not looser. A seam that
could launder a constant would be worse than no seam.

**And the location rule has its own blind spot, which is why there is a third mechanism.**
Once every buffer read goes through `lookahead.py`, a caller can commit the original defect
without indexing anything:

```
peek_u32(data, position + _TEAM_ID_OFFSET)      # no subscript here at all
```

The indexing happens inside the seam, where it is allowed. So the **position handed to a
lookahead** is judged too, and the question it asks is whether the constant is a *distance
to travel* or an *address to land on* — see `SPAN_SUFFIXES`. `_AGE_LOOKAHEAD` passes because
it is derived from field widths; the identical call with a folded `= 19` would not. That is
what re-expressing those two constants bought, and this mechanism is what makes it stick.

## What this cannot see, named so nobody assumes otherwise

- **A read whose every index component is a bare name.** `at = start + 58; end = at + 4`
  then `data[at:end]` passes, as does `data[at]`. Note this is **narrower than a hoist**:
  `data[at : at + 4]` is still caught, because the slice's upper bound carries arithmetic —
  measured 2026-08-18, after an earlier draft of this list claimed otherwise. Closing the
  remainder needs dataflow analysis inside a test module.
- **An attribute-valued buffer.** `self._buf[start + 58]` passes; only a plain `Name` is
  tracked. `Cursor.take` is exactly this shape, and is also exempt.
- **`bytearray` and `memoryview` annotations.** Nothing in the tree uses either; the
  accepted set is `{bytes}` and widening it is one line when something does.
- **A renamed unannotated parameter.** The fallback covers `data`, `buf` and `buffer`.
- **A position composed into a local before the call.** `at = offset + 58` then
  `peek_u32(data, at)` passes, because the rule judges the *argument* and a lone local says
  nothing about how it was built. This is the same shape as the subscript residual above and
  it has the same fix — dataflow analysis — and the same reason for declining it. It is also
  the shape of `world.py:750`, which does exactly this **legitimately**, composing `date_at`
  from three named widths; any rule strict enough to catch the bad version fires on the good
  one too.
- **An offset misnamed as a span.** `_TEAM_ID_WIDTH = 58` passes, because `SPAN_SUFFIXES` is
  the only signal separating a width from an address and both are bare integers. Evading it
  means labelling an address a distance, which is a deliberate act, not a slip.

Each is a **known** hole rather than an unnoticed one, and every one is pinned as an
executable control in `tests/test_fixed_offset_guard_scope.py` — so a future edit that
silently widens or closes one fails there rather than drifting. Prose alone is exactly what
the bug being fixed here proves insufficient.

**They are not equally remote.** Four of the six require writing something the surrounding
code gives no reason to write. The fifth does not: composing a position into a local is
ordinary, readable, and what `world.py:750` correctly does — so that hole is genuinely open,
and it is open because closing it would fire on the good version too. Anyone tempted to call
this guard complete should read that item twice.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "src" / "ootp_ai"

#: The only modules allowed to index a save buffer, as repo-relative posix paths — the
#: same string the real scan builds. `lookahead.py` is the sanctioned seam;
#: `primitives.py` holds `Cursor.take`, which indexes the buffer the cursor owns.
#: **Two entries, and it must stay that small** — an allowlist that grows is how a guard
#: stops being one. Nothing asserts the count yet; Phase 4 pins it as a control.
EXEMPT_MODULES = (
    "src/ootp_ai/parser/lookahead.py",
    "src/ootp_ai/parser/primitives.py",
)

#: Annotations that mean "this parameter is a save buffer". Deliberately just `bytes`:
#: every buffer parameter in the tree is annotated that way, and adding speculative
#: entries for types nothing uses is how a rule stops matching the code.
ACCEPTED_ANNOTATIONS = frozenset({"bytes"})

#: Unannotated parameters with these names are treated as buffers too. The narrow
#: fallback exists because the repro fixture is unannotated, and shipping only the
#: annotation rule would have turned it green for the wrong reason.
FALLBACK_BUFFER_NAMES = frozenset({"data", "buf", "buffer"})

#: Functions whose second positional argument is a **buffer position**. Every read that is
#: not a `Cursor` walk goes through one of these, so this is where a folded offset would
#: arrive. `_peek_*` catches the private wrappers a module writes over the seam —
#: `players._peek_valid_date` is one, and it takes one of the two arguments that prompted
#: this whole request.
LOOKAHEAD_PREFIXES = ("peek_", "_peek_")
LOOKAHEAD_NAMES = frozenset({"zero_run_width"})

#: Which argument is the position. Fixed across the seam by design — `(data, position, …)` —
#: so the limit/count arguments that follow are never judged. `peek_length_prefixed_ascii`
#: takes a `limit` third and `zero_run_width` a `limit` keyword; both are sizes, and flagging
#: `limit=_MAX_PAD` would be the cry-wolf failure.
POSITION_ARGUMENT = 1

#: Suffixes that mark a module constant as a **distance to travel** rather than a **place to
#: land**. This distinction is the whole rule, and it cannot be read off the value: both
#: `LENGTH_PREFIX_WIDTH = 4` and a hypothetical `_TEAM_ID_OFFSET = 58` are module-level bare
#: integers, and only the second is the defect. Stepping over a field you have named is what
#: a sequential walk looks like when written arithmetically; landing at a remembered address
#: is the thing the ban exists to prevent.
#:
#: **Name-based, and therefore evadable** — an offset called `_TEAM_ID_WIDTH` would pass.
#: That is a deliberate mislabel rather than an accident, it is pinned as a control in
#: `tests/test_fixed_offset_guard_scope.py`, and the alternative — inferring intent from a
#: number — is not available.
SPAN_SUFFIXES = ("_WIDTH", "_LEN", "_LENGTH", "_SPAN", "_COUNT")


class FixedOffsetVisitor(ast.NodeVisitor):
    """Flags a constant offset however it is spelled — as a call or as a subscript."""

    def __init__(self, filename: str, *, exempt: bool = False) -> None:
        self.filename = filename
        self.exempt = exempt
        self.violations: list[str] = []
        self._buffers: set[str] = set()
        #: Module-level names bound to a bare integer and NOT named as a span. These are
        #: the folded offsets — a magic number wearing a name — and using one as a position
        #: is the defect a subscript rule structurally cannot see.
        self._folded: set[str] = set()

    def visit_Module(self, node: ast.Module) -> None:
        """Collect module-level constants before judging any call that might use one."""
        self._folded = _folded_constants(node)
        self.generic_visit(node)

    @staticmethod
    def _nonzero_literal(node: ast.AST) -> int | None:
        """Takes `AST` rather than `expr` because `ast.walk` yields the wider type."""
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            if not isinstance(node.value, bool) and node.value != 0:
                return node.value
        return None

    def _index_literals(self, index: ast.expr) -> list[int]:
        """Every nonzero int literal anywhere in a subscript index."""
        found: list[int] = []
        for sub in ast.walk(index):
            literal = self._nonzero_literal(sub)
            if literal is not None:
                found.append(literal)
        return found

    @staticmethod
    def _has_arithmetic(index: ast.expr) -> bool:
        return any(isinstance(sub, ast.BinOp) for sub in ast.walk(index))

    def _buffer_parameters(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        args = node.args
        names: set[str] = set()
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            annotation = arg.annotation
            if isinstance(annotation, ast.Name) and annotation.id in ACCEPTED_ANNOTATIONS:
                names.add(arg.arg)
            elif annotation is None and arg.arg in FALLBACK_BUFFER_NAMES:
                names.add(arg.arg)
        return names

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Save and restore, so a nested function's buffers do not leak outward.
        outer = self._buffers
        self._buffers = outer | self._buffer_parameters(node)
        self.generic_visit(node)
        self._buffers = outer

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        outer = self._buffers
        self._buffers = outer | self._buffer_parameters(node)
        self.generic_visit(node)
        self._buffers = outer

    def visit_Assign(self, node: ast.Assign) -> None:
        """`buf = data` makes `buf` a buffer too. A derived slice is NOT tracked."""
        if isinstance(node.value, ast.Name) and node.value.id in self._buffers:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._buffers.add(target.id)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        value = node.value
        if isinstance(value, ast.Name) and value.id in self._buffers:
            literals = self._index_literals(node.slice)
            if self.exempt:
                # The stricter interior rule: a sanctioned module may compute an offset
                # from named widths, but never from a bare number.
                if literals:
                    self.violations.append(
                        f"{self.filename}:{node.lineno}: {value.id}[… {literals[0]} …] — "
                        "a bare literal inside a module allowed to index a buffer; the "
                        "seam must use a named width"
                    )
            elif self._has_arithmetic(node.slice) or literals:
                self.violations.append(
                    f"{self.filename}:{node.lineno}: {value.id}[…] — a record-relative "
                    "buffer subscript outside the sanctioned seam; read through "
                    "parser/lookahead.py or walk with a Cursor"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        if isinstance(func, ast.Attribute) and func.attr == "seek" and node.args:
            offset = self._nonzero_literal(node.args[0])
            if offset is not None:
                self.violations.append(
                    f"{self.filename}:{node.lineno}: .seek({offset}) — a fixed offset"
                )

        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name == "unpack_from" and len(node.args) >= 3:
            offset = self._nonzero_literal(node.args[2])
            if offset is not None:
                self.violations.append(
                    f"{self.filename}:{node.lineno}: unpack_from(..., {offset}) — "
                    "a constant record-relative offset"
                )

        if name.startswith(LOOKAHEAD_PREFIXES) or name in LOOKAHEAD_NAMES:
            self._judge_position(name, node)

        self.generic_visit(node)

    def _judge_position(self, name: str, node: ast.Call) -> None:
        """Judge the position handed to a lookahead — the one place a subscript rule misses.

        `peek_u32(data, position + 58)` never indexes a buffer in the caller's own source, so
        `visit_Subscript` cannot see it; the indexing happens inside the seam, where it is
        allowed. The constant is the defect and the constant is right here.
        """
        position = None
        if len(node.args) > POSITION_ARGUMENT:
            position = node.args[POSITION_ARGUMENT]
        else:
            for keyword in node.keywords:
                if keyword.arg == "position":
                    position = keyword.value

        if position is None:
            return

        for sub in ast.walk(position):
            literal = self._nonzero_literal(sub)
            if literal is not None:
                self.violations.append(
                    f"{self.filename}:{node.lineno}: {name}(…, … {literal} …) — a bare "
                    "literal in a buffer position; step over named field widths instead"
                )
            elif isinstance(sub, ast.Name) and sub.id in self._folded:
                self.violations.append(
                    f"{self.filename}:{node.lineno}: {name}(…, … {sub.id} …) — a folded "
                    "record-relative constant. Naming a magic number does not stop it being "
                    "one; derive it from field widths, as players.py does for its lookaheads"
                )


def _is_span_name(name: str) -> bool:
    """Does this identifier declare a distance rather than an address?"""
    return name.endswith(SPAN_SUFFIXES)


def _folded_constants(tree: ast.Module) -> set[str]:
    """Module-level names bound to a bare integer that are NOT declared spans.

    Three bindings, three verdicts, and only the first is a defect:

    - `_TEAM_ID_OFFSET = 58`  -> folded. A remembered address with a name on it.
    - `U32_WIDTH = 4`         -> a span, by its name. A distance to travel.
    - `_AGE_LOOKAHEAD = _BIRTH_DATE_LOOKAHEAD + DATE_WIDTH + _GAP_AFTER_BIRTH_DATE`
                              -> derived. Not a `Constant` node at all, so it never enters
                                 this set, and using it as a position stays legal. That is
                                 exactly what re-expressing those two constants bought.

    Imports contribute spans but never folded names: a name imported from another module
    cannot be resolved to a value here, so the permissive reading is the only honest one —
    and a false positive is the failure this guard cannot afford. `asname` is respected, so
    `from lookahead import U32_WIDTH as W` makes `W` a span.
    """
    folded: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom | ast.Import):
            continue
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value: ast.expr | None = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value = node.value
        else:
            continue

        if not isinstance(value, ast.Constant) or not isinstance(value.value, int):
            continue
        if isinstance(value.value, bool) or value.value == 0:
            continue
        folded.update(name for name in names if not _is_span_name(name))
    return folded


def scan_source(source: str, filename: str = "<test>") -> list[str]:
    visitor = FixedOffsetVisitor(filename, exempt=filename in EXEMPT_MODULES)
    visitor.visit(ast.parse(source))
    return visitor.violations


def parser_modules() -> list[Path]:
    """Every module the real scan covers.

    A module-level callable rather than a loop inside the test, so that Phase 4's meta-guard
    can assert against exactly the code the real test runs rather than a re-implementation of
    it. `tests/test_no_leaks.py` exposes its seams for the same reason.
    """
    modules = sorted(SCAN_ROOT.rglob("*.py"))
    assert modules, f"nothing to scan under {SCAN_ROOT} — the guard would pass vacuously"
    return modules


def parser_module_violations() -> list[str]:
    """Every violation in the real tree, as `path:line: message` strings."""
    violations: list[str] = []
    for path in parser_modules():
        rel = path.relative_to(REPO_ROOT).as_posix()
        violations.extend(scan_source(path.read_text(encoding="utf-8"), rel))
    return violations


# ── the scanner must be able to fail ─────────────────────────────────────────

OFFENDING = """
import struct

def read_rating(handle, buf):
    handle.seek(128)
    return struct.unpack_from("<H", buf, 40)[0]
"""

INNOCENT = """
import struct

def read_rating(buf, position):
    # Never seek to a fixed offset; walk sequentially. seek(0) is only a rewind.
    handle.seek(0)
    return struct.unpack_from("<H", buf, position)[0]
"""

#: The SAME defect as OFFENDING, spelled as a subscript instead of a call. This is the
#: spelling this parser's style makes likeliest, because it passes `bytes` around rather
#: than file handles — `players.py`, `teams.py` and `world.py` all read `data[...]`
#: directly. Reading `team_id` at a constant offset from a record start is the exact
#: failure the ban exists to prevent: measured, it is correct for 86.9% of players and
#: silently wrong for the rest, because `last_team_id` is elided when zero.
SUBSCRIPT_OFFENDER = """
def read_team_id(data, record_start):
    return int.from_bytes(data[record_start + 58 : record_start + 62], "little")
"""

#: The defect **folded behind a name**, and handed to the seam rather than written as a
#: subscript. No buffer is indexed in this source at all — the indexing happens inside
#: `lookahead.py`, where it is sanctioned — so `visit_Subscript` is structurally blind to it.
#: This is the shape `players.py` had at the two sites that prompted the request.
FOLDED_OFFENDER = """
from ootp_ai.parser.lookahead import peek_u32

_TEAM_ID_OFFSET = 58


def read_team_id(data: bytes, position: int) -> int | None:
    return peek_u32(data, position + _TEAM_ID_OFFSET)
"""

#: `lookahead.py:174`'s shape — stepping over a length prefix to reach its payload. The name
#: ends `_WIDTH`, so it declares a distance rather than an address.
WIDTH_SUM_INNOCENT = """
from ootp_ai.parser.lookahead import peek_bytes

LENGTH_PREFIX_WIDTH = 4


def read_payload(data: bytes, position: int, length: int) -> bytes | None:
    return peek_bytes(data, position + LENGTH_PREFIX_WIDTH, length)
"""

#: `players.py`'s shape **after Phase 5**. The constant is an offset, not a span, and its
#: name says so — it passes because it is DERIVED from field widths rather than folded from
#: a literal. This fixture is the reward for that phase: the same call site was a violation
#: before it and is legal after, with no change to the call.
DERIVED_INNOCENT = """
from ootp_ai.parser.lookahead import DATE_WIDTH, U32_WIDTH, peek_u8

_PLAYER_ID_WIDTH = U32_WIDTH
_NAME_INDEX_WIDTH = U32_WIDTH
_NAME_INDEX_COUNT = 2
_GAP_AFTER_BIRTH_DATE = 3

_BIRTH_DATE_LOOKAHEAD = _PLAYER_ID_WIDTH + _NAME_INDEX_COUNT * _NAME_INDEX_WIDTH
_AGE_LOOKAHEAD = _BIRTH_DATE_LOOKAHEAD + DATE_WIDTH + _GAP_AFTER_BIRTH_DATE


def read_age(data: bytes, position: int) -> int | None:
    return peek_u8(data, position + _AGE_LOOKAHEAD)
"""

#: `world.py:750-751`'s exact shape — the position composed into a local from named widths,
#: then handed over. Legal, and **also the residual**: the rule judges the argument, and an
#: argument that is a lone local says nothing about how it was built. See the module
#: docstring; a control in `tests/test_fixed_offset_guard_scope.py` pins the hole.
LOCAL_POSITION_INNOCENT = """
from ootp_ai.parser.lookahead import peek_date_parts

_SEQ_WIDTH = 4
_LEAGUE_ID_WIDTH = 4
_EVENT_TYPE_WIDTH = 2


def read_event_date(data: bytes, offset: int) -> tuple[int, int, int] | None:
    date_at = offset + _SEQ_WIDTH + _LEAGUE_ID_WIDTH + _EVENT_TYPE_WIDTH
    return peek_date_parts(data, date_at)
"""

#: `human_managers._is_club_landmark`'s post-Phase-2 shape — walking an array by slot. The
#: multiplier is a loop variable and the unit is a declared span, which is what array
#: arithmetic looks like when it is not hiding a constant. `slot * 4` would be flagged.
SLOT_ARITHMETIC_INNOCENT = """
from ootp_ai.parser.lookahead import U32_WIDTH, peek_u32

CLUB_SLOTS = 3


def is_landmark(data: bytes, offset: int, first: int) -> bool:
    return all(peek_u32(data, offset + slot * U32_WIDTH) == first for slot in range(1, CLUB_SLOTS))
"""


def test_the_scanner_flags_a_synthetic_offender() -> None:
    """A guard never seen to fail is not a guard."""
    violations = scan_source(OFFENDING, "offender.py")
    assert len(violations) == 2
    assert any("seek(128)" in v for v in violations)
    assert any("unpack_from(..., 40)" in v for v in violations)


def test_the_scanner_does_not_cry_wolf() -> None:
    """`seek(0)`, a named offset, and the word 'seek' in a comment are all legal."""
    assert scan_source(INNOCENT, "innocent.py") == []


def test_the_scanner_flags_a_record_relative_subscript() -> None:
    """The same defect, spelled as a slice, must not pass because of its syntax.

    `unpack_from("<I", data, 58)` is caught and `data[start + 58 : start + 62]` is not,
    though they are the same wrong read. A ban that depends on which spelling an author
    reached for is not a ban — and the uncaught spelling is the one this codebase's own
    style produces, since every walker holds `bytes` rather than a file handle.
    """
    violations = scan_source(SUBSCRIPT_OFFENDER, "subscript.py")
    assert violations, (
        "a record-relative read at a constant offset passed the guard because it was "
        "written as a subscript rather than a call"
    )


def test_the_scanner_flags_a_constant_folded_behind_a_name() -> None:
    """The hazard a subscript rule structurally cannot see.

    `peek_u32(data, position + _TEAM_ID_OFFSET)` indexes no buffer in its own source — the
    indexing happens inside `lookahead.py`, where it is sanctioned. So the location rule
    Phase 3 landed is blind to it by construction, and without this the next author can
    reintroduce the exact defect that prompted the request and get a green build.
    """
    violations = scan_source(FOLDED_OFFENDER, "src/ootp_ai/parser/probe.py")
    assert violations, "a record-relative constant handed to the seam passed the guard"
    assert "_TEAM_ID_OFFSET" in violations[0]


def test_the_scanner_flags_a_bare_literal_handed_to_the_seam() -> None:
    """The unfolded form of the same thing, and the cheaper one to write."""
    source = (
        "from ootp_ai.parser.lookahead import peek_u32\n\n\n"
        "def read(data: bytes, position: int) -> int | None:\n"
        "    return peek_u32(data, position + 58)\n"
    )
    assert scan_source(source, "src/ootp_ai/parser/probe.py")


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("width sum — lookahead.py:174", WIDTH_SUM_INNOCENT),
        ("derived offset — players.py after Phase 5", DERIVED_INNOCENT),
        ("local position — world.py:750", LOCAL_POSITION_INNOCENT),
        ("slot arithmetic — human_managers.py:254", SLOT_ARITHMETIC_INNOCENT),
    ],
)
def test_a_legitimate_position_argument_is_not_flagged(label: str, source: str) -> None:
    """Four real shapes from the tree. A rule that flagged any of them would be reverted.

    The second is the one worth noticing: that call site was a violation before Phase 5 and
    is legal after it, with **no change to the call** — only to how its constant is defined.
    """
    assert scan_source(source, "src/ootp_ai/parser/probe.py") == [], f"cried wolf on {label}"


def test_a_size_argument_is_not_judged_as_a_position() -> None:
    """Only the position is judged. `limit=` and `count` are sizes, and a rule that read
    `limit=_MAX_PAD` as an offset would fire on four real call sites."""
    source = (
        "from ootp_ai.parser.lookahead import peek_length_prefixed_ascii, zero_run_width\n\n"
        "_MAX_PAD = 256\n"
        "_MAX_STRING = 128\n\n\n"
        "def read(data: bytes, position: int) -> object:\n"
        "    zero_run_width(data, position, limit=_MAX_PAD)\n"
        "    return peek_length_prefixed_ascii(data, position, _MAX_STRING)\n"
    )
    assert scan_source(source, "src/ootp_ai/parser/probe.py") == []


def test_prose_about_seeking_does_not_trip_the_scanner() -> None:
    """The reason this is AST-based. Every parser module explains the ban in prose."""
    prose = '''
"""Never seek to a fixed offset. A read at struct.unpack_from(buf, 40) corrupts."""
# handle.seek(128) would be a bug
X = 1
'''
    assert scan_source(prose, "prose.py") == []


# ── the real scan ────────────────────────────────────────────────────────────


def test_no_parser_module_seeks_to_a_fixed_offset() -> None:
    violations = parser_module_violations()

    assert not violations, (
        "fixed-offset reads found — these pass on day-0 data and silently return the "
        "wrong field on any record with a different shape:\n" + "\n".join(violations)
    )
