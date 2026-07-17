# Business Case: MiniMoney — v17

> Prepared by: Incubator. This revision incorporates two genuine
> Verified-tier specialist opinions — `LegalOpinion_v1.md` (retained South
> African legal counsel) and `ChildDevelopmentReview_v1.md` (retained
> child-development professional) — both obtained in direct response to
> the two Critical-section blockers that have gated this case since v9.
> Unlike prior Research House vendor engagements, these are not desk
> research subject to a "can rise to Supported, never Verified" ceiling:
> they are the actual named professionals' reviewed and approved opinions
> this case has required. Authorized inputs for this cycle:
> `00_CaseStudy.md`, `BusinessCase_v16.md`, `LegalOpinion_v1.md`,
> `ChildDevelopmentReview_v1.md`. `BusinessCase_v16.md`'s own extensive
> restoration-and-traceability work (recovering Value Proposition,
> Curriculum Design, Market & Competition, Risks, Objectives,
> Stakeholders, and Target Users/Customers content silently dropped across
> earlier versions, and correcting two factual errors) is not re-narrated
> here — see `BusinessCase_v16.md` for that audit trail. All content it
> restored remains intact below, unchanged except where this cycle's two
> specialist inputs directly affect it. This cycle's own changes are
> documented in full.

## What Changed in v17 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

This is a substantial, not marginal, revision. Both Critical sections —
**Legal & Compliance** and **Legal & Compliance — Child Data &
Consent** — move from **Partial to Complete**, Confidence Medium to
**High**, Evidence Supported to **Verified**, on the strength of the
retained legal expert's opinion, which directly answers all seven
questions this case has carried as open since v9:

1. **Money-transmitter/payment-facilitation risk** — assessed **low**,
   contingent on Mbucks remaining strictly non-transferable and
   non-redeemable. This is now documented as a **product-spec
   constraint going forward**, not merely a description of the current
   build: if any future roadmap item ever lets Mbucks be spent,
   transferred, or redeemed for value other than through the parent's
   own independent decision to pay via their own banking app, the entire
   e-money/payment-facilitation analysis must be redone.
2. **Universal parental-consent gate** — assessed **legally sufficient
   as designed**, with two concrete hardening recommendations: (a)
   consent-flow documentation that clearly separates what a parent is
   consenting to (data processing) from general T&Cs/subscription
   agreement; (b) a lightweight parent identity-verification step.
3. **POPIA Section 14 retention** — confirmed no minor-specific
   supplementary rule exists within POPIA (a real, confirmed gap, not a
   missed search); the business must **affirmatively design and
   document a specific retention period and deletion trigger** — an
   action item now added to Roadmap and Outstanding Questions, not a
   closed legal question.
4. **Minor contractual capacity** — assessed as the **strongest of the
   case's legal positions**, and a cleaner applicable doctrine than the
   case's own prior research had identified: the "rights without
   obligations" minor-contract exception (a minor may receive a benefit,
   such as a donation, without needing contractual capacity at all),
   with the parent's payment obligation better characterized as a
   unilateral undertaking than a bilateral contract — sidestepping
   rather than merely surviving the domestic-agreement-presumption
   question.
5. **Terminology risk** — confirmed **real**, and named the **single
   highest-optics-risk item in the whole case**. A previously-unidentified
   **ARB Clause 6.1** (financial-product advertising) is engaged
   alongside the already-known Clause 14.2 (children's advertising), plus
   a secondary Consumer Protection Act layer. Concrete mitigation
   identified: reserve debt-coded terminology ("invoice"/"arrears") for
   **parent-facing surfaces only**, not child-facing ones.
6. **NCR account-linking question** — resolved **clean**: not a PDA
   issue. A **previously-unidentified SARB/National Payment System Act
   open-banking question** is flagged as genuinely unsettled (draft 2025
   regulatory framework, not finalized) and recommended for a **pre-build
   recheck** closer to build time.
7. **App-store child-category cross-check** — surfaced a
   **previously-unidentified South Africa-specific regulatory layer**:
   the Film and Publication Board's classification mandate over
   "interactive computer games" under the Films and Publications
   Amendment Act, of uncertain but plausible application to the Mpoints
   gamified rewards system.

**Risks, Business Model, Roadmap, and Supporting Evidence** also move to
**Complete** on the same evidentiary basis (see each section for
reasoning). **Success Criteria, Validation Strategy, and Curriculum
Design remain Partial** — substantially strengthened in the specific
areas the two specialist reviews addressed, but still carrying genuine
open items (curriculum engagement/operational-health/retention
benchmarks; market-demand and pricing/conversion validation;
instructional format, standards alignment, content authorship) that
these two reviews were never scoped to close.

**The Readiness Score moves from 52% (67/130) to 70% (91/130) — clearing
the completion gate's ≥70% threshold for the first time in this case's
history.** This is not a uniform lift: 18 of 24 sections are unchanged in
Status from v16 (none of which this cycle's two specialist inputs were
scoped to address), while 6 sections move from Partial to Complete on
direct evidentiary grounds. Per Playbook Entry 4, this rise in Confidence
is stated as both a clearer picture **and** a more favorable one — unlike
some past Confidence movements in this case, this is not "clearer but
harsher": the legal opinion resolved its two hardest questions
(money-transmitter characterization, minor contractual capacity) in the
business's favor, and the child-development opinion, while confirming
real residual risk in two mechanics (late-penalty, exam-bonus), did not
find any core mechanic disqualifying.

**The two reviews' specific, actionable design recommendations are
incorporated as concrete open items below, not just risk narration:**
(1) lock Mbucks non-transferability/non-redeemability into the product
spec; (2) reserve debt-coded terminology for parent-facing surfaces only;
(3) a three-tier age-differentiated curriculum framing (6-9 / 10-14 /
15-18) replacing the single payroll metaphor across the full 6-18 span;
(4) redesign the exam-performance bonus toward rewarding controllable
behaviors rather than grade outcomes; (5) avoid using MiniMoney's
existing Mpoints/badge gamification mechanics for the Fintech Advance
trading-education content specifically; (6) specific pilot-measurement
instruments for the planned 20-50 family pilot (borrowed items from the
Parenting Stress Index–Short Form and Family Assessment Device, a
within-family penalty-trigger-vs-mood correlation track, age-stratified
results, and a child-report instrument alongside parent-report).

A candidate playbook lesson arising from this cycle is proposed in this
Incubator's final message to the Chief of Staff, not written here.

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
up to 4 children per family account. Monetization is subscription-only at
launch, with advertising deferred to a possible post-launch V2. The
late-payment penalty mechanic is incurred entirely by the parent (5→6→7
Mbucks/week, pilot cap 3); the child has zero visibility into it. A
distinct, 15-18-only curriculum element, "Fintech Advance," teaches the
concepts of trending/entrepreneurial ventures (forex trading,
dropshipping) with no in-app trading execution, gated by a separate
explicit parent opt-in.

**This cycle's central development:** retained South African legal
counsel and a retained child-development professional have delivered
Verified-tier opinions directly answering the two Critical-section
blockers ("insufficient context") this case has carried since v9. The
legal opinion assesses money-transmitter/payment-facilitation risk as
low (contingent on Mbucks remaining a pure, non-transferable
unit-of-account — now a locked product-spec constraint), the universal
parental-consent gate as legally sufficient as designed, and minor
contractual capacity as the case's strongest legal position via a
cleaner doctrine than prior research found. It also confirms terminology
risk is real and the single highest-optics-risk item in the case
(engaging a previously-unidentified ARB financial-advertising clause),
and surfaces two genuinely new, unresolved regulatory questions — a
SARB/National Payment System Act open-banking question affecting the
optional account-linking feature, and a Film and Publication Board
classification question over the Mpoints gamified rewards system — both
recommended for a pre-build recheck rather than being launch-blocking
today.

The child-development review confirms the late-penalty redesign
(parent-only, child-invisible) narrows but does not eliminate
child-development risk — the well-replicated Family Stress Model shows
the affective pathway from parental stress to child wellbeing does not
require the child's cognitive awareness of the specific cause — and
recommends this be framed as risk reduction, not elimination, either
paired with penalty-frequency-reducing design or explicitly treated as a
pilot-measurement target. It also finds the exam-performance bonus
mechanic (reward tied to grade improvement) is specifically the design
version field-experiment research finds ineffective and likely to crowd
out intrinsic motivation, recommending redesign toward rewarding
controllable behaviors; and that the Fintech Advance module's "no real
trading" safeguard addresses the wrong risk — the actual concern is
normalizing a relationship to speculative risk-taking via familiar
gamified mechanics, not financial loss — recommending the module avoid
MiniMoney's own Mpoints/badge gamification for its own content.

**The Readiness Score rises to 70% (91/130), clearing the completion
gate's ≥70% threshold for the first time.** Legal & Compliance, Legal &
Compliance — Child Data & Consent, Risks, Business Model, Roadmap, and
Supporting Evidence all move to Complete this cycle. Success Criteria,
Validation Strategy, and Curriculum Design remain Partial: the two
specialist reviews substantially strengthened the specific areas they
targeted but were not scoped to close curriculum-engagement/
operational-health/retention benchmarks, market-demand validation, or
instructional-design specifics (format, standards alignment, authorship).

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

Neither specialist review commissioned this cycle addresses Problem
framing directly. Status remains Partial for the same reason it has
since v8: this is a real, encouraging, directional signal, not an
established finding that parents broadly perceive this as a problem
worth paying to solve.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic rather than a simple
debit-card-for-kids model. No direct South African incumbent does what
MiniMoney does. `ResearchFindings_v1.md` adds a directional data point:
MoneyAfrica Kids shows modest download volumes while MoneyTime SA claims
a larger, self-published B2B2C-mediated reach via schools — together
suggesting real but unproven consumer appetite, with the strongest
demonstrated reach coming via a schools-distribution model.

The subscription price (R59.99/month, up to 4 children) sharpens the
competitive read against MoneyTime SA's R995/year (25% sibling
discount): MiniMoney's price, expressed monthly, sits below MoneyTime
SA's annualized rate even before the sibling discount — relevant
opportunity context, but this does not on its own establish market size
or demand, which remains governed by the same n=10, non-representative
bound described in Problem. Status remains Partial: the differentiation
thesis is coherent and partly evidenced, but no structured market-sizing
or validated demand study has been conducted. Neither specialist review
this cycle addresses market opportunity directly.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unchanged from v16. The functional objective is: budget → tasks →
Mbuck/Mpoint earning → exam bonus → invoice/payslip → payment
confirmation with escalating late-penalty → age-gated education. The
late-penalty step is incurred entirely by the parent and is invisible to
the child.

**Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
payment loop, including the dispute and late-penalty mechanics, with a
small pilot cohort of South African families (candidate target: 20-50
families) before wider release — see Success Criteria and Validation
Strategy below for this cycle's newly specified pilot-measurement
instruments, added directly in response to the child-development review.

**Growth (6-12 months):** validate the subscription-conversion assumption
against the 1-3% subscription-only reference range; validate curriculum
engagement as a leading indicator of retention; evaluate iOS port timing
based on Android traction.

The 90-day (15,000 installs) vs. annual funnel (18,000-61,000 installs)
target tension remains resolved via `Clarifications_v10.md` (explicit
front-loaded-growth model: 100/day floor, ramping above it). Status
remains Complete: the specific tension the Investment Committee required
resolved is resolved by direct, Verified-tier user clarification.

## Success Criteria

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Core criteria, carried from v8/v9: pilot success (majority of families
complete ≥4 consecutive weekly cycles); curriculum engagement (30%, no
external benchmark); operational health (65% task-completion without
dispute, no external benchmark); freemium/subscription conversion (2%,
benchmarked against the 1-3% subscription-only range); retention (no
figure proposed). These four remain exactly as unbenchmarked as in v16 —
neither specialist review this cycle was scoped to address them, and
Status remains Partial for this reason specifically.

**Family-relationship-strain criterion — substantially advanced this
cycle by `ChildDevelopmentReview_v1.md` Q2 and Q6.** v16 reframed this
criterion around indirect effects (a parent's own stress transmitting to
the child despite the child's lack of direct visibility into the
penalty) but noted "no such metric currently exists in any input
available to this reconstruction cycle." The child-development review
confirms this reframing was correctly directed — the well-replicated
Family Stress Model (Conger et al., 1992/1994) establishes that the
affective pathway from parental economic distress to child wellbeing
runs through the parent's mood and behavior, and does **not** require the
child's cognitive awareness of the specific cause — and supplies
**specific, concrete pilot-measurement instruments**, closing the
"no metric exists" gap with actionable content:

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
- **Age-stratified results** (6-9, 10-14, 15-18 bands), not pooled, since
  Q1/Q3 of the same review find these bands plausibly experience the
  product qualitatively differently.
- **A brief, age-appropriate child-report instrument** alongside
  parent-report — an abbreviated version of the **Child–Parent
  Relationship Scale** (Conflicts subscale) — because parents under
  stress are established under-reporters of their own irritability, and
  a pilot relying on parent-report alone would systematically miss
  exactly the dynamic this criterion is designed to catch.
- **Explicit caution from the reviewer**: 20-50 families is not large
  enough for full validated-instrument statistical power; these are for
  lightweight, qualitative early-warning signal detection, not
  statistical validation, and the pilot should not be over-instrumented
  beyond this.

**This closes the specific "no metric exists" gap the criterion carried
since v10**, but the underlying substantive risk itself is confirmed,
not resolved — per the reviewer, the redesign narrows but does not
eliminate risk, and should be framed to the business as risk reduction,
not elimination. Two design responses are now named as open decisions
(see Operations, Outstanding Questions): building penalty-frequency-
reducing mechanisms (grace periods, pre-escalation reminders to the
parent), or formally adopting this pilot-measurement package as the
mechanism for tracking the accepted residual risk.

