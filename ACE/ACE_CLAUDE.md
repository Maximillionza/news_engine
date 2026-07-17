# CLAUDE.MD — ACE (Adaptive Confluence Engine)
> MQL5 Expert Advisor | XAUUSD | MT5 via XM Broker
> Masood — South Africa (UTC+2 / SAST)
> Last updated: 2026-06-23

---

## What This File Is

This is the authoritative context document for all ACE development and debugging sessions. Claude reads this at session start and must not ask Masood to re-explain architecture, conventions, or module contracts already covered here.

**Sync rule:** Claude must prompt Masood to update this file when any version bump, new module, new input, or architectural decision is introduced.

---

## Project Identity

| Field | Value |
|---|---|
| Full name | Adaptive Confluence Engine |
| Short name | ACE |
| File prefix | `ACE_` |
| Header comment | Must read "Adaptive Confluence Engine" in all source files |
| Current version | v3.14.3 |
| Magic number | 203143 |
| Instrument | XAUUSD |
| Platform | MT5 |
| Broker | XM |

### Magic Number Convention
Format: `20XXXX` where last 4 digits = version digits concatenated.

| Version | Magic Number |
|---|---|
| v3.14.3 | 203143 |
| v3.14.2 | 203142 |
| v3.14.1 | 203141 |

**Apply automatically on every version bump. Never ask.**

---

## File Delivery Rules

- Send **affected files individually** unless more than 5 files change → send full `.zip`
- Always bump the version when delivering changed files
- Zip naming convention: `ACE_v{version}_{feature_tag}.zip` (e.g. `ACE_v3143_ct_gate_v3.zip`)
- No preamble before code blocks — deliver the code

---

## Architecture Overview

ACE is a regime-aware, multi-timeframe Expert Advisor built on ICT/SMC concepts. It operates as an **8-state machine** with a **two-layer HTF bias architecture**.

### State Machine

```
IDLE → WAIT_HTF → WAIT_SETUP → WAIT_TRIGGER → WAIT_EXECUTION → MANAGE → COOLDOWN
                                                                          ↓
                                                                        IDLE
```

| State | Responsibility |
|---|---|
| IDLE | EA initialised, waiting for session open or cooldown expiry |
| WAIT_HTF | Polling HTF bias — H1 primary, D1 ceiling. Requires 2-candle stability before advancing |
| WAIT_SETUP | Looking for valid setup structure (OB, FVG, liquidity sweep) aligned with bias |
| WAIT_TRIGGER | Waiting for trigger confirmation (BOS, CHoCH, candle close) |
| WAIT_EXECUTION | Entry conditions met, awaiting execution window (spread, session, slippage check) |
| MANAGE | Position open — trailing, TP mode execution, partial close logic |
| COOLDOWN | Post-trade lockout period before returning to IDLE |

### Two-Layer HTF Bias Architecture

- **H1 = Primary bias layer.** Drives directional decision. BOS/CHoCH on H1 sets the active bias.
- **D1 = Ceiling layer.** Acts as a hard filter — H1 bias must align with D1 bias to proceed.
- **2-candle stability rule:** HTF bias must hold for 2 confirmed candles before the state machine advances past WAIT_HTF. Prevents whipsaw entries on single-candle flips.

**Known architectural behaviour:** H1 BOS can temporarily flip direction during relief bounces even when H4/D1 trend is committed in the opposite direction. This is by design — H1 overrides H4 within the current architecture. The counter-trend gate (`InpCTEMASepThreshold`) exists to suppress low-quality setups in this scenario.

---

## Regime Engine

### Classifications

| Regime | Description |
|---|---|
| TRENDING | Clear directional structure, BOS sequence intact |
| RANGING | Price oscillating between defined highs and lows, no clear BOS |
| COMPRESSION | Narrowing range, ATR contraction, pre-breakout condition |
| HIGH_VOL | ATR expansion above threshold, volatile/news-driven conditions |
| MANIPULATION | Liquidity sweep detected without follow-through, potential trap |

