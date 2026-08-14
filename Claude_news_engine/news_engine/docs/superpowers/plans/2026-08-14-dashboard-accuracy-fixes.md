# Dashboard Accuracy Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three small, related dashboard-accuracy fixes surfaced by live use today: (1) Trend Streak's raw "higher/lower" label translated into a tradeable BUY/SELL-style lean, (2) a curated allowlist of Medium-impact titles genuinely worth accumulator (article-based) coverage, (3) an agent-run enrichment script that fills in real, cited actuals when Forex Factory's feed leaves them blank past a grace period.

**Architecture:** (1) and (2) are small, targeted backend+frontend changes reusing existing instrument-mapping and filtering functions. (3) is a new standalone script — not a live-service feature, since WebSearch is only callable by an agent session, not by the running Python process — mirroring `scripts/confirm_backtest_outcomes.py`'s "list stale items, agent/human supplies real researched values, script writes them" pattern.

**Tech Stack:** Python 3.14, Flask, vanilla JS, SQLite. No new dependencies.

## Global Constraints

- No changes to `scoring/probability_engine.py`'s core weighted-aggregate math in any task.
- The actuals-fallback script never fabricates a value — every write requires a real, cited source, same "real data or absent" standard as the historical backfill.
- A web-fallback actual is marked with a distinct `source` value (`'live_web_fallback'`), never conflated with `'live'` (FF-sourced) or `'seeded'` (pre-live-start backfill) — this project's History tab and any future analysis must be able to tell all three apart.
- The Medium-title allowlist only affects `scoring/backtest_accumulator.py`'s event selection — `webapp/scheduler.py`'s existing Medium+ essence-only coverage is untouched, and `filter_relevant_events()`'s default behavior for every other caller is unchanged.

---

### Task 1: Trend Streak instrument-relative lean

