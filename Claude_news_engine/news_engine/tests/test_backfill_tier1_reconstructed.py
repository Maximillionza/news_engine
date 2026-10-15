import datetime as dt

from scoring import backtest_store as bs
import pytest

from scripts import backfill_tier1_reconstructed as bf
from scripts.backfill_tier1_reconstructed import FileNowcastProvider, run_backfill
from webapp import store as ws

UTC = dt.timezone.utc
RELEASE = dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC)


class FakeProvider:
    def __init__(self, rows): self.rows = rows
    def nowcast_before(self, title, release):
        return self.rows.get((title, release))


def _seed(dash):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("CPI m/m", RELEASE.isoformat(), "0.3%", "0.2%", "0.4%", None, RELEASE.isoformat(), RELEASE.isoformat(), "t", "High", "USD"))
    dash.commit()


def test_writes_a_reconstructed_snapshot_and_is_idempotent():
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash)
    provider = FakeProvider({("CPI m/m", RELEASE): (0.4, RELEASE - dt.timedelta(days=1), "rebuilt")})
    since, until = dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 8, 1, tzinfo=UTC)
    first = run_backfill(dash, bt, provider, "v1", since, until)
    second = run_backfill(dash, bt, provider, "v1", since, until)
    assert first["written"] == 1 and second["written"] == 1   # INSERT OR IGNORE: still one row
    assert bt.execute("SELECT COUNT(*) FROM tier1_nowcast_snapshots").fetchone()[0] == 1
    assert bt.execute("SELECT kind, rule_version FROM tier1_nowcast_snapshots").fetchone()[:] == ("reconstructed", "v1")


def test_a_provider_value_dated_after_the_release_is_refused():
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash)
    provider = FakeProvider({("CPI m/m", RELEASE): (0.4, RELEASE + dt.timedelta(hours=1), "bad")})
    result = run_backfill(dash, bt, provider, "v1", dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 8, 1, tzinfo=UTC))
    assert result["skipped_lookahead"] == 1 and result["written"] == 0


def test_no_data_is_skipped_not_invented():
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash)
    result = run_backfill(dash, bt, FakeProvider({}), "v1", dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 8, 1, tzinfo=UTC))
    assert result == {"written": 0, "newly_inserted": 0, "skipped_no_data": 1, "skipped_lookahead": 0}


def test_file_provider_reads_the_latest_as_of_before_release(tmp_path):
    path = tmp_path / "n.csv"
    path.write_text(
        "event_title,release_utc,as_of_utc,value,source\n"
        "CPI m/m,2026-03-11T12:30:00+00:00,2026-03-09T00:00:00+00:00,0.30,fed\n"
        "CPI m/m,2026-03-11T12:30:00+00:00,2026-03-10T00:00:00+00:00,0.40,fed\n")
    value, as_of, source = FileNowcastProvider(path).nowcast_before("CPI m/m", RELEASE)
    assert value == 0.40 and as_of.day == 10 and source == "fed"


def test_newly_inserted_counts_new_rows_only_so_a_rerun_reports_zero():
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash)
    provider = FakeProvider({("CPI m/m", RELEASE): (0.4, RELEASE - dt.timedelta(days=1), "rebuilt")})
    window = (dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 8, 1, tzinfo=UTC))
    first = run_backfill(dash, bt, provider, "v1", *window)
    second = run_backfill(dash, bt, provider, "v1", *window)
    assert (first["written"], first["newly_inserted"]) == (1, 1)
    assert (second["written"], second["newly_inserted"]) == (1, 0)


def test_an_offset_form_release_time_still_finds_its_nowcast(tmp_path):
    est = dt.timezone(dt.timedelta(hours=-5))
    release_local = RELEASE.astimezone(est)                 # 07:30-05:00, the same instant as 12:30Z
    path = tmp_path / "n.csv"
    path.write_text(
        "event_title,release_utc,as_of_utc,value,source\n"
        "CPI m/m,2026-03-11T12:30:00+00:00,2026-03-10T23:59:59+00:00,0.40,fed\n")
    found = FileNowcastProvider(path).nowcast_before("CPI m/m", release_local)
    assert found is not None and found[0] == 0.40


def test_run_backfill_normalises_offset_form_event_times():
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("CPI m/m", "2026-03-11T07:30:00-05:00", "0.3%", "0.2%", "0.4%", None, "t", "t", "t", "High", "USD"))
    dash.commit()
    provider = FakeProvider({("CPI m/m", RELEASE): (0.4, RELEASE - dt.timedelta(days=1), "rebuilt")})
    result = run_backfill(dash, bt, provider, "v1", dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 12, 31, tzinfo=UTC))
    assert result["written"] == 1 and result["skipped_no_data"] == 0


