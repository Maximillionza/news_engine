# Business Case: MiniMoney — v3

> Prepared by: Incubator
> Source input: `00_CaseStudy.md` (verbatim user submission, 2026-07-05),
> `BusinessCase_v2.md` (prior version), `Clarifications_v3.md` (user
> clarifications supplied after v2 gate failure, 2026-07-05).
> This document is self-certified against the Incubator completion gate.
> Changes from v2 are limited to what `Clarifications_v3.md` addresses:
> (1) confirming South Africa as the initial launch jurisdiction, making
> POPIA the applicable child-data-privacy law rather than a placeholder;
> (2) the user selecting Freemium (with parent-unlockable features) as the
> chosen monetization direction, retiring the other four candidate options
> from active consideration; and (3) the user describing an intended
> consent model (modeled on Google Family Link) for child sign-up. All
> other sections are carried forward from v2 unchanged except where a
> clarification has a direct, logical knock-on effect (noted inline).
> Nothing beyond the case study, v2, and this clarification was used.
> Anything not directly stated or reasonably inferable is tagged Unknown
> or Assumed — never fabricated. **Critically: the consent model described
> by the user is treated in this document as a stated design intent, not
> as a confirmed-compliant mechanism** — the Incubator does not have the
> authority to certify that a Family-Link-style self-consent flow
> satisfies POPIA's actual requirements for processing children's
> personal information, and flags this explicitly rather than assuming it
> away.

---

## What Changed in v3 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Per `Clarifications_v3.md`, the user supplied three facts: (1) initial
launch jurisdiction is South Africa; (2) the chosen monetization
direction is Freemium, with parents able to unlock additional features —
the other four candidate options from v2 are retired unless this path is
invalidated; (3) an intended consent model modeled on Google Family Link,
under which a child obtains "consent" by downloading and signing up
directly, the app does not restrict or monitor the child's device, users
over 10 may opt out unilaterally at any time, and a linked parent is
notified (not asked for approval) if a conversation hasn't already
occurred. This v3 updates **Target Users/Customers**, **Business Model**,
**Revenue & Costs**, **Legal & Compliance** (including the **Child Data &
Consent** domain extension), **Risks**, **Assumptions**, **Roadmap**, and
**Outstanding Questions** accordingly, and recalculates the **Readiness
Score**. All other sections are unchanged from v2 and are carried forward
verbatim below for a complete, standalone document.

**Headline finding of this revision:** the jurisdiction and monetization
gaps are now substantively narrowed, but the consent-model clarification,
while informative, does **not** close the Child Data & Consent critical
gap — it surfaces a specific, material compliance risk (see Legal &
Compliance and Risks below) that the Incubator judges as likely
insufficient under POPIA for a *financial* app processing data from
6–9-year-olds. This is flagged as a probable gap, not asserted as settled
law, since the Incubator is not a legal authority — but it cannot be
scored as "Complete" or treated as resolved.

---

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6–18), launching first in South Africa, that combines gamified task
assignment with a simulated payroll system: children complete
parent-assigned tasks to earn points pegged to real currency, incur
percentage-based "expenses" that scale with earnings, and receive a
"payslip" summarizing earnings, overtime, and deductions. The parent
receives a corresponding invoice and pays the owed amount directly to the
child using the parent's own banking app — **MiniMoney itself never
holds, transmits, or takes custody of funds** (confirmed in
`Clarifications_v2.md`). The chosen monetization direction is
**Freemium**: the core task/invoice/payslip mechanic is free, with
parents able to unlock additional features (confirmed in
`Clarifications_v3.md`), retiring four other candidate models proposed in
v2. Financial literacy education is layered on top, tailored to the age
of the user. The concept is well-formed as a family finance/allowance-
management tool with an embedded curriculum, now with a confirmed initial
market (South Africa) and a confirmed monetization direction. It still
sits at the intersection of three regulated domains — payments-adjacent
facilitation, child-directed digital services, and financial education —
and the user's described consent model (self-consent via signup,
modeled on Google Family Link, with notification-not-approval for linked
parents) is a stated design intent that the Incubator judges **likely
insufficient** to satisfy South Africa's POPIA requirements for
processing a young child's personal information in a financial-app
context — this is the single largest remaining risk to the business case
and is surfaced explicitly rather than assumed resolved.

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
by `Clarifications_v3.md`.

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
competitor like Greenlight or GoHenry. The confirmed South Africa launch
market (per `Clarifications_v3.md`) narrows this further: none of
Greenlight, GoHenry, or RoosterMoney currently operate as South
African-licensed card issuers (Incubator general knowledge, not
case-study-sourced), which may reduce direct incumbent competition at
launch but also means there is less local market validation data
available for kids'-fintech/edtech adoption specifically in South Africa.
This remains an inference about market positioning, not a claim made in
the source document. No market sizing, competitor analysis, or demand
validation (e.g. waitlist signups, parent surveys) is present in the case
study or clarifications.

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
clarifications. Unchanged in substance by `Clarifications_v3.md`.

