#ifndef ASE_CHARTVISUALS_MQH
#define ASE_CHARTVISUALS_MQH
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ACE — Chart Visuals (key markers only)                            |
//|                                                                    |
//| Deliberately narrow scope, per explicit request: show ONLY the     |
//| pivot-based support/resistance levels the structure engine is      |
//| actually tracking, and mark a BOS the moment it confirms. No FVG    |
//| zones, no liquidity markers, no EMA lines, no score/regime HUD —    |
//| those were considered and explicitly declined in favour of         |
//| keeping the chart uncluttered.                                     |
//|                                                                    |
//| v3.14.17 Fix 24 — added one exception to that scope, also on       |
//| explicit request: a compact active-trade panel (entry/SL/TP1/TP2,  |
//| unrealized R, protection state) that exists ONLY while a position  |
//| is open and is deleted the instant it closes. Zero footprint the   |
//| rest of the time — the same "key info only" bar the BOS/SR         |
//| markers were held to, just applied to an in-trade context that     |
//| previously had no chart-level visibility at all.                   |
//|                                                                    |
//| Draws from data the structure engine already computes (the         |
//| persistent pivot registry, GetActivePivotHigh/Low) — this file      |
//| adds no new detection logic, only a visual layer on top.           |
//+------------------------------------------------------------------+
class CASE_ChartVisuals
{
private:
   double   m_lastDrawnHigh;
   double   m_lastDrawnLow;
   int      m_bosMarkerCount;
   string   m_prefix;

   string NameSRHigh() const { return m_prefix + "_SR_High"; }
   string NameSRLow()  const { return m_prefix + "_SR_Low";  }
   string NameBOS(datetime t) const { return m_prefix + "_BOS_" + IntegerToString((long)t); }
   string NameTradePanel() const { return m_prefix + "_TradePanel"; }

public:
   CASE_ChartVisuals() : m_lastDrawnHigh(0.0), m_lastDrawnLow(0.0),
                         m_bosMarkerCount(0), m_prefix("ACE_VIS") {}

   void Initialize(string prefix)
   {
      m_prefix = prefix + "_VIS";
   }

   //------------------------------------------------------------------
   // Resistance/support: one horizontal ray each, redrawn only when the
   // active pivot actually changes (a new pivot forms, or the old one
   // breaks and a different one becomes active). Cheap — this is a
   // move/no-op on every other call.
   //------------------------------------------------------------------
   void UpdateSR(double activeHigh, datetime highTime, double activeLow, datetime lowTime)
   {
      if(!InpShowChartVisuals) return;

      if(activeHigh > 0 && activeHigh != m_lastDrawnHigh)
      {
         DrawRay(NameSRHigh(), highTime, activeHigh, clrOrangeRed, "R: pivot high");
         m_lastDrawnHigh = activeHigh;
      }
      else if(activeHigh <= 0 && m_lastDrawnHigh != 0)
      {
         ObjectDelete(0, NameSRHigh());
         m_lastDrawnHigh = 0.0;
      }

      if(activeLow > 0 && activeLow != m_lastDrawnLow)
      {
         DrawRay(NameSRLow(), lowTime, activeLow, clrDodgerBlue, "S: pivot low");
         m_lastDrawnLow = activeLow;
      }
      else if(activeLow <= 0 && m_lastDrawnLow != 0)
      {
         ObjectDelete(0, NameSRLow());
         m_lastDrawnLow = 0.0;
      }
   }

   //------------------------------------------------------------------
   // BOS marker: one small arrow at the break bar/price, the instant a
   // fresh break-of-structure confirms. Capped at InpMaxBOSMarkers so a
   // chart left running for weeks doesn't accumulate clutter — oldest
   // marker is deleted once the cap is hit.
   //------------------------------------------------------------------
   void MarkBOS(datetime barTime, double price, bool isBullish)
   {
      if(!InpShowChartVisuals) return;

      string name = NameBOS(barTime);
      if(ObjectFind(0, name) >= 0) return;   // already marked this bar

      ObjectCreate(0, name, OBJ_ARROW, 0, barTime, price);
      ObjectSetInteger(0, name, OBJPROP_ARROWCODE, isBullish ? 233 : 234);   // up/down arrow
      ObjectSetInteger(0, name, OBJPROP_COLOR, isBullish ? clrLime : clrRed);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
      ObjectSetString(0, name, OBJPROP_TOOLTIP,
                       StringFormat("BOS %s @ %.5f", isBullish ? "bullish" : "bearish", price));
      m_bosMarkerCount++;

      TrimOldMarkers();
   }

