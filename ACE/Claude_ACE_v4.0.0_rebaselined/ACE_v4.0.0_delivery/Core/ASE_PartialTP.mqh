#ifndef ASE_PARTIALTP_MQH
#define ASE_PARTIALTP_MQH
#include <Trade/Trade.mqh>
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Partial TP Engine (scale out at TP1)                    |
//| FIX #17: Volume normalization now uses SYMBOL_VOLUME_STEP-derived |
//|           decimal places instead of SYMBOL_DIGITS (price digits). |
//|           For GOLDmicro: VOLUME_STEP=0.01 → 2 decimal places,    |
//|           whereas SYMBOL_DIGITS=5 was rounding to price precision.|
//+------------------------------------------------------------------+
class CASE_PartialTP
{
private:
   CTrade m_trade;
   ulong  m_tp1Done[];
   int    m_tp1Count;
   // Fix (2026-09-09) — separate from m_tp1Done. A ticket lands here the
   // first time price reaches TP1, whether the partial actually fires or
   // gets skipped (position too small to split — see Process() below).
   // Purpose is purely to stop Process() re-evaluating/re-logging the same
   // ticket on every subsequent tick once a decision has been made.
   // m_tp1Done must stay reserved for a REAL secured partial — HasAnyTP1Done()
   // gates the structural/ATR trail on it, and a skipped position has no
   // secured profit to justify trailing off its original stop.
   ulong  m_tp1Evaluated[];
   int    m_tp1EvalCount;
   // v3.14.6 Fix 9 — one-shot partial-fill accounting.
   // RecordClosedTrade() in ASE_StateMachine only fires when the position
   // is FULLY flat, so a TP1 partial close (which leaves the runner open)
   // was previously invisible to the StateLogger AND its profit was never
   // added into the trade's final logged total. Confirmed 2026-07-22/07-23
   // backtest: 117 of 454 closed trades (all TP1-partial winners, 100% WR,
   // $2,413 total) had no TRADE row at all, and every logged trade that HAD
   // a prior partial understated its true combined profit. This flag/value
   // pair is drained once per partial fire by StateMachine.
   bool   m_pendingPartialFlag;
   double m_pendingPartialProfit;
   ulong  m_pendingPartialTicket;

public:
   CASE_PartialTP() : m_tp1Count(0), m_tp1EvalCount(0), m_pendingPartialFlag(false),
                      m_pendingPartialProfit(0.0), m_pendingPartialTicket(0)
                      { ArrayResize(m_tp1Done, 0); ArrayResize(m_tp1Evaluated, 0); }

   bool Initialize()
   {
      m_trade.SetExpertMagicNumber(InpMagicNumber);
      return true;
   }

