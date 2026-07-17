# Business Case: MiniMoney — v11

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v10.md` (prior version),
> `Clarifications_v11.md` (user decision on v10's request-for-payment
> internal-consistency flag, 2026-07-08 off-cycle), and
> `ResearchFindings_v2.md` (Research House, Engagement 2 — enforcement
> mechanisms for the redesigned parent-side late-penalty). This document
> is self-certified against the Incubator completion gate. This revision
> supersedes a stray/incomplete `BusinessCase_v11.md` found already
> present at this path before this engagement began — that file was not
> an input this Incubator was instructed to read or build on, was
> inconsistent with the two items this delegation actually specified,
> and left `ExpertRoster.md`, `reviews/DevilsAdvocate.md`, and
> `ExecutiveSummary.md` unregenerated. It has been overwritten in full
> rather than merged with, so this version's content can be traced
> entirely to the four files this delegation authorized.

> **Changes from v10 — summary of what this revision addresses:**
> Two inputs land this cycle. (1) `Clarifications_v11.md` resolves v10's
> flagged Operations/Child Data & Consent internal inconsistency: the
> user confirms that "arrears" in the child-facing "request for payment"
> feature previously meant the penalty-inclusive figure (v10's Reading
> #2), which makes the feature incoherent under the redesigned
> zero-child-visibility penalty model. **Decision: remove the feature
> entirely, for now** — not a redesign limiting it to base-wage-only
> arrears, a full removal, with reintroduction left open as a future
> decision, not assumed. Every reference to this feature is removed
> across Operations, Risks, Legal & Compliance — Child Data & Consent,
> Outstanding Questions, and Critical Gaps, per instruction, rather than
> left as a stale description. (2) `ResearchFindings_v2.md` (Research
> House Engagement 2) addresses the enforcement-mechanism question v10
> explicitly deferred: read-only account-linking options exist (Stitch,
> Mono) but are assessed as later-stage/V2+ features given South
> Africa's immature Open Finance framework, enterprise-sales-led vendor
> access, and unconfirmed local pricing/coverage; comparable non-custodial
> apps (FamZoo, Bomad) confirm honor-system self-reporting is standard
> category practice, not a MiniMoney-specific weakness; and the deeper
> question of legal enforceability of the arrears/penalty balance itself
> (domestic-agreement presumption, minor contractual-capacity rules)
> remains genuinely open and is explicitly deferred by Research House to
> the specialist legal opinion already planned for this case. Per
> standing instruction, this vendor output is treated with the
> Incubator's own scrutiny throughout — it can support raising tags to
> Supported, never to Verified.

## What Changed in v11 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

1. **Request-for-payment feature — removed entirely, resolving v10's
   flagged internal inconsistency.** The user confirmed the feature's
   "arrears" language previously included penalty-inclusive figures, so
   it cannot coexist with the redesigned zero-child-visibility penalty.
   Rather than redesign it to reference base-wage-only arrears, the user
   chose full removal, "for now," with reintroduction left open as a
   future, not-yet-made decision. All descriptions of this feature are
   removed from Operations, Risks, Legal & Compliance — Child Data &
   Consent, and the Critical Gaps/Outstanding Questions lists.

2. **Operations — assessed for restoration to Complete.** The
   contradiction that caused v10's downgrade (a feature presupposing
   child-facing arrears visibility the redesign had just removed) no
   longer exists once the feature itself is removed — the mechanic is
   again internally coherent. The Incubator restores Operations to
   **Complete**. Removal is not treated as risk-free, however: it
   surfaces a genuinely new, previously-unasked question — with the
   feature gone, the case now describes **no** in-app mechanism at all
   for a child (or parent) to flag an overdue base-wage payslip payment.
   This is named as a new Outstanding Question, not folded silently into
   "resolved," per the standing instruction to check whether a
   correction's ripple effects are fully closed out before marking a
   section clean.

3. **Enforcement-mechanism research (Research House Engagement 2) —
   substantially clarifies, does not fully resolve, Critical Gap #4.**
   Applying the Incubator's own scrutiny (per standing instruction, this
   vendor output is never accepted uncritically and never reaches
   Verified-tier): the *technical/product* question — what near-term
   verification mechanism, if any, MiniMoney should build — is now
   reasonably well-answered: continue the existing honor-system
   self-report model (confirmed, at High confidence from multiple
   independent sources, to be standard practice among comparable
   non-custodial apps — FamZoo, Bomad); treat read-only account-linking
   (Stitch, Mono) as an explicit later-stage/V2+ feature, not initial-build
   scope, given South Africa's Open Finance framework is not yet mandated
   (effective date cited as 2026, full compliance targeted 2028) and
   neither vendor publishes confirmed South African pricing; optionally
   evaluate PayShap Request reference-number transcription or
   proof-of-payment document-fraud-detection APIs as lower-cost
   intermediate steps. The *legal* question — whether the arrears/penalty
   balance has real contractual enforceability, given South African
   common law's domestic-agreement presumption and minors' limited
   contractual capacity — remains genuinely open. Research House itself
   states it is not qualified to answer this and routes it to the
   specialist legal opinion already planned for this case. Legal &
   Compliance's Critical status is therefore **unchanged (Partial)**, but
   its documented scope is sharpened: the specialist opinion must now
   also address minor contractual-capacity implications for the
   underlying payslip obligation and whether MiniMoney's "agreed
   condition of budget setup" framing could overcome the domestic-
   agreement presumption.

**Net effect on Readiness Score:** one section moves. **Operations**
upgrades from Partial to Complete (+3 points). No other section's Status
changes this revision — Legal & Compliance and Child Data & Consent
remain Partial for reasons the research findings sharpen but do not
resolve (the specialist opinion itself is still unobtained). **Readiness
Score: 67/130 = 51.5%, rounded to 52%, up from 49% in v10.**

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
purchases remain parent-only; a minor cannot access any part of the app
without a pre-existing, consenting parent account. The late-payment
penalty mechanic is incurred entirely by the parent (5→6→7 Mbucks/week,
pilot cap 3); the child has zero visibility into it.

**This revision resolves one internal design inconsistency and
substantially clarifies, without fully resolving, one Critical Gap.**
The child-facing "request for payment" feature — flagged in v10 as
presupposing arrears visibility the redesigned penalty model had just
removed — is now confirmed to have previously meant penalty-inclusive
arrears, and is therefore **removed entirely, for now**, per the user's
direct decision; reintroduction in a redesigned, base-wage-only form is
left open as a future possibility, not assumed. This restores Operations
to Complete status but surfaces a new, smaller open question: the case
now describes no in-app mechanism at all for a child to flag an overdue
payslip payment. Separately, Research House's second engagement (desk
research, not a legal opinion) clarifies that MiniMoney's honor-system
approach to verifying parent payment is standard, unremarkable practice
among comparable non-custodial allowance apps, and that fuller
technical verification (read-only bank-account linking) is realistically
a later-stage feature for South Africa's current regulatory and vendor
landscape — but it explicitly does not and cannot resolve whether the
parent-side arrears/penalty balance is legally enforceable, a question
that remains with the still-unobtained specialist legal opinion. The
Readiness Score rises to **52% (67/130)**, up from 49% in v10 — driven
by Operations' single restoration to Complete. The Legal & Compliance
Critical gap remains open: the trigger for commissioning the specialist
opinion is defined and the opinion's required scope is now better
understood, but the opinion itself has not been obtained, and the
underlying legal uncertainty is unchanged.

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed by `Clarifications_v11.md` or
`ResearchFindings_v2.md`.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision.

## Objectives

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. The two recalibrated child-development metrics
(parent-reported stress; child-reported payment-delay perception) remain
unaffected by this revision's removal of the request-for-payment feature
— neither metric depended on that feature's existence, since both are
proposed as pilot survey instruments, not in-app telemetry tied to it.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision.

## Value Proposition

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. **One relevant addition:** Research House's
Engagement 2 comparable-app research (FamZoo, Bomad, GoHenry, Greenlight)
sharpens the existing competitive landscape by confirming a clean
architectural split in the category — money-mover platforms (GoHenry,
Greenlight) versus honor-system trackers (FamZoo, Bomad) — with
MiniMoney sitting in the latter group. This is offered strictly as
context for the enforcement-mechanism question this engagement was
scoped to research (see Operations, Legal & Compliance), not as a
competitive-landscape reassessment — this case's existing competitive
positioning claims are outside this revision's scope and are not
re-evaluated here. Status unchanged.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision. The
unreconciled discrepancy between the Incubator's computed subscriber
range (180-1,830) and `Clarifications_v10.md`'s cited 360-2,440 range
remains open (see Outstanding Questions).

## Operations

**Status:** Complete (restored from Partial) | **Confidence:** High
(restored from Medium) | **Evidence:** Supported

**The request-for-payment feature is removed entirely.** Per
`Clarifications_v11.md`, the user confirms that "arrears" in this
feature — present since `Clarifications_v5.md` — previously meant the
penalty-inclusive figure, i.e. v10's flagged Reading #2. Under the
redesigned zero-child-visibility penalty model, a feature presupposing
that level of child-facing awareness cannot coexist with it. Rather than
redesign the feature to reference only the child's own unpaid base
wages, the user's explicit decision is **full removal, for now** — not a
narrower replacement mechanic. The Incubator does not invent a
replacement. All prior descriptions of this feature (v5 through v10) are
retracted, not merely supplemented.

**Status restored to Complete.** The specific mechanical contradiction
that caused v10's downgrade — a feature requiring child visibility the
redesign had just eliminated — no longer exists, because the feature no
longer exists. The core payroll/task/payslip mechanic (budget → tasks →
Mbuck/Mpoint earning → exam bonus → invoice/payslip → parent-direct bank
payment → parent-side-only late penalty) is now internally coherent
across every section that describes it, with no remaining unresolved
contradiction. Confidence is restored to High for the same reason it was
lowered in v10: the ambiguity that justified Medium has been closed, not
merely narrowed.

**This restoration is not treated as risk-free, however — removal
surfaces its own new question.** With the feature gone, the case now
describes **no** in-app mechanism at all — for the child or the parent —
to flag, request, or escalate an overdue base-wage payslip payment. Prior
to this revision, that gap was masked by a feature that (per the now-
confirmed Reading #2) was never actually coherent in the first place; its
removal makes the gap visible rather than closing it. This is named as a
new Outstanding Question, not assumed away, and not treated as blocking
Complete status — Operations describes what the mechanic *does* without
internal contradiction, which is the bar this Status tracks; the absence
of a recourse feature is a scope gap, not a contradiction, and several
other Complete-status sections in this case (e.g. Objectives, Value
Proposition) carry comparable residual open items without losing Complete
status.

**Enforcement mechanism for the parent-side penalty — substantially
clarified this revision, not fully resolved.** Per `ResearchFindings_v2.md`
(Research House Engagement 2), applying the Incubator's own scrutiny: the
practical, near-term answer is to **continue the existing honor-system
self-report model** — Research House's Item 3 finding (High confidence,
multiple independent sources: vendor FAQs, app-store listings, and
third-party comparison reviews) confirms this is standard practice among
comparable non-custodial apps (FamZoo's IOU accounts, Bomad), not a
MiniMoney-specific weakness, and that no app was found solving external-
payment verification without either becoming a money-mover (GoHenry,
Greenlight — a different regulatory posture MiniMoney has deliberately
not pursued) or trusting the parent's self-report. Read-only account-
linking (Stitch, Mono) is assessed (Item 4, Medium confidence) as a
later-stage/V2+ feature, not initial-build scope, given South Africa's
Open Finance framework is not yet mandated (effective date cited as
2026, full compliance targeted 2028), Stitch's account-data product is
enterprise-sales-led with no published self-serve pricing, and neither
vendor's South African bank coverage could be confirmed from public
sources. PayShap Request reference-number transcription and proof-of-
payment document-fraud-detection APIs are flagged as cheaper, non-
custodial intermediate options worth evaluating, but are design ideas,
not validated or committed features — no comparable app was found
actually using the PayShap-reference approach. **What remains
unresolved:** whether the parent-side arrears/penalty balance has any
real contractual enforceability at all — a distinct legal question
Research House explicitly declines to answer and routes to the
specialist legal opinion (see Legal & Compliance). This finding is
treated as Supported-tier only, per standing instruction, and does not
raise any tag to Verified.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10 in its core gaps. **One addition this revision:**
Research House's Engagement 2 confirms two viable read-only account-
linking vendors exist for a possible future integration (Stitch, Mono),
but both are assessed as unsuitable for the initial build (see
Operations). This is noted here for technology-stack planning
continuity but does not change this section's Status, which remains
Partial for reasons predating and independent of this addition (core
platform/architecture technology-stack decisions remain undocumented in
this case).

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This section remains flagged Critical, and its Status is unchanged.**
The underlying legal uncertainty — money-transmitter characterization of
the invoice/payment trigger; the absence of ARB/NCR precedent for
"payslip"/"invoice"/"late penalty" terminology applied to minors; POPIA
Section 34/14 sufficiency — is unresolved, and the specialist legal
opinion required to address it has still not been obtained. The trigger
for commissioning it remains as resolved in v10: event-based, once a
stable working model exists and before any pilot testing begins.

**This revision sharpens, but does not close, the opinion's required
scope**, per `ResearchFindings_v2.md` Item 2 (desk research on general
South African contract-law doctrines, explicitly not a legal
conclusion). Two additional, specific questions are added to what the
specialist opinion must address, beyond what v10 already listed:

1. **The domestic-agreement presumption.** South African common law
   (via the widely-cited *Balfour v Balfour* doctrine) presumes promises
   made in an ordinary family setting are not intended to be legally
   binding, rebuttable only with clear evidence both parties intended
   otherwise. No South African case law applying this specifically to a
   parent-child allowance or penalty arrangement was found by Research
   House — its application to MiniMoney's "agreed condition of budget
   setup" framing is unconfirmed, not merely unresearched, and is a
   genuine open question the specialist opinion needs to address.
2. **Minor contractual capacity.** South African law gives minors
   (age 7-18) only limited contractual capacity; an unassisted minor's
   agreement generally binds the other party while the minor may elect
   to disregard the obligation. The redesigned penalty runs against the
   parent, not the child, which sidesteps this issue for the penalty
   itself — but the underlying payslip amount owed to the child likely
   still sits inside this same limited-capacity framework, a question
   this case has not previously named explicitly.

Research House also checked the National Credit Act as a possible
regulatory analogy and found it does not apply to non-interest-bearing
informal arrangements between individuals (and explicitly excludes
comparable informal vehicles like stokvels) — suggesting, as an
inference from the Act's scope provisions rather than a ruling on this
specific design, that a private family payment-tracking arrangement
would likely sit outside the NCA's regulatory perimeter. This is useful
landscape context but is explicitly flagged by Research House as
insufficient to answer the enforceability question — that remains with
the specialist opinion, and Research House states plainly it is not
qualified to give that conclusion. Per standing instruction, none of
this raises any Legal & Compliance tag beyond Supported.

**Redesigned mechanic implications — unchanged from v10.** The
late-penalty mechanic being parent-incurred and parent-invisible-only
changes, but does not resolve, the terminology-to-minors risk: "invoice,"
"payslip," and "arrears" language is still applied in a product
explicitly directed at minors as young as 6.

**Request-for-payment feature — removed, per Operations above.** This
closes the specific data-exposure question v10 raised (whether the
feature required penalty-inclusive arrears data reaching the child's
account) by eliminating the feature that raised it, rather than by
answering it. See Legal & Compliance — Child Data & Consent below for
the corresponding update.

The feature-level gating plan established in v9 (financial-trigger
features locked behind the opinion; foundational rails may proceed in
parallel) is unchanged and still applies; read-only account-linking, if
ever pursued, is now explicitly confirmed as a later-stage feature that
would itself require inclusion in that same gate before development.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Carried forward largely unchanged from v10, with two updates:

**Child-development/age-appropriateness risk — one of three residual
pathways is now closed.** v10 named three residual pathways after the
penalty redesign narrowed this risk: (1) indirect parental-stress
effects a child can still perceive; (2) payment-delay visibility distinct
from penalty visibility; and (3) the request-for-payment feature's
unresolved status, which — if it had ever required penalty-inclusive
arrears data — would have reintroduced exactly the child-facing
visibility the redesign was meant to remove. **Pathway (3) is now
closed**, not merely narrowed: the feature is confirmed to have required
penalty-inclusive data (v10's Reading #2) and is removed entirely, so it
cannot reintroduce that visibility in any form. Pathways (1) and (2)
remain open, unmeasured, and unchanged. The required child-development
review's scope narrows correspondingly — it no longer needs to consider
a live feature-level reintroduction risk, only the two residual
relational/perceptual pathways.

**Trust/enforcement risk — informed, not resolved, by Research House
Engagement 2.** The finding that honor-system self-reporting is standard
category practice (Item 3, High confidence) somewhat normalizes this
risk — MiniMoney is not attempting something no comparable product has
tried and is not, by that fact alone, an outlier design choice. This
does not change the fundamental limitation the risk describes: MiniMoney
still has no way to independently confirm or compel actual parent
payment, and the redesigned parent-side penalty's real-world
enforceability remains legally unconfirmed (see Legal & Compliance). Risk
is retained, reframed as "narrowed by category-consistency evidence, not
eliminated," consistent with how the child-development risk was treated
in v10.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10, with two additions:

**New this revision — no assumption is made about future reintroduction
of the removed request-for-payment feature.** The user's "for now"
framing in `Clarifications_v11.md` explicitly leaves open, rather than
commits to, a future redesigned version scoped to base-wage-only
arrears. The Incubator does not assume reintroduction is planned, likely,
or off the table — this is named as an explicit non-assumption, not a
silent default in either direction.

**New this revision — it is assumed, pending the specialist legal
opinion, that a purely honor-system verification model (no account-
linking, no automated payment confirmation) is an acceptable design
choice for at least the initial launch.** This is supported by Research
House's finding that comparable non-custodial apps use the same model
(Supported-tier evidence), but the specialist legal opinion has not yet
confirmed this model is compliant or that the resulting arrears/penalty
balance is enforceable for a South African, minor-directed product
specifically — the assumption rests on category-consistency, not on
legal confirmation.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in overall structure from v10's feature-level gating plan.
**This revision adds one sequencing clarification:** read-only account-
linking (Stitch, Mono), if ever pursued, is now explicitly confirmed as
a later-stage/V2+ feature, not initial-build scope (see Operations,
Technology) — consistent with, and further supporting, the existing
foundational-rails-first sequencing established in v9. This removes a
previously undetermined scope question but does not resolve Roadmap's
Partial status: no dated milestone plan, phased budget, or external-help
budget ceiling has been supplied, and "stable working model" remains a
judgment call, not a checkable milestone.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not directly addressed this revision. The
family-vs-child install-count ambiguity and the unreconciled subscriber-
count discrepancy remain open (see Outstanding Questions).

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

1. **Legal validation** — unchanged from v10; the specialist opinion's
   required scope is sharpened this revision (see Legal & Compliance:
   domestic-agreement presumption, minor contractual capacity for the
   payslip obligation) but the opinion itself remains unobtained.
2. **Primary user-research validation** — unchanged from v10.
3. **Child-development/age-appropriateness review** — required, scope
   further narrowed this revision: one of three residual risk pathways
   (the request-for-payment feature's reintroduction risk) is now closed
   by the feature's removal, leaving two (indirect parental-stress
   effects; payment-delay perception) as the review's required focus.
4. **Trust/enforcement and dispute-mechanism validation — updated this
   revision.** Research House Engagement 2 (desk research) confirms
   honor-system self-reporting is standard, category-consistent practice
   and that read-only account-linking is realistically a later-stage
   feature for the current South African regulatory/vendor landscape.
   This informs, but does not substitute for, empirical pilot validation
   of whether parents and children find the honor-system model
   trustworthy in practice, and does not resolve the separate legal-
   enforceability question routed to the specialist opinion.
5. **Market/demand validation** — unchanged from v10.
6. **Pricing/conversion validation** — unchanged from v10.
7. **Curriculum validation** — unchanged from v10.

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in content and treatment from v10. `ResearchFindings_v2.md` adds
new Supported-tier desk-research evidence (comparable-app architecture
split; South African contract-law landscape; open-banking vendor
landscape) but, per standing instruction, this vendor output does not
and cannot raise any tag to Verified — that tier remains reserved for
information the user has personally confirmed.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this revision (removed from the open list):** whether the
request-for-payment prompt feature refers only to base wages or included
penalty-inclusive figures — confirmed as the latter (v10's Reading #2)
and the feature is removed entirely, closing this item.

**New this revision:**

- With the request-for-payment feature removed, the case now describes
  no in-app mechanism for a child (or parent) to flag, request, or
  escalate an overdue base-wage payslip payment. Is this an acceptable
  gap for launch (i.e., is passive noticing — the child simply observes
  the payslip is late — considered sufficient UX for now), or should a
  narrower, base-wage-only replacement feature be designed before
  launch? The user's "for now" framing in `Clarifications_v11.md` leaves
  this open rather than resolving it in either direction.
- Given Research House's finding that honor-system self-reporting is
  standard category practice and account-linking is a later-stage
  feature, is the user comfortable formally adopting "honor-system only
  at launch, account-linking deferred to V2+" as a stated design
  decision, or is this still considered open pending the specialist
  legal opinion's view on enforceability?
- Does the user want a direct sales inquiry made to Stitch and/or Mono
  now (to obtain firm South African pricing and bank-coverage figures),
  or is this deferred until account-linking is actually prioritized as a
  later-stage feature? Research House flagged this as the only way to
  resolve the pricing gap it could not close via desk research.

**Still open, carried forward unchanged from v10** (see
`BusinessCase_v10.md` for the full itemized list): the family-vs-child
install ambiguity; the unreconciled subscriber-count discrepancy
(180-1,830 computed vs. 360-2,440 cited); the recommended preliminary
legal read's adoption decision; fund custody mechanics; consent-gate
technical mechanism; task verification; dispute-escalation beyond 48
hours; payment-routing timeline; late-penalty cap rationale; Fintech
Advance scope; exam-bonus data source; Mbucks-peg flexibility;
curriculum age-band splits; app-store policy sub-questions; MoneyAfrica
Kids' unpublished premium price; whether informal engineering-cost
quotes will be sought; the external-help budget ceiling; the
schools-partnership channel's timeline/target school count/resourcing
plan.

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

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
| Business Model | Partial | 1x | 2 |
| Revenue & Costs | Partial | 1x | 2 |
| Operations | **Complete (was Partial)** | 1x | **5** |
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

Points earned: **67** (up from 64 in v10: +3 Operations).

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130** (unchanged).

**Readiness Score = 67 / 130 = 51.5%, rounded to 52%. Up from 49% in
v10.**

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → **52% (v11).**

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB legal opinion remains unobtained. Its
   required scope is sharpened this revision (domestic-agreement
   presumption; minor contractual capacity for the payslip obligation),
   but the underlying legal uncertainty is unchanged, and the trigger
   remains event-based rather than dated.

2. **Family-vs-child install ambiguity (Financial Considerations,
   Revenue & Costs, Assumptions)** — unresolved, carried forward
   unchanged from v10.

3. **Request-for-payment feature inconsistency — RESOLVED this
   revision.** The feature is confirmed to have presupposed
   penalty-inclusive arrears visibility and is removed entirely, per
   the user's direct decision in `Clarifications_v11.md`. No longer a
   Critical Gap; retained here for audit-trail continuity only. A
   smaller, non-Critical open question surfaces from the removal itself
   — see Outstanding Questions.

4. **Late-penalty enforcement mechanism — substantially clarified this
   revision, not fully resolved.** Research House Engagement 2 provides
   a reasonably well-supported near-term technical answer (continue
   honor-system self-report, defer account-linking to a later stage),
   but the deeper legal-enforceability question of the arrears/penalty
   balance is explicitly not answered by this research and remains with
   the still-unobtained specialist legal opinion (see Gap #1).

5. **Child-development/age-appropriateness risk (Success Criteria,
   Risks, Validation Strategy)** — one of three residual pathways is
   closed this revision (the request-for-payment feature's reintroduction
   risk); two remain open (indirect parental-stress effects;
   payment-delay perception). The required expert review has not yet
   been conducted in any version of this case.

6. **Subscriber-count discrepancy (Revenue & Costs)** — unresolved,
   carried forward unchanged from v10.

7. **90-day vs. annual funnel tension — RESOLVED in v10**, retained here
   for audit-trail continuity only.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v10. Not addressed this revision.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This revision resolves the specific contingency flagged in v10.** v10
held this section's Status as Partial "contingent on" the request-for-
payment feature's unresolved status — because if that feature had
required penalty-inclusive arrears data to reach the child's account, it
would have reintroduced the more complex minor-facing data-exposure
surface the penalty redesign was intended to close off. That contingency
is now resolved: the feature is removed entirely, so no penalty-inclusive
data is exposed to the child's account by any current feature. The
data-retention/deletion pipeline (POPIA Section 14) need only ever
surface the penalty to the parent, confirmed as the simpler
data-exposure surface v10 anticipated but could not yet confirm.

**Status remains Partial, however, for reasons independent of this
resolved contingency, unchanged from v9 and v10:** the universal
consent-gate model's technical mechanism is still undocumented; the two
explicit user risk-accepted assumptions (POPIA Section 14 retention
sufficiency; exam-bonus mechanic's no-schools-data-privacy-dimension
assumption) remain accepted but unreviewed by a specialist; Google Play's
Families Policy loyalty-point disclosure requirement and Apple's Kids
Category IAP-currency question remain open; and the confirmed absence of
ARB/NCR precedent for "payslip"/"invoice"/"late penalty" terminology
applied to minors is unchanged. This section's Complete status is
therefore not restored this revision — the resolved contingency removes
one of several open items, not all of them. This is the kind of
analytical progress that does not, on its own, move a section's Status —
stated explicitly here rather than left for a later reviewer to notice
unprompted.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Child Data & Consent are both Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 52% (67/130), up from
  49% in v10. Progression: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) → 40%
  (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11).

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
rises to 52% from 49% in v10 — driven by a single genuine resolution
(the request-for-payment feature's internal inconsistency, closed by
removal, restoring Operations to Complete). The enforcement-mechanism
research materially informs but does not close Legal & Compliance's
Critical gap, and does not move the Readiness Score on its own, since
that section's Status was, and remains, Partial for reasons the research
sharpens rather than resolves — this is stated explicitly here so the
unchanged Legal & Compliance score is not misread as the research having
been ignored. A v12 would need: (a) the actual specialist legal opinion
(or at minimum the recommended preliminary read) obtained, now with a
sharpened scope; (b) resolution of the family-vs-child install-count
ambiguity; (c) resolution of the subscriber-count discrepancy; (d) a
user decision on the new, non-Critical question of whether any recourse
mechanism is needed for overdue payslip payments; and (e) the required,
narrower-scope child-development review conducted, to meaningfully
advance the Readiness Score further.
