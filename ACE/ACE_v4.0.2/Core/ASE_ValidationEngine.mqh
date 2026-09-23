#ifndef ASE_VALIDATIONENGINE_MQH
#define ASE_VALIDATIONENGINE_MQH
#include "../Models/ASE_Config.mqh"
#include "../Utilities/ASE_Broker.mqh"
//+------------------------------------------------------------------+
//| ASE v3.4.3 — Pre-Entry Validation                                |
//| v3.3.0 additions (Area D — Live Survivability):                  |
//|   IsSpreadSpiked()  — detects abnormal spread during open trade  |
//|   GetSpreadNorm()   — spread as fraction of ATR                  |
//| v3.4.3 fix:                                                      |
//|   GetSpreadScore() now uses InpSpreadBaseline to normalise       |
//|   spread against the achievable range [baseline, maxSpread]      |
//|   rather than [0, maxSpread]. Instruments like GOLD on XM never  |
//|   produce spreads below 35–40 pts, so the old formula was        |
//|   permanently capping the spread score at 2–4 out of 10 even    |
//|   when conditions were as tight as they ever get for that pair.  |
//|   Default baseline = 0 → identical to previous behaviour.        |
//+------------------------------------------------------------------+
class CASE_ValidationEngine
{
public:
   bool SpreadAcceptable(double maxSpread)
   {
      return CASE_Broker::IsSpreadOK(maxSpread);
   }

   //------------------------------------------------------------------
   // GetSpreadScore — spread component of composite score (0–10).
   //
   // Original formula:
   //   10 * (1 - spread / maxSpread)
   //   → score=10 requires spread=0 (impossible on GOLD/XM)
   //   → at spread=55 with max=70: score = 2.14
   //
   // v3.4.3 formula (when InpSpreadBaseline > 0):
   //   10 * (1 - (spread - baseline) / (maxSpread - baseline))
   //   → score=10 when spread <= baseline (best achievable)
   //   → score=0  when spread = maxSpread (gate threshold)
   //   → at spread=55, baseline=35, max=70: score = 5.71
   //
   // Backward compatibility: InpSpreadBaseline = 0 (default) produces
   // exactly the original formula — no change for existing configs.
   //
   // Safety guards:
   //   spread > maxSpread   → 0.0  (gate-blocked, no score)
   //   spread < baseline    → 10.0 (better than best — full score)
   //   baseline >= maxSpread → original formula (degenerate config)
   //------------------------------------------------------------------
   double GetSpreadScore(double maxSpread)
   {
      double spread = CASE_Broker::GetSpread();
      if(spread <= 0)        return 0.0;
      if(spread > maxSpread) return 0.0;

      // Clamp baseline strictly below maxSpread to avoid div-by-zero
      double baseline = MathMin(InpSpreadBaseline, maxSpread - 1.0);
      baseline        = MathMax(baseline, 0.0);

      // Print once per session to confirm the effective scoring range
      static bool s_printed = false;
      if(!s_printed)
      {
         s_printed = true;
         Print(StringFormat(
            "[VALID] SpreadScore range: baseline=%.0f max=%.0f "
            "| spread=%.0f at tight → score=%.2f at typical",
            baseline, maxSpread, 55.0,
            (baseline > 0)
               ? 10.0 * (1.0 - MathMax(55.0 - baseline, 0.0) / (maxSpread - baseline))
               : 10.0 * (1.0 - 55.0 / maxSpread)));
      }

      if(baseline > 0 && spread <= baseline) return 10.0;

      double range    = maxSpread - baseline;
      double adjusted = spread   - baseline;
      return 10.0 * (1.0 - (adjusted / range));
   }

   bool HasAdequateMargin(double lots)
   {
      return CASE_Broker::HasFreeMargin(lots);
   }

   bool IsSymbolTradeable()
   {
      return (bool)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE);
   }

   //──────────────────────────────────────────────────────────────────
   // Area D — Spread spike detection
   //
   // Returns true if current spread exceeds entrySpreadPts multiplied
   // by InpSpreadSpikeMultiplier. When true, trailing stop modifications
   // are skipped — the artificially wide spread should not trigger SL.
   //
   // entrySpreadPts = 0 disables the check (e.g. if not yet captured).
   //──────────────────────────────────────────────────────────────────
   bool IsSpreadSpiked(double entrySpreadPts) const
   {
      if(entrySpreadPts <= 0) return false;
      double currentSpread = CASE_Broker::GetSpread();
      return (currentSpread > entrySpreadPts * InpSpreadSpikeMultiplier);
   }

   // Normalised spread: current spread / ATR.
   // Useful for scale-independent anomaly logging.
   // < 0.05 = tight (GOLD, majors), > 0.30 = abnormal.
   double GetSpreadNorm(double atrValue) const
   {
      if(atrValue <= 0) return 0.0;
      return CASE_Broker::GetSpread() / atrValue;
   }
};
#endif // ASE_VALIDATIONENGINE_MQH
