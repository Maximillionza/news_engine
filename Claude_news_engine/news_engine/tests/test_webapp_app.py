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


def test_predictions_prefers_future_pending_event_over_a_past_stuck_pending_one():
    print("=== app: among still-pending events, a genuinely upcoming one outranks one whose release time already passed ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        # Real-world shape observed live: an event's release time passes but
        # it never resolves (the live calendar feed hasn't published its
        # actual yet — a feed-lag issue, not a code bug), so it stays
        # "pending" indefinitely. A pure abs(distance)-to-now sort treats
        # "6h48m in the past, still stuck" as CLOSER than "11h in the
        # future, genuinely upcoming" and keeps showing the stale one —
        # exactly the bug this test locks in the fix for.
        past_stuck_pending = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=6, minutes=48), forecast="0.1%", actual=None,
        )
        future_upcoming_pending = EconomicEvent(
            title="PPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=11), forecast="0.2%", actual=None,
        )
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, [past_stuck_pending, future_upcoming_pending])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", "CPI m/m", past_stuck_pending.event_time_utc, None, "pending", None)
            store.record_run(conn, "XAUUSD", "PPI m/m", future_upcoming_pending.event_time_utc, None, "pending", None)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert events[0]["event_title"] == "PPI m/m", (
                f"expected the genuinely upcoming pending event first, not the past one still stuck pending, "
                f"got {events[0]['event_title']!r}"
            )
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


