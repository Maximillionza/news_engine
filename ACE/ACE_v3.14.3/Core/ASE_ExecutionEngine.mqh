#ifndef ASE_EXECUTIONENGINE_MQH
#define ASE_EXECUTIONENGINE_MQH
#include <Trade/Trade.mqh>
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v4.0 — Execution Engine                                      |
//|                                                                  |
//| v3.3.0 — FIX #15:                                                |
//|   Fill policy read from SYMBOL_FILLING_MODE instead of hardcoded |
//|   FOK. Avoids retcode 10030 on XM and similar CFD brokers.      |
//|                                                                  |
//| v4.0 additions (§5 Execution Engine Rewrite):                    |
//|                                                                  |
//|   1. Spread shock rejection (pre-send guard)                     |
//|      Maintains an EMA of normal spread. If spread at the moment  |
//|      of execution exceeds normalSpread × InpExecSpreadShockMult, |
//|      the order is rejected without sending, logged, and counted  |
//|      as a shock rejection (not a broker rejection).              |
//|                                                                  |
//|   2. Retry loop with back-off                                    |
//|      On transient broker errors (REQUOTE, PRICE_CHANGED,         |
//|      OFF_QUOTES, etc.) the engine re-fetches live price, rebuilds|
//|      the order parameters, and retries up to InpExecRetries      |
//|      times with a 250 ms sleep between attempts.                 |
//|      Hard errors (invalid SL/TP, no money, etc.) abort           |
//|      immediately — retrying would not resolve them.              |
//|                                                                  |
//|   3. Latency measurement                                         |
//|      GetTickCount() is sampled before each send attempt and      |
//|      after a confirmed fill. The round-trip for the successful    |
//|      attempt is stored in m_lastLatencyMs and is exposed via     |
//|      GetLastLatencyMs(). ASE_TradeAttribution.mqh reads this     |
//|      via StateMachine to populate TradeRecord.latencyMs.        |
//|                                                                  |
//|   4. Execution telemetry                                         |
//|      Every outcome — fill, retry, shock rejection, hard abort —  |
//|      is counted and printable via PrintSummary().                |
//|                                                                  |
//|   Retcode classification:                                        |
//|     Retryable: 10004 REQUOTE, 10006 REJECTED, 10014 INVALID_FILL,|
//|                10016 INVALID_STOPS (price slipped), 10018 MARKET |
//|                _CLOSED (transient), 10021 NO_QUOTES, 10025       |
//|                TOO_MANY_REQUESTS                                 |
//|     Hard abort: all others (10011–10013 invalid params,          |
//|                10019 NO_MONEY, 10022 NOT_ENOUGH_MONEY, etc.)     |
//+------------------------------------------------------------------+

// Retcode constants for retryable conditions
#define EXEC_RC_REQUOTE          10004
#define EXEC_RC_REJECTED         10006
#define EXEC_RC_INVALID_FILL     10014
#define EXEC_RC_INVALID_STOPS    10016
#define EXEC_RC_MARKET_CLOSED    10018
#define EXEC_RC_NO_QUOTES        10021
#define EXEC_RC_TOO_MANY_REQ     10025
// Back-off delay between retry attempts (ms)
#define EXEC_RETRY_SLEEP_MS      250
// Spread EMA smoothing factor (α = 0.05 → ~20-sample warm-up)
#define EXEC_SPREAD_EMA_ALPHA    0.05

class CASE_ExecutionEngine
{
private:
   CTrade  m_trade;

   // Fill state
   double  m_lastFillPrice;
   int     m_lastLatencyMs;   // round-trip ms for the successful attempt

   // Spread shock tracking (independent of TradeAttribution EMA)
   double  m_avgSpread;
   int     m_spreadSamples;

   // Telemetry counters
   int     m_successCount;
   int     m_rejectCount;       // broker-side rejections (hard or exhausted retries)
   int     m_shockRejectCount;  // pre-send spread shock aborts
   int     m_retryTotal;        // cumulative retry attempts across all orders
   int     m_hardAbortCount;    // orders abandoned due to non-retryable retcode

public:
   CASE_ExecutionEngine()
      : m_lastFillPrice(0.0),
        m_lastLatencyMs(0),
        m_avgSpread(0.0),
        m_spreadSamples(0),
        m_successCount(0),
        m_rejectCount(0),
        m_shockRejectCount(0),
        m_retryTotal(0),
        m_hardAbortCount(0) {}

