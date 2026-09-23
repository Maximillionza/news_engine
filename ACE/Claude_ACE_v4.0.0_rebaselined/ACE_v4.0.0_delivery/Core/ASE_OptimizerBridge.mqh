#ifndef ASE_OPTIMIZERBRIDGE_MQH
#define ASE_OPTIMIZERBRIDGE_MQH
#include "ASE_MonteCarlo.mqh"
#include "ASE_SensitivityMap.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Optimizer Bridge                                        |
//|                                                                  |
//| Hard rejection thresholds (spec §11.2):                          |
//|   WR ≥ 60%    RR ≥ 2.0    PF ≥ 1.4    DD ≤ 25%    OOS ≥ 85%   |
//|                                                                  |
//| Plateau stability architecture:                                  |
//|                                                                  |
//|   MQL5 side (this file):                                         |
//|     neighborFitness1/2/3 parameters exist and are wired to       |
//|     CASE_SensitivityMap.AdjustedFitness(). However, in the       |
//|     Strategy Tester a single OnTester() call cannot evaluate     |
//|     adjacent parameter sets — it only has access to the current  |
//|     run's results. The neighbor parameters are therefore always   |
//|     passed as 0.0 from GetFitnessScore(), which causes the       |
//|     plateau penalty to be SKIPPED (hasNeighbours = false).       |
//|                                                                  |
//|   Python side (ase_optimizer.py — PlateauDetector):              |
//|     This is where plateau validation is authoritative. For each  |
//|     Optuna trial, PlateauDetector perturbs each free parameter   |
//|     by ±1 step, evaluates fitness at those neighbor points, and  |
//|     applies a 50% penalty if the center fitness is an isolated   |
//|     spike (>15% delta from neighbors). This runs AFTER the MQL5  |
//|     tester pass and correctly identifies plateau-stable regions.  |
//|                                                                  |
//|   This split is intentional and correct. Do not attempt to wire  |
//|   neighbor evaluations into OnTester() — the overhead would make |
//|   optimization runs impractical. The Python layer is the right   |
//|   place for multi-point stability checks.                         |
//+------------------------------------------------------------------+
class CASE_OptimizerBridge
{
private:
   CASE_MonteCarlo     m_mc;
   CASE_SensitivityMap m_stability;

public:
   void Initialize() {}

   //------------------------------------------------------------------
   // Primary fitness function — called from OnTester() via
   // StateMachine.GetFitnessScore().
   //------------------------------------------------------------------
   double CalculateFitness(
      double wr,
      double avgRR,
      int    trades,
      double maxDD,
      double pf,
      double oosRetention,
      double neighborFitness1 = 0.0,
      double neighborFitness2 = 0.0,
      double neighborFitness3 = 0.0)
   {
      //── Hard rejections (spec §11.2) ─────────────────────────────
      if(trades       < 10)    return -9000.0;
      if(wr           < 60.0)  return -8000.0;
      if(avgRR        < 2.0)   return -7000.0;
      if(pf           < 1.4)   return -6000.0;
      if(maxDD        > 25.0)  return -5000.0;
      if(oosRetention < 0.85)  return -4000.0;

      // Trade frequency scoring
      double tradeScore = 0.0;
      if(trades >= 10 && trades <= 60)       tradeScore = 10.0;
      else if(trades > 60 && trades <= 120)  tradeScore = 5.0;

      //── Weighted composite ────────────────────────────────────────
      double score = 0.0;
      score += oosRetention  * 30.0;
      score += (wr - 60.0)   *  1.5;
      score += (avgRR - 2.0) * 10.0;
      score += (pf - 1.4)    * 15.0;
      score -= maxDD         *  2.0;
      score += tradeScore;

      //── Monte Carlo survivability ─────────────────────────────────
      double variance = (100.0 - wr) * avgRR;
      score = m_mc.Simulate(score, variance, trades);

      //── Plateau stability (MQL5 side — skipped when no neighbours) ─
      // See architecture note above. This fires only when caller
      // provides real neighbor values (currently never from OnTester).
      bool hasNeighbours = (neighborFitness1 != 0.0 ||
                            neighborFitness2 != 0.0 ||
                            neighborFitness3 != 0.0);
      if(hasNeighbours)
         score = m_stability.AdjustedFitness(score,
                    neighborFitness1, neighborFitness2, neighborFitness3);

      return score;
   }

   // Legacy 5-parameter overload — existing OnTester() calls
   double CalculateFitness(double wr, double avgRR, int trades,
                           double maxDD, double oosRetention)
   {
      return CalculateFitness(wr, avgRR, trades, maxDD, 1.5, oosRetention);
   }
};
#endif // ASE_OPTIMIZERBRIDGE_MQH
