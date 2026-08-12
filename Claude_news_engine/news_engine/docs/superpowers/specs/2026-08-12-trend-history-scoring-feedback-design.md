# Trend-History Feed-Back Into Scoring — Design

## Problem

The economic-print-prediction + trend-history feature
(`docs/superpowers/specs/2026-08-11-economic-print-prediction-trend-history-design.md`)
shipped two new signals — a per-occurrence print-direction call
(`scoring/backtest_store.py`'s `print_predictions`) and durable
forecast/previous/actual history across occurrences
(`webapp/store.py`'s `event_history`, summarized by `webapp/trend.py`'s
`summarize_trend()`) — but deliberately kept both **display-only**. Neither
feeds back into `scoring/probability_engine.score_bundle()`'s actual
instrument-direction math. That spec's own "Explicitly out of scope"
section named this as the natural next step, conditional on having enough
real data to know whether either signal is actually predictive:

> Feeding the print-direction call or the trend streak back into
> `score_bundle()`'s instrument scoring... A future spec can revisit once
> there's enough real `print_predictions` data to know whether it's
> actually predictive.

This is that spec. Live data collected during this session's first real
CPI release (2026-08-12, `Core CPI m/m`/`CPI m/m`) is genuinely thin (one
correct call, one wrong, out of two) — not enough to validate predictive
value, which is exactly why this design gates both new signals behind a
minimum-data threshold rather than trusting them from day one.

## Scope boundary

Two new optional contributions blend into `score_bundle()`'s existing
weighted-average math. No change to `_weighted_aggregate()`,
`_agreement_and_coverage()`, `_map_to_instrument_score()`, or any existing
contribution type (`ArticleContribution`, `PrecursorContribution`). No UI
change — the print-call badge and History panel already display the raw
inputs this feature consumes. No change to the essence-only dashboard's
`webapp/scoring_service.py`, which doesn't call `score_bundle()` at all and
stays fully decoupled from this, consistent with every prior spec this
session.

## Architecture

Two new dataclasses in `scoring/probability_engine.py`, next to
`PrecursorContribution`, duck-typed the same way (`usd_sentiment`,
`trust_weight`, `time_weight`, `combined_weight`) so they flow through the
existing blend math without any change to it:

```python
@dataclass
class PrintCallContribution:
    """This occurrence's print_predictions call, mapped onto the USD axis."""
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float


@dataclass
class TrendStreakContribution:
    """The event's historical beat/miss streak, mapped onto the USD axis."""
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float
```

`score_bundle()` gains two new optional parameters:

```python
def score_bundle(
    bundle: EventNewsBundle,
    instrument: str,
    precursor_events: list[EconomicEvent] | None = None,
    print_call: "PrintCall | None" = None,
    trend_signal: "TrendSignal | None" = None,
) -> ProbabilityResult:
```

Omitting both reproduces today's exact output byte-for-byte — this is how
`precursor_events` already behaves, and the only caller that will ever pass
the two new params is `scoring/backtest_accumulator.py`. The essence-only
dashboard never calls `score_bundle()` at all, so it's unaffected either
way.

`trend_signal` takes the already-derived `TrendSignal` (direction +
strength), not the raw `event_history` rows — the accumulator computes it
via `webapp.trend.compute_trend_signal()` before calling `score_bundle()`
(see "Cross-pipeline data flow" and "Blend math" below for why the
derivation lives in `webapp/trend.py` rather than being duplicated here).

## Cross-pipeline data flow

`event_history` lives in `webapp/store.py`'s dashboard DB (a deliberate
choice in the prior spec, since only the dashboard needed it for display).
`score_bundle()` lives in `scoring/probability_engine.py`, used only by the
accumulator — a pipeline this project has kept strictly decoupled from the
dashboard's process/DB throughout this session. Feeding the streak into
scoring means crossing that boundary, so this spec makes that crossing
explicit rather than accidental.

