# Business Case: MiniMoney — v10

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v9.md` (prior version), and
> `Clarifications_v10.md` (user-supplied answers to v9's five remaining
> open items, 2026-07-08). This document is self-certified against the
> Incubator completion gate.

> **Changes from v9 — summary of what this revision addresses:**
> `Clarifications_v10.md` resolves four of v9's five remaining open
> items outright (subscription price: R59.99/month, up to 4 children per
> family account; legal-opinion trigger: event-based — commissioned once
> a stable working model exists and before any pilot testing begins; the
> 90-day-vs-annual-target tension: the 100/day figure is confirmed as a
> **floor**, not a flat-rate target, with intended growth above it,
> reconciling it with the 15,000-in-90-days aspiration; and the n=10
> interview bounding is accepted as-is, non-representative, no
> retroactive methodology documentation planned). The fifth item — the
> late-penalty mechanic — is not merely clarified but **redesigned**,
> and this revision corrects, rather than supplements, every prior
> section that described it as a penalty the child incurs or sees. This
> is stated plainly: versions v5 through v9 were inaccurate on this
> specific point, including Risks' language that "a minor is financially
> penalized for the parent's own delay" — that sentence no longer
> describes the current design and is retracted, not merely appended to,
> below. A specific internal-consistency question raised by
> `Clarifications_v10.md` — whether the previously-described minor-facing
> "request for payment" prompt for unsettled arrears remains coherent once
> the child has zero visibility into arrears/penalties — is flagged as an
> **unresolved internal inconsistency**, not silently carried forward.
> Enforcement of the redesigned parent-side penalty (how MiniMoney would
> confirm or compel actual parent payment, given it holds no banking-rail
> visibility) is explicitly **out of scope for this revision** — a
> separate Research House engagement is running in parallel on that
> specific question and will feed a later version.

## What Changed in v10 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

1. **Subscription price point — resolved.** R59.99/month, covering up to
   4 children per family account. Applied to Value Proposition, Business
   Model, and Financial Considerations, where it now permits an actual
   (if bounded) revenue model for the first time in this case's history.
   A new modeling nuance is surfaced as a byproduct: the "up to 4
   children per family" structure means revenue scales with **paying
   families**, not **installed children**, and this case has never
   established whether its existing 18,000-61,000 Year-1 install figures
   count families or individual child accounts. This is named as a new,
   specific Outstanding Question rather than silently assumed away.

2. **Legal-opinion trigger — resolved, event-based.** Commissioned once
   a stable working model exists and before any pilot testing with real
   families begins. This satisfies the Investment Committee's
   requirement for "a firm trigger," though the Incubator notes explicitly
   that an event-based trigger ("stable working model") is inherently
   softer than a calendar date — it is only as firm as the user's own
   discipline in judging when "stable" has been reached. This is flagged
   as a residual soft spot, not treated as fully equivalent to a dated
   milestone.

3. **90-day vs. annual funnel tension — resolved as floor-plus-growth.**
   100/day is confirmed as a floor for the first 90 days, with intended
   growth above it; 15,000-in-90-days is now understood as the
   aspirational total consistent with that growth trajectory, not a
   flat-rate calculation. Objectives' Status is upgraded this revision
   (see below) because this was the one item among the Investment
   Committee's six requiring outright resolution, and it has now
   genuinely received one — not merely been quantified, as in v9.

4. **Late-penalty mechanic — redesigned and corrected across every
   affected section.** The parent alone incurs the escalating penalty
   (5→6→7 Mbucks/week, pilot cap 3); the child has zero visibility into
   whether a penalty was charged or how much is owed. This is corrected,
   not supplemented, in Operations, Success Criteria, Risks, Legal &
   Compliance, Legal & Compliance — Child Data & Consent, Assumptions,
   Critical Gaps, and Outstanding Questions. The Incubator's assessment of
   how much this narrows the child-development risk is detailed in Risks
   below: substantially, but not to zero — residual pathways remain.

5. **Internal consistency flag — the minor-facing "request for payment"
   prompt feature.** This feature (present since `Clarifications_v5.md`,
   per `Clarifications_v10.md`'s own description) allows a minor to
   generate a request-for-payment prompt for unsettled arrears. Under
   the redesigned zero-visibility penalty model, this presupposes a
   level of child-facing arrears awareness the redesign now removes. The
   Incubator does **not** resolve this silently in either direction — it
   is named as an open design contradiction requiring a user decision,
   detailed in Operations and Outstanding Questions.

6. **n=10 interview evidence — user accepts the bounding as-is.** No
   retroactive methodology documentation is planned; the data point
   remains permanently bounded as non-representative per the standing
   instruction carried from v9.

7. **Enforcement mechanism for the parent-side penalty — explicitly out
   of scope this revision.** Flagged in Legal & Compliance, Operations,
   Risks, and Outstanding Questions as pending a separate, parallel
   Research House engagement (Engagement 2), distinct from the design
   clarification addressed here.

**Net effect on Readiness Score:** two sections move. **Objectives**
upgrades from Partial to Complete (the 90-day tension is now genuinely
resolved, not merely quantified). **Operations** downgrades from
Complete to Partial (the newly surfaced internal inconsistency in the
request-for-payment feature means the mechanic can no longer be
described as free of unresolved contradiction). **Value Proposition**
upgrades from Partial to Complete (the price-point gap was its only
named blocker). Financial Considerations, Business Model, and Legal &
Compliance remain Partial — each still has open items independent of
what this revision resolved (no funding ask/runway; the Mpoints/Apple
IAP-currency question; the specialist legal opinion itself remains
unobtained). **Readiness Score: 64/130 = 49%, up from 47% in v9.**

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
funds. **Subscription pricing is now set at R59.99/month, covering up to
4 children per family account.** Monetization is subscription-only at
launch, with advertising deferred to a possible post-launch V2. Real-
money in-app purchases remain parent-only; a minor cannot access any
part of the app without a pre-existing, consenting parent account.

**This revision incorporates the user's answers to four of v9's five
open items and a substantive redesign of the fifth.** The late-payment
penalty mechanic — previously described across v5-v9 as something a
minor incurs or is exposed to — is corrected: **the parent alone incurs
the escalating penalty; the child has no visibility into it whatsoever.**
This materially narrows, but does not eliminate, the child-development
risk the Investment Committee required a review for (see Risks). A
specific internal inconsistency surfaces as a result — a previously-
described feature letting the child request payment for "unsettled
arrears" presupposes visibility the redesign now removes — and is
flagged rather than silently carried forward. Enforcement of the
redesigned parent-side penalty (confirming or compelling actual payment,
given MiniMoney holds no banking-rail visibility) is a distinct, new
question, explicitly out of scope for this revision and routed to a
parallel Research House engagement. The Readiness Score rises to **49%
(64/130)**, up from 47% in v9 — a genuine, if modest, improvement driven
by two real resolutions (price point, the 90-day/annual tension) offset
by one section (Operations) losing its Complete status due to the newly
surfaced internal inconsistency. The Legal & Compliance Critical gap
remains open: the trigger for commissioning the specialist opinion is now
defined, but the opinion itself has not been obtained, and the
underlying legal uncertainty is unchanged.

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9. Parents lack a structured, automated system to teach
children (6-18) real-world financial concepts — earning, budgeting,
taxation/expenses, and payment mechanics — using real money in a
controlled, task-based framework. The n=10 interview finding (6/10
would-pay, 7/10 education-interested) stands, and per the user's explicit
acceptance in `Clarifications_v10.md`, remains permanently bounded as
non-representative, directional evidence — no retroactive methodology
documentation is planned, and the standing instruction from v9 (this data
point must not be used as if it were validated demand evidence in any
future modeling) continues unchanged. Status remains Partial for the same
reason as v9: a real, encouraging, directional signal, not an established
finding.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9. MiniMoney's differentiator remains the
payroll-simulation mechanic; no direct South African incumbent does what
MiniMoney does; the schools-partnership distribution channel remains a
parallel, unproven intended channel. Not directly addressed by
`Clarifications_v10.md`.

## Objectives

**Status:** Complete (upgraded from Partial) | **Confidence:** Medium
(upgraded from Medium — reasoning strengthened, tier unchanged) |
**Evidence:** Supported

The functional objective (budget → tasks → Mbuck/Mpoint earning → exam
bonus → invoice/payslip → payment confirmation → age-gated education) is
unchanged, with one correction: "escalating late-penalty" is no longer
listed as something the child experiences in this flow — the redesigned
mechanic sits entirely on the parent side and does not gate the child's
own progression through tasks, earning, or education content.

**This revision — the 90-day-vs-annual-target tension is resolved, not
merely quantified, per the user's clarification:** the 100/day figure is
confirmed as a **floor** for the first 90 days, with the explicit
intention to grow adoption above it. The 15,000-in-90-days figure is
therefore correctly understood as the aspirational total consistent with
growth above that floor across the window — not a flat 100/day
calculation, and not in tension with the annual funnel range once
understood this way. This is a genuine resolution: v9 could only quantify
the gap (15,000 ≈ 3.4x a linear reading of the annual range's low end);
this revision removes the apparent contradiction by clarifying that
15,000 was never intended as a linear-pace figure in the first place, and
100/day was never intended as the ceiling.

**Status upgraded to Complete** because this was the one item among the
Investment Committee's six requiring an actual user decision to resolve
(as opposed to analytical reconciliation), and that decision has now been
supplied. **Residual note, not a Status-blocking gap:** no explicit
growth curve (e.g., what rate of increase above the 100/day floor is
expected week-over-week) has been supplied — this would sharpen forecast
precision further but is not required to consider the stated tension
resolved.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9 for pilot success, curriculum engagement (30%,
unbenchmarked), operational health (65%, unbenchmarked), subscription
conversion (2%, correctly benchmarked against 1-3%), and retention (no
figure proposed).

**This revision — the family-relationship-strain success criterion
(added in v9 per Investment Committee requirement #5) is recalibrated,
not dropped, given the late-penalty redesign.** Because the child no
longer sees or bears the penalty directly, the original framing
(tracking child-facing distress from an escalating, visible,
real-money-denominated penalty) no longer matches the actual mechanic.
The Incubator recalibrates the criterion's scope to two narrower,
still-unmeasured candidate metrics: (a) parent-reported stress or
household friction associated with an accumulating parent-side
obligation (an indirect pathway to the child, distinct from the direct
one the Investment Committee originally flagged); and (b) child-reported
experience of **payment delay itself** — independent of the invisible
penalty mechanics, a child can still notice that their payslip payout
arrived late, and this alone may carry its own smaller-scale
trust/relationship signal worth tracking. Neither metric currently
exists in measurable form; this remains an open requirement for the
planned 20-50 family pilot. Status remains Partial.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9. Not directly addressed by `Clarifications_v10.md`.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9, with one addition: the subscription's "up to 4
children per family" structure clarifies that the paying customer unit is
the **family account**, not the individual child — relevant to how this
case should model its addressable market and conversion funnel going
forward (see Financial Considerations).

## Value Proposition

**Status:** Complete (upgraded from Partial) | **Confidence:** Medium |
**Evidence:** Supported

For parents: an automated system that turns household tasks into a
structured payroll-like experience with a built-in financial literacy
curriculum, now available at a stated price of **R59.99/month, covering
up to 4 children per family account**. For children: a "real job"
simulation paid out via the parent's own bank transfer, tied to
age-appropriate lessons, alongside a separate cosmetic-reward system
(Mpoints). **This revision resolves the section's sole named blocker:**
a specific South African Rand price point now exists, replacing the
MoneyTime SA R995/year anchor as a reference point only — MiniMoney's
own price is no longer inferred, it is stated. At R59.99/month
(≈R719.88/year), MiniMoney prices below MoneyTime SA's R995/year single-
child anchor, and materially below it on a per-child basis for families
using the full 4-child allowance (≈R180/child/year) — a meaningfully
different value proposition (family-plan economics) than the earlier
under-anchor concern contemplated, worth noting as a competitive
positioning point rather than only a risk. Status upgraded to Complete:
the section's only outstanding item (a price point) is resolved, and the
rest of its content was already substantively described.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9. The new price point sharpens the MoneyTime SA
comparison (see Value Proposition) but does not change this section's
Status — the underlying competitive landscape description is otherwise
unchanged.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Structurally confirmed: subscription-only at launch (R59.99/month, up to
4 children/family), ads deferred to V2. **This revision resolves the
price-point gap named in v9**, but the section remains Partial for a
reason independent of price: the Mpoints/Apple IAP-currency question
remains unresolved, unchanged from every prior version. A new,
Business-Model-specific consideration surfaces from the family-plan
structure: at up to 4 children per subscription, a family with multiple
qualifying children pays no more than a single-child family, which is a
deliberate underlying assumption about acceptable revenue-per-install
economics that should be stated explicitly rather than left implicit —
named in Assumptions and Outstanding Questions below.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9's build-timeline/engineering-cost reconciliation
(different production models, not a raw contradiction; no external-help
budget ceiling stated). **New this revision — a first pass at revenue
modeling is now possible given the resolved price point,** presented here
with an explicit reconciliation note:

`Clarifications_v10.md` references an existing Year-1 paying-subscriber
range of "360-2,440." The Incubator cannot independently reconcile this
upper figure (2,440) from the inputs available in this case: applying the
documented conversion benchmarks (a 2% target, within a stated 1-3%
external range) to the documented annual install range (18,000-61,000)
produces:

- At 1% conversion: 180 subscribers (low end of install range) to 610
  (high end).
- At 2% (the stated target): 360 to 1,220 subscribers.
- At 3% (top of stated external range): 540 to 1,830 subscribers.

None of these combinations independently produce 2,440. Rather than
adopt the externally-cited figure uncritically, the Incubator flags this
as an **unreconciled discrepancy** and proceeds on the range it can
verify from this case's own documented inputs: **180-1,830 subscribing
families in Year 1**, with **360-1,220** as the range specifically implied
by the 2% target conversion rate. At R59.99/month (≈R719.88/year/family),
this implies approximate Year-1 subscription revenue of:

- Verified range (1-3% conversion): **≈R129,600 - R1,317,400**
- Target-case range (2% conversion): **≈R259,200 - R878,300**

This is a **family-level** revenue estimate; it does not yet correct for
whether the underlying 18,000-61,000 install figures count children or
family accounts (see Outstanding Questions) — if a meaningful share of
installs represent a second or third child within an already-subscribed
family, actual paying-family counts (and thus revenue) could be lower
than this estimate implies. CAC and curriculum-production cost remain
unresolved, unchanged from v9.

## Operations

**Status:** Partial (downgraded from Complete) | **Confidence:** Medium
(downgraded from High) | **Evidence:** Supported

**This revision corrects, rather than supplements, the mechanic
description carried since v5:** the late-payment penalty (5→6→7
Mbucks/week, pilot cap 3) is incurred entirely by the **parent**, not the
child, and the child has **no visibility whatsoever** into whether a
penalty was charged or how much is owed — no UI element, statement, or
report reflects it to the minor's account. Every prior description
implying the child sees or bears this penalty is retracted, not merely
supplemented.

**Status downgraded this revision, not upgraded, because a genuine
mechanical inconsistency has surfaced as a direct result of this
correction — this is precisely the kind of gap Operations' Complete
status previously did not have to account for.** Per `Clarifications_v10.md`,
a feature has existed since `Clarifications_v5.md` allowing a minor to
generate a "request for payment" prompt after month 1, and every month
thereafter, for unsettled arrears. This presupposes the child has enough
visibility into arrears to know when to invoke the feature. Under the
redesigned zero-visibility penalty model, this is now an **open design
contradiction, not a resolved mechanic**, and the Incubator does not
silently carry both descriptions forward as if compatible. Two readings
are possible, and only the user can choose between them:

1. **"Arrears" in this feature refers only to the child's own unpaid base
   payslip earnings** (an amount the child should always be able to see,
   distinct from the invisible parent-side penalty amount). Under this
   reading, the feature remains coherent, but its description requires
   correction: it concerns overdue wages, not "arrears" inclusive of any
   penalty.
2. **"Arrears" as previously described included penalty-inclusive
   figures.** Under this reading, the feature as designed is no longer
   coherent and requires either removal or redesign — e.g., limiting the
   child's prompt to a reminder about unpaid base wages only, with no
   reference to penalty amounts or escalation.

This is not a cosmetic wording issue: it determines what data the child's
account is permitted to display, which is a Legal & Compliance and Child
Data & Consent question as much as an Operations one (see those
sections). Operations can no longer be described as mechanically
unambiguous until this is resolved — hence the downgrade to Partial.

**Also unchanged in scope:** enforcement of the redesigned parent-side
penalty (confirming or compelling actual parent payment, given MiniMoney
has no banking-rail visibility or fund custody) is explicitly **out of
scope for this revision**, per the delegation task — this is the subject
of a separate, parallel Research House engagement (Engagement 2) and will
be incorporated into a later version, not invented here.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9. Not directly addressed by `Clarifications_v10.md`.

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This section remains flagged Critical.** The underlying legal
uncertainty — money-transmitter characterization of the invoice/payment
trigger; the absence of ARB/NCR precedent for "payslip"/"invoice"/"late
penalty" terminology applied to minors; POPIA Section 34/14 sufficiency —
is **unchanged by this revision**. What changes is sequencing clarity:

**Trigger — resolved, event-based.** Per `Clarifications_v10.md`, the
specialist POPIA/ARB legal opinion will be commissioned once a stable
working model exists, and before any pilot testing with real families
begins. This satisfies the Investment Committee's requirement for a
"firm trigger." The Incubator flags one residual softness explicitly:
an event-based trigger ("stable working model") is judged, not dated —
it depends on the user's own assessment of when that threshold is
reached, and carries more slippage risk than a calendar date would. This
is noted as a materially better answer than v9's open gap, not as fully
equivalent to a fixed deadline.

**Redesigned mechanic implications.** The late-penalty mechanic being
parent-incurred and parent-invisible-only changes, but does not resolve,
the terminology-to-minors risk: "invoice," "payslip," and "arrears"
language is still applied in a product explicitly directed at minors as
young as 6, regardless of who bears the financial consequence of late
payment. The specialist opinion's scope (money-transmitter
characterization; terminology risk) is unchanged by the redesign.

**Enforcement question — explicitly out of scope this revision.** How
MiniMoney would confirm or compel actual parent payment of the
parent-side penalty, given it holds no banking-rail visibility or fund
custody, is a distinct, new legal/operational question not addressed
here — routed to a parallel Research House engagement per the delegation
task.

The feature-level gating plan established in v9 (financial-trigger
features locked behind the opinion; foundational rails may proceed in
parallel) is unchanged and still applies.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Carried forward largely unchanged from v9: regulatory risk (Critical);
trust/enforcement risk; dispute-escalation risk; terminology/perception
risk; advertising/child-data risk; Fintech Advance content risk;
competitive risk; monetization-execution risk; app-store policy risk;
platform-concentration risk; adoption/forecasting risk; engineering-cost
estimation risk; legal-opinion-deferral risk (now narrowed to the
softness of an event-based, rather than dated, trigger).

**Child-development/age-appropriateness risk — substantially narrowed
this revision, not eliminated.** The Investment Committee required this
review because, under the pre-redesign mechanic, a child directly
experienced an escalating, real-money-denominated penalty across a
12-year age span (6-18). Under the redesign:

- **What is resolved:** the child no longer directly bears or perceives
  the escalating penalty amount or its increase over time. The most
  direct pathway to the risk the Investment Committee named — a child
  watching a real-money penalty grow against them for a delay that is not
  their fault — no longer exists as described.
- **What remains, explicitly named rather than assumed away:**
  1. **Indirect effects.** A parent managing an accumulating penalty
     obligation may exhibit stress, irritability, or conflict a child can
     still perceive, even without visibility into the mechanism causing
     it.
  2. **Payment-delay visibility, distinct from penalty visibility.** The
     redesign removes the child's visibility into the *penalty*; it does
     not necessarily remove the child's experience of the underlying
     late payment itself (a delayed payslip payout). A child can still
     notice "I haven't been paid yet" independent of whether they know
     why or how much extra the parent now owes as a result.
  3. **The request-for-payment feature's unresolved status** (see
     Operations) — if "arrears" in that feature was ever meant to include
     penalty-inclusive figures, its continued existence in any form would
     reintroduce exactly the child-facing visibility the redesign was
     meant to remove.
- **Net assessment:** the risk is meaningfully smaller in scope and
  severity than the one the Investment Committee originally flagged, but
  a child-development/age-appropriateness review remains warranted — its
  required scope is now narrower (indirect/relational effects and
  payment-delay perception, not direct exposure to an escalating
  penalty amount), not eliminated as a requirement.

**Objectives-tension risk — resolved this revision**, per Objectives
above; retained here only as a closed item for audit-trail continuity,
not as a standing risk.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9: parent-direct payment, SA launch jurisdiction,
universal consent gate, Android-first, Mbucks/Mpoints dual currency,
7-Mbuck cap with 3-Mbuck pilot cap, Fintech Advance scoping, the two
explicit POPIA/exam-bonus risk acceptances, the fixed Mbucks-to-Rand peg.

**Corrected this revision:** the assumption previously stated as "the
late-penalty mechanic's intended nature as a behavioral nudge rather than
a strictly-collected financial detriment" no longer accurately describes
the mechanic and is retracted. The corrected assumption: **the penalty is
now a real, strictly-incurred financial detriment to the parent** (not a
behavioral nudge framing directed at the child), with the child
insulated from both its existence and its amount by design.

**New this revision:** it is assumed, but not confirmed by the user, that
the existing 18,000-61,000 Year-1 install figures represent distinct
**family accounts** rather than distinct **child installs** — a
distinction that did not matter before the "up to 4 children per
subscription" pricing structure existed, but now directly affects revenue
modeling (see Revenue & Costs, Financial Considerations). This is the
Incubator's own inference surfaced by the price-point clarification, not
a user-confirmed fact.

The engineering-cost/build-timeline assumption from v9 (external
expertise engaged sparingly relative to the agency-quote range) remains
unchanged and unconfirmed.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9: solopreneur venture, AI-assisted ("vibe coding")
development, external technical expertise on-demand, ~3-month directional
build timeline. Not directly addressed by `Clarifications_v10.md`.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in overall structure from v9's feature-level gating plan
(foundational rails may proceed immediately; financial-trigger features
locked behind the specialist legal opinion). **This revision adds the
resolved, event-based legal trigger directly into the sequencing logic:**
the legal-opinion gate now has a defined starting condition (a stable
working model, prior to any pilot) rather than an undefined one. Status
remains Partial: no dated milestone plan, phased budget, or external-help
budget ceiling has been supplied, and "stable working model" itself is a
judgment call, not a checkable milestone.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This revision provides the case's first actual revenue estimate,**
detailed in Revenue & Costs above: approximately R129,600-R1,317,400
Year-1 subscription revenue on the verified 1-3% conversion range
(R259,200-R878,300 on the 2% target case specifically), with an explicit,
unreconciled discrepancy flagged against `Clarifications_v10.md`'s own
cited 360-2,440 subscriber range. This is real progress — the
subscription-price-point gap that was, per v9, "the single most direct
blocker to modeling this venture's actual unit economics" is now
resolved. **Status remains Partial, not Complete, for reasons independent
of price:** no funding ask, runway, or cost-side numeric projection
exists anywhere in this case; the family-vs-child install-count ambiguity
(Assumptions, Outstanding Questions) means even the new revenue range
carries a real, unquantified downside risk; and the external-help budget
ceiling for engineering costs remains unstated.

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

1. **Legal validation** — trigger now defined (event-based, pre-pilot);
   the recommended low-cost preliminary legal read (adopted by the
   Incubator in v9) remains an open recommendation, not yet a decision.
2. **Primary user-research validation** — the n=10 bounding is accepted
   as final per the user's clarification; no further methodology
   documentation is planned.
3. **Child-development/age-appropriateness review — required, scope
   narrowed this revision.** Per Risks above, the review's required focus
   shifts from direct child exposure to an escalating visible penalty
   (largely resolved by the redesign) to indirect/relational effects and
   payment-delay perception (residual, smaller-scope risk). This does not
   remove the requirement; it sharpens what the review needs to examine.
4. **Trust/enforcement and dispute-mechanism validation** — unchanged
   from v9, with the enforcement question for the redesigned parent-side
   penalty now explicitly routed to a separate Research House engagement,
   out of scope here.
5. **Market/demand validation** — unchanged from v9.
6. **Pricing/conversion validation** — now has an actual price to
   validate against (R59.99/month); still requires empirical testing
   against the modeled 1-3% conversion range.
7. **Curriculum validation** — unchanged from v9.
8. **90-day target reconciliation** — resolved this revision; no longer
   an open validation item.

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in content and treatment from v9. Per `Clarifications_v10.md`,
the user accepts the Incubator's proposed bounding of the n=10 data point
(non-representative, [Supported/Low-Medium] evidentiary weight) rather
than commissioning retroactive methodology documentation — this is now
the case's final position on this data point absent a future pilot or
structured survey superseding it.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this revision (removed from the open list):** subscription
price point (R59.99/month, up to 4 children/family); legal-opinion
trigger (event-based, pre-pilot); 90-day-vs-annual target tension
(floor-plus-growth framing); n=10 interview methodology documentation
decision (declined; bounding accepted as final).

**New this revision:**

- Do the existing 18,000-61,000 Year-1 install figures represent distinct
  family accounts or distinct child installs? This directly determines
  how much the "up to 4 children per subscription" pricing structure
  should discount the revenue estimates in Revenue & Costs.
- Does the "request for payment" prompt feature (child-facing, for
  unsettled arrears, described since `Clarifications_v5.md`) refer only
  to the child's own unpaid base wages (in which case it remains coherent
  under the redesign, with corrected wording), or did it previously
  include penalty-inclusive figures (in which case it requires removal or
  redesign)? This cannot be resolved without a user decision.
- What is the actual enforcement mechanism for the redesigned parent-side
  penalty, given MiniMoney holds no banking-rail visibility or fund
  custody? Explicitly out of scope for this revision — pending a
  separate, parallel Research House engagement.
- Is the Incubator's unreconciled discrepancy between its own computed
  subscriber range (180-1,830) and `Clarifications_v10.md`'s cited
  360-2,440 range attributable to a different conversion-rate assumption
  the user has in mind but has not yet stated? Worth clarifying before
  this range is used in any further financial modeling.

**Still open, carried forward unchanged from v9** (see `BusinessCase_v9.md`
for the full itemized list): the recommended preliminary legal read's
adoption decision; fund custody mechanics; consent-gate technical
mechanism; task verification; dispute-escalation beyond 48 hours;
payment-routing timeline; late-penalty cap rationale; Fintech Advance
scope; exam-bonus data source; Mbucks-peg flexibility; curriculum
age-band splits; app-store policy sub-questions; MoneyAfrica Kids'
unpublished premium price; whether informal engineering-cost quotes will
be sought; the external-help budget ceiling; the schools-partnership
channel's timeline/target school count/resourcing plan.

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted.

| Section | Status | Weight | Points |
| - | - | - | - |
| Executive Summary | Partial | 1x | 2 |
| Problem | Partial | 1x | 2 |
| Opportunity | Partial | 1x | 2 |
| Objectives | **Complete (was Partial)** | 1x | **5** |
| Success Criteria | Partial | 1x | 2 |
| Stakeholders | Partial | 1x | 2 |
| Target Users/Customers | Partial | 1x | 2 |
| Value Proposition | **Complete (was Partial)** | 1x | **5** |
| Market & Competition | Partial | 1x | 2 |
| Business Model | Partial | 1x | 2 |
| Revenue & Costs | Partial | 1x | 2 |
| Operations | **Partial (was Complete)** | 1x | **2** |
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

Points earned: **64** (up from 61 in v9: +3 Objectives, +3 Value
Proposition, -3 Operations).

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130** (unchanged).

**Readiness Score = 64 / 130 = 49.2%, rounded to 49%. Up from 47% in v9.**

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → **49% (v10).**

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB legal opinion remains unobtained. A firm
   trigger now exists (event-based: stable working model, pre-pilot),
   resolving Investment Committee requirement #1 in full, but the
   underlying legal uncertainty (money-transmitter characterization;
   terminology-to-minors risk) is unchanged, and an event-based trigger
   is softer than a dated one.

2. **Family-vs-child install ambiguity (new, Financial Considerations,
   Revenue & Costs, Assumptions)** — the existing Year-1 install range
   has never distinguished family accounts from child installs; the "up
   to 4 children per subscription" pricing structure makes this
   distinction materially relevant to revenue modeling for the first
   time, and it remains unresolved.

3. **Request-for-payment feature inconsistency (new, Operations, Risks,
   Legal & Compliance — Child Data & Consent)** — a child-facing feature
   presupposing arrears visibility may now conflict with the redesigned,
   zero-visibility penalty mechanic. Unresolved; requires a user
   decision on whether "arrears" in that feature ever included
   penalty-inclusive figures.

4. **Late-penalty enforcement mechanism (new, Legal & Compliance,
   Operations, Risks)** — how MiniMoney confirms or compels actual parent
   payment of the redesigned penalty, given no banking-rail visibility,
   is unresolved and explicitly out of scope for this revision — pending
   a parallel Research House engagement.

5. **Child-development/age-appropriateness risk (Success Criteria, Risks,
   Validation Strategy)** — substantially narrowed by the penalty
   redesign (the child no longer directly bears or sees the penalty), but
   not eliminated (indirect parental-stress effects, payment-delay
   perception). The required expert review's scope is now narrower but
   still required; it has not yet been conducted in any version of this
   case.

6. **Subscriber-count discrepancy (new, Revenue & Costs)** — the
   Incubator's independently computed Year-1 subscriber range (180-1,830)
   does not reconcile with `Clarifications_v10.md`'s cited 360-2,440
   figure; the source of this discrepancy is unclear and should be
   clarified before either figure is used in further financial modeling.

7. **90-day vs. annual funnel tension — RESOLVED this revision**, no
   longer a Critical Gap; retained in the Objectives section for
   audit-trail continuity only.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v9. Not addressed by `Clarifications_v10.md`.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in substance from v9: the universal consent-gate model; the two
explicit user risk-accepted assumptions (POPIA Section 14 retention
sufficiency; exam-bonus mechanic's no-schools-data-privacy-dimension
assumption); Google Play's Families Policy loyalty-point disclosure
requirement; Apple's Kids Category requirements and the unresolved IAP-
currency question; the confirmed absence of ARB/NCR precedent for
"payslip"/"invoice"/"late penalty" terminology applied to minors.

**This revision — directly relevant to the redesigned penalty mechanic:**
the fact that the child now has zero visibility into the penalty
narrows what minor-facing account data must reflect at all — the
data-retention/deletion pipeline (POPIA Section 14) need only ever
surface the penalty to the parent, not the child, which is arguably a
**simpler** data-exposure surface than the pre-redesign version. However,
the unresolved request-for-payment feature question (Operations, Risks)
means this simplification cannot yet be confirmed as complete: if that
feature is found to require penalty-inclusive arrears data to function as
originally described, the minor-facing data surface would need to
include it after all, reintroducing the more complex exposure question
this redesign was intended to close off. This section's Status therefore
remains Partial, contingent on that open item's resolution.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Child Data & Consent are both Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 49% (64/130), up from
  47% in v9. Progression: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) → 40%
  (v7) → 47% (v8) → 47% (v9) → 49% (v10).

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle to reflect the
  redesigned penalty mechanic and the new revenue-modeling assumptions.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
rises to 49% from 47% in v9 — real progress from two genuine resolutions
(subscription price point, the 90-day/annual tension), partially offset
by Operations losing its Complete status due to a newly surfaced internal
design inconsistency (the request-for-payment feature) that this
revision's redesign correction brought to light rather than created. A
v11 would need: (a) the user's decision on the request-for-payment
feature's coherence; (b) resolution of the family-vs-child install-count
ambiguity; (c) the Research House enforcement-mechanism findings; (d) the
actual specialist legal opinion (or at minimum the recommended
preliminary read) obtained; and (e) the required, now-narrower-scope
child-development review conducted, to meaningfully advance the Readiness
Score further.
