# Business Case: MiniMoney — v7

> Prepared by: Incubator. Source input: `00\_CaseStudy.md` (verbatim user submission, 2026-07-05), `BusinessCase\_v6.md` (prior version, self- certified), `ResearchFindings\_v1.md` (Research House vendor output, Engagement 1 — 10 flagged items researched). This document is self- certified against the Incubator completion gate.

> **Changes from v6** are driven entirely by `ResearchFindings\_v1.md`. Per standing instruction, Research House output is treated as **vendor** work product requiring the Incubator's own scrutiny before acceptance — it is never Verified-tier regardless of how confident it reads, and can only ever support raising a tag to **Supported**, never higher. The Incubator's own review of the 10 findings below determined which, if any, section tags actually move as a result.

> **Incubator's scrutiny of ResearchFindings\_v1.md, item by item:**

> - **Item 1 (SA-specific adoption/install-conversion benchmarks):** Negative finding — Research House confirms no such data exists publicly and cannot be produced by further desk research. This does **not** let the Incubator upgrade the Year-1 adoption/conversion figures beyond their existing \[Guessing\] tag; if anything, it *reinforces* keeping them Assumed/Guessing, now with documented confirmation that no better public data exists and that closing the gap requires either a commissioned survey (R80,000-R250,000, 3-6 weeks) or a live pilot. The Incubator accepts this as a genuine, well-sourced negative finding and folds the cost/timeline scoping into Validation Strategy and Financial Considerations, but does **not** move Market & Competition, Objectives, or Success Criteria's Status.

> - **Item 2 (local pricing benchmark):** MoneyTime SA's R995/year figure is directly sourced from the company's own pricing page — the Incubator accepts this as a real anchor point and folds it into Market & Competition and Revenue & Costs. Caveat preserved: MoneyTime SA is a lighter-weight product (course + game, no real allowance/task-payment workflow), so this likely under-anchors MiniMoney's own pricing. MoneyAfrica Kids' premium price remains genuinely unknown (Research House did not attempt a paywall walkthrough, correctly flagging that as outside desk-research scope).

> - **Item 3 (SA eCPM data):** A $0.80 blended eCPM figure from a third-party aggregator (not Google's own rate card), Medium confidence per Research House's own labeling. The Incubator accepts this as a directional planning figure only, not a firm input, and folds it into Business Model's ad-revenue discussion with that caveat preserved.

> - **Item 4 (ads-hybrid vs. subscription-only benchmark applicability):** Research House correctly identified this as a non-researchable internal decision dependency, not a fact to discover. The Incubator agrees and makes no tag change — Outstanding Question 15 remains open exactly as before.

> - **Item 5 (SA demand signal):** MoneyAfrica Kids' app-store download bands (10,000+ Google Play, 3,000+ Apple) and MoneyTime SA's self-published 130,000-student claim are accepted as directional, Medium-confidence signals — the Incubator explicitly preserves Research House's own caveat that the MoneyTime figure is a self- published company claim, not independently audited, and that neither figure is South-Africa-specific installs for MiniMoney's own category position. Folded into Market & Competition.

> - **Item 6 (app-store child-category policy):** Real, useful, directly sourced from Apple's and Google's own policy pages. Google's loyalty-point disclosure requirement is High confidence and directly actionable; Apple's applicability to a non-cash-out points system is Medium confidence (inferred from adjacent guideline language, not a direct statement). The Incubator accepts both and upgrades the app-store-policy risk and Technology section from a purely speculative flag to a Supported, partially-specific one — but this does **not** resolve the risk, only names it more precisely.

> - **Item 7 (POPIA retention norms):** The general Section 14 principle is High-confidence statutory text; no comparable-product-specific retention commitment was found. The Incubator accepts the statutory anchor into Legal & Compliance but preserves the finding that the "is POPIA's general principle sufficient without child-specific rules akin to COPPA" question remains a legal-interpretation question outside desk-research scope.

> - **Item 8 (terminology precedent):** Negative finding — no ARB/NCR ruling addresses "payslip"/"invoice"/"late penalty" terminology applied to minors. The Incubator accepts this as confirming the question is real and requires a legal opinion, not as resolving it.

> - **Item 9 (legal-opinion cost scoping):** A firm shortlist (Caveat Legal, VeraSafe, PPM Attorneys, Bregman Moodley, MJ Kotze Inc) and one sourced fixed-fee data point (R8,325 for a narrow addendum review) are High confidence; the R25,000-R80,000 bespoke-opinion range is explicitly Research House's own order-of-magnitude inference, Low-to- Medium confidence, not a quote. The Incubator accepts this as a budgeting anchor for Financial Considerations and Revenue & Costs, labeled accordingly as a scoping estimate, not a quote.

> - **Item 10 (build-cost scoping):** Five independent development-agency sources converge on a two-tier range (~$25,000-$40,000 basic MVP; ~$60,000-$120,000+ full-featured build). Medium confidence per Research House's own caveat (agency marketing pages have an incentive to anchor toward their own typical project size). The Incubator accepts this as a refinement of the previously single, very broad engineering-cost range in Revenue & Costs.

> **Net effect on tags:** No section moves from Partial to Complete or from Incomplete to Partial as a direct result of this research — the Incubator's own judgment is that none of the 10 findings resolve a section's core open question (they refine ranges, name specific policy clauses, and confirm several gaps are real rather than closing them). However, several sections gain materially more specific, sourced detail within their existing Partial status, and Evidence tags for Market & Competition, Business Model, Revenue & Costs, Legal & Compliance, and Financial Considerations are reinforced at Supported with stronger citations than v6 had. This is reflected inline below. The Readiness Score calculation later in this document explains why the numeric score is essentially unchanged despite this qualitative improvement.

## What Changed in v7 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

This revision incorporates `ResearchFindings\_v1.md`, a completed Research House vendor engagement covering 10 previously-flagged gaps. Per the Incubator's own scrutiny (detailed above), the findings: (a) confirm, with sourcing, that several gaps are genuinely unclosable by desk research alone (SA-specific adoption/conversion data, MoneyAfrica Kids' exact price, any ARB/NCR precedent on payslip-terminology-to-minors) — these remain Assumed/Guessing exactly as before, now with documented reasons why; (b) supply new, real, sourced anchors that did not exist in v6: a comparable SA product's actual price (MoneyTime SA, R995/year), an SA eCPM figure ($0.80 blended, Medium confidence), app-store child-category policy specifics (Apple Kids Category, Google Families Policy loyalty- point disclosure rule), a refined two-tier engineering-cost range, and a legal-opinion cost/firm scoping range (R25,000-R80,000, five named firms); (c) confirm the general POPIA Section 14 retention principle as statutory text, though a child-specific or comparable-product retention norm remains unfound. No section's Status changes as a direct result (Partial remains Partial throughout), because none of these findings resolve a section's central open question — they narrow ranges and add citations within sections that were already Partial/Supported. This is consistent with the Incubator's standing rule that vendor findings can only raise a tag to Supported, never to Verified, and only where the Incubator's own review agrees the finding actually informs the flagged gap.

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens (ages 6-18), launching first in South Africa on **Android** (with iOS porting planned as future work), that combines gamified task assignment with a simulated payroll system. Before any tasks are assigned, the parent submits a **budget** that sets the minor's "basic income"; tasks earn **Mbucks** (a real-money-pegged in-app currency, e.g. 10 Mbucks = R10, calculated as either a percentage of the budget or a parent-set fixed amount, minimum 1 Mbuck per task) which accumulate into a "payslip," while every completed task separately earns a fixed 10 **Mpoints** — a distinct, non-monetary currency spendable only in a child-facing cosmetic in-app store (stickers, themes). The parent receives a corresponding invoice and pays the owed Mbuck-equivalent amount directly to the child using the parent's own banking app — **MiniMoney itself never holds, transmits, or** **takes custody of funds**. The chosen monetization direction is **Freemium**, with real-money in-app purchases restricted to the parent's account only. A minor cannot access any part of the app, including education content, without a pre-existing, consenting parent account — there is no education-only carve-out. Operations are comprehensively described: task typology and recurrence (monthly/weekly/daily), an exam- performance bonus mechanic, a completion-and-notification flow with optional live-camera photo-proof, a 48-hour dispute window, and a payment- confirmation mechanism enforced via an escalating late penalty confirmed at **5 Mbucks/week, rising to 6, capping at 7** (pilot cap: 3) — rather than any technical payment verification. The Freemium paywall structure includes a **"Fintech Advance" course**, exclusive to the 15-18 age band, conceptual/educational only (no in-app trading execution), gated behind explicit parent opt-in beyond the general paywall.

