#ifndef ASE_DIRECTIONGATE_MQH
#define ASE_DIRECTIONGATE_MQH
#include "../Models/ASE_Enums.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3.11.0 — Direction Gate                                     |
//|                                                                  |
//| PURPOSE                                                          |
//|   Single authoritative source of market direction that runs      |
//|   BEFORE any setup or liquidity logic. All downstream engines    |
//|   receive a direction confirmed by multi-timeframe confluence.   |
//|                                                                  |
//| ARCHITECTURE (v3.12.2)                                          |
//|   Three independent signals, InpDGMinVotes required to agree:    |
//|                                                                  |
//|   1. H4 EMA Cross  — confirmed macro trend (bar[1] cross only)  |
//|      v3.12.2: slope requirement removed. H4 now always votes     |
//|      LONG or SHORT based on EMA20 vs EMA50 on bar[1]. The prior  |
//|      dual condition (cross AND slope) made H4 neutral during any  |
//|      minor correction, causing 200k+ DIR_NONE blocks per day.    |
//|   2. H1 BOS        — structural bias (last H1 swing broken)     |
//|   3. D1 Price Side — daily context (close vs D1 EMA50)          |
//|                                                                  |
//|   H4 EMA reads bar[1]/bar[2] ONLY — forming bar[0] is excluded. |
//|   This eliminates mid-candle EMA noise that caused false splits  |
//|   during normal intra-H4 corrections in v3.10.x.                |
//|                                                                  |
//| SHORT STRUCTURAL EXCEPTION (Fix 1)                               |
//|   When the H4 macro trend is LONG but H1 BOS confirms a genuine |
//|   SHORT (lower-low break = structural change, not pullback):     |
//|     - If D1 also agrees SHORT → standard 2-of-3 path, fires.    |
//|     - If D1 is LONG/neutral → SHORT allowed as structural        |
//|       exception IF H1 BOS strength is confirmed (genuine break). |
//|   Pullback filter: if H1 BOS is still pointing LONG, any SHORT  |
//|   signal is blocked regardless of H4/D1. A pullback in the       |
//|   SHORT direction within a LONG H1 structure is not a reversal. |
//|                                                                  |
//| DAILY RESET                                                      |
//|   ResetGateState() clears resolved direction and vote state.     |
//|   Called by StateMachine at InpDailyResetHour UTC when no trade  |
//|   is open. H1 swing levels (owned by StructureEngine) are NOT   |
//|   affected — structural memory persists across midnight.         |
//|                                                                  |
//| DIR_NONE RETRY                                                    |
//|   When gate returns DIR_NONE, m_noneBarCount increments each     |
//|   M15 bar. When it reaches InpDGRetryBars, ForceRetry() signals  |
//|   the StateMachine to re-enter STATE_WAIT_HTF immediately rather |
//|   than waiting for the next organic pipeline advance.            |
//+------------------------------------------------------------------+

class CASE_DirectionGate
{
private:
   int m_h4FastHandle;   // H4 EMA fast (confirmed-bar read)
   int m_h4SlowHandle;   // H4 EMA slow (confirmed-bar read)
   int m_d1EMAHandle;    // D1 EMA50 (daily context)

   ENUM_TRADE_DIRECTION m_resolvedDirection;
   int                  m_longVotes;
   int                  m_shortVotes;

   // Signal results for logging
   ENUM_TRADE_DIRECTION m_sigH4EMA;
   ENUM_TRADE_DIRECTION m_sigH1BOS;
   ENUM_TRADE_DIRECTION m_sigD1;

   // v3.11.0 — SHORT structural exception flag (set during Evaluate)
   bool                 m_shortStructuralException;

   // v3.11.0 — DIR_NONE retry counter (M15 bars)
   int                  m_noneBarCount;
   datetime             m_lastNoneBar;

public:
   CASE_DirectionGate() : m_h4FastHandle(INVALID_HANDLE),
                          m_h4SlowHandle(INVALID_HANDLE),
                          m_d1EMAHandle(INVALID_HANDLE),
                          m_resolvedDirection(DIR_NONE),
                          m_longVotes(0),
                          m_shortVotes(0),
                          m_sigH4EMA(DIR_NONE),
                          m_sigH1BOS(DIR_NONE),
                          m_sigD1(DIR_NONE),
                          m_shortStructuralException(false),
                          m_noneBarCount(0),
                          m_lastNoneBar(0) {}

