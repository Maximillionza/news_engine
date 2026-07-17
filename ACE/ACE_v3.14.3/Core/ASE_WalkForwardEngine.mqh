#ifndef ASE_WALKFORWARDENGINE_MQH
#define ASE_WALKFORWARDENGINE_MQH
//+------------------------------------------------------------------+
//| ASE v3 — Walk-Forward Validation Engine                          |
//| Phase 2: Rolling IS/OOS window tracking (spec §4.1)              |
//|                                                                  |
//| v3.8.0 — Live degradation alert (Task 13):                       |
//|   CheckRetentionAlert() is called every WF_ALERT_INTERVAL trades.|
//|   If the most recent complete window's wrRetention falls below   |
//|   WF_ALERT_THRESHOLD for WF_ALERT_CONSECUTIVE consecutive checks |
//|   the engine flags m_degradationWarning = true so the caller     |
//|   can forward to AlertEngine. Alert-only — does not halt trading.|
//|   Default: check every 10 trades, warn at <0.80 for 2 checks.   |
//+------------------------------------------------------------------+

#define WF_MAX_WINDOWS        24    // max rolling windows stored
#define WF_IS_DAYS            60    // in-sample period (days)
#define WF_OOS_DAYS           30    // out-of-sample period (days)
#define WF_SECS_PER_DAY       86400
#define WF_ALERT_INTERVAL     10    // check every N trades
#define WF_ALERT_THRESHOLD    0.80  // wrRetention floor for warning
#define WF_ALERT_CONSECUTIVE  2     // consecutive failing checks before flag

struct WFWindow
{
   datetime isStart;
   datetime isEnd;
   datetime oosStart;
   datetime oosEnd;

   // IS stats
   int    isTrades;
   double isWR;
   double isRR;
   double isPF;
   double isDD;

   // OOS stats
   int    oosTrades;
   double oosWR;
   double oosRR;
   double oosPF;
   double oosDD;

   // Retention ratios (OOS/IS)
   double wrRetention;    // ≥0.85 = pass
   double rrRetention;
   double pfRetention;

   bool   passes;
};

class CASE_WalkForwardEngine
{
private:
   // Per-trade storage
   datetime m_tradeTimes[];
   double   m_tradeProfits[];
   double   m_tradeRR[];
   int      m_tradeCount;

   // Window results
   WFWindow m_windows[];
   int      m_windowCount;

   datetime m_testStart;
   datetime m_testEnd;

   // v3.8.0 — live degradation alert state
   int  m_alertFailCount;       // consecutive check failures
   bool m_degradationWarning;   // true = alert needs to fire

public:
   CASE_WalkForwardEngine() : m_tradeCount(0), m_windowCount(0),
                              m_testStart(0), m_testEnd(0),
                              m_alertFailCount(0),
                              m_degradationWarning(false) {}

   void Initialize()
   {
      m_tradeCount         = 0;
      m_windowCount        = 0;
      m_testStart          = 0;
      m_testEnd            = 0;
      m_alertFailCount     = 0;
      m_degradationWarning = false;
      ArrayResize(m_tradeTimes,   0);
      ArrayResize(m_tradeProfits, 0);
      ArrayResize(m_tradeRR,      0);
      ArrayResize(m_windows,      0);
   }

   // Add a closed trade — call from StateMachine.RecordClosedTrade()
   void AddTrade(datetime closeTime, double profit, double rr)
   {
      int idx = m_tradeCount++;
      ArrayResize(m_tradeTimes,   m_tradeCount);
      ArrayResize(m_tradeProfits, m_tradeCount);
      ArrayResize(m_tradeRR,      m_tradeCount);

      m_tradeTimes[idx]   = closeTime;
      m_tradeProfits[idx] = profit;
      m_tradeRR[idx]      = rr;

      if(m_testStart == 0 || closeTime < m_testStart) m_testStart = closeTime;
      if(closeTime > m_testEnd) m_testEnd = closeTime;

      // v3.8.0 — check for live retention degradation every N trades
      if(m_tradeCount % WF_ALERT_INTERVAL == 0)
         CheckRetentionAlert();
   }

