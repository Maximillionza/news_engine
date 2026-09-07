"""
Causation-Matrix Option A — first real (not synthetic) comparison cases.

Two real historical CPI/PPI occurrences, working backwards from
2026-09-07 ("this month"): the most recent CPI/PPI releases with BOTH
(a) a real, already-recorded sentiment prediction in scoring/backtest_store.py's
predictions table (the live accumulator was running by then — its
earliest captured row is 2026-08-09), and (b) real Tier 1 causation-
matrix source data independently researched for this exact case, not
copied from Pending_Predictions_Log's own (still-TBD) live test.

Why only two, not more: going further back than Aug 2026 would mean
either fabricating a sentiment prediction (the accumulator has no real
row before Aug 9 2026) or reconstructing one from paraphrased articles
the way tests/run_historical_backtest.py does for sentiment-only cases —
neither is honest for a COMPARISON test whose whole point is putting two
independently-real predictions side by side. Two genuinely real cases
beats a longer list padded with an invented one.

Sentiment side: pulled directly from the real, already-scored
predictions table (same pattern as scoring/backtest.py's
build_real_backtest_report(), not re-run through score_bundle()).

Tier 1 side: researched via WebSearch specifically for these two dates
(NOT copied from the workbook's own Sep 2026 predict-then-check test,
which covers a different, later occurrence). See each case's
Tier1Prediction.source for citations.

predicted_direction on both Tier1Predictions is a MANUAL judgment call,
per docs/News_Engine_Causation_Matrix_v2.xlsx's POC_Sub_Event_Consolidation
sheet's working (not-yet-fully-validated) standardized-surprise
hypothesis — reasoning documented inline on each case, not hidden inside
an automated rule. See scoring/backtest.py's Tier1Prediction docstring
for why this stays manual.

Ground truth (actual_direction): real XAUUSD price reaction from the
user-supplied XAUUSD_USD_News_400Pip_Analysis_Aug2025-Sep2026.xlsx
(M1-bar-derived, 15-minute window, "Complete 15 x M1" data quality for
both cases below).
"""
import datetime as dt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from scoring.backtest import BacktestCase, BacktestReport, Tier1Prediction
from scoring.backtest_store import get_connection, get_latest_prediction_for_occurrence
from scoring.probability_engine import Direction, ProbabilityResult


def _case_from_real_prediction(
    event: EconomicEvent, instrument: str, actual_direction: Direction, actual_move_note: str,
    tier1: Tier1Prediction,
) -> BacktestCase:
    """
    Builds a BacktestCase from a REAL, already-recorded predictions-table
    row (not a fresh score_bundle() run) — same reasoning as
    scoring/backtest.py's build_real_backtest_report(): the live
    accumulator already made this call blind, before the event resolved,
    and re-scoring it now would not be a real predict-then-check test.
    """
    conn = get_connection()
    try:
        prediction = get_latest_prediction_for_occurrence(conn, event.title, instrument, event.event_time_utc)
    finally:
        conn.close()
    if prediction is None:
        raise RuntimeError(f"No real recorded prediction found for {event.title}/{instrument}@{event.event_time_utc}")

    case = BacktestCase(
        event=event, instrument=instrument,
        actual_direction=actual_direction, actual_move_note=actual_move_note,
        tier1=tier1,
    )
    case.result = ProbabilityResult(
        instrument=instrument,
        as_of_utc=dt.datetime.fromisoformat(prediction.scored_at_utc),
        aggregate_usd_sentiment=0.0, instrument_score=0.0,
        probability=prediction.probability, direction=Direction(prediction.direction),
        confidence=prediction.confidence, article_count=prediction.article_count,
        contradiction_flag=prediction.contradiction_flag, contradiction_note=None,
    )
    case.evaluate()
    return case


report = BacktestReport()

