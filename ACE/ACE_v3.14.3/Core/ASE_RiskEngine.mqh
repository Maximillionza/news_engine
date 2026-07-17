#ifndef ASE_RISKENGINE_MQH
#define ASE_RISKENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
#include "../Utilities/ASE_Math.mqh"
#include "../Utilities/ASE_Broker.mqh"
#include "ASE_RegimeProfile.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — Risk Engine                                             |
//| v3.14.0: BuildSetup() accepts const RegimeProfile &profile.      |
//|   SL multiplier and SL cap read from profile.slMultiplier /      |
//|   profile.slCap instead of InpATRMultiplierSL* globals.          |
//|   Legacy overload (no profile) retained for callers that haven't |
//|   been updated — passes a COMPRESSION default profile.           |
//|   CacheRegime() retained as a no-op stub for compatibility.      |
//+------------------------------------------------------------------+
//| Phase 1 additions:                                               |
//|   - DD-adaptive risk multiplier table (spec §8.1)               |
//|     DD < 5%   → 1.00× risk (full)                               |
//|     DD 5–10%  → 0.75× risk                                      |
//|     DD 10–15% → 0.50× risk                                      |
//|     DD > 15%  → trading halt (returns invalid setup)            |
//| v3.4.1 fix:                                                      |
//|   - ComputeTP() TP_ATR guard split into two explicit if blocks   |
//|     so TP_ATR mode can never fall through to structural path     |
//|     regardless of enum cast behaviour in MQL5 compiled binary.  |
//|   - Initialize() now prints resolved TP modes on startup.        |
//| v3.4.5 fix:
//| v3.4.6 additions:
//|   - CacheRegime() wired from StateMachine before BuildSetup()      |
//|   - SL multiplier selects InpATRMultiplierSL (COMPRESSION) or      |
//|     InpATRMultiplierSL_Wide (all other regimes) at build time.      |
//|   - InpATRSLCap applies a hard point ceiling after the multiplier   |
//|     so extreme ATR spikes cannot produce outsized position losses.  |                                                      |
//|   - RR denominator frozen to ATR x InpATRMultiplierSL (not live  |
//|     slDist). Decouples TP validation from SL placement so broker  |
//|     minimum distance SL adjustments cannot invalidate a valid TP. |
//|   - Epsilon guard (InpMinRR - 0.0001) absorbs float representation|
//|     of exact 2.0x multiples (7 blocks observed across 06-02/03). |
//+------------------------------------------------------------------+
class CASE_RiskEngine
{
private:
   int    m_atrHandle;
   double m_peakEquity;          // peak equity for DD calculation
   int    m_cachedRegime;
   double m_cachedScore;

   // v3.12.9 — DD Recovery Mode state (persists while EA runs; resets on reload)
   double m_sessionTarget;       // AccountBalance() at EA load — Phase 1 reference
   double m_secondaryBalance;    // AccountBalance() when halt first fired — Phase 2 reference
   bool   m_inRecoveryMode;      // true = Phase 2 active
   bool   m_sessionComplete;     // true = Phase 3a: target reached, no more trades
   bool   m_secondaryHaltFired;  // true = Phase 3b: secondary halt, no more trades

public:
   CASE_RiskEngine() : m_atrHandle(INVALID_HANDLE),
                    m_peakEquity(0.0),
                    m_cachedRegime((int)REGIME_COMPRESSION),
                    m_cachedScore(0.0),
                    m_sessionTarget(0.0),
                    m_secondaryBalance(0.0),
                    m_inRecoveryMode(false),
                    m_sessionComplete(false),
                    m_secondaryHaltFired(false) {}

   void CacheRegime(ENUM_MARKET_REGIME regime) { m_cachedRegime = (int)regime; }
   void CacheScore(double score)               { m_cachedScore  = score; }

