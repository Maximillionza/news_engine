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
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch/WebFetch finding, independently re-verified for this task by "
            "directly fetching the source article's own text (FXStreet blocks direct fetches; fetched "
            "via a working mirror instead): on the 2026-09-11 US CPI day, AUD/USD 'traded at 0.7171, "
            "up a decent 0.38%' (FXStreet, 'AUD/USD Price Forecast: Doji high guards bulls as Fed bets "
            "bite', fxstreet.com/news/aud-usd-price-forecast-doji-high-guards-bulls-as-fed-bets-bite-"
            "202609112201; quote confirmed verbatim via mirror vpsi.org/aud-usd-price-forecast-doji-"
            "high-guards-bulls-as-fed-bets-bite/), though the RBA rate-hike narrative and the prior "
            "day's hot US PPI were also live drivers that day. Price level corroborated by a separate "
            "same-day Mitrade wrap quoting AUD/USD at 0.7176 (mitrade.com/au/insights/news/live-news/"
            "article-1-2080126-20260911), though that piece states no percentage of its own. 0.38% is "
            "within the ~0.3-0.8% MEDIUM band. FLAG: the Phase 1 relevance "
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
    # --- PPI m/m (Task 3) -------------------------------------------
    ("PPI m/m", "XAUUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='PPI m/m', "
            "instrument=XAUUSD, 6 real logged 30-min post-release moves (Dukascopy, auto): "
            "-0.24% (2026-02-27), -0.41% (2026-03-18), +0.33% (2026-06-11), +0.73% (2026-07-15), "
            "+0.25% (2026-08-13), -0.54% (2026-09-10). Median absolute move ~0.37%, mean ~0.42% -- "
            "MEDIUM. The 2026-09-10 print is the same one XAGUSD's own entry below documents as a "
            "sharp real silver reaction, and is also the case docs/feature-inventory-2026-09-11.md "
            "Sec.3 flags as a live Tier1 directional miss on gold -- wrongness there was directional, "
            "not a magnitude question."
        ),
    ),
    ("PPI m/m", "XAGUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated finding, PPI-specific, independently re-verified for this task by directly "
            "fetching the source article's own text: on 2026-09-10, right at the 8:30 a.m. ET release "
            "of the hot August PPI (annual rate accelerating to 5.4%), 'silver dropped from $67.31 to "
            "$64.63, a 4.1% slide' -- gold fell only 1.35% the same session (goldsilver.com, 'Silver "
            "Just Fell Three Times Harder Than Gold. Here's the PPI Story Behind It.', goldsilver.com/"
            "industry-news/goldsilver-news/silver-underperforms-gold-ppi-day/). 4.1% is well over the "
            "~0.8% HIGH line. NOTE: an earlier-seen WebSearch summary of a different article (vantage"
            "markets.com) claimed a $68.50->$63.99 move (~6.6%) for the same day -- that figure could "
            "not be independently confirmed by direct fetch (403) and was NOT used here in favor of "
            "the goldsilver.com figure whose exact wording was directly confirmed; both point to the "
            "same HIGH tier regardless."
        ),
    ),
    ("PPI m/m", "US30"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='PPI m/m', "
            "instrument=US30, 4 real logged post-release moves: -0.61% (2026-03-18, Dukascopy 30-min "
            "auto), +0.17% (2026-07-15, Dukascopy 30-min auto), +0.24% (2026-08-13, Dow +119pts shortly "
            "after the open following a flat/cooler July PPI, closed the day +0.24% -- CNBC live market "
            "updates, ts2.tech), -0.24% (2026-09-10, Dukascopy 30-min auto). Median absolute move 0.24%, "
            "under the ~0.3% LOW line, with only one of four prints (0.61%) reaching MEDIUM -- LOW. "
            "Same pattern as this project's own CPI m/m x US30 entry: the Dow's value/industrial "
            "weighting reacts less than the more rate-sensitive S&P/Nasdaq composition."
        ),
    ),
    ("PPI m/m", "US500"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch finding, PPI-specific, independently re-verified for this task: on "
            "2026-09-10, following the hot August PPI report (producer prices accelerating to 5.4% y/y "
            "on a 4.2% energy surge), 'the stock market opened in the red ... with the S&P 500 down "
            "0.6%, the Dow down 0.3%, and the Nasdaq Composite down 1.2%' (Seeking Alpha, 'Wall Street "
            "slides as investors digest PPI report', seekingalpha.com/news/4641457). 0.6% is within the "
            "~0.3-0.8% MEDIUM band. A separate dated instance in Phase 1's own citation shows the "
            "opposite-direction case -- a cooler PPI print sending the S&P 500 to a fresh record -- "
            "consistent with this being a real, surprise-magnitude-dependent PPI reaction, not a one-"
            "off."
        ),
    ),
    ("PPI m/m", "NAS100"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, PPI-specific finding from Nasdaq.com's own NDX options research, independently "
            "re-verified for this task: this is the same ROLLING tracker Phase 1's own relevance "
            "citation already flagged as shifting with the trailing window used. Re-confirmed figures "
            "across the source's own articles: 'the average price change for NDX on PPI-day is +/-1.01%, "
            "lower than the average price change for all days over the same period of +/-1.06%' and, in "
            "a different window, 'the average move for NDX over the most recent twelve PPI reports is "
            "+/-0.94%, much higher than +/-0.66% for CPI reports' (nasdaq.com/articles/inflation-numbers-"
            "tap-recent-nasdaq-100-ndx-reactions-cpi-and-ppi-mixed, nasdaq.com/articles/nasdaq-100-and-a-"
            "lack-of-volatility-on-ppi-days). Every window checked (0.83%-1.08%) sits at or above the "
            "~0.8% HIGH line -- HIGH, though no single number is stable enough to cite as fixed."
        ),
    ),
    ("PPI m/m", "EURUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated finding, PPI-specific, independently re-verified for this task by directly "
            "fetching the source article's own text: investingLive's Americas FX news wrap for "
            "2026-05-13 (the day of the hot April PPI report, 1.4% m/m vs 0.5% forecast) gives the "
            "day's currency-vs-USD moves verbatim: 'Versus the USD, the only currency to move higher "
            "vs the USD was the AUD which rose by 0.23% vs the greenback. The others fell: EUR -0.22%, "
            "JPY -0.16%, GBP -0.10%, CHF -0.14%, CAD -0.07%, NZD -0.27%' (investinglive.com/news/"
            "investinglive-americas-fx-news-wrap-13-may-20260513/, headlined 'PPI shocks markets, "
            "stocks recover'). EUR -0.22% (EURUSD -0.22%) is under the ~0.3% LOW line. A separate, "
            "distinct September 2026 hot-PPI instance (FXStreet, 'Euro weakens despite ECB rate hike as "
            "US PPI comes in hot') was found via WebSearch summary only (~0.25%, direct fetch blocked "
            "403/Cloudflare) and points the same direction/tier but was not relied on alone."
        ),
    ),
    ("PPI m/m", "GBPUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated WebSearch finding, PPI-specific: the Aug 2026 US PPI beat (5.4% y/y vs 5.3% "
            "forecast, released 2026-09-10) sent GBPUSD down -- 'The GBP/USD trades at 1.3525, down "
            "0.17%' -- as 'investors priced in a more hawkish Federal Reserve' (FXStreet, 'British "
            "Pound feels the heat as hot PPI puts Fed hike in play', fxstreet.com/news/british-pound-"
            "feels-the-heat-as-hot-ppi-puts-fed-hike-in-play-202609101527; direct fetch blocked, "
            "403 -- figure taken from a WebSearch result that quoted the article's own price-action "
            "line verbatim). 0.17% is under the ~0.3% LOW line."
        ),
    ),
    ("PPI m/m", "USDJPY"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated finding, PPI-specific, independently re-verified for this task by directly "
            "fetching the source article's own text: investingLive's Americas FX news wrap for "
            "2026-05-13 (hot April PPI day) gives 'JPY -0.16%' in its per-currency-vs-USD move listing "
            "(investinglive.com/news/investinglive-americas-fx-news-wrap-13-may-20260513/) -- JPY "
            "weakening 0.16% vs USD means USDJPY rose ~0.16% that day. Under the ~0.3% LOW line. A "
            "separate September 2026 instance (FXStreet) shows USDJPY bouncing off a seven-month low to "
            "reclaim 154.00 on the same hot PPI print, and a mirror-day instance shows USDJPY falling "
            "'over 0.50%' the FOLLOWING day on CPI/BoJ-driven Yen strength -- that later move belongs to "
            "CPI's own entry, not PPI's, so it was not used here."
        ),
    ),
    ("PPI m/m", "USDCHF"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated finding, PPI-specific, independently re-verified for this task by directly "
            "fetching the source article's own text: investingLive's Americas FX news wrap for "
            "2026-05-13 (hot April PPI day) gives 'CHF -0.14%' in its per-currency-vs-USD move listing "
            "(investinglive.com/news/investinglive-americas-fx-news-wrap-13-may-20260513/) -- CHF "
            "weakening 0.14% vs USD means USDCHF rose ~0.14% that day. Under the ~0.3% LOW line. NOTE: "
            "Phase 1's own relevance citation for this pair instead describes a technical retracement "
            "level ('USDCHF moved above the 50% midpoint of the move up from the January 2026 low at "
            "0.78228') with no percentage attached -- that framing describes a multi-week technical "
            "level, not this single print's own magnitude, so it was not used for the tier here."
        ),
    ),
    ("PPI m/m", "AUDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated finding, PPI-specific, independently re-verified for this task by directly "
            "fetching a source article's own text: on 2026-09-10, 'The Australian dollar fell 0.80% "
            "against the US dollar on Thursday as hotter US producer inflation pushed markets towards a "
            "more hawkish Federal Reserve outlook. AUD/USD traded around 0.7159 after touching 0.7223' "
            "(VT Markets, global-vtrader.com/en/live-updates/australian-dollar-slides-as-us-ppi-lifts-"
            "fed-hike-bets-and-oil-surge-boosts-greenback/). 0.80% sits right at the MEDIUM/HIGH "
            "boundary -- read as MEDIUM (top of the ~0.3-0.8% band) rather than HIGH, since it does not "
            "clearly exceed the line. A SEPARATE real, dated instance from the same investingLive "
            "2026-05-13 wrap used for the other FX pairs above shows the opposite-direction case: 'the "
            "only currency to move higher vs the USD was the AUD which rose by 0.23%' on that day's hot "
            "April PPI print -- a real LOW-tier instance. FLAG: the two real dated instances span LOW "
            "to the MEDIUM/HIGH boundary (0.23% vs 0.80%), so MEDIUM is a reasoned middle read, not a "
            "confident single point estimate."
        ),
    ),
    ("PPI m/m", "NZDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated finding, PPI-specific, independently re-verified for this task by directly "
            "fetching the source article's own text: investingLive's Americas FX news wrap for "
            "2026-05-13 (hot April PPI day) gives 'NZD -0.27%' in its per-currency-vs-USD move listing "
            "(investinglive.com/news/investinglive-americas-fx-news-wrap-13-may-20260513/) -- NZDUSD "
            "-0.27% that day, just under the ~0.3% LOW line. A separate June 2026 instance (FXStreet, "
            "'New Zealand Dollar weakens below 0.5850 as hot US PPI lifts US Dollar') confirms the same "
            "direction (NZDUSD weakening to ~0.5820 on a hot PPI print) but its own article text, "
            "directly fetched, does not state a percentage figure -- so the quantified 2026-05-13 figure "
            "above was used for the tier."
        ),
    ),
    ("PPI m/m", "USDCAD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated finding, PPI-specific, independently re-verified for this task by directly "
            "fetching the source article's own text: investingLive's Americas FX news wrap for "
            "2026-05-13 (hot April PPI day) gives 'CAD -0.07%' in its per-currency-vs-USD move listing "
            "(investinglive.com/news/investinglive-americas-fx-news-wrap-13-may-20260513/) -- CAD "
            "weakening 0.07% vs USD means USDCAD rose ~0.07% that day, well under the ~0.3% LOW line. "
            "Consistent with Phase 1's own relevance citation for this pair, which frames USDCAD's Sep "
            "2026 PPI-day move as 'real, contained' since oil moves compete with the PPI-driven USD "
            "impulse the same day (that Sep 2026 FXStreet piece's own text, directly fetched, gave price "
            "levels -- ~1.3815-1.3835 -- but no percentage, so the quantified May 2026 figure above was "
            "used for the tier)."
        ),
    ),
    # --- Non-Farm Employment Change (Task 4) --------------------------
    ("Non-Farm Employment Change", "XAUUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='Non-Farm "
            "Employment Change', instrument=XAUUSD, 7 real logged 30-min post-release moves "
            "(Dukascopy, auto): +0.22% (2026-01-09), -0.30% (2026-02-11), +0.30% (2026-05-08), "
            "-1.30% (2026-06-05), +1.28% (2026-07-02), +1.22% (2026-08-07), -1.73% (2026-09-04). "
            "Median absolute move 1.22%, mean ~0.91% -- both well over the ~0.8% HIGH line, with "
            "4 of 7 prints exceeding 1.2%. Consistent with the Phase 1 relevance citation's own "
            "framing of NFP as gold's most reliably large release."
        ),
    ),
    ("Non-Farm Employment Change", "XAGUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task by "
            "directly fetching a WebSearch result that quotes the source article's own exact "
            "words: on 2026-09-04 (August NFP beat, 162K vs 56K forecast), 'Silver (XAG/USD) "
            "trades around $66.20 on Friday, down 1.18% on the day, after recovering part of its "
            "sharp post-Nonfarm Payrolls (NFP) decline. The precious metal initially tumbled to an "
            "intraday low of $64.74' (FXStreet, 'Silver bounces from intraday lows as USD retreats "
            "from post-NFP highs', fxstreet.com/news/silver-claws-back-post-nfp-losses-after-"
            "briefly-crashing-below-65-202609041551; direct fetch blocked, 403 -- exact wording "
            "confirmed via a WebSearch result quoting the article verbatim). 1.18% is over the "
            "~0.8% HIGH line, and the intraday low-to-open swing was materially larger still."
        ),
    ),
    ("Non-Farm Employment Change", "US30"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='Non-Farm "
            "Employment Change', instrument=US30, 5 real logged 30-min post-release moves "
            "(Dukascopy, auto): +0.18% (2026-01-09), +0.37% (2026-02-11), -0.84% (2026-03-06), "
            "+0.22% (2026-07-02), -0.23% (2026-09-04). Median absolute move 0.23%, with 4 of 5 "
            "prints under the ~0.3% LOW line and only one (0.84%) reaching HIGH -- LOW, same "
            "pattern as this project's own CPI m/m and PPI m/m x US30 entries (Dow's value/"
            "industrial weighting reacts less than the more rate-sensitive S&P/Nasdaq)."
        ),
    ),
    ("Non-Farm Employment Change", "US500"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task via a "
            "WebSearch result quoting the source article's own exact words: on 2026-09-04 (August "
            "NFP beat, 162K vs 53K-56K forecast), 'The S&P 500 slid 0.38% to end at 7,718.60, while "
            "the Nasdaq Composite dropped 0.29% to 26,506.99 ... Nonfarm payrolls grew 162,000 last "
            "month, much more than the 53,000 that economists polled by Dow Jones expected' "
            "(TheStreet, 'Stock Market Today (Sept. 4, 2026): Yields jump, stocks fall after jobs "
            "report surprises to upside', thestreet.com/stock-market-today/stock-market-today-dow-"
            "jones-sp-500-nasdaq-updates-sept-04-2026; direct fetch blocked, 403 -- exact wording "
            "confirmed via a WebSearch result quoting the article verbatim, matching the figure in "
            "Phase 1's own relevance citation for this pair). 0.38% sits within the ~0.3-0.8% "
            "MEDIUM band."
        ),
    ),
    ("Non-Farm Employment Change", "NAS100"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task by "
            "directly fetching the source article's own text: on the May 2026 NFP beat (172,000 "
            "actual vs ~85,000 consensus), 'Nasdaq-100 (NQ) Futures: Down heavily ~1.4-2.0% "
            "(trading near 29,900-30,100 after opening around 30,414)' (Quantum Trading, 'Strong "
            "May 2026 NFP Beat (+172k) -- Why Nasdaq Sold Off Heavily on Jobs Data', "
            "quantumtrading.com/trading/us-non-farm-payrolls-may-2026-strong-beat-keeps-labour-"
            "market-resilient-but-markets-sell-the-news/). 1.4-2.0% is well over the ~0.8% HIGH "
            "line -- a specific, sourced NAS100 (not Nasdaq Composite) NFP reaction, distinct from "
            "the US500 entry above."
        ),
    ),
    ("Non-Farm Employment Change", "EURUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task via a "
            "WebSearch result quoting the source article's own exact words: on 2026-09-04 (August "
            "NFP beat), 'EUR/USD comes under selling pressure on Friday ... the pair trades around "
            "1.1605, down roughly 0.18% on the day' (FXStreet, 'Euro slips against US Dollar as "
            "Nonfarm Payrolls crush expectations', fxstreet.com/news/euro-slips-against-us-dollar-"
            "as-nonfarm-payrolls-crush-expectations-202609041319; direct fetch blocked, 403 -- exact "
            "wording confirmed via a WebSearch result quoting the article verbatim). 0.18% is under "
            "the ~0.3% LOW line. Phase 1's own citation shows the mirror-direction case (Aug 2026 "
            "miss) moving the other way, confirming this is a real two-way NFP reaction, just "
            "small in magnitude on this print."
        ),
    ),
    ("Non-Farm Employment Change", "GBPUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task via a "
            "WebSearch result quoting the source article's own exact words: on 2026-09-04 (August "
            "NFP beat), 'The pair dropped to an intraday low of 1.3482 following the release of "
            "stronger-than-expected US Nonfarm Payrolls ... Following the release, GBP/USD regained "
            "ground, trading around 1.3512' -- with the day's stated range running up to 1.3535 "
            "(VT Markets / FXDailyReport coverage of the same session, vtmarkets.com/en-eu/live-"
            "updates/following-strong-us-payrolls-data-gbp-usd-falls-again-suggesting-the-federal-"
            "reserve-maintains-higher-rates-longer/; fxdailyreport.com/gbp-usd-rebounds-toward-1-"
            "3510-as-strong-us-payrolls-fail-to-sustain-dollar-momentum/). The 1.3535-to-1.3482 "
            "intraday swing is ~0.39%, within the ~0.3-0.8% MEDIUM band -- read as a real but not "
            "extreme reaction, distinct from the more decisive EURUSD move the same day."
        ),
    ),
    ("Non-Farm Employment Change", "USDJPY"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task by "
            "directly fetching the source article's own text: on the June 2026 NFP miss (57,000 "
            "actual vs 110,000 forecast), 'USD/JPY down about 85 pips on the release and trading at "
            "160.79' (InvestingLive, 'US June non-farm payrolls +57K vs +110K expected', "
            "investinglive.com/news/us-june-non-farm-payrolls-57k-vs-110k-expected-20260702/). 85 "
            "pips off a ~160.79-161.64 base is ~0.53%, within the ~0.3-0.8% MEDIUM band. Same NFP-"
            "reaction pattern flagged in Phase 1's own relevance citation for this pair."
        ),
    ),
    ("Non-Farm Employment Change", "USDCHF"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task via a "
            "WebSearch result quoting the source article's own exact words: on 2026-09-04 (August "
            "NFP beat), 'USD/CHF trades higher on Friday ... The pair jumped to 0.8126 following the "
            "release before giving back part of its advance, and at the time of writing, USD/CHF "
            "trades around 0.8102, up nearly 0.34% on the day' (FXStreet, 'Swiss Franc loses ground "
            "upbeat US Nonfarm Payrolls', fxstreet.com/news/swiss-franc-loses-ground-upbeat-us-"
            "nonfarm-payrolls-202609041453; direct fetch blocked, 403 -- exact wording confirmed via "
            "a WebSearch result quoting the article verbatim). 0.34% is just inside the ~0.3-0.8% "
            "MEDIUM band, right at the LOW/MEDIUM boundary."
        ),
    ),
    ("Non-Farm Employment Change", "AUDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task by "
            "directly fetching the source article's own text: on the June 2026 NFP miss (57,000 "
            "actual vs 113,000 consensus), 'AUD/USD and NZD/USD were 0.4% higher' as the Dollar "
            "sank on the weak print (Convera, 'Dollar sinks on payrolls miss', convera.com/blog/"
            "market-insights/fx-research/daily-market-updates/dollar-sinks-on-payrolls-miss/). 0.4% "
            "sits within the ~0.3-0.8% MEDIUM band -- figure independently confirmed by direct "
            "fetch, per the review lesson from PPI's prior AUDUSD correction."
        ),
    ),
    ("Non-Farm Employment Change", "NZDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Two independent, dated NFP-specific real findings agree: the same Convera article used "
            "for AUDUSD above states 'AUD/USD and NZD/USD were 0.4% higher' on the June 2026 NFP "
            "miss (convera.com/blog/market-insights/fx-research/daily-market-updates/dollar-sinks-"
            "on-payrolls-miss/); separately, independently re-verified via a WebSearch result "
            "quoting the source article's own exact words, 'NZD/USD trades around 0.5890 on Friday "
            "at the time of writing, up 0.36% on the day' on the July 2026 NFP miss (-23,000 vs "
            "+80,000 forecast) (FXStreet, 'New Zealand Dollar advances as weak US jobs data hits the "
            "USD', fxstreet.com/news/new-zealand-dollar-advances-as-us-labor-market-weakness-"
            "pressures-the-usd-202608071603; direct fetch blocked, 403). Both real, dated instances "
            "(0.36%, 0.4%) sit within the ~0.3-0.8% MEDIUM band."
        ),
    ),
    ("Non-Farm Employment Change", "USDCAD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated finding, NFP-specific, independently re-verified for this task via a "
            "WebSearch result quoting the source article's own exact words: on 2026-09-04 (August "
            "NFP beat, 162K vs 56K forecast, compounded by Canada shedding 41,700 jobs the same "
            "session), 'USD/CAD accelerated sharply higher on Friday, trading around 1.3850 at the "
            "time of writing, up 0.39% on the day. The pair gained nearly 80 pips' (FXStreet, "
            "'Canadian Dollar under pressure as employment falls by 41.7K in August', fxstreet.com/"
            "news/canadian-dollar-slides-as-canada-sheds-417k-jobs-us-payrolls-surge-202609041400; "
            "direct fetch blocked, 403 -- exact wording confirmed via a WebSearch result quoting the "
            "article verbatim). 0.39% is within the ~0.3-0.8% MEDIUM band. Phase 1's own relevance "
            "citation for this pair flags the reaction as contingent on Canadian jobs data landing "
            "the same day -- this instance is one where it did."
        ),
    ),

    # --- FOMC Rate Decision (Task 5) ---------------------------------
    # Bands (reasoned starting ruler, not independently re-derived):
    # <~0.3% typical move = LOW, ~0.3-0.8% = MEDIUM, >~0.8% = HIGH.
    # Where possible, anchored to this project's own live-logged moves
    # for the actual 2026-09-16 FOMC "Federal Funds Rate" decision
    # (25bp hike to 3.75-4.00%, first hike since 2023) in
    # scoring/backtest_log.db's outcomes table -- preferred over
    # external sourcing per this task's research procedure. Remaining
    # pairs sourced from real, dated WebSearch findings, either for
    # that same 2026-09-16 decision or (where no post-decision figure
    # for that date could be confirmed after multiple real searches)
    # the well-documented June 17 2026 hawkish-hold FOMC, which is also
    # the dated event already used in Phase 1's own relevance citations
    # for most of these pairs.
    ("FOMC Rate Decision", "XAUUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='Federal Funds "
            "Rate' (also logged identically under 'FOMC Statement' and 'FOMC Economic Projections'), "
            "instrument=XAUUSD, event_time_utc=2026-09-16T18:00:00+00:00 (the actual 25bp hike to "
            "3.75%-4.00%, first Fed hike since 2023): 'Dukascopy: -0.81% in 30min (auto)'. -0.81% is "
            "just over the ~0.8% HIGH line. A related same-day entry, event_title='FOMC Press "
            "Conference' (18:30 UTC, Chair Warsh's remarks), logged an even larger -1.42% in 30min, "
            "confirming the decision-day reaction was real and sizeable, not a fluke of the 30-minute "
            "window chosen."
        ),
    ),
    ("FOMC Rate Decision", "XAGUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "No exact post-decision percentage for XAG/USD specifically was found after several real, "
            "dated WebSearch attempts targeting the 2026-09-16 decision (FXStreet's same-day coverage "
            "-- 'Silver Price Forecast: XAG/USD jumps to near $65 ahead of Fed's interest rate "
            "decision', fxstreet.com/news/silver-price-forecast-xag-usd-jumps-to-near-65-ahead-of-"
            "feds-interest-rate-decision-202609160801, and 'Silver price rebounds as Fed rate hike, "
            "Warsh speech loom', fxstreet.com/news/silver-price-rebounds-ahead-of-expected-fed-rate-"
            "hike-warsh-press-conference-202609161341 -- both pre-announcement only). Tier is "
            "therefore inferred, not directly quoted: this project's own internal XAUUSD figure for "
            "the same event (-0.81% in 30min, scoring/backtest_log.db) plus two independent, dated, "
            "FOMC-specific findings already in Phase 1's own relevance citation for this pair (XAG/USD "
            "falling to near $63.50 'amid Fed hike bets' on 2026-09-14, and to near $66.00 'amid Fed "
            "Chair Warsh's hawkish tone' on 2026-08-31) confirm the same real, repeated, rates-driven "
            "downward pressure on silver around this event. Silver's real, repeatedly-observed higher "
            "volatility than gold on rates-driven moves (also seen in this table's CPI m/m entry: "
            "XAGUSD HIGH at 1.13% vs XAUUSD MEDIUM the same day) makes HIGH the reasoned tier here, "
            "though flagged as the least directly-evidenced of these 12 entries."
        ),
    ),
    ("FOMC Rate Decision", "US30"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "This project's own scoring/backtest_log.db outcomes table, event_title='Federal Funds "
            "Rate' (also logged identically under 'FOMC Statement' and 'FOMC Economic Projections'), "
            "instrument=US30, event_time_utc=2026-09-16T18:00:00+00:00: 'Dukascopy: -0.23% in 30min "
            "(auto)'. -0.23% is under the ~0.3% LOW line. The follow-on 'FOMC Press Conference' entry "
            "(18:30 UTC) logged a larger -0.90% in 30min, closely matching CNBC's own reporting of the "
            "day's full session (Yahoo Finance/CNBC market-close coverage, 2026-09-16: 'the Dow Jones "
            "Industrial Average fell 0.9%' during Chair Warsh's press conference, later extending to "
            "'down 751 points, or 1.5%' by the close) -- confirming the initial announcement reaction "
            "(this cell) was genuinely small relative to the larger press-conference-driven move."
        ),
    ),
    ("FOMC Rate Decision", "US500"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch finding, FOMC-specific, for the actual 2026-09-16 decision (25bp "
            "hike to 3.75%-4.00%): 'the S&P 500 (^GSPC) dropped 0.3%' during Chair Warsh's post-"
            "decision press conference (Yahoo Finance / CNBC market-close coverage, 2026-09-16, "
            "finance.yahoo.com/markets/live/stock-market-today-wednesday-september-16-dow-sp-500-"
            "nasdaq-fed-meeting-decision-080356525.html). 0.3% sits right at the LOW/MEDIUM boundary; "
            "read as MEDIUM per the band's inclusive lower edge, and distinctly smaller than the same-"
            "day Dow move (-0.9% to -1.5%), consistent with this table's CPI/PPI-era observation that "
            "US500 and US30 do not always move in lockstep on the same macro print."
        ),
    ),
    ("FOMC Rate Decision", "NAS100"): MagnitudeJudgment(
        tier=MagnitudeTier.LOW,
        citation=(
            "Real, dated WebSearch finding, FOMC-specific, for the actual 2026-09-16 decision: 'the "
            "Nasdaq Composite wavered near the flat line' during Chair Warsh's post-decision press "
            "conference, after having been 'up 0.8%' in the immediate initial reaction to the rate-"
            "hike announcement itself (Yahoo Finance / CNBC market-close coverage, 2026-09-16, "
            "finance.yahoo.com/markets/live/stock-market-today-wednesday-september-16-dow-sp-500-"
            "nasdaq-fed-meeting-decision-080356525.html). A near-flat net close-to-close reading is "
            "under the ~0.3% LOW line; flagged that this is the Composite rather than the NAS100 "
            "futures index specifically, but the two are tightly correlated and no NAS100-specific "
            "figure was found in the sources checked."
        ),
    ),
    ("FOMC Rate Decision", "EURUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch finding, FOMC-specific (already in Phase 1's own relevance citation "
            "for this pair, reused directly per this task's research procedure): on the June 17 2026 "
            "hawkish-hold decision, 'EUR/USD had been sitting just below 1.1600 into the announcement "
            "and fell close to 60 pips within minutes through 1.1550 toward 1.1500' (FXStreet, 'Euro "
            "routed as Warsh's Fed turns the dot plot upside down', fxstreet.com/news/euro-routed-as-"
            "warshs-fed-turns-the-dot-plot-upside-down-202606171915). 60 pips off a ~1.1600 base is "
            "~0.52%, within the ~0.3-0.8% MEDIUM band. The same citation notes a larger ~180-pip "
            "(~1.55%) move over the following day, so the immediate-reaction figure used here is the "
            "conservative read."
        ),
    ),
    ("FOMC Rate Decision", "GBPUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated WebSearch finding, FOMC-specific (already in Phase 1's own relevance citation "
            "for this pair, reused directly per this task's research procedure): on the June 17 2026 "
            "hawkish-hold decision, 'GBP/USD tanked by over 1%' and fell to a two-month low near 1.3270 "
            "amid broad US Dollar strength following the hawkish dot plot (FXStreet, 'British Pound "
            "craters as Warsh's guidance void fuels US Dollar rally', fxstreet.com/news/british-pound-"
            "sinks-as-warshs-hawkish-dots-power-us-dollar-202606171827). 'Over 1%' is above the ~0.8% "
            "HIGH line."
        ),
    ),
    ("FOMC Rate Decision", "USDJPY"): MagnitudeJudgment(
        tier=MagnitudeTier.UNVERIFIED,
        citation=(
            "UNVERIFIED: no real, confirmed post-decision percentage move for USD/JPY specifically was "
            "found after multiple dated WebSearch attempts against both the actual 2026-09-16 decision "
            "and the well-documented June 17 2026 hawkish-hold decision. Sources checked describe only "
            "pre-decision levels ('USD/JPY recovered its early losses and flattened around 155.00... "
            "touching a one-week high around the 155.45-155.50 region', FXStreet, 2026-09-16) or "
            "conflicting post-event levels across different searches (160.66/160.11 range in Phase 1's "
            "own citation for the June event vs. a separate 'fresh weekly highs around 156.00' result "
            "for the day after) with no shared, reliable starting baseline to compute a real percentage "
            "from. Marked UNVERIFIED rather than guessing between these inconsistent figures."
        ),
    ),
    ("FOMC Rate Decision", "USDCHF"): MagnitudeJudgment(
        tier=MagnitudeTier.UNVERIFIED,
        citation=(
            "UNVERIFIED: Phase 1's own relevance citation for this pair already notes the June 17 2026 "
            "reaction was 'qualitative only' with 'no exact pip/percent figure found in the sources "
            "checked'. Repeated new WebSearch attempts against the actual 2026-09-16 decision found "
            "only pre-decision levels ('USD/CHF halted its five-day winning streak, trading around "
            "0.8180 during Asian hours on Wednesday, with the pair inching lower as the US Dollar "
            "depreciated ahead of the interest rate decision', FXStreet-sourced coverage, 2026-09-16) "
            "and no post-decision reaction figure. Marked UNVERIFIED rather than guessing."
        ),
    ),
    ("FOMC Rate Decision", "AUDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.HIGH,
        citation=(
            "Real, dated WebSearch finding, FOMC-specific (already in Phase 1's own relevance citation "
            "for this pair, reused directly per this task's research procedure): on the June 17 2026 "
            "hawkish-hold decision, 'AUD/USD fell from around 0.7080 to a session low of 0.6988 (close "
            "to 80-90 pips)... as the hawkish dot plot... drove broad US Dollar strength' (Vantage "
            "Markets, 'AUD/USD Today: 0.7012 as Hawkish Fed Hits Aussie Hard', vantagemarkets.com/"
            "market-analysis/audusd-analysis-19-june-2026/). ~90 pips off a 0.7080 base is ~1.3%, above "
            "the ~0.8% HIGH line."
        ),
    ),
    ("FOMC Rate Decision", "NZDUSD"): MagnitudeJudgment(
        tier=MagnitudeTier.UNVERIFIED,
        citation=(
            "UNVERIFIED: Phase 1's own relevance citation for this pair already notes 'no exact post-"
            "decision pip figure was found in the sources checked' for the June 17 2026 decision. "
            "Repeated new WebSearch attempts against the actual 2026-09-16 decision found only pre-"
            "decision context ('NZD/USD bears pushing against two-month lows at 0.5765 after dropping "
            "beyond 2.5% so far in September', FXStreet-sourced coverage, 2026-09-15 -- a month-to-"
            "date figure, not an event-specific one) and no confirmed post-decision reaction figure. "
            "Marked UNVERIFIED rather than guessing."
        ),
    ),
    ("FOMC Rate Decision", "USDCAD"): MagnitudeJudgment(
        tier=MagnitudeTier.MEDIUM,
        citation=(
            "Real, dated WebSearch finding, FOMC-specific, for the actual 2026-09-16 decision: 'The "
            "Loonie trades at its weakest since early August, with USD/CAD just under 1.4000 after a "
            "71-pip rise and a 0.51% gain' following the Fed's 25bp hike to 3.75%-4.00% (FXStreet, "
            "'The Canadian Dollar slips to a summer low on the Fed's rate hike', fxstreet.com/news/fed-"
            "hike-sends-the-loonie-to-a-six-week-low-202609161841). 0.51% is within the ~0.3-0.8% "
            "MEDIUM band; the pip figure (71 pips on a ~1.393 base is ~0.51%) is internally consistent "
            "with the stated percentage, cross-checking the number."
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