def test_predictions_shows_article_prediction_even_when_essence_score_missing():
    print("=== /api/predictions: article_prediction/print_prediction show even when NO essence-only score exists yet for this symbol ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            _seed_calendar(db_path, _fake_events())
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            # Deliberately NO store.record_run() call — simulates a newly-added
            # symbol before webapp/scheduler.py's next essence-only scoring cycle.
            conn.close()

            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_prediction(
                bconn, "Non-Farm Employment Change", "XAUUSD", event_time,
                0.66, "bullish", 0.4, 12, False,
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            entry = next(e for e in data["predictions"] if e["symbol"] == "XAUUSD")
            event = entry["events"][0]
            assert event["article_prediction"] is not None  # THE bug fix — this was previously unreachable without an essence score
            assert event["article_prediction"] == {
                "direction": "bullish", "probability": 0.66, "article_count": 12,
            }
            assert event["direction"] == "pending", "no essence-only run recorded — direction must default to 'pending', not crash or None"
            assert event["probability"] is None
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


def test_event_history_endpoint_returns_occurrences_and_trend():
    print("=== app: /api/event_history returns past occurrences plus a summarized trend ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(store, "DB_PATH", db_path):
            conn = store.get_connection(db_path)
            for month, actual, surprise in [(6, "0.4%", "higher"), (7, "0.5%", "higher")]:
                event = EconomicEvent(
                    title="CPI m/m", country="USD", impact="High",
                    event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                    forecast="0.3%", previous="0.3%", actual=actual,
                )
                store.upsert_event_history(conn, event, surprise, now=dt.datetime(2026, month, 12, 13, 0, tzinfo=UTC_TZ))
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/event_history?title=CPI m/m")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["occurrences"]) == 2
            assert data["occurrences"][0]["actual"] == "0.5%"  # most recent first
            assert "trend_summary" in data
    print("PASS\n")


def test_event_history_endpoint_unknown_title_returns_empty():
    print("=== app: /api/event_history for an unknown title returns an empty list, not a 500 ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()
            resp = client.get("/api/event_history?title=Nonexistent Event")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["occurrences"] == []
    print("PASS\n")


def test_predictions_includes_print_prediction_when_accumulator_scored_it():
    print("=== app: /api/predictions includes print_prediction sourced from the accumulator's print_predictions table ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = _fake_events()
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", events[0].title, events[0].event_time_utc, 0.6, "bullish", 0.4)
            conn.close()

            from scoring.print_direction import PrintCall
            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_print_prediction_if_changed(
                bconn, events[0].title, events[0].event_time_utc,
                PrintCall(direction="higher", confidence=0.62, article_count=4),
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event_entry = data["predictions"][0]["events"][0]
            assert event_entry["print_prediction"] == {"direction": "higher", "confidence": 0.62}
    print("PASS\n")


def test_predictions_print_prediction_is_none_when_never_scored():
    print("=== app: /api/predictions omits print_prediction (None) when the accumulator never made a print call ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = _fake_events()
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", events[0].title, events[0].event_time_utc, 0.6, "bullish", 0.4)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event_entry = data["predictions"][0]["events"][0]
            assert event_entry["print_prediction"] is None
    print("PASS\n")


def test_predictions_includes_trend_signal_and_kalshi_read_when_present():
    print("=== app: /api/predictions includes trend_signal and kalshi_read when real data exists for them ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = _fake_events()
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")

            # Two prior CONFIRMED occurrences of the same title, same
            # surprise_direction, at earlier event_time_utc values — a
            # streak of length 2 (MIN_STREAK_LENGTH), enough for
            # compute_trend_signal() to return a real TrendSignal.
            prior_event_1 = EconomicEvent(
                title=events[0].title, country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 7, 7, 12, 30, tzinfo=UTC_TZ),
                forecast="70K", actual="80K",
            )
            prior_event_2 = EconomicEvent(
                title=events[0].title, country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 6, 5, 12, 30, tzinfo=UTC_TZ),
                forecast="65K", actual="72K",
            )
            store.upsert_event_history(conn, prior_event_1, "higher", now=prior_event_1.event_time_utc)
            store.upsert_event_history(conn, prior_event_2, "higher", now=prior_event_2.event_time_utc)
            conn.close()

            from dataclasses import dataclass

            @dataclass
            class _FakeKalshiRead:
                strike: float
                implied_direction: str
                implied_probability: float
                open_interest: float

            bconn = backtest_store.get_connection(backtest_db_path)
            read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.62, open_interest=100.0)
            backtest_store.record_kalshi_read_if_changed(
                bconn, events[0].title, events[0].event_time_utc, read, now=events[0].event_time_utc,
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event = data["predictions"][0]["events"][0]
            assert event["trend_signal"] is not None
            assert event["trend_signal"]["direction"] == "higher"
            assert event["kalshi_read"] is not None
            assert event["kalshi_read"]["implied_direction"] in ("higher", "lower", "in_line")
    print("PASS\n")


def test_predictions_trend_signal_and_kalshi_read_absent_when_nothing_recorded():
    print("=== app: /api/predictions leaves trend_signal and kalshi_read as None, not fabricated, when nothing real exists for them ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = _fake_events()
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", events[0].title, events[0].event_time_utc, 0.6, "bullish", 0.4)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event = data["predictions"][0]["events"][0]
            assert event["trend_signal"] is None
            assert event["kalshi_read"] is None
    print("PASS\n")


def test_trend_signal_includes_instrument_relative_lean():
    print("=== /api/predictions: trend_signal gains instrument_lean, translating raw higher/lower into a BUY/SELL-style lean ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = [
                EconomicEvent(
                    title="CPI m/m", country="USD", impact="High",
                    event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
                    forecast="0.2%", actual="0.4%",
                )
            ]
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")

            # Two prior CONFIRMED "higher" occurrences of CPI m/m — a streak
            # of length 2 (MIN_STREAK_LENGTH), enough for compute_trend_signal()
            # to return a real TrendSignal with direction="higher".
            prior_event_1 = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 7, 7, 12, 30, tzinfo=UTC_TZ),
                forecast="0.2%", actual="0.4%",
            )
            prior_event_2 = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 6, 5, 12, 30, tzinfo=UTC_TZ),
                forecast="0.2%", actual="0.3%",
            )
            store.upsert_event_history(conn, prior_event_1, "higher", now=prior_event_1.event_time_utc)
            store.upsert_event_history(conn, prior_event_2, "higher", now=prior_event_2.event_time_utc)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event = next(e for e in data["predictions"][0]["events"] if e["event_title"] == "CPI m/m")
            assert event["trend_signal"]["direction"] == "higher"
            # CPI m/m is higher_bullish -> a 'higher' trend is USD-bullish ->
            # XAUUSD (inverse) -> bearish for gold
            assert event["trend_signal"]["instrument_lean"] == "bearish"
    print("PASS\n")


def test_trend_signal_instrument_lean_none_for_unmapped_title():
    print("=== /api/predictions: instrument_lean is None (not fabricated) when the event title has no EVENT_SURPRISE_DIRECTION entry ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            unmapped_title = "Building Permits"  # not present in EVENT_SURPRISE_DIRECTION
            events = [
                EconomicEvent(
                    title=unmapped_title, country="USD", impact="High",
                    event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
                    forecast="1.4M", actual="1.5M",
                )
            ]
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")

            prior_event_1 = EconomicEvent(
                title=unmapped_title, country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 7, 7, 12, 30, tzinfo=UTC_TZ),
                forecast="1.4M", actual="1.5M",
            )
            prior_event_2 = EconomicEvent(
                title=unmapped_title, country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 6, 5, 12, 30, tzinfo=UTC_TZ),
                forecast="1.4M", actual="1.5M",
            )
            store.upsert_event_history(conn, prior_event_1, "higher", now=prior_event_1.event_time_utc)
            store.upsert_event_history(conn, prior_event_2, "higher", now=prior_event_2.event_time_utc)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event = next(e for e in data["predictions"][0]["events"] if e["event_title"] == unmapped_title)
            assert event["trend_signal"] is not None
            assert event["trend_signal"]["direction"] == "higher"
            assert event["trend_signal"]["instrument_lean"] is None
    print("PASS\n")


def test_predictions_does_not_500_for_fx_cross_symbol_outside_instruments():
    print("=== /api/predictions: a tracked fx_cross symbol (not in the 2-entry INSTRUMENTS dict) with a real trend_signal returns 200, instrument_lean=None, instead of crashing the whole endpoint ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            # GBPAUD is 6-letter FX-shaped but neither USDxxx nor xxxUSD ->
            # classify_symbol() resolves it to symbol_class="fx_cross",
            # usd_relationship=None — it is NOT a key in config.settings.
            # INSTRUMENTS (only XAUUSD/US30 are), so the old
            # INSTRUMENTS[instrument] lookup in _trend_instrument_lean()
            # raised an unhandled KeyError for exactly this symbol.
            events = [
                EconomicEvent(
                    title="CPI m/m", country="USD", impact="High",
                    event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
                    forecast="0.2%", actual="0.4%",
                )
            ]
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "GBPAUD")

            # Two prior CONFIRMED "higher" occurrences of CPI m/m — enough
            # for compute_trend_signal() to return a real TrendSignal.
            prior_event_1 = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 7, 7, 12, 30, tzinfo=UTC_TZ),
                forecast="0.2%", actual="0.4%",
            )
            prior_event_2 = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 6, 5, 12, 30, tzinfo=UTC_TZ),
                forecast="0.2%", actual="0.3%",
            )
            store.upsert_event_history(conn, prior_event_1, "higher", now=prior_event_1.event_time_utc)
            store.upsert_event_history(conn, prior_event_2, "higher", now=prior_event_2.event_time_utc)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            assert resp.status_code == 200
            data = resp.get_json()
            symbol_entry = next(s for s in data["predictions"] if s["symbol"] == "GBPAUD")
            event = next(e for e in symbol_entry["events"] if e["event_title"] == "CPI m/m")
            assert event["trend_signal"] is not None
            assert event["trend_signal"]["direction"] == "higher"
            assert event["trend_signal"]["instrument_lean"] is None
    print("PASS\n")


