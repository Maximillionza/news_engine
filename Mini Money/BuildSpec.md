# Build Specification: MiniMoney

> Prepared by: Developing Committee, from `BusinessCase_v24.md` (final),
> `Verdict_v7.md`, `PRD.md`, and `TraceabilityMatrix.md`. Compliance
> requirements below are translated into concrete technical constraints,
> not restated as legal language. Nothing here trims or softens an
> Investment Committee finding — only Incubator-originated scope bloat is
> trimmed, each with a stated reason (see §Trimmed Scope).

> **Correction log — 2026-07-13, pre-Milestone-1, founder-identified.**
> The Mbuck currency-precision design was under-specified: the original
> data model confirmed the 1 Mbuck = R1 peg but did not state (a) that
> Mbuck has no sub-unit/cents representation at all, (b) how fractional
> remainders from any percentage-based Mbuck calculation are handled, (c)
> that the budget-input screen must reject cents at the validation layer,
> not just formatting, and (d) how currency display behaves when
> account-linking is active versus inactive. All four are corrected below,
> at the point of change, per this document's own revision discipline (see
> `ExecutionInstructions.md`). No code had been written against the prior
> version at the time of this correction.

> **Correction log — 2026-07-14, pre-Milestone-1, Chief-of-Staff-traced.**
> The percentage-of-budget task earn-rate mechanic — referenced in the
> 2026-07-13 correction above but, at that time, absent from this
> document's permitted inputs and therefore left as a forward-only flag
> rather than a specified mechanic — has since been traced by the Chief
> of Staff and confirmed as real, established design: sourced from this
> case's own historical record (`BusinessCase_v5.md`, itself sourced from
> `Clarifications_v5.md`, the founder's own original design), present
> through early Business Case versions and silently dropped from later
> versions during the case's own review process — a defect in that
> historical record's maintenance, not evidence the feature was ever
> actually cut. The `Task` entity and the Mbuck Precision & Truncation
> Rule section below are updated accordingly to specify it as an in-scope
> MVP mechanic, including the original design's stated 1-Mbuck floor. No
> code had been written against the prior version at the time of this
> correction.

## Architecture Overview

Android-first native application.

- **Stack:** Kotlin, MVVM architecture, Hilt (dependency injection), Room
  (local persistence), Jetpack Compose (UI) — per standing Android/Kotlin
  architecture convention.
- **Critical build constraint:** never add `applicationIdSuffix` to debug
  build variants. (Standing platform-level constraint; applies to any
  Kotlin/Android build regardless of project.)
- **Backend:** minimal — MiniMoney does not move money, so no
  payment-processing backend is required. A lightweight backend/API layer
  is needed for: account sync across devices (parent + child on separate
  devices), push-notification triggering (reminders, escalations), and
  server-side enforcement of the non-transferability constraint on Mbucks
  (see §Data Model). Specific backend platform choice (e.g., Firebase vs.
  a custom lightweight server) is left to the founder's build-time
  tooling preference — this does not affect any compliance or product
  requirement above, so it is not treated as an open decision requiring
  resolution here.
- **Feature flags (config-level, not build-time):** `ACCOUNT_LINKING_ENABLED`
  and `MPOINTS_ENABLED`, both **OFF by default at launch**. Each may be
  turned on only after its respective regulatory recheck (SARB/NPS Act;
  FPB) resolves favorably. Owner: founder. See `ExecutionInstructions.md`
  for the milestone check.
