"""The operator's ingest path: the shared read, and the command over it.

Split by what each half needs. The offline half runs in CI and covers the pre-flight's
comparison logic, the command's surface and its refusals — everything provable without a
game, a save or a warehouse. The `gamedata` half targets the **probe only** (SD-20), and
is the only place a real landing happens.

**A fully-skipped `-m gamedata` run exits 0.** Every gate here is run with `-rs` and the
passed count is read, because a green run that collected nothing proves nothing — which is
the failure mode `tests/fixtures/warehouse.py`'s loud-skip discipline exists to make
visible rather than silent.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

import pymysql
import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

import fixtures.warehouse as fixtures_warehouse
import test_no_leaks
import test_read_only
from fixtures.warehouse import purge_snapshot, save_or_skip, settings_or_skip, warehouse_or_skip
from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.contracts.loader import load_contracts
from ootp_ai.ingest import IngestRun, ParsedSnapshot, SourceFile, read
from ootp_ai.ingest import __main__ as command
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.snapshot import (
    SIM_DATE_SOURCE,
    SNAPSHOT_FILES,
    Snapshot,
    SnapshotFile,
    source_facts,
    take_snapshot,
)
from ootp_ai.warehouse.ingest_run import (
    IngestRunExists,
    as_sql_date,
    landed_max_seq,
    latest_landing,
    read_ingest_run,
)
from ootp_ai.warehouse.load import ConcurrentLandingError, table_digest
from ootp_ai.warehouse.sql import quote_ident


def _as_date(text: str) -> SaveDate:
    """`YYYY-MM-DD` off the command's own stdout, back as the save's date type."""
    year, month, day = (int(part) for part in text.split("-"))
    return SaveDate(day=day, month=month, year=year)


# ── the allowlist this change deliberately does not widen ────────────────────


def test_the_write_allowlist_did_not_widen() -> None:
    """AC1. The new modules create nothing, so neither earns a `WRITERS` entry.

    `ingest/read.py` and `ingest/__main__.py` delegate every write to `snapshot.py`,
    which is why this set is byte-unchanged rather than gaining two names. That is a
    stronger outcome than allowlisting them would have been: an entry here is a standing
    permission, and the two modules that most want one are the two a future refactor is
    most likely to grow a write in.
    """
    assert test_read_only.WRITERS == {
        "snapshot.py",
        "reports/__main__.py",
        "catalog/__main__.py",
    }


def test_the_sim_date_source_is_one_of_the_digested_files() -> None:
    """The soundness guard under keying the pre-flight on `save_id` alone.

    The pre-flight asks the warehouse for a save's most recent landing, not for a
    landing at a particular date — a date-keyed lookup would need the sim date, which is
    itself a game read, and would push that read outside the bracket ADR 0001's proof
    covers. The equivalence that makes the cheaper shape sound is: the sim date comes
    from `teams.dat`'s header, `teams.dat` is one of the digested files, so unchanged
    bytes imply an unchanged sim date.

    That derivation is invisible in the code it justifies, so it is asserted here. If
    `SIM_DATE_SOURCE` ever leaves `SNAPSHOT_FILES`, the pre-flight can report *unchanged*
    for a save whose date has moved, and this is the only thing that would say so.
    """
    assert SIM_DATE_SOURCE in SNAPSHOT_FILES


def test_the_documented_invocation_names_a_command_that_exists() -> None:
    """AC8. The anti-drift device for a literal that must live in three places.

    `README.md` and `reports/resolve.py`'s "nothing landed" advice are prose an import
    cannot reach, so the string is duplicated by necessity. What is *not* left to chance
    is whether the copies agree: both are read from disk here and checked against the
    command module's own constant.

    The `resolve.py` line advised running an ingest for two phases while no ingest
    command existed. This is what would have caught it.
    """
    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "README.md").read_text(encoding="utf-8")
    resolve = (repo / "src" / "ootp_ai" / "reports" / "resolve.py").read_text(encoding="utf-8")

    assert command.INVOCATION in readme
    assert "There is no ingest command" not in readme, "the retired gap notice is back"
    assert command.INVOCATION in resolve, "resolve.py advises a command that does not exist"


# ── the pre-flight comparison, offline ───────────────────────────────────────

_SIZES: Mapping[str, int] = {
    "teams.dat": 512,
    "players.dat": 4096,
    "names.dat": 256,
    "world.dat": 1024,
    "human_managers.dat": 64,
}

_LANDED_DATE = SaveDate(year=2024, month=3, day=7)


def _payload(name: str, size: int) -> bytes:
    """Distinct bytes per file, so a digest comparison is not comparing all-zeros."""
    return (name.encode("ascii") * size)[:size]


def _save(tmp_path: Path, sizes: Mapping[str, int] = _SIZES) -> SaveRef:
    """A save-shaped directory holding the five in-scope files at chosen sizes.

    Not a real save: its headers are meaningless, so every test using it stubs
    `read_sim_date`. What it provides is a real filesystem the size survey and the
    digest can run against, which is the half of the pre-flight worth proving.
    """
    root = tmp_path / "saves"
    directory = root / "Fake-League.lg"
    directory.mkdir(parents=True)
    for name, size in sizes.items():
        (directory / name).write_bytes(_payload(name, size))
    return SaveRef(league="Fake-League", root=root)


def _prior(
    sizes: Mapping[str, int] = _SIZES,
    *,
    sim_date: SaveDate = _LANDED_DATE,
    ingest_seq: int = 3,
    digest_of: Mapping[str, bytes] | None = None,
) -> read.PriorLanding:
    """A `PriorLanding` describing exactly what `_save` writes, unless told otherwise."""
    contents = {name: _payload(name, size) for name, size in sizes.items()}
    if digest_of is not None:
        contents.update(digest_of)
    return read.PriorLanding(
        sim_date=sim_date,
        ingest_seq=ingest_seq,
        files=tuple(
            SnapshotFile(name=name, size=size, sha256=hashlib.sha256(contents[name]).hexdigest())
            for name, size in sizes.items()
        ),
    )


@dataclass
class _DigestSpy:
    """Wraps `source_facts` and counts calls, so "no digest was performed" is testable.

    Delegating rather than faking: the assertion worth making is that the expensive call
    did not happen, and a spy that returned canned data could not tell a skipped digest
    from a wrong one.
    """

    inner: Callable[[SaveRef], tuple[SnapshotFile, ...]]
    calls: int = 0

    def __call__(self, save: SaveRef) -> tuple[SnapshotFile, ...]:
        self.calls += 1
        return self.inner(save)


@dataclass
class _StubbedRead:
    """What a stubbed `read_save` recorded: the digest spy and the snapshots taken."""

    digests: _DigestSpy
    snapshots: list[SaveRef]


def _stub_the_copy(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sim_date: SaveDate = _LANDED_DATE,
) -> _StubbedRead:
    """Let `read_save` run offline: stub the header read, the copy and the parse.

    Everything the pre-flight itself does — the size survey, the digest, the comparison,
    the refusal — runs for real against `_save`'s files. Only the three steps that need a
    genuine OOTP save are replaced, and each records that it was reached.
    """
    taken: list[SaveRef] = []
    spy = _DigestSpy(inner=source_facts)

    def _snapshot(save: SaveRef, *, snapshot_root: Path, ingest_seq: int | None = None) -> Snapshot:
        taken.append(save)
        return Snapshot(
            save_id=save.save_id,
            sim_date=sim_date,
            ingest_seq=1 if ingest_seq is None else ingest_seq,
            path=snapshot_root,
            files=(),
        )

    monkeypatch.setattr(read, "read_sim_date", lambda save: sim_date)
    monkeypatch.setattr(read, "source_facts", spy)
    monkeypatch.setattr(read, "take_snapshot", _snapshot)
    monkeypatch.setattr(read, "parse_snapshot", lambda snapshot: cast(ParsedSnapshot, snapshot))
    return _StubbedRead(digests=spy, snapshots=taken)


def test_a_moved_sim_date_is_a_reason_before_any_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cheapest signal there is, and it must settle the question on its own."""
    stub = _stub_the_copy(monkeypatch, sim_date=SaveDate(year=2024, month=3, day=18))

    reading = read.read_save(_save(tmp_path), snapshot_root=tmp_path / "snap", previous=_prior())

    assert reading.verdict == "changed"
    assert stub.digests.calls == 0, "a moved sim date was digested when it did not need to be"
    assert len(stub.snapshots) == 1


