# GAME_DESIGN.md — TradeWise Game Design Document

**Version:** 0.2  
**Owner:** Masood  
**Read alongside:** PRD.md, LEARNING_THEORY.md, MONETISATION.md

---

## Design North Star

Every mechanic in TradeWise must pass this test: **does it make the user a better trader, or does it make the game more addictive at the expense of learning?**

Addictive mechanics that teach nothing are rejected. Educational mechanics that feel like homework are redesigned until they're fun. The goal is the overlap: mechanics that are genuinely engaging AND that build real trading cognition.

---

## 1. Career Mode — Full Design

### 1.1 The Narrative Frame

Career Mode is not framed as a quiz. It is framed as a trading career. The user is a trader who started with $500. The world of the game takes that premise seriously.

Narrative touchpoints:
- First launch: "You've opened your first trading account. $500. This is where it starts."
- First milestone ($1,000): "You doubled your account. Most traders never get here."
- First loss streak: "Every trader faces this. What separates them is what they do next."
- Soft Restart: "Your account is gone. But your knowledge isn't. Here's $250 — a loan, not a gift."
- Career Death: "This account is closed. But the lessons stay. Start again — smarter."

Narrative cards appear at key moments. They are single-screen, skippable after 2 seconds, but designed to be read. Tone: honest, not patronising, not cheerful. The game takes the user seriously.

### 1.2 Session Flow (Full Detail)

**Step 1: Session initiation**
- User taps "Trade" from Home screen
- Session select screen shows: instrument (EURUSD in MVP), current Practice Capital, current leverage tier
- "Start Session" CTA

**Step 2: Pre-session briefing (Stage 3+ only)**
- For users in Stage 3 (151–300 sessions) and Stage 4 (301–500+): a 3-line market context card is shown before the session. Example: "Current dataset condition: Ranging market. Key level at 1.0850. Session contains 5 trade opportunities."
- Stage 1 and 2: no briefing (information would overwhelm new users)

**Step 3: Chart plays at 5× speed to decision point**
- Chart scrolls through historical candles at 5× speed
- A brief visual cue (subtle pulse on chart border) signals the approach to a decision point
- Chart pauses at trigger_candle_index

**Step 4: Decision phase**
- Charting tools available (tier-dependent — see Leverage Unlock Tiers in PRD.md FR-010)
- Timeframe toggle available (tier-dependent)
- User commits: Direction + Lot Size + SL + TP
- "No Trade" always available regardless of tier
- "Lock In" button activates only when all required fields are populated
- For Stage 1–2 users: lot size picker is simplified (3 options: conservative/moderate/aggressive). Labels chosen to teach, not to just pick a number.
- For Stage 3–4 users: full lot size input (0.01 increments) with live risk % calculator shown as user adjusts

**Step 5: Chart plays to outcome**
- SL and TP levels shown as horizontal lines on chart
- Chart plays at 5× to outcome_candle_index
- Outcome overlay: result icon + Practice Capital change + TradePoints change

**Step 6: Post-trade card**
- Direction: correct or incorrect
- Practice Capital impact: +$X or −$X
- Risk taken: X% of Practice Capital
- Optimal 1% risk trade: "A 1% risk trade on this setup would have been [lot size], risking $[amount]"
- Stage 1 only: setup label + coaching text

**Step 7: Next trade or session end**
- If more trade opportunities: brief transition (1 second), chart scrolls to next decision point
- If session complete: Session Summary screen

### 1.3 Session Summary Screen

Displayed at end of every Career Mode session.

Shows:
- Total TradePoints earned/lost this session (net)
- Running TradePoints total
- Practice Capital: opening and closing balance for the session
- Win/loss/neutral/correct no-trade breakdown
- Session risk average: average % risk per decisive trade
- Weekly growth bonus notification (if applicable — see FR-012)
- Badges earned this session (with animation if any)
- CTA: "Back to Home"

### 1.4 Leverage Tiers — Full Design

Leverage tiers are the primary progression mechanic in Career Mode. They are deliberately not tied to account balance (which would incentivise reckless risk to hit a number) but to TradePoints (which reward consistent, skilled trading over time).

Each tier unlock is a moment of celebration in the app. Full-screen unlock animation. Brief tooltip explaining the new capability.

