"""ootp-ai — an AI front office for Out of the Park Baseball 25.

The save-file parser, the bronze landing that puts it in MySQL, and the reports the
GM reads off it. Nothing here writes to the game (ADR 0001).

See `docs/data-access.md` for what the save-format investigation established and with
what confidence, and `docs/warehouse-catalog.md` for what is landed, what is withheld,
and what is read but landed by nothing.
"""

__version__ = "0.1.0"
