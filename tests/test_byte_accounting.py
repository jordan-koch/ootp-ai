"""AC12 — how much of each file the walk actually accounted for, per file, per tier.

Byte accounting is the only correctness check that works on fields with **no ground
truth at all**, which is most of a 4.5 MB team record. It answers a narrow question
honestly: did the walk consume the file exactly, or did it stop somewhere and leave
bytes behind? A walk that ends where the file ends has had every one of its width
assumptions checked by the file itself — a wrong width anywhere desynchronises the very
next length prefix and raises, rather than returning a plausible wrong value.

**The tiers are pre-registered, and the choice is not the test's to make.**
`tests/fixtures/tiers.py` owns the vocabulary and explains what each one claims; each
walker declares which one it reached.

This module holds those declarations to what the real files do, **in both directions**: a
`strict` claim must survive zero-residual on every configured save, and a `diagnostic`
claim that in fact achieves zero residual everywhere is an **under-claim** and fails too.
Under-claiming is the cheaper mistake to make and the harder one to notice, because it
never turns anything red.

Scope note: this module covers `teams.dat` (diagnostic), `world.dat` (region-accounted,
Phase 5b), `players.dat` (diagnostic, Phase 6 — the scope is explicit that full accounting
over 32 MB is a research task rather than a counter) and, since Phase 7, `names.dat` at
the **strict** tier. `names.dat` is the only one that reaches strict, and the reason is
the file's rather than the walk's: a name record has no undecoded body.

`world.dat` is the one that needs its own section rather than another helper, because
"residual" is not the question there. A landmark-entered walk never reads most of the
file, so what can be audited from outside is an **identity**: every byte of the file is
either inside a region the walk claims to have accounted for, or in the un-walked
remainder it reports. Anything that satisfies that identity has nowhere to hide a byte it
quietly skipped inside a region it claimed.

`gamedata`: needs the saves. Excluded from CI.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fixtures.tiers import KNOWN_TIERS
from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.parser.names import BYTE_ACCOUNTING_TIER as NAMES_TIER
from ootp_ai.parser.names import NAMES_FILE, NamesFile, read_names
from ootp_ai.parser.players import BYTE_ACCOUNTING_TIER as PLAYERS_TIER
from ootp_ai.parser.players import PLAYERS_FILE, PlayersFile, read_players
from ootp_ai.parser.teams import BYTE_ACCOUNTING_TIER, TEAMS_FILE, TeamsFile, read_teams
from ootp_ai.parser.world import BYTE_ACCOUNTING_TIER as WORLD_TIER
from ootp_ai.parser.world import WORLD_FILE, WorldFile, read_world

pytestmark = pytest.mark.gamedata

#: Measured from the export, 2026-08-16: `SELECT COUNT(*) FROM teams` on the
#: standard-mode save's ground truth. The one save where an independent count exists.
TRUTH_TEAM_COUNT = 259

#: The top league holds 30 clubs plus four All-Star sides. Any league file holding
#: fewer records than the clubs of its own top division is short, whatever else is true.
MINIMUM_PLAUSIBLE_TEAMS = 30

#: `measured` 2026-08-17 on the standard-mode save. 18,072 is the export's `retired = 0`
#: count; the file carries five more records that the export does not know about at all,
#: so the file total and the export total are deliberately two different constants.
TRUTH_ACTIVE_PLAYERS = 18_072
TRUTH_PLAYER_RECORDS = 18_077

#: Thirty clubs at 26 active apiece is 780 before a single affiliate. A file returning
#: fewer records than that is short however plausible the ones it did return look.
MINIMUM_PLAUSIBLE_PLAYERS = 780

#: `measured` 2026-08-18 — the count `names.dat`'s header declares, and the number of
#: records the walk frames, in all three saves. The one file in the save whose declared
#: count and framed count can be compared to each other.
NAME_TABLE_ENTRIES = 264_095


@dataclass(frozen=True, slots=True)
class Walked:
    """One save's walk, with the file size the residual has to be judged against."""

    league: str
    parsed: TeamsFile
    file_bytes: int

    @property
    def mean_record_bytes(self) -> float:
        return (self.file_bytes - self.parsed.residual_bytes) / len(self.parsed.teams)


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings: {exc}")


