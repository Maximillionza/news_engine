import datetime as dt

import pytest

from scoring import backtest_store as bs

UTC = dt.timezone.utc
EST = dt.timezone(dt.timedelta(hours=-5))
RELEASE = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
KEY = RELEASE.isoformat()
V05 = {"baseline_quantile": 0.5, "reaction_multiple": 1.0}     # the version args are required (no defaults)


@pytest.fixture
def conn():
    return bs.get_connection(":memory:")


def _ok(conn, p0=2000.0, p5=2005.0, when=RELEASE, **kw):
    kw = {**V05, **kw}
    return bs.record_release_reaction(conn, when, "XAUUSD", "ok", p0=p0, p5=p5, **kw)


def test_record_then_get_returns_row_with_derived_move_and_pct(conn):
    row_id = _ok(conn, typical_abs_move=3.0, reaction="buy")
    rows = bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)
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
    row = bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)[KEY]
    assert row["move"] == pytest.approx(-10.0)
    assert row["move_pct"] == pytest.approx(-0.5)


def test_duplicate_is_ignored_not_overwritten_and_returns_existing_id(conn):
    first = _ok(conn, p5=2005.0)
    second = _ok(conn, p5=2100.0)
    assert second == first
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 1
    assert bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)[KEY]["p5"] == pytest.approx(2005.0)


def test_same_time_different_instrument_is_a_separate_row(conn):
    a = _ok(conn)
    b = bs.record_release_reaction(conn, RELEASE, "EURUSD", "ok", p0=1.1, p5=1.101, baseline_quantile=0.5, reaction_multiple=1.0)
    assert a != b
    assert list(bs.get_release_reactions(conn, "EURUSD", 0.5, 1.0)) == [KEY]


def test_offset_form_time_is_normalised_and_found_under_utc_key(conn):
    _ok(conn, when=dt.datetime(2026, 10, 14, 7, 30, tzinfo=EST))      # == 12:30Z
    rows = bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)
    assert list(rows) == [KEY]
    # same instant in another offset is a duplicate, not a new row
    _ok(conn, when=RELEASE)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 1


def test_naive_datetime_is_rejected(conn):
    with pytest.raises(ValueError):
        _ok(conn, when=dt.datetime(2026, 10, 14, 12, 30))


def test_invalid_status_and_reaction_are_rejected(conn):
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "maybe", p0=1.0, p5=2.0, baseline_quantile=0.5, reaction_multiple=1.0)
    with pytest.raises(ValueError):
        _ok(conn, reaction="up")
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_ok_row_requires_both_prices_and_nonzero_p0(conn):
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=None, p5=2.0, baseline_quantile=0.5, reaction_multiple=1.0)
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=2.0, p5=None, baseline_quantile=0.5, reaction_multiple=1.0)
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=0.0, p5=2.0, baseline_quantile=0.5, reaction_multiple=1.0)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_no_data_row_stores_null_prices_and_derived_fields(conn):
    row_id = bs.record_release_reaction(conn, RELEASE, "XAUUSD", "no_data", typical_abs_move=2.5, baseline_quantile=0.5, reaction_multiple=1.0)
    row = bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)[KEY]
    assert row["id"] == row_id
    assert row["status"] == "no_data"
    for col in ("p0", "p5", "move", "move_pct", "reaction"):
        assert row[col] is None
    assert row["typical_abs_move"] == pytest.approx(2.5)


def test_no_data_row_with_prices_or_reaction_is_rejected(conn):
    for kw in ({"p0": 1.0}, {"p5": 2.0}, {"reaction": "buy"}):
        with pytest.raises(ValueError):
            bs.record_release_reaction(conn, RELEASE, "XAUUSD", "no_data", **kw, **V05)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["p0", "p5", "typical_abs_move"])
def test_non_finite_reaction_inputs_are_rejected_and_write_nothing(conn, field, bad):
    kw = {"p0": 2000.0, "p5": 2005.0, "typical_abs_move": 3.0}
    kw[field] = bad
    with pytest.raises(ValueError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", **kw, **V05)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_negative_typical_abs_move_is_rejected(conn):
    with pytest.raises(ValueError):
        _ok(conn, typical_abs_move=-0.1)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_reaction_none_text_is_stored_and_python_none_is_null(conn):
    _ok(conn, reaction="none")
    assert bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)[KEY]["reaction"] == "none"
    later = dt.datetime(2026, 10, 15, 12, 30, tzinfo=UTC)
    _ok(conn, when=later)
    assert bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)[later.isoformat()]["reaction"] is None


def test_get_reactions_empty_for_unknown_instrument(conn):
    _ok(conn)
    assert bs.get_release_reactions(conn, "EURUSD", 0.5, 1.0) == {}


# ---- baselines ----

P_START = dt.datetime(2026, 1, 1, tzinfo=UTC)
P_END_1 = dt.datetime(2026, 7, 1, tzinfo=UTC)
P_END_2 = dt.datetime(2026, 10, 1, tzinfo=UTC)


