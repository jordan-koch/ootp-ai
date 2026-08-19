"""Snapshots are immutable, and that is what makes a past decision re-examinable.

`.claude/agents/data-engineer.md` puts it as a rule: a snapshot, once written, is
never modified. The reason is downstream of everything this project is for. The
warehouse can be rebuilt from a snapshot; a snapshot cannot be rebuilt from the game,
because the game moves forward and Challenge Mode has no undo. So the bytes the GM's
decision was actually made from either survive on disk or are gone.

Three properties carry that, and each is tested here rather than described:

**A snapshot directory is written once.** Re-snapshotting an existing
`(save_id, sim_date, ingest_seq)` refuses loudly instead of overwriting.

**A second look at the same in-game date is a new `ingest_seq`, not an overwrite.**
Plan §2.3(d): the operator executes an action on 2024-03-07 and wants the club before
and after. The sim date has not moved. Both states are retrievable, and the first is
bit-identical after the second lands.

**The copy is provably the source.** Per-file size and SHA-256, recorded at copy
time, so a later disagreement between the warehouse and the game is triaged against
bytes rather than memory.

The offline half builds a synthetic save from `tests/fixtures/synthetic.py` and needs
no game, so CI enforces all three. The `gamedata` half confirms the same properties
on the disposable Challenge Mode probe — never on the managed league, which this
module has no reason to touch.

## AC10, and being precise about which test closes which clause

The warehouse clauses arrived with the loader in Phase 8b and are below: a re-load of a
landed triple refuses and changes no count and no checksum; two sequences of one sim date
both persist with neither disturbing the other; two universes land side by side; and
parsing the same snapshot twice is byte-identical.

AC10's *"loading a second `snapshot_date` leaves the first snapshot's rows bit-identical"*
is covered **twice**, and it is worth being precise about which half is the criterion.
`test_two_sequences_of_one_sim_date_both_persist` varies `ingest_seq`, which is the
operator's real case and the reason that column exists — but it is **not** a stronger
version of the criterion, and an earlier draft of this docstring claimed it was. Two
sequences and two dates each differ in exactly one key column, so neither is harder; the
seq case is a *different* case, not a superset.

The literal clause is therefore closed literally, by
`test_a_landing_at_another_sim_date_is_left_untouched`, which digests a triple already in
the warehouse at a different `sim_date` and re-asserts it after a landing. It costs one
extra digest and no extra landing, and it skips loudly by name if no such triple exists so
it can never pass vacuously — which matters because nothing else in this suite varies the
date-valued key column at all.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from fixtures.synthetic import make_header
from fixtures.warehouse import (
    landed_probe,
    purge_snapshot,
    save_or_skip,
    settings_or_skip,
    warehouse_or_skip,
)
from ootp_ai.config import DEFAULT_SNAPSHOT_ROOT, ConfigError, SaveRef, Settings, load_settings
from ootp_ai.contracts.loader import Contracts, load_contracts
from ootp_ai.ingest import IngestRun, ParsedSnapshot, dump_parse
from ootp_ai.parser.header import read_header
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.snapshot import (
    SNAPSHOT_FILES,
    Snapshot,
    SnapshotCorrupt,
    SnapshotExists,
    next_ingest_seq,
    read_manifest,
    take_snapshot,
    verify_snapshot,
)
from ootp_ai.warehouse.ingest_run import IngestRunExists, as_sql_date, read_ingest_run
from ootp_ai.warehouse.load import land_snapshot, table_digest

REPO_ROOT = Path(__file__).resolve().parent.parent

SYNTHETIC_SIM_DATE = (7, 3, 2024)
SYNTHETIC_SIM_DATE_TEXT = "2024-03-07"

#: Present in a save, deliberately NOT in scope for the copy. `retired.dat` is 154 MB
#: of players nobody on the roster is; `challenge.dat` is a 241-byte integrity blob
#: that is not ours to move around. The snapshot copies a **named set**, never a
#: directory — a sweep would quietly grow the copy every time OOTP adds a file.
NOT_COPIED = ("retired.dat", "challenge.dat", "scouting.dat")

#: Files the set must contain, whatever else it grows. `world.dat` joined in Phase 5
#: under ADR 0018's tier-2 rule (operator-disposed 2026-08-16): division membership
#: and the league calendar are there and nowhere else, so a snapshot without it cannot
#: reproduce a parse. `human_managers.dat` is 835 bytes and is the **only** file that
#: names the club we manage — measured, offsets 231/235/239 read 4/4/6 across the
#: three saves — so omitting it would make provenance unresolvable from the copy.
REQUIRED_IN_SET = ("teams.dat", "players.dat", "names.dat", "world.dat", "human_managers.dat")


# ── a synthetic save, so the whole contract runs offline ─────────────────────


def _make_save(root: Path, name: str = "Synthetic") -> SaveRef:
    """A save directory whose files carry real headers and junk bodies.

    The bodies differ per file so a copy that mixed two of them up would show as a
    digest mismatch rather than passing.
    """
    path = root / f"{name}.lg"
    path.mkdir(parents=True)
    for index, filename in enumerate(SNAPSHOT_FILES):
        header = make_header(filename=filename, sim_date=SYNTHETIC_SIM_DATE)
        (path / filename).write_bytes(header + bytes([index + 1]) * (64 * (index + 1)))
    for filename in NOT_COPIED:
        (path / filename).write_bytes(make_header(filename=filename) + b"\xff" * 32)
    return SaveRef(league=name, root=root)


def _stat_facts(path: Path) -> dict[str, tuple[int, int]]:
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(path.glob("*.dat"))}


# ── the copy is the source ───────────────────────────────────────────────────


def test_a_snapshot_copies_exactly_the_in_scope_files(tmp_path: Path) -> None:
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")

    assert {f.name for f in snap.files} == set(SNAPSHOT_FILES)
    assert {p.name for p in snap.path.glob("*.dat")} == set(SNAPSHOT_FILES)
    for excluded in NOT_COPIED:
        assert not (snap.path / excluded).exists(), (
            f"{excluded} was copied. The snapshot is a named set, not a directory "
            "sweep — retired.dat alone is 154 MB and out of scope."
        )


def test_the_snapshot_set_holds_every_file_a_parse_depends_on() -> None:
    """Widening this set is ADR 0018 tier 2 and belongs in a request, not a refactor.

    Narrowing it is the failure this guards. A snapshot that omits a file the parser
    needs is not a smaller snapshot — it is one that cannot be re-parsed without the
    game, which is the entire property snapshots exist to provide.
    """
    missing = [name for name in REQUIRED_IN_SET if name not in SNAPSHOT_FILES]
    assert not missing, (
        f"SNAPSHOT_FILES no longer copies {missing}. Division membership and the "
        "league calendar live only in world.dat, and human_managers.dat is the only "
        "file naming the club we manage — a snapshot without them is not re-parseable."
    )


def test_every_copied_byte_matches_the_source(tmp_path: Path) -> None:
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")

    for filename in SNAPSHOT_FILES:
        assert (snap.path / filename).read_bytes() == (save.path / filename).read_bytes()


def test_the_manifest_records_the_size_and_digest_of_each_file(tmp_path: Path) -> None:
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")

    assert len(snap.files) == len(SNAPSHOT_FILES)
    for entry in snap.files:
        assert entry.size == (save.path / entry.name).stat().st_size
        assert len(entry.sha256) == 64, "a SHA-256 is 64 hex characters"
    digests = {entry.sha256 for entry in snap.files}
    assert len(digests) == len(snap.files), "two files share a digest — a copy went wrong"


def test_the_manifest_round_trips_from_disk(tmp_path: Path) -> None:
    """A snapshot outlives the process that wrote it, or it is not a snapshot."""
    save = _make_save(tmp_path / "games")
    written = take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    assert read_manifest(written.path) == written


def test_verify_detects_a_tampered_snapshot(tmp_path: Path) -> None:
    """The manifest exists to be checked, so prove checking it works."""
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    verify_snapshot(snap.path)

    target = snap.path / SNAPSHOT_FILES[0]
    payload = bytearray(target.read_bytes())
    payload[-1] ^= 0xFF  # same length, one bit different
    target.write_bytes(bytes(payload))

    with pytest.raises(SnapshotCorrupt, match=SNAPSHOT_FILES[0]):
        verify_snapshot(snap.path)


def test_snapshotting_does_not_touch_the_source(tmp_path: Path) -> None:
    """ADR 0001 in miniature, on a tree that can be safely broken."""
    save = _make_save(tmp_path / "games")
    before = _stat_facts(save.path)
    take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    assert _stat_facts(save.path) == before


# ── immutability, and the seq that keeps it from being a wall ────────────────


def test_the_snapshot_path_is_save_id_then_sim_date_then_seq(tmp_path: Path) -> None:
    """The key and the path are the same three components, in the same order.

    Plan §2.3(d) keys every bronze row `(save_id, sim_date, ingest_seq)`. A snapshot
    directory that is keyed differently is a second grain nobody declared, and the
    first thing to disagree with the warehouse.
    """
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=root)

    assert snap.path.relative_to(root).parts == (save.save_id, SYNTHETIC_SIM_DATE_TEXT, "1")
    assert snap.save_id == save.save_id
    assert str(snap.sim_date) == SYNTHETIC_SIM_DATE_TEXT
    assert snap.ingest_seq == 1


def test_the_sim_date_comes_from_the_header_not_the_wall_clock(tmp_path: Path) -> None:
    """The league's date, not ours. A key built from the clock drifts off the league."""
    save = _make_save(tmp_path / "games")
    snap = take_snapshot(save, snapshot_root=tmp_path / "snapshots")
    header = read_header((save.path / "teams.dat").read_bytes(), "teams.dat")
    assert snap.sim_date == header.sim_date


