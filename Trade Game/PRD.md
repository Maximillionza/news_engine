# PRD.md — TradeWise Product Requirements Document

**Version:** 0.2  
**Owner:** Masood  
**Status:** Draft — not yet approved for build

---

## 1. Problem Statement

Retail trading has a structural onboarding failure. New traders move from interest to live accounts with no meaningful intermediate step. The 70–80% first-year loss rate is well documented. Existing tools — courses, paper trading, YouTube — fail because they don't build the specific cognitive habit of pre-hoc conviction under repeated conditions, and they don't simulate the emotional arc of building, protecting, and risking capital over time.

TradeWise solves this by wrapping trading education inside a genuine career progression game. The user isn't just practising trades — they're building a simulated financial life, with real stakes within the simulation, real consequences for poor risk management, and real rewards for discipline and growth.

---

## 2. Target Users

| Segment | Description |
|---|---|
| New to Trading | Zero prior experience. Drawn by curiosity or financial aspiration. Needs vocabulary and confidence. |
| Learning to Trade | Has consumed content, hasn't found consistent edge. Knows the terms, struggles under pressure. |
| Struggling to Trade | Has a live account and is losing. Needs diagnosis and structured rebuilding. |
| Gamers Interested in Finance | May not intend to trade live but engage through the game layer. Secondary acquisition channel. |

---

## 3. Modes Overview

### Career Mode (Core)
The primary game. Users start with $500 Practice Capital at 1:10 leverage and build through milestones that unlock leverage tiers, features, and mini-games. Progression is driven by both account growth (Practice Capital balance) and trading performance (TradePoints). This is where the full educational value lives.

### Arcade Mode
Skill-testing mode decoupled from the Career Mode economy. No Practice Capital at stake. Users face rapid-fire analytical challenges — setup identification, candlestick pattern naming, Bollinger Band reading, reversal vs pullback classification. Competitive, fast, replayable. Awards TradePoints that feed into the shared TradePoints economy.

### Competitions (Post-MVP)
Monthly structured events. Users compete on a defined metric (e.g. highest % account growth in Career Mode, or highest Arcade Mode score in the month). Prizes are in-app rewards in MVP competitions, cash prizes post-legal-review. See REGULATORY_NOTES.md.

---

## 4. MVP Feature Requirements

---

### 4.1 Onboarding

**FR-001: Experience level selection**
- Beginner / Amateur / Professional
- Gates learning module behaviour
- Sets initial Arcade Mode difficulty
- Affects coaching card verbosity in Career Mode
- Changeable in settings (badge does not auto-upgrade)

**FR-002: Profile creation**
- Username (3–20 chars, alphanumeric + underscore, unique)
- Avatar (12 preset options, MVP — cosmetic shop expands this)
- Country (ISO code, required for Post-MVP regional competitions)
- Linked to Apple ID or Google ID (required — enables cross-app ecosystem)

**FR-003: Disclaimer acceptance**
- Active acceptance (checkbox + button). Cannot be passive.
- Full disclaimer content defined in REGULATORY_NOTES.md.
- Contextual disclaimers shown throughout app at relevant moments.

**FR-004: Learning module gate**
- Beginner: mandatory before Career Mode unlocks
- Amateur / Professional: prompted, deferrable, periodic reminders (every session until completed or dismissed after 5 dismissals)

---

### 4.2 Learning Module

**FR-005: Core curriculum — 7 sections**
1. What is a financial market
2. How to read a candlestick chart
3. Market structure
4. What is a confluence (5 core setups — see CONTENT_SPEC.md)
5. Risk management (lot size, SL, pip value, risk %)
6. Margin and leverage
7. What is a trading plan

**FR-006: Module format**
- Slide-based, illustration per slide, max 8 slides per section
- 3-question quiz at end of each section (2/3 to pass, unlimited retries)
- Progress saved, resumable

**FR-007: Learning badge on completion**
- Beginner → Bronze Learning Badge
- Amateur → Silver Learning Badge
- Professional → Gold Learning Badge

**FR-008: Risk management module (standalone)**
- Always accessible from main menu and Career Mode session screen
- Covers lot sizing, SL placement, margin, risk % worked examples
- Not gated behind main module completion

---

### 4.3 Career Mode

#### Account Structure

**FR-009: Starting state**
- Practice Capital: $500
- Leverage: 1:10 (max position size = $5,000 notional)
- Instrument: EURUSD only (MVP)
- TradePoints: 1,000 (shared pool with Arcade Mode)

