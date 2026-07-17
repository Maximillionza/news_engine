#ifndef ASE_SETUPENGINE_MQH
#define ASE_SETUPENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — M15 Setup Engine                                        |
//| FIX #10: Removed dead member variables m_compBarsCount,          |
//|           m_compRangeHigh, m_compRangeLow. These were declared   |
//|           but never written after construction — CheckCompression |
//|           computed everything locally and never used the members. |
//+------------------------------------------------------------------+

#define SETUP_FVG_LOOKBACK   20
#define SETUP_COMP_BARS       5

class CASE_SetupEngine
{
private:
   int      m_emaHandle;
   int      m_atrHandle;
   // FIX #10 — dead members removed:
   //   int    m_compBarsCount;   (was never written post-init)
   //   double m_compRangeHigh;   (was never written post-init)
   //   double m_compRangeLow;    (was never written post-init)

   // v3.14.9 Fix 11: track EMA distance across consecutive M15 bar evaluations
   // so CheckEMAPullback() can detect price approaching the EMA (distance decreasing)
   // even when the macro EMA slope is steep. Prevents the Jul 1 false-block where
   // macroSlope >= 1.4 rejected every bar regardless of direction-of-approach.
   double   m_prevDistFromEMA;    // distFromEMA from prior CheckEMAPullback() call
   datetime m_prevDistTimestamp;  // time of prior call — staleness guard

public:
   CASE_SetupEngine() : m_emaHandle(INVALID_HANDLE),
                        m_atrHandle(INVALID_HANDLE),
                        m_prevDistFromEMA(0.0),
                        m_prevDistTimestamp(0) {}

   bool Initialize()
   {
      m_emaHandle = iMA(_Symbol, PERIOD_M15, InpM15EMA, 0, MODE_EMA, PRICE_CLOSE);
      m_atrHandle = iATR(_Symbol, PERIOD_M15, InpATRPeriod);
      return (m_emaHandle != INVALID_HANDLE && m_atrHandle != INVALID_HANDLE);
   }

   void Deinitialize()
   {
      if(m_emaHandle != INVALID_HANDLE) IndicatorRelease(m_emaHandle);
      if(m_atrHandle != INVALID_HANDLE) IndicatorRelease(m_atrHandle);
   }

