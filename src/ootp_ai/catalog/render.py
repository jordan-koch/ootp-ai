"""One generator, two renderings, and — with the volume attached or not — two files.

`render_markdown(structure)` is byte-for-byte what `docs/warehouse-catalog.md` holds;
`render_markdown(structure, volume)` is the GM's copy, the same page with the landing's
counts folded in. That they come from one function is the whole reason the split is safe:
the tracked half cannot describe a schema the generated half contradicts, because there is
no second renderer to drift.

## Why the tracked half carries no path and no link into the output root

`tests/test_doc_links.py` resolves every relative Markdown link in every tracked `.md` and
`tests/test_no_leaks.py` bans drive letters and home directories outright. The rendered
reports live under a git-ignored root that a fresh clone does not have, so a link to one
is a link that can never resolve. Every pointer here is therefore a **code span** naming
an `.env` key and a path *shape* — `<save_id>/<sim_date>/<ingest_seq>/roster.md` — which
is the durable fact anyway: the resolved path is machine-specific and this repo is public.
"""

from __future__ import annotations

import json
from typing import Any

from ootp_ai.catalog.structure import Structure, TableEntry
from ootp_ai.catalog.volume import TableVolume, Volume

__all__ = [
    "SCHEMA_VERSION",
    "render_json",
    "render_markdown",
]

#: Bumped when the JSON shape changes in a way a consumer must notice. The Markdown has no
#: such version: it is read by an agent, and an agent reads the prose.
SCHEMA_VERSION = 1

_GENERATOR = "uv run python -m ootp_ai.catalog"


def render_markdown(structure: Structure, volume: Volume | None = None) -> str:
    """The catalog page. With `volume`, the GM's copy; without it, the tracked half."""
    lines: list[str] = []
    lines.extend(_header(volume))
    lines.extend(_landing_section(volume))
    lines.extend(_tables_section(structure, volume))
    lines.extend(_coverage_section(volume))
    lines.extend(_withheld_section(structure))
    lines.extend(_reports_section(structure))
    lines.extend(_spawn_contract())
    return "\n".join(lines).rstrip() + "\n"


def render_json(structure: Structure, volume: Volume | None = None) -> str:
    """The machine-readable sibling (scope folded-in §4).

    `sort_keys` and a fixed indent, so the tracked copy is byte-stable across Python
    versions and dict-ordering changes for exactly the same reason the Markdown is.
    """
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": _GENERATOR,
        # Three states, summing to `declared`. The first version reported two and made
        # `withheld` a subtraction, which is how 23 fields that reach no page were counted
        # as reaching one.
        "fields": {
            "declared": structure.field_count,
            "bound_to_a_column": structure.bound_field_count,
            "served": structure.served_field_count,
            "withheld": structure.withheld_field_count,
            "unexposed": len(structure.unexposed_fields),
        },
        "tables": [_table_json(table) for table in structure.tables],
        "withheld_groups": [
            {
                "name": group.name,
                "source": group.source,
                "summary": group.summary,
                "truncated": group.truncated,
                "adrs": list(group.adrs),
            }
            for group in structure.withheld_groups
        ],
        "withheld_fields": [
            {
                "name": field.name,
                "source": field.source,
                "disposition": field.disposition,
                "category": field.category,
                "epistemic": field.epistemic,
            }
            for field in structure.withheld_fields
        ],
        # Counted by source, never named — the same rule the Markdown follows, because a
        # machine-readable copy that listed what the page redacts would make the redaction
        # decorative.
        #
        # Named `rating_category_counts` and not `withheld_rating_fields`, which is what it
        # was called first: that spelling is identifier-shaped and `RATING_NAME_PATTERN`
        # rejected it. Renaming rather than exempting was the cheaper of the two, and it
        # keeps the scan absolute — an exemption list is the thing that would eventually be
        # widened to admit a real rating.
        "rating_category_counts": dict(structure.withheld_rating_counts),
        "unexposed_fields": [
            {
                "name": field.name,
                "source": field.source,
                "category": field.category,
                "epistemic": field.epistemic,
            }
            for field in structure.unexposed_fields
        ],
        "reports": [
            {
                "logical_name": report.logical_name,
                "filename": report.filename,
                "env_key": report.env_key,
                "relative_path": report.relative_path,
                "command": report.command,
            }
            for report in structure.reports
        ],
    }
    if volume is not None:
        document["landing"] = _volume_json(volume)
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ── markdown ─────────────────────────────────────────────────────────────────


