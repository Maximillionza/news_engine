#ifndef ASE_STATEMACHINE_MQH
#define ASE_STATEMACHINE_MQH
#include <Trade/Trade.mqh>

// v4.0.2 Phase 1 -- oppId-keyed join buffer for the "both" comparison
// cell (V4 would-qualify AND legacy traded). Sized generously: at most
// InpMaxPositions concurrent trades exist, but a setup's theoretical
// resolution and its real trade's close are two independent async
// events, so several can be in flight waiting for their other half.
#define ASE_MAX_PENDING_COMPARE 40
// A theoretical resolves within InpAceV4TheoreticalMaxBars M15 bars (see
// ASE_Config.mqh), but the REAL trade for the same setup may still be
// open well after that -- this join needs a much longer, separate
// timeout. ~200 M15 bars (~2 days) is generous without leaking memory
// indefinitely if a trade is somehow never seen closing.
#define ASE_COMPARE_JOIN_TIMEOUT_SECONDS (200*15*60)

// Models
#include "../Models/ASE_Enums.mqh"
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
#include "../Models/ASE_State.mqh"

// Utilities
#include "../Utilities/ASE_Logger.mqh"
#include "../Utilities/ASE_Math.mqh"
#include "../Utilities/ASE_Time.mqh"
#include "../Utilities/ASE_Broker.mqh"

// Core engines
#include "ASE_Diagnostics.mqh"
#include "ASE_Telemetry.mqh"
#include "ASE_AlertEngine.mqh"
#include "ASE_SessionEngine.mqh"
#include "ASE_NewsEngine.mqh"
#include "ASE_ValidationEngine.mqh"
#include "ASE_RegimeEngine.mqh"
// v3.6.0 — ASE_BiasEngine.mqh removed. BiasEngine.Evaluate() was never called
// in v3.5.0 — StructureEngine (H1 BOS) fully replaced it. The two H4 EMA
// indicator handles it held open served no purpose and wasted handle slots.
#include "ASE_SetupEngine.mqh"
#include "ASE_TriggerEngine.mqh"
#include "ASE_LiquidityEngine.mqh"
//#include "ASE_DirectionGate.mqh"   // v3.10.0 removed in v3.12.3 — see pullback filter in ProcessHTF
#include "ASE_ScoringEngine.mqh"
#include "ASE_RiskEngine.mqh"
#include "ASE_ExecutionEngine.mqh"
#include "ASE_TradeManager.mqh"
#include "ASE_ChartVisuals.mqh"   // v3.14.17 Fix 24 — active-trade panel
#include "ASE_PositionClusterProtection.mqh"
#include "ASE_BrokerNormalization.mqh"
#include "ASE_MonteCarlo.mqh"
#include "ASE_OptimizerBridge.mqh"
#include "ASE_VPSOptimizer.mqh"
#include "ASE_StructureEngine.mqh"
#include "ASE_WalkForwardEngine.mqh"

// Reporting
#include "../Reporting/ASE_HTMLReporter.mqh"
#include "../Reporting/ASE_TradeExporter.mqh"

// Calibration state logger
#include "ASE_StateLogger.mqh"

// v3.14.0 — Regime profile engine
#include "ASE_RegimeProfile.mqh"

// v4.0 — Trade attribution (§4)
#include "ASE_TradeAttribution.mqh"

// v4.0 — Evidence/Confluence/Classifier/Adaptive scaffolding.
// See ASE_v4_0_Plan_UPDATED.md Phase 1-4 + §82. Every call site this
// section's classes are used from is gated behind
// InpAceV4Mode >= ACEV4_EVIDENCE and none of them write to any
// variable a v3 execution decision reads — see each file's header
// comment for the specific authority boundary.
#include "ASE_SetupEvidenceCollector.mqh"
#include "ASE_ConfluenceEngine.mqh"
#include "ASE_SetupClassifier.mqh"
#include "ASE_SetupAnalytics.mqh"
#include "ASE_ConfluenceSequence.mqh"
#include "ASE_AdaptiveEngine.mqh"
#include "ASE_LearningMigrator.mqh"   // v4.0.2 amendment -- provenance-stamped learning migration
#include "ASE_DisciplineEngine.mqh"
#include "ASE_Orchestrator.mqh"
#include "ASE_V4Dashboard.mqh"

//+------------------------------------------------------------------+
//| ASE v3 — Deterministic State Machine                             |
//| Every decision is explainable. Every rejection is logged.        |
//|                                                                  |
//| Fix log (audit pass):                                            |
//|   #1  VPS throttle now active — ShouldProcess() wired in Update()|
//|   #2  m_risk.UpdatePeak() called every tick — DD tracking live   |
//|   #3  InpLiquidityConfirm now gates entry, not just scores it    |
//|   #4  m_ctx.liquidityType assigned from m_liq.GetLiquidityType() |
//|   #5  ScanUpcomingNews() wired to CalendarValueHistory (48h)     |
//|   #9  STATE_POSITION_OPEN removed — MANAGE stays in MANAGE       |
//|   #11 HistorySelect window uses m_tradeOpenTime (not 120s)       |
//|   #12 Exit reason tolerance is ATR-relative (not _Point*5)       |
//+------------------------------------------------------------------+
class CASE_StateMachine
{
private:
   ENUM_ASE_STATE         m_state;
   ASE_PipelineContext    m_ctx;
   string                 m_ctxStatePath;   // v4.0 — WAIT_HTF/WAIT_SETUP/WAIT_TRIGGER restore across same-session reinit
   datetime               m_cooldownEnd;
   datetime               m_tradeOpenTime;
   // v3.14.6 Fix 9 — running sum of realized P&L from TP1 partial(s) on
   // the CURRENT open trade. Reset to 0 on new entry; drained into the
   // final RecordClosedTrade() profit figure, then reset again.
   double                 m_partialProfitAccum;
   // v3.14.7 Fix 10 — ticket of the partial deal already claimed by
   // CASE_PartialTP for the CURRENT open trade. RecordClosedTrade()'s
   // backward deal scan must skip this ticket so it can never re-attribute
   // the partial deal as if it were the final close (see Fix 10 note at
   // the scan site). Reset alongside m_partialProfitAccum.
   ulong                  m_partialTicketSeen;
   bool                   m_htfBarReset;      // true = force H4 re-eval on next ProcessHTF()
   bool                   m_wasOffSession;     // v3.4.7: throttle off-session journal prints
   // Fix (2026-08-30): true only when THIS process opened the currently
   // managed position (m_ctx.tradeSetup is real, StartTracking() was
   // called). Defaults false — fail-closed — so a position discovered
   // already-open via ProcessIdle()'s HasOpenPosition() reroute (restart
   // / tick-gap reconciliation, zero real SL/TP context) is never
   // mistaken for one this instance actually knows the levels for.
   bool                   m_positionSelfOpened;
   datetime               m_cooldownLastBeat;
   int                    m_biasBlockCycles;   // v3.4.9: counts completed bias gate cooldown cycles

   // v3.11.0 — Daily pipeline reset state (Fix 2)
   datetime               m_lastDailyReset;    // last midnight UTC reset executed
   bool                   m_pendingDailyReset; // true = reset deferred (trade was open at midnight)

   // v3.12.1 Fix 3: guard against triple-logging the same deal.
   // When a SL/TP fires, the backtester delivers several ticks at the same
   // timestamp. Each tick enters ProcessManagement() (VPS bypass is active
   // while managing). All ticks see HasOpenPosition()=false and call
   // RecordClosedTrade(). Without this guard every trade is logged 3×.
   ulong                  m_lastLoggedTicket;

   // v3.12.3: DirectionGate removed. m_dgateRetryPending retained as stub (always false).
   bool                   m_dgateRetryPending;

   // v3.14.0 — Active regime profile (loaded in ProcessHTF after regime gate).
   // All downstream engines read tuneable parameters from m_profile rather than
   // global Inp* values. Defaults match v3.13.0 global inputs exactly so
   // behaviour is unchanged until per-regime values are consciously tuned.

   // v3.14.2 Fix 4 — Off-Session bias staleness guard.
   // Tracks the calendar date (UTC) of the last successful H1 regime
   // evaluation so ProcessIdle() can detect when we are in Off-Session
   // before any H1 bar has been evaluated on the current day.
   datetime               m_lastH1EvalDate;    // UTC date of last H1 regime eval
   RegimeProfile          m_profile;

   // v3.4.9 fix (Fix 3): Entry context snapshot.
   // Captured at the moment the order is confirmed open. Used exclusively
   // by RecordClosedTrade() so mid-manage context corruption (ATR=0 glitch,
   // regime reclassification) cannot corrupt the TRADE row values.
   double                 m_snapRR;            // tradeSetup.rr at entry
   double                 m_snapScore;         // scoreCard.total at entry
   double                 m_snapATR;           // regimeAtEntry.atr at entry
   string                 m_snapRegime;        // regime name at entry
   string                 m_snapSession;       // sessionAtEntry at entry
   string                 m_snapDirection;     // direction string at entry

   // Infrastructure
   CASE_Diagnostics              m_diag;
   CASE_Telemetry                m_tel;
   CASE_AlertEngine              m_alert;   // v3.8.0 — WF degradation + DD alerts
   CASE_VPSOptimizer             m_vps;

   // Gate engines
   CASE_SessionEngine            m_session;
   CASE_NewsEngine               m_news;
   CASE_ValidationEngine         m_valid;
   CASE_RegimeEngine             m_regime;
   CASE_PositionClusterProtection m_cluster;
   CASE_BrokerNormalization      m_norm;

   // Signal pipeline
   // v3.6.0 — m_bias (CASE_BiasEngine) removed. Replaced by m_structure (H1 BOS).
   CASE_StructureEngine          m_structure;
   CASE_SetupEngine              m_setup;
   CASE_TriggerEngine            m_trigger;
   CASE_LiquidityEngine          m_liq;
   // v3.12.3: m_dgate (CASE_DirectionGate) removed — direction from H1 BOS + pullback filter
   CASE_ScoringEngine            m_score;

   // Execution
   CASE_RiskEngine               m_risk;
   CASE_ExecutionEngine          m_exec;
   CASE_TradeManager             m_mgr;
   CASE_ChartVisuals             m_tradeVis;   // v3.14.17 Fix 24 — active-trade panel (separate instance from the one CASE_StructureEngine owns for BOS/SR; disjoint object names, no collision)

   // Optimisation
   CASE_OptimizerBridge          m_optBridge;
   CASE_WalkForwardEngine        m_wf;
   CASE_MonteCarlo               m_mc;

   // Reporting
   CASE_HTMLReporter             m_html;
   CASE_TradeExporter            m_csv;

   // Calibration state logger
   CASE_StateLogger              m_stateLog;

   // v4.0 — Trade attribution engine
   CASE_TradeAttribution         m_attr;

   // v4.0 — Evidence/Confluence/Classifier/Adaptive execution architecture.
   CASE_SetupEvidenceCollector    m_v4Evidence;
   CASE_ConfluenceEngine          m_v4Confluence;
   CASE_SetupClassifier           m_v4Classifier;
   CASE_SetupAnalytics            m_v4Analytics;
   CASE_AdaptiveEngine             m_v4Adaptive;
   CASE_DisciplineEngine            m_v4Discipline;
   CASE_Orchestrator               m_v4Orchestrator;
   CASE_V4Dashboard                m_v4Dashboard;
   AdaptiveDecision                m_v4AdaptiveDecision;
   bool                            m_v4ShadowAEligible;
   bool                            m_v4ShadowBEligible;
   bool                            m_v4OpportunityOpen;
   bool                            m_v4ExecutedByV4;
   bool                            m_v4ExecutionAttempt;
   ConfluenceResult                m_v4LastConfluence;
   string                          m_v4LastOpportunityId;
   // v4.0.2 -- entry snapshot taken on Execute success; RecordClosedTrade
   // attributes from this, not from the live (since-overwritten) V4 fields.
   string                          m_v4EntryOppId;
   ConfluenceResult                m_v4EntryConf;
   int                             m_v4EntryRegime;
   bool                            m_v4EntryHasLiq;
   bool                            m_v4EntryValid;
   double                          m_lastClosedRealisedR;   // v4.0.2 -- realised R of the most recent closed trade (0 if risk unknown)
   datetime                        m_v4LastSaveBar;         // v4.0.2 -- M15 bar of last periodic V4 state save
   uint                            m_v4EvidenceTick;
   uint                            m_v4ConfluenceTick;
   uint                            m_v4ExecutionTick;

   // v4.0.2 Phase 1 -- oppId-keyed join buffer for the comparison
   // ledger's "both" cell. Lives here (not on CASE_SetupAnalytics)
   // because it needs to be written from BOTH the M15 resolution loop
   // (Update()) and RecordClosedTrade() -- both already live on
   // CASE_StateMachine, so a small in-memory join here avoids inventing
   // a new class or passing state back and forth between two others
   // just for a 40-slot lookup table. Empty slot == m_pendingCompareOppId[i]=="".
   string   m_pendingCompareOppId[ASE_MAX_PENDING_COMPARE];
   string   m_pendingCompareArch[ASE_MAX_PENDING_COMPARE];
   string   m_pendingCompareRegime[ASE_MAX_PENDING_COMPARE];
   double   m_pendingCompareR[ASE_MAX_PENDING_COMPARE];
   datetime m_pendingCompareStamp[ASE_MAX_PENDING_COMPARE];

public:
   CASE_StateMachine() : m_state(STATE_IDLE), m_cooldownEnd(0), m_cooldownLastBeat(0), m_tradeOpenTime(0), m_partialProfitAccum(0.0), m_partialTicketSeen(0), m_htfBarReset(false), m_wasOffSession(false), m_positionSelfOpened(false), m_biasBlockCycles(0),
                    m_snapRR(0.0), m_snapScore(0.0), m_snapATR(0.0),
                    m_lastDailyReset(0), m_pendingDailyReset(false), m_dgateRetryPending(false),
                    m_lastLoggedTicket(0), m_lastH1EvalDate(0), m_v4LastOpportunityId(""), m_v4EntryOppId(""), m_v4EntryRegime(0), m_v4EntryHasLiq(false), m_v4EntryValid(false), m_lastClosedRealisedR(0.0), m_v4LastSaveBar(0), m_v4EvidenceTick(0), m_v4ConfluenceTick(0), m_v4ExecutionTick(0), m_v4ShadowAEligible(false), m_v4ShadowBEligible(false), m_v4OpportunityOpen(false), m_v4ExecutedByV4(false), m_v4ExecutionAttempt(false)
   {
      // v3.14.0 — initialise profile to safe defaults at construction so
      // any accidental read before first H1 bar doesn't use garbage values.
      ZeroMemory(m_profile);
      m_profile = LoadProfile(REGIME_COMPRESSION);  // conservative baseline
      m_v4EntryConf.Clear();   // v4.0.2
   }

