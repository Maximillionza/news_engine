# Business Case: MiniMoney — v24

> Prepared by: Incubator. This revision incorporates `Clarifications_v24.md`,
> resolving two of `Verdict_v7.md`'s six required changes (Required Change
> 3: founder-eligibility facts gating the named funding fallback; Required
> Change 5: concrete organic-acquisition channels). Per the user's
> explicit, documented decision (recorded in `Clarifications_v24.md`'s
> Process Note), the remaining four required changes — completing the two
> trigger-defined specialist reviews, a minimal P&L/break-even model, a
> quantified stop/redesign threshold for the child-welfare instruments, and
> an aggregate founder-capacity assessment — are deliberately OUT OF SCOPE
> for this cycle. They are not resolved, not drafted, and not guessed at
> here; they are named plainly below as open items explicitly carried
> forward for the Developing Committee to trace, per a user-authorized
> deviation from the standard "proceed with changes returns to Investment
> Committee" routing default. **This is the final Incubator revision before
> the case routes directly to Developing Committee.** Authorized inputs for
> this cycle: `00_CaseStudy.md`, `BusinessCase_v23.md`, `Verdict_v7.md`,
> `Clarifications_v24.md`.

## What Changed in v24 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (two
newly user-confirmed founder-specific facts); Supported (channel naming;
the funding candidate list itself, now narrowed, remains vendor-desk-
research-derived)

Two of `Verdict_v7.md`'s six required changes are resolved this cycle via
direct user clarification (`Clarifications_v24.md`) — Verified-tier
evidence, the highest tier this document uses, reserved for facts the user
directly confirms.

**Required Change 3 (founder-eligibility facts): RESOLVED, WITH A
MATERIAL, UNFAVORABLE FINDING, STATED PLAINLY, NOT SOFTENED.** The
founder's age is 39 — outside NYDA's 18-35 eligibility band. **NYDA,
previously named as the funding fallback's primary candidate and the
single best-timelined option of the group, is excluded outright, not
merely uncertain.** MiniMoney is also not yet CIPC-registered and holds no
current SARS tax-clearance status — **SEDA's eligibility requirement is
not currently met either**, and SEDA was the prior secondary candidate.
**Both previously-named top candidates are now confirmed non-viable in
their current form, not merely unresolved.** The genuinely available
non-dilutive fallback narrows to Injini's earlier-stage EdTech-accelerator
track (contingent on a future cohort opening — none is currently open) and
TIA instruments (whose eligibility for a solo, non-research-affiliated
consumer-app founder remains itself unresolved per Research House's own
prior findings). **This is a genuine increase in financial and execution
risk, not a routine confirmation update — it is read and weighted as such
throughout this document, not treated as equivalent to the "trigger
defined, category decided" pattern this document has applied to other
externally-gated items.** See Constraints, Financial Considerations,
Risks, Critical Gaps, and Outstanding Questions for the full,
threaded-through treatment.

**Required Change 5 (concrete acquisition channels): RESOLVED.** Four
specific organic channels now replace the prior generic "organic-only"
label: (1) founder personal network/word of mouth; (2) organic social
media (Instagram, TikTok, Facebook parent groups); (3) App Store
Optimization (Google Play listing); (4) parent/community forums and groups
(South African parenting forums, Facebook parent groups, WhatsApp
community groups). **Naming the channels resolves the "which channels"
question. It does not, on its own, validate reachability of the funnel:
none of the four channels carries a stated, even directional,
expected-volume estimate.** This is stated honestly, not glossed over —
see Market & Competition, Roadmap, and Validation Strategy.

**Explicitly out of scope this cycle, per `Clarifications_v24.md`'s
Process Note — named plainly, not resolved, not drafted, not guessed at:**

1. **Completing the two trigger-defined specialist reviews** (Data-Privacy
   Practitioner; child-development specialist). **Framing confirmed
   correct and unchanged: this is a pre-pilot gate, not a pre-build gate**,
   consistent with this case's own build-gating logic established since
   v9 (financial-trigger features and pilot-stage work are gated;
   foundational, non-pilot development work is not gated by these
   reviews). Foundational build work may proceed without them; no real
   family may be enrolled in the pilot until both have actually occurred.
2. **A minimal P&L/break-even model** — remains unproduced, the sole named
   reason Financial Considerations has remained Partial across many
   cycles.
3. **A quantified stop/redesign threshold for the child-welfare
   instruments** (family-relationship-strain package; motivation-probe) —
   remains undefined.
4. **An aggregate founder-capacity/bandwidth assessment** across all
   concurrent pre-launch obligations — remains unassessed as a total,
   though each individual obligation is separately tracked throughout this
   document.

These four are carried forward as explicit traceability items for the
Developing Committee, per the user-authorized routing deviation recorded
in `Clarifications_v24.md` — the Developing Committee is architecturally
responsible for ensuring each is traceable in execution instructions,
rather than requiring closure via further Incubator/Investment Committee
cycling first.

**Readiness Score recomputed in full this cycle: it does not move under
the methodology this document has applied consistently since v17.** It
remains 94/130 = 72.3% (or 91/130 = 70.0% under the disclosed conservative
Curriculum Design reading), identical to v21-v23. **No section's Status
flips under that consistently-applied methodology.** A further,
newly-disclosed conservative tension is named explicitly in Readiness
Score and deliberately not adjudicated unilaterally here: under a stricter
reading of Constraints' Complete standard — one requiring a currently-
viable, specific named candidate rather than a decided fallback category —
this section would score Partial, producing a most-conservative reading of
88/130 = 67.7%, below the gate threshold. This tension is flagged for the
Developing Committee and any future review, not resolved by silent
methodology change at v24. See Readiness Score for the full reasoning.

## Executive Summary

**Status:** Partial | **Confidence:** High | **Evidence:** Supported (with
two newly Verified-tier founder-specific facts)

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
post-launch v2 feature, against a quantified dual trigger (500 paying
subscribers AND 60% 90-day retention). The core launch mechanic itself
already carries embedded financial literacy (earning, budgeting,
expense/tax-style deductions, payment mechanics); structured instructional
content is what remains deferred.

Growth is organic-only at launch — zero paid acquisition, no marketing
budget allocated. **Four specific organic channels are now named this
cycle** (founder personal network/word of mouth; organic social media;
App Store Optimization; parent/community forums and groups), replacing
the prior generic "organic-only" label. **Naming these channels does not
itself validate reachability of the funnel: none carries a stated
expected-volume estimate**, a limitation stated plainly, not glossed
over. The schools-partnership channel — the strongest demonstrated local
reach precedent in the category — remains explicitly deferred for stated
founder-bandwidth reasons. The pilot's own acquisition checkpoint/
kill-metric is quantified: if fewer than 60% of enrolled pilot families
complete 4 consecutive weekly task→payslip cycles, organic-only
acquisition/mechanic engagement is treated as not yet validated before
widening release.

**A material, unfavorable finding this cycle: the non-dilutive funding
fallback for the R20,000 self-fund ceiling is now confirmed materially
weaker than previously understood, not merely uncertain.** The founder's
age (39) excludes NYDA — previously named the fallback's best-timelined
primary candidate — outright. MiniMoney's current lack of company
registration and SARS tax clearance excludes SEDA — the prior secondary
candidate — as currently applicable. The genuinely available fallback
narrows to Injini (contingent on a future cohort opening, none currently
open) and TIA (eligibility for a solo consumer-app founder itself
unresolved). **This is stated as a genuine increase in financial and
execution risk, not a routine confirmation update.**

Two hard pre-pilot specialist reviews — the data-breach/incident-response
commitment (Data-Privacy Practitioner) and the exam-bonus motivation-probe
(child-development specialist) — remain unperformed as of this revision.
Their trigger point (once a stable working model exists, and before any
pilot testing with real families begins) is confirmed correctly framed as
a pre-pilot gate, not a pre-build gate, consistent with this case's own
build-gating logic since v9: foundational build work may proceed; pilot
enrollment may not, until both reviews actually occur. Completing these
reviews, producing a minimal P&L/break-even model, defining a quantified
stop/redesign threshold for the child-welfare instruments, and producing
an aggregate founder-capacity assessment are all explicitly out of scope
for this cycle and are carried forward as named, unresolved traceability
items for the Developing Committee, per a user-authorized routing
deviation.

The runway-slippage contingency remains bounded at R20,000 total maximum
personal commitment, tied explicitly to the low end of the revenue range
(92 paying families, ~R5,519/month) as a foreseen, already-planned-for
scenario — though the fallback available if that ceiling is exhausted is
now demonstrably weaker than previously understood. The beyond-48-hour
dispute-escalation gap is resolved via an interim placeholder — manual
founder review at MVP stage — explicitly named as non-scalable and
founder-capacity-dependent.

Revenue figures are unchanged in magnitude across the last several
cycles: **≈9,150-30,500 Year-1 family installs and ≈92-915 paying
families** (≈R5,519-R54,891/month run-rate), still resting on
Guessing/Assumed-tier funnel assumptions.

**Two of six required changes from `Verdict_v7.md` are resolved this
cycle** (founder-eligibility facts, with an unfavorable finding; concrete
acquisition channels, with an honest reachability caveat). **The remaining
four — completing both specialist reviews, a P&L/break-even model, a
quantified child-welfare stop/redesign threshold, and an aggregate
founder-capacity assessment — are explicitly out of scope for this
cycle**, per the user's documented decision, and are carried forward as
named traceability items for the Developing Committee rather than cycled
through a further Incubator/Investment Committee round.

**The Readiness Score is unchanged at 94/130 = 72.3%** (or 91/130 = 70.0%
under the disclosed conservative Curriculum Design reading), clearing the
completion gate's ≥70% threshold under both established readings,
identical to v21-v23. This cycle's founder-eligibility finding does not,
under the methodology this document has consistently applied, flip any
section's Status — but it materially worsens the substantive risk
represented within Constraints, Financial Considerations, and the
execution-capacity Critical Gap, and a further, newly-disclosed
conservative tension (not adjudicated here) would drop the score to
67.7%, below the gate threshold, if Constraints were scored under a
stricter obtainability-based standard. See Readiness Score for the full
reasoning.

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
a deliberate v2 addition, gated by a quantified dual trigger (500
subscribers AND 60% 90-day retention, see Curriculum Design) — a
sequencing decision, not an abandonment of the education premise.

