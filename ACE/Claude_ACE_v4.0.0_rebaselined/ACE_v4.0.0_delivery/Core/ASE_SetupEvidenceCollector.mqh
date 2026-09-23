#ifndef ASE_SETUPEVIDENCECOLLECTOR_MQH
#define ASE_SETUPEVIDENCECOLLECTOR_MQH
#include "../Models/ASE_EvidenceTypes.mqh"
#include "ASE_SetupEngine.mqh"
#include "ASE_TriggerEngine.mqh"
#include "ASE_StructureEngine.mqh"
#include "ASE_LiquidityEngine.mqh"
#include "ASE_RegimeEngine.mqh"
//+------------------------------------------------------------------+
//| ACE v4.0 — Evidence Collector (Plan §66 Integration Principle:    |
//| "wrap existing engines rather than duplicate them")               |
//|                                                                  |
//| Calls ONLY public methods of the existing engines (including the |
//| two additive EvaluateAllEvidence() methods added to SetupEngine   |
//| and TriggerEngine). Never writes to any legacy engine's state.    |
//| Two collection passes, matching where the data is already         |
//| resolved in the existing StateMachine pipeline:                   |
//|                                                                  |
//|   CollectM15Context() — called once per M15 bar from              |
//|     ProcessSetup(), after m_ctx.direction/regimeAtEntry are        |
//|     resolved. Populates H1/H4/M15 evidence.                       |
//|                                                                  |
//|   CollectM1Context() — called every tick from ProcessTrigger(),   |
//|     after the scorecard's vol/session/spread fields are computed, |
//|     for genuine same-tick M1 responsiveness. Internally clears     |
//|     and re-adds its own evidence types each call (REPLACE, not     |
//|     append — see SetupEvidenceSet::RemoveTypes()) and throttles    |
//|     only the expensive DetectSweep() scan to once per M1 bar       |
//|     close; the M15 evidence gathered earlier in the bar by         |
//|     CollectM15Context() is untouched either way.                  |
//|                                                                  |
//| v4.0 — new file. Nothing here is read by any v3 execution path.   |
//+------------------------------------------------------------------+
class CASE_SetupEvidenceCollector
{
private:
   SetupEvidenceSet m_set;
   datetime         m_m15BarStamp;

   // v4.0 fix — DetectSweep() throttle state (see CollectM1Context).
   datetime m_liqBarStamp;
   bool     m_liqCachedActive;    double m_liqCachedScore;    string m_liqCachedReason;
   bool     m_oppLiqCachedActive; double m_oppLiqCachedScore; string m_oppLiqCachedReason;

private:
   void NormalizeEvidenceTimes()
   {
      datetime h1=iTime(_Symbol,PERIOD_H1,1);
      datetime h4=iTime(_Symbol,PERIOD_H4,1);
      datetime m15=iTime(_Symbol,PERIOD_M15,1);
      datetime m1=iTime(_Symbol,PERIOD_M1,1);
      datetime now=TimeCurrent();
      for(int i=0;i<m_set.count;i++)
      {
         switch(m_set.items[i].sourceTF)
         {
            case PERIOD_H4: m_set.items[i].timestamp=(h4>0?h4:now); break;
            case PERIOD_H1: m_set.items[i].timestamp=(h1>0?h1:now); break;
            case PERIOD_M15: m_set.items[i].timestamp=(m15>0?m15:now); break;
            case PERIOD_M1: m_set.items[i].timestamp=(m1>0?m1:now); break;
            default: break;
         }
         long age=(long)(now-m_set.items[i].timestamp);
         if(age<0) age=0;
         int secs=(m_set.items[i].sourceTF==PERIOD_H4?14400:m_set.items[i].sourceTF==PERIOD_H1?3600:m_set.items[i].sourceTF==PERIOD_M15?900:60);
         m_set.items[i].freshnessBars=(secs>0)?(int)(age/secs):0;
      }
   }

public:
   CASE_SetupEvidenceCollector() : m_m15BarStamp(0), m_liqBarStamp(0),
      m_liqCachedActive(false), m_liqCachedScore(0.0), m_liqCachedReason(""),
      m_oppLiqCachedActive(false), m_oppLiqCachedScore(0.0), m_oppLiqCachedReason("")
   { m_set.Reset(); }