def _header(volume: Volume | None) -> list[str]:
    lines = ["# Warehouse catalog — what is landed, and what is deliberately not", ""]
    if volume is None:
        lines.extend(
            [
                "> **Generated. Do not edit by hand.** "
                f"`{_GENERATOR}` rewrites this file from "
                "`src/ootp_ai/contracts/tables.toml` and "
                "`src/ootp_ai/contracts/field_map.toml`. "
                "`tests/test_catalog.py` rebuilds it during the test run and refuses any "
                "byte that differs, so a hand edit here is red before it is stale.",
                "",
                "This is the **structural half**: table names, grains, keys, coverage "
                "populations, source files, epistemic labels, the withheld groups and "
                "where the rendered reports land. It is derived schema knowledge, which "
                "ADR 0006 tracks deliberately, so it survives a fresh clone with no game, "
                "no save and no database.",
                "",
                "**No figure on this page is computed from a landing.** Row counts, "
                "snapshot dates and freshness generate into the git-ignored output root "
                "beside the reports — see *Where the reports are*, below. Read that copy "
                "to learn what a particular snapshot holds; read this one to learn what "
                "the warehouse is *shaped* like.",
                "",
                "**The coverage notes below do quote numbers, and those numbers are "
                "historical.** They are measured records copied from "
                "`src/ootp_ai/contracts/tables.toml`, describing the save they were "
                "measured on — usually the probe. They are *not* this warehouse's current "
                "contents and will disagree with the generated copy whenever the league "
                "has moved. Where the two differ, the generated copy is the one that "
                "counted.",
                "",
            ]
        )
        return lines

    club = "unknown club" if volume.human_team_id is None else f"team {volume.human_team_id}"
    lines.extend(
        [
            f"**Save** `{volume.save_id}` · **Sim date** {volume.sim_date} · "
            f"**Ingest seq** {volume.ingest_seq} · **Managed club** {club}",
            "",
            f"Generated by `{_GENERATOR}` from the warehouse landing "
            f"`({volume.save_id}, {volume.sim_date}, {volume.ingest_seq})`. Every "
            "**computed** figure below — every row count, and every line under *Coverage, "
            "computed from this landing* — is that landing and no other.",
            "",
            "**One exception, and it is signposted rather than cleaned up.** Each table's "
            "*Coverage (as declared)* note is prose copied from "
            "`src/ootp_ai/contracts/tables.toml`, and several quote counts measured on "
            "the probe save. Those are historical records, not this landing: where a "
            "declared note and a computed figure disagree about the same population, the "
            "computed one counted and the declared one remembered.",
            "",
            "This page answers two questions: **what the warehouse holds**, and **what was "
            "deliberately withheld and why**. The second is the one a list of tables "
            "cannot give you — an action priced against a gap you can see is a different "
            "action from one priced against a gap you discover by hitting it.",
            "",
        ]
    )
    return lines


def _landing_section(volume: Volume | None) -> list[str]:
    if volume is None:
        return []
    lines = ["## This landing", ""]
    lines.append(f"- **Ingested at** — {volume.ingested_at or 'not recorded'}")
    if volume.parse_seconds is not None:
        lines.append(
            f"- **Parse cost** — {volume.parse_seconds:.3f} s of wall clock for the walk "
            "(AC17: the number is recorded, and there is no threshold — the work takes as "
            "long as it needs)."
        )
    lines.append(f"- **Rows in this landing** — {volume.total_rows:,} across every declared table.")
    dates = ", ".join(volume.landed_dates) if volume.landed_dates else "none"
    lines.extend(
        [
            f"- **In-game dates this universe has landed** — {dates}. Bronze is "
            "append-only (ADR 0021): a second look at one date takes the next "
            "`ingest_seq` and lands beside its predecessor, never over it.",
            "",
        ]
    )

    if volume.source_files:
        lines.extend(
            [
                "### What the parse read",
                "",
                "| File | Bytes | Unaccounted bytes |",
                "|---|---:|---:|",
            ]
        )
        for source in volume.source_files:
            left = "—" if source.residual_bytes is None else f"{source.residual_bytes:,}"
            lines.append(f"| `{source.name}` | {source.size:,} | {left} |")
        lines.extend(
            [
                "",
                "*Unaccounted bytes* is what the walk framed but did not claim — a "
                "diagnostic, not an error. Nothing in this project reads a fixed offset, "
                "so a region nobody has mapped is simply skipped and counted.",
                "",
            ]
        )
    return lines