   // v3.14.3 — regime and h4Dir passed from StateMachine so CheckDisplacement()
   // can apply the counter-trend threshold when direction != h4Dir in TRENDING.
   // Defaults preserve backward compatibility for all other call sites.
   // v3.14.3 — h4EMASep / h4ATR replace regime parameter.
   // Counter-trend gate activates when h4EMASep > InpCTEMASepThreshold * h4ATR,
   // measuring H4 trend commitment directly rather than H1 regime classification.
   // Defaults (0.0) keep the gate inactive at all call sites that omit them.
   ValidationResult Evaluate(ENUM_TRADE_DIRECTION direction, string &setupClass,
                              double h4EMASep        = 0.0,
                              double h4ATR           = 0.0,
                              ENUM_TRADE_DIRECTION h4Dir = DIR_NONE,
                              double ctDispMultiplier = 0.60,
                              double ctFVGMinGap     = 0.30,
                              double ctFVGMaxDepth   = 0.70)
   {
      ValidationResult r;
      r.passed = false;
      r.reason = "No M15 setup";
      r.score  = 0.0;
      setupClass = "None";

      if(direction == DIR_NONE) { r.reason = "Setup: no direction from HTF"; return r; }

      double hi[], lo[], cl[], op[];
      ArraySetAsSeries(hi, true); ArraySetAsSeries(lo, true);
      ArraySetAsSeries(cl, true); ArraySetAsSeries(op, true);

      int needed = MathMax(SETUP_FVG_LOOKBACK + 3, 22);
      if(CopyHigh( _Symbol, PERIOD_M15, 0, needed, hi) < needed) { r.reason = "Setup: H buffer fail"; return r; }
      if(CopyLow(  _Symbol, PERIOD_M15, 0, needed, lo) < needed) { r.reason = "Setup: L buffer fail"; return r; }
      if(CopyClose(_Symbol, PERIOD_M15, 0, needed, cl) < needed) { r.reason = "Setup: C buffer fail"; return r; }
      if(CopyOpen( _Symbol, PERIOD_M15, 0, needed, op) < needed) { r.reason = "Setup: O buffer fail"; return r; }

      double ema[], atr[];
      ArraySetAsSeries(ema, true); ArraySetAsSeries(atr, true);
      if(CopyBuffer(m_emaHandle, 0, 0, 22, ema) < 22) { r.reason = "Setup: EMA buffer fail"; return r; }
      if(CopyBuffer(m_atrHandle, 0, 0, 22, atr) < 22) { r.reason = "Setup: ATR buffer fail"; return r; }

      double price  = cl[1];
      double emaVal = ema[0];
      double atrVal = atr[0];

      // v3.7.0 — per-setupClass suppression gates (Task 10).
      // Each class can be disabled independently via its boolean input.
      // All default true (backward compatible). After running the
      // per-class × regime win-rate analysis, set the worst-performing
      // class to false to suppress it without removing any logic.
      ValidationResult fvgResult;
      if(InpEnableFVG)
      {
         fvgResult = CheckFVG(direction, price, hi, lo, atrVal, h4EMASep, h4ATR, h4Dir, ctFVGMinGap, ctFVGMaxDepth);
         if(fvgResult.passed) { r = fvgResult; setupClass = "FVG"; return r; }
      }
      else { fvgResult.reason = "FVG disabled"; }

      ValidationResult dispResult;
      if(InpEnableDisplacement)
      {
         dispResult = CheckDisplacement(direction, cl, op, hi, lo, atrVal, h4EMASep, h4ATR, h4Dir, ctDispMultiplier);
         if(dispResult.passed) { r = dispResult; setupClass = "M15_Displacement"; return r; }
      }
      else { dispResult.reason = "Displacement disabled"; }

      ValidationResult compResult;
      if(InpEnableCompressionBO)
      {
         compResult = CheckCompression(direction, price, cl, atr, atrVal);
         if(compResult.passed) { r = compResult; setupClass = "Compression_BO"; return r; }
      }
      else { compResult.reason = "CompressionBO disabled"; }

      ValidationResult emaResult;
      if(InpEnableEMAPullback)
      {
         emaResult = CheckEMAPullback(direction, price, emaVal, atr, ema, atrVal);
         if(emaResult.passed) { r = emaResult; setupClass = "EMA_Pullback"; return r; }
      }
      else { emaResult.reason = "EMAPullback disabled"; }

      r.reason = StringFormat(
         "Setup failed | FVG:%s Disp:%s Comp:%s EMA:%s | dist=%.2fATR",
         fvgResult.reason, dispResult.reason,
         compResult.reason, emaResult.reason,
         (price - emaVal) / atrVal);
      return r;
   }

   ValidationResult Evaluate(ENUM_TRADE_DIRECTION direction)
   {
      string dummy;
      return Evaluate(direction, dummy);
   }