   //─────────────────────────────────────────────────────────────────
   bool Initialize(int deinitReason = 0)
   {
      Print("[ASE] StateMachine::Initialize() — start | Symbol=", _Symbol,
            " | Server=", TimeCurrent());

      m_diag.Initialize();
      m_tel.Initialize();
      m_optBridge.Initialize();
      m_vps.Initialize();   // FIX #1 — must init before Update() uses it
      m_ctx.Reset();
      m_state = STATE_IDLE;
      m_ctxStatePath = StringFormat("ASE_StateLogs\\%s_%s_context.csv", ASE_VERSION_TAG, _Symbol);
      RestoreContextSnapshot(deinitReason);   // overwrites the two lines above only on a genuine restore

      if(!m_regime.Initialize())    { Print("[ASE] RegimeEngine  init failed"); return false; }
      // v3.6.0 — m_bias.Initialize() removed (BiasEngine retired)
      if(!m_setup.Initialize())     { Print("[ASE] SetupEngine   init failed"); return false; }
      if(!m_trigger.Initialize())   { Print("[ASE] TriggerEngine init failed"); return false; }
      if(!m_liq.Initialize())       { Print("[ASE] LiquidityEng  init failed"); return false; }
      if(!m_structure.Initialize()) { Print("[ASE] StructureEng  init failed"); return false; }
      // v3.12.3: m_dgate removed
      m_wf.Initialize();
      m_mc.Initialize();
      if(!m_risk.Initialize())      { Print("[ASE] RiskEngine    init failed"); return false; }
      if(!m_exec.Initialize())      { return false; }
      if(!m_mgr.Initialize())       { Print("[ASE] TradeManager  init failed"); return false; }
      m_tradeVis.Initialize(ASE_VERSION_TAG);

      // v3.4.4 — print effective session windows on startup so misconfigured
      // UTC times are caught immediately in the Experts tab before trading begins.
      m_session.PrintConfig();

      // v3.14.11 Fix 16: every output filename now derives from
      // ASE_VERSION_TAG (Models/ASE_Config.mqh) instead of a hardcoded
      // literal, so different builds never collide on the same file.
      m_csv.Open(ASE_VERSION_TAG + "_trades.csv");
      m_stateLog.Initialize(_Symbol, PERIOD_CURRENT, ASE_VERSION_TAG);

      // v4.0 — attribution engine
      if(!m_attr.Initialize())
      {
         Print("[ASE] TradeAttribution init failed — exports will be unavailable");
         // Non-fatal: EA continues without the three attribution output files
      }

      // v4.0 — evidence/confluence/classifier/adaptive scaffolding.
      // Non-fatal if it can't open its log file, same as m_attr above —
      // the EA continues trading exactly as it would with InpAceV4Mode
      // set to ACEV4_LEGACY either way.
      if(InpAceV4Mode >= ACEV4_EVIDENCE)
         m_v4Analytics.Initialize(ASE_VERSION_TAG);
      if(InpAceV4Mode >= ACEV4_EVIDENCE)
      {
         m_v4Adaptive.Initialize(ASE_VERSION_TAG);
         m_v4Dashboard.Initialize();
      }

      // v4.0.2 amendment -- one-time learning-state migration. Gated on:
      // (a) a source tag actually configured, (b) BOTH v4 engines just
      // initialized fresh (no state file of their own yet) -- so a
      // restart of the SAME version never re-imports, only the genuine
      // first run of a NEW version does. Runs only when both engines
      // were initialized above (InpAceV4Mode >= ACEV4_EVIDENCE).
      if(InpAceV4Mode >= ACEV4_EVIDENCE && InpAceV4MigrateFromTag != ""
         && !m_v4Adaptive.HadExistingState() && !m_v4Analytics.HadExistingState())
      {
         CASE_LearningMigrator migrator;
         LearningMigrationResult migResult = migrator.Migrate(m_v4Adaptive, m_v4Analytics, InpAceV4MigrateFromTag);
         if(migResult.success)
            Print("[ASE] Learning-state migration SUCCEEDED from '", InpAceV4MigrateFromTag, "':\n  ", migResult.reason);
         else
            Print("[ASE] Learning-state migration REFUSED from '", InpAceV4MigrateFromTag, "':\n  ", migResult.reason);
         m_v4Adaptive.LogMigrationResult(migResult.success, migResult.reason, InpAceV4MigrateFromTag);
         m_v4Analytics.LogMigrationResult(migResult.success, migResult.reason, InpAceV4MigrateFromTag);
      }
      else if(InpAceV4Mode >= ACEV4_EVIDENCE && InpAceV4MigrateFromTag != "")
      {
         Print("[ASE] Learning-state migration SKIPPED -- current version already has its own state file (not a fresh run).");
      }

      // v4.0.2 Phase 1 -- explicit clear of the comparison join buffer.
      // Not persisted across restarts by design: it is a short-lived
      // in-memory join for two events that should both occur within
      // ASE_COMPARE_JOIN_TIMEOUT_SECONDS of each other, not learning state.
      for(int i = 0; i < ASE_MAX_PENDING_COMPARE; i++) ClearCompareSlot(i);

      Print("[ASE] StateMachine::Initialize() — complete");
      return true;
   }

   //─────────────────────────────────────────────────────────────────
   void Deinitialize(int reason = 0)
   {
      SaveContextSnapshot(reason);

      m_regime.Deinitialize();
      // v3.6.0 — m_bias.Deinitialize() removed (BiasEngine retired)
      m_setup.Deinitialize();
      m_trigger.Deinitialize();
      m_risk.Deinitialize();
      m_mgr.Deinitialize();
      m_tradeVis.Deinitialize();
      m_structure.Deinitialize();
      // v3.12.3: m_dgate removed

      m_wf.BuildWindows();
      m_wf.PrintReport();
      m_tel.PrintSummary();
      m_exec.PrintSummary();   // v4.0 — execution telemetry summary
      m_html.Export(ASE_VERSION_TAG + "_report.html", m_tel, m_wf);   // v3.14.11 Fix 16
      m_csv.Close();
      m_stateLog.Deinitialize();
      m_attr.Deinitialize();   // v4.0 — flush and close attribution streams

      if(InpAceV4Mode >= ACEV4_EVIDENCE)
      {
         m_v4Analytics.PrintSummary();
         m_v4Analytics.Deinitialize();
         m_v4Adaptive.Deinitialize();
         m_v4Dashboard.Clear();
      }
   }

   //─────────────────────────────────────────────────────────────────
   // v4.0 — pre-position context persistence (WAIT_HTF/WAIT_SETUP/
   // WAIT_TRIGGER only). An open position never needs this — it's
   // already rediscovered from the broker via magic-number scan on
   // every Initialize() regardless of internal state. What has no
   // recovery path otherwise is the H1-bias-forming / M15-setup-
   // waiting / M1-trigger-waiting states, which live only in m_state
   // and m_ctx — a chart period/symbol change or an input edit tears
   // both down and rebuilds from STATE_IDLE with no hint anything was
   // in progress.
   //
   // Deliberately NOT restored: STATE_WAIT_EXECUTION (an order is
   // actively being placed — too narrow and ambiguous a window to
   // safely resume; falls back to re-evaluation from STATE_IDLE, same
   // as today) and STATE_POSITION_OPEN/STATE_MANAGE (already covered
   // by the existing broker-scan recovery — restoring m_ctx for these
   // too would be redundant, not additive).
   //
   // Known residual gap, stated rather than silently ignored: several
   // Process*() methods gate on function-local `static` bar-throttle
   // variables (e.g. the M15 heartbeat stamps) which MQL5 always resets
   // to their initial value on any reinit, restored or not — this
   // snapshot does not and cannot reach into another method's local
   // statics. Worst case on a restored bar, a Process*() call that
   // would have been throttled fires one extra time on the same bar it
   // already ran on — re-evaluates current data, not destructive, just
   // a duplicate log line at most.
   //─────────────────────────────────────────────────────────────────
   void SaveContextSnapshot(int reason)
   {
      bool restorable = (m_state == STATE_WAIT_HTF || m_state == STATE_WAIT_SETUP || m_state == STATE_WAIT_TRIGGER);
      int h = FileOpen(m_ctxStatePath, FILE_WRITE | FILE_CSV | FILE_COMMON, ',');
      if(h == INVALID_HANDLE)
      {
         Print("[ASE] WARNING — could not save context snapshot to ", m_ctxStatePath, " | Error: ", GetLastError());
         return;
      }
      if(!restorable)
      {
         // Explicitly write an empty/non-restorable marker rather than
         // leaving a prior restorable snapshot on disk — otherwise a
         // later reinit from STATE_IDLE could wrongly resurrect
         // whatever WAIT_* state existed several trades ago.
         FileWrite(h, "STATE", (int)STATE_IDLE, reason, (long)0);
         FileClose(h);
         return;
      }

      datetime m15Bar = iTime(_Symbol, PERIOD_M15, 0);
      datetime h1Bar  = iTime(_Symbol, PERIOD_H1, 0);
      datetime h4Bar  = iTime(_Symbol, PERIOD_H4, 0);

      FileWrite(h, "STATE", (int)m_state, reason, (long)m15Bar);
      FileWrite(h, "BARS", (long)m15Bar, (long)h1Bar, (long)h4Bar);
      FileWrite(h, "CTX_CORE", (int)m_ctx.direction, m_ctx.sessionAtEntry, m_ctx.liquidityType,
                m_ctx.m15SetupClass, m_ctx.m1TriggerClass, (long)m_ctx.entryTime,
                DoubleToString(m_ctx.entrySpreadPts,2), m_ctx.execLatencyMs,
                DoubleToString(m_ctx.triggerClosePrice,5), DoubleToString(m_ctx.triggerM1ATR,5),
                m_ctx.isCountertrendShortException ? 1 : 0);
      FileWrite(h, "CTX_SCORE", DoubleToString(m_ctx.scoreCard.h4Bias,4), DoubleToString(m_ctx.scoreCard.m15Setup,4),
                DoubleToString(m_ctx.scoreCard.m1Trigger,4), DoubleToString(m_ctx.scoreCard.liquidity,4),
                DoubleToString(m_ctx.scoreCard.volatility,4), DoubleToString(m_ctx.scoreCard.session,4),
                DoubleToString(m_ctx.scoreCard.spread,4), DoubleToString(m_ctx.scoreCard.total,4));
      FileWrite(h, "CTX_REGIME", (int)m_ctx.regimeAtEntry.regime, DoubleToString(m_ctx.regimeAtEntry.atr,5),
                DoubleToString(m_ctx.regimeAtEntry.trendSlope,5), DoubleToString(m_ctx.regimeAtEntry.volatilityRank,4),
                DoubleToString(m_ctx.regimeAtEntry.wickRatio,4), DoubleToString(m_ctx.regimeAtEntry.adrExpansion,4),
                (int)m_ctx.regimeAtEntry.macroRegime, DoubleToString(m_ctx.regimeAtEntry.h4EMASep,5),
                DoubleToString(m_ctx.regimeAtEntry.h4ATR,5));
      FileWrite(h, "CTX_LEVELS", DoubleToString(m_ctx.structLevels.tp1,5), DoubleToString(m_ctx.structLevels.tp2,5),
                m_ctx.structLevels.tp1Valid ? 1 : 0, m_ctx.structLevels.tp2Valid ? 1 : 0, m_ctx.structLevels.source);
      FileClose(h);
      Print(StringFormat("[ASE] Context snapshot saved | state=%d reason=%d m15Bar=%s",
            (int)m_state, reason, TimeToString(m15Bar, TIME_DATE|TIME_MINUTES)));
   }

   void RestoreContextSnapshot(int deinitReason)
   {
      // Only a same-session, automatic reinit is safe to resume exactly
      // as-is. A genuine restart (terminal close/reopen, account
      // switch, template load, or first-ever attach) falls through to
      // the existing clean-slate behaviour — deliberately, not an
      // oversight: resuming "waiting for an M15 trigger on a LONG H1
      // bias" after an unknown gap could mean acting on a bias that's
      // since gone stale.
      bool safeReason = (deinitReason == REASON_CHARTCHANGE || deinitReason == REASON_PARAMETERS ||
                          deinitReason == REASON_RECOMPILE);
      if(!safeReason) return;
      if(!FileIsExist(m_ctxStatePath, FILE_COMMON)) return;

      int h = FileOpen(m_ctxStatePath, FILE_READ | FILE_CSV | FILE_COMMON | FILE_SHARE_READ, ',');
      if(h == INVALID_HANDLE) return;

      ENUM_ASE_STATE savedState = STATE_IDLE;
      long savedM15Bar = 0;
      int savedReason = 0;
      ASE_PipelineContext restored; restored.Reset();
      bool haveCore = false, haveScore = false, haveRegime = false, haveLevels = false;

      while(!FileIsEnding(h))
      {
         string tag = FileReadString(h);
         if(tag == "") break;
         if(tag == "STATE")
         {
            savedState = (ENUM_ASE_STATE)(int)FileReadNumber(h);
            savedReason = (int)FileReadNumber(h);
            savedM15Bar = (long)FileReadNumber(h);
         }
         else if(tag == "BARS")
         { FileReadNumber(h); FileReadNumber(h); FileReadNumber(h); }   // h1Bar/h4Bar not currently compared — reserved
         else if(tag == "CTX_CORE")
         {
            restored.direction = (ENUM_TRADE_DIRECTION)(int)FileReadNumber(h);
            restored.sessionAtEntry = FileReadString(h);
            restored.liquidityType  = FileReadString(h);
            restored.m15SetupClass  = FileReadString(h);
            restored.m1TriggerClass = FileReadString(h);
            restored.entryTime      = (datetime)FileReadNumber(h);
            restored.entrySpreadPts = FileReadNumber(h);
            restored.execLatencyMs  = (int)FileReadNumber(h);
            restored.triggerClosePrice = FileReadNumber(h);
            restored.triggerM1ATR      = FileReadNumber(h);
            restored.isCountertrendShortException = ((int)FileReadNumber(h)) != 0;
            haveCore = true;
         }
         else if(tag == "CTX_SCORE")
         {
            restored.scoreCard.h4Bias = FileReadNumber(h); restored.scoreCard.m15Setup = FileReadNumber(h);
            restored.scoreCard.m1Trigger = FileReadNumber(h); restored.scoreCard.liquidity = FileReadNumber(h);
            restored.scoreCard.volatility = FileReadNumber(h); restored.scoreCard.session = FileReadNumber(h);
            restored.scoreCard.spread = FileReadNumber(h); restored.scoreCard.total = FileReadNumber(h);
            haveScore = true;
         }
         else if(tag == "CTX_REGIME")
         {
            restored.regimeAtEntry.regime = (ENUM_MARKET_REGIME)(int)FileReadNumber(h);
            restored.regimeAtEntry.atr = FileReadNumber(h); restored.regimeAtEntry.trendSlope = FileReadNumber(h);
            restored.regimeAtEntry.volatilityRank = FileReadNumber(h); restored.regimeAtEntry.wickRatio = FileReadNumber(h);
            restored.regimeAtEntry.adrExpansion = FileReadNumber(h);
            restored.regimeAtEntry.macroRegime = (ENUM_MACRO_REGIME)(int)FileReadNumber(h);
            restored.regimeAtEntry.h4EMASep = FileReadNumber(h); restored.regimeAtEntry.h4ATR = FileReadNumber(h);
            haveRegime = true;
         }
         else if(tag == "CTX_LEVELS")
         {
            restored.structLevels.tp1 = FileReadNumber(h); restored.structLevels.tp2 = FileReadNumber(h);
            restored.structLevels.tp1Valid = ((int)FileReadNumber(h)) != 0;
            restored.structLevels.tp2Valid = ((int)FileReadNumber(h)) != 0;
            restored.structLevels.source = FileReadString(h);
            haveLevels = true;
         }
      }
      FileClose(h);

      if(savedState != STATE_WAIT_HTF && savedState != STATE_WAIT_SETUP && savedState != STATE_WAIT_TRIGGER) return;
      if(!haveCore || !haveScore || !haveRegime || !haveLevels) return;   // partial/corrupt write — don't half-restore

      // Bar-staleness check — a same-session bounce lands on the same
      // M15 bar essentially always; if it doesn't, the market has moved
      // on since the snapshot and resuming would be acting on outdated
      // structure rather than genuinely continuing the same evaluation.
      datetime currentM15Bar = iTime(_Symbol, PERIOD_M15, 0);
      if((long)currentM15Bar != savedM15Bar)
      {
         Print(StringFormat("[ASE] Context snapshot found but stale (saved bar=%s, current bar=%s) — starting clean instead of resuming %d",
               TimeToString((datetime)savedM15Bar, TIME_DATE|TIME_MINUTES),
               TimeToString(currentM15Bar, TIME_DATE|TIME_MINUTES), (int)savedState));
         return;
      }

      m_state = savedState;
      m_ctx   = restored;
      Print(StringFormat("[ASE] Context RESTORED | state=%d (was reason=%d) | direction=%s | m15SetupClass=%s | m1TriggerClass=%s",
            (int)savedState, savedReason,
            (restored.direction == DIR_LONG ? "LONG" : restored.direction == DIR_SHORT ? "SHORT" : "NONE"),
            restored.m15SetupClass, restored.m1TriggerClass));
   }

