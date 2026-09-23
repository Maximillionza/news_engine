#ifndef ASE_ALERTENGINE_MQH
#define ASE_ALERTENGINE_MQH
#include "../Models/ASE_Config.mqh"

// Rate limit: same alert type fires at most once per this many seconds
#define ALERT_COOLDOWN_SEC 900   // 15 minutes

//+------------------------------------------------------------------+
//| ASE v3 — Alert Engine                                            |
//|                                                                  |
//| Delivers alerts via MT5 push notifications (SendNotification).   |
//| To enable: Tools → Options → Notifications → check "Enable" and  |
//| enter your MetaQuotes ID. Messages arrive on the MetaTrader      |
//| mobile app.                                                       |
//|                                                                  |
//| InpAlertsEnabled = false (default) — safe for backtesting        |
//| and initial live deployment. Enable deliberately.                 |
//+------------------------------------------------------------------+
class CASE_AlertEngine
{
private:
   datetime m_lastDDAlert;
   datetime m_lastSpikeAlert;
   datetime m_lastHeartbeatAlert;
   datetime m_lastNewsAlert;
   datetime m_lastHaltAlert;

   void Send(string msg, datetime &lastSent)
   {
      if(!InpAlertsEnabled) return;
      if(TimeCurrent() - lastSent < ALERT_COOLDOWN_SEC) return;
      lastSent = TimeCurrent();
      SendNotification(msg);
      Print("[ALERT] ", msg);
   }

public:
   CASE_AlertEngine()
      : m_lastDDAlert(0), m_lastSpikeAlert(0),
        m_lastHeartbeatAlert(0), m_lastNewsAlert(0),
        m_lastHaltAlert(0) {}

   void CheckDD(double ddPct, double haltPct = 15.0)
   {
      if(ddPct >= haltPct)
      {
         Send(StringFormat("ASE %s HALT: DD=%.1f%% exceeded %.1f%% limit — trading suspended",
                           _Symbol, ddPct, haltPct),
              m_lastHaltAlert);
         return;
      }
      if(ddPct >= haltPct * 0.80)
      {
         Send(StringFormat("ASE %s WARN: DD=%.1f%% approaching halt (%.1f%%)",
                           _Symbol, ddPct, haltPct),
              m_lastDDAlert);
      }
   }

   void SpreadSpike(double currentSpread, double entrySpread)
   {
      Send(StringFormat("ASE %s WARN: Spread spike %.0f pts (entry=%.0f, x%.1f) — trailing paused",
                        _Symbol, currentSpread, entrySpread,
                        (entrySpread > 0 ? currentSpread / entrySpread : 0.0)),
           m_lastSpikeAlert);
   }

   void HeartbeatLost(int silentMinutes)
   {
      Send(StringFormat("ASE %s WARN: No ticks for %d min during session — check connection",
                        _Symbol, silentMinutes),
           m_lastHeartbeatAlert);
   }

   void NewsBlock(int minutesToEvent)
   {
      Send(StringFormat("ASE %s INFO: News block active — high-impact event in %d min",
                        _Symbol, minutesToEvent),
           m_lastNewsAlert);
   }

   // v3.8.0 — Walk-forward OOS retention degradation warning
   void WFDegradation(double wrRetention)
   {
      Send(StringFormat(
         "ASE %s WF WARN: OOS WR retention %.0f%% below 80%% threshold "
         "for 2+ consecutive checks — review walk-forward report",
         _Symbol, wrRetention * 100.0),
           m_lastHaltAlert);   // reuse halt cooldown slot — both are rare operator warnings
   }
};

#undef ALERT_COOLDOWN_SEC
#endif // ASE_ALERTENGINE_MQH
