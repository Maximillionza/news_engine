#ifndef ASE_ADAPTIVETYPES_MQH
#define ASE_ADAPTIVETYPES_MQH
#include "ASE_Enums.mqh"
#include "ASE_ConfluenceTypes.mqh"
//+------------------------------------------------------------------+
//| ACE v4.0 — Adaptive Learning scaffolding                         |
//|                                                                  |
//| Design basis: learning starts at opportunity #1 for every setup   |
//| class (Learning Clock). Adaptation authority is graduated and     |
//| PER SETUP CLASS, not a single global switch (Adaptation Clock +   |
//| Authority Clock). Four tiers:                                    |
//|                                                                  |
//|   AUTH_OBSERVE    1-20  obs  — stats only, zero behavioural effect|
//|   AUTH_CAUTIOUS   20-50 obs  — Level 1: priority/preference only  |
//|                                 (changes internal v4 ranking,     |
//|                                  never touches an order)          |
//|   AUTH_CONTROLLED 50-100 obs — Level 2: bounded threshold nudges  |
//|                                 WITHIN the v4 Confluence Engine's  |
//|                                 own internal evidence weighting —  |
//|                                 never writes to the legacy v3     |
//|                                 engines' Inp* parameters           |
//|   AUTH_VALIDATED  100+ obs   — ELIGIBLE for Level 3/4, but Level  |
//|                                 3 (setup activation) and Level 4   |
//|                                 (model promotion) additionally     |
//|                                 require the shadow-model           |
//|                                 validation this delivery declares  |
//|                                 the interface for but cannot       |
//|                                 itself satisfy (no accumulated     |
//|                                 history exists yet) — see          |
//|                                 ShadowModelState.eligibleForPromotion|
//|                                                                  |
//| At NO tier does anything in this file touch OrderSend, the       |
//| legacy engines' Inp* inputs, or ACE_V4_MODE's execution gate.     |
//| That boundary is enforced by construction: AdaptationBox only     |
//| ever mutates .currentValue, which is read by the v4 Confluence    |
//| Engine's OWN internal scoring — never passed to m_setup/m_score.  |
//|                                                                  |
//| v4.0 — new file. Nothing here is read by any v3 execution path.   |
//+------------------------------------------------------------------+

enum ENUM_ADAPT_AUTHORITY
{
   AUTH_OBSERVE    = 0,
   AUTH_CAUTIOUS   = 1,
   AUTH_CONTROLLED = 2,
   AUTH_VALIDATED  = 3
};

// v4.0.2 Phase 2 item 2 -- one cell of the general per-(archetype x
// regime x evidence-type) enhancer effectiveness table. Fed ONLY from
// in-sample (oos==false) outcomes -- see CASE_AdaptiveEngine::
// RecordEnhancerEffectiveness(). "with" = the evidence type was ACTIVE
// in the winning direction when the setup resolved; "without" = the
// type was EVALUATED for this archetype/regime (i.e. not a core item)
// but was NOT active. Replaces the old global liquidity-only
// m_liqWithN/m_liqWithoutN/m_liqWithR/m_liqWithoutR mechanism, of which
// EVID_LIQUIDITY_SWEEP is now just one bit among twenty.
struct EnhancerEffCell
{
   long   withCount;
   double withSumR;
   long   withoutCount;
   double withoutSumR;
   void Clear(){withCount=0;withSumR=0.0;withoutCount=0;withoutSumR=0.0;}
   double WithAvgR()    const { return withCount>0    ? withSumR/(double)withCount       : 0.0; }
   double WithoutAvgR() const { return withoutCount>0 ? withoutSumR/(double)withoutCount  : 0.0; }
   double Edge()        const { return WithAvgR()-WithoutAvgR(); }
};

string ASE_AuthorityName(ENUM_ADAPT_AUTHORITY a)
{
   switch(a)
   {
      case AUTH_CAUTIOUS:   return "CAUTIOUS(L1-priority)";
      case AUTH_CONTROLLED: return "CONTROLLED(L2-bounded-threshold)";
      case AUTH_VALIDATED:  return "VALIDATED(L3/4-eligible, pending shadow validation)";
      default:              return "OBSERVE";
   }
}

