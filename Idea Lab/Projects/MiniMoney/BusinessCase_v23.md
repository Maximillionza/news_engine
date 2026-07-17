# Business Case: MiniMoney — v23

> Prepared by: Incubator. This revision incorporates `ResearchFindings_v4.md`
> (Research House Engagement 4) into Constraints and Financial
> Considerations, resolving the seventh and final required change from the
> Investment Committee's sixth review (`Verdict_v6.md`) that v22 left
> explicitly and deliberately open pending this research. **Scope of this
> cycle is narrow and stated plainly: only the non-dilutive funding target
> sub-item, and the sections/items that directly reference it, are
> touched. No other section's substance changes.** Authorized inputs for
> this cycle: `00_CaseStudy.md`, `BusinessCase_v22.md`,
> `ResearchFindings_v4.md`. Per standing framework rule, vendor research
> output is never trusted internal work product — it has received the
> Incubator's own scrutiny below and can support raising a tag to
> Supported, never to Verified.

## What Changed in v23 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Supported (vendor
research); Unknown (two newly surfaced founder-specific facts)

`ResearchFindings_v4.md` identified eight named, currently-traceable
non-dilutive funding candidates for South African founders, evaluated their
timelines, eligibility, and award-size proportionality, and explicitly
flagged what it could not resolve. Applying the Incubator's own scrutiny
(vendor output, Supported-tier ceiling, never Verified) rather than
accepting the research uncritically, this cycle resolves the seventh and
final `Verdict_v6.md` required change as follows:

**Primary candidate: NYDA (National Youth Development Agency) Grant
Programme.** Non-repayable grant, R1,000 up to a cumulative R200,000 cap
(R250,000 for technology/co-op projects); rolling, year-round applications;
the single best-sourced timeline of the group (~30 working days from
approval to disbursement, per NYDA's own materials) — genuinely proportionate
to the R20,000 gap at the lower end of its range. **Hard eligibility gate,
unconfirmed and not assumed in either direction:** requires the founder to
be aged 18-35 and the business 100% youth-owned. This case study does not
state the founder's age; if the founder falls outside this band, NYDA is
excluded outright.

**Secondary candidates, weaker on timeline and/or eligibility confirmation:**
SEDA Technology Programme (award up to R600,000, but requires CIPC
company-registration and SARS tax-clearance status, both unconfirmed for
MiniMoney, and its own timeline could not be pinned down — the 4-12-week
figure found is a general SEDA claim, not confirmed specific to this
programme) and, contingent on a future cohort opening, Injini's
earlier-stage EdTech-accelerator track (plausible sector fit, historically
~R100,000, but no confirmed open 2026 cohort was found and its timeline is
entirely unconfirmed).

**Tertiary, genuinely uncertain fit:** Technology Innovation Agency (TIA)
instruments — eligibility itself is unresolved, since TIA's public
materials are structured around Technology Readiness Levels and
university/research-institution pathways, and no source addressed whether a
solo, non-research-affiliated consumer-app founder would even be considered
eligible. Weakest timeline evidence of the group (a generic, non-instrument-
specific "3-6 months" figure).

**Not viable as a near-term fallback, named rather than silently omitted:**
SAB Foundation Social Innovation Fund (2026 cycle already closed as of this
research; next window plausibly not until early-to-mid 2027) and FNB App of
the Year (a recognition competition structurally favoring already-live,
traction-demonstrating apps, not proportionate pre-launch seed capital, and
its exact 2026 entry-window dates could not be confirmed due to a
research-tooling access issue during this engagement). **Hard-excluded on
stated eligibility grounds:** Mastercard Foundation EdTech Fellowship
(requires post-revenue, growth-stage status, likely ~R1,000,000+ turnover —
MiniMoney is pre-revenue) and Google for Startups Black Founders Fund:
Africa (requires a live, in-market product — MiniMoney is pre-launch — plus
a founder-demographic criterion this research neither confirmed nor
assumed). **Structurally excluded** (dilutive, defunct, or stage-mismatched):
National Empowerment Fund, Standard Bank/Founders Factory Africa, Naspers
Foundry, Grindstone.

**What this resolution does NOT do, stated plainly per instruction:** it
does not overstate the founder's eligibility for any candidate. Two
founder-specific facts remain genuinely unknown and are not assumed in
either direction — the founder's **age** (gates NYDA, the single
best-timelined candidate) and MiniMoney's current **company-registration/
tax-clearance status** (gates SEDA). These are newly surfaced, tracked open
items (see Outstanding Questions), not resolved by this research and not
glossed over as resolved.

**Readiness Score recomputed in full this cycle: it does not move.** It
remains 94/130 = 72.3% (or 91/130 = 70.0% under the disclosed conservative
reading), identical to v21 and v22. **No section's Status flips.**
Constraints was already Complete under the "owned, timed, decided-fallback-
category" pattern already used for the SARB/FPB items; it is strengthened
(a decided fallback *target list* now exists, not just a category) but
cannot score higher than Complete. Financial Considerations remains
Partial: the funding-target's naming is resolved, but this section's
Partial status was never solely dependent on that one sub-item — **full
financial projections (P&L, break-even analysis) remain entirely absent**,
a distinct material question untouched by this research, with no owner,
timing, or decision anywhere in this document's history. Risks, Outstanding
Questions, Supporting Evidence, and Roadmap were already Complete
(register-type sections whose standard is comprehensive tracking with a
recorded disposition per item, not closure of every underlying question) —
the funding-target item's disposition is updated, not newly created, so
these sections remain Complete as before. The full section-by-section
reasoning is in Readiness Score.

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
post-launch v2 feature, against a quantified dual trigger (500 paying
subscribers AND 60% 90-day retention). The core launch mechanic itself
already carries embedded financial literacy (earning, budgeting,
expense/tax-style deductions, payment mechanics); structured instructional
content is what remains deferred.

Growth is organic-only at launch — zero paid acquisition, no marketing
budget allocated; the schools-partnership channel remains explicitly
deferred for stated founder-bandwidth reasons. The pilot's own acquisition
checkpoint/kill-metric is quantified: if fewer than 60% of enrolled pilot
families complete 4 consecutive weekly task→payslip cycles, organic-only
acquisition/mechanic engagement is treated as not yet validated before
widening release.

