#ifndef ASE_STATELOGGER_MQH
#define ASE_STATELOGGER_MQH

//+------------------------------------------------------------------+
//| ASE_StateLogger.mqh                                              |
//| Daily CSV logger for all state machine events.                   |
//| One file per day per symbol/TF — used for threshold calibration. |
//|                                                                  |
//| Output columns (all calibration-relevant):                       |
//|   Timestamp, EventType, Stage, StateFrom, StateTo,               |
//|   Direction, Session, Regime, Reason,                            |
//|   Score_H4, Score_M15, Score_M1, Score_Liq, Score_Vol,          |
//|   Score_Total, Threshold, Spread, ATR,                           |
//|   Param_MaxSpread, Param_ScoreThreshold, Param_RegimeFilter      |
//|                                                                  |
//| Files land in: <CommonFiles>\ASE_StateLogs\                      |
//| Naming:  ASE_v3_XAUUSD_M15_2026.05.21.csv                       |
//+------------------------------------------------------------------+

#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Enums.mqh"
#include "../Models/ASE_Config.mqh"

class CASE_StateLogger
{
private:
   int      m_handle;
   datetime m_fileDate;
   string   m_filePrefix;

   //----------------------------------------------------------------
   string BuildPath(datetime dt)
   {
      MqlDateTime t;
      TimeToStruct(dt, t);
      return StringFormat("ASE_StateLogs\\%s_%04d.%02d.%02d.csv",
                          m_filePrefix, t.year, t.mon, t.day);
   }

   //----------------------------------------------------------------
   void OpenFile(datetime dt)
   {
      if(m_handle != INVALID_HANDLE)
      {
         FileClose(m_handle);
         m_handle = INVALID_HANDLE;
      }

      string path  = BuildPath(dt);
      bool   isNew = !FileIsExist(path, FILE_COMMON);

      // Ensure subdirectory exists — MT5 will not auto-create it
      if(!FolderCreate("ASE_StateLogs", FILE_COMMON))
      {
         int err = GetLastError();
         if(err != 5018)  // 5018 = already exists, safe to ignore
            Print("[StateLogger] WARNING — FolderCreate: ", err);
      }

      m_handle = FileOpen(path,
                          FILE_WRITE | FILE_READ | FILE_CSV |
                          FILE_COMMON | FILE_SHARE_READ,
                          ',');

      if(m_handle == INVALID_HANDLE)
      {
         Print("[StateLogger] ERROR — could not open: ", path,
               " | Error: ", GetLastError());
         return;
      }

      FileSeek(m_handle, 0, SEEK_END);   // always append

      if(isNew) WriteHeader();

      m_fileDate = dt;
      Print("[StateLogger] Active log: ", path);
   }

   //----------------------------------------------------------------
   void WriteHeader()
   {
      FileWrite(m_handle,
         "Timestamp",
         "EventType",
         "Stage",
         "StateFrom",
         "StateTo",
         "Direction",
         "Session",
         "Regime",
         "MacroRegime",        // v3.13.0 — D1 ceiling classification
         "Reason",
         "SetupClass",
         "TriggerClass",
         "Score_H4",
         "Score_M15",
         "Score_M1",
         "Score_Liq",
         "Score_Vol",
         "Score_Total",
         "Threshold",
         "Spread",
         "ATR",
         "Param_MaxSpread",
         "Param_ScoreThreshold",
         "Param_RegimeFilter"
      );
   }

   //----------------------------------------------------------------
   void CheckRollover()
   {
      datetime    now = TimeCurrent();
      MqlDateTime cur, old;
      TimeToStruct(now,        cur);
      TimeToStruct(m_fileDate, old);

      if(cur.year != old.year || cur.mon != old.mon || cur.day != old.day)
         OpenFile(now);
   }

   //----------------------------------------------------------------
   string DirectionStr(int dir)
   {
      if(dir == DIR_LONG)  return "LONG";
      if(dir == DIR_SHORT) return "SHORT";
      return "NONE";
   }

