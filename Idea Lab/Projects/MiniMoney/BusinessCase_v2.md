# Business Case: MiniMoney — v2

> Prepared by: Incubator
> Source input: `00_CaseStudy.md` (verbatim user submission, 2026-07-05),
> `BusinessCase_v1.md` (prior version), `Clarifications_v2.md` (user
> clarifications supplied after v1 gate failure, 2026-07-05).
> This document is self-certified against the Incubator completion gate.
> Changes from v1 are limited to what `Clarifications_v2.md` addresses:
> (1) narrowing the money-transmission question in Legal & Compliance and
> Risks, and (2) developing Business Model / Revenue & Costs monetization
> options at the user's explicit request. All other sections are carried
> forward from v1 unchanged except where the clarification has a direct,
> logical knock-on effect (noted inline). Nothing beyond the case study,
> v1, and the clarification was used. Anything not directly stated or
> reasonably inferable is tagged Unknown or Assumed — never fabricated.

---

## What Changed in v2 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Per `Clarifications_v2.md`, the user supplied two facts: (1) MiniMoney
never holds or transmits funds — the parent pays the child directly via
the parent's own banking app, entirely outside MiniMoney's systems; and
(2) the user has not decided on a monetization model and explicitly asked
the Incubator to develop options. This v2 updates **Legal & Compliance**,
**Risks**, **Assumptions**, **Business Model**, and **Revenue & Costs**
accordingly, and recalculates the **Readiness Score**. All other sections
are unchanged from v1 and are carried forward verbatim below for a
complete, standalone document, per the Incubator's obligation to produce
a document sufficient for an outside party without needing v1.

---

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6–18) that combines gamified task assignment with a simulated
payroll system: children complete parent-assigned tasks to earn points
pegged to real currency, incur percentage-based "expenses" that scale
with earnings, and receive a "payslip" summarizing earnings, overtime,
and deductions. The parent receives a corresponding invoice and pays the
owed amount directly to the child using the parent's own banking app —
**MiniMoney itself never holds, transmits, or takes custody of funds**
(confirmed by the user in `Clarifications_v2.md`), which materially
narrows — but does not eliminate — the money-transmission licensing
question. Financial literacy education is layered on top, tailored to
the age of the user. The concept is well-formed as a family
finance/allowance-management tool with an embedded curriculum. It still
sits at the intersection of three regulated domains — payments-adjacent
facilitation, child-directed digital services, and financial education —
and the monetization model remains undecided; the user has explicitly
asked the Incubator to propose options, which are developed below as
candidate directions, not confirmed decisions. This Business Case
surfaces remaining gaps explicitly rather than assuming them solved.

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
solution mechanic, not independently evidenced in the source. Unchanged
by `Clarifications_v2.md`.

---

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Assumed

If financial literacy for minors is an underserved niche (plausible given
the well-documented broader interest in "kids' fintech" apps such as
Greenlight, GoHenry, and RoosterMoney — none of which are named or
referenced in the case study itself), MiniMoney's differentiator would be
the payroll-simulation mechanic (tasks → points → invoice → real bank
payment → payslip) rather than a simple debit-card-for-kids model. The
clarification that MiniMoney never touches funds directly (it is a
facilitation/education layer, not a payments company) reinforces this
positioning: MiniMoney's opportunity is more accurately framed as an
**edtech app with a payroll-simulation UX**, competing on curriculum
quality and mechanic engagement rather than on banking features — a
lighter-weight, lower-regulatory-burden opportunity than a card-issuing
competitor like Greenlight or GoHenry. This remains an inference about
market positioning, not a claim made in the source document. No market
sizing, competitor analysis, or demand validation (e.g. waitlist signups,
parent surveys) is present in the case study or clarification.

---

## Objectives

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

The case study does not state measurable business objectives (user
targets, revenue targets, timeline to launch, etc.). The only objective
explicitly implied is functional: build an app that (1) assigns tasks,
(2) converts completion into point-based earnings, (3) applies
percentage-based scalable expenses, (4) generates a parent invoice and
child payslip, (5) prompts/confirms a real bank payment made by the
parent via their own banking app (not by MiniMoney), and (6) delivers
age-appropriate financial education. No success metrics (DAU, retention,
revenue, curriculum completion rate) are defined in the source or
clarification. Unchanged in substance by `Clarifications_v2.md`, beyond
item (5) being clarified as parent-initiated-and-executed rather than
MiniMoney-executed.

