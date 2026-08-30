"""The ingest-run record: what was read, from where, and on whose authority.

The shape was landed in Phase 4 before anything could fill it, on purpose — a provenance
schema invented three phases later, under time pressure, is how a grain drifts and how a
key ends up meaning two things. Phase 8b is where it starts being filled:
`parse_snapshot` walks a landed snapshot and returns the run with `residual_bytes` and
`parse_seconds` measured, and `warehouse/load.py` returns it again with `row_counts` set
to what actually landed.

`ingest_save` still returns the empty shape. It snapshots and resolves provenance and
stops there, which is the operation Phase 4 defined and which several tests pin; parsing
is a separate, more expensive act and the two are worth being able to do apart.

**Every fact in a run is resolved from data, never configured or assumed.** The sim date
comes from `teams.dat`'s own header, the digests and sizes from the snapshot copy, and
the version from each file's header. Code that hardcoded *"we are team 6"* would pass on
every save the parser is developed against and break invisibly on the managed league —
and since the validation harness runs against a probe, nothing would catch it. The human
club is now resolved the same way, out of the snapshot's own `human_managers.dat`.

**Nothing here writes.** `snapshot.py` is the only module in this package allowed to
create a file, and `tests/test_read_only.py` asserts that allowlist mechanically. This
module reads a snapshot that has already landed, and never re-opens the save.

**No path field, anywhere in the record.** `saved_games.dat` embeds an absolute
user-profile path per save, and an ingest-run row is the artifact most likely to be
rendered into a catalog. The defence is that the type has nowhere to put one (ADR 0006).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from ootp_ai.config import SaveRef, Settings
from ootp_ai.parser.header import read_header
from ootp_ai.parser.human_managers import HUMAN_MANAGERS_FILE, read_human_manager
from ootp_ai.parser.names import NAMES_FILE, NamesFile, read_names
from ootp_ai.parser.players import PLAYERS_FILE, PlayersFile, read_players
from ootp_ai.parser.primitives import SaveDate
from ootp_ai.parser.rosters import RostersFile, read_rosters
from ootp_ai.parser.teams import TEAMS_FILE, TeamsFile, read_teams
from ootp_ai.parser.world import WORLD_FILE, WorldFile, read_world
from ootp_ai.snapshot import Snapshot, SnapshotFile, read_manifest, take_snapshot

__all__ = [
    "PARSED_FILES",
    "IngestRun",
    "ParsedSnapshot",
    "SnapshotDateMismatch",
    "SourceFile",
    "UndecodedRecords",
    "check_decoded",
    "check_sim_dates",
    "dump_parse",
    "ingest_save",
    "parse_snapshot",
]

#: The files a parse reads, each exactly once. `human_managers.dat` is in the snapshot and
#: is *not* here: it is 835 bytes read for provenance, not a table.
PARSED_FILES: tuple[str, ...] = (TEAMS_FILE, PLAYERS_FILE, NAMES_FILE, WORLD_FILE)


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One parsed input, as provenance rather than as content.

    `version` is the header's self-declared format version, read from the snapshot copy
    of each file individually rather than assumed from the save. A patched game that
    moved one file's layout would show up here as a refusal, not as a silent misparse.
    """

    name: str
    size: int
    sha256: str
    version: int


