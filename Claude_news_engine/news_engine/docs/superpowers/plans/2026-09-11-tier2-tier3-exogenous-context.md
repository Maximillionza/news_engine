# Tier 2/3 Exogenous Market Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect a real, statistically anomalous daily move in DXY/UST_BOND/XAUUSD/US30 that no scheduled USD release explains, research its real-world cause, and downgrade the displayed confidence (never the direction, never the stored row) of any live CPI/PPI Tier 1 prediction on a day one is detected.

**Architecture:** A pure-function anomaly detector (`data_layer/discovery_detector.py`) computes a 20-day rolling baseline per series from real Dukascopy ticks and flags a move beyond 2 standard deviations with no matching calendar event. A daily scheduled-task step persists any real finding (`exogenous_shocks` table) after real WebSearch research attaches a cause. The live dashboard reads that table and layers a display-only confidence downgrade onto Tier 1's existing badge — the stored `Tier1Prediction` row is never touched.

**Tech Stack:** Python (dukascopy-python, sqlite3), vanilla JS/CSS (no new frontend dependency).

**Spec:** `docs/superpowers/specs/2026-09-11-tier2-tier3-exogenous-context-design.md`

## Global Constraints

- Confidence-only. Never write, infer, or display a `predicted_direction` change from this feature. Never rewrite, delete, or version a stored `tier1_predictions` row — the downgrade is computed fresh per request, display-only.
- Scoped to CPI/PPI `Tier1Prediction` rows only (the only event types with a live Tier 1 methodology) — no other event type is touched.
- `DETECTOR_SERIES` is exactly `["DXY", "UST_BOND", "XAUUSD", "US30"]` — 10Y and 30Y do not exist as separate Dukascopy instruments (verified: only one generic `INSTRUMENT_BND_CFD_USTBOND_TR_USD` exists), merged into one `UST_BOND` series per explicit user decision. Real dukascopy_python constants, verified 2026-09-11: `INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD` (DXY), `INSTRUMENT_BND_CFD_USTBOND_TR_USD` (UST_BOND), `INSTRUMENT_FX_METALS_XAU_USD` (XAUUSD, already mapped), `INSTRUMENT_IDX_AMERICA_E_D_J_IND` (US30, already mapped).
- No automated headline-to-taxonomy classification anywhere in this codebase — attaching a real-world cause is a human/LLM research step described in a scheduled-task prompt (not code in this repo), classified against `AdHoc_Category_Taxonomy`'s exact 8 category names: `"Treasury buyback size/schedule change"`, `"US sovereign credit-rating action"`, `"Government shutdown / funding lapse"`, `"Fed-independence shock"`, `"Fed Chair transition"`, `"Tariff/trade policy executive action"`, `"OPEC+ supply decision"`, `"Geopolitical war-driven oil supply shock"` — or `None` if no real fit exists.
- No retroactive re-scoring — this feature only ever affects what's displayed for TODAY's live data, never an already-graded historical case.
- Every "no anomaly found" result is the expected, common path, never logged as a warning or treated as a failure.
- A failed Dukascopy fetch for one series must never block any other series or crash whatever's calling it — fail open (`None`), same discipline `scoring/outcome_classifier.py` already uses.
- ANY unresolved anomaly across all 4 series downgrades EVERY tracked instrument's CPI/PPI Tier 1 rows for that day by exactly one confidence tier (`Certain`→`Likely`, `Likely`→`Guessing`, `Guessing`→`Guessing`) — never more than one tier regardless of how many series are anomalous the same day, and never scoped to just the anomalous series' own instrument.

---

### Task 1: `data_layer/discovery_detector.py` — instrument map + `compute_daily_move()`

**Files:**
- Create: `data_layer/discovery_detector.py`
- Test: `tests/test_discovery_detector.py`

**Interfaces:**
- Consumes: `data_layer.dukascopy_feed.get_price_at(instrument: str, when_utc: dt.datetime) -> Optional[PricePoint]` (existing, already used by `scoring/outcome_classifier.py`).
- Produces: `DETECTOR_SERIES: list[str]` (module-level constant, `["DXY", "UST_BOND", "XAUUSD", "US30"]`), `compute_daily_move(series: str, date: dt.date) -> Optional[float]` — later tasks call this by exact name.