---

## Success Criteria

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarification. No criteria are given
for what constitutes a successful pilot, launch, or ongoing operation
(e.g. number of families onboarded, task-completion rates, curriculum
mastery scores, parent satisfaction, retention past 90 days). This must
be defined before validation can proceed.

---

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Directly named or clearly implied in the source:
- **Children/teens (6–18)** — the end users who complete tasks, earn
  points, and receive education content.
- **Parents/guardians** — who assign tasks, adjust the percentage-based
  expense rules, receive the automated invoice, and execute the real
  bank payment via their own banking app (confirmed in
  `Clarifications_v2.md` — MiniMoney does not execute or touch this
  payment).
- **The app operator (Masood / MiniMoney)** — owns the platform,
  curriculum content, and invoice/payslip-generation logic, but per the
  clarification, not the payment rail itself.

Not addressed in the source but relevant: the parent's bank (as the
external rail the parent uses independently of MiniMoney), app store
platforms (Apple/Google) whose policies on minors and financial
transactions would apply, and any regulatory body governing child data
in the user's jurisdiction (South Africa, per user profile, though not
stated in the case study or clarification itself).

---

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Two user tiers are explicit in the source: children/teens aged 6–18 (a
12-year age span implying the need for distinct sub-band experiences —
e.g. 6–9, 10–13, 14–18 — though the source only says education must
"appeal to the respective age demographic" without specifying bands) and
their parents, who are the actual paying/administrating customer and
bank-account holder. The case study does not specify geography,
household income level, or whether this is aimed at a single market
(e.g. South Africa) or designed for multi-market use. The clarification
that the parent pays via their **own** banking app (rather than MiniMoney
integrating with banking rails) reduces — but does not eliminate — the
dependency on specific banking infrastructure (e.g. open banking/instant
EFT), since MiniMoney now only needs to generate a payable amount and
reference, not initiate a transfer itself. This still leaves open whether
MiniMoney provides any structured "pay now" deep-link/handoff into the
parent's banking app or purely displays a manual instruction.

---

## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household chores/tasks into
a structured payroll-like experience for their children, removing manual
tracking and adding a built-in financial literacy curriculum, with
expense rules that scale proportionally to earnings (so the system
remains meaningful regardless of how much or little a child earns). For
children: a "real job" simulation — payslips, overtime, deductions — that
pays out in actual money via the parent's own bank transfer, tied to
age-appropriate lessons. This is the strongest, most concrete part of the
original submission. The clarification reinforces that MiniMoney's value
is specifically as an **education-and-facilitation layer**, not a
payments product — parents are not being asked to trust a new entity
with their money, only with generating the calculations, invoice, and
curriculum, which may itself be a value-proposition angle worth testing
("we never touch your money"). What is still not addressed: why a parent
would choose this over simply paying an allowance manually, or over a
competing app; no differentiation claim is made in the source or
clarification.

---

## Market & Competition

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarification. No competitor names,
market size, pricing benchmarks, or category definition are provided.
(The Incubator notes, for the Expert Roster's benefit, that a competitive
kids'-fintech category is known to exist publicly — e.g. debit-card-for-
kids apps such as Greenlight, GoHenry, RoosterMoney — but since neither
the case study nor the clarification references this, it cannot be
asserted as part of the Business Case itself beyond this flag.) The
clarification that MiniMoney does not hold/move funds arguably
repositions it as competing more directly with allowance-tracking and
chore-gamification apps (e.g. simpler, non-card-issuing competitors) than
with card-issuing incumbents — but this is the Incubator's inference, not
a stated market analysis, and remains a significant gap for a product
entering a category with existing, well-capitalized incumbents.

---

## Business Model

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

*Updated per `Clarifications_v2.md`: the user has not chosen a
monetization mechanism and explicitly asked the Incubator to develop
options. The following are candidate directions only — none is a
decision, all require validation, and none should be read as the
Investment Committee's or user's chosen path.*

Confirmed structurally: MiniMoney is a facilitation/education layer that
sits on top of the parent's own bank account and does not move or hold
funds. This removes the need for a money-transmitter license as its
primary business-model constraint (subject to full confirmation by a
payments/compliance expert — see Legal & Compliance), which opens the
monetization design space considerably compared to a card-issuing
competitor, since MiniMoney does not need interchange or transaction-fee
revenue as its core mechanic.