   //----------------------------------------------------------------
   // SanitiseReason — replace commas with semicolons so the reason
   // string never adds extra fields to the CSV row.
   // Root cause of the 2026.05.26 bad-line bug: reason strings such
   // as "EMA falling hard (-1.07) | dist=-0.89ATR" were being written
   // verbatim, but commas inside them (e.g. from score descriptions)
   // caused pandas to see 24 columns instead of 23 and skip the row.
   string SanitiseReason(string s)
   {
      StringReplace(s, ",", ";");
      return s;
   }

   //----------------------------------------------------------------
   // Central write — all public methods funnel through here.
   // v3.14.2 Fix 1: effectiveThreshold is the regime-specific gate value
   // actually used in the scoring decision (m_profile.minScoreThreshold,
   // reduced by 8 during RequireReconfirmation). Previously this column
   // was always InpScoreThreshold (the global input default), making it
   // impossible to tell from the CSV whether a trade passed a tighter
   // COMPRESSION/MANIPULATION gate or a looser RANGING gate.
   // Callers that do not yet know the effective threshold pass -1.0 and
   // the column falls back to InpScoreThreshold for backwards compat.
   void WriteRow(
      string                     eventType,
      string                     stage,
      string                     stateFrom,
      string                     stateTo,
      const ASE_PipelineContext& ctx,
      string                     reason,
      double                     spread,
      double                     atr,
      string                     setupClass        = "",
      string                     triggerClass      = "",
      double                     effectiveThreshold = -1.0)
   {
      if(m_handle == INVALID_HANDLE) return;
      CheckRollover();

      string regime = (ctx.regimeAtEntry.regime != 0)
                    ? EnumToString((ENUM_MARKET_REGIME)ctx.regimeAtEntry.regime)
                    : "";

      // v3.13.0 — D1 macro ceiling label
      string macroRegime = (ctx.regimeAtEntry.macroRegime != 0)
                         ? EnumToString((ENUM_MACRO_REGIME)ctx.regimeAtEntry.macroRegime)
                         : "";

      string sc = (setupClass   != "") ? setupClass   : ctx.m15SetupClass;
      string tc = (triggerClass != "") ? triggerClass : ctx.m1TriggerClass;

      // v3.14.2 Fix 1: use the regime-specific effective threshold when
      // provided; fall back to global InpScoreThreshold for callers that
      // don't have it in scope (e.g. LogBlock from non-scoring paths).
      double logThreshold = (effectiveThreshold >= 0.0) ? effectiveThreshold : InpScoreThreshold;

      // Sanitise reason: commas inside reason strings corrupt CSV rows
      string safeReason = SanitiseReason(reason);

      FileWrite(m_handle,
         TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
         eventType,
         stage,
         stateFrom,
         stateTo,
         DirectionStr(ctx.direction),
         ctx.sessionAtEntry,
         regime,
         macroRegime,
         safeReason,
         sc,
         tc,
         DoubleToString(ctx.scoreCard.h4Bias,     1),
         DoubleToString(ctx.scoreCard.m15Setup,   1),
         DoubleToString(ctx.scoreCard.m1Trigger,  1),
         DoubleToString(ctx.scoreCard.liquidity,  1),
         DoubleToString(ctx.scoreCard.volatility, 1),
         DoubleToString(ctx.scoreCard.total,      1),
         DoubleToString(logThreshold,             1),
         DoubleToString(spread,                   1),
         DoubleToString(atr,                      5),
         IntegerToString(InpMaxSpread),
         DoubleToString(logThreshold,             1),
         (InpRegimeFilterEnabled ? "ON" : "OFF")
      );
   }

public:
   //----------------------------------------------------------------
   CASE_StateLogger() : m_handle(INVALID_HANDLE), m_fileDate(0) {}

   //----------------------------------------------------------------
   ~CASE_StateLogger() { Deinitialize(); }

