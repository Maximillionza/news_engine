# Trend-History Feed-Back Into Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Blend two new optional signals — this occurrence's print-direction
call and the event's historical beat/miss streak — into
`scoring/probability_engine.score_bundle()`'s existing weighted-average
instrument scoring, gated so neither contributes anything below a real
minimum-data threshold.

**Architecture:** Two new duck-typed contribution dataclasses
(`PrintCallContribution`, `TrendStreakContribution`) join the existing
`ArticleContribution`/`PrecursorContribution` list `score_bundle()` already
weight-averages. `webapp/trend.py` gets a new `compute_trend_signal()`
function sharing its streak/tally arithmetic with the existing
`summarize_trend()` via an extracted private helper. `scoring/backtest_accumulator.py`
opens a short-lived read-only connection to the dashboard's DB (mirroring
the existing reverse precedent in `webapp/app.py`) to fetch `event_history`
and compute the gated trend signal.

**Tech Stack:** Python 3.14, SQLite (stdlib `sqlite3`) — no new dependencies.

## Global Constraints

- `score_bundle()` called with neither `print_call` nor `trend_signal`
  (both default `None`) must reproduce today's exact output — every
  existing caller and test stays unaffected.
- `PRINT_CALL_TRUST_WEIGHT = 0.5`, `TREND_STREAK_TRUST_WEIGHT = 0.3`,
  `MIN_OCCURRENCES_FOR_TREND_PRIOR = 3` — exact values from the spec.
- An `in_line` print call, a `"Mixed"`/no-majority trend, or fewer than
  `MIN_OCCURRENCES_FOR_TREND_PRIOR` confirmed occurrences must all produce
  **zero contributions** (absent from the list), never a zero-weight
  entry with an arbitrary sign.
- The print-call contribution decays like a precursor
  (`PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES`); the trend-streak contribution
  never decays (`time_weight = 1.0` always).
- Both new contributions' `usd_sentiment` sign comes from
  `EVENT_SURPRISE_DIRECTION` (existing dict, `config/settings.py`) — never
  a new/duplicate mapping.
- A cross-pipeline read failure (dashboard DB missing/locked) must not
  crash the accumulator cycle — fail open to `trend_signal = None`, same
  pattern already used for calendar-fetch failures.
- `webapp/trend.py`'s existing `summarize_trend()` behavior must not
  change — all 7 existing tests in `tests/test_webapp_trend.py` must pass
  unmodified after the refactor.

---

### Task 1: `PrintCallContribution` + `TrendStreakContribution` in `score_bundle()`

**Files:**
- Modify: `config/settings.py` (new constants, near `PRECURSOR_TRUST_WEIGHT` at line 225)
- Modify: `scoring/probability_engine.py` (new dataclasses, builder functions, `score_bundle()` params)
- Test: `tests/test_probability_engine.py` (new file — `test_scoring_smoke.py` has a pre-existing, unrelated Windows console Unicode crash that makes it unreliable to run standalone, so this feature gets its own clean test file)

**Interfaces:**
- Consumes: `EVENT_SURPRISE_DIRECTION`, `PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES`
  (existing, `config/settings.py`); `EconomicEvent` (existing,
  `data_layer/calendar_feed.py`); `PrintCall` (existing,
  `scoring/print_direction.py` — fields `direction: str`, `confidence: float`,
  `article_count: int`).
- Produces: `PrintCallContribution`, `TrendStreakContribution` dataclasses
  (fields: `event_title: str, usd_sentiment: float, trust_weight: float,
  time_weight: float, combined_weight: float`) and `score_bundle()`'s two
  new optional params — `print_call: "PrintCall | None" = None`,
  `trend_signal: "TrendSignal | None" = None` (where `TrendSignal` is a
  forward reference to Task 2's dataclass — Task 1 does NOT import
  `webapp.trend` itself, since `scoring/probability_engine.py` must stay
  free of any dependency on `webapp/` — only `scoring/backtest_accumulator.py`,
  in Task 3, imports both `probability_engine` and `webapp.trend` and
  wires them together. Task 1's `_build_trend_streak_contribution()` takes
  a duck-typed object with `.direction`/`.strength` attributes, not an
  imported `TrendSignal` type).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_probability_engine.py`:

```python
"""
Tests for scoring/probability_engine.py's PrintCallContribution and
TrendStreakContribution — the two new optional signals that blend into
score_bundle()'s existing weighted-average math. No network needed.
"""
import datetime as dt
import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
from scoring.probability_engine import score_bundle, Direction
from scoring.print_direction import PrintCall

EVENT_TIME = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)


@dataclass
class _FakeTrendSignal:
    """Duck-typed stand-in for webapp.trend.TrendSignal — probability_engine.py
    never imports webapp/, so tests exercise the duck-typed contract directly."""
    direction: str
    strength: float


def _cpi_event():
    # "CPI m/m" is 'higher_bullish' in EVENT_SURPRISE_DIRECTION.
    return EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=EVENT_TIME, forecast="0.3%", previous="0.3%",
    )


def _unemployment_event():
    # "Unemployment Rate" is 'higher_bearish' — opposite sign convention,
    # used to prove the mapping isn't hardcoded to "higher = bullish".
    return EconomicEvent(
        title="Unemployment Rate", country="USD", impact="High",
        event_time_utc=EVENT_TIME, forecast="4.0%", previous="3.9%",
    )


def test_score_bundle_without_new_params_is_unchanged():
    print("=== score_bundle: omitting print_call and trend_signal reproduces the exact prior behavior ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD", precursor_events=None)
    assert result.direction == Direction.NEUTRAL
    assert result.probability == 0.5
    assert result.contradiction_note == "No articles or leading indicators in window — no basis for a directional call."
    print("PASS\n")


