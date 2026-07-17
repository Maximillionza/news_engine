#ifndef ASE_NEWSENGINE_MQH
#define ASE_NEWSENGINE_MQH
#include "../Models/ASE_Config.mqh"

// CALENDAR_IMPACT_HIGH is part of ENUM_CALENDAR_EVENT_IMPACT, introduced in
// MT5 build 2215. Older terminal builds do not define it, causing
// "undeclared identifier" compile errors. Guard with explicit integer
// values so the EA compiles on any build version.
// Values match the MQL5 specification exactly:
//   CALENDAR_IMPACT_NA     = 0
//   CALENDAR_IMPACT_LOW    = 1
//   CALENDAR_IMPACT_MEDIUM = 2
//   CALENDAR_IMPACT_HIGH   = 3
#ifndef CALENDAR_IMPACT_HIGH
   #define CALENDAR_IMPACT_NA     0
   #define CALENDAR_IMPACT_LOW    1
   #define CALENDAR_IMPACT_MEDIUM 2
   #define CALENDAR_IMPACT_HIGH   3
#endif
//+------------------------------------------------------------------+
//| ASE v3 — News Engine                                             |
//| FIX #14: Upgraded from single-event tracking to a small sorted   |
//|           queue (capacity 8). Previously, if a second event was  |
//|           scheduled after the first, and was later than the first,|
//|           it was silently discarded. After the first event's     |
//|           post-window expired, the second event was lost.        |
//|                                                                  |
//| New behaviour: SetNextEvent() inserts into a sorted array of up  |
//| to 8 events. IsNewsBlocked() checks only the soonest future      |
//| event and purges past events automatically.                      |
//+------------------------------------------------------------------+

#define NEWS_QUEUE_MAX 8   // maximum concurrent high-impact events tracked

class CASE_NewsEngine
{
private:
   datetime m_events[NEWS_QUEUE_MAX];   // sorted ascending, 0 = empty slot
   int      m_count;

public:
   CASE_NewsEngine() : m_count(0)
   {
      ArrayInitialize(m_events, 0);
   }

   // Insert an upcoming event into the sorted queue.
   // Ignores duplicates and past events.
   void SetNextEvent(datetime eventTime)
   {
      if(eventTime <= TimeCurrent()) return;   // already past

      // Check for duplicate (same minute)
      for(int i = 0; i < m_count; i++)
         if(MathAbs((long)m_events[i] - (long)eventTime) < 60) return;

      // Drop oldest if queue is full
      if(m_count >= NEWS_QUEUE_MAX)
      {
         // shift out index 0 (soonest = earliest in queue)
         for(int i = 0; i < NEWS_QUEUE_MAX - 1; i++) m_events[i] = m_events[i+1];
         m_events[NEWS_QUEUE_MAX - 1] = 0;
         m_count = NEWS_QUEUE_MAX - 1;
      }

      // Insert sorted
      m_events[m_count] = eventTime;
      m_count++;
      // Insertion sort — queue stays small so this is fine
      for(int i = m_count - 1; i > 0 && m_events[i] < m_events[i-1]; i--)
      {
         datetime tmp      = m_events[i];
         m_events[i]       = m_events[i-1];
         m_events[i-1]     = tmp;
      }
   }

   // Returns true if we are within the blocking window of ANY queued event.
   // Purges events whose post-window has fully expired.
   bool IsNewsBlocked()
   {
      if(m_count == 0) return false;

      datetime now    = TimeCurrent();
      long     window = (long)InpNewsBlockMinutes * 60;
      bool     blocked = false;

      // Scan from soonest, purge expired
      int writeIdx = 0;
      for(int i = 0; i < m_count; i++)
      {
         if(m_events[i] == 0) continue;

         long diff = (long)now - (long)m_events[i];

         if(diff > window)
         {
            // Post-window expired — drop this event (don't copy to writeIdx)
            continue;
         }

         // Keep this event
         m_events[writeIdx++] = m_events[i];

         if(MathAbs(diff) <= window) blocked = true;
      }

      // Zero out the now-empty tail
      for(int i = writeIdx; i < m_count; i++) m_events[i] = 0;
      m_count = writeIdx;

      return blocked;
   }

   // Minutes to the soonest queued event (negative = in the past)
   int MinutesToEvent()
   {
      if(m_count == 0) return 9999;
      return (int)((long)(m_events[0] - TimeCurrent()) / 60);
   }

   // Number of events currently queued (diagnostics)
   int QueueCount() const { return m_count; }
};
#endif // ASE_NEWSENGINE_MQH