def test_a_changed_size_is_a_reason_without_digesting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One file bigger than it landed is proof of change; digesting adds nothing."""
    stub = _stub_the_copy(monkeypatch)
    grown = dict(_SIZES)
    grown["players.dat"] = _SIZES["players.dat"] + 8

    reading = read.read_save(
        _save(tmp_path, grown), snapshot_root=tmp_path / "snap", previous=_prior()
    )

    assert reading.verdict == "changed"
    assert stub.digests.calls == 0, "a changed size was digested when it did not need to be"


def test_a_file_added_to_scope_since_the_landing_is_a_reason() -> None:
    """Risk 2, and a real state on disk rather than a hypothetical.

    `SNAPSHOT_FILES` was widened on 2026-08-16, so a landing older than that names three
    files. A comparison that only checked the files `previous` happens to name would
    report *unchanged* for a save whose `world.dat` was never digested at all.
    """
    narrow = {name: _SIZES[name] for name in ("teams.dat", "players.dat", "names.dat")}

    reason = read.reason_from_sizes(_prior(narrow), _LANDED_DATE, _SIZES)

    assert reason is not None
    assert "world.dat" in reason


def test_equal_sizes_escalate_rather_than_reporting_unchanged() -> None:
    """`None` here means *keep looking*, and getting this backwards is the worst bug.

    If this returned a verdict instead of escalating, the digest branch would be
    unreachable and the pre-flight could never refuse — the plan's own worst risk,
    arriving silently and passing every other test in this file.
    """
    assert read.reason_from_sizes(_prior(), _LANDED_DATE, _SIZES) is None


def test_a_same_size_edit_is_caught_by_the_digest() -> None:
    """The case sizes cannot see, and the only reason the digest is paid for at all."""
    edited = {"players.dat": _payload("players.dat", _SIZES["players.dat"] - 1) + b"!"}
    current = tuple(
        SnapshotFile(
            name=name,
            size=size,
            sha256=hashlib.sha256(_payload(name, size)).hexdigest(),
        )
        for name, size in _SIZES.items()
    )

    reason = read.reason_from_digests(_prior(digest_of=edited), current)

    assert reason is not None
    assert "players.dat" in reason


def test_an_identical_save_raises_rather_than_landing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal, and the proof it fires before anything is copied.

    `snapshots` staying empty is what makes "refused before 52.4 MiB was copied" an
    observation rather than a claim.
    """
    stub = _stub_the_copy(monkeypatch)

    with pytest.raises(read.SaveUnchanged) as caught:
        read.read_save(_save(tmp_path), snapshot_root=tmp_path / "snap", previous=_prior())

    assert stub.digests.calls == 1, "the digest is the only thing that can prove unchanged"
    assert stub.snapshots == [], "the refusal did not fire before the copy"
    assert caught.value.ingest_seq == 3
    assert caught.value.sim_date == _LANDED_DATE
    assert "--new-look" in str(caught.value)


