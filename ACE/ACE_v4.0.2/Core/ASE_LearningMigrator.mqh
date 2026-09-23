#ifndef ASE_LEARNINGMIGRATOR_MQH
#define ASE_LEARNINGMIGRATOR_MQH
//+------------------------------------------------------------------+
//| ACE v4.0.2 amendment -- learning-state migration                  |
//|                                                                    |
//| Imports a prior, provenance-clean version's adaptive/analytics      |
//| state into the current version's live engines, additively, after   |
//| a validation pass that must find nothing wrong across all 5        |
//| archetypes. Reuses CASE_AdaptiveEngine/CASE_SetupAnalytics          |
//| themselves (via throwaway instances) for parsing the source files — |
//| no duplicate CSV-parsing logic lives here.                          |
//+------------------------------------------------------------------+
#include "ASE_AdaptiveEngine.mqh"
#include "ASE_SetupAnalytics.mqh"
#include "../Models/ASE_Config.mqh"

struct LearningMigrationResult
{
   bool   success;
   string reason;   // full explanation either way -- refusal detail, or import summary
   void Clear(){success=false;reason="";}
};

class CASE_LearningMigrator
{
private:
   string San(string s) const { string r=s; StringReplace(r,","," ;"); StringReplace(r,"\n"," | "); return r; }

   // Real legitimate threshold range, per CASE_AdaptiveEngine::Observe()'s
   // own nudge logic: "edge>0.10 && threshold>70.0" decreases it,
   // "edge<-0.10 && threshold<90.0" increases it -- i.e. threshold is
   // only ever adapted while it sits strictly inside (70,90). Combined
   // with InitPolicy()'s starting value of 80.0, the legitimate closed
   // range for a value that has only ever moved through that logic is
   // [70,90] inclusive of the untouched-default case.
   bool ThresholdInRange(double th) const { return th>=70.0 && th<=90.0; }