   //──────────────────────────────────────────────────────────────────
   bool Initialize()
   {
      m_trade.SetExpertMagicNumber(InpMagicNumber);
      m_trade.SetDeviationInPoints(20);

      // FIX #15 — use the broker's declared fill policy for this symbol
      ENUM_ORDER_TYPE_FILLING fillMode = GetSymbolFillMode();
      m_trade.SetTypeFilling(fillMode);
      Print(StringFormat("[EXEC] Fill mode: %s", EnumToString(fillMode)));

      m_lastFillPrice   = 0.0;
      m_lastLatencyMs   = 0;
      m_avgSpread       = 0.0;
      m_spreadSamples   = 0;
      m_successCount    = 0;
      m_rejectCount     = 0;
      m_shockRejectCount= 0;
      m_retryTotal      = 0;
      m_hardAbortCount  = 0;
      return true;
   }

   //──────────────────────────────────────────────────────────────────
   // UpdateSpread — maintain an independent spread EMA used only for
   // execution-time shock detection. Call once per bar or per tick.
   // Kept separate from TradeAttribution's EMA so the two can warm
   // up and drift independently without coupling.
   //──────────────────────────────────────────────────────────────────
   void UpdateSpread()
   {
      double spread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) -
                       SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;
      if(spread <= 0.0) return;

      if(m_spreadSamples == 0)
         m_avgSpread = spread;
      else
         m_avgSpread = m_avgSpread * (1.0 - EXEC_SPREAD_EMA_ALPHA)
                     + spread       * EXEC_SPREAD_EMA_ALPHA;
      m_spreadSamples++;
   }

   //──────────────────────────────────────────────────────────────────
   // Execute — the main entry point called from StateMachine.
   //
   // Flow:
   //   1. Spread shock guard  (pre-send)
   //   2. Retry loop          (up to InpExecRetries attempts)
   //      a. Refresh live price for each attempt
   //      b. Send order
   //      c. On fill → record latency, return true
   //      d. On retryable error → sleep and retry
   //      e. On hard error → abort immediately
   //   3. Exhausted retries → count as reject, return false
   //──────────────────────────────────────────────────────────────────
   bool Execute(TradeSetup &setup)
   {
      if(!setup.valid) return false;

      //── 1. Spread shock guard ──────────────────────────────────────
      if(!SpreadShockCheck(setup))
         return false;

      int  maxAttempts = (InpExecRetries > 0) ? InpExecRetries : 1;
      bool ok          = false;

      //── 2. Retry loop ──────────────────────────────────────────────
      for(int attempt = 0; attempt < maxAttempts; attempt++)
      {
         if(attempt > 0)
         {
            m_retryTotal++;
            Sleep(EXEC_RETRY_SLEEP_MS);
            // Re-check spread after the sleep — another spike may have
            // started; abort early rather than send into it.
            if(!SpreadShockCheck(setup))
               return false;
         }

         // Refresh live ask/bid so price is current for this attempt
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         if(ask <= 0 || bid <= 0)
         {
            Print(StringFormat("[EXEC] Attempt %d: invalid price — ask=%.5f bid=%.5f",
                               attempt + 1, ask, bid));
            continue;
         }

         //── Send ──────────────────────────────────────────────────
         uint tBefore = GetTickCount();

         if(setup.type == ORDER_TYPE_BUY)
            ok = m_trade.Buy(
                    setup.lotSize, _Symbol,
                    ask, setup.stopLoss, setup.takeProfit2,
                    StringFormat("ASE v4 BUY | RR=%.2f", setup.rr));
         else
            ok = m_trade.Sell(
                    setup.lotSize, _Symbol,
                    bid, setup.stopLoss, setup.takeProfit2,
                    StringFormat("ASE v4 SELL | RR=%.2f", setup.rr));

         uint tAfter  = GetTickCount();

         //── Fill confirmed ────────────────────────────────────────
         if(ok)
         {
            m_lastFillPrice  = m_trade.ResultPrice();
            m_lastLatencyMs  = (int)(tAfter - tBefore);
            m_successCount++;

            // Update actual fill on setup so StateMachine / TradeRecord
            // can capture it without re-reading the history.
            setup.actualFill = m_lastFillPrice;

            if(attempt > 0)
               Print(StringFormat("[EXEC] Filled on attempt %d | Latency=%d ms | Fill=%.5f",
                                  attempt + 1, m_lastLatencyMs, m_lastFillPrice));
            else
               Print(StringFormat("[EXEC] Filled | Latency=%d ms | Fill=%.5f",
                                  m_lastLatencyMs, m_lastFillPrice));
            return true;
         }

         //── Handle error ──────────────────────────────────────────
         uint retcode = m_trade.ResultRetcode();
         Print(StringFormat("[EXEC] Attempt %d failed | Retcode=%u (%s)",
                            attempt + 1, retcode,
                            m_trade.ResultRetcodeDescription()));

         if(!IsRetryable(retcode))
         {
            m_hardAbortCount++;
            Print("[EXEC] Hard error — aborting retries");
            break;
         }
         // else: retryable — loop continues
      }

      // Exhausted attempts or hard abort
      m_rejectCount++;
      return false;
   }

   //──────────────────────────────────────────────────────────────────
   // Getters — used by StateMachine, TradeAttribution, and reports
   //──────────────────────────────────────────────────────────────────
   ulong  LastTicket()          const { return m_trade.ResultOrder(); }
   double GetLastFillPrice()    const { return m_lastFillPrice;       }
   int    GetLastLatencyMs()    const { return m_lastLatencyMs;       }
   int    GetRejectCount()      const { return m_rejectCount;         }
   int    GetSuccessCount()     const { return m_successCount;        }
   int    GetShockRejectCount() const { return m_shockRejectCount;    }
   int    GetRetryTotal()       const { return m_retryTotal;          }
   double GetAvgSpread()        const { return m_avgSpread;           }

   double GetRejectionRate() const
   {
      int total = m_rejectCount + m_successCount + m_shockRejectCount;
      return (total > 0)
             ? (double)(m_rejectCount + m_shockRejectCount) / total * 100.0
             : 0.0;
   }

   void PrintSummary() const
   {
      Print(StringFormat(
         "[EXEC] Summary | Fills=%d | BrokerRejects=%d | ShockRejects=%d"
         " | HardAborts=%d | RetryAttempts=%d | AvgSpread=%.1f pts",
         m_successCount, m_rejectCount, m_shockRejectCount,
         m_hardAbortCount, m_retryTotal, m_avgSpread));
   }

   //══════════════════════════════════════════════════════════════════
   //  PRIVATE helpers
   //══════════════════════════════════════════════════════════════════