def test_a_second_snapshot_of_the_same_sim_date_gets_the_next_seq(tmp_path: Path) -> None:
    """The operator's real case: the club before and after an executed action."""
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    first = take_snapshot(save, snapshot_root=root)

    (save.path / "teams.dat").write_bytes(
        make_header(filename="teams.dat", sim_date=SYNTHETIC_SIM_DATE) + b"\x99" * 128
    )
    second = take_snapshot(save, snapshot_root=root)

    assert (first.ingest_seq, second.ingest_seq) == (1, 2)
    assert first.path != second.path
    assert str(first.sim_date) == str(second.sim_date), "the in-game date did not move"


def test_the_earlier_seq_is_bit_identical_after_a_later_one_lands(tmp_path: Path) -> None:
    """Append-only means the first state is still exactly the first state."""
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    first = take_snapshot(save, snapshot_root=root)
    before = {p.name: p.read_bytes() for p in sorted(first.path.iterdir())}

    (save.path / "players.dat").write_bytes(
        make_header(filename="players.dat", sim_date=SYNTHETIC_SIM_DATE) + b"\x77" * 256
    )
    take_snapshot(save, snapshot_root=root)

    assert {p.name: p.read_bytes() for p in sorted(first.path.iterdir())} == before
    verify_snapshot(first.path)