| Tier | TradePoints | Leverage | Feature Unlocked |
|---|---|---|---|
| Starter | 0 | 1:10 | Career Mode access. Horizontal line tool only. 5M timeframe only. |
| Developing | 2,500 | 1:20 | Fibonacci retracement tool. |
| Intermediate | 7,500 | 1:30 | 15M timeframe. Trendline tool. |
| Advanced | 15,000 | 1:50 | 1H timeframe. Multi-confluence label overlay (Stage 3 datasets unlocked). |
| Elite | 30,000 | 1:100 | PropWise mini-game tab appears. 1-minute timeframe. |
| Master | 75,000 | 1:200 | CompWise mini-game tab appears. Full custom lot size input. |

**Leverage choice is always the user's.** Unlocking 1:50 does not force 1:50. The tier defines the ceiling, not the floor. Coaching nudge shown when user consistently uses maximum available leverage: "Elite traders rarely use maximum leverage. Your current leverage is [X]. Consider [X/2]."

### 1.5 Blow-Up Mechanic — Full Design

#### Soft Restart

Trigger: Practice Capital < $10 (account effectively blown).

Screen shown: "Career Mode Blown"
- Summary of career to date: sessions completed, best win streak, highest account balance reached, badges earned
- Explanation of what is retained vs lost
- Two options: "Take the Loan ($250)" or "Restart Fresh (lose all progress)"
- If "Take the Loan": Soft Restart initiated. One-time per Career Mode life.

**Retained on Soft Restart:**
- TradePoints balance (fully retained)
- All badges earned
- All mini-game unlocks (tabs remain visible)
- Learning module completion
- PropFunds and BizFunds in mini-games (unaffected)

**Lost on Soft Restart:**
- Practice Capital (replaced with $250 loan)
- Leverage tier: resets to Developing (1:20) regardless of prior tier — must rebuild
- Active perks (see Perks section below)
- Current win streak

**Loan framing in UI:**
- Practice Capital display shows: "Balance: $180 | Loan Outstanding: $250"
- Once Practice Capital exceeds $250, loan is "cleared". Narrative card: "Loan repaid. Back on your own capital."
- Loan clearance does NOT restore lost leverage tier — user must continue earning TradePoints.

#### Career Mode Death

Trigger: Practice Capital < $10 after Soft Restart has been used.

Screen shown: "Career Mode Ended"
- Summary of full career (both lives)
- Comparison: Life 1 vs Life 2 performance
- What is retained permanently (TradePoints, badges, mini-game progress)
- Transfer prompt: "You have $[X] in PropFunds and $[Y] in BizFunds. Transfer up to $5,000 combined to seed your new account?"
- If transfer confirmed: 48-hour processing delay shown. "Your funds are being transferred. Your new career starts [date/time]."
- "Restart Career" button (greyed out until transfer resolves or user skips transfer)

**New career starting capital:**
- Base: $500
- Plus transferred mini-game funds: max $5,000 combined from PropWise + CompWise
- Maximum new starting capital: $5,500

**What the new career inherits:**
- TradePoints (retained fully)
- All badges (retained)
- Mini-game unlocks (retained — tabs visible immediately)
- Career-level leverage tier: resets to Starter (1:10). Must be rebuilt.

### 1.6 Perks System

Perks are passive bonuses that Career Mode users earn through milestones. They are lost on Soft Restart (not on Career Mode Death — Death resets everything including perks).

Perks are designed to make progression feel meaningful without creating pay-to-win dynamics.

| Perk | Unlock Condition | Effect | Lost on Soft Restart? |
|---|---|---|---|
| Risk Advisor | Complete Risk Management module | Post-trade card shows optimal lot size | No (module-based, not career-based) |
| Streak Shield | 20-win streak achieved | First loss after a 10+ streak does not break streak (one-time use per streak) | Yes |
| Growth Bonus | Practice Capital reaches $10,000 | Weekly growth bonus TradePoints increased by 20% | Yes |
| Market Sense | 300 sessions completed | Pre-session briefing unlocked for Stage 1–2 users | Yes |
| Loan Negotiator | Soft Restart completed without blowing second account | Starting capital for next Career Mode Death restart increases to $750 (base) | Permanent once earned |

Perks are shown in the Profile screen. Lost perks are shown as greyed-out with "Lost in restart — re-earn" tooltip.

---

## 2. Arcade Mode — Full Design

### 2.1 Design Intent

