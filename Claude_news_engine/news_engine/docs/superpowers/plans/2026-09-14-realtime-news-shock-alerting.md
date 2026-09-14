# Real-Time News-Shock Alerting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect unscheduled, market-moving news events near-instantaneously (free RSS, polled every 1-2 min), classify them by category and severity, map them to the user's currently-tracked symbols, deliver High-severity alerts via Telegram (all severities to a dashboard panel), and run a weekly reality check comparing each alert's assigned severity against the realized price move.

**Architecture:** A new standalone `alerting/` package with no dependency on a running Claude Code session — a Windows Task Scheduler-driven script (`poll_once.py`) does one poll cycle and exits every 1-2 minutes; rule-based triage handles unambiguous cases for free, a single plain Anthropic API call (Haiku 4.5, not an agentic session) classifies ambiguous candidates. A second Task Scheduler-driven script (`reality_check.py`) runs weekly. State lives in a brand-new standalone SQLite DB, separate from `dashboard.db` and `backtest_log.db`. A small read-only addition to the existing Flask webapp exposes the alerts to a new dashboard tab.

**Tech Stack:** Python (stdlib `sqlite3`, `difflib`, `json`), `requests` (already a core dependency), `anthropic` SDK (new, `requirements-alerting.txt`), existing `data_layer.rss_sources` / `data_layer.news_feed` / `data_layer.dukascopy_feed` / `webapp.symbols` / `webapp.store`, Flask (existing `webapp/app.py`), vanilla JS (existing `webapp/static` ES module pattern).

**Spec:** `docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md`

## Global Constraints

