# Product Requirements Document: MiniMoney

> Prepared by: Developing Committee, from `BusinessCase_v24.md` (final)
> and `Verdict_v7.md`, cross-checked against `TraceabilityMatrix.md`. All
> open technical/product decisions within the Developing Committee's own
> remit are resolved below. The four items explicitly out of scope for
> this cycle per the user's authorized deviation (two specialist reviews;
> P&L/break-even model; child-welfare stop/redesign threshold; aggregate
> founder-capacity assessment) are process/compliance/business obligations,
> not technical decisions, and are intentionally not force-resolved here —
> see `TraceabilityMatrix.md` and `ExecutionInstructions.md` for how they
> are tracked instead.

> **Correction log — 2026-07-13, pre-Milestone-1, founder-identified.**
> Mbuck currency precision was under-specified: whole-unit-only precision
> (no cents), the truncation-not-rounding rule for any percentage-based
> Mbuck calculation, and the whole-Rand-only budget input constraint are
> added below at the point of change. See `BuildSpec.md` §Mbuck Precision
> & Truncation Rule for the full technical detail; this file states the
> product-level consequence only. No code had been written against the
> prior version at the time of this correction.

> **Correction log — 2026-07-14, pre-Milestone-1, Chief-of-Staff-traced.**
> A percentage-of-budget task earn-rate mechanic, referenced in the
> 2026-07-13 correction above but absent from this document's permitted
> inputs at the time and therefore left flagged rather than specified, has
> since been traced by the Chief of Staff and confirmed as real,
> established design: sourced from this case's own historical record
> (`BusinessCase_v5.md`, itself sourced from `Clarifications_v5.md`, the
> founder's own original design), present through early Business Case
> versions and silently dropped from later versions during the case's own
> review process — a defect in that historical record's maintenance, not
> evidence the feature was ever actually cut. It is restored below as an
> in-scope MVP mechanic (see Core Feature 5 and the Open Technical
> Decisions section). See `BuildSpec.md` §Data Model (Task) and §Mbuck
> Precision & Truncation Rule for the full technical detail. No code had
> been written against the prior version at the time of this correction.

## Product Summary

MiniMoney is an Android application, launching in South Africa, that lets
a parent/guardian run a real-money-linked "payroll simulation" for their
child or teen (ages 6-18): the parent sets a budget and assigns tasks, the
child earns Mbucks (a real-money-pegged, non-transferable unit of account,
e.g. 10 Mbucks = R10) and a separate flat 10 Mpoints (a non-monetary
cosmetic-store currency) per completed task, these accumulate into a
periodic "payslip"/invoice, and the parent pays the owed amount directly
to the child through the parent's own banking app — MiniMoney itself never
holds, moves, or has custody of any money at any point. The launch product
is the mechanic alone (budgeting, task/earning loop, payslip, payment
confirmation, dispute handling, and an escalating late-penalty mechanic);
structured instructional financial-literacy curriculum content is a
deliberately deferred v2 feature, gated behind a quantified adoption
trigger. Monetization is a R59.99/month subscription per family (up to 4
children), with zero paid acquisition at launch.

## User Personas / Cohorts

MiniMoney has one payer/administrator role and three functionally
distinct child cohorts. These are kept separate, not merged, because each
faces different UI framing, different mechanic exposure, and different
consent/data-handling treatment.

**Parent / Guardian (customer, payer, sole registration custodian).**
Registers the account, is the only party who can create a child profile,
sets the budget, verifies task completion, receives the payslip/invoice,
makes the actual payment via their own banking app, confirms payment
in-app, decides accept/decline on disputes, and is the recipient of all
debt-coded terminology ("invoice," "arrears," "late penalty"). Also the
subscription purchaser (R59.99/month, up to 4 children).

**Child 6-9 ("early childhood" tier).** Softened task/reward framing, no
debt-coded language exposure anywhere in their surfaces. Excluded from the
exam-bonus grade-input mechanic in any grade band below school-leaving
stage where not applicable, and from Fintech Advance entirely. Late-penalty
exposure is capped more conservatively at pilot stage (3-Mbuck pilot cap
vs. 7-Mbuck production cap) given this cohort's heightened Family Stress
Model sensitivity.

**Child 10-14 ("pre-teen" tier).** Basic transactional literacy framing;
full core mechanic (tasks, Mbucks, Mpoints, payslip, disputes, late
penalty, exam-bonus hybrid). Excluded from Fintech Advance.

**Child 15-18 ("teen" tier).** Pre-employment literacy framing; full core
mechanic; the only cohort in scope for the v2-deferred Fintech Advance
module (trading/entrepreneurship content) once built, under a
risk-literacy (not aspirational) framing and with no product gamification
applied to that content specifically.

The Business Case's finer six-way sub-band split (6, 7, 8, 9-10, 11-14,
15-18) exists as a drafted, unreviewed reconciliation for future
specialist review and is not adopted into this PRD's cohort definitions —
see `BuildSpec.md` §Trimmed Scope.

