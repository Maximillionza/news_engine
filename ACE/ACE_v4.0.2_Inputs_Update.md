# ACE v4.0.2 — Inputs Update

**Adaptive Confluence Engine (ACE)** · audited build `ACE_v4.0.2` (`ASE_VERSION_TAG "ASE_v4.0.2"`, magic `204002`) · prepared 2026-09-30 (SAST)

**Status: proposal. No source file was changed.** This is the spec for an `ACE_v4.0.3` inputs clean-up (magic `204003` under the `20XXXX` convention). Scope is the MT5 Inputs tab only, meaning every `input` declared in `Models/ASE_Config.mqh`.

---

## 1. Bottom line

| Tier | Count | What happens |
|---|---|---|
| **KEEP** (visible in MT5) | 48 | Stays an `input`, regrouped under `input group` headers (Appendix A) |
| **HIDE** (config file only) | 145 | Becomes a `const` with the same name and value; editable only in `ASE_Config.mqh` (needs a recompile) |
| **DELETE** | 17 | No effect on behaviour anywhere in the source; the declaration is removed |
| Total | 210 | |

The Inputs tab is crowded because releases kept adding knobs and rarely retired any (the config still carries `RETIRED` stubs from v3.12.3), not because 210 things need tuning. Two structural facts explain most of the result. First, the EA trades as the legacy v3.14.17 path unless `InpAceV4Mode` is raised to `CONDITIONAL` or `ACTIVE`, so **[Likely] 95 of the 210 inputs are V4-only and cannot change a trade's entry, size or exit in the default mode** (F5). Second, the per-regime profile block was rewired in v3.14.0 and the inputs were never pruned to match, which left inputs that only write to a log line (F2) or that nothing reads (F1).

The 48 that remain decide how much you risk, where you exit, which setups and regimes may trade, when the EA stands down, and which magic number it owns. Add to that the single V4 authority switch and its two promotion-time dials.

Confidence tags: **[Certain]** = read directly in the source (file and line given). **[Likely]** = strong inference from the source or general MT5 behaviour. **[Guessing]** = gap-filling. Nothing here was compiled or back-tested, because this environment has no MT5 runtime.

---

## 2. How the audit was done

All 210 inputs were extracted from `Models/ASE_Config.mqh` and searched by whole-word match across every `.mq5` and `.mqh` file in the package (23,122 lines), with comments stripped so a mention in documentation does not count as use. Anything with zero or log-only consumers was then traced by hand to its reader. Tier decisions follow four tests in order: does it change behaviour at all; is it auto-adjusted by the learner or derived elsewhere; is it only needed when diagnosing a problem; is it set once per broker or instrument. Only an input that passes the first test and fails the other three stays visible.

---

## 3. Findings that change the answer

**F1. [Certain] Seventeen inputs are dead.** `InpHoldoutDays` has zero references anywhere. `InpDGMinVotes`, `InpDGShortScoreBonus` and `InpDGRetryBars` are read only inside `ASE_DirectionGate.mqh`, whose include is commented out (`ASE_StateMachine.mqh:44`, removed in v3.12.3). `InpATRMultiplierSL_Wide`, `InpATRSLCap`, `InpTP1Mode`, `InpTP2Mode` and `InpScoreThreshold` survive only in the `default:` branch of `LoadProfile()` (`ASE_RegimeProfile.mqh:181-188`), which the regime gate makes unreachable, plus one Print and two logger fallbacks. The real SL, cap, TP modes and score gate all come from the per-regime profile (`ASE_RiskEngine.mqh:145-146`, `:184-185`; `ASE_StateMachine.mqh:1946` onward). The other eight are F2.

**F2. [Certain] The per-regime `InpSpread_*` (4) and `InpBiasConf_*` (4) inputs are log-only.** They load into `profile.maxSpread` and `profile.biasConfidenceMin`, whose only reader is one Print (`ASE_StateMachine.mqh:1139-1141`). The spread gate that actually blocks trades is the global `InpMaxSpread` (`:978`, `:1666`, `:1910`, `:2156`). The bias-conflict timer is the global `InpBiasReEvalBars` (`ASE_StructureEngine.mqh:798`). Anyone tuning the per-regime versions today is changing a log line.

**F3. [Certain] `InpATRMultiplierSL` no longer sets the stop.** Since v3.14.0 the SL comes from the regime profile. The global survives only as the RR-gate denominator (`rrDenom = ATR x InpATRMultiplierSL`, `ASE_RiskEngine.mqh:217`) and in log Prints, so touching it silently rescales `InpMinRR`. At 1.0 and `InpMinRR` 2.0, TP2 must be at least 2 ATR away. It is hidden, not deleted, because the RR gate still needs the constant.

**F4. [Certain] The COMPRESSION profile is unreachable at the shipped default.** With `InpCompressionMode = 0`, the HTF step returns to IDLE on any COMPRESSION regime (`ASE_StateMachine.mqh:1151-1157`) before a setup can be built. `InpSL_Compression`, `InpSLCap_Compression` and `InpScore_Compression` are therefore inert until the mode is set to 1. `InpCompressionMode` stays visible; its three sub-parameters go to the config file.

**F5. [Certain for the three gates, Likely for "no other path"] V4 inputs are inert below CONDITIONAL.** V4 can place a trade only through `v4Authority`, which requires `InpAceV4Mode` to be `CONDITIONAL` or `ACTIVE` and `InpAceV4ResearchOnly` false (`ASE_StateMachine.mqh:1858-1861`, `:1907-1927`). It can override a legacy setup failure only under the same condition (`:1525`). The archetype-aware SL/TP branch runs only when `m_v4ExecutionAttempt` is true (`:2259`); every other trade takes the unchanged 3-argument `BuildSetup()` (`:2292`). In `EVIDENCE` (the default) and `ADVISORY` the V4 inputs change what is logged and learned, not what is traded. I read those regions, not all 3,112 lines of the state machine, so "no other path" is an inference.

**F6. [Certain] The archetype SL multipliers compound, and the config comment about them is stale.** The config says "all fifteen defaults below are 1.0" (`ASE_Config.mqh:493`), but the five SL defaults are 1.2, 1.4, 1.6, 1.8 and 1.2 (`:505-517`). On a V4-executed trade the final SL multiplier is regime x archetype x any learned leaf override (`ASE_RiskEngine.mqh:145`, `ASE_StateMachine.mqh:2276`). With current defaults RANGING 2.4 x PULLBACK_CONTINUATION 1.8 = 4.32 x ATR before the regime's SL cap. The archetype x leaf product also scales the ATR trail distance (`ASE_ATRTrailEngine.mqh:64`). **[Guessing]** whether the SL cap usually binds first; that depends on live ATR. All 15 are hidden: they are a hand-set prior that the learner rescales, so they need no operator dial, and they do nothing until V4 holds authority.