@dataclass(frozen=True, slots=True)
class IngestRun:
    """Everything one pass over one snapshot knows about itself.

    Keyed, like every bronze table, on `(save_id, sim_date, ingest_seq)` — the universe,
    the in-game date, and which attempt at that date (plan §2.3(d)). There is no
    wall-clock field in the key: ingestion time is an attribute, and keying on it would
    fragment a single game state across re-runs.

    `human_team_id` is resolved from `human_managers.dat`, which names the managed club
    outright in 835 bytes. It is **not** taken from `saved_games.dat`, which carries only
    a display string ("Chicago" is two clubs), and not from `teams.dat`, which reaches the
    same answer through the last slot of a variable-length integer run — a longer route,
    and the one `tests/test_parse_real_save.py` cross-checks this against rather than
    trusts. `None` means the file was absent from the snapshot, which is a known gap and
    never a zero.
    """

    save_id: str
    sim_date: SaveDate
    ingest_seq: int
    human_team_id: int | None
    snapshot: Snapshot
    sources: tuple[SourceFile, ...]
    #: Per-table landed row counts. Filled by the bronze loader, Phase 8.
    row_counts: Mapping[str, int] = field(default_factory=dict)
    #: Per-file unaccounted bytes after a walk. Filled by the walkers, Phase 6.
    residual_bytes: Mapping[str, int] = field(default_factory=dict)
    #: Wall-clock duration of the walk, from `time.perf_counter()`: reading the four parsed
    #: files and the five walker calls over them, plus the agreement checks. `None` means
    #: "not measured", which is not the same number as zero — an ingest that never parsed
    #: and one that parsed instantaneously must not read alike. `parse_snapshot` sets it.
    #:
    #: It does **not** include snapshotting, header provenance, or landing. Phase 9 reads
    #: this to answer whether re-ingestion is viable, so what it covers is stated rather
    #: than left to be inferred from where the timer happens to stop.
    parse_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ParsedSnapshot:
    """Everything one walk of one snapshot produced, plus the run that describes it.

    The five walkers land here together because bronze is written in one transaction: a
    snapshot whose `teams.dat` landed and whose `players.dat` raised would leave the
    warehouse holding half a universe under a key that claims to be whole.

    **`teams` and `rosters` come from the same two buffers, read once.** Phase 6b's panel
    (CF-7) recorded `read_rosters` walking the 32 MB `players.dat` a second time and
    deferred the fix here. The buffer is now read once and shared, which is free and safe
    because `bytes` is immutable — the plan's caution about "a shared mutable buffer
    between two walkers" does not apply in Python. The second *walk* remains: collapsing
    it would mean `read_rosters` consuming `read_players`' output instead of the bytes,
    which is a parser change nobody sequenced. The measurement is in the phase handoff.
    """

    run: IngestRun
    teams: TeamsFile
    players: PlayersFile
    rosters: RostersFile
    names: NamesFile
    world: WorldFile


class SnapshotDateMismatch(Exception):  # noqa: N818
    """Two files of one snapshot name different in-game dates.

    That means two snapshots got mixed, and a warehouse row set built across them would
    describe a state of the league that never existed. `parser/rosters.py` already refuses
    outright on a `teams.dat` ↔ `players.dat` disagreement for exactly this reason; this
    extends the same refusal to the three files it does not read together.

    Named without the `…Error` suffix to match `SnapshotExists` and `SnapshotCorrupt`,
    which are the same concept seen from the filesystem side.
    """


def parse_snapshot(snapshot: Snapshot) -> ParsedSnapshot:
    """Walk every in-scope file of a landed snapshot and measure what it cost.

    Reads the **snapshot copy**, never the save. That is the whole reason snapshots exist:
    the warehouse is rebuildable from one, and a disagreement between the two is decidable
    only if the bytes the parse saw are still on disk.

    Raises:
        SaveFormatError: any walker refused its file — a header, a record layout, or a
            count that is not what every save measured holds.
        SnapshotDateMismatch: two files disagree about the league's in-game date.
    """
    started = perf_counter()
    buffers = {name: (snapshot.path / name).read_bytes() for name in PARSED_FILES}

    teams = read_teams(buffers[TEAMS_FILE])
    players = read_players(buffers[PLAYERS_FILE])
    rosters = read_rosters(buffers[TEAMS_FILE], buffers[PLAYERS_FILE])
    names = read_names(buffers[NAMES_FILE])
    world = read_world(buffers[WORLD_FILE])

    check_sim_dates(
        snapshot.sim_date,
        {
            TEAMS_FILE: teams.sim_date,
            PLAYERS_FILE: players.sim_date,
            NAMES_FILE: names.sim_date,
            WORLD_FILE: world.sim_date,
        },
    )
    check_decoded(players)

    elapsed = perf_counter() - started

    run = IngestRun(
        save_id=snapshot.save_id,
        sim_date=snapshot.sim_date,
        ingest_seq=snapshot.ingest_seq,
        human_team_id=_resolve_human_team(snapshot),
        snapshot=snapshot,
        sources=tuple(
            _describe(snapshot, entry, buffers.get(entry.name)) for entry in snapshot.files
        ),
        residual_bytes={
            TEAMS_FILE: teams.residual_bytes,
            PLAYERS_FILE: players.residual_bytes,
            NAMES_FILE: names.residual_bytes,
            # `world.dat` is walked region-accounted, not strictly: a landmark-entered walk
            # of a single-record 8.9 MB file never reads most of it, so the honest number
            # is the span no region covered rather than a residual (`tests/fixtures/tiers.py`).
            WORLD_FILE: world.file_bytes - sum(region.length for region in world.regions),
        },
        parse_seconds=elapsed,
    )
    return ParsedSnapshot(
        run=run, teams=teams, players=players, rosters=rosters, names=names, world=world
    )


