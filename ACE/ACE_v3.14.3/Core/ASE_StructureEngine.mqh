#ifndef ASE_STRUCTUREENGINE_MQH
#define ASE_STRUCTUREENGINE_MQH
#include "../Models/ASE_Structs.mqh"
#include "../Models/ASE_Config.mqh"
//+------------------------------------------------------------------+
//| ASE v3 — H4 Structure Engine                                     |
//| FIX #13: Pivot scan now returns the MOST RECENT qualifying pivot  |
//|           (lowest bar index in AsTimeSeries array) rather than   |
//|           the highest/lowest extreme across all bars. This is    |
//|           correct ICT/SMC behaviour — we trade the most recent   |
//|           broken swing level, not the historical extreme.        |
//|                                                                  |
//| v3.7.0 — Ranging-day staleness guard (Task 07):                  |
//|   m_lastBOSTime tracks when the most recent H1 BOS fired.        |
//|   If InpH1BiasStaleBars H1 bars have elapsed with no new BOS,   |
//|   bias is reset to DIR_NONE and the pipeline is held until a     |
//|   fresh BOS re-establishes direction. Prevents stale prior-      |
//|   session bias from entering trades on a ranging day.            |
//|   Default: 20 H1 bars (~2 sessions). 0 = disabled.             |
//+------------------------------------------------------------------+

#define STRUCT_SWING_LOOKBACK  20
#define STRUCT_SWING_PIVOT     3

class CASE_StructureEngine
{
private:
   int m_atrHandle;
   int m_emaFastHandle;
   int m_emaSlowHandle;

   double               m_lastSwingHigh;
   double               m_lastSwingLow;
   ENUM_STRUCTURE_TYPE  m_lastBOS;
   ENUM_TRADE_DIRECTION m_structureBias;
   ENUM_TRADE_DIRECTION m_h4ClosedDir;      // H4 last closed candle dir (context/logging only)
   ENUM_TRADE_DIRECTION m_h1BiasCurrent;    // v3.5.0: current H1 structure bias
   ENUM_TRADE_DIRECTION m_h1BiasPrior;      // v3.5.0: prior H1 bias (for flip logging)
   double               m_h1SwingHigh;      // v3.5.0: most recent H1 swing high used for BOS
   double               m_h1SwingLow;       // v3.5.0: most recent H1 swing low used for BOS
   int                  m_h1ConfirmCount;    // retained for logging compatibility
   datetime             m_lastH1Bar;         // retained for logging compatibility
   datetime             m_lastBOSTime;       // v3.7.0: when the most recent H1 BOS fired
   bool                 m_requiresReconfirm; // v3.9.1: true = wait for next BOS after loss
   datetime             m_reconfirmSetTime;  // v3.9.4: when RequireReconfirmation() was called
   // v3.12.1 Fix 1: direction of the LOSING trade that triggered reconfirmation.
   // While reconfirmation is pending the gate receives this held direction
   // instead of the post-loss BOS direction. A losing LONG trade often
   // produces a SHORT BOS (the pullback that caused the loss). Without this
   // hold, the gate sees H1BOS=SHORT vs D1=LONG → 1v1 split → DIR_NONE
   // permanently. Holding at LONG means the gate resolves LONG (D1+H1held=2)
   // and trades can resume once reconfirmation clears.
   ENUM_TRADE_DIRECTION m_preLossDirection;

public:
   CASE_StructureEngine() : m_atrHandle(INVALID_HANDLE),
                            m_emaFastHandle(INVALID_HANDLE),
                            m_emaSlowHandle(INVALID_HANDLE),
                            m_h4ClosedDir(DIR_NONE),
                            m_h1BiasCurrent(DIR_NONE),
                            m_h1BiasPrior(DIR_NONE),
                            m_h1SwingHigh(0.0),
                            m_h1SwingLow(0.0),
                            m_h1ConfirmCount(0),
                            m_lastH1Bar(0),
                            m_lastBOSTime(0),
                            m_requiresReconfirm(false),
                            m_reconfirmSetTime(0),
                            m_preLossDirection(DIR_NONE),
                            m_lastSwingHigh(0), m_lastSwingLow(0),
                            m_lastBOS(STRUCT_NONE),
                            m_structureBias(DIR_NONE), m_biasBlockBar(0),
                            m_biasGraceUntil(0), m_biasMinNextBlock(0),
                            m_graceJustStarted(false) {}

   bool Initialize()
   {
      m_atrHandle     = iATR(_Symbol, PERIOD_H4, 14);
      m_emaFastHandle = iMA(_Symbol, PERIOD_H4, InpH4FastEMA, 0, MODE_EMA, PRICE_CLOSE);
      m_emaSlowHandle = iMA(_Symbol, PERIOD_H4, InpH4SlowEMA, 0, MODE_EMA, PRICE_CLOSE);

      return (m_atrHandle     != INVALID_HANDLE &&
              m_emaFastHandle != INVALID_HANDLE &&
              m_emaSlowHandle != INVALID_HANDLE);
   }

