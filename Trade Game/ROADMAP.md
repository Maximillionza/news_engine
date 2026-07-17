# ROADMAP.md — TradeWise Delivery Roadmap

**Version:** 0.3 (Risk-hardened)  
**Owner:** Masood  
**Change from v0.2:** All mitigations from RISK_REGISTER.md integrated as explicit checkboxes. New milestones 0.6 (economy model) and 0.7 (App Store pre-submission) added. Phase 1 exit criteria tightened. Launch buffer added.

---

## Phase 0 — Foundation (Pre-Build) ← YOU ARE HERE

**Goal:** All documents complete. Tech stack validated with explicit exit criteria. Dataset pool curated AND trader-validated. Economy modelled mathematically. Legal initiated. App Store pre-consulted. No production code written until all Phase 0 gates pass.

---

### 0.1 — Documentation
- [x] CLAUDE.md
- [x] PRD.md
- [x] GAME_DESIGN.md
- [x] LEARNING_THEORY.md
- [x] MONETISATION.md
- [x] FEATURE_SPEC.md
- [x] DATA_SCHEMA.md
- [x] ARCHITECTURE.md
- [x] CONTENT_SPEC.md
- [x] REGULATORY_NOTES.md
- [x] ROADMAP.md
- [x] RISK_REGISTER.md

---

### 0.2 — Content Validation
*Mitigates: RISK-02 (dataset quality), RISK-09 (content volume)*

- [ ] CONTENT_SPEC.md reviewed by Trader A (actively trades all 5 setups)
- [ ] CONTENT_SPEC.md reviewed by Trader B (independent second opinion — minimum Amateur level)
- [ ] All 5 confluence setup definitions confirmed as technically sound
- [ ] All 6 trap setup types confirmed as genuinely ambiguous/invalid (not just hard setups)
- [ ] Coaching card template finalised with at least 10 decision points written end-to-end
- [ ] Arcade challenge pool: minimum 30 candlestick pattern entries, 20 reversal/pullback entries, 15 Bollinger Band entries — all trader-reviewed
- [ ] Return rates for PropWise and CompWise mini-games benchmarked against real-world data and documented (RISK-12)

---

### 0.3 — Dataset Curation (MVP Minimum)
*Mitigates: RISK-02 (dataset quality), RISK-09 (content volume)*

**Increased from 20 to 35 datasets based on RISK-09 analysis.**

- [ ] Source 180+ days of EURUSD 5-minute OHLCV data (Dukascopy or HistData)
- [ ] Tag 35 datasets using decision_points schema in DATA_SCHEMA.md
- [ ] 90+ unique decision points tagged across all datasets
- [ ] **Two-stage validation for every dataset before marking active = true:**
  - [ ] Stage 1 (technical): schema compliance, no null required fields, candle indices sequential and valid, SL/TP pips numerically sensible
  - [ ] Stage 2 (trading): qualified trader manually replays each dataset, confirms correct_direction at each decision point, confirms trap setups are genuinely invalid, confirms coaching text accurately describes the setup. Sign-off logged with date and trader name.
- [ ] At least 2 independent trader reviews for all Stage-1-facing datasets (beginner content)
- [ ] At least 4 datasets per market condition (trending_up, trending_down, ranging, compression, high_vol)
- [ ] At least 4 pure Stage-1 datasets (zero traps, unambiguous setups)
- [ ] At least 5 trap-heavy sessions (is_trap_session = true)
- [ ] Datasets converted to app-ready JSON format
- [ ] Dataset file sizes checked (target <15MB per dataset, hard limit 20MB)
- [ ] Total storage budget calculated: 35 datasets × average size ≤ 200MB target

---

### 0.4 — Tech Stack Validation: WebView Bridge Spike
*Mitigates: RISK-01 (WebView bridge failure) — highest risk item in the entire plan*

**This is the single most critical Phase 0 task. No Phase 1 build begins until this spike produces a pass or a confirmed fallback decision.**

**Duration: 5 business days maximum.**

