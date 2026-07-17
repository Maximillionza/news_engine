# Business Case: MiniMoney — v4

> Prepared by: Incubator
> Source input: `00_CaseStudy.md` (verbatim user submission, 2026-07-05),
> `BusinessCase_v3.md` (prior version), `Clarifications_v4.md` (user
> clarifications supplied after v3 gate failure, 2026-07-05).
> This document is self-certified against the Incubator completion gate.
>
> **Changes from v3** are driven entirely by `Clarifications_v4.md`, which
> supplied four things: (1) a revised consent model — every parent must
> give consent regardless of the minor's age, because the parent is
> legally responsible regardless of the child's ability to read/
> understand; the parent account is now primary and must exist before any
> minor can use the earnings features; the user intends to allow direct
> minor signup for the *education-only* portion, but explicitly defers to
> Incubator/expert judgment on whether that carve-out itself still poses a
> risk requiring a full lock-behind-parental-consent design instead; (2) a
> clarification that in-app purchases (real money) are restricted to the
> parent's account only, with minors interacting solely with an in-app
> points system (earned via tasks or parent-granted) redeemable for
> cosmetic items (stickers, themes) in an in-app store; (3) an explicit
> user request for Incubator research assistance on **Market &
> Competition**, **Objectives/Success Criteria/Validation Strategy**, and
> **Revenue & Costs**, since the user states they do not have this
> information themselves; and (4) curriculum clarity — the rationale for
> starting at age 6 (introduce financial literacy as early as possible),
> and a concrete instructional shape (a short daily/weekly completable
> course, not a full year of content, covering currency differentiation
> and "word sum" transactions to calculate change/remainder owed).
>
> **On item (3):** per the Chief of Staff's explicit instruction, this is
> handled the same way the Business Model monetization options were
> handled in v2 — the Incubator develops **candidate, clearly-flagged
> directional content** for these three sections, drawing on general
> market/business knowledge (not case-study-sourced facts), rather than
> either fabricating case-study-attributed data or leaving the sections
> untouched. Every such passage is explicitly marked **Incubator-proposed
> / general knowledge, not case-study-sourced** and carries **Evidence:
> Assumed**, never Verified or Supported. This materially improves the
> completeness of these sections but must not be mistaken by the
> Investment Committee for user-supplied or externally validated fact.
>
> Nothing beyond the case study, v3, and this clarification was used. All
> other sections are carried forward from v3 unchanged except where a
> clarification has a direct, logical knock-on effect (noted inline).

---

## What Changed in v4 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Per `Clarifications_v4.md`, this revision updates: **Legal & Compliance**
(including the **Child Data & Consent** domain extension) — the consent
model is substantially strengthened (universal, prior, parent-primary
consent replaces the Family-Link-style self-consent model flagged as
likely insufficient in v3) but a new specific open question is
introduced (the education-only carve-out for direct minor signup);
**Business Model** and **Technology** — in-app purchases are now
confirmed parent-only, with a separate non-monetary points/cosmetic
system for minors, which meaningfully de-risks the app-store
child-category in-app-purchase concern raised in v3; **Operations —
Curriculum Design** — concrete instructional shape and rationale now
supplied; and, per the Chief of Staff's explicit handling instruction,
**Market & Competition**, **Objectives**, **Success Criteria**,
**Validation Strategy**, and **Revenue & Costs** now contain
Incubator-developed candidate directional content, clearly flagged as
general-knowledge-based rather than case-study-sourced, since the user
stated they lack this information and requested research assistance.
All other sections are unchanged from v3 and are carried forward
verbatim below for a complete, standalone document. The Readiness Score
is recalculated accordingly.

**Headline finding of this revision:** the consent-model gap — the
single largest flagged risk in v3 — is substantially, though not
completely, addressed: requiring universal prior parental consent and a
parent-primary account structure directly answers the Incubator's v3
concern about the 6–9 band and the "notification, not approval"
mechanism. This is a genuine, material improvement, not a cosmetic one.
However, a new, narrower open question is introduced by the
education-only direct-signup carve-out, and the Incubator declines to
independently resolve it (see Legal & Compliance). Separately, the
Incubator-researched additions to Market & Competition, Objectives/
Success Criteria/Validation Strategy, and Revenue & Costs move those
sections from Incomplete to Partial, but — being general-knowledge-based
rather than sourced or validated — they do not, and should not, score as
Complete, since no actual market research, user testing, or financial
modeling has occurred. The combination of these changes raises the
Readiness Score meaningfully but the case still requires a specialist
legal opinion and real (not candidate) financial/market inputs before
it can be considered investment-ready.

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
**Freemium**, with the newly-confirmed detail (per `Clarifications_v4.md`)
that **any real-money in-app purchase is restricted to the parent's
account only** — children interact exclusively with a non-monetary
points system (earned via tasks or parent-granted) redeemable for
cosmetic items (stickers, themes) in a child-facing in-app store. Most
significantly, **the consent model has been substantially revised**: per
`Clarifications_v4.md`, every parent must give prior consent regardless
of the minor's age (because the parent bears legal responsibility
irrespective of the child's ability to read or understand), and the
**parent account is primary and must be established before any minor can
use the earnings features**. The user intends to allow direct minor
signup for the *education-only* portion of the app, while explicitly
deferring judgment to the Incubator/experts on whether that carve-out
itself still poses a compliance risk requiring the entire app to be
locked behind parental consent first. This is a materially stronger
starting position than the v3 Family-Link-style model the Incubator
judged likely POPIA-insufficient, though it does not yet close every
open question (see Legal & Compliance). Per the user's explicit request
in `Clarifications_v4.md`, this version also incorporates
Incubator-researched, clearly-flagged candidate content for Market &
Competition, Objectives/Success Criteria/Validation Strategy, and
Revenue & Costs — directional research support, not case-study-sourced
fact, intended to give the Investment Committee something concrete to
evaluate rather than blank sections.

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
by `Clarifications_v4.md`.

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
the source document. Unchanged in substance by `Clarifications_v4.md`;
see Market & Competition below for Incubator-researched candidate detail
on the competitive set.

---

## Objectives

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