Two hard pre-pilot/pre-enrollment specialist reviews — the data-breach/
incident-response commitment (Data-Privacy Practitioner) and the
exam-bonus motivation-probe (child-development specialist) — have a
defined trigger point (once a stable working model exists, and before any
pilot testing with real families begins), matching the trigger already
used for the retained legal opinion. Neither review has occurred as of
this revision. The runway-slippage contingency remains bounded at R20,000
total maximum personal commitment, tied explicitly to the low end of the
revenue range (92 paying families, ~R5,519/month) as a foreseen,
already-planned-for scenario. The beyond-48-hour dispute-escalation gap is
resolved via an interim placeholder — manual founder review at MVP stage —
explicitly named as non-scalable and founder-capacity-dependent.

Revenue figures are unchanged in magnitude across the last several
cycles: **≈9,150-30,500 Year-1 family installs and ≈92-915 paying
families** (≈R5,519-R54,891/month run-rate), still resting on
Guessing/Assumed-tier funnel assumptions.

**All seven required changes from `Verdict_v6.md` are now resolved.** The
first six were resolved in v22 (specialist-review timing defined;
advice-policy coverage confirmed; dispute-escalation interim mechanism;
low-end revenue stress test cross-referenced; acquisition kill-metric
quantified at 60%; v2-curriculum trigger quantified). **The seventh — a
concrete non-dilutive funding target for the R20,000 self-fund ceiling's
fallback — is resolved this cycle (v23) via Research House Engagement 4**:
a prioritized, honestly-caveated candidate list headed by the NYDA Grant
Programme (best-sourced near-term timeline, contingent on the founder's
unconfirmed age falling in the 18-35 band), with SEDA Technology Programme
and Injini's earlier-stage track as weaker secondary options and TIA as a
genuinely uncertain tertiary fit. Several other named candidates were
excluded on hard eligibility or structural grounds. **This resolution does
not overstate the founder's eligibility for any candidate** — the
founder's age and MiniMoney's company-registration status remain
unconfirmed and are named as new open items, not assumed.

**The Readiness Score is unchanged at 94/130 = 72.3%** (or 91/130 = 70.0%
under the disclosed conservative reading), clearing the completion gate's
≥70% threshold in both computations, identical to v21 and v22. This
cycle's resolution is a genuine evidentiary improvement — from "out for
research" to "named and prioritized, with honest caveats" — that does
not, on its own terms, close Financial Considerations' independently open
P&L/break-even gap, so no section's status moves. See Readiness Score for
the full section-by-section reasoning.

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

Status remains Partial, unaffected by this cycle's funding-target
research: there is a real, encouraging directional signal, but no
established finding that parents broadly perceive this as a problem worth
paying to solve.

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
this cycle's funding-target research: the differentiation thesis is
coherent and partly evidenced, but no structured market-sizing or
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
requirement, and serves double duty: mechanic-safety signal AND a
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
unaffected by this cycle's funding-target research: every tension
previously flagged in this section is resolved by direct, Verified-tier
user clarification.

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
lightweight, qualitative early-warning signal detection.

**Exam-bonus motivation-risk instrumentation — candidate instrument
exists; review trigger defined, not satisfied.** The instrument itself:
parent-facing Likert/open items alongside the existing PSI-SF/FAD-GFS
timepoints; child-facing age-appropriate items alongside the existing
Child–Parent Relationship Scale timepoint; near-zero marginal cost,
administered at existing survey events. The review must occur once a
stable working model exists, and before any pilot testing with real
families begins — the same trigger already used for the retained legal
opinion. No family may be enrolled in the pilot until this review has
actually occurred, and it has not yet occurred as of this revision. The
probe remains Evidence: Assumed until that review occurs.

The underlying substantive risk remains confirmed, not resolved: the
late-penalty redesign narrows but does not eliminate the Family Stress
Model's affective pathway, and the exam-bonus hybrid's residual
intrinsic-motivation risk is candidate-instrumented but not yet
specialist-reviewed or adopted.

Status remains Partial, unaffected by this cycle's funding-target
research: the acquisition checkpoint is a specific, correct figure and the
relationship-strain criterion has an adopted measurement plan, but
operational health and the general retention benchmark remain
unbenchmarked, and the motivation-risk review — though trigger-defined —
has still not occurred.

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
pilot testing with real families begins. Their advice is confirmed
zero-marginal-cost. Neither review has yet occurred. A future AI mediator
feature for dispute resolution remains explicitly out of current scope,
named specifically as the eventual replacement for the interim
manual-founder-review dispute-escalation placeholder (see Operations). A
curriculum/instructional-design specialist (Expert Roster Entry 3) is a
named future stakeholder for the deferred v2 curriculum feature, not yet
engaged. **A new candidate stakeholder class is surfaced this cycle by the
funding-target research, not yet engaged or contacted: the named
non-dilutive funding bodies themselves (principally NYDA), contingent on
confirming the founder's own eligibility first** (see Outstanding
Questions).

Status remains Partial: both regulator stakeholders have an owned recheck
and a fallback but remain unresolved pending those rechecks; the two named
specialist reviews have a defined trigger point but neither has actually
occurred; the newly-surfaced funding-body relationship is not yet pursued
pending founder-fact confirmation.

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
Status remains Partial, unaffected by this cycle's funding-target
research: the target population is clearly named and the customer unit is
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

Status remains Complete, unaffected by this cycle's funding-target
research: price, feature boundaries for the corrected launch scope, and
all previously-pending decisions within this section's scope are made.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unaffected by this cycle's funding-target research.

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
absolute terms (the pilot's 60% checkpoint gates the pilot-to-wider-
release transition but does not itself validate whether organic discovery
can reach the 9,150-30,500 range — see Validation Strategy).

Status remains Partial: the competitive landscape and funnel are fully
documented and the population-conversion gap remains closed via a stated
(Assumed-tier) figure, but the most decision-relevant figures (Year-1
adoption, conversion rate) remain unvalidated.

## Business Model

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unaffected by this cycle's funding-target research. Subscription-only at
launch, ads deferred to V2; R59.99/month per family, covering up to 4
children — the family is the revenue unit. MiniMoney is a
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
  personal commitment**, hard ceiling, with grant/startup-program funding
  named as the fallback if exhausted (see Constraints, Financial
  Considerations). **The specific non-dilutive funding target for that
  fallback is now named this cycle — see Constraints and Financial
  Considerations for the full, honestly-caveated list.**
