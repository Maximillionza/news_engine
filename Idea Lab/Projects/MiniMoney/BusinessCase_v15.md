# Business Case: MiniMoney — v15

> Prepared by: Incubator. Source input for this cycle: `00_CaseStudy.md`
> (verbatim user submission, 2026-07-05), `BusinessCase_v9.md` (last
> version where the ten sections addressed below still carried
> substantive, if condensed, content), `BusinessCase_v14.md` (current,
> otherwise-correct state), `Clarifications_v10.md`, `Clarifications_v11.md`,
> `ResearchFindings_v2.md`, `Clarifications_v12.md`, `ResearchFindings_v3.md`,
> `Clarifications_v14.md`. This document is self-certified against the
> Incubator completion gate.

> **This is a consolidation cycle, not a clarification-driven revision.**
> A Chief of Staff audit found that `BusinessCase_v14.md` (and several
> versions before it) carried ten sections forward as bare, contentless
> pointers — literally "Unchanged from v13. Not addressed this revision,"
> with no substantive text reproduced. This breaks the document's own
> stated design principle: a complete, standalone Business Case readable
> without needing any prior version. The Investment Committee is
> architecturally restricted to reading only `BusinessCase.md` and
> `ExecutiveSummary.md` — a bare pointer is unreadable to it.
>
> **The ten affected sections:** Problem, Opportunity, Objectives, Success
> Criteria, Stakeholders, Target Users/Customers, Value Proposition,
> Market & Competition, Constraints, and Curriculum Design (the domain
> extension). Each is reconstructed below by starting from its last full
> version in `BusinessCase_v9.md` and tracing forward through every
> clarification/research-finding file that actually touched it —
> reproducing what each intervening cycle should have written instead of
> collapsing to a pointer. All other sections (already complete and
> correct in v14) are preserved essentially as-is; this is a completeness
> fix, not an occasion to re-litigate settled content.
>
> **A genuine sub-limitation, disclosed rather than papered over:** two of
> the ten sections — Market & Competition and Curriculum Design — were
> *already* thin, bare pointers in `BusinessCase_v9.md` itself ("Unchanged
> from v8," with no substantive content reproduced there either), and
> `BusinessCase_v8.md` is not among this cycle's authorized inputs. For
> these two sections, this Incubator reconstructs everything it can from
> the material actually available (the case study, v9's own cross-
> references, and relevant research findings) and explicitly flags,
> rather than invents, whatever remains genuinely unknown as a result.

## What Changed in v15 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Ten sections reconstructed to full, self-contained, substantive text:
Problem, Opportunity, Objectives, Success Criteria, Stakeholders, Target
Users/Customers, Value Proposition, Market & Competition, Constraints,
and Curriculum Design (Domain Extension). Method: for each section, start
from `BusinessCase_v9.md`'s last full text, then apply — in chronological
order — every subsequent clarification or research finding that named or
substantively affected that section, exactly as if each intervening
version had reproduced the section properly:

- **Objectives:** the v9 90-day-vs-annual tension is resolved via
  `Clarifications_v10.md`'s confirmation that 100/day is a floor, not the
  target — Status raised from Partial to **Complete**, matching
  `BusinessCase_v14.md`'s scoring table (this status was already correct
  in v14's numbers; only the section's text was missing).
- **Value Proposition:** the v9 subscription-price-point gap is resolved
  via `Clarifications_v10.md` (R59.99/month, up to 4 children per family)
  — Status raised from Partial to **Complete**, likewise already correct
  in v14's numbers.
- **Success Criteria, Stakeholders, Target Users/Customers, Market &
  Competition:** updated where later clarifications or research findings
  actually touched them (late-penalty redesign, optional account-linking,
  competitive-landscape research); otherwise reproduced from v9 largely
  intact. Status unchanged from v14's table (Partial in all four cases).
- **Problem, Opportunity, Constraints:** no later clarification or
  research finding touched these directly — reproduced from v9's full
  text essentially unchanged. Status unchanged from v14's table.
- **Curriculum Design (Domain Extension):** reconstructed from the
  limited material available (see limitation note above); Confidence
  explicitly **downgraded from Medium to Low** on reconstruction, because
  writing the section out in full — rather than leaving it as a pointer —
  reveals the actual evidentiary base is thinner than a Medium tag
  implied. Per Playbook Entry 3 (track Confidence trajectory as its own
  signal, separate from Status), this downgrade is stated explicitly
  rather than left for a future reviewer to notice on their own.

