# Month-Lookahead Calendar Source — Research (not integrated)

**Prepared:** 2026-08-15. **Status:** research only — nothing in this doc is wired into the codebase. Purpose: find a reliable alternate source for a month-ahead schedule of upcoming USD economic releases, to be cross-checked against `data_layer/calendar_feed.py`'s Forex Factory feed as FF's own "thisweek" window populates those same dates (FF has no `nextweek`/`lastweek` variant — confirmed dead ends, see that module's docstring — so it can never itself look more than the current week ahead).

Every candidate below was **live-tested from this sandbox**, not assumed from documentation — same discipline this project has used all session (Kalshi, FMP, NewsAPI were all corrected by live checks, not research summaries).

## Recommendation: FRED (Federal Reserve Economic Data) API

**`https://api.stlouisfed.org/fred/releases/dates`** — St. Louis Fed's official, free API.

- **Live-verified reachable and functional**: an unauthenticated request returns a clean, structured error (`{"error_code":400,"error_message":"Bad Request. Variable api_key is not set..."}`) — not a bot-block, not a redirect, not an HTML wall. That response shape is exactly what a real, documented API surface looks like.
- **Free, but requires a registered account** — sign up at `fred.stlouisfed.org/docs/api/api_key.html` for an API key. This is why it's "not plugged in yet": creating an account is something you'd do, not something to do on your behalf without asking first.
- **What it gives**: `release_id` + `realtime_start`/`realtime_end` → every scheduled release date for that indicator (or all indicators, unscoped) within the window — this is a genuine forward-looking schedule endpoint, not a historical-data query dressed up as one. FRED aggregates release calendars FROM the primary agencies (BLS, BEA, Census, the Fed itself) into one unified API, which sidesteps the next finding below.
- **What it does NOT give**: forecast/consensus values. FRED only knows the scheduled release date and (once published) the actual number — no analyst-consensus forecast field. That's a real gap relative to FF, not a weakness of FRED specifically; nothing free provides consensus forecasts (this was already the conclusion of this project's earlier Trading Economics/FMP research). For this task's actual purpose — verifying FF's date/time accuracy and catching events before FF's own week-ahead window populates them — that gap doesn't matter; FRED's job here is pure date/time confirmation, not a forecast source.
- **Mapping work needed before integration** (not started): FRED release IDs for the indicators this project tracks (Employment Situation → NFP, Consumer Price Index → CPI, Producer Price Index → PPI, GDP, PCE, etc.) need to be looked up and mapped to this project's `EVENT_SURPRISE_DIRECTION` titles — a config-only mapping, same pattern as `KALSHI_SERIES_BY_EVENT_TITLE`.

## Also live-verified reachable (secondary, narrower)

- **Federal Reserve's own FOMC calendar page** (`federalreserve.gov/monetarypolicy/fomccalendars.htm`) — live-verified 200 OK, no bot-block, no auth needed. Publishes every FOMC meeting date **a year or more ahead**, directly from the primary source — the single most authoritative possible source for FOMC dates specifically (this is in fact the same settlement source Kalshi's own KXFED market cites). Scraping an HTML page rather than a clean API, so lower priority than FRED for anything beyond FOMC, but a genuine, free, always-current fallback for that one event type.
- **BEA (Bureau of Economic Analysis) API** — live-verified reachable (`apps.bea.gov/api/data`, returned a structured 200 response even with a placeholder `UserID=test`). Free, registered-key API, primary source for GDP releases specifically. Redundant with FRED's GDP release coverage for this task's purpose — FRED already aggregates BEA's schedule — so not worth a separate integration unless FRED's GDP coverage turns out incomplete.

## Ruled out this check (live-tested, real reasons)

- **BLS (Bureau of Labor Statistics) — direct ICS calendar feeds** (`bls.gov/schedule/news_release/{cpi,empsit,ppi}.ics`): live-tested, **403 Access Denied** with an explicit anti-bot message ("Automated retrieval programs ... bot activity that doesn't conform to BLS usage policy is prohibited"). BLS is the *primary* source for CPI/PPI/NFP data and would otherwise be the single most authoritative option — but it actively blocks the exact kind of unauthenticated automated fetch this project would need. Not usable programmatically without going through BLS's own registered Public Data API (which is a historical-data query API, not a forward-schedule endpoint) or a manual/browser-based workaround, neither of which fits "plot a month-ahead schedule" cleanly. FRED's release-dates endpoint effectively gets BLS's schedule data through a bot-friendly front door instead.
- **Trading Economics, Financial Modeling Prep, NewsAPI.org production tier** — already live-verified paid/unsuitable earlier this session (see `docs/fundamental-analysis-swot-2026-08-14.md`'s W5 and the 2026-08-14 handover); not re-tested here, no reason to expect it's changed.

## Not yet tested (candidates, lower confidence)

- **Investing.com's economic calendar** — same risk profile as Forex Factory itself (unofficial, scraped, informal rate limits) — would add a second copy of the same single-source-fragility problem (W5) rather than a genuinely independent one. Not tested; not recommended as a next step for that reason.
- **Finnhub's economic calendar endpoint** — the 2026-08-14 handover flagged this as "plausible but unverified, needs a real key test." Not retested this pass — FRED's clean live result made it unnecessary to chase a second untested candidate for the same job.

## Suggested next step, when you're ready to integrate

1. Register a free FRED API key (your action, not mine).
2. A short, isolated `data_layer/fred_calendar_feed.py` (mirroring `kalshi_feed.py`'s read-only, fail-open shape) that calls `/fred/releases/dates`, mapped through a new `FRED_RELEASE_ID_BY_EVENT_TITLE` config dict.
3. Run it alongside `data_layer/calendar_feed.py` for a few weeks **read-only, display-only** — log where FRED's date for an event disagrees with FF's, or where FRED shows an event before FF's window has populated it — before trusting it for anything scoring-relevant. That's the verification step you described: comparing FRED's lookahead against FF's own week-ahead as it fills in.
