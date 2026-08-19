"""`names.dat` walked offline, against bytes we authored.

Phase 7's plan lists only `-m gamedata` tests, and §4.1 of the same plan is why this
module exists anyway: *"a phase proved only by `gamedata` tests has zero CI signal"*.
CI has no save, so without this file the entire names walk — the strict tier, the
refusal lattice, the leading-category-byte reading — is unproven on every pull request.

The refusals below are the interesting half. A walker that returns a plausible short
table is the failure this project cannot afford, so each way the shape can be wrong is
built here and required to raise rather than to cope.
"""

from __future__ import annotations

import pytest

from fixtures.synthetic import (
    NAME_CATEGORY_GIVEN_BLOCK,
    NAME_CATEGORY_SURNAME_BLOCK,
    make_header,
    make_name_record,
    make_names_file,
    make_player_head,
    make_players_file,
)
from fixtures.tiers import KNOWN_TIERS
from ootp_ai.parser.errors import (
    SaveFilenameMismatch,
    UnexpectedEndOfData,
    UnsupportedSaveVersion,
)
from ootp_ai.parser.names import (
    BYTE_ACCOUNTING_TIER,
    SINGLE_NAME_SPACE,
    NameRecordLayout,
    NameTable,
    UnknownNameIndex,
    build_name_table,
    read_names,
)
from ootp_ai.parser.players import read_players
from ootp_ai.parser.primitives import SaveDate

# Three entries whose widths differ in every way a record's width can differ: the name
# length, and the number of usage pairs. A fixed-stride reader cannot walk this.
SAMPLE = (
    make_name_record(index=1, text="A.C.", category=NAME_CATEGORY_GIVEN_BLOCK, usage=((0, 1),)),
    make_name_record(index=2, text="Aalto", usage=((11, 1), (6, 2), (30, 7))),
    make_name_record(index=3, text="Yorking", usage=()),
)


def test_the_declared_tier_is_a_known_one() -> None:
    assert BYTE_ACCOUNTING_TIER in KNOWN_TIERS


def test_the_walk_reads_every_entry_and_accounts_for_every_byte() -> None:
    """The strict tier's whole content, offline. Zero residual, or red."""
    parsed = read_names(make_names_file(SAMPLE))

    assert BYTE_ACCOUNTING_TIER == "strict"
    assert parsed.residual_bytes == 0
    assert parsed.declared_record_count == 3
    assert [record.index for record in parsed.names] == [1, 2, 3]
    assert [record.text for record in parsed.names] == ["A.C.", "Aalto", "Yorking"]
    assert parsed.sim_date == SaveDate(day=18, month=3, year=2024)


def test_records_of_different_widths_all_decode() -> None:
    """The variable-length property, stated as an assertion rather than a hope.

    The three fixtures carry 4-, 5- and 7-character names and 1, 3 and 0 usage pairs, so
    every field of record 3 sits at a different absolute offset than it would if records
    1 and 2 were shaped differently. A reader that crossed a record by a constant width
    could not produce this.
    """
    parsed = read_names(make_names_file(SAMPLE))

    assert [len(record.usage) for record in parsed.names] == [1, 3, 0]
    assert parsed.names[1].usage == ((11, 1), (6, 2), (30, 7))
    assert parsed.names[0].category == NAME_CATEGORY_GIVEN_BLOCK
    assert parsed.names[2].category == NAME_CATEGORY_SURNAME_BLOCK


def test_a_name_beginning_with_the_category_byte_still_parses() -> None:
    """The regression that fixes the shape, kept as a test because it is subtle.

    `'t Hart` is a real Dutch surname in the table at index 31,877, and its first
    character is an apostrophe — `0x27`, exactly the value the category byte takes in the
    block before it. Under the trailing-separator reading the walk stops here. Under the
    correct leading-byte reading nothing about it is special, which is what this asserts.
    """
    records = (
        make_name_record(index=1, text="Jin-mook", category=NAME_CATEGORY_GIVEN_BLOCK),
        make_name_record(index=2, text="'t Hart"),
        make_name_record(index=3, text="'t Mannetje"),
    )
    parsed = read_names(make_names_file(records))

    assert [record.text for record in parsed.names] == ["Jin-mook", "'t Hart", "'t Mannetje"]
    assert parsed.residual_bytes == 0


