#ifndef ASE_ATRTRAILENGINE_MQH
#define ASE_ATRTRAILENGINE_MQH
#include <Trade/Trade.mqh>
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — ATR Trailing Stop Engine                                |
//+------------------------------------------------------------------+
class CASE_ATRTrailEngine
{
private:
   CTrade m_trade;
   int    m_atrHandle;

public:
   CASE_ATRTrailEngine() : m_atrHandle(INVALID_HANDLE) {}

   bool Initialize()
   {
      m_trade.SetExpertMagicNumber(InpMagicNumber);
      m_atrHandle = iATR(_Symbol, PERIOD_M15, InpATRPeriod);
      return (m_atrHandle != INVALID_HANDLE);
   }

   void Deinitialize()
   {
      if(m_atrHandle != INVALID_HANDLE) IndicatorRelease(m_atrHandle);
   }

   void Update()
   {
      if(!InpATRTrailEnabled) return;

      double atr[];
      ArraySetAsSeries(atr, true);
      if(CopyBuffer(m_atrHandle, 0, 0, 1, atr) < 1) return;

      double trailDist = atr[0] * InpATRTrailMultiplier;

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol)  continue;
         if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

         ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double sl  = PositionGetDouble(POSITION_SL);
         double tp  = PositionGetDouble(POSITION_TP);

         if(ptype == POSITION_TYPE_BUY)
         {
            double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double newSL  = NormalizeDouble(bid - trailDist,
                              (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
            if(newSL > sl)
               m_trade.PositionModify(ticket, newSL, tp);
         }
         else if(ptype == POSITION_TYPE_SELL)
         {
            double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double newSL  = NormalizeDouble(ask + trailDist,
                              (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
            if(sl == 0 || newSL < sl)
               m_trade.PositionModify(ticket, newSL, tp);
         }
      }
   }
};
#endif // ASE_ATRTRAILENGINE_MQH
