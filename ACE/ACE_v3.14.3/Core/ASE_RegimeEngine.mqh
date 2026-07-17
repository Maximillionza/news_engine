#ifndef ASE_REGIMEENGINE_MQH
#define ASE_REGIMEENGINE_MQH
#include "../Models/ASE_Enums.mqh"
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3.13.0 — Market Regime Engine                               |
//|                                                                  |
//| v3.13.0 — H1-primary regime with D1 macro ceiling:              |
//|                                                                  |
//|   PRIMARY DATA (H1):                                             |
//|     H1 ATR(14)  — operational volatility measure.               |
//|     H1 OHLC ×12 — candle body/wick ratios for MANIPULATION       |
//|                   detection and directional persistence.          |
//|     H4 EMA(fast/slow) — macro trend direction context for         |
//|                   TRENDING confirmation (unchanged from v3.12).  |
//|                                                                  |
//|   MACRO CEILING (D1, cached once per day):                       |
//|     D1 ATR(1) ×20 — classifies into ENUM_MACRO_REGIME.          |
//|     Evaluated in GetMacroRegime() and cached in RegimeState.     |
//|     Ceiling gate applied inside GetState():                      |
//|       MACRO_HIGH_VOL    → override regime to REGIME_HIGH_VOL     |
//|       MACRO_CONTRACTION → cap REGIME_TRENDING to REGIME_RANGING  |
//|                                                                  |
//|   STABILITY RULE:                                                |
//|     Regime only commits after 2 consecutive H1 bars classify      |
//|     identically. A single spike H1 candle does NOT flip the      |
//|     active regime. Pending confirmation logged as:               |
//|       [REGIME] Pending: HIGH_VOL (1/2)                          |
//|     Second consecutive confirmation:                             |
//|       [REGIME] Confirmed: HIGH_VOL (was Ranging)                |
//|     If consecutive candles disagree, pending resets and held      |
//|     regime is retained.                                          |
//|                                                                  |
//|   FIRING RATE:                                                   |
//|     GetState() is throttled to H1 bar closes inside              |
//|     ProcessHTF() via the _lastRegimeBar static.                  |
//|     GetMacroRegime() is called once per day at ExecuteDailyReset |
//|     and cached into m_ctx.regimeAtEntry.macroRegime.             |
//|                                                                  |
//|   COHERENCE:                                                     |
//|     H1 ATR and StructureEngine H1 BOS now share the same TF.    |
//|     A H1 BOS confirmation and a TRENDING regime classification    |
//|     both read from the same H1 candle, eliminating the           |
//|     M15-regime vs H1-structure mismatch present in v3.12.        |
//|                                                                  |
//| Previous primary (M15):                                          |
//|   m_atrM15Handle — retired. H1 ATR replaces it.                 |
//|   M15 OHLC reads in GetState() — retired. H1 OHLC replaces.    |
//|   D1 handle retained unchanged (ADR baseline → ceiling gate).   |
//+------------------------------------------------------------------+

#define REGIME_ADR_LOOKBACK    20
#define REGIME_PERSIST_BARS    10
#define REGIME_DISP_BARS       10
#define REGIME_STABILITY_COUNT  2   // consecutive H1 bars required to confirm a regime change

class CASE_RegimeEngine
{
private:
   int m_atrH1Handle;    // v3.13.0: H1 ATR — replaces m_atrM15Handle
   int m_atrD1Handle;    // D1 ATR — unchanged; now used for macro ceiling classification
   int m_atrH4Handle;    // v3.14.3: H4 ATR — denominator for EMA separation gate
   int m_emaFastHandle;  // H4 EMA fast — macro trend direction context
   int m_emaSlowHandle;  // H4 EMA slow — macro trend direction context

   // v3.13.0 — Stability rule state
   ENUM_MARKET_REGIME m_activeRegime;   // currently committed regime (held until confirmed flip)
   ENUM_MARKET_REGIME m_pendingRegime;  // candidate regime awaiting 2nd confirmation
   int                m_pendingCount;   // how many consecutive bars have agreed on m_pendingRegime

