"""
Tier 1 registry and timing rules (B3, Adaptive news engine). Zero project
imports on purpose: the Cleveland capture script, the research CLI and the
Stats tab all read it, so it must be importable from anywhere.

Tier 1 = the pre-release call the dashboard compares news sentiment against.
Three kinds: "formula" (a deterministic rule on a published model output),
"market_implied" (reserved for B12 / Kalshi, no titles yet) and "judgment"
(researched by hand each release).
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

TIER1_FORMULA = "formula"
TIER1_MARKET_IMPLIED = "market_implied"   # reserved for B12 (Kalshi); no titles map here yet
TIER1_JUDGMENT = "judgment"
TIER1_TIERS: tuple[str, ...] = (TIER1_FORMULA, TIER1_MARKET_IMPLIED, TIER1_JUDGMENT)

# Covered USD releases -> which kind of Tier 1 call they get. Order is the
# display / research order.
TIER1_EVENTS: dict[str, str] = {
    "CPI m/m": TIER1_FORMULA,
    "Core CPI m/m": TIER1_FORMULA,
    "PPI m/m": TIER1_JUDGMENT,
    "Non-Farm Employment Change": TIER1_JUDGMENT,
    "FOMC Meeting Minutes": TIER1_JUDGMENT,
    "FOMC Statement": TIER1_JUDGMENT,
    "Federal Funds Rate": TIER1_JUDGMENT,
    "Prelim GDP q/q": TIER1_JUDGMENT,
    "Advance GDP q/q": TIER1_JUDGMENT,
    "Final GDP q/q": TIER1_JUDGMENT,
    "GDP q/q": TIER1_JUDGMENT,
    "Core PCE Price Index m/m": TIER1_JUDGMENT,
    "ISM Manufacturing PMI": TIER1_JUDGMENT,
    "ISM Services PMI": TIER1_JUDGMENT,
    "Retail Sales m/m": TIER1_JUDGMENT,
    "Core Retail Sales m/m": TIER1_JUDGMENT,
}

TIER1_FORMULA_SOURCE = "Cleveland Fed nowcast (formula)"
# A published model output: primary-sourced but still a model, so never "Certain".
TIER1_FORMULA_CONFIDENCE = "Likely"

TIER1_RESEARCH_LOOKAHEAD = dt.timedelta(days=8)   # research plan covers releases this far ahead
LATE_CHECK_STALE_AFTER = dt.timedelta(days=5)     # a call this old (no newer reading) gets a late check
LATE_CHECK_WINDOW = dt.timedelta(hours=24)        # one more check inside the last 24h before release
LATE_CHECK_REASONS: tuple[str, ...] = ("stale_call", "release_within_24h")


def tier1_titles(tier: str) -> list[str]:
    """Titles of one tier, in TIER1_EVENTS order; ValueError for an unknown tier."""
    if tier not in TIER1_TIERS:
        raise ValueError(f"tier={tier!r} is not valid -- must be one of: {', '.join(TIER1_TIERS)}")
    return [title for title, t in TIER1_EVENTS.items() if t == tier]


def tier1_row_tier(source: str) -> str:
    """Tier of a stored tier1_predictions row: formula only for the formula source (a pre-B3 LLM CPI row is judgment)."""
    return TIER1_FORMULA if source == TIER1_FORMULA_SOURCE else TIER1_JUDGMENT


def late_check_reason(
    newest_reading_utc: dt.datetime, event_time_utc: dt.datetime, now_utc: dt.datetime,
    has_window_check: bool,
) -> Optional[str]:
    """
    Why a judgment event needs a late check right now, or None. All datetimes
    aware. newest_reading_utc is the later of the call's logged_at_utc and the
    newest late check's checked_at_utc, so a fresh check resets staleness.
    The 24h check fires once per occurrence (has_window_check) and only when
    nothing was read inside the window; otherwise every run after day 5 would
    log a check.
    """
    if now_utc >= event_time_utc:
        return None
    if event_time_utc - now_utc <= LATE_CHECK_WINDOW:
        if not has_window_check and newest_reading_utc < event_time_utc - LATE_CHECK_WINDOW:
            return "release_within_24h"
        return None
    if now_utc - newest_reading_utc > LATE_CHECK_STALE_AFTER:
        return "stale_call"
    return None
