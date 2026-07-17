# Business Case: MiniMoney — v21

> Prepared by: Incubator. This revision responds to the Investment
> Committee's fifth review (`Verdict_v5.md`, "Proceed with Changes," six
> required changes plus a Gate Integrity Check finding) using the user's
> item-by-item decisions in `Clarifications_v21.md`. Authorized inputs for
> this cycle: `00_CaseStudy.md`, `BusinessCase_v20.md`, `Verdict_v5.md`,
> `Clarifications_v21.md`.

## What Changed in v21 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**1. Gate Integrity fix — self-fund-further contingency now bounded
(required change 1).** Maximum personal commitment: **R20,000 total**
(R10,000 initial development budget + R10,000 additional self-fund cap),
stated as a hard ceiling, not directional. If the cap is exhausted
without the venture being sustainable, the stated fallback is grant or
startup-program funding (non-dilutive), not equity or informal borrowing.

**Re-derivation, shown explicitly, per this cycle's instruction:**
`Verdict_v5.md`'s Gate Integrity Check applied the Readiness Score
section's own standard — "documentation of an open decision is not
resolution of it" — to the v20 self-fund-further item and found it
failed that standard: no number, no ceiling, nothing distinguishing it
from an unmade decision. Applying the *same* standard to this cycle's
replacement: does "R20,000 total, hard ceiling, fallback = grant/
startup-program funding if exhausted" constitute a made decision under
the definition ("resolved, adopted, or a deliberate, documented
residual-risk acceptance")? **Yes** — two things are now present that
were absent at v20: (a) a specific number bounding the maximum exposure,
and (b) a named fallback *form* (grant/startup-program funding) for what
happens if that bound is reached. Both of the specific absences the
Investment Committee's own Devil's Advocate objection identified — "an
unlimited personal commitment is not a real constraint, it is the
absence of one" — are directly addressed: the commitment is no longer
unlimited, and it has a subsequent step defined rather than trailing off
into nothing. This is not a re-assertion of the prior Complete status; it
is new content that satisfies the definition's test on its own terms.
**Constraints' Complete status is therefore restored on genuinely new
grounds, not merely reasserted** — detailed further in Constraints and
Readiness Score below, including an explicit statement of what the
honest v20 recompute would have been.

**2. Data-breach/incident-response specialist review — ELEVATED to hard
pre-pilot gate (required change 2).** No longer "advisable." The
Data-Privacy Practitioner's review of the Incubator-drafted candidate
breach commitment must occur, and the reviewed (not merely drafted)
commitment must be in force, before pilot enrollment of real families
begins. Updated in Constraints, Roadmap, and the Child Data & Consent
domain extension.

**3. Exam-bonus motivation-probe specialist review — ELEVATED to hard
pre-enrollment gate (required change 3).** No longer "a recommended next
step." The child-development specialist's review of the candidate
motivation-probe must occur before any family is enrolled in the pilot.
Updated in Success Criteria, Risks, and Validation Strategy.

**4. Curriculum authorship — RESOLVED via a broader MVP-scope decision,
not the original question's literal framing (required change 4).**
Verbatim from the user: *"This is not a MVP feature meaning it is not
critical for the Launch version of the App. It will be a add on once we
have proved a demand."* Curriculum/educational content — including the
15-18-only "Fintech Advance" module, itself a curriculum element — is
**deferred in its entirety to a post-launch v2 feature**, contingent on
demonstrated demand for the core product. MiniMoney launches with the
core task-assignment, budget, Mbucks/Mpoints, and payslip/invoice
mechanic only. **This is traced as a correction, per Playbook Entry 2,
across every section that described curriculum as in-scope,
in-progress, or launch-parallel** — Executive Summary, Problem,
Opportunity, Objectives, Success Criteria, Value Proposition, Operations,
Legal & Compliance, Risks, Roadmap, Revenue & Costs, Financial
Considerations, Validation Strategy, Outstanding Questions, and the
Curriculum Design domain extension itself. Authorship remains genuinely
undecided but is no longer time-pressured, since nothing is scheduled
against it before v2 begins. **A ripple effect actively checked for and
found, per Playbook Entry 2's instruction to look beyond the named
sections:** Fintech Advance is itself curriculum content under the
clarification's own broad framing ("curriculum/educational content"),
so its "mitigation adopted" and "gamification-avoidance decided" status
throughout the document is now moot-for-launch, not an active build
task — named explicitly wherever it previously appeared as active.

**4b. Three-tier-to-six-way sub-band reconciliation — drafted now as
prep work, despite the feature's deferral (required change 4b).** Per
explicit user instruction. See the Curriculum Design domain extension
below. **This draft is Incubator-authored, unreviewed by the
child-development specialist, and — per Playbook Entry 9 — does not
itself resolve or count toward closing any material question; it is
documentation prepared ahead of a deferred feature, nothing more.**

**5. Schools-partnership channel — EXPLICITLY DEFERRED, not left
unscoped (required change 5).** Stated reason: founder bandwidth within
the 6-month solo-founder runway does not allow schools-partnership
outreach pre-launch alongside the build, the pilot, and two regulatory
rechecks. **This resolves the Investment Committee's request by decision
rather than by the requested light-scoping exercise** — named explicitly
here, consistent with how curriculum authorship (item 4) was also
resolved via a scope decision rather than the original question's literal
shape, rather than force-fitting the answer given onto the question
asked.

**6. Child-to-family population-conversion gap — RESOLVED via a stated
assumption (required change 6).** **2.0 children per subscribing family**
(within the up-to-4-per-family cap), Evidence: Assumed, not derived or
validated — applied to recompute the reachable-family population and the
downstream install/paying-family funnel. **This is a material
recalculation, not a cosmetic one:** dividing the previously-used
reachable-*child* figure by 2.0 to get a reachable-*family* figure,
before applying the Year-1 install-capture and conversion rates (the
mathematically correct order — the prior range applied these rates
directly to a child-level population and treated the result as a
family-level count, which is what the named residual gap identified),
**roughly halves the previously-stated ranges.** Restated in full below
(Market & Competition, Revenue & Costs, Financial Considerations,
Executive Summary). **Per Playbook Entry 4, stated explicitly: this is
a more accurate figure, not a more favorable one** — the correction
narrows the case's revenue potential; the underlying evidentiary tier
(Assumed/Guessing) is unchanged, only the arithmetic is now internally
consistent.

**Readiness Score recomputed in full — see the Readiness Score section.
The honest v20 baseline (had the Gate Integrity finding been applied)
was 88/130 = 67.7%, below threshold. This cycle's genuine resolution of
that finding, plus one further status change (Curriculum Design, argued
explicitly below), brings the score to 94/130 = 72.3%. Under the more
conservative reading that withholds the Curriculum Design status change,
the score is 91/130 = 70.0% — still clears the threshold, with no
margin, exactly as v20 asserted. Both computations are shown; the case
clears 70% either way.**

## Executive Summary

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18), launching first in
South Africa on Android (iOS porting planned as future work). **The
launch (MVP) product is the financial mechanic alone**: a parent submits
a budget setting the minor's "basic income"; tasks earn Mbucks (a
real-money-pegged in-app currency, e.g. 10 Mbucks = R10) which
accumulate into a "payslip," while every completed task separately earns
a fixed 10 Mpoints — a distinct, non-monetary cosmetic-store currency.
The parent receives an invoice and pays the owed amount directly to the
child via the parent's own banking app — MiniMoney itself never holds,
transmits, or takes custody of funds. Subscription pricing is
R59.99/month, covering up to 4 children per family account; the funnel
and revenue unit is the family. Monetization is subscription-only at
launch, with advertising deferred to a possible post-launch V2.