- **Professional opinions/advice: zero marginal cost to the venture**, via
  the user's existing policy. Coverage for the two named hard-gate
  reviews (Data-Privacy Practitioner; child-development specialist) is
  confirmed, Verified-tier. The policy's general scope for other
  engagement types (e.g., a curriculum designer) remains undocumented.
- **Runway: 6 months** at current commitment before external funding is
  needed.
- **Acquisition/CAC: organic-only, zero paid acquisition.** No marketing
  budget is allocated from the R10,000 total. The schools-partnership
  channel remains explicitly deferred.
- **Curriculum content-production cost:** remains moot for launch,
  deferred alongside the feature itself, against a quantified v2 trigger.

**Reconciliation against the prior agency reference range, unchanged:**
the previously-cited $25,000-$120,000+ engineering-cost range was a
reference frame, not the plan. R10,000 buys days, not months, of
professional engineering if the founder's own capacity fails — there is
no buffer to purchase execution beyond the R20,000 total ceiling.

**Still open:** no post-runway external funding-ask is precisely sized —
the *target* is now named (see above), but the researched award figures
are program ceiling figures, not typical disbursements, and actual
obtainability is contingent on unconfirmed founder-eligibility facts.
Status remains Partial: the low-end stress test is cross-referenced
consistently with Constraints and the advice-policy coverage question is
resolved for the two named reviews, and the funding target is now named,
but the revenue side still rests on unvalidated Guessing-tier estimates
and precise funding-ask sizing remains unspecified.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Unaffected by this cycle's funding-target research. Core mechanics
(budget and earning, task structure, completion/verification/reporting
flow, dispute mechanism, payment confirmation, late-penalty parent-only
design) are unchanged in structure. All specialist design decisions from
prior cycles stand.

**Dispute-escalation beyond 48 hours** is resolved via an interim
placeholder: unresolved disputes beyond the 48-hour parent-decline window
are flagged for manual founder review, at MVP stage — not a scalable
long-term solution, pending the future (out-of-scope) AI-mediator
feature. This is founder-capacity-dependent and is named explicitly as a
direct extension of the execution-capacity Critical Gap — founder
bandwidth already spans the build, the instrumented pilot, and two
regulatory rechecks within the 6-month runway, and now also absorbs any
beyond-48-hour disputes the pilot generates.

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

Unaffected by this cycle's funding-target research. Still unspecified: how
account-linking is technically initiated; how payment confirmation is
captured beyond the accept/dispute UI; the exam-bonus grade-input
mechanism; the hybrid bonus's behavior-input logging/verification
mechanism; the grace-period/reminder notification infrastructure. No
curriculum-delivery technology is in scope, consistent with its deferral.
Status remains Partial.

## Legal & Compliance ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unaffected by this cycle's funding-target research. The retained
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
updated per this cycle's one change (funding-target resolution).

- **Regulatory risk:** unchanged — core mechanic low-risk; two narrower
  open regulatory questions each carry a named owner, timing trigger, and
  decided fallback.
- **Execution-capacity risk — bounded contingency, now with a named
  funding-fallback candidate list, obtainability still untested.** A
  solopreneur venture with a R10,000 total development budget, a ~3-month
  directional build timeline, an instrumented 20-50 family pilot, two
  personally-owned regulatory rechecks, and manual founder review of any
  dispute unresolved beyond 48 hours — all inside a 6-month runway,
  executed substantially by one person. The self-fund-further contingency
  remains capped at R20,000 total, with grant/startup-program funding as
  the stated fallback, explicitly the mechanism triggered if actual
  revenue lands at the low end of the range (see Revenue & Costs,
  Constraints). **The specific non-dilutive funding target is now named
  this cycle via Research House Engagement 4** — a prioritized candidate
  list headed by NYDA (see Constraints, Financial Considerations) — but
  whether R20,000 total is itself sufficient capital to reach
  sustainability, and whether any named candidate is actually obtainable
  given unconfirmed founder-eligibility facts (age; company-registration
  status), both remain untested.
- **Acquisition/adoption risk — defined checkpoint, not fully resolved.**
  Zero paid acquisition remains the decided strategy against the
  9,150-30,500 family-install funnel. The pilot's 60%
  task-cycle-completion criterion doubles as an explicit
  acquisition/mechanic-engagement checkpoint for the pilot-to-wider-
  release transition — this gates premature scaling but does not itself
  validate whether organic discovery can reach the funnel's absolute
  size, which remains untested. The schools-partnership channel remains
  explicitly deferred.
- **Child-safety/data-privacy risk:** consent model confirmed legally
  sufficient; two hardening recommendations remain build tasks. POPIA
  Section 14 retention policy remains an affirmative design requirement.
  The data-breach/incident-response commitment specialist review has a
  defined trigger — once a stable working model exists, before any pilot
  testing with real families begins. It has not yet occurred.
- **Minor-contractual-capacity risk:** resolved, unchanged.
- **Terminology/perception risk:** mitigation decided, unchanged.
- **Late-penalty/relationship risk:** both mitigation paths engaged,
  unchanged; residual risk remains real.
- **Exam-bonus/intrinsic-motivation risk — candidate-instrumented, review
  trigger defined, not yet obtained.** The behavior-primary redesign
  follows the evidence; the retained outcome-contingent bonus layer means
  the crowding-out risk is reduced, not eliminated. No family may be
  enrolled until the review has actually occurred, and it has not yet
  occurred as of this revision.
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
- **Non-dilutive-funding-target risk — RESOLVED this cycle, with
  caveats.** The previously-named gap (no known candidate) is closed: a
  prioritized, honestly-caveated candidate list exists, headed by NYDA
  (contingent on unconfirmed founder age). A narrower residual risk
  remains and is newly named: if the founder does not meet NYDA's
  eligibility band, the next-best candidates carry meaningfully weaker
  timeline or eligibility evidence, and the fallback's practical
  reliability is correspondingly weaker than the primary candidate alone
  would suggest.
- **Competitive risk; monetization-execution risk; app-store policy risk;
  platform-concentration risk:** unchanged in substance.

Status remains Complete: the risk landscape is comprehensively identified
and characterized, and every specialist-recommended mitigation within it
carries a recorded decision. A Complete risk register does not mean the
risks are eliminated: execution capacity (funding fallback now named but
obtainability untested), two external regulatory questions, the accepted
exam-bonus residual, and the untested organic-only acquisition strategy
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