   // v4.0 — overload that also populates structural TP levels.
   // Called from ProcessSetup() so RiskEngine has concrete price targets
   // available when BuildSetup() is called at execution time.
   // v3.14.3 — regime, h4Dir, ctDispMultiplier forwarded to inner Evaluate().
   ValidationResult Evaluate(ENUM_TRADE_DIRECTION  direction,
                              string               &setupClass,
                              StructuralLevels     &levels,
                              double               h4EMASep         = 0.0,
                              double               h4ATR            = 0.0,
                              ENUM_TRADE_DIRECTION h4Dir            = DIR_NONE,
                              double               ctDispMultiplier = 0.60,
                              double               ctFVGMinGap      = 0.30,
                              double               ctFVGMaxDepth    = 0.70)
   {
      ZeroMemory(levels);
      levels.source = "None";

      // Run the standard evaluation first (passes regime context down)
      ValidationResult r = Evaluate(direction, setupClass, h4EMASep, h4ATR, h4Dir, ctDispMultiplier, ctFVGMinGap, ctFVGMaxDepth);
      if(!r.passed) return r;

      // Get current ATR for distance validation
      double atr[];
      ArraySetAsSeries(atr, true);
      double atrVal = (CopyBuffer(m_atrHandle, 0, 0, 1, atr) >= 1) ? atr[0] : 0.0;

      // Rebuild the price buffers needed for level computation
      int needed = MathMax(SETUP_FVG_LOOKBACK + 3, 22);
      double hi[], lo[], op[], cl[];
      ArraySetAsSeries(hi, true); ArraySetAsSeries(lo, true);
      ArraySetAsSeries(op, true); ArraySetAsSeries(cl, true);
      if(CopyHigh( _Symbol, PERIOD_M15, 0, needed, hi) < needed) return r;
      if(CopyLow(  _Symbol, PERIOD_M15, 0, needed, lo) < needed) return r;
      if(CopyOpen( _Symbol, PERIOD_M15, 0, needed, op) < needed) return r;
      if(CopyClose(_Symbol, PERIOD_M15, 0, needed, cl) < needed) return r;

      double entry = (direction == DIR_LONG)
                   ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                   : SymbolInfoDouble(_Symbol, SYMBOL_BID);

      if     (setupClass == "FVG")            ComputeFVGLevels(direction, entry, hi, lo, atrVal, levels);
      else if(setupClass == "M15_Displacement") ComputeDisplacementLevels(direction, entry, hi, lo, op, cl, atrVal, levels);
      else if(setupClass == "Compression_BO") ComputeCompressionLevels(direction, entry, hi, lo, cl, atr, atrVal, levels);
      else if(setupClass == "EMA_Pullback")   ComputeH4SwingLevels(direction, entry, atrVal, levels);
      // EMA_Fallback — same approach as EMA_Pullback
      else                                    ComputeH4SwingLevels(direction, entry, atrVal, levels);

      return r;
   }

private:
   // v3.14.3 — regime/h4Dir/ctFVGMinGap/ctFVGMaxDepth added.
   // When regime == REGIME_TRENDING and dir != h4Dir (counter-trend entry):
   //   - Minimum gap size raised to ctFVGMinGap × ATR (default 0.50 vs standard 0.30)
   //   - Maximum penetration tightened to ctFVGMaxDepth (default 0.50 vs standard 0.70)
   // Both raise the quality bar for counter-trend FVG entries in a committed trend.
   // Zero behaviour change in RANGING, COMPRESSION, MANIPULATION, or with-trend entries.
   ValidationResult CheckFVG(ENUM_TRADE_DIRECTION dir, double price,
                              const double &hi[], const double &lo[], double atr,
                              double h4EMASep               = 0.0,
                              double h4ATR                  = 0.0,
                              ENUM_TRADE_DIRECTION h4Dir    = DIR_NONE,
                              double ctFVGMinGap            = 0.30,
                              double ctFVGMaxDepth          = 0.70)
   {
      ValidationResult r;
      r.passed = false; r.score = 0.0; r.reason = "No FVG";

      // v3.14.3 — Counter-trend gate condition.
      // Activates when H4 EMA separation exceeds threshold × H4 ATR AND
      // the setup direction opposes the committed H4 trend direction.
      // h4ATR=0 on warmup → ratio=0 → gate inactive (safe default).
      bool emaSepCommitted = (h4ATR > 0 &&
                              h4EMASep > InpCTEMASepThreshold * h4ATR);
      bool isCounterTrend  = (emaSepCommitted &&
                              h4Dir != DIR_NONE &&
                              dir   != h4Dir);
      double minGap   = isCounterTrend ? ctFVGMinGap   : 0.30;
      double maxDepth = isCounterTrend ? ctFVGMaxDepth : 0.70;
      if(isCounterTrend)
         Print(StringFormat("[SETUP] CT-FVG gate | H4=%s Dir=%s | sep=%.5f ATR=%.5f ratio=%.2f | minGap=%.2f maxDepth=%.0f%%",
               h4Dir == DIR_LONG ? "LONG" : "SHORT",
               dir   == DIR_LONG ? "LONG" : "SHORT",
               h4EMASep, h4ATR, (h4ATR > 0 ? h4EMASep/h4ATR : 0),
               minGap, maxDepth * 100));

      for(int i = 2; i < SETUP_FVG_LOOKBACK; i++)
      {
         // v3.7.0 — age gate: reject FVGs older than InpFVGMaxBars bars.
         // An FVG formed 18 bars ago has had 18 × 15 min = 4.5h for price
         // to fully mitigate it; the statistical edge of entering diminishes
         // sharply with age. Default 10 = 2.5 hours. 0 = disabled.
         if(InpFVGMaxBars > 0 && i > InpFVGMaxBars) break;

         if(dir == DIR_LONG)
         {
            double fvgTop    = lo[i];
            double fvgBottom = hi[i + 2];
            if(fvgTop <= fvgBottom) continue;
            if(fvgTop - fvgBottom < atr * minGap) continue;
            if(price >= fvgBottom && price <= fvgTop)
            {
               // v3.7.0 — proximity gate: reject if price is > maxDepth through
               // the gap from the entry side. Counter-trend: tighter ceiling.
               double penetration = (fvgTop > fvgBottom)
                                    ? (price - fvgBottom) / (fvgTop - fvgBottom)
                                    : 0.0;
               if(penetration > maxDepth)
               {
                  r.reason = StringFormat(
                     "Bullish FVG [%.5f-%.5f] bar=%d rejected: %.0f%% deep (>%.0f%%)",
                     fvgBottom, fvgTop, i, penetration * 100, maxDepth * 100);
                  continue;
               }

               r.passed = true;
               r.score  = 22.0 + (i <= 5 ? 3.0 : 0.0);
               r.reason = StringFormat(
                  "Bullish FVG [%.5f–%.5f] bar=%d price=%.5f depth=%.0f%%",
                  fvgBottom, fvgTop, i, price, penetration * 100);
               return r;
            }
         }
         else if(dir == DIR_SHORT)
         {
            double fvgBottom = hi[i];
            double fvgTop    = lo[i + 2];
            if(fvgBottom >= fvgTop) continue;
            if(fvgTop - fvgBottom < atr * minGap) continue;
            if(price >= fvgBottom && price <= fvgTop)
            {
               // v3.7.0 — proximity gate (SHORT): entry from the top of the gap.
               // penetration measures how far price has fallen into the gap from fvgTop.
               double penetration = (fvgTop > fvgBottom)
                                    ? (fvgTop - price) / (fvgTop - fvgBottom)
                                    : 0.0;
               if(penetration > maxDepth)
               {
                  r.reason = StringFormat(
                     "Bearish FVG [%.5f-%.5f] bar=%d rejected: %.0f%% deep (>%.0f%%)",
                     fvgBottom, fvgTop, i, penetration * 100, maxDepth * 100);
                  continue;
               }

               r.passed = true;
               r.score  = 22.0 + (i <= 5 ? 3.0 : 0.0);
               r.reason = StringFormat(
                  "Bearish FVG [%.5f–%.5f] bar=%d price=%.5f depth=%.0f%%",
                  fvgBottom, fvgTop, i, price, penetration * 100);
               return r;
            }
         }
      }
      return r;
   }