Arcade Mode is the training ground for isolated analytical skills. Where Career Mode tests the full trading decision (direction + size + SL/TP under account pressure), Arcade Mode isolates individual skills and tests them rapidly. It is designed to be:
- Playable in 3–5 minutes
- Completable without entering Career Mode
- A daily habit driver (quick, satisfying, measurable improvement over time)
- A valid entry point for users who haven't started Career Mode yet

### 2.2 Challenge Types (Full)

**1. Setup Identification**
Chart pauses at a decision point. User selects: Buy / Sell / No Trade.
- Stage-appropriate difficulty (same dataset system as Career Mode)
- No lot size or SL/TP input — direction only
- Correct: +5 TradePoints. Incorrect: −2.

**2. Candlestick Pattern Recognition**
Single candle or 2–3 candle formation displayed (zoomed, isolated from wider chart context).
User selects from 4 labelled options: e.g. "Bullish Engulfing", "Doji", "Hammer", "Shooting Star".
- 4 options always include 1 correct + 3 plausible distractors
- Correct: +5. Incorrect: −2.
- After answer: brief explanation shown (1 sentence, name + what it signals)

**3. Reversal vs Pullback**
A section of price action shown. User selects: "Reversal" or "Pullback".
- Must be an unambiguous example in Stage 1. Increasingly ambiguous in Stage 2+.
- Correct: +5. Incorrect: −2.
- After answer: the key differentiating feature highlighted on the chart

**4. Bollinger Band Reading**
Chart shown with Bollinger Bands overlaid. A specific candle or zone is highlighted.
Question type rotates between:
- "Where is price relative to the band?" (options: upper band, lower band, midline, outside band)
- "What does this Bollinger Band squeeze suggest?" (options: volatility expanding, volatility contracting, no signal, trend continuation)
- "Is this a mean reversion opportunity or a breakout?" (context-dependent)
- Correct: +5. Incorrect: −2.

**5. Market Structure Classification**
A chart section is shown. User classifies: Trending Up / Trending Down / Ranging / Compression.
- Correct: +5. Incorrect: −2.
- After answer: key structural features annotated

**6. Support or Resistance**
A horizontal level is marked on the chart with price approaching it.
User selects: "Support" or "Resistance".
- Requires reading price history context (price came from above or below)
- Correct: +5. Incorrect: −2.

**7. Next Move Prediction**
Chart shown up to a specific candle. That candle's close is hidden.
User selects the most likely next candle from 4 illustrated options (shown as candle illustrations, not labels).
- Hardest challenge type. Unlocked from Medium difficulty upward.
- Correct: +5. Incorrect: −2.

### 2.3 Session Structure

- 10 challenges per session
- Challenge types drawn from the pool, weighted by user's weak areas (types they answer incorrectly most often get slightly higher frequency — adaptive)
- Session score shown at end: X/10 correct, TradePoints earned, accuracy %
- Accuracy tracked over time (profile: "Candlestick Pattern accuracy: 73%")

### 2.4 Arcade Mode Streak

Consecutive correct answers within a session only (not cross-session — Arcade streaks are in-session only to keep sessions discrete).

| Consecutive Correct | Bonus |
|---|---|
| 5 | +10 bonus TradePoints |
| 7 | +15 bonus TradePoints |
| 10 (perfect session) | +25 bonus TradePoints + "Perfect Session" badge animation |

---

## 3. Points Economy — Unified Rules

### 3.1 TradePoints Sources

| Source | Amount | Notes |
|---|---|---|
| Career Mode win | +10 (×multiplier) | Streak multiplier applied |
| Career Mode loss | −10 | No multiplier |
| Career Mode correct No-Trade | +5 | Flat |
| Career Mode weekly growth bonus | +50 to +300 | Tier-dependent on % growth |
| Arcade correct answer | +5 | Per challenge |
| Arcade incorrect answer | −2 | Per challenge |
| Arcade speed bonus | +2 | Answer within 10 seconds |
| Arcade in-session streak (5/7/10) | +10/+15/+25 | One per streak level per session |
| Learning module completion | +200 | One-time |
| Risk management module completion | +50 | One-time |
| Practice Capital milestone | +100 to varies | See FR-011 |
| Badge unlock | +25 | Each new badge (not star upgrades) |

### 3.2 TradePoints Sinks

TradePoints are spent only through the unlocking of leverage tiers (they are consumed by progression, not spent on items — purchases use real money). This means TradePoints can only go up through gameplay. They go down only through Career Mode losses and Arcade incorrect answers.