- No Claude Code session anywhere in the poll or reality-check loop — plain scripts, plain `anthropic.Anthropic()` API calls only.
- Free RSS sources only for v1 (`data_layer/rss_sources.py`'s `FREE_PREVIEW_FEEDS`) — no paid wire integration in this plan.
- Standalone DB (`alerting/shock_alerts.db`) — never merged into `dashboard.db` or `backtest_log.db`.
- Every I/O failure (RSS fetch, LLM call, Telegram send, Dukascopy price fetch) degrades gracefully (skip/fallback/`None`) — never crashes the calling script or fabricates a result.
- V1 reality-check thresholds: XAUUSD $10/5min, US30 150pts/5min (both explicitly tunable, not hardcoded as unchangeable truth).
- Taxonomy category names, once defined in Task 2, are used verbatim by every later task — no renaming or re-deriving elsewhere.

---

## Task 1: Standalone storage — `alerting/store.py`

**Files:**
- Create: `alerting/__init__.py` (empty)
- Create: `alerting/store.py`
- Test: `tests/test_alerting_store.py`

**Interfaces:**
- Produces: `get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection`; `ShockAlertRow` dataclass (`id: int, headline: str, sources: list[dict], detected_at_utc: dt.datetime, category: str, severity: str, classification_method: str, rationale: Optional[str], affected_symbols: list[dict], delivery_status: Optional[str], reality_move_5min: Optional[dict], reality_move_secondary: Optional[dict], reality_check_at_utc: Optional[dt.datetime], reality_mismatch: Optional[bool]`); `record_alert(conn, headline, source, url, published_utc, detected_at_utc, category, severity, classification_method, rationale, affected_symbols) -> int`; `append_source(conn, alert_id, source, url, published_utc) -> None`; `get_alert(conn, alert_id) -> Optional[ShockAlertRow]`; `list_recent_alerts_in_category(conn, category, since_utc) -> list[ShockAlertRow]`; `list_recent_alerts(conn, since_utc) -> list[ShockAlertRow]`; `set_delivery_status(conn, alert_id, status) -> None`; `record_near_miss(conn, headline, closest_category, near_miss_score, seen_at_utc=None) -> int`; `get_cursor(conn, source) -> Optional[dt.datetime]`; `set_cursor(conn, source, last_seen_utc) -> None`; `get_alerts_needing_reality_check(conn, older_than_utc) -> list[ShockAlertRow]`; `record_reality_check(conn, alert_id, move_5min, move_secondary, mismatch, checked_at_utc=None) -> None`.

- [ ] **Step 1: Write the failing test for schema creation + record/get round-trip**

```python
# tests/test_alerting_store.py
from __future__ import annotations

import datetime as dt

from alerting import store

UTC = dt.timezone.utc


def test_record_and_get_alert_round_trip():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn,
        headline="Strait of Hormuz closed after naval incident",
        source="reuters_business",
        url="https://example.com/hormuz",
        published_utc=dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC),
        detected_at_utc=dt.datetime(2026, 9, 14, 8, 1, tzinfo=UTC),
        category="energy",
        severity="High",
        classification_method="rule_tier",
        rationale=None,
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven"}],
    )
    row = store.get_alert(conn, alert_id)
    assert row is not None
    assert row.headline == "Strait of Hormuz closed after naval incident"
    assert row.category == "energy"
    assert row.severity == "High"
    assert row.classification_method == "rule_tier"
    assert row.sources == [{
        "source": "reuters_business", "url": "https://example.com/hormuz",
        "published_utc": "2026-09-14T08:00:00+00:00",
    }]
    assert row.affected_symbols == [{"symbol": "XAUUSD", "channel": "safe_haven"}]
    assert row.delivery_status is None
    assert row.reality_mismatch is None


def test_append_source_adds_corroboration_not_new_row():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn, headline="Headline", source="reuters_business", url="https://a",
        published_utc=dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC),
        detected_at_utc=dt.datetime(2026, 9, 14, 8, 1, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier",
        rationale=None, affected_symbols=[],
    )
    store.append_source(conn, alert_id, "cnbc_top_news", "https://b", dt.datetime(2026, 9, 14, 8, 3, tzinfo=UTC))
    row = store.get_alert(conn, alert_id)
    assert len(row.sources) == 2
    assert row.sources[1]["source"] == "cnbc_top_news"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting'`

- [ ] **Step 3: Write the implementation — schema, connection, record/get/append**

```python
# alerting/store.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_store.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add alerting/__init__.py alerting/store.py tests/test_alerting_store.py
git commit -m "feat: add standalone alerting store — schema, record/get/append"
```

- [ ] **Step 6: Write the failing test for cursor, near-miss log, and reality-check fields**

```python
# append to tests/test_alerting_store.py

def test_cursor_round_trip_and_default_none():
    conn = store.get_connection(":memory:")
    assert store.get_cursor(conn, "reuters_business") is None
    store.set_cursor(conn, "reuters_business", dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC))
    assert store.get_cursor(conn, "reuters_business") == dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    # setting again overwrites, doesn't duplicate (PRIMARY KEY on source)
    store.set_cursor(conn, "reuters_business", dt.datetime(2026, 9, 14, 8, 2, tzinfo=UTC))
    assert store.get_cursor(conn, "reuters_business") == dt.datetime(2026, 9, 14, 8, 2, tzinfo=UTC)


def test_record_near_miss():
    conn = store.get_connection(":memory:")
    near_miss_id = store.record_near_miss(conn, "Oil prices tick up slightly", "energy", 0.31)
    assert isinstance(near_miss_id, int)


def test_list_recent_alerts_in_category_and_overall():
    conn = store.get_connection(":memory:")
    old = store.record_alert(
        conn, headline="Old energy alert", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 1, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 1, tzinfo=UTC),
        category="energy", severity="Low", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    recent = store.record_alert(
        conn, headline="Recent energy alert", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    since = dt.datetime(2026, 9, 10, tzinfo=UTC)
    in_category = store.list_recent_alerts_in_category(conn, "energy", since)
    assert [r.id for r in in_category] == [recent]
    overall = store.list_recent_alerts(conn, since)
    assert [r.id for r in overall] == [recent]


def test_record_reality_check_writes_result():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn, headline="H", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    store.record_reality_check(
        conn, alert_id,
        move_5min={"XAUUSD": 12.5}, move_secondary={"XAUUSD": 15.0},
        mismatch=False, checked_at_utc=dt.datetime(2026, 9, 21, tzinfo=UTC),
    )
    row = store.get_alert(conn, alert_id)
    assert row.reality_move_5min == {"XAUUSD": 12.5}
    assert row.reality_mismatch is False
    assert row.reality_check_at_utc == dt.datetime(2026, 9, 21, tzinfo=UTC)


def test_get_alerts_needing_reality_check_excludes_already_checked():
    conn = store.get_connection(":memory:")
    unchecked = store.record_alert(
        conn, headline="H1", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    checked = store.record_alert(
        conn, headline="H2", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    store.record_reality_check(conn, checked, move_5min=None, move_secondary=None, mismatch=None,
                                checked_at_utc=dt.datetime(2026, 9, 15, tzinfo=UTC))
    pending = store.get_alerts_needing_reality_check(conn, dt.datetime(2026, 9, 1, tzinfo=UTC))
    assert [r.id for r in pending] == [unchecked]
```

- [ ] **Step 7: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_store.py -v`
Expected: FAIL — `AttributeError: module 'alerting.store' has no attribute 'get_cursor'` (and similarly for the other new functions)

- [ ] **Step 8: Implement cursor, near-miss, list, and reality-check functions**

```python
# append to alerting/store.py

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
```

- [ ] **Step 9: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_store.py -v`
Expected: PASS (7 tests)

- [ ] **Step 10: Commit**

```bash
git add alerting/store.py tests/test_alerting_store.py
git commit -m "feat: add cursor, near-miss log, and reality-check fields to alerting store"
```

---

## Task 2: Shock taxonomy — `alerting/taxonomy.py`

**Files:**
- Create: `alerting/taxonomy.py`
- Test: `tests/test_alerting_taxonomy.py`

**Interfaces:**
- Consumes: nothing (pure data module)
- Produces: `SHOCK_CATEGORIES: list[str]`; `HARD_RULE_PATTERNS: dict[str, list[str]]` (category -> lowercase phrases that mean an automatic High, no LLM call); `CATEGORY_SIGNAL_KEYWORDS: dict[str, list[str]]` (category -> lowercase phrases that mean "plausible candidate, escalate to LLM"); `NEAR_MISS_LOG_THRESHOLD: float`.

**Note:** these v1 lists are real, researched wire-service phrasing patterns for each category (chokepoint names, standard sanctions/war/rate-decision/credit-rating language) — a deliberate starting point per the spec's "Open items" section, expected to grow as real headlines are reviewed via the non-match audit log (Task 3).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_alerting_taxonomy.py
from __future__ import annotations

from alerting import taxonomy


def test_every_hard_rule_category_is_a_known_shock_category():
    for category in taxonomy.HARD_RULE_PATTERNS:
        assert category in taxonomy.SHOCK_CATEGORIES


def test_every_signal_keyword_category_is_a_known_shock_category():
    for category in taxonomy.CATEGORY_SIGNAL_KEYWORDS:
        assert category in taxonomy.SHOCK_CATEGORIES


def test_all_patterns_are_lowercase():
    for patterns in list(taxonomy.HARD_RULE_PATTERNS.values()) + list(taxonomy.CATEGORY_SIGNAL_KEYWORDS.values()):
        for phrase in patterns:
            assert phrase == phrase.lower(), f"{phrase!r} must be lowercase (triage.py matches case-insensitively)"


def test_hard_rule_patterns_nonempty_for_energy_and_geopolitical():
    assert len(taxonomy.HARD_RULE_PATTERNS["energy"]) > 0
    assert len(taxonomy.HARD_RULE_PATTERNS["geopolitical_conflict"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_taxonomy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.taxonomy'`

- [ ] **Step 3: Write the implementation**

```python
# alerting/taxonomy.py
"""
Real-time shock taxonomy for alerting/triage.py — deliberately broader
than docs/News_Engine_Causation_Matrix_v2.xlsx's AdHoc_Category_Taxonomy
(that 8-category set was sized for backward-looking backtest research on
already-detected price anomalies; live headlines need a wider net). See
docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.

HARD_RULE_PATTERNS: an exact-phrase match here skips the LLM entirely and
is always severity="High" -- reserved for genuinely unambiguous events
(a named chokepoint closure, a war declaration) where waiting on an LLM
call would cost real seconds for no judgment benefit.

CATEGORY_SIGNAL_KEYWORDS: a match here means "plausible candidate," not
an automatic tier -- escalated to llm_classify.py for a real severity
judgment. Broader and noisier than HARD_RULE_PATTERNS by design.

Both are v1, researched from real historical wire-service phrasing per
category, not exhaustive -- expected to grow as shock_near_misses (see
alerting/store.py's record_near_miss()) surfaces real missed events.
"""
from __future__ import annotations

SHOCK_CATEGORIES = [
    "energy",
    "geopolitical_conflict",
    "central_bank",
    "sovereign_fiscal",
    "trade_policy",
    "natural_disaster_supply_chain",
]

NEAR_MISS_LOG_THRESHOLD = 0.3  # triage.py's near_miss_score scale — tunable once real examples exist

HARD_RULE_PATTERNS: dict[str, list[str]] = {
    "energy": [
        "strait of hormuz closed",
        "strait of hormuz blocked",
        "strait of hormuz shut",
        "bab el-mandeb closed",
        "opec+ agrees to cut",
        "opec+ agrees to increase",
        "oil export ban",
        "tanker attacked",
        "pipeline attack",
    ],
    "geopolitical_conflict": [
        "declares war",
        "declaration of war",
        "military invasion",
        "state of war declared",
    ],
    "central_bank": [
        "emergency rate decision",
        "unscheduled rate cut",
        "unscheduled rate hike",
        "fed chair fired",
        "fed chair resigns",
    ],
    "sovereign_fiscal": [
        "sovereign default",
        "credit rating downgraded",
    ],
    "trade_policy": [
        "retaliatory tariffs announced",
    ],
    "natural_disaster_supply_chain": [
        "suez canal blocked",
    ],
}

CATEGORY_SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "energy": [
        "strait of hormuz", "strait of malacca", "bab el-mandeb", "opec+", "opec output",
        "oil pipeline", "refinery strike", "sanctions on oil", "chokepoint", "shipping lane",
        "houthi attack", "oil production cut", "oil production increase",
    ],
    "geopolitical_conflict": [
        "invasion", "airstrike", "missile strike", "military strike", "state of emergency",
        "coup d'etat", "martial law", "ceasefire collapses", "troops mobilized",
    ],
    "central_bank": [
        "emergency meeting", "surprise rate move", "central bank independence",
        "intervenes in currency market", "central bank governor resigns",
    ],
    "sovereign_fiscal": [
        "credit rating upgraded", "government shutdown begins", "government shutdown ends",
        "debt ceiling", "treasury buyback", "fiscal emergency",
    ],
    "trade_policy": [
        "tariffs announced", "tariffs imposed", "trade war escalates", "export ban",
        "import ban", "trade deal collapses",
    ],
    "natural_disaster_supply_chain": [
        "earthquake", "hurricane", "port closed", "supply chain disruption",
        "factory shutdown", "chip shortage", "grounded ships",
    ],
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_taxonomy.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add alerting/taxonomy.py tests/test_alerting_taxonomy.py
git commit -m "feat: add v1 real-time shock taxonomy"
```

---

## Task 3: Rule-based triage — `alerting/triage.py`

**Files:**
- Create: `alerting/triage.py`
- Test: `tests/test_alerting_triage.py`

**Interfaces:**
- Consumes: `taxonomy.SHOCK_CATEGORIES`, `taxonomy.HARD_RULE_PATTERNS`, `taxonomy.CATEGORY_SIGNAL_KEYWORDS`, `taxonomy.NEAR_MISS_LOG_THRESHOLD`; `data_layer.news_feed.NewsArticle` (fields used: `.title`, `.summary`)
- Produces: `TriageResult` dataclass (`matched: bool, category: Optional[str], rule_tier_hit: bool, matched_keywords: list[str], near_miss_score: Optional[float]`); `triage_article(article: NewsArticle) -> TriageResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_alerting_triage.py
from __future__ import annotations

import datetime as dt

from alerting.triage import triage_article
from data_layer.news_feed import NewsArticle

UTC = dt.timezone.utc


def _article(title: str, summary: str = "") -> NewsArticle:
    return NewsArticle(
        title=title, summary=summary, source="test", source_type="rss_test",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), url="https://example.com",
    )


def test_hard_rule_pattern_gives_rule_tier_hit():
    result = triage_article(_article("Iran says Strait of Hormuz closed after clash"))
    assert result.matched is True
    assert result.rule_tier_hit is True
    assert result.category == "energy"


def test_category_signal_keyword_gives_ambiguous_candidate():
    result = triage_article(_article("Oil prices tick higher on OPEC+ output chatter"))
    assert result.matched is True
    assert result.rule_tier_hit is False
    assert result.category == "energy"


def test_no_match_returns_matched_false():
    result = triage_article(_article("Local bakery wins regional award"))
    assert result.matched is False
    assert result.category is None
    assert result.rule_tier_hit is False


def test_matching_checks_title_and_summary():
    result = triage_article(_article("Markets steady", summary="Reports say the Strait of Hormuz was closed overnight"))
    assert result.matched is True
    assert result.rule_tier_hit is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_triage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.triage'`

- [ ] **Step 3: Write the implementation**

```python
# alerting/triage.py
"""Pure, no-I/O rule-based first pass over each fetched article."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from data_layer.news_feed import NewsArticle
from alerting.taxonomy import CATEGORY_SIGNAL_KEYWORDS, HARD_RULE_PATTERNS, NEAR_MISS_LOG_THRESHOLD


@dataclass
class TriageResult:
    matched: bool
    category: Optional[str]
    rule_tier_hit: bool
    matched_keywords: list[str]
    near_miss_score: Optional[float]


def _searchable_text(article: NewsArticle) -> str:
    return f"{article.title} {article.summary}".lower()


def triage_article(article: NewsArticle) -> TriageResult:
    """
    HARD_RULE_PATTERNS checked first (unambiguous -> rule_tier_hit=True,
    severity decided as High by the caller, no LLM call needed); then
    CATEGORY_SIGNAL_KEYWORDS (plausible category, ambiguous severity ->
    caller escalates to llm_classify.py). No match at all -> matched=False,
    with near_miss_score recording how many signal keywords (as a
    fraction of the category with the most hits) came close, purely for
    the non-match audit log (alerting/store.py's record_near_miss()) --
    never used to alert on its own.
    """
    text = _searchable_text(article)

    for category, patterns in HARD_RULE_PATTERNS.items():
        hits = [p for p in patterns if p in text]
        if hits:
            return TriageResult(matched=True, category=category, rule_tier_hit=True, matched_keywords=hits, near_miss_score=None)

    best_category: Optional[str] = None
    best_hits: list[str] = []
    for category, keywords in CATEGORY_SIGNAL_KEYWORDS.items():
        hits = [k for k in keywords if k in text]
        if len(hits) > len(best_hits):
            best_category, best_hits = category, hits

    if best_hits:
        return TriageResult(matched=True, category=best_category, rule_tier_hit=False, matched_keywords=best_hits, near_miss_score=None)

    # No match at all -- record how close the single best keyword hit
    # count came, scaled by the largest keyword list, purely as a rough
    # near-miss signal. 0 hits -> score 0.0 (an honest "not close at all"
    # rather than a fabricated positive number).
    all_keyword_lists = list(CATEGORY_SIGNAL_KEYWORDS.values())
    largest_list_len = max(len(k) for k in all_keyword_lists) if all_keyword_lists else 1
    near_miss_score = 0.0
    return TriageResult(matched=False, category=None, rule_tier_hit=False, matched_keywords=[], near_miss_score=near_miss_score)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_triage.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add alerting/triage.py tests/test_alerting_triage.py
git commit -m "feat: add rule-based shock triage"
```

---

## Task 4: Deduplication — `alerting/dedup.py`

**Files:**
- Create: `alerting/dedup.py`
- Test: `tests/test_alerting_dedup.py`

**Interfaces:**
- Consumes: `alerting.store.get_connection`, `alerting.store.record_alert`, `alerting.store.list_recent_alerts_in_category` (all from Task 1)
- Produces: `find_existing_alert(candidate_headline: str, category: str, conn: sqlite3.Connection, window_hours: float = 6.0) -> Optional[int]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_alerting_dedup.py
from __future__ import annotations

import datetime as dt

from alerting import store
from alerting.dedup import find_existing_alert

UTC = dt.timezone.utc


def _seed_alert(conn, headline: str, category: str, detected_at_utc: dt.datetime) -> int:
    return store.record_alert(
        conn, headline=headline, source="s", url="u", published_utc=detected_at_utc,
        detected_at_utc=detected_at_utc, category=category, severity="High",
        classification_method="rule_tier", rationale=None, affected_symbols=[],
    )


def test_similar_headline_same_category_within_window_matches():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    existing_id = _seed_alert(conn, "Strait of Hormuz closed after naval clash", "energy", now)
    match = find_existing_alert("Strait of Hormuz closed following naval clash", "energy", conn)
    assert match == existing_id


def test_different_category_never_matches():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    _seed_alert(conn, "Strait of Hormuz closed after naval clash", "energy", now)
    match = find_existing_alert("Strait of Hormuz closed after naval clash", "geopolitical_conflict", conn)
    assert match is None


def test_dissimilar_headline_does_not_match():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    _seed_alert(conn, "OPEC+ agrees to cut oil output", "energy", now)
    match = find_existing_alert("Refinery strike halts production in Texas", "energy", conn)
    assert match is None


def test_outside_window_does_not_match():
    conn = store.get_connection(":memory:")
    old = dt.datetime(2026, 9, 14, 0, 0, tzinfo=UTC)
    _seed_alert(conn, "Strait of Hormuz closed after naval clash", "energy", old)
    match = find_existing_alert("Strait of Hormuz closed following naval clash", "energy", conn, window_hours=6.0)
    assert match is None
```

Note: `find_existing_alert`'s `since_utc` argument to `list_recent_alerts_in_category` must be computed from *now* (real wall clock), not from the seeded alert's own timestamp — the last test relies on this (seeded 8+ hours before the real current time, which is 2026-09-14 or later while this plan is executed, so it always falls outside a 6-hour window).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_dedup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.dedup'`

- [ ] **Step 3: Write the implementation**

```python
# alerting/dedup.py
"""Content-similarity + time-window deduplication for poll_once.py."""
from __future__ import annotations

import datetime as dt
import difflib
import sqlite3
from typing import Optional

from alerting import store

SIMILARITY_THRESHOLD = 0.6  # difflib.SequenceMatcher ratio -- tunable; conservative enough to
                             # catch reworded corroborating headlines without merging distinct events


def find_existing_alert(
    candidate_headline: str, category: str, conn: sqlite3.Connection, window_hours: float = 6.0,
) -> Optional[int]:
    """
    Same difflib-based approach data_layer/news_feed.py already uses for
    article de-duplication. Returns the existing alert's id on a real
    similarity match within `category` and `window_hours` of now (caller
    should call store.append_source() instead of firing a new alert), or
    None (a genuinely new alert). Accepted v1 limitation: two distinct
    events with similar wording in the same window could merge -- flagged
    in the design spec, not solved here.
    """
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=window_hours)
    for existing in store.list_recent_alerts_in_category(conn, category, since):
        ratio = difflib.SequenceMatcher(None, candidate_headline.lower(), existing.headline.lower()).ratio()
        if ratio >= SIMILARITY_THRESHOLD:
            return existing.id
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_dedup.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add alerting/dedup.py tests/test_alerting_dedup.py
git commit -m "feat: add content-similarity dedup for shock alerts"
```

---

## Task 5: Symbol relevance mapping — `alerting/symbol_relevance.py`

**Files:**
- Create: `alerting/symbol_relevance.py`
- Test: `tests/test_alerting_symbol_relevance.py`

**Interfaces:**
- Consumes: `webapp.symbols.classify_symbol(ticker) -> SymbolClass` (`.symbol_class`, `.usd_relationship`), `webapp.symbols.UnrecognizedSymbolError`; `taxonomy.SHOCK_CATEGORIES`
- Produces: `SymbolImpact` dataclass (`symbol: str, channel: str`); `affected_symbols(category: str, tracked_symbols: list[str]) -> list[SymbolImpact]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_alerting_symbol_relevance.py
from __future__ import annotations

from alerting.symbol_relevance import affected_symbols


def test_energy_shock_affects_gold_via_safe_haven():
    result = affected_symbols("energy", ["XAUUSD", "US30"])
    symbols = {r.symbol: r.channel for r in result}
    assert symbols["XAUUSD"] == "safe_haven"


def test_energy_shock_affects_us30_via_risk_sentiment():
    result = affected_symbols("energy", ["XAUUSD", "US30"])
    symbols = {r.symbol: r.channel for r in result}
    assert symbols["US30"] == "risk_sentiment"


def test_energy_shock_affects_oil_linked_usdcad_directly():
    result = affected_symbols("energy", ["USDCAD"])
    symbols = {r.symbol: r.channel for r in result}
    assert symbols["USDCAD"] == "oil_linkage"


def test_no_tracked_symbols_returns_empty_list():
    assert affected_symbols("energy", []) == []


def test_unrecognized_tracked_symbol_is_skipped_not_crashed():
    result = affected_symbols("energy", ["XAUUSD", "NOT_A_REAL_TICKER_9"])
    symbols = {r.symbol for r in result}
    assert "XAUUSD" in symbols
    assert "NOT_A_REAL_TICKER_9" not in symbols


def test_category_with_no_real_relevance_for_a_symbol_omits_it():
    # trade_policy has no established transmission logic for a plain FX cross
    result = affected_symbols("trade_policy", ["GBPAUD"])
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_symbol_relevance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.symbol_relevance'`

- [ ] **Step 3: Write the implementation**

```python
# alerting/symbol_relevance.py
"""
Maps a classified shock category to the user's currently-tracked symbols
and the transmission channel, per the design spec's per-instrument-quirks
section. Built as its own lightweight category -> symbol_class table
(NOT a reuse of scoring/probability_engine.py's private _check_oil_shock,
which takes a pre-computed MacroBackdropRead object, not a category
label -- the wrong shape for this purpose) layered on top of
webapp.symbols.classify_symbol()'s public usd_relationship baseline.
"""
from __future__ import annotations

from dataclasses import dataclass

from webapp.symbols import classify_symbol, UnrecognizedSymbolError


@dataclass
class SymbolImpact:
    symbol: str
    channel: str


# category -> {symbol_class: channel} -- only combinations with a real,
# documented transmission path are listed; anything absent here means
# "no established relevance," an honest [] result, not a guess.
_CATEGORY_SYMBOL_CLASS_CHANNELS: dict[str, dict[str, str]] = {
    "energy": {
        "metal": "safe_haven",
        "index_risk": "risk_sentiment",
    },
    "geopolitical_conflict": {
        "metal": "safe_haven",
        "index_risk": "risk_sentiment",
    },
    "central_bank": {
        "metal": "usd_relationship",
        "index_risk": "risk_sentiment",
        "fx_usd_base": "usd_relationship",
        "fx_usd_quote": "usd_relationship",
    },
    "sovereign_fiscal": {
        "metal": "usd_relationship",
        "index_risk": "risk_sentiment",
        "fx_usd_base": "usd_relationship",
        "fx_usd_quote": "usd_relationship",
    },
    "trade_policy": {
        "index_risk": "risk_sentiment",
    },
    "natural_disaster_supply_chain": {
        "index_risk": "risk_sentiment",
    },
}

# Oil-linked FX pairs (design spec: "USDCAD is oil-linked... independent
# of and sometimes working against the pure USD-weakness direction") get
# their own channel regardless of category, checked before the generic
# symbol_class table above -- a real, specific transmission path, not
# the plain usd_relationship mapping.
_OIL_LINKED_SYMBOLS = {"USDCAD"}


def affected_symbols(category: str, tracked_symbols: list[str]) -> list[SymbolImpact]:
    """
    tracked_symbols is expected to come from webapp.store.list_tracked_symbols()
    at call time -- live, not cached (poll_once.py's job to fetch it fresh
    each cycle). An unrecognized ticker is skipped, not raised -- a
    classify_symbol() failure for one tracked symbol must never block
    relevance mapping for the others. Returns [] if no real relevance can
    be established for any currently-tracked symbol under this category.
    """
    channels_by_class = _CATEGORY_SYMBOL_CLASS_CHANNELS.get(category, {})
    results: list[SymbolImpact] = []
    for symbol in tracked_symbols:
        if category == "energy" and symbol in _OIL_LINKED_SYMBOLS:
            results.append(SymbolImpact(symbol=symbol, channel="oil_linkage"))
            continue
        try:
            symbol_class = classify_symbol(symbol)
        except UnrecognizedSymbolError:
            continue
        channel = channels_by_class.get(symbol_class.symbol_class)
        if channel is not None:
            results.append(SymbolImpact(symbol=symbol, channel=channel))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_symbol_relevance.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add alerting/symbol_relevance.py tests/test_alerting_symbol_relevance.py
git commit -m "feat: add category-to-tracked-symbol relevance mapping"
```

---

## Task 6: LLM classification for ambiguous candidates — `alerting/llm_classify.py`

**Files:**
- Create: `alerting/llm_classify.py`
- Modify: `requirements-alerting.txt` (create)
- Test: `tests/test_alerting_llm_classify.py`

**Interfaces:**
- Consumes: `alerting.triage.TriageResult` (Task 3); `alerting.taxonomy.SHOCK_CATEGORIES` (Task 2); `data_layer.news_feed.NewsArticle`
- Produces: `ClassificationResult` dataclass (`category: str, severity: str, rationale: str, classification_failed: bool = False`); `classify_candidate(article: NewsArticle, triage: TriageResult) -> ClassificationResult`; `_call_model(prompt: str) -> str` (isolated seam for testing, wraps the real `anthropic.Anthropic()` call — not part of the public interface other tasks use, but named here since `poll_once.py`'s tests will monkeypatch it)

- [ ] **Step 1: Create the requirements file**

```
# requirements-alerting.txt
# Only needed for alerting/llm_classify.py's severity classification of
# ambiguous shock candidates -- a single plain API call per candidate,
# not a Claude Code session. Install only if running the alerting/ tool.
anthropic>=0.40.0
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_alerting_llm_classify.py
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from alerting.llm_classify import classify_candidate
from alerting.triage import TriageResult
from data_layer.news_feed import NewsArticle

UTC = dt.timezone.utc


def _article() -> NewsArticle:
    return NewsArticle(
        title="Oil prices tick higher on OPEC+ output chatter", summary="",
        source="test", source_type="rss_test",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), url="https://example.com",
    )


def _triage() -> TriageResult:
    return TriageResult(matched=True, category="energy", rule_tier_hit=False, matched_keywords=["opec+"], near_miss_score=None)


def test_valid_model_response_parses_into_result():
    with patch("alerting.llm_classify._call_model", return_value='{"category": "energy", "severity": "Medium", "rationale": "Routine OPEC+ commentary, not a supply disruption."}'):
        result = classify_candidate(_article(), _triage())
    assert result.category == "energy"
    assert result.severity == "Medium"
    assert result.classification_failed is False


def test_malformed_json_falls_back_to_medium():
    with patch("alerting.llm_classify._call_model", return_value="not json at all"):
        result = classify_candidate(_article(), _triage())
    assert result.severity == "Medium"
    assert result.classification_failed is True
    assert result.category == "energy"  # falls back to triage's own category


def test_invalid_category_in_response_falls_back():
    with patch("alerting.llm_classify._call_model", return_value='{"category": "not_a_real_category", "severity": "High", "rationale": "x"}'):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is True
    assert result.severity == "Medium"


def test_api_call_raising_falls_back():
    with patch("alerting.llm_classify._call_model", side_effect=RuntimeError("network down")):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is True
    assert result.severity == "Medium"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_llm_classify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.llm_classify'`

- [ ] **Step 4: Write the implementation**

```python
# alerting/llm_classify.py
"""
Single plain Anthropic API call per ambiguous candidate -- NOT a Claude
Code session, no fixed per-poll-cycle cost. Called only for candidates
triage.py couldn't resolve with a hard rule (see
docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

from alerting.taxonomy import SHOCK_CATEGORIES
from alerting.triage import TriageResult
from data_layer.news_feed import NewsArticle

_MODEL = "claude-haiku-4-5"
_VALID_SEVERITIES = ("High", "Medium", "Low")


@dataclass
class ClassificationResult:
    category: str
    severity: str
    rationale: str
    classification_failed: bool = False


def _build_prompt(article: NewsArticle, triage: TriageResult) -> str:
    return (
        "Classify this news headline for a forex/macro shock-alerting tool.\n"
        f"Headline: {article.title}\n"
        f"Summary: {article.summary}\n"
        f"Source: {article.source}\n"
        f"Plausible category from initial keyword triage: {triage.category}\n\n"
        f"Valid categories: {', '.join(SHOCK_CATEGORIES)}\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        '{"category": "<one of the valid categories>", "severity": "High"|"Medium"|"Low", "rationale": "<one sentence>"}\n'
        "severity should reflect how likely this event is to cause an immediate, sharp market "
        "reaction -- not a routine, already-priced-in development."
    )


def _call_model(prompt: str) -> str:
    """
    Isolated so classify_candidate()'s parsing/fallback logic can be unit
    tested by monkeypatching this function instead of mocking the SDK's
    response object shape.
    """
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def classify_candidate(article: NewsArticle, triage: TriageResult) -> ClassificationResult:
    """
    On any API error or malformed/invalid response: falls back to
    triage.category at severity="Medium" with classification_failed=True
    -- never dropped, never crashes the poll cycle. Caller
    (alerting/poll_once.py) is expected to persist the fallback result
    with classification_method="llm_failed_fallback" for manual review.
    """
    prompt = _build_prompt(article, triage)
    try:
        text = _call_model(prompt)
        data = json.loads(text)
        category = data["category"]
        severity = data["severity"]
        rationale = data["rationale"]
        if category not in SHOCK_CATEGORIES or severity not in _VALID_SEVERITIES:
            raise ValueError(f"model returned invalid category/severity: {data!r}")
        return ClassificationResult(category=category, severity=severity, rationale=rationale)
    except Exception as exc:  # noqa: BLE001 -- any API/parse failure must degrade safely, never crash the poll cycle
        print(f"[llm_classify] WARNING: classification failed for {article.title!r}: {exc}")
        return ClassificationResult(
            category=triage.category,
            severity="Medium",
            rationale=f"LLM classification failed ({exc}) -- falling back to rule-tier category at Medium for manual review.",
            classification_failed=True,
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_llm_classify.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add alerting/llm_classify.py requirements-alerting.txt tests/test_alerting_llm_classify.py
git commit -m "feat: add LLM severity classification for ambiguous shock candidates"
```

---

## Task 7: Telegram delivery — `alerting/notify_telegram.py`

**Files:**
- Create: `alerting/notify_telegram.py`
- Modify: `config/settings.py` (add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
- Test: `tests/test_alerting_notify_telegram.py`

**Interfaces:**
- Consumes: `config.settings.TELEGRAM_BOT_TOKEN`, `config.settings.TELEGRAM_CHAT_ID`
- Produces: `send_alert(headline: str, category: str, severity: str, rationale: Optional[str], affected_symbols: list[dict], sources: list[dict]) -> bool`

- [ ] **Step 1: Add the two new settings**

```python
# config/settings.py -- add alongside the existing API keys (near ALPHA_VANTAGE_API_KEY etc.)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
```

**Setup instructions (do this before Task 8's poll cycle can actually push anything — not a code step, an operational one):**
1. In Telegram, message `@BotFather`, send `/newbot`, follow the prompts to name the bot. BotFather replies with a token like `123456789:AAH...` — this is `TELEGRAM_BOT_TOKEN`.
2. Message your new bot directly (search its username, hit Start) so it's allowed to message you back.
3. Get your numeric chat ID: visit `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates` in a browser right after step 2, and read `result[0].message.chat.id` from the JSON response.
4. Add both values to the project's `.env` file (already loaded via `load_dotenv()` in `config/settings.py`):
   ```
   TELEGRAM_BOT_TOKEN=123456789:AAH...
   TELEGRAM_CHAT_ID=987654321
   ```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_alerting_notify_telegram.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

from alerting import notify_telegram


def test_missing_config_returns_false_without_network_call():
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", ""), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", ""), \
         patch("alerting.notify_telegram.requests.post") as mock_post:
        result = notify_telegram.send_alert("Headline", "energy", "High", "rationale", [], [])
    assert result is False
    mock_post.assert_not_called()


def test_successful_send_returns_true():
    mock_response = MagicMock(status_code=200)
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", return_value=mock_response) as mock_post:
        result = notify_telegram.send_alert(
            "Strait of Hormuz closed", "energy", "High", "Chokepoint closure",
            [{"symbol": "XAUUSD", "channel": "safe_haven"}], [{"source": "reuters", "url": "https://x"}],
        )
    assert result is True
    assert mock_post.called
    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert "Strait of Hormuz closed" in sent_text
    assert "XAUUSD" in sent_text


def test_non_200_response_returns_false():
    mock_response = MagicMock(status_code=401)
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", return_value=mock_response):
        result = notify_telegram.send_alert("Headline", "energy", "High", None, [], [])
    assert result is False


def test_network_exception_returns_false_not_raised():
    import requests
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", side_effect=requests.RequestException("timeout")):
        result = notify_telegram.send_alert("Headline", "energy", "High", None, [], [])
    assert result is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_notify_telegram.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.notify_telegram'`

- [ ] **Step 4: Write the implementation**

```python
# alerting/notify_telegram.py
"""Telegram Bot API push for High-severity shock alerts only."""
from __future__ import annotations

from typing import Optional

import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_alert(
    headline: str, category: str, severity: str, rationale: Optional[str],
    affected_symbols: list[dict], sources: list[dict],
) -> bool:
    """
    Returns True on a confirmed 200 from Telegram's API, False on any
    failure (missing config, network error, non-200) -- never raises.
    The alert row must already be persisted by the caller (alerting/
    poll_once.py) before this is called, so a False return here never
    means a lost alert -- the caller records delivery_status separately.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notify_telegram] WARNING: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set -- skipping push")
        return False

    symbols_line = ", ".join(f"{s['symbol']} ({s['channel']})" for s in affected_symbols) or "none currently tracked"
    source_line = sources[0]["url"] if sources else ""
    text = (
        f"\U0001F6A8 HIGH -- {category}\n"
        f"{headline}\n"
        f"Affects: {symbols_line}\n"
        f"{rationale or ''}\n"
        f"{source_line}"
    ).strip()

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        return resp.status_code == 200
    except requests.RequestException as exc:
        print(f"[notify_telegram] WARNING: send failed: {exc}")
        return False
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_notify_telegram.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add alerting/notify_telegram.py config/settings.py tests/test_alerting_notify_telegram.py
git commit -m "feat: add Telegram push delivery for High-severity shock alerts"
```

---

## Task 8: Poll orchestration + Task Scheduler — `alerting/poll_once.py`

**Files:**
- Create: `alerting/poll_once.py`
- Create: `alerting/scripts/register_poll_task.ps1`
- Test: `tests/test_alerting_poll_once.py`

**Interfaces:**
- Consumes: `alerting.store.*` (Task 1), `alerting.triage.triage_article` (Task 3), `alerting.dedup.find_existing_alert` (Task 4), `alerting.symbol_relevance.affected_symbols` (Task 5), `alerting.llm_classify.classify_candidate` (Task 6), `alerting.notify_telegram.send_alert` (Task 7); `data_layer.rss_sources.RSSNewsSource`, `data_layer.rss_sources.FREE_PREVIEW_FEEDS`; `webapp.store.get_connection`, `webapp.store.list_tracked_symbols`
- Produces: `run_poll_cycle(conn=None, webapp_conn=None) -> None` (the Task Scheduler entry point via `if __name__ == "__main__"`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_alerting_poll_once.py
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from alerting import store
from alerting.poll_once import run_poll_cycle
from data_layer.news_feed import NewsArticle
from webapp import store as webapp_store

UTC = dt.timezone.utc


def _article(title: str) -> NewsArticle:
    return NewsArticle(
        title=title, summary="", source="reuters_business", source_type="rss_reuters_business",
        published_utc=dt.datetime.now(UTC), url="https://example.com/a",
    )


def test_rule_tier_hit_persists_and_pushes_high_alert():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")
    webapp_conn.execute("INSERT INTO tracked_symbols (symbol) VALUES ('XAUUSD')")
    webapp_conn.commit()

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True) as mock_send:
        mock_source_cls.return_value.fetch.return_value = [_article("Strait of Hormuz closed after naval clash")]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    alerts = store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC))
    assert len(alerts) == 1
    assert alerts[0].severity == "High"
    assert alerts[0].classification_method == "rule_tier"
    assert mock_send.called


def test_no_match_never_persists_or_pushes():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert") as mock_send:
        mock_source_cls.return_value.fetch.return_value = [_article("Local bakery wins regional award")]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    assert store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC)) == []
    mock_send.assert_not_called()


def test_duplicate_article_appends_source_not_new_alert():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True):
        mock_source_cls.return_value.fetch.return_value = [_article("Strait of Hormuz closed after naval clash")]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)
        mock_source_cls.return_value.fetch.return_value = [_article("Strait of Hormuz closed following naval clash")]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    alerts = store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC))
    assert len(alerts) == 1
    assert len(alerts[0].sources) == 2