**Files:**
- Modify: `webapp/app.py`
- Modify: `webapp/static/app.js`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `config.settings.EVENT_SURPRISE_DIRECTION`, `config.settings.INSTRUMENTS`, `scoring.probability_engine._map_to_instrument_score`-equivalent logic (reused, not imported directly since that's a private function — reimplement the same three-branch mapping inline or extract a shared helper, your call, see Step 3).
- Produces: `/api/predictions`'s `trend_signal` dict gains a new key, `instrument_lean`: `'bullish' | 'bearish' | 'neutral' | None`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_webapp_app.py`:

```python
def test_trend_signal_includes_instrument_relative_lean():
    print("=== /api/predictions: trend_signal gains instrument_lean, translating raw higher/lower into a BUY/SELL-style lean ===")
    # Seed enough confirmed event_history rows for CPI m/m (higher_bullish in
    # EVENT_SURPRISE_DIRECTION) so compute_trend_signal() returns a real
    # 'higher' streak — mirror this file's existing trend_signal test fixture
    # pattern (test_predictions_includes_trend_signal_and_kalshi_read_when_present).
    ...  # implementer: mirror existing fixture style exactly
    resp = client.get("/api/predictions")
    data = resp.get_json()
    event = next(e for e in data["predictions"][0]["events"] if e["event_title"] == "CPI m/m")
    assert event["trend_signal"]["direction"] == "higher"
    # CPI m/m is higher_bullish -> a 'higher' trend is USD-bullish -> XAUUSD (inverse) -> bearish for gold
    assert event["trend_signal"]["instrument_lean"] == "bearish"
    print("PASS\n")


def test_trend_signal_instrument_lean_none_for_unmapped_title():
    print("=== /api/predictions: instrument_lean is None (not fabricated) when the event title has no EVENT_SURPRISE_DIRECTION entry ===")
    ...  # implementer: an event with a real trend_signal but a title not in EVENT_SURPRISE_DIRECTION
    resp = client.get("/api/predictions")
    data = resp.get_json()
    event = ...  # find the relevant event
    assert event["trend_signal"]["instrument_lean"] is None
    print("PASS\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_app.py`
Expected: `KeyError: 'instrument_lean'`.

- [ ] **Step 3: Implement the mapping**

Read `webapp/app.py`'s current `trend_signal` construction (added by an earlier plan — search for `trend_signal = {"direction"`) and `scoring/probability_engine.py`'s `_map_to_instrument_score()` (confirm its exact current body — it maps `usd_sentiment: float` through `INSTRUMENTS[instrument]["usd_relationship"]`: `inverse` negates, `direct` passes through, `risk_sentiment` negates and dampens).

Add a small helper in `webapp/app.py` (or a shared location if you judge that cleaner — your call, but keep it out of `scoring/probability_engine.py`, which stays untouched per Global Constraints):

```python
def _trend_instrument_lean(event_title: str, trend_direction: str, instrument: str) -> Optional[str]:
    """
    Translates a trend streak's raw forecast-relative direction ('higher'/
    'lower') into a USD-bullish/bearish/neutral lean for THIS instrument —
    same EVENT_SURPRISE_DIRECTION + usd_relationship mapping score_bundle()
    uses internally, reimplemented here at display-only granularity (no
    score_bundle() call, no scoring-math change). Returns None — never
    fabricated — when event_title has no EVENT_SURPRISE_DIRECTION entry.
    """
    surprise_mapping = EVENT_SURPRISE_DIRECTION.get(event_title)
    if surprise_mapping is None:
        return None
    # surprise_mapping is 'higher_bullish' or 'higher_bearish' — the sign
    # this event's "higher than forecast" carries for USD.
    higher_is_usd_bullish = surprise_mapping == "higher_bullish"
    usd_bullish = higher_is_usd_bullish if trend_direction == "higher" else not higher_is_usd_bullish

    relationship = INSTRUMENTS[instrument]["usd_relationship"]
    if relationship == "inverse":
        instrument_bullish = not usd_bullish
    elif relationship == "direct":
        instrument_bullish = usd_bullish
    elif relationship == "risk_sentiment":
        instrument_bullish = not usd_bullish  # dovish/USD-bearish -> risk-on -> equity-bullish, same simplification score_bundle() uses
    else:
        return None
    return "bullish" if instrument_bullish else "bearish"
```

Add the import: `from config.settings import EVENT_SURPRISE_DIRECTION, INSTRUMENTS` (merge into whatever import block already exists — check first, `EVENT_SURPRISE_DIRECTION` may already be imported for the print-call logic).

In the `trend_signal` dict construction, add the new key:

```python
            trend_signal = None
            if trend is not None:
                trend_signal = {
                    "direction": trend.direction, "strength": trend.strength,
                    "instrument_lean": _trend_instrument_lean(event["title"], trend.direction, ticker),
                }
```

- [ ] **Step 4: Update the frontend**

In `webapp/static/app.js`'s `breakdownPanelHtml()` (and the pending-branch trend line added by the prior plan's final-review fix), render `instrument_lean` alongside the raw direction:

```javascript
    if (next.trend_signal) {
      const lean = next.trend_signal.instrument_lean;
      const leanLabel = lean ? ` — lean: <b>${lean === 'bullish' ? 'BUY' : 'SELL'}</b>` : '';
      rows.push(`<div>📈 Trend streak: ${next.trend_signal.direction} (strength ${next.trend_signal.strength.toFixed(2)})${leanLabel}</div>`);
    }
```

Apply the same pattern to `trendSignalHtml()` (the pending-branch renderer added in the final-review fix) — read its current body first, adjust consistently rather than guessing at line numbers.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python tests/test_webapp_app.py`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add webapp/app.py webapp/static/app.js tests/test_webapp_app.py
git commit -m "feat: translate Trend Streak's raw direction into a BUY/SELL instrument lean

Trend Streak previously showed only the raw forecast-relative
direction ('higher'/'lower') -- not translatable into a trade lean
without mentally applying EVENT_SURPRISE_DIRECTION and the
instrument's USD relationship, unlike every other signal on the card.
_trend_instrument_lean() reuses that same mapping (display-only, no
scoring-math change) to add instrument_lean ('bullish'/'bearish'/
None) to trend_signal. None when the event has no
EVENT_SURPRISE_DIRECTION entry -- absent, not guessed."
```

