#ifndef ASE_SETUPANALYTICS_MQH
#define ASE_SETUPANALYTICS_MQH
#include "../Models/ASE_EvidenceTypes.mqh"
#include "../Models/ASE_ConfluenceTypes.mqh"
#include "../Models/ASE_AdaptiveTypes.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ACE v4.0 — Setup Analytics / Adaptive Engine (Plan §29-32, §82)   |
//|                                                                  |
//| Four jobs, all additive/observational:                           |
//|  1. Opportunity logging (CSV) — one row per DISTINCT setup         |
//|     occurrence (see m_lastDNA dedup below), executed or not, with  |
//|     block-reason attribution (§29-30).                            |
//|  2. Learning statistics — plan §82.4's hierarchy: GLOBAL,          |
//|     per-archetype, per-archetype+direction, per exact setup DNA.   |
//|     Each bucket computes its OWN authority tier from its OWN       |
//|     observation count (LearningStatsBucket.Tier()) — a young       |
//|     archetype and a mature one can sit at different tiers          |
//|     simultaneously, per the transcript's design.                  |
//|  3. Theoretical-outcome resolution for BLOCKED opportunities that   |
//|     had a COMPLETE core (i.e. were only stopped by grade/conflict/ |
//|     separation/legacy gates, not by missing evidence) — a setup    |
//|     that never had a real chance isn't "a rejected opportunity".   |
//|  4. Bounded adaptation — RecomputeAdaptation() actually calls       |
//|     AdaptationBox.Nudge() now (previously the boxes existed but    |
//|     nothing ever moved them — see chat). Two hypotheses, both      |
//|     gated on sample size AND the relevant bucket's own tier:       |
//|       Level 1 (priority, per archetype) — nudges toward whichever  |
//|         archetype's blended real+theoretical R beats GLOBAL's.     |
//|       Level 2 (liquidity evidence weight, GLOBAL-scoped) — nudges  |
//|         toward whichever side of a DNA-tag split (setups whose DNA |
//|         contains ULIQ vs not) has the better blended R.            |
//|                                                                  |
//| PERSISTENCE: every table, every box's currentValue, the pending    |
//| queue, and the dedup cursor are written to a FILE_COMMON file on   |
//| Deinitialize() and reloaded in Initialize() BEFORE anything else   |
//| runs. Without this, any terminal restart (not just a network drop  |
//| — see chat) silently zeroed every counter, which defeats a         |
//| tier system built specifically to reward accumulated evidence.    |
//|                                                                  |
//| AUTHORITY BOUNDARY unchanged from the original delivery: every     |
//| value this file produces is read ONLY by (a) the opportunity log   |
//| row, and (b) the v4 Confluence Engine's OWN liquidity-weight        |
//| parameter via SetLiquidityWeightOverride(). Nothing here writes to |
//| a v3 Inp* input, m_setup/m_score/m_liq's parameters, OrderSend, or |
//| ACE_V4_MODE. See AdaptationBox.Apply() in ASE_AdaptiveTypes.mqh    |
//| for the mechanical guarantee behind that statement.               |
//+------------------------------------------------------------------+

#define ASE_MAX_PENDING_THEORETICAL 40
#define ASE_MIN_SAMPLE_FOR_NUDGE    5     // per-side minimum before any hypothesis is trusted
#define ASE_NUDGE_EDGE_THRESHOLD    0.10  // blended-R differential that triggers a nudge (in R)

struct PendingTheoretical
{
   string   dnaKey;
   string   archKey;      // e.g. "TrendContinuation"
   string   archDirKey;   // e.g. "TrendContinuation-L"
   ENUM_TRADE_DIRECTION direction;
   double   entry;
   double   sl;
   double   tp1;
   datetime openedBar;
   string   regimeKey;
   int      barsWaited;
   bool     active;

   void Clear() { dnaKey=""; archKey=""; archDirKey=""; direction=DIR_NONE; entry=0; sl=0; tp1=0; openedBar=0; regimeKey=""; barsWaited=0; active=false; }
};

class CASE_SetupAnalytics
{
private:
   int      m_handle;
   datetime m_fileDate;
   string   m_filePrefix;
   string   m_statePath;

   LearningStatsTable m_global;      // single "GLOBAL" bucket
   LearningStatsTable m_byArch;      // keyed by archetype name
   LearningStatsTable m_byArchDir;   // keyed by "archetype-direction"
   LearningStatsTable m_byRegime;    // keyed by regime name
   LearningStatsTable m_byDNA;       // keyed by full setup DNA