   //─────────────────────────────────────────────────────────────────
   void Update()
   {
      // FIX #2 — UpdatePeak() must run every tick regardless of throttle
      // so peak equity tracking is always current for DD calculations.
      m_risk.UpdatePeak();

      // v3.4.1 fix — keep sessionAtEntry current on every tick so that
      // every StateLogger row (BLOCK, TRANSITION, TRIGGER_EVAL) carries
      // the correct session name. Previously this field was only written
      // at trade execution (ProcessExecution) causing all non-trade rows
      // to log an empty Session column.
      m_ctx.sessionAtEntry = m_session.GetSessionName();

      // v4.0 — maintain rolling spread average for volatility cluster detection.
      // Called every tick so the EMA sample rate matches market activity.
      m_attr.UpdateSpread();

      // v4.0 — execution engine maintains its own independent spread EMA
      // used exclusively for pre-send shock rejection.
      m_exec.UpdateSpread();

      // v4.0.2 -- periodic V4 state save once per new M15 bar (was only on
      // Deinitialize, so a crash/kill lost all learning since attach).
      // Placed before the tick throttle so it runs in every state.
      if(InpAceV4Mode >= ACEV4_EVIDENCE)
      {
         datetime saveBar = iTime(_Symbol, PERIOD_M15, 0);
         if(saveBar > 0 && saveBar != m_v4LastSaveBar)
         {
            m_v4LastSaveBar = saveBar;
            m_v4Adaptive.SaveState();
            m_v4Analytics.SaveState();
            // v4.0.2 Phase 1 -- surface the V4-vs-legacy comparison report
            // once per M15 bar alongside the periodic save. No dedicated
            // dashboard slot exists for it (CASE_V4Dashboard's 16 chart
            // labels are already all in use -- see that file), so Print()
            // is the reporting surface for now, gated the same way as the
            // rest of the V4 pipeline.
            Print(m_v4Analytics.BuildComparisonReport());
         }
      }

      // FIX #1 — VPS tick throttle: skip full pipeline evaluation if
      // nothing changed on M1. Bypass during position management so
      // SL/TP closes (which happen mid-bar in the tester and live) are
      // detected on the very next tick rather than at the next M1 bar open.
      bool managing = (m_state == STATE_MANAGE);
      if(!managing && !m_vps.ShouldProcess() && !(InpAceV4Mode >= ACEV4_ADVISORY && m_state == STATE_WAIT_TRIGGER)) return;

      // v3.11.0 — Daily pipeline reset (Fix 2).
      // Runs once per day at InpDailyResetHour UTC. If no position is open,
      // the DirectionGate state is cleared and the pipeline returns to IDLE
      // so the new trading day starts with a fresh directional evaluation.
      // H1 swing levels and BOS staleness tracking are preserved.
      // If a trade is open at reset time, m_pendingDailyReset is set and
      // the reset fires at the end of the subsequent cooldown instead.
      CheckDailyReset();

      // v3.11.0 — DirectionGate DIR_NONE retry (Fix 5).
      // When the gate has been stuck at DIR_NONE for InpDGRetryBars M15 bars,
      // ForceRetry() returns true. Flag is consumed in ProcessIdle() to
      // immediately transition to STATE_WAIT_HTF for a fresh evaluation.
      if(m_state == STATE_IDLE && !m_dgateRetryPending)
         m_dgateRetryPending = false; // v3.12.3: DGate removed

      switch(m_state)
      {
         case STATE_IDLE:           ProcessIdle();       break;
         case STATE_WAIT_HTF:       ProcessHTF();        break;
         case STATE_WAIT_SETUP:     ProcessSetup();      break;
         case STATE_WAIT_TRIGGER:   ProcessTrigger();    break;
         case STATE_WAIT_EXECUTION: ProcessExecution();  break;
         // FIX #9 — STATE_POSITION_OPEN is removed as a distinct state.
         // ProcessIdle() and ProcessManagement() both route to STATE_MANAGE.
         // The case is left here as a safety net only (should never fire).
         case STATE_POSITION_OPEN:  Transition(STATE_MANAGE); break;
         case STATE_MANAGE:         ProcessManagement(); break;
         case STATE_COOLDOWN:       ProcessCooldown();   break;
      }
   }

   //─────────────────────────────────────────────────────────────────
   // FIX #5 — ScanUpcomingNews() wired to MQL5 calendar API.
   // Scans next 48h of high-impact events on startup so the first
   // session is protected before OnCalendarEvent() fires live events.
   void ScanUpcomingNews()
   {
      MqlCalendarValue values[];
      datetime now    = TimeCurrent();
      datetime window = now + 172800;   // 48 hours

      int count = CalendarValueHistory(values, now, window, NULL, NULL);
      if(count <= 0)
      {
         Print("[NEWS] ScanUpcomingNews: no events in next 48h (or calendar unavailable)");
         return;
      }

      int registered = 0;
      for(int i = 0; i < count; i++)
      {
         if(values[i].impact_type == CALENDAR_IMPACT_HIGH && values[i].time > now)
         {
            m_news.SetNextEvent(values[i].time);
            registered++;
         }
      }
      Print("[NEWS] ScanUpcomingNews: scanned ", count, " events, registered ",
            registered, " high-impact events in next 48h");
   }

   void NotifyNewsEvent(datetime time)
   {
      m_news.SetNextEvent(time);
      Print("[NEWS] Event registered: ", TimeToString(time, TIME_DATE|TIME_MINUTES));
   }

   bool IsInSession() { return m_session.IsTradingSession(); }

   double GetFitnessScore()
   {
      m_wf.BuildWindows();
      return m_optBridge.CalculateFitness(
         m_tel.GetWinRate(),
         m_tel.GetAverageRR(),
         m_tel.GetTradeCount(),
         m_tel.GetMaxDrawdownPct(),
         m_tel.GetProfitFactor(),
         m_wf.GetOOSRetention()
      );
   }

private:
   //─────────────────────────────────────────────────────────────────
   void Transition(ENUM_ASE_STATE next)
   {
      // v3.4.5 fix (Issue 2): STATE_IDLE resets m_ctx on the next
      // ProcessIdle() pass — if a position is already open (e.g. opened
      // by a leaked execution, or an ATR=0 glitch fired mid-manage),
      // any Transition(STATE_IDLE) would blank the trade context, making
      // RecordClosedTrade() unable to resolve exit reason, RR, or scorecard.
      // Observed on 2026-06-03: ATR=0 at 16:22 forced STATE_IDLE while
      // Trade 2 was live — TRADE row showed rr=0.00, Score=0, ATR=0.
      // Fix: intercept STATE_IDLE when position is open and route to
      // STATE_MANAGE. Log the override so it is visible in Experts tab.
      if(next == STATE_IDLE && HasOpenPosition())
      {
         Print(StringFormat("[ASE] Transition guard: %s → STATE_IDLE blocked (position open) → STATE_MANAGE",
               EnumToString(m_state)));
         next = STATE_MANAGE;
      }

      // v3.4.7 — cosmetic: clear scoreCard.total on STATE_IDLE transitions
      // (position not open) so TRANSITION rows in the CSV don't carry the
      // previous cycle's score. Harmless — score is recomputed at TRIGGER_EVAL.
      if(next == STATE_IDLE && !HasOpenPosition())
         m_ctx.scoreCard.total = 0.0;

      if(next == m_state) return;
      Print(StringFormat("[ASE] State: %s → %s",
            EnumToString(m_state), EnumToString(next)));
      m_stateLog.LogTransition(m_state, next, m_ctx,
                                CASE_Broker::GetSpread(),
                                m_ctx.regimeAtEntry.atr);
      m_diag.LogState(EnumToString(next));
      m_state = next;

      // When returning to WAIT_HTF after a downstream failure (setup/trigger
      // rejected), force H4 to re-evaluate on the very next ProcessHTF() call
      // rather than waiting hours for the next H4 bar to open.
      // The M15 throttle inside ProcessSetup() prevents setup from re-running
      // on the same bar, providing the natural rate limit.
      if(next == STATE_WAIT_HTF)
         m_htfBarReset = true;
   }

   //─────────────────────────────────────────────────────────────────
   // LogBlock — records a gate rejection to the state log CSV and,
   // once per M15 bar, also prints to the MT5 journal so blocking
   // reasons are visible in the Experts tab.
   // Throttle prevents journal flooding at M1 frequency (60 prints/h)
   // while still giving one visible line per 15-minute window.
   //─────────────────────────────────────────────────────────────────
   void LogBlock(string stage, string reason)
   {
      // Throttle: print to journal at most once per M15 bar
      static datetime _lastBlockBar = 0;
      static string   _lastBlockReason = "";
      datetime curM15 = iTime(_Symbol, PERIOD_M15, 0);
      if(curM15 != _lastBlockBar || reason != _lastBlockReason)
      {
         Print(StringFormat("[ASE][%s] Blocked: %s", stage, reason));
         _lastBlockBar    = curM15;
         _lastBlockReason = reason;
      }

      m_diag.LogBlock(stage, reason);
      m_stateLog.LogBlock(stage, reason, m_ctx,
                           CASE_Broker::GetSpread(),
                           m_ctx.regimeAtEntry.atr);
   }

   //─────────────────────────────────────────────────────────────────
   void ProcessIdle()
   {
      // v3.12.9: terminal halt check — fires before all other gates.
      // When recovery mode is active and either the session target has been
      // reached (Phase 3a) or the secondary halt has fired (Phase 3b),
      // block all trading and log to Experts tab until EA is reloaded.
      if(InpDDRecoveryMode && m_risk.IsTerminalHalt())
      {
         string haltReason = m_risk.GetTerminalHaltReason();
         static string s_lastHaltReason = "";
         if(haltReason != s_lastHaltReason)
         {
            Print("[ASE][IDLE] ", haltReason);
            LogBlock("DD_RECOVERY", haltReason);
            s_lastHaltReason = haltReason;
         }
         return;   // No trading — pipeline completely blocked until reload
      }
      // ── v4.0 Per-bar heartbeat ────────────────────────────────────
      // Prints one diagnostic line per M15 bar so the pipeline is
      // visible in the Experts tab even when nothing trades.
      // v3.13.0: uses cached m_ctx.regimeAtEntry instead of calling
      // GetState() (which copies 8 indicator buffers) — zero cost.
      // Guard: only use cache when atr > 0 (i.e. regime has been
      // evaluated at least once since EA load). Before first H1 bar
      // evaluation regimeAtEntry is zeroed (REGIME_UNKNOWN).
      {
         static datetime _lastHeartbeatBar = 0;
         datetime hbBar = iTime(_Symbol, PERIOD_M15, 0);
         if(hbBar != _lastHeartbeatBar)
         {
            _lastHeartbeatBar = hbBar;
            string regimeLbl = (m_ctx.regimeAtEntry.atr > 0)
                             ? m_regime.RegimeName(m_ctx.regimeAtEntry.regime)
                             : "Initialising";
            string macroLbl  = (m_ctx.regimeAtEntry.macroRegime != MACRO_UNKNOWN)
                             ? m_regime.MacroRegimeName(m_ctx.regimeAtEntry.macroRegime)
                             : "--";
            Print(StringFormat(
               "[ASE] Heartbeat | State=IDLE | Bar=%s | Session=%s | "
               "Regime=%s | Macro=%s | Spread=%.1f | Score=-- | HasPos=%s",
               TimeToString(hbBar, TIME_DATE|TIME_MINUTES),
               m_session.GetSessionName(),
               regimeLbl,
               macroLbl,
               CASE_Broker::GetSpread(),
               HasOpenPosition() ? "YES" : "NO"));
         }
      }

      // v3.11.0 — Consume pending DGate retry (Fix 5).
      // ForceRetry() fired in Update() — immediately advance to HTF
      // evaluation without waiting for all idle preconditions to be met.
      // This catches opportunities that the pipeline missed while stuck at
      // DIR_NONE, particularly during transitions between market regimes.
      if(m_dgateRetryPending)
      {
         m_dgateRetryPending = false;
         // v3.12.3: m_dgate removed
         Print("[ASE][IDLE] DGate retry triggered — advancing to HTF evaluation");
         Transition(STATE_WAIT_HTF);
         return;
      }

      // FIX #9 — re-entry guard routes to STATE_MANAGE, not POSITION_OPEN
      // Fix (2026-08-30): position exists but this process didn't open it
      // (restart / tick-gap discovery) — m_ctx.tradeSetup has no real
      // levels for it. Flag so RecordClosedTrade() doesn't try to
      // classify its exit against zeroed SL/TP/entry.
      if(HasOpenPosition())
      {
         m_positionSelfOpened = false;
         Transition(STATE_MANAGE);
         return;
      }

      if(TimeCurrent() < m_cooldownEnd) { Transition(STATE_COOLDOWN); return; }

      if(!m_session.IsTradingSession())
      {
         // v3.4.7 — throttle off-session BLOCK logging to once per session
         // boundary crossing rather than once per M15 bar. Previously generated
         // ~73 rows per pre-session hour (08:47–09:59) inflating CSV file size.
         // Prints to Experts tab only on state change; CSV row still written
         // once per bar for audit continuity but journal suppressed.
         if(!m_wasOffSession)
         {
            Print("[ASE][IDLE] Outside session — ", m_session.GetSessionName(),
                  " | Waiting for London/NY open");
            m_wasOffSession = true;
         }
         m_stateLog.LogBlock("IDLE",
            "Outside session (" + m_session.GetSessionName() + ")",
            m_ctx, CASE_Broker::GetSpread(), m_ctx.regimeAtEntry.atr);
         return;
      }
      m_wasOffSession = false;   // reset when session is active

      if(m_news.IsNewsBlocked())
      {
         LogBlock("IDLE", "News block (" + IntegerToString(m_news.MinutesToEvent()) + " min)");
         return;
      }

      if(!m_valid.SpreadAcceptable(InpMaxSpread))
      {
         LogBlock("IDLE", StringFormat("Spread %.1f > %d",
                                        CASE_Broker::GetSpread(), InpMaxSpread));
         return;
      }

      if(!m_cluster.AllowNewTrade(InpMaxPositions))
      {
         LogBlock("IDLE", "Max positions reached");
         return;
      }

      // ── v3.14.2 Fix 4: Off-Session early-morning bias staleness guard ──
      // Block entries before the first H1 bar of the new UTC day has been
      // processed by ProcessHTF(). This prevents a direction bias set in the
      // prior session (e.g. from the previous day's London/NY close) from
      // carrying into the pre-London hours when H1 structure has not yet
      // been re-evaluated.
      //
      // Root cause observed in May–Jun 2026 live logs:
      //   May 26 02:10 — bias=NONE (prior day ended with no BOS), SHORT trade fired
      //   Jun 4  03:02 — bias carried from Jun 3 close, no H1 eval on Jun 4 yet
      //
      // Guard: if InpOffSessionBiasGuard=true AND the current session is Off-Session
      // AND the last H1 evaluation date is NOT today (UTC), block and wait.
      // The guard lifts automatically once the first H1 bar of the day fires
      // in ProcessHTF() and stamps m_lastH1EvalDate with today's date.
      if(InpOffSessionBiasGuard && !m_session.IsTradingSession())
      {
         MqlDateTime nowDt, evalDt;
         TimeToStruct(TimeCurrent(), nowDt);
         TimeToStruct(m_lastH1EvalDate, evalDt);

         bool h1EvalledToday = (nowDt.year  == evalDt.year &&
                                nowDt.mon   == evalDt.mon  &&
                                nowDt.day   == evalDt.day);

         if(!h1EvalledToday)
         {
            static datetime s_lastGuardLog = 0;
            if(TimeCurrent() - s_lastGuardLog >= 900)   // suppress repeat logs; 1 per 15 min
            {
               string guardReason = StringFormat(
                  "Off-Session bias guard: no H1 eval today (last=%s) — awaiting first H1 bar",
                  m_lastH1EvalDate > 0 ? TimeToString(m_lastH1EvalDate, TIME_DATE) : "never");
               Print("[ASE][IDLE] ", guardReason);
               LogBlock("IDLE", guardReason);
               s_lastGuardLog = TimeCurrent();
            }
            return;
         }
      }

      Transition(STATE_WAIT_HTF);
   }