def test_no_prior_landing_skips_the_comparison_entirely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What both test call sites pass, and what a first landing on a fresh clone hits."""
    stub = _stub_the_copy(monkeypatch)

    reading = read.read_save(_save(tmp_path), snapshot_root=tmp_path / "snap", previous=None)

    assert reading.verdict == "no-prior"
    assert stub.digests.calls == 0
    assert len(stub.snapshots) == 1
    assert reading.mode == "standard"


# ── the two read-only warehouse helpers, against a fake cursor ───────────────


@dataclass
class _FakeCursor:
    """Records what it was asked and answers with whatever the connection was given."""

    owner: _FakeConnection

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_excinfo: object) -> None:
        return None

    def execute(self, statement: str, args: object = None) -> None:
        self.owner.statements.append(statement)
        self.owner.args.append(args)

    def fetchone(self) -> Mapping[str, Any] | None:
        return self.owner.row


@dataclass
class _FakeConnection:
    """The `cast`-at-the-boundary shim `tests/test_bronze_landing.py` established.

    The helpers under test take a real `Connection`, so the fake is cast at the call
    site rather than made to satisfy the protocol — which keeps the fake honest about
    being a fake instead of growing toward a driver.
    """

    row: Mapping[str, Any] | None = None
    statements: list[str] = field(default_factory=list)
    args: list[object] = field(default_factory=list)

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def _as_connection(fake: _FakeConnection) -> Connection[DictCursor]:
    return cast("Connection[DictCursor]", fake)


def test_landed_max_seq_reports_zero_when_the_date_never_landed() -> None:
    """Zero, not one. The caller adds one; a helper that pre-added would double-count."""
    fake = _FakeConnection(row={"used": 0})

    assert landed_max_seq(_as_connection(fake), save_id="X", sim_date=_LANDED_DATE) == 0


def test_landed_max_seq_returns_the_highest_landed_sequence() -> None:
    fake = _FakeConnection(row={"used": 4})

    assert landed_max_seq(_as_connection(fake), save_id="X", sim_date=_LANDED_DATE) == 4


def test_landed_max_seq_takes_no_row_lock() -> None:
    """The absence *is* the contract, which is what makes a string assertion right here.

    `next_ingest_seq` sits two functions away and does take `FOR UPDATE`, because it
    allocates inside the inserting transaction. This one is asked before any transaction
    is open, where the same lock would protect nothing and imply that it did.
    """
    fake = _FakeConnection(row={"used": 1})

    landed_max_seq(_as_connection(fake), save_id="X", sim_date=_LANDED_DATE)

    assert fake.statements, "the helper issued no statement at all"
    assert "FOR UPDATE" not in fake.statements[0].upper()


def test_latest_landing_is_none_for_a_save_that_never_landed() -> None:
    assert latest_landing(_as_connection(_FakeConnection(row=None)), save_id="X") is None


def test_latest_landing_decodes_its_json_columns() -> None:
    """PyMySQL hands a JSON column back as text, and a pre-flight cannot iterate text."""
    files = [{"name": "teams.dat", "size": 512, "sha256": "abc", "version": 25}]
    fake = _FakeConnection(
        row={
            "save_id": "X",
            "ingest_seq": 2,
            "source_files": json.dumps(files),
            "table_row_counts": json.dumps({"bronze_player": 226}),
            "residual_bytes": json.dumps({"teams.dat": 0}),
        }
    )

    landing = latest_landing(_as_connection(fake), save_id="X")

    assert landing is not None
    assert landing["source_files"] == files
    assert landing["table_row_counts"] == {"bronze_player": 226}


def test_latest_landing_orders_by_the_leagues_date_not_the_wall_clock() -> None:
    """A correction re-lands an older date after a newer one; league order is the answer."""
    fake = _FakeConnection(row={"save_id": "X", "ingest_seq": 1})

    latest_landing(_as_connection(fake), save_id="X")

    statement = fake.statements[0].upper()
    assert "ORDER BY" in statement
    assert "INGESTED_AT" not in statement


# ── the command surface ──────────────────────────────────────────────────────


def test_the_land_subcommand_and_its_four_flags_parse() -> None:
    """AC2. The surface `incremental-loading` writes its procedure against."""
    parsed = command._parser().parse_args(["land"])
    assert parsed.command == "land"
    assert parsed.save_id is None
    assert parsed.json is False
    assert parsed.new_look is False
    assert parsed.from_snapshot is None

    full = command._parser().parse_args(
        ["land", "--save-id", "X", "--json", "--from-snapshot", "d"]
    )
    assert (full.save_id, full.json, full.from_snapshot) == ("X", True, "d")
    assert command._parser().parse_args(["land", "--new-look"]).new_look is True


@pytest.mark.parametrize("flag", ["--sim-date", "--snapshot-root", "--ingest-seq", "--force"])
def test_the_options_this_command_deliberately_lacks_are_rejected(flag: str) -> None:
    """AC2. Each absence is a decision, so each is pinned rather than left to drift.

    `--sim-date` because the in-game date is read from `teams.dat`'s header and never
    supplied; `--snapshot-root` because `.env` owns every write root; `--ingest-seq`
    and `--force` because bronze is append-only and neither a chosen sequence nor an
    overwrite is the operator's to ask for (ADR 0021).
    """
    with pytest.raises(SystemExit):
        command._parser().parse_args(["land", flag, "x"])


def test_the_subcommand_is_required_and_argparse_raises() -> None:
    """AC2. `main([])` **raises** `SystemExit(2)` — it does not return 2."""
    with pytest.raises(SystemExit) as exc:
        command.main([])
    assert exc.value.code == 2


def test_a_new_look_at_a_snapshot_re_land_is_refused_by_argparse() -> None:
    """AC2. A snapshot re-land has no pre-flight, so there is nothing to override."""
    with pytest.raises(SystemExit) as exc:
        command.main(["land", "--from-snapshot", "d", "--new-look"])
    assert exc.value.code == 2


# ── target resolution ────────────────────────────────────────────────────────


def _settings(tmp_path: Path, **overrides: str) -> Settings:
    """Offline `Settings`, built through the injection point `config.py:111` exists for.

    Mirrors `tests/test_config.py`'s `_env`, which mkdirs the two directories
    `_required_directory` insists exist — without them `load_settings` raises
    `ConfigError` and none of these tests can be written at all.
    """
    install = tmp_path / "install"
    saves = tmp_path / "saves"
    install.mkdir(exist_ok=True)
    saves.mkdir(exist_ok=True)
    values = {
        "OOTP_INSTALL": str(install),
        "OOTP_SAVED_GAMES": str(saves),
        "OOTP_LEAGUE": "OOTP-AI",
        "MYSQL_USER": "u",
        "MYSQL_PASSWORD": "p",
        "MYSQL_DATABASE": "ootp_dev",
        "OOTP_SNAPSHOT_ROOT": str(tmp_path / "snapshots"),
        "OOTP_OUTPUT_ROOT": str(tmp_path / "reports"),
    }
    values.update(overrides)
    return load_settings(values)


def test_an_absent_save_id_resolves_to_the_managed_league(tmp_path: Path) -> None:
    """AC3. The club this front office runs is the default target."""
    settings = _settings(tmp_path)
    assert command._resolve_save(settings, None) is settings.managed


def test_a_fresh_clone_with_no_validation_saves_still_resolves(tmp_path: Path) -> None:
    """AC3. `truth_save` and `probe_save` are both `None` on a machine that has neither."""
    settings = _settings(tmp_path)
    assert settings.truth_save is None
    assert settings.probe_save is None
    assert command._resolve_save(settings, "OOTP-AI").league == "OOTP-AI"


def test_an_unconfigured_save_id_is_refused_by_name(tmp_path: Path) -> None:
    """AC3. The message names every configured id, which usually identifies the typo."""
    settings = _settings(tmp_path, OOTP_PROBE_LEAGUE="Test-Save-Challenge-Mode")

    with pytest.raises(command.UnknownSave) as caught:
        command._resolve_save(settings, "Nope")

    assert "OOTP-AI" in str(caught.value)
    assert "Test-Save-Challenge-Mode" in str(caught.value)


def test_a_filesystem_path_passed_as_a_save_id_is_rejected(tmp_path: Path) -> None:
    """AC3. Resolve by name, never by path — the command is not a way to aim the pipeline."""
    settings = _settings(tmp_path)

    with pytest.raises(command.UnknownSave):
        command._resolve_save(settings, str(tmp_path / "saves" / "OOTP-AI.lg"))


def test_an_unconfigured_save_id_exits_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC3. Exit 2, not 1: an argv problem, not a refused operation."""
    monkeypatch.setattr(command, "load_settings", lambda: _settings(tmp_path))

    assert command.main(["land", "--save-id", "Nope"]) == 2


