"""
Hand-authored, cited historical event facts for the Jan 2026 -> live-start
backfill (2026-01-01T00:00:00Z through 2026-08-09T23:49:59Z — the live
system's earliest real captured row, confirmed at 2026-08-09T23:50:00+00:00).

Every forecast/previous/actual value here is REAL, researched history —
same citation standard as tests/run_historical_backtest.py's existing 14
cases (Reuters/CNBC/Kitco/BLS/TradingKey/etc.) — never simulated or
invented. See docs/superpowers/specs/2026-08-13-historical-backfill-and-ui-redesign-design.md
for the full provenance rules: this file is ONLY event facts (forecast/
previous/actual). Article-based predictions and price outcomes are never
hand-typed here — scripts/seed_historical_data.py attempts to derive
those from genuinely real, separately-fetched data (Alpha Vantage
articles, Dukascopy prices) at seed time, and records nothing for an
occurrence where that real data isn't retrievable.

Task 4 extends this file to (near-)full Jan 1 - Aug 9 2026 coverage across
every EVENT_SURPRISE_DIRECTION title with monthly cadence, researched via
WebSearch against CNBC/Bloomberg/BLS/investing.com/tradingeconomics/ADP/
ISM/Challenger Gray & Christmas primary and wire-service sources — one
citation per entry in source_note. Two categories were deliberately
scoped down rather than force-fit with unverifiable numbers:

- Unemployment Claims (weekly, ~31 occurrences in range): SKIPPED
  entirely. A weekly-cadence claims trend streak is rarely the
  analytical focus versus the monthly prints, and 31 additional
  entries would dominate this file's volume for low marginal value —
  explicit scope-down per the Task 4 brief's own suggestion.
- Core PCE Price Index m/m: SKIPPED entirely. Financial press
  (CNBC/BEA coverage) consistently reports Core PCE's pre-release
  consensus as a year-over-year figure, not month-over-month — no
  reliably sourced m/m FORECAST could be found for any 2026 occurrence
  after a genuine search attempt, so no m/m entries are included here
  (m/m actuals were found but a forecast-less entry would misrepresent
  the surprise-classification mechanism).
- Challenger Job Cuts: SKIPPED entirely. This indicator has no
  standard published market consensus/forecast figure (Challenger,
  Gray & Christmas's report is a survey tally, not tracked against a
  Dow-Jones/Reuters poll the way NFP/CPI/PPI are) — no real forecast
  value exists to cite, so no entries are included.
- Import Prices m/m, ADP Nonfarm Employment Change, Average Hourly
  Earnings m/m, Unemployment Rate, ISM Manufacturing PMI: partial
  coverage — included only for the specific months where a full,
  independently-citable forecast/previous/actual triplet was found;
  remaining months were left out rather than guessed at.

See docs/superpowers/specs/2026-08-13-historical-backfill-and-ui-redesign-design.md
for the full provenance rules.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from config.settings import UTC_TZ


@dataclass
class HistoricalEventFact:
    title: str                    # must exactly match a config.settings.EVENT_SURPRISE_DIRECTION key
    event_time_utc: dt.datetime
    forecast: str
    previous: str
    actual: str
    source_note: str              # citation — where this forecast/previous/actual was verified


HISTORICAL_EVENTS: list[HistoricalEventFact] = [
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 7, 2, 12, 30, tzinfo=UTC_TZ),
        forecast="110K", previous="129K", actual="57K",
        source_note="June NFP, released Jul 2 2026 — actual +57K vs +110K "
                     "expected; May was revised down to +129K from the "
                     "originally-reported +172K. Verified independently via "
                     "WebSearch (investinglive.com, KuCoin, TradingView News, "
                     "FXStreet all report +57K vs +110K/May revised to "
                     "+129K); corrects tests/run_historical_backtest.py case "
                     "e2's transcription of previous (that file only cites "
                     "the actual-vs-forecast miss, not the previous figure).",
    ),
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 6, 5, 12, 30, tzinfo=UTC_TZ),
        forecast="88K", previous="179K", actual="172K",
        source_note="May NFP, released Jun 5 2026 — actual +172K vs +88K "
                     "consensus forecast (Bloomberg: '172,000... beating all "
                     "economists' estimates'), April revised up to +179K. "
                     "Verified via WebSearch (Bloomberg "
                     "bloomberg.com/news/articles/2026-06-05/us-adds-172-000-"
                     "jobs-in-may-beating-all-economists-estimates); "
                     "corresponds to tests/run_historical_backtest.py case "
                     "e3 (that file used an 85K/'80K-96K' approximation for "
                     "the forecast — this entry uses the confirmed Bloomberg "
                     "consensus figure instead).",
    ),
    # ============================================================
    # Non-Farm Employment Change -- remaining Jan-Aug 2026 occurrences
    # ============================================================
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 1, 9, 13, 30, tzinfo=UTC_TZ),
        forecast="73K", previous="56K", actual="50K",
        source_note="December 2025 NFP, released Jan 9 2026 -- actual +50K "
                     "vs Dow Jones estimate +73K, November revised down to "
                     "+56K. CNBC 'Jobs report December 2025' "
                     "(cnbc.com/2026/01/09/jobs-report-december-2025.html) "
                     "and UPI Jan 9 2026.",
    ),
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 2, 11, 13, 30, tzinfo=UTC_TZ),
        forecast="55K", previous="48K", actual="130K",
        source_note="January 2026 NFP, released Feb 11 2026 (delayed from "
                     "the usual early-Feb date by a government shutdown) -- "
                     "actual +130K vs Dow Jones estimate +55K, December "
                     "revised down to +48K from +50K. CNBC 'Jobs report "
                     "January 2026' "
                     "(cnbc.com/2026/02/11/jobs-report-january-2026-.html).",
    ),
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 3, 6, 13, 30, tzinfo=UTC_TZ),
        forecast="50K", previous="126K", actual="-92K",
        source_note="February 2026 NFP, released Mar 6 2026 -- actual -92K "
                     "vs estimate +50K, January revised up to +126K. CNBC "
                     "'February 2026 jobs report' "
                     "(cnbc.com/2026/03/06/february-2026-jobs-report.html), "
                     "corroborated by BLS empsit_03062026.htm.",
    ),
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 4, 3, 12, 30, tzinfo=UTC_TZ),
        forecast="59K", previous="-133K", actual="178K",
        source_note="March 2026 NFP, released Apr 3 2026 -- actual +178K vs "
                     "Dow Jones consensus +59K, February revised to -133K "
                     "(from originally-reported -92K). CNBC 'Jobs report "
                     "March 2026' and Bloomberg 'US Jobs Report March 2026: "
                     "178,000 Jobs Added' "
                     "(bloomberg.com/news/articles/2026-04-03/us-adds-178-"
                     "000-jobs-unemployment-rate-drops-to-4-3).",
    ),
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 5, 8, 12, 30, tzinfo=UTC_TZ),
        forecast="55K", previous="185K", actual="115K",
        source_note="April 2026 NFP, released May 8 2026 -- actual +115K "
                     "vs Dow Jones consensus +55K, March revised up to "
                     "+185K (from +178K). CNBC 'Jobs report April 2026' "
                     "(cnbc.com/2026/05/08/jobs-report-april-2026.html).",
    ),
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
        forecast="83K", previous="20K", actual="-23K",
        source_note="July 2026 NFP, released Aug 7 2026 -- actual -23K vs "
                     "Dow Jones consensus +83K (FactSet's separate estimate "
                     "was +97.5K), June revised down to +20K (from +57K). "
                     "CNBC 'The July jobs numbers are due out Friday. "
                     "Here's what to expect' (cnbc.com/2026/08/06/the-july-"
                     "jobs-numbers-are-due-out-friday-heres-what-to-expect."
                     "html) and NBC News 'July jobs report: US economy "
                     "shed 23,000 jobs' (nbcnews.com/business/economy/"
                     "july-2026-jobs-report-rcna591138).",
    ),

    # ============================================================
    # Unemployment Rate (bundled with the NFP report, same release)
    # ============================================================
    HistoricalEventFact(
        title="Unemployment Rate",
        event_time_utc=dt.datetime(2026, 2, 11, 13, 30, tzinfo=UTC_TZ),
        forecast="4.4%", previous="4.4%", actual="4.3%",
        source_note="January 2026 unemployment rate, released with the Feb "
                     "11 2026 jobs report -- actual 4.3% vs forecast to "
                     "hold at 4.4% (December's rate). CNBC 'Jobs report "
                     "January 2026'.",
    ),
    HistoricalEventFact(
        title="Unemployment Rate",
        event_time_utc=dt.datetime(2026, 4, 3, 12, 30, tzinfo=UTC_TZ),
        forecast="4.4%", previous="4.4%", actual="4.3%",
        source_note="March 2026 unemployment rate, released with the Apr 3 "
                     "2026 jobs report -- actual edged lower to 4.3% vs "
                     "forecast to hold at 4.4% (February's rate). CNBC "
                     "'The March jobs report will be released on Friday' "
                     "preview + 'Jobs report March 2026'.",
    ),
    HistoricalEventFact(
        title="Unemployment Rate",
        event_time_utc=dt.datetime(2026, 5, 8, 12, 30, tzinfo=UTC_TZ),
        forecast="4.3%", previous="4.3%", actual="4.3%",
        source_note="April 2026 unemployment rate, released with the May 8 "
                     "2026 jobs report -- held at 4.3%, in line with "
                     "March's rate and the forecast. CNBC 'Jobs report "
                     "April 2026'.",
    ),

    # ============================================================
    # Average Hourly Earnings m/m (bundled with the NFP report)
    # ============================================================
    HistoricalEventFact(
        title="Average Hourly Earnings m/m",
        event_time_utc=dt.datetime(2026, 5, 8, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.2%", actual="0.2%",
        source_note="April 2026 average hourly earnings, released with "
                     "the May 8 2026 jobs report -- actual +0.2% vs +0.3% "
                     "estimate, March's m/m gain was also +0.2%. CNBC "
                     "'Jobs report April 2026' "
                     "(cnbc.com/2026/05/08/jobs-report-april-2026.html) + "
                     "'Jobs report March 2026' for the previous figure.",
    ),

    # ============================================================
    # CPI m/m
    # ============================================================
    HistoricalEventFact(
        title="CPI m/m",
        event_time_utc=dt.datetime(2026, 1, 13, 13, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.3%", actual="0.3%",
        source_note="December 2025 CPI, released Jan 13 2026 -- headline "
                     "m/m in line at 0.3% vs 0.3% forecast. Transcribed "
                     "from tests/run_historical_backtest.py case e12's "
                     "'Consensus centers on 0.3% MoM... actual 0.3% MoM' "
                     "(sourced there via Kitco).",
    ),
    HistoricalEventFact(
        title="CPI m/m",
        event_time_utc=dt.datetime(2026, 2, 13, 13, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.3%", actual="0.2%",
        source_note="January 2026 CPI, released Feb 13 2026 -- headline "
                     "m/m 0.2% vs 0.3% forecast (core matched forecast at "
                     "0.3%). CNBC 'CPI inflation report January 2026' "
                     "(cnbc.com/2026/02/13/cpi-inflation-report-"
                     "january-2026.html).",
    ),
    HistoricalEventFact(
        title="CPI m/m",
        event_time_utc=dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.2%", actual="0.3%",
        source_note="February 2026 CPI, released Mar 11 2026 -- headline "
                     "m/m 0.3%, in line with Wall Street estimates. CNBC "
                     "'CPI inflation report February 2026: CPI rose 2.4% "
                     "annually in February, as expected' "
                     "(cnbc.com/2026/03/11/cpi-inflation-report-"
                     "february-2026.html) and Bloomberg's companion "
                     "'Key Takeaways' piece.",
    ),
    HistoricalEventFact(
        title="CPI m/m",
        event_time_utc=dt.datetime(2026, 4, 10, 12, 30, tzinfo=UTC_TZ),
        forecast="1.0%", previous="0.3%", actual="0.9%",
        source_note="March 2026 CPI, released Apr 10 2026 -- actual 0.9% "
                     "MoM vs 1.0% expected (Iran-war energy-driven spike, "
                     "softer than feared). Transcribed from "
                     "tests/run_historical_backtest.py case e8.",
    ),
    HistoricalEventFact(
        title="CPI m/m",
        event_time_utc=dt.datetime(2026, 5, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.6%", previous="0.9%", actual="0.6%",
        source_note="April 2026 CPI, released May 12 2026 -- headline m/m "
                     "matched the 0.6% forecast (annual rate ran 0.1pp "
                     "hot at 3.8% vs 3.7%). CNBC 'CPI inflation April "
                     "2026: Prices rose 3.8% annually' "
                     "(cnbc.com/2026/05/12/cpi-inflation-april-2026-.html).",
    ),
    HistoricalEventFact(
        title="CPI m/m",
        event_time_utc=dt.datetime(2026, 6, 10, 12, 30, tzinfo=UTC_TZ),
        forecast="0.5%", previous="0.6%", actual="0.5%",
        source_note="May 2026 CPI, released Jun 10 2026 -- headline m/m "
                     "in line at 0.5% (annual rate 4.2%, hottest since "
                     "April 2023). CNBC 'CPI inflation report May 2026: "
                     "Prices rose 4.2% annually' "
                     "(cnbc.com/2026/06/10/cpi-inflation-report-"
                     "may-2026.html).",
    ),
    HistoricalEventFact(
        title="CPI m/m",
        event_time_utc=dt.datetime(2026, 7, 14, 12, 30, tzinfo=UTC_TZ),
        forecast="-0.2%", previous="0.5%", actual="-0.4%",
        source_note="June 2026 CPI, released Jul 14 2026 -- CPI fell "
                     "-0.4% vs Dow Jones estimate for a -0.2% drop, "
                     "biggest monthly decline since April 2020 (energy "
                     "price drop). CNBC 'Consumer price index inflation "
                     "report June 2026' (cnbc.com/2026/07/14/consumer-"
                     "price-index-inflation-report-june-2026.html) -- "
                     "supersedes tests/run_historical_backtest.py case "
                     "e4's vaguer '-0.1% expected' approximation with the "
                     "confirmed Dow Jones consensus figure.",
    ),

    # ============================================================
    # CPI y/y
    # ============================================================
    HistoricalEventFact(
        title="CPI y/y",
        event_time_utc=dt.datetime(2026, 1, 13, 13, 30, tzinfo=UTC_TZ),
        forecast="2.7%", previous="2.7%", actual="2.7%",
        source_note="December 2025 CPI y/y, released Jan 13 2026 -- in "
                     "line at 2.7%. Transcribed from "
                     "tests/run_historical_backtest.py case e12.",
    ),
    HistoricalEventFact(
        title="CPI y/y",
        event_time_utc=dt.datetime(2026, 2, 13, 13, 30, tzinfo=UTC_TZ),
        forecast="2.5%", previous="2.7%", actual="2.4%",
        source_note="January 2026 CPI y/y, released Feb 13 2026 -- actual "
                     "2.4% vs Dow Jones consensus 2.5%. CNBC 'Consumer "
                     "prices rose 2.4% annually in January, less than "
                     "expected' (cnbc.com/2026/02/13/cpi-inflation-"
                     "report-january-2026.html).",
    ),
    HistoricalEventFact(
        title="CPI y/y",
        event_time_utc=dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC_TZ),
        forecast="2.5%", previous="2.4%", actual="2.4%",
        source_note="February 2026 CPI y/y, released Mar 11 2026 -- "
                     "actual 2.4% (unchanged from January) vs 2.5% median "
                     "estimate. CNBC 'CPI inflation report February "
                     "2026' (cnbc.com/2026/03/11/cpi-inflation-report-"
                     "february-2026.html).",
    ),
    HistoricalEventFact(
        title="CPI y/y",
        event_time_utc=dt.datetime(2026, 4, 10, 12, 30, tzinfo=UTC_TZ),
        forecast="3.4%", previous="2.4%", actual="3.3%",
        source_note="March 2026 CPI y/y, released Apr 10 2026 -- actual "
                     "3.3% vs 3.4% expected. Transcribed from "
                     "tests/run_historical_backtest.py case e8.",
    ),
    HistoricalEventFact(
        title="CPI y/y",
        event_time_utc=dt.datetime(2026, 5, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="3.7%", previous="3.3%", actual="3.8%",
        source_note="April 2026 CPI y/y, released May 12 2026 -- actual "
                     "3.8% vs 3.7% expected (0.1pp hot). CNBC 'CPI "
                     "inflation April 2026: Prices rose 3.8% annually' -- "
                     "corroborated by tests/run_historical_backtest.py "
                     "case e9's independently-sourced '3.8% YoY vs 3.7% "
                     "expected'.",
    ),
    HistoricalEventFact(
        title="CPI y/y",
        event_time_utc=dt.datetime(2026, 6, 10, 12, 30, tzinfo=UTC_TZ),
        forecast="4.2%", previous="3.8%", actual="4.2%",
        source_note="May 2026 CPI y/y, released Jun 10 2026 -- in line at "
                     "4.2%, hottest since April 2023. Transcribed from "
                     "tests/run_historical_backtest.py case e5, "
                     "corroborated by CNBC 'CPI inflation report May "
                     "2026'.",
    ),
    HistoricalEventFact(
        title="CPI y/y",
        event_time_utc=dt.datetime(2026, 7, 14, 12, 30, tzinfo=UTC_TZ),
        forecast="3.8%", previous="4.2%", actual="3.5%",
        source_note="June 2026 CPI y/y, released Jul 14 2026 -- actual "
                     "3.5% vs Dow Jones estimate 3.8%, following the "
                     "4.2% May reading. CNBC 'Consumer price index "
                     "inflation report June 2026' "
                     "(cnbc.com/2026/07/14/consumer-price-index-"
                     "inflation-report-june-2026.html).",
    ),

    # ============================================================
    # Core CPI m/m
    # ============================================================
    HistoricalEventFact(
        title="Core CPI m/m",
        event_time_utc=dt.datetime(2026, 2, 13, 13, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.3%", actual="0.3%",
        source_note="January 2026 core CPI m/m, released Feb 13 2026 -- "
                     "in line at 0.3%. CNBC 'CPI inflation report January "
                     "2026'.",
    ),
    HistoricalEventFact(
        title="Core CPI m/m",
        event_time_utc=dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC_TZ),
        forecast="0.2%", previous="0.3%", actual="0.2%",
        source_note="February 2026 core CPI m/m, released Mar 11 2026 -- "
                     "in line at 0.2%. CNBC 'CPI inflation report "
                     "February 2026' + Bloomberg 'US CPI Report February "
                     "2026: Key Takeaways'.",
    ),
    HistoricalEventFact(
        title="Core CPI m/m",
        event_time_utc=dt.datetime(2026, 6, 10, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.2%", actual="0.2%",
        source_note="May 2026 core CPI m/m, released Jun 10 2026 -- "
                     "actual 0.2% vs 0.3% estimate (annual rate 2.9% was "
                     "in line). CNBC 'CPI inflation report May 2026'.",
    ),
    HistoricalEventFact(
        title="Core CPI m/m",
        event_time_utc=dt.datetime(2026, 7, 14, 12, 30, tzinfo=UTC_TZ),
        forecast="0.2%", previous="0.2%", actual="0.0%",
        source_note="June 2026 core CPI m/m, released Jul 14 2026 -- flat "
                     "(0.0%) vs 0.2% consensus. CNBC 'Consumer price "
                     "index inflation report June 2026'.",
    ),

    # ============================================================
    # Core CPI y/y
    # ============================================================
    HistoricalEventFact(
        title="Core CPI y/y",
        event_time_utc=dt.datetime(2026, 1, 13, 13, 30, tzinfo=UTC_TZ),
        forecast="2.7%", previous="2.7%", actual="2.6%",
        source_note="December 2025 core CPI y/y, released Jan 13 2026 -- "
                     "actual 2.6%, slightly softer than the 2.7% "
                     "consensus. Transcribed from "
                     "tests/run_historical_backtest.py case e12.",
    ),
    HistoricalEventFact(
        title="Core CPI y/y",
        event_time_utc=dt.datetime(2026, 2, 13, 13, 30, tzinfo=UTC_TZ),
        forecast="2.5%", previous="2.6%", actual="2.5%",
        source_note="January 2026 core CPI y/y, released Feb 13 2026 -- "
                     "in line at 2.5% (lowest since April 2021). CNBC "
                     "'CPI inflation report January 2026'.",
    ),
    HistoricalEventFact(
        title="Core CPI y/y",
        event_time_utc=dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC_TZ),
        forecast="2.5%", previous="2.5%", actual="2.5%",
        source_note="February 2026 core CPI y/y, released Mar 11 2026 -- "
                     "in line at 2.5%. CNBC 'CPI inflation report "
                     "February 2026'.",
    ),
    HistoricalEventFact(
        title="Core CPI y/y",
        event_time_utc=dt.datetime(2026, 6, 10, 12, 30, tzinfo=UTC_TZ),
        forecast="2.9%", previous="2.8%", actual="2.9%",
        source_note="May 2026 core CPI y/y, released Jun 10 2026 -- in "
                     "line at 2.9%. CNBC 'CPI inflation report May "
                     "2026'.",
    ),
    HistoricalEventFact(
        title="Core CPI y/y",
        event_time_utc=dt.datetime(2026, 7, 14, 12, 30, tzinfo=UTC_TZ),
        forecast="2.9%", previous="2.9%", actual="2.6%",
        source_note="June 2026 core CPI y/y, released Jul 14 2026 -- "
                     "actual 2.6% vs 2.9% consensus, following a 2.9% May "
                     "level. CNBC 'Consumer price index inflation report "
                     "June 2026'.",
    ),

    # ============================================================
    # PPI m/m
    # ============================================================
    HistoricalEventFact(
        title="PPI m/m",
        event_time_utc=dt.datetime(2026, 1, 30, 13, 30, tzinfo=UTC_TZ),
        forecast="0.2%", previous="0.2%", actual="0.5%",
        source_note="December 2025 PPI m/m, released Jan 30 2026 -- "
                     "actual 0.5% vs 0.2% expected, November was 0.2%. "
                     "Transcribed from tests/run_historical_backtest.py "
                     "case e13, previous figure independently confirmed "
                     "via WebSearch (BLS ppi_01302026.htm summary: "
                     "'producer prices rose 0.2% month-over-month in "
                     "November 2025').",
    ),
    HistoricalEventFact(
        title="PPI m/m",
        event_time_utc=dt.datetime(2026, 2, 27, 13, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.5%", actual="0.5%",
        source_note="January 2026 PPI m/m, released Feb 27 2026 -- actual "
                     "0.5% vs 0.3% forecast. CNBC 'Core wholesale prices "
                     "rose 0.8% in January, much more than expected' "
                     "(cnbc.com/2026/02/27/ppi-january-2026-.html).",
    ),
    HistoricalEventFact(
        title="PPI m/m",
        event_time_utc=dt.datetime(2026, 3, 18, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.5%", actual="0.7%",
        source_note="February 2026 PPI m/m, released Mar 18 2026 -- "
                     "actual 0.7% vs 0.3% forecast, above January's 0.5%. "
                     "Confirms and supersedes "
                     "tests/run_historical_backtest.py case e10's '3.4% "
                     "vs ~1.7% expected' entry, which does not match any "
                     "real BLS/press m/m or y/y figure found for this "
                     "release and was not transcribed here; this entry "
                     "uses the freshly WebSearch-confirmed CNBC/BLS "
                     "figures instead (BLS ppi_03182026.htm; "
                     "TradingEconomics 'US PPI Seen Slowing' preview).",
    ),
    HistoricalEventFact(
        title="PPI m/m",
        event_time_utc=dt.datetime(2026, 5, 13, 12, 30, tzinfo=UTC_TZ),
        forecast="0.5%", previous="0.7%", actual="1.4%",
        source_note="April 2026 PPI m/m, released May 13 2026 -- actual "
                     "1.4% vs 0.5% Dow Jones consensus (largest monthly "
                     "gain since March 2022), March upwardly revised to "
                     "0.7%. CNBC 'PPI inflation report April 2026' "
                     "(cnbc.com/2026/05/13/ppi-inflation-report-"
                     "april-2026-.html).",
    ),
    HistoricalEventFact(
        title="PPI m/m",
        event_time_utc=dt.datetime(2026, 6, 11, 12, 30, tzinfo=UTC_TZ),
        forecast="0.7%", previous="1.4%", actual="1.1%",
        source_note="May 2026 PPI m/m, released Jun 11 2026 -- actual "
                     "1.1% vs 0.7% Dow Jones consensus (12-month rate "
                     "6.5%). CNBC 'Producer price index May 2026' "
                     "(cnbc.com/2026/06/11/producer-price-index-"
                     "may-2026-.html).",
    ),
    HistoricalEventFact(
        title="PPI m/m",
        event_time_utc=dt.datetime(2026, 7, 15, 12, 30, tzinfo=UTC_TZ),
        forecast="-0.3%", previous="1.1%", actual="-0.3%",
        source_note="June 2026 PPI m/m, released Jul 15 2026 -- in line "
                     "at -0.3% (gasoline-price-driven decline). CNBC "
                     "'Wholesale prices unexpectedly declined 0.3% in "
                     "June on big drop in gasoline' "
                     "(cnbc.com/2026/07/15/wholesale-inflation-"
                     "june-2026-.html).",
    ),

    # ============================================================
    # Core PPI m/m
    # ============================================================
    HistoricalEventFact(
        title="Core PPI m/m",
        event_time_utc=dt.datetime(2026, 1, 30, 13, 30, tzinfo=UTC_TZ),
        forecast="0.2%", previous="0.2%", actual="0.7%",
        source_note="December 2025 core PPI m/m, released Jan 30 2026 -- "
                     "actual 0.7% vs 0.2% expected, November was 0.2%. "
                     "Transcribed from tests/run_historical_backtest.py "
                     "case e13, previous figure via WebSearch (BLS "
                     "ppi_01302026.htm summary: 'Core PPI increased by "
                     "0.2% in November').",
    ),
    HistoricalEventFact(
        title="Core PPI m/m",
        event_time_utc=dt.datetime(2026, 2, 27, 13, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.6%", actual="0.8%",
        source_note="January 2026 core PPI m/m, released Feb 27 2026 -- "
                     "actual 0.8% vs 0.3% Dow Jones consensus, December "
                     "revised to +0.6% (from the originally-reported "
                     "+0.7%). CNBC 'Core wholesale prices rose 0.8% in "
                     "January, much more than expected' "
                     "(cnbc.com/2026/02/27/ppi-january-2026-.html).",
    ),
    HistoricalEventFact(
        title="Core PPI m/m",
        event_time_utc=dt.datetime(2026, 3, 18, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="0.8%", actual="0.5%",
        source_note="February 2026 core PPI m/m, released Mar 18 2026 -- "
                     "actual 0.5% vs 0.3% forecast, slowing from "
                     "January's 0.8%. WebSearch-confirmed via BLS "
                     "ppi_03182026.htm and TradingEconomics coverage.",
    ),

    # ============================================================
    # ISM Manufacturing PMI
    # ============================================================
    HistoricalEventFact(
        title="ISM Manufacturing PMI",
        event_time_utc=dt.datetime(2026, 3, 2, 15, 0, tzinfo=UTC_TZ),
        forecast="51.8", previous="52.6", actual="52.4",
        source_note="February 2026 ISM Manufacturing PMI, released Mar 2 "
                     "2026 10:00am ET -- actual 52.4 vs 51.8 expected, "
                     "slipped from January's 52.6 but stayed above "
                     "consensus. ISM/prnewswire 'Manufacturing PMI at "
                     "52.4%; February 2026 ISM Manufacturing PMI Report'.",
    ),
    HistoricalEventFact(
        title="ISM Manufacturing PMI",
        event_time_utc=dt.datetime(2026, 8, 3, 14, 0, tzinfo=UTC_TZ),
        forecast="54.0", previous="53.3", actual="55.6",
        source_note="July 2026 ISM Manufacturing PMI, released Aug 3 2026 "
                     "10:00am ET -- actual 55.6 vs 54.0 expected "
                     "(strongest reading since May 2022), up from June's "
                     "53.3. FXStreet 'Breaking: US ISM Manufacturing PMI "
                     "rises to 55.6 in July vs. 54 expected' + prnewswire "
                     "'Manufacturing PMI at 55.6%; July 2026 ISM "
                     "Manufacturing PMI Report'.",
    ),

    # ============================================================
    # Retail Sales m/m
    # ============================================================
    HistoricalEventFact(
        title="Retail Sales m/m",
        event_time_utc=dt.datetime(2026, 3, 6, 13, 30, tzinfo=UTC_TZ),
        forecast="-0.3%", previous="0.0%", actual="-0.2%",
        source_note="January 2026 retail sales, released Mar 6 2026 "
                     "(delayed from the usual mid-Feb date). Census "
                     "Bureau Advance Monthly Retail Trade Survey, "
                     "adv2601.pdf (www2.census.gov/retail/releases/"
                     "historical/marts/adv2601.pdf); forecast/previous "
                     "cross-checked via investing.com's US retail sales "
                     "m/m historical calendar table.",
    ),
    HistoricalEventFact(
        title="Retail Sales m/m",
        event_time_utc=dt.datetime(2026, 4, 1, 12, 30, tzinfo=UTC_TZ),
        forecast="0.5%", previous="-0.1%", actual="0.6%",
        source_note="February 2026 retail sales, released Apr 1 2026 -- "
                     "actual 0.6% vs 0.5% forecast, rebounding from a "
                     "0.1% January drop. WebSearch-confirmed: 'retail "
                     "sales in the US jumped 0.6% month-over-month in "
                     "February 2026, rebounding from a 0.1% drop in "
                     "January and above forecasts of a 0.5% gain' "
                     "(Census Bureau data via multiple outlets).",
    ),
    HistoricalEventFact(
        title="Retail Sales m/m",
        event_time_utc=dt.datetime(2026, 4, 21, 12, 30, tzinfo=UTC_TZ),
        forecast="1.4%", previous="0.7%", actual="1.7%",
        source_note="March 2026 retail sales, released Apr 21 2026 -- "
                     "actual 1.7% vs 1.4% forecast, previous 0.7%. "
                     "investing.com US retail sales m/m historical "
                     "calendar table, cross-validated against the "
                     "independently confirmed adjacent Feb/May/Jun rows.",
    ),
    HistoricalEventFact(
        title="Retail Sales m/m",
        event_time_utc=dt.datetime(2026, 5, 14, 12, 30, tzinfo=UTC_TZ),
        forecast="0.5%", previous="1.6%", actual="0.5%",
        source_note="April 2026 retail sales, released May 14 2026 -- in "
                     "line at 0.5% (later revised down to 0.4%, per the "
                     "May 2026 report's own reference to 'a downwardly "
                     "revised 0.4% rise in April'). investing.com US "
                     "retail sales m/m historical calendar table.",
    ),
    HistoricalEventFact(
        title="Retail Sales m/m",
        event_time_utc=dt.datetime(2026, 6, 17, 12, 30, tzinfo=UTC_TZ),
        forecast="0.5%", previous="0.4%", actual="0.9%",
        source_note="May 2026 retail sales, released Jun 17 2026 -- "
                     "actual +0.9% vs +0.5% expected, previous month "
                     "revised down to +0.4%. investinglive.com 'US May "
                     "advance retail sales +0.9% vs +0.5% expected' "
                     "(investinglive.com/news/us-may-advance-retail-"
                     "sales-09-vs-05-expected-20260617/).",
    ),
    HistoricalEventFact(
        title="Retail Sales m/m",
        event_time_utc=dt.datetime(2026, 7, 16, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", previous="1.0%", actual="0.2%",
        source_note="June 2026 retail sales, released Jul 16 2026 -- "
                     "actual +0.2% vs +0.3% FactSet consensus, down from "
                     "May's revised +1.0%. CNN Business 'Retail sales "
                     "last month rose less than expected' "
                     "(cnn.com/2026/07/16/economy/us-retail-sales-june).",
    ),

    # ============================================================
    # ADP Nonfarm Employment Change
    # ============================================================
    HistoricalEventFact(
        title="ADP Nonfarm Employment Change",
        event_time_utc=dt.datetime(2026, 6, 3, 12, 15, tzinfo=UTC_TZ),
        forecast="110K", previous="105K", actual="122K",
        source_note="May 2026 ADP private payrolls, released Jun 3 2026 "
                     "-- actual +122K vs Dow Jones consensus +110K, "
                     "April was +105K. CNBC 'ADP jobs report May 2026: "
                     "Payrolls increase by 122000' "
                     "(cnbc.com/2026/06/03/adp-jobs-report-may-2026-"
                     "payrolls-increase-by-122000.html).",
    ),
    HistoricalEventFact(
        title="ADP Nonfarm Employment Change",
        event_time_utc=dt.datetime(2026, 7, 1, 12, 15, tzinfo=UTC_TZ),
        forecast="110K", previous="122K", actual="98K",
        source_note="June 2026 ADP private payrolls, released Jul 1 2026 "
                     "-- actual +98K vs +110K forecast, down from May's "
                     "+122K. CNBC 'Private payrolls rose by 98,000 in "
                     "June, less than expected, ADP reports' "
                     "(cnbc.com/2026/07/01/private-payrolls-rose-"
                     "by-98000-in-june-less-than-expected-adp-reports.html).",
    ),
    HistoricalEventFact(
        title="ADP Nonfarm Employment Change",
        event_time_utc=dt.datetime(2026, 8, 5, 12, 15, tzinfo=UTC_TZ),
        forecast="70K", previous="98K", actual="44K",
        source_note="July 2026 ADP private payrolls, released Aug 5 2026 "
                     "-- actual +44K vs Wall Street forecast +70K, down "
                     "from June's +98K. Fox Business 'ADP report July "
                     "2026: Private sector adds 44,000 jobs' "
                     "(foxbusiness.com/economy/private-sector-added-"
                     "44000-jobs-july-below-expectations-adp-says).",
    ),

    # ============================================================
    # Import Prices m/m
    # ============================================================
    HistoricalEventFact(
        title="Import Prices m/m",
        event_time_utc=dt.datetime(2026, 7, 17, 12, 30, tzinfo=UTC_TZ),
        forecast="-0.8%", previous="1.7%", actual="0.3%",
        source_note="June 2026 import prices, released Jul 17 2026 -- "
                     "actual +0.3% (a surprise gain) vs Dow Jones "
                     "estimate for a -0.8% decline, following a +1.7% "
                     "May increase. CNBC 'Import prices post surprise "
                     "gain as costs of goods from China hit highest "
                     "since 2008' (cnbc.com/2026/07/17/import-prices-"
                     "post-surprise-gain-as-costs-of-goods-from-china-"
                     "hit-highest-since-2008.html).",
    ),
]