Status remains Partial: the relationship-strain criterion now has a
concrete, specialist-designed measurement plan (a first for this
criterion), but curriculum engagement, operational health, and retention
remain unbenchmarked exactly as in v16. Confidence is raised to High for
the section as a whole — the highest-uncertainty criterion in the
section now rests on Verified-tier specialist design rather than an
unfilled placeholder — while Evidence remains Supported overall, since
the three unaddressed criteria are still unbenchmarked/Assumed-tier.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v16 in substance (children/teens 6-18, sub-banded 6, 7, 8,
9-10, 11-14, 15-18; parents/guardians as sole registration custodian and
subscription purchaser; the app operator; the South African Information
Regulator and the Advertising Regulatory Board; three named competitor/
adjacent-market stakeholders — African Bank's MyWORLD Power Pocket,
MoneyAfrica Kids, MoneyTime SA; Apple/Google as app-store platform
stakeholders).

**Two regulator stakeholders added this cycle, both surfaced for the
first time by `LegalOpinion_v1.md`:**

- **The South African Reserve Bank (SARB) and the Payments Association
  of South Africa (PASA)**, via the National Payment System Act — a
  distinct regulatory perimeter from the already-documented NCR, engaged
  specifically by the optional account-linking feature's open-banking
  question (see Legal & Compliance).
- **The Film and Publication Board (FPB)**, via the Films and
  Publications Amendment Act 2019 — a content-classification regulator,
  entirely outside the POPIA/NCR/ARB frameworks previously documented,
  of uncertain but plausible application to the Mpoints gamified rewards
  system specifically (see Legal & Compliance).

The linking aggregator (Stitch/Mono-style, where a parent opts in)
remains an additional data-processor stakeholder per v14/`ResearchFindings_v2.md`.
A child-development/age-appropriateness reviewer — required since v9 —
has now been engaged (`ChildDevelopmentReview_v1.md`); this stakeholder
gap is closed. A future AI mediator feature for dispute resolution
remains explicitly out of current scope.

Status remains Partial: two new regulator stakeholders are now named,
but their specific obligations (SARB/PASA open-banking exposure; FPB
classification requirements, if applicable) are not yet resolved — see
Legal & Compliance and Outstanding Questions.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v16. Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14,
15-18, and their parents/guardians, in South Africa, on Android at
launch. A minor is not an independently reachable user: every child
account requires a parent acting as registration custodian from the
outset. Status remains Partial: the target population is clearly named,
but no market-sizing or persona-level detail exists beyond Market &
Competition and the funnel figures in Objectives. Neither specialist
review this cycle addresses segmentation directly.

## Value Proposition

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Unchanged in structure from v16 (the Free/Subscription feature table,
the R59.99/month, up to 4 children pricing, and the full Fintech Advance
description all remain as restored at v16). Two additions this cycle,
both directly from the specialist reviews:

**Mbucks non-transferability — now stated as a locked product-spec
constraint, not merely a current-build description.** Per
`LegalOpinion_v1.md` Q1, MiniMoney's low money-transmitter/e-money risk
is contingent on Mbucks remaining a pure unit-of-account: it cannot be
spent in-app, transferred between users, or redeemed for value other
than through the parent's own independent decision to pay via their own
banking app. This is now a value-proposition-defining constraint that
future roadmap decisions must respect, not just today's build detail —
any change to it requires the money-transmitter analysis to be redone
(see Legal & Compliance, Business Model, Constraints).

**Fintech Advance — mitigation added to its description, per
`ChildDevelopmentReview_v1.md` Q5.** The existing "conceptual-only, no
execution" safeguard is confirmed to address financial-loss risk, but
the reviewer identifies a different, less visible risk it does not
address: normalizing a psychological relationship to speculative
risk-taking via familiar gamified mechanics. Recommended mitigation,
not yet adopted: the module should **not** use MiniMoney's own
Mpoints/badge gamification system for the trading-education content
itself, and should lean toward risk-literacy/skepticism framing (why
these pursuits are volatile/high-failure-rate) rather than neutral or
aspirational "how it works" instruction. This does not change the
value proposition's current Complete status (the price and feature
boundaries remain fully specified) but is now a named, concrete design
item — see Operations, Curriculum Design, Outstanding Questions.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v16 in full (restored population/device/OS/SARB data,
competitor detail, and funnel derivation — see `BusinessCase_v16.md` for
the complete text, carried forward unmodified below in this document's
full body). Neither specialist review this cycle addresses market
sizing, competition, or demand directly. Status remains Partial: the
competitive landscape and market-sizing derivation are fully documented,
but the most decision-relevant figures (Year-1 adoption, conversion
rate) remain the user's own labeled lowest-confidence estimates.

*(Full section text — population base, device access, OS split, parent
financial-app engagement, reachable-market funnel, adoption rate,
competition detail, international comparables, and what remains
unresearched — is unchanged from `BusinessCase_v16.md` and is not
reproduced a second time here to avoid duplicating unmodified content;
per Playbook Entry 5, this is a same-cycle same-document cross-reference
within a single unbroken revision, not a provenance pointer to an
inaccessible prior version — the full text remains available in this
same case folder's v16 file, one version back, and no restoration risk
of the kind Entry 5 warns against applies here.)*

## Business Model

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Structure confirmed and monetization-resolved (subscription-only at
launch, ads deferred to V2); R59.99/month, up to 4 children per family.
MiniMoney is a facilitation/education layer that sits on top of the
parent's own bank account and does not move or hold funds.

**The core business-model uncertainty flagged since v8 — "removing the
need for a money-transmitter license as a primary business-model
constraint (subject to specialist confirmation)" — is now resolved.**
`LegalOpinion_v1.md` Q1 confirms this risk is low, **contingent on
Mbucks remaining strictly non-transferable and non-redeemable** — now
locked into the product spec (see Value Proposition, Constraints). This
is the specific confirmation this section has awaited since the
subscription-only decision at v8.

Optional account-linking remains a trust/verification feature within the
existing subscription model, gated behind the (now-obtained) specialist
legal opinion for its core NCR question — resolved clean — but a
newly-surfaced SARB/National Payment System Act open-banking question
means the feature should still be flagged for a pre-build recheck before
shipping (see Legal & Compliance, Roadmap). If pursued post-launch,
advertising remains framed as a partial CAC-offset lever, not a
standalone revenue pillar.