def test_a_configuration_failure_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC5. `.env` is unreadable or incomplete, so nothing was attempted."""

    def _raise() -> Settings:
        raise ConfigError("OOTP_LEAGUE is required and is unset or empty")

    monkeypatch.setattr(command, "load_settings", _raise)

    assert command.main(["land"]) == 2


# ── the two output formats ───────────────────────────────────────────────────


def _result(
    *,
    ingest_seq: int = 2,
    snapshot_dir_seq: int = 2,
    warehouse_max_seq: int = 1,
    tables_created: tuple[str, ...] = (),
    reason: str | None = "players.dat is 32,078,633 bytes against 32,070,091 landed",
) -> command.LandingResult:
    """A synthetic `LandingResult` carrying a path, so the leak guard has something to find.

    `Snapshot.path` is a real absolute path exactly as a live run would produce — which is
    the point: a formatter that leaked one would leak this one.

    Built from `Path.cwd()` rather than written out, because a literal absolute path in
    a tracked file is the thing `tests/test_no_leaks.py` fails the build over — and this
    repo is public. The guard caught the first draft of this helper, which is a fair
    demonstration that it works.
    """
    snapshot = Snapshot(
        save_id="Test-Save-Challenge-Mode",
        sim_date=_LANDED_DATE,
        ingest_seq=snapshot_dir_seq,
        path=Path.cwd().resolve() / "var" / "snapshots" / "Test" / "2024-03-07" / "2",
        files=(SnapshotFile(name="teams.dat", size=512, sha256="a" * 64),),
    )
    run = IngestRun(
        save_id=snapshot.save_id,
        sim_date=snapshot.sim_date,
        ingest_seq=ingest_seq,
        human_team_id=6,
        snapshot=snapshot,
        sources=(SourceFile(name="teams.dat", size=512, sha256="a" * 64, version=25),),
        row_counts={"bronze_player": 226, "bronze_name": 264095},
        residual_bytes={"teams.dat": 1137},
        parse_seconds=2.214,
    )
    return command.LandingResult(
        run=run,
        verdict="changed",
        mode="challenge",
        snapshot_dir_seq=snapshot_dir_seq,
        warehouse_max_seq=warehouse_max_seq,
        tables_created=tables_created,
        reason=reason,
    )


def test_the_human_block_pins_the_triple_on_line_one() -> None:
    """AC4. `incremental-loading` parses this line; taste may not move it."""
    line = command.format_result(_result()).splitlines()[0]

    assert line == "landed Test-Save-Challenge-Mode 2024-03-07 ingest_seq 2"


def test_the_human_block_carries_the_row_counts_and_the_mode() -> None:
    """AC4. Per-table counts are the honest measurable for a cost nobody has bounded."""
    block = command.format_result(_result())

    assert "bronze_player 226" in block
    assert "bronze_name 264,095" in block
    assert "challenge" in block


@pytest.mark.parametrize("render", [command.format_result, command.format_json])
def test_neither_output_format_emits_an_absolute_path(
    render: Callable[[command.LandingResult], str],
) -> None:
    """AC4. Against `test_no_leaks.PATTERNS` imported, never restated.

    An ingest run is the record most likely to be pasted into a tracked file, and
    `saved_games.dat` embeds a user-profile path per save (ADR 0006). The synthetic
    result carries a real absolute snapshot path, so this fails if either format ever
    starts printing one.
    """
    rendered = render(_result())

    for label, pattern in test_no_leaks.PATTERNS:
        assert not pattern.search(rendered), f"{label} reached the output: {rendered}"


def test_the_json_payload_is_exactly_the_documented_key_set() -> None:
    """AC4. A stable contract for `incremental-loading`, not a print format to grep."""
    payload = json.loads(command.format_json(_result(ingest_seq=2, snapshot_dir_seq=2)))

    assert set(payload) == set(command.JSON_KEYS)
    assert payload["sim_date"] == "2024-03-07"
    assert payload["ingest_seq"] == 2
    assert payload["row_counts"]["bronze_player"] == 226


def test_a_landing_says_why_it_happened_in_both_formats() -> None:
    """Scope Core: changed bytes land the next sequence **and say why**.

    The comparison has already computed the answer — "players.dat is N bytes against M
    landed" — and an operator reading only `verdict: changed` has no way to learn what
    moved. `reason` is `null` rather than absent where no comparison was made, so a
    consumer branching on `verdict` always finds the key.
    """
    moved = _result()
    assert "players.dat is 32,078,633 bytes" in command.format_result(moved)
    assert json.loads(command.format_json(moved))["reason"] == moved.reason

    first_landing = _result(reason=None)
    assert "no prior landing was compared against" in command.format_result(first_landing)
    payload = json.loads(command.format_json(first_landing))
    assert "reason" in payload
    assert payload["reason"] is None


def test_the_two_sequences_reach_the_json_only_when_they_diverge() -> None:
    """Decision 4. Printed prose the operator may not keep is not a record."""
    agreed = json.loads(command.format_json(_result(ingest_seq=2, snapshot_dir_seq=2)))
    assert not set(command.SEQUENCE_KEYS) & set(agreed)

    diverged = json.loads(
        command.format_json(_result(ingest_seq=5, snapshot_dir_seq=2, warehouse_max_seq=4))
    )
    assert diverged["snapshot_dir_seq"] == 2
    assert diverged["warehouse_max_seq"] == 4


def test_the_sequence_line_is_printed_on_every_run_agreeing_or_not() -> None:
    """Silence must never read as agreement.

    Three states, and all three have to say something. Printing only on divergence
    leaves a reader unable to tell "the two allocators agreed" from "nobody looked",
    which is exactly the ambiguity AC15's third clause exists to close.
    """
    agreed = command.format_result(_result(ingest_seq=2, snapshot_dir_seq=2, warehouse_max_seq=1))
    assert "sequence:" in agreed
    assert "agree" in agreed

    warehouse_ahead = command.format_result(
        _result(ingest_seq=5, snapshot_dir_seq=2, warehouse_max_seq=4)
    )
    assert "landed 5" in warehouse_ahead
    assert "NOT filed under" in warehouse_ahead

    # The direction the old predicate missed entirely: the landed sequence equals the
    # directory's number, so `ingest_seq != snapshot_dir_seq` is False — yet the
    # warehouse just acquired a gapped sequence, which is a live state on this machine.
    filesystem_ahead = command.format_result(
        _result(ingest_seq=4, snapshot_dir_seq=4, warehouse_max_seq=0)
    )
    assert "gapped" in filesystem_ahead, filesystem_ahead


def test_a_forced_landing_does_not_report_no_prior() -> None:
    """`--new-look` means "do not look", which is not the same as "nothing was there".

    `read_save` derives its verdict from `previous is None` and cannot tell the two
    apart; only `land()` knows the intent. Collapsing them made `--new-look` against a
    save with five landings report `no-prior`, which is a false statement about the
    warehouse in the field a downstream driver branches on.
    """
    assert set(command.LandingVerdict.__args__) == {  # type: ignore[attr-defined]
        "no-prior",
        "changed",
        "new-look",
        "from-snapshot",
    }


# ── refusals ─────────────────────────────────────────────────────────────────


def _refusal(name: str) -> Exception:
    """One instance of each refusal, constructed the way its own module constructs it."""
    if name == "SaveUnchanged":
        return read.SaveUnchanged("X", _LANDED_DATE, 1)
    kinds: Mapping[str, Any] = {kind.__name__: kind for kind in command.REFUSALS}
    raised = kinds[name](f"{name} happened")
    assert isinstance(raised, Exception)
    return raised


@pytest.mark.parametrize("name", [kind.__name__ for kind in command.REFUSALS])
def test_every_refusal_exits_one_and_is_named_rather_than_traced(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC5. Parametrised over the tuple itself, so a tenth added without handling reds.

    The nine share no base class — five derive from `Exception`, two from `RuntimeError`
    — which is exactly why the tuple is explicit rather than a hierarchy catch.
    """
    monkeypatch.setattr(command, "load_settings", lambda: _settings(tmp_path))

    def _raise(*_args: object, **_kwargs: object) -> command.LandingResult:
        raise _refusal(name)

    monkeypatch.setattr(command, "land", _raise)

    assert command.main(["land"]) == 1
    assert name in capsys.readouterr().err


