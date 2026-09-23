#ifndef ASE_REGIMEPROFILE_MQH
#define ASE_REGIMEPROFILE_MQH
#include "../Models/ASE_Enums.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3.14.0 — Regime Profile Engine                              |
//|                                                                  |
//| Holds per-regime parameter sets loaded once per H1 bar after     |
//| the regime gate clears. Every downstream engine reads from the   |
//| active profile (m_profile in StateMachine) instead of global     |
//| Inp* values for the tuneable parameters.                         |
//|                                                                  |
//| ZERO BEHAVIOUR CHANGE ON FIRST DEPLOY:                          |
//| All default values in ASE_Config.mqh match the equivalent        |
//| global Inp* values used in v3.13.0. Run a backtest over the same |
//| date range as v3.13.0 and confirm trade count, win rate, and     |
//| average score are identical before tuning any per-regime values. |
//|                                                                  |
//| TUNING ORDER (after parity confirmed):                           |
//|   1. COMPRESSION threshold → raise to 75 (tighter signal filter) |
//|   2. RANGING SL multiplier → 1.5× (wider SL for oscillation)    |
//|   3. MANIPULATION liq mode → SWEEP_ONLY (stop-hunt confirmation) |
//|   4. All others — data-driven after 20+ trades per regime        |
//|                                                                  |
//| HIGH_VOL has no profile — it is always a hard block from the     |
//| regime gate and never reaches LoadProfile().                     |
//| DEAD has no profile — pipeline blocks before LoadProfile().      |
//+------------------------------------------------------------------+

// Liquidity mode per regime — maps to the existing three detection
// branches inside LiquidityEngine.DetectSweep().
enum ENUM_LIQ_MODE
{
   LIQ_STANDARD   = 0,   // regime-aware routing (default — same as current)
   LIQ_TIGHT       = 1,   // TREND mode forced regardless of regime
   LIQ_SWEEP_ONLY  = 2    // SWEEP mode forced — requires equal-highs/lows pool
};

struct RegimeProfile
{
   // Risk parameters
   double slMultiplier;      // ATR × this = SL distance
   double slCap;             // hard SL point ceiling (0 = no cap)

   // Score gate
   double minScoreThreshold; // composite score must reach this (0–100)

   // TP mode (mirrors ENUM_TP_MODE — stored as int for ZeroMemory safety)
   int    tp1Mode;           // ENUM_TP_MODE value for TP1
   int    tp2Mode;           // ENUM_TP_MODE value for TP2

   // Liquidity gate
   ENUM_LIQ_MODE liqMode;   // detection mode passed to DetectSweep()

   // Spread
   int    maxSpread;         // per-regime spread ceiling (points)

   // Bias confidence (minimum M15 bars aligning before bias is accepted)
   // Mirrors InpBiasReEvalBars in meaning — higher = stricter filter
   int    biasConfidenceMin;

   // v3.14.3 — Counter-trend setup quality gates (TRENDING regime only).
   // Applied when H1 BOS direction opposes the committed H4 direction.
   //
   // counterTrendDispMultiplier: CheckDisplacement() ATR body threshold.
   //   0.60 = parity. 0.85 = default. 1.0 = strict.
   //
   // counterTrendFVGMinGap: CheckFVG() minimum gap size (× ATR).
   //   0.30 = parity (current standard). 0.50 = default. 0.70 = strict.
   //
   // counterTrendFVGMaxDepth: CheckFVG() penetration ceiling.
   //   0.70 = parity (current standard). 0.50 = default. 0.30 = strict.
   //
   // All three are inert in RANGING, COMPRESSION, MANIPULATION.
   double counterTrendDispMultiplier;
   double counterTrendFVGMinGap;
   double counterTrendFVGMaxDepth;

   // Profile label — for logging
   string label;
};

