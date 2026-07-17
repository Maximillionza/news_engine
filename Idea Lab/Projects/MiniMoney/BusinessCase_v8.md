# Business Case: MiniMoney — v8

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v7.md` (prior version — note:
> v7 was hand-edited directly by the user, not produced by the
> Incubator, before reaching this revision), `Clarifications_v8.md`
> (user-supplied clarifications and explicit risk-acceptance decisions,
> 2026-07-08). This document is self-certified against the Incubator
> completion gate.

> **Changes from v7 — summary of what the Incubator is scrutinizing this
> revision:** `BusinessCase_v7.md` on disk was hand-edited directly by
> the user after the Incubator produced it, adding: (1) a claimed
> 10-family interview result in Problem; (2) a distribution-model
> clarification in Opportunity (schools partnership as an intended
> parallel channel, not a rejected alternative); (3) a 90-day download
> target (15,000) in Objectives; (4) company-side Constraints detail
> (solopreneur venture, AI-assisted/"vibe coding" build approach,
> external expertise on-demand, ~3-month build timeline, deliberately
> non-granular); (5) two explicit risk-accepted assumptions (POPIA
> retention sufficiency; exam-bonus mechanic has no schools-data-privacy
> dimension); (6) a stated policy deferring the specialist POPIA/ARB
> legal opinion to post-Investment-Committee (build-spec stage); and
> (7) a resolved monetization decision (subscription-only at launch, ads
> deferred to a possible V2). `Clarifications_v8.md` documents all of
> this precisely, including the Chief of Staff's follow-up clarification
> resolving the ambiguous wording of the interview result: **"6 of 10
> confirmed interest in using the app, and would pay for it"** (7 of 10,
> separately, were interested specifically in the education aspect).

> **How the Incubator is treating these hand-edits:** with the same
> scrutiny as any other input — not accepted uncritically because the
> user supplied them directly rather than through a research vendor.
> Three of the seven items above are genuine gap closures (monetization
> decision, company-side Constraints characterization, and the
> now-explicit framing of two previously-implicit assumptions as
> conscious risk acceptances); the remaining four are new evidence or
> new policy statements that inform existing sections without closing
> their central open questions. Each is scrutinized individually below,
> section by section.

> **Correction carried into this revision:** `BusinessCase_v7.md`'s
> Readiness Score arithmetic stated "3 critical sections" in its
> points-possible calculation (105 + 30 = 135), but only **two** sections
> in its own table carry the ★ critical marker (Legal & Compliance;
> Child Data & Consent). This is a carried-forward inconsistency, not a
> deliberate design choice — the Incubator cannot find a third ★-marked
> section anywhere in v7's table. This revision corrects the
> points-possible denominator to reflect the table as actually
> constructed: 22 non-critical sections × 5 = 110, plus 2 critical
> sections × 5 × 2 = 20, total possible = **130**. This is flagged
> explicitly, not silently changed — see Readiness Score below for the
> full recomputation and a side-by-side against the legacy (inconsistent)
> denominator for transparency.

## What Changed in v8 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

This revision incorporates the user's direct hand-edits to
`BusinessCase_v7.md` plus `Clarifications_v8.md`. Net effect on section
tags:

- **Constraints** moves from Partial to **Complete** — for the first
  time across eight versions, company-side budget approach, team size,
  and a directional timeline have been supplied by the user, even though
  deliberately non-numeric and non-granular.
- **Business Model / Success Criteria** retain their **Partial** status,
  but the specific ambiguity previously flagged as v7's "Critical Gap
  #6" (which conversion benchmark applies — ads-hybrid 2-4% or
  subscription-only 1-3%) is now **resolved**: subscription-only at
  launch, ads deferred to a possible V2. This is treated as a genuine
  decision-based gap closure, not merely new evidence, since Research
  House had already confirmed in v7 that no further research — paid or
  unpaid — could resolve this question; only a user decision could, and
  now one has been made. Business Model remains Partial because two
  other open items persist: the actual subscription price point, and
  whether the Mpoints cosmetic-currency system triggers Apple's
  in-game-currency IAP-routing rule.
- **Problem / Supporting Evidence** gain the case's first-ever direct,
  primary MiniMoney-specific research data point (n=10 family
  interviews). This is characterized with deliberate rigor below: it is
  directionally real, first-party evidence — categorically different in
  kind from both the Incubator's general-knowledge content and Research
  House's vendor-sourced market comparables — but n=10 is not
  statistically significant, and the sampling method, recruitment
  channel, family selection criteria, and exact question wording are all
  unknown. Both sections remain Partial.
- **Objectives** gains a real, user-committed 90-day download target
  (15,000), which is reconciled below against the existing Year-1 funnel
  range (18,000-61,000) — a reconciliation that surfaces a mild internal
  tension rather than a clean confirmation. Objectives remains Partial.
- **Legal & Compliance / Child Data & Consent** remain Partial and
  Critical, but this revision adds explicit, plain documentation of two
  conscious user decisions: (a) the specialist POPIA/ARB legal opinion is
  **deliberately deferred** to post-Investment-Committee, build-spec
  stage — a stated policy choice, not an oversight; (b) two specific
  compliance sub-questions (POPIA retention sufficiency; exam-bonus
  mechanic's schools-data-privacy status) are now **explicit
  risk-accepted assumptions**, standing until challenged, per the user's
  own stated policy. These are documented plainly as user risk
  acceptances for the Investment Committee to weigh directly — not
  folded in as resolved facts, and not hidden as unaddressed gaps.
- **Opportunity / Risks (competitive-risk framing):** the schools
  distribution-model observation is corrected — a schools partnership is
  now an intended, parallel channel to direct-to-parent distribution, not
  a model MiniMoney has ruled out, as v7's Risks section had
  characterized it.

No section moves to Incomplete. No section moves from Critical to
Incomplete. The Readiness Score change is discussed in full below.

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
holds, transmits, or takes custody of funds**. The monetization
direction is now resolved: **subscription-only at launch**, with
advertising explicitly deferred to a possible post-launch V2 feature
intended, if pursued, to reduce subscription cost to parents rather than
serve as a launch-day revenue line. Real-money in-app purchases remain
parent-only; a minor cannot access any part of the app, including
education content, without a pre-existing, consenting parent account.
Operations remain comprehensively described, including the
escalating late-penalty mechanism (5→6→7 Mbucks/week, pilot cap 3) and
the "Fintech Advance" course exclusive to the 15-18 band.

Two new inputs materially change this revision's character relative to
v7. First, the user reports the case's first direct primary-research
data point: interviews with 10 families, of whom 6 confirmed interest in
using the app and stated willingness to pay for it, and 7 expressed
interest specifically in the education component. This is genuine,
first-party evidence — a meaningful step up in kind from every
comparable-market inference used elsewhere in this case — but n=10 is
not statistically significant, and the sampling method, recruitment
channel, and question wording are undocumented; it should be read as a
directional, encouraging signal, not validated demand. Second, the
previously-flagged "must simply decide" monetization gap is closed:
subscription-only at launch is now the stated model, ads deferred to a
possible V2. Company-side Constraints are, for the first time across
eight versions, characterized (solopreneur venture, AI-assisted build,
external technical help on-demand, ~3-month directional build timeline)
though deliberately without a Rand budget figure or dated milestone
schedule. The specialist POPIA/ARB legal opinion remains unobtained by
explicit, deliberate user decision — deferred to the build-spec stage,
after Investment Committee review — a conscious risk-acceptance choice
the Investment Committee should evaluate directly as a go/no-go input,
not treat as a resolved matter. Two specific compliance sub-questions
(POPIA retention sufficiency; exam-bonus mechanic's schools-data-privacy
status) are likewise now explicit, standing user risk acceptances rather
than open Incubator-flagged gaps. A new 90-day download target (15,000)
is reconciled against the existing Year-1 funnel range below and
surfaces a mild tension worth the Investment Committee's attention
rather than a clean milestone confirmation.

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

**New this revision — the case's first direct primary-research data
point:** the user reports interviews completed with 10 families: 6 of
10 confirmed interest in using the app **and stated willingness to pay**
for it; 7 of 10 expressed interest specifically in the education
aspect. This is treated with deliberate rigor rather than either
dismissal or over-crediting: it is genuine, first-party, MiniMoney-
specific evidence — a categorically different (and stronger-in-kind)
data point than any comparable-market inference used elsewhere in this
case — but n=10 is far below any threshold of statistical significance,
and the recruitment method, family selection criteria, sampling frame,
and exact question wording are all unknown. A 6/10 "would pay" result
from an unknown, possibly convenience-sampled group of 10 families
(potentially friends, family, or a warm network) carries meaningfully
different weight than the same result from a randomly-sampled cohort of
unaffiliated parents — and the case study does not specify which this
is. The Incubator's judgment: this is a real, encouraging, directional
signal that the Problem is at least perceived as real by some parents,
and it is the first time in eight versions this case has any direct
evidence of parent perception at all — but it does not, by itself,
establish that parents broadly perceive this as a problem worth paying
to solve. Status remains Partial for this reason.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic (budget → tasks →
Mbucks → invoice → real bank payment → payslip, plus a parallel Mpoints
cosmetic-reward loop) rather than a simple debit-card-for-kids model.
MiniMoney's opportunity is more accurately framed as an **edtech app
with a payroll-simulation UX**, competing on curriculum quality and
mechanic engagement rather than banking features. No direct South
African incumbent does what MiniMoney does; the three named local
players each miss at least one defining dimension (see Market &
Competition).

`ResearchFindings_v1.md` Item 5 (carried from v7) adds a directional
data point: MoneyAfrica Kids (the closest edtech comparable) shows
modest download volumes (10,000+ Google Play, 3,000+ Apple, pan-African
not SA-specific), while MoneyTime SA claims a much larger, self-published
B2B2C-mediated reach (130,000 students via schools) — together
suggesting real but unproven consumer appetite, with the strongest
demonstrated reach coming via a schools-distribution model.

**Distribution model, clarified this revision:** MiniMoney plans to
launch privately, direct-to-parent, and **also** intends to partner with
schools as a channel to teach financial literacy in a real-world
setting. This is a parallel, intended channel — not a model the venture
has ruled out. This directly updates the framing in Risks below, where
v7 had incorrectly characterized MiniMoney's distribution choice as
excluding the schools-mediated model that produces the strongest local
demand signal available.

## Objectives

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The case study states a functional objective: build an app that (1)
requires a parent to submit a budget before task assignment, (2)
assigns tasks (predefined or custom, recurring or one-off), (3) converts
completion into Mbuck earnings and a flat 10-Mpoint cosmetic reward, (4)
applies an exam-performance bonus mechanic, (5) generates a parent
invoice and child payslip inclusive of arrears, (6) prompts/confirms a
real bank payment with the escalating late-penalty mechanism (5→6→7
Mbucks/week, pilot cap 3), and (7) delivers age-appropriate financial
education — fully gated behind a consenting parent account.

1. **Pre-launch:** validate the core budget→task→Mbuck/Mpoint→
   payslip→payment loop with a small pilot cohort of South African
   families (candidate: 20-50 families) on Android. The n=10 interview
   round (see Problem) is a first, informal step in this direction but
   is not itself this pilot.

2. **Launch (first 90 days):** the funnel model gives a reference range
   of 18,000-61,000 free installs and 360-2,440 paying subscribers in
   Year 1. **New this revision — a user-committed 90-day target: 15,000
   downloads within the first 90 days.** The Incubator reconciles this
   against the annual range rather than treating the two figures as
   unrelated, per standing instruction:

   - Against the **low end** of the annual range (18,000), 15,000 in the
     first 90 days represents **83%** of the entire year's low-end
     target consumed in the first 25% of the year — implying either a
     sharply front-loaded adoption curve (plausible if a launch
     marketing push or app-store feature is planned but not currently
     stated anywhere in this case) or a material risk that, absent such
     a push, the remaining 9 months would need to contribute only
     ~3,000 further installs to still hit the low end.
   - Against the **high end** of the annual range (61,000), 15,000 in 90
     days is roughly proportional to elapsed time (90/365 ≈ 24.7% of the
     year, 15,000/61,000 ≈ 24.6% of the total) — a materially more
     plausible, linear pace.
   - **Net assessment:** the 90-day target is only internally consistent
     with the annual funnel model if the business is implicitly
     targeting the upper half of its own modeled range, or if a
     front-loaded launch-marketing assumption is intended but has not
     been stated. This is flagged as a reconciliation note, not a
     contradiction requiring rejection — but it should not be read as a
     clean, low-effort milestone inside an already-conservative range.

3. **Growth (6-12 months):** validate the Freemium/subscription
   conversion assumption — now correctly benchmarked against the 1-3%
   subscription-only range specifically (see Success Criteria, resolved
   this revision); validate curriculum engagement as a leading indicator
   of retention; evaluate iOS port timing based on Android traction.

These remain candidate objectives beyond the newly-confirmed 90-day
download figure: the funnel model supplies a real range, but growth-phase
targets are not yet user-prioritized.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

- **Pilot success:** a defined percentage (candidate: majority) of pilot
  families complete at least 4 consecutive weekly task→payslip cycles
  without abandoning the app; the late-penalty mechanic (5→6→7
  Mbucks/week, pilot cap 3) is exercised and tracked, with running
  arrears visible as a line item.

- **Curriculum engagement:** the user's hand-edited figure of 30% of
  child users complete daily/weekly micro-course content within the
  first month. No external benchmark is cited for this figure.

- **Operational health:** the user's hand-edited figure of 65% of tasks
  are marked complete without triggering a parent dispute. No external
  benchmark supports this specific number.

- **Freemium/subscription conversion — ambiguity resolved this
  revision:** the user's hand-edited figure of 2% should now be assessed
  against the **1-3% subscription-only** reference range specifically,
  not the 2-4% ads-hybrid range, since the monetization decision
  (subscription-only at launch, ads deferred to V2) resolves the
  previously-flagged ambiguity. The 2% figure sits comfortably within
  the middle of the correct 1-3% range — this is now a coherent,
  correctly-benchmarked target, though still unvalidated against any
  MiniMoney-specific data.

- **Retention:** a defined 90-day retention benchmark for the parent
  account (candidate framing only — no figure proposed).

Status remains Partial: the conversion-benchmark ambiguity is genuinely
resolved, but two of five criteria (curriculum engagement, operational
health) still lack any external benchmark, and no retention figure has
been proposed at all.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v7: children/teens (6-18, sub-banded), parents/guardians,
the app operator, the South African Information Regulator (POPIA) and
the Advertising Regulatory Board (ARB), three named competitors
(African Bank MyWORLD Power Pocket, MoneyAfrica Kids, MoneyTime SA), and
Apple/Google as app-store platform stakeholders (Kids Category, Families
Policy). Still not addressed: the parent's bank as an external rail. A
future AI mediator for dispute resolution remains explicitly out of
scope. No new stakeholder is introduced by this revision's clarifications
(the schools-partnership clarification refines the *distribution*
relationship with schools, already named, rather than introducing a new
stakeholder category).

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v7: children/teens 6-18 (sub-banded) and their parents
(the paying/administrating customer and bank-account holder), South
Africa, Android-first. The customer relationship is unambiguous: the
parent account is primary and must exist, with consent given, before a
minor can access anything. Real-money in-app purchase is confirmed
parent-only, and the monetization model resolved this revision
(subscription-only) does not change the target-user definition itself.

## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household tasks into a
structured payroll-like experience, removing manual tracking and adding
a built-in financial literacy curriculum. For children: a "real job"
simulation — payslips, overtime, deductions, exam bonuses — paid out via
the parent's own bank transfer, tied to age-appropriate lessons,
alongside a separate cosmetic-reward system (Mpoints).

| Feature | Free | Subscription |
| - | - | - |
| Setting up a budget | X | X |
| Adding minor | X | X |
| Adding 3+ minors |  | X |
| Access to education | X | X |
| Additional content (expert videos, interactive content) |  | X |
| Enrolling a 15-18 minor for "Fintech Advance" |  | X — and requires separate explicit parent opt-in |

**Monetization model resolved this revision:** subscription-only at
launch (previously labeled "Freemium," which described the free/paid
tier split but left open whether the free tier would carry
advertising). Ads are explicitly deferred to a possible V2, intended, if
pursued, to reduce subscription cost rather than serve as a launch
revenue line. MoneyTime SA's R995/year (25% sibling discount) remains
the case's one real South African price anchor, with the caveat
(preserved from v7) that MoneyTime SA is a lighter-weight product and
likely under-anchors what MiniMoney could or should charge. MiniMoney's
own subscription price point is still not specified.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v7: population base, device access, OS split, and parent
financial-app engagement figures (Stats SA, Stellenbosch study,
Statcounter, SARB Payments Study) yield a reachable-market funnel of
≈6.1M kids in "reachable" households and a Year-1 range of 18,000-61,000
free installs, 360-2,440 paying subscribers. `ResearchFindings_v1.md`'s
10 items (see v7 for full detail) remain incorporated: MoneyTime SA
pricing (R995/year), app-store child-category policy specifics, a
confirmed absence of any SA-specific adoption/conversion benchmark, and
directional download-volume signals for comparables. No new market data
was supplied this revision; the schools-partnership clarification (see
Opportunity) is a distribution-strategy update, not new market evidence.
Status remains Partial: the most decision-relevant figures (Year-1
adoption, conversion rate) remain [Guessing]-tagged extrapolations.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Confirmed structurally: MiniMoney is a facilitation/education layer that
sits on top of the parent's own bank account and does not move or hold
funds, removing the need for a money-transmitter license as a primary
constraint (subject to specialist confirmation — see Legal &
Compliance).

**Monetization decision — resolved this revision:** subscription-only at
launch. Advertising is explicitly deferred to a possible post-launch V2
feature, to be investigated as a way to reduce subscription cost to
parents, not adopted now. This is treated as a genuine gap closure, not
merely new evidence: `ResearchFindings_v1.md` Item 4 had already
confirmed in v7 that this question — ads-hybrid vs. subscription-only —
could not be resolved by any further research, paid or unpaid; it was a
pure internal decision dependency. A decision has now been made. This
resolves what v7 called its cleanest "the user must simply decide"
Critical Gap.

**Why Business Model remains Partial despite this closure:** two
distinct open items persist. First, no specific subscription price point
has been supplied — MoneyTime SA's R995/year remains the only local
anchor, and is flagged as likely under-anchoring MiniMoney's more
feature-rich product. Second, whether the Mpoints cosmetic-currency
system triggers Apple's Kids Category in-game-currency IAP-routing rule
remains unresolved (Medium confidence, per Research House's own
labeling in v7 Item 6) — Google's side of this question (Families
Policy loyalty-point disclosure) is resolved and actionable, Apple's is
not. Because both of these are core to "how the business actually
makes and reports money," the section does not yet meet the Complete
bar.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v7 in substance: engineering-cost range (~$25,000-$40,000
MVP; ~$60,000-$120,000+ full build, Medium confidence, five converging
agency sources); legal-opinion cost scoping (R25,000-R80,000, explicitly
Research House's own inference, not a quote, five named firms
shortlisted); CAC unresolved; curriculum-production cost unresolved. The
monetization resolution (subscription-only) removes ad-revenue
uncertainty as a *modeling* variable for Year-1 (there is no ad revenue
line to model at launch), but does not supply an absolute price point,
so revenue still cannot be modeled in Rand or USD terms. Constraints'
new company-side characterization (solopreneur, AI-assisted build) is a
qualitative input, not a numeric budget — it does not change this
section's Status.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Unchanged from v7 — already Complete. Budget/earning mechanics, task
structure, the exam-performance bonus mechanic, the completion/
verification/reporting flow, the dispute mechanism, and the
payment-confirmation/late-penalty mechanism (5→6→7 Mbucks/week, pilot
cap 3) remain fully described. The real-money-denominated late-penalty
system, enforced entirely on mutual honor-system reporting with no
technical payment verification, remains a novel operational and
possibly trust/relationship risk (see Risks) — the mechanism is fully
described and internally consistent; its soundness as a design choice
is a separate, open question.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v7: mobile app, Android primary, iOS future work;
budget-setting flow, task-assignment engine, dual-currency ledger,
exam-bonus calculator, notification system, weekly report generation,
camera-app invocation for photo-proof, dispute workflow,
payment-accept/dispute workflow, arrears/late-penalty calculator,
document generation, feature-entitlement/paywall system with a distinct
Fintech Advance dual-gate. App-store child-category policy specifics
(Google Families Policy loyalty-point disclosure; Apple Kids Category
age-band/parental-gate/advertising-review requirements, and the
unresolved question of whether Apple's Kids Category age bands, which
top out at 9-11, are compatible with MiniMoney's 6-18 span for an
eventual iOS port) remain as sourced in v7 — this revision's user
clarifications did not add new technical detail. What remains
unspecified: exactly how "linking" a child account to a parent account
is technically initiated; how payment confirmation is captured beyond
the accept/dispute UI; technical specifics of the exam-bonus grade-input
mechanism.

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**This section remains flagged Critical.** Resolved from prior versions:
MiniMoney does not hold, move, or take custody of funds. Initial launch
jurisdiction is South Africa, governed by POPIA. A minor cannot access
any part of the app without a pre-existing, consenting parent account.
POPIA Section 34, ARB Clause 14, POPIA Section 14 (retention), and the
absence of any ARB/NCR precedent addressing "payslip"/"invoice"/"late
penalty" terminology applied to minors all remain as sourced in v7.

**New this revision — a deliberate, stated policy on legal-opinion
timing, documented plainly:** the user has explicitly decided that the
specialist POPIA/ARB legal opinion will be commissioned once build-spec
work begins — i.e., **after** Investment Committee review, entering the
Developing Committee stage — not before. In the user's own words, the
current stage's purpose is to answer "if it should be built (the app as
a whole, not specific features)," not to pre-resolve every legal
question first. The Incubator documents this as a **conscious
risk-acceptance choice**, made openly during this test period's manual
gate-check process — not as an unresolved oversight, and not as a
resolved fact. The underlying legal uncertainty (money-transmitter
characterization of the invoice/payment-trigger mechanic;
terminology-to-minors risk; POPIA sufficiency) is entirely unchanged by
this decision — only the timing of when it gets formally addressed, and
who bears the interim risk, has been clarified. The Investment Committee
should evaluate this deferral explicitly as a go/no-go input in its own
right, not treat the underlying Legal & Compliance uncertainty as
resolved because a plan now exists to eventually resolve it.

**New this revision — two explicit, user-stated risk-accepted
assumptions** (per the user's own stated policy: "some of the sections
cannot be evidenced as nothing exists like this currently within South
Africa so the assumptions made by the user in this instance will be
considered acceptable until proven otherwise"):

1. POPIA's general data-retention principle (Section 14) is assumed
   sufficient for MiniMoney's data model without child-specific
   supplementary rules, absent any South African precedent either way.
2. The exam-performance bonus mechanic is assumed to carry no
   schools-data-privacy dimension, because grade data is purely
   self-reported/parent-entered, with no school-system data-sharing
   integration.

These are documented here as **explicit user risk acceptances**, standing
until challenged — not as Incubator inferences, and not as settled legal
conclusions. They remain unverified by any external authority.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Risks largely unchanged from v7, with two corrections this revision:

- **Regulatory risk (Critical, substantially narrowed but not
  resolved):** unchanged in substance. **Reframed this revision:** the
  still-missing specialist legal opinion is now understood as a
  deliberate, timed deferral (post-Investment-Committee, build-spec
  stage) rather than an open-ended gap — this changes *how* the
  Investment Committee should read the gap (a scheduled, owned decision
  vs. an unaddressed unknown) but does not reduce the underlying
  regulatory uncertainty itself.
- **Child-safety/data-privacy risk (Critical, substantially reduced,
  now partly risk-accepted):** the POPIA Section 14 retention question
  and the exam-bonus schools-data-privacy question are now explicit
  user risk acceptances (see Legal & Compliance) rather than open
  questions — the risk itself is unchanged, but its disposition (accepted
  vs. pending) is now explicit.
- **Trust/enforcement risk (unresolved):** unchanged.
- **Late-penalty/relationship risk (unresolved):** unchanged.
- **Dispute-escalation risk (unresolved):** unchanged.
- **Terminology/perception risk (confirmed, not hypothesized):**
  unchanged from v7.
- **Advertising/child-data risk:** now **reduced in near-term
  relevance** — since ads are explicitly deferred to a possible V2, the
  POPIA Section 34/ARB Clause 14 ad-targeting compliance burden is not
  an immediate launch-blocking concern, though it remains relevant if V2
  is pursued.
- **Fintech Advance content risk (narrowed but not eliminated):**
  unchanged.
- **Competitive risk — corrected this revision:** v7 characterized
  MiniMoney's distribution model as direct-to-parent only, framing the
  strongest local demand signal (MoneyTime SA's schools-mediated reach)
  as belonging to "a distribution model MiniMoney does not currently
  plan to use." This is now known to be inaccurate: a schools
  partnership is an intended, parallel channel (see Opportunity). The
  competitive-risk framing is corrected accordingly — this is a more
  neutral, arguably favorable, framing than v7's, though the schools
  partnership itself remains unexecuted and unvalidated.
- **Monetization-execution risk — resolved this revision:** the
  ads-vs-subscription decision is made (subscription-only); remaining
  execution risk is limited to price-point selection and conversion-rate
  validation, not model selection itself.
- **App-store policy risk (substantiated, not resolved):** unchanged
  from v7 — Apple's Kids Category age-band ceiling (9-11) vs.
  MiniMoney's 6-18 span remains an open structural question for any
  future iOS port.
- **Platform-concentration risk (narrowed, evidence-backed):**
  unchanged.
- **Adoption/forecasting risk:** unchanged in substance, but now joined
  by a related, more specific risk: the 90-day download target (15,000)
  is only cleanly consistent with the *upper half* of the annual funnel
  range (see Objectives) — if the business is implicitly relying on a
  front-loaded launch spike to hit 15,000 in 90 days, that assumption is
  not stated anywhere and should be made explicit before it is used for
  planning.
- **Engineering-cost estimation risk:** unchanged from v7.
- **New — legal-opinion-deferral risk:** deferring the specialist
  opinion to the build-spec stage means the Investment Committee is
  being asked to evaluate a Critical-tagged Legal & Compliance section
  that will not itself be closed before its own review. This is not
  inherently unreasonable (building foundational, non-legally-sensitive
  rails before commissioning a scoped legal review is a legitimate
  sequencing choice) but it is a risk the Investment Committee should
  weigh explicitly, not discover implicitly.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Assumptions carried forward unchanged from v7 (parent-direct payment, SA
launch jurisdiction, universal consent gate, Android-first, Mbucks/
Mpoints dual currency, 7-Mbuck cap with 3-Mbuck pilot cap, Fintech
Advance scoping) — see v7 for full detail.

**New this revision — two assumptions reclassified as explicit,
user-stated risk acceptances** (not Incubator inferences, per the user's
own stated policy in `Clarifications_v8.md`):

1. POPIA's general Section 14 retention principle is assumed sufficient
   for MiniMoney's data model without child-specific supplementary
   rules, absent any South African precedent either way — **standing
   until proven otherwise**, by explicit user decision.
2. The exam-performance bonus mechanic is assumed to carry no
   schools-data-privacy dimension (grade data is self-reported/
   parent-entered only, no school-system integration) — **standing
   until proven otherwise**, by explicit user decision.

**New this revision — monetization is no longer an open assumption:**
subscription-only at launch is now a stated decision, not an assumption
to be validated.

**Still assumed, unchanged:** the exact Mbucks-to-Rand peg is fixed
platform-wide; the app is intended primarily as a South African B2C
product at launch; the late-penalty mechanic is intended as a
behavioral nudge rather than a genuine financial detriment to be
strictly collected.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

**Resolved this revision, for the first time across eight versions:**
the user has supplied company-side budget, timeline, and team-size
information. MiniMoney is a **solopreneur venture**, using **AI-assisted
("vibe coding") development** to build the foundational rails, with
explicit plans to onboard external technical expertise if and when the
need arises. The build timeline target is **as early as 3 months from
the date final documents are drafted and app building begins** — the
user explicitly states this is intentionally not more granular, since
the current focus is building the foundational structure rather than
committing to a feature-level schedule.

**Why this is scored Complete despite being directional rather than
numeric:** the section's central open question across every prior
version was "what company-side budget, timeline, and team size are
available?" — a question the user had never answered in any form. It is
now answered, in the terms the user has chosen to answer it in
(qualitative budget approach and team size, directional timeline). The
Incubator judges this sufficient to close the section's core open
question, while flagging clearly — see Devil's Advocate — that "Complete"
here means "the user's own stated constraints have been captured
faithfully," not "a fully numeric, dated budget/milestone plan exists."
Platform choice (Android primary, iOS future) remains confirmed and
substantiated by Statcounter data, as in prior versions.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in overall structure from v7's candidate MVP sequence (legal
validation → free-tier core build → pilot → paywalled-feature layer →
iOS evaluation), refined this revision by two clarifications: (1) legal
validation is now explicitly sequenced **after** Investment Committee
review, at the build-spec stage — not a step to be completed before
this case proceeds, by deliberate user decision (see Legal &
Compliance); (2) the build itself is characterized as solopreneur,
AI-assisted, with a directional ~3-month timeline from build-start (see
Constraints). Status remains Partial: a real sequencing logic and a
directional timeline now exist, but no dated milestone plan, phased
budget, or specific resourcing schedule has been supplied.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

No funding ask, runway, or numeric financial projections are present in
any input document. Constraints' new qualitative characterization
(solopreneur, AI-assisted build, external help on-demand) informs the
cost side directionally but supplies no Rand or USD budget figure. The
monetization resolution (subscription-only) removes ad-revenue as a
Year-1 modeling variable but does not supply a price point, so absolute
revenue still cannot be modeled. Engineering-cost and legal-opinion-cost
ranges (see Revenue & Costs, carried from v7) remain the only numeric
cost inputs available, both externally sourced rather than
company-specific.

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Recommended validation priorities, refined this revision:

1. **Legal validation — deliberately deferred, not merely
   deprioritized:** the specialist POPIA/ARB legal opinion is, by
   explicit user decision, scheduled for the build-spec stage,
   post-Investment-Committee — not a validation step the Investment
   Committee should expect to see completed before its own review.

2. **Primary user-research validation — newly relevant:** the n=10
   family-interview round is a useful first informal step, but its
   sample size, sampling method, and question wording fall well short of
   a validated pilot. The Incubator recommends the next step be either
   (a) a formally structured, larger-sample survey with documented
   recruitment methodology, or (b) proceeding directly to the
   already-planned 20-50 family pilot — either of which would supply
   materially stronger evidence than treating the n=10 result as
   sufficient on its own.

3. **Trust/enforcement and late-penalty validation:** unchanged from v7.

4. **Dispute-mechanism validation:** unchanged from v7.

5. **Market/demand validation:** unchanged from v7 — a confirmed data
   ceiling exists (commissioned survey, R80,000-R250,000, 3-6 weeks, or a
   live pilot).

6. **Pricing/conversion validation:** unchanged from v7, now correctly
   scoped against the 1-3% subscription-only benchmark specifically
   (monetization decision resolved).

7. **Curriculum validation:** unchanged from v7.

8. **90-day target reconciliation:** newly recommended — before treating
   the 15,000-download 90-day target as a planning input, the business
   should make explicit whether it is relying on a front-loaded
   launch-marketing assumption (see Objectives) or should instead revise
   the target to be consistent with a linear pace against the annual
   funnel's low end.

This section remains Partial: several steps are now more specifically
scoped, but no validation activity beyond the informal n=10 interview
round has actually occurred.

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**New this revision — the case's first direct, primary MiniMoney-specific
evidence:**

- [Supported/Low-Medium] First-party pilot-interview data: n=10 South
  African families; 6 of 10 confirmed interest in using the app and
  stated willingness to pay for it; 7 of 10 expressed interest
  specifically in the education component. Sampling method, recruitment
  channel, family-selection criteria, and exact question wording are
  undocumented. This is directionally real, first-party evidence — a
  categorically stronger kind of evidence than the comparable-market
  inference used elsewhere in this case — but it is not statistically
  powered and should not be treated as validated demand. It is the
  first data point in eight versions to speak directly to whether real
  parents, not comparable markets, perceive value in MiniMoney
  specifically.

Carried forward unchanged from v7: `ResearchFindings_v1.md`'s 10-item
vendor engagement (pricing, cost, and policy anchors — see v7 for full
detail); the user's own directly-cited South African statutory/
statistical sources (`Clarifications_v6.md`). Status remains Partial:
even with the new interview data point, no prototype, no legal opinion,
and no statistically-powered demand validation exists.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this revision:**

- ~~What company-side budget, timeline, and team size are available for
  the actual build?~~ **Resolved** (directionally): solopreneur venture,
  AI-assisted build, external expertise on-demand, ~3-month timeline
  from build-start (see Constraints). Open across all seven prior
  versions; now answered in the terms the user chose to answer it.

- ~~Does the ads-hybrid vs. subscription-only monetization question
  require further research?~~ **Resolved by decision, not research:**
  subscription-only at launch; ads deferred to a possible V2.

- ~~Is MiniMoney's distribution strategy direct-to-parent only, or does
  it include a schools channel?~~ **Resolved:** both — direct-to-parent
  is the primary launch channel, with a schools partnership as an
  intended parallel channel.

**Newly introduced by this revision:**

- What is the actual South African Rand subscription price point? (Only
  MoneyTime SA's R995/year exists as a — likely under-anchoring —
  reference.)
- Does the user intend the n=10 interview round to be scaled into a
  larger, methodologically documented survey before it is used in any
  further financial or go/no-go modeling, or is a live 20-50-family pilot
  the intended next validation step instead?
- What forcing mechanism or deadline governs the now-deferred specialist
  legal opinion, to ensure it is actually commissioned at the build-spec
  stage rather than slipping indefinitely, as the ads-vs-subscription
  decision itself lingered across two prior versions before being
  resolved?
- Is the 15,000-download 90-day target premised on a front-loaded
  launch-marketing push, and if so, what is that push (paid acquisition,
  app-store feature, PR)? If no such push is planned, should the target
  be revised to track more consistently with the annual funnel model's
  low end?
- Does the schools-partnership channel (Opportunity, Risks) have any
  timeline, target school count, or resourcing plan, or does it remain a
  stated intention only at this stage?

**Still open, carried forward unchanged from v7** (see `BusinessCase_v7.md`
for the full prior itemized list, items covering: fund custody,
consent-gate model, task verification, dispute-escalation beyond 48
hours, payment-routing timeline, late-penalty cap rationale, Fintech
Advance scope, arrears disposition, exam-bonus data source, Mbucks-peg
flexibility, curriculum age-band splits, whether a specialist legal
opinion will in fact be commissioned as planned, app-store policy
sub-questions, MoneyAfrica Kids' unpublished premium price, and whether
informal engineering-cost quotes will be sought).

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
| Constraints | **Complete** | 1x | **5** |
| Roadmap | Partial | 1x | 2 |
| Financial Considerations | Partial | 1x | 2 |
| Validation Strategy | Partial | 1x | 2 |
| Supporting Evidence | Partial | 1x | 2 |
| Outstanding Questions | Complete | 1x | 5 |
| Curriculum Design (extension) | Partial | 1x | 2 |
| Child Data & Consent (extension) ★ | Partial | 2x | 4 |

Points earned:
2+2+2+2+2+2+2+2+2+2+2+5+2+4+2+2+**5**+2+2+2+2+5+2+4 = **61**

**Points possible — corrected this revision:** the table contains 24
sections, of which exactly **2** carry the ★ critical marker (Legal &
Compliance; Child Data & Consent). Points possible = 22 non-critical
sections × 5 = 110, plus 2 critical sections × 5 × 2 = 20. **Total
possible = 130** (corrected from v7's inconsistent stated total of 135,
which had assumed a third, unmarked critical section — see the
correction note at the top of this document).

**Readiness Score = 61 / 130 = 46.9%, rounded to 47%.**

For direct comparability with v7's own (inconsistent) denominator: under
the legacy 135-point total, this revision's 61 earned points would read
as 61/135 = 45.2%. Either way, the movement from v7 (40%) is **+6 to +7
percentage points**, driven almost entirely by Constraints' move to
Complete (+3 points net of weighting effects) plus the corrected
denominator itself contributing a smaller additional lift. This is a
real, if modest, improvement — not a research-driven one, but a
decision-and-disclosure-driven one: the user made a monetization
decision, supplied constraint information for the first time, and
converted two implicit assumptions and one deferred legal step into
explicit, documented positions. None of this closes the case's Critical
Legal & Compliance gap, which remains Partial by deliberate user choice.

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB legal opinion remains unobtained, now by
   **explicit, deliberate user decision** to defer it to the build-spec
   stage (post-Investment-Committee) — a conscious risk-acceptance
   choice the Investment Committee should evaluate directly, not treat
   as resolved. Two specific compliance sub-questions (POPIA retention
   sufficiency; exam-bonus mechanic's schools-data-privacy status) are
   now explicit, standing user risk acceptances rather than open
   questions — the underlying legal uncertainty is unchanged.

2. **Supporting Evidence (Partial)** — now includes the case's first
   direct, primary MiniMoney-specific data point (n=10 family
   interviews, 6/10 would-pay, 7/10 education-interested) — a real but
   statistically thin addition; no prototype, legal opinion, or
   at-scale validated demand signal yet exists.

3. **Objectives / Success Criteria / Validation Strategy (Partial)** —
   the ads-vs-subscription ambiguity is resolved (subscription-only),
   and a real 90-day download target (15,000) now exists, but this
   target is only cleanly consistent with the upper half of the annual
   funnel range, and no rationale for a front-loaded adoption curve has
   been stated; curriculum-engagement and operational-health benchmarks
   remain unbenchmarked.

4. **Constraints — resolved this revision, flagged here for
   transparency rather than as a remaining gap:** company-side budget
   approach, team size, and a directional timeline are now characterized
   for the first time across eight versions. This is a genuine
   improvement, though deliberately directional rather than numeric — no
   Rand budget figure or dated milestone schedule exists.

5. **Late-penalty and dispute-escalation mechanics (Operations Complete,
   Risks Partial, unchanged)** — internally consistent at 5→6→7
   Mbucks/week (pilot cap 3); the underlying, still-untested trust/
   fairness risk is unaffected by this revision.

6. ~~Monetization-model decision (Business Model/Success Criteria)~~ —
   **Resolved this revision:** subscription-only at launch, ads deferred
   to a possible V2. Retained here, struck through, for continuity with
   prior versions' Critical Gap numbering.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs.*

Unchanged from v7: the age floor of 6 introduces financial literacy
early via short daily/weekly-completable content; "Fintech Advance" is a
distinct, fully-scoped 15-18-only conceptual course, described by the
user as a "non-negotiable requirement" for that age band, gated by
separate parent opt-in. The n=10 interview finding that 7 of 10 families
were interested specifically in the education aspect is a modest,
directional positive signal for this section, but does not resolve any
of its still-unspecified items: age-band curriculum splits,
instructional format, standards alignment, and content authorship,
including for Fintech Advance specifically.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Appended because MiniMoney targets users as young as age 6, triggering
child-directed-app compliance obligations beyond general Legal &
Compliance.*

**Model:** unchanged — every minor requires a pre-existing, consenting
parent account before any access.

**New this revision — two explicit user risk-accepted assumptions,
documented here plainly per `Clarifications_v8.md`'s specific
instruction:**

1. **POPIA Section 14 retention sufficiency:** the user explicitly
   assumes POPIA's general retention principle (records not retained
   longer than necessary; destruction must be unreconstructable) is
   sufficient for MiniMoney's data model **without** child-specific
   supplementary rules (unlike COPPA or GDPR-K), absent any South
   African precedent either way. This is documented as a **conscious
   user risk acceptance**, standing until challenged — not an Incubator
   inference, and not a settled legal conclusion. No South African
   authority has confirmed this either way.

2. **Exam-bonus mechanic — no schools-data-privacy dimension:** the user
   explicitly assumes the exam-performance bonus mechanic carries no
   schools-data-privacy dimension, because grade data is purely
   self-reported/parent-entered (the child's own end result per
   subject), with no school-system data-sharing integration. This is
   likewise documented as a **conscious user risk acceptance**, standing
   until challenged.

Carried forward from v7, unchanged: Google Play's Families Policy
loyalty-point disclosure requirement (directly applicable to Mpoints);
Apple's Kids Category age-band/parental-gate/advertising-review
requirements and the unresolved question of whether its IAP-currency
rule extends to non-cash-out cosmetic points; the confirmed absence of
any ARB/NCR precedent addressing "payslip"/"invoice"/"late penalty"
terminology applied to minors; a firm shortlist and rough cost range
(R25,000-R80,000) for the still-unobtained legal opinion.

**Unresolved, specifically:** a specialist POPIA/ARB legal opinion has
still not been obtained — by explicit, deliberate deferral to the
build-spec stage, not oversight (see Legal & Compliance); whether the
Mpoints store's Apple IAP-currency question requires a direct App Review
test or legal confirmation; whether "payslip"/"invoice"/"late
penalty"/"arrears" terminology carries regulatory implication (confirmed
as unprecedented, not resolved); whether Apple's Kids Category age-band
structure (topping out at 9-11) is compatible with MiniMoney's full 6-18
span for an eventual iOS port.

This should still be confirmed via a South African data-protection and
advertising-law legal opinion — the user's decision to obtain this at
the build-spec stage rather than now is documented above as a conscious,
explicit risk acceptance for the Investment Committee to evaluate on its
own terms.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Child Data & Consent are both Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 47% (61/130, corrected
  denominator), up from 40% in v7 (or 45% if measured against v7's own
  legacy, inconsistent 135-point denominator). Progression across
  versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) → 40% (v7) → 47%
  (v8).

- Expert roster entries ≥3 sentences, each naming a specific
  case-study assumption: see `ExpertRoster.md`.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
improved from 40% to 47% (or from 40% to 45% under v7's own legacy
denominator), driven by a genuine decision closure (monetization model)
and a genuine, if directional, disclosure closure (Constraints) — not by
new research. The case's Critical gap (Legal & Compliance / Child Data &
Consent) remains open by the user's own explicit, deliberate choice to
defer it past this review stage; this is now documented plainly rather
than ambiguously. A v9 would need: the specialist legal opinion actually
commissioned and returned (whenever the user chooses to trigger the
build-spec stage), a specific subscription price point, either a scaled
user-research effort or a live pilot beyond the informal n=10 round, and
ideally a stated rationale (or revision) for the 15,000-in-90-days target
relative to the annual funnel model, to meaningfully advance the score
further.
