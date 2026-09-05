# Co-Released Event Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the dashboard from showing contradictory article-based accumulator calls (e.g. US30 bullish under NFP, bearish under Unemployment Rate) for events that released at the exact same instant, by adding a read-time reconciliation layer requiring strict unanimity among co-released titles' calls, and surfacing a distinct conflict state instead of a silently-picked or blended call whenever even one title disagrees.

**Architecture:** A new pure-function module (`webapp/reconciliation.py`) takes a `{title: Prediction}` map for one instrument's co-released titles and returns either `None` (nothing to reconcile) or a `ReconciledCall` (unanimous agreement → the highest-confidence title's own untouched prediction; any real disagreement → a conflict marker, regardless of confidence gap). `webapp/app.py`'s `/api/predictions` route groups each ticker's events by `event_time_utc`, calls this function per group, and overwrites the group's `article_prediction`/adds `article_prediction_conflict` uniformly across every member of a reconciled group — so the card shows the same read regardless of which co-released title the existing sort happens to feature. `webapp/static/app.js` renders a new conflict badge when `article_prediction` is null but `article_prediction_conflict` is present.

**Tech Stack:** Python 3.14, Flask, sqlite3, vanilla JS/CSS (no build step) — same stack as the rest of `webapp/`.

**Spec:** `docs/superpowers/specs/2026-09-04-co-released-event-reconciliation-design.md`

## Global Constraints

- **History tab (`webapp/history.py`) must not be modified and its behavior must not change** — it reads `predictions`/`print_predictions` directly and keeps grading every co-released title independently, exactly as today.
- **Essence-only scoring (`webapp/scoring_service.py`) must not be modified** — this is strictly an accumulator-pipeline (`scoring/probability_engine.py` → `predictions` table) change.
- **The `predictions` table's write path must not be modified** — no changes to `scoring/probability_engine.py`'s scoring logic or `scoring/backtest_store.py`'s `record_prediction()`/INSERT statements. This is a read-time-only display layer over data that already exists.
- **Grouping key is exact `event_time_utc` string equality** — no fuzzy time-window matching, consistent with `webapp/static/app.js`'s existing `otherEventsHtml()` grouping.
- **No new field changes the JSON shape on the non-conflict path** — `article_prediction`'s dict shape (`direction`/`probability`/`article_count`/`top_contributions`) stays exactly as today when reconciliation resolves to agreement; the only addition is the new, always-present-but-usually-null `article_prediction_conflict` sibling field.
- **`reconcile_group()` never raises** — a title with a malformed/missing prediction is simply excluded from its group's reconciliation input, same "one bad lookup must not crash the whole build" discipline `webapp/history.py` already uses. If reconciliation itself throws for any reason inside `/api/predictions`, the route catches it, logs a warning, and falls back to today's plain per-title `article_prediction` for that group — never a card-rendering crash.

---

## File Structure

- **Create:** `webapp/reconciliation.py` — the pure reconciliation algorithm (`reconcile_group()`, `ReconciledCall`). No DB access, no Flask dependency — a unit-testable function over data the caller already fetched.
- **Create:** `tests/test_webapp_reconciliation.py` — unit tests for `reconcile_group()` in isolation.
- **Modify:** `webapp/app.py` — new private helper `_apply_co_released_reconciliation(ticker_events, predictions_by_time_and_title)` wired into the existing `/api/predictions` route (`get_predictions()`, currently at `webapp/app.py:227`), called once per ticker after that ticker's `entry["events"]` list is fully built, before the existing `entry["events"].sort(key=_sort_key)` call.
- **Modify:** `tests/test_webapp_app.py` — extend `/api/predictions` route tests for the new `article_prediction_conflict` field, including the real 2026-09-04 regression case.
- **Modify:** `webapp/static/app.js` — new `articlePredictionConflictHtml()` function and a small change to how `articlePredictionLine` is built, so a conflict renders its badge instead of nothing.
- **Modify:** `webapp/static/style.css` — new `.article-prediction-conflict` rule, added next to the existing `.article-prediction`/`.bull-bear-scale` rules.

---

### Task 1: `webapp/reconciliation.py` — the reconciliation algorithm

**Files:**
- Create: `webapp/reconciliation.py`
- Test: `tests/test_webapp_reconciliation.py`