def test_history_endpoint_returns_numeric_and_text_rows():
    print("=== app: /api/history returns build_print_call_history()'s rows as JSON, including the instrument field ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
            event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
                forecast="0.1%", previous="-0.4%", actual="0.1%",
            )
            conn = store.get_connection(db_path)
            store.upsert_event_history(conn, event, "in_line", now=event_time)
            conn.close()

            from scoring.print_direction import PrintCall
            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_print_prediction_if_changed(
                bconn, "CPI m/m", event_time,
                PrintCall(direction="in_line", confidence=0.4, article_count=89), now=event_time,
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/history")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["rows"]) == 1
            assert data["rows"][0]["event_title"] == "CPI m/m"
            assert data["rows"][0]["instrument"] is None
            assert data["rows"][0]["outcome"] == "Confirmed"
    print("PASS\n")


def test_history_endpoint_empty_when_nothing_resolved():
    print("=== app: /api/history returns an empty list (200, not 500) when nothing has resolved yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            store.get_connection(db_path).close()
            backtest_store.get_connection(backtest_db_path).close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/history")
            assert resp.status_code == 200
            assert resp.get_json()["rows"] == []
    print("PASS\n")


def test_calendar_date_route_returns_events_and_calls_for_that_date_only():
    print("=== GET /api/calendar/date/<date>: returns only that date's events, with each tracked symbol's call ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = [
                EconomicEvent(
                    title="Non-Farm Employment Change", country="USD", impact="High",
                    event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
                    forecast="75K", actual="44K",
                ),
                EconomicEvent(
                    title="CPI m/m", country="USD", impact="High",
                    event_time_utc=dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ),
                    forecast="0.2%", actual=None,
                ),
            ]
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            nfp_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=dt.timezone.utc)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", nfp_time, 0.66, "bullish", 0.35)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar/date/2026-08-12")
            data = resp.get_json()
            assert len(data["events"]) == 1  # only the one event actually on 2026-08-12
            assert data["events"][0]["title"] == "Non-Farm Employment Change"
            assert data["events"][0]["calls"]["XAUUSD"] is not None
            assert data["events"][0]["calls"]["XAUUSD"]["direction"] == "bullish"
            assert data["events"][0]["calls"]["XAUUSD"]["probability"] == 0.66
    print("PASS\n")


