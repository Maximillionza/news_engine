# Calendar-Feed Single-Source Risk & Staleness Policy

**Prepared:** 2026-08-14, implementing R6 of `docs/fundamental-analysis-swot-2026-08-14.md` (W5/T1).

## The risk, stated plainly

Every event timestamp, forecast, previous, and actual value in this system ultimately traces back to one feed: `https://nfs.faireconomy.media/ff_calendar_thisweek.json` (`data_layer/calendar_feed.py`). It is:

- **Unofficial.** Forex Factory publishes no developer API; this is FairEconomy's public JSON backing FF's embeddable widget, reverse-engineered by the retail trading tool community, this project included.
- **Rate-limited, informally.** FF's own published guidance: max 2 downloads per 5 minutes across all formats combined, with an explicit recommendation to fetch once a week and cache — not poll on an interval, which is what both `webapp/scheduler.py` and `scoring/backtest_accumulator.py` do (on adaptive intervals, tightening as events approach). This project has been rate-limited (429) three times in a single session.
- **Single-sourced.** No genuinely free alternative survived live verification this project has done: Trading Economics (paid), Financial Modeling Prep (paid as of 2026-08-14, contradicting earlier "free" research), NewsAPI.org's production tier (dev-only, delayed). Finnhub remains plausible but unverified with a real key. Decision already made with the user this session: stop chasing alternates, respect FF's real limit, use manual WebSearch/screenshot fallback when the feed lags.

## What already mitigates this (in place before this document)

- A persisted, file-backed cooldown (`data_layer/.last_ff_fetch_at`, gitignored) enforces a 600-second minimum between ANY `fetch_calendar()` call, from ANY caller/process, surviving restarts — well under FF's hard 2-per-5-minutes limit, though still far more aggressive than FF's own "once a week" recommendation.
- Every caller of `fetch_calendar()` fails open on any exception (including the cooldown's own `FetchCooldownError`) — a blocked or failed fetch keeps serving the last successfully persisted `calendar_snapshot`, never crashes a route or the scoring loop.
- `webapp/app.py`'s API routes never fetch live at all — they only ever read `webapp/store.py`'s persisted snapshot, so a live feed outage never blocks a request.

## What was missing, and what this pass adds

None of the above told a *reader* of the dashboard how stale the data currently is — a snapshot from 6 hours ago and one from 4 days ago looked identical at the API layer. `data_layer.calendar_feed.get_last_successful_fetch_age_seconds()` (new) exposes the cooldown file's timestamp; `/api/calendar`'s response now includes `feed_staleness_seconds` alongside `fetched_at_utc`.

## Operational policy — what "too stale" means

This is a **recommendation for how a consumer (dashboard UI, or a future automated check) should treat the number**, not a new code-level gate — the existing fail-open behavior already does the right defensive thing (keep last-known-good data rather than show nothing), and adding a hard cutoff that stops scoring on stale data would trade a display problem for an availability one.

| `feed_staleness_seconds` | Treat as | Rationale |
|---|---|---|
| < 3 hours | Fresh | Within the accumulator's own baseline hourly cadence once an event is active; normal operation. |
| 3–24 hours | Aging — display a subtle staleness indicator | Plausible during a quiet week (`FAR_INTERVAL_SECONDS` = 12h baseline) or a budget-fallback backoff; not yet a reason to distrust a call, but worth a visual cue. |
| > 24 hours | Stale — flag prominently, do not treat any newly-"pending"-turned-"resolved" transition as fresh news | Something has gone wrong with the sole live fetcher (scheduler thread died, repeated cooldown/429 collisions, or a genuine FF outage) and needs investigation before trusting any *new* directional call; already-recorded `prediction_runs`/`event_history` rows remain exactly as trustworthy as when they were written — staleness affects only what's NOT been re-checked since. |

## What this does not solve

- It does not add a second data source (ruled out this session — no verified free alternative).
- It does not change scoring behavior — this is observability, not a new gate, per the explicit "no new hard cutoff" reasoning above.
- If FF's feed structure or endpoint changes without notice (a real, standing threat per T1), this policy only helps a human notice faster via `feed_staleness_seconds` climbing — it does not auto-recover.
