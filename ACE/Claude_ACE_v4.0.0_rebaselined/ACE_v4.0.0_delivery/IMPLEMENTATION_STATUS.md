# ACE v4.0.0 — Implementation Status

The uploaded ACE v4.0.0 foundation was reworked in-place into the completed V4.0 adaptive architecture described by the updated plan.

## Operational model

`EVIDENCE` (default): V4 learns from observation #1 while V3 remains the live control path.

`ADVISORY`: V4 decision state is exposed without live authority.

`CONDITIONAL` / `ACTIVE`: V4 may take authority only after the adaptive validation gate is satisfied. The first executable class is Trend Continuation in TRENDING conditions. Risk, Discipline, Orchestrator, broker, spread, drift and fill protections remain mandatory.

## Adaptive progression

- Learning: immediate from first distinct setup occurrence.
- Cautious authority: configurable, default 20 observations.
- Controlled adaptation: configurable, default 50 observations.
- Validated authority: configurable, default 100 observations plus OOS/quality validation.
- Adaptation is bounded and cooldown-controlled.
- Shadow A/B policies are evaluated on the same opportunity stream.
- The adaptive model persists across terminal restarts through FILE_COMMON.

## Final verification

Source/static validation passed for:

- balanced braces/parentheses/brackets;
- local include graph;
- historical MQL5 anti-pattern checks;
- direct order-call authority isolation;
- legacy V3.14.17 hash preservation;
- ZIP integrity;
- one attribution export path per close record;
- V4 same-tick execution handoff wiring.

MetaEditor compilation and MT5 Strategy Tester execution are not claimed because no MT5 runtime is available in this environment.