This task owns mapping the 4 `DETECTOR_SERIES` names to real `dukascopy_python` instrument constants — a SEPARATE map from `data_layer/dukascopy_feed.py`'s own `_INSTRUMENT_MAP` (that module's map is keyed by this project's tracked-symbol names `XAUUSD`/`US30` only, used by the outcome-confirmation pipeline; this feature needs DXY/UST_BOND too, which aren't tracked symbols in that sense). Reuses `dukascopy_feed.get_price_at()` directly rather than duplicating its fetch logic — this task only needs a NEW instrument map, not a new fetch mechanism.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_discovery_detector.py
"""
Tests for data_layer/discovery_detector.py.
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer import discovery_detector


def test_detector_series_is_exactly_four_series():
    print("=== discovery_detector: DETECTOR_SERIES is exactly the 4 verified series, in order ===")
    assert discovery_detector.DETECTOR_SERIES == ["DXY", "UST_BOND", "XAUUSD", "US30"]
    print("PASS\n")


def test_compute_daily_move_unknown_series_raises_value_error():
    print("=== discovery_detector: compute_daily_move raises ValueError for a series with no instrument mapping (caller bug, not a data-availability issue) ===")
    try:
        discovery_detector.compute_daily_move("NOT_A_REAL_SERIES", dt.date(2026, 9, 10))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "NOT_A_REAL_SERIES" in str(exc)
    print("PASS\n")


def test_compute_daily_move_returns_a_real_percentage_for_a_real_past_date():
    print("=== discovery_detector: compute_daily_move returns a real, plausible daily move for XAUUSD on a real past trading day ===")
    # 2026-09-10 is a real, already-resolved PPI release day used
    # elsewhere in this project's own real backtest cases (Causation-
    # Matrix Option A) -- a real trading day, not a weekend/holiday.
    move = discovery_detector.compute_daily_move("XAUUSD", dt.date(2026, 9, 10))
    assert move is not None
    assert -20.0 < move < 20.0, f"expected a plausible single-day %% move, got {move}"
    print("PASS\n")


if __name__ == "__main__":
    test_detector_series_is_exactly_four_series()
    test_compute_daily_move_unknown_series_raises_value_error()
    test_compute_daily_move_returns_a_real_percentage_for_a_real_past_date()
    print("All discovery_detector tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_discovery_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_layer.discovery_detector'`

- [ ] **Step 3: Write minimal implementation**

```python
# data_layer/discovery_detector.py
"""
Discovery_Detector_Spec implementation (docs/News_Engine_Causation_Matrix_v2.xlsx):
a statistical anomaly detector over 4 market-wide series, flagging a
real, unexplained daily move so a Tier 1 CPI/PPI prediction's DISPLAYED
confidence (never its stored value, never its direction) can be
downgraded on the live dashboard. See
docs/superpowers/specs/2026-09-11-tier2-tier3-exogenous-context-design.md
for the full design and rationale.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import dukascopy_python
from dukascopy_python.instruments import (
    INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD,
    INSTRUMENT_BND_CFD_USTBOND_TR_USD,
    INSTRUMENT_FX_METALS_XAU_USD,
    INSTRUMENT_IDX_AMERICA_E_D_J_IND,
)
from data_layer.dukascopy_feed import get_price_at

# Verified 2026-09-11 against dukascopy_python's real instrument catalog
# (1380 entries): 10Y and 30Y Treasury yields do NOT exist as separate
# Dukascopy instruments -- only one generic US T-Bond CFD does. Per
# explicit user decision, merged into one UST_BOND series rather than
# forcing an unsupported 10Y/30Y split. This map is intentionally
# SEPARATE from data_layer/dukascopy_feed.py's own _INSTRUMENT_MAP (that
# one is keyed by this project's tracked-symbol names for the outcome-
# confirmation pipeline; DXY/UST_BOND are not tracked symbols in that sense).
DETECTOR_SERIES = ["DXY", "UST_BOND", "XAUUSD", "US30"]

_DETECTOR_INSTRUMENT_MAP = {
    "DXY": INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD,
    "UST_BOND": INSTRUMENT_BND_CFD_USTBOND_TR_USD,
    "XAUUSD": INSTRUMENT_FX_METALS_XAU_USD,
    "US30": INSTRUMENT_IDX_AMERICA_E_D_J_IND,
}


def compute_daily_move(series: str, date: dt.date) -> Optional[float]:
    """
    Real percentage move from session open to session close for `date`,
    using the same get_price_at() Dukascopy tick fetch
    scoring/outcome_classifier.py already relies on -- no new fetch
    mechanism, just a new instrument map. Session open/close are UTC
    00:00 and 23:59:59 for `date` -- a coarse but real and consistent
    definition, matching this project's existing "before/after" tick
    convention rather than inventing a market-hours-aware session
    boundary this codebase doesn't otherwise track.

    Returns None -- never fabricated -- if either tick fetch fails for
    any reason (market closed, feed gap, bad tick). Raises ValueError
    for a `series` with no instrument mapping -- that's a caller bug,
    not a data-availability issue, same distinction get_price_at()
    itself already draws for an unmapped tracked-symbol instrument.
    """
    if series not in _DETECTOR_INSTRUMENT_MAP:
        raise ValueError(
            f"series={series!r} has no Dukascopy instrument mapping — "
            f"known series: {DETECTOR_SERIES}"
        )
    instrument = _DETECTOR_INSTRUMENT_MAP[series]
    session_start = dt.datetime.combine(date, dt.time(0, 0), tzinfo=dt.timezone.utc)
    session_end = dt.datetime.combine(date, dt.time(23, 59, 59), tzinfo=dt.timezone.utc)

    open_price = _fetch_tick(instrument, session_start)
    close_price = _fetch_tick(instrument, session_end)
    if open_price is None or close_price is None:
        return None
    return (close_price - open_price) / open_price * 100


