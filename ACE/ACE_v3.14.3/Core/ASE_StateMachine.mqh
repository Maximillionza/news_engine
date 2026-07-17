#ifndef ASE_STATEMACHINE_MQH
#define ASE_STATEMACHINE_MQH
#include <Trade/Trade.mqh>

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
   datetime               m_cooldownEnd;
   datetime               m_tradeOpenTime;
   bool                   m_htfBarReset;      // true = force H4 re-eval on next ProcessHTF()
   bool                   m_wasOffSession;     // v3.4.7: throttle off-session journal prints
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

   // v3.14.9 Fix 10: H4 EMA handles for CalcH4HybridScore().
   // DirectionGate held these (m_h4FastHandle / m_h4SlowHandle) but was removed
   // in v3.12.3. They must be owned here so the hybrid scoring method can read
   // H4 EMA20 vs EMA50 spread for the convergence-against-trade penalty.
   int                    m_h4FastHybridHandle;   // H4 EMA20 (InpH4FastEMA)
   int                    m_h4SlowHybridHandle;   // H4 EMA50 (InpH4SlowEMA)

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

public:
   CASE_StateMachine() : m_state(STATE_IDLE), m_cooldownEnd(0), m_cooldownLastBeat(0), m_tradeOpenTime(0), m_htfBarReset(false), m_wasOffSession(false), m_biasBlockCycles(0),
                    m_snapRR(0.0), m_snapScore(0.0), m_snapATR(0.0),
                    m_lastDailyReset(0), m_pendingDailyReset(false), m_dgateRetryPending(false),
                    m_lastLoggedTicket(0), m_lastH1EvalDate(0),
                    m_h4FastHybridHandle(INVALID_HANDLE), m_h4SlowHybridHandle(INVALID_HANDLE)
   {
      // v3.14.0 — initialise profile to safe defaults at construction so
      // any accidental read before first H1 bar doesn't use garbage values.
      ZeroMemory(m_profile);
      m_profile = LoadProfile(REGIME_COMPRESSION);  // conservative baseline
   }

   //─────────────────────────────────────────────────────────────────
   // v3.14.7 — Reinit-survival persistence.
   //
   // Root cause (06.29 log audit): any EA reinitialization while a trade
   // is open or a cooldown is running — recompiling a build, changing an
   // input via Properties, reattaching to the chart — runs Initialize(),
   // which unconditionally does m_ctx.Reset() and m_state=STATE_IDLE
   // (unchanged below). A full module reload (recompile) also re-runs
   // this constructor, zeroing m_cooldownEnd and the entry-time snapshot
   // fields. Confirmed effect in the 06.29 log: a trade closed at
   // 21:53:32 with Direction=NONE and no "TRADE" CSV row ever written for
   // it — RecordClosedTrade()/LogTrade() had no valid entry/direction/
   // timing data left to work with. Separately, the cooldown that should
   // have started at 21:53:32 lasted 34 seconds instead of the configured
   // window — consistent with m_cooldownEnd having been zeroed by the
   // same event.
   //
   // Fix: persist the handful of fields needed to (a) correctly attribute
   // win/loss and reconfirmation direction, (b) keep RecordClosedTrade()
   // able to locate and classify the closing deal, and (c) keep the
   // cooldown timer intact — to terminal GlobalVariables, which survive
   // recompiles, input changes, and even terminal restarts — and restore
   // them in Initialize(). This is pure bookkeeping: nothing here touches
   // scoring, gating, or entry/execution decision logic, so it has no
   // effect on whether/when trades fire.
   string GVKey(string field) { return StringFormat("ASE_%d_%s", InpMagicNumber, field); }

   void PersistOpenTradeSnapshot()
   {
      GlobalVariableSet(GVKey("OpenDir"),   (double)m_ctx.direction);
      GlobalVariableSet(GVKey("OpenEntry"), m_ctx.tradeSetup.entry);
      GlobalVariableSet(GVKey("OpenSL"),    m_ctx.tradeSetup.stopLoss);
      GlobalVariableSet(GVKey("OpenTP1"),   m_ctx.tradeSetup.takeProfit1);
      GlobalVariableSet(GVKey("OpenTP2"),   m_ctx.tradeSetup.takeProfit2);
      GlobalVariableSet(GVKey("OpenTime"),  (double)m_tradeOpenTime);
      GlobalVariableSet(GVKey("SnapRR"),    m_snapRR);
      GlobalVariableSet(GVKey("SnapScore"), m_snapScore);
      GlobalVariableSet(GVKey("SnapATR"),   m_snapATR);
   }

   void PersistCooldownEnd() { GlobalVariableSet(GVKey("CooldownEnd"), (double)m_cooldownEnd); }

   void ClearPersistedTradeSnapshot()
   {
      GlobalVariableDel(GVKey("OpenDir"));
      GlobalVariableDel(GVKey("OpenEntry"));
      GlobalVariableDel(GVKey("OpenSL"));
      GlobalVariableDel(GVKey("OpenTP1"));
      GlobalVariableDel(GVKey("OpenTP2"));
      GlobalVariableDel(GVKey("OpenTime"));
      GlobalVariableDel(GVKey("SnapRR"));
      GlobalVariableDel(GVKey("SnapScore"));
      GlobalVariableDel(GVKey("SnapATR"));
   }

   void ClearPersistedCooldown() { GlobalVariableDel(GVKey("CooldownEnd")); }

   // Restores cooldown + (if the broker confirms a position is genuinely
   // still open) the entry-time snapshot. Called once from Initialize().
   void RestorePersistedState()
   {
      if(GlobalVariableCheck(GVKey("CooldownEnd")))
      {
         datetime restored = (datetime)GlobalVariableGet(GVKey("CooldownEnd"));
         if(restored > TimeCurrent())
         {
            m_cooldownEnd = restored;
            Print(StringFormat("[ASE] Restored cooldown from prior session — resumes %s",
                  TimeToString(m_cooldownEnd, TIME_DATE|TIME_MINUTES)));
         }
         else
            GlobalVariableDel(GVKey("CooldownEnd"));  // stale/expired — do not carry forward
      }

      if(HasOpenPosition() && GlobalVariableCheck(GVKey("OpenEntry")))
      {
         m_ctx.direction              = (ENUM_TRADE_DIRECTION)(int)GlobalVariableGet(GVKey("OpenDir"));
         m_ctx.tradeSetup.entry       = GlobalVariableGet(GVKey("OpenEntry"));
         m_ctx.tradeSetup.stopLoss    = GlobalVariableGet(GVKey("OpenSL"));
         m_ctx.tradeSetup.takeProfit1 = GlobalVariableGet(GVKey("OpenTP1"));
         m_ctx.tradeSetup.takeProfit2 = GlobalVariableGet(GVKey("OpenTP2"));
         m_tradeOpenTime              = (datetime)GlobalVariableGet(GVKey("OpenTime"));
         m_snapRR                     = GlobalVariableGet(GVKey("SnapRR"));
         m_snapScore                  = GlobalVariableGet(GVKey("SnapScore"));
         m_snapATR                    = GlobalVariableGet(GVKey("SnapATR"));
         m_snapDirection              = (m_ctx.direction == DIR_LONG) ? "LONG" : "SHORT";
         Print(StringFormat(
            "[ASE] Restored open-trade context after reinit | dir=%s entry=%.5f — "
            "win/loss attribution and TRADE-row logging protected",
            m_snapDirection, m_ctx.tradeSetup.entry));
      }
   }

   //─────────────────────────────────────────────────────────────────
   bool Initialize()
   {
      Print("[ASE] StateMachine::Initialize() — start | Symbol=", _Symbol,
            " | Server=", TimeCurrent());

      m_diag.Initialize();
      m_tel.Initialize();
      m_optBridge.Initialize();
      m_vps.Initialize();   // FIX #1 — must init before Update() uses it
      m_ctx.Reset();
      m_state = STATE_IDLE;

      if(!m_regime.Initialize())    { Print("[ASE] RegimeEngine  init failed"); return false; }
      // v3.6.0 — m_bias.Initialize() removed (BiasEngine retired)
      if(!m_setup.Initialize())     { Print("[ASE] SetupEngine   init failed"); return false; }
      if(!m_trigger.Initialize())   { Print("[ASE] TriggerEngine init failed"); return false; }
      if(!m_liq.Initialize())       { Print("[ASE] LiquidityEng  init failed"); return false; }
      if(!m_structure.Initialize()) { Print("[ASE] StructureEng  init failed"); return false; }
      // v3.12.3: m_dgate removed
      // v3.14.9 Fix 10: H4 EMA handles for hybrid h4Bias scoring
      m_h4FastHybridHandle = iMA(_Symbol, PERIOD_H4, InpH4FastEMA, 0, MODE_EMA, PRICE_CLOSE);
      m_h4SlowHybridHandle = iMA(_Symbol, PERIOD_H4, InpH4SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
      if(m_h4FastHybridHandle == INVALID_HANDLE || m_h4SlowHybridHandle == INVALID_HANDLE)
      { Print("[ASE] H4 hybrid EMA handles init failed"); return false; }
      m_wf.Initialize();
      m_mc.Initialize();
      if(!m_risk.Initialize())      { Print("[ASE] RiskEngine    init failed"); return false; }
      if(!m_exec.Initialize())      { return false; }
      if(!m_mgr.Initialize())       { Print("[ASE] TradeManager  init failed"); return false; }

      // v3.4.4 — print effective session windows on startup so misconfigured
      // UTC times are caught immediately in the Experts tab before trading begins.
      m_session.PrintConfig();

      m_csv.Open("ASE_v3_trades.csv");
      m_stateLog.Initialize(_Symbol, PERIOD_CURRENT, "ASE_v3");

      // v4.0 — attribution engine
      if(!m_attr.Initialize())
      {
         Print("[ASE] TradeAttribution init failed — exports will be unavailable");
         // Non-fatal: EA continues without the three attribution output files
      }

      // v3.14.7 — restore cooldown/open-trade state that may have been
      // dropped by this very reinitialization (or a prior one).
      RestorePersistedState();

      Print("[ASE] StateMachine::Initialize() — complete");
      return true;
   }

   //─────────────────────────────────────────────────────────────────
   void Deinitialize()
   {
      m_regime.Deinitialize();
      // v3.6.0 — m_bias.Deinitialize() removed (BiasEngine retired)
      m_setup.Deinitialize();
      m_trigger.Deinitialize();
      m_risk.Deinitialize();
      m_mgr.Deinitialize();
      m_structure.Deinitialize();
      // v3.12.3: m_dgate removed
      // v3.14.9 Fix 10: release H4 hybrid EMA handles
      if(m_h4FastHybridHandle != INVALID_HANDLE) { IndicatorRelease(m_h4FastHybridHandle); m_h4FastHybridHandle = INVALID_HANDLE; }
      if(m_h4SlowHybridHandle != INVALID_HANDLE) { IndicatorRelease(m_h4SlowHybridHandle); m_h4SlowHybridHandle = INVALID_HANDLE; }

      m_wf.BuildWindows();
      m_wf.PrintReport();
      m_tel.PrintSummary();
      m_exec.PrintSummary();   // v4.0 — execution telemetry summary
      m_html.Export("ASE_v3_report.html", m_tel, m_wf);
      m_csv.Close();
      m_stateLog.Deinitialize();
      m_attr.Deinitialize();   // v4.0 — flush and close attribution streams
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

      // FIX #1 — VPS tick throttle: skip full pipeline evaluation if
      // nothing changed on M1. Bypass during position management so
      // SL/TP closes (which happen mid-bar in the tester and live) are
      // detected on the very next tick rather than at the next M1 bar open.
      bool managing = (m_state == STATE_MANAGE);
      if(!managing && !m_vps.ShouldProcess()) return;

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
      if(HasOpenPosition()) { Transition(STATE_MANAGE); return; }

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
   // v3.14.9 Fix 10 — H4 Hybrid Bias Score (replaces direct res.score assignment)
   //
   // Computes an H4 bias score on [0,10] from three independent signals:
   //
   //   Component 1 — H4 direction alignment (base score):
   //     H4 last closed bar aligns with trade direction → 7
   //     H4 last closed bar opposes trade direction    → 3
   //     H4 direction unknown / data fail              → 5 (neutral)
   //
   //   Component 2 — H4 candle body check (+3 bonus):
   //     Counter-body of last closed bar ≤ 30% of the prior trade-direction
   //     body → trend-structure intact → +3. Counter-body > 30% = probable
   //     reversal candle building → no bonus (score capped at base).
   //     "Counter-body": for LONG, the bearish portion of bar[1]; for SHORT,
   //     the bullish portion of bar[1]. Compared to the trade-direction body
   //     of bar[2] (the confirmed candle before the last closed one).
   //
   //   Component 3 — EMA spread convergence penalty (−2):
   //     If H4 EMA20 spread vs EMA50 is converging AGAINST the trade direction
   //     (fast EMA moving toward slow EMA in the wrong way), subtract 2.
   //     Corroborates a possible trend reversal forming on H4.
   //
   //   Score clamped to [0, 10]. Logged per evaluation with full breakdown.
   //
   // WHY 10 NOT 30:
   //   H4 bias was max 30/105 raw (28.5%) — it could single-handedly prevent
   //   a trade from reaching any threshold on fast-move days where H4 EMA had
   //   not yet crossed. Reducing to max 10/85 (~12%) makes H4 a genuine context
   //   signal that adds conviction without acting as a gate.
   //─────────────────────────────────────────────────────────────────
   double CalcH4HybridScore(ENUM_TRADE_DIRECTION dir)
   {
      // ── Read H4 OHLC: bar[0]=forming, bar[1]=last closed, bar[2]=prior ──
      double h4Op[], h4Cl[];
      ArraySetAsSeries(h4Op, true);
      ArraySetAsSeries(h4Cl, true);
      if(CopyOpen( _Symbol, PERIOD_H4, 0, 3, h4Op) < 3 ||
         CopyClose(_Symbol, PERIOD_H4, 0, 3, h4Cl) < 3)
      {
         Print("[ASE][H4][HYBRID] OHLC data fail — neutral score 5.0");
         return 5.0;
      }

      // ── Component 1: H4 direction alignment ─────────────────────────────
      ENUM_TRADE_DIRECTION h4Dir = m_structure.GetH4ClosedDirection();
      double score = 5.0;   // neutral default
      if(h4Dir == dir)             score = 7.0;
      else if(h4Dir != DIR_NONE)   score = 3.0;

      // ── Component 2: Counter-body (30% rule) ────────────────────────────
      // bar[2] = candle before last closed; bar[1] = last closed candle
      double prevDirBody     = 0.0;
      double currCounterBody = 0.0;
      string bodyLabel       = "";
      if(dir == DIR_LONG)
      {
         prevDirBody     = MathMax(h4Cl[2] - h4Op[2], 0.0);   // bullish body of bar[2]
         currCounterBody = MathMax(h4Op[1] - h4Cl[1], 0.0);   // bearish body of bar[1]
      }
      else if(dir == DIR_SHORT)
      {
         prevDirBody     = MathMax(h4Op[2] - h4Cl[2], 0.0);   // bearish body of bar[2]
         currCounterBody = MathMax(h4Cl[1] - h4Op[1], 0.0);   // bullish body of bar[1]
      }
      if(prevDirBody > 0.0)
      {
         double counterPct = currCounterBody / prevDirBody;
         if(counterPct <= 0.30) { score += 3.0; bodyLabel = "intact"; }
         else                     bodyLabel = StringFormat("counter=%.0f%%", counterPct * 100.0);
      }
      else
      {
         score += 3.0;   // doji prev bar — no prior trend body to violate, treat as OK
         bodyLabel = "no-prev-body";
      }

      // ── Component 3: EMA spread convergence penalty ──────────────────────
      string spreadLabel = "";
      if(m_h4FastHybridHandle != INVALID_HANDLE && m_h4SlowHybridHandle != INVALID_HANDLE)
      {
         double h4Fast[], h4Slow[];
         ArraySetAsSeries(h4Fast, true);
         ArraySetAsSeries(h4Slow, true);
         if(CopyBuffer(m_h4FastHybridHandle, 0, 0, 3, h4Fast) >= 3 &&
            CopyBuffer(m_h4SlowHybridHandle, 0, 0, 3, h4Slow) >= 3)
         {
            double spread1 = h4Fast[1] - h4Slow[1];   // bar[1] spread
            double spread2 = h4Fast[2] - h4Slow[2];   // bar[2] spread
            // Converging against trade direction:
            //   LONG  → spread should stay positive or grow; if spread1 < spread2, EMAs converging bearish
            //   SHORT → spread should stay negative or grow; if spread1 > spread2, EMAs converging bullish
            bool convergingAgainst = (dir == DIR_LONG  && spread1 < spread2) ||
                                     (dir == DIR_SHORT && spread1 > spread2);
            if(convergingAgainst) { score -= 2.0; spreadLabel = "converging-against"; }
            else                    spreadLabel = "spread-ok";
         }
         else spreadLabel = "buf-fail";
      }
      else spreadLabel = "no-handle";

      score = MathMax(MathMin(score, 10.0), 0.0);

      Print(StringFormat(
         "[ASE][H4][HYBRID] score=%.1f | h4Dir=%s trade=%s | body=%s (prev=%.5f ctr=%.5f) | ema=%s",
         score,
         h4Dir == DIR_LONG ? "L" : (h4Dir == DIR_SHORT ? "S" : "N"),
         dir  == DIR_LONG ? "L" : "S",
         bodyLabel, prevDirBody, currCounterBody, spreadLabel));
      return score;
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

      // v3.14.9 Fix 10: replace direct StructureEngine score with H4 hybrid bias score.
      // StructureEngine res.score (H1 BOS quality, 0-30) no longer drives h4Bias.
      // CalcH4HybridScore() produces a capped [0,10] signal from H4 direction
      // alignment + candle body check + EMA spread convergence penalty.
      m_ctx.scoreCard.h4Bias = CalcH4HybridScore(m_ctx.direction);
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
         LogBlock("SETUP", res.reason);
         Transition(STATE_IDLE);
         return;
      }

      m_stateLog.LogSetup(setupClass, "PASS", "", m_ctx, spread, atr);
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
      //
      // v3.14.5 FIX — made direction-aware. The original check used an
      // unsigned drift, so a fast FAVORABLE move (price continuing in the
      // signal's direction — exactly what a displacement/momentum trigger
      // is supposed to catch) aborted identically to an ADVERSE move. Audit
      // of three live sessions (06.23, 06.25) found this gate killed every
      // single setup that ever cleared the scoring threshold that day, and
      // in at least one case (06.25 16:16) the abort was triggered by
      // continuation in the trade's favor, not staleness. Structural levels
      // (freshLevels below) are recomputed off the live entry price either
      // way, so a favorably-drifted fill still gets correct SL/TP — only
      // adverse drift beyond the cap still aborts.
      if(InpSlippageGateATRMult > 0 && m_ctx.triggerClosePrice > 0 && m_ctx.triggerM1ATR > 0)
      {
         double livePrice  = (m_ctx.direction == DIR_LONG)
                             ? CASE_Broker::GetAsk()
                             : CASE_Broker::GetBid();
         // Signed, direction-relative drift: positive = price moved in the
         // signal's favor since the trigger bar closed; negative = adverse.
         double signedDrift = (m_ctx.direction == DIR_LONG)
                              ? (livePrice - m_ctx.triggerClosePrice)
                              : (m_ctx.triggerClosePrice - livePrice);
         double driftLimit  = m_ctx.triggerM1ATR * InpSlippageGateATRMult;
         if(signedDrift < -driftLimit)
         {
            LogBlock("EXECUTION", StringFormat(
               "Trigger-to-fill drift %.2f pts (adverse) > %.1f× M1ATR (%.2f pts) — stale trigger abort",
               -signedDrift, InpSlippageGateATRMult, driftLimit));
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
         m_mgr.SetTP1(m_ctx.tradeSetup.takeProfit1);
         m_tradeOpenTime = TimeCurrent();

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

         // v3.14.7 — make this snapshot survive a reinit mid-trade.
         PersistOpenTradeSnapshot();

         m_tel.StartTracking(
            m_ctx.tradeSetup.entry,
            m_ctx.tradeSetup.stopLoss,
            m_ctx.tradeSetup.takeProfit2,
            m_ctx.direction == DIR_LONG);
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
         // v3.14.7 — persist the fresh cooldown end and drop the now-closed
         // trade's snapshot so a reinit during this cooldown can't lose the
         // timer, and can't mistakenly restore a closed trade's context.
         PersistCooldownEnd();
         ClearPersistedTradeSnapshot();
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
         ClearPersistedCooldown();   // v3.14.7 — natural completion; nothing left to restore

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

         double profit = HistoryDealGetDouble(dTicket, DEAL_PROFIT)
                       + HistoryDealGetDouble(dTicket, DEAL_SWAP)
                       + HistoryDealGetDouble(dTicket, DEAL_COMMISSION);

         // FIX #12 — ATR-relative exit tolerance (5% of ATR)
         // Scales correctly across GOLD, indices, and FX.
         double closePrice = HistoryDealGetDouble(dTicket, DEAL_PRICE);
         double atrTol     = m_ctx.regimeAtEntry.atr * 0.05;
         if(atrTol < _Point * 3) atrTol = _Point * 3;   // hard floor for thin markets

         ENUM_EXIT_REASON exitReason = EXIT_UNKNOWN;
         if(MathAbs(closePrice - m_ctx.tradeSetup.stopLoss)        < atrTol) exitReason = EXIT_SL;
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

         m_tel.CommitTradeRecord(rec);

         if(profit >= 0) m_tel.RecordWin(profit, m_ctx.tradeSetup.rr);
         else            m_tel.RecordLoss(profit, m_ctx.tradeSetup.rr);

         // v4.0 — enrich the record with causal attribution fields,
         // then export to CSV + NDJSON + pipe-delimited SQLite ingest.
         // m_csv.Write() is superseded; ASE_TradeAttribution writes the
         // full-attribution CSV that includes all v4 columns.
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
         m_stateLog.LogTrade(m_snapDirection, rec.result, profit, m_snapRR,
                              m_ctx, rec.spread, m_snapATR,
                              m_profile.minScoreThreshold);

         CASE_Logger::Trade(StringFormat("Closed | %s | Profit=%.2f | Exit=%s | MAE=%.1f%% MFE=%.1f%% | WR=%.1f%%",
                            rec.result, profit, EnumToString(exitReason),
                            rec.maePct, rec.mfePct, m_tel.GetWinRate()));
         m_tradeOpenTime = 0;   // reset for next trade
         break;
      }
   }
};
#endif // ASE_STATEMACHINE_MQH
