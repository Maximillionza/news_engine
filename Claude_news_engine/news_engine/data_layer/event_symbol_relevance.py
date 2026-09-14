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
_RELEVANCE_TABLE: dict[tuple[str, str], RelevanceJudgment] = {
    ("CPI m/m", "XAUUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Layer1_Event_to_USD 2025-07-CPI/2026-03-CPI/2026-07-CPI rows -- "
        "repeated, dated, sourced gold reactions to CPI surprises "
        "(e.g. 2025-07-CPI: gold to a 1-week low as headline dominated)",
    ),
    ("CPI m/m", "XAGUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Same USD-inflation channel as XAUUSD (Tier1 prompt's PER-INSTRUMENT "
        "QUIRKS: silver moves off the same baseline, amplified annually "
        "though not always monthly) -- no real evidence CPI's reach to "
        "silver is itself in question, only its relative magnitude vs gold",
    ),
    ("CPI m/m", "US30"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Tier1 prompt's PER-INSTRUMENT QUIRKS: equity indices react to "
        "the same rate-path news CPI feeds into, framing-dependent "
        "(soft-landing vs recession-fear) but real and documented "
        "(Evercore ISI post-rate-cut pattern already cited there)",
    ),
    ("CPI m/m", "US500"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, CPI-specific (not by analogy to a "
        "different event): Sep 11 2026 US CPI (headline hotter on energy, "
        "core in-line at 2.4% y/y) -- S&P 500 gapped up and closed the day "
        "up about 0.9-1%, part of a 'losing week ending on a high note as "
        "Fed rate-hike bets jump' (Yahoo Finance, "
        "finance.yahoo.com/markets/live/stock-market-today-friday-"
        "september-11-dow-sp-500-nasdaq-cpi-inflation-082201751.html); "
        "academic event-study evidence (Tandfonline, 'Asymmetric S&P 500 "
        "reactions to CPI surprises in a high-inflation environment', "
        "2021-2025 sample) separately documents statistically significant "
        "S&P 500 abnormal returns on disinflationary CPI surprises",
    ),
    ("CPI m/m", "NAS100"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, CPI-specific: same Sep 11 2026 US "
        "CPI release -- Nasdaq rose alongside the S&P 500 that day (Yahoo "
        "Finance, same URL as the US500 entry); separately, Nasdaq.com's "
        "own reporting on Nasdaq-100 (NDX) documents a real quantified "
        "CPI-day volatility premium -- average price change on CPI-release "
        "days is +/-1.44% vs +/-1.05% on an average day "
        "(nasdaq.com/articles/inflation-numbers-tap-recent-nasdaq-100-ndx-"
        "reactions-cpi-and-ppi-mixed) -- a specific, sourced NAS100 CPI "
        "reaction, not reasoned by analogy from US30",
    ),
    ("CPI m/m", "EURUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch findings: Sep 11 2026 US CPI (headline "
        "in-line, core hotter) moved EURUSD from an intraday low of 1.1569 "
        "back toward 1.1600 on reinforced Fed-hike expectations "
        "(fxstreet.com/news/euro-steadies-against-us-dollar-after-volatile-"
        "reaction-to-us-cpi-202609111302); a milder case (Apr 2026 CPI, "
        "May 13 2026 report) shows only a 3-pip move, so the pair's CPI "
        "sensitivity is real but surprise-magnitude-dependent, not uniform",
    ),
    ("CPI m/m", "GBPUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding: an August US CPI release (headline "
        "in-line at 3.4% y/y, core hotter at 0.3% vs 0.2% forecast) moved "
        "GBPUSD from 1.3524 down to an intraday low near 1.3470 before "
        "recovering, roughly 54 pips of CPI-driven movement "
        "(fxstreet.com/news/pound-sterling-price-news-and-forecast-gbp-usd-"
        "shakes-off-us-cpi-jolt-as-uk-growth-steals-spotlight-202609111657)",
    ),
    ("CPI m/m", "USDJPY"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding: Dec 2025 US CPI undershoot (2.7% "
        "actual vs 3.1% expected) triggered fresh dollar-selling pressure "
        "in USDJPY; separately, Forex Factory documents USDJPY as 'a big "
        "mover on US CPI data' with a >700-pip move over roughly a week "
        "during a volatile stretch -- consistent with Tier1 prompt's "
        "PER-INSTRUMENT QUIRKS on USDJPY's layered (mechanical + carry + "
        "safe-haven) CPI sensitivity",
    ),
    ("CPI m/m", "USDCHF"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding: an August US CPI release (core "
        "hotter than forecast) moved USDCHF up over 0.40%, from a daily "
        "low of 0.8124 to 0.8165-0.8170 "
        "(fxstreet.com/news/usd-chf-price-forecast-bulls-break-08150-as-cpi"
        "-fuels-fed-bets-202609112101) -- consistent with Layer2's mechanical "
        "USD-leg baseline for this pair",
    ),
    ("CPI m/m", "AUDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding: a downside US CPI surprise drove "
        "AUDUSD intraday highs above $0.71 as the dollar fell roughly 1.1% "
        "on the yield correction and risk appetite surged "
        "(fxstreet.com/amp/analysis/aud-surges-on-heels-of-us-inflation-"
        "surprise-202208110051) -- an older dated instance, but a real, "
        "specific CPI-surprise reaction in this exact pair, on top of "
        "Layer2's mechanical USD-leg baseline",
    ),
    ("CPI m/m", "NZDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding: a June 2026 US CPI undershoot "
        "(headline -0.4% m/m vs -0.1% forecast, y/y easing to 3.5% from "
        "4.2%) sent NZDUSD to a one-month high near 0.5820, up nearly "
        "1.23% on the day "
        "(tmgm.com/en/analysis/market-news/article/new-zealand-dollar-"
        "soars-to-one-month-high-as-us-cpi-undershoots-202607141433)",
    ),
    ("CPI m/m", "USDCAD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding: an August 2026 US CPI release "
        "(core hotter than forecast) pushed USDCAD to an intraday high of "
        "1.3882 before settling near 1.3870, with the move compounded (not "
        "replaced) by a separate >4% Oil selloff that independently "
        "weighed on CAD the same day -- CPI's own initial impulse is real "
        "and documented even though oil is a competing driver "
        "(forex.com/en-us/news-and-analysis/usdcad-analysis-canadian-"
        "dollar-rebounds-after-cpi-and-boc-decision/, vantagemarkets.com/"
        "market-analysis/usdcad-oil-four-month-high-us-cpi-september-11-"
        "2026/), consistent with Layer2's oil-linked USDCAD nuance",
    ),
}


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
