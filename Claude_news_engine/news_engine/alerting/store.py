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

from config.settings import INCIDENT_URL_WINDOW_HOURS
from data_layer.news_feed import normalize_url

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
    first_published_utc TEXT,
    incident_id INTEGER,
    incident_role TEXT,
    incident_rule TEXT
);

CREATE TABLE IF NOT EXISTS shock_near_misses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    closest_category TEXT,
    near_miss_score REAL,
    seen_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_near_miss_headline_seen ON shock_near_misses(headline, seen_at_utc);
CREATE INDEX IF NOT EXISTS idx_near_miss_seen ON shock_near_misses(seen_at_utc);

CREATE TABLE IF NOT EXISTS poll_cursor (
    source TEXT PRIMARY KEY,
    last_seen_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_health (
    source TEXT PRIMARY KEY,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    failing_since_utc TEXT,
    backoff_until_utc TEXT,
    last_success_utc TEXT,
    last_failure_utc TEXT,
    last_error TEXT
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

CREATE TABLE IF NOT EXISTS seen_urls (
    url TEXT NOT NULL,
    alert_id INTEGER NOT NULL,
    first_seen_utc TEXT NOT NULL,
    first_published_utc TEXT,
    PRIMARY KEY (url, alert_id)
);

CREATE INDEX IF NOT EXISTS idx_seen_urls_first_seen ON seen_urls(first_seen_utc);
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
    # B7 (2026-10-22): incident linking. NULL incident_id = the alert is its own incident
    # (every pre-B7 row); NULL incident_role = the incident's first alert.
    ("incident_id", "INTEGER"),
    ("incident_role", "TEXT"),
    ("incident_rule", "TEXT"),
)

# B7: roles of a non-first alert on an incident -- "follow_up" is stored and labelled with no push,
# "update" is pushed once (severity rise or direction flip).
INCIDENT_ROLES: tuple[str, ...] = ("follow_up", "update")
SEEN_URL_RETENTION = dt.timedelta(hours=INCIDENT_URL_WINDOW_HOURS)
SEEN_URL_PRUNE_BATCH = 500  # rows deleted per call, same bound as the near-miss prune

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
    incident_id: Optional[int] = None  # B7: the reader fills the row's own id when the column is NULL
    incident_role: Optional[str] = None  # None = first alert of its incident, else one of INCIDENT_ROLES
    incident_rule: Optional[str] = None  # "url" | "entity:<a,b>" -- why the alert was linked


@dataclass
class SeenUrl:
    """B7 K9: one sighting of a normalized URL on an alert; first_published_utc is that alert's first publication time."""
    url: str
    alert_id: int
    first_seen_utc: dt.datetime
    first_published_utc: Optional[dt.datetime]


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
        # B7: backfill URL memory exactly once, when seen_urls is first created. Two processes racing
        # here both backfill; INSERT OR IGNORE makes that harmless.
        had_seen_urls = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'seen_urls'").fetchone() is not None
        conn.executescript(_SCHEMA)
        _migrate_shock_alert_columns(conn)
        if not had_seen_urls:
            _backfill_seen_urls(conn, dt.datetime.now(dt.timezone.utc))
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
        incident_id=d["incident_id"] if d["incident_id"] is not None else d["id"],
        incident_role=d["incident_role"],
        incident_rule=d["incident_rule"],
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
    incident_id: Optional[int] = None,
    incident_role: Optional[str] = None,
    incident_rule: Optional[str] = None,
    first_published_utc: Optional[dt.datetime] = None,
) -> int:
    """
    Inserts a new shock_alerts row with one initial source; returns the new row's id.
    first_published_utc defaults to the detection source's published time --
    at detection the alert has exactly one source, so it is the earliest.
    B7 (2026-10-22): a caller may pass the URL-memory first publication of a re-stamped URL
    (the source entry keeps the article's own time). incident_id None makes the new row its
    own incident (id set in the same transaction); a follow-up passes its incident root's id.
    """
    sources = [{"source": source, "url": url, "published_utc": published_utc.isoformat()}]
    cur = conn.execute(
        "INSERT INTO shock_alerts (headline, sources_json, detected_at_utc, category, severity, "
        "classification_method, rationale, affected_symbols_json, polarity, country, us_link, "
        "capped_no_us_link, original_severity, first_published_utc, incident_id, incident_role, incident_rule) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (headline, json.dumps(sources), detected_at_utc.isoformat(), category, severity,
         classification_method, rationale, json.dumps(affected_symbols), polarity, country, us_link,
         None if capped_no_us_link is None else int(capped_no_us_link), original_severity,
         (first_published_utc or published_utc).isoformat(), incident_id, incident_role, incident_rule),
    )
    if incident_id is None:
        conn.execute("UPDATE shock_alerts SET incident_id = id WHERE id = ?", (cur.lastrowid,))
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