---

## Success Criteria

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications. No criteria are given
for what constitutes a successful pilot, launch, or ongoing operation
(e.g. number of families onboarded, task-completion rates, curriculum
mastery scores, parent satisfaction, retention past 90 days, freemium
conversion rate). This must be defined before validation can proceed.
Unchanged by `Clarifications_v3.md`.

---

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Directly named or clearly implied in the source:
- **Children/teens (6–18)** — the end users who complete tasks, earn
  points, and receive education content.
- **Parents/guardians** — who assign tasks, adjust the percentage-based
  expense rules, receive the automated invoice, execute the real bank
  payment via their own banking app (confirmed in `Clarifications_v2.md`
  — MiniMoney does not execute or touch this payment), and are the
  freemium purchaser who unlocks additional features (confirmed in
  `Clarifications_v3.md`).
- **The app operator (Masood / MiniMoney)** — owns the platform,
  curriculum content, and invoice/payslip-generation logic, but per the
  v2 clarification, not the payment rail itself.

Newly relevant per `Clarifications_v3.md`: the **South African
Information Regulator** (the body that enforces POPIA), whose child-data
requirements now directly and specifically apply as the confirmed launch
jurisdiction, rather than as a placeholder possibility. Still not
addressed in the source: app store platforms (Apple/Google) whose
policies on minors and financial transactions would apply, and the
parent's bank (as the external rail the parent uses independently of
MiniMoney).

---

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Two user tiers are explicit in the source: children/teens aged 6–18 (a
12-year age span implying the need for distinct sub-band experiences —
e.g. 6–9, 10–13, 14–18 — though the source only says education must
"appeal to the respective age demographic" without specifying bands) and
their parents, who are the actual paying/administrating customer and
bank-account holder. **Geography is now confirmed** per
`Clarifications_v3.md`: initial launch is South Africa (previously an
assumption inferred only from user profile context, not the case study
itself — this is now Verified rather than Assumed for the launch market
specifically, though multi-market expansion plans remain unstated). The
clarification that the parent pays via their **own** banking app (rather
than MiniMoney integrating with banking rails) reduces — but does not
eliminate — the dependency on specific banking infrastructure. The
freemium model (per `Clarifications_v3.md`) also implies two customer
sub-segments going forward: free-tier parents (acquisition/funnel) and
paying parents who unlock additional features (monetized segment) — the
specific features gated behind the paywall are not yet specified by the
user.

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
("we never touch your money"). With Freemium now confirmed as the
monetization direction, the core value proposition must be strong enough
in its free tier to drive adoption and habit formation before any
paywall is hit — what specific features sit behind the paywall (per
`Clarifications_v3.md`, "additional features," unspecified) will
materially determine whether the free tier alone is compelling enough to
compete with a parent simply paying an allowance manually. This remains
unaddressed by the user.

---