Candidate monetization options for consideration (not sourced from the
case study — Incubator-proposed, Evidence: Assumed):
1. **Parent subscription (B2C, recurring):** monthly/annual fee per
   family for access to the task/payroll engine and full curriculum
   library. Comparable in structure to Greenlight/GoHenry subscription
   tiers (Incubator general knowledge, not case-study-sourced). Simplest
   to implement given no payment-rail dependency; revenue predictability
   is the main advantage; customer acquisition cost and price sensitivity
   among parents is the main risk.
2. **Freemium with curriculum paywall:** core task/invoice/payslip
   mechanic free, deeper curriculum content (e.g. advanced age bands,
   investing basics for teens) gated behind a paid tier. Lowers adoption
   friction but requires enough free-tier value to build habit before
   monetizing, and curriculum production cost (see Revenue & Costs) must
   be weighed against expected conversion rate, which is currently
   unknown.
3. **B2B2C via schools or employers:** license MiniMoney to schools (as a
   financial-literacy curriculum tool for the classroom, with the
   payroll mechanic mapped to classroom "jobs" or a district-wide
   allowance program) or to employers as a family-benefit perk. Longer
   sales cycle, potentially larger contract value, but introduces a
   second, distinct stakeholder (school administrators / HR benefits
   teams) and a second compliance surface (school data-privacy rules,
   e.g. FERPA-equivalent in the user's jurisdiction) not currently
   addressed anywhere in this case.
4. **Bank/fintech partnership referral or co-brand:** partner with a
   kids'-banking product (debit card issuer) to refer parents who want
   an actual spending vehicle for the earned money, taking a referral
   fee. This reintroduces a payments-adjacent partner relationship and
   associated due diligence, but does not require MiniMoney itself to
   hold a license, since the partner already does.
5. **One-time purchase / lifetime license:** single upfront payment per
   family. Simpler pricing psychology for a household-budgeting tool but
   provides no recurring revenue to fund ongoing curriculum updates or
   compliance maintenance, which is a real ongoing cost (see Revenue &
   Costs).

None of these five options is validated; the Incubator recommends the
user and Investment Committee treat this as a shortlist to test (e.g. via
a pricing-sensitivity survey with target parents) rather than a decision,
per the Validation Strategy section below.

---

## Revenue & Costs

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Assumed

Not addressed with figures in the case study or clarification — no
pricing, cost structure, customer acquisition cost, curriculum content
production cost, or engineering cost estimate is present. However, given
the monetization options newly developed above, the following cost
categories can now be directionally flagged (Incubator-inferred, not
sourced, and containing no dollar/rand figures since none were supplied):
engineering cost for the task/points/expense-rules engine and
invoice/payslip generation; curriculum content production cost (likely
the largest recurring cost if age-banded, ongoing-updated content is
required — see Curriculum Design section); customer acquisition cost
specific to a parent-facing app in a competitive kids'-fintech-adjacent
category; and, if the B2B2C school/employer path is pursued, a sales
cost distinct from consumer-app marketing. This section remains
Incomplete because no actual figures, benchmarks, or estimates with
numbers were supplied by the user — the Incubator will not fabricate
placeholder dollar amounts. This is flagged clearly as a required
next-step input from the user or a finance-focused expert.

---

## Operations

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarification. Open operational
questions include how task assignment/verification works (parent
manually marks tasks complete? photo proof? integration with smart
home/chore trackers?), how disputes are handled (child claims task done,
parent disagrees), how the invoice-to-payment loop is enforced or
reminded now that payment happens entirely inside the parent's own
banking app (i.e. MiniMoney cannot detect or confirm payment
automatically unless the parent manually marks the invoice paid, or
MiniMoney integrates a read-only bank-statement check — neither
specified), and what happens if a parent does not mark/complete the
payment (no described consequence or escalation mechanism).

---

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The case study and clarification together imply: a mobile app (platform
unspecified — iOS/Android/both not stated), a task-assignment and
point-calculation engine, a percentage-based rules engine for "expenses"
(parent-adjustable defaults), a document-generation feature (invoice for
parent, payslip for child), and — now clarified — **no integration with
banking rails to move money**. MiniMoney's technical scope is therefore
narrower than assumed in v1: it needs only to generate the payable amount
and (optionally) a reference/reminder, and separately needs some
mechanism (manual parent confirmation, or a read-only bank-linking
service such as Plaid-equivalent, if pursued later) to know whether
payment occurred. This significantly reduces the payments-engineering
and money-transmitter compliance scope versus v1's open question, though
it does not eliminate the need for a decision on how payment confirmation
is captured, which remains unresolved.

---

## Legal & Compliance

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This section remains flagged Critical**, though it is materially
narrowed by `Clarifications_v2.md`. Resolved: MiniMoney does not hold,
move, or take custody of funds — the parent pays the child directly via
the parent's own banking app, entirely outside MiniMoney's systems. This
substantially reduces (though a compliance expert should still confirm
it eliminates) the risk that MiniMoney is itself a money-transmitter or
payment-facilitator subject to financial services licensing, since it
never intermediates the transaction.

Still open and unaddressed: (1) child data protection law applicable to
an app collecting data from users as young as 6 (e.g. COPPA in the US,
POPIA in South Africa, GDPR-K in the EU — jurisdiction not stated in
source or clarification); (2) parental consent mechanisms required
before processing a minor's data; (3) app store policy compliance for
apps directed at children (Apple/Google both have specific rules for
kids' categories, including restrictions on data collection and
monetization mechanics — this is now directly relevant given the
monetization options proposed above, several of which involve in-app
purchase or subscription flows that fall under child-category app store
rules); (4) whether "payslip" and "invoice" terminology carries any
unintended regulatory implication (e.g. implying an employment
relationship, which is not the intent but could be misconstrued) — this
is unaffected by the clarification; (5) if the B2B2C-school monetization
option is pursued, school-specific student-data-privacy law (not
addressed at all yet). None of items (1)–(5) is addressed in the source
or clarification.

---

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Risks identifiable from the described mechanic and clarification:
- **Regulatory risk (Critical, reduced but not closed):** the
  money-transmission licensing risk is substantially narrowed now that
  MiniMoney is confirmed not to hold or move funds — but child-data and
  app-store child-category compliance risk remains fully open (see Legal
  & Compliance), so this risk is downgraded from v1's severity but not
  removed.
- **Child-safety/data-privacy risk (Critical):** collecting data from
  6-year-olds requires verified parental consent and strict data
  minimization; not addressed in source or clarification. Unchanged from
  v1.
- **Trust/enforcement risk (elevated by clarification):** because
  MiniMoney cannot itself detect or confirm that the parent's banking-app
  payment actually occurred (it never touches the transaction), the
  system now more clearly depends on either an honor-system
  self-confirmation by the parent or a separate bank-linking integration
  to verify payment — the case study and clarification describe no
  enforcement or fallback mechanism if a parent fails to pay or fails to
  mark payment complete, which would undermine the "real money" promise
  to the child. This risk is arguably more acute post-clarification, not
  less, since the simplest technical path (no bank integration at all)
  relies entirely on parent self-reporting.
- **Terminology/perception risk:** framing a child's allowance as
  "payslip," "overtime," and "expenses" could raise concerns among child
  psychologists or regulators about normalizing labor-like relationships
  between parent and child; not addressed in source or clarification.
- **Competitive risk:** established kids'-fintech apps with debit cards
  and bank partnerships already exist in the broader category (Incubator
  general knowledge, not sourced); MiniMoney's differentiation and
  defensibility against these — now more clearly as an edtech/chore-
  gamification play rather than a banking play — is still unaddressed by
  the user.
- **Monetization-uncertainty risk (new):** because no monetization model
  is chosen, and five candidate options are proposed above with materially
  different cost structures, sales motions, and compliance surfaces
  (e.g. B2B2C-school introduces student-data law), the business model
  risk is currently unresolved and should be treated as a Critical open
  item alongside Legal & Compliance until validated.

---

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Assumed

Assumptions made by the Incubator in order to complete this document, all
flagged as such:
- **Confirmed by clarification (no longer an assumption):** the parent
  pays the child directly from the parent's own existing bank account via
  the parent's own banking app; MiniMoney does not hold or move funds
  itself.
- Still assumed: target market is South Africa given user profile
  context, but this is not stated anywhere in the case study or
  clarification and must be confirmed.
- Still assumed: "points equivalent to real money" means a fixed or
  parent-configured conversion rate (e.g. 1 point = R1), not a
  floating/market-based value — neither document specifies the
  conversion mechanism.
- Still assumed: the app is intended as a consumer (B2C) product as the
  primary path, with B2B2C (schools/employers) as one candidate
  monetization option among several proposed by the Incubator, not a
  stated design decision.
- New assumption introduced in v2: that MiniMoney will need some form of
  payment-status confirmation (manual or automated) to make the
  payslip/invoice loop meaningful, since it no longer has any technical
  visibility into whether the parent actually paid — this is an
  Incubator inference from the clarification, not a stated design
  decision.

---

## Constraints

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarification. No budget, timeline,
team size, technical constraint, or platform constraint (iOS-only vs
cross-platform) is stated. The user's known technical stack (per general
working profile: Kotlin/Android, MQL5, Python, React/Three.js) is not
referenced anywhere in the case study or clarification and therefore is
not used here as a stated constraint — it is flagged only as a possible
future input the user may wish to supply.

