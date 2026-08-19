"""AC7 — Tier B. Every resolved name matched against the probe save's export.

This is the strong half of the names validation and the only one that can be exact,
because the standard-mode probe is the one save with an export (ADR 0003). The claim is
narrow and absolute: **every** name index the parser resolves out of `players.dat`
matches `ootp_truth_real.players` by exact string equality, on 100% of compared rows,
with zero unresolved indices and every failure named.

Two anti-vacuity rules from the plan's §4.2/§4.3 govern this module.

**No aggregate pass rate.** A parser reading the adjacent `u32` would score 0.01% here
and a parser reading a stale table would score 99%; both are equally wrong and both must
name what disagreed. Every assertion below enumerates.

**A vacuous green is worse than a red.** If the export is unreachable this module skips
with a named reason rather than passing. `test_the_skip_path_names_its_reason` proves the
skip works, because a skip nobody has seen fire is as unverified as a guard nobody has
seen fail.

**Comparison happens in Python on decoded `str` (SD-13).** `ops/mysql-bootstrap.sql`
creates every schema `utf8mb4_0900_ai_ci` — accent- **and** case-insensitive — so
`WHERE a = b` in SQL scores `Ramirez == Ramírez` as a match, in a repo whose own export
doc turns *Replace accents* Off precisely to keep names comparable. Both sides are
fetched and compared here; nothing is compared server-side.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.db import connect_truth
from ootp_ai.parser.names import NAMES_FILE, NameTable, build_name_table
from ootp_ai.parser.players import PLAYERS_FILE, read_players

pytestmark = pytest.mark.gamedata

#: `retired = 0` rows in the export. The same population every other Tier-B test uses.
TRUTH_ACTIVE_PLAYERS = 18_072

#: Entries in the string table, in all three saves. The header declares it and the walk
#: frames exactly that many.
NAME_TABLE_ENTRIES = 264_095

#: How many indices are used as a first name by one player and a last name by another.
#: `measured` on the probe save — and the single clearest evidence that the table is ONE
#: index space rather than two. Under two spaces these indices would mean different
#: strings in each role, and both readings could not be correct at once.
INDICES_USED_IN_BOTH_ROLES = 510

#: What the REJECTED slot assignment scores — `measured`, exactly 1 of 18,072, a player
#: whose two name indices happen to resolve symmetrically. Pinned at the measured value
#: rather than at a percentage floor: a 1%-of-population bound would tolerate 180 matches
#: and quietly accept a reading that had started to work, which is the one thing the
#: negative control exists to notice.
SWAPPED_SLOT_MATCHES = 1


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"save configuration unavailable: {exc}")


def _probe(settings: Settings) -> SaveRef:
    """The standard-mode save. Tier B exists only here and that is permanent."""
    if settings.truth_save is None:
        pytest.skip(
            "OOTP_TRUTH_LEAGUE is unset, so the standard-mode probe — the only save with "
            "an export, and therefore the only exact answer key for names — is not "
            "available. Skipping rather than passing: AC7 is unproven, not satisfied."
        )
    return settings.truth_save


@contextmanager
def _truth_cursor(settings: Settings) -> Iterator[Any]:
    try:
        connection = connect_truth(settings)
    except ConfigError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(
            f"ground-truth export unavailable ({exc}), so the names join has no answer "
            "key. AC7 is unproven, not satisfied."
        )
    try:
        with connection.cursor() as cursor:
            yield cursor
    finally:
        connection.close()


def _table(save: SaveRef) -> NameTable:
    path = save.path / NAMES_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {NAMES_FILE} on this machine")
    return build_name_table(save.save_id, path.read_bytes())


def _players(save: SaveRef) -> dict[int, tuple[int, int]]:
    path = save.path / PLAYERS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {PLAYERS_FILE} on this machine")
    return {
        player.player_id: (player.first_name_index, player.last_name_index)
        for player in read_players(path.read_bytes()).players
    }


def _export_names(settings: Settings) -> dict[int, tuple[str, str]]:
    """The answer key, fetched whole. No comparison happens server-side (SD-13)."""
    with _truth_cursor(settings) as cursor:
        cursor.execute("SELECT player_id, first_name, last_name FROM players WHERE retired = 0")
        rows = cursor.fetchall()
    return {int(row["player_id"]): (row["first_name"], row["last_name"]) for row in rows}


def test_the_answer_key_is_the_population_every_other_tier_b_test_uses() -> None:
    """Guards against a silently narrowed key making the join look easy."""
    settings = _settings()
    assert len(_export_names(settings)) == TRUTH_ACTIVE_PLAYERS


def test_the_name_table_is_whole_and_singly_indexed() -> None:
    """The walk's own account of the table, before anything joins against it."""
    table = _table(_probe(_settings()))

    assert len(table.entries) == NAME_TABLE_ENTRIES
    assert min(table.entries) == 1
    assert max(table.entries) == NAME_TABLE_ENTRIES, (
        "the indices do not run 1..N without a gap, which is what a second index space "
        "sharing the file would look like"
    )
    assert all(text for text in table.entries.values()), "an entry resolved to an empty string"


