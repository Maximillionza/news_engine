#ifndef ASE_VPSOPTIMIZER_MQH
#define ASE_VPSOPTIMIZER_MQH
//+------------------------------------------------------------------+
//| ASE v3 — VPS Runtime Optimizer                                   |
//|                                                                  |
//| Implements a bar-change tick throttle for LIVE trading only.     |
//| ShouldProcess() returns false for all ticks within the same M1   |
//| bar, cutting pipeline evaluations from ~200–300/min down to      |
//| 1/min (one per M1 bar open). CPU reduction: ~60–80%.             |
//|                                                                  |
//| BACKTESTING / OPTIMISATION:                                       |
//| The throttle is automatically bypassed when running inside the   |
//| Strategy Tester (MQL_TESTER / MQL_OPTIMIZATION flags).           |
//| Reason: the tester generates many artificial ticks per bar and   |
//| MT5 raises "too many containers without changes" [51] when the   |
//| EA blocks them all. More critically, SL/TP closes happen mid-bar |\
//| and must be detected on the very next tick — the throttle would  |
//| prevent this and leave the EA stuck in STATE_POSITION_OPEN for   |
//| the remainder of the bar, causing it to only ever place 1 trade. |
//|                                                                  |
//| v3.8.0 — Maximum interval fallback (Task 15):                    |
//| If no M1 bar change is detected for VPS_MAX_SILENCE_SEC seconds, |
//| ShouldProcess() returns true regardless. Protects against VPS    |
//| clock drift or tick gaps that could stall the pipeline in a      |
//| mid-state indefinitely. Forced evaluations are logged.           |
//+------------------------------------------------------------------+

#define VPS_MAX_SILENCE_SEC 120   // 2 minutes — force process if no M1 bar change

class CASE_VPSOptimizer
{
private:
   datetime m_lastBar;
   datetime m_lastProcessTime;   // v3.8.0: tracks last time ShouldProcess returned true
   bool     m_inTester;

public:
   CASE_VPSOptimizer() : m_lastBar(0), m_lastProcessTime(0), m_inTester(false) {}

   void Initialize()
   {
      // Detect tester / optimiser once at init — cheaper than checking every tick
      m_inTester = (bool)MQLInfoInteger(MQL_TESTER) ||
                   (bool)MQLInfoInteger(MQL_OPTIMIZATION);
   }

   // Returns true when the pipeline should run this tick.
   // In the Strategy Tester: always true (every tick processed).
   // In live trading: true once per M1 bar open OR if silent > 2 min.
   bool ShouldProcess()
   {
      if(m_inTester) return true;

      datetime currentBar = iTime(_Symbol, PERIOD_M1, 0);
      datetime now        = TimeCurrent();

      // v3.8.0 — maximum silence fallback: force process if no M1 bar change
      // has been seen for VPS_MAX_SILENCE_SEC. This handles VPS clock drift
      // or tick gaps (broker outage, reconnect) that stall the state machine.
      if(m_lastProcessTime > 0 &&
         (now - m_lastProcessTime) > VPS_MAX_SILENCE_SEC)
      {
         Print(StringFormat(
            "[VPS] Force-process: no M1 bar change for %ds (max=%d) — possible tick gap",
            (int)(now - m_lastProcessTime), VPS_MAX_SILENCE_SEC));
         m_lastBar         = currentBar;
         m_lastProcessTime = now;
         return true;
      }

      if(currentBar == m_lastBar) return false;
      m_lastBar         = currentBar;
      m_lastProcessTime = now;
      return true;
   }
};
#undef VPS_MAX_SILENCE_SEC
#endif // ASE_VPSOPTIMIZER_MQH
