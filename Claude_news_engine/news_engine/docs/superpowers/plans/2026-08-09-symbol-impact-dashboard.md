# Symbol Impact Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Flask + vanilla-JS dashboard that shows a BUY/HOLD/SELL-style directional call per tracked symbol, driven purely by structured economic-calendar data (no article fetching), with a calendar view and a before/after diff when a re-score changes the call.

**Architecture:** New `webapp/` package, independent of `scoring/probability_engine.py`'s article pipeline. `webapp/symbols.py` classifies tickers into USD-relationship classes; `webapp/scoring_service.py` scores an event for a symbol using `EconomicEvent.usd_surprise_score()` (already built); `webapp/store.py` persists every scoring run to SQLite; `webapp/scheduler.py` re-scores on a 15-minute background loop; `webapp/app.py` is the Flask API; `webapp/static/` is the plain HTML/CSS/JS frontend.

**Tech Stack:** Python 3.14, Flask (new dependency, `requirements-webapp.txt`), stdlib `sqlite3` and `threading` (no new dependency), vanilla HTML/CSS/JS (no build step, no framework).

## Global Constraints

- No article fetching anywhere in this feature — every score comes from `EconomicEvent.usd_surprise_score()` (calendar forecast/actual only). Never call into `scoring/probability_engine.py`'s RSS/lexicon/FinBERT/LLM path from `webapp/`.
- `fx_cross` symbols (no USD leg) are never scored — always `applicable=False`, never a fabricated neutral score.
- Events with no `actual` value yet are always `pending=True`, never a fabricated score.
- No price-target UI ("Low/Target/High" row) — dropped per design approval. Cards show only the gauge, the day-strip, and the diff strip.
- Diff visualization: two-tone donut, green delta for an increase, red delta for a decrease — confirmed color scheme, not monochrome.
- New tests follow the existing project's plain-`assert`-plus-`__main__` style (see `tests/test_scoring_smoke.py`) — no pytest, no new test-framework dependency.
- SQLite DB file lives at `webapp/dashboard.db`, already covered by `.gitignore`'s `*.db` pattern — never commit it.
- Reuse `config.settings.SURPRISE_SENSITIVITY` for the sigmoid transform — don't invent a second tuning constant for the same shape of calculation.

---

### Task 1: Symbol classification

**Files:**
- Create: `webapp/__init__.py` (empty)
- Create: `webapp/symbols.py`
- Test: `tests/test_webapp_symbols.py`

**Interfaces:**
- Produces: `SymbolClass` (frozen dataclass: `symbol: str`, `symbol_class: str`, `usd_relationship: Optional[str]`), `classify_symbol(ticker: str) -> SymbolClass`, `UnrecognizedSymbolError(ValueError)`, module constants `METALS: set[str]`, `INDICES: set[str]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_webapp_symbols.py`:

```python
"""
Tests for webapp.symbols — synthetic, no network needed. Same style as
tests/test_scoring_smoke.py: plain functions with asserts, run via
__main__, no pytest dependency.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.symbols import classify_symbol, UnrecognizedSymbolError


def test_metal_classifies_inverse():
    print("=== metal ticker classifies as inverse ===")
    result = classify_symbol("XAUUSD")
    assert result.symbol_class == "metal"
    assert result.usd_relationship == "inverse"
    print("PASS\n")


def test_index_classifies_risk_sentiment():
    print("=== index ticker classifies as risk_sentiment ===")
    result = classify_symbol("US30")
    assert result.symbol_class == "index_risk"
    assert result.usd_relationship == "risk_sentiment"
    print("PASS\n")


def test_usd_base_classifies_direct():
    print("=== USDxxx classifies as fx_usd_base/direct ===")
    result = classify_symbol("USDJPY")
    assert result.symbol_class == "fx_usd_base"
    assert result.usd_relationship == "direct"
    print("PASS\n")


def test_usd_quote_classifies_inverse():
    print("=== xxxUSD classifies as fx_usd_quote/inverse ===")
    result = classify_symbol("EURUSD")
    assert result.symbol_class == "fx_usd_quote"
    assert result.usd_relationship == "inverse"
    print("PASS\n")


def test_fx_cross_has_no_usd_relationship():
    print("=== cross pair (no USD leg) has usd_relationship=None ===")
    result = classify_symbol("GBPAUD")
    assert result.symbol_class == "fx_cross"
    assert result.usd_relationship is None
    print("PASS\n")


def test_lowercase_input_normalized():
    print("=== lowercase ticker input is normalized to uppercase ===")
    result = classify_symbol("eurusd")
    assert result.symbol == "EURUSD"
    print("PASS\n")


def test_unrecognized_ticker_raises():
    print("=== malformed ticker raises UnrecognizedSymbolError ===")
    try:
        classify_symbol("NOTASYMBOL123")
        assert False, "expected UnrecognizedSymbolError"
    except UnrecognizedSymbolError:
        pass
    print("PASS\n")


if __name__ == "__main__":
    test_metal_classifies_inverse()
    test_index_classifies_risk_sentiment()
    test_usd_base_classifies_direct()
    test_usd_quote_classifies_inverse()
    test_fx_cross_has_no_usd_relationship()
    test_lowercase_input_normalized()
    test_unrecognized_ticker_raises()
    print("All symbol classification tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_webapp_symbols.py`
Expected: `ModuleNotFoundError: No module named 'webapp'`

- [ ] **Step 3: Create the empty package init**

Create `webapp/__init__.py` with no content (0 bytes).

- [ ] **Step 4: Write the implementation**

Create `webapp/symbols.py`:

