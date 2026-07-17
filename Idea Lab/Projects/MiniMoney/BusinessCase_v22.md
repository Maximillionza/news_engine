# Business Case: MiniMoney — v22

> Prepared by: Incubator. This revision responds to the Investment
> Committee's sixth review (`Verdict_v6.md`, "Proceed with changes,"
> seven required changes) using the user's item-by-item decisions in
> `Clarifications_v22.md`. **Six of the seven required changes are
> resolved this cycle. The seventh (a concrete non-dilutive funding
> target) is explicitly NOT part of this cycle** — per the user's own
> decision it has been routed to Research House (Engagement 4,
> `TaskOrder_ResearchHouse_v4.md`) rather than guessed at, and remains a
> named, open item in Critical Gaps and Outstanding Questions below, not
> silently dropped. Authorized inputs for this cycle: `00_CaseStudy.md`,
> `BusinessCase_v21.md`, `Verdict_v6.md`, `Clarifications_v22.md`.

## What Changed in v22 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (six items); Unknown (one item, explicitly deferred)

**1. Required change 1 — specialist-review timing DEFINED, not
satisfied.** Both hard-gate reviews (Data-Privacy Practitioner on the
data-breach commitment; child-development specialist on the
motivation-probe) now share the same trigger already established for the
retained specialist legal opinion: **once a stable working model exists,
and before any pilot testing with real families begins.** This converts
the prior open-ended "must occur" language into a scheduled, though not
yet dated, commitment. **Stated explicitly, per the Investment
Committee's own required-change language: this is a timing fix, not a
completion.** Neither review has actually occurred as of this revision.
Updated in Constraints, Stakeholders, Roadmap, Success Criteria,
Validation Strategy, Risks, Outstanding Questions, and the Child Data &
Consent domain extension — everywhere the prior "must occur" phrasing
appeared, it now carries the specific trigger point alongside the
unchanged "not yet occurred" fact.

**2. Required change 2 — advice-policy coverage CONFIRMED for both named
reviews.** The user has confirmed the zero-marginal-cost professional-
advice policy covers both the Data-Privacy Practitioner review and the
child-development specialist review specifically. This resolves the
previously-Assumed coverage question for these two engagements
(Verified-tier). **It does not resolve the policy's general scope** —
whether it extends to other engagement types (e.g., a curriculum
designer for the deferred v2 workstream) remains undocumented and is
retained as an open item in Outstanding Questions.

**3. Required change 3 — dispute-escalation beyond 48 hours RESOLVED via
an interim placeholder.** Unresolved disputes beyond the 48-hour
parent-decline window are flagged for **manual founder review, at MVP
stage.** The user explicitly frames this as a placeholder, not a
scalable long-term solution, pending the previously-noted (out-of-scope)
future AI-mediator feature. This is **founder-capacity-dependent** — a
direct extension of the execution-capacity Critical Gap, since founder
bandwidth is already allocated across the build, the instrumented pilot,
and two regulatory rechecks inside the 6-month runway. Updated in
Operations, Technology, Risks, Roadmap, and Outstanding Questions.

**4. Required change 4 — low-end revenue stress test cross-referenced
against the self-fund-further contingency, RESOLVED.** If actual results
land at the low end of the revenue range (92 paying families,
~R5,519/month), this is treated as a **foreseen, already-planned-for
scenario that triggers the self-fund-further contingency** (up to the
R20,000 total ceiling) — not a failure state requiring a new decision.
Constraints, Revenue & Costs, and Financial Considerations now
cross-reference each other explicitly on this point so the sections read
consistently, per this cycle's specific instruction.

**5. Required change 5 — acquisition checkpoint/kill-metric DEFINED,
correcting Success Criteria's existing text.** The user has set the
pilot success criterion at **60%**: if fewer than 60% of enrolled pilot
families complete 4 consecutive weekly task→payslip cycles, organic-only
acquisition/mechanic engagement is treated as not yet validated before
widening release. **This replaces Success Criteria's previous vague
"majority" language directly — a correction to the section's own text,
not an addition alongside it** — and is cross-referenced explicitly as
the acquisition checkpoint/kill-metric in Validation Strategy and
Roadmap.

**6. Required change 6 — v2-curriculum "proved demand" trigger
QUANTIFIED.** Both a subscriber-count AND a retention-rate threshold
must be met: **500 paying subscribers AND 60% 90-day retention** — both
conditions required, a conservative dual-gate design chosen specifically
to avoid investing in curriculum for a subscriber base that has not
demonstrated it sticks around. **This replaces the previously undefined
"proved demand" phrase directly in Curriculum Design — a correction, not
an addition.** Whether a *general* retention success criterion,
independent of this v2-specific trigger, is still needed elsewhere
remains an explicitly open question (see Success Criteria, Outstanding
Questions).

**7. Required change 7 — non-dilutive funding target: NOT PART OF THIS
CYCLE, explicitly deferred to research, not guessed at.** No specific
program was known to the user; this has been routed to Research House
(Engagement 4, `TaskOrder_ResearchHouse_v4.md`) per standing framework
rules for vendor engagement. **This Business Case does not attempt to
resolve it and does not treat the deferral as a resolution** — it
remains a named, explicitly open item in Critical Gaps and Outstanding
Questions, to be incorporated once `ResearchFindings_v4.md` is delivered
and has passed the Incubator's own scrutiny (vendor output, Supported-tier
ceiling, per standing rules — never Verified-tier regardless of the
research's own confidence).

**Readiness Score recomputed in full this cycle — see the Readiness
Score section below. Stated plainly, as the completion gate requires:
the score does NOT move. It remains 94/130 = 72.3% (or 91/130 = 70.0%
under the disclosed conservative reading), identical to v21.** This
cycle's six resolutions converted process commitments into scheduled,
quantified, or confirmed items and corrected internal cross-referencing,
but none of them closed every remaining material question within any
individual section to the point of flipping that section's status from
Partial to Complete — in each affected section, at least one other
material question (a review not yet occurring; a funding-ask size still
unset; a revenue funnel still Guessing-tier; a general retention
benchmark still unset) remains open under the document's own "Complete"
standard. The full section-by-section reasoning is in Readiness Score.

## Executive Summary

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18), launching first in
South Africa on Android (iOS porting planned as future work). The launch
(MVP) product is the financial mechanic alone: a parent submits a budget
setting the minor's "basic income"; tasks earn Mbucks (a real-money-pegged
in-app currency, e.g. 10 Mbucks = R10) which accumulate into a "payslip,"
while every completed task separately earns a fixed 10 Mpoints — a
distinct, non-monetary cosmetic-store currency. The parent receives an
invoice and pays the owed amount directly to the child via the parent's
own banking app — MiniMoney itself never holds, transmits, or takes
custody of funds. Subscription pricing is R59.99/month, covering up to 4
children per family account; the funnel and revenue unit is the family.
Monetization is subscription-only at launch, with advertising deferred to
a possible post-launch V2.

Instructional curriculum content — including the 15-18-only "Fintech
Advance" module — remains out of MVP/launch scope, deferred to a
post-launch v2 feature. **What changed this cycle: the trigger for that
v2 feature is now quantified — 500 paying subscribers AND 60% 90-day
retention, both required** — replacing the previously undefined "proved
demand" phrase. The core launch mechanic itself already carries embedded
financial literacy (earning, budgeting, expense/tax-style deductions,
payment mechanics); structured instructional content is what remains
deferred, now against a specific, evaluable trigger rather than an
open-ended one.

Growth is organic-only at launch — zero paid acquisition, no marketing
budget allocated; the schools-partnership channel remains explicitly
deferred for stated founder-bandwidth reasons. **The pilot's own
acquisition checkpoint/kill-metric is now quantified this cycle: if fewer
than 60% of enrolled pilot families complete 4 consecutive weekly
task→payslip cycles, organic-only acquisition/mechanic engagement is
treated as not yet validated before widening release** — correcting the
prior vague "majority" language and giving the pilot-to-wider-release
transition an actual decision rule.

**Two hard pre-pilot/pre-enrollment specialist reviews — the data-breach/
incident-response commitment (Data-Privacy Practitioner) and the
exam-bonus motivation-probe (child-development specialist) — now have a
defined trigger point this cycle: once a stable working model exists,
and before any pilot testing with real families begins, matching the
trigger already used for the retained legal opinion. Stated plainly:
this defines *when* the reviews occur; it does not mean they have
occurred. Neither review has happened as of this revision.** The
runway-slippage contingency remains bounded at R20,000 total maximum
personal commitment, and **this cycle explicitly ties the low end of the
revenue range (92 paying families, ~R5,519/month) to that same
contingency as a foreseen, already-planned-for scenario** rather than an
unaddressed failure state. **The beyond-48-hour dispute-escalation gap
identified by the Investment Committee is now resolved via an interim
placeholder — manual founder review at MVP stage — explicitly named as
non-scalable and founder-capacity-dependent, pending a future
out-of-scope AI-mediator feature.**

Revenue figures are unchanged in magnitude from v21: **≈9,150-30,500
Year-1 family installs and ≈92-915 paying families** (≈R5,519-R54,891/
month run-rate), still resting on Guessing/Assumed-tier funnel
assumptions unchanged by this cycle's process resolutions.