**F7. [Certain] `InpAceV4AuthCautiousMin` is used as two different things.** It is the observation count for the first authority tier (`ASE_AdaptiveEngine.mqh:277`) and also the lower bound of a 0-100 score threshold that the learner nudges (`ClampCandidateThreshold`, `:300`). Raising it from 20 to 40 to "require more evidence" also raises the floor of every learned threshold to 40. The tier order Cautious < Controlled < Validated is not checked either; a mis-ordered set simply makes a tier unreachable (`:275-277`). Both are reasons to keep the authority-tier trio out of the Inputs tab.

**F8. News protection is off by default, and [Likely] it lapses after 48 hours.** **[Certain]** `InpNewsBlockMinutes = 0` makes the block window zero seconds wide (`ASE_NewsEngine.mqh:85`, `:105`), which is effectively off. **[Certain]** The calendar is scanned once, at attach (`ACE_v4.0.2.mq5:112`, 48-hour window), and later events are supposed to arrive through a function named `OnCalendarEvent` (`:128`). **[Likely]** That function is never called: it is not among the event handlers MQL5 documents (`OnInit`, `OnDeinit`, `OnTick`, `OnCalculate`, `OnTimer`, `OnTrade`, `OnTradeTransaction`, `OnBookEvent`, `OnChartEvent`, `OnTester*`), so MetaEditor compiles it as an ordinary unused function. I could not open the MQL5 reference from this environment to confirm. A cheap live check: after the first 48 hours, search the Journal for `[NEWS] Event registered`. If that line never appears, the handler is dead and the queue empties. The consequence is that raising `InpNewsBlockMinutes` gives protection for roughly two days after each attach and then stops without warning. The input stays visible because it is the only news lever; a periodic rescan is a code fix outside this inputs update. **[Likely]** The news gate is also live-only, because the calendar API is not available in the Strategy Tester (the scan would just log `no events in next 48h (or calendar unavailable)`), so backtests never exercise it.

**F9. Hiding has four side effects to plan for.** (a) **[Certain]** A saved `.set` preset that overrides any of the 162 removed or hidden inputs stops applying once they are constants; audit your presets and bake any non-default value into the new config defaults first. (b) **[Likely]** MT5 tester reports list only `input` variables, so hidden constants will not appear in a report's input list and your baseline-vs-challenger dashboard's Input Parameter tab will show no diff for them; add a config fingerprint line (Section 7, step 6). (c) **[Certain]** The MT5 optimiser can sweep only `input` variables, so a hidden constant needs a temporary edit or a compile switch before it can be optimised. (d) **[Certain]** Nothing inside the package addresses inputs by name (zero matches in `ASE_OptimizerBridge`, `ASE_SensitivityMap`, `ASE_VPSOptimizer`, `ASE_Diagnostics` and `Reporting/`), so hiding breaks no in-source tooling.

---

## 4. KEEP: 48 inputs visible in MT5

### 4.1 Sizing and exposure

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpRiskPercent` | `0.50` | Balance % risked per trade at full size (no drawdown scaling since v4.0.2). The dominant driver of both return and ruin. A sub-minimum-lot size still trades the minimum lot and logs the real risk. |
| `InpMinRR` | `2.0` | Reward:risk gate on the TP2 distance, measured against ATR x `InpATRMultiplierSL` (1.0). At 2.0 the setup is rejected at `BuildSetup()` unless TP2 sits at least 2 ATR away (F3). |
| `InpMaxPositions` | `1` | Concurrent-position cap; cluster protection and the V4 orchestrator both read it. A direct exposure limit. |
| `InpCooldownBars` | `5` | M15 bars of lockout after a close (5 = 75 min). Controls re-entry frequency after a loss. |

### 4.2 Risk Guard

Blocks NEW entries only; open positions keep being managed. State is keyed by account and symbol and survives restarts, version bumps and magic changes.

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpRiskDailyLossPct` | `2.0` | Equity loss vs day-start balance that blocks new entries until the next broker day. The only guard active below the pause level (see Observation O1). |
| `InpRiskPauseDDPct` | `30.0` | Peak-balance drawdown that pauses new entries until the next broker day. 30% is loose (O1). |
| `InpRiskProbationDDPct` | `5.0` | After a pause, the drawdown from the resume peak that HALTS trading for human review. |
| `InpRiskGuardResetNonce` | `0` | The only way to clear a HALTED guard is to change this value and re-attach. It must stay in the Inputs tab, otherwise every halt reset costs a recompile. |

### 4.3 Exits

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpATRMultiplierTP1` | `2.0` | TP1 distance in ATR. Moves only the ATR-mode and ATR-fallback leg; a structural TP1 target ignores it. |
| `InpATRMultiplierTP2` | `4.0` | Runner target in ATR (same caveat); also sets the RR-gate numerator. |
| `InpPartialTPEnabled` | `true` | Close part of the position at TP1. Skipped automatically at or near minimum lot. |
| `InpPartialTPPercent` | `50.0` | Percent of the position closed at TP1. |
| `InpATRTrailEnabled` | `true` | ATR trailing stop on or off. |
| `InpATRTrailMultiplier` | `1.5` | Trail distance = ATR x this. On V4-executed trades it is further scaled by the archetype x leaf SL multiplier (F6). |

### 4.4 Regime profiles: TRENDING, RANGING, MANIPULATION

These nine are the real per-regime SL and entry gate. `InpSLCap_*` is a price distance, not broker points (O2). `InpScore_*` is the score gate that actually blocks entries; the global `InpScoreThreshold` is dead (F1).

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpSL_Trending` | `1.8` | SL distance = ATR x this, before the cap. |
| `InpSLCap_Trending` | `15.0` | Hard SL ceiling in price units (0 = none). |
| `InpScore_Trending` | `60.0` | Minimum composite score (0-100) to enter in TRENDING. |
| `InpSL_Ranging` | `2.4` | As above for RANGING. |
| `InpSLCap_Ranging` | `20` | As above for RANGING. |
| `InpScore_Ranging` | `55.0` | As above for RANGING. |
| `InpSL_Manipulation` | `1.6` | As above for MANIPULATION. |
| `InpSLCap_Manipulation` | `14.0` | As above for MANIPULATION. |
| `InpScore_Manipulation` | `75.0` | As above for MANIPULATION. |

