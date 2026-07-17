#ifndef ASE_TELEMETRY_MQH
#define ASE_TELEMETRY_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3.3.0 — Trade Telemetry & Attribution Engine                |
//| v3.3.0 additions (Area A — Statistical Methodology):             |
//|   GetExpectancy()   — (WR×avgWin) − (LR×avgLoss)                |
//|   GetSharpeRatio()  — per-trade mean/stddev                      |
//|   GetCalmarRatio()  — net profit / max absolute drawdown          |
//|   GetWinRateCI95()  — Wilson score confidence interval            |
//|   MinSampleRequired() — minimum n for 80% power                  |
//| v3.3.0 additions (Area B — Real Execution Validation):           |
//|   Slippage accumulators and getters                              |
//|   SetRejectCount() for execution quality summary                 |
//+------------------------------------------------------------------+
class CASE_Telemetry
{
private:
   // Core aggregate stats
   int    m_wins;
   int    m_losses;
   double m_grossProfit;
   double m_grossLoss;
   double m_peakEquity;
   double m_maxDrawdown;    // as percentage
   double m_sumRR;
   int    m_rrCount;

   // MAE/MFE aggregates
   double m_sumMAE;
   double m_sumMFE;
   double m_sumMAEPct;
   double m_sumMFEPct;

   // Statistical methodology (Area A)
   double m_sumProfit;      // Σ profit (all trades, signed)
   double m_sumProfitSq;    // Σ profit² for online variance
   double m_maxDrawdownAbs; // largest equity drawdown in currency units

   // Execution quality (Area B)
   double m_sumSlippagePts;
   double m_worstSlippagePts;
   int    m_slippageCount;
   int    m_externalRejectCount; // set via SetRejectCount()

   // Live excursion tracking
   bool   m_tracking;
   double m_trackEntry;
   double m_trackSL;
   double m_trackTP2;
   bool   m_trackLong;
   double m_liveMFE;
   double m_liveMAE;
   int    m_liveBars;
   int    m_barsToMFE;
   int    m_barsToMAE;
   double m_mfePeak;
   double m_maePeak;

   // Trade record store
   TradeRecord m_records[];
   int         m_recordCount;

public:
   void Initialize()
   {
      m_wins                 = 0;
      m_losses               = 0;
      m_grossProfit          = 0.0;
      m_grossLoss            = 0.0;
      m_peakEquity           = AccountInfoDouble(ACCOUNT_EQUITY);
      m_maxDrawdown          = 0.0;
      m_sumRR                = 0.0;
      m_rrCount              = 0;
      m_sumMAE               = 0.0;
      m_sumMFE               = 0.0;
      m_sumMAEPct            = 0.0;
      m_sumMFEPct            = 0.0;
      m_sumProfit            = 0.0;
      m_sumProfitSq          = 0.0;
      m_maxDrawdownAbs       = 0.0;
      m_sumSlippagePts       = 0.0;
      m_worstSlippagePts     = 0.0;
      m_slippageCount        = 0;
      m_externalRejectCount  = 0;
      m_tracking             = false;
      m_recordCount          = 0;
      ArrayResize(m_records, 0);
   }

   //──────────────────────────────────────────────────────────────────
   void StartTracking(double entry, double sl, double tp2, bool isLong)
   {
      m_tracking   = true;
      m_trackEntry = entry;
      m_trackSL    = sl;
      m_trackTP2   = tp2;
      m_trackLong  = isLong;
      m_liveMFE    = entry;
      m_liveMAE    = entry;
      m_liveBars   = 0;
      m_barsToMFE  = 0;
      m_barsToMAE  = 0;
      m_mfePeak    = entry;
      m_maePeak    = entry;
   }

   //──────────────────────────────────────────────────────────────────
   void UpdateExcursion()
   {
      if(!m_tracking) return;
      double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double price = m_trackLong ? bid : ask;
      m_liveBars++;
      if(m_trackLong)
      {
         if(price > m_mfePeak) { m_mfePeak = price; m_barsToMFE = m_liveBars; }
         if(price < m_maePeak) { m_maePeak = price; m_barsToMAE = m_liveBars; }
      }
      else
      {
         if(price < m_mfePeak) { m_mfePeak = price; m_barsToMFE = m_liveBars; }
         if(price > m_maePeak) { m_maePeak = price; m_barsToMAE = m_liveBars; }
      }
   }

   //──────────────────────────────────────────────────────────────────
   void RecordWin(double profit, double rr = 0.0)
   {
      m_wins++;
      m_grossProfit  += profit;
      m_sumProfit    += profit;
      m_sumProfitSq  += profit * profit;
      if(rr > 0) { m_sumRR += rr; m_rrCount++; }
      UpdateDrawdown();
   }

   void RecordLoss(double loss, double rr = 0.0)
   {
      m_losses++;
      m_grossLoss    += MathAbs(loss);
      m_sumProfit    += loss;          // signed
      m_sumProfitSq  += loss * loss;
      if(rr > 0) { m_sumRR += rr; m_rrCount++; }
      UpdateDrawdown();
   }