   //─────────────────────────────────────────────────────────────────
   // FIX #7 — regime state captured once per H4 bar and reused in
   // ProcessTrigger() via m_ctx.regimeAtEntry, eliminating duplicate
   // GetState() calls from Detect() + GetState() + GetVolatilityScore().
   void ProcessHTF()
   {
      // v3.4.9 fix (Fix 1): ProcessHTF() must never run while a position
      // is open. When STATE_MANAGE routes here via an unexpected state
      // transition, m_ctx.regimeAtEntry.atr gets overwritten — either
      // with ATR=0 during an indicator warmup glitch, or with the new
      // H4 bar regime which may differ from the entry regime. Both
      // corrupt the context that RecordClosedTrade() relies on at close.
      // Observed 2026-06-05: 7 STATE_IDLE->STATE_MANAGE reroutes from
      // 16:27 to 16:59 all showed ATR=0/Regime=NaN in the TRADE row.
      if(HasOpenPosition())
      {
         Print("[ASE][HTF] Skipped — position open (context protection)");
         return;
      }

      // v3.13.0 — Split throttle: regime evaluates on H1 bar close (hourly);
      // structure evaluates on H4 bar close (every 4 hours, unchanged).
      // Both statics are cleared by m_htfBarReset so downstream failures
      // force a fresh evaluation on the next M15 bar for both engines.
      static datetime _lastRegimeBar    = 0;   // H1 throttle — regime only
      static datetime _lastStructureBar = 0;   // H4 throttle — structure only
      static datetime _lastHTFHBBar     = 0;   // M15 heartbeat (unchanged)

      datetime h1Bar = iTime(_Symbol, PERIOD_H1, 0);
      datetime h4Bar = iTime(_Symbol, PERIOD_H4, 0);

      // When returning from a downstream failure (setup/trigger rejected),
      // Transition() sets m_htfBarReset=true. Clear BOTH throttles so
      // both regime and structure re-evaluate immediately on the next M15 bar.
      if(m_htfBarReset)
      {
         _lastRegimeBar    = 0;
         _lastStructureBar = 0;
         m_htfBarReset     = false;
      }

      // Per-M15 heartbeat — now includes macro regime for diagnostics
      datetime hbBar = iTime(_Symbol, PERIOD_M15, 0);
      if(hbBar != _lastHTFHBBar)
      {
         _lastHTFHBBar = hbBar;
         Print(StringFormat("[ASE] Heartbeat | State=WAIT_HTF | Bar=%s | "
               "Direction=%s | Regime=%s | Macro=%s | Spread=%.1f",
               TimeToString(hbBar, TIME_DATE|TIME_MINUTES),
               (m_ctx.direction == DIR_LONG ? "LONG" :
                m_ctx.direction == DIR_SHORT ? "SHORT" : "NONE"),
               m_regime.RegimeName(m_ctx.regimeAtEntry.regime),
               m_regime.MacroRegimeName(m_ctx.regimeAtEntry.macroRegime),
               CASE_Broker::GetSpread()));
      }

      // v3.13.0 — Regime evaluation: once per H1 bar.
      // If neither H1 bar nor H4 bar has changed, hold STATE_WAIT_HTF
      // (v3.4.9 ping-pong fix preserved — now checks either bar advanced).
      bool newH1Bar = (h1Bar != _lastRegimeBar);
      bool newH4Bar = (h4Bar != _lastStructureBar);

      if(!newH1Bar && !newH4Bar)
      {
         if(m_state != STATE_WAIT_HTF) Transition(STATE_WAIT_HTF);
         return;
      }

      // ── Step A: Regime evaluation (H1 throttle) ──────────────────
      if(newH1Bar)
      {
         _lastRegimeBar = h1Bar;

         // Capture H1 regime state — cached in m_ctx.regimeAtEntry for
         // the full pipeline cycle until the next H1 bar evaluation.
         m_ctx.regimeAtEntry = m_regime.GetState();

         // v3.4.5 fix: ATR=0 on mid-session bar — skip and retry next H1 bar
         if(m_ctx.regimeAtEntry.atr < _Point && m_tradeOpenTime == 0)
         {
            Print(StringFormat("[ASE][HTF] ATR=0 on H1 bar %s — skipping regime eval (indicator warmup)",
                  TimeToString(h1Bar, TIME_DATE|TIME_MINUTES)));
            _lastRegimeBar = 0;   // allow retry on next tick
            return;
         }

         if(InpRegimeFilterEnabled)
         {
            if(m_ctx.regimeAtEntry.regime == REGIME_DEAD ||
               m_ctx.regimeAtEntry.regime == REGIME_HIGH_VOL)
            {
               LogBlock("HTF", "Regime blocked: " + m_regime.RegimeName(m_ctx.regimeAtEntry.regime)
                        + " | Macro=" + m_regime.MacroRegimeName(m_ctx.regimeAtEntry.macroRegime));
               Transition(STATE_IDLE);
               return;
            }
         }

         // v3.14.0 — Load regime profile.
         // Called after the hard-block gate so HIGH_VOL and DEAD never
         // reach LoadProfile(). Profile is valid for the entire pipeline
         // cycle until the next H1 bar re-evaluation.
         m_profile = LoadProfile(m_ctx.regimeAtEntry.regime);
         Print(StringFormat("[ASE][HTF] Profile loaded: %s | SL=%.1f× | ScoreMin=%.0f | Spread=%d | BiasConf=%d",
               m_profile.label, m_profile.slMultiplier,
               m_profile.minScoreThreshold, m_profile.maxSpread,
               m_profile.biasConfidenceMin));

         // v3.14.5 Fix 8: sync the logger's threshold cache so TRANSITION
         // rows log the same gate value as TRIGGER_EVAL rows.
         m_stateLog.SetEffectiveThreshold(m_profile.minScoreThreshold);

         // v3.14.5 Fix 6a: COMPRESSION trade mode.
         // Mode 0 blocks all new entries in COMPRESSION — the regime is a
         // breakout watch only. Mode 1 preserves v3.14.4 behaviour (the
         // InpScore_Compression=75 gate limits entries).
         if(InpCompressionMode == 0 &&
            m_ctx.regimeAtEntry.regime == (int)REGIME_COMPRESSION)
         {
            LogBlock("HTF", "Regime blocked: Compression (InpCompressionMode=0 — breakout watch only)");
            Transition(STATE_IDLE);
            return;
         }

         // v3.14.5 Fix 6b: COMPRESSION-exit early-trend arming.
         // Compression is the precursor to the moves this EA wants most.
         // When a confirmed flip OUT of COMPRESSION lands, do not wait up
         // to 4 hours for the H4 structure throttle — force an immediate
         // structure re-evaluation so the first BOS of the breakout is
         // caught on this pass.
         ENUM_MARKET_REGIME flipFrom;
         if(m_regime.ConsumeConfirmedFlip(flipFrom) &&
            flipFrom == REGIME_COMPRESSION)
         {
            Print("[ASE][HTF] Compression exit confirmed — forcing immediate structure re-evaluation (early-trend watch)");
            _lastStructureBar = 0;
            newH4Bar          = true;
         }

         // v3.14.2 Fix 4 — record the calendar date of this H1 evaluation
         // so ProcessIdle() can detect a fresh-day Off-Session entry before
         // any H1 bar has been processed on the current UTC day.
         MqlDateTime evalDt;
         TimeToStruct(h1Bar, evalDt);
         evalDt.hour = 0; evalDt.min = 0; evalDt.sec = 0;
         m_lastH1EvalDate = StructToTime(evalDt);
      } // end newH1Bar block

      // ── Step B: Structure evaluation (H4 throttle) ───────────────
      // Structure only re-evaluates when H4 bar advances. When only H1
      // advanced (regime updated, structure unchanged), skip to direction
      // confirmation with the existing m_ctx.direction and scoreCard.h4Bias.
      if(newH4Bar)
      {
         _lastStructureBar = h4Bar;

      // v3.12.3 — Direction resolution: H1 BOS + H4 pullback filter.
      //
      // RATIONALE FOR REMOVING DIRECTIONGATE:
      // The 3-signal vote (H4 EMA + H1 BOS + D1) introduced in v3.10.0 was
      // intended to prevent wrong-direction trades. In practice it caused
      // permanent DIR_NONE blocks on days where H1 BOS and D1 disagreed —
      // which is the most common profitable setup (pullback in a trend).
      // Confirmed: 203,243 DIR_NONE blocks on Jan 6 alone (v3.12.2 logs).
      // Even with the H4 slope removed (Fix B, v3.12.2), the gate still
      // blocked when H4 EMA=LONG and H1 BOS=SHORT on any pullback day.
      //
      // SOLUTION: restore v3.9.6 architecture — H1 BOS sets direction
      // directly — with ONE targeted addition: the H4 pullback filter.
      //
      // H4 PULLBACK FILTER (the only problem the gate was solving):
      // When H4 last closed candle is LONG and H1 BOS is also LONG,
      // a SHORT trade is a pullback within the uptrend — block it.
      // When H4 last closed candle is SHORT and H1 BOS is also SHORT,
      // a LONG trade is a pullback within the downtrend — block it.
      // In both cases the H1 BOS and H4 AGREE on direction, so the
      // trade going against both is clearly wrong-direction.
      //
      // When H4 and H1 BOS DISAGREE (H4=LONG, H1=SHORT or vice versa),
      // the H1 BOS wins — this is the structural change/anticipation
      // scenario that v3.9.6 traded profitably (25 shorts at 64% WR).
      // This is NOT a pullback — it is genuine counter-trend structure.

      // Step 1: Run StructureEngine — sets H1 BOS direction and H4 closed dir.
      ValidationResult res = m_structure.Evaluate(m_ctx.direction);

      if(!res.passed || m_ctx.direction == DIR_NONE)
      {
         // MANIPULATION regime swing fallback (preserved from v3.9.6)
         if(m_ctx.regimeAtEntry.regime == (int)REGIME_MANIPULATION)
         {
            string swingReason;
            ENUM_TRADE_DIRECTION swingDir = m_liq.GetDirectionFromSwing(
               m_ctx.regimeAtEntry.atr, swingReason,
               m_structure.GetH1BiasCurrent());
            if(swingDir == DIR_NONE)
            {
               LogBlock("HTF", "Direction=NONE (H1 BOS + swing fail) | " + res.reason);
               Transition(STATE_IDLE);
               return;
            }
            m_ctx.direction = swingDir;
            Print(StringFormat("[ASE][HTF] MANIPULATION swing fallback resolved %s | %s",
                  m_ctx.direction == DIR_LONG ? "LONG" : "SHORT", swingReason));

            // FIX (2026.06.24): res.score was left at its failed-Evaluate()
            // default of 0.0 here, even though a valid direction was just
            // resolved via the swing fallback. m_ctx.scoreCard.h4Bias reads
            // res.score below — so every MANIPULATION-regime swing-fallback
            // cycle scored 0/30 on H4 bias, making the 75-point MANIPULATION
            // threshold mathematically unreachable. Confirmed live: zero
            // trades fired across ~9 hours of MANIPULATION regime on
            // 2026.06.24, log showing "Score pre-filter ... cannot reach 75"
            // on every cycle. Assign a reduced-confidence score — mirrors
            // the reconfirmation-window pattern (r.score=10.0, above in
            // StructureEngine) since this direction also bypassed a clean
            // H1 BOS. Set below the weakest normal BOS tier (15.0) so
            // swing-fallback setups still must clear threshold on M15/M1/
            // liquidity strength, not on this score alone.
            res.score = 12.0;
         }
         else
         {
            LogBlock("HTF", "Direction=NONE | " + res.reason);
            Transition(STATE_IDLE);
            return;
         }
      }

      // Step 2: H4 pullback filter.
      // Block a trade only when H4 closed candle and H1 BOS BOTH agree on
      // the same direction — meaning a trade in the OPPOSITE direction is a
      // confirmed pullback within a trend, not a structural change.
      // When H4 and H1 BOS disagree, let H1 BOS win (anticipation-of-change).
      //
      // v3.12.7 Fix 2: H4 body size guard.
      // A doji or inside bar with a 1-point body can flip m_h4ClosedDir,
      // causing false pullback blocks on ambiguous candles. Only apply the
      // pullback filter when the H4 closed candle has a body ≥ 20% of ATR.
      // If H4 body is too small, H4 direction is considered ambiguous and
      // the filter is bypassed — H1 BOS determines direction freely.
      {
         ENUM_TRADE_DIRECTION h4Dir = m_structure.GetH4ClosedDirection();
         ENUM_TRADE_DIRECTION h1Dir = m_ctx.direction;
         double               atrVal = m_ctx.regimeAtEntry.atr;

         // Read H4 closed candle body size
         double h4Cl[], h4Op[];
         ArraySetAsSeries(h4Cl, true);
         ArraySetAsSeries(h4Op, true);
         bool h4BodyValid = false;
         if(CopyClose(_Symbol, PERIOD_H4, 1, 1, h4Cl) >= 1 &&
            CopyOpen( _Symbol, PERIOD_H4, 1, 1, h4Op) >= 1 &&
            atrVal > 0)
         {
            double h4Body = MathAbs(h4Cl[0] - h4Op[0]);
            h4BodyValid   = (h4Body >= atrVal * 0.20);   // ≥ 20% ATR = meaningful candle
            if(!h4BodyValid)
               Print(StringFormat(
                  "[ASE][HTF] Pullback filter bypassed — H4 body %.5f < 20%% ATR (%.5f) — ambiguous candle",
                  h4Body, atrVal * 0.20));
         }

         bool pullbackBlock  = false;
         string pullbackReason = "";

         if(h4BodyValid)
         {
            // SHORT blocked when H4=LONG and H1 BOS=LONG (confirmed uptrend pullback)
            if(h1Dir == DIR_SHORT && h4Dir == DIR_LONG &&
               m_structure.GetH1BiasCurrent() == DIR_LONG)
            {
               pullbackBlock  = true;
               pullbackReason = StringFormat(
                  "Pullback filter: SHORT blocked — H4=LONG + H1BOS=LONG (pullback in uptrend) | %s",
                  res.reason);
            }
            // LONG blocked when H4=SHORT and H1 BOS=SHORT (confirmed downtrend pullback)
            else if(h1Dir == DIR_LONG && h4Dir == DIR_SHORT &&
                    m_structure.GetH1BiasCurrent() == DIR_SHORT)
            {
               pullbackBlock  = true;
               pullbackReason = StringFormat(
                  "Pullback filter: LONG blocked — H4=SHORT + H1BOS=SHORT (pullback in downtrend) | %s",
                  res.reason);
            }
         }

         if(pullbackBlock)
         {
            LogBlock("HTF", pullbackReason);
            Transition(STATE_IDLE);
            return;
         }
      }

      // Direction confirmed — log and advance.
      m_ctx.isCountertrendShortException = false;   // no gate exception path in v3.12.3
      Print(StringFormat("[ASE][HTF] Direction confirmed | dir=%s | H4ctx=%s | H1BOS: %s",
            m_ctx.direction == DIR_LONG ? "LONG" : "SHORT",
            m_structure.GetH4ClosedDirection() == DIR_LONG  ? "bull" :
            m_structure.GetH4ClosedDirection() == DIR_SHORT ? "bear" : "n/a",
            res.reason));

      // v3.4.9 fix (Fix 2): Bias flip escalation via CheckBiasConfidence.
      // Bias confidence gate still runs after H1 confirmation — it checks
      // M15 momentum against the resolved direction. Cycle counter increments
      // on each fresh M15 conflict; after InpBiasFlipCycles cycles the EA
      // forces a fresh H4 re-evaluation. On a clean pass the counter resets.
      string confReason;
      if(!m_structure.CheckBiasConfidence(m_ctx.direction,
                                           m_ctx.regimeAtEntry.atr,
                                           confReason))
      {
         LogBlock("HTF", "Bias confidence low: " + confReason);

         if(StringFind(confReason, "M15 momentum") >= 0)
         {
            m_biasBlockCycles++;
            Print(StringFormat("[ASE][HTF] Bias block cycle %d/%d | dir=%s",
                  m_biasBlockCycles, InpBiasFlipCycles,
                  m_ctx.direction == DIR_SHORT ? "SHORT" : "LONG"));

            if(m_biasBlockCycles >= InpBiasFlipCycles)
            {
               Print(StringFormat(
                  "[ASE][HTF] Bias flip escalation: %d cycles elapsed — "
                  "forcing H1/H4 re-evaluation", m_biasBlockCycles));
               m_biasBlockCycles = 0;
               m_structure.ResetBiasBlockBar();
               m_htfBarReset = true;   // clears both _lastRegimeBar and _lastStructureBar
               return;
            }
         }

         // v3.11.1 fix (Fix C): set m_htfBarReset so the pipeline re-evaluates
         // after the M15 bias cooldown expires (InpBiasReEvalBars bars) rather
         // than waiting up to 1 hour for the next H1 candle to open.
         // Without this, a bias confidence block at 00:01 on an H1 bar caused
         // a ~1h silence window because _lastRegimeBar matched the current bar.
         m_htfBarReset = true;

         Transition(STATE_IDLE);
         return;
      }
      m_biasBlockCycles = 0;

      // v3.12.8: if the bias cooldown JUST expired this evaluation, force
      // immediate re-entry on the next M15 bar by bypassing both throttles.
      // Root cause of 145,198 cycling blocks (Mar logs): the 2-hour grace window
      // (8 M15 bars) was always fully elapsed before ProcessHTF ran again.
      // m_htfBarReset=true clears both _lastRegimeBar and _lastStructureBar.
      if(m_structure.WasGraceJustStarted())
      {
         m_htfBarReset = true;   // clears both throttles
         Print("[ASE][HTF] Cooldown expired — H1/H4 throttle bypassed for grace window");
      }

      // v3.12.0 Fix B: assign H4 bias score from StructureEngine result.
      m_ctx.scoreCard.h4Bias = res.score;
      } // end newH4Bar block

      // If only regime updated (H1 bar advanced, H4 bar did not), advance
      // to WAIT_SETUP using the existing direction and scoreCard.h4Bias
      // from the last H4 evaluation. Regime change is now reflected in
      // m_ctx.regimeAtEntry and will affect scoring and liq mode.
      Transition(STATE_WAIT_SETUP);
   }

