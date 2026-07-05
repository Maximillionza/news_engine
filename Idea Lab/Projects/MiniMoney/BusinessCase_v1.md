# Business Case: MiniMoney — v1

> Prepared by: Incubator
> Source input: `00_CaseStudy.md` (verbatim user submission, 2026-07-05)
> This document is self-certified against the Incubator completion gate.
> No content beyond the case study file was used. Anything not directly
> stated or reasonably inferable from the case study is tagged Unknown
> or Assumed — never fabricated.

---

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6–18) that combines gamified task assignment with a simulated
payroll system: children complete parent-assigned tasks to earn points
pegged to real currency, incur percentage-based "expenses" that scale
with earnings, and receive a "payslip" summarizing earnings, overtime,
and deductions. The parent receives a corresponding invoice and is
required to transfer the actual owed funds to the child via their
registered bank account. Financial literacy education is layered on top,
tailored to the age of the user. The concept is well-formed as a family
finance/allowance-management tool with an embedded curriculum, but it
sits at the intersection of three regulated domains — payments,
child-directed digital services, and financial education — none of which
are addressed in the original submission beyond the core mechanic. This
Business Case surfaces those gaps explicitly rather than assuming they
are solved.

---

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Parents lack a structured, automated system to teach children (6–18)
real-world financial concepts — earning, budgeting, taxation/expenses,
and payment mechanics — using real money in a controlled, task-based
framework. Existing allowance-tracking apps (implied competitive gap, not
stated in source) typically either (a) simulate money entirely in-app
with no real bank transfer, limiting real-world stakes, or (b) require
manual parent bookkeeping with no education layer. The case study does
not cite data, research, or a personal anecdote establishing this problem
empirically — the problem statement is inferred from the described
solution mechanic, not independently evidenced in the source.

---

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Assumed

If financial literacy for minors is an underserved niche (plausible given
the well-documented broader interest in "kids' fintech" apps such as
Greenlight, GoHenry, and RoosterMoney — none of which are named or
referenced in the case study itself), MiniMoney's differentiator would be
the payroll-simulation mechanic (tasks → points → invoice → real bank
payment → payslip) rather than a simple debit-card-for-kids model. This
is an inference about market positioning, not a claim made in the source
document. No market sizing, competitor analysis, or demand validation
(e.g. waitlist signups, parent surveys) is present in the case study.

---

## Objectives

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

The case study does not state measurable business objectives (user
targets, revenue targets, timeline to launch, etc.). The only objective
explicitly implied is functional: build an app that (1) assigns tasks,
(2) converts completion into point-based earnings, (3) applies
percentage-based scalable expenses, (4) generates a parent invoice and
child payslip, (5) triggers a real bank payment from parent to child,
and (6) delivers age-appropriate financial education. No success metrics
(DAU, retention, revenue, curriculum completion rate) are defined in the
source.

---

## Success Criteria

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No criteria are given for what
constitutes a successful pilot, launch, or ongoing operation (e.g.
number of families onboarded, task-completion rates, curriculum mastery
scores, parent satisfaction, retention past 90 days). This must be
defined before validation can proceed.

---

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Directly named or clearly implied in the source:
- **Children/teens (6–18)** — the end users who complete tasks, earn
  points, and receive education content.
- **Parents/guardians** — who assign tasks, adjust the percentage-based
  expense rules, receive the automated invoice, and execute the real
  bank payment.
- **The app operator (Masood / MiniMoney)** — owns the platform,
  curriculum content, and payment-triggering logic.

Not addressed in the source but relevant: banks/payment rails processing
the parent-to-child transfer, app store platforms (Apple/Google) whose
policies on minors and financial transactions would apply, and any
regulatory body governing child data or payment facilitation in the
user's jurisdiction (South Africa, per user profile, though not stated
in the case study itself).

---

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Two user tiers are explicit in the source: children/teens aged 6–18 (a
12-year age span implying the need for distinct sub-band experiences —
e.g. 6–9, 10–13, 14–18 — though the source only says education must
"appeal to the respective age demographic" without specifying bands) and
their parents, who are the actual paying/administrating customer and
bank-account holder. The case study does not specify geography,
household income level, banking infrastructure assumed (e.g. does the
"registered bank" need open banking / instant EFT capability?), or
whether this is aimed at a single market (e.g. South Africa) or designed
for multi-market use.