   // v3.14.3 — regime/h4Dir/ctDispMultiplier added.
   // When regime == REGIME_TRENDING and dir != h4Dir (counter-trend entry),
   // the ATR body threshold is raised to ctDispMultiplier instead of 0.60.
   // In all other cases (regime != TRENDING, or dir == h4Dir, or h4Dir == DIR_NONE)
   // standard 0.60 threshold applies — zero behaviour change.
   ValidationResult CheckDisplacement(ENUM_TRADE_DIRECTION dir,
                                      const double &cl[], const double &op[],
                                      const double &hi[], const double &lo[], double atr,
                                      double h4EMASep          = 0.0,
                                      double h4ATR             = 0.0,
                                      ENUM_TRADE_DIRECTION h4Dir = DIR_NONE,
                                      double ctDispMultiplier  = 0.60)
   {
      ValidationResult r;
      r.passed = false; r.score = 0.0; r.reason = "No M15 displacement";

      // Resolve effective ATR body threshold.
      // Counter-trend in TRENDING regime → raise the bar.
      // With-trend, ranging, compression, manipulation → standard 0.60.
      // v3.14.3 — same H4 EMA separation condition as CheckFVG.
      bool emaSepCommitted    = (h4ATR > 0 &&
                                 h4EMASep > InpCTEMASepThreshold * h4ATR);
      bool isCounterTrend     = (emaSepCommitted &&
                                 h4Dir != DIR_NONE &&
                                 dir   != h4Dir);
      double atrBodyThreshold = isCounterTrend ? ctDispMultiplier : 0.60;
      if(isCounterTrend)
         Print(StringFormat("[SETUP] CT-Disp gate | H4=%s Dir=%s | sep=%.5f ATR=%.5f ratio=%.2f | threshold=%.2f×ATR",
               h4Dir == DIR_LONG ? "LONG" : "SHORT",
               dir   == DIR_LONG ? "LONG" : "SHORT",
               h4EMASep, h4ATR, (h4ATR > 0 ? h4EMASep/h4ATR : 0),
               atrBodyThreshold));

      for(int i = 1; i <= 3; i++)
      {
         double body  = MathAbs(cl[i] - op[i]);
         double range = hi[i] - lo[i];
         if(body < atr * atrBodyThreshold) continue;

         bool bullBar   = cl[i] > op[i];
         bool bearBar   = cl[i] < op[i];
         double bodyRatio = (range > 0) ? body / range : 0;

         if(dir == DIR_LONG && bullBar && bodyRatio >= 0.65)
         {
            r.passed = true;
            r.score  = 20.0 + (i == 1 ? 2.0 : 0.0);
            r.reason = StringFormat("M15 LONG displacement bar[%d] body=%.5f atr=%.5f", i, body, atr);
            return r;
         }
         if(dir == DIR_SHORT && bearBar && bodyRatio >= 0.65)
         {
            r.passed = true;
            r.score  = 20.0 + (i == 1 ? 2.0 : 0.0);
            r.reason = StringFormat("M15 SHORT displacement bar[%d] body=%.5f atr=%.5f", i, body, atr);
            return r;
         }
      }
      return r;
   }