```python
"""
Symbol classification for the essence-only (no-articles) scoring path.

Every tracked symbol is auto-classified from its ticker into a
SymbolClass, which decides two things: whether a USD economic event
applies to it at all, and if so, which direction a USD-bullish surprise
pushes it. This extends the same usd_relationship concept already used in
config.settings.INSTRUMENTS for XAUUSD/US30, but derives it from the
ticker pattern instead of requiring a hand-entered config line per symbol.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

METALS = {"XAUUSD", "XAGUSD"}
INDICES = {"US30", "US500", "NAS100"}

_USD_BASE_PATTERN = re.compile(r"^USD([A-Z]{3})$")   # USDJPY, USDCHF, USDCAD
_USD_QUOTE_PATTERN = re.compile(r"^([A-Z]{3})USD$")  # EURUSD, GBPUSD, AUDUSD, NZDUSD
_FX_PATTERN = re.compile(r"^[A-Z]{6}$")               # any 6 uppercase letters, e.g. GBPAUD


class UnrecognizedSymbolError(ValueError):
    """Raised when a ticker doesn't match any known symbol shape."""


@dataclass(frozen=True)
class SymbolClass:
    symbol: str
    symbol_class: str                 # "metal" | "fx_usd_base" | "fx_usd_quote" | "index_risk" | "fx_cross"
    usd_relationship: Optional[str]   # "inverse" | "direct" | "risk_sentiment" | None (fx_cross: not applicable)


def classify_symbol(ticker: str) -> SymbolClass:
    """
    Raises UnrecognizedSymbolError for anything that isn't a known metal,
    a known index, or a 6-letter FX-shaped ticker — never silently
    misclassifies.
    """
    ticker = ticker.strip().upper()

    if ticker in METALS:
        return SymbolClass(symbol=ticker, symbol_class="metal", usd_relationship="inverse")

    if ticker in INDICES:
        return SymbolClass(symbol=ticker, symbol_class="index_risk", usd_relationship="risk_sentiment")

    if _USD_BASE_PATTERN.match(ticker):
        return SymbolClass(symbol=ticker, symbol_class="fx_usd_base", usd_relationship="direct")

    if _USD_QUOTE_PATTERN.match(ticker):
        return SymbolClass(symbol=ticker, symbol_class="fx_usd_quote", usd_relationship="inverse")

    if _FX_PATTERN.match(ticker):
        return SymbolClass(symbol=ticker, symbol_class="fx_cross", usd_relationship=None)

    raise UnrecognizedSymbolError(
        f"{ticker!r} doesn't match a known metal, index, or 6-letter FX pair shape"
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python tests/test_webapp_symbols.py`
Expected: `All symbol classification tests passed.`

- [ ] **Step 6: Commit**

```bash
git add webapp/__init__.py webapp/symbols.py tests/test_webapp_symbols.py
git commit -m "feat: symbol classification for essence-only scoring"
```

---

### Task 2: Essence-only scoring service

**Files:**
- Create: `webapp/scoring_service.py`
- Test: `tests/test_webapp_scoring_service.py`

**Interfaces:**
- Consumes: `SymbolClass` and `classify_symbol` from `webapp.symbols` (Task 1); `EconomicEvent` and `EconomicEvent.usd_surprise_score() -> Optional[float]` from `data_layer.calendar_feed` (already exists); `Direction` enum (`BULLISH`/`BEARISH`/`NEUTRAL`) from `scoring.probability_engine` (already exists); `SURPRISE_SENSITIVITY` from `config.settings` (already exists).
- Produces: `EssenceScore` (dataclass: `symbol: str`, `event_title: str`, `applicable: bool`, `pending: bool`, `probability: Optional[float]`, `direction: Optional[Direction]`, `raw_score: Optional[float]`), `score_event_for_symbol(event: EconomicEvent, symbol_class: SymbolClass) -> EssenceScore`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_webapp_scoring_service.py`:

```python
"""
Tests for webapp.scoring_service — synthetic, no network needed.
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from scoring.probability_engine import Direction
from webapp.symbols import classify_symbol
from webapp.scoring_service import score_event_for_symbol


def test_fx_cross_not_applicable():
    print("=== fx_cross symbol is not applicable to a USD event ===")
    event = EconomicEvent(
        title="Non-Farm Employment Change", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
        forecast="75K", actual="44K",
    )
    symbol_class = classify_symbol("GBPAUD")
    result = score_event_for_symbol(event, symbol_class)
    assert result.applicable is False
    assert result.probability is None
    print("PASS\n")


def test_pending_event_has_no_score_yet():
    print("=== event with no actual value yet reports pending, not a fabricated score ===")
    event = EconomicEvent(
        title="Non-Farm Employment Change", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
        forecast="75K", actual=None,
    )
    symbol_class = classify_symbol("XAUUSD")
    result = score_event_for_symbol(event, symbol_class)
    assert result.applicable is True
    assert result.pending is True
    assert result.probability is None
    print("PASS\n")


def test_adp_miss_flips_gold_bullish():
    print("=== real ADP miss (75K forecast, 44K actual) scores gold BULLISH via inverse relationship ===")
    # Same real numbers used in tests/test_scoring_smoke.py's
    # test_precursor_leading_indicator — confirms this independent,
    # article-free path agrees with the precursor-contribution path,
    # since both are built on the same EconomicEvent.usd_surprise_score().
    event = EconomicEvent(
        title="ADP Nonfarm Employment Change", country="USD", impact="Medium",
        event_time_utc=dt.datetime(2026, 8, 5, 13, 0, tzinfo=UTC_TZ),
        forecast="75K", actual="44K",
    )
    symbol_class = classify_symbol("XAUUSD")
    result = score_event_for_symbol(event, symbol_class)
    assert result.applicable is True
    assert result.pending is False
    assert result.direction == Direction.BULLISH
    print(f"  probability={result.probability:.0%} raw_score={result.raw_score:+.4f}")
    print("PASS\n")


def test_adp_miss_flips_usdjpy_bearish():
    print("=== same ADP miss scores USDJPY BEARISH via direct relationship (USD weak -> USDJPY falls) ===")
    event = EconomicEvent(
        title="ADP Nonfarm Employment Change", country="USD", impact="Medium",
        event_time_utc=dt.datetime(2026, 8, 5, 13, 0, tzinfo=UTC_TZ),
        forecast="75K", actual="44K",
    )
    symbol_class = classify_symbol("USDJPY")
    result = score_event_for_symbol(event, symbol_class)
    assert result.direction == Direction.BEARISH
    print("PASS\n")


if __name__ == "__main__":
    test_fx_cross_not_applicable()
    test_pending_event_has_no_score_yet()
    test_adp_miss_flips_gold_bullish()
    test_adp_miss_flips_usdjpy_bearish()
    print("All scoring_service tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_webapp_scoring_service.py`
Expected: `ModuleNotFoundError: No module named 'webapp.scoring_service'`

- [ ] **Step 3: Write the implementation**

Create `webapp/scoring_service.py`:

```python
"""
Essence-only scoring — a symbol's directional call driven purely by
structured calendar data (forecast vs. actual), with no article
fetching/sentiment involved at all. Parallel to, and independent of, the
article-based pipeline in scoring/probability_engine.py; this is what the
dashboard uses.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from config.settings import SURPRISE_SENSITIVITY
from data_layer.calendar_feed import EconomicEvent
from scoring.probability_engine import Direction
from webapp.symbols import SymbolClass