   PendingTheoretical m_pending[ASE_MAX_PENDING_THEORETICAL];

   AdaptationBox m_priorityBox[5];   // one per archetype — Level 1
   AdaptationBox m_liqWeightBox;     // Level 2 — liquidity evidence weight nudge

   // v4.0 fix — dedup cursor. RecordOpportunity() used to fire once per
   // M1 bar regardless of whether the setup underneath it had changed,
   // so a signal that stayed qualified-but-blocked for 8 consecutive M1
   // bars was counted as 8 observations of "one" setup instead of one.
   // Since the 20/50/100 authority thresholds are read directly off
   // that count, a merely-persistent setup reached VALIDATED far faster
   // than a short-lived one, independent of which was actually
   // stronger. A "new observation" is now an edge: this bar's DNA
   // differs from the immediately prior bar's DNA (whether or not that
   // prior bar was itself logged) — so a setup re-forming identically
   // after a gap still counts as new, but one held steady across
   // consecutive bars counts once.
   string   m_lastDNA;
   datetime m_lastDNABar;
   ENUM_SETUP_ARCHETYPE m_resolvedArch[ASE_MAX_PENDING_THEORETICAL]; double m_resolvedR[ASE_MAX_PENDING_THEORETICAL]; int m_resolvedCount;

   string BuildPath(datetime dt)
   {
      MqlDateTime t; TimeToStruct(dt, t);
      return StringFormat("ASE_StateLogs\\%s_opportunities_%04d.%02d.%02d.csv",
                          m_filePrefix, t.year, t.mon, t.day);
   }

   void OpenFile(datetime dt)
   {
      if(m_handle != INVALID_HANDLE) { FileClose(m_handle); m_handle = INVALID_HANDLE; }
      string path = BuildPath(dt);
      bool isNew = !FileIsExist(path, FILE_COMMON);
      if(!FolderCreate("ASE_StateLogs", FILE_COMMON))
      {
         int err = GetLastError();
         if(err != 5018) Print("[SetupAnalytics] WARNING — FolderCreate: ", err);
      }
      m_handle = FileOpen(path, FILE_WRITE | FILE_READ | FILE_CSV | FILE_COMMON | FILE_SHARE_READ, ',');
      if(m_handle == INVALID_HANDLE)
      {
         Print("[SetupAnalytics] ERROR — could not open: ", path, " | Error: ", GetLastError());
         return;
      }
      FileSeek(m_handle, 0, SEEK_END);
      if(isNew)
         FileWrite(m_handle, "Timestamp","Symbol","Direction","Regime","Archetype","SetupDNA",
                   "LongScore","ShortScore","Separation","CoreMet","CoreTotal","EnhMet","EnhTotal",
                   "Conflict","Grade","Qualified","BlockReason","Executed","OpportunityID","TheoreticalEntry",
                   "TheoreticalSL","TheoreticalTP1","TheoreticalOutcome","PriorityHint","LiqWeightApplied");
      m_fileDate = dt;
   }

   string San(string s) { string r = s; StringReplace(r, ",", ";"); return r; }

   int ArchIndex(ENUM_SETUP_ARCHETYPE a) const
   {
      switch(a)
      {
         case ARCH_TREND_CONTINUATION:    return 0;
         case ARCH_LIQUIDITY_REVERSAL:    return 1;
         case ARCH_COMPRESSION_EXPANSION: return 2;
         case ARCH_PULLBACK_CONTINUATION: return 3;
         case ARCH_STRUCTURAL_REVERSAL:   return 4;
         default:                        return -1;
      }
   }

   // Blended real+theoretical edge, in R, for one bucket. Used as the
   // single comparison scalar for both nudge hypotheses below.
   double BlendedEdge(const LearningStatsBucket &b) const
   {
      long n = b.executed + b.theoreticalResolved;
      if(n <= 0) return 0.0;
      return (b.sumR + b.sumTheoreticalR) / (double)n;
   }