def test_latest_period_end_wins_per_hour(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1, quantile=0.5)
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 3.0, 80, P_START, P_END_2, quantile=0.5)
    bs.record_reaction_baseline(conn, "XAUUSD", 13, 1.5, 40, P_START, P_END_1, quantile=0.5)
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD", 0.5) == {12: 3.0, 13: 1.5}


def test_latest_wins_regardless_of_insert_order(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 3.0, 80, P_START, P_END_2, quantile=0.5)
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1, quantile=0.5)
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD", 0.5) == {12: 3.0}


def test_latest_compared_by_instant_across_offsets(conn):
    # 20:00-05:00 on 09-30 is 01:00Z on 10-01: a later instant than 00:30Z, though its local clock reads earlier.
    later_instant_in_est = dt.datetime(2026, 9, 30, 20, 0, tzinfo=EST)    # == 2026-10-01T01:00Z
    earlier_utc = dt.datetime(2026, 10, 1, 0, 30, tzinfo=UTC)
    bs.record_reaction_baseline(conn, "XAUUSD", 9, 1.0, 10, P_START, earlier_utc, quantile=0.5)
    bs.record_reaction_baseline(conn, "XAUUSD", 9, 2.0, 10, P_START, later_instant_in_est, quantile=0.5)
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD", 0.5) == {9: 2.0}


def test_baseline_duplicate_is_ignored_and_returns_existing_id(conn):
    first = bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1, quantile=0.5)
    second = bs.record_reaction_baseline(conn, "XAUUSD", 12, 9.9, 99, P_START, P_END_1, quantile=0.5)
    assert second == first
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 1
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD", 0.5) == {12: 2.0}


def test_baseline_validation(conn):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 24, 2.0, 5, P_START, P_END_1, quantile=0.5)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", -1, 2.0, 5, P_START, P_END_1, quantile=0.5)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, -0.1, 5, P_START, P_END_1, quantile=0.5)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, -1, P_START, P_END_1, quantile=0.5)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 5, dt.datetime(2026, 1, 1), P_END_1, quantile=0.5)
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 5, P_START, dt.datetime(2026, 7, 1), quantile=0.5)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


def test_baselines_scoped_per_instrument_and_empty_default(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1, quantile=0.5)
    assert bs.get_latest_reaction_baselines(conn, "EURUSD", 0.5) == {}


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_baseline_abs_move_is_rejected_and_writes_nothing(conn, bad):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, bad, 5, P_START, P_END_1, quantile=0.5)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


@pytest.mark.parametrize("bad_hour", [12.5, True, "12", 12.0])
def test_non_integer_utc_hour_is_rejected(conn, bad_hour):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", bad_hour, 2.0, 5, P_START, P_END_1, quantile=0.5)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


def test_period_start_after_end_is_rejected_but_equal_is_allowed(conn):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 5, P_END_1, P_START, quantile=0.5)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 0, P_START, P_START, quantile=0.5)


# ---- versioning by baseline quantile (owner ruling 2026-10-16: 75th percentile) ----

def test_reaction_row_stores_its_quantile_and_multiple(conn):
    _ok(conn)
    _ok(conn, when=dt.datetime(2026, 10, 15, 12, 30, tzinfo=UTC), baseline_quantile=0.75, reaction_multiple=1.5)
    old = bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)[KEY]
    assert (old["baseline_quantile"], old["reaction_multiple"]) == (0.5, 1.0)
    new = bs.get_release_reactions(conn, "XAUUSD", 0.75, 1.5)["2026-10-15T12:30:00+00:00"]
    assert (new["baseline_quantile"], new["reaction_multiple"]) == (0.75, 1.5)


def test_a_row_under_quantile_0_5_does_not_block_a_row_under_0_75(conn):
    first = _ok(conn, p5=2005.0)
    second = _ok(conn, p5=2009.0, baseline_quantile=0.75)
    assert first != second
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 2
    assert bs.get_release_reactions(conn, "XAUUSD", 0.5, 1.0)[KEY]["p5"] == pytest.approx(2005.0)
    assert bs.get_release_reactions(conn, "XAUUSD", 0.75, 1.0)[KEY]["p5"] == pytest.approx(2009.0)
    assert _ok(conn, p5=2100.0, baseline_quantile=0.75) == second          # still idempotent per quantile


def test_reaction_getter_never_mixes_quantiles(conn):
    _ok(conn)
    assert bs.get_release_reactions(conn, "XAUUSD", 0.75, 1.0) == {}


@pytest.mark.parametrize("kw", [
    {"baseline_quantile": 0.0}, {"baseline_quantile": 1.0}, {"baseline_quantile": float("nan")},
    {"baseline_quantile": -0.25}, {"reaction_multiple": 0.0}, {"reaction_multiple": -1.0},
    {"reaction_multiple": float("inf")},
])
def test_invalid_quantile_or_multiple_is_rejected_and_writes_nothing(conn, kw):
    with pytest.raises(ValueError):
        _ok(conn, **kw)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_baseline_rows_are_versioned_by_quantile(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1, quantile=0.5)
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 3.5, 50, P_START, P_END_1, quantile=0.75)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 2
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD", 0.5) == {12: 2.0}
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD", 0.75) == {12: 3.5}


