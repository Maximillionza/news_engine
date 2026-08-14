"""
Persistence for the article-based backtest accumulator — a running log
of real predictions (made blind, before the event) and their real
confirmed outcomes (added later, via research). Separate from
webapp/store.py's essence-only prediction_runs table on purpose: this is
for the article-based pipeline (scoring/probability_engine.py), a
distinct concern from the dashboard's article-free scoring.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from scoring.probability_engine import Direction

DB_PATH = Path(__file__).parent / "backtest_log.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    scored_at_utc TEXT NOT NULL,
    probability REAL NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL NOT NULL,
    article_count INTEGER NOT NULL,
    contradiction_flag INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'live'
);
CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    actual_direction TEXT NOT NULL,
    actual_move_note TEXT NOT NULL,
    confirmed_at_utc TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'live',
    UNIQUE(event_title, instrument, event_time_utc)
);
CREATE TABLE IF NOT EXISTS dismissals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    reason TEXT NOT NULL,
    dismissed_at_utc TEXT NOT NULL,
    UNIQUE(event_title, instrument, event_time_utc)
);
CREATE TABLE IF NOT EXISTS check_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS print_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    predicted_vs_forecast TEXT NOT NULL,
    confidence REAL NOT NULL,
    article_count INTEGER NOT NULL,
    scored_at_utc TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'live'
);
CREATE TABLE IF NOT EXISTS kalshi_reads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    strike REAL NOT NULL,
    implied_direction TEXT NOT NULL,
    implied_probability REAL NOT NULL,
    open_interest REAL NOT NULL,
    read_at_utc TEXT NOT NULL
);
"""


@dataclass
class Prediction:
    id: int
    event_title: str
    instrument: str
    event_time_utc: str
    scored_at_utc: str
    probability: float
    direction: str
    confidence: float
    article_count: int
    contradiction_flag: bool
    source: str


@dataclass
class Outcome:
    id: int
    event_title: str
    instrument: str
    event_time_utc: str
    actual_direction: str
    actual_move_note: str
    confirmed_at_utc: str
    source: str


@dataclass
class PrintPrediction:
    id: int
    event_title: str
    event_time_utc: str
    predicted_vs_forecast: str
    confidence: float
    article_count: int
    scored_at_utc: str
    source: str


@dataclass
class KalshiReadRecord:
    id: int
    event_title: str
    event_time_utc: str
    strike: float
    implied_direction: str
    implied_probability: float
    open_interest: float
    read_at_utc: str


def _migrate_add_source_columns(conn: sqlite3.Connection) -> None:
    """
    Same reasoning as webapp/store.py's _migrate_add_source_column() —
    CREATE TABLE IF NOT EXISTS doesn't retroactively add a column.
    Covers predictions, print_predictions, and outcomes (NOT
    dismissals/check_log/kalshi_reads — no seeded rows are ever written
    to those).
    """
    for table in ("predictions", "print_predictions", "outcomes"):
        existing_columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "source" not in existing_columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN source TEXT NOT NULL DEFAULT 'live'")
    conn.commit()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # db_path resolved inside the body (not as a default arg value) so
    # tests can patch module-level DB_PATH and have it take effect.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate_add_source_columns(conn)
    return conn


def record_prediction(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    probability: float,
    direction: str,
    confidence: float,
    article_count: int,
    contradiction_flag: bool,
    scored_at_utc: Optional[dt.datetime] = None,
    source: str = "live",
) -> int:
    scored_at = scored_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO predictions (event_title, instrument, event_time_utc, scored_at_utc, "
        "probability, direction, confidence, article_count, contradiction_flag, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), scored_at.isoformat(),
         probability, direction, confidence, article_count, int(contradiction_flag), source),
    )
    conn.commit()
    return cursor.lastrowid