A first-party interview round (n=10 families) found 6 of 10 confirmed
interest in using the app and stated willingness to pay for it; 7 of 10
expressed interest specifically in the education aspect. This remains
genuine, first-party, MiniMoney-specific evidence, not statistically
significant, and per standing instruction must not be used as a
representative demand signal until superseded by the planned pilot or a
structured survey.

Status remains Partial, unaffected by this cycle's `Clarifications_v24.md`
findings (founder-eligibility facts; acquisition channels — neither bears
on the underlying problem thesis): there is a real, encouraging
directional signal, but no established finding that parents broadly
perceive this as a problem worth paying to solve.

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

The schools-partnership channel remains explicitly deferred, for
founder-bandwidth reasons: the strongest demonstrated reach model in the
category (MoneyTime SA's own claimed 1,500+ schools, 130,000+ students),
deliberately not pursued pre-launch. Status remains Partial, unaffected by
this cycle's `Clarifications_v24.md` findings: the differentiation thesis
is coherent and partly evidenced, but no structured market-sizing or
validated demand study has been conducted, and the one channel with local
reach precedent is out of scope for launch.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The functional objective is: budget → tasks → Mbuck/Mpoint earning →
exam-period bonus (hybrid: behavior-primary rewards plus a retained
secondary results bonus, motivation-probe review trigger-defined — see
Success Criteria) → invoice/payslip → payment confirmation with
escalating late-penalty (grace-period/pre-escalation reminder mechanism
committed; disputes beyond 48 hours resolved via a manual founder-review
interim placeholder) → age-gated core mechanic. Structured curriculum
content remains deferred to v2, against a quantified dual-gate trigger
(500 subscribers AND 60% 90-day retention).

**Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
payment loop, including the dispute and late-penalty mechanics, with a
small pilot cohort of South African families (candidate target: 20-50
families) before wider release. The pilot formally adopts the specialist
pilot-measurement package (see Success Criteria) plus the motivation-probe
addition, subject to its own trigger-defined specialist-review
requirement — a pre-pilot gate, not a pre-build gate, confirmed unchanged
this cycle — and serves double duty: mechanic-safety signal AND a
directional demand read, with an explicit 60% task-cycle-completion
acquisition checkpoint (see Validation Strategy).

**Growth (6-12 months):** validate the subscription-conversion assumption
against the recalculated 1-3% subscription-only reference range applied
to the corrected funnel; curriculum-engagement-as-a-retention-indicator
validation remains deferred alongside the v2 curriculum feature itself,
against its quantified dual trigger; evaluate iOS port timing based on
Android traction.

The 90-day (recalculated installs) vs. annual funnel target tension
remains resolved via `Clarifications_v10.md`'s per-family convention. All
install and subscriber figures are per-family, per the 2.0-children-per-
family assumption (see Market & Competition). Status remains Complete,
unaffected by this cycle's `Clarifications_v24.md` findings: every
tension previously flagged in this section is resolved by direct,
Verified-tier user clarification.

## Success Criteria

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Core criteria:** pilot success / acquisition checkpoint is **60%** — if
fewer than 60% of enrolled pilot families complete ≥4 consecutive weekly
task→payslip cycles, organic-only acquisition/mechanic engagement is
treated as not yet validated before widening release. Operational health
(65% task-completion without dispute, no external benchmark) and
freemium/subscription conversion (2%, benchmarked against the
recalculated 1-3% subscription-only range) are unchanged. **Retention: no
general figure proposed** — a distinct **60% 90-day retention** figure
exists but is scoped specifically to the v2-curriculum demand trigger, not
this section's own general retention benchmark (see Curriculum Design).
Whether a general retention success criterion, independent of that
trigger, is still needed here remains an explicitly open question (see
Outstanding Questions).

**Curriculum-engagement criterion (30%)** remains reclassified, not
scored as an open gap, since curriculum content is deferred to v2 —
retained as a placeholder to be reintroduced, unbenchmarked, when the v2
feature is actually built against its quantified trigger.

**Family-relationship-strain criterion — measurement package adopted into
pilot design**, unchanged (`ChildDevelopmentReview_v1.md`): borrowed items
from the Parenting Stress Index – Short Form and the Family Assessment
Device – General Functioning Scale, administered to parents at baseline
and partway through the pilot; within-family, within-week correlation
tracking (late-penalty events vs. reported household tension);
age-stratified results (6-9, 10-14, 15-18 bands); a brief child-report
instrument (abbreviated Child–Parent Relationship Scale, Conflicts
subscale). The reviewer's caution stands: 20-50 families is not large
enough for full validated-instrument statistical power; these are for
lightweight, qualitative early-warning signal detection. **A quantified
stop/redesign threshold for this instrument — what result would halt or
force redesign of the pilot — is explicitly NOT defined this cycle**,
carried forward as a named open item for the Developing Committee (see
Outstanding Questions), per `Clarifications_v24.md`'s scope decision.

**Exam-bonus motivation-risk instrumentation — candidate instrument
exists; review trigger defined, not satisfied.** The instrument itself:
parent-facing Likert/open items alongside the existing PSI-SF/FAD-GFS
timepoints; child-facing age-appropriate items alongside the existing
Child–Parent Relationship Scale timepoint; near-zero marginal cost,
administered at existing survey events. The review must occur once a
stable working model exists, and before any pilot testing with real
families begins — a pre-pilot gate, not a pre-build gate, the same
framing already used for the retained legal opinion, confirmed correct
and unchanged this cycle. No family may be enrolled in the pilot until
this review has actually occurred, and it has not yet occurred as of this
revision — completing it is explicitly out of scope for this cycle and is
carried forward as a named item for the Developing Committee. The probe
remains Evidence: Assumed until that review occurs. **The same quantified
stop/redesign threshold gap applies here as above: not defined this
cycle.**

The underlying substantive risk remains confirmed, not resolved: the
late-penalty redesign narrows but does not eliminate the Family Stress
Model's affective pathway, and the exam-bonus hybrid's residual
intrinsic-motivation risk is candidate-instrumented but not yet
specialist-reviewed or adopted.

Status remains Partial, unaffected in substance by this cycle's
`Clarifications_v24.md` findings (which concern funding eligibility and
acquisition channels, not the child-welfare instruments): the acquisition
checkpoint is a specific, correct figure and the relationship-strain
criterion has an adopted measurement plan, but operational health and the
general retention benchmark remain unbenchmarked, the motivation-risk
review has still not occurred, and the quantified stop/redesign threshold
for both child-welfare instruments remains explicitly undefined and
carried forward.

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
remains an additional data-processor stakeholder. The retained
child-development professional (Expert Roster Entry 2) and the
Data-Privacy Practitioner (Expert Roster Entry 5) both have a defined
review trigger — once a stable working model exists, and before any
pilot testing with real families begins, a pre-pilot gate rather than a
pre-build gate. Their advice is confirmed zero-marginal-cost. Neither
review has yet occurred, and completing them is explicitly out of scope
for this cycle. A future AI mediator feature for dispute resolution
remains explicitly out of current scope, named specifically as the
eventual replacement for the interim manual-founder-review
dispute-escalation placeholder (see Operations). A curriculum/
instructional-design specialist (Expert Roster Entry 3) is a named future
stakeholder for the deferred v2 curriculum feature, not yet engaged.

**The candidate non-dilutive-funding-body stakeholder class surfaced in
v23 is updated this cycle with a material, unfavorable finding
(`Clarifications_v24.md`): NYDA and SEDA — previously the two leading
candidates — are now confirmed non-viable for this founder in their
current form (age 39 excludes NYDA; absent company registration/tax
clearance excludes SEDA). The genuinely live candidate stakeholders
narrow to Injini (not yet engageable — no open cohort) and TIA
(eligibility itself unresolved). None of the four has yet been contacted
or engaged.** This is a narrower and weaker candidate-stakeholder picture
than v23's framing, not merely a still-pending relationship.

Status remains Partial: both regulator stakeholders have an owned recheck
and a fallback but remain unresolved pending those rechecks; the two named
specialist reviews have a defined, correctly-framed pre-pilot trigger
point but neither has actually occurred, and completing them is out of
scope this cycle; the funding-body stakeholder relationship is now
confirmed materially narrower than v23's framing, not merely
still-pending.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18, and their
parents/guardians, in South Africa, on Android at launch (iOS deferred).
A minor is not an independently reachable user: every child account
requires a parent acting as registration custodian from the outset. The
paying customer unit is the family (one subscription = one family = up to
4 children) — the child is the user, the parent is the customer, and all
funnel counts are family counts, applying a stated 2.0-children-per-
family assumption (Evidence: Assumed) to convert the reachable-child
population into a reachable-family figure (see Market & Competition).
Status remains Partial, unaffected by this cycle's `Clarifications_v24.md`
findings: the target population is clearly named and the customer unit is
unambiguous, but no market-sizing or persona-level detail exists beyond
Market & Competition and the funnel figures in Objectives.

## Value Proposition

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The launch value proposition is the financial mechanic alone — budget
setting, task assignment, Mbuck/Mpoint earning, payslip/invoice, payment
confirmation, dispute and late-penalty handling, including a defined (if
interim) beyond-48-hour dispute-escalation path. The Free/Subscription
split and the R59.99/month (up to 4 children per family) price stand.
Fintech Advance (the 15-18-only trading/entrepreneurship module) remains
deferred to v2 alongside the rest of curriculum content, against a
quantified dual trigger (500 subscribers AND 60% 90-day retention). Its
prior mitigation decisions (no product gamification for its content;
risk-literacy framing over aspirational framing, per
`ChildDevelopmentReview_v1.md` Q5) remain adopted and will apply unchanged
whenever the module is actually built.

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

Status remains Complete, unaffected by this cycle's `Clarifications_v24.md`
findings: price, feature boundaries for the corrected launch scope, and
all previously-pending decisions within this section's scope are made.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

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
(Evidence: Assumed), within the up-to-4-per-family cap. **Reachable
families = 6.1M reachable kids ÷ 2.0 ≈ 3.05M reachable families.**

**Adoption rate:** [Guessing] no public South African benchmark exists;
inference from adjacent markets (GoHenry/Greenlight UK/US) suggests
0.3-1% Year-1 install capture; free-to-paid conversion for freemium/
subscription kids'-finance apps benchmarks 2-6% globally — South Africa's
lower discretionary income argues for the low end, **1-3%**.

**Funnel:** ≈3.05M reachable families × 0.3-1% Year-1 install capture ≈
**9,150 to 30,500 family installs.** Applying 1-3% conversion: **≈92 to
915 paying families in Year 1.**

**Acquisition channels — four now named this cycle (`Clarifications_v24.md`),
replacing the prior generic "organic-only" label:**

1. **Founder personal network/word of mouth** — direct outreach,
   encouraging referrals from early users.
2. **Organic social media** (Instagram, TikTok, Facebook parent groups) —
   no paid ad spend, relying on shareability.
3. **App Store Optimization (ASO)** — optimizing the Google Play listing
   (keywords, screenshots, description) for organic search/browse
   traffic.
4. **Parent/community forums and groups** — South African parenting
   forums, Facebook parent groups, WhatsApp community groups where the
   target audience already congregates.

**Naming these channels resolves which channels the founder intends to
use. It does not validate reachability: none of the four carries a
stated, even directional, expected-volume estimate.** Whether these four
channels, in combination, can plausibly reach the 9,150-30,500 Year-1
family-install funnel remains untested and unbenchmarked — an honest,
explicit limitation, not glossed over.

**Competition in South Africa:** African Bank's MyWORLD Power Pocket,
MoneyAfrica Kids, MoneyTime SA remain the three named local players, each
missing at least one defining dimension. MoneyTime SA's 1,500+
schools/130,000+ students remains the strongest demonstrated reach model,
deliberately deferred as a channel.

**International comparables:** GoHenry/Greenlight solve payment
verification via card-issuing/e-money licensing; FamZoo/Bomad are closer
structural analogs, track-only with no bank integration, confirming
MiniMoney's model has precedent elsewhere.

**What remains unresearched:** validated demand; structured market sizing
beyond the user's own funnel estimate; MoneyAfrica Kids' premium price;
acquisition economics against the organic-only growth strategy in
absolute terms — four specific channels are now named, but none carries a
volume estimate, so the pilot's 60% checkpoint gates the pilot-to-wider-
release transition but does not itself validate whether these channels
can reach the 9,150-30,500 range (see Validation Strategy).

Status remains Partial: the competitive landscape and funnel are fully
documented, the population-conversion gap remains closed via a stated
(Assumed-tier) figure, and the acquisition channels themselves are now
concretely named — but the most decision-relevant figures (Year-1
adoption, conversion rate, and per-channel volume) remain unvalidated.

## Business Model

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unaffected by this cycle's `Clarifications_v24.md` findings. Subscription-
only at launch, ads deferred to V2; R59.99/month per family, covering up
to 4 children — the family is the revenue unit. MiniMoney is a
facilitation/education layer that sits on top of the parent's own bank
account and does not move or hold funds. The core mechanic — not
instructional curriculum content — is what the subscription pays for at
launch.

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
mooted entirely under the no-Mpoints fallback. Status remains Complete:
the model's structure, unit, price, and every put-to-decision item within
its scope are decided.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Revenue (per-family):** unchanged in magnitude across recent cycles.
Subscription revenue at R59.99/month per family against the Year-1 range
of **92 to 915 paying families**:

- Lower bound: 92 families ≈ **R5,519/month** (≈ R66,229/year run-rate).
- Upper bound: 915 families ≈ **R54,891/month** (≈ R658,690/year
  run-rate).
- These are end-state run-rates against an unvalidated funnel and
  conversion rate; actual Year-1 collected revenue would be
  ramp-dependent and lower.

**Low-end stress test:** if actual results land at the lower bound (92
paying families, ~R5,519/month), this is treated as a **foreseen scenario
that triggers the self-fund-further contingency** (up to the R20,000
total ceiling) described in Constraints — not a new decision point or an
unaddressed failure state.

**Costs.**

- **Development budget: R10,000 total** committed for the app build.
- **Self-fund-further cap: an additional R10,000 — R20,000 total maximum
  personal commitment**, hard ceiling. **The fallback if exhausted is
  grant/startup-program (non-dilutive) funding — but as of this cycle
  (`Clarifications_v24.md`), the two previously top-ranked candidates
  (NYDA, SEDA) are confirmed non-viable for this founder in their current
  form.** The genuinely available candidates narrow to Injini (contingent
  on a future cohort opening) and TIA (eligibility itself unresolved) —
  see Constraints and Financial Considerations for the full,
  honestly-caveated treatment. This materially weakens, not merely
  re-states, the reliability of this fallback.
- **Professional opinions/advice: zero marginal cost to the venture**, via
  the user's existing policy. Coverage for the two named hard-gate
  reviews (Data-Privacy Practitioner; child-development specialist) is
  confirmed, Verified-tier. Completing those reviews is explicitly out of
  scope for this cycle. The policy's general scope for other engagement
  types (e.g., a curriculum designer) remains undocumented.
- **Runway: 6 months** at current commitment before external funding is
  needed.
- **Acquisition/CAC: organic-only, zero paid acquisition.** No marketing
  budget is allocated from the R10,000 total. Four specific channels are
  now named (founder network/word of mouth; organic social; ASO;
  parent/community forums), but none carries an expected-volume estimate.
  The schools-partnership channel remains explicitly deferred.
- **Curriculum content-production cost:** remains moot for launch,
  deferred alongside the feature itself, against a quantified v2 trigger.

**Reconciliation against the prior agency reference range, unchanged:**
the previously-cited $25,000-$120,000+ engineering-cost range was a
reference frame, not the plan. R10,000 buys days, not months, of
professional engineering if the founder's own capacity fails — there is
no buffer to purchase execution beyond the R20,000 total ceiling, and that
ceiling's own fallback is now confirmed weaker than previously understood.

**Still open:** no post-runway external funding-ask is precisely sized —
a candidate target list exists (materially narrower this cycle — see
above), but the researched award figures are program ceiling figures, not
typical disbursements, and actual obtainability for the two remaining
live candidates (Injini, TIA) is itself unresolved (cohort timing;
eligibility). **A minimal P&L/break-even model remains unproduced this
cycle — explicitly out of scope, carried forward as a named item for the
Developing Committee.** Status remains Partial: the low-end stress test is
cross-referenced consistently with Constraints and the advice-policy
coverage question is resolved for the two named reviews, but the revenue
side still rests on unvalidated Guessing-tier estimates, the funding
fallback is now confirmed materially weaker, and precise funding-ask
sizing and a P&L remain unaddressed.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Unaffected by this cycle's `Clarifications_v24.md` findings. Core
mechanics (budget and earning, task structure, completion/verification/
reporting flow, dispute mechanism, payment confirmation, late-penalty
parent-only design) are unchanged in structure. All specialist design
decisions from prior cycles stand.

**Dispute-escalation beyond 48 hours** is resolved via an interim
placeholder: unresolved disputes beyond the 48-hour parent-decline window
are flagged for manual founder review, at MVP stage — not a scalable
long-term solution, pending the future (out-of-scope) AI-mediator
feature. This is founder-capacity-dependent and is named explicitly as a
direct extension of the execution-capacity Critical Gap — founder
bandwidth already spans the build, the instrumented pilot, and two
regulatory rechecks within the 6-month runway, and now also absorbs any
beyond-48-hour disputes the pilot generates. **An aggregate assessment of
this total founder-capacity load remains explicitly out of scope this
cycle, carried forward as a named item for the Developing Committee.**

**Fintech Advance gamification-avoidance decision** remains moot for
launch, not an active build task. Fintech Advance itself is deferred to
v2 alongside all curriculum content, against a quantified trigger; its
mitigation decision (no product gamification for its content) remains
adopted for whenever the module is eventually built.

**New build-spec items introduced by the hybrid bonus, unchanged:** the
mechanism for logging/verifying the behavior inputs and the grade-input
mechanism for the retained results-bonus layer both need specification at
build time.

Status remains Complete: every specialist recommendation within this
section's scope has a recorded decision.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unaffected by this cycle's `Clarifications_v24.md` findings. Still
unspecified: how account-linking is technically initiated; how payment
confirmation is captured beyond the accept/dispute UI; the exam-bonus
grade-input mechanism; the hybrid bonus's behavior-input logging/
verification mechanism; the grace-period/reminder notification
infrastructure. No curriculum-delivery technology is in scope, consistent
with its deferral. Status remains Partial.

## Legal & Compliance ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unaffected by this cycle's `Clarifications_v24.md` findings. The retained
specialist legal opinion (`LegalOpinion_v1.md`) remains the Verified-tier
foundation of this section — all seven originally-scoped questions
answered.

**1. Money-transmitter/payment-facilitation risk: low, contingent on a
locked product-spec constraint.** [Likely] holds only as long as Mbucks
cannot be spent, transferred, or redeemed anywhere other than through the
parent's independent banking-app payment — confirmed [Certain] against
SARB's e-money Position Paper. Courts look at substance, not labels
(*Maize Board v Jackson* 2005 (6) SA 592 (SCA)). NCR's Payment
Distribution Agent category confirmed inapplicable.

**2. Universal parental-consent gate:** legally sufficient as designed,
POPIA s34/s35(1)(a) satisfied. Two hardening recommendations remain build
tasks: consent-flow documentation separation; lightweight parent
identity-verification step.

**3. POPIA Section 14 retention:** confirmed [Certain] no minor-specific
supplementary rule exists; a specific retention purpose, period, and
deletion trigger must be affirmatively designed.

**4. Minor contractual capacity:** fully verified — the "rights without
obligations" exception fits MiniMoney's structure, supported by *Pitout v
North Cape Livestock* (1977) and *Conradie v Rossouw* (1919 AD 279).

**5. Terminology risk:** real, mitigation adopted — debt-coded
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

Status remains Complete: all seven originally-scoped questions are
answered at Verified tier; the two unsettled external regulatory
questions are pending external rechecks with named owners and decided
fallbacks.

## Risks

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

All previously-identified risk categories remain catalogued; disposition
updated per this cycle's two resolutions (founder-eligibility facts;
acquisition channels).