**Spike deliverable:** A working prototype (not production quality) that:
- Loads 500 OHLCV candles from a local JSON file
- Renders them as a candlestick chart in a React Native WebView using TradingView Lightweight Charts
- Plays through candles at 5× speed
- Pauses at a hardcoded candle index via postMessage
- Receives the pause signal in React Native and changes a UI element
- Resumes playback via postMessage from React Native
- Draws a horizontal line at a specified price level
- All of the above: tested on a physical iOS device AND a physical Android device

**Exit criteria — ALL must pass:**
- [ ] Chart renders correctly on iOS (WKWebView)
- [ ] Chart renders correctly on Android (Chromium WebView)
- [ ] postMessage round-trip latency: < 100ms measured across 10 samples on each platform
- [ ] Offline rendering confirmed: airplane mode enabled before chart loads — chart must render from bundled HTML + local JSON
- [ ] Memory stable: 30-minute continuous playback session on each platform — no WebView reload
- [ ] Touch interaction on horizontal line drawing tool does not conflict with chart scroll (the biggest known risk on Android)
- [ ] Timeframe switching (swap from 5M candles to 1H candles) via postMessage without chart reload

**If any exit criterion fails on either platform:**

**0.4b — Fallback Evaluation (Victory Native XL)**
- [ ] Victory Native XL installed and rendering the same 500 candles on both platforms
- [ ] Candlestick chart type confirmed available in Victory Native XL
- [ ] Custom line drawing (horizontal line, trendline) confirmed achievable in Victory Native XL
- [ ] Fibonacci retracement: confirmed achievable or acceptable substitute designed
- [ ] If Victory Native XL passes: architecture decision logged, ARCHITECTURE.md updated, Phase 1 build proceeds with Victory Native XL
- [ ] If Victory Native XL also fails: escalate to Masood immediately. Phase 1 cannot begin without a confirmed chart rendering solution.

---

### 0.5 — Infrastructure Setup
*Mitigates: RISK-08 (cross-app identity), RISK-06 (sync conflicts)*

- [ ] Supabase project created (dev environment)
- [ ] Supabase project created (staging environment — separate from dev)
- [ ] **Cross-app auth test (expanded from v0.2):**
  - [ ] TradeWise Expo build: Sign in with Apple → record Supabase UUID
  - [ ] Second Expo build (simulating PropWise): Sign in with same Apple ID → confirm identical Supabase UUID returned
  - [ ] Repeat with Google ID
  - [ ] Test: user changes linked Google account mid-session — confirm graceful error, not silent failure or data corruption
  - [ ] Test: pending fund transfer in database → app uninstall → reinstall → transfer status visible on profile screen
- [ ] Expo project scaffolded, all production dependencies installed, dev build running on physical iOS device
- [ ] Expo project scaffolded, dev build running on physical Android device
- [ ] RevenueCat: account created, test IAP products configured in App Store Connect sandbox AND Google Play sandbox
- [ ] RevenueCat: webhook endpoint deployed (Supabase Edge Function), test event received and subscription table updated

---

### 0.6 — Economy Model (NEW — mitigates RISK-04)
*Mitigates: RISK-04 (economy exploits), RISK-07 (revenue pre-scale)*

**A spreadsheet model must be built and reviewed before any economy-touching code is written.**

- [ ] Economy model spreadsheet created covering:
  - [ ] Normal play scenario: 4 Career Mode sessions/week, 50% win rate, no Arcade. TradePoints accumulated per week and time-to-Elite-tier calculated.
  - [ ] Arcade grind scenario: 10 Arcade Easy sessions/day, zero Career Mode. TradePoints accumulated per day and time-to-Elite-tier calculated.
  - [ ] Weekly growth bonus exploit scenario: deliberate capital manipulation as described in RISK-04. TradePoints gained per week calculated.
  - [ ] Maximum theoretical daily TradePoints across all sources combined
