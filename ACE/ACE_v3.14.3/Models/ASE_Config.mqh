#ifndef ASE_CONFIG_MQH
#define ASE_CONFIG_MQH
//+------------------------------------------------------------------+
//| ASE v3.14.0 — All Input Parameters                              |
//| v3.14.0: Added per-regime profile inputs (── Regime Profiles ──) |
//+------------------------------------------------------------------+

// ── TP Calculation Mode (v4.0) ────────────────────────────────────
// Controls how TP1 and TP2 levels are calculated at entry time.
enum ENUM_TP_MODE
{
   TP_ATR        = 0,  // ATR × multiplier (consistent, regime-agnostic)
   TP_STRUCTURAL = 1,  // Structural target; ATR fallback when unavailable
   TP_HYBRID     = 2,  // Structural clamped to ATR bounds; ATR fallback outside
};

// ── Risk ──────────────────────────────────────────────────────────
input double InpRiskPercent        = 0.50;   // Risk % per trade
input double InpMinRR              = 2.0;    // Minimum acceptable R:R

// ── ATR ───────────────────────────────────────────────────────────
input int    InpATRPeriod          = 14;     // ATR period (M15)
input double InpATRMultiplierSL      = 1.0;   // SL = ATR x this (COMPRESSION baseline)
input double InpATRMultiplierSL_Wide = 1.5;   // SL multiplier for RANGING regime
input double InpATRSLCap             = 15.0;  // Max SL in points (0=no cap; GOLD/XM: 15.0)
input double InpATRMultiplierTP1     = 2.0;   // TP1 = ATR x this (ATR mode only)
input double InpATRMultiplierTP2     = 4.0;   // TP2 = ATR x this (runner)
input double InpATRTrailMultiplier   = 1.5;   // Trailing stop = ATR x this
input ENUM_TP_MODE InpTP1Mode = TP_ATR;        // TP1 mode: ATR gives clean 2×ATR target
input ENUM_TP_MODE InpTP2Mode = TP_ATR;        // TP2 mode: runner stays ATR-based

// ── EMA ───────────────────────────────────────────────────────────
// v3.12.2 — H4 EMA vote uses bar[1] cross only (slope removed).
// EMA20 > EMA50 on last confirmed H4 bar = LONG vote.
// EMA20 < EMA50 on last confirmed H4 bar = SHORT vote.
// H4 now always votes — never neutral. The prior slope condition
// (fast[1] > fast[2]) caused H4 to abstain during normal pullbacks,
// deadlocking the gate at 1v1 for entire trading days.
input int    InpH4FastEMA          = 20;     // H4 fast EMA (bar[1] cross-only vote — v3.12.2)
input int    InpH4SlowEMA          = 50;     // H4 slow EMA (bar[1] cross-only vote — v3.12.2)
// ── H1 Market Structure Bias (v3.5.0) ────────────────────────────
// Direction is set by H1 Break of Structure (BOS) — a candle close beyond
// the most recent H1 swing high (LONG) or swing low (SHORT).
input int    InpH1SwingPivot      = 2;    // Bars each side to confirm H1 swing pivot
                                           // 2=standard 3=conservative (fewer swings)
input int    InpH1SwingLookback   = 10;   // H1 bars to scan for swing high/low
                                           // 10=~1.5 sessions 16=~2 sessions
// v3.7.0 — Ranging-day staleness guard.
// If no new H1 BOS fires within this many H1 bars of the last confirmed BOS,
// the bias is considered stale and reset to DIR_NONE. Pipeline holds until a
// fresh BOS re-establishes direction. Prevents prior-session bias from entering
// trades on a ranging or low-momentum day.
// v3.9.5 fix: default raised from 20 to 120 (5 trading days).
// At 20 bars (20 hours) the guard was firing constantly on normal GOLD trending
// days where H1 BOS events naturally space 24–48 hours apart, causing the
// pipeline to stall and wipe bias every single day. 120 bars = 5 trading days
// — only fires on genuine multi-day consolidation. 0 = disabled.
input int    InpH1BiasStaleBars   = 120;  // H1 bars before bias expires (0=off)
input int    InpM15EMA             = 21;     // M15 dynamic S/R
input int    InpM1FastEMA          = 9;      // M1 trigger fast EMA
input int    InpM1SlowEMA          = 21;     // M1 trigger slow EMA

// ── Execution ─────────────────────────────────────────────────────
input int    InpMaxSpread          = 70;     // Max spread in points (hard gate)
input double InpSpreadBaseline     = 35;      // Min achievable spread for instrument (0=disabled)
                                             // GOLD/XM recommended: 30–35
                                             // When > 0, spread score uses range [baseline, max]
                                             // so tight-but-not-zero spreads score near 10.
