# ACE v3.14.12 — Chart Visuals: Key Markers Only

No trading-logic change. Direct response to today's diagnostic
session — you can't see whether the EA is currently assessing
anything, since regime/gate evaluation only ever surfaced through the
Experts log.

## Fix 17 — Pivot-based S/R rays + BOS markers
- **Date:** 2026-07-31
- **Scope, by explicit request:** ONLY the pivot-based support/
  resistance levels the structure engine already tracks, plus a
  marker the instant a break-of-structure confirms. No FVG zones, no
  liquidity markers, no regime/score HUD — those were considered and
  declined in favor of keeping the chart uncluttered.
- **What it draws:** a dashed orange ray from the current active
  (unbroken) pivot high, a dashed blue ray from the current active
  pivot low — both redrawn only when the active pivot actually
  changes (new pivot forms, or the current one breaks and a different
  one becomes active) — and a small arrow at the exact bar/price a BOS
  confirms (green/up for bullish, red/down for bearish).
- **No new detection logic:** every value drawn comes from
  `GetActivePivotHigh()`/`GetActivePivotLow()` and the existing BOS
  confirmation branch in `CASE_StructureEngine::Evaluate()` — both in
  place since v3.14.5 Fix 1. This file only visualizes data the EA
  was already computing.
- **New inputs:** `InpShowChartVisuals` (default `true`) is the
  master toggle. `InpMaxBOSMarkers` (default 20) caps clutter on a
  chart left running for weeks — once the count is exceeded, the
  oldest BOS marker is deleted; set to 0 for unlimited.
- **Files affected:** `Core/ASE_ChartVisuals.mqh` (new),
  `Core/ASE_StructureEngine.mqh`, `Models/ASE_Config.mqh`

## Also in this release
- `InpMagicNumber` bumped 203151 → 203152. No accounting or
  trading-logic change.
- Main file renamed `ACE_v3.14.12.mq5`; header, init banner, and
  `#property version` updated.

## Validation
1. Compile; confirm the v3.14.12 init banner.
2. Attach to a chart and confirm two dashed rays appear near the
   current price (one above, one below) once the H1 pivot registry
   has resolved an active high and low.
3. Confirm no chart objects appear if `InpShowChartVisuals=false`.
4. Watch for a BOS marker the next time price actually breaks a
   tracked pivot — should appear at the exact bar/price of the break,
   matching the `[STRUCT]` BOS log line in the Experts tab.
5. No change expected to trade count, WR, or PF versus v3.14.11 — this
   is a pure visualization addition.