# --- Case 1: July 2026 CPI, released 2026-08-12T12:30 UTC ---
#
# Real print (BLS, per Numeric_Backfill_25_26 and the XAUUSD impact
# workbook, both agreeing): headline m/m -0.4% (forecast -0.1%, previous
# 0.5%), headline y/y 3.5% (forecast 3.8%, previous 4.2%), core m/m 0.0%
# (forecast 0.2%, previous 0.2%), core y/y 2.6% (forecast 2.8%, previous
# 2.9%) -- a broad, genuine cooling surprise on every measure.
#
# Real Tier 1 (Cleveland Fed nowcast, researched via WebSearch specifically
# for this occurrence, 2026-09-07): the nowcast's own pre-release reading
# projected a modest headline m/m DECLINE and a core y/y estimate near
# 2.85% -- i.e. the nowcast's own headline and core signals pointed in
# different strengths (headline: a real decline call, unusually strong
# directionally; core: a mild overshoot vs. the ~2.5% Dow Jones consensus
# for core y/y). Per POC_Sub_Event_Consolidation's working hypothesis
# (standardized surprise relative to a measure's own typical volatility,
# not a fixed headline/core hierarchy or a vote) -- headline's "decline"
# call is the rarer, more informative signal here (a flat-to-rising m/m
# print is the norm; an outright projected decline is not), so it is
# treated as dominant for this case's predicted_direction. This is a
# judgment call, not a validated derivation -- see Tier1Prediction's own
# field-level warning.
# Confidence: Likely, not Certain -- this is a secondary-sourced
# retrospective read of the nowcast's pre-release output (via
# intellectia.ai's coverage of the Aug 12 release), not a same-day
# primary pull the way Pending_Predictions_Log's live test case is.
e1 = EconomicEvent(
    title="CPI m/m", country="USD", impact="High",
    event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
    forecast="-0.1%", previous="0.5%", actual="-0.4%",
)
tier1_cpi = Tier1Prediction(
    value=(
        "Cleveland Fed nowcast (pre-release read): projected a modest m/m decline in "
        "headline CPI; core CPI y/y estimated near 2.85% (vs. ~2.5% Dow Jones consensus "
        "for core y/y) -- headline and core pointed in different directions/strengths"
    ),
    confidence="Likely",
    source=(
        "Cleveland Fed Inflation Nowcasting tool, via intellectia.ai's retrospective "
        "coverage of the 2026-08-12 CPI release (secondary source, not a same-day "
        "primary pull)"
    ),
    predicted_direction=Direction.BULLISH,  # headline's decline call treated as dominant, per the reasoning above
)
case1 = _case_from_real_prediction(
    event=e1, instrument="XAUUSD",
    # Real ground truth: XAUUSD_USD_News_400Pip_Analysis workbook, "All USD Events"
    # row for 2026-08-12 12:30 UTC -- Direction UP, Max Move 4494 (0.01 pips) = $44.94,
    # "Complete 15 x M1".
    actual_direction=Direction.BULLISH,
    actual_move_note="XAUUSD +$44.94 max move in 15min (UP) -- XAUUSD_USD_News_400Pip_Analysis_Aug2025-Sep2026.xlsx",
    tier1=tier1_cpi,
)
report.add(case1)

# --- Case 2: July 2026 PPI, released 2026-08-13T12:30 UTC ---
#
# Real print (BLS, both workbooks agreeing): PPI m/m 0.0% (forecast 0.2%,
# previous -0.1%), Core PPI m/m 0.2% (forecast 0.3%, previous 0.4%) -- a
# genuine miss, muted vs. forecast.
#
# Real Tier 1 (BLS's own prior release + ISM Manufacturing Prices Paid,
# researched via WebSearch specifically for this occurrence): June 2026
# PPI actual (BLS's own most recent release ahead of this one, from the
# 2026-07-15 release) was m/m -0.3%, an energy-driven decline. July 2026
# ISM Manufacturing Prices Paid registered 71.1% (released 2026-08-03,
# confirmed via prnewswire.com's ISM report + piptheory.com's coverage
# noting prices had eased from June's ~73.0 reading but stayed elevated)
# -- both real Tier 1 inputs agree on a muted, non-reaccelerating call
# for this occurrence's own print, same pattern (two agreeing Tier 1
# inputs) already established for the later, still-TBD Sep 2026 test in
# Pending_Predictions_Log.
# Confidence: Certain -- both inputs are primary-sourced (BLS's own
# release; ISM's own report, cross-confirmed by two outlets) and agree.
e2 = EconomicEvent(
    title="PPI m/m", country="USD", impact="High",
    event_time_utc=dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ),
    forecast="0.2%", previous="-0.1%", actual="0.0%",
)
tier1_ppi = Tier1Prediction(
    value=(
        "Muted, non-reaccelerating call: June 2026 PPI actual -0.3% m/m (energy-driven "
        "decline, BLS's own prior release) plus July 2026 ISM Manufacturing Prices Paid "
        "at 71.1% (eased from June's ~73.0 but still elevated, not accelerating) -- two "
        "Tier 1 inputs agreeing"
    ),
    confidence="Certain",
    source=(
        "BLS July 2026 PPI release covering June 2026 data (ppi_07152026); ISM "
        "Manufacturing Prices Paid, July 2026 reading (prnewswire.com 'Manufacturing "
        "PMI at 55.6%; July 2026 ISM Manufacturing PMI Report', released 2026-08-03; "
        "corroborated by piptheory.com's July 2026 preview coverage)"
    ),
    predicted_direction=Direction.BULLISH,  # muted/non-reaccelerating PPI reads dovish for USD -> bullish gold
)
case2 = _case_from_real_prediction(
    event=e2, instrument="XAUUSD",
    # Real ground truth: XAUUSD_USD_News_400Pip_Analysis workbook, "All USD Events"
    # row for 2026-08-13 12:30 UTC -- Direction UP, Max Move 1040 (0.01 pips) = $10.40,
    # "Complete 15 x M1".
    actual_direction=Direction.BULLISH,
    actual_move_note="XAUUSD +$10.40 max move in 15min (UP) -- XAUUSD_USD_News_400Pip_Analysis_Aug2025-Sep2026.xlsx",
    tier1=tier1_ppi,
)
report.add(case2)

report.print_report()
