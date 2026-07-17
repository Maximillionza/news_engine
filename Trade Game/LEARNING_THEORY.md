# LEARNING_THEORY.md — TradeWise Pedagogical Framework

**Version:** 0.2  
**Owner:** Masood

---

## Why This Document Exists

The game design is only as good as the learning it delivers. This document defines what competence looks like at each stage, what cognitive skills the app is building, and how the session architecture evolves across 500 Career Mode sessions. Every feature in the trading loop must be validated against this before build.

---

## 1. The Four Competency Pillars

| Pillar | What It Means | How TradeWise Trains It | Risk If Skipped |
|---|---|---|---|
| **Market Structure Literacy** | Can identify trend, range, compression, key levels across timeframes | Curated datasets covering all conditions. Arcade Market Structure challenges. Timeframe toggle during decision phase. | User only wins in trending markets. Falls apart in ranges. |
| **Pre-Hoc Conviction** | Commits to a directional bias BEFORE price moves, not after | Core mechanic: chart pauses before the move. All inputs locked before chart plays. | Without this, user learns post-hoc labelling — can analyse past charts, freezes in real-time. |
| **Risk Mechanics** | Correctly applies lot sizing, SL placement, and risk-per-trade % as live constraints | Practice Capital system. Lot size input with live risk % display. Post-trade equity impact card. | User develops directional skill with no position discipline. Will overleverage a live account immediately. |
| **Psychological Discipline** | Knows when NOT to trade. Consistent process under losing streaks. | No Trade option at every decision point. Points floor (no death spiral). Streak cooldown in Stage 4. | User trained to always have a position. Overtrading is the most cited cause of retail losses. |

---

## 2. The Pre-Hoc vs Post-Hoc Distinction

**Post-hoc (what most tools train):** Chart plays. User watches price move. User labels what happened. This trains recognition of completed patterns — not real-time decision-making.

**Pre-hoc (what TradeWise trains):** Chart pauses. User sees only the setup forming. User commits to direction, size, SL, TP before seeing outcome. Chart plays.

This is the difference between "I can analyse a chart in hindsight" and "I can make a decision in real-time." The first is easy. The second is what separates profitable traders.

**Developer rule:** Any feature that lets the user observe price movement before committing to a trade decision breaks this mechanic. Flag it, escalate to Masood, do not build it.

---

## 3. Stage Progression Architecture

### Stage 1 — Foundation (Career Mode Sessions 1–50)
**User state:** Overwhelmed. High churn risk. Doesn't know what to look for.

- Clean, unambiguous setups only. No traps.
- Setup label shown on post-trade card (after outcome, not before)
- Lot size: 3 options labelled Conservative / Moderate / Aggressive (not raw numbers)
- SL/TP: preset only (tight/moderate/wide)
- "No Trade" available but not penalised if valid setup was missed
- Coaching card shown after every trade
- 3 decision points per session

### Stage 2 — Pattern Recognition (Sessions 51–150)
**User state:** Recognises individual signals. Struggles to combine into confluences.

- 2-component confluence setups introduced
- 25% of decision points are traps (No Trade is correct)
- Lot size labels shift toward numbers with percentage context shown
- SL/TP: 3 preset options (must choose, not auto-selected)
- Post-trade card shows risk % impact ("You risked 2.3% of your Practice Capital")
- Coaching card on losses only
- 4–5 decision points per session

### Stage 3 — Confluence Mastery (Sessions 151–300)
**User state:** Can identify setups. Inconsistent risk management. May overtrade.

- Full 5-setup curriculum active
- All market conditions present
- 35% of decision points are traps
- Lot size: full range with live risk % calculator (shown before confirmation)
- SL/TP: 5 presets or user-defined (Pro or feature unlock)
- Session risk budget concept: warning (not block) if single trade exceeds 2% of Practice Capital
- Pre-session briefing card (market condition, key level context)
- 5–7 decision points per session

### Stage 4 — Independence (Sessions 301+)
**User state:** Internalising setups. Developing personal edge.

- All setups, all conditions, no labels
- 40% of decision points are traps
- No coaching cards (loss result only)
- User-defined SL/TP default
- Session review screen available (end-of-session, shows all decision points with user choice vs optimal)
- Streak cooldown: if 15+ win streak, 1 in 5 sessions is deliberately ambiguous (Hard Mode, unlabelled)
- Career Readiness Rating visible and updated after each session

---

## 4. The No-Trade Mechanic — Why It Cannot Be Removed

Overtrading kills new traders. They take a position on every setup because inaction feels like wasted time. In reality, the best traders are highly selective — they avoid 80% of potential setups.

The No Trade option appears at every decision point. The correct answer at many points is No Trade. Points are awarded for correct No Trade selections. No points are deducted for incorrect No Trade (sitting out is always safe).

This mechanic will face pressure in design reviews because it "reduces engagement" (fewer trades per session = fewer point events). Do not remove it. It is the most important pedagogical feature in the app after the pre-hoc mechanic.

---

## 5. Risk Mechanics as a Live Experience

Risk management cannot be taught by a quiz. It must be experienced as a financial consequence — even simulated.

TradeWise implements this through the Practice Capital system:
- Every lot size decision has real pip-value consequences on the $500 simulated account
- A 50-pip SL on 0.10 lots = −$50 Practice Capital if hit = 10% of starting account
- This is shown before the trade locks in AND after the outcome
- The margin call simulation at ~10% of starting capital creates the visceral experience of overleveraging — safely

Over hundreds of trades, this builds an internalised sense of position sizing. No written lesson produces the same result.

Post-trade card must always show:
1. Direction: correct or incorrect
2. Risk taken: [lot size] × [SL pips] × [pip value] = $[amount] = [%] of Practice Capital
3. Outcome: ±$[amount] to Practice Capital
4. Optimal 1% risk: what a disciplined trade would have looked like

---

## 6. Arcade Mode Pedagogy

Arcade Mode develops isolated analytical skills at speed. It is not a substitute for Career Mode — it is a complement.

Career Mode trains: full decision sequence under account pressure.
Arcade Mode trains: rapid pattern identification, vocabulary, visual fluency.

A user who plays Arcade Mode heavily but avoids Career Mode will develop fast pattern recognition but poor risk discipline. A user who does Career Mode only may develop good decision-making but slow pattern identification. Both modes together produce the most rounded practitioner.

This is by design. Neither mode is complete alone. The interplay between them is the product.

---

## 7. What 500 Sessions Means

A user who completes 500 Career Mode sessions with serious engagement will have:
- Made approximately 2,000–3,000 individual trade decisions
- Practised all 5 core confluence setups across all 4 market conditions
- Made hundreds of position sizing decisions with real equity consequence
- Experienced at least one significant Practice Capital drawdown
- Developed a personal preference pattern across setup types

The Career Readiness Rating aggregates this. A user with 500 sessions and a score of 30 is not ready. A user with 250 sessions and a score of 75 may be more prepared than most with 500.

**The app never tells the user they are ready to trade live.** It reflects practice quality. The user decides when to cross that line. The disclaimer on the Career Readiness Rating exists precisely because this distinction matters.
