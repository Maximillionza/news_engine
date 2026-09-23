#ifndef ASE_SESSIONENGINE_MQH
#define ASE_SESSIONENGINE_MQH
#include "../Models/ASE_Config.mqh"
#include "../Utilities/ASE_Time.mqh"
//+------------------------------------------------------------------+
//| ASE v3.4.4 — Session Engine                                      |
//| v3.4.4: Overlap detection now uses CASE_Time::IsOverlap() which  |
//| derives its window from the configurable input parameters rather  |
//| than a hardcoded 13:00–16:00 UTC check.                          |
//+------------------------------------------------------------------+
class CASE_SessionEngine
{
public:
   bool IsTradingSession()
   {
      if(CASE_Time::IsWeekend()) return false;
      if(InpTrade24_7) return true;

      bool london = InpUseLondon && CASE_Time::IsLondon();
      bool ny     = InpUseNY    && CASE_Time::IsNewYork();

      return (london || ny);
   }

   // v3.7.0 — Kill zone sub-scoring.
   // Kill zones score 10.0 (highest) — they are the highest-probability
   // sub-windows within each session. Overlap drops to 9.5 so genuine
   // kill-zone entries remain differentiated from overlap-only entries.
   // London and NY remain 8.0 / 7.0 — unchanged from v3.5.0 outside KZ.
   double GetSessionScore()
   {
      if(CASE_Time::IsKillZone())  return 10.0;  // ICT KZ — top tier
      if(CASE_Time::IsOverlap())   return 9.5;   // London/NY overlap (was 10.0)
      if(CASE_Time::IsLondon())    return 8.0;
      if(CASE_Time::IsNewYork())   return 7.0;
      return 0.0;
   }

   string GetSessionName()
   {
      if(CASE_Time::IsKillZone())                                       return "KillZone";
      if(CASE_Time::IsOverlap())                                        return "Overlap";
      if(CASE_Time::IsLondon() && CASE_Time::IsNewYork())               return "Overlap";
      if(CASE_Time::IsLondon())                                         return "London";
      if(CASE_Time::IsNewYork())                                        return "NewYork";
      return "Off-Session";
   }

   // Call once from StateMachine::Initialize() to log effective windows
   void PrintConfig() { CASE_Time::PrintSessionConfig(); }
};
#endif // ASE_SESSIONENGINE_MQH