   // Returns true if a WF degradation alert needs to fire.
   // Caller (StateMachine) reads this flag after AddTrade() and
   // forwards to AlertEngine, then resets via ClearDegradationWarning().
   bool HasDegradationWarning() const { return m_degradationWarning; }
   void ClearDegradationWarning()     { m_degradationWarning = false; }

   //------------------------------------------------------------------
   // Build rolling windows and compute all IS/OOS metrics
   // Call once at end of test (from OnTester or Deinitialize)
   //------------------------------------------------------------------
   void BuildWindows()
   {
      m_windowCount = 0;
      ArrayResize(m_windows, 0);

      if(m_tradeCount < 10) return;

      long totalDays = (long)((m_testEnd - m_testStart) / WF_SECS_PER_DAY);
      if(totalDays < WF_IS_DAYS + WF_OOS_DAYS) return;

      datetime wStart = m_testStart;

      while(true)
      {
         datetime isEnd   = (datetime)(wStart + (long)WF_IS_DAYS  * WF_SECS_PER_DAY);
         datetime oosEnd  = (datetime)(isEnd  + (long)WF_OOS_DAYS * WF_SECS_PER_DAY);

         if(oosEnd > m_testEnd) break;
         if(m_windowCount >= WF_MAX_WINDOWS) break;

         WFWindow w;
         w.isStart  = wStart;
         w.isEnd    = isEnd;
         w.oosStart = isEnd;
         w.oosEnd   = oosEnd;

         CalcPeriodStats(wStart, isEnd,  w.isTrades,  w.isWR,  w.isRR,  w.isPF,  w.isDD);
         CalcPeriodStats(isEnd,  oosEnd, w.oosTrades, w.oosWR, w.oosRR, w.oosPF, w.oosDD);

         // Retention ratios — 0 if IS had 0 (avoid div/0)
         w.wrRetention = SafeRatio(w.oosWR, w.isWR);
         w.rrRetention = SafeRatio(w.oosRR, w.isRR);
         w.pfRetention = SafeRatio(w.oosPF, w.isPF);

         // Pass if all retention ≥ 0.85 AND enough OOS trades
         w.passes = (w.oosTrades >= 5      &&
                     w.wrRetention >= 0.85 &&
                     w.rrRetention >= 0.85 &&
                     w.pfRetention >= 0.85);

         int idx = m_windowCount++;
         ArrayResize(m_windows, m_windowCount);
         m_windows[idx] = w;

         // Roll forward by OOS period
         wStart = (datetime)(wStart + (long)WF_OOS_DAYS * WF_SECS_PER_DAY);
      }
   }

   //------------------------------------------------------------------
   // Primary output for OptimizerBridge
   // Returns 0.0–1.0 (fraction of windows that pass)
   //------------------------------------------------------------------
   double GetOOSRetention()
   {
      if(m_windowCount <= 0) return 1.0;   // no data — neutral
      int passes = 0;
      for(int i = 0; i < m_windowCount; i++)
         if(m_windows[i].passes) passes++;
      return (double)passes / m_windowCount;
   }

   // Average OOS WR as % of IS WR across all windows
   double GetAvgWRRetention()
   {
      if(m_windowCount <= 0) return 1.0;
      double sum = 0.0;
      for(int i = 0; i < m_windowCount; i++) sum += m_windows[i].wrRetention;
      return sum / m_windowCount;
   }

   int      GetWindowCount()     { return m_windowCount; }
   WFWindow GetWindow(int i)     { return m_windows[i]; }