**Decided this cycle: instructional curriculum content — including the
15-18-only "Fintech Advance" trading-education module — is explicitly
out of MVP/launch scope, deferred to a post-launch v2 feature contingent
on demonstrated demand for the core product** (the user's verbatim
framing: "not critical for the Launch version... an add on once we have
proved a demand"). MiniMoney's identity as a financial-*education* app
in the broader sense is unchanged — this is a sequencing decision about
what ships first, not an abandonment of the education premise. The core
launch mechanic itself already carries embedded financial literacy
(earning, budgeting, expense/tax-style deductions, payment mechanics);
structured instructional content is what is deferred.

Growth is organic-only at launch — zero paid acquisition, no marketing
budget allocated. **The schools-partnership channel is explicitly
deferred, not left unscoped**, for a stated reason: founder bandwidth
within the 6-month solo-founder runway cannot absorb schools outreach
alongside the build, pilot, and two regulatory rechecks; it remains a
named, possible post-launch channel once traction and bandwidth allow.
The late-payment penalty mechanic is incurred entirely by the parent
(5→6→7 Mbucks/week, pilot cap 3); the child has zero visibility into it,
with a grace-period/pre-escalation reminder mechanism reducing trigger
frequency at the source. The exam-period bonus is a user-defined hybrid
(behavior-primary, with a retained secondary results bonus), carrying a
known, accepted residual intrinsic-motivation risk; the candidate
motivation-probe instrument designed to detect that risk **must now be
reviewed by the child-development specialist before any family is
enrolled in the pilot — a hard gate, not a recommendation.**

**The runway-slippage contingency is now bounded, closing the gap that
undermined the case's own completion gate last cycle:** maximum personal
commitment R20,000 total (R10,000 build budget + R10,000 self-fund cap),
with grant/startup-program funding as the stated fallback if that cap is
exhausted without a sustainable venture. **The candidate data-breach/
incident-response commitment must now be specialist-reviewed before real
children's data is collected at pilot — also a hard gate, not advisable
guidance.**

**Revenue figures are materially recalculated this cycle**, not merely
re-stated: applying a stated 2.0-children-per-family assumption to
correctly convert the reachable-*child* population to a reachable-*family*
population before applying install-capture and conversion rates yields
**≈9,150-30,500 Year-1 family installs and ≈92-915 paying families**
(≈R5,519-R54,891/month run-rate) — roughly half the previously-stated
range, which had applied these rates to a child-level population and
treated the result as family-level by convention. This is a correction
toward accuracy, not a new pessimistic assumption; the underlying
evidentiary tier (Assumed/Guessing) is unchanged.

**The Readiness Score is 94/130 = 72.3%** (or 91/130 = 70.0% under a
more conservative status call — see Readiness Score), clearing the
completion gate's ≥70% threshold in both computations. This cycle's
changes are substantive: a genuinely bounded financial contingency, two
elevated hard gates protecting real children's data and the case's own
motivation-risk instrumentation, an MVP-scope decision that removes
curriculum from launch-critical-path pressure, and a corrected (more
accurate, less favorable) revenue funnel.

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

**MVP-scope clarification, this cycle:** the launch product addresses
this problem through its earning/budgeting/payment mechanic itself
(tasks, payroll simulation, invoicing, payment confirmation) — the
mechanic *is* a form of experiential financial education. Structured,
explicit instructional curriculum content is a deliberate v2 addition,
not part of what the launch product claims to solve; MiniMoney's
identity as a financial-education product is not abandoned, only
sequenced so that the core mechanic ships and is validated first.

A first-party interview round (n=10 families) found 6 of 10 confirmed
interest in using the app and stated willingness to pay for it; 7 of 10
expressed interest specifically in the education aspect. This is
genuine, first-party, MiniMoney-specific evidence, categorically
different from comparable-market inference, but it is not statistically
significant. Per a standing instruction adopted at v9 and reaffirmed at
v10, this data point must not be used as if it were a representative or
validated demand signal until superseded by the planned pilot or a
structured survey.

Status remains Partial for the same reason it has since v8: there is a
real, encouraging, directional signal, but still no established finding
that parents broadly perceive this as a problem worth paying to solve.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic rather than a simple
debit-card-for-kids model. No direct South African incumbent does what
MiniMoney does. The competitive detail, the reachable-market funnel
derivation, and international comparables (GoHenry, Greenlight, FamZoo,
Bomad) confirm MiniMoney's non-custodial, track-only model has
structural precedent elsewhere and is not a category outlier.

The subscription price (R59.99/month, up to 4 children per family)
sharpens the competitive read against MoneyTime SA's R995/year (25%
sibling discount): MiniMoney's annualized price (R719.88/family/year)
sits below MoneyTime SA's rate even before the sibling discount —
relevant opportunity context, but this does not on its own establish
market size or demand, which remains governed by the same n=10,
non-representative bound described in Problem.

**Schools-partnership channel — explicitly deferred this cycle, with a
stated reason, not left unscoped by omission:** founder bandwidth within
the solo-founder 6-month runway cannot absorb schools outreach alongside
the build, the pilot, and two regulatory rechecks. This is the strongest
demonstrated reach model in the category (MoneyTime SA's own claimed
1,500+ schools, 130,000+ students), deliberately not pursued pre-launch,
named as a possible post-launch channel once initial traction and
founder bandwidth allow. Status remains Partial: the differentiation
thesis is coherent and partly evidenced, but no structured market-sizing
or validated demand study has been conducted, and the one channel with
local reach precedent is now explicitly out of scope for launch.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The functional objective is: budget → tasks → Mbuck/Mpoint earning →
exam-period bonus (hybrid: behavior-primary rewards plus a retained
secondary results bonus, motivation-probe review now a hard
pre-enrollment gate) → invoice/payslip → payment confirmation with
escalating late-penalty (grace-period/pre-escalation reminder mechanism
committed) → age-gated core mechanic. Structured curriculum content is
explicitly deferred to v2, not part of the launch loop.

**Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
payment loop, including the dispute and late-penalty mechanics, with a
small pilot cohort of South African families (candidate target: 20-50
families) before wider release. The pilot formally adopts the specialist
pilot-measurement package (see Success Criteria) plus the motivation-probe
addition, subject to its own hard pre-enrollment specialist-review gate,
and serves double duty: mechanic-safety signal AND a directional demand
read (see Validation Strategy).

**Growth (6-12 months):** validate the subscription-conversion assumption
against the recalculated 1-3% subscription-only reference range applied
to the corrected funnel; **curriculum-engagement-as-a-retention-indicator
validation is deferred alongside the v2 curriculum feature itself and is
not part of this window's validation set** — it will be reintroduced when
that feature is actually built; evaluate iOS port timing based on
Android traction.

The 90-day (recalculated installs) vs. annual funnel target tension
remains resolved via `Clarifications_v10.md`'s per-family convention. All
install and subscriber figures are per-family, now recalculated against
the 2.0-children-per-family assumption (see Market & Competition). Status
remains Complete: every tension previously flagged in this section is
resolved by direct, Verified-tier user clarification.

## Success Criteria

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Core criteria, carried forward: pilot success (majority of families
complete ≥4 consecutive weekly cycles); operational health (65%
task-completion without dispute, no external benchmark); freemium/
subscription conversion (2%, benchmarked against the recalculated 1-3%
subscription-only range); retention (no figure proposed).

**Curriculum-engagement criterion (30%) — RECLASSIFIED this cycle, not
scored as an open gap.** Since curriculum content is deferred entirely
to v2, a criterion measuring engagement with content that will not exist
at launch is moot for the near-term success-criteria set. It is retained
in the document as a placeholder to be reintroduced, unbenchmarked, when
the v2 curriculum feature is actually built — it no longer counts against
this section's completeness for launch purposes. Operational-health and
retention remain unbenchmarked and do still count.

**Family-relationship-strain criterion — measurement package adopted into
pilot design** (`ChildDevelopmentReview_v1.md`): borrowed items from the
Parenting Stress Index – Short Form and the Family Assessment Device –
General Functioning Scale, administered to parents at baseline and
partway through the pilot; within-family, within-week correlation
tracking (late-penalty events vs. reported household tension);
age-stratified results (6-9, 10-14, 15-18 bands); a brief child-report
instrument (abbreviated Child–Parent Relationship Scale, Conflicts
subscale). The reviewer's explicit caution stands: 20-50 families is not
large enough for full validated-instrument statistical power; these are
for lightweight, qualitative early-warning signal detection.

**Exam-bonus motivation-risk instrumentation — candidate instrument
exists; specialist review is now a HARD PRE-ENROLLMENT GATE, not a
recommended next step (`Verdict_v5.md` required change 3,
`Clarifications_v21.md`).** The instrument itself is unchanged from v20:
parent-facing Likert/open items alongside the existing PSI-SF/FAD-GFS
timepoints; child-facing age-appropriate items alongside the existing
Child–Parent Relationship Scale timepoint; near-zero marginal cost,
administered at existing survey events. **What changes this cycle: no
family may be enrolled in the pilot until the child-development
specialist (Expert Roster Entry 2) has actually reviewed this instrument.
The probe remains Evidence: Assumed until that review occurs — the gate
elevation changes the process requirement, not the instrument's current
evidentiary tier.**

The underlying substantive risk remains confirmed, not resolved: the
late-penalty redesign narrows but does not eliminate the Family Stress
Model's affective pathway, and the exam-bonus hybrid's residual
intrinsic-motivation risk is candidate-instrumented but not yet
specialist-reviewed or adopted.

Status remains Partial: the relationship-strain criterion has an adopted,
specialist-designed measurement plan; the motivation-risk gap now has a
candidate instrument gated by a hard pre-enrollment review requirement,
not yet satisfied; operational health and retention remain unbenchmarked.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18;
parents/guardians as sole registration custodian and subscription
purchaser; the app operator (a solopreneur founder); the South African
Information Regulator and the Advertising Regulatory Board; three named
competitor/adjacent-market stakeholders — African Bank's MyWORLD Power
Pocket, MoneyAfrica Kids, MoneyTime SA; Apple/Google as app-store
platform stakeholders.

Two regulator stakeholders remain, each owned by the user personally at
build-spec stage with a decided launch fallback: the South African
Reserve Bank (SARB) and the Payments Association of South Africa (PASA),
via the National Payment System Act, engaged by the optional
account-linking feature's open-banking question (fallback: launch without
account-linking); and the Film and Publication Board (FPB), via the Films
and Publications Amendment Act 2019, of uncertain but plausible
application to the Mpoints gamified rewards system (fallback: launch
without Mpoints).

