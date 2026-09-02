# Fundamental Signals Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three independent, fail-open confidence-modifying signals to the article-based scoring pipeline — COT positioning crowding, an equity risk-sentiment cross-check for US30, and an oil single-day shock flag — none of which ever alter direction or probability, only `confidence`.

**Architecture:** Two of the three (equity leg, oil shock) extend the existing `data_layer/macro_backdrop.py` module and its `MacroBackdropRead` dataclass with new fields, fetched from FRED alongside the existing dollar-index/real-yield/oil reads. The third (COT) is a new, independent module (`data_layer/cot_positioning.py`) fetching CFTC's free public COT API, cached daily. All three get a `_check_*()` comparator in `scoring/probability_engine.py`, mirroring the existing `_check_macro_backdrop()`'s exact shape (returns `(bool|None, str|None)`, multiplies `confidence`, never touches `direction`/`probability`), wired into `score_bundle()` as new optional parameters (default `None`, fully backward compatible). Only the article-based accumulator pipeline (`scoring/backtest_accumulator.py`) needs new fetch-wiring — the essence-only dashboard pipeline (`webapp/scoring_service.py`) does not call `score_bundle()` and is untouched by this plan.

**Tech Stack:** Python 3, `requests` (already a dependency), SQLite (for COT's daily cache — mirrors the existing `check_history` cache table pattern in `scoring/backtest_store.py`), pytest.

**Spec:** [docs/superpowers/specs/2026-09-02-fundamental-signals-batch-design.md](../specs/2026-09-02-fundamental-signals-batch-design.md)

## Global Constraints

- None of the three new checks may ever alter `direction` or `probability` — only `confidence`, via a multiplicative discount. This is the single most important invariant in this plan; every task that touches `score_bundle()` must have a test proving it.
- Every new module/check is fail-open: a missing key, failed request, insufficient data, or any exception returns `None`/`(None, None)`/`(False, None)` as appropriate — never raises, never fabricates a value, never blocks scoring.
- Series-specific/module-local constants (series IDs, lookback windows, lean/shock thresholds) live in the module that owns them (`data_layer/macro_backdrop.py`, `data_layer/cot_positioning.py`) — mirroring `DOLLAR_INDEX_LEAN_THRESHOLD_PCT`'s existing placement, NOT `config/settings.py`. Only the cross-module confidence-multiplier constants (consumed by `scoring/probability_engine.py`) live in `config/settings.py`, mirroring `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER`'s existing placement exactly. (This corrects the spec's Section 1/COT code block, which showed the COT threshold constants under a `config/settings.py` heading — the plan follows the codebase's real, established convention instead.)
- Every new threshold constant carries an inline comment marking it as an explicitly untuned starting value, matching every existing threshold constant's own honesty in this codebase.
- Omitting any of the three new `score_bundle()` parameters must reproduce today's exact behavior (same contract `macro_backdrop=None` already has).
- Equity risk-sentiment only ever applies to instruments whose `INSTRUMENTS[instrument]["usd_relationship"] == "risk_sentiment"` (today: US30 only) — must return `(None, None)` for any other instrument regardless of data availability.
- COT crowding only ever dampens confidence when positioning is BOTH extreme AND aligned with the read's own direction — never on disagreement (opposite polarity from the other checks).

---

## File Structure

- **Modify `config/settings.py`**: add `COT_CROWDING_CONFIDENCE_MULTIPLIER`, `EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER`, `OIL_SHOCK_CONFIDENCE_MULTIPLIER` — the three cross-module confidence multipliers, placed near the existing `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER`.
- **Modify `data_layer/macro_backdrop.py`**: add `EQUITY_INDEX_SERIES_ID`/`EQUITY_INDEX_LEAN_THRESHOLD_PCT`/`OIL_SHOCK_DAILY_THRESHOLD_PCT` module constants, extend `MacroBackdropRead` with `equity_index_trend_pct`/`equity_index_latest_date`/`oil_daily_change_pct` fields, extend `get_macro_backdrop_read()` to fetch the new series and correctly detect "genuinely no data at all."
- **Create `data_layer/cot_positioning.py`**: `CotPositioningRead` dataclass (with `.is_crowded` property), `get_cot_positioning_read()` — fetches CFTC's free TFF (Traders in Financial Futures) API, computes a trailing-window percentile, caches the result for the current day.
- **Modify `scoring/probability_engine.py`**: add `_check_cot_crowding()`, `_check_equity_risk_sentiment()`, `_check_oil_shock()`; wire all three into `score_bundle()` (new optional params, new `ProbabilityResult` fields).
- **Modify `scoring/backtest_accumulator.py`**: fetch `cot_positioning` once per cycle (mirroring the existing `macro_backdrop`-once-per-cycle pattern) and thread it through `score_and_record_event()` → `score_bundle()`. The equity/oil-shock checks need NO new wiring here — they ride on the same `macro_backdrop` object already threaded through today.
- **Tests**: `tests/test_macro_backdrop.py` (extended), `tests/test_cot_positioning.py` (new), `tests/test_probability_engine.py` (extended), `tests/test_backtest_accumulator.py` (extended).

---

### Task 1: Confidence-multiplier constants in `config/settings.py`

**Files:**
- Modify: `config/settings.py` (near line 627, right after `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER`)

**Interfaces:**
- Produces: `COT_CROWDING_CONFIDENCE_MULTIPLIER: float`, `EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER: float`, `OIL_SHOCK_CONFIDENCE_MULTIPLIER: float` — importable from `config.settings`, consumed by Task 4.

This task has no独立 test file of its own (three constants, no logic) — it's verified by Tasks 4's tests importing and using them. No TDD cycle applies to a bare constant addition; just add them and move on to the next task, which is the one that actually exercises them.

- [ ] **Step 1: Add the three constants**

In `config/settings.py`, immediately after the existing block ending in `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER = 0.7` (around line 627), add:

```python
# --- Fundamental signals batch (docs/superpowers/specs/2026-09-02-fundamental-signals-batch-design.md) ---
# Three more confidence-only modifiers, same discipline as
# MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER above: none of these
# are blended into aggregate_usd_sentiment as a weighted vote (no
# backtested trust weight exists for any of them yet) — each can only
# discount CONFIDENCE, never invent or override a direction. All three
# are untuned starting values, needs revisiting once real backtest data
# exists.

# COT positioning crowding (scoring/probability_engine.py's
# _check_cot_crowding()): dampens confidence when speculative USD Index
# futures positioning is BOTH extreme AND aligned with this read's own
# direction — a crowded trade in the same direction as the call is a
# caution signal, the opposite polarity from the disagreement-based
# checks below.
COT_CROWDING_CONFIDENCE_MULTIPLIER = 0.85

# Equity risk-sentiment leg (scoring/probability_engine.py's
# _check_equity_risk_sentiment()): dampens confidence when an equity
# index's trend clearly disagrees with a risk_sentiment-mapped
# instrument's own score (today: US30 only) — same disagreement-based
# discount pattern as the macro backdrop check above.
EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER = 0.7

# Oil single-day shock flag (scoring/probability_engine.py's
# _check_oil_shock()): dampens confidence whenever a sharp single-session
# oil move fires, regardless of direction or agreement with anything else
# — a "treat this call with extra caution, something sharp just happened
# outside the tracked calendar" flag, not an agree/disagree comparison.
OIL_SHOCK_CONFIDENCE_MULTIPLIER = 0.8
```

- [ ] **Step 2: Verify the file still imports cleanly**

Run: `python -c "from config.settings import COT_CROWDING_CONFIDENCE_MULTIPLIER, EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER, OIL_SHOCK_CONFIDENCE_MULTIPLIER; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add config/settings.py
git commit -m "feat: add confidence-multiplier constants for COT/equity-risk/oil-shock checks"
```

---

### Task 2: Equity risk-sentiment + oil-shock data in `data_layer/macro_backdrop.py`

**Files:**
- Modify: `data_layer/macro_backdrop.py`
- Test: `tests/test_macro_backdrop.py`

**Interfaces:**
- Consumes: nothing new from Task 1 (this task's new module constants are self-contained, following `DOLLAR_INDEX_LEAN_THRESHOLD_PCT`'s existing local-constant pattern, not `config.settings`).
- Produces: `MacroBackdropRead.equity_index_trend_pct: Optional[float]`, `MacroBackdropRead.equity_index_latest_date: Optional[dt.date]`, `MacroBackdropRead.oil_daily_change_pct: Optional[float]` — consumed by Task 4's `_check_equity_risk_sentiment()`/`_check_oil_shock()`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_macro_backdrop.py`. First, read the existing tests for `DOLLAR_INDEX_SERIES_ID`/`OIL_SERIES_ID` fetches in that file (they mock `requests.get` and feed it a FRED-shaped JSON response) — reuse the exact same mocking pattern and any existing `_fred_response(...)` helper the file already has. Add these tests near the existing oil-trend tests:

```python
def test_get_macro_backdrop_read_includes_equity_index_trend():
    print("=== get_macro_backdrop_read: SP500 equity trend is fetched alongside dollar/yield/oil ===")
    with patch("data_layer.macro_backdrop.FRED_API_KEY", "test-key"), \
         patch("requests.get") as mock_get:
        mock_get.return_value = _fred_response([
            {"date": "2026-08-20", "value": "5000.00"},
            {"date": "2026-08-31", "value": "5100.00"},
        ])
        read = get_macro_backdrop_read()

    assert read is not None
    assert read.equity_index_trend_pct == pytest.approx(2.0, abs=0.01)  # (5100-5000)/5000*100
    assert read.equity_index_latest_date == dt.date(2026, 8, 31)
    print("PASS\n")


def test_get_macro_backdrop_read_includes_oil_daily_change():
    print("=== get_macro_backdrop_read: oil's single most-recent-day change is captured separately from its 10-day trend ===")
    with patch("data_layer.macro_backdrop.FRED_API_KEY", "test-key"), \
         patch("requests.get") as mock_get:
        mock_get.return_value = _fred_response([
            {"date": "2026-08-28", "value": "70.00"},
            {"date": "2026-08-29", "value": "70.50"},
            {"date": "2026-08-31", "value": "75.00"},  # the newest observation
        ])
        read = get_macro_backdrop_read()

    assert read is not None
    # Daily change = newest vs. SECOND-newest observation only (70.50 -> 75.00),
    # not the full window (70.00 -> 75.00) — a shock is a one-session move.
    assert read.oil_daily_change_pct == pytest.approx((75.00 - 70.50) / 70.50 * 100.0, abs=0.01)
    print("PASS\n")


def test_get_macro_backdrop_read_returns_none_only_when_all_four_series_fail():
    print("=== get_macro_backdrop_read: a real equity-only read is NOT discarded as \"no data\" ===")
    def _side_effect(*args, **kwargs):
        series_id = kwargs["params"]["series_id"]
        if series_id == EQUITY_INDEX_SERIES_ID:
            return _fred_response([
                {"date": "2026-08-20", "value": "5000.00"},
                {"date": "2026-08-31", "value": "5100.00"},
            ])
        raise requests.exceptions.RequestException("simulated failure")

    with patch("data_layer.macro_backdrop.FRED_API_KEY", "test-key"), \
         patch("requests.get", side_effect=_side_effect):
        read = get_macro_backdrop_read()

    assert read is not None  # NOT None, even though dollar/yield/oil all failed
    assert read.equity_index_trend_pct == pytest.approx(2.0, abs=0.01)
    assert read.dollar_index_trend_pct is None
    assert read.real_yield_trend_bps is None
    assert read.oil_trend_pct is None
    print("PASS\n")
```

Check the top of `tests/test_macro_backdrop.py` for its existing imports — add `EQUITY_INDEX_SERIES_ID` to whatever import line already pulls in `DOLLAR_INDEX_SERIES_ID`/`OIL_SERIES_ID`, and confirm `pytest` and `requests` are already imported (they should be, given the existing tests use `pytest.approx` and raise `requests.exceptions.RequestException`-shaped failures — if not already imported, add them). Add all three new test names to the file's `if __name__ == "__main__":` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_macro_backdrop.py -k "equity_index or oil_daily_change or all_four_series" -v`
Expected: FAIL — `AttributeError: 'MacroBackdropRead' object has no attribute 'equity_index_trend_pct'` (and similar) on all three.

- [ ] **Step 3: Live-verify the FRED `SP500` series before wiring it in**

Before writing the implementation, confirm the series actually exists and returns real data — same "verify against the real endpoint before trusting it" discipline this module's own docstring already follows for `DTWEXBGS`/`DFII10`/`DCOILWTICO`. Run (with a real `FRED_API_KEY` set in the environment):

```bash
python -c "
import requests, os
resp = requests.get('https://api.stlouisfed.org/fred/series/observations', params={
    'series_id': 'SP500', 'file_type': 'json', 'api_key': os.environ['FRED_API_KEY'],
    'sort_order': 'desc', 'limit': 5,
})
print(resp.status_code)
print(resp.json().get('observations', [])[:3])
"
```

Expected: HTTP 200, a real list of recent S&P 500 closing values with non-`.` values. If this fails (series doesn't exist, or is deprecated/renamed), stop and find FRED's current correct series ID for the S&P 500 before proceeding — do not guess or hardcode an unverified ID.

- [ ] **Step 4: Implement — extend `MacroBackdropRead`, add module constants, extend `_fetch_trend`'s caller, extend `get_macro_backdrop_read()`**

In `data_layer/macro_backdrop.py`, add near the top (alongside `OIL_SERIES_ID`):

```python
EQUITY_INDEX_SERIES_ID = "SP500"

# Same reasoning as OIL_LEAN_THRESHOLD_PCT's comment — an untuned starting
# value. The S&P 500 is a broad index like the dollar index, not a raw
# commodity like oil, so this uses a threshold in the dollar index's
# scale (0.3%) rather than oil's wider 5% — tightened somewhat since
# risk-sentiment moves worth flagging tend to be larger single moves than
# routine dollar-index drift. Needs revisiting once real backtest data
# exists.
EQUITY_INDEX_LEAN_THRESHOLD_PCT = 1.0

# A single most-recent-DAY oil move, deliberately distinct from
# OIL_LEAN_THRESHOLD_PCT's 10-day trend — a "shock" is a sharp one-session
# move, not a multi-day drift, and re-using the 10-day trend's threshold
# would conflate the two. Tighter than OIL_LEAN_THRESHOLD_PCT=5.0 because
# this is measuring ONE session's move, not a 10-day window's worth.
# Untuned starting value.
OIL_SHOCK_DAILY_THRESHOLD_PCT = 4.0
```

Add `EQUITY_INDEX_SERIES_ID` to `PERCENT_CHANGE_SERIES_IDS` (it's a level series like the dollar index and oil, not already a percentage like the real yield):

```python
PERCENT_CHANGE_SERIES_IDS = {DOLLAR_INDEX_SERIES_ID, OIL_SERIES_ID, EQUITY_INDEX_SERIES_ID}
```

Extend the `MacroBackdropRead` dataclass:

```python
@dataclass
class MacroBackdropRead:
    dollar_index_trend_pct: Optional[float]   # % change over the window; positive = dollar strengthening
    dollar_index_latest_date: Optional[dt.date]
    real_yield_trend_bps: Optional[float]      # change in basis points over the window; positive = yields rising
    real_yield_latest_date: Optional[dt.date]
    oil_trend_pct: Optional[float]             # % change over the window; positive = WTI strengthening (inflation-expectations proxy)
    oil_latest_date: Optional[dt.date]
    equity_index_trend_pct: Optional[float]    # % change over the window; positive = equities strengthening (risk-on proxy)
    equity_index_latest_date: Optional[dt.date]
    oil_daily_change_pct: Optional[float]      # % change over the single most recent session ONLY — distinct from oil_trend_pct's 10-day window; used for shock detection, not the .lean fallback chain
    lookback_days: int

    @property
    def lean(self) -> Optional[int]:
        """
        +1 = macro backdrop leans USD-bullish, -1 = USD-bearish, None =
        no clear lean (below threshold on every measure, or no data at
        all). Dollar index is the primary read (it's the more direct
        USD-strength measure); real yield is the first fallback when the
        dollar index itself shows no clear move — real yields moving
        while the index is flat is still a genuine, if secondary,
        USD-supportive/undermining signal. Oil is the lowest-priority
        fallback: it's one causal step further removed (a leading
        inflation-expectations proxy, not a direct USD measure — see
        module docstring), so it only fills a gap when BOTH direct USD
        measures are silent, and never overrides them.

        equity_index_trend_pct and oil_daily_change_pct are deliberately
        NOT part of this fallback chain — they answer different
        questions (risk-on/off, single-day shock) than "does the dollar
        backdrop lean bullish or bearish," and are consumed directly by
        their own dedicated checks in scoring/probability_engine.py
        instead (_check_equity_risk_sentiment, _check_oil_shock).
        """
        if self.dollar_index_trend_pct is not None and abs(self.dollar_index_trend_pct) >= DOLLAR_INDEX_LEAN_THRESHOLD_PCT:
            return 1 if self.dollar_index_trend_pct > 0 else -1
        if self.real_yield_trend_bps is not None and abs(self.real_yield_trend_bps) >= REAL_YIELD_LEAN_THRESHOLD_BPS:
            return 1 if self.real_yield_trend_bps > 0 else -1
        if self.oil_trend_pct is not None and abs(self.oil_trend_pct) >= OIL_LEAN_THRESHOLD_PCT:
            return 1 if self.oil_trend_pct > 0 else -1
        return None
```

Add a small helper for the single-day change, right after `_fetch_trend`:

```python
def _fetch_daily_change(series_id: str) -> Optional[float]:
    """
    Returns the % change between the two most recent REAL observations
    (newest vs. second-newest) — deliberately NOT the same as
    _fetch_trend()'s window-based change, which compares newest vs.
    OLDEST across the whole lookback. Used for shock detection: a
    "shock" is defined as one session's move, not a multi-day drift.
    Returns None on any failure, missing key, or fewer than 2 usable
    observations — same fail-open contract as _fetch_trend().
    """
    if not FRED_API_KEY:
        return None
    try:
        resp = requests.get(
            f"{FRED_BASE_URL}/series/observations",
            params={
                "series_id": series_id, "file_type": "json", "api_key": FRED_API_KEY,
                "sort_order": "desc", "limit": 5,  # a handful of recent obs is enough to find 2 usable ones past weekends/holidays
            },
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[macro_backdrop] WARNING: daily-change fetch failed for {series_id}: {exc}")
        return None

    usable = [r for r in rows if r.get("value") not in (None, ".")]
    if len(usable) < 2:
        return None

    newest_value, second_newest_value = float(usable[0]["value"]), float(usable[1]["value"])
    if second_newest_value == 0:
        return None
    return (newest_value - second_newest_value) / second_newest_value * 100.0
```

Update `get_macro_backdrop_read()`:

```python
def get_macro_backdrop_read(days_back: int = DEFAULT_LOOKBACK_DAYS) -> Optional[MacroBackdropRead]:
    """
    Returns None only if ALL FOUR series are entirely unavailable (no
    key, or every fetch failed) — a partial read (some series available,
    others not) still returns a real MacroBackdropRead with the missing
    fields None, since .lean already handles a partial read via its
    fallback chain, and equity_index_trend_pct/oil_daily_change_pct are
    read independently of .lean by their own dedicated checks.
    """
    dollar_trend, dollar_date = _fetch_trend(DOLLAR_INDEX_SERIES_ID, days_back)
    yield_trend, yield_date = _fetch_trend(REAL_YIELD_SERIES_ID, days_back)
    oil_trend, oil_date = _fetch_trend(OIL_SERIES_ID, days_back)
    equity_trend, equity_date = _fetch_trend(EQUITY_INDEX_SERIES_ID, days_back)
    oil_daily_change = _fetch_daily_change(OIL_SERIES_ID)

    if dollar_trend is None and yield_trend is None and oil_trend is None and equity_trend is None:
        return None

    return MacroBackdropRead(
        dollar_index_trend_pct=dollar_trend, dollar_index_latest_date=dollar_date,
        real_yield_trend_bps=yield_trend, real_yield_latest_date=yield_date,
        oil_trend_pct=oil_trend, oil_latest_date=oil_date,
        equity_index_trend_pct=equity_trend, equity_index_latest_date=equity_date,
        oil_daily_change_pct=oil_daily_change,
        lookback_days=days_back,
    )
```

Note: `oil_daily_change_pct` is deliberately NOT part of the all-four-None check — it's sourced from the same `OIL_SERIES_ID` as `oil_trend`, so if `oil_trend` fetched successfully, `oil_daily_change` almost always will too (and if oil fails entirely, `oil_trend is None` already contributes to the check). This avoids a redundant fifth condition that can never independently flip the outcome.

- [ ] **Step 5: Run tests to verify they pass, and run the whole file**

Run: `python -m pytest tests/test_macro_backdrop.py -v`
Expected: all PASS, including the three new tests. Any existing test that constructs a `MacroBackdropRead(...)` directly (not via `get_macro_backdrop_read()`) will now fail with a missing-argument error — find those call sites (grep the test file for `MacroBackdropRead(`) and add `equity_index_trend_pct=None, equity_index_latest_date=None, oil_daily_change_pct=None` to each (these fields have no default in the dataclass, matching every other field's style — explicit is better than a silently-defaulted None here, since a caller constructing this directly should have to think about what it means).

- [ ] **Step 6: Commit**

```bash
git add data_layer/macro_backdrop.py tests/test_macro_backdrop.py
git commit -m "feat: add equity index trend and oil daily-change to macro backdrop read"
```

---

### Task 3: `data_layer/cot_positioning.py` (new module)

**Files:**
- Create: `data_layer/cot_positioning.py`
- Test: `tests/test_cot_positioning.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `CotPositioningRead` dataclass with `.is_crowded` property (`Optional[int]`: `+1`/`-1`/`None`), `get_cot_positioning_read(now: Optional[dt.datetime] = None) -> Optional[CotPositioningRead]` — consumed by Task 4's `_check_cot_crowding()` and Task 5's accumulator wiring.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cot_positioning.py`:

```python
"""
Tests for data_layer/cot_positioning.py — CFTC's free "Traders in
Financial Futures" (TFF) report, used for a confidence-only "is this
positioning already crowded" dampener (never a directional lean — see
docs/superpowers/specs/2026-09-02-fundamental-signals-batch-design.md).
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

from data_layer.cot_positioning import (
    get_cot_positioning_read, CotPositioningRead,
    COT_CROWDING_PERCENTILE_THRESHOLD, COT_CROWDING_LOOKBACK_WEEKS,
)


def _cftc_response(rows):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = rows
    return mock_resp


def _row(report_date, net_long):
    """One TFF report row shaped like the real CFTC API response — only
    the fields this module actually reads."""
    return {
        "market_and_exchange_names": "U.S. DOLLAR INDEX - ICE FUTURES U.S.",
        "report_date_as_yyyy_mm_dd": report_date,
        "lev_money_positions_long": str(net_long if net_long > 0 else 0),
        "lev_money_positions_short": str(-net_long if net_long < 0 else 0),
    }


def test_fetch_failure_returns_none():
    print("=== get_cot_positioning_read: a failed request returns None, never raises ===")
    with patch("requests.get", side_effect=requests.exceptions.RequestException("simulated failure")):
        assert get_cot_positioning_read() is None
    print("PASS\n")


def test_empty_response_returns_none():
    print("=== get_cot_positioning_read: an empty result set (no matching rows) returns None ===")
    with patch("requests.get", return_value=_cftc_response([])):
        assert get_cot_positioning_read() is None
    print("PASS\n")


def test_real_data_computes_percentile_and_is_crowded():
    print("=== get_cot_positioning_read: a real trailing window computes a percentile and .is_crowded ===")
    # 20 weekly rows, net long climbing from 1000 to 20000 — the newest
    # (20000) is the highest in the window, so it should rank at/near the
    # 100th percentile and read as crowded-long.
    rows = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", 1000 * (i + 1)) for i in range(20)]
    # Ensure rows are returned newest-first, matching a real $order=...DESC query
    rows = list(reversed(rows))
    with patch("requests.get", return_value=_cftc_response(rows)):
        read = get_cot_positioning_read()

    assert read is not None
    assert isinstance(read, CotPositioningRead)
    assert read.net_leveraged_funds_position == 20000
    assert read.percentile_in_trailing_window == pytest.approx(100.0, abs=0.01)
    assert read.is_crowded == 1  # extreme long
    print("PASS\n")


def test_mid_range_positioning_is_not_crowded():
    print("=== get_cot_positioning_read: positioning in the middle of its trailing range is NOT flagged crowded ===")
    # Net long oscillating in a tight band around 5000 — the newest
    # reading sits near the middle of the range, not an extreme.
    values = [4800, 5200, 4900, 5100, 5000] * 4  # 20 rows, newest last before reversal
    rows = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", v) for i, v in enumerate(values)]
    rows = list(reversed(rows))
    with patch("requests.get", return_value=_cftc_response(rows)):
        read = get_cot_positioning_read()

    assert read is not None
    assert read.is_crowded is None  # mid-range, not extreme
    print("PASS\n")


def test_daily_cache_avoids_refetching_same_day():
    print("=== get_cot_positioning_read: a second call the same day reuses the cached read, doesn't re-fetch ===")
    rows = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", 1000 * (i + 1)) for i in range(20)]
    rows = list(reversed(rows))
    now = dt.datetime(2026, 9, 2, 10, 0, tzinfo=dt.timezone.utc)
    with patch("requests.get", return_value=_cftc_response(rows)) as mock_get:
        first = get_cot_positioning_read(now=now)
        second = get_cot_positioning_read(now=now + dt.timedelta(hours=2))  # same calendar day
    assert mock_get.call_count == 1  # only fetched once
    assert first == second
    print("PASS\n")


if __name__ == "__main__":
    test_fetch_failure_returns_none()
    test_empty_response_returns_none()
    test_real_data_computes_percentile_and_is_crowded()
    test_mid_range_positioning_is_not_crowded()
    test_daily_cache_avoids_refetching_same_day()
    print("All cot_positioning tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cot_positioning.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_layer.cot_positioning'`.

- [ ] **Step 3: Implement `data_layer/cot_positioning.py`**

The dataset ID and field names below were live-verified during this plan's brainstorm (a real request against `https://publicreporting.cftc.gov/resource/gpe5-46if.json` returned real rows with these exact field names, including a confirmed row for `"U.S. DOLLAR INDEX - ICE FUTURES U.S."` with `lev_money_positions_long`/`lev_money_positions_short` fields). Re-verify freshness live once more before trusting this in production (the same discipline `data_layer/macro_backdrop.py`'s own docstring documents for its FRED series) — the dataset ID itself is stable (Socrata resource IDs don't change), but confirm the query below still returns current data, not stale/archived rows.

```python
"""
Free, no-token CFTC "Traders in Financial Futures" (TFF) Commitments of
Traders data — data_layer/cot_positioning.py, part of the fundamental
signals batch (docs/superpowers/specs/2026-09-02-fundamental-signals-batch-design.md).

Used for ONE thing only: a confidence-only "is USD positioning already
crowded" dampener in scoring/probability_engine.py's
_check_cot_crowding() — deliberately NEVER a directional lean (see the
spec's Decisions section: explicitly deferred, revisit only if the
dampener-only design proves insufficient).

Data source: CFTC's Socrata Open Data API, publicreporting.cftc.gov,
resource gpe5-46if ("TFF - Futures Only") — live-verified during this
plan's brainstorm: genuinely free, no API key/token required, real
weekly rows for "U.S. DOLLAR INDEX - ICE FUTURES U.S." with
lev_money_positions_long/lev_money_positions_short fields (the
"Leveraged Funds" trader category — the standard "smart money crowding"
read in COT-based fundamental analysis, as opposed to Dealers/Asset
Managers/Other Reportables, which are hedging-driven).

Published weekly (Fridays, covering the prior Tuesday's positions) —
fetched at most once per calendar day via a simple in-process cache,
never re-fetched every scoring cycle.

READ-ONLY, same fail-open contract as every other data_layer module:
returns None on a missing/empty response, a failed request, or any
exception — never raises, never invents a value.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import requests

CFTC_TFF_RESOURCE_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
USD_INDEX_MARKET_NAME = "U.S. DOLLAR INDEX - ICE FUTURES U.S."

# How far back to look for the trailing percentile window — a standard
# one-year COT lookback. Untuned starting value.
COT_CROWDING_LOOKBACK_WEEKS = 52

# Top/bottom this-many-percent of the trailing window counts as
# "crowded." Untuned starting value, needs revisiting once real backtest
# data exists.
COT_CROWDING_PERCENTILE_THRESHOLD = 15.0


@dataclass
class CotPositioningRead:
    net_leveraged_funds_position: Optional[int]     # contracts, net long(+)/short(-); None if unavailable
    percentile_in_trailing_window: Optional[float]   # 0-100, this reading's rank within the trailing window
    report_date: Optional[dt.date]
    lookback_weeks: int

    @property
    def is_crowded(self) -> Optional[int]:
        """
        +1 = net-long crowding (extreme long positioning), -1 = net-short
        crowding, None = not extreme (within the normal range) or no
        data. "Extreme" = top/bottom COT_CROWDING_PERCENTILE_THRESHOLD of
        the trailing window.
        """
        if self.percentile_in_trailing_window is None or self.net_leveraged_funds_position is None:
            return None
        if self.percentile_in_trailing_window >= (100.0 - COT_CROWDING_PERCENTILE_THRESHOLD):
            return 1
        if self.percentile_in_trailing_window <= COT_CROWDING_PERCENTILE_THRESHOLD:
            return -1
        return None


_cache_date: Optional[dt.date] = None
_cache_read: Optional[CotPositioningRead] = None


def _fetch_rows(limit: int) -> list[dict]:
    resp = requests.get(
        CFTC_TFF_RESOURCE_URL,
        params={
            "$where": f"market_and_exchange_names = '{USD_INDEX_MARKET_NAME}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": limit,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_cot_positioning_read(now: Optional[dt.datetime] = None) -> Optional[CotPositioningRead]:
    """
    Returns None on any failure, an empty result, or fewer than 2 usable
    rows (can't compute a percentile from one point). Cached per
    calendar day (UTC) — a second call the same day reuses the first
    call's result rather than re-fetching, matching this data's real
    weekly-at-best freshness.
    """
    global _cache_date, _cache_read

    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.date()
    if _cache_date == today:
        return _cache_read

    try:
        rows = _fetch_rows(COT_CROWDING_LOOKBACK_WEEKS)
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[cot_positioning] WARNING: fetch failed: {exc}")
        _cache_date, _cache_read = today, None
        return None

    if not rows:
        _cache_date, _cache_read = today, None
        return None

    try:
        net_positions = []
        for row in rows:
            net_long = float(row.get("lev_money_positions_long", 0) or 0)
            net_short = float(row.get("lev_money_positions_short", 0) or 0)
            net_positions.append(net_long - net_short)
    except (TypeError, ValueError) as exc:
        print(f"[cot_positioning] WARNING: unexpected row shape: {exc}")
        _cache_date, _cache_read = today, None
        return None

    if len(net_positions) < 2:
        _cache_date, _cache_read = today, None
        return None

    newest_net = net_positions[0]
    # Percentile rank of the newest reading within the whole window
    # (including itself) — what fraction of the window's values are at
    # or below the newest reading.
    at_or_below = sum(1 for v in net_positions if v <= newest_net)
    percentile = at_or_below / len(net_positions) * 100.0

    newest_date = dt.date.fromisoformat(rows[0]["report_date_as_yyyy_mm_dd"].split("T")[0])

    read = CotPositioningRead(
        net_leveraged_funds_position=int(newest_net),
        percentile_in_trailing_window=percentile,
        report_date=newest_date,
        lookback_weeks=COT_CROWDING_LOOKBACK_WEEKS,
    )
    _cache_date, _cache_read = today, read
    return read
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cot_positioning.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add data_layer/cot_positioning.py tests/test_cot_positioning.py
git commit -m "feat: add CFTC COT positioning read for the crowding confidence dampener"
```

---

### Task 4: Wire all three checks into `scoring/probability_engine.py`

**Files:**
- Modify: `scoring/probability_engine.py`
- Test: `tests/test_probability_engine.py`

**Interfaces:**
- Consumes: `MacroBackdropRead.equity_index_trend_pct`/`.oil_daily_change_pct` (Task 2), `CotPositioningRead`/`.is_crowded` (Task 3), `COT_CROWDING_CONFIDENCE_MULTIPLIER`/`EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER`/`OIL_SHOCK_CONFIDENCE_MULTIPLIER` (Task 1).
- Produces: `_check_cot_crowding(aggregate_usd, cot_positioning) -> tuple[bool | None, str | None]`, `_check_equity_risk_sentiment(instrument_score, instrument, macro_backdrop) -> tuple[bool | None, str | None]`, `_check_oil_shock(macro_backdrop) -> tuple[bool, str | None]`. `score_bundle()` gains `cot_positioning=None` and reuses the existing `macro_backdrop` parameter for the other two (no new parameter needed for equity/oil-shock — they read new fields off the same object). `ProbabilityResult` gains `cot_crowding_flag: bool | None = None`, `cot_crowding_note: str | None = None`, `equity_risk_agrees: bool | None = None`, `equity_risk_note: str | None = None`, `oil_shock_flag: bool = False`, `oil_shock_note: str | None = None` — consumed by Task 5 (indirectly, via `score_bundle()`'s existing return contract) and any future dashboard-display work (out of scope here).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_probability_engine.py`. First read the existing tests for `_check_macro_backdrop()` and `score_bundle(..., macro_backdrop=...)` in that file (search for `macro_backdrop` and `_check_macro_backdrop`) — reuse whatever bundle-building/instrument-fixture helpers that file already has (e.g. a `_bundle(...)` helper, `EventNewsBundle` construction pattern). Add these tests near the existing macro-backdrop tests:

```python
# --- _check_cot_crowding ---

def test_check_cot_crowding_no_data_returns_none_none():
    print("=== _check_cot_crowding: no COT data at all returns (None, None) ===")
    assert _check_cot_crowding(aggregate_usd=0.5, cot_positioning=None) == (None, None)
    print("PASS\n")


def test_check_cot_crowding_not_extreme_returns_none_none():
    print("=== _check_cot_crowding: positioning within the normal range returns (None, None) regardless of the read's direction ===")
    cot = CotPositioningRead(net_leveraged_funds_position=100, percentile_in_trailing_window=50.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    assert _check_cot_crowding(aggregate_usd=0.5, cot_positioning=cot) == (None, None)
    print("PASS\n")


def test_check_cot_crowding_extreme_and_aligned_dampens():
    print("=== _check_cot_crowding: extreme long positioning aligned with a USD-bullish read triggers the dampener ===")
    cot = CotPositioningRead(net_leveraged_funds_position=50000, percentile_in_trailing_window=98.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    crowded, note = _check_cot_crowding(aggregate_usd=0.5, cot_positioning=cot)  # positive = USD-bullish, matches is_crowded=+1
    assert crowded is True
    assert note is not None
    print("PASS\n")


def test_check_cot_crowding_extreme_but_opposite_direction_no_effect():
    print("=== _check_cot_crowding: extreme long positioning does NOT dampen a USD-BEARISH read (crowding must match direction) ===")
    cot = CotPositioningRead(net_leveraged_funds_position=50000, percentile_in_trailing_window=98.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    crowded, note = _check_cot_crowding(aggregate_usd=-0.5, cot_positioning=cot)  # negative = USD-bearish, opposite of is_crowded=+1
    assert crowded is None  # not (False, ...) — this check has no disagreement case, only "crowded+aligned" or "no concern"
    assert note is None
    print("PASS\n")


# --- _check_equity_risk_sentiment ---

def test_check_equity_risk_sentiment_only_applies_to_risk_sentiment_instruments():
    print("=== _check_equity_risk_sentiment: returns (None, None) for XAUUSD regardless of equity data (not risk_sentiment-mapped) ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=5.0, equity_index_latest_date=dt.date(2026, 8, 29),  # strongly risk-on
        oil_daily_change_pct=None, lookback_days=10,
    )
    assert _check_equity_risk_sentiment(instrument_score=-0.5, instrument="XAUUSD", macro_backdrop=macro) == (None, None)
    print("PASS\n")


def test_check_equity_risk_sentiment_agrees_for_us30():
    print("=== _check_equity_risk_sentiment: US30 with equities trending up and a bullish instrument_score agrees ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=5.0, equity_index_latest_date=dt.date(2026, 8, 29),
        oil_daily_change_pct=None, lookback_days=10,
    )
    agrees, note = _check_equity_risk_sentiment(instrument_score=0.3, instrument="US30", macro_backdrop=macro)
    assert agrees is True
    assert note is None
    print("PASS\n")


def test_check_equity_risk_sentiment_disagrees_for_us30():
    print("=== _check_equity_risk_sentiment: US30 with equities trending DOWN (risk-off) but a bullish instrument_score disagrees ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=-5.0, equity_index_latest_date=dt.date(2026, 8, 29),
        oil_daily_change_pct=None, lookback_days=10,
    )
    agrees, note = _check_equity_risk_sentiment(instrument_score=0.3, instrument="US30", macro_backdrop=macro)
    assert agrees is False
    assert note is not None
    print("PASS\n")


def test_check_equity_risk_sentiment_below_threshold_no_effect():
    print("=== _check_equity_risk_sentiment: a tiny equity move below EQUITY_INDEX_LEAN_THRESHOLD_PCT has no effect ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=0.1, equity_index_latest_date=dt.date(2026, 8, 29),  # well below 1.0% threshold
        oil_daily_change_pct=None, lookback_days=10,
    )
    assert _check_equity_risk_sentiment(instrument_score=0.3, instrument="US30", macro_backdrop=macro) == (None, None)
    print("PASS\n")


# --- _check_oil_shock ---

def test_check_oil_shock_no_data_returns_false_none():
    print("=== _check_oil_shock: no macro backdrop data at all returns (False, None) ===")
    assert _check_oil_shock(macro_backdrop=None) == (False, None)
    print("PASS\n")


def test_check_oil_shock_below_threshold_no_effect():
    print("=== _check_oil_shock: a routine day-over-day oil move below OIL_SHOCK_DAILY_THRESHOLD_PCT has no effect ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=None, equity_index_latest_date=None,
        oil_daily_change_pct=1.5, lookback_days=10,  # well below 4.0% threshold
    )
    assert _check_oil_shock(macro_backdrop=macro) == (False, None)
    print("PASS\n")


def test_check_oil_shock_above_threshold_triggers_regardless_of_direction():
    print("=== _check_oil_shock: a sharp single-day oil move (either direction) triggers the flag ===")
    for daily_change in (6.0, -6.0):
        macro = MacroBackdropRead(
            dollar_index_trend_pct=None, dollar_index_latest_date=None,
            real_yield_trend_bps=None, real_yield_latest_date=None,
            oil_trend_pct=None, oil_latest_date=None,
            equity_index_trend_pct=None, equity_index_latest_date=None,
            oil_daily_change_pct=daily_change, lookback_days=10,
        )
        shocked, note = _check_oil_shock(macro_backdrop=macro)
        assert shocked is True
        assert note is not None
    print("PASS\n")


# --- score_bundle() integration: the core invariant — none of the three ever touch direction/probability ---

def test_score_bundle_new_signals_default_to_no_effect_when_omitted():
    print("=== score_bundle: omitting cot_positioning entirely reproduces today's exact behavior (backward compatible) ===")
    bundle = _bundle("CPI m/m", [_article("Sticky inflation could push CPI higher")])
    result = score_bundle(bundle, "XAUUSD")  # no cot_positioning, no macro_backdrop — exactly like every existing call site
    assert result.cot_crowding_flag is None
    assert result.equity_risk_agrees is None
    assert result.oil_shock_flag is False
    print("PASS\n")


def test_score_bundle_cot_crowding_only_touches_confidence():
    print("=== score_bundle: a crowded, aligned COT read discounts confidence but never changes direction or probability ===")
    bundle = _bundle("CPI m/m", [_article("Sticky inflation could push CPI higher")])
    baseline = score_bundle(bundle, "XAUUSD")
    cot = CotPositioningRead(net_leveraged_funds_position=50000, percentile_in_trailing_window=98.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    with_cot = score_bundle(bundle, "XAUUSD", cot_positioning=cot)

    assert with_cot.direction == baseline.direction
    assert with_cot.probability == pytest.approx(baseline.probability)
    assert with_cot.confidence < baseline.confidence  # crowding only ever DAMPENS
    assert with_cot.cot_crowding_flag is True
    print("PASS\n")


def test_score_bundle_oil_shock_only_touches_confidence():
    print("=== score_bundle: an oil shock discounts confidence but never changes direction or probability ===")
    bundle = _bundle("CPI m/m", [_article("Sticky inflation could push CPI higher")])
    baseline = score_bundle(bundle, "XAUUSD")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=None, equity_index_latest_date=None,
        oil_daily_change_pct=7.0, lookback_days=10,
    )
    with_shock = score_bundle(bundle, "XAUUSD", macro_backdrop=macro)

    assert with_shock.direction == baseline.direction
    assert with_shock.probability == pytest.approx(baseline.probability)
    assert with_shock.confidence < baseline.confidence
    assert with_shock.oil_shock_flag is True
    print("PASS\n")
```

Add every new test name to the file's `if __name__ == "__main__":` block, and add `_check_cot_crowding`, `_check_equity_risk_sentiment`, `_check_oil_shock`, `CotPositioningRead`, `MacroBackdropRead` to the file's existing imports from `scoring.probability_engine`/`data_layer.macro_backdrop`/`data_layer.cot_positioning` as needed (check what's already imported first — `MacroBackdropRead` is likely already imported for the existing macro-backdrop tests).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_probability_engine.py -k "cot_crowding or equity_risk_sentiment or oil_shock" -v`
Expected: FAIL — `ImportError`/`AttributeError` on all of them (none of the three functions or fields exist yet).

- [ ] **Step 3: Implement the three `_check_*` functions**

In `scoring/probability_engine.py`, add these three functions right after the existing `_check_macro_backdrop()` (around line 590):

```python
def _check_cot_crowding(
    aggregate_usd: float,
    cot_positioning,  # CotPositioningRead | None — duck-typed (.is_crowded), no data_layer.cot_positioning import needed
) -> tuple[bool | None, str | None]:
    """
    Confidence-only crowding dampener (spec: never a directional lean).
    Opposite polarity from _check_macro_backdrop: this fires on
    AGREEMENT with an extreme reading, not disagreement — a crowded
    trade in the SAME direction as this read is the caution signal, not
    a crowded trade in the opposite direction (which this check ignores
    entirely, hence no (False, ...) case here at all).

    Returns (None, None) if no COT data, or positioning isn't extreme.
    Returns (True, note) if positioning IS extreme AND aligned with
    aggregate_usd's sign.
    """
    if cot_positioning is None:
        return None, None
    crowded_direction = cot_positioning.is_crowded
    if crowded_direction is None:
        return None, None

    usd_sign = 1 if aggregate_usd >= 0 else -1
    if crowded_direction != usd_sign:
        return None, None

    direction_label = "long" if crowded_direction > 0 else "short"
    note = (
        f"COT positioning shows crowded {direction_label} USD Index speculative positioning "
        f"(percentile {cot_positioning.percentile_in_trailing_window:.0f}) aligned with this read — "
        f"may already be priced in, treat with extra caution."
    )
    return True, note


def _check_equity_risk_sentiment(
    instrument_score: float,
    instrument: str,
    macro_backdrop,  # MacroBackdropRead | None — duck-typed (.equity_index_trend_pct), reuses the same object _check_macro_backdrop reads
) -> tuple[bool | None, str | None]:
    """
    Only ever active for risk_sentiment-mapped instruments (today: US30)
    — returns (None, None) immediately for anything else, regardless of
    equity data availability. Compares equity_index_trend_pct's sign
    (positive = risk-on) against instrument_score's sign for THIS
    instrument (not aggregate_usd) — an equity index has no USD sign of
    its own.
    """
    if INSTRUMENTS.get(instrument, {}).get("usd_relationship") != "risk_sentiment":
        return None, None
    if macro_backdrop is None:
        return None, None
    equity_trend = macro_backdrop.equity_index_trend_pct
    if equity_trend is None or abs(equity_trend) < EQUITY_INDEX_LEAN_THRESHOLD_PCT:
        return None, None

    equity_sign = 1 if equity_trend > 0 else -1
    instrument_sign = 1 if instrument_score >= 0 else -1
    if equity_sign == instrument_sign:
        return True, None

    equity_dir = "risk-on (equities up)" if equity_sign > 0 else "risk-off (equities down)"
    read_dir = "bullish" if instrument_sign > 0 else "bearish"
    note = (
        f"Equity risk-sentiment backdrop leans {equity_dir}, but this {instrument} read is {read_dir} "
        f"— treat with extra caution until they align."
    )
    return False, note


def _check_oil_shock(macro_backdrop) -> tuple[bool, str | None]:
    """
    Fires on a sharp single-session oil move, regardless of direction or
    of this bundle's own USD read — "something sharp just happened
    outside the tracked calendar," not an agree/disagree comparison.
    Always returns a bool (never None) for the flag itself, matching
    ProbabilityResult.oil_shock_flag's bool (not Optional[bool]) type —
    there's no meaningful "unknown" state distinct from "no shock."
    """
    if macro_backdrop is None:
        return False, None
    daily_change = macro_backdrop.oil_daily_change_pct
    if daily_change is None or abs(daily_change) < OIL_SHOCK_DAILY_THRESHOLD_PCT:
        return False, None

    direction = "spiked" if daily_change > 0 else "dropped"
    note = (
        f"Oil {direction} {abs(daily_change):.1f}% in the most recent session — "
        f"a possible exogenous shock outside the tracked calendar, treat this call with extra caution."
    )
    return True, note
```

Add the required imports at the top of `scoring/probability_engine.py` (check what's already imported first — `MacroBackdropRead`/`INSTRUMENTS` are likely already there for the existing macro-backdrop check; add whatever's missing):

```python
from config.settings import (
    COT_CROWDING_CONFIDENCE_MULTIPLIER, EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER,
    OIL_SHOCK_CONFIDENCE_MULTIPLIER,
)
from data_layer.macro_backdrop import EQUITY_INDEX_LEAN_THRESHOLD_PCT, OIL_SHOCK_DAILY_THRESHOLD_PCT
```

- [ ] **Step 4: Extend `ProbabilityResult` and wire the checks into `score_bundle()`**

In `ProbabilityResult` (around line 147-165), add after the existing `macro_backdrop_note` field:

```python
    cot_crowding_flag: bool | None = None       # None = no COT data or not extreme; True = crowded and aligned with this read (see R-fundamental-signals-batch)
    cot_crowding_note: str | None = None
    equity_risk_agrees: bool | None = None       # None = not a risk_sentiment instrument, or no equity data; True/False = did the equity backdrop agree?
    equity_risk_note: str | None = None
    oil_shock_flag: bool = False                 # True = a sharp single-session oil move was detected
    oil_shock_note: str | None = None
```

In `score_bundle()`'s signature (around line 701-711), add the new `cot_positioning` parameter (equity/oil-shock reuse the existing `macro_backdrop` parameter, no new parameter needed for those two):

```python
def score_bundle(
    bundle: EventNewsBundle,
    instrument: str,
    precursor_events: list[EconomicEvent] | None = None,
    print_call=None,   # PrintCall | None — duck-typed
    trend_signal=None,  # TrendSignal | None — duck-typed
    kalshi_read=None,   # KalshiRead | None — duck-typed
    kalshi_direction_override=None,  # str | None — 'higher_bullish'/'higher_bearish', see below
    macro_backdrop=None,  # MacroBackdropRead | None — duck-typed, see _check_macro_backdrop(), _check_equity_risk_sentiment(), _check_oil_shock()
    cot_positioning=None,  # CotPositioningRead | None — duck-typed, see _check_cot_crowding()
    current_direction: str | None = None,  # 'bullish'/'bearish'/'neutral' | None — see _direction_for_score()
) -> ProbabilityResult:
```

Add this to the function's docstring, right after the existing `macro_backdrop:` paragraph:

```
    cot_positioning: optional — an independent CFTC COT positioning read
    (data_layer.cot_positioning.CotPositioningRead), the fundamental
    signals batch's crowding dampener. NEVER blended into
    aggregate_usd_sentiment (same "no real backtested trust weight yet"
    discipline as macro_backdrop) — it can only discount CONFIDENCE, and
    only when positioning is BOTH extreme AND aligned with this read's
    own direction (opposite polarity from macro_backdrop's disagreement-
    based discount). See _check_cot_crowding().
```

In the body, right after the existing macro-backdrop check (around line 848-850), add the three new checks:

```python
    macro_backdrop_agrees, macro_backdrop_note = _check_macro_backdrop(aggregate_usd, macro_backdrop)
    if macro_backdrop_agrees is False:
        confidence *= MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER

    cot_crowding_flag, cot_crowding_note = _check_cot_crowding(aggregate_usd, cot_positioning)
    if cot_crowding_flag:
        confidence *= COT_CROWDING_CONFIDENCE_MULTIPLIER

    equity_risk_agrees, equity_risk_note = _check_equity_risk_sentiment(instrument_score, instrument, macro_backdrop)
    if equity_risk_agrees is False:
        confidence *= EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER

    oil_shock_flag, oil_shock_note = _check_oil_shock(macro_backdrop)
    if oil_shock_flag:
        confidence *= OIL_SHOCK_CONFIDENCE_MULTIPLIER
```

And add the new fields to the `ProbabilityResult(...)` construction at the end of `score_bundle()` (around line 859-875), alongside the existing `macro_backdrop_agrees=macro_backdrop_agrees, macro_backdrop_note=macro_backdrop_note,`:

```python
        cot_crowding_flag=cot_crowding_flag,
        cot_crowding_note=cot_crowding_note,
        equity_risk_agrees=equity_risk_agrees,
        equity_risk_note=equity_risk_note,
        oil_shock_flag=oil_shock_flag,
        oil_shock_note=oil_shock_note,
```

Note the early-return branch for `not all_contributions` (around line 801-813) does NOT get these new checks — it already returns a placeholder `ProbabilityResult` with no real `aggregate_usd_sentiment` to check anything against, matching how the existing `macro_backdrop_agrees`/`macro_backdrop_note` fields are also absent from that branch today (they fall back to their dataclass defaults of `None`). Do not add the new fields there.

- [ ] **Step 5: Run tests to verify they pass, and run the whole file**

Run: `python -m pytest tests/test_probability_engine.py -v`
Expected: all PASS, including every new test. The one known pre-existing unrelated failure (`test_redundancy_discount_works_across_sentiment_tiers_not_just_lexicon`, a FinBERT environment-dependent test) may still be present — that's expected and unrelated to this task.

- [ ] **Step 6: Commit**

```bash
git add scoring/probability_engine.py tests/test_probability_engine.py
git commit -m "feat: wire COT crowding, equity risk-sentiment, and oil shock checks into score_bundle"
```

---

### Task 5: Wire COT fetch into `scoring/backtest_accumulator.py`

**Files:**
- Modify: `scoring/backtest_accumulator.py`
- Test: `tests/test_backtest_accumulator.py`

**Interfaces:**
- Consumes: `data_layer.cot_positioning.get_cot_positioning_read()` (Task 3), `score_bundle(..., cot_positioning=...)` (Task 4).
- Produces: nothing new for later tasks — this is the final wiring point. Equity risk-sentiment and oil-shock need NO changes here: they ride on the same `macro_backdrop` object `run_accumulator_cycle()` already fetches once per cycle and passes to `score_and_record_event()` → `score_bundle()` today.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_backtest_accumulator.py`. First read the existing tests for the `macro_backdrop`-once-per-cycle behavior in that file (search for `macro_backdrop_fetched` or `get_macro_backdrop_read` in the test file) — reuse the exact same mocking/fixture pattern. Add these tests alongside them:

```python
def test_run_accumulator_cycle_fetches_cot_once_per_cycle_not_per_event():
    print("=== run_accumulator_cycle: cot_positioning is fetched ONCE per cycle, reused across every active event, same as macro_backdrop ===")
    event_a = EconomicEvent(title="CPI m/m", country="USD", impact="High", event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ), forecast="0.3%", previous="0.3%")
    event_b = EconomicEvent(title="PPI m/m", country="USD", impact="High", event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ), forecast="0.2%", previous="0.2%")
    with patch.object(accumulator, "fetch_calendar", return_value=[event_a, event_b]), \
         patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
         patch.object(accumulator, "events_in_pre_window", return_value=[event_a, event_b]), \
         patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
         patch.object(accumulator, "get_macro_backdrop_read", return_value=None), \
         patch.object(accumulator, "get_cot_positioning_read", return_value=None) as mock_cot, \
         patch.object(accumulator, "score_and_record_event") as mock_score, \
         patch.object(accumulator, "get_connection"):
        accumulator.run_accumulator_cycle(["XAUUSD"])

    assert mock_cot.call_count == 1  # fetched once, not once per event
    # Both calls to score_and_record_event received the SAME cot_positioning value (None here, but the point is it's the one shared fetch, not a fresh one per event)
    assert mock_score.call_count == 2
    print("PASS\n")


def test_score_and_record_event_passes_cot_positioning_through_to_score_bundle():
    print("=== score_and_record_event: cot_positioning is threaded through to score_bundle() unchanged ===")
    event = EconomicEvent(title="CPI m/m", country="USD", impact="High", event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ), forecast="0.3%", previous="0.3%")
    sentinel_cot = CotPositioningRead(net_leveraged_funds_position=100, percentile_in_trailing_window=50.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    with patch.object(accumulator, "build_event_news_bundle", return_value=_bundle(event, [])), \
         patch.object(accumulator, "record_check"), \
         patch.object(accumulator, "find_precursor_events", return_value=[]), \
         patch.object(accumulator, "score_print_direction", return_value=None), \
         patch.object(accumulator, "_read_trend_signal", return_value=None), \
         patch.object(accumulator, "_read_kalshi_signal", return_value=(None, None)), \
         patch.object(accumulator, "get_latest_prediction", return_value=None), \
         patch.object(accumulator, "score_bundle") as mock_score_bundle, \
         patch.object(accumulator, "_is_material_change", return_value=False):
        accumulator.score_and_record_event(
            conn=MagicMock(), event=event, all_events=[event], instruments=["XAUUSD"],
            sources=[], cot_positioning=sentinel_cot,
        )

    assert mock_score_bundle.call_args.kwargs["cot_positioning"] is sentinel_cot
    print("PASS\n")
```

Check the top of `tests/test_backtest_accumulator.py` for its existing imports and helpers (`_bundle`, `MagicMock`, `EconomicEvent`, `UTC_TZ`, `accumulator` module alias) and reuse them — do not reinvent. Add `CotPositioningRead` to the imports (from `data_layer.cot_positioning`). Add both new test names to the file's `if __name__ == "__main__":` block if one exists in this file (check first — some test files in this repo use pytest discovery only).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_backtest_accumulator.py -k "cot" -v`
Expected: FAIL — `AttributeError: module 'scoring.backtest_accumulator' has no attribute 'get_cot_positioning_read'` (first test) and a `TypeError: score_and_record_event() got an unexpected keyword argument 'cot_positioning'` (second test).

- [ ] **Step 3: Wire the fetch and the parameter through**

In `scoring/backtest_accumulator.py`, add the import near the existing `from data_layer.macro_backdrop import get_macro_backdrop_read`:

```python
from data_layer.cot_positioning import get_cot_positioning_read
```

Update `score_and_record_event()`'s signature and docstring (around line 384-420):

```python
def score_and_record_event(
    conn,
    event: EconomicEvent,
    all_events: list[EconomicEvent],
    instruments: list[str],
    sources,
    now: Optional[dt.datetime] = None,
    macro_backdrop=None,  # MacroBackdropRead | None — duck-typed, see scoring/probability_engine.py's _check_macro_backdrop()/_check_equity_risk_sentiment()/_check_oil_shock()
    cot_positioning=None,  # CotPositioningRead | None — duck-typed, see scoring/probability_engine.py's _check_cot_crowding()
) -> dict:
```

Add one sentence to the docstring's existing `macro_backdrop` paragraph (do not rewrite the whole docstring, just extend it):

```
    `cot_positioning` is passed in for the same reason as `macro_backdrop`
    — it's a USD-level positioning read (weekly CFTC data, not
    event-specific), so a caller scoring multiple events in one cycle
    should fetch it once, not once per event.
```

Update the `score_bundle(...)` call inside the `for instrument in instruments:` loop (around line 467-473) to pass it through:

```python
            result = score_bundle(
                bundle, instrument, precursor_events=precursors,
                print_call=print_call, trend_signal=trend_signal,
                kalshi_read=kalshi_read, kalshi_direction_override=kalshi_direction_value,
                macro_backdrop=macro_backdrop,
                cot_positioning=cot_positioning,
                current_direction=latest.direction if latest is not None else None,
            )
```

Update `run_accumulator_cycle()` (around line 527-547) to fetch it once per cycle, same pattern as `macro_backdrop`:

```python
        sources = None  # lazily built, only if at least one event is actually active this cycle
        macro_backdrop = None
        macro_backdrop_fetched = False
        cot_positioning = None
        cot_positioning_fetched = False
        for event in active:
            if sources is None:
                sources = build_all_preview_sources()
            if not macro_backdrop_fetched:
                macro_backdrop = get_macro_backdrop_read()
                macro_backdrop_fetched = True
            # Same once-per-cycle reasoning as macro_backdrop above — COT
            # is weekly data, not event-specific.
            if not cot_positioning_fetched:
                cot_positioning = get_cot_positioning_read()
                cot_positioning_fetched = True
            score_and_record_event(
                conn, event, all_events, instruments, sources, now=now,
                macro_backdrop=macro_backdrop, cot_positioning=cot_positioning,
            )
```

- [ ] **Step 4: Run tests to verify they pass, and run the whole file**

Run: `python -m pytest tests/test_backtest_accumulator.py -v`
Expected: all PASS, including both new tests.

- [ ] **Step 5: Commit**

```bash
git add scoring/backtest_accumulator.py tests/test_backtest_accumulator.py
git commit -m "feat: fetch and thread COT positioning through the accumulator's scoring cycle"
```

---

### Task 6: Whole-batch verification

**Files:** none modified — this task runs the full suite and confirms the core invariant, no code changes.

- [ ] **Step 1: Run the entire test suite**

Run: `python -m pytest tests/ -v`
Expected: all PASS except the one known pre-existing, unrelated, environment-dependent failure (`tests/test_probability_engine.py::test_redundancy_discount_works_across_sentiment_tiers_not_just_lexicon`, a FinBERT tier-scoring test that depends on the test environment's torch/transformers install). If any OTHER test fails, stop and investigate before proceeding — do not treat a new failure as pre-existing.

- [ ] **Step 2: Confirm the essence-only dashboard pipeline is untouched**

Run: `grep -rn "score_bundle\|cot_positioning\|_check_cot_crowding\|_check_equity_risk_sentiment\|_check_oil_shock" webapp/scoring_service.py`
Expected: no matches — confirms this plan never touched the essence-only pipeline (`webapp/scoring_service.py` computes its own calendar-math-based score, entirely separate from `score_bundle()`), exactly as the plan's Architecture section states.

- [ ] **Step 3: Confirm the core invariant one more time, end to end**

Run: `python -m pytest tests/test_probability_engine.py -k "only_touches_confidence or defaults_to_no_effect" -v`
Expected: PASS — this re-runs the two most important tests from Task 4 (the ones proving direction/probability are never touched by any new signal) as a final, explicit gate before calling this batch done.

## Self-Review Notes

- **Spec coverage:** COT crowding dampener (Tasks 1, 3, 4), equity risk-sentiment leg instrument-scoped to `risk_sentiment` (Task 2, 4), oil shock flag with both confidence dampening and a visible note (Task 2, 4), accumulator wiring (Task 5), the `get_macro_backdrop_read()` None-check update the spec's Architecture section called out (Task 2 Step 4). N2/N5/the symbol-picker feature are explicitly out of scope per the spec and are not present in any task, correctly.
- **Placeholder scan:** none found — every step has real code, real test bodies, real commands. The one open external-verification step (Task 2 Step 3, live-checking the FRED `SP500` series) is a genuine verification gate this codebase's own established discipline requires, not a placeholder — it has a concrete command and a concrete expected result.
- **Type consistency:** `CotPositioningRead`/`.is_crowded` (Task 3) matches its usage in `_check_cot_crowding()` (Task 4) exactly. `MacroBackdropRead`'s new fields (Task 2: `equity_index_trend_pct`, `oil_daily_change_pct`) match their usage in `_check_equity_risk_sentiment()`/`_check_oil_shock()` (Task 4) exactly. `score_bundle()`'s new `cot_positioning` parameter (Task 4) matches `score_and_record_event()`'s new parameter and its call-site (Task 5) exactly. `ProbabilityResult`'s six new fields (Task 4) are all given explicit defaults, so no existing construction site (e.g. the early-return branch) breaks.
