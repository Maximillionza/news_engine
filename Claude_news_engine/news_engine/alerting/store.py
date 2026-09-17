"""
Standalone storage for the real-time news-shock alerting tool — a brand
new, separate SQLite DB, deliberately not merged into webapp/dashboard.db
or scoring/backtest_log.db until this tool has proven worth integrating
(see docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md,
Scope boundary).
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "shock_alerts.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shock_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    detected_at_utc TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    classification_method TEXT NOT NULL,
    rationale TEXT,
    affected_symbols_json TEXT NOT NULL,
    delivery_status TEXT,
    reality_move_5min_json TEXT,
    reality_move_secondary_json TEXT,
    reality_check_at_utc TEXT,
    reality_mismatch INTEGER
);

CREATE TABLE IF NOT EXISTS shock_near_misses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    closest_category TEXT,
    near_miss_score REAL,
    seen_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS poll_cursor (
    source TEXT PRIMARY KEY,
    last_seen_utc TEXT NOT NULL
);
"""

_schema_ready_paths: set[str] = set()


@dataclass
class ShockAlertRow:
    id: int
    headline: str
    sources: list[dict]
    detected_at_utc: dt.datetime
    category: str
    severity: str
    classification_method: str
    rationale: Optional[str]
    affected_symbols: list[dict]
    delivery_status: Optional[str]
    reality_move_5min: Optional[dict]
    reality_move_secondary: Optional[dict]
    reality_check_at_utc: Optional[dt.datetime]
    reality_mismatch: Optional[bool]


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # Mirrors webapp/store.py's get_connection() pattern exactly: resolve
    # inside the body (not a default arg) so tests can pass ":memory:" or
    # a patched path, row_factory for name-based access, and a per-path
    # ready-cache so idempotent CREATE TABLE IF NOT EXISTS doesn't re-run
    # on every call. ":memory:" is never cached -- each call creates a
    # genuinely separate empty DB.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if path == ":memory:":
        conn.executescript(_SCHEMA)
        return conn
    path_key = str(Path(path).resolve())
    if path_key not in _schema_ready_paths:
        conn.executescript(_SCHEMA)
        _schema_ready_paths.add(path_key)
    return conn


def _row_to_shock_alert(d: dict) -> ShockAlertRow:
    return ShockAlertRow(
        id=d["id"],
        headline=d["headline"],
        sources=json.loads(d["sources_json"]),
        detected_at_utc=dt.datetime.fromisoformat(d["detected_at_utc"]),
        category=d["category"],
        severity=d["severity"],
        classification_method=d["classification_method"],
        rationale=d["rationale"],
        affected_symbols=json.loads(d["affected_symbols_json"]),
        delivery_status=d["delivery_status"],
        reality_move_5min=json.loads(d["reality_move_5min_json"]) if d["reality_move_5min_json"] else None,
        reality_move_secondary=json.loads(d["reality_move_secondary_json"]) if d["reality_move_secondary_json"] else None,
        reality_check_at_utc=dt.datetime.fromisoformat(d["reality_check_at_utc"]) if d["reality_check_at_utc"] else None,
        reality_mismatch=bool(d["reality_mismatch"]) if d["reality_mismatch"] is not None else None,
    )


def record_alert(
    conn: sqlite3.Connection,
    headline: str,
    source: str,
    url: str,
    published_utc: dt.datetime,
    detected_at_utc: dt.datetime,
    category: str,
    severity: str,
    classification_method: str,
    rationale: Optional[str],
    affected_symbols: list[dict],
) -> int:
    """Inserts a new shock_alerts row with one initial source; returns the new row's id."""
    sources = [{"source": source, "url": url, "published_utc": published_utc.isoformat()}]
    cur = conn.execute(
        "INSERT INTO shock_alerts (headline, sources_json, detected_at_utc, category, severity, "
        "classification_method, rationale, affected_symbols_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (headline, json.dumps(sources), detected_at_utc.isoformat(), category, severity,
         classification_method, rationale, json.dumps(affected_symbols)),
    )
    conn.commit()
    return cur.lastrowid


def append_source(conn: sqlite3.Connection, alert_id: int, source: str, url: str, published_utc: dt.datetime) -> None:
    """Appends a corroborating source to an existing alert instead of creating a new row (dedup.py's match path)."""
    row = conn.execute("SELECT sources_json FROM shock_alerts WHERE id = ?", (alert_id,)).fetchone()
    sources = json.loads(row["sources_json"])
    sources.append({"source": source, "url": url, "published_utc": published_utc.isoformat()})
    conn.execute("UPDATE shock_alerts SET sources_json = ? WHERE id = ?", (json.dumps(sources), alert_id))
    conn.commit()