*Updated per `Clarifications_v4.md`: the user explicitly stated they do
not have this information and requested Incubator research assistance.
The following is Incubator-developed candidate content based on general
product-management practice for early-stage consumer apps, not
case-study-sourced fact. It is offered as a starting framework for the
user to confirm, edit, or reject — not as a settled set of objectives.*

The case study itself states only a functional objective: build an app
that (1) assigns tasks, (2) converts completion into point-based
earnings, (3) applies percentage-based scalable expenses, (4) generates a
parent invoice and child payslip, (5) prompts/confirms a real bank
payment made by the parent via their own banking app, and (6) delivers
age-appropriate financial education, now further shaped by
`Clarifications_v4.md`'s parent-primary consent model and points/cosmetic
store for minors.

**Incubator-proposed candidate objectives (Evidence: Assumed, not
sourced):**
1. **Pre-launch:** resolve the parental-consent/education-carve-out
   compliance question (see Legal & Compliance) and validate the core
   task→payslip→payment loop with a small pilot cohort of South African
   families (candidate target: 20–50 families) before wider release.
2. **Launch (first 90 days):** achieve a target number of registered
   parent accounts (a specific number cannot be proposed responsibly
   without a marketing budget and CAC estimate — see Revenue & Costs) and
   validate that a meaningful majority of pilot families complete at
   least one full task→invoice→payment→payslip cycle without the
   Incubator-flagged trust/enforcement risk (see Risks) derailing the
   loop.
3. **Growth (6–12 months):** validate the Freemium conversion assumption
   (a specific free-to-paid conversion percentage cannot be proposed
   without market data — see Revenue & Costs) and validate curriculum
   engagement (e.g. percentage of children completing the daily/weekly
   micro-course, per the shape described in `Clarifications_v4.md`) as a
   leading indicator of retention.