   void Deinitialize()
   {
      if(m_atrHandle     != INVALID_HANDLE) IndicatorRelease(m_atrHandle);
      if(m_emaFastHandle != INVALID_HANDLE) IndicatorRelease(m_emaFastHandle);
      if(m_emaSlowHandle != INVALID_HANDLE) IndicatorRelease(m_emaSlowHandle);
   }

   //------------------------------------------------------------------
   // v3.5.0: H1 MARKET STRUCTURE BIAS ENGINE
   //
   // Determines HTF direction from H1 Break of Structure (BOS).
   //
   // LONG  bias: H1 price closes above the most recent H1 swing high
   //             (higher high confirmed by candle close — not a wick).
   // SHORT bias: H1 price closes below the most recent H1 swing low
   //             (lower low confirmed by candle close — not a wick).
   // NONE:       Price inside the prior H1 swing range — no genuine
   //             HTF bias. Pipeline holds. Correct for ranging days.
   //
   // SWING DETECTION:
   //   A swing high requires bar[i].high > bar[i±InpH1SwingPivot].high
   //   for all pivot bars on each side. Same for swing low.
   //   Looks back InpH1SwingLookback closed H1 bars.
   //
   // BOS CONFIRMATION:
   //   Requires full candle CLOSE beyond the swing level.
   //   Wicks do not count — prevents stop-hunt spikes from flipping bias.
   //
   // BIAS PERSISTENCE:
   //   Once set, bias holds until the opposite BOS occurs.
   //   Does not reset at H4 bar boundaries.
   //   Resets to DIR_NONE after trade close (via ResetH1Bias()).
   //
   // H4 CONTEXT:
   //   H4 last closed candle direction logged for reference only.
   //   Not a gate — no gating effect on pipeline.
   //------------------------------------------------------------------
   ValidationResult Evaluate(ENUM_TRADE_DIRECTION &direction)
   {
      ValidationResult r;
      r.passed  = false;
      r.reason  = "H1 structure: scanning";
      r.score   = 0.0;
      direction = DIR_NONE;

      // ── H4 context (logging only) ───────────────────────────────────
      double h4Cl[], h4Op[];
      ArraySetAsSeries(h4Cl, true);
      ArraySetAsSeries(h4Op, true);
      if(CopyClose(_Symbol, PERIOD_H4, 1, 1, h4Cl) >= 1 &&
         CopyOpen( _Symbol, PERIOD_H4, 1, 1, h4Op) >= 1)
      {
         ENUM_TRADE_DIRECTION h4Dir = (h4Cl[0] > h4Op[0]) ? DIR_LONG : DIR_SHORT;
         if(m_h4ClosedDir != h4Dir)
         {
            m_h4ClosedDir = h4Dir;
            Print(StringFormat("[STRUCT] H4 context updated: %s (reference only)",
                  h4Dir == DIR_LONG ? "BULLISH" : "BEARISH"));
         }
      }

      // ── H1 Swing Detection ─────────────────────────────────────────
      // ── H1 Swing Detection ─────────────────────────────────────────
      // When reconfirmation is pending after a loss, extend the lookback
      // to InpH1SwingLookback * 3 so the scan can find a swing pivot in
      // a strongly trending market where recent bars have already exceeded
      // the normal lookback window's swing highs/lows.
      int effectiveLookback = (m_requiresReconfirm)
                              ? InpH1SwingLookback * 3
                              : InpH1SwingLookback;

      int needed = effectiveLookback + InpH1SwingPivot + 1;
      double h1Hi[], h1Lo[], h1Cl[], h1Op[];
      ArraySetAsSeries(h1Hi, true); ArraySetAsSeries(h1Lo, true);
      ArraySetAsSeries(h1Cl, true); ArraySetAsSeries(h1Op, true);

      if(CopyHigh( _Symbol, PERIOD_H1, 1, needed, h1Hi) < needed ||
         CopyLow(  _Symbol, PERIOD_H1, 1, needed, h1Lo) < needed ||
         CopyClose(_Symbol, PERIOD_H1, 1, needed, h1Cl) < needed ||
         CopyOpen( _Symbol, PERIOD_H1, 1, needed, h1Op) < needed)
      {
         r.reason = "H1 structure: buffer fail (holding current bias)";
         direction = m_h1BiasCurrent;
         r.passed  = (m_h1BiasCurrent != DIR_NONE);
         r.score   = r.passed ? 15.0 : 0.0;
         return r;
      }

      // Find most recent H1 swing high and swing low within effectiveLookback
      // bar[0] in these arrays = last closed H1 (index 1 on chart)
      double swingHigh = 0.0, swingLow = 0.0;
      int    shBar = -1, slBar = -1;

      for(int i = InpH1SwingPivot; i < effectiveLookback; i++)
      {
         if(shBar < 0)
         {
            bool isPivotHigh = true;
            for(int k = 1; k <= InpH1SwingPivot; k++)
            {
               if(h1Hi[i] <= h1Hi[i-k] || h1Hi[i] <= h1Hi[i+k])
               { isPivotHigh = false; break; }
            }
            if(isPivotHigh) { swingHigh = h1Hi[i]; shBar = i; }
         }
         if(slBar < 0)
         {
            bool isPivotLow = true;
            for(int k = 1; k <= InpH1SwingPivot; k++)
            {
               if(h1Lo[i] >= h1Lo[i-k] || h1Lo[i] >= h1Lo[i+k])
               { isPivotLow = false; break; }
            }
            if(isPivotLow) { swingLow = h1Lo[i]; slBar = i; }
         }
         if(shBar >= 0 && slBar >= 0) break;
      }

      // ── Reconfirmation fallback for strongly trending markets ───────
      // If reconfirmation is pending and the extended scan still finds no
      // swing pivot (sustained trend has broken all pivots in the window),
      // use the highest/lowest close in the lookback as the reference level.
      // A new H1 close above that level confirms the trend is intact.
      if(m_requiresReconfirm)
      {
         if(swingHigh <= 0.0 && m_h1BiasCurrent == DIR_LONG)
         {
            // Find highest close in the extended lookback as reference
            for(int i = 1; i < effectiveLookback; i++)
               if(h1Hi[i] > swingHigh) swingHigh = h1Hi[i];
            if(swingHigh > 0.0)
               Print(StringFormat("[STRUCT] Reconfirm: no swing pivot found — "
                     "using lookback high=%.5f as BOS reference", swingHigh));
         }
         if(swingLow <= 0.0 && m_h1BiasCurrent == DIR_SHORT)
         {
            swingLow = h1Lo[1];
            for(int i = 1; i < effectiveLookback; i++)
               if(h1Lo[i] < swingLow) swingLow = h1Lo[i];
            if(swingLow > 0.0)
               Print(StringFormat("[STRUCT] Reconfirm: no swing pivot found — "
                     "using lookback low=%.5f as BOS reference", swingLow));
         }
      }

      // ── v3.14.6 NEW: NONE-bias breakout fallback ───────────────────
      // The reconfirmation fallback above only fires when m_h1BiasCurrent
      // is already LONG or SHORT — it exists to RE-confirm a held bias
      // once the fractal scan loses its pivot mid-trend. It did nothing
      // when bias is flat (DIR_NONE), leaving no path to ever establish
      // an initial bias during a persistent, pivot-less rally. Confirmed
      // via 06.26 log: swingH=0.00000 from 09:07 to 22:06 straight,
      // REGIME_RANGING all day, zero TRIGGER_EVALs the entire session,
      // despite a clean 4027->4095 rally on the chart (no H1 retracement
      // ever long/deep enough to confirm a fractal pivot before the move
      // itself topped out).
      // Same channel-breakout logic as the reconfirm fallback (highest
      // high / lowest low in the lookback) applied with no directional
      // anchor — both sides are computed and bosLong/bosShort below
      // naturally resolve whichever side qualifies. Scored identically to
      // a real pivot BOS via the body/ATR tiering further down — no extra
      // discount, since the composite score threshold and every
      // downstream gate (liquidity, setup, regime threshold) are
      // untouched and still do the filtering.
      if(m_h1BiasCurrent == DIR_NONE)
      {
         if(swingHigh <= 0.0)
         {
            for(int i = 1; i < effectiveLookback; i++)
               if(h1Hi[i] > swingHigh) swingHigh = h1Hi[i];
            if(swingHigh > 0.0)
               Print(StringFormat("[STRUCT] No bias yet: no swing pivot found — "
                     "using lookback high=%.5f as BOS reference", swingHigh));
         }
         if(swingLow <= 0.0)
         {
            swingLow = h1Lo[1];
            for(int i = 1; i < effectiveLookback; i++)
               if(h1Lo[i] < swingLow) swingLow = h1Lo[i];
            if(swingLow > 0.0)
               Print(StringFormat("[STRUCT] No bias yet: no swing pivot found — "
                     "using lookback low=%.5f as BOS reference", swingLow));
         }
      }

      // ── BOS Detection ──────────────────────────────────────────────
      // bar[0] = most recent closed H1 candle (the potential BOS bar)
      double lastClose = h1Cl[0];
      double lastOpen  = h1Op[0];

      // ATR for scoring the BOS strength
      double atr[];
      ArraySetAsSeries(atr, true);
      double atrVal = 0.0;
      if(CopyBuffer(m_atrHandle, 0, 0, 2, atr) >= 2) atrVal = atr[0];
      double bosBody = MathAbs(lastClose - lastOpen);

      bool bosLong  = (swingHigh > 0 && lastClose > swingHigh);
      bool bosShort = (swingLow  > 0 && lastClose < swingLow);

      ENUM_TRADE_DIRECTION newBias = m_h1BiasCurrent;   // default: hold current bias

      if(bosLong && !bosShort)
      {
         newBias       = DIR_LONG;
         m_h1SwingHigh = swingHigh;
         m_lastBOSTime = TimeCurrent();   // v3.7.0: stamp fresh BOS time
         m_requiresReconfirm = false;     // v3.9.1: fresh BOS clears post-loss gate
         m_preLossDirection  = DIR_NONE;  // v3.12.1: clear held direction
      }
      else if(bosShort && !bosLong)
      {
         newBias      = DIR_SHORT;
         m_h1SwingLow = swingLow;
         m_lastBOSTime = TimeCurrent();   // v3.7.0: stamp fresh BOS time
         m_requiresReconfirm = false;     // v3.9.1: fresh BOS clears post-loss gate
         m_preLossDirection  = DIR_NONE;  // v3.12.1: clear held direction
      }
      // Both false: price inside range — retain prior bias
      // Both true:  conflicting (only possible in extreme gap) — retain prior bias

      // ── Bias Flip Logging ──────────────────────────────────────────
      if(newBias != DIR_NONE && newBias != m_h1BiasCurrent)
      {
         Print(StringFormat(
            "[STRUCT] H1 BOS %s | close=%.5f vs swing%s=%.5f | bar=%d bars ago | body=%.5f",
            newBias == DIR_LONG ? "LONG (higher high)" : "SHORT (lower low)",
            lastClose,
            newBias == DIR_LONG ? "High" : "Low",
            newBias == DIR_LONG ? swingHigh : swingLow,
            newBias == DIR_LONG ? shBar : slBar,
            bosBody));
      }

      m_h1BiasPrior   = m_h1BiasCurrent;
      m_h1BiasCurrent = newBias;
      m_structureBias = newBias;

      // ── v3.7.0: Ranging-day staleness guard ───────────────────────
      // If the bias was set in a prior session and no new H1 BOS has
      // fired within InpH1BiasStaleBars H1 bars, the bias is stale.
      // Reset to DIR_NONE and block the pipeline so we don't trade a
      // direction confirmed many hours ago on a market that has since
      // turned rangebound. newBias here is the held value from the last
      // BOS — a fresh BOS above updates m_lastBOSTime and bypasses this.
      if(InpH1BiasStaleBars > 0 &&
         newBias != DIR_NONE &&
         m_lastBOSTime > 0 &&
         !bosLong && !bosShort)   // no new BOS this evaluation
      {
         long staleLimit = (long)InpH1BiasStaleBars * PeriodSeconds(PERIOD_H1);
         long elapsed    = (long)(TimeCurrent() - m_lastBOSTime);
         if(elapsed > staleLimit)
         {
            int barsElapsed = (int)(elapsed / PeriodSeconds(PERIOD_H1));
            Print(StringFormat(
               "[STRUCT] Ranging guard: bias %s stale — last BOS %d H1 bars ago "
               "(limit=%d) — resetting to NONE",
               newBias == DIR_LONG ? "LONG" : "SHORT",
               barsElapsed, InpH1BiasStaleBars));
            m_h1BiasCurrent  = DIR_NONE;
            m_h1BiasPrior    = DIR_NONE;
            m_structureBias  = DIR_NONE;
            newBias          = DIR_NONE;
            m_lastBOSTime    = 0;   // reset — next BOS will re-stamp
         }
      }

      // ── v3.9.1: Post-loss reconfirmation gate ─────────────────────
      // If RequireReconfirmation() was called after a losing trade,
      // block the pipeline until a fresh BOS fires (cleared above).
      // v3.9.3: time-based expiry — if reconfirmation has been pending
      // for more than 5 trading days (120 H1 bars) without a fresh BOS,
      // clear it automatically. This prevents indefinite silence in
      // strongly trending markets where the H1 swing scan cannot find a
      // qualifying pivot above/below the current price level.
      if(m_requiresReconfirm)
      {
         bool expired = false;
         if(m_reconfirmSetTime > 0)
         {
            // v3.9.4 fix: expiry clock starts from when the loss occurred
            // (m_reconfirmSetTime), not from the last BOS. Using m_lastBOSTime
            // caused immediate expiry when the prior BOS was >120 H1 bars ago.
            long elapsedH1 = (long)(TimeCurrent() - m_reconfirmSetTime)
                             / PeriodSeconds(PERIOD_H1);
            // v3.12.0 Fix C: reduce reconfirmation expiry from 120 to 30 H1 bars.
            // In a parabolic gold move no traditional H1 lower-low BOS forms for days,
            // so the 120-bar expiry (5 trading days) kept the block active indefinitely.
            // 30 H1 bars = ~30 trading hours (~1.5 trading days) — long enough to avoid
            // re-entering immediately after consecutive losses, short enough to recover
            // in trending markets where BOS pivots are structurally unavailable.
            if(elapsedH1 > 30)
            {
               m_requiresReconfirm = false;
               m_reconfirmSetTime  = 0;
               m_preLossDirection  = DIR_NONE;  // v3.12.1
               expired = true;
               Print(StringFormat(
                  "[STRUCT] Reconfirmation expired after %d H1 bars since loss — "
                  "pipeline resuming with existing %s bias",
                  (int)elapsedH1,
                  m_h1BiasCurrent == DIR_LONG ? "LONG" : "SHORT"));
            }
         }

         if(m_requiresReconfirm)
         {
            // v3.12.4 Fix 1: reconfirmation no longer blocks direction.
            //
            // ROOT CAUSE (confirmed from Jan 6-7 logs — 11,368 blocks):
            // After one SL loss at 16:52 Jan 6, RequireReconfirmation fired
            // and returned Direction=NONE + r.passed=false. This shut down
            // the pipeline entirely until a fresh H1 BOS fired OR the 30H1
            // expiry triggered (~30 trading hours later). In a ranging Jan 7
            // market no fresh BOS formed, so the pipeline was dead for the
            // entire day. Combined with the DD halt, this produced 0 trades
            // on Jan 7 from 18 PASSes. The 2-trade backtest result traces
            // directly to this: one loss → 30+ hour shutdown → repeat.
            //
            // FIX: keep the BOS quality requirement for EXECUTION (r.passed)
            // but do NOT block direction. Return the pre-loss direction with
            // a reduced score (r.score=10 vs normal 15–28) so the pipeline
            // advances. The reduced score means marginal setups won't cross
            // the 60-point threshold — only high-conviction setups fire during
            // the reconfirmation window. The score guard IS the protection.
            // r.passed=true so ProcessHTF advances to SetupEngine normally.
            r.score  = 10.0;   // reduced vs normal 15–28: only strong setups clear threshold
            r.passed = true;   // pipeline advances — score guards entry quality
            r.reason = StringFormat(
               "Reconfirmation window (bias=%s) — reduced score, awaiting fresh BOS",
               newBias == DIR_LONG ? "LONG" : "SHORT");
            direction = newBias;
            return r;
         }
      }

      // ── No bias case ───────────────────────────────────────────────
      if(newBias == DIR_NONE)
      {
         r.reason = StringFormat(
            "H1 structure: no BOS | swingH=%.5f(%dbars) swingL=%.5f(%dbars) | close=%.5f",
            swingHigh, shBar, swingLow, slBar, lastClose);
         Print(StringFormat("[STRUCT] %s", r.reason));
         return r;
      }

      // ── Set output ─────────────────────────────────────────────────
      direction = newBias;

      // Score: strong BOS (displacement body) > moderate > weak
      double score = 20.0;
      if(atrVal > 0)
      {
         if(bosBody >= atrVal * 0.6)       score = 28.0;   // strong displacement BOS
         else if(bosBody >= atrVal * 0.3)  score = 22.0;   // moderate BOS
         else                               score = 15.0;   // weak/marginal BOS
      }

      r.passed = true;
      r.score  = score;
      r.reason = StringFormat(
         "H1 BOS %s | swing%s=%.5f (%d bars) | close=%.5f | body=%.5f(%.0f%% ATR) | H4ctx=%s",
         newBias == DIR_LONG  ? "LONG"  : "SHORT",
         newBias == DIR_LONG  ? "High"  : "Low",
         newBias == DIR_LONG  ? swingHigh : swingLow,
         newBias == DIR_LONG  ? shBar     : slBar,
         lastClose, bosBody,
         atrVal > 0 ? bosBody/atrVal*100 : 0,
         m_h4ClosedDir == DIR_LONG  ? "bull" :
         m_h4ClosedDir == DIR_SHORT ? "bear" : "n/a");

      return r;
   }

