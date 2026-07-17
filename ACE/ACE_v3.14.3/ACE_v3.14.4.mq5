//+------------------------------------------------------------------+
//|                                                  ACE_v3.14.4.mq5 |
//|                      Adaptive Confluence Engine v3.14.9              |
//|                                                                  |
//|  FIX 12 (v3.14.9) — LIQ routing: MANIPULATION → DetectTrend      |
//|    (ASE_LiquidityEngine.mqh, DetectSweep()):                     |
//|    07.01 log audit: MANIPULATION regime routed to DetectRangingMode|
//|    (DetectHTFPool) which requires equal-high/low pairs. On a fast- |
//|    move trend day the 30-bar lookback had zero such pairs →        |
//|    universal LIQ_FAIL. Root cause: v3.12.1 extension grouped      |
//|    MANIPULATION with RANGING under isRelaxedMode to share the HTF |
//|    pool path — correct for RANGING-day consolidation zones, wrong  |
//|    for MANIPULATION which is a directional trending event. Fix:    |
//|    MANIPULATION now maps to isTrendMode (DetectUnmitigatedSwing),  |
//|    unchanged TRENDING/COMPRESSION path. RANGING retains isRelaxed. |
//|    One-line change; no scoring, gate logic, or candle reads altered.|
//|                                                                  |
//|  FIX 11 (v3.14.9) — EMA distance: direction-of-approach block     |
//|    (ASE_SetupEngine.mqh, CheckEMAPullback()):                    |
//|    07.01 log audit: macroSlope >= 1.4 ("EMA rising hard") blocked  |
//|    all LONG setups regardless of whether price was approaching or  |
//|    receding from the EMA. Root cause: the check was pure magnitude  |
//|    with no direction-of-approach context. The intended block is a  |
//|    missed-entry guard (price already ran away from EMA), but a     |
//|    price pulling back INTO a steep EMA is a valid reversal/pullback |
//|    setup — and was blocked identically. Fix: macroSlope >= 1.4 now |
//|    additionally checks m_prevDistFromEMA (tracked per evaluation). |
//|    If the new dist is closer to EMA than the prior call (approaching|
//|    = true), the block is bypassed. Mirror logic for SHORT. New     |
//|    members: m_prevDistFromEMA, m_prevDistTimestamp (SetupEngine).  |
//|    No other gates changed; distFromEMA/distTooFar checks unchanged. |
//|                                                                  |
//|  FIX 10 (v3.14.9) — H4 hybrid bias scoring                        |
//|    (ASE_StateMachine.mqh CalcH4HybridScore(), ASE_ScoringEngine): |
//|    H4 EMA cross is a lagging indicator on fast-move/reversal days. |
//|    The prior architecture sourced h4Bias directly from             |
//|    StructureEngine res.score (H1 BOS quality, max 30) — meaning   |
//|    H4 alignment dominated 28.5% of the raw score. Fix replaces    |
//|    this with CalcH4HybridScore() (new private method in            |
//|    StateMachine), a [0,10] signal built from: (1) H4 direction     |
//|    alignment vs trade direction (base: align=7, oppose=3, none=5); |
//|    (2) counter-body check: last closed H4 bar counter-body ≤ 30%  |
//|    of prior trade-direction body → +3 (trend-structure intact);   |
//|    (3) EMA spread convergence: if H4 EMA20/50 converging AGAINST  |
//|    trade direction → −2 (early reversal signal). Score clamped     |
//|    [0,10]. ASE_SCORE_RAW_MAX reduced 105→85 to preserve score      |
//|    normalisation proportionality (h4Bias raw ceiling 30→10).      |
//|    Two new H4 EMA handles (m_h4FastHybridHandle, m_h4SlowHybridHandle)|
//|    added to StateMachine Initialize()/Deinitialize() using existing|
//|    InpH4FastEMA=20 / InpH4SlowEMA=50 config params. No thresholds |
//|    changed; all existing gates (pullback filter, regime, setup,    |
//|    trigger, liquidity) unchanged.                                  |
//|                                                                  |
//|  v3.14.3 — Counter-trend FVG gate added (H4 EMA sep / H4 ATR),   |
//|    instrumented with a temporary CANARY debug print.             |
//|    Base: v3.14.1 (all prior fixes retained)                      |
//|                                                                  |
//|  FIX 9 (v3.14.8) — RANGING liquidity pool: wider zone tolerance   |
//|    (ASE_LiquidityEngine.mqh, DetectHTFPool() / DetectRangingMode)|
//|    06.30 log audit: 12 LIQ_FAILs in RANGING, Score_Liq=0.0 all   |
//|    day, 0 trades fired. Root cause: DetectHTFPool() required two  |
//|    M15 swing lows within 0.15×ATR (~0.75 pt at ATR=5). XAUUSD    |
//|    S/R zones in RANGING manifest as 1-4 pt wide bands, not exact  |
//|    double-bottom levels — the 16:00 4009-4013 zone (tested 3x)   |
//|    had minimum pairwise low separation of ~2 pts, far exceeding   |
//|    the 0.75-pt cap. New constant LIQ_HTF_EQ_TOLERANCE_RANGING=    |
//|    0.40 (≈2.0 pt at ATR=5) is passed via optional tolOverride     |
//|    param only from DetectRangingMode(); SWEEP and TREND mode call  |
//|    sites retain 0.15×ATR unchanged. No scoring, gate logic, or    |
//|    entry decision changed — only the equal-level definition in     |
//|    RANGING is widened to match how zones form on XAUUSD.          |
//|                                                                  |
//|  FIX 8 (v3.14.7) — Reinit-survival persistence for cooldown +    |
//|    open-trade context (ASE_StateMachine.mqh):                    |
//|    06.29 log audit found a trade close at 21:53:32 with          |
//|    Direction=NONE and no TRADE/result row ever written, plus a   |
//|    cooldown that started the same moment but lasted 34 seconds   |
//|    instead of its configured window. Root cause: Initialize()    |
//|    runs on every reinit (recompile, input change, reattach) and  |
//|    unconditionally resets m_ctx/m_state; a full reload also re-  |
//|    runs the constructor, zeroing m_cooldownEnd and the entry-time|
//|    snapshot fields. If either happens while a trade is open or a |
//|    cooldown is running, that state was silently lost. Fix now    |
//|    persists m_cooldownEnd and the entry snapshot (direction,     |
//|    entry, SL/TP, open time, score/RR/ATR) to GlobalVariables on  |
//|    trade-open and cooldown-start, restoring them in Initialize() |
//|    — guarded by HasOpenPosition() for the trade snapshot and an  |
//|    expiry check for cooldown, so nothing stale is ever restored. |
//|    Pure bookkeeping — no change to scoring, gating, or entry/    |
//|    execution decision logic; trade-firing behaviour unaffected.  |
//|                                                                  |
//|  FIX 7 (v3.14.6) — NONE-bias breakout fallback in StructureEngine|
//|    (ASE_StructureEngine.mqh, Evaluate()):                        |
//|    The existing lookback-high/low fallback only fired to RE-     |
//|    confirm an already-held LONG/SHORT bias once the fractal      |
//|    pivot scan lost its reference mid-trend. It did nothing when  |
//|    bias was flat (DIR_NONE) — confirmed via 06.26 log: H1        |
//|    swingH stuck at 0.00000 for 13 straight hours, zero           |
//|    TRIGGER_EVALs all session, despite a clean 4027->4095 rally   |
//|    on the chart. No H1 retracement was ever long/deep enough to  |
//|    confirm a fractal pivot before the move itself topped out, so |
//|    the EA had no path to ever flip LONG. Fallback now also       |
//|    applies when bias is DIR_NONE, regardless of reconfirm state, |
//|    using the same highest-high/lowest-low-in-lookback reference. |
//|    Scored identically to a real pivot BOS — no downstream gates  |
//|    changed, so composite score threshold/liquidity/setup checks  |
//|    still filter quality.                                         |
//|                                                                  |
//|  FIX 6 (v3.14.5) — Direction-aware entry-timing slippage gate:   |
//|    The v3.6.0 stale-trigger-abort gate compared unsigned drift   |
//|    against 0.5x M1ATR, aborting on fast FAVORABLE continuation   |
//|    exactly the same as on adverse/stale drift. Audit of three   |
//|    live sessions (06.23, 06.25) found this gate killed every     |
//|    setup that ever cleared the scoring threshold that day,      |
//|    including the 06.25 16:16 LONG signal that would have caught |
//|    the 15:00-18:00 rally — aborted one minute later on FAVORABLE|
//|    drift (2.46 pts > 2.10 pt cap). Gate now uses signed,         |
//|    direction-relative drift and only aborts on adverse drift     |
//|    beyond the cap; favorable drift no longer aborts. Downstream  |
//|    structural levels are already recomputed off live price      |
//|    regardless, so SL/TP remain correct either way.                |
//|    (ASE_StateMachine.mqh, ProcessExecution())                    |
//|                                                                  |
//|  FIX 5 (v3.14.4) — Conflict-audit cleanup:                       |
//|    - MANIPULATION swing-fallback scoring bug fixed: res.score    |
//|      was left at 0.0 after a valid direction was resolved via    |
//|      swing fallback, zeroing 30/105 raw scoring points (h4Bias)  |
//|      and making the 75-pt MANIPULATION threshold unreachable.    |
//|      Now assigns a reduced-confidence score of 12.0.             |
//|      (ASE_StateMachine.mqh, ProcessHTF())                        |
//|    - InpMagicNumber bumped 203142 → 203143 to avoid colliding    |
//|      with prior-version open positions/history on the account.   |
//|    - Removed dead countertrend-SHORT score-bonus branch in       |
//|      ProcessTrigger(): m_ctx.isCountertrendShortException is     |
//|      hardcoded false with no other writer anywhere in the repo,  |
//|      so the InpDGShortScoreBonus boost path could never execute. |
//|    - Removed the v3.14.3 CANARY debug print from                 |
//|      ASE_SetupEngine.mqh::CheckFVG() (compile verification done).|
//|                                                                  |
//|  FIX 1 — Threshold logging (StateLogger):                        |
//|    Threshold/Param_ScoreThreshold CSV columns now log the        |
//|    regime-specific effective threshold (m_profile.minScore-      |
//|    Threshold) instead of always writing InpScoreThreshold.       |
//|    LogTriggerEval() and LogTrade() accept effectiveThreshold     |
//|    as an optional parameter; all call sites updated.             |
//|                                                                  |
//|  FIX 2 — EMA_Fallback blocked in RANGING (InpEMAFallbackIn-     |
//|    Ranging, default=false):                                      |
//|    EMA_Fallback trigger (Score_M1=7, no structural confirm)      |
//|    produced 7 losses @ avg -$21.15 and $148 total in RANGING     |
//|    where the SL is wide (~1.5x ATR). Gate added in ProcessTrigger|
//|    after trigger class is resolved. Set true to restore old      |
//|    behaviour. All other regimes unaffected.                      |
//|                                                                  |
//|  FIX 3 — COMPRESSION score threshold raised 72 → 75             |
//|    (InpScore_Compression, default=75.0):                         |
//|    4 COMPRESSION losses fired below the prior 72-pt gate         |
//|    (scores 67.3-70.9). Jun 12 afternoon cluster (4 consecutive   |
//|    losses) all had scores 70.6-76.6; raising to 75 blocks the   |
//|    bottom 3 of those 4. COMPRESSION SL is tight (~1x ATR, avg   |
//|    -$8), so the gate tightens without significant loss of        |
//|    profitable opportunity.                                       |
//|                                                                  |
//|  FIX 4 — Off-Session bias staleness guard                        |
//|    (InpOffSessionBiasGuard, default=true):                       |
//|    Blocks Off-Session entries before the first H1 bar of the     |
//|    new UTC day has been processed by ProcessHTF(). Prevents      |
//|    carrying a prior-session direction into pre-London hours      |
//|    with no H1 BOS reconfirmation. m_lastH1EvalDate stamped on    |
//|    each successful H1 regime evaluation; gate checks vs today.   |
//|    Root cause: May 26 02:10 (bias=NONE from prior day) and       |
//|    Jun 4 03:02 (prior-day SHORT carried into new day).           |
//+------------------------------------------------------------------+
#property copyright "ASE v3 — Adaptive Signal Engine"
#property link      ""
#property version   "3.14.9"

