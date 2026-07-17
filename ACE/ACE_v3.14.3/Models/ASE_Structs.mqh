#ifndef ASE_STRUCTS_MQH
#define ASE_STRUCTS_MQH
#include "ASE_Enums.mqh"
//+------------------------------------------------------------------+
//| ASE v3.3.0 / v4 — Core Structures                               |
//| v3.3.0 additions:                                                |
//|   TradeSetup  — signalPrice (Area B)                             |
//|   TradeRecord — signalPrice, actualFill, slippagePts,            |
//|                 slippagePct (Area B)                             |
//|   ASE_PipelineContext — entrySpreadPts (Area D)                  |
//| v4.0 additions (TradeAttribution §4):                            |
//|   TradeRecord — sessionSubtype, volatilityCluster,               |
//|                 inducementType, displacementType,                 |
//|                 latencyMs, adr, win                              |
//|                 timeToMAEMin, timeToMFEMin                       |
//| v3.6.0 additions:                                                |
//|   ASE_PipelineContext — triggerClosePrice, triggerM1ATR          |
//|     Entry timing slippage gate — captures M1 close and ATR at    |
//|     trigger time; ProcessExecution() aborts if live price has    |
//|     moved > 0.5× M1 ATR since the trigger bar closed.           |
//| v3.13.0 additions:                                               |
//|   RegimeState — macroRegime (ENUM_MACRO_REGIME)                  |
//|     D1 ceiling classification cached at daily reset.             |
//|     ZeroMemory-safe: MACRO_UNKNOWN = 0 is the safe default.      |
//+------------------------------------------------------------------+

struct ValidationResult
{
   bool   passed;
   string reason;
   double score;
};

// v4.0 — Structural TP levels surfaced from SetupEngine.
// Populated in ProcessSetup() and passed to RiskEngine.BuildSetup().
// Both levels are 0.0 when the setup type cannot derive a structural target
// (EMA_Pullback without a nearby H4 swing); RiskEngine falls back to ATR.
struct StructuralLevels
{
   double tp1;       // near structural target — natural first objective
   double tp2;       // far structural target  — runner objective
   bool   tp1Valid;  // false = use ATR for TP1
   bool   tp2Valid;  // false = use ATR for TP2
   string source;    // "FVG" | "Displacement" | "Compression" | "H4Swing" | "None"
};

struct ScoreCard
{
   double h4Bias;
   double m15Setup;
   double m1Trigger;
   double liquidity;
   double volatility;
   double session;
   double spread;
   double total;
};

struct TradeSetup
{
   bool              valid;
   ENUM_ORDER_TYPE   type;
   double            entry;
   double            stopLoss;
   double            takeProfit1;
   double            takeProfit2;
   double            lotSize;
   double            rr;
   string            reason;
   double            signalPrice;    // Ask/Bid when BuildSetup() was called
   double            actualFill;     // Fill price captured after Execute()
};

struct RegimeState
{
   ENUM_MARKET_REGIME regime;
   double             atr;
   double             trendSlope;
   double             volatilityRank;
   double             wickRatio;
   double             adrExpansion;
   // v3.13.0 — D1 macro ceiling cached at daily reset (once per day).
   // ZeroMemory-safe: MACRO_UNKNOWN(0) is the correct uninitialised default.
   // Populated by ExecuteDailyReset() via RegimeEngine.GetMacroRegime().
   // Read by GetState() to apply the ceiling gate before returning regime.
   ENUM_MACRO_REGIME  macroRegime;
   // v3.14.3 — H4 EMA separation and H4 ATR for counter-trend setup gate.
   // h4EMASep = MathAbs(EMA_fast[0] - EMA_slow[0]) on confirmed H4 bar.
   // h4ATR    = H4 ATR(14) on confirmed H4 bar.
   // Both written by RegimeEngine.GetState() and carried through
   // m_ctx.regimeAtEntry to ProcessSetup() without additional call overhead.
   // ZeroMemory-safe: 0.0 defaults cause gate to be inactive on warmup.
   double             h4EMASep;
   double             h4ATR;
};