Market & Competition remains backed by cited South African data (Stats SA population figures, a 2024 Stellenbosch device-ownership study, Statcounter OS-share data, SARB's Payments Study, three named South African competitors), and this revision adds a completed Research House engagement's findings on top: a real comparable price point (MoneyTime SA, R995/year), app-store child-category policy specifics (Apple, Google), refined engineering-cost bands (~$25,000-$40,000 MVP; ~$60,000-$120,000+ full build), and a legal-opinion cost/firm scoping range (R25,000-R80,000, five named South African POPIA/advertising-law firms). Equally important, the same engagement **confirms with sourcing** that several previously-flagged gaps genuinely cannot be closed by further desk research: no South Africa-specific kids'-app adoption/conversion benchmark exists, and no ARB/NCR ruling addresses the "payslip"/"invoice"/ "late penalty" terminology-to-minors question which is an accepted risk at this stage. While this remains the case's weakest links, it will be confirmed when  a live pilot is held and a paid legal opinion is retrieved. Constraints (company-side budget is minimal as this is a soloprenuer venture utilising AI and vibe coding to build the foundational rails with plans to onboard external expertise should the need arise. The time to launch is as early as 3 months from the date the final documents have been drafted and app building begins.This timeline is intentionally not specified as the key focus is to build the foundational structure which wil form the app. a specialist legal opinion will be gathered once we stat specing the build as that will inform what gets built while the current stage needs to answer if it should be built(the app as a whole not specific features), the  monetization- model decision will be subscription as the starting point while we investigate the possibility of introducing ads at a later stage(post launch as a possible V2 feature)as a source of revenue to reduce the cost of subscription.

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Parents lack a structured, automated system to teach children (6-18) real-world financial concepts — earning, budgeting, taxation/expenses, and payment mechanics — using real money in a controlled, task-based framework. Existing allowance-tracking apps typically either (a) simulate money entirely in-app with no real bank transfer, limiting real-world stakes, or (b) require manual parent bookkeeping with minimal education layer. The underlying gate on this problem is parent willingness and digital-financial engagement (SARB: 50.3% of SA adults use banking apps regularly, adjusted to a \[Guessing\] 55-65% for the economically-active parent cohort), not device access among children (\[Likely\] 62% personal- device ownership by age 10). This reframes the Problem statement: the addressable pain point is real, but it is gated by parent adoption behavior, a narrower and less-evidenced filter than child device access alone. `ResearchFindings\_v1.md` did not add new evidence to this section specifically (none of the 10 flagged items targeted Problem directly) — Status remains Partial: the case still does not cite direct user research (interviews, surveys) establishing that parents perceive this as a problem worth paying to solve.

Based on interviews completed with 10 families, 6 of the 10 confirmed their interest in using the app will 7 of the 10 were interested in the education aspect of the app.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's differentiator is the payroll-simulation mechanic (budget → tasks → Mbucks → invoice → real bank payment → payslip, plus a parallel Mpoints cosmetic-reward loop) rather than a simple debit-card-for-kids model. MiniMoney's opportunity is more accurately framed as an **edtech app with** **a payroll-simulation UX**, competing on curriculum quality and mechanic engagement rather than on banking features. No direct South African incumbent does what MiniMoney does; the three named local players each miss at least one defining dimension (see Market & Competition). `ResearchFindings\_v1.md` Item 5 adds a new, directional data point reinforcing this: MoneyAfrica Kids (the closest edtech comparable) shows meaningful but modest download volumes (10,000+ Google Play, 3,000+ Apple, pan-African not SA-specific), and MoneyTime SA claims a much larger B2B2C-mediated reach (130,000 students, self-published, not independently audited) — together suggesting real but unproven consumer appetite, with the strongest demonstrated reach coming via a schools-distribution model MiniMoney does not currently plan to use. Mini Money plans to launch this privately to parents directly but partner weith schools to use this as a tool to teach finacial literacy in real world. 

## Objectives

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The case study itself states a functional objective: build an app that (1) requires a parent to submit a budget before task assignment, (2) assigns tasks (predefined or custom, recurring or one-off), (3) converts completion into Mbuck earnings and a flat 10-Mpoint cosmetic-currency reward, (4) applies an exam-performance bonus mechanic, (5) generates a parent invoice and child payslip inclusive of any arrears, (6) prompts/ confirms a real bank payment with an escalating late-penalty mechanism confirmed at 5→6→7 Mbucks/week (pilot cap 3), and (7) delivers age- appropriate financial education — fully gated behind a consenting parent account.

1. **Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→ payment loop with a small pilot cohort of South African families (candidate target: 20-50 families) on the confirmed Android platform.

2. **Launch (first 90 days):** the funnel model gives a reference range of **18,000-61,000 free installs and 360-2,440 paying subscribers in** **Year 1**. `ResearchFindings\_v1.md` Item 1 confirms, with sourcing, that no South Africa-specific benchmark exists to validate this range against, and that closing this gap requires either a commissioned survey (R80,000-R250,000, 3-6 weeks, moves the figure only to Likely/ stated-intent, not actual behavior) or a live pilot. This is a materially useful confirmation that the range is a genuine planning estimate, not a researchable-but-unresearched fact — but it does not move the range itself or its \[Guessing\] tag. We aim to achieve a range of 15000 downloads withing the first 90 days

3. **Growth (6-12 months):** validate the Freemium conversion assumption against the 2-4% (ads-hybrid) or 1-3% (subscription-only) reference ranges, reconciling against the user's own hand-edited 2% Success Criteria figure (unresolved ambiguity, see Success Criteria); validate curriculum engagement as a leading indicator of retention; evaluate iOS port timing based on Android traction.

These remain candidate objectives: the funnel model supplies a real range, now confirmed by vendor research as the practical ceiling of what desk research alone can validate, but no specific target has been confirmed or prioritized by the user.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Candidate and user-supplied success criteria, mapped to the objectives above:

- **Pilot success:** a defined percentage (candidate: majority) of pilot families complete at least 4 consecutive weekly task→payslip cycles without abandoning the app; the escalating late-penalty mechanic (5 Mbucks/week, rising to 6 in month 2, capping at 7; pilot cap 3) is exercised and tracked, with running arrears visible as a line item. Minors can generate "request for payment" prompts after month 1 and monthly thereafter while arrears remain unsettled.

- **Curriculum engagement:** the user's hand-edited figure of **30%** of child users complete the daily/weekly micro-course content within the first month of use. No external benchmark is cited for this figure; `ResearchFindings\_v1.md` did not target this item and none of its 10 findings supply one — it remains a user-set target, not a researched one.

- **Operational health:** the user's hand-edited figure of **65%** of tasks are marked complete without triggering a parent dispute. As with curriculum engagement, no external benchmark supports this specific number.

- **Freemium conversion:** the user's hand-edited figure of **2%** remains assessable against the 2-4% (ads-hybrid) or 1-3% (subscription-only) ranges, with the same unresolved ambiguity as v6 about which sub-model the figure targets (Item 4 in `ResearchFindings\_v1.md` explicitly confirms this cannot be resolved by research — it is a pending internal product decision). This reconciliation gap is carried into Outstanding Questions below.

- **Retention:** a defined 90-day retention benchmark for the parent account (candidate framing only — no figure proposed).

Status remains Partial: real figures exist for four of five criteria, two (curriculum engagement, operational health) still lack an external benchmark, and the Freemium conversion ambiguity is now confirmed — not merely flagged — as unresolvable by research alone.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Directly named or clearly implied in the source:

- **Children/teens (6-18)**, with sub-bands 6, 7, 8, 9-10, 11-14, 15-18 — the end users who complete tasks, earn Mbucks and Mpoints, and receive education content. A minor cannot access any part of the app without a pre-existing, consenting parent account. Minors in the 15-18 sub-band are additionally eligible (subject to separate parent opt-in) for "Fintech Advance."

- **Parents/guardians** — who submit the budget, assign/approve tasks, set task earn-rates, assign exam-period bonuses, receive the automated invoice, execute the real bank payment, adjudicate disputes within a 48-hour window, and are the sole gate for any minor's app access and for Fintech Advance specifically.

- **The app operator (Masood / MiniMoney)** — owns the platform, curriculum content, and invoice/payslip-generation logic, but not the payment rail itself.

- **The South African Information Regulator** (enforces POPIA) and the **Advertising Regulatory Board (ARB)**, whose Code of Advertising Practice Clause 14 governs advertising directed at or exposed to children.

- Three named **competitor/adjacent-market stakeholders**: African Bank (MyWORLD Power Pocket), MoneyAfrica Kids, and MoneyTime SA.

- **Newly relevant per `ResearchFindings\_v1.md`:** Apple and Google, as **app-store platform stakeholders** whose Kids Category (Apple) and Families Policy (Google) requirements are now confirmed, with sourcing, to impose disclosure obligations on point/reward mechanics independent of real-money transactions — a stakeholder category previously named only as "still not addressed" in v6, now substantiated with specific, citable policy language.

Still not addressed: the parent's bank (as the external rail the parent uses independently of MiniMoney). A future AI mediator feature for dispute resolution remains explicitly out of current scope.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Two user tiers: children/teens aged 6-18 with sub-bands 6, 7, 8, 9-10, 11-14, 15-18, and their parents, who are the paying/administrating customer and bank-account holder. Geography: South Africa. Platform: Android first, iOS as future work, substantiated by Statcounter data (Android 76.74% of SA mobile OS share, May 2026). The customer relationship remains unambiguous: the parent account is primary and must exist, with consent given, before a minor can access anything. The freemium model implies free-tier parents (acquisition/funnel) and paying parents who unlock additional features, with in-app purchase confirmed parent-only. `ResearchFindings\_v1.md` did not target this section directly; no change to Status.

## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household chores/tasks into a structured payroll-like experience for their children, removing manual tracking and adding a built-in financial literacy curriculum, with a budget-driven earn-rate system and an exam-performance bonus mechanic. For children: a "real job" simulation — payslips, overtime, deductions, exam bonuses — that pays out in actual money via the parent's own bank transfer, tied to age-appropriate lessons, alongside a separate, lower-stakes cosmetic-reward system (Mpoints) that does not expose the child to any real-money transaction. MiniMoney's value is specifically as an **education-and-facilitation layer**, not a payments product.

The Freemium/paywall structure:

| Feature | Freemium | Paywall |
| - | - | - |
| Setting up a budget | X | X |
| Adding minor | X | X |
| Adding 3+ minors |  | X |
| Access to education | X | X |
| Enrolling a child for additional content (expert videos, interactive content) |  | X |
| Enrolling a 15-18 minor for "Fintech Advance" |  | X — **and** requires separate explicit parent opt-in |


`ResearchFindings\_v1.md` Item 2 supplies a new, directly relevant comparable: **MoneyTime SA prices its financial-literacy course/game** **product at R995/year (25% sibling discount for additional children)**. The Incubator accepts this as the first real South African price anchor for a child financial-education digital product, but preserves Research House's own caveat: MoneyTime SA is a lighter-weight product (course + virtual-money game, no real allowance/task-payment/banking-simulation workflow), so it likely **under-anchors** what MiniMoney — a materially more feature-rich product — could or should charge. This gives the value proposition a concrete, if imperfect, reference point it did not have in v6, without resolving MiniMoney's own pricing decision.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Population base, device access, OS split, and parent financial-app engagement figures are unchanged from v6 (Stats SA, Stellenbosch study, Statcounter, SARB Payments Study — see prior version for full figures), yielding a reachable-market funnel of ≈6.1M kids in "reachable" households and a Year-1 range of 18,000-61,000 free installs, 360-2,440 paying subscribers.

**New in this revision, from `ResearchFindings\_v1.md`:**

- **Item 1 confirms, with sourcing,** that no South Africa-specific kids'-app or kids'-fintech install-conversion or adoption-rate figure exists publicly, and that GoHenry/Greenlight (the adjacent-market comparables the funnel model extrapolates from) do not publish install-to-paid conversion rates either. This is accepted as a well-evidenced negative finding: it does not change the funnel model's numbers, but it confirms — rather than merely asserts — that the \[Guessing\] tag on these figures reflects a genuine, currently unclosable public-data gap, not an oversight.

- **Item 2 adds a real local pricing comparable:** MoneyTime SA, R995/year (see Value Proposition). African Bank's MyWORLD Power Pocket is confirmed to carry **no monthly fee** (a free sub-account add-on), which the Incubator notes sets a "zero price" anchor in the same market for a banking-feature (not education-led) alternative — relevant context for parent price sensitivity even though it is not a direct product comparable. MoneyAfrica Kids' premium price point remains unpublished/unknown.

- **Item 5 adds directional demand-signal data:** MoneyAfrica Kids shows 10,000+ Google Play downloads and 3,000+ Apple downloads (pan-African, not SA-specific, thin review base on Apple's side); MoneyTime SA claims over 1,500 schools and 130,000 students reached (self- published, not independently audited, B2B2C schools-distribution model rather than direct-to-parent). The Incubator accepts these as Medium-confidence directional signals only — the strongest demand signal found belongs to a distribution model (schools) that MiniMoney does not currently plan to use, which is itself a relevant competitive observation.

**Competition in South Africa specifically:** unchanged from v6 — no direct incumbent combines gamification + mobile-native + direct-to- parent distribution the way MiniMoney proposes; the three named local players each miss at least one defining dimension.

**What remains genuinely unresearched (now confirmed, not merely** **believed, to require paid/commissioned work beyond desk research):** SA- specific adoption/conversion benchmarks (commissioned survey, R80,000-R250,000, 3-6 weeks, or a live pilot); MoneyAfrica Kids' exact premium price (would require a manual account walkthrough or direct company outreach). Status remains Partial/Supported — not Complete, because the most decision-relevant figures (Year-1 adoption, conversion rate) remain \[Guessing\]-tagged extrapolations, now confirmed as unclosable by further desk research rather than simply unclosed.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Confirmed structurally: MiniMoney is a facilitation/education layer that sits on top of the parent's own bank account and does not move or hold funds, removing the need for a money-transmitter license as a primary constraint (subject to specialist confirmation — see Legal & Compliance).

**Chosen model — Freemium**, structurally unchanged from v6 (free tier: core engine, base education, single-minor setup; paid tier: 3+ minors, additional content, Fintech Advance with separate opt-in). Real-money IAP remains parent-only.

**Advertising as a candidate partial-revenue/CAC-offset lever:** `ResearchFindings\_v1.md` Item 3 supplies a first SA-specific eCPM data point: **$0.80 blended eCPM for South Africa**, sourced from a third- party AdMob-rate aggregator rather than Google's own published rate card (Medium confidence per Research House's own labeling; not broken out by ad format, and rewarded-video formats specifically are noted to outperform blended averages even in low-tier markets). The Incubator accepts this as a directional planning figure, consistent with the existing framing that ad revenue is a partial CAC offset / "remove ads" paywall nudge, not a standalone revenue pillar — this figure does not change that conclusion, it simply gives it a rough number. Statutory constraints (POPIA Section 34, ARB Clause 14) still restrict any ad layer to contextual, non-profiled inventory.

**Open implementation questions, unchanged:** the specific price point/ tier structure; whether ads-hybrid or subscription-only is intended (`ResearchFindings\_v1.md` Item 4 confirms this is a pending internal decision, not researchable); whether the Mpoints cosmetic store requires app-store disclosure — **now substantiated by Item 6:** Google Play's Families Policy confirms that loyalty-point/reward systems must disclose their accrual/redemption ratio conspicuously, in-app and in official program terms, regardless of whether real money is involved (High confidence, directly sourced). Apple's Kids Category guidelines require age-band selection and human-reviewed advertising, and separately state that "in-game currencies" that gate features or functionality may need to route through Apple's own IAP mechanism — Research House flags this Apple-side question (does this extend to a non-cash-out cosmetic points system) as Medium confidence, not fully resolved by the public guideline summary alone. This is a materially more specific, actionable finding than v6's purely speculative flag, though it does not close the question — it narrows it to a specific guideline reference worth a direct compliance review.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Candidate cost categories, refined this revision:**

1. **Engineering/build cost** — `ResearchFindings\_v1.md` Item 10 refines the previous single broad range ("tens of thousands to low hundreds of thousands of USD-equivalent") into a two-tier estimate, converging across five independent SA/offshore development-agency sources: **~$25,000-$40,000 for a basic-MVP-tier build; ~$60,000-$120,000+ for** **a full-featured build** matching all seven named engineering components (ledger, task engine, exam-bonus calculator, photo-proof, dispute/payment workflows, document generation), plus ongoing maintenance typically 15-20% of build cost annually. Medium confidence — these are development-agency marketing-page figures, which the Incubator notes carry an inherent incentive to anchor toward the agency's own typical project size; convergence across five independent sources increases confidence somewhat but this is not cross-checked against an independent industry-analyst benchmark. A tighter estimate would require sharing MiniMoney's actual spec with 2-3 agencies for informal ballpark quotes — a low-cost next step, not yet performed.

2. **Curriculum content production cost** — likely the largest recurring cost if age-banded content requiring periodic updates is needed, including the Fintech Advance course. No new data from this engagement.

3. **Customer acquisition cost (CAC)** — unchanged: a new entrant with no bank/school distribution typically captures 0.3-1% of its reachable pool as Year-1 installs organically; a distribution partnership is the actual lever to move this materially. No absolute Rand/USD CAC figure is available; `ResearchFindings\_v1.md` Item 1 confirms this cannot be tightened by desk research.

4. **Legal/compliance cost** — `ResearchFindings\_v1.md` Item 9 supplies a **scoping estimate (explicitly not a quote): R25,000-R80,000** **(~$1,400-$4,500)** for a bespoke opinion letter covering both POPIA consent-model sufficiency and ARB/ad-targeting-to-minors restrictions, plus a shortlist of five South African POPIA/advertising-law firms (Caveat Legal, VeraSafe, PPM Attorneys, Bregman Moodley Attorneys, MJ Kotze Inc) and one sourced fixed-fee comparable (R8,325 for a narrow Data Protection Addendum review, 48-hour turnaround). The Incubator accepts the firm shortlist and the R8,325 comparable as High- confidence, directly sourced; the R25,000-R80,000 bespoke-opinion range is explicitly Research House's own inference and is presented with that lower confidence preserved. This moves the legal-cost line item from "get a lawyer, cost unknown" to "get a lawyer, plausible range and firm shortlist identified" — a real, if soft, planning input that did not exist in v6.

**Candidate revenue framing:** unchanged funnel — 18,000-61,000 Year-1 free installs, 360-2,440 Year-1 paying subscribers, at 2-4% (ads-hybrid) or 1-3% (subscription-only) conversion. `ResearchFindings\_v1.md` Item 2's MoneyTime SA comparable (R995/year) offers a first real, if likely under-anchoring, South African willingness-to-pay reference point for a lighter-weight comparable product; no price point for MiniMoney itself is supplied, so absolute revenue still cannot be modeled. Item 3's $0.80 eCPM figure confirms ad revenue remains a marginal CAC-offset, not a material second revenue line.

Status remains Partial/Supported: cost ranges are now meaningfully more specific (engineering, legal) than in v6, and one real pricing comparable exists, but no MiniMoney-specific price point, absolute revenue model, or company-side budget has been supplied.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Unchanged from v6 — this section was already Complete and is not the subject of any of the 10 research items. Budget/earning mechanics, task structure, the exam-performance bonus mechanic, the completion/ verification/reporting flow, the dispute mechanism, and the payment- confirmation/late-penalty mechanism (5→6→7 Mbucks/week, pilot cap 3) remain as fully described in v6. The Incubator flags again (see Risks) that the real-money-denominated late-penalty system, enforced entirely on mutual honor-system reporting with no technical payment verification, remains a novel operational and possibly trust/relationship risk — the mechanism is fully described and internally consistent, but its soundness as a design choice is a separate, open question.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Core technical scope is unchanged from v6: a mobile app, Android confirmed primary launch platform, iOS as future porting work; budget- setting flow, task-assignment engine, dual-currency ledger, exam-bonus calculator, notification system, weekly report generation, camera-app invocation for photo-proof, 48-hour dispute-window workflow, payment- accept/dispute workflow, arrears/late-penalty calculator, document generation, no banking-rail integration, feature-entitlement/paywall system with a distinct Fintech Advance dual-gate.

**New in this revision, from `ResearchFindings\_v1.md` Item 6:** app-store child-category policy requirements are now substantiated with specific, sourced detail rather than a general "may be subject to" flag. **Google** **Play's Families Policy** confirms a concrete technical/design requirement: any fixed accrual/redemption ratio for a loyalty-point-style system (directly applicable to Mpoints) must be disclosed conspicuously both in-app and in official program terms — this is now a specific, actionable build requirement, not a speculative risk. **Apple's Kids Category** guidelines require an age-band selection at setup (5-and-under, 6-8, 9-11 — note this only covers ages up to 11, raising a new open question about how Apple's Kids Category framework interacts with MiniMoney's 6-18 span if an iOS port proceeds), human-reviewed advertising, parental gates for any unlock-style mechanic, and restrictions on transmitting device/personal data to third parties without explicit parental consent. Apple's applicability to a non-cash-out cosmetic points system specifically (does Mpoints need to route through Apple's own IAP mechanism) remains Medium-confidence/unresolved — Research House correctly declined to give a legal-interpretation answer, flagging this as needing either a direct App Review submission or legal/consultancy confirmation. This is a materially more specific finding than v6 had available, and the Incubator now recommends this be added explicitly to the technical build spec and to the Legal & Compliance review scope, rather than remaining a generic "may need to check" note.

What remains unspecified: exactly how "linking" a child account to a parent account is technically initiated; how payment confirmation is captured beyond the accept/dispute UI; technical specifics of the exam- bonus grade-input mechanism.

## Legal & Compliance

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**This section remains flagged Critical.** Resolved from prior versions: MiniMoney does not hold, move, or take custody of funds. Initial launch jurisdiction is South Africa, governed by POPIA. A minor cannot access any part of the app without a pre-existing, consenting parent account. POPIA Section 34 and ARB Code of Advertising Practice Clause 14 remain cited as directly relevant statutory anchors (see v6 for full citation detail, unchanged).

**New in this revision, from `ResearchFindings\_v1.md`:**

1. **Item 7 — data retention:** POPIA Section 14 is confirmed (High confidence, statutory text) as the general principle: personal information may not be retained longer than necessary for its collection purpose, and destruction must render records unreconstructable; a data subject (or guardian, for a minor) may request correction/deletion at any time, with a 30-day response window. **No child-specific retention rule** (comparable to COPPA's or GDPR-K's more prescriptive regimes) was found within POPIA itself. A schools-sector convention of 7-year retention was found but is explicitly not confirmed to apply to a consumer fintech/edtech app — Research House correctly did not extend it by analogy. Whether POPIA's general principle is *sufficient* on its own for MiniMoney's specific data model remains an unresolved legal-interpretation question requiring a specialist opinion, not resolvable by further desk research.

2. **Item 8 — terminology precedent:** confirmed, with sourcing, that no ARB ruling, National Credit Regulator guidance, or other consumer- protection precedent addresses "payslip"/"invoice"/"late penalty"/ "arrears" terminology applied to a minor specifically. The ARB's general Clause 14 principle (prohibiting exploitation of children's credulity/inexperience) and the National Credit Act (which does not apply, since minors cannot enter binding credit agreements in SA law) are the closest applicable frameworks, but applying them to MiniMoney's specific terminology choice is confirmed to be an interpretive legal judgment, not a settled precedent. This strengthens, rather than resolves, the case for obtaining a specialist opinion specifically covering this terminology question.