//+------------------------------------------------------------------+
//| Per-setup-class learning bucket. One instance keyed by setup DNA  |
//| (exact evidence combination) plus roll-up instances keyed by      |
//| archetype and by archetype+direction, per plan §82.4's hierarchy: |
//| Global -> Regime -> Setup Class -> Direction -> DNA.               |
//| This struct is the leaf shape used at every level; which level a  |
//| given bucket represents is determined by its map key, not by a    |
//| field here (keeps one struct instead of four near-duplicates).    |
//+------------------------------------------------------------------+
struct LearningStatsBucket
{
   string   key;                // e.g. "TRND-L-HBOS-FVG-DISP-MBOS" or "TRND-L" or "TRND" or "GLOBAL"
   long     observations;       // every opportunity seen, executed or not (Learning Clock ticks)
   long     executed;
   long     wins;                // executed AND profit > 0
   long     theoreticalWins;     // blocked, but forward-resolver marked it a theoretical win
   long     theoreticalResolved; // blocked opportunities whose forward-resolver has completed
   double   sumR;                 // realised R, executed trades only
   double   sumTheoreticalR;      // theoretical R, blocked-and-resolved opportunities only
   datetime firstSeen;
   datetime lastSeen;

   void Clear()
   {
      key = ""; observations = 0; executed = 0; wins = 0;
      theoreticalWins = 0; theoreticalResolved = 0;
      sumR = 0.0; sumTheoreticalR = 0.0;
      firstSeen = 0; lastSeen = 0;
   }

   double WinRate()            const { return executed > 0 ? (double)wins / executed : 0.0; }
   double AvgR()                const { return executed > 0 ? sumR / executed : 0.0; }
   double TheoreticalWinRate() const { return theoreticalResolved > 0 ? (double)theoreticalWins / theoreticalResolved : 0.0; }
   double AvgTheoreticalR()     const { return theoreticalResolved > 0 ? sumTheoreticalR / theoreticalResolved : 0.0; }

   // Authority tier is a pure function of observation count — no
   // separate "confidence" field to drift out of sync with it.
   ENUM_ADAPT_AUTHORITY Tier(int cautiousMin, int controlledMin, int validatedMin) const
   {
      if(observations >= validatedMin)  return AUTH_VALIDATED;
      if(observations >= controlledMin) return AUTH_CONTROLLED;
      if(observations >= cautiousMin)   return AUTH_CAUTIOUS;
      return AUTH_OBSERVE;
   }
};

#define ASE_MAX_LEARNING_BUCKETS 64

// Fixed-capacity table of learning buckets, linear-scanned by key.
// 64 is deliberately generous — 5 archetypes x 2 directions x global
// x regime roll-ups leaves ~40 slots free for distinct DNA strings
// before the oldest-inactive eviction below is ever exercised.
struct LearningStatsTable
{
   LearningStatsBucket buckets[ASE_MAX_LEARNING_BUCKETS];
   int                 count;

   void Reset() { count = 0; for(int i = 0; i < ASE_MAX_LEARNING_BUCKETS; i++) buckets[i].Clear(); }

   int Find(const string key) const
   {
      for(int i = 0; i < count; i++) if(buckets[i].key == key) return i;
      return -1;
   }

   // Returns the index of the bucket for `key`, creating it if absent.
   // If the table is full, evicts the least-recently-seen bucket —
   // acceptable for a first cut; a full 64-bucket table with active
   // eviction pressure is itself a signal the DNA space needs
   // consolidating, which is a data question, not a code one.
   int GetOrCreate(const string key, datetime now)
   {
      int idx = Find(key);
      if(idx >= 0) return idx;

      if(count < ASE_MAX_LEARNING_BUCKETS)
      {
         buckets[count].Clear();
         buckets[count].key       = key;
         buckets[count].firstSeen = now;
         idx = count;
         count++;
         return idx;
      }

      int oldest = 0;
      for(int i = 1; i < ASE_MAX_LEARNING_BUCKETS; i++)
         if(buckets[i].lastSeen < buckets[oldest].lastSeen) oldest = i;
      buckets[oldest].Clear();
      buckets[oldest].key       = key;
      buckets[oldest].firstSeen = now;
      return oldest;
   }
};

//+------------------------------------------------------------------+
//| One bounded, self-describing adaptive parameter (plan §82.6).     |
//| minAuthorityTier gates whether .currentValue is allowed to move   |
//| away from .baseValue at all — below that tier the box is a no-op  |
//| by construction (Apply() below returns baseValue unconditionally).|
//+------------------------------------------------------------------+
struct AdaptationBox
{
   string                paramName;
   ENUM_ADAPT_AUTHORITY   minAuthorityTier;   // AUTH_CAUTIOUS for Level 1, AUTH_CONTROLLED for Level 2
   double                 baseValue;
   double                 minValue;
   double                 maxValue;
   double                 stepSize;
   double                 currentValue;
   bool                   locked;             // true = hard override, ignores tier entirely (kill switch)

