"""No test creates files in a tree a guard reads.

Two guards in this repository are proved to work by planting something offending on disk and
watching them report it. Both used to plant into the live working tree, and both were the same
defect: an interrupted run left the file behind, and any concurrent reader of that tree went
red on a file no author wrote. It cost five reviewer sightings and zero builds — the worst
ratio a defect can have, because nothing ever forced anyone to file it. See
`requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/` and ADR 0022.

Both sites are fixed. **This module is what stops a third being invented.** The convention it
enforces is one sentence:

> A guard's scope test may plant only in a tree it owns; a test that reads the live tree
> plants nothing.

## The rule, stated precisely

Within `tests/**/*.py`, a **creative** write whose **target** derives from the live checkout —
directly, or through a module constant such as `PARSER_DIR` — is a violation. These create or
extend, and a test that needs to create something can create it somewhere it owns.

The verb set starts from `tests/test_read_only.py:337`'s `CREATIVE_CALLS` — an in-repo
precedent rather than a new list — and follows that precedent to its end: the same module
defines `_WRITE_MODE_CHARS` and `_OPEN_MODE` at `:339-341` and pins them at `:396-397`, so
write-mode `open` belongs here too. `(PARSER_DIR / name).open("w")` is an entirely ordinary
spelling of the exact defect this change fixed, and the first draft of this rule could not see
it. `os.mkdir`, the `shutil` copy family keyed on its destination, and the `for` / `with` /
walrus binding forms were the other measured gaps. The full covered set, and what is still
outside it, are listed below.

**`unlink` is deliberately excluded**, and the exclusion is what keeps this guard's empty
allowlist honest: `tests/test_guard_probe_isolation.py` deletes a survivor under the live
package, on purpose, in the test whose whole job is removing residue an older revision left.
Deleting a probe that should not exist is not planting one.

## AST, never a text scan

`tests/test_read_only.py:337` holds those very verbs as string literals and `:398` asserts on a
literal `.write_bytes(` line. A substring scan would cry wolf on this repo's own write guard,
and on the two fixtures whose docstrings discuss the live tree at length. A guard that cries
wolf gets loosened, and a loosened guard is worse than none — so the rule walks the parse tree,
which ignores strings, docstrings and comments by construction.

It keys on the **target expression**, not on whether `REPO_ROOT` appears in the call at all.
Copying a real file *out of* the repo *into* a mirror is exactly what
`tests/fixtures/guard_trees.py` does, and it is the correct shape rather than a violation.

## What it does not cover, said out loud

An unpinned hole is one the next reader assumes is absent, so:

- **The taint follows names, not values.** A repo-derived path passed into a function as an
  argument, or returned from one, loses its taint at the boundary — closing that needs real
  dataflow analysis, the cost `tests/test_no_fixed_offsets.py` declined for its own
  hoisted-read residual. It is not reachable by accident. **The specific case that matters —
  a caller handing a fixture the live repo root — is covered from the other side**, by
  `fixtures.guard_trees.assert_owned`, which refuses it at runtime on every plant.
- **`from os import makedirs` and then a bare `makedirs(...)`** is invisible: the rule keys on
  the `module.function` spelling. So is any write to a bare relative-path literal, which is
  resolved against the working directory rather than a named root.
- **`unlink` and `rename` are absent by design**, not by oversight — see above.

What *is* covered: `write_text`, `write_bytes`, `touch`, `mkdir`, `os.mkdir`, `os.makedirs`,
write-mode `open` in both its builtin and method spellings, and the `shutil` copy family keyed
on its destination — against a target whose base is built from `REPO_ROOT` or from `__file__`
under any name, bound by assignment, annotation, walrus, `for` target or `with ... as`.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = REPO_ROOT / "tests"

#: Ways to create or extend a file. The first four are `tests/test_read_only.py`'s
#: `CREATIVE_CALLS`, as method names rather than source fragments. `unlink` and `rename` are
#: absent on purpose — see the docstring above.
CREATIVE_METHODS = frozenset({"write_text", "write_bytes", "touch", "mkdir"})

#: The module-function forms. `os.makedirs`/`os.mkdir` take their target first; the `shutil`
#: copy family takes it **second**, which is the whole reason the rule keys on a chosen
#: argument rather than on any mention of a live path in the call. `shutil.copytree` and
#: `shutil.copy2` are what `tests/fixtures/guard_trees.py` uses to BUILD a mirror — reading
#: out of the repo into a tree you own — so both are clean there and would report only if
#: someone reversed the arguments.
CREATIVE_FUNCTIONS: dict[tuple[str, str], int] = {
    ("os", "makedirs"): 0,
    ("os", "mkdir"): 0,
    ("shutil", "copy"): 1,
    ("shutil", "copy2"): 1,
    ("shutil", "copyfile"): 1,
    ("shutil", "copytree"): 1,
    ("shutil", "move"): 1,
}

#: Mode characters that mean a file is being created or extended. Lifted from
#: `tests/test_read_only.py:339`'s `_WRITE_MODE_CHARS`: that module pins an `open`-mode rule
#: its own tests exercise, so covering `open(path, "w")` here honours the cited precedent more
#: completely rather than inventing a rule. `(PARSER_DIR / name).open("w")` is an entirely
#: ordinary spelling of exactly the defect this change fixed.
WRITE_MODE_CHARS = frozenset("wax+")

#: Names that mean "somewhere inside the live checkout". The taint spreads from these through
#: module constants, so `PARSER_DIR`, `SCAN_ROOT` and any future `SOMETHING = REPO_ROOT / ...`
#: are covered without being listed.
#:
#: **`__file__` is seeded as well as `REPO_ROOT`, and that is not belt-and-braces.** Keyed on
#: `REPO_ROOT` alone the rule had a real hole: `tests/test_read_only.py` binds
#: `SRC = Path(__file__).resolve().parent.parent / "src" / "ootp_ai"` without ever mentioning
#: `REPO_ROOT`, and a creative write through that name would have been invisible. Measured when
#: this guard was written — five such bindings across the suite. Seeding the expression every
#: repo root is ultimately derived from closes the class rather than the instance.
ROOT_SEEDS = frozenset({"REPO_ROOT", "__file__"})

#: **Deliberately empty, and asserted to be.** An allowlist that grows is how a guard stops
#: being one, and this guard is young enough that the first entry would set the pattern. The
#: plan for this change expected one entry — this module itself, on the theory that it must
#: contain the strings it bans. Making the rule AST-based removed the need: its banned verbs
#: appear here only inside string constants and its own frozensets, which a parse tree does
#: not confuse with a call. If an entry is ever genuinely needed, that is a decision to make
#: against a failing test.
EXEMPT_MODULES: tuple[str, ...] = ()


def _mentions(node: ast.expr, names: set[str]) -> bool:
    return any(isinstance(child, ast.Name) and child.id in names for child in ast.walk(node))


def _path_base(node: ast.expr) -> ast.expr:
    """The leftmost thing a path expression is built from.

    `PARSER_DIR / name` -> `PARSER_DIR`; `Path(str(REPO_ROOT)) / "x"` -> the `Path(...)` call,
    whose arguments still carry the taint; `tmp_path / Path(__file__).name` -> `tmp_path`.

    That last one is why this exists. Testing taint against *any* name inside the target
    expression flags a write to a temp file merely NAMED after the test module — an ordinary
    idiom, and a false positive on a guard shipping an empty allowlist is how the first
    allowlist entry gets written.
    """
    while True:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            node = node.left
        elif isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            node = node.func.value  # a `.resolve()` / `.parent` chain
        else:
            return node


def _tainted_names(tree: ast.Module) -> set[str]:
    """Every name in this module that stands for a path inside the live repository.

    A fixpoint rather than a single pass, so an ordering accident cannot silently narrow the
    rule: `A = REPO_ROOT / "x"` and `B = A / "y"` taint both however they are ordered.
    """
    tainted = set(ROOT_SEEDS)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            # Every binding form, not just `=`. A live path laundered through a `for` target,
            # a `with ... as`, or a walrus is still a live path, and each of those was a way
            # around an Assign-only rule.
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            elif isinstance(node, ast.NamedExpr):
                targets, value = [node.target], node.value
            elif isinstance(node, ast.For):
                targets, value = [node.target], node.iter
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                targets, value = [node.optional_vars], node.context_expr
            else:
                continue

            if not _mentions(value, tainted):
                continue
            for target in targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name) and name.id not in tainted:
                        tainted.add(name.id)
                        changed = True
    return tainted


def _mode_is_a_write(node: ast.Call, position: int) -> bool:
    """Whether an `open`-shaped call's mode argument creates or extends."""
    mode: ast.expr | None = None
    if len(node.args) > position:
        mode = node.args[position]
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode = keyword.value

    if mode is None:
        return False  # no mode given means "r"
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return bool(WRITE_MODE_CHARS & set(mode.value))
    return True  # a computed mode is judged conservatively


