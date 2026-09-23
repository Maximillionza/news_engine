# DNA/Regime Combo Tracking — TrendContinuation-shape-in-Manipulation

Tracking whether ACE v4.0.1's classifier keeps seeing TrendContinuation's
4-of-5 evidence signature (H1_BOS, M15_FVG, M15_DISPLACEMENT, M1_DISPLACEMENT)
fire while regime is tagged MANIPULATION instead of TRENDING — the only
missing core item is the regime gate itself (see ASE_SetupClassifier.mqh:46).

Because the regime gate is hard-coded as a core requirement, these setups
always classify ARCH_NONE and never enter the adaptive engine's LIVE bucket,
so nothing will ever "learn" this pattern on its own. This file is the
manual substitute — a running count so a real decision (loosen the regime
gate vs. leave it) is based on more than one trade.

## Exact DNA watched
`NONE-S-HBOS-H4AL-FVG-DISP-KZ-LP-M1D-M1E-ULIQ` (and directional/tag variants —
see broader pattern below)

## Broader pattern watched
Any opportunities.csv row where:
- Regime = Manipulation
- BlockReason contains "closest: TrendContinuation"
- CoreMet/CoreTotal = 4/5

## Log

| Checked (local time) | Source file | Exact-DNA samples | Broader-pattern count (today's file) | Notes |
|---|---|---|---|---|
| 2026-09-23 ~16:30 SAST (baseline) | ASE_v4.0.1_GOLD_v4state2.csv | 1 | 1 (the 16:04:00 row) | First occurrence, trade still open. Baseline set here. |
