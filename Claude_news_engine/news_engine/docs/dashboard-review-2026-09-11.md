# Dashboard Review — Backend + UI (2026-09-11)

Scope: `webapp/app.py`, `webapp/store.py`, `scoring/backtest_store.py`, `webapp/scheduler.py`, `webapp/static/app.js`, `webapp/static/index.html`, `webapp/static/style.css`. Read-through + `tests/test_webapp_app.py` for behavior confirmation. One finding (the `/api/predictions` N+1) has already been fixed on `news-engine/batch-predictions-queries` (commit `7f596bc`); it's kept here for the record and cross-referenced.

## Backend

**`/api/predictions`'s N+1 query pattern — fixed.** [Certain] Before `7f596bc`, `get_predictions()` issued up to 6 SQLite round trips per `(symbol, event)` pair (`get_latest_two`, `get_event_history`, `get_latest_two_predictions`, `get_latest_print_prediction`, `get_latest_kalshi_read`, `get_latest_tier1_prediction_for_occurrence`) — 2 symbols × ~15 events meant 150+ queries per request, re-run on every 60s poll. Now batched: 6 bulk fetches once per request (`get_latest_two_bulk`, `get_event_history_bulk` in `webapp/store.py`; `get_latest_two_predictions_bulk`, `get_latest_print_predictions_bulk`, `get_latest_kalshi_reads_bulk`, `get_latest_tier1_predictions_bulk` in `scoring/backtest_store.py`), with per-iteration `dict.get()` lookups. Kept the pre-existing `event_time_utc` string-normalization rule (`datetime.fromisoformat(...).isoformat()`, not raw string equality) on both the write and read side of every occurrence-keyed dict, since this codebase has more than one producer of that string. 549/549 tests pass.

**Two DB connections opened and closed per request, no pooling.** [Certain] `get_connection()` and `get_backtest_connection()` are called fresh in every route handler ([app.py:254](../webapp/app.py:254), [app.py:261](../webapp/app.py:261), repeated across every other route) and closed at the end. `get_connection()` also runs `conn.executescript(_SCHEMA)` plus three `PRAGMA table_info` migration checks on every single open ([store.py:221-231](../webapp/store.py:221)) — three metadata queries per request just to re-verify migrations that already ran once. Move schema/migration to a one-time startup call; consider Flask's `g`-scoped connection instead of open/close per route.

**`app.py` is a 800+ line file with one 230-line route function.** [Certain] `get_predictions()` ([app.py:250-587](../webapp/app.py:250) pre-batching, similar length post-batching) does calendar filtering, retention-window merging, per-symbol/per-event enrichment across 5 signal sources, reconciliation, and sorting, all inline. Hard to unit-test in isolation — hence the 1837-line integration-style `test_webapp_app.py`. Worth pulling into a service module (`PredictionsAssembler` or a small pipeline of functions) the route just calls and serializes. [Likely — not urgent, but the next signal source added here will be the one that makes this genuinely unmanageable.]

**JSON blob storage for the calendar snapshot.** [Certain] `calendar_snapshot.events_json` ([store.py:52-56](../webapp/store.py:52)) means every read deserializes the whole blob and every filter (impact rank, date range) happens in Python. Fine at current volume (dozens of events); no path to indexed/partial reads as it grows, and no safe concurrent partial-write semantics beyond the existing full-blob-replace-if-changed approach.

**Flask dev server in what's meant to be a persistently-running app.** [Certain] `app.run(port=5001, debug=False)` ([app.py:808](../webapp/app.py:808)) is single-threaded by default and shares the process with a scheduler thread and an actuals-sync thread, all contending for SQLite file locks. If this needs to reliably serve more than one local tab, it wants `threaded=True` at minimum, or a real WSGI server (waitress, given Windows).

**Duplicate serialization logic across three routes.** [Likely] The article/print/tier1 prediction dict-shaping is written out longhand in `/api/predictions`, `/api/calendar/date/<date>`, and `_article_prediction_dict`, each with a slightly different field set. Only one signal type (`article_prediction`) got the shared-helper treatment; the pattern wasn't applied to the others.