Precedent already exists in the opposite direction: `webapp/app.py` opens a
read-only connection to `scoring/backtest_log.db` today, purely to display
`article_prediction`/`print_prediction` — it computes nothing from that
data, just reads it. This spec mirrors that pattern in reverse:

```python
from webapp.store import get_connection as get_dashboard_connection, get_event_history
```

Once per event per cycle (not per instrument — same "compute once, reuse
across instruments" pattern the existing precursor lookup and article-bundle
fetch already follow), `run_accumulator_cycle()` opens a short-lived
read-only connection to the dashboard's DB, calls
`get_event_history(conn, event.title, limit=6)`, and closes it immediately.
No write, no schema change, no new table on either side.

A connection failure (e.g. the dashboard's DB file doesn't exist yet on a
fresh install, or is locked) must not crash the accumulator cycle — caught
and treated as "no trend history available," the same fail-open pattern
already used for calendar-fetch failures elsewhere in
`scoring/backtest_accumulator.py`.

## Blend math

### Print call → contribution

Gate: `PrintCallContribution` is only built when `print_call is not None`
and `print_call.direction != "in_line"` — an `in_line` call produces **no
contribution at all**, not a zero-weight one (a zero-weight entry with the
wrong sign could still leak into `_agreement_and_coverage()`'s denominator
via `coverage`, so "absent" and "present at weight 0" are not
interchangeable here).

```python
def _build_print_call_contribution(
    print_call: "PrintCall | None",
    event: EconomicEvent,
    as_of: dt.datetime,
) -> "PrintCallContribution | None":
    if print_call is None or print_call.direction == "in_line":
        return None
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event.title)
    if surprise_map is None:
        return None  # defensive — PRINT_SURPRISE_LEXICON is a subset of this, should never miss

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
```

`PRINT_CALL_TRUST_WEIGHT = 0.5` (new constant, `config/settings.py`) —
below `PRECURSOR_TRUST_WEIGHT = 0.9` (a real released number for a
different event; near-certain), above per-article trust (this is inference
about a number that hasn't printed yet, but already an aggregate read
across the whole article bundle). Decays like a precursor — reuses
`PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES` — since it's tied to a specific,
dated occurrence the same way a precursor event is.

### Trend streak → contribution

