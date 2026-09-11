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
import json
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
    source TEXT NOT NULL DEFAULT 'live',
    top_contributions_json TEXT,
    confidence_multipliers_json TEXT
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
CREATE TABLE IF NOT EXISTS tier1_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence TEXT NOT NULL,
    source TEXT NOT NULL,
    predicted_direction TEXT NOT NULL,
    logged_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tier1_comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    sentiment_direction TEXT NOT NULL,
    sentiment_correct INTEGER,          -- NULL = sentiment made no call (neutral), same convention as BacktestCase
    tier1_direction TEXT NOT NULL,
    tier1_confidence TEXT NOT NULL,
    tier1_correct INTEGER,              -- NULL = Tier 1 made no call (neutral, e.g. a Guessing "no confident call")
    actual_direction TEXT NOT NULL,
    actual_move_note TEXT NOT NULL,
    compared_at_utc TEXT NOT NULL,
    UNIQUE(event_title, instrument, event_time_utc)
);
CREATE TABLE IF NOT EXISTS exogenous_shocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series TEXT NOT NULL,
    shock_date TEXT NOT NULL,
    move_pct REAL NOT NULL,
    stdev_move REAL NOT NULL,
    taxonomy_category TEXT,
    headline_cause TEXT,
    source TEXT,
    logged_at_utc TEXT NOT NULL,
    UNIQUE(series, shock_date)
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
    top_contributions_json: Optional[str] = None
    confidence_multipliers_json: Optional[str] = None

    @property
    def top_contributions(self) -> list[dict]:
        """
        Parsed top_contributions_json — the "why did this call change"
        context (2026-08-17): each entry is one article's
        {title, url, source, published_utc, usd_sentiment, weight_pct},
        ranked by weight_pct descending, capped at
        TOP_CONTRIBUTIONS_LIMIT. [] — never fabricated — for any row
        written before this feature existed (top_contributions_json is
        NULL) or with an empty/malformed value.
        """
        if not self.top_contributions_json:
            return []
        try:
            return json.loads(self.top_contributions_json)
        except (ValueError, TypeError):
            return []

    @property
    def confidence_multipliers(self) -> dict:
        """
        Parsed confidence_multipliers_json (2026-09-11, P2 — fundamental-
        analysis-review-2026-09-11.md #9): which of
        scoring.probability_engine.py's confidence-only modifiers fired on
        this exact call — macro_backdrop_agrees, cot_crowding_flag,
        equity_risk_agrees, oil_shock_flag, chain_conflict_flag, mirroring
        ProbabilityResult's own field names exactly. Without this, the
        next miss in one of these newer signal paths would be as
        undiagnosable as the August 2026 PPI miss was for
        top_contributions before THAT column existed. {} — never
        fabricated — for any row written before this feature existed
        (confidence_multipliers_json is NULL) or with an empty/malformed
        value.
        """
        if not self.confidence_multipliers_json:
            return {}
        try:
            return json.loads(self.confidence_multipliers_json)
        except (ValueError, TypeError):
            return {}


def _prediction_from_row(d: dict) -> Prediction:
    """
    Builds a Prediction from a sqlite3.Row-turned-dict — centralized
    (2026-09-11) so every read site gets both JSON columns consistently.
    Before this, two of the four construction sites never passed
    top_contributions_json at all (a real, pre-existing gap this
    centralization fixes as a side effect, not a new feature) — .get()
    on both JSON columns so a pre-migration row (column simply absent
    from an older schema in a stale in-memory dict) degrades to None
    rather than a KeyError.
    """
    return Prediction(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], scored_at_utc=d["scored_at_utc"],
        probability=d["probability"], direction=d["direction"], confidence=d["confidence"],
        article_count=d["article_count"], contradiction_flag=bool(d["contradiction_flag"]),
        source=d["source"], top_contributions_json=d.get("top_contributions_json"),
        confidence_multipliers_json=d.get("confidence_multipliers_json"),
    )


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


@dataclass
class Tier1PredictionRow:
    id: int
    event_title: str
    instrument: str
    event_time_utc: str
    value: str
    confidence: str          # 'Certain' | 'Likely' | 'Guessing'
    source: str
    predicted_direction: str  # 'bullish' | 'bearish' | 'neutral' -- Direction enum's own string values
    logged_at_utc: str


