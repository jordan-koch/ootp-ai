"""Where a snapshot came from — resolved from data, and carrying no username.

Two binds meet in this module, and both are structural rather than advisory.

**The human team is resolved from the save on every run.** Plan §2.5: `OOTP-AI` is
Boston, the Challenge probe is *also* Boston, and the standard-mode save is the Cubs.
Code that hardcodes *"we are team 6"* passes on both saves the parser is developed
against and breaks on nothing visible — and since the validation harness runs against
the probe, no existing test would catch it. So the control is the third save: the
three universes must not all resolve to the same club.

**`saved_games.dat` embeds an absolute user-profile path per save, and it must not be
representable in anything this pipeline carries forward** (plan §4 step 5). Not
filtered on the way out — *absent from the type*, the way `SaveHeader` has no
`body_offset`. A field that cannot be constructed cannot be rendered into a tracked
catalog by a later phase that did not read this comment. This repo is public, and a
provenance section that published a username would be a permanent leak (ADR 0006).

The offline half pins the shapes; the `gamedata` half reads the real index.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path

import pytest

from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.ingest import IngestRun, SourceFile, ingest_save
from ootp_ai.parser.saved_games import SAVED_GAMES_FILE, SavedGameEntry, read_saved_games

#: Any of these on `SavedGameEntry` would be a place for the embedded absolute path
#: to live. The field is not filtered — it does not exist.
PATH_SHAPED_NAMES = frozenset(
    {"path", "root", "directory", "dir", "folder", "location", "file", "filename", "save_path"}
)


# ── offline: shapes that make the leak unrepresentable ───────────────────────


def _field_names(cls: type) -> frozenset[str]:
    assert is_dataclass(cls), f"{cls.__name__} is expected to be a dataclass"
    return frozenset(f.name for f in fields(cls))


def test_a_saved_game_entry_has_nowhere_to_put_a_path() -> None:
    offenders = _field_names(SavedGameEntry) & PATH_SHAPED_NAMES
    assert not offenders, (
        f"SavedGameEntry gained {sorted(offenders)}. `saved_games.dat` embeds an "
        "absolute user-profile path, and this repo is public — the defence is that "
        "the field does not exist, not that callers remember to drop it."
    )


def test_a_saved_game_entry_carries_exactly_what_it_is_for() -> None:
    """Which league, at what in-game date, managed by whom. Nothing else.

    `human_team_name` is the club's display string and is here to **check** Phase 5's
    answer, not to be joined on — `teams.dat` resolves the id from a flag, and this is
    the only independent statement of which club that should be.
    """
    assert _field_names(SavedGameEntry) == {
        "league",
        "sim_date",
        "human_team_id",
        "human_team_name",
    }


def test_an_ingest_run_has_nowhere_to_put_a_path_either() -> None:
    """The provenance record is the thing most likely to be rendered somewhere."""
    offenders = _field_names(IngestRun) & PATH_SHAPED_NAMES
    assert not offenders, f"IngestRun gained {sorted(offenders)}"


def test_the_ingest_run_shape_is_landed_now_and_filled_later() -> None:
    """Plan §4 step 2: land the shape in this phase so later phases fill fields.

    `row_counts` (Phase 8), `residual_bytes` (Phase 6) and `parse_seconds` (Phase 9)
    are all empty here. Their presence is the point — a schema invented under time
    pressure three phases from now is how a grain drifts.
    """
    assert _field_names(IngestRun) == {
        "save_id",
        "sim_date",
        "ingest_seq",
        "human_team_id",
        "snapshot",
        "sources",
        "row_counts",
        "residual_bytes",
        "parse_seconds",
    }
    assert _field_names(SourceFile) == {"name", "size", "sha256", "version"}


def test_the_path_shaped_name_list_is_not_vacuous() -> None:
    """A guard that matches nothing passes on every possible dataclass."""
    assert PATH_SHAPED_NAMES & _field_names(SaveRef), (
        "SaveRef legitimately carries a root path, so it proves the name list can "
        "actually match something. If it stops matching, the list has gone stale."
    )


# ── gamedata: the real index ─────────────────────────────────────────────────


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings: {exc}")


def _entries(settings: Settings) -> tuple[SavedGameEntry, ...]:
    index = settings.saved_games / SAVED_GAMES_FILE
    if not index.is_file():
        pytest.skip(f"no {SAVED_GAMES_FILE} under the saved-games root")
    return read_saved_games(index.read_bytes())


@pytest.mark.gamedata
def test_the_saved_games_index_lists_the_saves_on_disk() -> None:
    settings = _settings()
    listed = {entry.league for entry in _entries(settings)}
    assert settings.managed.league in listed, (
        f"the managed league is absent from {SAVED_GAMES_FILE}: found {sorted(listed)}"
    )


@pytest.mark.gamedata
def test_no_entry_carries_a_drive_letter_or_home_directory() -> None:
    """The substring form of the same bind, against the real bytes.

    The type makes the leak unrepresentable; this proves the walker did not smuggle
    it into a value instead — a league named after its own directory would do it.
    """
    settings = _settings()
    forbidden = (str(settings.saved_games), str(settings.install))
    for entry in _entries(settings):
        for value in (entry.league, entry.human_team_name):
            if value is None:
                continue
            for root in forbidden:
                assert root not in value, f"{value!r} carries a machine path"
            assert ":" not in value and "\\" not in value, f"{value!r} looks like a path"


def _all_three(settings: Settings) -> list[SavedGameEntry]:
    """The three configured saves, in a fixed order, or a skip naming what is missing."""
    if settings.probe_save is None or settings.truth_save is None:
        pytest.skip("both validation saves are needed — a two-Boston sample proves nothing")

    by_league = {entry.league: entry for entry in _entries(settings)}
    wanted = [settings.managed.league, settings.probe_save.league, settings.truth_save.league]
    missing = [name for name in wanted if name not in by_league]
    assert not missing, f"{SAVED_GAMES_FILE} does not list {missing}"
    return [by_league[name] for name in wanted]


@pytest.mark.gamedata
def test_the_human_club_is_read_from_data_not_hardcoded() -> None:
    """The control that works at this phase: Boston, Boston, Chicago.

    The display name is the only human-club fact the index carries, and it is enough to
    prove the walk reaches the right region of the record. It is **not** enough to
    identify the club to the warehouse, which is what its sibling below is for.
    """
    names = [entry.human_team_name for entry in _all_three(_settings())]

    assert all(names), f"a human club failed to resolve: {names}"
    assert len(set(names)) > 1, (
        f"all three saves resolved to {names[0]!r} — the standard-mode save is managed "
        "by the Chicago Cubs and the other two by Boston, so a single value means the "
        "field is hardcoded or the walk is reading the wrong region"
    )


@pytest.mark.gamedata
def test_the_human_team_id_resolves_to_the_club_the_warehouse_knows() -> None:
    """KNOWN RED until Phase 5. The index carries no team id; `teams.dat` does.

    Kept red rather than deleted or xfailed, because this is the assertion that actually
    matters: a display name cannot key a join, and every downstream row needs the id.

    Measured 2026-08-16 — the index identifies the human club by display name and logo
    filename only. Every numeric slot in all three records was enumerated at u8/u16/u32
    against ground truth (Boston 4, Cubs 6) with no match. The one slot that separates
    the Boston saves from the Cubs save reads 2/2/1 and splits Challenge/Challenge/
    Standard, not Boston/Boston/Chicago — reading it here would go green with a
    confidently wrong club, which is the one failure this project cannot afford.
    """
    teams = [entry.human_team_id for entry in _all_three(_settings())]

    assert all(team is not None for team in teams), (
        f"a human team id failed to resolve: {teams}. EXPECTED until Phase 5 lands the "
        "teams.dat walk — the id comes from a flag on the team record, not from the "
        "index. This is a known gap, not a regression."
    )
    assert len(set(teams)) > 1, f"all three saves resolved to team {teams[0]}"


@pytest.mark.gamedata
def test_the_sim_dates_differ_across_saves_as_measured() -> None:
    """2024-03-07 managed, 2024-03-18 both probes. A constant cannot produce both."""
    settings = _settings()
    if settings.probe_save is None:
        pytest.skip("OOTP_PROBE_LEAGUE is unset — nothing to compare the managed date against")

    by_league = {entry.league: entry for entry in _entries(settings)}
    managed = by_league.get(settings.managed.league)
    probe = by_league.get(settings.probe_save.league)
    if managed is None or probe is None:
        pytest.skip(f"{SAVED_GAMES_FILE} does not list both saves")

    assert str(managed.sim_date) != str(probe.sim_date)


@pytest.mark.gamedata
def test_an_ingest_run_resolves_its_own_provenance(tmp_path: Path) -> None:
    """End to end at this phase: snapshot taken, sources digested, club resolved.

    The one KNOWN-RED assertion sits **last** on purpose. Put anywhere earlier it aborts
    the test at the Phase 5 gap, and every genuine end-to-end check below it stops running
    — so a real regression in snapshotting or digesting would hide behind a failure
    everyone had already agreed to ignore.
    """
    settings = _settings()
    if settings.probe_save is None:
        pytest.skip("OOTP_PROBE_LEAGUE is unset — the managed league is not a test target")

    run = ingest_save(settings.probe_save, settings=replace(settings, snapshot_root=tmp_path))

    assert run.save_id == settings.probe_save.save_id
    assert run.ingest_seq == 1
    assert run.snapshot.sim_date == run.sim_date
    assert {source.name for source in run.sources} == {entry.name for entry in run.snapshot.files}
    assert all(source.version == 25 for source in run.sources)
    assert run.parse_seconds is None, "Phase 9 fills this, not Phase 4"
    assert run.row_counts == {} and run.residual_bytes == {}

    assert run.human_team_id is not None, (
        "KNOWN RED until Phase 5 — the id comes from a flag on the team record in "
        "teams.dat, not from the saved-games index. Everything above this line passed, "
        "so this is the known gap rather than a regression."
    )
