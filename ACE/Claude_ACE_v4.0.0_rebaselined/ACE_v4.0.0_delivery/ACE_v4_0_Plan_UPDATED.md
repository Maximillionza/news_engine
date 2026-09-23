# ACE v4.0 — High-Confluence Evolution Plan

## Purpose

This document defines the implementation and validation plan for evolving ACE v3.14.17 into ACE v4.0.

The objective is **not** to simply add more filters or make the EA trade less often. The objective is to make ACE better at identifying complete, repeatable market setup archetypes, measuring confluence quality, recognizing contradictions, and eventually executing only setup combinations that demonstrate a statistically defensible edge.

> **More intelligence must not automatically mean more restrictions.**

ACE v4.0 should become more sophisticated internally while initially preserving existing trade behavior. Only after sufficient data is collected should the new confluence logic be allowed to change execution.

---

# 1. Executive Summary

ACE v3.14.17 already contains substantial market-analysis engines:

- Regime
- H1 structure/BOS
- H4 context
- M15 FVG
- M15 displacement
- M15 compression
- M15 EMA pullback
- M1 displacement
- M1 micro BOS
- M1 rejection
- Liquidity pools
- Liquidity sweeps
- ATR/volatility
- Session
- Spread
- Risk
- Execution
- Trade management
- News/session protection

The principal architectural limitation is not a lack of signals. It is that many pieces of evidence are evaluated independently and can be collapsed into a single setup classification or weighted score.

The most important example is the current M15 Setup Engine:

1. Check FVG.
2. If FVG passes, return immediately.
3. Otherwise check displacement.
4. Otherwise compression.
5. Otherwise EMA pullback.

ACE can therefore observe several simultaneous pieces of evidence but retain only the first successful setup class.

ACE v4.0 should instead:

1. Evaluate all available evidence.
2. Preserve each evidence item independently.
3. Group evidence into independent families.
4. Determine direction.
5. Identify a setup archetype.
6. Validate the archetype's core requirements.
7. Apply enhancers.
8. Detect contradictions.
9. Apply freshness/decay.
10. Generate a setup signature (setup DNA).
11. Produce a quality grade.
12. Record the complete opportunity whether or not it trades.

This creates the progression:

**Signal detection → confluence recognition → setup classification → statistical validation → selective execution.**

---

# 2. Primary Objective

The primary objective of ACE v4.0 is:

> Identify high-quality, repeatable market setup classes without unnecessarily reducing opportunity frequency.

The EA should optimize for **quality of expectancy**, not simply trade frequency.

The target is not:

- maximum trades
- minimum trades
- maximum win rate
- maximum score
- maximum number of confirmations

The target is:

- positive expectancy
- robust profit factor
- sustainable trade frequency
- controlled drawdown
- good average R
- stable OOS performance
- low degradation from IS to OOS
- repeatability across market conditions
- explainable decisions

---

# 3. Current ACE Architecture

## 3.1 Existing State Flow

Current ACE follows a state-machine approach approximately equivalent to:

`IDLE → WAIT_HTF → WAIT_SETUP → WAIT_TRIGGER → WAIT_EXECUTION → MANAGE → COOLDOWN`

The architecture already separates major responsibilities.

Current engines include:

- State Machine
- Regime Engine
- Structure Engine
- Setup Engine
- Trigger Engine
- Liquidity Engine
- Scoring Engine
- Risk Engine
- Execution Engine
- Trade Manager
- Session Engine
- News Engine
- Validation
- Presentation

This architecture should be preserved. ACE v4.0 should extend it rather than unnecessarily rewrite it.

---

# 4. Core Design Principle

## 4.1 More Complexity Does Not Mean More Filters

A dangerous implementation would be:

`TRENDING AND H1 BOS AND FVG AND displacement AND liquidity AND sweep AND EMA alignment AND volume expansion AND session AND micro BOS AND H4 alignment`

This would almost certainly reduce trade frequency substantially.

ACE v4.0 should **not** work this way.

Evidence must instead be divided into:

### Core requirements

These define whether a setup archetype actually exists.

### Enhancers

These improve setup quality but do not define the setup itself.

### Environment/transaction conditions

These determine whether execution is sensible.

### Contradictions

These can invalidate a setup even if the raw score is high.

This creates a controlled decision hierarchy.

---

# 5. Evidence Families

Evidence should be grouped into independent families so redundant confirmations are not counted as independent proof.

## 5.1 Structure