### Regime Detection Logic
- Regime is classified on H1 (primary) with D1 as context
- ATR used as normalisation baseline across all regime thresholds
- COMPRESSION threshold was historically set too low — raised in v3.14.2 fix
- Regime is re-evaluated on each new H1 candle close

### Per-Regime Input Parameters
Each regime has **20 dedicated input parameters** controlling behaviour independently. These include (but are not limited to):

- Entry aggressiveness (confirmation requirements)
- TP mode selection (see TP Modes below)
- Risk percentage
- Minimum score threshold
- Session filter overrides
- Liquidity detection routing
- EMA bias weight

> ⚠️ **INCOMPLETE SECTION** — Full per-regime input parameter list to be added by Masood. Do not fabricate specific input names not listed here.

---

## Module Index

### Core Modules

| File | Responsibility |
|---|---|
| `ACE.mq5` | Main EA file — state machine, OnTick, OnInit, OnDeinit |
| `ACE_RegimeProfile.mqh` | Regime classification engine + per-regime parameter routing |
| `ACE_DisplayPanel.mqh` | Chart display panel (added v3.14.3) |

### Supporting Modules

| File | Responsibility |
|---|---|
| `ACE_SignalLayer.mqh` | BOS/CHoCH detection, FVG identification, OB validation |
| `ACE_ExecutionLayer.mqh` | Order placement, spread checks, slippage guard, partial close |
| `ACE_RiskEngine.mqh` | Position sizing — dynamic risk ladder (floor/ceiling), ATR-based SL |
| `ACE_LiquidityEngine.mqh` | Liquidity sweep detection, routing to regime classifier |
| `ACE_BiasEngine.mqh` | HTF bias management — H1 primary, D1 ceiling, stability rule |
| `ACE_SessionFilter.mqh` | Kill zone definitions, direction-specific session gates |

> ⚠️ **INCOMPLETE SECTION** — Confirm active module filenames against current codebase. Some modules may be consolidated or renamed.

---

## Key Inputs & Parameters

### Counter-Trend Gate (added v3.14.3)

| Input | Default | Description |
|---|---|---|
| `InpCTEMASepThreshold` | 0.80 | Minimum H4 EMA separation ratio (h4EMASep / h4ATR) required to allow a counter-trend setup. Below this threshold, counter-trend entries are suppressed. |

**Logic:** Self-normalising — divides raw H4 EMA separation by H4 ATR. A ratio below `InpCTEMASepThreshold` indicates insufficient trend commitment on H4, suppressing the counter-trend trade regardless of H1 signal quality.

### Risk Sizing

- Dynamic risk ladder system (Kelly-lite deprecated)
- Floor: 5% | Ceiling: 30%
- SL based on ATR — per-symbol pullback ATR values
- No fixed lot sizing — always ATR-normalised

### TP Modes

> ⚠️ **INCOMPLETE SECTION** — List all available TP modes and their per-regime routing logic here. Claude must not guess mode names.

### Trade Comment Format

```
R:{REGIME} D:{DIRECTION} S:{SCORE}
```

Example: `R:COMPRESS D:SHORT S:74.3`

- `R:` = Active regime at entry
- `D:` = Trade direction (LONG / SHORT)
- `S:` = Signal score at entry (0–100)

---

## Signal & Entry Logic

### Trigger Types

| Trigger | Description |
|---|---|
| BOS | Break of Structure — primary trend-continuation trigger |
| CHoCH | Change of Character — standalone reversal trigger (not just a filter) |
| Liquidity Sweep | Price takes out a swing high/low then reverses — confirms trap |

### Entry Scoring
- Signal score (0–100) computed from confluence of: HTF bias alignment, structure quality, session timing, regime match, FVG/OB proximity
- Minimum score threshold is regime-dependent (set via per-regime inputs)
- Score stamped in trade comment at entry

### Session Filters
- Kill zones defined (London open, NY open, London close)
- Direction-specific filters — certain sessions suppressed for LONG or SHORT depending on regime
- Off-session bias staleness fix applied in v3.14.2 — bias resets correctly after session gap

