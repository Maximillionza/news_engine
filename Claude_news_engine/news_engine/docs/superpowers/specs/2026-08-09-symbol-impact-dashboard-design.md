# Symbol Impact Dashboard — Design Spec

**Date:** 2026-08-09
**Status:** Approved, pending implementation plan

## Purpose

A local web dashboard showing, per tracked symbol, a directional call (BUY/HOLD/SELL-style) driven by upcoming/just-released USD economic events — without requiring article text. The engine already has an RSS/lexicon/FinBERT/LLM article pipeline (`scoring/probability_engine.py`); this is a **separate, simpler, faster path** that scores purely off structured calendar data (forecast vs. actual), reusing `EconomicEvent.usd_surprise_score()` built earlier this session.

Two other requirements beyond the score itself:
1. A calendar view showing where "today" sits relative to each tracked event.
2. When a re-score changes a symbol's call, show the previous prediction alongside the new one with the delta, not just silently overwrite it.

## Non-goals

- Not replacing the existing article-based scoring pipeline — this is additive, a different (article-free) signal source for a different UI.
- Not fetching/displaying news article text in this UI at all.
- Not a price-target tool — no "Low/Target/High" price slider (explicitly dropped from the reference screenshot's design); the card shows only the directional probability gauge.
- Not multi-user/auth — single local user, single machine, matches how the rest of this project runs.

## 1. Symbol & impact model

Extends the existing `usd_relationship` concept in `config/settings.py`'s `INSTRUMENTS` dict, but auto-derived from the ticker instead of hand-entered per symbol, and expanded to also decide *applicability* (does this USD event affect this symbol at all), not just direction.

New module: `webapp/symbols.py`.

```python
@dataclass
class SymbolClass:
    symbol: str
    symbol_class: str        # "metal" | "fx_usd_base" | "fx_usd_quote" | "index_risk" | "fx_cross"
    usd_relationship: str | None   # "inverse" | "direct" | "risk_sentiment" | None (fx_cross -> not applicable)

def classify_symbol(ticker: str) -> SymbolClass:
    ...
```

Classification rules, in order:
1. Ticker in a hardcoded metals list (`XAUUSD`, `XAGUSD`) → `metal`, inverse.
2. Ticker in a hardcoded index list (`US30`, `US500`, `NAS100`, ...) → `index_risk`, risk_sentiment.
3. Ticker matches `^USD[A-Z]{3}$` → `fx_usd_base`, direct (USD is the base currency — USD strength pushes the pair up).
4. Ticker matches `^[A-Z]{3}USD$` → `fx_usd_quote`, inverse (USD is the quote currency — USD strength pushes the pair down).
5. Otherwise (two 3-letter currency codes, neither is USD) → `fx_cross`, `usd_relationship=None` — **not applicable to USD events**. This is the GBPAUD case: the dashboard shows "No USD exposure for this event," not a fabricated score.

Adding a symbol via the UI is just typing a ticker — classification is automatic, no manual per-symbol config needed for the common cases. An unrecognized ticker (not 6 uppercase letters, not in either hardcoded list) is rejected with a clear error rather than silently misclassified.

## 2. Essence-only scoring path

New module: `webapp/scoring_service.py`. Does **not** touch `scoring/probability_engine.py`'s article pipeline — parallel, simpler path:

```python
def score_event_for_symbol(event: EconomicEvent, symbol_class: SymbolClass) -> EssenceScore:
    if symbol_class.usd_relationship is None:
        return EssenceScore(applicable=False, ...)

    usd_surprise = event.usd_surprise_score()   # None if not yet released, or unmapped indicator
    if usd_surprise is None:
        return EssenceScore(applicable=True, pending=True, ...)  # "awaiting release" state

    relationship = symbol_class.usd_relationship
    if relationship == "inverse":
        symbol_score = -usd_surprise
    elif relationship == "direct":
        symbol_score = usd_surprise
    elif relationship == "risk_sentiment":
        symbol_score = -usd_surprise * 0.7   # same dampening as probability_engine._map_to_instrument_score

    probability = 0.5 + 0.5 * math.tanh(SURPRISE_SENSITIVITY * symbol_score)  # reuses existing sigmoid shape
    direction = BUY if symbol_score > 0.02 else (SELL if symbol_score < -0.02 else HOLD)
    return EssenceScore(applicable=True, pending=False, probability=probability, direction=direction, raw_score=symbol_score)
```

Reuses `SURPRISE_SENSITIVITY` and the same tanh-saturation approach already in `probability_engine.py`/`calendar_feed.py` rather than inventing new tuning constants. `applicable=False` (fx_cross) and `pending=True` (event hasn't printed yet) are both distinct, explicit states — never silently rendered as a 50% "neutral" score, same honesty discipline as `usd_surprise_score()` returning `None` rather than a fabricated 0.0.

## 3. Persistence — SQLite

New module: `webapp/store.py`. Single table:

```sql
CREATE TABLE prediction_runs (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    scored_at_utc TEXT NOT NULL,
    probability REAL NOT NULL,
    direction TEXT NOT NULL,
    raw_score REAL NOT NULL
);
```

One row per (symbol, event, scoring run). The dashboard's "previous vs new" diff strip is just: for a given (symbol, event), take the two most recent rows and diff them. DB file: `webapp/dashboard.db` (gitignored, like `ruvector.db` already is in this repo's pattern).

## 4. Scheduler — 15-minute auto-poll

New module: `webapp/scheduler.py`. A background thread loop (stdlib `threading.Timer` or a simple `while True: sleep(900)` loop — no new dependency needed for this):

1. Fetch `thisweek` calendar (existing `calendar_feed.fetch_calendar()`).
2. For each tracked symbol × each high-impact USD event in its pre-event/just-released window: compute `score_event_for_symbol()`, persist a new row if the score changed meaningfully from the last stored row for that (symbol, event) pair (avoids writing identical rows every 15 minutes when nothing changed).
3. Log what changed, for debugging.

Known limitation carried over from earlier this session, not solved here: `fetch_calendar()` only has a working `thisweek` endpoint — events already scored can roll out of that response once the calendar week turns over. The scheduler keeps its own DB rows regardless (history isn't lost), but it can't re-fetch a rolled-off event's metadata if needed later.

## 5. Backend API — Flask

New `webapp/app.py`. Endpoints:

- `GET /api/symbols` — list tracked symbols + their classification
- `POST /api/symbols` — add `{"ticker": "EURUSD"}`, returns classification or a 400 with a clear error if unrecognized
- `DELETE /api/symbols/<ticker>` — remove
- `GET /api/calendar` — this week's high-impact USD events (for the month-grid calendar tab)
- `GET /api/predictions` — latest + previous score per tracked symbol (what the dashboard cards render from)
- `GET /api/predictions/<symbol>/history` — full run history for that symbol's current tracked event (not surfaced in the UI yet per the approved design, but useful for debugging/future use)

## 6. Frontend — plain HTML/CSS/JS, no build step

New `webapp/static/`. Two views:

**Dashboard** (default view): a grid of cards, one per tracked symbol —
- Circular gauge: BUY/HOLD/SELL % (direct port of the reference screenshot's gauge style, minus the price-target row — dropped per approval).
- Day-strip countdown beneath the gauge: ~14 visible day cells, today boxed in green, the symbol's next tracked event day boxed in orange, connecting progress bar.
- Two-tone pie diff strip above the card, appears only when the latest run's direction/probability changed from the previous run: light-green = previous %, dark-green = the added slice (increase) OR light-green = current %, red = the lost slice (decrease). Confirmed color scheme: green/red contrast, not monochrome.
- fx_cross symbols with no applicable event: card shows "No USD exposure for this event" instead of a gauge.
- Pending events (not yet released): gauge shows a neutral "Awaiting release" state, not a fabricated percentage.
- Add-symbol input + remove button per card.

**Calendar tab**: month grid (Sun–Sat) for the current month, today's cell boxed, each tracked event's cell marked with a colored dot per symbol affected, list of upcoming events below the grid.

Polling: frontend polls `GET /api/predictions` and `GET /api/calendar` every 60 seconds (independent of the backend's 15-minute scheduler — the poll just picks up whatever's already in the DB, it doesn't trigger new scoring).

## Error handling

- Calendar fetch failure (network, non-200): scheduler logs and skips that cycle, keeps existing DB data, dashboard shows the last-known state with a "data may be stale" indicator rather than blanking out.
- Unrecognized symbol ticker: rejected at the `POST /api/symbols` boundary with a specific error, never silently misclassified.
- `usd_surprise_score()` returns `None` (unmapped indicator or missing data): surfaced as the explicit "pending" state, not a fabricated neutral score — same as the "applicable=False" case, these are always visually distinct from a real 50% HOLD reading.

## Testing

- Unit tests for `classify_symbol()` covering all 5 classes + rejection of malformed tickers, following the existing `tests/test_scoring_smoke.py` style (synthetic, no network).
- Unit tests for `score_event_for_symbol()` — reuse the same real ADP-miss numbers already used in `test_precursor_leading_indicator()` to confirm the essence-only path produces the same directional read as the precursor contribution path did (both ultimately go through the same `usd_surprise_score()`).
- `store.py` round-trip test: write two runs for the same (symbol, event), confirm the diff calculation matches.
- No live-browser/UI automation testing in scope for v1 — manual verification against the running app.

## Open items carried forward, not blocking this spec

- Which indices beyond US30 go in the hardcoded `index_risk` list — default to just US30 for now (matches existing `INSTRUMENTS`), expand later.
- Whether `fx_cross` symbols should get *any* signal in the future (e.g., an EUR-specific or GBP-specific calendar) — explicitly out of scope; USD-only calendar coverage for now.
