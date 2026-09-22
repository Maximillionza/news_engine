# ACE v4.0.0 — Build Notes

## What this delivery is

Everything in ACE_v4_0_Plan_UPDATED.md Phases 1-4 (evidence architecture,
Confluence Engine, Setup Classifier, opportunity/DNA logging) plus the
revised §82 adaptive-learning design from the follow-up chat: graduated
authority tiers (Level 1 priority / Level 2 bounded threshold / Level 3
setup activation / Level 4 model promotion), starting to learn from
opportunity #1, with Level 3/4 declared but structurally inert.

Delivered as one pass, not phased — per your instruction. Nothing here
requires a second build session to be "complete" as code; what it
cannot do yet is validate itself, because that needs data this build
hasn't generated yet (see "What is NOT in this delivery" below).

## Files changed

**New:**
- `Models/ASE_EvidenceTypes.mqh` — evidence type/family enums, `SetupEvidence`, `SetupEvidenceSet`
- `Models/ASE_ConfluenceTypes.mqh` — archetype/grade enums, `ConfluenceResult`, setup DNA builder
- `Models/ASE_AdaptiveTypes.mqh` — `LearningStatsBucket/Table`, `AdaptationBox`, `ShadowModelState`
- `Core/ASE_SetupEvidenceCollector.mqh` — wraps existing engines into one evidence set per bar
- `Core/ASE_ConfluenceEngine.mqh` — directional scoring, separation, conflict detection
- `Core/ASE_SetupClassifier.mqh` — 5 APEX archetypes + NO_CLASS, grading
- `Core/ASE_SetupAnalytics.mqh` — opportunity CSV log, learning stats, theoretical-outcome resolver, adaptation-box wiring
- `ACE_v4.0.0.mq5` — new main file; `ACE_v3.14.17.mq5` kept unmodified as the baseline-preservation control group (plan §28)

**Modified (additive only — see inline comments at each change):**
- `Core/ASE_SetupEngine.mqh` — added `EvaluateAllEvidence()`. Calls the same four private `Check*` methods `Evaluate()` already calls; `Evaluate()` itself has zero lines changed.
- `Core/ASE_TriggerEngine.mqh` — added `EvaluateAllEvidence()`. Deliberately RE-COMPUTES its conditions independently rather than refactoring `Evaluate()` into shared helpers, trading a small amount of duplicated arithmetic for a hard guarantee that the method actually gating live orders is untouched.
- `Core/ASE_StateMachine.mqh` — new member engines, two `Initialize`/`Deinitialize` hooks, and three call sites (`ProcessSetup()`: M15 evidence + theoretical-outcome resolution; `ProcessTrigger()`: M1 evidence + confluence + classify + log). Every new call site is gated behind `InpAceV4Mode >= ACEV4_EVIDENCE`; none replace or reorder an existing line.
- `Models/ASE_Config.mqh` — `ASE_VERSION_TAG` bumped to `ASE_v4.0.0`; added `InpAceV4Mode` and the four `InpAceV4*` tuning inputs.

## Two risks found and fixed during implementation (not in the original plan)

1. **`ASE_TriggerEngine.mqh` has the same first-match-wins cascade as the M15 Setup Engine.** The plan document names only the M15 Setup Engine; the M1 Trigger Engine's `longDisplace`/`microBOSLong`/`longRejection`/`emaLongAligned` are local variables with the identical discard-on-first-match problem. Fixed the same way — additive `EvaluateAllEvidence()`, legacy `Evaluate()` untouched.
2. **The evidence collector originally called `m_structure.Evaluate()` and `m_liq.DetectSweep()` a second time per bar.** Both have side effects (`m_structure.Evaluate()` mutates `m_h4ClosedDir` and pivot-registry state; `DetectSweep()` mutates `m_lastLiqType` and does a real buffer scan with its own `Print()` calls). Fixed: H1 BOS evidence now reads already-resolved state (`m_ctx.scoreCard.h4Bias`, `GetLastStructure()`) instead of re-scanning; the liquidity/M1 collection pass is throttled to once per M1 bar close instead of every tick, matching the cadence the legacy path already uses that exact scan at.

## Follow-up fixes (same delivery, before first compile)

Six more issues found by tracing actual runtime behavior rather than re-reading the design — the first was flagged proactively, the other five were found on request when asked to check for anything else of the same kind:

