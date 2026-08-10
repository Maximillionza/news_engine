# Dukascopy Auto-Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-confirm clear post-event price moves for predictions sitting in the backtest accumulator's outcome queue, using free Dukascopy historical price data, leaving ambiguous/failed cases in the existing manual-review flow unchanged.

**Architecture:** A thin fetch wrapper (`data_layer/dukascopy_feed.py`) around the `dukascopy-python` library returns a single price at a timestamp; a classifier (`scoring/outcome_classifier.py`) compares prices 30 minutes apart and calls a move >=0.15% bullish/bearish, anything smaller or any fetch failure ambiguous; `scripts/confirm_backtest_outcomes.py` gets an additive `--auto` flag that runs the classifier over everything in `get_predictions_awaiting_outcome()`, auto-recording clear cases via the existing `record_outcome()` and leaving the rest exactly where they already were.

**Tech Stack:** Python 3.14, `dukascopy-python` (new, MIT license, pulls in `pandas` + `requests`), stdlib `datetime`/`dataclasses`, plain `assert`+`print` tests matching this repo's existing convention (not pytest).

## Global Constraints

- New dependency (`dukascopy-python`, `pandas`) goes in a new `requirements-dukascopy.txt`, following the existing opt-in-file pattern (`requirements-webapp.txt`, `requirements-contextual.txt`) — the core RSS-only pipeline must not gain this dependency by default.
- `MEASUREMENT_WINDOW_MINUTES = 30`, `CLEAR_MOVE_THRESHOLD_PCT = 0.15` — exact values from the approved spec, module-level constants, not buried in function defaults.
- Never auto-classify `neutral`. A move below the threshold is ambiguous (`direction=None`), not a confident "no reaction" call.
- No live network calls in any test — every Dukascopy-touching test mocks at the function boundary (`dukascopy_python.fetch` or this project's own `get_price_at`/`classify` wrappers, depending on which layer is under test).
- Tests are plain `assert` + `print` + an `if __name__ == "__main__":` block calling every test function in order, exactly matching every existing file under `tests/` — not pytest, anywhere.
- `record_outcome()` (in `scoring/backtest_store.py`) already validates `actual_direction` against the `Direction` enum — the auto-confirm path must call it exactly as-is, not reimplement or bypass that validation.
- Branch → work → `git merge --no-ff` into `master` → delete branch when the whole plan is done (this project's established convention, no remote, no PRs). Commit after every task's tests pass, on the feature branch.
- End every commit message with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

### Task 1: Dukascopy fetch wrapper — `data_layer/dukascopy_feed.py`

**Files:**
- Create: `requirements-dukascopy.txt`
- Create: `data_layer/dukascopy_feed.py`
- Test: `tests/test_dukascopy_feed.py`

**Interfaces:**
- Produces: `PricePoint` (dataclass, field `price: float`), `get_price_at(instrument: str, when_utc: dt.datetime) -> Optional[PricePoint]` — raises `ValueError` for an instrument with no Dukascopy mapping (a caller bug, not a data-availability issue); returns `None` for any fetch failure or an empty result window. `instrument` accepts exactly the two strings `config.settings.INSTRUMENTS` already uses: `"XAUUSD"`, `"US30"`.

- [ ] **Step 1: Create the opt-in requirements file**

Create `requirements-dukascopy.txt`:

```
# Only needed for scripts/confirm_backtest_outcomes.py's --auto flag (Dukascopy
# price-based outcome auto-confirmation). Core scoring/backtest pipeline has no
# dependency on this — install only if you want auto-confirmation.
dukascopy-python>=4.0.1
```

- [ ] **Step 2: Install it**

Run: `pip install -r requirements-dukascopy.txt`
Expected: installs `dukascopy-python`, `pandas`, and any transitive deps without error.

- [ ] **Step 3: Write the failing tests**

Create `tests/test_dukascopy_feed.py`:

```python
"""
Tests for data_layer/dukascopy_feed.py — no live network, dukascopy_python.fetch
is mocked with synthetic pandas DataFrames.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import data_layer.dukascopy_feed as dukascopy_feed


def test_get_price_at_returns_first_tick_price():
    print("=== dukascopy_feed: get_price_at returns the first tick's bid price ===")
    when = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    fake_df = pd.DataFrame({
        "bidPrice": [2415.32, 2415.40],
        "askPrice": [2415.50, 2415.58],
    })
    with patch.object(dukascopy_feed.dukascopy_python, "fetch", return_value=fake_df) as mock_fetch:
        result = dukascopy_feed.get_price_at("XAUUSD", when)
        assert result is not None
        assert result.price == 2415.32, "should use the FIRST row's bidPrice, not e.g. the last"
        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert args[3] == when, "fetch window must start exactly at when_utc — no lookahead"
    print("PASS\n")


def test_get_price_at_returns_none_on_empty_window():
    print("=== dukascopy_feed: get_price_at returns None when the fetch window has no ticks (market closed/gap) ===")
    when = dt.datetime(2026, 8, 8, 3, 0, tzinfo=dt.timezone.utc)  # a Saturday — market closed
    fake_df = pd.DataFrame({"bidPrice": [], "askPrice": []})
    with patch.object(dukascopy_feed.dukascopy_python, "fetch", return_value=fake_df):
        result = dukascopy_feed.get_price_at("XAUUSD", when)
        assert result is None
    print("PASS\n")


def test_get_price_at_returns_none_on_fetch_exception():
    print("=== dukascopy_feed: get_price_at returns None (not a crash) when fetch() raises ===")
    when = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(dukascopy_feed.dukascopy_python, "fetch", side_effect=Exception("network down")):
        result = dukascopy_feed.get_price_at("US30", when)
        assert result is None
    print("PASS\n")


def test_get_price_at_rejects_unmapped_instrument():
    print("=== dukascopy_feed: get_price_at raises a clear ValueError for an instrument with no Dukascopy mapping ===")
    when = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    try:
        dukascopy_feed.get_price_at("EURUSD", when)
        raise AssertionError("expected ValueError for an unmapped instrument")
    except ValueError as e:
        assert "EURUSD" in str(e)
    print("PASS\n")


if __name__ == "__main__":
    test_get_price_at_returns_first_tick_price()
    test_get_price_at_returns_none_on_empty_window()
    test_get_price_at_returns_none_on_fetch_exception()
    test_get_price_at_rejects_unmapped_instrument()
    print("All dukascopy_feed tests passed.")
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python tests/test_dukascopy_feed.py`
Expected: `ModuleNotFoundError: No module named 'data_layer.dukascopy_feed'`

- [ ] **Step 5: Write the implementation**

Create `data_layer/dukascopy_feed.py`:

```python
"""
Thin wrapper around the dukascopy-python library (see
requirements-dukascopy.txt — opt-in, not a core dependency) for fetching a
single real historical price at a given UTC instant. Used by
scoring/outcome_classifier.py to auto-confirm backtest accumulator
predictions instead of manual research — see
docs/superpowers/specs/2026-08-10-dukascopy-outcome-confirmation-design.md.

Contains the third-party dependency's response shape (a pandas DataFrame) to
this one file — callers only ever see PricePoint, same pattern
data_layer/news_feed.py already uses to contain Alpha Vantage's response shape.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import dukascopy_python
from dukascopy_python.instruments import (
    INSTRUMENT_FX_METALS_XAU_USD,
    INSTRUMENT_IDX_AMERICA_E_D_J_IND,
)

# Tracked instrument (config.settings.INSTRUMENTS key) -> Dukascopy's own
# instrument identifier. Deliberately not reusing INSTRUMENTS directly here —
# its values are UI labels/relationships, not Dukascopy identifiers.
_INSTRUMENT_MAP = {
    "XAUUSD": INSTRUMENT_FX_METALS_XAU_USD,
    "US30": INSTRUMENT_IDX_AMERICA_E_D_J_IND,
}

# A short window is enough to catch the next real tick without pulling a
# large range. BID consistently (not ASK, not a mid) — an arbitrary but fixed
# choice, avoids spread noise from mixing sides across two measurement points.
_FETCH_WINDOW_MINUTES = 5


@dataclass
class PricePoint:
    price: float


def get_price_at(instrument: str, when_utc: dt.datetime) -> Optional[PricePoint]:
    """
    Returns the price of the first tick AT OR AFTER when_utc — same
    no-lookahead discipline event_context.py already enforces on the
    prediction side, applied here on the confirmation side. Returns None on
    any fetch failure, or if the window contains no ticks at all (market
    closed, data gap) — never raises out to the caller for a data-
    availability reason, matching every other feed module in this codebase.
    Raises ValueError for an instrument this module doesn't know how to map
    — that's a caller bug, not a data-availability issue, so it's not
    swallowed into None like the data-availability cases above.
    """
    if instrument not in _INSTRUMENT_MAP:
        raise ValueError(
            f"instrument={instrument!r} has no Dukascopy mapping — "
            f"known instruments: {sorted(_INSTRUMENT_MAP)}"
        )

    dukascopy_instrument = _INSTRUMENT_MAP[instrument]
    window_end = when_utc + dt.timedelta(minutes=_FETCH_WINDOW_MINUTES)
    try:
        df = dukascopy_python.fetch(
            dukascopy_instrument,
            dukascopy_python.INTERVAL_TICK,
            dukascopy_python.OFFER_SIDE_BID,
            when_utc,
            window_end,
        )
    except Exception as exc:  # noqa: BLE001 — a failed fetch must degrade to None, never crash the caller
        print(f"[dukascopy_feed] WARNING: fetch failed for {instrument} at {when_utc.isoformat()}: {exc}")
        return None

    if df is None or df.empty:
        return None

    return PricePoint(price=float(df.iloc[0]["bidPrice"]))
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python tests/test_dukascopy_feed.py`
Expected: `All dukascopy_feed tests passed.`

- [ ] **Step 7: Commit**

```bash
cd "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
git add requirements-dukascopy.txt data_layer/dukascopy_feed.py tests/test_dukascopy_feed.py
git commit -m "$(cat <<'EOF'
feat: add Dukascopy price fetch wrapper for outcome auto-confirmation

get_price_at(instrument, when_utc) returns the first real tick at or
after the given UTC instant, using the dukascopy-python library (new
opt-in dependency, requirements-dukascopy.txt). Degrades to None on any
fetch failure or empty result window; raises ValueError only for a
caller passing an instrument with no Dukascopy mapping.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Outcome classifier — `scoring/outcome_classifier.py`

**Files:**
- Create: `scoring/outcome_classifier.py`
- Test: `tests/test_outcome_classifier.py`

**Interfaces:**
- Consumes: `data_layer.dukascopy_feed.get_price_at(instrument: str, when_utc: dt.datetime) -> Optional[PricePoint]` (Task 1), `data_layer.dukascopy_feed.PricePoint` (field `price: float`), `scoring.probability_engine.Direction` (existing enum, members `BULLISH`/`BEARISH`/`NEUTRAL`).
- Produces: `ClassificationResult` (dataclass: `direction: Optional[Direction]`, `move_pct: Optional[float]`, `note: str`), `classify(instrument: str, event_time_utc: dt.datetime) -> ClassificationResult`, module constants `MEASUREMENT_WINDOW_MINUTES = 30`, `CLEAR_MOVE_THRESHOLD_PCT = 0.15`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_outcome_classifier.py`:

```python
"""
Tests for scoring/outcome_classifier.py — data_layer.dukascopy_feed.get_price_at
is mocked, no live network or real Dukascopy calls.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.probability_engine import Direction
from data_layer.dukascopy_feed import PricePoint
import scoring.outcome_classifier as outcome_classifier


def test_clear_upward_move_classifies_bullish():
    print("=== outcome_classifier: a clear upward move (>=0.15%) classifies BULLISH ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=2400.00), PricePoint(price=2404.00)]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction == Direction.BULLISH
        assert result.move_pct > 0.15
        assert "(auto)" in result.note
    print("PASS\n")


def test_clear_downward_move_classifies_bearish():
    print("=== outcome_classifier: a clear downward move classifies BEARISH ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=995.00)]):
        result = outcome_classifier.classify("US30", event_time)
        assert result.direction == Direction.BEARISH
        assert result.move_pct < -0.15
    print("PASS\n")


def test_move_exactly_at_threshold_classifies_not_ambiguous():
    print("=== outcome_classifier: a move exactly AT the 0.15% threshold still classifies, not ambiguous ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=1001.50)]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction == Direction.BULLISH
        assert abs(result.move_pct - 0.15) < 1e-9
    print("PASS\n")


def test_move_just_under_threshold_is_ambiguous():
    print("=== outcome_classifier: a move just under the threshold is ambiguous (no direction) ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=1001.49)]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction is None
        assert result.move_pct is not None
        assert "below" in result.note
    print("PASS\n")


def test_fetch_failure_is_ambiguous_with_no_move_pct():
    print("=== outcome_classifier: a fetch failure (either side) classifies as ambiguous with move_pct=None ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), None]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction is None
        assert result.move_pct is None
        assert "no data available" in result.note
    print("PASS\n")


def test_never_returns_neutral():
    print("=== outcome_classifier: never auto-classifies NEUTRAL — ambiguous is always direction=None, not Direction.NEUTRAL ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=1000.00)]):
        result = outcome_classifier.classify("XAUUSD", event_time)  # exactly 0% move
        assert result.direction is None, "a below-threshold move must be ambiguous (needs a human), never a confident NEUTRAL call"
        assert result.direction != Direction.NEUTRAL
    print("PASS\n")


if __name__ == "__main__":
    test_clear_upward_move_classifies_bullish()
    test_clear_downward_move_classifies_bearish()
    test_move_exactly_at_threshold_classifies_not_ambiguous()
    test_move_just_under_threshold_is_ambiguous()
    test_fetch_failure_is_ambiguous_with_no_move_pct()
    test_never_returns_neutral()
    print("All outcome_classifier tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_outcome_classifier.py`
Expected: `ModuleNotFoundError: No module named 'scoring.outcome_classifier'`

- [ ] **Step 3: Write the implementation**

Create `scoring/outcome_classifier.py`:

```python
"""
Classifies a backtest accumulator prediction's real outcome from Dukascopy
price data — the post-event price move over MEASUREMENT_WINDOW_MINUTES
becomes an auto-confirmable bullish/bearish call above
CLEAR_MOVE_THRESHOLD_PCT, or is left ambiguous (needs manual review) below
it. Never auto-classifies neutral: a small move means "needs a human to
look," not "confidently no reaction" — those are different claims, and
conflating them would silently under-report real small moves as neutral in
the accuracy report. See
docs/superpowers/specs/2026-08-10-dukascopy-outcome-confirmation-design.md.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from data_layer.dukascopy_feed import get_price_at
from scoring.probability_engine import Direction

MEASUREMENT_WINDOW_MINUTES = 30
CLEAR_MOVE_THRESHOLD_PCT = 0.15


@dataclass
class ClassificationResult:
    direction: Optional[Direction]   # bullish/bearish, or None if ambiguous
    move_pct: Optional[float]        # None only if a fetch failed outright
    note: str                        # human-readable; becomes actual_move_note verbatim on auto-confirm


def classify(instrument: str, event_time_utc: dt.datetime) -> ClassificationResult:
    before = get_price_at(instrument, event_time_utc)
    after = get_price_at(instrument, event_time_utc + dt.timedelta(minutes=MEASUREMENT_WINDOW_MINUTES))

    if before is None or after is None:
        return ClassificationResult(
            direction=None, move_pct=None,
            note="Dukascopy: no data available (market closed or feed gap)",
        )

    move_pct = (after.price - before.price) / before.price * 100

    if abs(move_pct) < CLEAR_MOVE_THRESHOLD_PCT:
        return ClassificationResult(
            direction=None, move_pct=move_pct,
            note=f"Dukascopy: {move_pct:+.2f}% in {MEASUREMENT_WINDOW_MINUTES}min, below {CLEAR_MOVE_THRESHOLD_PCT}% threshold",
        )

    direction = Direction.BULLISH if move_pct > 0 else Direction.BEARISH
    return ClassificationResult(
        direction=direction, move_pct=move_pct,
        note=f"Dukascopy: {move_pct:+.2f}% in {MEASUREMENT_WINDOW_MINUTES}min (auto)",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_outcome_classifier.py`
Expected: `All outcome_classifier tests passed.`

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
git add scoring/outcome_classifier.py tests/test_outcome_classifier.py
git commit -m "$(cat <<'EOF'
feat: add Dukascopy-based outcome classifier

classify(instrument, event_time_utc) compares Dukascopy prices 30
minutes apart; a move >=0.15% classifies bullish/bearish, anything
smaller or a fetch failure is ambiguous (direction=None) and left for
manual review — never auto-classified as neutral, since a small move
means "needs a human," not "confidently no reaction."

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `--auto` integration — `scripts/confirm_backtest_outcomes.py`

**Files:**
- Modify: `scripts/confirm_backtest_outcomes.py` (full file — currently 59 lines)
- Test: `tests/test_confirm_backtest_outcomes.py`

**Interfaces:**
- Consumes: `scoring.backtest_store.get_connection`, `get_predictions_awaiting_outcome`, `record_outcome`, `record_dismissal` (all existing), `scoring.outcome_classifier.classify(instrument, event_time_utc) -> ClassificationResult` (Task 2).
- Produces: `run_auto_confirm_phase(conn) -> dict` with keys `"auto_confirmed": int`, `"left_for_review": int`, `"suggestions": dict[tuple[str, str, str], ClassificationResult]` keyed by `(event_title, instrument, event_time_utc)` (the last element is the ISO string exactly as stored on `Prediction.event_time_utc`, not a `datetime`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_confirm_backtest_outcomes.py`:

```python
"""
Tests for scripts/confirm_backtest_outcomes.py's --auto phase
(run_auto_confirm_phase). classify() is mocked, no live Dukascopy calls.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import get_connection, record_prediction, get_all_confirmed_cases
from scoring.probability_engine import Direction
from scoring.outcome_classifier import ClassificationResult
import scripts.confirm_backtest_outcomes as confirm_cli


def test_auto_confirms_clear_classifications_and_leaves_ambiguous_ones():
    print("=== confirm_backtest_outcomes --auto: clear classifications get recorded, ambiguous ones are left for review ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        clear_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        ambiguous_time = dt.datetime(2026, 8, 2, 12, 30, tzinfo=dt.timezone.utc)
        record_prediction(conn, "NFP", "XAUUSD", clear_time, 0.7, "bullish", 0.4, 8, False)
        record_prediction(conn, "CPI", "US30", ambiguous_time, 0.6, "bearish", 0.3, 5, False)

        def fake_classify(instrument, event_time_utc):
            if instrument == "XAUUSD":
                return ClassificationResult(direction=Direction.BULLISH, move_pct=0.34, note="Dukascopy: +0.34% in 30min (auto)")
            return ClassificationResult(direction=None, move_pct=0.05, note="Dukascopy: +0.05% in 30min, below 0.15% threshold")

        with patch.object(confirm_cli, "classify", side_effect=fake_classify):
            summary = confirm_cli.run_auto_confirm_phase(conn)

        assert summary["auto_confirmed"] == 1
        assert summary["left_for_review"] == 1
        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1
        assert cases[0][1].actual_direction == "bullish"
        key = ("CPI", "US30", ambiguous_time.isoformat())
        assert key in summary["suggestions"]
        assert summary["suggestions"][key].note == "Dukascopy: +0.05% in 30min, below 0.15% threshold"
        conn.close()
    print("PASS\n")


def test_auto_confirm_on_empty_queue_does_nothing():
    print("=== confirm_backtest_outcomes --auto: an empty awaiting-outcome queue produces a 0/0 summary, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        summary = confirm_cli.run_auto_confirm_phase(conn)
        assert summary == {"auto_confirmed": 0, "left_for_review": 0, "suggestions": {}}
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_auto_confirms_clear_classifications_and_leaves_ambiguous_ones()
    test_auto_confirm_on_empty_queue_does_nothing()
    print("All confirm_backtest_outcomes tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_confirm_backtest_outcomes.py`
Expected: `AttributeError: module 'scripts.confirm_backtest_outcomes' has no attribute 'run_auto_confirm_phase'`

- [ ] **Step 3: Rewrite the implementation**

Replace the full contents of `scripts/confirm_backtest_outcomes.py`:

```python
"""
Manual outcome confirmation for the article-based backtest accumulator.
Lists every prediction whose event has passed with no recorded outcome
yet, and prompts for the real result — same research rigor as this
project's reconstructed backtest cases (tests/run_historical_backtest.py),
just applied to real predictions made blind (before the event actually
happened), not reconstructed after the fact.

--auto runs a Dukascopy-based auto-confirm pass first (see
scoring/outcome_classifier.py and
docs/superpowers/specs/2026-08-10-dukascopy-outcome-confirmation-design.md):
clear post-event price moves get recorded automatically, everything
ambiguous or fetch-failed is left exactly where it already was — the
existing awaiting-outcome queue, unchanged — with its computed
classification shown alongside the manual prompt as a suggestion.

Usage:
    python scripts/confirm_backtest_outcomes.py          # interactive
    python scripts/confirm_backtest_outcomes.py --list   # list only, no prompts
    python scripts/confirm_backtest_outcomes.py --auto   # auto-confirm phase, then interactive for what's left
    python scripts/confirm_backtest_outcomes.py --auto --list   # auto-confirm phase, then list what's left, no prompts
"""
import sys
import os
import datetime as dt
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import (
    get_connection, get_predictions_awaiting_outcome, record_outcome, record_dismissal,
)
from scoring.outcome_classifier import classify


def run_auto_confirm_phase(conn) -> dict:
    """
    Runs the Dukascopy auto-confirm pass over everything currently awaiting
    outcome. Returns {"auto_confirmed": int, "left_for_review": int,
    "suggestions": dict} — suggestions maps (event_title, instrument,
    event_time_utc) to the ClassificationResult computed for that row, so
    the interactive loop can show a leftover row's already-computed
    classification instead of re-fetching it.
    """
    awaiting = get_predictions_awaiting_outcome(conn)
    auto_confirmed = 0
    suggestions = {}
    for p in awaiting:
        event_time = dt.datetime.fromisoformat(p.event_time_utc)
        result = classify(p.instrument, event_time)
        if result.direction is not None:
            record_outcome(conn, p.event_title, p.instrument, event_time, result.direction.value, result.note)
            auto_confirmed += 1
            print(f"  [auto] {p.instrument} / {p.event_title}: {result.note}")
        else:
            suggestions[(p.event_title, p.instrument, p.event_time_utc)] = result
    left_for_review = len(awaiting) - auto_confirmed
    return {"auto_confirmed": auto_confirmed, "left_for_review": left_for_review, "suggestions": suggestions}


def main():
    list_only = "--list" in sys.argv
    auto = "--auto" in sys.argv

    with closing(get_connection()) as conn:
        suggestions = {}
        if auto:
            summary = run_auto_confirm_phase(conn)
            suggestions = summary["suggestions"]
            print(f"\nAuto-confirm: {summary['auto_confirmed']} confirmed, {summary['left_for_review']} left for review.\n")

        awaiting = get_predictions_awaiting_outcome(conn)

        if not awaiting:
            print("Nothing awaiting confirmation — every past prediction already has a recorded outcome.")
            return

        print(f"{len(awaiting)} prediction(s) awaiting outcome confirmation:\n")
        for p in awaiting:
            print(f"  {p.instrument} / {p.event_title} ({p.event_time_utc}) — "
                  f"predicted {p.direction.upper()} {p.probability:.0%}, "
                  f"{p.confidence:.0%} confidence, {p.article_count} articles")

        if list_only:
            return

        print("\nFor each, research the real outcome and enter it below.")
        print("Blank to skip for now (asked again next run). 'd' to dismiss for good — use this")
        print("when the event was rescheduled or canceled and a real outcome will never arrive;")
        print("otherwise a stale prediction sits in this queue forever.\n")
        for p in awaiting:
            print(f"--- {p.instrument} / {p.event_title} ({p.event_time_utc}) ---")
            print(f"    predicted: {p.direction.upper()} {p.probability:.0%}")
            suggestion = suggestions.get((p.event_title, p.instrument, p.event_time_utc))
            if suggestion is not None:
                print(f"    {suggestion.note}")
            direction = input("    actual direction (bullish/bearish/neutral, 'd' to dismiss, blank to skip): ").strip().lower()
            event_time = dt.datetime.fromisoformat(p.event_time_utc)
            if not direction:
                print("    skipped — will be asked again next run.\n")
                continue
            if direction == "d":
                reason = input("    dismissal reason (e.g. 'rescheduled', 'canceled', with source): ").strip()
                if not reason:
                    print("    dismissal needs a reason — skipped.\n")
                    continue
                record_dismissal(conn, p.event_title, p.instrument, event_time, reason)
                print("    dismissed — will not be asked again.\n")
                continue
            if direction not in {"bullish", "bearish", "neutral"}:
                print(f"    {direction!r} is not bullish/bearish/neutral/d — skipped.\n")
                continue
            note = input("    real outcome note (what actually happened, with source): ").strip()
            record_outcome(conn, p.event_title, p.instrument, event_time, direction, note)
            print("    recorded.\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_confirm_backtest_outcomes.py`
Expected: `All confirm_backtest_outcomes tests passed.`

- [ ] **Step 5: Run the full existing test suite to check for regressions**

Run: `python tests/test_backtest_store.py && python tests/test_backtest_accumulator.py && python tests/test_backtest_report.py`
Expected: all three print `All ... tests passed.` with no failures — this task only added a new flag and two new imports to `confirm_backtest_outcomes.py`, it must not have touched `backtest_store.py`'s or `backtest_accumulator.py`'s behavior.

- [ ] **Step 6: Commit**

```bash
cd "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
git add scripts/confirm_backtest_outcomes.py tests/test_confirm_backtest_outcomes.py
git commit -m "$(cat <<'EOF'
feat: add --auto flag to confirm_backtest_outcomes.py for Dukascopy auto-confirmation

run_auto_confirm_phase() runs the outcome classifier over everything
awaiting confirmation, auto-recording clear bullish/bearish moves via
the existing record_outcome() and leaving ambiguous/failed cases
exactly where they were. When --auto is combined with the existing
interactive mode, leftover rows show their already-computed
classification as a suggestion instead of a blank prompt. Bare
confirm_backtest_outcomes.py (no --auto) is unchanged - fully manual,
zero Dukascopy calls.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## After all tasks: merge to master

- [ ] **Merge and clean up**

```bash
cd "C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine"
git checkout master
git merge --no-ff <feature-branch-name> -m "Merge branch '<feature-branch-name>' into master

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git branch -d <feature-branch-name>
```

Run the full test suite one more time on `master` after the merge to confirm nothing regressed:

Run: `python tests/test_backtest_store.py && python tests/test_backtest_accumulator.py && python tests/test_backtest_report.py && python tests/test_dukascopy_feed.py && python tests/test_outcome_classifier.py && python tests/test_confirm_backtest_outcomes.py`
Expected: every file prints its own `All ... tests passed.` line, no failures.
