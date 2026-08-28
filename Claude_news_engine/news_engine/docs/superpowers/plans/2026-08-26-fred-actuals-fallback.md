# FRED Actuals Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Forex Factory's `actual` is missing or late for a tracked event, automatically fill it in from FRED — same day, no agent/human intervention needed — for the subset of tracked titles that are FRED-published percent-change price/level indices.

**Architecture:** A new read-only, fail-open `data_layer/fred_actuals.py` module (`get_actual_from_fred(event_title, event_time_utc) -> Optional[str]`) mirrors `data_layer/macro_backdrop.py`'s existing FRED-fetch contract. `webapp/scheduler.py`'s `run_scoring_cycle()` calls it once per already-passed event whose `actual` is still `None`, writing a result through the existing `upsert_event_history(..., source="fred")` path — the same function `scripts/fill_missing_actuals.py` already uses, whose SQL-level `WHERE excluded.actual IS NOT NULL` guard already prevents ever overwriting a real value from any source.

**Tech Stack:** Python 3.14, `requests`, SQLite (`webapp/store.py`'s existing `event_history` table — no schema change), FRED's public `series/observations` endpoint (already-configured `FRED_API_KEY`).

**Spec:** `docs/superpowers/specs/2026-08-26-fred-actuals-fallback-design.md`

## Global Constraints

- Read-only, fail-open: `get_actual_from_fred()` never raises — missing API key, no series mapping, network/HTTP failure, missing/stale observation all return `None`.
- No new external dependency, no paid tier — reuses the already-configured `FRED_API_KEY` and the free `series/observations` endpoint.
- Never overwrite an existing real `actual` from any source (`live`, `seeded`, `live_web_fallback`, or a prior `fred` write) — enforced by `upsert_event_history()`'s existing SQL guard, not re-implemented here.
- Scope: only the 10 titles below (percent-change price/level indices verified live against the real FRED API on 2026-08-26). `Non-Farm Employment Change`, `Unemployment Rate`, `Unemployment Claims`, `Prelim GDP q/q`, `Prelim UoM Consumer Sentiment`, and `ADP Nonfarm Employment Change` are explicitly OUT of scope for this plan — they need a raw-level/absolute-change/annualized-rate `units` convention this plan's design doesn't cover; deferred to a follow-up plan.

---

### Task 1: `data_layer/fred_actuals.py` — FRED actual-value fetch, with tests

**Files:**
- Modify: `config/settings.py` (add `FRED_SERIES_ID_BY_EVENT_TITLE`)
- Create: `data_layer/fred_actuals.py`
- Create: `tests/test_fred_actuals.py`

**Interfaces:**
- Produces: `data_layer.fred_actuals.get_actual_from_fred(event_title: str, event_time_utc: dt.datetime) -> Optional[str]` — returns a formatted percentage string (e.g. `"0.2%"`) or `None`. Used by Task 2.
- Produces: `config.settings.FRED_SERIES_ID_BY_EVENT_TITLE: dict[str, tuple[str, str]]` — `event_title -> (fred_series_id, fred_units_param)`.

- [ ] **Step 1: Add the FRED series mapping to `config/settings.py`**

Add this block immediately after `FRED_RELEASE_ID_BY_EVENT_TITLE`'s closing `}` (currently around line 71, right before the `# --- Contextual sentiment scoring` section):

```python
# FRED series ID + `units` param for data_layer/fred_actuals.py's live
# actual-value fallback (missing/late Forex Factory `actual` — see
# docs/superpowers/specs/2026-08-26-fred-actuals-fallback-design.md).
# Every (series_id, units) pair below was live-verified 2026-08-26 against
# the real FRED API, same discipline FRED_RELEASE_ID_BY_EVENT_TITLE above
# already requires — not assumed from series naming conventions.
#
# `units="pch"` (percent change from the prior period) for m/m-framed
# titles, `units="pc1"` (percent change from a year ago) for y/y-framed
# titles — FRED computes the percent change server-side, so no manual
# level-to-percent math is needed here.
#
# Deliberately NOT included (need a different, not-yet-designed `units`/
# formatting convention — raw level, absolute change, or annualized rate,
# not a plain percent change): "Non-Farm Employment Change" (FF reports an
# absolute count, e.g. "150K"), "Unemployment Rate" (FF reports the raw
# level, e.g. "4.4%", not a change), "Unemployment Claims" (raw weekly
# count), "Prelim GDP q/q" (FF's figure is an ANNUALIZED rate — FRED's
# GDPC1 with units="pch" gives the raw quarterly change, ~1/4 the
# annualized figure, which would silently write a wrong value),
# "Prelim UoM Consumer Sentiment" (raw index level), "ADP Nonfarm
# Employment Change" (no FRED series has been confirmed to actually match
# ADP's own monthly report).
FRED_SERIES_ID_BY_EVENT_TITLE = {
    "CPI m/m": ("CPIAUCSL", "pch"),
    "CPI y/y": ("CPIAUCSL", "pc1"),
    "Core CPI m/m": ("CPILFESL", "pch"),
    "Core CPI y/y": ("CPILFESL", "pc1"),
    "PPI m/m": ("PPIFIS", "pch"),
    "Core PPI m/m": ("PPIFES", "pch"),
    "Core PCE Price Index m/m": ("PCEPILFE", "pch"),
    "Retail Sales m/m": ("RSAFS", "pch"),
    "Average Hourly Earnings m/m": ("CES0500000003", "pch"),
    "Import Prices m/m": ("IR", "pch"),
}
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_fred_actuals.py`:

```python
"""
Tests for data_layer/fred_actuals.py — no live network, requests.get is
mocked with synthetic FRED /series/observations responses, same pattern
as tests/test_macro_backdrop.py.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.fred_actuals as fred_actuals
from config.settings import UTC_TZ


def _fake_response(observations, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = {"observations": observations}
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def _obs(date_str, value, realtime_start):
    return {"date": date_str, "value": value, "realtime_start": realtime_start}


def test_get_actual_from_fred_returns_none_without_api_key():
    print("=== fred_actuals: get_actual_from_fred returns None (not a crash) when FRED_API_KEY is unset ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", ""):
        assert fred_actuals.get_actual_from_fred("CPI m/m", event_time) is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_for_untracked_title():
    print("=== fred_actuals: an event title with no FRED_SERIES_ID_BY_EVENT_TITLE entry returns None, no request made ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        result = fred_actuals.get_actual_from_fred("Some Untracked Title", event_time)
        assert result is None
        mock_get.assert_not_called()
    print("PASS\n")


def test_get_actual_from_fred_returns_formatted_value_when_fresh():
    print("=== fred_actuals: a fresh observation (realtime_start on/after the release date) returns a formatted percentage ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-07-01", "0.24552", "2026-08-26")])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result == "0.2%"
    print("PASS\n")


def test_get_actual_from_fred_uses_pc1_units_for_a_yy_title():
    print("=== fred_actuals: a y/y title requests units=pc1, not pch ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-07-01", "3.30386", "2026-08-26")])
        result = fred_actuals.get_actual_from_fred("CPI y/y", event_time)
        assert result == "3.3%"
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["series_id"] == "CPIAUCSL"
        assert kwargs["params"]["units"] == "pc1"
    print("PASS\n")


def test_get_actual_from_fred_returns_none_when_observation_is_stale():
    print("=== fred_actuals: an observation whose realtime_start predates the release is treated as not-yet-available ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-06-01", "0.14676", "2026-07-30")])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_on_missing_value_marker():
    print("=== fred_actuals: a FRED '.' (not-yet-published) observation returns None, not a fabricated 0.0 ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-07-01", ".", "2026-08-26")])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_on_request_failure():
    print("=== fred_actuals: a failed request fails open to None, never raises ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get", side_effect=Exception("network down")):
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_on_empty_observations():
    print("=== fred_actuals: no observations returned at all -> None, not an index-error crash ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_get_actual_from_fred_returns_none_without_api_key()
    test_get_actual_from_fred_returns_none_for_untracked_title()
    test_get_actual_from_fred_returns_formatted_value_when_fresh()
    test_get_actual_from_fred_uses_pc1_units_for_a_yy_title()
    test_get_actual_from_fred_returns_none_when_observation_is_stale()
    test_get_actual_from_fred_returns_none_on_missing_value_marker()
    test_get_actual_from_fred_returns_none_on_request_failure()
    test_get_actual_from_fred_returns_none_on_empty_observations()
    print("All fred_actuals tests passed.")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_fred_actuals.py -v`
Expected: `ModuleNotFoundError: No module named 'data_layer.fred_actuals'` (the module doesn't exist yet).

- [ ] **Step 4: Write the implementation**

Create `data_layer/fred_actuals.py`:

```python
"""
Live fallback for Forex Factory's `actual` field going missing or posting
hours late — confirmed recurring, not a one-off (docs/superpowers/specs/
2026-08-26-fred-actuals-fallback-design.md): Core PCE Price Index m/m and
Prelim GDP q/q both released 2026-08-26 12:30 UTC and still showed
actual=None in FF's feed 45+ minutes later.

get_actual_from_fred() pulls the real released value directly from FRED
for the subset of tracked titles that are FRED-published percent-change
price/level indices (config.settings.FRED_SERIES_ID_BY_EVENT_TITLE) —
live-verified 2026-08-26 to post SAME DAY as release (PCEPILFE's newest
point carried realtime_start == the release date), independently
corroborated against Investing.com's real print the same day.

READ-ONLY, same fail-open contract as every other data_layer module:
returns None on a missing key, an untracked title, a failed request, a
missing/stale observation, or FRED's "not yet published" marker ('.') —
never raises, never invents a value.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import requests

from config.settings import FRED_API_KEY, FRED_SERIES_ID_BY_EVENT_TITLE

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


def get_actual_from_fred(event_title: str, event_time_utc: dt.datetime) -> Optional[str]:
    """
    Returns a formatted percentage string (e.g. "0.2%") for event_title's
    most recent FRED-published value, or None if this title has no FRED
    mapping, no FRED_API_KEY is configured, the request fails, or the
    newest observation isn't fresh enough to plausibly BE this release
    (see the realtime_start freshness check below).
    """
    mapping = FRED_SERIES_ID_BY_EVENT_TITLE.get(event_title)
    if mapping is None:
        return None
    if not FRED_API_KEY:
        return None

    series_id, units = mapping
    try:
        resp = requests.get(
            f"{FRED_BASE_URL}/series/observations",
            params={
                "series_id": series_id, "file_type": "json", "api_key": FRED_API_KEY,
                "sort_order": "desc", "limit": 1, "units": units,
            },
            timeout=15,
        )
        resp.raise_for_status()
        observations = resp.json().get("observations", [])
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[fred_actuals] WARNING: fetch failed for {event_title!r} ({series_id}): {exc}")
        return None

    if not observations:
        return None

    newest = observations[0]
    # FRED marks a missing/not-yet-published observation with the literal
    # string "." — treat exactly like macro_backdrop.py already does.
    if newest.get("value") in (None, "."):
        return None

    # Freshness check, not period-matching (see module docstring / spec):
    # realtime_start is the date FRED itself published this observation —
    # if that's on or after the release date, this is a genuine fresh
    # figure for THIS release, not a stale prior-period value FRED simply
    # hasn't updated yet.
    try:
        realtime_start = dt.date.fromisoformat(newest["realtime_start"])
    except (KeyError, ValueError):
        return None
    if realtime_start < event_time_utc.date():
        return None

    try:
        value = float(newest["value"])
    except (TypeError, ValueError):
        return None

    return f"{value:.1f}%"
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_fred_actuals.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py data_layer/fred_actuals.py tests/test_fred_actuals.py
git commit -m "feat: FRED actual-value fallback for events FF hasn't posted yet

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Wire into `webapp/scheduler.py`'s live cycle

**Files:**
- Modify: `webapp/scheduler.py`
- Test: `tests/test_webapp_scheduler.py`

**Interfaces:**
- Consumes: `data_layer.fred_actuals.get_actual_from_fred(event_title: str, event_time_utc: dt.datetime) -> Optional[str]` (Task 1).
- Consumes: `webapp.store.upsert_event_history(conn, event, surprise_direction, now, source="live") -> None` (existing).
- Consumes: `data_layer.calendar_feed.classify_surprise(event) -> Optional[str]` (existing).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_scheduler.py`, right after `test_run_scoring_cycle_confirms_a_matching_macro_calendar_row` (and add `from unittest.mock import patch` is already imported at the top of this file — confirm, it is):

```python
def test_run_scoring_cycle_fills_actual_from_fred_when_ff_has_none():
    print("=== scheduler: run_scoring_cycle fills event_history.actual from FRED when FF's own actual is still None ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        past_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[past_event]), \
             patch.object(scheduler, "get_actual_from_fred", return_value="0.2%") as mock_fred, \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        mock_fred.assert_called_once_with("Core PCE Price Index m/m", past_event.event_time_utc)
        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "Core PCE Price Index m/m")
        assert len(rows) == 1
        assert rows[0].actual == "0.2%"
        assert rows[0].source == "fred"
        conn.close()
    print("PASS\n")


def test_run_scoring_cycle_does_not_call_fred_when_ff_already_has_actual():
    print("=== scheduler: run_scoring_cycle does not call FRED at all when FF's own actual is already present ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        resolved_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual="0.2%",
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[resolved_event]), \
             patch.object(scheduler, "get_actual_from_fred") as mock_fred, \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        mock_fred.assert_not_called()
    print("PASS\n")


def test_run_scoring_cycle_does_not_call_fred_for_a_future_event():
    print("=== scheduler: run_scoring_cycle does not call FRED for an event that hasn't released yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        future_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[future_event]), \
             patch.object(scheduler, "get_actual_from_fred") as mock_fred, \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        mock_fred.assert_not_called()
    print("PASS\n")


def test_run_scoring_cycle_does_not_write_when_fred_also_has_nothing():
    print("=== scheduler: run_scoring_cycle leaves the event pending when FRED returns None too ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        past_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[past_event]), \
             patch.object(scheduler, "get_actual_from_fred", return_value=None), \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "Core PCE Price Index m/m")
        assert len(rows) == 1
        assert rows[0].actual is None
        conn.close()
    print("PASS\n")
```

Add the corresponding calls to this file's `if __name__ == "__main__":` block, right after `test_run_scoring_cycle_confirms_a_matching_macro_calendar_row()`:

```python
    test_run_scoring_cycle_fills_actual_from_fred_when_ff_has_none()
    test_run_scoring_cycle_does_not_call_fred_when_ff_already_has_actual()
    test_run_scoring_cycle_does_not_call_fred_for_a_future_event()
    test_run_scoring_cycle_does_not_write_when_fred_also_has_nothing()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_webapp_scheduler.py -k "fred" -v`
Expected: `AttributeError: <module 'webapp.scheduler'> does not have the attribute 'get_actual_from_fred'` (not imported into scheduler.py yet).

- [ ] **Step 3: Write the implementation**

In `webapp/scheduler.py`, add the import (near the top, alongside the existing `from webapp.store import ...` block):

```python
from data_layer.fred_actuals import get_actual_from_fred
```

Then modify `run_scoring_cycle()`'s existing event_history loop. Find this exact block:

```python
    now_for_history = dt.datetime.now(dt.timezone.utc)
    for event in all_events:
        upsert_event_history(conn, event, classify_surprise(event), now_for_history)
        # "Micro lens" reconciliation (docs/macro-calendar-design-2026-08-16.md):
        # every real event FF's feed returns gets a chance to confirm a
        # macro_calendar row (scripts/refresh_macro_calendar.py's FRED-sourced
        # month-ahead estimate) with FF's real exact time. No-ops (returns
        # False) if no macro row exists for this occurrence — normal, not
        # every FF event necessarily has a prior FRED-sourced entry.
        confirm_macro_calendar_event(conn, event.title, event.event_time_utc, now_for_history)
```

Replace it with:

```python
    now_for_history = dt.datetime.now(dt.timezone.utc)
    for event in all_events:
        upsert_event_history(conn, event, classify_surprise(event), now_for_history)
        # "Micro lens" reconciliation (docs/macro-calendar-design-2026-08-16.md):
        # every real event FF's feed returns gets a chance to confirm a
        # macro_calendar row (scripts/refresh_macro_calendar.py's FRED-sourced
        # month-ahead estimate) with FF's real exact time. No-ops (returns
        # False) if no macro row exists for this occurrence — normal, not
        # every FF event necessarily has a prior FRED-sourced entry.
        confirm_macro_calendar_event(conn, event.title, event.event_time_utc, now_for_history)

        # FRED actuals fallback (docs/superpowers/specs/2026-08-26-fred-actuals-fallback-design.md):
        # FF's own `actual` is frequently missing or posts hours late,
        # confirmed recurring — only attempted for events that have
        # already released (a future event obviously has no actual yet
        # regardless of source) and only when FF hasn't supplied one
        # already. get_actual_from_fred() itself is a cheap no-op (a dict
        # lookup, no request) for any title outside its ~10-title
        # coverage, so this is safe to call unconditionally here.
        if event.actual is None and event.event_time_utc <= now_for_history:
            fred_actual = get_actual_from_fred(event.title, event.event_time_utc)
            if fred_actual is not None:
                fred_event = dataclasses.replace(event, actual=fred_actual)
                upsert_event_history(
                    conn, fred_event, classify_surprise(fred_event), now_for_history,
                    source="fred",
                )
```

Add `import dataclasses` to the top of `webapp/scheduler.py`, alongside the existing `import threading` / `import time` imports.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_webapp_scheduler.py -v`
Expected: all tests in this file PASS, including the 4 new ones.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: same pass count as before this plan, plus the 12 new tests (8 from Task 1, 4 from Task 2). One pre-existing, unrelated failure is expected and known: `tests/test_probability_engine.py::test_redundancy_discount_works_across_sentiment_tiers_not_just_lexicon` (an environment-order-dependent FinBERT test, confirmed failing on unmodified `master` too — not caused by this plan).

- [ ] **Step 6: Commit**

```bash
git add webapp/scheduler.py tests/test_webapp_scheduler.py
git commit -m "feat: wire FRED actuals fallback into the live scheduler cycle

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Manual verification (after both tasks)

Not a substitute for the tests above — a real-world sanity check once both tasks are merged and the live engine is restarted:

1. Restart the engine (`scripts/run_engine.bat` or equivalent).
2. Wait for the next `run_scoring_cycle()` to complete (check `webapp` process logs for `[scheduler]` lines, or poll `/api/calendar`).
3. For a tracked title in `FRED_SERIES_ID_BY_EVENT_TITLE` whose most recent occurrence has already released and whose FF `actual` is still `None` (check via `/api/calendar`), confirm `event_history.source` becomes `"fred"` and `actual` becomes a real, non-guessed percentage — cross-check the value against Investing.com or another independent source before trusting it, same discipline used throughout this session.