   ValidationResult CheckCompression(ENUM_TRADE_DIRECTION dir, double price,
                                      const double &cl[], const double &atr[], double atrNow)
   {
      ValidationResult r;
      r.passed = false; r.score = 0.0; r.reason = "No compression";

      double atrAvg = 0.0;
      for(int i = 1; i <= 20; i++) atrAvg += atr[i];
      atrAvg /= 20.0;

      // Local variables only — FIX #10 confirms member vars correctly removed
      int    compBars = 0;
      double compHigh = cl[1], compLow = cl[1];
      for(int i = 2; i <= 10; i++)
      {
         if(atr[i] < atrAvg * 0.70)
         {
            compBars++;
            if(cl[i] > compHigh) compHigh = cl[i];
            if(cl[i] < compLow)  compLow  = cl[i];
         }
         else break;
      }

      if(compBars < SETUP_COMP_BARS) { r.reason = StringFormat("Compression: only %d comp bars", compBars); return r; }
      if(atrNow < atrAvg * 0.9)      { r.reason = "Compression: ATR not yet expanding"; return r; }

      bool breakLong  = price > compHigh && dir == DIR_LONG;
      bool breakShort = price < compLow  && dir == DIR_SHORT;

      if(breakLong)
      {
         r.passed = true;
         r.score  = 15.0 + (double)compBars * 0.5;
         r.reason = StringFormat("Compression BO LONG | %d comp bars | range=[%.5f–%.5f]",
                                  compBars, compLow, compHigh);
      }
      else if(breakShort)
      {
         r.passed = true;
         r.score  = 15.0 + (double)compBars * 0.5;
         r.reason = StringFormat("Compression BO SHORT | %d comp bars | range=[%.5f–%.5f]",
                                  compBars, compLow, compHigh);
      }
      else
      {
         r.reason = StringFormat("Compression: no breakout | price=%.5f range=[%.5f–%.5f]",
                                  price, compLow, compHigh);
      }
      return r;
   }