## Market & Competition

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications. No competitor names,
market size, pricing benchmarks, or category definition are provided.
(The Incubator notes, for the Expert Roster's benefit, that a competitive
kids'-fintech category is known to exist publicly — e.g. debit-card-for-
kids apps such as Greenlight, GoHenry, RoosterMoney — but since neither
the case study nor the clarifications reference this, it cannot be
asserted as part of the Business Case itself beyond this flag.) The
confirmed South Africa launch market (per `Clarifications_v3.md`) means
the relevant competitive set is more likely local allowance/chore apps
and any South African-specific fintech-for-minors offerings, none of
which are named in any input document — this remains a significant gap
for a product entering a category whose local competitive landscape is
entirely unresearched in this case.

---

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Updated per `Clarifications_v3.md`: the user has selected Freemium
(Option 2 from the five candidates proposed in v2) as the chosen
monetization direction — "core mechanic free, with an ability for
parents to unlock additional features." This is now a stated decision,
not merely a candidate, and Confidence is upgraded from v2's Low to
Medium, and Evidence from Assumed to Supported, reflecting that the
direction itself is now user-confirmed even though implementation
details remain unspecified.*

Confirmed structurally: MiniMoney is a facilitation/education layer that
sits on top of the parent's own bank account and does not move or hold
funds (per `Clarifications_v2.md`). This removes the need for a
money-transmitter license as a primary business-model constraint
(subject to full confirmation by a payments/compliance expert — see
Legal & Compliance).

**Chosen model — Freemium:**
- Free tier: the core task/points/expense-rules engine and
  invoice/payslip generation (per the original case study's central
  mechanic) are available at no cost.
- Paid tier: parents can unlock "additional features" — the specific
  features are not yet specified by the user. Candidates the Incubator
  flags for the user's consideration (Incubator-proposed, Evidence:
  Assumed, not sourced): deeper/advanced curriculum content (e.g.
  investing basics for older teens), multiple-child household management,
  customizable expense-rule templates, or reporting/analytics for
  parents. None of these is confirmed; the user has not specified what
  sits behind the paywall.
- The four other candidate models from v2 (parent subscription-only,
  B2B2C schools/employers, bank-partnership referral, one-time purchase)
  are **retired from active consideration** per `Clarifications_v3.md`,
  "unless this path is invalidated" — i.e. they remain available as
  fallback options if freemium validation fails, but are not the current
  design target.

