#ifndef ASE_ADAPTIVEENGINE_MQH
#define ASE_ADAPTIVEENGINE_MQH
#include "../Models/ASE_AdaptiveTypes.mqh"
#include "../Models/ASE_ConfluenceTypes.mqh"
#include "../Models/ASE_EvidenceTypes.mqh"
#include "ASE_ConfluenceSequence.mqh"
#include "ASE_WalkForwardEngine.mqh"
#include "../Models/ASE_Config.mqh"

struct AdaptiveDecision
{
   ENUM_ADAPT_AUTHORITY authority;
   bool liveEligible;
   bool shadowAEligible;
   bool shadowBEligible;
   bool promotionEligible;
   double liveThreshold;
   double priority;
   string reason;
   void Clear(){ authority=AUTH_OBSERVE; liveEligible=false; shadowAEligible=false; shadowBEligible=false; promotionEligible=false; liveThreshold=80.0; priority=1.0; reason=""; }
};

struct AdaptivePolicyState
{
   string name;
   long samples;
   long wins;
   double sumR;
   long oosSamples;
   long oosWins;
   double oosSumR;
   double threshold;
   double lastThreshold;
   datetime lastAdapt;
   int cooldownEvents;
   bool validated;
   long recentSamples; double recentSumR;
   long firstHalfSamples; double firstHalfSumR; long secondHalfSamples; double secondHalfSumR;
   double cumulativeR; double peakR; double maxDrawdownR;
   int regimeSamples[5];
   void Clear(){name="";samples=0;wins=0;sumR=0;oosSamples=0;oosWins=0;oosSumR=0;threshold=80;lastThreshold=80;lastAdapt=0;cooldownEvents=0;validated=false;recentSamples=0;recentSumR=0;firstHalfSamples=0;firstHalfSumR=0;secondHalfSamples=0;secondHalfSumR=0;cumulativeR=0;peakR=0;maxDrawdownR=0;for(int i=0;i<5;i++)regimeSamples[i]=0;}
   double AvgR() const { return samples>0?sumR/(double)samples:0.0; }
   double WR() const { return samples>0?(double)wins/(double)samples:0.0; }
   double OOSAvgR() const { return oosSamples>0?oosSumR/(double)oosSamples:0.0; }
};

struct AdaptiveShadowPending
{
   bool active; int arm; ENUM_SETUP_ARCHETYPE archetype; ENUM_TRADE_DIRECTION direction;
   double entry; double sl; double tp; datetime opened; int bars;
   void Clear(){active=false;arm=0;archetype=ARCH_NONE;direction=DIR_NONE;entry=0;sl=0;tp=0;opened=0;bars=0;}
};
#define ADAPT_MAX_PENDING 40

class CASE_AdaptiveEngine
{
private:
   AdaptivePolicyState m_live[5];
   AdaptivePolicyState m_shadowA[5];
   AdaptivePolicyState m_shadowB[5];
   datetime m_lastLearning;
   long m_totalObservations;
   string m_statePath;
   bool m_loaded;
   string m_lastDNA;
   bool m_lastHasLiquidity; long m_liqWithN; long m_liqWithoutN; double m_liqWithR; double m_liqWithoutR;
   double m_liqWeight; int m_liqCooldown;
   AdaptiveShadowPending m_pending[ADAPT_MAX_PENDING];
   ShadowModelState m_shadowStateA[5];
   ShadowModelState m_shadowStateB[5];

