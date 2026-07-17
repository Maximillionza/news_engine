# MONETISATION.md — TradeWise Monetisation Design

**Version:** 0.2  
**Owner:** Masood  
**Read alongside:** PRD.md, GAME_DESIGN.md  
**Managed via:** RevenueCat

---

## Monetisation Principles

1. **No pay-to-win.** Real money never buys TradePoints, Practice Capital, leverage tiers, or competitive advantages. The leaderboard and career progression are earned, not purchased.
2. **No ads.** The product is ad-free. Revenue comes entirely from IAP and subscriptions.
3. **Purchases are visible value.** Every purchase either makes the experience more personal (cosmetics) or unlocks genuine additional content (packs, features). Nothing is paywalled that is essential to the core learning experience.
4. **Subscription is for committed users.** The subscription rewards depth of engagement with exclusive features — not by restricting the base product, but by adding to it.

---

## 1. Subscription — TradeWise Pro

**Price range (to be confirmed):** $7.99–$12.99 per month / $59.99–$89.99 per year  
**Platform:** RevenueCat (App Store + Play Store billing)

### What Pro Includes

| Feature | Free | Pro |
|---|---|---|
| Career Mode (full) | ✓ | ✓ |
| Arcade Mode (full) | ✓ | ✓ |
| Learning module (full) | ✓ | ✓ |
| Mini-games (when unlocked) | ✓ | ✓ |
| Global leaderboard | ✓ | ✓ |
| 3 active side quests | ✓ | ✓ |
| 5 active side quests | — | ✓ |
| Competition entry (Post-MVP) | Standard | Priority entry + exclusive competition |
| Detailed session analytics | Basic | Full (win rate by setup type, risk consistency chart, equity curve) |
| Session review (Stage 4) | — | ✓ (also available as one-time purchase) |
| Cosmetic pack (monthly) | — | 1 free cosmetic item per month from rotating selection |
| Early access to new datasets | — | ✓ |
| Career Readiness deep report | — | ✓ (full pillar breakdown, not just score) |
| Cloud backup of session history | 30 days | Unlimited |

### What Pro Does NOT Include

- Extra TradePoints
- Starting Practice Capital advantage
- Higher starting leverage
- Access to setups or datasets unavailable to free users (early access only, not exclusive)
- Any competitive advantage in leaderboard or competitions

### Trial

- 7-day free trial on first subscription (standard App Store / Play Store trial)
- Trial converts automatically. Cancel before day 7 to avoid charge.

---

## 2. One-Time Purchases

### 2.1 Content Packs

Content packs expand the dataset pool and learning content. They are permanent unlocks tied to the user's account (not the device).

| Pack | Price (est.) | Contents |
|---|---|---|
| **Advanced Setup Pack** | $4.99 | 15 additional Career Mode datasets (Stage 3–4 only). Introduces 2 advanced confluence variations not in the base curriculum. |
| **Arcade Challenge Pack** | $2.99 | 50 additional Arcade Mode challenges across all 7 types. Unlocks "Expert" Arcade difficulty. |
| **Strategies Pack** | $9.99 | 20 curated datasets built around 3 advanced strategies (e.g. ICT-inspired, SMC structure, momentum continuation). Each strategy has a 5-slide intro card. |
| **Market Conditions Pack** | $4.99 | 10 high-volatility datasets (news-event simulation, expansion phase moves). Stage 3+ appropriate. |

### 2.2 Feature Unlocks

| Feature | Price (est.) | Description |
|---|---|---|
| **Session Review** | $2.99 one-time | Unlocks end-of-session review for all users (not just Stage 4). Shows decision choices vs optimal choices. Also included in Pro. |
| **Detailed Analytics** | $4.99 one-time | Full session analytics dashboard: win rate by setup type, risk chart, equity curve, accuracy over time. Also included in Pro. |
| **Extra Side Quest Slot** | $1.99 one-time | Unlocks a 4th and 5th active side quest slot (replaces the Pro-only benefit for users who prefer one-time). |

### 2.3 Ecosystem Starters

These purchases seed cross-app engagement. They provide starting funds in mini-games — the only case where real money approaches the in-game economy, but it only affects the mini-games (not Career Mode which is always earned).

| Item | Price (est.) | Description |
|---|---|---|
| **PropWise Starter Pack** | $3.99 | Seeds $500 PropFunds into PropWise mini-game when it is unlocked. One-time. Does not transfer to Career Mode directly. |
| **CompWise Starter Pack** | $3.99 | Seeds $500 BizFunds into CompWise mini-game when it is unlocked. One-time. |

**Important:** These packs only activate when the mini-game is unlocked via gameplay. Purchasing before unlock stores the credit; it is applied at unlock. This preserves the progression integrity — you cannot buy your way to a mini-game, only seed it once earned.

---

## 3. Cosmetic Purchases

Cosmetics are purely aesthetic. They never affect gameplay, TradePoints, or leaderboard ranking. All cosmetics are permanent unlocks.

