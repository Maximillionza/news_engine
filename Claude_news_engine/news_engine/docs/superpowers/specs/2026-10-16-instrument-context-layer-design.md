# Instrument Context Layer — Design

**Status:** PROPOSED 2026-10-16 (SAST). Not approved, nothing built. Per this project's convention (brainstorm → spec → plan → subagent-driven build), this needs your sign-off before a plan is written.

**Why now:** you've confirmed scope. Gold is traded today, but majors, indices and commodities will be added. That supersedes the US-only triage in `docs/fundamental-analysis-industry-benchmark-2026-10-16.md` §3. The 2026-10-16 audit's §5 sketched per-currency axes plus a gold axis; this spec turns that sketch into a contract that every future instrument follows.

**Requirement (yours):** a gold-specific context layer is acceptable *only if* the same approach applies to every instrument added later, with no rework.

---

## 1. Problem: transmission is encoded nine times, three different ways

`[Certain]` Each row below was read from the current code. Each one answers "how does this news/event reach instrument X?", and they don't share a key.

| # | Location | Keyed by | Instruments covered |
|---|---|---|---|
| 1 | `webapp/symbols.py` `classify_symbol()` → `usd_relationship` | ticker shape → `inverse`/`direct`/`risk_sentiment` | anything ticker-shaped; crosses get `None` |
| 2 | `scoring/probability_engine.py:818` `_map_to_instrument_score()` + `RISK_SENTIMENT_DAMPENING` | `usd_relationship` | same as #1 |
| 3 | `scoring/probability_engine.py:720` `_check_equity_risk_sentiment()` | `usd_relationship == "risk_sentiment"` | indices only |
| 4 | `alerting/symbol_relevance.py:29` `_CATEGORY_SYMBOL_CLASS_CHANNELS` + `_OIL_LINKED_SYMBOLS` | (6-category shock taxonomy, symbol_class) | class-level, plus USDCAD special case |
| 5 | `alerting/direction.py:84` `_LEAN_TABLE` | (6-category taxonomy, polarity, symbol_class) | class-level |
| 6 | `data_layer/exposure.py:42` `_NOT_EXPOSED` | (**8-category** taxonomy, symbol_class) | class-level |
| 7 | `data_layer/event_symbol_relevance.py` / `event_symbol_magnitude.py` | (event type, **exact symbol**), 108 + 94 hand-cited cells | the 12 picker symbols |
| 8 | `alerting/reality_check.py:20` `MAGNITUDE_THRESHOLDS` | exact symbol, **absolute points** ($10, 150 pts) | XAUUSD, US30 only |
| 9 | `data_layer/dukascopy_feed.py:35` `_INSTRUMENT_MAP`, `discovery_detector.py:35` `DETECTOR_SERIES` | exact symbol | hand-listed |

The consequences:

