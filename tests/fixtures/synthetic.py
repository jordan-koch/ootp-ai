"""Synthetic byte builders for parser tests.

**Functions, not data files.** `.gitignore:31` ignores `*.dat`, but `.gitignore:62`'s
`!tests/fixtures/**` is a *later* negation and git's last-match-wins, so a
`tests/fixtures/sample.dat` would in fact be committable — the only thing catching
it is `tests/test_no_leaks.py`'s banned suffixes, as a red build. Building the bytes
in code sidesteps the question entirely, and ADR 0006 keeps OOTP's data out of the
repo at any size for any reason.

`tests/fixtures/README.md` makes the affirmative argument too: a real save's day-0
state is the **least** informative input available, because every variable-length
region is at its minimum — precisely the condition under which a fixed-offset reader
passes cleanly and then corrupts everything later.

Header layout below is `measured` (2026-08-16), byte-for-byte against `teams.dat`,
`players.dat`, `names.dat`, `world.dat` and `scouting.dat` in an OOTP 25 save. Note
`docs/data-access.md` §4 documents the fields but not the filename field's WIDTH;
that is recorded here and routed to the doc gate.
"""

from __future__ import annotations

import struct

# ── Header layout, measured ──────────────────────────────────────────────────
LEADING_NULL = 0x00
MAGIC = b"OOTP"
CURRENT_VERSION = 25

MAGIC_OFFSET = 1
VERSION_OFFSET = 5
FILENAME_OFFSET = 25
FILENAME_FIELD_LEN = 50
SIM_DATE_OFFSET = 75
WRITTEN_DATE_OFFSET = 87

# The four constants between the version and the filename. Identical in every .dat
# file measured; their meaning is unknown and this project does not depend on it.
HEADER_CONSTANTS = (11, 104, 84, 1)

# Bytes that are IDENTICAL across every save — everything up to the sim date. This
# is the correct span for a cross-save header comparison; anything beyond it is
# save-specific and will differ legitimately.
STABLE_PREFIX_LEN = 75

# How much this builder emits: the stable prefix plus the two dates.
BUILT_LEN = 99

# ── A CORRECTION, and the reason it is written down ──────────────────────────
# An earlier version of this file declared `TRAILING_U32 = 7` at offset 75, as a
# header constant. It is not a constant. It is the **day of the league's sim date**,
# and it read 7 in every file sampled only because all five files came from ONE save
# — OOTP-AI, whose sim date is 2024-03-07.
#
# Measured across three saves, offsets 75-98 are two dates as six u32-LE values:
#     75  sim date      day, month, year
#     87  written date  day, month, year
#   OOTP-AI  -> (7, 3, 2024) then (16, 8, 2026)
#   both probes -> (18, 3, 2024), matching their 2024-03-18 sim date
#   saved_games.dat, which has no league, carries (0, 0, 0) first
#
# Two lessons worth keeping. A constant confirmed against a single save is not a
# constant — vary the save before believing it. And the header does NOT end here:
# bytes 99-110 vary per save (a write time, apparently), byte 111 is constant per
# FILE TYPE, and byte 115 varies per save. **Where records actually begin is still
# unknown, so nothing may treat any of these as the start of the body.**


def make_header(
    *,
    version: int = CURRENT_VERSION,
    filename: str = "players.dat",
    magic: bytes = MAGIC,
    leading: int = LEADING_NULL,
    magic_at_offset_zero: bool = False,
    sim_date: tuple[int, int, int] = (7, 3, 2024),
    written_date: tuple[int, int, int] = (16, 8, 2026),
) -> bytes:
    """Build a save-file header.

    `magic_at_offset_zero` builds the *malformed* shape a naive reader assumes —
    `b"OOTP"` at offset 0 with no leading null. `docs/data-access.md:183-186` records
    why that matters: a reader checking `data[0:4]` against `b"OOTP"` sees `\\x00OOT`
    on a real save and rejects every valid file, while one reading the version as a
    u32 at offset 4 gets 6480 rather than 25.
    """
    encoded = filename.encode("ascii")
    if len(encoded) > FILENAME_FIELD_LEN:
        raise ValueError(f"filename exceeds the {FILENAME_FIELD_LEN}-byte field: {filename!r}")
    name_field = encoded.ljust(FILENAME_FIELD_LEN, b"\x00")

    body = (
        magic
        + struct.pack("<I", version)
        + b"".join(struct.pack("<I", value) for value in HEADER_CONSTANTS)
        + name_field
        + b"".join(struct.pack("<I", part) for part in sim_date)
        + b"".join(struct.pack("<I", part) for part in written_date)
    )
    if magic_at_offset_zero:
        return body
    return bytes([leading]) + body


