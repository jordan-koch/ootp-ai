"""AC17 — the extraction cost exists, was measured, and was recorded in the warehouse.

**There is no threshold, and its absence is a ruling rather than an omission.** Decisions §6:
the operator ruled that the work takes as long as it needs. The tautology objection — *"a
test that only checks a number exists cannot fail"* — was raised, considered and accepted
deliberately, on the grounds that a threshold nobody has justified is worse than an honest
measurement. A 4-second budget invented here would eventually go red on a bigger league and
be raised without thought, which teaches a reader that the number means nothing.

So this asserts the things that *can* be wrong, and each of them has been wrong somewhere in
this project already:

* the number is **read back out of `ingest_run`**, not taken from stdout or from the object
  the loader returned. The acceptance asks what the warehouse holds, and a number that only
  ever existed in a Python attribute proves nothing about that (Phase 8b, decision 3);
* it is **not NULL**, which is the value the column carried for the whole of Phase 8a and
  which means *not measured*;
* it is **not zero**, because `parse_seconds` is nullable precisely so that "did not
  measure" and "measured instantaneous" stay different facts, and a loader that quietly
  wrote 0.0 would satisfy a NOT NULL check;
* it **covers the walk it claims to cover**, checked by parsing the same snapshot again and
  requiring the two measurements to be the same order of magnitude. That is the one part of
  the claim a stored number cannot make about itself.

What it covers is stated in `ingest.py` rather than inferred from where the timer stops:
reading the four parsed files and the five walker calls plus the agreement checks. It
excludes snapshotting, header provenance and landing.
"""

from __future__ import annotations

from collections.abc import Iterator
from time import perf_counter

import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from fixtures.warehouse import landed_probe, settings_or_skip, warehouse_or_skip
from ootp_ai.config import Settings
from ootp_ai.ingest import PARSED_FILES, IngestRun, ParsedSnapshot, parse_snapshot
from ootp_ai.warehouse.ingest_run import read_ingest_run

pytestmark = pytest.mark.gamedata

#: The loosest sanity bound that is still a bound: a full parse of ~46 MB across four files
#: is not going to take a quarter of an hour, and a number that large means the column is
#: carrying something other than seconds. This is NOT the threshold Decisions §6 rules out —
#: it is three orders of magnitude above the measured ~2 s and exists to catch a unit
#: mistake, not to police performance.
ABSURD_SECONDS = 900.0

#: How far the re-parse may drift from the recorded number before the two stop describing
#: the same work. Wide on purpose — a cold page cache, a busy machine and an antivirus scan
#: all land inside it — because the claim under test is "this measures the walk", not "the
#: walk is fast".
DRIFT_FACTOR = 10.0


@pytest.fixture(scope="module")
def settings() -> Settings:
    return settings_or_skip()


@pytest.fixture(scope="module")
def warehouse(settings: Settings) -> Iterator[Connection[DictCursor]]:
    with warehouse_or_skip(settings) as connection:
        yield connection


@pytest.fixture(scope="module")
def landed(
    settings: Settings, warehouse: Connection[DictCursor]
) -> Iterator[tuple[ParsedSnapshot, IngestRun]]:
    with landed_probe(settings, warehouse, which="probe_save") as landing:
        yield landing


def _recorded(warehouse: Connection[DictCursor], run: IngestRun) -> dict[str, object]:
    row = read_ingest_run(
        warehouse,
        save_id=run.save_id,
        sim_date=run.sim_date,
        ingest_seq=run.ingest_seq,
    )
    assert row is not None, (
        "the landing this test performed has no ingest_run row, so there is no provenance "
        "record to read the cost out of"
    )
    return row