   void Process(double tp1Level)
   {
      if(!InpPartialTPEnabled) return;
      if(tp1Level <= 0)        return;

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(!PositionSelectByTicket(ticket))                               continue;
         if(PositionGetString(POSITION_SYMBOL)  != _Symbol)               continue;
         if(PositionGetInteger(POSITION_MAGIC)  != InpMagicNumber)        continue;
         if(IsTP1Evaluated(ticket))                                        continue;

         ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double price = (ptype == POSITION_TYPE_BUY)
                      ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                      : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

         bool atTP1 = (ptype == POSITION_TYPE_BUY  && price >= tp1Level) ||
                      (ptype == POSITION_TYPE_SELL && price <= tp1Level);

         if(atTP1)
         {
            double vol = PositionGetDouble(POSITION_VOLUME);

            // FIX #17 — normalize volume using VOLUME_STEP decimal precision,
            // not SYMBOL_DIGITS (which is for price, not lot size).
            double step      = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
            double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
            int    volDigits = (step > 0) ? (int)MathRound(-MathLog10(step)) : 2;

            double closeVol = NormalizeDouble(vol * InpPartialTPPercent / 100.0, volDigits);
            double remainder = NormalizeDouble(vol - closeVol, volDigits);

            // Fix (2026-09-09) — the old code force-floored closeVol up to
            // minLot with "if(closeVol < minLot) closeVol = minLot;", which
            // silently consumed the ENTIRE position whenever vol itself was
            // at or near minLot (e.g. 50% of a 0.01-lot position rounds to
            // 0.005, which the floor then bumped to the full 0.01) — leaving
            // no runner for TP2 at all. Confirmed live 2026-09-09: a 0.01-lot
            // trade logged "[PartialTP] Closed=0.01" (its entire size) and
            // closed the whole ticket at TP1 (Exit=EXIT_TP1), even though
            // price went on to reach TP2 with room to spare.
            // Now: only activate the partial if BOTH the partial leg AND the
            // leftover runner would independently clear minLot. Otherwise
            // skip the split and leave the full position on its original
            // SL/TP2 bracket, untouched, to run for TP2 whole.
            bool canSplit = (closeVol >= minLot) && (remainder >= minLot);

            // Full record, every time TP1 is reached, whichever way it goes —
            // this is the one line to grep in the Journal to confirm the
            // feature is (or isn't) firing on a given trade.
            Print(StringFormat(
               "[PartialTP] Eligibility | Ticket=%llu Vol=%.2f Pct=%.0f%% CloseVol=%.2f Remainder=%.2f MinLot=%.2f -> %s",
               ticket, vol, InpPartialTPPercent, closeVol, remainder, minLot,
               canSplit ? "ACTIVATE" : "SKIP (would leave <minLot runner)"));

            if(!canSplit)
            {
               // Fix (2026-09-09, v3.14.16) — backtest evidence (v14.14 vs
               // v14.15) showed the skip path left these positions with
               // ZERO protection between TP1 and the original SL: 33
               // matched trades where the OLD bug had force-closed the
               // whole position at TP1 (always a win by construction) were
               // re-run under v3.14.15's skip-instead-of-force-close fix.
               // 19 rode on to a legitimately bigger win (avg $19.66 ->
               // $37.33, +$335.72 total) — the fix working as intended.
               // But 14 reversed all the way back to the untouched
               // original SL and became full losses (~-$20 each), a
               // -$629 swing on that subgroup, netting the whole change to
               // -$293 — which accounted for essentially the ENTIRE
               // -$291.87 net-profit decline across the full 619-deal
               // backtest. Removing the old bug also removed its
               // accidental side effect of guaranteeing these trades could
               // only ever be a full win or a full loss, never "won then
               // gave it back." This restores a floor — breakeven only,
               // not a trail, since no partial was actually secured — so
               // a position that reaches TP1 level without being large
               // enough to split can't fully round-trip back to its
               // original risk.
               double entry = PositionGetDouble(POSITION_PRICE_OPEN);
               double tp    = PositionGetDouble(POSITION_TP);
               double beLevel = ComputeBreakevenLevel(ptype, entry);

               if(m_trade.PositionModify(ticket, beLevel, tp))
                  Print(StringFormat(
                     "[PartialTP] BE set (skip path, no partial) | Ticket=%llu Entry=%.5f BE=%.5f",
                     ticket, entry, beLevel));
               else
                  Print(StringFormat(
                     "[PartialTP] BE set FAILED (skip path) | Ticket=%llu Entry=%.5f TargetBE=%.5f",
                     ticket, entry, beLevel));

               MarkTP1Evaluated(ticket);
               continue;
            }

            if(m_trade.PositionClosePartial(ticket, closeVol))
            {
               MarkTP1Done(ticket);
               MarkTP1Evaluated(ticket);
               Print("[PartialTP] Ticket=", ticket, " Closed=", closeVol, " @ TP1=", tp1Level);

               double entry    = PositionGetDouble(POSITION_PRICE_OPEN);
               double tp       = PositionGetDouble(POSITION_TP);

               // v3.6.0 fix: BE level must account for spread so the remaining
               // runner is not stopped immediately when bid retraces to entry.
               // LONG: SL = entry + spread (ask-side break-even).
               // SHORT: SL = entry - spread (bid-side break-even).
               // Without this, a 30-pt GOLD spread stops the runner the instant
               // bid touches the open price on any trivial pullback.
               double beLevel = ComputeBreakevenLevel(ptype, entry);

               if(m_trade.PositionModify(ticket, beLevel, tp))
                  Print("[PartialTP] BE set | Ticket=", ticket,
                        " Entry=", entry,
                        " BE=", beLevel);

               // v3.14.6 Fix 9 — capture this partial deal's realized P&L
               // immediately (the deal that PositionClosePartial() just
               // created is the newest one in history) so the caller can
               // fold it into the eventual full-trade record.
               HistorySelect(TimeCurrent() - 86400, TimeCurrent());
               int htotal = HistoryDealsTotal();
               for(int h = htotal - 1; h >= 0; h--)
               {
                  ulong hTicket = HistoryDealGetTicket(h);
                  if(HistoryDealGetInteger(hTicket, DEAL_POSITION_ID) != (long)ticket) continue;
                  if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(hTicket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;
                  m_pendingPartialProfit += HistoryDealGetDouble(hTicket, DEAL_PROFIT)
                                          + HistoryDealGetDouble(hTicket, DEAL_SWAP)
                                          + HistoryDealGetDouble(hTicket, DEAL_COMMISSION);
                  m_pendingPartialTicket  = ticket;
                  m_pendingPartialFlag    = true;
                  Print(StringFormat("[PartialTP] Partial P&L captured | Ticket=%llu | Profit=%.2f | RunningAccum=%.2f",
                        ticket, HistoryDealGetDouble(hTicket, DEAL_PROFIT)
                              + HistoryDealGetDouble(hTicket, DEAL_SWAP)
                              + HistoryDealGetDouble(hTicket, DEAL_COMMISSION),
                        m_pendingPartialProfit));
                  break;
               }
            }
         }
      }
   }

