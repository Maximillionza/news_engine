"""
Tests for scripts/capture_tier1.py (B12 T10): the Windows Tier 1 task runs the Cleveland formula phase, then the
Kalshi market-implied phase. No network: both fetchers are injected; databases live under tmp_path.
"""
import datetime as dt

from data_layer.kalshi_feed import KalshiFetchError, KalshiLadder, KalshiStrike
from data_layer.tier1_events import TIER1_MARKET_IMPLIED, TIER1_MARKET_IMPLIED_SOURCE, tier1_titles
from scoring import backtest_store as bs
from scripts import capture_tier1 as ct
from scripts import tier1_research
from tests.test_capture_nowcast_from_cleveland import PCE_MONTH
from tests.test_tier1_market import GDP, PAYROLLS, RETAIL
from webapp import stats_service as svc
from webapp import store as ws
from webapp.tier1_market import MARKET_SERIES

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 28, 5, 0, tzinfo=UTC)
PCE_RELEASE = dt.datetime(2026, 10, 29, 12, 30, tzinfo=UTC)
GDP_RELEASE = dt.datetime(2026, 10, 29, 12, 30, tzinfo=UTC)
NFP_RELEASE = dt.datetime(2026, 11, 6, 13, 30, tzinfo=UTC)
RETAIL_RELEASE = dt.datetime(2026, 11, 17, 13, 30, tzinfo=UTC)
FED_RELEASE = dt.datetime(2026, 12, 9, 19, 0, tzinfo=UTC)
# Live-shaped KXFED-26DEC: a priced hike (P(>4.00) = 0.81, P(>4.25) = 0.085) -> discrete median 4.25.
FED = KalshiLadder("KXFED-26DEC", tuple(KalshiStrike(s, p, p, 500.0) for s, p in
                                        ((3.75, 0.975), (4.0, 0.81), (4.25, 0.085), (4.5, 0.03))))
LADDERS = {"KXGDP": GDP, "KXPAYROLLS": PAYROLLS, "KXUSRETAIL": RETAIL, "KXFED": FED}


def _event(dash, title, when, forecast):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, None, None, None, when.isoformat(), when.isoformat(), "t", "High", "USD"))
    dash.commit()


def _setup(tmp_path, events):
    """Returns (dash_path, bt_path); XAUUSD and US30 tracked; events = [(title, release, forecast)]."""
    dash_path, bt_path = tmp_path / "dash.db", tmp_path / "bt.db"
    dash = ws.get_connection(str(dash_path))
    for symbol in ("XAUUSD", "US30"):
        ws.add_tracked_symbol(dash, symbol)
    for title, when, forecast in events:
        _event(dash, title, when, forecast)
    dash.close()
    return dash_path, bt_path


def _args(paths, *extra, window="192"):
    return [*extra, "--window-hours", window, "--dash-db", str(paths[0]), "--bt-db", str(paths[1])]


def _ladder_fetch(calls=None):
    def fetch(series_ticker, ticketing, release):
        if calls is not None:
            calls.append((series_ticker, ticketing, release))
        return LADDERS.get(series_ticker)
    return fetch


def _cleveland(key):
    return PCE_MONTH


def _rows(bt_path, title=None):
    conn = bs.get_connection(bt_path)
    try:
        sql, params = "SELECT * FROM tier1_predictions", ()
        if title is not None:
            sql, params = sql + " WHERE event_title = ?", (title,)
        return conn.execute(sql + " ORDER BY instrument, id", params).fetchall()
    finally:
        conn.close()


def test_market_series_cover_exactly_the_market_implied_titles():
    assert set(MARKET_SERIES) == set(tier1_titles(TIER1_MARKET_IMPLIED))


