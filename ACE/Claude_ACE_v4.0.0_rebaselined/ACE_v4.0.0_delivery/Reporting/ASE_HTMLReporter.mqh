#ifndef ASE_HTMLREPORTER_MQH
#define ASE_HTMLREPORTER_MQH
#include "../Core/ASE_Telemetry.mqh"
#include "../Core/ASE_WalkForwardEngine.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — HTML Report Exporter                                    |
//| Updated: accepts WalkForwardEngine for OOS section               |
//+------------------------------------------------------------------+
class CASE_HTMLReporter
{
public:
   void Export(string filename, CASE_Telemetry &tel, CASE_WalkForwardEngine &wf)
   {
      int h = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
      if(h == INVALID_HANDLE) { Print("[HTMLReporter] Cannot open: ", filename); return; }

      FileWrite(h, "<!DOCTYPE html><html><head><meta charset='utf-8'>");
      FileWrite(h, "<title>ASE v3 Report</title>");
      FileWrite(h, "<style>");
      FileWrite(h, "body{font-family:monospace;background:#0d0d0d;color:#c8c8c8;padding:20px;}");
      FileWrite(h, "h2{color:#7ec8e3;} h3{color:#a0c8a0;margin-top:24px;}");
      FileWrite(h, "table{border-collapse:collapse;width:100%;margin-bottom:20px;}");
      FileWrite(h, "td,th{border:1px solid #333;padding:6px 12px;}");
      FileWrite(h, "th{background:#1a1a1a;color:#7ec8e3;}");
      FileWrite(h, ".pos{color:#00c896;} .neg{color:#e05252;} .neu{color:#c8c8c8;}");
      FileWrite(h, "</style></head><body>");

      FileWrite(h, "<h2>ASE v3 — Performance Report</h2>");
      FileWrite(h, "<p>Generated: " + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + "</p>");

      // ── Core metrics ─────────────────────────────────────────────
      FileWrite(h, "<h3>Core Metrics</h3><table>");
      FileWrite(h, "<tr><th>Metric</th><th>Value</th><th>Spec</th></tr>");
      _row(h, "Total Trades",   IntegerToString(tel.GetTradeCount()),            "≥10/month", tel.GetTradeCount() >= 10);
      _row(h, "Win Rate",       DoubleToString(tel.GetWinRate(), 1) + "%",       "≥60%",      tel.GetWinRate() >= 60.0);
      _row(h, "Avg R:R",        DoubleToString(tel.GetAverageRR(), 2),           "≥2.0",      tel.GetAverageRR() >= 2.0);
      _row(h, "Profit Factor",  DoubleToString(tel.GetProfitFactor(), 2),        "≥1.4",      tel.GetProfitFactor() >= 1.4);
      _row(h, "Net Profit",     DoubleToString(tel.GetNetProfit(), 2),           ">0",        tel.GetNetProfit() > 0);
      _row(h, "Max Drawdown",   DoubleToString(tel.GetMaxDrawdownPct(), 2) + "%","≤25%",      tel.GetMaxDrawdownPct() <= 25.0);
      FileWrite(h, "</table>");

      // ── MAE/MFE ──────────────────────────────────────────────────
      FileWrite(h, "<h3>Excursion Analytics</h3><table>");
      FileWrite(h, "<tr><th>Metric</th><th>Value</th></tr>");
      FileWrite(h, "<tr><td>Avg MAE (% of SL)</td><td>" + DoubleToString(tel.GetAvgMAEPct(), 1) + "%</td></tr>");
      FileWrite(h, "<tr><td>Avg MFE (% of TP)</td><td>" + DoubleToString(tel.GetAvgMFEPct(), 1) + "%</td></tr>");
      FileWrite(h, "</table>");

      // ── Walk-forward ─────────────────────────────────────────────
      FileWrite(h, "<h3>Walk-Forward Validation</h3>");
      double oosRet = wf.GetOOSRetention();
      string oosStr = DoubleToString(oosRet * 100.0, 0) + "% of windows passing";
      FileWrite(h, "<p>OOS Retention: <span class='" +
                   (oosRet >= 0.85 ? "pos" : "neg") + "'>" + oosStr + "</span></p>");

      if(wf.GetWindowCount() > 0)
      {
         FileWrite(h, "<table><tr><th>Window</th><th>IS WR</th><th>OOS WR</th>"
                      "<th>WR Ret</th><th>IS PF</th><th>OOS PF</th><th>Status</th></tr>");
         for(int i = 0; i < wf.GetWindowCount(); i++)
         {
            WFWindow w = wf.GetWindow(i);
            string st = w.passes ? "<span class='pos'>PASS</span>" : "<span class='neg'>FAIL</span>";
            FileWrite(h, "<tr><td>W" + IntegerToString(i+1) + "</td>"
                        + "<td>" + DoubleToString(w.isWR, 0) + "%</td>"
                        + "<td>" + DoubleToString(w.oosWR, 0) + "%</td>"
                        + "<td>" + DoubleToString(w.wrRetention * 100, 0) + "%</td>"
                        + "<td>" + DoubleToString(w.isPF, 2) + "</td>"
                        + "<td>" + DoubleToString(w.oosPF, 2) + "</td>"
                        + "<td>" + st + "</td></tr>");
         }
         FileWrite(h, "</table>");
      }

      FileWrite(h, "</body></html>");
      FileClose(h);
      Print("[HTMLReporter] Saved: ", filename);
   }

private:
   void _row(int h, string label, string value, string spec, bool pass)
   {
      string cls = pass ? "pos" : "neg";
      FileWrite(h, "<tr><td>" + label + "</td><td class='" + cls + "'>" +
                value + "</td><td class='neu'>" + spec + "</td></tr>");
   }
};
#endif // ASE_HTMLREPORTER_MQH