These are candidate objectives only — none has been confirmed,
prioritized, or quantified by the user, and the Incubator is not in a
position to assert specific numeric targets (e.g. "1,000 users by month
3") without fabricating figures the user has not supplied. This section
is upgraded from v3's Incomplete to Partial on the strength of having a
structured candidate framework, not because measurable, user-confirmed
objectives now exist.

---

## Success Criteria

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

*Updated per `Clarifications_v4.md`'s explicit request for research
assistance. The following is Incubator-developed candidate content, not
case-study-sourced or user-confirmed.*

Candidate success criteria, mapped to the candidate objectives above:
- **Pilot success:** a defined percentage (candidate: majority) of pilot
  families complete at least 4 consecutive weekly task→payslip cycles
  without abandoning the app, and at least one family per cohort
  self-reports the parent successfully made the real bank payment each
  cycle.
- **Curriculum engagement:** a defined percentage (candidate: majority)
  of child users complete the daily/weekly micro-course content
  described in `Clarifications_v4.md` (currency differentiation,
  word-sum transactions) within the first month of use.
- **Freemium conversion:** a free-to-paid conversion rate benchmark
  (candidate reference point: consumer freemium apps commonly convert in
  the low single digits, e.g. 2–5%, though this varies enormously by
  category and MiniMoney has no comparable published benchmark — this is
  Incubator general knowledge, not a MiniMoney-specific figure and should
  not be treated as a target).
- **Retention:** a defined 90-day retention benchmark for the parent
  account (candidate framing only — no figure proposed, since retention
  benchmarks vary too widely by category to respectably estimate without
  comparable data).

None of these candidate criteria have been reviewed, confirmed, or
adjusted by the user. This section is upgraded from v3's Incomplete to
Partial because a structured candidate framework now exists for the user
and Investment Committee to react to, not because verified success
criteria exist.

---

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Directly named or clearly implied in the source:
- **Children/teens (6–18)** — the end users who complete tasks, earn
  points, and receive education content. Per `Clarifications_v4.md`,
  minors interact only with the non-monetary points/cosmetic system and
  the education content directly; the earnings/payslip features require
  an established, consenting parent account.
- **Parents/guardians** — who assign tasks, adjust the percentage-based
  expense rules, receive the automated invoice, execute the real bank
  payment via their own banking app (confirmed in `Clarifications_v2.md`
  — MiniMoney does not execute or touch this payment), are the freemium
  purchaser who unlocks additional features (confirmed in
  `Clarifications_v3.md`), and — newly per `Clarifications_v4.md` — are
  now the **primary account holder whose prior consent is mandatory
  before any minor can access the earnings features**, and the sole
  account type through which any real-money in-app purchase can occur.
- **The app operator (Masood / MiniMoney)** — owns the platform,
  curriculum content, and invoice/payslip-generation logic, but per the
  v2 clarification, not the payment rail itself.

Still relevant per `Clarifications_v3.md`: the **South African
Information Regulator** (the body that enforces POPIA). Still not
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
bank-account holder. Geography is confirmed per `Clarifications_v3.md`:
initial launch is South Africa. Per `Clarifications_v4.md`, the customer
relationship is now more precisely structured: the **parent account is
primary and must exist, with consent given, before a minor can access the
earnings features** — meaning the parent is unambiguously the
account-creating customer of record, while the child is a
secondary/dependent user whose access to specific feature sets (earnings
vs. education-only) may differ depending on how the still-open
education-only-carve-out question (see Legal & Compliance) is resolved.
The freemium model (per `Clarifications_v3.md` and `Clarifications_v4.md`)
implies two parent sub-segments: free-tier parents (acquisition/funnel)
and paying parents who unlock additional features — with in-app purchase
now confirmed as parent-only, this monetized segment is unambiguously the
parent, not the child, which simplifies the app-store child-directed
in-app-purchase compliance question somewhat (see Legal & Compliance).

---

## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household chores/tasks into
a structured payroll-like experience for their children, removing manual
tracking and adding a built-in financial literacy curriculum, with
expense rules that scale proportionally to earnings. For children: a
"real job" simulation — payslips, overtime, deductions — that pays out in
actual money via the parent's own bank transfer, tied to age-appropriate
lessons, alongside a separate, lower-stakes points/cosmetic-reward system
for engagement (per `Clarifications_v4.md`) that does not expose the
child to any real-money transaction. This separation — real money flows
only through the parent, cosmetic rewards flow to the child — may itself
be a value-proposition angle worth testing with parents concerned about
handing a minor any purchasing power ("your child earns and learns, but
never spends real money without you"). The clarification reinforces that
MiniMoney's value is specifically as an **education-and-facilitation
layer**, not a payments product. With Freemium confirmed as the
monetization direction and in-app purchases now confirmed parent-only,
the core value proposition must be strong enough in its free tier to
drive adoption before any parent-facing paywall is hit — what specific
features sit behind the paywall (per `Clarifications_v3.md`, "additional
features," still unspecified) remains unaddressed by the user.

---

## Market & Competition

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

*Per `Clarifications_v4.md`, the user explicitly requested Incubator
research assistance for this section, stating they do not have this
information. The following is Incubator-developed candidate content
based on general market knowledge, not case-study-sourced or verified
market research. It is offered so the Investment Committee and user have
a concrete starting point to react to, edit, or commission real research
against — it must not be mistaken for validated market analysis.*

**Candidate competitive category (Incubator general knowledge, Evidence:
Assumed):** MiniMoney sits adjacent to two overlapping global categories:
(1) **debit-card-for-kids / family fintech apps** — e.g. Greenlight,
GoHenry, RoosterMoney — which typically issue a real or virtual card to
the child, allow parent-controlled allowance/chore payments, and monetize
via a monthly parent subscription; and (2) **financial-literacy
edutainment apps for children** — a more fragmented category of
game/quiz-based apps with far less standardized business models. None of
these named competitors is confirmed to operate as a South
African-licensed product (per v3's inference); this remains unverified
and would require direct research (e.g. checking App Store/Play Store
South African listings) rather than Incubator assumption.

**Candidate positioning (Incubator-proposed, Evidence: Assumed):**
MiniMoney's distinguishing mechanic — a payroll-style
task→invoice→real-bank-payment→payslip loop, with MiniMoney never
holding funds — is structurally lighter-weight (no card issuance, no
money transmission) than Greenlight/GoHenry's card-based model. This
could be framed as a competitive advantage (lower regulatory burden,
faster to market, "you keep full control of your own bank account") or a
competitive disadvantage (no physical/virtual card = less "real-feeling"
for the child, no point-of-sale spend experience) depending on how
parents value those trade-offs. Neither framing has been tested with any
target user.

**Candidate market sizing approach (Incubator-proposed, Evidence:
Assumed, no figures fabricated):** a defensible market-sizing exercise
would typically start from (a) number of South African households with
children aged 6–18, (b) smartphone/banking-app penetration among parents
in that cohort, and (c) a plausible adoption rate for a paid-adjacent
financial-education app — none of these inputs are available in any
input document, and the Incubator declines to invent placeholder
population or penetration figures. This is flagged as a specific,
commissionable research task (e.g. via Statistics South Africa household
data, or a targeted parent survey) rather than something the Incubator
can responsibly estimate from general knowledge alone.

**What remains genuinely unresearched:** no direct South African
competitor is named or ruled out in any input document; no pricing
benchmark for a comparable South African product exists; no demand
signal (waitlist, survey, pilot interest) has been collected. This
section is upgraded from v3's Incomplete to Partial on the strength of
having a structured candidate framework and category identification, not
because actual market research or competitive analysis has been
performed.

---

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Confirmed structurally: MiniMoney is a facilitation/education layer that
sits on top of the parent's own bank account and does not move or hold
funds (per `Clarifications_v2.md`). This removes the need for a
money-transmitter license as a primary business-model constraint
(subject to full confirmation by a payments/compliance expert — see
Legal & Compliance).

**Chosen model — Freemium (confirmed per `Clarifications_v3.md`):**
- Free tier: the core task/points/expense-rules engine and
  invoice/payslip generation are available at no cost.
- Paid tier: parents can unlock "additional features" — the specific
  features are not yet specified by the user. Candidates the Incubator
  flags for the user's consideration (Incubator-proposed, Evidence:
  Assumed, not sourced): deeper/advanced curriculum content, multiple-
  child household management, customizable expense-rule templates, or
  parent reporting/analytics.
- **Newly confirmed per `Clarifications_v4.md`:** any real-money in-app
  purchase (i.e. the Freemium paywall unlock) is available **only through
  the parent's account**. Children never see or interact with a
  real-money purchase flow. Instead, children interact with a
  **non-monetary points system** — earned via task completion or
  granted directly by the parent — redeemable in a child-facing in-app
  store for **cosmetic items only** (stickers, themes, etc.), which
  carries no real-money value and is structurally separate from the
  Freemium paywall. This is a meaningful business-model clarification:
  it confirms MiniMoney has two entirely separate "currency" systems —
  real-money Freemium unlocks (parent-only) and cosmetic points
  (child-facing, non-monetary, earned/granted) — which should reduce (but
  the Incubator cannot confirm eliminate — see Legal & Compliance)
  app-store child-directed in-app-purchase policy risk, since the
  cosmetic points store does not appear to constitute a real-money
  transaction directed at a minor.
- The four other candidate models from v2 (parent subscription-only,
  B2B2C schools/employers, bank-partnership referral, one-time purchase)
  remain retired per `Clarifications_v3.md`, available only as fallback.

**Open implementation questions** (not addressed by any clarification to
date): what specific features are paywalled; pricing point/tier
structure; whether freemium conversion assumptions have been tested with
any target parents; and whether the cosmetic points store itself (even
though non-monetary) requires any app-store disclosure given it still
functions as a rewards/loot-adjacent mechanic aimed at children (an
Incubator-flagged consideration, Evidence: Assumed, not resolved).

---

## Revenue & Costs

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

*Per `Clarifications_v4.md`, the user explicitly requested Incubator
research assistance for this section, stating they do not have this
information. The following is Incubator-developed candidate content
based on general startup/app-economics knowledge, not case-study-sourced
figures. No dollar or rand amounts below should be read as MiniMoney-
specific estimates — they are illustrative benchmarks from the broader
consumer-app category, offered only to give the user and Investment
Committee a framework to populate with real numbers.*

**Candidate cost categories (Incubator-proposed, Evidence: Assumed):**
1. **Engineering/build cost** — task/points/expense-rules engine,
   invoice/payslip generation, parent-primary consent and account-linking
   flow (now more complex per `Clarifications_v4.md`'s universal prior-
   consent requirement), dual-currency system (real-money Freemium
   unlocks vs. non-monetary cosmetic points), and feature-entitlement/
   paywall logic. As a category, cross-platform consumer mobile apps of
   comparable scope (multi-user account linking, rules engine, document
   generation, in-app purchase) commonly run from tens of thousands to
   low hundreds of thousands of USD-equivalent in initial build cost
   depending on team composition (in-house vs. contracted, South Africa
   vs. offshore rates) — this is a general industry range, not a
   MiniMoney-specific quote, and the user's own technical background
   (per general working profile, unstated in any case-study input) could
   plausibly reduce this if self-built.
2. **Curriculum content production cost** — likely the largest *recurring*
   cost if age-banded content requiring periodic updates is needed. Per
   `Clarifications_v4.md`, the described shape (a short daily/weekly
   completable course per age band, not a full year of content) is
   more tractable and lower-cost than a full curriculum build, which
   somewhat de-risks this cost category relative to v3's framing.
3. **Customer acquisition cost (CAC)** — no South African benchmark exists
   in any input document. General consumer-app CAC in comparable
   categories (family/parenting apps) varies enormously by channel
   (organic/App Store Optimization vs. paid social) and is not
   responsibly estimable without a defined marketing channel strategy,
   which has not been supplied.
4. **Legal/compliance cost** — a POPIA-specialist legal opinion (see
   Legal & Compliance) is a near-term, essential, and estimable line
   item even in the absence of other figures — this is the one cost
   category the Incubator recommends the user obtain an actual quote for
   before further product investment, since it is a bounded, one-time
   legal engagement rather than an open-ended estimate.

**Candidate revenue framing (Incubator-proposed, Evidence: Assumed):**
Freemium revenue = (number of active parent accounts) × (free-to-paid
conversion rate) × (price point for unlocked features), none of which
are populated with real figures here. The Incubator explicitly declines
to propose a specific price point or conversion rate as if it were
MiniMoney-specific — general consumer freemium conversion benchmarks
(commonly low single digits, e.g. 2–5%, though this varies by category
and is not MiniMoney-validated) are noted only as an industry reference
point, not a target or forecast.

This section is upgraded from v3's Incomplete to Partial on the strength
of a structured cost/revenue framework and category-level detail, not
because actual figures, quotes, or validated benchmarks specific to
MiniMoney now exist. Real numbers — even rough ones — from the user or a
finance-focused expert remain a prerequisite for any meaningful financial
modeling.

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
`Clarifications_v4.md`.

---

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The case study and clarifications together imply: a mobile app (platform
unspecified — iOS/Android/both not stated), a task-assignment and
point-calculation engine, a percentage-based rules engine for "expenses"
(parent-adjustable defaults), a document-generation feature (invoice for
parent, payslip for child), no integration with banking rails to move
money (per `Clarifications_v2.md`), a feature-entitlement/paywall system
to support the Freemium model (per `Clarifications_v3.md`), and — newly
per `Clarifications_v4.md` — a **dual-account architecture** in which a
parent account must be created and must give consent *before* any linked
minor account can access earnings features, plus a **dual-currency
system**: real-money Freemium entitlements (parent-account-only) and a
separate non-monetary points ledger for minors (earned via task
completion or parent grant, spendable only in a cosmetic in-app store).
This is a more architecturally complex account/permission model than v3
described (which envisioned a lighter-weight, notification-based
parent-child link) — the technical scope now explicitly requires
enforcing that a minor account *cannot* access earnings features, invoice
generation, or any real-money purchase flow until a parent account with
recorded consent exists and is linked. What remains unspecified: how
"linking" a child account to a parent account is technically initiated
(parent-invited, or child enters a parent identifier subject to parent
approval), how payment confirmation is captured (unresolved since v2),
and whether the education-only content (if a minor is permitted to
directly sign up for it, per `Clarifications_v4.md`) is technically
gated in a separate, lower-permission account mode from the full
parent-linked account, or whether that mode will exist at all pending
resolution of the open compliance question below.

---

## Legal & Compliance

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This section remains flagged Critical.** Resolved from prior versions:
MiniMoney does not hold, move, or take custody of funds (per
`Clarifications_v2.md`), substantially reducing money-transmitter
licensing risk. Initial launch jurisdiction is confirmed as South Africa,
making **POPIA (Protection of Personal Information Act)** the specific
governing child-data-privacy law (per `Clarifications_v3.md`).

**Materially strengthened per `Clarifications_v4.md`:** the user has
revised the consent model away from the Family-Link-style self-consent
approach the Incubator judged likely POPIA-insufficient in v3. The new
described model is: **every parent must give consent regardless of the
minor's age**, because the parent bears legal responsibility irrespective
of the child's ability to read or understand; and the **parent account
is primary and must be established, with consent recorded, before any
minor can access the earnings features**. This directly answers the v3
concern that the youngest band (6–9) had no described consent gate at
all, and replaces "notification, not approval" with what is described as
consent obtained up front. **The Incubator judges this a genuine,
material improvement** that moves the design intent much closer to
POPIA's competent-person-consent structure (Sections 34–35) for the
earnings features specifically. This is still a directional Incubator
judgment, not a legal certification — the Incubator has no legal
authority to confirm POPIA compliance, and a specialist opinion remains
required, but the gap between the described model and POPIA's apparent
requirements is now substantially narrower than in v3.

**Newly surfaced and NOT resolved — the central open compliance question
of this revision:** the user states an intent to "allow users to sign up
for the education portion of the app" directly (i.e. without a
pre-existing, consenting parent account), while explicitly stating "if
this still poses a risk, [I intend] to lock everything behind a parental
consent being required first" — i.e. the user has deferred this specific
design decision to Incubator/expert judgment rather than asserting the
education-only carve-out is safe. **The Incubator declines to resolve
this on the user's behalf.** The relevant question a specialist must
answer: does POPIA's competent-person-consent requirement apply
differently (or not at all) to an "education-only" mode that collects
some data (e.g. account creation, usage/progress data, possibly age) but
does not process financial/earnings data? The Incubator's non-binding
observation is that POPIA's definition of "personal information" is not
limited to financial data — a child's name, age, and usage data collected
at direct signup for the education-only mode would still plausibly
constitute personal information requiring competent-person consent,
which would suggest the education-only carve-out carries meaningful
residual risk even though it avoids the *financial*-data sensitivity that
made the v3 model particularly concerning. This is a directional flag,
not a legal determination.

Still open and unaddressed: (1) app store policy compliance for
children's-category apps (Apple/Google) — now somewhat narrower in scope
given in-app purchases are confirmed parent-only (per
`Clarifications_v4.md`), but the cosmetic points/rewards store aimed at
children may still trigger child-directed-app disclosure or design
requirements even without real-money transactions, and this is
unresolved; (2) whether "payslip" and "invoice" terminology carries any
unintended regulatory implication (e.g. implying an employment
relationship) — unaffected by any clarification to date; (3) data
retention/deletion policies for minors, unaddressed; (4) whether the
education-only direct-signup mode, if built, would need its own
separate, lighter-weight consent mechanism distinct from the
earnings-feature consent gate, or whether the user's stated fallback
(lock everything behind parental consent) is the safer and simpler path
the Incubator would recommend absent a favorable legal opinion
specifically permitting the carve-out.

---

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Risks identifiable from the described mechanic and clarifications:
- **Regulatory risk (Critical, further narrowed by `Clarifications_v4.md`
  but not closed):** the money-transmission licensing risk remains
  substantially narrowed (per `Clarifications_v2.md`). The child-consent
  risk is materially reduced by the revised universal prior-consent,
  parent-primary model, but the new education-only carve-out question
  (see Legal & Compliance) introduces a fresh, narrower open item rather
  than leaving the risk fully closed.
- **Child-safety/data-privacy risk (Critical, reduced but not
  eliminated):** the previously most acute risk — no described consent
  gate for the 6–9 band — is directly addressed by the revised model. The
  residual risk is now narrower and specific: whether an education-only
  direct-signup mode (if built as described) can lawfully collect any
  personal information from a minor without prior parental consent, even
  where no financial data is involved.
- **Trust/enforcement risk (unchanged from v2):** because MiniMoney
  cannot itself detect or confirm that the parent's banking-app payment
  actually occurred, the system depends on either honor-system
  self-confirmation or a separate bank-linking integration to verify
  payment — no enforcement or fallback mechanism is described.
- **Terminology/perception risk (unchanged):** framing a child's
  allowance as "payslip," "overtime," and "expenses" could raise concerns
  among child psychologists or regulators about normalizing labor-like
  relationships between parent and child.
- **Competitive risk (unchanged in substance; see Market & Competition
  for Incubator-researched candidate detail):** established kids'-fintech
  apps with debit cards and bank partnerships exist in the broader global
  category; whether any operate specifically in South Africa remains
  unresearched with certainty.
- **Monetization-execution risk (narrowed further by
  `Clarifications_v4.md`'s parent-only IAP confirmation, but still
  present):** Freemium is selected and IAP is now confirmed parent-only,
  which reduces app-store child-directed-purchase risk, but the specific
  paywalled features, pricing, and conversion assumptions remain
  undefined; see Revenue & Costs for Incubator-researched candidate
  framing.
- **App-store policy risk (reduced by the parent-only IAP confirmation,
  but not eliminated):** restricting real-money purchases to the parent
  account meaningfully reduces the most acute version of this risk
  (children directly making in-app purchases), but the cosmetic
  points/rewards store aimed at children may still be subject to
  child-directed-app design and disclosure requirements on both
  platforms, which remains unresolved.
- **Dual-currency design/perception risk (new, introduced by
  `Clarifications_v4.md`):** operating two parallel "currency" systems —
  real-money-pegged points for earnings/education, and a separate
  non-monetary points system for cosmetic rewards — creates a risk of
  child (or even parent) confusion between the two, particularly since
  both are described using the word "points." Clear in-product naming and
  visual distinction between the two systems will likely be necessary; no
  such distinction has been described yet.

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
  with parent-unlockable features (`Clarifications_v3.md`). Real-money
  in-app purchases are parent-account-only; minors use a separate
  non-monetary, cosmetic-redeemable points system (`Clarifications_v4.md`).
  The parent account is primary and consent-gated before any minor can
  access earnings features, and this consent requirement applies
  regardless of the minor's age (`Clarifications_v4.md`).
- Still assumed: "points equivalent to real money" (the earnings
  mechanic) means a fixed or parent-configured conversion rate (e.g. 1
  point = R1), not a floating/market-based value — neither document
  specifies the conversion mechanism. Note this is a distinct concept
  from the newly-clarified non-monetary cosmetic points system, and the
  Incubator flags a naming-collision risk between the two (see Risks).
- Still assumed: the app is intended primarily as a South African
  consumer (B2C) product at launch; whether multi-market expansion is
  planned, and on what timeline, is not stated.
- Carried from v2: that MiniMoney will need some form of payment-status
  confirmation (manual or automated) to make the payslip/invoice loop
  meaningful, since it has no technical visibility into whether the
  parent actually paid — this is an Incubator inference, not a stated
  design decision.
- **Revised in v4 (previously an assumption in v3, now more precisely
  characterized):** the Incubator no longer assumes the described consent
  model is likely POPIA-insufficient for the 6–9 band — the revised
  universal, prior, parent-primary consent model is judged a material
  improvement — but continues to flag, pending specialist legal opinion,
  that the education-only direct-signup carve-out (if built) plausibly
  still requires its own consent gate under POPIA's general definition of
  personal information, not only financial data.
- **New assumption introduced in v4:** all Market & Competition,
  Objectives, Success Criteria, Validation Strategy, and Revenue & Costs
  candidate content added in this revision is Incubator-generated from
  general market/business knowledge per the user's explicit request for
  research assistance — none of it is case-study-sourced, user-confirmed,
  or externally validated, and all of it requires real research, user
  testing, or user confirmation before being treated as fact.
- Carried from v3: that "additional features" to be unlocked under
  Freemium will require some form of in-app purchase or subscription
  mechanism — now confirmed parent-facing only per `Clarifications_v4.md`,
  but the specific features remain unspecified.

---

## Constraints

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study or clarifications. No budget, timeline,
team size, technical constraint, or platform constraint (iOS-only vs
cross-platform) is stated. The user's known technical stack (per general
working profile: Kotlin/Android, MQL5, Python, React/Three.js) is not
referenced anywhere in the case study or clarifications and therefore is
not used here as a stated constraint — it is flagged only as a possible
future input the user may wish to supply. Unchanged by
`Clarifications_v4.md`.

---

## Roadmap

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

Not addressed in the case study or clarifications as a stated plan by the
user. Given the clarifications' narrowing of scope (no banking-rail
integration required for launch; monetization direction chosen as
Freemium with parent-only IAP; jurisdiction confirmed as South Africa;
consent model substantially strengthened), the Incubator flags — as a
suggestion only, not a stated plan — an updated candidate MVP sequence:
(1) obtain a specialist POPIA legal opinion specifically on (a) whether
the revised universal prior-consent, parent-primary model is compliant
for the earnings features, and (b) whether the education-only
direct-signup carve-out is separately permissible or must also be
consent-gated — this gates the entire build, not just the 6–9 band, as
it did in v3; (2) build the free-tier core mechanic (task/points/
expense-rules/invoice/payslip) with the parent-primary consent gate
enforced from the start, and the separate non-monetary cosmetic points
system, to validate the curriculum-and-mechanic hypothesis with a South
African pilot group; (3) layer in the paywalled "additional features" and
Freemium conversion mechanics only after free-tier engagement is
validated. This is a recommendation, not a roadmap supplied by the user,
and is upgraded from v3's Incomplete to Partial only because it now
reflects the updated compliance and product-architecture facts from
`Clarifications_v4.md`, not because the user has supplied an actual
timeline, milestone plan, or resourcing detail.

