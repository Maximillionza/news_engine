# Business Case: MiniMoney — v9

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v8.md` (prior version, produced
> by the Incubator), `Verdict.md` (Investment Committee verdict on v8:
> "Sufficient context — Proceed with changes," six required changes,
> each cited to a specific section, 2026-07-08). This document is
> self-certified against the Incubator completion gate.

> **Changes from v8 — summary of what the Incubator is addressing this
> revision:** the Investment Committee returned v8 with a verdict of
> "proceed with changes," not "insufficient context" and not "do not
> proceed." Six required changes were specified, each tied to named
> sections. This revision addresses all six directly, section by
> section, below. Per standing instruction and the delegation task for
> this cycle, where a required change depends on a real decision or fact
> the user has not yet supplied (a specific subscription price point; a
> resolution of the 90-day-vs-annual-target tension; a firm
> trigger/deadline date for the legal opinion), the Incubator does
> **not** invent a resolution. Instead it does the analytical work that
> *can* be done without inventing facts — clarifying structure,
> reconciling existing figures, naming the decision explicitly, bounding
> evidentiary weight — and flags plainly what still requires the user's
> own input. This means several sections gain real rigor this revision
> without changing Status, because the underlying open questions are, in
> most cases, genuinely still open pending a user decision, not an
> Incubator judgment call.

> **Also this revision:** per the delegation task, `ExpertRoster.md` and
> `reviews/DevilsAdvocate.md` are regenerated from scratch with genuine
> rigor — not carried forward — because the Investment Committee's Gate
> Integrity Check flagged that it could not verify either document's
> substantive content from its isolated vantage, and asked that a later
> audit be able to confirm they are substantively done, not superficially
> present.

## What Changed in v9 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Six Investment Committee-required changes, each addressed below in its
cited section:

1. **Legal & Compliance sequencing tightened.** A feature-level gating
   plan is now explicit: which build components may proceed in parallel
   (non-financial rails) versus which are locked behind the specialist
   legal opinion (financial-trigger features). The Incubator also
   formally adopts the Investment Committee's suggestion of a short,
   low-cost preliminary legal read on the two highest-stakes questions
   as a recommended next step, distinct from the full opinion. **What
   remains open:** a firm trigger/deadline date — this requires a user
   decision the Incubator cannot supply on the user's behalf.

2. **Subscription price point — still requires user input.** The
   Incubator does not invent a figure. This is now elevated from a
   background Outstanding Question to a named pre-Developing-Committee
   requirement, with the existing anchor (MoneyTime SA R995/year,
   flagged as an under-anchor) restated as the only current reference
   point.

3. **90-day vs. annual funnel tension — options clarified, not
   resolved.** The Incubator computes exactly what a linear-pace 90-day
   figure would be against the annual range's low end (≈4,400-4,500
   installs) versus the stated 15,000 target, making the size of the gap
   explicit. The choice between stating a front-loaded marketing
   assumption or revising the 90-day target remains the user's to make.

4. **Build timeline vs. engineering-cost range — reconciled
   analytically.** The Incubator explains why a solopreneur/AI-assisted
   build and a $25,000-$120,000+ agency-quote range are not directly
   contradictory (different production models), while flagging that no
   user-supplied budget ceiling exists for the "external expertise
   on-demand" line — so the two figures are reconciled in *kind*, not in
   *amount*.

5. **Late-penalty mechanic — child-development review now explicitly
   required.** A distinct risk category is named (previously folded into
   generic trust/enforcement risk), a new Success Criteria item is added
   (family-relationship-strain tracking by child age band), and Validation
   Strategy now names a child-development/age-appropriateness expert
   review as a required, not optional, pre-pilot step.

6. **n=10 interview evidence — bounded explicitly.** The Incubator adds
   an explicit instruction, carried into Supporting Evidence and Problem,
   that this data point must not be used as if representative in any
   future financial or go/no-go modeling until either its methodology is
   documented retroactively or it is superseded by the planned pilot or a
   structured survey.

No section's Status, Confidence, or Evidence tag changes as a direct
result of these six items, because in every case the underlying gap
depends on a user decision or a real-world action (commissioning a
review, running a documented survey) that has not yet occurred — the
Incubator has done the analytical work possible without inventing that
missing input. The Readiness Score is therefore **unchanged from v8: 47%
(61/130)**. This is stated plainly rather than dressed up: addressing the
Investment Committee's six items has made this case's remaining gaps
sharper and more actionable, not fewer.

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6-18), launching first in South Africa on **Android** (iOS porting
planned as future work), combining gamified task assignment with a
simulated payroll system. The parent submits a **budget** setting the
minor's "basic income"; tasks earn **Mbucks** (a real-money-pegged
in-app currency, e.g. 10 Mbucks = R10) which accumulate into a
"payslip," while every completed task separately earns a fixed 10
**Mpoints** — a distinct, non-monetary cosmetic-store currency. The
parent receives an invoice and pays the owed amount directly to the
child via the parent's own banking app — **MiniMoney itself never
holds, transmits, or takes custody of funds**. Monetization is
subscription-only at launch, with advertising deferred to a possible
post-launch V2. Real-money in-app purchases remain parent-only; a minor
cannot access any part of the app without a pre-existing, consenting
parent account.

This revision responds to the Investment Committee's "proceed with
changes" verdict on v8, addressing all six required changes. None of the
six is a hard blocker on its own, and none has been resolved by
inventing information the user has not supplied — each is either
structurally tightened (legal-opinion sequencing, now with an explicit
feature-level gate and a recommended low-cost preliminary read),
analytically reconciled (build timeline vs. engineering-cost range),
newly required as a distinct action (child-development review of the
late-penalty mechanic), more precisely bounded (the n=10 interview
evidence), or explicitly named as still requiring a user decision
(subscription price point; the 90-day-vs-annual-target tension). The
Readiness Score is unchanged at 47% (61/130) — this revision increases
the case's rigor and traceability, not its measured completeness, since
the underlying open questions the Investment Committee flagged are, in
five of six cases, genuinely dependent on decisions or actions the
Incubator cannot make on the user's behalf. The Legal & Compliance
Critical gap remains open by the user's own prior, deliberate deferral
decision (unchanged from v8), now with a materially clearer plan for
what may proceed in parallel and what may not.

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
personal-device ownership by age 10).

**This revision — the n=10 interview finding is bounded explicitly, per
Investment Committee requirement #6.** The finding stands as reported: 6
of 10 families interviewed confirmed interest in using the app and
stated willingness to pay for it; 7 of 10 expressed interest specifically
in the education aspect. The Incubator's treatment of this evidence does
not change in substance from v8 — it remains genuine, first-party,
MiniMoney-specific evidence, categorically different from
comparable-market inference, but not statistically significant, with
sampling method, recruitment channel, family-selection criteria, and
exact question wording all unknown. **What changes this revision is an
explicit, standing instruction, carried into every downstream use of this
data point:** it must not be used, in this or any future version, as if
it were a representative or validated demand signal — in funnel modeling,
in Financial Considerations, in Objectives, or anywhere else — until
either (a) its methodology is documented retroactively (recruitment
channel, sampling frame, exact question wording), or (b) it is superseded
by the already-planned 20-50 family pilot or a structured survey. This
instruction exists precisely because a directional, encouraging n=10
result can otherwise quietly accumulate more evidentiary weight across
successive versions than it warrants — a risk the Investment Committee
named specifically. Status remains Partial for the same reason as v8:
this is a real, encouraging, directional signal, not an established
finding that parents broadly perceive this as a problem worth paying to
solve.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in substance from v8: if financial literacy for minors is an
underserved niche, MiniMoney's differentiator is the payroll-simulation
mechanic rather than a simple debit-card-for-kids model, framed as an
edtech app with a payroll-simulation UX. No direct South African
incumbent does what MiniMoney does. `ResearchFindings_v1.md` Item 5
(carried from v7) adds a directional data point: MoneyAfrica Kids shows
modest download volumes, while MoneyTime SA claims a larger,
self-published B2B2C-mediated reach (130,000 students via schools) —
together suggesting real but unproven consumer appetite, with the
strongest demonstrated reach coming via a schools-distribution model.
The distribution-model clarification from v8 (schools partnership as an
intended, parallel channel, not a rejected alternative) carries forward
unchanged. This revision does not add new Opportunity content — none of
the six Investment Committee items is cited to this section directly,
though the schools-partnership timeline gap (named in Outstanding
Questions) remains an open item feeding into the same underlying
distribution-dependency risk the Investment Committee flagged.

## Objectives

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The functional objective (budget → tasks → Mbuck/Mpoint earning → exam
bonus → invoice/payslip → payment confirmation with escalating
late-penalty → age-gated education) is unchanged from v8.

**This revision — Investment Committee requirement #3, the 90-day vs.
annual target tension, clarified with explicit arithmetic rather than
merely re-described:**

- Against the annual range's **low end** (18,000 installs/year), a
  strictly linear pace across the first 90 days of a 365-day year would
  imply 90/365 × 18,000 ≈ **4,438 installs** — not 15,000. The
  user-committed 90-day target of 15,000 is roughly **3.4x** a
  linear-pace reading of the annual range's low end.
- Against the **high end** (61,000), a linear pace across 90 days implies
  90/365 × 61,000 ≈ **15,041 installs** — the stated 15,000 target is
  almost exactly consistent with this reading.
- **The gap is therefore precise, not vague:** the 15,000-in-90-days
  target is only internally consistent with the annual funnel model if
  the business is effectively targeting the **top of its own modeled
  range**, or if a front-loaded launch-marketing push (not stated
  anywhere in this case) is assumed to concentrate a disproportionate
  share of Year-1 installs into the launch window.
- **This remains the user's decision to make, not the Incubator's to
  invent:** either (a) state explicitly what the front-loaded
  launch-marketing assumption is (paid acquisition spend, an app-store
  feature placement, a PR push, or some combination), or (b) revise the
  90-day target downward to track the funnel's low end more
  consistently (candidate figure, if resolved this way: roughly
  4,000-5,000 rather than 15,000). The Incubator states both paths
  precisely so the decision, when made, can be made against clear
  numbers — but does not select between them.

Pre-launch and Growth-phase objectives are otherwise unchanged from v8.
Status remains Partial: the tension is now precisely quantified rather
than only qualitatively flagged, but it is not resolved, per Investment
Committee requirement #3's own framing ("must be resolved, not
described") — the Incubator has done everything short of resolution that
does not require inventing the user's decision.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8: pilot success (majority of families complete ≥4
consecutive weekly cycles), curriculum engagement (30%, no external
benchmark), operational health (65% task-completion without dispute, no
external benchmark), Freemium/subscription conversion (2%, correctly
benchmarked against the 1-3% subscription-only range), retention (no
figure proposed).

**New this revision — Investment Committee requirement #5, a
family-relationship-strain success criterion:** the planned 20-50 family
pilot's success criteria must be expanded beyond completion-rate metrics
to explicitly track relationship-strain indicators segmented **by child
age band**, since the escalating late-penalty mechanic (5→6→7
Mbucks/week, pilot cap 3) plausibly lands very differently on a 6-year-old
than a 17-year-old. Candidate metrics, none yet adopted or measured:
parent-reported friction/conflict incidents tied to late-penalty
application; dispute frequency segmented by child age band rather than
pooled; pause/opt-out rate by age band; a simple pre/post parent-reported
household-stress indicator specific to the payslip/penalty mechanic. No
such metric currently exists in any version of this case — this is a new
requirement, not a refinement of an existing one, and it stands until the
pilot design formally incorporates it. Status remains Partial: the
conversion-benchmark ambiguity remains resolved from v8, but curriculum
engagement, operational health, and retention remain unbenchmarked, and
the newly-required relationship-strain criterion does not yet exist in
any concrete, measurable form.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8: children/teens (6-18, sub-banded), parents/guardians,
the app operator, the South African Information Regulator (POPIA) and
the Advertising Regulatory Board (ARB), three named competitors, and
Apple/Google as app-store platform stakeholders. None of the six
Investment Committee items is cited to this section directly, though
requirement #5 implicitly strengthens the case for treating a
child-development/age-appropriateness reviewer as a stakeholder-adjacent
expert voice this venture has not yet consulted (see `ExpertRoster.md`).
The parent's bank as an external rail remains unaddressed.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8: children/teens 6-18 (sub-banded) and their parents,
South Africa, Android-first. Not cited by any of the six Investment
Committee items directly.

## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household tasks into a
structured payroll-like experience with a built-in financial literacy
curriculum. For children: a "real job" simulation paid out via the
parent's own bank transfer, tied to age-appropriate lessons, alongside a
separate cosmetic-reward system (Mpoints). The free/subscription feature
split is unchanged from v8.

**This revision — Investment Committee requirement #2, addressed as
thoroughly as possible without inventing a figure:** the Business Case
still does not contain a specific MiniMoney subscription price point.
MoneyTime SA's R995/year (25% sibling discount) remains the only South
African price anchor available anywhere in this case, and it is flagged
again, as in every prior version, as a likely under-anchor given
MoneyTime SA is described as a lighter-weight product. The Investment
Committee's own framing was explicit: a price point "even as a stated
range with rationale" is required before this section — and Business
Model and Financial Considerations, which depend on it — can be treated
as modelable. Per the standing no-invention rule and this cycle's
explicit delegation instruction, the Incubator does not supply that
range on the user's behalf: doing so would mean presenting a fabricated
business decision as though it were the user's own. This is now named
plainly as the single most direct blocker to modeling this venture's
actual unit economics, and is carried into Outstanding Questions as a
named, elevated pre-Developing-Committee requirement rather than a
background open item.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8. Not cited by any of the six Investment Committee
items directly, though the underlying funnel figures (18,000-61,000
Year-1 installs) are the same figures used in the Objectives
reconciliation above.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Structurally confirmed and monetization-resolved (subscription-only at
launch, ads deferred to V2), unchanged from v8.

**This revision:** the same subscription-price-point gap named in Value
Proposition applies directly here — "how the business actually makes and
reports money" cannot be fully modeled without a price point, per
Investment Committee requirement #2. The Mpoints/Apple IAP-currency
question remains unresolved, unchanged from v8. Status remains Partial
for the same reasons as v8, now with the price-point gap stated as an
explicit pre-Developing-Committee requirement rather than a standing
background question.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This revision — Investment Committee requirement #4, the build-timeline
vs. engineering-cost reconciliation, addressed analytically:**

The engineering-cost range carried since early versions of this case
($25,000-$40,000 MVP; $60,000-$120,000+ full build) was explicitly
sourced from **five converging agency-quote estimates** — i.e., the cost
of a professional development team or agency building this product from
a standing start, billed at market development rates. The company-side
Constraints information supplied in v8 (solopreneur venture, AI-assisted
"vibe coding" development, external expertise engaged only on-demand, a
directional ~3-month timeline) describes a **structurally different
production model**, not a faster version of the same one: founder labor
and AI-assisted tooling substitute for the bulk of the labor cost that
the agency-quote figures were pricing, with paid external help presumably
reserved for scoped, harder problems the founder cannot resolve alone
(the specialist legal opinion itself is one clear example, already
costed separately at R25,000-R80,000).

**Why this reconciles the two figures in kind, but not in amount:** it is
entirely plausible for a solopreneur AI-assisted build to cost a small
fraction of $25,000-$120,000+ in direct cash outlay, while still taking
roughly the stated 3 months of founder time — the two figures are not
measuring the same thing (agency-priced labor cost vs. founder-time
timeline), so their apparent tension is partly an artifact of comparing
incompatible measures rather than a genuine contradiction. **What is
still missing, and cannot be supplied without the user:** no budget
ceiling has been stated for the "external expertise on-demand" line
itself. Without that figure, it is impossible to say how much of the
original $25,000-$120,000+ agency range this approach actually displaces
versus how much it merely defers into future ad hoc engagements (e.g., if
the AI-assisted build stalls on a hard technical problem, or if App Store
review issues require paid specialist help). This is named as a
still-open Outstanding Question, not resolved by this reconciliation.

CAC and curriculum-production cost remain unresolved, unchanged from v8.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Unchanged from v8 in mechanical description — already Complete. **This
revision adds a cross-reference, not new mechanical content:** the
escalating late-penalty system (5→6→7 Mbucks/week, pilot cap 3),
enforced entirely on honor-system reporting, is fully and consistently
described here, but per Investment Committee requirement #5, its
soundness as a design choice from a child-development standpoint remains
an open question tracked in Risks and Validation Strategy, not in this
section — Operations' Complete status describes mechanical clarity, not
the mechanic's psychological appropriateness.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8. Not cited by any of the six Investment Committee items
directly.

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This section remains flagged Critical.** Carried forward unchanged
from v8: MiniMoney does not hold, move, or take custody of funds; SA
launch jurisdiction under POPIA; universal consent gate; POPIA Section
34, ARB Clause 14, POPIA Section 14 (retention), absence of ARB/NCR
precedent for "payslip"/"invoice"/"late penalty" terminology applied to
minors; the user's explicit, deliberate decision to defer the specialist
POPIA/ARB legal opinion to the build-spec stage, post-Investment-
Committee; the two explicit user risk-accepted assumptions (POPIA Section
14 retention sufficiency; exam-bonus mechanic's schools-data-privacy
status).

**New this revision — Investment Committee requirement #1, addressed in
full to the extent the Incubator can without inventing a user decision:**

1. **Feature-level gating plan, now explicit rather than implied.** The
   Investment Committee required that the specialist opinion gate
   specific financial-trigger features, not the whole build. The
   Incubator specifies this plan as follows, drawn directly from the
   mechanics already described in Operations and Technology:

   - **Gated behind the specialist opinion — must not ship to real users
     without sign-off:** invoice generation and the parent-billing
     trigger; the real bank-payment confirmation workflow; the
     late-penalty/arrears calculation and enforcement mechanism; the
     data-retention/deletion pipeline implementing POPIA Section 14.
     These are precisely the mechanics that carry the
     money-transmitter-characterization risk and the
     terminology-to-minors risk the legal opinion is meant to resolve.

   - **May proceed in parallel, unblocked by the legal opinion:** the UI
     shell and navigation; the task-assignment engine (task creation,
     assignment, and completion tracking, independent of financial
     consequence); curriculum content authoring and delivery; the
     budget-setting input capture (as data entry, prior to any live
     financial trigger); account creation and the consent-gate
     scaffolding itself (as a UX flow, distinct from the legal adequacy
     of the consent it captures).

   This split is the Incubator's own structural inference from the
   mechanics already documented elsewhere in this case — it does not
   require, and does not supply, any new fact from the user.

2. **A firm trigger/deadline — still requires a user decision, named
   explicitly as such.** The Investment Committee required "a firm
   trigger/deadline for commissioning" the opinion. The Incubator cannot
   supply a specific date or milestone on the user's behalf without
   inventing it. This is named plainly here as the one part of
   requirement #1 that remains genuinely open, carried into Outstanding
   Questions as an elevated, named item: what event or date triggers
   commissioning (e.g., "when the build reaches the invoice/payment
   module," "within 30 days of build-spec kickoff," a fixed calendar
   date)? Absent an answer, the legal-opinion-deferral risk named in v7
   and v8 (a Critical-tagged section closed by a plan that could itself
   slip indefinitely) is unchanged in substance, only better-structured
   around it.

3. **A short, low-cost preliminary legal read — the Incubator formally
   adopts the Investment Committee's suggestion as its own
   recommendation.** Rather than the full specialist opinion (scoped at
   R25,000-R80,000, per Research House's inference in v7), the Incubator
   recommends the user consider commissioning a narrower, cheaper
   preliminary read addressing exactly two questions before any further
   version of this case: (a) whether the invoice/payment-trigger
   mechanic is likely to be characterized as money-transmission-adjacent
   under South African law, and (b) whether "payslip"/"invoice"/"late
   penalty"/"arrears" terminology applied to minors carries any
   identifiable regulatory or advertising-standards risk. This is
   presented as a recommendation the Incubator judges sound, not as a
   decision already made — whether the user adopts it, and on what
   timeline, remains open.

The underlying legal uncertainty itself (money-transmitter
characterization; terminology-to-minors risk; POPIA sufficiency) is
unchanged by any of the above — only the sequencing plan around it has
been sharpened, exactly as the Investment Committee asked.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Carried forward unchanged from v8: regulatory risk (Critical, now
sequenced via the gating plan above but not reduced); child-safety/
data-privacy risk (Critical, partly risk-accepted); trust/enforcement
risk; dispute-escalation risk; terminology/perception risk;
advertising/child-data risk (reduced near-term relevance); Fintech
Advance content risk; competitive risk; monetization-execution risk
(narrowed to price-point selection only); app-store policy risk;
platform-concentration risk; adoption/forecasting risk; engineering-cost
estimation risk; legal-opinion-deferral risk.

**New this revision — Investment Committee requirement #5, a distinct
named risk category:** **child-development/age-appropriateness risk.**
In every prior version of this case, the escalating late-penalty
mechanic (5→6→7 Mbucks/week, pilot cap 3, honor-system enforced) was
assessed only through a trust/enforcement/dispute lens — whether families
would report honestly and whether disputes would be resolved fairly.
That framing does not address a distinct question: whether an escalating,
real-money-denominated penalty is an age-appropriate mechanic at all
across a 12-year span (age 6 to age 18), or whether it risks introducing
financial-anxiety or family-conflict dynamics disproportionate to its
behavioral-nudge intent, particularly at the younger end of the age
range. No version of this case has had this mechanic reviewed by anyone
with child-development or educational-psychology expertise. This risk is
named here explicitly, as its own category, per the Investment
Committee's requirement — see Success Criteria (new
relationship-strain metric) and Validation Strategy (new required
review) for the corresponding response.

**Objectives-tension risk, sharpened this revision:** the 90-day vs.
annual-funnel tension is now precisely quantified (see Objectives) —
15,000 in 90 days is ≈3.4x a linear reading of the annual range's low
end, and almost exactly consistent with a linear reading of the annual
range's high end. This does not change the risk's substance from v8, but
removes any ambiguity about how large the implicit gap actually is.

**Engineering-cost/build-timeline risk, reconciled in kind:** see Revenue
& Costs — the apparent tension between the 3-month solopreneur timeline
and the $25,000-$120,000+ agency-cost range is explained as a
different-production-model comparison rather than a raw contradiction,
but the absence of any stated external-help budget ceiling means real
cost-overrun risk if the AI-assisted approach stalls remains
unquantified and unmitigated.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8: parent-direct payment, SA launch jurisdiction,
universal consent gate, Android-first, Mbucks/Mpoints dual currency,
7-Mbuck cap with 3-Mbuck pilot cap, Fintech Advance scoping, the two
explicit POPIA/exam-bonus risk acceptances, the fixed Mbucks-to-Rand peg,
the late-penalty mechanic's intended nature as a behavioral nudge rather
than a strictly-collected financial detriment.

**New this revision — a new assumption surfaced by the Revenue & Costs
reconciliation, named explicitly:** it is assumed, but not confirmed by
the user, that the "external expertise on-demand" line will be
engaged sparingly and at modest cost relative to the $25,000-$120,000+
agency-quote range — i.e., that the solopreneur/AI-assisted approach
displaces most, not merely some, of that range. This assumption is the
Incubator's own inference from the qualitative Constraints description,
not a user-confirmed figure, and should be treated as an open
Outstanding Question rather than a settled fact.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8: solopreneur venture, AI-assisted ("vibe coding")
development, external technical expertise on-demand, ~3-month directional
build timeline, deliberately non-granular. Status remains Complete for
the same reason as v8 — the section's central open question ("what
company-side budget, timeline, and team size are available?") has been
answered in the terms the user chose to answer it in. **This revision
adds a cross-reference, not a status change:** the Revenue & Costs
reconciliation above explains why this qualitative characterization does
not contradict the case's separately-sourced agency-cost estimates, while
flagging that no external-help budget ceiling exists within this
section's own content. This is a cross-section consistency note, not a
retraction of Constraints' own Complete status — the user's stated
constraints remain faithfully captured as given.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in overall structure from v8's candidate sequence. **This
revision adds the feature-level gating plan from Legal & Compliance
directly into the sequencing logic:** foundational, non-financial rails
(UI shell, task-assignment engine, curriculum content, budget-input
capture, consent-gate scaffolding) may proceed under the solopreneur/
AI-assisted build immediately; financial-trigger features (invoice
generation, payment-confirmation workflow, late-penalty/arrears
calculation, data-retention pipeline) may not ship to real users until
the specialist legal opinion — or, per the Incubator's recommendation,
at minimum the narrower preliminary legal read — has been obtained.
Status remains Partial: a real sequencing logic, a directional timeline,
and now an explicit feature-level legal gate exist, but no dated
milestone plan, phased budget, external-help budget ceiling, or firm
legal-opinion trigger date has been supplied.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

No funding ask, runway, or numeric financial projections exist in any
input document. The subscription-price-point gap (Value Proposition,
Business Model) remains the single most direct blocker to modeling
absolute revenue, named again here per Investment Committee requirement
#2 rather than invented. The Revenue & Costs reconciliation (requirement
#4) clarifies why the build-cost figures are not directly contradictory,
but supplies no new numeric budget. Engineering-cost and legal-opinion-
cost ranges remain the only numeric cost inputs available, both
externally sourced rather than company-specific.

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Recommended validation priorities, refined this revision:

1. **Legal validation — deliberately deferred, sequencing now explicit.**
   The specialist opinion remains scheduled for the build-spec stage,
   post-Investment-Committee, but is now explicitly bounded to gate only
   financial-trigger features (see Legal & Compliance, Roadmap). The
   Incubator additionally recommends the short, low-cost preliminary
   legal read on the two highest-stakes questions before any further
   version.

2. **Primary user-research validation — bounded explicitly this
   revision.** The n=10 family-interview round must not be used as a
   representative demand signal in any future modeling until either its
   methodology is documented or it is superseded by the planned 20-50
   family pilot or a structured survey (see Problem, Supporting
   Evidence).

3. **Child-development/age-appropriateness review — newly required,
   Investment Committee requirement #5.** Before or alongside the
   planned 20-50 family pilot, the escalating late-penalty mechanic
   should be reviewed by someone with child-development or
   educational-psychology expertise, distinct from the existing
   trust/enforcement/dispute-mechanism lens. The pilot's own success
   criteria should incorporate the new relationship-strain metrics named
   in Success Criteria.

4. **Trust/enforcement and dispute-mechanism validation:** unchanged
   from v8.

5. **Market/demand validation:** unchanged from v8 — a confirmed data
   ceiling exists (commissioned survey, R80,000-R250,000, 3-6 weeks, or a
   live pilot).

6. **Pricing/conversion validation:** unchanged from v8 in substance —
   still blocked on a specific subscription price point.

7. **Curriculum validation:** unchanged from v8.

8. **90-day target reconciliation — now quantified, decision still
   pending.** See Objectives for the precise arithmetic; the business
   should state its intended path (front-loaded marketing assumption,
   named explicitly, or a revised, lower 90-day target) before treating
   15,000 as a firm planning input.

This section remains Partial: validation steps are now more precisely
scoped and one new required step (child-development review) has been
added, but no validation activity beyond the informal n=10 interview
round has actually occurred.

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in content from v8: the n=10 first-party interview data point
(6/10 would-pay, 7/10 education-interested); `ResearchFindings_v1.md`'s
10-item vendor engagement; the user's directly-cited South African
statutory/statistical sources. **This revision adds an explicit bounding
instruction, per Investment Committee requirement #6:** the n=10 finding
must be labeled and treated as [Supported/Low-Medium] evidentiary weight
in all future use — an informal, directional signal, not a validated
demand finding — until its sampling method, recruitment channel, and
question wording are documented, or until it is superseded by the
planned pilot or a structured survey. This instruction is now a standing
constraint on how this data point may be cited in any future revision or
committee deliberation, not a one-time caveat attached only to this
version's Problem section.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Elevated this revision — Investment Committee-required, pending user
decision (not Incubator-invented):**

- What is the actual South African Rand subscription price point (or
  stated range with rationale)? This is now the single most direct
  blocker to modeling Business Model, Value Proposition, and Financial
  Considerations.
- What firm trigger or deadline governs commissioning the specialist
  POPIA/ARB legal opinion (or, at minimum, the recommended preliminary
  legal read)? A feature-level gate now exists (see Legal & Compliance,
  Roadmap); the date/event that starts the clock does not.
- Is the 15,000-in-90-days download target premised on a stated
  front-loaded launch-marketing push (and if so, what specifically), or
  should it instead be revised toward a linear-pace figure (≈4,400-4,500,
  per this revision's arithmetic) consistent with the annual funnel's low
  end?
- What budget ceiling, if any, exists for "external expertise on-demand"
  in the build? This determines how much of the $25,000-$120,000+
  agency-cost range the solopreneur/AI-assisted approach is actually
  expected to displace.
- Will the child-development/age-appropriateness review of the
  late-penalty mechanic (newly required this revision) be commissioned
  before, during, or independently of the planned 20-50 family pilot, and
  who will conduct it?
- Does the user intend to document the n=10 interview round's
  methodology retroactively, or treat it as fully superseded by the
  planned pilot/structured survey without further documentation?

**Resolved across prior versions, unchanged:** company-side budget/
timeline/team-size characterization (v8); ads-hybrid vs.
subscription-only decision (v8); distribution strategy — both
direct-to-parent and schools-partnership (v8).

**Still open, carried forward unchanged from v8** (see `BusinessCase_v8.md`
for the full itemized list: fund custody, consent-gate technical
mechanism, task verification, dispute-escalation beyond 48 hours,
payment-routing timeline, late-penalty cap rationale, Fintech Advance
scope, arrears disposition, exam-bonus data source, Mbucks-peg
flexibility, curriculum age-band splits, whether the specialist legal
opinion will in fact be commissioned as planned, app-store policy
sub-questions, MoneyAfrica Kids' unpublished premium price, whether
informal engineering-cost quotes will be sought, and the
schools-partnership channel's timeline/target school count/resourcing
plan).

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted.

| Section | Status | Weight | Points |
| - | - | - | - |
| Executive Summary | Partial | 1x | 2 |
| Problem | Partial | 1x | 2 |
| Opportunity | Partial | 1x | 2 |
| Objectives | Partial | 1x | 2 |
| Success Criteria | Partial | 1x | 2 |
| Stakeholders | Partial | 1x | 2 |
| Target Users/Customers | Partial | 1x | 2 |
| Value Proposition | Partial | 1x | 2 |
| Market & Competition | Partial | 1x | 2 |
| Business Model | Partial | 1x | 2 |
| Revenue & Costs | Partial | 1x | 2 |
| Operations | Complete | 1x | 5 |
| Technology | Partial | 1x | 2 |
| Legal & Compliance ★ | Partial | 2x | 4 |
| Risks | Partial | 1x | 2 |
| Assumptions | Partial | 1x | 2 |
| Constraints | Complete | 1x | 5 |
| Roadmap | Partial | 1x | 2 |
| Financial Considerations | Partial | 1x | 2 |
| Validation Strategy | Partial | 1x | 2 |
| Supporting Evidence | Partial | 1x | 2 |
| Outstanding Questions | Complete | 1x | 5 |
| Curriculum Design (extension) | Partial | 1x | 2 |
| Child Data & Consent (extension) ★ | Partial | 2x | 4 |

Points earned: **61** (unchanged from v8 — no section's Status changed
this revision).

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130** (unchanged from v8's
corrected denominator).

**Readiness Score = 61 / 130 = 46.9%, rounded to 47%. Unchanged from
v8.**

**Why the score did not move despite six items being addressed:** the
Investment Committee's six required changes were, on inspection, five
items requiring either a genuine user decision (price point, 90-day
target resolution, legal-opinion trigger date) or a real-world action not
yet taken (child-development review, interview-methodology
documentation), plus one item (build-timeline/cost reconciliation) that
the Incubator could and did resolve analytically — but analytical
reconciliation of two already-known figures does not itself constitute
new evidence that moves a section's Status tier. This is stated plainly:
addressing the Investment Committee's verdict thoroughly, within the
no-invention constraint, does not always move the numeric score, and this
revision is a clear case of that. Progression across versions: 24% (v3)
→ 36% (v4) → 39% (v5) → 40% (v6) → 40% (v7) → 47% (v8) → **47% (v9,
unchanged)**.

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB legal opinion remains unobtained. This
   revision adds an explicit feature-level gating plan (financial-trigger
   features locked; foundational rails may proceed) and a recommended
   low-cost preliminary legal read, per Investment Committee requirement
   #1 — but the firm trigger/deadline for commissioning either the
   preliminary read or the full opinion is still a user decision not yet
   made. The underlying legal uncertainty is unchanged.

2. **Subscription price point (Value Proposition, Business Model,
   Financial Considerations)** — still not set. Elevated this revision
   from a background Outstanding Question to a named, required
   pre-Developing-Committee input, per Investment Committee requirement
   #2. MoneyTime SA's R995/year remains the only anchor, flagged as
   likely under-anchoring.

3. **90-day (15,000) vs. annual funnel (18,000-61,000) target tension
   (Objectives, Risks)** — now precisely quantified (15,000 in 90 days ≈
   3.4x a linear reading of the annual low end; almost exactly consistent
   with a linear reading of the high end) per Investment Committee
   requirement #3, but the choice between stating a front-loaded
   marketing assumption or revising the target remains open.

4. **Build-timeline vs. engineering-cost reconciliation (Revenue &
   Costs, Constraints)** — reconciled in kind this revision (different
   production models, not a raw contradiction) per Investment Committee
   requirement #4, but no external-help budget ceiling exists, so the
   reconciliation is qualitative, not quantitative.

5. **Late-penalty mechanic child-development risk (Success Criteria,
   Operations, Risks, Validation Strategy)** — newly named as its own
   risk category this revision, per Investment Committee requirement #5,
   with a required (not yet completed) expert review and new pilot
   success-criteria to be added. No version of this case has yet had this
   mechanic assessed from a child-development standpoint.

6. **n=10 interview evidence weight (Problem, Supporting Evidence)** —
   explicitly bounded this revision, per Investment Committee requirement
   #6: must not be used as representative demand evidence until its
   methodology is documented or it is superseded by the planned pilot or
   a structured survey.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8. Not cited by any of the six Investment Committee items
directly, though the newly-required child-development review (Risks,
Validation Strategy) is adjacent to, but distinct from, this section's
existing unresolved items (age-band curriculum splits, instructional
format, standards alignment, content authorship).

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v8 in substance: the universal consent-gate model; the two
explicit user risk-accepted assumptions (POPIA Section 14 retention
sufficiency; exam-bonus mechanic's no-schools-data-privacy-dimension
assumption); Google Play's Families Policy loyalty-point disclosure
requirement; Apple's Kids Category age-band/parental-gate/
advertising-review requirements and the unresolved IAP-currency question;
the confirmed absence of ARB/NCR precedent for "payslip"/"invoice"/"late
penalty" terminology applied to minors.

**This revision:** the feature-level gating plan specified in Legal &
Compliance above applies directly to this section's concerns — the
data-retention/deletion pipeline implementing the POPIA Section 14
risk-accepted assumption is explicitly named as one of the
financial/compliance-trigger features that may not ship without the
specialist opinion (or, at minimum, the recommended preliminary legal
read) having been obtained.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Child Data & Consent are both Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 47% (61/130), unchanged
  from v8. Progression: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) → 40%
  (v7) → 47% (v8) → 47% (v9).

- Expert roster entries ≥3 sentences, each naming a specific
  case-study assumption: see `ExpertRoster.md`, regenerated in full this
  cycle per the Investment Committee's Gate Integrity Check note.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated in full this cycle per the
  same note.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
remains 47%, unchanged from v8 — this revision addresses all six
Investment Committee-required changes with real analytical rigor
(precise arithmetic on the 90-day target tension, an explicit
feature-level legal gating plan, an analytical reconciliation of the
build-cost figures, a newly-named and required child-development risk
review, and an explicit evidentiary-weight bound on the n=10 interview
data) without inventing the specific user decisions still required
(subscription price point, the legal-opinion trigger date, the choice
between a front-loaded marketing assumption or a revised 90-day target).
A v10 would need those specific user decisions, plus the
child-development review and interview-methodology documentation actually
carried out, to meaningfully advance the Readiness Score beyond this
revision's structural, non-numeric improvements.
