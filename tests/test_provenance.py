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

    **`human_team_id` was removed here in Phase 5, and its absence is the finding.**
    Phase 4 carried it as `None` on every entry, which read as structural absence — a
    field the record has, holding nothing. It is not that. The index has no team id at
    all: every numeric slot in all three records was enumerated at u8/u16/u32 against
    ground truth and none of them held one. A field that is `None` by construction on
    every input invites the next reader to believe the index might one day supply it.
    The id comes from `teams.dat` and nowhere else.

    `human_team_name` stays, because it is real and because it is an independent
    statement of which club the team flag should be pointing at. Measured: it is the
    club's **full name** (`'Boston Red Sox'`, `'Chicago Cubs'`), so it identifies the
    club unambiguously — but it remains a **cross-check, never a join key**, because
    joining on a display name across two universes is what `team_id` exists to avoid.
    """
    assert _field_names(SavedGameEntry) == {
        "league",
        "sim_date",
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
    """The control that works from the index alone: two Bostons and a Chicago.

    Measured: the index carries full club names — `'Boston Red Sox'`, `'Chicago Cubs'`.
    That is enough to prove the walk reaches the right region of the record, and enough
    to name the club, but it is **not an id**, which is what every downstream row is
    keyed on. `tests/test_parse_real_save.py` resolves the id from `human_managers.dat`
    and `teams.dat` and holds all three sources against each other.
    """
    names = [entry.human_team_name for entry in _all_three(_settings())]

    assert all(names), f"a human club failed to resolve: {names}"
    assert len(set(names)) > 1, (
        f"all three saves resolved to {names[0]!r} — the standard-mode save is managed "
        "by the Chicago Cubs and the other two by Boston, so a single value means the "
        "field is hardcoded or the walk is reading the wrong region"
    )


#: The human team **id** is asserted in `tests/test_parse_real_save.py`, not here.
#: Phase 4 kept a known-red assertion at this spot, on the theory that the index would
#: eventually yield an id. It does not, and the walk that does — `teams.dat`'s human
#: flag — belongs with the rest of the team-dimension checks rather than in a module
#: about the saved-games index. What remains here is the display-name control below,
#: which is the index's own contribution to the same question.


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
    """End to end: snapshot taken, sources digested, club resolved from the data.

    The club assertion sits **last** deliberately, and stays there now that it passes.
    While it was the Phase 4 known-red, putting it earlier would have aborted the test at
    the known gap and stopped every genuine end-to-end check below it from running — a
    real regression in snapshotting or digesting would have hidden behind a failure
    everyone had agreed to ignore. The ordering costs nothing and keeps that property if
    a later phase ever adds another gap here.
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
        "the run resolved no human club. The id comes from the human flag on a record "
        "in the snapshot's teams.dat — if the walk found no flagged club, the ingest "
        "cannot say which organisation it is reporting on."
    )
    assert run.human_team_id > 0, "team ids run from 1; zero is 'no team', not a club"