**Remaining load-bearing assumptions, untested:**

- The exam-bonus risk-acceptance assumption stands: the secondary bonus's
  salience will not dominate the behavior-primary structure in the
  child's perception. Untested; candidate-observable via the
  motivation-probe, pending its trigger-defined specialist review.
- Organic-only acquisition will be sufficient to reach a meaningful share
  of the 9,150-30,500 family-install funnel. Untested, unbenchmarked;
  partially checkpointed via the pilot's 60% completion criterion but not
  validated in absolute terms.
- **The self-fund-further ceiling (R20,000 total) is sufficient capital
  to reach a sustainable venture, or grant/startup-program funding is
  actually obtainable if it is not. Neither is tested.** Research House
  Engagement 4 (`ResearchFindings_v4.md`) has now named a concrete,
  prioritized candidate list for the non-dilutive fallback (see
  Constraints, Financial Considerations) — **this makes the assumption's
  evidentiary picture clearer, not more favorable**, consistent with this
  document's standing practice of stating those two dimensions
  separately: only one candidate (NYDA) has a solidly-sourced near-term
  timeline, and even that candidate's eligibility is contingent on the
  founder's age (18-35), which remains unconfirmed. Every other viable
  candidate carries materially weaker timeline or eligibility evidence.
  Whether the fallback is actually obtainable remains untested — the
  assumption itself is not resolved, only better informed.
- The Incubator-drafted candidate data-breach commitment and
  motivation-probe are adequate as interim policy/design pending their
  respective specialist reviews. Both remain Evidence: Assumed by
  construction; both reviews have a defined trigger, neither has
  occurred.
- Mbucks non-transferability/non-redeemability and the SARB/NPS Act
  contingency remain documented constraints, not assumptions (see
  Constraints).

Status remains Partial: several load-bearing assumptions remain untested
even where the evidentiary picture behind one of them (funding-fallback
obtainability) has improved this cycle — the list is a working inventory,
not a closed set.

## Constraints

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (with
two Assumed-tier and one Supported-tier addition, named below)

- Solopreneur venture; AI-assisted development; external technical
  expertise engaged only on-demand; directional ~3-month build timeline;
  Android primary, iOS deferred.
- **Mbucks non-transferability/non-redeemability** — binding product-spec
  constraint on all future roadmap decisions (`LegalOpinion_v1.md` Q1).
- **R10,000 total development budget; 6-month runway before external
  funding is needed; professional opinions at zero marginal cost.**
  Coverage of the two hard-gate specialist reviews under this policy is
  confirmed.
- **Zero paid acquisition — organic-only growth.** No marketing budget is
  allocated from the R10,000 total; the pilot's 60% task-cycle-completion
  criterion serves as the checkpoint gating the transition to wider
  release.
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
- **Runway-slippage contingency — self-fund further, bounded.** Maximum
  personal commitment: R20,000 total (R10,000 initial + R10,000
  additional) — a hard ceiling. If the cap is exhausted without the
  venture being sustainable, the stated fallback is grant or
  startup-program funding (non-dilutive), not equity or informal
  borrowing. This contingency is the exact mechanism triggered if actual
  Year-1 revenue lands at the low end of the range (92 paying families,
  ~R5,519/month) — a foreseen, already-planned-for scenario, not a new
  failure state requiring a new decision.

  **The specific non-dilutive funding target is now research-informed
  this cycle (`ResearchFindings_v4.md`, Research House Engagement 4),
  resolving the seventh and final required change from `Verdict_v6.md`.**
  Stated as a prioritized, honestly-caveated list, Supported-tier (vendor
  desk research, never Verified-tier per standing rule):

  1. **Primary candidate: NYDA (National Youth Development Agency) Grant
     Programme** — non-repayable grant, R1,000 up to a cumulative
     R200,000 cap (R250,000 for technology/co-op projects); rolling,
     year-round applications; the best-sourced timeline of the group
     (~30 working days from approval to disbursement, per NYDA's own
     materials). **Hard eligibility gate, unconfirmed:** requires the
     founder to be aged 18-35 and the business 100% youth-owned. The
     founder's age is not stated anywhere in this case study and is not
     assumed here in either direction — if the founder falls outside
     this band, NYDA is excluded outright.
  2. **Secondary candidate: SEDA Technology Programme (STP)** —
     non-repayable grant, up to R600,000 per project (though the
     practical cash-runway-relevant amount is likely well below the
     headline cap, given cited co-funding-split structures). Requires
     South African CIPC company registration and a valid SARS
     tax-clearance status — MiniMoney's current registration status is
     not stated in this case study and is unconfirmed. Timeline evidence
     is weak: the 4-12-week figure found is a general SEDA claim, not
     confirmed specific to STP.
  3. **Tertiary, genuinely uncertain fit: Technology Innovation Agency
     (TIA) instruments** (Seed Fund / SMME Seed Fund / Grant Startup
     Capital) — up to R200,000 (plus a R60,000/year project fee) in one
     cited instrument, but TIA's public materials are structured around
     Technology Readiness Levels and university/research-institution
     pathways; whether a solo, non-research-affiliated consumer-app
     founder would even be considered eligible could not be confirmed
     from public material. Weakest timeline evidence of the group (a
     generic, non-instrument-specific "3-6 months" figure).
  4. **Contingent on a future cohort opening: Injini (EdTech Accelerator,
     Cape Town), earlier-stage cohort track** — historically an initial
     ~R100,000 grant component; plausible sector fit (dedicated EdTech
     accelerator) but no confirmed open 2026 cohort was found for this
     track, and its timeline is entirely unconfirmed.

  **Explicitly not viable as a near-term fallback, named rather than
  silently omitted:** SAB Foundation Social Innovation Fund (2026 cycle
  already closed as of this research; next window plausibly not until
  early-to-mid 2027); FNB App of the Year (a recognition competition
  structurally favoring already-live, traction-demonstrating apps — not
  proportionate pre-launch seed capital, and its 2026 entry-window dates
  could not be confirmed due to a research-tooling access issue).
  **Hard-excluded on stated eligibility grounds:** Mastercard Foundation
  EdTech Fellowship (requires post-revenue, growth-stage status, ~R1M+
  turnover — MiniMoney is pre-revenue); Google for Startups Black
  Founders Fund: Africa (requires a live, in-market product — MiniMoney
  is pre-launch — and a founder-demographic criterion this research
  neither confirmed nor assumed). **Structurally excluded** (dilutive,
  defunct, or stage-mismatched): National Empowerment Fund (loan/equity
  instruments, not grants); Standard Bank/Founders Factory Africa
  (equity-investing accelerator); Naspers Foundry (wound down March
  2023); Grindstone (growth-stage, post-revenue accelerator).

  **What remains genuinely open, not overstated:** the founder's age
  (gates NYDA, the single best-timelined candidate) and current
  company-registration/tax-clearance status (gates SEDA) are both unknown
  to this research and unconfirmed in this case study — these are
  founder-specific facts, not researchable ones, and are named as open
  items below (see Outstanding Questions) rather than assumed in either
  direction. **Evidence: Supported (vendor desk research), not
  Verified** — per standing rule, Research House's output can support
  raising a tag to Supported but never to Verified; that tier is reserved
  for user-confirmed facts.