def _fetch_tick(instrument, when_utc: dt.datetime) -> Optional[float]:
    """
    Thin wrapper around dukascopy_python.fetch(), same BID-consistent,
    first-tick-at-or-after convention data_layer/dukascopy_feed.py's
    get_price_at() uses -- duplicated here rather than imported because
    that function's instrument map is keyed by different names (this
    project's tracked symbols, not DETECTOR_SERIES); the fetch mechanics
    themselves are copied verbatim, not reinvented.
    """
    try:
        df = dukascopy_python.fetch(
            instrument, dukascopy_python.INTERVAL_TICK, dukascopy_python.OFFER_SIDE_BID,
            when_utc, when_utc + dt.timedelta(minutes=5),
        )
        if df is None or df.empty:
            return None
        return float(df.iloc[0]["bidPrice"])
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[discovery_detector] WARNING: fetch failed for {when_utc.isoformat()}: {exc}")
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_discovery_detector.py -v`
Expected: PASS (3 tests) — the third test makes a REAL Dukascopy call; if it fails on a transient network/feed issue rather than a real code bug, re-run once before treating it as a real failure.

- [ ] **Step 5: Commit**

```bash
git add data_layer/discovery_detector.py tests/test_discovery_detector.py
git commit -m "feat: add discovery_detector instrument map + compute_daily_move()"
```

---

### Task 2: `rolling_baseline()` + `AnomalyResult`

**Files:**
- Modify: `data_layer/discovery_detector.py`
- Test: `tests/test_discovery_detector.py`

**Interfaces:**
- Consumes: `compute_daily_move(series, date)` (Task 1).
- Produces: `AnomalyResult` dataclass (`series: str`, `move_pct: float`, `baseline_mean: float`, `baseline_stdev: float`, `stdev_move: float`, `date: dt.date`), `rolling_baseline(series: str, as_of_date: dt.date, window_days: int = 20) -> Optional[tuple[float, float]]` — later tasks call this by exact name; return shape is `(mean, stdev)`.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_discovery_detector.py, before the `if __name__` block

from unittest.mock import patch


def test_rolling_baseline_computes_mean_and_stdev_from_prior_days_only():
    print("=== discovery_detector: rolling_baseline computes real mean/stdev from the window_days BEFORE as_of_date, never including as_of_date itself ===")
    as_of = dt.date(2026, 9, 10)
    # 3 fabricated daily moves for a 3-day window -- fabricated ONLY
    # here, to test pure math in isolation; compute_daily_move itself
    # (Task 1) is never faked on the live path.
    fake_moves = {
        dt.date(2026, 9, 7): 1.0,
        dt.date(2026, 9, 8): 2.0,
        dt.date(2026, 9, 9): 3.0,
    }

    def fake_compute(series, date):
        return fake_moves.get(date)

    with patch.object(discovery_detector, "compute_daily_move", side_effect=fake_compute):
        result = discovery_detector.rolling_baseline("XAUUSD", as_of, window_days=3)
    assert result is not None
    mean, stdev = result
    assert abs(mean - 2.0) < 1e-9
    assert stdev > 0
    print("PASS\n")


def test_rolling_baseline_returns_none_with_fewer_than_window_days_of_real_data():
    print("=== discovery_detector: rolling_baseline returns None (never a fabricated partial baseline) when fewer than window_days real moves are available ===")
    as_of = dt.date(2026, 9, 10)

    def fake_compute(series, date):
        return 1.0 if date == dt.date(2026, 9, 9) else None  # only 1 of 3 days has real data

    with patch.object(discovery_detector, "compute_daily_move", side_effect=fake_compute):
        result = discovery_detector.rolling_baseline("XAUUSD", as_of, window_days=3)
    assert result is None
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_discovery_detector.py -v -k rolling_baseline`
Expected: FAIL with `AttributeError: module 'data_layer.discovery_detector' has no attribute 'rolling_baseline'`

- [ ] **Step 3: Write minimal implementation**