def _write_target(node: ast.Call) -> ast.expr | None:
    """The expression being written to, or None if this call is not a creative write."""
    func = node.func

    # The module-function forms are tested FIRST, and the order is load-bearing: `os.mkdir`
    # ends in an attribute named `mkdir`, so a methods-first check would return the untainted
    # Name `os` and drop it before ever reaching this branch — while `os.makedirs`, whose
    # attribute is not a method name, was caught. That asymmetry was a real hole.
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        position = CREATIVE_FUNCTIONS.get((func.value.id, func.attr))
        if position is not None:
            return node.args[position] if len(node.args) > position else None

    # The builtin `open(path, "w")`.
    if isinstance(func, ast.Name) and func.id == "open":
        return node.args[0] if node.args and _mode_is_a_write(node, 1) else None

    if isinstance(func, ast.Attribute):
        if func.attr in CREATIVE_METHODS:
            return func.value
        if func.attr == "open":
            return func.value if _mode_is_a_write(node, 0) else None

    return None


def scan_source(source: str, filename: str = "<test>") -> list[str]:
    """Every creative write into the live tree in `source`, as `path:line: message` strings.

    A module-level callable taking source text, mirroring `tests/test_no_fixed_offsets.py`'s
    seam, so the guard can be asserted to REPORT rather than merely to enumerate. A scan that
    opened every file and returned nothing would satisfy an enumeration test perfectly — which
    is how a mutant scanning zero files passed this repo's whole leak suite once.
    """
    tree = ast.parse(source)
    tainted = _tainted_names(tree)

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = _write_target(node)
        if target is None or not _mentions(_path_base(target), tainted):
            continue

        verb = node.func.attr if isinstance(node.func, ast.Attribute) else "open"
        violations.append(
            f"{filename}:{node.lineno}: {verb}() into the live tree — a test may plant only "
            "in a tree it owns (ADR 0022); build one with tests/fixtures/guard_trees.py"
        )
    return violations


