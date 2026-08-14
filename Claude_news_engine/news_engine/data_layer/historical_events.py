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

Full Jan 1 - Aug 9 2026 coverage is Task 4. This file ships with two real,
independently-verified seed facts (proof the mechanism works end-to-end).
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
]