def test_calendar_date_route_empty_date_returns_empty_list_not_error():
    print("=== GET /api/calendar/date/<date>: a date with no events returns {events: []}, not a 404/500 ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            _seed_calendar(db_path, _fake_events())
            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar/date/2026-12-25")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["events"] == []
    print("PASS\n")


def test_calendar_date_route_invalid_date_returns_400():
    print("=== GET /api/calendar/date/<date>: a malformed date returns 400, not a 500 ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar/date/not-a-date")
            assert resp.status_code == 400
            assert "error" in resp.get_json()
    print("PASS\n")


def test_predictions_recomputes_stale_pending_direction_from_event_history():
    print("=== app: R1 fix — a stale 'pending' essence direction is recomputed from event_history's real actual ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            event_time = dt.datetime(2026, 8, 13, 12, 30, tzinfo=dt.timezone.utc)
            # Calendar snapshot still shows actual=None — exactly what the
            # scheduler saw when it wrote the "pending" prediction_runs row.
            calendar_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=event_time, forecast="0.2%", previous="0.2%", actual=None,
            )
            _seed_calendar(db_path, [calendar_event])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", "CPI m/m", event_time, None, "pending", None)

            # A fallback script (scripts/fill_missing_actuals.py) later
            # resolved the real actual into event_history — WITHOUT a
            # fresh scheduler cycle ever following it (the bug this fix
            # targets).
            resolved_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=event_time, forecast="0.2%", previous="0.2%", actual="0.5%",
            )
            store.upsert_event_history(conn, resolved_event, "higher", dt.datetime.now(dt.timezone.utc), source="live_web_fallback")
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert len(events) == 1
            assert events[0]["direction"] != "pending", f"expected a recomputed direction, still 'pending': {events[0]}"
            assert events[0]["direction"] == "bearish"  # CPI beat (higher_bullish for USD) -> XAUUSD inverse -> bearish
            assert events[0]["probability"] is not None
            assert events[0]["recomputed_from_event_history"] is True
    print("PASS\n")


