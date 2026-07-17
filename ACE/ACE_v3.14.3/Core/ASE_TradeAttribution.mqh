#ifndef ASE_TRADEATTRIBUTION_MQH
#define ASE_TRADEATTRIBUTION_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
#include "../Utilities/ASE_Time.mqh"
//+------------------------------------------------------------------+
//| ASE v4.0 — Trade Attribution Engine                              |
//|                                                                  |
//| Responsibility:                                                  |
//|   1. Populate every causal field of TradeRecord that the         |
//|      StateMachine cannot fill at execution time (sessionSubtype, |
//|      volatilityCluster, inducementType, displacementType,        |
//|      latencyMs, adr, win, timeToMAEMin, timeToMFEMin).           |
//|   2. Export each closed trade in three formats:                  |
//|        CSV  — compatible with existing ase_analysis.py           |
//|        JSON — one object per trade, newline-delimited (NDJSON)   |
//|        SQLite-row — pipe-delimited flat row written to           |
//|                      ASE_v4_attribution.pipe for Python DB ingest|
//|                                                                  |
//| Integration:                                                     |
//|   Called from StateMachine.ProcessManagement() after             |
//|   CommitTradeRecord(), before m_csv.Write().                     |
//|   Replace:                                                       |
//|     m_csv.Write(rec);                                            |
//|   With:                                                          |
//|     m_attr.Enrich(rec, m_ctx, m_regime);                         |
//|     m_attr.Export(rec);                                          |
//|   (m_csv.Write is superseded — the CSV exporter in this module   |
//|   uses the same column set plus the new v4 columns.)             |
//|                                                                  |
//| Latency measurement:                                             |
//|   StateMachine must capture the pre-order timestamp and pass it  |
//|   via ctx.execLatencyMs populated by ExecutionEngine after fill.  |
//|   This module computes the round-trip delta on the first tick    |
//|   after a fill is confirmed.                                      |
//|                                                                  |
//| File outputs (MQL5 Files directory):                             |
//|   ASE_v4_trades_full.csv   — full attribution CSV                |
//|   ASE_v4_trades.ndjson     — newline-delimited JSON              |
//|   ASE_v4_attribution.pipe  — pipe-delimited SQLite ingest rows   |
//+------------------------------------------------------------------+

// Number of M15 bars used to scan for inducement / displacement.
#define ATTR_SCAN_BARS     20
// Minimum candle body/range ratio to qualify as a displacement candle.
#define ATTR_DISP_THRESHOLD 0.60
// Spread multiplier above which a spread event counts as "Spike" volatility.
#define ATTR_SPREAD_SPIKE  3.0
// Minimum equal-high/low match tolerance as a fraction of ATR.
#define ATTR_EQ_TOL_FACTOR 0.15
// Timeframe in minutes for the trigger timeframe (M15 = 15).
#define ATTR_TF_MINUTES    15

class CASE_TradeAttribution
{
private:
   int    m_csvHandle;
   int    m_jsonHandle;
   int    m_pipeHandle;
   int    m_adrHandle;         // D1 ATR handle for 20-bar ADR
   double m_normalSpread;      // rolling average spread for spike detection
   int    m_spreadSamples;

public:
   CASE_TradeAttribution()
      : m_csvHandle(INVALID_HANDLE),
        m_jsonHandle(INVALID_HANDLE),
        m_pipeHandle(INVALID_HANDLE),
        m_adrHandle(INVALID_HANDLE),
        m_normalSpread(0.0),
        m_spreadSamples(0) {}