   bool Initialize()
   {
      m_atrHandle          = iATR(_Symbol, PERIOD_M15, InpATRPeriod);
      m_peakEquity         = AccountInfoDouble(ACCOUNT_EQUITY);
      m_sessionTarget      = AccountInfoDouble(ACCOUNT_BALANCE);
      m_secondaryBalance   = 0.0;
      m_inRecoveryMode     = false;
      m_sessionComplete    = false;
      m_secondaryHaltFired = false;

      Print(StringFormat("[RISK] Init | SessionTarget=%.2f | DDHalt=%.0f%% | RecoveryMode=%s",
            m_sessionTarget, InpDDHaltPct, InpDDRecoveryMode ? "ON" : "OFF"));
      Print(StringFormat("[RISK] TP1 default=%s  TP2 default=%s  MinRR=%.2f  (per-regime overrides via profile)",
            EnumToString(InpTP1Mode), EnumToString(InpTP2Mode), InpMinRR));

      return (m_atrHandle != INVALID_HANDLE);
   }

   void Deinitialize()
   {
      if(m_atrHandle != INVALID_HANDLE) IndicatorRelease(m_atrHandle);
   }

   // Call on every tick to keep peak equity current and check recovery milestones.
   void UpdatePeak()
   {
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(eq > m_peakEquity) m_peakEquity = eq;
      if(InpDDRecoveryMode) CheckDDRecovery();
   }

   // v3.12.9 — DD Recovery Mode lifecycle check.
   // Called every tick. Manages Phase 1 → 2 → 3a/3b transitions.
   // All state persists in class members and resets to zero on EA reload
   // (constructor runs fresh on each OnInit).
   void CheckDDRecovery()
   {
      if(InpDDHaltPct <= 0.0) return;

      double balance = AccountInfoDouble(ACCOUNT_BALANCE);

      // ── Phase 3a: session complete — balance reached session target ──
      if(m_sessionComplete)
      {
         // Already in terminal phase — no further action until reload
         return;
      }

      // ── Phase 3b: secondary halt already fired ─────────────────────
      if(m_secondaryHaltFired) return;

      // ── Phase 2: Recovery mode active ─────────────────────────────
      if(m_inRecoveryMode)
      {
         // Check if session target has been recovered
         if(balance >= m_sessionTarget)
         {
            // Target recovered — reset session target to current balance
            // and return to Phase 1 (normal trading continues uninterrupted).
            // This is a milestone log only — trading does NOT stop.
            Print(StringFormat(
               "[RISK][RECOVERY] Session target %.2f recovered! Balance=%.2f | "
               "Resetting session target and resuming normal Phase 1 tracking.",
               m_sessionTarget, balance));
            m_sessionTarget    = balance;   // new Phase 1 reference from here
            m_secondaryBalance = 0.0;
            m_inRecoveryMode   = false;
            m_peakEquity       = AccountInfoDouble(ACCOUNT_EQUITY);
            // m_sessionComplete intentionally NOT set — trading continues
            return;
         }

         // Check secondary halt
         double secondaryHaltFloor = m_secondaryBalance * (1.0 - InpDDHaltPct / 100.0);
         if(balance <= secondaryHaltFloor)
         {
            m_secondaryHaltFired = true;
            Print(StringFormat(
               "[RISK][RECOVERY] SECONDARY HALT: Balance=%.2f <= Floor=%.2f "
               "(%.0f%% below secondary balance %.2f) | "
               "Trading STOPPED — reload EA to resume.",
               balance, secondaryHaltFloor, InpDDHaltPct, m_secondaryBalance));
         }
         return;
      }

      // ── Phase 1: Normal — check if initial DD halt should trigger ──
      if(m_sessionTarget > 0.0)
      {
         double ddFromTarget = ((m_sessionTarget - balance) / m_sessionTarget) * 100.0;
         if(ddFromTarget >= InpDDHaltPct)
         {
            m_secondaryBalance = balance;
            m_inRecoveryMode   = true;
            m_peakEquity       = AccountInfoDouble(ACCOUNT_EQUITY);  // reset peak for recovery phase
            Print(StringFormat(
               "[RISK][RECOVERY] Phase 1 halt triggered: DD=%.1f%% from target %.2f | "
               "Current balance=%.2f | Entering recovery mode | "
               "Secondary halt floor=%.2f",
               ddFromTarget, m_sessionTarget, balance,
               balance * (1.0 - InpDDHaltPct / 100.0)));
         }
      }
   }