- **Currency display layer (conditional on `ACCOUNT_LINKING_ENABLED`,
  correction 2026-07-13):** Mbuck is the app's internal unit of account
  everywhere — in the ledger and in the UI — by default, regardless of
  the flag's state. This is a display-layer behavior only, gated on two
  conditions both being true at render time: (1) `ACCOUNT_LINKING_ENABLED`
  is on, AND (2) the linked account has returned a confirmed real-payment
  event for the specific amount being displayed. Only when both hold may
  the UI render the local currency (ZAR, "R") instead of the Mbuck
  abstraction for that amount. If either condition is false — flag off,
  or flag on but payment not yet confirmed via the link — the UI shows
  Mbucks. **The underlying ledger entry is never re-denominated.**
  `MbuckLedgerEntry` rows remain Mbuck-typed permanently; ZAR display is
  computed at render time via the fixed 1 Mbuck = R1 peg, never written
  back to storage as a currency value. This keeps the non-transferability
  enforcement (see §Data Model) intact regardless of display state.

## Data Model (entities, key constraints)

- **ParentAccount** — sole registration custodian; 1 parent account : up
  to 4 ChildProfiles.
- **ChildProfile** — `age_band` enum (`6-9`, `10-14`, `15-18`); no
  standalone login independent of parent-linked account.
- **Budget** — parent-set, per child. **Whole-Rand only (correction
  2026-07-13):** stored as an integer Rand amount; there is no decimal/
  cents field in the `Budget` entity at all — not a nullable or hidden
  field, it does not exist in the schema. See §Mbuck Precision &
  Truncation Rule below and §Screens/Flows for the corresponding
  validation-layer requirement on the input screen.
- **Task** — assigned by parent, `status` (assigned / completed / verified
  / disputed), linked to ChildProfile. **Mbuck earn-value, two
  parent-configurable modes (restored 2026-07-14, sourced from
  `BusinessCase_v5.md`/`Clarifications_v5.md`, the founder's own original
  design, silently dropped from later Business Case versions during the
  case's own review process — this is restored original scope, not a new
  feature):**
  - `earn_mode` — enum, `FIXED` or `PERCENTAGE`, set per task by the
    parent at task-creation time. This is a per-task field, not an
    account-wide or platform-wide setting; a parent may use either mode
    on any individual task.
  - `FIXED` mode: `earn_value` is a whole-Mbuck integer, entered directly
    by the parent. No calculation occurs at any point for this path, so
    the truncation rule below is moot for it — the same constraint as the
    presently-specified model prior to this correction.
  - `PERCENTAGE` mode: `earn_value` is a whole-number percentage (integer
    only, e.g. `1`, `5` — no fractional percentages) applied against the
    child's current `Budget`. The Mbuck amount is computed at
    task-creation/assignment time as `budget × earn_value / 100`,
    truncated to a whole Mbuck per §Mbuck Precision & Truncation Rule
    below, **with a floor of 1 Mbuck applied if that truncation would
    otherwise yield 0** — see that section for the exact truncate-then-
    floor order of operations.
  - **Minimum 1 Mbuck per task, enforced at the ledger-write level (not
    just UI validation), in both modes** — a `FIXED`-mode entry of 0 is
    rejected at input; a `PERCENTAGE`-mode calculation that would
    otherwise yield 0 is floored to 1, never written as 0.
- **MbuckLedgerEntry** — earning events only. **No transfer endpoint, no
  redemption endpoint, no cash-out endpoint exists anywhere in the schema
  or API surface.** This is the direct technical enforcement of the
  locked non-transferability/non-redeemability product-spec constraint
  (`LegalOpinion_v1.md` Q1) that the low money-transmitter-risk finding is
  contingent on. **Any future roadmap change permitting Mbuck transfer or
  redemption requires the money-transmitter legal analysis to be redone
  before implementation** — this is a hard stop on any future feature
  work, not a soft guideline. **Precision (correction 2026-07-13):** the
  `amount` field is a whole-number integer type; there is no decimal/
  sub-unit field anywhere on this entity or in any query/aggregate over
  it. See §Mbuck Precision & Truncation Rule below.
- **MpointLedgerEntry** — flat 10/task, cosmetic-store currency only,
  entirely separate ledger from Mbucks, gated by `MPOINTS_ENABLED`.
- **Payslip/Invoice** — generated periodically from verified
  MbuckLedgerEntries.