def _walk(save: SaveRef) -> Walked:
    path = save.path / TEAMS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {TEAMS_FILE} — nothing to account for")
    payload = path.read_bytes()
    return Walked(league=save.league, parsed=read_teams(payload), file_bytes=len(payload))


def _every_save(settings: Settings) -> list[Walked]:
    """All configured saves, named. Skips loudly rather than testing one universe."""
    present = [ref for ref in (settings.managed, settings.probe_save, settings.truth_save) if ref]
    if len(present) < 2:
        pytest.skip(
            "fewer than two saves are configured; byte accounting against a single "
            "file cannot distinguish a correct walk from one tuned to that file"
        )
    return [_walk(ref) for ref in present]


# ── the tier, held to what the files do ──────────────────────────────────────


def test_the_walk_accounts_for_every_byte_when_it_claims_to() -> None:
    """The strict tier's whole content. Nothing to interpret: zero, or red."""
    if BYTE_ACCOUNTING_TIER != "strict":
        pytest.skip(f"the teams walk is declared {BYTE_ACCOUNTING_TIER!r}, not strict")

    for walked in _every_save(_settings()):
        assert walked.parsed.residual_bytes == 0, (
            f"{walked.league}: the walk claims the strict tier but left "
            f"{walked.parsed.residual_bytes} bytes unaccounted after "
            f"{len(walked.parsed.teams)} teams. Either fix the widths or demote the "
            "declaration with a rationale — a strict claim that is not true is worse "
            "than an honest diagnostic one."
        )


def test_a_diagnostic_claim_is_not_an_under_claim() -> None:
    """Closes the escape hatch: declare `diagnostic`, achieve zero, assert nothing.

    A tier is a statement about the file, not a difficulty setting. If every configured
    save walks to exhaustion, the strict tier was reached and the declaration should say
    so — otherwise the next reader inherits a warning about a problem that no longer
    exists, and stops believing the tier labels.
    """
    if BYTE_ACCOUNTING_TIER != "diagnostic":
        pytest.skip("the teams walk already claims the strict tier")

    residuals = {walked.league: walked.parsed.residual_bytes for walked in _every_save(_settings())}
    assert any(value > 0 for value in residuals.values()), (
        f"every save walked to zero residual ({residuals}) while the module still "
        "declares the diagnostic tier. Promote the declaration to `strict` and delete "
        "the rationale."
    )


def test_the_walk_stops_on_a_record_boundary_even_when_it_leaves_bytes() -> None:
    """The diagnostic tier's real assertion, and the one that makes it worth having.

    A residual smaller than one record means the walk consumed whole teams and ran out
    of file — a trailing region it has not classified. A residual *larger* than a record
    means it stopped mid-league with whole teams left unread, which is a different and
    much worse failure: the league is silently short, and a count is the only thing that
    would ever show it.
    """
    for walked in _every_save(_settings()):
        assert walked.parsed.teams, f"{walked.league}: the walk returned no teams at all"
        assert walked.parsed.residual_bytes < walked.mean_record_bytes, (
            f"{walked.league}: {walked.parsed.residual_bytes} bytes remain, which "
            f"exceeds the ~{walked.mean_record_bytes:.0f}-byte mean record — the walk "
            "stopped with whole teams unread, so the league it returned is short."
        )


# ── the independent count ────────────────────────────────────────────────────


def test_the_team_count_matches_the_export_on_the_only_save_that_has_one() -> None:
    """259 teams, from a source that is not this parser.

    Challenge Mode has no export (ADR 0003), so this check exists on exactly one save.
    That is the whole reason the standard-mode probe is retained.
    """
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("OOTP_TRUTH_LEAGUE is unset — no save with an independent count")

    walked = _walk(settings.truth_save)
    assert len(walked.parsed.teams) == TRUTH_TEAM_COUNT, (
        f"walked {len(walked.parsed.teams)} teams; the export says {TRUTH_TEAM_COUNT}. "
        "A count that is close but wrong is the signature of a width error rather than "
        "of a missing league — read the residual before touching the field map."
    )