The floor of 100 ensures the user never reaches zero.

### 3.3 Leaderboard Ranking

The Career Mode leaderboard ranks by **Practice Capital balance**, not TradePoints. This creates two separate competitive dimensions:
- TradePoints → progression, unlock gates, Arcade leaderboard
- Practice Capital → Career Mode prestige leaderboard

A user with high TradePoints but a blown account (during restart) will rank lower on the Career Mode leaderboard. This is intentional — it reflects the actual state of their trading career.

---

## 4. Badge Catalogue (Full)

### Learning Badges
| Badge | Trigger |
|---|---|
| Bronze Learning Badge | Learning module completed as Beginner |
| Silver Learning Badge | Learning module completed as Amateur |
| Gold Learning Badge | Learning module completed as Professional |

### Career Milestone Badges
| Badge | Trigger |
|---|---|
| First Double | Practice Capital reaches $1,000 |
| Five Figure Trader | Practice Capital reaches $10,000 |
| Quarter Century | Practice Capital reaches $25,000 |
| Half Century | Practice Capital reaches $50,000 |
| Six Figure Trader | Practice Capital reaches $100,000 |
| Quarter Million | Practice Capital reaches $250,000 |
| TradeWise Legend | Practice Capital reaches $1,000,000 |

### Win Streak Badges
| Badge | Stars | Trigger |
|---|---|---|
| Bronze Streak | ⭐ | 5-win streak |
| Bronze Streak | ⭐⭐ | 10-win streak |
| Bronze Streak | ⭐⭐⭐ | 20-win streak |
| Silver Streak | ⭐ | 20-win streak |
| Silver Streak | ⭐⭐ | 35-win streak |
| Silver Streak | ⭐⭐⭐ | 50-win streak |
| Gold Streak | ⭐ | 50-win streak |
| Gold Streak | ⭐⭐ | 75-win streak |
| Gold Streak | ⭐⭐⭐ | 100-win streak |

### Arcade Badges
| Badge | Trigger |
|---|---|
| Quick Draw | 5 consecutive correct Arcade answers within 10 seconds each |
| Pattern Master | 90%+ accuracy on Candlestick Pattern challenges over 50 attempts |
| Structure Scout | 90%+ accuracy on Market Structure challenges over 50 attempts |
| Perfect Session | 10/10 correct in a single Arcade session |
| Arcade Champion | Top 10 on weekly Arcade leaderboard |

### Resilience Badges
| Badge | Trigger |
|---|---|
| Comeback Kid | Reach $1,000 Practice Capital after a Soft Restart |
| Phoenix | Complete Career Mode Death and reach $5,000 in new career |
| Loan Repaid | Clear the Soft Restart loan (Practice Capital exceeds $250 after soft restart) |

### Mini-Game Badges
| Badge | Trigger |
|---|---|
| Property Mogul | Unlock PropWise mini-game |
| Business Builder | Unlock CompWise mini-game |
| Cross-Platform Pioneer | Transfer progress to a dedicated app (PropWise or CompWise) |

---

## 5. Side Quests

Side quests are optional narrative-driven objectives that appear alongside Career Mode. They provide focused goals, break up the monotony of open-ended trading sessions, and teach specific skills.

### Quest Types

**Skill Quests** — "Win 5 trades in a row using a Key Level + Candlestick setup"
- Teach specific confluence execution
- Reward: bonus TradePoints + cosmetic item

**Discipline Quests** — "Complete 10 sessions with average risk below 1.5%"
- Teach risk management consistency
- Reward: bonus TradePoints + Perk unlock

**Recovery Quests** — Appear after Soft Restart only: "Rebuild your account to $500 from $250"
- Reward: Comeback Kid badge + Streak Shield perk restored

**Exploration Quests** — "Complete 3 sessions in a ranging market dataset"
- Encourage exposure to all market conditions
- Reward: bonus TradePoints

**Mini-Game Quests** — Appear after mini-game unlock: "Invest in your first PropWise property"
- Bridge the user from Career Mode to the mini-game
- Reward: PropFunds seed amount ($100 starting PropFunds — one-time)

### Quest Display

- Active quests shown on Home screen (max 3 active simultaneously)
- Quest log accessible from Profile
- Completed quests archived with completion date
- Quest refresh: new quests offered on session completion (not time-based — prevents pressure)
