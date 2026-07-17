#ifndef ASE_PARTIALTP_MQH
#define ASE_PARTIALTP_MQH
#include <Trade/Trade.mqh>
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Partial TP Engine (scale out at TP1)                    |
//| FIX #17: Volume normalization now uses SYMBOL_VOLUME_STEP-derived |
//|           decimal places instead of SYMBOL_DIGITS (price digits). |
//|           For GOLDmicro: VOLUME_STEP=0.01 → 2 decimal places,    |
//|           whereas SYMBOL_DIGITS=5 was rounding to price precision.|
//+------------------------------------------------------------------+
class CASE_PartialTP
{
private:
   CTrade m_trade;
   ulong  m_tp1Done[];
   int    m_tp1Count;

public:
   CASE_PartialTP() : m_tp1Count(0) { ArrayResize(m_tp1Done, 0); }

   bool Initialize()
   {
      m_trade.SetExpertMagicNumber(InpMagicNumber);
      return true;
   }

   void Process(double tp1Level)
   {
      if(!InpPartialTPEnabled) return;
      if(tp1Level <= 0)        return;

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket))                               continue;
         if(PositionGetString(POSITION_SYMBOL)  != _Symbol)               continue;
         if(PositionGetInteger(POSITION_MAGIC)  != InpMagicNumber)        continue;
         if(IsTP1Done(ticket))                                             continue;

         ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double price = (ptype == POSITION_TYPE_BUY)
                      ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                      : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

         bool atTP1 = (ptype == POSITION_TYPE_BUY  && price >= tp1Level) ||
                      (ptype == POSITION_TYPE_SELL && price <= tp1Level);

         if(atTP1)
         {
            double vol = PositionGetDouble(POSITION_VOLUME);

            // FIX #17 — normalize volume using VOLUME_STEP decimal precision,
            // not SYMBOL_DIGITS (which is for price, not lot size).
            double step      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
            double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
            int    volDigits = (step > 0) ? (int)MathRound(-MathLog10(step)) : 2;

            double closeVol = NormalizeDouble(vol * InpPartialTPPercent / 100.0, volDigits);
            if(closeVol < minLot) closeVol = minLot;

            if(m_trade.PositionClosePartial(ticket, closeVol))
            {
               MarkTP1Done(ticket);
               Print("[PartialTP] Ticket=", ticket, " Closed=", closeVol, " @ TP1=", tp1Level);

               double entry    = PositionGetDouble(POSITION_PRICE_OPEN);
               double tp       = PositionGetDouble(POSITION_TP);

               // v3.6.0 fix: BE level must account for spread so the remaining
               // runner is not stopped immediately when bid retraces to entry.
               // LONG: SL = entry + spread (ask-side break-even).
               // SHORT: SL = entry - spread (bid-side break-even).
               // Without this, a 30-pt GOLD spread stops the runner the instant
               // bid touches the open price on any trivial pullback.
               double spreadPts = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
               double beLevel;
               if(ptype == POSITION_TYPE_BUY)
                  beLevel = NormalizeDouble(entry + spreadPts,
                               (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
               else
                  beLevel = NormalizeDouble(entry - spreadPts,
                               (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));

               if(m_trade.PositionModify(ticket, beLevel, tp))
                  Print("[PartialTP] BE set | Ticket=", ticket,
                        " Entry=", entry, " Spread=", spreadPts,
                        " BE=", beLevel);
            }
         }
      }
   }

   void ClearClosed()
   {
      for(int i = m_tp1Count - 1; i >= 0; i--)
      {
         if(!PositionSelectByTicket(m_tp1Done[i]))
         {
            for(int j = i; j < m_tp1Count - 1; j++)
               m_tp1Done[j] = m_tp1Done[j+1];
            m_tp1Count--;
            ArrayResize(m_tp1Done, m_tp1Count);
         }
      }
   }

   // v3.6.0 — public so TradeManager can gate the ATR trail behind TP1.
   bool IsTP1Done(ulong ticket)
   {
      for(int i = 0; i < m_tp1Count; i++)
         if(m_tp1Done[i] == ticket) return true;
      return false;
   }

   // Returns true if ANY managed position has had TP1 hit.
   // Used by TradeManager to gate ATR trailing stop activation.
   bool HasAnyTP1Done() const { return (m_tp1Count > 0); }

private:
   void MarkTP1Done(ulong ticket)
   {
      m_tp1Count++;
      ArrayResize(m_tp1Done, m_tp1Count);
      m_tp1Done[m_tp1Count - 1] = ticket;
   }
};
#endif // ASE_PARTIALTP_MQH