@dataclass
class Tier1ComparisonRow:
    id: int
    event_title: str
    instrument: str
    event_time_utc: str
    sentiment_direction: str
    sentiment_correct: Optional[bool]
    tier1_direction: str
    tier1_confidence: str
    tier1_correct: Optional[bool]
    actual_direction: str
    actual_move_note: str
    compared_at_utc: str


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


def _migrate_add_top_contributions_column(conn: sqlite3.Connection) -> None:
    """Same reasoning as _migrate_add_source_columns() — a pre-existing DB file from before this feature (2026-08-17) needs the column added, not just declared in _SCHEMA."""
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()}
    if "top_contributions_json" not in existing_columns:
        conn.execute("ALTER TABLE predictions ADD COLUMN top_contributions_json TEXT")
        conn.commit()


def _migrate_add_confidence_multipliers_column(conn: sqlite3.Connection) -> None:
    """Same reasoning as _migrate_add_top_contributions_column() — a pre-existing DB file from before this feature (2026-09-11, P2) needs the column added, not just declared in _SCHEMA."""
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()}
    if "confidence_multipliers_json" not in existing_columns:
        conn.execute("ALTER TABLE predictions ADD COLUMN confidence_multipliers_json TEXT")
        conn.commit()


_schema_ready_paths: set[str] = set()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # db_path resolved inside the body (not as a default arg value) so
    # tests can patch module-level DB_PATH and have it take effect.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Dashboard-review-2026-09-11.md: executescript + migration checks used
    # to re-run on EVERY call — pure overhead once a path's schema is
    # already current. Same fix and same ":memory:" exception as
    # webapp/store.py's get_connection() — see its comment for why
    # ":memory:" must never be cached (every connection to it is a
    # genuinely separate, empty database).
    if path == ":memory:":
        conn.executescript(_SCHEMA)
        _migrate_add_source_columns(conn)
        _migrate_add_top_contributions_column(conn)
        _migrate_add_confidence_multipliers_column(conn)
        return conn
    path_key = str(Path(path).resolve())
    if path_key not in _schema_ready_paths:
        conn.executescript(_SCHEMA)
        _migrate_add_source_columns(conn)
        _migrate_add_top_contributions_column(conn)
        _migrate_add_confidence_multipliers_column(conn)
        _schema_ready_paths.add(path_key)
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
    top_contributions: Optional[list[dict]] = None,
    confidence_multipliers: Optional[dict] = None,
) -> int:
    """
    top_contributions (2026-08-17): the "why did this call change"
    context — up to TOP_CONTRIBUTIONS_LIMIT article contributions ranked
    by weight share, built by
    scoring.backtest_accumulator._build_top_contributions() from the same
    ProbabilityResult.contributions this row's probability/direction came
    from. Stored as JSON since it's a small, bounded, write-once-read-
    together-with-the-row structure — same "JSON blob column" precedent
    webapp/store.py's calendar_snapshot already uses, not a new relational
    child table for what's always exactly one row's own detail. None/[]
    (never fabricated) when the caller has nothing to attach — e.g. no
    articles carried any real signal this round.

    confidence_multipliers (2026-09-11, P2 — fundamental-analysis-
    review-2026-09-11.md #9): which confidence-only modifiers fired on
    this exact ProbabilityResult — macro_backdrop_agrees, cot_crowding_flag,
    equity_risk_agrees, oil_shock_flag, chain_conflict_flag — same field
    names as ProbabilityResult itself, passed through verbatim by the
    caller (scoring.backtest_accumulator.py). Same "JSON blob, None when
    empty" contract as top_contributions above.
    """
    scored_at = scored_at_utc or dt.datetime.now(dt.timezone.utc)
    top_contributions_json = json.dumps(top_contributions) if top_contributions else None
    confidence_multipliers_json = json.dumps(confidence_multipliers) if confidence_multipliers else None
    cursor = conn.execute(
        "INSERT INTO predictions (event_title, instrument, event_time_utc, scored_at_utc, "
        "probability, direction, confidence, article_count, contradiction_flag, source, "
        "top_contributions_json, confidence_multipliers_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), scored_at.isoformat(),
         probability, direction, confidence, article_count, int(contradiction_flag), source,
         top_contributions_json, confidence_multipliers_json),
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
    predictions = [_prediction_from_row(dict(row)) for row in rows]
    return predictions


