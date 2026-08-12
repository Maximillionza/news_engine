# Kalshi Prediction-Market Scoring Contribution — Design

## Problem

Every signal currently feeding `scoring/probability_engine.score_bundle()`
is either text-derived (article sentiment, print-direction lexicon calls)
or a pattern over past events (trend streak) or a real number from a
*different* event (precursor). Nothing prices the market's own forward
view of the *exact* event being scored. Researched and confirmed live
this session: [Kalshi](https://kalshi.com), a CFTC-regulated prediction
market, has free, unauthenticated public REST access
(`external-api.kalshi.com/trade-api/v2`, confirmed via
[docs.kalshi.com](https://docs.kalshi.com/getting_started/quick_start_market_data))
to real-money markets pricing exactly this — "will CPI print above X%"
ahead of the release. Live verification confirmed real, current series
for the core events this system tracks: `KXCPI` (CPI m/m), `KXCPICORE`
(Core CPI m/m), `KXUSPPI` (PPI m/m), `KXPAYROLLS` (Non-Farm Employment
Change), `KXU3`/`KXUE` (Unemployment Rate).

## Scope boundary

Read-only market-data integration only. **No trading, no order
placement, no authentication of any kind** — this spec never touches
Kalshi's trading endpoints, only its public unauthenticated market-data
reads. Additive to `score_bundle()`, following the exact pattern
`PrecursorContribution`/`PrintCallContribution`/`TrendStreakContribution`
already established — omitting the new param reproduces prior behavior
exactly. No History tab UI change in this pass (that tab doesn't exist
yet — this spec only adds persistence a future UI pass can build on).

## Architecture

### `data_layer/kalshi_feed.py` (new)

Thin, testable HTTP client, no auth, mirroring `data_layer/dukascopy_feed.py`'s
shape:

```python
@dataclass
class KalshiRead:
    strike: float
    implied_direction: str      # 'higher' | 'lower' | 'in_line'
    implied_probability: float  # 0.0-1.0, the yes-price midpoint
    open_interest: float


def get_market_read(series_ticker: str, event_month: dt.date, target_strike: float) -> Optional[KalshiRead]:
    """
    Fetches the series' current event, finds the strike closest to
    target_strike, reads its yes_bid/yes_ask midpoint and open_interest.
    Returns None — never fabricated — if the series/event/market doesn't
    exist, the market list is empty, or the request fails for any reason.
    """
```

Discretization: yes-price midpoint `> 0.55` → `'higher'`, `< 0.45` →
`'lower'`, otherwise `'in_line'` — same three-way shape
`score_print_direction()` already uses, just fed by a market price
instead of a lexicon hit-count.

Nearest-strike tie-break: when the forecast is exactly equidistant
between two adjacent strikes, the **lower** strike wins, deterministically
(no randomness, no "first in API response order").

### `config/settings.py`: `KALSHI_SERIES_BY_EVENT_TITLE`

Config-only-to-extend mapping, same pattern as `PRINT_SURPRISE_LEXICON`.
Every entry below was verified live against the actual market's
`rules_primary` text (not just its title or `settlement_sources` —
Kalshi's own metadata has real copy-paste errors: `KXPAYROLLS`'s listed
settlement source URL points to a PPI page, `KXACPI`'s points to an
employment-situation page). All 16 of this system's 19 tracked
high-impact USD events with a numeric forecast (`EVENT_SURPRISE_DIRECTION`)
have real, active Kalshi coverage:

```python
KALSHI_SERIES_BY_EVENT_TITLE = {
    "Non-Farm Employment Change": "KXPAYROLLS",
    "ADP Nonfarm Employment Change": "KXADP",
    "Unemployment Rate": "KXU3",
    "Unemployment Claims": "KXJOBLESSCLAIMS",
    "Challenger Job Cuts": "KXCHCUTS",
    "CPI m/m": "KXCPI",
    "CPI y/y": "KXCPIYOY",
    "Core CPI m/m": "KXCPICORE",
    "Core CPI y/y": "KXCPICOREYOY",
    "PPI m/m": "KXUSPPI",
    "Advance GDP q/q": "KXGDP",
    "ISM Manufacturing PMI": "KXISMPMI",
    "Retail Sales m/m": "KXUSRETAIL",
    "Core PCE Price Index m/m": "KXPCECORE",
    "Prelim UoM Consumer Sentiment": "KXUSMICHCSP",
}
```

**Confirmed with no usable Kalshi coverage** (verified live, not left
unchecked): `Average Hourly Earnings m/m` (Kalshi's `KXREALWAGES` prices
a different, inflation-adjusted metric, not the raw nominal figure Forex
Factory reports); `Core PPI m/m` and `Import Prices m/m` (no matching
series exists at all); `ISM Services PMI` (the series `KXISMSERVICES`/
`KXUSISMSERV` exist in Kalshi's category listing but currently have zero
markets — dormant, not usable). These four simply have no entry — same
"absent, not fabricated" guarantee as every other optional signal —
revisit if Kalshi adds coverage later.

An event title with no entry never triggers a Kalshi lookup at all.

### FOMC / Federal Funds Rate — a second, parallel mapping

Kalshi has strong, verified coverage for the Fed's actual rate decision
(`KXFED` — confirmed live: "Will the upper bound of the federal funds
rate be above X% following the Fed's [date] meeting?"), but
`EVENT_SURPRISE_DIRECTION` deliberately excludes `"Federal Funds Rate"`/
`"FOMC Statement"` — they're discrete policy decisions (cut/hold/hike),
not a continuous forecast-vs-actual number, so they don't fit that dict's
existing convention. Rather than force a numeric mapping onto a discrete
decision, this event gets its own small, parallel dict:

```python
# For FOMC/Federal Funds Rate specifically — a discrete decision, not a
# forecast-vs-actual numeric surprise, so it can't reuse
# EVENT_SURPRISE_DIRECTION's convention. A rate hike is unambiguously
# USD-bullish, a cut USD-bearish — simpler than the numeric case, just a
# different shape.
RATE_DECISION_DIRECTION = {
    "hike": "bullish",
    "hold": "neutral",
    "cut": "bearish",
}

KALSHI_RATE_DECISION_SERIES = {
    "Federal Funds Rate": "KXFED",
}
```

`_build_kalshi_contribution()` (see Blend math below) checks
`KALSHI_RATE_DECISION_SERIES` for a discrete-decision event title
separately from `KALSHI_SERIES_BY_EVENT_TITLE`'s numeric-strike lookup —
the two dicts are mutually exclusive per title, and the direction-mapping
source (`RATE_DECISION_DIRECTION` vs `EVENT_SURPRISE_DIRECTION`) is
chosen based on which dict matched. `KXFED`'s markets are themselves
strike-threshold (e.g. "above 4.25%"), so the same nearest-strike-to-
forecast selection logic applies — the *interpretation* of "higher than
this strike" differs (a hike/higher rate is direction `'hike'`, mapped via
`RATE_DECISION_DIRECTION`), not the strike-selection mechanism itself.

### `MIN_KALSHI_OPEN_INTEREST` liquidity gate

New constant, `config/settings.py`. A market whose `open_interest_fp` is
below this floor is treated as **no signal at all** — same "contribute
nothing, not a diluted nudge" pattern already used for `in_line` print
calls and thin trend history. Protects the highest-trust-weight
contribution in the system from being driven by an illiquid, easily-skewed
price (observed live: some Kalshi strikes currently show zero 24h volume).

### `scoring/probability_engine.py`: `KalshiMarketContribution`

```python
@dataclass
class KalshiMarketContribution:
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float
```

Duck-typed identically to the other three contribution types — flows
through `_weighted_aggregate()`/`_agreement_and_coverage()` unchanged.
`usd_sentiment` sign via `EVENT_SURPRISE_DIRECTION` for the 15
numeric-forecast events (zero new direction-mapping logic there, same
reuse as the print call and trend streak) or `RATE_DECISION_DIRECTION`
for the FOMC/Federal Funds Rate case (see below) — the caller
(`scoring/backtest_accumulator.py`) already knows which dict matched
from its title lookup, and passes the resolved direction-mapping value
straight through rather than `_build_kalshi_contribution()` re-deriving
it. `trust_weight = KALSHI_TRUST_WEIGHT = 0.95` (new constant) —
above precursor's `0.9`, since this prices real money directly on the
*exact* event being scored, not a related-but-different one. Decays like
a precursor (`PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES`) — tied to a
specific dated event.

`score_bundle()` gains one more optional param:

```python
def score_bundle(
    bundle, instrument, precursor_events=None,
    print_call=None, trend_signal=None,
    kalshi_read: "KalshiRead | None" = None,
) -> ProbabilityResult:
```

Omitting it reproduces prior output exactly, following the same
regression-tested guarantee `print_call`/`trend_signal` already have.

### Persistence: `kalshi_reads` table

New table, `scoring/backtest_store.py` (same DB/ownership as
`print_predictions`):

```sql
CREATE TABLE IF NOT EXISTS kalshi_reads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    strike REAL NOT NULL,
    implied_direction TEXT NOT NULL,
    implied_probability REAL NOT NULL,
    open_interest REAL NOT NULL,
    read_at_utc TEXT NOT NULL
);
```

Diff-aware recording (`record_kalshi_read_if_changed()`, mirroring
`record_print_prediction_if_changed()`) — only a new row on an
`implied_direction` flip for that exact occurrence. This is a separate
deliverable from the not-yet-implemented History tab
(`docs/superpowers/plans/2026-08-12-history-tab.md`) — extends that tab
with a second prediction column in a future pass, not part of this spec's
UI.

## Accumulator wiring

`scoring/backtest_accumulator.py`'s `run_accumulator_cycle()`, once per
event (same "compute once, reuse across instruments" pattern as the
article bundle, precursor lookup, print call, and trend signal already
follow):

1. Look up `event.title` in `KALSHI_SERIES_BY_EVENT_TITLE` first, then
   `KALSHI_RATE_DECISION_SERIES` if the first misses — the two are
   mutually exclusive per title. Neither matches → skip,
   `kalshi_read = None`. Which dict matched also selects the
   direction-mapping source (`EVENT_SURPRISE_DIRECTION` for the numeric
   case, `RATE_DECISION_DIRECTION` for the discrete-decision case) used
   later when `_build_kalshi_contribution()` maps the sign.
2. `target_strike` is `event.forecast` parsed via
   `data_layer.calendar_feed._parse_numeric()` (the same existing helper
   `usd_surprise_score()`/`classify_surprise()` already use for
   forecast/actual strings — no new parsing logic). A `None` parse result
   (missing/unparseable forecast) skips the Kalshi lookup entirely, same
   as a missing series mapping.
3. `get_market_read(series_ticker, event.event_time_utc.date(),
   target_strike)` — any failure (network, missing market, liquidity
   gate) → `None`, logged as a WARNING, never crashes the cycle (same
   fail-open guarantee as the existing cross-pipeline trend-signal read).
4. `record_kalshi_read_if_changed(...)` if a read was obtained.
5. `kalshi_read` passed into every `score_bundle()` call for that event's
   instruments this cycle.

## Testing

- All tests mock the HTTP layer — no live Kalshi network calls in the
  suite, matching every other `data_layer` module's convention.
- `get_market_read()`: series/event/market not found → `None`; request
  timeout/error → `None`, logged; nearest-strike tie-break at an exact
  midpoint → lower strike, deterministic.
- Liquidity gate: `open_interest_fp` at/above `MIN_KALSHI_OPEN_INTEREST` →
  used; below → `None`, same as no market.
- `score_bundle()` with `kalshi_read=None` reproduces prior output exactly
  — regression test mirrors the existing `print_call`/`trend_signal` one.
- `kalshi_reads` diff-aware recording: first-write, no-write-when-
  unchanged, write-on-flip.
- Accumulator wiring: computed once per event, passed into every
  instrument's `score_bundle()` call; a fetch failure fails open without
  crashing the cycle.

## Explicitly out of scope (this pass)

- **No trading or order placement of any kind** — read-only market-data
  access only, restated here for emphasis given Kalshi is a real-money
  regulated exchange.
- No History tab UI column for the Kalshi read — persistence ships now,
  display is a follow-up once the History tab itself exists.
- No full implied-probability-distribution blending across multiple
  strikes — nearest-strike-to-forecast only.
- No calibration of `KALSHI_TRUST_WEIGHT` (0.95) or
  `MIN_KALSHI_OPEN_INTEREST` against real outcomes — launch defaults,
  same "revisit once there's real confirmed data" posture as every other
  trust constant in this system.
- No websocket/streaming — a simple periodic REST poll within the
  accumulator's existing per-cycle architecture.