struct ASE_PipelineContext
{
   ENUM_TRADE_DIRECTION direction;
   ScoreCard            scoreCard;
   TradeSetup           tradeSetup;
   RegimeState          regimeAtEntry;
   StructuralLevels     structLevels;    // v4.0 — structural TP targets from SetupEngine
   string               sessionAtEntry;
   string               liquidityType;
   string               m15SetupClass;
   string               m1TriggerClass;
   datetime             entryTime;
   double               entrySpreadPts;
   int                  execLatencyMs;
   // v3.6.0 — entry timing slippage gate fields.
   // Set in ProcessTrigger() when the trigger passes; read in ProcessExecution()
   // to reject fills where price has moved materially since trigger confirmation.
   double               triggerClosePrice;  // close price of the triggering M1 bar
   double               triggerM1ATR;       // M1 ATR at trigger time
   // v3.11.0 — DirectionGate SHORT structural exception flag
   bool                 isCountertrendShortException;

   void Reset()
   {
      direction          = DIR_NONE;
      ZeroMemory(scoreCard);
      ZeroMemory(tradeSetup);
      ZeroMemory(regimeAtEntry);
      ZeroMemory(structLevels);
      structLevels.source    = "None";
      sessionAtEntry         = "";
      liquidityType          = "None";
      m15SetupClass          = "";
      m1TriggerClass         = "";
      entryTime              = 0;
      entrySpreadPts         = 0.0;
      execLatencyMs          = 0;
      triggerClosePrice      = 0.0;
      triggerM1ATR           = 0.0;
      isCountertrendShortException = false;
   }
};

//+------------------------------------------------------------------+
//| Full trade attribution record                                    |
//+------------------------------------------------------------------+
struct TradeRecord
{
   // Identity
   ulong    ticket;
   datetime timestamp;
   string   symbol;

   // Context
   string   session;
   string   regime;
   string   h4Bias;
   string   m15SetupClass;
   string   m1TriggerClass;
   string   liquidityType;

   // Scores
   double   entryScore;
   double   h4Score;
   double   m15Score;
   double   m1Score;
   double   liqScore;
   double   volScore;

   // Execution — setup parameters
   double   spread;
   double   atr;
   double   entry;
   double   sl;
   double   tp1;
   double   tp2;
   double   lotSize;
   double   rr;

   // Execution quality — signal vs actual fill (Area B)
   double   signalPrice;    // price when BuildSetup() was called
   double   actualFill;     // actual fill price from broker
   double   slippagePts;    // (actualFill − signalPrice) / _Point
                            // positive = adverse (paid more / sold less)
   double   slippagePct;    // |slippage| as % of entry ATR

   // Excursion analytics
   double   mae;
   double   mfe;
   double   maePct;
   double   mfePct;
   int      barsToMFE;
   int      barsToMAE;

   // Result
   ENUM_EXIT_REASON exitReason;
   int      durationBars;
   double   profit;
   string   result;

   // v4.0 — TradeAttribution additions (§4)
   // These fields complete the causal decomposition required for
   // regime segmentation, survivability analysis, and research DB storage.
   string   sessionSubtype;       // e.g. "London Open", "NY Overlap", "Asia"
   string   volatilityCluster;    // "Low" | "Normal" | "High" | "Spike"
   string   inducementType;       // "None" | "EqualHighs" | "EqualLows" | "StopRaid"
   string   displacementType;     // "None" | "BullDisplacement" | "BearDisplacement"
   int      latencyMs;            // order-send round-trip latency in milliseconds
   double   adr;                  // 20-day average daily range at trade time
   bool     win;                  // true if profit > 0 (convenience for analytics)
   int      timeToMAEMin;         // bars-to-MAE converted to minutes (bars × timeframe_mins)
   int      timeToMFEMin;         // bars-to-MFE converted to minutes
};
#endif // ASE_STRUCTS_MQH