class UndecodedRecords(Exception):  # noqa: N818
    """A walk crossed records whose tail it could not decode, so the format moved.

    `parser/players.py` delegates this refusal outright: *"On every save on disk that count
    is zero; a nonzero count means the format changed and the landing gate must refuse, not
    guess."* Phase 8b is the landing gate, so the refusal lives here.

    **The alternative is the shape this project ranks worse than a crash.** A soft landing
    would put NULL into `bats`, `throws` and `historical_id` for an unknown fraction of
    records, commit a run row that looks perfectly healthy, and leave nothing downstream
    able to ask how many records failed to decode — a confidently wrong roster with nothing
    raised.
    """


def check_sim_dates(expected: SaveDate, by_file: Mapping[str, SaveDate]) -> None:
    """Refuse a snapshot whose files do not agree about the league's in-game date.

    Every bronze row is keyed on one date, taken from `teams.dat`'s header because that is
    the file the snapshot reads first. `snapshot.py` labels *"every record file in a save
    carries the same sim date in its header"* **measured** — and this project's convention
    is that a belief nothing checks is a task, not a fact. Four comparisons over values
    already in hand turn it into a check.

    The failure it catches is a mixed snapshot: 264,095 name rows and 3,058 calendar rows
    landing under a date that does not describe them, silently, because nothing read the
    dates those files declare.

    Raises:
        SnapshotDateMismatch: naming every disagreeing file and both dates.
    """
    disagreeing = {name: date for name, date in by_file.items() if date != expected}
    if disagreeing:
        detail = ", ".join(f"{name} declares {date}" for name, date in sorted(disagreeing.items()))
        raise SnapshotDateMismatch(
            f"the snapshot is dated {expected} but {detail}. These are two different "
            "snapshots, and a row set built across them would describe a state of the "
            "league that never existed"
        )


def check_decoded(players: PlayersFile) -> None:
    """Refuse a walk that crossed records whose tail it could not decode.

    Public and named because `parser/players.py` refers to "the landing gate" as a thing
    that exists; an unnamed private would leave the delegation pointing at nothing a reader
    can find.

    Raises:
        UndecodedRecords: naming the count.
    """
    if players.undecoded_tails:
        raise UndecodedRecords(
            f"{players.undecoded_tails} player records were crossed without their tail "
            "being decoded, against zero on every save measured. That means the record "
            "layout moved, and landing would write NULL handedness and NULL Lahman ids "
            "for those records under a run row that looks healthy. Re-measure the tail "
            "rather than loosening this"
        )