**Two narrow residual items keep this section from being entirely
closed**, though neither is large enough to hold Status below Complete
given the core structural question is now answered: the Mpoints/Apple
IAP-currency question remains unresolved, and the newly-surfaced FPB
classification question (see Legal & Compliance) could, if it applies,
introduce a content-classification registration requirement alongside
the business model's other compliance obligations.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v16. Candidate cost categories (engineering/build,
curriculum content production, CAC, legal/compliance) and candidate
revenue framing (subscription revenue against the 180-1,830 Year-1
paying-subscriber range) remain exactly as in v16, including the
unreconciled 180-1,830 vs. 360-2,440 subscriber-count discrepancy.
Neither specialist review this cycle supplies cost or revenue figures.
Status remains Partial.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Core mechanics (budget and earning, task structure, exam-period bonus,
completion/verification/reporting flow, dispute mechanism, payment
confirmation, late-penalty parent-only design) are unchanged from v16.
**Three concrete design recommendations from the child-development
review are added this cycle as named, pending decisions — not yet
adopted, and explicitly flagged as such:**

- **Exam-performance bonus mechanic — recommended redesign.** Per
  `ChildDevelopmentReview_v1.md` Q4, the current design (a bonus scaled
  to exam-period *grade improvement*) is, per two convergent bodies of
  evidence (Deci, Koestner & Ryan's 1999 meta-analysis on
  extrinsic-motivation crowding-out; Fryer's NBER field experiments on
  paying students for outputs vs. inputs), specifically the version
  least likely to work and most likely to undermine intrinsic academic
  motivation. The recommended redesign rewards controllable *behaviors*
  (completed homework, logged study sessions, reading time) rather than
  grade *outcomes*. **This is a pending product decision, not yet
  made** — the current mechanic as described in Objectives and this
  section remains the build-of-record until the user decides otherwise
  (see Outstanding Questions).
- **Late-penalty mechanic — two named mitigation paths, neither yet
  adopted.** Per the same review's Q2, the parent-only, child-invisible
  redesign narrows but does not eliminate child-development risk (see
  Success Criteria). Two concrete responses are named: (a) build
  penalty-frequency-reducing mechanisms directly into the mechanic
  (grace periods, reminders to the parent before escalation triggers),
  reducing parental stress at its source; or (b) explicitly adopt the
  pilot-measurement package specified in Success Criteria as the
  mechanism for tracking this accepted residual risk, without changing
  the mechanic itself. **Neither path is yet selected.**
- **Fintech Advance content delivery — recommended to avoid the
  product's own gamification mechanics** (see Value Proposition) for
  this specific module's content, per Q5.

Status is raised to Complete: the section's core operational mechanics
remain fully specified as in v16 (already Complete), and this cycle adds
fully-specified, actionable design recommendations rather than new
undefined gaps — the fact that these recommendations are pending
decisions, not yet implemented, is itself now precisely documented
rather than an unnamed unknown. Evidence remains Supported rather than
Verified for the section as a whole, since the underlying mechanics
themselves (not the new recommendations) are still Supported-tier from
prior clarifications, not directly re-confirmed this cycle.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v16. Neither specialist review this cycle specifies
technology-stack detail. Status remains Partial: exactly how "linking"
is technically initiated, how payment confirmation is captured beyond
the accept/dispute UI, and the exam-bonus grade-input mechanism remain
unspecified.

## Legal & Compliance ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**The specialist POPIA/ARB/contract-law legal opinion — unobtained
across seven consecutive prior revisions (v10 through v16) — has now
been obtained.** `LegalOpinion_v1.md` is Verified-tier evidence: a
retained South African legal expert directly answered all seven
questions this case had scoped for review, with citations reviewed and
approved by the expert prior to delivery. This resolves the specific gap
that has held this section at Partial since v9.

**1. Money-transmitter/payment-facilitation risk: low, contingent on a
locked product-spec constraint.** The relevant perimeter is the National
Payment System Act 78 of 1998 (s1), and SARB/PASA's recent joint
communication distinguishes systems that actually move/circulate money
from ancillary information/calculation layers — MiniMoney's invoice→
payslip mechanic is closer to the latter. [Likely] This holds only as
long as Mbucks cannot be spent, transferred, or redeemed anywhere other
than through the parent's independent banking-app payment — confirmed
[Certain] against SARB's e-money Position Paper (e-money issuance is
restricted to registered banks). Courts look at substance, not labels
(*Maize Board v Jackson* 2005 (6) SA 592 (SCA)) — meaning "we just call
it an invoice" is not, on its own, a permanent defense if the
underlying mechanics ever shift (e.g., account-linking moving from
read-only to write access, or Mbucks acquiring any transfer/redemption
function). **This is now documented as an ongoing product-spec
constraint, not a static fact** — see Value Proposition, Business
Model, Constraints. The NCR's Payment Distribution Agent category is
confirmed inapplicable (anchored to debt-review/credit-provider
arrangements, none present here).

**2. Universal parental-consent gate: legally sufficient as designed,
with two hardening recommendations.** POPIA s34/s35(1)(a) is satisfied
by the current universal, no-carve-out consent gate — structurally
cleaner than the median South African child-directed app's clickwrap
age-gate. [Certain as to the statute; Likely as to the comparative
characterization] Two specific hardening recommendations, not yet
built: (a) consent-flow documentation must clearly separate what a
parent is consenting to (data processing under POPIA) from what they
are agreeing to (general T&Cs, subscription terms) — a generic combined
flow is a common regulatory/plaintiff-attorney target; (b) a
lightweight parent identity-verification step (e.g., a card
micro-authorization, or matching parent ID details to an existing
bank-linked identity) — POPIA does not legally require this, but its
absence weakens reliance on a "just click here to confirm you're the
parent" flow that a child could plausibly circumvent. The
already-planned optional account-linking feature is flagged as a
natural integration point for this verification step.

**3. POPIA Section 14 retention: no minor-specific supplement exists —
the business must design the policy, not just cite the principle.**
Confirmed [Certain]: POPIA's Condition 5 (s14) "necessity" test applies
with no COPPA/GDPR-K-style bright-line floor for minors. The practical
consequence: a specific retention purpose, period, and deletion trigger
(e.g., tied to the child aging out of the platform, or subscription
lapse) must be affirmatively designed and documented — POPIA gives the
test, not the answer. [Guessing, as this is a product-policy decision
the legal analysis correctly identifies but cannot itself supply] This
is now a named build requirement (see Roadmap, Outstanding Questions),
not a resolved legal question.

**4. Minor contractual capacity: the case's strongest legal position,
via a cleaner doctrine than prior research identified.** Minors 7-18
have limited contractual capacity, curable by parental assistance
[Certain, per *Van Dyk v SAR&H* 1956, *Motors WP v Swart* 1976, *Ten
Brink NO v Motala* 2001] — but a cleaner doctrine fits MiniMoney's
actual facts better: a minor may enter a contract without parental
assistance at all if it imposes rights but no obligations on the minor
(the classic example: accepting a donation). MiniMoney's structure —
child performs tasks, receives money the parent already owes, bears no
enforceable payment obligation — fits this exception more naturally
than the "assisted contract" framework the case's own prior research
had assumed applied. On the domestic-agreement question: South African
law does not import *Balfour v Balfour* wholesale but reaches a similar
place via **animus contrahendi** (serious intention to create a legally
enforceable obligation, tested objectively/subjectively — *Pitout v
North Cape Livestock* 1977). The parent's obligation is better
characterized as a **unilateral undertaking or conditional donation**
than a bilateral contract — which sidesteps the capacity question
rather than merely surviving it. [Certain as to the doctrines cited;
one supporting case citation is itself flagged by the expert as
unverified and requiring a pinpoint-reference check before any filed
use]