**Interfaces:**
- Consumes: `scoring.backtest_store.Prediction` (existing dataclass — fields used: `direction: str` ('bullish'/'bearish'/'neutral'), `probability: float`, `confidence: float`, `article_count: int`, `top_contributions_json`, plus the `top_contributions` property).
- Produces (for Task 2): `reconcile_group(predictions_by_title: dict[str, Prediction]) -> Optional[ReconciledCall]`, and the `ReconciledCall` dataclass with fields `conflict: bool`, `prediction: Optional[Prediction]`, `conflicting_titles: Optional[list[str]]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_webapp_reconciliation.py`:

```python
"""
Tests for webapp/reconciliation.py's reconcile_group() — a pure function
over already-fetched Prediction rows, no DB, no network. See
docs/superpowers/specs/2026-09-04-co-released-event-reconciliation-design.md
for the algorithm this implements.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import Prediction
from webapp.reconciliation import reconcile_group, ReconciledCall


def _pred(title, direction, probability, confidence, instrument="US30", article_count=100):
    return Prediction(
        id=1, event_title=title, instrument=instrument, event_time_utc="2026-09-04T12:30:00+00:00",
        scored_at_utc="2026-09-04T06:00:00+00:00", probability=probability, direction=direction,
        confidence=confidence, article_count=article_count, contradiction_flag=False, source="live",
    )


def test_single_real_call_returns_none():
    print("=== reconcile_group: only one non-neutral title in the group -> nothing to reconcile, caller falls through ===")
    result = reconcile_group({
        "Non-Farm Employment Change": _pred("Non-Farm Employment Change", "bullish", 0.60, 0.30),
        "Unemployment Rate": _pred("Unemployment Rate", "neutral", 0.50, 0.0),
    })
    assert result is None
    print("PASS\n")


def test_all_neutral_returns_none():
    print("=== reconcile_group: every co-released title is neutral -> nothing to reconcile (falls through to plain neutral display) ===")
    result = reconcile_group({
        "Non-Farm Employment Change": _pred("Non-Farm Employment Change", "neutral", 0.50, 0.0),
        "Unemployment Rate": _pred("Unemployment Rate", "neutral", 0.50, 0.0),
    })
    assert result is None
    print("PASS\n")


def test_unanimous_agreement_returns_highest_confidence_titles_own_prediction():
    print("=== reconcile_group: every non-neutral title agrees on direction -> no conflict, the highest-confidence title's own prediction is returned untouched ===")
    dominant = _pred("Non-Farm Employment Change", "bullish", 0.70, 0.55, article_count=136)
    weaker_agree = _pred("Average Hourly Earnings m/m", "bullish", 0.55, 0.20)
    result = reconcile_group({
        "Non-Farm Employment Change": dominant,
        "Average Hourly Earnings m/m": weaker_agree,
    })
    assert result is not None
    assert result.conflict is False
    assert result.prediction is dominant  # exact same object -- never a synthetic blend
    assert result.prediction.article_count == 136
    print("PASS\n")


def test_real_2026_09_04_case_is_a_conflict():
    print("=== reconcile_group: the real 2026-09-04 occurrence (US30 bullish/bullish/bearish across NFP/AHE/Unemployment Rate) resolves as a genuine conflict ===")
    # Real confidence/probability values recorded live for this exact
    # occurrence (US30, 2026-09-04T12:30 UTC) -- see this plan's Task 2
    # for the matching /api/predictions-level regression test. Note:
    # NFP+AHE's COMBINED confidence (0.53+0.54) exceeds Unemployment
    # Rate's alone (0.37) -- an earlier, confidence-weighted design for
    # this function let that combined weight silently outvote the
    # dissenting title and call this "no conflict". The real subsequent
    # price move (XAUUSD -1.73%, bearish) agreed with the OUTVOTED
    # minority title, not the higher-combined-confidence pair -- which is
    # exactly why this function uses strict unanimity instead of a
    # confidence contest (see the design spec's 2026-09-05 revision).
    nfp = _pred("Non-Farm Employment Change", "bullish", 0.4697793269246527, 0.5314798614615047)
    ahe = _pred("Average Hourly Earnings m/m", "bullish", 0.46705663115758544, 0.536405991676083)
    unemployment_rate = _pred("Unemployment Rate", "bearish", 0.4495123783660442, 0.3705108141070306)
    result = reconcile_group({
        "Non-Farm Employment Change": nfp,
        "Average Hourly Earnings m/m": ahe,
        "Unemployment Rate": unemployment_rate,
    })
    assert result is not None
    assert result.conflict is True
    assert set(result.conflicting_titles) == {
        "Non-Farm Employment Change", "Average Hourly Earnings m/m", "Unemployment Rate",
    }
    print("PASS\n")


def test_a_single_dissenting_title_is_still_a_conflict_regardless_of_confidence_gap():
    print("=== reconcile_group: one low-confidence dissenting title is STILL a conflict, even against two much-higher-confidence agreeing titles -- no confidence contest overrules a real disagreement ===")
    strong_bullish_1 = _pred("Title A", "bullish", 0.75, 0.60)
    strong_bullish_2 = _pred("Title B", "bullish", 0.72, 0.58)
    weak_bearish = _pred("Title C", "bearish", 0.48, 0.05)
    result = reconcile_group({
        "Title A": strong_bullish_1, "Title B": strong_bullish_2, "Title C": weak_bearish,
    })
    assert result is not None
    assert result.conflict is True
    assert set(result.conflicting_titles) == {"Title A", "Title B", "Title C"}
    print("PASS\n")


def test_neutral_titles_never_block_agreement_among_the_real_calls():
    print("=== reconcile_group: neutral titles in the group are irrelevant to agreement -- two agreeing non-neutral titles plus a neutral one is still no conflict ===")
    dominant = _pred("Title A", "bullish", 0.65, 0.50)
    agrees = _pred("Title B", "bullish", 0.55, 0.20)
    neutral = _pred("Title C", "neutral", 0.50, 0.0)
    result = reconcile_group({"Title A": dominant, "Title B": agrees, "Title C": neutral})
    assert result is not None
    assert result.conflict is False
    assert result.prediction is dominant
    print("PASS\n")


def test_empty_input_returns_none():
    print("=== reconcile_group: an empty group (e.g. every title excluded upstream for a malformed row) is handled the same as 'nothing to reconcile' ===")
    result = reconcile_group({})
    assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_single_real_call_returns_none()
    test_all_neutral_returns_none()
    test_unanimous_agreement_returns_highest_confidence_titles_own_prediction()
    test_real_2026_09_04_case_is_a_conflict()
    test_a_single_dissenting_title_is_still_a_conflict_regardless_of_confidence_gap()
    test_neutral_titles_never_block_agreement_among_the_real_calls()
    test_empty_input_returns_none()
    print("All tests passed!")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_webapp_reconciliation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webapp.reconciliation'`