---

## Debugging Guide

### Diagnosing a Bad Trade

**Step 1 — Read the trade comment**
```
R:COMPRESS D:SHORT S:74.3
```
Immediately tells you: what regime was active, what direction was taken, and the signal score. If the score seems high but the trade was bad, the problem is in regime classification or HTF bias — not scoring weights.

**Step 2 — Check HTF bias at entry time**
- Was H1 bias genuinely aligned with D1 ceiling?
- Did the 2-candle stability rule fire correctly, or did it advance on a single candle?
- Was this a counter-trend setup? If so, did `InpCTEMASepThreshold` fire as expected?

**Step 3 — Check regime at entry**
- Was COMPRESSION classified correctly or was ATR threshold too low?
- Was MANIPULATION detected but overridden?
- Cross-reference regime with H4 EMA separation — if H4 shows committed trend opposite to trade direction, CT gate may not have suppressed correctly.

**Step 4 — Check session filter**
- Was the trade taken during a valid kill zone?
- Was direction suppressed for this session in the current regime config?
- Check for off-session staleness — bias set before session gap, not refreshed.

**Step 5 — Log cutoff**
- Ignore all log data before **15:30:00 SAST on 2026-05-05** — belongs to prior EA version.

---

### Common Failure Patterns

| Symptom | Likely Cause | Where to Look |
|---|---|---|
| Bad long against H4 bear trend | H1 BOS flipped LONG on relief bounce | CT gate — check `InpCTEMASepThreshold` value vs actual h4EMASep/h4ATR ratio at entry |
| EMA_Fallback losses in RANGING | EA falling back to EMA signal when structure is absent | `ACE_BiasEngine.mqh` — EMA fallback logic, RANGING regime inputs |
| Entries firing off-session | Bias staleness from prior session | `ACE_SessionFilter.mqh` — staleness reset logic (fixed v3.14.2) |
| COMPRESSION entries too frequent | COMPRESSION ATR threshold too low | Per-regime COMPRESSION inputs — raise ATR contraction threshold |
| Threshold not appearing in logs | Logging bug for threshold values | Fixed v3.14.2 — if still occurring, check log formatting in regime profile engine |
| Score high but trade invalid | Regime misclassified at entry | Cross-reference trade comment regime vs H1/D1 structure at that timestamp |

---

### Log Analysis Protocol

1. Always anchor to cutoff: **15:30:00 SAST on 2026-05-05**
2. Filter by magic number `203143` (current) — older magic numbers = prior versions, exclude
3. Read trade comment first (`R:` / `D:` / `S:`) before checking OHLC
4. Cross-reference entry timestamp against H1 candle close (not tick time)
5. When reviewing a loss cluster, check if regime was consistent across all losses — same regime + same direction = systematic problem in that regime's config

---

## Version History (Recent)

| Version | Key Changes |
|---|---|
| v3.14.3 | Added `ACE_DisplayPanel.mqh` chart panel; trade comment stamping (`R:COMPRESS D:SHORT S:74.3`); CT gate (`InpCTEMASepThreshold` = 0.80) |
| v3.14.2 | Fixed: threshold logging bug, EMA_Fallback losses in RANGING, COMPRESSION threshold too low, off-session bias staleness |
| v3.14.1 | Per-regime TP modes wired; configurable liquidity detection routing |
| v3.14.0 | Regime profile engine delivered — 20 per-regime input parameters |
| v3.13.0 | Two-layer H1-primary/D1-ceiling architecture; 2-candle stability rule |

---

## What Claude Must Never Do

- Rename files from `ACE_` prefix to anything else without explicit instruction
- Change the magic number format or skip updating it on a version bump
- Restructure the state machine without explicit architectural approval
- Assume per-regime input names not listed in this document — ask instead
- Suggest replacing the dynamic risk ladder with fixed lot sizing
- Fabricate module filenames not confirmed in the Module Index above
- Ignore the log cutoff timestamp when analysing trade history