def dump_parse(path: Path) -> str:
    """Serialize the parse of the snapshot at `path`, deterministically and key-sorted.

    This is how "parsing the same snapshot twice is byte-identical" (AC10) becomes
    testable: hash this, twice, and compare. Determinism is the entire contract, so two
    things are deliberately **not** in it — `parse_seconds`, which is wall-clock and
    differs on every run, and the snapshot's filesystem path, which differs per machine
    and would put a home directory into a string this repo is public enough to regret
    (ADR 0006).

    Every collection is emitted in its declared key order rather than in walk order, so a
    walker that returned the same rows in a different sequence still compares equal — the
    claim being made is about the *data*, not about iteration.

    It covers the **diagnostics** as well as the rows — residuals, declared-versus-parsed
    counts, the content digest, the unrostered pairs, the walked region spans. Those are
    walker outputs too, and a digest that skipped them would let a walk vary in the numbers
    the ingest-run row is built from while still reporting itself byte-identical.
    """
    return _serialize(parse_snapshot(read_manifest(path)))


def _serialize(parsed: ParsedSnapshot) -> str:
    run = parsed.run
    payload: dict[str, Any] = {
        "save_id": run.save_id,
        "sim_date": str(run.sim_date),
        "ingest_seq": run.ingest_seq,
        "human_team_id": run.human_team_id,
        "sources": sorted(
            (
                {"name": s.name, "size": s.size, "sha256": s.sha256, "version": s.version}
                for s in run.sources
            ),
            key=lambda entry: str(entry["name"]),
        ),
        "residual_bytes": dict(run.residual_bytes),
        # The walkers' own diagnostics. Deterministic by construction, and each one feeds
        # something the ingest-run row records — so leaving them out would let the numbers
        # in that row vary while the digest reported the parse unchanged.
        "diagnostics": {
            "players_content_digest": parsed.players.content_digest,
            "players_declared_record_count": parsed.players.declared_record_count,
            "players_undecoded_tails": parsed.players.undecoded_tails,
            "names_declared_record_count": parsed.names.declared_record_count,
            "world_file_bytes": parsed.world.file_bytes,
            "world_regions": sorted(
                [
                    region.name,
                    region.entered_at,
                    region.length,
                    region.declared_count,
                    region.parsed_count,
                ]
                for region in parsed.world.regions
            ),
            "unrostered": sorted(
                [team_id, player_id] for team_id, player_id in parsed.rosters.unrostered
            ),
        },
        "teams": sorted(
            (
                {
                    "team_id": team.team_id,
                    "city": team.city,
                    "abbr": team.abbr,
                    "nickname": team.nickname,
                    "logo_filename": team.logo_filename,
                    "full_name": team.full_name,
                    "colors": list(team.colors),
                    "city_id": team.city_id,
                    "park_id": team.park_id,
                    "league_id": team.league_id,
                    "sub_league_id": team.sub_league_id,
                    "nation_id": team.nation_id,
                    "human_team": team.human_team,
                    "level": team.level,
                    "parent_team_id": team.parent_team_id,
                    "historical_id": team.historical_id,
                }
                for team in parsed.teams.teams
            ),
            key=lambda entry: int(entry["team_id"]),
        ),
        "players": sorted(
            (
                {
                    "player_id": player.player_id,
                    "first_name_index": player.first_name_index,
                    "last_name_index": player.last_name_index,
                    "date_of_birth": str(player.date_of_birth),
                    "age": player.age,
                    "nation_id": player.nation_id,
                    "city_of_birth_id": player.city_of_birth_id,
                    "weight": player.weight,
                    "height": player.height,
                    "uniform_number": player.uniform_number,
                    "experience": player.experience,
                    "team_id": player.team_id,
                    "last_team_id": player.last_team_id,
                    "organization_id": player.organization_id,
                    "last_organization_id": player.last_organization_id,
                    "league_id": player.league_id,
                    "last_league_id": player.last_league_id,
                    "free_agent": player.free_agent,
                    "bats": player.bats,
                    "throws": player.throws,
                    "historical_id": player.historical_id,
                }
                for player in parsed.players.players
            ),
            key=lambda entry: int(entry["player_id"]),
        ),
        "rosters": sorted(
            [row.team_id, row.player_id, row.list_id] for row in parsed.rosters.memberships
        ),
        "names": sorted(
            (
                {"index": record.index, "text": record.text, "category": record.category}
                for record in parsed.names.names
            ),
            key=lambda entry: int(entry["index"]),
        ),
        "divisions": sorted(
            [
                membership.league_id,
                membership.sub_league_id,
                membership.division_id,
                sorted(membership.team_ids),
            ]
            for membership in parsed.world.divisions
        ),
        "calendar": sorted(
            (
                {
                    "seq": event.seq,
                    "league_id": event.league_id,
                    "event_type": event.event_type,
                    "start_date": str(event.start_date),
                    "name": event.name,
                    "event_over": event.event_over,
                    "deleted": event.deleted,
                    "needs_human_action": event.needs_human_action,
                    "real_sim_date": event.real_sim_date,
                }
                for event in parsed.world.calendar
            ),
            key=lambda entry: int(entry["seq"]),
        ),
    }
    # `ensure_ascii` on purpose: names are latin-1 and this project develops on Windows and
    # runs CI on Linux, so an escaped-ASCII dump hashes to the same digest on both.
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True)