def test_dry_run_lists_both_tiers_and_creates_no_bt_db(tmp_path, capsys):
    # NFP 2026-11-06 13:30Z is 224.5 h after NOW, so this run uses the 240 h ceiling (192 h would leave it out).
    paths = _setup(tmp_path, [("Core PCE Price Index m/m", PCE_RELEASE, "0.3%"),
                              ("Advance GDP q/q", GDP_RELEASE, "3.2%"),
                              ("Non-Farm Employment Change", NFP_RELEASE, "50K")])
    calls: list = []
    code = ct.main(_args(paths, "--dry-run", window="240"), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(calls), now=NOW)
    out = capsys.readouterr().out
    assert code == 0
    assert "TIER1 Core PCE Price Index m/m XAUUSD: neutral (would write)" in out
    assert "TIER1 [market-implied] Advance GDP q/q XAUUSD: bullish (would write)" in out
    assert "TIER1 [market-implied] Non-Farm Employment Change XAUUSD: bearish (would write)" in out
    assert "MARKET CALL Advance GDP q/q release 2026-10-29T12:30:00+00:00: implied 3.07353 (cooler than forecast)" in out
    assert "MARKET CALL Non-Farm Employment Change release 2026-11-06T13:30:00+00:00: implied 70 (hotter than forecast)" in out
    assert not paths[1].exists()
    assert sorted(c[:2] for c in calls) == [("KXGDP", "release_date"), ("KXPAYROLLS", "reference_month")]


def test_live_run_writes_market_implied_rows_and_a_rerun_is_unchanged(tmp_path, capsys):
    paths = _setup(tmp_path, [("Advance GDP q/q", GDP_RELEASE, "3.2%")])
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(), now=NOW) == 0
    rows = _rows(paths[1])
    assert [(r["instrument"], r["predicted_direction"], r["source"], r["confidence"]) for r in rows] == [
        ("US30", "bullish", TIER1_MARKET_IMPLIED_SOURCE, "Likely"),
        ("XAUUSD", "bullish", TIER1_MARKET_IMPLIED_SOURCE, "Likely")]
    assert rows[0]["value"].startswith("Kalshi KXGDP-26OCT30 implied median 3.0735 vs forecast 3.2%: cooler")
    capsys.readouterr()
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(),
                   now=NOW + dt.timedelta(hours=1)) == 0
    assert "TIER1 [market-implied] Advance GDP q/q XAUUSD: bullish (unchanged)" in capsys.readouterr().out
    assert len(_rows(paths[1])) == 2


def test_market_phase_runs_when_cleveland_fetch_fails(tmp_path, capsys):
    paths = _setup(tmp_path, [("Core PCE Price Index m/m", PCE_RELEASE, "0.3%"),
                              ("Advance GDP q/q", GDP_RELEASE, "3.2%")])

    def down(key):
        raise ConnectionError("clevelandfed.org unreachable")

    code = ct.main(_args(paths), cleveland_fetch=down, ladder_fetch=_ladder_fetch(), now=NOW)
    captured = capsys.readouterr()
    assert code == 1
    assert "Cleveland" in captured.err and "unreachable" in captured.err
    assert [r["event_title"] for r in _rows(paths[1])] == ["Advance GDP q/q", "Advance GDP q/q"]
    assert "TIER1 [market-implied] Advance GDP q/q XAUUSD: bullish (written)" in captured.out


def test_kalshi_fetch_error_is_a_skip_exit_2(tmp_path, capsys):
    paths = _setup(tmp_path, [("Advance GDP q/q", GDP_RELEASE, "3.2%")])

    def broken(series_ticker, ticketing, release):
        raise KalshiFetchError("KXGDP (release_date) ladder read failed: 503")

    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=broken, now=NOW) == 2
    out = capsys.readouterr().out
    assert "SKIPPED Advance GDP q/q release 2026-10-29T12:30:00+00:00:" in out and "503" in out
    assert _rows(paths[1]) == []