**Open implementation questions** (not addressed by the clarification):
what specific features are paywalled; pricing point/tier structure;
whether the freemium paywall interacts with app-store child-category
restrictions on in-app purchases (see Legal & Compliance — this is a
live compliance question given the confirmed monetization path, not a
hypothetical one as it was in v2's five-option state); and whether
freemium conversion assumptions have been tested with any target
parents.

---

## Revenue & Costs

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Assumed

Not addressed with figures in the case study or clarifications — no
pricing, cost structure, customer acquisition cost, curriculum content
production cost, or engineering cost estimate is present. With Freemium
now the confirmed direction (per `Clarifications_v3.md`), the following
cost/revenue categories can be more specifically flagged than in v2
(Incubator-inferred, not sourced, and containing no dollar/rand figures
since none were supplied): engineering cost for the task/points/
expense-rules engine, invoice/payslip generation, **and** the
feature-gating/entitlement logic needed to distinguish free vs. paid
users; curriculum content production cost (likely the largest recurring
cost if age-banded, ongoing-updated content is required — see Curriculum
Design section, and now specifically relevant if advanced curriculum
content is one of the features behind the paywall); customer acquisition
cost specific to a parent-facing freemium app in South Africa (a market
with no stated local benchmark in either input document); and expected
free-to-paid conversion rate, which is a standard freemium unit-economics
input entirely absent here. This section remains Incomplete because no
actual figures, benchmarks, or estimates with numbers were supplied by
the user — the Incubator will not fabricate placeholder dollar amounts.
This is flagged clearly as a required next-step input from the user or a
finance-focused expert.

---

## Operations

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications. Open operational
questions include how task assignment/verification works (parent
manually marks tasks complete? photo proof? integration with smart
home/chore trackers?), how disputes are handled (child claims task done,
parent disagrees), how the invoice-to-payment loop is enforced or
reminded now that payment happens entirely inside the parent's own
banking app (i.e. MiniMoney cannot detect or confirm payment
automatically unless the parent manually marks the invoice paid, or
MiniMoney integrates a read-only bank-statement check — neither
specified), and what happens if a parent does not mark/complete the
payment (no described consequence or escalation mechanism). Unchanged by
`Clarifications_v3.md`.

---

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The case study and clarifications together imply: a mobile app (platform
unspecified — iOS/Android/both not stated), a task-assignment and
point-calculation engine, a percentage-based rules engine for "expenses"
(parent-adjustable defaults), a document-generation feature (invoice for
parent, payslip for child), no integration with banking rails to move
money (per `Clarifications_v2.md`), and — new per `Clarifications_v3.md`
— an account-linking/parent-child relationship model (a child account can
be "linked" to a parent account, with a notification mechanism to the
parent) and a feature-entitlement/paywall system to support the freemium
model. MiniMoney's technical scope therefore now explicitly includes:
child account creation independent of verified parental gating (per the
described consent model), an opt-out mechanism for users over 10, a
parent-notification system (not an approval-gate) for linked accounts,
and free/paid feature-flagging. What remains unspecified: how "linking" a
child account to a parent account is initiated (parent-initiated invite,
or child self-links by entering a parent identifier), and how payment
confirmation is captured (still unresolved from v2).

---

## Legal & Compliance

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This section remains flagged Critical.** Resolved from prior versions:
MiniMoney does not hold, move, or take custody of funds (per
`Clarifications_v2.md`), substantially reducing money-transmitter
licensing risk. **Newly resolved per `Clarifications_v3.md`:** the
initial launch jurisdiction is confirmed as South Africa, making
**POPIA (Protection of Personal Information Act)** the specific
governing child-data-privacy law, rather than an unstated placeholder.

**Newly surfaced and NOT resolved — the central compliance concern of
this revision:** the user has described an intended consent model
modeled on Google Family Link: a child obtains "consent" by downloading
the app and signing up directly; the app does not restrict or monitor
the child's device; users over age 10 may opt out unilaterally at any
time; and if a child's account is linked to a parent, the parent is
*notified* (not asked for approval) so a conversation can occur if one
has not already. **The Incubator flags — as a compliance-risk observation,
not a legal ruling, since the Incubator has no legal authority — that this
model as described appears likely insufficient under POPIA.** POPIA
(Sections 34–35) generally requires **prior consent from a "competent
person"** (a parent or legal guardian) before an organization may process
a child's personal information, subject to narrow exceptions (e.g.
information already made public by the child with the competent person's
consent, or processing necessary for specific legal/public-interest
purposes) — a self-consent-by-signup model with post-hoc notification
rather than prior parental approval does not, on its face, match this
structure, particularly for a **financial** application that will process
data tied to real household earnings and payment amounts, which is
plausibly more sensitive than the general app-usage data Google Family
Link governs. This is a directional flag, not a legal determination — a
South African data-protection/POPIA-specialist legal opinion is required
before this can be resolved either way. The Incubator explicitly declines
to mark this section, or the Child Data & Consent extension below, as
resolved on the strength of the user's description alone.

Still open and unaddressed: (1) whether the youngest age band (6–9, who
per the description are not excluded from direct signup) can lawfully
create an account and have data processed under this model at all under
POPIA, versus needing a hard verified-parental-consent gate before any
data collection for that age band specifically; (2) app store policy
compliance for apps directed at children (Apple/Google both have specific
rules for kids' categories, including restrictions on data collection and
in-app purchase/subscription mechanics — now directly relevant given the
confirmed Freemium monetization path, which likely requires in-app
purchase flows that fall under child-category app store rules on both
platforms); (3) whether "payslip" and "invoice" terminology carries any
unintended regulatory implication (e.g. implying an employment
relationship) — unaffected by any clarification to date; (4) whether the
"linked parent, notified not asked" structure is legally sufficient even
for the 10–18 age band, or only reduces (without eliminating) risk
relative to the 6–9 band. None of items (1)–(4) is resolved by the source
or clarifications.