### 4.5 COMPRESSION switch

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpCompressionMode` | `0` | 0 = no entries in COMPRESSION (breakout watch; the default since Fix 13, which cites COMPRESSION at 16.2% WR and PF 0.55 inside a 335-trade backtest). 1 = trade it using the config-only COMPRESSION SL 1.8 / cap 8.0 / score 75 (F4). |

### 4.6 Entry filters

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpMaxSpread` | `70` | Hard spread ceiling in points. The only spread gate that is enforced: idle check (`ASE_StateMachine.mqh:978`), execution stage (`:2156`, logged as `Spread widened at entry`) and V4 discipline (`:1910`). Also the top of the spread-score range (F2). |
| `InpLiquidityConfirm` | `true` | Requires liquidity confirmation before entry. It gates entry, it does not merely score. |
| `InpSlippageGateATRMult` | `0.8` | Aborts when price drifts adversely by more than this multiple of M1 ATR between trigger-bar close and order (0 = off). Raised 0.5 to 0.8 in Fix 4 after it vetoed the best signal of a day. |
| `InpNewsBlockMinutes` | `0` | Blocks entries within this many minutes of a high-impact calendar event. 0 = off, which is the shipped default. Read F8 before relying on it. |

### 4.7 Setup and trigger filters

Attribution-driven switches. The three trigger blocks default to false because the config comments cite backtest or live evidence for each.

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpEnableFVG` | `true` | Allow FVG setups. Per-class kill switch for pruning by attribution. |
| `InpEnableDisplacement` | `true` | Allow M15 displacement setups. |
| `InpEnableCompressionBO` | `true` | Allow compression-breakout setups. |
| `InpEnableEMAPullback` | `true` | Allow EMA-pullback setups. |
| `InpEMAFallbackInRanging` | `false` | Allow the weakest trigger (Score_M1 = 7, no structural confirmation) in RANGING. False since v3.14.2 (avg -$21.15 per trade in May-Jun 2026 live data). |
| `InpEMAFallbackInTrending` | `false` | Same trigger in TRENDING. False since v3.14.9 (335-trade backtest: EMA_Fallback -$670.66, PF 0.66). |
| `InpWeakShortTriggersInTrending` | `false` | Allow Rejection and Displacement triggers on SHORT in TRENDING (Disp+mBOS is always allowed). False since v3.14.10 (TRENDING+SHORT PF 0.69 vs LONG 1.18). |

### 4.8 Sessions

London is 06:00-12:30 UTC (08:00-14:30 SAST) and NY is 12:30-21:00 UTC (14:30-23:00 SAST). The window edges themselves are config-only (Section 5, group I1).

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpUseLondon` | `true` | Trade the London window. |
| `InpUseNY` | `true` | Trade the NY window. |
| `InpTrade24_7` | `false` | Master bypass of the session filter. |

### 4.9 Structure

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpH1SwingPivot` | `2` | Bars each side that confirm an H1 swing pivot. The BOS and bias sensitivity dial (3 = fewer, more conservative swings). |
| `InpBiasInvalidATRMult` | `2.0` | An adverse close of this multiple of H4 ATR since the BOS that set the bias resets the bias to none (0 = off). The safety valve against the one-way bias ratchet. |

### 4.10 V4 authority

Dormant below CONDITIONAL (F5). `InpAceV4Mode` is the master switch and the only V4 input that matters on day one.

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpAceV4Mode` | `ACEV4_EVIDENCE` | LEGACY = V4 off (byte-for-byte v3.14.17); EVIDENCE = learn with no authority (default); ADVISORY = decision visible, legacy executes; CONDITIONAL and ACTIVE = V4 may execute once the adaptive gates validate. |
| `InpAceV4AllowBConditional` | `true` | Lets an APEX_B setup qualify for execution authority. The path also requires a hard-coded separation of at least 25.0 (`ASE_AdaptiveEngine.mqh:290`, O3). |
| `InpAceV4MinSeparation` | `15` | Minimum directional score separation for a setup to qualify (`ASE_ConfidenceEngine.mqh:100`). Changes which opportunities count as qualified and learned in every mode, and authority in CONDITIONAL and above. |

### 4.11 Operations

| Input | Default | What it does / why it stays |
|---|---|---|
| `InpMagicNumber` | `ASE_MAGIC_DEFAULT` (204002) | Position identity for every manage and filter call; must be unique per instance so side-by-side builds cannot touch each other's trades. Convention `20XXXX`. |
| `InpAlertsEnabled` | `false` | MT5 push notifications (including a Risk Guard halt). |
| `InpStateLogEnabled` | `true` | Daily CSV state log. Turn off on live accounts to stop file build-up; when off, the state logger opens no files. |
| `InpShowChartVisuals` | `true` | Pivot S/R rays, BOS markers and the active-trade panel. |
| `InpShowV4Dashboard` | `true` | V4 status panel. The declaration's comment is copy-pasted from the chart-visuals input; the behaviour is the V4 panel only. |

### Observations on the visible defaults

**O1. [Certain] `InpRiskPauseDDPct = 30.0` is a loose leash.** The multi-day protective layers (Pause, then Probation, then Halt) only begin once equity is 30% below peak balance. Below that, the only guard is the 2.0% daily cap. Confirm that is deliberate; it is the most consequential default in the visible list.

**O2. [Certain] `InpSLCap_*` is a price distance, not broker points.** `ASE_RiskEngine.mqh:148-156` compares it directly with ATR x multiplier, so on XAUUSD a cap of 15.0 means a $15.00 stop. The input comment says "points" and the log says "pts". **[Certain]** The cap overrides the multiplier whenever M15 ATR exceeds cap / multiplier: 8.33 for TRENDING (15.0 / 1.8) and RANGING (20.0 / 2.4), 8.75 for MANIPULATION (14.0 / 1.6) and only 4.44 for COMPRESSION (8.0 / 1.8). **[Guessing]** How often your feed's ATR exceeds those levels; check against live ATR before trusting the multipliers, especially for COMPRESSION if you ever set `InpCompressionMode` to 1.

**O3. [Certain] `InpAceV4AllowBConditional` has a hidden partner.** The B-grade path also requires `separation >= 25.0`, hard-coded in `LivePolicy()` (`ASE_AdaptiveEngine.mqh:290`), independent of `InpAceV4MinSeparation`.

---

## 5. HIDE: 145 inputs become config-file-only

Each becomes `const <type> <same name> = <same value>;` in a marked CONFIG-ONLY section of `ASE_Config.mqh` (Appendix B). Nothing else in the source changes, because the names are unchanged. The tables list every input with its type, current default and its line in the v4.0.2 `ASE_Config.mqh`.

### A. Learner hyperparameters (14)

