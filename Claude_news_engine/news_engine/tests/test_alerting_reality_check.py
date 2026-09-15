# tests/test_alerting_reality_check.py
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from alerting import store
from alerting.reality_check import run_reality_check
from data_layer.dukascopy_feed import PricePoint

UTC = dt.timezone.utc


def _seed_alert(conn, severity: str, symbol: str, detected_at_utc: dt.datetime) -> int:
    return store.record_alert(
        conn, headline="H", source="s", url="u", published_utc=detected_at_utc,
        detected_at_utc=detected_at_utc, category="energy", severity=severity,
        classification_method="rule_tier", rationale=None,
        affected_symbols=[{"symbol": symbol, "channel": "safe_haven"}],
    )


def test_high_severity_alert_with_confirming_spike_is_no_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    # price at T0 = 2800.0, T+5min = 2812.0 (+$12, clears the $10 XAUUSD threshold)
    prices = [PricePoint(price=2800.0), PricePoint(price=2812.0), PricePoint(price=2815.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is False


def test_high_severity_alert_with_no_move_is_flagged_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    prices = [PricePoint(price=2800.0), PricePoint(price=2801.0), PricePoint(price=2800.5)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_mismatch is True


def test_missing_price_data_logs_no_data_not_a_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    with patch("alerting.reality_check.get_price_at", return_value=None):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is None


def test_low_severity_alert_with_confirming_move_is_flagged_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "Low", "XAUUSD", detected_at)

    # price at T0 = 2800.0, T+5min = 2812.0 (+$12, clears the $10 XAUUSD threshold)
    # -- a Low alert that actually moved the market is under-alerted.
    prices = [PricePoint(price=2800.0), PricePoint(price=2812.0), PricePoint(price=2815.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is True


def test_low_severity_alert_with_no_move_is_no_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "Low", "XAUUSD", detected_at)

    prices = [PricePoint(price=2800.0), PricePoint(price=2801.0), PricePoint(price=2800.5)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is False


def test_medium_severity_alert_with_confirming_move_is_never_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "Medium", "XAUUSD", detected_at)

    # move clears the threshold, but Medium never mismatches in v1.
    prices = [PricePoint(price=2800.0), PricePoint(price=2812.0), PricePoint(price=2815.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is False


def test_too_recent_alert_is_skipped_while_old_enough_alert_is_checked():
    conn = store.get_connection(":memory:")
    now = dt.datetime.now(UTC)
    recent_alert_id = _seed_alert(conn, "High", "XAUUSD", now - dt.timedelta(minutes=5))
    old_alert_id = _seed_alert(conn, "High", "XAUUSD", now - dt.timedelta(days=1))

    # Only the old-enough alert should ever call get_price_at, so three
    # PricePoints (t0, t5, t_secondary) is exactly enough for one alert.
    prices = [PricePoint(price=2800.0), PricePoint(price=2812.0), PricePoint(price=2815.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    recent_row = store.get_alert(conn, recent_alert_id)
    old_row = store.get_alert(conn, old_alert_id)
    assert recent_row.reality_check_at_utc is None
    assert old_row.reality_check_at_utc is not None
    assert old_row.reality_mismatch is False


def test_alert_with_no_affected_symbols_is_still_marked_checked():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = store.record_alert(
        conn, headline="H", source="s", url="u", published_utc=detected_at,
        detected_at_utc=detected_at, category="energy", severity="Low",
        classification_method="rule_tier", rationale=None, affected_symbols=[],
    )

    with patch("alerting.reality_check.get_price_at") as mock_get_price:
        run_reality_check(conn=conn)

    mock_get_price.assert_not_called()
    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is None