1. **No persistence.** Every learning table, adaptation box, and the pending-theoretical queue lived only in `CASE_SetupAnalytics`'s in-memory members. Any terminal restart (not just a network drop — process lifetime, not clock time) silently zeroed every counter, defeating a tier system built specifically to reward accumulated evidence. Fixed: `SaveState()`/`LoadState()` to a `FILE_COMMON` CSV (`<VERSION_TAG>_<SYMBOL>_v4state.csv`), called from `Deinitialize()`/`Initialize()`.
2. **Adaptation boxes never moved.** `Nudge()` existed; nothing ever called it. `RecomputeAdaptation()` now runs two bounded hypotheses on every genuinely new opportunity (see #4): Level 1 nudges an archetype's priority box toward whichever side of a blended real+theoretical R comparison against GLOBAL wins; Level 2 nudges the liquidity-evidence weight toward whichever side of a DNA-tag split (setups whose DNA contains `ULIQ` vs not) wins. Both require a minimum sample per side (5) and a minimum edge (0.10R) before moving at all.
3. **Authority was gated globally, not per setup class.** `ArchTier(archName)` now reads that archetype's own bucket observation count; the liquidity-weight box (a GLOBAL-scoped parameter — it affects every archetype's scoring, not one) correctly still uses the GLOBAL tier.
4. **Opportunities were counted once per M1 bar, not once per distinct setup.** A signal sitting qualified-but-blocked for 8 consecutive bars was 8 observations of one setup, inflating its tier faster than a short-lived one regardless of which was actually stronger — and flooding the opportunity CSV and the 40-slot pending buffer with near-duplicate rows. Fixed with an edge-detection dedup cursor (`m_lastDNA`): only a bar whose setup DNA differs from the immediately prior bar's counts as new.
5. **Classifier evidence checks didn't filter by direction.** Harmless today (one evidence set only ever holds one direction), but every core check was relying on that invariant rather than checking it, and `SetupEvidence.direction` existing as a field says this was meant to be checked. Added a direction-aware `HasActive(type, dir)` overload; every core check in `ASE_SetupClassifier.mqh` now uses it.
6. **Theoretical-outcome tracking wasn't gated on core-complete.** Every non-executed opportunity was registered for forward resolution, including ones that never had a real chance (`ARCH_NONE`, missing core evidence) — diluting the "what would ACE have done if it hadn't blocked this" signal the feature exists to surface, and adding to the same buffer pressure as #4. Now gated on `archetype != ARCH_NONE && coreMet == coreTotal`.

One more, caught mid-implementation and not listed above because it never reached a save point: the evidence collector's first draft called `m_structure.Evaluate()` and `m_liq.DetectSweep()` a second time per bar to gather evidence for the v4 pipeline — both mutate internal engine state as a side effect, and `DetectSweep()` does a real buffer scan with its own `Print()` calls that would have run on every tick instead of only when the legacy path actually needs it. Fixed before it was ever written to a file — H1 BOS evidence now reads already-resolved state instead of re-scanning, and the liquidity/M1 pass is throttled to once per M1 bar close.



