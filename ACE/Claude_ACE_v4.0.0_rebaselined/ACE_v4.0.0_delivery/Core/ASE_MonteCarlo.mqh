#ifndef ASE_MONTECARLO_MQH
#define ASE_MONTECARLO_MQH
#include "../Models/ASE_Structs.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Monte Carlo Survivability Engine                        |
//| Phase 2: Real simulation replacing the single-formula stub       |
//|                                                                  |
//| Simulations (spec §10.1):                                        |
//|   1. Trade shuffle         — sequence dependency test            |
//|   2. Slippage injection    — execution realism                   |
//|   3. Spread expansion      — broker stress test                  |
//|   4. Skipped trades (5%)   — missed signal simulation            |
//|   5. Delayed execution     — latency simulation                  |
//+------------------------------------------------------------------+

#define MC_MAX_TRADES  500
#define MC_RUNS        200   // simulation iterations per test

class CASE_MonteCarlo
{
private:
   double m_profits[];    // trade P&L array for simulation
   double m_slDists[];    // SL distances for slippage modelling
   int    m_tradeCount;
   uint   m_seed;

public:
   CASE_MonteCarlo() : m_tradeCount(0), m_seed(12345) {}

   void Initialize()
   {
      ArrayResize(m_profits,  MC_MAX_TRADES);
      ArrayResize(m_slDists,  MC_MAX_TRADES);
      m_tradeCount = 0;
      // v3.8.0 fix: TimeCurrent() has 1-second resolution — two backtests
      // run within the same second get identical shuffle sequences, making
      // the robustness test deterministic. GetTickCount() has millisecond
      // resolution; XOR with InpMagicNumber further differentiates runs
      // even when called at the same wall-clock millisecond.
      m_seed = (uint)GetTickCount() ^ (uint)InpMagicNumber;
   }

   // Feed trade data into the simulator
   void AddTrade(double profit, double slDistance)
   {
      if(m_tradeCount >= MC_MAX_TRADES) return;
      m_profits[m_tradeCount] = profit;
      m_slDists[m_tradeCount] = slDistance;
      m_tradeCount++;
   }

   void ClearTrades() { m_tradeCount = 0; }

   //------------------------------------------------------------------
   // Run full Monte Carlo battery — returns survivability score 0–100
   // Score < 60 = fragile (reject in optimizer)
   // Score ≥ 80 = robust
   //------------------------------------------------------------------
   double RunFullBattery(double &outWorstDD, double &outAvgNet)
   {
      if(m_tradeCount < 10) return 0.0;

      double scoreSum = 0.0;
      double totalWorstDD = 0.0;
      double totalNet     = 0.0;

      // Run each simulation type and accumulate scores
      scoreSum    += SimulateShuffle(totalWorstDD, totalNet);
      scoreSum    += SimulateSlippage(totalWorstDD, totalNet);
      scoreSum    += SimulateSpreadExpansion(totalWorstDD, totalNet);
      scoreSum    += SimulateSkippedTrades(totalWorstDD, totalNet);
      scoreSum    += SimulateDelayedExecution(totalWorstDD, totalNet);

      outWorstDD = totalWorstDD / 5.0;
      outAvgNet  = totalNet     / 5.0;

      return scoreSum / 5.0;   // average across 5 simulation types
   }

   // Legacy simple interface (for OptimizerBridge)
   double Simulate(double expectancy, double variance, int trades)
   {
      if(trades < 10)     return -1000.0;
      if(expectancy <= 0) return -500.0;

      double score = expectancy;
      score -= variance * 0.5;
      score += MathSqrt((double)trades) * 0.1;

      // If we have real trades loaded, adjust with battery result
      if(m_tradeCount >= 10)
      {
         double worstDD, avgNet;
         double batteryScore = RunFullBattery(worstDD, avgNet);
         score *= (batteryScore / 100.0);  // scale by survivability
         if(worstDD > 25.0) score -= 50.0; // hard penalty for catastrophic DD
      }

      return score;
   }

   bool PassesStressTest(double maxDrawdownPct, double recoveryFactor)
   {
      if(maxDrawdownPct > 25.0) return false;
      if(recoveryFactor < 1.5)  return false;
      return true;
   }

   double CalcRecoveryFactor(double netProfit, double maxDrawdown)
   {
      if(maxDrawdown < 1e-10) return (netProfit > 0) ? 999.0 : 0.0;
      return netProfit / maxDrawdown;
   }

private:
   //------------------------------------------------------------------
   // 1. Trade shuffle — tests sequence dependency
   //    Shuffles the trade P&L order MC_RUNS times, measures worst DD
   //------------------------------------------------------------------
   double SimulateShuffle(double &worstDD, double &avgNet)
   {
      double localProfits[];
      ArrayResize(localProfits, m_tradeCount);

      double sumNet = 0.0;
      double localWorstDD = 0.0;
      int    passes = 0;

      for(int run = 0; run < MC_RUNS; run++)
      {
         ArrayCopy(localProfits, m_profits, 0, 0, m_tradeCount);
         ShuffleArray(localProfits, m_tradeCount);

         double equity = 0.0, peak = 0.0, maxDD = 0.0;
         for(int i = 0; i < m_tradeCount; i++)
         {
            equity += localProfits[i];
            if(equity > peak) peak = equity;
            double dd = (peak > 0) ? (peak - equity) / peak * 100.0 : 0.0;
            if(dd > maxDD) maxDD = dd;
         }
         if(maxDD > localWorstDD) localWorstDD = maxDD;
         sumNet += equity;
         if(maxDD <= 25.0 && equity > 0) passes++;
      }

      worstDD += localWorstDD;
      avgNet  += sumNet / MC_RUNS;
      return (double)passes / MC_RUNS * 100.0;
   }