def test_baseline_getter_never_mixes_quantiles_even_when_the_other_is_newer(conn):
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_2, quantile=0.5)            # newer, but 0.5
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 3.5, 50, P_START, P_END_1, quantile=0.75)
    assert bs.get_latest_reaction_baselines(conn, "XAUUSD", 0.75) == {12: 3.5}


@pytest.mark.parametrize("bad", [0.0, 1.0, 1.5, -0.1, float("nan"), float("inf")])
def test_invalid_baseline_quantile_is_rejected(conn, bad):
    with pytest.raises(ValueError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 5, P_START, P_END_1, quantile=bad)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


def test_getters_require_the_quantile_argument(conn):
    with pytest.raises(TypeError):
        bs.get_release_reactions(conn, "XAUUSD")
    with pytest.raises(TypeError):
        bs.get_release_reactions(conn, "XAUUSD", 0.75)          # the multiple is required too
    with pytest.raises(TypeError):
        bs.get_latest_reaction_baselines(conn, "XAUUSD")


# ---- hardening: version args are required, column named for what it holds ----

def test_record_reaction_without_version_args_fails_loudly(conn):
    with pytest.raises(TypeError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=1.0, p5=2.0)
    with pytest.raises(TypeError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=1.0, p5=2.0, baseline_quantile=0.75)
    with pytest.raises(TypeError):
        bs.record_release_reaction(conn, RELEASE, "XAUUSD", "ok", p0=1.0, p5=2.0, reaction_multiple=1.0)
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 0


def test_record_baseline_without_quantile_fails_loudly(conn):
    with pytest.raises(TypeError):
        bs.record_reaction_baseline(conn, "XAUUSD", 12, 2.0, 50, P_START, P_END_1)
    assert conn.execute("SELECT COUNT(*) FROM reaction_baselines").fetchone()[0] == 0


def test_baseline_column_is_named_baseline_abs_move(conn):
    columns = {r[1] for r in conn.execute("PRAGMA table_info(reaction_baselines)")}
    assert "baseline_abs_move" in columns and "median_abs_move" not in columns
    bs.record_reaction_baseline(conn, "XAUUSD", 12, 4.5, 50, P_START, P_END_1, quantile=0.75)
    assert conn.execute("SELECT baseline_abs_move FROM reaction_baselines").fetchone()[0] == 4.5


# ---- versioning by reaction multiple (final fix wave A) ----

def test_a_row_at_multiple_1_never_blocks_or_mixes_with_one_at_1_5(conn):
    at_1 = _ok(conn, p5=2005.0, baseline_quantile=0.75, reaction_multiple=1.0, reaction="buy")
    at_15 = _ok(conn, p5=2005.0, baseline_quantile=0.75, reaction_multiple=1.5, reaction="none")
    assert at_1 != at_15
    assert conn.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 2
    assert bs.get_release_reactions(conn, "XAUUSD", 0.75, 1.0)[KEY]["reaction"] == "buy"
    assert bs.get_release_reactions(conn, "XAUUSD", 0.75, 1.5)[KEY]["reaction"] == "none"
    assert bs.get_release_reactions(conn, "XAUUSD", 0.75, 2.0) == {}
    # still idempotent per (quantile, multiple), and the returned id is that version's row
    assert _ok(conn, p5=2100.0, baseline_quantile=0.75, reaction_multiple=1.5) == at_15
    assert _ok(conn, p5=2100.0, baseline_quantile=0.75, reaction_multiple=1.0) == at_1


def test_version_columns_have_no_default_so_a_raw_insert_without_them_fails(conn):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO release_reactions (event_time_utc, instrument, status, reaction_multiple, "
                     "bar_source, computed_at_utc) VALUES (?,?,?,?,?,?)", (KEY, "XAUUSD", "no_data", 1.0, "t", KEY))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO release_reactions (event_time_utc, instrument, status, baseline_quantile, "
                     "bar_source, computed_at_utc) VALUES (?,?,?,?,?,?)", (KEY, "XAUUSD", "no_data", 0.75, "t", KEY))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO reaction_baselines (instrument, utc_hour, baseline_abs_move, n_windows, "
                     "period_start_utc, period_end_utc, computed_at_utc) VALUES (?,?,?,?,?,?,?)",
                     ("XAUUSD", 12, 1.0, 5, KEY, KEY, KEY))
    columns = {r[1]: r[4] for r in conn.execute("PRAGMA table_info(release_reactions)")}
    assert columns["baseline_quantile"] is None and columns["reaction_multiple"] is None      # no DEFAULT
    assert {r[1]: r[4] for r in conn.execute("PRAGMA table_info(reaction_baselines)")}["quantile"] is None