   // v3.5.0: Called after trade close to reset H1 structure bias.
   // v3.7.0: Also resets m_lastBOSTime so staleness timer starts fresh.
   // v3.9.1: Retained for edge cases only (e.g. emergency full reset).
   //         Normal post-trade path now uses RequireReconfirmation() below.
   void ResetH1Bias()
   {
      m_h1BiasCurrent      = DIR_NONE;
      m_h1BiasPrior        = DIR_NONE;
      m_h1SwingHigh        = 0.0;
      m_h1SwingLow         = 0.0;
      m_h1ConfirmCount     = 0;
      m_lastH1Bar          = 0;
      m_lastBOSTime        = 0;
      m_requiresReconfirm  = false;
      m_reconfirmSetTime   = 0;
      Print("[STRUCT] H1 structure bias FULL reset");
   }

   // v3.9.1 — Soft reconfirmation gate.
   //
   // Called after a losing trade instead of ResetH1Bias().
   // Preserves the known bias direction, swing levels, and m_lastBOSTime
   // so the staleness guard and swing scan continue from where they were.
   // Sets m_requiresReconfirm = true, which blocks Evaluate() from
   // returning passed=true until one fresh BOS fires in the same direction.
   //
   // Effect: after a loss the EA waits for the NEXT valid H1 BOS in the
   // existing direction before re-entering. It does not require the market
   // to start from scratch — just one confirming structural event.
   // This prevents both (a) immediate re-entry on a losing direction and
   // (b) the indefinite silence caused by a full bias wipe.
   void RequireReconfirmation(ENUM_TRADE_DIRECTION lossDirection = DIR_NONE)
   {
      m_requiresReconfirm  = true;
      m_reconfirmSetTime   = TimeCurrent();
      // v3.12.1 Fix 1: store the direction of the losing trade.
      // GetH1BiasCurrent() at loss time == the direction we were trading.
      // If not explicitly passed, fall back to current bias.
      m_preLossDirection   = (lossDirection != DIR_NONE) ? lossDirection : m_h1BiasCurrent;
      Print(StringFormat("[STRUCT] Reconfirmation required after loss — "
            "current bias=%s retained, waiting for next BOS",
            m_h1BiasCurrent == DIR_LONG ? "LONG" : "SHORT"));
   }

