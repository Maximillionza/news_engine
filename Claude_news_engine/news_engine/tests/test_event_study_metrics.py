"""Pure-helper tests for scripts/archive/event_study_metrics.py (synthetic bars only; no network, no DB)."""
import datetime as dt
import math

import pandas as pd
import pytest

from scripts.archive import event_study_metrics as m

UTC = dt.timezone.utc
T = dt.datetime(2026, 3, 12, 12, 30, 0, tzinfo=UTC)

# Reference fixture (plan Task 1): offset s from t -> (open, high, low, close).
REFERENCE = [
    (-2, 4079.0, 4079.2, 4078.8, 4079.1),
    (0, 4080.0, 4081.0, 4079.5, 4080.5),
    (7, 4080.5, 4089.0, 4080.4, 4088.0),
    (40, 4088.0, 4088.5, 4084.0, 4085.0),
    (90, 4085.0, 4090.0, 4083.0, 4084.0),
    (290, 4084.0, 4084.5, 4082.0, 4083.0),
    (600, 4083.0, 4083.0, 4068.0, 4072.0),
    (1790, 4072.0, 4073.0, 4071.0, 4071.5),
    (1850, 4071.5, 4100.0, 4071.0, 4099.0),
]


def _bars(spec: list[tuple], t: dt.datetime = T) -> list[m.Bar]:
    return [m.Bar(t + dt.timedelta(seconds=s), o, h, lo, c) for s, o, h, lo, c in spec]


def _measures(result: dict) -> dict:
    return {k: v for k, v in result.items() if k not in ("status", "bar_source", "resolution_s")}


# ---- measure_window ---------------------------------------------------------------------------

def test_measure_window_reference_fixture():
    r = m.measure_window(_bars(REFERENCE), T, "sec1", 1)
    assert r["status"] == "ok"
    assert r["bar_source"] == "sec1" and r["resolution_s"] == 1
    assert r["p0"] == 4080.0 and r["p0_lag_s"] == 0
    # 1 minute
    assert r["up_1"] == pytest.approx(9.0)
    assert r["down_1"] == pytest.approx(0.5)
    assert r["peak_1"] == pytest.approx(9.0)
    assert r["ttp_1_s"] == 7
    assert r["side_1"] == 1
    assert r["first_min_dir"] == 1
    assert r["first_min_peak"] == pytest.approx(9.0)
    # 5 minutes
    assert r["up_5"] == pytest.approx(10.0)
    assert r["down_5"] == pytest.approx(0.5)
    assert r["peak_5"] == pytest.approx(10.0)
    assert r["ttp_5_s"] == 90
    assert r["side_5"] == 1
    # 30 minutes
    assert r["up_30"] == pytest.approx(10.0)
    assert r["down_30"] == pytest.approx(12.0)
    assert r["peak_30"] == pytest.approx(12.0)
    assert r["side_30"] == -1
    assert r["ttp_30_s"] == 600
    # net, retrace, spike-then-pull-back
    assert r["net_5"] == pytest.approx(3.0)
    assert r["net_30"] == pytest.approx(-8.5)
    assert r["retrace_5"] == pytest.approx(2 / 3)
    assert r["spike_pullback_5"] is True
    assert r["retrace_30"] == pytest.approx(1 + 8.5 / 9)
    assert r["spike_pullback_30"] is True


def test_bars_after_horizon_and_before_t_are_ignored():
    r = m.measure_window(_bars(REFERENCE), T, "sec1", 1)
    p0 = r["p0"]
    for k in m.HORIZONS_MIN:
        # The 4100.0 high at +1850 s would make up_30 = 20.0; the 4078.8 low at -2 s would make
        # down_k = 1.2. Neither may appear.
        assert r[f"up_{k}"] != pytest.approx(4100.0 - p0)
        assert r[f"down_{k}"] != pytest.approx(p0 - 4078.8)
        assert r[f"up_{k}"] <= 10.0 + 1e-9
    assert r["down_1"] == pytest.approx(0.5) and r["down_5"] == pytest.approx(0.5)


def test_measure_window_exact_key_set():
    ok = m.measure_window(_bars(REFERENCE), T, "sec1", 1)
    none = m.measure_window([], T, "none", 0)
    assert set(ok) == set(m.METRIC_KEYS)
    assert set(none) == set(m.METRIC_KEYS)
    assert len(m.METRIC_KEYS) == len(set(m.METRIC_KEYS))


def test_p0_more_than_60s_after_t_is_no_data():
    spec = [(75, 4080.0, 4085.0, 4079.0, 4084.0), (200, 4084.0, 4086.0, 4083.0, 4085.0)]
    r = m.measure_window(_bars(spec), T, "sec1", 1)
    assert r["status"] == "no_data"
    assert r["bar_source"] == "sec1" and r["resolution_s"] == 1
    assert all(v is None for v in _measures(r).values())
    assert m.first_open_at_or_after(_bars(spec), T) is None


def test_net_needs_a_bar_within_120s():
    # Drop the +290 s bar: the last bar before t+5 min is then the +90 s bar (210 s stale).
    spec = [row for row in REFERENCE if row[0] != 290]
    r = m.measure_window(_bars(spec), T, "sec1", 1)
    assert r["status"] == "ok"
    assert r["net_5"] is None
    assert r["retrace_5"] is None
    assert r["spike_pullback_5"] is None
    # The 30-minute net is unaffected (+1790 s bar is 10 s before t+30 min).
    assert r["net_30"] == pytest.approx(-8.5)
    # Exactly 120 s stale is still accepted; 121 s is not.
    bars = _bars([(0, 1.0, 1.0, 1.0, 1.0), (180, 1.0, 1.0, 1.0, 2.0)])
    assert m.close_before(bars, T + dt.timedelta(minutes=5)) == 2.0
    bars = _bars([(0, 1.0, 1.0, 1.0, 1.0), (179, 1.0, 1.0, 1.0, 2.0)])
    assert m.close_before(bars, T + dt.timedelta(minutes=5)) is None


