"""AC15 — the catalog is generated, tracked, deterministic, and says what it withholds.

Two halves, and the split is the same one the artifact itself makes:

* **Offline** — everything that follows from the tracked declarations alone. It runs in CI
  with no game, no save and no MySQL, and it is the half that holds the *tracked* file
  honest: the structural catalog is rebuilt during the test and compared **byte for byte**
  against the committed copy, so a hand edit is red before it is stale.
* **`-m gamedata`** — the generated copy, which needs a landing to describe. Row counts,
  the snapshot date, the coverage statements, and the two properties a page carrying real
  data has to have: no player-level value on it, and no path to a tracked file.

## Why byte-identity rather than "contains the right things"

A tracked generated artifact has exactly one failure mode worth guarding: somebody edits
it. Not maliciously — they fix a typo, or paste in a number, and the file stops being the
output of the generator while still looking like it. A containment assertion cannot see
that. Byte-identity can see nothing else.

It only works because `catalog/structure.py` is a pure function of the declarations: no
clock, no path, no hostname, no git. `test_two_generations_are_byte_identical` is the
anti-vacuity half of that claim, and `test_the_comparison_can_actually_fail` is the
anti-vacuity half of the comparison itself — a guard that has never been shown to reject
anything is a guard nobody has tested.

## The clause about rating column names

AC15 says *"no player-level value and no rating column name appears anywhere in it"*, and
this module reads "rating column name" as `contracts/policy.py`'s own definition —
`WITHHELD_NAME_FRAGMENTS` — rather than inventing a second list. That matters more than it
looks: a fragment added there because a rating slipped past the serving gate starts
guarding the catalog in the same commit, with nobody remembering this file exists.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from fixtures.warehouse import settings_or_skip, warehouse_or_skip
from ootp_ai.catalog import (
    CATALOG_JSON_FILENAME,
    CATALOG_MARKDOWN_FILENAME,
    DEFAULT_DOCS_ROOT,
    TRACKED_JSON_FILENAME,
    TRACKED_MARKDOWN_FILENAME,
)
from ootp_ai.catalog.__main__ import CatalogFiles, generate, main, write_tracked_catalog
from ootp_ai.catalog.render import render_json, render_markdown
from ootp_ai.catalog.structure import (
    RATING_NAME_PATTERN,
    build_structure,
    has_withheld_fragment,
    is_rating,
    summarise_reason,
)
from ootp_ai.catalog.volume import COVERAGE_COLUMNS, fetch_volume
from ootp_ai.config import DEFAULT_OUTPUT_ROOT, ConfigError, Settings, reject_inside_game_roots
from ootp_ai.contracts.loader import Contracts, load_contracts
from ootp_ai.contracts.policy import (
    WITHHELD_NAME_FRAGMENTS,
    Disposition,
    column_disposition,
    disposition,
)
from ootp_ai.parser.names import SINGLE_NAME_SPACE
from ootp_ai.reports.__main__ import ROSTER_FILENAME
from ootp_ai.reports.resolve import NoSuchSnapshot, resolve_snapshot
from ootp_ai.reports.roster import name_join_predicate
from ootp_ai.warehouse.sql import quote_ident

REPO_ROOT = Path(__file__).resolve().parent.parent

TRACKED_MARKDOWN = REPO_ROOT / DEFAULT_DOCS_ROOT / TRACKED_MARKDOWN_FILENAME
TRACKED_JSON = REPO_ROOT / DEFAULT_DOCS_ROOT / TRACKED_JSON_FILENAME

#: Ids below this could appear in the catalog's own prose by coincidence — 259 clubs, 30
#: divisions, 96 columns. Sampling above it makes "this player id is not on the page" a
#: statement about the page rather than about arithmetic.
MIN_SAMPLED_PLAYER_ID = 10_000

#: A name short enough to be a substring of ordinary prose proves nothing when absent.
MIN_SAMPLED_NAME_LEN = 5


def contracts() -> Contracts:
    return load_contracts()


def _rendered_markdown() -> str:
    return render_markdown(build_structure(contracts()))


def _rendered_json() -> str:
    return render_json(build_structure(contracts()))


def _committed(path: Path) -> bytes:
    assert path.is_file(), (
        f"{path.relative_to(REPO_ROOT).as_posix()} is missing. It is a GENERATED file that "
        "is nonetheless tracked — run `uv run python -m ootp_ai.catalog --structure-only` "
        "to write it. `tests/test_repo_structure.py` requires it to exist at all"
    )
    return path.read_bytes()


def _is_git_ignored(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
        ).returncode
        == 0
    )


# ── offline: the tracked half cannot drift from the generator ────────────────


def test_the_tracked_markdown_is_exactly_what_the_generator_produces() -> None:
    """AC15's first clause, and the reason the file may be tracked at all.

    Regenerated *here*, in this process, from the same declarations CI has — then compared
    as bytes. Anything else about this file is negotiable; this is not.
    """
    assert _committed(TRACKED_MARKDOWN) == _rendered_markdown().encode("utf-8"), (
        "docs/warehouse-catalog.md is not what the generator produces. Either it was "
        "edited by hand — it says at the top not to be — or a declaration changed and "
        "nobody regenerated it. `uv run python -m ootp_ai.catalog --structure-only` fixes "
        "the second case and reverts the first"
    )


def test_the_tracked_json_is_exactly_what_the_generator_produces() -> None:
    """The machine-readable sibling gets the same guarantee, or it is a second copy."""
    assert _committed(TRACKED_JSON) == _rendered_json().encode("utf-8")


def test_the_comparison_can_actually_fail() -> None:
    """Anti-vacuity for the two above. A guard never seen to reject is not a guard.

    The plan's acceptance asks the operator to hand-edit one character of the committed
    file and watch this module go red. That is a good manual check and it is not a
    repeatable one, so the same event is staged here: one character, one comparison, and
    the answer must be no.
    """
    rendered = _rendered_markdown()
    mutated = rendered.replace("Grain", "Grian", 1)
    assert mutated != rendered, "the mutation did not change anything, so it proves nothing"
    assert _committed(TRACKED_MARKDOWN) != mutated.encode("utf-8")


def test_two_generations_are_byte_identical() -> None:
    """Determinism, which is what makes byte-identity a fair thing to demand.

    Sorted ordering, no timestamp, no path, no hostname, no git-derived value. A single
    non-deterministic byte would turn the assertions above into a coin flip, and a flaky
    guard gets deleted rather than fixed.
    """
    assert _rendered_markdown() == _rendered_markdown()
    assert _rendered_json() == _rendered_json()


def test_the_entry_point_writes_what_the_renderer_renders(tmp_path: Path) -> None:
    """`uv run python -m ootp_ai.catalog --structure-only`, exercised as the command.

    Through `main()` rather than by calling the writer: AC15 names an invocation, and a
    test that called `render_markdown` directly would prove the renderer works while the
    command stayed broken — the same reason `tests/test_reports.py` renders through
    `render()`.
    """
    assert main(["--structure-only", "--docs-root", str(tmp_path)]) == 0
    assert (tmp_path / TRACKED_MARKDOWN_FILENAME).read_bytes() == _committed(TRACKED_MARKDOWN)
    assert (tmp_path / TRACKED_JSON_FILENAME).read_bytes() == _committed(TRACKED_JSON)


def test_the_two_markdown_files_are_addressed_by_role_not_by_name() -> None:
    """The collision that cost this module four vacuous assertions before it was caught.

    Both Markdown halves are called `warehouse-catalog.md` — the right name in both places
    — so a caller selecting from a flat list by `path.name` silently gets the tracked file
    when it wanted the landing. `CatalogFiles` returns roles instead. This pins the
    hazard so the next author does not helpfully flatten it back into a list.
    """
    assert TRACKED_MARKDOWN_FILENAME == CATALOG_MARKDOWN_FILENAME, (
        "the two Markdown halves no longer share a basename. That is a fine thing to "
        "change, but `CatalogFiles` exists because they did — read its docstring before "
        "flattening it back into a list of paths"
    )


def test_a_docs_root_inside_the_game_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    """CF-06 / ADR 0001. The refusal must be seen to fire, not assumed.

    `--docs-root` is the project's first operator-supplied write root; every other one
    arrives through `.env` and has been fenced since Phase 3. It shipped unvalidated, and
    `--docs-root "$OOTP_SAVED_GAMES/OOTP-AI.lg"` — a slip between two directories the
    operator types often — created four levels of directories inside the managed save and
    exited 0.

    Driven through `reject_inside_game_roots` against a fake game root rather than a real
    one, because a test that needed the real saved-games directory to prove this could
    only run on one machine — and would be pointing a write at the game to prove writes at
    the game are refused.
    """
    game = tmp_path / "saved_games"
    target = game / "OOTP-AI.lg" / "docs"
    game.mkdir(parents=True)

    with pytest.raises(ConfigError) as raised:
        reject_inside_game_roots(target, key="--docs-root", game_roots=(game,))
    assert "ADR 0001" in str(raised.value)
    assert not target.exists(), "the refusal still created the directory it refused"

    # And it must be able to say yes, or it is refusing everything and proves nothing.
    reject_inside_game_roots(tmp_path / "elsewhere", key="--docs-root", game_roots=(game,))


def test_the_structural_half_needs_no_warehouse(tmp_path: Path) -> None:
    """The property that lets a fresh clone regenerate the file CI insists exists.

    `write_tracked_catalog` takes no settings and opens no connection, so this passing in
    CI — which has neither — is the assertion. Stated as a test rather than left implicit
    because the cheapest way to break it is to reach for one count "just for the header".
    """
    written = write_tracked_catalog(tmp_path)
    assert written.catalog_markdown is None and written.catalog_json is None
    assert [path.name for path in written.paths] == [
        TRACKED_MARKDOWN_FILENAME,
        TRACKED_JSON_FILENAME,
    ]
    assert all(path.is_file() for path in written.paths)


# ── offline: what the tracked half must and must not contain ─────────────────


def assert_no_rating_name(text: str, where: str) -> None:
    """AC15's *"no rating column name appears anywhere in it"*, by three predicates.

    Shared so the tracked pair and the GM's copy are held to one rule. The first version
    scanned only the two `docs/` files, which left the page the GM actually reads — and
    `catalog.json` beside it — checked by nothing.
    """
    lowered = text.lower()
    found = [fragment for fragment in WITHHELD_NAME_FRAGMENTS if fragment in lowered]
    assert not found, (
        f"{where} carries withheld name fragment(s) {found}. contracts/policy.py treats "
        "these as rating names on sight"
    )
    shaped = RATING_NAME_PATTERN.findall(lowered)
    assert not shaped, (
        f"{where} carries rating-shaped identifier(s) {shaped[:5]}. The fragment list is "
        "three substrings and cannot know the name of a rating nobody has decoded yet"
    )


def test_no_withheld_name_reaches_the_catalog() -> None:
    """The tracked pair. The GM's copy is held to the same rule under `-m gamedata`."""
    for path in (TRACKED_MARKDOWN, TRACKED_JSON):
        assert_no_rating_name(path.read_text(encoding="utf-8"), path.name)


