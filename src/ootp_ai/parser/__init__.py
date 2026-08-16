"""Sequential readers for OOTP's save binaries.

The spine is three modules and one rule. `primitives.Cursor` moves forward and
cannot be made to do anything else, `header.read_header` refuses any file it has not
been proven against, and `errors` gives every refusal a name a caller can catch.
Walkers for the individual files land on top of this, one file per phase.

Nothing in this package opens a file. Callers hand it `bytes`, which keeps every
read in the pipeline `"rb"` by construction — the game's saves are read-only, and a
Challenge-mode save carries an integrity hash that one write destroys irreversibly.
"""

from __future__ import annotations