**One required change from `Verdict_v6.md` — a concrete non-dilutive
funding target for the R20,000 self-fund ceiling's fallback — is
explicitly NOT resolved this cycle.** It is routed to Research House
(Engagement 4) rather than guessed at, and remains a named open item
below, distinct from the six changes that are resolved.

**The Readiness Score is unchanged at 94/130 = 72.3%** (or 91/130 = 70.0%
under the disclosed conservative reading), clearing the completion gate's
≥70% threshold in both computations, identical to v21's result. This
cycle's changes convert process commitments into scheduled, quantified,
or confirmed items and correct internal cross-referencing — genuine
progress on process integrity and internal consistency — but do not, on
their own terms, resolve any section's remaining material open questions
sufficiently to change its Complete/Partial status. See Readiness Score
for the full section-by-section reasoning.

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Parents lack a structured, automated system to teach children (6-18)
real-world financial concepts — earning, budgeting, taxation/expenses,
and payment mechanics — using real money in a controlled, task-based
framework. Existing allowance-tracking apps typically either (a) simulate
money entirely in-app with no real bank transfer, or (b) require manual
parent bookkeeping with minimal education layer. The underlying gate on
this problem is parent willingness and digital-financial engagement
(SARB: 50.3% of SA adults use banking apps regularly, adjusted to a
[Guessing] 55-65% for the economically-active parent cohort), not device
access among children ([Likely] 62% personal-device ownership by age 10,
per a 2024 Stellenbosch-region study of five former Model C high schools,
Grade 4-11).

The launch product addresses this problem through its earning/budgeting/
payment mechanic itself (tasks, payroll simulation, invoicing, payment
confirmation) — the mechanic *is* a form of experiential financial
education. Structured, explicit instructional curriculum content remains
a deliberate v2 addition, now gated by a quantified dual trigger (500
subscribers AND 60% 90-day retention, see Curriculum Design) rather than
an undefined "proved demand" phrase — a sequencing decision, not an
abandonment of the education premise.

A first-party interview round (n=10 families) found 6 of 10 confirmed
interest in using the app and stated willingness to pay for it; 7 of 10
expressed interest specifically in the education aspect. This remains
genuine, first-party, MiniMoney-specific evidence, not statistically
significant, and per standing instruction must not be used as a
representative demand signal until superseded by the planned pilot or a
structured survey.

Status remains Partial, unchanged this cycle: there is a real, encouraging
directional signal, but no established finding that parents broadly
perceive this as a problem worth paying to solve. None of this cycle's
six resolved changes bear on this section's core open question.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic rather than a simple
debit-card-for-kids model. No direct South African incumbent does what
MiniMoney does. The competitive detail, the reachable-market funnel
derivation, and international comparables (GoHenry, Greenlight, FamZoo,
Bomad) confirm MiniMoney's non-custodial, track-only model has structural
precedent elsewhere and is not a category outlier.

The subscription price (R59.99/month, up to 4 children per family)
sharpens the competitive read against MoneyTime SA's R995/year (25%
sibling discount): MiniMoney's annualized price (R719.88/family/year)
sits below MoneyTime SA's rate even before the sibling discount —
relevant opportunity context, but this does not on its own establish
market size or demand, which remains governed by the same n=10,
non-representative bound described in Problem.

The schools-partnership channel remains explicitly deferred, unchanged
this cycle, for founder-bandwidth reasons: the strongest demonstrated
reach model in the category (MoneyTime SA's own claimed 1,500+ schools,
130,000+ students), deliberately not pursued pre-launch. Status remains
Partial: the differentiation thesis is coherent and partly evidenced, but
no structured market-sizing or validated demand study has been conducted,
and the one channel with local reach precedent is out of scope for
launch. This cycle's six resolved changes do not bear on this section's
core open question.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The functional objective is: budget → tasks → Mbuck/Mpoint earning →
exam-period bonus (hybrid: behavior-primary rewards plus a retained
secondary results bonus, motivation-probe review now trigger-defined —
see Success Criteria) → invoice/payslip → payment confirmation with
escalating late-penalty (grace-period/pre-escalation reminder mechanism
committed; disputes beyond 48 hours now resolved via a manual
founder-review interim placeholder) → age-gated core mechanic. Structured
curriculum content remains deferred to v2, now against a quantified
dual-gate trigger (500 subscribers AND 60% 90-day retention).

**Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
payment loop, including the dispute and late-penalty mechanics, with a
small pilot cohort of South African families (candidate target: 20-50
families) before wider release. The pilot formally adopts the specialist
pilot-measurement package (see Success Criteria) plus the motivation-probe
addition, subject to its own trigger-defined specialist-review
requirement, and serves double duty: mechanic-safety signal AND a
directional demand read, now with an explicit 60% task-cycle-completion
acquisition checkpoint (see Validation Strategy).

**Growth (6-12 months):** validate the subscription-conversion assumption
against the recalculated 1-3% subscription-only reference range applied
to the corrected funnel; curriculum-engagement-as-a-retention-indicator
validation remains deferred alongside the v2 curriculum feature itself,
now against its quantified dual trigger; evaluate iOS port timing based
on Android traction.

The 90-day (recalculated installs) vs. annual funnel target tension
remains resolved via `Clarifications_v10.md`'s per-family convention. All
install and subscriber figures are per-family, per the 2.0-children-per-
family assumption (see Market & Competition). Status remains Complete:
every tension previously flagged in this section is resolved by direct,
Verified-tier user clarification; this cycle's resolutions strengthen
several of the section's own decisions without altering its status.

## Success Criteria

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Core criteria, CORRECTED this cycle (`Clarifications_v22.md` required
change 5):** pilot success / acquisition checkpoint is now **60%** — if
fewer than 60% of enrolled pilot families complete ≥4 consecutive weekly
task→payslip cycles, organic-only acquisition/mechanic engagement is
treated as not yet validated before widening release. **This figure
replaces the section's own previous vague "majority" language directly —
a correction to existing text, not an addition alongside it** — and now
doubles as the acquisition checkpoint/kill-metric cross-referenced
explicitly in Validation Strategy and Roadmap. Operational health (65%
task-completion without dispute, no external benchmark) and
freemium/subscription conversion (2%, benchmarked against the
recalculated 1-3% subscription-only range) are unchanged. **Retention: no
general figure proposed** — a distinct **60% 90-day retention** figure
now exists (`Clarifications_v22.md` required change 6) but is scoped
specifically to the v2-curriculum demand trigger, not this section's own
general retention benchmark (see Curriculum Design). Whether a general
retention success criterion, independent of that trigger, is still needed
here remains an explicitly open question (see Outstanding Questions).

**Curriculum-engagement criterion (30%)** remains reclassified, not
scored as an open gap, since curriculum content is deferred to v2 —
retained as a placeholder to be reintroduced, unbenchmarked, when the v2
feature is actually built against its now-quantified trigger.

**Family-relationship-strain criterion — measurement package adopted into
pilot design**, unchanged from v21 (`ChildDevelopmentReview_v1.md`):
borrowed items from the Parenting Stress Index – Short Form and the
Family Assessment Device – General Functioning Scale, administered to
parents at baseline and partway through the pilot; within-family,
within-week correlation tracking (late-penalty events vs. reported
household tension); age-stratified results (6-9, 10-14, 15-18 bands); a
brief child-report instrument (abbreviated Child–Parent Relationship
Scale, Conflicts subscale). The reviewer's caution stands: 20-50 families
is not large enough for full validated-instrument statistical power;
these are for lightweight, qualitative early-warning signal detection.

**Exam-bonus motivation-risk instrumentation — candidate instrument
exists; review trigger DEFINED this cycle, not satisfied
(`Clarifications_v22.md` required change 1).** The instrument itself is
unchanged: parent-facing Likert/open items alongside the existing
PSI-SF/FAD-GFS timepoints; child-facing age-appropriate items alongside
the existing Child–Parent Relationship Scale timepoint; near-zero
marginal cost, administered at existing survey events. **What changes
this cycle: the review must occur once a stable working model exists,
and before any pilot testing with real families begins — the same
trigger already used for the retained legal opinion. Stated plainly: no
family may be enrolled in the pilot until this review has actually
occurred, and it has not yet occurred as of this revision.** The probe
remains Evidence: Assumed until that review occurs.

The underlying substantive risk remains confirmed, not resolved: the
late-penalty redesign narrows but does not eliminate the Family Stress
Model's affective pathway, and the exam-bonus hybrid's residual
intrinsic-motivation risk is candidate-instrumented but not yet
specialist-reviewed or adopted.

Status remains Partial: the acquisition checkpoint is now a specific,
correct figure and the relationship-strain criterion has an adopted
measurement plan, but operational health and the general retention
benchmark remain unbenchmarked, and the motivation-risk review — though
now trigger-defined — has still not occurred.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18;
parents/guardians as sole registration custodian and subscription
purchaser; the app operator (a solopreneur founder); the South African
Information Regulator and the Advertising Regulatory Board; three named
competitor/adjacent-market stakeholders — African Bank's MyWORLD Power
Pocket, MoneyAfrica Kids, MoneyTime SA; Apple/Google as app-store platform
stakeholders.

Two regulator stakeholders remain, each owned by the user personally at
build-spec stage with a decided launch fallback: SARB and PASA, via the
National Payment System Act, engaged by the optional account-linking
feature's open-banking question (fallback: launch without
account-linking); and the FPB, via the Films and Publications Amendment
Act 2019, of uncertain but plausible application to the Mpoints gamified
rewards system (fallback: launch without Mpoints).