- [ ] **Step 3: Write the implementation**

Create `webapp/reconciliation.py`:

```python
"""
Read-time reconciliation for co-released tracked events — titles that
share the exact same event_time_utc (e.g. 2026-09-04T12:30 UTC's
Non-Farm Employment Change, Unemployment Rate, and Average Hourly
Earnings m/m, all from one BLS jobs report). Each title is scored fully
independently by scoring/probability_engine.py's accumulator (see
data_layer/event_context.py's per-title EVENT_RELEVANCE_KEYWORDS_BY_TITLE
article filter — different titles pull different article samples even
when released simultaneously), which can and does produce contradictory
per-instrument directional calls for what is economically one USD move
at one instant. Confirmed live 2026-09-04: US30 scored bullish under NFP,
bullish under AHE, bearish under Unemployment Rate, for the same
30-minute window.

Uses strict unanimity, not a confidence-weighted contest (2026-09-05
design revision — see docs/superpowers/specs/2026-09-04-co-released-
event-reconciliation-design.md): an earlier confidence-weighted design
let two moderately-confident agreeing titles outvote a single dissenting
title, and tested against this exact real occurrence, that resolved to
"no conflict" even though the dissenting title (Unemployment Rate,
bearish) was the one that matched the real subsequent price move
(XAUUSD -1.73%). A confidence contest can pick the wrong side; strict
unanimity never silently overrules a real disagreement.

This module never scores anything itself and never writes anything —
it's a pure, read-time validation layer over Prediction rows the caller
already fetched from scoring.backtest_store. See
docs/superpowers/specs/2026-09-04-co-released-event-reconciliation-design.md
for the full design and docs/superpowers/plans/2026-09-04-co-released-event-reconciliation.md
for how webapp/app.py wires this in.

Deliberately does NOT touch: scoring/probability_engine.py (no rescoring),
scoring/backtest_store.py's write path (predictions table is untouched),
or webapp/history.py (History keeps grading every title independently).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from scoring.backtest_store import Prediction


@dataclass
class ReconciledCall:
    conflict: bool
    # Only set when conflict is False — the highest-confidence
    # non-neutral title's OWN Prediction object, completely untouched
    # (never a synthetic blend of multiple titles' numbers). Only used
    # to pick WHICH of several unanimous titles' prediction to display,
    # never to decide whether they agree in the first place.
    prediction: Optional[Prediction] = None
    # Only set when conflict is True — every non-neutral title in the
    # group, for the caller to report/display which titles disagreed.
    conflicting_titles: Optional[list[str]] = None


def reconcile_group(predictions_by_title: dict[str, Prediction]) -> Optional[ReconciledCall]:
    """
    predictions_by_title: every co-released title's latest prediction for
    ONE instrument (caller is responsible for scoping this to a single
    instrument and a single event_time_utc group before calling).

    Returns None when there are fewer than 2 non-neutral-direction titles
    in the group -- nothing to reconcile, caller falls through to
    whatever plain single-title display it already had. Otherwise:

    1. Titles with direction == 'neutral' are excluded entirely — a
       neutral call has no direction to agree or conflict with, and
       plays no role in either outcome.
    2. If every remaining (non-neutral) title shares the SAME direction
       -> conflict=False, returning the highest-confidence one of
       those titles' own Prediction object untouched. Confidence here
       only breaks a tie among titles that already agree; it is never a
       contest between titles that disagree.
    3. If the non-neutral titles do NOT all share the same direction
       -> conflict=True, regardless of any confidence gap between them —
       one real dissenting title is enough, however low its confidence
       relative to the others.
    """
    non_neutral = {
        title: pred for title, pred in predictions_by_title.items()
        if pred.direction != "neutral"
    }
    if len(non_neutral) < 2:
        return None

    directions = {pred.direction for pred in non_neutral.values()}
    if len(directions) == 1:
        dominant = max(non_neutral.values(), key=lambda pred: pred.confidence)
        return ReconciledCall(conflict=False, prediction=dominant)

    return ReconciledCall(conflict=True, conflicting_titles=sorted(non_neutral.keys()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_webapp_reconciliation.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add webapp/reconciliation.py tests/test_webapp_reconciliation.py
git commit -m "feat: add reconcile_group() for co-released event contradiction detection"
```