def get_alert(conn: sqlite3.Connection, alert_id: int) -> Optional[ShockAlertRow]:
    row = conn.execute("SELECT * FROM shock_alerts WHERE id = ?", (alert_id,)).fetchone()
    if row is None:
        return None
    return _row_to_shock_alert(dict(row))


def get_cursor(conn: sqlite3.Connection, source: str) -> Optional[dt.datetime]:
    row = conn.execute("SELECT last_seen_utc FROM poll_cursor WHERE source = ?", (source,)).fetchone()
    if row is None:
        return None
    return dt.datetime.fromisoformat(row["last_seen_utc"])


def set_cursor(conn: sqlite3.Connection, source: str, last_seen_utc: dt.datetime) -> None:
    conn.execute(
        "INSERT INTO poll_cursor (source, last_seen_utc) VALUES (?, ?) "
        "ON CONFLICT(source) DO UPDATE SET last_seen_utc = excluded.last_seen_utc",
        (source, last_seen_utc.isoformat()),
    )
    conn.commit()


def record_near_miss(
    conn: sqlite3.Connection, headline: str, closest_category: Optional[str],
    near_miss_score: Optional[float], seen_at_utc: Optional[dt.datetime] = None,
) -> int:
    """Rolling audit log for taxonomy tuning -- never read by the live alerting path itself."""
    seen_at_utc = seen_at_utc or dt.datetime.now(dt.timezone.utc)
    cur = conn.execute(
        "INSERT INTO shock_near_misses (headline, closest_category, near_miss_score, seen_at_utc) VALUES (?, ?, ?, ?)",
        (headline, closest_category, near_miss_score, seen_at_utc.isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def list_recent_alerts_in_category(conn: sqlite3.Connection, category: str, since_utc: dt.datetime) -> list[ShockAlertRow]:
    rows = conn.execute(
        "SELECT * FROM shock_alerts WHERE category = ? AND detected_at_utc >= ? ORDER BY detected_at_utc DESC",
        (category, since_utc.isoformat()),
    ).fetchall()
    return [_row_to_shock_alert(dict(r)) for r in rows]


def list_recent_alerts(conn: sqlite3.Connection, since_utc: dt.datetime) -> list[ShockAlertRow]:
    rows = conn.execute(
        "SELECT * FROM shock_alerts WHERE detected_at_utc >= ? ORDER BY detected_at_utc DESC",
        (since_utc.isoformat(),),
    ).fetchall()
    return [_row_to_shock_alert(dict(r)) for r in rows]


def set_delivery_status(conn: sqlite3.Connection, alert_id: int, status: str) -> None:
    conn.execute("UPDATE shock_alerts SET delivery_status = ? WHERE id = ?", (status, alert_id))
    conn.commit()


def set_severity(conn: sqlite3.Connection, alert_id: int, severity: str) -> None:
    """
    Upgrades an existing alert's stored severity -- used by poll_once.py
    when a dedup-matched corroborating article turns out more severe than
    the original assessment (e.g. a story dedup caught as Medium later
    escalates to an unambiguous hard-rule High). Never called to
    downgrade -- that judgment call stays manual, same discipline as
    every other severity/direction call in this project.
    """
    conn.execute("UPDATE shock_alerts SET severity = ? WHERE id = ?", (severity, alert_id))
    conn.commit()


def get_alerts_needing_reality_check(conn: sqlite3.Connection, older_than_utc: dt.datetime) -> list[ShockAlertRow]:
    rows = conn.execute(
        "SELECT * FROM shock_alerts WHERE reality_check_at_utc IS NULL AND detected_at_utc >= ? "
        "ORDER BY detected_at_utc ASC",
        (older_than_utc.isoformat(),),
    ).fetchall()
    return [_row_to_shock_alert(dict(r)) for r in rows]


def record_reality_check(
    conn: sqlite3.Connection, alert_id: int,
    move_5min: Optional[dict], move_secondary: Optional[dict],
    mismatch: Optional[bool], checked_at_utc: Optional[dt.datetime] = None,
) -> None:
    checked_at_utc = checked_at_utc or dt.datetime.now(dt.timezone.utc)
    conn.execute(
        "UPDATE shock_alerts SET reality_move_5min_json = ?, reality_move_secondary_json = ?, "
        "reality_check_at_utc = ?, reality_mismatch = ? WHERE id = ?",
        (
            json.dumps(move_5min) if move_5min is not None else None,
            json.dumps(move_secondary) if move_secondary is not None else None,
            checked_at_utc.isoformat(),
            None if mismatch is None else int(mismatch),
            alert_id,
        ),
    )
    conn.commit()