The linking aggregator (Stitch/Mono-style, where a parent opts in)
remains an additional data-processor stakeholder. **The retained
child-development professional (Expert Roster Entry 2) and the
Data-Privacy Practitioner (Expert Roster Entry 5) both now have a
defined review trigger** — once a stable working model exists, and
before any pilot testing with real families begins — **rather than the
prior open-ended "must occur" framing. Their advice is confirmed
zero-marginal-cost this cycle. Neither review has yet occurred — the
trigger definition changes the requirement's schedulability, not its
completion status.** A future AI mediator feature for dispute resolution
remains explicitly out of current scope, now named specifically as the
eventual replacement for the interim manual-founder-review
dispute-escalation placeholder (see Operations). A curriculum/
instructional-design specialist (Expert Roster Entry 3) is a named future
stakeholder for the deferred v2 curriculum feature, now gated by a
quantified trigger, not yet engaged.

Status remains Partial: both regulator stakeholders have an owned recheck
and a fallback but remain unresolved pending those rechecks; the two
named specialist reviews now have a defined trigger point but neither has
actually occurred.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18, and their
parents/guardians, in South Africa, on Android at launch (iOS deferred).
A minor is not an independently reachable user: every child account
requires a parent acting as registration custodian from the outset. The
paying customer unit is the family (one subscription = one family = up to
4 children) — the child is the user, the parent is the customer, and all
funnel counts are family counts, applying a stated 2.0-children-per-family
assumption (Evidence: Assumed, unchanged this cycle) to convert the
reachable-child population into a reachable-family figure (see Market &
Competition). Status remains Partial, unchanged this cycle: the target
population is clearly named and the customer unit is unambiguous, but no
market-sizing or persona-level detail exists beyond Market & Competition
and the funnel figures in Objectives.

## Value Proposition

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The launch value proposition is the financial mechanic alone — budget
setting, task assignment, Mbuck/Mpoint earning, payslip/invoice, payment
confirmation, dispute and late-penalty handling, now including a defined
(if interim) beyond-48-hour dispute-escalation path. The Free/Subscription
split and the R59.99/month (up to 4 children per family) price stand.
Fintech Advance (the 15-18-only trading/entrepreneurship module) remains
deferred to v2 alongside the rest of curriculum content, now against a
quantified dual trigger (500 subscribers AND 60% 90-day retention) rather
than an undefined phrase. Its prior mitigation decisions (no product
gamification for its content; risk-literacy framing over aspirational
framing, per `ChildDevelopmentReview_v1.md` Q5) remain adopted and will
apply unchanged whenever the module is actually built.

**Mbucks non-transferability — a locked product-spec constraint,
unchanged.** Per `LegalOpinion_v1.md` Q1, MiniMoney's low money-
transmitter/e-money risk is contingent on Mbucks remaining a pure
unit-of-account. Any future roadmap change to this requires the
money-transmitter analysis to be redone (see Legal & Compliance, Business
Model, Constraints).

**Terminology — adopted, unchanged.** Debt-coded language ("invoice,"
"arrears," "late penalty") is reserved for parent-facing surfaces only;
child-facing surfaces use softer language.

**Conditional exposure, named not hidden:** under the no-Mpoints launch
fallback (see Legal & Compliance), the in-app cosmetic store has no
currency and must be removed from that configuration, thinning the
subscription tier's child-facing appeal further on top of Fintech
Advance's deferral. The launch value proposition is narrower than the
product's eventual full vision by two independent, stated decisions
(regulatory fallback; MVP-scope deferral) — both named explicitly.

Status remains Complete, unchanged this cycle: price, feature boundaries
for the corrected launch scope, and all previously-pending decisions
within this section's scope are made; this cycle's resolutions
strengthen (dispute-escalation path defined; curriculum trigger
quantified) without altering the section's decided core.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in substance from v21 — none of this cycle's six resolved
changes bear directly on this section's own open questions.

**Population base (6-18):** [Certain] Stats SA's mid-2025 estimate puts
South Africa's total population at 63.1 million, with children under 15
at 26.2% (≈16.5 million). [Guessing] extrapolating from single-year
cohort size and adding the 15-18 band gives a modeled estimate of roughly
**14-15 million people aged 6-18** — not a directly sourced figure.

**Device access:** [Likely] a 2024 South Africa-specific study (five
former Model C high schools, Stellenbosch research) found 62% of learners
Grade 4-11 own a personal device by age 10. Household access is plausibly
75-85% for the 6-18 band, a bounded guess.

**OS split:** [Certain] Android holds 76.74% of mobile OS share in South
Africa as of May 2026 (Statcounter), iOS 23.24%.

**Parent financial-app engagement (the real gate):** [Likely] SARB's
Payments Study found 50.3% of South African adults use banking apps
regularly. [Guessing] a reasonable adjustment for the economically-active
parent cohort is **55-65% banking-app engagement**.

**Reachable-market funnel (population-level, child-count):** 14.5M kids ×
~70% device access × ~60% parent digital-financial engagement ≈ **6.1M
kids in "reachable" households**.

**Family-level conversion:** 2.0 children per subscribing family
(Evidence: Assumed, unchanged this cycle), within the up-to-4-per-family
cap. **Reachable families = 6.1M reachable kids ÷ 2.0 ≈ 3.05M reachable
families.**

**Adoption rate:** [Guessing] no public South African benchmark exists;
inference from adjacent markets (GoHenry/Greenlight UK/US) suggests
0.3-1% Year-1 install capture; free-to-paid conversion for freemium/
subscription kids'-finance apps benchmarks 2-6% globally — South Africa's
lower discretionary income argues for the low end, **1-3%**.

**Funnel, unchanged this cycle:** ≈3.05M reachable families × 0.3-1%
Year-1 install capture ≈ **9,150 to 30,500 family installs.** Applying
1-3% conversion: **≈92 to 915 paying families in Year 1.**

**Competition in South Africa:** unchanged — African Bank's MyWORLD Power
Pocket, MoneyAfrica Kids, MoneyTime SA remain the three named local
players, each missing at least one defining dimension. MoneyTime SA's
1,500+ schools/130,000+ students remains the strongest demonstrated reach
model, deliberately deferred as a channel per prior cycles.

**International comparables:** GoHenry/Greenlight solve payment
verification via card-issuing/e-money licensing; FamZoo/Bomad are closer
structural analogs, track-only with no bank integration, confirming
MiniMoney's model has precedent elsewhere.

**What remains unresearched, unchanged:** validated demand; structured
market sizing beyond the user's own funnel estimate; MoneyAfrica Kids'
premium price; acquisition economics against the organic-only growth
strategy in absolute terms (the pilot's new 60% checkpoint gates the
pilot-to-wider-release transition but does not itself validate whether
organic discovery can reach the 9,150-30,500 range — see Validation
Strategy).

Status remains Partial, unchanged this cycle: the competitive landscape
and funnel are fully documented and the population-conversion gap remains
closed via a stated (Assumed-tier) figure, but the most decision-relevant
figures (Year-1 adoption, conversion rate) remain unvalidated.

## Business Model

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unchanged in substance from v21. Subscription-only at launch, ads
deferred to V2; R59.99/month per family, covering up to 4 children — the
family is the revenue unit. MiniMoney is a facilitation/education layer
that sits on top of the parent's own bank account and does not move or
hold funds. The core mechanic — not instructional curriculum content — is
what the subscription pays for at launch.

The core business-model uncertainty flagged since v8 — money-transmitter
licensing — remains resolved per `LegalOpinion_v1.md` Q1: risk is low,
contingent on Mbucks remaining strictly non-transferable and
non-redeemable.

Optional account-linking remains a trust/verification feature within the
existing subscription model. Its NCR question is resolved clean; the
SARB/NPS Act open-banking question remains genuinely unsettled, owned by
the user personally, timed to build-spec stage, with an explicit
fallback: launch without account-linking.

The FPB classification question carries an explicit launch fallback
(launch without Mpoints); the Mpoints/Apple IAP-currency question is
mooted entirely under the no-Mpoints fallback. Status remains Complete,
unchanged this cycle: the model's structure, unit, price, and every
put-to-decision item within its scope are decided.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Revenue (per-family):** unchanged in magnitude from v21. Subscription
revenue at R59.99/month per family against the Year-1 range of **92 to
915 paying families**:

- Lower bound: 92 families ≈ **R5,519/month** (≈ R66,229/year run-rate).
- Upper bound: 915 families ≈ **R54,891/month** (≈ R658,690/year
  run-rate).
- These are end-state run-rates against an unvalidated funnel and
  conversion rate; actual Year-1 collected revenue would be
  ramp-dependent and lower.

**Low-end stress test, cross-referenced this cycle
(`Clarifications_v22.md` required change 4):** if actual results land at
the lower bound (92 paying families, ~R5,519/month), this is treated as a
**foreseen scenario that triggers the self-fund-further contingency** (up
to the R20,000 total ceiling) described in Constraints — not a new
decision point or an unaddressed failure state. This does not change the
revenue figures themselves; it states explicitly what happens if they
land at the low end.

**Costs.**

