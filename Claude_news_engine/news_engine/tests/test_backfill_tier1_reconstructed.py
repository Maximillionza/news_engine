import datetime as dt

from scoring import backtest_store as bs
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
    assert result == {"written": 0, "skipped_no_data": 1, "skipped_lookahead": 0}


def test_file_provider_reads_the_latest_as_of_before_release(tmp_path):
    path = tmp_path / "n.csv"
    path.write_text(
        "event_title,release_utc,as_of_utc,value,source\n"
        "CPI m/m,2026-03-11T12:30:00+00:00,2026-03-09T00:00:00+00:00,0.30,fed\n"
        "CPI m/m,2026-03-11T12:30:00+00:00,2026-03-10T00:00:00+00:00,0.40,fed\n")
    value, as_of, source = FileNowcastProvider(path).nowcast_before("CPI m/m", RELEASE)
    assert value == 0.40 and as_of.day == 10 and source == "fed"