---

## Roadmap

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarification. No phasing, MVP scope,
pilot plan, or launch timeline is present. Given the clarification's
narrowing of technical scope (no banking-rail integration required for
launch), the Incubator flags — as a suggestion only, not a stated plan —
that an MVP could plausibly exclude any payment-confirmation automation
entirely (pure manual/honor-system) to accelerate validation of the core
curriculum-and-mechanic hypothesis before investing in more complex
payment-status verification. This is a recommendation, not a roadmap
supplied by the user.

---

## Financial Considerations

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarification. No funding ask, runway,
unit economics, or financial projections are present. The Legal &
Compliance narrowing (no money-transmitter licensing needed) likely
reduces the compliance-cost side of any future financial model compared
to v1's worst-case scenario, but this is a directional inference, not a
figure, and financial considerations still cannot be meaningfully modeled
until a monetization option (see Business Model) is chosen and
validated.

---

## Operations — Curriculum Design (Domain Extension)

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

*Appended because MiniMoney is an education product for a 12-year age
span (6–18) — the completion gate requires domain-specific sections for
products with curriculum design needs.* Unchanged by `Clarifications_v2.md`.
The case study states only that "education needs to be incorporated and
designed to appeal to the respective age demographic," without
specifying: age-band curriculum splits, learning objectives per band,
instructional format (game-based, video, quiz, narrative), alignment to
any existing financial literacy standard (e.g. Jump$tart Coalition
standards, national curricula), or who authors the content (in-house
curriculum designer vs. licensed third-party content). This is now also
directly relevant to the freemium monetization option proposed above
(which curriculum content sits behind a paywall), making its resolution
somewhat more urgent than in v1.