def get_latest_two_predictions_bulk(
    conn: sqlite3.Connection, event_titles: list[str], instruments: list[str],
) -> dict[tuple[str, str], list[Prediction]]:
    """
    Batched version of get_latest_two_predictions() — one query for the
    whole `event_titles` x `instruments` cross product, instead of
    webapp/app.py's /api/predictions issuing one query per (event, symbol)
    pair. Returns a dict keyed by (event_title, instrument); a pair with
    no rows is simply absent. Same most-recent-first, `id`-breaks-ties
    ordering as get_latest_two_predictions().
    """
    if not event_titles or not instruments:
        return {}
    title_placeholders = ",".join("?" for _ in event_titles)
    instrument_placeholders = ",".join("?" for _ in instruments)
    rows = conn.execute(
        f"SELECT * FROM predictions WHERE event_title IN ({title_placeholders}) "
        f"AND instrument IN ({instrument_placeholders}) "
        "ORDER BY event_title, instrument, scored_at_utc DESC, id DESC",
        (*event_titles, *instruments),
    ).fetchall()
    grouped: dict[tuple[str, str], list[Prediction]] = {}
    for row in rows:
        prediction = _prediction_from_row(dict(row))
        bucket = grouped.setdefault((prediction.event_title, prediction.instrument), [])
        if len(bucket) < 2:
            bucket.append(prediction)
    return grouped


def get_latest_print_predictions_bulk(
    conn: sqlite3.Connection, event_titles: list[str],
) -> dict[tuple[str, str], PrintPrediction]:
    """
    Batched version of get_latest_print_prediction() — one query covering
    every title in `event_titles` (all of that title's occurrences, since
    a title recurs monthly/quarterly with a different event_time_utc each
    time — see get_latest_print_prediction()'s own docstring) instead of
    one query per occurrence. Returns a dict keyed by
    (event_title, event_time_utc); an occurrence with no row is absent.
    """
    if not event_titles:
        return {}
    placeholders = ",".join("?" for _ in event_titles)
    rows = conn.execute(
        f"SELECT * FROM print_predictions WHERE event_title IN ({placeholders}) "
        "ORDER BY event_title, event_time_utc, scored_at_utc DESC, id DESC",
        event_titles,
    ).fetchall()
    latest: dict[tuple[str, str], PrintPrediction] = {}
    for row in rows:
        d = dict(row)
        # Normalized via parse+isoformat, not the raw stored string — same
        # reasoning as webapp/app.py's own "compare parsed datetimes, not
        # raw strings" rule (Finding 1, 2026-09-06): this codebase has more
        # than one producer of event_time_utc strings, and their formatting
        # isn't guaranteed byte-identical even for the same instant.
        key = (d["event_title"], dt.datetime.fromisoformat(d["event_time_utc"]).isoformat())
        if key in latest:
            continue  # first row seen per key is already the latest, per the ORDER BY above
        latest[key] = PrintPrediction(
            id=d["id"], event_title=d["event_title"], event_time_utc=d["event_time_utc"],
            predicted_vs_forecast=d["predicted_vs_forecast"], confidence=d["confidence"],
            article_count=d["article_count"], scored_at_utc=d["scored_at_utc"],
            source=d["source"],
        )
    return latest


