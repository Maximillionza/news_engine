//+------------------------------------------------------------------+
//|                                                   TDP_Panel.mqh   |
//|                                            Trade Desk Pro v1.0.0  |
//|  Lightweight on-chart GUI wrapper. ALL chart object creation and  |
//|  event routing lives here — no other module makes raw object      |
//|  calls. Planner / Manager / Settings build on these primitives.   |
//+------------------------------------------------------------------+
#property copyright "Trade Desk Pro"
#property strict

#ifndef TDP_PANEL_MQH
#define TDP_PANEL_MQH

#include "TDP_Utils.mqh"

//====================================================================
// Event-handler interface — Planner / Manager / Settings implement
// this so the panel can fan a chart event out to every module.
//====================================================================
class ITDPEventHandler
{
public:
   virtual void OnTDPEvent(const int id, const long &lparam, const double &dparam, const string &sparam) {}
   virtual void OnTDPTick() {}
};

//====================================================================
// CTDPPanel — chrome, theme, object primitives, event fan-out
//====================================================================
class CTDPPanel
{
private:
   string            m_prefix;
   ENUM_BASE_CORNER  m_corner;
   ENUM_TDP_THEME    m_theme;
   ENUM_TDP_TAB      m_activeTab;
   bool              m_settingsOpen;
   bool              m_collapsed;

   ITDPEventHandler *m_handlers[];

   int               m_x0, m_y0;
   int               m_width;

public:
   // Theme colours, public so other modules can read them directly.
   color clrBg, clrPanelBg, clrBorder, clrText, clrTextDim, clrAccent,
         clrUp, clrDown, clrWarn, clrHeaderBg, clrCardBg, clrButtonBg,
         clrButtonBg2, clrButtonText, clrInputBg;

   // Anonymous enum — MQL5 does not support inline-initialized
   // "static const int" class members, so layout constants live here.
   enum
   {
      PANEL_WIDTH = 360,
      MARGIN      = 8,
      TITLE_H     = 24,
      TAB_H       = 24,
      STATS_H     = 34,
      ROW_H       = 20,
      CARD_H      = 64
   };

   CTDPPanel() { m_settingsOpen = false; m_collapsed = false; m_activeTab = TDP_TAB_PLAN; }

   //----------------------------------------------------------------
   void Init(const string prefix, ENUM_BASE_CORNER corner, ENUM_TDP_THEME theme)
   {
      m_prefix = prefix;
      m_corner = corner;
      ApplyTheme(theme);
      RecomputeOrigin();
   }

   void RegisterHandler(ITDPEventHandler *h)
   {
      int n = ArraySize(m_handlers);
      ArrayResize(m_handlers, n + 1);
      m_handlers[n] = h;
   }

   //----------------------------------------------------------------
   // Theme
   //----------------------------------------------------------------
   void ApplyTheme(ENUM_TDP_THEME theme)
   {
      m_theme = theme;
      if(theme == TDP_THEME_LIGHT)
      {
         clrBg        = C'242,242,245';
         clrPanelBg   = C'250,250,252';
         clrHeaderBg  = C'230,232,238';
         clrCardBg    = C'255,255,255';
         clrBorder    = C'190,193,200';
         clrText      = C'30,30,34';
         clrTextDim   = C'110,113,120';
         clrAccent    = C'33,110,230';
         clrUp        = C'24,140,68';
         clrDown      = C'205,40,40';
         clrWarn      = C'196,150,10';
         clrButtonBg  = C'225,228,234';
         clrButtonBg2 = C'33,110,230';
         clrButtonText= C'25,25,28';
         clrInputBg   = C'255,255,255';
      }
      else
      {
         clrBg        = C'18,18,20';
         clrPanelBg   = C'28,28,32';
         clrHeaderBg  = C'38,38,44';
         clrCardBg    = C'34,34,40';
         clrBorder    = C'60,62,70';
         clrText      = C'230,230,235';
         clrTextDim   = C'150,152,160';
         clrAccent    = C'76,139,245';
         clrUp        = C'52,168,83';
         clrDown      = C'234,67,53';
         clrWarn      = C'230,180,40';
         clrButtonBg  = C'48,48,56';
         clrButtonBg2 = C'76,139,245';
         clrButtonText= C'230,230,235';
         clrInputBg   = C'24,24,28';
      }
      RepaintTheme();
   }

   ENUM_TDP_THEME Theme() const { return m_theme; }

   void SetCorner(ENUM_BASE_CORNER corner)
   {
      m_corner = corner;
      RecomputeOrigin();
      // Re-anchor every object already on the chart to the new corner —
      // x/y offsets are corner-relative, so the objects themselves don't
      // need to move, only their OBJPROP_CORNER reference point.
      int total = ObjectsTotal(0, -1, -1);
      for(int i = total - 1; i >= 0; i--)
      {
         string nm = ObjectName(0, i, -1, -1);
         if(StringFind(nm, m_prefix) == 0)
            ObjectSetInteger(0, nm, OBJPROP_CORNER, m_corner);
      }
   }
   ENUM_BASE_CORNER Corner() const { return m_corner; }

