//+------------------------------------------------------------------+
//|                                                TDP_Manager.mqh    |
//|                                            Trade Desk Pro v1.0.0  |
//|  [MANAGE] tab — scope-aware trade list, modify SL/TP, breakeven,  |
//|  trailing arm, close operations and the profit watcher.           |
//+------------------------------------------------------------------+
#property copyright "Trade Desk Pro"
#property strict

#ifndef TDP_MANAGER_MQH
#define TDP_MANAGER_MQH

#include "TDP_Panel.mqh"
#include "TDP_Settings.mqh"
#include <Trade\Trade.mqh>

struct TDP_TrailEntry
{
   ulong  ticket;
   double distPts;
};

class CTDPManager : public ITDPEventHandler
{
private:
   CTDPPanel         *m_panel;
   CTDPSettingsStore *m_store;
   CTrade             m_trade;
   CTDPAtrCache       m_atr;

   ENUM_TDP_SCOPE     m_scope;
   ulong              m_checked[];       // tickets checked in Selected scope
   ulong              m_watch[];         // tickets armed by Close-in-Profit
   TDP_TrailEntry     m_trail[];         // tickets with an armed native-style trail

   int                m_sortField;       // 0=time,1=symbol,2=pnl
   bool               m_sortAsc;
   int                m_page;

   ENUM_TDP_UNIT      m_modUnit;
   ENUM_TDP_APPLY_MODE m_applyMode;

   int                m_closeAllStage;   // 0 idle,1 armed
   int                m_closeLossStage;  // 0 idle,1 first confirm,2 second confirm

   enum { ROWS_PER_PAGE = 5, ROW_H = 32 };

   string N(const string s) { return m_panel.Name("MANAGE_" + s); }
   string R(int i, const string s) { return m_panel.Name("MANAGE_R" + IntegerToString(i) + "_" + s); }

public:
   CTDPManager()
   {
      m_scope = TDP_SCOPE_GLOBAL;
      m_sortField = 0;
      m_sortAsc = false; // open time descending by default
      m_page = 0;
      m_modUnit = TDP_UNIT_POINTS;
      m_applyMode = TDP_APPLY_ABSOLUTE;
      m_closeAllStage = 0;
      m_closeLossStage = 0;
   }

   void Init(CTDPPanel *panel, CTDPSettingsStore *store)
   {
      m_panel = panel;
      m_store = store;
      m_trade.SetExpertMagicNumber(TDP_MAGIC);
      RestoreWatchersFromGlobals();
      RestoreTrailFromGlobals();
   }