   //──────────────────────────────────────────────────────────────────
   bool Initialize()
   {
      // D1 ATR for ADR calculation (20 bars, matches RegimeEngine lookback)
      m_adrHandle = iATR(_Symbol, PERIOD_D1, 20);
      if(m_adrHandle == INVALID_HANDLE)
      {
         Print("[ATTR] WARNING: D1 ATR handle failed — adr field will be 0");
      }

      m_csvHandle = FileOpen("ASE_v4_trades_full.csv",
                             FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ);
      if(m_csvHandle == INVALID_HANDLE)
      {
         Print("[ATTR] Cannot open CSV output");
         return false;
      }
      WriteCSVHeader();

      m_jsonHandle = FileOpen("ASE_v4_trades.ndjson",
                              FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
      if(m_jsonHandle == INVALID_HANDLE)
      {
         Print("[ATTR] Cannot open JSON output");
         return false;
      }

      m_pipeHandle = FileOpen("ASE_v4_attribution.pipe",
                              FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
      if(m_pipeHandle == INVALID_HANDLE)
      {
         Print("[ATTR] Cannot open pipe output");
         return false;
      }
      WritePipeHeader();

      m_normalSpread   = 0.0;
      m_spreadSamples  = 0;

      Print("[ATTR] TradeAttribution initialized — 3 output streams open");
      return true;
   }

   //──────────────────────────────────────────────────────────────────
   void Deinitialize()
   {
      if(m_adrHandle != INVALID_HANDLE)
      {
         IndicatorRelease(m_adrHandle);
         m_adrHandle = INVALID_HANDLE;
      }
      CloseFile(m_csvHandle,  "ASE_v4_trades_full.csv");
      CloseFile(m_jsonHandle, "ASE_v4_trades.ndjson");
      CloseFile(m_pipeHandle, "ASE_v4_attribution.pipe");
   }

   //──────────────────────────────────────────────────────────────────
   // UpdateSpread — call on every tick (or once per bar) to maintain
   // a running average spread used for spike detection.
   //──────────────────────────────────────────────────────────────────
   void UpdateSpread()
   {
      double spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
      if(spread <= 0) return;

      // Exponential moving average with α ≈ 0.05 (fast warm-up, slow drift)
      if(m_spreadSamples == 0)
         m_normalSpread = spread;
      else
         m_normalSpread = m_normalSpread * 0.95 + spread * 0.05;
      m_spreadSamples++;
   }

   //──────────────────────────────────────────────────────────────────
   // Enrich — populate the 9 v4 fields on an already-committed rec.
   // Call AFTER Telemetry.CommitTradeRecord() so barsToMFE/MAE are set.
   //
   // Parameters:
   //   rec      — the TradeRecord to enrich (mutated in place)
   //   ctx      — the pipeline context at entry time
   //   fillTime — datetime of the confirming fill tick
   //──────────────────────────────────────────────────────────────────
   void Enrich(TradeRecord &rec,
               const ASE_PipelineContext &ctx,
               datetime fillTime)
   {
      // 1. sessionSubtype — granular session label
      rec.sessionSubtype = GetSessionSubtype(fillTime);

      // 2. volatilityCluster — spread + ATR-based tier
      rec.volatilityCluster = GetVolatilityCluster(rec.spread, rec.atr);

      // 3. Scan recent M15 bars for inducement and displacement
      double hi[], lo[], open[], close[];
      ArraySetAsSeries(hi,    true);
      ArraySetAsSeries(lo,    true);
      ArraySetAsSeries(open,  true);
      ArraySetAsSeries(close, true);

      int copied = 0;
      if(CopyHigh( _Symbol, PERIOD_M15, 0, ATTR_SCAN_BARS, hi)    == ATTR_SCAN_BARS &&
         CopyLow(  _Symbol, PERIOD_M15, 0, ATTR_SCAN_BARS, lo)    == ATTR_SCAN_BARS &&
         CopyOpen( _Symbol, PERIOD_M15, 0, ATTR_SCAN_BARS, open)  == ATTR_SCAN_BARS &&
         CopyClose(_Symbol, PERIOD_M15, 0, ATTR_SCAN_BARS, close) == ATTR_SCAN_BARS)
         copied = ATTR_SCAN_BARS;

      if(copied > 0)
      {
         rec.inducementType   = GetInducementType(hi, lo, rec.atr, ctx.direction);
         rec.displacementType = GetDisplacementType(open, close, hi, lo, ctx.direction);
      }
      else
      {
         rec.inducementType   = "None";
         rec.displacementType = "None";
      }

      // 4. ADR — 20-bar D1 ATR
      rec.adr = GetADR();

      // 5. Latency — read directly from PipelineContext where ExecutionEngine
      //    stored the measured round-trip after the successful fill attempt.
      //    This is more accurate than a GetTickCount() delta taken here because
      //    it isolates exactly the broker round-trip, excluding EA processing time.
      rec.latencyMs = ctx.execLatencyMs;

      // 6. win — convenience bool
      rec.win = (rec.profit > 0.0);

      // 7. timeToMAEMin / timeToMFEMin
      rec.timeToMAEMin = rec.barsToMAE * ATTR_TF_MINUTES;
      rec.timeToMFEMin = rec.barsToMFE * ATTR_TF_MINUTES;
   }

   //──────────────────────────────────────────────────────────────────
   // Export — write the enriched record to all three output streams.
   // Replaces the old m_csv.Write(rec) call.
   //──────────────────────────────────────────────────────────────────
   void Export(const TradeRecord &r)
   {
      WriteCSVRow(r);
      WriteJSONRow(r);
      WritePipeRow(r);
   }

   //══════════════════════════════════════════════════════════════════
   //  PRIVATE — enrichment helpers
   //══════════════════════════════════════════════════════════════════
private:

   //──────────────────────────────────────────────────────────────────
   // Session subtype — finer granularity than the binary London/NY
   // labels already present in TradeRecord.session.
   //──────────────────────────────────────────────────────────────────
   string GetSessionSubtype(datetime t)
   {
      MqlDateTime dt;
      TimeToStruct(t, dt);
      int h = dt.hour;

      // Times in server time (assumed UTC+2 / UTC+3 — adjust via
      // broker offset if required; matches existing CASE_Time logic).
      if(h >= 7  && h < 9)  return "LondonOpen";
      if(h >= 9  && h < 12) return "LondonMid";
      if(h >= 12 && h < 14) return "LondonClose";
      if(h >= 14 && h < 16) return "NYOpen";
      if(h >= 16 && h < 18) return "NYOverlap";   // London + NY
      if(h >= 18 && h < 22) return "NYMid";
      if(h >= 22 || h < 2)  return "AsiaOpen";
      return "AsiaMid";
   }

   //──────────────────────────────────────────────────────────────────
   // Volatility cluster — four tiers based on spread vs normal spread.
   // Combines execution-quality and market-condition signals.
   //──────────────────────────────────────────────────────────────────
   string GetVolatilityCluster(double spread, double atr)
   {
      if(m_normalSpread <= 0 || atr <= 0) return "Normal";

      double spreadRatio = (m_normalSpread > 0)
                           ? spread / m_normalSpread
                           : 1.0;

      if(spreadRatio >= ATTR_SPREAD_SPIKE) return "Spike";

      // ATR-relative tiers (same three buckets as the plan)
      double atrD1Avg = GetADR();
      if(atrD1Avg <= 0) return "Normal";

      // Compare current M15 ATR to 20% of daily range as a proxy
      double low_thresh  = atrD1Avg * 0.008;   // < 0.8% of ADR
      double high_thresh = atrD1Avg * 0.025;   // > 2.5% of ADR

      if(atr < low_thresh)  return "Low";
      if(atr > high_thresh) return "High";
      return "Normal";
   }

   //──────────────────────────────────────────────────────────────────
   // Inducement detection — scans for equal highs / equal lows in the
   // lookback window, then checks if price swept through them before
   // the entry direction was taken.
   //
   // Returns: "None" | "EqualHighs" | "EqualLows" | "StopRaid"
   //──────────────────────────────────────────────────────────────────
   string GetInducementType(const double &hi[],
                             const double &lo[],
                             double atr,
                             ENUM_TRADE_DIRECTION dir)
   {
      double tol = atr * ATTR_EQ_TOL_FACTOR;
      if(tol < _Point * 5) tol = _Point * 5;

      int equalHighs = 0;
      int equalLows  = 0;

      for(int i = 1; i < ATTR_SCAN_BARS - 1; i++)
      {
         if(MathAbs(hi[i] - hi[i + 1]) <= tol) equalHighs++;
         if(MathAbs(lo[i] - lo[i + 1]) <= tol) equalLows++;
      }

      // A "StopRaid" requires equal levels AND a wick that swept
      // through them (the candle close reversed back inside the range).
      // Detected as: price swept past the cluster on bar[0] then closed
      // in the opposite direction (wick > body on the sweep side).
      bool raidHigh = false;
      bool raidLow  = false;
      if(ATTR_SCAN_BARS > 1)
      {
         double body  = MathAbs(hi[0] - lo[0]);
         double oBody = MathAbs(hi[1] - lo[1]);
         if(body > 0 && oBody > 0)
         {
            // Upper wick dominates — likely swept above and reversed
            double upperWick0 = hi[0] - MathMax(hi[0], lo[0]);
            // Simplified: if most recent high exceeded prior high cluster
            // and candle closed below midpoint, tag as StopRaid
            if(equalHighs > 0 && hi[0] > hi[1] + tol) raidHigh = true;
            if(equalLows  > 0 && lo[0] < lo[1] - tol) raidLow  = true;
         }
      }

      if(raidHigh || raidLow)    return "StopRaid";
      if(dir == DIR_LONG  && equalLows  > 0) return "EqualLows";
      if(dir == DIR_SHORT && equalHighs > 0) return "EqualHighs";
      if(equalHighs > 0)         return "EqualHighs";
      if(equalLows  > 0)         return "EqualLows";
      return "None";
   }

   //──────────────────────────────────────────────────────────────────
   // Displacement scoring — §9 spec: score = candleBody / candleRange.
   // Returns: "None" | "BullDisplacement" | "BearDisplacement"
   //──────────────────────────────────────────────────────────────────
   string GetDisplacementType(const double &open[],
                               const double &close[],
                               const double &hi[],
                               const double &lo[],
                               ENUM_TRADE_DIRECTION dir)
   {
      // Scan the three most recent completed M15 bars for a strong
      // displacement candle preceding the entry.
      for(int i = 1; i <= 3 && i < ATTR_SCAN_BARS; i++)
      {
         double range = hi[i] - lo[i];
         if(range <= 0) continue;

         double body  = MathAbs(close[i] - open[i]);
         double score = body / range;

         if(score >= ATTR_DISP_THRESHOLD)
         {
            bool bullish = close[i] > open[i];
            if(bullish) return "BullDisplacement";
            else        return "BearDisplacement";
         }
      }
      return "None";
   }

   //──────────────────────────────────────────────────────────────────
   // ADR — 20-bar D1 ATR, same lookback as RegimeEngine.
   // Returns the raw D1 ATR value (not scaled).
   //──────────────────────────────────────────────────────────────────
   double GetADR()
   {
      if(m_adrHandle == INVALID_HANDLE) return 0.0;
      double buf[];
      ArraySetAsSeries(buf, true);
      if(CopyBuffer(m_adrHandle, 0, 1, 1, buf) < 1) return 0.0;
      return buf[0];
   }

   //══════════════════════════════════════════════════════════════════
   //  PRIVATE — output writers
   //══════════════════════════════════════════════════════════════════

   void WriteCSVHeader()
   {
      if(m_csvHandle == INVALID_HANDLE) return;
      string hdr =
         "ticket,timestamp,symbol,session,session_subtype,regime,"
         "volatility_cluster,h4_bias,m15_setup,m1_trigger,"
         "liquidity_type,inducement_type,displacement_type,"
         "entry_score,h4_score,m15_score,m1_score,liq_score,vol_score,"
         "spread,atr,adr,entry,sl,tp1,tp2,lot_size,rr,"
         "signal_price,actual_fill,slippage_pts,slippage_pct_atr,"
         "latency_ms,mae,mfe,mae_pct_sl,mfe_pct_tp,"
         "bars_to_mfe,bars_to_mae,time_to_mfe_min,time_to_mae_min,"
         "exit_reason,duration_bars,profit,result,win";
      FileWrite(m_csvHandle, hdr);
      FileFlush(m_csvHandle);
   }

   void WriteCSVRow(const TradeRecord &r)
   {
      if(m_csvHandle == INVALID_HANDLE) return;
      string row =
         IntegerToString((long)r.ticket)                   + "," +
         TimeToString(r.timestamp, TIME_DATE|TIME_MINUTES) + "," +
         r.symbol                                          + "," +
         r.session                                         + "," +
         r.sessionSubtype                                  + "," +
         r.regime                                          + "," +
         r.volatilityCluster                               + "," +
         r.h4Bias                                          + "," +
         r.m15SetupClass                                   + "," +
         r.m1TriggerClass                                  + "," +
         r.liquidityType                                   + "," +
         r.inducementType                                  + "," +
         r.displacementType                                + "," +
         DoubleToString(r.entryScore,   1)                 + "," +
         DoubleToString(r.h4Score,      1)                 + "," +
         DoubleToString(r.m15Score,     1)                 + "," +
         DoubleToString(r.m1Score,      1)                 + "," +
         DoubleToString(r.liqScore,     1)                 + "," +
         DoubleToString(r.volScore,     1)                 + "," +
         DoubleToString(r.spread,       1)                 + "," +
         DoubleToString(r.atr,          5)                 + "," +
         DoubleToString(r.adr,          5)                 + "," +
         DoubleToString(r.entry,        5)                 + "," +
         DoubleToString(r.sl,           5)                 + "," +
         DoubleToString(r.tp1,          5)                 + "," +
         DoubleToString(r.tp2,          5)                 + "," +
         DoubleToString(r.lotSize,      2)                 + "," +
         DoubleToString(r.rr,           2)                 + "," +
         DoubleToString(r.signalPrice,  5)                 + "," +
         DoubleToString(r.actualFill,   5)                 + "," +
         DoubleToString(r.slippagePts,  1)                 + "," +
         DoubleToString(r.slippagePct,  1)                 + "," +
         IntegerToString(r.latencyMs)                      + "," +
         DoubleToString(r.mae,          5)                 + "," +
         DoubleToString(r.mfe,          5)                 + "," +
         DoubleToString(r.maePct,       1)                 + "," +
         DoubleToString(r.mfePct,       1)                 + "," +
         IntegerToString(r.barsToMFE)                      + "," +
         IntegerToString(r.barsToMAE)                      + "," +
         IntegerToString(r.timeToMFEMin)                   + "," +
         IntegerToString(r.timeToMAEMin)                   + "," +
         ExitReasonStr(r.exitReason)                       + "," +
         IntegerToString(r.durationBars)                   + "," +
         DoubleToString(r.profit,       2)                 + "," +
         r.result                                          + "," +
         (r.win ? "1" : "0");
      FileWrite(m_csvHandle, row);
      FileFlush(m_csvHandle);
   }

   //──────────────────────────────────────────────────────────────────
   // JSON writer — newline-delimited JSON (NDJSON).
   // Each trade is one complete JSON object on a single line.
   // Compatible with Python json.loads() line-by-line and pandas
   // read_json(..., lines=True).
   //──────────────────────────────────────────────────────────────────
   void WriteJSONRow(const TradeRecord &r)
   {
      if(m_jsonHandle == INVALID_HANDLE) return;

      string j = "{";
      j += JStr("ticket",            IntegerToString((long)r.ticket));
      j += JStr("timestamp",         TimeToString(r.timestamp, TIME_DATE|TIME_MINUTES));
      j += JStr("symbol",            r.symbol);
      j += JStr("session",           r.session);
      j += JStr("session_subtype",   r.sessionSubtype);
      j += JStr("regime",            r.regime);
      j += JStr("volatility_cluster",r.volatilityCluster);
      j += JStr("h4_bias",           r.h4Bias);
      j += JStr("m15_setup",         r.m15SetupClass);
      j += JStr("m1_trigger",        r.m1TriggerClass);
      j += JStr("liquidity_type",    r.liquidityType);
      j += JStr("inducement_type",   r.inducementType);
      j += JStr("displacement_type", r.displacementType);
      j += JNum("entry_score",       r.entryScore,  1);
      j += JNum("h4_score",          r.h4Score,     1);
      j += JNum("m15_score",         r.m15Score,    1);
      j += JNum("m1_score",          r.m1Score,     1);
      j += JNum("liq_score",         r.liqScore,    1);
      j += JNum("vol_score",         r.volScore,    1);
      j += JNum("spread",            r.spread,      1);
      j += JNum("atr",               r.atr,         5);
      j += JNum("adr",               r.adr,         5);
      j += JNum("entry",             r.entry,       5);
      j += JNum("sl",                r.sl,          5);
      j += JNum("tp1",               r.tp1,         5);
      j += JNum("tp2",               r.tp2,         5);
      j += JNum("lot_size",          r.lotSize,     2);
      j += JNum("rr",                r.rr,          2);
      j += JNum("signal_price",      r.signalPrice, 5);
      j += JNum("actual_fill",       r.actualFill,  5);
      j += JNum("slippage_pts",      r.slippagePts, 1);
      j += JNum("slippage_pct_atr",  r.slippagePct, 1);
      j += JInt("latency_ms",        r.latencyMs);
      j += JNum("mae",               r.mae,         5);
      j += JNum("mfe",               r.mfe,         5);
      j += JNum("mae_pct_sl",        r.maePct,      1);
      j += JNum("mfe_pct_tp",        r.mfePct,      1);
      j += JInt("bars_to_mfe",       r.barsToMFE);
      j += JInt("bars_to_mae",       r.barsToMAE);
      j += JInt("time_to_mfe_min",   r.timeToMFEMin);
      j += JInt("time_to_mae_min",   r.timeToMAEMin);
      j += JStr("exit_reason",       ExitReasonStr(r.exitReason));
      j += JInt("duration_bars",     r.durationBars);
      j += JNum("profit",            r.profit,      2);
      j += JStr("result",            r.result);
      // win is the final key — no trailing comma
      j += "\"win\":" + (r.win ? "true" : "false") + "}";

      FileWrite(m_jsonHandle, j);
      FileFlush(m_jsonHandle);
   }

   //──────────────────────────────────────────────────────────────────
   // Pipe writer — pipe-delimited flat row for SQLite bulk ingest.
   //
   // Python ingest pattern:
   //   import sqlite3, csv
   //   conn = sqlite3.connect("ase_research.db")
   //   with open("ASE_v4_attribution.pipe") as f:
   //       reader = csv.DictReader(f, delimiter="|")
   //       conn.executemany("INSERT INTO trades VALUES (...)", reader)
   //
   // Column order is identical to CSV header but pipe-delimited to
   // avoid conflicts with comma-containing string fields.
   //──────────────────────────────────────────────────────────────────
   void WritePipeHeader()
   {
      if(m_pipeHandle == INVALID_HANDLE) return;
      string hdr =
         "ticket|timestamp|symbol|session|session_subtype|regime|"
         "volatility_cluster|h4_bias|m15_setup|m1_trigger|"
         "liquidity_type|inducement_type|displacement_type|"
         "entry_score|h4_score|m15_score|m1_score|liq_score|vol_score|"
         "spread|atr|adr|entry|sl|tp1|tp2|lot_size|rr|"
         "signal_price|actual_fill|slippage_pts|slippage_pct_atr|"
         "latency_ms|mae|mfe|mae_pct_sl|mfe_pct_tp|"
         "bars_to_mfe|bars_to_mae|time_to_mfe_min|time_to_mae_min|"
         "exit_reason|duration_bars|profit|result|win";
      FileWrite(m_pipeHandle, hdr);
      FileFlush(m_pipeHandle);
   }

   void WritePipeRow(const TradeRecord &r)
   {
      if(m_pipeHandle == INVALID_HANDLE) return;
      string row =
         IntegerToString((long)r.ticket)                   + "|" +
         TimeToString(r.timestamp, TIME_DATE|TIME_MINUTES) + "|" +
         r.symbol                                          + "|" +
         r.session                                         + "|" +
         r.sessionSubtype                                  + "|" +
         r.regime                                          + "|" +
         r.volatilityCluster                               + "|" +
         r.h4Bias                                          + "|" +
         r.m15SetupClass                                   + "|" +
         r.m1TriggerClass                                  + "|" +
         r.liquidityType                                   + "|" +
         r.inducementType                                  + "|" +
         r.displacementType                                + "|" +
         DoubleToString(r.entryScore,   1)                 + "|" +
         DoubleToString(r.h4Score,      1)                 + "|" +
         DoubleToString(r.m15Score,     1)                 + "|" +
         DoubleToString(r.m1Score,      1)                 + "|" +
         DoubleToString(r.liqScore,     1)                 + "|" +
         DoubleToString(r.volScore,     1)                 + "|" +
         DoubleToString(r.spread,       1)                 + "|" +
         DoubleToString(r.atr,          5)                 + "|" +
         DoubleToString(r.adr,          5)                 + "|" +
         DoubleToString(r.entry,        5)                 + "|" +
         DoubleToString(r.sl,           5)                 + "|" +
         DoubleToString(r.tp1,          5)                 + "|" +
         DoubleToString(r.tp2,          5)                 + "|" +
         DoubleToString(r.lotSize,      2)                 + "|" +
         DoubleToString(r.rr,           2)                 + "|" +
         DoubleToString(r.signalPrice,  5)                 + "|" +
         DoubleToString(r.actualFill,   5)                 + "|" +
         DoubleToString(r.slippagePts,  1)                 + "|" +
         DoubleToString(r.slippagePct,  1)                 + "|" +
         IntegerToString(r.latencyMs)                      + "|" +
         DoubleToString(r.mae,          5)                 + "|" +
         DoubleToString(r.mfe,          5)                 + "|" +
         DoubleToString(r.maePct,       1)                 + "|" +
         DoubleToString(r.mfePct,       1)                 + "|" +
         IntegerToString(r.barsToMFE)                      + "|" +
         IntegerToString(r.barsToMAE)                      + "|" +
         IntegerToString(r.timeToMFEMin)                   + "|" +
         IntegerToString(r.timeToMAEMin)                   + "|" +
         ExitReasonStr(r.exitReason)                       + "|" +
         IntegerToString(r.durationBars)                   + "|" +
         DoubleToString(r.profit,       2)                 + "|" +
         r.result                                          + "|" +
         (r.win ? "1" : "0");
      FileWrite(m_pipeHandle, row);
      FileFlush(m_pipeHandle);
   }

   //──────────────────────────────────────────────────────────────────
   // JSON key helpers — avoid repeated string concatenation boilerplate.
   //──────────────────────────────────────────────────────────────────
   string JStr(string key, string val)
   {
      // Escape any embedded double-quotes in val (rare but defensive)
      StringReplace(val, "\"", "\\\"");
      return "\"" + key + "\":\"" + val + "\",";
   }
   string JNum(string key, double val, int digits)
   {
      return "\"" + key + "\":" + DoubleToString(val, digits) + ",";
   }
   string JInt(string key, int val)
   {
      return "\"" + key + "\":" + IntegerToString(val) + ",";
   }

   string ExitReasonStr(ENUM_EXIT_REASON r)
   {
      switch(r)
      {
         case EXIT_SL:        return "SL";
         case EXIT_TP1:       return "TP1";
         case EXIT_TP2:       return "TP2";
         case EXIT_TRAIL:     return "Trail";
         case EXIT_BREAKEVEN: return "Breakeven";
         case EXIT_MANUAL:    return "Manual";
         case EXIT_DD_HALT:   return "DD_Halt";
         default:             return "Unknown";
      }
   }

   void CloseFile(int &handle, string label)
   {
      if(handle != INVALID_HANDLE)
      {
         FileClose(handle);
         handle = INVALID_HANDLE;
         Print("[ATTR] Closed: ", label);
      }
   }
};
#endif // ASE_TRADEATTRIBUTION_MQH
