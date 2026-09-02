# Low-Impact Event Context Tracking — Design

**Date:** 2026-08-31
**Status:** Approved (via conversational brainstorm + AskUserQuestion decisions, not the full brainstorming-skill ceremony — scope was small and decisions were made directly with the user)

## Problem

Two related gaps, found while answering the user's question "is it worth including Low impact events":

1. **Low-impact USD events aren't tracked anywhere.** The dashboard (`webapp/scheduler.py`) tracks High+Medium USD events; the article accumulator tracks High + 3 curated Medium titles. Low-impact USD releases (Housing Starts, Building Permits, Factory Orders, regional Fed surveys, etc.) carry real information that shifts the market's read on the *next* Medium/High release, but none of that data is captured today.

2. **`event_history` writes are globally unscoped.** `webapp/scheduler.py`'s history-writing loop (`for event in all_events:`) iterates the FULL unfiltered Forex Factory feed — every country, every impact tier — and writes a row for each. `get_resolved_event_history()` (`webapp/store.py`) then reads that table back with no country/impact filter either. Traced downstream:
   - The History tab (`webapp/history.py`) is safe by construction — it title-joins against the accumulator's own scored predictions, and the accumulator never processes foreign-country or untracked titles, so those rows are silently dropped before display.
   - `/api/predictions`'s "recently resolved" backfill (`webapp/app.py`, the `recently_resolved` list built from `get_resolved_event_history()`) is **not** safe — it merges any resolved event_history row not already in the current USD Medium+ calendar snapshot back into the events list used to build dashboard cards, with no country/impact filter. A resolved foreign-country event within the retention window can leak into `/api/predictions` today and generate a card (showing "no essence score yet" since it can't be scored, but still visually present as a tracked item).

## Decisions

- **Low-impact USD events: track for data only.** Actual/forecast/previous visible in the Calendar tab and `/api/event_history`, feeding the macro-backdrop cross-check and future month-on-month comparisons. **No essence score, no card, no gauge** — showing one would visually read as a tradeable signal, which contradicts the stated purpose (context only, not for trading these).
- **Scope: all Low-impact USD events**, not a curated allowlist. Accept some initial noise; revisit with a curated list only if a month of data shows specific titles are dead weight.
- **Accumulator (article-based scoring): untouched.** It already only pulls High + the 3-title Medium allowlist; Low is never added to it, so "excluded from the accumulator" requires no code change — only requires not adding Low anywhere the accumulator reads from.
- **`event_history` writes: scope to USD only** (regardless of impact tier — Low-impact USD events now legitimately need history rows; foreign-country events never did and never will, since nothing in this codebase scores non-USD instruments).
- **`/api/predictions`'s recently-resolved backfill: scope to USD Medium+ only** (matching the existing scoring-events threshold, not the new Low-impact calendar threshold) — a Low-impact event must never re-enter the predictions/card list via this backfill path, even after it resolves.
- **NON_MARKET_MOVING tag: parked, not built.** The user's own framing: "The dashboard doesn't have enough data currently to make that determination." Revisit after roughly a month of collected outcome data (around 2026-10-01) to see what actually moved the market vs. what didn't, and design the tag against real evidence instead of a guess.

## Architecture

`webapp/scheduler.py`'s `run_scoring_cycle()` currently computes ONE `events` list (`filter_relevant_events(all_events, min_impact="Medium")`) used for three different jobs: the persisted calendar snapshot, the symbol-scoring loop, and (indirectly, via `all_events`) the history-writing loop. This design splits it into two explicit event lists, plus a scoped history write:

- **`calendar_events`** = `filter_relevant_events(all_events, min_impact="Low")` — USD, Low+. Persisted via `save_calendar_snapshot_if_changed()`, feeding `/api/calendar` (Calendar tab grid + date panel). This is the ONLY new surface Low-impact events appear on.
- **`scoring_events`** = `filter_relevant_events(all_events, min_impact="Medium")` — USD, Medium+, unchanged from today. Feeds the symbol-scoring loop (unchanged behavior — Low events never get scored, never get a card).
- **History-writing loop**: currently `for event in all_events:` (fully unfiltered). Changes to iterate a USD-only-filtered list (any impact tier) — `filter_relevant_events(all_events, min_impact="Low")` is exactly this (USD, Low+, which is "USD, any real impact tier" since Low is the floor), so `calendar_events` itself is the correct iterable here — no third list needed.
- **`webapp/app.py`'s `/api/predictions`**: the `recently_resolved` backfill must filter `get_resolved_event_history()`'s rows to Medium+ before merging into `events` — checked via `EVENT_SURPRISE_DIRECTION`/impact-rank, since `get_resolved_event_history()` rows carry no impact field (impact isn't stored in `event_history` at all — see Task 2 for the exact scoping mechanism used, since the row itself doesn't carry impact tier and re-deriving it requires a title-based check).

## Explicitly out of scope

- Any change to `scoring/backtest_accumulator.py` (article-based accumulator) — it already doesn't touch Low, and doesn't need to touch it now.
- The NON_MARKET_MOVING tag itself — parked per Decisions above.
- Curating the Low-impact list down to specific titles — starting with the full USD Low+ set per the user's explicit choice.
