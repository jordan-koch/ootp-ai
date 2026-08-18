"""The link guard's contract, as five skills promise it to artifact authors.

`tests/test_doc_links.py` is the repo-wide scanner; this module is the unit test of the
rules it applies. They are separated because the scanner's verdict depends on what is
on disk, while these four rules must hold against fixture strings alone — which is the
only way to prove a rule is implemented rather than merely never exercised.

The four promises, quoted from `.claude/skills/make-feature-request/SKILL.md:245-250`
and the four sibling copies: fenced content is exempt "precisely so a report can quote
a dead target"; "citations may carry a `file.py:123` suffix"; "`var/` targets are
exempt too"; and — in four of the five copies — "every relative link **and bare
`requests/...` token** you write must resolve on disk".

None of the four was implemented. Authors who followed the documentation got a red
build, and the repo grew a code-span citation convention to work around it. See
`requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md`.
"""

from __future__ import annotations

from pathlib import Path

import test_doc_links as guard

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- Promise 1: fenced content is exempt ------------------------------------------


def test_a_link_inside_a_fenced_block_is_exempt() -> None:
    """The reason this exists: a report must be able to quote a dead target."""
    text = "\n".join(
        [
            "Live text with [a real link](test_doc_links.py).",
            "",
            "```",
            "[a dead target](requests/feature-requests/not-yet/PROJECT_SCOPE.md)",
            "```",
            "",
            "More live text.",
        ]
    )
    targets = guard.link_targets(guard.strip_fences(text))
    assert "test_doc_links.py" in targets, "the live link outside the fence must still be seen"
    assert not [t for t in targets if "not-yet" in t], (
        "a link inside a fence must be exempt — quoting a dead target is the documented use"
    )


def test_a_tilde_fence_and_a_blockquoted_fence_are_both_exempt() -> None:
    """The promise names both markers and says "blockquoted is fine"."""
    text = "\n".join(
        [
            "~~~",
            "[dead](requests/gone/A.md)",
            "~~~",
            "> ```",
            "> [also dead](requests/gone/B.md)",
            "> ```",
        ]
    )
    assert guard.link_targets(guard.strip_fences(text)) == []


def test_stripping_a_fence_keeps_the_line_count_stable() -> None:
    """Blanking rather than deleting, so any future line-numbered report stays honest."""
    text = "a\n```\nb\n```\nc"
    assert len(guard.strip_fences(text).splitlines()) == len(text.splitlines())


def test_a_fence_opened_inside_a_list_item_closes_again() -> None:
    """Missing this form does not lose one block — it flips parity for the whole file.

    `.claude/skills/commit/SKILL.md:189` is literally "2. ```". An earlier draft of the
    FENCE pattern required the marker at the start of the line (after blockquote markers
    only), so that opener never registered, its closer opened a fence instead, and every
    line to EOF read as fenced. Measured: 76 of that file's 194 non-blank lines were
    silently dropped from the scan, and a broken link after them went unreported. A guard
    that quietly stops checking is the failure class this whole request exists to remove.
    """
    text = "\n".join(
        [
            "1. Some step:",
            "",
            "2. ```",
            "   git commit -F var/commit-msg.txt",
            "   ```",
            "",
            "[a live broken link](does-not-exist-anywhere.md)",
        ]
    )
    targets = guard.link_targets(guard.strip_fences(text))
    assert targets == ["does-not-exist-anywhere.md"], (
        "a fence opened on a list-item line must close, or everything after it is "
        f"silently exempt (saw {targets})"
    )


def test_a_bulleted_fence_closes_too() -> None:
    text = "- ```\n  code\n  ```\n[live](does-not-exist.md)"
    assert guard.link_targets(guard.strip_fences(text)) == ["does-not-exist.md"]


# --- Promise 2: a citation may carry a file.py:123 suffix -------------------------


def test_a_citation_with_a_line_suffix_resolves_to_the_file() -> None:
    resolved = guard.resolve_target("test_doc_links.py:38", REPO_ROOT / "tests")
    assert resolved is not None and resolved.exists(), (
        "a `file.py:123` citation must resolve to the file — the suffix is a line number, not a path"
    )


def test_a_citation_with_a_line_range_resolves_too() -> None:
    for suffix in (":10-20", ":10\u201320"):
        resolved = guard.resolve_target(f"test_doc_links.py{suffix}", REPO_ROOT / "tests")
        assert resolved is not None and resolved.exists(), f"a {suffix} range must resolve"


def test_a_genuinely_dead_target_is_still_dead_with_a_suffix() -> None:
    """Stripping the suffix must not become a way to launder a broken path."""
    resolved = guard.resolve_target("no_such_file_at_all.py:12", REPO_ROOT / "tests")
    assert resolved is not None and not resolved.exists()


# --- Promise 3: link titles are exempt --------------------------------------------