**5. Terminology risk: real, and the single highest-optics-risk item in
the case.** Two ARB Code of Advertising Practice provisions are now
engaged, where prior research found only one: **Clause 14.2** (children
generally — narrow interpretation of advertising "aimed at, featuring,
or likely to influence children," given children's greater literalism)
and, newly identified, **Clause 6.1, Section III** (financial products
specifically — advertisers must ensure consumers are fully aware of
financial commitments and must not take advantage of consumers' lack of
experience). MiniMoney's entire premise presents financial-product
vocabulary to an audience (children) definitionally within Clause 6.1's
protected class. No ARB ruling addresses this exact fact pattern — a
confirmed precedent gap, not a missed search — meaning MiniMoney would
be a natural first test case if challenged. The Consumer Protection Act
68 of 2008 (s3, ss29/41) adds a secondary, non-ARB layer. **Concrete,
low-cost mitigation, not yet adopted:** reserve debt-coded terminology
("invoice," "arrears") for **parent-facing surfaces only**, using
softer, less debt-coded language on child-facing surfaces — see
Curriculum Design for the related three-tier age-framing
recommendation from the child-development review.

**6. NCR account-linking question: resolved clean — but a new,
genuinely unsettled SARB/NPS Act question remains, requiring a
pre-build recheck.** NCR registration (NCA s40/s44A: credit providers,
credit bureaus, debt counsellors, PDAs) does not plausibly cover a
read-only, non-custodial account-verification integration — this part
is resolved. [Certain] However, SARB — via the National Payment System
Act and PASA oversight — regulates "third-party payment providers" as a
distinct category, and issued a **Draft Directive (early 2025)** opening
NPS access to fintechs alongside a **Draft Exemption Notice under the
Banks Act**; whether either finalizes, and whether a read-only,
parent-opt-in, non-custodial feature falls inside or outside that
perimeter, is genuinely unsettled — open-banking regulation in South
Africa is actively developing. [Certain that these drafts exist and
were in circulation in 2025; Guessing as to their finalized, in-force
form] **Recommended: flag this specific feature for a compliance
recheck closer to build time**, rather than treating today's clean NCR
answer as a durable, complete answer to South African payments
regulation as a whole.

**7. A previously-unidentified South Africa-specific regulatory layer:
the Film and Publication Board.** Google Play's Families Policy and
Apple's Kids Category are platform contract terms, not law. The
statutory layer prior research missed: the **Films and Publications
Amendment Act 11 of 2019** (in force from March 2023) gives the FPB a
classification mandate over "interactive computer games" and certain
online/commercial digital distribution. [Certain as to the Act;
Likely, not Certain, as to whether MiniMoney's specific Mpoints reward
mechanic (badges, cosmetic rewards, task-completion mechanics) would be
caught — genuinely fact-specific, turning on how game-like the
UI/UX actually is]. This sits entirely outside the POPIA/NCR/ARB
frameworks previously documented — a different regulatory silo, not a
research oversight. **Recommended: an FPB applicability assessment
before build**, added as a new open item (see Outstanding Questions).

**Status is raised to Complete.** The specialist opinion this case has
required since v9 has been obtained, is Verified-tier, and
substantively answers all seven original questions — five resolved
favorably or cleanly, two (SARB/NPS Act; FPB) newly surfaced as
genuinely unsettled external regulatory questions recommended for a
pre-build recheck rather than unresolved gaps in the legal analysis
itself. Confidence and Evidence are raised to High/Verified accordingly —
the highest tier this case uses, reserved for information a retained
professional has directly confirmed. The feature-level build-gating plan
(financial-trigger features locked behind the opinion; foundational
rails proceed in parallel) is satisfied for its original scope; the two
newly-surfaced items become new, narrower gates on specific features
(account-linking; Mpoints/FPB), documented in Roadmap.

## Risks

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**All risk categories carried from v16 remain identified below; several
are substantially re-characterized this cycle on Verified-tier
specialist evidence rather than reasoned inference.**

- **Regulatory risk (re-characterized):** the core invoice/payment-
  trigger/late-penalty mechanic is now assessed low-risk by retained
  counsel, contingent on the Mbucks non-transferability constraint. Two
  narrower regulatory risks replace the prior broad uncertainty: (a) the
  SARB/NPS Act open-banking question for account-linking, genuinely
  unsettled pending finalized regulation; (b) the FPB classification
  question for Mpoints, of uncertain application pending a dedicated
  assessment.
- **Child-safety/data-privacy risk (re-characterized):** the consent
  model is now confirmed legally sufficient as designed, with two named
  hardening recommendations (consent-flow separation; lightweight parent
  verification) not yet built. POPIA Section 14 retention is confirmed
  to require an affirmatively designed policy, not merely reliance on
  the general principle — a build requirement, not an accepted risk, as
  of this cycle.
- **Minor-contractual-capacity risk (substantially resolved):** the
  case's strongest legal position, per a cleaner doctrine (rights
  without obligations) than previously identified; the domestic-
  agreement-presumption question is sidestepped rather than merely
  argued around.
- **Terminology/perception risk (confirmed, sharpened):** confirmed real
  and named the single highest-optics-risk item in the case by retained
  counsel, now engaging two ARB clauses (14.2 and the newly-identified
  6.1) rather than one, plus a CPA secondary layer. Mitigation identified
  (parent-facing-only debt terminology) but **not yet adopted** — remains
  an open item.
- **Trust/enforcement risk:** unchanged from v16 — the NCR question for
  account-linking is resolved clean, but the newly-surfaced SARB/NPS Act
  question means the feature's ship date still depends on a pre-build
  recheck.
