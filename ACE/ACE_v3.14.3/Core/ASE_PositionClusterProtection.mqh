#ifndef ASE_POSITIONCLUSTERPROTECTION_MQH
#define ASE_POSITIONCLUSTERPROTECTION_MQH
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Position Cluster Protection                             |
//+------------------------------------------------------------------+
class CASE_PositionClusterProtection
{
public:
   bool AllowNewTrade(int maxPositions)
   {
      int count = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL)  == _Symbol &&
            PositionGetInteger(POSITION_MAGIC)  == InpMagicNumber)
            count++;
      }
      return (count < maxPositions);
   }

   int CountOpen()
   {
      int count = 0;
      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL)  == _Symbol &&
            PositionGetInteger(POSITION_MAGIC)  == InpMagicNumber)
            count++;
      }
      return count;
   }
};
#endif // ASE_POSITIONCLUSTERPROTECTION_MQH