   // Returns true if trading is permanently stopped until reload.
   // Called from BuildSetup() as the first gate.
   bool IsTerminalHalt() const
   {
      if(!InpDDRecoveryMode) return false;
      return m_secondaryHaltFired;   // target recovery resumes Phase 1 — not terminal
   }

   string GetTerminalHaltReason() const
   {
      if(m_secondaryHaltFired)
         return StringFormat(
            "DD Recovery: secondary balance %.2f reduced by %.0f%% — reload EA to resume",
            m_secondaryBalance, InpDDHaltPct);
      return "";
   }

   // Returns the block reason string for the Experts tab when terminal halt is active.

   TradeSetup BuildSetup(ENUM_TRADE_DIRECTION direction,
                         StructuralLevels &levels,
                         const RegimeProfile &profile)
   {
      TradeSetup s;
      ZeroMemory(s);
      s.valid  = false;
      s.reason = "RiskEngine init";

      if(direction == DIR_NONE) { s.reason = "RiskEngine: no direction"; return s; }

      //── DD-adaptive multiplier ────────────────────────────────────
      // v3.12.9: recovery mode uses secondary balance as the DD reference.
      double ddPct;
      if(InpDDRecoveryMode && m_inRecoveryMode && m_secondaryBalance > 0.0)
      {
         // Phase 2: DD measured from secondary balance
         double balance = AccountInfoDouble(ACCOUNT_BALANCE);
         ddPct = ((m_secondaryBalance - balance) / m_secondaryBalance) * 100.0;
         ddPct = MathMax(ddPct, 0.0);
      }
      else
      {
         ddPct = GetCurrentDrawdownPct();
      }

      double riskMult = GetRiskMultiplier(ddPct);
      if(riskMult <= 0.0)
      {
         // Terminal halt check — session complete or secondary halt fired
         if(IsTerminalHalt())
         {
            s.reason = GetTerminalHaltReason();
            Print("[RISK] TERMINAL HALT: ", s.reason);
            return s;
         }

         // v3.12.8 Fix 2 / v3.12.9: allow at 0.25× when DD between halt and 1.5× halt.
         // Setup has already passed all 5 pipeline gates — it is proven quality.
         double hardCeiling = InpDDHaltPct * 1.5;
         if(ddPct < hardCeiling)
         {
            riskMult = 0.25;
            Print(StringFormat(
               "[RISK] DD halt override: DD=%.1f%% < ceiling %.0f%% — trading at 0.25× risk",
               ddPct, hardCeiling));
         }
         else
         {
            s.reason = StringFormat("RiskEngine: TRADING HALT — DD=%.1f%% exceeds %.0f%%",
                                    ddPct, InpDDHaltPct);
            Print("[RISK] ", s.reason);
            return s;
         }
      }
      if(riskMult < 1.0)
         Print(StringFormat("[RISK] DD=%.1f%% — risk scaled to %.0f%%", ddPct, riskMult*100.0));

      //── ATR base ─────────────────────────────────────────────────
      double atr[];
      ArraySetAsSeries(atr, true);
      if(CopyBuffer(m_atrHandle, 0, 0, 1, atr) < 1)
         { s.reason = "RiskEngine: ATR buffer fail"; return s; }

      double atrVal  = atr[0];

      // v3.14.0 — SL multiplier and cap from active regime profile.
      // profile.slMultiplier replaces the InpATRMultiplierSL / InpATRMultiplierSL_Wide
      // conditional. profile.slCap replaces InpATRSLCap.
      double slMult = profile.slMultiplier;
      double slCapVal = profile.slCap;

      double slDist = atrVal * slMult;
      bool   slCapped = false;
      if(slCapVal > 0 && slDist > slCapVal)
      {
         Print(StringFormat("[RISK] SL cap applied: %.2f pts -> %.2f pts (ATR=%.5f mult=%.1f cap=%.1f)",
               slDist, slCapVal, atrVal, slMult, slCapVal));
         slDist  = slCapVal;
         slCapped = true;
      }
      Print(StringFormat("[RISK] SL | profile=%s mult=%.1f raw=%.2f final=%.2f%s",
            profile.label, slMult, atrVal*slMult, slDist, slCapped ? " [CAPPED]" : ""));

      double ask = CASE_Broker::GetAsk();
      double bid = CASE_Broker::GetBid();

      if(direction == DIR_LONG)
      {
         s.type     = ORDER_TYPE_BUY;
         s.entry    = ask;
         s.stopLoss = CASE_Math::NormalizePrice(ask - slDist);
      }
      else
      {
         s.type     = ORDER_TYPE_SELL;
         s.entry    = bid;
         s.stopLoss = CASE_Math::NormalizePrice(bid + slDist);
      }
      s.signalPrice = s.entry;

      //── TP1 selection ─────────────────────────────────────────────
      // v3.14.1 — TP mode read from active regime profile.
      // TRENDING=Structural (targets next H4 swing level on momentum moves).
      // COMPRESSION=ATR (no reliable structural target in a tight range).
      // MANIPULATION=Structural (sweep reversal targets the swept level).
      // RANGING=ATR (oscillating price makes structural targets unreliable).
      // Profile defaults replicate InpTP1Mode/InpTP2Mode exactly on deploy.
      ENUM_TP_MODE tp1Mode = (ENUM_TP_MODE)profile.tp1Mode;
      ENUM_TP_MODE tp2Mode = (ENUM_TP_MODE)profile.tp2Mode;

      s.takeProfit1 = ComputeTP(
         tp1Mode, 1,
         direction, s.entry, slDist, atrVal,
         InpATRMultiplierTP1,
         1.2, 2.5,          // hybrid clamp: TP1 between 1.2–2.5 ATR
         levels.tp1, levels.tp1Valid);

      //── TP2 selection ─────────────────────────────────────────────
      s.takeProfit2 = ComputeTP(
         tp2Mode, 2,
         direction, s.entry, slDist, atrVal,
         InpATRMultiplierTP2,
         2.0, 6.0,          // hybrid clamp: TP2 between 2.0–6.0 ATR
         levels.tp2, levels.tp2Valid);

      //── RR check (uses TP2 as runner target) ─────────────────────
      // v3.4.5 fix: RR denominator is always ATR × InpATRMultiplierSL,
      // never the live slDist. This decouples TP validation from SL
      // placement — SL can be adjusted by broker minimum distance or
      // spread without invalidating a structurally valid TP level.
      // A structural TP landing at exactly 2× ATR_SL would previously
      // fail due to floating-point representation; the epsilon guard
      // absorbs that without requiring a larger tolerance margin.
      double tp2Dist    = MathAbs(s.takeProfit2 - s.entry);
      double rrDenom    = atrVal * InpATRMultiplierSL;   // base ATR denominator (regime-agnostic for RR gate)
      s.rr = (rrDenom > 0) ? tp2Dist / rrDenom : 0.0;
      if(s.rr < InpMinRR - 0.0001)
      {
         s.reason = StringFormat("RR %.2f < minimum %.2f", s.rr, InpMinRR);
         Print("[RISK] ", s.reason,
               " | TP2mode=", EnumToString(tp2Mode),
               " profile=", profile.label,
               " struct=", (levels.tp2Valid ? "valid" : "fallback"),
               " | rrDenom=ATR(", DoubleToString(atrVal, 5),
               ")×SLmult(", DoubleToString(InpATRMultiplierSL, 2), ")=",
               DoubleToString(rrDenom, 5));
         return s;
      }

      //── Log which mode was used ───────────────────────────────────
      string tp1src = TPSourceLabel(tp1Mode, levels.tp1Valid);
      string tp2src = TPSourceLabel(tp2Mode, levels.tp2Valid);
      Print(StringFormat("[RISK] TP1=%.5f(%s) TP2=%.5f(%s) RR=%.2f ATR=%.5f src=%s profile=%s",
            s.takeProfit1, tp1src, s.takeProfit2, tp2src, s.rr, atrVal,
            levels.source, profile.label));

      // v3.6.0 — when SL was capped, log the actual live RR against capped
      // slDist alongside the gate RR (which uses uncapped ATR denominator).
      // Gate RR and actual RR can diverge when the cap is active; both are
      // needed for accurate post-trade attribution.
      if(slCapped)
      {
         double actualRR = (slDist > 0) ? tp2Dist / slDist : 0.0;
         Print(StringFormat("[RISK] Actual RR vs capped SL: %.2f  (gate used %.2f vs ATR denom)",
               actualRR, s.rr));
      }

      //── Lot sizing ────────────────────────────────────────────────
      s.lotSize = CalcLotSize(s.entry, s.stopLoss, riskMult);
      if(s.lotSize <= 0) { s.reason = "RiskEngine: lot size=0"; return s; }

      s.valid  = true;
      s.reason = StringFormat("RR=%.2f Lots=%.2f DD=%.1f%% ATR=%.5f TP1[%s] TP2[%s]",
                              s.rr, s.lotSize, ddPct, atrVal, tp1src, tp2src);
      return s;
   }

