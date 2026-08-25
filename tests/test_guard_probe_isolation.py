"""The guard's own probe must not poison the tree the guard scans.

`tests/test_fixed_offset_guard_scope.py` proves the fixed-offset scan can be *seen to
fail* by writing a real offending module into the live `src/ootp_ai/parser/` package and
removing it in a `finally`. That fidelity is worth having — a probe in `tmp_path` proves
the scan reads *a* directory rather than *the* directory — but it is bought by mutating a
shared resource that `tests/test_no_fixed_offsets.py` reads, and the two tests below are
the two ways that bill comes due:

- **A run that does not survive to its `finally`** leaves a real `.py` inside the package.
  The next run reports a fixed-offset violation in a file that is in neither git nor
  anyone's editor — this project's most expensive defect class, on a phantom.
- **Any reader that scans the tree while a probe is planted** sees the same thing, with
  nothing left behind afterwards to explain it. This is the shape every recorded sighting
  actually had: acceptance panels run their lenses concurrently against one working tree.

Both are the same cause — the probe is planted in the tree the guard scans — and neither
is a defect in `src/`. See `requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/`.

These tests go through `parser_probe` deliberately rather than planting a file themselves.
A test that plants its own module could only be made green by teaching the guard to ignore
the file, which is a fix this diagnosis does not get to choose; driving the real fixture
means any fix that stops it poisoning the live tree turns both green.

## How it was fixed, and what that costs these two tests

`parser_probe` now plants into a byte-faithful mirror of the package built under the OS temp
root — `tests/fixtures/guard_trees.py` — so both modes close at once, and the two tests below
went green **without a single assertion here being edited**. The guard was *not* taught to
recognise probe filenames: that is a per-site exemption registry, which ADR 0020 forecloses
outright (`docs/decisions/0020-sanctioned-lookahead-seam.md:92-93`), and
`test_the_guard_has_not_learned_the_probe_filenames` below keeps the refusal mechanical.

**Be honest about the regression value of the second test now.** Post-fix, `leaked == []` is
satisfied by a fixture that plants nothing at all, so it no longer distinguishes a working
probe from a vacuous one. What carries that property instead is named, not assumed:
`test_the_probe_really_plants_in_the_mirror_it_owns` and
`test_no_probe_is_ever_written_into_the_live_package` in
`tests/test_fixed_offset_guard_scope.py`, plus
`test_the_mirror_reports_a_planted_offender_with_the_real_path_string` there. The first test
below keeps its full value: `os._exit` still cannot be intercepted.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import ast
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path

import test_no_fixed_offsets as guard
from fixtures.guard_trees import MIRROR_PARENT_ENV
from test_fixed_offset_guard_scope import OFFENDER, PARSER_DIR, parser_probe

REPO_ROOT = Path(__file__).resolve().parent.parent

#: A distinctive exit code, so "the child died inside the probe" is provable rather than
#: assumed. An import error or a changed fixture signature exits 1 and fails differently.
ABORTED_INSIDE_PROBE = 97

#: The interrupted run, reduced to its essentials: enter the probe, then die in a way no
#: `finally`, `atexit` hook or signal handler can intercept. `os._exit` is what a tool
#: timeout, a `Ctrl-C` at the wrong moment or a killed process do to this fixture.
ABORT_CHILD = """\
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "tests"))

from test_fixed_offset_guard_scope import OFFENDER, parser_probe

with parser_probe("_guard_scope_abort_probe.py", OFFENDER):
    os._exit(97)