def make_string(value: str) -> bytes:
    """u32-LE length prefix, raw ASCII, **no terminator** (`docs/data-access.md:195`)."""
    encoded = value.encode("ascii")
    return struct.pack("<I", len(encoded)) + encoded


def make_date(day: int, month: int, year: int) -> bytes:
    """u8 day, u8 month, u16 year (`docs/data-access.md:196`)."""
    return struct.pack("<BBH", day, month, year)


def make_color(argb: int) -> bytes:
    """u32 ARGB (`docs/data-access.md:197`)."""
    return struct.pack("<I", argb)


# ── The league calendar, measured ────────────────────────────────────────────
# `world.dat`'s calendar is a u32-count-prefixed array of fixed-shape records with one
# length-prefixed string in the middle. Layout `measured` 2026-08-16: all 3,058 entries
# in the standard-mode probe decode against `ootp_truth_real.league_events` on all eight
# exported columns, and the array is byte-identical in all three saves on disk.
#
# **This is why a synthetic calendar record is legitimate where a synthetic `teams.dat`
# record was not.** Phase 5a refused to hand-build a team record because that record's
# layout was the thing being measured in the phase — a fixture would have asserted a
# guess. Here the shape was measured first, against a full answer key, and the fixture
# pins a finding rather than a hypothesis.
#
# Three bytes of padding sit between the date and the name's length prefix. Measured, the
# real ones are zero — and `parser/world.py`'s *search* relies on that, since three zero
# bytes in a fixed position are part of what distinguishes a calendar record from 8.9 MB of
# everything else. The *decoder* must not rely on it: it is handed a region whose boundaries
# the search already established, and a width it re-derives from the pad would be a width it
# did not read. So the builder fills them with a non-zero byte by default, and a decoder
# that quietly starts validating them goes red here rather than in a save that pads
# differently.
CALENDAR_PAD = b"\xcd\xcd\xcd"


def make_calendar_event(
    *,
    seq: int = 1,
    league_id: int = 1,
    event_type: int = 7,
    day: int = 11,
    month: int = 7,
    year: int = 2024,
    name: str = "SYNTHETIC EVENT",
    event_over: int = 0,
    deleted: int = 0,
    needs_human_action: int = 0,
    real_sim_date: int = 0,
    pad: bytes = CALENDAR_PAD,
) -> bytes:
    """One calendar record: `u32 seq, u32 league_id, u16 type, date, 3 pad, name, 3 flags, u16`.

    `name` is length-prefixed, so records built with different names have different
    widths — which is the whole point of building two of them in a test. Every field
    after the name sits at a different absolute offset in a short-named record than in a
    long-named one, and a reader that seeks past the name by a constant returns the wrong
    flag with nothing raised.
    """
    return (
        struct.pack("<I", seq)
        + struct.pack("<I", league_id)
        + struct.pack("<H", event_type)
        + make_date(day, month, year)
        + pad
        + make_string(name)
        + struct.pack("<BBB", event_over, deleted, needs_human_action)
        + struct.pack("<H", real_sim_date)
    )


def make_calendar(events: tuple[bytes, ...], *, declared_count: int | None = None) -> bytes:
    """A u32 count followed by the events themselves.

    `declared_count` defaults to the truth and exists so a test can **lie** — a region
    that declares more records than it carries must raise rather than return a short
    calendar, which is the self-checking property that makes landmark entry defensible
    at all (`IMPLEMENTATION_PLAN.md` §Phase 5b step 1).
    """
    count = len(events) if declared_count is None else declared_count
    return struct.pack("<I", count) + b"".join(events)


# ── players.dat, measured ────────────────────────────────────────────────────
# The 37-byte fixed head is `measured` 2026-08-17: every field below was scored against
# EVERY `retired = 0` row of `ootp_truth_real.players` (18,072 of them) and matched
# exactly. Like the calendar builder above and unlike a hand-built team record, this
# fixture pins a finding rather than a hypothesis.
#
# The gaps are bytes the walk crosses and does not interpret. They are filled with a
# non-zero sentinel by default for the same reason the calendar pad is: a decoder that
# quietly starts depending on them goes red here rather than in a save that pads
# differently. They must NOT be zero in the fixture — real records carry zeros there, and
# a fixture that copied that would let a zero-scanning bug pass.
PLAYER_GAP_FILL = 0xCD