   //─────────────────────────────────────────────────────────────────
   void ProcessSetup()
   {
      static datetime _lastSetupBar = 0;
      datetime currentBar = iTime(_Symbol, PERIOD_M15, 0);
      if(currentBar == _lastSetupBar) return;
      _lastSetupBar = currentBar;

      Print(StringFormat("[ASE] Heartbeat | State=WAIT_SETUP | Bar=%s | "
            "Direction=%s | Spread=%.1f",
            TimeToString(currentBar, TIME_DATE|TIME_MINUTES),
            (m_ctx.direction == DIR_LONG ? "LONG" :
             m_ctx.direction == DIR_SHORT ? "SHORT" : "NONE"),
            CASE_Broker::GetSpread()));

      // v4.0 — M15/H1/H4 evidence collection. Runs BEFORE the legacy
      // evaluation below and regardless of its outcome — plan §29 wants
      // opportunities logged whether or not a trade is taken. Read-only
      // with respect to every legacy engine (see
      // ASE_SetupEvidenceCollector.mqh); m_ctx.direction/regimeAtEntry
      // are read, never written, here.
      // v4.0 — resolve theoretical outcomes for opportunities logged on
      // prior bars, using the just-closed M15 bar's range. Runs every
      // M15 bar regardless of direction (a pending record may resolve
      // even on a bar where m_ctx.direction has since gone DIR_NONE).
      if(InpAceV4Mode >= ACEV4_EVIDENCE)
      {
         double closedHi = iHigh(_Symbol, PERIOD_M15, 1);
         double closedLo = iLow(_Symbol, PERIOD_M15, 1);
         datetime closedTime = iTime(_Symbol, PERIOD_M15, 1);
         if(closedHi > 0.0 && closedLo > 0.0)
         {
            m_v4Analytics.ResolvePending(closedTime, closedHi, closedLo);
            m_v4Adaptive.ResolveShadow(closedTime, closedHi, closedLo);
            ENUM_SETUP_ARCHETYPE theoArch=ARCH_NONE; double theoR=0.0;
            bool theoLiq=false; string theoOppId=""; bool theoLegacy=false;
            bool theoWouldQualify=false; string theoRegime="";
            ulong theoEnhMask=0; ulong theoEvalMask=0; int theoRegimeEnum=0;
            while(m_v4Analytics.GetNextTheoreticalOutcome(theoArch,theoR,theoLiq,theoOppId,theoLegacy,theoWouldQualify,theoRegime,
                                                            theoEnhMask,theoEvalMask,theoRegimeEnum))
            {
               if(theoLegacy)
               {
                  // v4.0.2 -- legacy actually traded this setup: the real close
                  // records the learning outcome (RecordOutcome), so skip that
                  // here to avoid double counting.
                  // v4.0.2 Phase 1 -- only join into the "both" cell when V4
                  // would ALSO have qualified this setup (wouldQualify==true).
                  // When legacy traded a setup V4's classifier completed but
                  // did NOT qualify (grade FAIL/C), that's legacyOnly, not
                  // both -- and legacyOnly needs the REAL R, which only exists
                  // once the trade closes, so RecordClosedTrade() records that
                  // case entirely on its own; nothing to do here for it.
                  if(theoWouldQualify)
                     StashOrResolveCompareBoth(theoOppId, ASE_ArchetypeName(theoArch), theoRegime, true, theoR, closedTime);
                  continue;
               }
               m_v4Adaptive.RecordOutcome(theoArch,theoR,m_v4Adaptive.IsOOS(closedTime,theoOppId),theoLiq,
                                          (ENUM_MARKET_REGIME)theoRegimeEnum,theoEnhMask,theoEvalMask);
               // v4.0.2 Phase 1 -- Case A: legacy did NOT trade this setup.
               // wouldQualify=true -> v4Only (V4 would have taken it);
               // wouldQualify=false -> neither (V4 didn't qualify it either).
               m_v4Analytics.RecordComparison(ASE_ArchetypeName(theoArch), theoRegime, theoWouldQualify, false, theoR, 0.0);
            }
            ExpireStaleCompareJoins(closedTime);
         }
      }

      if(InpAceV4Mode >= ACEV4_EVIDENCE && m_ctx.direction != DIR_NONE)
      {
         m_v4Evidence.BeginBar(currentBar);
         m_v4Evidence.CollectM15Context(m_structure, m_setup, m_regime,
                                         m_ctx.direction, m_ctx.regimeAtEntry,
                                         m_structure.GetH4ClosedDirection(),
                                         m_ctx.scoreCard.h4Bias,
                                         m_profile.counterTrendDispMultiplier,
                                         m_profile.counterTrendFVGMinGap,
                                         m_profile.counterTrendFVGMaxDepth);
      }

      string setupClass;
      StructuralLevels levels;
      // v3.14.3 — pass H4 EMA separation and H4 ATR so CheckDisplacement() and
      // CheckFVG() can apply counter-trend quality gates when H4 trend is committed.
      // Gate activates when h4EMASep > InpCTEMASepThreshold * h4ATR, independent
      // of H1 regime classification — fires in RANGING and COMPRESSION too.
      ValidationResult res = m_setup.Evaluate(
         m_ctx.direction, setupClass, levels,
         m_ctx.regimeAtEntry.h4EMASep,
         m_ctx.regimeAtEntry.h4ATR,
         m_structure.GetH4ClosedDirection(),
         m_profile.counterTrendDispMultiplier,
         m_profile.counterTrendFVGMinGap,
         m_profile.counterTrendFVGMaxDepth);
      m_ctx.scoreCard.m15Setup = res.score;
      m_ctx.m15SetupClass      = setupClass;
      m_ctx.structLevels       = levels;   // v4.0 — stored for BuildSetup() at execution

      double spread = CASE_Broker::GetSpread();
      double atr    = m_ctx.regimeAtEntry.atr;

      if(!res.passed)
      {
         m_stateLog.LogSetup(setupClass, "FAIL", res.reason, m_ctx, spread, atr);
         // In V4 authoritative modes the legacy setup cascade is no longer the
         // decision authority. Preserve its result for parity/diagnostics, but
         // allow the V4 evidence path to complete on M1 and make the setup decision.
         bool v4MayContinue=(InpAceV4Mode>=ACEV4_CONDITIONAL && !InpAceV4ResearchOnly);
         if(!v4MayContinue)
         {
            LogBlock("SETUP", res.reason);
            Transition(STATE_IDLE);
            return;
         }
         Print("[ACE v4] Legacy setup failed but V4 authority is enabled; continuing to M1 evidence.");
      }
      else
      {
         m_stateLog.LogSetup(setupClass, "PASS", "", m_ctx, spread, atr);
      }

      Transition(STATE_WAIT_TRIGGER);
   }

   //─────────────────────────────────────────────────────────────────
   // FIX #3  — InpLiquidityConfirm now gates entry when liq.passed=false
   // FIX #4  — m_ctx.liquidityType assigned from GetLiquidityType()
   // FIX #7  — volatility score derived from cached regimeAtEntry
   // v4.0    — regime passed to DetectSweep(); vol/session/spread
   //           computed before liq gate so LogTriggerEval captures
   //           complete scorecard on every exit path.
   void ProcessTrigger()
   {
      m_v4ExecutionAttempt=false;

      // M15 heartbeat — ProcessTrigger runs every tick so throttle output
      {
         static datetime _lastTrigHBBar = 0;
         datetime hbBar = iTime(_Symbol, PERIOD_M15, 0);
         if(hbBar != _lastTrigHBBar)
         {
            _lastTrigHBBar = hbBar;
            Print(StringFormat("[ASE] Heartbeat | State=WAIT_TRIGGER | Bar=%s | "
                  "Direction=%s | Spread=%.1f",
                  TimeToString(hbBar, TIME_DATE|TIME_MINUTES),
                  (m_ctx.direction == DIR_LONG ? "LONG" :
                   m_ctx.direction == DIR_SHORT ? "SHORT" : "NONE"),
                  CASE_Broker::GetSpread()));
         }
      }

      double spread = CASE_Broker::GetSpread();
      double atr    = m_ctx.regimeAtEntry.atr;

      // ── Step 1: M1 trigger evaluation ────────────────────────────
      ValidationResult trig = m_trigger.Evaluate(m_ctx.direction);
      m_ctx.scoreCard.m1Trigger = trig.score;
      m_ctx.m1TriggerClass      = m_trigger.GetTriggerClass(trig);

      // ── Step 2: Complete the scorecard BEFORE any gate check ─────
      // Vol/session/spread were previously computed after the liq gate,
      // meaning LogBlock() on liq failure always logged a partial score.
      // Computing them here ensures LogTriggerEval captures the full
      // composite at every exit path.
      m_ctx.scoreCard.volatility = m_regime.GetVolatilityScoreFromState(m_ctx.regimeAtEntry);
      m_ctx.scoreCard.session    = m_session.GetSessionScore();
      m_ctx.scoreCard.spread     = m_valid.GetSpreadScore(InpMaxSpread);

      // v4.0 — live evidence/confluence/adaptive decision. M1 evidence is
      // evaluated on the current tick so the final confirmation can qualify
      // and hand off to Execution on the same tick. The V4 path remains
      // authority-gated; legacy execution below remains the compatibility path.
      if(InpAceV4Mode >= ACEV4_EVIDENCE && m_ctx.direction != DIR_NONE)
      {
         m_v4Evidence.CollectM1Context(m_trigger, m_liq, m_ctx.direction,
                                        m_ctx.regimeAtEntry.regime, m_profile.liqMode,
                                        m_ctx.scoreCard.session, m_ctx.scoreCard.spread);
         m_v4EvidenceTick=GetTickCount();
         SetupEvidenceSet v4ev = m_v4Evidence.Get();
         ConfluenceResult v4conf;
         m_v4Confluence.SetLiquidityWeightOverride(m_v4Adaptive.LiquidityWeight());
         m_v4Confluence.Evaluate(v4ev, v4conf);
         m_v4ConfluenceTick=GetTickCount();
         m_v4Classifier.Classify(v4ev, (ENUM_MARKET_REGIME)m_ctx.regimeAtEntry.regime, v4conf);
         v4conf.hasLiquiditySweep=v4ev.HasActive(EVID_LIQUIDITY_SWEEP,v4conf.direction);   // v4.0.2 -- carried to pending/entry snapshot
         m_v4Adaptive.Observe(v4conf, v4ev, (ENUM_MARKET_REGIME)m_ctx.regimeAtEntry.regime, m_v4AdaptiveDecision);
         m_v4ShadowAEligible=m_v4AdaptiveDecision.shadowAEligible;
         m_v4ShadowBEligible=m_v4AdaptiveDecision.shadowBEligible;
         m_v4OpportunityOpen=(v4conf.direction!=DIR_NONE);
         m_v4ExecutedByV4=false;
         bool v4Authority=(InpAceV4Mode==ACEV4_ACTIVE || InpAceV4Mode==ACEV4_CONDITIONAL) &&
                           !InpAceV4ResearchOnly &&
                           m_v4Adaptive.CanActivate(v4conf.archetype,v4conf.grade,(ENUM_MARKET_REGIME)m_ctx.regimeAtEntry.regime,v4conf.separation);
         v4conf.executionDecision=v4Authority?"EXECUTION_AUTHORITY":"LEARNING_ONLY";
         if(v4conf.qualified && !v4Authority) v4conf.blockReason="BLOCKED_ADAPTIVE_AUTHORITY";
         m_v4LastConfluence=v4conf;
         m_v4Dashboard.Update(v4conf,m_regime.RegimeName(m_ctx.regimeAtEntry.regime),m_ctx.m1TriggerClass,m_v4Adaptive.AuthorityName(),m_v4AdaptiveDecision.reason);

         double theoEntry=(v4conf.direction==DIR_LONG)?SymbolInfoDouble(_Symbol,SYMBOL_ASK):SymbolInfoDouble(_Symbol,SYMBOL_BID);
         double atrNow=m_ctx.regimeAtEntry.atr;
         double theoSL=0.0,theoTP1=0.0;
         if(v4conf.direction==DIR_LONG){theoSL=theoEntry-atrNow*m_profile.slMultiplier;theoTP1=m_ctx.structLevels.tp1Valid?m_ctx.structLevels.tp1:theoEntry+atrNow*InpATRMultiplierTP1;}
         else if(v4conf.direction==DIR_SHORT){theoSL=theoEntry+atrNow*m_profile.slMultiplier;theoTP1=m_ctx.structLevels.tp1Valid?m_ctx.structLevels.tp1:theoEntry-atrNow*InpATRMultiplierTP1;}
         if(v4conf.direction!=DIR_NONE)
         {
            // v4.0.2 -- RecordOpportunity returns "" while the DNA persists;
            // keep the last NON-EMPTY ID so trade close can still attribute it.
            string v4OppId=m_v4Analytics.RecordOpportunity(v4conf,false,theoEntry,theoSL,theoTP1,m_regime.RegimeName(m_ctx.regimeAtEntry.regime),(ENUM_MARKET_REGIME)m_ctx.regimeAtEntry.regime);
            if(v4OppId!="") m_v4LastOpportunityId=v4OppId;
            if(m_v4AdaptiveDecision.shadowAEligible) m_v4Adaptive.RegisterShadowCandidate(0,v4conf,theoEntry,theoSL,theoTP1);
            if(m_v4AdaptiveDecision.shadowBEligible) m_v4Adaptive.RegisterShadowCandidate(1,v4conf,theoEntry,theoSL,theoTP1);
         }

         // V4 validated execution is the only point where V4 may become
         // authoritative. It is still subject to discipline, orchestrator,
         // risk, broker, spread and execution protection.
         if(v4Authority)
         {
            DisciplineResult dr; OrchestratorResult orr;
            if(!m_v4Discipline.Check(m_session,m_news,m_valid,InpMaxSpread,dr))
            { m_v4LastConfluence.blockReason="DISCIPLINE: "+dr.reason; return; }
            if(!m_v4Orchestrator.CheckPortfolio(m_cluster,InpMaxPositions,orr))
            { m_v4LastConfluence.blockReason="ORCHESTRATOR: "+orr.reason; return; }
            double m1cl[]; ArraySetAsSeries(m1cl,true); double m1atr[]; ArraySetAsSeries(m1atr,true);
            if(CopyClose(_Symbol,PERIOD_M1,1,1,m1cl)>=1) m_ctx.triggerClosePrice=m1cl[0];
            if(CopyBuffer(m_trigger.GetATRHandle(),0,0,1,m1atr)>=1) m_ctx.triggerM1ATR=m1atr[0];
            if(v4ev.HasActive(EVID_M1_DISPLACEMENT,v4conf.direction) && v4ev.HasActive(EVID_M1_MICRO_BOS,v4conf.direction))
               m_ctx.m1TriggerClass="M1_DISP+MBOS";
            else if(v4ev.HasActive(EVID_M1_DISPLACEMENT,v4conf.direction))
               m_ctx.m1TriggerClass="M1_DISP";
            else if(v4ev.HasActive(EVID_M1_REJECTION,v4conf.direction))
               m_ctx.m1TriggerClass="M1_REJECTION";
            // ProcessExecution performs the remaining timing/risk/broker checks and
            // calls the same ExecutionEngine used by the legacy path.
            m_v4ExecutionAttempt=true;
            m_v4ExecutionTick=GetTickCount();
            ProcessExecution();
            return;
         }
      }

      // ── Step 2b: EMA_Fallback filter in RANGING (v3.14.2 Fix 2) ─
      // In RANGING the SL is wide (~1.5× ATR). EMA_Fallback is the
      // weakest trigger (Score_M1=7, no structural confirmation), and
      // produced the largest per-trade loss of any trigger class in RANGING
      // (7 losses, avg −$21.15, $148 total — May/Jun 2026 live data).
      // When InpEMAFallbackInRanging=false (default), reject EMA_Fallback
      // entries in RANGING and require a proper M1 confirmation signal
      // (Displacement, Disp+mBOS, or Rejection with EMA/mBOS confluence).
      if(!InpEMAFallbackInRanging &&
         trig.passed &&
         m_ctx.m1TriggerClass == "EMA_Fallback" &&
         m_ctx.regimeAtEntry.regime == (int)REGIME_RANGING)
      {
         string blockReason = "EMA_Fallback blocked in RANGING (InpEMAFallbackInRanging=false) — require stronger M1 trigger";
         m_score.Validate(m_ctx.scoreCard, m_profile.minScoreThreshold);
         m_stateLog.LogTriggerEval("TRIG_FAIL", blockReason, m_ctx, spread, atr,
                                    m_profile.minScoreThreshold);
         LogBlock("TRIGGER", blockReason);
         Transition(STATE_IDLE);
         return;
      }

      // ── Step 2c: EMA_Fallback filter in TRENDING (v3.14.9 Fix 14) ─
      // Full-period backtest (335 trades, v3.14.7 data): EMA_Fallback is
      // the worst trigger class in the whole system (WR 38%, PF 0.66,
      // -$670.66 net across all regimes), and within TRENDING specifically
      // it's 87 of 191 trades at PF 0.69 / -$480.08 — almost the entirety
      // of TRENDING's net loss. Same weakness the RANGING gate above
      // already addresses (no structural confirmation, Score_M1=7); this
      // extends it to TRENDING. Disp+mBOS, Displacement, and Rejection
      // remain available in TRENDING — only the weakest trigger is gated.
      if(!InpEMAFallbackInTrending &&
         trig.passed &&
         m_ctx.m1TriggerClass == "EMA_Fallback" &&
         m_ctx.regimeAtEntry.regime == (int)REGIME_TRENDING)
      {
         string blockReason = "EMA_Fallback blocked in TRENDING (InpEMAFallbackInTrending=false) — require stronger M1 trigger";
         m_score.Validate(m_ctx.scoreCard, m_profile.minScoreThreshold);
         m_stateLog.LogTriggerEval("TRIG_FAIL", blockReason, m_ctx, spread, atr,
                                    m_profile.minScoreThreshold);
         LogBlock("TRIGGER", blockReason);
         Transition(STATE_IDLE);
         return;
      }

      // ── Step 2d: Weak SHORT triggers in TRENDING (v3.14.10 Fix 15) ─
      // Full-period backtest (252 trades, clean PositionID-joined data,
      // post Fix 14): TRENDING+SHORT measured WR 37.1%, PF 0.69, -$428.35
      // net (n=70) against TRENDING+LONG at WR 52.2%, PF 1.18, +$182.50
      // (n=69) — a direction-specific weakness. Disp+mBOS is explicitly
      // exempt: it's the one trigger already proven to work in TRENDING on
      // both sides (PF 1.59 combined) and must keep firing regardless of
      // direction. Only Rejection and Displacement are gated on the SHORT
      // side — the two trigger classes carrying TRENDING's SHORT-side loss.
      if(!InpWeakShortTriggersInTrending &&
         trig.passed &&
         m_ctx.direction == DIR_SHORT &&
         m_ctx.regimeAtEntry.regime == (int)REGIME_TRENDING &&
         (m_ctx.m1TriggerClass == "Rejection" || m_ctx.m1TriggerClass == "Displacement"))
      {
         string blockReason = StringFormat(
            "%s blocked on SHORT in TRENDING (InpWeakShortTriggersInTrending=false) — Disp+mBOS still allowed",
            m_ctx.m1TriggerClass);
         m_score.Validate(m_ctx.scoreCard, m_profile.minScoreThreshold);
         m_stateLog.LogTriggerEval("TRIG_FAIL", blockReason, m_ctx, spread, atr,
                                    m_profile.minScoreThreshold);
         LogBlock("TRIGGER", blockReason);
         Transition(STATE_IDLE);
         return;
      }

      // ── Step 3: M1 trigger pass check ────────────────────────────
      // v3.12.7 Fix 1: M1 trigger evaluated BEFORE liquidity gate.
      // Prior order (liq → trigger) discarded valid setups on LIQ_FAIL
      // before checking whether the M1 trigger was even present — a setup
      // with a perfect trigger signal was killed without seeing it.
      // New order: if trigger fails, skip liquidity (faster). If trigger
      // passes, liquidity must also confirm. Both gates remain active;
      // only the evaluation order changes.
      if(!trig.passed)
      {
         m_score.Validate(m_ctx.scoreCard, m_profile.minScoreThreshold);
         m_stateLog.LogTriggerEval("TRIG_FAIL", trig.reason, m_ctx, spread, atr,
                                    m_profile.minScoreThreshold);
         LogBlock("TRIGGER", trig.reason);
         Transition(STATE_IDLE);
         return;
      }

      // ── Step 3b: Score pre-filter (v3.14.0 — Wave 0 Rec 3, profile-aware)
      // Max liquidity contribution = 15/105 × 100 = 14.3 normalised points.
      // If the current score (excluding liquidity) is already below
      // (profile threshold − 14.3), no liq score can rescue the trade.
      // Skip the 34-bar DetectSweep() scan entirely.
      // Uses m_profile.minScoreThreshold so the filter tightens automatically
      // in restrictive regimes (e.g. COMPRESSION threshold 75 → filter at 60.7).
      {
         double partialNorm = m_score.Normalise(
            m_ctx.scoreCard.h4Bias   + m_ctx.scoreCard.m15Setup  +
            m_ctx.scoreCard.m1Trigger + m_ctx.scoreCard.volatility +
            m_ctx.scoreCard.session  + m_ctx.scoreCard.spread);

         double liqMaxContrib = 14.3;   // 15/105 × 100
         if(partialNorm < m_profile.minScoreThreshold - liqMaxContrib)
         {
            m_ctx.scoreCard.liquidity = 0.0;
            m_score.Validate(m_ctx.scoreCard, m_profile.minScoreThreshold);
            m_stateLog.LogTriggerEval("SCORE_PREFAIL",
               StringFormat("Pre-filter: partial=%.1f < threshold(%.0f)-liq(%.1f)=%.1f — liq scan skipped",
                  partialNorm, m_profile.minScoreThreshold, liqMaxContrib,
                  m_profile.minScoreThreshold - liqMaxContrib),
               m_ctx, spread, atr, m_profile.minScoreThreshold);
            LogBlock("SCORING", StringFormat("Score pre-filter: %.1f cannot reach %.0f even with max liq",
               partialNorm, m_profile.minScoreThreshold));
            Transition(STATE_IDLE);
            return;
         }
      }

      // ── Step 4: Liquidity gate ────────────────────────────────────
      // Runs only when M1 trigger has passed and score pre-filter cleared.
      // v3.14.1: liqMode from active profile forces detection branch.
      // Default LIQ_STANDARD preserves existing regime-based routing.
      // MANIPULATION profile uses LIQ_SWEEP_ONLY (set in Wave 3 tuning).
      if(InpLiquidityConfirm)
      {
         ValidationResult liq = m_liq.DetectSweep(
            m_ctx.direction,
            (ENUM_MARKET_REGIME)m_ctx.regimeAtEntry.regime,
            m_profile.liqMode);

         m_ctx.scoreCard.liquidity = liq.score;
         m_ctx.liquidityType       = m_liq.GetLiquidityType();

         if(!liq.passed)
         {
            m_score.Validate(m_ctx.scoreCard, m_profile.minScoreThreshold);
            m_stateLog.LogTriggerEval("LIQ_FAIL", liq.reason, m_ctx, spread, atr,
                                       m_profile.minScoreThreshold);
            LogBlock("TRIGGER", "Liq confirm required: " + liq.reason);
            Transition(STATE_IDLE);
            return;
         }
      }

      // ── Step 5: Composite score gate ─────────────────────────────
      // v3.12.7 Fix 3: reduced threshold during RequireReconfirmation window.
      // v3.14.0: base threshold now from m_profile.minScoreThreshold.
      double effectiveThreshold = m_profile.minScoreThreshold;
      if(m_structure.IsReconfirmRequired())
         effectiveThreshold = MathMax(m_profile.minScoreThreshold - 8.0, 40.0);

      if(!m_score.Validate(m_ctx.scoreCard, effectiveThreshold))
      {
         // FIX (2026.06.24): removed dead countertrend-SHORT score-bonus branch.
         // m_ctx.isCountertrendShortException is hardcoded false in ProcessHTF()
         // ("no gate exception path in v3.12.3") and is never set true anywhere
         // else in this codebase (confirmed via full-repo search) — so the
         // InpDGShortScoreBonus boost path below could never execute. Collapsed
         // to the always-reachable fail path; behavior is unchanged.
         m_stateLog.LogTriggerEval("SCORE_FAIL",
            m_score.Describe(m_ctx.scoreCard), m_ctx, spread, atr,
            effectiveThreshold);
         LogBlock("SCORING", m_score.Describe(m_ctx.scoreCard) +
                             " | Threshold=" + DoubleToString(effectiveThreshold, 1) +
                             (m_structure.IsReconfirmRequired() ? " [reconfirm-8]" : ""));
         Transition(STATE_IDLE);
         return;
      }

      // ── All gates passed ─────────────────────────────────────────
      // v3.6.0 — snapshot the M1 trigger bar close price and M1 ATR so
      // ProcessExecution() can reject a fill where live price has drifted
      // materially since the trigger fired (entry timing slippage gate).
      {
         double m1Cl[], m1Atr[];
         ArraySetAsSeries(m1Cl,  true);
         ArraySetAsSeries(m1Atr, true);
         if(CopyClose(_Symbol, PERIOD_M1, 1, 1, m1Cl)  >= 1) m_ctx.triggerClosePrice = m1Cl[0];
         if(CopyBuffer(m_trigger.GetATRHandle(), 0, 0, 1, m1Atr) >= 1) m_ctx.triggerM1ATR = m1Atr[0];
      }
      m_stateLog.LogTriggerEval("PASS", "", m_ctx, spread, atr, effectiveThreshold);
      Transition(STATE_WAIT_EXECUTION);
   }

