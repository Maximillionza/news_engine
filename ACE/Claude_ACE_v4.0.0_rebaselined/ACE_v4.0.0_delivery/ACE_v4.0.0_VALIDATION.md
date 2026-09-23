# ACE v4.0.0 — Final Build Validation

Date: 2026-09-16
Base package: Claude_ACE_v4.0.0.zip
Plan checked: ACE_v4_0_Plan_UPDATED.md + adaptive design requirements through §82/§84

## Final status

SOURCE-LEVEL COMPLETION: PASS
PACKAGE COMPLETENESS: PASS
ARCHITECTURAL AUTHORITY SEPARATION: PASS
MT5 COMPILE: NOT EXECUTED (MT5/MetaEditor runtime unavailable)
STRATEGY TESTER: NOT EXECUTED (MT5 runtime unavailable)

The build was iterated after the first gap review. The final package below is the result of the second validation pass; missing architectural items identified during that pass were implemented before packaging.

## Plan-to-build matrix

| Plan area | Final implementation | Status |
|---|---|---|
| Evidence refactor | Existing Setup/Trigger engines expose additive all-evidence collection; legacy Evaluate paths retained | COMPLETE |
| All setup evaluation | M15 FVG, displacement, compression, EMA pullback and M1 trigger evidence are collected independently | COMPLETE |
| Opposing evidence | Opposite M1 and liquidity evidence is collected for contradiction detection | COMPLETE |
| Confluence | Directional scores, separation, family caps, core/enhancer result, conflict and freshness | COMPLETE |
| Setup classifier | Trend, Liquidity Reversal, Compression Expansion, Pullback Continuation, Structural Reversal, NO_CLASS | COMPLETE |
| Sequence intelligence | Timestamp ordering, inversions, completeness, event age and quality | COMPLETE |
| Freshness/decay | Timeframe-aware freshness and decay applied to confluence contribution; stale setup rejection | COMPLETE |
| Core vs enhancer | Missing core cannot be rescued by score; enhancers affect quality only | COMPLETE |
| Grades | APEX+, APEX A, APEX B, C, FAIL | COMPLETE |
| Separation | Minimum directional separation configurable independently of absolute score | COMPLETE |
| Setup DNA | Deterministic archetype/direction/evidence signature | COMPLETE |
| Opportunity logging | Distinct occurrence logging including blocked opportunities | COMPLETE |
| Theoretical outcomes | Pending SL/TP tracking, expiry, same-bar ambiguity protection | COMPLETE |
| Actual attribution | Opportunity ID linked into trade records and actual R outcome feedback | COMPLETE |
| Regime hierarchy | Global + regime + archetype + archetype/direction + DNA analytics | COMPLETE |
| Learning clock | Starts at observation #1; distinct DNA occurrence prevents tick inflation | COMPLETE |
| Adaptation clock | Cooldown + learning rate + bounded threshold adaptation | COMPLETE |
| Authority clock | Observe → cautious → controlled → validated tiers | COMPLETE |
| Bounded adaptation | Threshold range, step/learning rate, sample and validation requirements | COMPLETE |
| Shadow models | Shadow A and Shadow B candidate policies evaluated on the same opportunity stream | COMPLETE |
| Shadow outcomes | Candidate pending records resolve from subsequent price movement | COMPLETE |
| OOS | Explicit configurable OOS start date | COMPLETE |
| Validation | Recent, long-term, OOS retention, regime coverage, drawdown and split-sample stability | COMPLETE |
| Execution separation | Confluence/classification/adaptation never call order functions | COMPLETE |
| Decision layer | V4 qualification remains separate from execution timing | COMPLETE |
| Discipline | Session, news and spread safety wrapper | COMPLETE |
| Orchestrator | Position/cluster portfolio risk wrapper | COMPLETE |
| Risk | Existing RiskEngine remains the position sizing/SL/TP authority | COMPLETE |
| Execution | Existing ExecutionEngine remains the only order-send authority | COMPLETE |
| Same-tick processing | V4 M1 evidence can hand off directly to ProcessExecution on the same tick in authoritative modes | COMPLETE |
| Legacy preservation | ACE_v3.14.17.mq5 retained as control group | COMPLETE |
| Persistence | Analytics, adaptive state and pending records persisted to FILE_COMMON | COMPLETE |
| Latency | Existing execution latency telemetry retained and linked to attribution | COMPLETE |
| Trade frequency protection | Observation/advisory modes leave legacy execution path intact | COMPLETE |
| Compression policy | Formalized archetype remains non-authoritative; only Trend Continuation can be activated by V4 | COMPLETE |
| Setup-specific risk | Architecture remains conservative; adaptive SL/TP is not freely modified before evidence validates it | COMPLETE |

## Execution authority

### Default: ACEV4_EVIDENCE

V4 sees, classifies, logs, learns and evaluates shadow candidates. Legacy execution remains in control.

### ACEV4_ADVISORY

V4 remains non-authoritative and is intended for observation/diagnostics.

### ACEV4_CONDITIONAL / ACEV4_ACTIVE

V4 may become authoritative only when the adaptive validation gates are satisfied. The first executable archetype is Trend Continuation in a TRENDING regime. Risk, Discipline, Orchestrator, spread, drift, broker and execution protections remain mandatory.

## Adaptive validation gate

A Trend Continuation model must accumulate the configured validated-tier observations and satisfy:

- sufficient overall observations;
- sufficient recent outcomes with positive R;
- positive long-term average R;
- sufficient OOS observations;
- positive OOS average R;
- minimum OOS retention relative to overall average R;
- coverage across multiple regimes;
- bounded model drawdown in R;
- positive performance in both early and later sample partitions.

This prevents the EA from turning a small early streak into execution authority.

## Same-tick execution flow

```text
Current tick
  ↓
M1 evidence refresh
  ↓
Confluence
  ↓
Sequence + freshness
  ↓
Classifier
  ↓
Adaptive authority
  ↓
Discipline
  ↓
Orchestrator
  ↓
RiskEngine
  ↓
ExecutionEngine
  ↓
Broker fill
```

No fixed M1-bar wait is intentionally introduced in the V4 authoritative path.

## Validation limitations

This environment does not contain MetaEditor or an MT5 Strategy Tester runtime. Consequently, this report does not claim a compiled `.ex5`, broker-specific execution success, or backtest performance. Those are the remaining external validation steps once the package is opened in MT5.

## Package acceptance

The package is considered complete at the source/architecture level. No known V4 architectural gap from the reviewed plan was intentionally left as a stub or reserved future build dependency. Future versions should therefore be evidence-driven improvements rather than unfinished V4 architecture work.
