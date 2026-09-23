//+------------------------------------------------------------------+
//|                                                  ACE_v4.0.2.mq5 |
//|                      Adaptive Confluence Engine v4.0.2           |
//|                                                                  |
//| ACE v4.0.2 — adaptive market setup recognition architecture.     |
//| Base/control path: ACE v3.14.17, preserved alongside V4.         |
//|                                                                  |
//| Standalone fork (own source tree, ACE_v4.0.2/) of v4.0.1 incl.   |
//| CHANGELOG_v4.0.0.md Addendum 14. Rebuilds the V4 learning layer:  |
//| learning-integrity fixes, same-setup comparison vs legacy,        |
//| regime-conditional enhancer learning + sub-setups, lifecycle/     |
//| dormancy, graduated promotion. See CHANGELOG_v4.0.2.md.           |
//| v4.0.0 control build must NOT be recompiled from the old shared   |
//| source tree (it now contains uncompiled Addendum 14 edits).       |
//|                                                                  |
//| Completed V4 engines: evidence state, directional confluence,    |
//| setup classification, sequence intelligence, freshness/decay,    |
//| opportunity attribution, theoretical outcomes, DNA analytics,    |
//| regime-aware learning, bounded adaptation, shadow candidates,    |
//| OOS-aware validation, graduated authority, discipline,            |
//| orchestrator, risk handoff and same-tick execution handoff.       |
//|                                                                  |
//| V4 default mode is observation-first: it learns from observation  |
//| #1 without changing legacy trading behaviour. Conditional/Active |
//| modes can execute only after the adaptive validation gates are    |
//| satisfied. Safety/risk protections remain mandatory.             |
//|                                                                  |
//| Source/static validation is performed in this package. MetaEditor |
//| compilation and Strategy Tester results require an MT5 runtime.  |
//+------------------------------------------------------------------+
#property copyright "ACE -- Adaptive Confluence Engine"
#property link      ""
#property version   "4.02"

#ifndef CALENDAR_IMPACT_HIGH
   #define CALENDAR_IMPACT_HIGH 3
#endif

// Own source tree, but Config.mqh still falls back to v4.0.0 defaults when
// these aren't defined first -- keep them above the #include so output
// files and magic number stay unique to this build.
#define ASE_VERSION_TAG   "ASE_v4.0.2"
#define ASE_MAGIC_DEFAULT 204002

#include "Core/ASE_StateMachine.mqh"

CASE_StateMachine g_stateMachine;
bool              g_fullyInitialized = false;   // guards OnDeinit against an instance that skipped real init

int OnInit()
{
   // ── M15 restriction ──────────────────────────────────────────────
   // The strategy's logic is timeframe-agnostic (every data call uses an
   // explicit PERIOD_M15/M1/H1/H4, never _Period/PERIOD_CURRENT for
   // anything that drives a decision — verified across the codebase
   // before building this), so this exists purely to stop an operator
   // from running the EA on a chart whose candles don't match what it's
   // actually trading, not because a different chart period would change
   // behaviour.
   //
   // MQL5 has no hook to veto a chart period change before OnDeinit/
   // OnInit fire for it — every EA on that chart gets reinitialized
   // regardless. What IS achievable: detect the wrong period here, snap
   // the chart back to M15 automatically (which itself triggers one more
   // same-kind reinit), and skip real initialization on this transient
   // pass so it costs nothing and every log file/state snapshot still
   // reflects M15 throughout. See CASE_StateMachine::Initialize()/
   // RestoreContextSnapshot() for the other half of this — restoring
   // WAIT_HTF/WAIT_SETUP/WAIT_TRIGGER context across that bounce so nothing
   // is lost, not just nothing broken.
   if(_Period != PERIOD_M15)
   {
      if((bool)MQLInfoInteger(MQL_TESTER))
      {
         // No chart to snap back in the Strategy Tester — the tester's
         // own period selector IS the chart period for the whole run.
         Print("[ASE] INIT FAILED — Strategy Tester period must be M15. Set it in the tester dialog, not on a live chart.");
         return INIT_FAILED;
      }
      Print("[ASE] Attached to ", EnumToString(_Period), " — ACE requires M15. Snapping chart back to M15.");
      ChartSetSymbolPeriod(0, _Symbol, PERIOD_M15);
      g_fullyInitialized = false;
      return INIT_SUCCEEDED;   // real init happens on the reinit this triggers, once _Period is actually M15
   }

   Print("══════════════════════════════════════════");
   Print("  ACE v4.0.2 — V4 learning rebuild (integrity fixes, legacy comparison, regime learning, lifecycle, promotion)");
   Print("  OOSMode: ", IntegerToString(InpAceV4OOSMode), " | OOSEveryK: ", IntegerToString(InpAceV4OOSEveryK));
   Print("  AceV4Mode: ", EnumToString(InpAceV4Mode),
         " | AuthTiers(obs): Cautious=", InpAceV4AuthCautiousMin,
         " Controlled=", InpAceV4AuthControlledMin,
         " Validated=", InpAceV4AuthValidatedMin);
   Print("  Base=v3.14.17 (unmodified) — see file header for the exact authority boundary");
   Print("  Fix1=PivotRegistry | Fix2=BiasInvalidation | Fix3=RegimeClassifier | Fix4=AdverseSlippageGate");
   Print("  Fix5=MacroLazyInit | Fix6=CompressionMode | Fix7=ManipVolScore | Fix8=LogIntegrity");
   Print("  EMAFallbackRanging: ", InpEMAFallbackInRanging ? "ON" : "OFF",
         " | OffSessionGuard: ", InpOffSessionBiasGuard ? "ON" : "OFF");
   Print("  RecoveryMode: ", InpDDRecoveryMode ? "ON" : "OFF",
         " | DDHalt: ", DoubleToString(InpDDHaltPct, 0), "%");
   Print("  SL=", DoubleToString(InpATRMultiplierSL,1),
         "xATR | TP1=", DoubleToString(InpATRMultiplierTP1,1),
         "xATR | Partial=", InpPartialTPEnabled ? "ON" : "OFF");
   Print("  Magic: ", IntegerToString(InpMagicNumber));
   Print("══════════════════════════════════════════");
   if(!g_stateMachine.Initialize(UninitializeReason())) { Print("[ASE] INIT FAILED"); return INIT_FAILED; }
   g_fullyInitialized = true;
   g_stateMachine.ScanUpcomingNews();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   // Skip Deinitialize() entirely for a transient pass that never ran
   // Initialize() (the wrong-timeframe bounce above) — most of the
   // engines it would call Deinitialize() on were never constructed
   // this cycle, and there is nothing meaningful to save; the real
   // instance's own OnDeinit already captured the actual state.
   if(g_fullyInitialized) g_stateMachine.Deinitialize(reason);
}
void OnTick()                   { g_stateMachine.Update(); }
double OnTester()               { return g_stateMachine.GetFitnessScore(); }

void OnCalendarEvent(const MqlCalendarEvent   &event[],
                     const MqlCalendarValue   &value[],
                     const MqlCalendarCountry &country[])
{
   for(int i = 0; i < ArraySize(value); i++)
      if(value[i].impact_type == CALENDAR_IMPACT_HIGH &&
         value[i].time > TimeCurrent())
         g_stateMachine.NotifyNewsEvent(value[i].time);
}
