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
            data = resp.get_json()
            assert len(data) == 1
            events = data[0]["events"]
            assert len(events) == 1
            assert events[0]["probability"] == 0.66
            assert events[0]["previous_probability"] == 0.54
    print("PASS\n")


def test_predictions_events_sorted_by_proximity_to_now():
    print("=== app: /api/predictions sorts a symbol's events by closeness to now, not feed order ===")
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
            event_time_utc=now + dt.timedelta(hours=2), forecast="75K", actual=None,
        )
        webapp_app._calendar_cache = {"events": None, "fetched_at": 0.0, "ttl_seconds": 900}  # avoid cross-test cache pollution
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=[far_event, near_event]), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", "CPI m/m", far_event.event_time_utc, 0.6, "bullish", 0.3)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", near_event.event_time_utc, None, "pending", None)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            events = data[0]["events"]
            assert len(events) == 2
            assert events[0]["event_title"] == "Non-Farm Employment Change", \
                f"expected the near event first, got {events[0]['event_title']!r}"
            assert events[1]["event_title"] == "CPI m/m"
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
    print("=== app: /api/predictions survives a fetch_calendar exception ===")
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
            assert len(data) == 1
            assert data[0]["symbol"] == "XAUUSD"
            assert data[0]["events"] == []
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
    test_predictions_events_sorted_by_proximity_to_now()
    test_calendar_fetch_failure_does_not_500()
    test_predictions_fetch_failure_does_not_500()
    test_calendar_fetch_is_cached_across_requests()
    print("All webapp.app tests passed.")
