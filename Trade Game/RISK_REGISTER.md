# RISK_REGISTER.md — TradeWise Product Risk Register

**Version:** 1.0  
**Owner:** Masood  
**Purpose:** Identifies every material product risk, ranks them by severity, and prescribes specific mitigations that have been integrated into the delivery plan. Cross-referenced to ROADMAP.md milestones.

---

## Risk Scoring Methodology

Each risk is scored across three dimensions:

- **Probability (P):** How likely is this risk to materialise? 1 (unlikely) → 5 (near certain)
- **Impact (I):** If it materialises, how badly does it damage the product? 1 (minor) → 5 (fatal)
- **Detectability (D):** How late would the team discover this risk? 1 (caught early) → 5 (discovered post-launch)

**Risk Score = P × I × D**  
Maximum possible: 125. Ranked highest score first.

---

## Risk Register

---

### RISK-01: WebView Bridge Technical Failure
**Category:** Technical  
**Risk Score: 100** (P:5 × I:5 × D:4)

**Description:**  
The entire chart replay mechanic — the core of the product — depends on a React Native WebView hosting TradingView Lightweight Charts, with a bidirectional postMessage bridge handling playback control, pause signals, drawing tools, timeframe switching, and outcome detection. This architecture has never been prototyped for this product. If the bridge has unacceptable latency on Android, fails to render correctly offline, or cannot reliably communicate pause/resume events, the core loop is broken. Every other feature is built on top of this. Discovering this problem at week 8 of a 14-week build is catastrophic.

**Specific failure modes:**
- postMessage latency between WebView and RN > 200ms makes the pause mechanic feel broken
- TradingView Lightweight Charts renders incorrectly at mobile viewport sizes
- Android WebView handles offline bundled HTML differently to iOS WKWebView
- Memory pressure causes WebView to reload during a session, losing state
- Drawing tools (trendline, Fibonacci) require canvas interaction that conflicts with the WebView touch event model

**Current plan gap:**  
The Phase 0 prototype task exists but is a single checkbox with no pass/fail criteria and no fallback specification.

**Mitigation (integrated into ROADMAP.md Phase 0):**  
- Prototype expanded to a full 5-day spike with explicit exit criteria (see ROADMAP.md milestone 0.4)
- Spike must test: offline rendering, postMessage round-trip latency (<100ms target), drawing tool touch interaction, memory under 60-minute continuous use, and Android vs iOS parity
- A complete fallback architecture (Victory Native XL) must be evaluated in parallel during the spike — not after failure
- If the WebView bridge passes all criteria: proceed to Phase 1 build
- If the WebView bridge fails any criterion: switch to Victory Native XL immediately. The architectural decision is made in Phase 0, not discovered mid-build.
- Victory Native XL evaluation checklist added to Phase 0 (see ROADMAP.md milestone 0.4b)

---

### RISK-02: Dataset Quality Invalidates the Educational Premise
**Category:** Content / Product  
**Risk Score: 90** (P:5 × I:5 × D:3 — but D is 3 because beta users surface this)

**Description:**  
Every trade decision in Career Mode and Arcade Mode is evaluated against pre-tagged decision points. The quality of those tags determines whether the app actually teaches trading or just teaches users to score points in an arbitrary system. If the `correct_direction` tags are wrong, the coaching cards teach incorrect behaviour, the scoring rewards bad trades, and users internalise false patterns. This is not a bug — it is a product integrity failure that could actively harm users who go on to trade real money.

Specific risks:
- A setup tagged as a valid BUY is actually counter-trend on the 1H — the tag is wrong
- A trap setup is tagged incorrectly, penalising users for taking a valid trade
- All 20 MVP datasets are curated by someone who codes well but doesn't trade — the tag methodology is technically correct but commercially invalid
- The coaching card text is written without reference to actual market behaviour, creating explanations that sound plausible but are subtly wrong

**Current plan gap:**  
The plan mentions "reviewed by a trader who actively trades these setups" as a single checkbox in Phase 0. No specification of the review process, no minimum review standard, and no ongoing quality gate for new datasets.