def test_one_source_fetch_failure_does_not_block_others():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    call_count = {"n": 0}

    def fetch_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("feed down")
        return [_article("Strait of Hormuz closed after naval clash")]

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True):
        mock_source_cls.return_value.fetch.side_effect = fetch_side_effect
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    alerts = store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC))
    assert len(alerts) >= 1  # at least one of the (mocked) multiple sources succeeded
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_poll_once.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.poll_once'`

- [ ] **Step 3: Write the implementation**

```python
# alerting/poll_once.py
"""
Task Scheduler entry point — one poll cycle across all free RSS sources,
then exits. Deliberately stateless between invocations (all state lives
in alerting/store.py's standalone DB) so the OS scheduler is the only
supervisor this needs: a crash or reboot just means the next scheduled
tick runs normally. See docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.
"""
from __future__ import annotations

import datetime as dt

from alerting import dedup, llm_classify, notify_telegram, store
from alerting.symbol_relevance import affected_symbols
from alerting.triage import triage_article
from alerting.taxonomy import NEAR_MISS_LOG_THRESHOLD
from data_layer.news_feed import NewsArticle
from data_layer.rss_sources import FREE_PREVIEW_FEEDS, RSSNewsSource
from webapp.store import get_connection as get_webapp_connection, list_tracked_symbols

_DEFAULT_LOOKBACK = dt.timedelta(minutes=10)  # first-ever run for a source, or a missing cursor


def run_poll_cycle(conn=None, webapp_conn=None) -> None:
    conn = conn if conn is not None else store.get_connection()
    webapp_conn = webapp_conn if webapp_conn is not None else get_webapp_connection()
    now = dt.datetime.now(dt.timezone.utc)
    for name, url in FREE_PREVIEW_FEEDS.items():
        _poll_source(conn, webapp_conn, name, url, now)


def _poll_source(conn, webapp_conn, name: str, url: str, now: dt.datetime) -> None:
    since = store.get_cursor(conn, name) or (now - _DEFAULT_LOOKBACK)
    try:
        articles = RSSNewsSource(name, url).fetch(query="", since_utc=since, limit=50)
    except Exception as exc:  # noqa: BLE001 -- one broken feed must never block the others
        print(f"[poll_once] WARNING: fetch failed for source {name!r}: {exc}")
        return
    for article in articles:
        _process_article(conn, webapp_conn, article)
    store.set_cursor(conn, name, now)


def _process_article(conn, webapp_conn, article: NewsArticle) -> None:
    result = triage_article(article)
    if not result.matched:
        if result.near_miss_score is not None and result.near_miss_score >= NEAR_MISS_LOG_THRESHOLD:
            store.record_near_miss(conn, article.title, result.category, result.near_miss_score)
        return

    if result.rule_tier_hit:
        category, severity, method, rationale = result.category, "High", "rule_tier", None
    else:
        classification = llm_classify.classify_candidate(article, result)
        category = classification.category
        severity = classification.severity
        method = "llm_failed_fallback" if classification.classification_failed else "llm"
        rationale = classification.rationale

    existing_id = dedup.find_existing_alert(article.title, category, conn)
    if existing_id is not None:
        store.append_source(conn, existing_id, article.source, article.url, article.published_utc)
        return

    tracked_symbols = list_tracked_symbols(webapp_conn)
    impacts = affected_symbols(category, tracked_symbols)
    affected_dicts = [{"symbol": i.symbol, "channel": i.channel} for i in impacts]

    alert_id = store.record_alert(
        conn, headline=article.title, source=article.source, url=article.url,
        published_utc=article.published_utc, detected_at_utc=dt.datetime.now(dt.timezone.utc),
        category=category, severity=severity, classification_method=method,
        rationale=rationale, affected_symbols=affected_dicts,
    )

    if severity == "High":
        sent = notify_telegram.send_alert(
            article.title, category, severity, rationale, affected_dicts,
            [{"source": article.source, "url": article.url}],
        )
        store.set_delivery_status(conn, alert_id, "sent" if sent else "failed")


if __name__ == "__main__":
    run_poll_cycle()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_poll_once.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add alerting/poll_once.py tests/test_alerting_poll_once.py
git commit -m "feat: add poll cycle orchestration for real-time shock alerting"
```