3. **Item 6 — app-store policy:** Google Play's Families Policy loyalty- point disclosure requirement and Apple's Kids Category age-band/ parental-gate/advertising-review requirements are now confirmed with direct sourcing (see Technology above) as applying independent of real-money transactions.

4. **Item 9 — legal-opinion cost/firm scoping:** a firm shortlist and a rough order-of-magnitude cost range (R25,000-R80,000) now exist for budgeting purposes (see Revenue & Costs) — this is scoping information only; the legal opinion itself has still not been obtained.

We will assume that the POPIA's general retention principle is sufficient without child-specific supplementary rules; the exam-performance bonus mechanic wil not have any schools-data-privacy dimension as it will be purely based on the childs end result per subject; whether Apple's Kids Category age-band structure (which tops out at 9-11) is compatible with MiniMoney's 6-18 span if an iOS port proceeds — a new question surfaced by this revision's research that did not exist as a named concern in v6.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Risks identifiable from the described mechanic, largely unchanged from v6, with research-informed refinements:

- **Regulatory risk (Critical, substantially narrowed but not resolved):** unchanged from v6. A specialist legal opinion is still recommended, now with a firm shortlist and rough cost range available (see Legal & Compliance, Revenue & Costs).

- **Child-safety/data-privacy risk (Critical, substantially reduced):** unchanged from v6, with the new POPIA Section 14 statutory anchor (Item 7) narrowing the retention-policy sub-question specifically, though not resolving whether the general principle suffices without child-specific supplementary rules.