input int    InpMaxPositions       = 1;      // Max concurrent positions
input int    InpCooldownBars       = 5;      // Cooldown bars (M15) after close — 5 bars = 75 min
input int    InpMagicNumber        = 203143; // EA magic number (v3.14.3 — bumped from 203142 to avoid colliding with prior-version open positions/history on the same account)

// ── Sessions ──────────────────────────────────────────────────────
input bool   InpUseLondon          = true;   // Trade London session
input bool   InpUseNY              = true;   // Trade NY session
input bool   InpTrade24_7          = false;  // MASTER: trade 24/7 (bypasses session filter)
// v3.7.0 — ICT Kill Zone sub-scoring (Task 11).
// When enabled, trades inside the London KZ (08:00–11:00 UTC) or NY KZ
// (13:00–16:00 UTC) score 10.0 vs 9.5 for plain Overlap and 8.0/7.0 for
// London/NY outside KZ. The KZ windows are fixed ICT definitions.
input bool   InpKillZoneEnabled    = true;   // Score kill zones at 10.0 (vs Overlap 9.5)
// Session windows — all times in UTC (broker-offset independent).
// Default values match GOLD/FX standard sessions.
// To use ICT kill zones only: London 08:00–11:00, NY 13:00–16:00.
// To use DAX Frankfurt-led:   London 07:00–10:00, NY 13:00–17:30.
input int    InpLondonStartHour    = 7;      // London open  — hour   (UTC)
input int    InpLondonStartMin     = 0;      // London open  — minute (UTC)
input int    InpLondonEndHour      = 12;     // London close — hour   (UTC)
input int    InpLondonEndMin       = 30;     // London close — minute (UTC)
input int    InpNYStartHour        = 12;     // NY open      — hour   (UTC)
input int    InpNYStartMin         = 30;     // NY open      — minute (UTC)
input int    InpNYEndHour          = 21;     // NY close     — hour   (UTC)
input int    InpNYEndMin           = 0;      // NY close     — minute (UTC)

// ── Scoring ───────────────────────────────────────────────────────
input double InpScoreThreshold     = 60.0;  // Min score to enter (0–100)
// v3.7.0 — Per-component minimum floors (Task 08).
// When non-zero, the named component must reach its raw floor or the
// trade is blocked regardless of total score.
// h4Bias raw range: 0–30 (StructureEngine BOS score).
// m15Setup raw range: 0–25 (SetupEngine setup class score).
input double InpMinBiasScore       = 0.0;   // Min h4Bias raw score (0=off; suggested 15)
input double InpMinSetupScore      = 0.0;   // Min m15Setup raw score (0=off; suggested 12)

// ── Strategy Modes ────────────────────────────────────────────────
input int    InpBiasReEvalBars     = 8;    // Bars bias block holds after 4/4 M15 conflict (one-way timer)
                                            // v3.12.0: timer no longer resets on continued conflict —
                                            // it drains to zero then PASSES regardless of M15 momentum.
                                            // 3/4 conflict threshold removed (was causing all-day silence).
                                            // Only 4/4 conflict triggers a new block.
                                            // 4=aggressive 8=balanced(default) 16=conservative
input int    InpBiasFlipCycles     = 3;    // Consecutive re-block cycles before H4 bias re-eval
                                            // v3.4.9: after N full cycles of persistent conflict
                                            // the EA forces a fresh H4 direction read and accepts
                                            // the result even if it means flipping bias direction.
                                            // 2=aggressive 3=balanced(default) 5=conservative