def get_latest_kalshi_reads_bulk(
    conn: sqlite3.Connection, event_titles: list[str],
) -> dict[tuple[str, str], KalshiReadRecord]:
    """Batched version of get_latest_kalshi_read() — same approach and occurrence-keying as get_latest_print_predictions_bulk()."""
    if not event_titles:
        return {}
    placeholders = ",".join("?" for _ in event_titles)
    rows = conn.execute(
        f"SELECT * FROM kalshi_reads WHERE event_title IN ({placeholders}) "
        "ORDER BY event_title, event_time_utc, read_at_utc DESC, id DESC",
        event_titles,
    ).fetchall()
    latest: dict[tuple[str, str], KalshiReadRecord] = {}
    for row in rows:
        d = dict(row)
        key = (d["event_title"], dt.datetime.fromisoformat(d["event_time_utc"]).isoformat())  # normalized, see get_latest_print_predictions_bulk()
        if key in latest:
            continue
        latest[key] = KalshiReadRecord(
            id=d["id"], event_title=d["event_title"], event_time_utc=d["event_time_utc"],
            strike=d["strike"], implied_direction=d["implied_direction"],
            implied_probability=d["implied_probability"], open_interest=d["open_interest"],
            read_at_utc=d["read_at_utc"],
        )
    return latest


def get_latest_tier1_predictions_bulk(
    conn: sqlite3.Connection, event_titles: list[str], instruments: list[str],
) -> dict[tuple[str, str, str], Tier1PredictionRow]:
    """
    Batched version of get_latest_tier1_prediction_for_occurrence() — one
    query covering every (event_title, instrument) combination in
    `event_titles` x `instruments` (all occurrences of each) instead of
    one query per occurrence. Returns a dict keyed by
    (event_title, instrument, event_time_utc); an occurrence with no row
    is absent. Callers should still wrap this in try/except — a bulk
    failure must not take down the whole /api/predictions route, same
    "fail open" reasoning as the per-occurrence call this replaces
    (final whole-branch review, 2026-09-07 — Finding 2).
    """
    if not event_titles or not instruments:
        return {}
    title_placeholders = ",".join("?" for _ in event_titles)
    instrument_placeholders = ",".join("?" for _ in instruments)
    rows = conn.execute(
        f"SELECT * FROM tier1_predictions WHERE event_title IN ({title_placeholders}) "
        f"AND instrument IN ({instrument_placeholders}) "
        "ORDER BY event_title, instrument, event_time_utc, logged_at_utc DESC, id DESC",
        (*event_titles, *instruments),
    ).fetchall()
    latest: dict[tuple[str, str, str], Tier1PredictionRow] = {}
    for row in rows:
        d = dict(row)
        key = (d["event_title"], d["instrument"], dt.datetime.fromisoformat(d["event_time_utc"]).isoformat())  # normalized, see get_latest_print_predictions_bulk()
        if key in latest:
            continue
        latest[key] = Tier1PredictionRow(
            id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
            event_time_utc=d["event_time_utc"], value=d["value"], confidence=d["confidence"],
            source=d["source"], predicted_direction=d["predicted_direction"],
            logged_at_utc=d["logged_at_utc"],
        )
    return latest


def get_prediction_history(
    conn: sqlite3.Connection, event_title: str, instrument: str, limit: int = 10,
) -> list[Prediction]:
    """
    The full recorded progression for this (event_title, instrument) pair,
    most recent first, capped at `limit` — every material-change snapshot
    scoring/backtest_accumulator.py ever wrote, each carrying its own
    top_contributions (2026-08-17's "why did this call change" feature).
    Unlike get_latest_two_predictions() (exactly 0-2 rows, for the
    dashboard's diff strip), this is the full timeline a user can inspect
    to see how a call evolved — e.g. "51% indecisive -> 52% Sell" plus
    whatever came before or after.
    """
    rows = conn.execute(
        "SELECT * FROM predictions WHERE event_title = ? AND instrument = ? "
        "ORDER BY scored_at_utc DESC, id DESC LIMIT ?",
        (event_title, instrument, limit),
    ).fetchall()
    return [Prediction(**dict(row)) for row in rows]


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


def get_last_check_utc(conn: sqlite3.Connection) -> Optional[dt.datetime]:
    """
    The most recent record_check() timestamp across everything the
    accumulator has done — a proxy for "is the accumulator process alive
    and actually completing cycles," same role
    data_layer.calendar_feed.get_last_successful_fetch_age_seconds() plays
    for the calendar fetch. Returns None if no check has ever been logged
    (fresh install, or the accumulator process has never run) — never a
    fabricated "just now."
    """
    row = conn.execute("SELECT MAX(checked_at_utc) AS latest FROM check_log").fetchone()
    if row is None or row["latest"] is None:
        return None
    return dt.datetime.fromisoformat(row["latest"])


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
        prediction = _prediction_from_row(d)
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
    return _prediction_from_row(dict(row))


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