   //─────────────────────────────────────────────────────────────────
   void ProcessExecution()
   {
      // v3.4.5 fix (Issue 1): If an ATR=0 glitch or external event caused
      // a Transition(STATE_IDLE) while this execution window was pending,
      // the state machine may have already reset before ProcessExecution()
      // was called on the next tick. Guard: abort immediately if context
      // direction is NONE (cleared by Reset()) or if a position already
      // exists from a prior leaked execution.
      // Observed on 2026-06-03: pipeline reached STATE_WAIT_EXECUTION at
      // 16:02, ATR=0 glitch fired STATE_IDLE at 16:22, trade still placed
      // at 16:50 with zeroed context (rr=0, score=0, ATR=0 in TRADE row).
      if(m_ctx.direction == DIR_NONE)
      {
         LogBlock("EXECUTION", "Aborted — context reset before order could fire (ATR=0 glitch)");
         Transition(STATE_IDLE);
         return;
      }
      if(HasOpenPosition())
      {
         LogBlock("EXECUTION", "Aborted — position already open (leaked execution guard)");
         Transition(STATE_MANAGE);
         return;
      }

      if(!m_valid.SpreadAcceptable(InpMaxSpread))
      {
         LogBlock("EXECUTION", "Spread widened at entry");
         Transition(STATE_IDLE);
         return;
      }

      // v3.6.0 — Entry timing slippage gate.
      // The trigger fires on bar[1] (last closed M1) but execution happens
      // on bar[0] (live price). On an active GOLD session, 1 M1 bar = 4–8 pts
      // of movement. If live price has drifted > 0.5× M1 ATR from the trigger
      // bar close, the entry location is materially different from what was
      // confirmed — abort and re-enter STATE_IDLE to wait for a fresh signal.
      // Threshold 0.5× ATR is conservative; adjust via InpSlippageGateATRMult.
      // v3.14.5 Fix 4: drift is measured ADVERSE-ONLY by default.
      // The trigger fires on M1 bar close and executes ~60s later; on GOLD
      // a routine minute moves more than half its own ATR, so the absolute
      // 0.5× gate vetoed valid entries (2026-07-23: the only qualified
      // signal of the session, 75.9 vs 55, aborted at 1.04 vs 1.02 pts —
      // a 2-cent miss). Favourable drift is a BETTER fill for the confirmed
      // direction and should never abort; only adverse drift means the
      // entry location has materially degraded. Default limit raised to
      // 0.8× M1 ATR (InpSlippageGateATRMult in Config).
      if(InpSlippageGateATRMult > 0 && m_ctx.triggerClosePrice > 0 && m_ctx.triggerM1ATR > 0)
      {
         double livePrice  = (m_ctx.direction == DIR_LONG)
                             ? CASE_Broker::GetAsk()
                             : CASE_Broker::GetBid();
         double drift;
         if(InpSlippageAdverseOnly)
            drift = (m_ctx.direction == DIR_LONG)
                    ? (livePrice - m_ctx.triggerClosePrice)    // paying up = adverse
                    : (m_ctx.triggerClosePrice - livePrice);   // selling down = adverse
         else
            drift = MathAbs(livePrice - m_ctx.triggerClosePrice);
         double driftLimit = m_ctx.triggerM1ATR * InpSlippageGateATRMult;
         if(drift > driftLimit)
         {
            LogBlock("EXECUTION", StringFormat(
               "Trigger-to-fill %sdrift %.2f pts > %.1f× M1ATR (%.2f pts) — stale trigger abort",
               InpSlippageAdverseOnly ? "adverse " : "",
               drift, InpSlippageGateATRMult, driftLimit));
            Transition(STATE_IDLE);
            return;
         }
      }

      // v3.4.6 — pass current regime to RiskEngine before BuildSetup() so
      // regime-aware SL multiplier selection uses the same regime already
      // captured in m_ctx.regimeAtEntry (no redundant GetState() call).
      // v3.14.0: CacheRegime() is now a no-op stub — profile carries SL values.
      m_risk.CacheRegime((ENUM_MARKET_REGIME)m_ctx.regimeAtEntry.regime);
      m_risk.CacheScore(m_ctx.scoreCard.total);   // v3.12.7: for DD halt override

      // v3.4.8 fix: recompute structural levels at execution time using the
      // live entry price. Levels captured during ProcessSetup() can be 10-30
      // minutes stale by the time the order fires — the distance validation
      // inside ComputeTP() then fails against the new entry, forcing ATR
      // fallback even though a valid structural level exists. Recomputing
      // here ensures levels.tp1Valid reflects the actual entry price.
      // setupClass is preserved from ProcessSetup() in m_ctx.m15SetupClass.
      StructuralLevels freshLevels;
      ValidationResult freshSetup = m_setup.Evaluate(
         m_ctx.direction, m_ctx.m15SetupClass, freshLevels);
      if(freshLevels.tp1Valid || freshLevels.tp2Valid)
      {
         m_ctx.structLevels = freshLevels;
         Print(StringFormat("[ASE][EXEC] Structural levels refreshed at execution | "
               "tp1=%.5f(%s) tp2=%.5f(%s) src=%s",
               freshLevels.tp1, freshLevels.tp1Valid?"valid":"n/a",
               freshLevels.tp2, freshLevels.tp2Valid?"valid":"n/a",
               freshLevels.source));
      }
      else
      {
         Print("[ASE][EXEC] Structural level refresh returned no valid levels — "
               "using setup-time levels (tp1Valid=",
               m_ctx.structLevels.tp1Valid?"true":"false", ")");
      }

      // v4.0 — structural levels (now refreshed) passed to BuildSetup().
      // v3.14.0 — active regime profile passed so SL/cap are regime-specific.
      m_ctx.tradeSetup = m_risk.BuildSetup(m_ctx.direction, m_ctx.structLevels, m_profile);

      double sessionMult = CASE_TradeManager::GetSessionRiskMultiplier();
      if(sessionMult <= 0.0)
      {
         LogBlock("EXECUTION", "Off-session risk=0");
         Transition(STATE_IDLE);
         return;
      }
      m_ctx.tradeSetup.lotSize *= sessionMult;
      m_ctx.tradeSetup.lotSize  = m_norm.NormalizeLot(m_ctx.tradeSetup.lotSize);

      if(!m_ctx.tradeSetup.valid)
      {
         LogBlock("EXECUTION", m_ctx.tradeSetup.reason);
         Transition(STATE_IDLE);
         return;
      }

      if(!m_valid.HasAdequateMargin(m_ctx.tradeSetup.lotSize))
      {
         LogBlock("EXECUTION", "Insufficient margin");
         Transition(STATE_IDLE);
         return;
      }

      // v4.0 — latency is measured inside Execute() via GetTickCount()
      // on each attempt. No pre-order snapshot needed here.

      if(m_exec.Execute(m_ctx.tradeSetup))
      {
         if(m_v4ExecutionAttempt) m_v4ExecutedByV4=true;
         if(InpAceV4Mode >= ACEV4_EVIDENCE && m_v4OpportunityOpen)
         {
            m_v4Analytics.RecordExecution(m_v4LastConfluence);
            m_v4Analytics.RecordRegimeExecution(m_regime.RegimeName(m_ctx.regimeAtEntry.regime));
            // v4.0.2 -- this setup was really traded: its theoretical twin must
            // not also feed the adaptive engine (no double counting).
            m_v4Analytics.MarkLegacyTraded(m_v4LastConfluence.setupDNA);
         }
         // v4.0.2 -- V4 entry snapshot, immune to later ticks overwriting
         // m_v4LastConfluence / m_v4LastOpportunityId while the trade is open.
         m_v4EntryValid  = (InpAceV4Mode >= ACEV4_EVIDENCE && m_v4OpportunityOpen);
         m_v4EntryConf   = m_v4LastConfluence;
         m_v4EntryOppId  = m_v4LastOpportunityId;
         m_v4EntryRegime = (int)m_ctx.regimeAtEntry.regime;
         m_v4EntryHasLiq = m_v4LastConfluence.hasLiquiditySweep;
         m_mgr.SetTP1(m_ctx.tradeSetup.takeProfit1);
         m_tradeOpenTime      = TimeCurrent();
         m_partialProfitAccum = 0.0;   // v3.14.6 Fix 9
         m_partialTicketSeen  = 0;     // v3.14.7 Fix 10

         // v3.4.9 fix (Fix 3): Snapshot entry context immediately after
         // confirmed execution. These values are immune to any subsequent
         // mid-manage context corruption and are used exclusively by
         // RecordClosedTrade() to populate the TRADE row.
         m_snapRR        = m_ctx.tradeSetup.rr;
         m_snapScore     = m_ctx.scoreCard.total;
         m_snapATR       = m_ctx.regimeAtEntry.atr;
         m_snapRegime    = m_regime.RegimeName(
                              (ENUM_MARKET_REGIME)m_ctx.regimeAtEntry.regime);
         m_snapSession   = m_ctx.sessionAtEntry;
         m_snapDirection = (m_ctx.direction == DIR_LONG) ? "LONG" : "SHORT";
         Print(StringFormat(
            "[ASE][EXEC] Entry snapshot | dir=%s score=%.1f rr=%.2f ATR=%.5f regime=%s",
            m_snapDirection, m_snapScore, m_snapRR, m_snapATR, m_snapRegime));

         m_tel.StartTracking(
            m_ctx.tradeSetup.entry,
            m_ctx.tradeSetup.stopLoss,
            m_ctx.tradeSetup.takeProfit2,
            m_ctx.direction == DIR_LONG);
         m_positionSelfOpened = true;   // Fix (2026-08-30): real context, trust it at close
         m_ctx.entryTime      = TimeCurrent();
         m_ctx.sessionAtEntry = m_session.GetSessionName();
         // v4.0 — store fill latency in context so Enrich() can read it
         // without a second GetTickCount() call at close time.
         m_ctx.execLatencyMs  = m_exec.GetLastLatencyMs();

         string dir = (m_ctx.direction == DIR_LONG) ? "LONG" : "SHORT";
         m_diag.LogTrade(dir,
            m_ctx.tradeSetup.entry, m_ctx.tradeSetup.stopLoss,
            m_ctx.tradeSetup.takeProfit1, m_ctx.tradeSetup.takeProfit2,
            m_ctx.tradeSetup.lotSize, m_ctx.scoreCard.total);

         CASE_Logger::Trade("Opened " + dir +
            " | Score=" + DoubleToString(m_ctx.scoreCard.total, 1) +
            " | " + m_ctx.tradeSetup.reason);

         // FIX #9 — transition directly to MANAGE (not POSITION_OPEN)
         Transition(STATE_MANAGE);
      }
      else
      {
         LogBlock("EXECUTION", "Order placement failed");
         Transition(STATE_IDLE);
      }
   }