   bool IsReconfirmRequired() const { return m_requiresReconfirm; }
   // v3.12.1: direction held during reconfirmation (the pre-loss trade direction)
   ENUM_TRADE_DIRECTION GetPreLossDirection() const { return m_preLossDirection; }

   // Public accessors
   ENUM_TRADE_DIRECTION GetH4ClosedDirection() { return m_h4ClosedDir; }
   ENUM_TRADE_DIRECTION GetH1BiasCurrent()     { return m_h1BiasCurrent; }
   // v3.11.0 — prior bias exposed so DirectionGate can detect a genuine
   // direction CHANGE (current != prior) vs a continuation of the same bias.
   // A SHORT BOS where prior was LONG is a structural reversal entry.
   // A SHORT BOS where prior was already SHORT is a continuation — not a
   // genuine break for the purposes of the structural exception path.
   ENUM_TRADE_DIRECTION GetH1BiasPrior()       { return m_h1BiasPrior; }
   double               GetH1SwingHigh()       { return m_h1SwingHigh; }
   double               GetH1SwingLow()        { return m_h1SwingLow; }


   ENUM_STRUCTURE_TYPE GetLastStructure() { return m_lastBOS; }
   double GetLastSwingHigh()              { return m_lastSwingHigh; }
   double GetLastSwingLow()               { return m_lastSwingLow;  }