   // v3.13.0 — Cached D1 macro ceiling (written by GetMacroRegime(), read by GetState())
   ENUM_MACRO_REGIME  m_cachedMacro;

public:
   CASE_RegimeEngine() : m_atrH1Handle(INVALID_HANDLE),
                         m_atrD1Handle(INVALID_HANDLE),
                         m_atrH4Handle(INVALID_HANDLE),
                         m_emaFastHandle(INVALID_HANDLE),
                         m_emaSlowHandle(INVALID_HANDLE),
                         m_activeRegime(REGIME_UNKNOWN),
                         m_pendingRegime(REGIME_UNKNOWN),
                         m_pendingCount(0),
                         m_cachedMacro(MACRO_UNKNOWN) {}

   bool Initialize()
   {
      m_atrH1Handle   = iATR(_Symbol, PERIOD_H1,  14);   // v3.13.0: H1 primary
      m_atrD1Handle   = iATR(_Symbol, PERIOD_D1,   1);   // D1 ceiling baseline
      m_atrH4Handle   = iATR(_Symbol, PERIOD_H4, 14);   // v3.14.3: H4 ATR for EMA sep gate
      m_emaFastHandle = iMA(_Symbol, PERIOD_H4, InpH4FastEMA, 0, MODE_EMA, PRICE_CLOSE);
      m_emaSlowHandle = iMA(_Symbol, PERIOD_H4, InpH4SlowEMA, 0, MODE_EMA, PRICE_CLOSE);

      if(m_atrH1Handle   == INVALID_HANDLE) { Print("[REGIME] INIT FAIL: H1 ATR handle");   return false; }
      if(m_atrD1Handle   == INVALID_HANDLE) { Print("[REGIME] INIT FAIL: D1 ATR handle");   return false; }
      if(m_atrH4Handle   == INVALID_HANDLE) { Print("[REGIME] INIT FAIL: H4 ATR handle");   return false; }
      if(m_emaFastHandle == INVALID_HANDLE) { Print("[REGIME] INIT FAIL: H4 fast EMA");     return false; }
      if(m_emaSlowHandle == INVALID_HANDLE) { Print("[REGIME] INIT FAIL: H4 slow EMA");     return false; }
      return true;
   }

   void Deinitialize()
   {
      if(m_atrH1Handle   != INVALID_HANDLE) IndicatorRelease(m_atrH1Handle);
      if(m_atrD1Handle   != INVALID_HANDLE) IndicatorRelease(m_atrD1Handle);
      if(m_atrH4Handle   != INVALID_HANDLE) IndicatorRelease(m_atrH4Handle);
      if(m_emaFastHandle != INVALID_HANDLE) IndicatorRelease(m_emaFastHandle);
      if(m_emaSlowHandle != INVALID_HANDLE) IndicatorRelease(m_emaSlowHandle);
   }

   //------------------------------------------------------------------
   // v3.13.0 — GetMacroRegime()
   // Classifies the D1 ATR vs its 20-day average into ENUM_MACRO_REGIME.
   // Called ONCE per day from ExecuteDailyReset() in StateMachine.
   // Result cached in m_cachedMacro and written into RegimeState.macroRegime
   // so GetState() can apply the ceiling without re-reading 20 D1 bars.
   //
   // Thresholds (same ratio logic as existing adrExpansion scalar):
   //   > 1.8× avg → MACRO_HIGH_VOL    (hard block ceiling)
   //   > 1.2× avg → MACRO_EXPANSION   (H1 runs freely, TRENDING allowed)
   //   > 0.8× avg → MACRO_NEUTRAL     (all regimes allowed)
   //   ≤ 0.8× avg → MACRO_CONTRACTION (TRENDING capped to RANGING)
   //------------------------------------------------------------------
   ENUM_MACRO_REGIME GetMacroRegime()
   {
      double atrD1[];
      ArraySetAsSeries(atrD1, true);

      // Use bar[1..20] — last 20 CLOSED D1 bars (skip current incomplete bar)
      if(CopyBuffer(m_atrD1Handle, 0, 1, REGIME_ADR_LOOKBACK, atrD1) < REGIME_ADR_LOOKBACK)
      {
         Print("[REGIME] GetMacroRegime: D1 ATR buffer fail — retaining MACRO_NEUTRAL");
         m_cachedMacro = MACRO_NEUTRAL;
         return m_cachedMacro;
      }

      double adrAvg = 0.0;
      for(int i = 0; i < REGIME_ADR_LOOKBACK; i++) adrAvg += atrD1[i];
      adrAvg /= REGIME_ADR_LOOKBACK;

      if(adrAvg <= 0)
      {
         m_cachedMacro = MACRO_NEUTRAL;
         return m_cachedMacro;
      }

      // today's D1 ATR = bar[0] of the D1 series (current day, may be incomplete)
      // Use bar[1] (last closed D1) for a clean read
      double todayD1 = atrD1[0];   // [0] in series = most recent closed day
      double ratio   = todayD1 / adrAvg;

      ENUM_MACRO_REGIME result;
      if     (ratio > 1.80) result = MACRO_HIGH_VOL;
      else if(ratio > 1.20) result = MACRO_EXPANSION;
      else if(ratio > 0.80) result = MACRO_NEUTRAL;
      else                  result = MACRO_CONTRACTION;

      Print(StringFormat("[REGIME] Macro ceiling: %s | D1_ATR=%.5f | 20d_avg=%.5f | ratio=%.2f",
            MacroRegimeName(result), todayD1, adrAvg, ratio));

      m_cachedMacro = result;
      return m_cachedMacro;
   }