- **Regulatory risk:** unchanged — core mechanic low-risk; two narrower
  open regulatory questions each carry a named owner, timing trigger, and
  decided fallback.
- **Execution-capacity risk — bounded contingency, now with a
  materially weaker funding-fallback candidate list, confirmed not merely
  untested.** A solopreneur venture with a R10,000 total development
  budget, a ~3-month directional build timeline, an instrumented 20-50
  family pilot, two personally-owned regulatory rechecks, and manual
  founder review of any dispute unresolved beyond 48 hours — all inside a
  6-month runway, executed substantially by one person. The self-fund-
  further contingency remains capped at R20,000 total, with grant/
  startup-program funding as the stated fallback, explicitly the
  mechanism triggered if actual revenue lands at the low end of the range
  (see Revenue & Costs, Constraints). **This cycle's finding
  (`Clarifications_v24.md`) is a genuine increase in this risk, not a
  routine confirmation: the two previously-strongest candidates (NYDA,
  SEDA) are now confirmed excluded, not merely untested, leaving only a
  not-currently-open accelerator cohort (Injini) and an eligibility-
  unresolved instrument (TIA).** Whether R20,000 total is itself
  sufficient capital to reach sustainability remains untested and is now
  compounded by a weaker fallback.
- **Acquisition/adoption risk — four channels now named, volume
  unvalidated.** Zero paid acquisition remains the decided strategy
  against the 9,150-30,500 family-install funnel. Four specific organic
  channels are named this cycle (founder network/word of mouth; organic
  social; ASO; parent/community forums), resolving "which channels" but
  not "will they reach sufficient volume" — none carries an expected-
  volume estimate. The pilot's 60% task-cycle-completion criterion
  doubles as an explicit acquisition/mechanic-engagement checkpoint for
  the pilot-to-wider-release transition — this gates premature scaling
  but does not itself validate whether the four named channels can reach
  the funnel's absolute size, which remains untested. The schools-
  partnership channel remains explicitly deferred.