```python
# Append to data_layer/discovery_detector.py

import statistics


@dataclass
class AnomalyResult:
    series: str
    move_pct: float
    baseline_mean: float
    baseline_stdev: float
    stdev_move: float  # (move_pct - baseline_mean) / baseline_stdev
    date: dt.date


def rolling_baseline(
    series: str, as_of_date: dt.date, window_days: int = 20,
) -> Optional[tuple[float, float]]:
    """
    Mean and stdev of the `window_days` daily moves immediately BEFORE
    as_of_date -- as_of_date itself is never included, same no-lookahead
    discipline data_layer/event_context.py's build_event_news_bundle()
    already enforces elsewhere in this codebase (a prediction must never
    see data from after the instant it's supposed to represent).

    Returns None -- never a fabricated partial baseline -- if fewer than
    `window_days` real moves are available in that lookback (a market
    holiday, a data gap, or simply too early in this feature's own life
    for 20 real trading days to exist yet).
    """
    moves = []
    check_date = as_of_date - dt.timedelta(days=1)
    days_checked = 0
    # Walks back one calendar day at a time (skipping weekends implicitly
    # via compute_daily_move returning None for a non-trading day) until
    # window_days REAL moves are collected or a reasonable calendar-day
    # budget is exhausted -- 2x window_days covers weekends without
    # risking an unbounded loop on a genuinely broken feed.
    while len(moves) < window_days and days_checked < window_days * 2:
        move = compute_daily_move(series, check_date)
        if move is not None:
            moves.append(move)
        check_date -= dt.timedelta(days=1)
        days_checked += 1
    if len(moves) < window_days:
        return None
    return statistics.mean(moves), statistics.stdev(moves)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_discovery_detector.py -v -k rolling_baseline`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add data_layer/discovery_detector.py tests/test_discovery_detector.py
git commit -m "feat: add discovery_detector rolling_baseline() + AnomalyResult"
```

---

### Task 3: `detect_anomaly()` — threshold + calendar gate

**Files:**
- Modify: `data_layer/discovery_detector.py`
- Test: `tests/test_discovery_detector.py`

**Interfaces:**
- Consumes: `rolling_baseline()` (Task 2), `compute_daily_move()` (Task 1), `data_layer.calendar_feed.EconomicEvent` (existing — fields `title`, `country`, `impact`, `event_time_utc`), `data_layer.calendar_feed.IMPACT_RANK` (existing).
- Produces: `detect_anomaly(series: str, date: dt.date, calendar_events: list[EconomicEvent]) -> Optional[AnomalyResult]` — Task 4 (the scheduled-task step) calls this by exact name, passing in that date's persisted calendar events (fetched from `webapp.store.get_calendar_snapshot()`, filtered to `country == "USD"`).

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_discovery_detector.py, before the `if __name__` block

from data_layer.calendar_feed import EconomicEvent, UTC_TZ


def _usd_event(title, impact, event_time_utc):
    return EconomicEvent(title=title, country="USD", impact=impact, event_time_utc=event_time_utc)


def test_detect_anomaly_flags_a_real_stdev_breach_with_no_calendar_event():
    print("=== discovery_detector: detect_anomaly flags a real >2 stdev move with no matching USD Medium+ calendar event ===")
    as_of = dt.date(2026, 9, 10)
    with patch.object(discovery_detector, "compute_daily_move", return_value=10.0), \
         patch.object(discovery_detector, "rolling_baseline", return_value=(0.0, 1.0)):
        result = discovery_detector.detect_anomaly("XAUUSD", as_of, calendar_events=[])
    assert result is not None
    assert result.series == "XAUUSD"
    assert result.stdev_move == 10.0
    print("PASS\n")


def test_detect_anomaly_none_when_move_within_threshold():
    print("=== discovery_detector: detect_anomaly returns None when the move is within the 2-stdev threshold, regardless of calendar ===")
    as_of = dt.date(2026, 9, 10)
    with patch.object(discovery_detector, "compute_daily_move", return_value=0.5), \
         patch.object(discovery_detector, "rolling_baseline", return_value=(0.0, 1.0)):
        result = discovery_detector.detect_anomaly("XAUUSD", as_of, calendar_events=[])
    assert result is None
    print("PASS\n")


def test_detect_anomaly_none_when_a_real_calendar_event_already_explains_it():
    print("=== discovery_detector: detect_anomaly returns None for a real >2 stdev move that a USD Medium+ calendar event on the same day already explains ===")
    as_of = dt.date(2026, 9, 10)
    ppi_event = _usd_event("PPI m/m", "High", dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ))
    with patch.object(discovery_detector, "compute_daily_move", return_value=10.0), \
         patch.object(discovery_detector, "rolling_baseline", return_value=(0.0, 1.0)):
        result = discovery_detector.detect_anomaly("XAUUSD", as_of, calendar_events=[ppi_event])
    assert result is None
    print("PASS\n")


def test_detect_anomaly_low_impact_calendar_event_does_not_explain_a_real_move():
    print("=== discovery_detector: a Low-impact calendar event does NOT gate a real anomaly -- only Medium+ counts, same IMPACT_RANK threshold this codebase already uses elsewhere ===")
    as_of = dt.date(2026, 9, 10)
    low_impact_event = _usd_event("Some Minor Release", "Low", dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ))
    with patch.object(discovery_detector, "compute_daily_move", return_value=10.0), \
         patch.object(discovery_detector, "rolling_baseline", return_value=(0.0, 1.0)):
        result = discovery_detector.detect_anomaly("XAUUSD", as_of, calendar_events=[low_impact_event])
    assert result is not None
    print("PASS\n")


def test_detect_anomaly_none_when_daily_move_unavailable():
    print("=== discovery_detector: detect_anomaly returns None (never fabricated) when compute_daily_move itself has no real data ===")
    as_of = dt.date(2026, 9, 10)
    with patch.object(discovery_detector, "compute_daily_move", return_value=None), \
         patch.object(discovery_detector, "rolling_baseline", return_value=(0.0, 1.0)):
        result = discovery_detector.detect_anomaly("XAUUSD", as_of, calendar_events=[])
    assert result is None
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_discovery_detector.py -v -k detect_anomaly`
Expected: FAIL with `AttributeError: module 'data_layer.discovery_detector' has no attribute 'detect_anomaly'`

