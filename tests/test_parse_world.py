"""`world.dat` — the division hierarchy and the league calendar, and what a landmark owes.

Phase 5b reaches the two structures `teams.dat` turned out not to hold. It is the first
walk in this project that does **not** start at the top of a file, and that is the whole
reason this module is shaped the way it is.

## Why entry is a search and not a seek

`world.dat` declares `record_count = 1`. The single record is the world: settings, forty
languages, ~94,000 cities, the leagues, a 12,961-game schedule, the calendar, then ~1.9 MB
of high schools and colleges. The leagues sit ~62% in, behind the city array, so a
from-the-top walk means modelling ~94,000 records nothing consumes — its own phase, and
one Phase 5b explicitly defers.

The alternative is not a fixed offset. Offsets are banned outright and the ban is
structural: `parser/primitives.py`'s cursor has no `seek` and no position setter, and
`tests/test_no_fixed_offsets.py` scans the AST of every parser module. The walk enters at
a **composite landmark** — a length-prefixed string matched on its prefix *and* its
payload, `measured` unique in all three saves, where the bare payload alone is not
(`OPENING DAY` occurs 95 times) — and then walks sequentially forward.

**What makes that defensible rather than merely clever is that both target regions declare
their own count.** Read the count, consume exactly that many records, land on the next
region's boundary. A wrong record width desynchronises within the region and raises; a
wrong landing point fails the boundary check. The landmark buys entry; the region's own
declared count is what audits the walk after it.

## Why this module hand-builds a calendar record when Phase 5a refused to

`tests/test_parse_teams_synthetic.py` deliberately builds no `teams.dat` record: that
layout was the thing being measured in the phase, so a fixture would have asserted a guess
— green when the parser agreed with the guess and red when the parser was right.

The calendar is the opposite case. Its shape was measured **first**, against a full answer
key: all 3,058 entries decode against `ootp_truth_real.league_events` on all eight exported
columns. So the fixture here pins a finding, and the offline half of the region-accounting
claim — *zero residual within the walked region* — gets CI signal on every PR rather than
only on the one machine with a save. The division nest is **not** synthesised, because its
enclosing framing is what this phase is measuring; it is checked against the real files and
the export instead.

**Corrected 2026-08-16, mid-phase.** An earlier draft of this module recorded that the
calendar array is *byte-identical across all three saves*. It is not, and the correction
matters more than the number: the two probes are byte-identical to each other, and
`OOTP-AI.lg` differs in exactly **233 bytes, every one of them a `deleted` flag**. The
shipped calendar is common; which of its events have been deleted is per-universe state.
Any assertion written on the old belief would have pinned one universe's answer as a
property of the format.

## The one interface demand this module makes

`read_calendar(cursor)` must be reachable on its own, separately from `read_world`. The
landmark search cannot be exercised without an 8.9 MB file, but the record decoder can be
exercised with 40 bytes — and the decoder is where a width error lives. Keeping the seam
open is what converts the weakest tier this project declares into something CI can check.

`gamedata` marks only the half that needs the saves; everything above it runs in CI.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import get_type_hints

import pytest

from fixtures.synthetic import make_calendar, make_calendar_event, make_header
from fixtures.tiers import KNOWN_TIERS
from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.parser.errors import (
    MalformedHeader,
    SaveFilenameMismatch,
    SaveFormatError,
    UnsupportedSaveVersion,
)
from ootp_ai.parser.primitives import Cursor
from ootp_ai.parser.teams import TeamRecord
from ootp_ai.parser.world import (
    BYTE_ACCOUNTING_TIER,
    TIER_RATIONALE,
    WORLD_FILE,
    CalendarEvent,
    DivisionMembership,
    WorldFile,
    WorldRegion,
    read_calendar,
    read_world,
)

#: The two regions this phase exists to land, in the order the file gives them: the
#: leagues region (~62% in) carries the division nest, and the calendar sits after the
#: schedule. Both must be present and in this relative order.
REQUIRED_REGIONS = ("divisions", "calendar")

#: The whole permitted vocabulary — and it is exactly the required set, deliberately.
#:
#: A third value, `schedule`, was pre-registered here on the theory that the calendar
#: might only be reachable *through* the schedule: it declares its own count at a measured
#: 37 bytes per record, so `count * 37` is a width computed from the data and crossing it
#: would not be a seek. **The 37-byte stride does not reproduce.** Both probes give
#: `479,557 = 12,961 x 37` exactly; `OOTP-AI.lg` gives `622,233 = 16,817 x 37 + 4`. A
#: crossing that is exact in the two universes with an export and four bytes off in the
#: one without is the project's signature failure shape, so the walk uses the calendar's
#: own landmark instead and the value came back out of this set.
#:
#: A new name is a finding, not a failure — bring it to the main thread rather than
#: widening this set from inside a walker.
KNOWN_REGIONS = frozenset(REQUIRED_REGIONS)

#: `measured` 2026-08-16 — 3,058 entries in every save on disk, and the export agrees.
#: The *count* is universe-independent even though the contents are not.
CALENDAR_EVENTS = 3058

#: `measured` — how many of the 3,058 carry `deleted`, **per universe**, which is the
#: finding rather than an inconvenience. Both probes read 2,492 and the export confirms it
#: (`SELECT SUM(deleted <> 0) FROM league_events` → 2492). `OOTP-AI.lg` reads 2,259.
#:
#: An earlier draft of this module pinned a single 2,482 across all three saves and was
#: wrong twice: wrong by ten against the answer key, and wrong in *kind* about the managed
#: league, where 233 more events are still live. Pinning one universe's count as a
#: property of the format is exactly the mistake a two-save comparison exists to catch.
PROBE_DELETED_EVENTS = 2492
MANAGED_DELETED_EVENTS = 2259

#: `measured` — the two universes differ on exactly this many `deleted` flags and on
#: nothing else in the calendar. 2,492 - 2,259 = 233.
DELETED_DELTA = 233

#: `measured` — the human-readable key `(league_id, start_date, type, name)` collapses
#: 3,058 rows to 2,600. **458 events lost with nothing raised**, which is the entire
#: argument for keying the grain on `seq` instead. Pinned so the argument survives.
COLLAPSED_BY_READABLE_KEY = 2600

#: `measured` — live MLB events the game itself marks as requiring the human. This is the
#: field the phase exists for: the game's own answer to which dates the front office must
#: show up for, against ADR 0013's action economy answering it by judgment alone. Landed
#: here; **no doctrine is built on it in this phase.**
#:
#: Measured 2026-08-16, and the shape of the answer is why this is a *subset*: 112 events
#: carry the flag in every save, of which **three** survive undeleted in the probes and
#: **ten** in `OOTP-AI.lg` — the managed league still has live duplicates (three Trading
#: Deadlines, two Rule 5 Drafts). So the league we actually manage faces more of these
#: dates than the probe would suggest, which is a fact for the action economy to digest
#: later and a reason not to pin a total here.
HUMAN_ACTION_EVENTS = frozenset(
    {
        ("First-Year Player Draft", "2024-07-11"),
        ("Trading Deadline", "2024-07-31"),
        ("Rule 5 Draft", "2024-12-13"),
    }
)

#: `measured` — the flag's total, which *is* universe-independent: 112 in all three saves
#: and in the export. Only how many of them survive undeleted differs.
FLAGGED_EVENTS = 112

#: Names that would give the undocumented `event_type` enum a human meaning. The
#: semantics of the integer are not known, and `db_structure_ootp25_mysql.txt` documents
#: the column without documenting the enum — the same posture Phase 6 takes with
#: `list_id`. A wrong human label produces a confidently wrong calendar with nothing
#: thrown, so the label is not representable until somebody reads the game screen.
FORBIDDEN_LABEL_FIELDS = frozenset(
    {"type_name", "type_label", "event_label", "event_category", "event_kind", "kind"}
)


def _field_names(cls: type) -> frozenset[str]:
    assert is_dataclass(cls), f"{cls.__name__} is expected to be a dataclass"
    return frozenset(f.name for f in fields(cls))


# ── the shapes are decisions, not accidents ──────────────────────────────────


def test_the_module_names_the_file_it_reads() -> None:
    assert WORLD_FILE == "world.dat"


def test_a_calendar_event_carries_the_eight_columns_the_export_proved_and_its_key() -> None:
    """Nine fields: the eight the export validated, plus `seq`, which it never exposes.

    `seq` is the interesting one. It is not in the export at all, so it could only be
    found by reading the bytes — and it is the only field that is unique across all
    3,058 entries. The grain rests on it.
    """
    assert _field_names(CalendarEvent) == {
        "seq",
        "league_id",
        "event_type",
        "start_date",
        "name",
        "event_over",
        "deleted",
        "needs_human_action",
        "real_sim_date",
    }


def test_the_three_flag_bytes_land_as_integers_rather_than_booleans() -> None:
    """`bool(2)` is `True`, and that is the whole problem.

    The three flags are `u8` and every observed value is 0 or 1 — but *observed* is doing
    real work in that sentence, and a `bool` field makes an unexpected 2 indistinguishable
    from a 1 forever. Bronze is 1:1 with the parser's output — typing and casing only, no
    semantic conversion (`.claude/agents/data-engineer.md`) — so the byte lands as the
    number it is and the meaning of the number is silver's job.

    `test_the_flag_bytes_only_ever_hold_zero_or_one` then checks the domain against the
    real files, so the day the game writes something else, we find out.
    """
    hints = get_type_hints(CalendarEvent)
    for name in ("event_over", "deleted", "needs_human_action"):
        assert hints[name] is int, (
            f"CalendarEvent.{name} is typed {hints[name]!r}. A u8 flag lands as its "
            "integer: collapsing it to bool asserts the domain is {0, 1}, which nothing "
            "has proven, and destroys the evidence if it ever is not."
        )


def test_the_event_type_integer_lands_raw_and_is_given_no_human_label() -> None:
    """Both halves together — the raw value IS landed, the interpretation is NOT.

    A guard that only banned the label would pass a parser that dropped `event_type`
    entirely, and a module that only landed the integer could still grow a lookup table
    next week. The pair is the actual posture: withhold the meaning, keep the datum.
    """
    hints = get_type_hints(CalendarEvent)
    assert hints["event_type"] is int, "the raw enum value must land, unmapped"

    offenders = _field_names(CalendarEvent) & FORBIDDEN_LABEL_FIELDS
    assert not offenders, (
        f"CalendarEvent gained {sorted(offenders)}. The event-type enum's semantics are "
        "undocumented and unread; a human label invented from the integers would be "
        "wrong on some rows with nothing raised. Ask the operator to read the calendar "
        "screen, as Phase 6 does for `list_id`, before naming anything."
    )


def test_division_membership_carries_the_explicit_team_array_and_its_place_in_the_nest() -> None:
    """The array is the point. A division that knew only its own id would prove nothing.

    Membership is `league → sub_league → division → u32 count + explicit team_id array`,
    and the array is what lets silver derive `teams.division_id` — the field Phase 5a
    correctly refused to parse because it is not in `teams.dat` (0 of 140 on the teams
    that have a non-zero one).
    """
    assert _field_names(DivisionMembership) == {
        "league_id",
        "sub_league_id",
        "division_id",
        "team_ids",
    }
    assert get_type_hints(DivisionMembership)["team_ids"] == tuple[int, ...], (
        "team_ids must be an immutable tuple of ints in the order the file gives them. "
        "A set would discard the order the array was written in, and a list would let a "
        "caller mutate a landed record."
    )


def test_division_id_did_not_sneak_back_onto_the_team_record() -> None:
    """The temptation this phase creates, guarded at the point it appears.

    Phase 5a removed `division_id` from `TeamRecord` because `teams.dat` does not carry
    it. This phase lands the array that *does* carry it, and the obvious next move — stamp
    it onto the team record while we have it — would re-import a field into a walker that
    cannot read it, keyed off a join the bronze layer is not allowed to do (bronze is 1:1
    with parser output; no joins). It is derived in **silver**, from this array.
    """
    assert "division_id" not in _field_names(TeamRecord), (
        "TeamRecord regained `division_id`. It is not in `teams.dat` — measured, 0 of "
        "140 on the discriminating subset — so any value there came from a join the "
        "parser performed. Derive it in silver from `bronze_division_team` instead."
    )


def test_a_walked_region_records_what_it_claimed_and_what_it_delivered() -> None:
    """`region-accounted` is only a claim if the numbers behind it are on the record.

    `declared_count` is what the file said; `parsed_count` is what the walk produced.
    Keeping both means the self-check is auditable after the fact rather than being an
    assertion that ran once inside the parser and left no trace.
    """
    assert _field_names(WorldRegion) == {
        "name",
        "entered_at",
        "length",
        "declared_count",
        "parsed_count",
    }


def test_the_file_result_reports_enough_to_reconstruct_the_accounting() -> None:
    """Everything `tests/test_byte_accounting.py` needs to check the tier from outside.

    `file_bytes` is here so the un-walked remainder is derivable rather than asserted by
    the parser about itself. A walker that reports its own residual and its own file size
    can be internally consistent and wrong; a walker that reports the file size the OS
    also knows cannot.
    """
    assert _field_names(WorldFile) == {
        "sim_date",
        "divisions",
        "calendar",
        "regions",
        "file_bytes",
    }


# ── the tier declaration ─────────────────────────────────────────────────────


def test_the_byte_accounting_tier_is_declared_and_known() -> None:
    assert BYTE_ACCOUNTING_TIER in KNOWN_TIERS, (
        f"{BYTE_ACCOUNTING_TIER!r} is not a pre-registered tier. The legal set is "
        f"{sorted(KNOWN_TIERS)} and it lives in `tests/fixtures/tiers.py`; adding a "
        "fourth is a main-thread decision, not a walker's."
    )


def test_a_tier_below_strict_has_to_say_why() -> None:
    """The demotion is allowed; doing it silently is not.

    Six months on, a bare `region-accounted` is indistinguishable from nobody having
    tried. Say what was reached, what was not, and what a later attempt should try first
    — for this file, that is the from-the-top walk behind the ~94,000-record city array.
    """
    if BYTE_ACCOUNTING_TIER == "strict":
        return
    assert len(TIER_RATIONALE.strip()) >= 80, (
        f"the world walk is at the {BYTE_ACCOUNTING_TIER!r} tier with no written "
        "rationale. This is the weakest claim any walker in this project makes — it is "
        "the one that most needs its limits written down."
    )


# ── refusals ─────────────────────────────────────────────────────────────────


def test_a_file_that_is_not_a_save_is_refused() -> None:
    with pytest.raises(MalformedHeader):
        read_world(b"not an OOTP file at all")


def test_the_magic_at_offset_zero_trap_is_refused() -> None:
    """`docs/data-access.md` §4: the magic begins at offset 1, after a leading null."""
    with pytest.raises(MalformedHeader):
        read_world(make_header(filename=WORLD_FILE, magic_at_offset_zero=True))


def test_a_future_game_version_is_refused_rather_than_guessed_at() -> None:
    with pytest.raises(UnsupportedSaveVersion):
        read_world(make_header(filename=WORLD_FILE, version=26))


def test_a_header_naming_a_different_file_is_refused() -> None:
    with pytest.raises(SaveFilenameMismatch):
        read_world(make_header(filename="teams.dat"))


def test_an_empty_buffer_is_refused_rather_than_read_as_an_empty_world() -> None:
    with pytest.raises(MalformedHeader):
        read_world(b"")


def test_a_file_with_no_landmark_raises_rather_than_returning_an_empty_world() -> None:
    """**The refusal this whole approach stands on.**

    A from-the-top walk that loses alignment runs off the end and raises. A landmark walk
    has a second, quieter failure available to it: find nothing, return nothing, and hand
    back a world with no divisions and no calendar that is structurally indistinguishable
    from a league that genuinely has neither. Nothing downstream can tell those apart —
    an empty division array yields an empty `bronze_division_team`, and a report showing
    no divisions looks like a report about a league without divisions.

    So a landmark that does not resolve is an error, always. Same for one that resolves
    more than once: `human_managers.py` set the precedent — the landmark is required to
    be **unique**, and ambiguity raises rather than taking the first match.
    """
    headers_only = make_header(filename=WORLD_FILE, sim_date=(18, 3, 2024))
    with pytest.raises(SaveFormatError):
        read_world(headers_only + bytes(4096))


# ── the calendar decoder, offline ────────────────────────────────────────────


def _cursor(payload: bytes) -> Cursor:
    return Cursor(payload, label="synthetic calendar")


def test_a_count_prefixed_calendar_decodes_and_consumes_its_region_exactly() -> None:
    """The region-accounting claim's inner half, provable with no game installed.

    "Zero residual **within** each walked region" is the only part of the
    `region-accounted` tier that is a statement about record widths rather than about
    where the file was entered. If it holds on synthetic bytes it is being tested on
    every PR; if it were only checked against the real save it would be checked on one
    machine, and the tier would be a promise rather than a test.
    """
    region = make_calendar(
        (
            make_calendar_event(seq=1, name="OPENING DAY", day=28, month=3, year=2024),
            make_calendar_event(seq=2, name="Trading Deadline", day=31, month=7, year=2024),
        )
    )
    cursor = _cursor(region)
    events = read_calendar(cursor)

    assert [event.seq for event in events] == [1, 2]
    assert [event.name for event in events] == ["OPENING DAY", "Trading Deadline"]
    assert str(events[0].start_date) == "2024-03-28"
    assert str(events[1].start_date) == "2024-07-31"
    assert cursor.exhausted(), (
        f"{cursor.remaining()} bytes remain after two records. The declared count was "
        "consumed but the widths do not add up, so the walk would land off the next "
        "region's boundary — which is exactly the desynchronisation the region's own "
        "count exists to catch."
    )


def test_the_fields_after_the_event_name_survive_a_change_in_its_length() -> None:
    """The variable-length hazard, on the one record in this file that carries it.

    The name is length-prefixed, so every field after it — the three flags and the
    trailing u16 — sits at a different absolute offset in a short-named record than in a
    long-named one. This is `tests/test_sequential_walk.py`'s argument applied to the
    calendar: same values in, same values out, whatever the name does to the width.
    """

    def only_event(name: str) -> CalendarEvent:
        region = make_calendar((make_calendar_event(name=name, seq=9, deleted=1),))
        return read_calendar(_cursor(region))[0]

    narrow = only_event("X")
    wide = only_event("A considerably longer event name than the other one")

    assert narrow.name != wide.name, "the two records were meant to differ in name width"
    assert narrow.seq == wide.seq == 9
    assert narrow.deleted == wide.deleted == 1
    assert (narrow.event_over, narrow.needs_human_action, narrow.real_sim_date) == (
        wide.event_over,
        wide.needs_human_action,
        wide.real_sim_date,
    )


def test_a_region_that_declares_more_records_than_it_holds_raises() -> None:
    """The self-check that makes landmark entry defensible instead of merely convenient.

    Entry is by content, so a landmark that matched the wrong place lands the walk in
    bytes that are not a calendar. What catches that is the count: read it, consume
    exactly that many records, and run off the end when the region was never a calendar
    at all. A walker that returned what it managed to read would convert a mis-entry into
    a short calendar with nothing raised.
    """
    region = make_calendar((make_calendar_event(),), declared_count=2)
    with pytest.raises(SaveFormatError):
        read_calendar(_cursor(region))


def test_the_declared_count_is_authoritative_and_the_boundary_check_is_the_callers() -> None:
    """Under-declaring is the mirror case, and it is deliberately *not* raised here.

    `read_calendar` consumes exactly what the region claims and stops — it has no way to
    know what follows, because what follows is another region. The leftover is visible to
    the caller as an un-exhausted cursor, and `read_world` is what turns it into a
    refusal by requiring the walk to land on the next region's boundary. Splitting the
    responsibility this way is what keeps the decoder testable in isolation.
    """
    region = make_calendar(
        (make_calendar_event(seq=1), make_calendar_event(seq=2)), declared_count=1
    )
    cursor = _cursor(region)

    events = read_calendar(cursor)
    assert len(events) == 1, "the count is authoritative; the decoder must not read past it"
    assert not cursor.exhausted(), (
        "the second record was silently consumed. The decoder must stop at the declared "
        "count and leave the remainder for the caller's boundary check to fail on."
    )


# ── the real files ───────────────────────────────────────────────────────────


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"cannot resolve settings: {exc}")


def _read(save: SaveRef) -> WorldFile:
    path = save.path / WORLD_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {WORLD_FILE}")
    return read_world(path.read_bytes())


def _every_save() -> list[tuple[str, WorldFile]]:
    """Every configured save, named, or a loud skip.

    Two at minimum, for the reason the teams module gives: a structure checked against a
    single file cannot distinguish a correct walk from one fitted to that file.
    """
    settings = _settings()
    present = [ref for ref in (settings.managed, settings.probe_save, settings.truth_save) if ref]
    if len(present) < 2:
        pytest.skip("fewer than two saves are configured; one universe proves nothing here")
    return [(ref.league, _read(ref)) for ref in present]


@pytest.mark.gamedata
def test_the_calendar_holds_every_entry_including_the_ones_marked_deleted() -> None:
    """3,058 — and the number is the assertion, not a sanity check.

    `deleted` is set on 2,482 of them, so a walker that filters at parse time returns 576
    and every count below it still looks internally consistent. The count is the only
    thing that catches it, which is why it is pinned rather than bounded.
    """
    for league, world in _every_save():
        assert len(world.calendar) == CALENDAR_EVENTS, (
            f"{league}: {len(world.calendar)} calendar entries, expected "
            f"{CALENDAR_EVENTS}. If this is near {CALENDAR_EVENTS - PROBE_DELETED_EVENTS} "
            f"or {CALENDAR_EVENTS - MANAGED_DELETED_EVENTS}, the walk is filtering deleted "
            "rows at parse time — land them and let the report filter."
        )


@pytest.mark.gamedata
def test_the_calendars_key_is_seq_and_the_readable_alternative_would_lose_events() -> None:
    """The grain decision, asserted as data rather than recorded as a preference.

    `(save_id, sim_date, ingest_seq, event_seq)`. The tempting alternative —
    `(league_id, start_date, type, name)`, which reads like a natural key and needs no
    field the export lacks — collapses 3,058 rows to 2,600. **458 events vanish, silently
    and by construction**, and a PK on it would land the survivor of each collision with
    no error anywhere.

    Both halves are asserted together. Uniqueness alone would pass on a `seq` the parser
    invented by enumeration; the collapse alone would not say what to use instead.
    """
    for league, world in _every_save():
        sequences = {event.seq for event in world.calendar}
        assert len(sequences) == len(world.calendar), (
            f"{league}: {len(world.calendar) - len(sequences)} duplicate `seq` values. "
            "The grain rests on this field being unique in the file; if it is not, the "
            "key is wrong and nothing else in this module matters."
        )

        readable = {
            (event.league_id, str(event.start_date), event.event_type, event.name)
            for event in world.calendar
        }
        assert len(readable) == COLLAPSED_BY_READABLE_KEY, (
            f"{league}: the human-readable key now yields {len(readable)} distinct rows, "
            f"not {COLLAPSED_BY_READABLE_KEY}. The measured collapse is the recorded "
            "reason for keying on `seq` — if the number moved, re-derive the argument "
            "rather than editing the constant."
        )


@pytest.mark.gamedata
def test_deleted_is_an_attribute_of_a_future_event_and_not_a_synonym_for_past() -> None:
    """The finding that stops the obvious optimisation.

    Most of the calendar carries `deleted`, and **deleted rows are dated after the sim
    date** — the set includes a duplicate OPENING DAY and three PLAYOFFS BEGIN. So the
    flag is not a tombstone for events that already happened; reading it that way and
    filtering on it would drop live schedule from the front office's view of its season.

    The count is asserted **per universe** because it is per-universe state. Pinning one
    number across all three saves is what this test did in its first draft, and it was
    wrong in both available directions at once.
    """
    managed = _settings().managed.league
    for league, world in _every_save():
        expected = MANAGED_DELETED_EVENTS if league == managed else PROBE_DELETED_EVENTS
        deleted = [event for event in world.calendar if event.deleted]
        assert len(deleted) == expected, (
            f"{league}: {len(deleted)} deleted entries, expected {expected}"
        )

        sim = str(world.sim_date)
        future_deleted = [event for event in deleted if str(event.start_date) > sim]
        assert future_deleted, (
            f"{league}: every deleted event is dated on or before the sim date {sim}, so "
            "`deleted` does look like history here. That contradicts the measurement — "
            "check the date decode before believing it, then bring it to the main thread."
        )


@pytest.mark.gamedata
def test_the_two_universes_share_a_calendar_and_disagree_only_about_deletion() -> None:
    """The corrected finding, asserted directly instead of through two pinned counts.

    `OOTP-AI.lg` and the Challenge probe are separately created universes, and their
    calendars are the same 3,058 events — same `seq`, same names, same dates, same flags —
    **except for `deleted`, which differs on exactly 233 of them and always in the same
    direction.** The shipped calendar is common; deletion is state the universe accumulates.

    This is worth an assertion of its own rather than being left implicit in the two
    counts above, because it is the claim those counts are evidence *for*. It also fails
    loudly on the one bug the landmark approach makes possible: a walk that entered a
    slightly different place in one save would agree on the count and disagree everywhere
    else, which two totals would never reveal.
    """
    settings = _settings()
    if settings.probe_save is None:
        pytest.skip("OOTP_PROBE_LEAGUE is unset — there is no second universe to compare")

    managed = {event.seq: event for event in _read(settings.managed).calendar}
    probe = {event.seq: event for event in _read(settings.probe_save).calendar}

    assert set(managed) == set(probe), (
        "the two universes' calendars do not even carry the same `seq` values, so the "
        "walk entered a different structure in one of them"
    )

    differing = [
        seq for seq in managed if replace(managed[seq], deleted=0) != replace(probe[seq], deleted=0)
    ]
    assert not differing, (
        f"{len(differing)} events differ in something other than `deleted` "
        f"(first: {managed[differing[0]]} vs {probe[differing[0]]})"
    )

    flipped = {
        (managed[seq].deleted, probe[seq].deleted)
        for seq in managed
        if managed[seq].deleted != probe[seq].deleted
    }
    count = sum(1 for seq in managed if managed[seq].deleted != probe[seq].deleted)
    assert count == DELETED_DELTA, (
        f"{count} events differ in `deleted`, expected {DELETED_DELTA} "
        f"({PROBE_DELETED_EVENTS} - {MANAGED_DELETED_EVENTS})"
    )
    assert flipped == {(0, 1)}, (
        f"the disagreements run in both directions ({sorted(flipped)}). Measured, every "
        "one of the 233 is live in the managed league and deleted in the probe — a "
        "two-way split means something other than accumulated deletion is going on."
    )


@pytest.mark.gamedata
def test_the_flag_bytes_only_ever_hold_zero_or_one() -> None:
    """The check that earns the right to treat the three flags as flags downstream.

    They land as integers precisely so this can be asked rather than assumed. A value
    outside {0, 1} is not a failure of the parser — it is a finding about the format, and
    it should arrive as a red test rather than as a `True` that used to be a 2.
    """
    for league, world in _every_save():
        observed = {
            (event.event_over, event.deleted, event.needs_human_action) for event in world.calendar
        }
        outside = {value for triple in observed for value in triple} - {0, 1}
        assert not outside, (
            f"{league}: calendar flag bytes hold {sorted(outside)} as well as 0 and 1. "
            "Do not coerce — the flags are not booleans, and what the other values mean "
            "is a question for the operator's calendar screen."
        )


@pytest.mark.gamedata
def test_the_game_names_the_three_dates_the_front_office_must_show_up_for() -> None:
    """The field this phase is for, pinned by name and date.

    `needs_human_action` is the game's own answer to a question ADR 0013 currently
    answers by our judgment alone: which dates require the GM rather than the staff. Three
    live MLB events carry it in the probes — the draft, the deadline, and the Rule 5 draft.

    **The live set is stated as a subset, not an equality, and the reason turned out to
    matter.** 112 events carry the flag in every save, but how many survive undeleted is
    per-universe: three in the probes and **ten** in `OOTP-AI.lg`, which still holds live
    duplicates. An equality fitted to the probe would have been red on the only league
    this project actually manages. What is pinned is that these three are present, live
    and flagged; that the total is 112 everywhere; and that the flag discriminates at all,
    because a constant-1 field would satisfy the first clause perfectly.
    """
    for league, world in _every_save():
        flagged = {
            (event.name, str(event.start_date))
            for event in world.calendar
            if event.needs_human_action and not event.deleted
        }
        missing = HUMAN_ACTION_EVENTS - flagged
        assert not missing, (
            f"{league}: the game flags no live event for {sorted(missing)}. These are the "
            "dates the front office is required to act on; losing one means the action "
            "economy is guessing about a date the save already knew."
        )

        total = sum(1 for event in world.calendar if event.needs_human_action)
        assert total == FLAGGED_EVENTS, (
            f"{league}: {total} events carry the flag, expected {FLAGGED_EVENTS}. Unlike "
            "`deleted`, this total is the same in all three saves and in the export, so a "
            "different number here is the walk rather than the universe."
        )
        assert total < len(world.calendar) // 2, (
            f"{league}: {total} of {len(world.calendar)} events want human action. A field "
            "that is nearly always set is not the field — the byte read is something else."
        )


@pytest.mark.gamedata
def test_no_club_appears_in_two_divisions_of_the_same_league() -> None:
    """Self-consistency, checkable in the universe that has no export.

    `OOTP-AI.lg` has no answer key, so what survives there is structural. A club in two
    divisions means the nest was mis-framed and one array's length prefix was read as
    something else — the failure mode a count-prefixed array is supposed to make
    impossible, which is exactly why it is worth confirming it did.
    """
    for league, world in _every_save():
        assert world.divisions, f"{league}: the walk found no divisions at all"
        for division in world.divisions:
            assert division.team_ids, (
                f"{league}: division {division.division_id} of league "
                f"{division.league_id} holds no clubs — an empty count-prefixed array is "
                "far more likely to be a mis-entered landmark than a real empty division"
            )
            assert len(set(division.team_ids)) == len(division.team_ids), (
                f"{league}: division {division.division_id} lists a club twice"
            )

        by_league: dict[int, list[int]] = {}
        for division in world.divisions:
            by_league.setdefault(division.league_id, []).extend(division.team_ids)
        for league_id, members in by_league.items():
            duplicates = sorted({tid for tid in members if members.count(tid) > 1})
            assert not duplicates, (
                f"{league}: clubs {duplicates} appear in more than one division of "
                f"league {league_id}"
            )


@pytest.mark.gamedata
def test_the_walk_enters_both_regions_and_each_one_audits_itself() -> None:
    """What `region-accounted` asserts about the regions themselves.

    Byte-level accounting is `tests/test_byte_accounting.py`'s job. What is checked here
    is that both target regions were actually entered, that the vocabulary stayed inside
    what was pre-registered, and that each region delivered exactly what it declared —
    the property the landmark approach trades a from-the-top walk for.
    """
    for league, world in _every_save():
        names = tuple(region.name for region in world.regions)
        unknown = set(names) - KNOWN_REGIONS
        assert not unknown, (
            f"{league}: the walk reports region(s) {sorted(unknown)}, which are not in "
            f"the pre-registered set {sorted(KNOWN_REGIONS)}. Naming a new region is a "
            "main-thread decision — say what it is and why it had to be crossed."
        )
        assert tuple(n for n in names if n in REQUIRED_REGIONS) == REQUIRED_REGIONS, (
            f"{league}: walked regions {list(names)} — both {list(REQUIRED_REGIONS)} must "
            "be present, in that order"
        )
        assert len(set(names)) == len(names), f"{league}: a region name repeats: {names}"

        for region in world.regions:
            assert region.declared_count == region.parsed_count, (
                f"{league}: region {region.name!r} declared {region.declared_count} "
                f"records and the walk accounted for {region.parsed_count}"
            )
            assert region.length > 0 and region.entered_at > 0


@pytest.mark.gamedata
def test_a_constant_offset_would_not_have_found_these_regions() -> None:
    """The premise the landmark exists to protect — and the one that can go vacuous.

    If every save happened to put the calendar at the same byte, then a constant would
    have worked, the search would be doing no work, and this module's central argument
    would be decoration. The leagues region sits behind a per-league team array (259
    records in the probes, 337 in the managed league) and the schedule, so the offsets
    should differ — but "should" is why it is asserted.

    **If this goes red, do not delete it.** A genuinely constant entry point is a real
    finding about the format and belongs in front of the main thread, not in a diff.
    """
    entries = {
        league: tuple(region.entered_at for region in world.regions)
        for league, world in _every_save()
    }
    assert len(set(entries.values())) > 1, (
        f"every configured save enters its regions at the same offsets ({entries}). "
        "Either the saves are more alike than they should be, or the walk is not "
        "searching for the landmark it claims to search for."
    )


@pytest.mark.gamedata
def test_two_reads_of_the_same_unchanged_file_agree() -> None:
    """A walk that carries state between calls fails here and nowhere else."""
    settings = _settings()
    first, second = _read(settings.managed), _read(settings.managed)

    assert first.calendar == second.calendar
    assert first.divisions == second.divisions
    assert first.regions == second.regions
