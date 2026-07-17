# Business Case: MiniMoney — v6

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v5.md` (prior version — **note:**
> this file was hand-edited directly by the user, not produced or
> reconciled by the Incubator, and contained one internal contradiction),
> `Clarifications_v6.md` (user clarifications supplied 2026-07-06,
> resolving that contradiction and supplying cited market research plus a
> scoping decision on the "Fintech Advance" course). This document is
> self-certified against the Incubator completion gate.

> **Changes from v5** are driven entirely by `Clarifications_v6.md`, which
> supplied three things: (1) **resolution of an internal contradiction**
> the Chief of Staff flagged in the user's hand-edited `BusinessCase_v5.md`
> — the hand-edited **Success Criteria** section stated the late-penalty
> cap at **7 Mbucks/week** (pilot cap: 3), while the un-touched
> **Operations** section (original Incubator v5 text) still stated a cap
> of **10 Mbucks/week**. The user has now confirmed **7 is correct** ("I
> want it capped at 7 as 10 may be overkill"); every section in this
> revision that referenced the escalating 5→6→10 figure has been corrected
> to **5→6→7**, pilot cap **3**, and this is now consistent end-to-end;
> (2) **rigorous, externally-cited market research** — Stats SA population
> data, a 2024 Stellenbosch device-ownership study, Statcounter OS-share
> data, SARB's Payments Study on banking-app usage, three named South
> African competitors (African Bank MyWORLD Power Pocket, MoneyAfrica Kids,
> MoneyTime SA), and cited POPIA/ARB advertising-to-children rules — each
> supplied with the user's own [Certain]/[Likely]/[Guessing] confidence
> tag. This is treated by the Incubator as genuine **Supporting Evidence**,
> materially different in kind from the Incubator's own prior general-
> knowledge candidate content, and the per-claim confidence tags are
> preserved rather than flattened into a single section-level rating; and
> (3) a **scoping clarification for "Fintech Advance"** (a course the user
> had already hand-added to `BusinessCase_v5.md`'s Value Proposition
> paywall table): it is exclusive to the **15-18 age band only**,
> conceptual/educational in scope only (teaches concepts of trending/
> entrepreneurial ventures, e.g. forex trading, dropshipping — **no in-app
> trading execution or brokerage functionality of any kind**), and gated
> behind **explicit parent opt-in even within the 15-18 band** — it is not
> automatically unlocked simply by reaching that paywall tier.

> Nothing beyond the case study, v5, and this clarification was used. All
> other sections are carried forward from v5 unchanged except where a
> clarification has a direct, logical knock-on effect (noted inline).


## What Changed in v6 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Per `Clarifications_v6.md`, this revision: (a) **corrects the late-penalty
cap** from the erroneous 10 Mbucks/week (carried in v5's Operations,
Technology, and Risks sections) to the user-confirmed **7 Mbucks/week**
cap (escalating 5→6→7), matching the figure the user had already hand-
edited into v5's Success Criteria, with the **pilot cap remaining 3
Mbucks/week** — this fix is applied consistently across Operations,
Technology, Risks, Success Criteria, Assumptions, and Outstanding
Questions; (b) **formally scopes "Fintech Advance"** — the course the user
hand-added to v5's Value Proposition paywall table without definition — as
15-18-only, conceptual/educational only with no in-app trading execution,
and requiring explicit parent opt-in distinct from the paywall unlock
itself; this narrows a risk the Incubator would otherwise have flagged
(teaching real trading concepts to minors alongside a real-money earnings
mechanic) and is reflected in Value Proposition, Legal & Compliance, Risks,
and the Curriculum Design extension; and (c) **upgrades Market &
Competition from Incubator-general-knowledge candidate content to a
Supported, evidence-backed section** — real population, device-access, OS-
share, and banking-engagement data, three named South African competitors,
and a funnel-based Year-1 adoption estimate are now available, each
carrying the user's own confidence tag. This third change has the largest
effect on this revision's Readiness Score, since Market & Competition
moves from Partial/Assumed to a stronger Partial/Supported footing (not yet
Complete, since several inputs remain [Guessing]-tagged extrapolations, not
[Certain] facts) and provides a real quantitative anchor — previously
entirely absent — for Objectives, Success Criteria, Revenue & Costs, and
Validation Strategy, each of which is updated accordingly.

**Headline finding of this revision:** for the first time across six
versions, MiniMoney's case includes externally-sourced, citation-backed
market data rather than purely Incubator-general-knowledge inference or
user-asserted mechanic description. This is a qualitatively different kind
of evidence and is treated as such throughout. However, three caveats
apply: (a) the research itself, by the user's own honest labeling, mixes
[Certain] facts (Stats SA population, Statcounter OS share, POPIA/ARB
statutory citations) with [Likely] inferences and explicit [Guessing]
extrapolations (the 6-18 population breakout, the SAM funnel, the Year-1
adoption/conversion estimates) — the Incubator preserves this distinction
rather than treating the whole research package as equally certain; (b)
the reconciled 7-Mbucks-per-week late-penalty cap is a corrected figure,
not a new risk resolution — the underlying trust/enforcement and family-
dynamics risk flagged in v5 is unchanged by lowering the cap from 10 to 7;
and (c) the Fintech Advance scoping narrows but does not eliminate a
legal/ethical question the Incubator flags in Legal & Compliance below:
teaching conceptual forex/dropshipping content to minors, even without
execution capability, still touches advertising-to-minors and financial-
promotion-adjacent rules that have not been reviewed by a specialist.


## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6-18), launching first in South Africa on **Android** (with iOS
porting planned as future work), that combines gamified task assignment
with a simulated payroll system. Before any tasks are assigned, the parent
submits a **budget** that sets the minor's "basic income"; tasks earn
**Mbucks** (a real-money-pegged in-app currency, e.g. 10 Mbucks = R10,
calculated as either a percentage of the budget or a parent-set fixed
amount, minimum 1 Mbuck per task) which accumulate into a "payslip," while
every completed task separately earns a fixed 10 **Mpoints** — a distinct,
non-monetary currency spendable only in a child-facing cosmetic in-app
store (stickers, themes). The parent receives a corresponding invoice and
pays the owed Mbuck-equivalent amount directly to the child using the
parent's own banking app — **MiniMoney itself never holds, transmits, or
takes custody of funds**. The chosen monetization direction is
**Freemium**, with real-money in-app purchases restricted to the parent's
account only. A minor cannot access any part of the app, including
education content, without a pre-existing, consenting parent account —
there is no education-only carve-out. Operations are comprehensively
described: task typology and recurrence (monthly/weekly/daily), an exam-
performance bonus mechanic, a completion-and-notification flow with
optional live-camera photo-proof, a 48-hour dispute window, and a payment-
confirmation mechanism enforced via an escalating late penalty — **now
confirmed at 5 Mbucks/week, rising to 6, capping at 7** (pilot cap: 3),
per `Clarifications_v6.md`'s correction of an internal contradiction in the
user's hand-edited v5 — rather than any technical payment verification;
the user explicitly acknowledges this cannot be strictly enforced unless
payment is someday routed through the app itself. The Freemium paywall
structure now includes a hand-added **"Fintech Advance" course**, which
`Clarifications_v6.md` clarifies is **exclusive to the 15-18 age band**,
**conceptual/educational only** (teaching the concepts of trending/
entrepreneurial ventures such as forex trading or dropshipping, with **no
in-app trading execution or brokerage functionality**), and gated behind
**explicit parent opt-in** even within that band — it does not
automatically unlock simply by reaching the relevant paywall tier. Most
significantly in this revision, Market & Competition is upgraded from pure
Incubator-general-knowledge inference to a **Supported** section backed by
cited South African data: Stats SA population figures, a 2024 Stellenbosch
device-ownership study, Statcounter OS-share data, SARB's Payments Study,
and three named South African competitors (African Bank MyWORLD Power
Pocket, MoneyAfrica Kids, MoneyTime SA), each carrying the user's own
[Certain]/[Likely]/[Guessing] confidence tag, which the Incubator preserves
rather than flattens. A funnel-based estimate derived from this research
suggests a realistic reachable pool of roughly 6.1 million South African
children (device present, parent already digitally banking), translating
to a plausible 18,000-61,000 Year-1 free installs and 360-2,440 Year-1
paying subscribers under stated assumptions — the least-certain,
[Guessing]-tagged figures in the chain. This is a materially more evidence-
backed case than v5, though Constraints (company-side budget/timeline/team
size), Supporting Evidence beyond this new research, and specific pricing/
paywall-feature decisions remain open.


## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Parents lack a structured, automated system to teach children (6-18)
real-world financial concepts — earning, budgeting, taxation/expenses, and
payment mechanics — using real money in a controlled, task-based
framework. Existing allowance-tracking apps typically either (a) simulate
money entirely in-app with no real bank transfer, limiting real-world
stakes, or (b) require manual parent bookkeeping with minimal education
layer, such as "Money Missions" offered by Acorns Early. `Clarifications_v6.md`
adds a more specific and locally-grounded framing of the underlying gate on
this problem: the true constraint is not device access among children (a
[Likely] 62% personal-device ownership by age 10, per the 2024 Stellenbosch
study) but **parent** willingness and digital-financial engagement, which
SARB's Payments Study puts at a [Certain] 50.3% of SA adults using banking
apps regularly (adjusted [Guessing] to 55-65% for the economically-active
parent cohort specifically). This reframes the Problem statement: the
addressable pain point is real, but it is gated by parent adoption
behavior, a narrower and less-evidenced filter than child device access
alone. Status remains Partial: the case still does not cite direct user
research (interviews, surveys) establishing that parents perceive this as
a problem worth paying to solve — the new research addresses market
reachability, not problem validation.


## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic (budget → tasks →
Mbucks → invoice → real bank payment → payslip, plus a parallel Mpoints
cosmetic-reward loop) rather than a simple debit-card-for-kids model. The
clarification that MiniMoney never touches funds directly reinforces this
positioning: MiniMoney's opportunity is more accurately framed as an
**edtech app with a payroll-simulation UX**, competing on curriculum
quality and mechanic engagement rather than on banking features. This is
now substantiated, not merely inferred: `Clarifications_v6.md` confirms
that **no direct South African incumbent does what MiniMoney does**
(gamified, standalone, mobile-native, direct-to-parent-distribution
consumer app) — the three named local players each miss at least one of
these dimensions (see Market & Competition). This is a genuine evidenced
gap, upgraded from v5's inference-only framing, though the same research
notes this also means **no local comparable exists to validate willingness-
to-pay against** — the opportunity is real but unproven at the price point
and mechanic MiniMoney proposes. Evidence upgraded from Assumed (v5) to
Supported given the cited competitive scan.


## Objectives

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The case study itself states only a functional objective: build an app
that (1) requires a parent to submit a budget before task assignment,
(2) assigns tasks (predefined or custom, recurring or one-off),
(3) converts completion into Mbuck earnings (percentage-of-budget or
fixed-rate) and a flat 10-Mpoint cosmetic-currency reward, (4) applies an
exam-performance bonus mechanic, (5) generates a parent invoice and child
payslip inclusive of any arrears from late payment, (6) prompts/confirms a
real bank payment made by the parent via their own banking app with an
escalating late-penalty mechanism now confirmed at 5→6→7 Mbucks/week
(pilot cap 3), and (7) delivers age-appropriate financial education —
fully gated behind an established, consenting parent account.

**Objectives now grounded in `Clarifications_v6.md`'s market research
(Evidence: Supported for the funnel logic; Evidence: Assumed for specific
numeric targets the user has not confirmed):**

1. **Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
   payment loop, including the dispute and late-penalty mechanics, with a
   small pilot cohort of South African families (candidate target: 20-50
   families) before wider release, on the confirmed Android platform.

2. **Launch (first 90 days):** the newly-supplied funnel model gives the
   Incubator its first evidence-anchored (though [Guessing]-labeled by the
   user) reference range rather than a fabricated target: **18,000-61,000
   free installs and 360-2,440 paying subscribers in Year 1**, derived from
   a ~6.1M reachable-household estimate × 0.3-1% Year-1 install capture ×
   2-4% free-to-paid conversion. This is a modeled range, not a commitment
   or a validated forecast, and the user's own [Guessing] tag on the
   adoption-rate inputs should be read by any reader as the weakest link in
   the chain.

3. **Growth (6-12 months):** validate the Freemium conversion assumption
   against the newly-supplied 2-4% (ads-supported hybrid) or 1-3%
   (subscription-only) reference ranges — reconciling these against the
   user's own hand-edited 2% Success Criteria figure (see Success Criteria
   below, where this reconciliation gap is flagged explicitly) — validate
   curriculum engagement as a leading indicator of retention, and evaluate
   iOS port timing based on Android traction.

These remain candidate objectives: the funnel model supplies a real range
for the first time, but no specific target within that range has been
confirmed or prioritized by the user.


## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Candidate and user-supplied success criteria, mapped to the objectives
above, with the late-penalty contradiction now resolved:

- **Pilot success:** a defined percentage (candidate: majority) of pilot
  families complete at least 4 consecutive weekly task→payslip cycles
  without abandoning the app, at least one family per cohort self-reports
  the parent successfully made the real bank payment each cycle, and the
  48-hour dispute window and late-penalty mechanic are exercised at a rate
  of **5 Mbucks per week of delay, escalating to 6 Mbucks in month 2, and
  capping at 7 Mbucks per week** — this figure is now confirmed by
  `Clarifications_v6.md` and is consistent with every other section in
  this document. Running arrears accumulate and are visible as a line
  item. Minors are able to generate "request for payment" prompts after
  month 1, and every month thereafter that arrears remain unsettled, both
  to encourage parent settlement and to teach the minor the procedure of
  requesting payment. **For the pilot specifically, the late-penalty cap
  is 3 Mbucks/week**, lower than the general 7-Mbuck cap, reflecting a
  more conservative pilot-phase design.

- **Curriculum engagement:** the user's hand-edited figure of **30%** of
  child users complete the daily/weekly micro-course content within the
  first month of use. No external benchmark is cited for this figure; it
  remains a user-set target, not a researched one.

- **Operational health:** the user's hand-edited figure of **65%** of
  tasks are marked complete without triggering a parent dispute, and
  photo-proof tasks (where required) are completed without friction. As
  with curriculum engagement, no external benchmark supports this specific
  number.

- **Freemium conversion:** the user's hand-edited figure of **2%** is
  now assessable against `Clarifications_v6.md`'s newly-supplied ranges:
  **2-4% for an ads-supported hybrid freemium model**, or **1-3% for a
  pure subscription model** (both [Guessing]-tagged by the user as
  inference from adjacent markets, not SA-specific data). The user's 2%
  figure sits within both ranges but at the low end of the ads-hybrid range
  and mid-range for subscription-only — **the Incubator flags that neither
  document states whether the user intends ads-supported or subscription-
  only monetization, so which benchmark the 2% figure should be judged
  against is not yet resolved.** This is a specific, named reconciliation
  gap carried into Outstanding Questions below.

- **Retention:** a defined 90-day retention benchmark for the parent
  account (candidate framing only — no figure proposed, no external
  benchmark supplied).

Status remains Partial: real figures now exist for four of five criteria,
but two (curriculum engagement, operational health) have no external
benchmark, and the Freemium conversion figure has an unresolved ambiguity
about which monetization sub-model it should be measured against.


## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Directly named or clearly implied in the source:

- **Children/teens (6-18)**, with sub-bands 6, 7, 8, 9-10, 11-14, 15-18 —
  the end users who complete tasks, earn Mbucks (real-money-pegged) and
  Mpoints (cosmetic, non-monetary), and receive education content. A minor
  cannot access any part of the app — including education content —
  without a pre-existing, consenting parent account. Per
  `Clarifications_v6.md`, minors in the **15-18 sub-band specifically** are
  additionally the population eligible (subject to separate parent opt-in)
  for the **"Fintech Advance"** conceptual course.

- **Parents/guardians** — who submit the initial budget, assign or approve
  tasks, set task earn-rates, assign exam-period bonuses, receive the
  automated invoice, execute the real bank payment via their own banking
  app, mark payments complete (subject to the minor's accept/dispute
  step), decide which tasks require photo-proof, adjudicate disputes
  within a 48-hour window, are the freemium purchaser who unlocks
  additional features including now the 3+ minors tier and Fintech
  Advance, and are the sole gate for any minor's access to the app in any
  form. Per `Clarifications_v6.md`, parents are additionally the sole,
  separate gate for enabling Fintech Advance access for an eligible 15-18
  minor, distinct from and in addition to the general paywall unlock for
  that content tier.

- **The app operator (Masood / MiniMoney)** — owns the platform, curriculum
  content, and invoice/payslip-generation logic, but not the payment rail
  itself.

- **The South African Information Regulator** (enforces POPIA) and,
  newly specific per `Clarifications_v6.md`, the **Advertising Regulatory
  Board (ARB)**, whose Code of Advertising Practice Clause 14 governs any
  advertising content directed at or exposed to children — relevant if any
  ad-supported free-tier monetization is pursued (see Business Model and
  Legal & Compliance).

- Three named **competitor/adjacent-market stakeholders** newly identified
  per `Clarifications_v6.md`: African Bank (MyWORLD Power Pocket),
  MoneyAfrica Kids, and MoneyTime SA — not partners, but relevant
  competitive/positioning stakeholders now that they are named rather than
  inferred.

Still not addressed in the source: app store platforms (Apple/Google)
whose policies on minors and financial transactions would apply, and the
parent's bank (as the external rail the parent uses independently of
MiniMoney). A future **AI mediator** feature for dispute resolution remains
explicitly out of current scope.


## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Two user tiers are explicit in the source: children/teens aged 6-18 with
sub-bands 6, 7, 8, 9-10, 11-14, 15-18, and their parents, who are the
actual paying/administrating customer and bank-account holder. Geography
is confirmed: initial launch is South Africa. Platform is confirmed:
Android first, iOS as future work. `Clarifications_v6.md` now substantiates
the Android-first addressable-market question left open in v5:
**Statcounter [Certain] data puts Android at 76.74% of South African
mobile OS share as of May 2026, versus iOS at 23.24%** — this is traffic
share, not population share, and the user's own caveat notes it skews
toward higher-usage/urban devices, but it is a reasonable proxy indicating
an Android-first launch reaches the large majority of the reachable market
rather than materially under-serving it, as the Incubator could only
speculate about in v5. The customer relationship remains unambiguous: the
parent account is primary and must exist, with consent given, before a
minor can access anything. The freemium model implies free-tier parents
(acquisition/funnel) and paying parents who unlock additional features
(now including a 3+ minors tier and, for eligible families, Fintech
Advance), with in-app purchase confirmed parent-only.


## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household chores/tasks into a
structured payroll-like experience for their children, removing manual
tracking and adding a built-in financial literacy curriculum, with a
budget-driven earn-rate system and an exam-performance bonus mechanic that
ties financial reward to academic improvement. For children: a "real job"
simulation — payslips, overtime, deductions, exam bonuses — that pays out
in actual money via the parent's own bank transfer, tied to age-appropriate
lessons, alongside a separate, clearly-named (Mpoints, not "points")
lower-stakes cosmetic-reward system for engagement that does not expose
the child to any real-money transaction. The clarification reinforces that
MiniMoney's value is specifically as an **education-and-facilitation
layer**, not a payments product.

The Freemium/paywall structure (as hand-edited by the user into v5, now
reconciled with `Clarifications_v6.md`'s scoping) is:

| Feature | Freemium | Paywall |
| - | - | - |
| Setting up a budget | X | X |
| Adding minor | X | X |
| Adding 3+ minors |  | X |
| Access to education | X | X |
| Enrolling a child for additional content (expert videos, interactive content) |  | X |
| Enrolling a 15-18 minor for "Fintech Advance" (concepts of trending/entrepreneurial ventures, e.g. forex trading, dropshipping) |  | X — **and** requires separate explicit parent opt-in |

Anything without an explicit "(capped)" tag implicitly implies additional
usage of that feature sits behind the paywall. **Fintech Advance is now
fully scoped per `Clarifications_v6.md`:** it is exclusive to the 15-18
age sub-band (not available to any younger band, even under the paywall
tier); its pedagogical content is explicitly **conceptual/educational
only** — it teaches the concepts of trending/entrepreneurial ventures such
as forex trading or dropshipping, and does **not** enable any in-app
trading execution, brokerage functionality, or real-money trading activity
of any kind; and it is gated behind **explicit parent opt-in specifically
for this course**, separate from and in addition to the general paywall
unlock — reaching the paywall tier and having an eligible 15-18 minor does
not automatically grant access. This resolves what would otherwise have
been a significant undefined risk (teaching real trading concepts to
minors who are simultaneously earning and transacting in a real-money-
pegged in-app currency) into a materially narrower, better-governed
feature. With Freemium confirmed as the monetization direction and in-app
purchases confirmed parent-only, the core value proposition must be strong
enough in its free tier to drive adoption before any parent-facing paywall
is hit.


## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Materially upgraded in this revision.* `Clarifications_v6.md` supplies the
first externally-cited market research across six versions of this case.
The Incubator preserves the user's own per-claim confidence tags rather
than flattening them into a single section rating, since the underlying
claims genuinely vary in certainty.

**Population base (6-18):** [Certain] Stats SA's mid-2025 estimate puts
South Africa's total population at 63.1 million, with children under 15 at
26.2% (≈16.5 million). [Guessing] Stats SA does not publish a clean 6-18
breakout; extrapolating from single-year cohort size (~1.1M/year under 15)
and adding the 15-18 band gives a modeled estimate of roughly **14-15
million people aged 6-18** — not a directly sourced figure.

**Device access:** [Likely] A 2024 South Africa-specific study (five
former Model C high schools, Stellenbosch research) found 62% of learners
Grade 4-11 own a personal device by age 10, and 83% have a social media
account by age 12. This is personal ownership, not household access;
broader household access (shared device, parent's phone) is plausibly
75-85% for the 6-18 band, but this is a bounded guess, not a stat.

**OS split:** [Certain] Android holds 76.74% of mobile OS share in South
Africa as of May 2026 (Statcounter), iOS 23.24%. This is traffic share, not
population share, and skews toward higher-usage/urban devices, but is a
reasonable proxy indicating an Android-first launch reaches the large
majority of the reachable market.

**Parent financial-app engagement (the real gate):** [Likely] SARB's
Payments Study (SCPC/DCPC, 2023, adults 18+, national population base
40.5M) found 50.3% of South African adults use banking apps regularly —
more than internet banking (27%) but well short of universal. [Guessing]
The "80%+ of SA adults use mobile banking" figure seen on some aggregator
sites (citing GSMA/Statista) is lower-confidence, since it conflates mobile
money with banking apps; SARB's own survey data is the more defensible
number. [Guessing] Parents of school-age kids skew toward the economically
active 25-54 bracket, more banked/app-literate than the national average —
a reasonable adjustment is **55-65% banking-app engagement** for this
specific parent cohort, not the raw 50.3% national figure.

**Reachable-market funnel:** 14.5M kids × ~70% device access × ~60% parent
digital-financial engagement ≈ **6.1M kids in "reachable" households**
(device present, parent already comfortable transacting digitally). This
is the realistic Serviceable Addressable Market, not the 14.5M Total
Addressable Market — a distinction the Incubator flags as important and
not previously available in any prior version.

**Adoption rate (the least-evidenced figure in the chain):** [Guessing] No
public South African benchmark exists for kids'-financial-education-app
adoption specifically; this is inference from adjacent markets (GoHenry/
Greenlight UK/US), not South African data: a new entrant with no bank/
school distribution typically captures 0.3-1% of its reachable pool as
installs in year one. Free-to-paid conversion for freemium kids'-finance
apps benchmarks 2-6% globally; South Africa's lower discretionary income
for a "nice-to-have" app argues for the low end initially (1-3% for a pure
subscription model, 2-4% for an ads-supported hybrid model — see Business
Model).

**Rerun funnel:** ≈6.1M reachable kids × 0.3-1% Year-1 install capture ≈
**18,000-61,000 free users**. Applying 2-4% conversion ≈ **360-2,440
paying subscribers in Year 1**, plus marginal ad revenue mostly offsetting
a slice of infrastructure/CAC cost rather than adding a real second revenue
stream. Landing a distribution partnership (school, bank, telco bundle) is
flagged by the user as the actual lever to move this materially, not
organic install rate.

**Competition in South Africa specifically:** no direct incumbent does
exactly what MiniMoney does (gamified, standalone, mobile-native, direct-
to-parent-distribution consumer app). Three named local players, each
missing at least one defining dimension:

- **African Bank's MyWORLD Power Pocket** — kids' sub-accounts with debit
  cards under a parent account; a banking feature, not education-led.
- **MoneyAfrica Kids** — Nigerian-origin edtech app, courses/quizzes,
  parent-subscribes-child model; available but not built for South Africa.
- **MoneyTime SA** — web-based financial literacy curriculum, ages 10-15,
  sold B2B2C through schools; not a gamified, mobile-first consumer app.

None combine gamification + mobile-native + direct-to-parent distribution
the way GoHenry/Greenlight do in the US/UK — a real, evidenced gap — but it
also means there is no local comparable data to validate willingness-to-pay
against, which the Incubator flags as the natural trade-off of a genuine
first-mover position.

**What remains genuinely unresearched:** no pricing benchmark for a
comparable South African product exists beyond the general global freemium
conversion ranges cited above; no direct demand signal (waitlist, survey,
pilot interest) has been collected specifically for MiniMoney; and the
adoption-rate figures remain explicitly [Guessing]-tagged extrapolations
from non-South African markets, not South African data. Status upgraded
from Partial/Assumed (v5) to Partial/Supported (v6) — not Complete, because
the most decision-relevant figures (Year-1 adoption, conversion rate) are
still the user's own labeled lowest-confidence estimates, not sourced
facts.


## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Confirmed structurally: MiniMoney is a facilitation/education layer that
sits on top of the parent's own bank account and does not move or hold
funds. This removes the need for a money-transmitter license as a primary
business-model constraint (subject to full confirmation by a payments/
compliance expert — see Legal & Compliance).

**Chosen model — Freemium:**

- Free tier: the core budget/task/Mbuck/Mpoint engine and invoice/payslip
  generation are available at no cost, along with base education access
  and single-minor account setup.

- Paid tier: parents can unlock additional minors (3+), additional content
  (expert videos, interactive content), and — for eligible 15-18 minors
  only, subject to separate explicit parent opt-in — the **Fintech
  Advance** conceptual course. Other candidates the Incubator flags for
  consideration (Evidence: Assumed, not sourced): customizable expense-rule
  templates, parent reporting/analytics, or the future AI-mediator dispute-
  resolution feature.

- Confirmed: any real-money in-app purchase (the Freemium paywall unlock)
  is available only through the parent's account. Children interact
  exclusively with the non-monetary **Mpoints** system — a flat 10
  Mpoints per completed task, redeemable in a child-facing in-app store for
  cosmetic items only. This is structurally separate from **Mbucks**, the
  real-money-pegged earnings currency (percentage-of-budget or fixed rate
  per task, minimum 1 Mbuck) used for the invoice/payslip loop.

- **New in this revision:** `Clarifications_v6.md`'s research raises
  advertising as a candidate partial-revenue/CAC-offset lever, not a
  standalone monetization pillar — [Guessing] ad revenue per free user is
  plausibly a few cents to low tens of cents per user per month given
  African-market CPMs sitting near the bottom of global ad-rate tables, and
  [Certain] statutory constraints (POPIA Section 34, ARB Clause 14 — see
  Legal & Compliance) would restrict any ad layer to contextual, non-
  profiled inventory rather than behavioral targeting on the child's own
  usage data. If pursued, this remains a "remove ads" psychological nudge
  toward the paid tier and a partial CAC offset, not a material revenue
  line, and it introduces a new item for Legal & Compliance review (see
  below) that did not previously exist as a live consideration.

- The four other candidate models from earlier versions (parent
  subscription-only, B2B2C schools/employers, bank-partnership referral,
  one-time purchase) remain retired, available only as fallback.

**Open implementation questions:** the specific price point/tier structure
for the freemium paywall; whether the ads-supported hybrid or subscription-
only path is intended (directly relevant to which conversion-rate benchmark
— 2-4% vs. 1-3% — the user's hand-edited 2% Success Criteria figure should
be judged against, an ambiguity not yet resolved by any input document);
and whether the Mpoints cosmetic store itself requires any app-store
disclosure given it still functions as a rewards mechanic aimed at
children.


## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Candidate cost categories:**

1. **Engineering/build cost** — scoped by Operations' detail: a budget-
   setting flow, a task engine, a dual-currency ledger, an exam-performance
   bonus calculator, a photo-proof capture flow, a dispute/decline
   workflow, a payment-confirmation accept/dispute flow, and an arrears/
   late-penalty calculator (now consistently 5→6→7 Mbucks/week, pilot cap
   3) visible on statements — a materially detailed engineering scope,
   though still not costed by the user. As a general category, cross-
   platform-intended (Android-first) consumer mobile apps of this
   complexity commonly run from tens of thousands to low hundreds of
   thousands of USD-equivalent in initial build cost depending on team
   composition — a general industry range, not a MiniMoney-specific quote.

2. **Curriculum content production cost** — likely the largest recurring
   cost if age-banded content requiring periodic updates is needed,
   including the newly-scoped Fintech Advance conceptual course for the
   15-18 band specifically.

3. **Customer acquisition cost (CAC)** — `Clarifications_v6.md` now
   supplies a first real, if [Guessing]-tagged, reference point: a new
   entrant with no bank/school distribution typically captures 0.3-1% of
   its reachable pool as Year-1 installs organically; a distribution
   partnership (school, bank, telco bundle) is flagged as the actual lever
   to move this materially, implying CAC via paid acquisition alone could
   be materially higher than via a partnership channel — no absolute Rand
   or USD CAC figure is available.

4. **Legal/compliance cost** — a POPIA-specialist legal opinion remains
   the one cost category the Incubator recommends the user obtain an
   actual quote for in the near term; `Clarifications_v6.md` adds a second,
   narrower item to this list if ads are pursued (ARB Clause 14 / POPIA
   Section 34 review of any ad-targeting approach).

**Candidate revenue framing, now anchored by real (if uncertain) figures
for the first time:** Freemium revenue = (number of active parent
accounts) × (free-to-paid conversion rate) × (price point for unlocked
features). Using `Clarifications_v6.md`'s funnel model: **18,000-61,000
Year-1 free installs, 360-2,440 Year-1 paying subscribers** at a 2-4%
(ads-hybrid) or 1-3% (subscription-only) conversion rate. No price point is
supplied, so absolute revenue cannot yet be modeled even with a subscriber-
count range now available; ad revenue is explicitly framed by the source
research as a partial CAC offset, not a standalone second revenue line, and
should not be modeled as material incremental revenue.

Status upgraded from Partial/Assumed (v5) to Partial/Supported (v6): real,
cited subscriber-count and conversion-rate ranges now exist for the first
time, though cost figures, pricing, and therefore absolute revenue
projections remain unsupplied.


## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

**Budget and earning mechanics:** Before any tasks are assigned, the parent
submits a **budget**, which sets the minor's "basic income." Task earn-
rates are derived from this budget either as a **percentage** (e.g. a task
worth 1% of a 100-Mbuck/month budget earns 1 Mbuck) or as a **parent-set
fixed Mbuck amount** — parent-configurable either way, with a stated
minimum of 1 Mbuck per task. Tasks not part of the basic budget agreement
earn additional Mbucks on top of the basic income. Every completed task,
regardless of Mbuck value, separately earns a flat **10 Mpoints** — the
non-monetary, cosmetic-store-only currency. Mbucks are described as pegged
1:1 in spirit to Rand (e.g. 10 Mbucks = R10), though the exact peg is
parent-visible via the budget-setting step rather than platform-fixed.

**Task structure:** Predefined tasks exist, grouped by type, assignable by
the parent; parents can also manually create custom tasks with an agreed
rate. Tasks can recur monthly, weekly, or daily, depending on task type.

**Bonus mechanic:** A distinct incentive exists for academic performance
during exam periods — the parent assigns a Mbuck bonus scaled to
improvement in average grade across the minor's subjects (example given: 6
subjects averaging 65%; every 5% improvement earns 5 Mbucks, capping at 15
Mbucks for a 15%+ improvement). This is a parent-configured, example-based
mechanic, not necessarily fixed platform logic.

**Completion, verification, and reporting flow:** The minor marks a task
complete; the parent receives a notification. A weekly report summarizing
completed tasks is sent to both parent and minor. Parents can require
photo-proof for specific tasks at their discretion — the photo must be
captured live via a direct camera-app launch (gallery/pre-taken photos are
not accepted), with the stated purpose of fostering trust on a task-by-
task basis.

**Dispute mechanism:** The parent can decline a marked-complete task within
a 48-hour window. Beyond that window, the source states "the parent and
minor need to compromise" — no formal, enforced resolution mechanism
exists for disputes not resolved within 48 hours; a future (explicitly
out-of-current-scope) AI-mediator feature is noted as a planned later
addition.

**Payment confirmation and enforcement:** Because payment happens via the
parent's own banking app (outside MiniMoney), MiniMoney cannot technically
verify payment occurred. The described mechanism is: the parent marks the
payment as complete; the minor then accepts or disputes that the payment
was actually made. The user explicitly acknowledges this cannot be
strictly enforced unless/until payment is someday routed through the app
itself. **A late penalty applies if payment is not marked complete: 5
Mbucks/week of delay, rising to 6 Mbucks/week after one month, capping at
7 Mbucks/week** — this figure is corrected in this revision per
`Clarifications_v6.md` ("I want it capped at 7 as 10 may be overkill"),
resolving a contradiction between the hand-edited Success Criteria section
of v5 (which already stated 7) and v5's original Operations text (which
incorrectly still stated 10). **For the pilot cohort specifically, this
cap is lower: 3 Mbucks/week.** Running arrears are displayed as a visible
line item on statements to both parent and minor. Minors may generate a
"request for payment" prompt after month 1, and every subsequent month
arrears remain unsettled.

**What remains open, even with this section Complete-rated:** the
Incubator flags (see Risks) that a real-money-denominated late-penalty
system, enforced entirely on mutual honor-system reporting between parent
and child with no technical payment verification, remains a novel
operational and possibly trust/relationship risk regardless of whether the
cap is 7 or 10 — the mechanism is fully described and now internally
consistent (hence Complete), but its soundness as a design choice is a
separate, open question raised in Risks and Validation Strategy.


## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The case study and clarifications together imply: a mobile app, with
Android confirmed as the primary launch platform and iOS planned as future
porting work. Required technical components include: a budget-setting
flow; a task-assignment engine supporting predefined and custom parent-
created tasks with monthly/weekly/daily recurrence; a dual-currency ledger
cleanly separating Mbucks (real-money-pegged, minimum 1 per task) from
Mpoints (flat 10 per completed task, cosmetic-store-only); an exam-
performance bonus calculator; a notification system; a weekly report-
generation feature; a direct camera-app invocation requirement for photo-
proof tasks; a 48-hour dispute-window timer/workflow; a payment-accept/
dispute workflow for the minor; an **arrears/late-penalty calculator with
escalating weekly rates (5→6→7, pilot cap 3) and statement visibility** —
this figure corrected in this revision to match Operations and Success
Criteria consistently; a document-generation feature (invoice for parent,
payslip for child, inclusive of arrears); no integration with banking
rails to move money; a feature-entitlement/paywall system for Freemium
(parent-account-only), now including a **distinct entitlement flag for
Fintech Advance** that must be gated by two independent conditions — the
paywall tier AND a separate explicit parent opt-in specifically for that
course, per `Clarifications_v6.md` — and an age-band check restricting
Fintech Advance visibility/eligibility to the 15-18 sub-band only. A single
universal consent gate (parent account, consent recorded, before any minor
access of any kind) remains sufficient; no two-mode account architecture is
needed. What remains unspecified: exactly how "linking" a child account to
a parent account is technically initiated; how payment confirmation is
captured beyond the accept/dispute UI; and technical specifics of the exam-
bonus grade-input mechanism.


## Legal & Compliance

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**This section remains flagged Critical**, though it is materially closer
to resolution than in any prior version. Resolved from prior versions:
MiniMoney does not hold, move, or take custody of funds, substantially
reducing money-transmitter licensing risk. Initial launch jurisdiction is
confirmed as South Africa, making **POPIA (Protection of Personal
Information Act)** the specific governing child-data-privacy law. A
minor cannot access any part of the app, including education content,
without a pre-existing, consenting parent account — the Incubator judges
this the more conservative and lower-legal-risk design choice, though a
specialist POPIA opinion confirming this model's sufficiency has still not
been obtained.

**New in this revision, per `Clarifications_v6.md`:** two additional,
specifically-cited statutory considerations now apply directly to the
Business Model's candidate advertising lever:

1. **POPIA Section 34** ([Certain], per the user's own citation) requires
   consent from a "competent person" (parent/guardian) before processing a
   child's personal information at all — including data used for ad
   targeting. This reinforces, with statutory specificity, the existing
   universal-consent-gate design, and extends it explicitly to cover any
   future ad-targeting data use, not merely account access.

2. **The Advertising Regulatory Board's Code of Advertising Practice,
   Clause 14** ([Certain], per the user's own citation) separately
   prohibits ads that exploit children's credulity, inexperience, or lack
   of judgment, and requires content aimed at children to avoid
   manipulative pressure tactics. Combined with POPIA Section 34, this
   rules out behavioral/programmatic ad targeting on the child's own usage
   data — any ad layer would need to be restricted to contextual, non-
   profiled inventory, or served against the parent's consented profile
   only. **This is a new, live compliance consideration that did not exist
   in v5**, since v5 did not yet raise advertising as a candidate
   monetization lever; it should be added to any legal review scope if ads
   are adopted.

**Also newly relevant per `Clarifications_v6.md`'s Fintech Advance
scoping:** the course teaches concepts of trending/entrepreneurial ventures
including forex trading and dropshipping to minors aged 15-18. Because the
course is explicitly conceptual/educational only, with **no in-app trading
execution, brokerage functionality, or real-money trading activity**, the
Incubator judges this substantially narrows (though does not entirely
eliminate) a candidate concern about financial-promotion-adjacent content
being served to minors. The dual gating (paywall tier + separate explicit
parent opt-in) further reduces this risk by ensuring no minor is exposed
to this content without a specific, distinct parental decision. The
Incubator nonetheless flags that **no specialist review has assessed
whether educational content describing speculative trading activities (even
without execution capability) triggers any advertising-to-minors or
financial-education-content rule** beyond the general POPIA/ARB
considerations already cited — this is a new, narrow, but unresolved
question, not a closed one.

**Still open and unaddressed:** (1) app store policy compliance for
children's-category apps (Apple/Google); (2) whether "payslip," "invoice,"
"late penalty," and "arrears" terminology carries any unintended
regulatory implication; (3) data retention/deletion policies for minors;
(4) whether the late-penalty mechanic (now confirmed at 5→6→7 Mbucks/week,
pilot cap 3) has any unintended regulatory or consumer-protection framing
issue — the specific cap figure does not change this open question, only
its magnitude; (5) whether the exam-performance bonus mechanic has any
schools-data-privacy dimension if grade data is ever sourced from or shared
with a school system.


## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Risks identifiable from the described mechanic and clarifications:

- **Regulatory risk (Critical, substantially narrowed):** the money-
  transmission licensing risk remains substantially narrowed. The child-
  consent risk is reduced by the universal parental-consent gate. A
  specialist legal opinion is still recommended.

- **Child-safety/data-privacy risk (Critical, substantially reduced):**
  residual risk is limited to standard child-directed-app considerations
  (data retention, app-store disclosure) rather than a live, unresolved
  design question.

- **Trust/enforcement risk (elevated detail, not resolved):** MiniMoney
  still cannot itself detect or confirm that the parent's banking-app
  payment actually occurred. The accept/dispute mechanism and escalating
  late-penalty (**now confirmed 5→6→7 Mbucks/week, pilot cap 3** — the
  figure corrected in this revision) give this risk much more operational
  detail, but do not resolve the underlying enforcement gap. **Lowering
  the cap from the erroneous 10 to the confirmed 7 does not reduce this
  risk's fundamental nature** — it is a magnitude adjustment to an
  unresolved enforcement design, not a resolution of it.

- **Late-penalty/relationship risk (unresolved, magnitude corrected):** an
  escalating, real-money-denominated penalty charged against a minor for a
  parent's own delayed payment is a mechanic with real potential for
  parent-child friction, perceived unfairness, and possible reputational/
  regulatory scrutiny. The cap is now confirmed at 7 (not 10), which
  somewhat softens the maximum weekly exposure, but the structural
  fairness question (a minor penalized for an adult's administrative
  delay) is unchanged by this correction.

- **Dispute-escalation risk (unresolved):** the described dispute process
  beyond the 48-hour window has no formal resolution mechanism in current
  scope. Families without an effective informal compromise mechanism have
  no in-app recourse.

- **Terminology/perception risk (unchanged):** framing a child's allowance
  as "payslip," "overtime," "expenses," "late penalty," and "arrears"
  could raise concerns among child psychologists or regulators about
  normalizing labor-like or debt-like relationships between parent and
  child.

- **New — Advertising/child-data risk (introduced by `Clarifications_v6.md`):**
  if an ads-supported hybrid monetization path is pursued, POPIA Section 34
  and ARB Clause 14 jointly restrict any ad-targeting approach to
  contextual, non-profiled inventory — a real constraint on the candidate
  ad-revenue lever raised in Business Model, and a compliance risk if not
  designed for from the outset.

- **New — Fintech Advance content risk (narrowed but not eliminated,
  introduced by `Clarifications_v6.md`):** teaching conceptual forex-
  trading and entrepreneurial-venture content to 15-18-year-olds, even
  without in-app execution capability, carries some residual risk of being
  perceived as normalizing speculative financial activity to minors. The
  dual gating (paywall + explicit separate parent opt-in) and the explicit
  exclusion of any trading execution substantially narrow this risk
  relative to what it would be as an unscoped feature, but no specialist
  has reviewed whether the conceptual content itself requires any
  additional disclosure or age-appropriateness review.

- **Competitive risk (narrowed, evidence-backed):** three named South
  African competitors exist, none combining MiniMoney's exact mechanic —
  a real, evidenced gap, but one that also means no local pricing/adoption
  comparable exists, itself a risk to revenue forecasting confidence.

- **Monetization-execution risk (partially narrowed):** Freemium is
  selected and IAP is confirmed parent-only; specific paywalled features
  are now more fully defined (3+ minors, additional content, Fintech
  Advance), but pricing and the ads-vs-subscription-only decision (which
  determines which conversion benchmark applies) remain undefined.

- **App-store policy risk (unchanged):** the Mpoints cosmetic store aimed
  at children may still be subject to child-directed-app design and
  disclosure requirements on both platforms.

- **Platform-concentration risk (narrowed, evidence-backed):** Statcounter
  data ([Certain]) now shows Android at 76.74% of South African mobile OS
  share, meaningfully de-risking the Android-only launch decision relative
  to v5's entirely unquantified concern, though the 23.24% iOS share
  represents a real, non-trivial excluded segment at launch.

- **Adoption/forecasting risk (new, introduced by `Clarifications_v6.md`):**
  the Year-1 adoption and conversion figures underpinning the funnel model
  (18,000-61,000 installs, 360-2,440 paying subscribers) are explicitly
  [Guessing]-tagged by the user as extrapolation from non-South-African
  adjacent markets (GoHenry/Greenlight), not South African data — these
  figures should be treated as a plausible planning range, not a forecast,
  and the Incubator flags a risk of over-reliance on them in downstream
  financial planning.


## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Assumptions made by the Incubator in order to complete this document, all
flagged as such:

- **Confirmed by clarification (no longer an assumption):** the parent
  pays the child directly from the parent's own existing bank account via
  the parent's own banking app; MiniMoney does not hold or move funds.
  Initial launch jurisdiction is South Africa. Monetization direction is
  Freemium with parent-unlockable features, IAP parent-only. Every minor's
  access to the app, in any form, requires a pre-existing, consenting
  parent account. Primary launch platform is Android, with iOS as planned
  future work. Two distinctly-named currencies exist — Mbucks and Mpoints.
  **The late-penalty cap is confirmed at 7 Mbucks/week (escalating 5→6→7),
  with a pilot-specific cap of 3 Mbucks/week** (`Clarifications_v6.md`,
  resolving the v5 internal contradiction). **Fintech Advance is confirmed
  as 15-18-only, conceptual/educational only with no in-app trading
  execution, and gated behind a separate explicit parent opt-in in addition
  to the paywall unlock** (`Clarifications_v6.md`).

- **Newly treated as Supported evidence, not Incubator assumption, per
  `Clarifications_v6.md`:** South African population, device-access, OS-
  share, and parent banking-app-engagement figures, each carrying the
  user's own [Certain]/[Likely]/[Guessing] tag as cited above; three named
  South African competitors; and the statutory citations for POPIA Section
  34 and ARB Clause 14.

- Still assumed: the exact Mbucks-to-Rand peg (illustrated as 10 Mbucks =
  R10) is fixed platform-wide rather than parent-configurable.

- Still assumed: the app is intended primarily as a South African consumer
  (B2C) product at launch; multi-market expansion beyond South Africa is
  not stated.

- Still assumed: the exam-performance bonus mechanic's grade data is self-
  reported or parent-entered rather than sourced from any school
  information system.

- Still assumed: the late-penalty mechanic (now 5/6/7) is intended as a
  behavioral/administrative nudge to the parent rather than a genuine
  financial detriment to be strictly collected — the source does not
  clarify what happens to accumulated arrears if never paid.

- **Newly flagged as an unresolved ambiguity, not an assumption:** whether
  the user's hand-edited 2% Freemium conversion figure in Success Criteria
  is intended as a target within, at the low end of, or independent of
  `Clarifications_v6.md`'s newly-supplied 2-4% (ads-hybrid) / 1-3%
  (subscription-only) ranges — neither document states which, and this
  depends on an as-yet-undecided choice between ads-supported and
  subscription-only monetization.

- Carried forward: all Objectives, Success Criteria, and Validation
  Strategy candidate content not directly anchored by the new market
  research remains Incubator-generated from general product-management
  practice, not case-study-sourced or externally validated.


## Constraints

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Platform choice is confirmed: primary platform is Android, with iOS
porting planned as future development. `Clarifications_v6.md`'s Statcounter
data further substantiates this choice as reaching the large majority
(76.74%) of the South African mobile market. **Still not addressed:** no
company-side budget, timeline, or team-size figure has been supplied. The
Incubator continues to note that the in-product "budget" (the minor's
basic-income budget) is a distinct concept from the company's own
development/operating budget, which remains entirely unaddressed. The
user's known technical stack (Kotlin/Android, MQL5, Python, React/Three.js)
is not referenced anywhere in the case study or clarifications as a stated
constraint, though the confirmed Android-first platform choice is at least
directionally consistent with a Kotlin/Android skill set — the Incubator
notes this as a plausible, favorable alignment but does not treat it as a
stated fact.


## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Not addressed in the case study or clarifications as a stated plan by the
user beyond platform sequencing (Android first, iOS later). Given the
narrowing of scope achieved across all clarifications to date, the
Incubator flags — as a suggestion only, not a stated plan — an updated
candidate MVP sequence:

1. **Legal validation (recommended, no longer strictly gating):** obtain a
   specialist POPIA legal opinion confirming the universal parental-
   consent model is sufficient, and — newly in scope per
   `Clarifications_v6.md` — confirming whether the candidate ad-supported
   monetization path and/or the Fintech Advance conceptual course require
   any additional review beyond the general consent gate.

2. **Build the free-tier core mechanic** on Android: budget-setting, task
   engine, dual-currency ledger, exam-bonus calculator, notification/
   weekly-report flow, photo-proof capture, 48-hour dispute window, payment
   accept/dispute + late-penalty/arrears tracking at the **now-confirmed
   5→6→7 Mbucks/week schedule (pilot cap 3)**, and invoice/payslip
   generation — with the parent-primary consent gate enforced from the
   start.

3. **Pilot with a small South African family cohort** (candidate: 20-50
   families) to validate the curriculum-and-mechanic hypothesis, paying
   particular attention to the late-penalty and dispute mechanics' real-
   world effect on parent-child dynamics, using the confirmed pilot-
   specific 3-Mbuck cap.

4. **Layer in the paywalled "additional features"** (3+ minors, additional
   content, and — for eligible, opted-in 15-18 families — Fintech Advance)
   only after free-tier engagement is validated, resolving the ads-vs-
   subscription-only monetization decision before finalizing pricing.

5. **Evaluate iOS port timing** based on Android traction — now with
   Statcounter data suggesting Android alone reaches roughly three-
   quarters of the South African mobile market, somewhat reducing the
   urgency of an early iOS port relative to a market where OS share was
   more evenly split.

This remains a recommendation, not a roadmap supplied by the user; no
actual timeline, milestone plan, or resourcing detail has been supplied.


## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

No funding ask, runway, or financial projections are present in any input
document. See Revenue & Costs above for the full candidate cost/revenue
framework, now anchored for the first time by a real (if [Guessing]-tagged)
subscriber-count range: 360-2,440 Year-1 paying subscribers. No price
point is supplied, so absolute Rand/USD revenue still cannot be modeled.
The one cost item the Incubator recommends the user obtain a real, bounded
quote for in the near term remains the POPIA-specialist legal opinion,
now with a narrower additional scope item (ad-targeting compliance) if
that monetization path is pursued. Status upgraded from Partial/Assumed
(v5) to Partial/Supported (v6): a real subscriber-count range now exists,
though cost figures, pricing, and company-side budget/timeline remain
unsupplied.


## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Recommended validation priorities, in sequence, updated for this revision:

1. **Legal validation (recommended, reduced urgency):** obtain a POPIA-
   specific legal opinion confirming the universal parental-consent model,
   and, if pursued, the ads-supported monetization path's compliance with
   POPIA Section 34 / ARB Clause 14.

2. **Trust/enforcement AND late-penalty validation (elevated priority):**
   test whether parents will trust and consistently execute/self-report
   the real bank payment step, and specifically whether the now-confirmed
   escalating late-penalty mechanic (5/6/7 Mbucks/week, pilot cap 3)
   produces the intended gentle-nudge effect or instead generates parent-
   child conflict, perceived unfairness, or app abandonment.

3. **Dispute-mechanism validation:** pilot-test the 48-hour decline window
   and the "parent and minor need to compromise" informal resolution step.

4. **Market/demand validation, now with a real reference range to test
   against:** `Clarifications_v6.md`'s funnel model (18,000-61,000 Year-1
   free installs) provides, for the first time, a concrete planning range
   a low-cost smoke test (landing page, pilot-cohort signup) could be
   measured against, rather than validating in a vacuum. A smoke test
   targeted at South African Android-using parents specifically remains
   recommended before committing engineering or curriculum-production
   resources.

5. **Pricing/conversion validation, now with two named benchmark ranges to
   test against:** once specific paywalled features are finalized, a
   pricing-sensitivity survey with target parents should explicitly test
   which of the 2-4% (ads-hybrid) or 1-3% (subscription-only) ranges the
   business should plan against, and reconcile this against the user's own
   2% Success Criteria figure.

6. **Curriculum validation:** pilot-test the described daily/weekly micro-
   course with a small group of children across the stated age range,
   including — for eligible, opted-in 15-18 families — early feedback on
   the Fintech Advance conceptual course specifically.

This section remains Partial: the addition of two real reference ranges
(items 4 and 5) is a meaningful strengthening, but no validation activity
has actually occurred.


## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Materially upgraded in this revision.* `Clarifications_v6.md` supplies the
first genuine external evidence in this case's six-version history:

- [Certain] Stats SA mid-2025 population estimate (63.1M total population,
  26.2% under 15).
- [Likely] 2024 Stellenbosch-region study on learner device ownership
  (five former Model C high schools, Grade 4-11).
- [Certain] Statcounter mobile OS share for South Africa, May 2026 (Android
  76.74%, iOS 23.24%).
- [Likely]/[Guessing] SARB Payments Study (SCPC/DCPC, 2023) on South
  African adult banking-app usage (50.3% national figure, adjusted for
  parent-cohort skew).
- Three named South African competitors (African Bank MyWORLD Power
  Pocket, MoneyAfrica Kids, MoneyTime SA), identified by name rather than
  inferred.
- [Certain] statutory citations: POPIA Section 34 (competent-person
  consent) and the ARB Code of Advertising Practice Clause 14.

This is genuine Supporting Evidence, materially different in kind from the
Incubator's own general-knowledge candidate content elsewhere in this
document, and is treated as such. Status upgraded from Incomplete (v5) to
**Partial** — not Complete, because: (a) several of the most decision-
relevant figures (Year-1 adoption rate, conversion rate) remain the user's
own [Guessing]-labeled extrapolations from non-South-African markets, not
South African data or direct user/market testing; (b) no user interviews,
prior prototype, or direct demand signal (waitlist, survey) for MiniMoney
specifically has been collected; and (c) no legal opinion has been
obtained despite the new statutory citations being available. The
distinction between "cited external data exists" and "MiniMoney has been
validated with real users or a lawyer" remains material and unresolved.


## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Carried forward with resolved items marked and new items added per
`Clarifications_v6.md`:

1. ~~Does MiniMoney ever hold, move, or touch funds itself?~~ **Resolved:**
   No.

2. ~~What jurisdiction(s) is MiniMoney intended to launch in first?~~
   **Resolved:** South Africa.

3. ~~Of the five monetization options proposed, which does the user want
   to prioritize?~~ **Resolved:** Freemium.

4. ~~Does the intended education-only direct-signup carve-out require its
   own POPIA consent gate?~~ **Resolved by user decision:** no carve-out
   exists; universal parental consent applies to all access.

5. ~~How is task completion verified?~~ **Resolved:** minor self-marks
   complete, parent notified, optional live-camera photo-proof.

6. **Partially resolved, unchanged this revision:** parent can decline
   within 48 hours; beyond that, informal compromise is expected, with a
   future AI-mediator planned. **Open sub-question, unchanged:** what
   happens if informal compromise fails and no mediator exists?

7. **Resolved (mechanism), not resolved (enforcement):** parent marks
   payment complete, minor accepts/disputes; an escalating late penalty
   now confirmed at **5/6/7 Mbucks/week** (pilot cap 3) applies if not
   marked complete. **Open question, unchanged:** is in-app payment
   routing ever planned, and on what timeline?

8. ~~What is the intended platform?~~ **Resolved:** Android first, iOS
   planned as future porting work — now further substantiated by
   Statcounter OS-share data.

9. **Newly resolved in this revision:** ~~What is the correct late-penalty
   cap — 7 or 10 Mbucks/week?~~ **Resolved:** 7 Mbucks/week (escalating
   5→6→7), pilot cap 3, per `Clarifications_v6.md`, correcting the
   contradiction between v5's hand-edited Success Criteria and its
   original Operations text.

10. **Newly resolved in this revision:** ~~Is "Fintech Advance" available
    to all age bands, and does it enable real trading?~~ **Resolved:**
    exclusive to the 15-18 band only, conceptual/educational content only
    with no in-app trading execution or brokerage functionality, gated
    behind a separate explicit parent opt-in in addition to the paywall
    unlock.

11. **Still open:** what happens to accumulated arrears if a parent never
    pays — do they cap, get written off, escalate further, or accumulate
    indefinitely?

12. **Still open:** is the exam-performance bonus mechanic's grade data
    self-reported/parent-entered, or is any school-system integration ever
    planned?

13. **Still open:** is the Mbucks-to-Rand peg (illustrated as 10:R10)
    fixed platform-wide, or parent-configurable like the task earn-rate
    is?

14. **Still open:** what are the specific age-band splits for the
    curriculum beyond the newly-confirmed Fintech Advance (15-18) scoping
    — e.g. 6-9, 10-13, 14-18 for the general curriculum — and who will
    author the content?

15. **New, introduced by this revision's reconciliation work:** does the
    user intend an ads-supported hybrid Freemium model or a subscription-
    only model? This determines which of `Clarifications_v6.md`'s two
    conversion-rate benchmarks (2-4% vs. 1-3%) the hand-edited 2% Success
    Criteria figure should be judged against, and neither document
    resolves it.

16. Is there any existing prototype, wireframe, or prior research the user
    has already produced that could accelerate validation beyond the
    market research now supplied?

17. Has the user considered app-store policy restrictions specific to
    apps in the "designed for kids" category, particularly regarding the
    Mpoints cosmetic store, given the confirmed parent-only real-money IAP
    model?

18. What company-side budget, timeline, and team size are available for
    the actual build?

19. Does the user wish to commission a specialist POPIA/ARB legal opinion
    now that specific statutory sections are cited, to move Legal &
    Compliance from a directional Incubator judgment to an actual legal
    certification?


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
| Constraints | Partial | 1x | 2 |
| Roadmap | Partial | 1x | 2 |
| Financial Considerations | Partial | 1x | 2 |
| Validation Strategy | Partial | 1x | 2 |
| Supporting Evidence | Partial | 1x | 2 |
| Outstanding Questions | Complete | 1x | 5 |
| Curriculum Design (extension) | Partial | 1x | 2 |
| Child Data & Consent (extension) ★ | Partial | 2x | 4 |

Points earned:
2+2+2+2+2+2+2+2+2+2+2+5+2+4+2+2+2+2+2+2+2+5+2+4 = **54**

Points possible: 21 non-critical sections × 5 = 105, plus 3 critical
sections × 5 × 2 = 30. Total possible = **135**

**Readiness Score = 54 / 135 = 40%**

**This score remains below the 70% completion gate threshold**, though it
represents a further improvement from v5's 39% (v4's 36%, v3's 24%). No
section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial; Supporting Evidence moves from Incomplete (0
pts) to Partial (2 pts) — the only section-level status change in this
revision — reflecting the newly-supplied cited market research. The
overall score increase (39% → 40%) is small in percentage terms because
Supporting Evidence is a single 1x-weighted section among 24; the
qualitative significance of this revision (genuine external evidence
existing for the first time, an internal contradiction resolved, and a
previously-unscoped feature now fully defined) is larger than the numeric
score movement alone suggests, which the Incubator flags for the
Investment Committee as a structural feature of the scoring rubric, not an
error.

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** — the
   universal parental-consent design is in place, and specific statutory
   citations (POPIA Section 34, ARB Clause 14) are now available for the
   first time, but a specialist legal opinion has still not been obtained
   to confirm sufficiency, and the newly-raised ad-targeting and Fintech
   Advance content questions add narrow new scope to that eventual review.

2. **Supporting Evidence (Partial, upgraded from Incomplete)** — genuine
   cited market research now exists, but no direct user testing, prior
   prototype, or legal opinion for MiniMoney specifically has been
   obtained, and the most decision-relevant figures (adoption/conversion
   rates) remain the user's own labeled lowest-confidence estimates.

3. **Objectives / Success Criteria / Validation Strategy (Partial,
   materially strengthened but not resolved)** — now anchored by a real
   funnel model, but specific numeric targets remain unconfirmed, and an
   unresolved ambiguity exists (Outstanding Question 15) about whether the
   user's hand-edited 2% conversion figure is meant against the ads-hybrid
   or subscription-only benchmark.

4. **Constraints (Partial, unchanged)** — platform choice is confirmed and
   substantiated by OS-share data, but no company-side build budget,
   timeline, or team-size figure has been supplied in any version.

5. **Late-penalty and dispute-escalation mechanics (Operations Complete,
   Risks Partial)** — now internally consistent at 5→6→7 Mbucks/week
   (pilot cap 3) across every section, but the correction of the cap
   figure does not resolve the underlying, still-untested trust/fairness
   risk; this remains a priority item for pilot validation.


## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs.*

The age floor of 6 is intentional, to introduce financial literacy "as
early as 6." The curriculum does not need to be a full year's worth of
content, but rather a short course completable daily or weekly, with
example mechanics including (a) differentiating between different
currencies, and (b) basic transactions that introduce "word sums" as a
mechanism for the child to derive what remains owed or returned after
paying for goods or services. **Newly and fully scoped in this revision:**
the **"Fintech Advance"** course is a distinct, higher-tier curriculum
element exclusive to the **15-18 sub-band**, teaching the concepts of
trending/entrepreneurial ventures (forex trading, dropshipping) as
**conceptual/educational content only** — explicitly excluding any in-app
trading execution or brokerage functionality — and is described by the
user as a "non-negotiable requirement" for that age band's curriculum,
while access to it for any individual minor remains solely a parent
decision made at the parent's discretion, gated separately from (in
addition to) the general paywall tier that contains it.

**Still unresolved:** specific age-band curriculum splits for the general
curriculum (e.g. 6-9, 10-13, 14-18) and learning objectives per band;
instructional format beyond "a short daily/weekly completable course"
(game-based, video, quiz, narrative — unspecified); alignment to any
existing financial literacy standard; who authors the content, including
the newly-scoped Fintech Advance material specifically, which the
Incubator flags may require subject-matter expertise (financial markets
education) distinct from the general curriculum's authorship needs.


## Legal & Compliance — Child Data & Consent (Domain Extension)

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

*Appended because MiniMoney targets users as young as age 6, triggering
child-directed-app compliance obligations beyond general Legal &
Compliance.*

**Model:** every minor, regardless of age or which part of the app they
wish to use, requires a pre-existing, consenting parent account before any
access is granted. This directly matches the Incubator's own recommended
conservative design.

**Newly specific per `Clarifications_v6.md`:**

1. **POPIA Section 34** ([Certain]) is now cited by name as the statutory
   basis for the competent-person consent requirement, and is confirmed to
   extend to any data used for ad-targeting purposes, not merely account
   creation or earnings features.

2. **ARB Code of Advertising Practice, Clause 14** ([Certain]) is newly
   identified as a distinct, additional compliance dimension if any ad-
   supported monetization is pursued — prohibiting ads that exploit
   children's credulity, inexperience, or lack of judgment, and requiring
   avoidance of manipulative pressure tactics in content aimed at children.
   This did not previously exist as a named consideration in this case.

3. **Fintech Advance's scoping** (15-18-only, conceptual-only, no trading
   execution, dual-gated behind paywall + separate parent opt-in)
   substantially narrows what would otherwise be a significant open
   question about exposing minors to speculative-finance content alongside
   a real-money earnings mechanic, though the Incubator flags this
   narrowing has not itself been confirmed sufficient by any specialist
   review of advertising-to-minors or financial-education-content rules
   beyond the general POPIA/ARB citations above.

**Resolved relative to prior versions:**

1. The education-only direct-signup carve-out no longer exists as a
   described feature.

2. The consent model is maximally conservative: universal, prior, parent-
   primary, with no exceptions.

**Unresolved, specifically:**

1. A specialist POPIA/ARB legal opinion has still not been obtained —
   recommended, with a now-defined scope including the ad-targeting and
   Fintech Advance content questions.

2. Data retention/deletion policies for minors are not addressed.

3. Whether the Mpoints cosmetic store aimed at children requires
   independent child-directed-app review even though non-monetary.

4. Whether "payslip," "invoice," "late penalty," and "arrears" terminology
   carries any unintended regulatory implication.

5. Whether the exam-performance bonus mechanic implies any data-sharing
   relationship with schools.

This should still be confirmed via a South African data-protection and
advertising-law legal opinion before technical build begins.


## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Child Data & Consent are both Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 40% (up from 39% in v5,
  36% in v4, 24% in v3).

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate**,
though the Critical + Incomplete condition remains cleared and the
Readiness Score has improved further (39% → 40%). The score remains below
the 70% threshold because: (a) Supporting Evidence, while upgraded, still
lacks direct user testing, a prototype, or a legal opinion; (b) Objectives,
Success Criteria, and Validation Strategy, while now anchored by real
funnel data, still lack confirmed numeric targets and contain an unresolved
ambiguity about which conversion benchmark applies; (c) Constraints still
lacks company-side budget, timeline, and team-size figures; and (d) the
late-penalty and dispute-escalation mechanics, now internally consistent,
remain untested design choices. This document is constructed under a
strict no-invention rule and is delivered in its current state
deliberately: a v7 would need a specialist POPIA/ARB legal opinion, a
decision on ads-vs-subscription-only monetization (resolving Outstanding
Question 15), company-side budget/timeline/team figures, and ideally early
pilot feedback on the late-penalty and dispute mechanics to meaningfully
advance the score further.