   bool ValidNumber(double x) const
   {
      if(x!=x) return false;              // NaN check (x!=x is only true for NaN)
      if(MathAbs(x)>=1000000.0) return false;
      return true;
   }

public:
   // Attempts to migrate learning state FROM sourceTag INTO the current
   // (real, already-initialized) adaptive/analytics engines for the
   // current symbol. Returns a full result either way; never partially
   // applies a merge -- either every archetype passes validation and the
   // full merge runs, or nothing is mutated on the real instances at all.
   LearningMigrationResult Migrate(CASE_AdaptiveEngine &realAdaptive, CASE_SetupAnalytics &realAnalytics, string sourceTag)
   {
      LearningMigrationResult result; result.Clear();

      if(sourceTag=="")
      {
         result.success=false; result.reason="No source tag configured (InpAceV4MigrateFromTag empty) -- nothing to import.";
         return result;
      }

      // Same path-building pattern as CASE_AdaptiveEngine::Initialize() /
      // CASE_SetupAnalytics::Initialize(), with the SOURCE tag substituted.
      string adaptivePath  = StringFormat("ASE_StateLogs\\%s_%s_adaptive2.csv", sourceTag, _Symbol);
      string analyticsPath = StringFormat("ASE_StateLogs\\%s_%s_v4state2.csv", sourceTag, _Symbol);

      bool adaptiveExists  = FileIsExist(adaptivePath, FILE_COMMON);
      bool analyticsExists = FileIsExist(analyticsPath, FILE_COMMON);
      if(!adaptiveExists || !analyticsExists)
      {
         string missing="";
         if(!adaptiveExists)  missing += adaptivePath + " ";
         if(!analyticsExists) missing += analyticsPath;
         result.success=false;
         result.reason=StringFormat("Source state file(s) for tag '%s' not found: %s -- no migration attempted.", sourceTag, missing);
         return result;
      }

      // Throwaway instances -- parsed via the exact same LoadState() code
      // path the live engines use, pointed at the SOURCE tag.
      CASE_AdaptiveEngine  srcAdaptive;
      CASE_SetupAnalytics  srcAnalytics;
      srcAdaptive.Initialize(sourceTag);
      srcAnalytics.Initialize(sourceTag);

      string srcAdaptiveCleanTag="", srcAnalyticsCleanTag="";
      bool adaptiveClean  = srcAdaptive.IsClean(srcAdaptiveCleanTag);
      bool analyticsClean = srcAnalytics.IsClean(srcAnalyticsCleanTag);
      if(!adaptiveClean || !analyticsClean)
      {
         result.success=false;
         result.reason="source not stamped clean (produced by a pre-integrity-fix build)"
                       + StringFormat(" [adaptive clean=%s tag='%s'; analytics clean=%s tag='%s']",
                          adaptiveClean?"true":"false", srcAdaptiveCleanTag,
                          analyticsClean?"true":"false", srcAnalyticsCleanTag);
         return result;
      }

      // ---- Validation pass across all 5 archetypes ----
      string failures = "";
      int failCount = 0;
      string names[5] = {"TrendContinuation","LiquidityReversal","CompressionExpansion","PullbackContinuation","StructuralReversal"};
      for(int i=0; i<5; i++)
      {
         AdaptivePolicyState live   = srcAdaptive.GetLive(i);
         AdaptivePolicyState shadA  = srcAdaptive.GetShadowA(i);
         AdaptivePolicyState shadB  = srcAdaptive.GetShadowB(i);

         if(live.wins > live.samples)
            { failures += StringFormat("[%s] LIVE wins(%d) > samples(%d); ", names[i], live.wins, live.samples); failCount++; }
         if(live.oosWins > live.oosSamples)
            { failures += StringFormat("[%s] LIVE oosWins(%d) > oosSamples(%d); ", names[i], live.oosWins, live.oosSamples); failCount++; }
         if(live.oosSamples > live.samples)
            { failures += StringFormat("[%s] LIVE oosSamples(%d) > samples(%d); ", names[i], live.oosSamples, live.samples); failCount++; }

         if(!ValidNumber(live.sumR))
            { failures += StringFormat("[%s] LIVE sumR is NaN/absurd (%.6f); ", names[i], live.sumR); failCount++; }
         if(!ValidNumber(live.oosSumR))
            { failures += StringFormat("[%s] LIVE oosSumR is NaN/absurd (%.6f); ", names[i], live.oosSumR); failCount++; }
         if(!ValidNumber(live.maxDrawdownR))
            { failures += StringFormat("[%s] LIVE maxDrawdownR is NaN/absurd (%.6f); ", names[i], live.maxDrawdownR); failCount++; }
         if(!ValidNumber(live.cumulativeR))
            { failures += StringFormat("[%s] LIVE cumulativeR is NaN/absurd (%.6f); ", names[i], live.cumulativeR); failCount++; }
         if(!ValidNumber(live.peakR))
            { failures += StringFormat("[%s] LIVE peakR is NaN/absurd (%.6f); ", names[i], live.peakR); failCount++; }

         int regimeSum=0; for(int k=0;k<5;k++) regimeSum+=live.regimeSamples[k];
         if(regimeSum > live.samples)
            { failures += StringFormat("[%s] LIVE sum(regimeSamples)=%d > samples(%d); ", names[i], regimeSum, live.samples); failCount++; }

         if(!ThresholdInRange(live.threshold))
            { failures += StringFormat("[%s] LIVE threshold(%.4f) outside legitimate range [70,90]; ", names[i], live.threshold); failCount++; }

         // Shadow arms -- same sample/win sanity, no regime/threshold fields to check.
         if(shadA.wins > shadA.samples)
            { failures += StringFormat("[%s] SHADOW_A wins(%d) > samples(%d); ", names[i], shadA.wins, shadA.samples); failCount++; }
         if(shadA.oosWins > shadA.oosSamples)
            { failures += StringFormat("[%s] SHADOW_A oosWins(%d) > oosSamples(%d); ", names[i], shadA.oosWins, shadA.oosSamples); failCount++; }
         if(!ValidNumber(shadA.sumR) || !ValidNumber(shadA.oosSumR))
            { failures += StringFormat("[%s] SHADOW_A sumR/oosSumR NaN/absurd; ", names[i]); failCount++; }

         if(shadB.wins > shadB.samples)
            { failures += StringFormat("[%s] SHADOW_B wins(%d) > samples(%d); ", names[i], shadB.wins, shadB.samples); failCount++; }
         if(shadB.oosWins > shadB.oosSamples)
            { failures += StringFormat("[%s] SHADOW_B oosWins(%d) > oosSamples(%d); ", names[i], shadB.oosWins, shadB.oosSamples); failCount++; }
         if(!ValidNumber(shadB.sumR) || !ValidNumber(shadB.oosSumR))
            { failures += StringFormat("[%s] SHADOW_B sumR/oosSumR NaN/absurd; ", names[i]); failCount++; }
      }

      if(failCount > 0)
      {
         result.success=false;
         result.reason=StringFormat("Migration refused -- %d validation failure(s): %s", failCount, San(failures));
         return result;
      }

      // ---- Merge (additive) into the REAL, live instances ----
      long totalSamplesImported=0, totalPendingTheoImported=0;
      for(int i=0; i<5; i++)
      {
         AdaptivePolicyState live  = srcAdaptive.GetLive(i);
         AdaptivePolicyState shadA = srcAdaptive.GetShadowA(i);
         AdaptivePolicyState shadB = srcAdaptive.GetShadowB(i);

         int regimes[5];
         for(int k=0;k<5;k++) regimes[k]=live.regimeSamples[k];

         realAdaptive.MergeLiveState(i, live.samples, live.wins, live.sumR, live.oosSamples, live.oosWins,
                                      live.oosSumR, regimes, live.cumulativeR, live.maxDrawdownR, live.threshold);
         realAdaptive.MergeShadowState(true,  i, shadA.samples, shadA.wins, shadA.sumR, shadA.oosSamples, shadA.oosWins, shadA.oosSumR, shadA.threshold);
         realAdaptive.MergeShadowState(false, i, shadB.samples, shadB.wins, shadB.sumR, shadB.oosSamples, shadB.oosWins, shadB.oosSumR, shadB.threshold);

         totalSamplesImported += live.samples;
      }

      realAnalytics.MergeLearningTables(srcAnalytics.GetGlobalTable(), srcAnalytics.GetArchTable(),
                                         srcAnalytics.GetArchDirTable(), srcAnalytics.GetRegimeTable(),
                                         srcAnalytics.GetDNATable());

      LearningStatsTable srcGlobalForSummary = srcAnalytics.GetGlobalTable();
      int gi = srcGlobalForSummary.Find("GLOBAL");
      long globalObs = (gi>=0) ? srcGlobalForSummary.buckets[gi].observations : 0;

      result.success=true;
      result.reason=StringFormat(
         "Imported from '%s': %d LIVE archetype samples (all 5 archetypes), shadow A/B states, and %d GLOBAL learning observations across the 5 SetupAnalytics tables. Merge was additive -- current instance's own (fresh) counters were added to, not overwritten.",
         sourceTag, (int)totalSamplesImported, (int)globalObs);
      return result;
   }
};
#endif // ASE_LEARNINGMIGRATOR_MQH