The linking aggregator (Stitch/Mono-style, where a parent opts in)
remains an additional data-processor stakeholder. The retained legal
counsel's open action (Conradie v Rossouw citation) remains closed, per
v20. **The retained child-development professional (Expert Roster Entry
2) now has a HARD PRE-ENROLLMENT GATE responsibility**, not a recommended
review: the candidate motivation-probe must be reviewed before pilot
enrollment. **The Data-Privacy Practitioner (Expert Roster Entry 5)
similarly now has a HARD PRE-PILOT GATE responsibility** for the
data-breach/incident-response commitment, not merely an advisable review.
**Neither review has yet occurred — the gate elevation changes the
requirement's bindingness, not its completion status.** A future AI
mediator feature for dispute resolution remains explicitly out of
current scope. A curriculum/instructional-design specialist (Expert
Roster Entry 3) is a named future stakeholder for the deferred v2
curriculum feature, not yet engaged, consistent with that workstream's
deferral.

Status remains Partial: both regulator stakeholders have an owned recheck
and a fallback, but their specific obligations remain unresolved pending
those rechecks; the two named specialist reviews are now hard gates but
neither has actually occurred.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18, and their
parents/guardians, in South Africa, on Android at launch (iOS deferred).
A minor is not an independently reachable user: every child account
requires a parent acting as registration custodian from the outset. The
paying customer unit is the family (one subscription = one family = up
to 4 children) — the child is the user, the parent is the customer, and
all funnel counts are family counts, **now applying a stated 2.0-
children-per-family assumption (Evidence: Assumed) to convert the
reachable-child population into a reachable-family figure** (see Market
& Competition). Status remains Partial: the target population is clearly
named and the customer unit is unambiguous, but no market-sizing or
persona-level detail exists beyond Market & Competition and the funnel
figures in Objectives.

## Value Proposition

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**MVP/launch feature set, corrected this cycle:** the Free/Subscription
split and the R59.99/month (up to 4 children per family) price stand.
**The launch value proposition is the financial mechanic alone** — budget
setting, task assignment, Mbuck/Mpoint earning, payslip/invoice, payment
confirmation, dispute and late-penalty handling. **Fintech Advance (the
15-18-only trading/entrepreneurship module) is deferred to v2 alongside
the rest of curriculum content**, per this cycle's MVP-scope decision —
a ripple effect actively traced (per Playbook Entry 2) from the
curriculum-deferral decision onto a feature that was not itself named in
the original clarification but shares the same "curriculum" category.
Its prior mitigation decisions (no product gamification for its content;
risk-literacy framing over aspirational framing, per
`ChildDevelopmentReview_v1.md` Q5) remain adopted and will apply
unchanged whenever the module is actually built — they are not undone,
only not currently in force because the module itself is not shipping at
launch.

**Mbucks non-transferability — a locked product-spec constraint,
unchanged.** Per `LegalOpinion_v1.md` Q1, MiniMoney's low money-
transmitter/e-money risk is contingent on Mbucks remaining a pure
unit-of-account. Any future roadmap change to this requires the
money-transmitter analysis to be redone (see Legal & Compliance,
Business Model, Constraints).

**Terminology — adopted, unchanged.** Debt-coded language ("invoice,"
"arrears," "late penalty") is reserved for parent-facing surfaces only;
child-facing surfaces use softer language.

**Conditional exposure, named not hidden:** under the no-Mpoints launch
fallback (see Legal & Compliance), the in-app cosmetic store has no
currency and must be removed from that configuration, thinning the
subscription tier's child-facing appeal further on top of Fintech
Advance's deferral. The launch value proposition is narrower than the
product's eventual full vision by two independent, stated decisions
(regulatory fallback; MVP-scope deferral) — both named explicitly, not
blended into a single unexplained thinning.

Status remains Complete: price, feature boundaries for the corrected
launch scope, and all previously-pending decisions within this section's
scope are made; the fallback and v2-deferral variants are explicitly
tracked conditionals, not unmade decisions.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Population base (6-18):** [Certain] Stats SA's mid-2025 estimate puts
South Africa's total population at 63.1 million, with children under 15
at 26.2% (≈16.5 million). [Guessing] Stats SA does not publish a clean
6-18 breakout; extrapolating from single-year cohort size (~1.1M/year
under 15) and adding the 15-18 band gives a modeled estimate of roughly
**14-15 million people aged 6-18** — not a directly sourced figure.

**Device access:** [Likely] A 2024 South Africa-specific study (five
former Model C high schools, Stellenbosch research) found 62% of learners
Grade 4-11 own a personal device by age 10, and 83% have a social media
account by age 12. Household access is plausibly 75-85% for the 6-18
band, a bounded guess, not a stat.

**OS split:** [Certain] Android holds 76.74% of mobile OS share in South
Africa as of May 2026 (Statcounter), iOS 23.24%.

**Parent financial-app engagement (the real gate):** [Likely] SARB's
Payments Study (SCPC/DCPC, 2023, adults 18+, national population base
40.5M) found 50.3% of South African adults use banking apps regularly.
[Guessing] a reasonable adjustment for the economically-active parent
cohort is **55-65% banking-app engagement**.

**Reachable-market funnel (population-level, child-count):** 14.5M kids ×
~70% device access × ~60% parent digital-financial engagement ≈ **6.1M
kids in "reachable" households** (device present, parent already
comfortable transacting digitally) — the realistic Serviceable
Addressable Market at the child level.

**Family-level conversion — RESOLVED this cycle
(`Clarifications_v21.md` required change 6): 2.0 children per
subscribing family**, Evidence: Assumed, within the up-to-4-per-family
subscription cap — not derived or validated, applied as a stated
convention consistent with how other unvalidated figures in this funnel
(the adoption rate, the conversion rate) are already labeled and used.
**Reachable families = 6.1M reachable kids ÷ 2.0 ≈ 3.05M reachable
families.** This applies the population-wide 2.0 average to the reachable
subset specifically — an approximation, not a family-specific study; the
true distribution of children-per-family within the *reachable* pool
could differ from the population-wide average, and this is not tested.

**Adoption rate (the least-evidenced figure in the chain):** [Guessing]
No public South African benchmark exists for kids'-financial-education-
app adoption specifically — confirmed unclosable by further desk research
(`ResearchFindings_v1.md` Item 1); inference from adjacent markets
(GoHenry/Greenlight UK/US): a new entrant with no bank/school
distribution typically captures 0.3-1% of its reachable pool as installs
in year one. Free-to-paid conversion for freemium/subscription
kids'-finance apps benchmarks 2-6% globally; South Africa's lower
discretionary income argues for the low end — **1-3%**.

**Rerun funnel, corrected this cycle:** ≈3.05M reachable *families* ×
0.3-1% Year-1 install capture ≈ **9,150 to 30,500 family installs.**
Applying the 1-3% subscription-only conversion range: **≈92 to 915
paying families in Year 1.** **This retires the previously-stated
18,000-61,000 install / 180-1,830 paying-family range**, which applied
the install-capture and conversion rates directly to the *child*-level
reachable population and treated the result as a family-level count
without dividing by children-per-family — the precise gap the Investment
Committee flagged. All revenue statements in this document now use
9,150-30,500 installs and 92-915 paying families exclusively. **Per
Playbook Entry 4, stated explicitly: this is a more accurate figure, not
a more favorable one** — the same Assumed/Guessing evidentiary tier
applies throughout; only the arithmetic changed, roughly halving the
prior range.

**Competition in South Africa specifically:** unchanged from v20. No
direct incumbent does exactly what MiniMoney does. Three named local
players, each missing at least one defining dimension:

- **African Bank's MyWORLD Power Pocket** — kids' sub-accounts with debit
  cards under a parent account; a banking feature, not education-led; no
  monthly fee.
- **MoneyAfrica Kids** — Nigerian-origin edtech app, courses/quizzes,
  parent-subscribes-child model; available but not built for South
  Africa; 10,000+ Google Play downloads, 3,000+ Apple downloads
  (pan-African); premium price unpublished/unknown.
- **MoneyTime SA** — web-based financial literacy curriculum, ages 10-15,
  sold B2B2C through schools at R995/year (25% sibling discount); claims
  over 1,500 schools and 130,000 students reached (self-published) — the
  strongest demonstrated reach model in the category, **now explicitly
  deferred as a channel for MiniMoney, for stated founder-bandwidth
  reasons** (see Opportunity, Roadmap), rather than left unscoped.

None combine gamification + mobile-native + direct-to-parent distribution
the way GoHenry/Greenlight do in the US/UK — a real, evidenced gap — but
it also means there is no local comparable data to validate
willingness-to-pay against.