def test_the_managed_league_count_degrades_honestly_without_an_export() -> None:
    """`OOTP-AI.lg` has no answer key, so say what is actually being claimed.

    What survives is structural: the walk returns a plausible league rather than a
    handful of records, and it returns the same one twice. This is deliberately weak,
    and the weakness is the point — asserting 259 here would assert that two
    independently created universes have identical shape, which nothing has checked.
    """
    settings = _settings()
    walked = _walk(settings.managed)
    assert len(walked.parsed.teams) >= MINIMUM_PLAUSIBLE_TEAMS, (
        f"{settings.managed.league} walked {len(walked.parsed.teams)} teams — fewer "
        f"than the {MINIMUM_PLAUSIBLE_TEAMS} clubs the top league alone must hold"
    )

    again = _walk(settings.managed)
    assert len(again.parsed.teams) == len(walked.parsed.teams)
    assert again.parsed.residual_bytes == walked.parsed.residual_bytes, (
        "two walks of the same unchanged file disagreed about the residual, so the "
        "walker is carrying state between calls"
    )


# ── world.dat, at the region-accounted tier ──────────────────────────────────


@dataclass(frozen=True, slots=True)
class WalkedWorld:
    """One save's world walk, with the size the accounting identity is checked against.

    `file_bytes` is read from disk here rather than taken from the parser's own report,
    and the first assertion below is that the two agree. A walker that supplies both
    halves of an identity can satisfy it while being wrong about the file.
    """

    league: str
    parsed: WorldFile
    file_bytes: int

    @property
    def walked_bytes(self) -> int:
        return sum(region.length for region in self.parsed.regions)

    @property
    def unwalked_bytes(self) -> int:
        return self.file_bytes - self.walked_bytes

    @property
    def prefix_bytes(self) -> int:
        """Everything before the first region — the header, the world settings, ~94k cities."""
        return min(region.entered_at for region in self.parsed.regions)

    @property
    def suffix_bytes(self) -> int:
        """Everything after the last region — the ~1.9 MB of high schools and colleges."""
        end = max(region.entered_at + region.length for region in self.parsed.regions)
        return self.file_bytes - end


def _walk_world(save: SaveRef) -> WalkedWorld:
    path = save.path / WORLD_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {WORLD_FILE} — nothing to account for")
    payload = path.read_bytes()
    return WalkedWorld(league=save.league, parsed=read_world(payload), file_bytes=len(payload))


def _every_world(settings: Settings) -> list[WalkedWorld]:
    present = [ref for ref in (settings.managed, settings.probe_save, settings.truth_save) if ref]
    if len(present) < 2:
        pytest.skip("fewer than two saves are configured")
    return [_walk_world(ref) for ref in present]


def test_the_world_walk_agrees_with_the_filesystem_about_the_size_of_the_file() -> None:
    """The identity's outside anchor, asserted before anything is derived from it."""
    for walked in _every_world(_settings()):
        assert walked.parsed.file_bytes == walked.file_bytes, (
            f"{walked.league}: the walk reports a {walked.parsed.file_bytes}-byte "
            f"{WORLD_FILE} and the file is {walked.file_bytes} bytes. Every number below "
            "is derived from this one, so nothing else here means anything until it agrees."
        )


def test_every_byte_is_either_inside_a_walked_region_or_reported_as_un_walked() -> None:
    """What `region-accounted` actually asserts, and the only form it can be asserted in.

    Zero-residual is unavailable — the walk never reads ~7.5 MB of an 8.9 MB file, by
    design. What is available is the accounting identity: regions are ordered, they do
    not overlap, they sit inside the file, and what they cover plus what is reported
    un-walked is the file exactly. A region whose declared length exceeded what it really
    consumed would show up as an overlap with the next one, or as a suffix that runs past
    the end of the file.
    """
    for walked in _every_world(_settings()):
        regions = walked.parsed.regions
        assert regions, f"{walked.league}: no regions were walked at all"

        cursor = 0
        for region in regions:
            assert region.entered_at >= cursor, (
                f"{walked.league}: region {region.name!r} starts at {region.entered_at}, "
                f"inside or before the previous region which ended at {cursor}. Two "
                "regions claiming the same bytes means one of the lengths is wrong."
            )
            assert region.length > 0
            cursor = region.entered_at + region.length

        assert cursor <= walked.file_bytes, (
            f"{walked.league}: the regions run {cursor - walked.file_bytes} bytes past "
            "the end of the file"
        )
        assert walked.walked_bytes + walked.unwalked_bytes == walked.file_bytes