   //----------------------------------------------------------------
   // Layout geometry (other modules read these to place their objects)
   //----------------------------------------------------------------
   int PanelX() const { return m_x0; }
   int PanelY() const { return m_y0; }
   int PanelWidth() const { return m_width; }
   int ContentY() const { return m_y0 + TITLE_H + TAB_H + STATS_H + MARGIN; }
   ENUM_TDP_TAB ActiveTab() const { return m_activeTab; }
   bool IsSettingsOpen() const { return m_settingsOpen; }
   void CloseSettings() { m_settingsOpen = false; }
   bool IsCollapsed() const { return m_collapsed; }
   void SetCollapsed(bool v) { m_collapsed = v; }

   string Name(const string suffix) const { return m_prefix + suffix; }
   string GearBtnName() const  { return m_prefix + "NAV_GEAR"; }
   string PlanBtnName() const  { return m_prefix + "NAV_PLAN"; }
   string ManageBtnName() const{ return m_prefix + "NAV_MANAGE"; }

   //----------------------------------------------------------------
   // Chrome: title bar, tab bar, always-visible header stats block
   //----------------------------------------------------------------
   void BuildChrome(const string versionStr)
   {
      int x = m_x0, y = m_y0, w = m_width;

      CreateRect(Name("CHROME_BG"), x, y, w, TITLE_H + TAB_H + STATS_H, clrPanelBg, clrBorder);
      CreateLabel(Name("CHROME_TITLE"), x + 8, y + 5, "Trade Desk Pro  " + versionStr, clrText, 9, "Calibri Bold");
      CreateButton(GearBtnName(), x + w - 26, y + 2, 20, 20, "Set", clrButtonBg, clrText, 7);

      int tabW = w / 2;
      CreateButton(PlanBtnName(),   x,        y + TITLE_H, tabW,     TAB_H, "PLAN",    clrAccent,  clrButtonText, 8);
      CreateButton(ManageBtnName(), x + tabW, y + TITLE_H, w - tabW, TAB_H, "MANAGE",  clrButtonBg,clrButtonText, 8);

      int sy = y + TITLE_H + TAB_H + 3;
      CreateLabel(Name("HDR_LINE1"), x + 8, sy, "Equity: --   Margin Level: --   Open: 0 trades   Float P&L: $0.00", clrText, 7);
      CreateLabel(Name("HDR_LINE2"), x + 8, sy + 15, "Largest drawdown (scope): $0.00", clrTextDim, 7);

      ShowTab(m_activeTab);
   }

   void SetHeaderStats(const string line1, const string line2)
   {
      SetText(Name("HDR_LINE1"), line1);
      SetText(Name("HDR_LINE2"), line2);
   }

   //----------------------------------------------------------------
   // Tab visibility — objects are tagged by name convention:
   //   <prefix>PLAN_*    -> only visible on the PLAN tab
   //   <prefix>MANAGE_*  -> only visible on the MANAGE tab
   //   anything else     -> always visible (chrome / settings overlay)
   //----------------------------------------------------------------
   void ShowTab(ENUM_TDP_TAB tab)
   {
      m_activeTab = tab;
      int total = ObjectsTotal(0, -1, -1);
      string planTag   = m_prefix + "PLAN_";
      string manageTag = m_prefix + "MANAGE_";
      for(int i = total - 1; i >= 0; i--)
      {
         string nm = ObjectName(0, i, -1, -1);
         if(StringFind(nm, planTag) == 0)
            SetVisible(nm, tab == TDP_TAB_PLAN);
         else if(StringFind(nm, manageTag) == 0)
            SetVisible(nm, tab == TDP_TAB_MANAGE);
      }
      SetButtonActive(PlanBtnName(),   tab == TDP_TAB_PLAN);
      SetButtonActive(ManageBtnName(), tab == TDP_TAB_MANAGE);
   }