def count_predictions(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> int:
    """
    How many prediction snapshots already exist for this (event,
    instrument, event_time_utc) OCCURRENCE — not the event title alone.
    Forex Factory event titles are stable and recur monthly/quarterly
    (e.g. "Non-Farm Employment Change" happens every month) with the SAME
    title but a DIFFERENT event_time_utc each time, so scoping must
    include event_time_utc or the budget cap would silently stop
    accumulating for that title forever after its first occurrence. This
    is pure data access — the accumulator's own snapshot budget cap
    enforcement lives in scoring/backtest_accumulator.py, not here.
    """
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM predictions "
        "WHERE event_title = ? AND instrument = ? AND event_time_utc = ?",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    return row["n"]


def get_predictions_awaiting_outcome(
    conn: sqlite3.Connection, now: Optional[dt.datetime] = None
) -> list[Prediction]:
    """
    Distinct (event_title, instrument, event_time_utc) triples whose
    event has already passed and have no matching row in outcomes yet —
    the LATEST prediction snapshot per pair is what gets surfaced (not
    every snapshot, just the final one before the event).
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = conn.execute(
        """
        SELECT p.* FROM predictions p
        WHERE p.event_time_utc <= ?
          AND p.scored_at_utc = (
              SELECT MAX(p2.scored_at_utc) FROM predictions p2
              WHERE p2.event_title = p.event_title AND p2.instrument = p.instrument
                AND p2.event_time_utc = p.event_time_utc
          )
          AND NOT EXISTS (
              SELECT 1 FROM outcomes o
              WHERE o.event_title = p.event_title AND o.instrument = p.instrument
                AND o.event_time_utc = p.event_time_utc
          )
          AND NOT EXISTS (
              SELECT 1 FROM dismissals x
              WHERE x.event_title = p.event_title AND x.instrument = p.instrument
                AND x.event_time_utc = p.event_time_utc
          )
        ORDER BY p.event_time_utc ASC
        """,
        (now.isoformat(),),
    ).fetchall()
    return [Prediction(**dict(row)) for row in rows]


def get_latest_prediction(
    conn: sqlite3.Connection, event_title: str, instrument: str,
) -> Optional[Prediction]:
    """
    Most recent prediction snapshot for this (event_title, instrument)
    pair, regardless of confirmed/dismissed/pending status — unlike
    get_predictions_awaiting_outcome() (past + unconfirmed only) and
    get_all_confirmed_cases() (confirmed only), this is a general lookup.
    Used by webapp/app.py to display "backed by N articles" alongside the
    dashboard's own essence-only score — a read of already-independently-
    fetched accumulator data, not a fetch/score of anything itself.
    Returns None if no snapshot exists for this pair yet. `id` breaks
    scored_at_utc ties, same reasoning as get_latest_two() in
    webapp/store.py.
    """
    latest_two = get_latest_two_predictions(conn, event_title, instrument)
    return latest_two[0] if latest_two else None


def get_latest_two_predictions(
    conn: sqlite3.Connection, event_title: str, instrument: str,
) -> list[Prediction]:
    """
    Most recent RECORDED prediction snapshots for this (event_title,
    instrument) pair, most recent first — 0, 1, or 2 rows. Backs the
    dashboard's article-based diff strip (webapp/app.py), mirroring
    webapp/store.py's get_latest_two() for the essence-only score: since
    scoring/backtest_accumulator.py only records a snapshot on a material
    change (direction flip or a same-direction move past its threshold —
    see backtest_accumulator.MATERIAL_CHANGE_THRESHOLD_PROBABILITY), any
    two consecutive rows here represent a genuine shift worth showing, not
    noise. `id` breaks scored_at_utc ties, same reasoning as
    get_latest_two() in webapp/store.py.
    """
    rows = conn.execute(
        "SELECT * FROM predictions WHERE event_title = ? AND instrument = ? "
        "ORDER BY scored_at_utc DESC, id DESC LIMIT 2",
        (event_title, instrument),
    ).fetchall()
    predictions = []
    for row in rows:
        d = dict(row)
        predictions.append(Prediction(
            id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
            event_time_utc=d["event_time_utc"], scored_at_utc=d["scored_at_utc"],
            probability=d["probability"], direction=d["direction"], confidence=d["confidence"],
            article_count=d["article_count"], contradiction_flag=bool(d["contradiction_flag"]),
            source=d["source"],
        ))
    return predictions


def record_outcome(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    actual_direction: str,
    actual_move_note: str,
    confirmed_at_utc: Optional[dt.datetime] = None,
    source: str = "live",
) -> int:
    # Validated here, not just in the interactive CLI (scripts/confirm_backtest_outcomes.py)
    # — that check is UI-layer only and doesn't protect any other caller. An
    # unrecognized value (typo, wrong case) would otherwise sit silently in the
    # DB until build_real_backtest_report() crashes on Direction(...) much later,
    # for every case in the report, not just the bad one.
    try:
        Direction(actual_direction)
    except ValueError:
        valid = ", ".join(d.value for d in Direction)
        raise ValueError(
            f"actual_direction={actual_direction!r} is not valid — must be one of: {valid}"
        )

    confirmed_at = confirmed_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO outcomes (event_title, instrument, event_time_utc, actual_direction, "
        "actual_move_note, confirmed_at_utc, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), actual_direction,
         actual_move_note, confirmed_at.isoformat(), source),
    )
    conn.commit()
    return cursor.lastrowid


def record_dismissal(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    reason: str,
    dismissed_at_utc: Optional[dt.datetime] = None,
) -> int:
    """
    Marks a (event, instrument, occurrence) prediction as never going to
    get a real outcome — e.g. Forex Factory rescheduled or canceled the
    event after the prediction was made. Without this, such a prediction
    has no way to leave get_predictions_awaiting_outcome()'s queue: it
    would resurface on every future --list / interactive run forever,
    since a matching outcomes row can never legitimately arrive.

    Refuses to dismiss a pair that already has a real confirmed outcome —
    dismissal and confirmation are mutually exclusive terminal states for
    a given (event_title, instrument, event_time_utc), and a genuine
    result must never be silently discarded by a later dismissal.
    """
    already_confirmed = conn.execute(
        "SELECT 1 FROM outcomes WHERE event_title = ? AND instrument = ? AND event_time_utc = ?",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if already_confirmed:
        raise ValueError(
            f"{event_title!r}/{instrument!r} at {event_time_utc.isoformat()} already has a "
            "confirmed real outcome — refusing to dismiss it"
        )

    dismissed_at = dismissed_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO dismissals (event_title, instrument, event_time_utc, reason, dismissed_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), reason, dismissed_at.isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def record_check(conn: sqlite3.Connection, checked_at_utc: dt.datetime) -> int:
    """
    Logs one article-fetch check attempt (roughly one Alpha Vantage credit
    spent, in the worst case) — used by scoring/backtest_accumulator.py to
    self-throttle its own polling frequency against a rolling 24h budget.
    Deliberately NOT keyed to a specific (event, instrument) pair — this
    tracks aggregate check VOLUME across everything the accumulator is
    doing, since the resource being protected (Alpha Vantage's daily
    quota) is shared across all of it, not per-pair.
    """
    cursor = conn.execute(
        "INSERT INTO check_log (checked_at_utc) VALUES (?)",
        (checked_at_utc.isoformat(),),
    )
    conn.commit()
    return cursor.lastrowid


def count_recent_checks(conn: sqlite3.Connection, since: dt.datetime) -> int:
    """How many checks have been logged at or after `since` — the rolling-window count record_check() feeds."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM check_log WHERE checked_at_utc >= ?",
        (since.isoformat(),),
    ).fetchone()
    return row["n"]