## Frontend

**Full DOM teardown/rebuild every 60s poll.** [Certain] `refreshDashboard()` does `cardsEl.innerHTML = ""` then rebuilds every card from scratch ([app.js:742-743](../webapp/static/app.js:742)). This is the direct cause of the state-restoration code already in the file — it has to snapshot which History panels were expanded and which cards were flipped before the wipe, then replay clicks to restore them ([app.js:726-757](../webapp/static/app.js:726)). Every future piece of card UI state will need its own version of this same hack. A keyed, targeted re-render (only touch a card whose data actually changed) removes the whole problem class.

**Hand-rolled string-templated HTML, ~1000 lines, no component boundaries.** [Certain] `renderCard()` alone is ~300 lines with a dozen nested helper functions, mixing rendering, formatting, and business logic (`directionPct`, `_trend_instrument_lean`'s client-side equivalent). Works today; each new signal type (article/tier1/print/kalshi/trend — five so far) has added another near-identical parallel render function. [Likely] the next one won't be materially harder to bolt on, but the file is already past the point where a newcomer can hold its shape in their head.

**Inconsistent HTML escaping.** [Certain] Most strings go through `escapeHtml()`, but the ticker symbol is interpolated raw into `data-symbol="${symbol}"` and card headers in several places ([app.js:260](../webapp/static/app.js:260), [app.js:465](../webapp/static/app.js:465)) without escaping. `symbol` is server-validated via `classify_symbol()` today, so this isn't currently exploitable, but the inconsistency means the escaping discipline isn't actually enforced anywhere — it's incidental, not structural.

**Unconditional 60s polling, no fetch error handling on the poll path.** [Certain] `setInterval(refreshAll, 60_000)` re-fetches everything regardless of whether anything changed, and `refreshDashboard()`/`refreshCalendar()` don't wrap their `fetch`/`.json()` in try/catch (unlike the Add-Symbol form, which does check `resp.ok`). A transient network blip throws an unhandled rejection and silently freezes the dashboard on stale data with no visible indicator — the existing staleness badges only cover backend staleness, not "the browser itself stopped successfully polling."

**Accessibility gaps.** [Certain] Direction relies on color (green/red) with text labels as the fallback (BUY/SELL helps here, so this is minor); no ARIA roles on the tab buttons, no `aria-expanded` on the toggle buttons, small hit targets on `.remove-btn`. Secondary-text styling is done via scattered inline `style="font-size:12px;color:#888"` strings in the JS rather than CSS classes (dozens of occurrences) — bypasses the stylesheet entirely, and has already drifted into 3-4 slightly different greys for what's conceptually one "meta text" role.

**No responsive handling.** [Certain] `#calendar-grid` is a hard 7-column grid with `min-height: 60px` cells and zero media queries in `style.css`. [Guessing] likely fine if this is only ever viewed on a desktop browser; will cramp or overflow at phone width if that's ever a use case.

## What's already solid

Correctness discipline is genuinely high for a solo project: absent-vs-pending-vs-computed is a consistently enforced convention, fail-open handling exists around every optional signal source, and the SQL upsert logic in `store.py` (first-writer-wins on `actual`, self-healing `forecast`/`impact`) reflects real incidents fixed at the root rather than patched at the symptom. There's a genuine test suite (549 tests passing as of this review) including integration-style coverage of `app.py`. The independent staleness indicators for the scheduler vs. the article accumulator are a better operational choice than most dashboards this size bother with.

## Priority order

1. ~~Batch the `/api/predictions` N+1 queries~~ — done, `7f596bc`.
2. Stop the full-DOM-rebuild-on-every-poll pattern in `app.js` — removes the state-restoration hacks and will visibly reduce UI flicker.
3. Extract `get_predictions()` into a testable service module before the next signal source gets added to it.
4. Move off the Flask dev server if this needs to reliably serve concurrent access.