- [ ] **Step 6: Write the Task Scheduler registration script**

```powershell
# alerting/scripts/register_poll_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/poll_once.py
# every 2 minutes indefinitely. Run this once from an elevated PowerShell
# prompt after Task 8 is committed. Adjust $PythonPath/$ProjectRoot if
# your environment differs.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
$PythonPath = (Get-Command python).Source

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "-m alerting.poll_once" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration ([TimeSpan]::MaxValue)
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask -TaskName "NewsEngine_ShockPoll" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Polls free RSS sources every 2 minutes for real-time news-shock alerting (news_engine/alerting)."

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockPoll'"
```

- [ ] **Step 7: Run the script and verify registration**

Run (elevated PowerShell): `powershell -File alerting\scripts\register_poll_task.ps1`
Then: `Get-ScheduledTask -TaskName "NewsEngine_ShockPoll"`
Expected: task listed with `State: Ready`

- [ ] **Step 8: Commit**

```bash
git add alerting/scripts/register_poll_task.ps1
git commit -m "chore: add Task Scheduler registration script for the shock poller"
```

---

## Task 9: Weekly reality check — `alerting/reality_check.py`

**Files:**
- Create: `alerting/reality_check.py`
- Create: `alerting/scripts/register_reality_check_task.ps1`
- Test: `tests/test_alerting_reality_check.py`

