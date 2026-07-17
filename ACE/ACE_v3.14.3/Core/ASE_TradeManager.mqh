#ifndef ASE_TRADEMANAGER_MQH
#define ASE_TRADEMANAGER_MQH
#include <Trade/Trade.mqh>
#include "ASE_ATRTrailEngine.mqh"
#include "ASE_PartialTP.mqh"
#include "../Models/ASE_Config.mqh"
#include "../Utilities/ASE_Time.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Trade Manager                                           |
//| FIX #6: ATR handle moved to member variable — initialized once   |
//|          in Initialize() and released in Deinitialize() instead  |
//|          of being created and destroyed on every tick.            |
//+------------------------------------------------------------------+

#define STRUCT_TRAIL_PIVOT  3
#define STRUCT_TRAIL_BUFFER 0.3

class CASE_TradeManager
{
private:
   CTrade              m_trade;
   CASE_ATRTrailEngine m_trail;
   CASE_PartialTP      m_partial;
   double              m_tp1Level;
   bool                m_structTrailActive;
   int                 m_atrHandle;   // FIX #6 — persistent handle, not per-tick

public:
   CASE_TradeManager() : m_tp1Level(0.0), m_structTrailActive(false),
                         m_atrHandle(INVALID_HANDLE) {}

   bool Initialize()
   {
      m_tp1Level          = 0.0;
      m_structTrailActive = false;
      m_trade.SetExpertMagicNumber(InpMagicNumber);

      // FIX #6 — create ATR handle once here, not inside UpdateStructureTrail()
      m_atrHandle = iATR(_Symbol, PERIOD_M15, InpATRPeriod);
      if(m_atrHandle == INVALID_HANDLE)
      {
         Print("[TradeManager] INIT FAIL: ATR handle");
         return false;
      }

      if(!m_trail.Initialize())   return false;
      if(!m_partial.Initialize()) return false;
      return true;
   }

   void Deinitialize()
   {
      m_trail.Deinitialize();
      // FIX #6 — release the persistent handle
      if(m_atrHandle != INVALID_HANDLE)
      {
         IndicatorRelease(m_atrHandle);
         m_atrHandle = INVALID_HANDLE;
      }
   }

   void SetTP1(double tp1) { m_tp1Level = tp1; }

   void Manage(long magic)
   {
      UpdateStructureTrail();

      // v3.6.0 fix: ATR trail activates only after TP1 has been hit.
      // Previously the trail ran from the first tick after entry, meaning
      // a slow-grinding move could tighten the trail against a retracement
      // and stop the runner before TP1 was ever reached — defeating the
      // partial-close / runner split entirely.
      // PartialTP.HasAnyTP1Done() returns true the moment the first partial
      // close fires, which is the correct activation condition.
      if(m_partial.HasAnyTP1Done())
         m_trail.Update();

      m_partial.Process(m_tp1Level);
      m_partial.ClearClosed();
   }

   static double GetSessionRiskMultiplier()
   {
      if(CASE_Time::IsOverlap())   return 1.00;
      if(CASE_Time::IsLondon())    return 0.90;
      if(CASE_Time::IsNewYork())   return 0.85;
      return 0.0;
   }

private:
   //------------------------------------------------------------------
   // FIX #6 — Uses m_atrHandle (initialized once) instead of calling
   // iATR() + IndicatorRelease() on every tick.
   //------------------------------------------------------------------
   void UpdateStructureTrail()
   {
      if(!InpATRTrailEnabled) return;
      if(m_atrHandle == INVALID_HANDLE) return;

      double atrBuf[];
      ArraySetAsSeries(atrBuf, true);
      if(CopyBuffer(m_atrHandle, 0, 0, 1, atrBuf) < 1) return;
      double atrVal = atrBuf[0];

      int lookback = 30;
      double hi[], lo[];
      ArraySetAsSeries(hi, true);
      ArraySetAsSeries(lo, true);
      if(CopyHigh(_Symbol, PERIOD_M15, 0, lookback, hi) < lookback) return;
      if(CopyLow( _Symbol, PERIOD_M15, 0, lookback, lo) < lookback) return;

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket))                              continue;
         if(PositionGetString(POSITION_SYMBOL)  != _Symbol)              continue;
         if(PositionGetInteger(POSITION_MAGIC)  != InpMagicNumber)       continue;

         ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double currentSL = PositionGetDouble(POSITION_SL);
         double tp        = PositionGetDouble(POSITION_TP);
         double entry     = PositionGetDouble(POSITION_PRICE_OPEN);

         if(ptype == POSITION_TYPE_BUY)
         {
            double swingLow = 0.0;
            for(int b = STRUCT_TRAIL_PIVOT; b < lookback - STRUCT_TRAIL_PIVOT; b++)
            {
               bool isPivot = true;
               for(int k = 1; k <= STRUCT_TRAIL_PIVOT; k++)
                  if(lo[b] >= lo[b-k] || lo[b] >= lo[b+k]) { isPivot = false; break; }

               if(isPivot)
               {
                  double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                  if(lo[b] < bid) { swingLow = lo[b]; break; }
               }
            }

            if(swingLow > 0)
            {
               double newSL = NormalizeDouble(swingLow - atrVal * STRUCT_TRAIL_BUFFER,
                                              (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
               double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
               if(newSL > currentSL && newSL > entry && bid > entry)
               {
                  if(m_trade.PositionModify(ticket, newSL, tp))
                     Print(StringFormat("[StructTrail] LONG SL → %.5f (swing=%.5f)", newSL, swingLow));
               }
            }
         }
         else if(ptype == POSITION_TYPE_SELL)
         {
            double swingHigh = 0.0;
            for(int b = STRUCT_TRAIL_PIVOT; b < lookback - STRUCT_TRAIL_PIVOT; b++)
            {
               bool isPivot = true;
               for(int k = 1; k <= STRUCT_TRAIL_PIVOT; k++)
                  if(hi[b] <= hi[b-k] || hi[b] <= hi[b+k]) { isPivot = false; break; }

               if(isPivot)
               {
                  double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                  if(hi[b] > ask) { swingHigh = hi[b]; break; }
               }
            }

            if(swingHigh > 0)
            {
               double newSL = NormalizeDouble(swingHigh + atrVal * STRUCT_TRAIL_BUFFER,
                                              (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
               double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
               if((currentSL == 0 || newSL < currentSL) && newSL < entry && ask < entry)
               {
                  if(m_trade.PositionModify(ticket, newSL, tp))
                     Print(StringFormat("[StructTrail] SHORT SL → %.5f (swing=%.5f)", newSL, swingHigh));
               }
            }
         }
      }
   }
};
#endif // ASE_TRADEMANAGER_MQH
