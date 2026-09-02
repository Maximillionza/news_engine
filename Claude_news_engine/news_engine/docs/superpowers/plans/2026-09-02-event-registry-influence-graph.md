# Recurring Event Registry & Influence Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the engine a full ~55-title recurring-event registry with cadence-derived next-occurrence estimates, and replace the two hardcoded ADP→NFP/PPI→CPI precursor links with a hand-curated, tier-agnostic influence graph that also detects when 2+ of a target event's linked precursors disagree in direction.

**Architecture:** Three new pieces. (1) `EVENT_REGISTRY` — a static config dict in `config/settings.py` giving every recurring USD title an impact tier and an average cadence in months, consumed by a new `data_layer/event_registry.py` module's `get_approximate_next_occurrence()` (3-tier fallback: live FF snapshot → macro_calendar → cadence math). (2) `EVENT_INFLUENCE_LINKS` — a static config dict, also in `config/settings.py`, mapping each target title to its linked precursor titles (absorbing and replacing the old `PRECURSOR_EVENTS`). (3) A graph-driven precursor fetch (`get_precursor_events_for()`) and a new chain-conflict check (`_check_precursor_chain_conflict()`) in `scoring/probability_engine.py`, wired into `score_bundle()` exactly like the existing COT/equity-risk/oil-shock confidence dampeners, then threaded through `scoring/backtest_accumulator.py` in place of the old `find_precursor_events()` call.

**Tech Stack:** Python 3, sqlite3 (via `webapp/store.py`'s existing `event_history`/`calendar_snapshot`/`macro_calendar` tables), pytest-discoverable test functions run with a `print("PASS")` convention (matches this codebase's existing test style — see any file under `tests/`).

**Spec:** `docs/superpowers/specs/2026-09-02-event-registry-influence-graph-design.md`

## Global Constraints

