# Business Case: MiniMoney — v18

> Prepared by: Incubator. This revision responds to the Investment
> Committee's third review (`Verdict_v3.md`, "Proceed with Changes",
> seven required changes) using the user's item-by-item decisions in
> `Clarifications_v18.md`, which resolve all seven. Authorized inputs for
> this cycle: `00_CaseStudy.md`, `BusinessCase_v17.md`, `Verdict_v3.md`,
> `Clarifications_v18.md`. All seven required changes are addressed
> below; the Committee's Gate Integrity observation about what "Complete"
> means in this rubric is addressed once, explicitly, in the Readiness
> Score section, and applied consistently throughout.

## What Changed in v18 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

All seven required changes from `Verdict_v3.md` are resolved by direct
user decision (`Clarifications_v18.md`, Verified-tier as to what was
decided):

1. **All six specialist design recommendations are now decided.** Five
   adopted as recommended: parent-facing-only debt terminology (1a);
   late-penalty grace-period/pre-escalation reminder mechanism (1c);
   Fintech Advance gamification-avoidance (1d); three-tier curriculum
   age framework (1e); the full pilot-measurement package (1f). The
   sixth — the exam-bonus mechanic (1b) — is adopted as a **user-designed
   hybrid**: the primary reward now targets controllable behaviors
   (effort: study time, homework completion), following the field
   evidence, while a **secondary bonus layer contingent on improved
   results is deliberately retained**. This is a partial adoption with a
   known, accepted residual intrinsic-motivation risk — documented
   honestly in Operations, Risks, and Assumptions, not smoothed over.
   Per the Committee's sequencing condition, items 1b and 1c are decided
   now, before any family enrolls in the pilot — satisfied at the
   decision level; build implementation follows.
2. **The funnel unit is resolved: per FAMILY.** One subscription = one
   family = up to 4 children. The funnel and revenue model are restated
   on this basis throughout. **The 180-1,830 paying-family range
   survives the correction; the 360-2,440 range is retired** (see Market
   & Competition, Revenue & Costs).
3. **Both regulatory rechecks now have an owner and timing: the user
   personally, at build-spec stage**, with explicit launch fallbacks —
   launch **without account-linking** if SARB/NPS Act is unresolved;
   launch **without Mpoints** if FPB is unresolved. A full
   ripple-effect trace of the no-Mpoints launch configuration
   (cosmetic store, 10-Mpoints-per-task reward, Google Play
   loyalty-point disclosure) is documented in Legal & Compliance.
4. **The unverified legal citation is now named** (Conradie v Rossouw
   pinpoint reference) and carried as an open external action with the
   retained lawyer — pending, not blocking, not dropped.
5. **The curriculum-content workstream is committed to run in parallel
   with the engineering build, starting now** — not after it.
6. **The pilot will validate BOTH mechanic safety/child-development
   signal AND market demand** — the user's explicit choice, made knowing
   the reviewer's caution that 20-50 families is statistically
   underpowered. Demand findings will be directional/qualitative, not
   validated. Documented with that caveat attached.
7. **Cost/runway is now supplied**: R10,000 total development budget;
   professional opinions at zero marginal cost via the user's existing
   policy; 6-month runway before funding is needed. Reconciled plainly
   against the previously-cited $25,000-$120,000+ agency range —
   the budget prices in the founder's own unpaid labor plus AI-assisted
   development, and **the 6-month runway is the binding constraint**.
   This is named as the case's execution-capacity risk (Financial
   Considerations, Constraints, Risks, Critical Gaps).

**Also this cycle:** the rubric's definition of "Complete" is stated
explicitly (Readiness Score section) per the Committee's Gate Integrity
observation, and every affected section is reassessed against it; and
Market & Competition is restored to self-contained text (it was carried
in v17 as a cross-reference to v16, which is not among this cycle's
authorized inputs — see that section's provenance note).

**The Readiness Score is unchanged at 70.0% (91/130).** Per Playbook
Entry 1, this is stated explicitly rather than left to be noticed: the
seven required changes were predominantly decision-making and
reconciliation within sections that were already scored Complete under
v17's looser reading of "Complete," or that remain Partial for
independent, unresolved reasons (unvalidated demand, unbenchmarked
success criteria, no CAC budget). The definitional tightening of
"Complete" (which would have demoted Operations, Risks, and Roadmap as
scored in v17) and the decisions that re-earn those sections' Complete
status under the tighter definition net out to a flat score. The case is
materially more decided than v17; the score's stability reflects rubric
tightening offset by genuine resolution, not ignored feedback.

## Executive Summary

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18), launching first in
South Africa on Android (iOS porting planned as future work), combining
gamified task assignment with a simulated payroll system. The parent
submits a budget setting the minor's "basic income"; tasks earn Mbucks (a
real-money-pegged in-app currency, e.g. 10 Mbucks = R10) which accumulate
into a "payslip," while every completed task separately earns a fixed 10
Mpoints — a distinct, non-monetary cosmetic-store currency. The parent
receives an invoice and pays the owed amount directly to the child via
the parent's own banking app — MiniMoney itself never holds, transmits,
or takes custody of funds. Subscription pricing is R59.99/month, covering
up to 4 children per family account; **the funnel and revenue unit is
the family** (one subscription = one family = up to 4 children), resolved
this cycle. Monetization is subscription-only at launch, with advertising
deferred to a possible post-launch V2. The late-payment penalty mechanic
is incurred entirely by the parent (5→6→7 Mbucks/week, pilot cap 3); the
child has zero visibility into it, and a grace-period/pre-escalation
reminder mechanism is now committed to reduce trigger frequency at the
source. The exam-period bonus is redesigned this cycle as a user-defined
hybrid: primary rewards for controllable behaviors (study time, homework
completion), with a secondary bonus retained for improved results — a
deliberate partial adoption of the specialist recommendation carrying a
known, accepted residual intrinsic-motivation risk. A distinct,
15-18-only curriculum element, "Fintech Advance," teaches the concepts of
trending/entrepreneurial ventures (forex trading, dropshipping) with no
in-app trading execution, gated by a separate explicit parent opt-in, and
will not use the product's own Mpoints/badge gamification for its
content (adopted this cycle).

**This cycle's central development:** the Investment Committee's seven
required changes are all resolved by direct user decision. All six
specialist design recommendations are decided (five adopted as
recommended; the exam-bonus as the hybrid above). Both newly-surfaced
regulatory rechecks (SARB/National Payment System Act for
account-linking; FPB classification for Mpoints) now have a named owner
(the user personally), a timing trigger (build-spec stage), and explicit
launch fallbacks: without account-linking, and without Mpoints,
respectively — with the no-Mpoints configuration's ripple effects on the
cosmetic store, the per-task Mpoints reward, and the Google Play
loyalty-point disclosure item traced in full. The pilot is confirmed as
double-duty (mechanic safety AND demand), with the reviewer's
underpowering caution attached: demand findings will be directional, not
validated. The curriculum workstream is committed to run parallel with
the build, starting now.

**The case's financial picture is now stated, and it is thin by
design:** R10,000 total development budget, professional opinions at
zero marginal cost via the user's existing policy, and a 6-month runway
before external funding is needed. Against the previously-cited
$25,000-$120,000+ agency engineering range, the R10,000 (~$550) figure
is not a comparable build budget — it prices in the founder's own unpaid
labor plus AI-assisted development, with the cash covering incidentals,
tooling, and on-demand external help. The binding constraint is the
6-month runway: build (~3 months directional), parallel curriculum
authoring, pilot instrumentation and execution, and two personally-owned
regulatory rechecks must all fit inside it, executed substantially by
one person. This is named as the case's execution-capacity risk.

**The Readiness Score holds at 70.0% (91/130), clearing the completion
gate's ≥70% threshold with no margin.** This cycle also defines
"Complete" explicitly in the rubric (a section is Complete only when
every material decision in its scope is made, not merely documented) and
reassesses every affected section against that definition — the score is
flat because the tightened definition and this cycle's decisions offset,
as detailed in the Readiness Score section.

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Parents lack a structured, automated system to teach children (6-18)
real-world financial concepts — earning, budgeting, taxation/expenses,
and payment mechanics — using real money in a controlled, task-based
framework. Existing allowance-tracking apps typically either (a)
simulate money entirely in-app with no real bank transfer, or (b)
require manual parent bookkeeping with minimal education layer. The
underlying gate on this problem is parent willingness and
digital-financial engagement (SARB: 50.3% of SA adults use banking apps
regularly, adjusted to a [Guessing] 55-65% for the economically-active
parent cohort), not device access among children ([Likely] 62%
personal-device ownership by age 10, per a 2024 Stellenbosch-region study
of five former Model C high schools, Grade 4-11).

