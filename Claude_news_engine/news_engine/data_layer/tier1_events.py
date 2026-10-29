"""
Tier 1 registry and timing rules (B3, Adaptive news engine). Zero project
imports on purpose: the Cleveland capture script, the research CLI and the
Stats tab all read it, so it must be importable from anywhere.

Tier 1 = the pre-release call the dashboard compares news sentiment against.
Three kinds: "formula" (a deterministic rule on a published model output),
"market_implied" (a fixed rule on a traded market's prices: Kalshi ladders,
and rows that cite CME FedWatch) and "judgment" (researched by hand each
release). The tier of a title names its only producer.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Optional

TIER1_FORMULA = "formula"
TIER1_MARKET_IMPLIED = "market_implied"   # B12: Kalshi capture rows and FedWatch-cited rows (tier1_row_tier)
TIER1_JUDGMENT = "judgment"
TIER1_TIERS: tuple[str, ...] = (TIER1_FORMULA, TIER1_MARKET_IMPLIED, TIER1_JUDGMENT)

# Covered USD releases -> which kind of Tier 1 call they get. Order is the
# display / research order. Producers: formula = scripts/capture_nowcast_from_cleveland.py,
# market_implied = the Kalshi phase of scripts/capture_tier1.py (webapp/tier1_market.MARKET_SERIES),
# judgment = scripts/tier1_research.py (B12).
TIER1_EVENTS: dict[str, str] = {
    "CPI m/m": TIER1_FORMULA,
    "Core CPI m/m": TIER1_FORMULA,
    "CPI y/y": TIER1_FORMULA,
    "Core CPI y/y": TIER1_FORMULA,
    "PPI m/m": TIER1_MARKET_IMPLIED,
    "Non-Farm Employment Change": TIER1_MARKET_IMPLIED,
    "FOMC Meeting Minutes": TIER1_JUDGMENT,
    "FOMC Statement": TIER1_JUDGMENT,
    "Federal Funds Rate": TIER1_MARKET_IMPLIED,
    "Prelim GDP q/q": TIER1_JUDGMENT,
    "Advance GDP q/q": TIER1_MARKET_IMPLIED,
    "Final GDP q/q": TIER1_JUDGMENT,
    "GDP q/q": TIER1_JUDGMENT,
    "Core PCE Price Index m/m": TIER1_FORMULA,
    "ISM Manufacturing PMI": TIER1_MARKET_IMPLIED,
    "ISM Services PMI": TIER1_JUDGMENT,
    "Retail Sales m/m": TIER1_MARKET_IMPLIED,
    "Core Retail Sales m/m": TIER1_JUDGMENT,
}

TIER1_FORMULA_SOURCE = "Cleveland Fed nowcast (formula)"
# A published model output: primary-sourced but still a model, so never "Certain".
TIER1_FORMULA_CONFIDENCE = "Likely"

TIER1_MARKET_IMPLIED_SOURCE = "Kalshi market-implied"
# A market price is a crowd's bet, not a certainty.
TIER1_MARKET_IMPLIED_CONFIDENCE = "Likely"

# A value that opens with a FedWatch citation ("CME FedWatch (via ...", "FedWatch: ~91% hold"); a mid-text
# mention ("... FedWatch hike odds rose") is not a citation of the call's basis.
_FEDWATCH_LEADING_CITATION = re.compile(r"^\s*(?:CME\s+)?FedWatch\b", re.IGNORECASE)

TIER1_RESEARCH_LOOKAHEAD = dt.timedelta(days=8)   # research plan covers releases this far ahead
LATE_CHECK_STALE_AFTER = dt.timedelta(days=5)     # a call this old (no newer reading) gets a late check
LATE_CHECK_WINDOW = dt.timedelta(hours=24)        # one more check inside the last 24h before release
LATE_CHECK_REASONS: tuple[str, ...] = ("stale_call", "release_within_24h")


def tier1_titles(tier: str) -> list[str]:
    """Titles of one tier, in TIER1_EVENTS order; ValueError for an unknown tier."""
    if tier not in TIER1_TIERS:
        raise ValueError(f"tier={tier!r} is not valid -- must be one of: {', '.join(TIER1_TIERS)}")
    return [title for title, t in TIER1_EVENTS.items() if t == tier]


def tier1_row_tier(source: str, value: Optional[str] = None) -> str:
    """
    Tier of a stored tier1_predictions row. Formula only for the formula source
    (a pre-B3 LLM CPI row is judgment); the Kalshi capture source is
    market_implied; a row citing CME FedWatch is market_implied too, because
    its call is the futures-implied rate path, not a researcher's view.
    FedWatch counts when it appears anywhere in the source or when the value
    opens with it: the live 2026-10-26 Fed rows have URL-only sources and carry
    FedWatch only as the value's leading citation, so a source-only test would
    miss them. Everything else is judgment.
    """
    if source == TIER1_FORMULA_SOURCE:
        return TIER1_FORMULA
    if source == TIER1_MARKET_IMPLIED_SOURCE or "fedwatch" in (source or "").lower():
        return TIER1_MARKET_IMPLIED
    if value is not None and _FEDWATCH_LEADING_CITATION.match(value):
        return TIER1_MARKET_IMPLIED
    return TIER1_JUDGMENT


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
