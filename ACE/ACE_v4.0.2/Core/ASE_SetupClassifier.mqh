#ifndef ASE_SETUPCLASSIFIER_MQH
#define ASE_SETUPCLASSIFIER_MQH
#include "../Models/ASE_EvidenceTypes.mqh"
#include "../Models/ASE_ConfluenceTypes.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ACE v4.0 — Setup Classifier (Plan §13-18, §21, §23-25, §35, §53)  |
//|                                                                  |
//| Consumes the SAME evidence set and the ConfluenceEngine's result, |
//| fills archetype/coreMet/coreTotal/enhancersMet/grade/qualified.   |
//| Never modifies direction/longScore/shortScore/conflict — those    |
//| stay the Confluence Engine's output, read-only here.              |
//|                                                                  |
//| PRECEDENCE (plan §17, §53): structural/reversal archetypes are    |
//| tested before continuation archetypes, since a setup meeting a    |
//| reversal's stricter core is more specifically classified than one |
//| that also happens to satisfy a looser continuation core. First    |
//| archetype whose full core list is met wins; ARCH_NONE if none are |
//| (plan §35 — never force a classification).                       |
//|                                                                  |
//| KNOWN GAP: "structural reversal" per plan §18 needs "H1 BOS       |
//| against the established H4 trend" — approximated here as          |
//| (H1_BOS active AND H4_ALIGNMENT NOT active), since that is what   |
//| the existing evidence set can actually express; a true prior-H4-  |
//| trend-persistence check would need StructureEngine internals this |
//| delivery does not touch. Documented, not silently assumed.        |
//|                                                                  |
//| v4.0 — new file. archetype/grade/qualified here are NEVER read by |
//| the legacy execution path — see ASE_SetupAnalytics.mqh for the    |
//| authority boundary this stops at (logging + adaptation-box        |
//| internal use only).                                               |
//+------------------------------------------------------------------+
class CASE_SetupClassifier
{
private:
   // v4.0.2 -- coreMask records WHICH ENUM_EVIDENCE_TYPE bits (1-20, bit i =
   // 1UL<<i) were counted as a REAL evidence-based core item for this check.
   // Regime-based core items (e.g. CheckTrendContinuation's REGIME_TRENDING
   // gate, CheckCompressionExpansion's REGIME_COMPRESSION gate) are NOT
   // evidence types and never set a bit here -- there is nothing for
   // Classify()'s enhancer-identity pass to exclude on their behalf, they
   // simply aren't evidence at all.
   struct CoreCheck { int met; int total; bool complete; ulong coreMask; };

