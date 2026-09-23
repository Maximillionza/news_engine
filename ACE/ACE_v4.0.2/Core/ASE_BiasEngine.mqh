#ifndef ASE_BIASENGINE_MQH
#define ASE_BIASENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — H4 Bias Engine                                          |
//| Logic: EMA50/200 crossover + price position                      |
//| Scores 0–30. Writes direction into context.direction.             |
//+------------------------------------------------------------------+
class CASE_BiasEngine
{
private:
   int m_fastHandle;   // EMA50  H4
   int m_slowHandle;   // EMA200 H4

public:
   CASE_BiasEngine() : m_fastHandle(INVALID_HANDLE),
                       m_slowHandle(INVALID_HANDLE) {}

   bool Initialize()
   {
      m_fastHandle = iMA(_Symbol, PERIOD_H4, InpH4FastEMA, 0, MODE_EMA, PRICE_CLOSE);
      m_slowHandle = iMA(_Symbol, PERIOD_H4, InpH4SlowEMA, 0, MODE_EMA, PRICE_CLOSE);

      return (m_fastHandle != INVALID_HANDLE && m_slowHandle != INVALID_HANDLE);
   }

   void Deinitialize()
   {
      if(m_fastHandle != INVALID_HANDLE) IndicatorRelease(m_fastHandle);
      if(m_slowHandle != INVALID_HANDLE) IndicatorRelease(m_slowHandle);
   }

   // direction is an output parameter — written by this engine
   ValidationResult Evaluate(ENUM_TRADE_DIRECTION &direction)
   {
      ValidationResult r;
      r.passed = false;
      r.reason = "No H4 bias";
      r.score  = 0.0;
      direction = DIR_NONE;

      double fast[], slow[];
      ArraySetAsSeries(fast, true);
      ArraySetAsSeries(slow, true);

      if(CopyBuffer(m_fastHandle, 0, 0, 3, fast) < 3) { r.reason = "BiasEngine: buffer read fail (fast)"; return r; }
      if(CopyBuffer(m_slowHandle, 0, 0, 3, slow) < 3) { r.reason = "BiasEngine: buffer read fail (slow)"; return r; }

      double price = iClose(_Symbol, PERIOD_H4, 1);

      bool bullFast = fast[0] > slow[0];
      bool bullSlope = fast[0] > fast[1];      // fast EMA rising
      bool priceAbove = price > fast[0];

      bool bearFast = fast[0] < slow[0];
      bool bearSlope = fast[0] < fast[1];      // fast EMA falling
      bool priceBelow = price < fast[0];

      if(bullFast && bullSlope)
      {
         direction   = DIR_LONG;
         r.passed    = true;
         r.reason    = "Bullish H4 bias (EMA" + IntegerToString(InpH4FastEMA) +
                       " > EMA" + IntegerToString(InpH4SlowEMA) + ")";
         r.score     = 25.0 + (priceAbove ? 5.0 : 0.0);  // bonus if price above fast
      }
      else if(bearFast && bearSlope)
      {
         direction   = DIR_SHORT;
         r.passed    = true;
         r.reason    = "Bearish H4 bias (EMA" + IntegerToString(InpH4FastEMA) +
                       " < EMA" + IntegerToString(InpH4SlowEMA) + ")";
         r.score     = 25.0 + (priceBelow ? 5.0 : 0.0);
      }
      else
      {
         r.reason = StringFormat("H4 EMAs mixed: fast=%.5f slow=%.5f", fast[0], slow[0]);
      }

      return r;
   }
};
#endif // ASE_BIASENGINE_MQH
