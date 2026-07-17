//+------------------------------------------------------------------+
//|                                          TDP_PlannerDialog.mqh    |
//|                                            Trade Desk Pro v1.0.0  |
//|  Floating, draggable Trade Planner popup. Opened from the [PLAN]  |
//|  tab's "Start Planning" button (see the gutted CTDPPlanner in     |
//|  TDP_Planner.mqh). Built on its own private, corner-fixed object  |
//|  primitives (NOT CTDPPanel's) so it can float independently of    |
//|  the docked panel's corner/theme settings and survive tab swaps. |
//|  All trade-count / risk / entry-mode / card math is ported       |
//|  unchanged from CTDPPlanner.                                      |
//+------------------------------------------------------------------+
#property copyright "Trade Desk Pro"
#property strict

#ifndef TDP_PLANNERDIALOG_MQH
#define TDP_PLANNERDIALOG_MQH

#include "TDP_Panel.mqh"
#include "TDP_Settings.mqh"
#include <Trade\Trade.mqh>

// Per-trade computed snapshot — identical to TDP_Planner.mqh's TDP_CardCalc.
struct TDP_DlgCardCalc
{
   bool              valid;
   string            error;
   bool              sell;
   ENUM_ORDER_TYPE   orderType;
   bool              isPending;
   bool              spreadWarn;
   double            entryPrice;
   double            lot;
   double            slPrice, tpPrice;
   double            slPoints, tpPoints;
   double            riskMoney, profitMoney;
   double            marginReq;
   double            rr;
};

//====================================================================
// CTDPPlannerDialog — floating popup version of the Plan tab.
//====================================================================
class CTDPPlannerDialog : public ITDPEventHandler
{
private:
   CTDPPanel         *m_panel;     // read-only: theme colours + store access
   CTDPSettingsStore *m_store;
   CTrade             m_trade;

   bool               m_built;
   bool               m_open;

   // --- window geometry (own coordinate space, always CORNER_LEFT_UPPER)
   int                m_winX, m_winY;
   int                m_winW, m_winH;
   enum { TITLE_H = 22 };

   // --- drag state
   bool               m_dragging;
   int                m_dragOffX, m_dragOffY;

   // --- ported planning state (unchanged from CTDPPlanner) -------------
   int                m_count;
   ENUM_TDP_RISK_DIST m_riskDist;
   ENUM_TDP_RISK_TYPE m_riskType;
   ENUM_TDP_ENTRY_MODE m_entryMode;
   ENUM_TDP_UNIT      m_unit;
   bool               m_dirSell[TDP_MAX_TRADES];
   int                m_page;
   bool               m_confirmArmed;
   string             m_error;

   enum { CARDS_PER_PAGE = 3, CARD_H = 108 };

   string N(const string s) { return "TDPDLG_" + s; }
   string C(int i, const string s) { return "TDPDLG_C" + IntegerToString(i) + "_" + s; }

public:
   CTDPPlannerDialog()
   {
      m_built = false;
      m_open = false;
      m_dragging = false;
      m_winW = 360;
      m_winX = 60; m_winY = 60;
      m_count = 1;
      m_riskDist = TDP_DIST_PER_TRADE;
      m_riskType = TDP_RISK_PCT_BALANCE;
      m_entryMode = TDP_ENTRY_IMMEDIATE;
      m_unit = TDP_UNIT_POINTS;
      m_page = 0;
      m_confirmArmed = false;
      ArrayInitialize(m_dirSell, false);
   }

   void Init(CTDPPanel *panel, CTDPSettingsStore *store)
   {
      m_panel = panel;
      m_store = store;
      m_riskDist = store.riskDist;
      m_trade.SetExpertMagicNumber(TDP_MAGIC);
      m_trade.SetTypeFillingBySymbol(_Symbol);
      ChartSetInteger(0, CHART_EVENT_MOUSE_MOVE, true);
   }