- **Development budget: R10,000 total** committed for the app build.
- **Self-fund-further cap: an additional R10,000 — R20,000 total maximum
  personal commitment**, hard ceiling, with grant/startup-program funding
  named as the fallback if exhausted (see Constraints, Financial
  Considerations). **The specific non-dilutive funding target for that
  fallback remains unresolved this cycle — out for research (see What
  Changed in v22, item 7).**
- **Professional opinions/advice: zero marginal cost to the venture**, via
  the user's existing policy. **Coverage for the two named hard-gate
  reviews (Data-Privacy Practitioner; child-development specialist) is
  now CONFIRMED this cycle (`Clarifications_v22.md` required change 2) —
  Verified-tier, no longer Assumed for these two engagements
  specifically.** The policy's general scope for other engagement types
  (e.g., a curriculum designer) remains undocumented.
- **Runway: 6 months** at current commitment before external funding is
  needed.
- **Acquisition/CAC: organic-only, zero paid acquisition.** No marketing
  budget is allocated from the R10,000 total. The schools-partnership
  channel remains explicitly deferred.
- **Curriculum content-production cost:** remains moot for launch,
  deferred alongside the feature itself, now against a quantified v2
  trigger.

**Reconciliation against the prior agency reference range, unchanged:**
the previously-cited $25,000-$120,000+ engineering-cost range was a
reference frame, not the plan. R10,000 buys days, not months, of
professional engineering if the founder's own capacity fails — there is
no buffer to purchase execution beyond the R20,000 total ceiling.

**Still open:** no post-runway external funding-ask is sized, and the
specific non-dilutive funding target for the R20,000 ceiling's fallback
is explicitly out for research this cycle, not resolved. Status remains
Partial: the low-end stress test is now cross-referenced consistently
with Constraints and the advice-policy coverage question is resolved for
the two named reviews, but the revenue side still rests on unvalidated
Guessing-tier estimates and the funding-ask size (including its
non-dilutive fallback target) remains unspecified.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Core mechanics (budget and earning, task structure,
completion/verification/reporting flow, dispute mechanism, payment
confirmation, late-penalty parent-only design) are unchanged in
structure. All specialist design decisions from prior cycles stand.

**Dispute-escalation beyond 48 hours — RESOLVED this cycle
(`Clarifications_v22.md` required change 3), no longer a tracked gap.**
Unresolved disputes beyond the 48-hour parent-decline window are flagged
for **manual founder review, at MVP stage** — an explicit interim
placeholder, not a scalable long-term solution, pending the future
(out-of-scope) AI-mediator feature. **This is founder-capacity-dependent
and is named explicitly as a direct extension of the execution-capacity
Critical Gap** — founder bandwidth already spans the build, the
instrumented pilot, and two regulatory rechecks within the 6-month
runway, and now also absorbs any beyond-48-hour disputes the pilot
generates.

**Fintech Advance gamification-avoidance decision — remains MOOT for
launch, not an active build task.** Fintech Advance itself is deferred to
v2 alongside all curriculum content, now against a quantified trigger;
its mitigation decision (no product gamification for its content) remains
adopted for whenever the module is eventually built.

**New build-spec items introduced by the hybrid bonus, unchanged:** the
mechanism for logging/verifying the behavior inputs and the grade-input
mechanism for the retained results-bonus layer both need specification at
build time.

Status remains Complete: every specialist recommendation within this
section's scope has a recorded decision; the previously-tracked
dispute-escalation gap is now resolved via a named interim mechanism,
strengthening rather than changing the section's status.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v21. Still unspecified: how account-linking is technically
initiated; how payment confirmation is captured beyond the accept/dispute
UI; the exam-bonus grade-input mechanism; the hybrid bonus's
behavior-input logging/verification mechanism; the grace-period/reminder
notification infrastructure. No curriculum-delivery technology is in
scope, consistent with its deferral. This cycle's six resolved changes do
not bear on this section's open items — they are process/decision
resolutions, not technical specifications. Status remains Partial.

## Legal & Compliance ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unchanged in substance from v21. The retained specialist legal opinion
(`LegalOpinion_v1.md`) remains the Verified-tier foundation of this
section — all seven originally-scoped questions answered.

**1. Money-transmitter/payment-facilitation risk: low, contingent on a
locked product-spec constraint.** [Likely] holds only as long as Mbucks
cannot be spent, transferred, or redeemed anywhere other than through the
parent's independent banking-app payment — confirmed [Certain] against
SARB's e-money Position Paper. Courts look at substance, not labels
(*Maize Board v Jackson* 2005 (6) SA 592 (SCA)). NCR's Payment
Distribution Agent category confirmed inapplicable.

**2. Universal parental-consent gate:** legally sufficient as designed,
POPIA s34/s35(1)(a) satisfied. Two hardening recommendations remain
build tasks: consent-flow documentation separation; lightweight parent
identity-verification step.

**3. POPIA Section 14 retention:** confirmed [Certain] no minor-specific
supplementary rule exists; a specific retention purpose, period, and
deletion trigger must be affirmatively designed.

**4. Minor contractual capacity:** fully verified — the
"rights without obligations" exception fits MiniMoney's structure,
supported by *Pitout v North Cape Livestock* (1977) and *Conradie v
Rossouw* (1919 AD 279).

**5. Terminology risk:** real, mitigation ADOPTED — debt-coded
terminology reserved for parent-facing surfaces only. ARB Code Clause
14.2 and Clause 6.1, Section III engaged, plus a CPA secondary layer; no
ARB ruling directly addresses this fact pattern — a genuine interpretive
gap.

**6. SARB/NPS Act open-banking question:** owned by the user, timed to
build-spec stage, fallback: launch without account-linking.

**7. FPB classification question (Mpoints):** owned by the user, timed to
build-spec stage, fallback: launch without Mpoints. Fintech Advance's own
content risk remains a v2 consideration.

**No-Mpoints launch configuration, unchanged:** the in-app cosmetic store
is removed; the flat 10-Mpoints-per-task reward is gone; the Google Play
loyalty-point disclosure item is mooted in that configuration.

Status remains Complete, unchanged this cycle: all seven originally-scoped
questions are answered at Verified tier; the two unsettled external
regulatory questions are pending external rechecks with named owners and
decided fallbacks. None of this cycle's six resolved changes touch this
section's substance — they are separately tracked process and product
decisions.

## Risks

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

All previously-identified risk categories remain catalogued; decision
status updated per this cycle's changes.

- **Regulatory risk:** unchanged — core mechanic low-risk; two narrower
  open regulatory questions each carry a named owner, timing trigger, and
  decided fallback.
- **Execution-capacity risk — bounded contingency, now with an additional
  named demand.** A solopreneur venture with a R10,000 total development
  budget, a ~3-month directional build timeline, an instrumented 20-50
  family pilot, two personally-owned regulatory rechecks, and now also
  **manual founder review of any dispute unresolved beyond 48 hours** —
  all inside a 6-month runway, executed substantially by one person. The
  self-fund-further contingency remains capped at R20,000 total, with
  grant/startup-program funding as the stated fallback, **now explicitly
  the mechanism triggered if actual revenue lands at the low end of the
  range (see Revenue & Costs, Constraints)**. Whether R20,000 total is
  itself sufficient capital to reach sustainability, and whether a
  specific non-dilutive funding target is actually obtainable, both
  remain untested and the latter is explicitly out for research.
- **Acquisition/adoption risk — now with a defined checkpoint, not fully
  resolved.** Zero paid acquisition remains the decided strategy against
  the 9,150-30,500 family-install funnel. **The pilot's 60%
  task-cycle-completion criterion now doubles as an explicit
  acquisition/mechanic-engagement checkpoint for the pilot-to-wider-
  release transition** (`Clarifications_v22.md` required change 5) — this
  gates premature scaling but does not itself validate whether organic
  discovery can reach the funnel's absolute size, which remains untested.
  The schools-partnership channel remains explicitly deferred.
- **Child-safety/data-privacy risk:** consent model confirmed legally
  sufficient; two hardening recommendations remain build tasks. POPIA
  Section 14 retention policy remains an affirmative design requirement.
  **The data-breach/incident-response commitment specialist review now
  has a defined trigger — once a stable working model exists, before any
  pilot testing with real families begins — matching the legal opinion's
  own trigger. It has not yet occurred.**
- **Minor-contractual-capacity risk:** resolved, unchanged.
- **Terminology/perception risk:** mitigation decided, unchanged.
- **Late-penalty/relationship risk:** both mitigation paths engaged,
  unchanged; residual risk remains real.
- **Exam-bonus/intrinsic-motivation risk — candidate-instrumented, review
  trigger now defined, not yet obtained.** The behavior-primary redesign
  follows the evidence; the retained outcome-contingent bonus layer means
  the crowding-out risk is reduced, not eliminated. No family may be
  enrolled until the review has actually occurred, and it has not yet
  occurred as of this revision.
- **Fintech Advance content risk:** moot for launch, deferred to v2,
  unchanged.
- **Age-appropriateness/terminology-uniformity risk:** framework adopted;
  reconciliation drafted, not yet specialist-reviewed, unchanged.
- **v2-trigger-criterion risk — RESOLVED this cycle
  (`Clarifications_v22.md` required change 6).** The previously-named risk
  of an unquantified "proved demand" trigger is closed: the trigger is now
  a specific dual gate (500 subscribers AND 60% 90-day retention). A minor
  residual remains untraced: the case does not specify what happens if
  one threshold is met and the other is not (e.g., 500 subscribers but
  under 60% retention) — a narrow interpretive gap, not a material one,
  since neither threshold being met currently blocks anything before
  launch.
