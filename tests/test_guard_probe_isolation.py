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
is a defect in `src/`. See `requests/bugfix-requests/guard-probe-survives-an-interrupted-run/`.

These tests go through `parser_probe` deliberately rather than planting a file themselves.
A test that plants its own module could only be made green by teaching the guard to ignore
the file, which is a fix this diagnosis does not get to choose; driving the real fixture
means any fix that stops it poisoning the live tree turns both green.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import test_no_fixed_offsets as guard
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


def _planted_probes() -> list[Path]:
    """Every probe module sitting in the live package right now."""
    return sorted(PARSER_DIR.glob("_guard_scope*_probe.py"))


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