A first-party interview round (n=10 families) found 6 of 10 confirmed
interest in using the app and stated willingness to pay for it; 7 of 10
expressed interest specifically in the education aspect. This is
genuine, first-party, MiniMoney-specific evidence, categorically
different from comparable-market inference, but it is not statistically
significant. Per a standing instruction adopted at v9 and reaffirmed at
v10, this data point must not be used as if it were a representative or
validated demand signal until superseded by the planned 20-50 family
pilot or a structured survey.

**Change this cycle:** the pilot is now confirmed as the vehicle for a
demand read (see Validation Strategy) — but per the child-development
reviewer's own caution, a 20-50 family pilot is underpowered for
statistical validation, so its demand findings will be directional and
qualitative. Status remains Partial for the same reason it has since
v8: there is a real, encouraging, directional signal, and now a
scheduled (directional) follow-up — but still no established finding
that parents broadly perceive this as a problem worth paying to solve.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic rather than a simple
debit-card-for-kids model. No direct South African incumbent does what
MiniMoney does. `ResearchFindings_v1.md` (prior cycle) adds a directional
data point: MoneyAfrica Kids shows modest download volumes while
MoneyTime SA claims a larger, self-published B2B2C-mediated reach via
schools — together suggesting real but unproven consumer appetite, with
the strongest demonstrated reach coming via a schools-distribution model
(which still has no timeline, target, or resourcing plan in this case —
see Outstanding Questions).