def test_an_already_landed_triple_and_a_lost_lock_race_read_differently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC5. `load.py:146-154` warns in terms that conflating these misleads the operator.

    One means *this snapshot is already in the warehouse* and is an answer; the other
    means *somebody else is writing right now* and is a retry that ran out.
    """
    monkeypatch.setattr(command, "load_settings", lambda: _settings(tmp_path))
    messages = []
    for kind in (IngestRunExists, ConcurrentLandingError):

        def _raise(*_args: object, _kind: type[Exception] = kind, **_kwargs: object) -> None:
            raise _kind("landed at ingest_seq 1")

        monkeypatch.setattr(command, "land", _raise)
        assert command.main(["land"]) == 1
        messages.append(capsys.readouterr().err)

    assert messages[0] != messages[1]
    assert "IngestRunExists" in messages[0]
    assert "ConcurrentLandingError" in messages[1]


def test_the_unchanged_refusal_emits_a_json_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Decision 6. The one verdict a successful landing can never carry.

    Emitting `verdict` only on the success path would promise a discriminator the
    control flow forbids: the unchanged case raises, so no `LandingResult` is built.
    """
    monkeypatch.setattr(command, "load_settings", lambda: _settings(tmp_path))

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise read.SaveUnchanged("Test-Save", _LANDED_DATE, 4)

    monkeypatch.setattr(command, "land", _raise)

    assert command.main(["land", "--json"]) == 1
    captured = capsys.readouterr()
    envelope = json.loads(captured.out)
    assert envelope == {
        "verdict": "unchanged",
        "save_id": "Test-Save",
        "sim_date": "2024-03-07",
        "ingest_seq": 4,
    }
    assert "SaveUnchanged" in captured.err


# ── the shared seam, proved behaviourally ────────────────────────────────────


@dataclass
class _FakeParsed:
    """Stands in for a `ParsedSnapshot` where only the run it carries is reached.

    A real one needs five walker outputs over a real save. `land()` only ever reads
    `parsed.run`, so this is the whole surface — and keeping it this thin is what makes
    a `land()` that started reaching further fail here rather than pass quietly.
    """

    run: IngestRun


@dataclass
class _LandHarness:
    """Everything `land()` reaches out to, stubbed, with one shared call-order log."""

    order: list[str] = field(default_factory=list)
    read_save_calls: list[SaveRef] = field(default_factory=list)
    landed_seq: list[int | None] = field(default_factory=list)


def _stub_land(
    monkeypatch: pytest.MonkeyPatch, *, prior: Mapping[str, Any] | None = None
) -> _LandHarness:
    """Drive `land()` with no game, no snapshot and no MySQL.

    The one call left un-stubbed is `read.read_save`, which is wrapped rather than
    replaced further down — a recorder that delegates is what makes "both callers route
    through the shared function" an observation rather than a source-text scan.
    """
    harness = _LandHarness()
    run = _result().run

    def _note(label: str) -> Callable[..., Any]:
        def _recorded(*_args: object, **_kwargs: object) -> Any:
            harness.order.append(label)
            return {
                "connect": object(),
                "ensure_tables": ("bronze_player",),
                "verify": None,
                "latest": prior,
                "max_seq": 1,
                "landed_dates": [],
            }[label]

        return _recorded

    monkeypatch.setattr(command, "connect_warehouse", lambda settings: _FakeWarehouse(harness))
    monkeypatch.setattr(command, "ensure_tables", _note("ensure_tables"))
    monkeypatch.setattr(command, "verify_snapshot", _note("verify"))
    monkeypatch.setattr(command, "latest_landing", _note("latest"))
    monkeypatch.setattr(command, "landed_max_seq", _note("max_seq"))
    monkeypatch.setattr(command, "landed_sim_dates", _note("landed_dates"))

    def _land_snapshot(
        _connection: object, _parsed: object, *, ingest_seq: int | None = None
    ) -> Any:
        harness.order.append("land_snapshot")
        harness.landed_seq.append(ingest_seq)
        return run

    monkeypatch.setattr(command, "land_snapshot", _land_snapshot)

    def _read_save(save: SaveRef, *, snapshot_root: Path, previous: object = None) -> Any:
        harness.order.append("read_save")
        harness.read_save_calls.append(save)
        return read.SaveReading(
            parsed=cast(ParsedSnapshot, _FakeParsed(run=_result().run)),
            verdict="changed",
            snapshot_dir_seq=2,
            mode="challenge",
        )

    # ONE patch, on the source module's attribute. Both call sites import the *module*
    # and call `read.read_save(...)`, so this single patch is observed by every caller —
    # patching `command.read_save` would raise `AttributeError`, or with `raising=False`
    # would silently set an attribute nothing reads and record zero calls.
    monkeypatch.setattr(read, "read_save", _read_save)
    return harness


class _FakeWarehouse:
    """A connection recording the two lifecycle calls `land()` makes on it.

    `commit` is here because `land()` ends its read view before deciding the sequence —
    without that, the sequence is chosen from a view of `ingest_run` fixed before the
    52.4 MiB copy, and a landing that committed meanwhile is invisible to the arithmetic
    meant to step over it.
    """

    def __init__(self, harness: _LandHarness) -> None:
        self.harness = harness

    def commit(self) -> None:
        self.harness.order.append("commit")

    def close(self) -> None:
        self.harness.order.append("close")


def test_the_command_reaches_the_shared_function_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC6, command half. Behavioural, not a source-text scan.

    `tree-seam-for-remaining-guards` exists because a string-pinned scan cannot fail in
    the direction that matters. A recorder that wraps and delegates can.
    """
    harness = _stub_land(monkeypatch)
    settings = _settings(tmp_path)

    command.land(settings, save_id=None)

    assert len(harness.read_save_calls) == 1
    assert harness.read_save_calls[0] is settings.managed


def test_the_command_module_holds_the_module_not_the_function() -> None:
    """AC6. Asserted on the *modules*, so a `from … import read_save` refactor reds this.

    If the command ever bound the function directly, the single patch above would set an
    attribute nothing reads and the recorder would count zero calls — a test passing for
    exactly the wrong reason.
    """
    # Through `vars` because `__main__` re-exports nothing: what is asserted is that the
    # name `read` bound inside the command module IS the module, not a function lifted
    # out of it.
    assert vars(command)["read"] is read


def test_the_tables_are_ensured_once_and_before_the_save_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC7. One shared ordering log, not two counters.

    A fresh clone with an empty schema must fail on the connection, not after a 52.4 MiB
    copy — so the ordering is the assertion, and two independent counters could not make
    it.
    """
    harness = _stub_land(monkeypatch)

    command.land(_settings(tmp_path), save_id=None)

    assert harness.order.count("ensure_tables") == 1
    assert harness.order.index("ensure_tables") < harness.order.index("read_save")
    assert harness.order.index("read_save") < harness.order.index("land_snapshot")
    assert harness.order[-1] == "close", "the connection outlived the landing"
    # The sequence is decided from a view opened AFTER the copy, not before it.
    assert harness.order.index("commit") < harness.order.index("max_seq"), (
        "landed_max_seq was read from the view _prior_landing opened before the copy"
    )
    assert harness.order.index("read_save") < harness.order.index("commit")