- **Trust/enforcement risk (unresolved):** unchanged from v6. MiniMoney still cannot itself detect or confirm that the parent's banking-app payment actually occurred.

- **Late-penalty/relationship risk (unresolved):** unchanged from v6.

- **Dispute-escalation risk (unresolved):** unchanged from v6.

- **Terminology/perception risk (now confirmed, not merely** **hypothesized):** `ResearchFindings\_v1.md` Item 8 confirms, with sourcing, that no prior ARB ruling or NCR guidance addresses this exact question — the risk is real and unresolved by precedent, meaning it rests entirely on a fresh interpretive legal judgment rather than an established or testable regulatory pathway. This is a firmer, better- evidenced statement of the risk than v6's more speculative framing.

- **Advertising/child-data risk (unchanged):** POPIA Section 34 and ARB Clause 14 jointly restrict any ad-targeting approach to contextual, non-profiled inventory. `ResearchFindings\_v1.md` Item 3's $0.80 eCPM figure suggests the monetary upside of pursuing ads at all is modest, which the Incubator flags as relevant risk/reward context: the compliance burden of an ad layer may not be proportionate to its likely revenue contribution.

- **Fintech Advance content risk (narrowed but not eliminated):** unchanged from v6.

- **Competitive risk (narrowed, evidence-backed, refined this** **revision):** `ResearchFindings\_v1.md` Item 5 adds that the strongest demonstrated demand signal among comparables (MoneyTime SA's claimed 130,000 students) comes via a B2B2C schools-distribution model, not a direct-to-parent consumer model — the Incubator flags this as a new, specific competitive-risk nuance: MiniMoney's chosen distribution model (direct-to-parent) may be harder to validate demand for than a schools-mediated alternative, since the best local evidence of scale belongs to a different distribution strategy.

- **Monetization-execution risk (partially narrowed):** unchanged from v6; Item 4 confirms the ads-vs-subscription decision cannot be resolved by research and must be made internally before the correct conversion-benchmark can be validated against.

- **App-store policy risk (now substantiated, not resolved):** Item 6 confirms specific, sourced disclosure obligations (Google Families Policy) and raises a new, more precise open question (Apple's IAP- routing rule for non-monetary in-game currencies, and Apple's Kids Category age-band ceiling of 9-11 versus MiniMoney's 6-18 span) — a materially more specific risk statement than v6's general flag.

- **Platform-concentration risk (narrowed, evidence-backed):** unchanged from v6.

- **Adoption/forecasting risk (now confirmed as structurally** **unresolvable by desk research, not merely under-evidenced):** Item 1 confirms no SA-specific benchmark exists and cannot be produced short of a commissioned survey (R80,000-R250,000, 3-6 weeks, yielding only stated-intent data, not verified behavior) or a live pilot. The Incubator flags this as strengthening, not weakening, the existing recommendation to treat the funnel range strictly as a planning estimate in any downstream financial modeling.

- **New — engineering-cost estimation risk (introduced by this** **revision):** the refined two-tier build-cost range ($25,000-$40,000 MVP; $60,000-$120,000+ full build) is sourced from development-agency marketing pages with an inherent incentive to anchor toward their own typical project size, and has not been checked against MiniMoney's actual feature spec via real quotes. The Incubator flags a risk of under- or over-budgeting against this range without obtaining actual informal bids.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Assumptions carried forward unchanged from v6 (parent-direct payment, SA launch jurisdiction, Freemium/parent-only IAP, universal consent gate, Android-first, Mbucks/Mpoints dual currency, 7-Mbuck cap with 3-Mbuck pilot cap, Fintech Advance scoping) — see v6 for full detail, none of which `ResearchFindings\_v1.md` addressed or altered.

**Newly informed by `ResearchFindings\_v1.md` (research findings, not** **Incubator assumptions):** the pricing, cost, and policy figures cited throughout this revision (MoneyTime SA's R995/year, the $0.80 SA eCPM, the two-tier engineering-cost range, the R25,000-R80,000 legal-opinion scoping range, Google's/Apple's app-store policy specifics) — each carrying Research House's own stated confidence level, preserved rather than flattened, consistent with how the user's own market-research confidence tags were preserved in v6.

**Still assumed, unchanged:** the exact Mbucks-to-Rand peg is fixed platform-wide; the app is intended primarily as a South African B2C product at launch; the exam-bonus grade data is self-reported/parent- entered; the late-penalty mechanic is intended as a behavioral nudge rather than a genuine financial detriment to be strictly collected.

**Newly flagged as confirmed-unresolvable, not merely unresolved:** whether the user's hand-edited 2% Freemium conversion figure targets the ads-hybrid or subscription-only benchmark — `ResearchFindings\_v1.md` Item 4 confirms this cannot be resolved externally; it depends entirely on an internal decision not yet made.

## Constraints

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Platform choice remains confirmed: Android primary, iOS as future porting work, substantiated by Statcounter data. **Still not addressed:** no company-side budget, timeline, or team-size figure has been supplied in any version. `ResearchFindings\_v1.md`'s cost-scoping findings (Items 9 and 10) provide external cost *ranges* the eventual company-side budget would need to accommodate, but do not supply the budget itself — this remains entirely the user's to provide. The user's known technical stack (Kotlin/Android) is directionally consistent with the confirmed Android- first platform choice, though this is not a stated fact in any input document.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in structure from v6's candidate MVP sequence (legal validation → free-tier core build → pilot → paywalled-feature layer → iOS evaluation). `ResearchFindings\_v1.md`'s findings refine step 1 (legal validation now has a firm shortlist and cost range to act against) and add a new candidate step the Incubator flags as worth considering before committing to the funnel-model figures in financial planning: **a** **low-cost informal quote request to 2-3 South African/offshore** **development agencies against MiniMoney's actual spec** (Item 10 notes this is typically free and low-effort, agencies quote informally to win business) to tighten the engineering-cost range before finalizing a build budget. This remains a recommendation, not a roadmap supplied by the user; no actual timeline, milestone plan, or resourcing detail has been supplied.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

No funding ask, runway, or financial projections are present in any input document. See Revenue & Costs above for the full candidate cost/revenue framework. `ResearchFindings\_v1.md` materially improves the specificity of the cost side without resolving the revenue side: a refined two-tier engineering-cost range, a legal-opinion cost/firm scoping range (R25,000-R80,000), and one real pricing comparable (MoneyTime SA, R995/year, likely under-anchoring) are now available as budgeting inputs. Absolute Rand/USD revenue still cannot be modeled, since no MiniMoney-specific price point or company-side budget/timeline has been supplied. Status remains Partial/Supported: cost-side specificity has materially improved; revenue-side and company-budget inputs remain unsupplied.

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Recommended validation priorities, in sequence, largely unchanged from v6, refined by this revision's findings:

1. **Legal validation (recommended, reduced urgency, now scoped):** obtain a POPIA/ARB-specialist legal opinion — now with a firm shortlist (Caveat Legal, VeraSafe, PPM Attorneys, Bregman Moodley Attorneys, MJ Kotze Inc) and a rough cost range (R25,000-R80,000) to budget and plan against, rather than an open-ended "get a lawyer" placeholder.

2. **Trust/enforcement AND late-penalty validation (elevated priority):** unchanged from v6.

3. **Dispute-mechanism validation:** unchanged from v6.

4. **Market/demand validation, now with a confirmed data ceiling:** `ResearchFindings\_v1.md` Item 1 confirms that closing the SA-specific adoption-benchmark gap requires either a commissioned parent survey (R80,000-R250,000, 3-6 weeks, TGM Research/GeoPoll/Experipanel- InfoQuest Africa identified as active SA vendors, though none publish fixed pricing) or a live pilot — a low-cost smoke test (landing page, pilot-cohort signup) remains the recommended first, cheaper step before committing to either.

5. **Pricing/conversion validation:** unchanged from v6, now with MoneyTime SA's R995/year as one real (if likely under-anchoring) reference point to test parent price sensitivity against, alongside the existing 2-4%/1-3% conversion benchmarks.

6. **Curriculum validation:** unchanged from v6.

7. **New — informal engineering-cost quote request:** obtain 2-3 informal ballpark quotes from South African or offshore development agencies against MiniMoney's actual feature spec, a low-cost step (typically free) that would tighten the $25,000-$120,000+ range into an actionable build budget.

This section remains Partial: several validation steps are now more specifically scoped (cost, firm names, vendor names), but no validation activity has actually occurred.

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

`ResearchFindings\_v1.md` is added as a second tranche of external evidence, distinct in kind from both the Incubator's own general- knowledge content and the user-supplied market research in `Clarifications\_v6.md`. Per standing instruction, vendor research is never Verified-tier and is treated with independent Incubator scrutiny, detailed at the top of this document. Newly available:

- \[Supported/High\] Google Play Families Policy loyalty-point disclosure requirement; POPIA Section 14 general retention principle.

- \[Supported/Medium\] Apple Kids Category guideline specifics (age-band, parental gates, IAP-currency question unresolved); SA eCPM figure ($0.80, third-party aggregator); MoneyTime SA pricing (R995/year) and usage claim (130,000 students, self-published); MoneyAfrica Kids download bands (10,000+ Google Play, 3,000+ Apple); engineering-cost range ($25,000-$120,000+, five converging agency sources); legal- opinion cost/firm scoping (R25,000-R80,000, five named firms, one sourced R8,325 comparable).

- \[Confirmed negative findings, High confidence they are genuine gaps\]: no SA-specific kids'-app adoption/conversion benchmark exists; no ARB/ NCR precedent on payslip-terminology-to-minors exists; MoneyAfrica Kids' premium price is unpublished.

This is genuine, if vendor-sourced, Supporting Evidence — the Incubator treats it as one tier below the user's own directly-cited `Clarifications\_v6.md` research (which included primary statutory/ statistical sources the user personally selected and confidence-tagged), since Research House's findings include more secondary/aggregator sourcing (agency marketing pages, third-party eCPM blogs) alongside genuinely primary sources (Apple's and Google's own policy pages, POPIA statutory text, company pricing pages). Status remains Partial: no user interviews, prior prototype, or direct MiniMoney-specific demand signal exists; no legal opinion has been obtained despite now having a scoped cost/firm range to commission one.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Carried forward from v6 (items 1-15 unchanged — see v6 for full detail: fund custody, jurisdiction, monetization choice, consent-gate model, task verification, dispute-escalation-beyond-48-hours, payment-routing timeline, platform, late-penalty cap, Fintech Advance scope, arrears disposition, exam-bonus data source, Mbucks-peg flexibility, curriculum age-band splits, ads-vs-subscription decision — all resolved or open exactly as stated in v6, since none of the 10 research items targeted these directly except where noted below).

1. ~~Is there any existing prototype, wireframe, or prior research the~~ ~~user has already produced that could accelerate validation?~~ **Not** **addressed by this research engagement** — remains open.

2. ~~Has the user considered app-store policy restrictions specific to~~ ~~apps in the "designed for kids" category?~~ **Substantially** **addressed:** Google Play Families Policy and Apple Kids Category specifics are now sourced (see Technology, Legal & Compliance). **New** **sub-question raised by this research:** does Apple's IAP-routing rule for "in-game currencies" that gate features apply to the non-cash-out Mpoints system, and is Apple's Kids Category age-band structure (topping out at 9-11) compatible with MiniMoney's 6-18 span for an eventual iOS port?

3. What company-side budget, timeline, and team size are available for the actual build? **Still open** — external cost ranges now exist (Items 9, 10) but do not substitute for the user's own budget figure.

4. Does the user wish to commission a specialist POPIA/ARB legal opinion? **Still open**, now with a firm shortlist and cost range to act on (R25,000-R80,000; Caveat Legal, VeraSafe, PPM Attorneys, Bregman Moodley Attorneys, MJ Kotze Inc).

5. **New, introduced by this revision:** does the user wish to commission a parent-focused market-research survey (R80,000- R250,000, 3-6 weeks, via TGM Research, GeoPoll, or Experipanel/ InfoQuest Africa) to move the adoption/conversion assumption from Assumed/Guessing toward Likely/Supported for stated purchase intent — noting this would not verify actual install/conversion behavior, only a live pilot would do that?

6. **New, introduced by this revision:** does the user wish to request informal ballpark build quotes from 2-3 South African or offshore development agencies against MiniMoney's actual spec, to tighten the $25,000-$120,000+ engineering-cost range (a low-cost, typically free step)?

7. **New, introduced by this revision:** does the user wish to attempt a manual walkthrough of MoneyAfrica Kids' payment flow (or direct company outreach) to obtain its unpublished premium price point?

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts. Critical sections (marked ★) are double-weighted.

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


Points earned: 2+2+2+2+2+2+2+2+2+2+2+5+2+4+2+2+2+2+2+2+2+5+2+4 = **54**

Points possible: 21 non-critical sections × 5 = 105, plus 3 critical sections × 5 × 2 = 30. Total possible = **135**

**Readiness Score = 54 / 135 = 40%**

**This score is numerically unchanged from v6** (40%), despite this revision incorporating a completed Research House engagement across 10 items. This is a deliberate, self-certified outcome, not an oversight: the Incubator's own scrutiny of `ResearchFindings\_v1.md` determined that none of the 10 findings resolved a section's central open question sufficiently to justify a Status change from Partial to Complete (or Incomplete to Partial) under the rubric's binary Status test. Several findings instead (a) confirmed, with sourcing, that certain gaps are genuinely unclosable by further desk research (adoption benchmarks, terminology precedent) — which strengthens confidence *that the gap is* *correctly characterized*, but does not close it; and (b) supplied real but partial figures (pricing, cost ranges, policy specifics) that improve a Partial section's internal quality without meeting the bar for Complete, since core open questions (a legal opinion, a company-side budget, a monetization-model decision, a validated adoption rate) remain unresolved in every case. The Incubator flags this as the same structural feature noted in v6: qualitative improvement in evidence quality does not necessarily move the binary Status rubric, particularly when — as here — the vendor engagement's most valuable output is confirming which gaps require paid, non-desk-research work (a commissioned survey, a legal opinion, informal agency quotes) rather than closing them outright.

No section is Critical + Incomplete: Legal & Compliance and Child Data & Consent are both Partial.

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** — the universal parental-consent design is in place and specific statutory citations exist, and this revision adds a firm shortlist and cost range (R25,000-R80,000) for the still-unobtained specialist legal opinion, plus new sourced findings on POPIA retention (Section 14) and app-store child-category policy (Google Families Policy, Apple Kids Category) — but the opinion itself has still not been obtained, and a new sub-question (Apple's Kids Category age-band ceiling of 9-11 vs. MiniMoney's 6-18 span) has been surfaced, not resolved.

2. **Supporting Evidence (Partial)** — now includes a second tranche of external evidence (Research House, 10 items), materially improving specificity on cost, pricing, and policy questions, but confirming rather than closing the two most decision-relevant gaps: no SA- specific adoption/conversion benchmark exists, and no direct MiniMoney-specific user testing, prototype, or legal opinion has been obtained.

3. **Objectives / Success Criteria / Validation Strategy (Partial)** — unchanged from v6: anchored by a real funnel model, but specific numeric targets remain unconfirmed, and Outstanding Question 15 (which conversion benchmark the 2% figure targets) is now confirmed — not merely believed — to be unresolvable without an internal decision.

4. **Constraints (Partial, unchanged)** — platform choice is confirmed and substantiated; external cost ranges now exist for budgeting reference, but no company-side build budget, timeline, or team-size figure has been supplied in any version.

5. **Late-penalty and dispute-escalation mechanics (Operations Complete,** **Risks Partial, unchanged)** — internally consistent at 5→6→7 Mbucks/week (pilot cap 3); the underlying, still-untested trust/ fairness risk is unaffected by this revision's research, which did not target this mechanic.

6. **New — Monetization-model decision (Business Model/Success Criteria,** **confirmed non-researchable):** `ResearchFindings\_v1.md` Item 4 confirms the ads-hybrid vs. subscription-only decision is a pending internal choice, not a fact any further research — paid or unpaid — can resolve. This is now the case's most clearly-defined "the user must simply decide" gap, distinct from every other gap in this document, which are at least theoretically closable by further work (legal opinion, survey, pilot, quotes).

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

*Appended because MiniMoney is an education product for a 12-year age* *span (6-18) — the completion gate requires domain-specific sections for* *products with curriculum design needs.*

Unchanged from v6: the age floor of 6 introduces financial literacy early via short daily/weekly-completable content (currency differentiation, "word sums" for change/remainder calculation); "Fintech Advance" is a distinct, fully-scoped 15-18-only conceptual course (forex/dropshipping concepts, no trading execution), described by the user as a "non-negotiable requirement" for that age band, gated by separate parent opt-in. `ResearchFindings\_v1.md` did not target curriculum content directly; no change to Status. **Still unresolved:** specific age-band curriculum splits, instructional format, standards alignment, and content authorship, including for Fintech Advance specifically.

## Legal & Compliance — Child Data & Consent (Domain Extension)

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

*Appended because MiniMoney targets users as young as age 6, triggering* *child-directed-app compliance obligations beyond general Legal &* *Compliance.*

**Model:** unchanged — every minor requires a pre-existing, consenting parent account before any access.

**Newly specific per `ResearchFindings\_v1.md`:**

1. **POPIA Section 14 (Item 7):** the general retention principle is confirmed as statutory text (records not retained longer than necessary; destruction must be unreconstructable; 30-day response window for deletion requests). No child-specific supplementary retention rule exists within POPIA itself — whether the general principle is sufficient for MiniMoney's data model remains an unresolved legal-interpretation question.

2. **App-store child-category policy (Item 6):** Google Play's Families Policy requires conspicuous disclosure of any point-accrual/ redemption ratio (directly applicable to Mpoints), independent of real-money involvement. Apple's Kids Category requires age-band selection, human-reviewed advertising, and parental gates for unlock mechanics; whether its IAP-currency rule extends to a non-cash-out points system remains unresolved and is flagged as needing either a direct App Review submission or legal confirmation.

3. **Terminology precedent (Item 8):** confirmed that no ARB ruling or NCR guidance addresses "payslip"/"invoice"/"late penalty"/"arrears" terminology applied to minors specifically — this remains a fresh interpretive legal question, not a settled or even precedented one.

4. **Legal-opinion scoping (Item 9):** a firm shortlist and rough cost range (R25,000-R80,000) now exist to act on.

**Resolved relative to prior versions:** unchanged from v6.

**Unresolved, specifically:** a specialist POPIA/ARB legal opinion has still not been obtained, though it is now scoped and budgetable; whether POPIA's general retention principle suffices without child-specific supplementary rules; whether the Mpoints store's Apple IAP-currency question requires a direct App Review test or legal confirmation; whether "payslip"/"invoice"/"late penalty"/"arrears" terminology carries regulatory implication (confirmed as unprecedented, not resolved); whether the exam-performance bonus mechanic implies any school-data-privacy dimension; **new** — whether Apple's Kids Category age-band structure (5-and-under, 6-8, 9-11) is compatible with MiniMoney's full 6-18 span for an eventual iOS port.

This should still be confirmed via a South African data-protection and advertising-law legal opinion before technical build begins.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal & Compliance and Child Data & Consent are both Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 40% (unchanged from v6; up from 39% in v5, 36% in v4, 24% in v3).

- Expert roster entries ≥3 sentences, each naming a specific case-study assumption: see `ExpertRoster.md`.

- Devil's Advocate objections ≥3, each citing a specific section: see `reviews/DevilsAdvocate.md`.

- ExecutiveSummary.md generated per fixed format: see `ExecutiveSummary.md`.

**This Business Case does not currently pass its own completion gate.** The Critical + Incomplete condition remains cleared. The Readiness Score is numerically unchanged at 40% despite incorporating a completed Research House engagement, because — per the Incubator's own scrutiny, detailed at the top of this document — none of the 10 vendor findings resolved a section's central open question to the binary Status rubric's Complete threshold; several instead confirmed that certain gaps require paid, non-desk-research work (a commissioned survey, a legal opinion, informal agency quotes) to close, which is valuable planning information but not itself a closed gap. A v8 would need: a commissioned specialist POPIA/ARB legal opinion (now scoped, R25,000-R80,000, firm shortlist available), a user decision on ads-vs-subscription-only monetization (confirmed non-researchable — this is the single most clearly "just decide" item in the case), company-side budget/timeline/team figures, and ideally either informal engineering quotes or early pilot feedback, to meaningfully advance the score further.