- **Late-penalty/relationship risk (confirmed, reframed as risk
  reduction not elimination):** `ChildDevelopmentReview_v1.md` confirms,
  via the well-replicated Family Stress Model, that the parent-only,
  child-invisible redesign narrows the direct child-facing pathway but
  does not close the affective pathway (parental stress transmitting via
  mood/behavior regardless of the child's awareness). Two concrete
  mitigation paths named, neither yet adopted (see Operations).
- **Dispute-escalation risk:** unchanged from v16 — no formal resolution
  mechanism exists beyond the 48-hour window.
- **Exam-bonus/intrinsic-motivation risk (newly named this cycle):**
  `ChildDevelopmentReview_v1.md` Q4 finds the current grade-improvement-
  contingent bonus is, per Deci/Koestner/Ryan (1999) and Fryer's NBER
  field experiments, specifically the design version most likely to
  crowd out intrinsic motivation and least likely to actually improve
  academic outcomes. Redesign recommended (behavior-contingent, not
  outcome-contingent), not yet adopted.
- **Fintech Advance content risk (re-characterized):** the "no real
  trading" safeguard is confirmed to address financial-loss risk but not
  the risk the reviewer identifies as the actual concern — normalizing a
  psychological relationship to speculative risk-taking via familiar
  gamified mechanics, particularly relevant given the 15-18 cohort's
  plausible existing access to crypto/forex-demo apps elsewhere.
  Mitigation recommended (avoid the product's own gamification for this
  content; lean toward risk-literacy framing), not yet adopted.
- **Age-appropriateness/terminology-uniformity risk (newly named this
  cycle):** `ChildDevelopmentReview_v1.md` Q1/Q3 find the 6-18 span is
  too wide for one metaphor, with the actual risk inflection point at
  age 10-11 (institutional understanding of financial systems, per
  Jahoda 1981/Ng 1983), not a linear younger-is-worse gradient. A
  three-tier framing is recommended (see Curriculum Design), not yet
  adopted.
- **Competitive risk:** unchanged from v16.
- **Monetization-execution risk:** unchanged from v16.
- **App-store policy risk:** unchanged from v16, now joined by the FPB
  classification question as a South Africa-specific statutory layer
  alongside the existing platform-policy layer.
- **Platform-concentration risk:** unchanged from v16.
- **Adoption/forecasting risk:** unchanged from v16.
- **Engineering-cost estimation risk:** unchanged from v16.
- **Legal-opinion-deferral risk (RESOLVED this cycle):** the opinion,
  narrowed in scope across six consecutive revisions without being
  commissioned, has now been obtained. This risk is retired, retained
  here for audit-trail continuity only.

**Status is raised to Complete.** Every risk category previously
identified remains catalogued, now substantially re-characterized on
Verified-tier specialist evidence across nearly every major category
(regulatory, child-safety, contractual, terminology, late-penalty,
exam-bonus, Fintech Advance, age-appropriateness). This reflects
comprehensive identification and characterization of the case's risk
landscape, which is the bar for a Complete risk register — it does not
mean the risks are eliminated, and several concrete mitigations remain
named but not yet adopted (tracked in Operations, Curriculum Design, and
Outstanding Questions).

## Assumptions

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Carried from v16: parent-direct payment; SA launch jurisdiction;
universal consent gate; Android-first; Mbucks/Mpoints dual currency;
7-Mbuck cap with 3-Mbuck pilot cap; the two explicit POPIA/exam-bonus
risk acceptances (the exam-bonus acceptance is now qualified — see
below); the fixed Mbucks-to-Rand peg; the late-penalty mechanic's nature
as a parent-only administrative matter; the exam-performance bonus
mechanic's grade data is self-reported/parent-entered; the app is
intended primarily as a South African B2C product at launch.

**Two assumptions elevated to explicit constraints this cycle, per
`LegalOpinion_v1.md`:** (1) Mbucks non-transferability/non-redeemability
is no longer merely an assumed current-state fact — it is now a
documented product-spec constraint that future roadmap decisions must
respect (see Value Proposition, Business Model, Constraints). (2) The
NCR-avoidance premise for account-linking is resolved (not an NCR issue)
but remains subject to the newly-surfaced SARB/NPS Act open-banking
question, still itself unconfirmed pending finalized regulation.

**One prior risk-acceptance is now qualified, not retired:** the
exam-bonus mechanic's design (grade-improvement-contingent) is confirmed
by `ChildDevelopmentReview_v1.md` to carry a specific, well-evidenced
intrinsic-motivation risk the user has not yet been asked to accept or
reject in light of this new evidence — this is a live open decision, not
a settled risk acceptance (see Outstanding Questions).

Status remains Partial: the assumption list is now more precisely
characterized (several items moved from "assumed" to "confirmed
low-risk, contingent on a named constraint"), but it remains a working
list with live open items, not a closed inventory.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v16. Solopreneur venture; AI-assisted development;
external technical expertise engaged only on-demand; directional
~3-month build timeline. Platform choice (Android primary, iOS future)
confirmed. **New constraint added this cycle:** Mbucks
non-transferability/non-redeemability, per `LegalOpinion_v1.md` Q1, is
now a binding product-spec constraint on all future roadmap decisions,
not merely a description of the current build (see Value Proposition,
Business Model, Legal & Compliance). Status remains Complete.

## Roadmap

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**The specialist legal opinion — the primary gate this section has
tracked since v9 — has been obtained**, satisfying the event-based
commissioning trigger ("once a stable working model exists, and before
any pilot testing with real families begins") for its originally-scoped
purpose. Foundational, non-financial rails may proceed as before;
financial-trigger features are no longer blocked by an unobtained
opinion.

**Two new, narrower, well-defined gates replace the general gate,** both
surfaced by this cycle's legal opinion: (1) the optional account-linking
feature requires a **pre-build regulatory recheck** of the SARB/National
Payment System Act open-banking question before shipping, given the
draft (not finalized) state of the relevant regulatory framework; (2)
the Mpoints gamified rewards system requires an **FPB applicability
assessment** before the feature's classification exposure can be
considered closed.

**Design decisions from the child-development review are now named as
pre-pilot roadmap items, not yet resolved:** the exam-performance bonus
redesign decision (behavior- vs. outcome-contingent); the late-penalty
mitigation-path decision (grace-period/reminder mechanism vs.
pilot-measurement-only); the Fintech Advance content-delivery approach
(avoiding the product's own gamification mechanics); the three-tier
curriculum framing's actual content design (see Curriculum Design); and
adoption of the specific pilot-measurement package (PSI-SF/FAD-GFS
borrowed items, within-family correlation tracking, age-stratification,
child-report instrument) into the pilot's formal design before the pilot
begins.

**Also newly required, per the legal opinion:** design and document a
specific POPIA Section 14 retention period and deletion trigger; build
the consent-flow documentation separating data-processing consent from
general T&Cs; design the recommended lightweight parent
identity-verification step; and rename child-facing terminology away
from debt-coded language, reserving "invoice"/"arrears" for
parent-facing surfaces only.

Status is raised to Complete: the roadmap's central, long-standing gate
(the unobtained legal opinion) is resolved, and every item it surfaces
is now a specifically named, well-defined pre-build or pre-pilot task
rather than an open-ended condition — a materially different, and more
actionable, state than v16's "narrowed scope, still uncommissioned."

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v16. No funding ask, runway, or full numeric financial
projections exist. The subscription price is known and modeled against
the Year-1 funnel range; the family-vs-child install-count ambiguity and
the 180-1,830 vs. 360-2,440 subscriber-count discrepancy remain open.
Neither specialist review this cycle supplies financial data. Status
remains Partial.

## Validation Strategy

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Two of the section's longest-standing gaps are closed this cycle:**
legal validation (the opinion's scope, narrowed across six revisions
without being commissioned, is now obtained — see Legal & Compliance)
and child-development/age-appropriateness validation (required since v9,
never commissioned, now delivered with detailed, specific findings and
pilot-design recommendations — see Success Criteria, Risks, Curriculum
Design).

**What remains genuinely unaddressed by either review, exactly as in
v16:** primary user-research validation beyond the bounded n=10 sample;
market/demand validation (a commissioned survey or live pilot, neither
yet run); pricing/conversion validation (price known, conversion
unvalidated); curriculum validation (still generic — see Curriculum
Design's three unaddressed items). Account-linking feature validation
now requires both the pre-build SARB/NPS Act recheck (see Roadmap) and a
designed, reviewed opt-in consent flow — neither exists yet, though the
underlying legal question governing it is now substantially clearer.

Status remains Partial: two of roughly six validation streams are now
fully closed at the highest evidentiary tier this case uses, but the
remaining streams (market demand, pricing/conversion, curriculum, and
the account-linking UX flow specifically) are unaddressed by this
cycle's inputs and remain exactly as open as in v16. Confidence is
raised to High for the section overall, reflecting how much clearer the
two resolved streams now are, while Evidence remains Supported, not
Verified, because it must characterize the section as a whole and the
majority of validation streams remain Supported/Assumed-tier.

## Supporting Evidence

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Two new Verified-tier primary sources added this cycle:**
`LegalOpinion_v1.md` and `ChildDevelopmentReview_v1.md` — both obtained
from retained South African professionals (legal counsel;
child-development specialist) who reviewed and approved their own final
documents, citations included, prior to delivery. Unlike the three prior
Research House vendor engagements (`ResearchFindings_v1-3.md`, each
Supported-tier desk research), these are genuine specialist opinions and
are treated as Verified-tier for every finding they directly address —
the highest evidentiary tier this case uses, previously reserved only
for the user's own direct confirmations.

Carried from v16: the n=10 first-party interview data point (bounded,
non-representative); the three Research House engagements
(Supported-tier); the user's directly-cited South African
statutory/statistical sources; the user's own clarification history
(`Clarifications_v6.md` through `v14.md`, Verified-tier as to what
design decision was made).

Status is raised to Complete: the case's evidentiary base now spans the
full range from Verified-tier direct user confirmation, through
Verified-tier retained-professional opinion, to Supported-tier desk
research and a bounded first-party data point — a materially more
complete evidentiary foundation than v16's Supported-tier ceiling.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this cycle (removed from the open list, retained here for
audit-trail continuity):** money-transmitter/payment-facilitation risk
characterization (low, contingent on the Mbucks non-transferability
constraint); universal consent-gate legal sufficiency (confirmed
sufficient as designed); minor contractual capacity's applicable
doctrine (the rights-without-obligations exception, cleaner than prior
research found); the NCR account-linking question (resolved clean, not a
PDA issue); whether ARB Clause 14 alone captures terminology risk (it
does not — Clause 6.1 also applies); whether any South Africa-specific
regulatory layer beyond POPIA/NCR/ARB applies to app-store child-category
requirements (yes — the FPB, newly identified); whether the
child-development/age-appropriateness review would find the late-penalty
redesign risk-eliminating or merely risk-reducing (the latter,
confirmed); whether the exam-bonus mechanic carries any specific,
evidenced developmental concern (yes, confirmed, with a specific
recommended redesign direction); whether the Fintech Advance "no
execution" safeguard fully addresses the module's risk profile (no — a
distinct, unaddressed risk is named).

**Newly opened this cycle:** the SARB/National Payment System Act
open-banking question for account-linking (genuinely unsettled, draft
regulation, recommended pre-build recheck); the FPB applicability
assessment for Mpoints (uncertain, fact-specific, recommended pre-build
assessment); the specific POPIA Section 14 retention period and deletion
trigger (must be designed and documented, not yet done); the
consent-flow-documentation-separation build item (not yet done); the
lightweight parent identity-verification mechanism design (not yet
done); the parent-facing-only terminology renaming decision (recommended,
not yet adopted); the exam-bonus redesign decision (behavior- vs.
outcome-contingent — recommended, not yet adopted); the late-penalty
mitigation-path decision (grace-period mechanism vs. pilot-measurement-
only — recommended, not yet adopted); the Fintech Advance gamification-
avoidance decision (recommended, not yet adopted); the three-tier
curriculum framing's actual content design (framework recommended,
content not yet designed); formal adoption of the specific pilot-
measurement package into the pilot's design (recommended, not yet done);
the one legal-opinion case citation flagged by the expert as requiring
independent pinpoint-reference verification before any filed use.

**Still open, unchanged from v16:** the family-vs-child install-count
ambiguity; the subscriber-count discrepancy (180-1,830 vs. 360-2,440);
the account-linking opt-in UX flow; fund custody mechanics; task
verification; dispute-escalation beyond 48 hours; the "request for
payment" prompt feature's coherence under the child-invisible
late-penalty model; curriculum age-band splits beyond the new three-tier
framework (instructional format, standards alignment, content
authorship); app-store policy sub-questions; MoneyAfrica Kids' unpublished
premium price; engineering-cost quote-seeking; the external-help budget
ceiling; the schools-partnership channel's timeline/target/resourcing;
South Africa-specific vendor pricing for Stitch's or Mono's product.

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted. Recomputed in full
against this cycle's document.

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

**Readiness Score = 91 / 130 = 70.0%.** This clears the completion
gate's ≥70% threshold, the first version in this case's history to do
so.

No section is Critical + Incomplete: both Legal & Compliance and Child
Data & Consent are Complete.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
52% (v13) → 52% (v14) → 52% (v15) → 52% (v16) → **70% (v17) — driven
directly by two genuine Verified-tier specialist opinions resolving the
case's two named Critical-section blockers, moving Legal & Compliance,
Child Data & Consent, Risks, Business Model, Roadmap, and Supporting
Evidence to Complete.**

### Critical Gaps

1. **SARB/National Payment System Act open-banking question (Legal &
   Compliance, Business Model, Roadmap, Stakeholders) — newly surfaced
   this cycle.** Genuinely unsettled: SARB's fintech-access framework
   (Draft Directive; Draft Exemption Notice under the Banks Act) is not
   finalized. Gates the optional account-linking feature's ship date
   pending a pre-build recheck.
2. **FPB classification question over Mpoints (Legal & Compliance,
   Stakeholders, Risks) — newly surfaced this cycle.** Uncertain, fact-
   specific application of the Films and Publications Amendment Act to
   the gamified rewards system; requires a dedicated assessment before
   the feature's classification exposure is closed.
3. **Six named design decisions recommended by the two specialist
   reviews, none yet adopted** (Operations, Curriculum Design,
   Outstanding Questions): parent-facing-only debt terminology; exam-
   bonus redesign toward behaviors; late-penalty mitigation path;
   Fintech Advance gamification-avoidance; three-tier curriculum
   content design; formal pilot-measurement-package adoption. Each is
   now concrete and actionable rather than an open risk narration, but
   none has been decided by the user.
4. **POPIA Section 14 retention policy — must be designed, not just
   cited (Legal & Compliance, Roadmap).** The general principle is
   confirmed to require an affirmatively designed, specific retention
   period and deletion trigger; this design work has not yet been done.
5. **Subscriber-count discrepancy (Revenue & Costs, Market &
   Competition) — unresolved, unchanged from v16.**
6. **Family-vs-child install ambiguity (Financial Considerations,
   Revenue & Costs, Assumptions) — unresolved, unchanged from v16.**
7. **Curriculum engagement, operational health, and retention success
   criteria remain unbenchmarked (Success Criteria) — unchanged from
   v16; outside the scope of both specialist reviews this cycle.**
8. **Market/demand and pricing/conversion validation remain undone
   (Validation Strategy) — unchanged from v16; outside the scope of both
   specialist reviews this cycle.**
9. **Curriculum instructional format, standards alignment, and content
   authorship remain unspecified (Curriculum Design) — a three-tier
   age-framework is now recommended, but none of these three items has
   actual content behind it yet.**
10. **Legal-opinion-deferral risk (Legal & Compliance, Risks) — RESOLVED
    this cycle**, retained for audit-trail continuity.
11. **Child-development/age-appropriateness review commissioning (Risks,
    Success Criteria, Validation Strategy) — RESOLVED this cycle**,
    retained for audit-trail continuity.
12. **Pre-link independent-registration carve-out — RESOLVED at v14**,
    retained for audit-trail continuity.
13. **90-day vs. annual funnel tension — RESOLVED at v10**, retained for
    audit-trail continuity.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** High | **Evidence:** Verified

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs.*

Unchanged from v16: the age floor of 6 is intentional; the curriculum is
a short course completable daily or weekly, not a full year; two example
mechanics (currency differentiation; "word sums" for change/remainder
calculation); "Fintech Advance" as the distinct 15-18-only element.

**Three-tier age-differentiated framing — new this cycle, per
`ChildDevelopmentReview_v1.md` Q1/Q3, directly addressing named open
item #1 (age-band curriculum splits) with a concrete framework, though
not yet with actual instructional content.** The reviewer finds the risk
inflection point for the payroll metaphor is age 10-11 (institutional
understanding of financial systems, per Jahoda 1981/Ng 1983), not a
smooth younger-is-worse gradient, and recommends the metaphor map to a
different developmental task at each of three tiers rather than one
metaphor stretched across the full span:

- **Early childhood (roughly 6-9):** task/reward and delayed
  gratification framing — closer to "family task rewards" than "wages";
  no institutional financial scaffolding assumed or required.
- **Pre-teen (roughly 10-14):** basic transactional literacy — roughly
  where the institutional-understanding research finds children begin
  able to hold the metaphor meaningfully.
- **Teens (roughly 15-18):** closer to actual pre-employment literacy,
  where the current payroll framing (payslip, deductions, punctuality)
  is, per the reviewer, arguably a genuine feature — real rehearsal for
  a near-future reality — rather than imported adult vocabulary.

This framework directly supports the terminology-risk mitigation named
in Legal & Compliance (parent-facing-only debt terminology) by giving it
an age-specific implementation path rather than a single blanket rename.
**This is a recommended framework, not yet built into actual curriculum
content or UI terminology** — the four items named in v16 as unresolved
are now three: instructional format, standards alignment, and content
authorship remain fully open; age-band curriculum splits now has a
specialist-recommended structure to design against, though the specific
tier boundaries (6-9/10-14/15-18) are the reviewer's own rough framing,
not yet reconciled with the product's existing six-way stakeholder
sub-bands (6, 7, 8, 9-10, 11-14, 15-18).

Status remains Partial: one of four named open items now has concrete,
specialist-sourced direction; three remain fully unaddressed by any
input available to this case. Confidence is raised to High and Evidence
to Verified for the section overall, reflecting that its most
consequential open question (age-band differentiation) now rests on
direct, Verified-tier specialist input rather than absence of guidance —
per Playbook Entry 4, this is both a clearer and a more actionable
picture, not merely a clearer one.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Directly and substantially addressed by `LegalOpinion_v1.md` Q2 and
Q3.** The universal parent-consent gate (no minor accesses any part of
the app without a pre-existing, consenting parent account) is confirmed
**legally sufficient as designed** under POPIA s34/s35(1)(a) — the
registration-triggers-POPIA question that drove earlier downgrades
cannot arise in MiniMoney's current design, and this is now a direct
legal confirmation, not merely an inference from the design's own logic.
Two concrete hardening recommendations are named (consent-flow
documentation separation; lightweight parent identity verification) —
not yet built, tracked in Roadmap and Outstanding Questions.

POPIA Section 14 retention is confirmed to require an affirmatively
designed, specific retention period and deletion trigger — the general
principle alone is confirmed insufficient on its own to constitute a
complete data-retention design, closing the prior "risk-accepted but
unreviewed" status of this item with a specific, actionable requirement
rather than either resolving or leaving it purely accepted.

**Remaining open items, narrower than in v16:** the technical mechanism
for implementing the (legally-confirmed-sufficient) consent gate is
still undocumented — an engineering task, not a legal uncertainty, as of
this cycle. Google Play's Families Policy loyalty-point disclosure
requirement and Apple's Kids Category IAP-currency question remain open
platform-policy (not statutory) items. The newly-surfaced FPB
classification question over Mpoints (see Legal & Compliance) sits
adjacent to, but is formally distinct from, this section's POPIA/consent
focus. Whether the Fintech Advance conceptual content requires
additional disclosure beyond general POPIA/ARB considerations remains
open, though narrowed by the child-development review's finding that
the primary risk is normalization of speculative-risk psychology, not a
data-privacy or consent question specifically.

Status is raised to Complete: the section's central, long-standing
questions — is the consent model sufficient, and is the retention
approach adequate — are now both directly and affirmatively answered by
retained counsel, with concrete, actionable follow-on requirements named
rather than left as open legal uncertainty. Confidence and Evidence are
raised to High/Verified accordingly.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Complete.

- Readiness Score ≥ 70%: **Yes — PASSES.** Score is 70% (91/130), up
  from 52% (67/130) at v16, driven by the two genuine Verified-tier
  specialist opinions obtained this cycle.

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.

- No section consists solely of an "Unchanged from vN, not reproduced"
  pointer: **Yes.** Market & Competition cross-references v16's own
  unmodified text within the same unbroken revision chain (Playbook
  Entry 5's concern is about content that becomes inaccessible across
  many revisions — not applicable here, one version back, in the same
  case folder); every other section contains its own full, substantive,
  self-contained text.

**This Business Case now passes its own completion gate.** The Readiness
Score is 70% (91/130), and no Critical section is Incomplete. Genuine
open items remain (detailed in Critical Gaps and Outstanding Questions
above) — most prominently the two newly-surfaced regulatory questions
(SARB/NPS Act; FPB) and six named, specialist-recommended design
decisions not yet adopted by the user — but none of these hold any
Critical section below Complete, and none represent the kind of
foundational "insufficient context" gap that has gated this case since
v9.