   //──────────────────────────────────────────────────────────────────
   void CommitTradeRecord(TradeRecord &rec)
   {
      if(m_tracking)
      {
         double slDist  = MathAbs(m_trackEntry - m_trackSL);
         double tp2Dist = MathAbs(m_trackEntry - m_trackTP2);
         rec.mae       = MathAbs(m_trackEntry - m_maePeak);
         rec.mfe       = MathAbs(m_trackEntry - m_mfePeak);
         rec.maePct    = (slDist  > 0) ? (rec.mae / slDist)  * 100.0 : 0.0;
         rec.mfePct    = (tp2Dist > 0) ? (rec.mfe / tp2Dist) * 100.0 : 0.0;
         rec.barsToMFE = m_barsToMFE;
         rec.barsToMAE = m_barsToMAE;
         rec.durationBars = m_liveBars;
         m_sumMAE    += rec.mae;
         m_sumMFE    += rec.mfe;
         m_sumMAEPct += rec.maePct;
         m_sumMFEPct += rec.mfePct;
         m_tracking   = false;
      }

      // Accumulate slippage (Area B)
      if(rec.slippagePts != 0.0)
      {
         m_sumSlippagePts += rec.slippagePts;
         if(rec.slippagePts > m_worstSlippagePts)
            m_worstSlippagePts = rec.slippagePts;
         m_slippageCount++;
      }

      int idx = m_recordCount++;
      ArrayResize(m_records, m_recordCount);
      m_records[idx] = rec;
   }

   void StopTracking() { m_tracking = false; }

   // Called from StateMachine.Deinitialize() to include order rejects
   void SetRejectCount(int n) { m_externalRejectCount = n; }

   //──────────────────────────────────────────────────────────────────
   // Standard getters
   //──────────────────────────────────────────────────────────────────
   double GetWinRate()
   {
      int total = m_wins + m_losses;
      return (total > 0) ? ((double)m_wins / total) * 100.0 : 0.0;
   }
   double GetAverageRR()      { return (m_rrCount > 0) ? m_sumRR / m_rrCount : 0.0; }
   int    GetTradeCount()     { return m_wins + m_losses; }
   double GetGrossProfit()    { return m_grossProfit; }
   double GetGrossLoss()      { return m_grossLoss; }
   double GetNetProfit()      { return m_grossProfit - m_grossLoss; }
   double GetMaxDrawdownPct() { return m_maxDrawdown; }
   double GetMaxDrawdownAbs() { return m_maxDrawdownAbs; }
   double GetProfitFactor()
   {
      if(m_grossLoss < 1e-10) return (m_grossProfit > 0) ? 999.0 : 0.0;
      return m_grossProfit / m_grossLoss;
   }
   double GetAvgMAE()     { return (GetTradeCount()>0) ? m_sumMAE    / GetTradeCount() : 0.0; }
   double GetAvgMFE()     { return (GetTradeCount()>0) ? m_sumMFE    / GetTradeCount() : 0.0; }
   double GetAvgMAEPct()  { return (GetTradeCount()>0) ? m_sumMAEPct / GetTradeCount() : 0.0; }
   double GetAvgMFEPct()  { return (GetTradeCount()>0) ? m_sumMFEPct / GetTradeCount() : 0.0; }
   double GetExcursionEfficiency()
   {
      double avgMFE = GetAvgMFE();
      if(avgMFE < 1e-10) return 0.0;
      return (GetNetProfit() > 0) ? MathMin(avgMFE, GetAvgMFE()) / avgMFE * 100.0 : 0.0;
   }
   int          GetRecordCount()  { return m_recordCount; }
   TradeRecord  GetRecord(int i)  { return m_records[i];  }

   //──────────────────────────────────────────────────────────────────
   // Area A — Statistical Methodology
   //──────────────────────────────────────────────────────────────────

   // Expectancy: expected P&L per trade in account currency.
   // (WR × avgWin) − (LR × avgLoss)
   // Positive means edge exists. Compare against avg commission cost.
   double GetExpectancy()
   {
      int total = m_wins + m_losses;
      if(total <= 0) return 0.0;
      double avgWin  = (m_wins   > 0) ? m_grossProfit / m_wins   : 0.0;
      double avgLoss = (m_losses > 0) ? m_grossLoss   / m_losses : 0.0;
      double wr = (double)m_wins   / total;
      double lr = (double)m_losses / total;
      return (wr * avgWin) - (lr * avgLoss);
   }

   // Per-trade Sharpe: mean(profit) / stddev(profit).
   // Not annualised — expressed per trade unit.
   double GetSharpeRatio()
   {
      int n = GetTradeCount();
      if(n < 2) return 0.0;
      double mean   = m_sumProfit / n;
      double var    = (m_sumProfitSq / n) - (mean * mean);
      double stddev = MathSqrt(MathMax(0.0, var));
      return (stddev > 1e-10) ? mean / stddev : 0.0;
   }

