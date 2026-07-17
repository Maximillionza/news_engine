#ifndef ASE_LIQUIDITYENGINE_MQH
#define ASE_LIQUIDITYENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
#include "../Models/ASE_Enums.mqh"
#include "ASE_RegimeProfile.mqh"   // v3.14.1 — ENUM_LIQ_MODE for DetectSweep()
//+------------------------------------------------------------------+
//| ASE v4.0 — Liquidity Engine                                      |
//|                                                                  |
//| v3 (original):                                                   |
//|   Two-level detection: HTF equal-highs/lows pool + M1 micro      |
//|   sweep. Designed for ICT sweep-and-reverse setups in ranges.    |
//|                                                                  |
//| v4.0 fixes (investigation 2026.05.26):                           |
//|                                                                  |
//|   ROOT CAUSE: in trending/compression regimes, the HTF pool      |
//|   detector requires equal highs (for SHORT) — a pattern that     |
//|   does not occur when the market is making lower highs.  The M1  |
//|   micro sweep required bar[1] to spike ABOVE recent swing highs  |
//|   and close back — also impossible in a downtrend.  Result: the  |
//|   liquidity gate blocked every trade on trending days.           |
//|                                                                  |
//|   FIX A — Regime-aware DetectSweep():                            |
//|     SWEEP regime  (MANIPULATION, EXPANSION):                     |
//|       Original logic unchanged — requires equal highs/lows pool  |
//|       + M1 spike-and-close sweep.                                |
//|     TREND regime (TRENDING, COMPRESSION):                        |
//|       HTF: any unmitigated swing high/low in last 30 bars counts |
//|         as a valid pool (no equal-level requirement).            |
//|       M1:  rejection wick confirmation — upper wick > 40% of bar |
//|         range with bearish close (SHORT), or lower wick > 40%    |
//|         with bullish close (LONG). Represents micro rejection at  |
//|         the current level without requiring a new swing extreme.  |
//|                                                                  |
//|   FIX B — HTF pool now passes (score=8) in trend regime:         |
//|     In SWEEP mode: HTFPool alone → passed=false (await sweep)    |
//|     In TREND mode: HTFPool alone → passed=true  (valid entry)    |
//|     Both modes:  HTF+Sweep → passed=true, score=15 (full conf.)  |
//|                                                                  |
//|   Scoring:                                                        |
//|     HTF pool + confirmation : 15.0  (primary — unchanged)        |
//|     HTF pool only (trend)   :  8.0  (relaxed — trend entry)      |
//|     Rejection wick only     :  5.0  (micro — no HTF context)     |
//|     Neither                 :  0.0                               |
//|                                                                  |
//|   liquidityType values:                                           |
//|     "HTF+Sweep"    — equal-highs pool + M1 spike sweep           |
//|     "HTF+Reject"   — unmitigated swing + M1 rejection wick       |
//|     "HTFPool"      — pool identified only (sweep mode)           |
//|     "MicroSweep"   — M1 spike sweep, no HTF context              |
//|     "TrendReject"  — M1 rejection wick only                      |
//|     "None"         — no confluence                               |
//+------------------------------------------------------------------+

#define LIQ_HTF_LOOKBACK    30
#define LIQ_HTF_PIVOT_BARS   3
#define LIQ_HTF_EQ_TOUCHES   2
#define LIQ_HTF_EQ_TOLERANCE         0.15   // ATR fraction — equal level tolerance (sweep/trend mode)
#define LIQ_HTF_EQ_TOLERANCE_RANGING 0.40   // ATR fraction — wider zone tolerance for RANGING pools
                                            //   0.15 × ATR ≈ 0.75 pt at ATR=5 (too tight for XAUUSD zones)
                                            //   0.40 × ATR ≈ 2.00 pt at ATR=5 (catches real S/R zones)
#define LIQ_M1_LOOKBACK      6
#define LIQ_REJECT_WICK_MIN  0.40   // minimum wick/range ratio for rejection candle

class CASE_LiquidityEngine
{
private:
   int    m_atrHandle;
   string m_lastLiqType;

public:
   CASE_LiquidityEngine() : m_atrHandle(INVALID_HANDLE), m_lastLiqType("None") {}

   bool Initialize()
   {
      m_atrHandle = iATR(_Symbol, PERIOD_M15, InpATRPeriod);
      return (m_atrHandle != INVALID_HANDLE);
   }

