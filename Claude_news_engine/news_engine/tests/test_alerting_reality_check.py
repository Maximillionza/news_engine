# tests/test_alerting_reality_check.py
from __future__ import annotations

import datetime as dt
import json
from unittest.mock import patch

import pytest

from alerting import lean_grading, reality_check, store
from alerting.reality_check import run_reality_check
from data_layer import minute_bars
from data_layer.dukascopy_feed import PricePoint

UTC = dt.timezone.utc

# B10 (2026-10-28): the mismatch rule reads hourly baselines; every test passes all four of these so none can
# reach the live default DB paths (test_explicit_args_never_touch_default_paths).
BASELINES = {"XAUUSD": {h: 10.0 for h in range(24)}}


def _fake_fetch(symbol, start, end):
    return {dt.datetime(2000, 1, 1, tzinfo=UTC): 1.0}   # one ancient bar: grading cells read no_data


def _run(conn, baselines=None, **extra):
    return run_reality_check(
        conn=conn, symbols=["XAUUSD"], baselines_by_symbol=BASELINES if baselines is None else baselines,
        fetch_bars=_fake_fetch, **extra)


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

    # price at T0 = 2800.0, T+5min = 2812.0 (+$12, clears the 10.0 hourly baseline)
    prices = [PricePoint(price=2800.0), PricePoint(price=2812.0), PricePoint(price=2815.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        _run(conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is False


def test_high_severity_alert_with_no_move_is_flagged_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    prices = [PricePoint(price=2800.0), PricePoint(price=2801.0), PricePoint(price=2800.5)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        _run(conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_mismatch is True


def test_missing_price_data_logs_no_data_not_a_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    with patch("alerting.reality_check.get_price_at", return_value=None):
        _run(conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is None


def test_low_severity_alert_with_confirming_move_is_flagged_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "Low", "XAUUSD", detected_at)

    # price at T0 = 2800.0, T+5min = 2812.0 (+$12, clears the 10.0 hourly baseline)
    # -- a Low alert that actually moved the market is under-alerted.
    prices = [PricePoint(price=2800.0), PricePoint(price=2812.0), PricePoint(price=2815.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        _run(conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is True


def test_low_severity_alert_with_no_move_is_no_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "Low", "XAUUSD", detected_at)

    prices = [PricePoint(price=2800.0), PricePoint(price=2801.0), PricePoint(price=2800.5)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        _run(conn)

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
        _run(conn)

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
        _run(conn)

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
        _run(conn)

    mock_get_price.assert_not_called()
    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is None


def test_run_returns_counts():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    _seed_alert(conn, "High", "XAUUSD", detected_at)   # no move -> mismatch
    _seed_alert(conn, "High", "US30", detected_at)     # no price data

    def fake_price(symbol, when):
        if symbol == "US30":
            return None
        return PricePoint(price=2800.0)

    with patch("alerting.reality_check.get_price_at", side_effect=fake_price):
        result = run_reality_check(
            conn=conn, symbols=["XAUUSD", "US30"],
            baselines_by_symbol={"XAUUSD": BASELINES["XAUUSD"], "US30": {h: 100.0 for h in range(24)}},
            fetch_bars=_fake_fetch)

    assert (result["checked"], result["mismatches"], result["no_price_data"]) == (2, 1, 1)


def test_30_minute_only_move_no_longer_clears_the_threshold():
    conn = store.get_connection(":memory:")
    alert_id = _seed_alert(conn, "High", "XAUUSD", dt.datetime.now(UTC) - dt.timedelta(days=1))
    # +1 at 5 min (below the 10.0 baseline), +12 at 30 min: the 30-minute move is stored, not compared.
    prices = [PricePoint(price=2800.0), PricePoint(price=2801.0), PricePoint(price=2812.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        _run(conn)
    row = store.get_alert(conn, alert_id)
    assert row.reality_mismatch is True
    assert row.reality_move_secondary == {"XAUUSD": 12.0}


def test_magnitude_thresholds_removed():
    assert not hasattr(reality_check, "MAGNITUDE_THRESHOLDS")


@pytest.mark.parametrize("baseline,expected", [(2.0, False), (4.0, True)])
def test_mismatch_uses_hourly_baseline(baseline, expected):
    conn = store.get_connection(":memory:")
    alert_id = _seed_alert(conn, "High", "XAUUSD", dt.datetime.now(UTC) - dt.timedelta(days=1))
    prices = [PricePoint(price=2800.0), PricePoint(price=2803.0), PricePoint(price=2803.0)]   # 5-min move 3.0
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        _run(conn, baselines={"XAUUSD": {h: baseline for h in range(24)}})
    assert store.get_alert(conn, alert_id).reality_mismatch is expected


def test_missing_baseline_skips_symbol_not_mismatch_signal():
    conn = store.get_connection(":memory:")
    alert_id = _seed_alert(conn, "High", "XAUUSD", dt.datetime.now(UTC) - dt.timedelta(days=1))
    with patch("alerting.reality_check.get_price_at") as mock_get_price:
        result = _run(conn, baselines={"XAUUSD": {}})
    mock_get_price.assert_not_called()      # no baseline for the hour: skipped before any price fetch
    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is None     # neither a mismatch nor a confirmation
    assert result["no_price_data"] == 1


def test_run_records_one_grading_run_and_summary_line(capsys):
    conn = store.get_connection(":memory:")
    _seed_alert(conn, "High", "XAUUSD", dt.datetime.now(UTC) - dt.timedelta(days=1))
    with patch("alerting.reality_check.get_price_at", return_value=None):
        result = _run(conn)
    rows = conn.execute("SELECT source, summary_line, counts_json FROM shock_grading_runs").fetchall()
    assert len(rows) == 1 and rows[0]["source"] == "weekly"
    assert rows[0]["summary_line"] == result["summary_line"]
    assert json.loads(rows[0]["counts_json"]) == result["grading"]["counts"]
    with patch.object(reality_check, "run_reality_check", return_value=result):
        assert reality_check.main() == 0
    assert f"[lean_grading] {result['summary_line']}" in capsys.readouterr().out


def test_main_exit_code_1_on_fetch_failure(capsys):
    result = {"checked": 0, "mismatches": 0, "no_price_data": 0, "summary_line": "graded 0",
              "grading": {"fetch_failed": {"XAUUSD": "boom"}}}
    with patch.object(reality_check, "run_reality_check", return_value=result):
        assert reality_check.main() == 1
    assert "[reality_check] checked 0" in capsys.readouterr().out


def test_explicit_args_never_touch_default_paths(monkeypatch):
    def boom(*args, **kwargs):
        pytest.fail("a default (live-path) loader was reached")
    monkeypatch.setattr(lean_grading, "load_tracked_symbols", boom)
    monkeypatch.setattr(lean_grading, "load_baselines", boom)
    monkeypatch.setattr(minute_bars, "fetch_bars", boom)
    conn = store.get_connection(":memory:")
    _seed_alert(conn, "High", "XAUUSD", dt.datetime.now(UTC) - dt.timedelta(days=1))
    with patch("alerting.reality_check.get_price_at", return_value=None):
        result = _run(conn, now=dt.datetime.now(UTC))
    assert result["checked"] == 1
