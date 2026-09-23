#ifndef ASE_BROKERNORMALIZATION_MQH
#define ASE_BROKERNORMALIZATION_MQH
//+------------------------------------------------------------------+
//| ASE v3 — Broker Lot Normalization                                |
//+------------------------------------------------------------------+
class CASE_BrokerNormalization
{
public:
   double NormalizeLot(double lots)
   {
      double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

      if(step <= 0) step = 0.01;

      lots = MathMax(minLot, lots);
      lots = MathMin(maxLot, lots);
      lots = MathFloor(lots / step) * step;

      return NormalizeDouble(lots, 2);
   }
};
#endif // ASE_BROKERNORMALIZATION_MQH