// v3.7.0 — FVG age and proximity filter (Task 09).
// InpFVGMaxBars: reject any FVG older than this many M15 bars. An FVG at
// bar[18] has been available for 4.5 hours — statistical edge decays with
// age. Default 10 = 2.5 hours. 0 = disabled (accepts all bars in lookback).
// InpFVGMaxDepthPct is currently hardcoded at 70% inside SetupEngine.
// Raise to 80 or lower to 60 based on attribution data.
input int    InpFVGMaxBars         = 10;   // Max FVG age in M15 bars (0=off)
// v3.7.0 — Per-setupClass suppression (Task 10).
// Run groupby(['m15SetupClass','regime'])['result'].value_counts() on your
// attribution CSV first. Disable the worst-performing class per regime by
// setting its flag false. All default true for backward compatibility.
input bool   InpEnableFVG           = true;  // Allow FVG setups
input bool   InpEnableDisplacement  = true;  // Allow M15 displacement setups
input bool   InpEnableCompressionBO = true;  // Allow compression breakout setups
input bool   InpEnableEMAPullback   = true;  // Allow EMA pullback setups
// v3.14.2 Fix 2: EMA_Fallback trigger in RANGING regime blocked by default.
// In RANGING the SL is wide (~1.5× ATR), so EMA_Fallback (Score_M1=7, no
// micro-BOS, no displacement, no rejection wick) produces the worst loss
// per trade of any trigger class (avg −$21.15, $148 total in May–Jun 2026).
// Set false (default) to require at least a Rejection-level M1 trigger
// (Score_M1 ≥ 10) in RANGING. True restores previous behaviour.
input bool   InpEMAFallbackInRanging = false; // Allow EMA_Fallback trigger in RANGING regime
input bool   InpRegimeFilterEnabled = true; // Enable regime gating
input bool   InpLiquidityConfirm   = true;  // Require liquidity confirmation
input bool   InpPartialTPEnabled   = true;  // Enable partial close at TP1
input double InpPartialTPPercent   = 50.0;  // % of position closed at TP1
input bool   InpATRTrailEnabled    = true;  // Enable ATR trailing stop

// ── Direction Gate (v3.12.3 — REMOVED) ──────────────────────────
// The 3-signal DirectionGate (H4 EMA + H1 BOS + D1) was removed in
// v3.12.3. Direction now comes directly from H1 BOS (StructureEngine)
// with a targeted H4 pullback filter in ProcessHTF.
// These inputs are retained as stubs to avoid compile errors in any
// dependent code but have no effect on EA behaviour.
input int    InpDGMinVotes         = 2;    // RETIRED — DirectionGate removed in v3.12.3
input double InpDGShortScoreBonus  = 0.0;  // RETIRED — DirectionGate removed in v3.12.3
input int    InpDGRetryBars        = 0;    // RETIRED — DirectionGate removed in v3.12.3

// v3.11.0 — Daily pipeline reset hour (UTC).
// At this hour, if no position is open, the DirectionGate resolved
// direction and vote state are cleared, bias block cycle counters are
// reset, and the pipeline returns to STATE_IDLE for a fresh evaluation.
// H1 swing levels and BOS tracking are preserved if the last confirmed
// BOS is still within InpH1BiasStaleBars — the reset clears gate state
// only, not structural memory.
// If a trade is open at reset time, the reset is deferred until the
// post-trade cooldown completes.
// 0 = midnight UTC (recommended — aligns with new trading day).
// Set to broker server midnight if broker time differs from UTC.
input int    InpDailyResetHour     = 0;    // Daily pipeline reset hour UTC (0=midnight)

// v3.14.2 Fix 4 — Off-Session early-morning bias staleness guard.
// When true (default), the pipeline blocks Off-Session entries before the
// first H1 bar of the new UTC day has been processed by ProcessHTF().
// This prevents carrying a prior-session direction (set hours earlier)
// into the pre-London hours when price context may have shifted overnight.
// Root cause: May 26 02:10, Jun 4 03:02 Off-Session losses both fired with
// a bias established from the previous day's last session close, with no
// H1 BOS reconfirmation on the new day. Set false to restore old behaviour.
input bool   InpOffSessionBiasGuard = true; // Block Off-Session entries before first H1 bar of day

// ── State Logging (v3.10.0) ──────────────────────────────────────
// Controls whether the daily CSV state log is written to disk.
// Enable during backtesting / calibration to capture TRANSITION,
// BLOCK, SETUP_EVAL, TRIGGER_EVAL, and TRADE events for analysis.
// Disable on live accounts to prevent per-day log files from
// accumulating and to avoid overwriting live trade records with
// backtest data. When disabled, NO files are opened or written —
// the logger is a complete no-op.
input bool   InpStateLogEnabled    = false;  // Write daily CSV state log (disable on live)

// ── News ──────────────────────────────────────────────────────────
input int    InpNewsBlockMinutes   = 30;    // Minutes to block around news

// ── Walk-Forward / Anti-Curve-Fit ─────────────────────────────────
input int    InpHoldoutDays        = 90;    // Holdout period (days, 0=disabled)