   //----------------------------------------------------------------
   void Build()
   {
      int x = m_panel.PanelX();
      int w = m_panel.PanelWidth();
      int y = m_panel.ContentY();

      // --- Scope toggle --------------------------------------------------
      m_panel.CreateLabel(N("SCOPE_LBL"), x + 8, y + 4, "Scope", m_panel.clrTextDim, 7);
      m_panel.CreateButton(N("SCOPE_G"), x + w - 168, y, 56, 20, "Global",   m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("SCOPE_C"), x + w - 112, y, 56, 20, "Chart",    m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("SCOPE_S"), x + w - 56,  y, 56, 20, "Selected", m_panel.clrButtonBg, m_panel.clrText, 7);
      y += 24;

      // --- Sort header ---------------------------------------------------
      m_panel.CreateButton(N("SORT_TIME"), x + 8,        y, 80, 16, "Time v",   m_panel.clrButtonBg, m_panel.clrTextDim, 7);
      m_panel.CreateButton(N("SORT_SYM"),  x + 90,       y, 80, 16, "Symbol",   m_panel.clrButtonBg, m_panel.clrTextDim, 7);
      m_panel.CreateButton(N("SORT_PNL"),  x + w - 90,   y, 82, 16, "P&L",      m_panel.clrButtonBg, m_panel.clrTextDim, 7);
      y += 18;

      int listTop = y;
      for(int i = 0; i < ROWS_PER_PAGE; i++)
         BuildRow(i, x, w, listTop + i * ROW_H);

      m_panel.CreateLabel(N("EMPTY"), x + 8, listTop + 8, "No active trades detected", m_panel.clrTextDim, 8);

      y = listTop + ROWS_PER_PAGE * ROW_H + 2;
      m_panel.CreateButton(N("PAGE_PREV"), x + 8, y, 50, 18, "< Prev", m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateLabel(N("PAGE_LBL"), x + w / 2 - 24, y + 2, "Page 1/1", m_panel.clrTextDim, 7);
      m_panel.CreateButton(N("PAGE_NEXT"), x + w - 58, y, 50, 18, "Next >", m_panel.clrButtonBg, m_panel.clrText, 7);
      y += 24;

      // --- Modify SL/TP ----------------------------------------------------
      m_panel.CreateLabel(N("MOD_TITLE"), x + 8, y, "Modify SL / TP", m_panel.clrText, 8, "Calibri Bold");
      y += 16;
      int bw = 41;
      m_panel.CreateButton(N("MU_PTS"),  x + 8,           y, bw, 18, "Pts",  m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("MU_PIPS"), x + 8 + bw,       y, bw, 18, "Pips", m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("MU_PCT"),  x + 8 + bw * 2,   y, bw, 18, "%Px",  m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("MU_DOL"),  x + 8 + bw * 3,   y, bw, 18, "$",    m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("MA_ABS"),  x + w - 168,      y, 78, 18, "Absolute", m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("MA_REL"),  x + w - 86,       y, 78, 18, "Relative", m_panel.clrButtonBg, m_panel.clrText, 7);
      y += 22;
      m_panel.CreateLabel(N("MOD_SL_LBL"), x + 8, y + 3, "New SL:", m_panel.clrTextDim, 7);
      m_panel.CreateEdit(N("MOD_SL_EDIT"), x + 56, y, 70, 18, "", m_panel.clrInputBg, m_panel.clrText, false);
      m_panel.CreateLabel(N("MOD_TP_LBL"), x + 134, y + 3, "New TP:", m_panel.clrTextDim, 7);
      m_panel.CreateEdit(N("MOD_TP_EDIT"), x + 182, y, 70, 18, "", m_panel.clrInputBg, m_panel.clrText, false);
      m_panel.CreateButton(N("MOD_APPLY"), x + w - 70, y - 1, 62, 20, "Apply", m_panel.clrAccent, m_panel.clrButtonText, 7);
      y += 24;

      // --- Breakeven / Trail -----------------------------------------------
      m_panel.CreateButton(N("BREAKEVEN"), x + 8, y, 110, 22, "Breakeven", m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateButton(N("TRAIL_ARM"), x + 124, y, 90, 22, "Trail Arm", m_panel.clrButtonBg, m_panel.clrText, 7);
      m_panel.CreateEdit(N("TRAIL_DIST"), x + 220, y, 60, 22, "150", m_panel.clrInputBg, m_panel.clrText, false);
      m_panel.CreateLabel(N("TRAIL_UNIT"), x + 284, y + 5, "pts", m_panel.clrTextDim, 7);
      y += 28;

      // --- Close operations --------------------------------------------------
      m_panel.CreateButton(N("CLOSE_ALL"),    x + 8, y, w - 16, 22, "Close All", m_panel.clrDown, C'255,255,255', 8);
      y += 26;
      m_panel.CreateButton(N("CLOSE_PROFIT"), x + 8, y, w - 16, 22, "Close in Profit", m_panel.clrUp, C'255,255,255', 8);
      y += 26;
      m_panel.CreateButton(N("CLOSE_LOSS"),   x + 8, y, w - 16, 22, "Close All in Loss", m_panel.clrDown, C'255,255,255', 8);
      y += 26;
      m_panel.CreateEdit(N("OLDEST_N"), x + 8, y, 40, 22, "1", m_panel.clrInputBg, m_panel.clrText, false);
      m_panel.CreateButton(N("CLOSE_OLDEST"), x + 52, y, w - 60, 22, "Close Oldest N", m_panel.clrButtonBg, m_panel.clrText, 8);
      y += 26;
      m_panel.CreateButton(N("CLOSE_LARGEST"), x + 8, y, w - 16, 22, "Close Largest Loss", m_panel.clrButtonBg, m_panel.clrText, 8);

      Refresh();
   }

   void BuildRow(int i, int x, int w, int y)
   {
      m_panel.CreateRect(R(i, "BG"), x, y, w, ROW_H - 2, m_panel.clrCardBg, m_panel.clrBorder);
      m_panel.CreateCheckbox(R(i, "CHK"), x + 4, y + 2, 14, false);
      m_panel.CreateLabel(R(i, "L1"), x + 22, y + 2, "", m_panel.clrText, 7, "Calibri Bold");
      m_panel.CreateLabel(R(i, "TAG"), x + w - 36, y + 2, "", m_panel.clrTextDim, 7, "Calibri Bold");
      m_panel.CreateLabel(R(i, "L2"), x + 22, y + 15, "", m_panel.clrTextDim, 7);
      m_panel.CreateLabel(R(i, "PNL"), x + w - 96, y + 15, "", m_panel.clrText, 7, "Calibri Bold");
   }

   //----------------------------------------------------------------
   virtual void OnTDPEvent(const int id, const long &lparam, const double &dparam, const string &sparam) override
   {
      bool resetConfirms = true;

      if(id == CHARTEVENT_OBJECT_CLICK)
      {
         if(sparam == N("SCOPE_G")) { m_scope = TDP_SCOPE_GLOBAL; m_page = 0; }
         else if(sparam == N("SCOPE_C")) { m_scope = TDP_SCOPE_CHART; m_page = 0; }
         else if(sparam == N("SCOPE_S")) { m_scope = TDP_SCOPE_SELECTED; m_page = 0; }
         else if(sparam == N("SORT_TIME")) { ToggleSort(0); }
         else if(sparam == N("SORT_SYM"))  { ToggleSort(1); }
         else if(sparam == N("SORT_PNL"))  { ToggleSort(2); }
         else if(sparam == N("PAGE_PREV")) { m_page = MathMax(0, m_page - 1); }
         else if(sparam == N("PAGE_NEXT")) { m_page++; }
         else if(sparam == N("MU_PTS"))  { m_modUnit = TDP_UNIT_POINTS; }
         else if(sparam == N("MU_PIPS")) { m_modUnit = TDP_UNIT_PIPS; }
         else if(sparam == N("MU_PCT"))  { m_modUnit = TDP_UNIT_PCT_PRICE; }
         else if(sparam == N("MU_DOL"))  { m_modUnit = TDP_UNIT_DOLLAR; }
         else if(sparam == N("MA_ABS"))  { m_applyMode = TDP_APPLY_ABSOLUTE; }
         else if(sparam == N("MA_REL"))  { m_applyMode = TDP_APPLY_RELATIVE; }
         else if(sparam == N("MOD_APPLY"))    { DoModifySLTP(); }
         else if(sparam == N("BREAKEVEN"))    { DoBreakeven(); }
         else if(sparam == N("TRAIL_ARM"))    { DoTrailArm(); }
         else if(sparam == N("CLOSE_ALL"))    { DoCloseAllStaged(); resetConfirms = false; }
         else if(sparam == N("CLOSE_PROFIT")) { DoArmCloseInProfit(); }
         else if(sparam == N("CLOSE_LOSS"))   { DoCloseLossStaged(); resetConfirms = false; }
         else if(sparam == N("CLOSE_OLDEST"))  { DoCloseOldestN(); }
         else if(sparam == N("CLOSE_LARGEST")) { DoCloseLargestLoss(); }
         else
         {
            bool rowHandled = false;
            for(int i = 0; i < ROWS_PER_PAGE; i++)
               if(sparam == R(i, "CHK")) { ToggleRowChecked(i); rowHandled = true; }
            if(!rowHandled) resetConfirms = false; // unknown object — leave staged state alone
         }

         if(resetConfirms) { m_closeAllStage = 0; m_closeLossStage = 0; }

         if(ObjectFind(0, sparam) >= 0 && ObjectGetInteger(0, sparam, OBJPROP_TYPE) == OBJ_BUTTON)
            ObjectSetInteger(0, sparam, OBJPROP_STATE, false);

         Refresh();
      }

      if(id == CHARTEVENT_OBJECT_ENDEDIT)
         Refresh();
   }

   virtual void OnTDPTick() override
   {
      RunProfitWatcher();
      RunTrailing();
      UpdateHeader();
      Refresh();
   }

   //----------------------------------------------------------------
   void Refresh()
   {
      bool active = (m_panel.ActiveTab() == TDP_TAB_MANAGE) && !m_panel.IsSettingsOpen() && !m_panel.IsCollapsed();

      m_panel.SetVisible(N("SCOPE_LBL"), active);
      m_panel.SetVisible(N("SCOPE_G"), active);
      m_panel.SetVisible(N("SCOPE_C"), active);
      m_panel.SetVisible(N("SCOPE_S"), active);
      m_panel.SetBg(N("SCOPE_G"), m_scope == TDP_SCOPE_GLOBAL   ? m_panel.clrAccent : m_panel.clrButtonBg);
      m_panel.SetBg(N("SCOPE_C"), m_scope == TDP_SCOPE_CHART    ? m_panel.clrAccent : m_panel.clrButtonBg);
      m_panel.SetBg(N("SCOPE_S"), m_scope == TDP_SCOPE_SELECTED ? m_panel.clrAccent : m_panel.clrButtonBg);

      m_panel.SetVisible(N("SORT_TIME"), active);
      m_panel.SetVisible(N("SORT_SYM"), active);
      m_panel.SetVisible(N("SORT_PNL"), active);

      ulong tickets[];
      CollectDisplayList(tickets);
      SortTickets(tickets);

      int total = ArraySize(tickets);
      bool empty = (total == 0);
      m_panel.SetVisible(N("EMPTY"), active && empty);

      int maxPage = MathMax(0, (total - 1) / ROWS_PER_PAGE);
      if(m_page > maxPage) m_page = maxPage;
      int pageStart = m_page * ROWS_PER_PAGE;

      for(int i = 0; i < ROWS_PER_PAGE; i++)
      {
         int idx = pageStart + i;
         bool show = active && idx < total;
         SetRowVisible(i, show);
         if(show) RenderRow(i, tickets[idx]);
      }

      bool showPager = active && total > ROWS_PER_PAGE;
      m_panel.SetVisible(N("PAGE_PREV"), showPager);
      m_panel.SetVisible(N("PAGE_NEXT"), showPager);
      m_panel.SetVisible(N("PAGE_LBL"), showPager);
      m_panel.SetText(N("PAGE_LBL"), "Page " + IntegerToString(m_page + 1) + "/" + IntegerToString(maxPage + 1));

      m_panel.SetVisible(N("MOD_TITLE"), active);
      m_panel.SetVisible(N("MU_PTS"), active);
      m_panel.SetVisible(N("MU_PIPS"), active);
      m_panel.SetVisible(N("MU_PCT"), active);
      m_panel.SetVisible(N("MU_DOL"), active);
      m_panel.SetVisible(N("MA_ABS"), active);
      m_panel.SetVisible(N("MA_REL"), active);
      m_panel.SetVisible(N("MOD_SL_LBL"), active);
      m_panel.SetVisible(N("MOD_SL_EDIT"), active);
      m_panel.SetVisible(N("MOD_TP_LBL"), active);
      m_panel.SetVisible(N("MOD_TP_EDIT"), active);
      m_panel.SetVisible(N("MOD_APPLY"), active);
      m_panel.SetBg(N("MU_PTS"),  m_modUnit == TDP_UNIT_POINTS    ? m_panel.clrAccent : m_panel.clrButtonBg);
      m_panel.SetBg(N("MU_PIPS"), m_modUnit == TDP_UNIT_PIPS      ? m_panel.clrAccent : m_panel.clrButtonBg);
      m_panel.SetBg(N("MU_PCT"),  m_modUnit == TDP_UNIT_PCT_PRICE ? m_panel.clrAccent : m_panel.clrButtonBg);
      m_panel.SetBg(N("MU_DOL"),  m_modUnit == TDP_UNIT_DOLLAR    ? m_panel.clrAccent : m_panel.clrButtonBg);
      m_panel.SetBg(N("MA_ABS"), m_applyMode == TDP_APPLY_ABSOLUTE ? m_panel.clrAccent : m_panel.clrButtonBg);
      m_panel.SetBg(N("MA_REL"), m_applyMode == TDP_APPLY_RELATIVE ? m_panel.clrAccent : m_panel.clrButtonBg);

      m_panel.SetVisible(N("BREAKEVEN"), active);
      m_panel.SetVisible(N("TRAIL_ARM"), active);
      m_panel.SetVisible(N("TRAIL_DIST"), active);
      m_panel.SetVisible(N("TRAIL_UNIT"), active);

      m_panel.SetVisible(N("CLOSE_ALL"), active);
      m_panel.SetText(N("CLOSE_ALL"), m_closeAllStage == 0 ? "Close All" : "Confirm — close all in scope?");

      m_panel.SetVisible(N("CLOSE_PROFIT"), active);
      m_panel.SetText(N("CLOSE_PROFIT"), "Close in Profit (" + IntegerToString(ArraySize(m_watch)) + " watching)");

      m_panel.SetVisible(N("CLOSE_LOSS"), active);
      string lossTxt = "Close All in Loss";
      if(m_closeLossStage == 1) lossTxt = "Sure? This closes all losing trades";
      if(m_closeLossStage == 2) lossTxt = "Confirm — cannot be undone";
      m_panel.SetText(N("CLOSE_LOSS"), lossTxt);

      m_panel.SetVisible(N("OLDEST_N"), active);
      m_panel.SetVisible(N("CLOSE_OLDEST"), active);
      m_panel.SetVisible(N("CLOSE_LARGEST"), active);
   }

   void UpdateHeader()
   {
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double marginLevel = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
      int openCount = PositionsTotal();
      double floatPL = 0;
      for(int i = 0; i < openCount; i++)
      {
         ulong t = PositionGetTicket(i);
         if(t == 0) continue;
         floatPL += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      }

      ulong scopedForHeader[];
      CollectScoped(m_scope, scopedForHeader);
      double worst = 0;
      for(int i = 0; i < ArraySize(scopedForHeader); i++)
      {
         if(!PositionSelectByTicket(scopedForHeader[i])) continue;
         double p = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         if(p < worst) worst = p;
      }

      string line1 = StringFormat("Equity: %s   Margin Level: %s%%   Open: %d trades   Float P&L: %s",
                                   TDP_FormatMoney(equity),
                                   (marginLevel > 0 ? DoubleToString(marginLevel, 0) : "—"),
                                   openCount, TDP_FormatSignedMoney(floatPL));
      string line2 = StringFormat("Largest drawdown (scope): %s", TDP_FormatMoney(worst));
      m_panel.SetHeaderStats(line1, line2);
   }

private:
   void ToggleSort(int field)
   {
      if(m_sortField == field) m_sortAsc = !m_sortAsc;
      else { m_sortField = field; m_sortAsc = (field == 1); }
   }

   void ToggleRowChecked(int rowIdx)
   {
      ulong tickets[];
      CollectDisplayList(tickets);
      SortTickets(tickets);
      int idx = m_page * ROWS_PER_PAGE + rowIdx;
      if(idx < 0 || idx >= ArraySize(tickets)) return;
      ulong ticket = tickets[idx];

      int pos = CheckedIndex(ticket);
      if(pos >= 0) ArrayRemoveTicket(m_checked, pos);
      else
      {
         int n = ArraySize(m_checked);
         ArrayResize(m_checked, n + 1);
         m_checked[n] = ticket;
      }
   }

   int CheckedIndex(ulong ticket)
   {
      for(int i = 0; i < ArraySize(m_checked); i++)
         if(m_checked[i] == ticket) return i;
      return -1;
   }

   void ArrayRemoveTicket(ulong &arr[], int idx)
   {
      int n = ArraySize(arr);
      for(int i = idx; i < n - 1; i++) arr[i] = arr[i + 1];
      ArrayResize(arr, n - 1);
   }

   //----------------------------------------------------------------
   // Scope / list collection
   //----------------------------------------------------------------
   void CollectScoped(ENUM_TDP_SCOPE scope, ulong &out[])
   {
      ArrayResize(out, 0);
      int total = PositionsTotal();
      for(int i = 0; i < total; i++)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0) continue;
         if(!PositionSelectByTicket(ticket)) continue;

         bool include = false;
         if(scope == TDP_SCOPE_GLOBAL) include = true;
         else if(scope == TDP_SCOPE_CHART) include = (PositionGetString(POSITION_SYMBOL) == _Symbol);
         else include = (CheckedIndex(ticket) >= 0);

         if(include)
         {
            int n = ArraySize(out);
            ArrayResize(out, n + 1);
            out[n] = ticket;
         }
      }
   }