- **Dispute-escalation risk — RESOLVED this cycle
  (`Clarifications_v22.md` required change 3) via an interim, explicitly
  non-scalable mechanism** (manual founder review beyond 48 hours),
  founder-capacity-dependent, pending the future AI-mediator feature.
- **Competitive risk; monetization-execution risk; app-store policy risk;
  platform-concentration risk:** unchanged in substance.

Status remains Complete: the risk landscape is comprehensively identified
and characterized, and every specialist-recommended mitigation within it
carries a recorded decision. A Complete risk register does not mean the
risks are eliminated: execution capacity (now carrying an additional
named demand), two external regulatory questions, the accepted exam-bonus
residual, the untested organic-only acquisition strategy (now partially
checkpointed), and the unresolved non-dilutive-funding-target question
are all live, and are stated as such.

## Assumptions

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Carried forward, unchanged: parent-direct payment; SA launch jurisdiction;
universal consent gate; Android-first; Mbucks/Mpoints dual currency;
7-Mbuck late-penalty cap with 3-Mbuck pilot cap; the fixed Mbucks-to-Rand
peg; the late-penalty mechanic as a parent-only administrative matter;
exam-bonus grade data self-reported/parent-entered; primarily a South
African B2C product at launch; 2.0 children per subscribing family
(Evidence: Assumed, not derived or validated).

**Two assumptions RESOLVED this cycle, no longer carried as open
assumptions:**

- **The advice-policy's coverage of the two hard-gate specialist reviews**
  is now confirmed (Verified-tier), not Assumed, per
  `Clarifications_v22.md` required change 2. (The policy's *general*
  scope for other engagement types remains undocumented — see Outstanding
  Questions — but that is now a distinct, narrower open item, not this
  specific assumption.)
- **The "once we have proved a demand" v2-curriculum trigger's
  interpretability** is resolved by quantification (500 subscribers AND
  60% 90-day retention, `Clarifications_v22.md` required change 6) — no
  longer an assumption about future interpretability, but a stated,
  evaluable rule.

**Remaining load-bearing assumptions, untested:**

- The exam-bonus risk-acceptance assumption stands: the secondary bonus's
  salience will not dominate the behavior-primary structure in the
  child's perception. Untested; candidate-observable via the
  motivation-probe, pending its now-trigger-defined specialist review.
- Organic-only acquisition will be sufficient to reach a meaningful share
  of the 9,150-30,500 family-install funnel. Untested, unbenchmarked;
  partially checkpointed via the pilot's 60% completion criterion but not
  validated in absolute terms.
- The self-fund-further ceiling (R20,000 total) is sufficient capital to
  reach a sustainable venture, or grant/startup-program funding is
  actually obtainable if it is not. Neither is tested; the specific
  non-dilutive target is explicitly out for research this cycle.
- The Incubator-drafted candidate data-breach commitment and
  motivation-probe are adequate as interim policy/design pending their
  respective specialist reviews. Both remain Evidence: Assumed by
  construction; both reviews now have a defined trigger, neither has
  occurred.
- Mbucks non-transferability/non-redeemability and the SARB/NPS Act
  contingency remain documented constraints, not assumptions (see
  Constraints).

Status remains Partial: two previously-open assumptions are resolved this
cycle, but several load-bearing assumptions remain untested — the list is
a working inventory, not a closed set.

## Constraints

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (with two Assumed-tier additions, named below)

- Solopreneur venture; AI-assisted development; external technical
  expertise engaged only on-demand; directional ~3-month build timeline;
  Android primary, iOS deferred.
- **Mbucks non-transferability/non-redeemability** — binding product-spec
  constraint on all future roadmap decisions (`LegalOpinion_v1.md` Q1).
- **R10,000 total development budget; 6-month runway before external
  funding is needed; professional opinions at zero marginal cost.**
  Coverage of the two hard-gate specialist reviews under this policy is
  **CONFIRMED this cycle** (`Clarifications_v22.md` required change 2).
  The runway, not the cash budget, is the binding constraint.
- **Zero paid acquisition — organic-only growth.** No marketing budget is
  allocated from the R10,000 total; the pilot's 60% task-cycle-completion
  criterion (`Clarifications_v22.md` required change 5) now serves as the
  checkpoint gating the transition to wider release.
- **Schools-partnership channel — explicitly deferred**, founder bandwidth
  is the binding constraint stated, unchanged.
- **Curriculum/educational content deferred to v2 — an explicit MVP-scope
  constraint**, now against a quantified dual trigger (500 subscribers AND
  60% 90-day retention, `Clarifications_v22.md` required change 6). The
  launch build, budget, and 6-month runway do not need to accommodate
  curriculum authoring or production.
- **Dispute-escalation beyond 48 hours — RESOLVED this cycle via an
  interim, explicitly non-scalable mechanism** (`Clarifications_v22.md`
  required change 3): manual founder review at MVP stage, pending the
  future out-of-scope AI-mediator feature. **A binding process constraint
  on founder bandwidth**, tracked as an extension of the
  execution-capacity Critical Gap.
- **Runway-slippage contingency — self-fund further, bounded, unchanged
  in magnitude this cycle.** Maximum personal commitment: R20,000 total
  (R10,000 initial + R10,000 additional) — a hard ceiling. If the cap is
  exhausted without the venture being sustainable, the stated fallback is
  grant or startup-program funding (non-dilutive), not equity or informal
  borrowing. **CROSS-REFERENCED explicitly this cycle
  (`Clarifications_v22.md` required change 4): this contingency is the
  exact mechanism triggered if actual Year-1 revenue lands at the low end
  of the range (92 paying families, ~R5,519/month) — a foreseen,
  already-planned-for scenario, not a new failure state requiring a new
  decision. See Revenue & Costs, Financial Considerations.** The specific
  non-dilutive funding target remains unresolved — explicitly out for
  research this cycle, not part of this Business Case's own decision set.
- **Minimal data-breach/incident-response commitment — Incubator-drafted
  candidate, review trigger DEFINED this cycle
  (`Clarifications_v22.md` required change 1): the same trigger already
  established for the specialist legal opinion — once a stable working
  model exists, and before any pilot testing with real families begins.**
  Stated plainly: this defines *when* the review occurs; the review
  itself has not yet occurred as of this revision. **Evidence: Assumed**
  — a founder-authored draft. The commitment must not be in force, and
  pilot enrollment of real families must not begin, until the
  Data-Privacy Practitioner (Expert Roster Entry 5) has actually reviewed
  it. Candidate minimum content, unchanged from v21:
  - **What constitutes a breach:** unauthorized access to a minor's
    personal information or account data held by MiniMoney.
  - **Who is notified:** affected parents; the South African Information
    Regulator, consistent with POPIA's Section 22 breach-notification
    obligation.
  - **Timeframe:** notification "as soon as reasonably possible" after
    confirmed detection.
  - **Content of notification:** nature of the breach, the personal
    information reasonably believed to be affected, and measures taken or
    recommended to mitigate harm.
- **Launch-configuration constraints (decided fallbacks):** the product
  must be buildable in three configurations — full; without
  account-linking (SARB unresolved); without Mpoints (FPB unresolved).

**Re-derivation, per the same standard this document has applied since
v21 — is Constraints' Complete status still soundly earned?** Every
material question within this section's scope carries a made decision:
budget, runway, acquisition, launch-configuration fallbacks, MVP-scope,
the self-fund-further bound and its fallback *form*, and now
dispute-escalation. The self-fund-further contingency's fallback *form*
(grant/startup-program funding) is decided; its specific *target* is
explicitly out for research and not yet decided — but per this document's
own standard, an owned, timed, externally-gated question with a decided
fallback (the pattern already used for SARB/FPB) is compatible with
Complete status. The specific funding target is analogous: owned (via the
Research House engagement), timed (before the R20,000 ceiling would be
exhausted), with a decided fallback *category* already in place. **This
section's Complete status is therefore retained on the same grounds as
v21, strengthened by this cycle's cross-referencing and the
dispute-escalation resolution, not weakened by the deferred seventh
required change.**

## Roadmap

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Now (parallel with build, starting immediately):** core engineering
build only. Curriculum-content workstream remains removed from this
phase, deferred to a post-launch v2 phase, now against a quantified
trigger (500 subscribers AND 60% 90-day retention).

**Build phase:** implement core loop with decided designs —
parent-facing-only debt terminology; hybrid exam bonus; grace-period/
pre-escalation reminders; **beyond-48-hour dispute escalation via manual
founder review (interim placeholder, resolved this cycle).** Legal build
tasks: POPIA s14 retention period and deletion trigger design;
consent-flow documentation separation; lightweight parent
identity-verification step. **The candidate data-breach/incident-response
commitment (see Constraints) must be reviewed by the Data-Privacy
Practitioner (Expert Roster Entry 5) once a stable working model exists
and before any pilot testing with real families begins — the same trigger
already used for the retained legal opinion, defined explicitly this
cycle. This has not yet occurred.**

**Build-spec stage:** the user personally runs both regulatory rechecks —
SARB/NPS Act and FPB. Decided fallbacks apply if unresolved by launch.

