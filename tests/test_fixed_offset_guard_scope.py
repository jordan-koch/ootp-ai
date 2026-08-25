"""The fixed-offset guard's SCOPE: whether it can fail, and whether it cries wolf.

`tests/test_no_fixed_offsets.py` owns *what* counts as a fixed offset. This module owns
*whether the scan means anything* — and those fail differently. A wrong rule produces a
false negative on code the scan read; a scan that reads nothing, or that reports nothing
whatever it reads, produces a false negative on everything at once and looks identical to
a clean repo.

**This repo has been bitten twice by exactly that.** The leak guard's no-op mutant left all
18 of its tests green, because every one asserted membership in a candidate set and none
asserted that anything was ever *reported*. The batching guard exited 1 on a clean checkout
for its whole life and nobody noticed, because a guard that always fails and a guard that
never runs are both invisible until someone plants something. A third instance is not a
discretionary nicety, which is why this module is not gated behind a judgment call.

## The two halves, and why neither works alone

- **Seen to fail** — a real offender written into a real `src/ootp_ai/` package on disk is
  REPORTED by the real disk scan, not merely visible to it. That package is a byte-faithful
  **mirror** rather than the live one: a probe planted in the tree the guard scans poisons
  every other reader of that tree, which cost this project five reviewer sightings and zero
  builds. `tests/fixtures/guard_trees.py` holds the reasoning, and the fidelity the mirror
  gives up is bought back by three compensating assertions below. Without this half the
  module proves the scan looks in the right places and nothing about whether it finds
  anything there.
- **Seen not to cry wolf** — every control here is derived from a **real line in the tree**
  and cited with it. `tests/test_no_fixed_offsets.py` says a guard that cries wolf gets
  loosened, and a loosened guard is worse than none; these are what stop a future widening
  from buying coverage with false positives.

## Known residuals are pinned, not left implicit

Five of these tests assert that something is **not** flagged which arguably should be. That
is deliberate: the guard cannot see a fully hoisted read, an attribute-valued buffer, an
unannotated parameter under an unexpected name, a position composed into a local before the
call, or an offset misnamed as a span. An unpinned hole is one the next reader assumes is
absent. Pinning it means a future edit that closes the hole fails here loudly and gets to
update the record on purpose.

**The position-into-a-local one is the open door**, and it is worth reading twice: unlike the
others it is a shape ordinary code produces, and `world.py:750` writes it correctly. Any rule
strict enough to catch the folded version fires on the good one too.

Each residual is also **bounded from the other side** — `test_a_partly_hoisted_read_is_still
_caught` and `test_an_annotated_buffer_under_any_name_is_still_covered` pin where the hole
stops. That matters because a residual stated too broadly is its own defect: the first draft
of this module claimed `data[at : at + 4]` slipped through, and measuring showed it does not.

See `requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/`.

Offline: no game, no MySQL.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path

import pytest

import test_no_fixed_offsets as guard
from fixtures.guard_trees import OPEN_MIRRORS, assert_owned, mirrored_package

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The LIVE package, with a role this module's fix deliberately changed: nothing here plants
#: into it any more. It is the tree the probe must never reach — asserted by
#: `test_no_probe_is_ever_written_into_the_live_package` below — and the directory
#: `tests/test_guard_probe_isolation.py` globs for residue left by an older revision.
PARSER_DIR = REPO_ROOT / "src" / "ootp_ai" / "parser"

#: A module the guard must flag. The exact shape the RCA measured: reading `team_id` at a
#: constant offset from a record start, which is correct for 86.9% of players and silently
#: wrong for the rest because `last_team_id` is elided when zero.
OFFENDER = """
def read_team_id(data: bytes, record_start: int) -> int:
    return int.from_bytes(data[record_start + 58 : record_start + 62], "little")
"""

#: The same read done the sanctioned way. Planted alongside the offender so a scan that
#: flagged everything would be caught rather than looking like a working guard.
INNOCENT = """
from ootp_ai.parser.lookahead import peek_u32


def read_team_id(data: bytes, position: int) -> int | None:
    return peek_u32(data, position)