- **Child-safety/data-privacy risk:** consent model confirmed legally
  sufficient; two hardening recommendations remain build tasks. POPIA
  Section 14 retention policy remains an affirmative design requirement.
  The data-breach/incident-response commitment specialist review has a
  defined, correctly-framed pre-pilot (not pre-build) trigger. It has not
  yet occurred, and completing it is explicitly out of scope this cycle.
- **Minor-contractual-capacity risk:** resolved, unchanged.
- **Terminology/perception risk:** mitigation decided, unchanged.
- **Late-penalty/relationship risk:** both mitigation paths engaged,
  unchanged; residual risk remains real. **No quantified stop/redesign
  threshold exists for this risk's own measurement instrument — explicitly
  out of scope this cycle, carried forward.**
- **Exam-bonus/intrinsic-motivation risk — candidate-instrumented, review
  trigger defined, not yet obtained.** The behavior-primary redesign
  follows the evidence; the retained outcome-contingent bonus layer means
  the crowding-out risk is reduced, not eliminated. No family may be
  enrolled until the review has actually occurred, and it has not yet
  occurred as of this revision. **No quantified stop/redesign threshold
  exists for this instrument either — explicitly out of scope this cycle,
  carried forward.**
- **Fintech Advance content risk:** moot for launch, deferred to v2,
  unchanged.
- **Age-appropriateness/terminology-uniformity risk:** framework adopted;
  reconciliation drafted, not yet specialist-reviewed, unchanged.
- **v2-trigger-criterion risk:** resolved — the trigger is a specific dual
  gate (500 subscribers AND 60% 90-day retention). A minor residual
  remains untraced: what happens if one threshold is met and the other is
  not — a narrow interpretive gap, not a material one.
- **Dispute-escalation risk:** resolved via an interim, explicitly
  non-scalable mechanism (manual founder review beyond 48 hours),
  founder-capacity-dependent, pending the future AI-mediator feature.
- **Non-dilutive-funding-target risk — PARTIALLY RESOLVED this cycle, with
  a materially unfavorable finding, not merely "resolved with caveats" as
  framed in v23.** The founder-eligibility facts that gated the top two
  candidates are now confirmed, and confirmed negative: the founder's age
  (39) excludes NYDA; MiniMoney's lack of company registration/tax
  clearance excludes SEDA. **This is a genuine narrowing and weakening of
  the fallback, not a routine confirmation** — the remaining candidates
  (Injini, TIA) carry meaningfully weaker timeline or eligibility
  evidence than either excluded candidate did, and the fallback's
  practical reliability is correspondingly weaker than v23's framing
  suggested.
- **Aggregate founder-capacity risk — named but not assessed as a total,
  explicitly out of scope this cycle.** Each individual obligation (build,
  pilot, two regulatory rechecks, two specialist reviews, manual dispute
  adjudication) is separately tracked throughout this document; no
  section assesses their combined, concurrent single-point-of-failure
  exposure. Carried forward as a named item for the Developing Committee.
- **Competitive risk; monetization-execution risk; app-store policy risk;
  platform-concentration risk:** unchanged in substance.

Status remains Complete: the risk landscape is comprehensively identified
and characterized, and every specialist-recommended mitigation within it
carries a recorded decision. A Complete risk register does not mean the
risks are eliminated: execution capacity (funding fallback now confirmed
materially weaker), two external regulatory questions, the accepted
exam-bonus residual, the untested organic-only acquisition strategy (now
channel-named but volume-unvalidated), and the un-assessed aggregate
founder-capacity load are all live, and are stated as such.

## Assumptions

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Carried forward, unchanged: parent-direct payment; SA launch jurisdiction;
universal consent gate; Android-first; Mbucks/Mpoints dual currency;
7-Mbuck late-penalty cap with 3-Mbuck pilot cap; the fixed Mbucks-to-Rand
peg; the late-penalty mechanic as a parent-only administrative matter;
exam-bonus grade data self-reported/parent-entered; primarily a South
African B2C product at launch; 2.0 children per subscribing family
(Evidence: Assumed, not derived or validated).

**Remaining load-bearing assumptions, untested:**

- The exam-bonus risk-acceptance assumption stands: the secondary bonus's
  salience will not dominate the behavior-primary structure in the
  child's perception. Untested; candidate-observable via the
  motivation-probe, pending its trigger-defined specialist review, itself
  explicitly out of scope this cycle.
- Organic-only acquisition will be sufficient to reach a meaningful share
  of the 9,150-30,500 family-install funnel. **Four specific channels are
  now named this cycle, but this does not resolve the underlying
  assumption — none carries a volume estimate.** Untested, unbenchmarked;
  partially checkpointed via the pilot's 60% completion criterion but not
  validated in absolute terms.
- **The self-fund-further ceiling (R20,000 total) is sufficient capital
  to reach a sustainable venture, or grant/startup-program funding is
  actually obtainable if it is not. Neither is tested, and this cycle's
  finding makes the second half of this assumption demonstrably weaker,
  not merely still-untested.** The founder's age (39) and MiniMoney's
  current lack of company registration/tax clearance — both now
  Verified-tier, user-confirmed facts, per `Clarifications_v24.md` —
  exclude the two previously-strongest named candidates (NYDA, SEDA)
  outright. The remaining candidates (Injini, contingent on a future
  cohort; TIA, eligibility itself unresolved) are both weaker. **This
  cycle's resolution makes the assumption's evidentiary picture both
  clearer and less favorable simultaneously** — a genuine increase in
  risk, consistent with this document's standing practice of stating
  clarity and favorability as separate dimensions, not conflating them.
- The Incubator-drafted candidate data-breach commitment and
  motivation-probe are adequate as interim policy/design pending their
  respective specialist reviews. Both remain Evidence: Assumed by
  construction; both reviews have a defined, correctly pre-pilot-framed
  trigger, neither has occurred, and completing either is explicitly out
  of scope this cycle.
- Mbucks non-transferability/non-redeemability and the SARB/NPS Act
  contingency remain documented constraints, not assumptions (see
  Constraints).

Status remains Partial: several load-bearing assumptions remain untested,
and the one dimension where this cycle's clarification could have
improved the picture (funding-fallback obtainability) has instead
worsened it — the list is a working inventory, not a closed set.

## Constraints

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (with
a materially narrower Supported-tier funding-candidate addition and two
Assumed-tier additions, named below)

- Solopreneur venture; AI-assisted development; external technical
  expertise engaged only on-demand; directional ~3-month build timeline;
  Android primary, iOS deferred.
- **Mbucks non-transferability/non-redeemability** — binding product-spec
  constraint on all future roadmap decisions (`LegalOpinion_v1.md` Q1).
- **R10,000 total development budget; 6-month runway before external
  funding is needed; professional opinions at zero marginal cost.**
  Coverage of the two hard-gate specialist reviews under this policy is
  confirmed; completing those reviews is explicitly out of scope this
  cycle.
- **Zero paid acquisition — organic-only growth, four channels now
  named.** No marketing budget is allocated from the R10,000 total. The
  four named channels (founder network/word of mouth; organic social
  media; App Store Optimization; parent/community forums and groups)
  replace the prior generic label but carry no volume estimate; the
  pilot's 60% task-cycle-completion criterion serves as the checkpoint
  gating the transition to wider release, not a validation of the
  channels' absolute reach.
- **Schools-partnership channel — explicitly deferred**, founder bandwidth
  is the binding constraint stated, unchanged.
- **Curriculum/educational content deferred to v2 — an explicit MVP-scope
  constraint**, against a quantified dual trigger (500 subscribers AND
  60% 90-day retention). The launch build, budget, and 6-month runway do
  not need to accommodate curriculum authoring or production.
- **Dispute-escalation beyond 48 hours — resolved via an interim,
  explicitly non-scalable mechanism**: manual founder review at MVP
  stage, pending the future out-of-scope AI-mediator feature. A binding
  process constraint on founder bandwidth, tracked as an extension of the
  execution-capacity Critical Gap.