   void Deinitialize()
   {
      if(m_atrHandle != INVALID_HANDLE) IndicatorRelease(m_atrHandle);
   }

   string GetLiquidityType() const { return m_lastLiqType; }

   //------------------------------------------------------------------
   // v3.4.2 — Fix 4: MANIPULATION regime direction fallback.
   //
   // Called from ProcessHTF() when both the pivot scan and EMA fallback
   // return DIR_NONE during MANIPULATION regime.  Uses the nearest
   // unmitigated M15 swing level to derive a tentative direction:
   //   SHORT — unmitigated swing HIGH above current price
   //   LONG  — unmitigated swing LOW  below current price
   //
   // Tries SHORT first (swing high above price), then LONG (swing low
   // below price). Returns the first direction found. Returns DIR_NONE
   // if no unmitigated swing exists in either direction within lookback.
   //
   // The result is passed through the Fix 3 confidence gate in
   // ProcessHTF() before the pipeline advances to STATE_WAIT_SETUP,
   // so a stale or momentum-conflicting swing is still blocked there.
   //------------------------------------------------------------------
   // v3.10.0 fix: original code tried DIR_SHORT unconditionally first,
   // causing SHORT trades to be placed in LONG markets whenever the
   // MANIPULATION fallback fired. Replaced with bias-aware priority:
   // the direction matching the caller s prior H1 bias is tried first.
   ENUM_TRADE_DIRECTION GetDirectionFromSwing(double               atrVal,
                                              string              &reason,
                                              ENUM_TRADE_DIRECTION biasPrior = DIR_NONE)
   {
      double poolLevel = 0.0;

      ENUM_TRADE_DIRECTION first  = (biasPrior == DIR_LONG) ? DIR_LONG : DIR_SHORT;
      ENUM_TRADE_DIRECTION second = (first == DIR_LONG) ? DIR_SHORT : DIR_LONG;

      if(DetectUnmitigatedSwing(first,  atrVal, poolLevel, reason)) return first;
      if(DetectUnmitigatedSwing(second, atrVal, poolLevel, reason)) return second;

      reason = "No unmitigated swing found in either direction";
      return DIR_NONE;
   }

