"""Trees a guard's scope test may plant in, because it owns them.

A guard that reads this repository cannot be *seen to fail* unless something offending is
on disk. The obvious way to arrange that — write the offender into the tree the guard
scans, remove it in a `finally` — is itself a defect, and it is the one this module exists
to retire:

- **A run that dies before its `finally`** leaves a real file inside the scanned tree. The
  next run reports a violation in a file that is in neither git nor anyone's editor.
- **Any concurrent reader** of that tree sees the same thing *while a healthy run has the
  probe planted*, and nothing is left behind afterwards to explain the red. This is the
  shape every recorded sighting actually had: acceptance panels run their lenses
  concurrently against one working tree.

Both are the same cause — the probe is planted in the tree the guard scans — and the fix is
not a sweep, a retry or a filename the guard learns to ignore. It is ownership. See
`requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/`.

## The convention, in one sentence

**A guard's scope test may plant only in a tree it owns; a test that reads the live tree
plants nothing.** That is ADR 0022, and the builders below are what make it cheap enough to
follow that nobody invents a third way.

## What a copy costs, and what buys it back

`parser_probe`'s original docstring argued that a `tmp_path` could not serve, because the
scan enumerates the package on disk and a probe outside it would prove only that the scan
reads *a* directory. That is true of an empty temp directory and false of a **byte-faithful
copy**: the scan still rglobs a real tree, opens the package's real modules, and reports a
real offender among real neighbours.

What a copy genuinely cannot prove is that *production* reads the original. That is bought
back explicitly, by compensating assertions in the calling modules — the production root is
pinned, the mirror is asserted equal to the live package set and bytes, and the tree-is-clean
tests are pinned from their own source to call the guards with no arguments.

## Why plain context managers, and why this file

Not pytest fixtures, and not a `conftest.py` — this repo deliberately has none. The reason
`tests/fixtures/warehouse.py` gives applies here too: a reader of the calling module should
see the tree being built by name rather than inheriting it. There is a second, harder reason:
`tests/test_guard_probe_isolation.py` drives the probe inside a bare child process with no
pytest running at all, where `tmp_path` does not exist.

Import as `from fixtures.guard_trees import mirrored_package` — `fixtures` is declared
first-party at `pyproject.toml:88`, and that is the form that resolves both under pytest and
inside that child.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import test_no_fixed_offsets as fixed_offset_guard

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: The package every mirror reproduces.
LIVE_PACKAGE = REPO_ROOT / "src" / "ootp_ai"

#: The directories the leak guard's probes address. Created in every mirrored repo so that a
#: test planting into one does not have to `mkdir` inside the tree it is trying not to touch —
#: which is how two of those `mkdir`s ended up pointed at the live repository.
MIRRORED_REPO_DIRS = ("var/tmp", "tests/fixtures", "requests/bugfix-requests", "datasets")

#: Probe modules an **older** revision may have left inside the live package. Excluded from
#: every mirror, and the exclusion is load-bearing: a faithful copy of a poisoned tree is a
#: poisoned mirror, and the tests built on it would then report a violation nobody planted —
#: reintroducing this very bug at one remove. `tests/test_guard_probe_isolation.py` is what
#: reports such a survivor; the mirror simply refuses to inherit it.
PROBE_RESIDUE_GLOB = "_guard_scope*_probe.py"

#: Where mirrors are built. Defaults to the OS temp root; a caller that can reap its own
#: directory — pytest, via `tmp_path` — points this at one so nothing is stranded there.
#: An **environment variable** rather than a parameter because the only caller that needs it
#: is a bare child process reached through `parser_probe`'s fixed two-argument call shape,
#: which `tests/test_guard_probe_isolation.py`'s abort child depends on.
MIRROR_PARENT_ENV = "OOTP_GUARD_MIRROR_ROOT"

#: Mirrors this PROCESS currently has open, innermost last. A test that needs to look inside
#: the tree a fixture built for itself reads this instead of globbing the temp root — that
#: root is machine-global, so a glob there counts sibling sessions' trees and stranded ones
#: from older runs, which is this very bug relocated one directory up.
OPEN_MIRRORS: list[Path] = []


def assert_owned(root: Path) -> None:
    """Refuse a caller-supplied tree that is, or is inside, the live repository.

    The convention is enforced on every plant, not merely asserted about the fixtures' source.
    The AST tests in `tests/test_guard_probe_isolation.py` and `tests/test_leak_guard_scope.py`
    prove the fixtures cannot *reach* the live tree on their own; they cannot see a caller
    handing one in, and `parser_probe(name, body, tree_root=REPO_ROOT)` restores the original
    defect exactly. This is the check that dies loudly at the call instead.

    It lives here rather than inline in either fixture on purpose: naming `REPO_ROOT` inside
    `parser_probe` or `untracked_file` would trip the very AST tests described above.
    """
    resolved = root.resolve()
    assert resolved != REPO_ROOT and REPO_ROOT not in resolved.parents, (
        f"a probe fixture was handed {resolved}, which is inside the live repository. A "
        "guard's scope test may plant only in a tree it owns (ADR 0022) — build one with "
        "mirrored_package() or mirrored_repo(), never a path under the working tree"
    )


def _mirror_parent() -> str | None:
    configured = os.environ.get(MIRROR_PARENT_ENV)
    return configured or None


@contextmanager
def mirrored_package() -> Iterator[Path]:
    """A private repo root holding a byte-faithful copy of `src/ootp_ai/`.

    Yields the **repo** root — the directory *containing* `src/ootp_ai/` — never the package
    directory, because the fixed-offset guard's exemption keys are repo-relative posix
    strings. A mirror laid out this way yields keys byte-identical to production's, so the
    allowlist, the stricter interior rule and the reported message all behave exactly as they
    do on the live tree.

    Built under the OS temp root rather than anywhere inside this repository. A mirror under
    `var/` would recreate the bug at one remove: `tests/test_grain_contracts.py` and the leak
    guard's own enumeration both read the working tree, and the per-process temp root is
    precisely what closes the concurrent-reader mode.
    """
    prefix = f"ootp_guard_mirror_{os.getpid()}_"
    with tempfile.TemporaryDirectory(
        prefix=prefix, ignore_cleanup_errors=True, dir=_mirror_parent()
    ) as name:
        root = Path(name)
        shutil.copytree(
            LIVE_PACKAGE,
            root / "src" / "ootp_ai",
            ignore=shutil.ignore_patterns("__pycache__", PROBE_RESIDUE_GLOB),
        )

        # A fresh mirror must be clean, and saying so here is what keeps the callers'
        # clobber assertions meaningful: every probe planted into this tree is the only
        # offender in it, so `any(rel in v for v in violations)` cannot be satisfied by
        # something that was already there.
        inherited = fixed_offset_guard.parser_module_violations(root)
        assert inherited == [], (
            "a freshly built mirror already reports violations, so nothing planted in it "
            f"can be attributed to the test that planted it: {inherited}"
        )

        OPEN_MIRRORS.append(root)
        try:
            yield root
        finally:
            OPEN_MIRRORS.remove(root)


@contextmanager
def mirrored_repo() -> Iterator[Path]:
    """A private git repository carrying this repo's `.gitignore`, and nothing else.

    The leak guard's scope is a **git index**, not a directory walk — `tests/test_no_leaks.py`
    shells `git ls-files --cached --others --exclude-standard` — so un-sharing it takes a real
    repository rather than a path parameter. `git init` is enough: `ls-files --others` works
    with no commits and no configured identity.

    **It never commits, and it must not learn to.** CI has no configured `user.email`, and a
    commit would fail there while passing on a developer's machine — an intermittently red
    guard being precisely the defect this whole change exists to remove.

    The `.gitignore` is copied **verbatim**, with `copy2` rather than a re-write, because the
    guard's own measurement depends on git's last-match-wins negations: `players.csv` at the
    root is ignored while `tests/fixtures/x.dat` and `datasets/x.dat` are NOT, because the
    `!tests/fixtures/**` and `!datasets/**` negations are later rules. A mirror that ignored a
    different set would quietly move the guard's scope.
    `tests/test_leak_guard_scope.py::test_the_mirror_repo_ignores_what_this_repo_ignores` pins
    seven verdicts pairwise against the live repo rather than trusting this paragraph.
    """
    prefix = f"ootp_leak_mirror_{os.getpid()}_"
    with tempfile.TemporaryDirectory(
        prefix=prefix, ignore_cleanup_errors=True, dir=_mirror_parent()
    ) as name:
        root = Path(name)
        subprocess.run(["git", "init", "-q", str(root)], capture_output=True, check=True)
        shutil.copy2(REPO_ROOT / ".gitignore", root / ".gitignore")

        for relative in MIRRORED_REPO_DIRS:
            (root / relative).mkdir(parents=True, exist_ok=True)

        yield root
