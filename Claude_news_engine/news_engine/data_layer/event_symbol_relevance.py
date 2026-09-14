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
    ("PPI m/m", "XAUUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Internal, dated, PPI-specific evidence from this project's own live "
        "scoring DB (scoring/backtest_log.db, tier1_predictions/outcomes "
        "tables): 6 real PPI m/m occurrences logged against XAUUSD in 2026 "
        "(2026-02-27, 2026-03-18, 2026-06-11, 2026-07-15, 2026-08-13, "
        "2026-09-10) each with a Dukascopy-measured 30-min price move "
        "(e.g. -0.54% on 2026-09-10, +0.73% on 2026-07-15); the 2026-09-10 "
        "case is also the one docs/feature-inventory-2026-09-11.md Sec.3 "
        "flags as a real live miss (Tier1 called Certain/bullish, actual "
        "was bearish) -- the wrongness was directional, but the case is "
        "real evidence PPI itself reaches gold, not borrowed from CPI",
    ),
    ("PPI m/m", "XAGUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, PPI-specific: the same Sep 10 2026 "
        "hot US PPI print (August data, annual PPI accelerating to 5.4% "
        "y/y) drove silver down sharply from $68.50 to $63.99 as Fed "
        "rate-hike odds rose above 73% "
        "(vantagemarkets.com/market-analysis/xagusd-silver-price-today-"
        "rate-hike-bets-september-11-2026/) -- a specific, sourced XAGUSD "
        "reaction to PPI itself, not reasoned by analogy from gold or CPI",
    ),
    ("PPI m/m", "US30"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Internal, dated, PPI-specific evidence from this project's own live "
        "scoring DB (scoring/backtest_log.db): 4 real PPI m/m occurrences "
        "logged against US30 in 2026 (2026-03-18, 2026-07-15, 2026-08-13, "
        "2026-09-10) with Dukascopy-measured moves, plus the 2026-08-13 row "
        "carries an independently-sourced note: 'Dow +119pts / +0.3% "
        "shortly after the open following flat July PPI ... closed the day "
        "+0.24%' (CNBC live market updates, ts2.tech, 2026-08-13) -- a real, "
        "quantified US30 reaction to PPI itself",
    ),
    ("PPI m/m", "US500"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, PPI-specific: Sep 2026 hot PPI "
        "(producer prices accelerating to 5.4% y/y on a 4.2% energy surge) "
        "-- 'stock market opened in the red ... S&P 500 down 0.6%' as the "
        "data pushed September rate-hike odds to 63% (Seeking Alpha, "
        "'Wall Street slides as investors digest PPI report', "
        "seekingalpha.com/news/4641457); a separate dated instance shows "
        "the opposite-direction case -- a cooler PPI print sent the S&P 500 "
        "to a fresh record as rate-hike odds fell (bitcoinworld.co.in/"
        "sp-500-record-cooler-ppi-rate-cut-odds/) -- both real, PPI-specific",
    ),
    ("PPI m/m", "NAS100"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, PPI-specific finding from Nasdaq.com's own NDX options "
        "research, re-verified 2026-09-14: this is a ROLLING tracker whose "
        "exact figures shift with the trailing window used -- re-fetched "
        "values found across the same source's own articles include "
        "+/-1.01% (PPI day) vs +/-1.06% (average day), +/-1.00% vs +/-1.08%, "
        "+/-0.83% vs +/-0.86% (2024 only), and +/-0.94% vs +/-0.89% (a "
        "trailing-twelve-PPI-report window) -- no single number is stable "
        "enough to state as fixed, but every window checked shows a real, "
        "PPI-specific NDX volatility print, distinct from and generally "
        "smaller than CPI's own (already-cited) premium, not reasoned by "
        "analogy (nasdaq.com/articles/inflation-numbers-tap-recent-nasdaq-"
        "100-ndx-reactions-cpi-and-ppi-mixed, nasdaq.com/articles/nasdaq-"
        "100-and-a-lack-of-volatility-on-ppi-days)",
    ),
    ("PPI m/m", "EURUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch findings, PPI-specific: hot Aug 2026 US PPI "
        "(annual producer inflation to 5.4% vs 5.3% forecast) 'reaffirmed "
        "Fed rate-hike bets and boosted the US Dollar', weighing on EURUSD "
        "(FXStreet, 'Euro weakens despite ECB rate hike as US PPI comes in "
        "hot', fxstreet.com/news/euro-weakens-despite-ecb-rate-hike-as-us-"
        "ppi-comes-in-hot-202609101256); a separate softer-PPI instance "
        "(Jul 2026 data, released Aug 2026) shows only a muted EURUSD "
        "reaction (fxstreet.com/news/euro-edges-higher-against-us-dollar-"
        "after-soft-us-ppi-data-202608131430) -- real but surprise-"
        "magnitude-dependent, same pattern as CPI's own EURUSD entry",
    ),
    ("PPI m/m", "GBPUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, PPI-specific: the Aug 2026 US PPI "
        "beat (5.4% y/y vs 5.3% forecast) sent GBPUSD down to 1.3525 "
        "(-0.17%) as 'investors priced in a more hawkish Federal Reserve' "
        "and Fed-hike odds rose above 70% (FXStreet, 'British Pound feels "
        "the heat as hot PPI puts Fed hike in play', fxstreet.com/news/"
        "british-pound-feels-the-heat-as-hot-ppi-puts-fed-hike-in-play-"
        "202609101527) -- a specific, sourced GBPUSD reaction to PPI "
        "itself, not borrowed from CPI's own (separately cited) reaction",
    ),
    ("PPI m/m", "USDJPY"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch findings, PPI-specific: Aug 2026 US PPI "
        "(5.4% y/y) 'reaffirmed Fed rate-hike bets and boosted the US "
        "Dollar ... which weighed heavily on' USDJPY; a separate, older "
        "dated instance shows USDJPY approaching 145.00 as 'US PPI rose "
        "strongly' (fxstreet.com/news/usd-jpy-approaches-14500-as-us-ppi-"
        "rose-strongly-202308111304); Sep 11 2026 also has the mirror case "
        "-- 'Japanese Yen edges higher on PPI, focus turns to US CPI' "
        "(fxstreet.com/news/japanese-yen-edges-higher-as-ppi-reaffirms-boj-"
        "rate-hike-bets-and-usd-bulls-await-us-cpi-202609110131) -- real, "
        "PPI-specific reactions on both sides of the pair",
    ),
    ("PPI m/m", "USDCHF"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, PPI-specific: May 2026 US PPI came "
        "in far above expectations (1.4% m/m, 6.0% y/y, core PPI also "
        "beating) and 'caused the US dollar to move higher after the US "
        "PPI data', pushing USDCHF above the 50% midpoint of its move up "
        "from the January 2026 low (investinglive.com/technical-analysis/"
        "the-usd-moved-higher-after-the-us-ppi-data-but-the-rise-has-had-"
        "its-limits-what-next-20260513/) -- a real, dated, PPI-specific "
        "USDCHF reaction, distinct from CPI's own (separately cited) move",
    ),
    ("PPI m/m", "AUDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, PPI-specific. CORRECTED 2026-09-14 "
        "after review flagged the prior version's number/direction as "
        "mismatched to its own cited URL -- re-checked against the "
        "underlying article rather than just flipping the sign: Sep 10 "
        "2026 hot US PPI (Aug data, 5.4% y/y vs 5.3% forecast) drove "
        "AUDUSD to a 0.80% LOSS on the day, from an intraday peak of "
        "0.7223 down to 0.7159, as the print 'triggered pricing for a more "
        "hawkish Federal Reserve' (VT Markets, 'Australian dollar slides "
        "as US PPI lifts Fed hike bets and oil surge boosts greenback', "
        "global-vtrader.com/en/live-updates/australian-dollar-slides-as-"
        "us-ppi-lifts-fed-hike-bets-and-oil-surge-boosts-greenback/ -- "
        "direct fetch returned HTTP 403, so this figure rests on multiple "
        "independent WebSearch result summaries that all independently "
        "repeat the same 0.7223->0.7159/-0.80% numbers, not on a single "
        "unverifiable claim). A SEPARATE, earlier dated instance (May 13 "
        "2026, April PPI: 1.4% m/m vs 0.5% forecast, 6.0% y/y vs 4.9% "
        "forecast) is the opposite-direction real case this entry "
        "previously misattributed to the Sep figure: AUDUSD actually "
        "GAINED roughly 0.3% that day, climbing through the session before "
        "pulling back from its peak (FXStreet, 'Australian Dollar retreats "
        "from session peak as US PPI print beats sharply', fxstreet.com/"
        "news/australian-dollar-retreats-from-session-peak-as-us-ppi-print"
        "-beats-sharply-202605132234) -- both real, dated, PPI-specific "
        "reactions, not reasoned by analogy from CPI",
    ),
    ("PPI m/m", "NZDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch findings, PPI-specific: multiple dated "
        "instances of NZDUSD moving on US PPI releases -- 'New Zealand "
        "Dollar weakens below 0.5850 as hot US PPI lifts US Dollar' "
        "(Jun 2026, fxstreet.com/news/new-zealand-dollar-weakens-below-"
        "05850-as-stronger-us-ppi-lifts-us-dollar-202606120655) and "
        "'New Zealand Dollar gives back gains as US PPI offsets RBNZ "
        "expectations' (May 2026, fxstreet.com/news/new-zealand-dollar-"
        "gave-back-gains-as-hot-us-ppi-offsets-rbnz-expectations-rise-"
        "202605132236), with a US PPI print of 6.5% y/y (vs 5.7% prior) "
        "cited as the driver -- real, dated, PPI-specific, not borrowed "
        "from CPI's own NZDUSD reaction",
    ),
    ("PPI m/m", "USDCAD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, PPI-specific: Aug 2026 US PPI "
        "(5.4% y/y, above the 5.3% forecast) left USDCAD trading around "
        "1.3815-1.3835 -- 'USD/CAD held modest gains as the US Dollar lost "
        "momentum ... despite US PPI data showing that producer inflation "
        "picked up again', with higher oil prices offsetting the USD-"
        "strength impulse the same day (FXStreet, 'Canadian Dollar trades "
        "under pressure as US PPI data supports Fed hike bets', "
        "fxstreet.com/news/canadian-dollar-trades-under-pressure-as-us-ppi"
        "-data-supports-fed-hike-bets-202609101551) -- a real, contained "
        "but PPI-specific reaction, consistent with Layer2's oil-linked "
        "USDCAD nuance (oil competes with, doesn't erase, PPI's own pull)",
    ),
    ("Non-Farm Employment Change", "XAUUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Two independent, dated NFP-specific sources agree: Layer1_Event_to_"
        "USD's 2026-06-NFP row (June 2026 print +57,000 vs +110-115,000 "
        "forecast -- 'Sept 2026 hike probability 67% -> ~50%; DXY posted "
        "biggest weekly decline since April; gold best week since March'), "
        "and this project's own live scoring DB (scoring/backtest_log.db, "
        "outcomes table): 7 real NFP occurrences logged against XAUUSD in "
        "2026 with Dukascopy-measured 30-min moves, including the matching "
        "2026-07-02 row (June print's release date) at +1.28% and the most "
        "recent 2026-09-04 row (August print, 162K vs 56K forecast) at "
        "-1.73% -- both directions real and NFP-specific, not borrowed",
    ),
    ("Non-Farm Employment Change", "XAGUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the Sep 4 2026 "
        "release (August print, 162K vs 56K forecast -- a beat) drove "
        "silver down sharply to an intraday low of $64.74 as the stronger "
        "print boosted the US Dollar and Treasury yields, before a partial "
        "recovery left it trading around $66.20, down 1.18% on the day "
        "(FXStreet, 'Silver claws back post-NFP losses after briefly "
        "crashing below 65', fxstreet.com/news/silver-claws-back-post-nfp-"
        "losses-after-briefly-crashing-below-65-202609041551)",
    ),
    ("Non-Farm Employment Change", "US30"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Internal, dated, NFP-specific evidence from this project's own "
        "live scoring DB (scoring/backtest_log.db, outcomes table): 5 real "
        "NFP occurrences logged against US30 in 2026 with Dukascopy-"
        "measured 30-min moves (e.g. 2026-03-06: -0.84%, 2026-09-04: "
        "-0.23%), corroborated by real WebSearch: the same Sep 4 2026 "
        "August-beat release (162K vs 55K forecast) sent the Dow down "
        "271.86 points (-0.51%) that day on revived rate-hike fears "
        "(TheStreet, 'Stock Market Today (Sept. 4, 2026): Yields jump, "
        "stocks fall after jobs report surprises to upside', thestreet.com/"
        "stock-market-today/stock-market-today-dow-jones-sp-500-nasdaq-"
        "updates-sept-04-2026)",
    ),
    ("Non-Farm Employment Change", "US500"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the same Sep 4 2026 "
        "August-beat release (162K vs 55K forecast, unemployment steady at "
        "4.1%) -- 'good news is bad news' reaction sent the S&P 500 down "
        "0.38% to close at 7,718.60 on revived Fed rate-hike expectations "
        "(TheStreet, same URL as the US30 entry) -- a specific, sourced "
        "US500 reaction to NFP itself",
    ),
    ("Non-Farm Employment Change", "NAS100"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the May 2026 NFP beat "
        "(172,000 actual vs ~85,000 consensus) triggered a sharp 'good "
        "news is bad news' reversal in growth-sensitive names -- 'Nasdaq-"
        "100 Futures down heavily around 1.4-2.0%' as cash equities opened "
        "(Quantum Trading, 'Strong May 2026 NFP Beat (+172k) -- Why Nasdaq "
        "Sold Off Heavily on Jobs Data', quantumtrading.com/trading/us-non-"
        "farm-payrolls-may-2026-strong-beat-keeps-labour-market-resilient-"
        "but-markets-sell-the-news/) -- a specific, sourced NAS100 (not "
        "Nasdaq Composite) NFP reaction, distinct from the US500 entry",
    ),
    ("Non-Farm Employment Change", "EURUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the Sep 4 2026 "
        "August-beat release (162K vs 56K forecast) sent EURUSD down to "
        "around 1.1605 (-0.18% on the day), retreating from an intraday "
        "high of 1.1633, as the US Dollar strengthened and yields rose "
        "(FXStreet, 'Euro slips against US Dollar as Nonfarm Payrolls "
        "crush expectations', fxstreet.com/news/euro-slips-against-us-"
        "dollar-as-nonfarm-payrolls-crush-expectations-202609041319) -- "
        "the mirror-direction case (Aug 7 2026, July print's -23,000 "
        "miss) is headlined 'Euro surges as shocking US NFP slashes Fed "
        "September hike odds' (fxstreet.com/news/euro-surges-as-shocking-"
        "us-nfp-reverses-fed-september-hike-expectations-202608071300), "
        "confirming the pair moves on NFP in both directions",
    ),
    ("Non-Farm Employment Change", "GBPUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the Sep 4 2026 "
        "August-beat release (162K vs 53K consensus) sent GBPUSD down to "
        "an intraday low of 1.3482 before recovering toward 1.3510-1.3512 "
        "as the initial Dollar strength faded (VT Markets, 'Following "
        "strong US payrolls data, GBP/USD falls again, suggesting the "
        "Federal Reserve maintains higher rates longer', vtmarkets.com/en-"
        "eu/live-updates/following-strong-us-payrolls-data-gbp-usd-falls-"
        "again-suggesting-the-federal-reserve-maintains-higher-rates-"
        "longer/; FXDailyReport, 'GBP/USD Rebounds Toward 1.3510 as Strong "
        "US Payrolls Fail to Sustain Dollar Momentum', fxdailyreport.com/"
        "gbp-usd-rebounds-toward-1-3510-as-strong-us-payrolls-fail-to-"
        "sustain-dollar-momentum/)",
    ),
    ("Non-Farm Employment Change", "USDJPY"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the June 2026 miss "
        "(57,000 actual vs 110,000 forecast) sent USDJPY dropping about 85 "
        "pips to trade at 160.79 as the weak print eliminated near-term "
        "Fed-hike odds and supported the yen (InvestingLive, 'US June non-"
        "farm payrolls +57K vs +110K expected', investinglive.com/news/us-"
        "june-non-farm-payrolls-57k-vs-110k-expected-20260702/) -- note "
        "USDJPY's NFP reaction is layered with real, separately-documented "
        "BoJ-intervention speculation around the same releases, consistent "
        "with Tier1 prompt's PER-INSTRUMENT QUIRKS on this pair",
    ),
    ("Non-Farm Employment Change", "USDCHF"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the Sep 4 2026 "
        "August-beat release (162K vs 56K forecast) sent USDCHF jumping to "
        "0.8126 before settling around 0.8102, up nearly 0.34% on the day "
        "(FXStreet, 'Swiss Franc loses ground upbeat US Nonfarm Payrolls', "
        "fxstreet.com/news/swiss-franc-loses-ground-upbeat-us-nonfarm-"
        "payrolls-202609041453) -- a real, dated, NFP-specific USDCHF "
        "reaction, distinct from CPI/PPI's own (separately cited) moves",
    ),
    ("Non-Farm Employment Change", "AUDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the June 2026 miss "
        "(57,000 actual vs 113,000 consensus) sent the US Dollar to a "
        "two-week low and AUDUSD 0.4% HIGHER in reaction, as reduced Fed-"
        "hike odds and lower yields weakened the Dollar (Convera, 'Dollar "
        "sinks on payrolls miss', convera.com/blog/market-insights/fx-"
        "research/daily-market-updates/dollar-sinks-on-payrolls-miss/) -- "
        "figure double-checked against the article's own stated direction "
        "and magnitude before use, per the review lesson from PPI's prior "
        "AUDUSD correction",
    ),
    ("Non-Farm Employment Change", "NZDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the July 2026 miss "
        "(-23,000 actual vs +80,000 forecast, with a combined 103,000 "
        "downward revision to prior months) sent NZDUSD to around 0.5890, "
        "up 0.36% on the day, as the weak print pressured the US Dollar "
        "(FXStreet, 'New Zealand Dollar advances as weak US jobs data hits "
        "the USD', fxstreet.com/news/new-zealand-dollar-advances-as-us-"
        "labor-market-weakness-pressures-the-usd-202608071603) -- real, "
        "dated, NFP-specific, not reasoned by analogy from AUDUSD",
    ),
    ("Non-Farm Employment Change", "USDCAD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, NFP-specific: the Sep 4 2026 "
        "August-beat release (162K vs 56K forecast) accelerated USDCAD "
        "sharply higher to trade around 1.3850, gaining nearly 80 pips, as "
        "the simultaneous Canadian jobs report (-41,700) compounded the "
        "US-Dollar-strength impulse rather than offsetting it (FXStreet, "
        "'Canadian Dollar slides as Canada sheds 41.7K jobs, US payrolls "
        "surge', fxstreet.com/news/canadian-dollar-slides-as-canada-sheds-"
        "417k-jobs-us-payrolls-surge-202609041400) -- a separate, earlier "
        "June 2026 instance shows the OPPOSITE dynamic (US and Canadian "
        "NFP-equivalent data both beating on the same day, cancelling each "
        "other out), so USDCAD's NFP reaction is real but contingent on "
        "whether Canadian jobs data lands the same day",
    ),
    ("FOMC Rate Decision", "XAUUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Internal, real, live-logged evidence from this project's own "
        "scoring DB (scoring/backtest_log.db, tier1_predictions table): "
        "'Federal Funds Rate' and 'FOMC Statement' predictions for the "
        "2026-09-16 FOMC meeting logged against XAUUSD at Certain "
        "confidence (85.5% CME FedWatch-implied probability of a 25bp "
        "hike as of 2026-09-12, up from ~56-70% on 2026-09-10, EFFR 3.63% "
        "per Fed H.15) -- real evidence the event reaches this symbol, "
        "consistent with Layer1_Event_to_USD's dated Fed rows (e.g. the "
        "2025-10-29-FOMC cut and Dec 2025 succession-storm DXY/yield move)",
    ),
    ("FOMC Rate Decision", "XAGUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: as of 2026-09-14, "
        "XAG/USD fell to near $63.50 'amid Fed hike bets' with the Sept "
        "16 2026 decision priced at an 87% probability of a 25bp hike (up "
        "from 59% the prior week) (FXStreet, 'Silver Price Forecast: "
        "XAG/USD falls to near $63.50 amid Fed hike bets, higher oil "
        "prices', fxstreet.com/news/silver-price-forecast-xag-usd-falls-"
        "to-near-6350-amid-fed-hike-bets-higher-oil-prices-202609140747); "
        "separately, an Aug 31 2026 FXStreet piece documents XAG/USD "
        "falling to near $66.00 specifically 'amid Fed Chair Warsh's "
        "hawkish tone' -- two independent, dated, FOMC-specific reactions",
    ),
    ("FOMC Rate Decision", "US30"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Internal, real, live-logged evidence (scoring/backtest_log.db, "
        "tier1_predictions table): 'Federal Funds Rate'/'FOMC Statement' "
        "predictions for 2026-09-16 logged against US30 at Certain "
        "confidence; corroborated by real, dated WebSearch, FOMC-specific: "
        "the prior June 17 2026 FOMC decision (hold at 3.50-3.75%, but a "
        "hawkish dot plot -- median 2026 fed funds dot to ~3.8% from 3.4%) "
        "sent the Dow Jones down 507.12 points (-0.97%) that day (X/"
        "Markets Today market-close summary, 2026-06-17; corroborated by "
        "CNBC 'Dow closes 500 points lower as Warsh's first Fed meeting "
        "sets off surge in bond yields', cnbc.com/2026/06/16/stock-market-"
        "today-live-updates.html)",
    ),
    ("FOMC Rate Decision", "US500"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: the June 17 2026 "
        "FOMC decision (rates held at 3.50-3.75%, but 9 of 19 members' dot "
        "plot pointed to a 2026 hike) -- 'S&P 500 Drops 1.2% as Fed "
        "Signals 2026 Rate Hike', the index declined 91.25 points (-1.21%) "
        "to close at 7,420.10 that day (X/Markets Today market-close "
        "summary, 2026-06-17; Swingfolio, swingfolio.com/daily/us/2026-06-"
        "17/afternoon; TheStreet, 'S&P 500, Nasdaq plummet as Fed meeting "
        "points to rate hike in late 2026', thestreet.com/stock-market-"
        "today/stock-market-today-dow-jones-sp-500-nasdaq-updates-june-17"
        "-2026)",
    ),
    ("FOMC Rate Decision", "NAS100"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: the same June 17 "
        "2026 hawkish-hold decision -- the Nasdaq 100 climbed steadily "
        "into the meeting then sold off sharply around 14:00-15:00 UTC on "
        "June 16, shedding over 500 points to lows near 29,800, with a "
        "partial recovery fading after the June 17 decision and Chair "
        "Warsh's press conference to settle back near 30,100 (Vantage "
        "Markets, 'NAS100 Slides After Fed Signals Rate Hike Risk for "
        "2026', vantagemarkets.com/market-analysis/nas100-analysis-"
        "hawkish-fed-june-18-2026/); TheStreet's own headline for the day "
        "explicitly names the Nasdaq alongside the S&P 500 plummeting",
    ),
    ("FOMC Rate Decision", "EURUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: the June 17 2026 "
        "hawkish-hold decision (2026 fed funds dot to ~3.8% from 3.4%) -- "
        "EUR/USD had been sitting just below 1.1600 into the announcement "
        "and fell close to 60 pips within minutes through 1.1550 toward "
        "1.1500, then continued falling roughly 180 pips over the "
        "following day to a 1.1420 session low (FXStreet, 'Euro routed as "
        "Warsh's Fed turns the dot plot upside down', fxstreet.com/news/"
        "euro-routed-as-warshs-fed-turns-the-dot-plot-upside-down-"
        "202606171915; Vantage Markets, 'EURUSD Falls to Multi-Week Low "
        "at 1.1420 After Hawkish Fed Surprise', vantagemarkets.com/"
        "market-analysis/eurusd-analysis-june-19-2026/)",
    ),
    ("FOMC Rate Decision", "GBPUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: the same June 17 "
        "2026 decision -- GBP/USD 'tanked by over 1%' and fell sharply to "
        "a two-month low near 1.3270 amid broad US Dollar strength "
        "following the hawkish dot plot (median 2026 fed funds projection "
        "to 3.8% from 3.4%) (FXStreet, 'British Pound craters as Warsh's "
        "guidance void fuels US Dollar rally', fxstreet.com/news/british-"
        "pound-sinks-as-warshs-hawkish-dots-power-us-dollar-202606171827)",
    ),
    ("FOMC Rate Decision", "USDJPY"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: the same June 17 "
        "2026 decision -- the Yen depreciated against the Dollar after "
        "the hawkish hold, with USD/JPY trading at 160.66 after bouncing "
        "off a daily low of 160.11 as the DXY spiked through the 100.00 "
        "handle on the release (FXStreet, 'US Dollar Index storms back as "
        "the Fed turns hawkish', fxstreet.com/news/us-dollar-index-storms"
        "-back-as-the-fed-turns-hawkish-202606171817)",
    ),
    ("FOMC Rate Decision", "USDCHF"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: the same June 17 "
        "2026 hawkish-hold decision -- the hawkish Summary of Economic "
        "Projections (median 2026 dot to 3.8% from 3.4%) 'immediately "
        "pushed US Treasury yields higher and fueled broad-based US "
        "dollar strength, while the Swiss Franc came under selling "
        "pressure' on the widening rate-differential expectation "
        "(TradingKey, 'USD/CHF (USDCHF) Volatility Intensified on Jun 17: "
        "Factors to Watch', tradingkey.com/news/market-movers/261973931-"
        "market-movers-usdchf-20260617) -- direction and driver are real "
        "and FOMC-specific, though no exact pip/percent figure was found "
        "in the sources checked, so the magnitude itself is qualitative "
        "only",
    ),
    ("FOMC Rate Decision", "AUDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: the same June 17 "
        "2026 hawkish-hold decision -- AUD/USD fell from around 0.7080 to "
        "a session low of 0.6988 (close to 80-90 pips), slicing through "
        "0.7050 and briefly breaking below 0.7000, as the hawkish dot "
        "plot (nine of 18 officials backing further 2026 hikes) drove "
        "broad US Dollar strength (Vantage Markets, 'AUD/USD Today: "
        "0.7012 as Hawkish Fed Hits Aussie Hard', vantagemarkets.com/"
        "market-analysis/audusd-analysis-19-june-2026/) -- figure checked "
        "against the article's own stated levels before use",
    ),
    ("FOMC Rate Decision", "NZDUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: NZD/USD traded "
        "sideways near 0.5830 ahead of the June 17 2026 decision, then "
        "reacted to the Fed's hawkish outlook -- the median fed funds "
        "rate projection for end-2026 rose to 3.8% from 3.4%, with "
        "officials also raising 2026 inflation forecasts to 3.6% headline "
        "/ 3.3% core, and the Kiwi's upside stayed limited on the shift "
        "(FXStreet, 'New Zealand Dollar trades sideways ahead of Fed rate "
        "decision', fxstreet.com/news/new-zealand-dollar-trades-sideways-"
        "ahead-of-fed-rate-decision-202606162132; CNBC, 'Fed interest "
        "rate decision June 2026: Fed holds rates steady', cnbc.com/2026/"
        "06/17/fed-interest-rate-decision-june-2026.html) -- direction "
        "and driver real and FOMC-specific; no exact post-decision pip "
        "figure was found in the sources checked",
    ),
    ("FOMC Rate Decision", "USDCAD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Real, dated WebSearch finding, FOMC-specific: following the same "
        "June 17 2026 hawkish-hold decision, USD/CAD climbed to a new "
        "2026 high of 1.4071, with traders repricing toward an October "
        "hike after the decision and Chair Warsh's remarks (InvestingLive, "
        "'How has the technical view changed after the FOMC rate "
        "decision?', investinglive.com/technical-analysis/what-has-the-"
        "usd-done-post-the-fomc-rate-decision-20260617/) -- a real, "
        "dated, FOMC-specific USDCAD reaction, consistent with the "
        "mechanical USD-leg baseline already used for CPI/PPI/NFP",
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
