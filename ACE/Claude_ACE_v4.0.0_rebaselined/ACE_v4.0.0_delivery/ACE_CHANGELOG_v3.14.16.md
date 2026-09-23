# ACE v3.14.16 — Breakeven Floor for Skip-Path (MinLot) Positions

**Trading-logic change**, confirmed against real backtest data before
being written, not speculative.

## Fix 23 — Skip path had zero protection between TP1 and original SL
- **Date:** 2026-09-09
- **How this was found:** a v3.14.14-vs-v3.14.15 backtest (same 8-month
  GOLD M15 range, identical inputs) showed fewer trades and lower net
  profit under v3.14.15 (626.37 vs 918.24). Matched all 235 identical
  entries between the two runs by (open time, entry price, volume,
  direction) and isolated the 34 v3.14.14 trades that showed the OLD
  bug's signature (a single unlabeled full-volume close — always a win,
  since that bug could only fire once price reached TP1 profitably).
  33 matched cleanly to the same entry in v3.14.15:
  - **19 rode on to a legitimately bigger win** — avg profit $19.66 →
    $37.33, +$335.72 total. Fix 22 working exactly as designed.
  - **14 reversed all the way back to the untouched original SL and
    became full losses** (~-$20 each) — a -$629 swing on that subgroup.
  - Net effect across all 33: **-$293.34**. Net effect across the
    entire 619-deal backtest: **-$291.87**. These two numbers are the
    same trade to within $1.47 — everything outside this mechanism
    performed identically between versions.
- **Root cause:** removing the old force-close bug (Fix 22, v3.14.15)
  also removed its accidental side effect: because the bug always
  closed the *entire* position the instant it touched TP1, a minLot
  trade could only ever be a full win or a full loss — never "won,
  then gave it back." Fix 22 correctly stopped the forced close, but
  the skip path it introduced left these positions with **no
  protection at all** between TP1 and the original SL — no breakeven
  shift, no trail, because both were (correctly) gated on a partial
  having actually secured profit, and a skipped position never has
  one.
- **Fix:** when the skip path fires (`canSplit == false`), SL now
  shifts to breakeven — the same spread-adjusted calculation the
  partial-success path already used, now extracted into a shared
  helper, `ComputeBreakevenLevel(ptype, entry)`. This is a floor, not
  a trail: no partial was secured, so nothing beyond breakeven is
  justified. `HasAnyTP1Done()` still stays keyed to `m_tp1Done[]` only
  (a real secured partial), so the structural/ATR trail from Fix 21
  still correctly never activates on a skipped-split position — that
  design boundary from v3.14.15 is unchanged, just no longer means
  "zero protection of any kind."
- **Files affected:** `Core/ASE_PartialTP.mqh`

## Also in this release
- `InpMagicNumber` bumped 203155 → 203156 — flagged as a trading-logic
  change.
- `ASE_VERSION_TAG` bumped `ASE_v3.14.15` → `ASE_v3.14.16`.
- Main file renamed `ACE_v3.14.16.mq5`; header, init banner, and
  `#property version` updated.
- New Journal lines: `[PartialTP] BE set (skip path, no partial) |
  Ticket=... Entry=... BE=...` on success, or `BE set FAILED (skip
  path)` if `PositionModify` is rejected — visible alongside the
  existing `[PartialTP] Eligibility` line from v3.14.15.

## Verification performed before writing this fix
- Full trade-by-trade reconciliation of both backtest reports' Deals
  tables (621 and 598 raw deal rows respectively), grouped into 257
  and 247 round-trip positions, matched by exact open-time/price/
  volume/direction key. Confirmed the trade-count drop (362→349 in the
  report's own "Total Trades" stat, which counts closing deals, not
  positions) is explained by fewer two-deal partial-then-final closes,
  and the smaller residual position-count drop (257→247) is explained
  by average holding time increasing (`2:05:35` → `2:40:05`) against a
  fixed `InpMaxPositions=1` constraint — both mechanical, expected
  consequences of v3.14.15, not bugs.
- This fix (Fix 23) has not yet been re-backtested — see Validation.

## Validation
1. Compile; confirm the v3.14.16 init banner.
2. Re-run the same backtest (GOLD M15, same 8-month range, identical
   inputs to the v3.14.14/v3.14.15 comparison) and confirm:
   - The 14 trades that flipped to a loss under v3.14.15 now close at
     or near breakeven instead of the full original SL.
   - The 19 trades that already improved under v3.14.15 are unaffected
     (breakeven-shift only matters for trades that reverse after
     reaching TP1 level; it shouldn't touch ones that continued
     straight to TP2).
   - Net profit should land at or above v3.14.14's 918.24 — recovering
     most or all of the -$291.87 gap, plus keeping the genuine TP2
     upside Fix 22 unlocked.
3. Confirm `[PartialTP] BE set (skip path, no partial)` appears exactly
   once per qualifying trade, immediately after the corresponding
   `Eligibility | ... -> SKIP` line.
