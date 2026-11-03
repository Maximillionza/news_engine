"""
Tests for scripts/rule_tier_replay.py -- temp SQLite files only, no network, the live DBs are never opened.
"""
import datetime as dt
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerting import store
from scripts import rule_tier_replay as replay_script

UTC = dt.timezone.utc

_ID_1 = "U.S. oil falls below $100 as Saudi Arabia reportedly offers more crude via Hormuz after pipeline attack"
_ID_5 = "Aramco halts October crude deliveries to some European refiners after pipeline attack, Bloomberg reports - reuters.com"
_ID_7 = "U.S. urges Americans to reconsider Middle East travel as Iran tensions rise"


def _db(tmp_path: Path, rows: list[tuple[str, str]]) -> str:
    path = str(tmp_path / "alerts.db")
    conn = store.get_connection(path)
    when = dt.datetime(2026, 10, 1, tzinfo=UTC)
    for index, (headline, method) in enumerate(rows):
        store.record_alert(
            conn, headline=headline, source="s", url=f"https://example.com/{index}",
            published_utc=when, detected_at_utc=when, category="energy", severity="High",
            classification_method=method, rationale=None, affected_symbols=[],
        )
    conn.close()
    return path


def test_replay_routes_the_three_live_alerts(tmp_path, capsys):
    path = _db(tmp_path, [(_ID_1, "rule_tier"), (_ID_5, "rule_tier"), (_ID_7, "rule_tier")])
    assert replay_script.main(["--alerts-db", path]) == 0
    out = capsys.readouterr().out
    assert "3 of 3" in out
    assert "price_report: 1 (ids 1)" in out
    assert "unknown_us_link: 1 (ids 2)" in out
    assert "summary_only: 1 (ids 3)" in out
    assert "summaries are not stored" in out


def test_replay_keeps_a_clean_hit_and_skips_other_methods(tmp_path, capsys):
    path = _db(tmp_path, [
        ("Strait of Hormuz closed after Iranian strike", "rule_tier"),
        ("Iran denies strait of hormuz closed", "llm"),
    ])
    assert replay_script.main(["--alerts-db", path]) == 0
    out = capsys.readouterr().out
    assert "0 of 1" in out
    assert "stays on the rule tier: 1 (ids 1)" in out


def test_replay_reads_only_and_writes_nothing(tmp_path, capsys):
    path = _db(tmp_path, [(_ID_1, "rule_tier")])
    before = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    assert replay_script.main(["--alerts-db", path]) == 0
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == before

    conn = replay_script.open_readonly(Path(path))
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM shock_alerts")
    conn.close()


def test_replay_missing_database_is_an_error_not_a_new_file(tmp_path, capsys):
    path = tmp_path / "missing.db"
    assert replay_script.main(["--alerts-db", str(path)]) == 2
    assert not path.exists()
