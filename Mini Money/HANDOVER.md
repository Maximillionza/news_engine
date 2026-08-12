# MiniMoney — Handover

Last updated: 2026-07-23. Written for picking the build back up cold (future me / future Claude session), not for external onboarding.

Reference docs this doesn't duplicate: `PRD.md`, `BuildSpec.md`, `TraceabilityMatrix.md`, `BusinessCase_v24.md`, `Task Tier.md`, `design_handoff_mini_money_app/`.

---

## 1. What MiniMoney is

South African parent-child chore/allowance app. Parent sets a monthly Rand budget, assigns tasks to child profiles, tasks earn **Mbucks** (whole-integer virtual currency, truncated — never rounded), verified tasks roll into a **payslip**, parent pays the child manually via their own banking app and confirms in-app. MiniMoney never moves real money — it's a ledger and nudge layer, not a payment rail. Deliberately avoids anything that reads as gambling, credit, or debt mechanics (see the `childFacingTermLint` Gradle task and the terminology split between `strings_parent.xml` and `strings_child.xml`).

Current version: **v0.10.0** (`versionCode 10`). `IS_PILOT = true` is baked into `BuildConfig`.

---

## 2. Current architecture

**Stack:** Kotlin, MVVM + Hilt + Jetpack Compose (Material3), Room (local-first), Retrofit + OkHttp against Supabase Edge Functions, kotlinx.coroutines/StateFlow throughout, DataStore for settings.

**Package layout** (`app/src/main/java/com/minimoney/app/`):
```
data/        auth, child, consent, db, dispute, flags, payslip, settings, tasks   — Room DAOs/entities, Retrofit APIs, repo impls
domain/      auth, child, consent, core, dispute, flags, payslip, tasks           — models, repository interfaces, MbuckCalculator, Clock
di/          Hilt modules (Core, Network, Consent) + AuthInterceptor
presentation/  auth, child, consent, exambonus, home, linking, more, mpoints,
               payslips, profile, tasks                                          — one Route/Screen/ViewModel per feature
ui/theme/    Theme.kt (design tokens), shape system
work/        WorkManager (on-demand init via Configuration.Provider, default
             androidx.startup disabled)
```

**Navigation:** `ParentNavGraph.kt` — single NavHost, session-driven root in `AppViewModel` picks LOADING / AUTH / CONSENT / HOME as a pure function of session state + POPIA consent completion. No persistent bottom nav (see §4).

**Local database:** Room, currently at **schema version 4** (`MiniMoneyDatabase.kt`), explicit migrations 1→2→3→4 in `Migrations.kt` — `fallbackToDestructiveMigration()` was deliberately removed before this counted as "production." Schema history exported to `app/schemas/`. Key tables: parents, children (with `AgeBand`: 6-9 / 10-14 / 15-18), tasks (now carries `frequency`), ledger entries, payslips, disputes, access log.

**Auth:** Google Sign-In via Credential Manager (`GoogleSignInLauncher.kt`) → ID token → `auth-google` Edge Function verifies it server-side against `MINIMONEY_GOOGLE_CLIENT_IDS` → session issued → `AuthInterceptor` attaches the bearer token to every subsequent request. Phone+OTP was fully removed (`PhoneNumberValidator` and its tests deleted) — Google Sign-In is the only auth path now.

**Backend — Supabase** (project ref `iftunypqqptuzoscuiub`, `API_BASE_URL = https://iftunypqqptuzoscuiub.supabase.co/functions/v1/`, `GOOGLE_WEB_CLIENT_ID = 148178496329-keig9g4apiorhsng4firv1ps84436jn8.apps.googleusercontent.com`), source in `supabase/`:
- `auth-google` — verifies Google ID token, creates/reuses `parent_accounts` row, issues session
- `consent-current` — returns the current POPIA document (public, versioned)
- `consent-accept` — marks a parent's consent complete for a document version (409 on stale version)
- `link-child` — registers a child's Google account email against the parent (409 on duplicate email or 4-child limit)
- `access-check` — child-device entry point: given an email + ID token, says whether that email has an active link to any parent (**endpoint exists, no app-side UI consumes it yet** — see §4)

Postgres: `parent_accounts`, `child_links`, deny-by-default RLS.

