"""Relative Markdown links must resolve. Broken cross-references rot docs fast.

The rules below are the contract five skills state to artifact authors in their "What
good looks like" sections. They were promised long before they were implemented: for
the repo's whole history this guard applied one regex to the raw file text and exempted
only `http(s)://`, `mailto:`, `#` and angle-bracket placeholders, so following the
documentation produced a red build. `tests/test_doc_link_contract.py` unit-tests each
rule against fixture strings; this module applies them to the tree.

See `requests/bugfix-requests/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md`.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")

#: A fence opens or closes on ``` or ~~~, optionally blockquoted ("blockquoted is fine")
#: and optionally as the content of a list item — `.claude/skills/commit/SKILL.md:189` is
#: literally "2. ```". Missing the list-item form is not a small miss: it flips fence
#: parity, so every line after it reads as fenced and the scan silently stops checking
#: the rest of the file. Measured before this was handled: that one file lost 76 of its
#: 194 non-blank lines, and a broken link placed after it went unreported.
#: Only the marker that opened a fence can close it, so a ``` block may quote a ~~~ one.
FENCE = re.compile(r"^\s*(?:>\s*)*(?:(?:[-*+]|\d+[.)])\s+)?(`{3,}|~{3,})")

#: A Markdown link may carry a title after the target: `[text](path.md "Title")`. The
#: title is not part of the path, and three skills promise it is exempt.
LINK_TITLE = re.compile(r"""\s+(?:"[^"]*"|'[^']*'|\([^)]*\))\s*$""")

#: A trailing line citation - `:38`, or a range `:10-20` written with either a hyphen or
#: an en dash, which this repo's prose uses freely. Stripped before resolving, because it
#: addresses a line inside the file rather than a path on disk. The dash class is spelled
#: with an escape so the source carries no ambiguous-glyph character (ruff RUF001/RUF003).
LINE_SUFFIX = re.compile(r":\s*L?\d+(?:\s*[-\u2013]\s*\d+)?\s*$")

#: A bare `requests/...` path written in prose or inside a code span, which four of the
#: five skills promise is resolved too. Trailing sentence punctuation is not part of it.
#: The character class excludes `*`, `<` and `>`, so a glob (`requests/*/BUGFIX_REQUEST.md`)
#: or an angle-bracket placeholder (`requests/<track>-requests/`) is never emitted whole —
#: a search and a template are not pointers. That exclusion lives HERE, in the pattern,
#: rather than as a downstream filter that could never fire.
BARE_REQUEST_TOKEN = re.compile(r"(?<![\w./-])(requests/[A-Za-z0-9._/-]*[A-Za-z0-9_/])")

#: `var/` is gitignored, so a target under it can never resolve in a fresh clone or in
#: CI. Demanding that it resolve is demanding the impossible.
IGNORED_ROOTS = ("var",)


def strip_fences(text: str) -> str:
    """Blank out fenced regions, preserving the line count.

    A pre-pass rather than a cleverer regex: fences are a line-level construct, and a
    regex that tries to skip them inline mishandles the nested and blockquoted cases
    the promise explicitly allows. Lines are blanked, not deleted, so line numbers on
    either side of a fence stay meaningful.
    """
    lines = text.splitlines()
    out: list[str] = []
    marker: str | None = None
    opened_at: int | None = None
    for index, line in enumerate(lines):
        hit = FENCE.match(line)
        if marker is None:
            if hit:
                marker = hit.group(1)
                opened_at = index
                out.append("")
                continue
        else:
            out.append("")
            # CommonMark: a closing fence uses the same character and is at least as long
            # as the opener, so an inner ``` cannot close a ```` block. Comparing only the
            # first character would end the block early and re-expose its contents.
            if hit and hit.group(1)[0] == marker[0] and len(hit.group(1)) >= len(marker):
                marker = None
                opened_at = None
            continue
        out.append(line)

    # An unterminated fence must not switch the scan off for the rest of the document.
    # Fail toward CHECKING: restore everything from the dangling opener onward, so a
    # missing closing fence costs a false positive rather than silent blindness. The
    # opposite default is how a guard stops checking without anyone noticing.
    if marker is not None and opened_at is not None:
        out[opened_at:] = lines[opened_at:]
    return "\n".join(out)


