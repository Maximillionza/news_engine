#ifndef ASE_SCORINGENGINE_MQH
#define ASE_SCORINGENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Weighted Scoring Engine                                 |
//| Phase 1 additions:                                               |
//|   - All component scores normalised to 0–100 output              |
//|   - Declared weight % per spec target (HTF 30, Setup 25,         |
//|     Liquidity 20, Volatility 15, Execution 10)                   |
//|   - volatility field now contributes (was always 0 before)       |
//|   - Describe() shows normalised total and raw components          |
//|                                                                  |
//| v3.7.0 — Per-component minimum floors (Task 08):                 |
//|   InpMinBiasScore  — h4Bias must meet this raw floor             |
//|   InpMinSetupScore — m15Setup must meet this raw floor           |
//|   Both default 0 (disabled) for backward compatibility.          |
//|   When a floor is breached, Validate() returns false immediately  |
//|   and populates card.total with the partial score for logging.   |
//|   This makes the scorer eliminative for the alpha components      |
//|   rather than fully additive — execution context (session,        |
//|   spread, volatility) can no longer compensate for a weak signal. |
//|                                                                  |
//| RAW SCORE CEILINGS (inputs from each engine):                    |
//|   h4Bias    max 10   → weight ~12% (v3.14.9: reduced from 30)   |
//|   m15Setup  max 25   → weight 25%                                |
//|   liquidity max 15   → weight 20% (proxy until Phase 2 upgrade)  |
//|   volatility max 15  → weight 15%                                |
//|   session   max 10  ─┐                                           |
//|   spread    max 10  ─┘ combined → weight 10%                     |
//|                                                                  |
//| NORMALISATION:                                                   |
//|   raw_max = 10+25+15+15+10+10 = 85  (v3.14.9: h4Bias 30→10)    |
//|   normalised = (raw_total / 85) * 100                            |
//|   InpScoreThreshold is compared against the normalised value.    |
//|   Default threshold 65 = 65/100 normalised = strong signal.      |
//|                                                                  |
//| v3.14.9 Fix 10 — h4Bias max 30→10:                              |
//|   H4 now contributes bias context only (max 10 pts) rather than  |
//|   being a primary conviction driver (max 30 pts). Raw max drops  |
//|   from 105 to 85. Score thresholds unchanged — the normalisation  |
//|   base change preserves their semantics at 0-100 output scale.   |
//+------------------------------------------------------------------+

static const double ASE_SCORE_RAW_MAX = 85.0;   // v3.14.9: h4Bias max 30→10, raw max 105→85

class CASE_ScoringEngine
{
public:
   // Returns true if:
   //   (a) all active component floors are met, AND
   //   (b) normalised total >= threshold
   // card.total is always populated (partial score on floor breach)
   // so LogBlock() downstream shows the actual component values.
   bool Validate(ScoreCard &card, double threshold)
   {
      card.total = Normalise(
           card.h4Bias
         + card.m15Setup
         + card.m1Trigger
         + card.liquidity
         + card.volatility
         + card.session
         + card.spread);

      // v3.7.0 — component floor gates.
      // Checked after total is computed so Describe() always shows the
      // full scorecard even on a floor-triggered rejection.
      if(InpMinBiasScore > 0 && card.h4Bias < InpMinBiasScore)
         return false;

      if(InpMinSetupScore > 0 && card.m15Setup < InpMinSetupScore)
         return false;

      return (card.total >= threshold);
   }

   // Normalise a raw sum to 0–100
   double Normalise(double rawSum)
   {
      if(ASE_SCORE_RAW_MAX <= 0) return 0.0;
      return CASE_Math_Clamp((rawSum / ASE_SCORE_RAW_MAX) * 100.0, 0.0, 100.0);
   }

   string Describe(const ScoreCard &card)
   {
      // v3.7.0 — flag floor breach in description for log clarity
      string biasFlag  = (InpMinBiasScore  > 0 && card.h4Bias  < InpMinBiasScore)
                         ? StringFormat("[HTF<%.0f!]", InpMinBiasScore)  : "";
      string setupFlag = (InpMinSetupScore > 0 && card.m15Setup < InpMinSetupScore)
                         ? StringFormat("[Setup<%.0f!]", InpMinSetupScore) : "";

      return StringFormat(
         "Score=%.1f/100%s%s | HTF=%.0f Setup=%.0f Trig=%.0f Liq=%.0f Vol=%.0f Sess=%.0f Sprd=%.0f",
         card.total, biasFlag, setupFlag,
         card.h4Bias, card.m15Setup, card.m1Trigger,
         card.liquidity, card.volatility, card.session, card.spread);
   }

private:
   // Inline clamp — avoids header dependency inside this file
   double CASE_Math_Clamp(double v, double lo, double hi)
   {
      if(v < lo) return lo;
      if(v > hi) return hi;
      return v;
   }
};
#endif // ASE_SCORINGENGINE_MQH
