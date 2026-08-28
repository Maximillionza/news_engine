# FRED Actuals Fallback for Missing/Late Forex Factory `actual` — Design

## Problem

Forex Factory reliably publishes `forecast` and `previous` for a tracked
event, but its `actual` is frequently missing or posts hours late —
confirmed live, not a one-off: Core PCE Price Index m/m and Prelim GDP q/q
both released 2026-08-26 12:30 UTC and still showed `actual: None` in FF's
own feed 45+ minutes later, requiring a manual agent-driven WebSearch
fallback (`scripts/fill_missing_actuals.py`) to unstick them. That script
exists specifically because this isn't the first occurrence — the same
gap hit CPI/PPI earlier this session too. The manual fallback only works
because an *agent* can call WebSearch/WebFetch; `webapp/scheduler.py`'s
live background loop cannot, so every recurrence requires a human noticing
and asking an agent to intervene.

This directly causes two live-observed downstream failures: an event stays
"pending" on the dashboard indefinitely (the essence score's
`_recompute_stale_pending()` has nothing to recompute from), and it never
appears in the History tab's numeric track record (`get_resolved_event_history()`
only returns rows with a real `actual`).

## Scope boundary

- Only addresses the `actual` field. Forecast/previous/timing/impact stay
  FF-sourced, unchanged — those aren't the reported problem.
- Only covers event titles FRED actually tracks (a subset of currently
  High/Medium-impact tracked titles — see Coverage below). Titles with no
  FRED series (ISM PMI, Challenger Job Cuts, FOMC/speech events) are
  untouched — no regression, no improvement there either.
- No change to `scoring/backtest_accumulator.py`'s article-based pipeline
  — this only ever writes to `webapp/store.py`'s `event_history`, the same
  table `scripts/fill_missing_actuals.py` already writes to manually.
- No new external dependency — reuses the already-configured `FRED_API_KEY`
  and the request pattern `data_layer/macro_backdrop.py` already
  establishes (`series/observations`, same fail-open contract).
- Free-tier only, per explicit instruction — no paid data source.

## Architecture

New module `data_layer/fred_actuals.py`, mirroring `macro_backdrop.py`'s
existing contract:

```python
def get_actual_from_fred(event_title: str, event_time_utc: dt.datetime) -> Optional[str]:
    """
    Returns FRED's real, freshly-published value for event_title's most
    recent release, formatted as a percentage string (e.g. "0.2%"), or
    None if there's no FRED coverage for this title, no fresh observation
    yet, or the request fails for any reason. Never raises, never guesses.
    """
```

- Looks up `(series_id, units)` for `event_title` in a new config dict,
  `FRED_SERIES_ID_BY_EVENT_TITLE` (`config/settings.py`) — `units="pch"`
  for m/m-framed titles, `"pc1"` for y/y-framed titles. FRED's own `units`
  parameter computes the percent change server-side — live-verified
  2026-08-26 against `PCEPILFE`: `units=pch` returned `0.24552` (≈0.2%,
  matching Core PCE m/m) and `units=pc1` returned `3.34414` (≈3.3%,
  matching Core PCE y/y) — both independently corroborated against
  Investing.com's real print the same day. No manual level-to-percent math
  needed, removing a category of rounding/edge-case bugs.
- Fetches the single newest observation for that series
  (`sort_order=desc&limit=1`).
- **Freshness check, not period-matching:** rather than computing which
  exact reference period a release covers (fiddly across monthly vs.
  quarterly titles), checks the observation's own `realtime_start` (when
  FRED itself published that point) is on-or-after `event_time_utc`'s
  calendar date. A match means this is a genuine fresh figure for this
  release — return it, formatted as a percentage string. No match means
  FRED hasn't updated yet — return `None`, same as "nothing exists."
  Live-verified 2026-08-26: `PCEPILFE`'s newest point carried
  `realtime_start: 2026-08-26`, same day as the 12:30 UTC release.
- Same fail-open contract as every other `data_layer` module: missing
  `FRED_API_KEY`, no series mapping for this title, a network/HTTP error,
  or a stale (not-yet-updated) observation all return `None` — never
  raises, never invents a value.