   //----------------------------------------------------------------
   void Initialize(string symbol, ENUM_TIMEFRAMES tf, string version)
   {
      if(!InpStateLogEnabled)
      {
         Print("[StateLogger] Logging DISABLED (InpStateLogEnabled=false) — no CSV files will be written.");
         return;   // m_handle stays INVALID_HANDLE; all WriteRow calls are no-ops
      }

      Print("[StateLogger] Initialize called for ", symbol, " ", EnumToString(tf));

      // Build prefix:  e.g. ASE_v3_XAUUSD_M15
      string tfStr = EnumToString(tf);
      StringReplace(tfStr, "PERIOD_", "");   // strip "PERIOD_" prefix

      m_filePrefix = StringFormat("%s_%s_%s", version, symbol, tfStr);
      OpenFile(TimeCurrent());
   }

   //----------------------------------------------------------------
   void Deinitialize()
   {
      if(m_handle != INVALID_HANDLE)
      {
         FileClose(m_handle);
         m_handle = INVALID_HANDLE;
      }
   }

   //----------------------------------------------------------------
   // Called from Transition() on every genuine state change.
   // Note: identity guard in Transition() means this never fires
   // for same-state self-transitions.
   void LogTransition(
      ENUM_ASE_STATE             stateFrom,
      ENUM_ASE_STATE             stateTo,
      const ASE_PipelineContext& ctx,
      double                     spread,
      double                     atr)
   {
      WriteRow("TRANSITION",
               EnumToString(stateFrom),   // Stage = where we came from
               EnumToString(stateFrom),
               EnumToString(stateTo),
               ctx, "",
               spread, atr);
   }

   //----------------------------------------------------------------
   // Called from the LogBlock() wrapper in StateMachine on every
   // gate rejection. StateTo is left empty — pipeline did not advance.
   void LogBlock(
      string                     stage,
      string                     reason,
      const ASE_PipelineContext& ctx,
      double                     spread,
      double                     atr)
   {
      WriteRow("BLOCK",
               stage,
               stage,
               "",
               ctx, reason,
               spread, atr);
   }

   //----------------------------------------------------------------
   // Called from ProcessSetup() on every M15 bar evaluation —
   // regardless of pass/fail. This is the primary calibration record:
   // every setup the EA considered, with its score and outcome.
   // result: "PASS" | "FAIL"
   void LogSetup(
      string                     setupClass,
      string                     result,
      string                     reason,
      const ASE_PipelineContext& ctx,
      double                     spread,
      double                     atr)
   {
      WriteRow("SETUP_EVAL",
               "STATE_WAIT_SETUP",
               "STATE_WAIT_SETUP",
               (result == "PASS") ? "STATE_WAIT_TRIGGER" : "STATE_IDLE",
               ctx,
               result + (reason != "" ? " | " + reason : ""),
               spread, atr,
               setupClass, "");
   }

   //----------------------------------------------------------------

   //----------------------------------------------------------------
   // LogTriggerEval — called from ProcessTrigger() AFTER all score
   // components (vol, session, spread) are set and Validate() has
   // computed scoreCard.total. Captures the complete scorecard for
   // every trigger decision. Fixes Score_Total/Liq/Vol always being
   // 0 in SETUP_EVAL (those fire before ProcessTrigger runs).
   // result: "PASS" | "LIQ_FAIL" | "TRIG_FAIL" | "SCORE_FAIL"
   // v3.14.2 Fix 1: effectiveThreshold added so TRIGGER_EVAL rows log the
   // regime-specific gate value (e.g. 72 for COMPRESSION, 75 for MANIPULATION)
   // rather than always showing the global InpScoreThreshold default.
   void LogTriggerEval(
      string                     result,
      string                     reason,
      const ASE_PipelineContext& ctx,
      double                     spread,
      double                     atr,
      double                     effectiveThreshold = -1.0)
   {
      WriteRow("TRIGGER_EVAL",
               "STATE_WAIT_TRIGGER",
               "STATE_WAIT_TRIGGER",
               (result == "PASS") ? "STATE_WAIT_EXECUTION" : "STATE_IDLE",
               ctx,
               result + (reason != "" ? " | " + reason : ""),
               spread, atr,
               ctx.m15SetupClass,
               ctx.m1TriggerClass,
               effectiveThreshold);
   }

