"""
Tests for scripts/news_floor_replay.py -- temp SQLite files only, no network, the live DBs are never opened.
"""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring import backtest_store as bs
from scripts import news_floor_replay as replay_script
from webapp import store as ws

UTC = dt.timezone.utc


def _t(month: int) -> dt.datetime:
    return dt.datetime(2026, month, 14, 12, 30, tzinfo=UTC)


def _event(dash, when, actual, forecast="0.3%"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("CPI m/m", when.isoformat(), forecast, "0.1%", actual, None, when.isoformat(), when.isoformat(), "t", "High", "USD"))
    dash.commit()


def _call(bt, when, probability, signal):
    """A final pre-release accumulator row with `signal` included non-zero evidence articles."""
    pid = bs.record_prediction(bt, "CPI m/m", "XAUUSD", when, probability, "bearish", 0.5, signal, False,
                               scored_at_utc=when - dt.timedelta(days=1))
    rows = [{"title": f"a{i}", "url": f"https://x/{i}", "source": "s", "source_type": "rss",
             "published_utc": when.isoformat(), "status": "included", "reason": None, "usd_sentiment": 0.5,
             "trust_weight": 1.0, "time_weight": 1.0, "combined_weight": 1.0, "weight_pct": 10.0, "matched_terms": []}
            for i in range(signal)]
    if rows:
        bs.record_prediction_article_contributions(bt, pid, "CPI m/m", when, "XAUUSD", rows)


@pytest.fixture
def db_files(tmp_path):
    dash_path, bt_path = tmp_path / "dash.db", tmp_path / "bt.db"
    dash, bt = ws.get_connection(dash_path), bs.get_connection(bt_path)
    for m in (1, 2, 3):                                  # scale history, no News calls (no accumulator rows)
        _event(dash, _t(m), "0.4%")
    _event(dash, _t(4), "0.4%"); _call(bt, _t(4), 0.9, signal=2)     # side, n=2, graded: flips (hotter print, bearish = higher: right)
    _event(dash, _t(5), "0.2%"); _call(bt, _t(5), 0.9, signal=3)     # side, n=3: kept
    _event(dash, _t(6), "0.4%"); _call(bt, _t(6), 0.55, signal=1)    # |lean| 0.1: no side before the floor either
    _event(dash, _t(7), None); _call(bt, _t(7), 0.9, signal=0)       # pending, side, n=0: flips
    dash.close(); bt.close()
    return dash_path, bt_path


def test_replay_lists_flips_only_for_rows_that_had_a_side(db_files):
    dash_path, bt_path = db_files
    dash, bt = replay_script.open_readonly(dash_path), replay_script.open_readonly(bt_path)
    flips = replay_script.replay(dash, bt)["CPI m/m"]
    assert flips.scored_with_side == 2                   # months 4 and 5; month 6 never had a side, month 7 is pending
    assert flips.scored_flipped == 1 and flips.pending_flipped == 1
    assert flips.verdicts["right"] == 1
    assert flips.lower_bound == 0 and flips.unknown_n == 0
    assert sorted(flips.n_values.elements()) == [0, 2]
    report = replay_script.render_report({"CPI m/m": flips}, "bt.db")
    assert "Total: 1 of 2 scored News calls flip" in report and "1 pending rows flip" in report


def test_replay_never_writes_and_missing_db_exits_2(db_files, tmp_path, capsys):
    dash_path, bt_path = db_files
    before = (dash_path.read_bytes(), bt_path.read_bytes())
    assert replay_script.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)]) == 0
    assert (dash_path.read_bytes(), bt_path.read_bytes()) == before
    assert "CPI m/m" in capsys.readouterr().out
    assert replay_script.main(["--dash-db", str(tmp_path / "nope.db"), "--bt-db", str(bt_path)]) == 2
