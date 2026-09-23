#ifndef ASE_EVIDENCETYPES_MQH
#define ASE_EVIDENCETYPES_MQH
#include "ASE_Enums.mqh"
//+------------------------------------------------------------------+
//| ACE v4.0 — Evidence Architecture (Plan §5, §7)                   |
//|                                                                  |
//| Purpose: give every piece of market evidence a place to live     |
//| independently, instead of the first-match-wins pattern in the    |
//| legacy M15 Setup Engine and M1 Trigger Engine (both confirmed —  |
//| see ASE_SetupEngine::EvaluateAllEvidence() and                   |
//| ASE_TriggerEngine::EvaluateAllEvidence() for the additive wraps  |
//| that populate these).                                            |
//|                                                                  |
//| v4.0 — new file. Nothing here is read by any v3 execution path.  |
//+------------------------------------------------------------------+

// Evidence family — plan §5. Used to prevent redundant confluence
// (e.g. EMA21 slope + EMA21 distance are the same family, not two
// independent confirmations).
enum ENUM_EVIDENCE_FAMILY
{
   FAM_NONE         = 0,
   FAM_STRUCTURE    = 1,   // H1 BOS/CHoCH, H4 alignment
   FAM_LOCATION     = 2,   // M15 FVG, EMA pullback, structural zone
   FAM_LIQUIDITY    = 3,   // sweeps, HTF pools, unmitigated swings
   FAM_MOMENTUM     = 4,   // M15/M1 displacement, M1 micro BOS
   FAM_ENVIRONMENT  = 5,   // regime, ATR state, session
   FAM_EXECUTION    = 6    // spread, drift, broker conditions
};

// Evidence type — plan §7. One entry per detector already in the
// codebase; nothing here invents a new detection method, it only
// gives an existing check a stable identity.
enum ENUM_EVIDENCE_TYPE
{
   EVID_NONE               = 0,
   EVID_H1_BOS              = 1,
   EVID_H1_CHOCH            = 2,   // reserved — CHoCH unimplemented in v3 (ASE_StructureEngine)
   EVID_H4_ALIGNMENT        = 3,
   EVID_M15_FVG             = 4,
   EVID_M15_DISPLACEMENT    = 5,
   EVID_M15_COMPRESSION     = 6,
   EVID_M15_EMA_PULLBACK    = 7,
   EVID_LIQUIDITY_SWEEP     = 8,   // ASE_LiquidityEngine::DetectSweep() composite result
   EVID_M1_DISPLACEMENT     = 9,
   EVID_M1_MICRO_BOS        = 10,
   EVID_M1_REJECTION        = 11,
   EVID_M1_EMA_ALIGN        = 12,
   EVID_VOLATILITY_STATE    = 13,  // regime/ATR state
   EVID_SESSION_QUALITY     = 14,
   EVID_SPREAD_QUALITY      = 15,
   EVID_ORDER_BLOCK         = 16,  // v4.0.1 — CASE_SetupEngine::CheckOrderBlock(); new detector, not a re-identified existing check (see file header of CheckOrderBlock)
   EVID_KILL_ZONE           = 17,  // v4.0.1 — surfaces the existing CASE_Time::IsKillZone() (v3.7.0) as discrete evidence; not a new detector
   EVID_AMD_PHASE           = 18,  // v4.0.1 — CASE_SetupEngine::CheckAMDPhase(); new detector (Accumulation/Manipulation/Distribution)
   EVID_MACRO_CORRELATION   = 19,  // v4.0.1 — CASE_SetupEngine::CheckMacroCorrelation(); new detector, first cross-symbol (non-_Symbol) read anywhere in this codebase
   EVID_LIQUIDITY_POOL      = 20   // v4.0.1 — CASE_SetupEngine::CheckLiquidityPool(); new detector (PDH/PDL + equal highs/lows), distinct from EVID_LIQUIDITY_SWEEP's swing-pivot logic
};

// One piece of evidence. Deliberately flat/POD so it can sit in a
// fixed-size array with no dynamic allocation (MQL5-safe, matches
// existing project convention — see ValidationResult, ScoreCard).
struct SetupEvidence
{
   ENUM_EVIDENCE_TYPE    evidType;
   ENUM_EVIDENCE_FAMILY  family;
   ENUM_TRADE_DIRECTION  direction;
   double                strength;    // raw score contribution the source check assigned (0 if none)
   bool                  active;      // true = detected/passed this evaluation
   int                   freshnessBars; // bars since this evidence was last (re)detected — 0 = this bar
   datetime              timestamp;
   ENUM_TIMEFRAMES       sourceTF;
   double                priceRef;    // level/price the evidence refers to (0 if not applicable)
   string                reason;      // human-readable detail from the source check