---

### Task 2: Curated Medium-title allowlist for accumulator coverage

**Files:**
- Modify: `config/settings.py`
- Modify: `data_layer/calendar_feed.py`
- Modify: `scoring/backtest_accumulator.py`
- Test: `tests/test_calendar_feed.py`, `tests/test_backtest_accumulator.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `config.settings.ACCUMULATOR_MEDIUM_ALLOWLIST: frozenset[str]`; `filter_relevant_events(events, countries=..., min_impact=..., extra_titles=frozenset())` gains a new optional param.

- [ ] **Step 1: Add the constant**

In `config/settings.py`, near `EVENT_SURPRISE_DIRECTION`:

```python
# Medium-impact USD titles genuinely worth accumulator (article-based)
# coverage despite Forex Factory's generic "Medium" tag — curated, not a
# blanket Medium+ threshold, to protect the accumulator's tuned signal
# budget from dilution. Grounded against the LIVE calendar's real impact
# tags (2026-08-14), not assumed: Unemployment Claims and Retail Sales
# m/m/Prelim UoM Consumer Sentiment were confirmed Medium (not High) on
# the actual feed. All three already have an EVENT_SURPRISE_DIRECTION
# entry. Excluded: Core Retail Sales m/m (redundant with Retail Sales
# m/m, no EVENT_SURPRISE_DIRECTION entry yet), Prelim UoM Inflation
# Expectations (no forecast field to compare against), any
# non-scheduled-print title (e.g. speeches).
ACCUMULATOR_MEDIUM_ALLOWLIST = frozenset({
    "Unemployment Claims",
    "Retail Sales m/m",
    "Prelim UoM Consumer Sentiment",
})
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_calendar_feed.py`:

```python
def test_filter_relevant_events_extra_titles_admits_medium_regardless_of_threshold():
    print("=== filter_relevant_events: extra_titles admits a specific Medium title even under the default High threshold ===")
    high_event = _fake_event(title="CPI m/m", impact="High")
    allowlisted_medium = _fake_event(title="Retail Sales m/m", impact="Medium")
    other_medium = _fake_event(title="Building Permits", impact="Medium")
    result = filter_relevant_events(
        [high_event, allowlisted_medium, other_medium],
        extra_titles=frozenset({"Retail Sales m/m"}),
    )
    titles = {e.title for e in result}
    assert titles == {"CPI m/m", "Retail Sales m/m"}
    print("PASS\n")


def test_filter_relevant_events_extra_titles_defaults_to_empty():
    print("=== filter_relevant_events: omitting extra_titles reproduces today's exact High-only default ===")
    high_event = _fake_event(title="CPI m/m", impact="High")
    medium_event = _fake_event(title="Retail Sales m/m", impact="Medium")
    result = filter_relevant_events([high_event, medium_event])
    assert {e.title for e in result} == {"CPI m/m"}
    print("PASS\n")
```

(Implementer: check this test file's existing `_fake_event()`-style helper — mirror its exact signature, don't invent a new one.)

Add to `tests/test_backtest_accumulator.py`:

```python
def test_accumulator_includes_allowlisted_medium_events():
    print("=== accumulator: run_accumulator_cycle() includes a Medium-impact event on the curated allowlist ===")
    ...  # implementer: mock fetch_calendar to return a mix of High and
         # allowlisted-Medium events, assert the Medium one is processed
         # (appears in the cycle's returned events / triggers score_bundle),
         # mirroring this file's existing fixture style.
    print("PASS\n")