   void Init(string name, ENUM_ADAPT_AUTHORITY tier, double base, double lo, double hi, double step)
   {
      paramName        = name;
      minAuthorityTier = tier;
      baseValue        = base;
      minValue         = lo;
      maxValue         = hi;
      stepSize         = step;
      currentValue     = base;
      locked           = false;
   }

   // The single choke point every consumer of this box must go
   // through. Below the box's authority tier, or while locked,
   // Apply() ignores whatever currentValue holds and returns base —
   // so a bug that mutates currentValue early cannot leak into
   // behaviour before its tier is reached.
   double Apply(ENUM_ADAPT_AUTHORITY liveTier) const
   {
      if(locked) return baseValue;
      if((int)liveTier < (int)minAuthorityTier) return baseValue;
      double v = currentValue;
      if(v < minValue) v = minValue;
      if(v > maxValue) v = maxValue;
      return v;
   }

   bool Nudge(double delta)
   {
      double proposed = currentValue + delta;
      if(proposed < minValue || proposed > maxValue) return false;
      currentValue = proposed;
      return true;
   }
};

//+------------------------------------------------------------------+
//| Shadow model validation state                                    |
//+------------------------------------------------------------------+
struct ShadowModelState
{
   string modelName;
   long sampleCount;
   double liveNetR;
   double shadowNetR;
   bool recentPerformanceChecked;
   bool longTermPerformanceChecked;
   bool oosPerformanceChecked;
   bool regimeCoverageChecked;
   bool drawdownImpactChecked;
   bool stabilityChecked;
   double recentAvgR;
   double longTermAvgR;
   double oosRetention;

   void Clear()
   {
      modelName="";sampleCount=0;liveNetR=0.0;shadowNetR=0.0;
      recentPerformanceChecked=false;longTermPerformanceChecked=false;
      oosPerformanceChecked=false;regimeCoverageChecked=false;
      drawdownImpactChecked=false;stabilityChecked=false;
      recentAvgR=0.0;longTermAvgR=0.0;oosRetention=0.0;
   }

   bool eligibleForPromotion() const
   {
      return sampleCount>=100 && recentPerformanceChecked && longTermPerformanceChecked &&
             oosPerformanceChecked && regimeCoverageChecked && drawdownImpactChecked && stabilityChecked;
   }

   void SetValidation(bool recent,bool longTerm,bool oos,bool regime,bool dd,bool stability)
   {
      recentPerformanceChecked=recent;longTermPerformanceChecked=longTerm;
      oosPerformanceChecked=oos;regimeCoverageChecked=regime;
      drawdownImpactChecked=dd;stabilityChecked=stability;
   }
};

//+------------------------------------------------------------------+
//| ACE v4.0.2 Phase 1 -- same-setup comparison vs legacy.            |
//|                                                                  |
//| V4's own learning stats (LearningStatsTable above) and legacy's   |
//| trade stats have never been linked: two piles of numbers with no  |
//| shared key, so "is V4 better than legacy" could never be answered |
//| with paired data on the SAME setup. This ledger fixes that.       |
//|                                                                  |
//| One row per (archetype, regime) pair, plus one extra "NoClass"    |
//| row for legacy trades V4 classified ARCH_NONE (today those are    |
//| silently dropped from all V4 learning). Keyed by a plain string   |
//| ("<archetype>|<regime>" or "NoClass") and linear-scanned, the same|
//| pattern as LearningStatsTable above -- this deliberately avoids   |
//| indexing by ENUM_MARKET_REGIME ordinal (that enum has 7 members,  |
//| not 5, including REGIME_UNKNOWN/REGIME_DEAD) so the row set can't |
//| silently miss a regime the enum grows later.                      |
//|                                                                  |
//| Per row, four cells based on what actually happened to that ONE   |
//| setup occurrence:                                                  |
//|   both       - V4 would-qualify AND legacy traded it (the only     |
//|                cell with a true apples-to-apples R pair)           |
//|   v4Only     - V4 would-qualify, legacy did NOT trade it           |
//|                (theoretical R only)                                |
//|   legacyOnly - V4 did NOT qualify (or NoClass), legacy traded it   |
//|                (realised R only)                                   |
//|   neither    - neither side acted; count only, nothing to sum      |
//+------------------------------------------------------------------+
struct ComparisonCell
{
   long   count;
   double sumV4R;
   double sumLegacyR;
   void Clear() { count = 0; sumV4R = 0.0; sumLegacyR = 0.0; }
};

struct ComparisonRow
{
   string        key;   // "<archetypeName>|<regimeName>", or "NoClass"
   ComparisonCell both;
   ComparisonCell v4Only;
   ComparisonCell legacyOnly;
   long           neitherCount;
   datetime       firstSeen;
   datetime       lastSeen;