   ValidationResult CheckEMAPullback(ENUM_TRADE_DIRECTION dir, double price,
                                      double emaVal, const double &atr[],
                                      const double &ema[], double atrVal)
   {
      ValidationResult r;
      r.passed = false; r.score = 0.0; r.reason = "No EMA pullback";

      double macroSlope     = (ema[0] - ema[10]) / atrVal;
      double shortTermSlope = (ema[0] - ema[3])  / atrVal;
      double distFromEMA    = (price - emaVal)    / atrVal;

      // v3.14.9 Fix 11: direction-of-approach tracking.
      // Save and update prevDist BEFORE any early return so the tracker stays
      // current regardless of pass/fail. On the next call, approaching=true when
      // the new dist is closer to 0 than the prior one.
      double   prevDist  = m_prevDistFromEMA;
      bool     prevValid = (m_prevDistTimestamp > 0);
      m_prevDistFromEMA   = distFromEMA;
      m_prevDistTimestamp = TimeCurrent();

      if(dir == DIR_LONG)
      {
         // v3.10.0 fix (Bug 3): Raised from 0.9 to 1.4 — only blocks when EMA
         // is rising extremely steeply (parabolic, true missed-entry).
         // v3.14.9 Fix 11: further refinement — bypass the steep-slope block when
         // price is APPROACHING the EMA (distFromEMA decreasing). A valid pullback
         // into a fast-rising EMA was the Jul 1 root cause: dist 2.72→2.40→1.86 ATR
         // across 3 evaluations, macroSlope >= 1.4 on all three → every bar blocked.
         if(macroSlope >= 1.4)
         {
            bool approaching = (prevValid && distFromEMA < prevDist);
            if(!approaching)
            { r.reason = StringFormat("LONG: trend resumed, EMA rising hard (%.2f)", macroSlope); return r; }
            Print(StringFormat("[SETUP] macroSlope=%.2f rising hard but approaching EMA (%.2f→%.2f ATR) — allowed", macroSlope, prevDist, distFromEMA));
         }
         if(distFromEMA >= 1.5)   { r.reason = StringFormat("LONG: price too far above EMA (%.2f ATR) — missed", distFromEMA); return r; }
         if(distFromEMA <= -1.8)  { r.reason = StringFormat("LONG: pullback overextended (%.2f ATR) — wait for bounce", distFromEMA); return r; }
         r.passed = true;
         r.score  = 15.0 + (MathAbs(distFromEMA) < 0.3 ? 3.0 : 0.0) + (shortTermSlope < 0 ? 2.0 : 0.0);
         r.reason = StringFormat("EMA pullback LONG | dist=%.2fATR macro=%.2f", distFromEMA, macroSlope);
      }
      else if(dir == DIR_SHORT)
      {
         // v3.14.9 Fix 11: mirror of LONG — bypass falling-hard block when price
         // approaching EMA from below (distFromEMA rising toward 0 = less negative).
         if(macroSlope <= -0.9)
         {
            bool approaching = (prevValid && distFromEMA > prevDist);
            if(!approaching)
            { r.reason = StringFormat("SHORT: trend resumed, EMA falling hard (%.2f)", macroSlope); return r; }
            Print(StringFormat("[SETUP] macroSlope=%.2f falling hard but approaching EMA (%.2f→%.2f ATR) — allowed", macroSlope, prevDist, distFromEMA));
         }
         if(distFromEMA <= -1.5)  { r.reason = StringFormat("SHORT: price too far below EMA (%.2f ATR) — missed", distFromEMA); return r; }
         if(distFromEMA >= 1.8)   { r.reason = StringFormat("SHORT: pullback overextended (%.2f ATR) — wait for rejection", distFromEMA); return r; }
         r.passed = true;
         r.score  = 15.0 + (MathAbs(distFromEMA) < 0.3 ? 3.0 : 0.0) + (shortTermSlope > 0 ? 2.0 : 0.0);
         r.reason = StringFormat("EMA pullback SHORT | dist=%.2fATR macro=%.2f", distFromEMA, macroSlope);
      }
      return r;
   }