   int ArchIndex(ENUM_SETUP_ARCHETYPE a) const
   {
      switch(a){case ARCH_TREND_CONTINUATION:return 0;case ARCH_LIQUIDITY_REVERSAL:return 1;case ARCH_COMPRESSION_EXPANSION:return 2;case ARCH_PULLBACK_CONTINUATION:return 3;case ARCH_STRUCTURAL_REVERSAL:return 4;default:return -1;}
   }
   int RegimeIndex(ENUM_MARKET_REGIME r) const
   {
      switch(r){case REGIME_TRENDING:return 0;case REGIME_RANGING:return 1;case REGIME_COMPRESSION:return 2;case REGIME_MANIPULATION:return 3;case REGIME_HIGH_VOL:return 4;default:return -1;}
   }
   ENUM_ADAPT_AUTHORITY Tier(long n) const
   {
      if(n>=InpAceV4AuthValidatedMin) return AUTH_VALIDATED;
      if(n>=InpAceV4AuthControlledMin) return AUTH_CONTROLLED;
      if(n>=InpAceV4AuthCautiousMin) return AUTH_CAUTIOUS;
      return AUTH_OBSERVE;
   }
   // Generalised across all 5 archetypes (was hard-locked to
   // ARCH_TREND_CONTINUATION + REGIME_TRENDING), same rationale as
   // CanActivate() below: none of the other four archetypes carry a
   // regime restriction in their own classifier core check, so locking
   // the shadow-model infrastructure to Trending-only silently excluded
   // them from ever being A/B-tested against a shadow policy.
   bool LivePolicy(const ConfluenceResult &c, ENUM_MARKET_REGIME regime) const
   {
      if(c.archetype==ARCH_NONE || !c.qualified) return false;
      if(c.grade==GRADE_APEX_PLUS || c.grade==GRADE_APEX_A) return true;
      return (InpAceV4AllowBConditional && c.grade==GRADE_APEX_B && c.separation>=25.0);
   }
   bool ShadowPolicyA(const ConfluenceResult &c, const SetupEvidenceSet &ev, ENUM_MARKET_REGIME regime) const
   {
      if(c.archetype==ARCH_NONE || !c.qualified) return false;
      return ev.HasActive(EVID_LIQUIDITY_SWEEP,c.direction);
   }
   bool ShadowPolicyB(const ConfluenceResult &c, const SetupEvidenceSet &ev, ENUM_MARKET_REGIME regime) const
   {
      if(c.archetype==ARCH_NONE || !c.qualified) return false;
      return c.separation>=25.0 && ev.HasActive(EVID_M1_DISPLACEMENT,c.direction) && ev.HasActive(EVID_M1_MICRO_BOS,c.direction);
   }
   void InitPolicy(AdaptivePolicyState &p,string name){p.Clear();p.name=name;p.threshold=80.0;p.lastThreshold=80.0;}
public:
   bool IsOOS(datetime t) const
   {
      if(InpAceV4OOSStartDate=="") return false;
      datetime cut=StringToTime(InpAceV4OOSStartDate);
      return (cut>0 && t>=cut);
   }