- **PaymentConfirmation** — parent-entered confirmation only; no payment
  data or payment-instrument data is ever captured by MiniMoney, since the
  actual payment happens entirely outside the app via the parent's own
  banking app.
- **Dispute** — linked to Task or Payslip; `opened_at`, `status`
  (open/accepted/declined/escalated); the 48-hour SLA and the
  dispute-escalation capacity threshold (see §Operations) are computed
  fields, not hardcoded UI copy.
- **LatePenaltyEvent** — linked to Payslip; enforces the 7-Mbuck production
  cap / 3-Mbuck pilot cap at the ledger-write level, not just UI
  validation. **Truncation-rule applicability confirmed not needed
  (correction 2026-07-13):** the escalating penalty figures (any weekly
  step schedule up to the 7-Mbuck production / 3-Mbuck pilot cap) are set
  directly as whole-Mbuck integers by design — they are not derived from
  a percentage-of-budget or any other calculation that could produce a
  fractional remainder, so the truncation rule below does not apply to
  this entity. Confirmed, not assumed.
- **ConsentRecord** — versioned, timestamped, structurally separate table
  from ParentAccount creation (see §Compliance).
- **ExamBonusRecord** — behavior-input log (primary) + grade-input field
  (secondary, parent-entered, self-reported) — see §Build-Spec Items
  Introduced by the Hybrid Bonus below. **Truncation-rule applicability
  flagged, not confirmed either way (correction 2026-07-13):** as
  currently specified, this BuildSpec does not define a percentage- or
  formula-based conversion of the behavior-checklist or grade-input field
  into a Mbuck amount — the Mbuck bonus value mechanism is not detailed
  in the Developing Committee's inputs for this entity. If a
  percentage-based or otherwise calculated bonus amount is introduced
  (e.g., "bonus = X% of budget" or "bonus = X% of grade delta"), it must
  apply the truncation rule below. Do not assume this currently applies;
  confirm against the actual bonus-calculation logic when it is built.
- **Pilot measurement instruments** (PSI-SF/FAD-GFS items, abbreviated
  CPRS Conflicts subscale, motivation-probe items) are **not** modeled as
  in-app database entities. They are administered via an external
  survey tool at defined pilot timepoints (baseline, mid-pilot), kept out
  of the production data model entirely, as a data-minimization measure —
  this reduces the amount of sensitive child-welfare data MiniMoney's own
  systems ever hold.

## Mbuck Precision & Truncation Rule (correction 2026-07-13)

Founder-identified correction, applied before any code was written.

- **Peg and precision, confirmed:** 1 Mbuck = R1 (the lowest usable
  denomination of the local currency — R1 for South Africa). Mbuck has
  **no sub-unit/cents representation anywhere in the ledger, in any UI
  surface, or in any stored or computed value.** Every Mbuck-typed field
  in the schema (`MbuckLedgerEntry.amount`, `Budget` where it is
  Mbuck-denominated, `LatePenaltyEvent` amounts, any future
  Mbuck-bonus field) is a whole-number integer type. This is a schema-
  level constraint, not a display-formatting convention layered on top of
  a decimal type — do not implement this as a `Decimal`/`Float` field
  with cosmetic rounding in the UI.
- **Truncation, not rounding, not carry-forward:** wherever a Mbuck
  amount is derived from a calculation that could yield a fractional
  result (the only currently-specified example being a percentage
  applied to a Rand amount, e.g. 1% of a R120 budget = R1.20), the
  fractional remainder (the R0.20 in that example) is **dropped at
  calculation time**. It is:
  - **not** rounded up or down to the nearest whole Mbuck,
  - **not** tracked anywhere (no "remainder" or "carry" field),
  - **not** accumulated across periods for later correction or payout.
  Implement this as integer division / explicit truncation
  (`floor()` toward zero on a non-negative amount), not as a rounding
  function, and not as a running-total adjustment.
