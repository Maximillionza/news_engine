# Handoff: Mini Money — Android App UI

## Overview
Mini Money is an Android app (Kotlin, Jetpack Compose, MVVM, Hilt, Room per the project's Build Spec) where a parent runs a "payroll simulation" for their child: the parent sets a budget, assigns tasks, the child earns Mbucks (a non-transferable, real-money-pegged unit — 1 Mbuck = R1), and the parent pays the child directly through their own banking app outside the product. This package covers the core loop UI: onboarding, parent home (multi-child), child home, tasks, payslip, verification queue, profile, and the "More" menu.

## About the Design Files
The bundled file (`mini_money_app_design.html`) is a **design reference built in HTML** (a "Design Component" prototype in our design tool) — it is a clickable mockup showing intended look, layout, and behavior. **It is not production code and should not be copied or embedded directly into the Android app.** The task is to recreate this UI natively in **Jetpack Compose**, using the project's established architecture (MVVM + Hilt + Room, per `BuildSpec.md`), not to port the HTML/JS.

## Fidelity
**High-fidelity.** Colors, spacing, typography, corner radii, and copy in the HTML file are final intent, not placeholders. Recreate pixel-close in Compose. Where a value isn't explicit below, inspect the inline styles in the HTML file directly (all styling is inline, no external stylesheet).

## Visual Direction
Dark-first UI (matches the founder's reference screenshots of an existing trading app's *layout patterns* — card-based, pill buttons, gradient hero cards, bottom nav — reinterpreted with Mini Money's own colors/content). A light theme is also implemented and toggled from Profile > Dark mode; both palettes are listed in Design Tokens below.

## Screens / Views

### 1. Splash
- **Purpose:** First-run brand moment + entry point to register or log in.
- **Layout:** Full-bleed dark background with two soft radial-gradient glows (top-left, bottom-right) behind a centered logo. Column, centered content, `justify-content:center` for the top ~70% of the screen; bottom ~30% is a fixed-bottom button stack with 28px horizontal padding.
- **Components:**
  - Logo mark: 96×96 circle, `accentGradient` fill, white "M" glyph (40px, weight 800), a 2px inset ring at 50% white opacity. Animates in with a pop+rotate keyframe (0.9s, cubic-bezier(.2,.9,.3,1.2)).
  - Wordmark "Mini Money" (24px/800) + tagline "Chores in. Mbucks out." (13px, muted), fades up 0.3s after logo.
  - 3 small floating dots (6–8px circles, low-opacity) drift via a slow float keyframe (~4–5s loop) — purely decorative background motion.
  - Primary pill button "Get started" → navigates to Register.
  - Text-only "Log in" link below it → navigates to Login.

### 2. Login
- **Purpose:** Returning-parent entry (phone number only in this mock; real app should follow the same OTP mechanism as Register).
- **Layout:** Back button top-left, then title/subtitle, one input, spacer, primary pill button pinned above safe area.
- **Components:** "Welcome back" (26px/800), subtext, "Mobile number" labeled input, "Continue" pill button (disabled until phone is non-empty).

### 3. Register → OTP → Consent → Child Setup → Budget (onboarding stack)
Shared shell: back button + a 5-segment progress bar (4px tall, rounded, filled steps use `accentSolid`, unfilled use `divider`) at the top; each step below is full-height column with a spacer pushing the primary button to the bottom.

- **Register:** phone input; "Send code" button shows an inline spinner while `registerLoading`, then advances to OTP after ~800ms (simulated network delay).
- **OTP:** 6-digit numeric input, large centered mono-spaced-feel text (26px, 0.5em letter-spacing), "Resend code" link, "Verify" button → spinner (~800ms) → checkmark pop animation (~350ms) → auto-advances to Consent after 500ms.
- **Consent:** POPIA-aligned consent copy in a scrollable rounded panel (`surface2` background), a checkbox ("I have read and accept the terms above"), "Agree and continue" disabled until checked. **This must remain a structurally separate screen from registration** — not a checkbox embedded in the signup form (compliance requirement, see `BuildSpec.md` §Compliance).
- **Child Setup:** first-name text input, then 3 selectable age-band rows (6–9 / 10–14 / 15–18), each row a rounded card that highlights (border + tinted fill) when selected. "Continue" disabled until a name is entered.
- **Budget:** currency-style input row (`R` prefix, "/ month" suffix) accepting **digits only** — no decimal point, no cents, enforced at the input layer (strip non-digits on every keystroke) per the Mbuck whole-Rand rule. "Finish setup" creates the child record and lands on Home.

### 4. Home — Family view (parent, default)
- **Purpose:** Parent's overview across all linked children (up to 4).
- **Layout:** Top bar (screen title "Home" left; bell, payslip-shortcut, and avatar-initial icon buttons right, all 36px circular). Below it, a horizontally-scrollable chip row: "Family" (selected by default) + one chip per child — tapping a child chip switches the same screen into that child's single-child view (see #5). Below the chips, a vertical stack of one card per child.
- **Per-child card:** 22px corner radius, full-width, padding 20px, background = that child's assigned gradient (see tokens), white text.
  - Row: 38px circular avatar (initial letter, translucent white fill) + child name (15px/800) + age (11px, 85% opacity) +, if there are pending verification items for that child, a pill badge top-right reading "{n} to verify" (dark translucent chip).
  - "Month to date" label (11px uppercase, 80% opacity) + big Mbuck total (32px/800).
  - Two pill buttons side by side: **Manage** (solid white bg, dark text — opens that child's Tasks screen) and **Verify** (translucent white outline — opens the Verify queue filtered to that child).

### 5. Home — Single-child view
- **Purpose:** What Mini Money shows for a specific child's month-to-date progress (this is the view referenced as "what the minor sees").
- **Layout:** Same top bar + chip row (now with that child's chip active). One large hero card (24px radius, child's gradient): "{name} · Month to date" label, huge Mbuck total (40px/800), "of R{budget} monthly budget" subtext, then two pill buttons — **My tasks** (solid white) and **Payslip** (translucent). Below the card: "This week's tasks" list — rounded 16px rows on `surface`, each showing task title + status (left) and `+{mbuck} Mb` in accent color (right).
- Note: on a real device, a minor does not have an independent login (per PRD) — this view is reached either via the parent tapping a child's chip, or via a shared/child-mode device session. Confirm the intended access model with the founder before implementing device-level access control.

### 6. Tasks
- **Purpose:** Parent creates/reviews tasks for the currently-selected child; view the child's assigned/verified tasks.
- **Layout:** Subtitle "Tasks for {name}", list of task rows (title + mode/status left, Mbuck value right, `surface` rounded-16 background). Below the list: either an open task-creation form or a dashed "+ New task" button.
- **Task creation form** (rounded-18 card on `surface`):
  - Text input: task name.
  - Segmented pill control (2 options, `surface2` track, active option filled `accentSolid`/white text): **Fixed** / **% of budget** — this is the two-mode earn-value selector from the Build Spec (per-task choice, not account-wide).
  - Numeric input for the value (placeholder swaps between "Mbucks e.g. 5" and "Percent e.g. 5" depending on mode).
  - Live preview line: "Earns **{computed} Mbucks** per completion" — computed with the exact Mbuck rule below.
  - Cancel (outline pill) / Add task (solid pill, disabled until title + value are present).

**Mbuck calculation rule (must match `BuildSpec.md` §Mbuck Precision & Truncation Rule exactly):**
```
FIXED mode:      mbuck = integer value entered by parent (min 1, enforced at input)
PERCENTAGE mode: raw = floor(childBudget * percentValue / 100)
                 mbuck = raw > 0 ? raw : 1   // truncate toward zero, then floor to 1 if the truncation yields 0
```
Mbuck is always a whole-number integer — no cents/sub-unit anywhere, ever. Truncate, never round, never carry the remainder forward.

### 7. Payslip
- **Purpose:** Shows the current period's total owed to the selected child and lets the parent confirm they've paid.
- **Layout:** "This period · {name}" kicker (accent-colored), big Rand total (34px/800), "{n} Mbucks earned" subtext, list of contributing task rows (title left, Mbuck value right), a disclosure line ("Pay {name} directly through your own banking app, then confirm below. Mini Money never moves money for you."), then either a solid pill "I've paid {name}" button, or — once tapped — a confirmation state: 52px circular checkmark badge (pop-in animation) + "Payment confirmed" label.
- This screen must never imply Mini Money moves money — the copy above is intentional and should be preserved.

### 8. Verify
- **Purpose:** The queue behind a child's "Verify" button on the Family view — houses **all three** verification types named by the founder: task completion, study/behavior-log completion, and payment confirmation.
- **Layout:** Back-button stack header ("Verify" title). Subtitle "Pending requests for {child}". One rounded-16 card per pending item on `surface`:
  - 34×34 rounded-10 icon tile (icon varies: checklist icon for task, open-book icon for study/behavior log, receipt icon for payment) + title + type label ("Task completion" / "Study / behavior log" / "Payment confirmation").
  - Two pill buttons: **Decline** (outline) / **Approve** (solid accent) — approving or declining removes the item from the list immediately (optimistic UI in the mock; real implementation should write to the ledger/dispute flow per Build Spec).
  - Empty state: centered muted text "Nothing pending — all caught up." when the queue is empty.

### 9. Profile ("My Profile")
- **Purpose:** Parent views/edits their account info and app-level settings.
- **Layout:** Back-button stack header. Avatar (56px circle, gradient fill, initial letter) + "Hey, {name}" (17px/800) + email (muted). A stats card (`surface`, rounded-18): two-column labels "Children linked" / "Paid out this month" over their values. Two side-by-side info tiles (`surface`, rounded-16): **Verification** (a green "Verified" pill badge) and **Notifications** ("Reminders on"). A plain list below with 1px bottom-dividers: **Dark mode** (row with a toggle switch on the right, animates the thumb 3px↔19px), **Support**, **Sign out** (styled in a red/warning tone, no divider under the last row).

### 10. More
- **Purpose:** Secondary features grouped by category, matching the founder's reference "More" screen pattern.
- **Layout:** Horizontally-scrollable pill tabs: **Family**, **Tools**, **Rewards** (active tab filled `accentSolid`/white text, inactive on `surface`). Below, a 3-column grid of rounded-18 tiles (`surface` background, 44×44 rounded-12 icon swatch + 11.5px/700 label, centered).
  - **Family tab:** Manage children, Add child (opens Child Setup to add another profile), Notifications.
  - **Tools tab:** Exam bonus (behavior checklist + grade input — gated per PRD until the child-development specialist's review), Disputes, Late penalty.
  - **Rewards tab:** Mpoint store, Account linking — both shown with a **"Coming soon"** badge (top-right corner chip) and reduced opacity (0.55), because both are real, built features shipped **feature-flagged off** by default (`MPOINTS_ENABLED`, `ACCOUNT_LINKING_ENABLED`) pending regulatory recheck — do not remove the flagged/disabled treatment without confirming the flags are on.

## Interactions & Behavior
- **Navigation model:** simple in-memory screen stack (`history` array in the mock) — back button pops one level. Bottom nav taps push a fresh screen rather than popping.
- **Bottom nav** (Home / Tasks / Payslip / More, 4 items): visible only on those 4 screens; icon + label recolor to accent when active, muted otherwise.
- **Loading states:** Register and OTP submit buttons swap their label for a spinning ring icon (CSS `rotate` keyframe, 0.8s linear infinite) during the simulated ~800ms network delay.
- **Success micro-interaction:** OTP verify and Payslip payment-confirm both use the same "pop in" checkmark (scale 0→1.25→1, ~350–400ms).
- **Background motion (Splash only):** 3 small dots drift up/down and slightly rotate on independent ~3.6–5.2s loops — decorative, non-blocking.
- **Disabled-state pattern:** every primary action button is disabled (and should visually dim, ~0.5 opacity) until its screen's required input is valid — phone non-empty, OTP = 6 digits, consent checked, child name entered, budget non-empty, new task has both a title and a value.
- **Dark mode toggle:** lives in Profile; flips every screen's color token set instantly (no separate light/dark screens — one token object swaps).

## State Management
Minimum state a Compose ViewModel needs to reproduce this flow:
- `screen` / nav stack (or Compose Navigation graph mirroring the screen list above)
- `parent`: name, email
- `children: List<Child>` — id, name, ageBand, monthlyBudget (Int, Rand, whole units only), monthToDateMbuck (Int)
- `selectedChildId: String?` — null = Family view; non-null = single-child Home/Tasks/Payslip scope
- `tasks: List<Task>` — id, childId, title, earnMode (FIXED | PERCENTAGE), earnValue, computedMbuck, status (assigned | completed | verified | disputed)
- `pendingVerifications: List<VerificationRequest>` — id, childId, type (task | study | payment), title
- `darkMode: Boolean`
- Transient per-screen UI state: OTP loading/verified flags, task-form-open + draft fields, payment-confirmed flag, active More-tab, active onboarding step

For the actual Mbuck ledger, task earn-rate math, truncation rule, dispute SLA, and late-penalty caps, **implement per `BuildSpec.md` and `PRD.md`** (provided separately in the project) — this handoff covers UI/UX only, not backend/data-layer rules beyond what's needed to preview values on screen.

## Design Tokens

### Dark theme (default)
| Token | Value |
|---|---|
| Background | `#0c1220` |
| Surface | `#161d30` |
| Surface 2 (inputs, tracks) | `#1e2740` |
| Text | `#f4f6fb` |
| Text muted | `rgba(244,246,251,0.58)` |
| Divider | `rgba(244,246,251,0.14)` |
| Accent (solid, buttons) | `#6c8dff` |
| Accent (text on surface) | `#93a9ff` |
| Accent gradient | `linear-gradient(135deg,#6c8dff,#a26cf0)` |
| Success soft / text | `rgba(51,209,122,0.16)` / `#33d17a` |

### Light theme
| Token | Value |
|---|---|
| Background | `#f4f5fa` |
| Surface | `#ffffff` |
| Surface 2 | `#eceef7` |
| Text | `#161b2e` |
| Text muted | `rgba(22,27,46,0.58)` |
| Divider | `rgba(22,27,46,0.12)` |
| Accent (solid) | `#4c6bef` |
| Accent (text) | `#3d55c9` |
| Accent gradient | `linear-gradient(135deg,#4c6bef,#8a4cef)` |
| Success soft / text | `rgba(24,163,94,0.14)` / `#189a5a` |

### Per-child hero-card gradients (decorative, one per child so cards are distinguishable)
- Child 1 (example "Alex"): `linear-gradient(135deg,#6a5cf0,#a24bd8 55%,#e94f9a)`
- Child 2 (example "Sam"): `linear-gradient(135deg,#2f8bf0,#4fd6c4)`
- New child (auto-assigned): `linear-gradient(135deg,#f0a24b,#e9574f 60%,#c94bd8)`
- Assign a new distinct gradient per additional child, or cycle through a defined palette of 4–6.

### Shape & spacing
- Buttons: fully pill (`border-radius: 100px`), 16px vertical padding for primary CTAs, 12px for secondary in-card actions.
- Cards: 16–24px corner radius depending on hierarchy (hero cards 22–24px, list rows 14–16px, small tiles 12–18px).
- Screen horizontal padding: 20–24px.
- Bottom nav: rounded top corners only (24px), sits flush to the bottom edge.

### Typography
- System font stack (`-apple-system, 'Segoe UI', Roboto, system-ui, sans-serif` in the mock — in Android use the app's standard Material type scale / Roboto).
- Weights used: 600 (body emphasis), 700 (labels/buttons), 800 (headings/numbers).
- Scale used in the mock: 10.5px (nav labels) · 11–12px (captions/kickers) · 13–15px (body) · 17–20px (section titles) · 24–26px (screen titles) · 32–40px (hero numbers).

## Assets
No external image or icon assets — all icons are hand-drawn inline SVGs (simple line-style, ~18–20px, 2px stroke, matching a Lucide-style icon set). No custom fonts loaded (system font stack). Recreate icons using your app's existing icon set/library (e.g. Material Symbols) rather than copying the inline SVG paths verbatim.

## Files
- `mini_money_app_design.html` — the full interactive design reference (all screens, states, and the exact inline styles/colors/copy described above). Open it in a browser to click through the flow. All styling is inline (no separate CSS file); all logic is in the single `<script>` block at the bottom of the file.
