# ACE v3.14.17 — Active-Trade Chart Panel

**Not a trading-logic change.** Purely additive chart visualization —
confirmed via diff against the v3.14.16 baseline that no existing line
in `ASE_StateMachine.mqh` was modified, only new lines added.

## Fix 24 — Active-trade panel, one exception to the "markers only" scope
- **Date:** 2026-09-14
- **Context:** the chart was deliberately kept to pivot S/R rays and BOS
  markers only, per an earlier explicit decision — a live status/text
  panel was considered and turned down at the time in favor of "just
  the key markers... not everything." This release adds one narrow
  exception to that, also on explicit request.
- **What it shows:** a compact label — `Entry`, `SL`, `TP1`, `TP2`,
  unrealized profit in points and R-multiple (computed against the
  *original* SL distance, so it stays meaningful even after SL moves),
  and a one-word `Protection` tag:
  - `NONE` — live SL unchanged from the original stop; full risk still
    on
  - `BE` — live SL sitting at/near entry (covers both the partial-close
    breakeven shift and the v3.14.16 skip-path BE floor — they're
    functionally the same state from the outside: risk capped near
    zero)
  - `TRAIL` — live SL has moved beyond pure breakeven in the favorable
    direction (only the structural/ATR trail does this)
- **Visible only while a position is open.** Created the moment a
  position opens, updated every tick after `Manage()` runs, deleted the
  instant the position closes. Zero footprint the rest of the time.
- **Design choice — no new coupling:** the `Protection` classification
  is derived purely by comparing the position's live SL
  (`PositionGetDouble(POSITION_SL)`) against its own entry and
  originally-recorded SL (`m_ctx.tradeSetup`). It does not query
  `CASE_PartialTP` or `CASE_TradeManager` internals at all — so it
  can't drift out of sync with whatever those classes decide to do,
  now or after some future change to either.
- **Motivation:** this entire session's TP1/TP2/breakeven/trail
  debugging (Fixes 21–23) was only possible by reading Journal lines
  after the fact. There was no way to see, live, which protection
  state a given open trade was actually in. This makes that visible on
  the chart in real time.
- **Files affected:** `Core/ASE_ChartVisuals.mqh` (two new methods,
  `UpdateTradePanel()` / `ClearTradePanel()`, plus a new object-name
  helper — the existing `UpdateSR()`/`MarkBOS()`/`Deinitialize()`
  methods are unchanged), `Core/ASE_StateMachine.mqh` (new include, one
  new member — a second `CASE_ChartVisuals` instance, separate from the
  one `CASE_StructureEngine` already owns for BOS/SR; disjoint object
  names, no collision — plus init/deinit wiring and two call sites).

## Also in this release
- `InpMagicNumber` bumped 203156 → 203157, per the standing
  every-version convention — explicitly flagged in-code as NOT a
  trading-logic change this time, breaking the pattern of the last
  three releases.
- `ASE_VERSION_TAG` bumped `ASE_v3.14.16` → `ASE_v3.14.17`.
- Main file renamed `ACE_v3.14.17.mq5`; header, init banner, and
  `#property version` updated.

## Verification performed before writing this fix
- Full diff against the v3.14.16 baseline: every changed line in
  `ASE_StateMachine.mqh` is additive (new include, new member, new
  init/deinit calls, two new call sites) — not one existing line was
  modified or removed anywhere in the file.
- Brace/paren balance confirmed on all four touched files.

## Validation
1. Compile; confirm the v3.14.17 init banner.
2. Open a demo/test position and confirm the panel appears immediately
   showing correct Entry/SL/TP1/TP2 and `Protection: NONE`.
3. Let it reach TP1 on a position large enough to split — confirm
   `Protection` switches to `BE` right when `[PartialTP] BE set` logs.
4. Let it reach TP1 on a `minLot` position (skip path) — confirm
   `Protection` shows `BE` here too, right when `[PartialTP] BE set
   (skip path, no partial)` logs.
5. Close the position (either TP2 or SL) and confirm the panel
   disappears from the chart immediately.