def test_a_decoded_rating_could_never_be_published() -> None:
    """The injection the panel used to prove the old guard vacuous, kept as a test.

    Two independent things are asserted, and the second is the one that was missing:

    1. `RATING_NAME_PATTERN` catches a realistically-named rating column. The fragment
       list does not — `batting_ratings_contact` contains none of `prone_`,
       `players_value` or `_talent_` — so before this pattern existed the *only* check on
       catalog prose was a list of three substrings that happened not to include it.
    2. The structural rule holds regardless of spelling: a rating-CATEGORY field is never
       named by `build_structure`, whatever it is called. That is the rule; the pattern is
       the backstop for prose, where there is no category to consult.
    """
    assert has_withheld_fragment("batting_ratings_contact")
    assert not any(f in "batting_ratings_contact" for f in WITHHELD_NAME_FRAGMENTS), (
        "the fragment list now catches this name on its own, so the pattern's reason for "
        "existing has changed — re-read the note on RATING_NAME_PATTERN before deleting it"
    )

    # ...and the English word must still survive, or the `ratings` group loses its reason.
    assert not has_withheld_fragment("Two lossy transforms sit between a stored rating")
    assert not has_withheld_fragment("category rating-true, label unconfirmed")

    declaration = contracts()
    named = {field.name for field in build_structure(declaration).withheld_fields}
    rating_fields = {entry.name for entry in declaration.fields if is_rating(entry)}
    assert rating_fields, "no field carries a rating category, so this assertion is vacuous"
    assert not (named & rating_fields), (
        f"the catalog names rating-category field(s) {sorted(named & rating_fields)}. "
        "Withholding a field must not be the thing that publishes its name"
    )