def _tables_section(structure: Structure, volume: Volume | None) -> list[str]:
    counts = {table.name: table for table in (volume.tables if volume else ())}
    columns = sum(table.column_count for table in structure.tables)
    unexposed = len(structure.unexposed_fields)
    lines = [
        "## The tables",
        "",
        f"{len(structure.tables)} tables are declared, carrying {columns} columns between them.",
        "",
        f"Of {structure.field_count} declared fields, **{structure.served_field_count} can "
        f"reach a page** — bound to a declared column *and* released by the serving gate. "
        f"{structure.withheld_field_count} are withheld by the gate, and {unexposed} are "
        "read by a walker but claimed by no column, so nothing lands them and nothing can "
        "print them. All three groups are accounted for under *What is withheld* below.",
        "",
    ]
    for table in structure.tables:
        lines.extend(_table_block(table, counts.get(table.name)))
    return lines


def _table_block(table: TableEntry, volume: TableVolume | None = None) -> list[str]:
    lines = [f"### `{table.name}`", ""]
    lines.append(f"- **Grain** — {table.grain}")
    lines.append(f"- **Key** — {_code_list(table.key)}")
    lines.append(f"- **Source** — {_code_list(table.source)}")
    lines.append(f"- **Walker** — `{table.walker}`")

    if volume is not None:
        if not volume.landed or volume.row_count is None:
            lines.append(
                "- **Rows** — **not landed by this run.** The table is declared, and this "
                "landing's `ingest_run` row does not account for it — so it was created "
                "after this snapshot was taken, or the walker that fills it did not exist "
                "yet. Not landed is a different fact from landed empty, and this line is "
                "the first rather than a count of zero."
            )
        else:
            lines.append(f"- **Rows in this landing** — {volume.row_count:,}")

    served = f"{table.served_columns} of {table.column_count} columns reach a page"
    if table.provenance_columns:
        served += f"; {table.provenance_columns} are provenance (ours, not the game's)"
    lines.append(f"- **Columns** — {served}.")

    if table.label_counts:
        labels = ", ".join(f"{label} {count}" for label, count in table.label_counts)
        weakest = table.weakest_label
        sentence = f"- **Epistemic labels** — {labels}."
        if len(table.label_counts) > 1:
            # Only worth saying when the labels actually disagree. On a table whose columns
            # are uniformly `verified`, "weakest: verified, however many verified columns
            # sit beside it" is a sentence that argues with itself.
            sentence += (
                f" Weakest: `{weakest}` — which is what the table as a whole is worth, "
                "however many better-evidenced columns sit beside it."
            )
        lines.append(sentence)
    else:
        lines.append(
            "- **Epistemic labels** — none: every column is provenance rather than a "
            "belief about a game fact."
        )

    # "as declared" is load-bearing, not a caption. This prose is hand-maintained in
    # `tables.toml` and several notes quote counts measured on the probe save — the GM's
    # copy would otherwise state 10,700 and a computed 12,426 for one population, thirty
    # lines apart, under a header promising every figure is this landing.
    lines.append(_bullet("Coverage (as declared)", table.coverage))
    if table.note:
        lines.append(_bullet("Note", table.note))

    if table.withheld_columns:
        lines.append("- **Not served** —")
        for column in table.withheld_columns:
            lines.append(f"  - `{column.column}` is **{column.disposition}**: {column.reason}.")
    lines.append("")
    return lines


def _coverage_section(volume: Volume | None) -> list[str]:
    if volume is None or not volume.coverage:
        return []
    lines = [
        "## Coverage, computed from this landing",
        "",
        "Every figure here is counted from the rows described above. None is remembered "
        "from another save, another date or an export.",
        "",
    ]
    lines.extend(f"- {fact.statement}" for fact in volume.coverage)
    lines.append("")
    return lines


