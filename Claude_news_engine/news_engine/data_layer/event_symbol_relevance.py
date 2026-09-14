"""
Phase 1 of a two-phase plan (see docs/superpowers/specs/2026-09-13-event-
symbol-relevance-grid-design.md): a static, hand-curated reference table
answering "does this Tier 1 event genuinely reach this specific symbol" --
Relevant, Not relevant, or honestly Unverified where no real evidence
exists yet. Same discipline as data_layer/exposure.py -- a real Python
constant, never a database table or a live fetch, extended by hand only
on real, cited evidence.

This is a REFERENCE TABLE ONLY. Nothing here is wired into live scoring,
the dashboard, or the tier1-cpi-ppi-autoresearch scheduled task -- that
wiring is phase 3, explicitly deferred until phase 2 (magnitude/
weighting) also exists.

Row labels represent the underlying economic event, not one exact
calendar title -- several cover more than one real title the way the
existing Tier1 methodologies already group them (see EVENT_TYPES below).
Do not confuse these with tier1-cpi-ppi-autoresearch's own Step 1 exact-
title list, which stays untouched and separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# The 9 event types, one per existing Tier 1 methodology. Several
# represent more than one exact calendar title -- "FOMC Rate Decision"
# covers "FOMC Meeting Minutes"/"FOMC Statement"/"Federal Funds Rate";
# "GDP q/q" covers "Prelim GDP q/q"/"Advance GDP q/q"/"GDP q/q"; "Retail
# Sales m/m" covers "Retail Sales m/m"/"Core Retail Sales m/m" -- same
# grouping POC_FOMC_Rate_Decision/POC_GDP_Nowcast/POC_Retail_Sales
# already use for their own methodology, since relevance is a property
# of the underlying event, not each printed title variant.
EVENT_TYPES: tuple[str, ...] = (
    "CPI m/m",
    "PPI m/m",
    "Non-Farm Employment Change",
    "FOMC Rate Decision",
    "GDP q/q",
    "Core PCE Price Index m/m",
    "ISM Manufacturing PMI",
    "ISM Services PMI",
    "Retail Sales m/m",
)

# The 12 symbols webapp/static/js/dashboard/symbol-picker.js's CATEGORIES
# constant already defines. Extend both alongside each other if either
# ever grows -- same "extend this alongside that" convention
# data_layer/dukascopy_feed.py's _INSTRUMENT_MAP comment already uses.
SYMBOLS: tuple[str, ...] = (
    "XAUUSD", "XAGUSD",
    "US30", "US500", "NAS100",
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
)


class RelevanceStatus(Enum):
    RELEVANT = "relevant"          # real, sourced evidence this event reaches this symbol
    NOT_RELEVANT = "not_relevant"  # real, sourced evidence this event does NOT meaningfully reach this symbol
    UNVERIFIED = "unverified"      # no real evidence checked yet -- honest, not a guess


@dataclass(frozen=True)
class RelevanceJudgment:
    status: RelevanceStatus
    citation: str  # required, non-empty for every status -- for
                    # RELEVANT/NOT_RELEVANT, the real source; for
                    # UNVERIFIED, a short honest note on what wasn't found


# Populated by Tasks 2-10 below -- every one of the 9x12=108 keys must be
# present by the time Task 11 runs its completeness test. Deliberately
# NOT sparse: a missing key here is a plan bug, not a valid "unverified"
# representation (UNVERIFIED cells still get a real, explicit entry).
_RELEVANCE_TABLE: dict[tuple[str, str], RelevanceJudgment] = {}


def get_relevance(event_type: str, symbol: str) -> RelevanceJudgment:
    """
    Returns the real, sourced judgment for (event_type, symbol). Raises
    KeyError for anything outside the defined 9x12 scope -- this never
    fabricates a judgment for a pair it doesn't recognize; an
    unrecognized pair is a caller bug (a new event type or symbol added
    elsewhere but never added here), not a data-availability case to
    swallow into a default.
    """
    return _RELEVANCE_TABLE[(event_type, symbol)]


def treat_as_relevant(judgment: RelevanceJudgment) -> bool:
    """
    The real yes/no a future phase-3 caller would act on: RELEVANT and
    UNVERIFIED both -> True (an unverified cell defaults to "assume
    relevant" so nothing gets silently suppressed before it's actually
    been checked -- explicit product decision, 2026-09-13); NOT_RELEVANT
    -> False. A caller DISPLAYING this to a person must still show
    judgment.status separately -- never collapse UNVERIFIED into a plain
    "yes" with no distinguishing label.
    """
    return judgment.status != RelevanceStatus.NOT_RELEVANT
