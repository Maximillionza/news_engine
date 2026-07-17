# FEATURE_SPEC.md — TradeWise Screen-by-Screen Feature Specification

**Version:** 0.2  
**Owner:** Masood  
**Read alongside:** PRD.md, GAME_DESIGN.md, MONETISATION.md

---

## Navigation Structure (MVP)

```
App Root
├── Auth Stack
│   ├── Splash Screen
│   ├── Onboarding Flow (first launch only)
│   │   ├── Welcome
│   │   ├── Experience Level Selection
│   │   ├── Profile Setup
│   │   └── Disclaimer Accept
│   ├── Login
│   └── Register
│
└── Main Tab Navigator
    ├── Home (Dashboard)
    ├── Career (Career Mode Hub)
    │   └── Active Session Screen
    ├── Arcade (Arcade Mode Hub)
    │   └── Active Arcade Session Screen
    ├── [PropWise] (hidden until Elite tier unlock)
    ├── [CompWise] (hidden until Master tier unlock)
    ├── Leaderboard
    └── Profile
        ├── Badge Case
        ├── Career Stats
        ├── Arcade Stats
        ├── Quest Log
        └── Settings
            ├── Subscription / Shop
            └── Account
```

---

## Screen Specifications

---

### SCREEN: Splash
**MVP:** Yes

- Logo + wordmark: 1.5 seconds
- Auth state check in background
- Route: authenticated + onboarding complete → Home; authenticated + incomplete → resume onboarding; unauthenticated → Welcome

---

### SCREEN: Welcome
**MVP:** Yes

- Headline: "Learn to trade. For real."
- Three-line value statement (prose, not bullets)
- "Get Started" → Experience Level Selection
- "Already have an account? Log in"
- No feature carousel. Not the place for feature education.

---

### SCREEN: Experience Level Selection
**MVP:** Yes

Three options, tap to select:
- **Beginner** — "New to trading. I want to learn from scratch."
- **Amateur** — "I know the basics. I want to sharpen my edge."
- **Professional** — "I trade regularly. I'm here to test setups and compete."

Each shows: label, description, learning module behaviour (Beginner: mandatory; others: encouraged).

Required. No skip.

---

### SCREEN: Profile Setup
**MVP:** Yes

- Username (required, unique, 3–20 chars)
- Avatar (12 preset grid, single select)
- Country (searchable dropdown, required)
- Sign in with Apple / Sign in with Google (required for cross-app ecosystem)

Username availability checked on blur.

---

### SCREEN: Disclaimer Accept
**MVP:** Yes

Heading: "Before you start — important information"

Four paragraphs:
1. TradeWise uses simulated trading only. No real money involved.
2. Simulated performance does not predict live trading performance.
3. Nothing in this app is financial advice or a recommendation to trade.
4. The Career Readiness Rating reflects practice quality only — it is not a qualification.

Checkbox (manual tap required): "I have read and understood the above."  
"Continue" button disabled until checked. Cannot be skipped.

---

### SCREEN: Home (Dashboard)
**MVP:** Yes

**Top section — user identity bar:**
- Avatar, username, experience level badge
- TradePoints balance (prominent)
- Current Career Mode win streak
- Practice Capital balance (smaller, below TradePoints)

**Quick Action:**
- If active Career Mode session in progress: "Resume Session" card (shows progress: "3 of 5 trades")
- If no active session: "Start Trading" → Career Hub
- "Play Arcade" → Arcade Hub (secondary CTA)

**Active Side Quests (up to 3, or 5 for Pro):**
- Quest card per active quest: name, progress bar, reward preview
- Tap to view full quest detail
- "View All Quests" link → Quest Log in Profile

**Recent Activity:**
- Last 3 sessions (Career or Arcade): date, mode, result summary, points change

**Mini-game tiles (when unlocked):**
- PropWise: PropFunds balance, last return, "Open" CTA
- CompWise: BizFunds balance, last return, "Open" CTA
- Both hidden until unlock. No teaser/locked tile shown before unlock (prevents confusion).

**Learning Module CTA (if incomplete):**
- Beginner: "Complete your learning module to unlock Career Mode." Persistent, cannot dismiss.
- Amateur/Professional: "Continue your learning module." Dismissible after 5 dismissals.

---