"""


#: Names that, if the fixture could reach one, would put a probe back in the live tree.
#: Asserted structurally rather than by a required parameter — see the AST test below.
LIVE_TREE_NAMES = frozenset({"PARSER_DIR", "REPO_ROOT"})


#: Where the leak guard's scope test used to plant, as repo-relative globs. **Hardcoded, with
#: their origin cited, and deliberately not imported from the module that owns them**: a
#: residue detector that imported the module whose residue it hunts would fail to collect if
#: that module ever broke — exactly when residue is most likely. Taken from
#: `tests/test_leak_guard_scope.py` at the repo root, `var/tmp/`, `requests/bugfix-requests/`
#: and `tests/fixtures/`. The leading `*` catches `café_leak_guard_probe.md` too.
LEAK_PROBE_GLOBS = (
    "*leak_guard*probe*",
    "var/tmp/*leak_guard*probe*",
    "requests/bugfix-requests/*leak_guard*probe*",
    "tests/fixtures/*leak_guard*probe*",
)


def _planted_probes() -> list[Path]:
    """Every probe module sitting in the live package right now."""
    return sorted(PARSER_DIR.glob("_guard_scope*_probe.py"))


def _planted_leak_probes() -> list[Path]:
    """Every leak-guard probe sitting in the live working tree right now."""
    return sorted(path for glob in LEAK_PROBE_GLOBS for path in REPO_ROOT.glob(glob))


def _strings_the_module_uses(source: str) -> list[str]:
    """Every string literal in `source`, minus docstrings.

    Docstrings are where this repo's guards legitimately cite one another by module name, and
    the sibling being cited — `tests/test_fixed_offset_guard_scope.py` — has the searched-for
    token inside its own filename. Dropping docstrings separates prose from the strings the
    code actually acts on, which is the same AST-over-substring argument this module already
    makes for the fixture-reach test. Comments never enter the tree at all.
    """
    tree = ast.parse(source)
    scopes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    docstrings = set()
    for node in ast.walk(tree):
        if not isinstance(node, scopes) or not node.body:
            continue
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                docstrings.add(id(first.value))

    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def test_a_run_that_dies_inside_the_probe_leaves_no_module_behind(tmp_path: Path) -> None:
    """The durability property, stated as the bug report states it: a fixture leaves no
    trace in the source tree, **however it exits**.

    A `try/finally` is not a guarantee when the failure mode is precisely the process not
    surviving to run it, and this is the assertion that says so out loud.
    """
    script = tmp_path / "abort_inside_probe.py"
    script.write_text(ABORT_CHILD, encoding="utf-8")

    try:
        child = subprocess.run(
            [sys.executable, str(script), str(REPO_ROOT)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            # `os._exit` skips `TemporaryDirectory`'s finalizer, so the mirror the fixture
            # built for the child is stranded by design — that is inherent to reproducing an
            # uninterruptible death. Pointing mirrors at `tmp_path` hands the cleanup to
            # pytest's own retention policy, which bounds it at the last few runs instead of
            # accumulating a ~646 KB tree per suite run in the OS temp root forever. ABORT_CHILD
            # itself is untouched: it still calls `parser_probe` with two positional arguments
            # and still exercises the default-root path, which is what a real run does.
            env={**os.environ, MIRROR_PARENT_ENV: str(tmp_path)},
        )
        assert child.returncode == ABORTED_INSIDE_PROBE, (
            "the child never reached the probe, so this test proved nothing about "
            f"cleanup (exit {child.returncode}). If the fixture's signature changed, "
            f"ABORT_CHILD must change with it.\n{child.stderr}"
        )

        survivors = [p.relative_to(REPO_ROOT).as_posix() for p in _planted_probes()]
        assert survivors == [], (
            "an interrupted run left a real module inside the scanned package: "
            f"{survivors}. The next run of tests/test_no_fixed_offsets.py reports it as a "
            "fixed-offset violation in a file that is in neither git nor anyone's editor"
        )
    finally:
        for survivor in _planted_probes():
            survivor.unlink(missing_ok=True)


def test_the_real_scan_does_not_report_a_probe_a_sibling_test_has_planted() -> None:
    """The concurrency property, and the one every recorded sighting actually had.

    While the probe is on disk, *any* reader of the package sees it — the acceptance
    panels that hit this five times run their lenses concurrently against one working
    tree, so the reader was a different pytest session and nothing was left behind
    afterwards to explain the red.

    Sequential and deterministic here: a scan performed while a probe is planted is
    exactly what a concurrent reader performs, without needing a second process to race.
    """
    with parser_probe("_guard_scope_isolation_probe.py", OFFENDER) as rel:
        leaked = [v for v in guard.parser_module_violations() if rel in v]

    assert leaked == [], (
        "the fixture's probe is visible to the real tree-is-clean scan, so any reader of "
        f"the package while it is planted goes red on a file no author wrote: {leaked}"
    )


# --- What no design change reaches, and what the fix refused to do -------------------


def test_no_probe_residue_is_present_in_the_working_tree() -> None:
    """The one case no design change reaches: a probe left by an OLDER revision.

    Nothing in the tree today can plant here — `parser_probe` builds its own mirror, and
    `tests/test_fixed_offset_guard_scope.py::test_no_probe_is_ever_written_into_the_live
    _package` drives the fixture to prove it. But a checkout that ran the pre-fix code and
    died inside the probe left a real module behind, and no fix is retroactive.

    **It reports; it does not sweep**, and the refusal is deliberate on three counts. A sweep
    fixes neither mode — the file is a symptom, and the concurrent-reader mode never leaves
    one behind at all. Deleting it silently destroys the evidence the next reader needs to
    explain a red they have already seen. And a session-scoped sweep would need this repo's
    first `conftest.py`.

    Probe filenames are deliberately **not** gitignored either. An untracked file showing up
    in `git status --porcelain --untracked-files=all` is the signal the original bug report
    used to identify the phantom; an ignore rule would take that signal away.

    **Both sites, not just this module's own.** The leak guard's scope test had the identical
    shape and a worse survivor: its probe bodies carry a deliberately banned machine-path
    string, so one left behind reddens `tests/test_no_leaks.py` — the only leak protection a
    public repository has.
    """
    residue = [
        p.relative_to(REPO_ROOT).as_posix() for p in _planted_probes() + _planted_leak_probes()
    ]
    assert residue == [], (
        f"a test fixture survived an interrupted run of an OLDER revision: {residue}. "
        "Delete it. Nothing in this tree writes there any more, the file is in neither git "
        "nor anyone's editor, and until it is gone it reddens the guard it was probing — "
        "tests/test_no_fixed_offsets.py for a parser probe, tests/test_no_leaks.py for a leak "
        "probe. See requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/"
    )


def test_the_probe_fixture_cannot_reach_the_live_package() -> None:
    """The structural half of the convention: there is no code path from the fixture to the
    live tree at all.

    Stronger than making the tree root a required parameter, and cheaper: `parser_probe`
    keeps its two-positional call shape, which is exactly what lets `ABORT_CHILD` above go on
    working unedited.

    **AST, not a substring scan**, and that is not fussiness. `parser_probe` legitimately
    contains the literal `"src/ootp_ai/parser/"` in the string it yields, and its docstring
    discusses the live package at length — a text scan would cry wolf on the very code this
    fix mandates. Walking the parse tree ignores strings, docstrings and comments by
    construction.
    """
    reached = sorted(
        {
            node.id
            for node in ast.walk(ast.parse(inspect.getsource(parser_probe)))
            if isinstance(node, ast.Name) and node.id in LIVE_TREE_NAMES
        }
    )
    assert reached == [], (
        f"the probe fixture can reach the live tree again through {reached}. Whatever it "
        "plants is then visible to every other reader of this repository, which is the bug "
        "this module exists to keep fixed"
    )


def test_the_guard_has_not_learned_the_probe_filenames() -> None:
    """ADR 0020's refusal, made mechanical: the guard knows nothing about its own tests.

    The tempting fix here was to teach `tests/test_no_fixed_offsets.py` to recognise a probe
    by name and report *"a fixture survived an interrupted run"* instead of a violation. That
    is a per-site exemption registry, which
    `docs/decisions/0020-sanctioned-lookahead-seam.md:92-93` forecloses outright — and after
    the mirror fix it is unreachable dead code sitting inside the enforcement of this repo's
    most load-bearing rule.

    A prose criterion checked once never fires again, so the refusal is a test.

    Keyed on the probe **filename shape** rather than on the bare `_guard_scope` token,
    because that token is a substring of this module's own sibling — `tests/test_fixed_offset
    _guard_scope.py`, which the guard legitimately cites four times. Pinning the bare token
    would cry wolf on documentation, and a guard that cries wolf gets loosened.
    """
    source = (REPO_ROOT / "tests" / "test_no_fixed_offsets.py").read_text(encoding="utf-8")
    message = (
        "the fixed-offset guard now names a test fixture's files. That is a per-site "
        "exemption registry inside the fixed-offset ban, refused by ADR 0020; the isolation "
        "this module proves is what makes it unnecessary"
    )
    assert not re.search(r"_guard_scope\w*_probe", source), message

    # Second clause, because the first is evadable in the exact direction it guards:
    # `if path.name.startswith("_guard_scope")` and `PROBE_PREFIX = "_guard_scope"` contain no
    # `_probe` and would sail through. Stripping docstrings by AST leaves only strings the
    # module actually USES, so the four legitimate prose citations of this module's sibling —
    # `test_fixed_offset_guard_scope.py`, whose own filename contains the token — are ignored
    # by construction rather than by an exemption. Comments never reach the tree at all.
    used = [s for s in _strings_the_module_uses(source) if "_guard_scope" in s]
    assert used == [], f"{message}. Found in strings the guard actually uses: {used}"
