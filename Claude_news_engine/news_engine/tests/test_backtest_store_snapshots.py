import datetime as dt

import pytest

from scoring import backtest_store as bs

UTC = dt.timezone.utc
RELEASE = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)


@pytest.fixture
def conn():
    return bs.get_connection(":memory:")


def _rec(conn, value, as_of, kind="live", **kw):
    return bs.record_nowcast_snapshot(conn, "CPI m/m", RELEASE, value, as_of, "cleveland", kind, **kw)


def test_scored_snapshot_is_the_latest_one_before_release(conn):
    _rec(conn, 0.30, dt.datetime(2026, 10, 12, 6, 6, tzinfo=UTC))
    _rec(conn, 0.40, dt.datetime(2026, 10, 14, 6, 0, tzinfo=UTC))
    row = bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)
    assert row["nowcast_value"] == pytest.approx(0.40)


def test_a_snapshot_dated_after_the_release_is_never_scored(conn):
    _rec(conn, 0.30, dt.datetime(2026, 10, 12, 6, 6, tzinfo=UTC))
    _rec(conn, 0.99, dt.datetime(2026, 10, 14, 13, 0, tzinfo=UTC))   # after 12:30 release: lookahead
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)["nowcast_value"] == pytest.approx(0.30)


def test_live_is_preferred_over_reconstructed_for_the_same_release(conn):
    _rec(conn, 0.50, dt.datetime(2026, 10, 14, 6, 0, tzinfo=UTC), kind="reconstructed", rule_version="v1")
    _rec(conn, 0.40, dt.datetime(2026, 10, 13, 6, 0, tzinfo=UTC), kind="live")
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)["kind"] == "live"


def test_no_snapshot_is_none_and_bad_kind_is_rejected(conn):
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE) is None
    with pytest.raises(ValueError):
        _rec(conn, 0.4, dt.datetime(2026, 10, 14, tzinfo=UTC), kind="guess")


def test_snapshots_are_append_only_a_duplicate_is_ignored_not_overwritten(conn):
    as_of = dt.datetime(2026, 10, 14, 6, 0, tzinfo=UTC)
    _rec(conn, 0.40, as_of)
    _rec(conn, 0.99, as_of)
    assert conn.execute("SELECT COUNT(*) FROM tier1_nowcast_snapshots").fetchone()[0] == 1
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)["nowcast_value"] == pytest.approx(0.40)


NAIVE = dt.datetime(2026, 10, 14, 6, 0)
EST = dt.timezone(dt.timedelta(hours=-5))


def test_naive_datetimes_are_rejected_on_record_and_on_get(conn):
    with pytest.raises(ValueError):
        _rec(conn, 0.4, NAIVE)                                             # naive as_of
    with pytest.raises(ValueError):
        bs.record_nowcast_snapshot(conn, "CPI m/m", NAIVE, 0.4, dt.datetime(2026, 10, 14, 6, 0, tzinfo=UTC),
                                   "cleveland", "live")                    # naive event time
    with pytest.raises(ValueError):
        bs.get_scored_nowcast_snapshot(conn, "CPI m/m", dt.datetime(2026, 10, 14, 12, 30))


def test_non_utc_offset_is_compared_as_an_instant_not_as_a_string(conn):
    # 08:00-05:00 is 13:00Z, AFTER the 12:30Z release: must not leak in as lookahead.
    _rec(conn, 0.99, dt.datetime(2026, 10, 14, 8, 0, tzinfo=EST))
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE) is None
    # 06:00-05:00 is 11:00Z, before release: scored, and stored normalised to UTC.
    _rec(conn, 0.40, dt.datetime(2026, 10, 14, 6, 0, tzinfo=EST))
    row = bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)
    assert row["nowcast_value"] == pytest.approx(0.40)
    assert row["as_of_utc"] == dt.datetime(2026, 10, 14, 11, 0, tzinfo=UTC).isoformat()


def test_release_time_in_another_offset_matches_the_same_release(conn):
    _rec(conn, 0.40, dt.datetime(2026, 10, 14, 6, 0, tzinfo=UTC))
    release_est = dt.datetime(2026, 10, 14, 7, 30, tzinfo=EST)             # == 12:30Z
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", release_est)["nowcast_value"] == pytest.approx(0.40)


def test_snapshot_exactly_at_release_time_is_scored(conn):
    _rec(conn, 0.40, RELEASE)
    assert bs.get_scored_nowcast_snapshot(conn, "CPI m/m", RELEASE)["nowcast_value"] == pytest.approx(0.40)
