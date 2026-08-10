"""
Tests for webapp.app — uses Flask's test client, no live server or
network needed (calendar fetch is patched).
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
import webapp.app as webapp_app
import webapp.store as store
import scoring.backtest_store as backtest_store


def _fake_events():
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="75K", actual="44K",
        )
    ]


def test_add_list_remove_symbol():
    print("=== app: POST/GET/DELETE /api/symbols round-trips ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()

            resp = client.post("/api/symbols", json={"ticker": "eurusd"})
            assert resp.status_code == 201
            assert resp.get_json()["symbol"] == "EURUSD"

            resp = client.get("/api/symbols")
            symbols = [s["symbol"] for s in resp.get_json()]
            assert symbols == ["EURUSD"]

            resp = client.delete("/api/symbols/EURUSD")
            assert resp.status_code == 204

            resp = client.get("/api/symbols")
            assert resp.get_json() == []
    print("PASS\n")


def test_add_unrecognized_symbol_rejected():
    print("=== app: POST /api/symbols with a malformed ticker returns 400 ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()
            resp = client.post("/api/symbols", json={"ticker": "NOTASYMBOL123"})
            assert resp.status_code == 400
            assert "error" in resp.get_json()
    print("PASS\n")


def test_predictions_endpoint_reflects_stored_runs():
    print("=== app: /api/predictions surfaces latest + previous run with delta info ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=_fake_events()), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.54, "bullish", 0.20)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.66, "bullish", 0.35)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()["predictions"]
            assert len(data) == 1
            events = data[0]["events"]
            assert len(events) == 1
            assert events[0]["probability"] == 0.66
            assert events[0]["previous_probability"] == 0.54
    print("PASS\n")


def test_predictions_sorts_resolved_events_by_proximity_to_now():
    print("=== app: among resolved events, /api/predictions picks the one closest to now ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        # Feed order deliberately puts the FAR event first and the NEAR
        # event second — a naive events[0] would pick the wrong one.
        far_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(days=10), forecast="0.2%", actual="0.3%",
        )
        near_event = EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=2), forecast="75K", actual="80K",
        )
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=[far_event, near_event]), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", "CPI m/m", far_event.event_time_utc, 0.6, "bullish", 0.3)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", near_event.event_time_utc, 0.7, "bullish", 0.4)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()["predictions"]
            events = data[0]["events"]
            assert len(events) == 2
            assert events[0]["event_title"] == "Non-Farm Employment Change", \
                f"expected the near event first, got {events[0]['event_title']!r}"
            assert events[1]["event_title"] == "CPI m/m"
    print("PASS\n")


def test_predictions_prefers_resolved_over_pending_regardless_of_distance():
    print("=== app: a resolved score always outranks a nearer-but-pending event — confirmed product choice ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        # The event that scored is CHRONOLOGICALLY FARTHER than the one
        # that's still pending — a pure-proximity sort would pick the
        # pending one, which is exactly the bug this test locks in the fix
        # for (confirmed live: a resolved call is more useful to show than
        # an "awaiting" placeholder for a nearer event).
        far_resolved = EconomicEvent(
            title="PPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(days=3), forecast="0.2%", actual="0.5%",
        )
        near_pending = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=1), forecast="0.1%", actual=None,
        )
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=[near_pending, far_resolved]), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "US30")
            store.record_run(conn, "US30", "CPI m/m", near_pending.event_time_utc, None, "pending", None)
            store.record_run(conn, "US30", "PPI m/m", far_resolved.event_time_utc, 0.66, "bullish", 0.35)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert events[0]["event_title"] == "PPI m/m", (
                f"expected the resolved-but-farther event first, got {events[0]['event_title']!r}"
            )
            assert events[0]["direction"] == "bullish"
    print("PASS\n")


def test_predictions_prefers_resolved_event_over_pending_sibling_at_same_timestamp():
    print("=== app: among events tied on timestamp, a resolved one beats a still-pending sibling ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        # Real-world shape: a release day publishes several sub-metrics at the
        # IDENTICAL timestamp. Feed order deliberately puts the still-pending
        # sibling first, so a naive time-only sort would keep it at events[0]
        # even though the other one has an actual real score.
        shared_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=dt.timezone.utc)
        pending_sibling = EconomicEvent(
            title="Core CPI m/m", country="USD", impact="High",
            event_time_utc=shared_time, forecast="0.2%", actual=None,
        )
        resolved_sibling = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=shared_time, forecast="0.1%", actual="0.3%",
        )
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=[pending_sibling, resolved_sibling]), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", "Core CPI m/m", shared_time, None, "pending", None)
            store.record_run(conn, "XAUUSD", "CPI m/m", shared_time, 0.71, "bullish", 0.55)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert events[0]["event_title"] == "CPI m/m", (
                f"expected the resolved sibling first despite feed order and identical timestamp, "
                f"got {events[0]['event_title']!r}"
            )
            assert events[0]["direction"] == "bullish"
    print("PASS\n")


def test_predictions_includes_article_count_from_accumulator_db():
    print("=== app: /api/predictions includes article_count read from the accumulator's own DB, for symbols it tracks ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=_fake_events()), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.66, "bullish", 0.35)
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_prediction(
                bconn, "Non-Farm Employment Change", "XAUUSD", event_time,
                0.66, "bullish", 0.4, 12, False,
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert len(events) == 1
            assert events[0]["article_count"] == 12
    print("PASS\n")


def test_predictions_article_count_is_none_when_accumulator_never_scored_it():
    print("=== app: /api/predictions leaves article_count as None for a symbol/event the accumulator never touched ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=_fake_events()), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "EURUSD")  # accumulator never tracks EURUSD (config.settings.INSTRUMENTS is XAUUSD/US30 only)
            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            store.record_run(conn, "EURUSD", "Non-Farm Employment Change", event_time, 0.55, "bearish", -0.2)
            conn.close()
            # backtest_log.db is never populated — get_connection() will just create it empty.

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert len(events) == 1
            assert events[0]["article_count"] is None
    print("PASS\n")


def test_prediction_history_endpoint_returns_full_run_history():
    print("=== app: /api/predictions/<symbol>/history returns the full oldest-first run history for that (symbol, event) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            conn = store.get_connection(db_path)
            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            t1 = dt.datetime(2026, 8, 5, 10, 0, tzinfo=dt.timezone.utc)
            t2 = dt.datetime(2026, 8, 5, 10, 15, tzinfo=dt.timezone.utc)
            store.record_run(conn, "XAUUSD", "CPI m/m", event_time, 0.54, "bullish", 0.20, scored_at_utc=t1)
            store.record_run(conn, "XAUUSD", "CPI m/m", event_time, 0.66, "bullish", 0.35, scored_at_utc=t2)
            # A different event for the same symbol — must not leak into the CPI history.
            store.record_run(conn, "XAUUSD", "NFP", event_time, 0.40, "bearish", -0.10, scored_at_utc=t1)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions/xauusd/history?event_title=CPI%20m/m")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) == 2, f"expected only the 2 CPI m/m runs, got {len(data)}"
            assert data[0]["probability"] == 0.54, "history must be oldest-first"
            assert data[1]["probability"] == 0.66
    print("PASS\n")


def test_prediction_history_endpoint_missing_event_title_returns_empty():
    print("=== app: /api/predictions/<symbol>/history with no event_title query param returns an empty list, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions/XAUUSD/history")
            assert resp.status_code == 200
            assert resp.get_json() == []
    print("PASS\n")


def test_calendar_fetch_failure_does_not_500():
    print("=== app: /api/calendar survives a fetch_calendar exception ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", side_effect=Exception("network down")):

            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["events"] == []
            assert "error" in data
    print("PASS\n")


def test_predictions_fetch_failure_does_not_500():
    print("=== app: /api/predictions survives a fetch_calendar exception, and surfaces it as a stale-data indicator ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", side_effect=Exception("network down")):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            assert resp.status_code == 200
            data = resp.get_json()
            # /api/calendar already surfaces a failed live fetch via an "error"
            # field so the frontend can flag stale data (see
            # test_calendar_fetch_failure_does_not_500) — /api/predictions was
            # silently swallowing the exact same failure with no way for the
            # frontend to know its calendar-derived event list might be stale.
            assert "error" in data, "predictions response should surface a failed calendar fetch, same as /api/calendar does"
            assert len(data["predictions"]) == 1
            assert data["predictions"][0]["symbol"] == "XAUUSD"
            assert data["predictions"][0]["events"] == []
    print("PASS\n")


def test_predictions_no_error_field_on_success():
    print("=== app: /api/predictions has no 'error' key when the calendar fetch succeeds ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=_fake_events()), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            assert data.get("error") is None
            assert len(data["predictions"]) == 1
    print("PASS\n")


def test_calendar_fetch_is_cached_across_requests():
    print("=== app: /api/calendar and /api/predictions share one cached fetch, not one per request ===")
    webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=_fake_events()) as mock_fetch, \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            client = webapp_app.app.test_client()
            client.get("/api/calendar")
            client.get("/api/calendar")
            client.get("/api/predictions")

            assert mock_fetch.call_count == 1, (
                f"expected 1 live fetch across 3 requests within the cache TTL, got {mock_fetch.call_count} — "
                "this is exactly the pattern that got the live feed rate-limited (429) in production"
            )
    print("PASS\n")


if __name__ == "__main__":
    test_add_list_remove_symbol()
    test_add_unrecognized_symbol_rejected()
    test_predictions_endpoint_reflects_stored_runs()
    test_predictions_sorts_resolved_events_by_proximity_to_now()
    test_predictions_prefers_resolved_over_pending_regardless_of_distance()
    test_predictions_prefers_resolved_event_over_pending_sibling_at_same_timestamp()
    test_predictions_includes_article_count_from_accumulator_db()
    test_predictions_article_count_is_none_when_accumulator_never_scored_it()
    test_prediction_history_endpoint_returns_full_run_history()
    test_prediction_history_endpoint_missing_event_title_returns_empty()
    test_calendar_fetch_failure_does_not_500()
    test_predictions_fetch_failure_does_not_500()
    test_predictions_no_error_field_on_success()
    test_calendar_fetch_is_cached_across_requests()
    print("All webapp.app tests passed.")
