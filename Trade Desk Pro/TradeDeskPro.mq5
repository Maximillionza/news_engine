//+------------------------------------------------------------------+
//|                                              TradeDeskPro.mq5     |
//|                                            Trade Desk Pro v1.0.0  |
//|                                                                    |
//|  Non-trading shell with CTrade execution and a full on-chart      |
//|  panel: a Trade Planner ([PLAN]) and a global Trade Manager       |
//|  ([MANAGE]), plus a Settings overlay.                              |
//|                                                                    |
//|  Magic number 999999 is fixed and does not change with version.  |
//|  Bump TDP_VERSION below on every release; update this header.     |
//+------------------------------------------------------------------+
#property copyright "Trade Desk Pro"
#property link      ""
#property version   "1.00"
#property strict
#property description "Trade Desk Pro — Trade Planner + global Trade Manager panel."

#define TDP_VERSION "v1.0.0"

#include "TDP_Utils.mqh"
#include "TDP_Panel.mqh"
#include "TDP_Settings.mqh"
#include "TDP_PlannerDialog.mqh"
#include "TDP_Planner.mqh"
#include "TDP_Manager.mqh"

CTDPSettingsStore  g_store;
CTDPPanel          g_panel;
CTDPPlannerDialog  g_plannerDialog;
CTDPPlanner        g_planner;
CTDPManager        g_manager;
CTDPSettingsPanel  g_settings;

//+------------------------------------------------------------------+
int OnInit()
{
   g_store.Load();

   g_panel.Init(TDP_PREFIX, g_store.panelCorner, g_store.theme);
   g_panel.BuildChrome(TDP_VERSION);

   g_plannerDialog.Init(&g_panel, &g_store);

   g_planner.Init(&g_panel, &g_store, &g_plannerDialog);
   g_planner.Build();

   g_manager.Init(&g_panel, &g_store);
   g_manager.Build();

   g_settings.Init(&g_panel, &g_store);
   g_settings.Build();

   g_panel.RegisterHandler(GetPointer(g_planner));
   g_panel.RegisterHandler(GetPointer(g_plannerDialog));
   g_panel.RegisterHandler(GetPointer(g_manager));
   g_panel.RegisterHandler(GetPointer(g_settings));

   g_panel.ShowTab(TDP_TAB_PLAN);

   EventSetTimer(1);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   g_plannerDialog.Destroy();
   g_panel.DestroyAll();
}

//+------------------------------------------------------------------+
void OnTick()
{
   Heartbeat();
}

//+------------------------------------------------------------------+
void OnTimer()
{
   Heartbeat();
}

//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   g_panel.RouteEvent(id, lparam, dparam, sparam);
}

//+------------------------------------------------------------------+
// Shared per-tick / per-second refresh — keeps the panel, the profit
// watcher and the trailing-arm logic alive even on quiet symbols where
// OnTick() fires rarely.
//+------------------------------------------------------------------+
void Heartbeat()
{
   g_panel.TickHandlers();
}
