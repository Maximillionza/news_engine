"""
Phase 2 of a three-phase plan (see docs/superpowers/specs/2026-09-16-
event-symbol-magnitude-grid-design.md): a static, hand-curated
magnitude tier for each of Phase 1's 94 RELEVANT (event_type, symbol)
cells -- LOW/MEDIUM/HIGH (cited) or honestly UNVERIFIED where no real
evidence pins down a typical move size. Same discipline as
data_layer/exposure.py and data_layer/event_symbol_relevance.py -- a
real Python constant, never a database table or a live fetch.

This is a REFERENCE TABLE ONLY. Nothing here is wired into live
scoring, the dashboard, or the tier1-cpi-ppi-autoresearch scheduled
task -- that's phase 3, explicitly deferred by user decision.

Scoped EXACTLY to the 94 pairs data_layer.event_symbol_relevance's
get_relevance() already resolved RELEVANT as of 2026-09-16 -- never
edited here, only read. A pair that's NOT_RELEVANT or UNVERIFIED in
that module has no entry here and never will until its own relevance
is resolved first.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MagnitudeTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNVERIFIED = "unverified"  # relevance is confirmed real (Phase 1's
                                 # RELEVANT), but no real evidence pins
                                 # down a typical magnitude -- honest,
                                 # not a guess


@dataclass(frozen=True)
class MagnitudeJudgment:
    tier: MagnitudeTier
    citation: str  # required, non-empty for every tier -- for
                    # LOW/MEDIUM/HIGH, the real occurrence(s) that
                    # justify the tier (often reused directly from
                    # event_symbol_relevance's own citation for that
                    # cell); for UNVERIFIED, a short honest note on
                    # what wasn't found


# Populated by Tasks 2-10 below -- every one of the 94 real RELEVANT
# (event_type, symbol) pairs from data_layer.event_symbol_relevance
# must be present by the time Task 11 runs its completeness test.
# Deliberately scoped to exactly that 94-pair subset, never the full
# 108 -- a pair that's NOT_RELEVANT or UNVERIFIED in that module has no
# key here.
_MAGNITUDE_TABLE: dict[tuple[str, str], MagnitudeJudgment] = {
    # --- CPI m/m (Task 2) -------------------------------------------
    # Bands (reasoned starting ruler, not independently re-derived):
    # <~0.3% typical move = LOW, ~0.3-0.8% = MEDIUM, >~0.8% = HIGH.
    ("CPI m/m", "XAUUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='CPI m/m', "
            "instrument=XAUUSD, 8 real logged 30-min post-release moves (Dukascopy, auto): "
            "+0.24% (2026-01-13), +0.40% (2026-02-13), -0.44% (2026-03-11), +0.19% (2026-04-10), "
            "+0.18% (2026-05-12), +1.15% (2026-07-14), +0.23% (2026-08-12), +1.09% (2026-09-11). "
            "Median absolute move ~0.32%, mean ~0.49% -- MEDIUM, though 2 of 8 prints (2026-07-14, "
            "2026-09-11) were independently HIGH-tier (~1.1%), so real tail risk above MEDIUM exists."
        ),
    ),
    ("CPI m/m", "XAGUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated WebSearch finding, CPI-specific: 2026-09-11 US CPI day -- silver whipsawed, "
            "dipping to a three-week low of $62.94 immediately post-release before rebounding to "
            "close the day up 1.13% around $64.30 (FXStreet, 'Silver erases post-CPI slump as US "
            "Dollar post-CPI rebound fades', fxstreet.com/news/silver-erases-post-cpi-slump-rebounds-"
            "from-three-week-low-202609111622). Same CPI day used for the US500/NAS100 citations "
            "below -- 1.13% close-to-close is HIGH; the intraday high-to-low swing was materially "
            "larger still."
        ),
    ),
    ("CPI m/m", "US30"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='CPI m/m', "
            "instrument=US30, 5 real logged 30-min-or-open post-release moves: +0.21% (2026-02-13), "
            "-0.29% (2026-03-11), -0.31% (2026-07-14), +0.11% (2026-08-12, Dow open reaction to "
            "in-line July CPI per TheStreet/Yahoo Finance/CNBC), +0.60% (2026-09-11). Median absolute "
            "move ~0.29%, i.e. just under the LOW/MEDIUM line, with only 1 of 5 prints reaching "
            "MEDIUM (0.60%) -- LOW. Flag: this puts US30 in a lower tier than its sibling indices "
            "US500 (HIGH) and NAS100 (HIGH) on the same CPI prints -- plausible given the Dow's "
            "value/industrial weighting vs. the more rate-sensitive S&P/Nasdaq composition, but worth "
            "noting since it's a real divergence, not an artifact."
        ),
    ),
    ("CPI m/m", "US500"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated WebSearch finding, CPI-specific (from Phase 1's own relevance citation, "
            "independently re-verified): 2026-09-11 US CPI (headline hotter on energy, core in-line "
            "at 2.4% y/y) -- S&P 500 gapped up and closed the day up about 0.9-1% (Yahoo Finance, "
            "finance.yahoo.com/markets/live/stock-market-today-friday-september-11-dow-sp-500-nasdaq-"
            "cpi-inflation-082201751.html). 0.9-1% is over the ~0.8% HIGH line."
        ),
    ),
    ("CPI m/m", "NAS100"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated WebSearch finding, CPI-specific (from Phase 1's own relevance citation, "
            "independently re-verified): Nasdaq.com's own reporting on the Nasdaq-100 (NDX) documents "
            "a quantified CPI-day volatility premium -- average price change on CPI-release days is "
            "+/-1.44% vs +/-1.05% on an average day (nasdaq.com/articles/inflation-numbers-tap-recent-"
            "nasdaq-100-ndx-reactions-cpi-and-ppi-mixed). 1.44% is well over the ~0.8% HIGH line."
        ),
    ),
    ("CPI m/m", "EURUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated WebSearch finding (from Phase 1's own relevance citation, independently "
            "re-verified): 2026-09-11 US CPI moved EURUSD from an intraday low of 1.1569 back toward "
            "1.1600, ~31 pips = ~0.27% (FXStreet, fxstreet.com/news/euro-steadies-against-us-dollar-"
            "after-volatile-reaction-to-us-cpi-202609111302). A milder instance (Apr 2026 CPI, "
            "reported 2026-05-13) showed only a 3-pip move. Both readings are under the ~0.3% LOW "
            "line -- LOW."
        ),
    ),
    ("CPI m/m", "GBPUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch finding (from Phase 1's own relevance citation, independently "
            "re-verified): an August 2026 US CPI release (headline in-line at 3.4% y/y, core hotter "
            "at 0.3% vs 0.2% forecast) moved GBPUSD from 1.3524 down to an intraday low near 1.3470, "
            "~54 pips = ~0.40% (FXStreet, fxstreet.com/news/pound-sterling-price-news-and-forecast-"
            "gbp-usd-shakes-off-us-cpi-jolt-as-uk-growth-steals-spotlight-202609111657). ~0.40% is "
            "within the ~0.3-0.8% MEDIUM band."
        ),
    ),
    ("CPI m/m", "USDJPY"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch finding, independently re-verified for this task: on the 2026-09-11 "
            "US CPI day, USDJPY fell over 0.50%, from a brief post-release spike to 154.49 down to "
            "close around 153.60 (~0.58%) as the Yen drew added support from BoJ rate-hike "
            "expectations alongside the CPI reaction (FXStreet, fxstreet.com/news/japanese-yen-"
            "strengthens-as-us-inflation-fails-to-sustain-dollar-rebound-202609111304). ~0.58% sits in "
            "the ~0.3-0.8% MEDIUM band. NOTE: the Phase 1 relevance citation's '>700-pip move over "
            "roughly a week' figure (originally sourced there to a Forex Factory / StoneX-syndicated "
            "piece, 'USD/JPY Has Been a Big Mover on US CPI Data -- Will Tomorrow Force a Repeat?') is "
            "too imprecisely dated and too multi-day to isolate a single CPI print's own contribution, "
            "so it was not used for this magnitude tier -- the verified same-day 2026-09-11 CPI print "
            "above was used instead."
        ),
    ),
    ("CPI m/m", "USDCHF"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch finding (from Phase 1's own relevance citation, independently "
            "re-verified): an August 2026 US CPI release (core hotter than forecast) moved USDCHF up "
            "over 0.40%, from a daily low of 0.8124 to 0.8165-0.8170 (FXStreet, fxstreet.com/news/usd-"
            "chf-price-forecast-bulls-break-08150-as-cpi-fuels-fed-bets-202609112101). Over 0.40% sits "
            "in the ~0.3-0.8% MEDIUM band."
        ),
    ),
    ("CPI m/m", "AUDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated WebSearch finding, independently re-verified for this task: on the 2026-09-11 "
            "US CPI day, AUD/USD advanced 0.17% on the day, trading around 0.7170, though the RBA "
            "rate-hike narrative and the prior day's hot US PPI were also live drivers that day "
            "(FXStreet, 'AUD/USD Price Forecast: Doji high guards bulls as Fed bets bite', "
            "fxstreet.com/news/aud-usd-price-forecast-doji-high-guards-bulls-as-fed-bets-bite-"
            "202609112201 -- corroborated by a separate same-day Mitrade wrap quoting AUD/USD at "
            "0.7176 after 'a firmer-than-expected US inflation print that would normally weigh on the "
            "Aussie', mitrade.com/au/insights/news/live-news/article-1-2080126-20260911). 0.17% is "
            "under the ~0.3% LOW line. FLAG: the Phase 1 relevance "
            "citation for this pair instead cites an older, dated Aug 2022 instance ('the dollar fell "
            "roughly 1.1%' on a downside CPI surprise) -- that figure describes a broad-dollar move on "
            "an outlier historical event, not this pair's typical CPI-day reaction, so it was not used "
            "here; the more representative and better-dated 2026-09-11 CPI-day figure was used instead "
            "for magnitude purposes."
        ),
    ),
    ("CPI m/m", "NZDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated WebSearch finding (from Phase 1's own relevance citation, independently "
            "re-verified): a June 2026 US CPI undershoot (headline -0.4% m/m vs -0.1% forecast, y/y "
            "easing to 3.5% from 4.2%) sent NZDUSD to a one-month high near 0.5820, up nearly 1.23% on "
            "the day (TMGM, tmgm.com/en/analysis/market-news/article/new-zealand-dollar-soars-to-one-"
            "month-high-as-us-cpi-undershoots-202607141433). 1.23% is well over the ~0.8% HIGH line."
        ),
    ),
    ("CPI m/m", "USDCAD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated WebSearch finding, independently re-verified for this task: on the 2026-09-11 "
            "US CPI day, USDCAD rose 0.27% to trade around 1.3870, after an intraday high of 1.3882 "
            "in the immediate reaction to the CPI release (FXStreet, via Vantage Markets summary of the "
            "same day -- CPI came in-line, and CAD underperformed separately as oil fell over 4% that "
            "day). 0.27% is under the ~0.3% LOW line. Consistent with the Phase 1 relevance citation's "
            "own framing that CPI's initial impulse here is real but small, compounded (not replaced) "
            "by the same-day oil selloff -- CPI's own contribution is LOW-tier."
        ),
    ),
}


def get_magnitude(event_type: str, symbol: str) -> MagnitudeJudgment:
    """
    Returns the real, sourced magnitude tier for (event_type, symbol).
    Raises KeyError for anything outside the 94-pair RELEVANT scope --
    this never fabricates a judgment for a pair it doesn't recognize,
    including a real Phase 1 pair that was NOT_RELEVANT or UNVERIFIED
    there (magnitude is only ever researched for a confirmed-RELEVANT
    pair).
    """
    return _MAGNITUDE_TABLE[(event_type, symbol)]