   void PrintReport()
   {
      Print("══ Walk-Forward Report ═════════════════");
      Print(StringFormat("  Windows : %d  Passing: %d (%.0f%%)",
            m_windowCount,
            (int)(GetOOSRetention() * m_windowCount),
            GetOOSRetention() * 100.0));
      for(int i = 0; i < m_windowCount; i++)
      {
         Print(StringFormat("  W%02d IS[%s-%s] OOS[%s-%s] WR:%.0f%%->%.0f%%(%.0f%%) PF:%.2f->%.2f %s",
               i+1,
               TimeToString(m_windows[i].isStart,  TIME_DATE),
               TimeToString(m_windows[i].isEnd,    TIME_DATE),
               TimeToString(m_windows[i].oosStart, TIME_DATE),
               TimeToString(m_windows[i].oosEnd,   TIME_DATE),
               m_windows[i].isWR, m_windows[i].oosWR, m_windows[i].wrRetention*100.0,
               m_windows[i].isPF, m_windows[i].oosPF,
               m_windows[i].passes ? "PASS" : "FAIL"));
      }
      Print("════════════════════════════════════════");
   }

private:
   //------------------------------------------------------------------
   // v3.8.0 — Live retention degradation check.
   // Called every WF_ALERT_INTERVAL trades. Rebuilds windows and reads
   // the most recent complete window's wrRetention. If it falls below
   // WF_ALERT_THRESHOLD for WF_ALERT_CONSECUTIVE consecutive checks,
   // sets m_degradationWarning = true for the caller to forward to
   // AlertEngine. Does not halt trading.
   //------------------------------------------------------------------
   void CheckRetentionAlert()
   {
      BuildWindows();
      if(m_windowCount < 1) return;

      // Read the most recent window (last in the array)
      double lastWR = m_windows[m_windowCount - 1].wrRetention;
      int    oosTr  = m_windows[m_windowCount - 1].oosTrades;

      // Need at least 5 OOS trades to make retention meaningful
      if(oosTr < 5) return;

      if(lastWR < WF_ALERT_THRESHOLD)
      {
         m_alertFailCount++;
         Print(StringFormat(
            "[WF] Retention check: wrRetention=%.2f < %.2f threshold "
            "(fail %d/%d) | oosTrades=%d",
            lastWR, WF_ALERT_THRESHOLD,
            m_alertFailCount, WF_ALERT_CONSECUTIVE, oosTr));

         if(m_alertFailCount >= WF_ALERT_CONSECUTIVE)
         {
            m_degradationWarning = true;
            Print(StringFormat(
               "[WF] *** DEGRADATION WARNING *** wrRetention=%.2f for %d "
               "consecutive checks — operator review recommended",
               lastWR, m_alertFailCount));
         }
      }
      else
      {
         // Retention recovered — reset consecutive counter
         if(m_alertFailCount > 0)
            Print(StringFormat("[WF] Retention recovered: wrRetention=%.2f (was failing)",
                               lastWR));
         m_alertFailCount = 0;
      }
   }

   void CalcPeriodStats(datetime from, datetime to,
                        int &trades, double &wr, double &rr,
                        double &pf, double &maxDD)
   {
      trades = 0; wr = 0; rr = 0; pf = 0; maxDD = 0;
      int wins = 0;
      double grossWin = 0, grossLoss = 0, sumRR = 0;
      double equity = 0, peak = 0;

      for(int i = 0; i < m_tradeCount; i++)
      {
         if(m_tradeTimes[i] < from || m_tradeTimes[i] >= to) continue;
         trades++;
         double p = m_tradeProfits[i];
         equity += p;
         if(equity > peak) peak = equity;
         double dd = (peak > 0) ? (peak - equity) / peak * 100.0 : 0.0;
         if(dd > maxDD) maxDD = dd;

         if(p >= 0) { wins++; grossWin  += p; }
         else       {         grossLoss += MathAbs(p); }

         if(m_tradeRR[i] > 0) sumRR += m_tradeRR[i];
      }

      if(trades > 0)
      {
         wr = (double)wins / trades * 100.0;
         rr = (trades > 0) ? sumRR / trades : 0.0;
         pf = (grossLoss > 1e-10) ? grossWin / grossLoss : (grossWin > 0 ? 999.0 : 0.0);
      }
   }

   double SafeRatio(double oosVal, double isVal)
   {
      if(isVal < 1e-10) return (oosVal > 0) ? 1.0 : 0.0;
      return oosVal / isVal;
   }
};
#endif // ASE_WALKFORWARDENGINE_MQH