The subscription price (R59.99/month, up to 4 children per family)
sharpens the competitive read against MoneyTime SA's R995/year (25%
sibling discount): MiniMoney's annualized price (R719.88/family/year)
sits below MoneyTime SA's rate even before the sibling discount —
relevant opportunity context, but this does not on its own establish
market size or demand, which remains governed by the same n=10,
non-representative bound described in Problem. Status remains Partial:
the differentiation thesis is coherent and partly evidenced, but no
structured market-sizing or validated demand study has been conducted;
the pilot's demand read (decided this cycle) will be directional only.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The functional objective is: budget → tasks → Mbuck/Mpoint earning →
exam-period bonus (hybrid: behavior-primary rewards plus a retained
secondary results bonus, per this cycle's decision — see Operations) →
invoice/payslip → payment confirmation with escalating late-penalty
(now with a committed grace-period/pre-escalation reminder mechanism) →
age-gated education. The late-penalty step is incurred entirely by the
parent and is invisible to the child.

**Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
payment loop, including the dispute and late-penalty mechanics, with a
small pilot cohort of South African families (candidate target: 20-50
families) before wider release. Per this cycle's decision, the pilot
formally adopts the specialist pilot-measurement package (see Success
Criteria) and serves double duty: mechanic-safety signal AND a
directional demand read (see Validation Strategy).

**Growth (6-12 months):** validate the subscription-conversion assumption
against the 1-3% subscription-only reference range; validate curriculum
engagement as a leading indicator of retention; evaluate iOS port timing
based on Android traction.

The 90-day (15,000 installs) vs. annual funnel (18,000-61,000 installs)
target tension remains resolved via `Clarifications_v10.md` (explicit
front-loaded-growth model: 100/day floor, ramping above it). **Per this
cycle's funnel-unit decision, all install and subscriber figures are
per-family** (one install-unit = one family account). Status remains
Complete: every tension previously flagged in this section is resolved
by direct, Verified-tier user clarification.

## Success Criteria

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Core criteria, carried from v8/v9: pilot success (majority of families
complete ≥4 consecutive weekly cycles); curriculum engagement (30%, no
external benchmark); operational health (65% task-completion without
dispute, no external benchmark); freemium/subscription conversion (2%,
benchmarked against the 1-3% subscription-only range); retention (no
figure proposed). The curriculum-engagement, operational-health, and
retention criteria remain unbenchmarked — per the Investment Committee's
own risk list, they should be treated as placeholders, not
evidence-grounded targets.

**Family-relationship-strain criterion — measurement package now
formally ADOPTED into pilot design (this cycle, per user decision 1f).**
The specialist-designed instruments specified by
`ChildDevelopmentReview_v1.md` are no longer a pending recommendation:

- **Borrowed items (not full scales) from the Parenting Stress Index –
  Short Form** (Abidin; Parental Distress, Parent–Child Dysfunctional
  Interaction, Difficult Child subscales) and the **Family Assessment
  Device – General Functioning Scale** (Epstein, Baldwin & Bishop, 1983;
  12 items), administered to parents at baseline and again partway
  through the pilot.
- **Within-family, within-week correlation tracking**: whether weeks
  with a late-penalty event coincide with higher parent- (and
  age-appropriate child-) reported household tension than weeks without
  one — testing the Family Stress Model hypothesis directly rather than
  assuming it.
- **Age-stratified results** (6-9, 10-14, 15-18 bands), not pooled.
- **A brief, age-appropriate child-report instrument** alongside
  parent-report — an abbreviated version of the **Child–Parent
  Relationship Scale** (Conflicts subscale) — because parents under
  stress are established under-reporters of their own irritability.
- **Explicit caution from the reviewer, carried forward verbatim in
  effect**: 20-50 families is not large enough for full
  validated-instrument statistical power; these are for lightweight,
  qualitative early-warning signal detection, not statistical
  validation, and the pilot should not be over-instrumented beyond this.

The underlying substantive risk remains confirmed, not resolved — the
late-penalty redesign narrows but does not eliminate the Family Stress
Model's affective pathway. Both named design responses are now engaged:
the grace-period/pre-escalation reminder mechanism is committed
(reducing trigger frequency at the source, decision 1c), AND the
measurement package above tracks the residual (decision 1f).

**One measurement gap noted, not invented away:** the exam-bonus
hybrid's retained outcome-contingent layer carries an accepted residual
intrinsic-motivation risk (see Operations) that the adopted measurement
package — designed for family-stress detection — does not formally
instrument. Motivation effects can be observed qualitatively during the
pilot but are not a measured criterion. Named as an open pilot-design
consideration in Outstanding Questions.

Status remains Partial: the relationship-strain criterion now has an
adopted, specialist-designed measurement plan, but curriculum engagement,
operational health, and retention remain unbenchmarked, and retention has
no proposed figure at all.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18;
parents/guardians as sole registration custodian and subscription
purchaser; the app operator (a solopreneur founder); the South African
Information Regulator and the Advertising Regulatory Board; three named
competitor/adjacent-market stakeholders — African Bank's MyWORLD Power
Pocket, MoneyAfrica Kids, MoneyTime SA; Apple/Google as app-store
platform stakeholders.

Two regulator stakeholders surfaced by `LegalOpinion_v1.md` (v17 cycle)
remain:

- **The South African Reserve Bank (SARB) and the Payments Association
  of South Africa (PASA)**, via the National Payment System Act —
  engaged specifically by the optional account-linking feature's
  open-banking question. **This cycle: the recheck is owned by the user
  personally, timed to build-spec stage, with an explicit fallback
  (launch without account-linking if unresolved).**
- **The Film and Publication Board (FPB)**, via the Films and
  Publications Amendment Act 2019 — of uncertain but plausible
  application to the Mpoints gamified rewards system. **This cycle: the
  recheck is owned by the user personally, timed to build-spec stage,
  with an explicit fallback (launch without Mpoints if unresolved) —
  ripple effects traced in Legal & Compliance.**

The linking aggregator (Stitch/Mono-style, where a parent opts in)
remains an additional data-processor stakeholder per
v14/`ResearchFindings_v2.md`. The retained legal counsel and retained
child-development professional are engaged specialist stakeholders; the
retained lawyer additionally carries the open Conradie v Rossouw
citation-verification action. A future AI mediator feature for dispute
resolution remains explicitly out of current scope.

Status remains Partial: both new regulator stakeholders now have an
owned recheck and a fallback, but their specific obligations (SARB/PASA
open-banking exposure; FPB classification requirements, if applicable)
remain unresolved pending those rechecks.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18, and their
parents/guardians, in South Africa, on Android at launch (iOS deferred).
A minor is not an independently reachable user: every child account
requires a parent acting as registration custodian from the outset.
**The paying customer unit is the family** (one subscription = one
family = up to 4 children), resolved this cycle — the child is the user,
the parent is the customer, and all funnel counts are family counts.
Status remains Partial: the target population is clearly named and the
customer unit is now unambiguous, but no market-sizing or persona-level
detail exists beyond Market & Competition and the funnel figures in
Objectives.

## Value Proposition

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The Free/Subscription feature split, the R59.99/month (up to 4 children
per family) price, and the full Fintech Advance description stand as
restored at v16 and carried through v17. Constraints and decisions now
attached:

**Mbucks non-transferability — a locked product-spec constraint.** Per
`LegalOpinion_v1.md` Q1, MiniMoney's low money-transmitter/e-money risk
is contingent on Mbucks remaining a pure unit-of-account: it cannot be
spent in-app, transferred between users, or redeemed for value other
than through the parent's own independent decision to pay via their own
banking app. Any future roadmap change to this requires the
money-transmitter analysis to be redone (see Legal & Compliance,
Business Model, Constraints).

**Fintech Advance mitigation — ADOPTED this cycle (decision 1d).** The
module will NOT use MiniMoney's existing Mpoints/badge gamification for
the trading-education content itself, and its presentation leans toward
risk literacy (why these pursuits are volatile/high-failure-rate) rather
than aspirational framing, per `ChildDevelopmentReview_v1.md` Q5. This
was a named-but-undecided recommendation in v17; it is now a made
decision.

**Terminology — ADOPTED this cycle (decision 1a).** Debt-coded language
("invoice," "arrears," "late penalty") is reserved for parent-facing
surfaces only; child-facing surfaces use softer language ("payslip"
stays; "arrears"/"penalty" wording never appears on the child's side).
This implements the legal opinion's mitigation for the case's single
highest-optics-risk item.

**Conditional exposure, named not hidden:** under the no-Mpoints launch
fallback (see Legal & Compliance), the in-app cosmetic store — part of
the child-facing subscription feature set — has no currency and must be
removed from that configuration, thinning the subscription tier's
child-facing appeal. The value proposition as specified is complete for
the primary configuration; the fallback configuration's feature-table
variant is a named conditional design item (Outstanding Questions).

Status remains Complete under this cycle's tightened definition: price,
feature boundaries, and all previously-pending decisions within this
section's scope are now made; the fallback variant is an explicitly
tracked conditional, not an unmade decision (it is only triggered if the
user's FPB recheck is unresolved at launch).

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

> **Provenance note (Playbook Entry 5).** v17 carried this section as a
> cross-reference to `BusinessCase_v16.md`'s full restored text rather
> than reproducing it. v16 is not among this revision's authorized
> inputs, so v18 restores a self-contained section rebuilt from every
> Market & Competition fact present in v17 itself, plus this cycle's
> funnel-unit correction. The decision-relevant figures (funnel,
> conversion, competitor pricing, demand-signal bounds) are all present
> below; v16's fuller narrative detail (population base derivation, OS
> split, international comparables) is not reproduced here and is
> flagged as such rather than reconstructed from memory — nothing below
> is invented to fill that gap.

**Market context.** South Africa, Android-first at launch. The gating
variable is parent digital-financial engagement: SARB reports 50.3% of
SA adults use banking apps regularly, adjusted to a [Guessing] 55-65%
for the economically-active parent cohort. Child device access is not
the gate: [Likely] 62% personal-device ownership by age 10, per a 2024
Stellenbosch-region study of five former Model C high schools (Grades
4-11) — a regionally and socioeconomically skewed sample, not nationally
representative.

**Reachable-market funnel — restated per-family this cycle.** The
funnel's unit is the FAMILY: one install-unit = one family account = one
potential subscription covering up to 4 children. Year-1 family-account
installs: 18,000-61,000 (the user's own labeled lowest-confidence
estimate, unchanged); front-loaded growth model (100 installs/day floor,
ramping; 15,000 installs in the first 90 days). Applying the documented
1-3% subscription-only conversion reference range (2% target):

- **Paying families, Year 1: 180 (18,000 × 1%) to 1,830 (61,000 × 3%).**
- Child users served: up to 4× the family counts (not revenue-bearing).

**Which prior range survives: 180-1,830.** The alternative 360-2,440
range cited in prior versions is retired: under the per-family unit and
the case's own documented 1-3% conversion benchmark, it is not derivable
from the funnel — its original derivation (not reconstructible from this
cycle's authorized inputs, but arithmetically consistent with having
applied a different conversion band and/or a per-child reading of some
funnel stage) does not survive the correction. All revenue statements in
this document use 180-1,830 paying families exclusively.

**Competition.** No direct South African incumbent runs MiniMoney's
payroll-simulation mechanic. Named landscape: **African Bank MyWORLD
Power Pocket** (adjacent-market offering from a banking incumbent;
detail as documented at v16, not reproduced among this cycle's inputs);
**MoneyAfrica Kids** (modest download volumes; premium price
unpublished — still an open item); **MoneyTime SA** (R995/year, 25%
sibling discount; self-published claims of larger B2B2C reach via
schools — the strongest demonstrated reach model in the category, per
`ResearchFindings_v1.md`). MiniMoney's annualized family price
(R719.88) undercuts MoneyTime SA's list rate even before the sibling
discount.

**What remains unresearched:** validated demand (n=10 bound still
governs; the pilot's demand read will be directional only); structured
market sizing beyond the user's own funnel estimate; MoneyAfrica Kids'
premium price; the schools-partnership channel's timeline, target, and
resourcing; international comparables detail (present in v16's text,
outside this cycle's inputs).

Status remains Partial: the competitive landscape and funnel are
documented and the unit ambiguity is resolved, but the most
decision-relevant figures (Year-1 adoption, conversion rate) remain the
user's own labeled lowest-confidence estimates, unvalidated.

## Business Model

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Subscription-only at launch, ads deferred to V2; **R59.99/month per
family, covering up to 4 children — the family is the revenue unit**
(resolved this cycle). MiniMoney is a facilitation/education layer that
sits on top of the parent's own bank account and does not move or hold
funds.

The core business-model uncertainty flagged since v8 — money-transmitter
licensing — remains resolved per `LegalOpinion_v1.md` Q1: risk is low,
contingent on Mbucks remaining strictly non-transferable and
non-redeemable, locked into the product spec (see Value Proposition,
Constraints).

Optional account-linking remains a trust/verification feature within the
existing subscription model. Its NCR question is resolved clean; the
SARB/NPS Act open-banking question remains genuinely unsettled — **and
now has an owner (the user personally), a timing trigger (build-spec
stage), and an explicit fallback: launch without account-linking**
(optional anyway; add later once the open-banking framework is
finalized). If pursued post-launch, advertising remains framed as a
partial CAC-offset lever, not a standalone revenue pillar.

The two residual items noted at v17 are both narrowed this cycle: the
FPB classification question now carries an explicit launch fallback
(launch without Mpoints — ripple effects traced in Legal & Compliance;
the cosmetic store, an engagement feature rather than a revenue line,
would be absent from that configuration, with unmodeled knock-on effects
on conversion/retention assumptions named in Risks); the Mpoints/Apple
IAP-currency question is narrowed in practical urgency by iOS deferral
and is mooted entirely under the no-Mpoints fallback. Status remains
Complete under the tightened definition: the model's structure, unit,
price, and every put-to-decision item within its scope are decided; the
remaining opens are externally-gated rechecks with owner and fallback.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Revenue (restated per-family this cycle).** Subscription revenue at
R59.99/month per family against the corrected Year-1 range of **180 to
1,830 paying families** (see Market & Competition for derivation and the
retirement of the 360-2,440 range):

- Lower bound: 180 families ≈ **R10,798/month** (≈ R129,578/year
  run-rate).
- Upper bound: 1,830 families ≈ **R109,782/month** (≈ R1,317,380/year
  run-rate).
- These are end-state run-rates against an unvalidated funnel and an
  unvalidated conversion rate; actual Year-1 collected revenue would be
  ramp-dependent and lower.

**Costs (supplied this cycle, `Clarifications_v18.md` change 7,
Verified-tier as to the user's commitment).**

- **Development budget: R10,000 total** committed for the app build.
- **Professional opinions/advice: zero marginal cost to the venture** —
  obtained through the user's existing policy (this also retroactively
  explains how the specialist legal opinion was obtained without the
  previously-scoped R25,000-R80,000 spend). The policy's scope and
  usage limits are not documented — a minor named open item.
- **Runway: 6 months** at current commitment before external funding is
  needed.

**Reconciliation against the prior agency reference range, stated
plainly:** the previously-cited $25,000-$120,000+ engineering-cost range
was a reference frame, not the plan — the solopreneur/AI-assisted build
model was always the stated approach. But the gap is now concrete:
R10,000 is roughly $550, i.e. 45× to 220× below the agency range's
bounds. The budget is only coherent because it prices in the founder's
own unpaid labor plus AI-assisted development, with the R10,000 covering
incidentals, tooling, and on-demand external help. **R10,000 buys days,
not months, of professional engineering if the founder's own capacity
fails — there is no buffer to purchase execution.** This is the case's
execution-capacity risk (see Risks, Constraints, Critical Gaps), and the
6-month runway — not the R10,000 — is the binding constraint.

**Still open:** no CAC estimate or marketing budget exists against the
18,000-61,000 family-install funnel (a material unmade element — the
funnel has no priced acquisition mechanism); curriculum content
production cost is unpriced (the workstream is committed, its cost is
not); no post-runway funding ask is sized. Status remains Partial: the
unit discrepancy is resolved and a real budget/runway now exists, but
the revenue side rests on unvalidated estimates and the cost side has no
acquisition or content-production figures. Per Playbook Entry 7, this
section is deliberately NOT raised to Complete on the momentum of this
cycle's resolutions — its own named opens (CAC, content cost, funding
ask) are untouched by them.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Core mechanics (budget and earning, task structure, completion/
verification/reporting flow, dispute mechanism, payment confirmation,
late-penalty parent-only design) are unchanged in structure. **The three
design decisions carried as pending in v17 are all now decided
(`Clarifications_v18.md`):**

- **Exam-period bonus — HYBRID redesign, user's own variant (decision
  1b), verbatim: "Reward behaviours while providing a Bonus for that
  translating into improved results. Rewards will still be given for the
  effort but bonus rewards for improved results."** The primary reward
  now targets controllable behaviors (effort: study time, homework
  completion), per the child-development review's recommendation; a
  secondary bonus layer contingent on improved results is retained.
  **Documented honestly as a partial adoption:** the behavior-primary
  structure follows the field evidence (Fryer's NBER experiments:
  rewarding inputs works, rewarding outputs doesn't), while the retained
  outcome-contingent bonus layer means the intrinsic-motivation risk
  identified by Deci, Koestner & Ryan (1999) is **reduced but not
  eliminated**. This is the user's deliberate design choice with a
  known, accepted residual risk — not full adoption of the
  recommendation, and not an oversight. Decided now, before any pilot
  family enrolls, satisfying the Investment Committee's sequencing
  condition at the decision level.
- **Late-penalty mitigation — grace-period/pre-escalation reminder
  mechanism ADDED (decision 1c).** The user chose the reviewer's first
  option (reduce trigger frequency at the source) over
  pilot-measurement-only; since the pilot-measurement package is ALSO
  adopted (decision 1f), both source-reduction and residual-tracking are
  now engaged. Design specifics (grace period length, reminder cadence)
  are build-spec parameters, not unmade decisions. Decided
  pre-enrollment, per the Committee's condition.
- **Fintech Advance content delivery — gamification-avoidance ADOPTED
  (decision 1d)** — see Value Proposition.

**New build-spec items introduced by the hybrid bonus, named:** the
mechanism for logging/verifying the behavior inputs (study sessions,
homework completion) and the grade-input mechanism for the retained
results-bonus layer (already an open Technology item) both need
specification at build time.

**Known operational gap, tracked:** dispute-escalation beyond the
48-hour window has no formal resolution mechanism — an explicitly
tracked build-spec/edge-case design item since early versions (see
Outstanding Questions), never put to a decision by any reviewing body,
and not a specialist recommendation awaiting adoption.

Status remains Complete under this cycle's tightened definition — and
now earns it on stricter terms than v17: every specialist recommendation
within this section's scope has a recorded decision (two adopted as
recommended, one adopted as a documented hybrid with accepted residual
risk); remaining opens are build-spec parameters and a tracked edge-case
mechanism, not undecided recommendations. Evidence remains Supported for
the section as a whole: the underlying mechanics are Supported-tier from
prior clarifications; this cycle's three decisions are themselves
Verified-tier as to what was decided.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in status from v17, with one addition. Still unspecified: how
account-linking is technically initiated; how payment confirmation is
captured beyond the accept/dispute UI; the exam-bonus grade-input
mechanism (retained — the hybrid's secondary results-bonus layer still
requires it). **Added this cycle:** the hybrid bonus's behavior-input
mechanism (how study time / homework completion is logged and verified)
is a new unspecified item introduced by decision 1b; and the committed
grace-period/reminder mechanism (decision 1c) requires notification
infrastructure whose parameters are build-spec details. Status remains
Partial.

## Legal & Compliance ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The retained specialist legal opinion (`LegalOpinion_v1.md`, v17 cycle)
remains the Verified-tier foundation of this section — all seven
originally-scoped questions answered. Summarized here in full,
self-contained form, with this cycle's ownership/fallback decisions
integrated:

**1. Money-transmitter/payment-facilitation risk: low, contingent on a
locked product-spec constraint.** The relevant perimeter is the National
Payment System Act 78 of 1998 (s1); SARB/PASA's joint communication
distinguishes systems that actually move/circulate money from ancillary
information/calculation layers — MiniMoney's invoice→payslip mechanic is
closer to the latter. [Likely] This holds only as long as Mbucks cannot
be spent, transferred, or redeemed anywhere other than through the
parent's independent banking-app payment — confirmed [Certain] against
SARB's e-money Position Paper (e-money issuance is restricted to
registered banks). Courts look at substance, not labels (*Maize Board v
Jackson* 2005 (6) SA 592 (SCA)). This is an ongoing product-spec
constraint (see Value Proposition, Constraints). The NCR's Payment
Distribution Agent category is confirmed inapplicable.

**2. Universal parental-consent gate: legally sufficient as designed,
with two hardening recommendations.** POPIA s34/s35(1)(a) is satisfied
by the current universal, no-carve-out consent gate. [Certain as to the
statute] Two hardening recommendations, not yet built: (a) consent-flow
documentation separating data-processing consent from general
T&Cs/subscription terms; (b) a lightweight parent identity-verification
step. Both are named build tasks (Roadmap).

**3. POPIA Section 14 retention:** confirmed [Certain] no minor-specific
supplementary rule exists; a specific retention purpose, period, and
deletion trigger must be affirmatively designed and documented — a named
build requirement (Roadmap, Outstanding Questions), not a resolved legal
question.

**4. Minor contractual capacity: the case's strongest legal position.**
The "rights without obligations" minor-contract exception fits
MiniMoney's structure (child receives a benefit, bears no enforceable
payment obligation), with the parent's obligation better characterized
as a unilateral undertaking or conditional donation — sidestepping the
domestic-agreement-presumption question via animus contrahendi doctrine
(*Pitout v North Cape Livestock* 1977). [Certain as to the doctrines
cited] **One supporting citation — the Conradie v Rossouw pinpoint
reference — is flagged by the expert as unverified. Per this cycle's
decision (change 4), verification goes back to the retained lawyer
directly as an external action: PENDING, carried as a named open item,
not blocking any other item, but required before any public or filed use
of the opinion.**

**5. Terminology risk: real, the single highest-optics-risk item in the
case — mitigation now ADOPTED (decision 1a).** ARB Code Clause 14.2
(children's advertising) and Clause 6.1, Section III (financial
products) are both engaged, plus a Consumer Protection Act secondary
layer (s3, ss29/41); no ARB ruling addresses this fact pattern, so
MiniMoney would be a natural first test case if challenged. The
recommended mitigation is now decided: debt-coded terminology
("invoice," "arrears," "late penalty") is reserved for parent-facing
surfaces only; child-facing surfaces never carry it. Implementation is a
build task; the decision is made.

**6. SARB/NPS Act open-banking question (account-linking) — owned,
timed, with fallback (this cycle, change 3).** NCR registration is
confirmed inapplicable [Certain]; the SARB question (Draft Directive,
early 2025; Draft Exemption Notice under the Banks Act) remains
genuinely unsettled. **Recheck owner: the user personally. Timing:
build-spec stage** (the same trigger as the original legal-opinion
commissioning: once a stable working model exists, before pilot testing
with real families). **Fallback, decided: if unresolved by launch,
launch WITHOUT account-linking** — the feature is optional, and is added
later once the open-banking framework finalizes. Ripple effects of this
fallback are modest and already documented: account-linking is also the
recommended natural integration point for the parent
identity-verification step (Q2 above), so a no-linking launch must
implement that verification by another route (e.g., card
micro-authorization) — named in Roadmap.

**7. FPB classification question (Mpoints) — owned, timed, with fallback
and a full ripple-effect trace (this cycle, change 3).** The Films and
Publications Amendment Act 11 of 2019 gives the FPB a classification
mandate over "interactive computer games"; whether the Mpoints reward
mechanic (badges, cosmetic rewards, task-completion mechanics) is caught
is genuinely fact-specific. [Certain as to the Act; Likely, not Certain,
as to applicability] **Recheck owner: the user personally. Timing:
build-spec stage. Fallback, decided: if unresolved by launch, launch
WITHOUT Mpoints** — the user accepts shipping without the
cosmetic-rewards gamification loop rather than shipping it unclassified,
consistent with the Investment Committee's escalation of this item above
the account-linking question.

**No-Mpoints launch configuration — ripple-effect trace (per Playbook
Entry 2, a real dependency check, not a footnote):**

- **In-app cosmetic store: removed from the fallback configuration.**
  Mpoints is the store's only currency; with no Mpoints there is nothing
  to spend. The store cannot ship visible-but-unusable, and shipping it
  dormant-but-present would still surface the loyalty-point and
  classification questions in platform/regulatory review — so the
  fallback build excludes it. Because the store is part of the
  child-facing subscription feature set, the Free/Subscription feature
  table needs a fallback variant, and the subscription's child-facing
  appeal is thinner in that configuration — an unmodeled effect on
  conversion/retention assumptions, named in Risks.
- **Flat 10-Mpoints-per-task reward: gone.** Every completed task then
  yields only Mbucks accruing to a weekly payslip — the immediate,
  non-monetary per-task feedback layer disappears. This matters most for
  the 6-9 curriculum tier, whose adopted framing (task/reward, delayed
  gratification, "family task rewards" — decision 1e) leans on immediate
  reinforcement. A no-Mpoints build either needs a replacement
  immediate-feedback mechanism that is not a reward currency (avoiding
  re-triggering the same FPB question), or accepts a weaker young-tier
  loop. Named as a conditional design item (Outstanding Questions).
- **Google Play Families Policy loyalty-point disclosure item: mooted in
  the fallback configuration** (no loyalty-point-like mechanic to
  disclose); remains open for the primary configuration. The Apple Kids
  Category IAP-currency question is likewise mooted under the fallback
  and already deferred with iOS.
- **Fintech Advance gamification-avoidance (decision 1d): trivially
  satisfied** under the fallback (no Mpoints anywhere).
- **Residual check, named:** v17 refers to "Mpoints/badge" gamification
  together; whether badges are Mpoints-dependent or a separate mechanic
  is unspecified. If separate, badges alone could still raise the FPB
  game-likeness question in reduced form — the user's FPB recheck should
  confirm whether the residual task-completion/badge mechanics are
  independently classifiable, so the fallback actually closes the
  exposure it exists to close.

**Status remains Complete.** All seven originally-scoped questions are
answered at Verified tier; the two unsettled external regulatory
questions are not gaps in the legal analysis but pending external
rechecks — each now with a named owner (the user), a timing trigger
(build-spec stage), and a decided launch fallback whose consequences are
traced above. The one unverified citation is a named, pending external
action with the retained lawyer.

## Risks

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

All previously-identified risk categories remain catalogued; decision
status is updated per `Clarifications_v18.md`, and one new risk is
named.

- **Regulatory risk:** core invoice/payment-trigger/late-penalty
  mechanic assessed low-risk by retained counsel, contingent on the
  Mbucks non-transferability constraint. Two narrower open regulatory
  questions — SARB/NPS Act (account-linking) and FPB (Mpoints) — now
  each carry a named owner (the user), a build-spec-stage timing
  trigger, and a decided launch fallback (launch without the affected
  feature). Residual: the questions themselves remain externally
  unsettled until the rechecks run.
- **Execution-capacity risk (NEW this cycle — named plainly, per change
  7):** a solopreneur venture with a R10,000 total development budget
  (~$550; 45×-220× below the agency reference range it was previously
  benchmarked against), a ~3-month directional build timeline, a
  parallel curriculum-authoring workstream starting now, an instrumented
  20-50 family pilot, and two personally-owned regulatory rechecks — all
  inside a 6-month runway, executed substantially by one person, with no
  cash buffer to purchase external engineering if founder capacity
  fails. Slippage in any single workstream consumes runway directly, and
  the funding need arrives (~month 6) when the strongest available
  demand evidence will still be directional pilot data. This is the
  binding constraint on the case as now stated.
- **Child-safety/data-privacy risk:** consent model confirmed legally
  sufficient as designed; two hardening recommendations (consent-flow
  separation; lightweight parent verification) remain build tasks, not
  yet built. POPIA Section 14 retention policy remains an affirmative
  design requirement, not yet done.
- **Minor-contractual-capacity risk:** substantially resolved (rights-
  without-obligations doctrine); one supporting citation (Conradie v
  Rossouw) pending pinpoint verification with the retained lawyer.
- **Terminology/perception risk — mitigation DECIDED (1a):** confirmed
  real and the single highest-optics-risk item (ARB Clauses 14.2 and
  6.1, CPA secondary layer); parent-facing-only debt terminology is now
  adopted; implementation is a build task.
- **Late-penalty/relationship risk — both mitigation paths now engaged
  (1c, 1f):** the Family Stress Model's affective pathway persists
  despite child-invisibility; risk narrowed, not eliminated. The
  grace-period/pre-escalation reminder mechanism is committed
  (source-reduction) AND the specialist pilot-measurement package is
  adopted (residual tracking). Residual risk remains real and is now
  actively mitigated and measured rather than pending decision.
- **Exam-bonus/intrinsic-motivation risk — DECIDED as a hybrid with
  accepted residual (1b):** the behavior-primary redesign follows the
  evidence (Fryer: inputs over outputs); the retained outcome-contingent
  bonus layer means the Deci/Koestner/Ryan crowding-out risk is reduced,
  not eliminated — a deliberate, known-residual-risk user choice. The
  adopted pilot instruments do not formally measure motivation effects
  (they target family stress); this residual is accepted and
  qualitatively observable in pilot, not instrumented.
- **Fintech Advance content risk — mitigation ADOPTED (1d):** the module
  avoids the product's own gamification and leans to risk-literacy
  framing, addressing the normalization-of-speculative-risk concern.
- **Age-appropriateness/terminology-uniformity risk — framework ADOPTED
  (1e):** the three-tier curriculum framing is adopted; reconciliation
  with the product's existing six-way sub-bands (6, 7, 8, 9-10, 11-14,
  15-18) is still to be done, and no instructional content yet exists
  behind the framework.