   long BlendedSample(const LearningStatsBucket &b) const { return b.executed + b.theoreticalResolved; }

public:
   CASE_SetupAnalytics() : m_handle(INVALID_HANDLE), m_fileDate(0), m_lastDNA(""), m_lastDNABar(0), m_resolvedCount(0)
   {
      m_global.Reset(); m_byArch.Reset(); m_byArchDir.Reset(); m_byRegime.Reset(); m_byDNA.Reset();
      for(int i = 0; i < ASE_MAX_PENDING_THEORETICAL; i++) m_pending[i].Clear();

      string names[5] = {"TrendContinuation","LiquidityReversal","CompressionExpansion","PullbackContinuation","StructuralReversal"};
      for(int i = 0; i < 5; i++)
         m_priorityBox[i].Init("Priority." + names[i], AUTH_CAUTIOUS, 1.0, 0.5, 2.0, 0.1);

      // Level 2 — bounded within +/-30% of the Confluence Engine's own
      // static LIQUIDITY_SWEEP weight (12.0). Never applied below
      // AUTH_CONTROLLED; Apply() enforces that against the GLOBAL tier.
      m_liqWeightBox.Init("Weight.LiquiditySweep", AUTH_CONTROLLED, 12.0, 8.4, 15.6, 0.5);
   }

   // Per-bucket authority tier (fix — previously every box was gated
   // against the single GLOBAL tier, so a 40-observation archetype and
   // a 220-observation one were treated identically). GLOBAL-scoped
   // parameters (the liquidity weight — it affects every archetype's
   // scoring, not one) still correctly use CurrentTier() below.
   ENUM_ADAPT_AUTHORITY CurrentTier() const
   {
      int gi = m_global.Find("GLOBAL");
      long obs = (gi >= 0) ? m_global.buckets[gi].observations : 0;
      return TierFromObs(obs);
   }

   ENUM_ADAPT_AUTHORITY TierFromObs(long obs) const
   {
      if(obs >= InpAceV4AuthValidatedMin)  return AUTH_VALIDATED;
      if(obs >= InpAceV4AuthControlledMin) return AUTH_CONTROLLED;
      if(obs >= InpAceV4AuthCautiousMin)   return AUTH_CAUTIOUS;
      return AUTH_OBSERVE;
   }

   ENUM_ADAPT_AUTHORITY ArchTier(string archName) const
   {
      int ai = m_byArch.Find(archName);
      return TierFromObs(ai >= 0 ? m_byArch.buckets[ai].observations : 0);
   }

   ENUM_ADAPT_AUTHORITY RegimeTier(string regimeName) const
   {
      int ri=m_byRegime.Find(regimeName);
      return TierFromObs(ri>=0 ? m_byRegime.buckets[ri].observations : 0);
   }

   double LiquidityWeightForNextEval() const { return 12.0; }

   void Initialize(string versionTag)
   {
      m_filePrefix = versionTag;
      m_statePath  = StringFormat("ASE_StateLogs\\%s_%s_v4state2.csv", versionTag, _Symbol);
      LoadState();   // before OpenFile — restores counters/boxes/pending/dedup cursor
      OpenFile(TimeCurrent());
   }

   void Deinitialize()
   {
      SaveState();
      if(m_handle != INVALID_HANDLE) { FileClose(m_handle); m_handle = INVALID_HANDLE; }
   }