**Pilot (20-50 families):** double-duty per prior decision — mechanic
safety/child-development signal AND directional demand read — with the
adopted measurement package plus the candidate motivation-probe addition
built into the pilot design. **The candidate motivation-probe must be
reviewed by the child-development specialist (Expert Roster Entry 2)
using the same trigger — once a stable working model exists, before any
pilot testing with real families begins. Not yet occurred.** **The pilot's
60% task-cycle-completion criterion now doubles explicitly as the
acquisition/mechanic-engagement checkpoint** (`Clarifications_v22.md`
required change 5) gating the transition to wider release: fewer than 60%
completing 4 consecutive weekly cycles means organic-only
acquisition/engagement is treated as not yet validated.

**Post-pilot (~month 6): external funding may be needed** — the initial
runway ends here. **Decision rule, unchanged in magnitude, cross-
referenced explicitly this cycle:** if month 6 arrives without secured
external funding, or any single workstream has slipped materially — **or
actual revenue lands at the low end of the range (92 paying families,
~R5,519/month), a foreseen scenario per this cycle's cross-reference** —
the user will self-fund further up to a hard ceiling of R20,000 total
personal commitment. If that ceiling is reached without a sustainable
venture, the stated fallback is grant or startup-program funding; **the
specific non-dilutive target for that fallback is out for research and
not yet determined.**

**Growth (6-12 months):** conversion validation against the corrected
1-3% range applied to the corrected funnel; iOS port timing evaluation;
account-linking and/or Mpoints re-introduction as their regulatory
questions resolve. Schools-partnership channel exploration remains
explicitly deferred.

**Post-launch, demand-gated (v2, timing determined by trigger, not
calendar): curriculum content workstream.** **Trigger QUANTIFIED this
cycle: 500 paying subscribers AND 60% 90-day retention, both required**
(`Clarifications_v22.md` required change 6) — replacing the previously
undefined "proved demand" phrase. Authorship (founder vs. engaged
designer via the zero-marginal-cost advice policy, pending confirmation
of that policy's *general* scope) remains open, not time-pressured. The
three-tier-to-six-way sub-band reconciliation remains drafted as low-cost
prep work, not adopted.

Status remains Complete: every pre-pilot decision the roadmap lists as
pending is made; the two specialist reviews now carry a defined trigger
point, not merely a stated intention; the low-end revenue scenario is now
explicitly tied to the existing self-fund-further contingency; the
dispute-escalation gap is resolved via a named interim mechanism; the
v2-curriculum trigger is quantified. The remaining opens are owned
external rechecks, build-spec parameters, the still-not-yet-occurred
specialist reviews (trigger defined, not satisfied), and the deferred
non-dilutive funding target.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**What exists:**

- **Budget: R10,000 total** for development.
- **Self-fund-further cap: R20,000 total maximum personal commitment**
  (R10,000 initial + R10,000 additional). Fallback if exhausted: grant or
  startup-program funding (non-dilutive), not equity or informal
  borrowing. **The specific non-dilutive funding target is explicitly OUT
  FOR RESEARCH this cycle (Research House Engagement 4,
  `TaskOrder_ResearchHouse_v4.md`) — not resolved, not guessed at, named
  here as a genuinely open item.**
- **Professional advice: zero marginal cost** via the user's existing
  policy. **Coverage of the two hard-gate specialist reviews CONFIRMED
  this cycle** (`Clarifications_v22.md` required change 2); the policy's
  general scope for other engagement types remains undocumented.
- **Runway: 6 months** before external funding is needed.
- **Revenue model (per-family), unchanged in magnitude:** R59.99/month
  per family against a Year-1 range of **92-915 paying families** —
  R5,519-R54,891/month run-rate at the range bounds (≈R66,229-R658,690/
  year); ramp-dependent actuals lower. **Low-end explicitly
  cross-referenced this cycle against the self-fund-further contingency
  as a foreseen scenario** (`Clarifications_v22.md` required change 4) —
  see Constraints, Revenue & Costs.
- **Acquisition spend: zero.** No marketing budget is allocated; growth
  is organic-only, now with the pilot's 60% completion criterion serving
  as an explicit checkpoint on the acquisition/engagement dimension.
- **Curriculum content-production cost:** remains moot for launch,
  deferred alongside the feature, now against a quantified trigger.

**The reconciliation, unchanged:** R10,000 (~$550) against the previously-
cited $25,000-$120,000+ agency range is a 45×-220× gap, coherent only as a
founder-labor-plus-AI-assisted build. The 6-month runway is the binding
constraint: build, instrumented pilot (behind two trigger-defined
specialist-review gates, neither yet satisfied), and two user-owned
regulatory rechecks must all complete inside it, after which funding is
needed — with, at best, directional pilot evidence to raise on, or the
user self-funds up to R20,000 total before falling back to grant/
startup-program funding of a still-undetermined specific target.

**This cycle's decisions:** confirm advice-policy coverage for the two
hard-gate reviews; cross-reference the low-end revenue scenario explicitly
against the self-fund-further contingency; remove dispute-escalation cost
ambiguity (an interim, no-marginal-cost mechanism); leave the
non-dilutive funding target explicitly and deliberately unresolved,
routed to research rather than guessed at. Still absent, named: the size
and specific target/form of any external funding ask beyond the R20,000
self-fund ceiling (pending Research House Engagement 4); full financial
projections (P&L, break-even). Status remains Partial: the section now
has confirmed advice-policy coverage and a consistent cross-reference
between the low-end revenue scenario and the runway contingency, but
funding-ask sizing (including its non-dilutive target) and break-even
analysis remain absent.

## Validation Strategy

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Closed streams, unchanged:** legal validation (retained opinion,
Verified-tier); child-development/age-appropriateness validation
(retained review, Verified-tier); all resulting design recommendations
carry decisions.

**Pilot — scope decided: double duty**, with the reviewer's underpowering
caution attached: demand findings will be directional and qualitative,
not statistically validated. **The adopted measurement package includes
a candidate motivation-probe, review trigger now DEFINED**
(`Clarifications_v22.md` required change 1) — once a stable working model
exists, before any pilot testing with real families begins; not yet
occurred.

**Acquisition/mechanic-engagement checkpoint — RESOLVED this cycle
(`Clarifications_v22.md` required change 5), previously "no validation
plan of any kind."** Tied to the pilot's own 60% task-cycle-completion
criterion (see Success Criteria): if fewer than 60% of enrolled pilot
families complete 4 consecutive weekly cycles, organic-only
acquisition/mechanic engagement is treated as not yet validated before
widening release — a real, evaluable checkpoint gating the
pilot-to-wider-release transition. **Stated precisely: this resolves the
prior finding that no validation plan existed for that specific
transition decision. It does not itself validate whether organic-only
acquisition can reach the corrected 9,150-30,500 install funnel in
absolute terms — that remains untested, a distinct and still-open
question** (see Market & Competition, Assumptions).

**Curriculum validation — remains reclassified, not an open gap for
launch.** Since curriculum content is deferred to v2, there is nothing to
validate at launch; this stream will be reintroduced when the feature is
actually built, now against its quantified dual trigger (500 subscribers
AND 60% 90-day retention).

**Still open, unchanged:** pricing/conversion validation (the pilot may
inform willingness-to-pay directionally but is not a conversion test);
account-linking UX/consent-flow validation; the no-Mpoints fallback
configuration's engagement loop has no validation plan.

Status remains Partial: the pilot is fully scoped and instrumented at the
decision level, both specialist reviews now carry a defined trigger, and
the acquisition checkpoint is resolved for the pilot-to-wider-release
transition specifically — but market demand, pricing/conversion, and
absolute acquisition feasibility have no statistically meaningful
validation scheduled anywhere in the plan.

## Supporting Evidence

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Verified-tier:** `LegalOpinion_v1.md` and `ChildDevelopmentReview_v1.md`
(retained professionals); the user's direct clarification history
through **`Clarifications_v22.md`** (Verified-tier as to what was decided
this cycle: the defined trigger point for both hard-gate specialist
reviews; confirmed advice-policy coverage for those two reviews; the
interim dispute-escalation mechanism; the low-end revenue/self-fund
cross-reference; the 60% acquisition checkpoint; the quantified v2-
curriculum trigger; and the explicit, deliberate deferral of the
non-dilutive funding target to research).

**Supported-tier:** three Research House engagements
(`ResearchFindings_v1-3.md`); the user's directly-cited South African
statutory/statistical sources; `BusinessCase_v16.md`'s restored Market &
Competition content. **A fourth Research House engagement
(`TaskOrder_ResearchHouse_v4.md`) is in flight**, addressing the
non-dilutive funding target specifically — its findings are not yet
incorporated and are explicitly excluded from this cycle's scope.

**Assumed-tier, named explicitly:** the candidate motivation-probe and
the candidate data-breach/incident-response commitment (both
Incubator-drafted, neither yet reviewed — both reviews now trigger-
defined, not merely recommended); the 2.0-children-per-family figure
(stated, not derived); the three-tier-to-six-way sub-band reconciliation
draft (Incubator-authored prep work, unreviewed).

**Bounded first-party data:** the n=10 interview round — non-
representative, governed by the standing instruction; the same rule
extends to the pilot's directional demand findings.

**Evidence-chain limitations, updated this cycle:** the self-fund-further
contingency's *sufficiency* and the grant/startup-program fallback's
*actual availability* (specific target) remain untested/unresolved —
explicitly routed to Research House, not resolved by this cycle's
Clarifications. The v2-curriculum trigger is no longer a named limitation
— it is now quantified.

Status remains Complete: the evidentiary base spans Verified-tier user
decisions and retained-professional opinions through Supported-tier desk
research to bounded first-party data and named Assumed-tier candidate
content, with each tier's limits stated, including the explicitly
in-flight fourth Research House engagement.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this cycle (`Clarifications_v22.md`):** specialist-review
trigger point defined for both hard-gate reviews (process only — reviews
themselves have not occurred, see below); advice-policy coverage
confirmed for those two reviews; beyond-48-hour dispute-escalation
mechanism defined (interim placeholder); low-end revenue scenario
cross-referenced against the self-fund-further contingency; acquisition
checkpoint/kill-metric quantified (60%); v2-curriculum "proved demand"
trigger quantified (500 subscribers AND 60% 90-day retention).

**Explicitly NOT resolved this cycle, named and tracked, not
dropped:**

- **Non-dilutive funding target for the R20,000 self-fund ceiling's
  fallback.** Per the user's own decision, no specific program was known;
  routed to Research House (Engagement 4, `TaskOrder_ResearchHouse_v4.md`)
  rather than guessed at. **Remains open until `ResearchFindings_v4.md`
  is delivered and has passed the Incubator's own scrutiny.**

**Open — hard gates, trigger now defined but not yet satisfied:**

- **Specialist review of the candidate motivation-probe** (child-
  development specialist, Expert Roster Entry 2) — trigger: once a stable
  working model exists, before any pilot testing with real families
  begins. Not yet occurred.
- **Specialist review of the candidate data-breach/incident-response
  commitment** (Data-Privacy Practitioner, Expert Roster Entry 5) — same
  trigger. Not yet occurred.

**Still genuinely open, not time-pressured:**

- **Curriculum authorship** (founder vs. engaged designer via the
  zero-marginal-cost advice policy, pending confirmation of that policy's
  *general* scope) — undecided, no longer gating anything before launch.
- **Whether a general retention success criterion, independent of the
  now-quantified v2-curriculum trigger, is still needed in Success
  Criteria** — an explicitly open question raised by this cycle's own
  resolution of required change 6.
- Whether one v2-curriculum threshold being met without the other (e.g.,
  500 subscribers without 60% retention) has a defined consequence — a
  narrow interpretive gap, not currently blocking anything.

**Open — analytical/planning gaps, updated:**

- Whether organic-only acquisition can plausibly reach the 9,150-30,500
  family-install funnel in absolute terms — untested, unbenchmarked; the
  pilot's 60% checkpoint gates the transition decision but does not
  validate the funnel's absolute reachability.
- Success-criteria benchmarks (operational-health 65%, general retention)
  remain placeholders; curriculum-engagement (30%) remains reclassified
  as deferred.
- Post-runway external funding-ask size and form (beyond the R20,000
  self-fund ceiling), including its specific non-dilutive target —
  explicitly out for research.
- MoneyAfrica Kids' unpublished premium price; South Africa-specific
  vendor pricing for Stitch's or Mono's product.
- The user's advice-policy *general* scope/limits (including whether it
  covers curriculum expertise specifically — coverage for the two
  hard-gate reviews is now confirmed, this is the narrower remaining
  question).