   //------------------------------------------------------------------
   // v3.13.0 — GetState()
   // H1-primary regime classification with stability rule.
   // Called once per H1 bar (throttled by _lastRegimeBar in ProcessHTF).
   //
   // STABILITY RULE:
   //   Raw classification stored in candidateRegime.
   //   If candidateRegime == m_pendingRegime → m_pendingCount++
   //   If m_pendingCount >= REGIME_STABILITY_COUNT → commit to m_activeRegime
   //   If candidateRegime != m_pendingRegime → reset pending, hold m_activeRegime
   //   On warmup (m_activeRegime == REGIME_UNKNOWN) → commit immediately (no hold)
   //
   // CEILING GATE (applied after stability rule):
   //   m_cachedMacro == MACRO_HIGH_VOL    → override to REGIME_HIGH_VOL
   //   m_cachedMacro == MACRO_CONTRACTION → cap REGIME_TRENDING → REGIME_RANGING
   //------------------------------------------------------------------
   RegimeState GetState()
   {
      RegimeState s;
      ZeroMemory(s);
      s.regime      = m_activeRegime;   // default: return last committed regime
      s.macroRegime = m_cachedMacro;

      // ── H1 ATR (primary volatility measure) ──────────────────────
      double atrH1[];
      ArraySetAsSeries(atrH1, true);
      // Read 20 closed H1 bars (bar[1..20]) — skip incomplete current bar
      if(CopyBuffer(m_atrH1Handle, 0, 1, 20, atrH1) < 20)
      {
         Print("[REGIME] GetState: H1 ATR buffer fail — holding active regime");
         return s;
      }

      double atrNow = atrH1[0];   // most recent closed H1 bar ATR
      double atrAvg = 0.0;
      for(int i = 0; i < 20; i++) atrAvg += atrH1[i];
      atrAvg /= 20.0;
      s.atr = atrNow;

      // adrExpansion retained for downstream logging compatibility
      // Uses D1 20-bar average from cached macro (no re-read of D1 buffers)
      // Approximate ratio: H1 ATR vs expected H1 contribution of daily range
      s.adrExpansion = (atrAvg > 0) ? atrNow / atrAvg : 1.0;

      // ── H4 EMA — macro trend direction (unchanged from v3.12) ────
      double fast[], slow[];
      ArraySetAsSeries(fast, true);
      ArraySetAsSeries(slow, true);
      if(CopyBuffer(m_emaFastHandle, 0, 0, 3, fast) < 3) { return s; }
      if(CopyBuffer(m_emaSlowHandle, 0, 0, 3, slow) < 3) { return s; }
      bool macroLong = fast[0] > slow[0];
      s.trendSlope   = fast[0] - fast[2];

      // v3.14.3 — H4 EMA separation and H4 ATR for counter-trend setup gate.
      // Both written to RegimeState so ProcessSetup() can forward them to
      // CheckFVG() and CheckDisplacement() without re-reading indicator buffers.
      s.h4EMASep = MathAbs(fast[0] - slow[0]);
      double atrH4[];
      ArraySetAsSeries(atrH4, true);
      if(CopyBuffer(m_atrH4Handle, 0, 1, 1, atrH4) >= 1)
         s.h4ATR = atrH4[0];
      else
      {
         Print("[REGIME] GetState: H4 ATR buffer fail — h4ATR=0 (gate inactive this bar)");
         s.h4ATR = 0.0;   // 0.0 causes sep/ATR ratio = 0 → gate inactive safely
      }

      // ── H1 OHLC candle metrics ────────────────────────────────────
      // Closed bars only: CopyXxx with start=1 (skip current incomplete bar)
      double hi[], lo[], cl[], op[];
      ArraySetAsSeries(hi, true); ArraySetAsSeries(lo, true);
      ArraySetAsSeries(cl, true); ArraySetAsSeries(op, true);
      int needed = MathMax(REGIME_PERSIST_BARS, REGIME_DISP_BARS) + 2;
      if(CopyHigh( _Symbol, PERIOD_H1, 1, needed, hi) < needed) { return s; }
      if(CopyLow(  _Symbol, PERIOD_H1, 1, needed, lo) < needed) { return s; }
      if(CopyClose(_Symbol, PERIOD_H1, 1, needed, cl) < needed) { return s; }
      if(CopyOpen( _Symbol, PERIOD_H1, 1, needed, op) < needed) { return s; }

      // Body efficiency — how directional each candle is
      double sumBodyRatio = 0.0;
      for(int i = 0; i < REGIME_DISP_BARS; i++)
      {
         double body  = MathAbs(cl[i] - op[i]);
         double range = hi[i] - lo[i];
         sumBodyRatio += (range > 0) ? body / range : 0.5;
      }
      double dispEff = sumBodyRatio / REGIME_DISP_BARS;

      // Wick ratio — MANIPULATION detection on H1 (stop-hunt wicks are
      // single H1 candles; cleaner signal than M15 where they fragment)
      double sumWickRatio = 0.0;
      for(int i = 0; i < 5; i++)
      {
         double body      = MathAbs(cl[i] - op[i]);
         double upperWick = hi[i] - MathMax(cl[i], op[i]);
         double lowerWick = MathMin(cl[i], op[i]) - lo[i];
         double totalWick = upperWick + lowerWick;
         sumWickRatio    += (body > _Point) ? totalWick / body : 2.0;
      }
      s.wickRatio = sumWickRatio / 5.0;

      // Directional persistence — bars consistent with H4 macro direction
      int persist = 0;
      for(int i = 0; i < REGIME_PERSIST_BARS; i++)
      {
         bool barLong = cl[i] > op[i];
         if((macroLong && barLong) || (!macroLong && !barLong))
            persist++;
         else
            break;
      }
      double persistScore = (double)persist / REGIME_PERSIST_BARS;

      // ── Raw classification (H1 thresholds) ───────────────────────
      // Thresholds calibrated for H1 ATR on XAUUSD M15 context.
      // H1 ATR at 0.2× avg = essentially flat (DEAD)
      // Wick/body > 2.5 + low dispEff = stop-hunt pattern (MANIPULATION)
      // H1 ATR > 1.8× avg = volatility spike (HIGH_VOL)
      // H1 ATR < 0.65× avg + low dispEff = compressed range (COMPRESSION)
      // persistScore ≥ 0.5 + good dispEff + EMA separation = TRENDING
      // Otherwise RANGING (expanded but not trending)
      ENUM_MARKET_REGIME candidate;

      if(atrNow < _Point * 5 || atrNow < atrAvg * 0.2)
         candidate = REGIME_DEAD;
      else if(s.wickRatio > 2.5 && dispEff < 0.4)
         candidate = REGIME_MANIPULATION;
      else if(atrNow > atrAvg * 1.8)
         candidate = REGIME_HIGH_VOL;
      else if(atrNow < atrAvg * 0.65 && dispEff < 0.45)
         candidate = REGIME_COMPRESSION;
      else
      {
         double emaSep = MathAbs(fast[0] - slow[0]);
         if(persistScore >= 0.5 && dispEff >= 0.5 && emaSep > atrNow * 0.3)
            candidate = REGIME_TRENDING;
         else if(atrNow >= atrAvg * 0.80)
            candidate = REGIME_RANGING;
         else
            candidate = REGIME_COMPRESSION;
      }

      // ── Stability rule ────────────────────────────────────────────
      // Warmup: commit immediately on first evaluation
      if(m_activeRegime == REGIME_UNKNOWN)
      {
         m_activeRegime  = candidate;
         m_pendingRegime = candidate;
         m_pendingCount  = REGIME_STABILITY_COUNT;
         Print(StringFormat("[REGIME] Initial classification: %s | H1_ATR=%.5f | avg=%.5f",
               RegimeName(candidate), atrNow, atrAvg));
      }
      else if(candidate == m_activeRegime)
      {
         // Same as active — reset any pending challenger
         m_pendingRegime = candidate;
         m_pendingCount  = REGIME_STABILITY_COUNT;
      }
      else if(candidate == m_pendingRegime)
      {
         // Second consecutive bar agrees with challenger
         m_pendingCount++;
         if(m_pendingCount >= REGIME_STABILITY_COUNT)
         {
            Print(StringFormat("[REGIME] Confirmed: %s (was %s) | H1_ATR=%.5f | avg=%.5f | wick=%.2f | disp=%.2f",
                  RegimeName(candidate), RegimeName(m_activeRegime),
                  atrNow, atrAvg, s.wickRatio, dispEff));
            m_activeRegime  = candidate;
            m_pendingRegime = candidate;
            m_pendingCount  = REGIME_STABILITY_COUNT;
         }
         else
         {
            Print(StringFormat("[REGIME] Pending: %s (%d/%d) — holding %s",
                  RegimeName(candidate), m_pendingCount, REGIME_STABILITY_COUNT,
                  RegimeName(m_activeRegime)));
         }
      }
      else
      {
         // New challenger — reset pending to this candidate (needs 2 consecutive)
         m_pendingRegime = candidate;
         m_pendingCount  = 1;
         Print(StringFormat("[REGIME] Pending reset: %s (1/%d) — holding %s",
               RegimeName(candidate), REGIME_STABILITY_COUNT, RegimeName(m_activeRegime)));
      }

      s.regime      = m_activeRegime;
      s.macroRegime = m_cachedMacro;

      // ── D1 macro ceiling gate ─────────────────────────────────────
      // Applied after stability rule so the committed regime is what gets
      // restricted — not the candidate that may not yet be confirmed.
      if(m_cachedMacro == MACRO_HIGH_VOL)
      {
         if(s.regime != REGIME_HIGH_VOL)
            Print(StringFormat("[REGIME] Macro ceiling override: %s → HIGH_VOL (D1 macro=HIGH_VOL)",
                  RegimeName(s.regime)));
         s.regime = REGIME_HIGH_VOL;
      }
      else if(m_cachedMacro == MACRO_CONTRACTION && s.regime == REGIME_TRENDING)
      {
         Print("[REGIME] Macro ceiling cap: TRENDING → RANGING (D1 macro=CONTRACTION)");
         s.regime = REGIME_RANGING;
      }

      return s;
   }