---

## Financial Considerations

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

*Per `Clarifications_v4.md`, the user requested Incubator research
assistance; see Revenue & Costs above for the full candidate cost/revenue
framework, which is summarized here rather than repeated.* No funding
ask, runway, or financial projections are present in any input document.
The Incubator-developed candidate framework (Revenue & Costs) identifies
engineering/build cost, curriculum production cost, customer acquisition
cost, and legal/compliance cost as the primary cost categories, and
Freemium conversion × price point as the primary revenue lever — all
without specific figures, since none were supplied and the Incubator
declines to fabricate them. The one cost item the Incubator recommends
the user obtain a real, bounded quote for in the near term is the
POPIA-specialist legal opinion (see Legal & Compliance), since it is
both a prerequisite to further build investment and a cost category that
can be estimated now via direct inquiry, unlike engineering or CAC costs
which depend on decisions not yet made. This section is upgraded from
v3's Incomplete to Partial on the strength of a structured candidate
framework, not because actual financial projections, funding
requirements, or runway figures now exist.

---

## Validation Strategy

**Status:** Partial | **Confidence:** Low | **Evidence:** Assumed

*Per `Clarifications_v4.md`'s explicit request for research assistance,
the following updates and extends v3's Incubator-recommended validation
priorities with candidate methods, not user-supplied or sourced fact.*