   CASE_AdaptiveEngine():m_lastLearning(0),m_totalObservations(0),m_statePath(""),m_loaded(false),m_lastDNA(""),m_lastHasLiquidity(false),m_liqWithN(0),m_liqWithoutN(0),m_liqWithR(0.0),m_liqWithoutR(0.0),m_liqWeight(12.0),m_liqCooldown(0)
   {
      string names[5]={"TrendContinuation","LiquidityReversal","CompressionExpansion","PullbackContinuation","StructuralReversal"};
      for(int i=0;i<5;i++){InitPolicy(m_live[i],names[i]);InitPolicy(m_shadowA[i],names[i]);InitPolicy(m_shadowB[i],names[i]);m_shadowStateA[i].Clear();m_shadowStateA[i].modelName="ShadowA."+names[i];m_shadowStateB[i].Clear();m_shadowStateB[i].modelName="ShadowB."+names[i];}
      for(int i=0;i<ADAPT_MAX_PENDING;i++)m_pending[i].Clear();
   }
   void Initialize(string versionTag)
   {
      m_statePath=StringFormat("ASE_StateLogs\\%s_%s_adaptive2.csv",versionTag,_Symbol);
      LoadState();
      m_loaded=true;
      Print("[ADAPT] Initialized | Learn=1st observation | tiers 20/50/100 | state=",m_statePath);
   }
   void Deinitialize(){ SaveState(); }
   void Observe(const ConfluenceResult &c,const SetupEvidenceSet &ev,ENUM_MARKET_REGIME regime,AdaptiveDecision &out)
   {
      out.Clear();
      int ai=ArchIndex(c.archetype);
      if(ai<0){out.reason="No archetype";return;}
      // Learning clock advances on distinct setup occurrences, not on every tick.
      if(c.setupDNA==m_lastDNA)
      {
         out.authority=Tier(m_live[ai].samples);
         out.liveThreshold=m_live[ai].threshold;
         out.reason="Persistent setup; learning observation already counted";
         return;
      }
      m_lastDNA=c.setupDNA;
      m_lastHasLiquidity=ev.HasActive(EVID_LIQUIDITY_SWEEP,c.direction);
      m_totalObservations++;
      m_live[ai].samples++;
      int ri=RegimeIndex(regime); if(ri>=0)m_live[ai].regimeSamples[ri]++;
      if(ShadowPolicyA(c,ev,regime)) m_shadowA[ai].samples++;
      if(ShadowPolicyB(c,ev,regime)) m_shadowB[ai].samples++;
      ENUM_ADAPT_AUTHORITY t=Tier(m_live[ai].samples); out.authority=t;
      // Adaptation clock: only evaluate candidate changes after a fresh observation and cooldown of 5 observations.
      if(t>=AUTH_CAUTIOUS && m_live[ai].cooldownEvents>=InpAceV4AdaptCooldownObs)
      {
         double edge=m_live[ai].AvgR();
         if(edge>0.10 && m_live[ai].threshold>70.0){m_live[ai].lastThreshold=m_live[ai].threshold;m_live[ai].threshold-=MathMax(0.25,InpAceV4AdaptLearningRate);m_live[ai].lastAdapt=TimeCurrent();m_live[ai].cooldownEvents=0;}
         else if(edge<-0.10 && m_live[ai].threshold<90.0){m_live[ai].lastThreshold=m_live[ai].threshold;m_live[ai].threshold+=MathMax(0.25,InpAceV4AdaptLearningRate);m_live[ai].lastAdapt=TimeCurrent();m_live[ai].cooldownEvents=0;}
      }
      m_live[ai].cooldownEvents++;
      m_liqCooldown++;
      if(m_liqWithN>=5 && m_liqWithoutN>=5 && m_liqCooldown>=InpAceV4AdaptCooldownObs)
      {
         double diff=m_liqWithR/(double)m_liqWithN - m_liqWithoutR/(double)m_liqWithoutN;
         if(MathAbs(diff)>0.10)
         { m_liqWeight+=MathMax(0.25,InpAceV4AdaptLearningRate)*(diff>0?1.0:-1.0); m_liqWeight=MathMax(8.4,MathMin(15.6,m_liqWeight)); m_liqCooldown=0; }
      }
      out.liveThreshold=m_live[ai].threshold;
      out.priority=(m_live[ai].AvgR()>0.0)?1.05:1.0;
      out.liveEligible=(t>=AUTH_VALIDATED && m_live[ai].validated && LivePolicy(c,regime));
      out.shadowAEligible=ShadowPolicyA(c,ev,regime);
      out.shadowBEligible=ShadowPolicyB(c,ev,regime);
      m_shadowStateA[ai].sampleCount=m_shadowA[ai].samples;
      m_shadowStateB[ai].sampleCount=m_shadowB[ai].samples;
      out.promotionEligible=(t>=AUTH_VALIDATED && m_shadowStateA[ai].eligibleForPromotion() && m_shadowStateB[ai].eligibleForPromotion());
      if(InpAceV4Mode==ACEV4_ACTIVE && out.liveEligible) out.reason="Validated adaptive policy permits TrendContinuation";
      else if(InpAceV4Mode==ACEV4_CONDITIONAL && out.liveEligible) out.reason="Validated adaptive policy; conditional authority";
      else if(InpAceV4Mode==ACEV4_ADVISORY) out.reason="Advisory authority only";
      else out.reason="Learning/validation authority not yet sufficient";
      m_lastLearning=TimeCurrent();
   }
   void RegisterShadowCandidate(int arm,const ConfluenceResult &c,double entry,double sl,double tp)
   {
      if(arm<0 || arm>1 || c.archetype==ARCH_NONE || entry<=0 || sl<=0 || tp<=0) return;
      int slot=-1; for(int i=0;i<ADAPT_MAX_PENDING;i++) if(!m_pending[i].active){slot=i;break;}
      if(slot<0){slot=0;for(int i=1;i<ADAPT_MAX_PENDING;i++)if(m_pending[i].opened<m_pending[slot].opened)slot=i;}
      m_pending[slot].Clear();m_pending[slot].active=true;m_pending[slot].arm=arm;m_pending[slot].archetype=c.archetype;m_pending[slot].direction=c.direction;
      m_pending[slot].entry=entry;m_pending[slot].sl=sl;m_pending[slot].tp=tp;m_pending[slot].opened=TimeCurrent();
   }