def test_the_sequence_is_reconciled_across_both_allocators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decision 4, asserted in both directions against a stubbed warehouse.

    `max(filesystem, warehouse + 1)` never collides and never refuses. The stub reports a
    filesystem sequence of 2 and a warehouse maximum of 1, so the two agree at 2; raise
    the warehouse past the directory and the warehouse wins.
    """
    harness = _stub_land(monkeypatch)
    command.land(_settings(tmp_path), save_id=None)
    assert harness.landed_seq == [2], "the filesystem sequence should win when it is ahead"

    harness = _stub_land(monkeypatch)
    monkeypatch.setattr(command, "landed_max_seq", lambda *a, **k: 7)
    command.land(_settings(tmp_path), save_id=None)
    assert harness.landed_seq == [8], "the warehouse should win when it is ahead"


def test_new_look_skips_the_pre_flight_entirely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--new-look` lands identical bytes deliberately, so it must not consult the prior."""
    harness = _stub_land(monkeypatch)
    seen: list[object] = []

    def _read_save(save: SaveRef, *, snapshot_root: Path, previous: object = None) -> Any:
        seen.append(previous)
        harness.order.append("read_save")
        return read.SaveReading(
            parsed=cast(ParsedSnapshot, _FakeParsed(run=_result().run)),
            verdict="changed",
            snapshot_dir_seq=2,
            mode="challenge",
        )

    monkeypatch.setattr(read, "read_save", _read_save)

    command.land(_settings(tmp_path), save_id=None, new_look=True)

    assert seen == [None]
    assert "latest" not in harness.order, "--new-look asked the warehouse for a prior landing"


def test_the_landing_fixture_reaches_the_same_shared_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC6, fixture half. The **same single patch**, driving `landed_probe` this time.

    This is the half that makes the criterion mean anything. The command routing through
    `read_save` proves only that the command is self-consistent; what AC6 asks is that
    the *fixture* — which every gamedata landing in the repo goes through — is the same
    code path, so the two cannot drift. `tests/fixtures/warehouse.py` used to compose
    `parse_snapshot(take_snapshot(...))` itself, and nothing said when that stopped
    matching what the operator ran.

    Offline: `save_or_skip` is stubbed so no save is needed, and the landing is stubbed
    so no warehouse is. What is exercised for real is which function the fixture reaches.
    """
    calls: list[SaveRef] = []
    ref = SaveRef(league="Fake-League", root=Path("nowhere"))

    def _read_save(save: SaveRef, *, snapshot_root: Path, previous: object = None) -> Any:
        calls.append(save)
        return read.SaveReading(
            parsed=cast(ParsedSnapshot, _FakeParsed(run=_result().run)),
            verdict="no-prior",
            snapshot_dir_seq=1,
            mode="challenge",
        )

    monkeypatch.setattr(read, "read_save", _read_save)
    monkeypatch.setattr(fixtures_warehouse, "save_or_skip", lambda settings, which: ref)
    monkeypatch.setattr(fixtures_warehouse, "_land", lambda connection, parsed: _result().run)
    monkeypatch.setattr(fixtures_warehouse, "purge_snapshot", lambda connection, run: None)

    with fixtures_warehouse.landed_probe(
        cast(Settings, object()), cast("Connection[DictCursor]", object())
    ):
        pass

    assert len(calls) == 1, "landed_probe no longer routes through the shared function"
    assert calls[0] is ref


def test_an_unreachable_warehouse_is_named_rather_than_traced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The likeliest thing to happen to a fresh clone, and AC18's own first step.

    Before this, `main` had no handler for a driver error at all: a machine whose
    `mysql-bootstrap.sql` had never been run exited on a bare `OperationalError`
    traceback, which is neither the 0/1/2 contract the docstring promises nor a message
    anybody can act on.
    """
    monkeypatch.setattr(command, "load_settings", lambda: _settings(tmp_path))

    def _refuse(settings: Settings) -> object:
        raise pymysql.err.OperationalError(2003, "Can't connect to MySQL server")

    monkeypatch.setattr(command, "connect_warehouse", _refuse)

    assert command.main(["land"]) == 2
    err = capsys.readouterr().err
    assert "OperationalError" in err
    assert "mysql-bootstrap.sql" in err, "the message does not say how to fix it"
    assert "nothing was landed" in err.lower()