- **Where this rule currently applies, confirmed per entity:**
  - `Budget`: no calculation occurs at input (see whole-Rand-only input
    constraint below), so truncation is moot at the point of entry. If
    `Budget` is later read into a percentage-based calculation elsewhere
    (e.g. a future task-rate feature), that calculation is where the
    rule applies, not the `Budget` entity itself.
  - Task earn-rate (percentage-of-budget): **confirmed in scope (restored
    2026-07-14)** — traced by the Chief of Staff to this case's own
    original design record (`BusinessCase_v5.md`/`Clarifications_v5.md`),
    present through early Business Case versions and silently dropped
    from later versions during the case's own review process; this is
    restored original scope, not a new feature. When a task is created in
    `PERCENTAGE` mode (see §Data Model above), the calculated value
    (`budget × earn_value / 100`) is truncated to a whole Mbuck — any
    fractional remainder is dropped, never rounded or carried forward —
    **except that the result is floored to 1 Mbuck, never 0**, per the
    original design's stated 1-Mbuck-per-task minimum. Apply these in
    order: (1) truncate the calculated value toward zero; (2) if the
    truncated result is 0, set it to 1 instead. This floor is a fixed,
    narrow exception to the general truncate-and-drop rule — it applies
    here specifically because the original design explicitly stated this
    minimum, and it is not a general license to round up elsewhere in the
    product. `FIXED`-mode task values (parent-entered whole-Mbuck
    integers) are unaffected by this bullet — no calculation occurs on
    that path, so neither truncation nor the floor applies to it, though
    the same 1-Mbuck minimum is separately enforced there at input
    validation (a parent cannot enter 0).
  - Exam-performance bonus mechanic: **not currently specified as a
    percentage- or formula-based calculation** in this BuildSpec (see
    `ExamBonusRecord` above) — flagged as a forward constraint on the
    same basis as the task earn-rate item above.
  - Late-penalty mechanic: **confirmed this rule does not apply.** The
    7-Mbuck production cap / 3-Mbuck pilot cap and any weekly escalation
    step values are set directly as whole-Mbuck integers, not derived
    from a percentage or other fractional-yielding calculation.

## Screens / Flows

1. Parent registration (phone number capture for OTP verification).
2. SMS-OTP identity verification (see §Compliance).
3. Consent flow — separate screen(s) from registration, POPIA s34/
   s35(1)(a)-aligned, versioned acceptance record written on completion.
4. Child profile creation (age-band selection).
5. Budget setup. **Whole-Rand-only input (correction 2026-07-13):** this
   screen must not present a cents/decimal input field at all — this is a
   validation-layer constraint (the input control accepts and the backend
   validates integers only, rejecting any submission containing a decimal
   point or fractional value), not merely a display-formatting choice
   layered over a decimal-capable field. See §Mbuck Precision &
   Truncation Rule.
6. Task list (child view) / task creation & verification (parent view).
   **Task creation includes an earn-mode selector (restored 2026-07-14):**
   fixed whole-Mbuck amount, or whole-number percentage of budget — see
   §Data Model (Task) and §Mbuck Precision & Truncation Rule. The parent
   chooses the mode per task; the UI must not offer a fractional-percentage
   input.
7. Payslip/invoice view.
8. Payment confirmation ("I have paid" parent-side action; no in-app money
   movement).
9. Dispute flow: accept/decline within 48 hours; past-due banner +
   escalation to manual founder-review queue beyond that window.
10. Late-penalty grace-period reminder notifications (parent-facing only).
11. Exam-bonus grade-input (parent) + behavior-log view — **not enabled
    for any real family pre-pilot until the motivation-probe review has
    occurred** (build/QA with test data only until then).
12. Mpoint cosmetic store — built but hidden behind `MPOINTS_ENABLED`.
13. Account-linking flow (aggregator, e.g. Stitch/Mono-style, opt-in) —
    built but hidden behind `ACCOUNT_LINKING_ENABLED`.

## Third-Party Dependencies