def test_run_market_no_call_writes_nothing_and_exits_0(tmp_path, capsys):
    paths = _setup(tmp_path, [("Retail Sales m/m", RETAIL_RELEASE, "0.4%")])
    now = dt.datetime(2026, 11, 10, 5, 0, tzinfo=UTC)
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(), now=now) == 0
    out = capsys.readouterr().out
    assert ("MARKET NO CALL Retail Sales m/m release 2026-11-17T13:30:00+00:00: "
            "no 50% crossing among liquid strikes") in out
    assert _rows(paths[1]) == []


def test_no_open_event_is_a_no_call_not_a_skip(tmp_path, capsys):
    paths = _setup(tmp_path, [("ISM Manufacturing PMI", dt.datetime(2026, 11, 2, 15, 0, tzinfo=UTC), "52.0")])
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(), now=NOW) == 0
    assert "MARKET NO CALL ISM Manufacturing PMI" in capsys.readouterr().out
    assert _rows(paths[1]) == []


def test_missing_forecast_is_pending_and_a_skip_inside_24h(tmp_path, capsys):
    paths = _setup(tmp_path, [("Advance GDP q/q", GDP_RELEASE, None)])
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(), now=NOW) == 0
    assert "TIER1 PENDING Advance GDP q/q release 2026-10-29T12:30:00+00:00: no readable forecast yet" in (
        capsys.readouterr().out)
    eve = GDP_RELEASE - dt.timedelta(hours=6)
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(), now=eve) == 2
    assert "SKIPPED Advance GDP q/q" in capsys.readouterr().out
    assert _rows(paths[1]) == []


def test_capture_never_writes_a_past_release(tmp_path, capsys):
    paths = _setup(tmp_path, [("Advance GDP q/q", GDP_RELEASE, "3.2%")])
    calls: list = []
    after = GDP_RELEASE + dt.timedelta(minutes=1)
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(calls), now=after) == 0
    assert calls == [] and _rows(paths[1]) == []
    assert "No market-implied release within 192 hours" in capsys.readouterr().out


def test_fed_funds_has_one_producer(tmp_path, capsys):
    paths = _setup(tmp_path, [("Federal Funds Rate", FED_RELEASE, "4.00%")])
    now = dt.datetime(2026, 12, 2, 5, 0, tzinfo=UTC)
    refused = tier1_research.main(
        ["record-call", "--dash-db", str(paths[0]), "--bt-db", str(paths[1]), "--event", "Federal Funds Rate",
         "--release", FED_RELEASE.isoformat(), "--instrument", "XAUUSD", "--value", "FedWatch: hike priced",
         "--confidence", "Likely", "--source", "CME FedWatch", "--direction", "bearish"], now=now)
    assert refused == 2
    assert ("'Federal Funds Rate' is a market-implied event: the Kalshi capture (capture_tier1.py) writes its "
            "call, do not log one by hand") in capsys.readouterr().err
    assert _rows(paths[1]) == []

    # An older FedWatch row from the research task (pre-B12) and a newer Kalshi row: the Kalshi row is the call.
    conn = bs.get_connection(paths[1])
    try:
        bs.record_tier1_prediction(conn, "Federal Funds Rate", "XAUUSD", FED_RELEASE,
                                   "CME FedWatch (via FXStreet): ~85% hike priced", "Likely", "https://fxstreet.com/x",
                                   "bearish", logged_at_utc=now - dt.timedelta(days=2))
    finally:
        conn.close()
    assert ct.main(_args(paths), cleveland_fetch=_cleveland, ladder_fetch=_ladder_fetch(), now=now) == 0
    out = capsys.readouterr().out
    assert "MARKET CALL Federal Funds Rate release 2026-12-09T19:00:00+00:00: implied 4.25 (hotter than forecast)" in out
    dash, bt = ws.get_connection(str(paths[0])), bs.get_connection(paths[1])
    try:
        row = svc.build_rows(dash, bt, event_title="Federal Funds Rate")[-1]
    finally:
        dash.close()
        bt.close()
    assert row.tier1_tier == "market_implied"
    assert row.detail.hand_logged["source"] == "Kalshi market-implied"
