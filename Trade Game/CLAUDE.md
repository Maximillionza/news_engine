# CLAUDE.md — TradeWise: Cowork Session Context

## Read This First, Every Session

This is the master context document. Read it before touching any other file. It overrides memory from prior sessions. Everything Cowork needs to know about conventions, constraints, and critical decisions lives here or is referenced here.

---

## Product Identity

**App Name:** TradeWise  
**Tagline:** "Learn to trade. For real."  
**Platform:** Mobile-first. iOS + Android. React Native (Expo managed workflow).  
**Stage:** Pre-build. These documents are the source of truth. No production code exists.

---

## One-Line Product Definition

TradeWise is a gamified trading education platform where users build a simulated trading career — learning confluence identification, risk management, and market analysis — through structured modes that progressively unlock deeper financial simulation games as their skill and account grow.

---

## What TradeWise Is NOT

- Not a broker or live trading platform
- Not a gambling product (see REGULATORY_NOTES.md before building any cash prize feature)
- Not a paper trading tool with live data (MVP uses historical datasets only)
- Not a signals service or financial advisor

---

## The Three-App Ecosystem

TradeWise is the entry point to a three-app ecosystem. All apps share a common identity layer (Apple ID / Google ID).

| App | Status | Description |
|---|---|---|
| **TradeWise** | Building now | Core trading education + Career Mode + Arcade Mode + mini-versions of PropWise and CompWise |
| **PropWise** | Future (separate app) | Full property investment simulation game |
| **CompWise** | Future (separate app) | Full business-building simulation game |

Users unlock PropWise and CompWise mini-games inside TradeWise by hitting Career Mode milestones. The mini-games are simplified. The dedicated apps are the full experience. Progress earned in a TradeWise mini-game is transferable to the dedicated app via shared Apple/Google ID.

**Architecture implication:** TradeWise, PropWise, and CompWise share a single authentication backend (Supabase, same project). Cross-app progress transfer is an API call, not a manual process. See ARCHITECTURE.md.

---

## Document Map

| Document | Read When |
|---|---|
| `CLAUDE.md` (this) | Every session, first |
| `PRD.md` | Feature decisions, scope questions, MVP vs post-MVP |
| `GAME_DESIGN.md` | Any work touching Career Mode, Arcade Mode, progression, economy |
| `LEARNING_THEORY.md` | Any feature touching the trading loop, curriculum, skill progression |
| `FEATURE_SPEC.md` | Screen-by-screen build work |
| `DATA_SCHEMA.md` | Database, API, or model work |
| `ARCHITECTURE.md` | Infrastructure, stack, cross-app design |
| `MONETISATION.md` | IAP, subscriptions, cosmetics, pricing |
| `CONTENT_SPEC.md` | Confluence definitions, dataset curation, curriculum arc |
| `REGULATORY_NOTES.md` | Competitions, prizes, disclaimers, jurisdiction risks |
| `ROADMAP.md` | Phasing questions, MVP vs post-MVP scope |

---

## Core Mechanic — Pre-Hoc Decision Loop (Non-Negotiable)

The chart **pauses before price moves**. The user commits to direction, lot size, SL, and TP **before** the chart plays. This is the single most important design constraint. Any feature that lets the user observe price movement before committing breaks the educational premise.

Flag and escalate any proposed deviation from this to Masood before building.

---

## Modes Summary

| Mode | Purpose | MVP |
|---|---|---|
| **Career Mode** | Main game. $500 simulated account. Build to milestones. Unlock mini-games. | Yes |
| **Arcade Mode** | Skill testing. Identify setups, patterns, and chart concepts under time pressure. | Yes |
| **Competitions** | Monthly challenges with prizes. Individual + leaderboard. | Post-MVP (legal gate) |

---

## Career Mode Economy — Critical Rules

1. Starting capital: **$500** simulated. Low leverage (1:10).
2. Leverage unlocks as TradePoints accumulate — not as account balance grows.
3. Account blown → **Soft Restart**: $250 loan. Certain perks lost. Mini-game unlocks retained.
4. Soft Restart account blown → **Career Mode Dead**. Full restart required.
5. On full restart: mini-game progress retained. If mini-game funds accumulated, user may transfer **max $5,000** to new career start (raising starting capital above $500).
6. Normal play (no blown account): user may transfer **max $50,000 per mini-game per month** into Career Mode.
7. Mini-game to Career Mode transfers go through a 48-hour processing delay (prevents abuse).
8. Career Mode to mini-game transfers: **not allowed**. Flow is one-directional: mini-game → Career Mode only.

---

## Monetisation Model (No Ads)

Three revenue streams:
1. **One-time purchases** — feature unlocks, expanded content packs
2. **Cosmetic purchases** — avatars, badge skins, UI themes, chart colour schemes
3. **Subscription (TradeWise Pro)** — recurring. Unlocks exclusive features, priority competition entry, expanded content. Does NOT give trading advantages (no extra leverage, no better setups).

See MONETISATION.md for full item catalogue and pricing framework.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile framework | React Native (Expo managed workflow) |
| Language | TypeScript |
| Navigation | React Navigation v6 |
| State management | Zustand |
| Chart rendering | TradingView Lightweight Charts via WebView |
| Backend / DB | Supabase (shared across TradeWise, PropWise, CompWise) |
| Payments / IAP | RevenueCat |
| Analytics | PostHog |
| Error tracking | Sentry |
| CI/CD | Expo EAS Build |

---

## Naming Conventions

- Feature flags: `MVP_` prefix for MVP, `POST_MVP_` for deferred
- Database tables: `snake_case`
- React components: `PascalCase`
- Simulated money in Career Mode: **"Practice Capital"** — never "balance", "funds", or "$" without context
- Points currency: **"TradePoints"** — never "coins" or "tokens"
- Mini-game simulated money: **"PropFunds"** (PropWise), **"BizFunds"** (CompWise)
- Readiness metric: **"Career Readiness Rating"** — never "ready to trade live" as a binary

---

## Owner

Project owner: Masood. All unresolved ambiguity gets flagged before building.
