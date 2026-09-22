//+------------------------------------------------------------------+
//|                                                  ACE_v4.0.1.mq5 |
//|                      Adaptive Confluence Engine v4.0.1           |
//|                                                                  |
//| ACE v4.0.1 — adaptive market setup recognition architecture.     |
//| Base/control path: ACE v3.14.17, preserved alongside V4.         |
//|                                                                  |
//| Fork of v4.0.0, deployed SIDE BY SIDE with it for comparison     |
//| (not a sequential replacement) — see ASE_VERSION_TAG/            |
//| InpMagicNumber comments in Models/ASE_Config.mqh for the         |
//| isolation reasoning. Only change vs v4.0.0: two previously        |
//| zero-weight confluence evidence types (M15 compression, M1 EMA   |
//| alignment) are now scored — see CHANGELOG_v4.0.0.md Addendum 4.  |
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
#property version   "4.01"

#ifndef CALENDAR_IMPACT_HIGH
   #define CALENDAR_IMPACT_HIGH 3
#endif

// Models/ASE_Config.mqh is shared #include source with ACE_v4.0.0.mq5 (and
// ACE_v3.14.17.mq5). These two overrides MUST appear before the #include
// below — Config.mqh only supplies its v4.0.0 defaults ("ASE_v4.0.0" /
// 203157) when these are not already defined. Without them, this build
// would silently share output files AND magic number with v4.0.0, which is
// exactly the collision side-by-side deployment requires avoiding. See the
// matching comments in Models/ASE_Config.mqh.
#define ASE_VERSION_TAG   "ASE_v4.0.1"
#define ASE_MAGIC_DEFAULT 204001

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
   Print("  ACE v4.0.1 — Evidence Architecture + Confluence Engine + Setup Classifier + Adaptive Scaffolding");
   Print("  Fork of v4.0.0 for side-by-side comparison — M15_COMPRESSION/M1_EMA_ALIGN now scored (was 0.0)");
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