---

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Risks identifiable from the described mechanic and clarifications:
- **Regulatory risk (Critical, reduced but not closed):** the
  money-transmission licensing risk remains substantially narrowed (per
  `Clarifications_v2.md`). The jurisdiction ambiguity flagged in v2 is
  now resolved (South Africa, per `Clarifications_v3.md`), which
  *sharpens* rather than reduces the child-data compliance risk, because
  POPIA's specific requirements can now be assessed directly instead of
  hypothetically — and the assessment (see Legal & Compliance) suggests
  the described consent model likely does not meet POPIA's bar. Net
  effect: this risk is more precisely characterized in v3, but not
  smaller.
- **Child-safety/data-privacy risk (Critical, sharpened by
  clarification):** collecting data from 6-year-olds under a
  self-consent-by-signup model with no described verified-parental-
  consent gate for that age band is now a specific, named risk rather
  than a generic placeholder — the user's own description of the
  intended model (Google Family Link-style) is the source of this
  sharpened risk, not an Incubator assumption. This is the single most
  material open risk in the current business case.
- **Trust/enforcement risk (unchanged from v2):** because MiniMoney
  cannot itself detect or confirm that the parent's banking-app payment
  actually occurred, the system depends on either honor-system
  self-confirmation or a separate bank-linking integration to verify
  payment — no enforcement or fallback mechanism is described.
- **Terminology/perception risk (unchanged):** framing a child's
  allowance as "payslip," "overtime," and "expenses" could raise concerns
  among child psychologists or regulators about normalizing labor-like
  relationships between parent and child.
- **Competitive risk (unchanged in substance, narrowed geographically):**
  established kids'-fintech apps with debit cards and bank partnerships
  exist in the broader global category; whether any operate specifically
  in South Africa is unknown and unresearched, per Market & Competition.
- **Monetization-execution risk (narrowed from v2's "monetization-
  uncertainty risk" now that a direction is chosen):** Freemium is
  selected, but the specific paywalled features, pricing, and conversion
  assumptions are undefined; freemium models carry a well-known risk of
  under-monetizing if the free tier is too generous or over-restricting
  if it's too limited to build habit — neither has been designed yet.
- **App-store policy risk (elevated by the Freemium confirmation):** a
  freemium/in-app-purchase model targeting a children's-category app on
  Apple/Google carries specific platform restrictions (e.g. restrictions
  on behavioral advertising and certain monetization mechanics directed
  at children) that were previously a hypothetical concern across five
  candidate models and are now a concrete, must-resolve design
  constraint tied to the one chosen model.

---

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Assumptions made by the Incubator in order to complete this document, all
flagged as such:
- **Confirmed by clarification (no longer an assumption):** the parent
  pays the child directly from the parent's own existing bank account via
  the parent's own banking app; MiniMoney does not hold or move funds
  itself (`Clarifications_v2.md`). Initial launch jurisdiction is South
  Africa (`Clarifications_v3.md`). Monetization direction is Freemium
  with parent-unlockable features (`Clarifications_v3.md`).
- Still assumed: "points equivalent to real money" means a fixed or
  parent-configured conversion rate (e.g. 1 point = R1), not a
  floating/market-based value — neither document specifies the
  conversion mechanism.
- Still assumed: the app is intended primarily as a South African
  consumer (B2C) product at launch; whether multi-market expansion is
  planned, and on what timeline, is not stated.
- Carried from v2: that MiniMoney will need some form of payment-status
  confirmation (manual or automated) to make the payslip/invoice loop
  meaningful, since it has no technical visibility into whether the
  parent actually paid — this is an Incubator inference, not a stated
  design decision.
- **New assumption introduced in v3:** the Incubator assumes — pending a
  qualified legal opinion — that the described Family-Link-style consent
  model, as stated, is **not yet POPIA-compliant for the 6–9 age band**
  specifically, given POPIA's competent-person-consent requirement. This
  is an Incubator risk judgment, not a legal fact, and is explicitly
  flagged as requiring specialist verification rather than being treated
  as either confirmed-compliant or confirmed-non-compliant.
- **New assumption introduced in v3:** that "additional features" to be
  unlocked under Freemium will require some form of in-app purchase or
  subscription mechanism, which is an inference from standard freemium
  implementation patterns, not a stated design choice by the user.

---

## Constraints

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications. No budget, timeline,
team size, technical constraint, or platform constraint (iOS-only vs
cross-platform) is stated. The user's known technical stack (per general
working profile: Kotlin/Android, MQL5, Python, React/Three.js) is not
referenced anywhere in the case study or clarifications and therefore is
not used here as a stated constraint — it is flagged only as a possible
future input the user may wish to supply.