Gate: built only when `trend_history` has at least
`MIN_OCCURRENCES_FOR_TREND_PRIOR = 3` rows with a non-`None`
`surprise_direction` (i.e. `summarize_trend()` would not return "Not enough
history yet" for the same data). Below that threshold, `score_bundle()`
behaves exactly as it does today — no low-weight nudge, no contribution.

The streak-walk logic (consecutive-direction count, beat/miss tally) is
factored out of `webapp/trend.py`'s `summarize_trend()` into a small shared
helper, `compute_trend_signal(rows) -> Optional[TrendSignal]`, living in
`webapp/trend.py` (`TrendSignal` = `(direction: str, strength: float)`,
where `direction` is `"higher"`/`"lower"` and `strength` is 0.0–1.0).
`summarize_trend()` calls this same helper to build its human-readable
string, so the arithmetic exists in exactly one place. `scoring/probability_engine.py`
imports `compute_trend_signal` and `TrendSignal` from `webapp.trend` (the
same cross-pipeline read the accumulator already performs to fetch the raw
rows — no new import boundary, just the derived signal instead of raw rows
if the caller prefers; the accumulator will call `compute_trend_signal()`
itself and pass the resulting `TrendSignal`, not the raw rows, into
`score_bundle()` — see the Architecture section's `trend_history` param,
which is renamed `trend_signal: Optional[TrendSignal]` to reflect this).

`strength` mapping:
- A consecutive streak (`compute_trend_signal`'s streak branch, same logic
  `summarize_trend()`'s streak block already uses): `strength = min(1.0,
  streak_length / 5)` — a 2-length streak barely registers (0.4), a 5+
  streak saturates at 1.0.
- A beat/miss tally with no streak: `strength = (majority_count /
  directional_total - 0.5) * 2` — a bare 50/50-adjacent majority maps
  to ~0, a unanimous run maps to 1.0.
- `"Mixed"` (no majority) or below the 3-occurrence gate: `compute_trend_signal`
  returns `None` — no contribution, not a zero-strength one.

```python
def _build_trend_streak_contribution(
    trend_signal: "TrendSignal | None",
    event: EconomicEvent,
) -> "TrendStreakContribution | None":
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

`TREND_STREAK_TRUST_WEIGHT = 0.3` (new constant) — weaker than the print
call's 0.5, since a streak is a pattern over past events, not evidence
about this one. No time decay (`time_weight = 1.0` always) — it isn't tied
to a timestamp the way a print call or precursor event is.

### Accumulator wiring

`scoring/backtest_accumulator.py`'s `run_accumulator_cycle()`, once per
event (reusing the `print_call` it already computes this cycle for the
existing `print_predictions` write, and the new read-only
`get_event_history()` call above):

```python
history_rows = _read_event_history_readonly(event.title)  # None on any failure, fail-open
trend_signal = compute_trend_signal(history_rows) if history_rows else None

for instrument in instruments:
    result = score_bundle(
        bundle, instrument, precursor_events=precursors,
        print_call=print_call, trend_signal=trend_signal,
    )
    ...
```

## Testing & edge cases

- `score_bundle()` called with neither `print_call` nor `trend_signal`
  reproduces today's exact output — every existing test in
  `tests/test_backtest_accumulator.py`/`tests/test_probability_engine.py`
  (or wherever `score_bundle()`'s own unit tests live — verify the exact
  file at implementation time) must pass unchanged with zero modification,
  proving the omission path is truly a no-op.
- `print_call.direction == "in_line"` → `_build_print_call_contribution`
  returns `None`, contribution list length unchanged from the
  no-print-call case.
- `trend_signal is None` (below the 3-occurrence gate, or a genuine
  "Mixed" streak) → `_build_trend_streak_contribution` returns `None`,
  same zero-contribution guarantee.
- `EVENT_SURPRISE_DIRECTION.get(event.title)` returning `None` for either
  builder (defensive, shouldn't happen given `PRINT_SURPRISE_LEXICON`'s
  subset relationship) → `None`, no contribution, no crash.
- Cross-pipeline read failure (dashboard DB missing/locked) → caught,
  `trend_signal = None`, accumulator cycle continues normally — a test
  simulating a missing/corrupt dashboard DB file must confirm the cycle
  still completes and still writes the article-based prediction.
- Boundary-value tests for both magnitude formulas: streak length 2 vs. 5
  (0.4 vs. 1.0 strength), tally at exactly a 3-of-5 majority vs. a
  unanimous 5-of-5 (0.2 vs. 1.0 strength), and the exact 3-occurrence gate
  (2 confirmed occurrences → no contribution, 3 → contributes).
- `compute_trend_signal()` and `summarize_trend()` must agree on when a
  signal exists — a test asserting `compute_trend_signal(rows) is None`
  if and only if `summarize_trend(rows) in ("Not enough history yet", ...)`
  matches a "no clean streak"/"Mixed" message, keeping the derived
  structured signal and the human-readable string from silently drifting
  apart as the arithmetic evolves.

## Explicitly out of scope (this pass)

- Auto-tuning `PRINT_CALL_TRUST_WEIGHT`, `TREND_STREAK_TRUST_WEIGHT`, or
  `MIN_OCCURRENCES_FOR_TREND_PRIOR` against real backtest accuracy — these
  are launch defaults. The live CPI release this session produced one
  correct print call and one wrong one out of two — exactly the kind of
  thin sample this design protects live scoring from over-trusting.
  Revisit once `print_predictions`/`outcomes` has enough confirmed cases to
  calibrate against.
- Feeding either signal into the essence-only dashboard
  (`webapp/scoring_service.py`) — untouched, per this session's
  established pipeline-decoupling convention.
- Any dashboard UI change — the existing print-call badge and History
  panel already surface the raw inputs this feature consumes; no new
  display is needed to show "the score now includes a trend nudge."