These parameterise the learning engine itself: authority-tier sample gates, adaptation rate and cooldown, lifecycle (dormant, retire, revive) rules, rollback window and prior weighting. The engine adapts its own thresholds inside them, so hand-tuning fights the learner. `InpAceV4AuthCautiousMin` carries the dual-use trap in F7.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpAceV4AdaptCooldownObs` | `int` | `5` | 561 |
| `InpAceV4AdaptLearningRate` | `double` | `0.20` | 562 |
| `InpAceV4ReqMinSamples` | `int` | `30` | 565 |
| `InpAceV4RetireMinRegimes` | `int` | `3` | 570 |
| `InpAceV4RetireMinPerRegime` | `int` | `20` | 571 |
| `InpAceV4ReviveWindow` | `int` | `30` | 572 |
| `InpAceV4NegativeEdgeFloor` | `double` | `0.0` | 573 |
| `InpAceV4PromoteMinPaired` | `int` | `50` | 576 |
| `InpAceV4RollbackWindow` | `int` | `20` | 590 |
| `InpAceV4EnhancerPriorWeight` | `double` | `20.0` | 781 |
| `InpAceV4AuthCautiousMin` | `int` | `20` | 553 |
| `InpAceV4AuthControlledMin` | `int` | `50` | 554 |
| `InpAceV4AuthValidatedMin` | `int` | `100` | 555 |
| `InpAceV4TheoreticalMaxBars` | `int` | `20` | 556 |

### B. Learned SL/TP candidate bounds (3)

Step, floor and ceiling for the learner's own SL/TP multiplier candidates (`CASE_SetupAnalytics`). Bounds on an auto-adjusted quantity are not an operator dial.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpAceV4SLTPCandidateStep` | `double` | `0.10` | 528 |
| `InpAceV4SLTPMultiplierMin` | `double` | `0.50` | 529 |
| `InpAceV4SLTPMultiplierMax` | `double` | `2.00` | 530 |

### C. Archetype SL/TP multipliers (15)

A hand-set prior that the learner rescales on top of, active only on V4-executed trades (F5, F6). The five SL defaults are not 1.0 despite the config comment, and the archetype x leaf product also scales the ATR trail distance.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpSL_ArchTrendContinuation` | `double` | `1.2` | 505 |
| `InpTP1_ArchTrendContinuation` | `double` | `1.0` | 506 |
| `InpTP2_ArchTrendContinuation` | `double` | `1.0` | 507 |
| `InpSL_ArchLiquidityReversal` | `double` | `1.4` | 508 |
| `InpTP1_ArchLiquidityReversal` | `double` | `1.0` | 509 |
| `InpTP2_ArchLiquidityReversal` | `double` | `1.0` | 510 |
| `InpSL_ArchCompressionExpansion` | `double` | `1.6` | 511 |
| `InpTP1_ArchCompressionExpansion` | `double` | `1.0` | 512 |
| `InpTP2_ArchCompressionExpansion` | `double` | `1.0` | 513 |
| `InpSL_ArchPullbackContinuation` | `double` | `1.8` | 514 |
| `InpTP1_ArchPullbackContinuation` | `double` | `1.0` | 515 |
| `InpTP2_ArchPullbackContinuation` | `double` | `1.0` | 516 |
| `InpSL_ArchStructuralReversal` | `double` | `1.2` | 517 |
| `InpTP1_ArchStructuralReversal` | `double` | `1.0` | 518 |
| `InpTP2_ArchStructuralReversal` | `double` | `1.0` | 519 |

### D. Holdout integrity (5)

`IsOOS()` hashes each opportunity id modulo K to decide which outcomes are held out (`ASE_AdaptiveEngine.mqh:326-340`). Changing K or the mode re-partitions every future outcome while the persisted statistics were accumulated under the old split. [Likely] hiding these is a safety measure as much as a tidy-up.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpAceV4OOSMode` | `int` | `1` | 592 |
| `InpAceV4OOSEveryK` | `int` | `5` | 593 |
| `InpAceV4OOSStartDate` | `string` | `""` | 591 |
| `InpAceV4OOSMinSamples` | `int` | `20` | 579 |
| `InpAceV4MinOOSRetention` | `double` | `0.85` | 580 |

### E. V4 scoring constants (16)

Calibrated against 2026 backtest distributions (the config cites Jan-Sep for the grades and Jan-Jun for the trigger layer). The config's own notes say not to re-tune the grade thresholds by hand until Phase 6 Cluster A is complete; family caps, conflict share, secondary credit, trigger-layer window and freshness windows are the same kind of constant.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpAceV4GradeB` | `double` | `51.9` | 729 |
| `InpAceV4GradeA` | `double` | `55.3` | 730 |
| `InpAceV4GradePlus` | `double` | `60.0` | 731 |
| `InpAceV4FamCapStructure` | `double` | `25.0` | 743 |
| `InpAceV4FamCapLocation` | `double` | `20.0` | 744 |
| `InpAceV4FamCapLiquidity` | `double` | `24.0` | 745 |
| `InpAceV4FamCapMomentum` | `double` | `20.0` | 746 |
| `InpAceV4FamCapEnvironment` | `double` | `14.0` | 747 |
| `InpAceV4FamCapExecution` | `double` | `5.0` | 748 |
| `InpAceV4ConflictOpposingShare` | `double` | `0.25` | 759 |
| `InpAceV4PhenomenonSecondaryCredit` | `double` | `0.25` | 803 |
| `InpAceV4TriggerMinAtrMove` | `double` | `0.10` | 800 |
| `InpAceV4TriggerMaxAgeBars` | `int` | `10` | 801 |
| `InpAceV4FreshnessMaxM1Bars` | `int` | `5` | 595 |
| `InpAceV4FreshnessMaxM15Bars` | `int` | `8` | 596 |
| `InpAceV4FreshnessMaxH1Bars` | `int` | `12` | 597 |

### F. Detector and classifier calibration (8)

Counter-trend gates, the strong-separation TRENDING path, the MANIPULATION volatility credit, FVG age and the kill-zone score toggle. Backtest-derived; change only with attribution data in hand.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpCTEMASepThreshold` | `double` | `0.80` | 410 |
| `InpTrendEMASepStrong` | `double` | `0.80` | 418 |
| `InpVolScore_Manipulation` | `double` | `6.0` | 419 |
| `InpCTDispMultiplier` | `double` | `0.85` | 431 |
| `InpCTFVGMinGap` | `double` | `0.50` | 432 |
| `InpCTFVGMaxDepth` | `double` | `0.50` | 433 |
| `InpFVGMaxBars` | `int` | `10` | 251 |
| `InpKillZoneEnabled` | `bool` | `true` | 209 |

### G. Per-regime TP modes (8)

Structural, ATR or hybrid targets were chosen per regime by design (rationale in the config comments). Flipping one is an A/B experiment, not routine tuning; promote back when you run it.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpTP1Mode_Trending` | `ENUM_TP_MODE` | `TP_STRUCTURAL` | 437 |
| `InpTP2Mode_Trending` | `ENUM_TP_MODE` | `TP_STRUCTURAL` | 438 |
| `InpTP1Mode_Ranging` | `ENUM_TP_MODE` | `TP_HYBRID` | 448 |
| `InpTP2Mode_Ranging` | `ENUM_TP_MODE` | `TP_HYBRID` | 449 |
| `InpTP1Mode_Compression` | `ENUM_TP_MODE` | `TP_ATR` | 467 |
| `InpTP2Mode_Compression` | `ENUM_TP_MODE` | `TP_ATR` | 468 |
| `InpTP1Mode_Manipulation` | `ENUM_TP_MODE` | `TP_STRUCTURAL` | 478 |
| `InpTP2Mode_Manipulation` | `ENUM_TP_MODE` | `TP_ATR` | 479 |

