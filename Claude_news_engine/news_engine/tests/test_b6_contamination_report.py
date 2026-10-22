"""
Tests for scripts/b6_contamination_report.py -- temp SQLite files only, no network,
the live DB is never opened.
"""
import datetime as dt
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import get_connection, record_prediction, record_prediction_article_contributions
from scripts import b6_contamination_report as report

UTC = dt.timezone.utc
_EVENT_TIME = dt.datetime(2026, 10, 14, 18, 0, tzinfo=UTC)

SCHNABEL = "Interest rates must rise further on inflation risks, ECB's Schnabel tells Bloomberg - Reuters"
FED_TITLE = "Fed signals faster rate cuts as US growth slows"
GOLD_LED = "Gold edges up as October rate hike bets ease, stronger dollar cap gains"
CLEAN_NFP = "US payrolls jump 250,000; rate cut bets fade"

_FAMILY_KEYS = {
    "rows", "rows_with_contributions", "contributions", "unique_contributions", "removed_by_reason",
    "removed_unique", "removed_nonzero", "rows_touched", "rows_all_removed", "occurrences_touched",
    "same_url_pairs",
}


def _entry(title: str, sentiment: float, url: str) -> dict:
    return {"title": title, "url": url, "source": "Reuters", "published_utc": "2026-10-14T12:00:00+00:00",
            "usd_sentiment": sentiment, "weight_pct": 33.3}


def _build_db(path: Path) -> None:
    conn = get_connection(path)
    try:
        record_prediction(conn, "FOMC Statement", "XAUUSD", _EVENT_TIME, 0.6, "bullish", 0.5, 3, False,
                          top_contributions=[_entry(SCHNABEL, 0.75, "https://x/1"),
                                             _entry(FED_TITLE, -0.40, "https://x/2"),
                                             _entry(GOLD_LED, 0.94, "https://x/3")])
        record_prediction(conn, "CPI m/m", "XAUUSD", _EVENT_TIME, 0.6, "bullish", 0.5, 2, False,
                          top_contributions=[_entry(SCHNABEL, 0.75, "https://x/1"),
                                             _entry(SCHNABEL, 0.75, "https://x/1")])
        record_prediction(conn, "Non-Farm Employment Change", "XAUUSD", _EVENT_TIME, 0.6, "bullish", 0.5, 1, False,
                          top_contributions=[_entry(CLEAN_NFP, -0.30, "https://x/4")])
        # No stored evidence at all: not counted as a row.
        record_prediction(conn, "FOMC Statement", "US30", _EVENT_TIME, 0.5, "neutral", 0.1, 0, False)
        # Non-live source is ignored.
        record_prediction(conn, "FOMC Statement", "EURUSD", _EVENT_TIME, 0.5, "neutral", 0.1, 1, False,
                          source="reconstructed", top_contributions=[_entry(SCHNABEL, 0.75, "https://x/1")])
    finally:
        conn.close()


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "b6_report.db"
    _build_db(path)
    return path


def _summary(db_path: Path) -> dict:
    conn = report.open_readonly(db_path)
    try:
        return report.summarize(conn)
    finally:
        conn.close()


def test_summary_keys_exact(db_path: Path):
    summary = _summary(db_path)
    assert set(summary) == {"families", "examples", "totals"}
    assert set(summary["families"]) == {"fomc", "cpi", "jobs"}
    for stats in summary["families"].values():
        assert set(stats) == _FAMILY_KEYS
    assert set(summary["totals"]) == _FAMILY_KEYS


def test_counts_by_reason(db_path: Path):
    families = _summary(db_path)["families"]
    fomc, cpi, jobs = families["fomc"], families["cpi"], families["jobs"]
    # The gold-led title has no stored summary, so the co-term step fires before the subject step.
    assert fomc["removed_by_reason"] == {"foreign_cb": 1, "no_fed_coterm": 1}
    assert fomc["removed_nonzero"] == 2
    assert fomc["rows"] == 1 and fomc["rows_with_contributions"] == 1
    assert fomc["contributions"] == 3 and fomc["rows_touched"] == 1 and fomc["rows_all_removed"] == 0
    assert cpi["same_url_pairs"] == 1
    assert cpi["removed_by_reason"] == {"foreign_cb": 2}
    assert cpi["contributions"] == 2 and cpi["unique_contributions"] == 1
    assert cpi["removed_unique"] == 1 and cpi["rows_all_removed"] == 1
    assert jobs["removed_unique"] == 0 and jobs["removed_by_reason"] == {} and jobs["rows_touched"] == 0