private:

   //──────────────────────────────────────────────────────────────────
   // SpreadShockCheck — pre-send guard.
   // Returns true (safe to send) or false (abort, count as shock).
   // Skips the check until the EMA has at least 10 samples to avoid
   // false triggers on session open when avgSpread is still warming up.
   //──────────────────────────────────────────────────────────────────
   bool SpreadShockCheck(const TradeSetup &setup)
   {
      if(m_spreadSamples < 10 || m_avgSpread <= 0.0)
         return true;   // not enough history — allow through

      double currentSpread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) -
                              SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;

      double shockThreshold = m_avgSpread * InpExecSpreadShockMult;

      if(currentSpread > shockThreshold)
      {
         m_shockRejectCount++;
         Print(StringFormat(
            "[EXEC] SPREAD SHOCK — rejecting order | Current=%.1f pts | "
            "Avg=%.1f pts | Threshold=%.1f pts (%.1fx)",
            currentSpread, m_avgSpread, shockThreshold, InpExecSpreadShockMult));
         return false;
      }
      return true;
   }

   //──────────────────────────────────────────────────────────────────
   // IsRetryable — classify broker retcode.
   // Transient conditions are worth retrying after a short sleep.
   // Parameter/account errors are hard and retrying wastes time.
   //──────────────────────────────────────────────────────────────────
   bool IsRetryable(uint retcode) const
   {
      switch(retcode)
      {
         case EXEC_RC_REQUOTE:       return true;
         case EXEC_RC_REJECTED:      return true;
         case EXEC_RC_INVALID_FILL:  return true;   // re-detect fill mode
         case EXEC_RC_INVALID_STOPS: return true;   // price may have moved
         case EXEC_RC_MARKET_CLOSED: return true;   // may reopen
         case EXEC_RC_NO_QUOTES:     return true;
         case EXEC_RC_TOO_MANY_REQ:  return true;
         default:                    return false;  // hard error
      }
   }

   //──────────────────────────────────────────────────────────────────
   // FIX #15 — resolve broker fill mode for this symbol.
   // Priority: FOK if supported, else IOC, else Return.
   //──────────────────────────────────────────────────────────────────
   ENUM_ORDER_TYPE_FILLING GetSymbolFillMode()
   {
      long fillFlags = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
      if((fillFlags & SYMBOL_FILLING_FOK) != 0) return ORDER_FILLING_FOK;
      if((fillFlags & SYMBOL_FILLING_IOC) != 0) return ORDER_FILLING_IOC;
      return ORDER_FILLING_RETURN;
   }
};
#endif // ASE_EXECUTIONENGINE_MQH