def ingest_save(save: SaveRef, *, settings: Settings) -> IngestRun:
    """Snapshot a save, digest what was copied, and resolve the run's provenance.

    Deliberately stops there: no walker runs, no warehouse is opened, nothing is
    persisted beyond the copy. What it establishes is that everything downstream parses an
    immutable copy rather than the live save — which is the whole reason it runs *before*
    the walkers open the 32 MB files, not after. Hand the returned `run.snapshot` to
    `parse_snapshot` to go further.

    The only interaction with the game's directories is reading. ADR 0001: one write to
    the managed Challenge Mode save is unrecoverable, and there is no upstream backup.

    Raises:
        SnapshotExists: this `(save_id, sim_date, ingest_seq)` already landed.
        SaveFormatError: a header is not version 25, or a file is not what it claims.
    """
    snapshot = take_snapshot(save, snapshot_root=settings.snapshot_root)
    return IngestRun(
        save_id=snapshot.save_id,
        sim_date=snapshot.sim_date,
        ingest_seq=snapshot.ingest_seq,
        human_team_id=_resolve_human_team(snapshot),
        snapshot=snapshot,
        sources=tuple(_describe(snapshot, entry, None) for entry in snapshot.files),
    )


def _resolve_human_team(snapshot: Snapshot) -> int | None:
    """Which club this universe is managed by, read from the snapshot copy.

    From the **copy**, never the save: re-opening the game's directory to answer a
    question the snapshot can answer is avoidable contact with the one tree this project
    must not disturb, and the copy is verified byte-identical to it (ADR 0001).

    `None` only when the file is not in the snapshot at all — a save shape this project
    has not seen. A parse failure is *not* swallowed into `None`: an unreadable
    `human_managers.dat` means the run does not know which club it describes, and every
    bronze row would be stamped with that ignorance.
    """
    source = snapshot.path / HUMAN_MANAGERS_FILE
    if not source.is_file():
        return None
    return read_human_manager(source.read_bytes()).team_id


def _describe(snapshot: Snapshot, entry: SnapshotFile, payload: bytes | None) -> SourceFile:
    """Attach a header version to a file the snapshot has already sized and digested.

    Read from the **snapshot copy**, not the save. Re-opening the save to answer a
    question the copy can answer is avoidable contact with the one directory this
    project must not disturb, and the copy is verified identical to it.

    `payload` is the buffer the walk already loaded, when there is one. Re-reading the four
    parsed files here to look at 25 bytes of header cost ~48 MB of avoidable I/O per
    ingest — and it happened *after* the timer stopped, so it did not even show up in the
    number Phase 9 is specified to make a decision from. `human_managers.dat` has no walker
    and is 835 bytes, so it is read here.
    """
    payload = (snapshot.path / entry.name).read_bytes() if payload is None else payload
    header = read_header(payload, entry.name)
    return SourceFile(
        name=entry.name,
        size=entry.size,
        sha256=entry.sha256,
        version=header.version,
    )