---

## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household chores/tasks into
a structured payroll-like experience for their children, removing manual
tracking and adding a built-in financial literacy curriculum, with
expense rules that scale proportionally to earnings (so the system
remains meaningful regardless of how much or little a child earns). For
children: a "real job" simulation — payslips, overtime, deductions — that
pays out in actual money via their parent's bank transfer, tied to
age-appropriate lessons. This is the strongest, most concrete part of the
original submission. What is not addressed: why a parent would choose
this over simply paying an allowance manually, or over a competing app;
no differentiation claim is made in the source itself.

---

## Market & Competition

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No competitor names, market size,
pricing benchmarks, or category definition are provided. (The Incubator
notes, for the Expert Roster's benefit, that a competitive kids'-fintech
category is known to exist publicly — e.g. debit-card-for-kids apps —
but since the case study does not reference this, it cannot be asserted
as part of the Business Case itself beyond this flag.) This is a
significant gap for a fintech-adjacent product entering a category with
existing, well-capitalized incumbents.

---

## Business Model

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No monetization mechanism (subscription,
freemium, transaction fee, bank partnership revenue share, B2B2C via
banks/schools) is specified. The core mechanic implies MiniMoney is a
facilitation/education layer sitting on top of the parent's own bank
account — it is not itself described as moving or holding money (the
parent pays the child "via their registered bank," suggesting the app
may not need a money-transmitter license if it never touches funds
directly — but this is an inference, not a stated design decision, and
must be validated with a payments/compliance expert).

---

## Revenue & Costs

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No pricing, cost structure, customer
acquisition cost, curriculum content production cost, or engineering
cost estimate is present. This section cannot be completed without
further input.

---

## Operations

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. Open operational questions include how
task assignment/verification works (parent manually marks tasks
complete? photo proof? integration with smart home/chore trackers?), how
disputes are handled (child claims task done, parent disagrees), how the
invoice-to-payment loop is enforced or reminded, and what happens if a
parent does not pay the generated invoice (no described consequence or
escalation mechanism).

---

## Technology

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

The case study implies at minimum: a mobile app (platform unspecified —
iOS/Android/both not stated), a task-assignment and point-calculation
engine, a percentage-based rules engine for "expenses" (parent-adjustable
defaults), a document-generation feature (invoice for parent, payslip for
child), and some integration point with the parent's "registered bank"
to facilitate or confirm payment. Whether this integration is a deep
banking API integration (e.g. open banking, instant EFT initiation) or
merely a payment reminder/confirmation workflow (parent pays manually
outside the app, and the app just records it) is not specified — this is
a materially different engineering and compliance scope depending on
which is intended, and must be resolved before technical design begins.

---

## Legal & Compliance

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

**This section is flagged Critical.** Not addressed at all in the case
study, despite being central to feasibility. Open items include: (1)
child data protection law applicable to an app collecting data from
users as young as 6 (e.g. COPPA in the US, POPIA in South Africa, GDPR-K
in the EU — jurisdiction not stated in source); (2) whether triggering or
facilitating a real bank payment makes MiniMoney a money-transmitter or
payment-facilitator subject to financial services licensing, even if
funds never touch the app's own accounts; (3) parental consent
mechanisms required before processing a minor's data; (4) app store
policy compliance for apps directed at children (Apple/Google both have
specific rules for kids' categories, including restrictions on data
collection and monetization mechanics); (5) whether "payslip" and
"invoice" terminology carries any unintended regulatory implication
(e.g. implying an employment relationship, which is not the intent but
could be misconstrued). None of this is addressed in the source
submission.

---

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Risks identifiable directly from the described mechanic:
- **Regulatory risk (Critical):** a minor-directed app that triggers or
  facilitates real bank transfers may require financial services
  licensing depending on jurisdiction and exact transaction flow.
- **Child-safety/data-privacy risk (Critical):** collecting data from
  6-year-olds requires verified parental consent and strict data minimization; not addressed in source.
- **Trust/enforcement risk:** the system depends on the parent actually
  making the bank payment after the invoice is issued — the case study
  describes no enforcement or fallback mechanism if a parent fails to
  pay, which would undermine the "real money" promise to the child.