- [ ] **Step 3: Write minimal implementation**

```python
# Append to data_layer/discovery_detector.py

from data_layer.calendar_feed import EconomicEvent, IMPACT_RANK

ANOMALY_STDEV_THRESHOLD = 2.0  # Discovery_Detector_Spec's own number, verbatim


def detect_anomaly(
    series: str, date: dt.date, calendar_events: list[EconomicEvent],
) -> Optional[AnomalyResult]:
    """
    None -- the overwhelmingly common, expected result -- if: today's
    move or the rolling baseline itself has no real data (never
    guessed), the move is within ANOMALY_STDEV_THRESHOLD standard
    deviations of the baseline, OR a real USD Medium+ impact calendar
    event already covers `date` (an expected move from a known release
    is not an anomaly -- same "the calendar already explains this" gate
    Discovery_Detector_Spec itself specifies). `calendar_events` is the
    caller's responsibility to fetch and filter to `date` and
    country == "USD" -- this function does no fetching of its own, kept
    a pure function of its inputs like every other function in this
    module.
    """
    move = compute_daily_move(series, date)
    if move is None:
        return None
    baseline = rolling_baseline(series, date)
    if baseline is None:
        return None
    mean, stdev = baseline
    if stdev == 0:
        return None  # a real but degenerate (zero-variance) baseline can't produce a meaningful stdev_move
    stdev_move = (move - mean) / stdev
    if abs(stdev_move) < ANOMALY_STDEV_THRESHOLD:
        return None

    has_explaining_event = any(
        e.country == "USD" and IMPACT_RANK.get(e.impact, 0) >= IMPACT_RANK["Medium"]
        and e.event_time_utc.date() == date
        for e in calendar_events
    )
    if has_explaining_event:
        return None

    return AnomalyResult(
        series=series, move_pct=move, baseline_mean=mean, baseline_stdev=stdev,
        stdev_move=stdev_move, date=date,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_discovery_detector.py -v -k detect_anomaly`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add data_layer/discovery_detector.py tests/test_discovery_detector.py
git commit -m "feat: add discovery_detector detect_anomaly() with calendar gate"
```

---

### Task 4: `scoring/backtest_store.py` — `exogenous_shocks` table

**Files:**
- Modify: `scoring/backtest_store.py`
- Test: `tests/test_backtest_store.py`

**Interfaces:**
- Consumes: none new (uses this module's existing `get_connection()`, `_schema_ready_paths` caching pattern).
- Produces: `ExogenousShockRow` dataclass (`id`, `series`, `shock_date`, `move_pct`, `stdev_move`, `taxonomy_category`, `headline_cause`, `source`, `logged_at_utc`), `record_exogenous_shock(conn, series, shock_date, move_pct, stdev_move, taxonomy_category=None, headline_cause=None, source=None, logged_at_utc=None) -> int`, `get_exogenous_shock_for_date(conn, series, shock_date) -> Optional[ExogenousShockRow]` — Task 5 calls both by exact name.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_backtest_store.py, before the `if __name__` block

def test_record_and_get_exogenous_shock_round_trip():
    print("=== backtest_store: record_exogenous_shock + get_exogenous_shock_for_date round-trip ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        shock_date = dt.date(2026, 9, 10)
        record_exogenous_shock(
            conn, "XAUUSD", shock_date, move_pct=8.5, stdev_move=3.2,
            taxonomy_category="Geopolitical war-driven oil supply shock",
            headline_cause="Real headline describing the event",
            source="Reuters, 2026-09-10",
        )
        row = get_exogenous_shock_for_date(conn, "XAUUSD", shock_date)
        assert row is not None
        assert row.move_pct == 8.5
        assert row.taxonomy_category == "Geopolitical war-driven oil supply shock"
        conn.close()
    print("PASS\n")


def test_get_exogenous_shock_returns_none_when_never_logged():
    print("=== backtest_store: get_exogenous_shock_for_date returns None (never fabricated) when nothing was ever recorded ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        assert get_exogenous_shock_for_date(conn, "XAUUSD", dt.date(2026, 9, 10)) is None
        conn.close()
    print("PASS\n")


def test_record_exogenous_shock_rejects_invalid_taxonomy_category():
    print("=== backtest_store: record_exogenous_shock rejects a taxonomy_category that isn't one of AdHoc_Category_Taxonomy's 8 real categories ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        try:
            record_exogenous_shock(
                conn, "XAUUSD", dt.date(2026, 9, 10), move_pct=8.5, stdev_move=3.2,
                taxonomy_category="Not A Real Category",
            )
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "Not A Real Category" in str(exc)
        conn.close()
    print("PASS\n")


def test_record_exogenous_shock_allows_none_taxonomy_category():
    print("=== backtest_store: record_exogenous_shock allows taxonomy_category=None -- a real anomaly with no fitting category is a real, honest outcome, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        record_exogenous_shock(conn, "XAUUSD", dt.date(2026, 9, 10), move_pct=8.5, stdev_move=3.2)
        row = get_exogenous_shock_for_date(conn, "XAUUSD", dt.date(2026, 9, 10))
        assert row.taxonomy_category is None
        conn.close()
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_backtest_store.py -v -k exogenous_shock`
Expected: FAIL with `ImportError: cannot import name 'record_exogenous_shock'`