   // Legacy overload — callers that supply structural levels but no profile.
   // Builds a COMPRESSION default profile so behaviour is conservative.
   TradeSetup BuildSetup(ENUM_TRADE_DIRECTION direction,
                         StructuralLevels &levels)
   {
      RegimeProfile defaultProfile = LoadProfile(REGIME_COMPRESSION);
      return BuildSetup(direction, levels, defaultProfile);
   }

   // Legacy overload — no structural levels and no profile.
   TradeSetup BuildSetup(ENUM_TRADE_DIRECTION direction)
   {
      StructuralLevels empty;
      ZeroMemory(empty);
      empty.source = "None";
      RegimeProfile defaultProfile = LoadProfile(REGIME_COMPRESSION);
      return BuildSetup(direction, empty, defaultProfile);
   }

   double GetCurrentDrawdownPct()
   {
      if(m_peakEquity <= 0) return 0.0;
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double dd = ((m_peakEquity - equity) / m_peakEquity) * 100.0;
      return MathMax(0.0, dd);
   }

private:
   //------------------------------------------------------------------
   // ComputeTP — central TP level resolver.
   // Applies InpTP1Mode / InpTP2Mode to pick between ATR and structural.
   //
   // Parameters:
   //   mode         — TP_ATR / TP_STRUCTURAL / TP_HYBRID
   //   tpNumber     — 1 or 2 (used only for log labels)
   //   direction    — trade direction
   //   entry        — entry price
   //   slDist       — SL distance in price (for ATR fallback)
   //   atrVal       — current M15 ATR value
   //   atrMult      — config multiplier (InpATRMultiplierTP1 or TP2)
   //   hybridFloor  — minimum ATR multiple for hybrid clamp
   //   hybridCeil   — maximum ATR multiple for hybrid clamp
   //   structLevel  — structural price level from SetupEngine
   //   structValid  — true if structLevel is usable
   //
   // Returns the normalised price level for the TP.
   //
   // v3.4.1 fix: TP_ATR guard is now a standalone early return in its
   // own if block. Previously the combined condition
   //   if(mode == TP_ATR || !structValid)
   // was susceptible to enum-cast ambiguity in MQL5's compiled form
   // allowing structural levels to bleed through when structValid=true.
   // Two explicit guards eliminate this entirely.
   //------------------------------------------------------------------
   double ComputeTP(ENUM_TP_MODE  mode,
                    int           tpNumber,
                    ENUM_TRADE_DIRECTION direction,
                    double        entry,
                    double        slDist,
                    double        atrVal,
                    double        atrMult,
                    double        hybridFloor,
                    double        hybridCeil,
                    double        structLevel,
                    bool          structValid)
   {
      double atrTarget = atrVal * atrMult;

      // Guard 1 — TP_ATR mode: return ATR immediately.
      // This block is intentionally standalone so that structValid
      // has absolutely no influence on the ATR path.
      if((int)mode == (int)TP_ATR)
      {
         return CASE_Math::NormalizePrice(
            (direction == DIR_LONG) ? entry + atrTarget : entry - atrTarget);
      }

      // Guard 2 — structural level unavailable.
      // v3.4.8: before falling back to ATR, attempt H4 swing level
      // as a secondary structural source. H4 swing highs/lows are always
      // available regardless of setup class and reflect genuine price
      // structure visible to any market participant. Only if H4 swing
      // also fails does the function fall through to ATR.
      if(!structValid)
      {
         double h4Level = 0.0;
         if(FindH4SwingTP(direction, entry, atrVal, h4Level))
         {
            Print(StringFormat(
               "[RISK] TP%d structural unavailable — H4 swing fallback %.5f (mode=%s)",
               tpNumber, h4Level, EnumToString(mode)));
            return CASE_Math::NormalizePrice(h4Level);
         }
         Print(StringFormat(
            "[RISK] TP%d structural unavailable — ATR fallback (no H4 swing) (mode=%s)",
            tpNumber, EnumToString(mode)));
         return CASE_Math::NormalizePrice(
            (direction == DIR_LONG) ? entry + atrTarget : entry - atrTarget);
      }

      // From this point: mode is TP_STRUCTURAL or TP_HYBRID,
      // and a valid structural level exists.
      double structDist = MathAbs(structLevel - entry);

      if((int)mode == (int)TP_STRUCTURAL)
      {
         // Use structural level; ATR fallback only if level is clearly
         // unusable (< 0.5 ATR away — would be inside spread noise).
         if(structDist >= atrVal * 0.5)
            return CASE_Math::NormalizePrice(structLevel);
         // Structural level too close — fall back to ATR
         Print(StringFormat("[RISK] TP%d structural %.5f too close (%.2fATR < 0.5) — ATR fallback",
               tpNumber, structLevel, structDist / atrVal));
         return CASE_Math::NormalizePrice(
            (direction == DIR_LONG) ? entry + atrTarget : entry - atrTarget);
      }

      // TP_HYBRID — structural level accepted only if within ATR bounds
      double floorDist = atrVal * hybridFloor;
      double ceilDist  = atrVal * hybridCeil;

      if(structDist >= floorDist && structDist <= ceilDist)
         return CASE_Math::NormalizePrice(structLevel);

      // Outside bounds — fall back to ATR
      Print(StringFormat("[RISK] TP%d hybrid: structural %.5f (%.2fATR) outside [%.1f–%.1f]ATR — ATR fallback",
            tpNumber, structLevel, structDist / atrVal, hybridFloor, hybridCeil));
      return CASE_Math::NormalizePrice(
         (direction == DIR_LONG) ? entry + atrTarget : entry - atrTarget);
   }