- **Terminology/perception risk:** framing a child's allowance as
  "payslip," "overtime," and "expenses" could raise concerns among
  child psychologists or regulators about normalizing labor-like
  relationships between parent and child; not addressed in source but a
  reasonable inference from the described mechanic.
- **Competitive risk:** established kids'-fintech apps with debit cards
  and bank partnerships already exist in the broader category (Incubator
  general knowledge, not sourced from case study); MiniMoney's
  differentiation and defensibility against these is unaddressed.

---

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Assumed

Assumptions made by the Incubator in order to complete this document,
all flagged as such and not verified against the source:
- Assumed the "registered bank" mechanism means the parent pays the
  child directly from the parent's own existing bank account (i.e.
  MiniMoney does not hold or move funds itself) — this materially
  changes the compliance burden if wrong.
- Assumed target market is South Africa given user profile context, but
  this is not stated anywhere in the case study itself and must be
  confirmed.
- Assumed "points equivalent to real money" means a fixed or
  parent-configured conversion rate (e.g. 1 point = R1), not a
  floating/market-based value — the case study does not specify the
  conversion mechanism.
- Assumed the app is intended as a consumer (B2C, parent-paid or
  freemium) product rather than a B2B2C offering through banks, schools,
  or employers — not stated in source.

---

## Constraints

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No budget, timeline, team size,
technical constraint, or platform constraint (iOS-only vs
cross-platform) is stated. The user's known technical stack (per general
working profile: Kotlin/Android, MQL5, Python, React/Three.js) is not
referenced anywhere in the case study submission itself and therefore is
not used here as a stated constraint — it is flagged only as a possible
future input the user may wish to supply.

---

## Roadmap

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No phasing, MVP scope, pilot plan, or
launch timeline is present.

---

## Financial Considerations

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No funding ask, runway, unit economics,
or financial projections are present. Given the Legal & Compliance gap
above, financial considerations cannot be meaningfully modeled until the
regulatory shape of the product (education-only content app vs.
payment-facilitating fintech app) is resolved, as the two paths carry
dramatically different cost structures (e.g. licensing, compliance
staffing, insurance).

---

## Operations — Curriculum Design (Domain Extension)

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

*Appended because MiniMoney is an education product for a 12-year age
span (6–18) — the completion gate requires domain-specific sections for
products with curriculum design needs.* The case study states only that
"education needs to be incorporated and designed to appeal to the
respective age demographic," without specifying: age-band curriculum
splits, learning objectives per band, instructional format (game-based,
video, quiz, narrative), alignment to any existing financial literacy
standard (e.g. Jump$tart Coalition standards, national curricula), or
who authors the content (in-house curriculum designer vs. licensed
third-party content). This is a substantial unaddressed workstream
distinct from the payments/app engineering workstream.

---

## Legal & Compliance — Child Data & Consent (Domain Extension)

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

*Appended because MiniMoney targets users as young as age 6, triggering
child-directed-app compliance obligations beyond general Legal &
Compliance.* Specific unresolved items: verifiable parental consent flow
before a 6-year-old's data is collected; data retention/deletion
policies for minors; whether the youngest age band (6–9) can use the app
directly at all or only via a parent-operated interface with the child
observing; advertising/monetization restrictions common to children's
app categories on Apple/Google (e.g. no behavioral ad targeting to
under-13s). None of this is addressed in the source and must be resolved
before any technical build begins.

---

## Validation Strategy

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No pilot design, user research plan, or
hypothesis-testing approach (e.g. testing the payslip/invoice mechanic
with a small cohort of families before building bank integration) is
proposed in the source. The Incubator recommends (as a gap flag, not a
sourced fact) that validation should test the core assumption — that
parents will trust and consistently execute the bank payment step —
before any further investment in curriculum content or engineering.

---

## Supporting Evidence

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

The case study provides no external evidence: no market research, no
citations, no user interviews, no prior prototype, no competitor
benchmarking. The entire Business Case rests on the internal logical
consistency of the mechanic described by the user, not on external
validation. This is explicitly flagged so the Investment Committee does
not mistake inference for evidence.

---

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

1. What jurisdiction(s) is MiniMoney intended to launch in first, and
   what are that jurisdiction's rules on (a) minors' data privacy and
   (b) payment facilitation/money transmission?