def suite_modules() -> list[Path]:
    """Every test module the rule covers.

    Not named `test_*`, deliberately: pytest would collect it, and a helper returning a list
    is a test that asserts nothing.
    """
    modules = sorted(p for p in TESTS_ROOT.rglob("*.py") if "__pycache__" not in p.parts)
    assert modules, f"nothing to scan under {TESTS_ROOT} — the guard would pass vacuously"
    return modules


def suite_module_violations() -> list[str]:
    violations: list[str] = []
    for path in suite_modules():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in EXEMPT_MODULES:
            continue
        violations.extend(scan_source(path.read_text(encoding="utf-8"), rel))
    return violations


# --- The rule must be SEEN TO FAIL --------------------------------------------------

OFFENDER = """
REPO_ROOT = Path(__file__).resolve().parent.parent
PARSER_DIR = REPO_ROOT / "src" / "ootp_ai" / "parser"


def probe():
    (PARSER_DIR / "_probe.py").write_text("x", encoding="utf-8")
"""


def test_the_rule_reports_a_write_into_the_live_tree() -> None:
    """The end-to-end property, and the exact shape both fixed sites used to have — including
    the indirection through a module constant, which is how `PARSER_DIR` hid the reach."""
    violations = scan_source(OFFENDER, "tests/test_probe.py")
    assert len(violations) == 1, f"expected exactly one violation, got {violations}"
    assert "write_text() into the live tree" in violations[0]


