# DATA_SCHEMA.md — TradeWise Database Schema

**Version:** 0.2  
**Owner:** Masood  
**Database:** Supabase (PostgreSQL) — shared across TradeWise, PropWise, CompWise  
**ORM:** Supabase JS client

---

## Design Principles

- All timestamps: UTC. Displayed in user's local timezone client-side.
- Soft delete: `deleted_at` column. No physical deletes except account deletion (anonymise, don't delete).
- All monetary values: stored as integers (USD cents). $500 = 50000. Avoids float errors.
- TradePoints: integers only. No fractional points displayed.
- Cross-app identity: `users.id` is the shared key across all three apps (same Supabase project).

---

## Entity Map

```
users (Supabase Auth)
 ├── user_profiles (1:1) — TradeWise-specific profile
 ├── career_lives (1:many) — each Career Mode run is a "life"
 │    ├── career_sessions (1:many)
 │    │    └── trades (1:many)
 │    ├── career_perks (1:many)
 │    └── fund_transfers (1:many)
 ├── arcade_sessions (1:many)
 │    └── arcade_answers (1:many)
 ├── user_badges (1:many)
 ├── user_quests (1:many)
 ├── minigame_propwise (1:1)
 │    └── propwise_properties (1:many)
 ├── minigame_compwise (1:1)
 │    └── compwise_ventures (1:many)
 └── subscriptions (1:1)

datasets
 └── dataset_candles (1:many)
      └── decision_points (1:many)

arcade_challenge_pool (static content table)

competitions (Post-MVP)
 └── competition_entries (1:many)
```

---

## Tables

---

### `users`
Managed by Supabase Auth. Shared across TradeWise, PropWise, CompWise.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | Supabase Auth user ID. Shared across ecosystem. |
| email | text unique | |
| created_at | timestamptz | |
| last_sign_in_at | timestamptz | |

---

### `user_profiles`
TradeWise-specific. One row per user.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | FK → users.id | |
| username | text | unique, not null | 3–20 chars |
| avatar_id | smallint | not null, default 1 | 1–12 free; higher = purchased |
| avatar_frame_id | smallint | null | null = no frame (purchased cosmetic) |
| chart_theme_id | smallint | not null, default 1 | purchased cosmetic |
| country_code | char(2) | not null | ISO 3166-1 alpha-2 |
| experience_level | text | not null | enum: 'beginner','amateur','professional' |
| trade_points | integer | not null, default 1000 | floor: 100 |
| current_career_life_id | uuid | FK → career_lives.id, null | null = no active career |
| learning_module_completed | boolean | not null, default false | |
| learning_module_completed_at | timestamptz | | |
| learning_badge_tier | text | | null, or 'bronze','silver','gold' |
| risk_module_completed | boolean | not null, default false | |
| onboarding_complete | boolean | not null, default false | |
| disclaimer_accepted_at | timestamptz | | |
| career_readiness_score | smallint | | 0–100, computed async |
| readiness_score_updated_at | timestamptz | | |
| subscription_tier | text | not null, default 'free' | enum: 'free','pro' |
| propwise_unlocked | boolean | not null, default false | |
| compwise_unlocked | boolean | not null, default false | |
| total_career_lives | smallint | not null, default 0 | increments on each new career life |
| created_at | timestamptz | default now() | |
| updated_at | timestamptz | default now() | |

**Indexes:** `username` (unique), `trade_points` (leaderboard)

---

### `career_lives`
Each Career Mode run. A user gets a maximum of 2 lives per career (original + soft restart). On Career Mode Death, a new career begins (new row with life_number reset).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | | |
| user_id | uuid | FK → users.id, not null | |
| career_number | smallint | not null, default 1 | increments on each full restart |
| life_number | smallint | not null, default 1 | 1 = original, 2 = soft restart |
| is_soft_restart | boolean | not null, default false | true if this is life 2 of a career |
| status | text | not null, default 'active' | enum: 'active','soft_restarted','dead' |
| starting_capital_cents | bigint | not null | 50000 ($500) base, or higher if transfer used |
| current_capital_cents | bigint | not null | updated on each trade resolve |
| peak_capital_cents | bigint | not null, default 0 | highest value reached |
| leverage_tier | smallint | not null, default 1 | 1–6, corresponds to PRD FR-010 |
| sessions_completed | integer | not null, default 0 | |
| total_trades | integer | not null, default 0 | |
| total_wins | integer | not null, default 0 | |
| total_losses | integer | not null, default 0 | |
| total_neutral | integer | not null, default 0 | |
| total_correct_no_trades | integer | not null, default 0 | |
| current_win_streak | integer | not null, default 0 | |
| longest_win_streak | integer | not null, default 0 | |
| stage | smallint | not null, default 1 | 1–4, derived from sessions_completed |
| loan_outstanding_cents | bigint | not null, default 0 | 25000 ($250) if soft restart |
| started_at | timestamptz | not null, default now() | |
| ended_at | timestamptz | | null until dead or soft restarted |

---

### `career_sessions`
One row per Career Mode session.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | | |
| career_life_id | uuid | FK → career_lives.id, not null | |
| user_id | uuid | FK → users.id, not null | denormalised |
| dataset_id | uuid | FK → datasets.id, not null | |
| status | text | not null, default 'active' | enum: 'active','complete','abandoned' |
| started_at | timestamptz | not null | |
| completed_at | timestamptz | | |
| trades_total | smallint | | set on session create |
| trades_completed | smallint | not null, default 0 | |
| points_earned_net | integer | not null, default 0 | signed |
| capital_change_cents | bigint | not null, default 0 | signed |
| win_count | smallint | not null, default 0 | |
| loss_count | smallint | not null, default 0 | |
| neutral_count | smallint | not null, default 0 | |
| correct_no_trade_count | smallint | not null, default 0 | |
| weekly_growth_bonus_awarded | integer | not null, default 0 | TradePoints from weekly growth (if any) |
| streak_at_start | integer | not null | |
| streak_at_end | integer | | |
| is_hard_mode | boolean | not null, default false | Stage 4 streak cooldown |

---

### `trades`
One row per decision point within a Career Mode session.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | | |
| session_id | uuid | FK → career_sessions.id, not null | |
| user_id | uuid | FK → users.id, not null | denormalised |
| career_life_id | uuid | FK → career_lives.id, not null | denormalised |
| decision_point_id | uuid | FK → decision_points.id, not null | |
| sequence_number | smallint | not null | 1-indexed within session |
| user_direction | text | | enum: 'buy','sell','no_trade' |
| lot_size | numeric(5,2) | | null if no_trade |
| sl_pips | smallint | | |
| tp_pips | smallint | | |
| sl_preset | text | | enum: 'tight','moderate','wide','custom' |
| tp_preset | text | | same enum |
| risk_percent | numeric(5,2) | | computed on commit |
| risk_amount_cents | bigint | | computed on commit |
| outcome | text | | null until resolved. enum: 'win','loss','neutral','correct_no_trade','incorrect_no_trade' |
| points_change | integer | | signed |
| capital_change_cents | bigint | | signed |
| correct_direction | text | not null | copied from decision_point |
| setup_type | text | | copied from decision_point |
| is_trap_setup | boolean | not null | copied from decision_point |
| streak_at_decision | integer | not null | |
| committed_at | timestamptz | | |
| resolved_at | timestamptz | | |
| capital_before_cents | bigint | not null | Practice Capital at moment of trade decision |
| capital_after_cents | bigint | | set on resolution |

---

### `arcade_sessions`
One row per Arcade Mode session.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | | |
| user_id | uuid | FK → users.id, not null | |
| difficulty | text | not null | enum: 'easy','medium','hard' |
| status | text | not null, default 'active' | enum: 'active','complete','abandoned' |
| started_at | timestamptz | not null | |
| completed_at | timestamptz | | |
| challenges_total | smallint | not null, default 10 | |
| challenges_completed | smallint | not null, default 0 | |
| correct_count | smallint | not null, default 0 | |
| incorrect_count | smallint | not null, default 0 | |
| points_earned_net | integer | not null, default 0 | |
| best_streak | smallint | not null, default 0 | in-session streak |

---

### `arcade_answers`
One row per challenge answered in an Arcade session.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | | |
| session_id | uuid | FK → arcade_sessions.id, not null | |
| user_id | uuid | FK → users.id, not null | denormalised |
| challenge_id | uuid | FK → arcade_challenge_pool.id, not null | |
| challenge_type | text | not null | enum: 'setup_id','candlestick','reversal_pullback','bollinger','structure','support_resistance','next_move' |
| user_answer | text | not null | |
| correct_answer | text | not null | |
| is_correct | boolean | not null | |
| response_time_ms | integer | | milliseconds to answer |
| speed_bonus_awarded | boolean | not null, default false | |
| points_change | integer | not null | |
| answered_at | timestamptz | not null | |

---

### `arcade_challenge_pool`
Static content table. Pre-populated by content team. Not user-writable.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | | |
| challenge_type | text | not null | enum: (7 types) |
| difficulty | text | not null | enum: 'easy','medium','hard' |
| question_text | text | not null | |
| correct_answer | text | not null | |
| wrong_answers | jsonb | not null | array of 1–3 wrong options |
| explanation | text | not null | shown after answer |
| dataset_id | uuid | FK → datasets.id, null | if chart-based challenge |
| candle_range_start | integer | | candle index range to display |
| candle_range_end | integer | | |
| highlight_candle_index | integer | | candle to highlight for pattern questions |
| active | boolean | not null, default true | |
| created_at | timestamptz | | |

---

### `datasets`
Curated historical OHLCV collections.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid PK | | |
| name | text | not null | e.g. "EURUSD_5M_TREND_UP_001" |
| instrument | text | not null | enum: 'EURUSD' (MVP, expands post-MVP) |
| timeframe | text | not null | enum: '5M' (MVP) |
| market_condition | text | not null | enum: 'trending_up','trending_down','ranging','compression','high_vol' |
| decision_point_count | smallint | not null | |
| stage_min | smallint | not null, default 1 | |
| stage_max | smallint | not null, default 4 | |
| is_trap_session | boolean | not null, default false | |
| active | boolean | not null, default true | |
| created_at | timestamptz | | |

---

### `dataset_candles`
Raw OHLCV data. Pre-loaded.

| Column | Type | Notes |
|---|---|---|
| id | bigserial PK | |
| dataset_id | uuid FK | |
| candle_index | integer | 0-indexed |
| open | numeric(10,5) | |
| high | numeric(10,5) | |
| low | numeric(10,5) | |
| close | numeric(10,5) | |
| volume | bigint | |

**Index:** `(dataset_id, candle_index)`

---

### `decision_points`
Pre-tagged trade opportunities. Content team populates.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| dataset_id | uuid FK | |
| trigger_candle_index | integer | chart pauses here |
| correct_direction | text | enum: 'buy','sell','no_trade' |
| is_trap_setup | boolean | |
| setup_type | text | e.g. 'key_level_candlestick', 'compression_breakout' |
| setup_components | jsonb | array of component names |
| outcome_candle_index | integer | where outcome resolves |
| sl_tight_pips | smallint | |
| sl_moderate_pips | smallint | |
| sl_wide_pips | smallint | |
| tp_tight_pips | smallint | |
| tp_moderate_pips | smallint | |
| tp_wide_pips | smallint | |
| max_favourable_pips | smallint | for Pro bonus calculation |
| stage_label | text | 'foundation','recognition','mastery','independence' |
| coaching_text_win | text | Stage 1 post-win card |
| coaching_text_loss | text | Stage 1 post-loss card |
| coaching_text_no_trade_correct | text | |
| coaching_text_no_trade_incorrect | text | |

---

### `user_badges`

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK | |
| badge_type | text | enum: (full list in GAME_DESIGN.md) |
| star_level | smallint | 1–3 where applicable |
| earned_at | timestamptz | |
| source_trade_id | uuid FK nullable | trade that triggered (if applicable) |
| source_session_id | uuid FK nullable | |
| career_life_id | uuid FK nullable | which career life it was earned in |

**Unique:** `(user_id, badge_type)` — one row per badge, star_level updates.  
Badges are never deleted, even across Career Mode deaths.

---

### `user_quests`

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK | |
| quest_template_id | text | references quest definition (static config) |
| status | text | enum: 'active','completed','expired' |
| progress_value | integer | current progress toward target |
| target_value | integer | from quest template |
| started_at | timestamptz | |
| completed_at | timestamptz | |
| reward_claimed | boolean | default false |

---

### `fund_transfers`
Mini-game → Career Mode transfer log.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK | |
| source | text | enum: 'propwise','compwise' |
| destination | text | enum: 'career_mode' |
| amount_cents | bigint | |
| transfer_type | text | enum: 'normal','death_restart' |
| career_life_id | uuid FK | destination career life |
| status | text | enum: 'pending','complete','failed' |
| initiated_at | timestamptz | |
| completes_at | timestamptz | initiated_at + 48 hours |
| completed_at | timestamptz | when actually processed |
| monthly_total_cents | bigint | running monthly total for cap enforcement |

**Monthly cap enforcement:** Application layer checks `fund_transfers` where `source = X` and `initiated_at >= first of current month` and `status IN ('pending','complete')` and `transfer_type = 'normal'`. Sum must not exceed 5,000,000 cents ($50,000) per source per user per month.

---

### `minigame_propwise`
One row per user (created on PropWise unlock).

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK unique | |
| prop_funds_cents | bigint | not null, default 0 |
| total_properties_owned | smallint | not null, default 0 |
| lifetime_returns_cents | bigint | not null, default 0 |
| last_return_processed_at | timestamptz | |
| cross_app_transferred | boolean | not null, default false | true if transferred to PropWise app |
| created_at | timestamptz | |

---

### `propwise_properties`
Properties owned in PropWise mini-game.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| minigame_id | uuid FK | |
| user_id | uuid FK | denormalised |
| property_type | text | enum: 'residential','commercial','industrial' |
| property_name | text | |
| purchase_price_cents | bigint | |
| current_value_cents | bigint | |
| monthly_return_rate | numeric(5,4) | e.g. 0.0080 = 0.80%/month |
| purchased_at | timestamptz | |
| status | text | enum: 'active','sold' |
| sold_at | timestamptz | |
| sale_price_cents | bigint | |

---

### `minigame_compwise` and `compwise_ventures`
Mirror structure of PropWise tables with BizFunds and venture types.

---

### `subscriptions`
Mirrored from RevenueCat webhooks.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK unique | |
| revenuecat_user_id | text unique | |
| tier | text | enum: 'free','pro' |
| status | text | enum: 'active','cancelled','expired','trial' |
| current_period_end | timestamptz | |
| entitlements | jsonb | array of active entitlement IDs |
| updated_at | timestamptz | |

---

### `purchased_items`
One-time IAP purchases. Checked for entitlement.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK | |
| product_id | text | RevenueCat product ID |
| entitlement | text | entitlement granted |
| purchased_at | timestamptz | |
| revenuecat_transaction_id | text unique | |

---

## Database Functions and Triggers

| Function | Trigger | Purpose |
|---|---|---|
| `resolve_trade` | Called by Edge Function | Updates trade outcome, career_life capital, user TradePoints, streak |
| `enforce_points_floor` | BEFORE UPDATE on user_profiles.trade_points | Prevents < 100 |
| `enforce_monthly_transfer_cap` | BEFORE INSERT on fund_transfers | Blocks if monthly cap exceeded |
| `process_pending_transfers` | Scheduled: every 15 minutes | Processes transfers where completes_at <= now() |
| `compute_weekly_growth_bonus` | Scheduled: Monday 00:01 UTC | Computes % growth vs 7 days prior, awards bonus TradePoints |
| `compute_readiness_score` | After career_sessions status → 'complete' | Recomputes career_readiness_score |
| `refresh_career_leaderboard` | Scheduled: every 60 minutes | Materialised view refresh |
| `check_leverage_tier_unlock` | After UPDATE on user_profiles.trade_points | Awards new tier if threshold crossed, triggers notification |
| `check_capital_milestone` | After UPDATE on career_lives.current_capital_cents | Checks milestone thresholds, awards badges |
| `trigger_blown_state` | After UPDATE on career_lives.current_capital_cents | If < 1000 cents ($10): sets status flags, triggers client notification |

---

## Row Level Security

All tables have RLS enabled.

| Table | Policy |
|---|---|
| user_profiles | Read own row. Leaderboard view exposes username, avatar, badges, capital — anonymised query via materialised view. |
| career_lives | Read/write own rows only. |
| career_sessions | Read/write own rows only. |
| trades | Read/write own rows only. |
| arcade_sessions | Read/write own rows only. |
| arcade_answers | Read/write own rows only. |
| user_badges | Read own. Write via server-side functions only. |
| fund_transfers | Read own. Insert via server-side function only (cap enforcement). |
| minigame_* | Read/write own rows only. |
| datasets | Read: all authenticated. Write: none (admin only). |
| dataset_candles | Read: all authenticated. Write: none. |
| decision_points | Read: all authenticated. Write: none. |
| arcade_challenge_pool | Read: all authenticated. Write: none. |
| subscriptions | Read own. Write: service role only (RevenueCat webhook). |