- **Minimal data-breach/incident-response commitment — Incubator-drafted
  candidate, review trigger defined:** the same trigger already
  established for the specialist legal opinion — once a stable working
  model exists, and before any pilot testing with real families begins.
  This defines *when* the review occurs; the review itself has not yet
  occurred as of this revision. Evidence: Assumed — a founder-authored
  draft. The commitment must not be in force, and pilot enrollment of
  real families must not begin, until the Data-Privacy Practitioner
  (Expert Roster Entry 5) has actually reviewed it. Candidate minimum
  content, unchanged:
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
dispute-escalation, and now the self-fund-further contingency's fallback
*target*. The self-fund-further contingency's fallback *form*
(grant/startup-program funding) was already decided; its specific
*target* is now named via Research House Engagement 4 as a prioritized
candidate list, headed by NYDA, with the caveats above. **This resolves
the seventh required change from `Verdict_v6.md` at Supported-tier
evidence — a genuine evidentiary upgrade from "out for research" to
"named and prioritized," though actual obtainability remains untested and
contingent on unconfirmed founder-eligibility facts.** This section's
Complete status is retained on the same grounds as v22 — an owned, timed,
externally-gated item with a decided fallback *category*, now further
strengthened by a decided fallback *target list* — **not newly earned by
this resolution, since the pattern already treated this as compatible
with Complete before the research was delivered.**

## Roadmap

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Now (parallel with build, starting immediately):** core engineering
build only. Curriculum-content workstream remains removed from this
phase, deferred to a post-launch v2 phase, against a quantified trigger
(500 subscribers AND 60% 90-day retention).

**Build phase:** implement core loop with decided designs —
parent-facing-only debt terminology; hybrid exam bonus; grace-period/
pre-escalation reminders; beyond-48-hour dispute escalation via manual
founder review (interim placeholder). Legal build tasks: POPIA s14
retention period and deletion trigger design; consent-flow documentation
separation; lightweight parent identity-verification step. The candidate
data-breach/incident-response commitment (see Constraints) must be
reviewed by the Data-Privacy Practitioner (Expert Roster Entry 5) once a
stable working model exists and before any pilot testing with real
families begins. This has not yet occurred.

**Build-spec stage:** the user personally runs both regulatory rechecks —
SARB/NPS Act and FPB. Decided fallbacks apply if unresolved by launch.

**Pilot (20-50 families):** double-duty per prior decision — mechanic
safety/child-development signal AND directional demand read — with the
adopted measurement package plus the candidate motivation-probe addition
built into the pilot design. The candidate motivation-probe must be
reviewed by the child-development specialist (Expert Roster Entry 2)
using the same trigger — once a stable working model exists, before any
pilot testing with real families begins. Not yet occurred. The pilot's
60% task-cycle-completion criterion doubles explicitly as the
acquisition/mechanic-engagement checkpoint gating the transition to wider
release: fewer than 60% completing 4 consecutive weekly cycles means
organic-only acquisition/engagement is treated as not yet validated.

**Post-pilot (~month 6): external funding may be needed** — the initial
runway ends here. Decision rule: if month 6 arrives without secured
external funding, or any single workstream has slipped materially — or
actual revenue lands at the low end of the range (92 paying families,
~R5,519/month), a foreseen scenario — the user will self-fund further up
to a hard ceiling of R20,000 total personal commitment. If that ceiling
is reached without a sustainable venture, the stated fallback is grant or
startup-program funding; **the specific non-dilutive target is now named
this cycle (Research House Engagement 4) as a prioritized candidate list
headed by NYDA** — see Constraints for the full list and its eligibility
caveats, none of which are yet confirmed for this founder.

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

Status remains Complete: every pre-pilot decision the roadmap lists as
pending is made; the two specialist reviews carry a defined trigger point;
the low-end revenue scenario is tied to the existing self-fund-further
contingency; the dispute-escalation gap is resolved via a named interim
mechanism; the v2-curriculum trigger is quantified. The remaining opens
are owned external rechecks, build-spec parameters, the still-not-yet-
occurred specialist reviews (trigger defined, not satisfied), and the
now-named-but-not-yet-pursued non-dilutive funding target (contingent on
unconfirmed founder-eligibility facts).

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**What exists:**

- **Budget: R10,000 total** for development.
- **Self-fund-further cap: R20,000 total maximum personal commitment**
  (R10,000 initial + R10,000 additional). Fallback if exhausted: grant or
  startup-program funding (non-dilutive), not equity or informal
  borrowing. **The specific non-dilutive funding target is now RESOLVED
  this cycle at Supported-tier (Research House Engagement 4,
  `ResearchFindings_v4.md`) as a prioritized, honestly-caveated candidate
  list** — see Constraints for the full list and caveats. In brief:
  primary candidate NYDA (best-sourced near-term timeline, ~30 working
  days disbursement after approval, contingent on the founder's
  unconfirmed age falling in the 18-35 band); secondary candidates SEDA
  Technology Programme and, contingent on a future cohort opening,
  Injini's earlier-stage track (both weaker on timeline and/or
  eligibility confirmation); TIA instruments a genuinely uncertain
  tertiary fit. Several other named candidates were excluded on hard
  eligibility or structural grounds (see Constraints). **This resolves
  the naming of a target; it does not resolve whether the target is
  actually obtainable** — that remains untested, contingent on
  founder-specific facts (age; company-registration status) this
  research could not and did not assume.