   //==================================================================
   // v4.0 — Structural TP level helpers
   //==================================================================

   void ComputeFVGLevels(ENUM_TRADE_DIRECTION dir, double entry,
                         const double &hi[], const double &lo[],
                         double atrVal, StructuralLevels &levels)
   {
      levels.source = "FVG";
      double minDist = atrVal * 0.3;   // v3.4.8: reduced from 0.5 — 0.5 ATR was rejecting
                                  // valid structural levels near entry on GOLD at ATR~12
      for(int i = 2; i < SETUP_FVG_LOOKBACK; i++)
      {
         if(dir == DIR_SHORT)
         {
            double fvgBottom = hi[i], fvgTop = lo[i + 2];
            if(fvgBottom >= fvgTop || entry < fvgBottom || entry > fvgTop) continue;
            if(entry - fvgBottom >= minDist) { levels.tp1 = fvgBottom; levels.tp1Valid = true; }
            for(int j = i+1; j < SETUP_FVG_LOOKBACK+10 && j < ArraySize(lo)-2; j++)
               if(SwgLow(lo,j,2) && lo[j] < fvgBottom) { levels.tp2 = lo[j]; levels.tp2Valid = true; break; }
            return;
         }
         else if(dir == DIR_LONG)
         {
            double fvgBottom = hi[i+2], fvgTop = lo[i];
            if(fvgTop <= fvgBottom || entry < fvgBottom || entry > fvgTop) continue;
            if(fvgTop - entry >= minDist) { levels.tp1 = fvgTop; levels.tp1Valid = true; }
            for(int j = i+1; j < SETUP_FVG_LOOKBACK+10 && j < ArraySize(hi)-2; j++)
               if(SwgHigh(hi,j,2) && hi[j] > fvgTop) { levels.tp2 = hi[j]; levels.tp2Valid = true; break; }
            return;
         }
      }
   }

   void ComputeDisplacementLevels(ENUM_TRADE_DIRECTION dir, double entry,
                                   const double &hi[], const double &lo[],
                                   const double &op[], const double &cl[],
                                   double atrVal, StructuralLevels &levels)
   {
      levels.source = "Displacement";
      double minDist = atrVal * 0.3;   // v3.4.8: reduced from 0.5 — 0.5 ATR was rejecting
                                  // valid structural levels near entry on GOLD at ATR~12
      for(int i = 1; i <= 3 && i < ArraySize(cl)-1; i++)
      {
         double body = MathAbs(cl[i]-op[i]), range = hi[i]-lo[i];
         if(body < atrVal*0.60 || range <= 0 || (body/range) < 0.65) continue;
         if(dir == DIR_SHORT && cl[i] < op[i])
         {
            double t1 = cl[i]-body*0.5, t2 = cl[i]-body*1.0;
            if(entry-t1 >= minDist) { levels.tp1=t1; levels.tp1Valid=true; }
            if(entry-t2 >= minDist) { levels.tp2=t2; levels.tp2Valid=true; }
            return;
         }
         if(dir == DIR_LONG && cl[i] > op[i])
         {
            double t1 = cl[i]+body*0.5, t2 = cl[i]+body*1.0;
            if(t1-entry >= minDist) { levels.tp1=t1; levels.tp1Valid=true; }
            if(t2-entry >= minDist) { levels.tp2=t2; levels.tp2Valid=true; }
            return;
         }
      }
   }