**Interfaces:**
- Consumes: `alerting.store.get_alerts_needing_reality_check`, `alerting.store.record_reality_check` (Task 1); `data_layer.dukascopy_feed.get_price_at`
- Produces: `MAGNITUDE_THRESHOLDS: dict[str, float]` (symbol -> dollar/point threshold over 5 min); `run_reality_check(conn=None) -> None`; `_check_alert(conn, alert) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_alerting_reality_check.py
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from alerting import store
from alerting.reality_check import run_reality_check
from data_layer.dukascopy_feed import PricePoint

UTC = dt.timezone.utc


def _seed_alert(conn, severity: str, symbol: str, detected_at_utc: dt.datetime) -> int:
    return store.record_alert(
        conn, headline="H", source="s", url="u", published_utc=detected_at_utc,
        detected_at_utc=detected_at_utc, category="energy", severity=severity,
        classification_method="rule_tier", rationale=None,
        affected_symbols=[{"symbol": symbol, "channel": "safe_haven"}],
    )


def test_high_severity_alert_with_confirming_spike_is_no_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    # price at T0 = 2800.0, T+5min = 2812.0 (+$12, clears the $10 XAUUSD threshold)
    prices = [PricePoint(price=2800.0), PricePoint(price=2812.0), PricePoint(price=2815.0)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is False


def test_high_severity_alert_with_no_move_is_flagged_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    prices = [PricePoint(price=2800.0), PricePoint(price=2801.0), PricePoint(price=2800.5)]
    with patch("alerting.reality_check.get_price_at", side_effect=prices):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_mismatch is True


def test_missing_price_data_logs_no_data_not_a_mismatch():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = _seed_alert(conn, "High", "XAUUSD", detected_at)

    with patch("alerting.reality_check.get_price_at", return_value=None):
        run_reality_check(conn=conn)

    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is None


def test_alert_with_no_affected_symbols_is_still_marked_checked():
    conn = store.get_connection(":memory:")
    detected_at = dt.datetime.now(UTC) - dt.timedelta(days=1)
    alert_id = store.record_alert(
        conn, headline="H", source="s", url="u", published_utc=detected_at,
        detected_at_utc=detected_at, category="energy", severity="Low",
        classification_method="rule_tier", rationale=None, affected_symbols=[],
    )

    with patch("alerting.reality_check.get_price_at") as mock_get_price:
        run_reality_check(conn=conn)

    mock_get_price.assert_not_called()
    row = store.get_alert(conn, alert_id)
    assert row.reality_check_at_utc is not None
    assert row.reality_mismatch is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_alerting_reality_check.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'alerting.reality_check'`