## Integration point

`webapp/scheduler.py`'s `run_scoring_cycle()`, after its existing
FF-driven `upsert_event_history()` calls: for any event whose
`event_time_utc` has passed and whose `event_history` row still has
`actual = None`, call `get_actual_from_fred()`. A real result gets written
via the same `upsert_event_history()` path `fill_missing_actuals.py`
already uses, tagged `source="fred"` — a fourth, honest provenance value
alongside the existing `live` / `seeded` / `live_web_fallback`, so it's
always traceable which source actually supplied a given actual.

This requires no other code changes downstream: `_recompute_stale_pending()`
already resolves the essence score the instant `event_history` has a real
`actual` (confirmed working today, off a manually-filled value — this just
automates the fill). `get_resolved_event_history()` already feeds the
History tab and the dashboard's recently-resolved merge off the same
field. Both start working automatically, same-day, for every FRED-covered
title, with zero changes to either of those consumers.

## Coverage

Starts from `FRED_RELEASE_ID_BY_EVENT_TITLE`'s existing ~13 titles (CPI
m/m·y/y, Core CPI m/m·y/y, PPI m/m, Core PPI m/m, Non-Farm Employment
Change, Unemployment Rate, Unemployment Claims, Average Hourly Earnings
m/m, ADP Nonfarm Employment Change, Retail Sales m/m, Prelim GDP q/q, Core
PCE Price Index m/m, Prelim UoM Consumer Sentiment, Import Prices m/m) —
already-confirmed FRED coverage of that data domain, via a *release ID*,
not yet the specific *series ID* `series/observations` needs.

**Only `PCEPILFE` (Core PCE Price Index, both m/m and y/y via `units`) is
live-verified as of this spec.** Every other title's series ID must be
live-verified the same way — real API call, real confirmed value — before
being added to `FRED_SERIES_ID_BY_EVENT_TITLE`, matching the standing rule
already documented on `FRED_RELEASE_ID_BY_EVENT_TITLE` itself ("every rid
below was live-verified... not assumed from documentation"). No series ID
ships from general knowledge alone. This verification work is
implementation-phase work, not resolved by this spec.

## Edge cases

- **FF eventually posts its own actual too.** `upsert_event_history()`
  already only fills `actual` when it's currently `None` — a
  FRED-sourced value is never overwritten by a later FF one (confirmed
  design choice; FRED is itself official-government-sourced, not a lesser
  stand-in). Accepted trade-off: a rare FRED/FF rounding or revision
  mismatch stays as FRED's version permanently, rather than being
  reconciled later.
- **A title is in `FRED_RELEASE_ID_BY_EVENT_TITLE` but its series turns
  out to have no clean m/m or y/y percent-change framing** (e.g. a series
  that's inherently a level with no natural "previous period" comparison,
  or a component release FRED bundles differently than FF's per-metric
  breakout) — excluded from `FRED_SERIES_ID_BY_EVENT_TITLE` rather than
  forced into a wrong shape; falls back to the current FF-only behavior
  for that title, same as an uncovered title.
- **FRED's observation exists but is stale (pre-dates the release).**
  Returns `None` — correctly treated as "not available yet," not "zero
  change" or any other guessed value.

## Testing

Mirrors `tests/test_macro_backdrop.py`'s existing pattern — mocked
`requests.get`, no live network:

- Freshness check accepts a same-day (or later) `realtime_start` and
  rejects a stale one.
- No `FRED_API_KEY` set → `None`.
- Title absent from `FRED_SERIES_ID_BY_EVENT_TITLE` → `None`, no request
  made.
- Network/HTTP failure → fail-open `None`, never raises.
- `units="pch"` vs `units="pc1"` both round-trip correctly into a
  formatted percentage string.
- `webapp/scheduler.py` integration test: `run_scoring_cycle()` writes
  `event_history` with `source="fred"` specifically when FF's own actual
  is still `None` and FRED has a fresh value; does *not* write (or
  overwrite) when FF already supplied a real actual.