#: What `players.dat` carries where `teams.dat` carries a record count.
PLAYER_NO_DECLARED_COUNT = 0xFFFFFFFF

#: The preamble between the header tail and the first record: a zero run, this constant,
#: then a length-prefixed 64-character hex digest. Measured identical in all three saves.
PLAYER_PREAMBLE_CONSTANT = 1234
PLAYER_DIGEST_LEN = 64

#: Zero padding before every record start except the first. Measured: 26 bytes in the
#: real files, and never fewer than 24 across all 18,071 gaps.
PLAYER_PAD = b"\x00" * 26


def player_age_on(birth: tuple[int, int, int], sim_date: tuple[int, int, int]) -> int:
    """Whole years between a birth date and a sim date, both `(day, month, year)`.

    The walk's framing depends on the age byte agreeing with this exactly — `measured`,
    it does for all 18,072 records — so the builder computes it rather than letting a
    caller supply an inconsistent default by accident.
    """
    b_day, b_month, b_year = birth
    s_day, s_month, s_year = sim_date
    return s_year - b_year - ((s_month, s_day) < (b_month, b_day))


#: The assignment presence mask's bit order — each field followed by its `last_`
#: counterpart. `verified` against every `retired = 0` export row.
PLAYER_ASSIGNMENT_BITS = (
    "team_id",
    "last_team_id",
    "organization_id",
    "last_organization_id",
    "league_id",
    "last_league_id",
)
PLAYER_FREE_AGENT_BIT = 0

#: The identity tail, `verified` 2026-08-18 against every `retired = 0` export row.
#: Bits 6 and 7 of the second mask carry `bats` and `throws` under **drop-DEFAULT**
#: encoding — the writer elides the majority value 1, so a set bit means a written byte
#: holding a value that is *not* 1. The byte after that mask is a third mask whose bit 1
#: is set on every record of every save measured; the walk requires it as a sentinel and
#: refuses the whole tail without it, which is what lets a record built WITHOUT a tail
#: (the pre-decode legacy shape) parse to `None` + a counted `undecoded_tails` rather
#: than to garbage.
PLAYER_BATS_BIT = 6
PLAYER_THROWS_BIT = 7
PLAYER_TAIL_SENTINEL = 0b10
PLAYER_DEFAULT_SIDE = 1

#: Between the second historical string and the roster-status byte: a 13-byte
#: unclassified span, the four injury-proneness bytes, and five further unclassified
#: bytes. `measured` — the status byte's IL bit matches the export at this distance on
#: all 18,072 scorable records. The fixture emits the span as gap fill because the walk
#: crosses it without interpreting it; a reader that started depending on its contents
#: goes red here rather than on a save that fills it differently.
PLAYER_STATUS_GAP = 22

#: The roster-status byte's decoded bits (`rosters.py`): active on an organisation
#: top club, the secondary/40-man roster, the injured list.
PLAYER_STATUS_ACTIVE_BIT = 2
PLAYER_STATUS_SECONDARY_BIT = 3
PLAYER_STATUS_INJURED_BIT = 4