**Net effect on Readiness Score: none.** No section's Status changes as a
result of this cycle beyond what was already reflected in
`BusinessCase_v14.md`'s own scoring table — the two sections whose Status
increased (Objectives, Value Proposition) were *already* counted as
Complete in v14's table; v14's failure was only that the section bodies
themselves were unreadable pointers, not that the table was wrong. The
Readiness Score is therefore recomputed in full below and confirmed
**unchanged at 52% (67/130)**. This cycle is a self-containment and
traceability fix, not a new information event.

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6-18), launching first in South Africa on Android (iOS porting
planned as future work), combining gamified task assignment with a
simulated payroll system. The parent submits a budget setting the
minor's "basic income"; tasks earn Mbucks (a real-money-pegged in-app
currency, e.g. 10 Mbucks = R10) which accumulate into a "payslip," while
every completed task separately earns a fixed 10 Mpoints — a distinct,
non-monetary cosmetic-store currency. The parent receives an invoice and
pays the owed amount directly to the child via the parent's own banking
app — MiniMoney itself never holds, transmits, or takes custody of
funds. Subscription pricing is R59.99/month, covering up to 4 children
per family account. Monetization is subscription-only at launch, with
advertising deferred to a possible post-launch V2. Real-money in-app
purchases remain parent-only. The late-payment penalty mechanic is
incurred entirely by the parent (5→6→7 Mbucks/week, pilot cap 3); the
child has zero visibility into it.

A minor cannot register an account, nor access any part of the app,
without a parent acting as registration custodian from the outset. A
brief pre-link independent-registration carve-out (allowing a minor to
independently register and access a practice-only budgeting feature
before any parent link existed) was introduced at v12 and removed again
at v14 — the case reverts to, and reaffirms, the universal
parental-consent gate established at v5. There is no longer any point at
which a minor's account exists, or their data is processed, ahead of
parental consent.

Account-linking is now an optional, parent-controlled feature, not an
exclusion. A parent may optionally link a read-only bank view (via a
Stitch/Mono-style integration) to help verify a child's payment; honor-
system self-report remains the default path for parents who decline to
link. The underlying regulatory question — whether the NCR or any other
South African regulator actually reaches a read-only, non-custodial
account-verification service — remains unresolved by desk research and
gates this feature's ship date behind the still-uncommissioned specialist
legal opinion.

Neither of these two design changes resolves the underlying, still-open
legal questions (contractual capacity; domestic-agreement presumption;
ARB precedent absence; whether the NCR regulates read-only linking) —
both Critical Legal sections remain **Partial**, and Confidence holds
flat at **Medium**, bounded by these unrelated, untouched items. The
Readiness Score is **52% (67/130)**, confirmed unchanged by this cycle's
recomputation.

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

