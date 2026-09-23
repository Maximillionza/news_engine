# ACE v3.14.15 — Partial-TP MinLot Split Guard

**This release changes trading behavior for any position sized at or
near minLot.** Those trades will now run for TP2 whole instead of
auto-closing entirely at TP1.

## Fix 22 — Partial close silently consumed the entire position at TP1
- **Date:** 2026-09-09
- **Root cause:** `CASE_PartialTP::Process()` (`Core/ASE_PartialTP.mqh`)
  computed the TP1 partial-close volume as
  `NormalizeDouble(vol * InpPartialTPPercent / 100.0, volDigits)`, then
  force-floored it up to `SYMBOL_VOLUME_MIN` whenever the computed split
  fell below that: `if(closeVol < minLot) closeVol = minLot;`. On a
  position already sized at `minLot` (`0.01`), 50% of that (`0.005`)
  floors right back up to the full `0.01` — the entire position, not a
  partial. The remaining "runner" leg that was supposed to continue
  toward TP2 never existed.
- **Confirmed in production:** 2026-09-09, a `0.01`-lot GOLD trade
  (`Bal=527.61`, `rawLots=0.0021` floored to `minLot`) logged
  `[PartialTP] Ticket=926099287 Closed=0.01` — its entire size — and the
  full ticket closed 32ms later with `Exit=EXIT_TP1`. The user manually
  replicated the same Entry/SL/TP1/TP2 and the position ran to full TP2.
  Not a trail-timing issue (v3.14.14's Fix 21 has nothing to act on when
  no runner leg exists in the first place) — the partial itself ate the
  whole position.
- **Fix:** the partial now only activates if BOTH the partial leg and
  the leftover runner would independently clear `minLot`
  (`canSplit = (closeVol >= minLot) && (remainder >= minLot)`). If not,
  the split is skipped entirely — no `PositionClosePartial` call, no
  breakeven shift, no trail activation — and the full position rides
  its original SL/TP2 bracket untouched.
- **Trail-gating stays correct for skipped tickets:** a new, separate
  `m_tp1Evaluated[]` array (distinct from the existing `m_tp1Done[]`)
  tracks "a TP1 decision has been made for this ticket" regardless of
  outcome, so `Process()` doesn't re-evaluate the same ticket every
  tick. `HasAnyTP1Done()` — which gates the structural/ATR trail
  (Fix 21) — stays keyed to `m_tp1Done[]` only, i.e. a REAL secured
  partial. A skipped ticket never marks `m_tp1Done`, so the trail
  correctly never activates on it either: no profit was secured to
  justify trailing off the original stop, so it shouldn't move.
- **Full-record logging, per explicit request:** every time price
  reaches TP1 — activated or skipped — one line now prints:
  `[PartialTP] Eligibility | Ticket=... Vol=... Pct=... CloseVol=...
  Remainder=... MinLot=... -> ACTIVATE` or `-> SKIP (would leave
  <minLot runner)`. Logged unconditionally, not just when the guard
  fires, so the Journal has a complete record to check against on any
  trade, not only the ones that hit the edge case.
- **Files affected:** `Core/ASE_PartialTP.mqh`

## Also in this release
- `InpMagicNumber` bumped 203154 → 203155 — flagged in-code as a
  trading-logic change.
- `ASE_VERSION_TAG` bumped `ASE_v3.14.14` → `ASE_v3.14.15`.
- Main file renamed `ACE_v3.14.15.mq5`; header, init banner, and
  `#property version` updated.

## Not addressed in this release
- The underlying position-sizing gap this exposes — `rawLots=0.0021`
  vs. `minLot=0.01`, meaning real risk per trade is currently running
  ~4.76x the configured `InpRiskPercent` (0.50% nominal, ~2.4% real) —
  is a separate, still-open decision. This release stops the min-lot
  floor from also destroying the TP1/TP2 split; it does not change
  position sizing itself. Raising `InpRiskPercent` enough to clear
  `2×minLot` with real headroom (roughly 9-10% per trade at the
  current $527.61 balance) was discussed but deliberately not applied
  here — that's a risk-profile decision, not a bug fix, and needs to
  be made on purpose.

## Validation
1. Compile; confirm the v3.14.15 init banner.
2. On the next trade that reaches TP1, confirm exactly one
   `[PartialTP] Eligibility` line appears (not one per tick), and that
   the verdict matches expectations given that trade's lot size.
3. For a trade sized at `minLot`, confirm it now shows `-> SKIP` and
   the position's Journal/CSV record shows no `[PartialTP] Closed=`
   line, no BE-shift line, and — if it goes on to close later — an
   exit reason other than a spurious `EXIT_TP1` at the TP1 price level.
4. For a trade sized comfortably above `2×minLot`, confirm it still
   shows `-> ACTIVATE` and behaves exactly as before (partial closes,
   BE shift applied, runner continues toward TP2 under the Fix 21
   trail gate).
