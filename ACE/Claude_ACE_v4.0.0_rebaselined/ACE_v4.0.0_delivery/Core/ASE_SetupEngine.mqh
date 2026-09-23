#ifndef ASE_SETUPENGINE_MQH
#define ASE_SETUPENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
#include "../Models/ASE_EvidenceTypes.mqh"   // v4.0 — EvaluateAllEvidence() below
#include "../Utilities/ASE_Time.mqh"          // v4.0.1 — CheckKillZone()/CheckAMDPhase() below
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
   int m_emaHandle;
   int m_atrHandle;
   // FIX #10 — dead members removed:
   //   int    m_compBarsCount;   (was never written post-init)
   //   double m_compRangeHigh;   (was never written post-init)
   //   double m_compRangeLow;    (was never written post-init)

   // v4.0.1 — resolved once at Initialize(), not re-checked per bar.
   // Genuinely new territory for this file (and this codebase — grepped
   // before writing this: every existing SymbolInfoDouble/CopyClose call
   // anywhere in Core/Utilities is scoped to _Symbol; nothing reads a
   // second symbol). Broker symbol availability for a DXY/USD-index proxy
   // is NOT verified in this environment (no MT5 runtime) — this must
   // fail soft, never block the EA, if InpMacroCorrSymbol doesn't exist
   // on the connected broker.
   bool   m_corrSymbolValid;

