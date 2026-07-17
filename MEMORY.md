# MEMORY.MD — Masood's Persistent Knowledge Base
> Last updated: 2026-06-23
> Sync rule: Claude must prompt Masood to update this file whenever a version bump, architecture change, or new project is introduced in conversation.

---

## Identity & Context

- **Name:** Masood
- **Location:** South Africa (UTC+2 / SAST)
- **Role:** Algorithmic trader + full-stack developer
- **Primary trading instrument:** XAUUSD (Gold)
- **Broker / Platform:** XM broker, MetaTrader 5 (MT5)
- **Other interests:** Graphic design (Vantage Studio brand), vehicle visualisation (Moddy app), 3D modelling (FORGE)

---

## Technical Fluency

Do not over-explain the following — Masood knows these well:

| Domain | Technologies |
|---|---|
| EA Development | MQL5, MQL4, MetaEditor, Strategy Tester |
| Python | Type hints, pandas, backtesting frameworks, Bayesian inference, Monte Carlo, walk-forward validation |
| Android | Kotlin, Jetpack Compose, MVVM, Hilt, Room, ML Kit |
| Web / Frontend | React, Three.js, HTML/CSS/JS |
| Concepts | ICT/SMC (BOS, CHoCH, FVG, OB, liquidity sweeps, kill zones, AMD model), regime-based trading, Kelly criterion, ATR-based sizing |

---

## Active Projects

### ACE — Adaptive Confluence Engine
| Field | Value |
|---|---|
| Type | MQL5 Expert Advisor |
| Instrument | XAUUSD, MT5 |
| Current version | v3.14.3 |
| Magic number | 203143 |
| File prefix | `ACE_` (e.g. `ACE_RegimeProfile.mqh`) |
| Header label | "Adaptive Confluence Engine" |

**Architecture**
- 8-state machine: IDLE → WAIT_HTF → WAIT_SETUP → WAIT_TRIGGER → WAIT_EXECUTION → MANAGE → COOLDOWN
- Regime classifications: TRENDING, RANGING, COMPRESSION, HIGH_VOL, MANIPULATION
- Two-layer HTF architecture: H1 primary / D1 ceiling, 2-candle stability rule
- Per-regime input parameters (20 per regime)
- Counter-trend gate: H4 EMA separation ratio (`h4EMASep / h4ATR`), input `InpCTEMASepThreshold`, default 0.80

**Key conventions**
- Magic number format: `20XXXX` — last 4 digits reflect version (e.g. v3.14.3 → 203143). Apply automatically on every version bump.
- Trade comment stamping format: `R:COMPRESS D:SHORT S:74.3`
- Log analysis cutoff: ignore data before **15:30:00 SAST on 2026-05-05** (prior EA version)

**Recent history**
- v3.14.2: fixed threshold logging bug, EMA_Fallback losses in RANGING, COMPRESSION threshold, off-session bias staleness
- v3.14.3: added `ACE_DisplayPanel.mqh` chart display panel + trade comment stamping
- v3.14.3 CT gate: counter-trend quality gate via H4 EMA separation ratio (delivered as `ACE_v3143_ct_gate_v3.zip`)

---

### MAE — Market Analysis Engine
| Field | Value |
|---|---|
| Type | MQL5 multi-symbol market scanner |
| Current version | v2.5.0 |
| Current filename | `MarketAnalysisEngine_7.mq5` |
| File suffix note | Suffix increments per major save session — independent of semantic version |

---

### SOR — Signal Outcome Recorder
| Field | Value |
|---|---|
| Type | MQL5 companion recorder |
| Current version | v1.1 |
| Current filename | `SignalOutcomeRecorder_3.mq5` |
| File suffix note | Same convention as MAE — suffix ≠ version |

---

### Traders Journey
| Field | Value |
|---|---|
| Type | Auto-journaling MT5/MT4 indicator |
| MT5 version | v4.5.1 (`Traders_Journey_v4_5_1.mq5`) |
| MT4 version | v1.1 (`Traders_Journey_mt4_v1_1.mq4`) |
| Parity | MT4 and MT5 versions maintained at feature parity |

---

### Moddy — Vehicle Visualiser App
| Field | Value |
|---|---|
| Type | Android app |
| Version | V2 |
| Stack | Kotlin, Jetpack Compose, MVVM, Hilt, Room, ML Kit |
| ML Kit usage | Object Detection + Subject Segmentation for vehicle part zone detection |
| Critical constraint | **Never add `applicationIdSuffix` to debug build variants** — causes Android 16 process freeze on Samsung Galaxy S22 Ultra |
| Testing | Autonomous Claude Code testing loop (7-step post-phase cycle), 3 manual checkpoint phases |

---

### FORGE — 3D Modelling App
| Field | Value |
|---|---|
| Type | Browser-based 3D modelling tool |
| Stack | React, Three.js (prototype stage) |

---

## Conventions & Rules

### File Delivery
- Send **affected files individually** unless more than 5 files change → then send full `.zip`
- Always include a version bump with any changed file
- Magic number: update automatically on every ACE version bump, no need to ask

### Code Style
- MQL5: include concise, purposeful comments; always add a default value and unit/effect comment on new inputs
- Python: type hints on all function signatures; `if __name__ == "__main__"` block with working example in scripts
- General: no one-liners that sacrifice clarity; code blocks always, even for short snippets

### Communication
- No preamble before code blocks — deliver the code
- No unsolicited refactoring unless it fixes a real problem
- No explaining syntax Masood clearly already knows
- Confidence tagging on non-trivial claims: `[Certain]` / `[Likely]` / `[Guessing]`
- Time references in **SAST (UTC+2)** unless otherwise specified

---

## Trading Context

### Strategy Concepts in Use
- ICT/SMC: BOS, CHoCH, FVG, Order Blocks, liquidity sweeps, kill zones, AMD model
- Regime-aware execution (TRENDING / RANGING / COMPRESSION / HIGH_VOL / MANIPULATION)
- HTF bias filtering (H4, D1) with H1 as trigger layer
- Counter-trend quality gates using ATR-normalised EMA separation
- Dynamic risk sizing (floor/ceiling ladder system, Kelly-lite deprecated)
- Session filters (direction-specific)

### Tooling
- Strategy Tester: MT5 native + HTML comparison dashboard (baseline + 5 challenger slots, Charts/Metric/Input Parameter tabs)
- Log viewer: browser-based, pipeline replay + analytics dashboard
- Bayesian Optimizer: custom-built (UCB surrogate, walk-forward validation, regime-aware scoring)
- EA Tester hybrid framework: Python

---

## Sync Reminder Protocol

Claude must prompt Masood to update this file when any of the following occur in conversation:
- A version bump is introduced (ACE, MAE, SOR, TJ, Moddy)
- A new project is started
- A new architectural decision is made (new module, new input, new convention)
- A critical constraint is identified (e.g. platform bugs, broker-specific behaviour)

Suggested prompt: *"Want me to update MEMORY.md to reflect [change]?"*