def test_a_high_byte_in_a_name_decodes_rather_than_raising() -> None:
    """1,621 of the real table's entries carry one, so ASCII would refuse the file."""
    parsed = read_names(make_names_file((make_name_record(index=1, text="Rodón"),)))

    assert parsed.names[0].text == "Rodón"


# ── the refusal lattice ──────────────────────────────────────────────────────


def test_a_trailing_byte_is_refused_not_ignored() -> None:
    """Every record framed and the file still not consumed — strict means strict."""
    with pytest.raises(NameRecordLayout, match="bytes remain"):
        read_names(make_names_file(SAMPLE, trailing=b"\x00"))


def test_a_count_larger_than_the_buffer_is_refused() -> None:
    """A short table returned silently is the failure byte accounting exists to catch."""
    with pytest.raises(UnexpectedEndOfData):
        read_names(make_names_file(SAMPLE, declared_count=4))


def test_a_count_smaller_than_the_buffer_is_refused() -> None:
    with pytest.raises(NameRecordLayout, match="bytes remain"):
        read_names(make_names_file(SAMPLE, declared_count=2))


def test_an_implausible_declared_count_is_refused_before_any_walking() -> None:
    """A garbage count must not become a loop bound over an 8.6 MB buffer."""
    with pytest.raises(NameRecordLayout, match="not a name table"):
        read_names(make_names_file(SAMPLE, declared_count=0))


def test_a_missing_preamble_sentinel_is_refused() -> None:
    with pytest.raises(NameRecordLayout, match="sentinel"):
        read_names(make_names_file(SAMPLE, preamble_constant=9999))


def test_content_inside_the_preamble_is_refused_rather_than_scanned_past() -> None:
    """The sentinel alone is not enough: the run in front of it must be *all* zero.

    Distinct from the test above, and the difference is the point. That one removes the
    sentinel; this one keeps it and puts a byte in the middle of the zero run, which is
    what "the walk found *a* 1234 rather than *the* preamble" actually looks like. The
    zero-run measurement is what makes the two separable.
    """
    interrupted = b"\x00" * 20 + b"\xff" + b"\x00" * 25
    with pytest.raises(NameRecordLayout, match="sentinel"):
        read_names(make_names_file(SAMPLE, lead_zeros=0, preamble_prefix=interrupted))


def test_a_nonzero_field_after_a_name_is_refused() -> None:
    """It is zero on 792,285 records across three saves; a value means lost alignment."""
    records = (make_name_record(index=1, text="Aalto", zero_field=7),)
    with pytest.raises(NameRecordLayout, match="not 0"):
        read_names(make_names_file(records))


def test_a_zero_length_name_is_refused() -> None:
    """A blank name resolves to a blank display name, which AC9 forbids outright."""
    records = (make_name_record(index=1, text=""),)
    with pytest.raises(NameRecordLayout, match="blank name"):
        read_names(make_names_file(records))


def test_a_whitespace_only_name_is_refused_too() -> None:
    """The shape a zero-length check alone would miss.

    A length-prefixed run of spaces is not empty, so `if not text` lets it through — and
    every downstream `.strip()` then produces exactly the blank display name AC9 forbids.
    Refused in the walker so it cannot depend on a report layer remembering to check.
    """
    with pytest.raises(NameRecordLayout, match="blank name"):
        read_names(make_names_file((make_name_record(index=1, text="   "),)))


def test_a_repeated_index_is_refused_rather_than_collapsed() -> None:
    """The silent-wrong-name path, and the reason it is refused in the walker.

    A dict keyed on the index is last-write-wins, so without this a file carrying index
    1 twice frames cleanly at **zero residual** — the strict tier fully satisfied and
    nothing raised — and the table then holds one of the two strings while every player
    pointing at that index silently gets it. That is the failure `names.py` §6 argues the
    module exists to prevent, so it may not be reachable by a correct-looking walk.
    """
    records = (
        make_name_record(index=1, text="Alpha"),
        make_name_record(index=1, text="Beta"),
        make_name_record(index=3, text="Gamma"),
    )
    with pytest.raises(NameRecordLayout, match="declares index"):
        read_names(make_names_file(records))