- **Professional advice: zero marginal cost** via the user's existing
  policy. Coverage of the two hard-gate specialist reviews confirmed; the
  policy's general scope for other engagement types remains
  undocumented.
- **Runway: 6 months** before external funding is needed.
- **Revenue model (per-family), unchanged in magnitude:** R59.99/month
  per family against a Year-1 range of **92-915 paying families** —
  R5,519-R54,891/month run-rate at the range bounds (≈R66,229-R658,690/
  year); ramp-dependent actuals lower. Low-end explicitly cross-
  referenced against the self-fund-further contingency as a foreseen
  scenario.
- **Acquisition spend: zero.** No marketing budget is allocated; growth
  is organic-only, with the pilot's 60% completion criterion serving as
  an explicit checkpoint on the acquisition/engagement dimension.
- **Curriculum content-production cost:** remains moot for launch,
  deferred alongside the feature, against a quantified trigger.

**The reconciliation, unchanged:** R10,000 (~$550) against the previously-
cited $25,000-$120,000+ agency range is a 45×-220× gap, coherent only as a
founder-labor-plus-AI-assisted build. The 6-month runway is the binding
constraint: build, instrumented pilot (behind two trigger-defined
specialist-review gates, neither yet satisfied), and two user-owned
regulatory rechecks must all complete inside it, after which funding is
needed — with, at best, directional pilot evidence to raise on, or the
user self-funds up to R20,000 total before falling back to the newly-named
grant/startup-program candidate list, whose actual obtainability remains
untested.

**Still open:** the non-dilutive funding *target* is now named (see
above), but the funding-ask is still not precisely *sized* — the
researched award figures are program ceiling figures, not typical
disbursements, and actual obtainability is contingent on unconfirmed
founder-eligibility facts. **Separately, and untouched by this cycle's
research: no full financial projections (P&L, break-even analysis) exist
anywhere in this Business Case.** This is a distinct, still fully open
material question — no owner, no timing, no decision has been made about
it at any point in this document's history.

**This cycle's decisions:** name a prioritized, honestly-caveated
non-dilutive funding candidate list, resolving the seventh and final
`Verdict_v6.md` required change, at Supported-tier evidence.

Status remains Partial, and explicitly does NOT move this cycle despite
the funding-target resolution: the revenue side still rests on
unvalidated Guessing-tier estimates, and — decisively — **full financial
projections (P&L, break-even analysis) remain entirely absent**, a
material question with no owner, timing, or decision anywhere in this
document. The non-dilutive funding target is now named and prioritized
(Supported-tier), a genuine evidentiary improvement over "out for
research," but per this document's own Complete standard a single
fully-unaddressed material question is sufficient to hold a section at
Partial — so it does. Stated plainly, per standing practice: this
cycle's resolution is real but does not, on its own terms, close this
section.

## Validation Strategy

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Unaffected by this cycle's funding-target research.

**Closed streams, unchanged:** legal validation (retained opinion,
Verified-tier); child-development/age-appropriateness validation
(retained review, Verified-tier); all resulting design recommendations
carry decisions.

**Pilot — scope decided: double duty**, with the reviewer's underpowering
caution attached: demand findings will be directional and qualitative,
not statistically validated. The adopted measurement package includes a
candidate motivation-probe, review trigger defined — once a stable
working model exists, before any pilot testing with real families begins;
not yet occurred.

**Acquisition/mechanic-engagement checkpoint — resolved**, tied to the
pilot's own 60% task-cycle-completion criterion (see Success Criteria):
if fewer than 60% of enrolled pilot families complete 4 consecutive
weekly cycles, organic-only acquisition/mechanic engagement is treated as
not yet validated before widening release. This does not itself validate
whether organic-only acquisition can reach the corrected 9,150-30,500
install funnel in absolute terms — that remains untested, a distinct and
still-open question (see Market & Competition, Assumptions).

**Curriculum validation — remains reclassified, not an open gap for
launch.** Since curriculum content is deferred to v2, there is nothing to
validate at launch; this stream will be reintroduced when the feature is
actually built, against its quantified dual trigger.

**Still open, unchanged:** pricing/conversion validation (the pilot may
inform willingness-to-pay directionally but is not a conversion test);
account-linking UX/consent-flow validation; the no-Mpoints fallback
configuration's engagement loop has no validation plan.

Status remains Partial: the pilot is fully scoped and instrumented at the
decision level, both specialist reviews carry a defined trigger, and the
acquisition checkpoint is resolved for the pilot-to-wider-release
transition specifically — but market demand, pricing/conversion, and
absolute acquisition feasibility have no statistically meaningful
validation scheduled anywhere in the plan.

## Supporting Evidence

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Verified-tier:** `LegalOpinion_v1.md` and `ChildDevelopmentReview_v1.md`
(retained professionals); the user's direct clarification history through
`Clarifications_v22.md` (Verified-tier as to what was decided in that
cycle: the defined trigger point for both hard-gate specialist reviews;
confirmed advice-policy coverage for those two reviews; the interim
dispute-escalation mechanism; the low-end revenue/self-fund
cross-reference; the 60% acquisition checkpoint; the quantified v2-
curriculum trigger).

**Supported-tier:** four Research House engagements
(`ResearchFindings_v1-4.md`); the user's directly-cited South African
statutory/statistical sources; `BusinessCase_v16.md`'s restored Market &
Competition content. **`ResearchFindings_v4.md` (Engagement 4) is now
incorporated this cycle**, addressing the non-dilutive funding target:
eight candidates identified, five structurally excluded, two hard-excluded
on eligibility grounds, and one (NYDA) carrying a solidly-sourced timeline
against several weaker or unconfirmed items — all named explicitly in
Constraints and Financial Considerations, at Supported tier throughout,
never Verified.

**Assumed-tier, named explicitly:** the candidate motivation-probe and
the candidate data-breach/incident-response commitment (both
Incubator-drafted, neither yet reviewed — both reviews trigger-defined,
not merely recommended); the 2.0-children-per-family figure (stated, not
derived); the three-tier-to-six-way sub-band reconciliation draft
(Incubator-authored prep work, unreviewed).

**Bounded first-party data:** the n=10 interview round — non-
representative, governed by the standing instruction; the same rule
extends to the pilot's directional demand findings.