## Core Features

### MVP (launch)

1. Parent registration and account creation, as sole custodian.
2. Consent flow — structurally and visually separate from general account
   onboarding (see Compliance, `BuildSpec.md`).
3. Child profile creation, age-band assignment (6-9 / 10-14 / 15-18).
4. Budget setting (parent-controlled). **Whole Rand only (correction
   2026-07-13):** the parent cannot input cents — there is no decimal
   input field on this screen at all, enforced at validation, not just
   display (see `BuildSpec.md`).
5. Task creation, assignment, child-side completion marking, parent-side
   verification. **Task Mbuck earn-value, two parent-configurable modes
   (restored 2026-07-14):** for each task, the parent sets its Mbuck value
   in either of two modes — a fixed whole-Mbuck amount, or a whole-number
   percentage of the child's budget (e.g. 1%, 5%). This is a per-task
   choice, not a platform-fixed or account-wide setting. In percentage
   mode, the Mbuck value is calculated from the budget in effect at
   task-creation/assignment time, truncated (not rounded) to a whole
   Mbuck per bullet 6 below, with a floor of 1 Mbuck if the calculation
   would otherwise truncate to zero. A minimum of 1 Mbuck per task applies
   in both modes. See `BuildSpec.md` §Data Model (Task) and §Mbuck
   Precision & Truncation Rule.
6. Mbuck earning ledger — non-transferable, non-redeemable outside the
   payslip/payment flow, fixed peg to Rand (1 Mbuck = R1, the lowest
   usable Rand denomination). **Whole-unit precision only (correction
   2026-07-13):** Mbuck has no cents/sub-unit representation anywhere in
   the ledger. Any fractional remainder arising from a percentage-based
   Mbuck calculation (e.g. 1% of a budget yielding R1.20, or the
   percentage-of-budget task earn-rate in bullet 5 above) is truncated
   and dropped at calculation time — never rounded, never carried
   forward or accumulated for later correction — **except that the
   result is floored to 1 Mbuck, never 0, per the task earn-rate
   minimum in bullet 5** (restored 2026-07-14; this floor does not apply
   to any other percentage-based calculation unless a stated minimum
   applies there too). See `BuildSpec.md` §Mbuck Precision & Truncation
   Rule for which specific mechanics this applies to.
7. Mpoint earning (flat 10/task) and cosmetic store — **feature-flagged
   off by default at launch**, pending FPB recheck (see Compliance).
8. Payslip/invoice generation (periodic).
9. Payment confirmation flow: MiniMoney presents the owed amount; the
   parent pays the child directly via their own banking app, outside
   MiniMoney; the parent marks payment as confirmed in-app.
10. Late-penalty mechanic: grace period, pre-escalation reminder, capped
    escalating penalty (7-Mbuck cap production / 3-Mbuck cap pilot),
    parent-facing only.
