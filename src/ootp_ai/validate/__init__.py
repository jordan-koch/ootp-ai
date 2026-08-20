"""Validation harnesses — the parser measured against an independent answer key.

Nothing here is part of the ingest path. These modules exist to *disprove* the parser,
and they run against the one save that can carry an answer key at all: the standard-mode
probe, because Challenge Mode has no export (ADR 0003).
"""
