import datetime as dt

import pytest

from scoring import backtest_store as bs

UTC = dt.timezone.utc
EST = dt.timezone(dt.timedelta(hours=-5))
RELEASE = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
KEY = RELEASE.isoformat()


@pytest.fixture
def conn():
    return bs.get_connection(":memory:")


def _ok(conn, p0=2000.0, p5=2005.0, when=RELEASE, **kw):
    return bs.record_release_reaction(conn, when, "XAUUSD", "ok", p0=p0, p5=p5, **kw)


def test_record_then_get_returns_row_with_derived_move_and_pct(conn):
    row_id = _ok(conn, typical_abs_move=3.0, reaction="buy")
    rows = bs.get_release_reactions(conn, "XAUUSD")
    assert list(rows) == [KEY]
    row = rows[KEY]
    assert row["id"] == row_id
    assert row["status"] == "ok"
    assert row["p0"] == pytest.approx(2000.0)
    assert row["p5"] == pytest.approx(2005.0)
    assert row["move"] == pytest.approx(5.0)
    assert row["move_pct"] == pytest.approx(0.25)
    assert row["typical_abs_move"] == pytest.approx(3.0)
    assert row["reaction"] == "buy"
    assert row["bar_source"] == "dukascopy_1m"
    assert row["computed_at_utc"]


def test_negative_move_is_derived(conn):
    _ok(conn, p0=2000.0, p5=1990.0, reaction="sell")
    row = bs.get_release_reactions(conn, "XAUUSD")[KEY]
    assert row["move"] == pytest.approx(-10.0)
    assert row["move_pct"] == pytest.approx(-0.5)


def test_duplicate_is_ignored_not_overwritten_and_returns_existing_id(conn):
    first = _ok(conn, p5=2005.0)
    second = _ok(conn, p5=2100.0)
    assert second == first
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 1
    assert bs.get_release_reactions(conn, "XAUUSD")[KEY]["p5"] == pytest.approx(2005.0)


def test_same_time_different_instrument_is_a_separate_row(conn):
    a = _ok(conn)
    b = bs.record_release_reaction(conn, RELEASE, "EURUSD", "ok", p0=1.1, p5=1.101)
    assert a != b
    assert list(bs.get_release_reactions(conn, "EURUSD")) == [KEY]


def test_offset_form_time_is_normalised_and_found_under_utc_key(conn):
    _ok(conn, when=dt.datetime(2026, 10, 14, 7, 30, tzinfo=EST))      # == 12:30Z
    rows = bs.get_release_reactions(conn, "XAUUSD")
    assert list(rows) == [KEY]
    # same instant in another offset is a duplicate, not a new row
    _ok(conn, when=RELEASE)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 1


def test_naive_datetime_is_rejected(conn):
    with pytest.raises(ValueError):
        _ok(conn, when=dt.datetime(2026, 10, 14, 12, 30))


def test_invalid_status_and_reaction_are_rejected(conn):
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "maybe", p0=1.0, p5=2.0)
    with pytest.raises(ValueError):
        _ok(conn, reaction="up")
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_ok_row_requires_both_prices_and_nonzero_p0(conn):
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=None, p5=2.0)
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=2.0, p5=None)
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=0.0, p5=2.0)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_no_data_row_stores_null_prices_and_derived_fields(conn):
    row_id = bs.record_release_reaction(conn, RELEASE, "XAUUSD", "no_data", typical_abs_move=2.5)
    row = bs.get_release_reactions(conn, "XAUUSD")[KEY]
    assert row["id"] == row_id
    assert row["status"] == "no_data"
    for col in ("p0", "p5", "move", "move_pct", "reaction"):
        assert row[col] is None
    assert row["typical_abs_move"] == pytest.approx(2.5)