def test_a_gap_in_the_indices_is_refused() -> None:
    """`index == position + 1` is measured on every record of every save, so enforce it.

    Both the single-index-space finding and `bronze_name`'s declared Phase 8 key rest on
    this property. Asserted in prose and enforced nowhere is how the two drift apart.
    """
    records = (
        make_name_record(index=1, text="Alpha"),
        make_name_record(index=99, text="Beta"),
    )
    with pytest.raises(NameRecordLayout, match="declares index 99"):
        read_names(make_names_file(records))


def test_an_index_of_zero_is_refused() -> None:
    """Indices start at 1. A zero would make `resolve(0)` meaningful and it is not."""
    with pytest.raises(NameRecordLayout, match="declares index 0"):
        read_names(make_names_file((make_name_record(index=0, text="Alpha"),)))


def test_the_header_guards_still_apply_to_this_file() -> None:
    """The version guard and the filename check are the walk's first two refusals."""
    with pytest.raises(UnsupportedSaveVersion):
        read_names(make_header(filename="names.dat", version=26) + b"\x00" * 128)
    with pytest.raises(SaveFilenameMismatch):
        read_names(make_header(filename="players.dat") + b"\x00" * 128)


# ── the table, and the per-save constraint ───────────────────────────────────


def test_a_table_carries_the_save_it_was_built_from() -> None:
    """The plan's step 4, in the form this build took — see `names.py` §6.

    The premise behind step 4 was refuted by measurement: the three saves' name tables
    are byte-identical, so a shared table would not in fact produce wrong names *today*.
    The constraint is kept because that identity is a property of shipped data rather
    than an invariant, and the failure it would produce is silent.
    """
    table = build_name_table("OOTP-AI", make_names_file(SAMPLE))

    assert table.save_id == "OOTP-AI"
    assert table.resolve(2) == "Aalto"
    assert table.display_name(1, 2) == "A.C. Aalto"


def test_two_saves_produce_two_independent_tables() -> None:
    """Nothing is shared between them, so one save's names cannot leak into another."""
    left = build_name_table("OOTP-AI", make_names_file(SAMPLE))
    right = build_name_table(
        "Test-Save-Standard-Mode",
        make_names_file((make_name_record(index=1, text="Somebody-Else"),)),
    )

    assert left.save_id != right.save_id
    assert left.entries is not right.entries
    assert left.resolve(1) == "A.C."
    assert right.resolve(1) == "Somebody-Else"


def test_names_py_holds_no_module_level_cache() -> None:
    """The structural half of the per-save constraint, asserted rather than promised.

    A module-level dict keyed on anything — or on nothing — is how one save's table
    reaches another save's players. The check is deliberately blunt: any mutable
    container at module scope in `names.py` fails it, so the next person to add one has
    to come here and argue for it.
    """
    import ootp_ai.parser.names as module

    containers = {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("__") and isinstance(value, dict | list | set)
    }
    assert not containers, (
        "names.py has grown a module-level mutable container "
        f"({sorted(containers)}). A name table must be owned by a save; a module-level "
        "one applied to the wrong save produces confident wrong names with nothing raised."
    )

    # A container is not the likeliest spelling of the cache this forbids. `@lru_cache`
    # on `build_name_table` or `read_names` is one line, reads as an optimisation, and
    # hides its dict behind a wrapper the check above cannot see — so look for the
    # wrapper's own signature instead.
    memoised = [
        name
        for name, value in vars(module).items()
        if not name.startswith("__") and hasattr(value, "cache_info")
    ]
    assert not memoised, (
        f"names.py has a memoised callable ({sorted(memoised)}). functools.lru_cache and "
        "functools.cache both keep a module-level dict keyed on the call arguments; a "
        "table cached on `data` alone would be handed to whichever save asked next."
    )


