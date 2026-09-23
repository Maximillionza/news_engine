#ifndef ASE_MATH_MQH
#define ASE_MATH_MQH
//+------------------------------------------------------------------+
//| ASE v3 — Math Utilities                                          |
//+------------------------------------------------------------------+
class CASE_Math
{
public:
   static double Clamp(double v, double lo, double hi)
   {
      if(v < lo) return lo;
      if(v > hi) return hi;
      return v;
   }

   static double SafeDiv(double num, double den, double fallback = 0.0)
   {
      if(MathAbs(den) < 1e-10) return fallback;
      return num / den;
   }

   static double NormalizePrice(double price)
   {
      return NormalizeDouble(price, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   }

   static double RoundToTickSize(double price)
   {
      double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      if(tick <= 0) return price;
      return NormalizeDouble(MathRound(price / tick) * tick,
                             (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   }
};
#endif // ASE_MATH_MQH
