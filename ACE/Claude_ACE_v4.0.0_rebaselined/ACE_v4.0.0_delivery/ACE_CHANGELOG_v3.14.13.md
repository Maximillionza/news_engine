# ACE v3.14.13 — Reconciled-Position Data Integrity Fix Set

No trading-logic change — entry/exit decisions are identical to
v3.14.12. This release fixes what gets *recorded* when a position
closes without this process having witnessed its open (restart or
multi-hour tick-processing gap while a trade was live), plus a
filename-collision holdout Fix 16 missed. Direct response to auditing
the 2026.08.24–28 live test logs.

## Fix 18 — Uninitialized MAE/MFE fields on reconciled closes
- **Date:** 2026-08-30
- **Root cause:** `CASE_Telemetry::CommitTradeRecord()`
  (`Core/ASE_Telemetry.mqh`) only assigned `rec.mae`, `rec.mfe`,
  `rec.maePct`, `rec.mfePct`, `rec.barsToMFE`, `rec.barsToMAE`,
  `rec.durationBars` inside `if(m_tracking)`, with no `else`.
  `m_tracking` is only ever set `true` by `StartTracking()`, called at
  position-open time in the *same* running process. `TradeRecord rec`
  in `RecordClosedTrade()` (`Core/ASE_StateMachine.mqh`) is a bare
  local struct with no constructor — when the position was opened in
  a prior process instance (restart / tick-gap discovery), these
  fields were never assigned and were read straight off uninitialized
  stack memory.
- **Confirmed in production:** a position that survived a 2026.08.26
  21:06 restart and a subsequent 4.24-hour tick-processing gap closed
  at 2026.08.27 01:21 with `MFE_Pct=1.05e+284` logged to both the
  Journal and the state-log CSV.
- **Fix:** all seven fields now unconditionally zeroed immediately on
  entry to `CommitTradeRecord()`, before the `if(m_tracking)` branch
  runs. "No excursion data available" now degrades to a clean `0.0`
  instead of garbage.
- **Files affected:** `Core/ASE_Telemetry.mqh`

## Fix 19 — Reconciled closes silently mislabeled `EXIT_TRAIL`
- **Date:** 2026-08-30
- **Root cause:** `RecordClosedTrade()` classifies exit reason by
  comparing close price to `m_ctx.tradeSetup.stopLoss` /
  `takeProfit1` / `takeProfit2` / `entry`. For a reconciled position
  these are all default-zero (fresh `m_ctx`, no real setup data
  survived the restart), so none of the proximity checks match and
  classification fell through to the `else exitReason = EXIT_TRAIL`
  default — reporting "trailing stop" for a close the EA has no
  actual exit-mechanism evidence for.
- **Fix:** new `bool m_positionSelfOpened` flag on `CASE_StateMachine`
  (fail-closed, default `false`). Set `true` only at the genuine
  self-open path, alongside `StartTracking()`. Set `false` explicitly
  at the `ProcessIdle()` → `HasOpenPosition()` reroute, where a
  position is discovered already-open rather than opened by this
  instance. `RecordClosedTrade()` now checks this flag first: if
  `false`, the trade classifies as the new `EXIT_RECONCILED` (value 8)
  without running the (untrustworthy) proximity checks at all.
  `ASE_TradeAttribution::ExitReasonStr()` maps it to
  `"Reconciled_NoContext"` so exports distinguish it from generic
  `EXIT_UNKNOWN`.
- **Files affected:** `Models/ASE_Enums.mqh`,
  `Core/ASE_StateMachine.mqh`, `Core/ASE_TradeAttribution.mqh`

## Fix 20 — TradeAttribution filename collision (Fix 16 holdout)
- **Date:** 2026-08-30
- **Root cause:** Fix 16 (v3.14.11) derived `m_csv`'s output filename
  from `ASE_VERSION_TAG` specifically to stop two concurrently-running
  instances from fighting over the same file. `CASE_TradeAttribution`
  was never migrated to the same pattern — its three output files
  (`ASE_v4_trades_full.csv`, `ASE_v4_trades.ndjson`,
  `ASE_v4_attribution.pipe`) stayed hardcoded literals. Confirmed
  recurring on 2026.08.26: `[ATTR] Cannot open CSV output` — whichever
  instance (this EA or ACE Global) inits first locks the files, the
  other runs with attribution exports permanently disabled for that
  session.
- **Fix:** all three filenames now derive from `ASE_VERSION_TAG`, same
  as `m_csv`.
- **Files affected:** `Core/ASE_TradeAttribution.mqh`

## Also in this release
- `InpMagicNumber` bumped 203152 → 203153. No accounting or
  trading-logic change.
- `ASE_VERSION_TAG` bumped `ASE_v3.14.12` → `ASE_v3.14.13`.
- Main file renamed `ACE_v3.14.13.mq5`; header, init banner, and
  `#property version` updated.

## Not fixed in this release
- The GOLD instance (`ACE_v3.14.12`/now `.13`) showed tick-processing
  gaps of 2.0h, 4.24h, and 7.0h this week — an order of magnitude
  larger than the US30/`ACE_Global` instance running on the same
  terminal at similar times. That asymmetry is unexplained and not a
  code fix — needs investigation (VPS resource contention on the
  GOLD chart specifically vs. a genuine platform-wide outage) before
  anything gets changed.
- The AutoTrading-disabled OnInit guard (see `ACE_PENDING_CHANGES.md`,
  PENDING-01) remains deferred — this week's recurrence (24 Aug,
  15 min, self-resolved) didn't meet the trigger condition.

## Validation
1. Compile; confirm the v3.14.13 init banner.
2. Force a restart mid-trade in a demo/test environment (open a
   position, close and reopen the terminal or EA while it's live,
   let it close) and confirm the resulting TRADE row shows
   `Exit=EXIT_RECONCILED`, `MAE_Pct=0.0`, `MFE_Pct=0.0` — not a
   garbage value and not `EXIT_TRAIL`.
3. Run both EA instances concurrently on startup; confirm neither logs
   `[ATTR] Cannot open CSV output`.