def test_rewriting_an_existing_snapshot_refuses(tmp_path: Path) -> None:
    """Immutability is enforced, not documented.

    `take_snapshot` allocates a fresh seq, so reaching this needs the seq named
    explicitly — which is exactly what a re-run script or a retry would do.
    """
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")
    first = take_snapshot(save, snapshot_root=root)

    with pytest.raises(SnapshotExists):
        take_snapshot(save, snapshot_root=root, ingest_seq=first.ingest_seq)


def test_next_ingest_seq_starts_at_one_and_counts_up(tmp_path: Path) -> None:
    root = tmp_path / "snapshots"
    save = _make_save(tmp_path / "games")

    assert next_ingest_seq(root, save.save_id, SYNTHETIC_SIM_DATE_TEXT) == 1
    take_snapshot(save, snapshot_root=root)
    assert next_ingest_seq(root, save.save_id, SYNTHETIC_SIM_DATE_TEXT) == 2


def test_two_universes_at_the_same_sim_date_do_not_collide(tmp_path: Path) -> None:
    """`save_id` separates universes. Without it these two would be one snapshot."""
    root = tmp_path / "snapshots"
    boston = take_snapshot(_make_save(tmp_path / "a", "OOTP-AI"), snapshot_root=root)
    probe = take_snapshot(_make_save(tmp_path / "b", "Test Save"), snapshot_root=root)

    assert boston.path != probe.path
    assert boston.ingest_seq == probe.ingest_seq == 1
    assert boston.save_id != probe.save_id