def test_the_redaction_rule_actually_fires() -> None:
    """Anti-vacuity for the check above: the truncation must be reachable.

    `summarise_reason` stops at the first sentence naming a withheld column. If it stopped
    firing — a fragment renamed, the split regex broken — the guard above would keep
    passing right up until the declaration's next edit published a rating name.
    """
    reason = "Safe first sentence. This one names prone_overall and must not survive."
    summary, truncated = summarise_reason(reason)

    assert summary == "Safe first sentence."
    assert truncated
    assert not has_withheld_fragment(summary)
    assert has_withheld_fragment(reason)


def test_the_summary_budget_stops_at_a_sentence_boundary() -> None:
    """Truncation never lands mid-clause, so a quoted reason is never a fragment."""
    reason = " ".join(f"Sentence number {index} of the declared argument." for index in range(40))
    summary, truncated = summarise_reason(reason)

    assert truncated
    assert summary.endswith(".")
    assert summary in reason


def test_the_tracked_half_carries_no_volume() -> None:
    """The split, asserted rather than trusted.

    A count in the tracked file would be a number that goes wrong on the next landing and
    is corrected by nobody, in the one file a fresh clone reads before it has a warehouse.
    """
    text = TRACKED_MARKDOWN.read_text(encoding="utf-8")
    for phrase in ("Rows in this landing", "Ingested at", "This landing", "Coverage, computed"):
        assert phrase not in text, (
            f"the tracked catalog carries {phrase!r}, which belongs to the generated half. "
            "Row counts, snapshot dates and freshness change with every landing"
        )