| Dependency | Purpose | Why chosen |
|---|---|---|
| Room | Local persistence | Standing Android/Kotlin architecture convention; offline-capable, works well with MVVM/Hilt. |
| Hilt | Dependency injection | Standing Android/Kotlin architecture convention; reduces boilerplate for a solo-founder build. |
| Jetpack Compose | UI | Standing Android/Kotlin architecture convention; faster iteration for a solo, AI-assisted build than legacy View system. |
| WorkManager | Scheduled reminders (grace-period, dispute-SLA checks) | Reliable, battery-friendly background scheduling built into the Android platform; avoids a bespoke server-side cron dependency given the minimal-backend approach. |
| Push notification service (e.g. Firebase Cloud Messaging) | Reminders, dispute-escalation alerts to founder | Free tier is sufficient at pilot/MVP scale, consistent with the R10,000 budget constraint; avoids building custom push infrastructure. |
| Account-linking aggregator SDK (Stitch/Mono-style) | Optional account-linking feature | Named in `BusinessCase_v24.md` as the intended integration partner category; **integrated but disabled** behind `ACCOUNT_LINKING_ENABLED` pending the SARB/NPS Act recheck. No SDK contract/cost commitment should be finalized until that recheck resolves. |

No payment-processing, e-money, or money-transmission SDK is included —
consistent with the locked constraint that MiniMoney never moves or holds
funds.

## Compliance Requirements as Concrete Technical Constraints

- **POPIA s34/s35(1)(a) consent:** consent flow is a structurally separate
  screen sequence from account registration, not a checkbox embedded in
  the registration form. Each acceptance writes a versioned
  `ConsentRecord` (consent-text version, timestamp, parent account ID).
  Re-consent is required whenever the consent-text version changes.
- **Parent identity verification (hardening recommendation, resolved):**
  SMS one-time-password (OTP) sent to the phone number entered at
  registration; registration cannot complete without a verified OTP
  match. This is a lightweight, low-friction mechanism consistent with
  the R10,000 budget and does not require ID-document verification at
  launch.
- **POPIA s14 retention period and deletion trigger (resolved, previously
  a named pending design task):**
  - Active-account data is retained for the lifetime of the account, plus
    a 90-day post-closure window (to allow dispute/payslip reconciliation
    after account closure).
  - **Parent-initiated deletion:** on a parent's deletion request, all
    identifiable PII is deleted within 30 days, consistent with POPIA's
    "as soon as reasonably practicable" standard.
  - **Inactivity-triggered deletion:** an account (no parent or child
    login) inactive for 24 consecutive months triggers an automated
    deletion notice to the parent's registered contact, followed by a
    30-day grace period, after which PII is anonymized/deleted.
  - This is a Developing Committee-resolved parameter set, since
    `LegalOpinion_v1.md` confirmed no minor-specific supplementary POPIA
    retention rule exists — the specific period/trigger was an open
    implementation decision within scope, not a legal question requiring
    further counsel.
- **Terminology governance (debt-coded language reserved to parent-facing
  surfaces):** implemented as two separate string-resource namespaces
  (`strings_parent.xml` / `strings_child.xml` equivalent), enforced by a
  build-time lint check that fails the build if a parent-facing debt term
  ("invoice," "arrears," "late penalty," etc.) appears in a child-facing
  resource file. The underlying interpretive legal uncertainty (no ARB
  ruling directly on point) is not resolved by this constraint and is not
  claimed to be.
- **SARB/NPS Act (account-linking) and FPB (Mpoints) open regulatory
  questions:** both implemented as config-level feature flags
  (`ACCOUNT_LINKING_ENABLED`, `MPOINTS_ENABLED`), OFF by default. The app
  must build and run correctly in all three configurations named in
  `BusinessCase_v24.md`: full; without account-linking; without Mpoints.
  QA must explicitly test all three configurations before launch.