**Evidence-chain limitations, updated this cycle:** the self-fund-further
contingency's overall *sufficiency* remains untested. The grant/startup-
program fallback's *specific target* is no longer unresolved — Research
House Engagement 4 named a prioritized candidate list — but its *actual
availability to this founder* remains untested, contingent on
founder-eligibility facts (age; company-registration status) this
research explicitly could not confirm and did not assume. Full financial
projections (P&L, break-even) remain entirely absent from this Business
Case, untouched by this cycle's research and unaddressed in any prior
cycle.

Status remains Complete: the evidentiary base spans Verified-tier user
decisions and retained-professional opinions through Supported-tier desk
research to bounded first-party data and named Assumed-tier candidate
content, with each tier's limits stated, now including the fully
incorporated fourth Research House engagement.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved in v22 (`Clarifications_v22.md`):** specialist-review trigger
point defined for both hard-gate reviews (process only — reviews
themselves have not occurred, see below); advice-policy coverage
confirmed for those two reviews; beyond-48-hour dispute-escalation
mechanism defined (interim placeholder); low-end revenue scenario
cross-referenced against the self-fund-further contingency; acquisition
checkpoint/kill-metric quantified (60%); v2-curriculum "proved demand"
trigger quantified (500 subscribers AND 60% 90-day retention).

**Resolved this cycle (v23, `ResearchFindings_v4.md`):** the non-dilutive
funding target for the R20,000 self-fund ceiling's fallback — named as a
prioritized, honestly-caveated candidate list (primary: NYDA; secondary:
SEDA Technology Programme, Injini earlier-stage track; tertiary/
uncertain: TIA), resolving the seventh and final required change from
`Verdict_v6.md`. See Constraints for full detail and caveats.

**New — founder-specific facts required before pursuing the named
funding candidates, surfaced by `ResearchFindings_v4.md`, not resolved
by it:**

- **The founder's age** — gates NYDA's 18-35 eligibility band, the single
  best-timelined candidate. Not stated anywhere in this case study; not
  assumed here in either direction.
- **MiniMoney's current company-registration/CIPC status and SARS
  tax-clearance status** — gates SEDA Technology Programme eligibility.
  Not stated anywhere in this case study; not assumed here.
- (The founder's race/gender was flagged by the research as relevant to
  some excluded/adjacent programs — e.g., Google Black Founders Fund —
  but that program is already hard-excluded on the separate live-product
  requirement regardless, so this fact does not currently gate any
  viable named candidate; noted for completeness, not currently
  blocking.)

**Open — hard gates, trigger defined but not yet satisfied:**

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
  quantified v2-curriculum trigger, is still needed in Success
  Criteria.**
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
- Post-runway external funding-ask precise sizing (the target is now
  named, per above, but the ask amount itself is not fixed — researched
  figures are program ceilings, not typical disbursements). **Full
  financial projections (P&L, break-even analysis) — absent from this
  Business Case at every prior cycle, untouched by this cycle's research,
  and the sole remaining material question keeping Financial
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
identification and tracking, and every item carries its disposition. The
seventh required change from `Verdict_v6.md` is now resolved (with honest
caveats) rather than deferred; the founder-specific eligibility facts it
surfaces (age; company-registration status) are newly tracked here, not
silently absorbed into a "resolved" framing.

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
instruction: does resolving the seventh and final `Verdict_v6.md`
required change — the non-dilutive funding target — via Research House
Engagement 4 move the score, and does it move any section's Status?
Answer: it does not move the score, and it does not flip any section's
Status from Partial to Complete or vice versa.** The score is unchanged
at 94/130 = 72.3% (or 91/130 = 70.0% under the disclosed conservative
reading), identical to v21 and v22.

**Why no section's Status moves, argued explicitly:**

- **Constraints (already Complete):** this section already treated the
  funding-target question as compatible with Complete status under the
  "owned, timed, decided-fallback-*category*" pattern established for the
  SARB/FPB items. Research House Engagement 4 now supplies a decided
  fallback *target list* in place of a bare category — a genuine
  strengthening — but a section already scored Complete cannot score
  higher than Complete. No movement.
- **Financial Considerations (remains Partial):** the funding-target's
  *naming* is resolved, but this section's Partial status was never
  solely dependent on that one sub-item. **Full financial projections
  (P&L, break-even analysis) remain entirely absent** — a distinct
  material question, untouched by this research, with no owner, timing,
  or decision anywhere in this document's history. Per this document's
  own Complete standard, one fully-unaddressed material question is
  sufficient to hold a section at Partial. It does. No movement.
- **Risks, Outstanding Questions, Supporting Evidence, Roadmap (all
  already Complete):** register-type or decision-tracking sections whose
  Complete status requires comprehensive identification with a recorded
  disposition per item, not the closure of every underlying substantive
  question. The funding-target item's disposition is updated (from
  "routed to research" to "named, with caveats"); the sections were
  already Complete on that basis and remain so. No movement.
- **Assumptions (remains Partial):** the self-fund-further sufficiency
  assumption is now better-evidenced (a real candidate list exists) but
  not resolved (obtainability untested, contingent on unconfirmed founder
  facts) — and several other load-bearing assumptions in this section
  (2.0 children per family; organic-only acquisition sufficiency;
  exam-bonus risk-acceptance) are entirely untouched by this cycle. No
  movement.
- **No other section references the funding-target question at all.**

This is the expected outcome under this document's own standing practice:
a genuine, honestly-caveated evidentiary resolution of one specific
sub-item does not mechanically translate into a score increase unless it
closes every material question within a section's own scope. It does not
here, for the specific, stated reason above (P&L/break-even absence).

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

**Readiness Score = 94 / 130 = 72.3%.** Unchanged from v21 and v22.
Clears the completion gate's ≥70% threshold with a 2.3-point margin.

**Conservative alternative, withholding the Curriculum Design judgment
call (i.e., leaving it Partial = 2 pts):** 91/130 = **70.0%** — unchanged
from v21 and v22, still clears the threshold, with no margin.

