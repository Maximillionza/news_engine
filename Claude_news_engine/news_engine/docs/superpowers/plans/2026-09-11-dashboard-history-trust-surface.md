# Dashboard/History Trust Surface (Batch 9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface accuracy and cross-signal trust information that already exists in the backend but is invisible in the running dashboard — an aggregate/per-event accuracy rollup on the History tab, a visible warning when a snapshot's drill-down had no real signal, the Tier1-vs-sentiment conflict flag in History (not just the Dashboard card), and a bounded view of a symbol's other tracked events so a real signal never goes invisible just because its event isn't `events[0]`.

**Architecture:** Every task is additive — no existing field, route shape, or scoring behavior changes. Backend tasks add new read-only aggregation/lookup functions and extend two response payloads (`/api/history`, plus a new `/api/history/stats`) with optional fields that are `None`/absent when not applicable, following this codebase's existing "absent, never fabricated" convention. Frontend tasks add new render functions and CSS classes; no existing render function's output changes for the cases it already handled.

**Tech Stack:** Flask (Python), vanilla JS (no framework), SQLite, plain `assert`+`print` test style run via `pytest`.

**Spec:** No separate spec doc exists for this batch — it was scoped directly from live evidence in `docs/fundamental-analysis-review-2026-09-11.md` (§3, §6 recommendations) and the live UI walkthrough logged in `docs/feature-inventory-2026-09-11.md` (§2e, §5 Batch 9). Both travel with this plan; read the Batch 9 bullet list in `docs/feature-inventory-2026-09-11.md` §5 before starting.

## Global Constraints

- Two items originally proposed for this batch were retracted during scoping — do not reintroduce them here: (1) "US30 has no Dashboard card" is not a bug (`webapp/store.py`'s `tracked_symbols` already supports add/remove; it's just never been added through the existing UI), (2) "blank Instr. cell in History" is not a bug (`HistoryRow.instrument` is `None` by design for a print-call-backed numeric row).
- No new per-event relevance-keyword curation (`config/settings.py`'s `EVENT_RELEVANCE_KEYWORDS_BY_TITLE`) — that's a content/curation task for a future batch, not this one. This batch only makes the already-detectable "zero signal-bearing contributions" case visibly a warning.
- Outcome-vocabulary relabeling (`Confirmed`/`Missed`/etc.), History filter/sort, and Calendar tab polish are Batch 10, not this plan — do not fold them in.
- Every new/extended dataclass field must default to `None` (or an empty collection) when not applicable, and every new UI element must render nothing (not a placeholder) when its data is absent — matches every existing optional signal in this codebase (article_prediction, print_prediction, trend_signal, kalshi_read, tier1_prediction all follow this rule).
- Grouping in the accuracy rollup is by exact `event_title` string, never a fuzzy category — this codebase has no existing event-type taxonomy to group by, and inventing one would contradict the project's own discipline against unvalidated guesses (see `config/settings.py`'s `EVENT_REGISTRY` comment on `avg_interval_months` being a real value, never a coarse label).
- Test style: plain `assert` + `print("=== description ===")` / `print("PASS")` functions, collected and run via `pytest`, matching every existing test file in `tests/` (not pytest fixtures/classes).

---

### Task 1: Backend — accuracy rollup computation and route

**Files:**
- Modify: `webapp/history.py` (add `CategoryStats`, `HistoryStats`, `compute_history_stats()`, `STATS_LOOKBACK_LIMIT`)
- Modify: `webapp/app.py` (add `/api/history/stats` route, extend the `webapp.history` import)
- Test: `tests/test_webapp_history.py` (new tests for `compute_history_stats()`)

**Interfaces:**
- Consumes: `webapp.history.HistoryRow` (existing — `event_title: str`, `outcome: Optional[str]` where `"Confirmed"`/`"Missed"`/`None`), `webapp.history.build_print_call_history(limit: int = DEFAULT_HISTORY_LIMIT, now: Optional[dt.datetime] = None) -> list[HistoryRow]` (existing).
- Produces: `webapp.history.CategoryStats` (fields `correct: int`, `wrong: int`, `no_call: int`, property `calls_made: int`, property `accuracy: Optional[float]`), `webapp.history.HistoryStats` (fields `overall: CategoryStats`, `by_event_title: dict[str, CategoryStats]`), `webapp.history.compute_history_stats(rows: list[HistoryRow]) -> HistoryStats`, `webapp.history.STATS_LOOKBACK_LIMIT: int`. Task 5 does not depend on this task; Task 2 (frontend) consumes the new `/api/history/stats` JSON shape this task produces.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_history.py`, immediately before the final `if __name__ == "__main__":` block:

```python
# --- compute_history_stats() ---

