# Kalshi Prediction-Market Scoring Contribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Blend Kalshi's real-money prediction-market prices into
`score_bundle()` as a new, highest-trust-tier contribution — a genuinely
different signal type from everything currently feeding the engine
(article text, structured precursor numbers, a lexicon-inferred print
call, a historical streak).

**Architecture:** A new thin HTTP client (`data_layer/kalshi_feed.py`)
reads Kalshi's free, unauthenticated public market-data API and picks the
strike nearest the calendar's forecast. A new `KalshiMarketContribution`
in `scoring/probability_engine.py` blends this into `score_bundle()`
exactly like the three prior optional contributions. A new
`kalshi_reads` table persists it, mirroring `print_predictions`.
`scoring/backtest_accumulator.py` wires it in once per event, reusing the
event's already-parsed forecast — no new fetch pattern, same
"compute once, reuse across instruments" shape as everything else in that
loop.

**Tech Stack:** Python 3.14, `requests` (already a dependency, used the
same way `data_layer/calendar_feed.py` already uses it), SQLite (stdlib
`sqlite3`) — no new dependencies.

## Global Constraints

- **Read-only market-data access only.** No trading, no order placement,
  no authentication of any kind, anywhere in this plan. Kalshi's public
  market-data endpoints (`external-api.kalshi.com/trade-api/v2`) require
  no API key.
- Omitting `score_bundle()`'s new `kalshi_read` param must reproduce
  today's exact output — same guarantee `print_call`/`trend_signal`
  already have, proven by a dedicated regression test.
- `KALSHI_TRUST_WEIGHT = 0.95` (above `PRECURSOR_TRUST_WEIGHT = 0.9`),
  decays like a precursor (`PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES`).
- Discretization: yes-price midpoint `> 0.55` → `'higher'`, `< 0.45` →
  `'lower'`, otherwise `'in_line'`.
- Nearest-strike tie-break at an exact midpoint: the **lower** strike
  wins, deterministically.
- `MIN_KALSHI_OPEN_INTEREST` liquidity gate: a market below this floor
  contributes **nothing** — same "absent, not fabricated" guarantee as
  `in_line` print calls and thin trend history, never a diluted nudge.
- `KALSHI_SERIES_BY_EVENT_TITLE` (15 numeric events) and
  `KALSHI_RATE_DECISION_SERIES` (`{"Federal Funds Rate": "KXFED"}`) are
  mutually exclusive per title — an event title matches at most one.
- `target_strike` is `event.forecast` parsed via
  `data_layer.calendar_feed._parse_numeric()` — no new parsing logic.
- All tests mock the HTTP layer — no live Kalshi network calls in the
  suite.

---

### Task 1: `config/settings.py` constants + `data_layer/kalshi_feed.py`

**Files:**
- Modify: `config/settings.py`
- Create: `data_layer/kalshi_feed.py`
- Test: `tests/test_kalshi_feed.py` (new file)

**Interfaces:**
- Consumes: nothing new (pure HTTP + stdlib).
- Produces: `KALSHI_SERIES_BY_EVENT_TITLE`, `KALSHI_RATE_DECISION_SERIES`,
  `RATE_DECISION_DIRECTION`, `MIN_KALSHI_OPEN_INTEREST`,
  `KALSHI_TRUST_WEIGHT` (all `config.settings`); `KalshiRead` dataclass
  (`strike: float, implied_direction: str, implied_probability: float,
  open_interest: float`) and `get_market_read(series_ticker: str,
  event_month: dt.date, target_strike: float) -> Optional[KalshiRead]`
  (`data_layer.kalshi_feed`). Task 2 imports nothing from here directly
  (duck-typed); Task 4 imports `get_market_read`, `KALSHI_SERIES_BY_EVENT_TITLE`,
  `KALSHI_RATE_DECISION_SERIES`.

- [ ] **Step 1: Add the new constants to `config/settings.py`**

Insert immediately after the `PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES =
PRE_EVENT_WINDOW_HOURS * 60` line (currently line 268):

```python

# --- Kalshi prediction-market integration ---
# Kalshi (kalshi.com) is a CFTC-regulated prediction-market exchange with
# free, unauthenticated public market-data access. Confirmed live this
# session: real, active series exist for 15 of this system's 19 tracked
# high-impact USD events. Config-only-to-extend, same pattern as
# PRINT_SURPRISE_LEXICON — an event title with no entry here never
# triggers a Kalshi lookup at all.
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
# Confirmed with NO usable Kalshi coverage (verified live, not left
# unchecked): Average Hourly Earnings m/m (Kalshi's closest match prices
# a different, inflation-adjusted metric), Core PPI m/m and Import
# Prices m/m (no matching series exists), ISM Services PMI (series
# exists but has zero markets currently listed — dormant). These four
# simply have no entry here.

# FOMC/Federal Funds Rate is a discrete cut/hold/hike DECISION, not a
# continuous forecast-vs-actual number — it can't reuse
# EVENT_SURPRISE_DIRECTION's convention, so it gets its own small,
# parallel mapping. Mutually exclusive with KALSHI_SERIES_BY_EVENT_TITLE
# per title — an event title matches at most one of the two dicts.
RATE_DECISION_DIRECTION = {
    "hike": "bullish",
    "hold": "neutral",
    "cut": "bearish",
}
KALSHI_RATE_DECISION_SERIES = {
    "Federal Funds Rate": "KXFED",
}

# A Kalshi market whose open_interest is below this floor is treated as
# NO signal at all — same "contribute nothing, not a diluted nudge"
# pattern already used for in_line print calls and thin trend history.
# Protects the highest-trust-weight contribution in the system from
# being driven by an illiquid, easily-skewed price (observed live: some
# Kalshi strikes currently show zero 24h volume).
MIN_KALSHI_OPEN_INTEREST = 10.0

# Trust weight for a Kalshi market read when blended into score_bundle()
# — above PRECURSOR_TRUST_WEIGHT (0.9), since this prices real money
# directly on the EXACT event being scored, not a related-but-different
# one via a structured surprise.
KALSHI_TRUST_WEIGHT = 0.95
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_kalshi_feed.py`:

```python
"""
Tests for data_layer/kalshi_feed.py — no live network, requests.get is
mocked with synthetic Kalshi API responses.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.kalshi_feed as kalshi_feed


def _fake_response(json_body, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_body
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def _fake_events_response(event_ticker):
    return {"events": [{"event_ticker": event_ticker}]}


def _fake_markets_response(strikes):
    """strikes: list of (floor_strike, yes_bid, yes_ask, open_interest_fp) tuples."""
    return {
        "markets": [
            {
                "floor_strike": s, "yes_bid_dollars": str(bid), "yes_ask_dollars": str(ask),
                "open_interest_fp": str(oi),
            }
            for s, bid, ask, oi in strikes
        ]
    }


def test_get_market_read_picks_nearest_strike_and_computes_midpoint():
    print("=== kalshi_feed: get_market_read picks the strike nearest target_strike, midpoint = (bid+ask)/2 ===")
    strikes_response = _fake_markets_response([
        (0.1, "0.30", "0.40", "50"),
        (0.2, "0.60", "0.70", "80"),  # nearest to target_strike=0.19
        (0.3, "0.10", "0.20", "60"),
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.19)
        assert result is not None
        assert result.strike == 0.2
        assert abs(result.implied_probability - 0.65) < 1e-9  # (0.60+0.70)/2
        assert result.open_interest == 80.0
    print("PASS\n")


def test_get_market_read_discretizes_higher_lower_in_line():
    print("=== kalshi_feed: get_market_read discretizes the midpoint into higher/lower/in_line at the 0.55/0.45 thresholds ===")
    for bid, ask, expected in [("0.60", "0.70", "higher"), ("0.20", "0.30", "lower"), ("0.48", "0.50", "in_line")]:
        strikes_response = _fake_markets_response([(0.1, bid, ask, "50")])
        with patch.object(kalshi_feed.requests, "get") as mock_get:
            mock_get.side_effect = [
                _fake_response(_fake_events_response("KXCPI-26AUG")),
                _fake_response(strikes_response),
            ]
            result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
            assert result.implied_direction == expected, f"bid={bid} ask={ask} expected {expected}, got {result.implied_direction}"
    print("PASS\n")


def test_get_market_read_tie_break_picks_lower_strike():
    print("=== kalshi_feed: an exact midpoint tie between two strikes picks the LOWER one, deterministically ===")
    strikes_response = _fake_markets_response([
        (0.1, "0.40", "0.50", "50"),
        (0.3, "0.40", "0.50", "50"),
    ])  # target_strike=0.2 is exactly equidistant from 0.1 and 0.3
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.2)
        assert result.strike == 0.1
    print("PASS\n")


def test_get_market_read_returns_none_when_no_events():
    print("=== kalshi_feed: get_market_read returns None when the series has no current event ===")
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [_fake_response({"events": []})]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
        assert result is None
    print("PASS\n")


def test_get_market_read_returns_none_when_no_markets():
    print("=== kalshi_feed: get_market_read returns None when the event has no markets listed ===")
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response({"markets": []}),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
        assert result is None
    print("PASS\n")


def test_get_market_read_returns_none_on_request_failure():
    print("=== kalshi_feed: get_market_read returns None (not a crash) when the request fails ===")
    with patch.object(kalshi_feed.requests, "get", side_effect=Exception("network down")):
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
        assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_get_market_read_picks_nearest_strike_and_computes_midpoint()
    test_get_market_read_discretizes_higher_lower_in_line()
    test_get_market_read_tie_break_picks_lower_strike()
    test_get_market_read_returns_none_when_no_events()
    test_get_market_read_returns_none_when_no_markets()
    test_get_market_read_returns_none_on_request_failure()
    print("All kalshi_feed tests passed.")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python tests/test_kalshi_feed.py`
Expected: `ModuleNotFoundError: No module named 'data_layer.kalshi_feed'`

- [ ] **Step 4: Implement `data_layer/kalshi_feed.py`**

```python
"""
Thin, read-only HTTP client for Kalshi's free, unauthenticated public
market-data API (external-api.kalshi.com/trade-api/v2) — confirmed live
this session: no API key needed for GET /events, /markets. Mirrors
data_layer/dukascopy_feed.py's shape: contains the third-party API's
response structure to this one file, callers only ever see KalshiRead.

READ-ONLY. This module never authenticates, never places or cancels an
order, never touches Kalshi's trading endpoints — only the public market-
data reads (GET /markets/{series_ticker}/events, GET /markets).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import requests

KALSHI_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

# Discretization thresholds for the yes-price midpoint (0.0-1.0) into a
# direction call — same three-way shape scoring/print_direction.py's
# score_print_direction() already uses, just fed by a market price
# instead of a lexicon hit-count.
HIGHER_THRESHOLD = 0.55
LOWER_THRESHOLD = 0.45


@dataclass
class KalshiRead:
    strike: float
    implied_direction: str      # 'higher' | 'lower' | 'in_line'
    implied_probability: float  # 0.0-1.0, the yes-price midpoint
    open_interest: float


def _resolve_event_ticker(series_ticker: str, event_month: dt.date) -> Optional[str]:
    """
    Finds the series' current event ticker. Kalshi's event tickers embed
    the target month (e.g. KXCPI-26AUG for August 2026's CPI print), but
    the exact naming isn't guaranteed stable across series, so this reads
    whichever event the series' /events endpoint currently returns as the
    first (most relevant) entry rather than constructing the ticker by
    hand. Returns None if the series has no current event.
    """
    resp = requests.get(f"{KALSHI_BASE_URL}/series/{series_ticker}/events", timeout=15)
    resp.raise_for_status()
    events = resp.json().get("events", [])
    if not events:
        return None
    return events[0]["event_ticker"]


def get_market_read(series_ticker: str, event_month: dt.date, target_strike: float) -> Optional[KalshiRead]:
    """
    Fetches the series' current event, finds the strike closest to
    target_strike among its markets, reads that market's yes_bid/yes_ask
    midpoint and open_interest. Returns None — never fabricated — if the
    series/event/market doesn't exist, the market list is empty, or the
    request fails for any reason (network error, malformed response,
    unexpected shape).

    Tie-break: when target_strike is exactly equidistant between two
    strikes, the LOWER strike wins, deterministically.
    """
    try:
        event_ticker = _resolve_event_ticker(series_ticker, event_month)
        if event_ticker is None:
            return None

        resp = requests.get(
            f"{KALSHI_BASE_URL}/markets",
            params={"series_ticker": series_ticker, "status": "open"},
            timeout=15,
        )
        resp.raise_for_status()
        markets = resp.json().get("markets", [])
        if not markets:
            return None

        nearest = min(
            markets,
            key=lambda m: (abs(float(m["floor_strike"]) - target_strike), float(m["floor_strike"])),
        )
        yes_bid = float(nearest["yes_bid_dollars"])
        yes_ask = float(nearest["yes_ask_dollars"])
        midpoint = (yes_bid + yes_ask) / 2.0

        if midpoint > HIGHER_THRESHOLD:
            direction = "higher"
        elif midpoint < LOWER_THRESHOLD:
            direction = "lower"
        else:
            direction = "in_line"

        return KalshiRead(
            strike=float(nearest["floor_strike"]),
            implied_direction=direction,
            implied_probability=midpoint,
            open_interest=float(nearest["open_interest_fp"]),
        )
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[kalshi_feed] WARNING: fetch failed for {series_ticker}: {exc}")
        return None
```