   void Clear()
   {
      key = ""; both.Clear(); v4Only.Clear(); legacyOnly.Clear();
      neitherCount = 0; firstSeen = 0; lastSeen = 0;
   }
};

// 5 archetypes x 7 regime values + 1 NoClass row = 36 possible keys at
// most; 48 leaves headroom without needing eviction pressure in practice.
#define ASE_MAX_COMPARE_ROWS 48

struct ComparisonLedger
{
   ComparisonRow rows[ASE_MAX_COMPARE_ROWS];
   int           count;

   void Reset() { count = 0; for(int i = 0; i < ASE_MAX_COMPARE_ROWS; i++) rows[i].Clear(); }

   int Find(const string key) const
   {
      for(int i = 0; i < count; i++) if(rows[i].key == key) return i;
      return -1;
   }

   int GetOrCreate(const string key, datetime now)
   {
      int idx = Find(key);
      if(idx >= 0) return idx;
      if(count < ASE_MAX_COMPARE_ROWS)
      {
         rows[count].Clear(); rows[count].key = key; rows[count].firstSeen = now;
         idx = count; count++; return idx;
      }
      int oldest = 0;
      for(int i = 1; i < ASE_MAX_COMPARE_ROWS; i++)
         if(rows[i].lastSeen < rows[oldest].lastSeen) oldest = i;
      rows[oldest].Clear(); rows[oldest].key = key; rows[oldest].firstSeen = now;
      return oldest;
   }

   string RowKey(const string archName, const string regimeName) const
   {
      return (archName == "NoClass") ? "NoClass" : (archName + "|" + regimeName);
   }

   // One observation into the right cell for the row identified by
   // (archName, regimeName). v4R is only meaningful when wouldQualify is
   // true (both/v4Only); legacyR is only meaningful when legacyTraded is
   // true (both/legacyOnly) -- callers pass 0.0 for the side that didn't
   // happen, which is never read for that cell.
   void Add(const string archName, const string regimeName, bool wouldQualify, bool legacyTraded,
            double v4R, double legacyR, datetime now)
   {
      string key = RowKey(archName, regimeName);
      int idx = GetOrCreate(key, now);
      rows[idx].lastSeen = now;
      if(wouldQualify && legacyTraded)
      {
         rows[idx].both.count++; rows[idx].both.sumV4R += v4R; rows[idx].both.sumLegacyR += legacyR;
      }
      else if(wouldQualify && !legacyTraded)
      {
         rows[idx].v4Only.count++; rows[idx].v4Only.sumV4R += v4R;
      }
      else if(!wouldQualify && legacyTraded)
      {
         rows[idx].legacyOnly.count++; rows[idx].legacyOnly.sumLegacyR += legacyR;
      }
      else
      {
         rows[idx].neitherCount++;
      }
   }

   // Average(v4R - legacyR) over the "both" cell only -- the only cell
   // with a genuine paired sample. 0.0 (with PairedCount()==0) when there
   // is no paired data yet; callers must check PairedCount(), not just
   // treat 0.0 as "no edge".
   double EdgeVsLegacy(const string archName, const string regimeName) const
   {
      int idx = Find(RowKey(archName, regimeName));
      if(idx < 0 || rows[idx].both.count <= 0) return 0.0;
      return (rows[idx].both.sumV4R - rows[idx].both.sumLegacyR) / (double)rows[idx].both.count;
   }

   long PairedCount(const string archName, const string regimeName) const
   {
      int idx = Find(RowKey(archName, regimeName));
      return (idx < 0) ? 0 : rows[idx].both.count;
   }

   // Compact human-readable summary, one line per row with any activity.
   string BuildReport() const
   {
      string s = "=== ACE v4 vs legacy: same-setup comparison ===\n";
      bool any = false;
      for(int i = 0; i < count; i++)
      {
         long totalSeen = rows[i].both.count + rows[i].v4Only.count + rows[i].legacyOnly.count + rows[i].neitherCount;
         if(totalSeen < 1) continue;
         any = true;
         double edge = (rows[i].both.count > 0)
                        ? (rows[i].both.sumV4R - rows[i].both.sumLegacyR) / (double)rows[i].both.count
                        : 0.0;
         s += StringFormat("  [%-28s] paired=%-3d edgeVsLegacy=%+.3fR  v4Only=%-3d legacyOnly=%-3d neither=%-3d\n",
                            rows[i].key, rows[i].both.count, edge,
                            rows[i].v4Only.count, rows[i].legacyOnly.count, rows[i].neitherCount);
      }
      if(!any) s += "  (no comparison data yet)\n";
      return s;
   }
};
#endif // ASE_ADAPTIVETYPES_MQH