// ── Live Survivability ────────────────────────────────────────────
// v3.12.4: DD halt threshold is now configurable.
// Previously hardcoded at 15% — confirmed from Jan 7 logs to be
// blocking all trades after just 2 losses on a small account.
// DD-adaptive risk tiers scale proportionally to InpDDHaltPct:
//   Tier 1 (< 1/3 of halt): full risk 1.00×
//   Tier 2 (< 2/3 of halt): reduced  0.75×
//   Tier 3 (< halt):        halved   0.50×
//   At/above halt:          TRADING HALT
// Default 30% gives tiers at 10%, 20%, 30% for a typical account.
// For small accounts or aggressive testing, raise to 40–50%.
// Set 0 to disable the halt entirely (not recommended for live).
input double InpDDHaltPct             = 30.0;  // DD % that triggers trading halt (0=disabled)

// ── DD Recovery Mode (v3.12.9) ────────────────────────────────────
// When enabled, after the initial DD halt fires the EA enters recovery
// mode rather than stopping permanently until reload.
//
// LIFECYCLE (persists only while EA is running — resets on reload):
//   Phase 1 — Normal:
//     Session target = balance at EA load (e.g. $100).
//     DD measured from session target. Halt fires at InpDDHaltPct%.
//
//   Phase 2 — Recovery (fires when DD halt triggers):
//     Secondary balance = current balance at halt (e.g. $70).
//     Trading resumes immediately at normal risk tiers measured from
//     secondary balance. InpDDHaltPct% now applies against secondary
//     (e.g. $70 × 30% = $21 floor → secondary halt at $49).
//     Goal: recover to session target ($100).
//
//   Phase 3a — Session target reached:
//     Balance recovers to or above session target ($100).
//     Trading STOPS. Experts tab logs "Session target reached — reload EA
//     to set new target." No further trades until EA is reloaded.
//
//   Phase 3b — Secondary halt fires:
//     Balance drops InpDDHaltPct% below secondary balance ($70→$49).
//     Trading STOPS. Experts tab logs "DD halt: secondary balance reduced
//     by 30% — reload EA to resume." No further trades until reload.
//
//   On EA reload: fresh start. Session target = current balance.
//
// When disabled (false): original behaviour — halt fires once and
// trades stop until the EA is manually reloaded/restarted.
input bool   InpDDRecoveryMode        = true;  // Enable DD recovery mode (false = halt until reload)
input bool   InpAlertsEnabled         = false; // MT5 push notifications on/off
input int    InpHeartbeatMinutes      = 5;     // Session tick timeout (minutes)
input double InpSpreadSpikeMultiplier = 1.5;   // Spike = entry spread × this (trade management)

// ── Execution Resilience (v4.0) ───────────────────────────────────
input int    InpExecRetries           = 3;     // Order send attempts before rejection
input double InpExecSpreadShockMult   = 2.5;   // Abort execution if spread > avg × this
// v3.6.0 — Entry timing slippage gate.
// If live price has drifted more than this multiple of M1 ATR from the
// trigger bar close by the time the order fires, the trade is aborted.
// 0.5 = conservative (abort if price moved half an M1 ATR).
// 0.0 = disabled (gate off; original behaviour).
input double InpSlippageGateATRMult   = 0.5;   // Trigger-to-fill drift limit (× M1 ATR; 0=off)

// ── Regime Profiles (v3.14.0) ────────────────────────────────────
// Per-regime parameter sets loaded by LoadProfile() in ASE_RegimeProfile.mqh.
// DEPLOY WITH DEFAULTS FIRST — all defaults replicate v3.13.0 global
// Inp* behaviour exactly. Run backtest parity check before tuning.
//
// Tuning guide (after parity confirmed):
//   COMPRESSION threshold: raise to 75 — tighter filter for thin markets
//   RANGING SL:            raise to 1.5 — wider SL for oscillating price
//   MANIPULATION liq:      switch to SWEEP_ONLY via LiquidityEngine routing
//   All others:            data-driven after 20+ trades per regime
//
// HIGH_VOL has no profile — hard block from regime gate.
//
// ── TRENDING profile ─────────────────────────────────────────────
input double InpSL_Trending          = 1.8;   // SL multiplier (ATR ×)  [default: InpATRMultiplierSL_Wide]
input double InpSLCap_Trending       = 15.0;  // SL point cap            [default: InpATRSLCap]
input double InpScore_Trending       = 60.0;  // Min score threshold     [default: InpScoreThreshold]
input int    InpSpread_Trending      = 70;    // Max spread (points)     [default: InpMaxSpread]
input int    InpBiasConf_Trending    = 4;     // Bias confidence bars    [default: InpBiasReEvalBars]
// v3.14.3 — Counter-trend setup quality gates.
// Activate when H4 EMA separation exceeds InpCTEMASepThreshold × H4 ATR,
// indicating a committed H4 trend regardless of H1 regime classification.
// 0.0 = gate always inactive. 0.8 = default. Higher = stricter activation.
input double InpCTEMASepThreshold    = 0.80;  // H4 EMA sep threshold (× H4 ATR) to activate counter-trend gates
input double InpCTDispMultiplier     = 0.85;  // Counter-trend displacement: min body size (× H1 ATR; 0.60=parity)
input double InpCTFVGMinGap          = 0.50;  // Counter-trend FVG: min gap size (× H1 ATR; 0.30=parity)
input double InpCTFVGMaxDepth        = 0.50;  // Counter-trend FVG: max penetration depth (0.70=parity, lower=stricter)
// v3.14.1 — per-regime TP modes. Default=global Inp* value for parity.
// TRENDING recommended: TP1=TP_STRUCTURAL, TP2=TP_STRUCTURAL
// (price has momentum — structural swing targets outperform fixed ATR multiples)
input ENUM_TP_MODE InpTP1Mode_Trending = TP_STRUCTURAL;      // TP1 mode for TRENDING regime
input ENUM_TP_MODE InpTP2Mode_Trending = TP_STRUCTURAL;      // TP2 mode for TRENDING regime

