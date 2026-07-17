//+------------------------------------------------------------------+
//|                                                TDP_Planner.mqh    |
//|                                            Trade Desk Pro v1.0.0  |
//|  [PLAN] tab — thin launcher. All trade-planning UI now lives in   |
//|  the floating popup (TDP_PlannerDialog.mqh, CTDPPlannerDialog).   |
//|  This class only renders the docked "Start Planning" button and   |
//|  opens that popup on click.                                       |
//+------------------------------------------------------------------+
#property copyright "Trade Desk Pro"
#property strict

#ifndef TDP_PLANNER_MQH
#define TDP_PLANNER_MQH

#include "TDP_Panel.mqh"
#include "TDP_Settings.mqh"
#include "TDP_PlannerDialog.mqh"

class CTDPPlanner : public ITDPEventHandler
{
private:
   CTDPPanel          *m_panel;
   CTDPSettingsStore  *m_store;
   CTDPPlannerDialog  *m_dialog;

   string N(const string s) { return m_panel.Name("PLAN_" + s); }

public:
   CTDPPlanner() { m_dialog = NULL; }

   void Init(CTDPPanel *panel, CTDPSettingsStore *store, CTDPPlannerDialog *dialog)
   {
      m_panel = panel;
      m_store = store;
      m_dialog = dialog;
   }

   void Build()
   {
      int x = m_panel.PanelX();
      int w = m_panel.PanelWidth();
      int y = m_panel.ContentY();

      m_panel.CreateLabel(N("HINT"), x + 8, y, "Open the planner to size and place trades.", m_panel.clrTextDim, 7);
      m_panel.CreateButton(N("START_BTN"), x + 8, y + 20, w - 16, 28, "Start Planning", m_panel.clrAccent, m_panel.clrButtonText, 9);

      Refresh();
   }

   virtual void OnTDPEvent(const int id, const long &lparam, const double &dparam, const string &sparam) override
   {
      if(id == CHARTEVENT_OBJECT_CLICK && sparam == N("START_BTN"))
      {
         ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
         if(CheckPointer(m_dialog) != POINTER_INVALID)
            m_dialog.Open();
      }
      Refresh();
   }

   virtual void OnTDPTick() override { Refresh(); }

   void Refresh()
   {
      bool active = (m_panel.ActiveTab() == TDP_TAB_PLAN) && !m_panel.IsSettingsOpen() && !m_panel.IsCollapsed();
      m_panel.SetVisible(N("HINT"), active);
      m_panel.SetVisible(N("START_BTN"), active);
      if(active && CheckPointer(m_dialog) != POINTER_INVALID)
         m_panel.SetText(N("START_BTN"), m_dialog.IsOpen() ? "Planner Open — Bring to Front" : "Start Planning");
   }
};

#endif // TDP_PLANNER_MQH