- [ ] **Exit criteria — ALL must pass before economy is built:**
  - [ ] Normal play reaches Elite tier in 90–180 days (too fast = no long-term progression; too slow = demoralising)
  - [ ] Arcade grind scenario: time-to-Elite-tier ≥ 180 days WITHOUT the daily cap. If < 180 days: daily Arcade TradePoints cap set at 200 and modelled again. Cap value must be confirmed before Phase 1.4 (economy build).
  - [ ] Weekly growth bonus exploit: if the exploit yields > 50% more TradePoints per week than normal play, the snapshot basis must be changed (minimum 3 sessions in the prior week). Model both versions.
- [ ] Economy model reviewed and signed off by Masood before Phase 1 begins
- [ ] Minimum viable revenue threshold calculated (see RISK-07 mitigation): monthly revenue required to cover infrastructure + 1 part-time developer at 6 months post-launch. Number documented. If projections don't reach it by month 6: pre-agreed response options documented.
- [ ] $0.99 IAP entry point (single cosmetic item) added to MONETISATION.md and RevenueCat product catalogue

---

### 0.7 — App Store Pre-Consultation (NEW — mitigates RISK-05)
*Mitigates: RISK-05 (App Store rejection)*

- [ ] App Store Review Support consultation submitted (describe TradeWise, ask for category guidance and flag potential review flags proactively)
- [ ] App Store metadata draft prepared: name, subtitle, description, keywords, age rating rationale
- [ ] App Store description reviewed against Review Guidelines 5.2 (financial) and 5.3 (gambling) — zero flags
- [ ] Terms "leverage", "margin call" replaced in App Store metadata only with safer equivalents (in-app language unchanged)
- [ ] Google Play: equivalent policy review against "Real-Money Gambling" policy
- [ ] Rejection contingency: 2-week remediation sprint added to Phase 1 → launch timeline buffer (see Phase 1 header)

---

### 0.8 — Capital Blow-Up Modelling (NEW — mitigates RISK-03)
*Mitigates: RISK-03 (early churn from blow-up)*

- [ ] Pip value maths for Stage 1 lot sizes calculated:
  - Conservative lot (0.01): SL at 50 pips = $5 risk per trade
  - Moderate lot (0.05): SL at 50 pips = $25 risk per trade
  - Aggressive lot (0.10): SL at 50 pips = $50 risk per trade
- [ ] Worst-case blow-up scenario modelled: user always selects Aggressive lot, loses 10 consecutive trades. Capital remaining: $500 − (10 × $50) = $0. Sessions to blow-up: 2–3 sessions (unacceptable).
- [ ] **Exit criteria:**
  - [ ] At Stage 1 default lot sizing, a user cannot blow their account in fewer than 15 sessions even under a worst-case losing scenario
  - [ ] If worst-case blow-up < 15 sessions: either (a) remove Aggressive lot from Stage 1 options OR (b) increase starting capital. Decision documented and PRD.md updated before Phase 1.
- [ ] Doom loop protection mechanic designed and added to PRD.md: if Practice Capital on Soft Restart loan falls below $100 within 5 sessions, mandatory 3-slide risk management refresher shown before next session
- [ ] Learning module gate on Soft Restart confirmed in PRD.md: users who skipped the module before blow-up must complete it before the $250 loan is issued

---

### 0.9 — Legal Initiation
*Mitigates: RISK-11 (regulatory action)*

- [ ] South Africa: FAIS + gambling legal opinion instructed (attorney engaged, retainer paid)
- [ ] Target delivery: legal opinion received before Phase 1.20 (beta launch). Hard gate: app does not go live without this opinion.
- [ ] App Store category and age rating confirmed: Education, 17+
- [ ] Play Store category confirmed

---

**Phase 0 Gate: ALL 0.1–0.9 milestones complete before a single line of Phase 1 production code is written.**

---

## Phase 1 — MVP Build

**Goal:** Shippable app with Career Mode, Arcade Mode, learning module, mini-game tab shells, IAP, and subscription.