   //------------------------------------------------------------------
   // Primary entry — regime-aware with profile liq mode override.
   // v3.14.1: accepts ENUM_LIQ_MODE from the active regime profile.
   //   LIQ_STANDARD   — regime-based routing (existing behaviour, default)
   //   LIQ_TIGHT      — forces TREND mode regardless of regime
   //   LIQ_SWEEP_ONLY — forces SWEEP mode (equal-highs/lows + M1 spike)
   //
   // Regime is passed from m_ctx.regimeAtEntry.regime so no extra
   // GetState() call is needed at the call site.
   //------------------------------------------------------------------
   ValidationResult DetectSweep(ENUM_TRADE_DIRECTION direction,
                                 ENUM_MARKET_REGIME   regime  = REGIME_COMPRESSION,
                                 ENUM_LIQ_MODE        liqMode = LIQ_STANDARD)
   {
      ValidationResult r;
      r.passed = false;
      r.reason = "No liquidity confluence";
      r.score  = 0.0;
      m_lastLiqType = "None";

      if(direction == DIR_NONE) return r;

      double atrVal = GetATR();

      // v3.14.1 — profile liq mode overrides regime-based routing when set.
      // LIQ_STANDARD falls through to the original regime routing.
      bool isTrendMode   = false;
      bool isRelaxedMode = false;
      string modeLabel;

      if(liqMode == LIQ_TIGHT)
      {
         isTrendMode = true;
         modeLabel   = "TREND(forced)";
      }
      else if(liqMode == LIQ_SWEEP_ONLY)
      {
         // isTrendMode and isRelaxedMode both false → falls through to DetectSweepMode
         modeLabel = "SWEEP(forced)";
      }
      else
      {
         // LIQ_STANDARD — original regime-based routing (unchanged from v3.12)
         // v3.14.9 Fix 12: MANIPULATION re-routed to TREND (DetectUnmitigatedSwing).
         // MANIPULATION is an aggressive trending event — it does not produce
         // equal-high/low pools. Routing it to RELAXED (DetectHTFPool) forced an
         // equal-level search on fast-move days where none exist → universal LIQ_FAIL.
         // DetectUnmitigatedSwing finds any prior unmitigated swing, a far easier bar
         // for trend/manipulation days to clear. RANGING keeps DetectHTFPool (pools
         // genuinely form in consolidation). Prior comment from v3.12.1 kept below:
         // [v3.12.0 Fix D / v3.12.1: 11/30 trigger evals found an HTF pool in
         //  MANIPULATION — those were RANGING-day logs where the routing was correct.
         //  MANIPULATION-specific days show LIQ_FAIL because DetectHTFPool finds
         //  no equal levels on a one-directional fast-move day — Fix 12 corrects this.]
         isTrendMode   = (regime == REGIME_TRENDING    ||
                          regime == REGIME_COMPRESSION ||
                          regime == REGIME_MANIPULATION);
         isRelaxedMode = (regime == REGIME_RANGING);
         modeLabel = isTrendMode ? "TREND" : (isRelaxedMode ? "RELAXED" : "SWEEP");
      }

      string dirLabel = (direction == DIR_SHORT) ? "SHORT" : "LONG";
      Print(StringFormat(
         "[LIQ] Start | dir=%s regime=%d mode=%s ATR=%.5f",
         dirLabel, (int)regime, modeLabel, atrVal));

      ValidationResult res;
      if(isTrendMode)
         res = DetectTrend(direction, atrVal);
      else if(isRelaxedMode)
         res = DetectRangingMode(direction, atrVal);
      else
         res = DetectSweepMode(direction, atrVal);

      Print(StringFormat(
         "[LIQ] Result | passed=%s score=%.1f type=%s reason=%s",
         res.passed ? "YES" : "NO", res.score,
         m_lastLiqType, res.reason));
      return res;
   }

private:
   //==================================================================
   // SWEEP MODE (original logic — MANIPULATION / EXPANSION / unknown)
   // Requires equal-highs/lows pool + M1 spike-and-close sweep.
   //==================================================================
   ValidationResult DetectSweepMode(ENUM_TRADE_DIRECTION direction, double atrVal)
   {
      ValidationResult r;
      r.passed = false;
      r.reason = "No liquidity confluence";
      r.score  = 0.0;
      m_lastLiqType = "None";

      bool   htfPool  = false;
      double poolLevel = 0.0;
      string htfReason = "";
      htfPool = DetectHTFPool(direction, atrVal, poolLevel, htfReason);

      bool   microSweep = false;
      string sweepReason = "";
      microSweep = DetectMicroSweep(direction, sweepReason);

      // v3.4.7 diagnostic: log each sub-check independently
      Print(StringFormat(
         "[LIQ][SWEEP] HTFPool=%s poolLevel=%.5f htfReason=%s",
         htfPool ? "YES" : "NO", poolLevel, htfReason));
      Print(StringFormat(
         "[LIQ][SWEEP] MicroSweep=%s sweepReason=%s",
         microSweep ? "YES" : "NO", sweepReason));

      if(htfPool && microSweep)
      {
         r.passed = true;
         r.score  = 15.0;
         r.reason = StringFormat("HTF pool %.5f + M1 sweep | %s | %s",
                                 poolLevel, htfReason, sweepReason);
         m_lastLiqType = "HTF+Sweep";
      }
      else if(htfPool)
      {
         r.passed = false;
         r.score  = 8.0;
         r.reason = StringFormat("HTF pool %.5f (awaiting M1 sweep) | %s",
                                 poolLevel, htfReason);
         m_lastLiqType = "HTFPool";
      }
      else if(microSweep)
      {
         r.passed = true;
         r.score  = 5.0;
         r.reason = "M1 micro sweep (no HTF context) | " + sweepReason;
         m_lastLiqType = "MicroSweep";
      }

      return r;
   }

