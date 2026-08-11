"""
SQLite persistence for the dashboard — three concerns in one file since
they share the same DB and open/close lifecycle:
  1. prediction_runs — one row per (symbol, event, scoring run), powers
     the before/after diff strip surviving server restarts.
  2. tracked_symbols — which tickers the dashboard currently tracks,
     added/removed via the API.
  3. calendar_snapshot — the current known-good calendar, persisted by
     webapp/scheduler.py's background loop (the SOLE calendar fetcher —
     see its module docstring) and read-only for API routes. Routes never
     fetch live themselves: a request is answered from whatever's stored,
     instantly, regardless of the live feed's health at that moment. Per
     explicit product decision, a fetch that returns unchanged data does
     NOT touch the stored row — "store and use as current until new
     information supersedes this" — see save_calendar_snapshot_if_changed().
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass, field
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
    probability REAL,
    direction TEXT NOT NULL,
    raw_score REAL
);
CREATE TABLE IF NOT EXISTS tracked_symbols (
    symbol TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS calendar_snapshot (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton row, the current snapshot
    events_json TEXT NOT NULL,
    fetched_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    forecast TEXT,
    previous TEXT,
    actual TEXT,
    surprise_direction TEXT,
    recorded_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    UNIQUE(event_title, event_time_utc)
);
"""


@dataclass
class PredictionRun:
    id: int
    symbol: str
    event_title: str
    event_time_utc: str
    scored_at_utc: str
    probability: Optional[float]
    direction: str
    raw_score: Optional[float]


@dataclass
class CalendarSnapshot:
    events: list[dict] = field(default_factory=list)  # plain dicts: title/country/impact/event_time_utc/forecast/previous/actual
    fetched_at_utc: str = ""


@dataclass
class EventHistoryRow:
    event_title: str
    event_time_utc: str
    forecast: Optional[str]
    previous: Optional[str]
    actual: Optional[str]
    surprise_direction: Optional[str]


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
    probability: Optional[float],
    direction: str,
    raw_score: Optional[float],
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
    """
    Most recent run first. Returns 0, 1, or 2 rows — callers must handle
    fewer than 2 (no diff possible yet). `id` breaks ties on identical
    scored_at_utc (e.g. a scheduler cycle stamping every run with one
    shared "now") — SQLite gives no ordering guarantee among ties on
    scored_at_utc alone, so without this "most recent" could silently
    pick the earlier-inserted row.
    """
    rows = conn.execute(
        "SELECT * FROM prediction_runs WHERE symbol = ? AND event_title = ? "
        "ORDER BY scored_at_utc DESC, id DESC LIMIT 2",
        (symbol, event_title),
    ).fetchall()
    return [PredictionRun(**dict(row)) for row in rows]


def get_history(conn: sqlite3.Connection, symbol: str, event_title: str) -> list[PredictionRun]:
    """Full run history for a (symbol, event) pair, oldest first. `id` breaks scored_at_utc ties, same reasoning as get_latest_two()."""
    rows = conn.execute(
        "SELECT * FROM prediction_runs WHERE symbol = ? AND event_title = ? "
        "ORDER BY scored_at_utc ASC, id ASC",
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


def _event_to_dict(event) -> dict:
    """
    Serializes an EconomicEvent (data_layer.calendar_feed) to a plain,
    JSON-safe dict for calendar_snapshot storage — deliberately duck-typed
    (no import of EconomicEvent itself) so this module doesn't need to
    know the calendar feed's exact type, just its attribute shape.
    Excludes `raw` (the source API's raw dict) — not needed for display,
    would bloat storage and churn the diff on every fetch for no reason.
    """
    return {
        "title": event.title,
        "country": event.country,
        "impact": event.impact,
        "event_time_utc": event.event_time_utc.isoformat(),
        "forecast": event.forecast,
        "previous": event.previous,
        "actual": event.actual,
    }


def get_calendar_snapshot(conn: sqlite3.Connection) -> Optional[CalendarSnapshot]:
    """Returns the current persisted calendar snapshot, or None if nothing has been fetched successfully yet."""
    row = conn.execute("SELECT events_json, fetched_at_utc FROM calendar_snapshot WHERE id = 1").fetchone()
    if row is None:
        return None
    return CalendarSnapshot(events=json.loads(row["events_json"]), fetched_at_utc=row["fetched_at_utc"])


def save_calendar_snapshot_if_changed(
    conn: sqlite3.Connection, events: list, fetched_at_utc: dt.datetime,
) -> bool:
    """
    Persists `events` (a list of EconomicEvent) as the current calendar
    snapshot, but ONLY if it actually differs from what's already stored —
    explicit product decision: a fetch that returns identical data is not
    new information and must not touch the stored row, not even its
    timestamp. "Store and use as current until new information
    supersedes this." Returns True if the snapshot was updated, False if
    unchanged (including when it matches byte-for-byte after serialization).
    """
    new_serialized = json.dumps([_event_to_dict(e) for e in events], sort_keys=True)
    row = conn.execute("SELECT events_json FROM calendar_snapshot WHERE id = 1").fetchone()
    if row is not None and row["events_json"] == new_serialized:
        return False
    conn.execute(
        "INSERT INTO calendar_snapshot (id, events_json, fetched_at_utc) VALUES (1, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET events_json = excluded.events_json, fetched_at_utc = excluded.fetched_at_utc",
        (new_serialized, fetched_at_utc.isoformat()),
    )
    conn.commit()
    return True


def upsert_event_history(
    conn: sqlite3.Connection,
    event,  # EconomicEvent — duck-typed, same reasoning as _event_to_dict()
    surprise_direction: Optional[str],
    now: dt.datetime,
) -> None:
    """
    Records this event occurrence's forecast/previous, filling in
    actual/surprise_direction once available without ever blanking a
    previously-recorded actual on a later, stale re-fetch that hasn't
    caught up yet (the `WHERE excluded.actual IS NOT NULL` guard below —
    SQLite's ON CONFLICT DO UPDATE has no per-column conditional syntax,
    so the WHERE clause on the whole UPDATE governs whether the actual/
    surprise_direction pair updates at all; forecast/previous are
    harmless to re-write identically every time since they don't change
    after an event first appears on the calendar).
    """
    conn.execute(
        """
        INSERT INTO event_history
            (event_title, event_time_utc, forecast, previous, actual, surprise_direction, recorded_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_title, event_time_utc) DO UPDATE SET
            actual = excluded.actual,
            surprise_direction = excluded.surprise_direction,
            updated_at_utc = excluded.updated_at_utc
        WHERE excluded.actual IS NOT NULL
        """,
        (
            event.title, event.event_time_utc.isoformat(), event.forecast, event.previous,
            event.actual, surprise_direction, now.isoformat(), now.isoformat(),
        ),
    )
    conn.commit()


def get_event_history(conn: sqlite3.Connection, event_title: str, limit: int = 6) -> list[EventHistoryRow]:
    """Past occurrences of this event title, most recent first, capped at `limit`. Empty list if none recorded yet."""
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction "
        "FROM event_history WHERE event_title = ? ORDER BY event_time_utc DESC LIMIT ?",
        (event_title, limit),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]