---

### Task 2: Wire reconciliation into `/api/predictions`

**Files:**
- Modify: `webapp/app.py` (the `get_predictions()` route, `webapp/app.py:227`)
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `webapp.reconciliation.reconcile_group`, `webapp.reconciliation.ReconciledCall` (Task 1). Also consumes the existing `accumulator_prediction` (a `scoring.backtest_store.Prediction | None`) already computed per-event inside the route's existing loop — this task does NOT change how `accumulator_prediction` itself is fetched.
- Produces: the `/api/predictions` JSON response's `predictions[].events[]` entries gain a new, always-present `article_prediction_conflict` field (`null` except on a genuine conflict, where it's `{"titles": [...]}`), and `article_prediction` is overwritten (to the dominant's data, or to `null`) for every member of a group that resolves to a conflict or an agreement — untouched for events with no co-released group or an unreconcilable one.

- [ ] **Step 1: Write the failing test**

`tests/test_webapp_app.py` already has everything this test needs imported and helper-wise: `store`, `backtest_store`, `webapp_app` (imported as `import webapp.app as webapp_app` — the Flask test client is `webapp_app.app.test_client()`, NOT a bare `app`), `EconomicEvent`, `UTC_TZ`, `tempfile`, `Path`, `dt`, `patch`, and the existing `_seed_calendar(db_path, events)` helper (seeds `webapp.store`'s `calendar_snapshot` table directly from a list of `EconomicEvent` objects — see `tests/test_webapp_app.py:34-38` and its use in `test_predictions_includes_article_count_from_accumulator_db`, `tests/test_webapp_app.py:295-328`, which this new test mirrors exactly). No new helper needed.

Add to `tests/test_webapp_app.py`:

```python
def test_predictions_route_flags_co_released_conflict_and_leaves_singleton_events_alone():
    print("=== app: /api/predictions flags contradictory co-released accumulator calls with article_prediction_conflict; a lone event is untouched ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            event_time = dt.datetime(2026, 9, 4, 12, 30, tzinfo=UTC_TZ)
            solo_event_time = dt.datetime(2026, 9, 5, 12, 30, tzinfo=UTC_TZ)
            _seed_calendar(db_path, [
                EconomicEvent(title="Non-Farm Employment Change", country="USD", impact="High",
                               event_time_utc=event_time, forecast="55K", previous="-23K", actual="162K"),
                EconomicEvent(title="Average Hourly Earnings m/m", country="USD", impact="High",
                               event_time_utc=event_time, forecast="0.3%", previous="0.1%", actual="0.3%"),
                EconomicEvent(title="Unemployment Rate", country="USD", impact="High",
                               event_time_utc=event_time, forecast="4.1%", previous="4.1%", actual="4.1%"),
                EconomicEvent(title="PPI m/m", country="USD", impact="High",
                               event_time_utc=solo_event_time, forecast="0.2%", previous="0.1%", actual=None),
            ])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "US30")
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            # Real recorded values from this exact live occurrence.
            backtest_store.record_prediction(
                bconn, "Non-Farm Employment Change", "US30", event_time,
                0.4697793269246527, "bullish", 0.5314798614615047, 136, False,
            )
            backtest_store.record_prediction(
                bconn, "Average Hourly Earnings m/m", "US30", event_time,
                0.46705663115758544, "bullish", 0.536405991676083, 136, False,
            )
            backtest_store.record_prediction(
                bconn, "Unemployment Rate", "US30", event_time,
                0.4495123783660442, "bearish", 0.3705108141070306, 90, False,
            )
            backtest_store.record_prediction(
                bconn, "PPI m/m", "US30", solo_event_time,
                0.65, "bullish", 0.40, 50, False,
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            by_title = {e["event_title"]: e for e in events}

            # All three co-released titles get the SAME conflict marker,
            # regardless of which one the existing sort would otherwise
            # feature -- and article_prediction is nulled out on every one.
            for title in ["Non-Farm Employment Change", "Average Hourly Earnings m/m", "Unemployment Rate"]:
                assert by_title[title]["article_prediction"] is None, f"{title} should be nulled on conflict"
                assert by_title[title]["article_prediction_conflict"] is not None
                assert set(by_title[title]["article_prediction_conflict"]["titles"]) == {
                    "Non-Farm Employment Change", "Average Hourly Earnings m/m", "Unemployment Rate",
                }

            # The solo event (no co-released siblings) is completely untouched.
            assert by_title["PPI m/m"]["article_prediction"]["direction"] == "bullish"
            assert by_title["PPI m/m"]["article_prediction_conflict"] is None
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_webapp_app.py -k test_predictions_route_flags_co_released_conflict -v`
Expected: FAIL — `article_prediction_conflict` KeyError (field doesn't exist yet), or all three titles keep their own independent (non-conflicting-looking) `article_prediction` values.

- [ ] **Step 3: Write the implementation**

In `webapp/app.py`, add the import (alongside the existing `webapp.history`/`webapp.trend` imports near the top of the file):

```python
from webapp.reconciliation import reconcile_group
```

Inside `get_predictions()`, after the existing `for ticker in symbols:` loop's inner `for event in events:` loop finishes building `entry["events"]` (i.e., immediately after the loop that ends at the `entry["events"].append({...})` call, `webapp/app.py:411-425`, and BEFORE the existing `entry["events"].sort(key=_sort_key)` at `webapp/app.py:472`), track each event's raw `accumulator_prediction` alongside the entry it belongs to, then reconcile:

Change the top of the `for ticker in symbols:` loop body to also initialize a side-tracking dict:

```python
        entry = {"symbol": ticker, "symbol_class": symbol_class.symbol_class, "events": []}
        accumulator_predictions_by_time_and_title: dict[str, dict[str, "Prediction"]] = {}
```

(`Prediction` here is `scoring.backtest_store.Prediction` — add `Prediction` to the existing `from scoring.backtest_store import (...)` block at the top of `webapp/app.py` if it isn't already imported there; it's only needed for the type hint, not runtime behavior.)

Inside the `for event in events:` loop, right after the existing `accumulator_prediction = accumulator_runs[0] if accumulator_runs else None` line (`webapp/app.py:323`), record it into the side dict:

```python
            accumulator_predictions_by_time_and_title.setdefault(event["event_time_utc"], {})
            if accumulator_prediction is not None:
                accumulator_predictions_by_time_and_title[event["event_time_utc"]][event["title"]] = accumulator_prediction
```

Then, after the `for event in events:` loop ends and before `entry["events"].sort(key=_sort_key)`, run reconciliation:

```python
        for time_key, predictions_by_title in accumulator_predictions_by_time_and_title.items():
            if len(predictions_by_title) < 2:
                continue
            try:
                reconciled = reconcile_group(predictions_by_title)
            except Exception as exc:  # noqa: BLE001 — a reconciliation bug must not crash the whole route
                print(f"[webapp.app] WARNING: reconciliation failed for {time_key}: {exc}")
                continue
            if reconciled is None:
                continue
            for ev in entry["events"]:
                if ev["event_time_utc"] != time_key:
                    continue
                if reconciled.conflict:
                    ev["article_prediction"] = None
                    ev["article_prediction_conflict"] = {"titles": reconciled.conflicting_titles}
                else:
                    ev["article_prediction"] = {
                        "direction": reconciled.prediction.direction,
                        "probability": reconciled.prediction.probability,
                        "article_count": reconciled.prediction.article_count,
                        "top_contributions": reconciled.prediction.top_contributions,
                    }
                    ev["article_prediction_conflict"] = None
```

Finally, every `entry["events"].append({...})` dict (`webapp/app.py:411-425`) needs the new field present by default (so events with no co-released group — the common case — still carry a consistent, always-present `article_prediction_conflict: None` rather than a key that's sometimes missing):

```python
            entry["events"].append({
                "event_title": event["title"],
                "event_time_utc": event["event_time_utc"],
                "probability": probability_value,
                "direction": direction_value,
                "recomputed_from_event_history": recomputed is not None,
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
                "article_count": accumulator_prediction.article_count if accumulator_prediction else None,
                "article_prediction": article_prediction,
                "article_prediction_conflict": None,
                "previous_article_prediction": previous_article_prediction,
                "print_prediction": print_prediction,
                "trend_signal": trend_signal,
                "kalshi_read": kalshi_read,
            })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_webapp_app.py -v`
Expected: all pass, including the new `test_predictions_route_flags_co_released_conflict_and_leaves_singleton_events_alone`.

- [ ] **Step 5: Run the FULL test suite to check for regressions**

Run: `python -m pytest -q`
Expected: same pass count as before this task plus the new tests, no new failures. (One pre-existing, unrelated FinBERT-environment test failure — `test_redundancy_discount_works_across_sentiment_tiers_not_just_lexicon` — is expected and NOT a regression from this work; confirm it's the only failure, if any.)

- [ ] **Step 6: Commit**

```bash
git add webapp/app.py tests/test_webapp_app.py
git commit -m "feat: reconcile contradictory co-released accumulator calls in /api/predictions"
```

---

### Task 3: Frontend conflict badge

**Files:**
- Modify: `webapp/static/app.js`
- Modify: `webapp/static/style.css`

**Interfaces:**
- Consumes: the new `article_prediction_conflict` field on each `events[]` entry from `/api/predictions` (Task 2) — shape `{"titles": [string, ...]} | null`.
- Produces: nothing consumed elsewhere in this plan — this is the terminal, user-visible piece.

- [ ] **Step 1: Modify `articlePredictionHtml` call site and add the conflict renderer**

In `webapp/static/app.js`, locate the existing `articlePredictionHtml` function and its call site (`webapp/static/app.js:288-306`). Add a new function immediately after `articlePredictionHtml`'s closing brace, and change how `articlePredictionLine` is built:

```javascript
  // article_prediction_conflict (2026-09-04): set when co-released
  // titles (same event_time_utc, e.g. NFP + Unemployment Rate + AHE
  // from one BLS report) did NOT unanimously agree on direction for
  // this instrument -- webapp/reconciliation.py's reconcile_group()
  // requires every non-neutral co-released title to point the same way;
  // even one real dissenter is a conflict, no confidence contest
  // decides a winner. Renders as a distinct warning state, never as "no
  // data" (the plain absent-article_prediction case) and never as a
  // real directional read -- a contradictory signal is worth
  // surfacing, not hiding or silently resolving.
  function articlePredictionConflictHtml(conflict) {
    if (!conflict) return '';
    const titles = conflict.titles.map(escapeHtml).join(', ');
    return `<div class="article-prediction-conflict">
      ⚠ Conflicting signals across co-released events
      <span style="font-size:12px;color:#888">(${titles})</span>
    </div>`;
  }
  const articlePredictionLine = next.article_prediction
    ? articlePredictionHtml(next.article_prediction, next.previous_article_prediction)
    : articlePredictionConflictHtml(next.article_prediction_conflict);
```

- [ ] **Step 2: Add the CSS rule**

In `webapp/static/style.css`, add immediately after the existing `.bull-bear-scale` rule (`webapp/static/style.css:82`, right before the `.other-events` block added earlier the same day):

```css
.article-prediction-conflict { margin-top: 8px; padding: 8px 10px; border-radius: 8px; font-size: 13px; text-align: center; background: rgba(255, 152, 0, 0.12); border: 1px solid rgba(255, 152, 0, 0.4); color: #ef6c00; }
```

(Same amber warning palette as the existing `.diff-strip.reversed` rule at `webapp/static/style.css:63` — this codebase's established "something needs a second look" color, not the bullish/bearish/neutral palette, since a conflict is neither of those.)

- [ ] **Step 3: Verify live in the browser**

Since this codebase has no JS/CSS automated test suite (confirmed by this plan's File Structure section — everything else in this plan has a `.py` test file, this task doesn't), verify by hand, matching the exact pattern used to verify `otherEventsHtml()` earlier the same day (2026-09-04, "N more events at this time" feature):

1. Ensure the dev server is running (this project's already-running supervised `webapp/app.py` instance, or `preview_start` against `.claude/launch.json` if none is running).
2. Navigate to the dashboard's root page.
3. Confirm the US30 card (given the real 2026-09-04 data already in this project's live database from earlier the same day — Non-Farm Employment Change/Average Hourly Earnings m/m/Unemployment Rate, all bullish/bullish/bearish) now shows the amber "⚠ Conflicting signals" badge instead of a bullish or bearish 📰 article-based read line.
4. Confirm the XAUUSD card for the same moment — check whether XAUUSD's own three calls agree or conflict (they may differ from US30's outcome, since reconciliation runs independently per instrument) and confirm the badge only appears if XAUUSD's own group is genuinely a conflict.
5. Confirm an unrelated, non-co-released event elsewhere on the page still shows its plain, un-conflicted 📰 article-based read line exactly as before this change.
6. Take a screenshot as evidence.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/app.js webapp/static/style.css
git commit -m "feat: render a conflict badge for co-released events with contradictory accumulator calls"
```

---

### Task 4: Final verification against the Global Constraints

**Files:** none created or modified — this task is a verification pass, no code changes expected.

**Interfaces:** none.

- [ ] **Step 1: Confirm History tab is unaffected**

Run: `python -m pytest tests/test_webapp_history.py -v`
Expected: all pass, unchanged from before this plan (this file was not modified by any task above — this step exists to catch an accidental import-order or shared-state regression, not because any task touched it).

- [ ] **Step 2: Confirm essence-only scoring is unaffected**

Run: `git diff --stat HEAD~3 -- webapp/scoring_service.py scoring/probability_engine.py scoring/backtest_store.py`
Expected: empty output — zero lines changed in any of these three files across every commit this plan made. (This plan produces exactly 3 commits — Task 1, Task 2, Task 3 — so `HEAD~3` is the commit right before Task 1's; adjust the number only if a task above ended up split into more than one commit.)

- [ ] **Step 3: Run the full test suite one final time**

Run: `python -m pytest -q`
Expected: same known-good pass count as Task 2 Step 5, no new failures.

- [ ] **Step 4: No commit needed for this task** — it's verification only. If Step 2 finds an unexpected diff in a forbidden file, STOP and treat it as a plan violation to fix before considering this plan complete, not something to wave through.