   //==================================================================
   // RANGING MODE (v3.12.0 Fix D — REGIME_RANGING)
   // Confirmed from Feb 5 logs: 15/17 trigger evals failed LIQ_FAIL
   // in RANGING/MANIPULATION regime even with Score_M15=25 (max setup
   // quality). RANGING markets rarely form equal-highs/lows pools with
   // M1 spike sweeps — the SWEEP mode requirement is too strict.
   //
   // Relaxed model for RANGING:
   //   HTFPool alone (S/R proximity without M1 sweep) → passed=true score=8
   //   MicroSweep alone                               → passed=true score=5
   //   HTFPool + MicroSweep                           → passed=true score=12
   //   Neither                                        → passed=false score=0
   //
   // Rationale: in a ranging market, price oscillates between S/R levels.
   // A touch of a known S/R pool without a full spike sweep is a valid
   // reversal signal — the pool itself IS the liquidity event.
   // This matches ICT fair value logic for ranging/consolidation sessions.
   //==================================================================
   ValidationResult DetectRangingMode(ENUM_TRADE_DIRECTION direction, double atrVal)
   {
      ValidationResult r;
      r.passed = false;
      r.reason = "No liquidity confluence";
      r.score  = 0.0;
      m_lastLiqType = "None";

      bool   htfPool   = false;
      double poolLevel = 0.0;
      string htfReason = "";
      htfPool = DetectHTFPool(direction, atrVal, poolLevel, htfReason, LIQ_HTF_EQ_TOLERANCE_RANGING); // v3.14.8

      bool   microSweep  = false;
      string sweepReason = "";
      microSweep = DetectMicroSweep(direction, sweepReason);

      Print(StringFormat(
         "[LIQ][RANGING] HTFPool=%s poolLevel=%.5f | MicroSweep=%s | tol=%.2f×ATR(%.2f×ATR swept)",
         htfPool ? "YES" : "NO", poolLevel, microSweep ? "YES" : "NO",
         LIQ_HTF_EQ_TOLERANCE_RANGING, LIQ_HTF_EQ_TOLERANCE));

      if(htfPool && microSweep)
      {
         r.passed = true;
         r.score  = 12.0;   // slightly below SWEEP mode (15) — no full spike
         r.reason = StringFormat("RANGING: HTF pool %.5f + micro sweep | %s | %s",
                                 poolLevel, htfReason, sweepReason);
         m_lastLiqType = "Ranging:HTF+Sweep";
      }
      else if(htfPool)
      {
         // Key relaxation vs SWEEP mode: HTFPool alone is sufficient in RANGING.
         // Price at a known S/R level is the liquidity context without needing
         // a full M1 spike-and-close confirmation.
         r.passed = true;
         r.score  = 8.0;
         r.reason = StringFormat("RANGING: HTF pool %.5f (S/R touch) | %s",
                                 poolLevel, htfReason);
         m_lastLiqType = "Ranging:HTFPool";
      }
      else if(microSweep)
      {
         r.passed = true;
         r.score  = 5.0;
         r.reason = "RANGING: M1 micro sweep (no pool) | " + sweepReason;
         m_lastLiqType = "Ranging:MicroSweep";
      }

      return r;
   }

   //==================================================================
   // TREND MODE (v4.0 — TRENDING / COMPRESSION)
   //
   // HTF: any unmitigated swing high (SHORT) or swing low (LONG) in
   //      the last 30 M15 bars counts as a valid pool — no equal-
   //      level requirement because trending markets make sequential
   //      new highs/lows rather than retesting the same level.
   //
   // M1:  rejection wick confirmation — price pushes against the
   //      trend direction briefly then closes back. For SHORT: upper
   //      wick > LIQ_REJECT_WICK_MIN × bar range with close in lower
   //      half. This represents micro liquidity taken before the
   //      continuation move.
   //
   // Gate logic:
   //   HTF pool + M1 rejection : passed=true,  score=15 (full)
   //   HTF pool alone           : passed=true,  score=8  (trend entry)
   //   M1 rejection alone       : passed=true,  score=5  (micro only)
   //   Neither                  : passed=false, score=0
   //==================================================================
   ValidationResult DetectTrend(ENUM_TRADE_DIRECTION direction, double atrVal)
   {
      ValidationResult r;
      r.passed = false;
      r.reason = "No liquidity confluence";
      r.score  = 0.0;
      m_lastLiqType = "None";

      bool   htfPool   = false;
      double poolLevel = 0.0;
      string htfReason = "";
      htfPool = DetectUnmitigatedSwing(direction, atrVal, poolLevel, htfReason);

      bool   rejection  = false;
      string rejReason  = "";
      rejection = DetectRejectionWick(direction, rejReason);

      // v3.4.7 diagnostic: log each sub-check independently
      Print(StringFormat(
         "[LIQ][TREND] HTFPool=%s poolLevel=%.5f htfReason=%s",
         htfPool ? "YES" : "NO", poolLevel, htfReason));
      Print(StringFormat(
         "[LIQ][TREND] Rejection=%s rejReason=%s",
         rejection ? "YES" : "NO", rejReason));

      if(htfPool && rejection)
      {
         r.passed = true;
         r.score  = 15.0;
         r.reason = StringFormat("Trend pool %.5f + M1 reject | %s | %s",
                                 poolLevel, htfReason, rejReason);
         m_lastLiqType = "HTF+Reject";
      }
      else if(htfPool)
      {
         r.passed = true;
         r.score  = 8.0;
         r.reason = StringFormat("Trend pool %.5f | %s", poolLevel, htfReason);
         m_lastLiqType = "HTFPool";
      }
      else if(rejection)
      {
         r.passed = true;
         r.score  = 5.0;
         r.reason = "M1 rejection wick (no HTF pool) | " + rejReason;
         m_lastLiqType = "TrendReject";
      }

      return r;
   }