**Mbuck calculation** (`MbuckCalculator.kt`, `domain/core`): three earn modes —
- `FIXED` — flat Mbucks/month, divided across occurrences
- `PERCENTAGE` — % of budget/month, divided across occurrences
- `TIER` — preset tasks (`TaskTemplates.kt`, 20+ entries by age band) draw a fixed share of the budget per frequency pool (Daily 40% / Weekly 35% / Monthly 25%) split by each task's `relativeWeight` within that pool

All three converge on a single final truncation (never round, never truncate at an intermediate step) with a 0→1 floor so no task ever pays literally nothing. `Frequency.occurrencesPerMonth` is a `Double` (30.0 / 4.3 / 1.0) specifically so Weekly's fractional division works.

**Theme:** `Theme.kt` — dark-first (`#0C1220` bg / `#161D30` surface / `#6C8DFF` accent), full light-mode token set too, toggle persisted in its own DataStore (`ThemeStore`, separate from session so sign-out doesn't reset it), per-child gradient card assignment, shape system (`PillShape`, `HeroCardShape`, `CardShape`, `RowShape`, `TileShape`).

**Feature flags** (`domain/flags/FeatureFlags`, own DataStore, survives sign-out): `ACCOUNT_LINKING_ENABLED`, `MPOINTS_ENABLED` — both OFF at launch, gate the Rewards tab tiles (rendered dimmed with a "Coming soon" badge, not hidden).

**Testing:** 16 test files (JUnit + MockK + coroutines-test), covering MbuckCalculator (incl. tiered and 4.3-weekly-division cases), TaskRepositoryImpl, TasksViewModel, HomeViewModel, AuthViewModel, AppViewModel. No instrumented/UI tests, no Room migration tests.

**Build hygiene:** `childFacingTermLint` custom Gradle task scans parent-facing strings for debt-coded terminology, wired as a `preBuild` dependency — runs on every local build, not enforced anywhere else (no CI to also run it).

---

## 3. What's been verified end-to-end on-device

- Google Sign-In: account picker → token verification → session issuance → consent gate → Home, full round trip against the live Supabase backend
- Account reset flow (local `pm clear` + server-side Supabase truncate) → clean first-time-user state
- Task Tier preset flow, dark/light theme toggle, Family/single-child Home views, Profile, More tabs

The Android OAuth client (package `com.minimoney.app`, debug SHA-1 `B3:EF:0B:DC:6F:DC:C9:D9:EF:84:16:35:0A:E8:06:04:B2:15:AA:10`) is registered in Google Cloud Console alongside the pre-existing Web client — this was the one-time missing piece that caused "Sign-in was cancelled" errors; don't need to touch it again unless the debug keystore or package ID changes.

---

## 4. Known gaps (scoped, not yet built)

1. **Child-device access screen** — `access-check` endpoint is live and correct, but no screen calls it. A child opening the app on their own device has nothing gating/routing them based on link status yet.
2. **Dedicated Verify queue** — Home's "Verify" pills currently route into the Tasks screen, where verification actually happens inline. The design handoff calls for a separate Verify surface, not built.
3. **Persistent bottom nav** — every screen is reachable via buttons, but there's no 4-item Home/Tasks/Payslip/More bar. Building it needs a cross-screen "selected child" concept that today lives only inside `HomeViewModel`.

## 5. Recommended, not yet started

Flagged during this handover pass — none blocking, but worth deciding on before this goes past pilot:

1. **No CI.** Tests and the terminology lint only run when someone builds locally. A GitHub Actions job running `./gradlew test childFacingTermLint` on push would catch regressions before they're noticed by hand.
2. **No crash/ANR reporting.** Nothing like Crashlytics or Sentry is wired in — once this is on a device you don't control, field failures are invisible.
3. **Play Store readiness is unscoped.** This is a children's financial-literacy app; Google's Families Policy and Data Safety declaration have specific requirements that likely constrain how Mbucks/rewards can be framed in listing copy. Worth a dedicated review pass before any submission, not something to discover at review time.
4. **Room migrations aren't tested.** Four migrations exist (1→2→3→4) with schema exports, but nothing exercises them via `MigrationTestHelper`. A bad migration currently would only surface on a real user's upgrade.
5. **No rate-limiting on the Edge Functions.** `link-child` and `access-check` are reachable without heavy auth friction and have no throttling — worth a Supabase-level rate limit before broader testing, given they touch POPIA-relevant data (email + child linkage).

---

## 6. Immediate next step, if resuming

Pick one of §4's three gaps or one of §5's five recommendations — none has been started. No pending uncommitted work as of this handover; `git log` head is `bd904a4` (v0.10.0 UI redesign commit).
