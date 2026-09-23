#ifndef ASE_CONFLUENCETYPES_MQH
#define ASE_CONFLUENCETYPES_MQH
#include "ASE_Enums.mqh"
#include "ASE_EvidenceTypes.mqh"
//+------------------------------------------------------------------+
//| ACE v4.0 — Confluence / Classification types (Plan §10, §13,     |
//| §22, §24, §31)                                                   |
//| v4.0 — new file. Read by the v4 Confluence/Classifier engines     |
//| only; nothing here is read by any v3 execution path.             |
//+------------------------------------------------------------------+

enum ENUM_SETUP_ARCHETYPE
{
   ARCH_NONE                   = 0,   // NO_CLASS — plan §35: never force a classification
   ARCH_TREND_CONTINUATION     = 1,
   ARCH_LIQUIDITY_REVERSAL     = 2,
   ARCH_COMPRESSION_EXPANSION  = 3,
   ARCH_PULLBACK_CONTINUATION  = 4,
   ARCH_STRUCTURAL_REVERSAL    = 5
};

// Plan §24 — fixed breakpoints on the 0-100 normalised score, applied
// ONLY after core requirements are confirmed present (plan §23: score
// can never rescue a missing core condition).
enum ENUM_SETUP_GRADE
{
   GRADE_FAIL      = 0,   // missing core, severe conflict, stale, or execution-protection failure
   GRADE_C         = 1,   // advisory only — interesting but insufficient evidence
   GRADE_APEX_B    = 2,   // 70-79
   GRADE_APEX_A    = 3,   // 80-89
   GRADE_APEX_PLUS = 4    // 90-100
};

// Plan §12 — conflict is a first-class result, not something averaged away.
struct ConflictInfo
{
   bool   hasConflict;
   string reason;

   void Clear() { hasConflict = false; reason = ""; }
};

// Plan §10/§11 — the full result of one confluence evaluation pass.
// This is what the Setup Classifier and the opportunity logger both
// consume. Nothing here places or blocks an order — see
// CASE_ConfluenceEngine header comment for the authority boundary.
struct ConfluenceResult
{
   datetime              timestamp;
   ENUM_TRADE_DIRECTION  direction;        // winning direction, DIR_NONE if no separation
   double                longScore;        // 0-100 normalised
   double                shortScore;       // 0-100 normalised
   double                separation;       // |longScore - shortScore|
   int                   coreMet;
   int                   coreTotal;
   int                   enhancersMet;
   int                   enhancersTotal;
   ConflictInfo          conflict;
   ENUM_SETUP_ARCHETYPE  archetype;
   ENUM_SETUP_GRADE      grade;
   bool                  qualified;        // core complete + no hard conflict + grade >= APEX_B
   string                blockReason;      // populated when !qualified
   string                setupDNA;         // plan §31 — compact evidence signature
   double                avgFreshness;     // 0..1, mean of active evidence freshness
   bool                  sequenceComplete;
   bool                  sequenceCoherent;
   double                sequenceQuality;
   int                   sequenceInversions;
   int                   sequenceAgeBars;
   datetime              firstCoreTime;
   datetime              finalCoreTime;
   string                executionDecision;
   string                opportunityId;

   void Clear()
   {
      timestamp       = 0;
      direction       = DIR_NONE;
      longScore       = 0.0;
      shortScore      = 0.0;
      separation      = 0.0;
      coreMet         = 0;
      coreTotal       = 0;
      enhancersMet    = 0;
      enhancersTotal  = 0;
      conflict.Clear();
      archetype       = ARCH_NONE;
      grade           = GRADE_FAIL;
      qualified       = false;
      blockReason     = "";
      setupDNA        = "";
      avgFreshness    = 0.0;
      sequenceComplete = false; sequenceCoherent = false; sequenceQuality = 0.0;
      sequenceInversions = 0; sequenceAgeBars = 0; firstCoreTime = 0; finalCoreTime = 0;
      executionDecision = ""; opportunityId = "";
   }
};

string ASE_ArchetypeName(ENUM_SETUP_ARCHETYPE a)
{
   switch(a)
   {
      case ARCH_TREND_CONTINUATION:    return "TrendContinuation";
      case ARCH_LIQUIDITY_REVERSAL:    return "LiquidityReversal";
      case ARCH_COMPRESSION_EXPANSION: return "CompressionExpansion";
      case ARCH_PULLBACK_CONTINUATION: return "PullbackContinuation";
      case ARCH_STRUCTURAL_REVERSAL:   return "StructuralReversal";
      default:                        return "NoClass";
   }
}

string ASE_GradeName(ENUM_SETUP_GRADE g)
{
   switch(g)
   {
      case GRADE_APEX_PLUS: return "APEX+";
      case GRADE_APEX_A:    return "APEX A";
      case GRADE_APEX_B:    return "APEX B";
      case GRADE_C:         return "C";
      default:              return "FAIL";
   }
}

// Plan §31 — compact setup signature so large datasets can be grouped
// by exact evidence combination. Deterministic ordering: archetype,
// direction, then one short tag per active evidence type present in
// the set, in EVID_* enum order (stable across runs).
string ASE_BuildSetupDNA(ENUM_SETUP_ARCHETYPE archetype,
                         ENUM_TRADE_DIRECTION direction,
                         const SetupEvidenceSet &ev)
{
   string archTag;
   switch(archetype)
   {
      case ARCH_TREND_CONTINUATION:    archTag = "TRND"; break;
      case ARCH_LIQUIDITY_REVERSAL:    archTag = "REV";  break;
      case ARCH_COMPRESSION_EXPANSION: archTag = "COMP"; break;
      case ARCH_PULLBACK_CONTINUATION: archTag = "PULL"; break;
      case ARCH_STRUCTURAL_REVERSAL:   archTag = "SREV"; break;
      default:                        archTag = "NONE";
   }
   string dirTag = (direction == DIR_LONG) ? "L" : (direction == DIR_SHORT) ? "S" : "N";

   string dna = archTag + "-" + dirTag;
   for(int i = 0; i < ev.count; i++)
   {
      if(!ev.items[i].active) continue;
      string tag = "";
      switch(ev.items[i].evidType)
      {
         case EVID_H1_BOS:           tag = "HBOS"; break;
         case EVID_H1_CHOCH:         tag = "CHOCH"; break;
         case EVID_H4_ALIGNMENT:     tag = "H4AL"; break;
         case EVID_M15_FVG:          tag = "FVG";  break;
         case EVID_M15_DISPLACEMENT: tag = "DISP"; break;
         case EVID_M15_COMPRESSION:  tag = "CMPR"; break;
         case EVID_M15_EMA_PULLBACK: tag = "EMA";  break;
         case EVID_LIQUIDITY_SWEEP:  tag = "ULIQ"; break;
         case EVID_M1_DISPLACEMENT:  tag = "M1D";  break;
         case EVID_M1_MICRO_BOS:     tag = "MBOS"; break;
         case EVID_M1_REJECTION:     tag = "M1R";  break;
         case EVID_M1_EMA_ALIGN:     tag = "M1E";  break;
         case EVID_ORDER_BLOCK:      tag = "OB";   break;
         case EVID_KILL_ZONE:        tag = "KZ";   break;
         case EVID_AMD_PHASE:        tag = "AMD";  break;
         case EVID_MACRO_CORRELATION:tag = "DXY";  break;
         default: continue;   // environment/execution evidence not part of the DNA signature
      }
      dna += "-" + tag;
   }
   return dna;
}
#endif // ASE_CONFLUENCETYPES_MQH