---

## Roadmap

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications as a stated plan. Given
the clarifications' narrowing of technical scope (no banking-rail
integration required for launch; monetization direction chosen as
Freemium; jurisdiction confirmed as South Africa), the Incubator flags —
as a suggestion only, not a stated plan — that an MVP could plausibly
sequence as follows: (1) resolve the Child Data & Consent compliance
question with a POPIA specialist before any build begins, since this
gates lawful data collection from the 6–9 age band entirely; (2) build
the free-tier core mechanic (task/points/expense-rules/invoice/payslip)
first to validate the curriculum-and-mechanic hypothesis with a South
African pilot group; (3) layer in the paywalled "additional features"
and freemium conversion mechanics only after free-tier engagement is
validated. This is a recommendation, not a roadmap supplied by the user.

---

## Financial Considerations

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications. No funding ask,
runway, unit economics, or financial projections are present. The
confirmed Freemium direction allows a more specific (though still
figure-free) framing than v2: financial viability will depend on
free-to-paid conversion rate, price point for unlocked features, and
customer acquisition cost in the South African market specifically —
none of which have been estimated or supplied. Financial considerations
still cannot be meaningfully modeled until these inputs are provided.

---

## Operations — Curriculum Design (Domain Extension)

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

*Appended because MiniMoney is an education product for a 12-year age
span (6–18) — the completion gate requires domain-specific sections for
products with curriculum design needs.* Unchanged by `Clarifications_v3.md`.
The case study states only that "education needs to be incorporated and
designed to appeal to the respective age demographic," without
specifying: age-band curriculum splits, learning objectives per band,
instructional format (game-based, video, quiz, narrative), alignment to
any existing financial literacy standard, or who authors the content. If
advanced curriculum content becomes one of the Freemium paywalled
features (Incubator-flagged possibility, not confirmed), its resolution
becomes more commercially urgent, but this is not yet specified by the
user.

---

## Legal & Compliance — Child Data & Consent (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Appended because MiniMoney targets users as young as age 6, triggering
child-directed-app compliance obligations beyond general Legal &
Compliance.* **Materially updated by `Clarifications_v3.md`** — upgraded
from v2's Incomplete to Partial, because the user has now described a
specific intended consent model rather than leaving the question fully
open. However, this upgrade reflects that the *design intent is now
stated*, not that the *compliance question is resolved* — the Incubator
explicitly does not certify the described model as sufficient.

Described model (per `Clarifications_v3.md`, modeled on Google Family
Link): a child obtains "consent" by downloading the app and signing up
directly; the app does not restrict or monitor the child's device
(distinguishing MiniMoney from a parental-control app); users older than
10 can opt out of the parent-link relationship at any time; if a child's
account is linked to a parent, the parent is notified (not asked for
approval) so a conversation can occur if it has not already.

**Unresolved, specifically:**
1. No mechanism is described for the 6–9 age band regarding consent
   prior to data collection, nor an opt-out equivalent to the 10+ band's
   right — this is the most acute gap, since POPIA's competent-person-
   consent requirement (see Legal & Compliance above) is least likely to
   be satisfied for this youngest band under a self-signup model.