   void Clear()
   {
      evidType      = EVID_NONE;
      family        = FAM_NONE;
      direction     = DIR_NONE;
      strength      = 0.0;
      active        = false;
      freshnessBars = 0;
      timestamp     = 0;
      sourceTF      = PERIOD_CURRENT;
      priceRef      = 0.0;
      reason        = "";
   }
};

#define ASE_MAX_EVIDENCE 24

// Fixed-capacity container for one evaluation pass. Replaces the
// legacy pattern of "first setup class that passes wins" — every
// detector's result is preserved here regardless of whether it
// passed, so the Confluence Engine can see the whole picture.
struct SetupEvidenceSet
{
   SetupEvidence items[ASE_MAX_EVIDENCE];
   int           count;
   datetime      evalTime;

   void Reset()
   {
      count = 0;
      evalTime = 0;
      for(int i = 0; i < ASE_MAX_EVIDENCE; i++) items[i].Clear();
   }

   bool Add(const SetupEvidence &e)
   {
      if(count >= ASE_MAX_EVIDENCE) return false;   // fail-safe: never overrun
      items[count] = e;
      count++;
      return true;
   }

   // v4.0 fix — without this, a caller that re-collects the SAME
   // evidence family every tick (M1/liquidity, now unthrottled per
   // tick for same-tick responsiveness) appends a fresh copy on top of
   // the previous tick's instead of replacing it. Two consequences,
   // both real: (1) ConfluenceEngine::Evaluate() sums weight per
   // MATCHING ACTIVE ITEM, so a duplicated active type gets double-
   // counted in the score every tick it survives — not a display
   // artefact, an actual score inflation; (2) with ASE_MAX_EVIDENCE=24
   // and ~12 M1-scoped items added per tick, the buffer fills after
   // ~2 ticks, after which Add() silently starts returning false and
   // the M1 evidence effectively freezes for the rest of the M15 bar —
   // the opposite of the same-tick responsiveness this was for. Call
   // this to clear a call's own evidence types before re-adding them,
   // leaving evidence added by OTHER callers (e.g. the once-per-bar
   // M15/H1/H4 collection) untouched.
   void RemoveTypes(const ENUM_EVIDENCE_TYPE &types[])
   {
      SetupEvidence kept[ASE_MAX_EVIDENCE];
      int keptCount = 0;
      for(int i = 0; i < count; i++)
      {
         bool matches = false;
         for(int j = 0; j < ArraySize(types); j++)
            if(items[i].evidType == types[j]) { matches = true; break; }
         if(!matches) kept[keptCount++] = items[i];
      }
      for(int i = 0; i < ASE_MAX_EVIDENCE; i++) items[i].Clear();
      for(int i = 0; i < keptCount; i++) items[i] = kept[i];
      count = keptCount;
   }

   int CountActive(ENUM_EVIDENCE_FAMILY fam = FAM_NONE) const
   {
      int n = 0;
      for(int i = 0; i < count; i++)
      {
         if(!items[i].active) continue;
         if(fam != FAM_NONE && items[i].family != fam) continue;
         n++;
      }
      return n;
   }

   bool HasActive(ENUM_EVIDENCE_TYPE t) const
   {
      for(int i = 0; i < count; i++)
         if(items[i].evidType == t && items[i].active) return true;
      return false;
   }

   // v4.0 fix — direction-aware overload. HasActive(t) alone is
   // currently harmless (every item added in one bar shares the single
   // resolved m_ctx.direction, so there is never a mixed-direction set
   // to conflate) but was a latent trap: SetupEvidence.direction exists
   // specifically because evidence collection was expected to
   // eventually score both directions in one pass, and every archetype
   // core check in ASE_SetupClassifier.mqh was silently relying on the
   // single-direction invariant instead of checking it. Fixed now,
   // before it became a chase later.
   bool HasActive(ENUM_EVIDENCE_TYPE t, ENUM_TRADE_DIRECTION dir) const
   {
      for(int i = 0; i < count; i++)
         if(items[i].evidType == t && items[i].active && items[i].direction == dir) return true;
      return false;
   }

   double StrengthOf(ENUM_EVIDENCE_TYPE t) const
   {
      for(int i = 0; i < count; i++)
         if(items[i].evidType == t && items[i].active) return items[i].strength;
      return 0.0;
   }

   double SumStrength(ENUM_EVIDENCE_FAMILY fam) const
   {
      double s = 0.0;
      for(int i = 0; i < count; i++)
         if(items[i].active && items[i].family == fam) s += items[i].strength;
      return s;
   }
};
#endif // ASE_EVIDENCETYPES_MQH