   //==================================================================
   // DetectUnmitigatedSwing — TREND MODE HTF detection
   //
   // For SHORT: find the most recent M15 swing high in the last 30
   //   bars that price has not since traded above (unmitigated).
   //   This is the resting buy-stop liquidity above that the market
   //   will eventually target in a downtrend continuation.
   //
   // For LONG: symmetric — most recent unmitigated swing low.
   //
   // "Unmitigated" = no subsequent bar's close has exceeded the swing
   //   level from the same side (close > swingHigh for SHORT).
   //==================================================================
   bool DetectUnmitigatedSwing(ENUM_TRADE_DIRECTION direction, double atrVal,
                                double &poolLevel, string &reason)
   {
      poolLevel = 0.0;
      reason    = "";

      double hi[], lo[], cl[];
      ArraySetAsSeries(hi, true);
      ArraySetAsSeries(lo, true);
      ArraySetAsSeries(cl, true);

      int needed = LIQ_HTF_LOOKBACK + LIQ_HTF_PIVOT_BARS + 1;
      if(CopyHigh( _Symbol, PERIOD_M15, 0, needed, hi) < needed) return false;
      if(CopyLow(  _Symbol, PERIOD_M15, 0, needed, lo) < needed) return false;
      if(CopyClose(_Symbol, PERIOD_M15, 0, needed, cl) < needed) return false;

      if(direction == DIR_SHORT)
      {
         // Find the most recent (smallest index) swing high that
         // is still above current price (unmitigated)
         double currentPrice = cl[0];

         for(int i = LIQ_HTF_PIVOT_BARS; i < LIQ_HTF_LOOKBACK; i++)
         {
            if(!IsSwingHigh(hi, i, LIQ_HTF_PIVOT_BARS)) continue;

            double swingHi = hi[i];
            if(swingHi <= currentPrice) continue;  // already traded through

            // Verify no close above this swing high since it formed
            bool mitigated = false;
            for(int k = 1; k < i; k++)
            {
               if(cl[k] > swingHi) { mitigated = true; break; }
            }
            if(mitigated) continue;

            poolLevel = swingHi;
            double dist = (swingHi - currentPrice) / MathMax(atrVal, _Point);
            reason = StringFormat("Unmitigated swing high %.5f | %d bars ago | dist=%.2fATR",
                                  swingHi, i, dist);
            return true;
         }
      }
      // v3.4.7 diagnostic: no qualifying swing found
      if(direction == DIR_SHORT)
         Print("[LIQ][SWING] SHORT: no unmitigated swing high found in last ",
               LIQ_HTF_LOOKBACK, " bars above price=", cl[0]);
      else if(direction == DIR_LONG)
      {
         double currentPrice = cl[0];

         for(int i = LIQ_HTF_PIVOT_BARS; i < LIQ_HTF_LOOKBACK; i++)
         {
            if(!IsSwingLow(lo, i, LIQ_HTF_PIVOT_BARS)) continue;

            double swingLo = lo[i];
            if(swingLo >= currentPrice) continue;

            bool mitigated = false;
            for(int k = 1; k < i; k++)
            {
               if(cl[k] < swingLo) { mitigated = true; break; }
            }
            if(mitigated) continue;

            poolLevel = swingLo;
            double dist = (currentPrice - swingLo) / MathMax(atrVal, _Point);
            reason = StringFormat("Unmitigated swing low %.5f | %d bars ago | dist=%.2fATR",
                                  swingLo, i, dist);
            return true;
         }
      }

      return false;
   }