def test_accumulator_excludes_non_allowlisted_medium_events():
    print("=== accumulator: a Medium event NOT on the allowlist is still excluded ===")
    ...
    print("PASS\n")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python tests/test_calendar_feed.py` and `python tests/test_backtest_accumulator.py`
Expected: `TypeError: filter_relevant_events() got an unexpected keyword argument 'extra_titles'`.

- [ ] **Step 4: Implement**

In `data_layer/calendar_feed.py`'s `filter_relevant_events()` (read the current body first — shown in this plan's research as lines 240-255ish, verify against the actual current file):

```python
def filter_relevant_events(
    events: list[EconomicEvent],
    countries: tuple[str, ...] = ("USD",),
    min_impact: str = "High",
    extra_titles: frozenset[str] = frozenset(),
) -> list[EconomicEvent]:
    """
    Narrow the full calendar down to the events that actually matter for
    gold / US30 directional analysis — high-impact USD releases by default
    (NFP, CPI, FOMC, PCE, ISM, retail sales, etc.), plus any event whose
    exact title is in extra_titles regardless of its impact tier (a
    curated allowlist, e.g. config.settings.ACCUMULATOR_MEDIUM_ALLOWLIST —
    never a blanket lower threshold, which would dilute callers that rely
    on this function's default High-only behavior).
    """
    impact_rank = {"Low": 1, "Medium": 2, "High": 3}
    min_rank = impact_rank.get(min_impact, 3)

    return [
        e for e in events
        if e.country in countries and (impact_rank.get(e.impact, 0) >= min_rank or e.title in extra_titles)
    ]
```

In `scoring/backtest_accumulator.py:304` (verify the actual current line — this plan's research found it at that line, may have shifted), change:

```python
        events = filter_relevant_events(all_events)
```

to:

```python
        events = filter_relevant_events(all_events, extra_titles=ACCUMULATOR_MEDIUM_ALLOWLIST)