**Mitigation (integrated into ROADMAP.md and CONTENT_SPEC.md):**  
- All datasets must pass a two-stage validation before being marked `active = true` in the database (see CONTENT_SPEC.md Section 4, updated)
- Stage 1: Technical tag review (schema compliance, no null required fields, candle indices valid)
- Stage 2: Trading validity review — a qualified trader must replay each dataset manually and confirm: (a) the correct_direction is sound at each decision point, (b) the trap setups are genuinely ambiguous or invalid, (c) the coaching text accurately describes the setup. Sign-off logged.
- Minimum 2 independent trading reviews for any dataset used in Stage 1 (beginner-facing) content — the stakes of a wrong lesson are highest at Stage 1
- Dataset validation checklist added to CONTENT_SPEC.md (see Section 4)
- Launch gate: Phase 1.20 (beta QA) now requires 5 beta users who are active traders to complete 10+ Career Mode sessions and rate coaching card accuracy. Minimum 4/5 must rate coaching as "accurate" before launch approval

---

### RISK-03: Early Churn from $500 Blow-Up Rate
**Category:** Retention / Product  
**Risk Score: 80** (P:4 × I:5 × D:4)

**Description:**  
New traders — the primary audience — will blow their $500 Practice Capital. That is the educational point. But the rate at which they do it, and the emotional experience when it happens, determines whether they engage with the Soft Restart or uninstall.

The plan has a blow-up mechanic but no modelling of what the actual blow-up rate will be. If 60% of new users hit the Soft Restart in their first 10 sessions — before they've engaged deeply enough with the product to care about restarting — the loss moment is pure frustration, not a meaningful game event. The narrative frame ("your knowledge stays with you") only lands if the user has accumulated enough knowledge to feel that.

Additional risk: the $250 loan resets leverage to Developing tier (1:20). At $250 with 1:20 leverage, a standard 50-pip SL on 0.05 lots = $25 at risk = 10% of the loan. Three bad trades wipes the loan. If the Soft Restart just accelerates the blow-up, it creates a doom loop rather than a recovery arc.

**Current plan gap:**  
No modelling of expected blow-up timing. No safeguards against the doom loop on the loan. No alternative career entry point for users who blow up before they've completed the learning module.

**Mitigation:**  
- Pre-launch: model expected sessions-to-blow-up using the pip value maths. At Stage 1 (conservative lot sizing), what is the realistic number of sessions before a run of losses wipes $500? This number must be above 20 sessions before the product ships.
- If modelling shows expected blow-up < 20 sessions at Stage 1 defaults: increase starting capital to $1,000 or reduce Stage 1 lot size options further. Decision must be made in Phase 0, not post-launch.
- Doom loop protection: if Practice Capital on the Soft Restart loan falls below $100 within 5 sessions of the restart, the app surfaces a mandatory "Trading Pause" screen — a 3-slide refresher on risk management — before the next session can begin. This is not optional. It breaks the doom loop with education rather than a hard stop.
- Learning module gate enforced before any Career Mode session on a new Soft Restart. If the user skipped the learning module before blowing their first account, the Soft Restart mandates completion before the $250 loan is available.
- PostHog event tracking added: `career_mode_blown`, `soft_restart_initiated`, `soft_restart_loan_at_risk` (triggered at <$100 on loan), `soft_restart_blown`. These four events are the primary health metrics for the first 30 days post-launch.

---

### RISK-04: TradePoints Economy Exploits and Imbalance
**Category:** Economy / Integrity  
**Risk Score: 72** (P:4 × I:4 × D:5 — D is 5 because exploits are found post-launch by players, not testing)

**Description:**  
The TradePoints economy has multiple earning sources: Career Mode wins, Arcade correct answers, weekly growth bonuses, one-time module completions, milestone bonuses, and badge awards. The economy has not been modelled mathematically. Without a model, the following risks are undetectable until post-launch:

- An Arcade grinding exploit: a user plays Easy mode Arcade with 10 setup identification challenges, all trivially correct, earning +50 TradePoints per session in ~3 minutes. At 10 sessions/day: 500 TradePoints/day. Hitting Elite tier (30,000 TP) takes 60 days of grinding with zero Career Mode engagement. The leaderboard is gamed by volume, not skill.
- Weekly growth bonus manipulation: a user starts the week with $500, runs the account to $600 (20% growth = +300 TradePoints), then deliberately takes losses to return to $500 before the next weekly snapshot. They repeat this every week for pure TradePoints without genuine account growth.
- Streak multiplier stacking: a carefully curated dataset selection (if users can influence dataset choice) allows cherry-picking easy setups during a streak, then accepting neutral outcomes to preserve the streak indefinitely.

**Current plan gap:**  
Economy health checks exist in GAME_DESIGN.md but are post-launch monitoring signals. There is no pre-launch economy model and no exploit analysis.

**Mitigation:**  
- Economy model spreadsheet built in Phase 0 (see ROADMAP.md milestone 0.6, added): models max daily TradePoints across all earning sources under normal play vs exploit scenarios. If any exploit path reaches Elite tier in <90 days without Career Mode engagement, the earning rates must be rebalanced before Phase 1 build begins.
- Arcade earning rate cap: maximum 200 TradePoints per day from Arcade Mode regardless of sessions played. Implemented as a daily cap in the `resolve_arcade_answer` Edge Function. Excess points from sessions beyond the cap are displayed as "Daily Arcade limit reached — see you tomorrow."
- Weekly growth bonus: change snapshot basis from absolute capital to sessions-adjusted capital. If the user has completed fewer than 3 sessions in the prior week, no growth bonus is awarded (prevents weekend grinding for the bonus then abandoning the account).
- Dataset selection: users do not choose datasets. Datasets are assigned by the server based on stage and market condition rotation. No cherry-picking.
- Neutral outcomes: confirm in the game engine that neutral outcomes do NOT preserve the streak. A neutral is treated as a streak pause (streak counter frozen, not reset, not advanced). This closes the cherry-picking-for-neutrals path.
- Economy audit added to Phase 1.20 QA criteria: 20 internal sessions of attempted exploit play across each identified exploit path. None should reach Elite tier in < 90 days equivalent.

---

### RISK-05: App Store Rejection — Finance/Gambling Classification
**Category:** Regulatory / Launch  
**Risk Score: 64** (P:4 × I:4 × D:4)

**Description:**  
Apple App Store and Google Play Store both have elevated review scrutiny for apps touching financial trading, simulated gambling, and investment content. An app that depicts candlestick charts, simulates account blow-ups, uses leverage, and contains the word "trading" prominently is likely to trigger manual review. If the App Store classifies TradeWise as a financial services app, it may require additional documentation, a specific category, or modifications to the app before approval. In the worst case, a rejection during the final weeks of Phase 1 adds 4–8 weeks to the launch timeline.

Specific risks:
- The term "leverage" in any context can trigger financial services review on Apple
- The blow-up / loan mechanic could be classified as simulated gambling
- "TradePoints" as a virtual currency could be flagged if Apple's automated systems pattern-match it to virtual casino currency
- Google Play's "Real-Money Gambling, Games, and Contests" policy could catch the Competitions feature even in its in-app-rewards-only form

**Current plan gap:**  
App Store category and age rating confirmation is a single checkbox in Phase 0.5. There is no App Store pre-submission consultation or rejection contingency.

**Mitigation:**  
- Pre-submission: consult Apple's App Review team via the App Review Support page before submitting the first build. This is a legitimate channel and reduces rejection probability significantly. Do this in Phase 0 with a clear product description.
- App metadata (name, subtitle, description, screenshots) reviewed against App Store Review Guidelines 5.2 (financial), 5.3 (gambling) before submission. Added to Phase 0.5 checklist.
- The phrases "leverage" and "margin call" in any marketing material or App Store description are replaced with "trading power multiplier" and "account protection limit" in App Store metadata only (in-app language unchanged — it is educational and uses correct terminology).
- Rejection contingency: if rejected, a 2-week remediation sprint is allocated in the ROADMAP.md Phase 1 → launch buffer. The launch date is not committed publicly until App Store approval is in hand.
- Google Play: submit to Internal Testing track first (no review required). Use the 2-week TestFlight beta to gather feedback while awaiting Google Play full review. Parallel tracks reduce total calendar time.