### H. Evidence-only detectors (16)

Feed V4 evidence and learning only: no legacy effect, and no trade effect below CONDITIONAL (F5). The DXY-basket symbol names are broker-specific; when a name does not exist the evidence degrades silently apart from a Journal warning (`DXY-basket symbol(s) not found`). Asian session here is 00:00-07:00 UTC (02:00-09:00 SAST).

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpEnableOrderBlock` | `bool` | `true` | 610 |
| `InpOBLookback` | `int` | `20` | 611 |
| `InpOBMaxBars` | `int` | `15` | 612 |
| `InpOBDispMultiplier` | `double` | `0.60` | 613 |
| `InpEnableKillZoneEvidence` | `bool` | `true` | 630 |
| `InpEnableAMDPhase` | `bool` | `true` | 631 |
| `InpAsianStartHour` | `int` | `0` | 632 |
| `InpAsianStartMin` | `int` | `0` | 633 |
| `InpAsianEndHour` | `int` | `7` | 634 |
| `InpAsianEndMin` | `int` | `0` | 635 |
| `InpAMDLookbackBars` | `int` | `12` | 636 |
| `InpEnableLiquidityPool` | `bool` | `true` | 698 |
| `InpLiqPoolLookback` | `int` | `20` | 699 |
| `InpLiqPoolEqualTolerance` | `double` | `0.10` | 700 |
| `InpLiqPoolSweepBars` | `int` | `8` | 701 |
| `InpEnableMacroCorrelation` | `bool` | `true` | 663 |

### I1. Set-once: session clock (8)

London 06:00-12:30 UTC (08:00-14:30 SAST), NY 12:30-21:00 UTC (14:30-23:00 SAST). Session definitions, not tuning levers; the on/off switches stay visible (4.8).

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpLondonStartHour` | `int` | `6` | 214 |
| `InpLondonStartMin` | `int` | `0` | 215 |
| `InpLondonEndHour` | `int` | `12` | 216 |
| `InpLondonEndMin` | `int` | `30` | 217 |
| `InpNYStartHour` | `int` | `12` | 218 |
| `InpNYStartMin` | `int` | `30` | 219 |
| `InpNYEndHour` | `int` | `21` | 220 |
| `InpNYEndMin` | `int` | `0` | 221 |

### I2. Set-once: macro basket plumbing (11)

Broker symbol names, coverage threshold, rate-of-change window and the init-time history warm-up (a one-time startup cost, never per tick).

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpDXYSymbolEUR` | `string` | `"EURUSD"` | 664 |
| `InpDXYSymbolJPY` | `string` | `"USDJPY"` | 665 |
| `InpDXYSymbolGBP` | `string` | `"GBPUSD"` | 666 |
| `InpDXYSymbolCAD` | `string` | `"USDCAD"` | 667 |
| `InpDXYSymbolSEK` | `string` | `"USDSEK"` | 668 |
| `InpDXYSymbolCHF` | `string` | `"USDCHF"` | 669 |
| `InpMacroBasketMinCoverage` | `double` | `0.70` | 670 |
| `InpMacroCorrLookbackBars` | `int` | `8` | 671 |
| `InpMacroCorrROCThreshold` | `double` | `0.0015` | 672 |
| `InpMacroBasketWarmupRetries` | `int` | `20` | 681 |
| `InpMacroBasketWarmupWaitMs` | `int` | `250` | 682 |

### I3. Set-once: defensive and execution constants (7)

Instrument or broker calibration and protective constants that are set once: spread-score baseline, spread-spike multiple, order retries, spread-shock abort, heartbeat timeout, daily reset hour (UTC), BOS marker history.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpSpreadBaseline` | `double` | `35` | 79 |
| `InpSpreadSpikeMultiplier` | `double` | `1.5` | 367 |
| `InpExecRetries` | `int` | `3` | 370 |
| `InpExecSpreadShockMult` | `double` | `2.5` | 371 |
| `InpHeartbeatMinutes` | `int` | `5` | 366 |
| `InpDailyResetHour` | `int` | `0` | 311 |
| `InpMaxBOSMarkers` | `int` | `20` | 154 |

### J. Diagnosis-only switches (20)

`InpAceV4Enable*` (9) isolate one pipeline stage. `InpRegimeFilterEnabled`, `InpOffSessionBiasGuard` and `InpSlippageAdverseOnly` switch off a bug-fix guard whose alternative is a known-worse behaviour. The six bias and pivot inputs matter only when diagnosing a stalled pipeline (bias-conflict blocking is the mechanism behind the all-day-silence episodes the config comments describe). `InpAceV4LogLevel` changes printing only. `InpAceV4MigrateFromTag` is a fresh-run-only import that never re-imports on restart (`ASE_StateMachine.mqh:373-394`); a version bump already needs a recompile, so config-only costs nothing.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpAceV4EnableArchTrendContinuation` | `bool` | `true` | 813 |
| `InpAceV4EnableArchLiquidityReversal` | `bool` | `true` | 814 |
| `InpAceV4EnableArchCompressionExpansion` | `bool` | `true` | 815 |
| `InpAceV4EnableArchPullbackContinuation` | `bool` | `true` | 816 |
| `InpAceV4EnableArchStructuralReversal` | `bool` | `true` | 817 |
| `InpAceV4EnableSequenceEngine` | `bool` | `true` | 818 |
| `InpAceV4EnableConflictDetection` | `bool` | `true` | 819 |
| `InpAceV4EnableFreshnessGate` | `bool` | `true` | 820 |
| `InpAceV4EnableOpportunityLogging` | `bool` | `true` | 821 |
| `InpRegimeFilterEnabled` | `bool` | `true` | 284 |
| `InpOffSessionBiasGuard` | `bool` | `true` | 321 |
| `InpSlippageAdverseOnly` | `bool` | `true` | 385 |
| `InpH1SwingLookback` | `int` | `10` | 46 |
| `InpPivotBackfillBars` | `int` | `200` | 54 |
| `InpPivotMaxAgeBars` | `int` | `120` | 55 |
| `InpH1BiasStaleBars` | `int` | `120` | 72 |
| `InpBiasReEvalBars` | `int` | `8` | 234 |
| `InpBiasFlipCycles` | `int` | `3` | 240 |
| `InpAceV4LogLevel` | `ENUM_ACE_LOG_LEVEL` | `LOG_NORMAL` | 843 |
| `InpAceV4MigrateFromTag` | `string` | `""` | 594 |

### K. Special handling (2)

`InpAceV4DiagnosticBypassValidationGate` grants execution authority without earned validation. Its own comment says never enable it on real capital, so it should not be one click away in a live Inputs dialog; keep it config-only and add a loud init Print when it is true. `InpAceV4ResearchOnly` is redundant: with it true, V4 authority and the legacy-veto override are both off (`ASE_StateMachine.mqh:1525`, `:1858`), which is the same execution authority as `ADVISORY`.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpAceV4DiagnosticBypassValidationGate` | `bool` | `false` | 560 |
| `InpAceV4ResearchOnly` | `bool` | `false` | 559 |