- **Execution authority.** No archetype, grade, or confluence score is read by `OrderSend` or any legacy `Inp*` parameter at any `InpAceV4Mode` value this build reaches. That is Phase 5+ in the plan, gated on backtest/OOS evidence this build will start generating but cannot itself supply.
- **Shadow-model validation.** `ShadowModelState.eligibleForPromotion()` requires six checks plus a 100-sample minimum; nothing in this codebase sets any of the six true. Declared, not functional — by design, since there is no accumulated history to validate against yet.
- **Cross-bar freshness decay (plan §20).** Evidence is recomputed fresh every bar rather than aged/carried-forward; `SetupEvidence.freshnessBars` is always 0 in this delivery. The averaging logic is wired so a future pass only needs to populate that field correctly.
- **Full sequence intelligence (plan §19).** Event-order/timing tracking (`ASE_ConfluenceSequence.mqh` in the plan's file list) was not built — freshness/decay is the scoped-down substitute this delivery ships instead.
- **Trade-to-opportunity linking.** Every v4 opportunity row logs `executed=NO`; on the rare bar the legacy path does open a real trade for the same setup, that trade's actual outcome is recorded by the existing `CASE_TradeAttribution` path exactly as before, but is not cross-referenced back to its v4 opportunity row. The theoretical-outcome resolver still runs for that row regardless, so it will show an approximate (not exact) R for it.
- **Structural-zone and trigger-to-entry-drift evidence** (plan §22) have no existing detector in the codebase; the Confluence Engine's weight table folds their points onto the nearest existing evidence type rather than fabricating a detector — see the comment block at the top of `ASE_ConfluenceEngine.mqh`.

## How to verify before trusting any of this

1. Compile both `ACE_v3.14.17.mq5` and `ACE_v4.0.0.mq5` with `InpAceV4Mode=ACEV4_LEGACY` on v4.0.0 — a byte-identical backtest between the two on the same data is the parity check plan §56 calls for. **I could not run this myself — no MQL5 compiler in this environment.**
2. Re-run with `InpAceV4Mode=ACEV4_EVIDENCE` (the default) on the same data — trade log should be identical to step 1; the new `*_opportunities_*.csv` file is the only new output.
3. Only after (1) and (2) confirm zero behavioural drift is the opportunity log itself worth reading for real analysis.

## Final V4.0 completion pass — 2026-09-16

This completion pass closes the architecture gaps identified against `ACE_v4_0_Plan_UPDATED.md`.

### Completed
- Live M1/tick-sensitive V4 evidence refresh in authoritative modes.
- Opposing M1/liquidity evidence collection for first-class conflict detection.
- Event timestamps and timeframe-aware evidence freshness/decay.
- Sequence intelligence: event order, inversions, age, coherence and quality.
- Family-capped directional confluence to reduce correlated evidence double-counting.
- Directional separation gate and score-vs-core separation.
- Five archetypes plus NO_CLASS retained.
- Regime bucket added to learning hierarchy: Global → Regime → Archetype → Direction → DNA.
- Distinct setup occurrence learning clock (persistent ticks do not inflate samples).
- Bounded adaptation clock with cooldown, learning-rate and parameter bounds.
- Authority tiers 0/20/50/100+ observations retained and wired.
- Shadow candidate policies A/B with same-opportunity evaluation and theoretical resolution.
- OOS split support via configurable `InpAceV4OOSStartDate`.
- Multi-condition model validation: recent, long-term, OOS retention, regime coverage, drawdown and split-sample stability.
- Opportunity → execution attribution and actual trade outcome feedback.
- Actual realized P/L converted to R using symbol tick value/tick size where available.
- Theoretical same-bar SL/TP ambiguity no longer invents a win/loss.
- Discipline and Orchestrator boundaries added as explicit V4 handoff layers.
- V4 Conditional/Active execution path added; it can only activate validated Trend Continuation.
- Legacy V3.14.17 path preserved as the baseline/control group.
- V4 trade attribution fields added to CSV/NDJSON/pipe outputs.
- Adaptive state and pending shadow/theoretical state persisted in `FILE_COMMON`.

### Authority model
`EVIDENCE` remains the default. V4 learns immediately but does not alter live execution until the configured validation requirements are met. `CONDITIONAL`/`ACTIVE` modes are capability switches, not bypasses: Risk, Discipline, Orchestrator, broker, spread, drift and execution protections remain mandatory.

### Validation performed in this environment
- Archive extracted and source inventory checked.
- Include graph checked for project-local files.
- Brace/parenthesis/bracket balance checked across all `.mq5`/`.mqh` sources.
- Known prohibited MQL5 patterns checked: no `PositionSelectByIndex`, no `OBJPROP_TRANSPARENCY`, no global Bid/Ask use, no StringToUpper/Lower ref misuse.
- V4 confluence/analytics/adaptive modules checked for direct order-send calls: none; only ExecutionEngine sends orders.
- V4 module execution boundaries inspected.
- Package integrity checked after rebuild.

### MT5-only validation still required
MetaEditor compilation and Strategy Tester runs cannot be executed in this environment because an MT5/MetaEditor runtime is not available. The package is therefore not represented as having a broker/tester-verified compile or performance result.

---

## Addendum — rebaselined on the "COMPLETE" build, fixes applied

This file now describes a different architecture than the section above,
which is stale as of this addendum: **"Level 3/4 declared but structurally
inert" is no longer true.** At the user's explicit direction, this delivery
is now baselined on a substantially expanded build (external origin, not
authored by Claude) which wires real execution authority, a richer
per-archetype adaptive engine (OOS tracking, drawdown, regime coverage,
stability, cooldown/learning-rate), genuine trade-outcome-to-opportunity
attribution, and a real sequence/freshness layer. That is a materially
different risk profile from the original delivery and should be read as
such — see the authority-gating description below before changing
`InpAceV4Mode` on a live account.

### What changed in this pass

**Fixed — evidence duplication / score inflation (found during this pass,
not by the external assessment that prompted the rebaseline):**
`CollectM1Context()` was being called every tick (for genuine same-tick
responsiveness) but `SetupEvidenceSet::Add()` only ever appends — nothing
cleared the previous tick's M1-scoped items first. Two consequences: (1)
`ConfluenceEngine::Evaluate()` sums weight per matching *active* item, so a
duplicated active evidence type was double-counted in the score every tick
it survived — a real scoring-correctness bug, not a cosmetic one; (2) with
`ASE_MAX_EVIDENCE=24` and ~12 M1-scoped items added per tick, the buffer
filled after roughly 2 ticks, after which `Add()` silently started
returning false and M1 evidence effectively froze for the rest of the M15
bar — the opposite of the same-tick goal this was built for. Fixed with
`SetupEvidenceSet::RemoveTypes()`: `CollectM1Context()` now clears its own
evidence types before re-adding them each tick (replace, not append); the
once-per-bar M15/H1/H4 items from `CollectM15Context()` are unaffected.

**Fixed — reintroduced, doubled log/CPU flood:** the M1-bar throttle
around `DetectSweep()` (added earlier in this project specifically because
that method does a real ~34-bar scan with its own `Print()` calls) had been
removed, and the call itself doubled (now once per direction, both
directions, every tick). Fixed by throttling only the `DetectSweep()` calls
to once per M1 bar close (cached and reused on ticks within the same bar);
the cheap, side-effect-free `trigger.EvaluateAllEvidence()` calls stay
per-tick, so genuine same-tick M1 displacement/microBOS/rejection
responsiveness is preserved — only the expensive, low-frequency-relevant
liquidity scan is bounded.

**Checked, not a bug (retracting a concern raised before this pass):**
whether `m_v4LastConfluence` could go stale between trade open and close,
misattributing a real outcome to whatever archetype happened to be most
recently evaluated rather than the one active at entry. Traced the state
machine: `ProcessTrigger()` — the only place that overwrites
`m_v4LastConfluence` — runs exclusively in `STATE_WAIT_TRIGGER`, and the
state machine leaves that state the moment a position opens
(`STATE_POSITION_OPEN` → `STATE_MANAGE`), not returning to
`STATE_WAIT_TRIGGER` until the position closes. So `m_v4LastConfluence`
correctly freezes at entry-time values for the duration of the trade.
Attribution is sound as designed.

**Not independently re-verified this pass:** the external assessment's
claims of "regime-specific learning missing" and "cooldowns/learning-rate
controls missing" do not match what's actually in this codebase —
`AdaptivePolicyState.regimeSamples[5]` is incremented per observation in
`Observe()`, and `InpAceV4AdaptCooldownObs`/`InpAceV4AdaptLearningRate`
gate every threshold nudge. Either the assessment was written against an
earlier draft, or it's simply inaccurate on these two points — flagging so
neither gets "fixed" a second time under the belief it's still missing.

### What this means for `InpAceV4Mode`

Default remains `ACEV4_EVIDENCE` (1) — unchanged behaviour unless you
deliberately raise it. `ACEV4_CONDITIONAL`/`ACEV4_ACTIVE` are now REAL, not
declared-and-inert: `CanActivate()` requires `TrendContinuation` specifically,
`REGIME_TRENDING`, `samples >= InpAceV4AuthValidatedMin`, and
`m_live[i].validated` — which itself requires positive recent AND long-term
AND OOS-retained R, drawdown under 20R, and stability across both sample
halves. That is a real, non-trivial gate, not a rubber stamp — but it has
never fired once, on any data, because nothing has been backtested yet.
Do not raise `InpAceV4Mode` above `ACEV4_EVIDENCE` on a live account before
that validation gate has been exercised against real history and you've
reviewed what it actually promoted and why.

---

## Addendum 2 — M15 restriction + pre-position context persistence

**M15 restriction.** MQL5 gives an EA no way to veto a chart period change
before `OnDeinit`/`OnInit` fire for it — confirmed by checking that every
data call in this codebase already uses an explicit `PERIOD_M15`/`M1`/`H1`/
`H4`, never `_Period`/`PERIOD_CURRENT`, for anything that drives a decision
(the only three `PERIOD_CURRENT` uses found were a default evidence tag,
two more of the same, and a log-message throttle — none touch trading
logic). So the EA's behaviour was already timeframe-agnostic; this only
stops an operator from running it on a chart that doesn't match what it's
trading. `OnInit()` now checks `_Period`; if it isn't M15 (and this isn't
the Strategy Tester, where there's no chart to correct — that case fails
init with a message to fix the tester's period setting instead), it calls
`ChartSetSymbolPeriod()` to snap back to M15 and returns without running
real initialization, since that pass is about to be torn down again
anyway. A `g_fullyInitialized` guard stops `OnDeinit` from calling
`Deinitialize()` on an instance that never ran `Initialize()`.

**Context persistence.** `CASE_StateMachine::SaveContextSnapshot()`/
`RestoreContextSnapshot()`, called from `Deinitialize(reason)`/
`Initialize(deinitReason)`. Saves `m_state` + the full `ASE_PipelineContext`
(direction, scorecard, regime snapshot, structural levels, session/
liquidity/setup-class strings) to `FILE_COMMON` whenever the EA is in
`STATE_WAIT_HTF`, `STATE_WAIT_SETUP`, or `STATE_WAIT_TRIGGER` at
deinit — explicitly writing an empty marker otherwise, so a later restart
from `STATE_IDLE` can't accidentally resurrect a stale in-progress setup
from several trades ago. Restored only when both hold: the deinit reason
was `REASON_CHARTCHANGE`/`REASON_PARAMETERS`/`REASON_RECOMPILE` (a same-
session, automatic reinit — a real restart, template load, or account
switch falls through to today's clean-slate behaviour, deliberately), and
the current M15 bar timestamp matches the one saved at snapshot time (a
same-session bounce lands on the same bar essentially always; if it
doesn't, the snapshot is treated as stale rather than resumed).

Deliberately not covered: `STATE_WAIT_EXECUTION` (an order actively being
placed — too narrow a window to safely resume, falls back to
re-evaluation) and `STATE_POSITION_OPEN`/`STATE_MANAGE` (already recovered
via the existing broker-side magic-number scan on every `Initialize()` —
restoring `m_ctx` for these too would be redundant).

**Known residual gap, stated rather than left implicit:** several
`Process*()` methods gate on function-local `static` bar-throttle
variables (e.g. the M15 heartbeat print stamp), which MQL5 resets on any
reinit regardless of whether this restore fires — this snapshot can't
reach into another method's local statics. Worst case on a restored bar,
one `Process*()` call fires an extra time on a bar it already ran on this
cycle — re-evaluates current data, not destructive, at most a duplicate
log line.

---

## Addendum 3 — H1_BOS never fired (found from the uploaded state files)

Your three uploaded files showed something worth taking seriously: 44
distinct setup occurrences logged, every single one classified `NoClass`,
zero samples reaching the adaptive engine for any of the five archetypes.
That's not "not enough data yet" — 44 is a real sample, and 0/44 landing
on a real archetype pointed at something structural, not chance.

Traced it: `EVID_H1_BOS` — a required core condition for 4 of the 5
archetypes — was checking `structure.GetLastStructure() == STRUCT_BOS`.
`GetLastStructure()` reads `m_lastBOS`, a field that is declared and
initialized to `STRUCT_NONE` in `ASE_StructureEngine`'s constructor and
then **never assigned again anywhere in the file**. Every fresh H1 BOS
correctly updates `m_h1BiasCurrent`, `m_h1SwingHigh`/`Low`, `m_lastBOSTime`,
and several other fields — just not `m_lastBOS`. The check was reading a
field that always held its constructor default, so it was always false,
regardless of what H1 structure actually did. This was my fix, from
earlier in this conversation (replacing a riskier double-`Evaluate()` call)
— I verified it had no side effects, but never verified `m_lastBOS` was
actually a live signal. It wasn't.

Fixed to `structure.GetH1BiasCurrent() == direction` — the field
`Evaluate()` genuinely maintains (set when a fresh BOS updates the bias,
cleared on invalidation), already has a public, side-effect-free getter,
and is the field three other places in the same file already trust for
the current confirmed H1 direction.

Given the DNA data in your upload — most rows already carry `H4AL`
(H4 alignment) and `DISP` (M15 displacement) — this fix should materially
change the archetype-classification rate going forward, not just the
odd edge case. Re-running with the same evidence pattern should now
produce real `TrendContinuation`/`PullbackContinuation` classifications
instead of `NoClass` for a large share of what was previously falling
through.

`EVID_M15_COMPRESSION` also never appeared in your DNA data. Checked the
call path (`setup.EvaluateAllEvidence()` → the real, unmodified
`CheckCompression()`) and found no equivalent dead-field issue — this one
looks like it's just a narrower, more infrequent condition by design, not
a bug. Flagging as something to watch once more data comes in rather than
claiming it's fine on zero contrary evidence.

---

## Addendum 4 — two zero-weight evidence types promoted to scored

Both `EVID_M15_COMPRESSION` and `EVID_M1_EMA_ALIGN` were collected,
DNA-tagged, and passed through to the classifier as enhancer evidence
since the original delivery, but contributed `0.0` to `ConfluenceEngine`'s
directional score — collected for logging/DNA value only, never actually
scored. Promoted both to a small nominal weight (`EVID_M15_COMPRESSION`
3.0, `EVID_M1_EMA_ALIGN` 2.0) in `ASE_ConfluenceEngine::WeightOf()`.

**These are interim numbers, not evidence-derived ones.** There is no
observation history yet to justify a specific figure for either — the
values chosen are in line with the other minor enhancer weights already
in the table (session quality 2.0, H4 alignment 5.0) rather than a
measured result. Revisit both once enough distinct-DNA observations
accumulate under the new weights to check whether they're pulling their
weight (pun intended) or should move.

**Found while in this file, fixed as a drive-by (not the task, but
directly adjacent and misleading to leave):** the file-header comment
claimed the weight table is "summed at runtime... so the normalisation is
always correct." False — `TotalWeight()` is dead code, never called from
anywhere; `Evaluate()` normalises `longRaw`/`shortRaw` against a hardcoded
`100.0`. The nominal total (93 before this change, 98 after) is therefore
always an approximation against a fixed denominator, not an exact sum.
Comment corrected to say so; `TotalWeight()` itself left in place, not
deleted — whether to wire it in or remove it is a separate decision, not
made here.

**Deliberately NOT done as part of this change: no `ASE_VERSION_TAG` or
`InpMagicNumber` bump**, despite the standing per-delivery convention.
`CASE_SetupAnalytics::Initialize(versionTag)` derives the FILE_COMMON
learning-state path directly from `ASE_VERSION_TAG`
(`ASE_StateLogs\%s_%s_v4state2.csv`) — V3 and V4 share the same
`ASE_Config.mqh`, the same tag, and the same magic number. Bumping either
would have orphaned every GLOBAL/ARCH/ARCHDIR/REGIME/DNA learning bucket
accumulated so far, not just fragmented the DNA-level rows the way adding
a genuinely new evidence type does. If a version cut is wanted here, it
should be a deliberate choice to reset the learning stage, not a
side-effect of following the versioning convention on a change intended
to be additive.

**Not done in this pass (separate, larger work, explicitly deferred):**
Order Block detector, kill-zone/AMD-phase timing evidence, DXY/real-yield
correlation evidence, liquidity-pool (equal highs/lows, PDH/PDL) mapping
beyond the existing binary sweep detector. Each needs a new
`ENUM_EVIDENCE_TYPE`, detector logic, DNA tag, and classifier
core/enhancer wiring — out of scope for what fit in this session's
remaining usage window.

---

## Addendum 5 — forked as ACE_v4.0.1, deployed side by side with v4.0.0

The Addendum 4 change (above) ships as a new main file, `ACE_v4.0.1.mq5`,
run **alongside** `ACE_v4.0.0.mq5` rather than replacing it — per explicit
instruction, to compare the two directly rather than overwrite the
control. That changes the versioning/isolation requirements from a normal
sequential release:

**`ASE_VERSION_TAG` and `InpMagicNumber` both diverge from v4.0.0.**
`ASE_VERSION_TAG`: `"ASE_v4.0.0"` → `"ASE_v4.0.1"`. `InpMagicNumber`
default: `203157` → `204001`. Both matter independently:
- `ASE_VERSION_TAG` drives every output filename — `SetupAnalytics`
  learning state, opportunity CSVs, context snapshot, trade CSV, HTML
  report, and `TradeAttribution`'s CSV/NDJSON/pipe outputs all derive
  their filename from it. Sharing it between two simultaneously-running
  builds means both silently write into the same files — this is not a
  hypothetical: see the Fix 16 note earlier in this changelog for a
  confirmed real incident of exactly that (v3.14.10 and ACE Global v1.0.0,
  same symbol, same terminal, one shared CSV, contaminated data).
- `InpMagicNumber` is what every position-management call site
  (`PartialTP`, `TradeManager`, `ATRTrailEngine`,
  `PositionClusterProtection`, the close-history scan in `StateMachine`)
  filters on to decide which live positions are "mine." Two builds
  sharing a magic number would each manage the other's trades — a live-
  account risk, not just a bookkeeping one.

**Mechanism — `Models/ASE_Config.mqh` is shared `#include` source between
both mains, so neither value could just be edited in place** (that would
silently retag v4.0.0 on its next recompile too, the same failure mode
being fixed, one step earlier). Both are now defined via an
override-before-include macro pattern:
- `ASE_VERSION_TAG`: `Models/ASE_Config.mqh` now wraps its definition in
  `#ifndef ASE_VERSION_TAG` / `#endif`, defaulting to `"ASE_v4.0.0"`.
  `ACE_v4.0.1.mq5` `#define`s `ASE_VERSION_TAG "ASE_v4.0.1"` before its
  `#include "Core/ASE_StateMachine.mqh"` line, so the override is already
  in effect by the time the preprocessor reaches Config.mqh's guard.
- `InpMagicNumber` is an `input` variable, not a macro — MQL5 permits
  exactly one declaration of an input per compiled unit, so only its
  *default value* could vary per build. Introduced `ASE_MAGIC_DEFAULT`
  (same `#ifndef` pattern, default `203157`) and changed the input
  declaration to `input int InpMagicNumber = ASE_MAGIC_DEFAULT;`.
  `ACE_v4.0.1.mq5` `#define`s `ASE_MAGIC_DEFAULT 204001` before the same
  include line.

**`ACE_v4.0.0.mq5` and `ACE_v3.14.17.mq5` are unmodified in behavior** —
neither defines either override macro, so both fall through to Config.mqh's
existing defaults exactly as before this change. Verified by inspection,
not by compiling (no MT5 runtime in this environment — same limitation
noted throughout this changelog).

**Found while verifying this, NOT fixed (pre-existing, predates this
session, out of scope for what was asked):** `ACE_v3.14.17.mq5` and
`ACE_v4.0.0.mq5` have *always* shared `ASE_VERSION_TAG = "ASE_v4.0.0"` —
the tag was bumped to `"ASE_v4.0.0"` once for the V4 delivery and
v3.14.17 was never given its own value, despite the Fix 16 comment in the
same file explicitly warning this exact scenario. If v3.14.17 and v4.0.0
(or v4.0.1) are ever run simultaneously on the same symbol/terminal, they
will collide on every output file the same way the Fix 16 incident did.
Not touched here because it wasn't part of what was asked and changing
v3.14.17's identity is a materially different decision than forking
v4.0.0 — flagging it because it's directly relevant to a multi-version
side-by-side deployment plan and silence here would be misleading.

**Also found, not fixed (separate, smaller, pre-existing):** the
opportunity-log filename (`CASE_SetupAnalytics::BuildPath()`) is built
from `m_filePrefix` (the version tag) and date only — no `_Symbol`
component, unlike the learning-state and context-snapshot paths right
next to it in the same file. Two instances of the *same* version tag
running on two different symbols in the same terminal would collide on
this one file specifically. Not a risk for the v4.0.0/v4.0.1 side-by-side
case (different tags), so left alone — noting it because it's the same
category of bug and someone will hit it the day this EA runs multi-symbol.

**Files touched this pass:**
- New: `ACE_v4.0.1.mq5` (forked from `ACE_v4.0.0.mq5`; banner text updated
  to state the fork relationship and the one behavioral difference).
- `Models/ASE_Config.mqh`: `ASE_VERSION_TAG` and the `InpMagicNumber`
  default converted to override-before-include macros, as above.
  `ACE_v4.0.0.mq5`/`ACE_v3.14.17.mq5` behavior unchanged.

---

## Addendum 6 — Order Block detector (v4.0.1, added to this same fork)

Highest-priority item from the confluence-gap review earlier in this
session: Order Block is named in this project's own ICT/SMC concept list
(BOS, CHoCH, FVG, OB, liquidity sweeps, kill zones, AMD) but had no
detector anywhere in the codebase — FVG and EMA pullback were the only
entry-zone evidence types. Added as `EVID_ORDER_BLOCK` /
`CASE_SetupEngine::CheckOrderBlock()`, delivered directly into this
already-forked `ACE_v4.0.1.mq5` rather than another new side-by-side
fork, since v4.0.1 is itself still an unreleased/unvalidated experimental
build (no separate isolation need yet — only one build wanted this).

**Definition used, stated explicitly because ICT/SMC literature is not
uniform on this point:** the last opposite-colour M15 candle immediately
before a same-direction displacement candle whose close breaks beyond
that candle's high/low (a mini BOS — required, not optional; without it
"last red candle before a green one" fires on noise). Zone = the OB
candle's full high/low range, matching this file's existing FVG
convention of wick-to-wick zones rather than body-only. A block is
treated as fully invalidated (excluded, not just weighted down) the
moment any subsequent bar closes cleanly through it — stricter than
FVG's depth-penetration gate, because OB literature generally treats a
clean close-through as the block having failed outright, not merely
faded.

**Wiring:**
- `Models/ASE_EvidenceTypes.mqh` — `EVID_ORDER_BLOCK = 16`.
- `Models/ASE_ConfluenceTypes.mqh` — DNA tag `"OB"`.
- `Core/ASE_ConfluenceEngine.mqh` — weight 6.0, `FAM_LOCATION` (same
  family as FVG 8 + EMA pullback 5; family cap is 20, so 19 total still
  has headroom). Interim nominal weight, same caveat as Addendum 4's two
  promotions: not evidence-derived, no backtest behind the number.
- `Core/ASE_SetupEngine.mqh` — new private `CheckOrderBlock()`, called
  ONLY from `EvaluateAllEvidence()`. The legacy `Evaluate()` cascade
  (the method that actually gates v3.14.17/v4.0.0/v4.0.1's real
  execution decisions) has zero lines changed — verified by diff, same
  standard this project has applied to every other v4 addition.
- `Models/ASE_Config.mqh` — four new inputs: `InpEnableOrderBlock` (kill
  switch), `InpOBLookback` (scan window, mirrors FVG's), `InpOBMaxBars`
  (age gate, same rationale as `InpFVGMaxBars`), `InpOBDispMultiplier`
  (ATR body-size threshold for the confirming displacement candle).

**Deliberately NOT done:** not added to any `CoreCheck*()` in
`ASE_SetupClassifier.mqh` — ships as enhancer-only (scored, but not
required for any archetype to qualify), same reasoning given earlier in
this session for the compression/EMA-align promotions: no observation
data exists yet to justify making a brand-new, unvalidated detector a
hard requirement for setup classification. `ASE_MAX_EVIDENCE` capacity
checked — M15 evidence collection goes from 8 to 9 items per bar,
nowhere near the 24-item cap.

**Not done in this session (per explicit instruction — one item per
session, not all four):** kill-zone/AMD-phase timing evidence, DXY/real-
yield correlation evidence, liquidity-pool (equal highs/lows, PDH/PDL)
mapping. Still queued in that priority order.

**Verification performed:** brace/paren balance confirmed on every
touched file. Not verified: actual detection behavior against real price
data — no MT5 runtime in this environment, same limitation stated
throughout this changelog. This detector has never fired once on real
data. Do not treat its presence as validated until it has.