2. Whether "notified, not asked for approval" for linked-parent accounts
   is sufficient for POPIA purposes at any age band is unresolved and
   requires specialist legal review — a notification-based structure is
   a materially weaker consent gate than prior-approval, and the
   Incubator judges (Evidence: Assumed, not a legal ruling) that this is
   unlikely to satisfy a "competent person consent" standard even for
   older minors if POPIA's provisions are read strictly.
3. Data retention/deletion policies for minors are not addressed.
4. Advertising/monetization restrictions common to children's app
   categories on Apple/Google (e.g. no behavioral ad targeting to
   under-13s) are not addressed, and are now directly relevant given the
   confirmed Freemium/in-app-purchase-likely monetization path.
5. Whether Google's own Family Link framework — which MiniMoney's model
   is stated to follow — is itself designed for general parental-control
   apps rather than financial apps processing earnings/payment data, and
   whether that distinction matters for POPIA purposes, is not addressed
   by the user and is flagged by the Incubator as a meaningful disanalogy
   worth specialist scrutiny.

This must be resolved — ideally via a South African data-protection
legal opinion — before any technical build begins, particularly before
any data collection from the 6–9 age band.

---

## Validation Strategy

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications as a user-proposed
plan. The Incubator recommends (as a gap flag, not a sourced fact) three
validation priorities given v3's changes: (1) obtain a POPIA-specific
legal opinion on the described consent model before any further product
investment, since this could force a redesign of the sign-up flow
entirely; (2) test the core assumption that parents will trust and
consistently execute/self-report the bank payment step, unaffected by
this revision; (3) test South African parent willingness-to-pay and
free-to-paid conversion expectations for the specific "additional
features" concept once defined, via a pricing-sensitivity survey or
smoke-test landing page, before committing engineering or curriculum-
production resources.

---

## Supporting Evidence

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

The case study and clarifications provide no external evidence: no
market research, no citations, no user interviews, no prior prototype,
no competitor benchmarking, no pricing research, and no legal opinion on
the described consent model. The entire Business Case rests on the
internal logical consistency of the mechanic described by the user plus
the clarifying facts supplied across v2 and v3, not on external
validation. This is explicitly flagged so the Investment Committee does
not mistake inference — including the Incubator's own compliance-risk
judgment on the consent model — for independently verified evidence.

---

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Carried forward from v2, with resolved items removed and new items added
per `Clarifications_v3.md`:

1. ~~Does MiniMoney ever hold, move, or touch funds itself?~~ **Resolved:**
   No — confirmed in `Clarifications_v2.md`.
2. ~~What jurisdiction(s) is MiniMoney intended to launch in first?~~
   **Resolved:** South Africa, per `Clarifications_v3.md`.
3. ~~Of the five monetization options proposed, which does the user want
   to prioritize?~~ **Resolved:** Freemium, per `Clarifications_v3.md`.
4. **New/critical:** Has the user obtained, or will the user obtain, a
   POPIA-specific legal opinion confirming whether the described
   Family-Link-style consent model (self-signup consent, no described
   verified-parental-consent gate for the 6–9 band, notification-not-
   approval for linked parents) is lawful for a South African financial-
   education app processing minors' data? This is now the single most
   urgent open question in the case.
5. **New:** What specific mechanism, if any, governs consent/eligibility
   for the 6–9 age band, given that the described model only specifies
   an opt-out right for users over 10?
6. What are the specific age-band splits for the curriculum (e.g. 6–9,
   10–13, 14–18) and who will author the content?
7. **New:** What specific "additional features" will be gated behind the
   Freemium paywall, and has any pricing or conversion-rate assumption
   been tested with target parents?
8. How will MiniMoney know or confirm that a parent has actually paid the
   invoice, given no visibility into the parent's banking app — honor-
   system self-confirmation, or a read-only bank-linking integration
   planned for later?
