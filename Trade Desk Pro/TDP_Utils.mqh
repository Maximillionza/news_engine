//+------------------------------------------------------------------+
//|                                                   TDP_Utils.mqh   |
//|                                            Trade Desk Pro v1.0.0  |
//|  Shared enums, math helpers, ATR cache, symbol-info utilities.    |
//|  No on-chart object calls live in this file.                      |
//+------------------------------------------------------------------+
#property copyright "Trade Desk Pro"
#property strict

#ifndef TDP_UTILS_MQH
#define TDP_UTILS_MQH

//====================================================================
// Core constants
//====================================================================
#define TDP_MAGIC          999999
#define TDP_PREFIX         "TDP_"
#define TDP_MAX_TRADES     10

//====================================================================
// Enumerations
//====================================================================
enum ENUM_TDP_LOT_MODE   { TDP_LOT_RISK_BASED = 0, TDP_LOT_FIXED = 1 };
enum ENUM_TDP_RISK_TYPE  { TDP_RISK_PCT_BALANCE = 0, TDP_RISK_DOLLAR = 1 };
enum ENUM_TDP_RISK_DIST  { TDP_DIST_PER_TRADE = 0, TDP_DIST_SPLIT = 1 };
enum ENUM_TDP_ENTRY_MODE { TDP_ENTRY_IMMEDIATE = 0, TDP_ENTRY_PENDING = 1 };
enum ENUM_TDP_UNIT       { TDP_UNIT_POINTS = 0, TDP_UNIT_PIPS = 1, TDP_UNIT_PCT_PRICE = 2, TDP_UNIT_DOLLAR = 3 };
enum ENUM_TDP_SCOPE      { TDP_SCOPE_GLOBAL = 0, TDP_SCOPE_CHART = 1, TDP_SCOPE_SELECTED = 2 };
enum ENUM_TDP_APPLY_MODE { TDP_APPLY_ABSOLUTE = 0, TDP_APPLY_RELATIVE = 1 };
enum ENUM_TDP_THEME      { TDP_THEME_LIGHT = 0, TDP_THEME_DARK = 1 };
enum ENUM_TDP_TAB        { TDP_TAB_PLAN = 0, TDP_TAB_MANAGE = 1 };
enum ENUM_TDP_DIRECTION  { TDP_DIR_BUY = 0, TDP_DIR_SELL = 1 };

//====================================================================
// Basic symbol-info helpers
//====================================================================
double TDP_Point(const string sym)        { return SymbolInfoDouble(sym, SYMBOL_POINT); }
int    TDP_Digits(const string sym)       { return (int)SymbolInfoInteger(sym, SYMBOL_DIGITS); }
double TDP_Bid(const string sym)          { return SymbolInfoDouble(sym, SYMBOL_BID); }
double TDP_Ask(const string sym)          { return SymbolInfoDouble(sym, SYMBOL_ASK); }

double TDP_LotMin(const string sym)       { return SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN); }
double TDP_LotMax(const string sym)       { return SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX); }
double TDP_LotStep(const string sym)      { return SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP); }

//--- Minimum stop distance allowed by the broker, in points ---------
double TDP_StopsLevelPoints(const string sym)
{
   double level = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   double freeze = (double)SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   return MathMax(level, freeze);
}

//--- Spread, in points and in price terms ---------------------------
double TDP_SpreadPoints(const string sym)
{
   double point = TDP_Point(sym);
   if(point <= 0.0) return 0.0;
   return (TDP_Ask(sym) - TDP_Bid(sym)) / point;
}

double TDP_SpreadPrice(const string sym)
{
   return (TDP_Ask(sym) - TDP_Bid(sym));
}

//--- Points-per-pip: 10 on 3/5 digit symbols, 1 otherwise -----------
double TDP_PipPoints(const string sym)
{
   int d = TDP_Digits(sym);
   if(d == 3 || d == 5) return 10.0;
   return 1.0;
}

//--- Dollar value of one point move, for one standard lot -----------
double TDP_TickValuePerLot(const string sym)
{
   double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double point     = TDP_Point(sym);
   if(tickSize <= 0.0) return 0.0;
   return (tickValue / tickSize) * point;   // $ per point, per 1.0 lot
}