def test_a_mkdir_into_the_live_tree_is_caught_too() -> None:
    """Two of the four writes this change removed were `mkdir`s rather than file writes. A
    rule catching only file writes would have left directories being created in the live
    repository — the same mutation of shared state, one level up the tree."""
    source = 'REPO_ROOT = Path(__file__).parent\n(REPO_ROOT / "var" / "tmp").mkdir(parents=True)\n'
    assert scan_source(source, "tests/test_probe.py"), "a mkdir into the live tree must report"


#: Spellings of the same defect the first draft of this rule could not see. Each was measured
#: green — i.e. undetected — before the verb set was widened; `os.mkdir` in particular was a
#: plain ordering bug, since `mkdir` is also a method name and matched the wrong branch first.
OTHER_SPELLINGS: list[tuple[str, str]] = [
    (
        "a write-mode Path.open",
        'REPO_ROOT = Path(__file__).parent\n(REPO_ROOT / "x.py").open("w")\n',
    ),
    (
        "the builtin open in write mode",
        'REPO_ROOT = Path(__file__).parent\nopen(REPO_ROOT / "x.py", "w")\n',
    ),
    ("os.mkdir", 'import os\nREPO_ROOT = Path(__file__).parent\nos.mkdir(REPO_ROOT / "d")\n'),
    (
        "a shutil copy INTO the repo",
        "import shutil\nREPO_ROOT = Path(__file__).parent\n"
        'def f(src):\n    shutil.copy2(src, REPO_ROOT / "x.py")\n',
    ),
    (
        # `as handle`, never `as p`: a single letter followed by `:\n` matches the leak
        # guard's windows-drive-path pattern — the escape-sequence false positive
        # `tests/test_no_leaks.py:33-36` documents. Measured: it reddened that guard.
        "a live path bound by a with-statement",
        "REPO_ROOT = Path(__file__).parent\n"
        'with (REPO_ROOT / "x.py") as handle:\n    handle.write_text("x")\n',
    ),
    (
        "a live path bound by a for-target",
        'REPO_ROOT = Path(__file__).parent\nfor p in (REPO_ROOT / "x.py",):\n    p.touch()\n',
    ),
]


@pytest.mark.parametrize(("label", "source"), OTHER_SPELLINGS, ids=[s[0] for s in OTHER_SPELLINGS])
def test_another_spelling_of_the_same_write_is_caught(label: str, source: str) -> None:
    """The rule's coverage is the set of spellings it catches, not the set it was written for.

    `tests/test_read_only.py` pins an `open`-mode rule of its own, so covering these is
    honouring the cited precedent completely rather than inventing a wider one.
    """
    assert scan_source(source, "tests/test_probe.py"), f"{label} into the live tree must report"


# --- Cry-wolf controls, each derived from a real line in the suite -------------------
# Every case below is a real construction this suite uses today. A rule change that flags one
# of them is a regression even if it also catches more real defects, because the fix that
# follows a false positive is always to loosen the rule.