9. How is task completion verified (self-report, parent approval, photo
   proof, third-party integration)?
10. What is the intended platform (iOS, Android, both, web) and MVP
    scope/timeline?
11. Is there any existing prototype, wireframe, or prior research the
    user has already produced that could accelerate validation?
12. What conversion rate or mechanism governs "points equivalent to real
    money," and is it fixed or parent-configurable per family?
13. Has the user considered app store policy restrictions specific to
    apps in the "designed for kids" category on Apple App Store and
    Google Play — now directly relevant given the confirmed Freemium/
    in-app-purchase monetization path?
14. **New:** How is "linking" a child account to a parent account
    initiated — parent-invited, or child self-enters a parent identifier
    — and what happens if a child account is never linked to any parent
    at all (is that permitted, and if so, does the invoice/payslip loop
    to a real bank payment simply not apply)?

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
| Child Data & Consent (extension) ★ | Partial | 2x | 4 |

Points earned:
2+2+2+0+0+2+2+2+0+2+0+0+2+4+2+2+0+0+0+0+0+5+0+4 = **33**

Points possible: 21 non-critical sections × 5 = 105, plus 3 critical
sections × 5 × 2 = 30. Total possible = **135**

**Readiness Score = 33 / 135 = 24%**

**This score remains below the 70% completion gate threshold.** Child
Data & Consent moved from Critical + Incomplete (v2) to Critical +
Partial (v3) — this independently un-fails the "no Critical + Incomplete"
gate item, since Partial is no longer Incomplete. However, the overall
score remains far below 70%, and the underlying compliance concern
(likely insufficient consent model for the 6–9 band) is unresolved in
substance, only more precisely characterized.

### Critical Gaps

1. **Child Data & Consent (Critical, Partial — upgraded from Incomplete,
   but not resolved)** — the user has now described an intended consent
   model, but the Incubator judges it likely insufficient under POPIA
   for the 6–9 age band specifically, and this judgment itself requires
   specialist legal verification, not Incubator or Investment Committee
   assumption either way. This remains the single most urgent open item.
2. **Legal & Compliance (Critical, Partial)** — money-transmission risk
   remains narrowed; jurisdiction is now confirmed (South Africa/POPIA),
   which sharpens rather than resolves the child-consent question; app-
   store child-category compliance for the now-confirmed Freemium/in-app-
   purchase path remains open.
3. **Business Model (Partial — direction confirmed) / Revenue & Costs
   (still Incomplete)** — Freemium is now the chosen direction, but no
   specific paywalled features, pricing, or cost/revenue figures exist.
4. **Objectives / Success Criteria / Validation Strategy** — no
   measurable definition of success or testing approach exists yet;
   unaffected by `Clarifications_v3.md`.
5. **Market & Competition** — still entirely unaddressed, now narrowed to
   a South African competitive set that remains unresearched in any
   input document.

---

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Child Data &
  Consent moved from Incomplete to Partial in v3; Legal & Compliance is
  Partial; no critical section remains Incomplete.
- Readiness Score ≥ 70%: **No — FAILS.** Score is 24% (up from 21% in
  v2).
- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`.
- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate**,
though the Critical + Incomplete condition is now cleared. Progress was
made on Target Users/Customers, Business Model, and Legal & Compliance /
Child Data & Consent directly in response to `Clarifications_v3.md`.
However, the Readiness Score (24%) remains far below the 70% threshold —
Market & Competition, Objectives/Success Criteria, Validation Strategy,
Revenue & Costs figures, Constraints, Roadmap, and Curriculum Design
remain Incomplete, and the newly-described consent model, while no
longer a blank gap, introduces a specific, unresolved compliance concern
that the Incubator judges probably requires a product/design change (a
verified-parental-consent gate for the 6–9 band) rather than being
resolved as-is. This document is constructed under a strict no-invention
rule and is delivered in its current state deliberately: a v4 would need
further user input — ideally including a specialist POPIA legal opinion,
specific paywalled features, and basic objectives/success metrics — to
meaningfully advance the score.
