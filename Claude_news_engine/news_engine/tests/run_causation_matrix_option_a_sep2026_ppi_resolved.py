"""
Causation-Matrix Option A -- the Sep 2026 PPI case, COMPLETED.

tests/run_causation_matrix_option_a_pending_sep2026.py logged
TIER1_PPI_SEP2026 (Certain, BULLISH -- "muted, non-reaccelerating" read on
July 2026 PPI actual + August 2026 ISM Prices Paid) on 2026-09-07, before
the event resolved, and explicitly deferred building a BacktestCase until
a real actual_direction was available (see that file's own TODO). The
event released 2026-09-10T12:30 UTC; this file completes the case for
both instruments now that real outcome data exists.

Sentiment side: the real, already-scored predictions table row for this
occurrence (recorded live, before the event, by the accumulator) -- same
_case_from_real_prediction() helper tests/run_causation_matrix_option_a_backtest.py
already uses, not a re-run of score_bundle().

Ground truth (actual_direction): real Dukascopy tick data, same feed
scoring/outcome_classifier.py uses for auto-confirming History-tab
outcomes. scripts/confirm_backtest_outcomes.py --auto auto-confirmed this
exact occurrence at 2026-09-10T15:00 UTC (30min window closed):
  XAUUSD: -0.54% in 30min (BEARISH)
  US30:   -0.24% in 30min (BEARISH)
Independently re-pulled tick-by-tick for this analysis (see the MAE/MFE
discussion earlier this session) -- same numbers, confirmed twice.

Result: Tier 1 called BULLISH/Certain. Real outcome was BEARISH on both
instruments. Sentiment's own live call was BEARISH on both instruments
(scored 2026-09-10T06:10 UTC, well before the release). Tier 1 was wrong
here; sentiment was right. n=1 for this specific case -- see this
session's own discussion of the market-forecast shift (consensus moved to
+0.4% m/m before the release, a real reacceleration signal Tier 1's
BLS-actual/ISM-Prices-Paid inputs don't capture) as the likely reason,
and see the tick-path survey (this session) showing the underlying
sweep-vs-continuation question is a real, unresolved, separate research
item -- this file is a directional-accuracy comparison only, not a
verdict on liquidity-sweep mechanics.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from scoring.backtest import BacktestReport
from scoring.probability_engine import Direction
from tests.run_causation_matrix_option_a_backtest import _case_from_real_prediction
from tests.run_causation_matrix_option_a_pending_sep2026 import (
    TIER1_PPI_SEP2026, PPI_EVENT_TIME_SEP2026,
)

report = BacktestReport()

event = EconomicEvent(
    title="PPI m/m", country="USD", impact="High",
    event_time_utc=PPI_EVENT_TIME_SEP2026,
    forecast="0.4%", previous="0.0%", actual="",  # actual not yet backfilled into historical_events.py
)

for instrument, move_note in (
    ("XAUUSD", "XAUUSD -0.54% in 30min (BEARISH) -- Dukascopy, auto-confirmed via "
               "scripts/confirm_backtest_outcomes.py --auto 2026-09-10T15:00 UTC, "
               "independently re-pulled tick-by-tick same session"),
    ("US30", "US30 -0.24% in 30min (BEARISH) -- Dukascopy, auto-confirmed via "
             "scripts/confirm_backtest_outcomes.py --auto 2026-09-10T15:00 UTC, "
             "independently re-pulled tick-by-tick same session"),
):
    case = _case_from_real_prediction(
        event=event, instrument=instrument,
        actual_direction=Direction.BEARISH,
        actual_move_note=move_note,
        tier1=TIER1_PPI_SEP2026,
    )
    report.add(case)

report.print_report()