**FR-010: Leverage unlock tiers**
Leverage unlocks are gated by TradePoints accumulated (not account balance — prevents reckless risk-taking to hit a balance milestone).

| Tier | TradePoints Required | Max Leverage | Additional Unlock |
|---|---|---|---|
| Starter | 0 | 1:10 | Career Mode access |
| Developing | 2,500 | 1:20 | Fibonacci tool in charting |
| Intermediate | 7,500 | 1:30 | 15M timeframe unlock |
| Advanced | 15,000 | 1:50 | Multi-confluence display overlay |
| Elite | 30,000 | 1:100 | PropWise mini-game unlock |
| Master | 75,000 | 1:200 | CompWise mini-game unlock |

Leverage tiers are unlocked permanently. Losing TradePoints does not reverse a leverage unlock. Leverage choice remains optional — user can always trade at a lower leverage than their unlocked tier.

**FR-011: Practice Capital milestones**
Account balance milestones trigger rewards and narrative events.

| Milestone | Reward |
|---|---|
| $1,000 | "First Double" badge. +100 bonus TradePoints. |
| $5,000 | New charting tool unlocked (trendline tool). Narrative card. |
| $10,000 | "Five Figure Trader" badge. Access to additional EURUSD datasets. |
| $25,000 | Arcade Mode hard difficulty unlocked. |
| $50,000 | Cosmetic reward: exclusive chart theme. |
| $100,000 | PropWise mini-game unlocked (if not already via TradePoints). Side quest initiated. |
| $250,000 | CompWise mini-game unlocked (if not already via TradePoints). |
| $1,000,000 | "TradeWise Legend" status. Permanent gold border on leaderboard entry. |

**FR-012: TradePoints in Career Mode**

Career Mode awards TradePoints based on two factors:

*Per-trade awards:*
- Win (TP hit): +10 base (modified by streak multiplier)
- Loss (SL hit): −10 base
- Correct No-Trade: +5
- Neutral outcome: 0

*Account growth awards (weekly snapshot):*
- Practice Capital up 5–10% vs prior week: +50 TradePoints
- Practice Capital up 10–25%: +150 TradePoints
- Practice Capital up 25%+: +300 TradePoints
- Practice Capital down 10%+: no bonus (loss is its own consequence)

This dual-reward structure ensures a user who takes many small wins also earns, but a user who grows their account efficiently earns faster. Both skill expressions are rewarded.

#### Blow-Up and Restart Mechanics

**FR-013: Soft Restart (Loan mechanic)**
Triggered when Practice Capital falls below $10 (effectively zero).

- User is shown Career Mode Blown screen with summary of what was lost and retained
- **Lost on Soft Restart:** active leverage above the Developing tier, certain active perks (defined in GAME_DESIGN.md), current win streak
- **Retained on Soft Restart:** TradePoints balance, all badges earned, all mini-game unlocks, learning badges
- New starting capital: **$250** (a loan, not a gift — narrative framing)
- Loan is represented in the UI as a negative equity counter that clears once Practice Capital exceeds $250 again
- User has one Soft Restart per Career Mode life. It is not repeatable.

**FR-014: Career Mode Death**
Triggered when Practice Capital falls below $10 after a Soft Restart has already been used.

- Career Mode is dead. Full restart required.
- **Permanently lost:** Practice Capital, leverage tier progress, active perks, career streak
- **Permanently retained:** TradePoints, all badges, mini-game unlocks, PropFunds/BizFunds in mini-games
- **Transfer mechanic:** If user has accumulated PropFunds or BizFunds in mini-games, they may transfer a maximum of **$5,000 combined** to seed their new Career Mode starting capital (raising it from $500 to a maximum of $5,500)
- Transfer must be requested before confirming the restart. Cannot be done retroactively.
- 48-hour processing delay on transfer.

**FR-015: Monthly mini-game to Career Mode transfer (normal play)**
For users who have not blown their Career Mode:
- Maximum transfer: **$50,000 per mini-game per month**
- Transfer direction: mini-game → Career Mode only. Career Mode → mini-game is not permitted.
- Processing delay: 48 hours.
- Transfer cap resets on the 1st of each month.
- Transfer history visible in profile.

#### Career Mode Session Flow

**FR-016: Session structure**
Identical pre-hoc decision mechanic as defined in CLAUDE.md. Chart pauses → user commits all four inputs → chart plays → outcome.