def get_all_confirmed_cases(conn: sqlite3.Connection) -> list[tuple[Prediction, Outcome]]:
    """
    Joins each (event, instrument) pair's LATEST prediction snapshot with
    its confirmed outcome, for reporting. Pairs with no confirmed outcome
    yet are excluded — never fabricate a result.
    """
    rows = conn.execute(
        """
        SELECT p.*, o.actual_direction, o.actual_move_note, o.confirmed_at_utc,
               o.id AS outcome_id, o.source AS outcome_source
        FROM outcomes o
        JOIN predictions p ON p.event_title = o.event_title
                           AND p.instrument = o.instrument
                           AND p.event_time_utc = o.event_time_utc
        WHERE p.scored_at_utc = (
            SELECT MAX(p2.scored_at_utc) FROM predictions p2
            WHERE p2.event_title = p.event_title AND p2.instrument = p.instrument
              AND p2.event_time_utc = p.event_time_utc
        )
        ORDER BY p.event_time_utc ASC
        """
    ).fetchall()

    cases = []
    for row in rows:
        d = dict(row)
        prediction = Prediction(
            id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
            event_time_utc=d["event_time_utc"], scored_at_utc=d["scored_at_utc"],
            probability=d["probability"], direction=d["direction"], confidence=d["confidence"],
            article_count=d["article_count"], contradiction_flag=bool(d["contradiction_flag"]),
            source=d["source"],
        )
        outcome = Outcome(
            id=d["outcome_id"], event_title=d["event_title"], instrument=d["instrument"],
            event_time_utc=d["event_time_utc"], actual_direction=d["actual_direction"],
            actual_move_note=d["actual_move_note"], confirmed_at_utc=d["confirmed_at_utc"],
            source=d["outcome_source"],
        )
        cases.append((prediction, outcome))
    return cases