Examples:

- H1 BOS
- BOS direction
- BOS strength
- structural continuation
- structural reversal
- H4 structural context

## 5.2 Location

Examples:

- M15 FVG
- EMA pullback
- structural zone
- previous swing
- retracement location

## 5.3 Liquidity

Examples:

- HTF liquidity pool
- equal highs/lows
- unmitigated swing liquidity
- liquidity sweep
- rejection from liquidity

## 5.4 Momentum

Examples:

- M15 displacement
- M1 displacement
- M1 micro BOS
- momentum persistence
- expansion

## 5.5 Environment

Examples:

- regime
- ATR state
- volatility expansion
- compression
- session quality
- macro context

## 5.6 Execution

Examples:

- spread
- trigger-to-fill drift
- execution shock
- broker conditions

---

# 6. Avoiding Redundant Confluence

Confluence must represent independent evidence.

For example:

`EMA21 slope + EMA21 distance + EMA21 alignment`

should not be treated as three independent confirmations. They are one evidence family: **EMA Pullback / Location**.

Likewise:

`M1 displacement + M1 body/range ratio + M1 candle body size`

are components of **M1 Momentum**, not three independent reasons to trade.

This prevents artificial score inflation.

---

# 7. ACE v4.0 Evidence Architecture

Create an evidence model capable of storing every detected condition.

Recommended conceptual object:

```text
SetupEvidence
{
    EvidenceType
    EvidenceFamily
    Direction
    Strength
    Quality
    Freshness
    Timestamp
    SourceTF
    PriceReference
    ValidUntil
    Active
}
```

Suggested evidence types:

```text
H1_BOS
H4_ALIGNMENT
M15_FVG
M15_DISPLACEMENT
M15_COMPRESSION
M15_EMA_PULLBACK
HTF_LIQUIDITY
MICRO_SWEEP
M1_REJECTION
M1_DISPLACEMENT
M1_MICRO_BOS
VOLATILITY_EXPANSION
SESSION_QUALITY
SPREAD_QUALITY
```

The implementation should use the project's established MQL5 types and naming conventions and avoid duplicating existing structures unnecessarily.

---

# 8. Replace "First Setup Wins"

The current Setup Engine should be refactored.

Current behavior:

```text
Evaluate FVG
    ↓
if valid → return

Evaluate Displacement
    ↓
if valid → return

Evaluate Compression
    ↓
if valid → return

Evaluate EMA Pullback
```

New behavior:

```text
Evaluate FVG
    ↓
store evidence

Evaluate Displacement
    ↓
store evidence

Evaluate Compression
    ↓
store evidence

Evaluate EMA Pullback
    ↓
store evidence

Return complete evidence set
```

This is one of the most important changes in ACE v4.0. It should initially have **zero intended effect on trade execution**.

---

# 9. Confluence Engine

Create:

`Core/ASE_ConfluenceEngine.mqh`

Responsibilities:

1. Receive evidence from existing engines.
2. Organize evidence by family.
3. Determine directional confluence.
4. Identify setup archetypes.
5. Validate setup core requirements.
6. Detect conflicts.
7. Apply freshness.
8. Calculate quality.
9. Produce setup signature.
10. Produce human-readable reasoning.
11. Return a complete confluence result.

The Confluence Engine must not execute trades.

It answers:

> "What setup is the market currently presenting, how strong is it, and is it structurally complete?"

---

# 10. Confluence Result

Recommended conceptual structure:

```text
ConfluenceResult
{
    qualified
    setupClass
    setupSignature
    direction

    longScore
    shortScore
    confidence

    coreStructure
    coreLocation
    coreLiquidity
    coreMomentum
    coreTrigger

    enhancers

    conflict
    conflictType

    freshness
    grade

    reason
}
```

Additional fields can be added as implementation requires.

---

# 11. Directional Confluence

ACE should not only calculate a total score. It should calculate:

`LongScore` and `ShortScore`

Then evaluate:

- WinningScore
- LoserScore
- ScoreSeparation

A trade should require both:

1. sufficient absolute directional strength
2. sufficient separation from the opposing direction

Example:

```text
Long = 86
Short = 42
Separation = 44
```

This is materially different from:

```text
Long = 86
Short = 79
Separation = 7
```

The second case represents a conflict-heavy environment even though the Long score is high.

---

# 12. Conflict Detection

Conflict detection is a first-class feature.

Example:

