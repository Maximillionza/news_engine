"""
SQLite persistence for the dashboard — two concerns in one file since
they share the same DB and open/close lifecycle:
  1. prediction_runs — one row per (symbol, event, scoring run), powers
     the before/after diff strip surviving server restarts.
  2. tracked_symbols — which tickers the dashboard currently tracks,
     added/removed via the API.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "dashboard.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prediction_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    scored_at_utc TEXT NOT NULL,
    probability REAL NOT NULL,
    direction TEXT NOT NULL,
    raw_score REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tracked_symbols (
    symbol TEXT PRIMARY KEY
);
"""


@dataclass
class PredictionRun:
    id: int
    symbol: str
    event_title: str
    event_time_utc: str
    scored_at_utc: str
    probability: float
    direction: str
    raw_score: float


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # db_path resolved inside the body (not as a default arg value) so
    # tests can patch module-level DB_PATH and have it take effect.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def record_run(
    conn: sqlite3.Connection,
    symbol: str,
    event_title: str,
    event_time_utc: dt.datetime,
    probability: float,
    direction: str,
    raw_score: float,
    scored_at_utc: Optional[dt.datetime] = None,
) -> int:
    scored_at = scored_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO prediction_runs (symbol, event_title, event_time_utc, scored_at_utc, probability, direction, raw_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (symbol, event_title, event_time_utc.isoformat(), scored_at.isoformat(), probability, direction, raw_score),
    )
    conn.commit()
    return cursor.lastrowid


def get_latest_two(conn: sqlite3.Connection, symbol: str, event_title: str) -> list[PredictionRun]:
    """Most recent run first. Returns 0, 1, or 2 rows — callers must handle fewer than 2 (no diff possible yet)."""
    rows = conn.execute(
        "SELECT * FROM prediction_runs WHERE symbol = ? AND event_title = ? "
        "ORDER BY scored_at_utc DESC LIMIT 2",
        (symbol, event_title),
    ).fetchall()
    return [PredictionRun(**dict(row)) for row in rows]


def get_history(conn: sqlite3.Connection, symbol: str, event_title: str) -> list[PredictionRun]:
    """Full run history for a (symbol, event) pair, oldest first."""
    rows = conn.execute(
        "SELECT * FROM prediction_runs WHERE symbol = ? AND event_title = ? "
        "ORDER BY scored_at_utc ASC",
        (symbol, event_title),
    ).fetchall()
    return [PredictionRun(**dict(row)) for row in rows]


def add_tracked_symbol(conn: sqlite3.Connection, symbol: str) -> None:
    conn.execute("INSERT OR IGNORE INTO tracked_symbols (symbol) VALUES (?)", (symbol,))
    conn.commit()


def remove_tracked_symbol(conn: sqlite3.Connection, symbol: str) -> None:
    conn.execute("DELETE FROM tracked_symbols WHERE symbol = ?", (symbol,))
    conn.commit()


def list_tracked_symbols(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT symbol FROM tracked_symbols ORDER BY symbol").fetchall()
    return [row["symbol"] for row in rows]