   // MQL5 has no reference-return, so this hands back a value copy —
   // the set is small (<= ASE_MAX_EVIDENCE items) and this is called
   // at most once per M1 tick, matching the cost profile of the
   // legacy m_trigger.Evaluate() call it sits alongside.
   SetupEvidenceSet Get() const { return m_set; }

   // Call once at the top of a new M15 bar, before either collection pass.
   void BeginBar(datetime m15Bar)
   {
      if(m15Bar != m_m15BarStamp)
      {
         m_set.Reset();
         m_set.evalTime = m15Bar;
         m_m15BarStamp  = m15Bar;
      }
   }

   //------------------------------------------------------------------
   // H1/H4/M15 evidence. Direction/regime context is exactly what
   // ProcessSetup() already has in m_ctx by this point — passed in
   // rather than re-derived, so this can never disagree with what
   // the legacy path is acting on.
   //------------------------------------------------------------------
   void CollectM15Context(CASE_StructureEngine &structure,
                           CASE_SetupEngine     &setup,
                           CASE_RegimeEngine    &regime,
                           ENUM_TRADE_DIRECTION direction,
                           const RegimeState    &regimeState,
                           ENUM_TRADE_DIRECTION h4ClosedDir,
                           double h4BiasScore,
                           double ctDispMultiplier,
                           double ctFVGMinGap,
                           double ctFVGMaxDepth)
   {
      if(direction == DIR_NONE) return;
      datetime now = TimeCurrent();

      // H1 BOS — deliberately does NOT call structure.Evaluate() again.
      // That method mutates internal engine state (m_h4ClosedDir and
      // likely pivot-registry bookkeeping) as a side effect of scanning,
      // so invoking it a second time per bar from this read-only
      // collector risked corrupting state the legacy execution path in
      // ProcessHTF() also depends on (caught during implementation —
      // see chat). Instead this reads h4BiasScore (m_ctx.scoreCard.h4Bias,
      // already computed once by ProcessHTF this cycle) and
      // GetH1BiasCurrent() (a plain accessor, confirmed no side effects
      // and, unlike GetLastStructure(), actually maintained — see the
      // fix note below) — both already-resolved values, zero re-scanning.
      SetupEvidence e;
      e.Clear();
      e.evidType = EVID_H1_BOS; e.family = FAM_STRUCTURE; e.direction = direction;
      // v4.0 fix — found by tracing why EVID_H1_BOS never fired across
      // 44 consecutive opportunities in an uploaded run (every one
      // classified NoClass; H1_BOS is a required core condition for 4
      // of the 5 archetypes). GetLastStructure() reads m_lastBOS, which
      // is declared and read but NEVER ASSIGNED anywhere in
      // ASE_StructureEngine.mqh outside its constructor default
      // (STRUCT_NONE) — a dead field, not a live signal. It always
      // returned false here, regardless of actual H1 structure. Fixed
      // to GetH1BiasCurrent() — the field Evaluate() actually maintains
      // (set whenever a fresh BOS updates the bias, cleared on
      // invalidation) and already has a public, side-effect-free getter.
      e.active = (structure.GetH1BiasCurrent() == direction) && (h4BiasScore > 0.0);
      e.strength = h4BiasScore;
      e.reason = "cached from this cycle's ProcessHTF() confirmation";
      e.timestamp = now; e.sourceTF = PERIOD_H1;
      m_set.Add(e);

      // H1 CHoCH — an explicit lower-timeframe structural change against
      // the established H4 direction. This is intentionally separate from
      // H1 BOS so Structural Reversal is not approximated by missing alignment.
      double hHi[],hLo[],hCl[]; ArraySetAsSeries(hHi,true);ArraySetAsSeries(hLo,true);ArraySetAsSeries(hCl,true);
      bool choch=false;
      if(CopyHigh(_Symbol,PERIOD_H1,0,8,hHi)>=8 && CopyLow(_Symbol,PERIOD_H1,0,8,hLo)>=8 && CopyClose(_Symbol,PERIOD_H1,0,8,hCl)>=8)
      {
         double priorHi=hHi[2],priorLo=hLo[2];
         for(int k=3;k<=6;k++){if(hHi[k]>priorHi)priorHi=hHi[k];if(hLo[k]<priorLo)priorLo=hLo[k];}
         choch=((h4ClosedDir==DIR_SHORT && direction==DIR_LONG && hCl[1]>priorHi) ||
               (h4ClosedDir==DIR_LONG && direction==DIR_SHORT && hCl[1]<priorLo));
      }
      e.Clear();
      e.evidType=EVID_H1_CHOCH; e.family=FAM_STRUCTURE; e.direction=direction;
      e.active=choch; e.strength=choch?15.0:0.0; e.reason=choch?"H1 structure broke against H4 direction":"No H1 CHoCH";
      e.timestamp=now; e.sourceTF=PERIOD_H1;
      m_set.Add(e);

      // H4 alignment — plan §5.1. Not a detector of its own; derived from
      // the H4 closed-candle direction StructureEngine already tracks.
      e.Clear();
      e.evidType = EVID_H4_ALIGNMENT; e.family = FAM_STRUCTURE; e.direction = direction;
      e.active = (h4ClosedDir == direction); e.strength = e.active ? 5.0 : 0.0;
      e.reason = StringFormat("H4=%s vs dir=%s", h4ClosedDir == DIR_LONG ? "L" : h4ClosedDir == DIR_SHORT ? "S" : "N",
                               direction == DIR_LONG ? "L" : "S");
      e.timestamp = now; e.sourceTF = PERIOD_H4;
      m_set.Add(e);

      // Regime/environment — one evidence item per plan §5.5.
      e.Clear();
      e.evidType = EVID_VOLATILITY_STATE; e.family = FAM_ENVIRONMENT; e.direction = direction;
      e.active = (regimeState.regime != REGIME_DEAD && regimeState.regime != REGIME_HIGH_VOL &&
                  regimeState.regime != REGIME_UNKNOWN);
      e.strength = regime.GetVolatilityScoreFromState(regimeState);
      e.reason = regime.RegimeName(regimeState.regime);
      e.timestamp = now; e.sourceTF = PERIOD_H1;
      m_set.Add(e);

      // M15 FVG/Displacement/Compression/EMA-Pullback — all four,
      // independent of which one the legacy cascade would have picked.
      setup.EvaluateAllEvidence(direction, m_set, regimeState.h4EMASep, regimeState.h4ATR,
                                 h4ClosedDir, ctDispMultiplier, ctFVGMinGap, ctFVGMaxDepth);
   }

