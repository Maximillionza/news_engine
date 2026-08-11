"""
Tests for webapp.app — uses Flask's test client, no live server or
network needed. The calendar is never fetched live from a route anymore
(webapp/scheduler.py's background loop is the sole fetcher — see its
module docstring); tests seed webapp.store's calendar_snapshot table
directly instead of mocking fetch_calendar/filter_relevant_events.
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


def _seed_calendar(db_path, events, fetched_at=None):
    """Seeds webapp.store's calendar_snapshot table directly — the only way calendar data reaches a route now."""
    conn = store.get_connection(db_path)
    store.save_calendar_snapshot_if_changed(conn, events, fetched_at or dt.datetime.now(dt.timezone.utc))
    conn.close()


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
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, _fake_events())
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
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, [far_event, near_event])
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
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, [near_pending, far_resolved])
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
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, [pending_sibling, resolved_sibling])
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
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            _seed_calendar(db_path, _fake_events())
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
            # The actual accumulator call — direction + probability — not
            # just the article count. This is the real prediction the
            # article-based pipeline exists to produce.
            assert events[0]["article_prediction"] == {
                "direction": "bullish", "probability": 0.66, "article_count": 12,
            }
            assert events[0]["previous_article_prediction"] is None, "only one snapshot recorded — no previous to diff against"
    print("PASS\n")


def test_predictions_includes_previous_article_prediction_when_two_snapshots_exist():
    print("=== app: /api/predictions includes previous_article_prediction when the accumulator has recorded a material change ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            _seed_calendar(db_path, _fake_events())
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.66, "bullish", 0.35)
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            t1 = dt.datetime(2026, 8, 5, 10, 0, tzinfo=dt.timezone.utc)
            t2 = dt.datetime(2026, 8, 6, 10, 0, tzinfo=dt.timezone.utc)
            # First recorded snapshot: bullish. Second: a material change to bearish.
            backtest_store.record_prediction(
                bconn, "Non-Farm Employment Change", "XAUUSD", event_time,
                0.65, "bullish", 0.5, 20, False, scored_at_utc=t1,
            )
            backtest_store.record_prediction(
                bconn, "Non-Farm Employment Change", "XAUUSD", event_time,
                0.30, "bearish", 0.5, 45, False, scored_at_utc=t2,
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert events[0]["article_prediction"] == {
                "direction": "bearish", "probability": 0.30, "article_count": 45,
            }, "the CURRENT article prediction must be the most recent recorded snapshot"
            assert events[0]["previous_article_prediction"] == {
                "direction": "bullish", "probability": 0.65, "article_count": 20,
            }, "the PREVIOUS article prediction must be the second-most-recent recorded snapshot"
    print("PASS\n")


def test_predictions_article_prediction_is_none_when_accumulator_never_scored_it():
    print("=== app: /api/predictions leaves article_prediction as None for a symbol/event the accumulator never touched ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            _seed_calendar(db_path, _fake_events())
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "EURUSD")
            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            store.record_run(conn, "EURUSD", "Non-Farm Employment Change", event_time, 0.55, "bearish", -0.2)
            conn.close()
            # backtest_log.db is never populated — get_connection() will just create it empty.

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert len(events) == 1
            assert events[0]["article_prediction"] is None
    print("PASS\n")


def test_predictions_article_count_is_none_when_accumulator_never_scored_it():
    print("=== app: /api/predictions leaves article_count as None for a symbol/event the accumulator never touched ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            _seed_calendar(db_path, _fake_events())
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


def test_calendar_returns_not_yet_available_before_first_fetch():
    print("=== app: /api/calendar reports 'not yet available' (not a crash) before the background loop's first fetch ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["events"] == []
            assert "error" in data
            assert data["fetched_at_utc"] is None
    print("PASS\n")


def test_calendar_returns_persisted_snapshot_once_available():
    print("=== app: /api/calendar returns the persisted snapshot instantly, once one exists ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            fetched_at = dt.datetime(2026, 8, 10, 20, 0, tzinfo=dt.timezone.utc)
            _seed_calendar(db_path, _fake_events(), fetched_at=fetched_at)

            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data.get("error") is None
            assert len(data["events"]) == 1
            assert data["events"][0]["title"] == "Non-Farm Employment Change"
            assert data["fetched_at_utc"] == fetched_at.isoformat()
    print("PASS\n")


def test_predictions_returns_not_yet_available_before_first_fetch():
    print("=== app: /api/predictions reports 'not yet available' (not a crash) before the background loop's first fetch ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "error" in data
            assert len(data["predictions"]) == 1
            assert data["predictions"][0]["symbol"] == "XAUUSD"
            assert data["predictions"][0]["events"] == []
    print("PASS\n")


def test_predictions_no_error_field_on_success():
    print("=== app: /api/predictions has no 'error' key once a calendar snapshot is persisted ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, _fake_events())
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            assert data.get("error") is None
            assert len(data["predictions"]) == 1
    print("PASS\n")


def test_calendar_and_predictions_read_the_same_persisted_snapshot():
    print("=== app: /api/calendar and /api/predictions both read the SAME persisted snapshot, no divergence ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, _fake_events())

            client = webapp_app.app.test_client()
            calendar_resp = client.get("/api/calendar").get_json()
            predictions_resp = client.get("/api/predictions").get_json()

            assert len(calendar_resp["events"]) == 1
            # Neither route ever fetches live — both are pure reads of the
            # one persisted row, so there's no possibility of the two
            # routes disagreeing about what "current" means, unlike the
            # old per-route in-memory cache which could independently expire.
            assert calendar_resp["fetched_at_utc"] is not None
            assert predictions_resp.get("error") is None
    print("PASS\n")


if __name__ == "__main__":
    test_add_list_remove_symbol()
    test_add_unrecognized_symbol_rejected()
    test_predictions_endpoint_reflects_stored_runs()
    test_predictions_sorts_resolved_events_by_proximity_to_now()
    test_predictions_prefers_resolved_over_pending_regardless_of_distance()
    test_predictions_prefers_resolved_event_over_pending_sibling_at_same_timestamp()
    test_predictions_includes_article_count_from_accumulator_db()
    test_predictions_includes_previous_article_prediction_when_two_snapshots_exist()
    test_predictions_article_prediction_is_none_when_accumulator_never_scored_it()
    test_predictions_article_count_is_none_when_accumulator_never_scored_it()
    test_prediction_history_endpoint_returns_full_run_history()
    test_prediction_history_endpoint_missing_event_title_returns_empty()
    test_calendar_returns_not_yet_available_before_first_fetch()
    test_calendar_returns_persisted_snapshot_once_available()
    test_predictions_returns_not_yet_available_before_first_fetch()
    test_predictions_no_error_field_on_success()
    test_calendar_and_predictions_read_the_same_persisted_snapshot()
    print("All webapp.app tests passed.")