- [ ] **Step 3: Write the implementation**

```python
# alerting/reality_check.py
"""
Task Scheduler entry point — runs weekly. For every alert without a
reality check yet, fetches price at detection time, +5min, and +30min
for each affected symbol, compares the realized move against per-symbol
magnitude thresholds, and flags a mismatch for manual review. Never
auto-changes an alert's category/severity or the thresholds themselves.
See docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.
"""
from __future__ import annotations

import datetime as dt

from alerting import store
from data_layer.dukascopy_feed import get_price_at

# V1 defaults, tunable -- see design spec's "V1 magnitude thresholds" table.
# $10 on XAUUSD's ~$2,800-3,000/oz base is ~0.35%; 150pts on US30 is the
# percentage-matched equivalent.
MAGNITUDE_THRESHOLDS: dict[str, float] = {
    "XAUUSD": 10.0,
    "US30": 150.0,
}

SECONDARY_WINDOW_MINUTES = 30


def run_reality_check(conn=None) -> None:
    conn = conn if conn is not None else store.get_connection()
    older_than = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)  # every unchecked alert, regardless of age
    for alert in store.get_alerts_needing_reality_check(conn, older_than):
        _check_alert(conn, alert)


def _check_alert(conn, alert) -> None:
    if not alert.affected_symbols:
        # Nothing to price-check -- still mark it checked so it doesn't
        # get re-queried every week forever.
        store.record_reality_check(conn, alert.id, move_5min=None, move_secondary=None, mismatch=None)
        return

    move_5min: dict[str, float] = {}
    move_secondary: dict[str, float] = {}
    any_threshold_cleared = False
    any_price_data = False

    for impact in alert.affected_symbols:
        symbol = impact["symbol"]
        threshold = MAGNITUDE_THRESHOLDS.get(symbol)
        if threshold is None:
            continue  # no v1 threshold for this symbol -- skip it, not a mismatch signal either way

        t0 = get_price_at(symbol, alert.detected_at_utc)
        t5 = get_price_at(symbol, alert.detected_at_utc + dt.timedelta(minutes=5))
        t_secondary = get_price_at(symbol, alert.detected_at_utc + dt.timedelta(minutes=SECONDARY_WINDOW_MINUTES))

        if t0 is None or t5 is None:
            continue  # real data unavailable for this symbol -- never fabricated

        any_price_data = True
        move_5min[symbol] = round(t5.price - t0.price, 4)
        if t_secondary is not None:
            move_secondary[symbol] = round(t_secondary.price - t0.price, 4)

        if abs(move_5min[symbol]) >= threshold or (symbol in move_secondary and abs(move_secondary[symbol]) >= threshold):
            any_threshold_cleared = True

    if not any_price_data:
        store.record_reality_check(conn, alert.id, move_5min=None, move_secondary=None, mismatch=None)
        return

    # A High alert with no confirming move is a mismatch (over-alerted);
    # a Low alert WITH a confirming move is also a mismatch (under-alerted,
    # the exact "should this have been a High" case the design discusses).
    if alert.severity == "High":
        mismatch = not any_threshold_cleared
    elif alert.severity == "Low":
        mismatch = any_threshold_cleared
    else:  # Medium is never flagged as a mismatch in v1 -- no established
           # "expected" magnitude band for Medium to compare against yet
        mismatch = False

    store.record_reality_check(
        conn, alert.id,
        move_5min=move_5min or None, move_secondary=move_secondary or None, mismatch=mismatch,
    )


if __name__ == "__main__":
    run_reality_check()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_alerting_reality_check.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add alerting/reality_check.py tests/test_alerting_reality_check.py
git commit -m "feat: add weekly reality check comparing alert severity to realized price moves"
```