public:
   CASE_SetupEngine() : m_emaHandle(INVALID_HANDLE),
                        m_atrHandle(INVALID_HANDLE),
                        m_corrSymbolValid(false) {}

   bool Initialize()
   {
      m_emaHandle = iMA(_Symbol, PERIOD_M15, InpM15EMA, 0, MODE_EMA, PRICE_CLOSE);
      m_atrHandle = iATR(_Symbol, PERIOD_M15, InpATRPeriod);

      // v4.0.1 — macro correlation symbol. Deliberately NOT part of the
      // return value below: an unresolvable correlation symbol degrades
      // EVID_MACRO_CORRELATION to permanently inactive (see
      // CheckMacroCorrelation()), it must never fail EA Initialize().
      m_corrSymbolValid = false;
      if(InpEnableMacroCorrelation && StringLen(InpMacroCorrSymbol) > 0)
      {
         m_corrSymbolValid = SymbolSelect(InpMacroCorrSymbol, true);
         if(!m_corrSymbolValid)
            Print("[SETUP] WARNING — macro correlation symbol '", InpMacroCorrSymbol,
                  "' not found/selectable on this broker. EVID_MACRO_CORRELATION will stay ",
                  "inactive until InpMacroCorrSymbol (ASE_Config.mqh) is set to a symbol this ",
                  "broker actually offers — verify the exact ticker in Market Watch first.");
      }

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

   //------------------------------------------------------------------
   // v4.0 — ACE_v4_0_Plan_UPDATED.md §8: "Replace First Setup Wins".
   // Additive only — calls the SAME four private Check* methods the
   // legacy Evaluate() above calls, but does not early-return on the
   // first pass. Every check runs and its result is preserved as
   // evidence, whether or not it passed. Evaluate() above is
   // untouched: this method does not change what it computes or when
   // it is called from ProcessSetup().
   //
   // Returns the count of evidence items added (0-4). Caller supplies
   // the same direction/h4/counter-trend parameters already threaded
   // through ProcessSetup() today.
   //------------------------------------------------------------------
   int EvaluateAllEvidence(ENUM_TRADE_DIRECTION direction,
                            SetupEvidenceSet     &ev,
                            double               h4EMASep         = 0.0,
                            double               h4ATR            = 0.0,
                            ENUM_TRADE_DIRECTION h4Dir            = DIR_NONE,
                            double               ctDispMultiplier = 0.60,
                            double               ctFVGMinGap      = 0.30,
                            double               ctFVGMaxDepth    = 0.70)
   {
      if(direction == DIR_NONE) return 0;

      double hi[], lo[], cl[], op[];
      ArraySetAsSeries(hi, true); ArraySetAsSeries(lo, true);
      ArraySetAsSeries(cl, true); ArraySetAsSeries(op, true);

      int needed = MathMax(SETUP_FVG_LOOKBACK + 3, 22);
      if(CopyHigh( _Symbol, PERIOD_M15, 0, needed, hi) < needed) return 0;
      if(CopyLow(  _Symbol, PERIOD_M15, 0, needed, lo) < needed) return 0;
      if(CopyClose(_Symbol, PERIOD_M15, 0, needed, cl) < needed) return 0;
      if(CopyOpen( _Symbol, PERIOD_M15, 0, needed, op) < needed) return 0;

      double ema[], atr[];
      ArraySetAsSeries(ema, true); ArraySetAsSeries(atr, true);
      if(CopyBuffer(m_emaHandle, 0, 0, 22, ema) < 22) return 0;
      if(CopyBuffer(m_atrHandle, 0, 0, 22, atr) < 22) return 0;

      double price  = cl[1];
      double emaVal = ema[0];
      double atrVal = atr[0];
      datetime now  = TimeCurrent();
      int added = 0;

      SetupEvidence e;

      if(InpEnableFVG)
      {
         ValidationResult res = CheckFVG(direction, price, hi, lo, atrVal, h4EMASep, h4ATR, h4Dir, ctFVGMinGap, ctFVGMaxDepth);
         e.Clear();
         e.evidType = EVID_M15_FVG; e.family = FAM_LOCATION; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_M15; e.priceRef = price;
         if(ev.Add(e)) added++;
      }
      if(InpEnableDisplacement)
      {
         ValidationResult res = CheckDisplacement(direction, cl, op, hi, lo, atrVal, h4EMASep, h4ATR, h4Dir, ctDispMultiplier);
         e.Clear();
         e.evidType = EVID_M15_DISPLACEMENT; e.family = FAM_MOMENTUM; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_M15; e.priceRef = price;
         if(ev.Add(e)) added++;
      }
      if(InpEnableCompressionBO)
      {
         ValidationResult res = CheckCompression(direction, price, cl, atr, atrVal);
         e.Clear();
         e.evidType = EVID_M15_COMPRESSION; e.family = FAM_ENVIRONMENT; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_M15; e.priceRef = price;
         if(ev.Add(e)) added++;
      }
      if(InpEnableEMAPullback)
      {
         ValidationResult res = CheckEMAPullback(direction, price, emaVal, atr, ema, atrVal);
         e.Clear();
         e.evidType = EVID_M15_EMA_PULLBACK; e.family = FAM_LOCATION; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_M15; e.priceRef = emaVal;
         if(ev.Add(e)) added++;
      }
      // v4.0.1 — Order Block. V4-evidence-only, same as the other checks
      // above; CheckOrderBlock() itself is never called from legacy
      // Evaluate(). See its own header comment for the definition used.
      if(InpEnableOrderBlock)
      {
         ValidationResult res = CheckOrderBlock(direction, price, hi, lo, cl, op, atrVal);
         e.Clear();
         e.evidType = EVID_ORDER_BLOCK; e.family = FAM_LOCATION; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_M15; e.priceRef = price;
         if(ev.Add(e)) added++;
      }
      // v4.0.1 — Kill Zone / AMD phase. Same V4-evidence-only wiring as
      // the checks above; neither is called from legacy Evaluate().
      if(InpEnableKillZoneEvidence)
      {
         ValidationResult res = CheckKillZone(direction);
         e.Clear();
         e.evidType = EVID_KILL_ZONE; e.family = FAM_ENVIRONMENT; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_CURRENT;
         if(ev.Add(e)) added++;
      }
      if(InpEnableAMDPhase)
      {
         ValidationResult res = CheckAMDPhase(direction, price);
         e.Clear();
         e.evidType = EVID_AMD_PHASE; e.family = FAM_LIQUIDITY; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_M15; e.priceRef = price;
         if(ev.Add(e)) added++;
      }
      // v4.0.1 — Macro correlation. Same V4-evidence-only wiring; never
      // called from legacy Evaluate(). Degrades to inactive-only if the
      // correlation symbol isn't available — see CheckMacroCorrelation().
      if(InpEnableMacroCorrelation)
      {
         ValidationResult res = CheckMacroCorrelation(direction);
         e.Clear();
         e.evidType = EVID_MACRO_CORRELATION; e.family = FAM_ENVIRONMENT; e.direction = direction;
         e.active = res.passed; e.strength = res.score; e.reason = res.reason;
         e.timestamp = now; e.sourceTF = PERIOD_M15;
         if(ev.Add(e)) added++;
      }
      return added;
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

      if(dir == DIR_LONG)
      {
         // v3.10.0 fix (Bug 3): Original threshold 0.9 was triggering in normal
         // bullish trending conditions, suppressing LONG EMA_Pullback setups on
         // the very days the market was making the clearest uptrend structure.
         // Raised to 1.4 — only blocks entry when the EMA is rising extremely
         // steeply (parabolic move), indicating a true missed-entry situation.
         // The downside EMA bound (-1.8) is unchanged — pullback overextension
         // detection remains conservative for LONG as before.
         if(macroSlope >= 1.4)    { r.reason = StringFormat("LONG: trend resumed, EMA rising hard (%.2f)", macroSlope); return r; }
         if(distFromEMA >= 1.5)   { r.reason = StringFormat("LONG: price too far above EMA (%.2f ATR) — missed", distFromEMA); return r; }
         if(distFromEMA <= -1.8)  { r.reason = StringFormat("LONG: pullback overextended (%.2f ATR) — wait for bounce", distFromEMA); return r; }
         r.passed = true;
         r.score  = 15.0 + (MathAbs(distFromEMA) < 0.3 ? 3.0 : 0.0) + (shortTermSlope < 0 ? 2.0 : 0.0);
         r.reason = StringFormat("EMA pullback LONG | dist=%.2fATR macro=%.2f", distFromEMA, macroSlope);
      }
      else if(dir == DIR_SHORT)
      {
         if(macroSlope <= -0.9)   { r.reason = StringFormat("SHORT: trend resumed, EMA falling hard (%.2f)", macroSlope); return r; }
         if(distFromEMA <= -1.5)  { r.reason = StringFormat("SHORT: price too far below EMA (%.2f ATR) — missed", distFromEMA); return r; }
         if(distFromEMA >= 1.8)   { r.reason = StringFormat("SHORT: pullback overextended (%.2f ATR) — wait for rejection", distFromEMA); return r; }
         r.passed = true;
         r.score  = 15.0 + (MathAbs(distFromEMA) < 0.3 ? 3.0 : 0.0) + (shortTermSlope > 0 ? 2.0 : 0.0);
         r.reason = StringFormat("EMA pullback SHORT | dist=%.2fATR macro=%.2f", distFromEMA, macroSlope);
      }
      return r;
   }

   //------------------------------------------------------------------
   // v4.0.1 — Order Block detector. NOT wired into the legacy Evaluate()
   // cascade above — only EvaluateAllEvidence() calls this, so it is
   // V4-evidence-only and carries zero risk to any existing execution
   // decision (v3.14.17, v4.0.0, or this build's own legacy-equivalent
   // path). A genuinely new detector, not a re-identified existing check
   // like the rest of this file's Check* methods were for plan §22.
   //
   // DEFINITION USED (one operational reading of "Order Block" among
   // several the ICT/SMC literature uses — documented, not claimed
   // canonical): the last opposite-colour M15 candle immediately before
   // a same-direction displacement candle whose close breaks beyond that
   // candle's high/low (a mini BOS — this is what distinguishes a real
   // order block from an arbitrary red candle before a green one). Zone
   // = the OB candle's full high/low range (not body-only — matches this
   // file's existing FVG convention of using full wicks, not bodies, for
   // zone boundaries). A block is disqualified if any bar between its
   // formation and now has already closed cleanly through the zone
   // (mitigated-and-broken, not just tapped) — same "don't chase a dead
   // zone" logic CheckFVG applies via its depth/penetration gate, applied
   // here as a hard invalidation instead since OB literature treats a
   // clean close-through as the block failing, not just weakening.
   //
   // Deliberately NOT added to any CoreCheck*() in ASE_SetupClassifier.mqh
   // this pass — ships as scored-but-optional (enhancer) evidence only.
   // There is no observation data yet to justify requiring it for any
   // archetype's core; see CHANGELOG_v4.0.0.md Addendum 6.
   //------------------------------------------------------------------
   ValidationResult CheckOrderBlock(ENUM_TRADE_DIRECTION dir, double price,
                                     const double &hi[], const double &lo[],
                                     const double &cl[], const double &op[],
                                     double atr)
   {
      ValidationResult r;
      r.passed = false; r.score = 0.0; r.reason = "No Order Block";

      int lookback = MathMax(3, InpOBLookback);

      for(int i = 2; i < lookback; i++)
      {
         // Same age-decay rationale as InpFVGMaxBars (see that input's
         // comment in ASE_Config.mqh) — an OB several hours old has had
         // ample time to be mitigated or invalidated already.
         if(InpOBMaxBars > 0 && i > InpOBMaxBars) break;

         if(dir == DIR_LONG)
         {
            bool obCandleBearish = cl[i] < op[i];
            if(!obCandleBearish) continue;

            double obTop = hi[i], obBottom = lo[i];
            if(obTop <= obBottom) continue;

            // The candle immediately after (more recent — index i-1) must
            // be a genuine bullish displacement that closes above the OB
            // candle's high. Without this, "last red candle before a
            // green one" fires constantly and means nothing.
            double dispBody = MathAbs(cl[i-1] - op[i-1]);
            bool   dispBull = cl[i-1] > op[i-1];
            if(!dispBull || dispBody < atr * InpOBDispMultiplier) continue;
            if(cl[i-1] <= obTop) continue;   // no BOS beyond the OB — not a confirmed block

            // Invalidation — any close between the displacement candle
            // and now that closed back below the zone means the block
            // already failed; don't offer a dead zone as evidence.
            bool invalidated = false;
            for(int k = i - 1; k >= 1; k--)
               if(cl[k] < obBottom) { invalidated = true; break; }
            if(invalidated) continue;

            // Must currently be trading back inside the zone — this is
            // the mitigation entry, not just "a block exists somewhere."
            if(price < obBottom || price > obTop) continue;

            r.passed = true;
            r.score  = 18.0 + (i <= 6 ? 3.0 : 0.0);
            r.reason = StringFormat("Bullish OB [%.5f-%.5f] bar=%d price=%.5f", obBottom, obTop, i, price);
            return r;
         }
         else if(dir == DIR_SHORT)
         {
            bool obCandleBullish = cl[i] > op[i];
            if(!obCandleBullish) continue;

            double obTop = hi[i], obBottom = lo[i];
            if(obTop <= obBottom) continue;

            double dispBody = MathAbs(cl[i-1] - op[i-1]);
            bool   dispBear = cl[i-1] < op[i-1];
            if(!dispBear || dispBody < atr * InpOBDispMultiplier) continue;
            if(cl[i-1] >= obBottom) continue;   // no BOS beyond the OB — not a confirmed block

            bool invalidated = false;
            for(int k = i - 1; k >= 1; k--)
               if(cl[k] > obTop) { invalidated = true; break; }
            if(invalidated) continue;

            if(price < obBottom || price > obTop) continue;

            r.passed = true;
            r.score  = 18.0 + (i <= 6 ? 3.0 : 0.0);
            r.reason = StringFormat("Bearish OB [%.5f-%.5f] bar=%d price=%.5f", obBottom, obTop, i, price);
            return r;
         }
      }
      return r;
   }

   //------------------------------------------------------------------
   // v4.0.1 — Kill Zone (discrete evidence). CASE_Time::IsKillZone() is
   // NOT new — it has existed since v3.7.0 and already feeds a
   // continuous session-quality SCORE via ASE_SessionEngine::
   // GetSessionScore() (10.0 inside a kill zone vs 9.5/8.0/7.0/0.0).
   // What's new here is only that this surfaces it as its own discrete,
   // DNA-tagged evidence item rather than an anonymous ingredient folded
   // into EVID_SESSION_QUALITY. Direction-agnostic — a kill zone is a
   // property of the clock, not the setup — so both directions receive
   // the same active/inactive read for a given bar, same convention
   // EVID_SESSION_QUALITY and EVID_VOLATILITY_STATE already use.
   //------------------------------------------------------------------
   ValidationResult CheckKillZone(ENUM_TRADE_DIRECTION dir)
   {
      ValidationResult r;
      r.passed = CASE_Time::IsKillZone();
      r.score  = r.passed ? 10.0 : 0.0;
      r.reason = r.passed ? "Inside ICT kill zone" : "Outside kill zone";
      return r;
   }

   //------------------------------------------------------------------
   // v4.0.1 — AMD phase (Accumulation / Manipulation / Distribution).
   // Genuinely new logic, not a re-identified existing check.
   //
   //   Accumulation — today's Asian-session (UTC) M15 high/low range.
   //   Manipulation — within the current kill zone, a swept high/low
   //                  BEYOND that range on the side OPPOSITE the setup
   //                  direction (the liquidity grab the AMD model
   //                  describes before the real move).
   //   Distribution — price currently trading back through the swept
   //                  level on the setup's actual direction.
   //
   // Only evaluated while CASE_Time::IsKillZone() is true: outside a
   // kill zone, "was there a sweep" isn't the AMD manipulation phase,
   // it's just ordinary liquidity evidence — EVID_LIQUIDITY_SWEEP
   // already covers that independently, this is not a duplicate of it.
   //
   // Known limitation, stated rather than silently assumed: does not
   // handle an Asian-session window configured to cross midnight UTC
   // (InpAsianEndHour/Min <= InpAsianStartHour/Min) — reports the
   // misconfiguration via r.reason instead of computing a wrong range.
   //------------------------------------------------------------------
   ValidationResult CheckAMDPhase(ENUM_TRADE_DIRECTION dir, double price)
   {
      ValidationResult r;
      r.passed = false; r.score = 0.0; r.reason = "No AMD phase";

      if(!CASE_Time::IsKillZone()) { r.reason = "Not in kill zone"; return r; }

      // Accumulation — today's Asian range, from today's UTC calendar date.
      // Safe to assume "today" here: kill zones (08:00+ UTC) always fall
      // after the Asian window (00:00-07:00 UTC default) on the SAME day.
      MqlDateTime dtNow;
      TimeToStruct(TimeGMT(), dtNow);
      MqlDateTime aStart = dtNow, aEnd = dtNow;
      aStart.hour = InpAsianStartHour; aStart.min = InpAsianStartMin; aStart.sec = 0;
      aEnd.hour   = InpAsianEndHour;   aEnd.min   = InpAsianEndMin;   aEnd.sec   = 0;
      datetime asianStart = StructToTime(aStart);
      datetime asianEnd   = StructToTime(aEnd);
      if(asianEnd <= asianStart)
      {
         r.reason = "Asian window misconfigured (end<=start) — midnight wraparound not supported";
         return r;
      }

      int shiftNewest = iBarShift(_Symbol, PERIOD_M15, asianEnd);
      int shiftOldest  = iBarShift(_Symbol, PERIOD_M15, asianStart);
      if(shiftOldest <= shiftNewest) { r.reason = "Insufficient Asian-session bar history"; return r; }

      int aCount = shiftOldest - shiftNewest + 1;
      double aHi[], aLo[];
      ArraySetAsSeries(aHi, true); ArraySetAsSeries(aLo, true);
      if(CopyHigh(_Symbol, PERIOD_M15, shiftNewest, aCount, aHi) < aCount) { r.reason = "Asian H buffer fail"; return r; }
      if(CopyLow( _Symbol, PERIOD_M15, shiftNewest, aCount, aLo) < aCount) { r.reason = "Asian L buffer fail"; return r; }

      double asianHigh = aHi[ArrayMaximum(aHi)];
      double asianLow  = aLo[ArrayMinimum(aLo)];
      if(asianHigh <= asianLow) { r.reason = "Degenerate Asian range"; return r; }

      // Manipulation — scan the kill-zone-so-far window for a sweep of the
      // Asian range opposite the setup direction. Reuses the standard
      // hi/lo/cl series convention (index 1 = last closed bar) already
      // established by CheckFVG/CheckDisplacement/CheckOrderBlock above.
      int kzLookback = MathMax(1, InpAMDLookbackBars);
      int needed = kzLookback + 1;
      double hi[], lo[];
      ArraySetAsSeries(hi, true); ArraySetAsSeries(lo, true);
      if(CopyHigh(_Symbol, PERIOD_M15, 0, needed, hi) < needed) { r.reason = "KZ H buffer fail"; return r; }
      if(CopyLow( _Symbol, PERIOD_M15, 0, needed, lo) < needed) { r.reason = "KZ L buffer fail"; return r; }

      bool sweptOpposite = false; int sweepBar = -1;
      for(int i = 1; i <= kzLookback; i++)
      {
         if(dir == DIR_LONG  && lo[i] < asianLow)  { sweptOpposite = true; sweepBar = i; break; }  // sell-side liquidity swept below Asian low
         if(dir == DIR_SHORT && hi[i] > asianHigh) { sweptOpposite = true; sweepBar = i; break; }  // buy-side liquidity swept above Asian high
      }
      if(!sweptOpposite)
      {
         r.reason = StringFormat("No %s-side Asian sweep yet [%.5f-%.5f]",
                                  dir == DIR_LONG ? "sell" : "buy", asianLow, asianHigh);
         return r;
      }

      // Distribution — price currently back through the swept level, on
      // the setup's actual direction.
      bool distributing = (dir == DIR_LONG) ? (price > asianLow) : (price < asianHigh);
      if(!distributing) { r.reason = "Swept but not yet distributing back through the range"; return r; }

      r.passed = true;
      r.score  = 12.0 + (sweepBar <= 2 ? 3.0 : 0.0);
      r.reason = StringFormat("AMD %s | Asian[%.5f-%.5f] swept bar=%d price=%.5f",
                               dir == DIR_LONG ? "LONG" : "SHORT", asianLow, asianHigh, sweepBar, price);
      return r;
   }

   //------------------------------------------------------------------
   // v4.0.1 — Macro correlation. Genuinely new signal CLASS for this
   // codebase, not just a new detector — every other Check* method in
   // this file (and every SymbolInfoDouble/CopyClose call anywhere in
   // Core/Utilities, confirmed by grep before writing this) reads only
   // _Symbol. This reads a SECOND symbol.
   //
   // Rationale: gold's dominant macro driver is real yields/the US
   // dollar, not its own chart structure — every other evidence type in
   // this engine is symbol-internal and blind to that. Standard (not
   // universal — regimes exist where it decouples) assumption: gold and
   // a USD-index proxy move inversely. A LONG gold setup is corroborated
   // by the correlation symbol showing recent downward momentum; a SHORT
   // setup by upward momentum. Measured as simple rate-of-change over
   // InpMacroCorrLookbackBars M15 bars — deliberately the simplest
   // possible measure, not a rolling correlation coefficient, so the
   // first version of this evidence type is easy to audit and reason
   // about against real data before anything more elaborate is built on
   // top of it.
   //
   // Degrades to permanently inactive, never an error, if
   // m_corrSymbolValid is false (symbol unavailable on this broker — see
   // Initialize()) or the buffer read fails for any other reason.
   //------------------------------------------------------------------
   ValidationResult CheckMacroCorrelation(ENUM_TRADE_DIRECTION dir)
   {
      ValidationResult r;
      r.passed = false; r.score = 0.0; r.reason = "No macro correlation evidence";

      if(!InpEnableMacroCorrelation) { r.reason = "Macro correlation disabled"; return r; }
      if(!m_corrSymbolValid) { r.reason = StringFormat("Correlation symbol '%s' unavailable", InpMacroCorrSymbol); return r; }
      if(dir == DIR_NONE) return r;

      int needed = MathMax(3, InpMacroCorrLookbackBars) + 1;
      double cl[];
      ArraySetAsSeries(cl, true);
      if(CopyClose(InpMacroCorrSymbol, PERIOD_M15, 0, needed, cl) < needed)
      {
         r.reason = StringFormat("'%s' buffer fail", InpMacroCorrSymbol);
         return r;
      }

      double older  = cl[needed - 1];
      double recent = cl[1];
      if(older <= 0.0) { r.reason = StringFormat("Invalid '%s' price", InpMacroCorrSymbol); return r; }
      double roc = (recent - older) / older;

      bool aligned = (dir == DIR_LONG)  ? (roc <= -InpMacroCorrROCThreshold)
                   : (dir == DIR_SHORT) ? (roc >=  InpMacroCorrROCThreshold)
                   : false;
      if(!aligned)
      {
         r.reason = StringFormat("%s ROC=%.4f%% not aligned with %s gold setup",
                                  InpMacroCorrSymbol, roc * 100, dir == DIR_LONG ? "LONG" : "SHORT");
         return r;
      }

      r.passed = true;
      r.score  = 10.0 + (MathAbs(roc) >= InpMacroCorrROCThreshold * 2 ? 3.0 : 0.0);
      r.reason = StringFormat("%s ROC=%.4f%% aligned with %s gold setup (inverse correlation)",
                               InpMacroCorrSymbol, roc * 100, dir == DIR_LONG ? "LONG" : "SHORT");
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
