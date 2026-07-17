//+------------------------------------------------------------------+
//|                                                TDP_Settings.mqh   |
//|                                            Trade Desk Pro v1.0.0  |
//|  Settings data store (persisted to GlobalVariables, prefix        |
//|  TDP_SETTING_) plus the gear-icon settings overlay, built on the  |
//|  CTDPPanel object primitives.                                     |
//+------------------------------------------------------------------+
#property copyright "Trade Desk Pro"
#property strict

#ifndef TDP_SETTINGS_MQH
#define TDP_SETTINGS_MQH

#include "TDP_Panel.mqh"

//====================================================================
// CTDPSettingsStore — values + GlobalVariable persistence
//====================================================================
class CTDPSettingsStore
{
public:
   ENUM_TDP_LOT_MODE  lotMode;
   ENUM_TDP_RISK_DIST riskDist;
   double             defaultRiskPct;
   double             atrMultiplier;
   double             closeInProfitPct;
   ENUM_BASE_CORNER   panelCorner;
   ENUM_TDP_THEME     theme;
   bool               collapseOnPlacement;

   CTDPSettingsStore() { LoadDefaults(); }

   void LoadDefaults()
   {
      lotMode             = TDP_LOT_RISK_BASED;
      riskDist            = TDP_DIST_PER_TRADE;
      defaultRiskPct      = 1.0;
      atrMultiplier       = 0.1;
      closeInProfitPct    = 1.0;
      panelCorner         = CORNER_LEFT_UPPER;
      theme               = TDP_THEME_LIGHT;
      collapseOnPlacement = false;
   }

   void Load()
   {
      lotMode             = (ENUM_TDP_LOT_MODE)GVGet("LOT_MODE", (double)TDP_LOT_RISK_BASED);
      riskDist            = (ENUM_TDP_RISK_DIST)GVGet("RISK_DIST", (double)TDP_DIST_PER_TRADE);
      defaultRiskPct      = GVGet("RISK_PCT", 1.0);
      atrMultiplier       = GVGet("ATR_MULT", 0.1);
      closeInProfitPct    = GVGet("CIP_PCT", 1.0);
      panelCorner         = (ENUM_BASE_CORNER)GVGet("CORNER", (double)CORNER_LEFT_UPPER);
      theme               = (ENUM_TDP_THEME)GVGet("THEME", (double)TDP_THEME_LIGHT);
      collapseOnPlacement = GVGet("COLLAPSE", 0.0) > 0.5;
   }

   void Save()
   {
      GVSet("LOT_MODE",  (double)lotMode);
      GVSet("RISK_DIST", (double)riskDist);
      GVSet("RISK_PCT",  defaultRiskPct);
      GVSet("ATR_MULT",  atrMultiplier);
      GVSet("CIP_PCT",   closeInProfitPct);
      GVSet("CORNER",    (double)panelCorner);
      GVSet("THEME",     (double)theme);
      GVSet("COLLAPSE",  collapseOnPlacement ? 1.0 : 0.0);
   }

private:
   string Key(const string suffix) { return "TDP_SETTING_" + suffix; }

   double GVGet(const string suffix, double dflt)
   {
      string key = Key(suffix);
      if(GlobalVariableCheck(key))
         return GlobalVariableGet(key);
      return dflt;
   }

   void GVSet(const string suffix, double value)
   {
      GlobalVariableSet(Key(suffix), value);
   }
};

//====================================================================
// CTDPSettingsPanel — the gear-icon overlay
//====================================================================
class CTDPSettingsPanel : public ITDPEventHandler
{
private:
   CTDPPanel        *m_panel;
   CTDPSettingsStore *m_store;
   bool              m_built;
   bool              m_wasOpen;

   // staged edits, committed to the store on [Save]
   ENUM_TDP_LOT_MODE  m_pLotMode;
   ENUM_TDP_RISK_DIST m_pRiskDist;
   ENUM_BASE_CORNER   m_pCorner;
   ENUM_TDP_THEME     m_pTheme;
   bool               m_pCollapse;

   int RowY(int row) { return m_panel.ContentY() + 28 + row * 24; }
   string N(const string s) { return m_panel.Name("SET_" + s); }

public:
   CTDPSettingsPanel() { m_built = false; m_wasOpen = false; }

   void Init(CTDPPanel *panel, CTDPSettingsStore *store)
   {
      m_panel = panel;
      m_store = store;
   }

