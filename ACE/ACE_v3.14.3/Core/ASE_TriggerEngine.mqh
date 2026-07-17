#ifndef ASE_TRIGGERENGINE_MQH
#define ASE_TRIGGERENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — M1 Trigger Engine                                       |
//| FIX #16: m_atrM15Handle removed. It was initialized, logged as   |
//|           "reference context only", and never actually used in   |
//|           any calculation. Removing it eliminates a live         |
//|           indicator handle slot wasted for nothing.              |
//+------------------------------------------------------------------+
class CASE_TriggerEngine
{
private:
   int m_atrM1Handle;    // M1 ATR — displacement threshold measurement
   int m_fastHandle;     // M1 fast EMA (fallback trigger)
   int m_slowHandle;     // M1 slow EMA (fallback trigger)
   // FIX #16 — m_atrM15Handle removed (was unused)

public:
   CASE_TriggerEngine() : m_atrM1Handle(INVALID_HANDLE),
                          m_fastHandle(INVALID_HANDLE),
                          m_slowHandle(INVALID_HANDLE) {}

   bool Initialize()
   {
      m_atrM1Handle = iATR(_Symbol, PERIOD_M1,  InpATRPeriod);
      m_fastHandle  = iMA(_Symbol, PERIOD_M1, InpM1FastEMA, 0, MODE_EMA, PRICE_CLOSE);
      m_slowHandle  = iMA(_Symbol, PERIOD_M1, InpM1SlowEMA, 0, MODE_EMA, PRICE_CLOSE);

      if(m_atrM1Handle == INVALID_HANDLE) Print("[TRIGGER] INIT FAIL: M1 ATR handle");
      if(m_fastHandle  == INVALID_HANDLE) Print("[TRIGGER] INIT FAIL: fast EMA handle");
      if(m_slowHandle  == INVALID_HANDLE) Print("[TRIGGER] INIT FAIL: slow EMA handle");

      return (m_atrM1Handle != INVALID_HANDLE &&
              m_fastHandle  != INVALID_HANDLE &&
              m_slowHandle  != INVALID_HANDLE);
   }

   void Deinitialize()
   {
      if(m_atrM1Handle != INVALID_HANDLE) IndicatorRelease(m_atrM1Handle);
      if(m_fastHandle  != INVALID_HANDLE) IndicatorRelease(m_fastHandle);
      if(m_slowHandle  != INVALID_HANDLE) IndicatorRelease(m_slowHandle);
   }

   // v3.6.0 — expose M1 ATR handle so StateMachine can snapshot M1 ATR
   // at trigger time for the entry timing slippage gate in ProcessExecution().
   int GetATRHandle() const { return m_atrM1Handle; }