   //------------------------------------------------------------------
   // v3.4.8 — FindH4SwingTP
   // Secondary structural TP source used when SetupEngine levels are
   // unavailable. Scans the last 8 H4 bars for the nearest swing
   // low (SHORT) or swing high (LONG) that is within 1–6 ATR of
   // entry. Sets tp1 at the midpoint between entry and the swing.
   // Returns true if a qualifying level is found.
   //
   // Uses the same distance gates as ComputeH4SwingLevels() in
   // SetupEngine to keep behaviour consistent.
   //------------------------------------------------------------------
   bool FindH4SwingTP(ENUM_TRADE_DIRECTION direction,
                      double entry, double atrVal, double &level)
   {
      level = 0.0;
      double h4Hi[], h4Lo[];
      ArraySetAsSeries(h4Hi, true);
      ArraySetAsSeries(h4Lo, true);
      int n = 8;
      if(CopyHigh(_Symbol, PERIOD_H4, 0, n, h4Hi) < n) return false;
      if(CopyLow( _Symbol, PERIOD_H4, 0, n, h4Lo) < n) return false;

      double minD = atrVal * 0.3;   // v3.4.8: matches reduced minDist in SetupEngine
      double maxD = atrVal * 6.0;

      if(direction == DIR_SHORT)
      {
         for(int i = 1; i < n - 1; i++)
         {
            if(h4Lo[i] >= h4Lo[i-1] || h4Lo[i] >= h4Lo[i+1]) continue;
            double dist = entry - h4Lo[i];
            if(dist < minD || dist > maxD) continue;
            // Use midpoint as TP1 (swing low itself is TP2 territory)
            level = entry - dist * 0.5;
            return true;
         }
      }
      else if(direction == DIR_LONG)
      {
         for(int i = 1; i < n - 1; i++)
         {
            if(h4Hi[i] <= h4Hi[i-1] || h4Hi[i] <= h4Hi[i+1]) continue;
            double dist = h4Hi[i] - entry;
            if(dist < minD || dist > maxD) continue;
            level = entry + dist * 0.5;
            return true;
         }
      }
      return false;
   }

