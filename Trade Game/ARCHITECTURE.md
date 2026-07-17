# ARCHITECTURE.md — TradeWise System Architecture

**Version:** 0.2  
**Owner:** Masood

---

## 1. Architecture Principles

1. **Shared identity layer.** TradeWise, PropWise, and CompWise share a single Supabase project and auth system. Apple ID / Google ID is the universal key.
2. **Offline-first for core gameplay.** Career Mode and Arcade Mode run on pre-loaded datasets. Network is not required for active sessions.
3. **Server-authoritative economy.** TradePoints, Practice Capital, badges, and transfers are computed and written server-side. The client never self-awards.
4. **Thin client.** Business logic lives in Supabase Edge Functions or PostgreSQL functions — not in React Native. This makes PropWise and CompWise apps cheaper to build (they share the same backend).
5. **No live market data in MVP.** Eliminates data licensing costs, network dependency, and latency risk in core gameplay.

---

## 2. Three-App Ecosystem Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                    Shared Supabase Project                        │
│                                                                   │
│  Auth (Apple ID / Google ID → Supabase UUID)                     │
│  Shared tables: users, user_profiles, user_badges,               │
│                 subscriptions, fund_transfers                     │
│                                                                   │
│  App-specific tables:                                             │
│  TradeWise: career_lives, career_sessions, trades,               │
│             arcade_sessions, arcade_answers,                      │
│             minigame_propwise, minigame_compwise                  │
│  PropWise (future): propwise_full_portfolio, mortgages, ...      │
│  CompWise (future): compwise_full_ventures, staff, ...           │
└─────────────────┬──────────────────────────────────┬─────────────┘
                  │                                  │
       ┌──────────▼──────────┐            ┌──────────▼──────────┐
       │     TradeWise       │            │  PropWise / CompWise │
       │  (React Native)     │            │  (React Native)      │
       │  Building now       │            │  Future builds       │
       └─────────────────────┘            └─────────────────────┘
```

**Cross-app transfer flow:**
1. User in TradeWise mini-game taps "Transfer to PropWise"
2. TradeWise calls Edge Function `initiate_cross_app_transfer`
3. Edge Function validates: mini-game unlocked, monthly cap not exceeded, no pending transfer
4. Creates `fund_transfers` row with `status: 'pending'`, `completes_at: now() + 48h`
5. After 48h: scheduled function processes transfer, updates `minigame_propwise.prop_funds_cents`
6. When user opens PropWise app (same Apple/Google ID): queries the shared prop funds balance
7. PropWise app reads from the same Supabase project — no API bridge needed

---

## 3. TradeWise App Architecture

```
┌─────────────────────────────────────────────────────┐
│                  TradeWise Mobile App               │
│              (React Native / Expo)                  │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Chart View  │  │  Game Engine │  │  Screens  │  │
│  │ (WebView +  │  │  (Zustand)   │  │  (RN)     │  │
│  │ TW Charts)  │  │              │  │           │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘  │
│         └────────────────┴──────────────── ┘        │
│                           │                         │
│         ┌─────────────────┼──────────────────┐      │
│    SQLite (expo-sqlite)  Zustand         AsyncStorage│
│    - OHLCV datasets      - session state  - auth    │
│    - arcade challenges   - user prefs     - tokens  │
│    - session cache       - pending sync             │
└───────────────────────────┬─────────────────────────┘
                            │ HTTPS / Supabase Realtime
                            │
┌───────────────────────────▼─────────────────────────┐
│                      Supabase                        │
│                                                     │
│  Auth │ PostgreSQL (RLS) │ Edge Functions            │
│  Storage │ Scheduled Jobs │ Realtime (Post-MVP)      │
└────────┬───────────────────────────┬────────────────┘
         │                           │
  ┌──────▼──────┐           ┌────────▼───────┐
  │ RevenueCat  │           │  PostHog       │
  │ (IAP / Sub) │           │  (Analytics)   │
  └─────────────┘           └────────────────┘