def test_first_minute_tie_has_no_direction():
    spec = [
        (0, 100.0, 101.0, 100.0, 100.5),
        (20, 100.5, 100.5, 99.0, 99.5),
        (200, 99.5, 99.6, 99.4, 99.5),
        (1700, 99.5, 99.6, 99.4, 99.5),
    ]
    r = m.measure_window(_bars(spec), T, "sec1", 1)
    assert r["up_1"] == pytest.approx(1.0) and r["down_1"] == pytest.approx(1.0)
    assert r["side_1"] == 0
    assert r["first_min_dir"] == 0
    assert r["retrace_5"] is None and r["retrace_30"] is None
    assert r["spike_pullback_5"] is None and r["spike_pullback_30"] is None
    # A flat first minute: tie of zeros -> no time to peak.
    flat = _bars([(0, 5.0, 5.0, 5.0, 5.0)])
    assert m.excursion(flat, T, 5.0, 1) == (0.0, 0.0, None, 0)


# ---- choose_bars ------------------------------------------------------------------------------

def test_choose_bars_falls_back_to_minute_bars():
    minute_spec = [
        (0, 4080.0, 4083.0, 4079.0, 4082.0),
        (60, 4082.0, 4090.0, 4081.0, 4088.0),
        (120, 4088.0, 4089.0, 4085.0, 4086.0),
        (1740, 4086.0, 4087.0, 4060.0, 4070.0),
    ]
    min_bars = _bars(minute_spec)
    source, res, chosen = m.choose_bars([], min_bars, T)
    assert (source, res) == ("min1", 60)
    assert chosen == min_bars
    assert m.choose_bars([], [], T) == ("none", 0, [])
    # Second bars good -> second bars win.
    sec_bars = _bars(REFERENCE)
    assert m.choose_bars(sec_bars, min_bars, T)[:2] == ("sec1", 1)
    # Second bars without a 30-minute close -> minute bars win.
    short_sec = _bars(REFERENCE[:5])
    assert m.choose_bars(short_sec, min_bars, T)[:2] == ("min1", 60)
    # Neither passes the 30-minute test -> whichever has p0, seconds first.
    assert m.choose_bars(short_sec, _bars(minute_spec[:2]), T)[:2] == ("sec1", 1)
    assert m.choose_bars([], _bars(minute_spec[:2]), T)[:2] == ("min1", 60)
    # Minute bars: times to peak are whole minutes.
    r = m.measure_window(min_bars, T, "min1", 60)
    for k in m.HORIZONS_MIN:
        if r[f"ttp_{k}_s"] is not None:
            assert r[f"ttp_{k}_s"] % 60 == 0
    assert r["ttp_5_s"] == 60 and r["ttp_30_s"] == 1740


# ---- bars_from_frame --------------------------------------------------------------------------

def test_bars_from_frame_drops_nan_and_rejects_naive_index():
    idx = pd.DatetimeIndex([T + dt.timedelta(seconds=5), T, T + dt.timedelta(seconds=9)])
    df = pd.DataFrame(
        {"open": [2.0, 1.0, 3.0], "high": [2.5, float("nan"), 3.5],
         "low": [1.5, 0.5, 2.5], "close": [2.2, 0.8, 3.2], "volume": [1, 1, 1]},
        index=idx,
    )
    bars = m.bars_from_frame(df)
    assert [b.ts for b in bars] == [T + dt.timedelta(seconds=5), T + dt.timedelta(seconds=9)]
    assert all(b.ts.tzinfo is not None and b.ts.utcoffset() == dt.timedelta(0) for b in bars)
    assert bars[0] == m.Bar(T + dt.timedelta(seconds=5), 2.0, 2.5, 1.5, 2.2)
    assert all(isinstance(b.open, float) and math.isfinite(b.high) for b in bars)
    # Non-UTC aware index is converted to UTC.
    df_sast = df.copy()
    df_sast.index = df.index.tz_convert("Africa/Johannesburg")
    assert [b.ts for b in m.bars_from_frame(df_sast)] == [b.ts for b in bars]
    # Naive index refused; empty frame -> [].
    naive = df.copy()
    naive.index = df.index.tz_localize(None)
    with pytest.raises(ValueError):
        m.bars_from_frame(naive)
    assert m.bars_from_frame(pd.DataFrame(columns=["open", "high", "low", "close"])) == []


# ---- units ------------------------------------------------------------------------------------

def test_owner_units_gold_pips_and_us30_points():
    assert m.owner_units("XAUUSD", 4090.0 - 4080.0) == (1000.0, "pips")
    assert m.owner_units("US30", 25.0) == (25.0, "points")
    assert m.owner_units("DXY", 0.12) == (0.12, "index points")
    with pytest.raises(ValueError):
        m.owner_units("EURUSD", 1.0)


def test_baseline_multiple():
    assert m.baseline_multiple(3.0, 1.5) == 2.0
    assert m.baseline_multiple(3.0, 0.0) is None
    assert m.baseline_multiple(3.0, -1.0) is None
    assert m.baseline_multiple(None, 1.5) is None
    assert m.baseline_multiple(3.0, None) is None