//--- Clamp a lot to broker min/max/step ------------------------------
double TDP_ClampLot(const string sym, double lot)
{
   double minLot  = TDP_LotMin(sym);
   double maxLot  = TDP_LotMax(sym);
   double step    = TDP_LotStep(sym);
   if(step <= 0.0) step = 0.01;

   if(lot < minLot) lot = minLot;
   if(lot > maxLot) lot = maxLot;

   double steps = MathRound((lot - minLot) / step);
   lot = minLot + steps * step;

   int stepDigits = 2;
   if(step >= 1.0) stepDigits = 0;
   else if(step >= 0.1) stepDigits = 1;
   else if(step >= 0.01) stepDigits = 2;
   else stepDigits = 3;

   lot = NormalizeDouble(lot, stepDigits);
   if(lot < minLot) lot = minLot;
   if(lot > maxLot) lot = maxLot;
   return lot;
}

//--- Lot size from a risk-money amount and SL distance (points) -----
double TDP_LotFromRisk(const string sym, double riskMoney, double slPoints)
{
   if(slPoints <= 0.0) return 0.0;
   double tvPerLot = TDP_TickValuePerLot(sym);
   if(tvPerLot <= 0.0) return 0.0;
   double rawLot = riskMoney / (slPoints * tvPerLot);
   return TDP_ClampLot(sym, rawLot);
}

//--- Dollar amount represented by a given lot over a points distance-
double TDP_MoneyAtPoints(const string sym, double lot, double points)
{
   return lot * points * TDP_TickValuePerLot(sym);
}

//====================================================================
// Unit conversion — SL/TP unit toggle: Points | Pips | %Price | $Amt
//====================================================================
// Converts an input value expressed in `unit` into a points distance.
// refPrice is required for the %-of-price conversion (typically the
// trade's entry price). The $-Amount conversion is expressed against
// a standard 1.0 lot tick value so it is independent of the trade's
// own (possibly not-yet-known) lot size — this avoids a circular
// dependency with the risk-based lot engine.
double TDP_UnitToPoints(const string sym, double value, ENUM_TDP_UNIT unit, double refPrice)
{
   double point = TDP_Point(sym);
   if(point <= 0.0) return 0.0;

   switch(unit)
   {
      case TDP_UNIT_POINTS:
         return value;
      case TDP_UNIT_PIPS:
         return value * TDP_PipPoints(sym);
      case TDP_UNIT_PCT_PRICE:
         if(refPrice <= 0.0) return 0.0;
         return ((value / 100.0) * refPrice) / point;
      case TDP_UNIT_DOLLAR:
      {
         double tvPerLot = TDP_TickValuePerLot(sym);
         if(tvPerLot <= 0.0) return 0.0;
         return value / tvPerLot;
      }
      default:
         return value;
   }
}

//--- Inverse: points distance back into the display unit ------------
double TDP_PointsToUnit(const string sym, double points, ENUM_TDP_UNIT unit, double refPrice)
{
   double point = TDP_Point(sym);
   switch(unit)
   {
      case TDP_UNIT_POINTS:
         return points;
      case TDP_UNIT_PIPS:
         return points / TDP_PipPoints(sym);
      case TDP_UNIT_PCT_PRICE:
         if(refPrice <= 0.0) return 0.0;
         return (points * point) / refPrice * 100.0;
      case TDP_UNIT_DOLLAR:
         return points * TDP_TickValuePerLot(sym);
      default:
         return points;
   }
}

string TDP_UnitLabel(ENUM_TDP_UNIT unit)
{
   switch(unit)
   {
      case TDP_UNIT_POINTS:    return "pts";
      case TDP_UNIT_PIPS:      return "pips";
      case TDP_UNIT_PCT_PRICE: return "%";
      case TDP_UNIT_DOLLAR:    return "$";
   }
   return "";
}

//====================================================================
// Price helpers
//====================================================================
double TDP_PriceOffset(double anchor, double points, double point, bool addDirection)
{
   return addDirection ? anchor + points * point : anchor - points * point;
}

//--- Margin required for one order ----------------------------------
double TDP_MarginRequired(const string sym, ENUM_ORDER_TYPE type, double volume, double price)
{
   double margin = 0.0;
   if(!OrderCalcMargin(type, sym, volume, price, margin))
      return 0.0;
   return margin;
}

