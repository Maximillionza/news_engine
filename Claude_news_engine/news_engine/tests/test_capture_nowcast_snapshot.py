import datetime as dt

import pytest

from scoring import backtest_store as bs
from scripts.capture_nowcast_snapshot import capture, parse_aware

UTC = dt.timezone.utc
RELEASE = dt.datetime(2026, 11, 12, 13, 30, tzinfo=UTC)


def test_capture_records_a_live_snapshot_before_release():
    conn = bs.get_connection(":memory:")
    capture(conn, "CPI m/m", RELEASE, 0.4, as_of_utc=RELEASE - dt.timedelta(hours=20))
    row = bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)
    assert row["kind"] == "live" and row["nowcast_value"] == pytest.approx(0.4)


def test_capture_refuses_an_as_of_time_after_the_release():
    conn = bs.get_connection(":memory:")
    with pytest.raises(ValueError):
        capture(conn, "CPI m/m", RELEASE, 0.4, as_of_utc=RELEASE + dt.timedelta(minutes=1))


def test_two_captures_keep_both_and_the_later_one_is_scored():
    conn = bs.get_connection(":memory:")
    capture(conn, "CPI m/m", RELEASE, 0.3, as_of_utc=RELEASE - dt.timedelta(days=3))
    capture(conn, "CPI m/m", RELEASE, 0.5, as_of_utc=RELEASE - dt.timedelta(hours=5))
    assert conn.execute("SELECT COUNT(*) FROM tier1_nowcast_snapshots").fetchone()[0] == 2
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)["nowcast_value"] == pytest.approx(0.5)


def test_capture_rejects_a_naive_release_with_value_error():
    conn = bs.get_connection(":memory:")
    naive_release = dt.datetime(2026, 11, 12, 13, 30)
    with pytest.raises(ValueError):
        capture(conn, "CPI m/m", naive_release, 0.4, as_of_utc=dt.datetime(2026, 11, 11, 17, 30, tzinfo=UTC))


def test_capture_rejects_a_naive_as_of_with_value_error():
    conn = bs.get_connection(":memory:")
    naive_as_of = dt.datetime(2026, 11, 11, 17, 30)
    with pytest.raises(ValueError):
        capture(conn, "CPI m/m", RELEASE, 0.4, as_of_utc=naive_as_of)


def test_parse_aware_accepts_an_offset_and_rejects_a_naive_timestamp():
    parsed = parse_aware("2026-11-12T13:30:00+00:00")
    assert parsed.utcoffset() == dt.timedelta(0)
    with pytest.raises(ValueError, match="UTC offset"):
        parse_aware("2026-11-12T13:30:00")
