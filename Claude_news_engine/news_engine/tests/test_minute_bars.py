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


if __name__ == "__main__":
    if "--write-golden" in sys.argv:
        with tempfile.TemporaryDirectory() as tmp:
            data = _snapshot(Path(tmp))
        GOLDEN.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {GOLDEN} ({len(data['release_reactions'])} reaction rows, "
              f"{len(data['reaction_baselines'])} baseline rows)")
    else:
        raise SystemExit(pytest.main([__file__, "-q", "-p", "no:warnings"]))