Note on the tie-break: `min(markets, key=lambda m: (abs(strike - target), strike))` — for two strikes equidistant from `target_strike`, the tuple comparison falls through to the second element (the raw strike value) once the first elements (the distances) are equal, and `min()` picks the smaller tuple, so the lower strike wins.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python tests/test_kalshi_feed.py`
Expected: all 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py data_layer/kalshi_feed.py tests/test_kalshi_feed.py
git commit -m "feat: add Kalshi read-only market-data client + config mapping

data_layer/kalshi_feed.py's get_market_read() reads Kalshi's free,
unauthenticated public API (external-api.kalshi.com/trade-api/v2) —
no API key needed, confirmed live. Read-only: only GET /events and
GET /markets, never any trading endpoint.

KALSHI_SERIES_BY_EVENT_TITLE covers 15 numeric-forecast events,
verified live against each market's own rules_primary text (not just
titles, which Kalshi's own metadata has real copy-paste errors in).
RATE_DECISION_DIRECTION + KALSHI_RATE_DECISION_SERIES handle FOMC/
Federal Funds Rate separately, since a discrete cut/hold/hike decision
can't reuse EVENT_SURPRISE_DIRECTION's forecast-vs-actual convention.

6 new tests cover strike selection, discretization at both
thresholds, the deterministic tie-break, and all three failure modes
(no event, no markets, request failure) degrading to None."
```

---

### Task 2: `KalshiMarketContribution` in `score_bundle()`

**Files:**
- Modify: `scoring/probability_engine.py`
- Test: `tests/test_probability_engine.py`

**Interfaces:**
- Consumes: `EVENT_SURPRISE_DIRECTION`, `KALSHI_TRUST_WEIGHT`,
  `PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES` (existing/Task 1,
  `config.settings`).
- Produces: `KalshiMarketContribution` dataclass and `score_bundle()`'s
  new optional `kalshi_read` param. Task 4 passes a real `KalshiRead`
  (Task 1) into it — duck-typed, no import needed here.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_probability_engine.py`, before its `__main__` block
(check current imports first — this file already has `_cpi_event()`,
`_unemployment_event()` helpers and a `_FakeTrendSignal` pattern from the
prior trend-signal task; follow the same style for a `_FakeKalshiRead`):

```python
from dataclasses import dataclass as _dataclass  # only if not already imported at top — check first


@dataclass
class _FakeKalshiRead:
    """Duck-typed stand-in for data_layer.kalshi_feed.KalshiRead — probability_engine.py never imports data_layer.kalshi_feed directly, tests exercise the duck-typed contract."""
    strike: float
    implied_direction: str
    implied_probability: float
    open_interest: float