   void Deinitialize()
   {
      ObjectDelete(0, NameSRHigh());
      ObjectDelete(0, NameSRLow());
      ObjectDelete(0, NameTradePanel());
      // BOS markers deliberately left on the chart after removal — they're
      // historical record of past breaks, not live state.
   }

   //------------------------------------------------------------------
   // Active trade lifecycle panel — added per explicit request, v3.14.17.
   // Renders ONLY while a position is open; deleted the instant it closes.
   // Deliberately still narrow: one compact label, not per-level chart
   // lines — same "key info only" philosophy as the BOS/SR markers above,
   // just applied to an in-trade context that has none today.
   //
   // Shows entry/SL/TP1/TP2, unrealized R (against the ORIGINAL SL
   // distance, so R stays meaningful even after SL moves), and a
   // Protection tag derived purely by comparing the position's live SL to
   // its own entry and original SL — no dependency on PartialTP's or
   // TradeManager's internal state, so this can't drift out of sync with
   // what those classes decide to do:
   //   NONE  — live SL unchanged from original (full risk still on)
   //   BE    — live SL sitting at/near entry (partial-close BE shift,
   //           v3.14.15's skip-path BE floor, or manual — all look the
   //           same from here, and functionally ARE the same: risk is
   //           capped near zero)
   //   TRAIL — live SL has moved beyond pure breakeven in the favorable
   //           direction (only the structural/ATR trail does this)
   //------------------------------------------------------------------
   void UpdateTradePanel(bool isLong, double entry, double origSL,
                         double curSL, double tp1, double tp2, double volume)
   {
      if(!InpShowChartVisuals) { ClearTradePanel(); return; }

      double bidask   = isLong ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                                : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double origRisk = MathAbs(entry - origSL);
      double moveNow  = isLong ? (bidask - entry) : (entry - bidask);
      double rMult    = (origRisk > 0) ? moveNow / origRisk : 0.0;

      double spreadPts = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
      string protection;
      if(MathAbs(curSL - origSL) < _Point)
         protection = "NONE";
      else if(isLong ? (curSL > entry + spreadPts + _Point) : (curSL < entry - spreadPts - _Point))
         protection = "TRAIL";
      else
         protection = "BE";

      int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      string text = StringFormat(
         "ACE Trade | %s %.2f\nEntry %.*f   SL %.*f\nTP1 %.*f   TP2 %.*f\n" +
         "Unrealized: %+.1f pts (%+.2fR)\nProtection: %s",
         isLong ? "LONG" : "SHORT", volume,
         digits, entry, digits, curSL, digits, tp1, digits, tp2,
         moveNow, rMult, protection);

      string name = NameTradePanel();
      if(ObjectFind(0, name) < 0)
      {
         ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
         ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
         ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 10);
         ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 20);
         ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
         ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
         ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, name, OBJPROP_BACK, false);
      }
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_COLOR,
                        protection == "NONE" ? clrSilver :
                        protection == "BE"   ? clrYellow : clrLime);
   }

   void ClearTradePanel()
   {
      if(ObjectFind(0, NameTradePanel()) >= 0) ObjectDelete(0, NameTradePanel());
   }

private:
   void DrawRay(string name, datetime anchorTime, double price, color clr, string tooltip)
   {
      if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
      // A ray from the pivot's own bar, extending right — visually ties
      // the level to where it formed rather than floating at bar 0.
      ObjectCreate(0, name, OBJ_TREND, 0, anchorTime, price, TimeCurrent() + PeriodSeconds(PERIOD_D1), price);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, tooltip);
   }

   void TrimOldMarkers()
   {
      if(InpMaxBOSMarkers <= 0) return;   // 0 = unlimited
      if(m_bosMarkerCount <= InpMaxBOSMarkers) return;

      // Find and delete the oldest BOS marker (lowest embedded timestamp).
      datetime oldest = 0;
      string   oldestName = "";
      int total = ObjectsTotal(0, 0, OBJ_ARROW);
      for(int i = 0; i < total; i++)
      {
         string nm = ObjectName(0, i, 0, OBJ_ARROW);
         if(StringFind(nm, m_prefix + "_BOS_") != 0) continue;
         datetime t = (datetime)ObjectGetInteger(0, nm, OBJPROP_TIME);
         if(oldest == 0 || t < oldest) { oldest = t; oldestName = nm; }
      }
      if(oldestName != "")
      {
         ObjectDelete(0, oldestName);
         m_bosMarkerCount--;
      }
   }
};
#endif