- **Adding one instrument means touching up to nine tables**, keyed by ticker shape, symbol class, exact symbol or one of two shock taxonomies.
- **Two shock taxonomies exist.** `alerting/taxonomy.py`'s 6 real-time categories and `scoring/backtest_store.py:950`'s 8 AdHoc categories describe the same world in different words. Rows #4/#5 use one and row #6 uses the other.
- **The per-cell grids (#7) grow as events × instruments.** `[Certain]` 9 × 12 = 108 relevance cells took several fix rounds for citation errors (feature inventory, 2026-09-16). At, say, 30 event types × 40 instruments, that's 1,200 cells per grid. It doesn't scale to "commodities etc.".
- **The single USD axis (#1–#2) can't express a two-sided pair** (EURUSD = EUR vs USD) or a driver that has nothing to do with the dollar (OPEC supply for oil, central-bank buying for gold).

Building gold's context the obvious way — more `XAUUSD` rows in #4–#8, more `metal`-class special cases — would add a tenth encoding, and it would be rewritten when EURUSD arrives.

---

## 2. Design principle: a factor model with per-instrument context providers

News and events produce **shocks to factors**. Instruments have **exposures** to factors. The impact on an instrument is the sum over factors of its exposure times that factor's shock:

```text
impact(instrument) = Σ_f exposure[instrument][f] × shock[f]
```

What goes into each layer:

- **Evidence is cited once per edge**: event → factor once, and instrument → factor once. It is no longer cited once per (event, instrument) cell, so maintenance grows as events + instruments instead of events × instruments.
- **Shared factors** carry everything instruments have in common: USD, other currency axes, US rates, risk appetite, safe haven, oil.
- **Context providers** carry what's specific to an instrument (gold's central-bank buying, oil's inventories), behind **one interface every instrument uses**. Gold is just the first provider.

`[Likely]` This is the standard organizing principle of multi-asset macro and risk systems: factor exposures plus asset-specific drivers. Macrosynergy's JPMaQS, for example, organizes indicators by currency area and factor family. It's a structure choice, not an accuracy claim. Exposures start hand-set and cited (the same discipline as today's trust weights) and get calibrated from the outcome DB once n allows.

**Behaviour-preserving start.** `[Certain]` by arithmetic, today's mapping is already a one-factor exposure vector:

| `usd_relationship` today | Equivalent exposure vector |
|---|---|
| `inverse` (XAUUSD, EURUSD…) | `{USD: -1.0}` |
| `direct` (USDJPY…) | `{USD: +1.0}` |
| `risk_sentiment` (US30…) | `{USD: -0.7}` (= `RISK_SENTIMENT_DAMPENING`) |
| `None` (crosses) | `{}` — later `{BASE: +1, QUOTE: -1}` |

So Phase 0 can replace #1–#2 with a dot product and prove byte-identical outputs with a regression test. That's the same discipline used when `EVENT_INFLUENCE_LINKS` absorbed the hardcoded precursor dict.

---

## 3. Components

### 3.1 Factor registry — `data_layer/factors.py` (new)

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Factor:
    factor_id: str        # e.g. "USD", "US_REAL_YIELD", "SAFE_HAVEN"
    description: str
    positive_means: str   # sign convention, e.g. "USD strengthens"
    live_sources: tuple[str, ...]  # data feeds that can shock it today; empty = dormant
```

Initial set, live versus dormant:

| Factor | Positive means | Live source today | Status |
|---|---|---|---|
| `USD` | USD strengthens | calendar surprises, article sentiment, Kalshi, DTWEXBGS | live |
| `US_REAL_YIELD` | real yields rise | FRED DFII10 | live |
| `US_2Y` | 2y yield rises (policy-path proxy) | FRED DGS2 | add |
| `RISK_APPETITE` | risk-on | FRED SP500 trend | live (VIX later) |
| `SAFE_HAVEN` | safe-haven demand rises | shock alerts (geopolitical/sovereign), GPR later | partial |
| `OIL` | crude rises | FRED DCOILWTICO | live |
| `EUR`, `JPY`, `GBP`, `CHF`, `CAD`, `AUD`, `NZD` | that currency strengthens | — | **dormant** until that currency's instrument is onboarded |

A dormant factor is registered but contributes zero, so an instrument can declare `{JPY: -1}` today without any JPY data existing yet.

### 3.2 Instrument profiles — `data_layer/instrument_profiles.py` (new)

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class InstrumentProfile:
    symbol: str
    asset_class: str                     # "metal" | "fx_major" | "fx_cross" | "index" | "energy" | "industrial_metal"
    exposures: dict[str, float]          # factor_id -> signed exposure; the ONLY transmission definition
    exposure_citations: dict[str, str]   # factor_id -> source/rationale (same citation discipline as exposure.py)
    context_provider: str | None         # registered provider name; None = shared factors only (explicit, never implicit)
    price_source: str                    # dukascopy instrument key (absorbs _INSTRUMENT_MAP)
    exposures_as_of: str = "2026-10-16"  # exposures are regime-dependent; dated so they can be revisited
```

Lookup rule: a hand-written profile wins. Otherwise `classify_symbol()` generates a default from the table in §2, which keeps today's behaviour for every symbol the picker can add.

Gold's profile is the first hand-written one. Values are starting points, `[Guessing]` until calibrated:

```python
XAUUSD = InstrumentProfile(
    symbol="XAUUSD", asset_class="metal",
    exposures={"USD": -1.0, "US_REAL_YIELD": -0.5, "SAFE_HAVEN": +0.6},
    exposure_citations={
        "USD": "USD-priced; existing inverse mapping",
        "US_REAL_YIELD": "GRAM opportunity cost; Layer2 notes the link weakened since 2024 -- deliberately < 1",
        "SAFE_HAVEN": "GRAM risk & uncertainty",
    },
    context_provider="gold", price_source="XAUUSD",
)
```

### 3.3 Event → factor map — keyed by `(country, title)`

`EVENT_SURPRISE_DIRECTION` becomes the USD special case of:

```python
EVENT_FACTOR_MAP: dict[tuple[str, str], dict[str, float]] = {
    ("USD", "CPI m/m"): {"USD": +1.0, "US_2Y": +1.0},
    ("USD", "Unemployment Rate"): {"USD": -1.0, "US_2Y": -1.0},
    # onboarded with EURUSD, not before:
    # ("EUR", "Main Refinancing Rate"): {"EUR": +1.0},
}
```

The factor shock is the **standardized** surprise (audit P0-2) multiplied by each loading. Keying by (country, title) is the audit's P1-4 and becomes mandatory here. It also closes audit §2.3 by construction: a Japanese `CPI m/m` row can only shock `JPY`.

### 3.4 News and shock attribution to factors

Every scored article and every shock alert carries `{country, institution, factors, polarity}`. Article sentiment becomes a **vote on a factor**, not a vote on USD:

- A dovish ECB article shocks `EUR −`. It reaches EURUSD and, through DXY weighting if desired, `USD +`. It never reaches `USD −`. This fixes audit §2.1 structurally.
- Shock alerts route through exposures. A shock on factor F reaches every tracked instrument with a nonzero exposure to F. That replaces #4–#6, and the 6- and 8-category taxonomies merge into one list where each category declares its factor shocks:

```python
SHOCK_FACTOR_MAP: dict[tuple[str, str], dict[str, float]] = {
    # (category, polarity) -> factor shocks
    ("geopolitical_conflict", "escalation"): {"SAFE_HAVEN": +1.0, "RISK_APPETITE": -1.0, "OIL": +0.5},
    ("trade_policy", "escalation"): {"RISK_APPETITE": -1.0, "SAFE_HAVEN": +0.5},
    ("energy", "escalation"): {"OIL": +1.0, "RISK_APPETITE": -0.5},
}
```

Under this rule gold now receives `trade_policy` shocks through `SAFE_HAVEN`, which closes the August-2025 gold-bar-tariff blind spot. USDCAD's oil linkage becomes an exposure (`CAD: +x` fed by `OIL`) instead of the `_OIL_LINKED_SYMBOLS` special case.

### 3.5 Context providers — the uniform "context layer"

```python
import datetime as dt
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class DriverRead:
    value: float | None
    lean: int | None          # +1 / -1 / None for the instrument itself
    as_of: dt.date | None     # provenance -- never fabricated, same fail-open contract as macro_backdrop.py
    note: str = ""


@dataclass
class ContextRead:
    drivers: dict[str, DriverRead]              # driver family -> reading
    expected_magnitude_pct: float | None        # vol-scaled expected move; the field an ACE risk gate would consume
    flags: list[str] = field(default_factory=list)  # e.g. "crowded_long", "bullion_tariff_risk"


class ContextProvider(Protocol):
    name: str
    asset_classes: tuple[str, ...]
    def read(self, symbol: str, as_of: dt.datetime) -> ContextRead | None: ...
```

These rules apply to **every** provider, gold included:

1. **Confidence-only until backtested.** A context read can discount confidence and set flags. It can't override direction. This is the existing discipline from `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER` and the COT dampener.
2. **Logged.** Every fired driver is written to the existing `confidence_multipliers_json` audit trail.
3. **Fail-open with provenance.** A missing feed returns `None` with no invented value, and every input carries `as_of`.
4. **Driver families follow a named framework** for the asset class, never an ad-hoc list (§4).
5. **A test enforces coverage.** Every tracked symbol's profile names a provider or explicitly declares `None`.

---

## 4. The driver-family template per asset class

Gold is fully specified. The other rows exist to prove the interface fits before gold is built; they aren't built until their instrument is onboarded.

| Asset class | Framework | Driver families (shared factor ← → provider-specific) | First data sources |
|---|---|---|---|
| **Gold** (XAUUSD; XAGUSD reuses it with an added industrial-demand driver) | WGC GRAM | Opportunity cost → shared `USD`, `US_REAL_YIELD`. Risk & uncertainty → shared `SAFE_HAVEN` plus provider GVZ and GPR. **Momentum & positioning → provider**: COMEX managed-money COT, ETF holdings, central-bank purchases. Economic expansion → minor at intraday horizons | CFTC Disaggregated COT, gold contract (same Socrata API as `cot_positioning.py`) `[Likely]`; FRED `GVZCLS` `[Likely]`; Iacoviello GPR (monthly, free) `[Certain]`; ETF holdings and WGC/central-bank data `[Guessing]` on free programmatic access, to verify before relying on it |
| **FX majors** | Rate differential + CB reaction function + positioning | Shared currency axes ← rate differential (2y), CB stance and decision surprises, relative surprise index, terms of trade (commodity FX), TFF COT per currency, intervention risk (JPY/CHF) | Treasury and foreign yields, CB calendars, CFTC TFF |
| **Equity indices** | Risk appetite + discount rate + earnings | Shared `RISK_APPETITE`, `US_2Y`/`US_REAL_YIELD`. Provider: VIX level/term structure, earnings-season calendar, index construction (US30 is price-weighted, NAS100 tech-concentrated) | FRED VIXCLS, SP500 |
| **Energy (oil)** | Supply / inventories / demand | Shared `OIL`, `RISK_APPETITE`, small `USD`. Provider: EIA weekly inventories, OPEC+ meeting calendar, outages, Disaggregated COT | EIA open data `[Likely]` free with key |
| **Industrial metals** | China demand + inventories | Shared `RISK_APPETITE`, `USD`. Provider: China PMIs, exchange inventories | `[Guessing]` — free inventory data is uncertain; verify at onboarding |

**Acceptance test for the template.** The second instrument onboarded — for example EURUSD — must need **zero edits to scoring core or alerting**. It should only need:

- an `InstrumentProfile`
- its currency's `EVENT_FACTOR_MAP` rows
- its context provider

If it needs a core edit, the design failed and gets fixed before a third instrument is added.

---

## 5. What happens to existing code (migration, not rewrite)

| Existing | Fate | Phase |
|---|---|---|
| `classify_symbol()` | Kept as the **default-profile generator** | 0 |
| `_map_to_instrument_score()`, `webapp/scoring_service.py`'s copy, `RISK_SENTIMENT_DAMPENING` | Replaced by the exposure dot product; regression test asserts identical outputs | 0 |
| `EVENT_SURPRISE_DIRECTION` | Becomes `EVENT_FACTOR_MAP[("USD", title)]` | 1 |
| `event_symbol_relevance` / `event_symbol_magnitude` (202 cited cells) | **Kept as validation evidence.** The factor model's derived relevance must agree with the 94 `RELEVANT` cells, and any disagreement is investigated. No new per-symbol cells get written | 1 |
| `_CATEGORY_SYMBOL_CLASS_CHANNELS`, `_LEAN_TABLE`, `_NOT_EXPOSED`, both shock taxonomies | Unified `SHOCK_FACTOR_MAP` with routing through exposures. Citations carried over | 3 |
| `MAGNITUDE_THRESHOLDS` (absolute $ / points) | Vol-scaled thresholds from the instrument's own baseline σ | 3 |
| `_INSTRUMENT_MAP`, `DETECTOR_SERIES` | `InstrumentProfile.price_source`, plus detector series per live factor | 3 |
| `cot_positioning.py` (USD Index) | Becomes the `USD` factor's positioning input. Gold COT goes into the gold provider using the same fetch pattern | 2 |
| `macro_backdrop.py` | Becomes the live-source feed for `USD`, `US_REAL_YIELD`, `OIL`, `RISK_APPETITE` | 0–1 |

---

## 6. Phasing — each phase independently shippable, gold first

| Phase | Delivers | Behaviour change | Effort |
|---|---|---|---|
| **Pre-0** (audit P0-1, now) | Foreign-CB exclusion from FOMC-family scoring, as a live-bug stopgap. The foreign-CB name list is reused as Phase 1's attribution fast path, so it isn't throwaway | Removes mis-signed articles | Low |
| **0** | Factor registry, profiles with generated defaults, dot product replacing `usd_relationship` mapping | **None** (regression-tested) | Low |
| **1** | `(country, title)` event→factor map, standardized surprises (P0-2), article attribution to factors | Surprise scaling changes, so re-run the essence history and report how many past directions change | Medium |
| **2** | **Gold context provider**: COMEX COT, GVZ expected magnitude, GPR, ETF and central-bank flows where a free source is confirmed | Confidence and flags only, plus `expected_magnitude_pct` | Medium |
| **3** | Shock routing via exposures, unified taxonomy, vol-scaled thresholds | Gold starts receiving trade-policy alerts | Medium |
| **4** | Second instrument through the template (EURUSD or whichever you trade first) — the acceptance test in §4 | New instrument only | Medium |
| **5+** | Index and commodity providers as each is onboarded | Per instrument | Per instrument |

Recommended second instrument: **EURUSD** `[Likely]`. It's the most liquid pair, EUR is 57.6% of DXY, the ECB calendar is clean, and the Pre-0 fix already sends ECB news somewhere useful. USDJPY adds intervention and carry dynamics, which make it a harder first test of the template.

---

## 7. Audit recommendations under the clarified scope

This supersedes `docs/fundamental-analysis-industry-benchmark-2026-10-16.md` §3.

| # | Item | Status now | Where it lands |
|---|---|---|---|
| P0-1 | Foreign-CB attribution | **Keep, now** | Pre-0 stopgap → Phase 1 attribution |
| P0-2 | Standardized surprises | **Keep** | Phase 1 |
| P0-3 | Rotate the Alpha Vantage key | **Keep, now** | — |
| P1-4 | (country, title) keying | Defer → **Keep** | Phase 1 (foundational) |
| P1-5 | Wire influence-link weights | **Keep** | Independent, any time |
| P1-6 | Shock-alert country tags and routing | Trim → **Keep in full** | Phase 3, through exposures |
| P1-7 | COMEX gold COT | **Keep** | Phase 2, inside the gold provider |
| P2-8 | JPY pilot | Drop → **Phase 4 template test** | EURUSD or USDJPY, your choice |
| P2-9 | CB-stance model plus FOMC delta | **Keep, P1** | Feeds `USD`/`US_2Y` factor shocks; reused per CB later |
| P2-10 | Transmission graph | Trim → **Keep, as the factor registry plus exposures** | Phases 0 and 3, not a separate graph |

Benchmark §4 (ACE integration, validation horizon, revisions, dispersion, magnitude prediction) is unaffected and still applies. `expected_magnitude_pct` in §3.5 is the field the ACE risk-gate bridge would read.

---

## 8. Non-goals and risks

- **Not a statistically fitted factor model yet.** Exposures are cited starting values. Calibrating them from graded outcomes waits for sample size, the same as every other constant in `config/settings.py`.
- **Exposures drift with regime.** Gold's real-yield link weakened after 2022, per the repo's Layer2 notes. Exposures are dated (`exposures_as_of`) and meant to be revisited; the gold provider exists precisely because shared factors under-explain gold.
- **Each new currency or commodity adds data feeds,** and each feed is a failure mode for a one-person operation (benchmark §4.9). Onboard instruments one at a time, behind the §4 acceptance test.
- **No ACE changes here.** The ACE news-blackout fix and any ACE bridge are separate work.

## 9. Open questions for you

1. Is the second instrument EURUSD, or something you'll actually trade sooner?
2. Is the gold provider's ETF and central-bank data allowed to come from a registration-gated source (WGC Goldhub), or only open APIs?
3. Phase 0 changes no numbers, but it touches the scoring core. Should it ship on its own before any Phase 1 work?