   void Build()
   {
      int x = m_panel.PanelX();
      int w = m_panel.PanelWidth();
      int y = m_panel.ContentY();
      int h = 28 + 8 * 24 + 36;

      StageFromStore();

      m_panel.CreateRect(N("BG"), x, y, w, h, m_panel.clrPanelBg, m_panel.clrBorder);
      m_panel.CreateLabel(N("TITLE"), x + 8, y + 6, "Settings", m_panel.clrText, 9, "Calibri Bold");

      AddToggleRow(0, "Lot sizing mode",     "LOTMODE_A", "Risk-Based", "LOTMODE_B", "Fixed");
      AddToggleRow(1, "Risk distribution",   "RISKDIST_A", "Per Trade", "RISKDIST_B", "Split");
      AddEditRow  (2, "Default risk %",      "RISKPCT");
      AddEditRow  (3, "ATR slippage mult.",  "ATRMULT");
      AddEditRow  (4, "Close-in-profit %",   "CIPPCT");
      AddToggleRow4(5, "Panel corner anchor","CORNER_TL","TL","CORNER_TR","TR","CORNER_BL","BL","CORNER_BR","BR");
      AddToggleRow(6, "Panel colour theme",  "THEME_A", "Light", "THEME_B", "Dark");
      AddToggleRow(7, "Collapse on placement","COLLAPSE_A", "Yes", "COLLAPSE_B", "No");

      int by = RowY(8) + 4;
      m_panel.CreateButton(N("BTN_SAVE"),  x + w - 168, by, 78, 24, "Save",  m_panel.clrAccent, m_panel.clrButtonText, 8);
      m_panel.CreateButton(N("BTN_CLOSE"), x + w - 86,  by, 78, 24, "Close", m_panel.clrButtonBg, m_panel.clrButtonText, 8);

      m_built = true;
      Refresh();
   }

   void Refresh()
   {
      if(!m_built) return;
      bool open = m_panel.IsSettingsOpen();
      SetGroupVisible(open);
      if(open && !m_wasOpen)
         StageFromStore();
      if(open)
         RepaintToggles();
      m_wasOpen = open;
   }

   virtual void OnTDPEvent(const int id, const long &lparam, const double &dparam, const string &sparam) override
   {
      if(!m_built) return;

      if(id == CHARTEVENT_OBJECT_CLICK && m_panel.IsSettingsOpen())
      {
         bool matched = true;

         if(sparam == N("LOTMODE_A")) m_pLotMode = TDP_LOT_RISK_BASED;
         else if(sparam == N("LOTMODE_B")) m_pLotMode = TDP_LOT_FIXED;
         else if(sparam == N("RISKDIST_A")) m_pRiskDist = TDP_DIST_PER_TRADE;
         else if(sparam == N("RISKDIST_B")) m_pRiskDist = TDP_DIST_SPLIT;
         else if(sparam == N("CORNER_TL")) m_pCorner = CORNER_LEFT_UPPER;
         else if(sparam == N("CORNER_TR")) m_pCorner = CORNER_RIGHT_UPPER;
         else if(sparam == N("CORNER_BL")) m_pCorner = CORNER_LEFT_LOWER;
         else if(sparam == N("CORNER_BR")) m_pCorner = CORNER_RIGHT_LOWER;
         else if(sparam == N("THEME_A")) m_pTheme = TDP_THEME_LIGHT;
         else if(sparam == N("THEME_B")) m_pTheme = TDP_THEME_DARK;
         else if(sparam == N("COLLAPSE_A")) m_pCollapse = true;
         else if(sparam == N("COLLAPSE_B")) m_pCollapse = false;
         else if(sparam == N("BTN_SAVE"))
         {
            CommitToStore();
            m_store.Save();
            ApplyVisualSettings();
            m_panel.CloseSettings();
         }
         else if(sparam == N("BTN_CLOSE"))
         {
            m_panel.CloseSettings();
         }
         else
            matched = false;

         if(matched)
         {
            ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
            RepaintToggles();
         }
      }

      if(id == CHARTEVENT_OBJECT_ENDEDIT)
      {
         if(sparam == N("EDIT_RISKPCT") || sparam == N("EDIT_ATRMULT") || sparam == N("EDIT_CIPPCT"))
            RepaintToggles();
      }

      Refresh();
   }

private:
   void StageFromStore()
   {
      m_pLotMode  = m_store.lotMode;
      m_pRiskDist = m_store.riskDist;
      m_pCorner   = m_store.panelCorner;
      m_pTheme    = m_store.theme;
      m_pCollapse = m_store.collapseOnPlacement;
   }

   void CommitToStore()
   {
      m_store.lotMode             = m_pLotMode;
      m_store.riskDist            = m_pRiskDist;
      m_store.panelCorner         = m_pCorner;
      m_store.theme               = m_pTheme;
      m_store.collapseOnPlacement = m_pCollapse;
      m_store.defaultRiskPct      = StrToDoubleSafe(m_panel.GetText(N("EDIT_RISKPCT")), m_store.defaultRiskPct);
      m_store.atrMultiplier       = StrToDoubleSafe(m_panel.GetText(N("EDIT_ATRMULT")), m_store.atrMultiplier);
      m_store.closeInProfitPct    = StrToDoubleSafe(m_panel.GetText(N("EDIT_CIPPCT")), m_store.closeInProfitPct);
   }

   double StrToDoubleSafe(const string s, double fallback)
   {
      if(StringLen(s) == 0) return fallback;
      double v = StringToDouble(s);
      if(v <= 0.0 && s != "0") return fallback;
      return v;
   }

   void ApplyVisualSettings()
   {
      m_panel.SetCorner(m_pCorner);
      m_panel.ApplyTheme(m_pTheme);
   }