   // v4.0 fix — every HasActive() call below now takes `dir` explicitly
   // (previously several checks omitted it and relied on the then-true
   // but undeclared invariant that a bar's evidence set only ever holds
   // one direction — see the HasActive(type,dir) overload comment in
   // ASE_EvidenceTypes.mqh).
   CoreCheck CheckTrendContinuation(const SetupEvidenceSet &ev, ENUM_MARKET_REGIME regime, ENUM_TRADE_DIRECTION dir)
   {
      CoreCheck c; c.total = 4; c.met = 0; c.coreMask = 0;   // regime handled by caller as a 5th gate, not evidence-set-based
      if(regime == REGIME_TRENDING) c.met++;
      if(ev.HasActive(EVID_H1_BOS, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_H1_BOS); }
      if(ev.HasActive(EVID_M15_FVG, dir) || ev.HasActive(EVID_M15_EMA_PULLBACK, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M15_FVG, dir))          c.coreMask |= (1UL << (ulong)EVID_M15_FVG);
         if(ev.HasActive(EVID_M15_EMA_PULLBACK, dir)) c.coreMask |= (1UL << (ulong)EVID_M15_EMA_PULLBACK);
      }
      if(ev.HasActive(EVID_M15_DISPLACEMENT, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_M15_DISPLACEMENT); }
      c.total = 5;
      if(ev.HasActive(EVID_M1_DISPLACEMENT, dir) || ev.HasActive(EVID_M1_MICRO_BOS, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M1_DISPLACEMENT, dir)) c.coreMask |= (1UL << (ulong)EVID_M1_DISPLACEMENT);
         if(ev.HasActive(EVID_M1_MICRO_BOS, dir))    c.coreMask |= (1UL << (ulong)EVID_M1_MICRO_BOS);
      }
      c.complete = (c.met == c.total);
      return c;
   }

   CoreCheck CheckLiquidityReversal(const SetupEvidenceSet &ev, ENUM_TRADE_DIRECTION dir)
   {
      CoreCheck c; c.total = 4; c.met = 0; c.coreMask = 0;
      if(ev.HasActive(EVID_LIQUIDITY_SWEEP, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_LIQUIDITY_SWEEP); }      // pool + sweep (composite detector)
      if(ev.HasActive(EVID_M1_REJECTION, dir))    { c.met++; c.coreMask |= (1UL << (ulong)EVID_M1_REJECTION); }      // rejection
      if(ev.HasActive(EVID_H1_BOS, dir))          { c.met++; c.coreMask |= (1UL << (ulong)EVID_H1_BOS); }      // structural change (approximation — see file header)
      if(ev.HasActive(EVID_M1_DISPLACEMENT, dir) || ev.HasActive(EVID_M1_MICRO_BOS, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M1_DISPLACEMENT, dir)) c.coreMask |= (1UL << (ulong)EVID_M1_DISPLACEMENT);
         if(ev.HasActive(EVID_M1_MICRO_BOS, dir))    c.coreMask |= (1UL << (ulong)EVID_M1_MICRO_BOS);
      }
      c.complete = (c.met == c.total);
      return c;
   }

   CoreCheck CheckCompressionExpansion(const SetupEvidenceSet &ev, ENUM_MARKET_REGIME regime, ENUM_TRADE_DIRECTION dir)
   {
      CoreCheck c; c.total = 4; c.met = 0; c.coreMask = 0;
      // v4.0.1 Fix -- regime now a core item, reversing the original
      // "not observable from one evidence set" rationale. ASE_RegimeEngine's
      // classification carries a 2-consecutive-H1-bar stability/hysteresis
      // rule (see ClassifyRegime()) before it flips to a new regime, so at
      // the moment M15/M1 breakout evidence first fires, the regime tag has
      // almost always not yet had time to flip away from COMPRESSION -- it
      // IS observable here, via the same `regime` parameter every other
      // core check in this file already reads. Without this, the archetype
      // matched any regime's leftover compression-shaped evidence (this is
      // checked LAST in Classify()'s precedence order, after the four more
      // specific archetypes have already failed), including Manipulation,
      // where a local micro-consolidation right before a stop-hunt sweep
      // looks identical to this core-4 checklist but is not the same setup.
      if(regime == REGIME_COMPRESSION) c.met++;
      // Compression's OWN evidence fires on the compressed state, but the
      // archetype is about the EXPANSION out of it -- this uses the
      // compression detector firing at all (its check already requires ATR
      // beginning to expand -- see CheckCompression()) as the proxy for
      // "compression -> expansion" in progress.
      if(ev.HasActive(EVID_M15_COMPRESSION, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_M15_COMPRESSION); }
      if(ev.HasActive(EVID_M15_DISPLACEMENT, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_M15_DISPLACEMENT); }
      if(ev.HasActive(EVID_M1_DISPLACEMENT, dir) || ev.HasActive(EVID_M1_MICRO_BOS, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M1_DISPLACEMENT, dir)) c.coreMask |= (1UL << (ulong)EVID_M1_DISPLACEMENT);
         if(ev.HasActive(EVID_M1_MICRO_BOS, dir))    c.coreMask |= (1UL << (ulong)EVID_M1_MICRO_BOS);
      }
      c.complete = (c.met == c.total);
      return c;
   }

   CoreCheck CheckPullbackContinuation(const SetupEvidenceSet &ev, ENUM_TRADE_DIRECTION dir)
   {
      CoreCheck c; c.total = 4; c.met = 0; c.coreMask = 0;
      if(ev.HasActive(EVID_H1_BOS, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_H1_BOS); }
      if(ev.HasActive(EVID_M15_FVG, dir) || ev.HasActive(EVID_M15_EMA_PULLBACK, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M15_FVG, dir))          c.coreMask |= (1UL << (ulong)EVID_M15_FVG);
         if(ev.HasActive(EVID_M15_EMA_PULLBACK, dir)) c.coreMask |= (1UL << (ulong)EVID_M15_EMA_PULLBACK);
      }
      if(ev.HasActive(EVID_M1_REJECTION, dir) || ev.HasActive(EVID_M1_DISPLACEMENT, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M1_REJECTION, dir))    c.coreMask |= (1UL << (ulong)EVID_M1_REJECTION);
         if(ev.HasActive(EVID_M1_DISPLACEMENT, dir)) c.coreMask |= (1UL << (ulong)EVID_M1_DISPLACEMENT);
      }
      if(ev.HasActive(EVID_M1_MICRO_BOS, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_M1_MICRO_BOS); }
      c.complete = (c.met == c.total);
      return c;
   }

   CoreCheck CheckStructuralReversal(const SetupEvidenceSet &ev, ENUM_TRADE_DIRECTION dir)
   {
      CoreCheck c; c.total = 5; c.met = 0; c.coreMask = 0;
      if(ev.HasActive(EVID_H1_CHOCH, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_H1_CHOCH); }   // explicit H1 structure change against established H4 trend
      if(ev.HasActive(EVID_M15_DISPLACEMENT, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_M15_DISPLACEMENT); }
      if(ev.HasActive(EVID_M15_FVG, dir) || ev.HasActive(EVID_M15_EMA_PULLBACK, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M15_FVG, dir))          c.coreMask |= (1UL << (ulong)EVID_M15_FVG);
         if(ev.HasActive(EVID_M15_EMA_PULLBACK, dir)) c.coreMask |= (1UL << (ulong)EVID_M15_EMA_PULLBACK);
      }
      if(ev.HasActive(EVID_LIQUIDITY_SWEEP, dir)) { c.met++; c.coreMask |= (1UL << (ulong)EVID_LIQUIDITY_SWEEP); }   // core here, not enhancer — plan §18: higher bar than continuation
      if(ev.HasActive(EVID_M1_DISPLACEMENT, dir) || ev.HasActive(EVID_M1_MICRO_BOS, dir))
      {
         c.met++;
         if(ev.HasActive(EVID_M1_DISPLACEMENT, dir)) c.coreMask |= (1UL << (ulong)EVID_M1_DISPLACEMENT);
         if(ev.HasActive(EVID_M1_MICRO_BOS, dir))    c.coreMask |= (1UL << (ulong)EVID_M1_MICRO_BOS);
      }
      c.complete = (c.met == c.total);
      return c;
   }

   ENUM_SETUP_GRADE GradeFromScore(double score) const
   {
      if(score >= 90.0) return GRADE_APEX_PLUS;
      if(score >= 80.0) return GRADE_APEX_A;
      if(score >= 70.0) return GRADE_APEX_B;
      return GRADE_C;
   }