def _withheld_section(structure: Structure) -> list[str]:
    lines = [
        "## What is withheld, and why",
        "",
        "The half a list of landed tables cannot give you. A gap named here is a gap the "
        "GM can price an action against; a gap discovered by hitting it is a wasted "
        "action and a wrong belief in between.",
        "",
        "### Groups never landed",
        "",
        "| Group | Source | ADR | Why |",
        "|---|---|---|---|",
    ]
    for group in structure.withheld_groups:
        adrs = ", ".join(f"ADR {number}" for number in group.adrs) if group.adrs else "—"
        summary = _cell(group.summary) + (" *(…)*" if group.truncated else "")
        lines.append(f"| {_cell(group.name)} | `{group.source}` | {adrs} | {summary} |")
    lines.extend(
        [
            "",
            "The full argument for each is in `src/ootp_ai/contracts/field_map.toml` under "
            "`[[withheld]]`. What is reproduced above stops at the first sentence naming a "
            "column this catalog may not print — the declaration is a working note and "
            "names them freely, and a catalog that quoted it whole would publish exactly "
            "the names the serving gate exists to keep off a page.",
            "",
            "### Rating-category fields — counted, never named",
            "",
            f"{sum(count for _, count in structure.withheld_rating_counts)} declared "
            "fields carry a rating category and are withheld. **This catalog does not "
            "print their names**, and that is structural rather than editorial: an "
            "**unclassified** field is recorded as a true rating rather than as *unknown* "
            "— ADR 0012's withhold-by-default posture, in which *probably fine* is not a "
            "classification — so naming every withheld field is exactly what would "
            "publish the first genuinely decoded true rating. The declaration holds the "
            "names; `src/ootp_ai/contracts/field_map.toml` is where an engineer reads "
            "them.",
            "",
            "| Source | Withheld fields |",
            "|---|---:|",
        ]
    )
    for source, count in structure.withheld_rating_counts:
        lines.append(f"| `{source}` | {count} |")

    lines.extend(
        [
            "",
            "### Other fields the serving gate does not release",
            "",
            f"{_count_phrase(len(structure.withheld_fields), 'declared field')} whose "
            "category is not a rating. These are named: the value is landed and only its "
            "*meaning* is unsettled, so knowing which one it is costs nothing and tells "
            "the GM where the page is guessing.",
            "",
            "| Field | Source | Decision | Category | Label |",
            "|---|---|---|---|---|",
        ]
    )
    for field in structure.withheld_fields:
        lines.append(
            f"| `{field.name}` | `{field.source}` | {field.disposition} | "
            f"`{field.category}` | `{field.epistemic}` |"
        )

    lines.extend(_unexposed_block(structure))
    return lines


def _unexposed_block(structure: Structure) -> list[str]:
    """Read by a walker, landed by nothing — the third state, and the one that was lost.

    These fields would pass the serving gate; no declared table claims them, so they reach
    no page anyway. Counting them as *served* is what made the headline figure overstate
    the GM's sight by 23 fields, and dropping them silently would have been the same error
    wearing a tidier number.
    """
    lines = [
        "",
        "### Read, but landed by nothing",
        "",
        f"{_count_phrase(len(structure.unexposed_fields), 'declared field')} that the "
        "serving gate would release and **no declared column claims**. The walker reads "
        "them and proves them; "
        "nothing lands them, so nothing can print them. They are here because a field "
        "somebody verified and chose not to surface is a gap the GM can price — and "
        "because counting them as served is precisely the mistake this section exists to "
        "stop repeating.",
        "",
        "| Field | Source | Category | Label |",
        "|---|---|---|---|",
    ]
    for field in structure.unexposed_fields:
        lines.append(
            f"| `{field.name}` | `{field.source}` | `{field.category}` | `{field.epistemic}` |"
        )
    lines.append("")
    return lines


def _reports_section(structure: Structure) -> list[str]:
    lines = [
        "## Where the reports are",
        "",
        "Rendered reports are **not** in this repository and never will be: they name real "
        "players, and this repo is public (ADR 0006). They resolve under a git-ignored "
        "root named by an `.env` key, partitioned by the snapshot triple they were "
        "rendered from — so a later date or a later sequence writes a new directory beside "
        "the old one rather than over it, and the exact bytes the GM read are still on "
        "disk when a decision citing them is checked months later.",
        "",
        "| Report | Resolves under | Path within it | Rendered by |",
        "|---|---|---|---|",
    ]
    for report in structure.reports:
        lines.append(
            f"| {report.logical_name} | `${report.env_key}` | "
            f"`{report.relative_path}` | `{report.command}` |"
        )
    lines.append("")
    return lines