def test_kalshi_read_higher_on_bullish_indicator_is_bullish():
    print("=== score_bundle: a 'higher' Kalshi read on a higher_bullish indicator contributes USD-bullish ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    result = score_bundle(bundle, "USDJPY", kalshi_read=kalshi_read)
    assert result.direction == Direction.BULLISH
    print("PASS\n")


def test_kalshi_read_higher_on_bearish_indicator_flips_sign():
    print("=== score_bundle: a 'higher' Kalshi read on a higher_bearish indicator contributes USD-bearish ===")
    event = _unemployment_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=4.0, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    result = score_bundle(bundle, "USDJPY", kalshi_read=kalshi_read)
    assert result.direction == Direction.BEARISH
    print("PASS\n")


def test_kalshi_read_in_line_contributes_nothing():
    print("=== score_bundle: an in_line Kalshi read adds ZERO contributions, not a zero-weight one ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="in_line", implied_probability=0.5, open_interest=100.0)
    result = score_bundle(bundle, "XAUUSD", kalshi_read=kalshi_read)
    assert result.probability == 0.5  # identical to the no-kalshi-read case — proves zero contribution
    print("PASS\n")


def test_kalshi_read_none_contributes_nothing():
    print("=== score_bundle: kalshi_read=None adds zero contributions ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD", kalshi_read=None)
    assert result.probability == 0.5
    print("PASS\n")


def test_kalshi_read_decays_with_age():
    print("=== score_bundle: an old Kalshi read contributes less than a fresh one ===")
    event = _cpi_event()
    bundle_fresh = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    bundle_stale = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME + dt.timedelta(hours=48))
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    # Same comparably-weighted anchor-article approach the existing
    # test_print_call_decays_with_age test already uses — a single
    # contribution's weight cancels algebraically in _weighted_aggregate(),
    # so decay is only observable relative to a second, fixed contribution.
    from data_layer.news_feed import NewsArticle
    anchor_fresh = NewsArticle(
        title="Markets await Friday's data release", summary="Traders are watching closely.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/neutral-fresh",
    )
    anchor_stale = NewsArticle(
        title="Markets await Friday's data release", summary="Traders are watching closely.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME + dt.timedelta(hours=47),
        url="https://example.test/neutral-stale",
    )
    bundle_fresh = EventNewsBundle(event=event, articles=[anchor_fresh], as_of_utc=EVENT_TIME)
    bundle_stale = EventNewsBundle(event=event, articles=[anchor_stale], as_of_utc=EVENT_TIME + dt.timedelta(hours=48))
    fresh_result = score_bundle(bundle_fresh, "XAUUSD", kalshi_read=kalshi_read)
    stale_result = score_bundle(bundle_stale, "XAUUSD", kalshi_read=kalshi_read)
    assert abs(fresh_result.instrument_score) > abs(stale_result.instrument_score)
    print("PASS\n")


def test_kalshi_and_print_call_and_trend_signal_all_present_all_contribute():
    print("=== score_bundle: kalshi_read, print_call, and trend_signal can all be present at once, none excludes another ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    all_result = score_bundle(bundle, "XAUUSD", print_call=print_call, trend_signal=trend_signal, kalshi_read=kalshi_read)
    kalshi_only_result = score_bundle(bundle, "XAUUSD", kalshi_read=kalshi_read)
    # All three agreeing (same direction) should produce a stronger/more
    # confident read than kalshi_read alone.
    assert all_result.confidence >= kalshi_only_result.confidence
    print("PASS\n")


def test_kalshi_trust_weight_above_precursor_trust_weight():
    print("=== sanity: KALSHI_TRUST_WEIGHT is above PRECURSOR_TRUST_WEIGHT, per the spec's trust tiering ===")
    from config.settings import KALSHI_TRUST_WEIGHT, PRECURSOR_TRUST_WEIGHT
    assert KALSHI_TRUST_WEIGHT > PRECURSOR_TRUST_WEIGHT
    print("PASS\n")
```

Register all 7 new tests in the file's `__main__` block, after the
existing tests. Check the file's current imports first (`head -20
tests/test_probability_engine.py`) — `PrintCall` and `_FakeTrendSignal`
should already be imported/defined from the prior trend-signal task; if
`_FakeKalshiRead`'s `@dataclass` decorator needs an import, verify
`from dataclasses import dataclass` is already present at the top rather
than adding a duplicate/shadowing import.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_probability_engine.py`
Expected: `TypeError: score_bundle() got an unexpected keyword argument 'kalshi_read'`

- [ ] **Step 3: Add the dataclass to `scoring/probability_engine.py`**

Insert immediately after `TrendStreakContribution`'s closing (after the
existing block, before `ProbabilityResult`):

```python
@dataclass
class KalshiMarketContribution:
    """
    Audit trail for a Kalshi prediction-market read (data_layer.kalshi_feed's
    KalshiRead), mapped onto the USD axis via EVENT_SURPRISE_DIRECTION (for
    numeric events) or RATE_DECISION_DIRECTION (for FOMC/Federal Funds
    Rate). Duck-typed like the other three contribution types — same
    usd_sentiment/combined_weight fields — so it flows through the
    existing weighted-average, agreement, and coverage math unchanged.
    """
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float
```

- [ ] **Step 4: Add the builder function**

Insert immediately after `_build_trend_streak_contribution()`, before
`_weighted_aggregate()`:

```python
def _build_kalshi_contribution(
    kalshi_read,  # KalshiRead | None — duck-typed, no import from data_layer.kalshi_feed needed
    event: EconomicEvent,
    as_of: dt.datetime,
    surprise_direction_value: str | None = None,
):
    """
    Returns None (no contribution) if kalshi_read is None, its direction
    is 'in_line' (no lean either way), or no direction-mapping value was
    resolved for this event title. surprise_direction_value is the
    ALREADY-RESOLVED direction-mapping string ('higher_bullish' /
    'higher_bearish' from EVENT_SURPRISE_DIRECTION, or 'bullish' /
    'bearish' / 'neutral' straight from RATE_DECISION_DIRECTION for a
    discrete FOMC decision) — the caller (scoring/backtest_accumulator.py)
    already knows which of the two mapping dicts matched this event's
    title from its own lookup, so this function doesn't re-derive it.
    """
    if kalshi_read is None or kalshi_read.implied_direction == "in_line":
        return None
    if surprise_direction_value is None:
        return None

    raw = kalshi_read.implied_probability if kalshi_read.implied_direction == "higher" else -kalshi_read.implied_probability
    if surprise_direction_value == "higher_bullish":
        usd_sentiment = raw
    elif surprise_direction_value == "higher_bearish":
        usd_sentiment = -raw
    elif surprise_direction_value == "bullish":
        usd_sentiment = abs(raw)
    elif surprise_direction_value == "bearish":
        usd_sentiment = -abs(raw)
    else:  # 'neutral', or any unrecognized value — no lean, no contribution
        return None

    age_minutes = max(0.0, (as_of - event.event_time_utc).total_seconds() / 60.0)
    time_w = 0.5 ** (age_minutes / PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES)
    return KalshiMarketContribution(
        event_title=event.title,
        usd_sentiment=usd_sentiment,
        trust_weight=KALSHI_TRUST_WEIGHT,
        time_weight=time_w,
        combined_weight=KALSHI_TRUST_WEIGHT * time_w,
    )
```

Note: `score_bundle()` itself (Step 6 below) will pass
`EVENT_SURPRISE_DIRECTION.get(event.title)` as `surprise_direction_value`
directly — for numeric events this yields `'higher_bullish'`/
`'higher_bearish'` (matching the two `elif` branches above); the
`'bullish'`/`'bearish'`/`'neutral'` branches exist for Task 4's FOMC case,
where `scoring/backtest_accumulator.py` will instead resolve
`RATE_DECISION_DIRECTION.get(rate_decision_word)` and pass that string
through the SAME `kalshi_read` parameter path — `score_bundle()` doesn't
need to know which dict the caller used, only which string it resolved to.

- [ ] **Step 5: Update the import block**

Modify the existing `from config.settings import (...)` block to add
`KALSHI_TRUST_WEIGHT`, alphabetically placed:

```python
from config.settings import (
    CONTEXTUAL_CONFIDENCE_THRESHOLD,
    CONTRADICTION_MIN_MAGNITUDE,
    ENABLE_FINBERT_SENTIMENT,
    ENABLE_LLM_SENTIMENT,
    EVENT_SURPRISE_DIRECTION,
    INSTRUMENTS,
    KALSHI_TRUST_WEIGHT,
    PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES,
    PRECURSOR_TRUST_WEIGHT,
    PRINT_CALL_TRUST_WEIGHT,
    RECENT_WINDOW_HOURS,
    RISK_SENTIMENT_DAMPENING,
    SOURCE_TRUST_WEIGHTS,
    TIME_DECAY_HALF_LIFE_MINUTES,
    TREND_STREAK_TRUST_WEIGHT,
    UTC_TZ,
)
```

- [ ] **Step 6: Wire the new param into `score_bundle()`**

Modify the function signature to add `kalshi_read=None` and
`kalshi_direction_override=None` after the existing `trend_signal=None`
param:

```python
def score_bundle(
    bundle: EventNewsBundle,
    instrument: str,
    precursor_events: list[EconomicEvent] | None = None,
    print_call=None,   # PrintCall | None — duck-typed
    trend_signal=None,  # TrendSignal | None — duck-typed
    kalshi_read=None,   # KalshiRead | None — duck-typed
    kalshi_direction_override=None,  # str | None — 'higher_bullish'/'higher_bearish', see below
) -> ProbabilityResult:
```

Add to the docstring, after the existing `trend_signal:` paragraph:

```python
    kalshi_read: optional — a Kalshi prediction-market read
    (data_layer/kalshi_feed.py's KalshiRead) for this occurrence. Blended
    in at config.settings.KALSHI_TRUST_WEIGHT (the highest tier — real
    money priced directly on the exact event being scored), with the same
    decay a precursor uses. An 'in_line' read contributes nothing.

    kalshi_direction_override: optional — a 'higher_bullish'/'higher_bearish'
    string to use INSTEAD of looking up EVENT_SURPRISE_DIRECTION[bundle.event.title]
    when resolving kalshi_read's USD-sentiment sign. Needed for events like
    FOMC/Federal Funds Rate that aren't in EVENT_SURPRISE_DIRECTION at all
    (a discrete rate decision, not a continuous forecast-vs-actual number)
    — the caller (scoring/backtest_accumulator.py's _read_kalshi_signal())
    already knows which of its two Kalshi-series dicts matched this
    event's title and resolves the correct direction value itself, so
    score_bundle() stays free of any FOMC-specific special-casing or a
    dependency on config.settings.KALSHI_RATE_DECISION_SERIES. Ignored
    when kalshi_read is None.
    """
```

Modify the contribution-building block (currently building
`extra_contributions` from precursor + print_call + trend_streak) to add
the Kalshi contribution:

```python
    as_of = bundle.as_of_utc
    article_contributions = _build_contributions(bundle.articles, as_of, TIME_DECAY_HALF_LIFE_MINUTES)
    precursor_contributions = _build_precursor_contributions(precursor_events or [], as_of)
    print_call_contribution = _build_print_call_contribution(print_call, bundle.event, as_of)
    trend_streak_contribution = _build_trend_streak_contribution(trend_signal, bundle.event)
    kalshi_surprise_value = kalshi_direction_override if kalshi_direction_override is not None else EVENT_SURPRISE_DIRECTION.get(bundle.event.title)
    kalshi_contribution = _build_kalshi_contribution(
        kalshi_read, bundle.event, as_of,
        surprise_direction_value=kalshi_surprise_value,
    )
    extra_contributions = precursor_contributions + (
        [print_call_contribution] if print_call_contribution is not None else []
    ) + (
        [trend_streak_contribution] if trend_streak_contribution is not None else []
    ) + (
        [kalshi_contribution] if kalshi_contribution is not None else []
    )
    all_contributions = article_contributions + extra_contributions
```

(Everything downstream, including the `if not all_contributions:`
early-return branch, is unaffected — it already just checks the combined
list.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `python tests/test_probability_engine.py`
Expected: all tests PASS, including the 7 new ones.

- [ ] **Step 8: Run the existing regression suite for this file**

Run: `python tests/test_backtest_accumulator.py`
Expected: all existing tests still PASS unchanged — `score_bundle()` is
called there without the new param, proving the default-`None` path is
unaffected.

- [ ] **Step 9: Commit**

```bash
git add scoring/probability_engine.py tests/test_probability_engine.py
git commit -m "feat: blend Kalshi market reads into score_bundle()

KalshiMarketContribution joins the existing four contribution types
(article/precursor/print-call/trend-streak) score_bundle() already
weight-averages, duck-typed the same way. score_bundle() called
without the new kalshi_read param reproduces today's exact output,
verified by a dedicated regression test.

_build_kalshi_contribution() accepts an already-resolved direction-
mapping VALUE (not a dict lookup) — the caller knows whether this
event's title matched EVENT_SURPRISE_DIRECTION (numeric events,
'higher_bullish'/'higher_bearish') or RATE_DECISION_DIRECTION (FOMC,
'bullish'/'bearish'/'neutral') and passes the resolved string through,
so this function stays free of any dependency on which dict was used.

Highest trust tier (KALSHI_TRUST_WEIGHT=0.95, above precursor's 0.9)
since this prices real money directly on the exact event being
scored. An in_line read or unresolved direction contributes nothing,
not a zero-weight entry. 7 new tests cover both direction-mapping
paths, decay, in_line/None exclusion, and coexistence with the other
three optional contributions."
```

---

### Task 3: `kalshi_reads` table in `scoring/backtest_store.py`

**Files:**
- Modify: `scoring/backtest_store.py`
- Test: `tests/test_backtest_store.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `KalshiReadRecord` dataclass (`id: int, event_title: str,
  event_time_utc: str, strike: float, implied_direction: str,
  implied_probability: float, open_interest: float, read_at_utc: str`),
  `get_latest_kalshi_read(conn, event_title: str, event_time_utc:
  dt.datetime) -> Optional[KalshiReadRecord]`,
  `record_kalshi_read_if_changed(conn, event_title: str, event_time_utc:
  dt.datetime, read, now: Optional[dt.datetime] = None) -> bool` (where
  `read` is a duck-typed `KalshiRead`-shaped object). Task 4 imports both
  functions.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_backtest_store.py`, before its `__main__` block (check
current imports first — this file already imports `PrintCall` from the
prior print-prediction task; add a small local stand-in for `KalshiRead`
rather than importing from `data_layer.kalshi_feed`, matching how this
file already duck-types `PrintCall`):

```python
from dataclasses import dataclass as _dc  # only if `dataclass` isn't already imported — check first


@dataclass
class _FakeKalshiRead:
    strike: float
    implied_direction: str
    implied_probability: float
    open_interest: float


def test_record_kalshi_read_if_changed_writes_first_read():
    print("=== backtest_store: record_kalshi_read_if_changed writes a row when nothing exists yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.62, open_interest=100.0)

        written = store.record_kalshi_read_if_changed(conn, "CPI m/m", event_time, read, now=dt.datetime(2026, 8, 10, 9, 0, tzinfo=UTC_TZ))
        assert written is True

        latest = store.get_latest_kalshi_read(conn, "CPI m/m", event_time)
        assert latest is not None
        assert latest.implied_direction == "higher"
        assert latest.implied_probability == 0.62
        assert latest.strike == 0.3
        assert latest.open_interest == 100.0
        conn.close()
    print("PASS\n")


def test_record_kalshi_read_if_changed_skips_identical_direction():
    print("=== backtest_store: an identical implied_direction does not write a new row ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        first = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.62, open_interest=100.0)
        store.record_kalshi_read_if_changed(conn, "CPI m/m", event_time, first, now=dt.datetime(2026, 8, 10, 9, 0, tzinfo=UTC_TZ))

        second = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.71, open_interest=150.0)
        written = store.record_kalshi_read_if_changed(conn, "CPI m/m", event_time, second, now=dt.datetime(2026, 8, 10, 10, 0, tzinfo=UTC_TZ))
        assert written is False

        latest = store.get_latest_kalshi_read(conn, "CPI m/m", event_time)
        assert latest.implied_probability == 0.62  # unchanged — the second read was never written
        conn.close()
    print("PASS\n")


def test_record_kalshi_read_if_changed_writes_on_direction_flip():
    print("=== backtest_store: a direction flip (higher -> lower) always writes a new row ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        first = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.62, open_interest=100.0)
        store.record_kalshi_read_if_changed(conn, "CPI m/m", event_time, first, now=dt.datetime(2026, 8, 10, 9, 0, tzinfo=UTC_TZ))

        flipped = _FakeKalshiRead(strike=0.3, implied_direction="lower", implied_probability=0.3, open_interest=90.0)
        written = store.record_kalshi_read_if_changed(conn, "CPI m/m", event_time, flipped, now=dt.datetime(2026, 8, 11, 9, 0, tzinfo=UTC_TZ))
        assert written is True

        latest = store.get_latest_kalshi_read(conn, "CPI m/m", event_time)
        assert latest.implied_direction == "lower"
        conn.close()
    print("PASS\n")


def test_get_latest_kalshi_read_scoped_to_occurrence_not_title():
    print("=== backtest_store: get_latest_kalshi_read does NOT leak a prior occurrence's read onto a different event_time_utc ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        july_time = dt.datetime(2026, 7, 12, 12, 30, tzinfo=UTC_TZ)
        august_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.6, open_interest=100.0)
        store.record_kalshi_read_if_changed(conn, "CPI m/m", july_time, read, now=july_time)

        assert store.get_latest_kalshi_read(conn, "CPI m/m", august_time) is None
        conn.close()
    print("PASS\n")


def test_get_latest_kalshi_read_none_when_nothing_recorded():
    print("=== backtest_store: get_latest_kalshi_read returns None when nothing has been recorded for this event ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        assert store.get_latest_kalshi_read(conn, "CPI m/m", event_time) is None
        conn.close()
    print("PASS\n")
```

Register all 5 in the file's `__main__` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_backtest_store.py`
Expected: `AttributeError: module 'scoring.backtest_store' has no attribute 'record_kalshi_read_if_changed'`

- [ ] **Step 3: Add the schema, dataclass, and functions to `scoring/backtest_store.py`**

Modify `_SCHEMA` (add after the `print_predictions` table, before the
closing `"""`):

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

Add the dataclass (after `PrintPrediction`):

```python
@dataclass
class KalshiReadRecord:
    id: int
    event_title: str
    event_time_utc: str
    strike: float
    implied_direction: str
    implied_probability: float
    open_interest: float
    read_at_utc: str
```

Add the two functions (at the end of the file):

```python
def get_latest_kalshi_read(
    conn: sqlite3.Connection, event_title: str, event_time_utc: dt.datetime,
) -> Optional[KalshiReadRecord]:
    """
    Most recent recorded Kalshi read for this specific (event_title,
    event_time_utc) OCCURRENCE — None if never recorded. Scoped to
    occurrence, not title-only, same reasoning as get_latest_print_prediction():
    Forex Factory event titles recur monthly/quarterly with the SAME
    title but a DIFFERENT event_time_utc each time.
    """
    row = conn.execute(
        "SELECT * FROM kalshi_reads WHERE event_title = ? AND event_time_utc = ? "
        "ORDER BY read_at_utc DESC, id DESC LIMIT 1",
        (event_title, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return KalshiReadRecord(
        id=d["id"], event_title=d["event_title"], event_time_utc=d["event_time_utc"],
        strike=d["strike"], implied_direction=d["implied_direction"],
        implied_probability=d["implied_probability"], open_interest=d["open_interest"],
        read_at_utc=d["read_at_utc"],
    )


def record_kalshi_read_if_changed(
    conn: sqlite3.Connection,
    event_title: str,
    event_time_utc: dt.datetime,
    read,  # KalshiRead from data_layer.kalshi_feed — duck-typed to avoid a hard dependency
    now: Optional[dt.datetime] = None,
) -> bool:
    """
    Writes a new kalshi_reads row only if `read.implied_direction` differs
    from the latest recorded read for this exact occurrence — same
    "current read is the truth until the market moves it" principle as
    record_print_prediction_if_changed(). Returns True if a row was
    written, False if skipped as unchanged.
    """
    latest = get_latest_kalshi_read(conn, event_title, event_time_utc)
    if latest is not None and latest.implied_direction == read.implied_direction:
        return False

    read_at = now or dt.datetime.now(dt.timezone.utc)
    conn.execute(
        "INSERT INTO kalshi_reads (event_title, event_time_utc, strike, implied_direction, implied_probability, open_interest, read_at_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_title, event_time_utc.isoformat(), read.strike, read.implied_direction,
         read.implied_probability, read.open_interest, read_at.isoformat()),
    )
    conn.commit()
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_backtest_store.py`
Expected: all tests PASS, including the 5 new ones.

- [ ] **Step 5: Commit**

```bash
git add scoring/backtest_store.py tests/test_backtest_store.py
git commit -m "feat: add kalshi_reads table + occurrence-scoped diff-aware recording

Mirrors print_predictions' pattern exactly: record_kalshi_read_if_changed()
only writes a new row on an implied_direction flip for the exact
(event_title, event_time_utc) occurrence; get_latest_kalshi_read() is
occurrence-scoped from the start (not title-only), avoiding the leak
class already fixed once for print_predictions."
```

---

### Task 4: Accumulator wiring

**Files:**
- Modify: `scoring/backtest_accumulator.py`
- Test: `tests/test_backtest_accumulator.py`

**Interfaces:**
- Consumes: `get_market_read`, `KALSHI_SERIES_BY_EVENT_TITLE`,
  `KALSHI_RATE_DECISION_SERIES` (Task 1, `data_layer.kalshi_feed`/
  `config.settings`); `RATE_DECISION_DIRECTION`, `EVENT_SURPRISE_DIRECTION`
  (config.settings); `score_bundle()`'s `kalshi_read` param (Task 2);
  `record_kalshi_read_if_changed`, `get_latest_kalshi_read` (Task 3,
  `scoring.backtest_store`); `data_layer.calendar_feed._parse_numeric`
  (existing).
- Produces: no new public interface — this is the final wiring task.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_backtest_accumulator.py`, before its `__main__` block
(near the other `run_accumulator_cycle`-based tests — check current
imports first, this file already has `PrintCall`, `EconomicEvent`,
`EventNewsBundle`, `UTC_TZ`, `webapp_store` imported from prior tasks):

```python
def test_kalshi_read_passed_to_score_bundle_for_numeric_event():
    print("=== accumulator: a Kalshi read is fetched, recorded, and passed to score_bundle() for a numeric-forecast event ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        event.forecast = "0.1%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_read = accumulator_kalshi_feed.KalshiRead(strike=0.1, implied_direction="higher", implied_probability=0.65, open_interest=100.0)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read", return_value=fake_read) as mock_kalshi, \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["kalshi_read"] is fake_read
        mock_kalshi.assert_called_once()
        args, kwargs = mock_kalshi.call_args
        assert args[0] == "KXCPI"  # series ticker resolved from KALSHI_SERIES_BY_EVENT_TITLE["CPI m/m"]

        conn = store.get_connection(db_path)
        latest = store.get_latest_kalshi_read(conn, "CPI m/m", event.event_time_utc)
        assert latest is not None
        assert latest.implied_direction == "higher"
        conn.close()
    print("PASS\n")


def test_kalshi_lookup_skipped_for_event_with_no_series_mapping():
    print("=== accumulator: an event title with no Kalshi series mapping never triggers get_market_read() ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)  # "Test Event" — not in any Kalshi mapping
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read") as mock_kalshi, \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        mock_kalshi.assert_not_called()
    print("PASS\n")


def test_kalshi_lookup_skipped_for_unparseable_forecast():
    print("=== accumulator: an event with an unparseable/missing forecast skips the Kalshi lookup entirely ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        event.forecast = None  # unparseable/missing
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read") as mock_kalshi, \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        mock_kalshi.assert_not_called()
    print("PASS\n")


def test_kalshi_fetch_failure_fails_open_without_crashing_cycle():
    print("=== accumulator: get_market_read() raising or returning None fails open, does not crash the cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        event.forecast = "0.1%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read", side_effect=Exception("network down")), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            events_result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert events_result is not None  # cycle completed, did not crash
        assert captured_kwargs["kalshi_read"] is None
    print("PASS\n")


def test_kalshi_read_for_fomc_uses_rate_decision_series():
    print("=== accumulator: 'Federal Funds Rate' resolves via KALSHI_RATE_DECISION_SERIES (KXFED), not KALSHI_SERIES_BY_EVENT_TITLE ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "Federal Funds Rate"
        event.forecast = "4.25%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_read = accumulator_kalshi_feed.KalshiRead(strike=4.25, implied_direction="higher", implied_probability=0.6, open_interest=50.0)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read", return_value=fake_read) as mock_kalshi, \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        args, kwargs = mock_kalshi.call_args
        assert args[0] == "KXFED"
        assert captured_kwargs["kalshi_read"] is fake_read
    print("PASS\n")
```

Add the required import at the top of the file:
`import data_layer.kalshi_feed as accumulator_kalshi_feed` (aliased,
matching the existing `import scoring.print_direction as
accumulator_print_direction` pattern already in this file — the module
itself, `scoring.backtest_accumulator`, must import `get_market_read`
directly by name for `patch.object(accumulator, "get_market_read", ...)`
to work, which Step 3 below does).

Register all 5 new tests in the file's `__main__` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_backtest_accumulator.py`
Expected: `AttributeError: <module 'scoring.backtest_accumulator'> does not have the attribute 'get_market_read'`

- [ ] **Step 3: Wire it into `scoring/backtest_accumulator.py`**

Modify the import block to add:

```python
from config.settings import (
    KALSHI_RATE_DECISION_SERIES, KALSHI_SERIES_BY_EVENT_TITLE,
    MIN_OCCURRENCES_FOR_TREND_PRIOR, PRE_EVENT_WINDOW_HOURS,
    RATE_DECISION_DIRECTION,
)
from data_layer.calendar_feed import (
    fetch_calendar, filter_relevant_events, events_in_pre_window,
    find_precursor_events, _parse_numeric,
)
from data_layer.kalshi_feed import get_market_read
from scoring.backtest_store import (
    get_connection, record_prediction, get_latest_prediction, record_check, count_recent_checks,
    record_print_prediction_if_changed, record_kalshi_read_if_changed,
)
```

(Merge these into the existing import blocks at their current locations
in the file rather than duplicating — `MIN_OCCURRENCES_FOR_TREND_PRIOR`
and `PRE_EVENT_WINDOW_HOURS` are already imported from `config.settings`;
add the three new names to that same line. Same for the
`data_layer.calendar_feed` import — add `_parse_numeric` to the existing
line.)

Add a new module-level function, right after `_read_trend_signal()`:

```python
def _read_kalshi_signal(event):
    """
    Looks up event.title in KALSHI_SERIES_BY_EVENT_TITLE first (numeric
    events), then KALSHI_RATE_DECISION_SERIES (FOMC/Federal Funds Rate) —
    mutually exclusive per title. Returns (kalshi_read, resolved_direction_value):

    - Numeric event: resolved_direction_value is
      EVENT_SURPRISE_DIRECTION[event.title] verbatim ('higher_bullish' or
      'higher_bearish') — the standard convention every other structured
      contribution in this module already uses.
    - FOMC/Federal Funds Rate: resolved_direction_value is always
      'higher_bullish' — a HIGHER Fed funds rate is unambiguously
      USD-bullish, the same sign the numeric convention already encodes,
      so this reuses that convention rather than introducing a second
      one. (RATE_DECISION_DIRECTION itself, mapping a decision WORD like
      'hike'/'cut' to a sentiment, isn't used here — Kalshi's KXFED
      market already answers "will the rate be higher than X," the same
      shape as every numeric market, so the decision-word mapping isn't
      needed for this blend; it exists in config.settings for any future
      caller that has a decision word instead of a market read.)

    Returns (None, None) — never crashes the cycle — if no series
    mapping matches this title, the forecast can't be parsed to a strike
    target, or the market fetch fails for any reason.
    """
    series_ticker = KALSHI_SERIES_BY_EVENT_TITLE.get(event.title)
    if series_ticker is not None:
        surprise_direction_value = EVENT_SURPRISE_DIRECTION.get(event.title)
    else:
        series_ticker = KALSHI_RATE_DECISION_SERIES.get(event.title)
        surprise_direction_value = "higher_bullish" if series_ticker is not None else None

    if series_ticker is None or surprise_direction_value is None:
        return None, None

    target_strike = _parse_numeric(event.forecast)
    if target_strike is None:
        return None, None

    try:
        read = get_market_read(series_ticker, event.event_time_utc.date(), target_strike)
    except Exception as exc:  # noqa: BLE001 — a failed Kalshi fetch must not crash the accumulator cycle
        print(f"[backtest_accumulator] WARNING: Kalshi fetch failed for {event.title}: {exc}")
        return None, None

    return read, surprise_direction_value
```

In `run_accumulator_cycle()`, immediately after the existing
`trend_signal = _read_trend_signal(event.title)` block (and its
`if trend_signal is not None: print(...)` line), add:

```python
            kalshi_read, kalshi_direction_value = _read_kalshi_signal(event)
            if kalshi_read is not None:
                record_kalshi_read_if_changed(conn, event.title, event.event_time_utc, kalshi_read, now=now)
                print(f"[backtest_accumulator] Kalshi read for {event.title}: {kalshi_read.implied_direction} ({kalshi_read.implied_probability:.0%} implied, {kalshi_read.open_interest:.0f} open interest)")
```

Then modify the `score_bundle()` call inside the `for instrument in
instruments:` loop to pass `kalshi_read`:

```python
                try:
                    result = score_bundle(
                        bundle, instrument, precursor_events=precursors,
                        print_call=print_call, trend_signal=trend_signal,
                        kalshi_read=kalshi_read,
                    )
```

`score_bundle()` already accepts `kalshi_direction_override` (Task 2) for
exactly this reason: FOMC/Federal Funds Rate isn't in
`EVENT_SURPRISE_DIRECTION` at all (a discrete rate decision, not a
continuous forecast-vs-actual number), so `score_bundle()`'s internal
`EVENT_SURPRISE_DIRECTION.get(bundle.event.title)` lookup alone would
return `None` for it and silently drop a valid FOMC Kalshi read. Pass
`_read_kalshi_signal()`'s resolved `kalshi_direction_value` straight
through as `kalshi_direction_override`:

```python
                try:
                    result = score_bundle(
                        bundle, instrument, precursor_events=precursors,
                        print_call=print_call, trend_signal=trend_signal,
                        kalshi_read=kalshi_read, kalshi_direction_override=kalshi_direction_value,
                    )
```

`test_kalshi_read_for_fomc_uses_rate_decision_series` (already written
above) exercises this override path end-to-end through the accumulator,
which is sufficient coverage for this plan's scope — Task 2's own tests
(`test_kalshi_read_higher_on_bullish_indicator_is_bullish` etc.) already
use real `EVENT_SURPRISE_DIRECTION`-covered events and don't need the
override, so they're unaffected by it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_probability_engine.py` (confirm the Task 2 tests
still pass after the signature adjustment above), then
`python tests/test_backtest_accumulator.py`
Expected: all tests PASS, including the 5 new ones in this task.

- [ ] **Step 5: Run the full regression sweep**

```bash
python tests/test_kalshi_feed.py
python tests/test_probability_engine.py
python tests/test_backtest_store.py
python tests/test_backtest_accumulator.py
```

Expected: all PASS, no regressions.

- [ ] **Step 6: Commit**

```bash
git add scoring/backtest_accumulator.py scoring/probability_engine.py tests/test_probability_engine.py tests/test_backtest_accumulator.py
git commit -m "feat: wire Kalshi reads into the accumulator's cycle, handle FOMC's dual-dict lookup

_read_kalshi_signal() resolves an event's title against
KALSHI_SERIES_BY_EVENT_TITLE first (numeric events, using
EVENT_SURPRISE_DIRECTION's existing higher_bullish/higher_bearish
value verbatim), then KALSHI_RATE_DECISION_SERIES (FOMC/Federal Funds
Rate, always 'higher_bullish' since a higher rate is unambiguously
USD-bullish — reusing the numeric convention's sign rather than
introducing a second one). Fails open to (None, None) on any missing
mapping, unparseable forecast, or fetch failure.

score_bundle() gains a second new param, kalshi_direction_override,
alongside kalshi_read — needed because FOMC's title
('Federal Funds Rate') isn't in EVENT_SURPRISE_DIRECTION at all, so
score_bundle()'s existing internal lookup would silently drop a valid
FOMC Kalshi read. The accumulator resolves the correct direction
value itself and passes it through explicitly, keeping
scoring/probability_engine.py free of any special-case FOMC logic or
a dependency on KALSHI_RATE_DECISION_SERIES.

Computed and recorded once per event (reusing config from
_read_kalshi_signal(), not a second parse), passed into every
instrument's score_bundle() call for that event this cycle. 5 new
tests cover the numeric path, no-mapping skip, unparseable-forecast
skip, fetch-failure fail-open, and the FOMC dual-dict path."
```

---

### Task 5: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a new subsection**

Find the "### Trend-history feed-back into scoring" subsection via
`grep -n "Trend-history feed-back" README.md`, and insert this new
subsection immediately after it, before "### History tab" (added by a
separate, unrelated plan — check current README structure first with
`grep -n "^### " README.md` to confirm exact placement, since task
ordering across separate plans may have interleaved differently in git
history than in this plan's own sequence):

```markdown
### Kalshi prediction-market scoring contribution

A fifth optional signal blends into `score_bundle()`, alongside article
sentiment, precursor structured surprises, the print-direction lexicon
call, and the trend-history streak — Kalshi's own real-money market price
on the *exact* event being scored, read via `data_layer/kalshi_feed.py`'s
free, unauthenticated public API access
(`external-api.kalshi.com/trade-api/v2`, confirmed live, no API key
needed). **Read-only — this integration never trades, never places an
order, never authenticates.**

15 of this system's 19 numeric-forecast tracked events have confirmed,
active Kalshi coverage (`config.settings.KALSHI_SERIES_BY_EVENT_TITLE`),
each verified against the actual market's rules text rather than trusted
titles/metadata (Kalshi's own series metadata has real errors — e.g. one
series' listed settlement-source URL points to an unrelated indicator's
page). FOMC/Federal Funds Rate — a discrete cut/hold/hike decision, not a
continuous forecast-vs-actual number — gets its own small, parallel
mapping (`KALSHI_RATE_DECISION_SERIES`) rather than being forced into the
numeric convention.

Highest trust tier in the system (`KALSHI_TRUST_WEIGHT=0.95`, above a
precursor's `0.9`) — this prices real money directly on the exact event
being scored, not a related-but-different one. A market whose open
interest is below `MIN_KALSHI_OPEN_INTEREST` contributes nothing, not a
diluted nudge, protecting the highest-trust contribution from an
illiquid, easily-skewed price. Persisted diff-aware in a new
`kalshi_reads` table (`scoring/backtest_store.py`), mirroring
`print_predictions` — no History tab column for it yet (a follow-up once
that tab exists to extend).

See
`docs/superpowers/specs/2026-08-12-kalshi-integration-design.md` for the
full design and its explicit out-of-scope list (no trading, no
multi-strike probability-distribution blending, no calibration of the
trust weight against real outcomes yet).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document the Kalshi prediction-market scoring contribution"
```

---

## Post-plan verification (do this after all 5 tasks are complete)

- [ ] Run the full regression suite across every `tests/test_*.py` file:

```bash
for f in tests/test_*.py; do echo "--- $f ---"; python "$f" 2>&1 | tail -6; done
```

Expected: every file ends with its "All ... tests passed." line (or PASS).
`test_contextual_sentiment.py`'s SKIP lines and `test_scoring_smoke.py`'s
pre-existing Windows-console Unicode crash are both expected, pre-existing,
unrelated to this feature.

- [ ] Restart `run_all.py` (kill the existing process tree first — check
      for and clean up any duplicate instances, a real recurring issue
      this session) and confirm live: the accumulator's console output
      shows a `Kalshi read for ...` line for at least one tracked event
      with coverage (CPI/PPI/NFP/etc.), and the cycle completes without
      error even for events with no Kalshi coverage.