   //------------------------------------------------------------------
   // v3.4.2 — Fix 3: Bias confidence gate.
   //
   // Called from ProcessHTF() after all direction-resolution paths so
   // that the final resolved bias is validated against recent M15 price
   // momentum before the pipeline advances to STATE_WAIT_SETUP.
   //
   // Mechanism: count how many of the last 4 closed M15 bars moved
   // AGAINST the resolved direction.
   //   SHORT bias conflict bar = bar closed ABOVE the previous bar.
   //   LONG  bias conflict bar = bar closed BELOW the previous bar.
   //
   // If 3 or more of the 4 bars conflict, the market is clearly moving
   // against the bias on the M15 timeframe and the setup is structurally
   // stale.  The pipeline is held at STATE_WAIT_HTF for one more bar.
   //
   // This caught today's (2026-05-29) SHORT bias problem: Gold was making
   // consecutive higher closes through the London session while the H4
   // pivot scan continued to report a bearish bias from an old swing.
   //
   // Fail-safe: returns true (confident) when the price buffer fails so
   // a data outage does not permanently suspend trading.
   //
   // Returns true  = bias confirmed  — advance to STATE_WAIT_SETUP
   //         false = momentum conflict — hold at STATE_WAIT_HTF
   //------------------------------------------------------------------
   // v3.4.7: m_biasBlockBar tracks the M15 bar on which the gate last
   // fired a block. ProcessHTF() will not re-enter CheckBiasConfidence()
   // until InpBiasReEvalBars M15 bars have elapsed, preventing the gate
   // from permanently holding the pipeline after a counter-trend burst.
   datetime m_biasBlockBar;       // v3.4.7: set when bias gate fires a block