- **No-Mpoints fallback ripple risk (NEW this cycle):** if the FPB
  fallback triggers, the launch configuration loses the cosmetic store
  and the per-task Mpoints reward — thinning child-facing subscription
  appeal and weakening the 6-9 tier's immediate-feedback loop, with
  unmodeled effects on the 2% conversion target and retention
  assumptions. Traced in full in Legal & Compliance; conditional, not
  active.
- **Dispute-escalation risk:** unchanged — no formal resolution
  mechanism beyond the 48-hour window; a tracked build-spec design item.
- **Adoption/forecasting risk:** unchanged in kind — the funnel unit is
  now resolved (per-family) and the surviving range is 180-1,830 paying
  families, but the underlying install and conversion estimates remain
  the user's own lowest-confidence, unvalidated figures; the pilot's
  demand read will be directional only.
- **Competitive risk; monetization-execution risk; app-store policy
  risk; platform-concentration risk:** unchanged in substance; the
  Google Play loyalty-disclosure item is mooted under the no-Mpoints
  fallback but open in the primary configuration.
- **Engineering-cost estimation risk:** superseded — subsumed into the
  execution-capacity risk above now that the actual budget (R10,000) is
  stated; retained here for audit-trail continuity.
- **Legal-opinion-deferral risk:** RESOLVED at v17; retained for
  audit-trail continuity.