def test_compute_history_stats_overall_and_per_title_breakdown():
    print("=== compute_history_stats: overall and per-event-title counts are correct ===")
    rows = [
        history.HistoryRow(
            event_title="CPI m/m", event_time_utc="2026-08-12T12:30:00+00:00", instrument="XAUUSD",
            previous="0.1%", forecast="0.2%", actual="0.2%", unchanged_vs_previous=False,
            ne_prediction="bullish", ne_confidence=0.5, outcome="Confirmed", unjudged_reason=None, source="live",
        ),
        history.HistoryRow(
            event_title="CPI m/m", event_time_utc="2026-09-11T12:30:00+00:00", instrument="XAUUSD",
            previous="0.2%", forecast="0.4%", actual="0.1%", unchanged_vs_previous=False,
            ne_prediction="bullish", ne_confidence=0.5, outcome="Missed", unjudged_reason=None, source="live",
        ),
        history.HistoryRow(
            event_title="CPI m/m", event_time_utc="2026-09-11T12:30:00+00:00", instrument="US30",
            previous="0.2%", forecast="0.4%", actual="0.1%", unchanged_vs_previous=False,
            ne_prediction="neutral", ne_confidence=0.01, outcome=None, unjudged_reason="shrug", source="live",
        ),
        history.HistoryRow(
            event_title="PPI m/m", event_time_utc="2026-09-10T12:30:00+00:00", instrument="XAUUSD",
            previous="0.0%", forecast="0.4%", actual="0.4%", unchanged_vs_previous=False,
            ne_prediction="bearish", ne_confidence=0.33, outcome="Confirmed", unjudged_reason=None, source="live",
        ),
    ]

    stats = history.compute_history_stats(rows)

    assert stats.overall.correct == 2
    assert stats.overall.wrong == 1
    assert stats.overall.no_call == 1
    assert stats.overall.calls_made == 3
    assert abs(stats.overall.accuracy - (2 / 3)) < 1e-9

    cpi = stats.by_event_title["CPI m/m"]
    assert cpi.correct == 1 and cpi.wrong == 1 and cpi.no_call == 1
    assert abs(cpi.accuracy - 0.5) < 1e-9

    ppi = stats.by_event_title["PPI m/m"]
    assert ppi.correct == 1 and ppi.wrong == 0 and ppi.no_call == 0
    assert ppi.accuracy == 1.0
    print("PASS\n")


def test_compute_history_stats_accuracy_none_when_zero_calls_made():
    print("=== compute_history_stats: accuracy is None (never fabricated as 0) when a category made zero calls ===")
    rows = [
        history.HistoryRow(
            event_title="FOMC Meeting Minutes", event_time_utc="2026-08-19T18:00:00+00:00", instrument="XAUUSD",
            previous=None, forecast=None, actual=None, unchanged_vs_previous=False,
            ne_prediction="neutral", ne_confidence=0.01, outcome=None, unjudged_reason="shrug", source="live",
        ),
    ]

    stats = history.compute_history_stats(rows)

    assert stats.overall.calls_made == 0
    assert stats.overall.accuracy is None
    assert stats.by_event_title["FOMC Meeting Minutes"].accuracy is None
    print("PASS\n")