def test_a_region_accounted_claim_is_not_an_under_claim_either() -> None:
    """Same escape hatch the diagnostic tier has, closed the same way.

    `region-accounted` is the weakest claim this project makes, so it is the most
    comfortable place to park. If a walk in fact covered the whole file it reached a
    stronger tier and the declaration should say so — otherwise the next reader inherits a
    warning about a limitation that no longer exists and stops believing the labels.
    """
    if WORLD_TIER != "region-accounted":
        pytest.skip(f"the world walk is declared {WORLD_TIER!r}")

    for walked in _every_world(_settings()):
        assert walked.unwalked_bytes > 0, (
            f"{walked.league}: the walk covered all {walked.file_bytes} bytes of "
            f"{WORLD_FILE} while still declaring the region-accounted tier. Promote it."
        )


def test_the_un_walked_prefix_and_suffix_are_recorded_rather_than_waved_at() -> None:
    """The plan's wording, made checkable: *un-walked prefix and suffix byte counts recorded*.

    Both are large and both are expected — ~62% of the file precedes the leagues region
    and ~1.9 MB of schools follows the calendar. The point is not that they are small. It
    is that a number exists for each, so the ingest row can carry it and a later reader
    can see exactly how much of this file has never been read by anything.
    """
    if WORLD_TIER != "region-accounted":
        pytest.skip(f"the world walk is declared {WORLD_TIER!r}")

    for walked in _every_world(_settings()):
        assert walked.prefix_bytes > 0, (
            f"{walked.league}: the first region starts at byte 0, which would mean the "
            "walk began before the header it is required to validate"
        )
        assert walked.suffix_bytes > 0, (
            f"{walked.league}: nothing follows the last walked region. Measured, ~1.9 MB "
            "of high schools and colleges does — a zero suffix means the last region's "
            "length is being computed as 'everything left', which accounts for nothing."
        )


# ── players.dat, whose accounting is weaker and has to say so ────────────────


@dataclass(frozen=True, slots=True)
class WalkedPlayers:
    """One save's player walk, with the file size the residual is judged against."""

    league: str
    parsed: PlayersFile
    file_bytes: int

    @property
    def mean_record_bytes(self) -> float:
        return (self.file_bytes - self.parsed.residual_bytes) / len(self.parsed.players)


def _walk_players(save: SaveRef) -> WalkedPlayers:
    path = save.path / PLAYERS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {PLAYERS_FILE} — nothing to account for")
    payload = path.read_bytes()
    return WalkedPlayers(league=save.league, parsed=read_players(payload), file_bytes=len(payload))


def _every_player_walk(settings: Settings) -> list[WalkedPlayers]:
    present = [ref for ref in (settings.managed, settings.probe_save, settings.truth_save) if ref]
    if len(present) < 2:
        pytest.skip("fewer than two saves are configured")
    return [_walk_players(ref) for ref in present]