def make_player_head(
    *,
    player_id: int = 47035,
    name_indices: tuple[int, int] = (12143, 76945),
    birth: tuple[int, int, int] = (26, 6, 1996),
    sim_date: tuple[int, int, int] = (18, 3, 2024),
    age: int | None = None,
    nation_id: int = 206,
    city_of_birth_id: int = 38609,
    weight: int = 187,
    height: int = 188,
    uniform_number: int = 34,
    experience: int = 5,
    assignments: dict[str, int] | None = None,
    free_agent: bool = False,
    assignment_mask: int | None = None,
    gap_fill: int = PLAYER_GAP_FILL,
    tail: bool = False,
    bats: int = PLAYER_DEFAULT_SIDE,
    throws: int = PLAYER_DEFAULT_SIDE,
    historical_id: str = "",
    historical_team_id: str = "",
    status: int | None = None,
) -> bytes:
    """One player record's head, through the club-assignment block.

    `age` defaults to the value consistent with `birth` and `sim_date`, because that
    agreement is what the walk frames on. Passing it explicitly is how a test builds the
    **impostor** that broke the first version of the walker: a run of bytes that has an
    ascending id and a parseable date but an age that cannot belong to it.

    `assignments` maps any of `PLAYER_ASSIGNMENT_BITS` to a value; **the mask is computed
    from which values are non-zero**, exactly as the writer does it, so a fixture cannot
    accidentally disagree with its own mask. `assignment_mask` overrides that, which is
    how a test builds a record whose mask *lies* about what follows.

    `tail=False` builds the **legacy shape** — the record as this fixture emitted it
    before the identity tail was decoded, whose third-mask byte is the non-zero gap fill
    and therefore lacks the sentinel bit. The walk must answer that shape with
    `bats`/`throws`/`historical_id` as `None` and a counted `undecoded_tails`, never by
    consuming it, so the legacy default is a fixture for the degrade path rather than an
    accident of history. `tail=True` builds the measured tail: bats/throws bits computed
    drop-DEFAULT from the values (set exactly when the value is not 1, written byte
    following), the sentinel third mask, then the two length-prefixed historical strings.
    An out-of-set value such as `bats=5` is written as asked — the parser must refuse it,
    and a fixture that sanitised it could never prove that.

    `status` appends the roster-status region — the 22 crossed bytes and then the status
    byte itself — which sits past where `read_players` stops and is read only by
    `rosters.py`'s deeper walk. It needs a valid tail in front of it to be reachable, so
    it requires `tail=True`.
    """
    if not tail and (
        bats != PLAYER_DEFAULT_SIDE
        or throws != PLAYER_DEFAULT_SIDE
        or historical_id
        or historical_team_id
    ):
        raise ValueError("tail fields were supplied but tail=False builds the legacy shape")
    if status is not None and not tail:
        raise ValueError("status requires tail=True — the status byte sits past the tail")
    day, month, year = birth
    stated_age = player_age_on(birth, sim_date) if age is None else age
    gap = bytes([gap_fill])

    values = dict.fromkeys(PLAYER_ASSIGNMENT_BITS, 0)
    values.update(assignments or {})
    mask = 0
    for bit, name in enumerate(PLAYER_ASSIGNMENT_BITS):
        if values[name]:
            mask |= 1 << bit
    written = b"".join(
        struct.pack("<i", values[name])
        for bit, name in enumerate(PLAYER_ASSIGNMENT_BITS)
        if (assignment_mask if assignment_mask is not None else mask) & (1 << bit)
    )
    flags = (1 << PLAYER_FREE_AGENT_BIT) if free_agent else 0

    third_mask = gap
    identity_tail = b""
    if tail:
        if bats != PLAYER_DEFAULT_SIDE:
            flags |= 1 << PLAYER_BATS_BIT
            identity_tail += struct.pack("<B", bats)
        if throws != PLAYER_DEFAULT_SIDE:
            flags |= 1 << PLAYER_THROWS_BIT
            identity_tail += struct.pack("<B", throws)
        third_mask = struct.pack("<B", PLAYER_TAIL_SENTINEL)
        identity_tail += make_string(historical_id) + make_string(historical_team_id)
        if status is not None:
            identity_tail += gap * PLAYER_STATUS_GAP + struct.pack("<B", status)

    return (
        struct.pack("<I", player_id)
        + struct.pack("<I", name_indices[0])
        + struct.pack("<I", name_indices[1])
        + make_date(day, month, year)
        + gap * 3
        + struct.pack("<B", stated_age)
        + gap
        + struct.pack("<B", nation_id)
        + gap * 5
        + struct.pack("<I", city_of_birth_id)
        + struct.pack("<H", weight)
        + struct.pack("<B", height)
        + gap
        + struct.pack("<B", uniform_number)
        + struct.pack("<B", experience)
        # Rating-shaped bytes the walk crosses and withholds, then an unclassified u32
        # that looks like a constant in the test saves and is not one in the managed
        # league — the fixture varies it so nothing can start depending on 203.
        + gap * 14
        + struct.pack("<I", 203 + (player_id % 3) * 18)
        + struct.pack("<B", assignment_mask if assignment_mask is not None else mask)
        + struct.pack("<B", flags)
        + third_mask
        + written
        + identity_tail
    )