   //─────────────────────────────────────────────────────────────────
   // FIX #9 — ProcessManagement() is the single state for open positions.
   // On close detected: record trade → cooldown → IDLE.
   // While open: manage → stay in MANAGE (no ping-pong to POSITION_OPEN).
   //
   // v3.4.5: On close detection, log elapsed hold time and the close price
   // relative to SL/TP so early exits (spike-outs, session exits, trailing
   // stop fires) are distinguishable in the Experts tab without needing MT5
   // history browser. Observed pattern: trades closing 4–34 min after entry
   // at prices that implied SL hit but with losses inconsistent with 1× ATR SL.
   void ProcessManagement()
   {
      if(!HasOpenPosition())
      {
         m_tradeVis.ClearTradePanel();   // v3.14.17 Fix 24
         // v3.4.5 — log hold time and close context before resetting ctx
         datetime holdSecs = (m_tradeOpenTime > 0) ? TimeCurrent() - m_tradeOpenTime : 0;
         double   closePrice = 0.0;
         // Attempt to read last deal close price for diagnostic log
         HistorySelect(m_tradeOpenTime > 0 ? m_tradeOpenTime : TimeCurrent() - 86400, TimeCurrent());
         for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
         {
            ulong dTkt = HistoryDealGetTicket(i);
            if(HistoryDealGetString(dTkt, DEAL_SYMBOL) != _Symbol) continue;
            if(HistoryDealGetInteger(dTkt, DEAL_MAGIC) != InpMagicNumber) continue;
            ENUM_DEAL_ENTRY de = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(dTkt, DEAL_ENTRY);
            if(de == DEAL_ENTRY_OUT || de == DEAL_ENTRY_INOUT)
               { closePrice = HistoryDealGetDouble(dTkt, DEAL_PRICE); break; }
         }
         double slDist  = MathAbs(m_ctx.tradeSetup.entry - m_ctx.tradeSetup.stopLoss);
         double tp1Dist = MathAbs(m_ctx.tradeSetup.entry - m_ctx.tradeSetup.takeProfit1);
         double moveDist= (closePrice > 0) ? MathAbs(closePrice - m_ctx.tradeSetup.entry) : 0;
         Print(StringFormat(
            "[ASE][MGR] Position closed | HoldTime=%ds (%.1fmin) | Entry=%.5f SL=%.5f TP1=%.5f | "
            "ClosePrice=%.5f | MovedPts=%.2f SLdist=%.2f TP1dist=%.2f | "
            "ClosedAt=%.0f%% of SL / %.0f%% of TP1",
            (int)holdSecs, holdSecs/60.0,
            m_ctx.tradeSetup.entry, m_ctx.tradeSetup.stopLoss, m_ctx.tradeSetup.takeProfit1,
            closePrice, moveDist, slDist, tp1Dist,
            (slDist  > 0 ? moveDist/slDist*100  : 0),
            (tp1Dist > 0 ? moveDist/tp1Dist*100 : 0)));

         RecordClosedTrade();
         // v3.9.1 — post-trade bias handling.
         //
         // WIN:  retain bias fully — structure that produced the trade is
         //       still valid; allow re-entry after cooldown without needing
         //       a new BOS.
         //
         // LOSS: call RequireReconfirmation() instead of ResetH1Bias().
         //       Preserves bias direction and swing levels (no silent period)
         //       but sets a flag that blocks re-entry until the next fresh
         //       H1 BOS fires in the same direction. One confirming structural
         //       event is required before the pipeline can advance again.
         //       This prevents both immediate re-entry on a losing direction
         //       AND the indefinite silence caused by a full bias wipe.
         {
            double closePrice2 = (m_ctx.direction == DIR_LONG)
                                 ? CASE_Broker::GetBid()
                                 : CASE_Broker::GetAsk();
            bool tradeWon = (m_ctx.direction == DIR_LONG)
                            ? closePrice2 > m_ctx.tradeSetup.entry
                            : closePrice2 < m_ctx.tradeSetup.entry;
            if(!tradeWon)
            {
               // v3.12.1 Fix 1: pass the losing trade direction so StructureEngine
               // can hold it during the reconfirmation window, preventing the
               // post-loss pullback BOS from voting against the pre-loss direction
               // in the DirectionGate.
               m_structure.RequireReconfirmation(m_ctx.direction);
            }
            else
               CASE_Logger::Info("[ASE] H1 bias retained — trade closed in profit");
         }
         // v3.6.0 fix: was PERIOD_M5 — EA runs on M15 so cooldown must use
         // M15 bar duration. 5 bars × 900s = 75 min (was 5 × 300s = 25 min).
         m_cooldownEnd      = (datetime)(TimeCurrent() + InpCooldownBars * PeriodSeconds(PERIOD_M15));
         m_cooldownLastBeat = 0;
         m_ctx.Reset();
         CASE_Logger::Info(StringFormat("Cooldown started — %d M15 bars (%d min) | Resumes: %s",
                            InpCooldownBars,
                            InpCooldownBars * 15,
                            TimeToString(m_cooldownEnd, TIME_DATE|TIME_MINUTES)));
         Transition(STATE_COOLDOWN);
         return;
      }

      m_tel.UpdateExcursion();
      m_mgr.Manage(InpMagicNumber);

      // v3.14.17 Fix 24 — active-trade panel. Re-selects explicitly rather
      // than assuming the position is still selected from HasOpenPosition()
      // earlier this call — cheap, and doesn't depend on Manage()'s
      // internal selection state.
      for(int pv = PositionsTotal() - 1; pv >= 0; pv--)
      {
         ulong pvTkt = PositionGetTicket(pv);
         if(!PositionSelectByTicket(pvTkt)) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol ||
            PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
         m_tradeVis.UpdateTradePanel(
            m_ctx.direction == DIR_LONG,
            m_ctx.tradeSetup.entry,
            m_ctx.tradeSetup.stopLoss,
            PositionGetDouble(POSITION_SL),
            m_ctx.tradeSetup.takeProfit1,
            m_ctx.tradeSetup.takeProfit2,
            PositionGetDouble(POSITION_VOLUME));
         break;
      }

      // v3.14.6 Fix 9 — drain any partial fill that just occurred inside
      // Manage() this tick. Logs a PARTIAL_CLOSE row (so the CSV trade
      // count reconciles with the broker's deal count) and accumulates the
      // profit so RecordClosedTrade() can fold it into the trade's true
      // total when the runner eventually closes.
      ulong  partialTicket;
      double partialProfit;
      if(m_mgr.ConsumePartialProfit(partialTicket, partialProfit))
      {
         m_partialProfitAccum += partialProfit;
         m_partialTicketSeen   = partialTicket;   // v3.14.7 Fix 10
         // v3.14.8 Fix 12: partialTicket IS the position ticket (see
         // CASE_PartialTP::Process — PositionGetTicket, not a deal ticket),
         // logged here so this row and the trade's eventual TRADE row join
         // unambiguously on PositionID instead of on timestamp.
         m_stateLog.LogPartialClose(partialProfit, m_ctx,
                                     CASE_Broker::GetSpread(),
                                     m_ctx.regimeAtEntry.atr,
                                     partialTicket,
                                     m_profile.minScoreThreshold);
         Print(StringFormat(
            "[ASE][MGR] Partial close logged | Ticket=%llu | PartialProfit=%.2f | RunningAccum=%.2f",
            partialTicket, partialProfit, m_partialProfitAccum));
      }
      // FIX #9 — self-transition guard in Transition() prevents log noise;
      // stays in STATE_MANAGE cleanly.
   }

   //─────────────────────────────────────────────────────────────────
   void ProcessCooldown()
   {
      datetime now = TimeCurrent();

      if(now >= m_cooldownEnd)
      {
         CASE_Logger::Info("Cooldown complete — resuming");
         m_cooldownLastBeat = 0;

         // v3.11.0 — consume deferred daily reset (Fix 2).
         // If midnight fired while a trade was open, the reset was deferred.
         // Now that the trade is closed and cooldown is complete, execute it.
         if(m_pendingDailyReset)
         {
            m_pendingDailyReset = false;
            ExecuteDailyReset();
         }

         Transition(STATE_IDLE);
         return;
      }

      datetime currentBar = iTime(_Symbol, PERIOD_CURRENT, 0);
      if(currentBar != m_cooldownLastBeat)
      {
         m_cooldownLastBeat = currentBar;
         int secsLeft = (int)(m_cooldownEnd - now);
         int minsLeft = secsLeft / 60;
         CASE_Logger::Info(StringFormat(
            "Cooldown | %02d:%02d remaining | Resumes: %s",
            minsLeft / 60, minsLeft % 60,
            TimeToString(m_cooldownEnd, TIME_DATE|TIME_MINUTES)));
      }
   }

   //─────────────────────────────────────────────────────────────────
   // v3.11.0 — CheckDailyReset() (Fix 2)
   // Called every Update() pass. Detects when the server clock crosses
   // InpDailyResetHour UTC and triggers a pipeline reset if no position
   // is open. If a trade is active, sets m_pendingDailyReset so the
   // reset fires at the end of the subsequent cooldown instead.
   //
   // Implementation notes:
   //   - Uses MQL5 TimeGMT() (UTC) not TimeCurrent() (broker local time)
   //     so the reset hour is broker-timezone-independent.
   //   - m_lastDailyReset stores the last date the reset fired.
   //     Prevents firing multiple times within the same hour.
   //─────────────────────────────────────────────────────────────────
   void CheckDailyReset()
   {
      MqlDateTime gmt;
      TimeToStruct(TimeGMT(), gmt);

      // Only fire at InpDailyResetHour UTC, once per calendar day
      if(gmt.hour != InpDailyResetHour) return;

      // Build today's reset timestamp (start of the reset hour, UTC)
      datetime todayReset = StructToTime(gmt) - (gmt.min * 60) - gmt.sec;
      if(todayReset <= m_lastDailyReset) return;   // already fired today

      // Mark that this day's reset has been processed regardless of whether
      // we execute immediately or defer — prevents repeated trigger attempts
      // within the same hour window
      m_lastDailyReset = todayReset;

      if(HasOpenPosition())
      {
         // Defer: trade is live — set flag for end-of-cooldown consumption
         m_pendingDailyReset = true;
         Print(StringFormat("[ASE][RESET] Daily reset deferred — position open at %02d:00 UTC | "
               "will execute after trade closes and cooldown ends", InpDailyResetHour));
         return;
      }

      ExecuteDailyReset();
   }

   //─────────────────────────────────────────────────────────────────
   // ExecuteDailyReset() — core reset logic. Clears DirectionGate
   // state and bias block counters. Preserves H1 structural memory
   // (swing levels, BOS time) if still within staleness window.
   //─────────────────────────────────────────────────────────────────
   void ExecuteDailyReset()
   {
      // v3.13.0 — Cache D1 macro ceiling at daily reset.
      // GetMacroRegime() reads 20 D1 ATR bars — called ONCE per day here,
      // not on every H1 evaluation. Result stored in m_ctx.regimeAtEntry.macroRegime
      // and in RegimeEngine's internal m_cachedMacro; both are read by GetState()
      // to apply the ceiling gate without re-reading D1 buffers intra-day.
      ENUM_MACRO_REGIME macro = m_regime.GetMacroRegime();
      m_ctx.regimeAtEntry.macroRegime = macro;
      Print(StringFormat("[ASE][RESET] Macro ceiling cached: %s",
            m_regime.MacroRegimeName(macro)));

      // v3.11.1 fix: do NOT reset m_biasBlockCycles here.
      // Resetting it at midnight prevented the bias flip escalation
      // (InpBiasFlipCycles) from ever accumulating 3 blocks, causing
      // CheckBiasConfidence to block indefinitely on intra-day pullbacks.
      // The escalation counter must persist across midnight so the
      // flip escalation can fire and break out of a prolonged block.
      // m_biasBlockCycles = 0;  ← intentionally removed

      // Force both regime and structure to re-evaluate on the next ProcessHTF pass.
      m_htfBarReset = true;

      // Clear any pending DGate retry (retry is superseded by the full reset)
      m_dgateRetryPending = false;

      Print(StringFormat("[ASE][RESET] Daily pipeline reset executed at %02d:00 UTC | "
            "Macro=%s | BiasBlockCycles preserved (%d) | H1 structural memory preserved",
            InpDailyResetHour, m_regime.MacroRegimeName(macro), m_biasBlockCycles));

      Transition(STATE_IDLE);
   }