   string TPSourceLabel(ENUM_TP_MODE mode, bool structUsed)
   {
      if(mode == TP_ATR)        return "ATR";
      if(!structUsed)           return "ATR(fallback)";
      if(mode == TP_STRUCTURAL) return "Structural";
      return "Hybrid";
   }

   //------------------------------------------------------------------
   // DD-adaptive multiplier table (spec §8.1)
   // v3.12.4: thresholds now scale relative to InpDDHaltPct so the
   // halt level is configurable without touching this function.
   // Default InpDDHaltPct=30.0:
   //   DD < 10%  → full risk (1.00×)
   //   DD < 20%  → reduced  (0.75×)
   //   DD < 30%  → halved   (0.50×)
   //   DD >= 30% → halt     (0.0 → block)
   //------------------------------------------------------------------
   double GetRiskMultiplier(double ddPct)
   {
      double halt  = InpDDHaltPct;
      double tier2 = halt * 0.667;   // ~2/3 of halt level
      double tier1 = halt * 0.333;   // ~1/3 of halt level
      if(ddPct < tier1)  return 1.00;
      if(ddPct < tier2)  return 0.75;
      if(ddPct < halt)   return 0.50;
      return 0.0;   // >= halt → trading halt
   }

   //------------------------------------------------------------------
   // Canonical percent-risk lot formula (GOLD/CFD safe)
   // riskPerLot = (slDistance / tickSize) * tickValue
   //------------------------------------------------------------------
   double CalcLotSize(double entry, double sl, double riskMult = 1.0)
   {
      double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
      double riskAmount = balance * InpRiskPercent / 100.0 * riskMult;

      double slDistance = MathAbs(entry - sl);
      double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      double minLot     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxLot     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      double lotStep    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

      Print(StringFormat("[RISK] Bal=%.2f Risk=%.2f(x%.2f) SLdist=%.5f TickSz=%.5f TickVal=%.5f",
            balance, riskAmount, riskMult, slDistance, tickSize, tickValue));

      if(slDistance <= 0)  { Print("[RISK] FAIL: slDistance=0");  return 0.0; }
      if(tickSize   <= 0)  { Print("[RISK] FAIL: tickSize=0");    return 0.0; }
      if(tickValue  <= 0)  { Print("[RISK] FAIL: tickValue=0");   return 0.0; }
      if(riskAmount <= 0)  { Print("[RISK] FAIL: riskAmount=0");  return 0.0; }

      double riskPerLot = (slDistance / tickSize) * tickValue;
      if(riskPerLot <= 0) { Print("[RISK] FAIL: riskPerLot=0");   return 0.0; }

      double lots = riskAmount / riskPerLot;
      Print(StringFormat("[RISK] riskPerLot=%.4f rawLots=%.4f", riskPerLot, lots));

      if(lotStep > 0) lots = MathFloor(lots / lotStep) * lotStep;
      lots = MathMax(minLot, lots);
      lots = MathMin(maxLot, lots);

      return NormalizeDouble(lots, 2);
   }
};
#endif // ASE_RISKENGINE_MQH
