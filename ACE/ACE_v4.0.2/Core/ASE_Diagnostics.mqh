#ifndef ASE_DIAGNOSTICS_MQH
#define ASE_DIAGNOSTICS_MQH
#include "../Utilities/ASE_Logger.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Diagnostics (every rejection is logged)                 |
//+------------------------------------------------------------------+
class CASE_Diagnostics
{
private:
   int m_blocks;
   int m_stateChanges;

public:
   void Initialize()
   {
      m_blocks       = 0;
      m_stateChanges = 0;
      Print("╔══════════════════════════════════════════╗");
      Print("║  ASE v3 — Diagnostics Initialized        ║");
      Print("╚══════════════════════════════════════════╝");
   }

   void LogBlock(string layer, string reason)
   {
      m_blocks++;
      Print(StringFormat("[BLOCKED #%d] %s | %s | %s",
            m_blocks, layer, reason,
            TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES)));
   }

   void LogState(string state)
   {
      m_stateChanges++;
      Print(StringFormat("[STATE  #%d] -> %s", m_stateChanges, state));
   }

   void LogTrade(string direction, double entry, double sl, double tp1,
                 double tp2, double lots, double score)
   {
      Print(StringFormat("[TRADE ] Dir=%s Entry=%.5f SL=%.5f TP1=%.5f TP2=%.5f Lots=%.2f Score=%.1f",
            direction, entry, sl, tp1, tp2, lots, score));
   }

   int GetBlockCount()     { return m_blocks;       }
   int GetStateChanges()   { return m_stateChanges; }
};
#endif // ASE_DIAGNOSTICS_MQH