---

## Legal & Compliance — Child Data & Consent (Domain Extension)

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

*Appended because MiniMoney targets users as young as age 6, triggering
child-directed-app compliance obligations beyond general Legal &
Compliance.* Unchanged in substance by `Clarifications_v2.md` — the
clarification addressed money-transmission, not child data. Specific
unresolved items: verifiable parental consent flow before a 6-year-old's
data is collected; data retention/deletion policies for minors; whether
the youngest age band (6–9) can use the app directly at all or only via
a parent-operated interface with the child observing; advertising/
monetization restrictions common to children's app categories on
Apple/Google (e.g. no behavioral ad targeting to under-13s) — now
directly relevant given that subscription/freemium monetization options
are being considered and must be built compliant with these
restrictions from the outset. None of this is addressed in the source or
clarification and must be resolved before any technical build begins.

---

## Validation Strategy

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarification. No pilot design, user
research plan, or hypothesis-testing approach is proposed by the user.
The Incubator recommends (as a gap flag, not a sourced fact) two
validation priorities given v2's changes: (1) test the core assumption
that parents will trust and consistently execute/self-report the bank
payment step now that MiniMoney has no visibility into whether payment
occurred; and (2) test parent willingness-to-pay against the five
monetization options proposed above (e.g. via a pricing-sensitivity
survey or a smoke-test landing page offering each model) before
committing engineering or curriculum-production resources to any one
path.

---

## Supporting Evidence

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

The case study and clarification provide no external evidence: no market
research, no citations, no user interviews, no prior prototype, no
competitor benchmarking, no pricing research. The entire Business Case
rests on the internal logical consistency of the mechanic described by
the user plus the two clarifying facts supplied, not on external
validation. This is explicitly flagged so the Investment Committee does
not mistake inference for evidence.

---

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Carried forward from v1, with resolved items removed and new items added
per the clarification:

1. ~~Does MiniMoney ever hold, move, or touch funds itself?~~ **Resolved:**
   No — confirmed in `Clarifications_v2.md`. MiniMoney never holds funds;
   the parent pays directly via their own banking app.
2. What jurisdiction(s) is MiniMoney intended to launch in first, and
   what are that jurisdiction's rules on minors' data privacy (still
   open, unaffected by the money-transmission clarification)?
3. What are the specific age-band splits for the curriculum (e.g. 6–9,
   10–13, 14–18) and who will author the content?
4. **New/refined:** Of the five monetization options proposed in
   Business Model (parent subscription, freemium, B2B2C schools/
   employers, bank-partnership referral, one-time purchase), which
   does the user want to prioritize for validation first, and does the
   user have a preference for recurring vs. one-time revenue?
5. **New:** How will MiniMoney know or confirm that a parent has actually
   paid the invoice, given that it has no visibility into the parent's
   banking app — is this purely an honor-system self-confirmation
   ("mark as paid") or is a read-only bank-linking integration (e.g.
   Plaid-equivalent) planned for a later phase?
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
    Google Play — this is now more urgent given that several proposed
    monetization options involve in-app purchases/subscriptions, which
    are specifically restricted in the children's category?
11. **New:** If the B2B2C-school monetization path is of interest, has
    the user considered the additional student-data-privacy compliance
    surface this introduces (distinct from general child-data-privacy
    rules)?

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
| Business Model | Partial | 1x | 2 |
| Revenue & Costs | Incomplete | 1x | 0 |
| Operations | Incomplete | 1x | 0 |
| Technology | Partial | 1x | 2 |
| Legal & Compliance ★ | Partial | 2x | 4 |
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

Points earned:
2+2+2+0+0+2+2+2+0+2+0+0+2+4+2+2+0+0+0+0+0+5+0+0 = **29**

Points possible: 21 non-critical sections × 5 = 105, plus 3 critical
sections × 5 × 2 = 30. Total possible = **135**

**Readiness Score = 29 / 135 = 21%**

**This score remains below the 70% completion gate threshold.** Child
Data & Consent remains Critical + Incomplete, which independently fails
the gate regardless of overall score. Legal & Compliance moved from
Incomplete to Partial (money-transmission question narrowed) but remains
short of Complete.

### Critical Gaps

1. **Child Data & Consent (Critical, Incomplete)** — no parental consent
   framework, data minimization approach, or app-store child-category
   compliance plan exists for users as young as 6. **Unresolved by
   `Clarifications_v2.md`** — the clarification addressed money-
   transmission, not child data or consent.
2. **Legal & Compliance (Critical, Partial — improved from v1)** —
   money-transmission licensing risk is now substantially narrowed
   (MiniMoney confirmed not to hold/move funds), but jurisdiction,
   app-store child-category compliance, and terminology/regulatory-
   perception risk remain open.
3. **Business Model (Partial — improved from v1) / Revenue & Costs
   (still Incomplete)** — five candidate monetization options are now
   proposed for the user's and Investment Committee's consideration, but
   none is chosen or validated, and no cost/revenue figures exist yet.
4. **Objectives / Success Criteria / Validation Strategy** — no
   measurable definition of what success looks like or how it would be
   tested exists yet; unaffected by the clarification.
5. **Market & Competition** — still entirely unaddressed; the Investment
   Committee cannot assess competitive viability without at least a
   directional competitive stance.

---

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **No — FAILS.** Child Data &
  Consent remains Critical and Incomplete. (Legal & Compliance improved
  from Incomplete to Partial and no longer independently fails this
  check, but the gate still fails due to Child Data & Consent.)
- Readiness Score ≥ 70%: **No — FAILS.** Score is 21% (up from 17% in
  v1).
- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`.
- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate.**
Progress was made on Legal & Compliance (money-transmission risk
narrowed) and Business Model (five monetization options proposed for
validation), directly in response to `Clarifications_v2.md`. However,
Child Data & Consent remains untouched — the clarification did not
address it — and Market & Competition, Objectives/Success Criteria,
Validation Strategy, Revenue & Costs figures, Constraints, and Roadmap
remain Incomplete. This document is constructed under a strict
no-invention rule and is delivered in its current state deliberately: a
v3 would need further user input specifically on child-data/consent
handling, jurisdiction, a chosen monetization path, and basic
objectives/success metrics to meaningfully advance the score.