   void ResolveShadow(datetime barTime,double barHigh,double barLow)
   {
      for(int i=0;i<ADAPT_MAX_PENDING;i++)
      {
         if(!m_pending[i].active || barTime<=m_pending[i].opened) continue;
         m_pending[i].bars++;
         bool sl=(m_pending[i].direction==DIR_LONG)?barLow<=m_pending[i].sl:barHigh>=m_pending[i].sl;
         bool tp=(m_pending[i].direction==DIR_LONG)?barHigh>=m_pending[i].tp:barLow<=m_pending[i].tp;
         bool done=false; double r=0.0;
         if(sl&&tp){if(m_pending[i].bars>=InpAceV4TheoreticalMaxBars){done=true;r=0.0;}}
         else if(sl){done=true;r=-1.0;}
         else if(tp){double rd=MathAbs(m_pending[i].entry-m_pending[i].sl);done=true;r=rd>0?MathAbs(m_pending[i].tp-m_pending[i].entry)/rd:0;}
         else if(m_pending[i].bars>=InpAceV4TheoreticalMaxBars){done=true;r=0.0;}
         if(done){RecordShadowOutcome(m_pending[i].archetype,m_pending[i].arm,r,IsOOS(barTime));m_pending[i].active=false;}
      }
   }

   void RecordOutcome(ENUM_SETUP_ARCHETYPE a,double r,bool oos)
   {
      int i=ArchIndex(a);if(i<0)return;
      if(r>0)m_live[i].wins++;
      if(m_lastHasLiquidity){m_liqWithN++;m_liqWithR+=r;} else {m_liqWithoutN++;m_liqWithoutR+=r;}
      m_live[i].sumR+=r; m_live[i].cumulativeR+=r;
      if(m_live[i].cumulativeR>m_live[i].peakR)m_live[i].peakR=m_live[i].cumulativeR;
      double dd=m_live[i].peakR-m_live[i].cumulativeR; if(dd>m_live[i].maxDrawdownR)m_live[i].maxDrawdownR=dd;
      m_live[i].recentSamples++; m_live[i].recentSumR+=r;
      if(m_live[i].recentSamples>20){m_live[i].recentSamples=1; m_live[i].recentSumR=r;}
      if(m_live[i].samples<=50){m_live[i].firstHalfSamples++;m_live[i].firstHalfSumR+=r;} else {m_live[i].secondHalfSamples++;m_live[i].secondHalfSumR+=r;}
      if(oos){m_live[i].oosSamples++;if(r>0)m_live[i].oosWins++;m_live[i].oosSumR+=r;}
      double oosRetention=(m_live[i].AvgR()!=0.0)?m_live[i].OOSAvgR()/m_live[i].AvgR():0.0;
      bool recent=(m_live[i].recentSamples>=20 && m_live[i].recentSumR>0.0);
      bool longTerm=(m_live[i].samples>=InpAceV4AuthValidatedMin && m_live[i].AvgR()>0.0);
      bool oosOk=(m_live[i].oosSamples>=InpAceV4OOSMinSamples && m_live[i].OOSAvgR()>0.0 && oosRetention>=InpAceV4MinOOSRetention);
      int regimes=0;for(int k=0;k<5;k++)if(m_live[i].regimeSamples[k]>=5)regimes++;
      bool regimeOk=(regimes>=2);
      bool ddOk=(m_live[i].maxDrawdownR<=20.0);
      bool stability=(m_live[i].firstHalfSamples>=20 && m_live[i].secondHalfSamples>=20 && m_live[i].firstHalfSumR/(double)m_live[i].firstHalfSamples>0.0 && m_live[i].secondHalfSumR/(double)m_live[i].secondHalfSamples>0.0);
      m_live[i].validated=(recent&&longTerm&&oosOk&&regimeOk&&ddOk&&stability);
   }
   void RecordShadowOutcome(ENUM_SETUP_ARCHETYPE a,int arm,double r,bool oos)
   {
      int i=ArchIndex(a);if(i<0)return;
      // Write explicit branches because MQL5 struct pointers are not used here.
      if(arm==0){if(r>0)m_shadowA[i].wins++;m_shadowA[i].sumR+=r;if(oos){m_shadowA[i].oosSamples++;if(r>0)m_shadowA[i].oosWins++;m_shadowA[i].oosSumR+=r;}if(m_shadowA[i].samples>=InpAceV4AuthValidatedMin&&m_shadowA[i].oosSamples>=InpAceV4OOSMinSamples&&m_shadowA[i].AvgR()>0&&m_shadowA[i].OOSAvgR()>0&&(m_shadowA[i].OOSAvgR()/m_shadowA[i].AvgR())>=InpAceV4MinOOSRetention)m_shadowA[i].validated=true;}
      else {if(r>0)m_shadowB[i].wins++;m_shadowB[i].sumR+=r;if(oos){m_shadowB[i].oosSamples++;if(r>0)m_shadowB[i].oosWins++;m_shadowB[i].oosSumR+=r;}if(m_shadowB[i].samples>=InpAceV4AuthValidatedMin&&m_shadowB[i].oosSamples>=InpAceV4OOSMinSamples&&m_shadowB[i].AvgR()>0&&m_shadowB[i].OOSAvgR()>0&&(m_shadowB[i].OOSAvgR()/m_shadowB[i].AvgR())>=InpAceV4MinOOSRetention)m_shadowB[i].validated=true;}
      if(arm==0)
      {
         m_shadowStateA[i].sampleCount=m_shadowA[i].samples; m_shadowStateA[i].shadowNetR=m_shadowA[i].sumR;
         m_shadowStateA[i].SetValidation(m_shadowA[i].samples>=20,m_shadowA[i].samples>=InpAceV4AuthValidatedMin,m_shadowA[i].oosSamples>=InpAceV4OOSMinSamples && m_shadowA[i].OOSAvgR()>0.0,m_shadowA[i].samples>=InpAceV4AuthValidatedMin,m_shadowA[i].AvgR()>0.0,m_shadowA[i].samples>=40 && m_shadowA[i].OOSAvgR()>0.0);
      }
      else
      {
         m_shadowStateB[i].sampleCount=m_shadowB[i].samples; m_shadowStateB[i].shadowNetR=m_shadowB[i].sumR;
         m_shadowStateB[i].SetValidation(m_shadowB[i].samples>=20,m_shadowB[i].samples>=InpAceV4AuthValidatedMin,m_shadowB[i].oosSamples>=InpAceV4OOSMinSamples && m_shadowB[i].OOSAvgR()>0.0,m_shadowB[i].samples>=InpAceV4AuthValidatedMin,m_shadowB[i].AvgR()>0.0,m_shadowB[i].samples>=40 && m_shadowB[i].OOSAvgR()>0.0);
      }
   }
   double LiquidityWeight() const { return m_liqWeight; }