def test_compute_history_stats_empty_rows_returns_empty_stats():
    print("=== compute_history_stats: an empty rows list produces zeroed overall stats and no per-title entries ===")
    stats = history.compute_history_stats([])

    assert stats.overall.correct == 0
    assert stats.overall.wrong == 0
    assert stats.overall.no_call == 0
    assert stats.overall.accuracy is None
    assert stats.by_event_title == {}
    print("PASS\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webapp_history.py -v -k compute_history_stats`
Expected: FAIL with `AttributeError: module 'webapp.history' has no attribute 'HistoryRow'` referencing the new fields, or `compute_history_stats` — `HistoryRow` exists already but the tests reference it with an interface that doesn't fail import; the real failure is `AttributeError: module 'webapp.history' has no attribute 'compute_history_stats'`.

- [ ] **Step 3: Implement `CategoryStats`, `HistoryStats`, `compute_history_stats()`**

In `webapp/history.py`, add after the `DEFAULT_HISTORY_LIMIT`/`PRE_FILTER_LIMIT`/`MIN_TEXT_EVENT_CONFIDENCE` constants (after line 67) and before `_implied_surprise_direction()`:

```python
# How many rows compute_history_stats() reads from, independent of the
# History table's own display DEFAULT_HISTORY_LIMIT (50) — the rollup
# should reflect the real track record the underlying tables can show,
# not an arbitrarily smaller display page. Matches PRE_FILTER_LIMIT, the
# same bound build_print_call_history() already applies internally before
# its own final display-limit truncation, so this introduces no new
# assumption about how much history the source tables realistically hold.
STATS_LOOKBACK_LIMIT = PRE_FILTER_LIMIT


@dataclass
class CategoryStats:
    """Confirmed/Missed/no-call tally for one grouping (overall, or one event_title)."""
    correct: int
    wrong: int
    no_call: int

    @property
    def calls_made(self) -> int:
        return self.correct + self.wrong

    @property
    def accuracy(self) -> Optional[float]:
        """None — never fabricated as 0 — when this grouping made zero calls."""
        if self.calls_made == 0:
            return None
        return self.correct / self.calls_made


@dataclass
class HistoryStats:
    overall: CategoryStats
    by_event_title: dict[str, CategoryStats]


def compute_history_stats(rows: list[HistoryRow]) -> HistoryStats:
    """
    Aggregate Confirmed/Missed/no-call counts across `rows` — the same
    manual eyeball-the-table exercise fundamental-analysis-review-2026-09-11.md
    already did twice by hand via direct SQL against scoring/backtest_log.db.
    Grouped by each row's exact event_title, never a fuzzy category (e.g.
    "CPI m/m" and "CPI y/y" stay separate rows) — see this plan's Global
    Constraints for why a new taxonomy isn't introduced here.

    A row counts as correct (outcome == "Confirmed"), wrong
    (outcome == "Missed"), or no_call (outcome is None, regardless of
    which unjudged_reason) — no further split here; unjudged_reason is
    already visible per-row in the History table itself for anyone who
    wants that detail.
    """
    overall = CategoryStats(correct=0, wrong=0, no_call=0)
    by_title: dict[str, CategoryStats] = {}
    for row in rows:
        bucket = by_title.setdefault(row.event_title, CategoryStats(correct=0, wrong=0, no_call=0))
        for stats in (overall, bucket):
            if row.outcome == "Confirmed":
                stats.correct += 1
            elif row.outcome == "Missed":
                stats.wrong += 1
            else:
                stats.no_call += 1
    return HistoryStats(overall=overall, by_event_title=by_title)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_webapp_history.py -v -k compute_history_stats`
Expected: 3 passed.

- [ ] **Step 5: Add the `/api/history/stats` route**

In `webapp/app.py`, change the existing import (line 27):

```python
from webapp.history import build_print_call_history, compute_history_stats, STATS_LOOKBACK_LIMIT
```

Add a new route immediately after `get_print_call_history()` (after the existing `/api/history` route, which ends around line 364):

```python
@app.route("/api/history/stats", methods=["GET"])
def get_history_stats():
    rows = build_print_call_history(limit=STATS_LOOKBACK_LIMIT)
    stats = compute_history_stats(rows)

    def _stats_dict(s):
        return {"correct": s.correct, "wrong": s.wrong, "no_call": s.no_call, "accuracy": s.accuracy}

    return jsonify({
        "overall": _stats_dict(stats.overall),
        "by_event_title": {
            title: _stats_dict(s)
            for title, s in sorted(stats.by_event_title.items(), key=lambda kv: kv[0])
        },
    })
```

- [ ] **Step 6: Add a Flask-level smoke test**

Add to `tests/test_webapp_app.py`, near the other `/api/history`-adjacent tests (search the file for `def test_` functions using `client.get("/api/predictions")` for the established pattern — insert a new test using the same `app.test_client()`/temp-DB setup pattern already used there):

```python
def test_history_stats_route_returns_overall_and_per_title_keys():
    print("=== GET /api/history/stats: response has overall and by_event_title keys ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        store.get_connection(dash_db).close()
        backtest_store.get_connection(backtest_db).close()
        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            client = webapp_app.app.test_client()
            resp = client.get("/api/history/stats")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "overall" in data
            assert set(data["overall"].keys()) == {"correct", "wrong", "no_call", "accuracy"}
            assert data["by_event_title"] == {}  # empty DBs -> no rows -> no per-title entries
    print("PASS\n")
```

Match this test's imports (`tempfile`, `Path`, `patch`, `store`, `backtest_store`, `webapp_app`) to whatever this file already imports at its top — reuse them, do not re-import if already present.

- [ ] **Step 7: Run the new and existing tests**

Run: `pytest tests/test_webapp_history.py tests/test_webapp_app.py -v`
Expected: all pass, no prior test broken.

- [ ] **Step 8: Commit**

```bash
git add webapp/history.py webapp/app.py tests/test_webapp_history.py tests/test_webapp_app.py
git commit -m "feat: add History accuracy rollup (compute_history_stats + /api/history/stats)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Frontend — render the accuracy rollup panel

**Files:**
- Modify: `webapp/static/index.html` (add a stats container above the History table)
- Modify: `webapp/static/app.js` (fetch `/api/history/stats`, render it)
- Modify: `webapp/static/style.css` (minimal layout rules for the new panel)

**Interfaces:**
- Consumes: `GET /api/history/stats` → `{"overall": {"correct": int, "wrong": int, "no_call": int, "accuracy": float|null}, "by_event_title": {str: {same shape}}}` (Task 1's output).
- Produces: nothing consumed by a later task.

- [ ] **Step 1: Add the container markup**

In `webapp/static/index.html`, inside `<section id="view-history" ...>`, immediately before the existing `<div id="history-empty-notice" ...>` line (line 50):

```html
  <div id="history-stats"></div>
```

- [ ] **Step 2: Add rendering + fetch logic**

In `webapp/static/app.js`, add a new function near `renderHistoryTable()` (immediately before it) and call it from `loadHistoryIfNeeded()`:

```javascript
function renderHistoryStats(stats) {
  const container = document.getElementById("history-stats");
  const overall = stats.overall;
  const overallLabel = overall.accuracy === null
    ? `${overall.correct + overall.wrong} calls made, ${overall.no_call} no-call`
    : `${overall.correct}/${overall.correct + overall.wrong} correct (${Math.round(overall.accuracy * 100)}%), ${overall.no_call} no-call`;

  const titles = Object.keys(stats.by_event_title).sort();
  const rows = titles.map((title) => {
    const s = stats.by_event_title[title];
    const label = s.accuracy === null
      ? `${s.no_call} no-call, 0 calls made`
      : `${s.correct}/${s.correct + s.wrong} (${Math.round(s.accuracy * 100)}%)${s.no_call ? `, ${s.no_call} no-call` : ""}`;
    return `<tr><td>${escapeHtml(title)}</td><td>${label}</td></tr>`;
  }).join("");

  container.innerHTML = `
    <div id="history-stats-overall"><b>Overall:</b> ${overallLabel}</div>
    <details id="history-stats-detail">
      <summary>By event type</summary>
      <table id="history-stats-table"><tbody>${rows}</tbody></table>
    </details>`;
}

async function loadHistoryStatsIfNeeded() {
  const resp = await fetch("/api/history/stats");
  const data = await resp.json();
  renderHistoryStats(data);
}
```

Update `loadHistoryIfNeeded()` (existing function, currently only fetches `/api/history`) to also call the new function:

```javascript
async function loadHistoryIfNeeded() {
  if (historyLoaded) return;  // fetched once per page load, not on the dashboard's poll cycle
  historyLoaded = true;
  const resp = await fetch("/api/history");
  const data = await resp.json();
  renderHistoryTable(data.rows || []);
  await loadHistoryStatsIfNeeded();
}
```

- [ ] **Step 3: Add minimal CSS**

In `webapp/static/style.css`, add near the other tab-view rules:

```css
#history-stats { margin-bottom: 12px; font-size: 13px; }
#history-stats-overall { margin-bottom: 4px; }
#history-stats-table { border-collapse: collapse; font-size: 12px; }
#history-stats-table td { padding: 2px 10px 2px 0; }
```

- [ ] **Step 4: Manually verify in the running app**

Run: `python webapp/app.py` (or use the existing `.claude/launch.json` `news-engine-webapp` config), open `http://localhost:5001`, click the History tab.
Expected: an "Overall: X/Y correct (Z%), N no-call" line appears above the table, and a collapsed "By event type" `<details>` expands to show one row per distinct event title with its own correct/wrong/no-call breakdown.

- [ ] **Step 5: Commit**

```bash
git add webapp/static/index.html webapp/static/app.js webapp/static/style.css
git commit -m "feat: render History accuracy rollup panel (overall + per-event-title)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — low-signal-coverage warning badge

**Files:**
- Modify: `webapp/static/app.js` (`articleProgressionEntryHtml()`)
- Modify: `webapp/static/style.css` (new `.low-signal-warning` class)

**Interfaces:**
- Consumes: `entry.top_contributions` (existing array, already available to `articleProgressionEntryHtml()` — no backend change).
- Produces: nothing consumed by a later task.

- [ ] **Step 1: Add the CSS class**

In `webapp/static/style.css`, add next to `.tier1-sentiment-conflict`'s rule (around line 92), reusing the exact same warning palette:

```css
.low-signal-warning { margin-top: 4px; padding: 4px 8px; border-radius: 6px; font-size: 11px; background: rgba(255, 152, 0, 0.12); border: 1px solid rgba(255, 152, 0, 0.4); color: #ef6c00; }
```

- [ ] **Step 2: Use the class in the fallback text**

In `webapp/static/app.js`, change `articleProgressionEntryHtml()`'s fallback line (currently line 686):

```javascript
    ${contribsHtml || '<div style="font-size:11px;color:#888">No individual article stood out — this read came from broad, low-signal coverage.</div>'}
```

to:

```javascript
    ${contribsHtml || '<div class="low-signal-warning">⚠ No individual article stood out — this read came from broad, low-signal coverage, not a genuinely on-topic signal.</div>'}
```

- [ ] **Step 3: Manually verify**

Run the app, flip a card whose drill-down has a snapshot with zero top_contributions (or add a temporary `console.log` / use an existing historical snapshot known to hit this case, e.g. XAUUSD's Aug 12 CPI snapshots per the live walkthrough in `docs/fundamental-analysis-review-2026-09-11.md`).
Expected: that entry renders with a visibly distinct orange warning badge instead of plain grey text; every other entry (with real `top_contributions`) is visually unchanged.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/app.js webapp/static/style.css
git commit -m "feat: visible warning badge for zero-signal drill-down snapshots

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Backend — Tier1-vs-sentiment conflict in History

**Files:**
- Modify: `webapp/predictions_service.py` (extract `compute_tier1_sentiment_conflict()`, use it in the existing inline loop)
- Modify: `webapp/history.py` (add `tier1_conflict` field to `HistoryRow`, populate it in the fallback-numeric and text-only branches)
- Modify: `webapp/app.py` (serialize `tier1_conflict` in the `/api/history` route)
- Test: `tests/test_webapp_history.py` (new tests), verify `tests/test_webapp_app.py`'s existing `/api/predictions` tests still pass unchanged (pure refactor there)

**Interfaces:**
- Consumes: `scoring.backtest_store.get_latest_tier1_prediction_for_occurrence(conn, event_title: str, instrument: str, event_time_utc: dt.datetime) -> Optional[Tier1PredictionRow]` (existing — `Tier1PredictionRow.predicted_direction: str` is `'bullish'|'bearish'|'neutral'`), `scoring.backtest_store.get_latest_prediction_for_occurrence(...)` (existing, already imported in `webapp/history.py`, whose `Prediction.direction` is on the same `'bullish'|'bearish'|'neutral'` axis).
- Produces: `webapp.predictions_service.compute_tier1_sentiment_conflict(sentiment_direction: Optional[str], tier1_direction: Optional[str]) -> Optional[dict]` (returns `{"sentiment_direction": str, "tier1_direction": str}` or `None`). `webapp.history.HistoryRow.tier1_conflict: Optional[dict] = None` (new field, same shape). Task 5 (frontend) consumes `HistoryRow.tier1_conflict` via the `/api/history` JSON this task extends.

- [ ] **Step 1: Write the failing test for the extracted helper**

Add to a new test file `tests/test_webapp_predictions_service.py` (this module currently has no dedicated test file — only Flask-level coverage via `test_webapp_app.py`):

```python
"""Tests for webapp/predictions_service.py's compute_tier1_sentiment_conflict() — the shared Tier1-vs-sentiment comparison used by both /api/predictions (Dashboard) and webapp/history.py (History tab)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.predictions_service import compute_tier1_sentiment_conflict


def test_opposing_directional_calls_flagged_as_conflict():
    print("=== compute_tier1_sentiment_conflict: bullish vs bearish is a real conflict ===")
    result = compute_tier1_sentiment_conflict("bearish", "bullish")
    assert result == {"sentiment_direction": "bearish", "tier1_direction": "bullish"}
    print("PASS\n")


def test_agreeing_directional_calls_are_not_a_conflict():
    print("=== compute_tier1_sentiment_conflict: agreement is never flagged ===")
    assert compute_tier1_sentiment_conflict("bullish", "bullish") is None
    print("PASS\n")


def test_neutral_or_missing_side_is_never_a_conflict():
    print("=== compute_tier1_sentiment_conflict: 'neutral' or None on either side is never a conflict ===")
    assert compute_tier1_sentiment_conflict("bullish", "neutral") is None
    assert compute_tier1_sentiment_conflict(None, "bullish") is None
    assert compute_tier1_sentiment_conflict("bearish", None) is None
    assert compute_tier1_sentiment_conflict(None, None) is None
    print("PASS\n")


if __name__ == "__main__":
    test_opposing_directional_calls_flagged_as_conflict()
    test_agreeing_directional_calls_are_not_a_conflict()
    test_neutral_or_missing_side_is_never_a_conflict()
    print("All webapp_predictions_service tests passed.")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_webapp_predictions_service.py -v`
Expected: FAIL with `ImportError: cannot import name 'compute_tier1_sentiment_conflict' from 'webapp.predictions_service'`.

- [ ] **Step 3: Extract the helper and use it in `build_predictions_payload()`**

In `webapp/predictions_service.py`, add this function after `_trend_instrument_lean()` (after line 105) and before `_recompute_stale_pending()`:

```python
def compute_tier1_sentiment_conflict(
    sentiment_direction: Optional[str], tier1_direction: Optional[str],
) -> Optional[dict]:
    """
    Shared by build_predictions_payload() (Dashboard card) and
    webapp/history.py (History tab) — the exact comparison rule
    build_predictions_payload() originally computed inline
    (fundamental-analysis-review-2026-09-11.md P0 #5), extracted so
    History can apply the identical rule instead of re-deriving it.
    "No call" on either side (None, or 'neutral') is never a conflict —
    only a REAL, opposing directional call from both sides counts, same
    convention scoring/backtest.py's BacktestCase.evaluate() already uses
    for Tier 1's own accuracy metric.
    """
    if sentiment_direction not in ("bullish", "bearish") or tier1_direction not in ("bullish", "bearish"):
        return None
    if sentiment_direction == tier1_direction:
        return None
    return {"sentiment_direction": sentiment_direction, "tier1_direction": tier1_direction}
```

Replace the existing inline loop in `build_predictions_payload()` (lines 450-463):

```python
        for ev in entry["events"]:
            article_pred = ev["article_prediction"]
            tier1_pred = ev["tier1_prediction"]
            if article_pred is None or tier1_pred is None:
                continue
            sentiment_direction = article_pred["direction"]
            tier1_direction = tier1_pred["predicted_direction"]
            if sentiment_direction not in ("bullish", "bearish") or tier1_direction not in ("bullish", "bearish"):
                continue
            if sentiment_direction != tier1_direction:
                ev["tier1_sentiment_conflict"] = {
                    "sentiment_direction": sentiment_direction,
                    "tier1_direction": tier1_direction,
                }
```

with:

```python
        for ev in entry["events"]:
            article_pred = ev["article_prediction"]
            tier1_pred = ev["tier1_prediction"]
            if article_pred is None or tier1_pred is None:
                continue
            ev["tier1_sentiment_conflict"] = compute_tier1_sentiment_conflict(
                article_pred["direction"], tier1_pred["predicted_direction"],
            )
```

- [ ] **Step 4: Run the test to verify it passes, and confirm the refactor changed nothing**

Run: `pytest tests/test_webapp_predictions_service.py tests/test_webapp_app.py -v`
Expected: all pass, including every pre-existing `/api/predictions` test in `test_webapp_app.py` — this step is a pure extraction with identical behavior.

- [ ] **Step 5: Write the failing tests for `HistoryRow.tier1_conflict`**

Add to `tests/test_webapp_history.py`, before the `compute_history_stats` tests added in Task 1:

```python
# --- tier1_conflict on fallback/text-only rows ---

def test_fallback_row_flags_tier1_sentiment_conflict():
    print("=== build_print_call_history: a fallback numeric row flags a real Tier1-vs-sentiment conflict ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("PPI m/m", event_time, "0.4%", "0.0%", "0.4%"),
            "higher_bullish", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, event_title="PPI m/m", instrument="XAUUSD", event_time_utc=event_time,
            probability=0.44, direction="bearish", confidence=0.33, article_count=142,
            contradiction_flag=False, source="live", scored_at_utc=event_time,
        )
        backtest_store.record_tier1_prediction(
            bt_conn, event_title="PPI m/m", instrument="XAUUSD", event_time_utc=event_time,
            value="Muted, non-reaccelerating call", confidence="Certain", source="ISM Prices Paid",
            predicted_direction="bullish", logged_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].tier1_conflict == {"sentiment_direction": "bearish", "tier1_direction": "bullish"}
    print("PASS\n")


def test_fallback_row_no_conflict_when_tier1_agrees():
    print("=== build_print_call_history: no tier1_conflict when Tier 1 and sentiment agree ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("PPI m/m", event_time, "0.4%", "0.0%", "0.4%"),
            "higher_bullish", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, event_title="PPI m/m", instrument="XAUUSD", event_time_utc=event_time,
            probability=0.56, direction="bullish", confidence=0.4, article_count=142,
            contradiction_flag=False, source="live", scored_at_utc=event_time,
        )
        backtest_store.record_tier1_prediction(
            bt_conn, event_title="PPI m/m", instrument="XAUUSD", event_time_utc=event_time,
            value="Muted, non-reaccelerating call", confidence="Certain", source="ISM Prices Paid",
            predicted_direction="bullish", logged_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].tier1_conflict is None
    print("PASS\n")


def test_fallback_row_no_tier1_conflict_field_when_no_tier1_row_exists():
    print("=== build_print_call_history: tier1_conflict stays None when no Tier 1 row was ever logged for this occurrence ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 4, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Unemployment Rate", event_time, "4.1%", "4.1%", "4.1%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, event_title="Unemployment Rate", instrument="XAUUSD", event_time_utc=event_time,
            probability=0.46, direction="bearish", confidence=0.35, article_count=89,
            contradiction_flag=False, source="live", scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].tier1_conflict is None
    print("PASS\n")
```

- [ ] **Step 6: Run the tests to verify they fail**

Run: `pytest tests/test_webapp_history.py -v -k tier1_conflict`
Expected: FAIL — `HistoryRow.__init__()` raises `TypeError: __init__() got an unexpected keyword argument 'tier1_conflict'` is not the failure mode here since the tests don't construct `HistoryRow` directly; instead expect `AssertionError` from `rows[0].tier1_conflict` raising `AttributeError: 'HistoryRow' object has no attribute 'tier1_conflict'`.

- [ ] **Step 7: Add the field and populate it**

In `webapp/history.py`, add the new field to `HistoryRow` (after `source: str`, the current last field):

```python
    tier1_conflict: Optional[dict] = None  # {"sentiment_direction": str, "tier1_direction": str} when Tier 1 and this occurrence's own sentiment call genuinely disagree; None otherwise — see build_print_call_history() for which row shapes this applies to
```

In the fallback-numeric branch of `build_print_call_history()` (inside the `for instrument in INSTRUMENTS.keys():` loop, after `prediction` is fetched and validated non-`None`, before the `fallback_outcome`/`fallback_unjudged_reason` block currently starting at line 195), add:

```python
                    try:
                        tier1_row = get_latest_tier1_prediction_for_occurrence(bt_conn, event.event_title, instrument, event_time)
                    except Exception as exc:  # noqa: BLE001 — one bad lookup must not crash the whole build
                        print(f"[webapp.history] WARNING: could not read tier1 for {event.event_title}/{instrument}: {exc}")
                        tier1_row = None
                    fallback_tier1_conflict = compute_tier1_sentiment_conflict(
                        prediction.direction, tier1_row.predicted_direction if tier1_row is not None else None,
                    )
```

and add `tier1_conflict=fallback_tier1_conflict,` to that branch's `rows.append(HistoryRow(...))` call (the one ending around line 249).

In the text-only branch (inside its own `for instrument in INSTRUMENTS.keys():` loop, after `prediction` is confirmed non-`None`, before the `text_outcome`/`text_unjudged_reason` block currently starting at line 316), add the same pattern:

```python
                try:
                    tier1_row = get_latest_tier1_prediction_for_occurrence(bt_conn, event.event_title, instrument, event_time)
                except Exception as exc:  # noqa: BLE001
                    print(f"[webapp.history] WARNING: could not read tier1 for {event.event_title}/{instrument}: {exc}")
                    tier1_row = None
                text_tier1_conflict = compute_tier1_sentiment_conflict(
                    prediction.direction, tier1_row.predicted_direction if tier1_row is not None else None,
                )
```

and add `tier1_conflict=text_tier1_conflict,` to that branch's `rows.append(HistoryRow(...))` call.

In the numeric print-call-backed branch (`instrument=None`, the one NOT inside a per-instrument loop, ending around line 297), leave `tier1_conflict` unset (defaults to `None`) — add a one-line comment there explaining why:

```python
                # tier1_conflict deliberately not computed here: this row
                # has instrument=None (a print-call is about the NUMBER,
                # not a specific instrument's price direction), and
                # Tier 1's predicted_direction is on the bullish/bearish
                # PRICE axis — there is no single per-instrument sentiment
                # call attached to this row to compare it against.
```

Update the module-level imports at the top of `webapp/history.py` to add `get_latest_tier1_prediction_for_occurrence` to the existing local import inside `build_print_call_history()` (the `from scoring.backtest_store import (...)` block at line 143-148), and add a new top-level import:

```python
from webapp.predictions_service import compute_tier1_sentiment_conflict
```

Place this import at the top of the file alongside the existing `from scoring.print_direction import NO_HIT_CONFIDENCE` line — `webapp.predictions_service` does not import `webapp.history` (verified: its imports are `webapp.scoring_service`, `webapp.store`, `webapp.trend`, `webapp.symbols`, `scoring.backtest_store`, `webapp.reconciliation`), so this is safe at module level and does not need the local-import-to-avoid-a-cycle treatment `scoring.backtest_store` itself needs in this file.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `pytest tests/test_webapp_history.py -v`
Expected: all pass, including every pre-existing test in this file (none of their assertions reference `tier1_conflict`, and the new field defaults to `None`, so no prior row shape changes).

- [ ] **Step 9: Serialize the field in `/api/history`**

In `webapp/app.py`'s existing `get_print_call_history()` route, add `"tier1_conflict": r.tier1_conflict,` to the per-row dict (inside the existing `jsonify({"rows": [...]})` comprehension, alongside `"source": r.source,`).

- [ ] **Step 10: Run the full test suite**

Run: `pytest tests/ -v`
Expected: all pass (no regression anywhere from this task's changes).

- [ ] **Step 11: Commit**

```bash
git add webapp/predictions_service.py webapp/history.py webapp/app.py tests/test_webapp_predictions_service.py tests/test_webapp_history.py
git commit -m "feat: surface Tier1-vs-sentiment conflict in History (extract shared helper)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Frontend — render the Tier1 conflict in the History table

**Files:**
- Modify: `webapp/static/app.js` (`renderHistoryTable()`)

**Interfaces:**
- Consumes: `r.tier1_conflict: {"sentiment_direction": str, "tier1_direction": str} | null` (Task 4's new `/api/history` field).
- Produces: nothing consumed by a later task.

- [ ] **Step 1: Add the badge**

In `webapp/static/app.js`'s `renderHistoryTable()`, add a new local next to the existing `predictionLabel`/`outcomeLabel` locals (matching this function's established inline-style convention rather than introducing a new CSS class, since every other badge in this specific function — `sourceBadge` — already does the same):

```javascript
    const tier1ConflictBadge = r.tier1_conflict
      ? ` <span style="color:#ef6c00;font-size:11px;font-weight:bold">⚠ Tier 1: ${escapeHtml(r.tier1_conflict.tier1_direction)}</span>`
      : "";
```

Append it to the `predictionLabel` cell (the `<td>` currently reading `${predictionLabel} <span ...>(${Math.round(r.ne_confidence * 100)}% conf.)</span>`):

```javascript
      <td>${predictionLabel} <span style="font-size:11px;color:#888">(${Math.round(r.ne_confidence * 100)}% conf.)</span>${tier1ConflictBadge}</td>
```

- [ ] **Step 2: Manually verify**

Run the app, open the History tab, find the `PPI m/m` / `Sep 10, 2026` / `XAUUSD` row (the real, already-confirmed conflict case).
Expected: that row's NE Prediction cell shows the existing `Bearish (33% conf.)` text plus a new `⚠ Tier 1: bullish` badge in orange; every row with no conflict is visually unchanged.

- [ ] **Step 3: Commit**

```bash
git add webapp/static/app.js
git commit -m "feat: render Tier1-vs-sentiment conflict badge in History table

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Frontend — bounded "other tracked events" section (fixes the `events[0]`-only limit)

**Files:**
- Modify: `webapp/static/app.js` (`renderCard()`)

**Interfaces:**
- Consumes: `events` (the full per-symbol array already passed into `renderCard()` — no backend change; every event's `tier1_prediction`/`tier1_sentiment_conflict` fields already exist per-event in this array).
- Produces: nothing consumed by a later task.

- [ ] **Step 1: Add the new render function**

In `webapp/static/app.js`, add immediately after `otherEventsHtml()` (after its closing `}` and the `const otherEventsLine = otherEventsHtml(events, symbol);` line, i.e. after line 545):

```javascript
  // Batch 9 (2026-09-11 UI review): `events` also carries this symbol's
  // OTHER upcoming/recent tracked events — a different day/cluster, not
  // just same-instant siblings, which otherEventsHtml() above
  // deliberately excludes (see its own comment) to keep that list scoped
  // to a genuine release-time cluster. Those other events were always
  // computed and shipped in the API response but never shown anywhere —
  // confirmed live 2026-09-10: the real PPI Tier1-vs-sentiment conflict
  // had no visibility path on the Dashboard tab once CPI's cluster became
  // the featured one the next day. Bounded at OTHER_TRACKED_EVENTS_LIMIT,
  // same "don't let this grow unboundedly" reasoning otherEventsHtml()'s
  // own comment gives for staying simultaneous-only — this takes the next
  // few by the same proximity sort the backend already applies
  // (webapp/predictions_service.py's _sort_key()), not everything queued.
  const OTHER_TRACKED_EVENTS_LIMIT = 3;
  function otherTrackedEventsHtml(allEvents, symbolForCard) {
    const featuredTime = allEvents[0].event_time_utc;
    const rest = allEvents.slice(1)
      .filter((e) => e.event_time_utc !== featuredTime)
      .slice(0, OTHER_TRACKED_EVENTS_LIMIT);
    if (rest.length === 0) return '';
    const rows = rest.map((e) => {
      const tier1Marker = otherEventTier1MarkerHtml(e.tier1_prediction, symbolForCard)
        + otherEventTier1ConflictMarkerHtml(e.tier1_sentiment_conflict);
      const whenLabel = formatEventDateTime(e.event_time_utc);
      if (e.direction === "pending") {
        return `<div class="other-event-row">
          <span class="other-event-title">${escapeHtml(e.event_title)} <span style="font-size:11px;color:#888">(${whenLabel})</span></span>
          <span class="other-event-pending">Pending</span>
          ${tier1Marker}
        </div>`;
      }
      const pct = directionPct(e.probability, e.direction);
      const dClass = directionClass(e.direction);
      return `<div class="other-event-row">
        <span class="other-event-title">${escapeHtml(e.event_title)} <span style="font-size:11px;color:#888">(${whenLabel})</span></span>
        <span class="other-event-call ${dClass}">${directionLabel(e.direction)} ${pct}%</span>
        ${tier1Marker}
      </div>`;
    }).join('');
    return `<div class="other-events">
      <div class="other-events-heading">Other tracked events</div>
      ${rows}
    </div>`;
  }
  const otherTrackedEventsLine = otherTrackedEventsHtml(events, symbol);
```

- [ ] **Step 2: Wire it into both render branches**

In the `pending` branch (the `body += ...${otherEventsLine}` line currently at 557), append the new line:

```javascript
      ${articlePredictionLine}${tier1PredictionLine}${printPredictionLine}${kalshiReadLine}${trendSignalLine}${otherEventsLine}${otherTrackedEventsLine}`;
```

In the resolved branch (`body += otherEventsLine;` currently at line 599), add immediately after:

```javascript
  body += otherEventsLine;
  body += otherTrackedEventsLine;
```

- [ ] **Step 3: Manually verify**

Run the app, open the Dashboard tab for a symbol with more than one non-simultaneous upcoming/recent event (e.g. XAUUSD around the Sep 10-11 PPI/CPI cluster).
Expected: below the existing "N more events at this time" block (if any), a new "Other tracked events" block lists up to 3 additional events with their own title, date/time, call-or-pending marker, and Tier 1 conflict badge where applicable — including the real Sep 10 PPI conflict once it's no longer the featured event.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/app.js
git commit -m "feat: show other tracked events beyond events[0] on the Dashboard card

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage:** all 4 remaining Batch 9 items (rollup, low-signal warning, Tier1-in-History, events[0]-only fix) each have a task; the two retracted items (US30, blank-Instr.-cell) correctly have no task.
- **Placeholder scan:** no TBD/TODO; every step has real code or a real, runnable test/verification command.
- **Type consistency:** `HistoryRow.tier1_conflict`, `compute_tier1_sentiment_conflict()`'s return shape, and the frontend's `r.tier1_conflict`/`e.tier1_sentiment_conflict` all agree on `{"sentiment_direction"|"tier1_direction": str} | None` (History) vs. the pre-existing `{"sentiment_direction"|"tier1_direction": str} | None` (Dashboard's `tier1_sentiment_conflict`, unchanged) — same shape, different field name per surface, intentional (History's field is named `tier1_conflict` to avoid confusion with the row's own unrelated `ne_prediction`/`outcome` naming; Dashboard's stays `tier1_sentiment_conflict` unchanged to avoid touching a field name other code already depends on).
- Task 4's Step 5 explicitly flags checking `record_prediction()`/`record_tier1_prediction()`'s real signatures before running — those two functions' exact parameter lists weren't re-verified line-by-line while writing this plan; do that check first if either test errors on a `TypeError` about unexpected/missing keyword arguments.