### SCREEN: Career Mode Hub
**Route:** `/career`  
**MVP:** Yes

**Header:** Practice Capital balance (large), current leverage tier, TradePoints, win streak.

**Session Start panel:**
- Instrument: EURUSD (MVP — shown as selected, not a picker)
- Timeframe: 5-minute (shown as selected)
- "Start Session" CTA
- "Resume Session" CTA (if incomplete session exists)

**Progression panel:**
- Current TradePoints vs next tier threshold (progress bar)
- Next unlock preview: "At 2,500 TradePoints: 1:20 leverage + Fibonacci tool"

**Leverage tier display:**
- Current tier badge
- All tiers shown in a timeline (locked tiers greyed, current highlighted, unlocked tiers filled)

**Weekly growth tracker:**
- Practice Capital vs same time last week
- Growth % and bonus TradePoints earned/available this week

---

### SCREEN: Career Mode — Active Session
**Route:** `/career/session/:sessionId`  
**MVP:** Yes  
**Critical screen — full state specification**

**Persistent elements (visible in all states):**
- Top bar: "Trade X of Y" progress | TradePoints | Practice Capital | Exit button (with confirm modal)
- Practice Capital at-a-glance disclaimer: "Practice Capital — not real money"

**STATE 1: PLAYING (chart scrolling to decision point)**
- Chart: full width, 70% screen height, playing at 5× speed
- Bottom panel: "Analysing market..." subtle status
- No user input
- Timeframe toggle: hidden
- Tools drawer: hidden

**STATE 2: PAUSED — DECISION POINT**
- Chart: frozen at trigger candle
- Subtle border pulse on chart (decision point signal)
- Bottom panel — Decision UI:

  ```
  [BUY]          [NO TRADE]         [SELL]
  
  (If Buy or Sell selected:)
  Lot Size: [Conservative] [Moderate] [Aggressive]  ← Stage 1-2
  Lot Size: [0.01 ----slider---- 1.00]              ← Stage 3-4 (custom input)
  Live risk display: "This risks $[X] = [Y]% of your Practice Capital"
  
  (After lot size selected:)
  Stop Loss: [Tight - Xpips] [Moderate - Ypips] [Wide - Zpips]  ← Preset
  
  (After SL selected:)
  Take Profit: [Tight - Xpips] [Moderate - Ypips] [Wide - Zpips]
  
  [LOCK IN TRADE] ← disabled until all fields populated
  ```

- Timeframe toggle: visible (1M / 5M / 15M / 1H — tier-gated)
- Tools drawer: slide-up from bottom (does not obscure chart area)
  - Tools available: horizontal line (all tiers), trendline (Intermediate+), Fibonacci (Developing+)
  - "Clear All Drawings" button in drawer

**STATE 3: LOCKED — PLAYING TO OUTCOME**
- Decision summary card replaces decision UI: "SELL | 0.05 lots | SL: 50 pips | TP: 100 pips | Risk: 1.1%"
- All inputs frozen
- Chart resumes at 5× speed
- SL line (red dashed) and TP line (green dashed) drawn on chart at committed levels
- Timeframe toggle: hidden
- Tools: hidden
- Bottom panel: "Watching outcome..."

**STATE 4: OUTCOME**
- Chart pauses at resolution candle
- Outcome overlay (modal over chart):

  *Win (TP hit):*
  - Large green ✓
  - "+X TradePoints" (with streak multiplier shown if active: "×2.0 streak bonus")
  - "+$[amount] Practice Capital"
  - Risk taken: "You risked [Y]% of your Practice Capital"
  - Stage 1 only: Setup label + coaching text

  *Loss (SL hit):*
  - Large red ✗
  - "−10 TradePoints"
  - "−$[amount] Practice Capital"
  - Risk taken
  - Optimal comparison: "A 1% risk trade would have been [lot size], risking $[amount]"
  - Stage 1–2 only: coaching text for loss

  *Correct No-Trade:*
  - "+5 TradePoints"
  - "Good read — no setup here. [Trap type explanation]"

  *Incorrect No-Trade (valid setup skipped):*
  - "0 TradePoints — sitting out is always safe. [Setup explanation for what was missed]"

  *Neutral:*
  - "0 TradePoints — neither target was hit in this window."

