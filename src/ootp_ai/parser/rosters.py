"""Roster membership — the `(team_id, player_id, list_id)` grain, from two files at once.

**Read this docstring before the code.** The obvious reading of this grain — "find the
roster array in `teams.dat` and read the list ids out of it" — is not available, and the
first half of this module's story is the proof of why.

## What the `teams.dat` array is, and what it is not

Each team record carries one contiguous stride-4 `u32` array of player ids, in the
record's undecoded body (`~record+1150..1520`; it moves per team). `measured` against
every club of the standard-mode export: the array's **multiset** is exactly the club's
`team_roster` rows plus one entry per player assigned to the club with no roster row —
229 of 229 clubs, no exceptions. A player on three lists appears three times.

**The array's order does not encode the list, and cannot.** Three refutations, each
measured on the standard save:

* It is not four lists concatenated: the same player recurs within a 3-slot window
  (id 31499 at slots 6, 9 and 12 of Boston's 97), so no partition into duplicate-free
  sub-arrays exists at the observed list sizes.
* No parallel tag data exists: scans for a per-slot `u8` list array, for index
  permutations into the array, and for count prefixes all came back empty; the array is
  bounded by the club's finance block before and its coaching-staff id array after.
* The order is not even a function of the roster: the two test saves hold **identical
  Boston rosters** (same 97-entry multiset) in **different orders** — 88 of 97 slots
  agree and the rest permute in local cycles, the fingerprint of a serialized container
  whose collision order depends on insertion history. Whatever wrote it, the bytes do
  not determine slot-to-list — for this parser or for the game.

## Where the list assignment actually lives

Per player, in `players.dat`, in a **roster-status byte** the identity-tail walk stops
just short of: 22 bytes past the second historical string (a 13-byte unclassified span,
the four injury-proneness bytes, five more unclassified bytes, then the flag byte).
`verified` bit-by-bit against every `retired = 0` row of the export:

| bit | meaning | evidence |
|---|---|---|
| 2 | on an organisation top club's **active roster** | 959/959 MLB players, zero disagreements in any save |
| 3 | on the organisation's **secondary (40-man) roster** | equals the 935 `list_id = 3` rows exactly; the only other carriers are league-less free agents with no team |
| 4 | on the **injured list** | equals the 330 `list_id = 4` rows exactly, 18,072/18,072 |
| 5 | 60-day IL placement | equals the plan's measured 58-player population exactly; not needed for the grain |

Membership then *solves*, using the array's multiplicity as the second equation. For a
player assigned to club `T` with `m` occurrences in `T`'s array:

    active = m - 1 - il_bit - (secondary_bit if org == T else 0)

and a correct decode leaves `active` 0 or 1. His rows are `1` at `T`, `2` at `T` if
active, `4` at `T` if injured, and `3` at his **organisation's** club if the secondary
bit is set — which is how one player legitimately spans two clubs (the 40-man prospect
assigned to an affiliate). The org attribution is `verified`: all 935 list-3 rows carry
the player's `organization_id` as their team.

The multiplicity is load-bearing, not decorative: the standard save never shows a
rostered-but-inactive minor leaguer (every rostered player is on an active list or the
IL, so list 2 looks derivable from flags alone) — but the **managed league at 2024-03-07
carries 154 of them**, players whose only row is their assignment. Only `m` distinguishes
`{1}` from `{1, 2}`; no per-player bit does. A flags-only decode validated green on both
test saves and wrong on 41 managed clubs is exactly the trap this project's rulebook
exists to prevent.

## The two players a multiplicity of one cannot separate — and the day-0 boundary

`m == 1` means `{1}` (rostered, nothing else — e.g. designated for assignment) or `{}`
(assigned to the club but on no roster list at all; the export renders `league_id`
negative for exactly this population, 176 players in every save on disk). The status
byte is `0x00` for both. What separates them, `measured` on all three saves: the
unrostered 176 all carry a non-zero `last_organization_id` (equal to their own
organisation, with `last_league_id` naming the league they came from), and **zero** of
the 7,370 rostered players carry one. That is a clean separator today and it is a
**day-0 fact**: after the league trades a player across organisations, rostered players
with non-zero `last_organization_id` will exist. The walk therefore treats the marker as
a *signature to match*, not a rule to trust: an `m == 1` player must match exactly one
of the two measured signatures or the parse refuses. A future save that breaks the
marker breaks it loudly.

## Reconciliation — the check that makes every wrong call visible

After solving every player, the walk rebuilds each club's expected array multiset —
own-club rows, cross-club 40-man entries, unrostered assignees — and requires the
club's actual array to equal it **exactly, per club, per player id**. Any wrong
membership call changes some player's multiplicity somewhere and fails this check by
name. The two files audit each other; neither is trusted alone. `verified`: the full
pipeline reproduces `ootp_truth_real.team_roster` — all 15,672 rows, no extras, no
misses — and runs clean on the challenge save and the managed league, where Boston
resolves to the operator-verified 33 / 26 / 30 / 7 over 96 rows and 34 players.

## What this module deliberately does not do

No derivation from correlates. `team_id > 0` (misses the 176), `injury_is_injured`
(off by 3), `organization_id` alone (identifies the club, not the membership) were all
tested by the plan and rejected; none is consulted here. Every emitted row traces to a
stored bit, a stored assignment field, or a stored array occurrence — and the one
measured-not-verified input, the unrostered marker, is fenced by the signature rule and
the reconciliation above.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ootp_ai.parser.errors import SaveFormatError
from ootp_ai.parser.header import read_header_from
from ootp_ai.parser.lookahead import DATE_WIDTH, U8_WIDTH, U16_WIDTH, U32_WIDTH, peek_u32
from ootp_ai.parser.players import (
    _ASSIGNMENT_BITS,
    _GAP_AFTER_AGE,
    _GAP_AFTER_BIRTH_DATE,
    _GAP_AFTER_EXPERIENCE,
    _GAP_AFTER_HEIGHT,
    _GAP_AFTER_NATION,
    _HEADER_TAIL_FIELDS,
    _UNCLASSIFIED_BEFORE_MASKS,
    PLAYERS_FILE,
    _looks_like_record,
    _next_record_start,
    _read_preamble,
    _scan_tail,
)
from ootp_ai.parser.primitives import Cursor, SaveDate
from ootp_ai.parser.teams import TEAMS_FILE, TeamRecordSpan, read_team_record_spans

__all__ = [
    "LIST_ACTIVE",
    "LIST_ASSIGNMENT",
    "LIST_INJURED",
    "LIST_SECONDARY",
    "AmbiguousRosterMembership",
    "RosterLayoutMismatch",
    "RosterMembership",
    "RostersFile",
    "read_rosters",
]

#: The `team_roster.list_id` enum, settled by operator reading and cross-checked against
#: the export (`requests/feature-requests/first-sight/reviews/list-id-semantics.md`).
LIST_ASSIGNMENT = 1
LIST_ACTIVE = 2
LIST_SECONDARY = 3
LIST_INJURED = 4

#: The record head from the end of `player_id` to the three mask bytes, as the sum of
#: the widths `players.py` names — imported, so a head correction there moves this too.
#: The field sequence is that module's head table: the name-index pair, the birth date,
#: its gap, age, a byte, nation, five bytes, city u32, weight u16, height, a byte,
#: uniform number, experience, the fourteen withheld bytes, and the unclassified u32
#: before the masks.
_NAME_PAIR_WIDTH = 2 * U32_WIDTH
_BIRTH_TO_EXPERIENCE_WIDTH = (
    DATE_WIDTH
    + _GAP_AFTER_BIRTH_DATE
    + U8_WIDTH  # age
    + _GAP_AFTER_AGE
    + U8_WIDTH  # nation_id
    + _GAP_AFTER_NATION
    + U32_WIDTH  # city_of_birth_id
    + U16_WIDTH  # weight
    + U8_WIDTH  # height
    + _GAP_AFTER_HEIGHT
    + U8_WIDTH  # uniform_number
    + U8_WIDTH  # experience
)
_HEAD_AFTER_ID_WIDTH = (
    _NAME_PAIR_WIDTH
    + _BIRTH_TO_EXPERIENCE_WIDTH
    + _GAP_AFTER_EXPERIENCE
    + _UNCLASSIFIED_BEFORE_MASKS
)

#: From the byte after the second historical string to the roster-status byte. `measured`:
#: the status byte's IL bit matches the export at this distance on every one of the
#: 18,072 scorable records, which is only possible if the region between is fixed-width
#: on every record of every save on disk. The three spans are: an unclassified
#: mostly-zero span, the four injury-proneness bytes (`players.py` docstring), and five
#: further unclassified bytes.
_IDENTITY_TRAILER_SPAN = 13
_PRONENESS_SPAN = 4
_PRE_STATUS_SPAN = 5
_IDENTITY_TO_STATUS_WIDTH = _IDENTITY_TRAILER_SPAN + _PRONENESS_SPAN + _PRE_STATUS_SPAN

#: The roster-status byte's decoded bits. Bits 0, 1, 6 and 7 are observed but not
#: classified; none is consulted. Bit 5 (60-day IL) is decoded knowledge but not needed
#: for the grain — the 60-day placement already shows as `il and not secondary`.
_STATUS_ACTIVE_BIT = 2
_STATUS_SECONDARY_BIT = 3
_STATUS_INJURED_BIT = 4

#: Assignment-run bit positions, resolved by name from the tuple `players.py` owns, so a
#: correction there propagates here rather than diverging.
_TEAM_BIT = _ASSIGNMENT_BITS.index("team_id")
_ORGANIZATION_BIT = _ASSIGNMENT_BITS.index("organization_id")
_LAST_ORGANIZATION_BIT = _ASSIGNMENT_BITS.index("last_organization_id")
_LAST_LEAGUE_BIT = _ASSIGNMENT_BITS.index("last_league_id")

#: The `last_league_id` every one of the 176 unrostered assignees carries. `measured` on
#: all three saves — 176 of 176 in each, and zero rostered players carry the marker at
#: all. Part of the signature, never a rule: a save where an unrostered player names a
#: different league is a save where the marker's meaning has moved, and the walk refuses
#: it rather than adapting to it.
_UNROSTERED_LAST_LEAGUE = 234

#: How many entries a single player may legitimately contribute to one club's array:
#: assignment, active-or-injured, and (top clubs only) the secondary roster.
_MAX_MULTIPLICITY = 3


class RosterLayoutMismatch(SaveFormatError):  # noqa: N818
    """A save whose roster structures are not shaped the way every save measured is.

    Raised when a club's membership array cannot be located as exactly one qualifying
    run, when a player record's tail cannot be walked to the status byte, or when the
    two files name different snapshots. The useful response is to re-measure, not to
    loosen the reader.
    """


class AmbiguousRosterMembership(SaveFormatError):  # noqa: N818
    """The two files disagree about somebody's membership, or a state is undecidable.

    Raised when the multiplicity solve leaves no consistent reading, when an `m == 1`
    player matches neither (or both) of the two measured signatures, or when a club's
    array multiset differs from the reconstruction. Emitting a plausible roster instead
    would put a wrong row into bronze with nothing raised — the one failure this grain
    exists to prevent.
    """


@dataclass(frozen=True, slots=True)
class RosterMembership:
    """One `team_roster` row: this player holds this list at this club."""

    team_id: int
    player_id: int
    list_id: int


@dataclass(frozen=True, slots=True)
class RostersFile:
    """Everything one reconciled walk of `teams.dat` + `players.dat` produced.

    `memberships` is sorted by `(team_id, list_id, player_id)`, so parsing the same
    snapshot twice is byte-identical downstream.

    `unrostered` carries the assigned-but-listless players — the population the export
    marks with a negative `league_id` — as `(team_id, player_id)` pairs. They are not
    roster rows and must not be counted as any; they are surfaced because their array
    entries are part of the reconciliation this walk performed, and dropping them
    silently would hide the one population every naive roster join gets wrong.
    """

    memberships: tuple[RosterMembership, ...]
    unrostered: tuple[tuple[int, int], ...]
    sim_date: SaveDate


@dataclass(frozen=True, slots=True)
class _PlayerStatus:
    """The six stored facts about one player that the roster grain consumes."""

    player_id: int
    team_id: int
    organization_id: int
    last_organization_id: int
    last_league_id: int
    status: int


def read_rosters(teams_data: bytes, players_data: bytes) -> RostersFile:
    """Extract the roster-membership grain, reconciling the two files against each other.

    Raises:
        MalformedHeader: either buffer is truncated or not an OOTP record file.
        UnsupportedSaveVersion: either file declares a version we are not proven on.
        SaveFilenameMismatch: either header names a different file.
        UnexpectedEndOfData: a read ran past the end of a buffer.
        PlayerRecordLayout: the players walk lost its framing.
        TeamRecordLayout: the teams walk could not frame the declared record count.
        RosterLayoutMismatch: the roster structures are not shaped as measured.
        AmbiguousRosterMembership: the files disagree, or a membership is undecidable.
    """
    teams_cursor = Cursor(teams_data, label=TEAMS_FILE)
    teams_sim_date = read_header_from(teams_cursor, TEAMS_FILE).sim_date

    players, players_sim_date = _walk_player_statuses(players_data)
    if teams_sim_date != players_sim_date:
        raise RosterLayoutMismatch(
            f"{TEAMS_FILE} is at {teams_sim_date} but {PLAYERS_FILE} is at "
            f"{players_sim_date}. These are two different snapshots, and a roster built "
            "across them would mix two states of the league."
        )

    spans = {span.team_id: span for span in read_team_record_spans(teams_data)}

    assigned: dict[int, list[_PlayerStatus]] = {}
    secondary_by_org: dict[int, list[_PlayerStatus]] = {}
    for player in players:
        if player.team_id <= 0:
            continue
        assigned.setdefault(player.team_id, []).append(player)
        if player.status & (1 << _STATUS_SECONDARY_BIT):
            secondary_by_org.setdefault(player.organization_id, []).append(player)

    arrays: dict[int, Counter[int]] = {}
    for club, members in assigned.items():
        span = spans.get(club)
        if span is None:
            raise RosterLayoutMismatch(
                f"{TEAMS_FILE} has no record for club {club}, but {len(members)} "
                "players are assigned to it. One of the two files is not from this save."
            )
        member_ids = {player.player_id for player in members}
        visitor_ids = {player.player_id for player in secondary_by_org.get(club, [])}
        arrays[club] = _locate_membership_array(teams_data, span, club, member_ids, visitor_ids)

    memberships: list[RosterMembership] = []
    unrostered: list[tuple[int, int]] = []
    expected: dict[int, Counter[int]] = {club: Counter() for club in arrays}
    for club, members in assigned.items():
        array = arrays[club]
        for player in members:
            rows = _solve_membership(player, array[player.player_id])
            if rows is None:
                unrostered.append((club, player.player_id))
                expected[club][player.player_id] += 1
                continue
            for list_id in rows:
                team = player.organization_id if list_id == LIST_SECONDARY else club
                memberships.append(
                    RosterMembership(team_id=team, player_id=player.player_id, list_id=list_id)
                )
                if team not in expected:
                    raise AmbiguousRosterMembership(
                        f"player {player.player_id} holds the secondary roster of "
                        f"organisation {team}, but no club with assigned players has "
                        f"that id — either the organisation field or the secondary bit "
                        "is not what this walk believes."
                    )
                expected[team][player.player_id] += 1

    for club, counts in expected.items():
        if counts != arrays[club]:
            drift = (counts - arrays[club]) + (arrays[club] - counts)
            raise AmbiguousRosterMembership(
                f"club {club}: the membership array and the per-player status fields "
                f"disagree about {len(drift)} player(s), e.g. {sorted(drift)[:5]}. "
                "The two files no longer corroborate each other, and emitting either "
                "reading alone would be a guess."
            )

    memberships.sort(key=lambda row: (row.team_id, row.list_id, row.player_id))
    unrostered.sort()
    return RostersFile(
        memberships=tuple(memberships),
        unrostered=tuple(unrostered),
        sim_date=teams_sim_date,
    )


# ── the players.dat side: assignment fields and the roster-status byte ────────


def _walk_player_statuses(data: bytes) -> tuple[list[_PlayerStatus], SaveDate]:
    """One sequential pass over `players.dat`, reading only what the grain needs.

    The framing, the preamble, the head widths and the identity-tail shape are all
    `players.py`'s — imported, not re-measured — so a correction there propagates here.
    This walk exists because the roster-status byte sits past where `read_players`
    deliberately stops, and extending that walk is not this module's call to make.
    """
    cursor = Cursor(data, label=PLAYERS_FILE)
    header = read_header_from(cursor, PLAYERS_FILE)
    for _ in range(_HEADER_TAIL_FIELDS):
        cursor.u32()
    _read_preamble(cursor, data)

    if not _looks_like_record(data, cursor.position, 0, header.sim_date):
        raise RosterLayoutMismatch(
            f"{PLAYERS_FILE}: the bytes after the preamble are not a player record; "
            "the roster walk would read every status byte from the wrong place."
        )

    players: list[_PlayerStatus] = []
    start: int | None = cursor.position
    previous_id = 0
    while start is not None:
        cursor.skip(start - cursor.position)
        players.append(_read_status_record(cursor, data))
        previous_id = players[-1].player_id
        start = _next_record_start(data, cursor.position, previous_id, header.sim_date)
    return players, header.sim_date


def _read_status_record(cursor: Cursor, data: bytes) -> _PlayerStatus:
    """Consume one record far enough to reach the roster-status byte."""
    player_id = cursor.u32()
    cursor.skip(_HEAD_AFTER_ID_WIDTH)
    assignment_mask = cursor.u8()
    flag_mask = cursor.u8()
    tail_mask = cursor.u8()

    values = dict.fromkeys(range(len(_ASSIGNMENT_BITS)), 0)
    for bit in range(len(_ASSIGNMENT_BITS)):
        if assignment_mask & (1 << bit):
            values[bit] = cursor.i32()
    team_id = values[_TEAM_BIT]
    organization_id = values[_ORGANIZATION_BIT]
    last_organization_id = values[_LAST_ORGANIZATION_BIT]
    last_league_id = values[_LAST_LEAGUE_BIT]

    scan = _scan_tail(data, cursor.position, flag_mask, tail_mask)
    if scan is None:
        if team_id > 0:
            raise RosterLayoutMismatch(
                f"{PLAYERS_FILE}: player {player_id} is assigned to club {team_id} but "
                "its identity tail is not the measured shape, so the roster-status byte "
                "cannot be reached. A membership guessed here would be a membership "
                "invented."
            )
        # An unassigned player contributes nothing to the grain; the framing search
        # recovers the next record without this one's tail being walked.
        return _PlayerStatus(
            player_id=player_id,
            team_id=team_id,
            organization_id=organization_id,
            last_organization_id=last_organization_id,
            last_league_id=last_league_id,
            status=0,
        )

    _, _, prefix_width = scan
    cursor.skip(prefix_width)
    cursor.string()  # historical_id — consumed, not interpreted here
    cursor.string()  # historical_team_id
    cursor.skip(_IDENTITY_TO_STATUS_WIDTH)
    status = cursor.u8()
    return _PlayerStatus(
        player_id=player_id,
        team_id=team_id,
        organization_id=organization_id,
        last_organization_id=last_organization_id,
        last_league_id=last_league_id,
        status=status,
    )


# ── the teams.dat side: locating one club's membership array ──────────────────


def _locate_membership_array(
    data: bytes,
    span: TeamRecordSpan,
    club: int,
    member_ids: set[int],
    visitor_ids: set[int],
) -> Counter[int]:
    """The club's membership array, as a multiset of player ids.

    The array is found by content, not by offset: every candidate id — the club's
    assigned players plus any player whose organisation points here — is searched for
    in the record's span, hits are chained into stride-4 runs (per byte phase, because
    nothing in these records is aligned), and **exactly one** run must contain every
    assigned member. The lineup block earlier in the record also holds player ids, but
    at stride 5 and only a dozen distinct — it cannot qualify, and did not in any of
    the 757 club arrays located across the three saves on disk.
    """
    hits_by_phase: dict[int, list[int]] = {phase: [] for phase in range(U32_WIDTH)}
    for player_id in member_ids | visitor_ids:
        needle = player_id.to_bytes(U32_WIDTH, "little")
        found = data.find(needle, span.start, span.end)
        while found >= 0:
            hits_by_phase[found % U32_WIDTH].append(found)
            found = data.find(needle, found + U8_WIDTH, span.end)

    qualifying: list[Counter[int]] = []
    for hits in hits_by_phase.values():
        hits.sort()
        run: list[int] = []
        for position in [*hits, -1]:  # -1 flushes the final run
            if run and position == run[-1] + U32_WIDTH:
                run.append(position)
                continue
            if run:
                values = Counter(_run_values(data, run))
                if member_ids <= set(values):
                    qualifying.append(values)
            run = [position] if position >= 0 else []

    if len(qualifying) != 1:
        raise RosterLayoutMismatch(
            f"{TEAMS_FILE}: club {club} has {len(qualifying)} candidate membership "
            f"arrays containing all {len(member_ids)} assigned players; exactly one "
            "must exist for the reconciliation to mean anything."
        )
    return qualifying[0]


def _run_values(data: bytes, run: list[int]) -> list[int]:
    """The `u32` at every position of a stride-4 run, through the sanctioned seam."""
    values: list[int] = []
    for position in run:
        value = peek_u32(data, position)
        if value is None:  # pragma: no cover - runs are found inside the buffer
            raise RosterLayoutMismatch(
                f"{TEAMS_FILE}: a membership-array run extends past the buffer."
            )
        values.append(value)
    return values


# ── the solve: which lists this player holds ──────────────────────────────────


def _solve_membership(player: _PlayerStatus, multiplicity: int) -> tuple[int, ...] | None:
    """This player's list ids at his own club, or `None` if he is assigned-but-unrostered.

    The status bits say *which* lists; the array multiplicity says *how many*. The two
    must agree exactly, and every `m == 1` player must match one of the two measured
    signatures — see the module docstring for why that boundary is drawn this sharply.
    """
    injured = bool(player.status & (1 << _STATUS_INJURED_BIT))
    secondary = bool(player.status & (1 << _STATUS_SECONDARY_BIT))
    active_flag = bool(player.status & (1 << _STATUS_ACTIVE_BIT))

    if multiplicity < 1 or multiplicity > _MAX_MULTIPLICITY:
        raise AmbiguousRosterMembership(
            f"player {player.player_id} appears {multiplicity} times in club "
            f"{player.team_id}'s membership array; a player holds one to "
            f"{_MAX_MULTIPLICITY} entries there."
        )

    if player.last_organization_id != 0:
        # The marker means "assigned but unrostered" only as the FULL measured
        # signature — own organisation, league 234, an all-zero status byte, one array
        # entry. A partial match is not a weaker yes: it is the marker's meaning having
        # moved (the expected cause is the league's first cross-organisation
        # transaction, which gives rostered players a non-zero last_organization_id),
        # and silently classifying such a player unrostered would drop his roster rows
        # with nothing raised — the one wrong call the multiset reconciliation provably
        # cannot catch, because both readings contribute exactly one array entry.
        if player.status != 0:
            raise AmbiguousRosterMembership(
                f"player {player.player_id} carries the unrostered marker alongside a "
                f"non-zero status byte (0x{player.status:02x}) — a combination no save "
                "on disk exhibits."
            )
        if multiplicity != 1:
            raise AmbiguousRosterMembership(
                f"player {player.player_id} carries the unrostered marker but appears "
                f"{multiplicity} times in club {player.team_id}'s array. The marker's "
                "measured meaning does not survive this save; re-measure before "
                "trusting either reading."
            )
        if (
            player.last_organization_id != player.organization_id
            or player.last_league_id != _UNROSTERED_LAST_LEAGUE
        ):
            raise AmbiguousRosterMembership(
                f"player {player.player_id} carries a non-zero last_organization_id "
                f"({player.last_organization_id}, organisation "
                f"{player.organization_id}, last league {player.last_league_id}) that "
                "does not match the measured unrostered signature — own organisation "
                f"plus league {_UNROSTERED_LAST_LEAGUE}. The marker has blurred, most "
                "likely at the league's first cross-organisation transaction; "
                "re-measure it before trusting either reading."
            )
        return None

    own_secondary = 1 if secondary and player.organization_id == player.team_id else 0
    active = multiplicity - 1 - int(injured) - own_secondary
    if active not in (0, 1):
        raise AmbiguousRosterMembership(
            f"player {player.player_id}: multiplicity {multiplicity} at club "
            f"{player.team_id} with injured={injured} and own-club "
            f"secondary={bool(own_secondary)} solves to {active} active entries; the "
            "status bits and the array do not describe the same roster."
        )
    if player.organization_id == player.team_id and bool(active) != active_flag:
        raise AmbiguousRosterMembership(
            f"player {player.player_id}: the stored active bit reads "
            f"{active_flag} but the multiplicity solve says {bool(active)} — the "
            "redundant storage disagrees, so one of the two is no longer what it was "
            "measured to be."
        )

    rows = [LIST_ASSIGNMENT]
    if active:
        rows.append(LIST_ACTIVE)
    if secondary:
        rows.append(LIST_SECONDARY)
    if injured:
        rows.append(LIST_INJURED)
    return tuple(rows)
