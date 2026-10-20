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
    reality_mismatch INTEGER,
    polarity TEXT,
    country TEXT,
    us_link TEXT,
    capped_no_us_link INTEGER,
    original_severity TEXT,
    first_published_utc TEXT
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

CREATE TABLE IF NOT EXISTS provider_cooldown (
    provider TEXT PRIMARY KEY,
    until_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classifier_outage_notices (
    utc_date TEXT PRIMARY KEY,
    sent_at_utc TEXT NOT NULL,
    detail TEXT
);
"""
# No index on the B2 shock_alerts columns may live in _SCHEMA: it runs
# before _migrate_shock_alert_columns() on an old DB, where those columns
# don't exist yet, so the CREATE INDEX would fail.

# B2 (2026-10-21) columns, all nullable -- NULL means "unknown" and every
# reader keeps pre-B2 behaviour for it (no cap, age derived from sources[0]).
_SHOCK_ALERT_ADDED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("polarity", "TEXT"),
    ("country", "TEXT"),
    ("us_link", "TEXT"),
    ("capped_no_us_link", "INTEGER"),
    ("original_severity", "TEXT"),
    ("first_published_utc", "TEXT"),
)

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
    polarity: Optional[str] = None
    country: Optional[str] = None
    us_link: Optional[str] = None
    capped_no_us_link: Optional[bool] = None
    original_severity: Optional[str] = None
    first_published_utc: Optional[dt.datetime] = None


def _migrate_shock_alert_columns(conn: sqlite3.Connection) -> None:
    """
    Same reasoning as scoring/backtest_store.py's column migrations --
    CREATE TABLE IF NOT EXISTS doesn't retroactively add a column to the
    live shock_alerts.db. Unlike those, two processes (the 2-minute poller
    and the webapp) can open the same old DB at once: both read the old
    PRAGMA, one ALTER wins and the other gets "duplicate column name".
    That one error means the column is there, so it is swallowed; any
    other OperationalError is real and re-raised.
    """
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(shock_alerts)").fetchall()}
    for name, sql_type in _SHOCK_ALERT_ADDED_COLUMNS:
        if name in existing_columns:
            continue
        try:
            conn.execute(f"ALTER TABLE shock_alerts ADD COLUMN {name} {sql_type}")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc):
                raise
    conn.commit()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # Mirrors webapp/store.py's get_connection() pattern exactly: resolve
    # inside the body (not a default arg) so tests can pass ":memory:" or
    # a patched path, row_factory for name-based access, and a per-path
    # ready-cache so idempotent CREATE TABLE IF NOT EXISTS doesn't re-run
    # on every call. ":memory:" is never cached -- each call creates a
    # genuinely separate empty DB.
    # The cache is per process, so the 2-minute poller migrates on its first tick after the merge.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if path == ":memory:":
        conn.executescript(_SCHEMA)
        _migrate_shock_alert_columns(conn)
        return conn
    path_key = str(Path(path).resolve())
    if path_key not in _schema_ready_paths:
        conn.executescript(_SCHEMA)
        _migrate_shock_alert_columns(conn)
        _schema_ready_paths.add(path_key)
    return conn


def _parse_utc(value: str) -> dt.datetime:
    """ISO string -> aware datetime; a naive value is treated as UTC."""
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _first_source_published(sources: list[dict]) -> Optional[dt.datetime]:
    """
    Fallback for pre-B2 rows whose first_published_utc column is NULL.
    sources[0] is the source present at detection (append_source only
    appends), so it is the right one -- not the min across sources.
    None when the data is missing or garbage rather than crashing a reader.
    """
    try:
        return _parse_utc(sources[0]["published_utc"])
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def _row_to_shock_alert(d: dict) -> ShockAlertRow:
    sources = json.loads(d["sources_json"])
    if d["first_published_utc"]:
        first_published_utc = _parse_utc(d["first_published_utc"])
    else:
        first_published_utc = _first_source_published(sources)
    return ShockAlertRow(
        id=d["id"],
        headline=d["headline"],
        sources=sources,
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
        polarity=d["polarity"],
        country=d["country"],
        us_link=d["us_link"],
        capped_no_us_link=bool(d["capped_no_us_link"]) if d["capped_no_us_link"] is not None else None,
        original_severity=d["original_severity"],
        first_published_utc=first_published_utc,
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
    *,
    polarity: Optional[str] = None,
    country: Optional[str] = None,
    us_link: Optional[str] = None,
    capped_no_us_link: Optional[bool] = None,
    original_severity: Optional[str] = None,
) -> int:
    """
    Inserts a new shock_alerts row with one initial source; returns the new row's id.
    first_published_utc is always the detection source's published time --
    at detection the alert has exactly one source, so it is the earliest.
    """
    sources = [{"source": source, "url": url, "published_utc": published_utc.isoformat()}]
    cur = conn.execute(
        "INSERT INTO shock_alerts (headline, sources_json, detected_at_utc, category, severity, "
        "classification_method, rationale, affected_symbols_json, polarity, country, us_link, "
        "capped_no_us_link, original_severity, first_published_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (headline, json.dumps(sources), detected_at_utc.isoformat(), category, severity,
         classification_method, rationale, json.dumps(affected_symbols), polarity, country, us_link,
         None if capped_no_us_link is None else int(capped_no_us_link), original_severity,
         published_utc.isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def update_alert_assessment(
    conn: sqlite3.Connection,
    alert_id: int,
    *,
    severity: str,
    polarity: Optional[str],
    country: Optional[str],
    us_link: Optional[str],
    capped_no_us_link: bool,
    original_severity: str,
    affected_symbols: list[dict],
) -> None:
    """
    Rewrites an alert's whole assessment in one statement -- used by
    poll_once.py when a corroborating article lifts the no-US-link cap,
    so the severity, the cap flag and the leans can never disagree (a
    High left carrying the capped alert's stale lean-less symbols).
    Sources and first_published_utc are detection-time facts and are
    left alone.
    """
    conn.execute(
        "UPDATE shock_alerts SET severity = ?, polarity = ?, country = ?, us_link = ?, "
        "capped_no_us_link = ?, original_severity = ?, affected_symbols_json = ? WHERE id = ?",
        (severity, polarity, country, us_link, int(capped_no_us_link), original_severity,
         json.dumps(affected_symbols), alert_id),
    )
    conn.commit()


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


def get_provider_cooldown_until(conn: sqlite3.Connection, provider: str) -> Optional[dt.datetime]:
    """When `provider` may be tried again, or None if it has no recorded cooldown."""
    row = conn.execute("SELECT until_utc FROM provider_cooldown WHERE provider = ?", (provider,)).fetchone()
    if row is None:
        return None
    return dt.datetime.fromisoformat(row["until_utc"])


def set_provider_cooldown(conn: sqlite3.Connection, provider: str, until_utc: dt.datetime) -> None:
    """
    Persisted (not in-process) because poll_once.py is a fresh process every
    scheduler tick -- an in-memory flag would forget a dead provider and
    pay its full timeout again on the very next cycle.
    """
    conn.execute(
        "INSERT INTO provider_cooldown (provider, until_utc) VALUES (?, ?) "
        "ON CONFLICT(provider) DO UPDATE SET until_utc = excluded.until_utc",
        (provider, until_utc.isoformat()),
    )
    conn.commit()


def outage_notice_sent(conn: sqlite3.Connection, utc_date: dt.date) -> bool:
    """Whether the 'classifier down' Telegram notice already went out on this UTC day."""
    row = conn.execute(
        "SELECT 1 FROM classifier_outage_notices WHERE utc_date = ?", (utc_date.isoformat(),)
    ).fetchone()
    return row is not None


def record_outage_notice(conn: sqlite3.Connection, utc_date: dt.date, sent_at_utc: dt.datetime, detail: str) -> None:
    """
    Marks the day's outage notice as sent -- call only after the send
    succeeded, so a failed send leaves the day open for a retry. INSERT OR
    IGNORE keeps it at one row per UTC day even if two ticks race.
    """
    conn.execute(
        "INSERT OR IGNORE INTO classifier_outage_notices (utc_date, sent_at_utc, detail) VALUES (?, ?, ?)",
        (utc_date.isoformat(), sent_at_utc.isoformat(), detail),
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