def test_a_naive_release_time_is_rejected_by_the_provider(tmp_path):
    path = tmp_path / "n.csv"
    path.write_text("event_title,release_utc,as_of_utc,value,source\n")
    with pytest.raises(ValueError):
        FileNowcastProvider(path).nowcast_before("CPI m/m", dt.datetime(2026, 3, 11, 12, 30))


def _cli_files(tmp_path):
    csv_path = tmp_path / "n.csv"
    csv_path.write_text(
        "event_title,release_utc,as_of_utc,value,source\n"
        "CPI m/m,2026-03-11T12:30:00+00:00,2026-03-10T23:59:59+00:00,0.40,fed\n")
    dash_db = tmp_path / "dash.db"
    conn = ws.get_connection(dash_db)
    _seed(conn)
    conn.close()
    return csv_path, dash_db


def test_cli_refuses_to_run_without_an_explicit_bt_db_or_the_live_env_var(tmp_path, monkeypatch, capsys):
    csv_path, dash_db = _cli_files(tmp_path)
    monkeypatch.delenv("STATS_BACKFILL_LIVE", raising=False)
    touched = []
    monkeypatch.setattr(bf.backtest_store, "get_connection",
                        lambda *a, **k: touched.append(a) or bs.get_connection(":memory:"))
    code = bf.main([str(csv_path), "v1", "2026-01-01", "2026-08-01", "--dash-db", str(dash_db)])
    assert code != 0 and touched == []                           # refused before any backtest DB was opened
    assert "STATS_BACKFILL_LIVE" in capsys.readouterr().err


def test_cli_runs_with_an_explicit_bt_db_and_prints_both_counts(tmp_path, monkeypatch, capsys):
    csv_path, dash_db = _cli_files(tmp_path)
    monkeypatch.delenv("STATS_BACKFILL_LIVE", raising=False)
    bt_db = tmp_path / "bt.db"
    code = bf.main([str(csv_path), "v1", "2026-01-01", "2026-08-01", "--dash-db", str(dash_db), "--bt-db", str(bt_db)])
    printed = capsys.readouterr().out
    assert code == 0 and "written" in printed and "newly_inserted" in printed
    bt = bs.get_connection(bt_db)
    assert bt.execute("SELECT COUNT(*) FROM tier1_nowcast_snapshots").fetchone()[0] == 1


def test_cli_env_var_allows_the_default_database(tmp_path, monkeypatch):
    csv_path, dash_db = _cli_files(tmp_path)
    monkeypatch.setenv("STATS_BACKFILL_LIVE", "1")
    memory = bs.get_connection(":memory:")
    monkeypatch.setattr(bf.backtest_store, "get_connection", lambda *a, **k: memory)
    assert bf.main([str(csv_path), "v1", "2026-01-01", "2026-08-01", "--dash-db", str(dash_db)]) == 0


def _bare_dash_db(path):
    """A dashboard.db holding ONLY event_history (old columns), so any schema setup or migration shows up."""
    import sqlite3
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE event_history (event_title TEXT, event_time_utc TEXT, forecast TEXT, actual TEXT)")
    conn.execute("INSERT INTO event_history VALUES ('CPI m/m', ?, '0.3%', '0.4%')", (RELEASE.isoformat(),))
    conn.commit()
    conn.close()


def test_cli_opens_the_dashboard_db_read_only_and_never_migrates_it(tmp_path, monkeypatch):
    import sqlite3
    csv_path, _ = _cli_files(tmp_path)
    dash_db = tmp_path / "bare_dash.db"
    _bare_dash_db(dash_db)
    before = dash_db.read_bytes()
    monkeypatch.delenv("STATS_BACKFILL_LIVE", raising=False)
    seen = {}
    real_run = bf.run_backfill

    def spy(dash_conn, *args, **kwargs):
        try:                                                 # the connection the CLI hands over cannot write
            dash_conn.execute("CREATE TABLE scribble (x)")
        except sqlite3.OperationalError as exc:
            seen["write_error"] = str(exc)
        return real_run(dash_conn, *args, **kwargs)

    monkeypatch.setattr(bf, "run_backfill", spy)
    code = bf.main([str(csv_path), "v1", "2026-01-01", "2026-08-01", "--dash-db", str(dash_db),
                    "--bt-db", str(tmp_path / "bt.db")])
    assert code == 0
    assert "readonly" in seen.get("write_error", "")
    assert dash_db.read_bytes() == before                    # no schema setup, no migration, no write at all
    tables = sqlite3.connect(dash_db).execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert tables == [("event_history",)]