   //------------------------------------------------------------------
   // FIX #7 — Takes a pre-captured RegimeState to avoid a redundant
   // GetState() call when the StateMachine already has regimeAtEntry.
   //------------------------------------------------------------------
   double GetVolatilityScoreFromState(const RegimeState &s)
   {
      switch(s.regime)
      {
         case REGIME_TRENDING:      return 15.0;
         case REGIME_RANGING:       return 10.0;
         case REGIME_COMPRESSION:   return  7.0;
         case REGIME_HIGH_VOL:      return  3.0;
         case REGIME_DEAD:          return  0.0;
         case REGIME_MANIPULATION:  return  0.0;
         default:                   return  5.0;
      }
   }

   // Convenience wrapper — calls GetState() internally.
   // Use GetVolatilityScoreFromState() when you already have the state.
   double GetVolatilityScore()
   {
      RegimeState s = GetState();
      return GetVolatilityScoreFromState(s);
   }

   string RegimeName(ENUM_MARKET_REGIME r)
   {
      switch(r)
      {
         case REGIME_TRENDING:     return "Trending";
         case REGIME_RANGING:      return "Ranging";
         case REGIME_COMPRESSION:  return "Compression";
         case REGIME_HIGH_VOL:     return "HighVol";
         case REGIME_DEAD:         return "Dead";
         case REGIME_MANIPULATION: return "Manipulation";
         default:                  return "Unknown";
      }
   }

   string MacroRegimeName(ENUM_MACRO_REGIME r)
   {
      switch(r)
      {
         case MACRO_EXPANSION:   return "Expansion";
         case MACRO_NEUTRAL:     return "Neutral";
         case MACRO_CONTRACTION: return "Contraction";
         case MACRO_HIGH_VOL:    return "HighVol";
         default:                return "Unknown";
      }
   }
};
#endif // ASE_REGIMEENGINE_MQH
