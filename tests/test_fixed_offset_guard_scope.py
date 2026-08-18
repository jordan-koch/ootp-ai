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

- **Seen to fail** — a real offender written into `src/ootp_ai/parser/` is REPORTED by the
  real disk scan, not merely visible to it. Without this the module below proves the scan
  looks in the right places and nothing about whether it finds anything there.
- **Seen not to cry wolf** — every control here is derived from a **real line in the tree**
  and cited with it. `tests/test_no_fixed_offsets.py` says a guard that cries wolf gets
  loosened, and a loosened guard is worse than none; these are what stop a future widening
  from buying coverage with false positives.

## Known residuals are pinned, not left implicit

Three of these tests assert that something is **not** flagged which arguably should be. That
is deliberate: the guard cannot see a fully hoisted read, an attribute-valued buffer, or an
unannotated parameter under an unexpected name, and an unpinned hole is one the next reader
assumes is absent. Pinning it means a future edit that closes the hole fails here loudly and
gets to update the record on purpose.

Each residual is also **bounded from the other side** — `test_a_partly_hoisted_read_is_still
_caught` and `test_an_annotated_buffer_under_any_name_is_still_covered` pin where the hole
stops. That matters because a residual stated too broadly is its own defect: the first draft
of this module claimed `data[at : at + 4]` slipped through, and measuring showed it does not.

See `requests/bugfix-requests/fixed-offset-guard-cannot-see-subscripts/`.

Offline: no game, no MySQL.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

import test_no_fixed_offsets as guard

REPO_ROOT = Path(__file__).resolve().parent.parent
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
def parser_probe(name: str, body: str) -> Iterator[str]:
    """Write a real module into `src/ootp_ai/parser/` and always remove it again.

    A `tmp_path` fixture cannot serve: the scan enumerates the package on disk, so the
    probe has to exist inside it to be a fair test of what the scan actually reads.

    The `finally` matters more here than in most harnesses — a leftover `.py` under `src/`
    would be collected by the next `ruff`, `mypy` and `pytest` run, and would also show up
    as an untracked file in `tests/test_no_leaks.py`.
    """
    path = PARSER_DIR / name
    assert not path.exists(), f"{name} already exists; refusing to clobber it"
    path.write_text(body, encoding="utf-8")
    try:
        yield f"src/ootp_ai/parser/{name}"
    finally:
        path.unlink(missing_ok=True)


# --- The scan must be SEEN TO FAIL --------------------------------------------------


def test_the_scan_reports_a_planted_offender_in_the_real_tree() -> None:
    """The end-to-end property: an offender on disk is REPORTED by the real scan.

    This is the test the whole module exists for. `test_no_parser_module_seeks_to_a_fixed
    _offset` asserts the tree is clean, and a scan that read zero files or reported nothing
    would satisfy it perfectly.
    """
    with parser_probe("_guard_scope_probe.py", OFFENDER) as rel:
        violations = guard.parser_module_violations()
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
    with parser_probe("_guard_scope_clean_probe.py", INNOCENT) as rel:
        assert not [v for v in guard.parser_module_violations() if rel in v]


def test_the_probe_is_removed_even_though_the_scan_read_it() -> None:
    """A leftover probe would break the next lint, type-check and leak-guard run."""
    with parser_probe("_guard_scope_cleanup_probe.py", OFFENDER):
        assert (PARSER_DIR / "_guard_scope_cleanup_probe.py").exists()
    assert not (PARSER_DIR / "_guard_scope_cleanup_probe.py").exists()


def test_the_module_set_has_a_floor() -> None:
    """A coverage floor, because every other test here survives the set collapsing.

    A probe being reported says nothing about the other seventeen modules going unread — the
    leak guard's collapse from ~134 files to 9 left all of its membership tests green. The
    floor sits far below the real count so ordinary churn never trips it; it exists to catch
    a collapse, not to track a number.
    """
    count = len(guard.parser_modules())
    assert count >= 12, (
        f"the scan covers only {count} modules; it has been covering 18. A collapse this "
        "large means a glob or a filter is swallowing the package, and the tree-is-clean "
        "test would still pass"
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
