"""
SQLite persistence for the dashboard — four concerns in one file since
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
  4. macro_calendar — the month-ahead "macro view" seeded from FRED
     (scripts/refresh_macro_calendar.py), display-only, NOT wired into
     scoring. FF's own calendar_snapshot is the "micro lens" that
     confirms/corrects a macro row's exact time once FF's near-term feed
     actually reaches that occurrence — see
     confirm_macro_calendar_event(), called from webapp/scheduler.py's
     run_scoring_cycle() on every real FF fetch, and
     docs/macro-calendar-design-2026-08-16.md for the full design.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import EVENT_SURPRISE_DIRECTION

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
    source TEXT NOT NULL DEFAULT 'live',
    impact TEXT,
    country TEXT,
    UNIQUE(event_title, event_time_utc)
);
CREATE TABLE IF NOT EXISTS macro_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_date TEXT NOT NULL,             -- YYYY-MM-DD, FRED's date-only granularity
    estimated_time_utc TEXT,              -- full ISO datetime, best-guess from event_history's most recent time-of-day for this title; NULL if no history exists yet
    time_source TEXT NOT NULL,            -- 'history_derived' | 'unconfirmed'
    confirmed INTEGER NOT NULL DEFAULT 0, -- 1 once FF's own feed has reached this exact occurrence
    confirmed_event_time_utc TEXT,        -- FF's real exact time, set only once confirmed
    source TEXT NOT NULL DEFAULT 'fred',
    recorded_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    UNIQUE(event_title, event_date)
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
    source: str
    impact: Optional[str] = None
    country: Optional[str] = None  # None = genuinely unknown (legacy row, never confirmed) — never guessed


@dataclass
class MacroCalendarRow:
    event_title: str
    event_date: str                        # YYYY-MM-DD
    estimated_time_utc: Optional[str]
    time_source: str                       # 'history_derived' | 'unconfirmed'
    confirmed: bool
    confirmed_event_time_utc: Optional[str]
    source: str

    @property
    def display_time_utc(self) -> Optional[str]:
        """
        The best time to actually show for this macro row — FF's
        confirmed exact time if the micro lens has reached it,
        otherwise the history-derived estimate, otherwise None (date
        known, time genuinely unconfirmed — never fabricated).
        """
        return self.confirmed_event_time_utc or self.estimated_time_utc


def _migrate_add_source_column(conn: sqlite3.Connection) -> None:
    """
    CREATE TABLE IF NOT EXISTS does not retroactively add a column to an
    already-created DB file — every DB created before this change lacks
    `source` on event_history. Adds it, defaulting existing (pre-backfill)
    rows to 'live' (their implicit meaning before this column existed).
    Safe to call on a fresh DB where the column already exists via
    CREATE TABLE — PRAGMA table_info is checked first, not a bare ALTER
    wrapped in try/except, so a genuine unrelated OperationalError isn't
    silently swallowed.
    """
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(event_history)").fetchall()}
    if "source" not in existing_columns:
        conn.execute("ALTER TABLE event_history ADD COLUMN source TEXT NOT NULL DEFAULT 'live'")
        conn.commit()


def _migrate_add_impact_column(conn: sqlite3.Connection) -> None:
    """
    Same reasoning as _migrate_add_source_column: CREATE TABLE IF NOT
    EXISTS doesn't retroactively add a column to an already-created DB
    file. Existing rows read back impact=None (genuinely unknown — never
    guessed) until something backfills it, and exactly what self-heals
    depends on the row's state at migration time:

    - A legacy row that's already RESOLVED (actual already non-NULL)
      keeps impact=None permanently. upsert_event_history()'s UPDATE
      branch is gated on a single WHERE (`excluded.actual IS NOT NULL
      AND event_history.actual IS NULL`) that governs the whole SET
      clause, impact included — SQLite's ON CONFLICT DO UPDATE has no
      per-column conditional, so once `event_history.actual` is already
      non-NULL that WHERE can never be true again for this row, and
      impact never gets touched, on any future call, for the life of the
      row. This is fine: a resolved row falls out of the 7-day recently-
      resolved retention window and is never read again after that.

    - A legacy row that's still PENDING (actual still NULL) self-heals
      impact, but only on the specific upsert_event_history() call that
      finally RESOLVES it (supplies a real `event.actual` for the first
      time) — that's the only call shape that satisfies the WHERE above.
      A call that still supplies no actual (event.actual is None) leaves
      the WHERE false and is a complete no-op on this row, impact
      included; it does not partially apply. See upsert_event_history()'s
      own docstring for the full COALESCE(event_history.impact,
      excluded.impact) reasoning.
    """
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(event_history)").fetchall()}
    if "impact" not in existing_columns:
        conn.execute("ALTER TABLE event_history ADD COLUMN impact TEXT")
        conn.commit()


def _migrate_add_country_column(conn: sqlite3.Connection) -> None:
    """
    Same reasoning and self-healing behavior as _migrate_add_impact_column()
    — see that docstring for the full COALESCE/resolution-gating mechanics,
    identical here. Added 2026-09-03 (root-cause fix): event_history had no
    country dimension at all, so foreign releases sharing a generic FF
    title with a US one (e.g. Australia's own "CPI m/m", the UK's own
    "Retail Sales m/m"/"Unemployment Rate") could be — and, confirmed live,
    WERE — silently miscounted as USD candidates by any title-only lookup
    (get_events_with_stale_missing_actual(), and more seriously
    scoring.probability_engine.get_precursor_events_for(), which feeds
    directly into automated scoring with no human review). New rows are
    populated at INSERT time from the real EconomicEvent.country the
    scheduler already only ever writes as "USD" (see
    webapp/scheduler.py's calendar_events, already properly USD-scoped —
    the contamination in legacy rows came from an OLDER, since-replaced
    process instance, confirmed by cross-referencing FF's live feed's own
    country tags for known-foreign titles, not from a live bug in the
    current write path). Legacy rows read back country=None (genuinely
    unknown) until self-healed on their next resolving call, or backfilled
    for known-USD-by-construction sources — see
    scripts/migrate_country_backfill.py.
    """
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(event_history)").fetchall()}
    if "country" not in existing_columns:
        conn.execute("ALTER TABLE event_history ADD COLUMN country TEXT")
        conn.commit()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # db_path resolved inside the body (not as a default arg value) so
    # tests can patch module-level DB_PATH and have it take effect.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate_add_source_column(conn)
    _migrate_add_impact_column(conn)
    _migrate_add_country_column(conn)
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


def get_latest_two_bulk(
    conn: sqlite3.Connection, symbols: list[str], event_titles: list[str],
) -> dict[tuple[str, str], list[PredictionRun]]:
    """
    Batched version of get_latest_two() — one query for the whole
    `symbols` x `event_titles` cross product, instead of webapp/app.py's
    /api/predictions issuing one query per (symbol, event) pair (an N+1
    pattern that scaled with symbols * events, every 60s poll). Returns a
    dict keyed by (symbol, event_title); a pair with no rows is simply
    absent from the dict — callers already treat that the same as an
    empty list. Same most-recent-first, `id`-breaks-ties ordering as
    get_latest_two(), applied per group via the ORDER BY below.
    """
    if not symbols or not event_titles:
        return {}
    symbol_placeholders = ",".join("?" for _ in symbols)
    title_placeholders = ",".join("?" for _ in event_titles)
    rows = conn.execute(
        f"SELECT * FROM prediction_runs WHERE symbol IN ({symbol_placeholders}) "
        f"AND event_title IN ({title_placeholders}) "
        "ORDER BY symbol, event_title, scored_at_utc DESC, id DESC",
        (*symbols, *event_titles),
    ).fetchall()
    grouped: dict[tuple[str, str], list[PredictionRun]] = {}
    for row in rows:
        run = PredictionRun(**dict(row))
        bucket = grouped.setdefault((run.symbol, run.event_title), [])
        if len(bucket) < 2:  # rows already arrive most-recent-first per group, per the ORDER BY above
            bucket.append(run)
    return grouped


def get_event_history_bulk(
    conn: sqlite3.Connection, event_titles: list[str], limit: int = 6,
) -> dict[str, list[EventHistoryRow]]:
    """
    Batched version of get_event_history() — one query covering every
    title in `event_titles`, instead of one query per title. Returns a
    dict keyed by event_title; a title with no rows is simply absent.
    Same most-recent-first ordering and per-title `limit` cap as
    get_event_history().
    """
    if not event_titles:
        return {}
    placeholders = ",".join("?" for _ in event_titles)
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, impact, country "
        f"FROM event_history WHERE event_title IN ({placeholders}) "
        "ORDER BY event_title, event_time_utc DESC",
        event_titles,
    ).fetchall()
    grouped: dict[str, list[EventHistoryRow]] = {}
    for row in rows:
        history_row = EventHistoryRow(**dict(row))
        bucket = grouped.setdefault(history_row.event_title, [])
        if len(bucket) < limit:
            bucket.append(history_row)
    return grouped


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
    source: str = "live",
) -> None:
    """
    Records this event occurrence's forecast/previous, filling in
    actual/surprise_direction ONLY ONCE — the first call that supplies a
    real actual wins, and every later call leaves actual/surprise_direction/
    source untouched, even if it supplies a different real actual (e.g.
    Forex Factory finally posting its own number after the FRED fallback
    already filled the row in) or none at all (a stale re-fetch must never
    blank a previously-recorded actual). Each of those three columns is
    gated by its own `CASE WHEN event_history.actual IS NULL THEN
    excluded.<col> ELSE event_history.<col> END` (2026-09-04 fix — see
    below for what this replaced).

    forecast/previous/impact/country are NOT first-writer-wins — every
    call updates them from the caller's freshest data, always (forecast/
    previous straight from `excluded`; impact/country via
    COALESCE(event_history.col, excluded.col), which keeps whatever's
    already stored and only fills in a legacy NULL, never overwriting a
    real value with another).

    2026-09-04 root-cause fix: this used to be one blanket `WHERE
    excluded.actual IS NOT NULL AND event_history.actual IS NULL` guarding
    the ENTIRE UPDATE (SQLite's ON CONFLICT DO UPDATE has no per-column
    conditional syntax, so a single WHERE governs whether the whole SET
    list applies at all). That silently froze forecast/previous/impact/
    country at whatever the row's FIRST-ever write captured, for as long
    as the event stayed pending — including forecast, which Forex Factory
    does revise between an event's first calendar appearance and its
    release. Confirmed live: 2026-09-04's Non-Farm Employment Change and
    Unemployment Rate rows were frozen at a stale/wrong forecast from an
    earlier fetch while every later re-fetch (with FF's corrected number)
    silently no-op'd. Per-column CASE/COALESCE expressions replace the
    blanket WHERE so each column's own update rule governs independently
    — actual/surprise_direction/source keep their exact first-writer-wins
    semantics, forecast/previous/impact/country now genuinely self-heal on
    every pending re-fetch instead of only on the one call that happens to
    also resolve actual.
    """
    conn.execute(
        """
        INSERT INTO event_history
            (event_title, event_time_utc, forecast, previous, actual, surprise_direction, recorded_at_utc, updated_at_utc, source, impact, country)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_title, event_time_utc) DO UPDATE SET
            forecast = excluded.forecast,
            previous = excluded.previous,
            actual = CASE WHEN event_history.actual IS NULL THEN excluded.actual ELSE event_history.actual END,
            surprise_direction = CASE WHEN event_history.actual IS NULL THEN excluded.surprise_direction ELSE event_history.surprise_direction END,
            updated_at_utc = excluded.updated_at_utc,
            source = CASE WHEN event_history.actual IS NULL THEN excluded.source ELSE event_history.source END,
            impact = COALESCE(event_history.impact, excluded.impact),
            country = COALESCE(event_history.country, excluded.country)
        """,
        (
            event.title, event.event_time_utc.isoformat(), event.forecast, event.previous,
            event.actual, surprise_direction, now.isoformat(), now.isoformat(), source, event.impact, event.country,
        ),
    )
    conn.commit()


def get_event_history(conn: sqlite3.Connection, event_title: str, limit: int = 6) -> list[EventHistoryRow]:
    """Past occurrences of this event title, most recent first, capped at `limit`. Empty list if none recorded yet."""
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, impact, country "
        "FROM event_history WHERE event_title = ? ORDER BY event_time_utc DESC LIMIT ?",
        (event_title, limit),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]


def get_resolved_event_history(conn: sqlite3.Connection, limit: int = 200) -> list[EventHistoryRow]:
    """
    Every RESOLVED event occurrence (actual IS NOT NULL) across ALL event
    titles, most recent first, capped at `limit`. Unlike get_event_history()
    (scoped to one title, includes pending occurrences), this is the
    cross-title, resolved-only query webapp/history.py's History tab needs
    for its numeric-forecast rows.
    """
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, impact, country "
        "FROM event_history WHERE actual IS NOT NULL ORDER BY event_time_utc DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]


def get_events_with_stale_missing_actual(
    conn: sqlite3.Connection, now: dt.datetime, grace_period_hours: float = 1.0,
) -> list[EventHistoryRow]:
    """
    Every event_history row whose actual is still NULL and whose
    event_time_utc is more than grace_period_hours in the past — a real
    candidate for the actuals-fallback enrichment pass. The grace period
    exists because Forex Factory's feed genuinely takes some time to
    publish an actual after release; searching too early would find
    nothing real and waste an agent's WebSearch budget. Lowered from 6h to
    1h (2026-09-02): FF has proven consistently unreliable at posting
    actuals promptly, and 6h left real gaps sitting unflagged for most of
    a trading session before an agent would even see them as candidates —
    1h is a tighter, still-reasonable margin past a genuine publish delay.

    Also excludes rows that are structurally text-only (forecast IS NULL
    AND previous IS NULL — e.g. "RBA Gov Bullock Speaks") using the same
    "never publishes a comparable number" concept get_text_only_resolved_
    events() encodes, just checked against `previous` instead of `actual`
    since `actual` is already guaranteed NULL by this query's own WHERE
    clause. Without this, a text-only event with an ever-NULL actual would
    perpetually re-qualify as a "stale missing actual" candidate — pure
    noise for the enrichment pass, since it will never have a number to go
    find.

    Also excludes titles absent from config.settings.EVENT_SURPRISE_DIRECTION.
    The scheduler (webapp/scheduler.py's run_scoring_cycle) now scopes
    event_history writes to calendar_events — USD, Low+ — not the full,
    unfiltered global FF feed, so a foreign-market event (German bond
    auctions, BRC Retail Sales Monitor, Cash Rate, ...) never gets an
    event_history row at all any more. This filter's remaining purpose is
    USD titles classify_surprise() still has no mapping for — even if an
    agent researched and filled one of those in, it would land with
    surprise_direction still NULL (classify_surprise() returns None for
    any title outside EVENT_SURPRISE_DIRECTION), so it can never count
    toward a trend or the History tab. Without this filter those titles
    are guaranteed-wasted WebSearch budget for the enrichment pass.

    Deliberately does NOT filter on country = 'USD' (2026-09-03): unlike
    scoring.probability_engine.get_precursor_events_for() (fully
    automated, no human review), a human researches this list's
    candidates via WebSearch before anything gets written — a legacy row
    with country still NULL (pre-migration, genuinely unresolved either
    way) stays a legitimate candidate for that manual review rather than
    being silently dropped. Title-only filtering already excludes the
    unambiguous country-prefixed foreign titles; a bare shared title
    (e.g. a stale legacy "CPI m/m" row that turns out to be foreign) is
    something the researching agent catches during WebSearch, same as
    any other cross-check in that workflow.
    """
    cutoff = (now - dt.timedelta(hours=grace_period_hours)).isoformat()
    known_titles = list(EVENT_SURPRISE_DIRECTION.keys())
    if not known_titles:
        return []
    placeholders = ",".join("?" for _ in known_titles)
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, country "
        "FROM event_history WHERE actual IS NULL AND event_time_utc < ? "
        "AND NOT (forecast IS NULL AND previous IS NULL) "
        f"AND event_title IN ({placeholders}) "
        "ORDER BY event_time_utc DESC",
        (cutoff, *known_titles),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]


def get_text_only_resolved_events(conn: sqlite3.Connection, now: Optional[dt.datetime] = None, limit: int = 200) -> list[EventHistoryRow]:
    """
    Past event occurrences that genuinely have NO forecast/actual figure
    at all (forecast IS NULL AND actual IS NULL) — e.g. FOMC Statement,
    FOMC Press Conference. Deliberately data-driven, not a check against
    PRINT_SURPRISE_LEXICON/EVENT_SURPRISE_DIRECTION: an event missing
    lexicon coverage today but that DOES have a real forecast (e.g. Core
    PPI m/m before it's added to the lexicon) is a config gap, not the
    same case as an event that structurally never publishes a number —
    only the latter belongs here.

    "Past" uses lexicographic ISO-8601 string comparison against `now`,
    same pattern get_predictions_awaiting_outcome() (scoring/backtest_store.py)
    already uses.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, country "
        "FROM event_history WHERE forecast IS NULL AND actual IS NULL AND event_time_utc <= ? "
        "ORDER BY event_time_utc DESC LIMIT ?",
        (now.isoformat(), limit),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]


def infer_event_time_of_day(conn: sqlite3.Connection, event_title: str) -> Optional[dt.time]:
    """
    Real-data basis for a macro-calendar row's time estimate: the
    time-of-day of this title's most recent RESOLVED (actual IS NOT NULL)
    event_history occurrence. Most scheduled US releases keep a stable
    time-of-day release slot (e.g. CPI/NFP at 12:30 UTC / 8:30am ET), so
    reusing the last real observed time is a genuine inference, not a
    fabrication — same "real data or absent" standard as every other
    inference in this project. Returns None if no resolved occurrence
    exists yet for this title (a title tracked for the first time, or
    never yet resolved) — callers must treat that as "time genuinely
    unknown," never defaulting to midnight or any other guessed value.
    """
    row = conn.execute(
        "SELECT event_time_utc FROM event_history WHERE event_title = ? AND actual IS NOT NULL "
        "ORDER BY event_time_utc DESC LIMIT 1",
        (event_title,),
    ).fetchone()
    if row is None:
        return None
    return dt.datetime.fromisoformat(row["event_time_utc"]).time()


def upsert_macro_calendar_event(
    conn: sqlite3.Connection,
    event_title: str,
    event_date: str,
    estimated_time_utc: Optional[str],
    time_source: str,
    now: dt.datetime,
    source: str = "fred",
) -> None:
    """
    Records/refreshes a macro-calendar row for this (title, date) pair.
    Never touches `confirmed`/`confirmed_event_time_utc` — those are
    owned exclusively by confirm_macro_calendar_event() (the FF "micro
    lens" reconciliation step), so a later macro refresh can never
    downgrade or overwrite a real FF-confirmed time.
    """
    conn.execute(
        """
        INSERT INTO macro_calendar
            (event_title, event_date, estimated_time_utc, time_source, confirmed, source, recorded_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, 0, ?, ?, ?)
        ON CONFLICT(event_title, event_date) DO UPDATE SET
            estimated_time_utc = excluded.estimated_time_utc,
            time_source = excluded.time_source,
            updated_at_utc = excluded.updated_at_utc
        """,
        (event_title, event_date, estimated_time_utc, time_source, source, now.isoformat(), now.isoformat()),
    )
    conn.commit()


def confirm_macro_calendar_event(
    conn: sqlite3.Connection,
    event_title: str,
    event_time_utc: dt.datetime,
    now: dt.datetime,
    tolerance_days: int = 2,
) -> bool:
    """
    The FF "micro lens" reconciliation step — called from
    webapp/scheduler.py's run_scoring_cycle() for every real event FF's
    feed returns. Finds the macro_calendar row for `event_title` whose
    event_date is within `tolerance_days` of event_time_utc's date and
    marks it confirmed with FF's real exact time — the macro row's
    date-only, history-derived estimate is superseded by real,
    FF-sourced ground truth the moment FF's own near-term feed actually
    reaches that occurrence. Returns True if a row was matched and
    confirmed, False if no macro row exists for this occurrence yet
    (normal — not every FF event necessarily has a prior FRED-sourced
    macro entry, e.g. Low-impact/foreign events FRED was never asked
    about). Idempotent: re-confirming an already-confirmed row with the
    same or a corrected time is harmless.
    """
    event_date = event_time_utc.date()
    rows = conn.execute(
        "SELECT event_date FROM macro_calendar WHERE event_title = ?",
        (event_title,),
    ).fetchall()
    match = next(
        (r["event_date"] for r in rows if abs((dt.date.fromisoformat(r["event_date"]) - event_date).days) <= tolerance_days),
        None,
    )
    if match is None:
        return False
    conn.execute(
        "UPDATE macro_calendar SET confirmed = 1, confirmed_event_time_utc = ?, updated_at_utc = ? "
        "WHERE event_title = ? AND event_date = ?",
        (event_time_utc.isoformat(), now.isoformat(), event_title, match),
    )
    conn.commit()
    return True


def get_macro_calendar_events(conn: sqlite3.Connection, start_date: str, end_date: str) -> list[MacroCalendarRow]:
    """Macro-calendar rows whose event_date falls within [start_date, end_date] (inclusive, both YYYY-MM-DD), ordered earliest first."""
    rows = conn.execute(
        "SELECT event_title, event_date, estimated_time_utc, time_source, confirmed, confirmed_event_time_utc, source "
        "FROM macro_calendar WHERE event_date BETWEEN ? AND ? ORDER BY event_date ASC",
        (start_date, end_date),
    ).fetchall()
    return [
        MacroCalendarRow(
            event_title=r["event_title"], event_date=r["event_date"],
            estimated_time_utc=r["estimated_time_utc"], time_source=r["time_source"],
            confirmed=bool(r["confirmed"]), confirmed_event_time_utc=r["confirmed_event_time_utc"],
            source=r["source"],
        )
        for r in rows
    ]