   //----------------------------------------------------------------
   // Own object primitives — always CORNER_LEFT_UPPER, independent of
   // the docked panel's corner setting, so drag math stays simple
   // (mouse pixel coords == XDISTANCE/YDISTANCE coords, no conversion).
   //----------------------------------------------------------------
private:
   void CreateRect(const string name, int x, int y, int w, int h, color bg, color border)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, name, OBJPROP_COLOR, border);
      ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 10);
   }

   void CreateLabel(const string name, int x, int y, const string text, color clr, int fontSize = 8, const string font = "Calibri")
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetString(0, name, OBJPROP_FONT, font);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 11);
   }

   void CreateButton(const string name, int x, int y, int w, int h, const string text, color bg, color txt, int fontSize = 8)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
      ObjectSetInteger(0, name, OBJPROP_COLOR, txt);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, m_panel.clrBorder);
      ObjectSetInteger(0, name, OBJPROP_STATE, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 12);
   }

   void CreateEdit(const string name, int x, int y, int w, int h, const string text, color bg, color txt, bool readOnly = false, int align = ALIGN_CENTER)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_EDIT, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, name, OBJPROP_COLOR, txt);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, m_panel.clrBorder);
      ObjectSetInteger(0, name, OBJPROP_ALIGN, align);
      ObjectSetInteger(0, name, OBJPROP_READONLY, readOnly);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 12);
   }

   void SetText(const string name, const string text)
   {
      if(ObjectFind(0, name) >= 0) ObjectSetString(0, name, OBJPROP_TEXT, text);
   }

   string GetText(const string name) { return ObjectGetString(0, name, OBJPROP_TEXT); }

   void SetTextColor(const string name, color clr)
   {
      if(ObjectFind(0, name) >= 0) ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   }

   void SetBg(const string name, color clr)
   {
      if(ObjectFind(0, name) >= 0) ObjectSetInteger(0, name, OBJPROP_BGCOLOR, clr);
   }

   void SetVisible(const string name, bool show)
   {
      if(ObjectFind(0, name) < 0) return;
      ObjectSetInteger(0, name, OBJPROP_TIMEFRAMES, show ? OBJ_ALL_PERIODS : OBJ_NO_PERIODS);
   }

   bool Exists(const string name) { return ObjectFind(0, name) >= 0; }

   //----------------------------------------------------------------
   // Window-level: open / close / destroy / drag
   //----------------------------------------------------------------
public:
   bool IsOpen() const { return m_open; }

   void Open()
   {
      if(!m_built) Build();
      else BringToFront();
      m_open = true;
      Refresh();
   }

   // Raise every owned object's click/draw priority above whatever else
   // is on the chart — makes repeated "Start Planning" clicks behave like
   // a real window manager's "bring to front", since z-order is otherwise
   // fixed at creation time.
   void BringToFront()
   {
      int total = ObjectsTotal(0, -1, -1);
      for(int i = total - 1; i >= 0; i--)
      {
         string nm = ObjectName(0, i, -1, -1);
         if(StringFind(nm, "TDPDLG_") == 0)
         {
            long z = ObjectGetInteger(0, nm, OBJPROP_ZORDER);
            ObjectSetInteger(0, nm, OBJPROP_ZORDER, z + 100);
         }
      }
   }

   void CloseDlg()
   {
      m_open = false;
      Refresh();
   }

   void Destroy()
   {
      int total = ObjectsTotal(0, -1, -1);
      for(int i = total - 1; i >= 0; i--)
      {
         string nm = ObjectName(0, i, -1, -1);
         if(StringFind(nm, "TDPDLG_") == 0)
            ObjectDelete(0, nm);
      }
   }