   // The list shown in the table: Global/Chart scope shows that filtered
   // set; Selected scope shows the full Global list so the user has
   // something to check boxes against.
   void CollectDisplayList(ulong &out[])
   {
      if(m_scope == TDP_SCOPE_CHART)
         CollectScoped(TDP_SCOPE_CHART, out);
      else
         CollectScoped(TDP_SCOPE_GLOBAL, out);
   }

   void SortTickets(ulong &tickets[])
   {
      int n = ArraySize(tickets);
      for(int i = 0; i < n - 1; i++)
      {
         for(int j = 0; j < n - 1 - i; j++)
         {
            if(CompareTickets(tickets[j], tickets[j + 1]) > 0)
            {
               ulong tmp = tickets[j];
               tickets[j] = tickets[j + 1];
               tickets[j + 1] = tmp;
            }
         }
      }
   }

   int CompareTickets(ulong a, ulong b)
   {
      if(!PositionSelectByTicket(a)) return 0;
      double va = SortKey(a);
      if(!PositionSelectByTicket(b)) return 0;
      double vb = SortKey(b);
      int cmp = (va < vb) ? -1 : (va > vb ? 1 : 0);
      return m_sortAsc ? cmp : -cmp;
   }

   double SortKey(ulong ticket)
   {
      if(!PositionSelectByTicket(ticket)) return 0;
      if(m_sortField == 0) return (double)PositionGetInteger(POSITION_TIME);
      if(m_sortField == 1)
      {
         string s = PositionGetString(POSITION_SYMBOL);
         double h = 0;
         for(int i = 0; i < StringLen(s); i++) h = h * 31 + StringGetCharacter(s, i);
         return h;
      }
      return PositionGetDouble(POSITION_PROFIT);
   }

