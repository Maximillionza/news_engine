"""
Causation-Matrix Option A — PENDING live predict-then-check cases for
this week's August 2026 PPI (releases 2026-09-10) and CPI (releases
2026-09-11), the real test Pending_Predictions_Log has been building
toward. Logged BEFORE the actuals are known (2026-09-07) — same
"predict, then check" discipline as that sheet, just as executable
Tier1Prediction objects instead of a spreadsheet row.

This file intentionally does NOT construct a BacktestCase for either
event yet — BacktestCase requires a real actual_direction, which doesn't
exist until each event resolves and real XAUUSD price data confirms the
reaction. Complete each case (add actual_direction + actual_move_note,
build the BacktestCase, run evaluate()) once that's available — see the
TODO at the bottom of this file, and
tests/run_causation_matrix_option_a_backtest.py for the exact pattern
the July 2026 cases already used.

Both readings pulled fresh 2026-09-07 (2 days after Pending_Predictions_Log's
own 2026-09-05 log), independently re-checked, not copied stale.
"""
from __future__ import annotations

import datetime as dt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from scoring.backtest import Tier1Prediction
from scoring.probability_engine import Direction
from scoring.backtest_store import get_connection, record_tier1_prediction

# --- PPI (August 2026 data), releases 2026-09-10T12:30 UTC ---
#
# Two Tier 1 inputs, BOTH now real, confirmed actuals (not projections):
# July 2026 PPI actual (BLS's own prior release, 2026-08-13): m/m 0.0%,
# core m/m +0.2% -- flat/muted. August 2026 ISM Manufacturing Prices
# Paid (released 2026-09-01, already a real number, not a forecast):
# 71.1%, unchanged from July's 71.1, and itself a miss vs. its own 72
# forecast (fxstreet.com, 2026-09-01) -- confirms continued elevated-
# but-NOT-accelerating input-cost pressure for a second straight month.
# Same "muted, not sharply reaccelerating" read as the July case
# (tests/run_causation_matrix_option_a_backtest.py), now with an
# additional real confirming data point -- the more confident of the
# two September calls.
TIER1_PPI_SEP2026 = Tier1Prediction(
    value=(
        "Muted, non-reaccelerating call, second consecutive confirming month: July "
        "2026 PPI actual 0.0% m/m / core +0.2% m/m (flat) plus August 2026 ISM "
        "Manufacturing Prices Paid at 71.1% (unchanged from July, missed its own 72 "
        "forecast) -- input-cost pressure remains elevated but is not accelerating"
    ),
    confidence="Certain",
    source=(
        "BLS August 2026 PPI release covering July 2026 data (ppi_08132026); ISM "
        "Manufacturing Prices Paid, August 2026 reading, released 2026-09-01 "
        "(fxstreet.com 'United States ISM Manufacturing Prices Paid registered at "
        "71.1, below expectations (72) in August'; fx.co corroborating)"
    ),
    predicted_direction=Direction.BULLISH,  # muted/non-reaccelerating PPI reads dovish for USD -> bullish gold
)
PPI_EVENT_TIME_SEP2026 = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)

# --- CPI (August 2026 data), releases 2026-09-11T12:30 UTC ---
#
# NO confident directional call -- logged honestly as such, not forced.
# Cleveland Fed nowcast, re-checked fresh 2026-09-07 (stable vs. the
# 2026-09-05 log, not drifted): headline y/y cooling to 3.38% (from
# July's confirmed 3.5%) -- a real, stable, decelerating trend, reads
# dovish/bullish-gold. But headline m/m is projected at +0.36%, a swing
# back to a real increase from July's outright -0.4% decline -- read on
# its own, that's a reacceleration, reads hawkish/bearish-gold. Two real
# signals from the SAME headline measure (m/m vs y/y framing) pointing
# opposite ways, and no forecast-distribution/consensus-clustering data
# was found to responsibly apply POC_Sub_Event_Consolidation's
# standardized-surprise heuristic the way the July retrospective case
# allowed. This is a live instance of exactly the "genuine discriminating
# case" that sheet's own Tier 2 open item says hasn't been found yet --
# logged as genuinely unresolved, per this project's own "never
# fabricate" discipline, not resolved by picking a side.
TIER1_CPI_SEP2026 = Tier1Prediction(
    value=(
        "NO CONFIDENT DIRECTIONAL CALL. Headline y/y cooling to 3.38% (from July's "
        "3.5%, stable across two independent checks 2 days apart) reads dovish/bullish-"
        "gold; headline m/m projected +0.36% (a swing back to increase from July's "
        "-0.4% decline) reads hawkish/bearish-gold on its own. No consensus-distribution "
        "data available to apply the standardized-surprise consolidation heuristic "
        "responsibly -- genuinely unresolved, not picked one way to force a call"
    ),
    confidence="Guessing",  # the raw readings are Certain/Likely; the CONSOLIDATED direction is a genuine Guess
    source=(
        "Cleveland Fed Inflation Nowcasting tool, re-checked 2026-09-07 (Motley Fool / "
        "Yahoo Finance coverage of the Fed's initial September inflation forecast, "
        "2026-09-04; cross-checked against Pending_Predictions_Log's 2026-09-05 log, "
        "headline y/y confirmed stable/unchanged)"
    ),
    predicted_direction=Direction.NEUTRAL,  # no confident call -- NEUTRAL is "no directional claim", not "muted move expected"
)
CPI_EVENT_TIME_SEP2026 = dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC_TZ)


if __name__ == "__main__":
    print("Pending Causation-Matrix Option A cases for this week (2026-09-07):\n")
    print(f"PPI (releases {PPI_EVENT_TIME_SEP2026.isoformat()}): {TIER1_PPI_SEP2026.confidence} -> "
          f"predicted {TIER1_PPI_SEP2026.predicted_direction.value.upper()} for XAUUSD")
    print(f"  {TIER1_PPI_SEP2026.value}\n")
    print(f"CPI (releases {CPI_EVENT_TIME_SEP2026.isoformat()}): {TIER1_CPI_SEP2026.confidence} -> "
          f"predicted {TIER1_CPI_SEP2026.predicted_direction.value.upper()} for XAUUSD (no real call)")
    print(f"  {TIER1_CPI_SEP2026.value}\n")
    print("TODO once real outcomes land: pull real XAUUSD price reaction (same source as "
          "the July cases -- XAUUSD_USD_News_400Pip_Analysis workbook or a fresh equivalent "
          "pull), pull the real, latest sentiment prediction for each occurrence from "
          "scoring.backtest_store, build each BacktestCase the same way "
          "tests/run_causation_matrix_option_a_backtest.py does, and run the comparison.\n")

    conn = get_connection()
    for instrument in ("XAUUSD", "US30"):
        record_tier1_prediction(
            conn, "PPI m/m", instrument, PPI_EVENT_TIME_SEP2026,
            value=TIER1_PPI_SEP2026.value, confidence=TIER1_PPI_SEP2026.confidence,
            source=TIER1_PPI_SEP2026.source,
            predicted_direction=TIER1_PPI_SEP2026.predicted_direction.value,
        )
        record_tier1_prediction(
            conn, "CPI m/m", instrument, CPI_EVENT_TIME_SEP2026,
            value=TIER1_CPI_SEP2026.value, confidence=TIER1_CPI_SEP2026.confidence,
            source=TIER1_CPI_SEP2026.source,
            predicted_direction=TIER1_CPI_SEP2026.predicted_direction.value,
        )
    conn.close()
    print("Persisted both cases to scoring/backtest_log.db's tier1_predictions table (XAUUSD + US30).")