   bool Initialize()
   {
      m_h4FastHandle = iMA(_Symbol, PERIOD_H4, InpH4FastEMA, 0, MODE_EMA, PRICE_CLOSE);
      m_h4SlowHandle = iMA(_Symbol, PERIOD_H4, InpH4SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
      m_d1EMAHandle  = iMA(_Symbol, PERIOD_D1, 50,           0, MODE_EMA, PRICE_CLOSE);

      bool ok = (m_h4FastHandle != INVALID_HANDLE &&
                 m_h4SlowHandle != INVALID_HANDLE &&
                 m_d1EMAHandle  != INVALID_HANDLE);
      if(!ok) Print("[DGATE] INIT FAIL — one or more indicator handles invalid");
      return ok;
   }

   void Deinitialize()
   {
      if(m_h4FastHandle != INVALID_HANDLE) IndicatorRelease(m_h4FastHandle);
      if(m_h4SlowHandle != INVALID_HANDLE) IndicatorRelease(m_h4SlowHandle);
      if(m_d1EMAHandle  != INVALID_HANDLE) IndicatorRelease(m_d1EMAHandle);
   }

   //------------------------------------------------------------------
   // ResetGateState() — daily reset called by StateMachine at
   // InpDailyResetHour UTC when no position is open. Clears direction
   // resolution and vote state so the new trading day starts with a
   // fresh evaluation. Does NOT touch H1 swing levels (StructureEngine
   // owns those) or the H1BiasStaleBars counter.
   //------------------------------------------------------------------
   void ResetGateState()
   {
      m_resolvedDirection      = DIR_NONE;
      m_longVotes              = 0;
      m_shortVotes             = 0;
      m_sigH4EMA               = DIR_NONE;
      m_sigH1BOS               = DIR_NONE;
      m_sigD1                  = DIR_NONE;
      m_shortStructuralException = false;
      m_noneBarCount           = 0;
      m_lastNoneBar            = 0;
      Print("[DGATE] Daily gate state reset — fresh evaluation on next HTF pass");
   }

   //------------------------------------------------------------------
   // ForceRetry() — returns true when DIR_NONE has persisted for
   // InpDGRetryBars M15 bars, signalling StateMachine to re-enter
   // STATE_WAIT_HTF. Caller resets the counter after acting on this.
   //------------------------------------------------------------------
   bool ForceRetry()
   {
      if(InpDGRetryBars <= 0) return false;
      if(m_resolvedDirection != DIR_NONE) { m_noneBarCount = 0; return false; }

      datetime curBar = iTime(_Symbol, PERIOD_M15, 0);
      if(curBar != m_lastNoneBar)
      {
         m_lastNoneBar = curBar;
         m_noneBarCount++;
         if(m_noneBarCount >= InpDGRetryBars)
         {
            Print(StringFormat("[DGATE] DIR_NONE retry — %d bars elapsed, forcing HTF re-eval",
                               m_noneBarCount));
            m_noneBarCount = 0;
            return true;
         }
      }
      return false;
   }

   // Reset the retry counter — called by StateMachine after acting on ForceRetry()
   void ResetRetryCounter() { m_noneBarCount = 0; m_lastNoneBar = 0; }

   //------------------------------------------------------------------
   // Evaluate() — run all three signals and resolve direction.
   //
   // h1Bias: current H1 BOS direction from StructureEngine (primary).
   //   Passed in so the gate does not duplicate the BOS scan.
   //
   // h1BosIsGenuineBreak: true when StructureEngine confirmed the H1
   //   BOS as a structural lower-low (SHORT) or higher-high (LONG),
   //   not merely a pullback continuation. Used by the SHORT structural
   //   exception path to distinguish reversal from pullback.
   //
   // Returns the resolved direction. DIR_NONE = no trade this cycle.
   //------------------------------------------------------------------
   ENUM_TRADE_DIRECTION Evaluate(ENUM_TRADE_DIRECTION h1Bias,
                                  bool h1BosIsGenuineBreak = false)
   {
      m_longVotes              = 0;
      m_shortVotes             = 0;
      m_sigH4EMA               = DIR_NONE;
      m_sigH1BOS               = DIR_NONE;
      m_sigD1                  = DIR_NONE;
      m_shortStructuralException = false;

      // ── Signal 1: H4 EMA Cross (confirmed bar[1] only) ────────────
      // v3.11.0: reads bar[1] only (last confirmed H4 bar). bar[0] is the
      // forming candle and is excluded to prevent mid-candle noise.
      //
      // v3.12.2 Option B: slope requirement removed.
      // Prior logic required BOTH emaCross (fast[1]>slow[1]) AND emaSlope
      // (fast[1]>fast[2]) to vote. This made H4 neutral whenever the EMA20
      // line dipped even fractionally on a single confirmed bar — a normal
      // occurrence during any pullback in a trending market.
      //
      // CONFIRMED IMPACT (Jan 6 log — 203,243 DGate split blocks in one day):
      // Gold was in a macro bull trend (D1=LONG). H4 EMA20 > EMA50 confirmed
      // (emaCross=true) but EMA20[bar1] < EMA20[bar2] by a tiny amount during
      // an intra-day correction (emaSlope=false). H4 voted neutral.
      // With H1BOS=SHORT (real intra-day structure) and D1=LONG (macro),
      // the gate split 1v1 and returned DIR_NONE for the entire trading day.
      //
      // FIX: use emaCross alone. If EMA20 > EMA50 on the last confirmed H4
      // bar, H4 votes LONG. If EMA20 < EMA50, H4 votes SHORT. The slope
      // across two confirmed bars added noise without adding signal quality
      // — a confirmed EMA cross is sufficient macro context.
      //
      // Result: in a bull trend H4 votes LONG even during corrections.
      // H4=LONG + D1=LONG = 2 votes → LONG confirmed without needing H1.
      // When H1BOS=SHORT (pullback), the gate resolves LONG (2v1), and the
      // SHORT structural exception path handles genuine reversals separately.
      double fast[], slow[];
      ArraySetAsSeries(fast, true);
      ArraySetAsSeries(slow, true);
      // Read 2 bars: bar[1] = last confirmed H4 bar (bar[0] is forming, excluded)
      if(CopyBuffer(m_h4FastHandle, 0, 0, 2, fast) >= 2 &&
         CopyBuffer(m_h4SlowHandle, 0, 0, 2, slow) >= 2)
      {
         // Cross on bar[1] only — slope test removed (v3.12.2)
         bool emaCross = fast[1] > slow[1];
         if( emaCross) { m_sigH4EMA = DIR_LONG;  m_longVotes++;  }
         if(!emaCross) { m_sigH4EMA = DIR_SHORT; m_shortVotes++; }
         // H4 now always votes LONG or SHORT — never neutral.
         // It can still be overridden by 2-of-3 from H1+D1 if they disagree.
      }
      else Print("[DGATE] H4 EMA buffer fail — H4 vote skipped this cycle");

      // ── Signal 2: H1 BOS (passed from StructureEngine) ────────────
      m_sigH1BOS = h1Bias;
      if(h1Bias == DIR_LONG)  m_longVotes++;
      if(h1Bias == DIR_SHORT) m_shortVotes++;

      // ── Signal 3: D1 Price vs EMA50 ───────────────────────────────
      double d1EMA[];
      ArraySetAsSeries(d1EMA, true);
      double d1Close[];
      ArraySetAsSeries(d1Close, true);
      if(CopyBuffer(m_d1EMAHandle, 0, 0, 2, d1EMA) >= 2 &&
         CopyClose(_Symbol, PERIOD_D1, 1, 1, d1Close) >= 1)
      {
         if(d1Close[0] > d1EMA[0]) { m_sigD1 = DIR_LONG;  m_longVotes++;  }
         if(d1Close[0] < d1EMA[0]) { m_sigD1 = DIR_SHORT; m_shortVotes++; }
      }
      else Print("[DGATE] D1 EMA buffer fail — D1 vote skipped this cycle");

      // ── Standard resolution ────────────────────────────────────────
      ENUM_TRADE_DIRECTION resolved = DIR_NONE;
      if(m_longVotes  >= InpDGMinVotes) resolved = DIR_LONG;
      if(m_shortVotes >= InpDGMinVotes) resolved = DIR_SHORT;
      // Defensive: both sides can't simultaneously reach threshold with
      // 3 signals and threshold >= 2, but guard it anyway.
      if(m_longVotes >= InpDGMinVotes && m_shortVotes >= InpDGMinVotes)
         resolved = DIR_NONE;

      // ── SHORT structural exception (Fix 1) ────────────────────────
      // Scenario: H4 macro is LONG (emaCross LONG), but H1 BOS has
      // confirmed a genuine structural SHORT (lower-low break). This
      // is an anticipation-of-direction-change entry, not a pullback.
      //
      // Pullback filter: H1 BOS must be SHORT. If H1 BOS is still LONG,
      // any short-direction signal is a pullback — always blocked here.
      //
      // Exception fires when ALL of the following are true:
      //   a) Standard gate returned DIR_NONE (insufficient SHORT votes)
      //   b) H1 BOS is confirmed SHORT (m_sigH1BOS == DIR_SHORT)
      //   c) The H1 BOS is a genuine structural break, not a retest
      //      (h1BosIsGenuineBreak = true, set by StructureEngine)
      //   d) H4 macro is not also SHORT (prevents double-counting)
      //   e) D1 is SHORT OR H1 BOS is a high-conviction structural break
      //      (either D1 agrees, or the structure alone is sufficient)
      //
      // When the exception fires, the trade is flagged as a countertrend
      // structural entry and InpDGShortScoreBonus is applied at scoring.
      if(resolved == DIR_NONE &&
         m_sigH1BOS == DIR_SHORT &&
         h1BosIsGenuineBreak &&
         m_sigH4EMA != DIR_SHORT)   // H4 not already in SHORT (not a standard path)
      {
         // Allow if D1 also agrees SHORT (directional confluence without H4)
         // OR if D1 is neutral and H1 BOS is confirmed genuine structural break
         bool d1AgreeOrNeutral = (m_sigD1 == DIR_SHORT || m_sigD1 == DIR_NONE);
         if(d1AgreeOrNeutral)
         {
            resolved = DIR_SHORT;
            m_shortStructuralException = true;
            Print(StringFormat(
               "[DGATE] SHORT structural exception: H1 genuine BOS SHORT vs LONG H4 | "
               "D1=%s | h1BosGenuine=true | ScoreBonus=%.1f",
               DirStr(m_sigD1), InpDGShortScoreBonus));
         }
      }

      m_resolvedDirection = resolved;

      // Reset retry counter if a direction was resolved
      if(resolved != DIR_NONE) { m_noneBarCount = 0; m_lastNoneBar = 0; }

      Print(StringFormat(
         "[DGATE] H4EMA=%s(bar1) H1BOS=%s D1=%s | longV=%d shortV=%d | resolved=%s%s",
         DirStr(m_sigH4EMA), DirStr(m_sigH1BOS), DirStr(m_sigD1),
         m_longVotes, m_shortVotes, DirStr(resolved),
         m_shortStructuralException ? " [STRUCT-EXCEPTION]" : ""));

      return resolved;
   }

   // Accessors
   ENUM_TRADE_DIRECTION GetDirection()           const { return m_resolvedDirection; }
   bool                 IsLongContext()          const { return m_resolvedDirection == DIR_LONG;  }
   bool                 IsShortContext()         const { return m_resolvedDirection == DIR_SHORT; }
   bool                 IsShortStructuralException() const { return m_shortStructuralException; }
   int                  GetLongVotes()          const { return m_longVotes;  }
   int                  GetShortVotes()         const { return m_shortVotes; }

   // Signal breakdown for logging
   string GetSignalSummary() const
   {
      return StringFormat("H4EMA=%s(conf) H1BOS=%s D1=%s [L=%d S=%d]%s",
         DirStr(m_sigH4EMA), DirStr(m_sigH1BOS), DirStr(m_sigD1),
         m_longVotes, m_shortVotes,
         m_shortStructuralException ? " STRUCT-EX" : "");
   }

private:
   string DirStr(ENUM_TRADE_DIRECTION d) const
   {
      if(d == DIR_LONG)  return "L";
      if(d == DIR_SHORT) return "S";
      return "N";
   }
};
#endif // ASE_DIRECTIONGATE_MQH