- **Data-breach/incident-response commitment:** implemented as (a) an
  incident-response runbook document (breach definition; notify affected
  parents and the Information Regulator per POPIA s22; "as soon as
  reasonably possible" notification standard; content requirements) and
  (b) a technical requirement for access-logging/alerting on the PII
  tables (`ParentAccount`, `ChildProfile`, `ConsentRecord`) sufficient to
  detect and evidence a breach event. **This commitment and its
  supporting logging must be built, but must not be represented as final
  policy, and no real family's data may be collected under it, until the
  Data-Privacy Practitioner has actually reviewed it** (see
  `ExecutionInstructions.md`).
- **Mbucks non-transferability (money-transmitter risk avoidance):**
  enforced structurally at the data-model/API level (see §Data Model) —
  not merely a documented policy, so it cannot be silently violated by a
  future feature addition without that addition also requiring the
  money-transmitter legal analysis to be redone.

## Operations — Dispute Handling (capacity threshold, resolved)

The interim manual founder-review dispute-escalation mechanism is deemed
to have **failed** when either:

- more than 5 disputes are concurrently open beyond the 48-hour
  parent-decline window, or
- average founder response time to an escalated dispute exceeds 5
  business days.

Crossing either threshold must trigger an explicit, logged
founder-capacity review — this is a new, Developing Committee-resolved
operational threshold, closing a previously open gap
(`TraceabilityMatrix.md` row 22). It does not resolve the broader,
carried-forward aggregate founder-capacity assessment (row 21), which
remains an outstanding founder action.

## Build-Spec Items Introduced by the Hybrid Bonus

- **Behavior-input logging/verification mechanism:** parent marks
  qualifying behaviors as observed via a structured checklist tied to the
  ExamBonusRecord; no automated verification (e.g. no third-party
  attestation) is in scope for launch.
- **Grade-input mechanism:** self-reported, parent-entered numeric or
  letter-grade field, no school-system integration in scope for launch.

## Trimmed Scope

Everything below was trimmed from Incubator-originated scope, each with a
stated reason. **No Investment Committee finding, risk, or required
change is trimmed here** — see `TraceabilityMatrix.md` for how every
Investment Committee item is instead tracked or addressed.

| Trimmed item | Reason |
|---|---|
| Structured curriculum content / Fintech Advance module, at launch | Already deferred by the Business Case itself to v2, behind a quantified trigger (500 subscribers AND 60% 90-day retention); building it now would be speculative effort against an unvalidated feature. |
| Three-tier-to-six-way sub-band reconciliation (6, 7, 8, 9-10, 11-14, 15-18) | Incubator-authored draft, Evidence: Assumed, unreviewed by the child-development specialist. Not build-ready; the three-tier model (6-9/10-14/15-18) is used instead until the finer split is specialist-reviewed. |
| AI-mediated dispute resolution | Named future feature; the interim manual founder-review mechanism (with the newly resolved capacity threshold above) is used at MVP/pilot stage instead. |
| Schools-partnership channel integration | Explicit founder-bandwidth-based deferral, already decided in the Business Case; no engineering work required for a channel not being pursued. |
| iOS build | Android-first decision already made; no iOS-specific work (e.g. IAP-currency handling for Apple's Kids Category) is in scope until post-launch traction evaluation. |
| Account-linking and Mpoints, as *enabled* features | Both are built but shipped disabled (feature-flagged) rather than fully excluded, since both are named, decided product features pending only an external regulatory recheck — trimming them to "not built at all" would exceed what the Business Case's own fallback calls for. |

## What Remains Out of Scope for This Build Cycle (not trimmed, carried forward)

Per `TraceabilityMatrix.md`, the following are process/compliance/business
obligations, not build items, and are not part of this BuildSpec at all —
tracked instead in `ExecutionInstructions.md`:

1. Completing the Data-Privacy Practitioner and child-development
   specialist reviews (pre-pilot gate).
2. A minimal P&L/break-even model.
3. A quantified stop/redesign threshold for the child-welfare pilot
   instruments.
4. An aggregate founder-capacity/bandwidth assessment.
