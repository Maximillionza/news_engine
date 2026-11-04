"""
Tests for scripts/relevance_replay.py -- temp SQLite files only, no network, the live DB is never opened.
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
from scripts import relevance_replay as replay_script

UTC = dt.timezone.utc
_EVENT_TIME = dt.datetime(2026, 10, 29, 12, 30, tzinfo=UTC)
_BEFORE = _EVENT_TIME - dt.timedelta(hours=2)

WESTPAC = "Westpac's latest job cuts not AI-driven, spokesperson says - Reuters"
GOLD = "Gold edges up as jobless claims rise"
CLAIMS = "US jobless claims fall to 194,000"
CLAIMS_2 = "US layoffs stay low as jobless claims drop"
CLAIMS_3 = "Labor Department says jobless claims held steady"
BLURB = "First Solar stock heads into the open after a 4.42 percent drop"


def _entry(title: str, sentiment: float) -> dict:
    return {"title": title, "url": f"https://x/{title[:12]}", "source": "Reuters",
            "published_utc": "2026-10-29T10:00:00+00:00", "usd_sentiment": sentiment, "weight_pct": 33.3}


def _row(title: str, status: str, reason, sentiment) -> dict:
    return {"title": title, "url": f"https://x/{title[:12]}", "source": "Reuters", "source_type": "rss",
            "published_utc": "2026-10-29T10:00:00+00:00", "status": status, "reason": reason, "usd_sentiment": sentiment,
            "trust_weight": None, "time_weight": None, "combined_weight": None, "weight_pct": None, "matched_terms": []}


def _record(conn: sqlite3.Connection, title: str, *, instrument: str = "XAUUSD", scored: dt.datetime = _BEFORE,
            event_time: dt.datetime = _EVENT_TIME, top: list | None = None) -> int:
    record_prediction(conn, title, instrument, event_time, 0.6, "bullish", 0.5, 3, False,
                      scored_at_utc=scored, top_contributions=top)
    return conn.execute("SELECT MAX(id) FROM predictions").fetchone()[0]


def _build_db(path: Path) -> None:
    conn = get_connection(path)
    try:
        # Evidence era. Three kept voters, one zero-sentiment article, one the new rule drops, stored exclusions.
        evidence_id = _record(conn, "Unemployment Claims", top=[_entry(WESTPAC, 0.5)])
        record_prediction_article_contributions(conn, evidence_id, "Unemployment Claims", _EVENT_TIME, "XAUUSD", [
            _row(WESTPAC, "included", None, 0.5),
            _row(CLAIMS, "included", None, -0.4),
            _row(CLAIMS_2, "included", "redundancy_discount", -0.3),
            _row(CLAIMS_3, "included", None, 0.0),
            _row(BLURB, "excluded", "single_stock_blurb", None),
            _row("Same story again", "excluded", "same_incident", 0.2),
        ])
        # Older occurrence: top_contributions_json only, final row is the later of two; one entry drops.
        old_time = _EVENT_TIME - dt.timedelta(days=7)
        _record(conn, "Unemployment Claims", event_time=old_time, scored=old_time - dt.timedelta(hours=5),
                top=[_entry(CLAIMS, -0.4), _entry(CLAIMS_2, -0.2), _entry(CLAIMS_3, -0.1)])
        _record(conn, "Unemployment Claims", event_time=old_time, scored=old_time - dt.timedelta(hours=1),
                top=[_entry(CLAIMS, -0.4), _entry(CLAIMS_2, -0.2), _entry(GOLD, 0.3)])
        # After the release: not the final pre-release row, but its article still counts as stored.
        _record(conn, "Unemployment Claims", event_time=old_time, scored=old_time + dt.timedelta(hours=1),
                top=[_entry(CLAIMS, -0.4), _entry(CLAIMS_2, -0.2), _entry(CLAIMS_3, -0.1)])
        # Other instruments never count as predictions, and a row with nothing stored is thin.
        _record(conn, "CPI m/m", instrument="US30", top=[_entry("Dollar rises after hot CPI", 0.4)])
        _record(conn, "CPI m/m")
    finally:
        conn.close()


@pytest.fixture()
def db_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "backtest_log.db"
        _build_db(path)
        yield path


def test_replay_counts_evidence_and_top_contributions(db_path):
    conn = replay_script.open_readonly(db_path)
    try:
        families = replay_script.replay(conn)
    finally:
        conn.close()

    jobs = families["jobs"]
    # Distinct (event, title): Westpac, Claims, Claims 2, Claims 3 from the evidence rows, Gold from the older JSON.
    assert jobs.articles == 5
    assert jobs.would_exclude == {"no_us_subject": 1, "other_asset_lead": 1}
    # Evidence era only: 4 included + the blurb. same_incident is a duplicate, not a filter decision.
    assert jobs.evidence_articles == 5
    assert jobs.stored_excluded == 1
    assert jobs.evidence_would_exclude == 1
    assert jobs.predictions == 2
    # Newest occurrence: 3 voters before, 2 after. Older: 3 before, 2 after, read from the final pre-release row.
    assert jobs.thin_before == 0
    assert jobs.thin_predictions == 2

    cpi = families["cpi"]
    assert cpi.articles == 1 and not cpi.would_exclude
    assert cpi.predictions == 1 and cpi.thin_predictions == 1 and cpi.thin_before == 1


def test_replay_never_writes(db_path, capsys):
    before = db_path.read_bytes()
    assert replay_script.main(["--bt-db", str(db_path)]) == 0
    assert db_path.read_bytes() == before
    out = capsys.readouterr().out
    assert "jobs" in out and "no_us_subject" in out
    assert "summaries are not stored" in out

    conn = replay_script.open_readonly(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM predictions")
    finally:
        conn.close()

    assert replay_script.main(["--bt-db", str(db_path.parent / "missing.db")]) == 2


def test_replay_survives_a_db_without_the_evidence_table(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "old.db"
        conn = get_connection(path)
        try:
            _record(conn, "Unemployment Claims", top=[_entry(WESTPAC, 0.5)])
            conn.execute("DROP TABLE prediction_article_contributions")
            conn.commit()
        finally:
            conn.close()
        assert replay_script.main(["--bt-db", str(path)]) == 0
    assert "no_us_subject" in capsys.readouterr().out