- [ ] **Step 3: Write minimal implementation**

```python
# In scoring/backtest_store.py's _SCHEMA string, add after the tier1_comparisons table:
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
```

```python
# Add near the top of scoring/backtest_store.py, alongside the module's
# other tag-validation constants (e.g. _VALID_TIER1_CONFIDENCE):
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
```

Also add a migration function (mirroring `_migrate_add_confidence_multipliers_column()`'s pattern) and wire it into both `get_connection()` call sites — even though `exogenous_shocks` is a brand-new table (`CREATE TABLE IF NOT EXISTS` in `_SCHEMA` already handles a fresh DB), the existing project convention runs every table's own migration function unconditionally for consistency and forward-compatibility with a future column addition. Since this is a NEW table with no missing-column scenario yet, skip a dedicated migration function for this task — `_SCHEMA`'s own `CREATE TABLE IF NOT EXISTS` is sufficient (there's no pre-existing `exogenous_shocks` table anywhere that could be missing this table's own columns).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_backtest_store.py -v -k exogenous_shock`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full backtest_store test file to confirm no regressions**

Run: `python -m pytest tests/test_backtest_store.py -v`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add scoring/backtest_store.py tests/test_backtest_store.py
git commit -m "feat: add exogenous_shocks table, record/get functions"
```

---

### Task 5: `webapp/predictions_service.py` — `tier1_confidence_downgrade` field

**Files:**
- Modify: `webapp/predictions_service.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `scoring.backtest_store.get_exogenous_shock_for_date(conn, series, shock_date)` (Task 4), `data_layer.discovery_detector.DETECTOR_SERIES` (Task 1).
- Produces: new `"tier1_confidence_downgrade"` key on every event dict in `build_predictions_payload()`'s output — `None`, or `{"original_confidence": str, "displayed_confidence": str, "reason": Optional[str], "series": str}`.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_webapp_app.py, before the `if __name__` block

def test_predictions_downgrades_tier1_confidence_when_a_real_shock_is_logged_today():
    print("=== app: /api/predictions downgrades a Tier 1 row's DISPLAYED confidence (never the stored row) when an exogenous_shocks row exists for today, across ANY detector series ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            ppi_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)
            _seed_calendar(db_path, [
                EconomicEvent(title="PPI m/m", country="USD", impact="High",
                               event_time_utc=ppi_time, forecast="0.2%", previous="0.0%", actual=None),
            ])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time, 0.60, "bearish", 0.5, 100, False,
            )
            backtest_store.record_tier1_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time,
                value="Some call", confidence="Certain", source="BLS/ISM", predicted_direction="bearish",
            )
            # A real shock logged on a DIFFERENT series (DXY) than this
            # instrument (XAUUSD) -- per the spec's own rule, ANY
            # unresolved shock across all 4 series downgrades EVERY
            # tracked instrument's Tier 1 rows, not just its own series'.
            backtest_store.record_exogenous_shock(
                bconn, "DXY", ppi_time.date(), move_pct=5.0, stdev_move=3.0,
                headline_cause="Real researched cause", source="Reuters",
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = {e["event_title"]: e for e in resp.get_json()["predictions"][0]["events"]}
            downgrade = events["PPI m/m"]["tier1_confidence_downgrade"]
            assert downgrade is not None
            assert downgrade["original_confidence"] == "Certain"
            assert downgrade["displayed_confidence"] == "Likely"
            assert downgrade["series"] == "DXY"
            # The stored row itself is untouched.
            stored = backtest_store.get_latest_tier1_prediction_for_occurrence(bconn := backtest_store.get_connection(backtest_db_path), "PPI m/m", "XAUUSD", ppi_time)
            assert stored.confidence == "Certain"
            bconn.close()
    print("PASS\n")


def test_predictions_no_tier1_confidence_downgrade_without_a_real_shock():
    print("=== app: /api/predictions: tier1_confidence_downgrade is null when no exogenous_shocks row exists for today ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            ppi_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)
            _seed_calendar(db_path, [
                EconomicEvent(title="PPI m/m", country="USD", impact="High",
                               event_time_utc=ppi_time, forecast="0.2%", previous="0.0%", actual=None),
            ])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time, 0.60, "bearish", 0.5, 100, False,
            )
            backtest_store.record_tier1_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time,
                value="Some call", confidence="Certain", source="BLS/ISM", predicted_direction="bearish",
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = {e["event_title"]: e for e in resp.get_json()["predictions"][0]["events"]}
            assert events["PPI m/m"]["tier1_confidence_downgrade"] is None
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_webapp_app.py -v -k tier1_confidence_downgrade`
Expected: FAIL with `KeyError: 'tier1_confidence_downgrade'`

- [ ] **Step 3: Write minimal implementation**

```python
# In webapp/predictions_service.py, add to the imports:
import datetime as dt  # already imported — confirm present, do not duplicate
from data_layer.discovery_detector import DETECTOR_SERIES
from scoring.backtest_store import get_exogenous_shock_for_date

# Add this pure helper function near the other small helpers
# (_print_prediction_dict, _tier1_prediction_dict):

_CONFIDENCE_DOWNGRADE_ORDER = ["Certain", "Likely", "Guessing"]


def _downgrade_one_tier(confidence: str) -> str:
    """Certain->Likely, Likely->Guessing, Guessing->Guessing (floor). Display-only — never mutates a stored Tier1PredictionRow."""
    if confidence not in _CONFIDENCE_DOWNGRADE_ORDER:
        return confidence  # unrecognized tag — leave untouched rather than guess
    idx = _CONFIDENCE_DOWNGRADE_ORDER.index(confidence)
    return _CONFIDENCE_DOWNGRADE_ORDER[min(idx + 1, len(_CONFIDENCE_DOWNGRADE_ORDER) - 1)]


def _get_todays_exogenous_shock(backtest_conn):
    """
    First unresolved shock found today across DETECTOR_SERIES, or None.
    Fail-open (same pattern as build_predictions_payload()'s existing
    get_latest_tier1_predictions_bulk() try/except) -- a broken lookup
    must never take down /api/predictions. "First found" is sufficient:
    per the spec, multiple same-day shocks still only downgrade ONE
    tier, so which specific shock's series/reason gets shown when
    several exist the same day is not a load-bearing distinction.
    """
    today = dt.datetime.now(dt.timezone.utc).date()
    try:
        for series in DETECTOR_SERIES:
            shock = get_exogenous_shock_for_date(backtest_conn, series, today)
            if shock is not None:
                return shock
    except Exception:
        logger.warning("exogenous shock lookup failed for this cycle", exc_info=True)
    return None
```

In `build_predictions_payload()`, call `_get_todays_exogenous_shock(backtest_conn)` once near the top (alongside the existing `tier1_by_occurrence` bulk fetch), then in the per-event loop right after `tier1_prediction` is computed:

```python
            tier1_confidence_downgrade = None
            if tier1_prediction is not None and todays_shock is not None:
                tier1_confidence_downgrade = {
                    "original_confidence": tier1_prediction["confidence"],
                    "displayed_confidence": _downgrade_one_tier(tier1_prediction["confidence"]),
                    "reason": todays_shock.headline_cause,
                    "series": todays_shock.series,
                }
```

and add `"tier1_confidence_downgrade": tier1_confidence_downgrade,` to the event dict literal, right after the existing `"tier1_sentiment_conflict": None,` line (also updating that line's own placeholder-comment pattern is not needed — this new field is computed inline in the same per-event loop, not in the later reconciliation-dependent pass).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_webapp_app.py -v -k tier1_confidence_downgrade`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full webapp test file to confirm no regressions**

Run: `python -m pytest tests/test_webapp_app.py -v`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add webapp/predictions_service.py tests/test_webapp_app.py
git commit -m "feat: surface tier1_confidence_downgrade in /api/predictions"
```

---

### Task 6: Frontend — confidence-downgrade badge

**Files:**
- Modify: `webapp/static/app.js`
- Modify: `webapp/static/style.css`

**Interfaces:**
- Consumes: `next.tier1_confidence_downgrade` (Task 5's new field, present on every event dict from `/api/predictions`).
- Produces: no new exported JS function other callers need — this is a leaf rendering addition, same shape as `tier1SentimentConflictHtml()`.

- [ ] **Step 1: Add the render function, right after `tier1SentimentConflictHtml()` in `webapp/static/app.js`**

```javascript
  // tier1_confidence_downgrade (Tier 2/3 exogenous-context spec,
  // 2026-09-11): a real, detected market-wide anomaly (DXY/UST_BOND/
  // XAUUSD/US30) with no calendar event explaining it downgrades this
  // Tier 1 row's DISPLAYED confidence one tier — never its direction,
  // never the stored value (original_confidence is shown alongside so
  // nothing is silently hidden).
  function tier1ConfidenceDowngradeHtml(downgrade) {
    if (!downgrade) return '';
    const reasonText = downgrade.reason ? `: ${escapeHtml(downgrade.reason)}` : '';
    return `<div class="tier1-confidence-downgrade">
      ⚠ Confidence downgraded to <b>${escapeHtml(downgrade.displayed_confidence)}</b>
      (was ${escapeHtml(downgrade.original_confidence)}) — unexplained ${escapeHtml(downgrade.series)} move${reasonText}
    </div>`;
  }
```

- [ ] **Step 2: Wire it into `tier1PredictionLine`'s existing concatenation**

Find the existing line:

```javascript
  const tier1PredictionLine = tier1PredictionHtml(next.tier1_prediction, symbol)
    + tier1SentimentConflictHtml(next.tier1_sentiment_conflict);
```

Replace with:

```javascript
  const tier1PredictionLine = tier1PredictionHtml(next.tier1_prediction, symbol)
    + tier1SentimentConflictHtml(next.tier1_sentiment_conflict)
    + tier1ConfidenceDowngradeHtml(next.tier1_confidence_downgrade);
```

- [ ] **Step 3: Add the CSS, right after `.tier1-sentiment-conflict` in `webapp/static/style.css`**

```css
/* Same warning palette as .tier1-sentiment-conflict — same visual
   language for "something real needs your attention here," different
   underlying question (an unexplained market-wide move, not a
   cross-system disagreement). */
.tier1-confidence-downgrade { margin-top: 6px; padding: 6px 10px; border-radius: 8px; font-size: 12px; text-align: center; background: rgba(255, 152, 0, 0.12); border: 1px solid rgba(255, 152, 0, 0.4); color: #ef6c00; }
```

- [ ] **Step 4: Verify syntax**

Run: `node --check webapp/static/app.js`
Expected: no output (success)

- [ ] **Step 5: Live-verify in the browser**

Restart the running dashboard process (find it via its PID, same process this project's own sessions have repeatedly needed to restart after a code change — see any prior session's PID-restart steps for the exact commands), then in the running dashboard:
1. Manually call `record_exogenous_shock()` for today's date on any `DETECTOR_SERIES` value, for an occurrence that also has a real logged Tier 1 prediction.
2. Reload the dashboard and confirm the new badge renders under the Tier 1 line, showing the downgraded confidence and the real reason text.
3. Confirm no console errors.

- [ ] **Step 6: Commit**

```bash
git add webapp/static/app.js webapp/static/style.css
git commit -m "feat: render Tier 1 confidence-downgrade badge on the dashboard"
```

---

### Task 7: Extend the scheduled research task (orchestrator-only, not a subagent task)

**This task is NOT dispatched to an implementer subagent.** It requires calling `update_scheduled_task` (an MCP tool available only to the controlling session, not to a code-writing subagent) to modify `tier1-multi-event-autoresearch` — the scheduled task itself lives in this app's own scheduler, not in this repository, and no subagent has the tool access to change it.

**Files:** none in this repository — this task's only artifact is the updated scheduled-task prompt, applied directly by the controller.

- [ ] **Step 1:** After Tasks 1–6 are merged and live-verified, the controller (not a subagent) calls `update_scheduled_task` on `tier1-multi-event-autoresearch`, extending its existing daily prompt with a new step: for each of `data_layer.discovery_detector.DETECTOR_SERIES`, call `detect_anomaly()` for yesterday's date (passing in that date's real persisted USD calendar events from `webapp.store.get_calendar_snapshot()`), and for any real result with no existing `get_exogenous_shock_for_date()` row, do real WebSearch research for a same-day headline cause, classify it against `AdHoc_Category_Taxonomy`'s 8 real categories (or leave `taxonomy_category=None` if no real fit exists — never forced), and call `record_exogenous_shock()`. Same "never fabricate a citation, never force a categorical fit" hard constraints the existing Tier 1 research prompt already states, extended to this new step.
- [ ] **Step 2:** Report the updated prompt's exact text back to the user for their own record (the scheduled task's prompt file is local to their machine, not tracked in this repo).

---

## Self-Review Notes (writing-plans skill's own checklist, run before handoff)

**Spec coverage:** All 4 architecture sections (detector module, persistence, scheduled trigger, live display) have a task. The spec's "Open technical risk" section is resolved directly in the Global Constraints (verified 2026-09-11, DXY/UST_BOND real, 10Y/30Y merged per user decision) rather than left as a Task 1 spike — the actual verification was already run during plan-writing, so re-dispatching it as a subagent spike would be pure duplicate work; Task 1 instead asserts the verified constants directly and tests that they resolve to real, working Dukascopy fetches.

**Placeholder scan:** No TBD/TODO. Every code step is complete, runnable code, not a description of code.

**Type consistency:** `AnomalyResult` (Task 2) and `ExogenousShockRow` (Task 4) field names checked against each other and against Task 5's usage (`shock.headline_cause`, `shock.series`) — consistent throughout. `DETECTOR_SERIES` (Task 1) is imported and iterated identically in Task 5's `_get_todays_exogenous_shock()`.