public:
   // ev/regime/dir describe the SAME evaluation pass conf already
   // summarised. conf.direction/longScore/shortScore/conflict are
   // read, never written, here.
   void Classify(const SetupEvidenceSet &ev, ENUM_MARKET_REGIME regime,
                 ConfluenceResult &conf)
   {
      if(conf.direction == DIR_NONE)
      {
         conf.archetype = ARCH_NONE;
         conf.grade = GRADE_FAIL;
         conf.qualified = false;
         conf.blockReason = "No directional separation";
         conf.setupDNA = ASE_BuildSetupDNA(ARCH_NONE, DIR_NONE, ev);
         return;
      }

      // Precedence order — see file header. Structural/liquidity
      // reversal checked before the two continuation archetypes;
      // compression checked last (plan §16: advisory-only by design,
      // should not casually win over a continuation classification).
      CoreCheck srev = CheckStructuralReversal(ev, conf.direction);
      CoreCheck lrev = CheckLiquidityReversal(ev, conf.direction);
      CoreCheck trnd = CheckTrendContinuation(ev, regime, conf.direction);
      CoreCheck pull = CheckPullbackContinuation(ev, conf.direction);
      CoreCheck comp = CheckCompressionExpansion(ev, regime, conf.direction);

      ENUM_SETUP_ARCHETYPE winner = ARCH_NONE;
      CoreCheck winnerCheck; winnerCheck.met = 0; winnerCheck.total = 1; winnerCheck.complete = false; winnerCheck.coreMask = 0;

      if(srev.complete)      { winner = ARCH_STRUCTURAL_REVERSAL;   winnerCheck = srev; }
      else if(lrev.complete) { winner = ARCH_LIQUIDITY_REVERSAL;    winnerCheck = lrev; }
      else if(trnd.complete) { winner = ARCH_TREND_CONTINUATION;    winnerCheck = trnd; }
      else if(pull.complete) { winner = ARCH_PULLBACK_CONTINUATION; winnerCheck = pull; }
      else if(comp.complete) { winner = ARCH_COMPRESSION_EXPANSION; winnerCheck = comp; }
      else
      {
         // plan §35 — no forced classification. Still surface whichever
         // candidate came closest, for opportunity-log diagnostic value
         // (§29/§48 false-negative analysis needs this, not just a bare
         // "NONE"). This does NOT count as qualified.
         CoreCheck best = trnd; ENUM_SETUP_ARCHETYPE bestArch = ARCH_TREND_CONTINUATION;
         if(srev.met > best.met) { best = srev; bestArch = ARCH_STRUCTURAL_REVERSAL; }
         if(lrev.met > best.met) { best = lrev; bestArch = ARCH_LIQUIDITY_REVERSAL; }
         if(pull.met > best.met) { best = pull; bestArch = ARCH_PULLBACK_CONTINUATION; }
         if(comp.met > best.met) { best = comp; bestArch = ARCH_COMPRESSION_EXPANSION; }

         conf.archetype   = ARCH_NONE;
         conf.coreMet      = best.met;
         conf.coreTotal    = best.total;
         conf.grade         = GRADE_FAIL;
         conf.qualified      = false;
         conf.blockReason  = StringFormat("No archetype core complete — closest: %s (%d/%d)",
                                          ASE_ArchetypeName(bestArch), best.met, best.total);
         conf.setupDNA     = ASE_BuildSetupDNA(ARCH_NONE, conf.direction, ev);
         return;
      }

      conf.archetype  = winner;
      conf.coreMet     = winnerCheck.met;
      conf.coreTotal   = winnerCheck.total;
      conf.coreMask    = winnerCheck.coreMask;
      conf.setupDNA    = ASE_BuildSetupDNA(winner, conf.direction, ev);

      // v4.0.2 -- Enhancers by real identity, not count-subtraction. An
      // item is a genuine enhancer only if its evidence TYPE bit is not
      // in the winning core's coreMask (regardless of how many other
      // items of the same type exist) AND it isn't FAM_NONE (matching the
      // prior exclusion). enhancersMet/enhancersTotal are KEPT as counts
      // (backward-compatible with anything already reading them as
      // numbers, e.g. CSV/report output) but are now computed from this
      // identity pass rather than a met/total subtraction, which could
      // previously miscount whenever a core check's "OR" branches meant
      // fewer distinct evidence types were consumed than c.met implied.
      int enhMet = 0, enhTotal = 0;
      ulong enhMask = 0;
      ulong evalMask = 0;   // v4.0.2 Phase 2 item 2 -- superset of enhMask; set regardless of active
      for(int i = 0; i < ev.count; i++)
      {
         if(ev.items[i].direction != conf.direction) continue;
         if(ev.items[i].family == FAM_NONE) continue;
         ulong bit = (1UL << (ulong)ev.items[i].evidType);
         if((conf.coreMask & bit) != 0) continue;   // real core identity exclusion, not a count guess
         evalMask |= bit;   // this type was evaluated for this direction this cycle, active or not
         enhTotal++;
         if(ev.items[i].active) { enhMet++; enhMask |= bit; }
      }
      conf.enhancersMet   = enhMet;
      conf.enhancersTotal = enhTotal;
      conf.enhancerMask   = enhMask;
      conf.evaluatedMask  = evalMask;

      double winningScore = (conf.direction == DIR_LONG) ? conf.longScore : conf.shortScore;
      // Sequence coherence is a quality modifier, never a substitute for core evidence.
      winningScore *= (0.80 + 0.20 * MathMax(0.0, MathMin(1.0, conf.sequenceQuality)));

      // plan §23 — score can never rescue a missing core requirement.
      if(!winnerCheck.complete)
      {
         conf.grade       = GRADE_FAIL;
         conf.qualified   = false;
         conf.blockReason = StringFormat("%s core incomplete (%d/%d)", ASE_ArchetypeName(winner), winnerCheck.met, winnerCheck.total);
         return;
      }

      if(conf.conflict.hasConflict)
      {
         conf.grade       = GRADE_FAIL;
         conf.qualified   = false;
         conf.blockReason = "Conflict: " + conf.conflict.reason;
         return;
      }

      if(conf.avgFreshness < 0.35)
      {
         conf.grade=GRADE_FAIL; conf.qualified=false;
         conf.blockReason=StringFormat("Evidence too stale (freshness %.2f)",conf.avgFreshness);
         return;
      }

      if(conf.separation < InpAceV4MinSeparation)   // plan §11 — absolute strength alone is not sufficient
      {
         conf.grade       = GRADE_FAIL;
         conf.qualified   = false;
         conf.blockReason = StringFormat("Directional separation too low (%.1f)", conf.separation);
         return;
      }

      conf.grade     = GradeFromScore(winningScore);
      conf.qualified = (conf.grade != GRADE_FAIL && conf.grade != GRADE_C);
      conf.blockReason = conf.qualified ? "" : StringFormat("Grade %s below execution threshold", ASE_GradeName(conf.grade));
   }
};
#endif // ASE_SETUPCLASSIFIER_MQH