   //------------------------------------------------------------------
   // 2. Slippage injection — adds random adverse slippage per trade
   //    Slippage = 0–30% of SL distance (realistic broker range)
   //------------------------------------------------------------------
   double SimulateSlippage(double &worstDD, double &avgNet)
   {
      double equity = 0.0, peak = 0.0, maxDD = 0.0;
      double sumNet = 0.0;
      int    passes = 0;

      for(int run = 0; run < MC_RUNS; run++)
      {
         equity = 0.0; peak = 0.0; maxDD = 0.0;
         for(int i = 0; i < m_tradeCount; i++)
         {
            double slipFraction = RandDouble() * 0.30;  // 0–30% of SL
            double slipCost     = m_slDists[i] * slipFraction;
            // Slippage always hurts — worsens losses, reduces wins
            double adjusted = m_profits[i] - MathAbs(slipCost);
            equity += adjusted;
            if(equity > peak) peak = equity;
            double dd = (peak > 0) ? (peak - equity) / peak * 100.0 : 0.0;
            if(dd > maxDD) maxDD = dd;
         }
         sumNet += equity;
         if(maxDD <= 25.0 && equity > 0) passes++;
      }

      worstDD += maxDD;
      avgNet  += sumNet / MC_RUNS;
      return (double)passes / MC_RUNS * 100.0;
   }

   //------------------------------------------------------------------
   // 3. Spread expansion — multiplies all losses by 1.2–1.5×
   //    Models broker spread widening during volatility
   //------------------------------------------------------------------
   double SimulateSpreadExpansion(double &worstDD, double &avgNet)
   {
      double equity = 0.0, peak = 0.0, maxDD = 0.0;
      double sumNet = 0.0;
      int    passes = 0;

      for(int run = 0; run < MC_RUNS; run++)
      {
         equity = 0.0; peak = 0.0; maxDD = 0.0;
         for(int i = 0; i < m_tradeCount; i++)
         {
            double p = m_profits[i];
            if(p < 0)
            {
               double mult = 1.2 + RandDouble() * 0.3;  // 1.2–1.5×
               p *= mult;
            }
            equity += p;
            if(equity > peak) peak = equity;
            double dd = (peak > 0) ? (peak - equity) / peak * 100.0 : 0.0;
            if(dd > maxDD) maxDD = dd;
         }
         sumNet += equity;
         if(maxDD <= 25.0 && equity > 0) passes++;
      }

      worstDD += maxDD;
      avgNet  += sumNet / MC_RUNS;
      return (double)passes / MC_RUNS * 100.0;
   }

   //------------------------------------------------------------------
   // 4. Skipped trades (5%) — randomly removes ~5% of signals
   //    Models missed entries due to latency/spread/connectivity
   //------------------------------------------------------------------
   double SimulateSkippedTrades(double &worstDD, double &avgNet)
   {
      double equity = 0.0, peak = 0.0, maxDD = 0.0;
      double sumNet = 0.0;
      int    passes = 0;

      for(int run = 0; run < MC_RUNS; run++)
      {
         equity = 0.0; peak = 0.0; maxDD = 0.0;
         for(int i = 0; i < m_tradeCount; i++)
         {
            if(RandDouble() < 0.05) continue;   // 5% skip rate
            equity += m_profits[i];
            if(equity > peak) peak = equity;
            double dd = (peak > 0) ? (peak - equity) / peak * 100.0 : 0.0;
            if(dd > maxDD) maxDD = dd;
         }
         sumNet += equity;
         if(maxDD <= 25.0 && equity > 0) passes++;
      }

      worstDD += maxDD;
      avgNet  += sumNet / MC_RUNS;
      return (double)passes / MC_RUNS * 100.0;
   }

   //------------------------------------------------------------------
   // 5. Delayed execution — shifts some wins to breakeven losses
   //    Models 3% of entries being filled late (missed the move)
   //------------------------------------------------------------------
   double SimulateDelayedExecution(double &worstDD, double &avgNet)
   {
      double equity = 0.0, peak = 0.0, maxDD = 0.0;
      double sumNet = 0.0;
      int    passes = 0;

      for(int run = 0; run < MC_RUNS; run++)
      {
         equity = 0.0; peak = 0.0; maxDD = 0.0;
         for(int i = 0; i < m_tradeCount; i++)
         {
            double p = m_profits[i];
            // 3% of trades delayed: win becomes breakeven, loss stays loss
            if(RandDouble() < 0.03 && p > 0) p = 0.0;
            equity += p;
            if(equity > peak) peak = equity;
            double dd = (peak > 0) ? (peak - equity) / peak * 100.0 : 0.0;
            if(dd > maxDD) maxDD = dd;
         }
         sumNet += equity;
         if(maxDD <= 25.0 && equity > 0) passes++;
      }

      worstDD += maxDD;
      avgNet  += sumNet / MC_RUNS;
      return (double)passes / MC_RUNS * 100.0;
   }

   //------------------------------------------------------------------
   // Fisher-Yates shuffle
   //------------------------------------------------------------------
   void ShuffleArray(double &arr[], int count)
   {
      for(int i = count - 1; i > 0; i--)
      {
         int j = (int)(RandDouble() * (i + 1));
         double tmp = arr[i];
         arr[i] = arr[j];
         arr[j] = tmp;
      }
   }

   // Simple LCG random in [0, 1)
   double RandDouble()
   {
      m_seed = m_seed * 1664525 + 1013904223;
      return (double)(m_seed & 0x7FFFFFFF) / 2147483648.0;
   }
};
#endif // ASE_MONTECARLO_MQH