---

### RISK-06: Offline/Online Sync Conflict Corrupts Economy State
**Category:** Technical / Integrity  
**Risk Score: 60** (P:3 × I:5 × D:4)

**Description:**  
The app is designed to run sessions offline with server sync on reconnect. This is the right architecture for gameplay continuity, but it creates a window where the client and server hold different state. Specific corruption vectors:

- User completes an offline session (3 trades, earns +50 TradePoints). Before sync, they open the app on a second device (or the session times out). The server has no record of those trades. The client syncs and the server accepts the queue — but if the server's authoritative state has changed (e.g. a Soft Restart was triggered on another device), the sync creates a contradiction.
- The pending sync queue writes to SQLite. If the app crashes during a session, the queue may be incomplete — half the trades are queued, half are not.
- A user deliberately force-closes the app after seeing a winning outcome but before the sync fires, hoping to replay the session if the outcome was bad. The server has no record, so the outcome is not awarded — but the user expects it to be.

**Current plan gap:**  
The sync architecture exists in ARCHITECTURE.md but the conflict resolution rules are a single line ("server wins"). There is no specification of what happens to the pending queue if the server state has changed since the queue was built.

**Mitigation:**  
- Each pending trade resolution in the queue includes a `career_life_id` and `capital_before_cents` snapshot taken at the moment of the trade commitment. The `resolve_trade` Edge Function validates that the `capital_before_cents` in the queue matches the current authoritative capital in `career_lives` before processing. If it doesn't match: the trade is logged as `status: 'conflict'` and skipped. The user sees a notification: "One trade outcome couldn't be confirmed. Your account has been updated to its last confirmed state."
- Session replay prevention: the server marks each `career_session` as `status: 'active'` on start. A session can only be resolved once. If a duplicate session resolution arrives (user replaying a session by crash-restoring): the second resolution is rejected with a duplicate session error.
- SQLite write-ahead logging (WAL mode) enabled in expo-sqlite to prevent partial writes on crash.
- Conflict resolution added explicitly to DATA_SCHEMA.md trades table: new column `sync_status` with enum: `pending`, `synced`, `conflict`. Conflict trades are visible in an admin view (PostHog event + Supabase dashboard query) for monitoring.
- Acceptance criterion in Phase 1.20 QA: simulate offline session → server state change → reconnect sync for all conflict scenarios. All must result in no net economy gain from the conflict.

---

### RISK-07: Monetisation Model Generates Insufficient Revenue Pre-Scale
**Category:** Business / Sustainability  
**Risk Score: 56** (P:4 × I:4 × D:3 — detectable when early revenue figures come in)

**Description:**  
The product has removed ads and is relying on IAP and subscriptions with no ads as fallback. The revenue projections in MONETISATION.md show ~$1,300/month at conservative scale (10,000 MAU). At 10,000 MAU, the cost to acquire those users through any paid channel will likely exceed monthly revenue. The model requires significant organic growth to be viable in the early period.

The subscription value proposition is genuine but the IAP catalogue is underdeveloped for a user who isn't ready to subscribe. The gap between "free user" and "Pro subscriber" has very few stepping stones — a user who finds the free tier good enough will never find a natural reason to spend $1.99 on an avatar pack.

**Current plan gap:**  
Revenue projections exist but no user acquisition cost model. No minimum viable revenue threshold defined. No plan for what happens if the model underperforms at 6 months.

