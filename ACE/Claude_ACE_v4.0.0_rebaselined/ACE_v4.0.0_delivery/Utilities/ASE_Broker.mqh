#ifndef ASE_BROKER_MQH
#define ASE_BROKER_MQH
//+------------------------------------------------------------------+
//| ASE v3 — Broker Utilities                                        |
//+------------------------------------------------------------------+
class CASE_Broker
{
public:
   static double GetSpread()
   {
      return (SymbolInfoDouble(_Symbol, SYMBOL_ASK) -
              SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;
   }

   static bool IsSpreadOK(double maxSpread)
   {
      return GetSpread() <= maxSpread;
   }

   static double GetAsk() { return SymbolInfoDouble(_Symbol, SYMBOL_ASK); }
   static double GetBid() { return SymbolInfoDouble(_Symbol, SYMBOL_BID); }

   static bool HasFreeMargin(double lotsNeeded)
   {
      double margin;
      if(!OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, lotsNeeded,
                          SymbolInfoDouble(_Symbol, SYMBOL_ASK), margin))
         return false;
      return margin <= AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   }
};
#endif // ASE_BROKER_MQH