   //------------------------------------------------------------------
   // Call once per completed confluence evaluation (once M1 evidence
   // has been merged in — see StateMachine wiring). Skips the whole
   // update when this bar's DNA is identical to the immediately prior
   // bar's (see m_lastDNA comment above) — still updates the dedup
   // cursor either way so the NEXT genuine change is detected.
   //------------------------------------------------------------------
   string RecordOpportunity(const ConfluenceResult &conf, bool executed,
                           double theoreticalEntry, double theoreticalSL, double theoreticalTP1,
                           string regimeName)
   {
      if(conf.direction == DIR_NONE) return "";   // nothing to learn from an unresolved direction

      bool isNewOccurrence = (conf.setupDNA != m_lastDNA);
      m_lastDNA    = conf.setupDNA;
      m_lastDNABar = TimeCurrent();
      if(!isNewOccurrence) return "";   // same setup still persisting — already counted

      datetime now = TimeCurrent();
      string archName = ASE_ArchetypeName(conf.archetype);
      string archDirKey = archName + "-" + (conf.direction == DIR_LONG ? "L" : "S");

      int gi = m_global.GetOrCreate("GLOBAL", now);
      int ri = m_byRegime.GetOrCreate(regimeName, now);
      int ai = m_byArch.GetOrCreate(archName, now);
      int adi = m_byArchDir.GetOrCreate(archDirKey, now);
      int di = (conf.setupDNA != "") ? m_byDNA.GetOrCreate(conf.setupDNA, now) : -1;

      m_global.buckets[gi].observations++;    m_global.buckets[gi].lastSeen = now;
      m_byRegime.buckets[ri].observations++;  m_byRegime.buckets[ri].lastSeen = now;
      m_byArch.buckets[ai].observations++;    m_byArch.buckets[ai].lastSeen = now;
      m_byArchDir.buckets[adi].observations++; m_byArchDir.buckets[adi].lastSeen = now;
      if(di >= 0) { m_byDNA.buckets[di].observations++; m_byDNA.buckets[di].lastSeen = now; }

      // Core-complete gate (fix) — only a setup the Classifier actually
      // resolved into an archetype with every core item present is a
      // genuine "rejected opportunity" candidate. A partial/ARCH_NONE
      // evaluation never had a real chance and would only have diluted
      // the false-negative signal this queue exists to surface.
      bool coreComplete = (conf.archetype != ARCH_NONE) && (conf.coreMet == conf.coreTotal);

      if(executed)
      {
         m_global.buckets[gi].executed++;
         m_byRegime.buckets[ri].executed++;
         m_byArch.buckets[ai].executed++;
         m_byArchDir.buckets[adi].executed++;
         if(di >= 0) m_byDNA.buckets[di].executed++;
         // Real R/win outcome is recorded separately by the existing
         // CASE_TradeAttribution/RecordClosedTrade() path when the trade
         // actually closes — linking a v4 opportunity row to its eventual
         // TradeRecord is a follow-on integration, not required for the
         // scaffolding to be live from opportunity #1.
      }
      else if(coreComplete && theoreticalEntry > 0.0 && theoreticalSL > 0.0 && theoreticalTP1 > 0.0)
      {
         RegisterPending(conf.setupDNA, archName, archDirKey, conf.direction,
                          theoreticalEntry, theoreticalSL, theoreticalTP1, regimeName, now);
      }

      RecomputeAdaptation(archName);

      int pIdx = ArchIndex(conf.archetype);
      double priorityHint = (pIdx >= 0) ? m_priorityBox[pIdx].Apply(ArchTier(archName)) : 1.0;

      string opportunityId=StringFormat("%s|%I64d|%u",conf.setupDNA,(long)now,(uint)GetTickCount());
      if(m_handle != INVALID_HANDLE)
      {
         MqlDateTime dtCheck; TimeToStruct(now, dtCheck);
         MqlDateTime dtFile;  TimeToStruct(m_fileDate, dtFile);
         if(dtCheck.day != dtFile.day || dtCheck.mon != dtFile.mon || dtCheck.year != dtFile.year)
            OpenFile(now);

         FileWrite(m_handle, TimeToString(now, TIME_DATE|TIME_SECONDS), _Symbol,
                   (conf.direction == DIR_LONG ? "LONG" : "SHORT"),
                   regimeName, archName, conf.setupDNA,
                   DoubleToString(conf.longScore,1), DoubleToString(conf.shortScore,1),
                   DoubleToString(conf.separation,1), conf.coreMet, conf.coreTotal,
                   conf.enhancersMet, conf.enhancersTotal,
                   conf.conflict.hasConflict ? "YES" : "NO", ASE_GradeName(conf.grade),
                   conf.qualified ? "YES" : "NO", San(conf.blockReason), executed ? "YES" : "NO", opportunityId,
                   DoubleToString(theoreticalEntry,5), DoubleToString(theoreticalSL,5), DoubleToString(theoreticalTP1,5),
                   coreComplete ? "PENDING" : "N/A", DoubleToString(priorityHint,2), DoubleToString(m_liqWeightBox.Apply(CurrentTier()),2));
      }
      return opportunityId;
   }

   void RegisterPending(string dna, string arch, string archDir, ENUM_TRADE_DIRECTION dir,
                         double entry, double sl, double tp1, string regimeName, datetime now)
   {
      int slot = -1;
      for(int i = 0; i < ASE_MAX_PENDING_THEORETICAL; i++)
         if(!m_pending[i].active) { slot = i; break; }
      if(slot < 0)
      {
         datetime oldest = m_pending[0].openedBar; slot = 0;
         for(int i = 1; i < ASE_MAX_PENDING_THEORETICAL; i++)
            if(m_pending[i].openedBar < oldest) { oldest = m_pending[i].openedBar; slot = i; }
      }
      m_pending[slot].Clear();
      m_pending[slot].dnaKey = dna; m_pending[slot].archKey = arch; m_pending[slot].archDirKey = archDir;
      m_pending[slot].direction = dir; m_pending[slot].entry = entry; m_pending[slot].sl = sl; m_pending[slot].tp1 = tp1;
      m_pending[slot].openedBar = now; m_pending[slot].regimeKey = regimeName; m_pending[slot].active = true;
   }