def make_players_file(
    heads: tuple[bytes, ...],
    *,
    sim_date: tuple[int, int, int] = (18, 3, 2024),
    body: bytes = b"\xab" * 64,
    bodies: tuple[bytes, ...] | None = None,
    digest: str | None = None,
    preamble_constant: int = PLAYER_PREAMBLE_CONSTANT,
    declared_count: int = PLAYER_NO_DECLARED_COUNT,
    pad: bytes = PLAYER_PAD,
    lead_zeros: int = 46,
) -> bytes:
    """A whole synthetic `players.dat`: header, tail, preamble, then padded records.

    The **first** record follows the preamble with no padding in front of it, which is
    how the real file is laid out and the reason the walker cannot simply search for a
    pad run to find record one.

    `body` is the undecoded remainder each record carries. It is deliberately non-zero:
    a body of zeros would merge with the next record's padding and let a walker that
    mis-locates the boundary pass anyway.

    **`bodies` gives each record its own length, and a test that does not use it is
    weaker than it looks.** With a single `body`, every record in the fixture is the same
    width — so a fixed-stride reimplementation of the walker passes. Real records run
    1,018 to 9,229 bytes, and variable length is the entire reason this parser may not
    seek. Pass `bodies` to exercise that; `body` remains the default for tests where the
    record shape is not what is under test.
    """
    if bodies is not None and len(bodies) != len(heads):
        raise ValueError(f"got {len(bodies)} bodies for {len(heads)} heads")
    per_record = tuple(body for _ in heads) if bodies is None else bodies

    text = "A1" * (PLAYER_DIGEST_LEN // 2) if digest is None else digest
    preamble = b"\x00" * lead_zeros + struct.pack("<I", preamble_constant) + make_string(text)
    tail = struct.pack("<IIIIII", 21, 21, 12, 144, declared_count, 3_289_089)
    records = b"".join(
        (b"" if index == 0 else pad) + head + tail_bytes
        for index, (head, tail_bytes) in enumerate(zip(heads, per_record, strict=True))
    )
    return make_header(filename="players.dat", sim_date=sim_date) + tail + preamble + records


# ── teams.dat, span level ────────────────────────────────────────────────────
# `make_teams_spans_file` builds ONLY what the span walk and the roster reconciliation
# decode: the record frame, an ascending team id, and an opaque body the caller controls.
# It deliberately does NOT synthesize a team record's head — the string signature and
# drop-zero integer run — for the reason Phase 5a refused to: `read_teams` decodes those
# by measurement, and a hand-built head would assert a hypothesis. `read_teams` therefore
# REFUSES buffers built here; `read_team_record_spans` and `read_rosters` accept them,
# because frames and content-located arrays are all they read.

#: Nine zero bytes and a `0x28`, immediately before every record's `team_id`. `measured`
#: (`teams.py`).
TEAMS_RECORD_FRAME = b"\x00" * 9 + b"\x28"


def make_u32_run(values: tuple[int, ...]) -> bytes:
    """A contiguous little-endian `u32` array — the shape of the membership array."""
    return b"".join(struct.pack("<I", value) for value in values)


def make_teams_spans_file(
    records: tuple[tuple[int, bytes], ...],
    *,
    sim_date: tuple[int, int, int] = (18, 3, 2024),
    declared_count: int | None = None,
) -> bytes:
    """A `teams.dat` buffer at span fidelity: header, tail, then framed opaque records.

    `records` is `(team_id, body)` per club, ids ascending. Bodies are the caller's —
    a roster test embeds a membership array (`make_u32_run`) between non-zero filler so
    the content search has exactly one qualifying run to find. Keep bodies free of long
    zero runs: nine zeros and a `0x28` *is* the frame, and a body that fabricates one
    earns a mis-frame the real files never produce.

    `declared_count` defaults to the truth and exists so a test can lie — the span walk
    must refuse a file that frames fewer records than its header declares.
    """
    count = len(records) if declared_count is None else declared_count
    tail = struct.pack("<IIIIII", 21, 21, 12, 144, count, 3_289_089)
    body = b"".join(
        TEAMS_RECORD_FRAME + struct.pack("<I", team_id) + record for team_id, record in records
    )
    return make_header(filename="teams.dat", sim_date=sim_date) + tail + body


def make_record(
    *,
    player_id: int = 47035,
    contract_years: int = 1,
    uniform_number: int = 34,
    historical_id: str = "deverra01",
    salary: int = 27_500_000,
) -> bytes:
    """A synthetic record with a **variable-length region in the middle**.

    This is the shape the whole fixed-offset ban exists for. `contract_years` changes
    the record's length, so every field *after* the contract array sits at a
    different absolute offset in a 1-year record than in a 10-year one. A sequential
    reader is unaffected; a reader that seeks to a constant offset returns the wrong
    field with nothing raised.

    Measured on the real thing (`.claude/agents/data-engineer.md:69-74`): the same
    player's ratings block sat 43 bytes from one anchor in one save and 107 in
    another, with byte-identical internal layout.
    """
    if contract_years < 0:
        raise ValueError("contract_years must not be negative")
    return (
        struct.pack("<I", player_id)
        + struct.pack("<I", contract_years)
        + b"".join(struct.pack("<I", salary) for _ in range(contract_years))
        + struct.pack("<I", uniform_number)
        + make_string(historical_id)
    )