**Mitigation:**  
- Define a minimum viable revenue threshold before launch: at 6 months post-launch, the product must be generating sufficient revenue to cover Supabase infrastructure, RevenueCat fees, and at least 1 part-time developer for ongoing maintenance. This number must be calculated and committed to. If projections suggest it won't be hit, either the cost base must be reduced or the monetisation model must change before launch, not after.
- Add a "starter" IAP priced at $0.99 — a single cosmetic item (chart background or badge frame). A $0.99 purchase has 3–5× the conversion rate of a $4.99 purchase for first-time IAP buyers. It breaks the payment inertia. Users who have purchased once are significantly more likely to purchase again. This is the most important addition to the monetisation model and should be added to MONETISATION.md immediately.
- The Pro trial (7 days) is the most important conversion mechanic. Every free user flow should surface the trial offer exactly once — at the moment of highest value (first milestone badge earned, or first session complete). Not on first launch. The right moment is when the user has already decided they like the product.
- Track "Pro trial started" and "Pro trial converted" as primary business metrics from day 1. If trial-to-paid conversion is below 25% (industry benchmark for well-positioned trials), investigate immediately.
- 6-month revenue review: if revenue is below minimum viable threshold, escalate to Masood with three options: (a) add optional video reward ads (single opt-in, not interstitial), (b) introduce a premium content paywall for advanced datasets, (c) reduce infrastructure costs. Decision made at that point, not improvised.

---

### RISK-08: Cross-App Identity Failure Blocks Ecosystem Progression
**Category:** Technical / Product  
**Risk Score: 48** (P:3 × I:4 × D:4)

**Description:**  
The entire three-app ecosystem depends on a single Supabase project with shared Apple ID / Google ID authentication. If this cross-app auth doesn't work seamlessly — if a user's PropWise session doesn't immediately recognise their TradeWise identity — the mini-game transfer mechanic breaks, and the PropWise/CompWise ecosystem value proposition disappears.