def test_a_save_id_never_carries_a_separator_into_a_path(tmp_path: Path) -> None:
    """The real save names contain spaces and dashes; a key may not."""
    snap = take_snapshot(
        _make_save(tmp_path / "games", "Test Save - Challenge Mode"),
        snapshot_root=tmp_path / "snapshots",
    )
    assert snap.save_id == "Test-Save-Challenge-Mode"
    assert " " not in snap.save_id


# ── the snapshot root is never tracked ───────────────────────────────────────


def _is_git_ignored(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
        ).returncode
        == 0
    )


def _tracked_under(path: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _assert_never_tracked(path: Path, *, label: str) -> None:
    """Either outside the worktree, or ignored inside it. Both are safe; nothing else.

    AC14's earlier phrasing asked for "outside the git worktree", which the default
    root cannot satisfy — `var/` is inside the worktree and merely ignored. A
    configured root, though, genuinely can be outside it, and that is *safer* rather
    than a failure, so the assertion admits both.
    """
    inside = path.resolve().is_relative_to(REPO_ROOT)
    if inside:
        assert _is_git_ignored(path), (
            f"{label} resolves inside the repo and is NOT git-ignored. A snapshot is "
            "OOTP's data and this repo is public (ADR 0006)."
        )
    assert not _tracked_under(path), f"{label} already has tracked files under it"


def test_the_default_snapshot_root_is_git_ignored() -> None:
    """Runs in CI, where there is no `.env` — so the default is what CI can prove."""
    _assert_never_tracked(REPO_ROOT / DEFAULT_SNAPSHOT_ROOT, label="the default snapshot root")


# ── gamedata: the disposable probe only ──────────────────────────────────────


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings: {exc}")


def _probe() -> SaveRef:
    settings = _settings()
    if settings.probe_save is None:
        pytest.skip("OOTP_PROBE_LEAGUE is unset — no disposable save to snapshot")
    return settings.probe_save


@pytest.mark.gamedata
def test_the_configured_snapshot_root_is_never_tracked() -> None:
    _assert_never_tracked(_settings().snapshot_root, label="OOTP_SNAPSHOT_ROOT")


@pytest.mark.gamedata
def test_a_real_snapshot_of_the_probe_carries_the_whole_set(tmp_path: Path) -> None:
    snap = take_snapshot(_probe(), snapshot_root=tmp_path)

    assert {entry.name for entry in snap.files} == set(SNAPSHOT_FILES)
    for entry in snap.files:
        assert (snap.path / entry.name).stat().st_size == entry.size
    verify_snapshot(snap.path)
    assert isinstance(snap, Snapshot)


@pytest.mark.gamedata
def test_a_real_snapshot_is_the_size_the_measurement_predicts(tmp_path: Path) -> None:
    """~55 MB across the set. A band, not the measured sizes.

    Exact sizes would go red the moment the operator legitimately sims the probe,
    which is what the probe is for. A truncated or empty copy still fails. The band
    was already wide enough to absorb `world.dat`'s 8.9 MB, so Phase 5's widening did
    not move it — worth knowing, because a band that never has to move is a band that
    might not be measuring anything.
    """
    total = sum(entry.size for entry in take_snapshot(_probe(), snapshot_root=tmp_path).files)
    assert 20_000_000 < total < 120_000_000, f"snapshot totals {total:,} bytes"


@pytest.mark.gamedata
def test_a_real_snapshot_uses_the_leagues_own_sim_date(tmp_path: Path) -> None:
    probe = _probe()
    snap = take_snapshot(probe, snapshot_root=tmp_path)

    header = read_header((probe.path / "teams.dat").read_bytes(), "teams.dat")
    assert snap.sim_date == header.sim_date
    assert snap.path.parent.name == str(header.sim_date)


# ── AC10: the same three properties, once they are rows in MySQL ─────────────


@pytest.fixture(scope="module")
def contracts() -> Contracts:
    return load_contracts()


@pytest.fixture(scope="module")
def warehouse() -> Iterator[Connection[DictCursor]]:
    with warehouse_or_skip(settings_or_skip()) as connection:
        yield connection


@pytest.fixture(scope="module")
def landed(warehouse: Connection[DictCursor]) -> Iterator[tuple[ParsedSnapshot, IngestRun]]:
    with landed_probe(settings_or_skip(), warehouse) as pair:
        yield pair


def _digests(
    connection: Connection[DictCursor], contracts: Contracts, run: IngestRun
) -> dict[str, str]:
    """One checksum per declared table, over exactly this landing's rows."""
    return {
        table.name: table_digest(
            connection,
            table,
            save_id=run.save_id,
            sim_date=as_sql_date(run.sim_date),
            ingest_seq=run.ingest_seq,
        )
        for table in contracts.tables
    }


@pytest.mark.gamedata
def test_the_run_row_records_what_actually_landed(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """Row counts are read **from the warehouse**, not from what the loader printed.

    The acceptance asks what the schema holds. A count that only ever existed on stdout
    proves nothing about that, and the whole reason `ingest_run` carries the counts is so
    the question can be asked months later by a reader who never saw the run.
    """
    parsed, run = landed
    row = read_ingest_run(
        warehouse, save_id=run.save_id, sim_date=run.sim_date, ingest_seq=run.ingest_seq
    )
    assert row is not None, "the run landed but its own provenance row is missing"

    counts = row["table_row_counts"]
    assert counts["bronze_team"] == len(parsed.teams.teams)
    assert counts["bronze_player"] == len(parsed.players.players)
    assert counts["bronze_team_roster"] == len(parsed.rosters.memberships)
    assert counts["bronze_name"] == len(parsed.names.names)
    assert counts["bronze_league_event"] == len(parsed.world.calendar)
    assert counts["ingest_run"] == 1
    # The two whose arithmetic is not a `len()` of a walker tuple, and therefore the two
    # this assertion is worth most on. `bronze_division_team` is the module's only builder
    # that can multiply rows, and `bronze_field_label` is derived from the declaration
    # rather than from any parse.
    assert counts["bronze_division_team"] == sum(
        len(membership.team_ids) for membership in parsed.world.divisions
    )
    assert counts["bronze_field_label"] == sum(
        len(table.columns) for table in load_contracts().tables
    )

    # Per file, and it must stay per file: the accounting tier differs by file, so a
    # summed total would make a strict-tier failure on names.dat arithmetically
    # indistinguishable from players.dat's expected diagnostic residual.
    residual = row["residual_bytes"]
    assert residual["names.dat"] == 0, "names.dat is walked strict; a residual is a defect"
    assert set(residual) == set(parsed.run.residual_bytes)

    assert row["parse_seconds"] is not None and float(row["parse_seconds"]) > 0, (
        "parse_seconds is NULL, which means 'not measured' — and this run measured it"
    )
    assert row["human_team_id"] == parsed.run.human_team_id
    assert {source["name"] for source in row["source_files"]} == {
        source.name for source in parsed.run.sources
    }
    assert all(len(source["sha256"]) == 64 for source in row["source_files"])


@pytest.mark.gamedata
def test_re_landing_a_landed_triple_refuses_and_changes_nothing(
    contracts: Contracts,
    warehouse: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> None:
    """**AC10's first and fourth clauses, and they are the same clause.**

    "Loading the same snapshot twice leaves row counts and checksums unchanged" holds
    *trivially* here, and that is the design rather than a lucky property: nothing is ever
    overwritten, because the second attempt never gets as far as writing. The refusal is
    what makes the byte-identity true, so both are asserted together — a loader that
    silently upserted would satisfy neither.
    """
    parsed, run = landed
    before = _digests(warehouse, contracts, run)

    with pytest.raises(IngestRunExists) as raised:
        land_snapshot(warehouse, parsed, ingest_seq=run.ingest_seq)
    message = str(raised.value)
    assert run.save_id in message and str(run.ingest_seq) in message, (
        "the refusal must name the triple it refused, or the operator cannot tell which "
        f"landing collided: {message}"
    )

    assert _digests(warehouse, contracts, run) == before


@pytest.mark.gamedata
def test_two_sequences_of_one_sim_date_both_persist(
    contracts: Contracts,
    warehouse: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> None:
    """The operator's real case: the club immediately before and immediately after an act.

    The sim date has not moved — the operator signed a free agent without simming — so
    both states share `(save_id, sim_date)` and are separated by `ingest_seq` alone. This
    is why that column is in every key: without it the second look either collides on the
    primary key or overwrites the evidence the first one holds.

    Being able to diff those two states is evidence this project specifically exists to
    collect, so "both persist and neither is mutated by the arrival of the other" is not a
    storage detail — it is the thing being tested.
    """
    parsed, first = landed
    before = _digests(warehouse, contracts, first)
    assert any(digest for digest in before.values()), "nothing landed to be preserved"

    second: IngestRun | None = None
    try:
        second = land_snapshot(warehouse, parsed)
        assert second.ingest_seq > first.ingest_seq, "the second landing reused a sequence"
        assert second.sim_date == first.sim_date, "the in-game date moved; it must not have"

        assert _digests(warehouse, contracts, first) == before, (
            "the first landing changed when the second arrived — the store is not append-only"
        )
        assert (
            read_ingest_run(
                warehouse,
                save_id=second.save_id,
                sim_date=second.sim_date,
                ingest_seq=second.ingest_seq,
            )
            is not None
        )
    finally:
        if second is not None:
            purge_snapshot(warehouse, second)


@pytest.mark.gamedata
def test_two_universes_at_one_sim_date_land_side_by_side(
    contracts: Contracts,
    warehouse: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> None:
    """`save_id` separates universes in the warehouse, not only in a directory name.

    The two test saves sit at the **same sim date** — an unusually clean matched pair — so
    without `save_id` in the key they would be one landing, and a roster report would
    quietly mix the Cubs into Boston.
    """
    settings = settings_or_skip()
    save_or_skip(settings, "truth_save")
    _, probe = landed
    before = _digests(warehouse, contracts, probe)

    with landed_probe(settings, warehouse, which="truth_save") as (_, other):
        assert other.save_id != probe.save_id
        assert _digests(warehouse, contracts, probe) == before, (
            "landing a second universe disturbed the first"
        )
        row = read_ingest_run(
            warehouse, save_id=other.save_id, sim_date=other.sim_date, ingest_seq=other.ingest_seq
        )
        assert row is not None


@pytest.mark.gamedata
def test_a_landing_at_another_sim_date_is_left_untouched(
    contracts: Contracts,
    warehouse: Connection[DictCursor],
    landed: tuple[ParsedSnapshot, IngestRun],
) -> None:
    """**AC10's second clause, closed literally rather than by substitution.**

    The date-valued key column is the one nothing else in this suite varies — both test
    saves sit at 2024-03-18, so every other landing here holds `sim_date` constant. If the
    warehouse already holds a triple at a different date (the managed league is at
    2024-03-07), digesting it before and after this module's landing closes the criterion
    word-for-word, and costs no extra landing at all.

    Skips **loudly and by name** when no such triple exists. A silently-green version would
    report that a second date leaves the first untouched without ever having looked.
    """
    parsed, run = landed
    other = _another_sim_date(warehouse, run)
    if other is None:
        pytest.skip(
            "no landing at a different sim_date is in the warehouse, so AC10's "
            "second clause has nothing to compare — land one and re-run"
        )
    assert other.sim_date != run.sim_date
    before = _digests(warehouse, contracts, other)
    assert any(digest for digest in before.values()), "the other-date landing holds no rows"

    fresh: IngestRun | None = None
    try:
        fresh = land_snapshot(warehouse, parsed)
        assert _digests(warehouse, contracts, other) == before, (
            f"landing {fresh.save_id} at {fresh.sim_date} changed the rows already landed "
            f"at {other.sim_date} — a second snapshot date is not supposed to touch the first"
        )
    finally:
        if fresh is not None:
            purge_snapshot(warehouse, fresh)


def _another_sim_date(connection: Connection[DictCursor], run: IngestRun) -> IngestRun | None:
    """An already-landed run at a different `sim_date`, if the warehouse holds one."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT save_id, sim_date, ingest_seq FROM ingest_run "
            "WHERE sim_date <> %s ORDER BY save_id, sim_date, ingest_seq LIMIT 1",
            (as_sql_date(run.sim_date),),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    landed_date = row["sim_date"]
    return replace(
        run,
        save_id=str(row["save_id"]),
        sim_date=SaveDate(day=landed_date.day, month=landed_date.month, year=landed_date.year),
        ingest_seq=int(row["ingest_seq"]),
    )


@pytest.mark.gamedata
def test_parsing_the_same_snapshot_twice_is_byte_identical(tmp_path: Path) -> None:
    """AC10's parser clause, and it needs no warehouse at all.

    Hashed rather than compared so the failure message stays readable — the serialization
    of a full parse runs to tens of megabytes. `dump_parse` deliberately excludes
    `parse_seconds`, which differs on every run; a digest that included it would fail here
    for a reason that has nothing to do with the parser.
    """
    snapshot = take_snapshot(_probe(), snapshot_root=tmp_path)

    first = hashlib.sha256(dump_parse(snapshot.path).encode("utf-8")).hexdigest()
    second = hashlib.sha256(dump_parse(snapshot.path).encode("utf-8")).hexdigest()
    assert first == second, "two parses of one snapshot disagree"


@pytest.mark.gamedata
def test_structural_absence_survives_landing_as_null(
    warehouse: Connection[DictCursor], landed: tuple[ParsedSnapshot, IngestRun]
) -> None:
    """NULL, never zero — the error `.claude/agents/data-engineer.md` names outright.

    **Anchored on a column that actually lands NULL on these saves.** `bronze_team.city` is
    `None` on the clubs whose record carries no city string, so the comparison below has a
    non-zero population to be wrong about. The obvious anchors do not: `bats` and
    `historical_id` are NULL only when a record's *tail* was not decoded, and that count is
    zero on every save on disk — which now cannot even reach a landing, since
    `ingest.check_decoded` refuses a walk with undecoded tails outright. Asserting
    `0 == 0` there would pass just as happily against a loader that coerced NULL to a
    default, which is the failure this test claims to catch. The offline half
    (`tests/test_bronze_landing.py`) proves those two columns against synthetic records
    where the population is whatever it needs to be.

    The empty-string clause is the other half of the same distinction: a fictional player
    carries `""`, which is present and empty, and must not be collapsed into NULL.
    """
    parsed, run = landed
    expected_absent_cities = sum(1 for team in parsed.teams.teams if team.city is None)

    with warehouse.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS rows_landed, SUM(city IS NULL) AS absent_cities "
            "FROM bronze_team "
            "WHERE save_id = %s AND sim_date = %s AND ingest_seq = %s",
            (run.save_id, as_sql_date(run.sim_date), run.ingest_seq),
        )
        teams = cursor.fetchone()
        cursor.execute(
            "SELECT COUNT(*) AS rows_landed, SUM(historical_id = '') AS fictional "
            "FROM bronze_player "
            "WHERE save_id = %s AND sim_date = %s AND ingest_seq = %s",
            (run.save_id, as_sql_date(run.sim_date), run.ingest_seq),
        )
        players = cursor.fetchone()
    assert teams is not None and players is not None
    # An aggregate always returns a row, so emptiness has to be asserted separately or
    # every comparison below is a comparison of two zeroes.
    assert int(teams["rows_landed"]) > 0 and int(players["rows_landed"]) > 0

    assert expected_absent_cities > 0, (
        "no parsed club has an absent city, so this test has nothing to prove. Re-anchor "
        "it on a column that does, rather than leaving it green and vacuous"
    )
    assert int(teams["absent_cities"]) == expected_absent_cities, (
        "the count of NULL cities in the warehouse does not match the count of None cities "
        "in the parse — absence was coerced into a value on the way in"
    )
    assert int(players["fictional"]) > 0, (
        "no player landed an empty historical_id. A fictional player carries '' and an "
        "undecoded tail carries NULL — if the empty strings have vanished, the two facts "
        "have been collapsed into one"
    )
