#ifndef ASE_TRADEEXPORTER_MQH
#define ASE_TRADEEXPORTER_MQH
#include "../Models/ASE_Structs.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Full Attribution CSV Exporter                           |
//| v3.3.0: Added signal_price, actual_fill, slippage_pts,           |
//|          slippage_pct_atr columns (Area B)                        |
//|                                                                  |
//| Output: MQL5\Files\ASE_v3_trades.csv                             |
//| One row per closed trade. Open in Excel or Python pandas.        |
//+------------------------------------------------------------------+
class CASE_TradeExporter
{
private:
   int    m_handle;
   string m_filename;

public:
   CASE_TradeExporter() : m_handle(INVALID_HANDLE), m_filename("") {}

   bool Open(string filename)
   {
      m_filename = filename;
      m_handle   = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_ANSI);
      if(m_handle == INVALID_HANDLE)
      {
         Print("[CSV] Cannot open: ", filename);
         return false;
      }

      // Full header — spec §2.1 + §3.1
      string hdr =
         "ticket,"
         "timestamp,"
         "symbol,"
         "session,"
         "regime,"
         "h4_bias,"
         "m15_setup,"
         "m1_trigger,"
         "liquidity_type,"
         "entry_score,"
         "h4_score,"
         "m15_score,"
         "m1_score,"
         "liq_score,"
         "vol_score,"
         "spread,"
         "atr,"
         "entry,"
         "sl,"
         "tp1,"
         "tp2,"
         "lot_size,"
         "rr,"
         "signal_price,"
         "actual_fill,"
         "slippage_pts,"
         "slippage_pct_atr,"
         "mae,"
         "mfe,"
         "mae_pct_sl,"
         "mfe_pct_tp,"
         "bars_to_mfe,"
         "bars_to_mae,"
         "exit_reason,"
         "duration_bars,"
         "profit,"
         "result";

      FileWrite(m_handle, hdr);
      return true;
   }

   // Write one fully attributed trade record
   void Write(const TradeRecord &r)
   {
      if(m_handle == INVALID_HANDLE) return;

      string exitStr = ExitReasonToString(r.exitReason);

      string row =
         IntegerToString((long)r.ticket)                  + "," +
         TimeToString(r.timestamp, TIME_DATE|TIME_MINUTES) + "," +
         r.symbol                                          + "," +
         r.session                                         + "," +
         r.regime                                          + "," +
         r.h4Bias                                          + "," +
         r.m15SetupClass                                   + "," +
         r.m1TriggerClass                                  + "," +
         r.liquidityType                                   + "," +
         DoubleToString(r.entryScore,   1)                 + "," +
         DoubleToString(r.h4Score,      1)                 + "," +
         DoubleToString(r.m15Score,     1)                 + "," +
         DoubleToString(r.m1Score,      1)                 + "," +
         DoubleToString(r.liqScore,     1)                 + "," +
         DoubleToString(r.volScore,     1)                 + "," +
         DoubleToString(r.spread,       1)                 + "," +
         DoubleToString(r.atr,          5)                 + "," +
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
         DoubleToString(r.mae,          5)                 + "," +
         DoubleToString(r.mfe,          5)                 + "," +
         DoubleToString(r.maePct,       1)                 + "," +
         DoubleToString(r.mfePct,       1)                 + "," +
         IntegerToString(r.barsToMFE)                      + "," +
         IntegerToString(r.barsToMAE)                      + "," +
         exitStr                                           + "," +
         IntegerToString(r.durationBars)                   + "," +
         DoubleToString(r.profit,       2)                 + "," +
         r.result;

      FileWrite(m_handle, row);
      FileFlush(m_handle);  // ensure data is not lost if EA crashes
   }

   void Close()
   {
      if(m_handle != INVALID_HANDLE)
      {
         FileClose(m_handle);
         m_handle = INVALID_HANDLE;
         Print("[CSV] Trade log closed: ", m_filename);
      }
   }

private:
   string ExitReasonToString(ENUM_EXIT_REASON r)
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
};
#endif // ASE_TRADEEXPORTER_MQH