### L. Structural constants (6)

Indicator periods. Not performance levers at these values; changing one changes what the regime, bias and trigger engines mean.

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpATRPeriod` | `int` | `14` | 22 |
| `InpH4FastEMA` | `int` | `20` | 39 |
| `InpH4SlowEMA` | `int` | `50` | 40 |
| `InpM15EMA` | `int` | `21` | 73 |
| `InpM1FastEMA` | `int` | `9` | 74 |
| `InpM1SlowEMA` | `int` | `21` | 75 |

### M. Inert, dormant or misleading (6)

`InpSL_Compression`, `InpSLCap_Compression`, `InpScore_Compression` are unreachable while `InpCompressionMode = 0` (F4). `InpMinBiasScore` and `InpMinSetupScore` default to 0 (off) and overlap the per-regime score gate. `InpATRMultiplierSL` no longer sets the stop and only scales the RR gate (F3).

| Input | Type | Default | Config line |
|---|---|---|---|
| `InpSL_Compression` | `double` | `1.8` | 452 |
| `InpSLCap_Compression` | `double` | `8.0` | 453 |
| `InpScore_Compression` | `double` | `75.0` | 462 |
| `InpMinBiasScore` | `double` | `0.0` | 230 |
| `InpMinSetupScore` | `double` | `0.0` | 231 |
| `InpATRMultiplierSL` | `double` | `1.0` | 23 |

---

## 6. DELETE: 17 inputs with no effect

Remove the declaration and patch the listed read sites so the package still compiles. None of these edits changes a trading decision.

| Input(s) | Why it is dead | Edit sites when removing |
|---|---|---|
| `InpHoldoutDays` | Zero references anywhere outside the config declaration. The OOS split that exists is `InpAceV4OOS*`. | Delete the declaration. |
| `InpDGMinVotes`, `InpDGShortScoreBonus`, `InpDGRetryBars` | Read only inside `ASE_DirectionGate.mqh`, whose include is commented out (`ASE_StateMachine.mqh:44`, removed in v3.12.3). | Delete the three declarations. Optionally drop `Core/ASE_DirectionGate.mqh` (327 lines, never compiled); left in place it stays uncompiled but would no longer build if re-included. |
| `InpATRMultiplierSL_Wide`, `InpATRSLCap` | Read only in the unreachable `default:` branch of `LoadProfile()` (`ASE_RegimeProfile.mqh:181-182`). The real SL and cap come from the profile (`ASE_RiskEngine.mqh:145-146`). | Replace the two reads with literals `1.5` and `15.0`. Fix the header comment `ASE_RegimeProfile.mqh:96-104`. |
| `InpTP1Mode`, `InpTP2Mode` | Read only in the same `default:` branch (`:184-185`) and one Print (`ASE_RiskEngine.mqh:74-75`). The real modes come from the profile (`ASE_RiskEngine.mqh:184-185`). | Replace the branch reads with `(int)TP_ATR`. Drop the `TP1 default=` and `TP2 default=` fields from the `[RISK] TP1 default` Print. |
| `InpScoreThreshold` | Only a logger fallback (`ASE_StateLogger.mqh:191`, `:452`, used before the first profile threshold exists) plus the `default:` branch (`ASE_RegimeProfile.mqh:183`). Every live gate uses `m_profile.minScoreThreshold`. | Replace the three reads with `const double ASE_LOG_THRESHOLD_FALLBACK = 60.0;` so the CSV column keeps today's values bit for bit. |
| `InpSpread_Trending`, `InpSpread_Ranging`, `InpSpread_Compression`, `InpSpread_Manipulation` | Load into `profile.maxSpread`, whose only reader is one Print (`ASE_StateMachine.mqh:1140`). The enforced gate is the global `InpMaxSpread` (F2). | In `LoadProfile()` (`ASE_RegimeProfile.mqh:120, 136, 152, 168`) set `p.maxSpread = InpMaxSpread;` so the Print reports the value that is really enforced. |
| `InpBiasConf_Trending`, `InpBiasConf_Ranging`, `InpBiasConf_Compression`, `InpBiasConf_Manipulation` | Load into `profile.biasConfidenceMin`, read only by the same Print (`:1141`). The enforced bias timer is the global `InpBiasReEvalBars` (F2). | In `LoadProfile()` (`:121, 137, 153, 169`) set `p.biasConfidenceMin = InpBiasReEvalBars;`. The printed value changes (for example 4 becomes 8); log text only. |

---

## 7. Implementation spec for `ACE_v4.0.3`

1. **Version bump.** Rename to `ACE_v4.0.3.mq5`, set `#property version "4.03"`, set `ASE_MAGIC_DEFAULT` to `204003`. Keep every `ACE_`/`ASE_` prefix. Update the header comment so it still reads "Adaptive Confluence Engine".
2. **Decide state continuity first.** Bumping `ASE_VERSION_TAG` renames the tagged state files (for example `<tag>_<symbol>_adaptive2.csv`), which orphans the learned V4 state; `ASE_Config.mqh:118-143` makes the same point. Option (a), recommended: bump the tag to `ASE_v4.0.3` and set `InpAceV4MigrateFromTag = "ASE_v4.0.2"` in the config for the first run (fresh-run-only, never re-imports on restart, `ASE_StateMachine.mqh:373-394`). Option (b): keep the tag at `ASE_v4.0.2` so the state files carry over, bumping only the file name, version property and magic. The Risk Guard state is keyed by account and symbol, so it survives either way. **Do not swap builds while a v4.0.2 position is open:** a 204003 instance does not manage positions opened under 204002.
3. **Preset audit (before editing).** Diff every saved `.set` against the v4.0.2 defaults for the 162 removed or hidden inputs and write any non-default value into the new config defaults (F9a).
4. **Config surgery in `Models/ASE_Config.mqh`.** Delete the 17 (Section 6). Convert the 145 to `const` in a marked CONFIG-ONLY section. Regroup the 48 with `input group` (Appendix A). Keep the three enums (`ENUM_TP_MODE`, `ENUM_ACE_V4_MODE`, `ENUM_ACE_LOG_LEVEL`) because hidden constants still use them. Refresh stale comments: the `[default: InpScoreThreshold]` style notes on the profile inputs, the "all fifteen defaults are 1.0" block (F6), the `InpShowV4Dashboard` comment, the `InpSLCap_*` unit wording (O2) and `ASE_RegimeProfile.mqh:96-104`.
5. **Patch the delete sites** exactly as listed in Section 6.
6. **Config fingerprint.** Add one `Print("[CFG] ...")` at `OnInit` that echoes every config-only constant (or a hash of them) and stamp the same string in the state-log CSV header. MT5 reports will not list hidden constants (F9b), so this is what keeps two runs diffable. Generate the function body mechanically from the Section 5 tables; Appendix B shows the pattern.
7. **Do not touch decision logic.** No gate, score, SL/TP or sizing code changes in this release. News rescan (F8) and any stale-comment fixes beyond the ones above are separate changes.
8. **Optional diagnostic switch.** A `#define ACE_EXPOSE_DIAG` that flips group J from `const` to `input` would keep diagnosis one recompile away. **[Guessing]** MetaEditor accepts a macro that expands to the `input` keyword, but I have not compiled it; prove it on a single constant first (Appendix B), and keep `InpAceV4DiagnosticBypassValidationGate` out of the switch.