def test_a_save_id_cannot_be_combined_with_a_snapshot_re_land(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A snapshot's manifest names its own save, so the two can only disagree."""
    monkeypatch.setattr(command, "load_settings", lambda: _settings(tmp_path))

    assert command.main(["land", "--save-id", "OOTP-AI", "--from-snapshot", "d"]) == 2
    assert "--from-snapshot" in capsys.readouterr().err


def test_a_snapshot_directory_that_is_not_one_is_refused_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing manifest is `SnapshotCorrupt` on stderr and exit 1, not a traceback."""
    monkeypatch.setattr(command, "load_settings", lambda: _settings(tmp_path))
    monkeypatch.setattr(
        command, "connect_warehouse", lambda settings: _FakeWarehouse(_LandHarness())
    )
    monkeypatch.setattr(command, "ensure_tables", lambda *a, **k: ())
    empty = tmp_path / "not-a-snapshot"
    empty.mkdir()

    assert command.main(["land", "--from-snapshot", str(empty)]) == 1
    assert "SnapshotCorrupt" in capsys.readouterr().err


# ── gamedata: the real thing, against the probe only (SD-20) ─────────────────


def _probe_settings(tmp_path: Path) -> tuple[Settings, SaveRef]:
    """Real settings with the snapshot root redirected, plus the probe.

    Redirected because `take_snapshot` refuses to overwrite, so landing into the
    configured root on every run would accrete a 52.4 MiB directory per test. The source
    side — the only side ADR 0001 is about — is untouched by the redirect.
    """
    settings = replace(settings_or_skip(), snapshot_root=tmp_path / "snapshots")
    return settings, save_or_skip(settings, "probe_save")


def _purge_triple(connection: Connection[DictCursor], save_id: str, run: IngestRun) -> None:
    """Remove exactly the rows one landing wrote, reached from the triple alone.

    `purge_snapshot` reads only `save_id`, `sim_date` and `ingest_seq` off the run, which
    is why a landing recovered from stdout can be cleaned up as thoroughly as one held as
    an object.
    """
    purge_snapshot(connection, run)


def _triple_from(line: str) -> tuple[str, str, int]:
    """The three facts off line one of the human block — the format AC10 pins."""
    parts = line.split()
    assert parts[0] == "landed", f"line one is not the pinned format: {line!r}"
    return parts[1], parts[2], int(parts[4])


def _shell_run(save_id: str, sim_date: SaveDate, ingest_seq: int) -> IngestRun:
    """An `IngestRun` carrying only the three fields `purge_snapshot` reads."""
    return IngestRun(
        save_id=save_id,
        sim_date=sim_date,
        ingest_seq=ingest_seq,
        human_team_id=None,
        snapshot=Snapshot(
            save_id=save_id, sim_date=sim_date, ingest_seq=ingest_seq, path=Path(), files=()
        ),
        sources=(),
    )


def _fresh_view(connection: Connection[DictCursor]) -> None:
    """End the test connection's transaction so it can see another one's commits.

    **Load-bearing, and quietly so.** InnoDB defaults to REPEATABLE READ, and `land()`
    commits on a connection of its own. A test connection that read *before* that commit
    holds a read view from before it and cannot see the new rows — so a `read_ingest_run`
    would report a landing missing that is really there, and, far worse, a `table_digest`
    comparison across the boundary would compare a snapshot of the schema against itself
    and pass without looking at anything.

    Measured here: AC13 failed with "ingest_seq 3 is missing" for exactly this reason
    while the row was present. The vacuous direction is the one to fear.
    """
    connection.commit()


def _directories_under(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_dir()) if root.exists() else 0


def _rows_for(connection: Connection[DictCursor], table: str, run: IngestRun) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS n FROM {quote_ident(table)} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s",
            (run.save_id, as_sql_date(run.sim_date), run.ingest_seq),
        )
        row = cursor.fetchone()
    return 0 if row is None else int(row["n"])


def _landings(connection: Connection[DictCursor], save_id: str) -> set[tuple[str, int]]:
    """Every `(sim_date, ingest_seq)` the warehouse currently holds for one save."""
    _fresh_view(connection)
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {quote_ident('sim_date')} AS d, {quote_ident('ingest_seq')} AS s "
            f"FROM {quote_ident('ingest_run')} WHERE {quote_ident('save_id')} = %s",
            (save_id,),
        )
        return {(str(row["d"]), int(row["s"])) for row in cursor.fetchall()}


@contextmanager
def _reclaiming(connection: Connection[DictCursor], save_id: str) -> Iterator[None]:
    """Purge every landing this block adds, whatever happens inside it.

    **Driven by a before/after census, not by a triple parsed from stdout.** The earlier
    shape put the first `main(...)` and its stdout parse *outside* the `try:` whose
    `finally` purged, so a run that exited non-zero — or printed nothing, making
    `_triple_from` raise `IndexError` — stranded a complete landing: 52.4 MiB of rows
    under a sequence nothing reclaimed. One did exactly that
    (`Test-Save-Challenge-Mode` 2024-03-18 seq 2, 2026-08-30), and because the leaked row
    raises the warehouse maximum, the next run's sequence arithmetic moves under it and
    the suite starts failing for reasons that have nothing to do with the code. A leak
    that makes the next run red is worse than a leak, because it costs somebody a
    diagnosis.

    A census cannot be defeated that way: it asks the warehouse what is actually there.
    """
    before = _landings(connection, save_id)
    # The census above fixed this connection's read view. Every landing inside the block
    # commits on a connection of its own, so a test that reads back without calling
    # `_fresh_view` first would see none of them — and `_landings` itself refreshes,
    # which is what makes the reclaim below see what the block actually wrote.
    try:
        yield
    finally:
        for sim_date, seq in sorted(_landings(connection, save_id) - before):
            purge_snapshot(connection, _shell_run(save_id, _as_date(sim_date), seq))


@pytest.mark.gamedata
def test_the_command_lands_the_probe_and_the_warehouse_agrees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC10 and AC11, through `main()` — an exit code a test asserts, not a human reads.

    **`--new-look` is required here rather than incidental.** The probe already holds a
    landing and does not sim between test runs, so the *default* path's correct answer
    against it is a refusal — which is what the next test asserts. Forcing the landing is
    what makes this test deterministic on a machine that has ingested before, and it
    still drives every step of the real path: connect, ensure, read, copy, verify,
    reconcile, land.
    """
    settings, probe = _probe_settings(tmp_path)
    monkeypatch.setattr(command, "load_settings", lambda: settings)

    with warehouse_or_skip(settings) as connection, _reclaiming(connection, probe.save_id):
        # Through `land()` rather than `main()`, because AC11's middle clause compares the
        # landed `table_row_counts` against the returned `run.row_counts` — and `main()`
        # returns an int, so a test driven through it can never hold the run to compare.
        result = command.land(settings, save_id=probe.save_id, new_look=True)
        run = result.run

        # `_reclaiming`'s opening census fixed this connection's read view, and `land()`
        # committed on a connection of its own — so without this the row it just wrote is
        # invisible here and the landing reads as missing.
        _fresh_view(connection)
        landed = read_ingest_run(
            connection,
            save_id=run.save_id,
            sim_date=run.sim_date,
            ingest_seq=run.ingest_seq,
        )
        assert landed is not None, "the command reported a triple the warehouse lacks"
        assert landed["table_row_counts"] == dict(run.row_counts), (
            "the warehouse's own row counts disagree with the ones the run reported"
        )
        assert run.row_counts["bronze_player"] > 0
        assert _rows_for(connection, "bronze_player", run) == run.row_counts["bronze_player"]

        # AC10's half: the same path through `main()`, whose exit code is the thing an
        # operator actually sees. Asserted here so the two halves cannot drift apart.
        assert command.main(["land", "--save-id", probe.save_id, "--new-look"]) == 0
        out = capsys.readouterr().out
        save_id, _date, ingest_seq = _triple_from(out.splitlines()[0])
        assert save_id == probe.save_id
        assert ingest_seq > run.ingest_seq, "the second landing reused the first's sequence"


@pytest.mark.gamedata
def test_an_unchanged_save_is_refused_before_anything_is_copied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC12. The directory count is what makes "before the copy" an observation.

    A refusal that fired *after* the copy would still exit non-zero and still name the
    triple — and would silently leave 52.4 MiB under a sequence nothing reclaims. Only
    counting directories can tell the two apart.
    """
    settings, probe = _probe_settings(tmp_path)
    monkeypatch.setattr(command, "load_settings", lambda: settings)

    with warehouse_or_skip(settings) as connection, _reclaiming(connection, probe.save_id):
        assert command.main(["land", "--save-id", probe.save_id, "--new-look"]) == 0
        first = capsys.readouterr().out
        save_id, sim_date, ingest_seq = _triple_from(first.splitlines()[0])
        run = _shell_run(save_id, _as_date(sim_date), ingest_seq)

        before_dirs = _directories_under(settings.snapshot_root)
        before_rows = _landings(connection, probe.save_id)

        code = command.main(["land", "--save-id", probe.save_id])

        captured = capsys.readouterr()
        assert code != 0
        assert "SaveUnchanged" in captured.err
        assert str(ingest_seq) in captured.err, "the refusal did not name the triple"
        assert sim_date in captured.err, "the refusal did not name the landed date"
        assert "--new-look" in captured.err
        assert _directories_under(settings.snapshot_root) == before_dirs, (
            "a directory appeared, so the refusal fired after the copy rather than before"
        )
        assert _landings(connection, probe.save_id) == before_rows, (
            "the refusal still wrote an ingest_run row"
        )
        assert run.ingest_seq == ingest_seq


@pytest.mark.gamedata
def test_changed_bytes_at_an_unchanged_sim_date_land_with_no_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC13. ADR 0021's motivating case, flowing with no flag at all.

    The change is simulated by altering the *prior landing the pre-flight compares
    against*, never by editing a real save (ADR 0001). That exercises the same branch a
    genuinely-simmed save would: one digest differs, so `reason_from_digests` returns a
    reason and the landing proceeds.
    """
    settings, probe = _probe_settings(tmp_path)
    monkeypatch.setattr(command, "load_settings", lambda: settings)

    with warehouse_or_skip(settings) as connection, _reclaiming(connection, probe.save_id):
        assert command.main(["land", "--save-id", probe.save_id, "--new-look"]) == 0
        first_id, first_date, first_seq = _triple_from(capsys.readouterr().out.splitlines()[0])
        first = _shell_run(first_id, _as_date(first_date), first_seq)

        real = command._prior_landing(connection, probe.save_id)
        assert real is not None
        moved = read.PriorLanding(
            sim_date=real.sim_date,
            ingest_seq=real.ingest_seq,
            files=tuple(
                SnapshotFile(name=f.name, size=f.size, sha256="0" * 64)
                if f.name == "players.dat"
                else f
                for f in real.files
            ),
        )
        monkeypatch.setattr(command, "_prior_landing", lambda *a, **k: moved)

        assert command.main(["land", "--save-id", probe.save_id]) == 0
        out = capsys.readouterr().out
        second_id, second_date, second_seq = _triple_from(out.splitlines()[0])
        second = _shell_run(second_id, _as_date(second_date), second_seq)

        assert second_date == first_date, "the sim date should not have moved"
        assert second_seq != first_seq, "the second landing reused the first's sequence"
        assert "verdict: changed" in out, (
            "a landing driven by a digest difference must report the changed verdict, "
            "not the no-prior one"
        )

        _fresh_view(connection)
        for run in (first, second):
            assert (
                read_ingest_run(
                    connection,
                    save_id=run.save_id,
                    sim_date=run.sim_date,
                    ingest_seq=run.ingest_seq,
                )
                is not None
            ), f"ingest_seq {run.ingest_seq} is missing — both sequences must persist"


@pytest.mark.gamedata
def test_new_look_lands_identical_bytes_without_disturbing_the_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC14. Append-only, proved by digesting the first landing's rows either side.

    The same assertion shape as
    `test_snapshot_semantics.py::test_two_sequences_of_one_sim_date_both_persist`: a
    second landing at the same date must be additive, and a per-snapshot digest over
    every declared table is what says so rather than a row count that could coincide.
    """
    settings, probe = _probe_settings(tmp_path)
    monkeypatch.setattr(command, "load_settings", lambda: settings)
    tables = load_contracts().tables

    with warehouse_or_skip(settings) as connection, _reclaiming(connection, probe.save_id):
        assert command.main(["land", "--save-id", probe.save_id, "--new-look"]) == 0
        out = capsys.readouterr().out
        first_id, first_date, first_seq = _triple_from(out.splitlines()[0])
        first = _shell_run(first_id, _as_date(first_date), first_seq)
        assert "verdict: new-look" in out, (
            "a forced landing must not report no-prior on a save that has landed before"
        )

        _fresh_view(connection)
        before = {
            table.name: table_digest(
                connection,
                table,
                save_id=first_id,
                sim_date=as_sql_date(first.sim_date),
                ingest_seq=first_seq,
            )
            for table in tables
        }

        assert command.main(["land", "--save-id", probe.save_id, "--new-look"]) == 0
        _id, _date, second_seq = _triple_from(capsys.readouterr().out.splitlines()[0])

        assert second_seq == first_seq + 1, "a new look takes the next sequence"

        # Without this the two digest passes share one read view and the comparison
        # compares the schema against itself — green, and proving nothing.
        _fresh_view(connection)
        after = {
            table.name: table_digest(
                connection,
                table,
                save_id=first_id,
                sim_date=as_sql_date(first.sim_date),
                ingest_seq=first_seq,
            )
            for table in tables
        }
        assert after == before, "the second landing changed the first one's rows"


@pytest.mark.gamedata
def test_from_snapshot_re_lands_without_reading_the_game(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC15. The correction ADR 0021 names, with the game provably untouched.

    The manifest diff is the same instrument `tests/test_read_only.py` uses, run over
    both game roots across the invocation. A re-land that opened the save would show up
    here as a changed mtime even though the read itself is harmless — which is the point:
    this path is supposed to reach the game not at all.
    """
    settings, probe = _probe_settings(tmp_path)
    monkeypatch.setattr(command, "load_settings", lambda: settings)
    snapshot = take_snapshot(probe, snapshot_root=settings.snapshot_root)

    roots = {"OOTP_SAVED_GAMES": settings.saved_games, "OOTP_INSTALL": settings.install}
    before = {key: test_read_only.manifest(root) for key, root in roots.items()}

    with warehouse_or_skip(settings) as connection, _reclaiming(connection, probe.save_id):
        code = command.main(["land", "--from-snapshot", str(snapshot.path)])
        out = capsys.readouterr().out
        assert code == 0, out
        save_id, sim_date, ingest_seq = _triple_from(out.splitlines()[0])
        run = _shell_run(save_id, _as_date(sim_date), ingest_seq)

        for key, root in roots.items():
            assert test_read_only.differences(before[key], test_read_only.manifest(root)) == [], (
                f"re-landing a snapshot touched ${key}"
            )

        _fresh_view(connection)
        assert (
            read_ingest_run(
                connection, save_id=save_id, sim_date=run.sim_date, ingest_seq=ingest_seq
            )
            is not None
        )
        assert "not recorded" in out, "the save mode was guessed rather than reported absent"

        # AC15's third clause, asserted so it can FAIL. The earlier form was
        # `str(dir_seq) in out or ingest_seq == dir_seq`, a disjunction whose second
        # branch is true exactly when the first is uninformative — it passed whether the
        # command said anything or not. What the criterion asks is that the output STATE
        # the relationship, so that is what is asserted: the line is present, it names
        # the directory's own number, and it says which way the two went.
        sequence = next(line for line in out.splitlines() if "sequence:" in line)
        assert f"snapshot directory {snapshot.ingest_seq}" in sequence, sequence
        if ingest_seq == snapshot.ingest_seq:
            assert "agree" in sequence or "gapped" in sequence, sequence
        else:
            assert "NOT filed under" in sequence, sequence

        for label, pattern in test_no_leaks.PATTERNS:
            assert not pattern.search(out), f"{label} reached --from-snapshot's output"