Status remains Complete under this cycle's tightened definition, now on
stricter terms: the risk landscape is comprehensively identified and
characterized, and — unlike v17 — every specialist-recommended
mitigation within it carries a recorded decision (adopted, or adopted-
as-hybrid with explicitly accepted residual). A Complete risk register
does not mean the risks are eliminated: the execution-capacity risk, the
two external regulatory questions, and the accepted exam-bonus residual
are all live, and are stated as such.

## Assumptions

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Carried forward: parent-direct payment; SA launch jurisdiction;
universal consent gate; Android-first; Mbucks/Mpoints dual currency;
7-Mbuck late-penalty cap with 3-Mbuck pilot cap; the fixed
Mbucks-to-Rand peg; the late-penalty mechanic as a parent-only
administrative matter; exam-bonus grade data self-reported/
parent-entered; primarily a South African B2C product at launch.

**Updated this cycle:**

- **The exam-bonus risk-acceptance is now settled** (was a live open
  decision at v17): the user has decided the hybrid design (1b) in full
  knowledge of the specialist evidence, deliberately retaining a
  reduced outcome-contingent layer. The residual intrinsic-motivation
  risk is now an explicit, accepted assumption — that the secondary
  bonus's salience will not dominate the behavior-primary structure in
  the child's perception. Untested; observable in pilot.