   //==================================================================
   // DetectRejectionWick — TREND MODE M1 confirmation
   //
   // For SHORT: most recent completed M1 bar has an upper wick that
   //   exceeds LIQ_REJECT_WICK_MIN × bar total range, AND the close
   //   is in the lower half of the bar. This is a bearish rejection
   //   candle — price tried to push up, liquidity was absorbed, close
   //   returned bearish.
   //
   // For LONG: symmetric — lower wick > threshold, close upper half.
   //==================================================================
   bool DetectRejectionWick(ENUM_TRADE_DIRECTION direction, string &reason)
   {
      reason = "";

      double hi[], lo[], op[], cl[];
      ArraySetAsSeries(hi, true);
      ArraySetAsSeries(lo, true);
      ArraySetAsSeries(op, true);
      ArraySetAsSeries(cl, true);

      if(CopyHigh( _Symbol, PERIOD_M1, 0, 3, hi) < 3) return false;
      if(CopyLow(  _Symbol, PERIOD_M1, 0, 3, lo) < 3) return false;
      if(CopyOpen( _Symbol, PERIOD_M1, 0, 3, op) < 3) return false;
      if(CopyClose(_Symbol, PERIOD_M1, 0, 3, cl) < 3) return false;

      // Use bar[1] — last fully closed M1 bar
      double barHigh  = hi[1];
      double barLow   = lo[1];
      double barOpen  = op[1];
      double barClose = cl[1];
      double barRange = barHigh - barLow;

      if(barRange < _Point * 5) return false;  // avoid doji / flat bars

      double barMid = (barHigh + barLow) / 2.0;

      if(direction == DIR_SHORT)
      {
         double upperWick = barHigh - MathMax(barOpen, barClose);
         double wickRatio = upperWick / barRange;

         bool strongWick  = wickRatio >= LIQ_REJECT_WICK_MIN;
         bool bearishClose = barClose < barMid;

         if(strongWick && bearishClose)
         {
            reason = StringFormat(
               "M1 bearish rejection: wick=%.1f%% range | high=%.5f close=%.5f",
               wickRatio * 100, barHigh, barClose);
            return true;
         }
      }
      else if(direction == DIR_LONG)
      {
         double lowerWick = MathMin(barOpen, barClose) - barLow;
         double wickRatio = lowerWick / barRange;

         bool strongWick   = wickRatio >= LIQ_REJECT_WICK_MIN;
         bool bullishClose = barClose > barMid;

         if(strongWick && bullishClose)
         {
            reason = StringFormat(
               "M1 bullish rejection: wick=%.1f%% range | low=%.5f close=%.5f",
               wickRatio * 100, barLow, barClose);
            return true;
         }
      }

      return false;
   }

   //==================================================================
   // SWEEP MODE helpers (original — unchanged)
   //==================================================================
   // v3.14.8 — tolOverride: pass LIQ_HTF_EQ_TOLERANCE_RANGING from DetectRangingMode()
   //   to widen the equal-level tolerance for zone-based S/R in RANGING.
   //   Default 0.0 → uses LIQ_HTF_EQ_TOLERANCE (sweep/trend mode unchanged).
   bool DetectHTFPool(ENUM_TRADE_DIRECTION direction, double atrVal,
                      double &poolLevel, string &reason,
                      double tolOverride = 0.0)
   {
      poolLevel = 0.0;
      reason    = "";

      double hi[], lo[];
      ArraySetAsSeries(hi, true);
      ArraySetAsSeries(lo, true);

      int needed = LIQ_HTF_LOOKBACK + LIQ_HTF_PIVOT_BARS + 1;
      if(CopyHigh(_Symbol, PERIOD_M15, 0, needed, hi) < needed) return false;
      if(CopyLow( _Symbol, PERIOD_M15, 0, needed, lo) < needed) return false;

      double tolFrac = (tolOverride > 0.0) ? tolOverride : LIQ_HTF_EQ_TOLERANCE;
      double tol     = (atrVal > 0) ? atrVal * tolFrac : _Point * 50;

      if(direction == DIR_LONG)
      {
         double swingLows[];
         int    count = 0;
         ArrayResize(swingLows, LIQ_HTF_LOOKBACK);

         for(int i = LIQ_HTF_PIVOT_BARS; i < LIQ_HTF_LOOKBACK; i++)
            if(IsSwingLow(lo, i, LIQ_HTF_PIVOT_BARS))
               swingLows[count++] = lo[i];

         for(int a = 0; a < count - 1; a++)
         {
            int touches = 1;
            for(int b = a + 1; b < count; b++)
               if(MathAbs(swingLows[a] - swingLows[b]) <= tol) touches++;

            if(touches >= LIQ_HTF_EQ_TOUCHES)
            {
               poolLevel = swingLows[a];
               reason    = StringFormat("Equal lows pool %.5f (%d touches)", poolLevel, touches);
               return true;
            }
         }
      }
      else if(direction == DIR_SHORT)
      {
         double swingHighs[];
         int    count = 0;
         ArrayResize(swingHighs, LIQ_HTF_LOOKBACK);

         for(int i = LIQ_HTF_PIVOT_BARS; i < LIQ_HTF_LOOKBACK; i++)
            if(IsSwingHigh(hi, i, LIQ_HTF_PIVOT_BARS))
               swingHighs[count++] = hi[i];

         for(int a = 0; a < count - 1; a++)
         {
            int touches = 1;
            for(int b = a + 1; b < count; b++)
               if(MathAbs(swingHighs[a] - swingHighs[b]) <= tol) touches++;

            if(touches >= LIQ_HTF_EQ_TOUCHES)
            {
               poolLevel = swingHighs[a];
               reason    = StringFormat("Equal highs pool %.5f (%d touches)", poolLevel, touches);
               return true;
            }
         }
      }

      // v3.4.7 diagnostic: log equal-level tolerance used
      Print(StringFormat(
         "[LIQ][HTFPOOL] No equal pool found | dir=%s tol=%.5f (%.2f ATR) lookback=%d",
         (direction==DIR_SHORT)?"SHORT":"LONG", tol,
         (atrVal>0?tol/atrVal:0), LIQ_HTF_LOOKBACK));
      return false;
   }