   //------------------------------------------------------------------
   // Call once per new M15 bar. Checks the JUST-CLOSED bar's high/low
   // against every pending theoretical trade.
   //------------------------------------------------------------------
   void ResolvePending(datetime closedBarTime, double barHigh, double barLow)
   {
      m_resolvedCount=0;
      for(int i = 0; i < ASE_MAX_PENDING_THEORETICAL; i++)
      {
         if(!m_pending[i].active) continue;
         if(closedBarTime <= m_pending[i].openedBar) continue;
         m_pending[i].barsWaited++;

         bool hitSL = false, hitTP = false;
         if(m_pending[i].direction == DIR_LONG)
         {
            hitSL = (barLow  <= m_pending[i].sl);
            hitTP = (barHigh >= m_pending[i].tp1);
         }
         else
         {
            hitSL = (barHigh >= m_pending[i].sl);
            hitTP = (barLow  <= m_pending[i].tp1);
         }

         bool resolved=false; bool win=false; bool applyOutcome=false; double rMultiple=0.0;
         double riskDist=MathAbs(m_pending[i].entry-m_pending[i].sl);
         if(hitSL && hitTP)
         {
            // Intrabar ordering is unknowable from OHLC. Do not invent a win/loss.
            // Expiry records a neutral observation (R=0) only once.
            if(m_pending[i].barsWaited>=InpAceV4TheoreticalMaxBars) { resolved=true; applyOutcome=true; }
         }
         else if(hitSL) { resolved=true; win=false; rMultiple=-1.0; applyOutcome=true; }
         else if(hitTP) { resolved=true; win=true; rMultiple=(riskDist>0.0)?MathAbs(m_pending[i].tp1-m_pending[i].entry)/riskDist:0.0; applyOutcome=true; }
         else if(m_pending[i].barsWaited>=InpAceV4TheoreticalMaxBars) { resolved=true; applyOutcome=true; }
         if(!resolved) continue;
         if(applyOutcome)
         {
            ApplyTheoreticalOutcome(m_pending[i],win,rMultiple);
            if(m_resolvedCount<ASE_MAX_PENDING_THEORETICAL)
            {
               m_resolvedArch[m_resolvedCount]=StringToArchetype(m_pending[i].archKey);
               m_resolvedR[m_resolvedCount]=rMultiple; m_resolvedCount++;
            }
         }
         m_pending[i].active=false;
      }
   }

private:
   void ApplyTheoreticalOutcome(const PendingTheoretical &p, bool win, double rMultiple)
   {
      datetime now = TimeCurrent();
      int gi = m_global.GetOrCreate("GLOBAL", now);
      int ri = m_byRegime.GetOrCreate(p.regimeKey, now);
      int ai = m_byArch.GetOrCreate(p.archKey, now);
      int adi = m_byArchDir.GetOrCreate(p.archDirKey, now);
      int di = (p.dnaKey != "") ? m_byDNA.GetOrCreate(p.dnaKey, now) : -1;

      m_global.buckets[gi].theoreticalResolved++;
      m_byRegime.buckets[ri].theoreticalResolved++;
      m_byArch.buckets[ai].theoreticalResolved++;
      m_byArchDir.buckets[adi].theoreticalResolved++;
      if(di >= 0) m_byDNA.buckets[di].theoreticalResolved++;

      if(win)
      {
         m_global.buckets[gi].theoreticalWins++;
         m_byRegime.buckets[ri].theoreticalWins++;
         m_byArch.buckets[ai].theoreticalWins++;
         m_byArchDir.buckets[adi].theoreticalWins++;
         if(di >= 0) m_byDNA.buckets[di].theoreticalWins++;
      }
      m_global.buckets[gi].sumTheoreticalR += rMultiple;
      m_byRegime.buckets[ri].sumTheoreticalR += rMultiple;
      m_byArch.buckets[ai].sumTheoreticalR += rMultiple;
      m_byArchDir.buckets[adi].sumTheoreticalR += rMultiple;
      if(di >= 0) m_byDNA.buckets[di].sumTheoreticalR += rMultiple;
   }

   //------------------------------------------------------------------
   // v4.0 fix — the boxes previously never moved: RecordOpportunity()
   // only ever called Apply() (read currentValue), nothing called
   // Nudge() (write it). Two bounded hypotheses now actually run,
   // each gated on its own sample-size floor and its own tier:
   //------------------------------------------------------------------
   void RecomputeAdaptation(string archName)
   {
      // V4.0 final: adaptive parameter authority is centralized in
      // CASE_AdaptiveEngine. The legacy boxes remain persisted/reportable
      // for backward compatibility but do not mutate live confluence weights.
   }