   // Generalised across all 5 archetypes (was hard-locked to
   // ARCH_TREND_CONTINUATION + REGIME_TRENDING). Each archetype's own
   // validated/samples/threshold state — already being tracked by
   // Observe() for all five regardless of this gate — now decides its
   // own authority. No blanket regime check here: TrendContinuation's
   // regime==TRENDING requirement is already enforced one layer up, as
   // a CORE evidence item inside CheckTrendContinuation() in
   // ASE_SetupClassifier.mqh — a setup can never even be classified as
   // TrendContinuation outside Trending, so duplicating that check here
   // was redundant for archetype 0 and wrongly blocked the other four
   // (none of which have a regime restriction in their own core check).
   // v4.0.1 Fix -- APEX_B path reconciled against LivePolicy() above.
   // Previously CanActivate() gated APEX_B on m_live[i].threshold<=80.0
   // alone, silently ignoring InpAceV4AllowBConditional -- the input
   // documented as "APEX B may execute only when adaptive authority
   // validates it" had no effect on actual execution authority, only on
   // the advisory LivePolicy() flag. Now both the master switch and the
   // separation floor from LivePolicy() apply here too, AND the archetype
   // must still have earned its own adaptively-tuned threshold <=80 --
   // stricter than either check was alone, not a relaxation.
   bool CanActivate(ENUM_SETUP_ARCHETYPE a,ENUM_SETUP_GRADE grade,ENUM_MARKET_REGIME regime,double separation) const
   {
      int i=ArchIndex(a);if(i<0)return false;
      if(!m_live[i].validated || m_live[i].samples<InpAceV4AuthValidatedMin)return false;
      if(grade==GRADE_APEX_PLUS||grade==GRADE_APEX_A)return true;
      return (grade==GRADE_APEX_B && InpAceV4AllowBConditional && separation>=25.0 && m_live[i].threshold<=80.0);
   }
   string AuthorityName() const { return ASE_AuthorityName(Tier(m_totalObservations)); }
   void LoadState()
   {
      if(m_statePath=="" || !FileIsExist(m_statePath,FILE_COMMON)) return;
      int h=FileOpen(m_statePath,FILE_READ|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,',');
      if(h==INVALID_HANDLE) return;
      while(!FileIsEnding(h))
      {
         string tag=FileReadString(h);
         if(tag=="") break;
         if(tag=="MODEL")
         { for(int k=0;k<9;k++) FileReadString(h); continue; }
         else if(tag=="LIVE" || tag=="SHADOW_A" || tag=="SHADOW_B")
         {
            string name=FileReadString(h); long samples=(long)FileReadNumber(h); long wins=(long)FileReadNumber(h); double sumR=FileReadNumber(h);
            long oosN=(long)FileReadNumber(h); long oosW=(long)FileReadNumber(h); double oosR=FileReadNumber(h); double th=FileReadNumber(h); bool val=((int)FileReadNumber(h))!=0;
            long recentN=0,firstN=0,secondN=0; double recentR=0,firstR=0,secondR=0,cumR=0,peakR=0,maxDDR=0; int rs0=0,rs1=0,rs2=0,rs3=0,rs4=0;
            if(tag=="LIVE")
            { recentN=(long)FileReadNumber(h);recentR=FileReadNumber(h);firstN=(long)FileReadNumber(h);firstR=FileReadNumber(h);secondN=(long)FileReadNumber(h);secondR=FileReadNumber(h);cumR=FileReadNumber(h);peakR=FileReadNumber(h);maxDDR=FileReadNumber(h);rs0=(int)FileReadNumber(h);rs1=(int)FileReadNumber(h);rs2=(int)FileReadNumber(h);rs3=(int)FileReadNumber(h);rs4=(int)FileReadNumber(h); }
            for(int i=0;i<5;i++) if(m_live[i].name==name)
            {
               if(tag=="LIVE")
               { m_live[i].samples=samples;m_live[i].wins=wins;m_live[i].sumR=sumR;m_live[i].oosSamples=oosN;m_live[i].oosWins=oosW;m_live[i].oosSumR=oosR;m_live[i].threshold=th;m_live[i].lastThreshold=th;m_live[i].validated=val;m_live[i].recentSamples=recentN;m_live[i].recentSumR=recentR;m_live[i].firstHalfSamples=firstN;m_live[i].firstHalfSumR=firstR;m_live[i].secondHalfSamples=secondN;m_live[i].secondHalfSumR=secondR;m_live[i].cumulativeR=cumR;m_live[i].peakR=peakR;m_live[i].maxDrawdownR=maxDDR;m_live[i].regimeSamples[0]=rs0;m_live[i].regimeSamples[1]=rs1;m_live[i].regimeSamples[2]=rs2;m_live[i].regimeSamples[3]=rs3;m_live[i].regimeSamples[4]=rs4; }
               else if(tag=="SHADOW_A")
               { m_shadowA[i].samples=samples;m_shadowA[i].wins=wins;m_shadowA[i].sumR=sumR;m_shadowA[i].oosSamples=oosN;m_shadowA[i].oosWins=oosW;m_shadowA[i].oosSumR=oosR;m_shadowA[i].threshold=th;m_shadowA[i].lastThreshold=th;m_shadowA[i].validated=val; }
               else
               { m_shadowB[i].samples=samples;m_shadowB[i].wins=wins;m_shadowB[i].sumR=sumR;m_shadowB[i].oosSamples=oosN;m_shadowB[i].oosWins=oosW;m_shadowB[i].oosSumR=oosR;m_shadowB[i].threshold=th;m_shadowB[i].lastThreshold=th;m_shadowB[i].validated=val; }
               break;
            }
         }
         else if(tag=="PENDING")
         {
            int slot=-1;for(int k=0;k<ADAPT_MAX_PENDING;k++)if(!m_pending[k].active){slot=k;break;}
            int arm=(int)FileReadNumber(h); ENUM_SETUP_ARCHETYPE a=(ENUM_SETUP_ARCHETYPE)(int)FileReadNumber(h); ENUM_TRADE_DIRECTION d=(ENUM_TRADE_DIRECTION)(int)FileReadNumber(h);
            double entry=FileReadNumber(h);double sl=FileReadNumber(h);double tp=FileReadNumber(h);datetime opened=(datetime)FileReadNumber(h);int bars=(int)FileReadNumber(h);
            if(slot>=0){m_pending[slot].Clear();m_pending[slot].active=true;m_pending[slot].arm=arm;m_pending[slot].archetype=a;m_pending[slot].direction=d;m_pending[slot].entry=entry;m_pending[slot].sl=sl;m_pending[slot].tp=tp;m_pending[slot].opened=opened;m_pending[slot].bars=bars;}
         }
         else if(tag=="REGIMES")
         {
            string name=FileReadString(h); for(int i=0;i<5;i++) if(m_live[i].name==name){for(int k=0;k<5;k++)m_live[i].regimeSamples[k]=(int)FileReadNumber(h);break;}
         }
         else if(tag=="META")
         { m_lastDNA=FileReadString(h); m_lastLearning=(datetime)FileReadNumber(h); m_totalObservations=(long)FileReadNumber(h); double lw=FileReadNumber(h); if(lw>0.0)m_liqWeight=MathMax(8.4,MathMin(15.6,lw)); m_liqWithN=(long)FileReadNumber(h); m_liqWithoutN=(long)FileReadNumber(h); m_liqWithR=FileReadNumber(h); m_liqWithoutR=FileReadNumber(h); }
      }
      FileClose(h);
   }