def test_every_declared_table_is_described() -> None:
    """AC15's structural clauses: grain sentence, key list and source file, per table."""
    text = TRACKED_MARKDOWN.read_text(encoding="utf-8")
    for table in contracts().tables:
        assert f"### `{table.name}`" in text, f"{table.name} has no section"
        assert table.grain in text, f"{table.name}'s grain sentence is not on the page"
        for column in table.key:
            assert f"`{column}`" in text
        for source in table.source:
            assert f"`{source}`" in text
        assert table.coverage.strip().split("\n\n")[0] in text, (
            f"{table.name}'s coverage population is not stated"
        )


def test_every_withheld_field_is_accounted_for_named_or_counted() -> None:
    """*"the GM knows what it is not seeing"* — every one of them, but not every NAME.

    **Reconciled with the rating ban, and the reconciliation is the finding.** This used
    to assert every withheld field's name is on the page — which meant the first genuinely
    decoded true rating would have been *required* to publish into a public tracked file
    by the very test guarding the catalog. Rating-category fields are now accounted for by
    count; everything else is still named, because for a non-rating the value is landed
    and only its meaning is unsettled.
    """
    text = TRACKED_MARKDOWN.read_text(encoding="utf-8")
    declaration = contracts()
    structure = build_structure(declaration)
    withheld = [
        entry for entry in declaration.fields if disposition(entry) is not Disposition.RENDERABLE
    ]
    assert withheld, "no field is withheld at all, so this assertion is vacuous"

    # Nothing is lost between the two treatments.
    assert structure.withheld_field_count == len(withheld)

    for entry in withheld:
        if is_rating(entry):
            continue
        assert f"`{entry.name}`" in text, f"withheld field {entry.name} is not named"
        assert f"`{entry.epistemic}`" in text


def test_the_headline_field_count_means_what_it_says() -> None:
    """CF-01: `served` is bound-AND-renderable, not merely renderable.

    Re-derived here from the declaration rather than trusting the model, because the two
    definitions look identical until you ask whether a column claims the field — and the
    page's headline was wrong by 23 for exactly that reason.
    """
    declaration = contracts()
    structure = build_structure(declaration)

    bound = {
        column.field
        for table in declaration.tables
        for column in table.columns
        if column.field is not None
    }
    expected = sum(
        1
        for entry in declaration.fields
        if entry.name in bound and disposition(entry) is Disposition.RENDERABLE
    )
    renderable_anywhere = sum(
        1 for entry in declaration.fields if disposition(entry) is Disposition.RENDERABLE
    )

    assert structure.served_field_count == expected
    assert structure.served_field_count < renderable_anywhere, (
        "every renderable field is bound to a column, so the distinction this test exists "
        "to protect no longer has an instance — check that is really true before deleting"
    )
    # The three states partition the declaration.
    assert (
        structure.served_field_count
        + structure.withheld_field_count
        + len(structure.unexposed_fields)
        == structure.field_count
    ), "the three field states do not sum to the declared count, so one is unaccounted for"


def test_every_withheld_group_carries_its_argument() -> None:
    text = TRACKED_MARKDOWN.read_text(encoding="utf-8")
    groups = contracts().withheld
    assert groups, "the declaration withholds no group, so this assertion is vacuous"
    for group in groups:
        assert group.name in text
        summary, _ = summarise_reason(group.reason)
        assert " ".join(summary.split())[:60] in text