   //------------------------------------------------------------------
   // M1 + liquidity + session/spread evidence. Called once the
   // scorecard's vol/session/spread fields are already computed in
   // ProcessTrigger(), so this reuses those values instead of
   // recomputing them a second way.
   //------------------------------------------------------------------
   void CollectM1Context(CASE_TriggerEngine   &trigger,
                          CASE_LiquidityEngine &liq,
                          ENUM_TRADE_DIRECTION direction,
                          ENUM_MARKET_REGIME   regime,
                          ENUM_LIQ_MODE        liqMode,
                          double                sessionScore,
                          double                spreadScore)
   {
      if(direction == DIR_NONE) return;
      datetime now = TimeCurrent();

      // v4.0 fix — this is called every tick now (same-tick
      // responsiveness), so every M1-scoped evidence type this method
      // owns must be cleared before re-adding this tick's read, or it
      // accumulates duplicates that both inflate the confluence score
      // and fill ASE_MAX_EVIDENCE within ~2 ticks — see
      // SetupEvidenceSet::RemoveTypes() for the full explanation. This
      // does NOT touch the once-per-bar M15/H1/H4 items added by
      // CollectM15Context — those use different evidence types and are
      // untouched by this list.
      ENUM_EVIDENCE_TYPE m1Types[] = { EVID_M1_DISPLACEMENT, EVID_M1_MICRO_BOS, EVID_M1_REJECTION,
                                        EVID_M1_EMA_ALIGN, EVID_LIQUIDITY_SWEEP,
                                        EVID_SESSION_QUALITY, EVID_SPREAD_QUALITY };
      m_set.RemoveTypes(m1Types);

      trigger.EvaluateAllEvidence(direction, m_set);

      // Opposing M1 evidence is collected as well so lower-TF contradictions
      // are first-class evidence rather than being averaged away. This does
      // not touch legacy execution state; EvaluateAllEvidence is additive
      // (no side effects — see ASE_TriggerEngine.mqh header comment).
      ENUM_TRADE_DIRECTION opposite = (direction == DIR_LONG) ? DIR_SHORT : DIR_LONG;
      trigger.EvaluateAllEvidence(opposite, m_set);

      // v4.0 fix — DetectSweep() does a real ~34-bar buffer scan with its
      // own Print() calls (a real side effect on the Experts log, not
      // just cost) and is regime-conditional legacy-engine logic, not a
      // detector whose result is meaningful to refresh sub-bar. Calling
      // it twice (both directions) on EVERY tick — as this did right
      // after the same-tick change — reintroduced the exact log-flood
      // this collector was built to avoid, doubled. Throttled here to
      // once per M1 bar close; the cheap, side-effect-free
      // trigger.EvaluateAllEvidence() calls above stay per-tick, so
      // genuine same-tick M1 displacement/microBOS/rejection
      // responsiveness is preserved — only the expensive, low-frequency-
      // relevant liquidity scan is bounded.
      datetime m1Bar = iTime(_Symbol, PERIOD_M1, 0);
      if(m1Bar != m_liqBarStamp)
      {
         m_liqBarStamp = m1Bar;
         ValidationResult liqRes = liq.DetectSweep(direction, regime, liqMode);
         ValidationResult oppLiqRes = liq.DetectSweep(opposite, regime, liqMode);
         m_liqCachedActive = liqRes.passed; m_liqCachedScore = liqRes.score; m_liqCachedReason = liqRes.reason;
         m_oppLiqCachedActive = oppLiqRes.passed; m_oppLiqCachedScore = oppLiqRes.score; m_oppLiqCachedReason = oppLiqRes.reason;
      }

      SetupEvidence e;
      e.Clear();
      e.evidType = EVID_LIQUIDITY_SWEEP; e.family = FAM_LIQUIDITY; e.direction = direction;
      e.active = m_liqCachedActive; e.strength = m_liqCachedScore; e.reason = m_liqCachedReason;
      e.timestamp = now; e.sourceTF = PERIOD_M15;
      m_set.Add(e);

      e.Clear();
      e.evidType = EVID_LIQUIDITY_SWEEP; e.family = FAM_LIQUIDITY; e.direction = opposite;
      e.active = m_oppLiqCachedActive; e.strength = m_oppLiqCachedScore; e.reason = m_oppLiqCachedReason;
      e.timestamp = now; e.sourceTF = PERIOD_M15;
      m_set.Add(e);

      e.Clear();
      e.evidType = EVID_SESSION_QUALITY; e.family = FAM_ENVIRONMENT; e.direction = direction;
      e.active = sessionScore > 0.0; e.strength = sessionScore;
      e.reason = "session score"; e.timestamp = now; e.sourceTF = PERIOD_CURRENT;
      m_set.Add(e);

      e.Clear();
      e.evidType = EVID_SPREAD_QUALITY; e.family = FAM_EXECUTION; e.direction = direction;
      e.active = spreadScore > 0.0; e.strength = spreadScore;
      e.reason = "spread score"; e.timestamp = now; e.sourceTF = PERIOD_CURRENT;
      m_set.Add(e);
      NormalizeEvidenceTimes();
   }
};
#endif // ASE_SETUPEVIDENCECOLLECTOR_MQH