   void SetButtonActive(const string name, bool active)
   {
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, active ? clrAccent : clrButtonBg);
      ObjectSetInteger(0, name, OBJPROP_STATE, false);
   }

   //----------------------------------------------------------------
   // Event fan-out — called once from the EA's OnChartEvent
   //----------------------------------------------------------------
   void RouteEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
   {
      if(id == CHARTEVENT_OBJECT_CLICK)
      {
         if(sparam == PlanBtnName())   { ShowTab(TDP_TAB_PLAN); ObjectSetInteger(0, sparam, OBJPROP_STATE, false); }
         else if(sparam == ManageBtnName()) { ShowTab(TDP_TAB_MANAGE); ObjectSetInteger(0, sparam, OBJPROP_STATE, false); }
         else if(sparam == GearBtnName())
         {
            m_settingsOpen = !m_settingsOpen;
            ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
         }
      }

      for(int i = 0; i < ArraySize(m_handlers); i++)
         if(CheckPointer(m_handlers[i]) != POINTER_INVALID)
            m_handlers[i].OnTDPEvent(id, lparam, dparam, sparam);
   }

   void TickHandlers()
   {
      for(int i = 0; i < ArraySize(m_handlers); i++)
         if(CheckPointer(m_handlers[i]) != POINTER_INVALID)
            m_handlers[i].OnTDPTick();
   }

   //----------------------------------------------------------------
   // Object primitives
   //----------------------------------------------------------------
   void CreateRect(const string name, int x, int y, int w, int h, color bg, color border)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
      ObjectSetInteger(0, name, OBJPROP_CORNER, m_corner);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, name, OBJPROP_COLOR, border);
      ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 0);
   }

   void CreateLabel(const string name, int x, int y, const string text, color clr, int fontSize = 8, const string font = "Calibri")
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_CORNER, m_corner);
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetString(0, name, OBJPROP_FONT, font);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 1);
   }

   void CreateButton(const string name, int x, int y, int w, int h, const string text, color bg, color txt, int fontSize = 8)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_BUTTON, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
      ObjectSetInteger(0, name, OBJPROP_CORNER, m_corner);
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
      ObjectSetInteger(0, name, OBJPROP_COLOR, txt);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, clrBorder);
      ObjectSetInteger(0, name, OBJPROP_STATE, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 2);
   }

   void CreateEdit(const string name, int x, int y, int w, int h, const string text, color bg, color txt, bool readOnly = false, int align = ALIGN_CENTER)
   {
      if(ObjectFind(0, name) < 0)
         ObjectCreate(0, name, OBJ_EDIT, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, name, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, name, OBJPROP_YSIZE, h);
      ObjectSetInteger(0, name, OBJPROP_CORNER, m_corner);
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, name, OBJPROP_COLOR, txt);
      ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, name, OBJPROP_BORDER_COLOR, clrBorder);
      ObjectSetInteger(0, name, OBJPROP_ALIGN, align);
      ObjectSetInteger(0, name, OBJPROP_READONLY, readOnly);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_ZORDER, 2);
   }

   // Checkbox rendered as a small toggle button showing a check glyph.
   void CreateCheckbox(const string name, int x, int y, int size, bool checked)
   {
      CreateButton(name, x, y, size, size, checked ? "v" : "", clrInputBg, clrAccent, 8);
   }

   void SetChecked(const string name, bool checked)
   {
      SetText(name, checked ? "v" : "");
   }

   bool IsChecked(const string name)
   {
      return ObjectGetString(0, name, OBJPROP_TEXT) == "v";
   }

   void SetText(const string name, const string text)
   {
      if(ObjectFind(0, name) >= 0)
         ObjectSetString(0, name, OBJPROP_TEXT, text);
   }

   string GetText(const string name)
   {
      return ObjectGetString(0, name, OBJPROP_TEXT);
   }

   void SetTextColor(const string name, color clr)
   {
      if(ObjectFind(0, name) >= 0)
         ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   }

   void SetBg(const string name, color clr)
   {
      if(ObjectFind(0, name) >= 0)
         ObjectSetInteger(0, name, OBJPROP_BGCOLOR, clr);
   }

   void SetVisible(const string name, bool show)
   {
      if(ObjectFind(0, name) < 0) return;
      ObjectSetInteger(0, name, OBJPROP_TIMEFRAMES, show ? OBJ_ALL_PERIODS : OBJ_NO_PERIODS);
   }

   bool Exists(const string name)
   {
      return ObjectFind(0, name) >= 0;
   }

   void Delete(const string name)
   {
      if(ObjectFind(0, name) >= 0)
         ObjectDelete(0, name);
   }

   // Delete every object whose name starts with the given tag.
   void DeleteTagged(const string tag)
   {
      int total = ObjectsTotal(0, -1, -1);
      for(int i = total - 1; i >= 0; i--)
      {
         string nm = ObjectName(0, i, -1, -1);
         if(StringFind(nm, tag) == 0)
            ObjectDelete(0, nm);
      }
   }

   void DestroyAll()
   {
      DeleteTagged(m_prefix);
   }

private:
   void RecomputeOrigin()
   {
      m_width = PANEL_WIDTH;
      m_x0 = MARGIN;
      m_y0 = MARGIN;
   }

   // Re-colour chrome objects already on the chart after a theme change.
   void RepaintTheme()
   {
      if(!Exists(Name("CHROME_BG"))) return;
      SetBg(Name("CHROME_BG"), clrPanelBg);
      ObjectSetInteger(0, Name("CHROME_BG"), OBJPROP_COLOR, clrBorder);
      SetTextColor(Name("CHROME_TITLE"), clrText);
      SetTextColor(Name("HDR_LINE1"), clrText);
      SetTextColor(Name("HDR_LINE2"), clrTextDim);
      SetBg(GearBtnName(), clrButtonBg);
      SetButtonActive(PlanBtnName(),   m_activeTab == TDP_TAB_PLAN);
      SetButtonActive(ManageBtnName(), m_activeTab == TDP_TAB_MANAGE);
   }
};

#endif // TDP_PANEL_MQH
