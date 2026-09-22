#ifndef ASE_CONFLUENCEENGINE_MQH
#define ASE_CONFLUENCEENGINE_MQH
#include "../Models/ASE_EvidenceTypes.mqh"
#include "../Models/ASE_ConfluenceTypes.mqh"
#include "ASE_ConfluenceSequence.mqh"
//+------------------------------------------------------------------+
//| ACE v4.0 — Confluence Engine (Plan §9-12, §22)                    |
//|                                                                  |
//| Pure function of a SetupEvidenceSet. Archetype-agnostic — fills   |
//| direction/longScore/shortScore/separation/conflict/avgFreshness   |
//| only. Setup Classifier (separate file) consumes this result plus  |
//| the same evidence set to fill archetype/core/enhancers/grade.     |
//|                                                                  |
//| SCORING MODEL — plan §22 proposes six weighted families summing   |
//| to 100 at a finer evidence granularity than the current codebase  |
//| exposes (e.g. "structural zone" and "trigger-to-entry drift" have |
//| no existing detector — see file-level note in                    |
//| ASE_SetupEvidenceCollector.mqh). This table folds §22's weights   |
//| onto the evidence types that actually exist today; each fold is   |
//| commented at its line. NOTE (v4.0 fix, found while promoting two   |
//| zero-weight lines): TotalWeight() below is DEAD CODE — Evaluate()  |
//| normalises against a hardcoded 100.0, not this table's dynamic     |
//| sum, despite what an earlier version of this comment claimed. The  |
//| nominal total (currently 98, was 93) is therefore an approximation |
//| against a fixed 100 denominator, not an exact-100 sum — acceptable |
//| for now, but TotalWeight() should either be wired into Evaluate()  |
//| or deleted; leaving both in place is misleading.                   |
//|                                                                  |
//| v4.0 — new file. Its output is never read by any v3 execution     |
//| path — see CASE_SetupClassifier / CASE_SetupAnalytics for the     |
//| explicit authority boundary this stops at.                       |
//+------------------------------------------------------------------+
class CASE_ConfluenceEngine
{
private:
   double m_liqWeightOverride;   // v4.0 — Level 2 adaptation box value, or <0 to use the static default

   double WeightOf(ENUM_EVIDENCE_TYPE t) const
   {
      switch(t)
      {
         case EVID_H1_BOS:           return 20.0;
         case EVID_H1_CHOCH:         return 15.0;  // Structural: H1 BOS 15 + BOS quality 5 (folded — no separate quality sub-score exposed)
         case EVID_H4_ALIGNMENT:     return 5.0;   // Structural: H4 alignment
         case EVID_M15_FVG:          return 8.0;   // Location: FVG
         case EVID_M15_EMA_PULLBACK: return 5.0;   // Location: EMA pullback ("structural zone" 7pts has no detector — omitted, not fabricated)
         case EVID_M15_COMPRESSION:  return 3.0;   // v4.0 fix — promoted from 0.0 (was DNA/logging-only per plan §22). Interim nominal weight, not evidence-derived; revisit once compression-present setups have enough observations to validate the figure. See ASE_ConfluenceEngine.mqh file header re: nominal total vs hardcoded 100.0 normalization.
         case EVID_LIQUIDITY_SWEEP:  return (m_liqWeightOverride >= 0.0) ? m_liqWeightOverride : 12.0;  // Liquidity: HTF pool 8 + sweep 8, folded — Level 2 adaptation box target (see ASE_SetupAnalytics.mqh)
         case EVID_M1_REJECTION:     return 8.0;   // Liquidity: sweep/rejection (rejection half)
         case EVID_M15_DISPLACEMENT: return 8.0;   // Momentum: M15 displacement
         case EVID_M1_DISPLACEMENT:  return 5.0;   // Momentum: M1 displacement
         case EVID_M1_MICRO_BOS:     return 7.0;   // Momentum: M1 micro BOS
         case EVID_M1_EMA_ALIGN:     return 2.0;   // v4.0 fix — promoted from 0.0 (was "weakest M1 fallback, not separately scored"). Small interim nominal weight, not evidence-derived; revisit once observation data supports a real figure.
         case EVID_VOLATILITY_STATE: return 8.0;   // Environment: regime 5 + volatility expansion 3, folded (one regime detector)
         case EVID_SESSION_QUALITY:  return 2.0;   // Environment: session
         case EVID_SPREAD_QUALITY:   return 5.0;   // Execution: spread 2 + drift 3, folded (drift has no pre-execution detector)
         default:                    return 0.0;
      }
   }

   double TotalWeight() const
   {
      // Not cached: WeightOf(EVID_LIQUIDITY_SWEEP) depends on
      // m_liqWeightOverride, which can change between calls (Level 2
      // adaptation). 15 iterations is negligible next to the CopyBuffer
      // calls already made once per M1 bar upstream of this.
      double total = 0.0;
      for(int t = EVID_H1_BOS; t <= EVID_SPREAD_QUALITY; t++)
         total += WeightOf((ENUM_EVIDENCE_TYPE)t);
      return total;
   }

double FreshnessFactor(const SetupEvidence &e) const
   {
      int maxBars=InpAceV4FreshnessMaxM1Bars;
      if(e.sourceTF==PERIOD_M15) maxBars=InpAceV4FreshnessMaxM15Bars;
      else if(e.sourceTF==PERIOD_H1 || e.sourceTF==PERIOD_H4) maxBars=InpAceV4FreshnessMaxH1Bars;
      if(maxBars<=0) return 1.0;
      double f=1.0-(double)e.freshnessBars/(double)maxBars;
      return MathMax(0.0,MathMin(1.0,f));
   }

public:
   CASE_ConfluenceEngine() : m_liqWeightOverride(-1.0) {}