   // v3.12.6: grace period after cooldown expiry — class members so they
   // persist correctly across calls (static locals inside member functions
   // are unreliable in the MT5 Strategy Tester — confirmed by zero grace
   // blocks in Feb 21-24 v3.12.5 logs despite the fix being present).
   // m_biasGraceUntil: pipeline passes unconditionally until this bar.
   // m_biasMinNextBlock: no new block can fire before this bar — prevents
   // immediate re-triggering on the bar after grace expires.
   datetime m_biasGraceUntil;     // v3.12.6: grace period end (M15 bar time)
   datetime m_biasMinNextBlock;   // v3.12.6: earliest bar a new block can fire
   // v3.12.8: flag set when cooldown JUST expired this call — tells ProcessHTF
   // to set m_htfBarReset so the H4 bar throttle is bypassed on the next tick.
   // Without this, the H4 throttle skips the entire 2-hour grace window because
   // ProcessHTF only runs once per H4 bar (every 4 hours).
   // Confirmed from Mar 7-31 logs: zero grace blocks across 145,198 cycling blocks.
   bool     m_graceJustStarted;

   // v3.4.9: called by StateMachine when bias flip escalation triggers,
   // so the cooldown timer resets cleanly for the new direction.
   void ResetBiasBlockBar()
   {
      m_biasBlockBar     = 0;
      m_biasGraceUntil   = 0;
      m_biasMinNextBlock = 0;
      m_graceJustStarted = false;
   }