---

## 8. Verification before shipping

1. **Compile** clean in MetaEditor (zero errors, no more warnings than v4.0.2).
2. **Parity backtest.** Same symbol, period, model and deposit as a stored v4.0.2 run, every visible input at its default. The v4.0.3 trade list (count, entry times, lots, SL, TP) must match v4.0.2 exactly, because no decision logic changed. Expected differences: magic number, the state-file tag if bumped, the profile log line at `ASE_StateMachine.mqh:1139-1141` (it now prints the global spread and bias values) and the new `[CFG]` line. Parity holds in `EVIDENCE` mode. At `CONDITIONAL` or `ACTIVE`, trades also depend on learned state, so compare only runs that start from identical (migrated) state.
3. **Inputs tab.** Exactly 48 inputs under 13 group headers. Count them.
4. **Preset round-trip.** Load an old v4.0.2 `.set`; confirm the Journal shows no error and the visible values apply.
5. **Live news check** (F8): after 48 hours attached, search the Journal for `[NEWS] Event registered`.

---

## 9. Hidden now, promote back when needed

| Input | Promote back when | Why it is hidden now |
|---|---|---|
| `InpAceV4EnableArch*` (5) | You run at CONDITIONAL or above and attribution shows one archetype losing | Kill switches with no effect below CONDITIONAL |
| `InpAceV4AuthValidatedMin` | You start the promotion decision | Count-only, unlike `InpAceV4AuthCautiousMin` (F7); the observation bar before V4 may execute |
| `InpAceV4GradeB/A/Plus` | You are at CONDITIONAL or above and want the grade floor as a lever | The config notes say do not hand-tune until Phase 6 Cluster A is complete |
| `InpMinBiasScore`, `InpMinSetupScore` | You want component floors beyond the per-regime score | Default 0 (off); overlaps the per-regime score |
| `InpBiasReEvalBars`, `InpBiasFlipCycles` | Diagnosing an all-day-silent EA | Bias-conflict block timers |
| `InpTP1Mode_*`, `InpTP2Mode_*` (8) | Running a structural-vs-ATR target A/B | Chosen per regime by design |
| `InpKillZoneEnabled` | Testing kill-zone scoring (10.0 vs 9.5) | Low leverage |
| `InpAceV4DiagnosticBypassValidationGate` | Never on real capital | Bypasses earned validation |

---

## 10. What I did not verify

- **Nothing was compiled or run.** This environment has no MT5 runtime, so the parity test in Section 8 is still to do.
- **`OnCalendarEvent` (F8).** The MQL5 reference was blocked by the network proxy; the claim rests on a search of the documented handler list and my own recall of it.
- **"No other path" (F5).** I read the authority, setup-veto, `BuildSetup` and execution regions of the state machine, not all 3,112 lines.
- **Preset behaviour (F9a, F9b).** Stated from general MT5 behaviour, not tested against your presets or dashboard.
- **The `ACE_EXPOSE_DIAG` macro (step 8)** is untested.
- **Repo context.** `ACE/ACE_CLAUDE.md` and `MEMORY.md` still describe v3.14.3 (last updated 2026-06-23), including a dynamic risk ladder (floor 5%, ceiling 30%), whereas v4.0.2 sizes every lot at the full `InpRiskPercent` (`ASE_RiskEngine.mqh:505`). They need a sync pass separate from this document.

---

## Appendix A: the proposed visible Inputs tab (48 inputs)

Defaults are identical to v4.0.2. Only the grouping and the comments changed. Every name, type and default in this block was machine-checked against `ASE_Config.mqh` and against the KEEP tables when this document was generated.