```text
H1 bullish BOS
+
M15 bullish location
+
M1 strong bearish structural break
```

This should not automatically trade simply because the bullish score is high.

Another example:

```text
H1 bullish
+
M15 bullish displacement
+
M1 strong bearish liquidity event
+
Bearish micro BOS
```

This may represent a temporary pullback, failed continuation, reversal, or incomplete setup.

The system should identify the contradiction rather than blindly average it away.

Recommended result:

`CONFLICT — Lower-TF structure contradicts continuation direction.`

---

# 13. Setup Archetypes

ACE v4.0 should classify market conditions into recognizable setup classes.

Initial proposed classes:

1. APEX Trend Continuation
2. APEX Liquidity Reversal
3. APEX Compression Expansion
4. APEX Pullback Continuation
5. APEX Structural Reversal

These are hypotheses that must be statistically validated; they are not guaranteed profitable setups.

---

# 14. APEX Trend Continuation

This should be the first production candidate.

## Core sequence

```text
TRENDING regime
    ↓
H1 BOS
    ↓
M15 valid location
    ↓
M15 momentum
    ↓
M1 confirmation
    ↓
ENTRY
```

Ideal example:

```text
H1 bullish BOS
→ M15 bullish FVG
→ M15 bullish displacement
→ liquidity remains supportive
→ M1 bullish displacement
→ M1 micro BOS
→ entry
```

Recommended core:

- TRENDING regime
- valid H1 BOS
- M15 location
- M15 momentum
- M1 confirmation

Liquidity should initially be treated as an important enhancer unless testing proves it must be core. This prevents unnecessary trade suppression.

---

# 15. APEX Liquidity Reversal

Conceptual sequence:

```text
HTF liquidity pool
→ liquidity sweep
→ rejection
→ structural change
→ M1 confirmation
```

Potential core:

- identifiable liquidity pool
- sweep
- rejection
- structural reversal evidence
- M1 confirmation

This setup should be tested independently from trend continuation.

---

# 16. APEX Compression Expansion

Conceptual sequence:

```text
Compression
→ ATR expansion
→ range breakout
→ structure confirmation
→ M15 displacement
→ M1 confirmation
```

Historical ACE testing showed poor compression-entry performance. Therefore this setup should initially remain **advisory/research-only**.

Do not automatically reactivate compression execution merely because it has been formalized as an archetype.

---

# 17. APEX Pullback Continuation

Conceptual sequence:

```text
H1 BOS
→ M15 pullback
→ FVG / EMA / structural location
→ M1 rejection or displacement
→ M1 micro BOS
```

This may overlap with Trend Continuation. The classifier therefore needs precedence rules.

A possible rule is:

- If M15 displacement is sufficiently strong and the market is actively expanding, classify as Trend Continuation.
- If the defining characteristic is pullback into location followed by lower-TF rejection, classify as Pullback Continuation.

This precedence must be tested.

---

# 18. APEX Structural Reversal

Conceptual sequence:

```text
Established H4 trend
→ H1 BOS against H4 direction
→ strong displacement
→ high-quality location
→ liquidity event
→ M1 confirmation
```

This is a higher-risk archetype and should initially require stronger evidence than normal continuation.

---

# 19. Setup Sequence Intelligence

Confluence should eventually care about **order**, not merely simultaneous conditions.

Example of a strong sequence:

```text
H1 BOS
→ M15 retracement
→ M15 FVG
→ M15 displacement
→ M1 confirmation
```

Example of a weak sequence:

```text
M1 spike
→ random FVG
→ late H1 BOS
```

Both might produce similar Boolean states at one moment, but they should not necessarily receive the same quality rating.

Create:

`Core/ASE_ConfluenceSequence.mqh`

The sequence engine should eventually record:

- event timestamp
- event order
- event age
- event relationship
- expected sequence
- actual sequence
- sequence completeness

---

# 20. Freshness and Confluence Decay

Evidence should not remain equally powerful forever.

Examples:

```text
Fresh FVG → Freshness 1.00
Older FVG → Freshness 0.55
Invalidated FVG → Freshness 0 / Active false
```

The same principle applies to:

- BOS
- liquidity
- displacement
- sweeps
- rejection
- triggers

This avoids trading on stale confluence.

---

# 21. Core Gates vs Enhancers

This is one of the most important design decisions.

## Core gates

If a core gate is missing:

`NO TRADE`

## Enhancers

If an enhancer is missing:

`TRADE MAY STILL BE VALID`