"""


@contextmanager
def parser_probe(name: str, body: str, tree_root: Path | None = None) -> Iterator[str]:
    """Write a real module into a mirrored `src/ootp_ai/parser/` and always remove it again.

    **The probe plants in a tree it owns.** Given no `tree_root` it builds a private mirror
    and owns it for the life of the context; a caller that needs to scan the same tree opens
    `mirrored_package()` itself and passes the root in. Either way the yielded value is the
    repo-relative posix string the scan reports, so callers assert on it unchanged.

    This fixture used to plant into the live `src/ootp_ai/parser/`, arguing that a `tmp_path`
    could not serve — the scan enumerates the package on disk, so a probe outside it would
    show only that the scan reads *a* directory rather than *the* directory. **That argument
    is answered here, not abandoned.** It holds against an empty temp directory and fails
    against a byte-faithful copy: the probe still sits among the package's 37 real modules,
    byte-identical, in a real tree the scan really rglobs and really opens. What changed is
    that the tree is one nothing else reads — so an interrupted run leaves nothing in this
    repository, and no concurrent reader of the package can see this fixture's work. Both
    modes are in `requests/bugfix-requests/_done/guard-probe-survives-an-interrupted-run/`.

    What a copy cannot prove is that *production* reads the original, and that is bought back
    explicitly by the three tests above: `test_the_production_scan_root_is_the_live_package`,
    `test_the_mirror_holds_the_same_modules_as_the_live_package` and
    `test_the_tree_is_clean_test_takes_the_default_root`. Together they assert strictly more
    than the live plant ever did — it never checked where the default root pointed.
    """
    with ExitStack() as stack:
        if tree_root is not None:
            assert_owned(tree_root)
        root = tree_root if tree_root is not None else stack.enter_context(mirrored_package())
        path = root / "src" / "ootp_ai" / "parser" / name

        # Near-vacuous against a freshly built mirror, and saying so out loud is the point:
        # `mirrored_package` excludes probe residue and asserts the fresh copy reports
        # nothing, so there is by construction nothing here to clobber. It is retained for
        # the caller-supplied `tree_root` path, where two probes in one mirror would collide.
        # Letting a live check quietly decay into a tautology is the failure mode the module
        # docstring above exists to refuse, so the decay is documented rather than hidden.
        assert not path.exists(), f"{name} already exists; refusing to clobber it"

        path.write_text(body, encoding="utf-8")
        try:
            yield f"src/ootp_ai/parser/{name}"
        finally:
            path.unlink(missing_ok=True)


# --- The scan must be SEEN TO FAIL --------------------------------------------------


def test_the_scan_reports_a_planted_offender_in_a_real_package_on_disk() -> None:
    """The end-to-end property: an offender on disk is REPORTED by the real scan.

    This is the test the whole module exists for. `test_no_parser_module_seeks_to_a_fixed
    _offset` asserts the tree is clean, and a scan that read zero files or reported nothing
    would satisfy it perfectly.

    The package is a mirror, not the live one, and the name says so — a test name that
    overclaims is the bug this module was fixed for, in miniature.
    """
    with (
        mirrored_package() as tree,
        parser_probe("_guard_scope_probe.py", OFFENDER, tree_root=tree) as rel,
    ):
        violations = guard.parser_module_violations(tree)
        assert any(rel in v for v in violations), (
            "an offending module on disk was not reported; the scan is not finding what it "
            f"can see (got {len(violations)} violations, none naming the probe)"
        )


def test_the_scan_is_silent_when_the_planted_module_is_clean() -> None:
    """The other half: a module must not be flagged merely for existing.

    Paired with the test above, this is what separates a working scan from one that reports
    everything — which would also make the tree-is-clean test fail, but for a reason nobody
    could diagnose from its message.
    """
    with (
        mirrored_package() as tree,
        parser_probe("_guard_scope_clean_probe.py", INNOCENT, tree_root=tree) as rel,
    ):
        assert not [v for v in guard.parser_module_violations(tree) if rel in v]


def test_the_probe_is_removed_even_though_the_scan_read_it() -> None:
    """The `finally` still runs, even though a leftover no longer poisons anything.

    Before the fix this guarded a live hazard: a leftover `.py` under `src/` was collected by
    the next ruff, mypy and pytest run, and showed up as an untracked file in the leak guard.
    The tree is disposable now, so what remains is the weaker but real property that the
    fixture cleans up inside a mirror its caller owns and may plant in again.

    **The mirror is opened in an OUTER context deliberately.** If the probe built its own,
    the tempdir would be torn down along with it and `not path.exists()` would pass whether
    or not the `finally` ran — the one assertion in this module that proves cleanup happens
    would go tautological, which is precisely the shape the module docstring refuses.
    """
    with mirrored_package() as tree:
        planted = tree / "src" / "ootp_ai" / "parser" / "_guard_scope_cleanup_probe.py"
        with parser_probe("_guard_scope_cleanup_probe.py", OFFENDER, tree_root=tree):
            assert planted.exists()
        assert not planted.exists()


def test_no_probe_is_ever_written_into_the_live_package() -> None:
    """The isolation property, driven through the fixture that used to break it.

    Paired with `tests/test_guard_probe_isolation.py::test_no_probe_residue_is_present_in
    _the_working_tree`, and the pair is not redundant: that one OBSERVES the live package at
    module scope and catches residue an older revision left behind, which no design change
    reaches retroactively. This one DRIVES the fixture and catches a regression that re-points
    it at the live tree — the cause rather than the leftover.
    """
    # Snapshotted, not asserted empty. Residue from a PRE-FIX revision also makes this glob
    # non-empty, and that is the one case no design change reaches — reporting it is the
    # residue detector's job. Asserting emptiness here would blame this fixture for a
    # regression that has not happened and point the reader at the wrong fix.
    before = {p.name for p in PARSER_DIR.glob("_guard_scope*_probe.py")}

    with parser_probe("_guard_scope_live_tree_probe.py", OFFENDER):
        during = {p.name for p in PARSER_DIR.glob("_guard_scope*_probe.py")} - before
        assert during == set(), (
            f"the probe reached the live package while planted: {sorted(during)}. Any reader "
            "scanning src/ootp_ai/ right now goes red on a file no author wrote"
        )

    after = {p.name for p in PARSER_DIR.glob("_guard_scope*_probe.py")} - before
    assert after == set(), f"the probe left a module in the live package: {sorted(after)}"


def test_the_probe_really_plants_in_the_mirror_it_owns() -> None:
    """Anti-vacuity, and this module cannot do without it: a `parser_probe` that planted
    NOTHING AT ALL would satisfy every isolation assertion above perfectly.

    That is the "green while guarding nothing" shape the two guards in this module's opening
    docstring both had. So the plant is located positively: the exact path exists inside the
    mirror the fixture built for itself, and a scan of that tree reports the yielded string.
    Delete the `write_text` in `parser_probe` and this is the test that dies.

    **The tree is read from `OPEN_MIRRORS`, never found by globbing the OS temp root.** An
    earlier version of this test globbed `tempfile.gettempdir()` and asserted exactly one
    match — and that root is machine-global, so a second session running this same module
    counted three, and a mirror stranded by an interrupted run counted forever. Measured red
    on 10 of 12 concurrent rounds. It was this bug exactly, moved one directory up from
    `src/ootp_ai/parser/` to the temp root, inside the change that exists to retire it.
    """
    name = "_guard_scope_anti_vacuity_probe.py"

    with parser_probe(name, OFFENDER) as rel:
        assert OPEN_MIRRORS, "the fixture built no mirror of its own, so it planted nowhere"

        tree = OPEN_MIRRORS[-1]
        planted = tree / "src" / "ootp_ai" / "parser" / name
        assert planted.is_file(), (
            f"the fixture yielded {rel!r} but wrote no file at {planted}. It is not writing "
            "the module it claims to write, and every isolation assertion here would still pass"
        )

        assert [v for v in guard.parser_module_violations(tree) if rel in v], (
            "the planted module is not reported by a scan of the tree it was planted in, so "
            "the yielded string names nothing"
        )


def test_the_module_set_has_a_floor() -> None:
    """A coverage floor, because every other test here survives the set collapsing.

    A probe being reported says nothing about the other thirty-six modules going unread — the
    leak guard's collapse from ~134 files to 9 left all of its membership tests green. The
    floor sits far below the real count so ordinary churn never trips it; it exists to catch
    a collapse, not to track a number.
    """
    # No argument, against the LIVE package, on purpose: a floor measured on a mirror is a
    # floor on the mirror. This is one of the two tests here that must keep observing
    # production, and it is exactly the line a future refactor would tidy onto a tree.
    count = len(guard.parser_modules())
    assert count >= 12, (
        f"the scan covers only {count} modules; it has been covering 37. A collapse this "
        "large means a glob or a filter is swallowing the package, and the tree-is-clean "
        "test would still pass"
    )


# --- The seam: production reads the package, and a mirror is the same tree -----------
# `parser_modules` and `parser_module_violations` take a repo root so the probes here can
# plant in a tree they OWN rather than in the one every other reader of this repo scans.
# That buys isolation at the price of the end-to-end tests reading a copy, and the four
# tests below pay it in full: production still points at the live package, the copy really
# is that package, an offender in it is reported under the real path string, and the
# tree-is-clean test takes the default root.


def test_the_production_scan_root_is_the_live_package() -> None:
    """Compensating assertion (a): the guard reads the original, never a copy.

    This is the one property a mirrored probe cannot demonstrate, so it is asserted head-on.
    The allowlist strings are deliberately NOT re-checked here — `test_an_allowlisted_path
    _matches_what_the_real_scan_builds` already pins those against the paths the real scan
    builds, and a second copy would only be a second thing to forget to update.
    """
    assert guard.SCAN_ROOT == REPO_ROOT / "src" / "ootp_ai", (
        f"the production scan root is {guard.SCAN_ROOT}, not the live package — every "
        "mirrored test in this module would then prove something about a directory this "
        "project does not ship from"
    )

    # Computed WITHOUT going through `PACKAGE_RELATIVE`, deliberately. Filtering
    # `parser_modules()` on `SCAN_ROOT` would be unfailable: both are built from that same
    # constant, so every returned path is under it by construction and the check reads as a
    # second assertion while asserting nothing. Rebuilding the expected set from the literal
    # path is what catches the drift that matters — a default root, a glob or a filter that
    # stops covering the live package.
    expected = sorted((REPO_ROOT / "src" / "ootp_ai").rglob("*.py"))
    assert guard.parser_modules() == expected, (
        "a no-argument scan does not return exactly the live package's modules "
        f"(expected {len(expected)}, got {len(guard.parser_modules())}). The default root is "
        "what production uses; if it can wander, the guard guards a copy"
    )


def test_the_mirror_holds_the_same_modules_as_the_live_package() -> None:
    """Compensating assertion (b): the copy is the package — file for file, byte for byte.

    Runs against a mirror with **nothing planted**, because the set equality below is false
    by exactly one entry the moment a probe is in it. That is why this test builds its own
    bare mirror instead of sharing one with a planting test.

    Bytes as well as names: a `copytree` that dropped a subpackage fails the set equality,
    and one that copied the right names with the wrong contents fails only the bytes.
    """
    with mirrored_package() as tree:
        live = {p.relative_to(REPO_ROOT).as_posix(): p for p in guard.parser_modules()}
        mirrored = {p.relative_to(tree).as_posix(): p for p in guard.parser_modules(tree)}

        assert set(mirrored) == set(live), (
            "the mirror is not the same module set as the live package (missing "
            f"{sorted(set(live) - set(mirrored))}, extra {sorted(set(mirrored) - set(live))}). "
            "A probe module surviving in the live package from an older revision is one "
            "cause; a copytree that dropped a subpackage is the other"
        )

        differing = [
            rel for rel, path in mirrored.items() if path.read_bytes() != live[rel].read_bytes()
        ]
        assert differing == [], (
            f"the mirror's copies differ from the live modules: {differing}. A scan of a "
            "tree that only looks like the package proves nothing about the package"
        )


def test_the_mirror_reports_a_planted_offender_with_the_real_path_string() -> None:
    """The riskiest assumption the seam rests on, pinned: a mirrored offender is reported
    under the SAME repo-relative string production would report.

    If this were false the mirror would differ from the package in the only way that
    matters. Exemption is keyed on that exact string, so a mirror reporting
    `parser/lookahead.py` instead of `src/ootp_ai/parser/lookahead.py` would silently
    un-exempt the sanctioned seam — and every mirrored test would then err in the direction
    of looseness, which is the direction nobody catches.
    """
    with mirrored_package() as tree:
        planted = tree / "src" / "ootp_ai" / "parser" / "_guard_scope_seam_probe.py"
        planted.write_text(OFFENDER, encoding="utf-8")

        rel = "src/ootp_ai/parser/_guard_scope_seam_probe.py"
        violations = guard.parser_module_violations(tree)
        assert [v for v in violations if v.startswith(f"{rel}:")], (
            f"an offender planted in a mirror was not reported as {rel!r}; the mirror's "
            f"repo-relative keys do not match production's (got {violations})"
        )


def test_the_tree_is_clean_test_takes_the_default_root() -> None:
    """Compensating assertion (c): nobody can quietly point production at a mirror.

    Read from the guard's own source rather than by calling it. A call would prove only what
    today's default happens to be; this proves the production test passes no root at all, so
    a later edit handing it a tree fails here instead of passing silently.
    """
    source = inspect.getsource(guard.test_no_parser_module_seeks_to_a_fixed_offset)
    assert re.search(r"parser_module_violations\(\s*\)", source), (
        "the tree-is-clean test no longer calls parser_module_violations() with no "
        f"arguments, so the guard may be reading a tree a test owns:\n{source}"
    )


# --- The allowlist must stay small and real -----------------------------------------


def test_the_allowlist_is_exactly_two_entries() -> None:
    """An allowlist that grows is how a guard stops being one.

    The count is asserted rather than described because the cheapest way to silence this
    guard is to add a third entry, and that must be a decision someone makes against a
    failing test rather than a line that slips through review.
    """
    assert len(guard.EXEMPT_MODULES) == 2, (
        f"the allowlist has {len(guard.EXEMPT_MODULES)} entries: {guard.EXEMPT_MODULES}. "
        "Adding one is how this guard gets quietly disabled — if the addition is right, "
        "update this test deliberately and say why in the commit"
    )


@pytest.mark.parametrize("relative", guard.EXEMPT_MODULES)
def test_every_allowlisted_module_exists(relative: str) -> None:
    """A stale entry is worse than no entry: it exempts nothing and reads as if it does."""
    assert (REPO_ROOT / relative).is_file(), f"{relative} is allowlisted but does not exist"


@pytest.mark.parametrize("relative", guard.EXEMPT_MODULES)
def test_an_allowlisted_path_matches_what_the_real_scan_builds(relative: str) -> None:
    """The exemption is keyed on a repo-relative posix string, so a backslash or a leading
    `./` would silently exempt nothing. Pinned against the paths the scan actually derives."""
    # No argument, against the LIVE package, on purpose — the second of the two tests here
    # that must keep observing production. Keyed on a mirror this would pin that the mirror
    # exempts the seam, which says nothing about what the shipped tree exempts.
    built = {p.relative_to(REPO_ROOT).as_posix() for p in guard.parser_modules()}
    assert relative in built, (
        f"{relative!r} is not one of the strings the scan builds, so it exempts nothing; "
        "the real scan keys on `path.relative_to(REPO_ROOT).as_posix()`"
    )


def test_being_allowlisted_is_not_exemption_from_everything() -> None:
    """The interior rule: a sanctioned module may compute an offset from named widths, but
    never from a bare number.

    Without this the seam is a laundering route — anyone wanting a constant read need only
    move it into `lookahead.py`. Being sanctioned is the reason to be tighter, not looser.
    """
    bare = "def probe(data: bytes, position: int) -> bytes:\n    return data[position + 4 :]\n"
    violations = guard.scan_source(bare, guard.EXEMPT_MODULES[0])
    assert violations, "a bare literal inside an allowlisted module must still be flagged"
    assert "named width" in violations[0]


def test_the_allowlisted_module_may_still_use_a_named_width() -> None:
    """The counterweight. If this failed, `lookahead.py` could not do its job at all."""
    named = (
        "def probe(data: bytes, position: int) -> bytes:\n"
        "    return data[position + U32_WIDTH : position + U32_WIDTH + DATE_WIDTH]\n"
    )
    assert guard.scan_source(named, guard.EXEMPT_MODULES[0]) == []


def test_the_same_read_is_judged_differently_inside_and_outside_the_seam() -> None:
    """The rule keys on LOCATION, not syntax — the whole design decision, pinned.

    A syntactic rule cannot separate a record-relative seek from the width arithmetic this
    parser is full of, which is why the fix moved the question to *which module is doing it*.
    """
    body = "def probe(data: bytes, position: int) -> bytes:\n    return data[position + 4 :]\n"
    inside = guard.scan_source(body, guard.EXEMPT_MODULES[0])
    outside = guard.scan_source(body, "src/ootp_ai/parser/players.py")
    assert inside and outside, "the same read must be flagged in both places"
    assert "named width" in inside[0]
    assert "outside the sanctioned seam" in outside[0]


# --- Cry-wolf controls, each derived from a real line in the tree --------------------
# `tests/test_no_fixed_offsets.py` says a guard that cries wolf gets loosened, and a
# loosened guard is worse than none. Every case below is a real construction the parser
# uses today; a rule change that flags one of them is a regression even if it also catches
# more real defects. Cited with the line each was taken from, so a reader can check.

CRY_WOLF: list[tuple[str, str]] = [
    (
        # teams.py:609 — `run` is `tuple[int, ...]` (declared teams.py:596), values already
        # read through the cursor. Indexing decoded integers is not indexing the save.
        "teams.py:609 run[base + 1] — a decoded integer run, not a buffer",
        "def _readings(run: tuple[int, ...], base: int) -> tuple[int, int]:\n"
        "    return run[base], run[base + 1]\n",
    ),
    (
        # players.py:390 — `tail` is a local tuple built from six cursor.u32() calls at :389.
        "players.py:390 tail[4] — a local tuple of cursor reads",
        "def probe(cursor: object) -> int:\n"
        "    tail = tuple(cursor.u32() for _ in range(6))\n"
        "    return tail[4]\n",
    ),
    (
        # world.py:856 — `pattern` IS bytes-annotated (world.py:845), so it IS tracked as a
        # buffer. It survives only because a lone Name index carries no arithmetic and no
        # literal. This is the sharpest control here: the one case where the rule could fire
        # on a genuine bytes object and deliberately does not (gated decision G6).
        "world.py:856 pattern[_LENGTH_PREFIX_WIDTH:] — a bytes param, lone Name index",
        "def _find_unique(data: bytes, pattern: bytes, what: str) -> str:\n"
        "    return f'{what} landmark {pattern[_LENGTH_PREFIX_WIDTH:]!r} is missing'\n",
    ),
    (
        # header.py — the form that REPLACED a literal `data[0]`/`data[1:5]` pair in Phase 2.
        # If the guard flagged this, the fix it exists to encourage would be unavailable.
        "header.py startswith(MAGIC_PREFIX) — the sanctioned replacement form",
        "def looks_like_save_file(data: bytes) -> bool:\n    return data.startswith(MAGIC_PREFIX)\n",
    ),
    (
        # The legal sequential walk the guard has always permitted: a named position.
        "unpack_from with a named offset — a walk carrying its own cursor",
        "import struct\n\n\ndef probe(buf: bytes, position: int) -> int:\n"
        '    return struct.unpack_from("<H", buf, position)[0]\n',
    ),
    (
        # A zero index is a rewind or a first element, never a seek.
        "a zero index — data[0:0] and seek(0) are not fixed-offset reads",
        "def probe(data: bytes) -> bytes:\n    return data[0:0]\n",
    ),
]


@pytest.mark.parametrize(("label", "source"), CRY_WOLF, ids=[c[0].split()[0] for c in CRY_WOLF])
def test_a_real_construction_in_the_tree_is_not_flagged(label: str, source: str) -> None:
    violations = guard.scan_source(source, "src/ootp_ai/parser/probe.py")
    assert violations == [], f"cried wolf on {label}: {violations}"


# --- Known residuals, pinned so nobody assumes they are covered ----------------------
# These assert that something is NOT flagged which arguably should be. An unpinned hole is
# one the next reader assumes is absent. If a future edit closes one of these, this module
# goes red and the record gets updated on purpose rather than by accident.


def test_a_fully_hoisted_read_is_a_documented_hole() -> None:
    """Every index component a bare name — `data[at:end]` — passes.

    Closing it needs dataflow analysis inside a test module, which is a cost the RCA
    declined. It is not reachable by accident: it requires hoisting *both* ends into locals
    for no reason the surrounding code supplies.
    """
    hoisted = (
        "def probe(data: bytes, start: int) -> bytes:\n"
        "    at = start + 58\n"
        "    end = at + 4\n"
        "    return data[at:end]\n"
    )
    assert guard.scan_source(hoisted, "src/ootp_ai/parser/probe.py") == [], (
        "this hole is documented in tests/test_no_fixed_offsets.py; if it has been closed, "
        "update that docstring and this test together"
    )


@pytest.mark.parametrize(
    "index",
    ["at : at + 4", "at : at + _WIDTH", "at + 4", "at + 4 : at + 8"],
    ids=["literal-width", "named-width", "single-arith", "both-arith"],
)
def test_a_partly_hoisted_read_is_still_caught(index: str) -> None:
    """The hole is NARROWER than "a hoisted position", and this is where the edge sits.

    Measured 2026-08-18: hoisting the start alone does not evade the rule, because the
    remaining arithmetic in the index is enough to fire it. An earlier draft of the residual
    list in `tests/test_no_fixed_offsets.py` claimed `data[at : at + 4]` passed; it does not,
    and this parametrisation is what stops the claim drifting back.
    """
    source = f"def probe(data: bytes, start: int) -> bytes:\n    at = start + 58\n    return data[{index}]\n"
    assert guard.scan_source(source, "src/ootp_ai/parser/probe.py"), (
        f"data[{index}] evaded the rule; only a read whose every index component is a bare "
        "name is a documented residual"
    )


def test_an_attribute_valued_buffer_is_a_documented_hole() -> None:
    """`self._buf[start + 58]` passes; only a plain `Name` is tracked.

    `Cursor.take` at `src/ootp_ai/parser/primitives.py` is exactly this shape, and is also
    allowlisted — so closing the hole would not change today's verdict on the real tree.
    """
    attribute = (
        "class Walker:\n"
        "    def probe(self, start: int) -> bytes:\n"
        "        return self._data[start + 58 : start + 62]\n"
    )
    assert guard.scan_source(attribute, "src/ootp_ai/parser/probe.py") == []


def test_a_renamed_unannotated_parameter_is_a_documented_hole() -> None:
    """The fallback covers `data`, `buf` and `buffer` only. An unannotated parameter named
    anything else is invisible — but every buffer parameter in the tree is annotated
    `bytes`, so this hole requires deliberately dropping an annotation the codebase's mypy
    strict setting would otherwise want.
    """
    renamed = "def probe(raw, start):\n    return raw[start + 58 : start + 62]\n"
    assert guard.scan_source(renamed, "src/ootp_ai/parser/probe.py") == []


def test_an_annotated_buffer_under_any_name_is_still_covered() -> None:
    """The counterweight to the test above, and the reason the hole is narrow: the rule
    keys on the ANNOTATION first, so renaming the parameter does not evade it."""
    renamed = (
        "def probe(raw: bytes, start: int) -> bytes:\n    return raw[start + 58 : start + 62]\n"
    )
    assert guard.scan_source(renamed, "src/ootp_ai/parser/probe.py"), (
        "an annotated buffer must be tracked whatever it is called; only the UNannotated "
        "fallback is name-based"
    )


def test_a_direct_alias_of_a_buffer_is_followed() -> None:
    """`buf = data` carries the buffer. A derived slice deliberately does not — that would
    need the same dataflow analysis the hoist test declines."""
    aliased = (
        "def probe(data: bytes, start: int) -> bytes:\n"
        "    buf = data\n"
        "    return buf[start + 58 : start + 62]\n"
    )
    assert guard.scan_source(aliased, "src/ootp_ai/parser/probe.py")


def test_a_position_composed_into_a_local_is_a_documented_hole() -> None:
    """`at = offset + 58` then `peek_u32(data, at)` passes — the third mechanism's residual.

    Unlike the subscript residual, this one has a *legitimate* twin that any stricter rule
    would break: `world.py:750` composes `date_at` from three named widths and hands it over,
    which is the model form the RCA called defensible. A rule that caught the folded version
    would fire on that too, so the hole is the price of not crying wolf rather than an
    oversight.
    """
    hoisted = (
        "from ootp_ai.parser.lookahead import peek_u32\n\n\n"
        "def probe(data: bytes, offset: int) -> int | None:\n"
        "    at = offset + 58\n"
        "    return peek_u32(data, at)\n"
    )
    assert guard.scan_source(hoisted, "src/ootp_ai/parser/probe.py") == [], (
        "documented in tests/test_no_fixed_offsets.py; if closed, update both together"
    )


def test_an_offset_misnamed_as_a_span_is_a_documented_hole() -> None:
    """`_TEAM_ID_WIDTH = 58` passes. The name is the only signal, and it can be a lie.

    Pinned rather than hidden because the guard's honesty depends on it: `SPAN_SUFFIXES`
    separates a distance from an address, both are bare integers, and no value inspection can
    tell them apart. Evading this means labelling an address a distance — deliberate, not a
    slip — and the meta-guard records that the door exists.
    """
    misnamed = (
        "from ootp_ai.parser.lookahead import peek_u32\n\n"
        "_TEAM_ID_WIDTH = 58\n\n\n"
        "def probe(data: bytes, position: int) -> int | None:\n"
        "    return peek_u32(data, position + _TEAM_ID_WIDTH)\n"
    )
    assert guard.scan_source(misnamed, "src/ootp_ai/parser/probe.py") == []


def test_the_span_rule_is_not_a_blanket_pass_for_every_module_constant() -> None:
    """The counterweight: a constant that is NOT span-named is judged, so the hole above is
    a narrow door rather than an open side."""
    folded = (
        "from ootp_ai.parser.lookahead import peek_u32\n\n"
        "_TEAM_ID_OFFSET = 58\n\n\n"
        "def probe(data: bytes, position: int) -> int | None:\n"
        "    return peek_u32(data, position + _TEAM_ID_OFFSET)\n"
    )
    violations = guard.scan_source(folded, "src/ootp_ai/parser/probe.py")
    assert violations and "_TEAM_ID_OFFSET" in violations[0]


def test_the_folded_constant_rule_reports_an_offender_in_a_real_package_on_disk() -> None:
    """Seen to fail on disk, not only against a string — the same standard the subscript
    rule is held to above, and in the same kind of tree: a mirror the test owns."""
    probe = (
        "from ootp_ai.parser.lookahead import peek_u32\n\n"
        "_MUTATION_PROBE_OFFSET = 58\n\n\n"
        "def probe(data: bytes, position: int) -> int | None:\n"
        "    return peek_u32(data, position + _MUTATION_PROBE_OFFSET)\n"
    )
    with (
        mirrored_package() as tree,
        parser_probe("_guard_scope_folded_probe.py", probe, tree_root=tree) as rel,
    ):
        violations = guard.parser_module_violations(tree)
        assert any(rel in v for v in violations), (
            "a folded record-relative constant on disk was not reported by the real scan"
        )


def test_a_nested_function_does_not_leak_its_buffer_outward() -> None:
    """The buffer set is saved and restored around each function. Without that, a name
    introduced inside a nested def would keep flagging subscripts after it went out of
    scope — a false positive, which is the failure mode this guard cannot afford."""
    nested = (
        "def outer(rows: list[int]) -> int:\n"
        "    def inner(data: bytes, start: int) -> int:\n"
        "        return data[start]\n"
        "    return rows[len(rows) - 1]\n"
    )
    assert guard.scan_source(nested, "src/ootp_ai/parser/probe.py") == []
