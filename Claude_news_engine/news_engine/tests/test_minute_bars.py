"""
Tests for data_layer/minute_bars.py (B10 C4: the Dukascopy 1-minute fetch/cache and the bar/baseline helpers
moved out of the one-off scripts/market_reaction_phase0.py).

The parity test is a characterization test: its golden was written on the code BEFORE the move, so it proves
the hourly reaction job (scripts/compute_release_reactions.py) produces byte-identical output afterwards.
Synthetic bars and tmp DBs only: no network, never the live DBs.

Regenerate the golden (only on code whose reaction-job behaviour you intend to define):
    python tests/test_minute_bars.py --write-golden
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:                      # `python tests/test_minute_bars.py` has tests/ on sys.path, not the app dir
    sys.path.insert(0, str(APP))

from scoring import backtest_store as bs  # noqa: E402
from scripts import compute_release_reactions as crr  # noqa: E402
from webapp import store as ws  # noqa: E402

UTC = dt.timezone.utc
GOLDEN = APP / "tests" / "fixtures" / "b10_reaction_parity_golden.json"
SINCE = dt.datetime(2026, 1, 1, tzinfo=UTC)
NOW = dt.datetime(2026, 3, 4, 9, 0, tzinfo=UTC)


def _t(day: int, hour: int, minute: int) -> dt.datetime:
    return dt.datetime(2026, 3, day, hour, minute, tzinfo=UTC)


# ---- reaction-job parity ---------------------------------------------------------------------

def _ramp(day: int, step: float, base: float) -> dict:
    """One bar per minute 12:00-14:10, open rising by `step` per minute."""
    first = _t(day, 12, 0)
    return {first + dt.timedelta(minutes=i): base + step * i for i in range(131)}


def _synthetic_bars() -> dict:
    """Mon-Wed ramps per symbol; XAUUSD jumps after the Tue 12:30 release; US30 lacks the Tue 13:35 bar."""
    bars: dict = {"XAUUSD": {}, "US30": {}}
    for day in (2, 3, 4):
        bars["XAUUSD"].update(_ramp(day, 0.1, 2000.0 + day))
        bars["US30"].update(_ramp(day, 1.5, 40000.0 + day))
    bars["XAUUSD"][_t(3, 12, 35)] = bars["XAUUSD"][_t(3, 12, 30)] + 5.0
    bars["US30"][_t(3, 12, 35)] = bars["US30"][_t(3, 12, 30)] - 90.0
    del bars["US30"][_t(3, 13, 35)]
    return bars


def _snapshot(tmp_path: Path) -> dict:
    dash = ws.get_connection(tmp_path / "dash.db")
    for title, when, country in (
        ("CPI m/m", _t(3, 12, 30), "USD"),
        ("CPI m/m", _t(3, 12, 32), "USD"),            # same-title duplicate 2 minutes later: collapses
        ("ISM Services PMI", _t(3, 13, 30), "USD"),
        ("Retail Sales m/m", _t(7, 13, 30), "USD"),   # Saturday, after NOW: future, never judged
        ("German Ifo", _t(3, 12, 45), "EUR"),         # non-USD: ignored
    ):
        ws.insert_event_history_if_absent(dash, title, when, None, None, None, None, "t", "High", country, NOW)
    bars = _synthetic_bars()

    def fake_fetch(symbol, start, end):
        return dict(bars[symbol])

    bt = bs.get_connection(tmp_path / "bt.db")
    backfill = crr.run(dash, bt, fake_fetch, "backfill", now=NOW, symbols=["US30", "XAUUSD"], since=SINCE)
    incremental = crr.run(dash, bt, fake_fetch, "incremental", now=NOW, symbols=["US30", "XAUUSD"], since=SINCE,
                          refresh_baselines=True)
    reactions = [dict(r) for r in bt.execute(
        "SELECT event_time_utc, instrument, status, p0, p5, move, move_pct, typical_abs_move, reaction, "
        "baseline_quantile, reaction_multiple, bar_source FROM release_reactions "
        "ORDER BY instrument, event_time_utc")]
    baselines = [dict(r) for r in bt.execute(
        "SELECT instrument, utc_hour, baseline_abs_move, n_windows, period_start_utc, period_end_utc, quantile "
        "FROM reaction_baselines ORDER BY instrument, utc_hour, period_end_utc")]
    dash.close()
    bt.close()
    return json.loads(json.dumps({"backfill": backfill, "incremental": incremental,
                                  "release_reactions": reactions, "reaction_baselines": baselines},
                                 sort_keys=True))


def test_reaction_job_output_unchanged_by_c4(tmp_path):
    snap = _snapshot(tmp_path)
    assert snap["release_reactions"], "scenario must produce reaction rows"
    assert snap == json.loads(GOLDEN.read_text(encoding="utf-8"))


# ---- shared-module contract -------------------------------------------------------------------

def test_cache_dir_unchanged():
    from data_layer import minute_bars
    # Same directory as the old script, so the month pickles already on disk are reused.
    assert minute_bars.CACHE_DIR == Path(tempfile.gettempdir()) / "market_reaction_phase0_cache"
    assert minute_bars.WINDOW_MIN == 5


def test_crr_uses_shared_helpers():
    from data_layer import minute_bars
    assert crr.default_fetch_bars is minute_bars.fetch_bars
    assert crr.quantile is minute_bars.quantile
    assert crr.to_opens is minute_bars.to_opens
    assert crr.price_at_minute is minute_bars.price_at_minute
    assert crr.WINDOW == dt.timedelta(minutes=minute_bars.WINDOW_MIN)
    source = (APP / "scripts" / "compute_release_reactions.py").read_text(encoding="utf-8")
    assert "market_reaction_phase0" not in source


def test_phase0_imports_the_moved_helpers_back():
    from data_layer import minute_bars
    from scripts.archive import market_reaction_phase0 as phase0
    assert phase0.fetch_bars is minute_bars.fetch_bars
    assert phase0.spec_baseline_moves is minute_bars.spec_baseline_moves
    assert phase0.read_usd_events is minute_bars.read_usd_events
    assert phase0._parse_utc is minute_bars.parse_utc


def test_parse_utc_naive_is_utc():
    from data_layer import minute_bars
    assert minute_bars.parse_utc("2026-03-02T12:30:00") == _t(2, 12, 30)
    assert minute_bars.parse_utc("2026-03-02T14:30:00+02:00") == _t(2, 12, 30)
    assert minute_bars.parse_utc("2026-03-02T14:30:00+02:00").utcoffset() == dt.timedelta(0)


def test_aware_utc_refuses_naive():
    from data_layer import minute_bars
    with pytest.raises(ValueError):
        minute_bars.aware_utc(dt.datetime(2026, 3, 2, 12, 0), "x")
    assert minute_bars.aware_utc(_t(2, 12, 0), "x") == _t(2, 12, 0)


def test_month_chunks_split_on_calendar_months():
    from data_layer import minute_bars
    chunks = minute_bars.month_chunks(dt.datetime(2026, 11, 20, tzinfo=UTC), dt.datetime(2027, 1, 5, tzinfo=UTC))
    assert chunks == [(dt.datetime(2026, 11, 1, tzinfo=UTC), dt.datetime(2026, 12, 1, tzinfo=UTC)),
                      (dt.datetime(2026, 12, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC)),
                      (dt.datetime(2027, 1, 1, tzinfo=UTC), dt.datetime(2027, 2, 1, tzinfo=UTC))]


def test_fetch_bars_caches_completed_months_only(tmp_path, monkeypatch):
    import types

    import pandas as pd

    from data_layer import dukascopy_feed, minute_bars

    calls: list = []

    def fake_fetch(instrument, interval, side, lo, hi):
        calls.append((lo, hi))
        index = pd.DatetimeIndex([lo + dt.timedelta(minutes=i) for i in range(3)], tz="UTC")
        return pd.DataFrame({"open": [1.0, 2.0, 3.0]}, index=index)

    fake_dk = types.SimpleNamespace(fetch=fake_fetch, INTERVAL_MIN_1="1m", OFFER_SIDE_BID="bid")
    monkeypatch.setitem(sys.modules, "dukascopy_python", fake_dk)
    monkeypatch.setattr(dukascopy_feed, "_resolve_dukascopy_instrument", lambda symbol: "INSTR")
    monkeypatch.setattr(minute_bars, "CACHE_DIR", tmp_path / "cache")

    done_start, done_end = dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 2, 1, tzinfo=UTC)
    first = minute_bars.fetch_bars("XAUUSD", done_start, done_end, pause_s=0)
    assert len(first) == 3 and len(calls) == 1
    assert len(list((tmp_path / "cache").glob("*.pkl"))) == 1
    second = minute_bars.fetch_bars("XAUUSD", done_start, done_end, pause_s=0)
    assert second == first and len(calls) == 1             # served from the pickle

    calls.clear()
    now = dt.datetime.now(UTC)
    current = dt.datetime(now.year, now.month, 1, tzinfo=UTC)
    minute_bars.fetch_bars("XAUUSD", current, now, pause_s=0)
    minute_bars.fetch_bars("XAUUSD", current, now, pause_s=0)
    assert len(calls) == 2                                  # the running month is never cached
    assert len(list((tmp_path / "cache").glob("*.pkl"))) == 1


# ---- spec baseline helpers (moved from test_market_reaction_phase0.py) -------------------------

def _flat_day(day: int, hour: int, step_value: float) -> dict:
    """One bar per minute for the hour (plus the next 5), open rising by step_value per minute."""
    return {_t(day, hour, 0) + dt.timedelta(minutes=i): 100.0 + step_value * i for i in range(66)}


def test_spec_baseline_excludes_release_windows_and_weekends():
    from data_layer import minute_bars
    opens = _flat_day(2, 12, 1.0)               # Mon 2026-03-02: every 5-min move = 5.0
    opens.update(_flat_day(7, 12, 9.0))         # Sat 2026-03-07: must be ignored
    opens[_t(2, 12, 30)] = 1000.0     # distorts the 12:25 window (875) and the 12:30 window (865)
    moves_all = minute_bars.spec_baseline_moves(opens, 12, set())
    moves_ex = minute_bars.spec_baseline_moves(opens, 12, {_t(2, 12, 30)})
    assert len(moves_all) == 12 and len(moves_ex) == 11
    assert 865.0 in moves_all and 865.0 not in moves_ex   # the release-minute window is dropped...
    assert 875.0 in moves_ex                              # ...but only that one (its neighbour starts at 12:25)
    assert sorted(moves_ex)[len(moves_ex) // 2] == 5.0


def test_spec_baseline_skips_windows_with_a_missing_bar():
    from data_layer import minute_bars
    opens = _flat_day(2, 12, 1.0)
    del opens[_t(2, 12, 15)]                     # kills the 12:10 (t+5) and 12:15 (t) windows
    assert len(minute_bars.spec_baseline_moves(opens, 12, set())) == 10


def test_spec_baseline_grid_limits_start_minutes():
    from data_layer import minute_bars
    opens = _flat_day(2, 12, 1.0)
    assert len(minute_bars.spec_baseline_moves(opens, 12, set(), grid=(0, 15, 30, 45))) == 4


if __name__ == "__main__":
    if "--write-golden" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            data = _snapshot(Path(tmp))
        GOLDEN.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {GOLDEN} ({len(data['release_reactions'])} reaction rows, "
              f"{len(data['reaction_baselines'])} baseline rows)")
    else:
        raise SystemExit(pytest.main([__file__, "-q", "-p", "no:warnings"]))