def test_the_report_pointer_names_the_files_the_renderers_write() -> None:
    """Scope Core §15 / SD-11 — and the pointer must not be a hand-kept path.

    Without this the USER-RUN criterion 20 is unreproducible by anyone who was not in the
    room. With a hand-kept path it is reproducible once and wrong afterwards, which is
    worse: a stale pointer sends the operator to an empty directory and reads as a
    pipeline failure.
    """
    text = TRACKED_MARKDOWN.read_text(encoding="utf-8")
    for filename in (ROSTER_FILENAME, CATALOG_MARKDOWN_FILENAME):
        assert f"/{filename}`" in text, f"the catalog does not say where {filename} lands"
    assert "$OOTP_OUTPUT_ROOT" in text, "the pointer names no .env key, so it resolves nothing"
    assert "uv run python -m ootp_ai.reports render" in text
    assert "uv run python -m ootp_ai.catalog" in text


def test_the_pointer_is_a_code_span_and_never_a_link_into_the_ignored_root() -> None:
    """`tests/test_doc_links.py` resolves every relative link in every tracked `.md`.

    The rendered reports live under a git-ignored root a fresh clone does not have, so a
    Markdown link to one can never resolve. Asserted here as well as there because the
    catalog is *generated*: the failure would arrive from a renderer edit, and pinning it
    beside the renderer's own tests is where the next author will see it.
    """
    text = TRACKED_MARKDOWN.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    assert not links, f"the tracked catalog carries Markdown links: {links}"


def test_the_spawn_contract_names_what_the_reports_cannot() -> None:
    """Plan step 7 (Decision P16). The umpire's framing message, recorded.

    The GM holds exactly `Read` and `Glob`, so the umpire's message is the whole delivery
    surface. The sim date and `ingest_seq` are on line one of each report; the period and
    the action budget are in no report at all, and an invocation omitting them asks for a
    plan against an unknown budget.
    """
    text = TRACKED_MARKDOWN.read_text(encoding="utf-8")
    assert "## The spawn contract" in text
    for blank in ("<club>", "<save_id>", "<YYYY-MM-DD>", "ingest_seq <n>", "Actions available"):
        assert blank in text, f"the spawn contract does not ask for {blank}"


def test_no_world_state_document_is_promised() -> None:
    """The scope's non-goal, pinned so the next author does not helpfully add one.

    A record/payroll/milestones page is a *third* report, and the scope rules it out —
    *"two is the deliberate 'how thin is thin' setting."* Watching the GM hit the limit of
    thin sight is the experiment.
    """
    structure = build_structure(contracts())
    assert len(structure.reports) == 2, (
        f"the catalog points at {len(structure.reports)} reports. A third is a scope "
        "amendment, not a catalog entry"
    )


# ── offline: the gate covers the columns the generated half reads ────────────


def test_every_coverage_column_is_declared_and_served() -> None:
    """Counts are a read of a column, and every read routes through the serving gate.

    `COVERAGE_COLUMNS` is the declared list `volume.py` checks before it queries anything.
    If it named a column the declaration does not have, the check would raise at runtime
    on a machine with a warehouse and pass in CI — so it is resolved here, where CI can
    see it.
    """
    declaration = contracts()
    assert COVERAGE_COLUMNS, "no coverage column is declared, so the gate guards nothing"
    for table_name, column_name in COVERAGE_COLUMNS:
        table = declaration.table(table_name)
        column = table.column(column_name)
        assert column_disposition(declaration, table, column) is Disposition.RENDERABLE, (
            f"{table_name}.{column_name} feeds a coverage statement and is not renderable"
        )


def test_the_generated_catalog_path_is_git_ignored() -> None:
    """The GM's copy names real counts and lands beside a report full of real names.

    The half CI can prove: the default root, at the actual path shape, for both files.
    """
    for filename in (CATALOG_MARKDOWN_FILENAME, CATALOG_JSON_FILENAME):
        candidate = DEFAULT_OUTPUT_ROOT / "Some-Save" / "2024-03-07" / "1" / filename
        assert _is_git_ignored(candidate), f"a generated {filename} at {candidate} is committable"