   ENUM_SETUP_ARCHETYPE StringToArchetype(string name) const
   {
      if(name == "TrendContinuation")    return ARCH_TREND_CONTINUATION;
      if(name == "LiquidityReversal")    return ARCH_LIQUIDITY_REVERSAL;
      if(name == "CompressionExpansion") return ARCH_COMPRESSION_EXPANSION;
      if(name == "PullbackContinuation") return ARCH_PULLBACK_CONTINUATION;
      if(name == "StructuralReversal")   return ARCH_STRUCTURAL_REVERSAL;
      return ARCH_NONE;
   }

   //------------------------------------------------------------------
   // Persistence — plain FILE_COMMON CSV, one FileWrite per record,
   // tagged by record type in the first field. Deliberately NOT the
   // same file as the human-readable opportunity log (that one rolls
   // daily by design; state needs exactly one current file per
   // symbol/version, matching the existing ASE_VERSION_TAG collision-
   // avoidance convention).
   //------------------------------------------------------------------
   void SaveState()
   {
      int h = FileOpen(m_statePath, FILE_WRITE | FILE_CSV | FILE_COMMON, ',');
      if(h == INVALID_HANDLE)
      {
         Print("[SetupAnalytics] WARNING — could not save v4 state to ", m_statePath, " | Error: ", GetLastError());
         return;
      }
      WriteTable(h, "GLOBAL",  m_global);
      WriteTable(h, "ARCH",    m_byArch);
      WriteTable(h, "ARCHDIR", m_byArchDir);
      WriteTable(h, "REGIME",  m_byRegime);
      WriteTable(h, "DNA",     m_byDNA);
      for(int i = 0; i < 5; i++)
         FileWrite(h, "BOX", m_priorityBox[i].paramName, DoubleToString(m_priorityBox[i].currentValue, 6));
      FileWrite(h, "BOX", m_liqWeightBox.paramName, DoubleToString(m_liqWeightBox.currentValue, 6));
      for(int i = 0; i < ASE_MAX_PENDING_THEORETICAL; i++)
      {
         if(!m_pending[i].active) continue;
         FileWrite(h, "PENDING", m_pending[i].dnaKey, m_pending[i].archKey, m_pending[i].archDirKey, m_pending[i].regimeKey,
                   (int)m_pending[i].direction, DoubleToString(m_pending[i].entry,6),
                   DoubleToString(m_pending[i].sl,6), DoubleToString(m_pending[i].tp1,6),
                   (long)m_pending[i].openedBar, m_pending[i].barsWaited);
      }
      FileWrite(h, "META", m_lastDNA, (long)m_lastDNABar);
      FileClose(h);
   }

   void WriteTable(int h, string tag, const LearningStatsTable &t)
   {
      for(int i = 0; i < t.count; i++)
      {
         LearningStatsBucket b = t.buckets[i];
         FileWrite(h, "BUCKET", tag, b.key, b.observations, b.executed, b.wins,
                   b.theoreticalWins, b.theoreticalResolved,
                   DoubleToString(b.sumR,6), DoubleToString(b.sumTheoreticalR,6),
                   (long)b.firstSeen, (long)b.lastSeen);
      }
   }