   //─────────────────────────────────────────────────────────────────
   bool HasOpenPosition()
   {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
            PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
            return true;
      }
      return false;
   }

   //─────────────────────────────────────────────────────────────────
   // v4.0.2 Phase 1 -- comparison-ledger join helpers. See
   // ASE_MAX_PENDING_COMPARE / ASE_COMPARE_JOIN_TIMEOUT_SECONDS above for
   // sizing rationale.
   //─────────────────────────────────────────────────────────────────
   void ClearCompareSlot(int i)
   {
      m_pendingCompareOppId[i]=""; m_pendingCompareArch[i]=""; m_pendingCompareRegime[i]="";
      m_pendingCompareR[i]=0.0; m_pendingCompareStamp[i]=0;
   }

   // Called once from each side of the "both" pair (the M15 theoretical
   // resolution when legacyTraded==true, and RecordClosedTrade() when the
   // entry snapshot has a real archetype). Whichever side arrives first
   // stashes its R keyed by oppId; whichever arrives second finds the
   // stash, combines both R values into one ComparisonLedger::Add() call,
   // and clears the slot. isV4Side=true means `rValue` is the V4
   // theoretical R; false means it is the legacy realised R.
   void StashOrResolveCompareBoth(const string oppId, const string archName, const string regimeName,
                                   bool isV4Side, double rValue, datetime now)
   {
      if(oppId=="") return;   // nothing to join on
      int idx=-1;
      for(int i=0;i<ASE_MAX_PENDING_COMPARE;i++)
         if(m_pendingCompareOppId[i]==oppId) { idx=i; break; }

      if(idx>=0)
      {
         double v4R     = isV4Side ? rValue : m_pendingCompareR[idx];
         double legacyR = isV4Side ? m_pendingCompareR[idx] : rValue;
         m_v4Analytics.RecordComparison(archName, regimeName, true, true, v4R, legacyR);
         ClearCompareSlot(idx);
         return;
      }

      int slot=-1;
      for(int i=0;i<ASE_MAX_PENDING_COMPARE;i++)
         if(m_pendingCompareOppId[i]=="") { slot=i; break; }
      if(slot<0)
      {
         datetime oldest=m_pendingCompareStamp[0]; slot=0;
         for(int i=1;i<ASE_MAX_PENDING_COMPARE;i++)
            if(m_pendingCompareStamp[i]<oldest) { oldest=m_pendingCompareStamp[i]; slot=i; }
         Print(StringFormat("[ACE v4] WARNING: comparison-join buffer full -- evicting unresolved oppId=%s to make room for oppId=%s",
               m_pendingCompareOppId[slot], oppId));
      }
      m_pendingCompareOppId[slot]=oppId; m_pendingCompareArch[slot]=archName; m_pendingCompareRegime[slot]=regimeName;
      m_pendingCompareR[slot]=rValue; m_pendingCompareStamp[slot]=now;
   }

   // Called once per M15 bar alongside ResolvePending() -- drops any join
   // slot whose other half never showed up within the timeout, logging a
   // one-line warning so a leak is visible rather than silent.
   void ExpireStaleCompareJoins(datetime now)
   {
      for(int i=0;i<ASE_MAX_PENDING_COMPARE;i++)
      {
         if(m_pendingCompareOppId[i]=="") continue;
         if(now - m_pendingCompareStamp[i] > ASE_COMPARE_JOIN_TIMEOUT_SECONDS)
         {
            Print(StringFormat("[ACE v4] WARNING: comparison join for oppId=%s (%s) timed out after %d bars-equivalent -- other side never arrived, discarding",
                  m_pendingCompareOppId[i], m_pendingCompareArch[i], (int)((now-m_pendingCompareStamp[i])/(15*60))));
            ClearCompareSlot(i);
         }
      }
   }

   //─────────────────────────────────────────────────────────────────
   // FIX #11 — HistorySelect window anchored to m_tradeOpenTime so
   //            trades closed after EA restart / gap open are found.
   // FIX #12 — Exit reason uses ATR-relative tolerance (not _Point*5)
   //            so GOLD and 5-digit brokers classify exits correctly.
   void RecordClosedTrade()
   {
      // FIX #11: use trade open time if available, else 24h back as safety net
      datetime fromTime = (m_tradeOpenTime > 0)
                          ? m_tradeOpenTime
                          : TimeCurrent() - 86400;
      HistorySelect(fromTime, TimeCurrent());

      int total = HistoryDealsTotal();
      for(int i = total - 1; i >= 0; i--)
      {
         ulong dTicket = HistoryDealGetTicket(i);
         if(HistoryDealGetString(dTicket, DEAL_SYMBOL)  != _Symbol)         continue;
         if(HistoryDealGetInteger(dTicket, DEAL_MAGIC)  != InpMagicNumber)  continue;
         ENUM_DEAL_ENTRY dealEntry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(dTicket, DEAL_ENTRY);\
         if(dealEntry != DEAL_ENTRY_OUT && dealEntry != DEAL_ENTRY_INOUT)   continue;

         // v3.14.7 Fix 10 — scope bug (measurement only, confirmed zero
         // impact on trading behavior/P&L; fixed for attribution integrity).
         // When a TP1 partial and the position's true final close land on
         // the same bar, this backward scan could find the PARTIAL deal
         // itself as "the most recent OUT deal" and misattribute it as the
         // final close — double-counting that leg's profit (once via
         // m_partialProfitAccum, once via this scan) while the true final
         // deal went unlogged. Confirmed via a 2026-01-01..07-23 audit:
         // 337 TRADE + 147 PARTIAL_CLOSE rows = 484 deal-attributions
         // against only 454 real closed deals, a 30-deal overlap matching
         // this exact mechanism. Skipping the ticket CASE_PartialTP already
         // claimed forces the scan to continue to the genuine final deal.
         if(dTicket == m_partialTicketSeen) continue;

         // v3.12.1 Fix 3: skip if we already logged this deal ticket.
         // Multiple ticks arrive at the same bar timestamp when a SL/TP
         // fires in the backtester. Without this guard each tick calls
         // RecordClosedTrade() independently, logging every trade 3×.
         if(dTicket == m_lastLoggedTicket)
         {
            Print(StringFormat("[ASE][MGR] Duplicate close detected for ticket %llu — skipping", dTicket));
            return;
         }
         m_lastLoggedTicket = dTicket;

         // v3.14.6 Fix 9: profit was previously ONLY the final (runner) leg's
         // realized P&L. Any TP1 partial that fired earlier in this trade's
         // life is folded in here via m_partialProfitAccum — confirmed missing
         // from every previously logged TRADE row that had a prior partial.
         double profit = HistoryDealGetDouble(dTicket, DEAL_PROFIT)
                       + HistoryDealGetDouble(dTicket, DEAL_SWAP)
                       + HistoryDealGetDouble(dTicket, DEAL_COMMISSION)
                       + m_partialProfitAccum;
         if(m_partialProfitAccum != 0.0)
            Print(StringFormat(
               "[ASE][MGR] Folding partial profit into final trade record | "
               "FinalLeg=%.2f | PartialAccum=%.2f | Total=%.2f",
               profit - m_partialProfitAccum, m_partialProfitAccum, profit));

         // FIX #12 — ATR-relative exit tolerance (5% of ATR)
         // Scales correctly across GOLD, indices, and FX.
         double closePrice = HistoryDealGetDouble(dTicket, DEAL_PRICE);
         double atrTol     = m_ctx.regimeAtEntry.atr * 0.05;
         if(atrTol < _Point * 3) atrTol = _Point * 3;   // hard floor for thin markets

         // Fix (2026-08-30): only trust the SL/TP/entry proximity checks
         // when this process actually opened the trade. A reconciled
         // position (m_positionSelfOpened == false) has zeroed
         // m_ctx.tradeSetup levels — every comparison below would fail
         // and previously fell through to EXIT_TRAIL by default, which
         // reported "trailing stop" for closes we genuinely have no
         // exit-mechanism evidence for.
         ENUM_EXIT_REASON exitReason = EXIT_UNKNOWN;
         if(!m_positionSelfOpened)
         {
            exitReason = EXIT_RECONCILED;
         }
         else if(MathAbs(closePrice - m_ctx.tradeSetup.stopLoss)        < atrTol) exitReason = EXIT_SL;
         else if(MathAbs(closePrice - m_ctx.tradeSetup.takeProfit2) < atrTol) exitReason = EXIT_TP2;
         else if(MathAbs(closePrice - m_ctx.tradeSetup.takeProfit1) < atrTol) exitReason = EXIT_TP1;
         else if(MathAbs(closePrice - m_ctx.tradeSetup.entry)       < atrTol) exitReason = EXIT_BREAKEVEN;
         else exitReason = EXIT_TRAIL;

         TradeRecord rec;
         rec.ticket        = dTicket;
         rec.timestamp     = (datetime)HistoryDealGetInteger(dTicket, DEAL_TIME);
         rec.symbol        = _Symbol;
         rec.session       = m_ctx.sessionAtEntry;
         rec.h4Bias        = (m_ctx.direction == DIR_LONG) ? "Bullish" : "Bearish";
         rec.m15SetupClass = m_ctx.m15SetupClass;
         rec.m1TriggerClass= m_ctx.m1TriggerClass;
         rec.liquidityType = m_ctx.liquidityType;    // FIX #4 — now populated
         // v3.4.9 fix (Fix 3): Use snapshot values for fields that may
         // have been corrupted by mid-manage ATR=0 glitches. Fields that
         // come from broker history (profit, closePrice, ticket) are still
         // read live. m_ctx.tradeSetup.entry/sl/tp are set once at
         // execution and not overwritten so remain safe to read directly.
         rec.entryScore    = m_snapScore;            // snapshot — immune to corruption
         rec.h4Score       = m_ctx.scoreCard.h4Bias;
         rec.m15Score      = m_ctx.scoreCard.m15Setup;
         rec.m1Score       = m_ctx.scoreCard.m1Trigger;
         rec.liqScore      = m_ctx.scoreCard.liquidity;
         rec.volScore      = m_ctx.scoreCard.volatility;
         rec.spread        = CASE_Broker::GetSpread();
         rec.atr           = m_snapATR;              // snapshot — immune to ATR=0 corruption
         rec.regime        = m_snapRegime;           // snapshot — immune to regime reclassification
         rec.entry         = m_ctx.tradeSetup.entry;
         rec.sl            = m_ctx.tradeSetup.stopLoss;
         rec.tp1           = m_ctx.tradeSetup.takeProfit1;
         rec.tp2           = m_ctx.tradeSetup.takeProfit2;
         rec.lotSize       = m_ctx.tradeSetup.lotSize;
         rec.rr            = m_snapRR;               // snapshot — immune to Reset() zeroing
         rec.exitReason    = exitReason;
         rec.profit        = profit;
         rec.result        = (profit > 0.01) ? "WIN" : (profit < -0.01) ? "LOSS" : "BE";
         // v4.0.2 -- attribute from the entry snapshot (live V4 fields have
         // been overwritten by every tick since entry).
         rec.v4OpportunityId=m_v4EntryValid ? m_v4EntryOppId : "";
         rec.v4Archetype=ASE_ArchetypeName(m_v4EntryConf.archetype);
         rec.v4Grade=ASE_GradeName(m_v4EntryConf.grade);
         rec.v4LongScore=m_v4EntryConf.longScore; rec.v4ShortScore=m_v4EntryConf.shortScore;
         rec.v4Separation=m_v4EntryConf.separation; rec.v4SequenceQuality=m_v4EntryConf.sequenceQuality;
         rec.v4Decision=m_v4ExecutedByV4 ? "V4_EXECUTED" : "LEGACY_EXECUTED";
         rec.v4EvidenceToConfluenceMs=(m_v4EvidenceTick>0 && m_v4ConfluenceTick>=m_v4EvidenceTick)?(int)(m_v4ConfluenceTick-m_v4EvidenceTick):0;
         rec.v4ConfluenceToExecutionMs=(m_v4ConfluenceTick>0 && m_v4ExecutionTick>=m_v4ConfluenceTick)?(int)(m_v4ExecutionTick-m_v4ConfluenceTick):0;
         rec.v4TotalEntryLatencyMs=rec.v4EvidenceToConfluenceMs+rec.v4ConfluenceToExecutionMs+m_ctx.execLatencyMs;

         // v4.0.2 -- realised R for EVERY closed trade, independent of V4
         // attribution. Realised P/L (incl. partials) / money at risk, via
         // tick value/size. riskMoney<=0 (no SL/lot, e.g. reconciled) => R unknown.
         double riskDist=MathAbs(m_ctx.tradeSetup.entry-m_ctx.tradeSetup.stopLoss);
         if(riskDist<=0.0) riskDist=MathMax(m_ctx.regimeAtEntry.atr, _Point);   // pre-existing fallback retained
         double tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
         double tickValue=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
         double riskMoney=(tickSize>0.0 && tickValue>0.0)
                          ? (riskDist/tickSize)*tickValue*m_ctx.tradeSetup.lotSize : 0.0;
         double realisedR=(riskMoney>0.0) ? rec.profit/riskMoney : 0.0;
         rec.realisedR=realisedR;
         m_lastClosedRealisedR=realisedR;

         m_tel.CommitTradeRecord(rec);

         if(profit >= 0) m_tel.RecordWin(profit, m_ctx.tradeSetup.rr);
         else            m_tel.RecordLoss(profit, m_ctx.tradeSetup.rr);

         // v4.0.2 -- V4 learning attribution from the entry snapshot. Legacy
         // trades V4 classified ARCH_NONE still do not reach RecordOutcome.
         // v4.0.2 Phase 1 -- ARCH_NONE and unqualified-but-classified legacy
         // trades ARE now routed to the comparison ledger below, so V4's
         // adaptive weighting stays untouched (per Phase 0's boundary) while
         // the comparison view finally captures what used to be dropped.
         if(InpAceV4Mode >= ACEV4_EVIDENCE && m_v4EntryValid && m_v4EntryConf.archetype != ARCH_NONE)
         {
            // v4.0.2 -- never feed raw money as "R" (old fallback when riskMoney==0)
            if(riskMoney<=0.0)
               Print(StringFormat("[ACE v4] WARNING: risk unknown for ticket %I64u -- outcome NOT recorded to adaptive engine", dTicket));
            else
            {
               bool oos=m_v4Adaptive.IsOOS(rec.timestamp,m_v4EntryOppId);
               m_v4Adaptive.RecordOutcome(m_v4EntryConf.archetype,realisedR,oos,m_v4EntryHasLiq,
                                          (ENUM_MARKET_REGIME)m_v4EntryRegime,m_v4EntryConf.enhancerMask,m_v4EntryConf.evaluatedMask);
               if(m_v4ShadowAEligible) m_v4Adaptive.RecordShadowOutcome(m_v4EntryConf.archetype,0,realisedR,oos);
               if(m_v4ShadowBEligible) m_v4Adaptive.RecordShadowOutcome(m_v4EntryConf.archetype,1,realisedR,oos);

               // v4.0.2 Phase 1 -- classified AND V4-qualified: this is the
               // ledger's "both" cell. Join against the theoretical R via
               // oppId (whichever side -- this close, or the M15 theoretical
               // resolution -- arrives first stashes; the second combines).
               // Classified but NOT V4-qualified (grade FAIL/C): legacyOnly
               // on this archetype's own row, using the real R directly --
               // there is no V4 theoretical side to join against because
               // wouldQualify==false is exactly the condition under which
               // the M15 loop above skips its join for this oppId.
               string regimeName=m_regime.RegimeName((ENUM_MARKET_REGIME)m_v4EntryRegime);
               if(m_v4EntryConf.qualified)
                  StashOrResolveCompareBoth(m_v4EntryOppId, ASE_ArchetypeName(m_v4EntryConf.archetype), regimeName, false, realisedR, rec.timestamp);
               else
                  m_v4Analytics.RecordComparison(ASE_ArchetypeName(m_v4EntryConf.archetype), regimeName, false, true, 0.0, realisedR);
            }
         }
         else if(InpAceV4Mode >= ACEV4_EVIDENCE && m_v4EntryValid && m_v4EntryConf.archetype == ARCH_NONE && riskMoney>0.0)
         {
            // v4.0.2 Phase 1 -- NoClass row: V4 had nothing to offer (no
            // archetype completed), legacy traded anyway. legacyOnly, using
            // the real R. riskMoney<=0.0 is excluded -- realisedR would be
            // the unreliable 0.0 fallback, not a genuine flat outcome.
            m_v4Analytics.RecordComparison("NoClass", "", false, true, 0.0, realisedR);
         }
         m_v4OpportunityOpen=false;
         m_v4EntryValid=false;   // v4.0.2 -- snapshot consumed
         m_attr.Enrich(rec, m_ctx, rec.timestamp);
         m_attr.Export(rec);
         m_wf.AddTrade(rec.timestamp, profit, m_ctx.tradeSetup.rr);

         // v3.8.0 — check for WF live degradation warning after each trade batch
         if(m_wf.HasDegradationWarning())
         {
            int    wfWindows = m_wf.GetWindowCount();
            double lastWR    = (wfWindows > 0)
                               ? m_wf.GetWindow(wfWindows - 1).wrRetention
                               : 0.0;
            m_alert.WFDegradation(lastWR);
            m_wf.ClearDegradationWarning();
         }

         m_mc.AddTrade(profit, MathAbs(m_ctx.tradeSetup.entry - m_ctx.tradeSetup.stopLoss));

         // v3.4.9: use snapshot direction/RR/ATR for TRADE row
         // v3.14.2 Fix 1: pass regime-specific threshold so TRADE rows log the
         // actual gate that was applied, not the global InpScoreThreshold.
         // v3.14.7 Fix 11: rec.maePct/mfePct were already computed by
         // CASE_Telemetry and previously only reached a Print() line —
         // now passed through to the CSV so excursion analysis is possible
         // in bulk across a full backtest.
         // v3.14.8 Fix 12: DEAL_POSITION_ID on the final closing deal is
         // the SAME position ticket CASE_PartialTP captured for any
         // partial on this trade — the unambiguous join key between this
         // row and a preceding PARTIAL_CLOSE row.
         ulong positionId = (ulong)HistoryDealGetInteger(dTicket, DEAL_POSITION_ID);
         m_stateLog.LogTrade(m_snapDirection, rec.result, profit, m_snapRR,
                              m_ctx, rec.spread, m_snapATR,
                              m_profile.minScoreThreshold,
                              rec.maePct, rec.mfePct, positionId);
         m_partialProfitAccum = 0.0;   // v3.14.6 Fix 9 — consumed, reset for next trade
         m_partialTicketSeen  = 0;     // v3.14.7 Fix 10 — consumed, reset for next trade

         CASE_Logger::Trade(StringFormat("Closed | %s | Profit=%.2f | Exit=%s | MAE=%.1f%% MFE=%.1f%% | WR=%.1f%%",
                            rec.result, profit, EnumToString(exitReason),
                            rec.maePct, rec.mfePct, m_tel.GetWinRate()));
         m_tradeOpenTime      = 0;       // reset for next trade
         m_positionSelfOpened = false;   // Fix (2026-08-30): fail-closed until next real open
         break;
      }
   }
};
#endif // ASE_STATEMACHINE_MQH