Example:

```text
TRENDING ✓
H1 BOS ✓
M15 FVG ✓
M15 displacement ✓
M1 Disp+mBOS ✓

Liquidity ✗
H4 alignment ✗
```

This could still qualify as an APEX setup if liquidity and H4 alignment are not core requirements. Missing enhancers reduce quality rather than invalidate the setup.

---

# 22. Proposed V4 Scoring Model

A proposed starting model:

## Structural — 25

- H1 BOS: 15
- H4 alignment: 5
- BOS quality: 5

## Location — 20

- FVG: 8
- EMA pullback: 5
- Structural zone: 7

## Liquidity — 20

- HTF liquidity: 8
- Sweep/rejection: 8
- Freshness: 4

## Momentum — 20

- M15 displacement: 8
- M1 displacement: 5
- M1 micro BOS: 7

## Environment — 10

- Regime: 5
- Volatility expansion: 3
- Session: 2

## Execution — 5

- Spread: 2
- Trigger-to-entry drift: 3

Total: **100**

This is a starting framework, not a permanent weighting. Weights must eventually be validated against data.

---

# 23. Do Not Let Score Rescue Missing Structure

A major design rule:

> **Score cannot compensate for a missing core requirement.**

Example:

```text
Score = 91
H1 BOS = missing
```

Result:

`FAIL`

Not:

`APEX+`

Likewise, a lower score with every core condition valid can still be a valid setup depending on the archetype and minimum grade.

This prevents score inflation.

---

# 24. Proposed Grades

Initial proposal:

```text
APEX+ = 90–100
APEX A = 80–89
APEX B = 70–79
C = advisory
FAIL = blocked
```

### APEX+

- core complete
- no conflict
- strong directional separation
- high-quality evidence
- fresh setup

### APEX A

- core complete
- no major conflict
- good confluence

### APEX B

- core complete
- weaker enhancer profile
- conditional execution depending on testing

### C

- interesting setup
- insufficient evidence for execution

### FAIL

- missing core
- severe conflict
- stale/invalid setup
- execution protection failure

---

# 25. Grade Policy

Preferred execution policy should initially be:

```text
APEX+ → Execute
APEX A → Execute
APEX B → Conditional / configurable
C → Advisory only
FAIL → Block
```

This policy should only be activated after validation. The architecture should support it before the policy becomes live.

---

# 26. Why Trade Frequency Should Not Collapse

The implementation should deliberately avoid unnecessary frequency reduction.

The first phase does not change trade decisions.

The second phase does not change execution.

Only the activation phase changes execution.

Therefore:

### Phase 1

Trade count: approximately current ACE.

### Phase 2

Trade count: approximately current ACE.

### Phase 3

Trade count: unknown until data validates which setup classes should execute.

This staged approach is critical.

---

# 27. Correct Optimization Target

Do not optimize solely for:

- trade count
- win rate
- score
- number of confirmations

Optimize for:

```text
Expectancy
+
Profit Factor
+
Average R
+
Drawdown
+
OOS stability
+
Trade frequency
+
Robustness
```

A lower-frequency strategy can be superior. A higher-win-rate strategy can also be inferior if it has poor R:R or large drawdowns.

---

# 28. Baseline Preservation

Before activating any new logic, capture the current ACE baseline.

Required baseline fields:

- Total trades
- Long trades
- Short trades
- Win rate
- Profit factor
- Net profit
- Average trade
- Average R
- Expectancy
- Maximum drawdown
- Sharpe ratio
- GHPR
- AHPR
- Average holding time
- TP1 rate
- TP2 rate
- SL rate
- MAE
- MFE
- Long expectancy
- Short expectancy
- Regime-specific performance
- Setup-specific performance
- Session-specific performance

This becomes the control group.

---

# 29. Opportunity Logging

ACE v4.0 should record opportunities even when no trade is taken.

This is essential.

Current trading-only statistics answer:

> What happened to trades we took?

They do not fully answer:

> What happened to setups we rejected?

V4 should log:

```text
Opportunity detected
→ setup class
→ direction
→ evidence
→ score
→ grade
→ core status
→ conflict
→ block reason
→ theoretical entry
→ theoretical SL
→ theoretical TP
→ subsequent outcome
```

This allows analysis of false negatives, false positives, over-filtering and under-filtering.

---

# 30. Attribution Engine

Create:

`Core/ASE_SetupAnalytics.mqh`

Every opportunity should have an attribution result.