def test_a_table_refuses_the_wrong_save() -> None:
    """`save_id` has to do something, or the per-save structure is a comment.

    The tables on disk are byte-identical today, so applying the probe's to the managed
    league would produce correct names and prove nothing — which is exactly why the
    mismatch is refused at the point the wrong table is picked up.
    """
    table = build_name_table("Test-Save-Standard-Mode", make_names_file(SAMPLE))

    assert table.for_save("Test-Save-Standard-Mode") is table
    with pytest.raises(UnknownNameIndex, match="built from"):
        table.for_save("OOTP-AI")


def test_an_unknown_index_raises_rather_than_resolving_to_a_placeholder() -> None:
    """A placeholder here would become a roster row with a plausible wrong name."""
    table = build_name_table("OOTP-AI", make_names_file(SAMPLE))

    with pytest.raises(UnknownNameIndex, match="not in the 3-entry table"):
        table.resolve(999)
    with pytest.raises(UnknownNameIndex):
        table.display_name(1, 999)


def test_the_name_space_discriminator_is_a_single_declared_value() -> None:
    """One space was measured, so the key column exists and takes one literal value.

    Pinned because Phase 8 keys `bronze_name` on it. If a second space is ever proven,
    this test is the thing that has to change, which is the point.
    """
    assert SINGLE_NAME_SPACE == "all"
    assert isinstance(SINGLE_NAME_SPACE, str)


def test_a_table_is_a_value_object_not_a_singleton() -> None:
    """Two tables built from the same bytes are equal in content and separate in identity."""
    data = make_names_file(SAMPLE)
    first = build_name_table("OOTP-AI", data)
    second = build_name_table("OOTP-AI", data)

    assert isinstance(first, NameTable)
    assert first.entries == second.entries
    assert first.entries is not second.entries


# ── the join itself, offline ─────────────────────────────────────────────────


def test_the_two_file_join_produces_a_display_name_offline() -> None:
    """The whole point of the phase, exercised in CI against bytes we authored.

    Every other proof of the join is `-m gamedata` and therefore invisible to CI. Both
    fixtures already existed; joining them costs nothing and means a refactor that
    crosses the two slots, or drops one, goes red on a pull request rather than on
    somebody's machine three phases later.

    The indices are deliberately **not** 1 and 2: a walker that returned the pair in file
    order regardless of which slot it read would still produce "Ada Aalto" if first and
    last happened to be adjacent. Pointing them at opposite ends of the table means only
    a correct slot assignment renders the expected name.
    """
    names = make_names_file(
        (
            make_name_record(index=1, text="Aalto", usage=((11, 1),)),
            make_name_record(index=2, text="Bruggeman"),
            make_name_record(index=3, text="Ada", category=NAME_CATEGORY_GIVEN_BLOCK),
        )
    )
    table = build_name_table("OOTP-AI", names)

    head = make_player_head(player_id=4242, first_name_index=3, last_name_index=1, tail=True)
    (player,) = read_players(make_players_file((head,), sim_date=(18, 3, 2024))).players

    assert table.display_name(player.first_name_index, player.last_name_index) == "Ada Aalto", (
        "the join rendered the wrong name from a two-record fixture, which means the "
        "first/last slot assignment or the table lookup is crossed"
    )


def test_the_offline_join_would_catch_a_swapped_slot() -> None:
    """The negative control, so the test above cannot pass by coincidence.

    Reading the slots the other way round must produce a visibly different string. If it
    did not, the fixture would be symmetric and the assertion above would prove nothing.
    """
    names = make_names_file(
        (
            make_name_record(index=1, text="Aalto"),
            make_name_record(index=2, text="Ada", category=NAME_CATEGORY_GIVEN_BLOCK),
        )
    )
    table = build_name_table("OOTP-AI", names)

    assert table.display_name(2, 1) == "Ada Aalto"
    assert table.display_name(1, 2) == "Aalto Ada"