```mql5
//+------------------------------------------------------------------+
//| ACE (Adaptive Confluence Engine) v4.0.3 -- visible MT5 Inputs     |
//| 48 inputs. Everything else is a config-only const or deleted.     |
//+------------------------------------------------------------------+

input group "1. Sizing and exposure"
input double InpRiskPercent       = 0.50;  // Risk per trade, % of balance (full size always, no DD scaling)
input double InpMinRR             = 2.0;   // Min reward:risk; RR = TP2 distance / (ATR x 1.0). Below this the setup is rejected
input int    InpMaxPositions      = 1;     // Max concurrent positions for this magic number
input int    InpCooldownBars      = 5;     // M15 bars locked out after a close (5 = 75 min)

input group "2. Risk Guard (blocks NEW entries only; open trades keep being managed)"
input double InpRiskDailyLossPct     = 2.0;   // % equity loss vs day-start balance that blocks entries until next broker day (0=off)
input double InpRiskPauseDDPct       = 30.0;  // % equity drawdown from peak balance that blocks entries until next broker day (0=off)
input double InpRiskProbationDDPct   = 5.0;   // % drawdown from the post-pause resume peak that HALTS trading for human review (0=off)
input int    InpRiskGuardResetNonce  = 0;     // Halt reset: change to any new value and re-attach to clear a HALTED guard

input group "3. Exits"
input double InpATRMultiplierTP1   = 2.0;   // TP1 distance = ATR x this (ATR mode / ATR fallback only; structural TP1 ignores it)
input double InpATRMultiplierTP2   = 4.0;   // TP2 (runner) distance = ATR x this (same caveat); also the RR-gate numerator
input bool   InpPartialTPEnabled   = true;  // Close part of the position at TP1 (auto-skipped at/near min lot)
input double InpPartialTPPercent   = 50.0;  // % of the position closed at TP1
input bool   InpATRTrailEnabled    = true;  // ATR trailing stop on/off
input double InpATRTrailMultiplier = 1.5;   // Trail distance = ATR x this

input group "4. Regime profile: TRENDING"
input double InpSL_Trending        = 1.8;   // SL distance = ATR x this (before cap)
input double InpSLCap_Trending     = 15.0;  // Hard SL ceiling, price units (0=no cap)
input double InpScore_Trending     = 60.0;  // Min composite score (0-100) to enter

input group "5. Regime profile: RANGING"
input double InpSL_Ranging         = 2.4;   // SL distance = ATR x this (before cap)
input double InpSLCap_Ranging      = 20.0;  // Hard SL ceiling, price units (0=no cap)
input double InpScore_Ranging      = 55.0;  // Min composite score (0-100) to enter

input group "6. Regime profile: MANIPULATION"
input double InpSL_Manipulation    = 1.6;   // SL distance = ATR x this (before cap)
input double InpSLCap_Manipulation = 14.0;  // Hard SL ceiling, price units (0=no cap)
input double InpScore_Manipulation = 75.0;  // Min composite score (0-100) to enter

input group "7. Regime profile: COMPRESSION"
input int    InpCompressionMode    = 0;     // 0=no entries in COMPRESSION (breakout watch), 1=trade it with the config-only compression SL/cap/score

input group "8. Entry filters"
input int    InpMaxSpread            = 70;    // Hard spread ceiling, points
input bool   InpLiquidityConfirm     = true;  // Require liquidity confirmation before entry
input double InpSlippageGateATRMult  = 0.8;   // Abort if adverse drift trigger-bar-close to order exceeds this x M1 ATR (0=off)
input int    InpNewsBlockMinutes     = 0;     // Block entries +/- this many minutes around high-impact news (0=off; see F8)

input group "9. Setup and trigger filters"
input bool   InpEnableFVG                   = true;   // Allow FVG setups
input bool   InpEnableDisplacement          = true;   // Allow M15 displacement setups
input bool   InpEnableCompressionBO         = true;   // Allow compression-breakout setups
input bool   InpEnableEMAPullback           = true;   // Allow EMA-pullback setups
input bool   InpEMAFallbackInRanging        = false;  // Allow the EMA_Fallback trigger in RANGING
input bool   InpEMAFallbackInTrending       = false;  // Allow the EMA_Fallback trigger in TRENDING
input bool   InpWeakShortTriggersInTrending = false;  // Allow Rejection/Displacement triggers on SHORT in TRENDING (Disp+mBOS always allowed)

input group "10. Sessions (UTC windows are config-only)"
input bool   InpUseLondon     = true;   // Trade the London window (06:00-12:30 UTC = 08:00-14:30 SAST)
input bool   InpUseNY         = true;   // Trade the NY window (12:30-21:00 UTC = 14:30-23:00 SAST)
input bool   InpTrade24_7     = false;  // MASTER: trade 24/7 (bypasses the session filter)

input group "11. Structure"
input int    InpH1SwingPivot        = 2;    // Bars each side confirming an H1 swing pivot (2=standard, 3=conservative)
input double InpBiasInvalidATRMult  = 2.0;  // Adverse close (x H4 ATR) beyond the BOS that set the bias resets it to none (0=off)

input group "12. V4 authority"
input ENUM_ACE_V4_MODE InpAceV4Mode = ACEV4_EVIDENCE;  // LEGACY / EVIDENCE (learn, no authority) / ADVISORY / CONDITIONAL / ACTIVE
input bool   InpAceV4AllowBConditional = true;   // Let APEX_B qualify for authority (also needs separation >= 25, hard-coded); dormant below CONDITIONAL
input int    InpAceV4MinSeparation     = 15;     // Min directional score separation for a setup to qualify

input group "13. Operations"
input int    InpMagicNumber        = ASE_MAGIC_DEFAULT;  // EA magic number, 20XXXX convention (v4.0.3 = 204003)
input bool   InpAlertsEnabled      = false;  // MT5 push notifications on/off
input bool   InpStateLogEnabled    = true;   // Write the daily CSV state log (disable on live)
input bool   InpShowChartVisuals   = true;   // Pivot S/R rays, BOS markers, active-trade panel
input bool   InpShowV4Dashboard    = true;   // V4 status panel
```

---

## Appendix B: config-only pattern

```mql5
// ── CONFIG-ONLY (hidden from the MT5 Inputs tab) ─────────────────────
// Same names and values as v4.0.2. Edit here and recompile.
// Before (v4.0.2):  input double InpAceV4GradeB = 51.9;
const double InpAceV4GradeB = 51.9;   // min winning-direction confluence score for APEX_B

// Optional diagnostic switch (untested; prove on one constant first).
// Define in the main .mq5 above the #include chain to expose group J for a one-off diagnostic build.
// #define ACE_EXPOSE_DIAG
#ifdef ACE_EXPOSE_DIAG
   #define ACE_DIAG_INPUT input
#else
   #define ACE_DIAG_INPUT const
#endif
ACE_DIAG_INPUT ENUM_ACE_LOG_LEVEL InpAceV4LogLevel = LOG_NORMAL;   // printing only; never gates a decision
```

```mql5
// Config fingerprint: call once from OnInit() after the existing banner.
// MT5 tester reports list only `input` variables, so echo the config-only constants here.
// Extend mechanically from the Section 5 tables.
void ASE_PrintConfigFingerprint()
{
   Print("[CFG] ", ASE_VERSION_TAG,
         " | OOS=", InpAceV4OOSMode, "/", InpAceV4OOSEveryK,
         " | Grade=", DoubleToString(InpAceV4GradeB, 1), "/",
                      DoubleToString(InpAceV4GradeA, 1), "/",
                      DoubleToString(InpAceV4GradePlus, 1),
         " | TP Trending=", EnumToString(InpTP1Mode_Trending), "/", EnumToString(InpTP2Mode_Trending),
         " | ... remaining config-only constants ...");
}
```