private:
   bool InTitleBar(int mx, int my)
   {
      return mx >= m_winX && mx <= m_winX + m_winW && my >= m_winY && my <= m_winY + TITLE_H;
   }

   // Shift every owned object's screen position by (dx,dy) — drag move.
   void ShiftAll(int dx, int dy)
   {
      if(dx == 0 && dy == 0) return;
      int total = ObjectsTotal(0, -1, -1);
      for(int i = total - 1; i >= 0; i--)
      {
         string nm = ObjectName(0, i, -1, -1);
         if(StringFind(nm, "TDPDLG_") == 0)
         {
            long curX = ObjectGetInteger(0, nm, OBJPROP_XDISTANCE);
            long curY = ObjectGetInteger(0, nm, OBJPROP_YDISTANCE);
            ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, curX + dx);
            ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, curY + dy);
         }
      }
   }

   void HandleMouseMove(const long &lparam, const double &dparam, const string &sparam)
   {
      if(!m_open) return;
      int mx = (int)lparam;
      int my = (int)dparam;
      int state = (int)StringToInteger(sparam);
      bool leftDown = (state & 1) != 0;

      if(!m_dragging)
      {
         if(leftDown && InTitleBar(mx, my))
         {
            m_dragging = true;
            m_dragOffX = mx - m_winX;
            m_dragOffY = my - m_winY;
         }
         return;
      }

      if(!leftDown) { m_dragging = false; return; }

      int newX = mx - m_dragOffX;
      int newY = my - m_dragOffY;
      ShiftAll(newX - m_winX, newY - m_winY);
      m_winX = newX;
      m_winY = newY;
      ChartRedraw(0);
   }

   //----------------------------------------------------------------
   // Build — title bar + chrome + ported planning controls + cards.
   // Geometry mirrors CTDPPlanner::Build()/BuildCard() exactly, just
   // re-anchored to (m_winX, m_winY+TITLE_H) instead of the docked
   // panel's (PanelX(), ContentY()).
   //----------------------------------------------------------------
   void Build()
   {
      int x = m_winX;
      int w = m_winW;

      CreateRect(N("TITLEBAR"), x, m_winY, w, TITLE_H, m_panel.clrAccent, m_panel.clrBorder);
      CreateLabel(N("TITLE"), x + 8, m_winY + 4, "Trade Planner", m_panel.clrButtonText, 9, "Calibri Bold");
      CreateButton(N("CLOSE"), x + w - 24, m_winY + 2, 18, 18, "X", m_panel.clrButtonBg, m_panel.clrText, 8);

      int y = m_winY + TITLE_H + 4;
      CreateRect(N("BODY_BG"), x, y, w, 0, m_panel.clrPanelBg, m_panel.clrBorder); // resized below once height known
      y += 4;

      // --- Trade count -------------------------------------------------
      CreateButton(N("CNT_MINUS"), x + 8, y, 24, 20, "-", m_panel.clrButtonBg, m_panel.clrText, 9);
      CreateLabel(N("CNT_LBL"), x + 38, y + 4, "1 Trade", m_panel.clrText, 8, "Calibri Bold");
      CreateButton(N("CNT_PLUS"), x + w - 32, y, 24, 20, "+", m_panel.clrButtonBg, m_panel.clrText, 9);
      y += 24;

      // --- Risk distribution (N>1 only) ---------------------------------
      CreateLabel(N("DIST_LBL"), x + 8, y + 4, "Risk Distribution", m_panel.clrTextDim, 7);
      CreateButton(N("DIST_A"), x + w - 168, y, 78, 20, "Per Trade", m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateButton(N("DIST_B"), x + w - 86,  y, 78, 20, "Split",     m_panel.clrButtonBg, m_panel.clrText, 7);
      y += 24;

      // --- Risk amount (Risk-Based lot mode only) -----------------------
      CreateLabel(N("RISK_LBL"), x + 8, y + 4, "Risk Amount", m_panel.clrTextDim, 7);
      CreateButton(N("RTYPE_A"), x + w - 168, y, 50, 20, "% Bal", m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateButton(N("RTYPE_B"), x + w - 118, y, 50, 20, "$ Amt", m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateEdit(N("RISK_EDIT"), x + w - 64, y, 56, 20, DoubleToString(m_store.defaultRiskPct, 2), m_panel.clrInputBg, m_panel.clrText, false);
      y += 24;

      // --- Entry mode -----------------------------------------------------
      CreateLabel(N("ENTRY_LBL"), x + 8, y + 4, "Entry Mode", m_panel.clrTextDim, 7);
      CreateButton(N("ENTRY_A"), x + w - 168, y, 78, 20, "Immediate", m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateButton(N("ENTRY_B"), x + w - 86,  y, 78, 20, "Pending",   m_panel.clrButtonBg, m_panel.clrText, 7);
      y += 24;

      // --- SL / TP unit -----------------------------------------------------
      CreateLabel(N("UNIT_LBL"), x + 8, y + 4, "SL / TP Unit", m_panel.clrTextDim, 7);
      int bw = 41;
      CreateButton(N("UNIT_PTS"),  x + w - 168,          y, bw, 20, "Pts",  m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateButton(N("UNIT_PIPS"), x + w - 168 + bw,     y, bw, 20, "Pips", m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateButton(N("UNIT_PCT"),  x + w - 168 + bw * 2, y, bw, 20, "%Px",  m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateButton(N("UNIT_DOL"),  x + w - 168 + bw * 3, y, bw, 20, "$",    m_panel.clrButtonBg, m_panel.clrText, 7);
      y += 28;

      int cardsTop = y;
      for(int i = 0; i < TDP_MAX_TRADES; i++)
         BuildCard(i, x, w, cardsTop);

      int afterCards = cardsTop + CARDS_PER_PAGE * (CARD_H + 4);

      // --- Pager -----------------------------------------------------------
      CreateButton(N("PAGE_PREV"), x + 8, afterCards, 50, 18, "< Prev", m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateLabel(N("PAGE_LBL"), x + w / 2 - 24, afterCards + 2, "Page 1/1", m_panel.clrTextDim, 7);
      CreateButton(N("PAGE_NEXT"), x + w - 58, afterCards, 50, 18, "Next >", m_panel.clrButtonBg, m_panel.clrText, 7);
      afterCards += 22;

      // --- Combined totals (N>1) -------------------------------------------
      CreateLabel(N("TOTALS"), x + 8, afterCards, "", m_panel.clrText, 7, "Calibri Bold");
      afterCards += 18;

      // --- Validation error --------------------------------------------------
      CreateLabel(N("ERROR"), x + 8, afterCards, "", m_panel.clrDown, 7);
      afterCards += 18;

      // --- Place orders --------------------------------------------------------
      CreateButton(N("PLACE_BTN"), x + 8, afterCards, w - 16, 26, "Place Orders", m_panel.clrAccent, m_panel.clrButtonText, 9);
      afterCards += 26 + 8;

      m_winH = afterCards - m_winY;
      ObjectSetInteger(0, N("BODY_BG"), OBJPROP_YSIZE, m_winH - TITLE_H - 4);

      m_built = true;
      SetGroupVisible(false); // start hidden until Open() is called
   }

   void BuildCard(int i, int x, int w, int top)
   {
      int y = top + i * (CARD_H + 4);
      CreateRect(C(i, "BG"), x, y, w, CARD_H, m_panel.clrCardBg, m_panel.clrBorder);
      CreateLabel(C(i, "TITLE"), x + 8, y + 4, "Trade #" + IntegerToString(i + 1), m_panel.clrText, 8, "Calibri Bold");
      CreateButton(C(i, "DIRA"), x + w - 168, y + 2, 38, 16, "BUY",  m_panel.clrUp, m_panel.clrButtonText, 7);
      CreateButton(C(i, "DIRB"), x + w - 128, y + 2, 38, 16, "SELL", m_panel.clrButtonBg, m_panel.clrText, 7);
      CreateLabel(C(i, "BADGE"), x + w - 86, y + 4, "[MARKET]", m_panel.clrAccent, 7, "Calibri Bold");

      int r1 = y + 20;
      CreateLabel(C(i, "ENTRY_LBL"), x + 8, r1 + 3, "Entry:", m_panel.clrTextDim, 7);
      CreateEdit(C(i, "ENTRY_EDIT"), x + 52, r1, 84, 18, "", m_panel.clrInputBg, m_panel.clrText, false);
      CreateLabel(C(i, "LOT_LBL"), x + w / 2 + 8, r1 + 3, "Lot:", m_panel.clrTextDim, 7);
      CreateEdit(C(i, "LOT_EDIT"), x + w / 2 + 38, r1, 70, 18, "0.01", m_panel.clrInputBg, m_panel.clrText, true);

      int r2 = y + 38;
      CreateLabel(C(i, "SL_LBL"), x + 8, r2 + 3, "SL:", m_panel.clrTextDim, 7);
      CreateEdit(C(i, "SL_EDIT"), x + 30, r2, 60, 18, "", m_panel.clrInputBg, m_panel.clrText, false);
      CreateLabel(C(i, "SL_INFO"), x + 96, r2 + 3, "", m_panel.clrTextDim, 7);
      CreateLabel(C(i, "RISK_INFO"), x + w - 96, r2 + 3, "", m_panel.clrText, 7);

      int r3 = y + 56;
      CreateLabel(C(i, "TP_LBL"), x + 8, r3 + 3, "TP:", m_panel.clrTextDim, 7);
      CreateEdit(C(i, "TP_EDIT"), x + 30, r3, 60, 18, "", m_panel.clrInputBg, m_panel.clrText, false);
      CreateLabel(C(i, "TP_INFO"), x + 96, r3 + 3, "", m_panel.clrTextDim, 7);
      CreateLabel(C(i, "PROFIT_INFO"), x + w - 96, r3 + 3, "", m_panel.clrText, 7);

      int r4 = y + 74;
      CreateLabel(C(i, "RR_INFO"), x + 8, r4 + 3, "R:R  —", m_panel.clrText, 7);
      CreateLabel(C(i, "MARGIN_INFO"), x + w - 140, r4 + 3, "", m_panel.clrText, 7);

      int r5 = y + 92;
      CreateLabel(C(i, "EXPIRY_LBL"), x + 8, r5 + 3, "Expiry:", m_panel.clrTextDim, 7);
      CreateEdit(C(i, "EXPIRY_EDIT"), x + 52, r5, 110, 18, "", m_panel.clrInputBg, m_panel.clrText, false);
      CreateLabel(C(i, "WARN"), x + 8, r5 + 3, "", m_panel.clrWarn, 7, "Calibri Bold");
   }

   // Show/hide every object this dialog owns (title bar + body + cards).
   void SetGroupVisible(bool show)
   {
      SetVisible(N("TITLEBAR"), show);
      SetVisible(N("TITLE"), show);
      SetVisible(N("CLOSE"), show);
      SetVisible(N("BODY_BG"), show);
      string parts[] = {"CNT_MINUS","CNT_LBL","CNT_PLUS","DIST_LBL","DIST_A","DIST_B",
                         "RISK_LBL","RTYPE_A","RTYPE_B","RISK_EDIT","ENTRY_LBL","ENTRY_A","ENTRY_B",
                         "UNIT_LBL","UNIT_PTS","UNIT_PIPS","UNIT_PCT","UNIT_DOL",
                         "PAGE_PREV","PAGE_LBL","PAGE_NEXT","TOTALS","ERROR","PLACE_BTN"};
      for(int k = 0; k < ArraySize(parts); k++)
         SetVisible(N(parts[k]), show);
      for(int i = 0; i < TDP_MAX_TRADES; i++)
         SetCardVisible(i, false); // cards re-shown per page/count in Refresh()
   }

   void SetCardVisible(int i, bool show)
   {
      string parts[] = {"BG","TITLE","DIRA","DIRB","BADGE","ENTRY_LBL","ENTRY_EDIT","LOT_LBL","LOT_EDIT",
                         "SL_LBL","SL_EDIT","SL_INFO","RISK_INFO","TP_LBL","TP_EDIT","TP_INFO","PROFIT_INFO",
                         "RR_INFO","MARGIN_INFO","EXPIRY_LBL","EXPIRY_EDIT","WARN"};
      for(int k = 0; k < ArraySize(parts); k++)
         SetVisible(C(i, parts[k]), show);
   }

   int MaxPage() { return MathMax(0, (m_count - 1) / CARDS_PER_PAGE); }

   //----------------------------------------------------------------
public:
   virtual void OnTDPEvent(const int id, const long &lparam, const double &dparam, const string &sparam) override
   {
      if(!m_built) return;

      if(id == CHARTEVENT_MOUSE_MOVE)
      {
         HandleMouseMove(lparam, dparam, sparam);
         return;
      }

      if(!m_open) return;

      bool changed = false;

      if(id == CHARTEVENT_OBJECT_CLICK)
      {
         if(sparam == N("CLOSE")) { CloseDlg(); ObjectSetInteger(0, sparam, OBJPROP_STATE, false); return; }

         if(sparam == N("CNT_MINUS")) { m_count = MathMax(1, m_count - 1); changed = true; }
         else if(sparam == N("CNT_PLUS")) { m_count = MathMin(TDP_MAX_TRADES, m_count + 1); changed = true; }
         else if(sparam == N("DIST_A")) { m_riskDist = TDP_DIST_PER_TRADE; changed = true; }
         else if(sparam == N("DIST_B")) { m_riskDist = TDP_DIST_SPLIT; changed = true; }
         else if(sparam == N("RTYPE_A")) { m_riskType = TDP_RISK_PCT_BALANCE; changed = true; }
         else if(sparam == N("RTYPE_B")) { m_riskType = TDP_RISK_DOLLAR; changed = true; }
         else if(sparam == N("ENTRY_A")) { m_entryMode = TDP_ENTRY_IMMEDIATE; changed = true; }
         else if(sparam == N("ENTRY_B")) { m_entryMode = TDP_ENTRY_PENDING; changed = true; }
         else if(sparam == N("UNIT_PTS"))  { m_unit = TDP_UNIT_POINTS; changed = true; }
         else if(sparam == N("UNIT_PIPS")) { m_unit = TDP_UNIT_PIPS; changed = true; }
         else if(sparam == N("UNIT_PCT"))  { m_unit = TDP_UNIT_PCT_PRICE; changed = true; }
         else if(sparam == N("UNIT_DOL"))  { m_unit = TDP_UNIT_DOLLAR; changed = true; }
         else if(sparam == N("PAGE_PREV")) { m_page = MathMax(0, m_page - 1); changed = true; }
         else if(sparam == N("PAGE_NEXT")) { m_page = MathMin(MaxPage(), m_page + 1); changed = true; }
         else if(sparam == N("PLACE_BTN")) { OnPlaceClicked(); changed = true; }
         else
         {
            for(int i = 0; i < TDP_MAX_TRADES; i++)
            {
               if(sparam == C(i, "DIRA")) { m_dirSell[i] = false; changed = true; }
               else if(sparam == C(i, "DIRB")) { m_dirSell[i] = true; changed = true; }
            }
         }

         if(changed && ObjectFind(0, sparam) >= 0 && ObjectGetInteger(0, sparam, OBJPROP_TYPE) == OBJ_BUTTON)
            ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
      }

      if(id == CHARTEVENT_OBJECT_ENDEDIT)
      {
         string nm = sparam;
         if(StringFind(nm, "TDPDLG_") == 0)
            changed = true; // any edit field belonging to this dialog
      }

      if(changed)
      {
         m_confirmArmed = false;
         Refresh();
      }
   }

   virtual void OnTDPTick() override { if(m_open) Refresh(); }

   //----------------------------------------------------------------
   void Refresh()
   {
      if(!m_built) return;

      bool active = m_open && !m_panel.IsSettingsOpen();
      SetGroupVisible(active);
      if(!active) return;

      SetText(N("CNT_LBL"), IntegerToString(m_count) + (m_count == 1 ? " Trade" : " Trades"));

      bool showDist = m_count > 1;
      SetVisible(N("DIST_LBL"), showDist);
      SetVisible(N("DIST_A"), showDist);
      SetVisible(N("DIST_B"), showDist);
      SetBg(N("DIST_A"), m_riskDist == TDP_DIST_PER_TRADE ? m_panel.clrAccent : m_panel.clrButtonBg);
      SetBg(N("DIST_B"), m_riskDist == TDP_DIST_SPLIT ? m_panel.clrAccent : m_panel.clrButtonBg);

      bool riskBased = (m_store.lotMode == TDP_LOT_RISK_BASED);
      bool showRisk = riskBased;
      SetVisible(N("RISK_LBL"), showRisk);
      SetVisible(N("RTYPE_A"), showRisk);
      SetVisible(N("RTYPE_B"), showRisk);
      SetVisible(N("RISK_EDIT"), showRisk);
      SetBg(N("RTYPE_A"), m_riskType == TDP_RISK_PCT_BALANCE ? m_panel.clrAccent : m_panel.clrButtonBg);
      SetBg(N("RTYPE_B"), m_riskType == TDP_RISK_DOLLAR ? m_panel.clrAccent : m_panel.clrButtonBg);

      SetBg(N("ENTRY_A"), m_entryMode == TDP_ENTRY_IMMEDIATE ? m_panel.clrAccent : m_panel.clrButtonBg);
      SetBg(N("ENTRY_B"), m_entryMode == TDP_ENTRY_PENDING ? m_panel.clrAccent : m_panel.clrButtonBg);

      SetBg(N("UNIT_PTS"),  m_unit == TDP_UNIT_POINTS    ? m_panel.clrAccent : m_panel.clrButtonBg);
      SetBg(N("UNIT_PIPS"), m_unit == TDP_UNIT_PIPS      ? m_panel.clrAccent : m_panel.clrButtonBg);
      SetBg(N("UNIT_PCT"),  m_unit == TDP_UNIT_PCT_PRICE ? m_panel.clrAccent : m_panel.clrButtonBg);
      SetBg(N("UNIT_DOL"),  m_unit == TDP_UNIT_DOLLAR    ? m_panel.clrAccent : m_panel.clrButtonBg);

      double totalRisk = 0, totalMargin = 0;

      int pageStart = m_page * CARDS_PER_PAGE;
      for(int i = 0; i < TDP_MAX_TRADES; i++)
      {
         bool isActiveCard = (i < m_count);
         bool onPage = (i >= pageStart && i < pageStart + CARDS_PER_PAGE);
         bool show = isActiveCard && onPage;

         SetCardVisible(i, show);
         if(!isActiveCard) continue;

         TDP_DlgCardCalc calc;
         ComputeCard(i, calc);
         if(show) RenderCard(i, calc);

         if(calc.valid)
         {
            totalRisk += calc.riskMoney;
            totalMargin += calc.marginReq;
         }
      }

      bool showPager = m_count > CARDS_PER_PAGE;
      SetVisible(N("PAGE_PREV"), showPager);
      SetVisible(N("PAGE_NEXT"), showPager);
      SetVisible(N("PAGE_LBL"), showPager);
      int totalPages = MaxPage() + 1;
      SetText(N("PAGE_LBL"), "Page " + IntegerToString(m_page + 1) + "/" + IntegerToString(totalPages));

      bool showTotals = m_count > 1;
      SetVisible(N("TOTALS"), showTotals);
      if(showTotals)
         SetText(N("TOTALS"), IntegerToString(m_count) + " Trades   Total Risk: " + TDP_FormatMoney(totalRisk) +
                               "   Margin: " + TDP_FormatMoney(totalMargin));

      SetVisible(N("ERROR"), m_error != "");
      SetText(N("ERROR"), m_error);

      SetText(N("PLACE_BTN"), m_confirmArmed ? "Confirm Placement" : "Place Orders");
      SetBg(N("PLACE_BTN"), m_confirmArmed ? m_panel.clrWarn : m_panel.clrAccent);
   }

private:
   //----------------------------------------------------------------
   // Core math for one trade card — ported unchanged from CTDPPlanner.
   //----------------------------------------------------------------
   void ComputeCard(int i, TDP_DlgCardCalc &cc)
   {
      string sym = _Symbol;
      double point = TDP_Point(sym);
      double bid = TDP_Bid(sym), ask = TDP_Ask(sym);

      cc.valid = true;
      cc.error = "";
      cc.spreadWarn = false;
      cc.isPending = (m_entryMode == TDP_ENTRY_PENDING);

      string entryStr = GetText(C(i, "ENTRY_EDIT"));
      double entryInput = StringToDouble(entryStr);

      if(!cc.isPending)
      {
         cc.sell = m_dirSell[i];
         cc.entryPrice = cc.sell ? bid : ask;
         cc.orderType = cc.sell ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      }
      else
      {
         if(entryInput <= 0.0)
         {
            cc.valid = false;
            cc.error = "entry price required for pending order";
            cc.entryPrice = 0; cc.sell = false; cc.orderType = ORDER_TYPE_BUY_STOP;
         }
         else
         {
            cc.entryPrice = entryInput;
            if(entryInput > ask) { cc.sell = false; cc.orderType = ORDER_TYPE_BUY_STOP; }
            else if(entryInput < bid) { cc.sell = true; cc.orderType = ORDER_TYPE_SELL_STOP; }
            else
            {
               cc.spreadWarn = true;
               cc.sell = (ask - entryInput) > (entryInput - bid);
               cc.orderType = cc.sell ? ORDER_TYPE_SELL_STOP : ORDER_TYPE_BUY_STOP;
            }
         }
      }

      double slInput = StringToDouble(GetText(C(i, "SL_EDIT")));
      double tpInput = StringToDouble(GetText(C(i, "TP_EDIT")));

      cc.slPoints = (slInput > 0) ? TDP_UnitToPoints(sym, slInput, m_unit, cc.entryPrice) : 0.0;
      cc.tpPoints = (tpInput > 0) ? TDP_UnitToPoints(sym, tpInput, m_unit, cc.entryPrice) : 0.0;

      if(cc.valid)
      {
         cc.slPrice = (cc.slPoints > 0) ? TDP_PriceOffset(cc.entryPrice, cc.slPoints, point, cc.sell) : 0.0;
         cc.tpPrice = (cc.tpPoints > 0) ? TDP_PriceOffset(cc.entryPrice, cc.tpPoints, point, !cc.sell) : 0.0;
      }

      if(m_store.lotMode == TDP_LOT_RISK_BASED)
      {
         if(cc.slPoints <= 0.0)
         {
            cc.valid = false;
            cc.error = "Stop Loss required for Risk-Based sizing";
            cc.lot = 0.0;
         }
         else
         {
            double riskValue = StringToDouble(GetText(N("RISK_EDIT")));
            double riskMoneyTotalIntent = (m_riskType == TDP_RISK_PCT_BALANCE)
                                             ? (riskValue / 100.0) * AccountInfoDouble(ACCOUNT_BALANCE)
                                             : riskValue;
            double riskMoneyThisTrade = (m_riskDist == TDP_DIST_PER_TRADE)
                                             ? riskMoneyTotalIntent
                                             : riskMoneyTotalIntent / MathMax(1, m_count);
            cc.lot = TDP_LotFromRisk(sym, riskMoneyThisTrade, cc.slPoints);
            cc.riskMoney = riskMoneyThisTrade;
         }
      }
      else
      {
         double lotInput = StringToDouble(GetText(C(i, "LOT_EDIT")));
         cc.lot = TDP_ClampLot(sym, lotInput);
         cc.riskMoney = (cc.slPoints > 0) ? TDP_MoneyAtPoints(sym, cc.lot, cc.slPoints) : 0.0;
      }

      cc.profitMoney = (cc.tpPoints > 0) ? TDP_MoneyAtPoints(sym, cc.lot, cc.tpPoints) : 0.0;
      cc.rr = (cc.slPoints > 0 && cc.tpPoints > 0) ? (cc.tpPoints / cc.slPoints) : -1.0;
      cc.marginReq = (cc.lot > 0) ? TDP_MarginRequired(sym, cc.orderType, cc.lot, cc.entryPrice) : 0.0;

      if(cc.valid && cc.lot <= 0.0)
      {
         cc.valid = false;
         cc.error = "invalid lot size";
      }
   }

   void RenderCard(int i, const TDP_DlgCardCalc &cc)
   {
      string sym = _Symbol;
      bool pending = (m_entryMode == TDP_ENTRY_PENDING);

      SetVisible(C(i, "DIRA"), !pending);
      SetVisible(C(i, "DIRB"), !pending);
      SetBg(C(i, "DIRA"), (!cc.sell) ? m_panel.clrUp : m_panel.clrButtonBg);
      SetBg(C(i, "DIRB"), (cc.sell)  ? m_panel.clrDown   : m_panel.clrButtonBg);

      string badge;
      switch(cc.orderType)
      {
         case ORDER_TYPE_BUY:        badge = "[MARKET BUY]"; break;
         case ORDER_TYPE_SELL:       badge = "[MARKET SELL]"; break;
         case ORDER_TYPE_BUY_STOP:   badge = "[BUY STOP]"; break;
         case ORDER_TYPE_SELL_STOP:  badge = "[SELL STOP]"; break;
         default: badge = ""; break;
      }
      SetText(C(i, "BADGE"), badge);
      SetTextColor(C(i, "BADGE"), cc.sell ? m_panel.clrDown : m_panel.clrUp);

      SetVisible(C(i, "ENTRY_EDIT"), true);
      if(!pending)
         SetText(C(i, "ENTRY_EDIT"), TDP_FormatPrice(sym, cc.entryPrice));

      bool fixedMode = (m_store.lotMode == TDP_LOT_FIXED);
      SetText(C(i, "LOT_EDIT"), fixedMode ? GetText(C(i, "LOT_EDIT")) : DoubleToString(cc.lot, 2));

      SetText(C(i, "SL_INFO"), cc.slPoints > 0 ? (TDP_FormatPrice(sym, cc.slPrice) + "  (" + TDP_FormatPoints(-cc.slPoints) + ")") : "—");
      SetText(C(i, "RISK_INFO"), "Risk: " + (cc.slPoints > 0 ? TDP_FormatMoney(cc.riskMoney) : "—"));
      SetText(C(i, "TP_INFO"), cc.tpPoints > 0 ? (TDP_FormatPrice(sym, cc.tpPrice) + "  (" + TDP_FormatPoints(cc.tpPoints) + ")") : "—");
      SetText(C(i, "PROFIT_INFO"), "Profit: " + (cc.tpPoints > 0 ? TDP_FormatMoney(cc.profitMoney) : "—"));
      SetText(C(i, "RR_INFO"), cc.rr > 0 ? StringFormat("R:R  1 : %.2f", cc.rr) : "R:R  —");
      SetText(C(i, "MARGIN_INFO"), "Margin req: " + TDP_FormatMoney(cc.marginReq));

      SetVisible(C(i, "EXPIRY_LBL"), pending);
      SetVisible(C(i, "EXPIRY_EDIT"), pending);
      SetVisible(C(i, "WARN"), pending && cc.spreadWarn);
      SetText(C(i, "WARN"), cc.spreadWarn ? "Entry inside spread — confirm before placing" : "");

      ObjectSetInteger(0, C(i, "BG"), OBJPROP_COLOR, cc.valid ? m_panel.clrBorder : m_panel.clrDown);
   }

   //----------------------------------------------------------------
   // Pre-flight validation + placement — ported unchanged from CTDPPlanner.
   //----------------------------------------------------------------
   void OnPlaceClicked()
   {
      m_error = "";
      string sym = _Symbol;

      TDP_DlgCardCalc calcs[TDP_MAX_TRADES];
      double totalMargin = 0;
      bool anySpreadWarn = false;

      for(int i = 0; i < m_count; i++)
      {
         ComputeCard(i, calcs[i]);
         if(!calcs[i].valid)
         {
            m_error = "Trade #" + IntegerToString(i + 1) + ": " + calcs[i].error;
            m_confirmArmed = false;
            return;
         }
         totalMargin += calcs[i].marginReq;
         if(calcs[i].spreadWarn) anySpreadWarn = true;

         double stopsLevel = TDP_StopsLevelPoints(sym);
         if(calcs[i].slPoints > 0 && calcs[i].slPoints < stopsLevel)
         {
            m_error = "Trade #" + IntegerToString(i + 1) + ": SL distance below broker minimum (" + DoubleToString(stopsLevel, 0) + " pts)";
            m_confirmArmed = false;
            return;
         }
         if(calcs[i].tpPoints > 0 && calcs[i].tpPoints < stopsLevel)
         {
            m_error = "Trade #" + IntegerToString(i + 1) + ": TP distance below broker minimum (" + DoubleToString(stopsLevel, 0) + " pts)";
            m_confirmArmed = false;
            return;
         }
      }

      double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if(totalMargin > freeMargin)
      {
         m_error = "Insufficient free margin: requires " + TDP_FormatMoney(totalMargin) + ", available " + TDP_FormatMoney(freeMargin);
         m_confirmArmed = false;
         return;
      }

      if(!TDP_IsMarketOpen(sym))
      {
         m_error = "Market is closed for " + sym;
         m_confirmArmed = false;
         return;
      }

      if(anySpreadWarn && !m_confirmArmed)
      {
         m_error = "One or more entries sit inside the spread — press Confirm Placement to proceed";
         m_confirmArmed = true;
         return;
      }

      int placed = 0;
      for(int i = 0; i < m_count; i++)
      {
         TDP_DlgCardCalc cc = calcs[i];
         bool ok = false;
         double sl = (cc.slPoints > 0) ? cc.slPrice : 0.0;
         double tp = (cc.tpPoints > 0) ? cc.tpPrice : 0.0;

         if(cc.orderType == ORDER_TYPE_BUY)
            ok = m_trade.Buy(cc.lot, sym, 0.0, sl, tp, "TDP");
         else if(cc.orderType == ORDER_TYPE_SELL)
            ok = m_trade.Sell(cc.lot, sym, 0.0, sl, tp, "TDP");
         else
         {
            string expStr = GetText(C(i, "EXPIRY_EDIT"));
            datetime exp = (StringLen(expStr) > 0) ? StringToTime(expStr) : 0;
            ENUM_ORDER_TYPE_TIME timeType = (exp > 0) ? ORDER_TIME_SPECIFIED : ORDER_TIME_GTC;

            if(cc.orderType == ORDER_TYPE_BUY_STOP)
               ok = m_trade.BuyStop(cc.lot, cc.entryPrice, sym, sl, tp, timeType, exp, "TDP");
            else
               ok = m_trade.SellStop(cc.lot, cc.entryPrice, sym, sl, tp, timeType, exp, "TDP");
         }
         if(ok) placed++;
      }

      m_confirmArmed = false;
      if(placed == m_count)
      {
         m_error = "";
         CloseDlg();
      }
      else
         m_error = StringFormat("%d of %d orders placed — check terminal log for details", placed, m_count);

      if(m_store.collapseOnPlacement)
         m_panel.SetCollapsed(true);
   }
};

#endif // TDP_PLANNERDIALOG_MQH