2. Does MiniMoney ever hold, move, or touch funds itself, or does it
   only generate the invoice/payslip while the parent pays via their own
   banking app entirely outside MiniMoney's systems?
3. What are the specific age-band splits for the curriculum (e.g. 6–9,
   10–13, 14–18) and who will author the content?
4. What is the monetization model — parent subscription, one-time
   purchase, freemium, bank/institution partnership revenue share, or
   something else?
5. What happens if a parent does not pay the generated invoice — is
   there any enforcement, reminder escalation, or consequence within the
   app?
6. How is task completion verified (self-report, parent approval, photo
   proof, third-party integration)?
7. What is the intended platform (iOS, Android, both, web) and MVP
   scope/timeline?
8. Is there any existing prototype, wireframe, or prior research the
   user has already produced that could accelerate validation?
9. What conversion rate or mechanism governs "points equivalent to real
   money," and is it fixed or parent-configurable per family?
10. Has the user considered app store policy restrictions specific to
    apps in the "designed for kids" category on Apple App Store and
    Google Play, which may restrict aspects of the payment/invoice
    mechanic as described?

---

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted.

| Section | Status | Weight | Points |
|---|---|---|---|
| Executive Summary | Partial | 1x | 2 |
| Problem | Partial | 1x | 2 |
| Opportunity | Partial | 1x | 2 |
| Objectives | Incomplete | 1x | 0 |
| Success Criteria | Incomplete | 1x | 0 |
| Stakeholders | Partial | 1x | 2 |
| Target Users/Customers | Partial | 1x | 2 |
| Value Proposition | Partial | 1x | 2 |
| Market & Competition | Incomplete | 1x | 0 |
| Business Model | Incomplete | 1x | 0 |
| Revenue & Costs | Incomplete | 1x | 0 |
| Operations | Incomplete | 1x | 0 |
| Technology | Partial | 1x | 2 |
| Legal & Compliance ★ | Incomplete | 2x | 0 |
| Risks | Partial | 1x | 2 |
| Assumptions | Partial | 1x | 2 |
| Constraints | Incomplete | 1x | 0 |
| Roadmap | Incomplete | 1x | 0 |
| Financial Considerations | Incomplete | 1x | 0 |
| Validation Strategy | Incomplete | 1x | 0 |
| Supporting Evidence | Incomplete | 1x | 0 |
| Outstanding Questions | Complete | 1x | 5 |
| Curriculum Design (extension) | Incomplete | 1x | 0 |
| Child Data & Consent (extension) ★ | Incomplete | 2x | 0 |

Points earned: 2+2+2+0+0+2+2+2+0+0+0+0+2+0+2+2+0+0+0+0+0+5+0+0 = **23**

Points possible: 21 non-critical sections × 5 = 105, plus 3 critical
sections × 5 × 2 = 30. Total possible = **135**

**Readiness Score = 23 / 135 = 17%**

**This score is below the 70% completion gate threshold.** Legal &
Compliance and Child Data & Consent are both Critical + Incomplete,
which independently fails the gate regardless of overall score.

### Critical Gaps
1. **Legal & Compliance (Critical, Incomplete)** — no jurisdiction,
   licensing, or money-transmission analysis exists; this is the single
   largest blocker to feasibility.
2. **Child Data & Consent (Critical, Incomplete)** — no parental consent
   framework, data minimization approach, or app-store child-category
   compliance plan exists for users as young as 6.
3. **Business Model / Revenue & Costs / Market & Competition** — entirely
   unaddressed; the Investment Committee cannot assess viability without
   at least a directional monetization and competitive stance.
4. **Objectives / Success Criteria / Validation Strategy** — no
   measurable definition of what success looks like or how it would be
   tested exists yet.

---

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **No — FAILS.** Legal &
  Compliance and Child Data & Consent are both Critical and Incomplete.
- Readiness Score ≥ 70%: **No — FAILS.** Score is 17%.
- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`.
- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate.**
It is being delivered in this state deliberately: the case study, as
submitted, does not contain enough information to responsibly complete
the Critical sections without fabrication, and this document is
constructed under a strict no-invention rule. The gaps identified above
(see Outstanding Questions and Critical Gaps) are the specific,
actionable items needed to bring this to a passing state in a v2.
