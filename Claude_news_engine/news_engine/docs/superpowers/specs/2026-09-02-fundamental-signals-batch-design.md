# Fundamental Signals Batch — COT Crowding, Equity Risk-Sentiment, Oil Shock Flag — Design

**Date:** 2026-09-02
**Status:** Approved via conversational brainstorm (architectural path — three new confidence-modifying signals into the scoring core)
**Supersedes/extends:** `docs/fundamental-analysis-alignment-review-2026-09-02.md` (items N1, N3, N4 of that review's consolidated priority list — N2 and N5 are explicitly out of scope, see below)

## Problem

`docs/fundamental-analysis-alignment-review-2026-09-02.md` identified three gaps against standard FX fundamental-analysis practice, all currently unaddressed anywhere in this codebase (confirmed via grep — zero references to COT, positioning, SP500, or a shock/exogenous flag):

1. **No positioning data.** Nothing in the system answers "is this move already crowded" — a materially different question than "what does the market expect" (Kalshi) or "where is the dollar/rates already positioned" (the existing macro-backdrop check).
2. **No cross-asset risk-sentiment confirmation for US30.** The `risk_sentiment` instrument mapping (`RISK_SENTIMENT_DAMPENING`) is a static dampened proxy off the raw USD axis alone — there is no actual equity-market read confirming or contradicting it.
3. **No exogenous-shock visibility.** A sudden, non-calendar-driven oil spike (or any comparably sharp macro move) currently reads identically to routine drift — the system has no way to flag "something outside the tracked calendar may be happening" the way the 2026-08-14 SWOT's backtest case (Iran strikes ahead of a CPI print) needed.

## Decisions (from brainstorm)

- **COT is a confidence dampener only, never a directional lean.** Explicitly revisit as a possible directional input later, only if experience shows the dampener-only design is leaving real signal on the table. Not now.
- **Equity risk-sentiment is instrument-scoped**, not folded into the existing instrument-agnostic macro-backdrop check. It only applies to instruments whose `usd_relationship` is `"risk_sentiment"` (today: US30 only) and is compared against that instrument's *mapped* score, not the raw USD axis — an equity index has no USD sign of its own.
- **Oil shock trigger:** a single most-recent-day move against a tight threshold, distinct from the existing 10-day `oil_trend_pct`/`OIL_LEAN_THRESHOLD_PCT` — not a "fraction of the existing trend" measure, which would conflate "sharp" with "the trend window happened to be short."
- **Oil shock surfacing:** both a confidence dampener *and* a visible note on the result, mirroring `macro_backdrop_agrees`/`macro_backdrop_note`'s existing pattern — visible on the dashboard, not a silent number change.
- **Rate differentials / cross-central-bank divergence (N5) and the FOMC forward-guidance delta (N2) are explicitly out of scope for this spec.** N5 has no leg to stand on until a real currency pair is tracked (flagged for that future effort); N2 is materially higher-effort (needs a stored prior-statement baseline and a diff mechanism, not a new data pull) and is its own future spec.
- **A separate, unrelated feature — a categorized (Forex Major/Minor/etc., XM-sourced) add-symbol picker — was raised in the same conversation and deliberately deferred to its own brainstorm/spec after this one**, per explicit sequencing instruction. Not covered here.

## Architecture

Three new independent read-only signals, each following the exact shape already proven twice in this codebase (`data_layer/macro_backdrop.py`'s DXY/real-yield/oil reads, `scoring/probability_engine.py`'s `_check_macro_backdrop()`):

- A `data_layer` module (or extension of `macro_backdrop.py`) returns a fail-open dataclass — `None` on any failure, real values only when real data exists, never fabricated.
- A `_check_*()` function in `scoring/probability_engine.py` compares the read against the relevant directional axis and returns `(agrees_or_triggered, note)` — never touches `direction` or `probability`, only ever multiplies `confidence`.
- `score_bundle()` gains new optional parameters (default `None`), so omitting them reproduces today's exact behavior — matching `macro_backdrop=None`'s existing contract.
- Every new threshold constant is added to `config/settings.py` with the same "explicitly unvalidated, needs revisiting once real backtest data exists" honesty already used for every existing threshold in this codebase (`OIL_LEAN_THRESHOLD_PCT`, `DOLLAR_INDEX_LEAN_THRESHOLD_PCT`, etc.) — nothing here is presented as calibrated.

### 1. COT crowding dampener

**New module:** `data_layer/cot_positioning.py`

**Data source:** CFTC's "Traders in Financial Futures" (TFF) report, via the free, no-token-required Socrata Open Data API at `publicreporting.cftc.gov` (live-verified during brainstorm: the API is genuinely free and covers currency futures including the US Dollar Index; the exact dataset ID/resource path needs a live confirmation call during implementation, same "verify against the real endpoint before trusting it" discipline already used for FRED/Kalshi in this codebase — do not hardcode an assumed dataset ID without checking it responds).

**Series:** ICE U.S. Dollar Index futures, "Leveraged Funds" net position (the TFF report's own most speculative/directional trader category — the standard "smart-money crowding" read in COT-based fundamental analysis, as opposed to "Dealers"/"Asset Managers"/"Other Reportables," which are hedging-driven and not the relevant crowding signal).

**Fetch cadence:** Published weekly (Fridays, covering the prior Tuesday's positions) — fetched at most once per day, cached, never re-fetched every scoring cycle. Mirrors this codebase's existing check-budget discipline (e.g. Alpha Vantage's daily budget backoff in `scoring/backtest_accumulator.py`).

```python
@dataclass
class CotPositioningRead:
    net_leveraged_funds_position: Optional[int]    # contracts, net long(+)/short(-)
    percentile_in_trailing_window: Optional[float]  # 0-100, this reading's rank within the trailing lookback
    report_date: Optional[dt.date]
    lookback_weeks: int

    @property
    def is_crowded(self) -> Optional[int]:
        """
        +1 = net-long crowding (extreme long positioning), -1 = net-short
        crowding, None = not extreme (within the normal range) or no data.
        Extreme = top/bottom COT_CROWDING_PERCENTILE_THRESHOLD of the
        trailing COT_CROWDING_LOOKBACK_WEEKS window — an explicitly
        untuned starting value, same honesty as every other threshold in
        this codebase.
        """
```

**New config constants** (`config/settings.py`):
- `COT_CROWDING_LOOKBACK_WEEKS = 52` — one year of weekly reports, a standard COT lookback window.
- `COT_CROWDING_PERCENTILE_THRESHOLD = 15.0` — top/bottom 15% of the trailing window counts as "crowded." Untuned.
- `COT_CROWDING_CONFIDENCE_MULTIPLIER = 0.85` — same style/magnitude class as `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER`, untuned.

**New function** (`scoring/probability_engine.py`):
```python
def _check_cot_crowding(
    aggregate_usd: float,
    cot_read,  # CotPositioningRead | None — duck-typed
) -> tuple[bool | None, str | None]:
    """
    (None, None) if no data or positioning isn't extreme. (True, note)
    if positioning IS extreme AND its sign matches aggregate_usd's sign
    (a crowded trade in the same direction as this read — dampen
    confidence, this is the opposite polarity from
    _check_macro_backdrop: crowding on AGREEMENT is the caution signal
    here, not disagreement). Never (False, ...) — this check has no
    "disagreement" case, only "crowded and aligned" vs. "not a concern."
    """
```
`score_bundle()` wiring: `cot_crowded, cot_crowding_note = _check_cot_crowding(aggregate_usd, cot_positioning)`; `if cot_crowded: confidence *= COT_CROWDING_CONFIDENCE_MULTIPLIER`. New `ProbabilityResult` fields: `cot_crowding_flag: bool | None = None`, `cot_crowding_note: str | None = None`.

### 2. Equity risk-sentiment leg (US30-scoped)

**Extends:** `data_layer/macro_backdrop.py` — a fourth FRED series, `SP500` (free, same API key already in use, no new credential).

```python
EQUITY_INDEX_SERIES_ID = "SP500"
EQUITY_INDEX_LEAN_THRESHOLD_PCT = 1.0  # untuned — a broad index, tighter than oil's 5% (oil's threshold is wide specifically because oil is far more volatile; equities are not)
```

Added to `MacroBackdropRead` as `equity_index_trend_pct: Optional[float]` / `equity_index_latest_date: Optional[dt.date]`, fetched via the existing `_fetch_trend()` (added to `PERCENT_CHANGE_SERIES_IDS`, no new fetch logic needed — `SP500` is a level series like the dollar index and oil).

**Not folded into `.lean`** — `.lean` stays a pure USD read (dollar index → real yield → oil fallback chain, unchanged). Equity trend is a separate property, read independently, since it answers a different question (risk-on/off) than `.lean` (dollar strength).

**One existing function needs a small update:** `get_macro_backdrop_read()`'s current "return `None` only if ALL series are entirely unavailable" check tests three series (dollar, real yield, oil) — it must be extended to also check `equity_trend is None` (all four/five null, counting the new daily-change field, means genuinely no data at all) so a real equity-only read isn't discarded, and so a fully-failed fetch still correctly returns `None` rather than a `MacroBackdropRead` with every field empty.

**New function** (`scoring/probability_engine.py`):
```python
def _check_equity_risk_sentiment(
    instrument_score: float,
    instrument: str,
    macro_backdrop,  # MacroBackdropRead | None — reuses the same object, now carrying equity_index_trend_pct
) -> tuple[bool | None, str | None]:
    """
    Only ever returns non-(None, None) when INSTRUMENTS[instrument]
    ["usd_relationship"] == "risk_sentiment" (today: US30). Compares
    equity_index_trend_pct's sign (risk-on = positive = equities up)
    against instrument_score's sign for THIS instrument (not
    aggregate_usd) — an equity index has no USD sign of its own, it only
    means something as a risk-on/off cross-check for a risk_sentiment-
    mapped instrument's own score. (None, None) if the instrument isn't
    risk_sentiment-mapped, no equity data, or below threshold. (True,
    None) if equities agree. (False, note) if they clearly diverge —
    same confidence-only-discount contract as _check_macro_backdrop.
    """
```
`score_bundle()` wiring (after `instrument_score` is computed): `equity_agrees, equity_note = _check_equity_risk_sentiment(instrument_score, instrument, macro_backdrop)`; `if equity_agrees is False: confidence *= EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER`. New config constant `EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER` (same style as `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER`, untuned starting value). New `ProbabilityResult` fields: `equity_risk_agrees: bool | None = None`, `equity_risk_note: str | None = None`.

### 3. Oil shock flag

**Extends:** `data_layer/macro_backdrop.py`'s existing oil fetch — no new data source, one new field.

```python
oil_daily_change_pct: Optional[float]  # most recent single-session % change, distinct from the 10-day oil_trend_pct
OIL_SHOCK_DAILY_THRESHOLD_PCT = 4.0  # untuned — tighter than the 10-day OIL_LEAN_THRESHOLD_PCT=5.0 because this measures ONE session, not a 10-day drift
```

`_fetch_trend()` already returns the newest and oldest usable observations internally — this needs the newest-vs-second-newest delta as a separate value, so either a small new helper (`_fetch_daily_change(series_id)`) reusing the same FRED call shape, or extending `_fetch_trend()` to optionally also return the latest single-day change alongside the window trend (implementer's call at plan time — functionally equivalent, pick whichever keeps `_fetch_trend()`'s existing callers/tests unaffected).

**New function** (`scoring/probability_engine.py`):
```python
def _check_oil_shock(macro_backdrop) -> tuple[bool, str | None]:
    """
    Returns (True, note) if oil_daily_change_pct's magnitude exceeds
    OIL_SHOCK_DAILY_THRESHOLD_PCT — regardless of direction or of this
    bundle's own USD read; a shock is a "treat this call with extra
    caution, something sharp just happened outside the tracked
    calendar" flag, not an agree/disagree comparison. (False, None) if
    no data or below threshold. Never raises.
    """
```
`score_bundle()` wiring: `oil_shock, oil_shock_note = _check_oil_shock(macro_backdrop)`; `if oil_shock: confidence *= OIL_SHOCK_CONFIDENCE_MULTIPLIER`. New config constant `OIL_SHOCK_CONFIDENCE_MULTIPLIER`. New `ProbabilityResult` fields: `oil_shock_flag: bool = False`, `oil_shock_note: str | None = None` — surfaced on the dashboard card the same way `macro_backdrop_note` already is (⚠ prefix, shown when the flag is set), per the "visible note, not just a silent confidence change" decision.

## Data Flow

```
webapp/scheduler.py (or wherever macro_backdrop/cot_positioning reads are
currently sourced for score_bundle() callers)
  → data_layer.macro_backdrop.get_macro_backdrop_read()   [existing, now
    also carries equity_index_trend_pct + oil_daily_change_pct]
  → data_layer.cot_positioning.get_cot_positioning_read()  [new, cached
    daily]
  → scoring.probability_engine.score_bundle(..., macro_backdrop=...,
    cot_positioning=...)
      → _check_macro_backdrop()        [existing, unchanged]
      → _check_cot_crowding()          [new]
      → _check_equity_risk_sentiment() [new, instrument-scoped]
      → _check_oil_shock()             [new]
      → confidence = agreement * coverage, then each check's multiplier
        applied in sequence (order doesn't matter — all are simple
        multiplicative discounts)
```

All four checks (existing macro-backdrop + three new) are independent and composable — a bundle can be discounted by multiple simultaneously (e.g., macro-backdrop disagreement AND a crowded COT read AND an oil shock all at once is a real, valid, maximally-discounted state, not a contradiction to resolve).

## Error Handling

Every new module and check follows the codebase's established fail-open contract, identical to `data_layer/macro_backdrop.py`'s existing module docstring: a missing API key, failed request, too few observations, or any exception returns `None`/`(None, None)`/`(False, None)` as appropriate — never raises, never fabricates a value, never blocks the scoring cycle. `cot_positioning.py`'s daily cache follows the same "keep stale data, log a warning" pattern already used for the calendar feed and Alpha Vantage budget backoff — a failed COT fetch on a given day means "no crowding read today," not "crash" or "guess."

## Testing

- `tests/test_cot_positioning.py` — new file, mirrors `tests/test_macro_backdrop.py`'s structure: fetch success/failure, percentile/threshold edge cases, cache-hit-vs-fetch behavior, fail-open on missing key/bad response.
- `tests/test_macro_backdrop.py` — extended with equity index trend fetch tests (mirroring the existing dollar-index/oil tests) and the new daily-change field.
- `tests/test_probability_engine.py` — extended with `_check_cot_crowding()`, `_check_equity_risk_sentiment()` (including the instrument-scoping — must return `(None, None)` for XAUUSD regardless of equity data), and `_check_oil_shock()` unit tests, plus `score_bundle()` integration tests confirming: each new signal defaults to `None`/no-effect when omitted (backward compatible), each correctly multiplies confidence when triggered, and direction/probability are never touched by any of the three (this is the single most important invariant to test explicitly for all three, given it's the core design constraint from the brainstorm).

## Explicitly out of scope

- N2 (FOMC forward-guidance delta) and N5 (rate differentials/cross-central-bank divergence) — separate future specs, per the priority list and this spec's own Decisions section.
- The add-symbol categorized picker (Forex Major/Minor/etc., XM-sourced) — separate, unrelated feature, deliberately sequenced after this spec.
- Turning COT into a directional lean — explicitly deferred, confidence-dampener-only for now.
- Recalibrating any of the new (or existing) threshold constants against real backtest data — every threshold introduced here is a starting value, same as the codebase's existing constants, and calibration is its own future effort once enough real outcome data accumulates (this mirrors the existing SWOT's W7/R8 finding, unchanged by this spec).