- **The funnel-unit assumption is resolved**: per-family throughout; the
  average-children-per-family distribution within the up-to-4 cap
  remains unknown (affects usage load and curriculum exposure, not
  revenue).
- **New assumption (change 7):** the user's policy covering professional
  opinions at zero marginal cost will continue to cover the future
  engagements this case anticipates (citation verification follow-up,
  possible recheck support). Its scope/limits are undocumented —
  Assumed.
- Mbucks non-transferability/non-redeemability and the SARB/NPS Act
  contingency remain as documented constraints rather than assumptions
  (see Constraints).

Status remains Partial: the list is more settled than v17 (the one live
undecided acceptance is now decided), but it remains a working inventory
with untested load-bearing assumptions (conversion rate, funnel size,
policy coverage, bonus-salience), not a closed set.

## Constraints

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

- Solopreneur venture; AI-assisted development; external technical
  expertise engaged only on-demand; directional ~3-month build timeline;
  Android primary, iOS deferred.
- **Mbucks non-transferability/non-redeemability** — binding product-spec
  constraint on all future roadmap decisions (`LegalOpinion_v1.md` Q1).
- **NEW (this cycle, user-verbatim, change 7): R10,000 total development
  budget; 6-month runway before external funding is needed; professional
  opinions at zero marginal cost via the user's existing policy.** The
  runway, not the cash budget, is the binding constraint: it must
  contain the build, the parallel curriculum workstream, the
  instrumented pilot, and both user-owned regulatory rechecks.
- **Launch-configuration constraints (decided fallbacks, change 3):**
  the product must be buildable in three configurations — full; without
  account-linking (SARB unresolved); without Mpoints (FPB unresolved) —
  and the no-Mpoints configuration excludes the cosmetic store and
  per-task Mpoints reward (see Legal & Compliance ripple trace).

Status remains Complete. Confidence is raised Medium→High and Evidence
Supported→Verified this cycle (per Playbook Entry 3, stated rather than
silent): the constraint set previously rested on general characterization
of the venture's resourcing; it now rests on the user's direct, verbatim
commitments (budget, runway, policy, fallbacks). Per Playbook Entry 4:
this is a clearer picture, not better news — the newly-verified
constraints are tight, and they ground the new execution-capacity risk.

## Roadmap

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Now (parallel with build, starting immediately — change 5):** the
curriculum-content workstream (authorship, instructional format,
standards alignment) runs alongside engineering, not after it. (An
Incubator-drafted candidate, `CurriculumDraft_v1.md`, exists from an
earlier prep task; it is unreviewed/unadopted by the user and was not an
input to this revision — available as a starting point only.)

**Build phase:** implement core loop with this cycle's decided designs —
parent-facing-only debt terminology (1a); hybrid exam bonus (1b);
grace-period/pre-escalation reminders (1c); Fintech Advance without
product gamification (1d); three-tier curriculum framing (1e), including
its reconciliation with the six-way sub-bands. Legal build tasks: POPIA
s14 retention period and deletion trigger design; consent-flow
documentation separating data-processing consent from T&Cs; lightweight
parent identity-verification step (with a non-account-linking route
available, since the linking feature may not ship at launch).

**Build-spec stage (trigger: stable working model exists, before pilot
families enroll):** the user personally runs both regulatory rechecks —
SARB/NPS Act (account-linking) and FPB (Mpoints, including the
badge-residual check). Decided fallbacks if unresolved by launch: ship
without account-linking; ship without Mpoints (cosmetic store and
per-task Mpoints reward excluded; feature-table fallback variant and
6-9-tier feedback replacement per the Legal & Compliance ripple trace).
In parallel, the retained lawyer verifies the Conradie v Rossouw
pinpoint citation (external action, pending).

**Pilot (20-50 families):** double-duty per this cycle's decision —
mechanic safety/child-development signal AND directional demand read —
with the adopted measurement package (PSI-SF/FAD-GFS borrowed items,
within-family correlation tracking, age-stratified results, child-report
instrument) built into the pilot design before enrollment. Items 1b and
1c were decided before enrollment, satisfying the Committee's sequencing
condition. Recruitment design must serve both goals (see Validation
Strategy).

**Post-pilot (~month 6): external funding is needed** — the runway ends
here; a funding ask is not yet sized (Outstanding Questions).

**Growth (6-12 months):** conversion validation against the 1-3% range;
curriculum-engagement-as-retention-indicator validation; iOS port timing
evaluation; account-linking and/or Mpoints re-introduction as their
regulatory questions resolve; schools-partnership channel exploration
(still unplanned — no timeline, target, or resourcing).

Status remains Complete under the tightened definition, on stricter
terms than v17: every pre-pilot decision the roadmap listed as pending
is now made; remaining opens are owned external rechecks with decided
fallbacks, build-spec parameters, and a post-runway funding ask that is
named as unsized rather than silently absent.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**What now exists (this cycle, change 7 — the section's first real
financial content):**

- **Budget: R10,000 total** for development (user-verbatim commitment).
- **Professional advice: zero marginal cost** via the user's existing
  policy (scope/limits undocumented — Assumed).
- **Runway: 6 months** before external funding is needed.
- **Revenue model (per-family, corrected this cycle):** R59.99/month per
  family against a Year-1 range of 180-1,830 paying families —
  R10,798-R109,782/month run-rate at the range bounds; ramp-dependent
  actuals lower. The 360-2,440 subscriber range is retired (see Market &
  Competition).

**The reconciliation, stated as the Investment Committee would want it:**
R10,000 (~$550) against the previously-cited $25,000-$120,000+ agency
range is a 45×-220× gap. The number is coherent only as a
founder-labor-plus-AI-assisted build with cash covering incidentals,
tooling, and small on-demand help — it is not a budget that can buy a
build, or buy rescue if the founder's own capacity fails. **The 6-month
runway is the binding constraint**: build (~3 months, directional),
parallel curriculum authoring, instrumented pilot, and two user-owned
regulatory rechecks must all complete inside it, after which funding is
needed with — at best — directional pilot evidence to raise on. This is
the case's execution-capacity risk (Risks; Critical Gaps).

**Still absent, named:** CAC estimate or any marketing budget against
the 18,000-61,000 family-install funnel; curriculum content production
cost; the size and form of the post-runway funding ask; full financial
projections (P&L, break-even — at R59.99/family/month, the R10,000
budget is recouped at trivial subscriber counts, but no break-even
analysis including acquisition and operating costs exists). Status
remains Partial: the section has moved from "no financial content at
all" (v16/v17) to a real budget, runway, and corrected revenue range —
but the acquisition economics and funding plan that would complete it do
not yet exist. Per Playbook Entry 7, not raised on momentum.

## Validation Strategy

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Closed streams:** legal validation (retained opinion, Verified-tier,
v17); child-development/age-appropriateness validation (retained review,
Verified-tier, v17); all six resulting design recommendations now
carry decisions (this cycle).

**Pilot — scope DECIDED this cycle (change 6): double duty.** The 20-50
family pilot will validate BOTH mechanic safety/child-development signal
AND market demand — the user's explicit choice, made knowing the
child-development reviewer's stated caution that a cohort this size is
statistically underpowered. **Documented with the caveat attached, not
smoothed over: demand findings from this pilot will be directional and
qualitative, not statistically validated.** The safety instrumentation
is the adopted specialist package (Success Criteria). The demand
dimension imposes a real recruitment-design requirement, named here:
recruiting only warm, pre-enthusiastic contacts would inflate the demand
read to uselessness while remaining adequate for safety measurement —
recruitment must reach beyond the founder's existing network for the
demand signal to carry even directional weight, and the pilot's demand
findings inherit the same standing instruction as the n=10 interviews:
directional input, never a validated demand signal.