def test_the_tracked_catalog_is_not_ignored() -> None:
    """Anti-vacuity for the check above, and the split's other half.

    If `git check-ignore` answered yes to everything, the assertion above would pass while
    proving nothing — and the tracked catalog really must be tracked, because
    `tests/test_repo_structure.py` requires it to be on disk in a fresh clone.
    """
    assert not _is_git_ignored(TRACKED_MARKDOWN)
    assert not _is_git_ignored(TRACKED_JSON)


def test_the_tracked_json_is_a_document_a_machine_can_read() -> None:
    """Folded-in §4's whole justification: a consumer discovers tables without prose."""
    document = json.loads(TRACKED_JSON.read_text(encoding="utf-8"))
    names = {table["name"] for table in document["tables"]}
    assert names == {table.name for table in contracts().tables}
    assert "landing" not in document, "the tracked JSON carries a landing, which is volume"
    for table in document["tables"]:
        assert table["grain"].startswith("one row per ")
        assert table["key"]


# ── gamedata: the generated half, against a real landing ─────────────────────


@pytest.fixture(scope="module")
def settings() -> Settings:
    return settings_or_skip()


@pytest.fixture(scope="module")
def warehouse(settings: Settings) -> Iterator[Connection[DictCursor]]:
    with warehouse_or_skip(settings) as connection:
        yield connection


@pytest.fixture(scope="module")
def generated(settings: Settings, tmp_path_factory: pytest.TempPathFactory) -> CatalogFiles:
    """Both halves, written by `generate()` — the tracked pair into a temp directory.

    Redirected on purpose: this test must not rewrite the committed catalog as a side
    effect of running, and pointing `docs_root` at a temp directory also proves that
    `generate()` and `--structure-only` produce the same structural bytes.
    """
    try:
        return generate(settings, docs_root=tmp_path_factory.mktemp("docs"))
    except NoSuchSnapshot as exc:
        pytest.skip(f"nothing landed to describe: {exc}")


@pytest.fixture(scope="module")
def catalog_page(generated: CatalogFiles) -> str:
    assert generated.catalog_markdown is not None
    return generated.catalog_markdown.read_text(encoding="utf-8")


@pytest.mark.gamedata
def test_generate_writes_both_halves(generated: CatalogFiles) -> None:
    assert [path.name for path in generated.paths] == [
        TRACKED_MARKDOWN_FILENAME,
        TRACKED_JSON_FILENAME,
        CATALOG_MARKDOWN_FILENAME,
        CATALOG_JSON_FILENAME,
    ]
    assert all(path.is_file() for path in generated.paths)
    # The two Markdown halves are different files despite sharing a basename — the
    # property the role-keyed result exists to keep true.
    assert generated.catalog_markdown != generated.tracked_markdown


@pytest.mark.gamedata
def test_generate_writes_the_same_structural_bytes_as_the_committed_copy(
    generated: CatalogFiles,
) -> None:
    """One generator, and the tracked file is its volume-free output — from either path."""
    assert generated.tracked_markdown.read_bytes() == _committed(TRACKED_MARKDOWN)
    assert generated.tracked_json.read_bytes() == _committed(TRACKED_JSON)


@pytest.mark.gamedata
def test_every_landed_table_carries_its_row_count_and_snapshot_date(
    settings: Settings, warehouse: Connection[DictCursor], catalog_page: str
) -> None:
    """AC15's generated clauses, all seven, against the landing actually described."""
    declaration = contracts()
    ref = resolve_snapshot(warehouse, save_id=settings.managed.save_id)
    volume = fetch_volume(warehouse, declaration, ref)

    assert str(ref.sim_date) in catalog_page, "the page does not name the snapshot date"
    assert f"**Ingest seq** {ref.ingest_seq}" in catalog_page
    assert ref.save_id in catalog_page

    for table in declaration.tables:
        assert f"### `{table.name}`" in catalog_page
        assert table.grain in catalog_page
        for source in table.source:
            assert f"`{source}`" in catalog_page

    landed = [entry for entry in volume.tables if entry.landed]
    assert landed, "the landing holds no declared table, so there is nothing to describe"
    for entry in landed:
        assert entry.row_count is not None
        assert f"{entry.row_count:,}" in catalog_page, (
            f"{entry.name} landed {entry.row_count} rows and the page does not say so"
        )