11. Dispute mechanism: accept/decline within a 48-hour window; beyond 48
    hours, interim manual founder-review escalation (see `BuildSpec.md`
    §Operations for the defined capacity threshold).
12. Exam-bonus hybrid mechanic: behavior-primary rewards plus a retained,
    secondary results-bonus layer. **Gated: not enabled for any real
    family until the child-development specialist's motivation-probe
    review has actually occurred** (see `ExecutionInstructions.md`
    Milestones — this is a pre-pilot, not pre-build, gate; the mechanic
    may be built and tested internally, but no real child may be exposed
    to it before the review completes).
13. Optional account-linking — **feature-flagged off by default at
    launch**, pending SARB/NPS Act recheck (see Compliance).
14. Age-gated core mechanic, applied per the three-tier cohort model
    above.

### Later (V2+, not built at launch)

1. Structured instructional curriculum content, gated behind a quantified
   dual trigger: 500 paying subscribers AND 60% 90-day retention (both
   required).
2. Fintech Advance module (15-18 only), built alongside curriculum
   content under the same trigger; risk-literacy framing, no product
   gamification applied to this content specifically.
3. iOS port, timing evaluated against Android traction post-launch.
4. Advertising monetization (possible V2 addition).
5. AI-mediated dispute resolution, replacing the interim manual
   founder-review mechanism.
6. Account-linking and/or Mpoints re-enablement, contingent on the SARB/
   NPS Act and FPB rechecks resolving favorably.
7. Schools-partnership acquisition channel exploration.

## Explicit Non-Goals

- MiniMoney will never hold, transmit, or take custody of real money at
  any point, in any configuration. This is a locked, binding
  product-spec constraint, not a launch-only decision (see
  `BuildSpec.md`).
- No structured instructional curriculum content, including Fintech
  Advance, ships at launch.
- No paid acquisition or marketing spend at MVP; growth is organic-only
  via four named channels (founder network/word of mouth; organic social
  media; App Store Optimization; parent/community forums and groups),
  with no expected-volume commitment attached to any of them.
- No schools-partnership channel at launch, deferred for founder-bandwidth
  reasons.
- No iOS build at launch.
- No product gamification applied to Fintech Advance content, whenever
  built.
- Neither the n=10 first-party interview round nor the pilot's own
  directional findings may be treated, cited, or reported internally as a
  statistically validated demand signal. Both are directional only.
- No real child's data is collected, and no real family is enrolled in
  the pilot, until **both** the Data-Privacy Practitioner's review of the
  data-breach/incident-response commitment and the child-development
  specialist's review of the exam-bonus motivation-probe have actually
  occurred, evidenced by documented sign-off — not merely triggered (see
  `ExecutionInstructions.md`). This is a pre-pilot gate; it does not block
  foundational, non-pilot build work.
- Mpoints and account-linking do not ship enabled at launch; both remain
  feature-flagged off pending their respective regulatory rechecks.
- No cents/sub-Mbuck precision anywhere in the product, at any point:
  not in the budget-input screen, not in the Mbuck ledger, not in any
  Mbuck-denominated calculation. Fractional remainders are truncated and
  dropped, never rounded or carried forward (correction 2026-07-13; see
  `BuildSpec.md` §Mbuck Precision & Truncation Rule).
- Mbuck is the default and universal unit of account shown to the user;
  the app does not switch to displaying ZAR unless account-linking is
  both enabled and has confirmed a real payment for that specific amount
  — and even then, this is a display-only change, never a change to the
  underlying ledger unit (correction 2026-07-13; see `BuildSpec.md`
  §Architecture Overview).

## Success Metrics (numeric, falsifiable)

1. **Pilot acquisition/engagement checkpoint:** ≥60% of enrolled pilot
   families (target cohort: 20-50 families) must complete ≥4 consecutive
   weekly task→payslip cycles. Below 60%, organic-only acquisition and
   mechanic engagement are treated as not yet validated, and wider release
   does not proceed on schedule. (Source: `BusinessCase_v24.md`, carried
   through unchanged.)