   //----------------------------------------------------------------
   void SetRowVisible(int i, bool show)
   {
      string parts[] = {"BG","CHK","L1","TAG","L2","PNL"};
      for(int k = 0; k < ArraySize(parts); k++)
         m_panel.SetVisible(R(i, parts[k]), show);
   }

   void RenderRow(int i, ulong ticket)
   {
      if(!PositionSelectByTicket(ticket)) return;

      string sym   = PositionGetString(POSITION_SYMBOL);
      long   type  = PositionGetInteger(POSITION_TYPE);
      double lots  = PositionGetDouble(POSITION_VOLUME);
      double openP = PositionGetDouble(POSITION_PRICE_OPEN);
      double nowP  = PositionGetDouble(POSITION_PRICE_CURRENT);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      double pnl   = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      long   magic = PositionGetInteger(POSITION_MAGIC);
      double bal   = AccountInfoDouble(ACCOUNT_BALANCE);
      double pnlPct = (bal != 0) ? (pnl / bal * 100.0) : 0.0;

      string dir = (type == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      string origin = (magic == TDP_MAGIC) ? "TDP" : "EXT";

      m_panel.SetChecked(R(i, "CHK"), CheckedIndex(ticket) >= 0);
      m_panel.SetVisible(R(i, "CHK"), m_scope == TDP_SCOPE_SELECTED);

      m_panel.SetText(R(i, "L1"), StringFormat("#%I64u  %s  %s  %.2f", ticket, sym, dir, lots));
      m_panel.SetText(R(i, "TAG"), origin);
      m_panel.SetText(R(i, "L2"), StringFormat("E:%s Now:%s SL:%s TP:%s",
                                   TDP_FormatPrice(sym, openP), TDP_FormatPrice(sym, nowP),
                                   sl > 0 ? TDP_FormatPrice(sym, sl) : "—",
                                   tp > 0 ? TDP_FormatPrice(sym, tp) : "—"));
      m_panel.SetText(R(i, "PNL"), TDP_FormatSignedMoney(pnl) + " (" + TDP_FormatPct(pnlPct) + ")");
      m_panel.SetTextColor(R(i, "PNL"), pnl >= 0 ? m_panel.clrUp : m_panel.clrDown);
   }

   //----------------------------------------------------------------
   // Modify SL / TP
   //----------------------------------------------------------------
   void DoModifySLTP()
   {
      ulong scoped[];
      CollectScoped(m_scope, scoped);
      string slText = m_panel.GetText(N("MOD_SL_EDIT"));
      string tpText = m_panel.GetText(N("MOD_TP_EDIT"));
      bool haveSL = StringLen(slText) > 0;
      bool haveTP = StringLen(tpText) > 0;
      if(!haveSL && !haveTP) return;
      double slVal = StringToDouble(slText);
      double tpVal = StringToDouble(tpText);

      for(int i = 0; i < ArraySize(scoped); i++)
      {
         if(!PositionSelectByTicket(scoped[i])) continue;
         string sym = PositionGetString(POSITION_SYMBOL);
         double point = TDP_Point(sym);
         double curSL = PositionGetDouble(POSITION_SL);
         double curTP = PositionGetDouble(POSITION_TP);
         double openP = PositionGetDouble(POSITION_PRICE_OPEN);

         double newSL = curSL, newTP = curTP;

         if(m_applyMode == TDP_APPLY_ABSOLUTE)
         {
            if(haveSL) newSL = slVal;
            if(haveTP) newTP = tpVal;
         }
         else
         {
            double refPrice = (curSL > 0) ? curSL : openP;
            double refTpPrice = (curTP > 0) ? curTP : openP;
            if(haveSL)
            {
               double pts = TDP_UnitToPoints(sym, MathAbs(slVal), m_modUnit, openP);
               newSL = refPrice + (slVal >= 0 ? pts : -pts) * point;
            }
            if(haveTP)
            {
               double pts = TDP_UnitToPoints(sym, MathAbs(tpVal), m_modUnit, openP);
               newTP = refTpPrice + (tpVal >= 0 ? pts : -pts) * point;
            }
         }

         m_trade.PositionModify(scoped[i], newSL, newTP);
      }
   }

   void DoBreakeven()
   {
      ulong scoped[];
      CollectScoped(m_scope, scoped);
      for(int i = 0; i < ArraySize(scoped); i++)
      {
         if(!PositionSelectByTicket(scoped[i])) continue;
         string sym = PositionGetString(POSITION_SYMBOL);
         bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         double openP = PositionGetDouble(POSITION_PRICE_OPEN);
         double spread = TDP_SpreadPrice(sym);
         double newSL = isBuy ? openP + spread : openP - spread;
         m_trade.PositionModify(scoped[i], newSL, PositionGetDouble(POSITION_TP));
      }
   }

   // Arms a simple fixed-distance trail (the "MT5 native" style trailing
   // stop) for every ticket currently in scope. Once armed, the trail is
   // re-applied on every tick by RunTrailing() until the position closes,
   // independent of which scope is active later.
   void DoTrailArm()
   {
      ulong scoped[];
      CollectScoped(m_scope, scoped);
      double distPts = StringToDouble(m_panel.GetText(N("TRAIL_DIST")));
      if(distPts <= 0) return;
      for(int i = 0; i < ArraySize(scoped); i++)
         ArmTrail(scoped[i], distPts);
   }

   void RunTrailing()
   {
      for(int i = ArraySize(m_trail) - 1; i >= 0; i--)
      {
         ulong ticket = m_trail[i].ticket;
         double distPts = m_trail[i].distPts;
         if(!PositionSelectByTicket(ticket)) { UnarmTrail(ticket); continue; }

         string sym = PositionGetString(POSITION_SYMBOL);
         double point = TDP_Point(sym);
         bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
         double price = isBuy ? TDP_Bid(sym) : TDP_Ask(sym);
         double newSL = isBuy ? price - distPts * point : price + distPts * point;
         double curSL = PositionGetDouble(POSITION_SL);
         bool improves = (curSL <= 0) || (isBuy && newSL > curSL) || (!isBuy && newSL < curSL);
         if(improves)
            m_trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP));
      }
   }

   int TrailIndex(ulong ticket)
   {
      for(int i = 0; i < ArraySize(m_trail); i++)
         if(m_trail[i].ticket == ticket) return i;
      return -1;
   }

   void ArmTrail(ulong ticket, double distPts)
   {
      int idx = TrailIndex(ticket);
      if(idx >= 0) m_trail[idx].distPts = distPts;
      else
      {
         int n = ArraySize(m_trail);
         ArrayResize(m_trail, n + 1);
         m_trail[n].ticket = ticket;
         m_trail[n].distPts = distPts;
      }
      GlobalVariableSet("TDP_TRAIL_" + IntegerToString(ticket), distPts);
   }

   void UnarmTrail(ulong ticket)
   {
      int idx = TrailIndex(ticket);
      if(idx >= 0)
      {
         int n = ArraySize(m_trail);
         for(int i = idx; i < n - 1; i++) m_trail[i] = m_trail[i + 1];
         ArrayResize(m_trail, n - 1);
      }
      string key = "TDP_TRAIL_" + IntegerToString(ticket);
      if(GlobalVariableCheck(key)) GlobalVariableDel(key);
   }

   void RestoreTrailFromGlobals()
   {
      int total = GlobalVariablesTotal();
      for(int i = total - 1; i >= 0; i--)
      {
         string name = GlobalVariableName(i);
         if(StringFind(name, "TDP_TRAIL_") != 0) continue;
         ulong ticket = StringToInteger(StringSubstr(name, 10));
         if(PositionSelectByTicket(ticket))
         {
            int n = ArraySize(m_trail);
            ArrayResize(m_trail, n + 1);
            m_trail[n].ticket = ticket;
            m_trail[n].distPts = GlobalVariableGet(name);
         }
         else
            GlobalVariableDel(name);
      }
   }

   //----------------------------------------------------------------
   // Close operations
   //----------------------------------------------------------------
   void DoCloseAllStaged()
   {
      if(m_closeAllStage == 0) { m_closeAllStage = 1; return; }
      ulong scoped[];
      CollectScoped(m_scope, scoped);
      for(int i = 0; i < ArraySize(scoped); i++)
         m_trade.PositionClose(scoped[i]);
      m_closeAllStage = 0;
   }

   void DoCloseLossStaged()
   {
      if(m_closeLossStage == 0) { m_closeLossStage = 1; return; }
      if(m_closeLossStage == 1) { m_closeLossStage = 2; return; }
      ulong scoped[];
      CollectScoped(m_scope, scoped);
      for(int i = 0; i < ArraySize(scoped); i++)
      {
         if(!PositionSelectByTicket(scoped[i])) continue;
         double pnl = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         if(pnl < 0) m_trade.PositionClose(scoped[i]);
      }
      m_closeLossStage = 0;
   }

   void DoCloseOldestN()
   {
      int n = (int)StringToInteger(m_panel.GetText(N("OLDEST_N")));
      if(n <= 0) return;
      ulong scoped[];
      CollectScoped(m_scope, scoped);

      // sort ascending by open time
      int cnt = ArraySize(scoped);
      for(int i = 0; i < cnt - 1; i++)
         for(int j = 0; j < cnt - 1 - i; j++)
         {
            if(!PositionSelectByTicket(scoped[j])) continue;
            datetime tj = (datetime)PositionGetInteger(POSITION_TIME);
            if(!PositionSelectByTicket(scoped[j + 1])) continue;
            datetime tj1 = (datetime)PositionGetInteger(POSITION_TIME);
            if(tj > tj1) { ulong tmp = scoped[j]; scoped[j] = scoped[j + 1]; scoped[j + 1] = tmp; }
         }

      int toClose = MathMin(n, cnt);
      for(int i = 0; i < toClose; i++)
         m_trade.PositionClose(scoped[i]);
   }

   void DoCloseLargestLoss()
   {
      ulong scoped[];
      CollectScoped(m_scope, scoped);
      ulong worstTicket = 0;
      double worst = 0;
      for(int i = 0; i < ArraySize(scoped); i++)
      {
         if(!PositionSelectByTicket(scoped[i])) continue;
         double pnl = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         if(pnl < worst) { worst = pnl; worstTicket = scoped[i]; }
      }
      if(worstTicket != 0)
         m_trade.PositionClose(worstTicket);
   }

   //----------------------------------------------------------------
   // Close-in-profit watcher
   //----------------------------------------------------------------
   void DoArmCloseInProfit()
   {
      ulong scoped[];
      CollectScoped(m_scope, scoped);
      for(int i = 0; i < ArraySize(scoped); i++)
         EvaluateWatchCandidate(scoped[i], true);
   }

   void RunProfitWatcher()
   {
      for(int i = ArraySize(m_watch) - 1; i >= 0; i--)
         EvaluateWatchCandidate(m_watch[i], false);
   }

   // seedIfEligible=true is used when the user presses the button (adds
   // new candidates); false is used on the per-tick pass over the
   // existing watch list only.
   void EvaluateWatchCandidate(ulong ticket, bool seedIfEligible)
   {
      if(!PositionSelectByTicket(ticket))
      {
         UnwatchTicket(ticket);
         return;
      }

      string sym = PositionGetString(POSITION_SYMBOL);
      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      double openP = PositionGetDouble(POSITION_PRICE_OPEN);
      double pnl = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      double pnlPct = (bal != 0) ? (pnl / bal * 100.0) : 0.0;

      bool alreadyWatched = (WatchIndex(ticket) >= 0);
      if(!seedIfEligible && !alreadyWatched) return;

      if(pnl <= 0)
      {
         UnwatchTicket(ticket);
         return;
      }

      double spread = TDP_SpreadPrice(sym);
      double atrBuf = m_atr.GetBuffer(sym, m_store.atrMultiplier) * TDP_Point(sym);
      double breakevenPrice = isBuy ? openP + spread + atrBuf : openP - spread - atrBuf;
      double curPrice = isBuy ? TDP_Bid(sym) : TDP_Ask(sym);
      bool eligible = isBuy ? (curPrice >= breakevenPrice) : (curPrice <= breakevenPrice);

      if(!eligible)
      {
         if(seedIfEligible) WatchTicket(ticket); // arm now, will close once it clears the cushion
         return;
      }

      if(pnlPct >= m_store.closeInProfitPct)
      {
         m_trade.PositionClose(ticket);
         UnwatchTicket(ticket);
      }
      else if(seedIfEligible || alreadyWatched)
      {
         WatchTicket(ticket);
      }
   }

   int WatchIndex(ulong ticket)
   {
      for(int i = 0; i < ArraySize(m_watch); i++)
         if(m_watch[i] == ticket) return i;
      return -1;
   }

   void WatchTicket(ulong ticket)
   {
      if(WatchIndex(ticket) >= 0) return;
      int n = ArraySize(m_watch);
      ArrayResize(m_watch, n + 1);
      m_watch[n] = ticket;
      GlobalVariableSet("TDP_WATCH_" + IntegerToString(ticket), 1.0);
   }

   void UnwatchTicket(ulong ticket)
   {
      int idx = WatchIndex(ticket);
      if(idx >= 0) ArrayRemoveTicket(m_watch, idx);
      string key = "TDP_WATCH_" + IntegerToString(ticket);
      if(GlobalVariableCheck(key)) GlobalVariableDel(key);
   }

   void RestoreWatchersFromGlobals()
   {
      int total = GlobalVariablesTotal();
      for(int i = total - 1; i >= 0; i--)
      {
         string name = GlobalVariableName(i);
         if(StringFind(name, "TDP_WATCH_") != 0) continue;
         ulong ticket = StringToInteger(StringSubstr(name, 10));
         if(PositionSelectByTicket(ticket))
         {
            int n = ArraySize(m_watch);
            ArrayResize(m_watch, n + 1);
            m_watch[n] = ticket;
         }
         else
            GlobalVariableDel(name); // stale — position no longer open
      }
   }
};

#endif // TDP_MANAGER_MQH