_VALID_TIER1_CONFIDENCE = ("Certain", "Likely", "Guessing")


_VALID_TAXONOMY_CATEGORIES = (
    "Treasury buyback size/schedule change",
    "US sovereign credit-rating action",
    "Government shutdown / funding lapse",
    "Fed-independence shock",
    "Fed Chair transition",
    "Tariff/trade policy executive action",
    "OPEC+ supply decision",
    "Geopolitical war-driven oil supply shock",
)


@dataclass
class ExogenousShockRow:
    id: int
    series: str
    shock_date: str
    move_pct: float
    stdev_move: float
    taxonomy_category: Optional[str]
    headline_cause: Optional[str]
    source: Optional[str]
    logged_at_utc: str


def record_tier1_prediction(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    value: str,
    confidence: str,
    source: str,
    predicted_direction: str,
    logged_at_utc: Optional[dt.datetime] = None,
) -> int:
    """
    Persists a Causation-Matrix Tier 1 prediction (scoring.backtest.Tier1Prediction)
    for one (event_title, instrument, event_time_utc) occurrence -- a
    human-researched value/confidence/source/predicted_direction, never
    auto-derived (see Tier1Prediction's own docstring). One row per
    instrument, same as record_prediction() -- a Tier 1 finding's raw
    value/confidence/source don't change per instrument, but
    predicted_direction can (XAUUSD is inverse-mapped, US30 is
    risk-sentiment-dampened), so each instrument gets its own row.

    confidence and predicted_direction are validated here, not just by
    callers -- same reasoning as record_outcome()'s Direction validation:
    an unrecognized value must never sit silently in the DB until
    something crashes on it much later, for every reader, not just the
    one bad write.
    """
    if confidence not in _VALID_TIER1_CONFIDENCE:
        raise ValueError(
            f"confidence={confidence!r} is not valid — must be one of: "
            f"{', '.join(_VALID_TIER1_CONFIDENCE)}"
        )
    try:
        Direction(predicted_direction)
    except ValueError:
        valid = ", ".join(d.value for d in Direction)
        raise ValueError(
            f"predicted_direction={predicted_direction!r} is not valid — must be one of: {valid}"
        )

    logged_at = logged_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO tier1_predictions (event_title, instrument, event_time_utc, value, "
        "confidence, source, predicted_direction, logged_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), value, confidence, source,
         predicted_direction, logged_at.isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_latest_tier1_prediction_for_occurrence(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Tier1PredictionRow]:
    """
    Most recent Tier 1 prediction logged for this EXACT (event_title,
    instrument, event_time_utc) occurrence -- same occurrence-scoping
    reasoning as get_latest_prediction_for_occurrence(): a title recurs
    monthly with the SAME title but a DIFFERENT event_time_utc each time,
    so a title-only lookup would leak a prior occurrence's Tier 1 call
    onto an unrelated later one.
    """
    row = conn.execute(
        "SELECT * FROM tier1_predictions WHERE event_title = ? AND instrument = ? AND event_time_utc = ? "
        "ORDER BY logged_at_utc DESC, id DESC LIMIT 1",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return Tier1PredictionRow(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], value=d["value"], confidence=d["confidence"],
        source=d["source"], predicted_direction=d["predicted_direction"],
        logged_at_utc=d["logged_at_utc"],
    )


def record_tier1_comparison(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    sentiment_direction: str,
    sentiment_correct: Optional[bool],
    tier1_direction: str,
    tier1_confidence: str,
    tier1_correct: Optional[bool],
    actual_direction: str,
    actual_move_note: str,
    compared_at_utc: Optional[dt.datetime] = None,
) -> int:
    """
    Persists the result of comparing a real, already-recorded sentiment
    prediction against a real, already-logged Tier 1 prediction for one
    occurrence, once a real outcome exists -- the durable version of what
    tests/run_causation_matrix_option_a_*.py's one-off scripts print to a
    console. sentiment_correct/tier1_correct are None when that side made
    no directional call (neutral) -- same "no call, not wrong" convention
    scoring/backtest.py's BacktestCase.evaluate() already uses; SQLite
    stores a Python None as NULL automatically, no extra handling needed.

    UNIQUE(event_title, instrument, event_time_utc) means a re-run for the
    same occurrence replaces the prior row (INSERT OR REPLACE) rather than
    accumulating duplicates -- this is a derived, recomputable result, not
    an append-only log like predictions/outcomes/tier1_predictions.
    """
    compared_at = compared_at_utc or dt.datetime.now(dt.timezone.utc)
    conn.execute(
        "INSERT OR REPLACE INTO tier1_comparisons (event_title, instrument, event_time_utc, "
        "sentiment_direction, sentiment_correct, tier1_direction, tier1_confidence, tier1_correct, "
        "actual_direction, actual_move_note, compared_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), sentiment_direction,
         sentiment_correct, tier1_direction, tier1_confidence, tier1_correct,
         actual_direction, actual_move_note, compared_at.isoformat()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM tier1_comparisons WHERE event_title = ? AND instrument = ? AND event_time_utc = ?",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    return row["id"]


def get_tier1_comparison_for_occurrence(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Tier1ComparisonRow]:
    """The recorded comparison for this exact occurrence, or None if never computed."""
    row = conn.execute(
        "SELECT * FROM tier1_comparisons WHERE event_title = ? AND instrument = ? AND event_time_utc = ?",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return Tier1ComparisonRow(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], sentiment_direction=d["sentiment_direction"],
        sentiment_correct=None if d["sentiment_correct"] is None else bool(d["sentiment_correct"]),
        tier1_direction=d["tier1_direction"], tier1_confidence=d["tier1_confidence"],
        tier1_correct=None if d["tier1_correct"] is None else bool(d["tier1_correct"]),
        actual_direction=d["actual_direction"], actual_move_note=d["actual_move_note"],
        compared_at_utc=d["compared_at_utc"],
    )


def record_exogenous_shock(
    conn: sqlite3.Connection,
    series: str,
    shock_date: dt.date,
    move_pct: float,
    stdev_move: float,
    taxonomy_category: Optional[str] = None,
    headline_cause: Optional[str] = None,
    source: Optional[str] = None,
    logged_at_utc: Optional[dt.datetime] = None,
) -> int:
    """
    Persists a real detected anomaly (data_layer.discovery_detector.AnomalyResult)
    plus its real, human/LLM-researched cause. taxonomy_category is
    validated against AdHoc_Category_Taxonomy's exact 8 real category
    names when set -- same rejection-on-typo discipline
    record_tier1_prediction()'s confidence-tag validation already uses.
    None is a fully valid, honest value for taxonomy_category (a real
    anomaly with no fitting known category) and for headline_cause/source
    (the research step hasn't run yet, or found nothing real to attach) --
    never forced to a fabricated fit.
    """
    if taxonomy_category is not None and taxonomy_category not in _VALID_TAXONOMY_CATEGORIES:
        raise ValueError(
            f"taxonomy_category={taxonomy_category!r} is not valid — must be one of: "
            f"{', '.join(_VALID_TAXONOMY_CATEGORIES)}, or None"
        )
    logged_at = logged_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO exogenous_shocks (series, shock_date, move_pct, stdev_move, "
        "taxonomy_category, headline_cause, source, logged_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (series, shock_date.isoformat(), move_pct, stdev_move,
         taxonomy_category, headline_cause, source, logged_at.isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_exogenous_shock_for_date(
    conn: sqlite3.Connection, series: str, shock_date: dt.date,
) -> Optional[ExogenousShockRow]:
    """The recorded shock for this exact (series, shock_date), or None if never logged — never fabricated."""
    row = conn.execute(
        "SELECT * FROM exogenous_shocks WHERE series = ? AND shock_date = ?",
        (series, shock_date.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return ExogenousShockRow(
        id=d["id"], series=d["series"], shock_date=d["shock_date"],
        move_pct=d["move_pct"], stdev_move=d["stdev_move"],
        taxonomy_category=d["taxonomy_category"], headline_cause=d["headline_cause"],
        source=d["source"], logged_at_utc=d["logged_at_utc"],
    )
