# ACE v3.14.14 — Structural Trail TP1 Gate

**This release changes trading behavior.** Unlike v3.14.13 (data-integrity
only), this fix changes when the stop loss gets moved — some trades that
previously closed early via the structural trail will now stay open
longer and follow a different profit path (better or worse, depending on
what price does after the point they'd have previously been stopped out).

## Fix 21 — UpdateStructureTrail() ran unconditionally, no TP1 gate
- **Date:** 2026-09-08
- **Root cause:** `CASE_TradeManager::Manage()` (`Core/ASE_TradeManager.mqh`)
  runs two independent trailing mechanisms. `m_trail.Update()` (the
  ATR-distance trail) was already correctly gated behind
  `m_partial.HasAnyTP1Done()` — that fix (v3.6.0) is documented in the
  code with the exact reasoning this bug reproduces: *"the trail ran
  from the first tick after entry, meaning a slow-grinding move could
  tighten the trail against a retracement and stop the runner before
  TP1 was ever reached."* `UpdateStructureTrail()`, called on the line
  directly above it, never received the same gate. Its only condition
  was `bid > entry` (long) / `ask < entry` (short) — any profit greater
  than zero — at which point it sets SL to the nearest confirmed 3-bar
  M15 swing pivot, buffered by only `0.3×ATR`. TP2 targets are computed
  2.0–6.0×ATR out (`ASE_RiskEngine.mqh`). A routine pullback, nowhere
  near large enough to threaten a 2–6×ATR target, was enough to catch
  this trail and close the runner.
- **Confirmed in production:** auditing the 2026.09.01–08 live CSVs, 6
  of 8 winning trades that week closed with `MFE_Pct` (max favorable
  excursion, as % of planned TP2 distance) clustered at 50–51% —
  across three different setup classes (FVG, M15_Displacement,
  EMA_Pullback) and four different planned RR values. That tight a
  cluster across that much variety isn't organic market behavior; it's
  the signature of a mechanical cap.
- **Fix:** `UpdateStructureTrail()` now gated behind
  `m_partial.HasAnyTP1Done()`, identical to the ATR trail below it.
- **Files affected:** `Core/ASE_TradeManager.mqh`

## Also in this release
- `InpMagicNumber` bumped 203153 → 203154 — flagged in-code as a
  trading-logic change, not the routine no-op bump of prior versions.
- `ASE_VERSION_TAG` bumped `ASE_v3.14.13` → `ASE_v3.14.14`.
- Main file renamed `ACE_v3.14.14.mq5`; header, init banner, and
  `#property version` updated.

## Not addressed in this release
- Whether `0.3×ATR` is the right buffer *once properly gated* is a
  separate, legitimate tuning question — untested until this gate fix
  has live data behind it. Don't retune the buffer yet; see how the
  gate alone changes the MFE distribution first.
- v3.14.13's fixes (Fix 18/19/20) were still showing the pre-fix
  corruption signature in a 2026.09.07 trade — filenames on the
  uploaded CSVs still read `ASE_v3_14_12`, suggesting v3.14.13 may not
  actually be deployed. Confirm before drawing conclusions from any
  data collected before this is verified running.

## Validation
1. Compile; confirm the v3.14.14 init banner.
2. Confirm this build is the one actually attached to the live/demo
   chart (check `ASE_VERSION_TAG` in the Journal on init, or the
   `_CURRENT_` state-log filename it starts writing).
3. Over the next batch of trades, check whether `MFE_Pct` on winners
   still clusters tightly — if the 50-51% signature persists even with
   this gate in place, the buffer itself (not just the missing gate)
   needs attention next.