A first-party interview round (n=10 families) found 6 of 10 confirmed
interest in using the app and stated willingness to pay for it; 7 of 10
expressed interest specifically in the education aspect. This is genuine,
first-party, MiniMoney-specific evidence, categorically different from
comparable-market inference, but it is not statistically significant —
sampling method, recruitment channel, family-selection criteria, and
exact question wording are all unknown. Per a standing instruction
adopted at v9 and reaffirmed at v10 (`Clarifications_v10.md`: "accept it
stays bounded as non-representative"), this data point must not be used,
in this or any future version, as if it were a representative or
validated demand signal — in funnel modeling, in Financial
Considerations, in Objectives, or anywhere else — until either (a) its
methodology is documented retroactively (recruitment channel, sampling
frame, exact question wording), or (b) it is superseded by the
already-planned 20-50 family pilot or a structured survey. This
instruction exists precisely because a directional, encouraging n=10
result can otherwise quietly accumulate more evidentiary weight across
successive versions than it warrants.

No clarification or research finding after v9 has revisited the core
Problem framing itself. Status remains Partial for the same reason it has
since v8: this is a real, encouraging, directional signal, not an
established finding that parents broadly perceive this as a problem worth
paying to solve.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic rather than a simple
debit-card-for-kids model, framed as an edtech app with a
payroll-simulation UX. No direct South African incumbent does what
MiniMoney does. `ResearchFindings_v1.md` Item 5 (carried from v7) adds a
directional data point: MoneyAfrica Kids shows modest download volumes,
while MoneyTime SA claims a larger, self-published B2B2C-mediated reach
(130,000 students via schools) — together suggesting real but unproven
consumer appetite, with the strongest demonstrated reach coming via a
schools-distribution model. Distribution strategy treats a
schools-partnership channel as an intended, parallel channel alongside
direct-to-parent acquisition, not a rejected alternative — the
schools-partnership timeline, target school count, and resourcing plan
remain open items (see Outstanding Questions).

No clarification or research finding between v10 and v14 revisits or adds
to this section's core content directly. The subscription price now
confirmed (R59.99/month, up to 4 children per family, per
`Clarifications_v10.md`) sharpens the competitive read against MoneyTime
SA's R995/year (25% sibling discount): MiniMoney's price, expressed
monthly, sits below MoneyTime SA's annualized rate even before the
sibling discount is applied, which is relevant opportunity context but
does not on its own establish market size or demand — that remains
governed by the same n=10, non-representative bound described in Problem.
Status remains Partial: the differentiation thesis is coherent and
partly evidenced, but no structured market-sizing or validated demand
study has been conducted.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The functional objective is: budget → tasks → Mbuck/Mpoint earning →
exam bonus → invoice/payslip → payment confirmation with escalating
late-penalty → age-gated education. As of `Clarifications_v10.md` and
`Clarifications_v14.md`, the late-penalty step in this flow is incurred
entirely by the parent and is invisible to the child (see Success
Criteria, Legal & Compliance); this does not change the objective
sequence itself, only who bears and sees the late-penalty consequence
within it.

**The 90-day (15,000 installs) vs. annual funnel (18,000-61,000
installs) target tension — resolved via `Clarifications_v10.md`, not
merely quantified.** At v9, the Incubator established the arithmetic
precisely without resolving it: a strictly linear pace against the
annual range's low end would imply ≈4,438 installs in 90 days, not
15,000 — the stated 90-day target was roughly 3.4x a linear-pace reading
of the annual low end, and almost exactly consistent with a linear
reading of the high end (61,000). This left two paths open: state an
explicit front-loaded launch-marketing assumption, or revise the 90-day
target downward.

`Clarifications_v10.md` resolves this directly. The user's own framing:
"We are targeting onboarding at least 100 a day for the first 90 days,"
clarified on follow-up as **"The 100 per day is the floor target with
the intention to increase the adoption rate above this."** This confirms
the front-loaded-growth path, not a target revision: 100/day × 90 days =
9,000 as an explicit *minimum* floor, while the retained 15,000-in-90-days
figure requires an average of ≈167/day across the window — well above
the 100/day floor, consistent with a ramping adoption curve rather than a
flat rate, and internally consistent with the annual range's high end as
already shown at v9. The tension is resolved in the sense the Investment
Committee required ("resolved, not described"): the business now has an
explicit, user-confirmed floor-plus-ramp model rather than an
unreconciled flat-rate mismatch.

Pre-launch and Growth-phase objectives beyond the 90-day/annual figures
are not independently detailed in any input available to this
reconstruction cycle — this is flagged as a genuine gap (Unknown, not
invented) rather than assumed identical to any prior version's
unspecified content.

Status is raised to **Complete**: the specific tension the Investment
Committee required resolved is now resolved by a direct, Verified-tier
user clarification, not merely bounded analytically. Confidence and
Evidence are set to **High/Verified** for this reason — this is the
highest evidentiary tier this case uses, reserved for facts the user has
personally confirmed.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Core criteria, carried from v8/v9: pilot success (majority of families
complete ≥4 consecutive weekly cycles); curriculum engagement (30%, no
external benchmark); operational health (65% task-completion without
dispute, no external benchmark); freemium/subscription conversion (2%,
correctly benchmarked against the 1-3% subscription-only range);
retention (no figure proposed).

**Family-relationship-strain criterion, added at v9 (Investment Committee
requirement #5), reframed at v10 following the late-penalty redesign.**
The v9 requirement was to track relationship-strain indicators segmented
by child age band, since the escalating late-penalty mechanic (5→6→7
Mbucks/week, pilot cap 3) plausibly lands very differently on a 6-year-old
than a 17-year-old. `Clarifications_v10.md` then redesigned the mechanic
itself: the parent alone incurs the penalty, and the child has **zero
visibility** into whether a penalty was charged or how much is owed. This
substantially narrows, but does not eliminate, the direct child-facing
version of this risk — a child who cannot see a penalty cannot be
directly distressed by it in the way the original criterion assumed. The
user's own framing when supplying this redesign explicitly anticipated
this: the Incubator was asked to assess "whether this substantially
narrows (though perhaps does not fully eliminate — a parent's own stress
or behavior around an accumulating obligation could still indirectly
affect the child) the child-development risk."

Accordingly, the relationship-strain criterion is reframed here, not
retired: candidate metrics should now target *indirect* effects — a
parent's own financial stress or behavioral change around an
accumulating, child-invisible penalty obligation, and whether that stress
measurably surfaces in the household regardless of the child's lack of
direct visibility — rather than child-reported friction over a penalty
amount the child can no longer see. Candidate metrics, none yet adopted
or measured: parent-reported friction/conflict incidents plausibly
traceable to the penalty obligation even though not disclosed to the
child; dispute frequency (now necessarily parent-only, since the child
cannot dispute a penalty they cannot see) segmented by child age band;
pause/opt-out rate by age band; a simple pre/post parent-reported
household-stress indicator specific to the payslip/penalty mechanic. No
such metric currently exists in any input available to this
reconstruction cycle — this is a reframed, not a newly invented,
requirement, and it stands until the pilot design formally incorporates
it.

Status remains Partial: the conversion benchmark is resolved, but
curriculum engagement, operational health, and retention remain
unbenchmarked, and the reframed relationship-strain criterion does not
yet exist in any concrete, measurable form.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens (6-18, sub-banded — the specific age-band boundaries
themselves are referenced elsewhere in this case's history as an
existing design decision, but are not present in any input available to
this reconstruction cycle; flagged as Unknown, cross-referenced to
Curriculum Design's still-open "age-band curriculum splits" item, which
may or may not use the same banding); parents/guardians; the app
operator; the South African Information Regulator (POPIA enforcement)
and the Advertising Regulatory Board (ARB); three named competitors (two
identified elsewhere in this case as MoneyAfrica Kids and MoneyTime SA —
see Market & Competition; the third's identity is not present in any
input available to this reconstruction cycle and is flagged as Unknown
rather than invented); and Apple/Google as app-store platform
stakeholders.

A minor cannot register, or have any data processed, without a parent
acting as registration custodian from the outset (reaffirmed at v14,
after a narrow v12 carve-out was tried and reverted) — this has been the
case's standing design since v5 and remains so; the parent's role as
registration custodian is not a peripheral detail but the entry point for
every other stakeholder relationship in the product.

**New stakeholder relationship, introduced at v14:** where a parent opts
into the now-optional account-linking feature (Stitch/Mono-style,
read-only), the linking aggregator itself becomes an additional
data-processor/controller stakeholder sitting between MiniMoney and the
parent's own bank — per `ResearchFindings_v2.md` Item 1, this
relationship introduces its own consent-flow, credential-handling, and
data-sharing-agreement obligations under POPIA's "operator" (processor)
provisions, distinct from and additional to MiniMoney's existing direct
obligations. This applies only to parents who opt in; the honor-system
default introduces no such third party. The parent's own bank remains an
unaddressed direct stakeholder for the honor-system default path.

A child-development/age-appropriateness reviewer, required since v9 to
assess the late-penalty mechanic, remains a stakeholder-adjacent expert
voice this venture has not yet engaged (see Risks, Validation Strategy).

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18 (sub-banded — see Stakeholders for the same
age-band-boundary limitation) and their parents/guardians, in South
Africa, on Android at launch (iOS planned as future work). A minor is
not an independently reachable user: every child account requires a
parent acting as registration custodian from the outset, and the product
is functionally sold to, and accessed through, the parent first. This
was reaffirmed at v14 after a narrow, since-reverted v12 exception; the
case's target-user model has not otherwise changed since v8.

No clarification or research finding between v10 and v14 revisits
segmentation, geography, or platform targeting directly. Status remains
Partial: the target population is clearly named, but no market-sizing,
persona-level detail, or segment-specific acquisition data exists beyond
what is captured in Market & Competition and the funnel figures in
Objectives.

## Value Proposition

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household tasks into a
structured payroll-like experience with a built-in financial literacy
curriculum, and — since v14 — an optional, parent-controlled way
(account-linking) to add automated verification on top of the default
honor-system self-report. For children: a "real job" simulation paid out
via the parent's own bank transfer, tied to age-appropriate lessons,
alongside a separate cosmetic-reward system (Mpoints). Since
`Clarifications_v10.md`'s late-penalty redesign, the child-facing value
proposition is purely additive — earning, lessons, and cosmetic rewards —
with no penalty-side friction visible to the child at all; the
escalating late-penalty is a parent-only administrative matter.

**Subscription price point — resolved.** `Clarifications_v10.md`:
"for the subscription it will start at R59.99 a month which will allow
upto 4 kids per family." This is Verified-tier evidence (direct user
confirmation), and it is the single fact that closes the v9 gap the
Investment Committee flagged as the most direct blocker to modeling this
venture's value proposition and unit economics. MoneyTime SA's R995/year
(25% sibling discount) remains the only other South African price
anchor in this case, and — expressed monthly (≈R82.92/month, before its
own sibling discount) — sits above MiniMoney's R59.99/month, consistent
with the earlier flag that MoneyTime SA's price likely represented an
under-anchor for a lighter-weight product rather than a ceiling MiniMoney
needed to match.

**What remains unresolved, and is not invented here:** the specific
free-vs-subscription feature split (which features, if any, are
accessible without a paid subscription, versus which are gated behind
it) is referenced in this case's history but its specific content is not
present in any input available to this reconstruction cycle. Confidence
is held at **Medium, not raised to High**, specifically because of this
residual gap — the pricing figure itself is Verified, but the
feature-boundary detail that would let a reader fully evaluate the
free/paid value proposition is not. This mirrors the pattern already
established elsewhere in this case (Legal & Compliance, v14): a
resolved sub-item does not automatically lift a section's Confidence
ceiling when an unrelated, untouched gap remains.

Status is raised to **Complete**: the specific gap that kept this section
Partial since v8 — the missing price point — is now resolved by direct
user confirmation, satisfying the Investment Committee's own framing that
a price point "even as a stated range with rationale" was required before
this section could be treated as modelable.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Disclosed limitation:** this section was already a bare, uncontentful
pointer at `BusinessCase_v9.md` ("Unchanged from v8," with no
substantive text reproduced there either). `BusinessCase_v8.md` is not
among this cycle's authorized inputs. What follows is reconstructed from
material actually available elsewhere in this case — v9's own
cross-references, the Opportunity section, Stakeholders' "three named
competitors" reference, and relevant research findings — not invented to
fill the gap.

No direct South African incumbent replicates MiniMoney's
payroll-simulation mechanic (see Opportunity). Two named South African
competitors are identifiable from material available to this
reconstruction: **MoneyAfrica Kids**, showing modest download volumes
per `ResearchFindings_v1.md` Item 5, and **MoneyTime SA**, which claims a
larger, self-published, schools-B2B2C-mediated reach (130,000 students)
at R995/year (25% sibling discount) — a price point flagged elsewhere in
this case as a likely under-anchor for a lighter-weight product.
Stakeholders references "three named competitors"; the third's identity
is not present in any input available to this reconstruction cycle and
is flagged as **Unknown**, not invented.

International comparables, surfaced by `ResearchFindings_v2.md` Item 3
(commissioned to research enforcement mechanisms, not competition, but
directly relevant here) split into two structurally different
approaches. **GoHenry** (recently folded into Acorns Early) and
**Greenlight** solve payment-verification by becoming the money-mover
themselves — issuing their own prepaid card and holding/moving funds
under card-issuing/e-money licensing, a materially different regulatory
posture than MiniMoney's deliberately non-custodial design. **FamZoo**
(IOU-accounts feature) and **Bomad** ("Bank of Mom and Dad") are closer
structural analogs to MiniMoney: both are track-only, honor-system
products with no bank integration, confirming that MiniMoney's chosen
model has precedent elsewhere and is not a category outlier. No
South-Africa-specific comparable to FamZoo or Bomad was found — this is
the same local-market evidence gap flagged in `ResearchFindings_v1.md`'s
Engagement 1, not a new one.

The Year-1 install funnel range (18,000-61,000, see Objectives) provides
the addressable-adoption backdrop against which competitive share would
eventually be judged, though no source in this case apportions that
range across named competitors specifically. The schools-partnership
distribution channel (see Opportunity) appears, from MoneyTime SA's
larger claimed reach, to be a more proven path to scale in this category
than direct-to-parent acquisition alone — this remains a directional
inference, not a validated finding.

Status remains Partial: the competitive landscape is more populated with
named players and structural comparables than a bare pointer would
suggest, but no structured market-share, pricing-elasticity, or
head-to-head feature comparison exists, and one named competitor's
identity remains genuinely unknown to this reconstruction.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Structure
confirmed and monetization-resolved (subscription-only at launch, ads
deferred to V2); R59.99/month, up to 4 children per family. Optional
account-linking is a trust/verification feature within the existing
subscription model, not a new revenue line — it gives parents who opt in
an additional, automated way to verify a child's earnings claim,
alongside the existing honor-system self-report default, and is gated
behind the specialist legal opinion before it can ship. The
Mpoints/Apple IAP-currency question remains unresolved.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. The
engineering-cost range ($25,000-$40,000 MVP; $60,000-$120,000+ full
build, from five converging agency-quote estimates) is reconciled *in
kind*, not *in amount*, against the solopreneur/AI-assisted production
model described in Constraints — the two figures price different things
(agency-priced labor cost vs. founder-time timeline). No budget ceiling
exists for the "external expertise on-demand" line, so how much of the
agency range this approach actually displaces remains open. CAC and
curriculum-production cost remain unresolved. The unreconciled
subscriber-count discrepancy (180-1,830 computed vs. 360-2,440 cited)
remains open (see Outstanding Questions).

## Operations

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Mechanical
description of the budget → task → earning → payslip → payment flow is
complete. The late-penalty mechanic (5→6→7 Mbucks/week, pilot cap 3) is
parent-incurred, invisible to the child. Optional account-linking's
operational opt-in flow (where offered, consent language, un-linking) is
undocumented and remains an open item. A residual ambiguity is flagged,
not resolved: whether a distinct post-registration, pre-budget-link stage
still exists within the now fully parent-supervised flow.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Optional
read-only account-linking is a Stitch/Mono-style API integration
dependency, parent-opt-in only, gated behind the specialist legal opinion.
Honor-system self-report remains the default technical path requiring no
external integration. No technology-stack detail for the linking
integration itself has been specified in any input available to this
case.

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. The
specialist POPIA/ARB/contract-law legal opinion remains unobtained. The
pre-link independent-registration carve-out is resolved by removal
(v14), which closes the specific scenario that likely triggered POPIA's
Section 34/35 consent requirement at registration — a genuine structural
risk elimination, not merely a Confidence-improving clarification.
Read-only account-linking is now optional rather than excluded; the
underlying NCR question (does the NCR reach a read-only, non-custodial
service) remains unresolved by desk research (`ResearchFindings_v3.md`
Item 2: none of the NCR's four registration categories plausibly fits,
but this is a reasoned inference, not a regulator statement) and now
gates a single shippable optional feature rather than justifying a
permanent exclusion. Minor contractual capacity, the domestic-agreement
presumption, and the absence of ARB/NCR precedent for
"payslip"/"invoice"/"late penalty" terminology applied to minors remain
untouched, unresolved items. Confidence holds flat at Medium, bounded by
these untouched items, not by anything resolved this cycle. The
feature-level build-gating plan established at v9 (financial-trigger
features locked behind the opinion; foundational rails may proceed in
parallel) remains in force, with optional account-linking added to it as
a new gated item.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Regulatory
risk (Critical); child-safety/data-privacy risk (Critical, partly
risk-accepted); trust/enforcement risk (reframed — the "foregone
opportunity" framing around account-linking is resolved since the
feature is no longer excluded, but the feature itself cannot ship until
the specialist opinion clears the NCR question); terminology/perception
risk; child-development/age-appropriateness risk (named at v9, still
requiring the not-yet-commissioned expert review); competitive risk;
monetization-execution risk; app-store policy risk; platform-
concentration risk; adoption/forecasting risk; engineering-cost
estimation risk; legal-opinion-deferral risk (sharpened — the opinion's
required scope has now been narrowed across five consecutive revisions,
v10 through v14, without being commissioned).

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Parent-
direct payment; SA launch jurisdiction; universal consent gate (no
exceptions, as of v14); Android-first; Mbucks/Mpoints dual currency;
7-Mbuck cap with 3-Mbuck pilot cap; the two explicit POPIA/exam-bonus
risk acceptances; the fixed Mbucks-to-Rand peg; the late-penalty
mechanic's nature as a parent-only administrative matter, invisible to
the child. The NCR-avoidance premise underlying the original Stitch/Mono
exclusion is decoupled from the current product decision (linking is now
optional regardless of how that question resolves) but remains itself
unconfirmed. The v12/v13 assumption about the pre-link carve-out's POPIA
posture is moot, superseded by its v14 removal, retained for audit-trail
continuity only.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Solopreneur venture; AI-assisted ("vibe coding") development; external
technical expertise engaged only on-demand, for scoped, harder problems
the founder cannot resolve alone (the specialist legal opinion is one
clear example, already costed separately at R25,000-R80,000);
directional ~3-month build timeline; deliberately non-granular by the
user's own stated preference. No clarification or research finding
between v10 and v14 revisits this section directly. Status remains
Complete for the same reason it has since v8 — the section's central
question ("what company-side budget, timeline, and team size are
available?") has been answered in the terms the user chose to answer it
in — even though this qualitative characterization does not, by itself,
resolve how much of the separately-sourced $25,000-$120,000+ agency-cost
range the solopreneur/AI-assisted approach actually displaces (see
Revenue & Costs).

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle.
Foundational, non-financial rails (UI shell, task-assignment engine,
curriculum content, budget-input capture, consent-gate scaffolding) may
proceed under the solopreneur/AI-assisted build immediately;
financial-trigger features (invoice generation, payment-confirmation
workflow, late-penalty/arrears calculation, data-retention pipeline, and
now optional account-linking) may not ship to real users until the
specialist legal opinion — or, at minimum, the recommended preliminary
legal read — has been obtained. The opinion's commissioning trigger
remains event-based ("once a stable working model exists, and before any
pilot testing with real families begins," per `Clarifications_v10.md`),
a point this Incubator has repeatedly flagged, without prescribing a
decision, as worth reconsidering in favor of a dated trigger, now that
five consecutive revisions have narrowed the opinion's required scope
without commissioning it.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. No funding
ask, runway, or full numeric financial projections exist. The
subscription price (R59.99/month, up to 4 children per family) is now
known and can be modeled against the Year-1 funnel range, but the
family-vs-child install-count ambiguity (does the funnel range count
families or individual children?) remains unresolved — checked against
the now-removed pre-link carve-out as a possible contributing cause per
`Clarifications_v14.md`'s prompt, but this Incubator's available inputs
cannot confirm or rule out that connection. The unreconciled
subscriber-count discrepancy (180-1,830 vs. 360-2,440) remains open.

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Legal
validation (opinion's required scope narrower, still unobtained);
primary user-research validation (n=10 bound, unchanged); child-
development/age-appropriateness review (still required, not yet
commissioned); trust/enforcement and dispute-mechanism validation (now
also covering whether parents actually opt into account-linking and
whether it measurably improves trust outcomes); market/demand validation
(commissioned survey, R80,000-R250,000, 3-6 weeks, or a live pilot);
pricing/conversion validation (price now known, conversion still
unvalidated); curriculum validation (unchanged, still generic — see
Curriculum Design below); account-linking feature validation (new at
v14: requires both specialist legal confirmation and a designed,
reviewed opt-in consent flow, neither of which exists yet).

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. The n=10
first-party interview data point (bounded, non-representative, per
standing instruction); `ResearchFindings_v1.md`'s (Engagement 1),
`ResearchFindings_v2.md`'s (Engagement 2), and `ResearchFindings_v3.md`'s
(Engagement 3) vendor engagements, all Supported-tier; the user's
directly-cited South African statutory/statistical sources;
`Clarifications_v10.md`, `Clarifications_v11.md`, `Clarifications_v12.md`,
and `Clarifications_v14.md`, each Verified-tier as to what design
decision was made, not Verified as to any underlying legal or market
question those decisions merely reframe rather than resolve.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Still
open: does the specialist legal opinion confirm or refute NCR exposure
for read-only account-linking; does a distinct post-registration,
pre-budget-link practice stage still exist; the account-linking opt-in
UX flow; the family-vs-child install-count ambiguity; whether the
event-based legal-opinion trigger should become a dated one; the
subscriber-count discrepancy; the preliminary legal read's adoption
decision; fund custody mechanics; task verification; dispute-escalation
beyond 48 hours; payment-routing timeline; late-penalty cap rationale;
Fintech Advance scope; exam-bonus data source; Mbucks-peg flexibility;
curriculum age-band splits, instructional format, standards alignment,
and content authorship (see Curriculum Design); app-store policy
sub-questions; MoneyAfrica Kids' unpublished premium price; the identity
of the third named competitor (new, surfaced by this cycle's Market &
Competition reconstruction); the specific free-vs-subscription feature
split (new, surfaced by this cycle's Value Proposition reconstruction);
whether informal engineering-cost quotes will be sought; the
external-help budget ceiling; the schools-partnership channel's
timeline/target school count/resourcing plan; the domestic-agreement
presumption's application to MiniMoney's "agreed condition of budget
setup" framing.

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted. Recomputed in full
against this cycle's reconstructed document.

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

Points earned: **67**.

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130.**

**Readiness Score = 67 / 130 = 51.5%, rounded to 52%. Confirmed unchanged
from v14** — every section's Status in this recomputation matches
`BusinessCase_v14.md`'s own scoring table exactly; this cycle fixed
section *bodies*, not section *statuses*.

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
52% (v13) → 52% (v14) → **52% (v15, consolidation — no Status changed;
ten previously-bare-pointer sections given full, self-contained
substantive text).**

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB/contract-law legal opinion remains
   unobtained. Scope is narrower than at any prior version (the pre-link
   carve-out's POPIA posture is removed) but still covers: domestic-
   agreement presumption; minor contractual capacity; the NCR question,
   now gating the optional account-linking feature specifically.
   Confidence holds flat at Medium.

2. **Family-vs-child install ambiguity (Financial Considerations,
   Revenue & Costs, Assumptions)** — unresolved; checked against the
   now-removed carve-out as a possible cause, inconclusively.

3. **Account-linking regulatory gate (Legal & Compliance, Risks,
   Roadmap)** — the "foregone opportunity" framing is resolved (linking
   is optional, not excluded); the underlying NCR question remains
   unresolved by desk research and gates the feature's ship date.

4. **Child-development/age-appropriateness risk (Success Criteria,
   Risks, Validation Strategy)** — the late-penalty mechanic's design has
   changed (parent-only, child-invisible), narrowing but not eliminating
   this risk; the required expert review has still not been commissioned.

5. **Subscriber-count discrepancy (Revenue & Costs)** — unresolved,
   carried forward unchanged.

6. **Market & Competition and Curriculum Design evidentiary thinness
   (new, surfaced by this cycle's reconstruction)** — both sections were
   already bare pointers as far back as v9, with the fuller detail that
   may once have existed in v8 or earlier not accessible to this or any
   future cycle unless independently re-supplied by the user. Curriculum
   Design's Confidence is explicitly downgraded to Low as a result. The
   third named competitor's identity and the specific free/paid feature
   split (Value Proposition) are newly named Outstanding Questions
   arising directly from this reconstruction.

7. **Request-for-payment feature inconsistency — RESOLVED in v11**,
   retained for audit-trail continuity.

8. **90-day vs. annual funnel tension — RESOLVED in v10**, retained for
   audit-trail continuity.

9. **Pre-link independent-registration carve-out — RESOLVED in v14 by
   removal**, retained for audit-trail continuity.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Low | **Evidence:** Supported

**Disclosed limitation, stated up front:** this section was already a
bare pointer at `BusinessCase_v9.md` ("Unchanged from v8," with no
substantive content reproduced there either), and `BusinessCase_v8.md`
is not among this cycle's authorized inputs. What follows reflects
everything actually available to this reconstruction — the case study's
own framing and v9's own cross-reference — not an invented fuller
description.

Per the case study (verbatim, `00_CaseStudy.md`): "Education needs to be
incorporated and designed to appeal to the respective age demographic."
This is the only first-party framing of the curriculum requirement
available to this reconstruction. MiniMoney's curriculum must span a
12-year age range (6-18) — a substantial instructional-design challenge
given how differently a 6-year-old and an 18-year-old engage with
financial concepts.

As of `BusinessCase_v9.md`, four items were named as explicitly
unresolved, and no clarification or research finding between v10 and v14
addresses any of them:

1. **Age-band curriculum splits** — how the 6-18 range divides into
   distinct instructional tiers is not specified in any available input.
2. **Instructional format** — whether lessons are video, interactive,
   gamified-quiz, text-based, or a mix is not specified.
3. **Standards alignment** — whether content maps to any South African
   national curriculum (e.g. CAPS) or recognized financial-literacy
   standard is not specified.
4. **Content authorship** — who writes and reviews the curriculum
   (in-house, licensed, or expert-commissioned) is not specified.

The child-development/age-appropriateness reviewer required since v9 to
assess the late-penalty mechanic (see Risks, Success Criteria) is
adjacent to, but formally distinct from, whatever review this section's
own content would eventually need — one assesses a mechanic's
psychological impact, the other would assess instructional-content
design. Neither has been engaged.

**Confidence is explicitly downgraded from Medium to Low on
reconstruction.** Writing this section out in full, rather than leaving
it as a "carried forward" pointer, makes clear that its actual
evidentiary base consists of one sentence from the original case study
and four named-but-undetailed open questions — materially thinner than a
Medium tag implied when the section was invisible behind a pointer. Per
Playbook Entry 3, this is stated explicitly rather than left for a
future reviewer to discover on their own. Status remains Partial:
something concrete exists (the four named gaps, the age-demographic
requirement), but no actual curriculum design content has been supplied
in any input available to this case.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Preserved from `BusinessCase_v14.md`, unchanged by this cycle. Since a
minor cannot register, or have any data processed, without a parent
acting as custodian from the outset, the registration-triggers-POPIA
question that drove earlier downgrades can no longer arise in
MiniMoney's actual design; `ResearchFindings_v3.md`'s statutory research
remains valid, sourced research but no longer applies to any live
feature. Confidence is held at Medium, not raised to High, for reasons
unrelated to that resolved question: the technical mechanism for the
(now-universal) consent gate is still undocumented; the two explicit
user risk-accepted assumptions (POPIA Section 14 retention sufficiency;
exam-bonus mechanic's no-schools-data-privacy-dimension assumption)
remain accepted but unreviewed by a specialist; Google Play's Families
Policy loyalty-point disclosure requirement and Apple's Kids Category
IAP-currency question remain open; the confirmed absence of ARB/NCR
precedent for "payslip"/"invoice"/"late penalty" terminology applied to
minors is unchanged. A residual item remains open: whether a distinct
post-registration, pre-budget-link stage still exists within the now
fully parent-supervised flow, and if so, whether a narrower version of
the practice-data-as-personal-information question persists within it.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 52% (67/130),
  confirmed unchanged from v14 by this cycle's full recomputation.

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.

- **No section consists solely of an "Unchanged from vN, not
  reproduced" pointer:** **Yes — this cycle's specific mandate.** All ten
  previously bare-pointer sections (Problem, Opportunity, Objectives,
  Success Criteria, Stakeholders, Target Users/Customers, Value
  Proposition, Market & Competition, Constraints, Curriculum Design) now
  contain full, self-contained substantive text. Two of the ten (Market &
  Competition, Curriculum Design) were already thin at their last fully
  accessible version (v9) and remain genuinely limited by that fact —
  this is disclosed explicitly within each section and in Critical Gap
  #6, not concealed.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
remains 52%, confirmed unchanged by full recomputation — this cycle is a
self-containment and traceability fix, not a new information event, and
does not by itself advance the score. A v16 would need: the actual
specialist legal opinion obtained; resolution of the family-vs-child
install-count and subscriber-count discrepancies; the account-linking
opt-in UX flow documented; the required child-development review
conducted; and, newly surfaced by this cycle, actual curriculum-design
content (age-band splits, format, standards alignment, authorship), the
free/paid feature-split detail for Value Proposition, and the third
named competitor's identity — to meaningfully advance the Readiness
Score beyond this cycle's completeness-only improvement.