**Estimated duration:** 12–16 weeks + 2-week App Store submission buffer  
**Total calendar time to launch:** 14–18 weeks from Phase 1 start

**Exit criteria (ALL must pass before launch):**
- Beta test: 50+ users, 2-week minimum run
- Day-7 retention: ≥ 15%
- Crash rate: < 1% of sessions
- Economy sanity check: no exploit path identified reaching Elite tier < 90 days equivalent
- Trader beta review: 5 active traders complete 10+ Career Mode sessions, ≥ 4/5 rate coaching card accuracy as "accurate" (RISK-02 gate)
- Blow-up rate: < 50% of beta users hit Soft Restart in first 10 sessions (RISK-03 monitor)
- App Store approval: in hand before public launch date is announced
- Legal opinion: South African FAIS opinion received

---

### 1.1 — Infrastructure
- [ ] Supabase schema deployed (all tables in DATA_SCHEMA.md)
- [ ] RLS policies applied and tested
- [ ] **New columns from risk mitigations:**
  - [ ] `trades.sync_status` (pending/synced/conflict) — RISK-06
  - [ ] `dataset_exposures` table (user_id, dataset_id, times_seen, last_seen_at) — RISK-09
  - [ ] `career_lives.capital_snapshot_at_session_start` (for sync conflict validation) — RISK-06
- [ ] Edge Functions deployed: resolve_trade, resolve_arcade_answer, initiate_transfer, weekly_growth_bonus, check_milestones, check_leverage_unlock, revenuecat_webhook, refresh_leaderboards
- [ ] **New Edge Function logic from risk mitigations:**
  - [ ] `resolve_trade`: validates `capital_before_cents` in sync queue matches authoritative server state before processing (RISK-06)
  - [ ] `resolve_arcade_answer`: enforces 200 TradePoints/day Arcade cap (RISK-04)
  - [ ] Weekly growth bonus: minimum 3 sessions in prior week gate (RISK-04)
  - [ ] Dataset assignment: server assigns datasets (user cannot select) — least-recently-seen algorithm (RISK-09)
- [ ] Scheduled functions: transfer processing (15 min), weekly growth bonus (Monday 00:01), leaderboard refresh (60 min)
- [ ] Dataset upload pipeline: JSON → Supabase Storage + local SQLite bundle
- [ ] SQLite WAL mode enabled (RISK-06)