- [ ] **Step 6: Write the weekly Task Scheduler registration script**

```powershell
# alerting/scripts/register_reality_check_task.ps1
# Registers a Windows Task Scheduler task that runs alerting/reality_check.py
# once a week. Run this once from an elevated PowerShell prompt.

$ProjectRoot = "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
$PythonPath = (Get-Command python).Source

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "-m alerting.reality_check" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "20:00"
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName "NewsEngine_ShockRealityCheck" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Weekly reality check comparing shock-alert severity to realized price moves (news_engine/alerting)."

Write-Host "Registered. Verify with: Get-ScheduledTask -TaskName 'NewsEngine_ShockRealityCheck'"
```

- [ ] **Step 7: Run the script and verify registration**

Run (elevated PowerShell): `powershell -File alerting\scripts\register_reality_check_task.ps1`
Then: `Get-ScheduledTask -TaskName "NewsEngine_ShockRealityCheck"`
Expected: task listed with `State: Ready`

- [ ] **Step 8: Commit**

```bash
git add alerting/scripts/register_reality_check_task.ps1
git commit -m "chore: add Task Scheduler registration script for the weekly reality check"
```

---

## Task 10: Dashboard API route — `webapp/app.py`

**Files:**
- Modify: `webapp/app.py`
- Test: `tests/test_app_shock_alerts_route.py`

**Interfaces:**
- Consumes: `alerting.store.get_connection`, `alerting.store.list_recent_alerts` (Task 1)
- Produces: `GET /api/shock-alerts` — JSON `{"rows": [...]}`, each row shaped `{id, headline, sources, detected_at_utc, category, severity, classification_method, rationale, affected_symbols, delivery_status, reality_mismatch}`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_app_shock_alerts_route.py
from __future__ import annotations

import datetime as dt

import pytest

from alerting import store as alerting_store
from webapp.app import app

UTC = dt.timezone.utc


@pytest.fixture
def client(monkeypatch):
    conn = alerting_store.get_connection(":memory:")
    monkeypatch.setattr(alerting_store, "get_connection", lambda *a, **kw: conn)
    alerting_store.record_alert(
        conn, headline="Strait of Hormuz closed", source="reuters_business", url="https://x",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None,
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven"}],
    )
    with app.test_client() as c:
        yield c