//--- Loose market-open check -----------------------------------------
bool TDP_IsMarketOpen(const string sym)
{
   long tradeMode = SymbolInfoInteger(sym, SYMBOL_TRADE_MODE);
   if(tradeMode == SYMBOL_TRADE_MODE_DISABLED) return false;

   datetime serverTime = TimeTradeServer();
   MqlDateTime dt;
   TimeToStruct(serverTime, dt);
   datetime from, to;
   bool sessionOk = SymbolInfoSessionTrade(sym, (ENUM_DAY_OF_WEEK)dt.day_of_week, 0, from, to);
   if(!sessionOk) return false;

   // Quote freshness fallback — if last tick is stale, treat as closed.
   MqlTick tick;
   if(SymbolInfoTick(sym, tick))
   {
      if(serverTime - tick.time > 600) return false; // >10 min stale
   }
   return true;
}

//====================================================================
// Formatting helpers
//====================================================================
string TDP_FormatMoney(double v)
{
   string sign = (v < 0) ? "-" : "";
   double av = MathAbs(v);
   string s = StringFormat("%s$%s", sign, TDP_Thousands(av, 2));
   return s;
}

string TDP_FormatPct(double v, int digits = 2)
{
   string sign = (v > 0) ? "+" : "";
   return StringFormat("%s%.*f%%", sign, digits, v);
}

string TDP_FormatSignedMoney(double v)
{
   string sign = (v > 0) ? "+" : (v < 0 ? "-" : "");
   double av = MathAbs(v);
   return StringFormat("%s$%s", sign, TDP_Thousands(av, 2));
}

string TDP_FormatPrice(const string sym, double price)
{
   return DoubleToString(price, TDP_Digits(sym));
}

string TDP_FormatPoints(double points)
{
   string sign = (points > 0) ? "+" : "";
   return StringFormat("%s%.0f pts", sign, points);
}

//--- Thousands separator helper -------------------------------------
string TDP_Thousands(double v, int digits)
{
   string raw = DoubleToString(v, digits);
   string intPart = raw;
   string decPart = "";
   int dot = StringFind(raw, ".");
   if(dot >= 0)
   {
      intPart = StringSubstr(raw, 0, dot);
      decPart = StringSubstr(raw, dot);
   }
   int len = StringLen(intPart);
   string out = "";
   int count = 0;
   for(int i = len - 1; i >= 0; i--)
   {
      out = StringSubstr(intPart, i, 1) + out;
      count++;
      if(count % 3 == 0 && i != 0)
         out = "," + out;
   }
   return out + decPart;
}

//====================================================================
// ATR cache — one indicator handle per symbol, reused across calls.
//====================================================================
class CTDPAtrCache
{
private:
   string   m_symbols[];
   int      m_handles[];

   int FindOrCreate(const string sym)
   {
      for(int i = 0; i < ArraySize(m_symbols); i++)
         if(m_symbols[i] == sym) return m_handles[i];

      int handle = iATR(sym, PERIOD_H1, 14);
      int n = ArraySize(m_symbols);
      ArrayResize(m_symbols, n + 1);
      ArrayResize(m_handles, n + 1);
      m_symbols[n] = sym;
      m_handles[n] = handle;
      return handle;
   }

public:
   ~CTDPAtrCache()
   {
      for(int i = 0; i < ArraySize(m_handles); i++)
         if(m_handles[i] != INVALID_HANDLE)
            IndicatorRelease(m_handles[i]);
   }

   // Raw ATR(14, H1) value for the most recently closed bar.
   double GetATR(const string sym)
   {
      int handle = FindOrCreate(sym);
      if(handle == INVALID_HANDLE) return 0.0;
      double buf[];
      ArraySetAsSeries(buf, true);
      if(CopyBuffer(handle, 0, 1, 1, buf) <= 0) return 0.0;
      return buf[0];
   }

   // ATR(14, H1) x multiplier — the slippage / breakeven buffer.
   double GetBuffer(const string sym, double multiplier)
   {
      return GetATR(sym) * multiplier;
   }
};

#endif // TDP_UTILS_MQH
