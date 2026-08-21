"""What a rendered report must look like, shared by the two modules that check one.

`tests/test_reports.py` applies this against a real landing under `-m gamedata`;
`tests/test_report_rendering.py` guards the pattern itself offline, so CI proves the rule
still admits what it should and rejects what it must even though CI can render nothing.
One definition with two consumers — the same shape `tests/fixtures/warehouse.py` uses for
the landing fixture, and for the same reason: two copies of a rule drift.
"""

from __future__ import annotations

import re
from typing import Final

__all__ = ["NAME_PATTERN"]

#: A name, not an integer. Deliberately permissive about *which* characters a name may
#: hold — O'Neill, Jr., de la Cruz — and strict about the one property the assertion
#: exists for: it must begin with a letter, so no id can satisfy it.
#:
#: **Unicode-aware, and that is a deliberate correction to AC14's own text.** The criterion
#: quotes ``^[A-Za-z][A-Za-z .'-]+$`` verbatim, which admits nothing above U+007F — while
#: `names.dat` is latin-1 and the landed table holds 1,623 entries carrying an accented
#: character, every one of which fails the ASCII form. Boston's books happen to hold none
#: today, so the ASCII pattern is green by circumstance; the first international signing,
#: draft class or DSL promotion turns it red **on a correct render**, which the plan names
#: twice as *"the most expensive kind of wrong test, because it sends the next agent
#: hunting a bug in working code."*
#:
#: ``[^\W\d_]`` reads as "a word character that is neither a digit nor an underscore" — a
#: letter in any script. So `José Ramírez` and `Yū Darvish` pass while `47035` and the
#: structural-absence marker still fail.
NAME_PATTERN: Final = re.compile(r"^[^\W\d_][\w .'-]+$", re.UNICODE)
