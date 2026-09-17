"""
Maps a live calendar event title (webapp/store.py's `event["title"]`, as
matched by the tier1-cpi-ppi-autoresearch scheduled task's own Step 1
exact-title list) to the methodology label both data_layer/
event_symbol_relevance.py and data_layer/event_symbol_magnitude.py key
their tables on. Neither table is keyed by exact calendar title -- both
group several real titles under one methodology row (see both tables'
own module docstrings for the same grouping) -- so this mapping must
resolve a live title to its row key before either table can be
consulted (docs/superpowers/specs/2026-09-17-live-wiring-design.md).
"""
from __future__ import annotations

EVENT_TITLE_TO_METHODOLOGY: dict[str, str] = {
    "FOMC Meeting Minutes": "FOMC Rate Decision",
    "FOMC Statement": "FOMC Rate Decision",
    "Federal Funds Rate": "FOMC Rate Decision",
    "Prelim GDP q/q": "GDP q/q",
    "Advance GDP q/q": "GDP q/q",
    "GDP q/q": "GDP q/q",
    "Retail Sales m/m": "Retail Sales m/m",
    "Core Retail Sales m/m": "Retail Sales m/m",
    "CPI m/m": "CPI m/m",
    "PPI m/m": "PPI m/m",
    "Non-Farm Employment Change": "Non-Farm Employment Change",
    "Core PCE Price Index m/m": "Core PCE Price Index m/m",
    "ISM Manufacturing PMI": "ISM Manufacturing PMI",
    "ISM Services PMI": "ISM Services PMI",
}


def resolve_methodology_label(calendar_title: str) -> str | None:
    """
    Returns the methodology label a live calendar title maps to, or None
    if the title isn't one of the 14 mapped Tier 1 titles. Never guesses
    a mapping for an unrecognized title -- unmapped means "not looked up
    at all," same as an untracked symbol.
    """
    return EVENT_TITLE_TO_METHODOLOGY.get(calendar_title)