   // v4.0 Level 2 — set once per evaluation from
   // CASE_SetupAnalytics::LiquidityWeightForNextEval(), which already
   // enforces the AUTH_CONTROLLED gate via AdaptationBox.Apply().
   // Passing < 0 (or never calling this) uses the static 12.0 default.
   void SetLiquidityWeightOverride(double w) { m_liqWeightOverride = w; }

   void Evaluate(const SetupEvidenceSet &ev, ConfluenceResult &out)
   {
      out.Clear();
      out.timestamp = ev.evalTime;
      double longRaw=0.0, shortRaw=0.0;
      double familyRaw[7]={0,0,0,0,0,0,0};
      double familyMax[7]={0,25,20,20,20,10,5};
      double freshSum=0.0; int freshCount=0;

      for(int i=0;i<ev.count;i++)
      {
         if(!ev.items[i].active) continue;
         double w=WeightOf(ev.items[i].evidType);
         if(w<=0.0) continue;
         double freshness=FreshnessFactor(ev.items[i]);
         if(freshness<=0.0) continue;
         double contribution=w*freshness;
         int fam=(int)ev.items[i].family;
         if(fam>=1 && fam<=6)
         {
            // Family cap prevents multiple correlated measurements from
            // becoming artificial independent confirmation.
            familyRaw[fam]=MathMin(familyMax[fam],familyRaw[fam]+contribution);
         }
         if(ev.items[i].direction==DIR_LONG) longRaw+=contribution;
         else if(ev.items[i].direction==DIR_SHORT) shortRaw+=contribution;
         freshSum+=freshness; freshCount++;
      }

      // Rebuild directional totals from capped family contributions so
      // correlated evidence cannot inflate the directional score.
      longRaw=0.0; shortRaw=0.0;
      for(int fam=1;fam<=6;fam++)
      {
         // Determine which direction owns the strongest active evidence in the family.
         double l=0.0,sr=0.0;
         for(int i=0;i<ev.count;i++)
         {
            if(!ev.items[i].active || ev.items[i].family!=(ENUM_EVIDENCE_FAMILY)fam) continue;
            double w=WeightOf(ev.items[i].evidType)*FreshnessFactor(ev.items[i]);
            if(ev.items[i].direction==DIR_LONG) l+=w;
            else if(ev.items[i].direction==DIR_SHORT) sr+=w;
         }
         if(l>0 || sr>0)
         {
            double cap=familyMax[fam];
            longRaw += MathMin(cap,l);
            shortRaw += MathMin(cap,sr);
         }
      }

      double totalW=100.0;
      out.longScore=MathMin(100.0,(longRaw/totalW)*100.0);
      out.shortScore=MathMin(100.0,(shortRaw/totalW)*100.0);
      out.separation=MathAbs(out.longScore-out.shortScore);
      out.avgFreshness=(freshCount>0)?freshSum/freshCount:0.0;
      out.direction=(out.longScore>out.shortScore)?DIR_LONG:(out.shortScore>out.longScore)?DIR_SHORT:DIR_NONE;

      out.conflict.Clear();
      if(out.direction!=DIR_NONE)
      {
         ENUM_TRADE_DIRECTION losing=(out.direction==DIR_LONG)?DIR_SHORT:DIR_LONG;
         for(int i=0;i<ev.count;i++)
         {
            if(!ev.items[i].active || ev.items[i].direction!=losing) continue;
            double w=WeightOf(ev.items[i].evidType);
            if(w<=0.0) continue;
            if(ev.items[i].family==FAM_STRUCTURE || ev.items[i].family==FAM_MOMENTUM)
            {
               out.conflict.hasConflict=true;
               out.conflict.reason=StringFormat("%s-family evidence opposes %s: %s",
                  (ev.items[i].family==FAM_STRUCTURE?"Structure":"Momentum"),
                  out.direction==DIR_LONG?"LONG":"SHORT",ev.items[i].reason);
               break;
            }
         }
      }

      CASE_ConfluenceSequence seq;
      SequenceResult sr;
      seq.Evaluate(ev,out.direction,sr);
      out.sequenceComplete=sr.complete;
      out.sequenceCoherent=sr.coherent;
      out.sequenceQuality=sr.quality;
      out.sequenceInversions=sr.inversionCount;
      out.sequenceAgeBars=sr.maxAgeBars;
      out.firstCoreTime=sr.firstCoreTime;
      out.finalCoreTime=sr.finalCoreTime;
      if(out.direction!=DIR_NONE && !sr.coherent && out.conflict.reason=="")
      {
         out.conflict.hasConflict=true;
         out.conflict.reason=sr.reason;
      }
   }
};
#endif // ASE_CONFLUENCEENGINE_MQH