@dataclass
class EssenceScore:
    symbol: str
    event_title: str
    applicable: bool           # False for fx_cross symbols — no USD exposure, no score at all
    pending: bool               # True if the event hasn't printed an actual value yet
    probability: Optional[float] = None    # 0.0-1.0, None if not applicable/pending
    direction: Optional[Direction] = None  # None if not applicable/pending
    raw_score: Optional[float] = None       # the underlying -1..1 symbol-directional score, None if not applicable/pending


def score_event_for_symbol(event: EconomicEvent, symbol_class: SymbolClass) -> EssenceScore:
    if symbol_class.usd_relationship is None:
        return EssenceScore(
            symbol=symbol_class.symbol, event_title=event.title,
            applicable=False, pending=False,
        )

    usd_surprise = event.usd_surprise_score()
    if usd_surprise is None:
        return EssenceScore(
            symbol=symbol_class.symbol, event_title=event.title,
            applicable=True, pending=True,
        )

    relationship = symbol_class.usd_relationship
    if relationship == "inverse":
        symbol_score = -usd_surprise
    elif relationship == "direct":
        symbol_score = usd_surprise
    elif relationship == "risk_sentiment":
        symbol_score = -usd_surprise * 0.7
    else:
        raise ValueError(f"Unknown usd_relationship {relationship!r} for {symbol_class.symbol!r}")

    probability = 0.5 + 0.5 * math.tanh(SURPRISE_SENSITIVITY * symbol_score)

    if symbol_score > 0.02:
        direction = Direction.BULLISH
    elif symbol_score < -0.02:
        direction = Direction.BEARISH
    else:
        direction = Direction.NEUTRAL

    return EssenceScore(
        symbol=symbol_class.symbol, event_title=event.title,
        applicable=True, pending=False,
        probability=probability, direction=direction, raw_score=symbol_score,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_webapp_scoring_service.py`
Expected: `All scoring_service tests passed.`

- [ ] **Step 5: Commit**

```bash
git add webapp/scoring_service.py tests/test_webapp_scoring_service.py
git commit -m "feat: essence-only per-symbol scoring from calendar surprise data"
```

---

### Task 3: SQLite persistence

**Files:**
- Create: `webapp/store.py`
- Test: `tests/test_webapp_store.py`

**Interfaces:**
- Produces: `DB_PATH: Path`, `PredictionRun` (dataclass: `id: int`, `symbol: str`, `event_title: str`, `event_time_utc: str`, `scored_at_utc: str`, `probability: float`, `direction: str`, `raw_score: float`), `get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection`, `record_run(conn, symbol, event_title, event_time_utc, probability, direction, raw_score, scored_at_utc=None) -> int`, `get_latest_two(conn, symbol, event_title) -> list[PredictionRun]`, `get_history(conn, symbol, event_title) -> list[PredictionRun]`, `add_tracked_symbol(conn, symbol) -> None`, `remove_tracked_symbol(conn, symbol) -> None`, `list_tracked_symbols(conn) -> list[str]`.
- **Important:** `get_connection`'s `db_path` default must be resolved *inside* the function body (`db_path if db_path is not None else DB_PATH`), not as the parameter's default value — a default value would bind `DB_PATH` at function-definition time, breaking tests that patch `store.DB_PATH` to point at a temp file.

- [ ] **Step 1: Write the failing test**

Create `tests/test_webapp_store.py`:

```python
"""
Tests for webapp.store — uses a temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.store import (
    get_connection, record_run, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
)


def test_round_trip_and_diff():
    print("=== store: two runs for the same (symbol, event) round-trip and diff correctly ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)

        event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
        t1 = dt.datetime(2026, 8, 5, 10, 0, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 8, 5, 10, 15, tzinfo=dt.timezone.utc)

        record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.54, "bullish", 0.20, scored_at_utc=t1)
        record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.66, "bullish", 0.35, scored_at_utc=t2)

        runs = get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
        assert len(runs) == 2
        assert runs[0].probability == 0.66, "most recent run should come first"
        assert runs[1].probability == 0.54

        delta = runs[0].probability - runs[1].probability
        assert abs(delta - 0.12) < 1e-9
        print(f"  latest={runs[0].probability:.0%} previous={runs[1].probability:.0%} delta={delta:+.0%}")

        history = get_history(conn, "XAUUSD", "Non-Farm Employment Change")
        assert len(history) == 2
        assert history[0].probability == 0.54, "history should be oldest-first"
        conn.close()
    print("PASS\n")


def test_fewer_than_two_runs():
    print("=== store: only one run recorded returns one row, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
        record_run(conn, "XAUUSD", "CPI", event_time, 0.5, "neutral", 0.0)
        runs = get_latest_two(conn, "XAUUSD", "CPI")
        assert len(runs) == 1
        conn.close()
    print("PASS\n")


def test_tracked_symbols_add_remove_list():
    print("=== store: tracked symbols add/remove/list round-trip, duplicates ignored ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)

        add_tracked_symbol(conn, "XAUUSD")
        add_tracked_symbol(conn, "EURUSD")
        add_tracked_symbol(conn, "XAUUSD")  # duplicate, should not error or double-add
        assert list_tracked_symbols(conn) == ["EURUSD", "XAUUSD"]

        remove_tracked_symbol(conn, "EURUSD")
        assert list_tracked_symbols(conn) == ["XAUUSD"]
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_round_trip_and_diff()
    test_fewer_than_two_runs()
    test_tracked_symbols_add_remove_list()
    print("All store tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_webapp_store.py`
Expected: `ModuleNotFoundError: No module named 'webapp.store'`

- [ ] **Step 3: Write the implementation**

Create `webapp/store.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_webapp_store.py`
Expected: `All store tests passed.`

- [ ] **Step 5: Commit**

```bash
git add webapp/store.py tests/test_webapp_store.py
git commit -m "feat: SQLite persistence for prediction runs and tracked symbols"
```

---

### Task 4: Background scheduler

**Files:**
- Create: `webapp/scheduler.py`
- Test: `tests/test_webapp_scheduler.py`

**Interfaces:**
- Consumes: `fetch_calendar(period) -> list[EconomicEvent]`, `filter_relevant_events(events) -> list[EconomicEvent]` from `data_layer.calendar_feed` (already exist); `classify_symbol`, `UnrecognizedSymbolError` from `webapp.symbols` (Task 1); `score_event_for_symbol` from `webapp.scoring_service` (Task 2); `get_connection`, `record_run`, `get_latest_two` from `webapp.store` (Task 3).
- Produces: `SCHEDULER_INTERVAL_SECONDS: int`, `run_scoring_cycle(tracked_symbols: list[str], db_path: Optional[Path] = None) -> None`, `start_scheduler(tracked_symbols_provider: Callable[[], list[str]]) -> None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_webapp_scheduler.py`:

```python
"""
Tests for webapp.scheduler — no live network, fetch_calendar is patched.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
import webapp.store as store
import webapp.scheduler as scheduler


def _fake_events():
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="75K", actual="44K",
        )
    ]


