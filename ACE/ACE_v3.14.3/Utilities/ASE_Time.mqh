#ifndef ASE_TIME_MQH
#define ASE_TIME_MQH
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3.4.4 — Time Utilities                                      |
//|                                                                  |
//| IMPORTANT: All session checks use TimeGMT() (true UTC), NOT      |
//| TimeCurrent() which returns broker server time and varies by      |
//| broker offset (XM is typically UTC+2 or UTC+3).                  |
//|                                                                  |
//| v3.4.4: Session windows now driven by input parameters           |
//| (InpLondonStartHour/Min, InpLondonEndHour/Min, InpNYStartHour/   |
//| Min, InpNYEndHour/Min). Default values are unchanged from the    |
//| hardcoded originals. PrintSessionConfig() logs effective windows |
//| on startup for verification.                                      |
//+------------------------------------------------------------------+
class CASE_Time
{
public:
   // ── True UTC hour/minute (broker-offset independent) ──────────
   static int GMTHour()
   {
      MqlDateTime dt;
      TimeToStruct(TimeGMT(), dt);
      return dt.hour;
   }

   static int GMTMinute()
   {
      MqlDateTime dt;
      TimeToStruct(TimeGMT(), dt);
      return dt.min;
   }

   static bool IsWeekend()
   {
      MqlDateTime dt;
      TimeToStruct(TimeGMT(), dt);
      return(dt.day_of_week == 0 || dt.day_of_week == 6);
   }

   // ── London session ─────────────────────────────────────────────
   // Window defined by InpLondonStartHour/Min → InpLondonEndHour/Min (UTC).
   // Default: 07:00–12:30 UTC (09:00–14:30 SAST / 10:00–15:30 XM server).
   static bool IsLondon()
   {
      int totalMin = GMTHour() * 60 + GMTMinute();
      int start    = InpLondonStartHour * 60 + InpLondonStartMin;
      int end      = InpLondonEndHour   * 60 + InpLondonEndMin;
      return(totalMin >= start && totalMin < end);
   }

   // ── New York session ───────────────────────────────────────────
   // Window defined by InpNYStartHour/Min → InpNYEndHour/Min (UTC).
   // Default: 12:30–21:00 UTC (14:30–23:00 SAST / 15:30–00:00 XM server).
   static bool IsNewYork()
   {
      int totalMin = GMTHour() * 60 + GMTMinute();
      int start    = InpNYStartHour * 60 + InpNYStartMin;
      int end      = InpNYEndHour   * 60 + InpNYEndMin;
      return(totalMin >= start && totalMin < end);
   }

   // ── London/NY overlap ──────────────────────────────────────────
   // Defined as NY open → 30 minutes past London end (capped at NY end).
   // When both sessions overlap this is the highest-quality window.
   static bool IsOverlap()
   {
      int totalMin    = GMTHour() * 60 + GMTMinute();
      int overlapStart = InpNYStartHour  * 60 + InpNYStartMin;
      int overlapEnd   = InpLondonEndHour * 60 + InpLondonEndMin + 30; // 30 min after London close
      int nyEnd        = InpNYEndHour    * 60 + InpNYEndMin;
      if(overlapEnd > nyEnd) overlapEnd = nyEnd;
      return(totalMin >= overlapStart && totalMin < overlapEnd);
   }

   static bool IsLondonOrNY()
   {
      return(IsLondon() || IsNewYork());
   }

   // ── ICT Kill Zones (v3.7.0) ────────────────────────────────────
   // Kill zones are the highest-probability windows within each session.
   // They represent the opening sweep / institutional order flow period.
   //   London KZ : 08:00–11:00 UTC (10:00–13:00 SAST) — London open flow
   //   NY KZ     : 13:00–16:00 UTC (15:00–18:00 SAST) — NY open / London close
   // These are fixed ICT windows and are not driven by configurable inputs
   // since they represent the kill-zone concept as published — adjusting them
   // effectively makes them a different concept.
   // Returns true when inside either kill zone AND inside the active session.
   static bool IsKillZone()
   {
      if(!InpKillZoneEnabled) return false;
      int totalMin = GMTHour() * 60 + GMTMinute();
      bool londonKZ = (totalMin >= 480  && totalMin < 660);   // 08:00–11:00 UTC
      bool nyKZ     = (totalMin >= 780  && totalMin < 960);   // 13:00–16:00 UTC
      return (londonKZ || nyKZ) && IsLondonOrNY();
   }

   // ── Legacy aliases ─────────────────────────────────────────────
   static int ServerHour()  { return GMTHour();   }
   static int ServerMinute(){ return GMTMinute();  }

   // ── Startup diagnostic — call once from Initialize() ───────────
   // Prints effective UTC windows and their SAST equivalents (+2h UTC).
   static void PrintSessionConfig()
   {
      Print(StringFormat(
         "[TIME] London  : %02d:%02d–%02d:%02d UTC  (%02d:%02d–%02d:%02d SAST)",
         InpLondonStartHour, InpLondonStartMin,
         InpLondonEndHour,   InpLondonEndMin,
         InpLondonStartHour + 2, InpLondonStartMin,
         InpLondonEndHour   + 2, InpLondonEndMin));
      Print(StringFormat(
         "[TIME] NewYork : %02d:%02d–%02d:%02d UTC  (%02d:%02d–%02d:%02d SAST)",
         InpNYStartHour, InpNYStartMin,
         InpNYEndHour,   InpNYEndMin,
         InpNYStartHour + 2, InpNYStartMin,
         InpNYEndHour   + 2, InpNYEndMin));
      int overlapStart = InpNYStartHour * 60 + InpNYStartMin;
      int overlapEnd   = InpLondonEndHour * 60 + InpLondonEndMin + 30;
      Print(StringFormat(
         "[TIME] Overlap : %02d:%02d–%02d:%02d UTC  (%02d:%02d–%02d:%02d SAST)  [score=9.5]",
         overlapStart / 60, overlapStart % 60,
         overlapEnd   / 60, overlapEnd   % 60,
         overlapStart / 60 + 2, overlapStart % 60,
         overlapEnd   / 60 + 2, overlapEnd   % 60));
      // v3.7.0 — kill zone diagnostic
      if(InpKillZoneEnabled)
      {
         Print("[TIME] London KZ : 08:00–11:00 UTC  (10:00–13:00 SAST)  [score=10.0]");
         Print("[TIME] NY KZ     : 13:00–16:00 UTC  (15:00–18:00 SAST)  [score=10.0]");
      }
      else
         Print("[TIME] Kill zones: DISABLED (InpKillZoneEnabled=false)");
   }
};
#endif // ASE_TIME_MQH