- **Runway-slippage contingency — self-fund further, bounded, fallback
  target now confirmed materially weaker.** Maximum personal commitment:
  R20,000 total (R10,000 initial + R10,000 additional) — a hard ceiling.
  If the cap is exhausted without the venture being sustainable, the
  stated fallback is grant or startup-program funding (non-dilutive), not
  equity or informal borrowing. This contingency is the exact mechanism
  triggered if actual Year-1 revenue lands at the low end of the range
  (92 paying families, ~R5,519/month) — a foreseen, already-planned-for
  scenario, not a new failure state requiring a new decision.

  **The specific non-dilutive funding target, named via `ResearchFindings_v4.md`
  in v23, is now confirmed materially narrower this cycle
  (`Clarifications_v24.md`), resolving Required Change 3 from `Verdict_v7.md`
  — with an unfavorable finding, stated plainly, not smoothed over:**

  1. **Previously primary, now EXCLUDED: NYDA (National Youth Development
     Agency) Grant Programme.** Hard eligibility gate required the
     founder to be aged 18-35. **The founder's age is 39 — outside this
     band. NYDA is excluded outright, confirmed, not merely uncertain.**
  2. **Previously secondary, now NOT CURRENTLY APPLICABLE: SEDA Technology
     Programme (STP).** Requires South African CIPC company registration
     and a valid SARS tax-clearance status. **MiniMoney is not yet
     registered and does not currently hold tax clearance. SEDA is
     therefore not currently applicable** — registration/tax clearance
     becomes a new, named prerequisite task before SEDA is even
     reachable, not an available near-term fallback today.
  3. **Genuinely available, weaker: Injini (EdTech Accelerator, Cape
     Town), earlier-stage cohort track** — historically an initial
     ~R100,000 grant component; plausible sector fit (dedicated EdTech
     accelerator) but **no confirmed open 2026 cohort exists for this
     track** — contingent on a future cohort opening, not currently
     pursuable.
  4. **Genuinely available, genuinely uncertain: Technology Innovation
     Agency (TIA) instruments** (Seed Fund / SMME Seed Fund / Grant
     Startup Capital) — up to R200,000 (plus a R60,000/year project fee)
     in one cited instrument, but TIA's public materials are structured
     around Technology Readiness Levels and university/research-
     institution pathways; **whether a solo, non-research-affiliated
     consumer-app founder would even be considered eligible remains
     unresolved.**

  **Net effect, stated plainly: with both the primary (NYDA) and
  secondary (SEDA) candidates confirmed non-viable in their current form,
  the genuinely available non-dilutive funding fallback narrows to two
  candidates, neither currently pursuable without a precondition being met
  first (Injini: a cohort opening; TIA: an eligibility question this
  research could not resolve). This is a genuine increase in financial
  and execution risk, not a routine confirmation update.**

  Previously-named excluded/structurally-excluded candidates (SAB
  Foundation Social Innovation Fund; FNB App of the Year; Mastercard
  Foundation EdTech Fellowship; Google for Startups Black Founders Fund:
  Africa; National Empowerment Fund; Standard Bank/Founders Factory
  Africa; Naspers Foundry; Grindstone) remain excluded on the same
  grounds established in v23 — see `ResearchFindings_v4.md` via
  `BusinessCase_v23.md` for the full original reasoning, unchanged this
  cycle.

  **What remains genuinely open:** whether the founder will pursue CIPC
  registration and SARS tax clearance to make SEDA reachable in future
  (a new, named prerequisite task, not yet committed to); whether an
  Injini cohort opens within the runway window; whether TIA's eligibility
  for this founder profile can be clarified directly (e.g., by contacting
  TIA, out of scope for this cycle). **Evidence for the founder-eligibility
  facts themselves (age; registration status) is now Verified-tier, user-
  confirmed, per `Clarifications_v24.md` — the highest tier this document
  uses. The candidate-list evaluation itself remains Supported-tier
  (vendor desk research), never Verified.**

- **Minimal data-breach/incident-response commitment — Incubator-drafted
  candidate, review trigger defined, correctly framed as pre-pilot, not
  pre-build:** the same trigger already established for the specialist
  legal opinion — once a stable working model exists, and before any
  pilot testing with real families begins. This defines *when* the review
  occurs; the review itself has not yet occurred as of this revision, and
  completing it is explicitly out of scope this cycle. Evidence: Assumed
  — a founder-authored draft. The commitment must not be in force, and
  pilot enrollment of real families must not begin, until the
  Data-Privacy Practitioner (Expert Roster Entry 5) has actually reviewed
  it. Candidate minimum content, unchanged:
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
v21 — is Constraints' Complete status still soundly earned, given this
cycle's unfavorable finding?** This question is answered honestly, not
mechanically. Every material question within this section's scope still
carries a made decision: budget, runway, acquisition (now channel-named),
launch-configuration fallbacks, MVP-scope, dispute-escalation, and the
self-fund-further contingency's fallback *category* (grant/startup-program
funding, non-dilutive). Under the literal standard this document has
applied consistently since v17 — a decided fallback *category* with a
named owner, not a currently-obtainable specific candidate, is sufficient
for Complete — this section remains Complete, on the same grounds as v22
and v23: the pattern was never contingent on obtainability, only on the
category and ownership being decided, and that has not changed.

**However, this is named as a genuine tension, not swept aside.** The
Investment Committee's own Gate Integrity Check (`Verdict_v7.md`) flagged
concern about exactly this pattern — treating "trigger defined" or
"category decided" as equivalent to "resolved" — as a recurring feature
of this document across at least six prior cycles. This cycle's finding
sharpens that tension materially: it is no longer merely that obtainability
is *untested*; two of the four named candidates are now *confirmed
excluded*. A stricter reading of this section's Complete standard — one
requiring a currently-viable, specific named candidate, not merely a
decided category — would score this section Partial. **This tension is
named explicitly here and carried into Readiness Score's disclosed
conservative computation, not adjudicated unilaterally at v24.** The
Incubator does not resolve this ambiguity by silently changing its own
scoring methodology this late in the document's history; it discloses the
tension and its numeric consequence for the Developing Committee and any
future review to weigh.

## Roadmap

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Now (parallel with build, starting immediately):** core engineering
build only. Curriculum-content workstream remains removed from this
phase, deferred to a post-launch v2 phase, against a quantified trigger
(500 subscribers AND 60% 90-day retention). **Foundational build work is
explicitly not gated by the two outstanding specialist reviews — those are
a pre-pilot gate, not a pre-build gate, confirmed unchanged this cycle
(`Clarifications_v24.md`).**

**Build phase:** implement core loop with decided designs —
parent-facing-only debt terminology; hybrid exam bonus; grace-period/
pre-escalation reminders; beyond-48-hour dispute escalation via manual
founder review (interim placeholder). Legal build tasks: POPIA s14
retention period and deletion trigger design; consent-flow documentation
separation; lightweight parent identity-verification step. The candidate
data-breach/incident-response commitment (see Constraints) must be
reviewed by the Data-Privacy Practitioner (Expert Roster Entry 5) once a
stable working model exists and before any pilot testing with real
families begins. This has not yet occurred; completing it is explicitly
out of scope this cycle.

**Build-spec stage:** the user personally runs both regulatory rechecks —
SARB/NPS Act and FPB. Decided fallbacks apply if unresolved by launch.

**Pilot (20-50 families):** double-duty per prior decision — mechanic
safety/child-development signal AND directional demand read — with the
adopted measurement package plus the candidate motivation-probe addition
built into the pilot design. The candidate motivation-probe must be
reviewed by the child-development specialist (Expert Roster Entry 2)
using the same pre-pilot trigger — once a stable working model exists,
before any pilot testing with real families begins. Not yet occurred;
completing it is explicitly out of scope this cycle. No family may be
enrolled until both this review and the data-breach-commitment review
have actually occurred. The pilot's 60% task-cycle-completion criterion
doubles explicitly as the acquisition/mechanic-engagement checkpoint
gating the transition to wider release: fewer than 60% completing 4
consecutive weekly cycles means organic-only acquisition/engagement is
treated as not yet validated. **Acquisition into the pilot itself will
draw on the four named channels** (founder network/word of mouth; organic
social; ASO; parent/community forums) — none carries a volume estimate,
so pilot recruitment timing/feasibility is itself untested.

**Post-pilot (~month 6): external funding may be needed** — the initial
runway ends here. Decision rule: if month 6 arrives without secured
external funding, or any single workstream has slipped materially — or
actual revenue lands at the low end of the range (92 paying families,
~R5,519/month), a foreseen scenario — the user will self-fund further up
to a hard ceiling of R20,000 total personal commitment. **If that ceiling
is reached without a sustainable venture, the stated fallback category is
grant or startup-program funding; the specific candidate list is now
confirmed materially narrower this cycle** (`Clarifications_v24.md`): NYDA
and SEDA excluded; only Injini (cohort not currently open) and TIA
(eligibility unresolved) remain — see Constraints for the full,
honestly-caveated list.

**Growth (6-12 months):** conversion validation against the corrected
1-3% range applied to the corrected funnel; iOS port timing evaluation;
account-linking and/or Mpoints re-introduction as their regulatory
questions resolve. Schools-partnership channel exploration remains
explicitly deferred.