- CTA: "Next Trade" or "End Session" (if final trade)

**STATE 5: SESSION COMPLETE**
- Session summary:
  - Net TradePoints this session
  - Updated TradePoints total
  - Practice Capital: opened at $X, closed at $Y, net change
  - Breakdown: W wins / L losses / N neutral / C correct no-trades
  - Session average risk %
  - Weekly growth bonus (if triggered this session)
  - Badges earned this session (animation plays)
  - Active side quest progress updates
- CTA: "Back to Career Hub"

---

### SCREEN: Career Mode Blown (Soft Restart)
**MVP:** Yes

Triggered when Practice Capital < $10.

- Career summary card: sessions completed, peak Practice Capital, best streak, total TradePoints earned in this career life
- "What you keep": TradePoints balance, all badges, mini-game unlocks (listed)
- "What you lose": Practice Capital, leverage tier progress (resets to Developing), active perks (listed), current streak
- Two options:
  - "Take the Loan — Restart with $250": initiates Soft Restart
  - "Fresh Start — Lose All Progress": skips Soft Restart, goes straight to Career Mode Death flow
- Narrative text: "Your account is gone. But you've been through [X] sessions and [Y] trades. The loan is $250. Use it differently."

---

### SCREEN: Career Mode Death (Full Restart Required)
**MVP:** Yes

Triggered when Practice Capital < $10 and Soft Restart already used.

- Full career summary (both lives if Soft Restart was used)
- "What stays with you forever": TradePoints, badges, mini-game unlocks
- Transfer prompt (if PropFunds or BizFunds > 0):
  - "Transfer funds to seed your new career. Maximum $5,000 combined."
  - PropFunds available: $X | BizFunds available: $Y
  - Transfer amount input (max $5,000 combined)
  - Processing time disclaimer: "48-hour processing delay."
- "Confirm Restart" button (greyed until transfer confirmed or explicitly skipped)
- Narrative text: "This career is closed. What you've learned stays. Start again — smarter."

---

### SCREEN: Arcade Mode Hub
**Route:** `/arcade`  
**MVP:** Yes