```

Add `ACCUMULATOR_MEDIUM_ALLOWLIST` to `scoring/backtest_accumulator.py`'s existing `from config.settings import (...)` block.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python tests/test_calendar_feed.py`, `python tests/test_backtest_accumulator.py`
Expected: all PASS, including existing tests unchanged (the new param defaults to `frozenset()`, reproducing today's exact behavior for every other caller — `data_layer/calendar_feed.py`'s own `__main__` demo block, `webapp/scheduler.py`'s `min_impact="Medium"` call, etc.).

- [ ] **Step 6: Commit**

```bash
git add config/settings.py data_layer/calendar_feed.py scoring/backtest_accumulator.py tests/test_calendar_feed.py tests/test_backtest_accumulator.py
git commit -m "feat: extend accumulator coverage to a curated Medium-impact allowlist

filter_relevant_events() gains an extra_titles param (defaults to
empty, every existing caller unaffected) -- events matching an exact
title pass regardless of impact tier, alongside the normal threshold.
scoring/backtest_accumulator.py uses this with a new
ACCUMULATOR_MEDIUM_ALLOWLIST (Unemployment Claims, Retail Sales m/m,
Prelim UoM Consumer Sentiment) -- grounded against the live calendar's
real impact tags, not a blanket Medium+ threshold that would dilute
the accumulator's tuned signal budget."
```

---

### Task 3: Agent-run actuals-fallback enrichment script

**Files:**
- Create: `scripts/fill_missing_actuals.py`
- Modify: `webapp/store.py`
- Modify: `webapp/static/app.js` (History tab badge — extend for the new source value)
- Test: `tests/test_fill_missing_actuals.py`, `tests/test_webapp_store.py`

**Interfaces:**
- Consumes: `webapp.store.upsert_event_history()`'s existing `source` param (already supports arbitrary string values — no schema change needed, the column has no CHECK constraint).
- Produces: `webapp.store.get_events_with_stale_missing_actual(conn, now, grace_period_hours) -> list[EventHistoryRow]`; `scripts/fill_missing_actuals.py`'s `run(facts, conn, now=None) -> FillReport`, where `facts` is a list of `(event_title, event_time_utc, actual, source_note)` tuples an agent session supplies after researching via WebSearch — mirrors `data_layer/historical_events.py`'s `HistoricalEventFact` shape but scoped to just the `actual` field (forecast/previous are already known from the live feed; only `actual` is missing).

- [ ] **Step 1: Write the failing tests for the store query**

Add to `tests/test_webapp_store.py`:

```python
def test_get_events_with_stale_missing_actual_respects_grace_period():
    print("=== webapp/store: get_events_with_stale_missing_actual only returns events past the grace period with actual still None ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)

        recent_event = _fake_event(title="CPI m/m", event_time_utc=now - dt.timedelta(hours=2))  # too recent
        stale_event = _fake_event(title="PPI m/m", event_time_utc=now - dt.timedelta(hours=48))  # past grace period
        resolved_event = _fake_event(title="Retail Sales m/m", event_time_utc=now - dt.timedelta(hours=48))
        resolved_event.actual = "0.3%"

        store.upsert_event_history(conn, recent_event, None, now)
        store.upsert_event_history(conn, stale_event, None, now)
        store.upsert_event_history(conn, resolved_event, "higher_bullish", now)

        stale = store.get_events_with_stale_missing_actual(conn, now, grace_period_hours=6)
        titles = {r.event_title for r in stale}
        assert titles == {"PPI m/m"}  # recent_event too fresh, resolved_event already has an actual
        conn.close()
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_webapp_store.py`
Expected: `AttributeError: module 'webapp.store' has no attribute 'get_events_with_stale_missing_actual'`.

- [ ] **Step 3: Implement the store query**

In `webapp/store.py`:

```python
def get_events_with_stale_missing_actual(
    conn: sqlite3.Connection, now: dt.datetime, grace_period_hours: float = 6.0,
) -> list[EventHistoryRow]:
    """
    Every event_history row whose actual is still NULL and whose
    event_time_utc is more than grace_period_hours in the past — a real
    candidate for the actuals-fallback enrichment pass. The grace period
    exists because Forex Factory's feed genuinely takes some time to
    publish an actual after release; searching too early would find
    nothing real and waste an agent's WebSearch budget.
    """
    cutoff = (now - dt.timedelta(hours=grace_period_hours)).isoformat()
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source "
        "FROM event_history WHERE actual IS NULL AND event_time_utc < ? "
        "ORDER BY event_time_utc DESC",
        (cutoff,),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_webapp_store.py`
Expected: all PASS.

- [ ] **Step 5: Write the failing tests for the enrichment script**

Create `tests/test_fill_missing_actuals.py`:

```python
"""
Tests for scripts/fill_missing_actuals.py — an agent-run enrichment pass,
not a live-service feature (WebSearch is only callable by an agent
session). `run()` takes agent-supplied, already-researched facts and
writes them; it never does any research itself.
"""
import sys
import os
import datetime as dt
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
import webapp.store as store
import scripts.fill_missing_actuals as fill


def _fake_event(title, event_time_utc):
    from data_layer.calendar_feed import EconomicEvent
    return EconomicEvent(title, "USD", "High", event_time_utc)


def test_run_writes_a_real_supplied_actual_with_web_fallback_source():
    print("=== fill_missing_actuals: run() writes an agent-supplied actual with source='live_web_fallback' ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)
        stale_event = _fake_event("PPI m/m", now - dt.timedelta(hours=48))
        store.upsert_event_history(conn, stale_event, None, now)

        facts = [("PPI m/m", now - dt.timedelta(hours=48), "0.3%", "BLS PPI report, bls.gov, released 2026-08-12")]
        report = fill.run(facts, conn, now=now)

        rows = store.get_event_history(conn, "PPI m/m")
        assert rows[0].actual == "0.3%"
        assert rows[0].source == "live_web_fallback"
        assert report.written == 1
        conn.close()
    print("PASS\n")


def test_run_skips_an_occurrence_that_already_has_a_real_actual():
    print("=== fill_missing_actuals: run() never overwrites an occurrence that already has a real actual ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)
        resolved_event = _fake_event("CPI m/m", now - dt.timedelta(hours=48))
        resolved_event.actual = "0.2%"
        store.upsert_event_history(conn, resolved_event, "higher_bullish", now, source="live")

        facts = [("CPI m/m", now - dt.timedelta(hours=48), "999%", "should never be written")]
        report = fill.run(facts, conn, now=now)

        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].actual == "0.2%"  # unchanged
        assert rows[0].source == "live"  # unchanged, never relabeled
        assert report.skipped == 1
        conn.close()
    print("PASS\n")


def test_run_skips_an_occurrence_with_no_matching_event_history_row():
    print("=== fill_missing_actuals: a fact for an occurrence never recorded in event_history at all is skipped, not inserted ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)
        facts = [("Nonexistent Event", now - dt.timedelta(hours=48), "1.0%", "should never be written")]
        report = fill.run(facts, conn, now=now)
        assert report.skipped == 1
        assert report.written == 0
        rows = store.get_event_history(conn, "Nonexistent Event")
        assert rows == []
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_run_writes_a_real_supplied_actual_with_web_fallback_source()
    test_run_skips_an_occurrence_that_already_has_a_real_actual()
    test_run_skips_an_occurrence_with_no_matching_event_history_row()
    print("All fill_missing_actuals tests passed.")
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `python tests/test_fill_missing_actuals.py`
Expected: `ModuleNotFoundError: No module named 'scripts.fill_missing_actuals'`.

- [ ] **Step 7: Implement `scripts/fill_missing_actuals.py`**

```python
"""
Agent-run enrichment pass: fills in real, cited `actual` values for
events Forex Factory's feed has left blank past a grace period.

This is NOT a live-service feature — WebSearch is only callable by an
agent session, not by webapp/scheduler.py's background loop. The
workflow is:
  1. An agent runs `python scripts/fill_missing_actuals.py --list` to
     see stale-missing-actual candidates (webapp.store's
     get_events_with_stale_missing_actual()).
  2. The agent researches each one via WebSearch, same citation
     standard as data_layer/historical_events.py's backfill facts —
     real data or absent, never guessed.
  3. The agent edits FACTS below (or calls run() directly, e.g. from an
     interactive Python session) with the researched (title,
     event_time_utc, actual, source_note) tuples, then runs the script
     for real (no --list) to write them.

Written rows get source='live_web_fallback' — distinct from 'live'
(Forex-Factory-sourced) and 'seeded' (pre-live-start historical
backfill), so this project can always tell which of the three
supplied a given actual.
"""
from __future__ import annotations

import sys
import os
import datetime as dt
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import classify_surprise, EconomicEvent
from config.settings import EVENT_SURPRISE_DIRECTION
import webapp.store as store

# Populated by an agent session after WebSearch research — see module
# docstring. Each tuple: (event_title, event_time_utc, actual, source_note).
FACTS: list[tuple[str, dt.datetime, str, str]] = []


@dataclass
class FillReport:
    written: int = 0
    skipped: int = 0
    skip_reasons: list[str] = field(default_factory=list)


def run(facts: list[tuple[str, dt.datetime, str, str]], conn, now: dt.datetime | None = None) -> FillReport:
    report = FillReport()
    now = now or dt.datetime.now(UTC_TZ)

    for title, event_time_utc, actual, source_note in facts:
        rows = conn.execute(
            "SELECT * FROM event_history WHERE event_title = ? AND event_time_utc = ?",
            (title, event_time_utc.isoformat()),
        ).fetchall()
        if not rows:
            report.skipped += 1
            report.skip_reasons.append(f"{title}@{event_time_utc.isoformat()}: no matching event_history row")
            continue
        existing = dict(rows[0])
        if existing["actual"] is not None:
            report.skipped += 1
            report.skip_reasons.append(f"{title}@{event_time_utc.isoformat()}: already has a real actual, not overwritten")
            continue

        event = EconomicEvent(title, "USD", "High", event_time_utc)
        event.forecast = existing["forecast"]
        event.previous = existing["previous"]
        event.actual = actual
        surprise_direction = classify_surprise(event)
        store.upsert_event_history(conn, event, surprise_direction, now, source="live_web_fallback")
        print(f"[fill_missing_actuals] wrote {title}@{event_time_utc.isoformat()}: actual={actual} ({source_note})")
        report.written += 1

    return report


if __name__ == "__main__":
    conn = store.get_connection()
    now = dt.datetime.now(UTC_TZ)

    if "--list" in sys.argv:
        stale = store.get_events_with_stale_missing_actual(conn, now)
        print(f"[fill_missing_actuals] {len(stale)} event(s) with a stale missing actual:")
        for r in stale:
            print(f"  {r.event_title} @ {r.event_time_utc} (forecast={r.forecast}, previous={r.previous})")
    elif not FACTS:
        print("[fill_missing_actuals] FACTS is empty — nothing to write. "
              "Run with --list to see candidates, research them via WebSearch, "
              "then populate FACTS and re-run without --list.")
    else:
        report = run(FACTS, conn, now=now)
        print(f"[fill_missing_actuals] written={report.written} skipped={report.skipped}")
        for reason in report.skip_reasons:
            print(f"[fill_missing_actuals] skipped: {reason}")

    conn.close()
```

**Note:** verify `classify_surprise()`'s real signature before trusting the `classify_surprise(event)` call above — an earlier plan's implementer found it takes exactly one argument (`event`), not two; confirm this is still current.

- [ ] **Step 8: Run tests to verify they pass**

Run: `python tests/test_fill_missing_actuals.py`
Expected: all 3 PASS.

- [ ] **Step 9: Extend the History tab badge for the new source value**

In `webapp/static/app.js`'s `renderHistoryTable()`, the existing badge logic checks `r.source === 'seeded'`. Extend it:

```javascript
    const sourceBadge = r.source === 'seeded' ? ' <span style="color:#888;font-size:11px;font-weight:normal">(seeded)</span>'
      : r.source === 'live_web_fallback' ? ' <span style="color:#888;font-size:11px;font-weight:normal">(web-sourced)</span>'
      : '';
```

- [ ] **Step 10: Run the full regression sweep**

```bash
python tests/test_webapp_store.py
python tests/test_fill_missing_actuals.py
python tests/test_webapp_app.py
python tests/test_webapp_history.py
```

Expected: all PASS.

- [ ] **Step 11: Commit**

```bash
git add scripts/fill_missing_actuals.py webapp/store.py webapp/static/app.js tests/test_fill_missing_actuals.py tests/test_webapp_store.py
git commit -m "feat: add agent-run actuals-fallback enrichment script

scripts/fill_missing_actuals.py -- not a live-service feature (WebSearch
is only callable by an agent session, not by webapp/scheduler.py's
background loop). --list surfaces event_history rows with a real,
stale (past a grace period) missing actual via the new
get_events_with_stale_missing_actual() query; an agent researches them
via WebSearch (same real-data-or-absent citation standard as the
historical backfill) and populates FACTS to write them.

Written rows get source='live_web_fallback', distinct from 'live'
(Forex-Factory-sourced) and 'seeded' (pre-live-start backfill) --
never overwrites an occurrence that already has a real actual, never
inserted for an occurrence with no matching event_history row at all.
History tab badge extended to show '(web-sourced)' for this source."
```

---

## Post-plan verification

- [ ] Run the full regression suite:

```bash
for f in tests/test_*.py; do echo "--- $f ---"; python "$f" 2>&1 | tail -6; done
```

- [ ] Restart `run_all.py` only if the Forex Factory rate limit has cleared (check for a fresh 429 before restarting — repeated restarts today already tripped this once; do not restart again if the feed is still throttling).
- [ ] Once live, verify: a card's "Why this call" panel shows a Trend Streak line with a BUY/SELL lean (not just raw higher/lower); confirm the accumulator now processes at least one of the three allowlisted Medium titles when one is on the calendar.
- [ ] The actuals-fallback script (`scripts/fill_missing_actuals.py --list`) is meant to be run periodically by an agent session, not automated — no further action needed here beyond confirming `--list` runs cleanly against the live DB.