def list_incident_alerts(conn: sqlite3.Connection, incident_id: int) -> list[ShockAlertRow]:
    """
    B7: every alert on an incident in detection order. A legacy row with a NULL incident_id is
    its own incident, so asking for its id returns just that row.
    """
    rows = conn.execute(
        "SELECT * FROM shock_alerts WHERE incident_id = ? OR (incident_id IS NULL AND id = ?) "
        "ORDER BY detected_at_utc",
        (incident_id, incident_id),
    ).fetchall()
    return [_row_to_shock_alert(dict(r)) for r in rows]


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


@dataclass
class SourceHealth:
    """Per-feed failure streak and backoff state (B4 O5); one row per RSS feed."""
    source: str
    consecutive_failures: int
    failing_since_utc: Optional[dt.datetime]
    backoff_until_utc: Optional[dt.datetime]
    last_success_utc: Optional[dt.datetime]
    last_failure_utc: Optional[dt.datetime]
    last_error: Optional[str]


def _row_to_source_health(row: sqlite3.Row) -> SourceHealth:
    def _opt(value: Optional[str]) -> Optional[dt.datetime]:
        return _parse_utc(value) if value else None

    return SourceHealth(
        source=row["source"],
        consecutive_failures=row["consecutive_failures"],
        failing_since_utc=_opt(row["failing_since_utc"]),
        backoff_until_utc=_opt(row["backoff_until_utc"]),
        last_success_utc=_opt(row["last_success_utc"]),
        last_failure_utc=_opt(row["last_failure_utc"]),
        last_error=row["last_error"],
    )


def get_source_health(conn: sqlite3.Connection, source: str) -> Optional[SourceHealth]:
    row = conn.execute("SELECT * FROM source_health WHERE source = ?", (source,)).fetchone()
    return _row_to_source_health(row) if row is not None else None


def list_source_health(conn: sqlite3.Connection) -> list[SourceHealth]:
    rows = conn.execute("SELECT * FROM source_health ORDER BY source").fetchall()
    return [_row_to_source_health(r) for r in rows]


def record_source_success(conn: sqlite3.Connection, source: str, now: dt.datetime) -> Optional[SourceHealth]:
    """
    Resets the feed's failure streak. Returns the previous row when it had
    failures (so the caller can log the recovery once), else None.
    """
    previous = get_source_health(conn, source)
    conn.execute(
        "INSERT INTO source_health (source, consecutive_failures, last_success_utc) VALUES (?, 0, ?) "
        "ON CONFLICT(source) DO UPDATE SET consecutive_failures = 0, failing_since_utc = NULL, "
        "backoff_until_utc = NULL, last_success_utc = excluded.last_success_utc",
        (source, now.isoformat()),
    )
    conn.commit()
    if previous is not None and previous.consecutive_failures > 0:
        return previous
    return None


def record_source_failure(
    conn: sqlite3.Connection, source: str, now: dt.datetime, error: str,
    backoff_until: Optional[dt.datetime],
) -> SourceHealth:
    """Counts one more failure; the first failure of a streak fixes failing_since_utc."""
    previous = get_source_health(conn, source)
    ongoing = previous is not None and previous.consecutive_failures > 0
    failures = (previous.consecutive_failures if ongoing else 0) + 1
    failing_since = previous.failing_since_utc if ongoing and previous.failing_since_utc else now
    conn.execute(
        "INSERT INTO source_health (source, consecutive_failures, failing_since_utc, backoff_until_utc, "
        "last_failure_utc, last_error) VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(source) DO UPDATE SET consecutive_failures = excluded.consecutive_failures, "
        "failing_since_utc = excluded.failing_since_utc, backoff_until_utc = excluded.backoff_until_utc, "
        "last_failure_utc = excluded.last_failure_utc, last_error = excluded.last_error",
        (
            source, failures, failing_since.isoformat(),
            backoff_until.isoformat() if backoff_until else None, now.isoformat(), (error or "")[:300],
        ),
    )
    conn.commit()
    return get_source_health(conn, source)


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


NEAR_MISS_REPEAT_WINDOW = dt.timedelta(hours=24)  # same headline is logged at most once per window
NEAR_MISS_RETENTION = dt.timedelta(days=30)
NEAR_MISS_PRUNE_BATCH = 500  # rows deleted per call, so one poll cycle never runs a huge DELETE