```

---

## 4. Chart Rendering Architecture

TradingView Lightweight Charts is the target library. It runs in a browser context and requires a WebView bridge in React Native.

### WebView Bridge Protocol

**Files:**
- `assets/chart/chart.html` — bundled static HTML, loads TW Lightweight Charts from bundle (not CDN — offline support)
- `src/components/ChartWebView.tsx` — React Native component wrapping the WebView

**Message protocol (RN → WebView):**

| Message Type | Payload | Purpose |
|---|---|---|
| `LOAD_SESSION` | `{ candles: CandleData[], decisionPoints: DecisionPoint[] }` | Load full session data |
| `PLAY` | `{ speed: number }` | Begin/resume playback |
| `PAUSE` | — | Pause at current candle |
| `SEEK` | `{ candleIndex: number }` | Jump to specific candle (for review mode) |
| `SET_TRADE_LEVELS` | `{ sl: number, tp: number, direction: 'buy'|'sell' }` | Draw SL/TP lines on chart |
| `CLEAR_DRAWINGS` | — | Remove all user drawings |
| `SET_TIMEFRAME` | `{ timeframe: '1M'|'5M'|'15M'|'1H' }` | Switch timeframe view |
| `ADD_DRAWING` | `{ type: 'hline'|'trendline'|'fibonacci', params: {...} }` | Add user charting tool |

**Message protocol (WebView → RN):**

| Message Type | Payload | Purpose |
|---|---|---|
| `PAUSE_AT_DECISION` | `{ candleIndex: number }` | Chart has reached a decision point |
| `OUTCOME_REACHED` | `{ candleIndex: number, outcomeType: 'tp'|'sl'|'neutral' }` | Outcome resolved |
| `PLAYBACK_COMPLETE` | — | All candles played, no more decision points |
| `DRAWING_ADDED` | `{ drawingId: string, type: string }` | User drew something (for tracking) |

**Data flow for a session:**
1. Session starts → RN loads candles from SQLite for the dataset
2. RN loads decision_points for the dataset (SQLite cache or Supabase)
3. RN sends `LOAD_SESSION` to WebView
4. WebView renders chart, begins playback on `PLAY`
5. At `trigger_candle_index` → WebView sends `PAUSE_AT_DECISION`
6. RN enters PAUSED state → decision UI shown
7. User commits → RN sends `SET_TRADE_LEVELS`, then `PLAY`
8. At `outcome_candle_index` → WebView sends `OUTCOME_REACHED`
9. RN calls Edge Function `resolve_trade` → server computes points + capital
10. RN enters OUTCOME state → displays result

---

## 5. Offline Architecture

**Sessions are fully offline.** All data required for a session is in SQLite.

### SQLite Database (expo-sqlite)

Tables mirrored locally:
- `local_datasets` — dataset metadata
- `local_candles` — all OHLCV data for downloaded datasets
- `local_decision_points` — decision point metadata
- `local_arcade_challenges` — Arcade challenge pool (subset)
- `pending_trade_resolutions` — queue of trade outcomes awaiting server sync
- `pending_points_updates` — TradePoints changes awaiting sync

**Download strategy:**
- On first install: 5 bundled datasets (in app binary, ~8MB each)
- On first auth: remaining datasets downloaded in background (~15 more)
- New datasets: checked on each app launch, downloaded in background
- Storage budget: aim for <200MB total dataset storage

**Sync on reconnect:**
- App detects network restoration
- Processes `pending_trade_resolutions` queue via Edge Function
- Server resolves each trade authoritatively, returns updated points/capital
- Client updates Zustand state from server response
- Conflicts: server wins

---

## 6. Edge Functions

All business logic runs server-side. These are the key Edge Functions:

| Function | Trigger | Logic |
|---|---|---|
| `resolve_trade` | Client POST on trade commitment | Validates trade inputs, determines outcome vs decision_point, computes points/capital delta, writes trade row, updates career_life, checks milestones and badges |
| `resolve_arcade_answer` | Client POST on answer submission | Validates answer, computes points, checks speed bonus, updates arcade_session |
| `initiate_transfer` | Client POST | Validates cap, creates fund_transfer row, returns transfer ID and completes_at |
| `process_transfers` | Scheduled (every 15 min) | Finds pending transfers where completes_at <= now(), applies funds, marks complete |
| `weekly_growth_bonus` | Scheduled (Monday 00:01 UTC) | Computes career_life capital growth vs 7 days ago, awards TradePoints |
| `check_milestones` | Called by resolve_trade | Checks Practice Capital milestones, awards badges and perks |
| `check_leverage_unlock` | Called after TradePoints update | Awards leverage tier if threshold crossed |
| `revenuecat_webhook` | POST from RevenueCat | Updates subscriptions table and purchased_items on IAP events |
| `refresh_leaderboards` | Scheduled (every 60 min) | Refreshes materialised leaderboard views |

---

## 7. Authentication and Cross-App Identity

**Sign in with Apple / Sign in with Google** are both required at onboarding. Email/password login is not offered (simplifies account recovery, ensures Apple/Google ID link exists for cross-app ecosystem).

**Supabase Auth configuration:**
- Provider: Apple + Google
- JWT issued by Supabase, stored in `expo-secure-store` (encrypted)
- Same JWT works across TradeWise, PropWise, CompWise (same Supabase project)
- `users.id` (Supabase UUID) is the shared identity across all three apps

**Cross-app login flow:**
1. User opens PropWise app for the first time
2. "Sign in with Apple/Google" — same credential used for TradeWise
3. Supabase Auth recognises the credential, returns same `users.id`
4. PropWise queries shared Supabase tables using this ID
5. User sees their PropFunds balance immediately (if any transferred from TradeWise)

---

## 8. Security

**Economy integrity:**
- TradePoints and Practice Capital are never sent from client to server as values. Client sends decisions (direction, lot, SL, TP). Server computes outcomes.
- Monthly transfer cap enforced by database trigger (`enforce_monthly_transfer_cap`) before insert — not just application layer.
- 48-hour transfer delay processed by scheduled function — cannot be bypassed by client.

**RLS:**
- All tables have RLS. Users can only read/write their own rows.
- Leaderboard data exposed via materialised view with only public fields.
- `decision_points.correct_direction` is readable by clients (educational app, not cheat-sensitive). If this changes in competitive phases, move to server-only resolution.

**IAP validation:**
- All IAP receipts validated by RevenueCat before entitlements are granted.
- `purchased_items` is written only by the RevenueCat webhook (service role) — never by the client.

---

## 9. Third-Party Services

| Service | Purpose | Configuration |
|---|---|---|
| RevenueCat | IAP + subscription management | One project, two platforms (iOS + Android). Webhook → Supabase `revenuecat_webhook` Edge Function. |
| PostHog | Product analytics | Self-hosted or PostHog Cloud. Key events: session_started, trade_committed, trade_resolved, badge_earned, tier_unlocked, transfer_initiated, iap_purchased. |
| Sentry | Error and crash tracking | React Native SDK. Session replay optional (check privacy implications). |
| Expo EAS | Build and OTA updates | One EAS project, three build profiles: development, preview, production. |

---

## 10. Build and Environment Configuration

**Environments:** development, staging, production (separate Supabase projects for dev/staging).

**EAS Secrets (never in repo):**

```
SUPABASE_URL
SUPABASE_ANON_KEY
REVENUECAT_IOS_KEY
REVENUECAT_ANDROID_KEY
POSTHOG_API_KEY
SENTRY_DSN
```

**Expo app.config.js** reads these via `process.env`. Never hardcoded.

---

## 11. PropWise and CompWise App Architecture (Future)

When built, PropWise and CompWise will:
- Use the same Supabase project (shared auth and fund tables)
- Be separate React Native (Expo) apps with separate App Store listings
- Have their own app-specific tables (mortgages, full portfolio, staff, supply chain)
- Share no client code with TradeWise (separate repos)
- Read `minigame_propwise` and `minigame_compwise` tables to show transferred progress

The design decision to share a Supabase project (rather than separate projects with API bridges) is deliberate. It eliminates cross-service authentication complexity and makes the fund transfer feature trivially simple — it is a database row update, not an API call between services.
