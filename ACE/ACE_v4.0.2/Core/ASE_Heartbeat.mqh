#ifndef ASE_HEARTBEAT_MQH
#define ASE_HEARTBEAT_MQH
#include "../Models/ASE_Config.mqh"
#include "../Utilities/ASE_Time.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Broker Connectivity Heartbeat                           |
//|                                                                  |
//| Pulse() is called at the top of every Update() tick. IsAlive()   |
//| checks whether ticks are arriving at a normal rate during active  |
//| session hours. Off-session gaps are expected and not flagged.     |
//|                                                                  |
//| Does NOT close positions or block trades. It only provides        |
//| diagnostic state to the StateMachine for alert dispatch.          |
//|                                                                  |
//| InpHeartbeatMinutes = 5: on any liquid pair during London or NY,  |
//| a 5-minute tick gap is a strong indication of feed disruption.   |
//+------------------------------------------------------------------+
class CASE_Heartbeat
{
private:
   datetime m_lastTick;

public:
   CASE_Heartbeat() : m_lastTick(0) {}

   // Call at the top of every Update() — records that a tick arrived
   void Pulse() { m_lastTick = TimeCurrent(); }

   // True if ticks are arriving normally, or if market is closed
   bool IsAlive() const
   {
      // Off-session silence is expected — not a connectivity failure
      if(!CASE_Time::IsLondon() && !CASE_Time::IsNewYork()) return true;
      if(m_lastTick == 0) return true;   // not yet initialised
      long silentSecs = (long)(TimeCurrent() - m_lastTick);
      return (silentSecs < (long)InpHeartbeatMinutes * 60);
   }

   // Minutes of silence during a live session (0 if alive or off-session)
   int SilentMinutes() const
   {
      if(m_lastTick == 0 || IsAlive()) return 0;
      return (int)((TimeCurrent() - m_lastTick) / 60);
   }
};
#endif // ASE_HEARTBEAT_MQH