def test_the_player_walk_consumes_essentially_the_whole_file() -> None:
    """The diagnostic tier's real assertion for this file, bounded as a *fraction*.

    **An earlier version compared the residual against the MEAN record and it was wrong
    in both directions.** Measured: the residual is 1,045 bytes against a 1,543-byte mean
    — but records run to 9,229 bytes, so a save whose *last* record happens to be a long
    one leaves more than the mean behind on a completely correct walk and goes red. And
    in the other direction, a walk that truncated near the end of the file leaves less
    than one mean record and passes. A bound that can fail on correct data and pass on
    broken data is worse than no bound.

    A fraction of the file has neither failure. The measured residuals are ~0.004% of
    their files; a walk that stopped anywhere but the end leaves whole percentage points.
    The threshold below is three orders of magnitude above what is observed and still
    catches a walk that quit halfway, which is the failure that matters when — as here —
    there is no declared record count to check against.
    """
    for walked in _every_player_walk(_settings()):
        assert walked.parsed.players, f"{walked.league}: the walk returned no players"
        unread = walked.parsed.residual_bytes / walked.file_bytes
        assert unread < 0.001, (
            f"{walked.league}: {walked.parsed.residual_bytes:,} bytes remain unread of "
            f"{walked.file_bytes:,} ({unread:.3%}). The walk stopped short of the end of "
            "the file, so it is returning fewer players than the file holds — and this "
            "file declares no record count, so nothing else would catch it."
        )


def test_the_player_walk_declares_the_weaker_tier_honestly() -> None:
    """`diagnostic`, and it must not be an under-claim any more than the teams walk is."""
    assert PLAYERS_TIER == "diagnostic"
    residuals = {w.league: w.parsed.residual_bytes for w in _every_player_walk(_settings())}
    assert any(value > 0 for value in residuals.values()), (
        f"every save walked to zero residual ({residuals}) while the module still "
        "declares the diagnostic tier. Promote it and delete the rationale."
    )


def test_no_save_gives_the_player_walk_an_in_file_record_count() -> None:
    """Why this file's accounting is weaker than `teams.dat`'s, asserted rather than said.

    `teams.dat` declares its record count and the walk uses it as a loop bound, so a
    mis-framed file runs out of records and raises. `players.dat` declares `0xFFFFFFFF`.
    The moment that changes, this walk can be given a real oracle and the rationale is
    out of date — so the absence is pinned rather than assumed.
    """
    for walked in _every_player_walk(_settings()):
        assert walked.parsed.declared_record_count is None, (
            f"{walked.league}: {PLAYERS_FILE} now declares "
            f"{walked.parsed.declared_record_count} records. The walk has gained an "
            "in-file count it has never had; use it as a loop bound and revisit "
            "TIER_RATIONALE."
        )


def test_the_player_count_matches_the_export_where_one_exists() -> None:
    """The independent count, and the five records the export does not carry.

    `18,072` is the export's `retired = 0` population and `18,077` is what the file
    holds. The gap is not slack in the walk — the five extras are real records — so the
    assertion is on the exact total rather than on a tolerance.
    """
    settings = _settings()
    if settings.truth_save is None:
        pytest.skip("no standard-mode save configured; there is no export to compare to")
    walked = _walk_players(settings.truth_save)
    assert len(walked.parsed.players) == TRUTH_PLAYER_RECORDS, (
        f"{walked.league}: framed {len(walked.parsed.players)} records against the "
        f"measured {TRUTH_PLAYER_RECORDS} ({TRUTH_ACTIVE_PLAYERS} exported plus "
        f"{TRUTH_PLAYER_RECORDS - TRUTH_ACTIVE_PLAYERS} the export omits)"
    )


def test_the_managed_player_walk_degrades_honestly_without_an_export() -> None:
    """No export, no oracle — so the assertion is a floor, and it says why."""
    settings = _settings()
    walked = _walk_players(settings.managed)
    assert len(walked.parsed.players) > MINIMUM_PLAUSIBLE_PLAYERS, (
        f"{walked.league}: {len(walked.parsed.players)} records is fewer than a league "
        "of 30 clubs can field. There is no export for this save, so this floor and the "
        "record-boundary check are the only things standing between a short walk and a "
        "warehouse that quietly holds half a league."
    )


# ── names.dat, the strict tier, Phase 7 ──────────────────────────────────────
#
# The only walk in this project that reaches strict, and the reason it can is a property
# of the file rather than of the effort spent on it: a name record has no undecoded body.
# `teams.dat` and `players.dat` carry variable-length remainders this slice does not
# read, so both are honest about being diagnostic; here every byte is a field the walk
# consumes, and a wrong width desynchronises the next length prefix immediately.