2. **Operational health:** 65% of tasks complete without a dispute.
   Carried through unchanged from `BusinessCase_v24.md` as the founder's
   existing committed figure; no external benchmark exists for this
   figure, a limitation stated plainly, not resolved here (see
   `TraceabilityMatrix.md` row 20).
3. **Subscription conversion:** 2% of Year-1 family installs convert to a
   paying subscription, benchmarked against the disclosed 1-3% reference
   range. (Source: `BusinessCase_v24.md`, carried through unchanged.)
4. **General 90-day retention: 40% of paying families remain subscribed
   at 90 days.** This figure is newly set by the Developing Committee —
   `BusinessCase_v24.md` explicitly left this as an open question
   ("[w]hether a general retention success criterion... is still needed
   here remains an explicitly open question"), distinct from the
   unrelated 60% 90-day figure that gates the v2-curriculum trigger. 40%
   is a Developing-Committee-set working baseline for build/QA and
   pilot-instrumentation purposes, not a specialist- or user-validated
   target — it should be recalibrated by the founder against real pilot
   and early-launch data as soon as that data exists.
5. **v2-curriculum trigger (dual gate, both required):** 500 paying
   subscribers AND 60% 90-day retention. (Source: `BusinessCase_v24.md`,
   carried through unchanged.)
6. **Dispute-escalation capacity threshold:** the interim manual
   founder-review mechanism is deemed to have failed when either (a) more
   than 5 disputes are concurrently open beyond the 48-hour window, or (b)
   average founder response time to an escalated dispute exceeds 5
   business days. Crossing either threshold triggers an explicit
   founder-capacity review (see `ExecutionInstructions.md`). This is a
   newly set Developing Committee threshold, resolving a previously open
   technical/operational gap (`TraceabilityMatrix.md` row 22).

## Open Technical Decisions

**None remaining.** Every implementation-level decision identified as
open in `BusinessCase_v24.md` and `Verdict_v7.md` that falls within the
Developing Committee's remit is resolved above or in `BuildSpec.md`
(feature flags for account-linking and Mpoints; POPIA retention
parameters; parent identity-verification mechanism; consent-flow
separation; dispute-escalation capacity threshold; general-retention
success metric; Mbuck precision/truncation rule and conditional
currency-display behavior, corrected 2026-07-13). The four items
intentionally not resolved here — completing the two specialist reviews,
the P&L/break-even model, the child-welfare stop/redesign threshold, and
the aggregate founder-capacity assessment — are not technical decisions;
they are outstanding founder actions/business obligations, tracked in
`ExecutionInstructions.md`, per the user-authorized routing deviation and
confirmed as such in `TraceabilityMatrix.md`'s hidden-technical-decision
check.

**Resolved 2026-07-14 (supersedes the "flagged, not resolved" note carried
in the 2026-07-13 correction):** the percentage-of-budget task earn-rate
mechanic is confirmed in scope for this build, traced by the Chief of
Staff to the case's own original design record (`BusinessCase_v5.md`,
sourced from `Clarifications_v5.md`, the founder's own original design),
present through early Business Case versions and silently dropped from
later versions during the case's own review process — a defect in that
historical record's maintenance, not evidence the feature was ever
actually cut. It is now a specified build item — see Core Feature 5 above
and `BuildSpec.md` §Data Model (Task) and §Mbuck Precision & Truncation
Rule.

**Still flagged, not resolved:** whether a percentage- or formula-based
exam-bonus Mbuck calculation is in scope for this build. No equivalent
historical record confirming this mechanic has been traced. It remains
unspecified as an implemented calculation in `BuildSpec.md`, flagged so
the founder confirms scope before building it, not assumed silently
either way. See `BuildSpec.md` §Mbuck Precision & Truncation Rule.