// ── RANGING profile ───────────────────────────────────────────────
input double InpSL_Ranging           = 2.4;   // SL multiplier (ATR ×)
input double InpSLCap_Ranging        = 20;  // SL point cap
input double InpScore_Ranging        = 55.0;  // Min score threshold
input int    InpSpread_Ranging       = 70;    // Max spread (points)
input int    InpBiasConf_Ranging     = 4;     // Bias confidence bars
// RANGING recommended: TP1=TP_ATR, TP2=TP_ATR
// (oscillating price makes structural targets unreliable — ATR is more consistent)
input ENUM_TP_MODE InpTP1Mode_Ranging = TP_HYBRID;       // TP1 mode for RANGING regime
input ENUM_TP_MODE InpTP2Mode_Ranging = TP_HYBRID;       // TP2 mode for RANGING regime

// ── COMPRESSION profile ───────────────────────────────────────────
input double InpSL_Compression       = 1.8;   // SL multiplier (ATR ×)  [default: InpATRMultiplierSL]
input double InpSLCap_Compression    = 8.0;  // SL point cap
// v3.14.2 Fix 3: COMPRESSION threshold raised from 72 → 75 to match
// MANIPULATION strictness. Analysis of May–Jun 2026 live data showed 4
// COMPRESSION losses (May 19 ×2, Jun 12 ×2) with scores 67.3–70.9 firing
// below the 72 gate, and the Jun 12 afternoon cluster (4 consecutive losses)
// all scoring 70.6–76.6 — the 75-point gate blocks the bottom 3 of those 4.
// The COMPRESSION SL is tight (~1× ATR, avg −$8), so raising the gate costs
// little in P&L per false-positive block but eliminates low-confidence entries
// in a regime where price is coiling and breakout direction is uncertain.
input double InpScore_Compression    = 75.0;  // Min score threshold
input int    InpSpread_Compression   = 70;    // Max spread (points)
input int    InpBiasConf_Compression = 8;     // Bias confidence bars
// COMPRESSION recommended: TP1=TP_ATR, TP2=TP_ATR
// (compressed ATR — no reliable swing structure; fixed multiplier is safer)
input ENUM_TP_MODE InpTP1Mode_Compression = TP_ATR;   // TP1 mode for COMPRESSION regime
input ENUM_TP_MODE InpTP2Mode_Compression = TP_ATR;   // TP2 mode for COMPRESSION regime

// ── MANIPULATION profile ──────────────────────────────────────────
input double InpSL_Manipulation      = 1.6;   // SL multiplier (ATR ×)
input double InpSLCap_Manipulation   = 14.0;  // SL point cap
input double InpScore_Manipulation   = 75.0;  // Min score threshold
input int    InpSpread_Manipulation  = 70;    // Max spread (points)
input int    InpBiasConf_Manipulation= 6;     // Bias confidence bars
// MANIPULATION recommended: TP1=TP_STRUCTURAL, TP2=TP_STRUCTURAL
// (sweep reversal targets the swept level — structural is more precise than ATR)
input ENUM_TP_MODE InpTP1Mode_Manipulation = TP_STRUCTURAL;  // TP1 mode for MANIPULATION regime
input ENUM_TP_MODE InpTP2Mode_Manipulation = TP_ATR;  // TP2 mode for MANIPULATION regime

#endif // ASE_CONFIG_MQH