- POPIA s14 retention period and deletion trigger; consent-flow
  documentation separation; lightweight parent identity-verification;
  grace-period length and reminder cadence; behavior-input logging/
  verification and grade-input mechanisms for the hybrid bonus.

Status remains Complete: this register's scope is comprehensive
identification and tracking, and every item carries its disposition,
including the seventh required change, which is tracked as explicitly
deferred to a named vendor engagement rather than silently dropped.

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**"Complete" definition, unchanged, applied consistently:** a section is
Complete when every material question within its scope has a made
decision — resolved, adopted, or a deliberate, documented residual-risk
acceptance — and anything still open is a tracked implementation detail,
build-spec parameter, or externally-gated recheck carrying a named owner
and (where launch-relevant) a decided fallback. A section carrying an
undecided specialist recommendation or an unmade material decision is
Partial. For register-type sections (Risks, Outstanding Questions),
Complete means comprehensive identification with a recorded disposition
per item.

**This cycle's central question, stated plainly per the delegation
instruction: does resolving six of Verdict_v6.md's seven required
changes move the score, and by how much? Answer: no, it does not move.
The score is unchanged at 94/130 = 72.3% (or 91/130 = 70.0% under the
disclosed conservative reading), identical to v21.**

**Why the score does not move, argued explicitly, section by section:**

- **Success Criteria (Partial):** the 60% kill-metric correction resolves
  one specific vagueness, but operational-health (65%, no benchmark) and
  a general retention figure remain unset — material questions within
  this section's own scope stay open, so the section stays Partial.
- **Stakeholders (Partial):** the specialist-review trigger is now
  defined, but "trigger defined" is explicitly not "review occurred" — the
  two named reviews remain the section's own material open questions,
  unresolved.
- **Validation Strategy (Partial):** the acquisition checkpoint closes one
  specific "no validation plan" finding, but pricing/conversion
  validation, account-linking UX validation, and the no-Mpoints fallback
  engagement-loop validation remain open.
- **Revenue & Costs / Financial Considerations (both Partial):** the
  low-end stress-test cross-reference and confirmed advice-policy
  coverage improve internal consistency, but the funding-ask size
  (including the now-explicitly-deferred non-dilutive target) and
  break-even analysis remain absent — material questions unresolved.
- **Assumptions (Partial):** two assumptions are resolved this cycle, but
  several load-bearing assumptions (children-per-family, self-fund-cap
  sufficiency, organic-only sufficiency) remain untested.
- **Constraints, Operations, Roadmap, Risks (already Complete):** this
  cycle's resolutions strengthen these sections' already-Complete status
  (dispute-escalation resolved; cross-references added; triggers defined)
  without altering it — a section already scored Complete cannot score
  higher than Complete.
- **Curriculum Design (extension, already Complete via a disclosed
  judgment call):** the quantified trigger strengthens the argument for
  this section's Complete status (one of the two previously-open
  sub-questions — trigger definition — is now closed, leaving only
  authorship open, analogous to the SARB/FPB "owned, timed, fallback"
  pattern already used elsewhere in this document) but does not change
  its already-Complete score.
- **No section crosses from Partial to Complete, and none crosses from
  Complete to Partial.** The seventh required change (non-dilutive
  funding target) was never itself a scored line item in this table — it
  is a sub-question within Constraints and Financial Considerations, both
  of which already accounted for it as an owned, timed, decided-fallback-
  category item consistent with the SARB/FPB pattern. Leaving it
  explicitly open for research therefore does not newly threaten either
  section's status, but it also does not newly resolve anything that
  would raise a score.

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted.

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
| Curriculum Design (extension) | Complete | 1x | 5 |
| Child Data & Consent (extension) ★ | Complete | 2x | 10 |

Points earned: **94**. Points possible = 22 non-critical sections × 5 =
110, plus 2 critical sections × 5 × 2 = 20. **Total possible = 130.**

**Readiness Score = 94 / 130 = 72.3%.** Unchanged from v21. Clears the
completion gate's ≥70% threshold with a 2.3-point margin.

**Conservative alternative, withholding the Curriculum Design judgment
call (i.e., leaving it Partial = 2 pts):** 91/130 = **70.0%** — unchanged
from v21, still clears the threshold, with no margin.

No section is Critical + Incomplete: both Legal & Compliance and Child
Data & Consent are Complete.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) → 52%
(v13) → 52% (v14) → 52% (v15) → 52% (v16) → 70% (v17) → 70% (v18) → 70%
(v20, later found to have been honestly 67.7% by `Verdict_v5.md`'s own
arithmetic) → 72.3% (v21, or 70.0% conservative) → **72.3% (v22, or 70.0%
conservative) — unchanged. Six of seven required changes resolved this
cycle without moving the score; this is stated plainly as an accurate
result, not a shortfall — process/consistency fixes and quantifications
that don't themselves close a section's remaining material questions are
not expected to move a status-based score, and this document does not
inflate the narrative to suggest otherwise.**

### Critical Gaps

1. **Execution capacity — bounded contingency, now with one additional
   named demand.** R10,000 total development budget plus a 6-month
   runway must contain the build, an instrumented pilot (behind two
   trigger-defined specialist-review gates, neither yet satisfied), two
   regulatory rechecks, and now manual founder review of any dispute
   unresolved beyond 48 hours — executed substantially by one person.
   Self-fund-further contingency: R20,000 total hard ceiling, explicitly
   the mechanism triggered if Year-1 revenue lands at the low end of the
   range; grant/startup-program funding is the stated fallback category,
   with the specific target unresolved (see Gap 11).
2. **SARB/National Payment System Act open-banking question** — owned and
   fallback-protected, still externally unsettled. Owner: the user, at
   build-spec stage; fallback: launch without account-linking.
3. **FPB classification question over Mpoints** — owned and
   fallback-protected, still externally unsettled. Owner: the user, at
   build-spec stage; fallback: launch without Mpoints.