def link_targets(text: str) -> list[str]:
    """Every Markdown link target in `text`. Feed it fence-stripped text."""
    return LINK.findall(text)


def resolve_target(target: str, base: Path) -> Path | None:
    """The path a link target points at, or None when the target is exempt.

    Exempt: external schemes, in-page anchors, angle-bracket template placeholders, and
    anything under an ignored root. A returned path is NOT asserted to exist — that is
    the caller's check, so that stripping a line suffix can never launder a dead path.
    """
    if target.startswith(SKIP_PREFIXES):
        return None
    # Angle brackets mark a template placeholder, not a path: the skills document
    # directory shapes like `[<slug>](<slug>/)`. Those are meant to be filled in.
    if "<" in target or ">" in target:
        return None

    clean = LINK_TITLE.sub("", target.strip())
    clean = clean.split("#", 1)[0].strip()
    clean = LINE_SUFFIX.sub("", clean).strip()
    if not clean:
        return None

    # A target that NAMES an ignored root is exempt however it resolves. Authors write
    # `var/reports/roster.md` meaning the repo's var/, not one relative to the document
    # they happen to be writing in, and both readings are equally unresolvable anyway.
    head = PurePosixPath(clean.replace("\\", "/")).parts
    if head and head[0].lstrip("./") in IGNORED_ROOTS:
        return None

    resolved = (base / clean).resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved
    if relative.parts and relative.parts[0] in IGNORED_ROOTS:
        return None
    return resolved


def bare_request_tokens(text: str) -> list[str]:
    """Bare `requests/...` tokens that do not resolve. Feed it fence-stripped text.

    Unlike the link scan this returns only the DEAD ones: a bare token has no link text
    to disambiguate it, so the check is worth making only where it can point at a real
    miss. A glob is a search rather than a path, and an angle-bracket placeholder is
    meant to be filled in; neither is emitted by the pattern at all.

    There is deliberately NO exemption for a document's own directory. A draft carried
    one, so that a plan's files-to-touch checklist could name the `IMPLEMENTATION_REPORT`
    its stage 4 will write. Measured, it bought exactly one token in the whole repo while
    making the guard permanently more permissive than the promise it implements — and the
    skills already prescribe the remedy for a forward reference: fence it. A guard looser
    than its own documentation is how this defect started.
    """
    dead: list[str] = []
    for token in BARE_REQUEST_TOKEN.findall(text):
        if not (REPO_ROOT / token).exists():
            dead.append(token)
    return dead


def markdown_files() -> list[Path]:
    """Live Markdown bodies. `_done/` is excluded because the promise says so.

    All five skills state that a "live (non-`_done/`) artifact body" is what gets
    scanned. An archived artifact is a historical record: its pointers described the
    repo as it was, and demanding they still resolve would turn the archive into a
    maintenance burden and, eventually, into a reason to stop archiving.
    """
    return [
        p
        for p in REPO_ROOT.rglob("*.md")
        if ".git" not in p.parts and "var" not in p.parts and "_done" not in p.parts
    ]


def test_relative_links_resolve() -> None:
    broken: list[str] = []
    for path in markdown_files():
        text = strip_fences(path.read_text(encoding="utf-8"))
        for target in link_targets(text):
            resolved = resolve_target(target, path.parent)
            if resolved is not None and not resolved.exists():
                rel = path.relative_to(REPO_ROOT).as_posix()
                broken.append(f"{rel} -> {target}")

    assert not broken, "broken relative links:\n" + "\n".join(broken)


def test_bare_request_tokens_resolve() -> None:
    """A dead `requests/...` pointer in prose misleads the next stage silently.

    This is the half the guard never had — the skills describe a scanner that reads
    bare tokens, not only Markdown link syntax, and a stage-3 plan that cites a
    stage-2 artifact by a path that has since moved is exactly the failure it catches.
    """
    dead: list[str] = []
    for path in markdown_files():
        text = strip_fences(path.read_text(encoding="utf-8"))
        for token in bare_request_tokens(text):
            rel = path.relative_to(REPO_ROOT).as_posix()
            dead.append(f"{rel} -> {token}")

    assert not dead, "bare requests/ tokens that do not resolve:\n" + "\n".join(dead)