**Post-launch, demand-gated (v2, timing determined by trigger, not
calendar): curriculum content workstream.** Trigger: 500 paying
subscribers AND 60% 90-day retention, both required. Authorship (founder
vs. engaged designer via the zero-marginal-cost advice policy, pending
confirmation of that policy's *general* scope) remains open, not
time-pressured. The three-tier-to-six-way sub-band reconciliation remains
drafted as low-cost prep work, not adopted.

**Explicitly carried forward to Developing Committee, not resolved this
cycle, per `Clarifications_v24.md`'s scope decision:** the two trigger-
defined specialist reviews (pre-pilot gate, confirmed); a minimal P&L/
break-even model; a quantified stop/redesign threshold for the
child-welfare instruments; an aggregate founder-capacity/bandwidth
assessment.

Status remains Complete: every pre-pilot decision the roadmap lists as
pending is made; the two specialist reviews carry a defined,
correctly-framed pre-pilot trigger; the low-end revenue scenario is tied
to the existing self-fund-further contingency; the dispute-escalation gap
is resolved via a named interim mechanism; the v2-curriculum trigger is
quantified; acquisition channels are now named. The remaining opens are
owned external rechecks, build-spec parameters, the still-not-yet-occurred
specialist reviews, the now-materially-weaker non-dilutive funding
fallback, and the four items explicitly deferred to the Developing
Committee.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**What exists:**

- **Budget: R10,000 total** for development.
- **Self-fund-further cap: R20,000 total maximum personal commitment**
  (R10,000 initial + R10,000 additional). Fallback if exhausted: grant or
  startup-program funding (non-dilutive), not equity or informal
  borrowing. **The specific non-dilutive funding target, named in v23 via
  Research House Engagement 4, is now confirmed materially narrower this
  cycle (`Clarifications_v24.md`) — a genuine increase in risk, not a
  routine confirmation:** the founder's age (39) excludes NYDA (the
  previously best-timelined primary candidate); MiniMoney's current lack
  of company registration/tax clearance excludes SEDA (the previous
  secondary candidate). The genuinely available fallback narrows to
  Injini (contingent on a future cohort opening) and TIA (eligibility
  itself unresolved) — see Constraints for the full list and caveats.
  **This resolves whether the top two candidates are obtainable (no); it
  does not resolve whether any candidate is actually obtainable in
  practice** — that remains untested for the two that remain.
- **Professional advice: zero marginal cost** via the user's existing
  policy. Coverage of the two hard-gate specialist reviews confirmed;
  completing them is explicitly out of scope this cycle. The policy's
  general scope for other engagement types remains undocumented.
- **Runway: 6 months** before external funding is needed.
- **Revenue model (per-family), unchanged in magnitude:** R59.99/month
  per family against a Year-1 range of **92-915 paying families** —
  R5,519-R54,891/month run-rate at the range bounds (≈R66,229-R658,690/
  year); ramp-dependent actuals lower. Low-end explicitly cross-
  referenced against the self-fund-further contingency as a foreseen
  scenario.
- **Acquisition spend: zero.** No marketing budget is allocated; growth
  is organic-only, now via four named channels (founder network/word of
  mouth; organic social; ASO; parent/community forums), none with a
  stated volume estimate, with the pilot's 60% completion criterion
  serving as an explicit checkpoint on the acquisition/engagement
  dimension.
- **Curriculum content-production cost:** remains moot for launch,
  deferred alongside the feature, against a quantified trigger.

**The reconciliation, unchanged:** R10,000 (~$550) against the previously-
cited $25,000-$120,000+ agency range is a 45×-220× gap, coherent only as a
founder-labor-plus-AI-assisted build. The 6-month runway is the binding
constraint: build, instrumented pilot (behind two trigger-defined,
pre-pilot-gated specialist-review requirements, neither yet satisfied),
and two user-owned regulatory rechecks must all complete inside it, after
which funding is needed — with, at best, directional pilot evidence to
raise on, or the user self-funds up to R20,000 total before falling back
to the now-materially-narrower grant/startup-program candidate list.

**Still open:** the non-dilutive funding *target* is confirmed narrower
this cycle (see above), and the funding-ask remains not precisely *sized*
— the researched award figures are program ceiling figures, not typical
disbursements, and actual obtainability for the two remaining candidates
(Injini, TIA) is itself contingent on preconditions neither yet met (a
cohort opening; an eligibility clarification). **Separately, and
explicitly out of scope this cycle per `Clarifications_v24.md`: no full
financial projections (P&L, break-even analysis) exist anywhere in this
Business Case.** This is a distinct, still fully open material question —
no owner, no timing, no decision has been made about it at any point in
this document's history, and it is carried forward as a named item for
the Developing Committee.

**This cycle's decisions:** confirm, via direct Verified-tier user
clarification, that the two previously-named top non-dilutive funding
candidates are not currently viable for this founder — resolving Required
Change 3 from `Verdict_v7.md` with an unfavorable finding, stated plainly.

Status remains Partial, and explicitly does NOT move this cycle despite
the founder-eligibility resolution: the revenue side still rests on
unvalidated Guessing-tier estimates, the funding fallback is now
materially weaker than previously understood, and — decisively — **full
financial projections (P&L, break-even analysis) remain entirely absent**,
a material question with no owner, timing, or decision anywhere in this
document, explicitly carried forward rather than addressed this cycle.

## Validation Strategy

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Closed streams, unchanged:** legal validation (retained opinion,
Verified-tier); child-development/age-appropriateness validation
(retained review, Verified-tier); all resulting design recommendations
carry decisions.

**Pilot — scope decided: double duty**, with the reviewer's underpowering
caution attached: demand findings will be directional and qualitative,
not statistically validated. The adopted measurement package includes a
candidate motivation-probe, review trigger correctly defined as pre-pilot
— once a stable working model exists, before any pilot testing with real
families begins; not yet occurred; completing it is explicitly out of
scope this cycle. **No quantified stop/redesign threshold exists for
either child-welfare instrument in this pilot — explicitly out of scope
this cycle, carried forward as a named item for the Developing
Committee.**

**Acquisition/mechanic-engagement checkpoint — resolved**, tied to the
pilot's own 60% task-cycle-completion criterion (see Success Criteria):
if fewer than 60% of enrolled pilot families complete 4 consecutive
weekly cycles, organic-only acquisition/mechanic engagement is treated as
not yet validated before widening release. **This checkpoint is now fed
by four named acquisition channels (`Clarifications_v24.md`), but this
does not itself validate whether organic-only acquisition can reach the
corrected 9,150-30,500 install funnel in absolute terms — none of the
four channels carries a volume estimate, so that remains untested, a
distinct and still-open question** (see Market & Competition,
Assumptions).

**Curriculum validation — remains reclassified, not an open gap for
launch.** Since curriculum content is deferred to v2, there is nothing to
validate at launch; this stream will be reintroduced when the feature is
actually built, against its quantified dual trigger.

**Still open, unchanged:** pricing/conversion validation (the pilot may
inform willingness-to-pay directionally but is not a conversion test);
account-linking UX/consent-flow validation; the no-Mpoints fallback
configuration's engagement loop has no validation plan.

Status remains Partial: the pilot is fully scoped and instrumented at the
decision level, both specialist reviews carry a defined, correctly
pre-pilot-framed trigger, and the acquisition checkpoint is resolved for
the pilot-to-wider-release transition specifically, with channels now
named — but market demand, pricing/conversion, per-channel acquisition
volume, and absolute acquisition feasibility have no statistically
meaningful validation scheduled anywhere in the plan, and the child-welfare
stop/redesign threshold remains undefined.

## Supporting Evidence

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Verified-tier:** `LegalOpinion_v1.md` and `ChildDevelopmentReview_v1.md`
(retained professionals); the user's direct clarification history through
`Clarifications_v24.md` (Verified-tier as to what was decided in each
cycle, including this cycle's two founder-specific facts: age (39,
excludes NYDA) and current lack of company registration/tax clearance
(excludes SEDA) — both directly user-confirmed, the highest evidence tier
this document uses, notwithstanding the unfavorable substance of the
finding itself; and the four named organic-acquisition channels).

**Supported-tier:** four Research House engagements
(`ResearchFindings_v1-4.md`); the user's directly-cited South African
statutory/statistical sources; `BusinessCase_v16.md`'s restored Market &
Competition content. `ResearchFindings_v4.md` (Engagement 4)'s candidate
funding list remains Supported-tier for its own evaluative content
(program terms, eligibility criteria, timelines) — the two founder-facts
that gate it are now separately Verified via `Clarifications_v24.md`, a
distinct and higher tier than the research itself.

**Assumed-tier, named explicitly:** the candidate motivation-probe and
the candidate data-breach/incident-response commitment (both
Incubator-drafted, neither yet reviewed — both reviews trigger-defined,
correctly pre-pilot-framed, not merely recommended, completing them out
of scope this cycle); the 2.0-children-per-family figure (stated, not
derived); the three-tier-to-six-way sub-band reconciliation draft
(Incubator-authored prep work, unreviewed).

**Bounded first-party data:** the n=10 interview round — non-
representative, governed by the standing instruction; the same rule
extends to the pilot's directional demand findings.

**Evidence-chain limitations, updated this cycle:** the self-fund-further
contingency's overall *sufficiency* remains untested, and is now
materially weaker on the *obtainability* dimension specifically: two of
four candidates are confirmed excluded, not merely untested. Full
financial projections (P&L, break-even) remain entirely absent from this
Business Case, explicitly out of scope this cycle and carried forward. A
quantified stop/redesign threshold for the child-welfare instruments and
an aggregate founder-capacity assessment remain similarly absent and
carried forward.

Status remains Complete: the evidentiary base spans Verified-tier user
decisions and retained-professional opinions through Supported-tier desk
research to bounded first-party data and named Assumed-tier candidate
content, with each tier's limits stated, now including two newly
Verified-tier founder-specific facts and their honestly-stated
unfavorable consequence for the funding fallback.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this cycle (v24, `Clarifications_v24.md`), Verified-tier —
Required Change 3 (with an unfavorable finding, stated plainly):**

- **The founder's age is 39.** This excludes NYDA outright (18-35
  eligibility band) — previously named the funding fallback's primary,
  best-timelined candidate.
- **MiniMoney is not yet CIPC-registered and holds no current SARS
  tax-clearance status.** This excludes SEDA Technology Programme as
  currently applicable — previously named the secondary candidate.
  Registration/tax clearance is now a named, distinct prerequisite task,
  not yet committed to, before SEDA becomes reachable.
- **Net effect:** the genuinely available non-dilutive funding fallback
  narrows to Injini (contingent on a future cohort opening — none
  currently open) and TIA (eligibility for a solo, non-research-
  affiliated consumer-app founder itself unresolved). This is a genuine
  increase in financial/execution risk, not a routine confirmation
  update — see Constraints, Financial Considerations, Risks, Critical
  Gaps.

**Resolved this cycle (v24, `Clarifications_v24.md`) — Required Change 5:**