Recommended validation priorities, in sequence:
1. **Legal validation (highest priority, gating):** obtain a POPIA-
   specific legal opinion covering both (a) the revised universal
   prior-consent, parent-primary model for earnings features, and (b) the
   education-only direct-signup carve-out — before any further product
   or curriculum investment, since an unfavorable opinion on (b) could
   require collapsing the two account modes into one (i.e. the user's own
   stated fallback of locking everything behind parental consent).
2. **Trust/enforcement validation (unaffected by this revision):** test
   the core assumption that parents will trust and consistently
   execute/self-report the real bank payment step, since MiniMoney has no
   technical visibility into whether payment actually occurred.
3. **Market/demand validation (Incubator-proposed candidate method,
   Evidence: Assumed):** given the user's stated lack of market
   information, a low-cost first step would be a smoke-test (e.g. a
   landing page describing the concept, offering pilot-cohort signup,
   measuring interest conversion) targeted at South African parents,
   before committing engineering or curriculum-production resources —
   this is a standard early-stage validation technique, not a
   MiniMoney-specific plan the user has confirmed.
4. **Pricing/conversion validation (Incubator-proposed candidate method):**
   once specific paywalled "additional features" are defined, a
   pricing-sensitivity survey (e.g. Van Westendorp-style or simple
   willingness-to-pay questions) with target parents, before finalizing
   the Freemium price point.