   // v3.12.8: ProcessHTF calls this after CheckBiasConfidence returns true.
   // If the cooldown JUST expired this call, ProcessHTF must set m_htfBarReset=true
   // so the H4 bar throttle is bypassed and the grace period is actually evaluated
   // on the next M15 bar rather than the next H4 bar (4 hours later).
   bool WasGraceJustStarted()
   {
      bool val          = m_graceJustStarted;
      m_graceJustStarted = false;   // consume the flag — single-fire
      return val;
   }

   bool CheckBiasConfidence(ENUM_TRADE_DIRECTION direction,
                             double              atrVal,
                             string             &reason)
   {
      if(direction == DIR_NONE)
      {
         reason = "Confidence: DIR_NONE — skip check";
         return true;
      }

      datetime curBar = iTime(_Symbol, PERIOD_M15, 0);

      // v3.12.6: class-member grace period — unconditional pass after cooldown expiry.
      // Root cause of v3.12.5 failure confirmed from Feb 21-24 logs (zero grace blocks):
      // static local variables in MQL5 class member functions are re-initialised per
      // EA instance in the Strategy Tester. The grace never held its value between calls.
      // m_biasGraceUntil is a class member — guaranteed to persist correctly.
      if(m_biasGraceUntil > 0)
      {
         if(curBar < m_biasGraceUntil)
         {
            int barsLeft = (int)((m_biasGraceUntil - curBar) / PeriodSeconds(PERIOD_M15));
            reason = StringFormat("Bias ok — post-cooldown grace (%d bars left) | %s",
                                  barsLeft, direction == DIR_LONG ? "LONG" : "SHORT");
            return true;
         }
         m_biasGraceUntil = 0;   // grace elapsed, clear
      }

      // v3.12.6: minimum re-block gap — prevents immediate re-triggering on the bar
      // after grace expires. This is the second half of the cycling fix:
      // without this, expiry→momentum check→new block fires on the very next M15 bar.
      // m_biasMinNextBlock = grace end + InpBiasReEvalBars bars forward.
      // Total silence per conflict: 8 bars cooldown + 8 grace + 8 gap = 24 bars (6h max).
      if(m_biasMinNextBlock > 0)
      {
         if(curBar < m_biasMinNextBlock)
         {
            int barsLeft = (int)((m_biasMinNextBlock - curBar) / PeriodSeconds(PERIOD_M15));
            reason = StringFormat("Bias ok — re-block gap (%d bars left) | %s",
                                  barsLeft, direction == DIR_LONG ? "LONG" : "SHORT");
            return true;
         }
         m_biasMinNextBlock = 0;   // gap elapsed, new conflicts can now fire
      }

      // One-way cooldown: counts down from m_biasBlockBar.
      // Does not restart on continued conflict — only on the next fresh 4/4 event
      // after m_biasMinNextBlock has cleared.
      if(m_biasBlockBar > 0)
      {
         datetime reEvalBar = (datetime)(m_biasBlockBar +
                              InpBiasReEvalBars * PeriodSeconds(PERIOD_M15));
         if(curBar < reEvalBar)
         {
            int barsLeft = (int)((reEvalBar - curBar) / PeriodSeconds(PERIOD_M15));
            reason = StringFormat("Bias re-eval cooldown: %d bars remaining", barsLeft);
            return false;
         }
         // Cooldown elapsed → set grace and re-block gap, then pass.
         // v3.12.8: grace extended from 8 to 16 M15 bars (4 hours = one H4 bar).
         // Root cause of zero grace blocks: ProcessHTF is H4-throttled (runs once
         // per H4 bar = every 4 hours). An 8-bar (2h) grace window was always
         // fully elapsed by the time ProcessHTF ran next. Grace must span ≥ 1 H4 bar.
         // m_graceJustStarted signals ProcessHTF to set m_htfBarReset=true so the
         // throttle is bypassed and the next M15 bar immediately re-enters HTF eval.
         m_biasBlockBar     = 0;
         m_biasGraceUntil   = (datetime)(curBar +
                              16 * PeriodSeconds(PERIOD_M15));   // 4h = one H4 bar
         m_biasMinNextBlock = (datetime)(curBar +
                              32 * PeriodSeconds(PERIOD_M15));   // 8h after expiry
         m_graceJustStarted = true;   // tells ProcessHTF to bypass H4 throttle
         reason = StringFormat(
            "Bias ok — cooldown elapsed | grace +16 bars (4h) | re-block gap +32 bars | %s",
            direction == DIR_LONG ? "LONG" : "SHORT");
         return true;
      }

      // Momentum conflict check — only when no cooldown, grace, or gap is active.
      double cl[], hi[], lo[];
      ArraySetAsSeries(cl, true);
      ArraySetAsSeries(hi, true);
      ArraySetAsSeries(lo, true);
      if(CopyClose(_Symbol, PERIOD_M15, 0, 6, cl) < 6)
      {
         reason = "Confidence: buffer fail (safe pass)";
         return true;
      }

      int conflictBars    = 0;
      int conflictWickOnly = 0;   // v3.12.7: bars where conflict is wick-driven, not body-driven
      bool hasOHLC = (CopyHigh(_Symbol, PERIOD_M15, 0, 6, hi) >= 6 &&
                      CopyLow (_Symbol, PERIOD_M15, 0, 6, lo) >= 6);

      for(int i = 1; i <= 4; i++)
      {
         if(i + 1 >= 6) break;
         bool closeConflicts = false;
         if(direction == DIR_SHORT && cl[i] > cl[i + 1]) closeConflicts = true;
         if(direction == DIR_LONG  && cl[i] < cl[i + 1]) closeConflicts = true;

         if(closeConflicts)
         {
            conflictBars++;
            // v3.12.7 Fix 4: check if this bar's conflict is body-driven or wick-driven.
            // A spike bar (large range, tiny body, close back inside) should not count
            // as a genuine momentum conflict. Body < 30% of range = wick-dominant.
            if(hasOHLC && atrVal > 0)
            {
               double barRange = hi[i] - lo[i];
               double barBody  = MathAbs(cl[i] - (i+1 < 6 ? cl[i+1] : cl[i]));
               // Use open-close body where open = prior close (M15 closes are adjacent)
               // If range > 0 and body is small fraction of range, it's a wick bar
               if(barRange > 0 && barBody / barRange < 0.30)
                  conflictWickOnly++;
            }
         }
      }

      // Block only when 4/4 bars conflict AND at least 2 have meaningful bodies.
      // Pure wick spikes (all conflict bars are wick-dominant) are not genuine
      // momentum reversals — they are liquidity grabs that reverse immediately.
      int bodyConflicts = conflictBars - conflictWickOnly;
      if(conflictBars >= 4 && bodyConflicts >= 2)
      {
         m_biasBlockBar = curBar;
         reason = StringFormat(
            "M15 momentum %s conflicts %s bias (%d/4 bars, %d body-driven) — holding HTF",
            (direction == DIR_SHORT) ? "bullish" : "bearish",
            (direction == DIR_SHORT) ? "SHORT"   : "LONG",
            conflictBars, bodyConflicts);
         return false;
      }

      reason = StringFormat("Bias ok | %s | conflictBars=%d/4 bodyConflicts=%d",
                             (direction == DIR_SHORT) ? "SHORT" : "LONG",
                             conflictBars, bodyConflicts);
      return true;
   }
};
#endif // ASE_STRUCTUREENGINE_MQH