- Never fabricate a date, a surprise score, or a direction — every "no answer" case returns `None` (or an empty list), matching this codebase's "real data or absent" discipline throughout.
- `EVENT_REGISTRY`/`EVENT_INFLUENCE_LINKS` title strings are best-effort standard Forex Factory naming, **not independently verified against a live feed capture** in this sandbox (same caveat `EVENT_SURPRISE_DIRECTION`'s own recent additions carry) — re-verify against the live feed once this runs where FF is reachable.
- Every new confidence-multiplier constant is an explicitly untuned starting value (matches `COT_CROWDING_CONFIDENCE_MULTIPLIER`/`OIL_SHOCK_CONFIDENCE_MULTIPLIER`/etc.'s own documented honesty) — flagged for later calibration against real backtest data, never treated as settled.
- Cadence-derived next-occurrence estimates are internal bookkeeping only — **do not** surface them on the Calendar tab UI or any webapp route in this plan.
- Approach B: `_build_precursor_contributions()`, the direction/probability weighted-average math, and the two existing links' proven numeric behavior must all be **byte-for-byte unchanged** after this plan lands — the single most important regression to protect against.
- `EVENT_INFLUENCE_LINKS`' per-link float weight (e.g. `0.90`, `0.40`) is **stored but not consumed by any scoring math in this plan** — it is authored metadata for a future refinement (matches the spec's "confluence extra weight deferred" decision). Do not wire it into `_build_precursor_contributions()` or anywhere else; a task below has an explicit test asserting this.

---

### Task 1: Event Registry config + cadence-derived next-occurrence resolution

**Files:**
- Modify: `config/settings.py` (add `EVENT_REGISTRY`, replacing the old `PRECURSOR_EVENTS` block at line 272-283)
- Create: `data_layer/event_registry.py`
- Test: `tests/test_event_registry.py` (new file)

**Interfaces:**
- Consumes: `webapp.store.get_calendar_snapshot(conn) -> Optional[CalendarSnapshot]` (`CalendarSnapshot.events: list[dict]`, each dict has `title`/`country`/`impact`/`event_time_utc` (ISO string)/`forecast`/`previous`/`actual`); `webapp.store.get_macro_calendar_events(conn, start_date: str, end_date: str) -> list[MacroCalendarRow]` (`MacroCalendarRow.event_title`, `.event_date` as `YYYY-MM-DD`); `webapp.store.get_event_history(conn, event_title: str, limit: int = 6) -> list[EventHistoryRow]` (`EventHistoryRow.event_time_utc` ISO string, `.actual: Optional[str]`, ordered DESC by `event_time_utc`).
- Produces: `config.settings.EVENT_REGISTRY: dict[str, dict]` (each value has `impact: str` and `avg_interval_months: float`), consumed by Task 2's link-validation test and by `data_layer.event_registry.get_approximate_next_occurrence(title: str, conn, now: Optional[dt.date] = None) -> Optional[dt.date]`.

- [ ] **Step 1: Replace `PRECURSOR_EVENTS` with `EVENT_REGISTRY` in `config/settings.py`**

Delete the existing `PRECURSOR_EVENTS` block (lines 272-283) and replace it with:

```python
# --- Recurring event registry ---
# Every recurring USD release worth tracking (docs/fundamental-analysis-
# monthly-event-map-2026-09-02.md's ~55-event map), regardless of impact
# tier or whether it's scoreable today — a title with no
# EVENT_SURPRISE_DIRECTION entry yet is still registered here, its
# EVENT_INFLUENCE_LINKS links just stay dormant (can't resolve a
# surprise) until that config gap is closed separately. Title strings
# are best-effort standard Forex Factory naming, NOT independently
# verified against a live feed capture in this sandbox (same caveat
# EVENT_SURPRISE_DIRECTION's own recent additions carry) — re-verify
# each new title against the live feed (or the already-confirmed
# EVENT_SURPRISE_DIRECTION/ACCUMULATOR_MEDIUM_ALLOWLIST dicts, for
# titles already confirmed there) once this runs where FF is reachable.
#
# avg_interval_months is a real average cadence, not a coarse monthly/
# quarterly/annual label — FOMC is real-world ~8 meetings/year (~1.6
# months apart), not literally quarterly, so a coarse label would
# misapproximate it. CFTC COT positioning (weekly, but not a scheduled
# FF "release") is deliberately NOT registered here — it has its own
# separate data_layer.cot_positioning mechanism, unrelated to this
# calendar-title registry.
EVENT_REGISTRY: dict[str, dict] = {
    # --- Labor market ---
    "Non-Farm Employment Change": {"impact": "High", "avg_interval_months": 1.0},
    "Unemployment Rate": {"impact": "High", "avg_interval_months": 1.0},
    "Average Hourly Earnings m/m": {"impact": "High", "avg_interval_months": 1.0},
    "Average Hourly Earnings y/y": {"impact": "Medium", "avg_interval_months": 1.0},
    "Participation Rate": {"impact": "Low", "avg_interval_months": 1.0},
    "ADP Nonfarm Employment Change": {"impact": "Medium", "avg_interval_months": 1.0},
    "JOLTS Job Openings": {"impact": "Medium", "avg_interval_months": 1.0},
    "JOLTS Quits Rate": {"impact": "Low", "avg_interval_months": 1.0},
    "Challenger Job Cuts": {"impact": "Low", "avg_interval_months": 1.0},
    "Unemployment Claims": {"impact": "Medium", "avg_interval_months": 0.23},
    "Continuing Claims": {"impact": "Low", "avg_interval_months": 0.23},
    "Nonfarm Productivity q/q": {"impact": "Medium", "avg_interval_months": 3.0},
    "Unit Labor Costs q/q": {"impact": "Medium", "avg_interval_months": 3.0},
    # --- Inflation ---
    "CPI m/m": {"impact": "High", "avg_interval_months": 1.0},
    "CPI y/y": {"impact": "High", "avg_interval_months": 1.0},
    "Core CPI m/m": {"impact": "High", "avg_interval_months": 1.0},
    "Core CPI y/y": {"impact": "High", "avg_interval_months": 1.0},
    "PPI m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "Core PPI m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "Import Prices m/m": {"impact": "Low", "avg_interval_months": 1.0},
    "Export Prices m/m": {"impact": "Low", "avg_interval_months": 1.0},
    "Core PCE Price Index m/m": {"impact": "High", "avg_interval_months": 1.0},
    "Core PCE Price Index y/y": {"impact": "High", "avg_interval_months": 1.0},
    "Prelim UoM Inflation Expectations": {"impact": "Low", "avg_interval_months": 1.0},
    # --- Growth & output ---
    "Prelim GDP q/q": {"impact": "High", "avg_interval_months": 3.0},
    "Final GDP q/q": {"impact": "Medium", "avg_interval_months": 3.0},
    "GDP Price Index q/q": {"impact": "Low", "avg_interval_months": 3.0},
    "ISM Manufacturing PMI": {"impact": "High", "avg_interval_months": 1.0},
    "ISM Manufacturing Prices": {"impact": "Medium", "avg_interval_months": 1.0},
    "ISM Manufacturing Employment": {"impact": "Low", "avg_interval_months": 1.0},
    "ISM Services PMI": {"impact": "High", "avg_interval_months": 1.0},
    "ISM Services Prices": {"impact": "Low", "avg_interval_months": 1.0},
    "S&P Global Manufacturing PMI Flash": {"impact": "Low", "avg_interval_months": 1.0},
    "S&P Global Manufacturing PMI": {"impact": "Low", "avg_interval_months": 1.0},
    "S&P Global Services PMI Flash": {"impact": "Low", "avg_interval_months": 1.0},
    "S&P Global Services PMI": {"impact": "Low", "avg_interval_months": 1.0},
    "Industrial Production m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "Capacity Utilization Rate": {"impact": "Low", "avg_interval_months": 1.0},
    "Durable Goods Orders m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "Core Durable Goods Orders m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "Factory Orders m/m": {"impact": "Low", "avg_interval_months": 1.0},
    # --- Consumer & housing ---
    "Retail Sales m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "Core Retail Sales m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "Personal Income m/m": {"impact": "Low", "avg_interval_months": 1.0},
    "Personal Spending m/m": {"impact": "Medium", "avg_interval_months": 1.0},
    "CB Consumer Confidence": {"impact": "Medium", "avg_interval_months": 1.0},
    "Prelim UoM Consumer Sentiment": {"impact": "Medium", "avg_interval_months": 1.0},
    "Final UoM Consumer Sentiment": {"impact": "Low", "avg_interval_months": 1.0},
    "Housing Starts": {"impact": "Low", "avg_interval_months": 1.0},
    "Building Permits": {"impact": "Low", "avg_interval_months": 1.0},
    "Existing Home Sales": {"impact": "Low", "avg_interval_months": 1.0},
    "New Home Sales": {"impact": "Low", "avg_interval_months": 1.0},
    "Pending Home Sales m/m": {"impact": "Low", "avg_interval_months": 1.0},
    "S&P/CS Composite-20 HPI y/y": {"impact": "Low", "avg_interval_months": 1.0},
    # --- Trade, inventories & policy ---
    "Trade Balance": {"impact": "Low", "avg_interval_months": 1.0},
    "Wholesale Inventories m/m": {"impact": "Low", "avg_interval_months": 1.0},
    "Business Inventories m/m": {"impact": "Low", "avg_interval_months": 1.0},
    "FOMC Statement": {"impact": "High", "avg_interval_months": 1.6},  # real-world ~8 meetings/year, NOT literally quarterly
    "FOMC Press Conference": {"impact": "High", "avg_interval_months": 1.6},
    "FOMC Meeting Minutes": {"impact": "Medium", "avg_interval_months": 1.6},  # same meeting cadence, published ~3 weeks later each time
    "Federal Funds Rate": {"impact": "High", "avg_interval_months": 1.6},
}
```

Note: the old module docstring comment block above `PRECURSOR_EVENTS` ("Leading-indicator precursor events") is deleted along with it — its content is superseded by `EVENT_INFLUENCE_LINKS`' own comment in Task 2.

- [ ] **Step 2: Write the failing tests for `EVENT_REGISTRY`'s structure**

Create `tests/test_event_registry.py`:

```python
"""
Tests for config.settings.EVENT_REGISTRY and
data_layer/event_registry.py's get_approximate_next_occurrence().
"""
import datetime as dt
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import EVENT_REGISTRY, UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_registry import get_approximate_next_occurrence
import webapp.store as store


def test_event_registry_every_entry_has_impact_and_interval():
    print("=== EVENT_REGISTRY: every entry has a valid impact tier and a positive avg_interval_months ===")
    for title, entry in EVENT_REGISTRY.items():
        assert entry["impact"] in ("Low", "Medium", "High"), f"{title!r} has an invalid impact tier: {entry['impact']!r}"
        assert entry["avg_interval_months"] > 0, f"{title!r} has a non-positive avg_interval_months"
    print("PASS\n")


def test_event_registry_covers_every_event_surprise_direction_title():
    print("=== EVENT_REGISTRY: every EVENT_SURPRISE_DIRECTION title is also registered ===")
    from config.settings import EVENT_SURPRISE_DIRECTION
    missing = [t for t in EVENT_SURPRISE_DIRECTION if t not in EVENT_REGISTRY]
    assert not missing, f"titles scored today but missing from EVENT_REGISTRY: {missing}"
    print("PASS\n")


if __name__ == "__main__":
    test_event_registry_every_entry_has_impact_and_interval()
    test_event_registry_covers_every_event_surprise_direction_title()
```

- [ ] **Step 3: Run the new tests to verify they pass against the registry alone**

Run: `python -m pytest tests/test_event_registry.py -v`
Expected: both tests PASS (the registry above already satisfies them — this step exists to catch a typo before building on top of it).

- [ ] **Step 4: Write `data_layer/event_registry.py`**

```python
"""
Cadence-derived next-occurrence resolution for the recurring event
registry (config.settings.EVENT_REGISTRY). Internal bookkeeping only —
never surfaced on the Calendar tab UI or any webapp route; that's
webapp/store.py's macro_calendar table's job for the titles it already
covers (see get_macro_calendar_events()).
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from config.settings import EVENT_REGISTRY

AVG_DAYS_PER_MONTH = 30.4368  # average Gregorian month length


def _next_from_ff_snapshot(title: str, conn, now: dt.date) -> Optional[dt.date]:
    """
    Tier 1: a real upcoming occurrence of `title` already sitting in the
    current Forex Factory calendar snapshot. Returns the earliest future
    event_time_utc's date for this title, or None if nothing has been
    fetched yet or no matching future row exists.
    """
    from webapp.store import get_calendar_snapshot  # local import: scoring/data_layer -> webapp, avoid a module-level cycle
    snapshot = get_calendar_snapshot(conn)
    if snapshot is None:
        return None
    candidates = []
    for raw in snapshot.events:
        if raw.get("title") != title:
            continue
        try:
            event_time = dt.datetime.fromisoformat(raw["event_time_utc"])
        except (KeyError, ValueError):
            continue
        if event_time.date() >= now:
            candidates.append(event_time.date())
    return min(candidates) if candidates else None


def _next_from_macro_calendar(title: str, conn, now: dt.date) -> Optional[dt.date]:
    """
    Tier 2: macro_calendar's existing FRED-release-schedule estimate, for
    the subset of titles it already covers. Looks ~13 months ahead — wide
    enough to catch even a quarterly (GDP) or FOMC-cadence (~1.6-month)
    title's next date. Returns the earliest matching event_date, or None.
    """
    from webapp.store import get_macro_calendar_events  # local import: avoid a module-level cycle
    end = now + dt.timedelta(days=395)
    rows = get_macro_calendar_events(conn, now.isoformat(), end.isoformat())
    matching = [r for r in rows if r.event_title == title]
    if not matching:
        return None
    return dt.date.fromisoformat(min(r.event_date for r in matching))


def _last_confirmed_occurrence(title: str, conn) -> Optional[dt.date]:
    """
    The most recent CONFIRMED (actual IS NOT NULL) event_history date for
    `title` — real, resolved data only, never guessed. None if this title
    has no resolved occurrence recorded yet.
    """
    from webapp.store import get_event_history  # local import: avoid a module-level cycle
    rows = get_event_history(conn, title, limit=6)
    resolved = [r for r in rows if r.actual is not None]
    if not resolved:
        return None
    return dt.datetime.fromisoformat(resolved[0].event_time_utc).date()  # rows are DESC by event_time_utc


def get_approximate_next_occurrence(
    title: str,
    conn,
    now: Optional[dt.date] = None,
) -> Optional[dt.date]:
    """
    Fallback chain, real data always wins over the estimate:
      1. A real upcoming occurrence already in the current FF calendar
         snapshot.
      2. macro_calendar's existing FRED-derived estimate, for the subset
         of titles it already covers.
      3. EVENT_REGISTRY[title]['avg_interval_months'] added to the most
         recent CONFIRMED event_history occurrence (rounded to the
         nearest day) — deliberately month-level approximate, never a
         fabricated exact date.

    Returns None if `title` isn't in EVENT_REGISTRY, or if none of the
    three sources have an answer.
    """
    if title not in EVENT_REGISTRY:
        return None
    now = now or dt.datetime.now(dt.timezone.utc).date()

    real = _next_from_ff_snapshot(title, conn, now)
    if real is not None:
        return real

    macro = _next_from_macro_calendar(title, conn, now)
    if macro is not None:
        return macro

    last_confirmed = _last_confirmed_occurrence(title, conn)
    if last_confirmed is None:
        return None
    interval_days = EVENT_REGISTRY[title]["avg_interval_months"] * AVG_DAYS_PER_MONTH
    return last_confirmed + dt.timedelta(days=round(interval_days))
```

- [ ] **Step 5: Add the fallback-chain tests**

Append to `tests/test_event_registry.py` (before the `if __name__ ==` block):

```python
def _event(title, event_time_utc, forecast="0.2%", actual=None, impact="High"):
    return EconomicEvent(title=title, country="USD", impact=impact, event_time_utc=event_time_utc, forecast=forecast, actual=actual)


def test_get_approximate_next_occurrence_unregistered_title_returns_none():
    print("=== get_approximate_next_occurrence: a title not in EVENT_REGISTRY returns None ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        assert get_approximate_next_occurrence("Not A Real Event", conn) is None
    print("PASS\n")


def test_get_approximate_next_occurrence_no_sources_returns_none():
    print("=== get_approximate_next_occurrence: no FF snapshot, no macro_calendar row, no resolved history -> None ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        assert get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2)) is None
    print("PASS\n")


def test_get_approximate_next_occurrence_tier3_cadence_math():
    print("=== get_approximate_next_occurrence: falls back to last-confirmed + avg_interval_months when no real source has an answer ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        last = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)
        store.upsert_event_history(conn, _event("CPI m/m", last, actual="0.3%"), surprise_direction="higher", now=last)
        result = get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2))
        # avg_interval_months=1.0 -> ~30 days after 2026-08-13
        assert result == dt.date(2026, 8, 13) + dt.timedelta(days=30)
    print("PASS\n")


def test_get_approximate_next_occurrence_tier3_fractional_interval():
    print("=== get_approximate_next_occurrence: FOMC's 1.6-month cadence produces a real fractional-month offset, not a rounded whole month ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        last = dt.datetime(2026, 7, 29, 18, 0, tzinfo=UTC_TZ)
        store.upsert_event_history(conn, _event("FOMC Statement", last, forecast=None, actual="ok", impact="High"), surprise_direction=None, now=last)
        result = get_approximate_next_occurrence("FOMC Statement", conn, now=dt.date(2026, 9, 2))
        expected_days = round(1.6 * 30.4368)
        assert result == dt.date(2026, 7, 29) + dt.timedelta(days=expected_days)
    print("PASS\n")


def test_get_approximate_next_occurrence_macro_calendar_beats_cadence_math():
    print("=== get_approximate_next_occurrence: a macro_calendar row wins over the cadence-math fallback ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        last = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)
        store.upsert_event_history(conn, _event("CPI m/m", last, actual="0.3%"), surprise_direction="higher", now=last)
        store.upsert_macro_calendar_event(
            conn, "CPI m/m", event_date="2026-09-10", estimated_time_utc=None,
            time_source="history_derived", now=dt.datetime(2026, 9, 2, tzinfo=UTC_TZ),
        )
        result = get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2))
        assert result == dt.date(2026, 9, 10), "macro_calendar's real estimate must win over the cadence-math guess"
    print("PASS\n")


def test_get_approximate_next_occurrence_ff_snapshot_beats_everything():
    print("=== get_approximate_next_occurrence: a real FF snapshot row wins over both macro_calendar and cadence math ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        last = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)
        store.upsert_event_history(conn, _event("CPI m/m", last, actual="0.3%"), surprise_direction="higher", now=last)
        store.upsert_macro_calendar_event(
            conn, "CPI m/m", event_date="2026-09-10", estimated_time_utc=None,
            time_source="history_derived", now=dt.datetime(2026, 9, 2, tzinfo=UTC_TZ),
        )
        future_event = _event("CPI m/m", dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC_TZ), forecast="0.2%")
        store.save_calendar_snapshot_if_changed(conn, [future_event], dt.datetime(2026, 9, 2, tzinfo=UTC_TZ))
        result = get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2))
        assert result == dt.date(2026, 9, 11), "a real FF snapshot occurrence must win over every fallback"
    print("PASS\n")
```

Also update the `if __name__ ==` block at the bottom to call all six test functions.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_event_registry.py -v`
Expected: all 8 tests PASS. If tier ordering fails, check that `_next_from_ff_snapshot` and `_next_from_macro_calendar` are actually being called before the cadence fallback in `get_approximate_next_occurrence`.

- [ ] **Step 7: Commit**

```bash
git add config/settings.py data_layer/event_registry.py tests/test_event_registry.py
git commit -m "feat: add EVENT_REGISTRY and cadence-derived next-occurrence resolution

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Influence graph config, replacing the hardcoded ADP/PPI links

**Files:**
- Modify: `config/settings.py` (add `EVENT_INFLUENCE_LINKS`)
- Test: `tests/test_event_registry.py` (extend)

**Interfaces:**
- Consumes: `config.settings.EVENT_REGISTRY` (Task 1) — every link's target and precursor title must be a key in it.
- Produces: `config.settings.EVENT_INFLUENCE_LINKS: dict[str, list[tuple[str, float]]]`, consumed by Task 3's `get_precursor_events_for()`.

- [ ] **Step 1: Write the failing structural-validation test**

Append to `tests/test_event_registry.py` (add this import at the top alongside the others: `from config.settings import EVENT_INFLUENCE_LINKS`):

```python
def test_event_influence_links_every_title_is_registered():
    print("=== EVENT_INFLUENCE_LINKS: every target and precursor title is present in EVENT_REGISTRY ===")
    for target, precursors in EVENT_INFLUENCE_LINKS.items():
        assert target in EVENT_REGISTRY, f"link target {target!r} is not in EVENT_REGISTRY — a link to an unregistered title is a config bug"
        for precursor_title, weight in precursors:
            assert precursor_title in EVENT_REGISTRY, f"link precursor {precursor_title!r} (-> {target!r}) is not in EVENT_REGISTRY"
            assert 0.0 < weight <= 1.0, f"link {precursor_title!r} -> {target!r} has an out-of-range weight: {weight}"
    print("PASS\n")


def test_event_influence_links_absorbs_the_old_hardcoded_adp_ppi_links():
    print("=== EVENT_INFLUENCE_LINKS: the two previously-hardcoded links (ADP->NFP, PPI->CPI) are present ===")
    nfp_precursors = dict(EVENT_INFLUENCE_LINKS.get("Non-Farm Employment Change", []))
    assert "ADP Nonfarm Employment Change" in nfp_precursors
    cpi_precursors = dict(EVENT_INFLUENCE_LINKS.get("CPI m/m", []))
    assert "PPI m/m" in cpi_precursors
    print("PASS\n")
```

Run: `python -m pytest tests/test_event_registry.py -v -k influence_links`
Expected: both new tests FAIL with `NameError`/`ImportError` (`EVENT_INFLUENCE_LINKS` doesn't exist yet).

- [ ] **Step 2: Add `EVENT_INFLUENCE_LINKS` to `config/settings.py`**

Insert immediately after the `EVENT_REGISTRY` block from Task 1:

```python
# --- Influence graph ---
# Hand-curated, seeded from docs/fundamental-analysis-monthly-event-
# map-2026-09-02.md's §6 precursor chains — same authoring discipline as
# EVENT_SURPRISE_DIRECTION, not inferred or ML-scored. Tier-agnostic in
# structure: Low->Medium, Low->High, Medium->High, and High->High links
# all use the same {target: [(precursor, weight), ...]} shape — impact
# tier (EVENT_REGISTRY) is metadata used only to decide dashboard-score-
# or-not, never a structural constraint on which links are allowed.
#
# Absorbs and replaces the old PRECURSOR_EVENTS dict — ADP->NFP and
# PPI->CPI are its first two entries below, at the same weight
# (PRECURSOR_TRUST_WEIGHT, 0.9) the old hardcoded mechanism used, so the
# migration is behavior-preserving (see tests/test_probability_engine.py's
# regression test).
#
# The float weight is EXPLICITLY NOT consumed by any scoring math yet —
# it's authored metadata for a future refinement once real backtest data
# justifies weighting one precursor's disagreement more than another's
# (see docs/superpowers/specs/2026-09-02-event-registry-influence-graph-design.md's
# "confluence as an explicit boost" deferral). Every value here is an
# untuned starting estimate, same honesty as every other confidence
# constant in this codebase.
EVENT_INFLUENCE_LINKS: dict[str, list[tuple[str, float]]] = {
    "Non-Farm Employment Change": [
        ("ADP Nonfarm Employment Change", 0.90),  # migrated from the old hardcoded PRECURSOR_EVENTS link
        ("JOLTS Job Openings", 0.40),
        ("Challenger Job Cuts", 0.35),
        ("Unemployment Claims", 0.30),
    ],
    "Unemployment Rate": [
        ("ADP Nonfarm Employment Change", 0.60),
        ("Unemployment Claims", 0.40),
    ],
    "Average Hourly Earnings m/m": [
        ("ADP Nonfarm Employment Change", 0.50),
    ],
    "CPI m/m": [
        ("PPI m/m", 0.90),  # migrated from the old hardcoded PRECURSOR_EVENTS link
        ("Core PPI m/m", 0.60),
        ("Import Prices m/m", 0.40),
        ("ISM Manufacturing Prices", 0.30),
        ("ISM Services Prices", 0.30),
    ],
    "CPI y/y": [
        ("PPI m/m", 0.80),
        ("Core PPI m/m", 0.55),
    ],
    "Core CPI m/m": [
        ("Core PPI m/m", 0.85),
    ],
    "Core CPI y/y": [
        ("Core PPI m/m", 0.70),
    ],
    "Core PCE Price Index m/m": [
        ("CPI m/m", 0.70),  # High->High: the Fed's own preferred gauge, reads the CPI print first
        ("Core CPI m/m", 0.75),
    ],
    "FOMC Statement": [
        ("Non-Farm Employment Change", 0.50),   # High->High: labor strength shapes the Fed's read
        ("CPI m/m", 0.60),                       # High->High: inflation is the Committee's primary input
        ("Core PCE Price Index m/m", 0.65),      # High->High: the Fed's own preferred gauge
    ],
    "Federal Funds Rate": [
        ("Non-Farm Employment Change", 0.50),
        ("CPI m/m", 0.60),
        ("Core PCE Price Index m/m", 0.65),
    ],
    "Prelim GDP q/q": [
        ("Retail Sales m/m", 0.35),        # feeds the Personal Consumption Expenditures component
        ("Durable Goods Orders m/m", 0.30),  # feeds the Business Investment component
        ("Trade Balance", 0.20),            # feeds the Net Exports component
        ("ISM Manufacturing PMI", 0.30),
        ("ISM Services PMI", 0.30),
    ],
    "ISM Manufacturing PMI": [
        ("S&P Global Manufacturing PMI Flash", 0.45),
    ],
    "ISM Services PMI": [
        ("S&P Global Services PMI Flash", 0.45),
    ],
    "Industrial Production m/m": [
        ("ISM Manufacturing PMI", 0.40),
    ],
    "Durable Goods Orders m/m": [
        ("ISM Manufacturing PMI", 0.30),
    ],
    "Retail Sales m/m": [
        ("CB Consumer Confidence", 0.35),
        ("Prelim UoM Consumer Sentiment", 0.35),
    ],
    "Housing Starts": [
        ("Building Permits", 0.55),  # leading -> coincident, same publish cycle
    ],
    "Existing Home Sales": [
        ("Building Permits", 0.30),
        ("Housing Starts", 0.30),
    ],
    "New Home Sales": [
        ("Building Permits", 0.30),
        ("Housing Starts", 0.30),
    ],
}
```

- [ ] **Step 3: Run the tests to verify they pass**

Run: `python -m pytest tests/test_event_registry.py -v`
Expected: all tests PASS, including both new ones from Step 1.

- [ ] **Step 4: Commit**

```bash
git add config/settings.py tests/test_event_registry.py
git commit -m "feat: add EVENT_INFLUENCE_LINKS, absorbing the old ADP->NFP/PPI->CPI hardcoded links

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Graph-driven precursor fetch (`get_precursor_events_for`)

**Files:**
- Modify: `scoring/probability_engine.py` (add `get_precursor_events_for()`)
- Test: `tests/test_probability_engine.py` (extend)

**Interfaces:**
- Consumes: `config.settings.EVENT_INFLUENCE_LINKS`, `config.settings.PRE_EVENT_WINDOW_HOURS` (Task 1/2); `webapp.store.get_event_history(conn, event_title, limit=6) -> list[EventHistoryRow]`.
- Produces: `get_precursor_events_for(target_title: str, target_event_time_utc: dt.datetime, conn) -> list[EconomicEvent]`, consumed by Task 6's `backtest_accumulator.py` wiring.

Note on signature: the spec's illustrative sketch shows `get_precursor_events_for(target_title, conn)` (2 args). This plan adds a third, required `target_event_time_utc` parameter — the old `find_precursor_events(target, all_events)` bounded its search to `target`'s own `PRE_EVENT_WINDOW_HOURS` pre-event window (via `target.event_time_utc`), and dropping that bound here would let a stale prior-cycle resolved row (e.g. last month's ADP print, still the "most recent resolved" row if this month's hasn't printed yet) get mistaken for a fresh precursor. The 2-arg sketch is not literally implementable without silently regressing that guarantee — carrying the target's own time forward preserves it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_probability_engine.py`'s imports: `from scoring.probability_engine import get_precursor_events_for` and `import webapp.store as webapp_store` and `import tempfile` and `from pathlib import Path`.

Append these test functions:

```python
def test_get_precursor_events_for_no_configured_links_returns_empty():
    print("=== get_precursor_events_for: a target with no EVENT_INFLUENCE_LINKS entry returns [] ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = webapp_store.get_connection(Path(tmp) / "test.db")
        result = get_precursor_events_for("Some Untracked Event", EVENT_TIME, conn)
        assert result == []
    print("PASS\n")


def test_get_precursor_events_for_finds_resolved_precursor_in_window():
    print("=== get_precursor_events_for: finds a linked precursor's most recent RESOLVED event_history row inside the target's pre-event window ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = webapp_store.get_connection(Path(tmp) / "test.db")
        precursor_time = EVENT_TIME - dt.timedelta(hours=5)
        webapp_store.upsert_event_history(
            conn,
            EconomicEvent(title="PPI m/m", country="USD", impact="Medium", event_time_utc=precursor_time, forecast="0.2%", actual="0.4%"),
            surprise_direction="higher", now=precursor_time,
        )
        result = get_precursor_events_for("CPI m/m", EVENT_TIME, conn)
        assert len(result) == 1
        assert result[0].title == "PPI m/m"
        assert result[0].actual == "0.4%"
    print("PASS\n")


def test_get_precursor_events_for_skips_unresolved_precursor():
    print("=== get_precursor_events_for: a linked precursor with no resolved actual yet is simply absent, never fabricated ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = webapp_store.get_connection(Path(tmp) / "test.db")
        precursor_time = EVENT_TIME - dt.timedelta(hours=5)
        webapp_store.upsert_event_history(
            conn,
            EconomicEvent(title="PPI m/m", country="USD", impact="Medium", event_time_utc=precursor_time, forecast="0.2%", actual=None),
            surprise_direction=None, now=precursor_time,
        )
        result = get_precursor_events_for("CPI m/m", EVENT_TIME, conn)
        assert result == []
    print("PASS\n")


def test_get_precursor_events_for_ignores_stale_resolved_row_outside_window():
    print("=== get_precursor_events_for: a resolved precursor row from a PRIOR cycle, outside this target's pre-event window, is not used ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = webapp_store.get_connection(Path(tmp) / "test.db")
        stale_time = EVENT_TIME - dt.timedelta(days=40)  # well outside PRE_EVENT_WINDOW_HOURS (72h)
        webapp_store.upsert_event_history(
            conn,
            EconomicEvent(title="PPI m/m", country="USD", impact="Medium", event_time_utc=stale_time, forecast="0.2%", actual="0.3%"),
            surprise_direction="higher", now=stale_time,
        )
        result = get_precursor_events_for("CPI m/m", EVENT_TIME, conn)
        assert result == [], "a month-old resolved PPI print must not be mistaken for this cycle's precursor"
    print("PASS\n")


def test_get_precursor_events_for_multiple_links_all_resolved():
    print("=== get_precursor_events_for: multiple configured links for one target all resolve independently ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = webapp_store.get_connection(Path(tmp) / "test.db")
        ppi_time = EVENT_TIME - dt.timedelta(hours=48)
        import_time = EVENT_TIME - dt.timedelta(hours=6)
        webapp_store.upsert_event_history(
            conn,
            EconomicEvent(title="PPI m/m", country="USD", impact="Medium", event_time_utc=ppi_time, forecast="0.2%", actual="0.4%"),
            surprise_direction="higher", now=ppi_time,
        )
        webapp_store.upsert_event_history(
            conn,
            EconomicEvent(title="Import Prices m/m", country="USD", impact="Low", event_time_utc=import_time, forecast="0.1%", actual="0.1%"),
            surprise_direction="in_line", now=import_time,
        )
        result = get_precursor_events_for("CPI m/m", EVENT_TIME, conn)
        titles = {e.title for e in result}
        assert titles == {"PPI m/m", "Import Prices m/m"}
    print("PASS\n")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_probability_engine.py -v -k get_precursor_events_for`
Expected: FAIL with `ImportError: cannot import name 'get_precursor_events_for'`.

- [ ] **Step 3: Implement `get_precursor_events_for()` in `scoring/probability_engine.py`**

Add `PRE_EVENT_WINDOW_HOURS` and `EVENT_INFLUENCE_LINKS` to the existing `from config.settings import (...)` block at the top of the file, then add this function immediately after `_build_precursor_contributions()`:

```python
def get_precursor_events_for(
    target_title: str,
    target_event_time_utc: dt.datetime,
    conn,
) -> list[EconomicEvent]:
    """
    Graph-driven replacement for data_layer.calendar_feed.find_precursor_events().
    Looks up EVENT_INFLUENCE_LINKS[target_title] (empty list if no
    configured links). For each linked precursor title, fetches that
    title's most recent RESOLVED (actual IS NOT NULL) event_history row —
    kept only if it falls inside target's own PRE_EVENT_WINDOW_HOURS
    pre-event window, the same bound find_precursor_events() used, so a
    resolved row from a PRIOR cycle (e.g. last month's ADP print) is never
    mistaken for this cycle's precursor. Skips any precursor title with
    no resolved row in that window at all — never fabricates.

    `conn` is a webapp.store-shaped sqlite3.Connection (duck-typed — this
    module never imports webapp/ at module level, to avoid a cycle with
    webapp/ importing scoring/).
    """
    from webapp.store import get_event_history  # local import: avoid a module-level cycle with webapp/

    linked = EVENT_INFLUENCE_LINKS.get(target_title, [])
    if not linked:
        return []
    window_start = target_event_time_utc - dt.timedelta(hours=PRE_EVENT_WINDOW_HOURS)

    precursors: list[EconomicEvent] = []
    for precursor_title, _weight in linked:
        rows = get_event_history(conn, precursor_title, limit=6)
        resolved = [r for r in rows if r.actual is not None]
        if not resolved:
            continue
        most_recent = resolved[0]  # get_event_history orders DESC by event_time_utc
        event_time = dt.datetime.fromisoformat(most_recent.event_time_utc)
        if not (window_start <= event_time < target_event_time_utc):
            continue
        precursors.append(
            EconomicEvent(
                title=most_recent.event_title,
                country="USD",
                impact=most_recent.impact or "Medium",
                event_time_utc=event_time,
                forecast=most_recent.forecast,
                previous=most_recent.previous,
                actual=most_recent.actual,
            )
        )
    return precursors
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_probability_engine.py -v -k get_precursor_events_for`
Expected: all 5 tests PASS.

- [ ] **Step 5: Run the full test file to check nothing else broke**

Run: `python -m pytest tests/test_probability_engine.py -v`
Expected: all tests PASS (the known pre-existing `test_redundancy_discount_works_across_sentiment_tiers_not_just_lexicon` FinBERT failure is the only acceptable failure — confirm it's the SAME failure, not a new one, before proceeding).

- [ ] **Step 6: Commit**

```bash
git add scoring/probability_engine.py tests/test_probability_engine.py
git commit -m "feat: add graph-driven get_precursor_events_for(), replacing find_precursor_events()

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Chain-conflict detection (`_check_precursor_chain_conflict`)

**Files:**
- Modify: `scoring/probability_engine.py` (add `_check_precursor_chain_conflict()`, new `ProbabilityResult` fields, `score_bundle()` wiring, `summary()` update)
- Modify: `config/settings.py` (add `PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER`)
- Test: `tests/test_probability_engine.py` (extend)

**Interfaces:**
- Consumes: `PrecursorContribution` (existing dataclass, `.usd_sentiment: float`).
- Produces: `_check_precursor_chain_conflict(precursor_contributions: list[PrecursorContribution]) -> tuple[bool, str | None]`; new `ProbabilityResult.chain_conflict_flag: bool = False` / `.chain_conflict_note: str | None = None` fields, consumed by Task 6's regression test and any future dashboard/accumulator surfacing.

- [ ] **Step 1: Add the new confidence multiplier to `config/settings.py`**

Insert immediately after `OIL_SHOCK_CONFIDENCE_MULTIPLIER = 0.8` (around line 658):

```python
# Confidence dampener when 2+ of a target event's linked, CONFIRMED
# precursors (config.settings.EVENT_INFLUENCE_LINKS) disagree in USD
# direction — a genuine conflict within the target's own precursor
# chain, distinct from _detect_contradiction() (article-only,
# recent-vs-older narrative shift) and _check_macro_backdrop() (compares
# against an EXTERNAL dollar/rates read, not other precursors). Same
# untuned-starting-value honesty as every other confidence multiplier
# here, calibrated later against real backtest data.
PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER = 0.75
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_probability_engine.py`:

```python
def _precursor_contribution(usd_sentiment: float):
    event = EconomicEvent(title="PPI m/m", country="USD", impact="Medium", event_time_utc=EVENT_TIME, forecast="0.2%", actual="0.4%")
    from scoring.probability_engine import PrecursorContribution
    return PrecursorContribution(event=event, usd_sentiment=usd_sentiment, trust_weight=0.9, time_weight=1.0, combined_weight=0.9)


def test_check_precursor_chain_conflict_fewer_than_two_no_conflict():
    print("=== _check_precursor_chain_conflict: fewer than 2 precursor contributions can never conflict ===")
    from scoring.probability_engine import _check_precursor_chain_conflict
    assert _check_precursor_chain_conflict([]) == (False, None)
    assert _check_precursor_chain_conflict([_precursor_contribution(0.5)]) == (False, None)
    print("PASS\n")


def test_check_precursor_chain_conflict_two_agree_no_conflict():
    print("=== _check_precursor_chain_conflict: 2 precursors agreeing in sign is not a conflict ===")
    from scoring.probability_engine import _check_precursor_chain_conflict
    result = _check_precursor_chain_conflict([_precursor_contribution(0.5), _precursor_contribution(0.3)])
    assert result == (False, None)
    print("PASS\n")


def test_check_precursor_chain_conflict_two_disagree_flags():
    print("=== _check_precursor_chain_conflict: 2 precursors disagreeing in sign flags a real conflict ===")
    from scoring.probability_engine import _check_precursor_chain_conflict
    flag, note = _check_precursor_chain_conflict([_precursor_contribution(0.5), _precursor_contribution(-0.4)])
    assert flag is True
    assert note is not None and "conflict" in note.lower()
    print("PASS\n")


def test_check_precursor_chain_conflict_three_with_one_outlier_flags():
    print("=== _check_precursor_chain_conflict: 3 precursors with one outlier still flags (2+ disagree is enough) ===")
    from scoring.probability_engine import _check_precursor_chain_conflict
    flag, note = _check_precursor_chain_conflict([_precursor_contribution(0.5), _precursor_contribution(0.4), _precursor_contribution(-0.3)])
    assert flag is True
    print("PASS\n")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_probability_engine.py -v -k chain_conflict`
Expected: FAIL with `ImportError: cannot import name '_check_precursor_chain_conflict'`.

- [ ] **Step 4: Implement `_check_precursor_chain_conflict()`**

Add `PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER` to the existing `from config.settings import (...)` block, then add this function immediately after `_check_oil_shock()`:

```python
def _check_precursor_chain_conflict(
    precursor_contributions: list[PrecursorContribution],
) -> tuple[bool, str | None]:
    """
    (True, note) if 2+ precursor contributions disagree in sign (one
    USD-bullish, one USD-bearish) — a genuine conflict within THIS target
    event's own linked-precursor chain (config.settings.EVENT_INFLUENCE_LINKS).
    Distinct from _detect_contradiction() (article-only, recent-vs-older
    narrative shift) and from _check_macro_backdrop() (compares against
    an external dollar/rates read, not against other precursors).

    (False, None) if fewer than 2 precursor contributions, or all agree.
    Never touches direction or probability — confidence-only, same
    discipline as every other _check_* function here.
    """
    if len(precursor_contributions) < 2:
        return False, None

    bullish = [c for c in precursor_contributions if c.usd_sentiment > 0]
    bearish = [c for c in precursor_contributions if c.usd_sentiment < 0]
    if not bullish or not bearish:
        return False, None

    bullish_titles = ", ".join(c.event.title for c in bullish)
    bearish_titles = ", ".join(c.event.title for c in bearish)
    note = (
        f"Linked precursor chain conflict: {bullish_titles} read USD-bullish while "
        f"{bearish_titles} read USD-bearish — not silently averaged, treat this call with extra caution."
    )
    return True, note
```

- [ ] **Step 5: Add the new `ProbabilityResult` fields**

In the `ProbabilityResult` dataclass, immediately after `oil_shock_note: str | None = None`, add:

```python
    chain_conflict_flag: bool = False             # True = 2+ linked, confirmed precursors disagreed in direction
    chain_conflict_note: str | None = None
```

- [ ] **Step 6: Wire it into `score_bundle()` and `summary()`**

In `score_bundle()`, immediately after the existing `oil_shock_flag, oil_shock_note = _check_oil_shock(macro_backdrop)` / `if oil_shock_flag: confidence *= OIL_SHOCK_CONFIDENCE_MULTIPLIER` block, add:

```python
    chain_conflict_flag, chain_conflict_note = _check_precursor_chain_conflict(precursor_contributions)
    if chain_conflict_flag:
        confidence *= PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER
```

In the `return ProbabilityResult(...)` call at the bottom of `score_bundle()`, add after `oil_shock_note=oil_shock_note,`:

```python
        chain_conflict_flag=chain_conflict_flag,
        chain_conflict_note=chain_conflict_note,
```

In `ProbabilityResult.summary()`, immediately after the existing `if self.macro_backdrop_agrees is False:` block, add:

```python
        if self.chain_conflict_flag:
            base += f" — ⚠ {self.chain_conflict_note}"
```

- [ ] **Step 7: Write the `score_bundle()` integration test for chain conflict**

Append to `tests/test_probability_engine.py`:

```python
def test_score_bundle_flags_chain_conflict_when_linked_precursors_disagree():
    print("=== score_bundle: 2 linked, confirmed precursors disagreeing in direction sets chain_conflict_flag and dampens confidence ===")
    event = _cpi_event()  # "CPI m/m" target, links to PPI m/m + Core PPI m/m + Import Prices m/m + ISM Prices Paid
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    ppi_beat = EconomicEvent(title="PPI m/m", country="USD", impact="Medium", event_time_utc=EVENT_TIME - dt.timedelta(hours=10), forecast="0.2%", actual="0.5%")  # higher_bullish, beat -> USD-bullish
    import_miss = EconomicEvent(title="Import Prices m/m", country="USD", impact="Low", event_time_utc=EVENT_TIME - dt.timedelta(hours=5), forecast="0.3%", actual="0.0%")  # higher_bullish, big miss -> USD-bearish

    no_conflict_result = score_bundle(bundle, "XAUUSD", precursor_events=[ppi_beat])
    assert no_conflict_result.chain_conflict_flag is False

    conflict_result = score_bundle(bundle, "XAUUSD", precursor_events=[ppi_beat, import_miss])
    assert conflict_result.chain_conflict_flag is True
    assert conflict_result.chain_conflict_note is not None
    assert conflict_result.confidence < no_conflict_result.confidence * 1.01, "a chain conflict must dampen confidence, never raise it"
    print("PASS\n")
```

- [ ] **Step 8: Run the tests to verify they all pass**

Run: `python -m pytest tests/test_probability_engine.py -v -k "chain_conflict"`
Expected: all tests PASS.

Run: `python -m pytest tests/test_probability_engine.py -v`
Expected: all PASS except the one known pre-existing FinBERT failure.

- [ ] **Step 9: Commit**

```bash
git add config/settings.py scoring/probability_engine.py tests/test_probability_engine.py
git commit -m "feat: add precursor chain-conflict detection to score_bundle()

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Regression proof — migrated links produce identical behavior

**Files:**
- Test: `tests/test_probability_engine.py` (extend)

**Interfaces:**
- Consumes: `get_precursor_events_for()` (Task 3), `score_bundle()` (Task 4) — no production code changes in this task, proof-only.

This is the single most important regression test in the whole plan: proving Approach B's "don't disturb what already works" goal actually held for the two links this migration absorbs.

- [ ] **Step 1: Write the regression test**

Append to `tests/test_probability_engine.py`:

```python
def test_migrated_links_produce_identical_score_bundle_result_old_vs_new_path():
    print("=== REGRESSION: graph-driven ADP->NFP and PPI->CPI precursors produce IDENTICAL score_bundle() results to the old hardcoded path ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = webapp_store.get_connection(Path(tmp) / "test.db")

        # --- NFP target, ADP precursor ---
        nfp_event = EconomicEvent(title="Non-Farm Employment Change", country="USD", impact="High", event_time_utc=EVENT_TIME, forecast="180K")
        adp_time = EVENT_TIME - dt.timedelta(hours=48)
        adp_event = EconomicEvent(title="ADP Nonfarm Employment Change", country="USD", impact="Medium", event_time_utc=adp_time, forecast="150K", actual="190K")
        webapp_store.upsert_event_history(conn, adp_event, surprise_direction="higher", now=adp_time)

        nfp_bundle = EventNewsBundle(event=nfp_event, articles=[], as_of_utc=EVENT_TIME)
        old_path_nfp = score_bundle(nfp_bundle, "XAUUSD", precursor_events=[adp_event])
        new_precursors_nfp = get_precursor_events_for("Non-Farm Employment Change", EVENT_TIME, conn)
        new_path_nfp = score_bundle(nfp_bundle, "XAUUSD", precursor_events=new_precursors_nfp)

        assert new_path_nfp.aggregate_usd_sentiment == old_path_nfp.aggregate_usd_sentiment
        assert new_path_nfp.probability == old_path_nfp.probability
        assert new_path_nfp.confidence == old_path_nfp.confidence
        assert new_path_nfp.direction == old_path_nfp.direction

        # --- CPI target, PPI precursor ---
        cpi_event = _cpi_event()
        ppi_time = EVENT_TIME - dt.timedelta(hours=36)
        ppi_event = EconomicEvent(title="PPI m/m", country="USD", impact="Medium", event_time_utc=ppi_time, forecast="0.2%", actual="0.4%")
        webapp_store.upsert_event_history(conn, ppi_event, surprise_direction="higher", now=ppi_time)

        cpi_bundle = EventNewsBundle(event=cpi_event, articles=[], as_of_utc=EVENT_TIME)
        old_path_cpi = score_bundle(cpi_bundle, "XAUUSD", precursor_events=[ppi_event])
        new_precursors_cpi = get_precursor_events_for("CPI m/m", EVENT_TIME, conn)
        new_path_cpi = score_bundle(cpi_bundle, "XAUUSD", precursor_events=new_precursors_cpi)

        assert new_path_cpi.aggregate_usd_sentiment == old_path_cpi.aggregate_usd_sentiment
        assert new_path_cpi.probability == old_path_cpi.probability
        assert new_path_cpi.confidence == old_path_cpi.confidence
        assert new_path_cpi.direction == old_path_cpi.direction
    print("PASS\n")


def test_event_influence_links_weight_is_stored_but_not_consumed_by_scoring():
    print("=== EVENT_INFLUENCE_LINKS: the per-link float weight has no effect on _build_precursor_contributions()'s trust_weight ===")
    from config.settings import PRECURSOR_TRUST_WEIGHT
    event = EconomicEvent(title="Challenger Job Cuts", country="USD", impact="Low", event_time_utc=EVENT_TIME, forecast="20K", actual="35K")  # linked to NFP at weight 0.35, NOT 0.9
    from scoring.probability_engine import _build_precursor_contributions
    contributions = _build_precursor_contributions([event], EVENT_TIME)
    assert len(contributions) == 1
    assert contributions[0].trust_weight == PRECURSOR_TRUST_WEIGHT, "trust_weight must still come from the single global constant, not the link's own 0.35 weight"
    print("PASS\n")
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `python -m pytest tests/test_probability_engine.py -v -k "migrated_links or weight_is_stored"`
Expected: both tests PASS. If `test_migrated_links_produce_identical_score_bundle_result_old_vs_new_path` fails, the most likely cause is `get_precursor_events_for()`'s window bound or `EconomicEvent` field mismatch (e.g. `impact` defaulting differently) — compare the exact `EconomicEvent` fields the old hardcoded path constructed vs. what `get_precursor_events_for()` reconstructs from `event_history`.

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -q`
Expected: same pass/fail count as the pre-plan baseline (446 passed, 1 known pre-existing FinBERT failure) plus this plan's new tests, all passing.

- [ ] **Step 4: Commit**

```bash
git add tests/test_probability_engine.py
git commit -m "test: prove the migrated ADP->NFP/PPI->CPI links are behavior-identical to the old hardcoded path

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Wire the accumulator, remove the old mechanism, final verification

**Files:**
- Modify: `scoring/backtest_accumulator.py` (replace `find_precursor_events()` call with a graph-driven read)
- Modify: `data_layer/calendar_feed.py` (remove `find_precursor_events()` and its `PRECURSOR_EVENTS` import — fully superseded)
- Modify: `config/settings.py` (remove the now-unused `PRECURSOR_EVENTS` import site check — already deleted in Task 1, this step just confirms no leftover references)
- Modify: `tests/test_backtest_accumulator.py` (rewrite the two precursor tests to the new DB-driven mechanism)
- Test: `tests/test_backtest_accumulator.py` (rewritten in place)

**Interfaces:**
- Consumes: `scoring.probability_engine.get_precursor_events_for()` (Task 3).
- Produces: nothing new downstream — this task is the final integration point.

- [ ] **Step 1: Add a dashboard-connection precursor helper to `scoring/backtest_accumulator.py`**

Add this import alongside the existing `from scoring.probability_engine import score_bundle` line:

```python
from scoring.probability_engine import score_bundle, get_precursor_events_for
```

Add this function immediately after `_read_trend_signal()`:

```python
def _read_precursor_events(event: EconomicEvent) -> list[EconomicEvent]:
    """
    Reads config.settings.EVENT_INFLUENCE_LINKS-linked precursor events
    for `event` via a short-lived READ-ONLY connection to the dashboard's
    own DB — same pattern and same fail-open contract as
    _read_trend_signal() above. Replaces the old
    data_layer.calendar_feed.find_precursor_events(event, all_events)
    call, which searched the CURRENT WEEK's in-memory calendar fetch
    instead of the persisted event_history table.
    """
    conn = None
    try:
        conn = get_dashboard_connection(DASHBOARD_DB_PATH)
        return get_precursor_events_for(event.title, event.event_time_utc, conn)
    except Exception as exc:  # noqa: BLE001 — ANY dashboard-DB failure (open OR read) must not crash the accumulator cycle
        print(f"[backtest_accumulator] WARNING: could not read precursor events for {event.title}: {exc}")
        return []
    finally:
        if conn is not None:
            conn.close()
```

- [ ] **Step 2: Replace the old precursor lookup in `score_and_record_event()`**

Replace:

```python
    # Against the FULL unfiltered calendar (all_events), not a
    # High-impact-only filtered list — precursors like ADP, PPI m/m are
    # typically Medium impact and would be silently excluded if this
    # searched a filtered list instead.
    precursors = find_precursor_events(event, all_events)
    if precursors:
        print(f"[backtest_accumulator] precursors for {event.title}: {[p.title for p in precursors]}")
```

with:

```python
    # Graph-driven (config.settings.EVENT_INFLUENCE_LINKS) precursor
    # lookup against the dashboard's persisted event_history — replaces
    # the old find_precursor_events(event, all_events) in-memory search.
    # `all_events` is still accepted as a parameter for signature
    # stability (scripts/run_manual_sentiment_check.py still passes it)
    # but is no longer used for precursor lookup.
    precursors = _read_precursor_events(event)
    if precursors:
        print(f"[backtest_accumulator] precursors for {event.title}: {[p.title for p in precursors]}")
```

Remove `find_precursor_events` from the `from data_layer.calendar_feed import (...)` block at the top of the file (leave `EconomicEvent, fetch_calendar, filter_relevant_events, events_in_pre_window, _parse_numeric` in place).

- [ ] **Step 3: Remove `find_precursor_events()` and `PRECURSOR_EVENTS` from `data_layer/calendar_feed.py`**

Delete the `find_precursor_events()` function (the block ending just before the module's trailing blank line) and remove `PRECURSOR_EVENTS` from the `from config.settings import (...)` block at the top of the file.

- [ ] **Step 4: Rewrite the two accumulator precursor tests**

In `tests/test_backtest_accumulator.py`, replace `test_precursor_events_found_and_passed_to_score_bundle` with:

```python
def test_precursor_events_found_via_graph_and_passed_to_score_bundle():
    print("=== accumulator: a graph-linked, already-resolved precursor event (e.g. PPI before CPI) is found via event_history and blended into scoring ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        target = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20), forecast="0.2%", actual=None,
        )
        precursor_time = now - dt.timedelta(hours=5)
        precursor = EconomicEvent(
            title="Core PPI m/m", country="USD", impact="Medium",
            event_time_utc=precursor_time, forecast="0.2%", actual="0.4%",  # already released, linked to CPI m/m
        )
        dash_conn = webapp_store.get_connection(dashboard_db_path)
        webapp_store.upsert_event_history(dash_conn, precursor, surprise_direction="higher", now=precursor_time)
        dash_conn.close()

        with patch.object(accumulator, "fetch_calendar", return_value=[target]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: [e for e in events if e.impact == "High"]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=target, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path), \
             patch.object(accumulator, "score_bundle") as mock_score:
            mock_score.return_value = _fake_result()
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            mock_score.assert_called_once()
            _, kwargs = mock_score.call_args
            assert "precursor_events" in kwargs, "score_bundle must be called with precursor_events, not left at its None default"
            precursors_passed = kwargs["precursor_events"]
            assert len(precursors_passed) == 1, f"expected exactly the Core PPI precursor (linked, resolved, in-window), got {precursors_passed}"
            assert precursors_passed[0].title == "Core PPI m/m"
    print("PASS\n")
```

Replace `test_precursor_events_uses_unfiltered_calendar_not_high_impact_only` with:

```python
def test_precursor_events_found_regardless_of_scoring_calendar_filter():
    print("=== accumulator: precursor lookup reads event_history directly, unaffected by the scoring candidate list's High-impact-only filter ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        target = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20), forecast="0.2%", actual=None,
        )
        precursor_time = now - dt.timedelta(hours=5)
        # "PPI m/m" is Medium impact — filter_relevant_events() (High-only)
        # would drop it from the SCORING candidate list, but the
        # graph-driven precursor lookup reads event_history directly and
        # must still find it.
        precursor = EconomicEvent(
            title="PPI m/m", country="USD", impact="Medium",
            event_time_utc=precursor_time, forecast="0.2%", actual="0.5%",
        )
        dash_conn = webapp_store.get_connection(dashboard_db_path)
        webapp_store.upsert_event_history(dash_conn, precursor, surprise_direction="higher", now=precursor_time)
        dash_conn.close()

        with patch.object(accumulator, "fetch_calendar", return_value=[target]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: [e for e in events if e.impact == "High"]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=target, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path), \
             patch.object(accumulator, "score_bundle") as mock_score:
            mock_score.return_value = _fake_result()
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            _, kwargs = mock_score.call_args
            titles_passed = [e.title for e in kwargs["precursor_events"]]
            assert "PPI m/m" in titles_passed, "Medium-impact precursor must still be found via event_history, regardless of the scoring filter"
    print("PASS\n")
```

Update the two call sites in the `if __name__ ==` block at the bottom of the file:
- `test_precursor_events_found_and_passed_to_score_bundle()` → `test_precursor_events_found_via_graph_and_passed_to_score_bundle()`
- `test_precursor_events_uses_unfiltered_calendar_not_high_impact_only()` → `test_precursor_events_found_regardless_of_scoring_calendar_filter()`

Update the one remaining reference at line ~1143 (`patch.object(accumulator, "find_precursor_events", return_value=[])` inside the COT-once-per-cycle test) to instead patch the new function:

```python
patch.object(accumulator, "_read_precursor_events", return_value=[]),
```

Also confirm `import webapp.store as webapp_store` already exists near the top of `tests/test_backtest_accumulator.py` (it does, per the file's existing `dash_conn = webapp_store.get_connection(...)` usage elsewhere) — no new import needed.

- [ ] **Step 5: Run the accumulator test file to verify it passes**

Run: `python -m pytest tests/test_backtest_accumulator.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest -q`
Expected: identical result to Task 5 Step 3 — same total, same single known pre-existing FinBERT failure, nothing new broken by removing `find_precursor_events()`/`PRECURSOR_EVENTS`.

- [ ] **Step 7: Grep-confirm no leftover references to the removed mechanism**

Run: `grep -rn "find_precursor_events\|PRECURSOR_EVENTS" --include="*.py" .`
Expected: no output (both are fully removed from production code; a hit anywhere means a call site or import was missed).

- [ ] **Step 8: Commit**

```bash
git add scoring/backtest_accumulator.py data_layer/calendar_feed.py tests/test_backtest_accumulator.py
git commit -m "feat: wire the accumulator to the graph-driven precursor lookup, remove find_precursor_events()

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Post-plan notes (not tasks — for whoever picks this up next)

- The spec says `chain_conflict_note` should be "surfaced on the dashboard the same visible way `oil_shock_note` already is" — grep-confirmed during plan-writing that `oil_shock_note`/`cot_crowding_note`/`equity_risk_note` are NOT actually wired into any webapp route or template; the only place any `ProbabilityResult` note is surfaced today is `summary()` (used for the accumulator's own print/log output), and only for `contradiction_note`/`macro_backdrop_note`. Task 4 matches that REAL existing mechanism (adds `chain_conflict_note` to `summary()`) rather than a dashboard hook that doesn't exist yet — if a real dashboard surfacing pass ever gets built for the fundamental-signals-batch notes, `chain_conflict_note` should be added to it at the same time, not before.
- `scripts/run_manual_sentiment_check.py` still does a live `fetch_calendar("thisweek")` specifically "for precursor lookup" (per its own comment) before calling `score_and_record_event()` — that fetch is now unused for precursor purposes (the graph-driven lookup reads `event_history` instead). Left untouched in this plan to avoid touching an unrelated script and its test; worth a small follow-up cleanup once this lands.
- Several `EVENT_INFLUENCE_LINKS` precursor titles have no `EVENT_SURPRISE_DIRECTION` entry yet (e.g. `JOLTS Job Openings`, `ISM Manufacturing Prices`, `Industrial Production m/m`, `Durable Goods Orders m/m`, `Building Permits`, `CB Consumer Confidence`) — their links are registered but stay dormant (`usd_surprise_score()` returns `None`, so `_build_precursor_contributions()` silently skips them) until each title's surprise-direction mapping is added separately, per the spec's explicit scoping.
- `EVENT_REGISTRY`/`EVENT_INFLUENCE_LINKS` title strings are unverified against a live FF feed capture (this sandbox can't reach it) — re-verify once this runs somewhere FF is reachable, same standing caveat as `EVENT_SURPRISE_DIRECTION`'s own recent additions.