def get_latest_print_prediction(
    conn: sqlite3.Connection, event_title: str, event_time_utc: dt.datetime,
) -> Optional[PrintPrediction]:
    """
    Most recent recorded print-direction call for this specific (event_title,
    event_time_utc) OCCURRENCE — None if never scored. Scoped to occurrence,
    not title-only, for the same reason count_predictions() in this module
    is: Forex Factory event titles recur monthly/quarterly with the SAME
    title but a DIFFERENT event_time_utc each time, so a title-only lookup
    would leak a prior occurrence's call onto an unrelated later one.
    """
    row = conn.execute(
        "SELECT * FROM print_predictions WHERE event_title = ? AND event_time_utc = ? "
        "ORDER BY scored_at_utc DESC, id DESC LIMIT 1",
        (event_title, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return PrintPrediction(
        id=d["id"], event_title=d["event_title"], event_time_utc=d["event_time_utc"],
        predicted_vs_forecast=d["predicted_vs_forecast"], confidence=d["confidence"],
        article_count=d["article_count"], scored_at_utc=d["scored_at_utc"],
        source=d["source"],
    )


def record_print_prediction_if_changed(
    conn: sqlite3.Connection,
    event_title: str,
    event_time_utc: dt.datetime,
    call,  # PrintCall from scoring.print_direction — duck-typed to avoid a circular import (print_direction doesn't import this module, but keeping this module free of a hard dependency on it costs nothing)
    now: Optional[dt.datetime] = None,
    source: str = "live",
) -> bool:
    """
    Writes a new print_predictions row only if `call.direction` differs
    from the latest recorded call for this exact (event_title,
    event_time_utc) OCCURRENCE — same "current call is the truth until
    articles contradict it" principle as _is_material_change() in
    scoring/backtest_accumulator.py, applied to a categorical value instead
    of a probability threshold. Returns True if a row was written, False if
    skipped as unchanged.
    """
    latest = get_latest_print_prediction(conn, event_title, event_time_utc)
    if latest is not None and latest.predicted_vs_forecast == call.direction:
        return False

    scored_at = now or dt.datetime.now(dt.timezone.utc)
    conn.execute(
        "INSERT INTO print_predictions (event_title, event_time_utc, predicted_vs_forecast, confidence, article_count, scored_at_utc, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_title, event_time_utc.isoformat(), call.direction, call.confidence, call.article_count, scored_at.isoformat(), source),
    )
    conn.commit()
    return True


def get_latest_prediction_for_occurrence(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Prediction]:
    """
    Most recent prediction snapshot for this EXACT (event_title,
    instrument, event_time_utc) occurrence — unlike get_latest_prediction()
    (title+instrument only), this is scoped to the specific occurrence,
    same reasoning as get_latest_print_prediction()'s occurrence scoping:
    a title recurs monthly/quarterly with the SAME title but a DIFFERENT
    event_time_utc each time, so a title-only lookup would leak a prior
    occurrence's prediction onto an unrelated later one.
    """
    row = conn.execute(
        "SELECT * FROM predictions WHERE event_title = ? AND instrument = ? AND event_time_utc = ? "
        "ORDER BY scored_at_utc DESC, id DESC LIMIT 1",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return Prediction(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], scored_at_utc=d["scored_at_utc"],
        probability=d["probability"], direction=d["direction"], confidence=d["confidence"],
        article_count=d["article_count"], contradiction_flag=bool(d["contradiction_flag"]),
        source=d["source"],
    )


def get_outcome(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Outcome]:
    """Confirmed outcome for this exact occurrence, or None if not yet confirmed — never fabricated."""
    row = conn.execute(
        "SELECT * FROM outcomes WHERE event_title = ? AND instrument = ? AND event_time_utc = ?",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return Outcome(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], actual_direction=d["actual_direction"],
        actual_move_note=d["actual_move_note"], confirmed_at_utc=d["confirmed_at_utc"],
        source=d["source"],
    )


def get_latest_kalshi_read(
    conn: sqlite3.Connection, event_title: str, event_time_utc: dt.datetime,
) -> Optional[KalshiReadRecord]:
    """
    Most recent recorded Kalshi read for this specific (event_title,
    event_time_utc) OCCURRENCE — None if never recorded. Scoped to
    occurrence, not title-only, same reasoning as get_latest_print_prediction():
    Forex Factory event titles recur monthly/quarterly with the SAME
    title but a DIFFERENT event_time_utc each time.
    """
    row = conn.execute(
        "SELECT * FROM kalshi_reads WHERE event_title = ? AND event_time_utc = ? "
        "ORDER BY read_at_utc DESC, id DESC LIMIT 1",
        (event_title, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return KalshiReadRecord(
        id=d["id"], event_title=d["event_title"], event_time_utc=d["event_time_utc"],
        strike=d["strike"], implied_direction=d["implied_direction"],
        implied_probability=d["implied_probability"], open_interest=d["open_interest"],
        read_at_utc=d["read_at_utc"],
    )


def record_kalshi_read_if_changed(
    conn: sqlite3.Connection,
    event_title: str,
    event_time_utc: dt.datetime,
    read,  # KalshiRead from data_layer.kalshi_feed — duck-typed to avoid a hard dependency
    now: Optional[dt.datetime] = None,
) -> bool:
    """
    Writes a new kalshi_reads row only if `read.implied_direction` differs
    from the latest recorded read for this exact occurrence — same
    "current read is the truth until the market moves it" principle as
    record_print_prediction_if_changed(). Returns True if a row was
    written, False if skipped as unchanged.
    """
    latest = get_latest_kalshi_read(conn, event_title, event_time_utc)
    if latest is not None and latest.implied_direction == read.implied_direction:
        return False

    read_at = now or dt.datetime.now(dt.timezone.utc)
    conn.execute(
        "INSERT INTO kalshi_reads (event_title, event_time_utc, strike, implied_direction, implied_probability, open_interest, read_at_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_title, event_time_utc.isoformat(), read.strike, read.implied_direction,
         read.implied_probability, read.open_interest, read_at.isoformat()),
    )
    conn.commit()
    return True