def test_every_name_index_resolves() -> None:
    """Zero unresolved indices — AC7's second clause, and a precondition for the first.

    An unresolved index is not a near miss. It means the player walk read a `u32` that
    is not an index at all, and every name derived from that position is arbitrary.
    """
    settings = _settings()
    probe = _probe(settings)
    table = _table(probe)
    players = _players(probe)
    export = _export_names(settings)

    unresolved = [
        f"player {player_id}: first={first} last={last}"
        for player_id, (first, last) in players.items()
        if player_id in export and (first not in table.entries or last not in table.entries)
    ]
    assert not unresolved, (
        f"{len(unresolved)} of {len(export)} players point at an index the "
        f"{len(table.entries):,}-entry table does not hold:\n" + "\n".join(unresolved[:20])
    )


def test_every_resolved_name_matches_the_export_exactly() -> None:
    """AC7. Exact string equality, 100% of compared rows, every failure named.

    Compared in Python on decoded `str`. Doing this in SQL under the schema's
    `utf8mb4_0900_ai_ci` collation would score `Ramírez == Ramirez` as a match and this
    test would pass while the parser mangled every accented name in the league.
    """
    settings = _settings()
    probe = _probe(settings)
    table = _table(probe)
    players = _players(probe)
    export = _export_names(settings)

    compared = sorted(set(players) & set(export))
    assert len(compared) == TRUTH_ACTIVE_PLAYERS, (
        f"only {len(compared)} of {TRUTH_ACTIVE_PLAYERS} export players were framed by the "
        "walk, so a green below would cover a population somebody quietly narrowed"
    )

    failures: list[str] = []
    for player_id in compared:
        first_index, last_index = players[player_id]
        got = (table.resolve(first_index), table.resolve(last_index))
        want = export[player_id]
        if got != want:
            failures.append(
                f"player {player_id}: export {want!r} vs resolved {got!r} "
                f"(indices {first_index}, {last_index})"
            )

    assert not failures, (
        f"{len(failures)} of {len(compared)} names disagree with the export. Listed by "
        "player, never as a rate — an aggregate is how a parser reading the adjacent u32 "
        "ships green:\n" + "\n".join(failures[:25])
    )


def test_the_opposite_slot_assignment_is_refuted_not_merely_unchosen() -> None:
    """The brute force, re-run as an assertion rather than left in a handoff.

    `+4 as first, +8 as last` is only meaningful as a finding if the alternative is
    *measured to be wrong* here, in the suite, on every run. A swap in `players.py`
    would otherwise turn `test_every_resolved_name_matches_the_export_exactly` red with
    no indication that the reversed reading had ever been considered.
    """
    settings = _settings()
    probe = _probe(settings)
    table = _table(probe)
    players = _players(probe)
    export = _export_names(settings)

    compared = sorted(set(players) & set(export))
    swapped = sum(
        1
        for player_id in compared
        if (table.resolve(players[player_id][1]), table.resolve(players[player_id][0]))
        == export[player_id]
    )
    assert swapped <= SWAPPED_SLOT_MATCHES, (
        f"reading +8 as the first name and +4 as the last scores {swapped}/{len(compared)}, "
        f"above the measured {SWAPPED_SLOT_MATCHES}. The two readings are supposed to be "
        "separated by three orders of magnitude; if the wrong one starts scoring, this "
        "test can no longer tell them apart and the field map's `verified` label on both "
        "indices is unearned."
    )