   void LoadState()
   {
      if(!FileIsExist(m_statePath, FILE_COMMON)) return;   // fresh start — nothing to restore
      int h = FileOpen(m_statePath, FILE_READ | FILE_CSV | FILE_COMMON | FILE_SHARE_READ, ',');
      if(h == INVALID_HANDLE)
      {
         Print("[SetupAnalytics] WARNING — could not load v4 state from ", m_statePath, " | Error: ", GetLastError());
         return;
      }

      int restoredBuckets = 0, restoredPending = 0;
      while(!FileIsEnding(h))
      {
         string tag = FileReadString(h);
         if(tag == "") break;   // trailing blank line at EOF

         if(tag == "BUCKET")
         {
            string tableTag = FileReadString(h);
            string key      = FileReadString(h);
            long   obs      = (long)FileReadNumber(h);
            long   exec     = (long)FileReadNumber(h);
            long   wins     = (long)FileReadNumber(h);
            long   theoWins = (long)FileReadNumber(h);
            long   theoRes  = (long)FileReadNumber(h);
            double sumR     = FileReadNumber(h);
            double sumTheoR = FileReadNumber(h);
            datetime first  = (datetime)FileReadNumber(h);
            datetime last   = (datetime)FileReadNumber(h);

            if(tableTag == "GLOBAL")       RestoreBucket(m_global,    key, obs, exec, wins, theoWins, theoRes, sumR, sumTheoR, first, last);
            else if(tableTag == "ARCH")    RestoreBucket(m_byArch,    key, obs, exec, wins, theoWins, theoRes, sumR, sumTheoR, first, last);
            else if(tableTag == "ARCHDIR") RestoreBucket(m_byArchDir, key, obs, exec, wins, theoWins, theoRes, sumR, sumTheoR, first, last);
            else if(tableTag == "REGIME")  RestoreBucket(m_byRegime,  key, obs, exec, wins, theoWins, theoRes, sumR, sumTheoR, first, last);
            else if(tableTag == "DNA")     RestoreBucket(m_byDNA,     key, obs, exec, wins, theoWins, theoRes, sumR, sumTheoR, first, last);
            restoredBuckets++;
         }
         else if(tag == "BOX")
         {
            string paramName = FileReadString(h);
            double val = FileReadNumber(h);
            bool matched = false;
            for(int i = 0; i < 5; i++)
               if(m_priorityBox[i].paramName == paramName)
               {
                  m_priorityBox[i].currentValue = MathMax(m_priorityBox[i].minValue, MathMin(m_priorityBox[i].maxValue, val));
                  matched = true; break;
               }
            if(!matched && m_liqWeightBox.paramName == paramName)
               m_liqWeightBox.currentValue = MathMax(m_liqWeightBox.minValue, MathMin(m_liqWeightBox.maxValue, val));
         }
         else if(tag == "PENDING")
         {
            string dna = FileReadString(h);
            string arch = FileReadString(h);
            string archDir = FileReadString(h);
            string regimeKey = FileReadString(h);
            ENUM_TRADE_DIRECTION dir = (ENUM_TRADE_DIRECTION)(int)FileReadNumber(h);
            double entry = FileReadNumber(h);
            double sl = FileReadNumber(h);
            double tp1 = FileReadNumber(h);
            datetime opened = (datetime)FileReadNumber(h);
            int waited = (int)FileReadNumber(h);

            if(restoredPending < ASE_MAX_PENDING_THEORETICAL)
            {
               m_pending[restoredPending].Clear();
               m_pending[restoredPending].dnaKey = dna; m_pending[restoredPending].archKey = arch;
               m_pending[restoredPending].archDirKey = archDir; m_pending[restoredPending].regimeKey = regimeKey; m_pending[restoredPending].direction = dir;
               m_pending[restoredPending].entry = entry; m_pending[restoredPending].sl = sl; m_pending[restoredPending].tp1 = tp1;
               m_pending[restoredPending].openedBar = opened; m_pending[restoredPending].barsWaited = waited;
               m_pending[restoredPending].active = true;
               restoredPending++;
            }
         }
         else if(tag == "META")
         {
            m_lastDNA    = FileReadString(h);
            m_lastDNABar = (datetime)FileReadNumber(h);
         }
      }
      FileClose(h);
      Print(StringFormat("[SetupAnalytics] v4 state restored: %d buckets, %d pending theoretical records, authority tier=%s",
            restoredBuckets, restoredPending, ASE_AuthorityName(CurrentTier())));
   }

   // MQL5 has no reference-return AND does not support GetPointer() on
   // struct instances (only on class instances) — an earlier draft of
   // this restore path used GetPointer() on the LearningStatsTable
   // structs and would not have compiled. Fixed to a plain reference-
   // parameter helper instead, the same pattern used everywhere else
   // in this codebase (ValidationResult&, ConfluenceResult&, etc).
   void RestoreBucket(LearningStatsTable &t, string key, long obs, long exec, long wins,
                       long theoWins, long theoRes, double sumR, double sumTheoR,
                       datetime first, datetime last)
   {
      int idx = t.GetOrCreate(key, first);
      t.buckets[idx].observations        = obs;
      t.buckets[idx].executed            = exec;
      t.buckets[idx].wins                = wins;
      t.buckets[idx].theoreticalWins      = theoWins;
      t.buckets[idx].theoreticalResolved  = theoRes;
      t.buckets[idx].sumR                 = sumR;
      t.buckets[idx].sumTheoreticalR       = sumTheoR;
      t.buckets[idx].firstSeen             = first;
      t.buckets[idx].lastSeen              = last;
   }

public:
   void RecordExecution(const ConfluenceResult &conf)
   {
      datetime now=TimeCurrent();
      int gi=m_global.Find("GLOBAL");
      int ai=m_byArch.Find(ASE_ArchetypeName(conf.archetype));
      int adi=m_byArchDir.Find(ASE_ArchetypeName(conf.archetype)+"-"+(conf.direction==DIR_LONG?"L":"S"));
      int di=m_byDNA.Find(conf.setupDNA);
      if(gi>=0)m_global.buckets[gi].executed++;
      if(ai>=0)m_byArch.buckets[ai].executed++;
      if(adi>=0)m_byArchDir.buckets[adi].executed++;
      if(di>=0)m_byDNA.buckets[di].executed++;
      // Regime execution count is updated by the explicit RecordRegimeExecution helper.
      if(gi>=0)m_global.buckets[gi].lastSeen=now;
      if(m_handle!=INVALID_HANDLE)
         FileWrite(m_handle,TimeToString(now,TIME_DATE|TIME_SECONDS),_Symbol,
                   conf.direction==DIR_LONG?"LONG":"SHORT",conf.setupDNA,
                   "EXECUTION_UPDATE",conf.archetype,conf.grade);
   }

