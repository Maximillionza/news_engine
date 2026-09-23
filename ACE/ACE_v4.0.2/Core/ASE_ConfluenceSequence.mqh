#ifndef ASE_CONFLUENCESEQUENCE_MQH
#define ASE_CONFLUENCESEQUENCE_MQH
#include "../Models/ASE_EvidenceTypes.mqh"

struct SequenceResult
{
   bool     complete;
   bool     coherent;
   double   quality;
   int      observedEvents;
   int      expectedEvents;
   int      inversionCount;
   int      maxAgeBars;
   datetime firstCoreTime;
   datetime finalCoreTime;
   string   expected;
   string   actual;
   string   reason;
   void Clear()
   {
      complete=false; coherent=false; quality=0.0; observedEvents=0; expectedEvents=0;
      inversionCount=0; maxAgeBars=0; firstCoreTime=0; finalCoreTime=0;
      expected=""; actual=""; reason="";
   }
};

class CASE_ConfluenceSequence
{
private:
   int Rank(ENUM_EVIDENCE_TYPE t) const
   {
      switch(t)
      {
         case EVID_H1_BOS: return 1;
         case EVID_H1_CHOCH: return 1;
         case EVID_H4_ALIGNMENT: return 0;
         case EVID_M15_FVG: return 2;
         case EVID_M15_EMA_PULLBACK: return 2;
         case EVID_M15_DISPLACEMENT: return 3;
         case EVID_LIQUIDITY_SWEEP: return 3;
         case EVID_M1_REJECTION: return 4;
         case EVID_M1_DISPLACEMENT: return 5;
         case EVID_M1_MICRO_BOS: return 6;
         default: return -1;
      }
   }
   string Tag(ENUM_EVIDENCE_TYPE t) const
   {
      switch(t)
      {
         case EVID_H1_BOS: return "H1_BOS";
         case EVID_H1_CHOCH: return "H1_CHOCH";
         case EVID_H4_ALIGNMENT: return "H4_ALIGN";
         case EVID_M15_FVG: return "M15_FVG";
         case EVID_M15_EMA_PULLBACK: return "M15_EMA";
         case EVID_M15_DISPLACEMENT: return "M15_DISP";
         case EVID_LIQUIDITY_SWEEP: return "SWEEP";
         case EVID_M1_REJECTION: return "M1_REJ";
         case EVID_M1_DISPLACEMENT: return "M1_DISP";
         case EVID_M1_MICRO_BOS: return "M1_MBOS";
         default: return "";
      }
   }
public:
   void Evaluate(const SetupEvidenceSet &ev, ENUM_TRADE_DIRECTION dir, SequenceResult &out)
   {
      out.Clear();
      if(dir == DIR_NONE) return;
      datetime times[ASE_MAX_EVIDENCE];
      int ranks[ASE_MAX_EVIDENCE];
      string tags[ASE_MAX_EVIDENCE];
      int n=0;
      for(int i=0;i<ev.count;i++)
      {
         if(!ev.items[i].active || ev.items[i].direction != dir) continue;
         int r=Rank(ev.items[i].evidType);
         if(r<0) continue;
         times[n]=ev.items[i].timestamp; ranks[n]=r; tags[n]=Tag(ev.items[i].evidType); n++;
      }
      out.observedEvents=n;
      if(n==0) return;
      // Stable insertion sort by event timestamp; equal timestamps retain detector order.
      for(int i=1;i<n;i++)
      {
         datetime t=times[i]; int r=ranks[i]; string tag=tags[i]; int j=i-1;
         while(j>=0 && times[j]>t) { times[j+1]=times[j]; ranks[j+1]=ranks[j]; tags[j+1]=tags[j]; j--; }
         times[j+1]=t; ranks[j+1]=r; tags[j+1]=tag;
      }
      out.firstCoreTime=times[0]; out.finalCoreTime=times[n-1];
      string actual="";
      for(int i=0;i<n;i++) { if(i>0) actual += " -> "; actual += tags[i]; if(ranks[i]>0) out.expectedEvents++; }
      out.actual=actual;
      int inversions=0;
      for(int i=1;i<n;i++) if(ranks[i]<ranks[i-1]) inversions++;
      out.inversionCount=inversions;
      long ageSec=(long)(TimeCurrent()-times[0]);
      if(ageSec<0) ageSec=0;
      out.maxAgeBars=(int)(ageSec/60);
      out.coherent=(inversions==0);
      // Sequence quality rewards coherent progression and penalises inversions/very stale first evidence.
      double q=1.0 - MathMin(0.60, inversions*0.20);
      if(ageSec>3600) q*=0.75;
      if(ageSec>7200) q*=0.60;
      out.quality=MathMax(0.0,MathMin(1.0,q));
      out.complete=(n>=3 && out.coherent);
      out.expected="H1_BOS -> M15_LOCATION -> M15_MOMENTUM -> M1_CONFIRMATION";
      out.reason=out.complete ? "Coherent evidence progression" :
                 (inversions>0 ? "Evidence arrived out of expected sequence" : "Sequence incomplete");
   }
};
#endif