Specific failure modes:
- Apple ID → Supabase auth on TradeWise returns a different UUID than the same Apple ID → Supabase auth on PropWise (this can happen if Supabase project is configured differently or if the Apple app bundle IDs are not both registered in the same Supabase project's auth settings)
- A user changes their Apple ID or Google account between apps — their TradeWise progress and PropWise app become unlinked with no recovery path
- The 48-hour fund transfer is processing when the user uninstalls TradeWise. The transfer is in `pending` status in the database. The user reinstalls, but the pending transfer may not be surfaced correctly.

**Current plan gap:**  
The cross-app auth test exists in Phase 0 (one checkbox) but the failure recovery paths are not documented.

**Mitigation:**  
- Phase 0 cross-app auth test expanded: must test with same Apple ID across two separate Expo builds on two separate devices. Must confirm same Supabase UUID is returned both times. Must test with same Google ID. Must test account link change (user changes Google account mid-session) and confirm graceful error, not silent failure.
- Account recovery path documented and built: if a user's linked identity changes, they can re-link by proving ownership of the original account (email verification to the registered email). This path must exist before launch, even if it is manual (support email in MVP, automated in Post-MVP).
- Pending transfers survive app uninstall: transfers are in Supabase (server-side). On reinstall and re-auth, the transfer history screen shows pending transfers and their status. No transfer is lost due to client state.
- Added to Phase 1.19 (offline support) QA: test the pending transfer → app uninstall → reinstall → transfer status display flow explicitly.

---

### RISK-09: Content Volume Insufficient for Long-Term Retention
**Category:** Content / Retention  
**Risk Score: 45** (P:5 × I:3 × D:3)

**Description:**  
The MVP launches with 20 datasets and approximately 60–100 unique decision points. A user who plays 4 sessions per week will exhaust the dataset pool in roughly 5–10 weeks if datasets are not carefully rotated to minimise repetition. Once users start seeing familiar chart patterns, the educational value collapses (they're recognising the dataset, not the setup) and the engagement value collapses (it's not interesting to replay a chart you've seen).

This is near-certain to happen. It is not a risk that can be mitigated by better design — only by more content.

**Current plan gap:**  
No content refresh cadence. No mechanism to detect when a user has seen too many repetitions of a dataset. No pipeline for ongoing dataset production post-launch.

**Mitigation:**  
- Increase MVP minimum dataset pool: from 20 to 35 datasets with 90+ unique decision points. The additional cost in curation time is justified by the retention extension it provides (adds approximately 3–4 weeks of non-repetitive play for a 4-sessions/week user).
- Dataset repetition tracking: add `dataset_exposures` table (user_id, dataset_id, last_seen_at, times_seen). Before assigning a dataset to a session, the server checks times_seen for that user. If times_seen ≥ 3 for all available datasets in the user's stage: the server flags this and selects the least-recently-seen dataset. A notification is sent to Masood (PostHog alert) so new datasets are prioritised.
- Content pipeline: commit to a minimum of 5 new datasets per month post-launch. This is a content production task (not engineering) and can be done by anyone trained on the decision-point tagging process. Dataset production cost must be included in the operational budget.
- Instrument expansion (Phase 3) is the structural solution to this problem. XAUUSD and BTCUSD datasets triple the available content pool and are visually distinct enough that a user won't confuse them with EURUSD datasets. Phase 3 must be treated as a retention-critical deliverable, not a nice-to-have.

---

### RISK-10: Learning Module Completion Rate Too Low to Drive Career Mode Engagement
**Category:** Product / Retention  
**Risk Score: 40** (P:4 × I:2 × D:3 — lower impact because Arcade Mode provides an alternative path)

**Description:**  
The plan requires Beginner users to complete the learning module before accessing Career Mode. Industry data on in-app course completion rates is grim: even mandatory modules see 30–50% abandonment in the first three sections. If a Beginner user hits the learning module gate and abandons before completion, they never reach Career Mode — the core product. They become a same-day churn.

Amateur and Professional users defer the module and may never complete it — arriving at Career Mode without the risk management vocabulary the coaching cards assume they have.

**Current plan gap:**  
No measurement of learning module abandonment by section. No intervention for users who abandon mid-module. Module is "mandatory" for Beginners but there is no recovery path designed for the abandonment case.

**Mitigation:**  
- Track `learning_module_section_started` and `learning_module_section_completed` as PostHog events for every section. The section with the highest abandonment rate is identified within 2 weeks of launch and redesigned (shorter, more visual, less text-dense). Commit to fixing the highest-abandonment section before week 4 post-launch.
- For Beginners who abandon the module mid-way: after 48 hours of inactivity, a push notification fires: "Your trading career is waiting. Pick up where you left off." (One notification only — not a spam sequence.)
- Add a "preview" mechanic: Beginner users can watch a single 2-minute Arcade Mode Easy session (read-only, no points earned) before being required to complete the module. This gives them a taste of the product before the educational barrier. Converts the module from "gate before the fun" to "prerequisite that makes the fun better." This single change is likely to increase module completion rates by 15–20%.
- Risk management module completion: surface the standalone risk management module as a side quest for all users ("Complete the Risk Management module — earn 50 TradePoints"). Quest-driven completion outperforms mandatory completion for non-Beginners.

---

### RISK-11: Regulatory Action Post-Launch (Financial Services or Gambling)
**Category:** Regulatory / Existential  
**Risk Score: 36** (P:2 × I:5 × D:4 — low probability if pre-launch legal review is done; catastrophic if not)

**Description:**  
If the South African FSCA, UK FCA, or EU ESMA issues an enforcement action against TradeWise post-launch, the consequences include: forced app removal, fines, reputational damage, and potential personal liability. This is a low-probability risk given the product classification (simulated education, no real money) but a high-consequence one.

The main triggers that could elevate probability post-launch:
- Competitions with cash prizes launched without legal clearance
- Marketing materials that frame TradeWise as a path to profitable live trading
- The broker referral mechanic (Post-MVP) implemented without jurisdiction-specific authorisation

**Current plan gap:**  
Legal review is initiated in Phase 0 but there is no ongoing compliance process for post-launch feature additions.

**Mitigation:**  
- Pre-launch: South African FAIS + gambling legal opinion obtained and on file before app goes live. This is a hard gate, not a soft recommendation.
- Cash prizes: build gate in REGULATORY_NOTES.md is a hard gate. No cash prizes ship without all legal clearances in REGULATORY_NOTES.md Section 4 checked.
- Marketing review process: all marketing copy (App Store description, social media, paid ads) reviewed against the legal opinion before publication. One marketing review checkpoint per quarter post-launch.
- Post-launch compliance audit: at 6 months post-launch, a second legal review of the app's actual implemented features (not the design documents) is commissioned. Apps evolve; the legal picture must stay current.
- Incident response plan: if a regulatory inquiry arrives, TradeWise's response is (a) cease any flagged feature immediately, (b) engage the same legal advisor who provided the original opinion, (c) do not communicate publicly until legal advice is received. This plan is documented and Masood is the named decision-maker.

---

### RISK-12: Mini-Game Return Mechanics Create Unrealistic Investment Expectations
**Category:** Product / Regulatory  
**Risk Score: 30** (P:3 × I:2 × D:5)

**Description:**  
PropWise and CompWise mini-games generate simulated monthly returns. If those return rates are unrealistically high — "your residential property returned 8% this month" — users may internalise those rates as real-world benchmarks and make poor real-world investment decisions. This is a softer version of the same risk the core trading simulator faces: simulated performance creating false expectations of real performance.

**Current plan gap:**  
Return rates for PropWise and CompWise mini-games are undefined. "Simplified market cycles" is not a specification.

**Mitigation:**  
- PropWise return rates capped at realistic long-term property return averages: Residential 0.5–0.8% per month (6–10% annually), Commercial 0.6–1.0%, Industrial 0.7–1.2%. These are not guaranteed — they vary by a ±30% random factor each cycle to simulate market variation.
- CompWise return rates: similarly benchmarked to realistic small business revenue multiples on investment. Not specified as guaranteed returns.
- Disclaimer on all mini-game return displays (already in REGULATORY_NOTES.md placement table): "Simulated returns — not real investment performance."
- The mini-game mechanics document (to be written when Phase 1b begins) must include a "return rate rationale" section that justifies the rates chosen against real-world benchmarks.

---

## Risk Summary Table

| Rank | Risk ID | Description | Score | Primary Mitigation |
|---|---|---|---|---|
| 1 | RISK-01 | WebView bridge technical failure | 100 | 5-day spike with exit criteria + fallback architecture evaluated in parallel |
| 2 | RISK-02 | Dataset quality invalidates educational premise | 90 | Two-stage validation + trader sign-off + beta trader review gate |
| 3 | RISK-03 | Early churn from $500 blow-up rate | 80 | Capital model pre-launch + doom loop protection + learning gate on Soft Restart |
| 4 | RISK-04 | TradePoints economy exploits | 72 | Economy model spreadsheet + Arcade daily cap + dataset not user-selectable |
| 5 | RISK-05 | App Store rejection | 64 | Pre-submission Apple consultation + rejection contingency buffer in ROADMAP |
| 6 | RISK-06 | Offline/online sync conflict corrupts economy | 60 | Capital snapshot validation in Edge Function + session replay prevention |
| 7 | RISK-07 | Insufficient revenue pre-scale | 56 | $0.99 IAP entry point + minimum viable revenue threshold + 6-month review trigger |
| 8 | RISK-08 | Cross-app identity failure | 48 | Expanded auth test + account recovery path + pending transfer survival |
| 9 | RISK-09 | Content volume insufficient for retention | 45 | 35 dataset MVP minimum + repetition tracking + 5 datasets/month pipeline |
| 10 | RISK-10 | Learning module completion too low | 40 | Section abandonment tracking + preview mechanic + quest-driven completion |
| 11 | RISK-11 | Regulatory action post-launch | 36 | Hard legal gate pre-launch + ongoing compliance audit at 6 months |
| 12 | RISK-12 | Mini-game returns create false expectations | 30 | Realistic rate caps + benchmarked rationale + persistent disclaimer |
