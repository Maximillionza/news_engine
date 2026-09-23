#ifndef ASE_LOGGER_MQH
#define ASE_LOGGER_MQH
//+------------------------------------------------------------------+
//| ASE v3 — Logger (static utility)                                 |
//+------------------------------------------------------------------+
class CASE_Logger
{
public:
   static void Info(string msg)    { Print("[INFO]    ", msg); }
   static void Warning(string msg) { Print("[WARNING] ", msg); }
   static void Error(string msg)   { Print("[ERROR]   ", msg); }

   static void Trade(string msg)
   {
      Print("[TRADE]   ", TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
            " | ", msg);
   }

   static void State(string from, string to)
   {
      Print("[STATE]   ", from, " -> ", to);
   }
};
#endif // ASE_LOGGER_MQH