def test_a_link_title_is_not_part_of_the_path() -> None:
    """The fifth promise, carried by three skills: "link titles are exempt too".

    `[the ADR](docs/decisions/0001-....md "ADR 0001")` — the quoted title is Markdown
    link syntax, not path. Measured against the shipped code before this landed: the
    titled form resolved to exists=False while the untitled control resolved True.
    """
    doc = "docs/decisions/0001-read-only-no-write-back.md"
    control = guard.resolve_target(doc, REPO_ROOT)
    assert control is not None and control.exists(), "control: the untitled path resolves"

    for titled in (f'{doc} "ADR 0001"', f"{doc} 'ADR 0001'", f"{doc} (ADR 0001)"):
        resolved = guard.resolve_target(titled, REPO_ROOT)
        assert resolved is not None and resolved.exists(), f"a title must be stripped: {titled}"


def test_a_title_does_not_launder_a_dead_path() -> None:
    resolved = guard.resolve_target('no_such_doc.md "Nice Title"', REPO_ROOT)
    assert resolved is not None and not resolved.exists()


# --- Promise 4: var/ targets are exempt -------------------------------------------


def test_a_var_target_is_exempt() -> None:
    """`var/` is gitignored, so its targets can never resolve in CI."""
    for target in ("var/snapshots/2024-03-07/", "../var/reports/roster.md"):
        assert guard.resolve_target(target, REPO_ROOT / "tests") is None, (
            f"{target} must be exempt, not merely absent"
        )


def test_the_var_exemption_does_not_swallow_a_lookalike() -> None:
    assert guard.resolve_target("variance.md", REPO_ROOT / "tests") is not None


# --- Promise 4: bare requests/... tokens resolve ----------------------------------


def test_a_dead_bare_request_token_is_reported() -> None:
    """The dropped capability: a dead pointer in prose misleads the next stage silently."""
    text = "The upstream artifact is requests/bugfix-requests/no-such-slug/ROOT_CAUSE_ANALYSIS.md."
    assert guard.bare_request_tokens(text) == [
        "requests/bugfix-requests/no-such-slug/ROOT_CAUSE_ANALYSIS.md"
    ]


def test_a_token_inside_a_code_span_is_still_scanned() -> None:
    """Code spans are how this repo actually writes these, so they must be in scope.

    Proven with a DEAD token: `bare_request_tokens` reports only what fails to resolve,
    so a live one coming back empty would prove nothing about whether it was examined.
    """
    live = "see `requests/bugfix-requests/README.md` for the contract"
    assert guard.bare_request_tokens(live) == [], "a live token in a code span must pass"

    dead = "see `requests/bugfix-requests/no-such-slug/README.md` for the contract"
    assert guard.bare_request_tokens(dead) == ["requests/bugfix-requests/no-such-slug/README.md"], (
        "a dead token inside a code span must be caught — code spans are not an exemption"
    )


def test_a_templated_or_globbed_token_is_not_a_dead_pointer() -> None:
    """A placeholder is meant to be filled in; a glob is a search, not a path.

    Asserted through the PATTERN, not a downstream filter. An earlier draft also carried
    an `if "*" in token` guard that could never fire, because the character class already
    excludes those characters — so this test passed for a reason unrelated to its name.
    A test that cannot distinguish its own mechanism is not testing one.
    """
    text = (
        "layout is requests/<track>-requests/<slug>/ and the grep covers "
        "requests/bugfix-requests/*/BUGFIX_REQUEST.md"
    )
    assert guard.bare_request_tokens(text) == []
    emitted = guard.BARE_REQUEST_TOKEN.findall(text)
    assert not [t for t in emitted if "*" in t or "<" in t or ">" in t], (
        f"the pattern itself must never emit a glob or a placeholder whole (saw {emitted})"
    )


def test_a_bare_token_inside_a_fence_is_exempt_like_a_link() -> None:
    text = "```\nrequests/bugfix-requests/no-such-slug/FILE.md\n```"
    assert guard.bare_request_tokens(guard.strip_fences(text)) == []


def test_there_is_no_own_directory_exemption() -> None:
    """A forward reference is fenced, not exempted — the guard matches its promise.

    A draft exempted not-yet-written pipeline artifacts in the citing document's own
    directory, so a plan could list the `IMPLEMENTATION_REPORT` its stage 4 will write.
    Measured, that bought exactly one token repo-wide while making the guard permanently
    looser than the contract it implements, and silencing a mistyped sibling filename.
    The skills already prescribe the remedy for a forward reference: put it in a fence.
    """
    own = "requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/NOT_WRITTEN_YET.md"
    assert guard.bare_request_tokens(f"write {own}") == [own], (
        "a not-yet-written artifact must be caught unless the author fences it"
    )
    fenced = f"```\n{own}\n```"
    assert guard.bare_request_tokens(guard.strip_fences(fenced)) == [], (
        "and fencing it must be the escape hatch, exactly as the skills promise"
    )
