"""The byte-accounting tier vocabulary — one definition, owned by the tests.

Three parser modules now declare a tier and three test modules check the declaration
against what the real files do. That is four places the set of legal values could be
written down, and a vocabulary with four copies is a vocabulary that will disagree with
itself the first time it grows.

**It lives under `tests/` rather than under `src/` for a reason that is not tidiness.**
`tests/` is in the implementation subagent's hard deny set, so a walker cannot widen its
own vocabulary — declaring a new tier means editing this file, which means the main
thread did it deliberately. Moving this constant into `src/ootp_ai/parser/` would hand
the builder both halves of the check and quietly turn the guard into a formality.

The tiers themselves, weakest claim last:

* `strict` — zero residual bytes. Every field width in the file is confirmed, because a
  wrong one desynchronises the next length prefix and the walk cannot reach the end.
* `diagnostic` — the residual is *recorded*, and the walk is asserted to stop on a record
  boundary. The file is walked from the top; some of it is crossed without being decoded.
* `region-accounted` — added 2026-08-16, operator-disposed, for `world.dat`. A
  landmark-entered walk of a single-record 8.9 MB file never reads ~7.5 MB of it, so
  "residual" is not even the right question. Zero residual *within* each walked region,
  each region's own declared count matched exactly, and the un-walked prefix and suffix
  recorded as numbers rather than waved at.

`region-accounted` is a **weaker** claim than `diagnostic`, and it has its own name so it
cannot be mistaken for one. Widening `diagnostic` to cover it was the alternative
considered and rejected: one word would then have meant two very different strengths of
claim, and the weaker meaning would have been the one nobody noticed.
"""

from __future__ import annotations

#: Every legal value of a parser module's `BYTE_ACCOUNTING_TIER`. A declaration outside
#: this set is an undeclared weakening — the failure the tier mechanism exists to make
#: expensive to hide.
KNOWN_TIERS = frozenset({"strict", "diagnostic", "region-accounted"})