- Session presents 3–7 trade opportunities depending on user stage
- Charting tools available during pause (tool availability gated by TradePoints tier — FR-010)
- Post-trade card shows: direction result, Practice Capital impact, risk % taken, optimal comparison

**FR-017: No Trade option**
Available at every decision point. See GAME_DESIGN.md for full scoring rules. Trains the discipline of not overtrading.

**FR-018: Practice Capital display**
- Always visible on session screen (not interruptive — small persistent element)
- Real pip-value computation applied to every trade (lot size × SL pips × pip value)
- Margin call simulation: below $50 (10% of $500 start) → warning. Below $10 → blown state triggered.

---

### 4.4 Arcade Mode

**FR-019: Arcade Mode structure**
Arcade Mode is a rapid-skill-testing mode. No Practice Capital. No blow-up risk. Pure analytical challenge.

Challenge types (presented in a queue, randomised):

| Challenge Type | Description |
|---|---|
| Setup Identification | Chart pauses. Is this a valid setup? Buy, Sell, or No Trade? |
| Candlestick Pattern | Single or multi-candle pattern shown. Name it from 4 options. |
| Reversal vs Pullback | Price action shown. Is this a reversal or a pullback? |
| Bollinger Band Reading | Chart with BB shown. Where is price relative to the band? What does it suggest? |
| Market Structure | Identify: trending up, trending down, ranging, or compression. |
| Support or Resistance | A level marked on the chart. Is it support or resistance in the current context? |
| Next Move Prediction | Chart freezes mid-pattern. Select the most likely next candle from 4 options. |

**FR-020: Arcade Mode scoring**
- Each correct answer: +5 TradePoints
- Each incorrect answer: −2 TradePoints (smaller penalty — Arcade is for learning, not punishment)
- Speed bonus: correct answer within 10 seconds: +2 bonus TradePoints
- Arcade Mode streak: consecutive correct answers. Bonus TradePoints at 5, 10, 20, 30.
- Arcade session: 10 challenges per session. Session score displayed at end.

**FR-021: Arcade Mode difficulty**
- Easy: setup identification only, clean unambiguous setups, no time pressure
- Medium (default): all challenge types, 30-second timer per challenge
- Hard: all types, 15-second timer, includes trap setups and ambiguous patterns (unlocked at $25,000 Practice Capital — FR-011)

**FR-022: Arcade Mode leaderboard**
- Weekly Arcade leaderboard (resets Monday 00:00 UTC)
- Ranked by total TradePoints earned in Arcade Mode that week
- Separate from Career Mode leaderboard. Both visible in Leaderboard screen via tabs.

---

### 4.5 Mini-Games (Unlockable)

**FR-023: PropWise mini-game**
Unlocked at: 30,000 TradePoints (Elite tier) OR $100,000 Practice Capital.

Concept: simplified property investment simulation. User allocates PropFunds to simulated property assets. Returns are generated based on simplified market cycles (not real data). Mini-game is intentionally limited — it is a teaser for the full PropWise app.

MVP mini-game mechanics:
- Starting PropFunds: $0 (must be seeded from Career Mode transfers or transfers from full PropWise app)
- Property types: Residential, Commercial, Industrial (3 types only in mini-game)
- Return cycle: monthly (in-game time = 1 real week)
- Max portfolio size in mini-game: 5 properties
- No mortgage mechanics in mini-game (full PropWise app only)
- PropFunds can be transferred to Career Mode (subject to FR-015 limits)

**FR-024: CompWise mini-game**
Unlocked at: 75,000 TradePoints (Master tier) OR $250,000 Practice Capital.

Concept: simplified business simulation. User allocates BizFunds to simulated business ventures. Revenue generated based on simplified business cycle mechanics.

MVP mini-game mechanics:
- Starting BizFunds: $0 (must be seeded from Career Mode transfers or transfers from full CompWise app)
- Business types: Retail, Tech, Services (3 types only in mini-game)
- Revenue cycle: monthly (in-game time = 1 real week)
- Max ventures in mini-game: 3
- BizFunds can be transferred to Career Mode (subject to FR-015 limits)