- Weekly Arcade leaderboard preview (top 5, user's position)
- Difficulty selector: Easy / Medium (default) / Hard (locked until $25k Practice Capital)
- "Start Arcade Session" CTA (10 challenges)
- Personal Arcade stats:
  - Sessions completed
  - Best session score (X/10)
  - Accuracy by challenge type (bar or small grid — type name + %)
- Recent sessions (last 3): score, date, TradePoints earned

---

### SCREEN: Arcade Mode — Active Session
**Route:** `/arcade/session/:sessionId`  
**MVP:** Yes

**Top bar:** Challenge X of 10 | TradePoints earned this session | Timer (if Medium/Hard)

**Challenge area:**
- Challenge type label (e.g. "Candlestick Pattern")
- Chart or candle illustration (full width)
- Question text
- Answer options (2 or 4 buttons depending on challenge type)

**On answer:**
- Correct: green flash, "+5 pts", brief explanation (1 sentence)
- Incorrect: red flash, "−2 pts", correct answer shown with brief explanation
- Speed bonus notification if applicable: "+2 speed bonus"
- Streak milestone notification if applicable

**Transition:** 1.5 seconds between challenges (answer shown during transition, then next challenge loads)

**Session Complete overlay:**
- Score: X/10
- TradePoints earned this session
- Running total
- Accuracy breakdown by type (for this session)
- Best streak this session
- Badge unlock if earned
- "Play Again" | "Back to Arcade Hub"

---

### SCREEN: PropWise Mini-Game
**Route:** `/propwise`  
**MVP:** Yes (tab visible after Elite tier or $100k unlock)

**Header:** PropFunds balance | Monthly return | "Transfer to Career Mode" CTA

**Portfolio view:**
- List of owned properties (up to 5)
- Each property: name, type (Residential/Commercial/Industrial), value, monthly return %, status
- "Buy Property" CTA (opens property marketplace)

**Property Marketplace:**
- 6–10 available properties at any time (rotated monthly)
- Each: name, type, price, projected monthly return %, description
- "Buy" button (deducts PropFunds)

**Transfer panel:**
- "Transfer PropFunds to Career Mode"
- Max transfer: $50,000/month (or $5,000 post-death restart)
- Shows: available to transfer this month, last transfer date, 48hr processing note
- Confirm transfer → 48-hour pending state shown

**Teaser:** "Want the full PropWise experience? Unlock mortgages, market cycles, and a full property portfolio in the dedicated app."
- "Download PropWise" CTA (App Store / Play Store link)
- "Transfer Progress to PropWise" CTA (available if user wants to move to dedicated app)

---

### SCREEN: CompWise Mini-Game
**Route:** `/compwise`  
**MVP:** Yes (tab visible after Master tier or $250k unlock)

Structure mirrors PropWise mini-game but with BizFunds and venture types (Retail/Tech/Services).

**Teaser:** "Want the full CompWise experience? Hire staff, manage supply chains, and compete in real markets in the dedicated app."

---

### SCREEN: Leaderboard
**Route:** `/leaderboard`  
**MVP:** Yes

**Tabs:**
- Career Mode: ranked by Practice Capital balance (global)
- Arcade: ranked by TradePoints earned in Arcade this week (global, resets Monday)

**List item per user:**
- Rank
- Avatar (with cosmetic frame if purchased)
- Username
- Country flag
- Learning badge + highest streak badge
- Career: Practice Capital balance | Arcade: weekly Arcade TradePoints

**User's own entry:** highlighted, pinned to bottom if outside visible range.

**Post-MVP tabs:** Country, Regional.

---

### SCREEN: Profile
**Route:** `/profile`  
**MVP:** Yes

**Identity section:**
- Avatar (tap to change — opens cosmetic shop or free picker)
- Username (tap to edit)
- Experience level badge
- Country
- Subscription status (Free / Pro badge)

**Career Stats:**
- Current Practice Capital
- Career Mode sessions completed
- Total decisive trades
- Win rate (all time + last 100)
- Longest win streak | Current win streak
- Best milestone reached
- Soft Restart used? (yes/no)
- Career lives: X of 2 remaining

**Arcade Stats:**
- Sessions completed
- Best session score
- Average accuracy
- Accuracy by challenge type

**Career Readiness Rating:**
- Large score (0–100) with label
- Pillar breakdown (Pro users or with analytics unlock): radar chart
- Disclaimer: "This score reflects your simulated practice performance only."

**Badge Case:**
- All earned badges (full colour, tappable for detail + earn date)
- Locked badges (greyed silhouette, tap shows unlock condition)
- Sections: Learning | Career Milestones | Streaks | Arcade | Resilience | Mini-Games

**Quest Log:**
- Active quests (progress bars)
- Completed quests (with completion date)
- "View more completed quests" pagination

**Transfer History:**
- List of mini-game → Career Mode transfers (date, amount, source, status)

---

### SCREEN: Shop
**Route:** `/profile/shop`  
**MVP:** Yes

**Tabs:**
- Subscription (TradeWise Pro)
- Content Packs
- Feature Unlocks
- Cosmetics
- Ecosystem (PropWise Starter, CompWise Starter)

**Each item shows:** name, description, price, "Buy" CTA, "Owned" state if already purchased.

**Subscription tab:** Pro feature comparison table, monthly/annual toggle, trial badge, "Subscribe" CTA.

**Restore Purchases** link at bottom of every tab.

---

## UX Rules (Apply to All Screens)

1. **No purchase prompts mid-session.** Shop is accessible only from Profile. Never surfaced during active Career Mode or Arcade sessions.
2. **No dark patterns.** No fake countdowns. No "your streak ends if you exit" fear messaging. Exit is always clean with a single confirm.
3. **Colour is never the only signal.** Win = green ✓ + text. Loss = red ✗ + text. All states are accessible without colour alone.
4. **Chart is never obscured during play states.** UI chrome minimises during STATE 1 and STATE 3.
5. **Offline core functionality.** Career Mode and Arcade Mode run fully offline (pre-loaded datasets). Sync on reconnect.
6. **Mini-game tabs are hidden, not locked.** Before unlock, the tabs simply don't exist in the nav. No greyed-out tab with a lock icon — that is a reminder of what the user doesn't have. The tabs appear as a reward at unlock.
7. **Narrative cards are skippable after 2 seconds, never immediately.** The 2-second delay ensures the user reads at least the headline.