5. **Curriculum validation (new, informed by `Clarifications_v4.md`'s
   curriculum shape detail):** pilot-test the described daily/weekly
   micro-course (currency differentiation, word-sum transactions) with a
   small group of children across the stated age range to confirm
   engagement and comprehension before scaling content production across
   all age bands.

This section is upgraded from v3's Incomplete to Partial on the strength
of a structured, prioritized candidate validation plan, not because any
validation activity has actually occurred.

---

## Supporting Evidence

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

The case study and clarifications provide no external evidence: no
market research, no citations, no user interviews, no prior prototype,
no competitor benchmarking, no pricing research, and no legal opinion on
the described consent model. The Market & Competition, Objectives/
Success Criteria/Validation Strategy, and Revenue & Costs candidate
content added in this v4 revision is explicitly **Incubator-generated
from general knowledge, not external evidence** — it does not count as
supporting evidence and must not be read as such. The entire Business
Case rests on the internal logical consistency of the mechanic described
by the user plus the clarifying facts supplied across v2, v3, and v4, not
on external validation. This is explicitly flagged so the Investment
Committee does not mistake inference — including the Incubator's own
compliance-risk judgment on the consent model and its candidate research
content — for independently verified evidence.

---

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Carried forward from v3, with resolved items removed and new items added
per `Clarifications_v4.md`:

1. ~~Does MiniMoney ever hold, move, or touch funds itself?~~ **Resolved:**
   No — confirmed in `Clarifications_v2.md`.
2. ~~What jurisdiction(s) is MiniMoney intended to launch in first?~~
   **Resolved:** South Africa, per `Clarifications_v3.md`.
3. ~~Of the five monetization options proposed, which does the user want
   to prioritize?~~ **Resolved:** Freemium, per `Clarifications_v3.md`.
4. ~~Has the user obtained, or will the user obtain, a POPIA-specific
   legal opinion confirming whether the described consent model is
   lawful?~~ **Partially resolved / re-scoped:** the consent model itself
   is now substantially revised and strengthened (universal prior
   consent, parent-primary account) per `Clarifications_v4.md`, but a
   specialist legal opinion has not yet been obtained, and a new, more
   specific question (below) has emerged from the revision.
5. **New/critical:** Does the intended **education-only direct-signup
   carve-out** (allowing a minor to sign up directly for education
   content without a pre-existing consenting parent account) require its
   own POPIA consent gate, given that POPIA's personal-information
   definition is not limited to financial data? The user has explicitly
   deferred this design decision to Incubator/expert judgment rather than
   asserting it is safe — this is now the single most urgent open
   question in the case.
6. ~~What specific mechanism, if any, governs consent/eligibility for the
   6–9 age band?~~ **Resolved:** universal prior parental consent
   applies regardless of age, per `Clarifications_v4.md` — subject to
   item 5 above for the education-only carve-out specifically.
7. What are the specific age-band splits for the curriculum (e.g. 6–9,
   10–13, 14–18), and who will author the content? (Partially informed by
   `Clarifications_v4.md`'s description of a short daily/weekly course
   covering currency differentiation and word-sum transactions, but exact
   band splits and authorship remain unspecified.)
8. What specific "additional features" will be gated behind the Freemium
   paywall (now confirmed parent-only per `Clarifications_v4.md`), and has
   any pricing or conversion-rate assumption been tested with target
   parents?
9. How will MiniMoney know or confirm that a parent has actually paid the
   invoice, given no visibility into the parent's banking app — honor-
   system self-confirmation, or a read-only bank-linking integration
   planned for later?
10. How is task completion verified (self-report, parent approval, photo
    proof, third-party integration)?
11. What is the intended platform (iOS, Android, both, web) and MVP
    scope/timeline?
12. Is there any existing prototype, wireframe, or prior research the
    user has already produced that could accelerate validation?
13. What conversion rate or mechanism governs "points equivalent to real
    money" (the earnings mechanic), and is it fixed or parent-configurable
    per family? **Related new question:** how will this earnings-points
    system be named/distinguished in-product from the separate
    non-monetary cosmetic points system introduced in
    `Clarifications_v4.md`, to avoid child/parent confusion between the
    two?
14. Has the user considered app-store policy restrictions specific to
    apps in the "designed for kids" category, particularly regarding the
    child-facing cosmetic points/rewards store (even though non-monetary),
    given the confirmed parent-only real-money IAP model?
15. How is "linking" a child account to a parent account initiated —
    parent-invited, or child self-enters a parent identifier subject to
    parent approval — and does the parent-primary requirement mean a
    minor cannot create any account at all (including education-only)
    without a parent account already existing, pending resolution of
    question 5?
16. **New, per the Incubator's explicit research-assistance role in this
    revision:** does the user wish to commission real market research
    (competitor scan, parent survey, or smoke-test landing page) to
    replace the Incubator's candidate Market & Competition / Objectives /
    Success Criteria / Revenue & Costs content with validated figures, or
    proceed to Investment Committee review with the candidate framing
    explicitly flagged as unvalidated?

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
| Objectives | Partial | 1x | 2 |
| Success Criteria | Partial | 1x | 2 |
| Stakeholders | Partial | 1x | 2 |
| Target Users/Customers | Partial | 1x | 2 |
| Value Proposition | Partial | 1x | 2 |
| Market & Competition | Partial | 1x | 2 |
| Business Model | Partial | 1x | 2 |
| Revenue & Costs | Partial | 1x | 2 |
| Operations | Incomplete | 1x | 0 |
| Technology | Partial | 1x | 2 |
| Legal & Compliance ★ | Partial | 2x | 4 |
| Risks | Partial | 1x | 2 |
| Assumptions | Partial | 1x | 2 |
| Constraints | Incomplete | 1x | 0 |
| Roadmap | Partial | 1x | 2 |
| Financial Considerations | Partial | 1x | 2 |
| Validation Strategy | Partial | 1x | 2 |
| Supporting Evidence | Incomplete | 1x | 0 |
| Outstanding Questions | Complete | 1x | 5 |
| Curriculum Design (extension) | Partial | 1x | 2 |
| Child Data & Consent (extension) ★ | Partial | 2x | 4 |

Points earned:
2+2+2+2+2+2+2+2+2+2+2+0+2+4+2+2+0+2+2+2+0+5+2+4 = **49**

Points possible: 21 non-critical sections × 5 = 105, plus 3 critical
sections × 5 × 2 = 30. Total possible = **135**

**Readiness Score = 49 / 135 = 36%**

**This score remains below the 70% completion gate threshold**, though it
represents a substantial improvement from v3's 24%. No section is
Critical + Incomplete: Legal & Compliance and Child Data & Consent are
both Partial (strengthened, not weakened, by this revision); Operations,
Constraints, and Supporting Evidence remain Incomplete but are not
Critical-flagged sections.

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial,
   materially strengthened but not resolved)** — the revised universal
   prior-consent, parent-primary model is a genuine improvement over v3's
   design, but the new education-only direct-signup carve-out introduces
   a fresh, unresolved compliance question that the user has explicitly
   deferred to expert judgment. A specialist POPIA legal opinion covering
   both the core model and the carve-out remains the single most urgent
   prerequisite before further build investment.
2. **Operations (Incomplete)** — task verification, dispute handling, and
   payment-confirmation mechanisms remain entirely unaddressed across all
   four versions of this case.
3. **Constraints (Incomplete)** — no budget, timeline, team size, or
   platform constraint has been supplied in any version.