   // v3.14.6 Fix 9 — one-shot drain. Returns true exactly once per partial
   // fire; profit is the partial leg's realized P&L (0 if none pending).
   // Accumulates across MULTIPLE partials on the same ticket if more than
   // one ever fires (future-proofing beyond the current single-TP1 design).
   bool ConsumePartialProfit(ulong &ticket, double &profit)
   {
      if(!m_pendingPartialFlag) { ticket = 0; profit = 0.0; return false; }
      ticket = m_pendingPartialTicket;
      profit = m_pendingPartialProfit;
      m_pendingPartialFlag    = false;
      m_pendingPartialProfit  = 0.0;
      m_pendingPartialTicket  = 0;
      return true;
   }

   void ClearClosed()
   {
      for(int i = m_tp1Count - 1; i >= 0; i--)
      {
         if(!PositionSelectByTicket(m_tp1Done[i]))
         {
            for(int j = i; j < m_tp1Count - 1; j++)
               m_tp1Done[j] = m_tp1Done[j+1];
            m_tp1Count--;
            ArrayResize(m_tp1Done, m_tp1Count);
         }
      }
      for(int i = m_tp1EvalCount - 1; i >= 0; i--)
      {
         if(!PositionSelectByTicket(m_tp1Evaluated[i]))
         {
            for(int j = i; j < m_tp1EvalCount - 1; j++)
               m_tp1Evaluated[j] = m_tp1Evaluated[j+1];
            m_tp1EvalCount--;
            ArrayResize(m_tp1Evaluated, m_tp1EvalCount);
         }
      }
   }

   // v3.6.0 — public so TradeManager can gate the ATR trail behind TP1.
   bool IsTP1Done(ulong ticket)
   {
      for(int i = 0; i < m_tp1Count; i++)
         if(m_tp1Done[i] == ticket) return true;
      return false;
   }

   // Returns true if ANY managed position has had TP1 hit.
   // Used by TradeManager to gate ATR trailing stop activation.
   bool HasAnyTP1Done() const { return (m_tp1Count > 0); }

   // Fix (2026-09-09) — true once a TP1 decision (activate or skip) has
   // been made for this ticket, regardless of outcome. Used only to stop
   // Process() re-evaluating the same ticket every tick; NOT used for
   // trail-gating (see HasAnyTP1Done() above, which stays keyed to a real
   // secured partial only).
   bool IsTP1Evaluated(ulong ticket)
   {
      for(int i = 0; i < m_tp1EvalCount; i++)
         if(m_tp1Evaluated[i] == ticket) return true;
      return false;
   }

private:
   // v3.6.0 fix, extracted as a shared helper in v3.14.16 — BE level must
   // account for spread so the position isn't stopped immediately when
   // price retraces to the exact open price on any trivial pullback.
   // LONG: SL = entry + spread (ask-side break-even).
   // SHORT: SL = entry - spread (bid-side break-even).
   double ComputeBreakevenLevel(ENUM_POSITION_TYPE ptype, double entry)
   {
      double spreadPts = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
      int    digits     = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      if(ptype == POSITION_TYPE_BUY)
         return NormalizeDouble(entry + spreadPts, digits);
      return NormalizeDouble(entry - spreadPts, digits);
   }

   void MarkTP1Done(ulong ticket)
   {
      m_tp1Count++;
      ArrayResize(m_tp1Done, m_tp1Count);
      m_tp1Done[m_tp1Count - 1] = ticket;
   }

   void MarkTP1Evaluated(ulong ticket)
   {
      m_tp1EvalCount++;
      ArrayResize(m_tp1Evaluated, m_tp1EvalCount);
      m_tp1Evaluated[m_tp1EvalCount - 1] = ticket;
   }
};
#endif // ASE_PARTIALTP_MQH