def test_no_data_row_with_prices_or_reaction_is_rejected(conn):
    for kw in ({"p0": 1.0}, {"p5": 2.0}, {"reaction": "buy"}):
        with pytest.raises(ValueError):
            bs.record_release_reaction(conn, RELEASE, "XAUUSD", "no_data", **kw)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["p0", "p5", "typical_abs_move"])
def test_non_finite_reaction_inputs_are_rejected_and_write_nothing(conn, field, bad):
    kw = {"p0": 2000.0, "p5": 2005.0, "typical_abs_move": 3.0}
    kw[field] = bad
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", **kw)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_negative_typical_abs_move_is_rejected(conn):
    with pytest.raises(ValueError):
        _ok(conn, typical_abs_move=-0.1)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_reaction_none_text_is_stored_and_python_none_is_null(conn):
    _ok(conn, reaction="none")
    assert bs.get_release_reactions(conn, "XAUUSD")[KEY]["reaction"] == "none"
    later = dt.datetime(2026, 10, 15, 12, 30, tzinfo=UTC)
    _ok(conn, when=later)
    assert bs.get_release_reactions(conn, "XAUUSD")[later.isoformat()]["reaction"] is None


def test_get_reactions_empty_for_unknown_instrument(conn):
    _ok(conn)
    assert bs.get_release_reactions(conn, "EURUSD") == {}


# ---- baselines ----

P_START = dt.datetime(2026, 1, 1, tzinfo=UTC)
P_END_1 = dt.datetime(2026, 7, 1, tzinfo=UTC)
P_END_2 = dt.datetime(2026, 10, 1, tzinfo=UTC)


def test_latest_period_end_wins_per_hour(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1)
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 3.0, 80, P_START, P_END_2)
    bs.record_reaction_baseline(conn, "XAUUSD", 13, 1.5, 40, P_START, P_END_1)
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD") == {12: 3.0, 13: 1.5}


def test_latest_wins_regardless_of_insert_order(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 3.0, 80, P_START, P_END_2)
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1)
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD") == {12: 3.0}


def test_latest_compared_by_instant_across_offsets(conn):
    # 20:00-05:00 on 09-30 is 01:00Z on 10-01: a later instant than 00:30Z, though its local clock reads earlier.
    later_instant_in_est = dt.datetime(2026, 9, 30, 20, 0, tzinfo=EST)    # == 2026-10-01T01:00Z
    earlier_utc = dt.datetime(2026, 10, 1, 0, 30, tzinfo=UTC)
    bs.record_reaction_baseline(conn, "XAUUSD", 9, 1.0, 10, P_START, earlier_utc)
    bs.record_reaction_baseline(conn, "XAUUSD", 9, 2.0, 10, P_START, later_instant_in_est)
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD") == {9: 2.0}


def test_baseline_duplicate_is_ignored_and_returns_existing_id(conn):
    first = bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1)
    second = bs.record_reaction_baseline(conn, "XAUUSD", 12, 9.9, 99, P_START, P_END_1)
    assert second == first
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 1
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD") == {12: 2.0}


def test_baseline_validation(conn):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 24, 2.0, 5, P_START, P_END_1)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", -1, 2.0, 5, P_START, P_END_1)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, -0.1, 5, P_START, P_END_1)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, -1, P_START, P_END_1)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 5, dt.datetime(2026, 1, 1), P_END_1)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 5, P_START, dt.datetime(2026, 7, 1))
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


def test_baselines_scoped_per_instrument_and_empty_default(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1)
    assert bs.get_latest_reaction_baselines(conn, "EURUSD") == {}


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_median_abs_move_is_rejected_and_writes_nothing(conn, bad):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, bad, 5, P_START, P_END_1)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


@pytest.mark.parametrize("bad_hour", [12.5, True, "12", 12.0])
def test_non_integer_utc_hour_is_rejected(conn, bad_hour):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", bad_hour, 2.0, 5, P_START, P_END_1)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


def test_period_start_after_end_is_rejected_but_equal_is_allowed(conn):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 5, P_END_1, P_START)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 0, P_START, P_START)