4. **Market demand remains directionally evidenced only**, against a
   corrected, smaller funnel. The n=10 standing instruction holds; the
   pilot's demand read will be directional/qualitative. Whether
   organic-only acquisition can plausibly reach the 9,150-30,500
   family-install funnel in absolute terms remains untested; the pilot's
   60% completion criterion now checkpoints the transition decision
   specifically, not the funnel's absolute reachability.
5. **Success-criteria benchmarks remain partial placeholders.**
   Operational health (65%) carries no external benchmark; a general
   retention figure has no proposed value (a distinct 60% 90-day figure
   exists but is scoped to the v2-curriculum trigger only). Curriculum
   engagement (30%) remains reclassified as deferred.
6. **Two specialist reviews now have a defined trigger, neither yet
   satisfied.** Trigger: once a stable working model exists, before any
   pilot testing with real families begins — the same trigger used for
   the retained legal opinion. Both remain Evidence: Assumed until the
   reviews actually occur.
7. **Legal/build tasks pending, unchanged.** POPIA s14 retention period
   and deletion trigger; consent-flow documentation separation;
   lightweight parent identity-verification.
8. **Exam-bonus residual risk — accepted, candidate-instrumented, review
   trigger-defined but not yet obtained.**
9. **NEW/NAMED this cycle, explicitly NOT resolved: the non-dilutive
   funding target for the R20,000 self-fund ceiling's fallback.** Routed
   to Research House (Engagement 4, `TaskOrder_ResearchHouse_v4.md`), not
   guessed at. Genuinely open until `ResearchFindings_v4.md` is delivered
   and reviewed.
10. **RESOLVED this cycle, retained for audit-trail continuity:**
    specialist-review trigger point defined (process, not outcome);
    advice-policy coverage confirmed for the two named reviews;
    dispute-escalation beyond 48 hours resolved via an interim mechanism;
    low-end revenue scenario cross-referenced against the self-fund
    contingency; acquisition checkpoint/kill-metric quantified (60%);
    v2-curriculum trigger quantified (500 subscribers AND 60% 90-day
    retention).
11. **Resolved in prior cycles, retained for audit-trail continuity:**
    self-fund-further contingency bounding (R20,000 total); curriculum
    MVP-scope deferral; schools-partnership explicit deferral;
    child-to-family population-conversion gap; all original specialist
    design decisions; the Conradie v Rossouw citation; recheck
    ownership/timing/fallbacks; pilot scope; cost/runway structure.

## Operations — Curriculum Design (Domain Extension)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (reconciliation draft: Assumed; authorship: Unknown)

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs, even where the curriculum feature
itself is deferred.*

**Scope decision, unchanged from v21:** curriculum/educational content,
including the 15-18-only "Fintech Advance" module, is deferred in its
entirety to a post-launch v2 feature.

**Trigger — QUANTIFIED this cycle (`Verdict_v6.md` required change 6,
`Clarifications_v22.md`), replacing the previously undefined "proved
demand" phrase directly.** Both a subscriber-count AND a retention-rate
threshold must be met: **500 paying subscribers AND 60% 90-day
retention** — both conditions required before curriculum work begins, a
conservative dual-gate design chosen specifically to avoid investing in
curriculum for a subscriber base that has not demonstrated it sticks
around. **This closes the previously-named v2-trigger-criterion risk**
(see Risks) and strengthens the basis for this section's Complete status:
of the section's two originally-open material questions (is curriculum in
scope; what triggers v2 and who authors it), the trigger half is now
closed, leaving only authorship open — the same "owned, timed/triggered,
with fallback" pattern this document already uses to keep other sections
at Complete despite open external questions.

Carried forward, unchanged: the age floor of 6 is intentional; the
curriculum is conceived as a short course completable daily or weekly;
two example mechanics (currency differentiation; "word sums"); "Fintech
Advance" as the distinct 15-18-only element (gamification-avoidance
decided, risk-literacy framing adopted).

**Three-tier age framework — adopted, unchanged:** early childhood
(roughly 6-9, softened task/reward framing); pre-teen (roughly 10-14,
basic transactional literacy); teens (roughly 15-18, pre-employment
literacy).

**Three-tier-to-six-way sub-band reconciliation — unchanged from v21,
still prep work, not adopted.** Incubator-authored, Evidence: Assumed,
unreviewed by the child-development specialist; does not itself resolve
anything or count toward this section's Complete status. Three resolution
options remain drafted for eventual specialist review: (a) fold the 9-10
band into the pre-teen tier for curriculum purposes specifically
(Incubator's draft recommendation); (b) fold the 9-10 band into the
early-childhood tier; (c) split content within the 9-10 band by exact age
(not recommended).

**Authorship — remains genuinely undecided, no longer time-pressured,
unchanged.** The user has not decided between authoring the curriculum
personally or engaging a curriculum designer via the zero-marginal-cost
advice policy, pending confirmation that the policy's *general* scope
extends to instructional-design expertise (a narrower open question this
cycle, since coverage for the two hard-gate specialist reviews is now
confirmed). `CurriculumDraft_v1.md` remains available as an earlier,
unreviewed/unadopted starting point.

**Still open, tracked as v2-phase items, not launch-blocking:**
instructional format, standards alignment, and content itself; the
conditional 6-9-tier immediate-feedback replacement under the no-Mpoints
fallback; the 30% curriculum-engagement success benchmark (deferred
alongside the feature); the narrow interpretive gap of what happens if
one v2 trigger threshold is met without the other.

Status: Complete, unchanged from v21, on a strengthened basis — the
trigger-quantification closes half of the section's two originally-open
material questions, leaving only authorship open under a pattern this
document already treats as compatible with Complete status.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Directly and substantially addressed by `LegalOpinion_v1.md` Q2 and Q3,
unchanged. The universal parent-consent gate is confirmed legally
sufficient as designed under POPIA s34/s35(1)(a). Two hardening
recommendations remain named build tasks: consent-flow documentation
separation; a lightweight parent identity-verification step.

POPIA Section 14 retention is confirmed to require an affirmatively
designed, specific retention period and deletion trigger — a named,
pending build task.

**A minimal data-breach/incident-response commitment (see Constraints)
directly extends this section's scope. Specialist (Data-Privacy
Practitioner) review now has a DEFINED trigger this cycle
(`Clarifications_v22.md` required change 1): once a stable working model
exists, and before any pilot testing with real families begins — the
same trigger already used for the retained legal opinion. Stated
plainly: this defines when the review occurs, not that it has occurred.
It has not yet occurred.** It is an Incubator-drafted candidate (Evidence:
Assumed), specifying what constitutes a breach, who is notified (parents;
the Information Regulator, per POPIA s22), and a notification timing
standard consistent with POPIA's "as soon as reasonably possible"
language. The commitment must not be in force, and real children's data
must not be collected at pilot, until this review has actually occurred.

Platform-policy items, unchanged: Google Play's Families Policy
loyalty-point disclosure requirement applies to the primary configuration
and is mooted under the no-Mpoints fallback; Apple's Kids Category
IAP-currency question is deferred with iOS and likewise mooted under that
fallback.

Status remains Complete: the section's central questions — consent-model
sufficiency and retention approach — are directly answered by retained
counsel; the breach commitment is an additive strengthening whose review
now carries a defined trigger rather than an open-ended intention, still
a hard gate rather than an unresolved central question of the section's
own original scope.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Complete.
- Readiness Score ≥ 70%: **Yes — PASSES.** Score is unchanged from v21:
  94/130 = 72.3% under the primary computation, or 91/130 = 70.0% under
  the disclosed conservative alternative. The case clears 70% under both
  readings.
- **Expert roster entries ≥3 sentences, each naming a specific
  case-study assumption:** see `ExpertRoster.md`, regenerated this cycle,
  six entries.
- **Devil's Advocate objections ≥3, each citing a specific section:** see
  `reviews/DevilsAdvocate.md`, regenerated this cycle, five objections.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.
- No section consists solely of an "Unchanged from vN, not reproduced"
  pointer: **Yes.** Every section contains its own full, substantive,
  self-contained text this cycle.

**This Business Case passes its own completion gate.** Six of the
Investment Committee's seven required changes from `Verdict_v6.md` are
resolved: the specialist-review trigger is defined (not yet satisfied);
advice-policy coverage is confirmed for both named reviews;
dispute-escalation beyond 48 hours has an interim mechanism; the low-end
revenue scenario is cross-referenced against the self-fund-further
contingency; the acquisition checkpoint/kill-metric is quantified at 60%,
correcting the prior vague language; and the v2-curriculum trigger is
quantified at 500 subscribers AND 60% 90-day retention, correcting the
prior undefined phrase. **The seventh required change — a concrete
non-dilutive funding target — is explicitly and deliberately NOT resolved
this cycle**, routed to Research House rather than guessed at, and
remains a named open item in Critical Gaps and Outstanding Questions.
**The Readiness Score is unchanged at 94/130 = 72.3% (or 91/130 = 70.0%
conservative)** — this cycle's resolutions are genuine process and
consistency improvements that do not, on their own terms, close any
section's remaining material open questions sufficiently to change its
status. Genuine open items remain — detailed in Critical Gaps — led by
execution capacity (now carrying one additional named demand), two
externally-unsettled regulatory questions, two trigger-defined but
not-yet-obtained specialist reviews, and the explicitly deferred
non-dilutive funding target.