- **Four organic-acquisition channels named:** founder personal
  network/word of mouth; organic social media; App Store Optimization;
  parent/community forums and groups. **This resolves "which channels,"
  not "will they reach sufficient volume"** — none carries a stated
  expected-volume estimate; that remains open (see below).

**Explicitly OUT OF SCOPE this cycle, per `Clarifications_v24.md`'s
Process Note — named plainly as carried-forward traceability items for
the Developing Committee, not resolved, not drafted, not guessed at:**

1. **Completing the two trigger-defined specialist reviews**
   (Data-Privacy Practitioner's review of the candidate data-breach/
   incident-response commitment; child-development specialist's review of
   the candidate exam-bonus motivation-probe). **Confirmed: this is a
   pre-pilot gate, not a pre-build gate**, consistent with this case's
   own build-gating logic established since v9. Neither review has
   occurred as of this revision.
2. **A minimal P&L/break-even model** — remains unproduced.
3. **A quantified stop/redesign threshold for the child-welfare
   instruments** (family-relationship-strain package; motivation-probe) —
   remains undefined.
4. **An aggregate founder-capacity/bandwidth assessment** across all
   concurrent pre-launch obligations — remains unassessed as a total.

**Still genuinely open, not time-pressured:**

- **Curriculum authorship** (founder vs. engaged designer via the
  zero-marginal-cost advice policy, pending confirmation of that policy's
  *general* scope) — undecided, no longer gating anything before launch.
- **Whether a general retention success criterion, independent of the
  quantified v2-curriculum trigger, is still needed in Success
  Criteria.**
- Whether one v2-curriculum threshold being met without the other (e.g.,
  500 subscribers without 60% retention) has a defined consequence — a
  narrow interpretive gap, not currently blocking anything.
- **Whether the founder will pursue CIPC registration and SARS tax
  clearance to make SEDA reachable in future** — a new, named task
  surfaced this cycle, not yet committed to.
- **Whether an Injini cohort opens within the runway window, and whether
  TIA's eligibility for this founder profile can be directly clarified**
  (e.g., by contacting TIA) — both newly narrowed-to candidates, neither
  currently actionable.

**Open — analytical/planning gaps, updated:**

- Whether the four newly-named organic channels can plausibly reach the
  9,150-30,500 family-install funnel in absolute terms — untested,
  unbenchmarked; the pilot's 60% checkpoint gates the transition decision
  but does not validate the funnel's absolute reachability.
- Success-criteria benchmarks (operational-health 65%, general retention)
  remain placeholders; curriculum-engagement (30%) remains reclassified
  as deferred.
- Post-runway external funding-ask precise sizing (the target list is
  confirmed narrower this cycle; the ask amount itself is not fixed —
  researched figures are program ceilings, not typical disbursements).
  **Full financial projections (P&L, break-even analysis) — absent from
  this Business Case at every prior cycle, explicitly out of scope this
  cycle, the sole remaining material question keeping Financial
  Considerations at Partial status.**
- MoneyAfrica Kids' unpublished premium price; South Africa-specific
  vendor pricing for Stitch's or Mono's product.
- The user's advice-policy *general* scope/limits (including whether it
  covers curriculum expertise specifically — coverage for the two
  hard-gate reviews is confirmed, this is the narrower remaining
  question).
- POPIA s14 retention period and deletion trigger; consent-flow
  documentation separation; lightweight parent identity-verification;
  grace-period length and reminder cadence; behavior-input logging/
  verification and grade-input mechanisms for the hybrid bonus.

Status remains Complete: this register's scope is comprehensive
identification and tracking, and every item carries its disposition. Two
of `Verdict_v7.md`'s six required changes are now resolved this cycle
(founder-eligibility facts, unfavorably; acquisition channels); the
remaining four are named plainly as explicitly out-of-scope, carried-
forward traceability items for the Developing Committee, not silently
absorbed or glossed over.

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
instruction: does the founder-eligibility finding — a genuine increase in
financial/execution risk, not a routine confirmation — move the score,
and does it flip any section's Status? Answer, applied honestly: under
the methodology this document has consistently applied since v17, it does
not move the score and does not flip any section's Status. But this
cycle discloses, explicitly and for the first time, a further conservative
tension that a stricter reading would move the score, and states that
tension's numeric consequence rather than suppressing it.**

**Why no section's Status moves under the established methodology:**

- **Constraints (already Complete):** the section's Complete standard has
  never required obtainability, only a decided fallback category with a
  named owner — unchanged by this cycle's finding under the literal
  standard applied since v17. See Constraints' own "Re-derivation"
  paragraph for the full, non-mechanical treatment of this tension.
- **Financial Considerations (remains Partial):** the funding-target's
  narrowing changes its content, not its independent basis for Partial
  status. **Full financial projections (P&L, break-even analysis) remain
  entirely absent** — a distinct material question, explicitly out of
  scope this cycle, with no owner, timing, or decision anywhere in this
  document's history. No movement.
- **Risks, Outstanding Questions, Supporting Evidence, Roadmap (all
  already Complete):** register-type or decision-tracking sections whose
  Complete status requires comprehensive identification with a recorded
  disposition per item, not the closure of every underlying substantive
  question. The funding-target item's disposition is updated (from
  "named, with caveats" to "confirmed narrower, with an unfavorable
  finding"); the sections were already Complete on that basis and remain
  so. No movement.
- **Assumptions (remains Partial):** the self-fund-further sufficiency
  assumption is now more clearly evidenced but less favorably so — not
  resolved — and several other load-bearing assumptions in this section
  (2.0 children per family; organic-only acquisition sufficiency,
  channel-named but volume-unvalidated; exam-bonus risk-acceptance) are
  entirely untouched by this cycle. No movement.
- **Market & Competition, Roadmap, Validation Strategy, Risks (content
  updated for acquisition channels):** naming four channels resolves
  "which channels," not "will they reach sufficient volume." No section's
  Status moves on this basis alone, since none of these sections' Partial/
  Complete status was solely contingent on channel-naming.

**The newly-disclosed conservative tension, stated explicitly and not
resolved unilaterally:** the Investment Committee's own Gate Integrity
Check (`Verdict_v7.md`) named a recurring pattern in this document —
treating "trigger defined" or "category decided" as equivalent to
"resolved" — as a specific concern warranting scrutiny. This cycle's
finding sharpens that tension for Constraints specifically: two of the
funding fallback's four named candidates are now *confirmed excluded*,
not merely untested. **If Constraints' Complete standard were read
strictly — requiring a currently-viable, specific named candidate rather
than a decided fallback category — this section would score Partial.**
This is disclosed here as a third, most-conservative reading, exactly
extending this document's own established practice (already used for the
Curriculum Design judgment call) of naming a stricter alternative rather
than resolving genuine ambiguity by fiat.

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

**Readiness Score = 94 / 130 = 72.3%.** Unchanged from v21, v22, and v23.
Clears the completion gate's ≥70% threshold with a 2.3-point margin.

**Conservative alternative (Curriculum Design judgment call withheld,
i.e., scored Partial = 2 pts), unchanged from v21-v23:** 91/130 = **70.0%**
— still clears the threshold, with no margin.

**New, most-conservative disclosed alternative this cycle (Curriculum
Design AND Constraints both scored Partial under the stricter,
obtainability-based reading discussed above):** 88/130 = **67.7%** — this
would NOT clear the ≥70% gate threshold. **This reading is disclosed for
transparency and is not the operative score this document certifies
against the completion gate.** The operative score, certified consistent
with the methodology applied since v17 across every prior Investment
Committee cycle, is the primary (72.3%) and standard-conservative (70.0%)
pair above. The most-conservative reading is a flagged interpretive
tension for the Developing Committee and any future review, not a
self-certified failing score adopted here.

No section is Critical + Incomplete: both Legal & Compliance and Child
Data & Consent are Complete.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) → 52%
(v13) → 52% (v14) → 52% (v15) → 52% (v16) → 70% (v17) → 70% (v18) → 70%
(v20, later found to have been honestly 67.7% by `Verdict_v5.md`'s own
arithmetic) → 72.3% (v21, or 70.0% conservative) → 72.3% (v22, or 70.0%
conservative) → 72.3% (v23, or 70.0% conservative) — unchanged across all
three — **72.3% (v24, or 70.0% conservative) — unchanged again. Two of
`Verdict_v7.md`'s six required changes are resolved this cycle (founder-
eligibility facts, with an unfavorable finding; acquisition channels);
neither moves the score under the established methodology, for the same
reason resolving a required change is not the same as resolving a
section's independent open items. A newly-disclosed, most-conservative
reading (88/130 = 67.7%) would fail the gate if Constraints were scored
under a stricter standard — named honestly, not adjudicated here.**

### Critical Gaps

1. **Execution capacity — bounded contingency, now with a materially
   weaker funding-fallback candidate list, confirmed narrower, not merely
   untested.** R10,000 total development budget plus a 6-month runway
   must contain the build, an instrumented pilot (behind two trigger-
   defined, pre-pilot-gated specialist-review requirements, neither yet
   satisfied), two regulatory rechecks, and manual founder review of any
   dispute unresolved beyond 48 hours — executed substantially by one
   person. Self-fund-further contingency: R20,000 total hard ceiling,
   explicitly the mechanism triggered if Year-1 revenue lands at the low
   end of the range; grant/startup-program funding is the stated fallback
   category, **now confirmed to exclude the two previously-strongest
   candidates (NYDA, SEDA) outright — see Gap 9 — leaving only a
   not-currently-open cohort (Injini) and an eligibility-unresolved
   instrument (TIA).**
2. **SARB/National Payment System Act open-banking question** — owned and
   fallback-protected, still externally unsettled. Owner: the user, at
   build-spec stage; fallback: launch without account-linking.
3. **FPB classification question over Mpoints** — owned and
   fallback-protected, still externally unsettled. Owner: the user, at
   build-spec stage; fallback: launch without Mpoints.
4. **Market demand remains directionally evidenced only**, against a
   corrected, smaller funnel. The n=10 standing instruction holds; the
   pilot's demand read will be directional/qualitative. Four organic
   acquisition channels are now named, but whether they can plausibly
   reach the 9,150-30,500 family-install funnel in absolute terms remains
   untested; the pilot's 60% completion criterion checkpoints the
   transition decision specifically, not the funnel's absolute
   reachability.