   // Called from RecordClosedTrade() to stamp trade outcomes in the
   // same daily file — allows direct correlation with prior state events.
   //
   // v3.4.5 fix: LogTrade() previously wrote Score_Total and ATR from
   // stale / incorrect values (observed as Score_Total=55 and ATR=65.0
   // in TRADE rows on 2026-06-02 and 2026-06-03 logs). Root cause:
   // columns were not aligned with WriteHeader() order. The two extra
   // columns (SetupClass, TriggerClass) that WriteRow() inserts between
   // Reason and Score_H4 were absent in the raw FileWrite() here,
   // shifting every subsequent column two positions left. Fix: add the
   // missing SetupClass and TriggerClass fields to restore alignment,
   // and route through the central WriteRow() helper so future header
   // changes are automatically reflected.
   //
   // v3.14.2 Fix 1: regimeThreshold added — the regime-specific gate
   // value used when this trade was approved (e.g. 72 for COMPRESSION).
   // Callers pass m_profile.minScoreThreshold. Default -1.0 falls back
   // to InpScoreThreshold for backwards compatibility.
   void LogTrade(
      string                     direction,
      string                     result,
      double                     profit,
      double                     rr,
      const ASE_PipelineContext& ctx,
      double                     spread,
      double                     atr,
      double                     regimeThreshold = -1.0)
   {
      if(m_handle == INVALID_HANDLE) return;
      CheckRollover();

      string regime = (ctx.regimeAtEntry.regime != 0)
                    ? EnumToString((ENUM_MARKET_REGIME)ctx.regimeAtEntry.regime)
                    : "";

      // v3.13.0 — D1 macro ceiling for TRADE row
      string macroRegime = (ctx.regimeAtEntry.macroRegime != 0)
                         ? EnumToString((ENUM_MACRO_REGIME)ctx.regimeAtEntry.macroRegime)
                         : "";

      string reason = SanitiseReason(
         StringFormat("result=%s profit=%.2f rr=%.2f", result, profit, rr));

      // v3.14.2 Fix 1: log the regime-specific threshold when provided
      double logThreshold = (regimeThreshold >= 0.0) ? regimeThreshold : InpScoreThreshold;

      // Route through FileWrite directly (not WriteRow) because TRADE rows
      // use fixed StateFrom/StateTo strings that differ from the pattern
      // WriteRow expects — but now include SetupClass + TriggerClass to
      // match the 24-column CSV header exactly (v3.13.0: +MacroRegime).
      FileWrite(m_handle,
         TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),  // Timestamp
         "TRADE",                                                 // EventType
         "EXECUTION",                                             // Stage
         "STATE_WAIT_EXECUTION",                                  // StateFrom
         "STATE_POSITION_OPEN",                                   // StateTo
         direction,                                               // Direction
         ctx.sessionAtEntry,                                      // Session
         regime,                                                  // Regime
         macroRegime,                                             // MacroRegime  ← v3.13.0
         reason,                                                  // Reason
         ctx.m15SetupClass,                                       // SetupClass
         ctx.m1TriggerClass,                                      // TriggerClass
         DoubleToString(ctx.scoreCard.h4Bias,     1),             // Score_H4
         DoubleToString(ctx.scoreCard.m15Setup,   1),             // Score_M15
         DoubleToString(ctx.scoreCard.m1Trigger,  1),             // Score_M1
         DoubleToString(ctx.scoreCard.liquidity,  1),             // Score_Liq
         DoubleToString(ctx.scoreCard.volatility, 1),             // Score_Vol
         DoubleToString(ctx.scoreCard.total,      1),             // Score_Total
         DoubleToString(logThreshold,             1),             // Threshold
         DoubleToString(spread,                   1),             // Spread
         DoubleToString(atr,                      5),             // ATR
         IntegerToString(InpMaxSpread),                           // Param_MaxSpread
         DoubleToString(logThreshold,             1),             // Param_ScoreThreshold
         (InpRegimeFilterEnabled ? "ON" : "OFF")                  // Param_RegimeFilter
      );
   }
};

#endif // ASE_STATELOGGER_MQH