def test_totals_sum_the_families(db_path: Path):
    summary = _summary(db_path)
    totals = summary["totals"]
    assert totals["rows"] == 3
    assert totals["contributions"] == 6
    assert totals["removed_by_reason"] == {"foreign_cb": 3, "no_fed_coterm": 1}
    assert totals["rows_touched"] == 2


def test_examples_are_capped_titles_by_reason(db_path: Path):
    examples = _summary(db_path)["examples"]
    assert examples["fomc"]["foreign_cb"] == [SCHNABEL]
    assert examples["fomc"]["no_fed_coterm"] == [GOLD_LED]
    assert examples["cpi"]["foreign_cb"] == [SCHNABEL]  # two copies, one example title
    assert "jobs" not in examples or examples["jobs"] == {}


def test_open_readonly_refuses_writes(db_path: Path, tmp_path: Path):
    conn = report.open_readonly(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO dismissals (event_title, instrument, event_time_utc, reason, dismissed_at_utc) "
                         "VALUES ('a', 'b', 'c', 'd', 'e')")
    finally:
        conn.close()
    with pytest.raises(FileNotFoundError):
        report.open_readonly(tmp_path / "missing.db")


def test_count_foreign_cb_included(tmp_path: Path):
    path = tmp_path / "verify.db"
    conn = get_connection(path)
    try:
        pid = record_prediction(conn, "FOMC Statement", "XAUUSD", _EVENT_TIME, 0.6, "bullish", 0.5, 3, False)

        def row(title: str, status: str, url: str) -> dict:
            return {"title": title, "url": url, "source": "Reuters", "source_type": "rss",
                    "published_utc": "2026-10-14T12:00:00+00:00", "status": status, "reason": None,
                    "usd_sentiment": 0.5, "trust_weight": 1.0, "time_weight": 1.0, "combined_weight": 1.0,
                    "weight_pct": 100.0, "matched_terms": None}

        record_prediction_article_contributions(conn, pid, "FOMC Statement", _EVENT_TIME, "XAUUSD", [
            row(SCHNABEL, "included", "https://x/old"),       # before `since`
            row(SCHNABEL, "excluded", "https://x/excl"),      # excluded rows never count
            row(FED_TITLE, "included", "https://x/fed"),      # not a foreign CB
            row("BoE's Pill says a rate hike need not be start of long series - Reuters", "included", "https://x/new"),
        ])
        # recorded_at_utc is "now" on insert; pin each row so the window is deterministic.
        for url, stamp in (("https://x/old", "2026-10-01T00:00:00+00:00"), ("https://x/excl", "2026-10-20T00:00:00+00:00"),
                           ("https://x/fed", "2026-10-20T00:00:00+00:00"), ("https://x/new", "2026-10-20T00:00:00+00:00")):
            conn.execute("UPDATE prediction_article_contributions SET recorded_at_utc = ? WHERE url = ?", (stamp, url))
        conn.commit()
        assert report.count_foreign_cb_included(conn, "2026-10-10T00:00:00+00:00") == 1
        assert report.count_foreign_cb_included(conn, "2026-10-10T00:00:00Z") == 1
        assert report.count_foreign_cb_included(conn, "2026-10-25T00:00:00+00:00") == 0
        assert report.count_foreign_cb_included(conn, "2026-09-01T00:00:00+00:00") == 2
    finally:
        conn.close()


def test_render_markdown_has_family_table_and_caveats(db_path: Path):
    text = report.render_markdown(_summary(db_path), "b6_report.db", "2026-10-22 12:00 SAST")
    assert "| Family |" in text
    assert "top-3 only" in text
    assert "title only" in text
    assert "SAST" in text
    assert "foreign_cb" in text


def test_main_prints_markdown(db_path: Path, capsys):
    assert report.main(["--db", str(db_path)]) == 0
    assert "| Family |" in capsys.readouterr().out


def test_main_verify_since(tmp_path: Path, capsys):
    path = tmp_path / "v.db"
    get_connection(path).close()
    assert report.main(["--db", str(path), "--verify-since", "2026-10-22T08:00:00+00:00"]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_main_verify_since_without_table_is_an_error(db_path: Path, tmp_path: Path, capsys):
    # A pre-B6 database has no evidence table: that must not read as a passing "0".
    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.execute("CREATE TABLE predictions (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    assert report.main(["--db", str(old), "--verify-since", "2026-10-22T08:00:00+00:00"]) == 2
    assert capsys.readouterr().out.strip() != "0"


def test_main_missing_db_returns_error(tmp_path: Path):
    assert report.main(["--db", str(tmp_path / "nope.db")]) == 2


def test_report_opens_db_read_only_via_uri():
    source = (Path(__file__).resolve().parent.parent / "scripts" / "b6_contamination_report.py").read_bytes()
    assert b"mode=ro" in source
    assert b"\x08" not in source
