"""AC12 — how much of each file the walk actually accounted for, per file, per tier.

Byte accounting is the only correctness check that works on fields with **no ground
truth at all**, which is most of a 4.5 MB team record. It answers a narrow question
honestly: did the walk consume the file exactly, or did it stop somewhere and leave
bytes behind? A walk that ends where the file ends has had every one of its width
assumptions checked by the file itself — a wrong width anywhere desynchronises the very
next length prefix and raises, rather than returning a plausible wrong value.

**Three pre-registered tiers, and the choice is not the test's to make.**

* `strict` — zero residual bytes. Every width is confirmed by the walk reaching the end.
* `diagnostic` — the residual is *recorded* and the walk is asserted to stop on a record
  boundary, with a written rationale for the demotion.
* `region-accounted` — added 2026-08-16 (operator-disposed) for `world.dat`, which fits
  neither: a landmark-entered walk of a single-record 8.9 MB file never reads ~7.5 MB of
  it. Zero residual *within* each walked region, the region's own declared count matched,
  and the un-walked prefix and suffix recorded rather than waved at. It is a weaker claim
  than `diagnostic` and has its own name so that it cannot be mistaken for one.

`parser/teams.py` declares which one it reached. This module holds that declaration to
what the real files do, in both directions: a `strict` claim must survive zero-residual
on every configured save, and a `diagnostic` claim that in fact achieves zero residual
everywhere is an **under-claim** and fails too. Under-claiming is the cheaper mistake to
make and the harder one to notice, because it never turns anything red.

Scope note: this module covers `teams.dat` only. `names.dat` joins it at the strict tier
in Phase 7; `players.dat` joins at the diagnostic tier in Phase 6, where the scope is
explicit that full accounting over 32 MB is a research task rather than a counter.

`gamedata`: needs the saves. Excluded from CI.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.parser.teams import BYTE_ACCOUNTING_TIER, TEAMS_FILE, TeamsFile, read_teams

pytestmark = pytest.mark.gamedata

#: Measured from the export, 2026-08-16: `SELECT COUNT(*) FROM teams` on the
#: standard-mode save's ground truth. The one save where an independent count exists.
TRUTH_TEAM_COUNT = 259

#: The top league holds 30 clubs plus four All-Star sides. Any league file holding
#: fewer records than the clubs of its own top division is short, whatever else is true.
MINIMUM_PLAUSIBLE_TEAMS = 30


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