def _walk_names(save: SaveRef) -> tuple[str, NamesFile, int]:
    path = save.path / NAMES_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {NAMES_FILE} — nothing to account for")
    payload = path.read_bytes()
    return save.league, read_names(payload), len(payload)


def _every_names_save(settings: Settings) -> list[tuple[str, NamesFile, int]]:
    present = [ref for ref in (settings.managed, settings.probe_save, settings.truth_save) if ref]
    if len(present) < 2:
        pytest.skip("fewer than two saves are configured")
    return [_walk_names(ref) for ref in present]


def test_the_names_tier_is_a_known_one() -> None:
    assert NAMES_TIER in KNOWN_TIERS


def test_the_names_walk_leaves_no_byte_unaccounted_for() -> None:
    """Strict means zero. Nothing to interpret and no residual to record.

    This is the assertion the tier label buys: `read_names` raises rather than returning
    a `NamesFile` with a residual, so reaching this line at all already means the walk
    consumed the buffer. Asserting it anyway keeps the claim visible at the place a
    reader looks for it, and catches a future walker that starts tolerating a remainder.
    """
    assert NAMES_TIER == "strict"

    for league, parsed, size in _every_names_save(_settings()):
        assert parsed.residual_bytes == 0, (
            f"{league}: {parsed.residual_bytes} of {size:,} bytes unaccounted for, in a "
            f"walk declared {NAMES_TIER!r}. Either the tier is wrong or a record carries "
            "a field this walk does not read."
        )


def test_the_names_walk_frames_exactly_the_count_the_file_declares() -> None:
    """The in-file oracle `players.dat` does not have, used as one.

    `players.dat` carries the `0xFFFFFFFF` sentinel, so its walk has nothing to check its
    own framing against and its rationale says so. This file declares a real count, which
    means the strict claim is checked against something other than itself: framing too
    few records and framing too many are both caught, in the file, on every save.
    """
    for league, parsed, _ in _every_names_save(_settings()):
        assert len(parsed.names) == parsed.declared_record_count, (
            f"{league}: framed {len(parsed.names):,} name records but the header declares "
            f"{parsed.declared_record_count:,}"
        )
        assert parsed.declared_record_count == NAME_TABLE_ENTRIES, (
            f"{league}: the table declares {parsed.declared_record_count:,} entries, not "
            f"{NAME_TABLE_ENTRIES:,}. A game patch may have shipped a different name "
            "master, which would change every index players.dat points with."
        )


def test_name_records_are_not_all_the_same_length() -> None:
    """Otherwise the file exercises none of the variable-length hazard.

    Two independent sources of width variation here — the length-prefixed name and the
    per-record usage array — and both must actually vary, or a fixed-stride reader would
    walk this file correctly and the strict result would prove nothing about the ban.
    """
    for league, parsed, _ in _every_names_save(_settings()):
        name_widths = {len(record.text) for record in parsed.names}
        usage_widths = {len(record.usage) for record in parsed.names}
        assert len(name_widths) > 1, f"{league}: every name is the same length"
        assert len(usage_widths) > 1, (
            f"{league}: every name record carries the same number of usage pairs, so the "
            "second source of width variation is not being read"
        )


# ── the premise byte accounting exists to protect ────────────────────────────


def test_team_records_are_not_all_the_same_length() -> None:
    """If they were, a fixed-offset reader would work and the whole ban would be moot.

    Measured as a **proxy**: the five signature strings are length-prefixed, so their
    combined width varies per team unless every club's name happens to be the same
    length. That variation is precisely the displacement a constant-offset read cannot
    survive — a reader calibrated on Arizona lands mid-field on San Francisco.
    """
    for walked in _every_save(_settings()):
        widths = {
            len(team.city or "") + len(team.abbr) + len(team.nickname) + len(team.full_name)
            for team in walked.parsed.teams
        }
        assert len(widths) > 1, (
            f"{walked.league}: every team's signature strings sum to the same width, so "
            "this file exercises none of the variable-length hazard. Either the walk is "
            "not reading the strings it thinks it is, or this check has gone vacuous."
        )
