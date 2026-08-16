# Macro/Micro Calendar Design (2026-08-16)

**Status:** shipped. Display-only — nothing here touches scoring (`scoring/probability_engine.py`, `webapp/scoring_service.py` are untouched).

## The problem this solves

`data_layer/calendar_feed.py`'s Forex Factory feed only ever returns "thisweek" — there's no `nextweek`/`lastweek` variant (confirmed dead ends, see that module's docstring). The Dashboard's Calendar tab therefore only ever shows a handful of days at a time, even though it renders a full month grid — most of the month is genuinely empty because FF hasn't published those occurrences yet. `docs/calendar-lookahead-source-research-2026-08-15.md` and `data_layer/fred_calendar_feed.py` already solved "where do we get forward dates" (FRED's official release schedule). This design wires that into the actual Dashboard the user sees.

## The model: macro view + micro lens

- **Macro view** — FRED-sourced, month-ahead, **date-only**. Seeded by `scripts/refresh_macro_calendar.py` into `webapp.store`'s new `macro_calendar` table. A best-guess **time**-of-day is attached only when real history exists to infer it from (`store.infer_event_time_of_day()` — the most recent *resolved* `event_history` occurrence for that title); otherwise the time is left `NULL` ("unconfirmed"), never fabricated.
- **Micro lens** — Forex Factory's own near-term feed, exact and authoritative. Every real cycle of `webapp/scheduler.py`'s `run_scoring_cycle()` now also calls `store.confirm_macro_calendar_event()` for every event FF returns — if a macro row exists for that title within `tolerance_days=2` of FF's real date, it's marked `confirmed=1` with FF's real exact `event_time_utc`. This runs against `all_events` (the full, unfiltered fetch), not just the Medium+/USD-filtered list that becomes the visible `calendar_snapshot` — same precedent `upsert_event_history()` already established for that loop, so a macro row can be confirmed even for an occurrence that isn't itself shown on the calendar grid (e.g. filtered by impact).
- FF is always the higher-trust source once it has an occurrence — every merge point (`/api/calendar/monthahead`, `/api/calendar/date/<date>`) skips a macro row when a real FF event already covers that exact `(title, date)`.

## Cadence

`scripts/refresh_macro_calendar.py` reruns itself roughly every **29 days**, measured from the last time it actually ran (a persisted, file-backed timestamp — `data_layer/.last_macro_calendar_refresh_at`, gitignored, same pattern as the FF fetch cooldown), not a fixed calendar day. Safe to invoke on any schedule (cron, manual, whatever) — it self-gates and no-ops if not due. `--force` runs it regardless (used for the first, once-off run).

## What's NOT done here

- **Not wired into scoring.** A macro row's estimated date/time never reaches `score_bundle()` or `score_event_for_symbol()` — it's Calendar-tab display only.
- **No cross-month grid.** The Calendar tab still renders only the current calendar month; a macro date landing in the *next* calendar month won't show a dot yet (known gap, not built this pass).
- **Known edge case, not a bug:** `/api/calendar/monthahead`'s FF-duplicate skip uses an *exact* date match, while `confirm_macro_calendar_event()` uses a `tolerance_days=2` window. A macro row can therefore become `confirmed` (and so stop rendering as "estimated," correctly) without being recognized as an exact duplicate of a specific FF snapshot entry, if FF's real date differs by 1-2 days from FRED's date for the same title. Observed live 2026-08-16: "Import Prices m/m" confirmed via the full unfiltered fetch while not appearing in the impact-filtered 3-event snapshot. Not incorrect — a confirmed row is real, trustworthy data — just a case where the two merge points use slightly different matching windows. Worth tightening if it ever produces a visibly wrong date.

## Files

- `webapp/store.py` — `macro_calendar` table, `MacroCalendarRow`, `infer_event_time_of_day()`, `upsert_macro_calendar_event()`, `confirm_macro_calendar_event()`, `get_macro_calendar_events()`.
- `scripts/refresh_macro_calendar.py` — the 29-day-cadence refresh job.
- `webapp/scheduler.py` — `run_scoring_cycle()` calls `confirm_macro_calendar_event()` per event.
- `webapp/app.py` — `/api/calendar/monthahead` (merged month-ahead view), `/api/calendar/date/<date>` extended to include macro-only entries for that date, `/api/calendar` now also returns `feed_staleness_seconds`.
- `webapp/static/` — Calendar tab shows a feed-staleness indicator (color-coded per `docs/calendar-feed-staleness-policy.md`'s thresholds) and hollow/dashed dots for estimated (unconfirmed) macro dates, distinct from solid FF-confirmed dots.

## Live verification (2026-08-16)

Ran `scripts/refresh_macro_calendar.py --force` against production — 21 macro-calendar rows written across all 10 mapped FRED release IDs. Started the real Dashboard and confirmed via the live `/api/calendar/monthahead` response and the rendered grid:

- Aug 26 (Advance GDP q/q + Core PCE Price Index m/m), Aug 27 (Unemployment Claims), Aug 28 (Prelim UoM Consumer Sentiment) all render as estimated (hollow) dots — exactly the dates the user asked about that weren't showing before.
- Aug 20 (Unemployment Claims), already present in FF's real snapshot, correctly deduped — no double dot, shows as the solid FF-confirmed dot only.
- `feed_staleness_seconds` renders as "Forex Factory feed last checked: 0m ago" immediately after a real scheduler cycle.