   ValidationResult Evaluate(ENUM_TRADE_DIRECTION direction)
   {
      ValidationResult r;
      r.passed = false;
      r.reason = "No M1 trigger";
      r.score  = 0.0;

      if(direction == DIR_NONE) { r.reason = "Trigger: no direction from HTF"; return r; }

      double hi[], lo[], cl[], op[];
      ArraySetAsSeries(hi, true); ArraySetAsSeries(lo, true);
      ArraySetAsSeries(cl, true); ArraySetAsSeries(op, true);

      if(CopyHigh( _Symbol, PERIOD_M1, 0, 8, hi) < 8) { r.reason = "Trigger: H buffer fail"; return r; }
      if(CopyLow(  _Symbol, PERIOD_M1, 0, 8, lo) < 8) { r.reason = "Trigger: L buffer fail"; return r; }
      if(CopyClose(_Symbol, PERIOD_M1, 0, 8, cl) < 8) { r.reason = "Trigger: C buffer fail"; return r; }
      if(CopyOpen( _Symbol, PERIOD_M1, 0, 8, op) < 8) { r.reason = "Trigger: O buffer fail"; return r; }

      double atrM1[];
      ArraySetAsSeries(atrM1, true);
      if(CopyBuffer(m_atrM1Handle, 0, 0, 3, atrM1) < 3)
      {
         r.reason = "Trigger: M1 ATR buffer fail (warming up — wait a few bars)";
         return r;
      }
      double m1Atr = atrM1[0];

      if(m1Atr < _Point) { r.reason = "Trigger: M1 ATR=0 (no data)"; return r; }

      double candleOpen  = op[1];
      double candleClose = cl[1];
      double candleHigh  = hi[1];
      double candleLow   = lo[1];
      double body        = MathAbs(candleClose - candleOpen);
      double candleRange = candleHigh - candleLow;
      double bodyRatio   = (candleRange > _Point) ? body / candleRange : 0.0;

      bool bullCandle = candleClose > candleOpen;
      bool bearCandle = candleClose < candleOpen;

      // v3.4.5 fix: displacement requires BOTH the body/ATR size threshold
      // AND the candle closing in the trade direction. Previously `displaced`
      // was a direction-agnostic flag (true for any large candle regardless
      // of colour), and longDisplace/shortDisplace added the direction check
      // afterwards. The log contradiction on 2026-06-03 12:16 (body=81%,
      // mBOS=Y, disp=N) occurred because the candle body met the ratio
      // threshold but closed in the wrong direction for a SHORT, so
      // shortDisplace was false — correctly — but the log string printed
      // `disp=N` referencing the generic `displaced` flag, making it appear
      // the body check itself had failed. The fix splits displaced into two
      // direction-specific flags so the fail reason accurately reflects
      // which condition was unmet, and ensures the check is unambiguous.
      bool longDisplace  = (body >= m1Atr * 0.55) && (bodyRatio >= 0.60) && bullCandle && direction == DIR_LONG;
      bool shortDisplace = (body >= m1Atr * 0.55) && (bodyRatio >= 0.60) && bearCandle && direction == DIR_SHORT;
      bool displaced     = longDisplace || shortDisplace;   // unified flag for fail-reason log only

      double structHigh = hi[2];
      double structLow  = lo[2];
      for(int i = 3; i <= 6; i++)
      {
         if(hi[i] > structHigh) structHigh = hi[i];
         if(lo[i] < structLow)  structLow  = lo[i];
      }

      bool microBOSLong  = (cl[1] > structHigh) && direction == DIR_LONG;
      bool microBOSShort = (cl[1] < structLow)  && direction == DIR_SHORT;

      double upperWick = candleHigh - MathMax(candleOpen, candleClose);
      double lowerWick = MathMin(candleOpen, candleClose) - candleLow;

      bool longRejection  = (lowerWick > body * 1.5) && direction == DIR_LONG;
      bool shortRejection = (upperWick > body * 1.5) && direction == DIR_SHORT;

      double fast[], slow[];
      ArraySetAsSeries(fast, true); ArraySetAsSeries(slow, true);

      int fastCopied = CopyBuffer(m_fastHandle, 0, 0, 3, fast);
      int slowCopied = CopyBuffer(m_slowHandle, 0, 0, 3, slow);
      bool emaOK = (fastCopied == 3 && slowCopied == 3);

      if(!emaOK)
         Print(StringFormat("[TRIGGER] EMA buffers: fast=%d/3 slow=%d/3 (handles warming up)",
               fastCopied, slowCopied));

      bool emaLongAligned  = emaOK && fast[0] > slow[0] && direction == DIR_LONG;
      bool emaShortAligned = emaOK && fast[0] < slow[0] && direction == DIR_SHORT;

      if(direction == DIR_LONG)
      {
         if(longDisplace && microBOSLong)
         {
            r.passed = true; r.score = 20.0;
            r.reason = StringFormat("LONG Disp+mBOS | body=%.3f m1atr=%.3f(%.0f%%) StructH=%.3f",
                                    body, m1Atr, body/m1Atr*100, structHigh);
         }
         else if(longDisplace)
         {
            r.passed = true; r.score = 15.0;
            r.reason = StringFormat("LONG Displacement | body=%.3f m1atr=%.3f(%.0f%%) ratio=%.2f",
                                    body, m1Atr, body/m1Atr*100, bodyRatio);
         }
         else if(longRejection && (emaLongAligned || microBOSLong))
         {
            r.passed = true; r.score = 10.0;
            r.reason = StringFormat("LONG Rejection | lowerWick=%.3f body=%.3f", lowerWick, body);
         }
         else if(emaLongAligned)
         {
            r.passed = true; r.score = 7.0;
            r.reason = "LONG EMA aligned (fallback)";
         }
         else
         {
            r.reason = StringFormat(
               "LONG fail | disp=%s(body=%.3f/%.3f=%.0f%% bull=%s) mBOS=%s ema=%s",
               longDisplace?"Y":"N", body, m1Atr, body/m1Atr*100,
               bullCandle?"Y":"N",
               microBOSLong?"Y":"N", emaOK?"aligned":"no_data");
         }
      }
      else if(direction == DIR_SHORT)
      {
         if(shortDisplace && microBOSShort)
         {
            r.passed = true; r.score = 20.0;
            r.reason = StringFormat("SHORT Disp+mBOS | body=%.3f m1atr=%.3f(%.0f%%) StructL=%.3f",
                                    body, m1Atr, body/m1Atr*100, structLow);
         }
         else if(shortDisplace)
         {
            r.passed = true; r.score = 15.0;
            r.reason = StringFormat("SHORT Displacement | body=%.3f m1atr=%.3f(%.0f%%) ratio=%.2f",
                                    body, m1Atr, body/m1Atr*100, bodyRatio);
         }
         else if(shortRejection && (emaShortAligned || microBOSShort))
         {
            r.passed = true; r.score = 10.0;
            r.reason = StringFormat("SHORT Rejection | upperWick=%.3f body=%.3f", upperWick, body);
         }
         else if(emaShortAligned)
         {
            r.passed = true; r.score = 7.0;
            r.reason = "SHORT EMA aligned (fallback)";
         }
         else
         {
            r.reason = StringFormat(
               "SHORT fail | disp=%s(body=%.3f/%.3f=%.0f%% bear=%s) mBOS=%s ema=%s",
               shortDisplace?"Y":"N", body, m1Atr, body/m1Atr*100,
               bearCandle?"Y":"N",
               microBOSShort?"Y":"N", emaOK?"aligned":"no_data");
         }
      }

      return r;
   }

   string GetTriggerClass(const ValidationResult &r)
   {
      if(StringFind(r.reason, "Disp+mBOS")    >= 0) return "Disp+mBOS";
      if(StringFind(r.reason, "Displacement") >= 0) return "Displacement";
      if(StringFind(r.reason, "Rejection")    >= 0) return "Rejection";
      if(StringFind(r.reason, "EMA aligned")  >= 0) return "EMA_Fallback";
      return "None";
   }
};
#endif // ASE_TRIGGERENGINE_MQH