**FR-025: Cross-app transfer to dedicated apps**
When a user decides to move from the mini-game to the dedicated app (PropWise or CompWise):
- They download the dedicated app (separate App Store listing)
- Log in with same Apple/Google ID
- Transferable progress: PropFunds/BizFunds balance, any cosmetics earned in the mini-game
- Non-transferable: TradeWise-specific badges, Career Mode progress
- Transfer is one-time per Career Mode life. Once transferred, mini-game progress in TradeWise resets. User continues in the dedicated app.

---

### 4.6 Points and Economy

**FR-026: TradePoints pool**
TradePoints are a single shared pool across Career Mode and Arcade Mode. They serve two functions:
1. **Progression currency:** gate leverage tiers and feature unlocks (FR-010)
2. **Ranking currency:** leaderboard ranking

TradePoints are never purchasable with real money. They are earned through gameplay only. This preserves leaderboard integrity and regulatory cleanliness.

**FR-027: TradePoints floor**
100 TradePoints minimum. Points cannot fall below this value.

**FR-028: Win streak multiplier**
Applies to Career Mode trade wins only (not Arcade Mode, which has its own streak system).

| Consecutive Wins | Multiplier | Effective Points per Win |
|---|---|---|
| 1–4 | 1.0× | 10 |
| 5–9 | 1.5× | 15 |
| 10–19 | 2.0× | 20 |
| 20–29 | 2.5× | 25 |
| 30+ | 3.0× | 30 |

---

### 4.7 Badge System

**FR-029: Learning badges** — see FR-007  
**FR-030: Win streak badges** — Bronze (5/10/20 streak), Silver (20/35/50), Gold (50/75/100)  
**FR-031: Milestone badges** — awarded at Practice Capital milestones (FR-011)  
**FR-032: Arcade badges** — awarded for Arcade Mode performance milestones  

Full badge catalogue in GAME_DESIGN.md.

---

### 4.8 Leaderboard

**FR-033: MVP leaderboard tabs**
- Career Mode: ranked by Practice Capital balance
- Arcade Mode: weekly, ranked by Arcade TradePoints earned that week
- Global only in MVP. Country/regional tabs in Post-MVP.

---

### 4.9 Disclaimer Architecture

**FR-034: Disclaimer placement**
- Onboarding: active acceptance required
- Practice Capital display: one-line disclaimer always shown nearby
- Any milestone badge that implies competence: contextual disclaimer
- Career Readiness Rating display: persistent disclaimer
- See REGULATORY_NOTES.md for full content requirements

---

### 4.10 Career Readiness Rating

**FR-035: Metric definition**
- 0–100 composite score
- Factors: win rate (last 100 trades), correct No-Trade rate, average risk % consistency, sessions completed, Practice Capital growth stability
- Labels: Early Stage (0–30), Developing (31–60), Progressing (61–80), Practice-Ready (81–100)
- "Practice-Ready" always shows: "This reflects your simulated practice performance only."
- Never framed as a qualification or guarantee

---

## 5. Post-MVP Features

### Phase 1 — Competitions
- Monthly structured competitions
- Entry: all users automatically eligible
- MVP prize: in-app rewards (cosmetics, bonus TradePoints, ad-free period)
- Cash prizes: post-legal-review only (see REGULATORY_NOTES.md)
- Separate competition leaderboard (does not affect main Career Mode or Arcade leaderboards)

### Phase 2 — Instrument Expansion
- XAUUSD (Gold)
- BTCUSD (Crypto)
- One stock instrument (TBD)
- User selects instrument or "Random" at session start

### Phase 3 — Regional Leaderboards
- Country, continental, global tabs
- Regional competitions

### Phase 4 — PropWise and CompWise Dedicated Apps
- Full PropWise: mortgage mechanics, market cycles, portfolio analytics
- Full CompWise: hiring, supply chain, market competition mechanics
- Cross-app transfer finalised
- Shared leaderboard across ecosystem

---

## 6. Out of Scope (Permanently)

- Executing real trades
- Holding real money
- Providing personalised financial advice
- Storing payment card data (RevenueCat handles this)

---

## 7. Success Metrics

| Metric | MVP Target |
|---|---|
| Day-1 retention | 60% |
| Day-7 retention | 18% |
| Day-30 retention | 10% |
| Sessions per active user per week | 4 |
| Learning module completion (Beginner) | 70% |
| IAP conversion (any purchase) | 8% of 30-day actives |
| Subscription conversion | 12% of 30-day actives |
| Career Mode blow-up rate (first 30 days) | Track only — no target yet |
| Soft Restart usage rate | Track only |