   bool DetectMicroSweep(ENUM_TRADE_DIRECTION direction, string &reason)
   {
      reason = "";

      double hi[], lo[], cl[];
      ArraySetAsSeries(hi, true);
      ArraySetAsSeries(lo, true);
      ArraySetAsSeries(cl, true);

      if(CopyHigh( _Symbol, PERIOD_M1, 0, LIQ_M1_LOOKBACK, hi) < LIQ_M1_LOOKBACK) return false;
      if(CopyLow(  _Symbol, PERIOD_M1, 0, LIQ_M1_LOOKBACK, lo) < LIQ_M1_LOOKBACK) return false;
      if(CopyClose(_Symbol, PERIOD_M1, 0, LIQ_M1_LOOKBACK, cl) < LIQ_M1_LOOKBACK) return false;

      if(direction == DIR_LONG)
      {
         double swingLow = lo[2];
         for(int i = 3; i < LIQ_M1_LOOKBACK; i++)
            if(lo[i] < swingLow) swingLow = lo[i];

         if(lo[1] < swingLow && cl[1] > swingLow)
         {
            reason = StringFormat("M1 bullish sweep: wick=%.5f swingLow=%.5f close=%.5f",
                                  lo[1], swingLow, cl[1]);
            return true;
         }
      }
      else if(direction == DIR_SHORT)
      {
         double swingHigh = hi[2];
         for(int i = 3; i < LIQ_M1_LOOKBACK; i++)
            if(hi[i] > swingHigh) swingHigh = hi[i];

         if(hi[1] > swingHigh && cl[1] < swingHigh)
         {
            reason = StringFormat("M1 bearish sweep: wick=%.5f swingHigh=%.5f close=%.5f",
                                  hi[1], swingHigh, cl[1]);
            return true;
         }
      }

      return false;
   }

   bool IsSwingLow(const double &lo[], int idx, int pivot)
   {
      for(int k = 1; k <= pivot; k++)
      {
         if(idx - k < 0 || idx + k >= ArraySize(lo)) return false;
         if(lo[idx - k] <= lo[idx]) return false;
         if(lo[idx + k] <= lo[idx]) return false;
      }
      return true;
   }

   bool IsSwingHigh(const double &hi[], int idx, int pivot)
   {
      for(int k = 1; k <= pivot; k++)
      {
         if(idx - k < 0 || idx + k >= ArraySize(hi)) return false;
         if(hi[idx - k] >= hi[idx]) return false;
         if(hi[idx + k] >= hi[idx]) return false;
      }
      return true;
   }

   double GetATR()
   {
      double atr[];
      ArraySetAsSeries(atr, true);
      if(CopyBuffer(m_atrHandle, 0, 0, 1, atr) < 1) return _Point * 100;
      return atr[0];
   }
};
#endif // ASE_LIQUIDITYENGINE_MQH