@pytest.mark.gamedata
def test_the_coverage_statement_prices_the_players_no_roster_list_holds(
    settings: Settings, warehouse: Connection[DictCursor], catalog_page: str
) -> None:
    """AC15 names this one explicitly, and it is the gap the GM is likeliest to hit.

    The figure is recomputed here with a query this module owns, so the assertion is that
    the page states the *right* number rather than that it states one.
    """
    ref = resolve_snapshot(warehouse, save_id=settings.managed.save_id)
    with warehouse.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM {quote_ident('bronze_player')} p "
            f"WHERE p.{quote_ident('save_id')} = %s "
            f"AND p.{quote_ident('sim_date')} = %s "
            f"AND p.{quote_ident('ingest_seq')} = %s "
            f"AND p.{quote_ident('player_id')} NOT IN ("
            f"SELECT r.{quote_ident('player_id')} FROM {quote_ident('bronze_team_roster')} r "
            f"WHERE r.{quote_ident('save_id')} = %s "
            f"AND r.{quote_ident('sim_date')} = %s "
            f"AND r.{quote_ident('ingest_seq')} = %s)",
            (*ref.triple, *ref.triple),
        )
        row = cursor.fetchone()
    assert row is not None
    unlisted = int(row["total"])
    assert unlisted > 0, "every player holds a roster row, so the gap this states is not real"

    assert f"**{unlisted:,}** players hold **no** roster row" in catalog_page, (
        f"the catalog does not state that {unlisted:,} players hold no roster row. That "
        'population is what makes "who is available" a known gap rather than a zero'
    )


@pytest.mark.gamedata
def test_no_player_level_value_reaches_the_catalog(
    settings: Settings, warehouse: Connection[DictCursor], catalog_page: str
) -> None:
    """AC15's other absolute clause, checked against the rows that actually landed.

    Names and ids are sampled from the same landing the page describes. A name short
    enough to be a substring of ordinary English proves nothing when absent, and an id
    small enough to be a row count proves nothing either — both are filtered out so that
    what remains is a statement about the page.
    """
    ref = resolve_snapshot(warehouse, save_id=settings.managed.save_id)
    with warehouse.cursor() as cursor:
        # FULL first-and-last display names, over the WHOLE landed player population —
        # not a `LIMIT 500` window of single name-table tokens.
        #
        # The first version of this test did the latter and was wrong in both directions
        # at once. Near-blind: 500 consecutive rows with no ORDER BY is 0.2% of one
        # alphabetical band (Aalto..Akrodhana, measured). And a false-red landmine: single
        # tokens like `Walker`, `Grain`, `Field`, `Label`, `Boston` and `Lahman` are real
        # surnames AND words this renderer emits on every table block, so widening the
        # window would have turned the guard red on a correct catalog — the failure the
        # plan names twice as the most expensive kind.
        #
        # A two-token display name cannot collide with the catalog's vocabulary, so this
        # is both exhaustive and quiet.
        # `name_join_predicate` rather than a hand-written ON clause: it binds EVERY column
        # of `bronze_name`'s declared key, `name_space` included. The first draft here
        # omitted `name_space` — the precise defect `reports/roster.py` documents and
        # guards against, where a second name space pairs every first name with every last
        # name. Correct today only by circumstance (one space is landed), and it also made
        # the query unable to use the primary key: measured, it had not finished in ten
        # minutes, while this form returns in seconds.
        cursor.execute(
            f"SELECT CONCAT(fn.{quote_ident('name_text')}, ' ', "
            f"ln.{quote_ident('name_text')}) AS value "
            f"FROM {quote_ident('bronze_player')} p "
            f"JOIN {quote_ident('bronze_name')} fn "
            f"ON {name_join_predicate('fn', 'first_name_index')} "
            f"JOIN {quote_ident('bronze_name')} ln "
            f"ON {name_join_predicate('ln', 'last_name_index')} "
            f"WHERE p.{quote_ident('save_id')} = %s "
            f"AND p.{quote_ident('sim_date')} = %s "
            f"AND p.{quote_ident('ingest_seq')} = %s "
            f"AND CHAR_LENGTH(fn.{quote_ident('name_text')}) >= %s "
            f"AND CHAR_LENGTH(ln.{quote_ident('name_text')}) >= %s",
            (
                SINGLE_NAME_SPACE,
                SINGLE_NAME_SPACE,
                *ref.triple,
                MIN_SAMPLED_NAME_LEN,
                MIN_SAMPLED_NAME_LEN,
            ),
        )
        names = [str(row["value"]) for row in cursor.fetchall()]

        # Ids are still bounded below rather than sampled: every one above the floor is
        # checked, and the floor exists because `30`, `96` and `259` appear in the
        # catalog's own prose as counts.
        cursor.execute(
            f"SELECT {quote_ident('player_id')} AS value FROM {quote_ident('bronze_player')} "
            f"WHERE {quote_ident('save_id')} = %s "
            f"AND {quote_ident('sim_date')} = %s "
            f"AND {quote_ident('ingest_seq')} = %s "
            f"AND {quote_ident('player_id')} >= %s",
            (*ref.triple, MIN_SAMPLED_PLAYER_ID),
        )
        ids = [int(row["value"]) for row in cursor.fetchall()]

    assert len(names) > 1000, f"only {len(names)} names resolved; this scan would be vacuous"
    assert len(ids) > 1000, f"only {len(ids)} player ids; this scan would be vacuous"

    leaked_names = [name for name in names if name in catalog_page]
    assert not leaked_names, (
        f"{len(leaked_names)} landed player name(s) appear in the catalog: "
        f"{leaked_names[:10]}. The catalog describes the shape of the warehouse; the "
        "roster report describes its contents, and only one of the two may name a person"
    )

    on_page = set(re.findall(r"\d+", catalog_page.replace(",", "")))
    leaked_ids = sorted(value for value in ids if str(value) in on_page)
    assert not leaked_ids, f"player id(s) appear in the catalog: {leaked_ids[:10]}"