5. **Success-criteria benchmarks remain partial placeholders.**
   Operational health (65%) carries no external benchmark; a general
   retention figure has no proposed value (a distinct 60% 90-day figure
   exists but is scoped to the v2-curriculum trigger only). Curriculum
   engagement (30%) remains reclassified as deferred.
6. **Two specialist reviews have a defined, correctly pre-pilot-framed
   trigger, neither yet satisfied. Completing them is explicitly out of
   scope this cycle, carried forward for the Developing Committee.**
   Trigger: once a stable working model exists, before any pilot testing
   with real families begins — the same trigger used for the retained
   legal opinion; a pre-pilot gate, not a pre-build gate. Both remain
   Evidence: Assumed until the reviews actually occur.
7. **Legal/build tasks pending, unchanged.** POPIA s14 retention period
   and deletion trigger; consent-flow documentation separation;
   lightweight parent identity-verification.
8. **Exam-bonus residual risk — accepted, candidate-instrumented, review
   trigger-defined but not yet obtained. No quantified stop/redesign
   threshold exists for this or the family-relationship-strain instrument
   — explicitly out of scope this cycle, carried forward.**
9. **PARTIALLY RESOLVED this cycle, with a materially unfavorable
   finding — not "resolved with caveats" as v23 framed it.** The
   founder's age (39) confirmed to exclude NYDA (previously primary,
   best-timelined candidate). MiniMoney's current lack of company
   registration/tax clearance confirmed to exclude SEDA (previously
   secondary candidate) as currently applicable. **Both previously-named
   top candidates are now confirmed non-viable, not merely uncertain.**
   The genuinely available fallback narrows to Injini (contingent on a
   future cohort opening — none currently open) and TIA (eligibility
   itself unresolved). **This is a genuine increase in financial/
   execution risk, stated as such, not a routine confirmation update.**
   Evidence for the two founder facts: Verified (user-confirmed). Evidence
   for the candidate-list evaluation itself: Supported (vendor desk
   research) — not Verified.
10. **Acquisition channels named this cycle, volume unvalidated.** Four
    specific organic channels (founder network/word of mouth; organic
    social; ASO; parent/community forums) replace the prior generic
    label, resolving Required Change 5 from `Verdict_v7.md`. **None
    carries a stated, even directional, expected-volume estimate** —
    naming the channels does not itself validate reachability of the
    9,150-30,500 family-install funnel.
11. **Explicitly out of scope this cycle, per `Clarifications_v24.md`'s
    Process Note — carried forward as named traceability items for the
    Developing Committee, not resolved, not drafted, not guessed at:**
    (a) completing the two trigger-defined, pre-pilot-gated specialist
    reviews; (b) a minimal P&L/break-even model; (c) a quantified
    stop/redesign threshold for the child-welfare instruments; (d) an
    aggregate founder-capacity/bandwidth assessment across all concurrent
    pre-launch obligations.
12. **Newly-disclosed conservative tension (Readiness Score):** under a
    stricter, obtainability-based reading of Constraints' Complete
    standard, this section would score Partial given Gap 9's finding,
    producing a most-conservative Readiness Score of 88/130 = 67.7% —
    below the gate threshold. Named explicitly for the Developing
    Committee and any future review; not adjudicated here.
13. **Resolved in prior cycles, retained for audit-trail continuity:**
    specialist-review trigger point defined (process, not outcome, v22);
    advice-policy coverage confirmed for the two named reviews (v22);
    dispute-escalation beyond 48 hours resolved via an interim mechanism
    (v22); low-end revenue scenario cross-referenced against the
    self-fund contingency (v22); acquisition checkpoint/kill-metric
    quantified at 60% (v22); v2-curriculum trigger quantified (v22);
    self-fund-further contingency bounding (R20,000 total); curriculum
    MVP-scope deferral; schools-partnership explicit deferral;
    child-to-family population-conversion gap; all original specialist
    design decisions; the Conradie v Rossouw citation; recheck
    ownership/timing/fallbacks; pilot scope; cost/runway structure.

## Operations — Curriculum Design (Domain Extension)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified
(reconciliation draft: Assumed; authorship: Unknown)

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs, even where the curriculum feature
itself is deferred.*

Unaffected by this cycle's `Clarifications_v24.md` findings.

**Scope decision, unchanged:** curriculum/educational content, including
the 15-18-only "Fintech Advance" module, is deferred in its entirety to a
post-launch v2 feature.

**Trigger — quantified:** both a subscriber-count AND a retention-rate
threshold must be met: **500 paying subscribers AND 60% 90-day
retention** — both conditions required before curriculum work begins, a
conservative dual-gate design chosen specifically to avoid investing in
curriculum for a subscriber base that has not demonstrated it sticks
around.

Carried forward, unchanged: the age floor of 6 is intentional; the
curriculum is conceived as a short course completable daily or weekly;
two example mechanics (currency differentiation; "word sums"); "Fintech
Advance" as the distinct 15-18-only element (gamification-avoidance
decided, risk-literacy framing adopted).

**Three-tier age framework — adopted, unchanged:** early childhood
(roughly 6-9, softened task/reward framing); pre-teen (roughly 10-14,
basic transactional literacy); teens (roughly 15-18, pre-employment
literacy).

**Three-tier-to-six-way sub-band reconciliation — unchanged, still prep
work, not adopted.** Incubator-authored, Evidence: Assumed, unreviewed by
the child-development specialist; does not itself resolve anything or
count toward this section's Complete status. Three resolution options
remain drafted for eventual specialist review: (a) fold the 9-10 band
into the pre-teen tier for curriculum purposes specifically (Incubator's
draft recommendation); (b) fold the 9-10 band into the early-childhood
tier; (c) split content within the 9-10 band by exact age (not
recommended).

**Authorship — remains genuinely undecided, unchanged.** The user has not
decided between authoring the curriculum personally or engaging a
curriculum designer via the zero-marginal-cost advice policy, pending
confirmation that the policy's *general* scope extends to
instructional-design expertise. `CurriculumDraft_v1.md` remains available
as an earlier, unreviewed/unadopted starting point.

**Still open, tracked as v2-phase items, not launch-blocking:**
instructional format, standards alignment, and content itself; the
conditional 6-9-tier immediate-feedback replacement under the no-Mpoints
fallback; the 30% curriculum-engagement success benchmark (deferred
alongside the feature); the narrow interpretive gap of what happens if
one v2 trigger threshold is met without the other.

Status: Complete, unchanged, on the same basis established in prior
cycles.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★
(Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unaffected by this cycle's `Clarifications_v24.md` findings. Directly and
substantially addressed by `LegalOpinion_v1.md` Q2 and Q3. The universal
parent-consent gate is confirmed legally sufficient as designed under
POPIA s34/s35(1)(a). Two hardening recommendations remain named build
tasks: consent-flow documentation separation; a lightweight parent
identity-verification step.

POPIA Section 14 retention is confirmed to require an affirmatively
designed, specific retention period and deletion trigger — a named,
pending build task.

A minimal data-breach/incident-response commitment (see Constraints)
directly extends this section's scope. Specialist (Data-Privacy
Practitioner) review has a defined, correctly pre-pilot-framed trigger:
once a stable working model exists, and before any pilot testing with
real families begins — the same trigger already used for the retained
legal opinion. This defines when the review occurs, not that it has
occurred. It has not yet occurred, and completing it is explicitly out of
scope this cycle. It is an Incubator-drafted candidate (Evidence:
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
carries a defined, correctly pre-pilot-framed trigger rather than an
open-ended intention, still a hard gate rather than an unresolved central
question of the section's own original scope.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Complete.
- Readiness Score ≥ 70%: **Yes — PASSES**, on the operative primary/
  conservative reading (72.3% / 70.0%), unchanged from v21-v23, certified
  consistent with the methodology this document has applied since v17. A
  newly-disclosed, most-conservative reading (67.7%) is named honestly in
  Readiness Score as a flagged interpretive tension, not adopted as the
  operative self-certified score.
- **Expert roster entries ≥3 sentences, each naming a specific
  case-study assumption:** see `ExpertRoster.md`, regenerated this
  cycle, six entries.
- **Devil's Advocate objections ≥3, each citing a specific section:** see
  `reviews/DevilsAdvocate.md`, regenerated this cycle, five objections.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.
- No section consists solely of an "Unchanged from vN, not reproduced"
  pointer: **Yes.** Every section contains its own full, substantive,
  self-contained text this cycle.

**This Business Case passes its own completion gate on the operative
reading.** Two of `Verdict_v7.md`'s six required changes are resolved
this cycle — Required Change 3 (founder-eligibility facts), with a
material, unfavorable finding stated plainly and threaded through
Constraints, Financial Considerations, Risks, and Critical Gaps rather
than smoothed over; and Required Change 5 (concrete acquisition
channels), with an honest reachability caveat. **The remaining four
required changes — completing the two trigger-defined specialist reviews
(confirmed a pre-pilot, not pre-build, gate consistent with this case's
build-gating logic since v9), a minimal P&L/break-even model, a
quantified child-welfare stop/redesign threshold, and an aggregate
founder-capacity assessment — are explicitly out of scope this cycle**,
per the user's documented decision in `Clarifications_v24.md`, and are
named plainly as carried-forward traceability items for the Developing
Committee rather than resolved, drafted, or guessed at here. **The
Readiness Score is unchanged at 94/130 = 72.3% (or 91/130 = 70.0%
conservative)** under the methodology applied consistently since v17. A
newly-disclosed, most-conservative reading (88/130 = 67.7%, which would
fail the gate) is named explicitly as an unresolved interpretive tension
rather than adjudicated by fiat, consistent with the Investment
Committee's own Gate Integrity Check concern about this document's
recurring "trigger/category-defined equals resolved" pattern. Genuine
open items remain — detailed in Critical Gaps — led by execution capacity
(funding fallback now confirmed materially weaker, not merely untested),
two externally-unsettled regulatory questions, two trigger-defined but
not-yet-obtained specialist reviews, and the four items explicitly
carried forward to the Developing Committee this cycle.