CRY_WOLF: list[tuple[str, str]] = [
    (
        # tests/test_snapshot_semantics.py — a write under pytest's `tmp_path`, the ordinary
        # way to need a file. The overwhelming majority of writes in this suite are this shape.
        "a write under tmp_path",
        'def test_x(tmp_path):\n    (tmp_path / "save.dat").write_bytes(b"x")\n',
    ),
    (
        # tests/test_save_enumerator.py — a write under a root a fixture built and handed over.
        # The name is local and carries no taint, which is the property being rewarded.
        "a write under a fixture-built root",
        'def test_x(tmp_path):\n    root = _make_tree(tmp_path)\n    (root / "a.dat").touch()\n',
    ),
    (
        # tests/test_fixed_offset_guard_scope.py — a REPO_ROOT-derived path CONSTRUCTION that
        # is read, never written. The rule keys on writes; building a path in order to look at
        # it is what every guard in this repo does for a living.
        "a REPO_ROOT-derived path that is read, not written",
        "REPO_ROOT = Path(__file__).parent\ndef test_x(rel):\n    assert (REPO_ROOT / rel).is_file()\n",
    ),
    (
        # tests/fixtures/guard_trees.py — the shape this very change introduces: the TARGET is
        # mirror-derived while a SOURCE argument is REPO_ROOT-derived. Copying the real tree
        # into a tree you own is the fix, not the defect, and this control is what proves the
        # rule keys on the target expression rather than on any mention of REPO_ROOT.
        "a mirror-derived target fed from a REPO_ROOT-derived source",
        "REPO_ROOT = Path(__file__).parent\n"
        "def build(root):\n"
        '    (root / ".gitignore").write_text((REPO_ROOT / ".gitignore").read_text())\n',
    ),
    (
        # tests/fixtures/guard_trees.py:101 — `shutil.copytree(LIVE_PACKAGE, root / ...)`.
        # The destination is the mirror; the SOURCE is the live package, which is the whole
        # point of a faithful copy. Keying on args[1] is what keeps the helper ADR 0022 points
        # every future author at from being reported by the guard it enables.
        "a shutil copy OUT of the repo into a mirror",
        "import shutil\nREPO_ROOT = Path(__file__).parent\n"
        "def build(root):\n    shutil.copytree(REPO_ROOT / 'src', root / 'src')\n",
    ),
    (
        # A read-mode open on a live path. Every guard in this repo opens repo files to read
        # them; flagging that would make the rule unusable in the repo it protects.
        "a read-mode open on a REPO_ROOT-derived path",
        'REPO_ROOT = Path(__file__).parent\ndef f():\n    return open(REPO_ROOT / "x.py").read()\n',
    ),
    (
        # tests/test_catalog.py and friends — a temp artifact NAMED after the test module.
        # `__file__` is a taint seed, so testing any mention inside the target would flag this;
        # keying on the base of the path expression is what makes it clean.
        "a tmp_path write whose filename is derived from __file__",
        'def test_x(tmp_path):\n    (tmp_path / Path(__file__).name).write_text("x")\n',
    ),
]


@pytest.mark.parametrize(("label", "source"), CRY_WOLF, ids=[c[0] for c in CRY_WOLF])
def test_a_real_construction_in_the_suite_is_not_flagged(label: str, source: str) -> None:
    violations = scan_source(source, "tests/test_probe.py")
    assert violations == [], f"cried wolf on {label}: {violations}"


# --- The allowlist, the seed, and the real scan --------------------------------------


def test_the_allowlist_is_empty() -> None:
    """Asserted rather than described, because the cheapest way to silence this guard is to
    add the first entry — and the first entry is what makes a second one ordinary."""
    assert EXEMPT_MODULES == (), (
        f"this guard has grown an allowlist: {EXEMPT_MODULES}. Every site it covers today can "
        "plant in a tree it owns; if one genuinely cannot, that is a decision to make against "
        "a failing test and to say out loud in the commit"
    )


def test_a_root_bound_under_another_name_is_still_covered() -> None:
    """The reason `__file__` is seeded, pinned as a control rather than left as a comment.

    `tests/test_read_only.py` binds `SRC = Path(__file__)... / "src" / "ootp_ai"` and never
    mentions `REPO_ROOT`. Keyed on `REPO_ROOT` alone, a write through that name was invisible —
    measured while writing this guard, five such bindings across the suite, which is why the
    seed set has two entries rather than the one the plan called for.
    """
    source = (
        "SRC = Path(__file__).resolve().parent.parent\n"
        'def probe():\n    (SRC / "_probe.py").write_text("x")\n'
    )
    assert scan_source(source, "tests/test_probe.py"), (
        "a repo root bound under a name other than REPO_ROOT evades the rule, so the taint "
        "seeds no longer cover the way this suite actually resolves paths"
    )


def test_the_scan_covers_the_whole_suite() -> None:
    """A coverage floor. Every assertion above survives the module set collapsing — the leak
    guard's collapse from ~134 files to 9 left all of its tests green."""
    count = len(suite_modules())
    assert count >= 40, (
        f"the contract guard scans only {count} test modules; it has been scanning 46. A "
        "collapse this large means a glob is swallowing the suite, and the test below would "
        "still pass"
    )


def test_no_test_creates_a_file_in_a_tree_a_guard_reads() -> None:
    violations = suite_module_violations()

    assert not violations, (
        "a test writes into the live repository. An interrupted run then leaves the file "
        "behind, and any concurrent reader of that tree goes red on a file no author wrote — "
        "this project's most expensive defect class, on a phantom:\n" + "\n".join(violations)
    )