   void AddToggleRow(int row, const string label, const string nameA, const string textA, const string nameB, const string textB)
   {
      int x = m_panel.PanelX();
      int w = m_panel.PanelWidth();
      int y = RowY(row);
      m_panel.CreateLabel(N("LBL_" + nameA), x + 8, y + 4, label, m_panel.clrText, 7);
      m_panel.CreateButton(N(nameA), x + w - 168, y, 78, 20, textA, m_panel.clrButtonBg, m_panel.clrButtonText, 7);
      m_panel.CreateButton(N(nameB), x + w - 86,  y, 78, 20, textB, m_panel.clrButtonBg, m_panel.clrButtonText, 7);
   }

   void AddToggleRow4(int row, const string label, const string n1, const string t1, const string n2, const string t2,
                       const string n3, const string t3, const string n4, const string t4)
   {
      int x = m_panel.PanelX();
      int w = m_panel.PanelWidth();
      int y = RowY(row);
      int bw = 41;
      m_panel.CreateLabel(N("LBL_" + n1), x + 8, y + 4, label, m_panel.clrText, 7);
      m_panel.CreateButton(N(n1), x + w - 168,          y, bw, 20, t1, m_panel.clrButtonBg, m_panel.clrButtonText, 7);
      m_panel.CreateButton(N(n2), x + w - 168 + bw,     y, bw, 20, t2, m_panel.clrButtonBg, m_panel.clrButtonText, 7);
      m_panel.CreateButton(N(n3), x + w - 168 + bw * 2, y, bw, 20, t3, m_panel.clrButtonBg, m_panel.clrButtonText, 7);
      m_panel.CreateButton(N(n4), x + w - 168 + bw * 3, y, bw, 20, t4, m_panel.clrButtonBg, m_panel.clrButtonText, 7);
   }

   void AddEditRow(int row, const string label, const string tag)
   {
      int x = m_panel.PanelX();
      int w = m_panel.PanelWidth();
      int y = RowY(row);
      double val = 0;
      if(tag == "RISKPCT") val = m_store.defaultRiskPct;
      else if(tag == "ATRMULT") val = m_store.atrMultiplier;
      else if(tag == "CIPPCT") val = m_store.closeInProfitPct;
      m_panel.CreateLabel(N("LBL_" + tag), x + 8, y + 4, label, m_panel.clrText, 7);
      m_panel.CreateEdit(N("EDIT_" + tag), x + w - 86, y, 78, 20, DoubleToString(val, 2), m_panel.clrInputBg, m_panel.clrText, false);
   }

   void SetGroupVisible(bool show)
   {
      m_panel.SetVisible(N("BG"), show);
      m_panel.SetVisible(N("TITLE"), show);
      string tags[] = {"LOTMODE_A","LOTMODE_B","RISKDIST_A","RISKDIST_B","EDIT_RISKPCT","EDIT_ATRMULT","EDIT_CIPPCT",
                       "CORNER_TL","CORNER_TR","CORNER_BL","CORNER_BR","THEME_A","THEME_B","COLLAPSE_A","COLLAPSE_B",
                       "BTN_SAVE","BTN_CLOSE",
                       "LBL_LOTMODE_A","LBL_RISKDIST_A","LBL_RISKPCT","LBL_ATRMULT","LBL_CIPPCT","LBL_CORNER_TL","LBL_THEME_A","LBL_COLLAPSE_A"};
      for(int i = 0; i < ArraySize(tags); i++)
         m_panel.SetVisible(N(tags[i]), show);
   }

   void RepaintToggles()
   {
      Highlight(N("LOTMODE_A"), m_pLotMode == TDP_LOT_RISK_BASED);
      Highlight(N("LOTMODE_B"), m_pLotMode == TDP_LOT_FIXED);
      Highlight(N("RISKDIST_A"), m_pRiskDist == TDP_DIST_PER_TRADE);
      Highlight(N("RISKDIST_B"), m_pRiskDist == TDP_DIST_SPLIT);
      Highlight(N("CORNER_TL"), m_pCorner == CORNER_LEFT_UPPER);
      Highlight(N("CORNER_TR"), m_pCorner == CORNER_RIGHT_UPPER);
      Highlight(N("CORNER_BL"), m_pCorner == CORNER_LEFT_LOWER);
      Highlight(N("CORNER_BR"), m_pCorner == CORNER_RIGHT_LOWER);
      Highlight(N("THEME_A"), m_pTheme == TDP_THEME_LIGHT);
      Highlight(N("THEME_B"), m_pTheme == TDP_THEME_DARK);
      Highlight(N("COLLAPSE_A"), m_pCollapse == true);
      Highlight(N("COLLAPSE_B"), m_pCollapse == false);
   }

   void Highlight(const string name, bool active)
   {
      if(!m_panel.Exists(name)) return;
      m_panel.SetBg(name, active ? m_panel.clrAccent : m_panel.clrButtonBg);
   }
};

#endif // TDP_SETTINGS_MQH