**Still open:** pricing/conversion validation (price known; the 2%
target and 1-3% range remain unvalidated by any study — the pilot may
inform willingness-to-pay directionally but is not a conversion test);
curriculum validation (no content yet exists to validate; the parallel
workstream must produce content before any engagement validation is
possible); account-linking UX/consent-flow validation (feature gated on
the SARB recheck; flow not yet designed); the no-Mpoints fallback
configuration, if triggered, has no validation plan for its thinner
engagement loop.

Status remains Partial: the pilot is now fully scoped and instrumented
at the decision level — a real advance — but market demand and
pricing/conversion still have no statistically meaningful validation
scheduled anywhere in the plan, by explicit, documented user choice.

## Supporting Evidence

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Verified-tier:** `LegalOpinion_v1.md` and `ChildDevelopmentReview_v1.md`
(retained professionals; reviewed and approved their own final
documents); the user's direct clarification history — `Clarifications_v6.md`
through `v14.md` and now **`Clarifications_v18.md`** (Verified-tier as
to what was decided: all six design decisions, the per-family funnel
unit, recheck ownership/timing/fallbacks, pilot scope, and the
budget/runway figures, several verbatim).

**Supported-tier:** three Research House engagements
(`ResearchFindings_v1-3.md`, desk research; capped at Supported per this
case's evidence rules); the user's directly-cited South African
statutory/statistical sources.

**Bounded first-party data:** the n=10 interview round —
non-representative, governed by the standing instruction (never a
validated demand signal); the same rule now extends explicitly to the
pilot's directional demand findings.

**Known evidence-chain limitation, named:** `BusinessCase_v16.md`'s full
Market & Competition narrative was not among this cycle's authorized
inputs; that section's v18 text is rebuilt from v17-visible facts and
flags what it does not reproduce (see its provenance note). One legal
citation (Conradie v Rossouw) remains unverified pending the retained
lawyer's pinpoint check.

Status remains Complete: the evidentiary base spans Verified-tier user
decisions and retained-professional opinions through Supported-tier desk
research to bounded first-party data, with each tier's limits stated.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this cycle (retained for audit-trail continuity):** all six
specialist design recommendations — terminology (1a, adopted), exam
bonus (1b, hybrid with accepted residual), late-penalty grace mechanism
(1c, committed), Fintech Advance gamification-avoidance (1d, adopted),
three-tier curriculum framework (1e, adopted), pilot-measurement package
(1f, adopted); the subscriber-count discrepancy and family-vs-child
install ambiguity (per-family unit; 180-1,830 survives, 360-2,440
retired); regulatory-recheck ownership, timing, and launch fallbacks
(user; build-spec stage; without-linking / without-Mpoints); pilot
validation scope (double duty, underpowered-for-demand caveat attached);
cost/runway (R10,000; zero-marginal-cost opinions; 6 months).

**Open — external actions in flight:** Conradie v Rossouw pinpoint
citation verification (with the retained lawyer; required before any
public/filed use of the legal opinion); SARB/NPS Act recheck and FPB
applicability recheck (user-owned, build-spec stage; fallbacks decided —
including the badge-residual check within the FPB recheck).

**Open — design/build tasks, named owner is the build itself:** POPIA
s14 retention period and deletion trigger; consent-flow documentation
separation; lightweight parent identity-verification (with a
non-account-linking route); grace-period length and reminder cadence
(build-spec parameters, 1c); behavior-input logging/verification and
grade-input mechanisms for the hybrid bonus (1b); the no-Mpoints
fallback's feature-table variant and 6-9-tier immediate-feedback
replacement (conditional); dispute-escalation mechanism beyond the
48-hour window; the "request for payment" prompt feature's coherence
under the child-invisible late-penalty model; account-linking opt-in UX
flow (if/when the feature ships); task verification mechanics.

**Open — analytical/planning gaps:** three-tier curriculum framework
reconciliation with the six-way sub-bands (6, 7, 8, 9-10, 11-14, 15-18);
curriculum instructional format, standards alignment, and content
authorship (workstream committed and starting, content nonexistent);
curriculum-engagement (30%), operational-health (65%), and retention
benchmarks (placeholders; retention has no figure); CAC estimate and
marketing budget; curriculum content production cost; post-runway
funding ask size and form; whether pilot instrumentation should add any
lightweight motivation observation for the exam-bonus residual (accepted
risk, currently uninstrumented); the schools-partnership channel's
timeline/target/resourcing; MoneyAfrica Kids' unpublished premium price;
South Africa-specific vendor pricing for Stitch's or Mono's product; the
user's advice-policy scope/limits.

Status remains Complete: this register's scope is comprehensive
identification and tracking, and every item above carries its
disposition (in flight, build task, conditional, or named gap) — none is
an undecided recommendation awaiting a user decision.

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**What "Complete" means in this rubric — stated once, here, per the
Investment Committee's Gate Integrity observation, and applied
consistently throughout this document:** a section is **Complete** when
every material question within its scope has a *made decision* — 
resolved, adopted, or a deliberate, documented residual-risk
acceptance — and anything still open is a tracked implementation detail,
build-spec parameter, or externally-gated recheck carrying a named owner
and (where launch-relevant) a decided fallback. A section carrying an
undecided specialist recommendation or an unmade material decision is
**Partial**, regardless of how thoroughly those open items are
documented: *documentation of an open decision is not resolution of it.*
For register-type sections (Risks, Outstanding Questions), Complete
means comprehensive identification with a recorded disposition per item,
since tracking — not elimination — is those sections' scope. Under this
definition, v17's Operations, Risks, and Roadmap — Complete while
carrying six undecided specialist recommendations — would have been
Partial; they are Complete in v18 because `Clarifications_v18.md`
resolved those decisions, which is exactly the tension the Committee's
observation identified and this cycle's user decisions largely dissolve.

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted. Recomputed in full
against this cycle's document and the definition above.

| Section | Status | Weight | Points |
| - | - | - | - |
| Executive Summary | Partial | 1x | 2 |
| Problem | Partial | 1x | 2 |
| Opportunity | Partial | 1x | 2 |
| Objectives | Complete | 1x | 5 |
| Success Criteria | Partial | 1x | 2 |
| Stakeholders | Partial | 1x | 2 |
| Target Users/Customers | Partial | 1x | 2 |
| Value Proposition | Complete | 1x | 5 |
| Market & Competition | Partial | 1x | 2 |
| Business Model | Complete | 1x | 5 |
| Revenue & Costs | Partial | 1x | 2 |
| Operations | Complete | 1x | 5 |
| Technology | Partial | 1x | 2 |
| Legal & Compliance ★ | Complete | 2x | 10 |
| Risks | Complete | 1x | 5 |
| Assumptions | Partial | 1x | 2 |
| Constraints | Complete | 1x | 5 |
| Roadmap | Complete | 1x | 5 |
| Financial Considerations | Partial | 1x | 2 |
| Validation Strategy | Partial | 1x | 2 |
| Supporting Evidence | Complete | 1x | 5 |
| Outstanding Questions | Complete | 1x | 5 |
| Curriculum Design (extension) | Partial | 1x | 2 |
| Child Data & Consent (extension) ★ | Complete | 2x | 10 |

Points earned: **91**.

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130.**

**Readiness Score = 91 / 130 = 70.0%.** Clears the completion gate's
≥70% threshold, with no margin.

No section is Critical + Incomplete: both Legal & Compliance and Child
Data & Consent are Complete.

**Why the score is unchanged from v17 despite all seven required changes
being resolved (stated explicitly per Playbook Entry 1):** the
Committee's changes were predominantly decisions and reconciliations,
not new information closing Partial sections' own gaps. Under the
tightened Complete definition above, three of v17's Complete sections
(Operations, Risks, Roadmap) only retain Complete *because* this cycle's
decisions were made — the definitional tightening and the decisions
offset. Meanwhile the sections that remain Partial (Revenue & Costs,
Financial Considerations, Validation Strategy, Success Criteria, and
others) were strengthened but not completed: their independent gaps —
CAC and acquisition economics, unbenchmarked success criteria,
statistically meaningful demand validation, curriculum content — were
not addressed by, and were outside the scope of, the seven changes. The
case is materially more decided than v17; the flat score is rubric
integrity, not ignored feedback. Per Playbook Entry 3, no section's
Confidence declined this cycle; one (Constraints) rose Medium→High on
direct user-verified commitments — a clearer picture whose content
(tight budget, hard runway) is less comfortable, not more (Playbook
Entry 4).

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
52% (v13) → 52% (v14) → 52% (v15) → 52% (v16) → 70% (v17) → **70%
(v18) — flat by offset: definitional tightening of "Complete" absorbed
by this cycle's seven resolved changes.**

### Critical Gaps

1. **Execution capacity (Financial Considerations, Constraints, Risks) —
   newly named this cycle.** R10,000 total development budget (~$550;
   45×-220× below the agency reference range) plus a 6-month runway must
   contain the build (~3 months directional), a parallel
   curriculum-authoring workstream, an instrumented 20-50 family pilot,
   and two user-owned regulatory rechecks — executed substantially by
   one person, with no cash buffer to purchase execution if founder
   capacity fails, and a funding need at ~month 6 backed by directional
   evidence only. The binding constraint on the case as now stated.
2. **SARB/National Payment System Act open-banking question (Legal &
   Compliance, Business Model, Roadmap) — owned and fallback-protected,
   still externally unsettled.** Owner: the user, at build-spec stage;
   decided fallback: launch without account-linking. The question itself
   remains open pending finalized regulation.
3. **FPB classification question over Mpoints (Legal & Compliance,
   Risks, Value Proposition) — owned and fallback-protected, still
   externally unsettled, with traced ripple effects.** Owner: the user,
   at build-spec stage; decided fallback: launch without Mpoints — which
   removes the cosmetic store and per-task Mpoints reward, thins
   child-facing subscription appeal, weakens the 6-9 tier's
   immediate-feedback loop, and moots the Google Play loyalty-disclosure
   item for that configuration. Badge-residual classifiability must be
   checked within the recheck.
4. **Market demand remains directionally evidenced only (Problem,
   Validation Strategy).** The n=10 standing instruction holds; the
   pilot's demand read (double-duty by explicit user choice, made
   knowing the cohort is statistically underpowered) will be
   directional/qualitative, not validated. No statistically meaningful
   demand or conversion study is scheduled anywhere in the plan.
