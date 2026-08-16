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

Offline: no game, no MySQL.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "src" / "ootp_ai"


class FixedOffsetVisitor(ast.NodeVisitor):
    """Flags `.seek(<nonzero literal>)` and `unpack_from(..., <nonzero literal>)`."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    @staticmethod
    def _nonzero_literal(node: ast.expr) -> int | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            if not isinstance(node.value, bool) and node.value != 0:
                return node.value
        return None

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
    visitor = FixedOffsetVisitor(filename)
    visitor.visit(ast.parse(source))
    return visitor.violations


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


def test_the_scanner_flags_a_synthetic_offender() -> None:
    """A guard never seen to fail is not a guard."""
    violations = scan_source(OFFENDING, "offender.py")
    assert len(violations) == 2
    assert any("seek(128)" in v for v in violations)
    assert any("unpack_from(..., 40)" in v for v in violations)


def test_the_scanner_does_not_cry_wolf() -> None:
    """`seek(0)`, a named offset, and the word 'seek' in a comment are all legal."""
    assert scan_source(INNOCENT, "innocent.py") == []


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
    modules = sorted(SCAN_ROOT.rglob("*.py"))
    assert modules, f"nothing to scan under {SCAN_ROOT} — the guard would pass vacuously"

    violations: list[str] = []
    for path in modules:
        rel = path.relative_to(REPO_ROOT).as_posix()
        violations.extend(scan_source(path.read_text(encoding="utf-8"), rel))

    assert not violations, (
        "fixed-offset reads found — these pass on day-0 data and silently return the "
        "wrong field on any record with a different shape:\n" + "\n".join(violations)
    )
