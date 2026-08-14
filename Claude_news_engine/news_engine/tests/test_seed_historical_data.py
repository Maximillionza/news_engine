"""
Tests for scripts/seed_historical_data.py — no live network calls.
AlphaVantageNewsSource and outcome_classifier.classify are both mocked;
this proves the SEEDING MECHANISM (real functions called with real
data-shaped inputs, source='seeded' threaded through, absent-not-
fabricated on empty results) without depending on live API availability.
"""
import sys
import os
import datetime as dt
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
import webapp.store as dash_store
import scoring.backtest_store as bt_store
from data_layer.historical_events import HistoricalEventFact
from data_layer.news_feed import NewsArticle
import scripts.seed_historical_data as seed


def _fact(title="CPI m/m", event_time_utc=None, actual="0.3%", forecast="0.2%", previous="0.1%"):
    return HistoricalEventFact(
        title=title,
        event_time_utc=event_time_utc or dt.datetime(2026, 1, 13, 12, 30, tzinfo=UTC_TZ),
        forecast=forecast, previous=previous, actual=actual,
        source_note="test fixture",
    )


def test_no_placeholder_facts_in_the_shipped_dataset():
    print("=== seed_historical_data: HISTORICAL_EVENTS ships with zero TBD_RESEARCH placeholders ===")
    from data_layer.historical_events import HISTORICAL_EVENTS
    placeholders = [f for f in HISTORICAL_EVENTS if "TBD_RESEARCH" in (f.forecast, f.previous, f.actual)]
    assert placeholders == [], f"Found {len(placeholders)} unresearched placeholder fact(s) — replace before shipping: {placeholders}"
    print("PASS\n")


def test_calendar_side_write_always_happens():
    print("=== seed_historical_data: the calendar-side event_history write always happens, regardless of article/outcome availability ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()

        with patch.object(seed, "_attempt_article_prediction", return_value=None), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        rows = dash_store.get_event_history(dash_conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].source == "seeded"
        assert rows[0].actual == "0.3%"
        assert report.calendar_writes == 1
        assert report.predictions_written == 0
        assert report.outcomes_written == 0
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_real_article_result_produces_a_real_scored_prediction():
    print("=== seed_historical_data: a genuine (mocked-but-real-shaped) article result runs through the actual score_bundle() and writes a prediction ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        real_article = NewsArticle(
            title="CPI comes in hot, dollar surges", summary="Inflation beats forecast, hawkish Fed bets rise",
            source="Test Wire", source_type="rss_reuters_business",
            published_utc=fact.event_time_utc - dt.timedelta(hours=2),
            url="https://example.test/real-article",
        )

        with patch.object(seed, "_fetch_real_articles", return_value=[real_article]), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        preds = bt_conn.execute("SELECT * FROM predictions WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(preds) == 1
        assert preds[0]["source"] == "seeded"
        assert preds[0]["article_count"] == 1  # the real article, not fabricated
        assert report.predictions_written == 1
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_empty_article_result_writes_nothing_not_a_fallback():
    print("=== seed_historical_data: no real articles found -> zero predictions rows, no reconstruction fallback ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()

        with patch.object(seed, "_fetch_real_articles", return_value=[]), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        preds = bt_conn.execute("SELECT * FROM predictions WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(preds) == 0
        assert report.predictions_written == 0
        assert report.predictions_skipped == 1
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_real_outcome_classification_writes_outcome():
    print("=== seed_historical_data: a clear (mocked-but-real-shaped) Dukascopy classification writes a real outcome ===")
    from scoring.outcome_classifier import ClassificationResult
    from scoring.probability_engine import Direction
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        clear_result = ClassificationResult(direction=Direction.BULLISH, move_pct=0.35, note="Dukascopy: +0.35% in 30min (auto)")

        with patch.object(seed, "_fetch_real_articles", return_value=[]), \
             patch.object(seed, "_classify_outcome", return_value=clear_result):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        outcomes = bt_conn.execute("SELECT * FROM outcomes WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(outcomes) == 1
        assert outcomes[0]["source"] == "seeded"
        assert outcomes[0]["actual_direction"] == "bullish"
        assert report.outcomes_written == 1
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_ambiguous_outcome_writes_nothing():
    print("=== seed_historical_data: an ambiguous (mocked) Dukascopy classification writes no outcome row ===")
    from scoring.outcome_classifier import ClassificationResult
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        ambiguous_result = ClassificationResult(direction=None, move_pct=0.05, note="Dukascopy: +0.05% in 30min, below 0.15% threshold")

        with patch.object(seed, "_fetch_real_articles", return_value=[]), \
             patch.object(seed, "_classify_outcome", return_value=ambiguous_result):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        outcomes = bt_conn.execute("SELECT * FROM outcomes WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(outcomes) == 0
        assert report.outcomes_written == 0
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_idempotent_rerun_does_not_duplicate_predictions():
    print("=== seed_historical_data: running twice does not duplicate a seeded predictions row for the same occurrence ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        real_article = NewsArticle(
            title="CPI in line", summary="Steady inflation read", source="Test Wire", source_type="rss_reuters_business",
            published_utc=fact.event_time_utc - dt.timedelta(hours=2), url="https://example.test/idempotent",
        )

        with patch.object(seed, "_fetch_real_articles", return_value=[real_article]), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))
            seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        preds = bt_conn.execute("SELECT * FROM predictions WHERE event_title = ? AND instrument = ?", ("CPI m/m", "XAUUSD")).fetchall()
        assert len(preds) == 1  # not 2
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_no_placeholder_facts_in_the_shipped_dataset()
    test_calendar_side_write_always_happens()
    test_real_article_result_produces_a_real_scored_prediction()
    test_empty_article_result_writes_nothing_not_a_fallback()
    test_real_outcome_classification_writes_outcome()
    test_ambiguous_outcome_writes_nothing()
    test_idempotent_rerun_does_not_duplicate_predictions()
    print("All seed_historical_data tests passed.")