### 3.1 Avatar Pack

| Pack | Price (est.) | Contents |
|---|---|---|
| Starter Avatars | Free | 12 preset avatars (included at account creation) |
| Pro Trader Pack | $1.99 | 8 additional avatars (professional trading aesthetic) |
| Street Style Pack | $1.99 | 8 additional avatars (urban/streetwear aesthetic) |
| Animated Avatars Pack | $3.99 | 6 animated avatar frames (subtle animation on profile and leaderboard) |

### 3.2 Chart Theme Pack

Cosmetic reskins of the chart colour scheme, candlestick style, and background.

| Theme | Price (est.) | Description |
|---|---|---|
| Classic (default) | Free | Standard green/red candles, dark background |
| Midnight | $1.99 | Deep navy background, cyan/coral candles |
| Terminal | $1.99 | Green-on-black terminal aesthetic |
| Champagne | $1.99 | Gold/charcoal palette (luxury editorial) |
| High Contrast | Free | Accessibility-optimised high contrast theme |

### 3.3 Badge Frame Pack

Decorative frames that appear around badge icons on the user's profile and leaderboard entry.

| Frame | Price (est.) | Description |
|---|---|---|
| Gold Frame | $0.99 | Gold border on all badges |
| Animated Frame | $2.99 | Subtle glow/pulse animation on badge display |
| Platinum Frame | $1.99 | Silver-platinum gradient border |

### 3.4 UI Accent Pack

Reskins the accent colour and button style of the app UI.

| Pack | Price (est.) | Description |
|---|---|---|
| Electric Teal | $0.99 | Teal accent throughout UI |
| Crimson | $0.99 | Deep red accent |
| Arctic | $0.99 | Ice blue/white minimal aesthetic |

---

## 4. IAP Catalogue — RevenueCat Configuration

### Product ID Naming Convention

All product IDs follow: `tradewise.[type].[name]`

Examples:
- `tradewise.sub.pro_monthly`
- `tradewise.sub.pro_annual`
- `tradewise.pack.advanced_setup`
- `tradewise.cosmetic.chart_midnight`
- `tradewise.feature.session_review`
- `tradewise.ecosystem.propwise_starter`

### Entitlement Structure (RevenueCat)

| Entitlement | Products That Grant It |
|---|---|
| `pro` | pro_monthly, pro_annual |
| `session_review` | pro_monthly, pro_annual, feature.session_review |
| `detailed_analytics` | pro_monthly, pro_annual, feature.detailed_analytics |
| `extra_quest_slots` | pro_monthly, pro_annual, feature.extra_quest_slot |
| `content_advanced_setup` | pack.advanced_setup |
| `content_arcade_challenge` | pack.arcade_challenge |
| `content_strategies` | pack.strategies |
| `content_market_conditions` | pack.market_conditions |
| `cosmetic_[name]` | Individual cosmetic products |
| `ecosystem_propwise_starter` | ecosystem.propwise_starter |
| `ecosystem_compwise_starter` | ecosystem.compwise_starter |

---

## 5. Purchase Flow UX Rules

1. **No paywalls on core gameplay.** A free user can complete the full learning module, play Career Mode indefinitely, play Arcade Mode indefinitely, and unlock both mini-games through gameplay. Real money accelerates or personalises, never gates.

2. **Shop is accessible, not intrusive.** The shop tab is visible in the nav. It is never pushed via popups, interstitials, or after-loss prompts. "Your account was blown. Want to buy a restart?" is explicitly prohibited.

3. **Contextual soft prompts are allowed.** When a user views their badge case and sees a greyed-out animated frame, a subtle "Unlock in Shop" label is acceptable. This is different from a popup.

4. **Purchase confirmation always shown.** Standard App Store/Play Store confirmation handles this, but no purchase should be triggerable with a single tap.

5. **Restore purchases always available.** Settings → Restore Purchases. Required by both App Store and Play Store policies.

6. **No ecosystem starter packs during Career Mode session.** These are only surfaced in the mini-game screens and shop, never during active trading.

---

## 6. Revenue Projections (Illustrative — Not Commitments)

Based on mobile gaming benchmarks for skill-based games with no ads:

| Metric | Conservative | Moderate |
|---|---|---|
| Monthly Active Users (6 months post-launch) | 10,000 | 50,000 |
| Subscription conversion (of 30-day actives) | 8% | 15% |
| Average subscription revenue per user | $9.99/month | $9.99/month |
| IAP conversion (any one-time purchase) | 5% | 10% |
| Average IAP spend per purchasing user | $6.00 | $9.00 |
| Monthly subscription revenue | ~$800 | ~$7,500 |
| Monthly IAP revenue | ~$500 | ~$4,500 |
| **Total monthly revenue** | ~$1,300 | ~$12,000 |

These figures validate the model is viable at moderate scale. The path to meaningful revenue is user growth + retention, not conversion rate optimisation of a small base.