   // Calmar: net profit / max absolute drawdown.
   // > 1.0 = recovered more than worst drawdown. > 3.0 = strong.
   double GetCalmarRatio()
   {
      double net = GetNetProfit();
      if(m_maxDrawdownAbs < 1e-10)
         return (net > 0) ? 999.0 : 0.0;
      return net / m_maxDrawdownAbs;
   }

   // Wilson score 95% CI for win rate. lower/upper in percent (0–100).
   // Reliable at n ≥ 30. Check against MinSampleRequired() first.
   void GetWinRateCI95(double &lower, double &upper)
   {
      lower = 0.0; upper = 100.0;
      int n = GetTradeCount();
      if(n <= 0) return;
      double p     = GetWinRate() / 100.0;
      double z     = 1.96;
      double z2    = z * z;
      double denom = 1.0 + z2 / n;
      double ctr   = (p + z2 / (2.0 * n)) / denom;
      double margin= (z / denom) * MathSqrt(p * (1.0-p) / n + z2 / (4.0*n*n));
      lower = MathMax(0.0,   (ctr - margin) * 100.0);
      upper = MathMin(100.0, (ctr + margin) * 100.0);
   }

   // Minimum trades for 80% power detecting targetWR vs nullWR (default 50%)
   // at one-tailed α = 0.05.  Example: target=60%, null=50% → ~98 trades.
   static int MinSampleRequired(double targetWR = 60.0, double nullWR = 50.0)
   {
      double p1 = targetWR / 100.0;
      double p0 = nullWR   / 100.0;
      if(MathAbs(p1 - p0) < 1e-10) return 9999;
      double zA = 1.645;   // one-tailed α=0.05
      double zB = 0.842;   // 80% power
      double num = MathPow(zA * MathSqrt(p0*(1.0-p0)) + zB * MathSqrt(p1*(1.0-p1)), 2);
      double den = MathPow(p1 - p0, 2);
      return (int)MathCeil(num / den);
   }

   //──────────────────────────────────────────────────────────────────
   // Area B — Execution Quality
   //──────────────────────────────────────────────────────────────────
   double GetAvgSlippagePts()
   {
      return (m_slippageCount > 0) ? m_sumSlippagePts / m_slippageCount : 0.0;
   }
   double GetWorstSlippagePts() { return m_worstSlippagePts; }

   //──────────────────────────────────────────────────────────────────
   void PrintSummary()
   {
      Print("─────────────────────────────────────────");
      Print(StringFormat("  Trades   : %d  (W:%d / L:%d)", GetTradeCount(), m_wins, m_losses));
      Print(StringFormat("  WinRate  : %.1f%%",    GetWinRate()));
      Print(StringFormat("  Avg RR   : %.2f",      GetAverageRR()));
      Print(StringFormat("  PF       : %.2f",      GetProfitFactor()));
      Print(StringFormat("  Net P&L  : %.2f",      GetNetProfit()));
      Print(StringFormat("  MaxDD    : %.2f%% (%.2f abs)", m_maxDrawdown, m_maxDrawdownAbs));
      Print(StringFormat("  Avg MAE  : %.5f (%.1f%% of SL)", GetAvgMAE(), GetAvgMAEPct()));
      Print(StringFormat("  Avg MFE  : %.5f (%.1f%% of TP)", GetAvgMFE(), GetAvgMFEPct()));
      // Area A
      Print(StringFormat("  Expectancy: %.2f  Sharpe: %.2f  Calmar: %.2f",
            GetExpectancy(), GetSharpeRatio(), GetCalmarRatio()));
      double ciLo, ciHi;
      GetWinRateCI95(ciLo, ciHi);
      int minN = MinSampleRequired();
      string samp = (GetTradeCount() < minN) ? " *** UNDER-SAMPLED" : "";
      Print(StringFormat("  WR 95%% CI: [%.1f%% – %.1f%%]  min_n=%d%s",
            ciLo, ciHi, minN, samp));
      // Area B
      if(m_slippageCount > 0)
      {
         int total = m_slippageCount + m_externalRejectCount;
         double rejectRate = (total > 0)
                           ? (double)m_externalRejectCount / total * 100.0 : 0.0;
         Print(StringFormat("  Avg slip  : %.1f pts  worst=%.1f pts",
               GetAvgSlippagePts(), GetWorstSlippagePts()));
         Print(StringFormat("  Reject rate: %.1f%% (%d/%d orders)",
               rejectRate, m_externalRejectCount, total));
      }
      Print("─────────────────────────────────────────");
   }

private:
   void UpdateDrawdown()
   {
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      if(equity > m_peakEquity) m_peakEquity = equity;
      if(m_peakEquity > 0)
      {
         double ddPct = ((m_peakEquity - equity) / m_peakEquity) * 100.0;
         if(ddPct > m_maxDrawdown) m_maxDrawdown = ddPct;
      }
      double ddAbs = m_peakEquity - equity;
      if(ddAbs > m_maxDrawdownAbs) m_maxDrawdownAbs = ddAbs;
   }
};
#endif // ASE_TELEMETRY_MQH