   void ComputeCompressionLevels(ENUM_TRADE_DIRECTION dir, double entry,
                                  const double &hi[], const double &lo[],
                                  const double &cl[], const double &atr[],
                                  double atrNow, StructuralLevels &levels)
   {
      levels.source = "Compression";
      double atrAvg = 0.0;
      for(int i = 1; i <= 20; i++) atrAvg += atr[i];
      atrAvg /= 20.0;
      double compHigh = cl[1], compLow = cl[1];
      int compBars = 0;
      for(int i = 2; i <= 10 && i < ArraySize(cl); i++)
      {
         if(atr[i] < atrAvg*0.70)
         { compBars++; if(cl[i]>compHigh) compHigh=cl[i]; if(cl[i]<compLow) compLow=cl[i]; }
         else break;
      }
      if(compBars < SETUP_COMP_BARS) return;
      double range = compHigh-compLow, minDist = atrNow*0.3;   // v3.4.8: reduced from 0.5
      if(dir == DIR_SHORT)
      {
         double t1=compLow-range*0.5, t2=compLow-range*1.0;
         if(entry-t1>=minDist){levels.tp1=t1;levels.tp1Valid=true;}
         if(entry-t2>=minDist){levels.tp2=t2;levels.tp2Valid=true;}
      }
      else if(dir == DIR_LONG)
      {
         double t1=compHigh+range*0.5, t2=compHigh+range*1.0;
         if(t1-entry>=minDist){levels.tp1=t1;levels.tp1Valid=true;}
         if(t2-entry>=minDist){levels.tp2=t2;levels.tp2Valid=true;}
      }
   }

   void ComputeH4SwingLevels(ENUM_TRADE_DIRECTION dir, double entry,
                              double atrVal, StructuralLevels &levels)
   {
      levels.source = "H4Swing";
      double h4Hi[], h4Lo[];
      ArraySetAsSeries(h4Hi,true); ArraySetAsSeries(h4Lo,true);
      int n = 8;
      if(CopyHigh(_Symbol,PERIOD_H4,0,n,h4Hi)<n) return;
      if(CopyLow( _Symbol,PERIOD_H4,0,n,h4Lo)<n) return;
      double minD=atrVal*1.0, maxD=atrVal*6.0;
      if(dir == DIR_SHORT)
      {
         for(int i=1;i<n-1;i++)
         {
            if(h4Lo[i]>=h4Lo[i-1]||h4Lo[i]>=h4Lo[i+1]) continue;
            double dist=entry-h4Lo[i];
            if(dist<minD||dist>maxD) continue;
            levels.tp2=h4Lo[i]; levels.tp2Valid=true;
            double tp1m=entry-dist*0.5;
            if(entry-tp1m>=minD*0.5){levels.tp1=tp1m;levels.tp1Valid=true;}
            return;
         }
      }
      else if(dir == DIR_LONG)
      {
         for(int i=1;i<n-1;i++)
         {
            if(h4Hi[i]<=h4Hi[i-1]||h4Hi[i]<=h4Hi[i+1]) continue;
            double dist=h4Hi[i]-entry;
            if(dist<minD||dist>maxD) continue;
            levels.tp2=h4Hi[i]; levels.tp2Valid=true;
            double tp1m=entry+dist*0.5;
            if(tp1m-entry>=minD*0.5){levels.tp1=tp1m;levels.tp1Valid=true;}
            return;
         }
      }
   }

   bool SwgLow(const double &lo[], int idx, int pivot)
   {
      for(int k=1;k<=pivot;k++)
      {
         if(idx-k<0||idx+k>=ArraySize(lo)) return false;
         if(lo[idx-k]<=lo[idx]||lo[idx+k]<=lo[idx]) return false;
      }
      return true;
   }
   bool SwgHigh(const double &hi[], int idx, int pivot)
   {
      for(int k=1;k<=pivot;k++)
      {
         if(idx-k<0||idx+k>=ArraySize(hi)) return false;
         if(hi[idx-k]>=hi[idx]||hi[idx+k]>=hi[idx]) return false;
      }
      return true;
   }

};
#endif // ASE_SETUPENGINE_MQH