def test_one_index_space_carries_both_roles() -> None:
    """The measurement behind the `name_space` decision, pinned so it cannot drift.

    Phase 8 keys `bronze_name` on `(save_id, sim_date, ingest_seq, name_space,
    name_index)` with `name_space` taking one literal value. That is only correct
    because the indices form a single space — and this is the evidence: hundreds of
    indices serve as a first name for one player and a last name for another, resolving
    correctly through the *same* table in both roles.
    """
    settings = _settings()
    probe = _probe(settings)
    players = _players(probe)
    export = _export_names(settings)

    compared = set(players) & set(export)
    firsts = {players[player_id][0] for player_id in compared}
    lasts = {players[player_id][1] for player_id in compared}

    assert len(firsts & lasts) == INDICES_USED_IN_BOTH_ROLES, (
        f"{len(firsts & lasts)} indices serve both roles, not {INDICES_USED_IN_BOTH_ROLES}. "
        "This number is the one-index-space finding; if it moved, re-derive the key-space "
        "question before trusting bronze_name's key."
    )


def test_the_comparison_is_accent_sensitive_which_sql_would_not_be() -> None:
    """SD-13, asserted rather than argued in a docstring.

    The module's whole collation position is that comparing in SQL would score
    `Ramirez == Ramírez` as equal under the schema's `utf8mb4_0900_ai_ci`, so both sides
    are fetched and compared in Python. That was prose; nothing stopped a later refactor
    from pushing the comparison back into a `WHERE` clause and turning every assertion
    above vacuous for exactly the names most likely to be mis-decoded.

    This pins the two properties that make the Python comparison meaningful — it is
    accent-sensitive and case-sensitive — and confirms the population it matters for is
    non-empty, so the check cannot pass on a table that happens to hold no accents.
    """
    settings = _settings()
    probe = _probe(settings)
    table = _table(probe)
    players = _players(probe)
    export = _export_names(settings)

    accented = [
        player_id
        for player_id in set(players) & set(export)
        if any(ord(character) > 127 for name in export[player_id] for character in name)
    ]
    assert accented, (
        "no exported name carries a character above ASCII, so this save cannot "
        "demonstrate the collation hazard and the SD-13 argument is untestable here"
    )

    for player_id in accented:
        first_index, last_index = players[player_id]
        resolved = (table.resolve(first_index), table.resolve(last_index))
        assert resolved == export[player_id], (
            f"player {player_id}: an accented name did not survive the round trip — "
            f"export {export[player_id]!r} vs resolved {resolved!r}"
        )

    # The hazard itself: strip the accents from one side and the comparison this module
    # performs must now FAIL. An accent-insensitive collation would call these equal, so
    # if this assertion ever passes, the comparison has moved somewhere it must not be.
    sample = export[accented[0]]
    stripped = tuple(
        "".join(character for character in name if ord(character) < 128) for name in sample
    )
    assert stripped != sample, "the sample lost its accents before the comparison began"
    assert not any(
        (table.resolve(players[player_id][0]), table.resolve(players[player_id][1])) == stripped
        for player_id in accented
    ), (
        "an accent-stripped name compared equal to a resolved one, which means the "
        "comparison is not the accent-sensitive Python `==` this module depends on"
    )


def test_the_skip_path_names_its_reason() -> None:
    """A guard nobody has seen fire is decoration — so fire it.

    `_truth_cursor` is the thing standing between "AC7 passed" and "AC7 was never run".
    This drives it with the truth database unset and requires an `ootp_ai` `ConfigError`
    to become a *skip*, not a pass and not an unrelated exception.
    """
    settings = _settings()
    blinded = Settings(
        install=settings.install,
        saved_games=settings.saved_games,
        managed=settings.managed,
        truth_save=settings.truth_save,
        probe_save=settings.probe_save,
        snapshot_root=settings.snapshot_root,
        output_root=settings.output_root,
        mysql=type(settings.mysql)(
            host=settings.mysql.host,
            port=settings.mysql.port,
            user=settings.mysql.user,
            password=settings.mysql.password,
            database=settings.mysql.database,
            truth_database=None,
        ),
    )

    with pytest.raises(BaseException) as caught:
        with _truth_cursor(blinded):
            pass  # pragma: no cover - the context manager never yields here

    assert caught.typename == "Skipped", (
        f"an unreachable ground-truth export raised {caught.typename}, not a skip. It "
        "must skip loudly: a pass here would report AC7 green having compared nothing."
    )
    assert "MYSQL_TRUTH_REAL_DATABASE" in str(caught.value), (
        "the skip does not name what is missing, so a reader sees a green-with-skips run "
        "and cannot tell which answer key was absent"
    )