#ifndef CALENDAR_IMPACT_HIGH
   #define CALENDAR_IMPACT_HIGH 3
#endif

#include "Core/ASE_StateMachine.mqh"

CASE_StateMachine g_stateMachine;

int OnInit()
{
   Print("══════════════════════════════════════════");
   Print("  ASE v3.14.9 — H4 hybrid scoring + EMA direction-of-approach + MANIPULATION LIQ routing fix");
   Print("  Fix1=ThresholdLog | Fix2=NoEMAFallbackRanging | Fix3=Compression75 | Fix4=OffSessionGuard | Fix5=AuditCleanup | Fix6=DirectionalSlippageGate | Fix7=NoneBiasFallback | Fix8=ReinitPersistence | Fix9=RangingZoneTolerance | Fix10=H4HybridScore | Fix11=EMAApproach | Fix12=ManipulationLIQRouting");
   Print("  EMAFallbackRanging: ", InpEMAFallbackInRanging ? "ON" : "OFF",
         " | OffSessionGuard: ", InpOffSessionBiasGuard ? "ON" : "OFF");
   Print("  RecoveryMode: ", InpDDRecoveryMode ? "ON" : "OFF",
         " | DDHalt: ", DoubleToString(InpDDHaltPct, 0), "%");
   Print("  SL=", DoubleToString(InpATRMultiplierSL,1),
         "xATR | TP1=", DoubleToString(InpATRMultiplierTP1,1),
         "xATR | Partial=", InpPartialTPEnabled ? "ON" : "OFF");
   Print("  Magic: ", IntegerToString(InpMagicNumber));
   Print("══════════════════════════════════════════");
   if(!g_stateMachine.Initialize()) { Print("[ASE] INIT FAILED"); return INIT_FAILED; }
   g_stateMachine.ScanUpcomingNews();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { g_stateMachine.Deinitialize(); }
void OnTick()                   { g_stateMachine.Update(); }
double OnTester()               { return g_stateMachine.GetFitnessScore(); }

void OnCalendarEvent(const MqlCalendarEvent   &event[],
                     const MqlCalendarValue   &value[],
                     const MqlCalendarCountry &country[])
{
   for(int i = 0; i < ArraySize(value); i++)
      if(value[i].impact_type == CALENDAR_IMPACT_HIGH &&
         value[i].time > TimeCurrent())
         g_stateMachine.NotifyNewsEvent(value[i].time);
}
