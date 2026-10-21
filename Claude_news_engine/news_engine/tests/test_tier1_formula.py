"""
Tests for webapp/tier1_formula.py (B3 T5): the deterministic CPI-family Tier 1 call from the Cleveland Fed
nowcast vs the forecast. No network; the backtest DB is in-memory.
"""
import datetime as dt

import pytest

from data_layer.tier1_events import TIER1_FORMULA_CONFIDENCE, TIER1_FORMULA_SOURCE
from scoring import backtest_store as bs
from webapp import tier1_formula as tf

UTC = dt.timezone.utc
RELEASE = dt.datetime(2026, 11, 12, 13, 30, tzinfo=UTC)
NOW = dt.datetime(2026, 11, 11, 5, 0, tzinfo=UTC)
VALUE_DATE = dt.date(2026, 11, 10)
FOUR = ["XAUUSD", "US30", "EURUSD", "USDJPY"]


def _rows(bt) -> list:
    return bt.execute("SELECT * FROM tier1_predictions ORDER BY id").fetchall()


# --- pure rules ----------------------------------------------------------------------------------

def test_surprise_side_uses_one_rounding_step_of_the_forecast():
    assert tf.surprise_side(0.47, "0.3%") == 1
    assert tf.surprise_side(0.359, "0.4%") == 0
    assert tf.surprise_side(0.26, "0.3%") == 0
    assert tf.surprise_side(0.15, "0.3%") == -1
    assert tf.surprise_side(0.4, None) is None
    assert tf.surprise_side(0.4, "n/a") is None


def test_formula_direction_per_instrument():
    # Hotter CPI = USD bullish: gold (inverse) and US30 (risk sentiment) fall, EURUSD falls, USDJPY rises.
    hot = {s: tf.formula_direction("CPI m/m", 1, s) for s in FOUR}
    assert hot == {"XAUUSD": "bearish", "US30": "bearish", "EURUSD": "bearish", "USDJPY": "bullish"}
    cool = {s: tf.formula_direction("CPI m/m", -1, s) for s in FOUR}
    assert cool == {"XAUUSD": "bullish", "US30": "bullish", "EURUSD": "bullish", "USDJPY": "bearish"}


def test_formula_in_line_is_neutral_for_every_instrument():
    for title in ("CPI m/m", "Core CPI m/m"):
        assert {tf.formula_direction(title, 0, s) for s in FOUR} == {"neutral"}


def test_value_text_round_trips_the_nowcast_and_shows_sast():
    text = tf.formula_value_text(0.5307, "0.3%", 1, VALUE_DATE, dt.datetime(2026, 11, 11, 5, 0, tzinfo=UTC))
    assert "0.5307%" in text and "hotter than forecast" in text and "2026-11-11 07:00 SAST" in text
    assert "Fed value dated 2026-11-10" in text
    assert tf.nowcast_in_value_text(text) == 0.5307
    assert tf.nowcast_in_value_text("Consensus 0.3%; BLS/ISM context points hotter") is None


# --- record_formula_calls ------------------------------------------------------------------------

def test_formula_rows_are_written_once_per_distinct_nowcast():
    bt = bs.get_connection(":memory:")
    # A pre-B3 judgment row for the same occurrence must not count as the formula row.
    bs.record_tier1_prediction(bt, "CPI m/m", "US30", RELEASE, "LLM research", "Guessing", "BLS/ISM", "bullish",
                               logged_at_utc=NOW - dt.timedelta(days=2))
    first = tf.record_formula_calls(bt, "CPI m/m", RELEASE, 0.5307, "0.3%", VALUE_DATE, ["US30", "XAUUSD"], NOW)
    assert first == {"written": [("US30", "bearish"), ("XAUUSD", "bearish")], "unchanged": [], "pending": None}
    assert len(_rows(bt)) == 3

    again = tf.record_formula_calls(bt, "CPI m/m", RELEASE, 0.5307, "0.3%", VALUE_DATE, ["US30", "XAUUSD"],
                                    NOW + dt.timedelta(hours=1))
    assert again == {"written": [], "unchanged": ["US30", "XAUUSD"], "pending": None}
    assert len(_rows(bt)) == 3

    moved = tf.record_formula_calls(bt, "CPI m/m", RELEASE, 0.5310, "0.3%", VALUE_DATE, ["US30", "XAUUSD"],
                                    NOW + dt.timedelta(hours=2))
    assert [s for s, _ in moved["written"]] == ["US30", "XAUUSD"] and moved["unchanged"] == []
    assert len(_rows(bt)) == 5
    latest = bs.get_latest_tier1_prediction_for_occurrence(bt, "CPI m/m", "US30", RELEASE)
    assert tf.nowcast_in_value_text(latest.value) == 0.5310


def test_record_formula_calls_without_a_forecast_writes_nothing():
    bt = bs.get_connection(":memory:")
    for forecast in (None, "", "n/a"):
        got = tf.record_formula_calls(bt, "CPI m/m", RELEASE, 0.47, forecast, VALUE_DATE, ["XAUUSD"], NOW)
        assert got == {"written": [], "unchanged": [], "pending": "no readable forecast yet"}
    assert _rows(bt) == []


def test_formula_rows_use_likely_and_the_formula_source():
    bt = bs.get_connection(":memory:")
    tf.record_formula_calls(bt, "Core CPI m/m", RELEASE, 0.26, "0.3%", VALUE_DATE, ["XAUUSD"], NOW)
    (row,) = _rows(bt)
    assert row["confidence"] == TIER1_FORMULA_CONFIDENCE == "Likely"
    assert row["source"] == TIER1_FORMULA_SOURCE == "Cleveland Fed nowcast (formula)"
    assert row["predicted_direction"] == "neutral" and "in line with forecast" in row["value"]
    assert dt.datetime.fromisoformat(row["logged_at_utc"]) == NOW
    assert dt.datetime.fromisoformat(row["event_time_utc"]) == RELEASE


def test_dry_run_reports_every_symbol_and_touches_nothing():
    got = tf.record_formula_calls(None, "CPI m/m", RELEASE, 0.47, "0.3%", VALUE_DATE, ["US30", "USDJPY"], NOW,
                                  dry_run=True)
    assert got == {"written": [("US30", "bearish"), ("USDJPY", "bullish")], "unchanged": [], "pending": None}


def test_record_formula_calls_refuses_a_naive_or_post_release_now():
    bt = bs.get_connection(":memory:")
    with pytest.raises(ValueError):
        tf.record_formula_calls(bt, "CPI m/m", RELEASE, 0.47, "0.3%", VALUE_DATE, ["XAUUSD"], NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        tf.record_formula_calls(bt, "CPI m/m", RELEASE, 0.47, "0.3%", VALUE_DATE, ["XAUUSD"],
                                RELEASE + dt.timedelta(minutes=1))
    assert _rows(bt) == []