5. **Success-criteria benchmarks remain placeholders (Success
   Criteria).** Curriculum engagement (30%) and operational health (65%)
   carry no external benchmark; retention has no proposed figure at all.
6. **Curriculum content does not yet exist (Curriculum Design,
   Roadmap).** The three-tier framework is adopted and the parallel
   workstream is committed starting now, but instructional format,
   standards alignment, and authorship are unspecified, and the
   three-tier/six-sub-band reconciliation is not yet done.
7. **Legal build tasks pending (Legal & Compliance, Child Data &
   Consent, Roadmap):** POPIA s14 retention period and deletion trigger;
   consent-flow documentation separation; lightweight parent
   identity-verification (needing a non-account-linking route).
8. **Conradie v Rossouw pinpoint citation verification (Legal &
   Compliance) — external action pending with the retained lawyer;**
   required before any public or filed use of the legal opinion.
9. **Exam-bonus residual risk — accepted, uninstrumented (Operations,
   Risks, Success Criteria).** The hybrid's retained outcome-contingent
   bonus layer carries a reduced-but-real intrinsic-motivation risk, by
   deliberate user choice; the adopted pilot instruments measure family
   stress, not motivation.
10. **Resolved this cycle, retained for audit-trail continuity:** all
    six specialist design decisions; the subscriber-count discrepancy
    and family-vs-child ambiguity (per-family; 180-1,830 survives);
    recheck ownership/timing/fallbacks; pilot scope; cost/runway.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** High | **Evidence:** Verified

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs.*

Carried forward: the age floor of 6 is intentional; the curriculum is a
short course completable daily or weekly, not a full year; two example
mechanics (currency differentiation; "word sums" for change/remainder
calculation); "Fintech Advance" as the distinct 15-18-only element (now
decided to avoid the product's own gamification and lean risk-literacy —
decision 1d).

**Three-tier age framework — ADOPTED this cycle (decision 1e).** Per
`ChildDevelopmentReview_v1.md` Q1/Q3 (risk inflection at age 10-11 —
institutional understanding of financial systems, per Jahoda 1981/Ng
1983 — not a linear younger-is-worse gradient):

- **Early childhood (roughly 6-9):** softened task/reward and delayed
  gratification framing — closer to "family task rewards" than "wages."
- **Pre-teen (roughly 10-14):** basic transactional literacy.
- **Teens (roughly 15-18):** pre-employment literacy, where the payroll
  framing (payslip, deductions, punctuality) is arguably a genuine
  feature — rehearsal for a near-future reality.

This framework also gives the adopted parent-facing-only terminology
decision (1a) an age-specific implementation path. **Workstream timing
DECIDED (change 5): curriculum content authoring runs in parallel with
the engineering build, starting now** — not after it.
`CurriculumDraft_v1.md` exists as Incubator-drafted candidate content
from an earlier prep task; the user has not reviewed or adopted it; it
was not an input to this revision and is available only as a starting
point.

**Still open:** instructional format, standards alignment, and content
authorship (the workstream exists; its outputs do not); reconciliation
of the three-tier framework with the product's existing six-way
stakeholder sub-bands (6, 7, 8, 9-10, 11-14, 15-18) — flagged by the
Investment Committee as not yet done, and still not done; the
conditional 6-9-tier immediate-feedback replacement under the no-Mpoints
fallback (see Legal & Compliance). The 30% curriculum-engagement
success benchmark remains unbenchmarked.

Status remains Partial: the framework and workstream timing are decided,
but the section's core deliverable — actual instructional content — does
not yet exist, and a named reconciliation task is outstanding.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Directly and substantially addressed by `LegalOpinion_v1.md` Q2 and Q3
(v17 cycle); unchanged in legal substance this cycle, with fallback
interactions integrated. The universal parent-consent gate (no minor
accesses any part of the app without a pre-existing, consenting parent
account) is confirmed **legally sufficient as designed** under POPIA
s34/s35(1)(a) — a direct legal confirmation, not an inference. Two
hardening recommendations are named build tasks (Roadmap): consent-flow
documentation separating data-processing consent from general
T&Cs/subscription terms; and a lightweight parent identity-verification
step — noting this cycle that its recommended natural integration point
(account-linking) may not ship at launch under the SARB fallback, so a
non-linking verification route (e.g., card micro-authorization) must be
designed.

POPIA Section 14 retention is confirmed to require an affirmatively
designed, specific retention period and deletion trigger — a named,
pending build task, not a closed legal question.

**Platform-policy items, updated for this cycle's fallback decisions:**
Google Play's Families Policy loyalty-point disclosure requirement
applies to the primary (Mpoints-included) configuration and is **mooted
under the no-Mpoints fallback**; Apple's Kids Category IAP-currency
question is deferred with iOS and likewise mooted under that fallback.
Both remain open for the primary configuration. The FPB classification
question sits adjacent to, but formally distinct from, this section's
POPIA/consent focus and is tracked in Legal & Compliance with its owned
recheck and fallback. Whether Fintech Advance's conceptual content
requires additional disclosure beyond general POPIA/ARB considerations
remains open but narrowed (the primary risk identified is
speculative-risk normalization — now mitigated by decision 1d — not a
data-privacy or consent question).

Status remains Complete under the tightened definition: the section's
central questions — consent-model sufficiency and retention approach —
are directly answered by retained counsel; remaining opens are named
build tasks and configuration-dependent platform-policy items with
decided fallbacks, not undecided recommendations or unresolved legal
uncertainty about the design as it stands.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Complete.
- Readiness Score ≥ 70%: **Yes — PASSES, with no margin.** Score is
  70.0% (91/130), unchanged from v17 — explained explicitly in the
  Readiness Score section (definitional tightening offset by this
  cycle's seven resolved changes), per Playbook Entry 1.
- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.
- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.
- No section consists solely of an "Unchanged from vN, not reproduced"
  pointer: **Yes.** Market & Competition — carried in v17 as a
  cross-reference to v16 — is restored to self-contained text this
  cycle, with an explicit provenance note stating what was rebuilt from
  v17-visible facts and what (v16's fuller narrative detail) is flagged
  as not reproduced rather than silently reconstructed. Every section
  contains its own full, substantive, self-contained text.

**This Business Case passes its own completion gate.** All seven of the
Investment Committee's required changes are resolved and documented,
including the honest characterizations it and the user's clarifications
demanded: the exam-bonus hybrid's accepted residual risk, the
underpowered double-duty pilot's directional-only demand read, the
retired 360-2,440 subscriber range, the no-Mpoints fallback's traced
ripple effects, and the R10,000/6-month execution-capacity risk stated
plainly. The rubric's definition of "Complete" is now explicit and
consistently applied. Genuine open items remain — detailed in Critical
Gaps — led by execution capacity, two externally-unsettled regulatory
questions (owned, with decided fallbacks), and the absence of any
statistically meaningful demand validation anywhere in the plan.
