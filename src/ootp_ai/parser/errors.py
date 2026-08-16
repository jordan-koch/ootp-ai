"""The parser's exception taxonomy — one base, four refusals.

Every one of these exists so a failure is **loud**. The rulebook's line is that a
loud failure is recoverable and a silent misparse is not: a parser that copes with
a header it does not recognise goes on to read the wrong bytes as ratings, contracts
and roster membership, and nothing downstream can tell.

The classes are pinned by name in the offline suite. Renaming one is an interface
change, not a refactor — which is why each carries `# noqa: N818` rather than an
`…Error` suffix: ruff's naming rule and the test that imports the name disagree, and
the test wins. `SaveFormatError` is the base a caller catches, so it keeps the suffix.
"""

from __future__ import annotations

__all__ = [
    "MalformedHeader",
    "SaveFilenameMismatch",
    "SaveFormatError",
    "UnexpectedEndOfData",
    "UnsupportedSaveVersion",
]


class SaveFormatError(Exception):
    """Base for every refusal to read a save file.

    Callers that want to fail a whole ingest run on any format problem catch this;
    callers that want to distinguish "OOTP 26 shipped" from "this file is not a
    save at all" catch the subclasses.
    """


class MalformedHeader(SaveFormatError):  # noqa: N818
    """The 79 header bytes are not the shape an OOTP save file has.

    Covers the two symmetric traps recorded in the format catalog: the magic begins
    at offset 1 rather than 0, and the leading byte is a null that is not part of
    it. Also covers a truncated or empty buffer — reading past the end of a header
    is never something to recover from.
    """


class UnsupportedSaveVersion(SaveFormatError):  # noqa: N818
    """The header declares a format version this parser has not been proven against.

    Refuse rather than attempt it. A patched game may move the layout, and every
    field mapping this project holds was measured against version 25.
    """

    def __init__(self, version: int, *, supported: int) -> None:
        super().__init__(
            f"save format version {version} is not supported "
            f"(this parser is proven against version {supported} only); "
            "refusing rather than risking a silent misparse"
        )
        self.version = version
        self.supported = supported


class SaveFilenameMismatch(SaveFormatError):  # noqa: N818
    """The header names a different file than the one that was opened.

    The header carries its own filename, which makes this a free check that the
    path wiring is right — cheap to run, and it catches a mis-resolved path before
    the bytes get interpreted as something they are not.
    """

    def __init__(self, declared: str, expected: str) -> None:
        super().__init__(
            f"header declares {declared!r} but the file opened is {expected!r}; "
            "the path wiring is wrong or the file is not what it claims"
        )
        self.declared = declared
        self.expected = expected


class UnexpectedEndOfData(SaveFormatError):  # noqa: N818
    """A read ran past the end of the buffer.

    Raised by the cursor. In a sequential walk this means the walk lost alignment
    somewhere upstream, so the useful response is to stop, not to return a short
    value and continue.
    """