def test_print_call_higher_on_bullish_indicator_is_bullish_for_direct_instrument():
    print("=== score_bundle: a 'higher' print call on a higher_bullish indicator contributes USD-bullish ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    result = score_bundle(bundle, "USDJPY", print_call=print_call)  # USDJPY = direct relationship
    assert result.direction == Direction.BULLISH
    print("PASS\n")


def test_print_call_higher_on_bearish_indicator_flips_sign():
    print("=== score_bundle: a 'higher' print call on a higher_bearish indicator contributes USD-bearish ===")
    event = _unemployment_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    result = score_bundle(bundle, "USDJPY", print_call=print_call)
    assert result.direction == Direction.BEARISH
    print("PASS\n")


def test_print_call_in_line_contributes_nothing():
    print("=== score_bundle: an in_line print call adds ZERO contributions, not a zero-weight one ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="in_line", confidence=0.15, article_count=5)
    result = score_bundle(bundle, "XAUUSD", print_call=print_call)
    assert result.direction == Direction.NEUTRAL
    assert result.probability == 0.5  # identical to the no-print-call case — proves zero contribution, not a diluted one
    print("PASS\n")


def test_print_call_decays_with_age():
    print("=== score_bundle: an old print call contributes less than a fresh one ===")
    event = _cpi_event()
    bundle_fresh = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    bundle_stale = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME + dt.timedelta(hours=48))
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    fresh_result = score_bundle(bundle_fresh, "XAUUSD", print_call=print_call)
    stale_result = score_bundle(bundle_stale, "XAUUSD", print_call=print_call)
    assert abs(fresh_result.instrument_score) > abs(stale_result.instrument_score)
    print("PASS\n")


def test_trend_signal_higher_contributes_in_correct_direction():
    print("=== score_bundle: a 'higher' trend signal on a higher_bullish indicator contributes USD-bullish ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    result = score_bundle(bundle, "USDJPY", trend_signal=trend_signal)
    assert result.direction == Direction.BULLISH
    print("PASS\n")


def test_trend_signal_none_contributes_nothing():
    print("=== score_bundle: trend_signal=None adds zero contributions ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD", trend_signal=None)
    assert result.probability == 0.5
    print("PASS\n")


def test_trend_signal_does_not_decay_with_age():
    print("=== score_bundle: a trend signal contributes identically regardless of bundle age (no time decay) ===")
    event = _cpi_event()
    bundle_fresh = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    bundle_stale = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME + dt.timedelta(hours=48))
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    fresh_result = score_bundle(bundle_fresh, "XAUUSD", trend_signal=trend_signal)
    stale_result = score_bundle(bundle_stale, "XAUUSD", trend_signal=trend_signal)
    assert abs(fresh_result.instrument_score - stale_result.instrument_score) < 1e-9
    print("PASS\n")


def test_print_call_and_trend_signal_both_present_both_contribute():
    print("=== score_bundle: print_call and trend_signal both present blend together, not mutually exclusive ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    both_result = score_bundle(bundle, "XAUUSD", print_call=print_call, trend_signal=trend_signal)
    print_only_result = score_bundle(bundle, "XAUUSD", print_call=print_call)
    # Both agreeing (same direction) should produce a stronger read than print_call alone,
    # since agreement/coverage both improve with a second agreeing signal.
    assert both_result.confidence >= print_only_result.confidence
    print("PASS\n")


def test_print_call_trust_weight_below_precursor_trust_weight():
    print("=== sanity: PRINT_CALL_TRUST_WEIGHT is below PRECURSOR_TRUST_WEIGHT, per the spec's trust tiering ===")
    from config.settings import PRINT_CALL_TRUST_WEIGHT, PRECURSOR_TRUST_WEIGHT, TREND_STREAK_TRUST_WEIGHT
    assert PRINT_CALL_TRUST_WEIGHT < PRECURSOR_TRUST_WEIGHT
    assert TREND_STREAK_TRUST_WEIGHT < PRINT_CALL_TRUST_WEIGHT
    print("PASS\n")


if __name__ == "__main__":
    test_score_bundle_without_new_params_is_unchanged()
    test_print_call_higher_on_bullish_indicator_is_bullish_for_direct_instrument()
    test_print_call_higher_on_bearish_indicator_flips_sign()
    test_print_call_in_line_contributes_nothing()
    test_print_call_decays_with_age()
    test_trend_signal_higher_contributes_in_correct_direction()
    test_trend_signal_none_contributes_nothing()
    test_trend_signal_does_not_decay_with_age()
    test_print_call_and_trend_signal_both_present_both_contribute()
    test_print_call_trust_weight_below_precursor_trust_weight()
    print("All probability_engine tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_probability_engine.py`
Expected: `ImportError: cannot import name 'PrintCall' from 'scoring.print_direction'`
is NOT expected (that module already exists) — instead expect a `TypeError:
score_bundle() got an unexpected keyword argument 'print_call'`.

- [ ] **Step 3: Add the new constants to `config/settings.py`**

Insert immediately after the `PRECURSOR_TRUST_WEIGHT = 0.9` line (currently
line 225):

```python

# Trust weight for THIS occurrence's print-direction call
# (scoring/print_direction.py's score_print_direction()) when blended into
# score_bundle() — below PRECURSOR_TRUST_WEIGHT (a real released number for
# a DIFFERENT event, near-certain) since this is inference about a number
# that hasn't printed yet, even though it's already an aggregate read
# across the whole article bundle.
PRINT_CALL_TRUST_WEIGHT = 0.5

# Trust weight for the event's historical beat/miss streak
# (webapp/trend.py's compute_trend_signal()) when blended into
# score_bundle() — weaker than PRINT_CALL_TRUST_WEIGHT, since a streak is
# a pattern over PAST events, not evidence about this one.
TREND_STREAK_TRUST_WEIGHT = 0.3

# Minimum confirmed (non-pending) historical occurrences required before
# the trend streak contributes to scoring AT ALL — enforced by
# scoring/backtest_accumulator.py before it ever calls
# webapp.trend.compute_trend_signal(). Below this, zero contribution, not
# a low-weight one. Deliberately stricter than webapp/trend.py's own
# MIN_CONFIRMED_ROWS_FOR_A_TREND=2 (which only gates the DISPLAY string) —
# trusting a 2-3 event pattern to nudge a live prediction is a bigger
# claim than merely showing it on a dashboard.
MIN_OCCURRENCES_FOR_TREND_PRIOR = 3
```

- [ ] **Step 4: Add the two dataclasses to `scoring/probability_engine.py`**

Insert immediately after `PrecursorContribution`'s closing (after line 84,
before `ProbabilityResult`):

```python
@dataclass
class PrintCallContribution:
    """
    Audit trail for this occurrence's print-direction call
    (scoring/print_direction.py's PrintCall), mapped onto the USD axis via
    EVENT_SURPRISE_DIRECTION. Duck-typed like PrecursorContribution — same
    usd_sentiment/combined_weight fields — so it flows through the
    existing weighted-average, agreement, and coverage math unchanged.
    """
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float


@dataclass
class TrendStreakContribution:
    """
    Audit trail for the event's historical beat/miss streak
    (webapp/trend.py's TrendSignal), mapped onto the USD axis via
    EVENT_SURPRISE_DIRECTION. Duck-typed like PrecursorContribution.
    """
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float
```

- [ ] **Step 5: Add the two builder functions**

Insert immediately after `_build_precursor_contributions()` (after line 226,
before `_weighted_aggregate`):

```python
def _build_print_call_contribution(
    print_call,  # PrintCall | None — duck-typed, no import from scoring.print_direction needed
    event: EconomicEvent,
    as_of: dt.datetime,
):
    """
    Returns None (no contribution) if print_call is None, its direction is
    'in_line' (no lean either way), or the event's title has no
    EVENT_SURPRISE_DIRECTION entry (defensive — PRINT_SURPRISE_LEXICON is
    a subset of that dict, so this should never actually miss).
    """
    if print_call is None or print_call.direction == "in_line":
        return None
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event.title)
    if surprise_map is None:
        return None

    raw = print_call.confidence if print_call.direction == "higher" else -print_call.confidence
    usd_sentiment = raw if surprise_map == "higher_bullish" else -raw

    age_minutes = max(0.0, (as_of - event.event_time_utc).total_seconds() / 60.0)
    time_w = 0.5 ** (age_minutes / PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES)
    return PrintCallContribution(
        event_title=event.title,
        usd_sentiment=usd_sentiment,
        trust_weight=PRINT_CALL_TRUST_WEIGHT,
        time_weight=time_w,
        combined_weight=PRINT_CALL_TRUST_WEIGHT * time_w,
    )


def _build_trend_streak_contribution(
    trend_signal,  # TrendSignal | None — duck-typed (.direction, .strength), no import from webapp.trend
    event: EconomicEvent,
):
    """
    Returns None if trend_signal is None (either the accumulator's
    MIN_OCCURRENCES_FOR_TREND_PRIOR gate wasn't met, or
    compute_trend_signal() itself found no clean majority) or the event's
    title has no EVENT_SURPRISE_DIRECTION entry. No time decay — a
    historical streak isn't tied to a specific timestamp.
    """
    if trend_signal is None:
        return None
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event.title)
    if surprise_map is None:
        return None

    raw = trend_signal.strength if trend_signal.direction == "higher" else -trend_signal.strength
    usd_sentiment = raw if surprise_map == "higher_bullish" else -raw

    return TrendStreakContribution(
        event_title=event.title,
        usd_sentiment=usd_sentiment,
        trust_weight=TREND_STREAK_TRUST_WEIGHT,
        time_weight=1.0,
        combined_weight=TREND_STREAK_TRUST_WEIGHT,
    )
```

- [ ] **Step 6: Update the import block**

Modify the existing `from config.settings import (...)` block (currently
lines 31-44) to add the three new names, alphabetically placed:

```python
from config.settings import (
    CONTEXTUAL_CONFIDENCE_THRESHOLD,
    CONTRADICTION_MIN_MAGNITUDE,
    ENABLE_FINBERT_SENTIMENT,
    ENABLE_LLM_SENTIMENT,
    EVENT_SURPRISE_DIRECTION,
    INSTRUMENTS,
    MIN_OCCURRENCES_FOR_TREND_PRIOR,
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

(`MIN_OCCURRENCES_FOR_TREND_PRIOR` is imported here even though this
module doesn't use it directly — the test file's
`test_print_call_trust_weight_below_precursor_trust_weight`-style sanity
checks import constants straight from `config.settings`, not from this
module, so this import is NOT actually required for Task 1's own code.
**Remove `MIN_OCCURRENCES_FOR_TREND_PRIOR` from this import block** — it
belongs in Task 3's `scoring/backtest_accumulator.py` import instead, where
it's actually used for the gate check. Only add `EVENT_SURPRISE_DIRECTION`,
`PRINT_CALL_TRUST_WEIGHT`, and `TREND_STREAK_TRUST_WEIGHT` to this file's
import block.)

- [ ] **Step 7: Wire the two new params into `score_bundle()`**

Modify the function signature (currently lines 348-352):

```python
def score_bundle(
    bundle: EventNewsBundle,
    instrument: str,
    precursor_events: list[EconomicEvent] | None = None,
    print_call=None,   # PrintCall | None — duck-typed
    trend_signal=None,  # TrendSignal | None — duck-typed
) -> ProbabilityResult:
```

Update the docstring (append after the existing `precursor_events:`
paragraph, currently ending at line 363):

```python
    print_call: optional — this occurrence's print-direction call
    (scoring/print_direction.py's PrintCall). Blended in as a structured
    contribution the same way a precursor is, but at a lower trust weight
    (config.settings.PRINT_CALL_TRUST_WEIGHT) since it's inference about a
    number that hasn't printed yet. An 'in_line' call contributes nothing.

    trend_signal: optional — the event's historical beat/miss streak
    (webapp/trend.py's TrendSignal, gated by the caller at
    MIN_OCCURRENCES_FOR_TREND_PRIOR before being passed in here). Blended
    in at TREND_STREAK_TRUST_WEIGHT, with no time decay. None contributes
    nothing.
    """
```

Modify the contribution-building block (currently lines 368-371):

```python
    as_of = bundle.as_of_utc
    article_contributions = _build_contributions(bundle.articles, as_of, TIME_DECAY_HALF_LIFE_MINUTES)
    precursor_contributions = _build_precursor_contributions(precursor_events or [], as_of)
    print_call_contribution = _build_print_call_contribution(print_call, bundle.event, as_of)
    trend_streak_contribution = _build_trend_streak_contribution(trend_signal, bundle.event)
    extra_contributions = precursor_contributions + (
        [print_call_contribution] if print_call_contribution is not None else []
    ) + (
        [trend_streak_contribution] if trend_streak_contribution is not None else []
    )
    all_contributions = article_contributions + extra_contributions
```

(`extra_contributions` replaces the bare `precursor_contributions` in the
`all_contributions` line — everything downstream, including the
`if not all_contributions:` early-return branch, is unaffected since it
already just checks the combined list.)

- [ ] **Step 8: Run tests to verify they pass**

Run: `python tests/test_probability_engine.py`
Expected: all 10 tests PASS.

- [ ] **Step 9: Run the existing regression suite for this file**

Run: `python tests/test_backtest_accumulator.py`
Expected: all existing tests still PASS unchanged — `score_bundle()` is
called there without the two new params, proving the default-`None` path
is unaffected.

Also attempt: `python tests/test_scoring_smoke.py` — if it crashes with the
pre-existing `UnicodeEncodeError` (Windows console, unrelated to this
change — confirmed pre-existing in prior sessions), that's expected and not
a regression to chase. If it runs cleanly in your environment, confirm all
tests still PASS.

- [ ] **Step 10: Commit**

```bash
git add config/settings.py scoring/probability_engine.py tests/test_probability_engine.py
git commit -m "feat: blend print-call and trend-streak signals into score_bundle()

PrintCallContribution and TrendStreakContribution join the existing
ArticleContribution/PrecursorContribution list score_bundle() already
weight-averages, duck-typed the same way. Both are purely additive —
score_bundle() called without the two new optional params (print_call,
trend_signal) reproduces today's exact output, verified by a dedicated
regression test.

Trust tiering: PRINT_CALL_TRUST_WEIGHT=0.5 (below a real precursor's
0.9, above raw article trust), TREND_STREAK_TRUST_WEIGHT=0.3 (weaker
still — a pattern over past events, not evidence about this one). An
in_line print call or a None trend signal contribute nothing, not a
zero-weight entry.

10 new tests cover both the blend math and the exact-parity regression
guarantee for the omitted-params case."
```

---

### Task 2: `compute_trend_signal()` in `webapp/trend.py`

**Files:**
- Modify: `webapp/trend.py`
- Test: `tests/test_webapp_trend.py` (existing file — the 7 existing tests must pass unmodified; new tests appended)

**Interfaces:**
- Consumes: `EventHistoryRow` (existing, `webapp/store.py`).
- Produces: `TrendSignal` dataclass (`direction: str, strength: float`) and
  `compute_trend_signal(confirmed_rows: list[EventHistoryRow]) ->
  Optional[TrendSignal]` — takes an ALREADY-FILTERED list of rows with a
  non-`None` `surprise_direction` (the caller does the
  `MIN_OCCURRENCES_FOR_TREND_PRIOR`/`MIN_CONFIRMED_ROWS_FOR_A_TREND` gate
  BEFORE calling this — this function itself applies no minimum-count
  gate, only decides streak-vs-tally-vs-mixed on whatever it's given).
  Task 3 imports both `TrendSignal` and `compute_trend_signal`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webapp_trend.py`, before its `__main__` block (find
with `grep -n "if __name__" tests/test_webapp_trend.py`):

```python
def test_compute_trend_signal_streak_direction_and_strength():
    print("=== compute_trend_signal: a 3-length streak maps to direction='higher', strength=3/5=0.6 ===")
    rows = [_row(8, "higher"), _row(7, "higher"), _row(6, "higher"), _row(5, "lower")]
    signal = compute_trend_signal(rows)
    assert signal is not None
    assert signal.direction == "higher"
    assert abs(signal.strength - 0.6) < 1e-9
    print("PASS\n")


def test_compute_trend_signal_streak_strength_caps_at_one():
    print("=== compute_trend_signal: a streak of 5+ caps strength at 1.0, does not exceed it ===")
    rows = [_row(m, "higher") for m in range(12, 4, -1)]  # 8 consecutive 'higher'
    signal = compute_trend_signal(rows)
    assert signal.direction == "higher"
    assert signal.strength == 1.0
    print("PASS\n")


def test_compute_trend_signal_tally_majority_strength():
    print("=== compute_trend_signal: a 3-of-4 tally (no streak) maps strength=(3/4-0.5)*2=0.5 ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "higher")]
    signal = compute_trend_signal(rows)
    assert signal is not None
    assert signal.direction == "higher"
    assert abs(signal.strength - 0.5) < 1e-9
    print("PASS\n")


def test_compute_trend_signal_unanimous_tally_strength_is_one():
    print("=== compute_trend_signal: a unanimous non-streak-shaped tally saturates strength at 1.0 ===")
    # Deliberately not a pure consecutive streak from index 0 — alternating
    # but all one direction: still 100% one-sided, so tally strength = 1.0.
    rows = [_row(8, "higher"), _row(7, "higher")]
    signal = compute_trend_signal(rows)
    assert signal is not None
    assert signal.strength == 1.0
    print("PASS\n")


def test_compute_trend_signal_mixed_returns_none():
    print("=== compute_trend_signal: an exact tie (mixed, no majority) returns None ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "lower")]
    signal = compute_trend_signal(rows)
    assert signal is None
    print("PASS\n")


def test_compute_trend_signal_all_in_line_returns_none():
    print("=== compute_trend_signal: all in_line rows (no directional lean at all) returns None ===")
    rows = [_row(8, "in_line"), _row(7, "in_line")]
    signal = compute_trend_signal(rows)
    assert signal is None
    print("PASS\n")


def test_summarize_trend_and_compute_trend_signal_agree_on_no_signal_cases():
    print("=== parity: summarize_trend's 'Mixed'/'Not enough history' cases correspond to compute_trend_signal returning None ===")
    mixed_rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "lower")]
    assert summarize_trend(mixed_rows).startswith("Mixed")
    assert compute_trend_signal(mixed_rows) is None

    streak_rows = [_row(8, "higher"), _row(7, "higher")]
    assert summarize_trend(streak_rows).startswith("Trending")
    assert compute_trend_signal(streak_rows) is not None
    print("PASS\n")
```

Add the new imports to the top of `tests/test_webapp_trend.py` (modify the
existing `from webapp.trend import summarize_trend` line):

```python
from webapp.trend import summarize_trend, compute_trend_signal
```

Register all 7 new tests in the file's `__main__` block, after the
existing 7.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_trend.py`
Expected: `ImportError: cannot import name 'compute_trend_signal' from 'webapp.trend'`

- [ ] **Step 3: Refactor `webapp/trend.py`**

Replace the entire file content with:

```python
"""
Plain-Python trend summary over webapp.store's event_history rows — no
I/O, no network, no LLM call. Two consumers share one arithmetic core
(_analyze_trend, below): summarize_trend() formats it as a human-readable
string for the dashboard's History panel; compute_trend_signal() maps it
to a numeric (direction, strength) signal for
scoring/backtest_accumulator.py to blend into score_bundle() (see
docs/superpowers/specs/2026-08-12-trend-history-scoring-feedback-design.md).
Deliberately arithmetic, not inference — same "cheap and deterministic
before reaching for anything smarter" pattern as scoring/sentiment.py's
lexicon tier.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from webapp.store import EventHistoryRow

MIN_CONFIRMED_ROWS_FOR_A_TREND = 2
MIN_STREAK_LENGTH = 2

# compute_trend_signal()'s strength formula denominator for a consecutive
# streak — a streak this long or longer saturates strength at 1.0.
STREAK_LENGTH_FOR_FULL_STRENGTH = 5


@dataclass
class TrendSignal:
    """direction: 'higher' | 'lower'. strength: 0.0-1.0."""
    direction: str
    strength: float


@dataclass
class _TrendAnalysis:
    """Internal shared result of the streak-then-tally arithmetic — never exposed outside this module."""
    kind: str  # "streak" | "tally" | "mixed"
    direction: Optional[str]
    streak_length: Optional[int] = None   # set when kind == "streak"
    majority_count: Optional[int] = None  # set when kind == "tally"
    directional_total: Optional[int] = None  # set when kind == "tally"
    window: int = 0  # len(confirmed_rows) — used by the "mixed" message/gate


def _analyze_trend(confirmed_rows: list[EventHistoryRow]) -> _TrendAnalysis:
    """
    `confirmed_rows` must already be filtered to non-None surprise_direction,
    most-recent-first (get_event_history()'s existing order), and must be
    non-empty (callers apply their own minimum-count gate before calling
    this — see summarize_trend()/compute_trend_signal() below).
    """
    streak_direction = confirmed_rows[0].surprise_direction
    streak_length = 1
    for row in confirmed_rows[1:]:
        if row.surprise_direction == streak_direction:
            streak_length += 1
        else:
            break

    if streak_length >= MIN_STREAK_LENGTH and streak_direction in ("higher", "lower"):
        return _TrendAnalysis(kind="streak", direction=streak_direction, streak_length=streak_length, window=len(confirmed_rows))

    higher_count = sum(1 for r in confirmed_rows if r.surprise_direction == "higher")
    lower_count = sum(1 for r in confirmed_rows if r.surprise_direction == "lower")
    directional_total = higher_count + lower_count

    if directional_total == 0:
        return _TrendAnalysis(kind="mixed", direction=None, window=len(confirmed_rows))

    if higher_count > lower_count:
        return _TrendAnalysis(kind="tally", direction="higher", majority_count=higher_count, directional_total=directional_total, window=len(confirmed_rows))
    if lower_count > higher_count:
        return _TrendAnalysis(kind="tally", direction="lower", majority_count=lower_count, directional_total=directional_total, window=len(confirmed_rows))
    return _TrendAnalysis(kind="mixed", direction=None, window=len(confirmed_rows))


def summarize_trend(rows: list[EventHistoryRow]) -> str:
    """
    `rows` is expected most-recent-first (get_event_history()'s existing
    order). Only rows with a non-None surprise_direction count as
    "confirmed" — a still-pending occurrence (event hasn't printed yet)
    doesn't count toward the trend.
    """
    confirmed = [r for r in rows if r.surprise_direction is not None]
    if len(confirmed) < MIN_CONFIRMED_ROWS_FOR_A_TREND:
        return "Not enough history yet"

    analysis = _analyze_trend(confirmed)
    if analysis.kind == "streak":
        return f"Trending {analysis.direction} for {analysis.streak_length} consecutive releases"
    if analysis.kind == "tally":
        verb = "Beat" if analysis.direction == "higher" else "Missed"
        return f"{verb} forecast {analysis.majority_count} of last {analysis.directional_total}"
    return f"Mixed — no clean streak over the last {analysis.window} prints"


def compute_trend_signal(confirmed_rows: list[EventHistoryRow]) -> Optional[TrendSignal]:
    """
    Maps the same streak-then-tally arithmetic summarize_trend() uses to a
    numeric (direction, strength) signal for scoring feed-back. Unlike
    summarize_trend(), this function applies NO minimum-row-count gate
    itself — the caller (scoring/backtest_accumulator.py) enforces the
    stricter MIN_OCCURRENCES_FOR_TREND_PRIOR (config.settings) before ever
    calling this, since trusting a pattern enough to nudge a live
    prediction is a bigger claim than merely displaying it. Returns None
    for a "mixed"/no-majority result — never a zero-strength signal.

    `confirmed_rows` must already be filtered to non-None surprise_direction
    and non-empty — passing an empty list is a caller bug (would raise on
    the [0] index in _analyze_trend), not a case this function handles.
    """
    analysis = _analyze_trend(confirmed_rows)
    if analysis.kind == "streak":
        strength = min(1.0, analysis.streak_length / STREAK_LENGTH_FOR_FULL_STRENGTH)
        return TrendSignal(direction=analysis.direction, strength=strength)
    if analysis.kind == "tally":
        strength = (analysis.majority_count / analysis.directional_total - 0.5) * 2
        return TrendSignal(direction=analysis.direction, strength=strength)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_trend.py`
Expected: all 14 tests PASS (7 pre-existing + 7 new), including all 7
pre-existing `summarize_trend()` tests passing UNCHANGED — this is the
proof the refactor preserved exact prior behavior.

- [ ] **Step 5: Run the full regression sweep for files that import `webapp.trend`**

```bash
python tests/test_webapp_app.py
```

Expected: all PASS — `webapp/app.py`'s `/api/event_history` route calls
`summarize_trend()`, must be unaffected.

- [ ] **Step 6: Commit**

```bash
git add webapp/trend.py tests/test_webapp_trend.py
git commit -m "feat: add compute_trend_signal(), share streak arithmetic with summarize_trend()

Extracts the streak-then-tally arithmetic both functions need into a
private _analyze_trend() helper, so the human-readable summary and the
new numeric scoring signal can never silently drift apart. All 7
pre-existing summarize_trend() tests pass unmodified — this refactor
changes zero observable behavior for the existing display path.

compute_trend_signal() applies no minimum-count gate itself (that's
the caller's job, since scoring wants a stricter threshold than
display does — see MIN_OCCURRENCES_FOR_TREND_PRIOR in Task 1);
returns a TrendSignal(direction, strength) or None for a mixed/
no-majority result."
```

---

### Task 3: Wire cross-pipeline read + accumulator call site

**Files:**
- Modify: `scoring/backtest_accumulator.py`
- Test: `tests/test_backtest_accumulator.py`

**Interfaces:**
- Consumes: `score_bundle()`'s `print_call`/`trend_signal` params (Task 1,
  `scoring.probability_engine`); `TrendSignal`, `compute_trend_signal()`
  (Task 2, `webapp.trend`); `get_connection`, `get_event_history` (existing,
  `webapp.store`); `MIN_OCCURRENCES_FOR_TREND_PRIOR` (Task 1,
  `config.settings`).
- Produces: no new public interface — this is the final wiring task.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_backtest_accumulator.py`, before its `__main__`
block (find the insertion point near the other `run_accumulator_cycle`
tests, e.g. after `test_print_direction_none_call_writes_nothing`):

```python
def test_trend_signal_passed_to_score_bundle_when_gate_met():
    print("=== accumulator: a trend_signal is computed and passed to score_bundle() when >=3 confirmed occurrences exist ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"  # must be in EVENT_SURPRISE_DIRECTION for the gate to matter downstream
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        # Seed 3 confirmed occurrences in the dashboard's event_history table.
        dash_conn = webapp_store.get_connection(dashboard_db_path)
        for month in (5, 6, 7):
            hist_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.3%", previous="0.3%", actual="0.5%",
            )
            webapp_store.upsert_event_history(dash_conn, hist_event, "higher", now=hist_event.event_time_utc)
        dash_conn.close()

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None):
            captured_kwargs["trend_signal"] = trend_signal
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["trend_signal"] is not None
        assert captured_kwargs["trend_signal"].direction == "higher"
    print("PASS\n")


def test_trend_signal_is_none_when_gate_not_met():
    print("=== accumulator: trend_signal is None when fewer than MIN_OCCURRENCES_FOR_TREND_PRIOR confirmed occurrences exist ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        # Seed only 2 confirmed occurrences — below MIN_OCCURRENCES_FOR_TREND_PRIOR=3.
        dash_conn = webapp_store.get_connection(dashboard_db_path)
        for month in (6, 7):
            hist_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.3%", previous="0.3%", actual="0.5%",
            )
            webapp_store.upsert_event_history(dash_conn, hist_event, "higher", now=hist_event.event_time_utc)
        dash_conn.close()

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None):
            captured_kwargs["trend_signal"] = trend_signal
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["trend_signal"] is None
    print("PASS\n")


def test_trend_signal_is_none_when_dashboard_db_unreachable():
    print("=== accumulator: a failed dashboard-DB read fails OPEN to trend_signal=None, does not crash the cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None):
            captured_kwargs["trend_signal"] = trend_signal
            return _fake_result()

        # Nonexistent path in a directory that doesn't exist — get_connection's
        # executescript() will raise (sqlite3.OperationalError: unable to open database file).
        unreachable_dashboard_db = Path(tmp) / "nonexistent_subdir" / "dashboard.db"

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", unreachable_dashboard_db):

            events_result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert events_result is not None  # cycle completed, did not crash/return None
        assert captured_kwargs["trend_signal"] is None
    print("PASS\n")


def test_print_call_passed_to_score_bundle():
    print("=== accumulator: the already-computed print_call is passed through to score_bundle() ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_call = accumulator_print_direction.PrintCall(direction="higher", confidence=0.6, article_count=2)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None):
            captured_kwargs["print_call"] = print_call
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=fake_call), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["print_call"] is fake_call
    print("PASS\n")
```

Add the required imports at the top of `tests/test_backtest_accumulator.py`
(check current imports first with `head -25
tests/test_backtest_accumulator.py` — add whichever of these aren't
already present):

```python
import webapp.store as webapp_store
```

(`EconomicEvent`, `EventNewsBundle`, `UTC_TZ`, and
`accumulator_print_direction` are already imported in this file from
earlier tasks — verify before adding duplicates.)

Register all 4 new tests in the file's `__main__` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_backtest_accumulator.py`
Expected: `AttributeError: <module 'scoring.backtest_accumulator'> does not
have the attribute 'DASHBOARD_DB_PATH'`

- [ ] **Step 3: Wire the cross-pipeline read into `scoring/backtest_accumulator.py`**

Modify the import block (currently lines 56-64) to add the new imports:

```python
from config.settings import MIN_OCCURRENCES_FOR_TREND_PRIOR, PRE_EVENT_WINDOW_HOURS
from data_layer.calendar_feed import fetch_calendar, filter_relevant_events, events_in_pre_window, find_precursor_events
from data_layer.event_context import build_event_news_bundle
from data_layer.rss_sources import build_all_preview_sources
from scoring.probability_engine import score_bundle
from scoring.print_direction import score_print_direction
from scoring.backtest_store import (
    get_connection, record_prediction, get_latest_prediction, record_check, count_recent_checks,
    record_print_prediction_if_changed,
)
from webapp.store import get_connection as get_dashboard_connection, get_event_history, DB_PATH as DASHBOARD_DB_PATH
from webapp.trend import compute_trend_signal
```

Add a new module-level function right after `_is_material_change()`
(before `compute_accumulator_interval_seconds`):

```python
def _read_trend_signal(event_title: str):
    """
    Reads webapp/store.py's event_history for this event title via a
    short-lived READ-ONLY connection to the dashboard's own DB — the
    accumulator writes nothing there, mirroring the existing reverse
    precedent (webapp/app.py already reads scoring/backtest_store.py's DB
    read-only for display). Returns None (fail open, never crashes the
    cycle) if the dashboard DB is unreachable, or if fewer than
    MIN_OCCURRENCES_FOR_TREND_PRIOR confirmed occurrences exist yet —
    trusting a thin pattern enough to nudge a live prediction is a bigger
    claim than merely displaying it (see webapp/trend.py's own, looser
    MIN_CONFIRMED_ROWS_FOR_A_TREND=2 display-only gate for contrast).
    """
    try:
        conn = get_dashboard_connection(DASHBOARD_DB_PATH)
    except Exception as exc:  # noqa: BLE001 — a missing/locked dashboard DB must not crash the accumulator cycle
        print(f"[backtest_accumulator] WARNING: could not read dashboard event_history for {event_title}: {exc}")
        return None

    try:
        rows = get_event_history(conn, event_title)
    finally:
        conn.close()

    confirmed = [r for r in rows if r.surprise_direction is not None]
    if len(confirmed) < MIN_OCCURRENCES_FOR_TREND_PRIOR:
        return None
    return compute_trend_signal(confirmed)
```

- [ ] **Step 4: Call it and pass both new signals into `score_bundle()`**

In `run_accumulator_cycle()`, modify the block that currently reads:

```python
            print_call = score_print_direction(bundle)
            if print_call is not None:
                written = record_print_prediction_if_changed(conn, event.title, event.event_time_utc, print_call, now=now)
                if written:
                    print(f"[backtest_accumulator] print call for {event.title}: {print_call.direction} ({print_call.confidence:.0%} confidence, {print_call.article_count} articles)")
```

to add the trend-signal read right after it (still once per event, before
the `for instrument in instruments:` loop):

```python
            print_call = score_print_direction(bundle)
            if print_call is not None:
                written = record_print_prediction_if_changed(conn, event.title, event.event_time_utc, print_call, now=now)
                if written:
                    print(f"[backtest_accumulator] print call for {event.title}: {print_call.direction} ({print_call.confidence:.0%} confidence, {print_call.article_count} articles)")

            trend_signal = _read_trend_signal(event.title)
            if trend_signal is not None:
                print(f"[backtest_accumulator] trend signal for {event.title}: {trend_signal.direction} (strength {trend_signal.strength:.2f})")
```

Then modify the `score_bundle()` call inside the `for instrument in
instruments:` loop (currently `result = score_bundle(bundle, instrument,
precursor_events=precursors)`):

```python
                try:
                    result = score_bundle(
                        bundle, instrument, precursor_events=precursors,
                        print_call=print_call, trend_signal=trend_signal,
                    )
                except Exception as exc:  # noqa: BLE001 — one pair's failure must not stop the others
                    print(f"[backtest_accumulator] WARNING: scoring failed for {instrument}/{event.title}: {exc}")
                    continue
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python tests/test_backtest_accumulator.py`
Expected: all tests PASS, including the 4 new ones.

- [ ] **Step 6: Run the full regression sweep**

```bash
python tests/test_probability_engine.py
python tests/test_webapp_trend.py
python tests/test_backtest_store.py
python tests/test_webapp_app.py
python tests/test_webapp_store.py
python tests/test_webapp_scheduler.py
python tests/test_print_direction.py
python tests/test_calendar_feed.py
```

Expected: all PASS, no regressions.

- [ ] **Step 7: Commit**

```bash
git add scoring/backtest_accumulator.py tests/test_backtest_accumulator.py
git commit -m "feat: wire trend-signal + print-call blending into the accumulator's cycle

_read_trend_signal() opens a short-lived READ-ONLY connection to
webapp/store.py's dashboard DB (mirroring the existing reverse
precedent — webapp/app.py already reads the accumulator's DB
read-only for display), applies the MIN_OCCURRENCES_FOR_TREND_PRIOR
gate, and calls webapp.trend.compute_trend_signal(). Both the trend
signal and the already-computed print_call now flow into
score_bundle() for every instrument scored this cycle.

Fails open (trend_signal=None) on any dashboard-DB read error —
verified by a dedicated test using an unreachable DB path — never
crashes the accumulator cycle over a cross-pipeline read failure."
```

---

### Task 4: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a new subsection**

Find the "### Economic-print prediction + trend history" subsection (added
by the prior feature's plan) via `grep -n "Economic-print prediction"
README.md`, and insert this new subsection immediately after it, before
the next `##`/`###` heading:

```markdown
### Trend-history feed-back into scoring

The two signals above now also feed back into the article-based
accumulator's actual instrument scoring
(`scoring/probability_engine.score_bundle()`), not just the dashboard
display — gated so neither contributes anything on thin data:

- **This occurrence's print call** blends in at
  `PRINT_CALL_TRUST_WEIGHT=0.5` (below a real precursor's `0.9`, above raw
  article trust) whenever it's `higher`/`lower` (never `in_line`), decaying
  like a precursor across the pre-event window.
- **The event's historical beat/miss streak** blends in at
  `TREND_STREAK_TRUST_WEIGHT=0.3`, with no time decay, but only once
  `MIN_OCCURRENCES_FOR_TREND_PRIOR=3` confirmed past occurrences exist —
  below that, exactly like a `None` print call, it contributes nothing at
  all, not a diluted nudge.

Both are additive to `score_bundle()`'s existing weighted-average math —
called without them, `score_bundle()` produces byte-for-byte the same
result as before this feature, verified by a dedicated regression test.
`scoring/backtest_accumulator.py` computes the trend signal via a
short-lived **read-only** connection to the dashboard's own
`event_history` table (`webapp/store.py`) — the one deliberate crossing of
this project's usual dashboard/accumulator pipeline separation, mirroring
the existing reverse precedent where `webapp/app.py` already reads the
accumulator's DB read-only for display.

See
`docs/superpowers/specs/2026-08-12-trend-history-scoring-feedback-design.md`
for the full design, including why the trust weights and the
3-occurrence gate are launch defaults rather than tuned values — this
session's first live CPI release produced one correct print call and one
wrong one out of two, exactly the kind of thin sample this design
protects live scoring from over-trusting.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document trend-history feed-back into scoring"
```

---

## Post-plan verification (do this after all 4 tasks are complete)

- [ ] Run the full regression suite across every `tests/test_*.py` file:

```bash
for f in tests/test_*.py; do echo "--- $f ---"; python "$f" 2>&1 | tail -6; done
```

Expected: every file ends with its "All ... tests passed." line (or PASS).
`test_contextual_sentiment.py`'s SKIP lines (no `ANTHROPIC_API_KEY`) and
`test_scoring_smoke.py`'s pre-existing Windows-console Unicode crash are
both expected, pre-existing, and unrelated to this feature.

- [ ] Restart `run_all.py` (kill the existing process tree first) and
      confirm live: the accumulator's console output shows a `trend signal
      for ...` line once any tracked event's history clears the
      3-occurrence gate (won't happen immediately on a fresh restart —
      this session's own live CPI history only has 1 confirmed occurrence
      so far, so the gate genuinely won't fire yet; confirm instead that
      the cycle completes without error and `print call for ...` lines
      still appear as before).