def test_scoring_cycle_writes_new_rows_and_skips_duplicates():
    print("=== scheduler: writes a row on first cycle, skips an identical second cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events: events):

            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            conn = store.get_connection(db_path)
            runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
            assert len(runs) == 1, "first cycle should write exactly one row"

            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
            assert len(runs) == 1, "second identical cycle should NOT write a duplicate row"
            conn.close()
    print("PASS\n")


def test_unrecognized_symbol_skipped_not_crashed():
    print("=== scheduler: an unrecognized tracked symbol is skipped, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events: events):
            scheduler.run_scoring_cycle(["NOTREAL123"], db_path=db_path)  # must not raise
    print("PASS\n")


if __name__ == "__main__":
    test_scoring_cycle_writes_new_rows_and_skips_duplicates()
    test_unrecognized_symbol_skipped_not_crashed()
    print("All scheduler tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_webapp_scheduler.py`
Expected: `ModuleNotFoundError: No module named 'webapp.scheduler'`

- [ ] **Step 3: Write the implementation**

Create `webapp/scheduler.py`:

```python
"""
Background poll loop — every SCHEDULER_INTERVAL_SECONDS, re-fetches the
calendar and re-scores every tracked symbol against every applicable
high-impact USD event, persisting a new row only when the score actually
changed from the last stored run (avoids writing identical rows every
cycle when nothing new has printed).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events
from webapp.scoring_service import score_event_for_symbol
from webapp.store import get_connection, record_run, get_latest_two
from webapp.symbols import classify_symbol, UnrecognizedSymbolError

SCHEDULER_INTERVAL_SECONDS = 15 * 60


def run_scoring_cycle(tracked_symbols: list[str], db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    try:
        all_events = fetch_calendar("thisweek")
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop or wipe existing data
        print(f"[scheduler] WARNING: calendar fetch failed, keeping existing data: {exc}")
        conn.close()
        return

    events = filter_relevant_events(all_events)

    for ticker in tracked_symbols:
        try:
            symbol_class = classify_symbol(ticker)
        except UnrecognizedSymbolError as exc:
            print(f"[scheduler] WARNING: skipping unrecognized symbol {ticker!r}: {exc}")
            continue

        for event in events:
            result = score_event_for_symbol(event, symbol_class)
            if not result.applicable or result.pending:
                continue

            existing = get_latest_two(conn, ticker, event.title)
            if existing and abs(existing[0].probability - result.probability) < 1e-6:
                continue  # unchanged since last cycle, don't write a duplicate row

            record_run(
                conn, ticker, event.title, event.event_time_utc,
                result.probability, result.direction.value, result.raw_score,
            )
            print(f"[scheduler] recorded {ticker} / {event.title}: {result.probability:.0%} {result.direction.value}")

    conn.close()


def start_scheduler(tracked_symbols_provider: Callable[[], list[str]]) -> None:
    """
    tracked_symbols_provider: a zero-arg callable returning the current
    list of tracked tickers (called fresh each cycle, so symbols added/
    removed via the API take effect without restarting the scheduler).
    """
    def _loop():
        while True:
            run_scoring_cycle(tracked_symbols_provider())
            time.sleep(SCHEDULER_INTERVAL_SECONDS)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_webapp_scheduler.py`
Expected: `All scheduler tests passed.`

- [ ] **Step 5: Commit**

```bash
git add webapp/scheduler.py tests/test_webapp_scheduler.py
git commit -m "feat: 15-minute background scoring scheduler"
```

---

### Task 5: Flask API

**Files:**
- Create: `requirements-webapp.txt`
- Create: `webapp/app.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: everything from Tasks 1-4 (`classify_symbol`, `UnrecognizedSymbolError`, `score_event_for_symbol` indirectly via scheduler, `get_connection`, `get_latest_two`, `get_history`, `add_tracked_symbol`, `remove_tracked_symbol`, `list_tracked_symbols`, `start_scheduler`, `fetch_calendar`, `filter_relevant_events`).
- Produces: Flask `app` object with routes `GET/POST /api/symbols`, `DELETE /api/symbols/<ticker>`, `GET /api/calendar`, `GET /api/predictions`, `GET /api/predictions/<symbol>/history`, `GET /` (serves `webapp/static/index.html`). `DEFAULT_SYMBOLS: list[str]`, `_ensure_defaults() -> None`.

- [ ] **Step 1: Create the requirements file**

Create `requirements-webapp.txt`:

```
# Only needed to run the dashboard (webapp/). Core scoring/backtest
# pipeline has no dependency on this — install only if you want the UI.
flask
```

- [ ] **Step 2: Install Flask**

Run: `pip install -r requirements-webapp.txt`
Expected: Flask installs successfully.

- [ ] **Step 3: Write the failing test**

Create `tests/test_webapp_app.py`:

```python
"""
Tests for webapp.app — uses Flask's test client, no live server or
network needed (calendar fetch is patched).
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
import webapp.app as webapp_app
import webapp.store as store


def _fake_events():
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="75K", actual="44K",
        )
    ]


def test_add_list_remove_symbol():
    print("=== app: POST/GET/DELETE /api/symbols round-trips ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()

            resp = client.post("/api/symbols", json={"ticker": "eurusd"})
            assert resp.status_code == 201
            assert resp.get_json()["symbol"] == "EURUSD"

            resp = client.get("/api/symbols")
            symbols = [s["symbol"] for s in resp.get_json()]
            assert symbols == ["EURUSD"]

            resp = client.delete("/api/symbols/EURUSD")
            assert resp.status_code == 204

            resp = client.get("/api/symbols")
            assert resp.get_json() == []
    print("PASS\n")


def test_add_unrecognized_symbol_rejected():
    print("=== app: POST /api/symbols with a malformed ticker returns 400 ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()
            resp = client.post("/api/symbols", json={"ticker": "NOTASYMBOL123"})
            assert resp.status_code == 400
            assert "error" in resp.get_json()
    print("PASS\n")


def test_predictions_endpoint_reflects_stored_runs():
    print("=== app: /api/predictions surfaces latest + previous run with delta info ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(webapp_app, "fetch_calendar", return_value=_fake_events()), \
             patch.object(webapp_app, "filter_relevant_events", side_effect=lambda events: events):

            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.54, "bullish", 0.20)
            store.record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.66, "bullish", 0.35)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            assert len(data) == 1
            events = data[0]["events"]
            assert len(events) == 1
            assert events[0]["probability"] == 0.66
            assert events[0]["previous_probability"] == 0.54
    print("PASS\n")


if __name__ == "__main__":
    test_add_list_remove_symbol()
    test_add_unrecognized_symbol_rejected()
    test_predictions_endpoint_reflects_stored_runs()
    print("All webapp.app tests passed.")
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python tests/test_webapp_app.py`
Expected: `ModuleNotFoundError: No module named 'webapp.app'` (or `flask` import error if Step 2 was skipped)

- [ ] **Step 5: Write the implementation**

Create `webapp/app.py`:

```python
"""
Flask API for the symbol impact dashboard — serves tracked symbols,
calendar events, and current/previous predictions to the frontend in
webapp/static/. Does not do any scoring itself; that's webapp/scheduler.py's
job, running in a background thread started at app startup.
"""
from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events
from webapp.scheduler import start_scheduler
from webapp.store import (
    get_connection, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
)
from webapp.symbols import classify_symbol, UnrecognizedSymbolError

app = Flask(__name__, static_folder="static")

DEFAULT_SYMBOLS = ["XAUUSD", "US30"]


def _ensure_defaults() -> None:
    conn = get_connection()
    if not list_tracked_symbols(conn):
        for symbol in DEFAULT_SYMBOLS:
            add_tracked_symbol(conn, symbol)
    conn.close()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/symbols", methods=["GET"])
def get_symbols():
    conn = get_connection()
    symbols = list_tracked_symbols(conn)
    conn.close()
    return jsonify([
        {"symbol": s.symbol, "symbol_class": s.symbol_class, "usd_relationship": s.usd_relationship}
        for s in (classify_symbol(sym) for sym in symbols)
    ])


@app.route("/api/symbols", methods=["POST"])
def add_symbol():
    data = request.get_json(silent=True) or {}
    ticker = (data.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    try:
        symbol_class = classify_symbol(ticker)
    except UnrecognizedSymbolError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    add_tracked_symbol(conn, symbol_class.symbol)
    conn.close()
    return jsonify({
        "symbol": symbol_class.symbol,
        "symbol_class": symbol_class.symbol_class,
        "usd_relationship": symbol_class.usd_relationship,
    }), 201


@app.route("/api/symbols/<ticker>", methods=["DELETE"])
def remove_symbol(ticker: str):
    conn = get_connection()
    remove_tracked_symbol(conn, ticker.strip().upper())
    conn.close()
    return "", 204


@app.route("/api/calendar", methods=["GET"])
def get_calendar():
    try:
        events = filter_relevant_events(fetch_calendar("thisweek"))
    except Exception as exc:  # noqa: BLE001 — a failed live fetch must not 500 the whole dashboard
        return jsonify({"error": f"calendar fetch failed: {exc}", "events": []}), 200
    return jsonify({
        "events": [
            {
                "title": e.title, "country": e.country, "impact": e.impact,
                "event_time_utc": e.event_time_utc.isoformat(),
                "forecast": e.forecast, "actual": e.actual,
            }
            for e in events
        ],
    })


@app.route("/api/predictions", methods=["GET"])
def get_predictions():
    conn = get_connection()
    symbols = list_tracked_symbols(conn)
    try:
        events = filter_relevant_events(fetch_calendar("thisweek"))
    except Exception:
        events = []

    predictions = []
    for ticker in symbols:
        symbol_class = classify_symbol(ticker)
        entry = {"symbol": ticker, "symbol_class": symbol_class.symbol_class, "events": []}
        for event in events:
            runs = get_latest_two(conn, ticker, event.title)
            if not runs:
                continue
            latest = runs[0]
            previous = runs[1] if len(runs) > 1 else None
            entry["events"].append({
                "event_title": event.title,
                "event_time_utc": event.event_time_utc.isoformat(),
                "probability": latest.probability,
                "direction": latest.direction,
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
            })
        predictions.append(entry)

    conn.close()
    return jsonify(predictions)


@app.route("/api/predictions/<symbol>/history", methods=["GET"])
def get_prediction_history(symbol: str):
    event_title = request.args.get("event_title", "")
    conn = get_connection()
    runs = get_history(conn, symbol.strip().upper(), event_title)
    conn.close()
    return jsonify([
        {"scored_at_utc": r.scored_at_utc, "probability": r.probability, "direction": r.direction}
        for r in runs
    ])


if __name__ == "__main__":
    _ensure_defaults()
    start_scheduler(lambda: list_tracked_symbols(get_connection()))
    app.run(port=5001, debug=False)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python tests/test_webapp_app.py`
Expected: `All webapp.app tests passed.`

- [ ] **Step 7: Commit**

```bash
git add requirements-webapp.txt webapp/app.py tests/test_webapp_app.py
git commit -m "feat: Flask API for the symbol impact dashboard"
```

---

### Task 6: Frontend — dashboard + calendar UI

**Files:**
- Create: `webapp/static/index.html`
- Create: `webapp/static/style.css`
- Create: `webapp/static/app.js`

**Interfaces:**
- Consumes: `GET /api/symbols`, `POST /api/symbols`, `DELETE /api/symbols/<ticker>`, `GET /api/calendar`, `GET /api/predictions` (all from Task 5). Response shapes match exactly what `webapp/app.py`'s routes return — see Task 5's Interfaces block.
- No automated test for this task — plain frontend code has no test harness in this codebase and the design spec scopes UI verification to manual checks (`docs/superpowers/specs/2026-08-09-symbol-impact-dashboard-design.md`, Testing section: "No live-browser/UI automation testing in scope for v1"). Verification is Step 3 below: run the app and check it in a browser.

- [ ] **Step 1: Create the HTML shell**

Create `webapp/static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>News Engine — Symbol Dashboard</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header>
  <h1>Symbol Impact Dashboard</h1>
  <nav>
    <button id="tab-dashboard" class="tab-btn active">Dashboard</button>
    <button id="tab-calendar" class="tab-btn">Calendar</button>
  </nav>
</header>

<section id="view-dashboard">
  <form id="add-symbol-form">
    <input id="add-symbol-input" placeholder="Add symbol e.g. EURUSD" maxlength="6" />
    <button type="submit">Add</button>
  </form>
  <div id="cards" class="cards-grid"></div>
</section>

<section id="view-calendar" style="display:none">
  <div id="calendar-grid"></div>
  <ul id="calendar-list"></ul>
</section>

<script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create the stylesheet**

Create `webapp/static/style.css`:

```css
:root {
  --bullish: #2e7d32;
  --bullish-light: #a5d6a7;
  --bearish: #c62828;
  --neutral: #888;
  --border: #ddd;
}

* { box-sizing: border-box; }
body { font-family: system-ui, sans-serif; margin: 0; padding: 0 16px 40px; background: #fafafa; color: #222; }

header { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; }
header h1 { font-size: 18px; margin: 0; }
nav .tab-btn { background: none; border: 1px solid var(--border); padding: 6px 14px; margin-left: 8px; border-radius: 6px; cursor: pointer; }
nav .tab-btn.active { background: #222; color: #fff; border-color: #222; }

#add-symbol-form { display: flex; gap: 8px; margin-bottom: 16px; }
#add-symbol-input { padding: 8px; border: 1px solid var(--border); border-radius: 6px; text-transform: uppercase; }
#add-symbol-form button { padding: 8px 16px; border: none; border-radius: 6px; background: #222; color: #fff; cursor: pointer; }

.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }

.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.card-header h3 { margin: 0; font-size: 15px; }
.remove-btn { background: none; border: none; color: #999; cursor: pointer; font-size: 14px; }

.diff-strip { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; padding: 8px; background: #f5f5f5; border-radius: 8px; font-size: 12px; }
.diff-strip .delta-up { color: var(--bullish); font-weight: bold; }
.diff-strip .delta-down { color: var(--bearish); font-weight: bold; }

.gauge-row { display: flex; align-items: center; gap: 14px; }
.gauge-label { font-weight: bold; font-size: 16px; }
.gauge-label.bullish { color: var(--bullish); }
.gauge-label.bearish { color: var(--bearish); }
.gauge-label.neutral { color: var(--neutral); }

.not-applicable, .pending { color: #999; font-size: 13px; padding: 20px 0; text-align: center; }

.day-strip { display: flex; gap: 4px; margin-top: 14px; overflow-x: auto; }
.day-cell { flex: 0 0 auto; padding: 6px 8px; font-size: 11px; text-align: center; border-radius: 6px; border: 1px solid transparent; background: #f0f0f0; }
.day-cell.today { border: 2px solid var(--bullish); background: #e8f5e9; font-weight: bold; }
.day-cell.event { border: 2px solid #ef6c00; background: #fff3e0; font-weight: bold; }

#calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-bottom: 16px; }
.cal-cell { min-height: 60px; padding: 6px; border: 1px solid var(--border); border-radius: 6px; font-size: 12px; background: #fff; }
.cal-cell.today { border: 2px solid var(--bullish); }
.cal-cell .cal-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #ef6c00; margin-right: 3px; }

#calendar-list { list-style: none; padding: 0; }
#calendar-list li { padding: 8px; border-bottom: 1px solid var(--border); font-size: 13px; }
```

- [ ] **Step 3: Create the frontend logic**

Create `webapp/static/app.js`:

```javascript
const POLL_INTERVAL_MS = 60_000;

const cardsEl = document.getElementById("cards");
const calendarGridEl = document.getElementById("calendar-grid");
const calendarListEl = document.getElementById("calendar-list");
const addForm = document.getElementById("add-symbol-form");
const addInput = document.getElementById("add-symbol-input");

document.getElementById("tab-dashboard").addEventListener("click", () => showView("dashboard"));
document.getElementById("tab-calendar").addEventListener("click", () => showView("calendar"));

function showView(name) {
  document.getElementById("view-dashboard").style.display = name === "dashboard" ? "" : "none";
  document.getElementById("view-calendar").style.display = name === "calendar" ? "" : "none";
  document.getElementById("tab-dashboard").classList.toggle("active", name === "dashboard");
  document.getElementById("tab-calendar").classList.toggle("active", name === "calendar");
}

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticker = addInput.value.trim().toUpperCase();
  if (!ticker) return;
  const resp = await fetch("/api/symbols", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    alert(body.error || "Could not add symbol");
    return;
  }
  addInput.value = "";
  await refreshDashboard();
});

async function removeSymbol(ticker) {
  await fetch(`/api/symbols/${ticker}`, { method: "DELETE" });
  await refreshDashboard();
}

function directionLabel(direction) {
  if (direction === "bullish") return "BUY";
  if (direction === "bearish") return "SELL";
  return "HOLD";
}

function directionClass(direction) {
  if (direction === "bullish") return "bullish";
  if (direction === "bearish") return "bearish";
  return "neutral";
}

function gaugeSvg(probability, direction) {
  const pct = Math.round(probability * 100);
  const color = direction === "bullish" ? "#2e7d32" : direction === "bearish" ? "#c62828" : "#888";
  const circumference = 2 * Math.PI * 26;
  const filled = (pct / 100) * circumference;
  return `
    <svg width="70" height="70" viewBox="0 0 70 70">
      <circle cx="35" cy="35" r="26" fill="none" stroke="#eee" stroke-width="7"/>
      <circle cx="35" cy="35" r="26" fill="none" stroke="${color}" stroke-width="7"
        stroke-dasharray="${filled} ${circumference}" stroke-linecap="round"
        transform="rotate(-90 35 35)"/>
      <text x="35" y="39" text-anchor="middle" font-size="13" font-weight="bold">${pct}%</text>
    </svg>`;
}

function diffPieSvg(previousPct, delta) {
  const isUp = delta >= 0;
  const baseColor = "#a5d6a7";
  const deltaColor = isUp ? "#2e7d32" : "#c62828";
  const basePct = isUp ? previousPct : previousPct + delta; // the smaller of the two — the part that's "still true"
  const deltaAbs = Math.abs(delta);
  return `
    <svg width="44" height="44" viewBox="0 0 32 32">
      <circle r="14" cx="16" cy="16" fill="#eee"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${baseColor}" stroke-width="14"
        stroke-dasharray="${basePct} 100" transform="rotate(-90 16 16)"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${deltaColor}" stroke-width="14" opacity="0.9"
        stroke-dasharray="${deltaAbs} 100" stroke-dashoffset="${-basePct}" transform="rotate(-90 16 16)"/>
    </svg>`;
}

function dayStripHtml(eventTimeUtc) {
  const today = new Date();
  const eventDate = new Date(eventTimeUtc);
  const cells = [];
  for (let offset = -4; offset <= 10; offset++) {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    const isToday = offset === 0;
    const isEvent = d.toDateString() === eventDate.toDateString();
    const classes = ["day-cell"];
    if (isToday) classes.push("today");
    if (isEvent) classes.push("event");
    cells.push(`<div class="${classes.join(" ")}">${d.getDate()}</div>`);
  }
  return `<div class="day-strip">${cells.join("")}</div>`;
}

function renderCard(symbolEntry) {
  const { symbol, symbol_class, events } = symbolEntry;
  const el = document.createElement("div");
  el.className = "card";

  let body = `<div class="card-header"><h3>${symbol}</h3><button class="remove-btn" data-symbol="${symbol}">Remove</button></div>`;

  if (symbol_class === "fx_cross") {
    body += `<div class="not-applicable">No USD exposure for tracked events</div>`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  if (!events || events.length === 0) {
    body += `<div class="pending">Awaiting next tracked event</div>`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  const next = events[0];
  const pct = Math.round(next.probability * 100);
  const dirClass = directionClass(next.direction);

  const hasPreviousChange = next.previous_probability !== null && next.previous_probability !== undefined
    && Math.abs(next.previous_probability - next.probability) > 1e-6;

  if (hasPreviousChange) {
    const prevPct = Math.round(next.previous_probability * 100);
    const delta = pct - prevPct;
    body += `<div class="diff-strip">${diffPieSvg(prevPct, delta)}
      <div>Previous: <b>${directionLabel(next.previous_direction)} ${prevPct}%</b><br>
      <span class="${delta >= 0 ? 'delta-up' : 'delta-down'}">${delta >= 0 ? '▲' : '▼'} ${delta >= 0 ? '+' : ''}${delta}pp → now ${pct}%</span></div>
    </div>`;
  }

  body += `<div class="gauge-row">${gaugeSvg(next.probability, next.direction)}
    <div><div class="gauge-label ${dirClass}">${directionLabel(next.direction)} ${pct}%</div>
    <div style="font-size:12px;color:#888">${next.event_title}</div></div></div>`;
  body += dayStripHtml(next.event_time_utc);

  el.innerHTML = body;
  el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
  return el;
}

async function refreshDashboard() {
  const resp = await fetch("/api/predictions");
  const data = await resp.json();
  cardsEl.innerHTML = "";
  data.forEach((entry) => cardsEl.appendChild(renderCard(entry)));
}

async function refreshCalendar() {
  const resp = await fetch("/api/calendar");
  const data = await resp.json();
  const events = data.events || [];

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startWeekday = firstDay.getDay();

  const eventsByDate = {};
  events.forEach((e) => {
    const d = new Date(e.event_time_utc).toDateString();
    (eventsByDate[d] = eventsByDate[d] || []).push(e);
  });

  let cells = "";
  for (let i = 0; i < startWeekday; i++) cells += `<div class="cal-cell"></div>`;
  for (let day = 1; day <= daysInMonth; day++) {
    const cellDate = new Date(year, month, day);
    const isToday = cellDate.toDateString() === today.toDateString();
    const dayEvents = eventsByDate[cellDate.toDateString()] || [];
    const dots = dayEvents.map(() => `<span class="cal-dot"></span>`).join("");
    cells += `<div class="cal-cell ${isToday ? "today" : ""}">${day}<br>${dots}</div>`;
  }
  calendarGridEl.innerHTML = cells;

  calendarListEl.innerHTML = events
    .map((e) => `<li>${new Date(e.event_time_utc).toLocaleString()} — ${e.title} (${e.impact})</li>`)
    .join("");
}

async function refreshAll() {
  await refreshDashboard();
  await refreshCalendar();
}

refreshAll();
setInterval(refreshAll, POLL_INTERVAL_MS);
```

- [ ] **Step 4: Manual verification**

Run: `python webapp/app.py`
Then open `http://localhost:5001` in a browser.
Expected: Dashboard tab shows cards for XAUUSD and US30 (the defaults) — likely "Awaiting next tracked event" until the scheduler's first cycle completes (up to 15 minutes, or trigger one manually per Step 5 below). Calendar tab shows the current month grid with today's cell boxed and dots on days with tracked USD events.

- [ ] **Step 5: Trigger an immediate scoring cycle for faster manual verification**

Run this in a second terminal while the app is running, to populate data without waiting 15 minutes:

```bash
python -c "
from webapp.scheduler import run_scoring_cycle
from webapp.store import get_connection, list_tracked_symbols
run_scoring_cycle(list_tracked_symbols(get_connection()))
"
```

Refresh the browser — cards should now show real gauge values (or "Awaiting next tracked event" / "No USD exposure" if no applicable event has an `actual` value yet this week).

- [ ] **Step 6: Commit**

```bash
git add webapp/static/index.html webapp/static/style.css webapp/static/app.js
git commit -m "feat: dashboard and calendar frontend"
```

---

### Task 7: Wire-up — README and final smoke check

**Files:**
- Modify: `README.md`

**Interfaces:**
- None — documentation only.

- [ ] **Step 1: Add a dashboard section to the README**

In `README.md`, after the "## Architecture" section's code block (the one listing `config/`, `data_layer/`, `scoring/`, `scripts/`, `tests/`), add:

```markdown
## Symbol impact dashboard (optional)

A local web dashboard showing a BUY/HOLD/SELL-style call per tracked
symbol, driven entirely by structured calendar data (forecast vs.
actual) — no article fetching, separate from the pipeline above. See
`docs/superpowers/specs/2026-08-09-symbol-impact-dashboard-design.md`
for the full design.

```bash
pip install -r requirements-webapp.txt
python webapp/app.py
```

Then open `http://localhost:5001`. Defaults to tracking XAUUSD and US30;
add more symbols from the dashboard itself — tickers are auto-classified
(metal / USD-base FX / USD-quote FX / risk index / non-USD cross pair)
from the symbol shape, no manual config needed. A background thread
re-scores every 15 minutes; `webapp/dashboard.db` (gitignored) persists
history across restarts so the before/after diff still works after you
close and reopen the app.
```

- [ ] **Step 2: Run every test file in the project to confirm nothing regressed**

Run:
```bash
python tests/test_scoring_smoke.py
python tests/test_webapp_symbols.py
python tests/test_webapp_scoring_service.py
python tests/test_webapp_store.py
python tests/test_webapp_scheduler.py
python tests/test_webapp_app.py
```
Expected: every file prints its own "All ... passed." line, no failures.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the symbol impact dashboard"
```