   void SaveState()
   {
      if(m_statePath=="")return;
      int h=FileOpen(m_statePath,FILE_WRITE|FILE_CSV|FILE_COMMON,',');if(h==INVALID_HANDLE)return;
      FileWrite(h,"MODEL","ARCH","SAMPLES","WINS","SUMR","OOSSAMPLES","OOSWINS","OOSSUMR","THRESHOLD","VALIDATED");
      for(int i=0;i<5;i++)
      {
         FileWrite(h,"REGIMES",m_live[i].name,m_live[i].regimeSamples[0],m_live[i].regimeSamples[1],m_live[i].regimeSamples[2],m_live[i].regimeSamples[3],m_live[i].regimeSamples[4]);
         FileWrite(h,"LIVE",m_live[i].name,m_live[i].samples,m_live[i].wins,DoubleToString(m_live[i].sumR,6),m_live[i].oosSamples,m_live[i].oosWins,DoubleToString(m_live[i].oosSumR,6),DoubleToString(m_live[i].threshold,4),m_live[i].validated?1:0,m_live[i].recentSamples,DoubleToString(m_live[i].recentSumR,6),m_live[i].firstHalfSamples,DoubleToString(m_live[i].firstHalfSumR,6),m_live[i].secondHalfSamples,DoubleToString(m_live[i].secondHalfSumR,6),DoubleToString(m_live[i].cumulativeR,6),DoubleToString(m_live[i].peakR,6),DoubleToString(m_live[i].maxDrawdownR,6),m_live[i].regimeSamples[0],m_live[i].regimeSamples[1],m_live[i].regimeSamples[2],m_live[i].regimeSamples[3],m_live[i].regimeSamples[4]);
         FileWrite(h,"SHADOW_A",m_shadowA[i].name,m_shadowA[i].samples,m_shadowA[i].wins,DoubleToString(m_shadowA[i].sumR,6),m_shadowA[i].oosSamples,m_shadowA[i].oosWins,DoubleToString(m_shadowA[i].oosSumR,6),DoubleToString(m_shadowA[i].threshold,4),m_shadowA[i].validated?1:0);
         FileWrite(h,"SHADOW_B",m_shadowB[i].name,m_shadowB[i].samples,m_shadowB[i].wins,DoubleToString(m_shadowB[i].sumR,6),m_shadowB[i].oosSamples,m_shadowB[i].oosWins,DoubleToString(m_shadowB[i].oosSumR,6),DoubleToString(m_shadowB[i].threshold,4),m_shadowB[i].validated?1:0);
      }
      for(int i=0;i<ADAPT_MAX_PENDING;i++) if(m_pending[i].active)
         FileWrite(h,"PENDING",m_pending[i].arm,(int)m_pending[i].archetype,(int)m_pending[i].direction,DoubleToString(m_pending[i].entry,6),DoubleToString(m_pending[i].sl,6),DoubleToString(m_pending[i].tp,6),(long)m_pending[i].opened,m_pending[i].bars);
      FileWrite(h,"META",m_lastDNA,(long)m_lastLearning,(long)m_totalObservations,DoubleToString(m_liqWeight,4),m_liqWithN,m_liqWithoutN,DoubleToString(m_liqWithR,6),DoubleToString(m_liqWithoutR,6));
      FileClose(h);
   }
};
#endif