@pytest.mark.gamedata
def test_regenerating_the_same_landing_is_byte_identical(
    settings: Settings, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """AC15's last clause. The generated half is idempotent per triple, like the reports.

    `ingested_at` and `parse_seconds` come out of the `ingest_run` row rather than off a
    clock, which is what makes this hold — a freshness figure read from the present moment
    would differ between two runs a second apart and say nothing true about the landing.
    """
    first = generate(settings, docs_root=tmp_path_factory.mktemp("docs-a"))
    # Captured BEFORE the second run, because the generated half is written to a path that
    # is a pure function of settings + ref — so the second `generate()` overwrites it and
    # a naive zip-compare afterwards reads the same file twice. Measured at the Phase 11
    # panel: two runs writing deliberately different bytes still passed. The generated
    # half is the only one with a clock and a live database behind it, which makes it the
    # only half where non-determinism could arise and the one that had no real assertion.
    captured = {path: path.read_bytes() for path in first.paths}

    second = generate(settings, docs_root=tmp_path_factory.mktemp("docs-b"))
    assert first.catalog_markdown == second.catalog_markdown, (
        "the generated half no longer writes to a stable path, so `captured` is comparing "
        "different files and this test has stopped asserting determinism"
    )

    for path, before in captured.items():
        assert path.read_bytes() == before, f"{path.name} differs between two runs"

    # And the tracked pair, which really are two different files in two temp directories.
    assert first.tracked_markdown.read_bytes() == second.tracked_markdown.read_bytes()
    assert first.tracked_json.read_bytes() == second.tracked_json.read_bytes()


@pytest.mark.gamedata
def test_the_written_catalog_is_git_ignored(generated: CatalogFiles) -> None:
    """The resolved path, not merely the default root."""
    for path in (generated.catalog_markdown, generated.catalog_json):
        assert path is not None
        if path.resolve().is_relative_to(REPO_ROOT):
            assert _is_git_ignored(path), f"{path} is not git-ignored"


@pytest.mark.gamedata
def test_no_rating_name_reaches_the_gm_copy(generated: CatalogFiles) -> None:
    """CF-10. AC15 says *anywhere in it*, and the GM's copy is the `it` that matters most.

    The offline scan covers the two tracked `docs/` files. Those are read by engineers;
    this is the page handed to the GM, and until now no test looked at it — nor at
    `catalog.json` beside it. The generated half also carries sections the tracked half
    does not, so the two are not the same document with different headers.
    """
    for path in (generated.catalog_markdown, generated.catalog_json):
        assert path is not None
        assert_no_rating_name(path.read_text(encoding="utf-8"), str(path.name))


@pytest.mark.gamedata
def test_the_generated_json_carries_the_landing(generated: CatalogFiles) -> None:
    """The discovery surface a future advisor reads instead of parsing prose."""
    assert generated.catalog_json is not None
    document: dict[str, Any] = json.loads(generated.catalog_json.read_text(encoding="utf-8"))

    landing = document["landing"]
    assert landing["ingest_seq"] >= 1
    assert landing["row_counts"], "the landing names no row count"
    assert landing["coverage"], "the landing names no coverage figure"
    assert landing["sim_date"] in landing["landed_sim_dates"]