//------------------------------------------------------------------
// LoadProfile()
// Returns the RegimeProfile for the active operational regime.
// Called from StateMachine after regime gate (DEAD/HIGH_VOL already
// blocked), so only TRENDING, RANGING, COMPRESSION, MANIPULATION
// need profiles.
//
// DEFAULTS match current v3.13.0 global Inp* values exactly:
//   slMultiplier    → InpATRMultiplierSL (COMPRESSION) / InpATRMultiplierSL_Wide (others)
//   slCap           → InpATRSLCap
//   minScoreThreshold → InpScoreThreshold
//   tp1Mode         → InpTP1Mode
//   tp2Mode         → InpTP2Mode
//   liqMode         → LIQ_STANDARD (regime-aware routing unchanged)
//   maxSpread       → InpMaxSpread
//   biasConfidenceMin → InpBiasReEvalBars
//------------------------------------------------------------------
RegimeProfile LoadProfile(ENUM_MARKET_REGIME regime)
{
   RegimeProfile p;

   switch(regime)
   {
      //──────────────────────────────────────────────────────────────
      case REGIME_TRENDING:
         p.slMultiplier      = InpSL_Trending;
         p.slCap             = InpSLCap_Trending;
         p.minScoreThreshold = InpScore_Trending;
         p.tp1Mode           = (int)InpTP1Mode_Trending;
         p.tp2Mode           = (int)InpTP2Mode_Trending;
         p.liqMode           = LIQ_STANDARD;
         p.maxSpread         = InpSpread_Trending;
         p.biasConfidenceMin = InpBiasConf_Trending;
         p.counterTrendDispMultiplier = InpCTDispMultiplier;
         p.counterTrendFVGMinGap      = InpCTFVGMinGap;
         p.counterTrendFVGMaxDepth    = InpCTFVGMaxDepth;
         p.label             = "Trending";
         break;

      //──────────────────────────────────────────────────────────────
      case REGIME_RANGING:
         p.slMultiplier      = InpSL_Ranging;
         p.slCap             = InpSLCap_Ranging;
         p.minScoreThreshold = InpScore_Ranging;
         p.tp1Mode           = (int)InpTP1Mode_Ranging;
         p.tp2Mode           = (int)InpTP2Mode_Ranging;
         p.liqMode           = LIQ_STANDARD;
         p.maxSpread         = InpSpread_Ranging;
         p.biasConfidenceMin = InpBiasConf_Ranging;
         p.counterTrendDispMultiplier = 0.60;   // parity — gate inactive outside TRENDING
         p.counterTrendFVGMinGap      = 0.30;   // parity
         p.counterTrendFVGMaxDepth    = 0.70;   // parity
         p.label             = "Ranging";
         break;

      //──────────────────────────────────────────────────────────────
      case REGIME_COMPRESSION:
         p.slMultiplier      = InpSL_Compression;
         p.slCap             = InpSLCap_Compression;
         p.minScoreThreshold = InpScore_Compression;
         p.tp1Mode           = (int)InpTP1Mode_Compression;
         p.tp2Mode           = (int)InpTP2Mode_Compression;
         p.liqMode           = LIQ_STANDARD;
         p.maxSpread         = InpSpread_Compression;
         p.biasConfidenceMin = InpBiasConf_Compression;
         p.counterTrendDispMultiplier = 0.60;   // parity — gate inactive outside TRENDING
         p.counterTrendFVGMinGap      = 0.30;   // parity
         p.counterTrendFVGMaxDepth    = 0.70;   // parity
         p.label             = "Compression";
         break;

      //──────────────────────────────────────────────────────────────
      case REGIME_MANIPULATION:
         p.slMultiplier      = InpSL_Manipulation;
         p.slCap             = InpSLCap_Manipulation;
         p.minScoreThreshold = InpScore_Manipulation;
         p.tp1Mode           = (int)InpTP1Mode_Manipulation;
         p.tp2Mode           = (int)InpTP2Mode_Manipulation;
         p.liqMode           = LIQ_STANDARD;
         p.maxSpread         = InpSpread_Manipulation;
         p.biasConfidenceMin = InpBiasConf_Manipulation;
         p.counterTrendDispMultiplier = 0.60;   // parity — gate inactive outside TRENDING
         p.counterTrendFVGMinGap      = 0.30;   // parity
         p.counterTrendFVGMaxDepth    = 0.70;   // parity
         p.label             = "Manipulation";
         break;

      //──────────────────────────────────────────────────────────────
      default:
         // REGIME_UNKNOWN / REGIME_DEAD / REGIME_HIGH_VOL — should
         // never reach here (blocked earlier in pipeline). Return
         // conservative defaults so the pipeline doesn't crash.
         p.slMultiplier      = InpATRMultiplierSL_Wide;
         p.slCap             = InpATRSLCap;
         p.minScoreThreshold = InpScoreThreshold;
         p.tp1Mode           = (int)InpTP1Mode;
         p.tp2Mode           = (int)InpTP2Mode;
         p.liqMode           = LIQ_STANDARD;
         p.maxSpread         = InpMaxSpread;
         p.biasConfidenceMin = InpBiasReEvalBars;
         p.counterTrendDispMultiplier = 0.60;   // parity
         p.counterTrendFVGMinGap      = 0.30;   // parity
         p.counterTrendFVGMaxDepth    = 0.70;   // parity
         p.label             = "Default";
         break;
   }

   return p;
}
#endif // ASE_REGIMEPROFILE_MQH