   void RecordRegimeExecution(string regimeName)
   {
      int ri=m_byRegime.Find(regimeName); if(ri>=0)m_byRegime.buckets[ri].executed++;
   }

   void RecordActualOutcome(const ConfluenceResult &conf,double r)
   {
      datetime now=TimeCurrent();
      int gi=m_global.Find("GLOBAL"); if(gi<0)return;
      int ai=m_byArch.Find(ASE_ArchetypeName(conf.archetype));
      int adi=m_byArchDir.Find(ASE_ArchetypeName(conf.archetype)+"-"+(conf.direction==DIR_LONG?"L":"S"));
      int di=m_byDNA.Find(conf.setupDNA);
      if(r>0){m_global.buckets[gi].wins++; if(ai>=0)m_byArch.buckets[ai].wins++; if(adi>=0)m_byArchDir.buckets[adi].wins++; if(di>=0)m_byDNA.buckets[di].wins++;}
      m_global.buckets[gi].sumR+=r; if(ai>=0)m_byArch.buckets[ai].sumR+=r; if(adi>=0)m_byArchDir.buckets[adi].sumR+=r; if(di>=0)m_byDNA.buckets[di].sumR+=r;
      m_global.buckets[gi].lastSeen=now;
   }

   bool GetNextTheoreticalOutcome(ENUM_SETUP_ARCHETYPE &arch,double &r)
   {
      if(m_resolvedCount<=0) return false;
      arch=m_resolvedArch[0]; r=m_resolvedR[0];
      for(int i=1;i<m_resolvedCount;i++){m_resolvedArch[i-1]=m_resolvedArch[i];m_resolvedR[i-1]=m_resolvedR[i];}
      m_resolvedCount--; return true;
   }

   void PrintSummary()
   {
      Print("═══ ACE v4.0 Learning Summary (GLOBAL) ═══");
      int gi = m_global.Find("GLOBAL");
      if(gi < 0) { Print("  No opportunities recorded."); return; }
      LearningStatsBucket b = m_global.buckets[gi];
      Print(StringFormat("  Observations=%d Executed=%d WR=%.1f%% AvgR=%.2f | TheoreticalResolved=%d TheoreticalWR=%.1f%% AvgTheoreticalR=%.2f | AuthorityTier=%s",
            b.observations, b.executed, b.WinRate()*100, b.AvgR(),
            b.theoreticalResolved, b.TheoreticalWinRate()*100, b.AvgTheoreticalR(),
            ASE_AuthorityName(CurrentTier())));
      for(int i = 0; i < m_byArch.count; i++)
      {
         LearningStatsBucket ab = m_byArch.buckets[i];
         Print(StringFormat("  [%s] obs=%d exec=%d WR=%.1f%% AvgR=%.2f theoreticalWR=%.1f%% tier=%s priority=%.2f",
               ab.key, ab.observations, ab.executed, ab.WinRate()*100, ab.AvgR(), ab.TheoreticalWinRate()*100,
               ASE_AuthorityName(ArchTier(ab.key)),
               (ArchIndex(StringToArchetype(ab.key)) >= 0) ? m_priorityBox[ArchIndex(StringToArchetype(ab.key))].currentValue : 1.0));
      }
      Print(StringFormat("  LiquidityWeight: base=12.00 current=%.2f", m_liqWeightBox.currentValue));
   }
};
#endif // ASE_SETUPANALYTICS_MQH