def _spawn_contract() -> list[str]:
    """The umpire's framing message, recorded because the GM's context *is* the delivery.

    Plan Phase 11 step 7 (amendment, Decision P16). The pointer above says where the
    reports are; it does not say what the umpire says when handing them over — and the GM
    subagent holds exactly `Read` and `Glob`, so whatever the umpire puts in its context
    is the entire delivery surface. This is free infrastructure under ADR 0016: it conveys
    existence and provenance, never analytical direction.

    It is deliberately **not** generated from anything. There is no world-state or
    "situation" document behind it: that would be a third report, and the scope rules one
    out — *"two is the deliberate 'how thin is thin' setting."* Watching the GM hit the
    limit of thin sight is the experiment; pre-empting it is not.
    """
    return [
        "## The spawn contract",
        "",
        "What the umpire says when handing the GM its reports. The `gm` subagent holds "
        "exactly `Read` and `Glob` and cannot query anything (ADR 0016), so its context is "
        "the whole delivery surface — an attachment nobody framed is an attachment the GM "
        "cannot date, attribute or trust. Fill in the blanks; add nothing analytical.",
        "",
        "```text",
        "You are the General Manager of <club>, in league <league>.",
        "",
        "Attached for this invocation:",
        "  - <report name> — rendered from save <save_id>, sim date <YYYY-MM-DD>,",
        "    ingest_seq <n>.",
        "  - <report name> — same landing.",
        "",
        "The reports describe that landing and no other. Anything that has happened in",
        "the league since is not in them.",
        "",
        "Period: <period>. Actions available: <n of m>. Actions already spent: <list>.",
        "",
        "Return your handoff in the standard sections.",
        "```",
        "",
        "**Every blank is a fact the GM cannot otherwise obtain.** The sim date and "
        "`ingest_seq` are on line one of each report, but the *period* and the *action "
        "budget* are not in any report and the GM has no way to read them — an invocation "
        "that omits them is asking for a plan against an unknown budget.",
        "",
    ]


# ── json ─────────────────────────────────────────────────────────────────────


def _table_json(table: TableEntry) -> dict[str, Any]:
    return {
        "name": table.name,
        "grain": table.grain,
        "key": list(table.key),
        "source": list(table.source),
        "walker": table.walker,
        "coverage": table.coverage,
        "note": table.note,
        "columns": {
            "declared": table.column_count,
            "served": table.served_columns,
            "provenance": table.provenance_columns,
        },
        "epistemic_labels": dict(table.label_counts),
        "weakest_label": table.weakest_label,
        "not_served": [
            {
                "column": column.column,
                "disposition": column.disposition,
                "category": column.category,
                "epistemic": column.epistemic,
            }
            for column in table.withheld_columns
        ],
    }


def _volume_json(volume: Volume) -> dict[str, Any]:
    return {
        "save_id": volume.save_id,
        "sim_date": volume.sim_date,
        "ingest_seq": volume.ingest_seq,
        "human_team_id": volume.human_team_id,
        "ingested_at": volume.ingested_at,
        "parse_seconds": volume.parse_seconds,
        "landed_sim_dates": list(volume.landed_dates),
        "row_counts": {table.name: table.row_count for table in volume.tables if table.landed},
        "declared_but_absent": [table.name for table in volume.tables if not table.landed],
        "coverage": {fact.name: fact.value for fact in volume.coverage},
        "source_files": [
            {
                "name": source.name,
                "size": source.size,
                "residual_bytes": source.residual_bytes,
            }
            for source in volume.source_files
        ],
    }


def _code_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def _count_phrase(count: int, noun: str) -> str:
    """`1 declared field` / `23 declared fields`.

    Generated prose still gets read by a person — the GM — and `1 declared field(s)` on a
    page whose whole job is to be trusted reads like nobody looked at the output.
    """
    return f"{count:,} {noun}" if count == 1 else f"{count:,} {noun}s"


def _bullet(label: str, body: str) -> str:
    """A list item whose body may be several paragraphs, kept inside the list.

    `tables.toml` states several coverage notes as multi-paragraph prose — the whole
    argument for a grain, not a caption — and pasting one after `- **Coverage** —`
    verbatim ends the list at the first blank line, so the remaining paragraphs render as
    unattached body text under the wrong heading. Continuation lines are indented to the
    list item's content column instead, which is what keeps them attached.
    """
    paragraphs = [part.strip() for part in body.strip().split("\n\n") if part.strip()]
    if not paragraphs:
        return f"- **{label}** —"
    head, *rest = paragraphs
    lines = [f"- **{label}** — {head}"]
    lines.extend(f"\n  {paragraph}" for paragraph in rest)
    return "\n".join(lines)


def _cell(text: str) -> str:
    """One table cell: no pipe may survive, and no newline.

    Both come from declared prose this module does not control. A pipe would silently add
    a column to the row and shift every value one place left — the kind of corruption that
    looks like a rendering quirk and reads as data.
    """
    return " ".join(text.split()).replace("|", "\\|")