No section is Critical + Incomplete: both Legal & Compliance and Child
Data & Consent are Complete.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) → 52%
(v13) → 52% (v14) → 52% (v15) → 52% (v16) → 70% (v17) → 70% (v18) → 70%
(v20, later found to have been honestly 67.7% by `Verdict_v5.md`'s own
arithmetic) → 72.3% (v21, or 70.0% conservative) → 72.3% (v22, or 70.0%
conservative) — unchanged; six of seven required changes resolved without
moving the score → **72.3% (v23, or 70.0% conservative) — unchanged. The
seventh and final `Verdict_v6.md` required change (non-dilutive funding
target) is now resolved via Research House Engagement 4, with full honest
caveats (only one candidate solidly timelined; two founder-eligibility
facts unconfirmed); this closes a genuine open item without moving the
score, because Financial Considerations' Partial status was never solely
dependent on it — the section remains Partial on the independent,
fully-unaddressed absence of financial projections (P&L, break-even).
Stated plainly, consistent with this document's standing practice:
resolving a required change is not the same as resolving a section, and
this cycle does not conflate the two.**

### Critical Gaps

1. **Execution capacity — bounded contingency, now with a named
   funding-fallback candidate list, obtainability still untested.**
   R10,000 total development budget plus a 6-month runway must contain
   the build, an instrumented pilot (behind two trigger-defined
   specialist-review gates, neither yet satisfied), two regulatory
   rechecks, and manual founder review of any dispute unresolved beyond
   48 hours — executed substantially by one person. Self-fund-further
   contingency: R20,000 total hard ceiling, explicitly the mechanism
   triggered if Year-1 revenue lands at the low end of the range;
   grant/startup-program funding is the stated fallback category, **now
   with a named, prioritized candidate list (see Gap 9), though actual
   obtainability remains untested and contingent on unconfirmed
   founder-eligibility facts.**
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
6. **Two specialist reviews have a defined trigger, neither yet
   satisfied.** Trigger: once a stable working model exists, before any
   pilot testing with real families begins — the same trigger used for
   the retained legal opinion. Both remain Evidence: Assumed until the
   reviews actually occur.
7. **Legal/build tasks pending, unchanged.** POPIA s14 retention period
   and deletion trigger; consent-flow documentation separation;
   lightweight parent identity-verification.
8. **Exam-bonus residual risk — accepted, candidate-instrumented, review
   trigger-defined but not yet obtained.**
9. **RESOLVED this cycle (with honest caveats): the non-dilutive funding
   target for the R20,000 self-fund ceiling's fallback.** Research House
   Engagement 4 (`ResearchFindings_v4.md`) named a prioritized candidate
   list: primary — NYDA Grant Programme (best-sourced near-term timeline,
   ~30 working days disbursement after approval, contingent on the
   founder's unconfirmed age falling in the 18-35 band); secondary — SEDA
   Technology Programme and, contingent on a future cohort opening,
   Injini's earlier-stage track (weaker timeline/eligibility
   confirmation); tertiary/uncertain — TIA instruments (eligibility
   itself unresolved). Several other candidates were hard-excluded on
   eligibility (Mastercard Foundation EdTech Fellowship; Google Black
   Founders Fund) or structural grounds (NEF; Standard Bank/Founders
   Factory Africa; Naspers Foundry; Grindstone), or are not viable
   near-term (SAB Foundation — 2026 cycle closed; FNB App of the Year —
   a post-launch recognition competition, not pre-launch seed capital).
   **What remains genuinely open: the founder's age and company-
   registration status, both unconfirmed by this research and required
   before pursuing the top two candidates** (see Outstanding Questions).
   Evidence: Supported (vendor desk research) — not Verified.
10. **RESOLVED in v22, retained for audit-trail continuity:**
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

**Status:** Complete | **Confidence:** High | **Evidence:** Verified
(reconciliation draft: Assumed; authorship: Unknown)

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs, even where the curriculum feature
itself is deferred.*

Unaffected by this cycle's funding-target research.

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

Unaffected by this cycle's funding-target research. Directly and
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
Practitioner) review has a defined trigger: once a stable working model
exists, and before any pilot testing with real families begins — the same
trigger already used for the retained legal opinion. This defines when
the review occurs, not that it has occurred. It has not yet occurred. It
is an Incubator-drafted candidate (Evidence: Assumed), specifying what
constitutes a breach, who is notified (parents; the Information
Regulator, per POPIA s22), and a notification timing standard consistent
with POPIA's "as soon as reasonably possible" language. The commitment
must not be in force, and real children's data must not be collected at
pilot, until this review has actually occurred.

Platform-policy items, unchanged: Google Play's Families Policy
loyalty-point disclosure requirement applies to the primary configuration
and is mooted under the no-Mpoints fallback; Apple's Kids Category
IAP-currency question is deferred with iOS and likewise mooted under that
fallback.

Status remains Complete: the section's central questions — consent-model
sufficiency and retention approach — are directly answered by retained
counsel; the breach commitment is an additive strengthening whose review
carries a defined trigger rather than an open-ended intention, still a
hard gate rather than an unresolved central question of the section's own
original scope.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Complete.
- Readiness Score ≥ 70%: **Yes — PASSES.** Score is unchanged from v21
  and v22: 94/130 = 72.3% under the primary computation, or 91/130 =
  70.0% under the disclosed conservative alternative. The case clears
  70% under both readings.
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

**This Business Case passes its own completion gate.** All seven of the
Investment Committee's required changes from `Verdict_v6.md` are now
resolved. The first six were resolved in v22 (specialist-review trigger
defined; advice-policy coverage confirmed; interim dispute-escalation
mechanism; low-end revenue/self-fund cross-reference; 60% acquisition
checkpoint; quantified v2-curriculum trigger). **The seventh — a concrete
non-dilutive funding target — is resolved this cycle (v23) via Research
House Engagement 4 (`ResearchFindings_v4.md`), named as a prioritized,
honestly-caveated candidate list (primary: NYDA; secondary: SEDA
Technology Programme, Injini's earlier-stage track; tertiary/uncertain:
TIA), at Supported-tier evidence — never Verified, per standing rule.**
This resolution surfaces two new, genuinely open founder-specific facts
(age; company-registration status) rather than closing the underlying
funding question entirely — named plainly in Outstanding Questions, not
glossed over. **The Readiness Score is unchanged at 94/130 = 72.3% (or
91/130 = 70.0% conservative)** — this cycle's resolution is a genuine
evidentiary improvement that does not, on its own terms, close Financial
Considerations' independently open P&L/break-even gap, so no section's
Status moves. Genuine open items remain — detailed in Critical Gaps —
led by execution capacity (funding fallback now named but obtainability
untested), two externally-unsettled regulatory questions, two
trigger-defined but not-yet-obtained specialist reviews, and the
newly-surfaced founder-eligibility-fact confirmations.