def record_near_miss(
    conn: sqlite3.Connection, headline: str, closest_category: Optional[str],
    near_miss_score: Optional[float], seen_at_utc: Optional[dt.datetime] = None,
) -> Optional[int]:
    """
    Rolling audit log for taxonomy tuning -- never read by the live alerting path itself.
    Returns None (nothing inserted) when the same headline was already logged in the last 24h:
    feeds keep a story for hours, so every 2-minute cycle used to re-log it.
    """
    seen_at_utc = seen_at_utc or dt.datetime.now(dt.timezone.utc)
    repeat = conn.execute(
        "SELECT 1 FROM shock_near_misses WHERE headline = ? AND julianday(seen_at_utc) >= julianday(?) LIMIT 1",
        (headline, (seen_at_utc - NEAR_MISS_REPEAT_WINDOW).isoformat()),
    ).fetchone()
    if repeat is not None:
        return None
    cur = conn.execute(
        "INSERT INTO shock_near_misses (headline, closest_category, near_miss_score, seen_at_utc) VALUES (?, ?, ?, ?)",
        (headline, closest_category, near_miss_score, seen_at_utc.isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def prune_near_misses(
    conn: sqlite3.Connection, now: dt.datetime, retention: dt.timedelta = NEAR_MISS_RETENTION,
    max_rows: int = NEAR_MISS_PRUNE_BATCH,
) -> int:
    """
    Deletes at most `max_rows` of the oldest near-misses past retention and returns the count.
    Bounded on purpose (runs inside the 2-minute poll); a backlog drains over a few cycles.
    One of two DELETEs in the alerting store (the other is prune_seen_urls).
    """
    cutoff = (now - retention).isoformat()
    cur = conn.execute(
        "DELETE FROM shock_near_misses WHERE id IN ("
        "SELECT id FROM shock_near_misses WHERE julianday(seen_at_utc) < julianday(?) "
        "ORDER BY seen_at_utc LIMIT ?)",
        (cutoff, max_rows),
    )
    conn.commit()
    return cur.rowcount


def remember_url(
    conn: sqlite3.Connection, url: str, alert_id: int, seen_at_utc: dt.datetime,
    published_utc: Optional[dt.datetime],
) -> None:
    """
    B7 K9: records that `url` is attached to alert `alert_id`. The key is the B6 normalized URL;
    a blank URL is a no-op. INSERT OR IGNORE keeps the FIRST sighting per (url, alert), so a feed
    re-stamping the same URL never moves its first-seen or first-published time.
    """
    key = normalize_url(url)
    if not key:
        return
    conn.execute(
        "INSERT OR IGNORE INTO seen_urls (url, alert_id, first_seen_utc, first_published_utc) VALUES (?, ?, ?, ?)",
        (key, alert_id, seen_at_utc.isoformat(), published_utc.isoformat() if published_utc else None),
    )
    conn.commit()


def lookup_seen_url(conn: sqlite3.Connection, url: str, since_utc: dt.datetime) -> list[SeenUrl]:
    """B7 K9: sightings of `url` first seen at or after `since_utc`, newest first-seen first."""
    key = normalize_url(url)
    if not key:
        return []
    rows = conn.execute(
        "SELECT * FROM seen_urls WHERE url = ? AND julianday(first_seen_utc) >= julianday(?) "
        "ORDER BY julianday(first_seen_utc) DESC",
        (key, since_utc.isoformat()),
    ).fetchall()
    return [
        SeenUrl(
            url=r["url"], alert_id=r["alert_id"], first_seen_utc=_parse_utc(r["first_seen_utc"]),
            first_published_utc=_parse_utc(r["first_published_utc"]) if r["first_published_utc"] else None,
        )
        for r in rows
    ]


def prune_seen_urls(
    conn: sqlite3.Connection, now: dt.datetime, retention: dt.timedelta = SEEN_URL_RETENTION,
    max_rows: int = SEEN_URL_PRUNE_BATCH,
) -> int:
    """
    B7: deletes at most `max_rows` of the oldest sightings past retention and returns the count.
    Bounded like prune_near_misses (runs inside the 2-minute poll); a backlog drains over a few cycles.
    """
    cutoff = (now - retention).isoformat()
    cur = conn.execute(
        "DELETE FROM seen_urls WHERE rowid IN ("
        "SELECT rowid FROM seen_urls WHERE julianday(first_seen_utc) < julianday(?) "
        "ORDER BY first_seen_utc LIMIT ?)",
        (cutoff, max_rows),
    )
    conn.commit()
    return cur.rowcount


def _backfill_seen_urls(conn: sqlite3.Connection, now: dt.datetime) -> int:
    """
    B7: one-time URL memory for alerts already stored when seen_urls is first created, so the first
    poll after deploy can already recognise a re-stamped URL. Covers alerts detected in the last 72 h:
    sources[0] was seen at detection; later sources were appended after their own publication, so
    their published time is the best available first-seen. Returns rows inserted.
    """
    cutoff = (now - SEEN_URL_RETENTION).isoformat()
    inserted = 0
    rows = conn.execute(
        "SELECT id, sources_json, detected_at_utc FROM shock_alerts WHERE julianday(detected_at_utc) >= julianday(?)", (cutoff,),
    ).fetchall()
    for row in rows:
        try:
            sources = json.loads(row["sources_json"])
        except (TypeError, ValueError):
            continue
        for index, source in enumerate(sources):
            key = normalize_url(source.get("url") or "") if isinstance(source, dict) else ""
            if not key:
                continue
            published = source.get("published_utc")
            first_seen = row["detected_at_utc"] if index == 0 else (published or row["detected_at_utc"])
            cur = conn.execute(
                "INSERT OR IGNORE INTO seen_urls (url, alert_id, first_seen_utc, first_published_utc) VALUES (?, ?, ?, ?)",
                (key, row["id"], first_seen, published),
            )
            inserted += cur.rowcount
    conn.commit()
    return inserted


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
