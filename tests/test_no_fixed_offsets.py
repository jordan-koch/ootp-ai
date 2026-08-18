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

## Two mechanisms, because one spelling was escaping

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

## What this cannot see, named so nobody assumes otherwise

- **A position hoisted into a local.** `at = start + 58` then `data[at : at + 4]` passes.
  Closing it needs dataflow analysis inside a test module.
- **An attribute-valued buffer.** `self._buf[start + 58]` passes; only a plain `Name` is
  tracked. `Cursor.take` is exactly this shape, and is also exempt.
- **`bytearray` and `memoryview` annotations.** Nothing in the tree uses either; the
  accepted set is `{bytes}` and widening it is one line when something does.
- **A renamed unannotated parameter.** The fallback covers `data`, `buf` and `buffer`.

Each is a **known** hole rather than an unnoticed one, and none is reachable by accident:
all four require writing something the surrounding code gives no reason to write. Pinning
them as executable controls — so a future edit that silently widens one fails — is Phase 4's
job, in a meta-guard over this module. Until that lands, this list is prose, and prose is
exactly what the bug being fixed here proves insufficient.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import ast
from pathlib import Path

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


class FixedOffsetVisitor(ast.NodeVisitor):
    """Flags a constant offset however it is spelled — as a call or as a subscript."""

    def __init__(self, filename: str, *, exempt: bool = False) -> None:
        self.filename = filename
        self.exempt = exempt
        self.violations: list[str] = []
        self._buffers: set[str] = set()

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

        self.generic_visit(node)


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