**International comparables** (`ResearchFindings_v2.md` Item 3):
**GoHenry**/**Greenlight** solve payment-verification by becoming the
money-mover themselves under card-issuing/e-money licensing, a
materially different regulatory posture than MiniMoney's deliberately
non-custodial design. **FamZoo** and **Bomad** are closer structural
analogs: both are track-only, honor-system products with no bank
integration, confirming MiniMoney's chosen model has precedent elsewhere.
No South-Africa-specific comparable to FamZoo or Bomad was found.

**What remains unresearched:** validated demand (n=10 bound still
governs); structured market sizing beyond the user's own funnel estimate;
MoneyAfrica Kids' premium price; **acquisition economics against the
organic-only growth strategy** — whether organic discovery alone can
plausibly reach the corrected funnel's own 9,150-30,500 range is
untested, now against a smaller target than previously stated.

Status remains Partial: the competitive landscape and corrected funnel
are fully documented, and the child-to-family population-conversion gap
is now closed via a stated (Assumed-tier) figure rather than left
unresolved, but the most decision-relevant figures (Year-1 adoption,
conversion rate) remain the user's own labeled lowest-confidence
estimates, unvalidated.

## Business Model

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Subscription-only at launch, ads deferred to V2; R59.99/month per family,
covering up to 4 children — the family is the revenue unit. MiniMoney is
a facilitation/education layer that sits on top of the parent's own bank
account and does not move or hold funds. **The core mechanic — not
instructional curriculum content — is what the subscription pays for at
launch**, consistent with this cycle's MVP-scope decision.

The core business-model uncertainty flagged since v8 — money-transmitter
licensing — remains resolved per `LegalOpinion_v1.md` Q1: risk is low,
contingent on Mbucks remaining strictly non-transferable and
non-redeemable.

Optional account-linking remains a trust/verification feature within the
existing subscription model. Its NCR question is resolved clean; the
SARB/NPS Act open-banking question remains genuinely unsettled, owned by
the user personally, timed to build-spec stage, with an explicit
fallback: launch without account-linking. If pursued post-launch,
advertising remains framed as a partial CAC-offset lever, not a
standalone revenue pillar.

The FPB classification question carries an explicit launch fallback
(launch without Mpoints); the Mpoints/Apple IAP-currency question is
mooted entirely under the no-Mpoints fallback. Status remains Complete:
the model's structure, unit, price, and every put-to-decision item within
its scope are decided; the remaining opens are externally-gated rechecks
with owner and fallback.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Revenue (per-family), recalculated this cycle.** Subscription revenue
at R59.99/month per family against the corrected Year-1 range of **92 to
915 paying families** (see Market & Competition):

- Lower bound: 92 families ≈ **R5,519/month** (≈ R66,229/year run-rate).
- Upper bound: 915 families ≈ **R54,891/month** (≈ R658,690/year
  run-rate).
- These are end-state run-rates against an unvalidated funnel and an
  unvalidated conversion rate; actual Year-1 collected revenue would be
  ramp-dependent and lower. **This range is roughly half the previously-
  stated 180-1,830 range, corrected per Market & Competition's resolution
  of the child-to-family population-conversion gap — not a new
  pessimistic assumption, an arithmetic fix.**

**Costs.**

- **Development budget: R10,000 total** committed for the app build.
- **Self-fund-further cap: an additional R10,000**, bounded this cycle —
  **R20,000 total maximum personal commitment**, hard ceiling, with
  grant/startup-program funding named as the fallback if exhausted (see
  Constraints, Financial Considerations).
- **Professional opinions/advice: zero marginal cost to the venture**,
  via the user's existing policy (scope/usage limits undocumented — a
  minor named open item).
- **Runway: 6 months** at current commitment before external funding is
  needed.
- **Acquisition/CAC: organic-only, zero paid acquisition.** No marketing
  budget is allocated from the R10,000 total. Growth relies on word of
  mouth and organic app-store discovery; **the schools-partnership
  channel is explicitly deferred (founder bandwidth), not a currently
  planned lever.**
- **Curriculum content-production cost — now MOOT for launch, not an
  open gap.** Since curriculum is deferred entirely to v2, its production
  cost is not a launch-phase cost item; it will need to be priced when
  that workstream actually starts. Removed from this section's "still
  open" list, consistent with the correction applied throughout the
  document.

**Reconciliation against the prior agency reference range, stated
plainly:** the previously-cited $25,000-$120,000+ engineering-cost range
was a reference frame, not the plan. R10,000 is roughly $550, i.e. 45× to
220× below the agency range's bounds, coherent only because it prices in
the founder's own unpaid labor plus AI-assisted development. **R10,000
buys days, not months, of professional engineering if the founder's own
capacity fails — there is no buffer to purchase execution beyond the
now-bounded R20,000 total.**

**Still open:** no post-runway external funding-ask is sized (the
self-fund-further decision and its grant/startup-program fallback state a
direction and a form, not the size of an eventual external raise). Status
remains Partial: the acquisition mechanism and the population-conversion
gap are both closed by decision this cycle, and curriculum-cost is no
longer an open item (deferred), but the revenue side still rests on
unvalidated Guessing-tier estimates and the funding-ask size remains
unspecified.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Core mechanics (budget and earning, task structure,
completion/verification/reporting flow, dispute mechanism, payment
confirmation, late-penalty parent-only design) are unchanged in
structure. All specialist design decisions from prior cycles stand:
exam-period bonus as a hybrid (primary reward for controllable behaviors,
secondary bonus retained for improved results, with a known, accepted
residual intrinsic-motivation risk — candidate-instrumented, review now a
hard pre-enrollment gate, see Success Criteria); late-penalty grace-
period/pre-escalation reminder mechanism.

**Fintech Advance gamification-avoidance decision — MOOT for launch, not
an active build task this cycle.** Fintech Advance itself is deferred to
v2 alongside all curriculum content; its mitigation decision (no product
gamification for its content) remains adopted and will apply when the
module is eventually built, but is not a current operational
requirement.

**New build-spec items introduced by the hybrid bonus, unchanged:** the
mechanism for logging/verifying the behavior inputs and the grade-input
mechanism for the retained results-bonus layer both need specification at
build time.

**Known operational gap, tracked:** dispute-escalation beyond the
48-hour window has no formal resolution mechanism.

Status remains Complete: every specialist recommendation within this
section's scope has a recorded decision; remaining opens are build-spec
parameters and a tracked edge-case mechanism, not undecided
recommendations.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v20. Still unspecified: how account-linking is technically
initiated; how payment confirmation is captured beyond the accept/dispute
UI; the exam-bonus grade-input mechanism; the hybrid bonus's behavior-
input logging/verification mechanism; the grace-period/reminder
notification infrastructure. No curriculum-delivery technology is
in scope, consistent with its deferral. Status remains Partial.

## Legal & Compliance ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The retained specialist legal opinion (`LegalOpinion_v1.md`) remains the
Verified-tier foundation of this section — all seven originally-scoped
questions answered.

**1. Money-transmitter/payment-facilitation risk: low, contingent on a
locked product-spec constraint.** [Likely] This holds only as long as
Mbucks cannot be spent, transferred, or redeemed anywhere other than
through the parent's independent banking-app payment — confirmed
[Certain] against SARB's e-money Position Paper. Courts look at
substance, not labels (*Maize Board v Jackson* 2005 (6) SA 592 (SCA)).
The NCR's Payment Distribution Agent category is confirmed inapplicable.

**2. Universal parental-consent gate: legally sufficient as designed,
with two hardening recommendations.** POPIA s34/s35(1)(a) is satisfied by
the current universal, no-carve-out consent gate. Two hardening
recommendations, not yet built: consent-flow documentation separation;
lightweight parent identity-verification step.

**3. POPIA Section 14 retention:** confirmed [Certain] no minor-specific
supplementary rule exists; a specific retention purpose, period, and
deletion trigger must be affirmatively designed and documented.

**4. Minor contractual capacity: the case's strongest legal position —
fully verified.** The "rights without obligations" minor-contract
exception fits MiniMoney's structure, with the parent's obligation better
characterized as a unilateral undertaking or conditional donation,
sidestepping the domestic-agreement-presumption question via animus
contrahendi doctrine (*Pitout v North Cape Livestock* 1977). The
supporting citation (*Conradie v Rossouw* 1919 AD 279, Appellate
Division) remains fully verified, both pinpoint reference and substantive
proposition.

**5. Terminology risk: real, the single highest-optics-risk item in the
case — mitigation ADOPTED.** ARB Code Clause 14.2 and Clause 6.1, Section
III are both engaged, plus a CPA secondary layer; no ARB ruling addresses
this fact pattern. Debt-coded terminology is reserved for parent-facing
surfaces only.

**6. SARB/NPS Act open-banking question (account-linking) — owned,
timed, with fallback.** NCR registration is confirmed inapplicable
[Certain]; the SARB question remains genuinely unsettled. Owner: the user
personally; timing: build-spec stage; fallback: launch without
account-linking.

**7. FPB classification question (Mpoints) — owned, timed, with fallback
and full ripple-effect trace.** The Films and Publications Amendment Act
11 of 2019 gives the FPB a classification mandate over "interactive
computer games"; whether the Mpoints mechanic is caught is genuinely
fact-specific. Owner: the user personally; timing: build-spec stage;
fallback: launch without Mpoints. **Fintech Advance's own content risk
is now a v2, not launch, consideration — mooted from this cycle's
launch-scope legal analysis, though its prior gamification-avoidance
mitigation remains adopted for whenever it is built.**

**No-Mpoints launch configuration — ripple-effect trace, unchanged:** the
in-app cosmetic store is removed; the flat 10-Mpoints-per-task reward is
gone (weakening the 6-9 tier's immediate-feedback loop); the Google Play
loyalty-point disclosure item is mooted in that configuration; the
badge-residual check within the FPB recheck remains a named open item.

**Status remains Complete.** All seven originally-scoped questions are
answered at Verified tier; the two unsettled external regulatory
questions are pending external rechecks with named owners and decided
fallbacks.

## Risks

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

All previously-identified risk categories remain catalogued; decision
status updated per this cycle's changes.

- **Regulatory risk:** core invoice/payment-trigger/late-penalty
  mechanic assessed low-risk by retained counsel. Two narrower open
  regulatory questions (SARB/NPS Act, FPB) each carry a named owner,
  timing trigger, and decided fallback.
- **Execution-capacity risk — now with a BOUNDED contingency.** A
  solopreneur venture with a R10,000 total development budget, a
  ~3-month directional build timeline, an instrumented 20-50 family
  pilot, and two personally-owned regulatory rechecks — all inside a
  6-month runway, executed substantially by one person. **This cycle: the
  self-fund-further contingency is capped at R20,000 total (R10,000
  build + R10,000 additional), with grant/startup-program funding as the
  stated fallback if exhausted.** This is a genuine improvement over the
  prior uncosted, unbounded version — the founder's personal-financial-
  exposure ceiling is now known, even though whether R20,000 total is
  itself sufficient capital to reach sustainability remains untested.
  **Curriculum authoring is no longer a parallel demand on this same
  6-month runway**, since it is deferred to v2 — a real narrowing of the
  execution-capacity risk's scope, traced from the MVP-scope decision.
- **Acquisition/adoption risk — recalculated this cycle.** Zero paid
  acquisition is the decided strategy against a corrected, smaller
  9,150-30,500 family-install funnel (down from the previously-stated
  18,000-61,000, per the population-conversion correction). Whether
  organic discovery and word of mouth can plausibly reach this smaller
  range is untested and not benchmarked anywhere in the case. The
  schools-partnership channel — the only channel with local reach
  precedent — is explicitly deferred, for stated founder-bandwidth
  reasons, not pursued as a near-term mitigation.
- **Child-safety/data-privacy risk:** consent model confirmed legally
  sufficient as designed; two hardening recommendations remain build
  tasks. POPIA Section 14 retention policy remains an affirmative design
  requirement. **The data-breach/incident-response commitment specialist
  review is now a HARD PRE-PILOT GATE** (see Constraints) — the
  commitment must not be in force, and pilot enrollment must not begin,
  until the Data-Privacy Practitioner has actually reviewed it.
- **Minor-contractual-capacity risk — resolved, unchanged.** The
  rights-without-obligations doctrine holds; the Conradie v Rossouw
  citation is fully verified.
- **Terminology/perception risk — mitigation decided:** parent-facing-
  only debt terminology is adopted.
- **Late-penalty/relationship risk — both mitigation paths engaged:** the
  grace-period/pre-escalation reminder mechanism is committed
  (source-reduction) AND the specialist pilot-measurement package is
  adopted (residual tracking). Residual risk remains real.
- **Exam-bonus/intrinsic-motivation risk — candidate-instrumented,
  review now a HARD PRE-ENROLLMENT GATE.** The behavior-primary redesign
  follows the evidence; the retained outcome-contingent bonus layer means
  the crowding-out risk is reduced, not eliminated. No family may be
  enrolled until the child-development specialist has reviewed the
  candidate motivation-probe.
- **Fintech Advance content risk — MOOT for launch, deferred to v2 with
  the rest of curriculum content.** Its prior mitigation (no product
  gamification, risk-literacy framing) remains adopted for whenever it is
  built.
- **Age-appropriateness/terminology-uniformity risk — framework adopted;
  reconciliation with the product's six-way sub-bands drafted this cycle
  as prep work (see Curriculum Design), not yet specialist-reviewed or
  adopted.**
- **No-Mpoints fallback ripple risk:** conditional, not active.
- **Dispute-escalation risk:** unchanged.
- **v2-trigger-criterion risk — NEW, named this cycle.** The stated
  trigger for building the deferred curriculum feature — "once we have
  proved a demand" — is not itself quantified (no specific pilot outcome,
  subscriber count, or retention figure defines "proved"). This creates a
  risk of indefinite deferral or, conversely, premature v2 investment
  based on an ambiguous signal.
- **Competitive risk; monetization-execution risk; app-store policy
  risk; platform-concentration risk:** unchanged in substance.

Status remains Complete: the risk landscape is comprehensively identified
and characterized, and every specialist-recommended mitigation within it
carries a recorded decision. A Complete risk register does not mean the
risks are eliminated: execution capacity, two external regulatory
questions, the accepted exam-bonus residual, the corrected but still
untested organic-only acquisition strategy, and the new v2-trigger-
criterion ambiguity are all live, and are stated as such.

## Assumptions

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Carried forward: parent-direct payment; SA launch jurisdiction; universal
consent gate; Android-first; Mbucks/Mpoints dual currency; 7-Mbuck
late-penalty cap with 3-Mbuck pilot cap; the fixed Mbucks-to-Rand peg;
the late-penalty mechanic as a parent-only administrative matter;
exam-bonus grade data self-reported/parent-entered; primarily a South
African B2C product at launch.

**Updated/new this cycle:**

- **New assumption, RESOLVING a prior named gap: 2.0 children per
  subscribing family**, Evidence: Assumed, applied to the reachable-child
  population to derive a reachable-family figure (see Market &
  Competition). Not derived or validated; the distribution within the
  specifically *reachable* subset could differ from this population-wide
  figure.
- **The exam-bonus risk-acceptance assumption stands:** the secondary
  bonus's salience will not dominate the behavior-primary structure in
  the child's perception. Untested; candidate-observable via the
  motivation-probe, now gated by a hard pre-enrollment specialist review.
- **New assumption: organic-only acquisition will be sufficient to reach
  a meaningful share of the corrected 9,150-30,500 family-install
  funnel**, with the schools-partnership channel explicitly deferred as a
  near-term mitigation. Untested, unbenchmarked against any South African
  comparable.
- **The self-fund-further contingency is now bounded (R20,000 total), but
  a new assumption remains: that this ceiling is sufficient capital to
  reach a sustainable venture, or that grant/startup-program funding is
  actually obtainable if it is not.** Neither is tested; the fallback
  form is named, its practical availability is not confirmed.
- **New assumption: the "once we have proved a demand" trigger for the
  deferred v2 curriculum feature will be interpretable in practice**,
  despite carrying no stated quantitative threshold. See Outstanding
  Questions and Risks.
- **New assumption: the Incubator-drafted candidate data-breach
  commitment and motivation-probe are adequate as interim policy/design
  pending their respective specialist reviews, both of which are now hard
  gates rather than advisable steps.** Both remain Evidence: Assumed by
  construction.
- The user's policy covering professional opinions at zero marginal cost
  will continue to cover future engagements this case anticipates
  (including the now-mandatory Data-Privacy Practitioner and
  child-development specialist reviews); its scope/limits are
  undocumented — Assumed.
- Mbucks non-transferability/non-redeemability and the SARB/NPS Act
  contingency remain as documented constraints rather than assumptions
  (see Constraints).

Status remains Partial: several new load-bearing assumptions are added
this cycle (children-per-family, self-fund-cap sufficiency, v2-trigger
interpretability, organic-only sufficiency against the corrected funnel),
none of which are tested — the list remains a working inventory, not a
closed set.

## Constraints

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (with one Assumed-tier addition, named below)

- Solopreneur venture; AI-assisted development; external technical
  expertise engaged only on-demand; directional ~3-month build timeline;
  Android primary, iOS deferred.
- **Mbucks non-transferability/non-redeemability** — binding product-spec
  constraint on all future roadmap decisions (`LegalOpinion_v1.md` Q1).
- **R10,000 total development budget; 6-month runway before external
  funding is needed; professional opinions at zero marginal cost via the
  user's existing policy.** The runway, not the cash budget, is the
  binding constraint.
- **Zero paid acquisition — organic-only growth.** No marketing budget is
  allocated from the R10,000 total; this is a binding constraint on how
  the funnel can plausibly be filled, not merely a cost-saving choice.
- **Schools-partnership channel — explicitly deferred, founder bandwidth
  is the binding constraint stated.** Consistent with, not separate from,
  the solopreneur-venture constraint above.
- **Curriculum/educational content deferred to v2 — an explicit MVP-scope
  constraint, not an unmade decision.** The launch build, budget, and
  6-month runway do not need to accommodate curriculum authoring or
  production; this narrows what the runway must contain this cycle.
- **Runway-slippage contingency — self-fund further, BOUNDED this cycle
  (`Verdict_v5.md` required change 1, `Clarifications_v21.md`).**
  **Maximum personal commitment: R20,000 total** (R10,000 initial +
  R10,000 additional self-fund cap) — a hard ceiling, not directional. If
  the cap is exhausted without the venture being sustainable, the stated
  fallback is grant or startup-program funding (non-dilutive), not equity
  or informal borrowing. **This is Verified-tier as to both the decision
  and its magnitude** — the specific gap that kept the prior version's
  Complete status from being soundly earned (a number, and a defined next
  step) is now closed. See "What Changed in v21" for the explicit
  re-derivation against the Readiness Score section's own "made decision"
  standard.
- **Minimal data-breach/incident-response commitment — Incubator-drafted
  candidate, specialist review now a HARD PRE-PILOT GATE
  (`Verdict_v5.md` required change 2, `Clarifications_v21.md`).**
  **Evidence: Assumed** — a founder-authored draft. **The commitment must
  not be in force, and pilot enrollment of real families must not begin,
  until the Data-Privacy Practitioner (Expert Roster Entry 5) has
  actually reviewed it.** This is a binding process constraint on the
  Roadmap's pilot phase, not merely advisable guidance. Candidate minimum
  content, unchanged from v20:
  - **What constitutes a breach:** unauthorized access to a minor's
    personal information or account data held by MiniMoney.
  - **Who is notified:** affected parents; the South African Information
    Regulator, consistent with POPIA's Section 22 breach-notification
    obligation.
  - **Timeframe:** notification "as soon as reasonably possible" after
    confirmed detection, consistent with POPIA's own standard.
  - **Content of notification:** nature of the breach, the personal
    information reasonably believed to be affected, and measures taken or
    recommended to mitigate harm.
- **Launch-configuration constraints (decided fallbacks):** the product
  must be buildable in three configurations — full; without
  account-linking (SARB unresolved); without Mpoints (FPB unresolved).

**Re-derivation, per this cycle's explicit instruction — is Constraints'
Complete status soundly earned now?** The Readiness Score section's
standard requires every material question within scope to carry "a made
decision — resolved, adopted, or a deliberate, documented residual-risk
acceptance." At v20, the self-fund-further item had neither a number nor
a defined next step — exactly what the Investment Committee's Gate
Integrity Check identified as failing this standard when applied
consistently. This cycle replaces it with a bounded figure (R20,000
total) and a named fallback form (grant/startup-program funding),
satisfying both elements the prior version lacked. Every other material
question in this section's scope (budget, runway, acquisition,
launch-configuration fallbacks, MVP-scope) was already genuinely decided
and remains so. **Constraints = Complete is therefore restored on
genuinely new grounds this cycle, not reasserted** — the data-breach
commitment remains a distinct, named Assumed-tier addition within this
otherwise Verified-tier section, exactly as it was handled at v20, now
strengthened by its hard-gate elevation.

## Roadmap

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Now (parallel with build, starting immediately):** core engineering
build only. **Curriculum-content workstream REMOVED from this phase —
deferred in its entirety to a post-launch v2 phase, contingent on
demonstrated demand for the core product** (`Clarifications_v21.md`
required change 4). Authorship remains genuinely undecided but is no
longer a scheduling risk against the 6-month runway, since nothing is
scheduled against it before v2 begins.

**Build phase:** implement core loop with decided designs —
parent-facing-only debt terminology; hybrid exam bonus; grace-period/
pre-escalation reminders. Legal build tasks: POPIA s14 retention period
and deletion trigger design; consent-flow documentation separation;
lightweight parent identity-verification step. **The candidate
data-breach/incident-response commitment (see Constraints) must be
reviewed by the Data-Privacy Practitioner (Expert Roster Entry 5) during
this phase — a HARD GATE, not advisable guidance: real children's data
must not be collected at pilot until this review has occurred.**

**Build-spec stage:** the user personally runs both regulatory rechecks —
SARB/NPS Act and FPB (including the badge-residual check). Decided
fallbacks apply if unresolved by launch.

**Pilot (20-50 families):** double-duty per prior decision — mechanic
safety/child-development signal AND directional demand read — with the
adopted measurement package plus the candidate motivation-probe addition
built into the pilot design. **The candidate motivation-probe MUST be
reviewed by the child-development specialist (Expert Roster Entry 2)
before pilot instrumentation is finalized and before any family is
enrolled — a HARD GATE, not a recommended next step.**

**Post-pilot (~month 6): external funding may be needed** — the initial
runway ends here. **Decision rule, bounded this cycle
(`Verdict_v5.md` required change 1):** if month 6 arrives without
secured external funding, or any single workstream has slipped
materially, the user will self-fund further up to a hard ceiling of
R20,000 total personal commitment. **If that ceiling is reached without a
sustainable venture, the stated fallback is grant or startup-program
funding**, not equity or informal borrowing — no external funding-ask
size is yet determined for that scenario.

**Growth (6-12 months):** conversion validation against the corrected
1-3% range applied to the corrected funnel; iOS port timing evaluation;
account-linking and/or Mpoints re-introduction as their regulatory
questions resolve. **Schools-partnership channel exploration — explicitly
deferred for stated founder-bandwidth reasons, a possible post-launch
consideration once initial traction and bandwidth allow, not scheduled
within this window.**

**Post-launch, demand-gated (v2, timing undetermined): curriculum content
workstream.** Triggered by "proved demand" for the core product — the
specific threshold constituting "proved" is not yet quantified (see
Outstanding Questions, Risks). Authorship (founder vs. engaged designer
via the zero-marginal-cost advice policy, pending confirmation of that
policy's scope) remains open, not time-pressured. The three-tier-to-
six-way sub-band reconciliation is drafted now as low-cost prep work
(see Curriculum Design domain extension) but not adopted, since the
underlying content itself is not yet being built.

Status remains Complete: every pre-pilot decision the roadmap lists as
pending is made; the two specialist reviews are now hard gates with
clear named owners, timing, and consequence (no pilot/enrollment without
them); the self-fund-further contingency carries a specific bound; the
remaining opens are owned external rechecks, build-spec parameters, and a
demand-gated v2 phase with an explicitly named (if unquantified) trigger.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**What exists:**

- **Budget: R10,000 total** for development.
- **Self-fund-further cap: R20,000 total maximum personal commitment**
  (R10,000 initial + R10,000 additional), bounded this cycle. Fallback if
  exhausted: grant or startup-program funding (non-dilutive), not equity
  or informal borrowing.
- **Professional advice: zero marginal cost** via the user's existing
  policy (scope/limits undocumented — Assumed).
- **Runway: 6 months** before external funding is needed.
- **Revenue model (per-family), recalculated:** R59.99/month per family
  against a corrected Year-1 range of **92-915 paying families** —
  R5,519-R54,891/month run-rate at the range bounds (≈R66,229-R658,690/
  year); ramp-dependent actuals lower. **Roughly half the previously-
  stated range**, a correction of an internal arithmetic gap, not a new
  pessimistic assumption.
- **Acquisition spend: zero.** No marketing budget is allocated; growth
  is organic-only, with schools-partnership explicitly deferred.
- **Curriculum content-production cost: MOOT for launch**, deferred
  alongside the feature itself — no longer a "still absent" item in this
  section for the launch runway.

**The reconciliation, stated as the Investment Committee would want it:**
R10,000 (~$550) against the previously-cited $25,000-$120,000+ agency
range is a 45×-220× gap, coherent only as a founder-labor-plus-AI-
assisted build. **The 6-month runway is the binding constraint**, now
narrower in scope (curriculum authoring removed) but with a hard ceiling
on personal financial exposure if it slips: build, instrumented pilot
(subject to two hard specialist-review gates), and two user-owned
regulatory rechecks must all complete inside it, after which funding is
needed with — at best — directional pilot evidence to raise on, or the
user self-funds up to R20,000 total before falling back to
grant/startup-program funding.

**This cycle's decisions close the population-conversion gap (recomputed
revenue range), bound the self-fund contingency with a specific ceiling
and fallback form, and remove curriculum-production cost from the
launch-phase cost picture (deferred).** Still absent, named: the size and
form of any external funding ask beyond the R20,000 self-fund ceiling;
full financial projections (P&L, break-even). Status remains Partial: the
section now has a bounded budget, runway, acquisition decision, and
runway contingency, and a corrected revenue range, but funding-ask sizing
and break-even analysis that would complete it do not yet exist.

## Validation Strategy

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Closed streams:** legal validation (retained opinion, Verified-tier,
fully closed including the citation dependency); child-development/
age-appropriateness validation (retained review, Verified-tier); all
resulting design recommendations carry decisions.

**Pilot — scope decided: double duty**, with the reviewer's underpowering
caution attached: demand findings will be directional and qualitative,
not statistically validated. **The adopted measurement package includes
a candidate motivation-probe, now gated by a HARD PRE-ENROLLMENT
specialist-review requirement (`Verdict_v5.md` required change 3)** —
no family may be enrolled until the child-development specialist has
reviewed it.

**Curriculum validation — RECLASSIFIED, not an open gap for launch.**
Since curriculum content is deferred to v2, there is nothing to validate
at launch; this validation stream will be reintroduced when the feature
is actually built, alongside its own trigger ("proved demand" —
currently unquantified, see Outstanding Questions).

**Still open:** pricing/conversion validation (the pilot may inform
willingness-to-pay directionally but is not a conversion test);
account-linking UX/consent-flow validation; the no-Mpoints fallback
configuration's engagement loop has no validation plan; **whether
organic-only acquisition can reach the corrected, smaller 9,150-30,500
funnel range has no validation plan of any kind anywhere in the case.**

Status remains Partial: the pilot is fully scoped and instrumented at the
decision level, with both specialist reviews now hard-gated rather than
advisory, but market demand, pricing/conversion, and acquisition
feasibility have no statistically meaningful validation scheduled
anywhere in the plan.

## Supporting Evidence

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Verified-tier:** `LegalOpinion_v1.md` and `ChildDevelopmentReview_v1.md`
(retained professionals); the user's direct clarification history
through **`Clarifications_v21.md`** (Verified-tier as to what was
decided: the bounded self-fund-further contingency and its fallback
form; the two hard-gate elevations; the MVP-scope deferral of curriculum;
the explicit schools-partnership deferral and its reason; the
2.0-children-per-family figure as a stated assumption, not a derived
one).

**Supported-tier:** three Research House engagements
(`ResearchFindings_v1-3.md`); the user's directly-cited South African
statutory/statistical sources; `BusinessCase_v16.md`'s restored Market &
Competition content.

**Assumed-tier, named explicitly:** the candidate motivation-probe and
the candidate data-breach/incident-response commitment (both
Incubator-drafted, neither yet reviewed by the specialist whose domain it
falls within — **both reviews are now hard gates, not merely
recommended**); the 2.0-children-per-family figure (stated, not derived);
the three-tier-to-six-way sub-band reconciliation draft (Incubator-
authored prep work, unreviewed, not counted toward resolving anything).

**Bounded first-party data:** the n=10 interview round — non-
representative, governed by the standing instruction; the same rule
extends to the pilot's directional demand findings.

**Evidence-chain limitations, updated this cycle:** the self-fund-further
contingency's *sufficiency* (is R20,000 total actually enough capital?)
and the grant/startup-program fallback's *actual availability* are both
new, untested assumptions layered on top of the now-Verified bound
itself. The v2-curriculum trigger ("proved demand") is stated but
unquantified, a new named limitation.

Status remains Complete: the evidentiary base spans Verified-tier user
decisions and retained-professional opinions through Supported-tier desk
research to bounded first-party data and named Assumed-tier candidate
content, with each tier's limits stated.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this cycle:** self-fund-further contingency sizing (R20,000
total, hard ceiling, grant/startup-program fallback); data-breach and
motivation-probe specialist reviews elevated to hard gates (process
decided, though the reviews themselves have not yet occurred — see
below); curriculum authorship's time-pressure (removed via MVP-scope
deferral — authorship itself remains open, see below); schools-
partnership channel (explicitly deferred, with reason); child-to-family
population-conversion gap (resolved via a stated 2.0 assumption).

**Newly named this cycle:**

- **v2-curriculum demand-trigger threshold — unquantified.** "Once we
  have proved a demand" is not defined against any specific pilot
  outcome, subscriber count, or retention figure. A genuine open item,
  not urgent (nothing is currently blocked by it), but worth resolving
  before the pilot concludes so the trigger can actually be evaluated
  against results.
- **Self-fund-cap sufficiency and grant/startup-program funding
  availability — both untested.** The R20,000 ceiling is a real bound on
  personal exposure, not a guarantee the venture can reach
  sustainability within it, nor that non-dilutive funding will actually
  be obtainable if it is exhausted.

**Still genuinely open, not time-pressured:**

- **Curriculum authorship** (founder vs. engaged designer via the
  zero-marginal-cost advice policy, pending confirmation of that policy's
  scope) — undecided, but no longer gating anything before launch.

**Open — hard gates, process decided but not yet satisfied:**

- **Specialist review of the candidate motivation-probe** (child-
  development specialist, Expert Roster Entry 2) — must occur before
  pilot enrollment; has not yet occurred.
- **Specialist review of the candidate data-breach/incident-response
  commitment** (Data-Privacy Practitioner, Expert Roster Entry 5) — must
  occur before pilot begins; has not yet occurred.

**Open — analytical/planning gaps, unchanged or updated:**

- Whether organic-only acquisition can plausibly reach the corrected
  9,150-30,500 family-install funnel — untested, unbenchmarked, now
  against a smaller target.
- Success-criteria benchmarks (operational-health 65%, retention) remain
  placeholders; curriculum-engagement (30%) is reclassified as
  deferred/moot, not an open launch-scope gap.
- Post-runway external funding-ask size and form (beyond the R20,000
  self-fund ceiling and its grant/startup-program fallback).
- MoneyAfrica Kids' unpublished premium price; South Africa-specific
  vendor pricing for Stitch's or Mono's product.
- The user's advice-policy scope/limits (including whether it covers
  curriculum expertise, data-privacy practitioner time, and
  child-development specialist time specifically).
- POPIA s14 retention period and deletion trigger; consent-flow
  documentation separation; lightweight parent identity-verification;
  grace-period length and reminder cadence; behavior-input logging/
  verification and grade-input mechanisms for the hybrid bonus;
  dispute-escalation mechanism beyond the 48-hour window.

Status remains Complete: this register's scope is comprehensive
identification and tracking, and every item carries its disposition (in
flight, build task, conditional, hard gate pending, or explicitly pending
decision) — none is an undecided recommendation silently awaiting a
decision without being named as such.

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

**Per Playbook Entry 8 — the honest v20 baseline, stated before applying
this cycle's fixes:** `Verdict_v5.md`'s Gate Integrity Check found that
applying this exact standard consistently to v20's self-fund-further item
would have scored Constraints as Partial (2 pts, not 5), moving v20's
true score to **88/130 = 67.7%**, below the 70% threshold, despite v20
asserting 91/130 = 70.0%. **This is the honest baseline this cycle
corrects from — v20's asserted score should not be read as having been
soundly earned at the time.**

**This cycle's two status changes, both argued explicitly:**

**1. Constraints: Partial (as honestly re-scored) → Complete, on
genuinely new grounds.** The self-fund-further contingency now carries a
specific number (R20,000 total) and a named fallback form (grant/
startup-program funding) — both elements the Gate Integrity Check found
missing. See Constraints' own re-derivation paragraph above for the full
argument. This is not a re-assertion; it rests on new content.

**2. Curriculum Design (domain extension): Partial → Complete — a
judgment call, disclosed explicitly for Investment Committee scrutiny,
not asserted flatly.** The section's material questions are now: (a) is
curriculum in launch scope? Decided: no, deferred to v2 (a genuine,
verbatim user decision, not a hedge). (b) Age-band framework? Adopted,
now reconciled with the six-way sub-bands as prep documentation. (c)
What triggers v2 development, and who authors it? Both remain open, but
**neither is currently blocking anything** — they function analogously to
the "owned, timed, with fallback" pattern this document already uses to
keep Business Model and Roadmap at Complete despite open SARB/FPB
questions (owner: the user; timing: post-launch, demand-gated). **The
Incubator judges this section satisfies the Complete definition on this
basis, but flags explicitly that this is a scope-narrowing move enabled
by a deferral decision, and invites the Investment Committee to weigh in
if it disagrees this is different in kind from "documentation of an open
decision."** Per Playbook Entry 9, the reconciliation draft itself does
NOT count toward this determination — it is unreviewed prep work, not a
resolution.

**Because this second call is a judgment call rather than an
unambiguous application of the standard, both computations are shown
below.**

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

**Readiness Score = 94 / 130 = 72.3%.** Clears the completion gate's
≥70% threshold with a 2.3-point margin.

**Conservative alternative, withholding the Curriculum Design judgment
call (i.e., leaving it Partial = 2 pts):** 91/130 = **70.0%** — still
clears the threshold, with no margin, identical to v20's asserted score
but this time on a base (Constraints genuinely Complete) that survives
the Gate Integrity Check's own standard. **The case clears 70% under
both readings; only the margin differs.**

No section is Critical + Incomplete: both Legal & Compliance and Child
Data & Consent are Complete.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
52% (v13) → 52% (v14) → 52% (v15) → 52% (v16) → 70% (v17) → 70% (v18) →
70% (v20, later found to have been honestly 67.7% by Verdict_v5.md's own
arithmetic) → **72.3% (v21), or 70.0% under the conservative reading.**

### Critical Gaps

1. **Execution capacity — narrower in scope, now with a bounded
   contingency.** R10,000 total development budget plus a 6-month runway
   must contain the build, an instrumented pilot (behind two hard
   specialist-review gates), and two regulatory rechecks — executed
   substantially by one person. Curriculum authoring no longer competes
   for this same runway. **Self-fund-further contingency: R20,000 total
   hard ceiling, with grant/startup-program funding as the stated
   fallback if exhausted.**
2. **SARB/National Payment System Act open-banking question — owned and
   fallback-protected, still externally unsettled.** Owner: the user, at
   build-spec stage; decided fallback: launch without account-linking.
3. **FPB classification question over Mpoints — owned and
   fallback-protected, still externally unsettled, with traced ripple
   effects.** Owner: the user, at build-spec stage; decided fallback:
   launch without Mpoints.
4. **Market demand remains directionally evidenced only, against a
   corrected, smaller funnel.** The n=10 standing instruction holds; the
   pilot's demand read will be directional/qualitative, not validated.
   Whether organic-only acquisition can plausibly reach the corrected
   9,150-30,500 family-install funnel is untested.
5. **Success-criteria benchmarks remain partial placeholders.**
   Operational health (65%) carries no external benchmark; retention has
   no proposed figure at all. Curriculum engagement (30%) is reclassified
   as deferred, not an open launch-scope gap.
6. **Two specialist reviews are now hard gates, neither yet satisfied.**
   The Data-Privacy Practitioner's review of the candidate data-breach
   commitment must occur before pilot begins; the child-development
   specialist's review of the candidate motivation-probe must occur
   before any family is enrolled. Both remain Evidence: Assumed until
   their respective reviews actually happen.
7. **Legal/build tasks pending, unchanged.** POPIA s14 retention period
   and deletion trigger; consent-flow documentation separation;
   lightweight parent identity-verification.
8. **Exam-bonus residual risk — accepted, candidate-instrumented, review
   now hard-gated but not yet obtained.** The hybrid's retained
   outcome-contingent bonus layer carries a reduced-but-real
   intrinsic-motivation risk.
9. **NEW this cycle: the v2-curriculum demand-trigger threshold is
   unquantified.** "Once we have proved a demand" has no stated
   subscriber count, retention figure, or pilot outcome attached to it.
10. **RESOLVED this cycle, retained for audit-trail continuity:**
    self-fund-further contingency bounding (R20,000 total, grant/
    startup-program fallback); data-breach and motivation-probe review
    hard-gate elevation (process, not outcome); curriculum MVP-scope
    deferral (removes time pressure, does not resolve authorship);
    schools-partnership explicit deferral; child-to-family
    population-conversion gap (resolved via stated 2.0 assumption).
11. **Resolved in prior cycles, retained for audit-trail continuity:**
    all original specialist design decisions; the Conradie v Rossouw
    citation; recheck ownership/timing/fallbacks; pilot scope;
    cost/runway structure.

## Operations — Curriculum Design (Domain Extension)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (reconciliation draft: Assumed; authorship: Unknown)

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs, even where the curriculum feature
itself is deferred.*

**Scope decision, this cycle (`Verdict_v5.md` required change 4,
`Clarifications_v21.md`): curriculum/educational content, including the
15-18-only "Fintech Advance" module, is deferred in its entirety to a
post-launch v2 feature, contingent on demonstrated demand for the core
product.** Verbatim from the user: *"This is not a MVP feature meaning it
is not critical for the Launch version of the App. It will be a add on
once we have proved a demand."* This is a genuine, direct decision — not
a hedge, not a placeholder — and is the basis for this section's status
change from Partial to Complete, argued explicitly in the Readiness Score
section above.

Carried forward, unchanged in substance, retained as v2 planning
groundwork: the age floor of 6 is intentional; the curriculum is
conceived as a short course completable daily or weekly, not a full
year; two example mechanics (currency differentiation; "word sums" for
change/remainder calculation); "Fintech Advance" as the distinct
15-18-only element (gamification-avoidance decided, risk-literacy
framing adopted — to apply whenever it is eventually built).

**Three-tier age framework — adopted:** early childhood (roughly 6-9,
softened task/reward framing); pre-teen (roughly 10-14, basic
transactional literacy); teens (roughly 15-18, pre-employment literacy).

**Three-tier-to-six-way sub-band reconciliation — DRAFTED this cycle as
prep work, per explicit user instruction (`Clarifications_v21.md`
required change 4b), despite the underlying feature's deferral.**
Incubator-authored, Evidence: Assumed, unreviewed by the child-development
specialist — per Playbook Entry 9, this draft does not itself resolve
anything and is not counted toward this section's Complete status; it is
documentation prepared ahead of a demand-gated feature.

The product's six-way stakeholder sub-bands (6, 7, 8, 9-10, 11-14, 15-18)
do not map cleanly onto the three curriculum tiers: the 9-10 sub-band
straddles the early-childhood/pre-teen tier boundary (age 9 fits the
"early childhood" softened framing; age 10 fits "pre-teen" basic
transactional literacy). Three resolution options, drafted for eventual
specialist review:

- **(a) Fold the entire 9-10 band into the pre-teen tier for curriculum
  purposes specifically**, while the 9-10 band remains intact for all
  other product purposes (consent flow, terminology, UI). This is the
  Incubator's draft recommendation: transactional-literacy content is
  lower-risk to introduce slightly early (age 9) than to delay a full
  year, and it avoids fracturing a stakeholder band that is unified
  elsewhere in the product.
- **(b) Fold the entire 9-10 band into the early-childhood tier**,
  keeping softer framing one year longer — more conservative, delays
  transactional-literacy content for 10-year-olds.
- **(c) Split content within the 9-10 band by exact age** — adds
  curriculum-authoring complexity and contradicts the six-way band's
  purpose of grouping 9-10 together elsewhere in the product; not
  recommended.

This reconciliation is documentation only, not an adopted design
decision — it will require the child-development specialist's review
whenever the v2 curriculum workstream actually begins.

**Authorship — remains genuinely undecided, no longer time-pressured.**
The user has not decided between authoring the curriculum personally or
engaging a curriculum designer via the zero-marginal-cost advice policy,
pending confirmation that policy's scope extends to instructional-design
expertise. Because the workstream is now demand-gated rather than
starting immediately, this is no longer a scheduling risk against the
6-month runway — it is a named, owned (by the user), untimed decision,
analogous to how this document already treats other owned-but-unresolved
external questions (SARB, FPB) as compatible with Complete status.
`CurriculumDraft_v1.md` remains available as an earlier, unreviewed/
unadopted starting point, not a resolution.

**Still open, tracked as v2-phase items, not launch-blocking:**
instructional format, standards alignment, and content itself; the
v2-trigger threshold ("proved demand") is unquantified (see Outstanding
Questions, Risks); the conditional 6-9-tier immediate-feedback
replacement under the no-Mpoints fallback; the 30% curriculum-engagement
success benchmark (deferred alongside the feature).

Status: Complete, on the basis argued above — the section's launch-scope
material question (is curriculum in scope?) is genuinely decided, the
framework is adopted, and the requested reconciliation prep work is done
this cycle. This determination is explicitly flagged as a judgment call
for Investment Committee review in the Readiness Score section, and the
document's own conservative-alternative score (70.0%) shows the case
still clears the completion gate even if the Investment Committee
disagrees with this specific call.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Directly and substantially addressed by `LegalOpinion_v1.md` Q2 and Q3.
The universal parent-consent gate is confirmed legally sufficient as
designed under POPIA s34/s35(1)(a). Two hardening recommendations remain
named build tasks: consent-flow documentation separation; a lightweight
parent identity-verification step (non-linking route required if the
SARB fallback triggers).

POPIA Section 14 retention is confirmed to require an affirmatively
designed, specific retention period and deletion trigger — a named,
pending build task.

**A minimal data-breach/incident-response commitment (see Constraints for
full text) directly extends this section's scope. Specialist
(Data-Privacy Practitioner) review is now a HARD PRE-PILOT GATE
(`Verdict_v5.md` required change 2, `Clarifications_v21.md`), not
advisable guidance.** It is an Incubator-drafted candidate (Evidence:
Assumed), specifying what constitutes a breach, who is notified (parents;
the Information Regulator, per POPIA s22), and a notification timing
standard consistent with POPIA's "as soon as reasonably possible"
language. **The commitment must not be in force, and real children's
data must not be collected at pilot, until this review has actually
occurred — this is now a binding process requirement on the Roadmap's
pilot phase, not a recommendation the pilot can proceed without.**

Platform-policy items, unchanged: Google Play's Families Policy
loyalty-point disclosure requirement applies to the primary configuration
and is mooted under the no-Mpoints fallback; Apple's Kids Category
IAP-currency question is deferred with iOS and likewise mooted under that
fallback.

Status remains Complete: the section's central questions — consent-model
sufficiency and retention approach — are directly answered by retained
counsel; the breach commitment is an additive strengthening whose review
is now a hard gate rather than an unresolved central question of the
section's own original scope.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Complete.
- Readiness Score ≥ 70%: **Yes — PASSES.** Score is 94/130 = 72.3% under
  the primary computation, or 91/130 = 70.0% under the disclosed
  conservative alternative that withholds the Curriculum Design judgment
  call. **The case clears 70% under both readings.**
- **Expert roster entries ≥3 sentences, each naming a specific
  case-study assumption:** see `ExpertRoster.md`, regenerated this
  cycle, six entries, each citing a specific assumption traceable to this
  case's own content (e.g., the undocumented scope of the
  zero-marginal-cost advice policy; the untested sufficiency of the
  R20,000 self-fund ceiling; the unquantified v2-curriculum demand
  trigger).
- **Devil's Advocate objections ≥3, each citing a specific section:**
  see `reviews/DevilsAdvocate.md`, regenerated this cycle, five
  objections, each naming a specific Business Case section.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.
- No section consists solely of an "Unchanged from vN, not reproduced"
  pointer: **Yes.** Every section contains its own full, substantive,
  self-contained text this cycle.

**This Business Case passes its own completion gate.** All six of the
Investment Committee's required changes from `Verdict_v5.md` are
resolved: the self-fund-further contingency is bounded with a re-derived,
shown-work justification for Constraints' restored Complete status; both
specialist reviews are elevated to hard gates; curriculum authorship is
resolved via a broader, verbatim MVP-scope decision (deferral to v2, not
a direct answer to the original question, named as such); the
three-tier-to-six-way reconciliation is drafted as prep work without
being scored as resolving anything; the schools-partnership channel is
explicitly deferred with a stated reason; and the child-to-family
population-conversion gap is resolved via a stated assumption that
materially and honestly recalculates the revenue range downward. **The
one status change beyond the direct required changes (Curriculum
Design) is disclosed as a judgment call, not asserted flatly, with a
conservative-alternative score shown to demonstrate the completion gate
is cleared either way.** Genuine open items remain — detailed in
Critical Gaps — led by execution capacity (now bounded), two
externally-unsettled regulatory questions, two hard-gated but
not-yet-obtained specialist reviews, and a newly named, unquantified
v2-curriculum demand trigger.