### 1.2 — Auth + Onboarding
- [ ] Sign in with Apple
- [ ] Sign in with Google
- [ ] Email/password fallback (reconsider: if cross-app auth requires Apple/Google, email fallback creates orphaned accounts that can't participate in ecosystem — decision needed)
- [ ] Splash → Welcome → Experience Level → Profile Setup → Disclaimer → Home
- [ ] Learning module gate logic (Beginner: hard gate; others: soft prompt)
- [ ] **New: Arcade Mode preview for Beginners** (single read-only session before learning module gate) — RISK-10
- [ ] Learning module abandonment tracking: `learning_module_section_started` and `learning_module_section_completed` PostHog events for all 7 sections — RISK-10

### 1.3 — Learning Module
- [ ] All 7 sections built (slides + trader-reviewed illustrations)
- [ ] Quiz engine (3 questions, 2/3 pass, retry logic)
- [ ] Progress saved and resumable
- [ ] Badge award on completion
- [ ] Risk management standalone module
- [ ] **New: side quest for risk module completion** ("Complete Risk Management module — earn 50 TradePoints") — RISK-10

### 1.4 — Career Mode Core
- [ ] WebView chart rendering (using architecture confirmed in Phase 0.4)
- [ ] Dataset loading from SQLite (server-assigned, not user-selected — RISK-04)
- [ ] Dataset exposure tracking: `dataset_exposures` updated on each session start (RISK-09)
- [ ] 5× playback engine
- [ ] Pause at decision point
- [ ] Decision UI: direction + lot size (Stage 1–2 simplified — no Aggressive option if modelling in Phase 0.8 flagged it) + SL + TP presets
- [ ] No Trade mechanic
- [ ] Lock In → resume → outcome detection
- [ ] `resolve_trade` Edge Function integration (with capital snapshot validation)
- [ ] Post-trade card (all outcome types)
- [ ] Coaching cards (Stage 1 win/loss, all stages for No Trade)
- [ ] Session summary screen

### 1.5 — Charting Tools + Timeframe Toggle
- [ ] Horizontal line tool (all tiers)
- [ ] Trendline tool (Intermediate+ tier)
- [ ] Fibonacci retracement tool (Developing+ tier)
- [ ] Timeframe toggle (1M/5M/15M/1H, tier-gated)
- [ ] Tools: visible during pause state only, cleared on chart resume

### 1.6 — Practice Capital System
- [ ] Pip value computation per trade
- [ ] Live risk % display before lock-in (Stage 3–4)
- [ ] Margin call simulation (<$50 warning, <$10 blown state)
- [ ] Capital display on session screen and home

### 1.7 — Blow-Up Mechanics
- [ ] Career Mode Blown screen (Soft Restart)
- [ ] **New: learning module completion check on Soft Restart** — module must be complete before $250 loan is issued (RISK-03)
- [ ] Career Mode Death screen (Full Restart) with transfer prompt
- [ ] 48-hour transfer processing
- [ ] Narrative cards (blown, restart, loan repaid)
- [ ] **New: doom loop protection** — if Practice Capital < $100 within 5 sessions of Soft Restart: mandatory 3-slide risk management refresher before next session (RISK-03)
- [ ] Doom loop PostHog events: `soft_restart_loan_at_risk` fires when < $100 within first 5 sessions (RISK-03)

### 1.8 — Leverage Tier System
- [ ] Tier unlock check after every TradePoints update
- [ ] Tier unlock celebration screen
- [ ] Feature gating per tier (tools, timeframes, lot size input)
- [ ] Tier display on Career Hub and Profile

### 1.9 — Practice Capital Milestones
- [ ] Milestone detection on every capital update
- [ ] Milestone badge awards
- [ ] Narrative cards at each milestone
- [ ] Bonus TradePoints on milestone

### 1.10 — Perks System
- [ ] Perks awarded on trigger conditions
- [ ] Perks lost on Soft Restart (except module-based)
- [ ] Perks display on Profile
- [ ] Streak Shield perk mechanic

### 1.11 — Side Quests
- [ ] Quest template system (static config)
- [ ] Quest progress tracking
- [ ] Quest display on Home (up to 3 active free, 5 Pro)
- [ ] Quest completion reward
- [ ] Quest refresh on session completion

### 1.12 — Arcade Mode
- [ ] 10-challenge session structure
- [ ] All 7 challenge types implemented
- [ ] Timer (Medium: 30s, Hard: 15s)
- [ ] Speed bonus detection
- [ ] In-session streak tracking
- [ ] Accuracy tracking by challenge type
- [ ] Session summary
- [ ] Arcade leaderboard (weekly, resets Monday)
- [ ] **New: daily Arcade TradePoints cap enforced** (200 pts/day cap value confirmed by economy model in Phase 0.6) — RISK-04
- [ ] "Daily Arcade limit reached" notification shown when cap hit (not an error — a friendly message)

### 1.13 — Game Economy
- [ ] TradePoints floor (100)
- [ ] Win streak multiplier (Career Mode)
- [ ] Weekly growth bonus computation (with 3-session minimum gate)
- [ ] Neutral outcomes do NOT advance or reset streak (frozen) — RISK-04
- [ ] All badge award logic
- [ ] Badge display (profile, leaderboard)

### 1.14 — Mini-Game Tabs (UI Shell)
- [ ] PropWise tab: appears after Elite tier or $100k. Congratulations card + "Full mini-game coming soon" placeholder.
- [ ] CompWise tab: same at Master tier or $250k.
- [ ] Full mechanics: Phase 1b

### 1.15 — Leaderboard
- [ ] Career Mode tab (Practice Capital ranking)
- [ ] Arcade tab (weekly TradePoints)
- [ ] User's own rank pinned
- [ ] 60-minute refresh

### 1.16 — Profile
- [ ] All stat sections
- [ ] Career Readiness Rating + disclaimer
- [ ] Badge case (earned + locked)
- [ ] Quest log
- [ ] Transfer history (including pending status and 48-hour countdown)
- [ ] Settings

### 1.17 — Monetisation
- [ ] RevenueCat SDK integration
- [ ] **New: $0.99 entry-point cosmetic IAP** (one chart background or badge frame — first item in the shop) — RISK-07
- [ ] Subscription (Pro) paywall
- [ ] 7-day trial flow
- [ ] Content pack IAPs
- [ ] Feature unlock IAPs
- [ ] Cosmetic shop (avatar packs, chart themes, badge frames, UI accents)
- [ ] Entitlement gating
- [ ] Restore Purchases
- [ ] **Pro trial offer surfaced at first milestone badge** (not on first launch) — RISK-07

### 1.18 — Disclaimer Architecture
- [ ] Onboarding disclaimer (active accept)
- [ ] Career Mode session Practice Capital disclaimer
- [ ] Career Readiness Rating disclaimer
- [ ] PropWise/CompWise mini-game return disclaimer (ready for Phase 1b)
- [ ] All disclaimer copy reviewed against REGULATORY_NOTES.md

### 1.19 — Offline + Sync
- [ ] SQLite caching (datasets, challenges, session state)
- [ ] Pending sync queue with `sync_status` tracking
- [ ] **Capital snapshot validation on sync** — RISK-06
- [ ] **Session replay prevention** (server marks session status: active → complete, rejects duplicate resolutions) — RISK-06
- [ ] Sync on reconnect with conflict handling (`conflict` status, user notification)
- [ ] **Offline test: pending transfer → uninstall → reinstall → transfer status visible** — RISK-08

### 1.20 — QA + Beta
- [ ] Internal QA: all flows, all edge cases, all blow-up states, all transfer paths
- [ ] **Economy exploit testing** (20 internal sessions attempting each exploit path in RISK-04) — RISK-04
- [ ] **Sync conflict QA** (simulate offline session → server state change → reconnect for all conflict vectors in RISK-06) — RISK-06
- [ ] **Blow-up rate check** (using Stage 1 lot sizes and worst-case model from Phase 0.8: confirm < 15-session blow-up is not possible) — RISK-03
- [ ] TestFlight (iOS): 25 general beta users minimum, 2 weeks
- [ ] TestFlight (iOS): 5 active traders who complete 10+ Career Mode sessions and rate coaching card accuracy — RISK-02
- [ ] Play Store Internal (Android): 25 users minimum
- [ ] Day-7 retention measurement: ≥ 15% required to proceed to launch
- [ ] Crash rate: < 1%
- [ ] Learning module abandonment by section: report generated. Sections with > 40% abandonment flagged for redesign before launch.
- [ ] App Store submission: after beta criteria met
- [ ] **2-week App Store submission buffer** in calendar (RISK-05)
- [ ] South African legal opinion: received and on file

---

## Phase 1b — Mini-Game Full Mechanics

**Can run in parallel with Phase 1.20 QA.**

- [ ] PropWise: property marketplace, monthly return cycle, PropFunds tracking
- [ ] PropWise: return rates benchmarked against real-world data (confirmed in Phase 0.2) and capped accordingly — RISK-12
- [ ] PropWise: "Simulated returns" disclaimer on all return displays
- [ ] CompWise: venture marketplace, monthly revenue cycle, BizFunds tracking
- [ ] CompWise: return rate same treatment as PropWise
- [ ] Full transfer mechanic: initiate_transfer Edge Function, 48-hour processing, monthly cap enforcement
- [ ] Mini-game to Career Mode transfer UI (with pending countdown)
- [ ] Cross-app transfer flow (download PropWise/CompWise App Store link)
- [ ] PropWise Starter Pack and CompWise Starter Pack IAPs (ecosystem starters)

---

## Phase 2 — Competitions

**Prerequisite:** ALL items in REGULATORY_NOTES.md Section 4 build gate checked AND South African legal opinion expanded to cover competitions. Hard gate.

- [ ] Competition infrastructure (tables, leaderboard, entry)
- [ ] Monthly competition (in-app prizes first)
- [ ] Competition badge
- [ ] Cash prize competitions: only after all legal opinions in REGULATORY_NOTES.md Section 4 received

---

## Phase 3 — Instrument Expansion

**Prerequisite:** MVP day-30 and day-60 retention data reviewed. Content repetition rate from `dataset_exposures` data reviewed.

- [ ] XAUUSD datasets (20 minimum, all conditions, trader-validated)
- [ ] BTCUSD datasets (20 minimum, trader-validated)
- [ ] Instrument selector on Career Mode and Arcade session start
- [ ] "Random" mode
- [ ] Regional leaderboards (country, continent)
- [ ] **5 new datasets per month content pipeline in operation by end of Phase 3** — RISK-09

---

## Phase 4 — PropWise and CompWise Dedicated Apps

- [ ] PropWise: full property mechanics, mortgage, market cycle simulation
- [ ] CompWise: full business mechanics, hiring, supply chain
- [ ] Cross-app leaderboard
- [ ] Shared cosmetics

---

## Phase 5 — 6-Month Post-Launch Review Gates

*Mitigates: RISK-07 (revenue), RISK-11 (regulatory)*

**At exactly 6 months post-launch, conduct the following:**

- [ ] **Revenue review:** actual vs minimum viable threshold. If below: escalate to Masood with three pre-agreed options (optional video reward ads / premium content paywall / infrastructure cost reduction).
- [ ] **Regulatory compliance audit:** second legal review of the app as-built (not as-designed). Features added post-launch reviewed for compliance.
- [ ] **Economy audit:** TradePoints distribution across player base. Top 1% analysed for exploit patterns. Economy rebalanced if needed.
- [ ] **Content repetition audit:** `dataset_exposures` data reviewed. Average times_seen per dataset per active user. If > 2.5 times_seen: content production pipeline accelerated.
- [ ] **Learning module abandonment audit:** section-level completion data reviewed. Any section with > 35% abandonment rate gets a redesign sprint.

---

## Dependency Map

```
Phase 0 (Foundation — ALL gates must pass)
    │
    ▼
Phase 1 (MVP Build + Launch) [14–18 weeks including App Store buffer]
    │
    ├──── Phase 1b (Mini-Game Full Mechanics) ← parallel with 1.20 QA
    │
    ├──── Phase 2 (Competitions) ← hard legal gate
    │
    └──── Phase 3 (Instrument Expansion) ← after MVP 60-day data
              │
              └──── Phase 4 (PropWise + CompWise Apps)
                        │
                        └──── Phase 5 (6-Month Review) ← runs at +6 months from launch
```

---

## Content Production Pipeline (Ongoing from Launch)

*Mitigates: RISK-09 (content volume)*

**Commit to this before launch. It is not optional.**

- Month 1–3 post-launch: 3 new datasets per month minimum
- Month 4+ post-launch: 5 new datasets per month minimum
- Each dataset must complete the two-stage validation process before activation
- Dataset production does not require engineering — only a trained curator and a qualified trader for Stage 2 sign-off
- Budget for dataset curation must be allocated before launch

---

## Backlog (Unscheduled)

- Stocks and Futures datasets
- Dark mode
- Haptic feedback on outcomes
- Push notifications (streak reminders, competition alerts, weekly growth bonus)
- Tablet / iPad optimised layouts
- Referral programme (invite user — TradePoints reward)
- AI-powered trade feedback
- Web app (react-native-web)
- Social: share badge card to social media
- Live delayed data feed (Phase 6 — data vendor contract + budget required)
- Account recovery automation (currently manual via support email — automate post-launch)