4. **Supporting Evidence (Incomplete)** — no external market research,
   user testing, prior prototype, or legal opinion exists; this v4's
   Incubator-researched candidate content for Market & Competition,
   Objectives/Success Criteria/Validation Strategy, and Revenue & Costs
   explicitly does not count as supporting evidence and is flagged as
   such throughout.
5. **Market & Competition / Revenue & Costs / Objectives-Success
   Criteria-Validation Strategy (all upgraded to Partial via
   Incubator-researched candidate content, per explicit user request)** —
   these sections now contain a structured framework rather than being
   blank, but none of the content is validated, sourced, or
   user-confirmed; real research or user input is still required before
   these can be scored as Complete.

---

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Appended because MiniMoney is an education product for a 12-year age
span (6–18) — the completion gate requires domain-specific sections for
products with curriculum design needs.* **Updated by
`Clarifications_v4.md`:** the user has now supplied a rationale and a
concrete instructional shape, upgrading this section from v3's
Incomplete to Partial. Rationale: the age floor of 6 is intentional,
specifically to introduce financial literacy "as early as 6." Shape: the
curriculum does not need to be a full year's worth of content, but rather
a **short course completable daily or weekly**, with example mechanics
including: (a) differentiating between different currencies, and (b)
basic transactions that introduce "word sums" (word-problem-style
arithmetic) as a mechanism for the child to derive what remains owed or
returned after paying for goods or services.

**Still unresolved:** specific age-band curriculum splits (e.g. 6–9,
10–13, 14–18) and learning objectives per band; instructional format
beyond "a short daily/weekly completable course" (game-based, video,
quiz, narrative — unspecified); alignment to any existing financial
literacy standard; who authors the content. If advanced curriculum
content becomes one of the Freemium paywalled features
(Incubator-flagged possibility, not confirmed), its resolution becomes
more commercially urgent, but this is not yet specified by the user.

---

## Legal & Compliance — Child Data & Consent (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Appended because MiniMoney targets users as young as age 6, triggering
child-directed-app compliance obligations beyond general Legal &
Compliance.* **Materially updated by `Clarifications_v4.md`** — the
described consent model is substantially strengthened relative to v3, but
this section remains Partial (not Complete) because a specialist legal
opinion has not been obtained and a new specific question (the
education-only carve-out) is unresolved.

**Revised model (per `Clarifications_v4.md`):** every parent must give
prior consent before a linked minor can access the app's earnings
features, regardless of the minor's age — because the parent bears legal
responsibility irrespective of the child's ability to read or understand
the consent itself. The parent account is primary and must be
established, with consent recorded, before any minor account can access
earnings features. The user intends to allow direct minor signup for an
education-only mode without this gate, but explicitly states: "if this
still poses a risk, [I intend] to lock everything behind a parental
consent being required first" — i.e. this specific design choice is
deferred to expert/Incubator judgment, not asserted as resolved.

**Resolved relative to v3:**
1. The 6–9 age band now has a described consent mechanism (universal
   prior parental consent, not age-dependent) — this was the single most
   acute gap in v3 and is directly addressed.
2. The "notified, not asked for approval" structure is replaced by prior
   consent — a materially stronger gate that the Incubator judges much
   more likely to satisfy a "competent person consent" standard, subject
   to specialist confirmation.
3. In-app purchases are confirmed parent-only, reducing (though not
   necessarily eliminating, per Risks) app-store child-directed-purchase
   compliance concerns.

**Unresolved, specifically:**
1. **The education-only direct-signup carve-out** — the central open
   question of this revision. POPIA's definition of personal information
   is not limited to financial data; a minor signing up directly for
   education-only content would still plausibly have personal information
   collected (name, age, usage/progress data) that may require
   competent-person consent under POPIA regardless of whether financial
   data is involved. This requires specialist confirmation before the
   carve-out is built; absent a favorable opinion, the user's own stated
   fallback (lock everything behind parental consent) is the safer
   design.
2. Data retention/deletion policies for minors are not addressed.
3. Advertising/monetization restrictions common to children's app
   categories on Apple/Google (e.g. no behavioral ad targeting to
   under-13s) are not addressed; somewhat narrowed in relevance now that
   real-money IAP is parent-only, but the cosmetic points/rewards store
   aimed at children may still be in scope.
4. Whether "payslip" and "invoice" terminology carries any unintended
   regulatory implication (e.g. implying an employment relationship) —
   unaffected by any clarification to date.
5. Whether the dual-currency system (real-money-pegged earnings points
   vs. non-monetary cosmetic points) requires distinct disclosure or
   design treatment under child-directed app store policies, given both
   are described using the word "points" and could be conflated by
   reviewers or regulators even if the underlying mechanics are properly
   separated in the product itself.

This must be resolved — ideally via a South African data-protection
legal opinion covering both the core consent model and the education-only
carve-out specifically — before any technical build begins.

---

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Child Data & Consent are both Partial, strengthened
  relative to v3.
- Readiness Score ≥ 70%: **No — FAILS.** Score is 36% (up from 24% in
  v3).
- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`.
- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`.
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate**,
though the Critical + Incomplete condition remains cleared and the
Readiness Score has improved substantially (24% → 36%) as a direct result
of `Clarifications_v4.md`'s consent-model revision and the Incubator's
research-assistance additions to Market & Competition, Objectives/Success
Criteria/Validation Strategy, and Revenue & Costs. The score remains well
below the 70% threshold because: (a) Operations, Constraints, and
Supporting Evidence remain entirely Incomplete across all four versions;
(b) the newly-added candidate research content, while structurally
useful, is explicitly unvalidated and cannot score as Complete; and (c)
the education-only consent carve-out introduces a new, specific,
unresolved compliance question rather than fully closing the Legal &
Compliance / Child Data & Consent gap. This document is constructed under
a strict no-invention rule and is delivered in its current state
deliberately: a v5 would need a specialist POPIA legal opinion (covering
both the core consent model and the carve-out), a decision on whether to
commission real market/financial research to replace this version's
candidate content, and basic operational/constraint inputs (budget,
timeline, task-verification design) to meaningfully advance the score
further.