def test_predictions_stale_pending_without_resolved_history_stays_pending():
    print("=== app: no matching resolved event_history row -> direction stays 'pending', not fabricated ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            event_time = dt.datetime(2026, 8, 13, 12, 30, tzinfo=dt.timezone.utc)
            calendar_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=event_time, forecast="0.2%", previous="0.2%", actual=None,
            )
            _seed_calendar(db_path, [calendar_event])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", "CPI m/m", event_time, None, "pending", None)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            assert len(events) == 1
            assert events[0]["direction"] == "pending"
            assert events[0]["recomputed_from_event_history"] is False
    print("PASS\n")


def test_calendar_route_includes_feed_staleness_seconds():
    print("=== GET /api/calendar: response includes feed_staleness_seconds ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, _fake_events())
            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar")
            data = resp.get_json()
            assert "feed_staleness_seconds" in data
    print("PASS\n")


def test_calendar_date_route_includes_estimated_macro_event_for_that_date():
    print("=== GET /api/calendar/date/<date>: includes a macro-only event for that date, marked estimated ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            _seed_calendar(db_path, [])  # FF has nothing on this date yet
            conn = store.get_connection(db_path)
            now = dt.datetime.now(dt.timezone.utc)
            store.upsert_macro_calendar_event(conn, "Core PCE Price Index m/m", "2026-08-26", None, "unconfirmed", now)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar/date/2026-08-26")
            data = resp.get_json()
            assert len(data["events"]) == 1
            assert data["events"][0]["title"] == "Core PCE Price Index m/m"
            assert data["events"][0]["estimated"] is True
            assert data["events"][0]["calls"] == {}
    print("PASS\n")


def test_calendar_date_route_prefers_ff_over_macro_duplicate():
    print("=== GET /api/calendar/date/<date>: a macro row already covered by a real FF event is NOT duplicated ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            ff_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ),
                forecast="0.2%", actual=None,
            )
            _seed_calendar(db_path, [ff_event])
            conn = store.get_connection(db_path)
            now = dt.datetime.now(dt.timezone.utc)
            store.upsert_macro_calendar_event(conn, "CPI m/m", "2026-08-26", None, "unconfirmed", now)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar/date/2026-08-26")
            data = resp.get_json()
            assert len(data["events"]) == 1
            assert data["events"][0]["estimated"] is False
    print("PASS\n")


def test_monthahead_merges_ff_and_macro_events():
    print("=== GET /api/calendar/monthahead: merges FF (exact) and macro_calendar (estimated) events, no duplicates ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            today = dt.date.today()
            ff_event_date = today + dt.timedelta(days=3)
            ff_event = EconomicEvent(
                title="Unemployment Claims", country="USD", impact="Medium",
                event_time_utc=dt.datetime.combine(ff_event_date, dt.time(12, 30), tzinfo=dt.timezone.utc),
            )
            _seed_calendar(db_path, [ff_event])

            conn = store.get_connection(db_path)
            now = dt.datetime.now(dt.timezone.utc)
            # A macro row for a title/date FF does NOT have yet — should surface as estimated.
            macro_only_date = (today + dt.timedelta(days=20)).isoformat()
            store.upsert_macro_calendar_event(conn, "CPI m/m", macro_only_date, None, "unconfirmed", now)
            # A macro row for the SAME (title, date) FF already has — must be skipped, not duplicated.
            store.upsert_macro_calendar_event(conn, "Unemployment Claims", ff_event_date.isoformat(), None, "unconfirmed", now)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar/monthahead")
            data = resp.get_json()
            titles_and_estimated = {(e["title"], e["estimated"]) for e in data["events"]}

            assert ("Unemployment Claims", False) in titles_and_estimated  # FF's exact entry, not the macro duplicate
            assert ("CPI m/m", True) in titles_and_estimated               # macro-only, estimated
            assert len(data["events"]) == 2  # the duplicate macro row for Unemployment Claims must NOT appear separately
    print("PASS\n")


def test_monthahead_confirmed_macro_row_reports_estimated_false():
    print("=== GET /api/calendar/monthahead: a CONFIRMED macro row (no FF duplicate present) reports estimated=false ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            _seed_calendar(db_path, [])  # no FF events at all this cycle
            conn = store.get_connection(db_path)
            now = dt.datetime.now(dt.timezone.utc)
            confirm_date = (dt.date.today() + dt.timedelta(days=15)).isoformat()
            confirmed_time = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=15)
            store.upsert_macro_calendar_event(conn, "PPI m/m", confirm_date, None, "unconfirmed", now)
            store.confirm_macro_calendar_event(conn, "PPI m/m", confirmed_time, now)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/calendar/monthahead")
            data = resp.get_json()
            ppi_events = [e for e in data["events"] if e["title"] == "PPI m/m"]
            assert len(ppi_events) == 1
            assert ppi_events[0]["estimated"] is False
    print("PASS\n")


def test_predictions_keeps_a_recently_resolved_event_after_it_scrolls_out_of_ff_snapshot():
    print("=== app: /api/predictions still shows a recently-resolved event (e.g. CPI) even after FF's live snapshot moves past it ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            now = dt.datetime.now(dt.timezone.utc)
            # FF's CURRENT snapshot only has a later, unrelated event —
            # simulating the real live symptom: CPI's date has already
            # scrolled out of FF's "thisweek" window.
            future_event = EconomicEvent(
                title="FOMC Meeting Minutes", country="USD", impact="High",
                event_time_utc=now + dt.timedelta(days=2),
            )
            _seed_calendar(db_path, [future_event])

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            cpi_time = now - dt.timedelta(days=3)
            store.record_run(conn, "XAUUSD", "CPI m/m", cpi_time, 0.71, "bullish", 0.6)
            resolved_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High", event_time_utc=cpi_time,
                forecast="0.2%", previous="0.2%", actual="0.1%",
            )
            store.upsert_event_history(conn, resolved_event, "lower", now)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            titles = {e["event_title"] for e in events}
            assert "CPI m/m" in titles, f"expected CPI m/m to still appear, got {titles}"
            cpi_entry = next(e for e in events if e["event_title"] == "CPI m/m")
            assert cpi_entry["direction"] == "bullish"
            assert cpi_entry["probability"] == 0.71
    print("PASS\n")


def test_predictions_excludes_a_resolved_event_older_than_the_retention_window():
    print("=== app: /api/predictions does NOT resurrect an event resolved long before the retention window (that's the History tab's job) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            now = dt.datetime.now(dt.timezone.utc)
            future_event = EconomicEvent(
                title="FOMC Meeting Minutes", country="USD", impact="High",
                event_time_utc=now + dt.timedelta(days=2),
            )
            _seed_calendar(db_path, [future_event])

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            old_cpi_time = now - dt.timedelta(days=30)  # well outside PREDICTIONS_RECENT_RESOLVED_RETENTION_DAYS (7)
            store.record_run(conn, "XAUUSD", "CPI m/m", old_cpi_time, 0.71, "bullish", 0.6)
            old_resolved_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High", event_time_utc=old_cpi_time,
                forecast="0.2%", previous="0.2%", actual="0.1%",
            )
            store.upsert_event_history(conn, old_resolved_event, "lower", now)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            titles = {e["event_title"] for e in events}
            assert "CPI m/m" not in titles, f"a 30-day-old resolved event should not resurface here, got {titles}"
    print("PASS\n")


def test_predictions_does_not_duplicate_a_recently_resolved_event_ff_still_has():
    print("=== app: a recently-resolved event still present in FF's OWN snapshot is not duplicated by the retention merge ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            now = dt.datetime.now(dt.timezone.utc)
            cpi_time = now - dt.timedelta(days=2)
            ff_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High", event_time_utc=cpi_time,
                forecast="0.2%", previous="0.2%", actual="0.1%",
            )
            _seed_calendar(db_path, [ff_event])  # FF STILL has it this cycle

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", "CPI m/m", cpi_time, 0.71, "bullish", 0.6)
            store.upsert_event_history(conn, ff_event, "lower", now)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            matching = [e for e in events if e["event_title"] == "CPI m/m"]
            assert len(matching) == 1, f"expected exactly one CPI m/m entry, got {len(matching)}"
    print("PASS\n")


if __name__ == "__main__":
    test_add_list_remove_symbol()
    test_add_unrecognized_symbol_rejected()
    test_predictions_endpoint_reflects_stored_runs()
    test_predictions_sorts_resolved_events_by_proximity_to_now()
    test_predictions_prefers_resolved_over_pending_regardless_of_distance()
    test_predictions_prefers_resolved_event_over_pending_sibling_at_same_timestamp()
    test_predictions_prefers_future_pending_event_over_a_past_stuck_pending_one()
    test_predictions_includes_article_count_from_accumulator_db()
    test_predictions_includes_previous_article_prediction_when_two_snapshots_exist()
    test_predictions_article_prediction_is_none_when_accumulator_never_scored_it()
    test_predictions_article_count_is_none_when_accumulator_never_scored_it()
    test_predictions_shows_article_prediction_even_when_essence_score_missing()
    test_prediction_history_endpoint_returns_full_run_history()
    test_prediction_history_endpoint_missing_event_title_returns_empty()
    test_calendar_returns_not_yet_available_before_first_fetch()
    test_calendar_returns_persisted_snapshot_once_available()
    test_predictions_returns_not_yet_available_before_first_fetch()
    test_predictions_no_error_field_on_success()
    test_calendar_and_predictions_read_the_same_persisted_snapshot()
    test_event_history_endpoint_returns_occurrences_and_trend()
    test_event_history_endpoint_unknown_title_returns_empty()
    test_predictions_includes_print_prediction_when_accumulator_scored_it()
    test_predictions_print_prediction_is_none_when_never_scored()
    test_predictions_includes_trend_signal_and_kalshi_read_when_present()
    test_predictions_trend_signal_and_kalshi_read_absent_when_nothing_recorded()
    test_trend_signal_includes_instrument_relative_lean()
    test_trend_signal_instrument_lean_none_for_unmapped_title()
    test_predictions_does_not_500_for_fx_cross_symbol_outside_instruments()
    test_calendar_date_route_returns_events_and_calls_for_that_date_only()
    test_calendar_date_route_empty_date_returns_empty_list_not_error()
    test_calendar_date_route_invalid_date_returns_400()
    test_history_endpoint_returns_numeric_and_text_rows()
    test_history_endpoint_empty_when_nothing_resolved()
    test_predictions_recomputes_stale_pending_direction_from_event_history()
    test_predictions_stale_pending_without_resolved_history_stays_pending()
    test_calendar_route_includes_feed_staleness_seconds()
    test_calendar_date_route_includes_estimated_macro_event_for_that_date()
    test_calendar_date_route_prefers_ff_over_macro_duplicate()
    test_monthahead_merges_ff_and_macro_events()
    test_monthahead_confirmed_macro_row_reports_estimated_false()
    test_predictions_keeps_a_recently_resolved_event_after_it_scrolls_out_of_ff_snapshot()
    test_predictions_excludes_a_resolved_event_older_than_the_retention_window()
    test_predictions_does_not_duplicate_a_recently_resolved_event_ff_still_has()
    print("All webapp.app tests passed.")