def test_the_extraction_cost_is_recorded_in_the_warehouse(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """AC17. Read back out of the schema, not off the object that wrote it."""
    _parsed, run = landed
    recorded = _recorded(warehouse, run)

    assert "parse_seconds" in recorded
    seconds = recorded["parse_seconds"]
    assert seconds is not None, (
        "parse_seconds is NULL, which the column is nullable in order to mean 'not "
        "measured'. AC17 asks for a measurement, and this run does not carry one"
    )
    # Through `str` because the column is `DECIMAL(12,3)` and PyMySQL hands back a
    # `Decimal`; going via the text is exact and does not assume the driver's type.
    measured = float(str(seconds))
    assert measured > 0.0, (
        "parse_seconds is zero. The column is nullable precisely so that 'did not measure' "
        "and 'measured instantaneous' stay distinguishable, and a zero here has collapsed "
        "them"
    )
    assert measured < ABSURD_SECONDS


def test_the_recorded_cost_is_the_one_the_parse_produced(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The stored number is the measurement, not a number that resembles one.

    `ingest_run_values` rounds to milliseconds on the way in, so this compares at that
    resolution rather than asserting equality on a float that went through DECIMAL(12,3).
    """
    parsed, run = landed
    recorded = _recorded(warehouse, run)

    assert parsed.run.parse_seconds is not None
    assert float(str(recorded["parse_seconds"])) == pytest.approx(
        round(parsed.run.parse_seconds, 3), abs=0.001
    )


def test_the_recorded_cost_describes_the_walk_it_claims_to_describe(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """The half a stored number cannot assert about itself.

    Everything above would still pass if `parse_seconds` were the *landing* duration, or a
    constant, or the time to read one file. So the same snapshot is parsed again here, under
    a timer this module owns, and the two are required to describe the same work.

    Order-of-magnitude rather than exact: this is a wall-clock measurement on a developer
    machine, and a tight bound would be a performance test wearing a correctness test's
    clothes — which is the thing Decisions §6 ruled out.
    """
    parsed, run = landed
    recorded = float(str(_recorded(warehouse, run)["parse_seconds"]))

    started = perf_counter()
    reparsed = parse_snapshot(parsed.run.snapshot)
    independent = perf_counter() - started

    assert reparsed.run.parse_seconds is not None
    assert recorded < independent * DRIFT_FACTOR
    assert recorded > independent / DRIFT_FACTOR, (
        f"the recorded {recorded:.3f}s and an independently timed re-parse of the same "
        f"snapshot at {independent:.3f}s differ by more than {DRIFT_FACTOR}x, so the "
        "recorded number is measuring something other than the walk"
    )


def test_the_cost_is_recorded_beside_what_it_was_paid_for(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """A duration with no account of what was read is not a cost, it is a number.

    The same row carries the four files with their sizes and digests, the per-file residual
    bytes, and the per-table row counts. That is what makes the measurement answerable later
    — *"2.2 seconds for what?"* — and Phase 11's catalog is specified to read exactly these
    columns.
    """
    _parsed, run = landed
    recorded = _recorded(warehouse, run)

    sources = recorded["source_files"]
    assert isinstance(sources, list)
    named = {str(entry["name"]) for entry in sources}
    assert set(PARSED_FILES) <= named, (
        f"the run row accounts for {sorted(named)}, which does not cover the four files the "
        f"parse reads ({sorted(PARSED_FILES)})"
    )
    assert all(int(entry["size"]) > 0 for entry in sources)

    residual = recorded["residual_bytes"]
    assert isinstance(residual, dict)
    assert set(PARSED_FILES) == set(residual), (
        "the residual is not accounted per file, so a strict-tier failure would be "
        "arithmetically indistinguishable from an expected diagnostic residual"
    )

    counts = recorded["table_row_counts"]
    assert isinstance(counts, dict)
    assert counts and all(int(value) >= 0 for value in counts.values())


def test_there_is_no_threshold_and_that_is_the_ruling(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """Decisions §6, pinned so a later reader does not add one as an obvious improvement.

    The only bound this module carries is `ABSURD_SECONDS`, three orders of magnitude above
    the measured cost, and it exists to catch a unit mistake. If somebody tightens it toward
    the observed value it stops catching units and starts failing on a slow morning, which
    is how a measurement quietly becomes a budget nobody agreed to.
    """
    _parsed, run = landed
    recorded = float(str(_recorded(warehouse, run)["parse_seconds"]))

    assert ABSURD_SECONDS > recorded * 100, (
        f"the sanity bound ({ABSURD_SECONDS}s) has been tightened to within 100x of the "
        f"measured {recorded:.3f}s. The operator ruled that the work takes as long as it "
        "needs; a threshold is a scope change, not a test tweak"
    )