def test_shock_alerts_route_returns_recent_rows(client):
    resp = client.get("/api/shock-alerts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["headline"] == "Strait of Hormuz closed"
    assert data["rows"][0]["severity"] == "High"
    assert data["rows"][0]["affected_symbols"] == [{"symbol": "XAUUSD", "channel": "safe_haven"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app_shock_alerts_route.py -v`
Expected: FAIL with 404 (`assert 404 == 200`)

- [ ] **Step 3: Add the route**

```python
# webapp/app.py -- add near the other GET routes (e.g. after get_print_call_history)
from alerting import store as alerting_store  # add to the existing import block at the top of the file


@app.route("/api/shock-alerts", methods=["GET"])
def get_shock_alerts():
    conn = alerting_store.get_connection()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    rows = alerting_store.list_recent_alerts(conn, since)
    return jsonify({
        "rows": [
            {
                "id": r.id, "headline": r.headline, "sources": r.sources,
                "detected_at_utc": r.detected_at_utc.isoformat(),
                "category": r.category, "severity": r.severity,
                "classification_method": r.classification_method,
                "rationale": r.rationale, "affected_symbols": r.affected_symbols,
                "delivery_status": r.delivery_status,
                "reality_mismatch": r.reality_mismatch,
            }
            for r in rows
        ],
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_app_shock_alerts_route.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add webapp/app.py tests/test_app_shock_alerts_route.py
git commit -m "feat: add read-only /api/shock-alerts dashboard route"
```

---

## Task 11: Dashboard panel — frontend

**Files:**
- Modify: `webapp/static/index.html` (new tab button + section)
- Modify: `webapp/static/app.js` (tab wiring)
- Modify: `webapp/static/js/api.js` (new fetch helper)
- Create: `webapp/static/js/shock-alerts/table.js`
- Modify: `webapp/static/style.css` (severity badge colors, reuse existing patterns)

**Interfaces:**
- Consumes: `GET /api/shock-alerts` (Task 10); `escapeHtml` from `../format.js`
- Produces: a new "Shock Alerts" tab in the existing dashboard, rendering High/Medium prominently and Low collapsed

- [ ] **Step 1: Add the tab button and section to `index.html`**

```html
<!-- add alongside the existing tab-history button, inside the same tab-bar container -->
<button id="tab-shock-alerts" class="tab-btn" role="tab" aria-selected="false" aria-controls="view-shock-alerts">Shock Alerts</button>
```

```html
<!-- add as a new top-level section, alongside view-history -->
<section id="view-shock-alerts" style="display:none" role="tabpanel" aria-labelledby="tab-shock-alerts">
  <div id="shock-alerts-empty-notice" class="stale-notice" style="display:none">No shock alerts in the last 7 days.</div>
  <div id="shock-alerts-list"></div>
  <details id="shock-alerts-low-details" style="display:none">
    <summary>Low-severity (collapsed)</summary>
    <div id="shock-alerts-low-list"></div>
  </details>
</section>
```

- [ ] **Step 2: Add the fetch helper to `api.js`**

```javascript
// webapp/static/js/api.js -- add alongside fetchHistory
export function fetchShockAlerts() {
  return fetchJson("/api/shock-alerts");
}
```

- [ ] **Step 3: Write `js/shock-alerts/table.js`**

```javascript
// webapp/static/js/shock-alerts/table.js
import { escapeHtml } from "../format.js";
import { fetchShockAlerts } from "../api.js";

let shockAlertsLoaded = false;

export async function loadShockAlertsIfNeeded() {
  if (shockAlertsLoaded) return;
  shockAlertsLoaded = true;
  try {
    const data = await fetchShockAlerts();
    renderShockAlerts(data.rows || []);
  } catch (err) {
    console.error("loadShockAlertsIfNeeded: fetch failed", err);
  }
}

const SEVERITY_COLOR = { High: "#c62828", Medium: "#ef6c00", Low: "#888" };

function _alertHtml(row) {
  const symbolsLine = (row.affected_symbols || [])
    .map((s) => `${escapeHtml(s.symbol)} (${escapeHtml(s.channel)})`)
    .join(", ") || "none currently tracked";
  const sourcesLine = (row.sources || [])
    .map((s) => `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.source)}</a>`)
    .join(", ");
  const mismatchBadge = row.reality_mismatch === true
    ? ' <span style="color:#c62828;font-weight:bold">⚠ reality check: mismatch</span>'
    : row.reality_mismatch === false
    ? ' <span style="color:#2e7d32">✓ reality check: confirmed</span>'
    : "";
  const deliveryBadge = row.severity === "High" && row.delivery_status === "failed"
    ? ' <span style="color:#c62828;font-weight:bold">⚠ push failed</span>'
    : "";
  return `<div class="shock-alert-card" style="border-left:4px solid ${SEVERITY_COLOR[row.severity] || "#888"}">
    <div><b>${escapeHtml(row.severity)} — ${escapeHtml(row.category)}</b>${deliveryBadge}</div>
    <div>${escapeHtml(row.headline)}</div>
    <div class="meta-text-sm">Affects: ${symbolsLine}</div>
    ${row.rationale ? `<div class="meta-text-sm">${escapeHtml(row.rationale)}</div>` : ""}
    <div class="meta-text-sm">Sources: ${sourcesLine}</div>
    <div class="meta-text-sm">${new Date(row.detected_at_utc).toLocaleString()}${mismatchBadge}</div>
  </div>`;
}

function renderShockAlerts(rows) {
  const emptyNotice = document.getElementById("shock-alerts-empty-notice");
  const list = document.getElementById("shock-alerts-list");
  const lowDetails = document.getElementById("shock-alerts-low-details");
  const lowList = document.getElementById("shock-alerts-low-list");

  if (rows.length === 0) {
    emptyNotice.style.display = "";
    list.innerHTML = "";
    lowDetails.style.display = "none";
    return;
  }
  emptyNotice.style.display = "none";

  const prominent = rows.filter((r) => r.severity !== "Low");
  const low = rows.filter((r) => r.severity === "Low");

  list.innerHTML = prominent.map(_alertHtml).join("");
  if (low.length > 0) {
    lowDetails.style.display = "";
    lowList.innerHTML = low.map(_alertHtml).join("");
  } else {
    lowDetails.style.display = "none";
  }
}
```

- [ ] **Step 4: Wire the tab into `app.js`**

```javascript
// webapp/static/app.js -- add import at the top, alongside the other view imports
import { loadShockAlertsIfNeeded } from "./js/shock-alerts/table.js";
```

```javascript
// add alongside the existing tab-history click handler
document.getElementById("tab-shock-alerts").addEventListener("click", () => {
  showView("shock-alerts");
  loadShockAlertsIfNeeded();
});
```

```javascript
// extend showView(name) to include the new view/tab, alongside the existing dashboard/calendar/history lines
document.getElementById("view-shock-alerts").style.display = name === "shock-alerts" ? "" : "none";
document.getElementById("tab-shock-alerts").classList.toggle("active", name === "shock-alerts");
document.getElementById("tab-shock-alerts").setAttribute("aria-selected", String(name === "shock-alerts"));
```

- [ ] **Step 5: Add minimal card styling to `style.css`**

```css
/* webapp/static/style.css -- add alongside existing card styles */
.shock-alert-card {
  background: #fff;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
```

- [ ] **Step 6: Manual verification**

Run the webapp dev server (per this project's existing `.claude/launch.json` entry, or `python webapp/app.py`), open the dashboard, click the "Shock Alerts" tab, and confirm: with no rows in `alerting/shock_alerts.db`, the empty notice shows; after manually calling `alerting.store.record_alert(...)` for a High and a Low test row (e.g. via a throwaway Python REPL session against `alerting/shock_alerts.db`), reload the tab and confirm the High row renders prominently and the Low row is collapsed behind the `<details>` toggle.

- [ ] **Step 7: Commit**

```bash
git add webapp/static/index.html webapp/static/app.js webapp/static/js/api.js webapp/static/js/shock-alerts/table.js webapp/static/style.css
git commit -m "feat: add Shock Alerts dashboard tab"
```

---

## Self-Review Notes

- **Spec coverage:** every spec section has a task — storage (Task 1), taxonomy (Task 2), triage (Task 3), dedup (Task 4), symbol relevance (Task 5), LLM classification (Task 6), Telegram delivery (Task 7), poll orchestration + Task Scheduler (Task 8), weekly reality check + Task Scheduler (Task 9), dashboard route (Task 10), dashboard panel (Task 11).
- **Corrected from the spec during planning:** the spec's Architecture section named `scoring/probability_engine.py`'s `_check_oil_shock` as something `symbol_relevance.py` would "reuse." On inspecting the real function, its signature (`_check_oil_shock(macro_backdrop) -> tuple[bool, str | None]`) takes a pre-computed `MacroBackdropRead` object and answers "is there a shock right now," not "which symbols does category X affect" — the wrong shape for this purpose, and it's a private (underscore-prefixed) function not meant for external import. Task 5 instead builds its own lightweight category→symbol-class table, informed by the same domain knowledge but not literally importing that function. This is a real correction, not a placeholder.
- **Placeholder scan:** no TBD/TODO markers; `taxonomy.py`'s keyword lists are real v1 content (not `{...}` placeholders) with an explicit, honest note that they're a starting point expected to grow.
- **Type consistency:** `TriageResult`, `ClassificationResult`, `SymbolImpact`, and `ShockAlertRow` are defined once (Tasks 3, 6, 5, 1 respectively) and referenced with the same field names in every later task that consumes them.

---

Plan complete and saved to `docs/superpowers/plans/2026-09-14-realtime-news-shock-alerting.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
